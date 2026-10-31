"""Merge the Toccata final-design tabs into ONE artifact page (index.html).

Final structure (2026-10-08, materials bought; the page shows only the final design):

  tab id    nav                      source
  summary   요약 한눈에 보기          src/summary.html            (src/build_summary.py)
  circuit   01 회로도                 hardware/pcb/page/circuit.{html,css,js} + assets.txt   (hardware/pcb/src/build.py -> page.py)
  dwg       02 설계도                 src/tabs/dwg/               (src/tabs/dwg/build_section.py; sheets from cad/src/drawings_final.py)
  partdwg   03 부품 도면·출력 파일    src/tabs/partdwg/           (hardware/mechanical/cad/src/part_sheets.py)
  cad       04 3D 모델                hardware/mechanical/cad/viewer/cad.{html,css,js}  (viewer/gen_viewer.py)
  sim       05 동작 시뮬레이션        src/tabs/sim/               (key-action-v4/model/export_sim.py)
  parts     06 부품·사용처            src/tabs/parts/             (cad/src/locate.py -> src/tabs/parts/build_section.py)
  prep      07 준비 체크              src/tabs/prep/              (src/build_prep.py)
  design    08 건반 액션 원리         src/progress.html p-design  (합니다체 + 개정 기록 뺌, this file)
  build     09 출력·조립              this file: print plan from cad/manifest.json, plywood / boards / body / desk /
                                      touchscreen / lids / service steps from cad/README.md, + module steps,
                                      key removal and adjustment from src/progress.html p-build
  check     10 검증·남은 위험         src/progress.html p-check   (남은 문제·단계 0 시험·남은 위험; 합니다체)
  asm       11 한 옥타브 조립         src/tabs/asm/               (src/tabs/asm/build_section.py from docs/report/octave-assembly)

Fragment contract (src/tabs/<id>/): section.html (one <section class="page" id="p-<id>" hidden>), style.css (scoped to
#p-<id>), script.js (one IIFE), assets.txt (runtime files relative to this folder), meta.json.

Publish-file bundles: one artifact version holds at most 511 files. The 122 per-part zips (fin/parts/*.zip.b64.txt)
and the location detail figures (fin/loc/detail/*.svg) are packed into a few JSON files under fin/bundle/ (written by
this script). The first page script installs window.toccata.bundle and wraps fetch() so a fetch of a bundled path is
answered from its bundle; the 06 detail <img> goes through toccata.bundle.img() (one-line patch of the parts script,
asserted below). The original files stay on disk and are simply not published.

usage:  python3 merge.py            -> index.html + publish_files.json (+ fin/bundle/*.json)
        python3 merge.py --check    -> also validates the page (sections, ids, links, local paths, scripts, CSS scope,
                                       size, bundles, 합니다체 leftovers in 08~10)
Publish: see README.md in this folder (same artifact URL every time).
"""
import base64
import collections
import glob
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PCB = os.path.join(ROOT, "hardware", "pcb", "page")
CAD = os.path.join(ROOT, "hardware", "mechanical", "cad")
TABS = os.path.join(HERE, "src", "tabs")
MAX_FILE = 15 * 1024 * 1024
VERSION_FILES = 511


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def styles(s):
    return re.findall(r"<style[^>]*>(.*?)</style>", s, flags=re.S)


def main_css(s):
    """The page's own stylesheet (the publish skeleton adds a small first <style>)."""
    st = styles(s)
    return max(st, key=len)


def between(s, a, b, start=0):
    i = s.index(a, start) + len(a)
    j = s.index(b, i)
    return s[i:j]


def split_css(css):
    """Split CSS into top-level blocks: (prelude, body) with body excluding outer braces."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        pre = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        out.append((pre, css[j + 1:k - 1]))
        i = k
    return out


def scope_css(css, scope):
    res = []
    for pre, body in split_css(css):
        if pre.startswith("@media") or pre.startswith("@supports"):
            res.append(f"{pre}{{{scope_css(body, scope)}}}")
        elif pre.startswith("@"):
            res.append(f"{pre}{{{body}}}")
        else:
            sels = []
            for sel in pre.split(","):
                sel = sel.strip()
                if not sel:
                    continue
                if sel.startswith(":root") or sel in ("html", "body"):
                    sels.append(sel)
                else:
                    sels.append(f"{scope} {sel}")
            res.append(",".join(sels) + "{" + body + "}")
    return "\n".join(res)


def extract_progress(s):
    css = main_css(s)
    nav = between(s, '<nav class="tabs" aria-label="페이지"><div class="wrap">', "</div></nav>")
    main = between(s, '<main class="wrap">', "</main>")
    foot = between(s, "<footer><div class=\"wrap\">", "</div></footer>")
    script = re.findall(r"<script>(.*?)</script>", s, flags=re.S)[0]
    if '<span class="sep"></span>' in nav:
        tabs, alts = nav.split('<span class="sep"></span>', 1)
    else:
        tabs, alts = nav, ""
    return dict(css=css, tabs=tabs, alts=alts, main=main, foot=foot, script=script)


def page_section(main, sid):
    a = main.find(f'<section class="page" id="{sid}"')
    if a < 0:
        return ""
    b = main.find('<section class="page"', a + 10)
    return main[a:] if b < 0 else main[a:b]


def split_h3(sec):
    """(head, [(title, chunk)], tail) of a page section split at its top-level <h3> headings."""
    end = sec.rfind("</section>")
    body, tail = sec[:end], sec[end:]
    parts = re.split(r"(?=<h3[ >])", body)
    chunks = []
    for c in parts[1:]:
        title = re.sub(r"<[^>]+>", "", re.search(r"<h3[^>]*>(.*?)</h3>", c, re.S).group(1)).strip()
        chunks.append((title, c))
    return parts[0], chunks, tail


def filter_h3(sec, keep=None, drop=None, intro=None):
    """Split a page section at its top-level <h3> headings; keep / drop chunks by heading text prefix."""
    head, chunks, tail = split_h3(sec)
    if intro is not None:
        h2 = re.search(r"<h2>.*?</h2>", head, re.S)
        head = head[:h2.end()] + intro if h2 else head
    out = [head]
    for title, c in chunks:
        if keep is not None and not any(title.startswith(k) for k in keep):
            continue
        if drop is not None and any(title.startswith(d) for d in drop):
            continue
        out.append(c)
    return "".join(out) + tail


# --------------------------------------------------------------------------------------------- asset sync
def sync_circuit_svgs():
    """Copy the current schematic / board SVGs from hardware/pcb into sch/ (published paths)."""
    dst = os.path.join(HERE, "sch")
    os.makedirs(dst, exist_ok=True)
    root = os.path.normpath(os.path.join(PCB, ".."))
    n = 0
    for sub in ("schematic", "board"):
        for f in glob.glob(os.path.join(root, sub, "*.svg")):
            shutil.copy2(f, dst)
            n += 1
    return n


def sync_cad_assets():
    """04 3D 모델: copy viewer/parts.json and ship the GLB as base64 text (the artifact host does not serve .glb).

    GLB = hardware/mechanical/cad/viewer/assets.json "glb" (repo-relative) when that file exists,
    else the older hardware/mechanical/cad/Toccata_전체조립.glb."""
    dst = os.path.join(HERE, "cad")
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(os.path.join(CAD, "viewer", "parts.json"), os.path.join(dst, "parts.json"))
    shutil.copyfile(os.path.join(CAD, "viewer", "asm.json"), os.path.join(dst, "asm.json"))      # 조립 순서 보기 (asm_graph.py)
    glb = os.path.join(CAD, "Toccata_전체조립.glb")
    aj = os.path.join(CAD, "viewer", "assets.json")
    if os.path.exists(aj):
        rel = json.load(open(aj, encoding="utf-8")).get("glb")
        if rel:
            cand = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
            if os.path.exists(cand):
                glb = cand
    raw = open(glb, "rb").read()
    with open(os.path.join(dst, "toccata.glb.b64.txt"), "w") as f:
        f.write(base64.b64encode(raw).decode("ascii"))
    old = os.path.join(dst, "toccata.glb")
    if os.path.exists(old):
        os.remove(old)
    return os.path.relpath(glb, ROOT), len(raw)


# D01~D05 dimensioned sheets + R01~R03 renders from hardware/mechanical/cad/src/drawings.py (build_all.py runs it).
# The 02 설계도 tab (rear group) and the summary hero use them from rear/.
REAR_DIR = "rear"
REAR_SHEETS = ["D01_plan", "D02_speaker_section", "D03_centre_sections", "D04_rear_elevation", "D05_touchscreen"]   # D06 dropped 10/16 (A안)
REAR_RENDERS = ["R01_front", "R02_rear_left", "R03_folded"]


def sync_rear_drawings():
    """copy cad/drawings/D0*.svg|png and cad/renders/R0*.png into rear/ (published paths rear/...)."""
    dst = os.path.join(HERE, REAR_DIR)
    os.makedirs(dst, exist_ok=True)
    copied = []
    for stem in REAR_SHEETS:
        for ext in (".svg", ".png"):
            src = os.path.join(CAD, "drawings", stem + ext)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst, stem + ext))
                copied.append(REAR_DIR + "/" + stem + ext)
    for stem in REAR_RENDERS:
        src = os.path.join(CAD, "renders", stem + ".png")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, stem + ".png"))
            copied.append(REAR_DIR + "/" + stem + ".png")
    return copied


# --------------------------------------------------------------------------------------------- publish bundles
BUNDLE_DIR = "fin/bundle"
BUNDLE_MAX = 1_400_000          # bytes of content per bundle file (lazy fetch on first use)
BUNDLE_RULES = [                # (regex on published path, bundle stem from match)
    (re.compile(r"^fin/parts/P-([0-9A-Z]+)-\d+\.zip\.b64\.txt$"), lambda m: "parts-zip-" + m.group(1).lower()),
    (re.compile(r"^fin/loc/detail/(i\d+)\.svg$"), lambda m: "loc-detail-items"),
    (re.compile(r"^fin/loc/detail/(p-[^/]+)\.svg$"), lambda m: "loc-detail-prints"),
    (re.compile(r"^fin/loc/detail/(ply-[^/]+)\.svg$"), lambda m: "loc-detail-plywood"),
    (re.compile(r"^fin/loc/detail/([a-z]\d+)\.svg$"), lambda m: "loc-detail-other"),
]


def bundle_stem(path):
    for rx, fn in BUNDLE_RULES:
        m = rx.match(path)
        if m:
            return fn(m)
    return None


def make_bundles(paths):
    """Pack bundled paths into fin/bundle/<stem>[-n].json ({path: text}). Returns (path -> bundle file, info)."""
    groups = collections.OrderedDict()
    for p in sorted(paths):
        st = bundle_stem(p)
        if st and os.path.isfile(os.path.join(HERE, p)):
            groups.setdefault(st, []).append(p)
    out_dir = os.path.join(HERE, BUNDLE_DIR)
    os.makedirs(out_dir, exist_ok=True)
    for old in glob.glob(os.path.join(out_dir, "*.json")):
        os.remove(old)
    mapping, info = {}, []
    for st, plist in groups.items():
        chunks, cur, cur_b = [], [], 0
        for p in plist:
            b = os.path.getsize(os.path.join(HERE, p))
            if cur and cur_b + b > BUNDLE_MAX:
                chunks.append(cur)
                cur, cur_b = [], 0
            cur.append(p)
            cur_b += b
        if cur:
            chunks.append(cur)
        for n, ch in enumerate(chunks, 1):
            name = f"{BUNDLE_DIR}/{st}{'-%d' % n if len(chunks) > 1 else ''}.json"
            data = {p: read(os.path.join(HERE, p)) for p in ch}
            with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            for p in ch:
                mapping[p] = name
            info.append({"bundle": name, "files": len(ch), "bytes": os.path.getsize(os.path.join(HERE, name))})
    return mapping, info


BUNDLE_JS = r"""
(function(){
  // published-file bundles (merge.py): small files are packed into a few JSON files under fin/bundle/ so one artifact
  // version stays under its file limit. fetch() of a bundled path is answered from its bundle; images use bundle.img().
  // API: window.toccata.bundle = { has(path), text(path) -> Promise<string>, url(path) -> Promise<img url>, img(imgEl, path) }
  var T = window.toccata = window.toccata || {};
  var MAP = __MAP__;
  var TYPES = { svg: 'image/svg+xml', txt: 'text/plain', json: 'application/json' };
  var base = ''; try { base = new URL('.', location.href).href; } catch (e) {}
  var nativeFetch = typeof window.fetch === 'function' ? window.fetch.bind(window) : null;
  var cache = {}, urls = {};
  function has(p) { return Object.prototype.hasOwnProperty.call(MAP, p); }
  function rel(u) {
    u = String(u).split('#')[0].split('?')[0];
    if (!/^[a-z][a-z0-9+.-]*:/i.test(u) && u.charAt(0) !== '/') return u.replace(/^\.\//, '');
    return base && u.indexOf(base) === 0 ? u.slice(base.length) : null;
  }
  function type(p) { return TYPES[(p.split('.').pop() || '').toLowerCase()] || 'application/octet-stream'; }
  function load(file) {
    if (!cache[file]) {
      cache[file] = nativeFetch(file).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + file);
        return r.json();
      });
      cache[file].catch(function () { delete cache[file]; });
    }
    return cache[file];
  }
  function text(p) {
    if (!has(p) || !nativeFetch) return Promise.reject(new Error('not bundled: ' + p));
    return load(MAP[p]).then(function (d) {
      if (typeof d[p] !== 'string') throw new Error('missing in bundle: ' + p);
      return d[p];
    });
  }
  if (nativeFetch && typeof Response === 'function') {
    window.fetch = function (input, init) {
      var u = typeof input === 'string' ? input : (input && input.url), p = u ? rel(u) : null;
      var method = (init && init.method) || (input && typeof input === 'object' && input.method) || 'GET';
      if (p && has(p) && String(method).toUpperCase() === 'GET') {
        return text(p).then(function (t) {
          return new Response(t, { status: 200, headers: { 'Content-Type': type(p) + ';charset=utf-8' } });
        });
      }
      return nativeFetch(input, init);
    };
  }
  function probe(u) {
    return new Promise(function (ok, bad) {
      var im = new Image();
      im.onload = function () { ok(u); };
      im.onerror = function () { bad(new Error('image')); };
      im.src = u;
    });
  }
  function url(p) {
    if (!urls[p]) {
      urls[p] = text(p).then(function (t) {
        var data = 'data:' + type(p) + ';charset=utf-8,' + encodeURIComponent(t), blob = null;
        try { blob = URL.createObjectURL(new Blob([t], { type: type(p) })); } catch (e) {}
        return blob ? probe(blob).catch(function () { return probe(data); }) : probe(data);
      });
      urls[p].catch(function () { delete urls[p]; });
    }
    return urls[p];
  }
  function img(el, p) {
    if (!has(p)) { el.setAttribute('src', p); return; }
    url(p).then(function (u) { el.setAttribute('src', u); }, function () { el.setAttribute('src', p); });
  }
  T.bundle = { has: has, text: text, url: url, img: img };
})();
"""

# 06 detail figures are <img data-src> set on <details> open; route them through the bundle (one asserted line).
PARTS_IMG_OLD = "img.setAttribute('src', img.getAttribute('data-src'));"
PARTS_IMG_NEW = ("(window.toccata && window.toccata.bundle ? window.toccata.bundle.img(img, img.getAttribute('data-src'))"
                 " : img.setAttribute('src', img.getAttribute('data-src')));")


# --------------------------------------------------------------------------------------------- 08~10: 합니다체, no history
HANGUL0 = 0xAC00
_ADJ_VOWEL = ("크", "다르", "아니", "빠르", "느리", "비싸", "이르", "싸", "짜", "흐리", "나쁘", "바쁘", "아프", "쓰",
              "무르", "모자라")


def _jong(c):
    o = ord(c) - HANGUL0
    return o % 28 if 0 <= o < 11172 else -1


def _with_jong(c, j):
    o = ord(c) - HANGUL0
    return chr(HANGUL0 + (o - o % 28) + j)


def _conv_word(stem):
    """해라체 sentence end (stem + '다') -> 합니다체, or None to leave it."""
    if not stem or stem.endswith(("보", "에", "까지", "마", "니")):
        return None                                   # 보다 (comparison), 마다 (each), …니다 already 합니다체
    if stem == "이":
        return "입니다"                                # 2.84이다
    P, j = stem[-1], _jong(stem[-1])
    if j < 0:
        return None
    if P == "는" and len(stem) >= 2:
        return stem[:-1] + "습니다"                    # 넣는다
    if j == 4:                                        # ㄴ: 한다, 본다, 민다, 붙인다
        return stem[:-1] + _with_jong(P, 17) + "니다"
    if j == 0:
        if stem.endswith(_ADJ_VOWEL):
            return stem[:-1] + _with_jong(P, 17) + "니다"
        if P == "이" and len(stem) >= 2 and _jong(stem[-2]) > 0:
            return stem[:-1] + "입니다"                # 기준이다
        return stem + "입니다"                         # 차이다, 모서리다
    if j == 8:                                        # ㄹ: 길다
        return stem[:-1] + _with_jong(P, 17) + "니다"
    return stem + "습니다"                             # 있다, 없다, 했다, 작다


_END = r"(?=[.:;)!?,(]|\s+[—–(\[]|\s*$)"
_WORD_RE = re.compile(r"([가-힣]*)다" + _END)
_NONH_RE = re.compile(r"(?<=[0-9A-Za-z%°)\]µ'’\"²³])다" + _END)
_RTAG = r"(?:r\d(?:\.\d+)?|v3(?:\.\d)?)"
_FIX = r"(?:\s*(?:고침(?:\s*\d+[a-z]?(?:·\d+[a-z]?)*)?|회로\s*2차|출력 공구))*"


def hamnida_text(t):
    t = _WORD_RE.sub(lambda m: _conv_word(m.group(1)) or m.group(0), t)
    return _NONH_RE.sub("입니다", t)


def strip_history_text(t):
    """Drop revision tags (r4.5 고침 2b, v3 …) and history comparisons (r3 68.9) from plain text."""
    t = re.sub(r"\s*\(\s*(?:r\d(?:\.\d+)?|v3)(?:\s+[-+0-9]|는|은|도|의|에서|와|과)[^()]*\)", "", t)
    t = re.sub(r"\br\d(?:\.\d+)?(?:\s*고침\s*\d*[a-z]?)?(?:부터|에서)\s+", "", t)
    t = re.sub(r"\s*\(\s*" + _RTAG + _FIX + r"(?:\s*방향)?\s*\)", "", t)                 # (r4.5 고침) (v3 방향)
    t = re.sub(r"\(\s*" + _RTAG + _FIX + r"\s*;\s*", "(", t)                             # (r4.4 고침 2b; …
    t = re.sub(r",\s*" + _RTAG + _FIX + r"(?=\s*\))", "", t)                             # …, r4.5 고침)
    t = re.sub(r"(^|[(;·,]\s*|\.\s+)" + _RTAG + _FIX + r"(?:\([^()]*\))?\s*:\s*", r"\1", t)
    t = re.sub(r"(?<=[\s→])" + _RTAG + _FIX + r"\s*:\s*", "", t)
    t = re.sub(r"\(\s*고침(?:\s*\d+[a-z]?(?:·\d+[a-z]?)*)?\s*:\s*", "(", t)              # (고침 2b: …
    t = re.sub(r"(\(|^|\s)" + _RTAG + _FIX + r"\s+(?=[가-힣A-Za-z])", r"\1", t)          # (r4.5 미스미 …
    return t


def walk_text(h, fn):
    """Apply fn to text outside tags; skip <script>, <style>, <code>."""
    out, i, skip = [], 0, None
    for m in re.finditer(r"<[^>]+>", h):
        txt = h[i:m.start()]
        out.append(txt if skip else fn(txt))
        tag = m.group(0)
        tn = re.match(r"</?([a-zA-Z0-9]+)", tag)
        name = tn.group(1).lower() if tn else ""
        if name in ("script", "style", "code"):
            skip = None if tag.startswith("</") else name
        out.append(tag)
        i = m.end()
    out.append(h[i:] if skip else fn(h[i:]))
    return "".join(out)


def tidy_html(h):
    h = h.replace("\\</td><td>", "|")          # 'F\|F#' split into two cells by the report's table writer
    return walk_text(h, lambda t: hamnida_text(strip_history_text(t)))


def apply_overrides(h, pairs, misses, tag):
    for old, new in pairs:
        if old not in h:
            misses.append(f"{tag}: {old[:60]}")
            continue
        h = h.replace(old, new)
    return h


def drop_rows(h, needles, misses, tag):
    for nd in needles:
        rx = re.compile(r"<tr>(?:(?!</tr>).)*" + re.escape(nd) + r"(?:(?!</tr>).)*</tr>", re.S)
        h, n = rx.subn("", h)
        if not n:
            misses.append(f"{tag} row: {nd}")
    return h


DESIGN_NOTE = ('<p class="small muted">글의 ‘10.1장’, ‘17장’ 같은 번호는 <code>hardware/mechanical/key-action-v4/DESIGN.md</code>의 '
               '장 번호입니다. 좌표는 mm이고 x 가로, y 흰 건반 앞 끝에서 뒤로, z 책상에서 위로입니다.</p>')

OVR_DESIGN = [
    ("윗판(프레임과 한 몸, z72.85)은 r3 브리지를 y146.5까지 늘린 것이다.", "윗판(프레임과 한 몸, z72.85)은 y146.5까지 이어진다."),
    ("<b>PETG 응력 한계(r3 기준 유지)</b>", "<b>PETG 응력 한계</b>"),
    ("<b>펌웨어 유령 거름(U6, r4.1 고침; r4.5 회로 2차: 글을 모델 gfilter·SCH-03 주 9와 같게)</b>",
     "<b>펌웨어 유령 거름(U6, 모델 gfilter·SCH-03 주 9와 같음)</b>"),
    ("r4.0의 문턱 1.2 m/s는 0.8~1.1 m/s 화음의 유령(내려옴 0.03~0.17 m/s)을 통과시켰다(검증자).",
     "문턱을 1.2 m/s로 두면 0.8~1.1 m/s 화음의 유령(내려옴 0.03~0.17 m/s)이 통과하므로 0.3 m/s로 둔다."),
    ("(드문 하중, r3 기준)", "(드문 하중)"),
    ("r4.5 고침 2 코일 뜸(검증 major):", "코일 뜸:"),
    ("(r4.5 한 면 받침이면 코일이 봉으로 0.47 밀려 2.18)", "(한 면 받침이면 코일이 봉으로 0.47 밀려 2.18)"),
    ("ABUSE 7.96 MPa (홈 없던 단면 3.44)", "ABUSE 7.96 MPa"),
    ("; r4.4 고침 2까지는 길이 없었음(핀 발이 바닥~윗판, 기판 뒤 여유 1.3)", ""),
    ("(고침 1 옆벽이면 0.73)", ""),
    ("(v3 z59, r3 커버 z78.0·머리 z80.7)", ""),
    ("(r4.4 펠트)", ""),
]
DESIGN_DROP_ROWS = ["필라멘트·출력 시간 (88건반", "기본 구성 비용 변화 (한도"]

OVR_BUILD = [
    ("허브 칼라·스프링 주머니 함께 출력 r4.5: 주머니", "허브 칼라·스프링 주머니도 함께 출력한다. 주머니"),
    ("<td>v3 (포켓이 위)</td>", "<td>포켓이 위로</td>"),
    ("<td>10.1장 표(모두 서포트 없음)</td>", "<td>아래 ‘출력 공구’ 표(모두 서포트 없음)</td>"),
    ("<p>r4.1(검증자 기하 M1): 윗판이 프레임과 한 몸이라", "<p>윗판이 프레임과 한 몸이라"),
    ("조인다(v3 절차)", "조인다"),
    ("그래서 r4.3 글의 ‘빔 윗면 위 2.5 단 게이지’ 대신 캡스턴 게이지를", "그래서 캡스턴 게이지를"),
    ("<b>업스톱 시점 합격 기준 (r4.1, 종이 띠)</b>", "<b>업스톱 시점 합격 기준 (종이 띠)</b>"),
    ("; r4.4 고침 2b: r4.4 고침 2까지 방향이 반대였음", ""),
    ("패드(폼 6T + 펠트 1T, 6×12.2)를 패드 바 쐐기에 붙이고",
     "패드(PORON 5T(i124) + 펠트 1T, 6×12.2; 04 패드 바는 5T용)를 패드 바 쐐기에 붙이고"),
]
BUILD_DROP_SENT = [r"공구는 지금 모델\(<code>final</code>.*?로 만들었다\.\s*"]

OVR_CHECK = [
    ("<td>고른 변형 (홈 폭 / 구멍 Ø) → 건반 빔 너트 홈 폭·자가 잠김 구멍 Ø를 모델 key_body &#x27;nut trap&#x27;에 넣음 (지금 5.6 / Ø2.8)</td>",
     "<td>고른 변형 (홈 폭 / 구멍 Ø) → 건반 빔 너트 홈 폭·자가 잠김 구멍 Ø를 모델 key_body &#x27;nut trap&#x27;에 넣음 (지금 5.6 / Ø2.8). "
     "<b>A13(2026-10-30)부터 건반에는 너트가 없고 캡스턴이 빔의 Ø2.7에 바로 들어갑니다(물림 z23.8~27.5 = 3.7 mm).</b> C08a는 너트 홈이 비어 "
     "물림이 1.1 mm뿐이라 대신 첫 건반 빔에서 같은 토크(처음·20번 조정 뒤 3~40 N·mm)와 1회전 0.50 ± 0.05 mm를 봅니다. 헐거우면 M3 열압입 인서트(Ø4.2 구멍)로 바꿉니다.</td>"),
    ("r4.3 글의 ‘D·D#·E 3건반 조각’은 C# 자리가 없고 패드 바 두 칸에 걸쳐 S1으로 바꿨다(FE로 S1의 C# 자리 강성은 모듈과 0.7 % 차이, 17.1장).",
     "S1의 C# 자리 강성은 모듈과 0.7 % 차이다(FE, 17.1장)."),
    ("업스톱 패드는 설계가 6T인데, 구매 목록의 PORON은 5T다.",
     "업스톱 패드는 구매한 PORON 5T(i124)다(설계값 6T + 펠트 1T)."),
    ("강철은 캘리퍼로 골라 쓰거나 냉간 인발재를 산다. 패드 두께는 주문 전에 맞춘다.",
     "받은 강철을 캘리퍼로 재서 8.9~9.1인 것만 쓴다. <code>stl/print/04</code>의 패드 바는 5T용(쐐기를 1.0 두껍게, 패드 면 위치는 설계와 같음)이므로 그대로 뽑는다. 6T를 쓸 때만 <code>stl/print_extra</code>의 ‘대안_패드바_PORON6T용’을 뽑는다."),
    ("센서 바 오른쪽 턱(r4.5 회로 2차에서 되살림)의", "센서 바 오른쪽 턱의"),
    ("지금 모델(<code>final</code>, r4.5, metrics.json)", "모델(<code>final</code>, metrics.json)"),
    ("DESIGN 1e 고침 2b", "DESIGN 1e"),
    ("비틀림 스프링 (r4.5 미스미, r4.5 고침 가둠 홈)", "비틀림 스프링 (미스미, 가둠 홈)"),
    ("스프링 넣기 (r4.5 고침 가둠 홈)", "스프링 넣기 (가둠 홈)"),
    ("첫 모듈 정하중 (r4.5 고침; 하중 방향은 r4.5 고침 3)", "첫 모듈 정하중"),
    ("스프링 넣기 (조립, r4.5 고침 2 가둠 홈)", "스프링 넣기 (조립, 가둠 홈)"),
    ("17.1 단계 0 시험 키트 (r4.4, 남은 문제 7)", "17.1 단계 0 시험 키트"),
    ("<p>여기서는 아무도 물리 시험을 할 수 없다. 그래서 집에 있는 도구로", "<p>집에 있는 도구로"),
    ("r4.1에서 화음 자리가 492 N/mm로 굳었어도 0.45~0.6 N", "화음 자리가 492 N/mm여도 0.45~0.6 N"),
    ("홈을 못 내면 화음 자리가 196 N/mm로 돌아가 r4.0의 화음 들림(1.3~1.4 m/s 0.23)이 되살아난다.",
     "홈을 못 내면 화음 자리가 196 N/mm로 떨어져 1.3~1.4 m/s 화음에서 들림이 0.23으로 커진다."),
    ("<b>제어 기판 인터페이스(r4.3, 회로 쪽 확인 필요).</b>", "<b>제어 기판 인터페이스(회로 쪽 확인 필요).</b>"),
    ("지금 구매 목록의 Coms NA993은 몰드 치수가 공개되지 않아 확인이 안 된다. 몰드가 실측으로 확인되고 한계 안에 드는 CVILUX DH-20M50052로 바꾸기를 권한다(1d-3장, +27,784원). 받은 선은 캘리퍼·C13a 게이지·시험 19로 확인한다.",
     "가진 Coms NA993 계열 선(i022)은 몰드 치수가 공개되지 않았다. 받은 선을 캘리퍼·C13a 게이지·시험 19로 확인하고, 맞지 않으면 몰드 치수가 확인된 CVILUX DH-20M50052로 바꾼다(1d-3장)."),
    (" r3와 같은 수준이다.", ""),
    ("— r4.2는 잎 돌기가 립을 떠나면 바가 0.3 내려앉기 때문.", "— 잎 돌기가 립을 떠나면 바가 0.3 내려앉기 때문이다."),
    ("<b>축 놀음이 줄었다(r4.4 고침 2).</b>", "<b>레버 축 놀음.</b>"),
    ("F는 여전히 59 %만 앉는다", "F는 59 %만 앉는다"),
    ("F#는 55 %로 늘었지만 쉼 반력이", "F#는 55 %가 앉지만 쉼 반력이"),
    ("<b>화음 자리 여유 6.4 %(r4.4 단계 0 키트에서 드러남).</b>", "<b>화음 자리 여유 6.4 %.</b>"),
    ("의 ‘z_top 73.4 / 74.0’은 고침 2 전 z_top 72.80 기준이라 17.1장 표에서 고쳐 적었다.",
     "의 ‘z_top 73.4 / 74.0’은 예전 z_top 72.80 기준이므로 쓰지 않고, 위 값(73.45 / 74.05)을 쓴다."),
]
CHECK_DROP_SENT = [r"공구와 단계 0 키트는 r4\.4 고침 2 모델\(<code>MODEL_DIR=final</code>\)로 다시 만들었다\([^)]*\)\.\s*"]


def drop_sentences(h, patterns, misses, tag):
    for p in patterns:
        h, n = re.subn(p, "", h)
        if not n:
            misses.append(f"{tag} sentence: {p[:50]}")
    return h


# --------------------------------------------------------------------------------------------- 09 출력·조립
def _num(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s


def _dims(sz):
    return " × ".join(_num(v) for v in sz)


def print_plan(misses):
    man = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
    names = {}
    idx = os.path.join(HERE, "fin", "parts", "index.json")
    if os.path.exists(idx):
        for g in json.load(open(idx, encoding="utf-8")).get("groups", []):
            names[g["id"]] = g["name"]
    rows = collections.OrderedDict()
    for p in man["print"]:
        extra = bool(p.get("extra")) or p["folder"].startswith("@extra")
        r = rows.setdefault(p["folder"], dict(files=0, parts=0, mass=0.0, big=[], tall=[], top=None, extra=extra))
        r["files"] += 1
        r["parts"] += p["qty"]
        r["mass"] += p["qty"] * p["mass_g_solid_petg"]
        sx, sy, sz = p["size_mm"]
        nm = p.get("name_ko") or p["name"].replace("_", " ")
        if max(sx, sy) > 220.0 + 1e-6:
            r["big"].append((nm, p["qty"], (sx, sy, sz)))
        if sz > 220.0 + 1e-6:
            r["tall"].append((nm, p["qty"], (sx, sy, sz)))
        if r["top"] is None or max(p["size_mm"]) > max(r["top"][1]):
            r["top"] = (nm, p["size_mm"])

    def label(folder):
        if folder.startswith("@extra/"):
            nm = folder.split("/", 1)[1]
            return "선택 · " + (nm[3:] if nm.startswith("선택_") else nm).replace("_", " ")
        return names.get(folder[:2], folder.replace("_", " "))

    inst = [k for k, r in rows.items() if not r["extra"] and k[:2] in ("01", "02", "03", "04", "05", "07")]
    tool = [k for k, r in rows.items() if not r["extra"] and k[:2] in ("06", "08", "09")]
    extra = [k for k, r in rows.items() if r["extra"]]

    def tr(k):
        r = rows[k]
        big = "; ".join(f"{n} {_dims(s[:2])}" + (f" ×{q}" if q > 1 else "") for n, q, s in r["big"]) or "없음"
        return (f"<tr><td>{label(k)}</td><td class=\"num\">{r['files']}</td><td class=\"num\">{r['parts']}</td>"
                f"<td class=\"num\">{r['mass']:,.0f}</td><td>{r['top'][0]} {_dims(r['top'][1])}</td><td>{big}</td></tr>")

    tot = dict(files=sum(rows[k]["files"] for k in inst), parts=sum(rows[k]["parts"] for k in inst),
               mass=sum(rows[k]["mass"] for k in inst))
    ka = sum(rows[k]["mass"] for k in inst if k[:2] in ("01", "02", "03", "04"))
    body = sum(rows[k]["mass"] for k in inst if k[:2] == "05")
    ts = sum(rows[k]["mass"] for k in inst if k[:2] == "07")
    toolm = sum(rows[k]["mass"] for k in tool)
    bigs = [(n, q, s) for k in inst for n, q, s in rows[k]["big"]]
    talls = [(n, q, s) for k in inst for n, q, s in rows[k]["tall"]]
    tool_bigs = [(n, s) for k in tool for n, q, s in rows[k]["big"]]
    head = ('<div class="tbl"><table><thead><tr><th>폴더 (<code>stl/print/</code>)</th><th>파일</th><th>개수</th>'
            '<th>속 100 % g</th><th>가장 큰 부품 (베드 위 x × y × z, mm)</th><th>220 × 220 베드보다 큰 것</th></tr></thead><tbody>')
    html = [head] + [tr(k) for k in inst]
    html.append(f"<tr><td><b>악기 출력물 합계</b></td><td class=\"num\"><b>{tot['files']}</b></td><td class=\"num\"><b>{tot['parts']}</b></td>"
                f"<td class=\"num\"><b>{tot['mass']:,.0f}</b></td><td></td><td></td></tr>")
    html += [tr(k) for k in tool] + [tr(k) for k in extra]
    html.append("</tbody></table></div>")
    big_txt = ", ".join(f"{n} {_dims(s[:2])}" + (f"(×{q})" if q > 1 else "") for n, q, s in bigs)
    tall_txt = ", ".join(f"{n} {q}개(높이 {_num(s[2])})" for n, q, s in talls)
    tool_txt = ", ".join(f"{n} {_dims(s[:2])}" for n, s in tool_bigs)
    para = (f'<p>악기 출력물은 {tot["files"]}파일 {tot["parts"]}개이고, 속을 100 % 채운 PETG(1.27 g/cm³)로 계산하면 '
            f'{tot["mass"] / 1000:.2f} kg입니다(01~04 건반 액션 {ka / 1000:.2f} kg, 05 본체 {body / 1000:.2f} kg, '
            f'07 터치스크린 {ts / 1000:.2f} kg). 공구·지그(06 · 08 · 09)는 {toolm:,.0f} g입니다. 실제로는 벽 3줄 + 채움 25~40 %로 '
            '뽑으므로 이보다 훨씬 적게 들고, 정확한 g과 시간은 슬라이서 값을 봅니다. 서포트는 건반(01)만 켭니다 — Bambu Studio 트리(자동), '
            '빌드 플레이트에서만, 숨은 꼬리 밑에만 생김. 나머지는 끕니다(2026-10-29 A12: 프레임·레버·패드 바를 나눔, 2026-10-30 A13: 천장을 '
            '45° 지붕으로 바꿈, <a href="#build-a13">아래</a>; 07 화면 받침·점검창 덮개는 A14에서 같은 기준으로 바꿈, <a href="#build-a14">아래</a>). 필라멘트는 PETG 흰색 2 kg(i087·i088), 검정 5 kg(i089), 여유 1 kg(i090)을 준비했습니다.</p>')
    bed = ('<div class="note warn"><b>베드 크기.</b> ' + (f'220 × 220 베드에 들어가지 않는 악기 부품이 있어 256 × 256 베드(예: P2S)가 필요합니다: {big_txt}. ' if big_txt else '')
           + (f'세워서 뽑는 부품은 높이도 그만큼 필요합니다: {tall_txt}. ' if tall_txt else '')
           + '나머지 악기 부품은 220 × 220 베드에 들어갑니다.'
           + (f' 220 베드에서 대각선(45°)으로 놓아야 하는 공구·지그: {tool_txt}.' if tool_txt else '') + '</div>')
    if not bigs:
        misses.append("print plan: no part over 220 found (check manifest)")
    return "".join(html) + para + bed, tot


def cable_cuts():
    """Cut lengths from the circuit's cable list (hardware/pcb/netlist/cables.csv, column '자르는 길이 (mm)')."""
    import csv
    fp = os.path.join(ROOT, "hardware", "pcb", "netlist", "cables.csv")
    with open(fp, encoding="utf-8-sig") as f:
        return {r["W"]: r["자르는 길이 (mm)"] for r in csv.DictReader(f)}


def fill_cables(h, misses):
    """09 fuse-holder step: 12 AWG tail, W601 lead and W602a lengths follow cables.csv (never typed here)."""
    cuts = cable_cuts()
    w601, w602a = cuts.get("W601", ""), cuts.get("W602a", "")
    lead = re.search(r"리드 (\d+)", w601)
    tails = set(re.findall(r"꼬리 (\d+)", w601 + " " + w602a))
    run = re.search(r"꼬리 \d+ \+ (\d+)", w602a)
    if not (lead and run and len(tails) == 1):
        misses.append(f"build: cables.csv W601 '{w601}' / W602a '{w602a}' not in the expected '리드 N + 꼬리 T' / "
                      f"'꼬리 T + N' form - fuse-holder step left with placeholders")
        return h
    tail = int(tails.pop())
    return (h.replace("__TAIL__", str(tail)).replace("__OVL__", f"{tail - 10}~{tail}")
            .replace("__LEAD__", lead.group(1)).replace("__W602A__", run.group(1)))


def tab_build(pm, items, misses):
    raw = page_section(pm, "p-build").replace("\\</td><td>", "|")
    raw = apply_overrides(raw, OVR_BUILD, misses, "build")
    raw = drop_sentences(raw, BUILD_DROP_SENT, misses, "build")
    _, chunks, _ = split_h3(raw)
    ch = {t.split(" ")[0]: c for t, c in chunks}
    for want in ("출력", "조립", "건반", "조정"):
        if want not in ch:
            misses.append(f"build chunk missing: {want}")
            ch[want] = ""
    orient = re.search(r'<div class="tbl">.*?</div>', ch["출력"], re.S)
    orient = orient.group(0) if orient else ""
    module = ch["조립"].replace("<h3>조립 순서</h3>", '<h3 id="build-module">건반 액션 모듈 조립</h3>', 1)
    removal = re.sub(r"<h3>", '<h3 id="build-remove">', ch["건반"], count=1)
    adjust = re.sub(r"<h3>", '<h3 id="build-adjust">', ch["조정"], count=1)
    plan, tot = print_plan(misses)
    gap = [x for x in items["items"] if x.get("source") == "gap"]
    gap_txt = ", ".join(f'<a href="#parts-{x["id"]}">{x["id"]} {x["name"]}</a>' for x in gap)

    out = []
    out.append('<section class="page" id="p-build" hidden>\n<h2>출력·조립</h2>')
    out.append('<p class="lede">악기 한 대를 출력하고 조립하는 순서입니다. 숫자는 CAD 입체(<code>hardware/mechanical/cad</code>)와 '
               '건반 액션 모델에서 온 값입니다. 부품마다의 도면과 STL은 <a href="#partdwg">03 부품 도면·출력 파일</a>, 놓이는 자리는 '
               '<a href="#parts">06 부품·사용처</a>, 준비 상황은 <a href="#prep">07 준비 체크</a>에서 봅니다.</p>')
    out.append(DESIGN_NOTE)
    out.append('<h3 id="build-order">전체 순서</h3><ol class="flow">'
               '<li><b>단계 0 시험</b> — 단계 0 시편(<code>key-action-v4/printables/stage0</code>, 34종 36개)을 뽑아 패드 반발·노치·'
               '스프링·강철 접착을 먼저 시험합니다. 시험 목록과 합격 숫자는 <a href="#check">10 검증·남은 위험</a>에 있습니다.</li>'
               '<li><b>공구·지그 출력</b> — 06 출력 공구 4개, 09 기판 지그 2개 (10/16부터 합판이 없어 08 합판 지그는 없습니다).</li>'
               '<li><b>건반 액션 모듈 1개</b> — 01~04 폴더에서 모듈 하나 몫을 뽑아 조립하고, 첫 모듈 정하중 시험(시험 21)을 통과하면 '
               '나머지를 뽑습니다.</li>'
               '<li><b>본체 출력물</b> — 05 폴더. 배터리 틀은 받은 배터리로 크기·선이 나오는 면·높이를 확인한 뒤, 07 화면 받침은 '
               '화면 실물로 뒤 커넥터 방향을 확인한 뒤 뽑습니다.</li>'
               '<li><b>판 출력·잇기</b> — 옛 합판 10조각도 출력, 가운데 판은 3토막 잇기 (<a href="#build-ply">아래</a>).</li>'
               '<li><b>기판 납땜</b> — <a href="#circuit">01 회로도</a>의 기판·배선도대로 (<a href="#build-pcb">아래</a>).</li>'
               '<li><b>건반 액션 모듈 7개 + 끝 부속 조립</b> (<a href="#build-module">아래</a>).</li>'
               '<li><b>뒷부분 조립 → 책상에서 합치기 → 터치스크린 → 뚜껑</b> (<a href="#build-body">아래</a>).</li>'
               '<li><b>첫 전원</b> — XT60 색(빨강 전원, 파랑 스피커)과 퓨즈를 확인하고 켭니다. 전원 계통은 '
               '<a href="#circuit-pwr">01 회로도 · 전원</a>에 있습니다.</li></ol>')
    out.append('<h3 id="build-print">출력 계획</h3>' + plan)
    out.append('<p><b>채움.</b> 건반·레버·패드 바·가림판은 벽 3줄 + 채움 25~40 %면 충분합니다. 끝 부속 볼(cheek), 스피커 앞판, 스피커 '
               '통로 틀은 속이 꽉 찬 덩어리이므로 벽 3~4줄 + 채움 15~40 %로 뽑습니다. 보드 받침 기둥과 캡스턴 게이지(T2)·핀 '
               '게이지(T3)만 채움 100 %입니다. 부품마다의 방향·서포트·설정은 <a href="#partdwg">03 탭</a> 카드의 출력 메모에 있습니다.</p>')
    out.append('<div class="note"><b>패드 바는 5T용을 뽑습니다.</b> <code>stl/print/04</code>의 패드 바는 구매한 PORON 5T(i124)에 맞춰 '
               '쐐기를 1.0 두껍게 만든 것입니다(패드 면 위치는 설계와 같음). <code>stl/print_extra</code>의 ‘대안_패드바_PORON6T용’은 '
               '6T를 쓸 때만 뽑습니다.</div>')
    out.append(A12_HTML + A13_HTML + A14_HTML + A16_HTML)
    if orient:
        out.append('<h4 class="sub4">건반 액션 부품의 출력 방향 (설계서 15장 원문 — 서포트 칸은 위 A12~A14로 바뀜)</h4>' + tidy_html(orient))
    out.append(PLY_HTML)
    out.append(PCB_HTML.replace("__GAPNOTE__", ('<div class="note warn"><b>아직 준비처가 없는 물건:</b> ' + gap_txt + '. 센서 기판을 납땜하기 전에 구해야 합니다.</div>') if gap_txt else '<p>센서 기판 SB 띠(161.6 × 15.24, 7개)·끝 부속 EL·ER 띠·J702·J501·페달 센서 조각은 가진 양면 만능기판(i081)에서 자릅니다. SB 띠는 길이 161.6 mm라 162 mm보다 긴 방향이 있는 판에서 자릅니다.</p>'))
    out.append(tidy_html(module))
    out.append(MODULE_NOTE)
    out.append(fill_cables(BODY_HTML, misses) + DESK_HTML + TS_HTML + LID_HTML + SERVICE_HTML)
    out.append(tidy_html(removal))
    out.append(tidy_html(adjust))
    out.append('<p class="small muted">끝 부속(A0·A#0·B0, C8)의 치수는 <a href="#dwg10">02 설계도의 도면 10</a>에 있습니다.</p>')
    out.append("</section>")
    return "\n".join(out), tot


A12_HTML = """<h3 id="build-a12">서포트 없는 출력 구조 (2026-10-29)</h3>
<p>한 옥타브를 뽑아 보니 서포트를 떼기 어려워(프레임 윗판 밑 모듈마다 약 88 g이 핀 사이 좁은 칸 안에, 레버 강철 칸 속 떼는 지지대, 패드 바 자리 밑) 부품을 나눴습니다. 모든 면이 베드 위 벽이나 짧은 다리로 나오게 했습니다(다음 날 A13에서 Bambu Studio 기준으로 다시 확인해 남은 천장을 없앰, 아래). 기능 치수(건반·레버 자리, 패드 면, 봉 위치)는 그대로입니다.</p>
<ul class="flow">
<li><b>프레임 = 바닥틀 + 레버틀 + 가이드 탭</b> (<code>03_프레임</code>). 바닥틀(바닥·앞 레일·밸런스 레일·도브테일)은 바로 세워, 레버틀(윗판·패드 바 레일·핀 5장·봉 보스·뒷벽·뒤 선반)은 뒷벽 바깥면을 베드에 눕혀 뽑습니다. 레버틀은 윗판↔핀 이음이 한 층 안에 들어가 옛 바로 세운 출력(층간)보다 강합니다. 핀 발이 바닥틀 홈 둑 사이에 들어가고, 모듈은 바닥 밑 M3×10 4개로 조입니다(본드를 같이 써도 됨; 나사만이면 레버째 들어낼 수 있음). 끝 부속은 볼이 바닥틀에 남고 레버틀이 볼 안쪽 홈에 MS 폴리머로 붙습니다. 가이드 탭(키퍼 훅 포함, 백 52 · 흑 36)은 옆으로 눕혀 뽑아 바닥틀 자리에 순간접착제로 꽂습니다.</li>
<li><b>레버 = 캐리어 + 덮개</b> (<code>02_레버캐리어/레버덮개__88개</code>). 강철 칸의 +x 옆벽과 립을 덮개로 따로 뽑아, 강철을 MS 폴리머로 붙일 때 같이 덮어 붙입니다. 옛 칸 속 떼는 지지대와 사포질이 없어집니다.</li>
<li><b>패드 바 윗면 한 평면</b> — 앞부분을 1.0 두께로 내리고 잎 혀를 윗면 높이로 올림(윗판 밑에 혀 길 홈 0.6). 레버 손톱 턱과 ff에서 1.56(규칙 1.3 이상).</li>
<li><b>건반은 한 몸 그대로</b> — (A12의 떼는 빗·기판 보스 밑 기둥은 A13에서 뺐습니다: 건반 꼬리는 Bambu 트리 서포트, 기판 보스는 없어짐, 아래.)</li>
</ul>
<figure class="sheet"><img src="img/a12/before_frame_section.webp" alt="옛 한 몸 프레임의 x20 단면, 윗판 밑과 키퍼 훅 밑의 서포트 자리를 빨강으로 칠한 그림" loading="lazy" style="display:block;width:100%;height:auto"><figcaption>옛 한 몸 프레임을 바로 세워 뽑을 때 서포트가 들어가는 자리(x20 단면, 빨강). 윗판 밑 서포트가 핀 사이 좁은 칸 안에 갇혀 떼기 어려웠습니다.</figcaption></figure>
<div class="grid g3">
<figure class="sheet"><img src="img/a12/frame_split.webp" alt="바닥틀, 가이드 탭, 레버틀을 벌려 본 그림" loading="lazy" style="display:block;width:100%;height:auto"><figcaption>새 프레임: 바닥틀(회색) + 가이드 탭 12(주황) + 레버틀(파랑).</figcaption></figure>
<figure class="sheet"><img src="img/a12/cage_print.webp" alt="레버틀을 뒷벽 바깥면이 베드에 닿게 눕힌 출력 자세" loading="lazy" style="display:block;width:100%;height:auto"><figcaption>레버틀 출력 자세: 뒷벽이 베드, 핀·윗판·선반이 모두 세워진 벽.</figcaption></figure>
<figure class="sheet"><img src="img/a12/lever_split.webp" alt="레버 캐리어 몸통, 강철 블록, 덮개를 벌려 본 그림" loading="lazy" style="display:block;width:100%;height:auto"><figcaption>레버: 캐리어(연두) + 강철 + 덮개(진초록). 강철을 붙일 때 덮개도 함께.</figcaption></figure>
</div>
<p class="small muted">CAD: <code>hardware/mechanical/cad/README.md</code> 부록 A12, <code>keyaction.frame_split</code> · <code>lever_cover_solid</code> · <code>padbar_a12_poly</code>. 확인: 쉼 자세 겹침 0, 레버 쉼~ff ↔ 레버틀 0.055(옛 프레임과 같은 축 놀음), 건반 ↔ 바닥틀 1.41 이상, 건반 ↔ 가이드 탭 0.55.</p>
"""


A13_HTML = """<h3 id="build-a13">Bambu Studio 기준 서포트 정리 (2026-10-30, A13)</h3>
<p>A12의 떼는 빗·기둥은 STL에 넣은 받침이라, Bambu Studio에서 서포트를 켜면 그와 상관없이 <b>바닥이 없는 천장마다 트리 서포트</b>가 생깁니다(바닥틀 가운데 작은 구멍·기판 보스 밑 포함). A13은 받침을 넣는 대신 <b>천장 자체를 없앴습니다</b>: 출력 자세에서 아래를 보는 면은 45° 지붕(리본 길만 40°)이거나 베드 위입니다. 확인은 <code>check_support.py</code> — STL을 0.2 mm 층으로 잘라 층마다 아래층보다 Bambu 기본 서포트 문턱 30°(0.35 mm)보다 더 나간 곳을 찾습니다(한두 층·폭 2 mm 이하는 그냥 뽑히는 작은 다리로 뺌).</p>
<ul class="flow">
<li><b>바닥틀</b> — 기판 구멍(밑에서 넣던 자리, 매단 보스 4개의 밑면이 천장)을 바닥으로 막고 <b>기판은 기둥 4개 위에 위에서</b> M3×6 2개 + 위치 핀 2개로 올렸습니다(<a href="#build-a16">A16</a>에서 다시 바뀜: 기판은 80 × 120 통째로 바닥에 눕고 밸런스 레일은 따로 출력). 밸런스 레일 밑 리본 길은 40° 뾰족 지붕(A16에서 없어짐), 암 도브테일 홈 위는 45° 지붕, 끝 부속 볼의 잭·선 홈은 45°, 너트 홈은 90° V 지붕.</li>
<li><b>건반</b> — 앞 멈춤 바닥과 밸런스 블록 위 칸 밑에 45° V 채움(건반 안쪽, 백건 +0.8 g), 흑건 윗면 뒤끝 턱은 45° 비탈. 캡스턴 너트는 <b>A15</b>에서 되살림: 옆 홈(맞변 5.6 × 2.8, 닫힌 끝은 축에서 3.2)의 천장을 구멍 없는 0.4 막으로 두어 홈 위 첫 층이 양쪽에 붙은 5.6 다리 — 서포트 없음, 캡스턴 끝이 처음 들어갈 때 막을 뚫음. <b>숨은 꼬리만 남김</b>: 위에 레버가 0.7 위라 채울 수 없어 바닥에서 떠 있으니 <b>건반만 서포트 켬 — 트리(자동) · 빌드 플레이트에서만</b>. 꼬리 밑 바깥 면 하나라 한 덩어리로 떨어집니다(03 탭 3D에서 주황 면). 키퍼 가로대 8.6은 위에 키퍼 펠트가 있어 지붕을 올릴 수 없는 양쪽 붙은 다리 — Bambu 기본 ‘최대 브리지 길이 10 mm’ 안이라 서포트가 생기지 않습니다.</li>
<li><b>레버 캐리어</b> — 스프링 칸 지붕에 45° 원뿔(Ø6.7 → Ø3.9). <b>본체</b> — 스피커 앞판 인서트·그릴 구멍 끝 45° 뾰족, 허브 선반 머리 자리 꼭지가 윗면으로 트임, 뚜껑 이음 레일 인서트 구멍은 기둥 위 뾰족·레일만인 곳 관통, 방진 브래킷 2는 옆으로 눕혀(핀이 층과 나란해 더 강함), CU 화면 뚜껑은 갈비 칸(38 × 48 천장)을 한 덩어리 판으로.</li>
<li><b>07 화면 받침·점검창 덮개</b> — A13 때는 서포트를 켜야 했던 두 파일(크래들 약 30 cm², 덮개 약 3.7 cm²)도 <a href="#build-a14">A14</a>에서 서포트 없이 바꿨습니다.</li>
</ul>
<p class="small muted">CAD: <code>hardware/mechanical/cad/README.md</code> 부록 A13, <code>keyaction.a13_board</code> · <code>a13_lanes</code> · <code>key_a13_adds</code> · <code>lever_a13_cut</code>, <code>check_support.py</code>. 확인: check_body · check_electronics · check_interf 통과, 동작 스윕은 A12와 같음(레버 ↔ 레버틀 0.055, 건반 ↔ 바닥틀 1.41 이상, ↔ 가이드 탭 0.55).</p>
"""


A14_HTML = """<h3 id="build-a14">07 화면 받침·점검창 덮개도 서포트 0 (2026-10-30, A14)</h3>
<p>같은 Bambu Studio 기준(<code>check_support.py</code>)입니다. 화면 받침은 지금처럼 <b>윗변을 베드에 세워</b>(귀가 위, 높이 119.76) 뽑습니다. 이 자세에서는 받침 아래쪽(유리 아래 끝 쪽)을 보는 면이 모두 천장이라, 그 면들을 45°로 바꾸거나 따로 뽑았습니다.</p>
<ul class="flow">
<li><b>유리 턱 띠 (새 출력물 2개)</b> — 유리가 얹히는 아래 벽 앞 턱(166.7 × 9)은 이 자세에서 맨 위 천장이라 떼어 냈습니다. <code>화면받침_유리턱띠_왼쪽</code>(131.25) · <code>_오른쪽</code>(17.30)을 유리 얹힘 면을 베드에 눕혀 뽑고(높이 2.5), 화면을 나사로 고정한 뒤 띠를 유리 아래 끝에 대고 받침 아래 벽 앞면에 세메다인 슈퍼X(<a href="#parts-i071">i071</a>)로 붙입니다(24시간). 두 띠 사이가 화면 아래 돌기 홈(xr48~66)입니다.</li>
<li><b>받침</b> — 남은 아래 벽 밑, 가로 갈비 2줄 밑(u24 갈비는 다리 축 길에서 멀어지게 기울임), 창 둘레 갈비 아래 변, 보스 4개와 옆벽 채움 밑, 리본 누름 패드 밑에 45° 받침을 붙였습니다.</li>
<li><b>점검창</b> — 곧은 위 변은 29.5 다리(Bambu 기본 ‘최대 브리지 길이’ 10 mm를 넘음)라, 창 위에 45° 박공을 올려 맨 위를 폭 9 다리로 만들었습니다. 창 둘레 갈비도 박공을 따라 돌고, 박공 위 가운데는 45°로 눕혔습니다. ZIF·MX1.25·리본 접힘 자리는 그대로 다 보입니다.</li>
<li><b>점검창 덮개</b> — 창과 같은 육각입니다. 턱 밑의 1.7 처마는 45° 모따기로 바꿔 창 뒤 모서리에 얹힙니다. 볼록 자리 천장(13.7 다리) 위에는 45° 지붕을 올려 맨 위를 9 × 9 다리로 만들었습니다(바깥 w18.75, 접은 상태·22~90° 스윕에서 닿는 곳 없음). 걸쇠 보 2개는 창 옆벽 쪽(u48~54)으로 옮겼고, 끼움 0.2 · 변형률 1.6 %는 그대로입니다.</li>
</ul>
<p>이제 <b>서포트를 켜는 출력물은 건반(01)뿐</b>입니다. 07 폴더는 모두 서포트를 끄고 뽑습니다. 남은 천장은 위의 9 mm 다리 세 곳(받침 박공 맨 위, 덮개 지붕 맨 위, 덮개 걸쇠 보 위 홈 7 × 2.3)과 2 mm 안의 구멍 꼭대기뿐입니다.</p>
<p class="small muted">CAD: <code>hardware/mechanical/cad/README.md</code> 부록 A14, <code>body.cradle_local</code> · <code>ledge_local</code> · <code>cover_local</code> · <code>win_pts</code>, <code>check_support.py</code>(BRIDGE_OK에 07 다리 세 곳). 확인: check_body 339 · check_electronics · check_interf 통과.</p>
"""

A16_HTML = """<h3 id="build-a16">제어 기판 80 × 120 통째로 — 바닥에 눕히고 밸런스 레일을 따로 (2026-10-31, A16)</h3>
<p>사용자: “80 120 으로 설계를 다시 만들어줄 수 있어? … 기판을 바닥으로 내려도 돼”. 만능기판을 70 × 50으로 자르지 않습니다. 모듈 바닥에는 80 mm 깊이의 빈 곳이 없어서(센서 바 y59~77.5, 검은 건반 탭 받침 ~y93, 밸런스 레일 y132.3~144.5, 레버틀 핀 발 y152~), 판을 탭 받침 바로 뒤 <b>바닥 x22.25~142.25 × y93.3~173.3</b>에 눕히고 밸런스 레일 밑을 지나게 했습니다.</p>
<ul class="flow">
<li><b>밸런스 레일</b> — 바닥틀에서 떼어 <b>따로 출력</b>(03 <code>밸런스레일</code> 7개, 밑면 z8.6 = 판 윗면, 바로 세워 서포트 없음). 윗면·봉 받침 판·밸런스 핀 구멍·옆 위치는 그대로라 건반 동작은 바뀌지 않습니다. 양 끝벽 사이(틈 0.15)와 끝 받침 두 곳에 놓고, 양 끝 깊은 구멍(Ø6.2)으로 예전 기판 나사 M3×6(<a href="#parts-i059">i059</a>) 2개를 받침에 조입니다. 레일 밑면이 판의 빈 띠를 눌러 판도 잡습니다.</li>
<li><b>바닥틀</b> — 판 받침 리브 z5~7.0(가장자리 둘레 + 레일 밑 띠; 앞은 리본 틈 x59.5~81.5, 레일 밑은 배선 틈 x92~114)와 둘레 턱(틈 0.3). 판 밑 2.0은 리본 가닥 배선이 엇갈리는 두 겹(1.8)이 지나가는 높이입니다. 판에는 <b>나사·구멍·자르기가 없습니다</b>. 옛 기판 기둥과 레일 밑 리본 길은 없어졌습니다.</li>
<li><b>레버틀</b> — 핀 2·4번은 판 위(y174.9 앞)에서 밑변 z9.5, F|F# 핀은 제로·USB 플러그 위로 z18부터. 레버틀 나사 2개(핀 2·4번 발)는 y186으로 옮겼습니다.</li>
<li><b>전자부</b> — RP2040-Zero는 핀 헤더 몰드(2.5)를 그대로 둔 채 뒤쪽 칸, USB-C 플러그(y170.5~195.5)는 지금 뒷벽 구멍으로 곧게 나갑니다(선 길이 여유 87 mm 이상, 산 선 그대로). 먹스·리본 J301은 레일 앞 칸. 판 밑으로 나온 다리 끝은 1.0 mm 이하로 자릅니다. 회로 BRD-01·BRD-08 △33(넷은 그대로).</li>
<li><b>판 수</b> — 7장 = 가진 BE163 4장(<a href="#parts-u06">u06</a>) + 새로 사는 8 × 12 양면 3장, 페달 보드 1장도 새 판에서(<a href="#parts-i228">i228</a>, 4장 14,140원 사비). 기판 지그는 페달 보드용 P-PED만 남습니다.</li>
</ul>
<p class="small muted">CAD: <code>hardware/mechanical/cad/README.md</code> 부록 A16, <code>keyaction.a16_rail</code> · <code>a16_bed</code> · <code>a16_cage_cuts</code>, <code>spec/electronics_modules.json</code> mb_board. 확인: check_interf · check_electronics 199 · check_body 339 · check_support 0 · check_perfboard_jigs 통과, 전자부 ↔ 건반 동작부 겹침 0.</p>
"""

PLY_HTML = """<h3 id="build-ply">판 (2026-10-16부터 모두 출력, 합판 없음)</h3>
<p>합판 가공비가 비싸 남은 오꾸메 10조각도 PETG로 출력합니다(A안). 모양·두께 11.5·자리는 같고, 환기 Ø8 구멍·뒤판 윗모서리 자석 자리·나사 안내 구멍(8호 Ø3.4 · 허브 선반 Ø2.5, 끝은 45° 원뿔)이 출력에 들어 있어 <b>드릴·톱질이 없습니다.</b> 판 출력은 약 2.0 kg · 49시간이라 검정 PETG를 4 kg 더 삽니다(<a href="#parts-i227">i227</a>). 이음은 모두 MS 폴리머(<a href="#parts-i071">i071</a>, 3개)로 붙입니다(PETG에는 목공본드가 붙지 않음). 조각마다의 치수 도면은 <a href="#partdwg">03 탭</a> 05 폴더 카드에 있습니다.</p>
<ul class="flow">
<li><b>스피커 바깥 옆판 L·R · 뒤판 · 윗판 · 아랫판 L·R</b> — 05 폴더 <code>스피커바깥옆판_L·R</code>, <code>스피커뒤판_L·R</code>, <code>스피커윗판_L·R</code>, <code>스피커아랫판_L·R</code>. 밀폐 상자 벽이라 벽 5줄 이상 + 윗·아랫면 5층 + 채움 40 % 이상으로 뽑고, 두드려 통통 울리는 판만 채움 60~100 %로 다시 뽑습니다. 아랫판 밑면에는 고무발 나사 안내 구멍 4곳이 있습니다.</li>
<li><b>가운데 유닛 아랫판 (679) · 뒤판 (702)</b> — 베드(256)보다 길어 x494 · x720에서 반턱 이음(겹침 16, 두께의 반씩)으로 3토막씩 뽑습니다(<code>가운데아랫판_1~3</code>, <code>가운데뒤판_1~3</code>, 가장 긴 토막 250). 가운데 토막은 이음 혀가 베드 쪽이 되게, 양쪽 토막은 뒤집어 뽑습니다(서포트 없음). 반턱끼리 MS 폴리머로 겹쳐 붙이고 곧은 자에 모서리를 맞춰 마스킹테이프로 눌러 굳힌 뒤 길이(679 · 702)를 잽니다. 아랫판 이음은 뚜껑 이음 기둥 곁, 뒤판 왼쪽 이음은 창 아래 띠(뒤판 출력물이 위에 붙음), 오른쪽 이음은 이음 레일 2의 끝면이 덮습니다.</li>
</ul>
<div class="note warn"><b>고무발 나사는 직결피스 8호 13 mm 이하(<a href="#parts-i053">i053</a>)를 씁니다.</b> 출력 아랫판의 안내 구멍(막힌 구멍)에 바로 조이고, 스피커 아랫판은 밀폐 상자 바닥이므로 나사 구멍마다 MS 폴리머를 한 방울 넣습니다. 넓은 판은 출력 중 모서리가 뜨기 쉬우니 문을 닫고 베드 70~80 °C로, 다 식은 뒤 떼어 냅니다.</div>"""

PCB_HTML = """<h3 id="build-pcb">기판 자르기·납땜</h3>
<p>제어 기판 MB 7장은 80 × 120 양면 만능기판을 <b>통째로</b> 씁니다(<a href="#build-a16">A16</a>) — 가진 Coms BE163 4장(<a href="#parts-u06">u06</a>) + 새로 사는 8 × 12 양면 3장(<a href="#parts-i228">i228</a>). 자르지도 뚫지도 않고, 납땜한 뒤 바닥틀 자리에 내려놓으면 밸런스 레일이 위에서 눌러 잡습니다. 판 밑으로 나온 다리 끝은 1.0 mm 이하로 자릅니다. 페달 기판 PED 1장만 새 판 1장에서 09 기판 지그 P-PED로 70 × 50을 자릅니다: 지그 밑의 Ø0.9 핀 6개를 시트 구멍에 꽂고, 네 옆면을 따라 커터칼로 긋고 꺾은 뒤, 지그 구멍으로 나사 Ø3.2 두 개와 위치 핀 Ø3.0 두 개 자리를 뚫습니다. 부품 배치와 배선은 <a href="#circuit">01 회로도</a>의 SCH·BRD 도면과 배선표대로 합니다.</p>
__GAPNOTE__"""

MODULE_NOTE = """<div class="note"><b>모듈 조립에서 더 지킬 것.</b> 모듈끼리는 도브테일(뿌리 6 → 끝 9, 깊이 4, 암은 밑이 열림)로 위에서 내려 끼웁니다. 뒤 꼬리는 높이 14라 빼려면 약 14 mm 들어야 하고, 모듈은 위로만 빠지므로 앞으로 밀지 않습니다. 모듈 밑 바닥 EVA는 한 장 그대로 붙이고 레버틀 나사 머리 자리 Ø7 4곳(x41.66·123.93 y186, x29·143 y203)만 오려 냅니다. 강철 블록은 칸 길이 40.0에 딱 맞으므로 40 −0.1/−0.3으로 자르고 두께 8.9~9.1만 씁니다. 캐리어 칸 속의 떼는 지지대는 먼저 떼어 냅니다.</div>"""

BODY_HTML = """<h3 id="build-body">뒷부분 조립 (책상 밖에서)</h3>
<p>뒷부분은 스피커 상자 L·R과 가운데 유닛입니다. 책상 밖에서 따로 만든 뒤 건반 뒤에 놓습니다. 도면은 <a href="#rd1">D01 평면</a>, <a href="#rd2">D02 스피커 단면</a>, <a href="#rd3">D03 가운데 유닛 단면</a>, <a href="#rd4">D04 뒷면</a>, 안쪽은 <a href="#dwg-i02">I02 가운데 유닛 내부 상세</a>입니다.</p>
<ol class="flow">
<li><b>고무발</b> — 스피커 아랫판마다 4개, 가운데 아랫판에 6개를 답니다(<a href="#parts-i039">i039</a> 28 × 5, 직결피스 8호 13 mm <a href="#parts-i053">i053</a>). 발은 모두 통로 뒤(y ≥ 248)에 있습니다. 스피커 아랫판은 나사 구멍마다 MS 폴리머를 한 방울 넣습니다.</li>
<li><b>스피커 상자 L·R</b><ul>
<li>출력 안쪽 옆판의 인서트 구멍 Ø5.6 × 6.5 두 곳에 M4 열 인서트(<a href="#parts-i211">i211</a>, 바깥 Ø6 × 길이 6)를 인두로 이음면까지 곧게 넣습니다. 구멍 바닥까지 밀지 않습니다.</li>
<li>바깥 옆판·아랫판·뒤판·윗판·안쪽 옆판(모두 출력)을 MS 폴리머(<a href="#parts-i071">i071</a>)로 잇습니다(PETG에는 목공본드가 붙지 않음). 출력 통로 틀을 옆판 사이 앞에 넣고 세움벽 밑을 아랫판 앞 모서리(y241)에 붙입니다.</li>
<li>출력 앞판(40°)을 앞벽·턱 위에 MS 폴리머로 붙이고 둘레를 밀봉한 뒤, 새는 곳이 없는지 확인합니다.</li>
<li>앞판 유닛 자리에 M4 인서트 4개를 인두로 면까지 넣습니다. 통로 지붕 밑(z27)에 핀 소켓 블록(L x2.5 · R x1219.5, y230)과 케이블 집게 3개를 붙이고, 바깥 옆판 홈에 통로 옆 마개를 끼웁니다.</li>
<li>스피커 꼬리선(XT60 암 + 16 AWG 10 cm, <a href="#parts-i225">i225</a>)에 파란 수축 튜브와 ‘SPK’ 표시를 하고, 상자 안에서 짧은 선과 납땜 + 수축 튜브로 이어 유닛 단자로 보냅니다. 꼬리는 안쪽 옆판 Ø6 구멍으로 약 55 mm 빼고 본드로 밀봉합니다.</li>
<li>Ø94 구멍으로 흡음솜(<a href="#parts-i052">i052</a>)을 상자 전체에 느슨하게 넣습니다. 유닛 뒤 10 mm와 폴 벤트 축 방향 10 mm는 비웁니다.</li>
<li>유닛(<a href="#parts-i051">i051</a>)은 가스켓 3T + M4 × 12 네 개로 앞판 인서트에 답니다(더 긴 나사는 쓰지 않습니다). 그릴은 직결피스 8호 19 mm 네 개(<a href="#parts-i055">i055</a>)로 답니다(25 mm는 쓰지 않습니다).</li></ul></li>
<li><b>가운데 유닛</b><ul>
<li>3토막씩 이은 아랫판 + 뒤판과 출력 끝벽 L·R을 MS 폴리머로 붙입니다. 끝벽 Ø8 구멍에는 고무 슬리브(연료 호스 OD8 × ID4.5, <a href="#parts-i216">i216</a>)를 꽉 끼웁니다.</li>
<li>뒤판 창에 뒤판 출력물을 끼우고 바닥 탭 나사 2개를 접시머리 직결피스 8호 13 mm(<a href="#parts-i219">i219</a>)로 (431.5, 321) · (446.5, 321)에 조입니다. KCD1 단자와 J501 받침 사이로 드라이버가 곧게 닿습니다. J501 기판은 그 뒤 받침 위에 MS 폴리머로 붙입니다.</li>
<li>이음 레일·기둥 2개는 M3 인서트(<a href="#parts-i213">i213</a>)를 먼저 인두로 넣은 뒤 뒤판 안면과 아랫판에 MS 폴리머로 붙입니다.</li>
<li>보드는 받침 기둥에 먼저 나사(M3 × 6, Pi는 M2.5 × 6)로 단 뒤 기둥 밑을 아랫판에 MS 폴리머로 붙입니다(관통 구멍은 막지 않게 고리 모양으로). PED 보드는 90° 돌려 x426.5~476.5에 둡니다.</li>
<li>배터리 틀은 접시머리 8호 13 mm 네 개(왼쪽 귀 2 + 앞 낮은 덩어리의 Ø9 구멍 2)로 조입니다. 허브는 뒤판에 붙여 바닥에 놓고, 허브 선반은 받침 2개를 뒤판에 M3 × 12 트러스 태핑 피스(<a href="#parts-i220">i220</a>)로 조입니다. 드라이버는 선반 윗면의 머리 길 홈을 따라 앞에서 넣습니다. 앰프는 선반 받침에 M3 × 6으로 답니다. 이 나사들은 모두 곧은 드라이버(Ø6 × 80)로 닿습니다.</li>
<li>XT60 집게 2개를 끝벽 안쪽 Ø19 구멍에 맞춰 MS 폴리머로 붙입니다(판 구멍과 끝벽 구멍이 같은 축이고 홈이 세워짐). 끝벽 L 안면에 케이블 집게 2개(y262~282 · 286~306, z48~58)를 붙입니다. 뚜껑 자석 12개(<a href="#parts-i099">i099</a>)는 극이 서로 당기게 붙입니다.</li>
<li>전원선·5.1 V선·스피커선을 <a href="#circuit-brd-04">BRD-04 가운데 유닛 배선도</a>대로 놓습니다. 스피커선 L은 끝벽 집게에 끼우고 집게 E1 앞에서 z56.5로 올려 XT60 집게 판 위로 y244까지 가져와 XT60 수로 끝냅니다. 앰프 선 끝 XT60 수는 16 AWG 10 cm 선(<a href="#parts-i224">i224</a>)을 앰프 선에 납땜 + 수축 튜브로 잇고, 파란 수축 튜브 + ‘SPK’를 붙입니다.</li>
<li>퓨즈 홀더(ATC/ATO, <a href="#parts-u04">u04</a>)에 5 A ATO 퓨즈(<a href="#parts-u05">u05</a>)를 넣고 덮개를 닫습니다. 홀더가 오면 12 AWG 꼬리가 __TAIL__ mm보다 긴지 먼저 확인합니다. 두 꼬리를 홀더 끝에서 __TAIL__ mm로 자르고(R15 굽힘 약 23.5 + 이음 자리 12), 16 AWG와 10 mm 겹쳐 꼬아 납땜한 뒤 수축 튜브를 씌웁니다. 겹침은 홀더 끝에서 __OVL__ mm, 굽힘이 끝난 뒤에 옵니다(12 AWG는 R15보다 좁게 꺾지 않습니다). −x 꼬리는 하네스 XT60 수 리드(W601, __LEAD__ mm)로, +x 꼬리는 16 AWG __W602A__ mm(W602a)로 KCD1 아래 단자까지 갑니다. 틀 나사 4개를 조인 뒤 홀더를 덮개가 +y(배터리 쪽)로 가게 눕혀 배터리 틀 퓨즈 선반의 꼭지 받침 2개에 눌러 끼웁니다.</li>
<li>마지막에 배터리(<a href="#parts-u01">u01</a>)를 틀에 넣고 벨크로 끈(<a href="#parts-i221">i221</a>)으로 감은 뒤, 선 두 개를 +x 끝에서 위로 꺾어 XT60 짝과 DC 충전 커넥터를 배터리 윗면에 눕힙니다.</li></ul></li>
</ol>
<div class="note warn"><b>XT60 색을 지킵니다.</b> 전원 XT60(배터리 선, 하네스, 시험 전원 어댑터)은 빨간 수축 튜브, 스피커 XT60은 파란 수축 튜브 + ‘SPK’입니다. <b>배터리나 시험 전원을 스피커 XT60(파랑)에 꽂지 않습니다.</b> 12.8 V 직류가 앰프 출력이나 스피커 코일에 걸립니다. 그래서 하네스 쪽 XT60 수 선은 퓨즈 홀더 −x 끝에서 XT60 수 뒤끝까지 이은 전체 길이를 68 mm 이하로 만듭니다(왼쪽 스피커 XT60 암까지 직선 94.4 mm). 자르는 길이는 <a href="#circuit-pwr">01 회로도 · 전원</a>의 W601에 있습니다.</div>"""

DESK_HTML = """<h3 id="build-desk">책상에서 합치기</h3>
<ol class="flow">
<li><b>건반 쪽</b> — 모듈과 끝 부속을 도브테일로 잇고, 볼 뒤 M3 자리에 방진 브래킷 BRK2를 답니다(그로밋 2 + M3 × 20 두 개, <a href="#parts-i112">i112</a>; 스피커를 올리기 전에 조임). 모듈 USB-C 선을 꽂아 통로 자리(y212~241) 책상 위에 눕힙니다. 스피커 밑에 올 O1·O7 선과 EL·ER 리드·JST-XH는 이때 통로 안쪽으로 가지런히 둡니다.</li>
<li><b>가운데 유닛 놓기</b> — 모듈 뒤 2 mm 틈(y212~214)을 두고 놓습니다. 앞벽이 없어 앞 공간(y214~241)이 선 위로 옵니다.</li>
<li><b>스피커 놓기</b> — EVA 3T 띠 2줄(<a href="#parts-i061">i061</a>)을 스피커 안쪽 옆판에 미리 붙입니다. 스피커를 브래킷 핀보다 약 10 mm 위, 제자리보다 약 18 mm 바깥에 듭니다. 꼬리의 XT60 암을 입구(가운데 쪽)부터 끝벽 Ø19 구멍(L z41 · R z46.5)에 세워서(넓은 면이 위아래) 넣고, 뒤끝을 드라이버 손잡이로 밀어 끝벽(11.5)과 집게 판(3)을 지나게 합니다. 가운데 안에서 잡아 집게 홈에 곧게 당겨 넣고 위에서 눌러 끼웁니다. 스피커를 안쪽으로 밀어 EVA가 끝벽에 닿게 하면서 남는 꼬리(여유 약 35 mm)를 끝벽 구멍 안에 느슨하게 감아 넣고, 핀에 곧게 내려 끼웁니다(L 둥근 소켓, R x 방향 긴 소켓; 핀 끝과 소켓 바닥 사이 2 mm). 가운데 안에서 M4 나비나사를 2개씩 조입니다(머리는 고무 슬리브에만 닿음).</li>
<li><b>스피커 XT60 꽂기</b> — 집게 홈에는 축 방향 멈춤이 없어, 홈 안의 암에 수를 대고 밀면 암이 터널로 밀려 들어갑니다. 암을 홈 입구로 가운데 쪽에 당겨 꺼내고(꼬리 여유 약 35 mm), 앰프 선 XT60 수(파랑 + SPK)를 손으로 끝까지 꽂은 뒤, 짝을 다시 가져와 암 앞면을 홈 입구에 맞춰 위에서 걸림 턱 밑으로 눌러 끼웁니다(수는 입구 밖으로 나옴).</li>
<li><b>선 정리</b> — 뚜껑을 모두 뗀 채 앞 공간에서 모듈 USB 선을 묶음(y237.5, 4층)으로 모아 허브 포트에 꽂습니다: 포트 2 PED, 3 O3, 4 O1, 5 O2, 6 O4, 7 O5, 8 O6, 9 O7(짧은 O5·O6은 묶음 위 앞쪽 줄). 허브의 충전 전용 포트가 2~9번이면 그 보드를 1번(또는 0번)으로 옮깁니다(<a href="#circuit-sys">01 회로도 · 시스템</a>의 포트 옮김 표). 헤드폰 선 W701/W702는 왼쪽 볼 홈에서 통로 바닥을 따라 동글·J702로 갑니다.</li>
</ol>"""

TS_HTML = """<h3 id="build-ts">터치스크린</h3>
<p>화면(<a href="#parts-i202">i202</a>)은 25°로 서고, 접으면 화면 뚜껑 위에 눕습니다. 도면은 <a href="#rd5">D05 터치스크린</a>과 <a href="#dwg-e07">E07 접은 상태</a>입니다.</p>
<ol class="flow">
<li><b>화면 → 받침 (책상 밖에서)</b><ul>
<li>화면 ZIF(22핀, 입구 +x)에 FFC B형(<a href="#parts-i203">i203</a>)을 3.5 mm 꽂고 잠급니다. 입구에서 +x로 4 mm 뒤 45°로 말아 접습니다(R3, 날카롭게 꺾지 않음).</li>
<li>리본 길 xr27.25~38.95(x638.25~649.95)를 따라 아래로 보내고, 누름 패드 자리(u8~16)에 캡톤 테이프(<a href="#parts-i026">i026</a>)를 붙입니다. MX1.25 전원선은 그 옆 xr40.45~43.45로 보냅니다.</li>
<li>둘을 아래 트인 홈으로 빼고 화면을 받침에 넣습니다(굵은 테두리 9.65가 아래, 커넥터 창이 오른쪽). 뒤에서 M2.5 × 6 네 개로 조입니다(구멍 깊이를 먼저 잽니다).</li>
<li>유리 턱 띠 2개(07 폴더 <code>화면받침_유리턱띠_왼쪽·오른쪽</code>, A14)를 유리 아래 끝에 대고, 받침을 책상에 세워 띠 바닥을 받침 바닥면에 맞춘 채 받침 아래 벽 앞면(w8)·옆벽 쪽 끝에 세메다인 슈퍼X(<a href="#parts-i071">i071</a>)를 얇게 발라 붙입니다(24시간). 두 띠 사이가 화면 아래 돌기 홈입니다.</li>
<li>점검창 덮개를 걸쇠가 걸리게 눌러 끼웁니다.</li>
<li>받침다리를 다리 걸이 볼 사이에 넣고 M3 × 20을 −x에서(육각 L렌치 2.0) 먼 볼에 탭으로 조입니다. 머리가 볼에 닿을 때까지 돌린 뒤 약 1/4바퀴 풀어 다리가 제 무게로 돌게 합니다. 조이면 볼이 다리를 물어 다리를 펼 수 없습니다.</li></ul></li>
<li><b>받침 → 화면 뚜껑</b><ul>
<li>리본과 전원선을 뚜껑의 22 × 6 구멍(x635.35~657.35)으로 위에서 아래로 넣습니다(3핀 이음도 지나감).</li>
<li>뚜껑 밑에서 리본을 밑면에 붙여 +y로 보내고, 클립 덩어리 밑에 리본을 댄 채 전원선 2가닥을 클립 윗면 홈(x652.6~656.1)에 넣고 클립 핀 2개를 Ø3.1 구멍에 눌러 끼웁니다. 리본은 y270.5에서 45° 접어 −x로 x583까지 보냅니다.</li>
<li>받침 귀 2개를 귀 홈에 넣고 M3 × 20을 바깥 가까운 볼에서(왼쪽 −x, 오른쪽 +x) 넣어 먼 볼 Ø2.5에 탭으로 조입니다(물림 7.6). 머리가 볼에 닿을 때까지 돌린 뒤 약 1/4바퀴 풉니다. 귀와 볼 사이 틈은 0.2씩뿐이라 조이면 화면이 25°로 돌아가지 않습니다.</li></ul></li>
<li><b>받침다리 펴기·접기</b> — 화면을 22°(뒤꿈치가 멈춤 블록에 닿음)까지 앞으로 기울여 댄 채 다리를 내립니다. 다리가 수평 아래 약 40°에서 발이 경사에 먼저 닿고, 손을 놓으면 화면이 25°로 돌아가며 발이 경사를 타고 뒷벽까지 미끄러집니다. 25°에서 그대로 내리면 발이 뒷벽 위 모서리를 약 0.66 긁습니다. 접을 때도 22°에서 다리를 올려 받침 뒤 클립에 끼운 뒤 화면을 뒤로 눕힙니다.</li>
</ol>"""

LID_HTML = """<h3 id="build-lid">뚜껑</h3>
<ol class="flow">
<li><b>뚜껑 L·R</b> — 출력 뚜껑마다 자석 3쌍입니다. 밑면 자석 자리는 출력에 있고, 순간접착제(<a href="#parts-i012">i012</a>)로 붙이며 극이 짝과 당기게 합니다.</li>
<li><b>화면 뚜껑</b> — 얹기 전에 리본을 기둥 x583으로 내려 안 쓰는 micro-HDMI 위로 Pi 5 CAM/DISP 1(x589, 입구 −x)에 2.7 mm 꽂고 잠급니다. 점퍼를 GPIO 2번(빨강 5 V)·6번(검정 GND)에 꽂습니다. 이음 레일 위에 얹고 M3 × 10 네 개로 조입니다(자리파기 5.5, 머리 자리 z67.35; 양쪽 이음에 0.5씩 틈).</li>
<li><b>높이 맞춤</b> — 고무발(5)과 모듈 EVA(3)의 눌림 차이로 뚜껑이 건반 윗면과 ±0.5 어긋나면 얇은 받침으로 맞춥니다.</li>
</ol>"""

SERVICE_HTML = """<h3 id="build-service">분해·점검</h3>
<div class="tbl"><table><thead><tr><th>하려는 일</th><th>여는 것</th><th>방법</th></tr></thead><tbody>
<tr><td>패드 바</td><td>없음</td><td>뒷부분이 y214부터라 패드 바(y146.5~185) 위가 비어 있습니다.</td></tr>
<tr><td>O2·O3 모듈</td><td>뚜껑 L (자석)</td><td>앞 공간에서 USB-C 부트를 위로 뽑고 모듈을 곧게 들어 올립니다.</td></tr>
<tr><td>O5 모듈</td><td>뚜껑 R (자석)</td><td>O2·O3와 같습니다.</td></tr>
<tr><td>O4 모듈</td><td>화면 뚜껑 (M3 × 10 네 개, 화면째)</td><td>화면을 뒤로 접고(다리는 클립에) M3 × 10 네 개(앞 y246, 뒤 y322)를 풉니다. 뚜껑을 화면째 천천히 들고(리본을 꽂은 채 약 96 mm), Pi 5 CAM/DISP 1 잠금 막대를 올려 리본을 뺍니다(화면 쪽 ZIF는 받침 안이라 건드리지 않습니다). GPIO 2·6 점퍼를 뺀 뒤 뚜껑을 옆에 두고 앞 공간에서 플러그를 뽑습니다. 되돌릴 때는 리본 B형 방향을 확인하고 잠그며, 점퍼는 2번 빨강·6번 검정입니다.</td></tr>
<tr><td>O1·O7 모듈, EL·ER 끝 부속</td><td>그쪽 스피커</td><td>허브에서 선을 뽑고 스피커를 들어낸 뒤(아래 줄) 모듈을 곧게 들어 올립니다.</td></tr>
<tr><td>O6 모듈</td><td>스피커 R (또는 뒷부분 전체)</td><td>플러그가 가운데 끝벽 R과 스피커 이음 밑에 있습니다.</td></tr>
<tr><td>스피커 하나</td><td>뚜껑 L 또는 R</td><td>XT60 짝을 홈 입구로 가운데 쪽에 당겨 꺼내 손으로 XT60 수(파랑)를 뽑고, 암은 다시 홈에 눌러 끼웁니다. 나비나사 2개를 풀고 스피커를 약 10 mm 들어 핀에서 뺍니다. 통로 지붕 밑 케이블 집게에 끼운 선(EL·ER 리드·헤드폰 선)이 있으면 이때 모두 빼냅니다. 약 18 mm 바깥으로 밀면 끝벽 구멍 안에 감긴 꼬리가 풀려 나오고 XT60 암은 집게에 남습니다. 가운데 안에서 XT60 암을 집게 홈에서 끝벽 쪽으로 곧게 밀어 터널에 넣고(드라이버 손잡이로), 벌어진 틈에서 꼬리를 당겨 끝벽 구멍 밖으로 빼낸 뒤 스피커를 들어냅니다.</td></tr>
<tr><td>뒷부분 전체</td><td>뚜껑 L · 화면 뚜껑 · 뚜껑 R</td><td>허브의 USB-A 7개(O1~O7; PED는 가운데 안이라 그대로)와 3.5 mm 플러그 2개(J702 x514~526, 동글 x644~656 — 둘 다 화면 뚜껑 아래)를 뽑아 앞 공간(y &lt; 241)으로 옮깁니다. 선은 모두 건반 쪽에 남아 통로에 놓입니다. 뒷부분을 곧게 들어 올립니다(앞 공간은 아래가 열려 있어 선 위로 빠집니다).</td></tr>
</tbody></table></div>"""


# --------------------------------------------------------------------------------------------- page parts
FINAL_ONLY = True  # kept for older notes; the page has only the final structure now
FINAL_TABS = [("summary", "요약", "한눈에 보기"), ("circuit", "01", "회로도"), ("dwg", "02", "설계도"),
              ("partdwg", "03", "부품 도면·출력 파일"), ("cad", "04", "3D 모델"), ("sim", "05", "동작 시뮬레이션"),
              ("parts", "06", "부품·사용처"), ("prep", "07", "준비 체크"), ("design", "08", "건반 액션 원리"),
              ("build", "09", "출력·조립"), ("check", "10", "검증·남은 위험"), ("asm", "11", "한 옥타브 조립")]
FRAG_TABS = ("dwg", "partdwg", "sim", "parts", "prep", "asm")

# old tabs and anchors -> new ones (links in the page are rewritten; the router maps old hashes the same way)
HASH_ALIAS = {"overview": "summary", "drawings": "dwg", "rear": "dwg", "buy": "parts", "cost": "parts",
              "dwg11": "dwg-i04"}
UPDATED = "2026-10-08"


def extract_costsel(s, base_css):
    """(old 재료·절감 page; not used by the final structure, kept for reference)"""
    css = main_css(s)
    i = 0
    while i < min(len(css), len(base_css)) and css[i] == base_css[i]:
        i += 1
    i = css.rfind("}", 0, i) + 1
    own = css[i:]
    sub = between(s, '<p class="sub">', "</p>")
    sumbar = s[s.index('<div class="sumbar"'):s.index('<main class="wrap">')]
    main = between(s, '<main class="wrap">', "</main>")
    foot = between(s, "<footer><div class=\"wrap\">", "</div></footer>")
    script = re.findall(r"<script>(.*?)</script>", s, flags=re.S)[0]
    return dict(own_css=own, sub=sub, sumbar=sumbar, main=main, foot=foot, script=script)


HEAD = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toccata v4 통합</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
"""

EXTRA_CSS = """
/* ---- integration (merge.py) ---- */
nav.tabs{z-index:30}
.tbgrid div{min-width:0;overflow-wrap:anywhere}
.tbgrid .wide{grid-column:1/-1;border-right:0}
.tbgrid a{color:var(--blue-ink)}
@media (max-width:820px){.tbgrid{justify-self:stretch;grid-template-columns:repeat(2,minmax(0,1fr))}}
nav.tabs a{min-height:36px;display:inline-flex;align-items:center}
@media (pointer:coarse){nav.tabs a{min-height:44px}}
main > section.page{scroll-margin-top:calc(var(--navh,50px) + 8px)}
/* long URLs in list items (08 건반 액션 원리 sources) must not widen the grid track on phones */
ol.flow,ul.flow{grid-template-columns:minmax(0,1fr)}
ol.flow li,ul.flow li{overflow-wrap:anywhere}
ol.flow li ul{margin:6px 0 0;padding-left:18px}
ol.flow li ul li{margin:3px 0}
#p-build h3[id],#p-build h4{scroll-margin-top:calc(var(--navh,50px) + 12px)}
/* secondary text: AA contrast (>= 4.5:1 on --card and the tint chips) in both themes */
:root{--ink-3:#5F6979}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink-3:#8A93A5}}
:root[data-theme="dark"]{--ink-3:#8A93A5}
.sheet{--ink-3:#5F6979}
#p-parts .pc-ph{--ink-3:#555E70}
"""

ROUTER_JS = """
(function(){
  // tab router: #<tab> shows p-<tab>; a hash naming an element inside a section shows that section and scrolls to it.
  var ALIAS = %s, DEF = 'summary';
  var pages = [].slice.call(document.querySelectorAll('main > section.page'));
  var links = [].slice.call(document.querySelectorAll('nav.tabs a[data-to]'));
  function rawHash(){ var h = (location.hash || '').slice(1); try { h = decodeURIComponent(h); } catch (e) {} return h; }
  function show(){
    var r = rawHash(), anchor = null, id = DEF, a = ALIAS[r.toLowerCase()];
    if (a) { r = a; try { history.replaceState(null, '', '#' + a); } catch (e) {} }
    var low = r.toLowerCase(), pg = low ? document.getElementById('p-' + low) : null;
    if (pg && pg.classList.contains('page')) id = low;
    else if (r) {
      var el = document.getElementById(r), host = el && el.closest('main > section.page');
      if (host) { id = host.id.slice(2); anchor = el; }
    }
    pages.forEach(function(p){ p.hidden = p.id !== 'p-' + id; });
    links.forEach(function(l){ if (l.getAttribute('data-to') === id) l.setAttribute('aria-current', 'page'); else l.removeAttribute('aria-current'); });
    if (anchor) anchor.scrollIntoView(); else window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', show);
  show();
})();
"""

NAVH_JS = """
(function(){
  function setH(){ var n=document.querySelector('nav.tabs'); if(n) document.documentElement.style.setProperty('--navh', n.offsetHeight+'px'); }
  window.addEventListener('resize', setH); setH();
})();
"""


def read_frag(tab):
    d = os.path.join(TABS, tab)
    html = read(os.path.join(d, "section.html"))
    css = read(os.path.join(d, "style.css")) if os.path.exists(os.path.join(d, "style.css")) else ""
    js = read(os.path.join(d, "script.js")) if os.path.exists(os.path.join(d, "script.js")) else ""
    assets = read_assets(os.path.join(d, "assets.txt"))
    return dict(html=html.strip(), css=css, js=js, assets=assets, owner="src/tabs/%s" % tab)


def read_assets(p):
    if not os.path.exists(p):
        return []
    out = []
    for ln in read(p).splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(ln)
    return out


def only_section(s, sid):
    a = s.find(f'<section class="page" id="{sid}"')
    if a < 0:
        raise SystemExit(f"merge: no <section class=\"page\" id=\"{sid}\"> found")
    b = s.rfind("</section>")
    return s[a:b + len("</section>")]


def strip_h2_number(sec):
    """The nav carries the tab number; the section title does not (02 설계도 -> 설계도)."""
    return re.sub(r"(<h2[^>]*>)\s*\d\d\s+", r"\1", sec, count=1)


def rewrite_links(s):
    for old, new in HASH_ALIAS.items():
        s = s.replace(f'href="#{old}"', f'href="#{new}"')
    return s


IDRE = re.compile(r"""\sid=(["'])([^"']+)\1""")


def ids_of(s):
    return [m.group(2) for m in IDRE.finditer(s)]


def rename_ids(sec, clash, prefix):
    """Rename ids in a progress section that another tab owns (e.g. dwg1 lives in 02 설계도 now)."""
    def sub(m):
        v = m.group(2)
        return f' id={m.group(1)}{prefix}-{v}{m.group(1)}' if v in clash else m.group(0)
    return IDRE.sub(sub, sec)


def pcb_revision():
    """(rev, date) = the highest sheet revision in hardware/pcb/netlist/sheets.json (else the README title)."""
    sj = os.path.join(ROOT, "hardware", "pcb", "netlist", "sheets.json")
    try:
        d = json.load(open(sj, encoding="utf-8"))
        sheets = d.get("sheets", d) if isinstance(d, dict) else dict(d)
        if isinstance(sheets, list):
            sheets = dict(sheets)
        best = max(sheets.values(), key=lambda v: (v.get("rev", ""), v.get("date", "")))
        return best.get("rev", "?"), best.get("date", "")
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    try:
        first = read(os.path.join(ROOT, "hardware", "pcb", "README.md")).splitlines()[0]
        m = re.search(r"개정\s*([A-Z])", first)
        return (m.group(1) if m else "?"), ""
    except OSError:
        return "?", ""


def money(n):
    return f"{n:,}"


def build(check=False):
    glb_src, glb_bytes = sync_cad_assets()
    sync_circuit_svgs()
    sync_rear_drawings()
    owners = {}           # section id -> who builds it (for issue reports)
    assets = {}           # asset path -> set(owner)
    misses = []           # text overrides that no longer match their source (report, not fatal)

    def add_assets(lst, owner):
        for a in lst:
            assets.setdefault(a, set()).add(owner)

    # --- 요약
    _sum = read(os.path.join(HERE, "src", "summary.html"))
    sum_css = "\n".join(styles(_sum))
    sum_html = only_section(_sum, "p-summary")
    owners["p-summary"] = "src/build_summary.py -> src/summary.html"
    # --- 01 회로도
    circ = dict(html=only_section(read(os.path.join(PCB, "circuit.html")), "p-circuit"),
                css=read(os.path.join(PCB, "circuit.css")), js=read(os.path.join(PCB, "circuit.js")),
                assets=read_assets(os.path.join(PCB, "assets.txt")), owner="hardware/pcb/src/page.py")
    owners["p-circuit"] = circ["owner"]
    add_assets(circ["assets"], circ["owner"])
    # --- 04 3D 모델
    cad = dict(html=only_section(read(os.path.join(CAD, "viewer", "cad.html")), "p-cad"),
               css=read(os.path.join(CAD, "viewer", "cad.css")), js=read(os.path.join(CAD, "viewer", "cad.js")),
               owner="hardware/mechanical/cad/viewer/gen_viewer.py")
    owners["p-cad"] = cad["owner"]
    add_assets(["cad/parts.json", "cad/asm.json", "cad/toccata.glb.b64.txt"], cad["owner"])
    # --- fragments
    frags = {}
    for t in FRAG_TABS:
        f = read_frag(t)
        f["html"] = only_section(f["html"], "p-" + t)
        frags[t] = f
        owners["p-" + t] = f["owner"]
        add_assets(f["assets"], f["owner"])
    add_assets(["rear/R01_front.png", "rear/R02_rear_left.png", "rear/R03_folded.png"], owners["p-summary"])
    # 06 detail figures through the bundle (see PARTS_IMG_*)
    n_patch = frags["parts"]["js"].count(PARTS_IMG_OLD)
    if n_patch != 1:
        raise SystemExit(f"merge: parts/script.js detail-image line found {n_patch} times (expected 1) - update PARTS_IMG_OLD")
    frags["parts"]["js"] = frags["parts"]["js"].replace(PARTS_IMG_OLD, PARTS_IMG_NEW)

    # --- 08~10 from the key-action report (src/progress.html), 합니다체 and without revision history
    items = json.load(open(os.path.join(HERE, "data", "final_items.json"), encoding="utf-8"))
    prog = extract_progress(read(os.path.join(HERE, "src", "progress.html")))
    pm = prog["main"]
    des = page_section(pm, "p-design")
    des = des.replace(re.search(r"<h2>.*?</h2>", des, re.S).group(0),
                      "<h2>건반 액션 원리 — W1+ 짧은 시소 건반 + 무게 레버</h2>" + DESIGN_NOTE, 1)
    des = apply_overrides(des, OVR_DESIGN, misses, "design")
    des = drop_rows(des, DESIGN_DROP_ROWS, misses, "design")
    des = tidy_html(des)
    n_pass = len(re.findall(r"<td>통과</td></tr>", des))
    bld, print_tot = tab_build(pm, items, misses)
    chk = filter_h3(page_section(pm, "p-check"), keep=["남은 문제", "단계 0 시험 계획", "남은 위험"],
                    intro=(f'<p class="lede">최종 설계(W1+ r4.5)는 <a href="#design">08 건반 액션 원리</a>의 목표 {n_pass}개를 '
                           '모두 통과했습니다. 아래는 아직 남은 문제와, 그것을 확인할 단계 0 시험, 남은 위험입니다.</p>' + DESIGN_NOTE))
    chk = chk.replace("<h2>검증 기록과 남은 문제</h2>", "<h2>검증 결과와 남은 위험</h2>")
    chk = apply_overrides(chk, OVR_CHECK, misses, "check")
    chk = drop_sentences(chk, CHECK_DROP_SENT, misses, "check")
    chk = tidy_html(chk)
    for sid in ("p-design", "p-check"):
        owners[sid] = "src/progress.html (key-action report) via merge.py"
    owners["p-build"] = "merge.py (cad/manifest.json + cad/README.md steps) + src/progress.html p-build"
    # ids that a new tab now owns (dwg1..dwg15 live in 02 설계도): rename the copies in 08~10
    owned = set()
    for s in [sum_html, circ["html"], cad["html"]] + [f["html"] for f in frags.values()]:
        owned.update(ids_of(s))
    prog_secs = {}
    for sid, sec in (("design", des), ("build", bld), ("check", chk)):
        clash = set(ids_of(sec)) & owned
        prog_secs[sid] = rename_ids(sec, clash, sid)
    # progress figures use dwg/*.svg directly
    for sec in prog_secs.values():
        add_assets(re.findall(r'src="(dwg/[^"]+)"', sec), "src/progress.html")

    body = {"summary": sum_html, "circuit": circ["html"], "cad": cad["html"]}
    body.update({t: f["html"] for t, f in frags.items()})
    body.update(prog_secs)
    main = "\n".join(strip_h2_number(body[t]) for t, _, _ in FINAL_TABS)
    main = rewrite_links(main)

    # --- bundles (before the scripts: the map goes into the first script)
    bundled, bundle_info = make_bundles([a for a in assets if bundle_stem(a)])
    for p in bundled:
        assets.pop(p, None)
    for b in bundle_info:
        add_assets([b["bundle"]], "merge.py (bundle of %d files)" % b["files"])

    # --- header / nav / footer
    tot = items["totals"]
    assert tot["school_items"] + tot["school_ship"] + tot["personal"] == tot["total"], tot
    rev, rev_date = pcb_revision()
    rev_txt = f"개정 {rev}" + (f" ({int(rev_date[5:7])}/{int(rev_date[8:10])})" if re.match(r"\d{4}-\d\d-\d\d", rev_date or "") else "")
    gap = [x for x in items["items"] if x.get("source") == "gap"]
    gap_txt = (f' · <a href="#sum-gap">준비처 없는 물건 {len(gap)}줄 ({", ".join(x["id"] for x in gap)})</a>' if gap else "")
    header = ('<header class="tb"><div class="wrap"><div><div class="kicker">Toccata · 최종 도안</div>'
              '<h1>Toccata 최종 도안</h1>'
              '<p class="sub">구매를 마친 최종 설계의 회로도, 방향별·내부 설계도, 부품 도면과 출력 파일, 3D 모델, 동작 시뮬레이션, '
              '부품 사용처와 준비 체크를 한곳에 모았습니다.</p></div>'
              f'<div class="tbgrid"><div><b>갱신</b>{UPDATED}</div><div><b>건반 액션</b>W1+ r4.5</div>'
              '<div><b>본체</b>L2</div><div><b>앞판</b>40°</div>'
              f'<div><b>전원</b>LiFePO4 12.8 V</div><div><b>회로</b>{rev_txt}</div>'
              f'<div class="wide"><b>구매</b>주문 {money(tot["total"])}원 (학교 {money(tot["school_items"])} + 배송 '
              f'{money(tot["school_ship"])} · 사비 {money(tot["personal"])}){gap_txt}</div></div></div></header>')
    nav = ('<nav class="tabs" aria-label="페이지"><div class="wrap">'
           + "".join(f'<a href="#{i}" data-to="{i}"><span class="tag">{t}</span>{n}</a>' for i, t, n in FINAL_TABS)
           + "</div></nav>")
    foot = ('<footer><div class="wrap">원본: hardware/mechanical/cad (CAD 입체·STL·도면, 2026-10-07 빌드) · '
            'hardware/mechanical/key-action-v4 (W1+ r4.5) · hardware/pcb (회로 ' + rev_txt + ') · '
            'docs/report/toccata-v4/data/final_items.json (주문 ' + money(tot["total"]) + '원) · docs/01-hardware-design.md · '
            '좌표 mm: x 가로 (0 = A0 왼쪽 끝), y 흰 건반 앞 끝에서 뒤로, z 책상에서 위로.</div></footer>')

    css = (prog["css"] + "\n/* ---- 01 회로도 (+ page-wide .zbar/.csheet) ---- */\n" + circ["css"]
           + "\n/* ---- 04 3D 모델 ---- */\n" + cad["css"]
           + "".join(f"\n/* ---- {t} ---- */\n" + frags[t]["css"] for t in FRAG_TABS)
           + "\n/* ---- 한눈에 보기 ---- */\n" + sum_css + EXTRA_CSS)
    bundle_js = BUNDLE_JS.replace("__MAP__", json.dumps(bundled, ensure_ascii=False, sort_keys=True))
    scripts = [("router", bundle_js + ROUTER_JS % json.dumps(HASH_ALIAS) + NAVH_JS), ("circuit", circ["js"]),
               ("dwg", frags["dwg"]["js"]), ("partdwg", frags["partdwg"]["js"]), ("cad", cad["js"]),
               ("sim", frags["sim"]["js"]), ("parts", frags["parts"]["js"]), ("prep", frags["prep"]["js"]),
               ("asm", frags["asm"]["js"])]
    page = (HEAD + f"<style>{css}</style>\n" + header + "\n" + nav + '\n<main class="wrap">\n' + main + "\n</main>\n" + foot
            + "".join(f"\n<script>/* {name} */\n{js.strip()}\n</script>" for name, js in scripts if js.strip()) + "\n")
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)

    # page-referenced local paths (static attributes + string literals in scripts); bundled paths are served by bundles
    refs = local_refs(page)
    for r in refs:
        if r not in bundled:
            assets.setdefault(r, set()).add("index.html")
    pub = write_publish_files(assets, page, bundled, bundle_info)
    report = dict(out=out, bytes=len(page.encode()), glb=glb_src, glb_bytes=glb_bytes, publish=pub,
                  bundles=len(bundle_info), bundled_files=len(bundled), print_plan=print_tot,
                  override_misses=misses)
    if check:
        report["check"] = run_checks(page, owners, frags, circ, cad, sum_css, assets, bundled, prog_secs)
    return report


# --------------------------------------------------------------------------------------------- references / publish list
LOCAL_DIRS = ("sch/", "rear/", "dwg/", "img/", "cad/", "fin/", "alt/", "data/")
ATTR_RE = re.compile(r"""\s(?:src|href|data-src|data-png|data-svg|data-href|data-dl|data-file|data-zip|poster)=["']([^"'#][^"']*)["']""")
LIT_RE = re.compile(r"""["'`]((?:sch|rear|dwg|img|cad|fin|alt|data)/[^"'`\s$+{}]+?\.(?:svg|png|jpg|jpeg|webp|json|txt|csv|css|js))["'`]""")


def local_refs(page):
    out = set()
    for m in ATTR_RE.finditer(page):
        v = m.group(1).split("?")[0]
        if re.match(r"^(https?:|mailto:|data:|javascript:|//)", v):
            continue
        if v.startswith(LOCAL_DIRS):
            out.add(v)
    for m in LIT_RE.finditer(page):
        out.add(m.group(1))
    return out


def write_publish_files(assets, page, bundled, bundle_info):
    files, missing, big = [], [], []
    for p in sorted(assets):
        fp = os.path.join(HERE, p)
        if not os.path.isfile(fp):
            missing.append({"path": p, "owners": sorted(assets[p])})
            continue
        sz = os.path.getsize(fp)
        files.append({"path": p, "bytes": sz, "owners": sorted(assets[p])})
        if sz > MAX_FILE:
            big.append(p)
    listed = {f["path"] for f in files}
    unref = []
    for d in LOCAL_DIRS:
        for fp in sorted(glob.glob(os.path.join(HERE, d, "**", "*"), recursive=True)):
            if os.path.isfile(fp):
                rel = os.path.relpath(fp, HERE)
                if rel not in listed and rel not in bundled:
                    unref.append({"path": rel, "bytes": os.path.getsize(fp)})
    total = sum(f["bytes"] for f in files)
    # publish batches: one publish sends at most 255 files and 64 MB (index.html goes with the first batch)
    batches, cur, cur_b = [], [], len(page.encode())
    for f in files:
        if len(cur) >= 250 or cur_b + f["bytes"] > 60 * 1048576:
            batches.append(cur)
            cur, cur_b = [], 0
        cur.append(f["path"])
        cur_b += f["bytes"]
    if cur:
        batches.append(cur)
    by_folder = collections.Counter(f["path"].split("/")[0] + "/" + (f["path"].split("/")[1] if f["path"].count("/") > 1 else "")
                                    for f in files)
    pub = {
        "generated": UPDATED,
        "page": {"path": "index.html", "bytes": len(page.encode())},
        "count": len(files),
        "count_with_page": len(files) + 1,
        "total_bytes": total,
        "total_mb": round(total / 1048576, 2),
        "limits": {"per_file_mb": 15, "per_publish_files": 255, "per_publish_mb": 64, "per_version_files": VERSION_FILES,
                   "per_version_mb": 256},
        "over_15mb": big,
        "missing": missing,
        "fits_one_version": len(files) + 1 <= VERSION_FILES and total + len(page.encode()) <= 256 * 1048576,
        "publishes_needed": len(batches),
        "capabilities": {"db": {}, "user": {}, "downloads": True},
        "by_folder": dict(sorted(by_folder.items())),
        "bundles": bundle_info,
        "bundled_sources": len(bundled),
        "batches": batches,
        "files": files,
        "not_referenced_local": unref,
        "note": ("Publish every path in 'files' (batches[0] with index.html, then the rest to the same url). Files in "
                 "'bundles' replace the per-part zips and location details (their sources stay on disk, unpublished). "
                 "Before publishing, list the live artifact's files (Artifact list, scope 'files') and pass null for every "
                 "live path that is not in 'files' (older versions hold alt/*, img/<old photos>, dwg/d11_overall_layout.svg "
                 "and possibly data/*), otherwise they still count toward the 511-file version limit. "
                 "not_referenced_local = files in this folder the final page does not use."),
    }
    with open(os.path.join(HERE, "publish_files.json"), "w", encoding="utf-8") as f:
        json.dump(pub, f, ensure_ascii=False, indent=1)
    return {k: pub[k] for k in ("count", "count_with_page", "total_mb", "over_15mb", "fits_one_version",
                                "publishes_needed")} | {"missing": len(missing), "not_referenced_local": len(unref)}


# --------------------------------------------------------------------------------------------- checks
class _Walk(html.parser.HTMLParser):
    """Collect ids with their owning section, hrefs, and script blocks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.ids, self.hrefs, self.scripts, self._scr = [], [], [], [], None
        self.section = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section" and "page" in (a.get("class") or "").split():
            self.section = a.get("id")
        if a.get("id"):
            self.ids.append((a["id"], self.section, tag))
        if tag == "a" and a.get("href", "").startswith("#"):
            self.hrefs.append((a["href"][1:], self.section))
        if tag == "script":
            self._scr = [a.get("type", ""), a.get("id", ""), []]

    def handle_endtag(self, tag):
        if tag == "script" and self._scr is not None:
            self.scripts.append((self._scr[0], self._scr[1], "".join(self._scr[2])))
            self._scr = None

    def handle_data(self, data):
        if self._scr is not None:
            self._scr[2].append(data)


def css_unscoped(css, scope, allow=()):
    bad = []
    for pre, body in split_css(css):
        if pre.startswith("@media") or pre.startswith("@supports") or pre.startswith("@container"):
            bad += css_unscoped(body, scope, allow)
        elif pre.startswith("@"):
            continue
        else:
            for sel in pre.split(","):
                sel = sel.strip()
                if not sel:
                    continue
                if sel.startswith(scope) or any(sel.startswith(x) for x in allow):
                    continue
                bad.append(sel)
    return bad


def style_residue(sec):
    """해라체 sentence ends and revision tags left in an 08~10 section (text outside tags/code)."""
    txt = []
    walk_text(sec, lambda t: txt.append(t) or t)
    t = " ".join(txt)
    ends = re.findall(r"[가-힣]{1,6}다(?=[.:;!?(]|\s*$)", t)
    ends = [e for e in ends if not e.endswith(("니다", "보다", "마다"))]
    tags = re.findall(r"(?<![\w_])r\d\.\d+(?:\s*고침[^,;)]{0,8})?", t)
    return {"haera_ends": collections.Counter(ends).most_common(20), "rev_tags": collections.Counter(tags).most_common(20)}


def _nums(s):
    return sorted(float(x) for x in re.findall(r"\d+(?:\.\d+)?", s or ""))


def data_freshness():
    """Cross-tab data check: the circuit's cables.csv is the source of every cut length; final_items.json is the
    source of every item card. Report downstream copies that no longer match (a builder was not re-run)."""
    cuts = cable_cuts()
    out = {}
    # 05 sim: system.json keeps a copy of cables.csv rows
    try:
        sysj = json.load(open(os.path.join(HERE, "fin", "sim", "system.json"), encoding="utf-8"))
        bad = []
        for w, row in (sysj.get("cables") or {}).items():
            if w in cuts and row.get("자르는 길이 (mm)") != cuts[w]:
                bad.append(f"{w}: sim '{row.get('자르는 길이 (mm)')}' != cables.csv '{cuts[w]}'")
        missing = sorted(set(cuts) - set(sysj.get("cables") or {}))
        out["sim_system_cables"] = {"owner": "key-action-v4/model/export_sim.py -> fin/sim/system.json",
                                    "stale": bad, "rows_missing": missing}
    except (OSError, ValueError) as e:
        out["sim_system_cables"] = {"error": str(e)[:200]}
    # 07 prep: c-w* lines carry 'W.. · 자르는 길이 ... · '
    try:
        lines = json.load(open(os.path.join(HERE, "fin", "prep", "lines.json"), encoding="utf-8"))["lines"]
        bad = []
        for ln in lines:
            m = re.match(r"(W[\w~]+) · 자르는 길이 (.*?) · ", ln.get("m", ""))
            if ln.get("id", "").startswith("c-w") and m and m.group(1) in cuts:
                if _nums(m.group(2).replace(" mm", "")) != _nums(cuts[m.group(1)]):
                    bad.append(f"{ln['id']}: prep '{m.group(2)}' != cables.csv '{cuts[m.group(1)]}'")
        out["prep_cable_lines"] = {"owner": "src/build_prep.py -> fin/prep/lines.json", "stale": bad}
    except (OSError, ValueError, KeyError) as e:
        out["prep_cable_lines"] = {"error": str(e)[:200]}
    # final_items texts: 'W703 580' style mentions must be numbers of that wire's cut
    items = json.load(open(os.path.join(HERE, "data", "final_items.json"), encoding="utf-8"))
    bad = []
    for it in items["items"]:
        txt = " ".join(str(it.get(k) or "") for k in ("need_note", "where", "check", "pack_note"))
        for w, n in re.findall(r"\b(W\d{3}[a-z]?) (\d+(?:\.\d+)?)(?!\.?\d|\s*(?:가닥|개|장|줄|곳))", txt):
            if w in cuts and float(n) not in _nums(cuts[w]):
                bad.append(f"{it['id']}: '{w} {n}' but cables.csv {w} = '{cuts[w]}'")
    out["items_cable_mentions"] = {"owner": "src/build_items.py -> data/final_items.json", "stale": sorted(set(bad))}
    # 06 parts: item cards must equal final_items.json
    try:
        cards = json.load(open(os.path.join(HERE, "fin", "loc", "cards.json"), encoding="utf-8"))["cards"]
        fim = {x["id"]: x for x in items["items"]}
        bad = []
        for c in cards:
            it = fim.get(c.get("key"))
            if it is None:
                continue
            for f in ("name", "where"):
                if (c.get(f) or "") != (it.get(f) or ""):
                    bad.append(f"{c['key']}.{f}")
        out["parts_cards_vs_items"] = {"owner": "cad/src/locate.py + src/tabs/parts/build_section.py -> fin/loc/cards.json",
                                       "stale": bad}
    except (OSError, ValueError, KeyError) as e:
        out["parts_cards_vs_items"] = {"error": str(e)[:200]}
    # build order of the generated data (newest source first)
    def mt(p):
        fp = os.path.join(ROOT, p)
        return os.path.getmtime(fp) if os.path.exists(fp) else 0
    chain = [("hardware/pcb/netlist/cables.csv", "circuit"), ("docs/report/toccata-v4/data/final_items.json", "items"),
             ("docs/report/toccata-v4/fin/loc/cards.json", "parts"), ("docs/report/toccata-v4/fin/prep/lines.json", "prep"),
             ("docs/report/toccata-v4/fin/sim/system.json", "sim"), ("docs/report/toccata-v4/src/summary.html", "summary")]
    t_c, t_i = mt(chain[0][0]), mt(chain[1][0])
    older = []
    for p, who in chain[1:]:
        ref = t_c if who in ("items", "sim") else max(t_c, t_i)
        if mt(p) < ref:
            older.append(f"{who}: {p.split('/')[-1]} is older than its source "
                         f"({'cables.csv' if who in ('items', 'sim') else 'cables.csv / final_items.json'})")
    out["older_than_source_info"] = older  # timestamps only; the content checks above decide 'ok'
    out["ok"] = not any(v.get("stale") or v.get("error") for v in out.values() if isinstance(v, dict))
    return out


def run_checks(page, owners, frags, circ, cad, sum_css, assets, bundled, prog_secs):
    res = {}
    res["placeholders_left"] = sorted(set(re.findall(r"__[A-Z0-9]{3,}__", page)) - {"__MAP__"})
    res["data_freshness"] = data_freshness()
    w = _Walk()
    w.feed(page)
    secs = re.findall(r'<section class="page" id="([^"]+)"', page)
    want = ["p-" + t for t, _, _ in FINAL_TABS]
    res["sections"] = {"found": secs, "ok": secs == want}
    navs = re.findall(r'data-to="([^"]+)"', page.split("</nav>")[0])
    res["nav"] = {"tabs": navs, "ok": navs == [t for t, _, _ in FINAL_TABS]}
    # unique ids
    seen = {}
    for i, sec, tag in w.ids:
        seen.setdefault(i, []).append(sec or "(header/nav)")
    dups = {i: v for i, v in seen.items() if len(v) > 1}
    res["ids"] = {"count": len(seen), "duplicates": {i: [owners.get(s, s) for s in v] for i, v in dups.items()}}
    # hash tokens allowed by the router
    res["ids"]["bad_tokens"] = [i for i in seen if not re.match(r"^[A-Za-z0-9._~-]+$", i)]
    # href targets
    idset = set(seen)
    broken = []
    for h, sec in w.hrefs:
        if not h:
            continue
        t = HASH_ALIAS.get(h.lower(), h)
        if ("p-" + t.lower()) in idset or t in idset:
            continue
        broken.append({"href": "#" + h, "in": owners.get(sec, sec)})
    res["hrefs"] = {"count": len(w.hrefs), "broken": broken}
    # old anchors that must still resolve
    old = ["dwg%d" % i for i in range(1, 16)] + ["rd%d" % i for i in range(1, 7)] + list(HASH_ALIAS)
    unresolved = []
    for h in old:
        t = HASH_ALIAS.get(h, h)
        if not (("p-" + t) in idset or t in idset):
            unresolved.append(h)
        elif t in seen and seen[t][0] != "p-dwg" and h.startswith(("dwg", "rd")):
            unresolved.append(h + " (not in p-dwg: %s)" % seen[t][0])
    res["old_anchors"] = {"checked": len(old), "unresolved": unresolved}
    # local paths
    miss = [p for p in sorted(assets) if not os.path.isfile(os.path.join(HERE, p))]
    res["local_paths"] = {"count": len(assets), "missing": [{"path": p, "owners": sorted(assets[p])} for p in miss]}
    # bundles: every bundled path is inside its bundle file, and no bundled source is also listed for publishing
    bad_b, loaded = [], {}
    for p, b in bundled.items():
        if b not in loaded:
            loaded[b] = json.load(open(os.path.join(HERE, b), encoding="utf-8"))
        if p not in loaded[b] or loaded[b][p] != read(os.path.join(HERE, p)):
            bad_b.append(p)
    res["bundles"] = {"files": len(loaded), "bundled_paths": len(bundled), "mismatch": bad_b,
                      "also_published": sorted(set(bundled) & set(assets)),
                      "parts_patch": PARTS_IMG_NEW in page}
    # scripts
    tmp = tempfile.mkdtemp(prefix="toccata-merge-", dir=os.environ.get("TMPDIR"))
    sres = []
    for k, (typ, sid, code) in enumerate(w.scripts):
        if typ in ("application/json", "application/ld+json"):
            try:
                json.loads(code)
                sres.append({"block": k, "type": "json", "id": sid, "ok": True})
            except ValueError as e:
                sres.append({"block": k, "type": "json", "id": sid, "ok": False, "err": str(e)[:200]})
            continue
        if typ and typ not in ("text/javascript", "module"):
            sres.append({"block": k, "type": typ, "skipped": True})
            continue
        fp = os.path.join(tmp, "block%02d.js" % k)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(code)
        r = subprocess.run(["node", "--check", fp], capture_output=True, text=True)
        head = code.strip().split("\n", 1)[0][:60]
        sres.append({"block": k, "head": head, "bytes": len(code.encode()), "ok": r.returncode == 0,
                     "err": r.stderr.strip()[-400:] if r.returncode else ""})
    res["scripts"] = sres
    # forbidden calls / external fetches in scripts
    js_all = "\n".join(c for t, _, c in w.scripts if t not in ("application/json",))
    res["js_lint"] = {
        "alert_confirm_prompt": re.findall(r"(?<![\w.])(?:window\.)?(alert|confirm|prompt)\s*\(", js_all),
        "external_urls": sorted(set(u for u in re.findall(r"https?://[^\s'\"`)]+", js_all)
                                    if not u.startswith("https://cdnjs.cloudflare.com/"))),
        "window_print": bool(re.search(r"window\.print\s*\(", js_all)),
    }
    # CSS scope
    scope = {}
    for t, f in frags.items():
        scope[t] = css_unscoped(f["css"], "#p-" + t)
    scope["summary"] = css_unscoped(sum_css, "#p-summary")
    scope["cad"] = css_unscoped(cad["css"], "#p-cad")
    scope["circuit"] = css_unscoped(circ["css"], "#p-circuit", allow=(".zbar", ".csheet"))
    res["css_scope"] = {k: v for k, v in scope.items() if v}
    # literal colours in fragment CSS outside drawing sheets (informational)
    lit = {}
    for t, f in list(frags.items()) + [("cad", cad), ("circuit", circ), ("summary", {"css": sum_css})]:
        n = []
        for pre, body in split_css(f["css"]):
            blocks = split_css(body) if pre.startswith("@") else [(pre, body)]
            for p2, b2 in blocks:
                if re.search(r"sheet|svg|draw|sim-draw|canvas|dwimg|loc|fig", p2):
                    continue
                if re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", b2):
                    n.append(p2[:80])
        if n:
            lit[t] = n[:8] + (["... +%d" % (len(n) - 8)] if len(n) > 8 else [])
    res["css_literal_colours"] = lit
    res["style_08_10"] = {sid: style_residue(sec) for sid, sec in prog_secs.items()}
    res["page_bytes"] = len(page.encode())
    return res


if __name__ == "__main__":
    rep = build(check="--check" in sys.argv)
    chk = rep.pop("check", None)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if chk is not None:
        print(json.dumps(chk, ensure_ascii=False, indent=1))
