"""Merge the Toccata v4 pages into ONE artifact page (index.html).

Sources (replace a source file, then re-run; the other parts stay as they are):
  src/progress.html   건반 액션 진행 현황 (full page, as published or as built by the v4 report builder)
  src/costsel.html    재료 목록·절감 선택 (full page from gen_sel.py or as published)
  ../../../hardware/pcb/page/circuit.{html,css,js}   회로도 탭 (hardware/pcb/src/page.py)

usage:  python3 merge.py            -> index.html
        python3 merge.py --check    -> also prints the section / tab inventory
Publish: see README.md in this folder (same artifact URL every time).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, "..", "..", "..", "hardware", "pcb", "page"))


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


def extract_costsel(s, base_css):
    css = main_css(s)
    i = 0
    while i < min(len(css), len(base_css)) and css[i] == base_css[i]:
        i += 1
    # back up to the last complete rule so the picker keeps whole rules
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
nav.tabs{z-index:30}
#p-cost .sumbar{top:calc(env(safe-area-inset-top,0px) + var(--navh,50px));margin:0 0 6px;border:1px solid var(--rule);border-radius:10px}
#p-cost .sumbar .wrap{padding-inline:14px}
.tb .merged{font-size:12.5px;color:var(--ink-3);margin:.4rem 0 0}
#p-rear .sheet .cap .zbar a{white-space:nowrap}
#p-rear .rgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:8px 0 14px}
#p-rear .rcard{margin:0;background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:8px}
#p-rear .rcard img{display:block;width:100%;max-width:100%;height:auto;border-radius:6px;background:#f8f8f8}
#p-rear .rcard figcaption{padding:6px 2px 0}
"""

REAR_JS = """
(function(){
  // 10 뒷부분 도면: 2배 = PNG 2000 px, 3배 = the sheet SVG at 3000 px (vector, sharp); 맞춤 = PNG
  document.addEventListener('click', function(e){
    var b = e.target.closest('#p-rear .zbar button'); if(!b) return;
    var img = b.closest('.rsheet').querySelector('.dwimg img'); if(!img) return;
    var want = b.dataset.z === '3' ? img.dataset.svg : img.dataset.png;
    if (want && img.getAttribute('src') !== want) img.setAttribute('src', want);
  });
})();
"""

NAVH_JS = """
(function(){
  function setH(){ var n=document.querySelector('nav.tabs'); if(n) document.documentElement.style.setProperty('--navh', n.offsetHeight+'px'); }
  window.addEventListener('resize', setH); setH();
})();
"""


def sync_circuit_svgs():
    """Copy the current schematic / board SVGs from hardware/pcb into sch/ (published paths)."""
    import glob
    import shutil
    dst = os.path.join(HERE, "sch")
    os.makedirs(dst, exist_ok=True)
    root = os.path.normpath(os.path.join(PCB, ".."))
    n = 0
    for sub in ("schematic", "board"):
        for f in glob.glob(os.path.join(root, sub, "*.svg")):
            shutil.copy2(f, dst)
            n += 1
    return n


CAD = os.path.normpath(os.path.join(HERE, "..", "..", "..", "hardware", "mechanical", "cad"))


def sync_cad_assets():
    """09 CAD 모델: copy the viewer data + GLB next to the page (hardware/mechanical/cad/viewer/gen_viewer.py)."""
    import shutil
    dst = os.path.join(HERE, "cad")
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(os.path.join(CAD, "viewer", "parts.json"), os.path.join(dst, "parts.json"))
    # the artifact host does not serve .glb: ship the GLB as base64 text, the viewer decodes it (cad.js)
    import base64
    raw = open(os.path.join(CAD, "Toccata_전체조립.glb"), "rb").read()
    open(os.path.join(dst, "toccata.glb.b64.txt"), "w").write(base64.b64encode(raw).decode("ascii"))
    old = os.path.join(dst, "toccata.glb")
    if os.path.exists(old):
        os.remove(old)


# 10 뒷부분 도면: dimensioned sheets + renders made by hardware/mechanical/cad/src/drawings.py (run by build_all.py)
REAR_DIR = "rear"
REAR_SHEETS = [
    ("D01_plan", "D01 · 전체 평면", "위에서 본 모습입니다. 뚜껑과 화면은 뗐습니다. 위는 전체 (1:2.5), 아래는 가운데 유닛 확대 (1:1.5)와 안 물건 번호표입니다. "
     "점선은 스피커와 바닥 밑에 숨은 것 (케이블 통로, 고무발, 볼 핀)입니다. A·B·C·D는 다른 도면이 자르는 자리입니다."),
    ("D02_speaker_section", "D02 · 스피커 단면", "왼쪽 스피커를 유닛 가운데에서 자른 단면입니다 (1:1). 40° 앞판, 판, 유닛, 그릴, 케이블 통로가 보입니다. "
     "확대 A (5:1)는 27° 소리 길이 모듈 뒤 윗모서리 위로 지나가는 여유를 보여 줍니다. 안 부피와 Qtc 계산은 아래 글에 있습니다."),
    ("D03_centre_sections", "D03 · 가운데 유닛 단면 2개", "가운데 유닛을 두 곳에서 자른 단면입니다 (1:1). B-B는 Pi 5와 화면, C-C는 허브와 앰프를 지납니다. "
     "뚜껑 높이, 안 높이, 흡기·배기 홈의 크기와 넓이를 적었습니다."),
    ("D04_rear_elevation", "D04 · 뒷면 입면 - I/O 판", "뒤에서 본 모습 (1:2.5)과 I/O 판 확대 (2:1)입니다. 케이블 통과 구멍, USB-C 전원 입력, 로커 스위치, "
     "페달 잭, 루버의 크기와 중심을 표로 정리했습니다."),
    ("D05_touchscreen", "D05 · 터치스크린 (사용 25° / 뒤꿈치 22° / 접은 상태)", "터치스크린 3판 옆 단면입니다 (1:1). 쓰는 자세 25°, 받침다리를 넣고 뺄 때의 "
     "뒤꿈치 22°, 접은 운반 상태입니다. 경첩 축, 가장 앞·가장 높은 점, 접은 높이, 모듈 쪽 지킴선을 적었습니다."),
    ("D06_plywood_cuts", "D06 · 합판 재단도 (400 × 1200 한 장)", "오꾸메 11.5T 400 × 1200 한 장에 합판 조각을 모두 배치했습니다 (1:3). "
     "아래는 조각별 도면 (1:4·1:5)과 경사 자르기·따냄·구멍 표입니다. 가게에서는 직사각형으로만 자르고 나머지는 집에서 다듬습니다."),
]
REAR_RENDERS = [("R01_front", "R01 · 앞 3/4 (쓰는 상태)"), ("R02_rear_left", "R02 · 뒤 왼쪽 3/4"),
                ("R03_folded", "R03 · 화면을 접은 운반 상태 (선택 부품인 화면 덮개는 빼고 그림)")]


def sync_rear_drawings():
    """10 뒷부분 도면: copy cad/drawings/D0*.svg|png and cad/renders/R0*.png into rear/ (published paths rear/...)."""
    import shutil
    dst = os.path.join(HERE, REAR_DIR)
    os.makedirs(dst, exist_ok=True)
    copied = []
    for stem, _, _ in REAR_SHEETS:
        for ext in (".svg", ".png"):
            src = os.path.join(CAD, "drawings", stem + ext)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst, stem + ext))
                copied.append(REAR_DIR + "/" + stem + ext)
    for stem, _ in REAR_RENDERS:
        src = os.path.join(CAD, "renders", stem + ".png")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, stem + ".png"))
            copied.append(REAR_DIR + "/" + stem + ".png")
    return copied


def rear_section_html():
    figs = []
    for i, (stem, title, cap) in enumerate(REAR_SHEETS):
        svg, png = "%s/%s.svg" % (REAR_DIR, stem), "%s/%s.png" % (REAR_DIR, stem)
        # zoom bar = the circuit tab's .zbar / .csheet (circuit.js toggles z2 / z3); REAR_JS swaps 3배 to the SVG (sharp)
        figs.append('<figure class="sheet csheet rsheet" id="rd%d"><div class="cap"><span><b>%s</b></span>'
                    '<span class="zbar" role="group" aria-label="확대"><button type="button" data-z="1" aria-pressed="true">맞춤</button>'
                    '<button type="button" data-z="2">2배</button><button type="button" data-z="3">3배</button>'
                    '<a class="mono" href="%s" target="_blank" rel="noopener">크게 보기 (SVG) ↗</a> · '
                    '<a class="mono" href="%s" target="_blank" rel="noopener">PNG ↗</a></span></div>'
                    '<div class="dwimg"><img src="%s" data-png="%s" data-svg="%s" alt="%s" loading="lazy"></div>'
                    '<figcaption class="small muted">%s</figcaption></figure>'
                    % (i + 1, title, svg, png, png, png, svg, title, cap))
    rend = "".join('<figure class="rcard"><a href="%s/%s.png" target="_blank" rel="noopener"><img src="%s/%s.png" alt="%s" loading="lazy"></a>'
                   '<figcaption class="small muted">%s</figcaption></figure>' % (REAR_DIR, st, REAR_DIR, st, t, t) for st, t in REAR_RENDERS)
    return ('<section class="page" id="p-rear" hidden><h2>뒷부분 도면 (L2 · 스피커 앞판 40° · 터치스크린 3판)</h2>'
            '<p class="lede">건반 뒤의 한 몸 뒷바(스피커 두 통 + 가운데 유닛)와 터치스크린의 치수 도면 6장입니다. '
            '모든 선과 숫자는 CAD 생성기가 만든 입체를 잘라서(단면) 또는 위·뒤에서 비춰서(투영) 그렸습니다. 그래서 출력 STL과 숫자가 같습니다. '
            '<code>build_all.py</code>를 돌리면 도면도 다시 만들어집니다. SVG는 A2(594 × 420 mm) 크기라 100 %로 출력하면 적힌 척도가 맞습니다. 글씨가 작으면 각 도면의 <b>2배·3배</b> 단추를 누르고 옆으로 밀어 봅니다 (3배는 SVG라 선명합니다).</p>'
            + "".join(figs)
            + '<h3>렌더 (같은 모델)</h3><div class="rgrid">' + rend + '</div>'
            '<p class="small muted">원본: hardware/mechanical/cad/src/drawings.py → hardware/mechanical/cad/drawings/, renders/. '
            '좌표: x 가로(0 = A0 왼쪽 끝), y 흰 건반 앞 끝에서 뒤로, z 책상에서 위로, 단위 mm.</p></section>')



# ---- 최종본만 보여 주기 (2026-10-02, 사용자: "예전 구조 다 빼고 최종적으로 다루는 내용만") ----
FINAL_ONLY = True
FINAL_TABS = [("summary", "요약", "한눈에 보기"), ("design", "01", "건반 액션 구조"), ("drawings", "02", "건반 도면"),
              ("check", "03", "검증·남은 위험"), ("build", "04", "출력·조립"), ("buy", "05", "구매 목록"),
              ("circuit", "06", "회로도"), ("cad", "07", "CAD 모델"), ("rear", "08", "뒷부분 도면")]


def page_section(main, sid):
    a = main.find(f'<section class="page" id="{sid}"')
    if a < 0:
        return ""
    b = main.find('<section class="page"', a + 10)
    return main[a:] if b < 0 else main[a:b]


def filter_h3(sec, keep=None, drop=None, intro=None):
    """Split a page section at its top-level <h3> headings; keep / drop chunks by heading text prefix."""
    end = sec.rfind("</section>")
    body, tail = sec[:end], sec[end:]
    parts = re.split(r"(?=<h3[ >])", body)
    head, chunks = parts[0], parts[1:]
    if intro is not None:
        h2 = re.search(r"<h2>.*?</h2>", head, re.S)
        head = head[:h2.end()] + intro if h2 else head
    out = [head]
    for c in chunks:
        title = re.sub(r"<[^>]+>", "", re.search(r"<h3[^>]*>(.*?)</h3>", c, re.S).group(1)).strip()
        if keep is not None and not any(title.startswith(k) for k in keep):
            continue
        if drop is not None and any(title.startswith(d) for d in drop):
            continue
        out.append(c)
    return "".join(out) + tail

def build(check=False):
    sync_circuit_svgs()
    sync_cad_assets()
    sync_rear_drawings()
    cad_html = read(os.path.join(CAD, "viewer", "cad.html"))
    cad_css = read(os.path.join(CAD, "viewer", "cad.css"))
    cad_js = read(os.path.join(CAD, "viewer", "cad.js"))
    prog = extract_progress(read(os.path.join(HERE, "src", "progress.html")))
    # 한눈에 보기 (src/build_summary.py -> src/summary.html): first tab and the landing page
    _sum = read(os.path.join(HERE, "src", "summary.html")) if os.path.exists(os.path.join(HERE, "src", "summary.html")) else ""
    sum_css = "\n".join(styles(_sum)) if _sum else ""
    sum_html = _sum[_sum.find('<section class="page" id="p-summary"'):_sum.rfind('</section>') + len('</section>')] if _sum else ""
    if sum_html:
        prog["script"] = prog["script"].replace("(location.hash||'#overview')", "(location.hash||'#summary')").replace("else id='overview';", "else id='summary';")
    cost = extract_costsel(read(os.path.join(HERE, "src", "costsel.html")), prog["css"])
    circ_html = read(os.path.join(PCB, "circuit.html"))
    circ_css = read(os.path.join(PCB, "circuit.css"))
    circ_js = read(os.path.join(PCB, "circuit.js"))
    _cm = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
    _n_parts = len(_cm["parts"])
    _n_print = len([p for p in _cm["print"] if "06_출력공구" not in json.dumps(p, ensure_ascii=False)])
    header = ('<header class="tb"><div class="wrap"><div><div class="kicker">Toccata · v4 · 통합본</div>'
              '<h1>Toccata 설계 · 비용 · 도면</h1>'
              '<p class="sub">맨 앞 "한눈에 보기" 탭에 지금 설계와 실제 구매 비용을 모았습니다. 뒤 탭에 건반 액션(W1+) 진행 현황, 재료 목록과 절감 선택, 전자부 회로도, 출력용 CAD 모델, 뒷부분 도면이 있습니다. '
              '앞으로 바뀌는 내용은 이 페이지에만 반영합니다.</p>'
              '<p class="merged">합친 원본: 진행 현황 1fA3D1HQRvNEanGCjDPhTZ · 재료 절감 Vv8pahUbEkKhwsZwGnmsGG (두 원본은 더 고치지 않음)</p></div>'
              '<div class="tbgrid"><div><b>갱신</b>2026-10-02</div><div><b>건반 액션</b>4.5차 설계 (r4.5)</div>'
              '<div><b>실제 구매</b>731,485원</div><div><b>재료 카드</b>86 (전체 목록)</div><div><b>회로도</b>9장 (hardware/pcb)</div>'
              f'<div><b>CAD</b>부품 {_n_parts:,} · 조립 3D</div><div><b>출력 STL</b>{_n_print}종 + 공구 4 (hardware/mechanical/cad)</div></div></div></header>')
    nav = ('<nav class="tabs" aria-label="페이지"><div class="wrap">'
           + ('<a href="#summary" data-to="summary"><span class="tag">요약</span>한눈에 보기</a>' if sum_html else '') + prog["tabs"]
           + '<a href="#cost" data-to="cost"><span class="tag">07</span>재료·절감 선택</a>'
           + '<a href="#circuit" data-to="circuit"><span class="tag">08</span>회로도</a>'
           + '<a href="#cad" data-to="cad"><span class="tag">09</span>CAD 모델</a>'
           + '<a href="#rear" data-to="rear"><span class="tag">10</span>뒷부분 도면</a>'
           + ('<span class="sep"></span>' + prog["alts"] if prog["alts"] else "") + "</div></nav>")
    cost_sec = ('<section class="page" id="p-cost" hidden><h2>재료 목록과 절감 선택</h2>'
                f'<p class="lede">{cost["sub"]}</p>' + cost["sumbar"] + cost["main"]
                + f'<p class="small muted">{cost["foot"]}</p></section>')
    # put the new tabs after the progress pages but before the alternative pages (p-s1 ...)
    main = sum_html + prog["main"]
    k = main.find('<section class="page" id="p-s1"')
    rear_html = rear_section_html()
    if k < 0:
        main = main + cost_sec + circ_html + cad_html + rear_html
    else:
        main = main[:k] + cost_sec + circ_html + cad_html + rear_html + main[k:]
    if FINAL_ONLY:
        pm = prog["main"]
        chk = filter_h3(page_section(pm, "p-check"), keep=["남은 문제", "단계 0 시험 계획", "남은 위험"],
                        intro='<p class="lede">최종 설계(W1+ r4.5)는 검증 45개를 모두 통과했습니다. 아래는 아직 남은 문제와, 그것을 확인할 단계 0 시험, 남은 위험입니다.</p>')
        chk = chk.replace("<h2>검증 기록과 남은 문제</h2>", "<h2>검증 결과와 남은 위험</h2>")
        bld = filter_h3(page_section(pm, "p-build"), drop=["예비 건반 보관함"])
        # 도면 11(전체 배치)은 L1·v3 뒷바(깊이 410, 보관함) 그림이라 뺀다 — 지금 전체 배치는 08 뒷부분 도면 D01·D02
        drw = page_section(pm, "p-drawings")
        i = drw.find('<figure class="sheet" id="dwg11">'); j = drw.find("</figure>", i) + len("</figure>")
        if i >= 0:
            drw = drw[:i] + drw[j:]
        drw = drw.replace('<li><a href="#dwg11">11. 전체 배치 측면</a></li>', "")
        drw = drw.replace("<h2>도면 15장</h2>", "<h2>건반 액션 도면</h2>")
        drw = drw.replace("주황 점선은 끝까지 누른 자세입니다.</p>", "주황 점선은 끝까지 누른 자세입니다. 본체 전체 배치(L2 뒷바·스피커·화면)는 08 뒷부분 도면의 D01~D06에 있습니다.</p>", 1)
        _buy = read(os.path.join(HERE, "src", "buylist.html"))
        buy_css = "\n".join(styles(_buy))
        buy_html = _buy[_buy.find('<section class="page" id="p-buy"'):_buy.rfind("</section>") + len("</section>")]
        circ_f = circ_html.replace('<a href="#cost">재료·절감 선택</a> 탭에 있습니다', '<a href="#buy">구매 목록</a> 탭과 최종 재료 페이지에 있습니다')
        main = (sum_html + page_section(pm, "p-design") + drw + chk + bld + buy_html
                + circ_f + cad_html + rear_html)
        nav = ('<nav class="tabs" aria-label="페이지"><div class="wrap">'
               + "".join(f'<a href="#{i}" data-to="{i}"><span class="tag">{t}</span>{n}</a>' for i, t, n in FINAL_TABS)
               + "</div></nav>")
        header = ('<header class="tb"><div class="wrap"><div><div class="kicker">Toccata · v4 확정 설계</div>'
                  '<h1>Toccata 설계 · 비용 · 도면</h1>'
                  '<p class="sub">지금 만들 최종 설계만 모았습니다. 맨 앞 "한눈에 보기"에 설계와 실제 구매 비용을 요약했고, 뒤 탭에 건반 액션, 도면, 남은 위험, 출력·조립, 구매 목록, 회로도, CAD 모델, 뒷부분 도면이 있습니다.</p></div>'
                  '<div class="tbgrid"><div><b>갱신</b>2026-10-02</div><div><b>건반 액션</b>W1+ r4.5</div>'
                  '<div><b>본체</b>L2 · 스피커 앞판 40°</div><div><b>화면</b>터치스크린 3판</div>'
                  '<div><b>회로도</b>9장 · 개정 C</div><div><b>실제 구매</b>731,485원</div></div></div></header>')
        css = prog["css"] + "\n/* ---- 회로도 ---- */\n" + circ_css + "\n" + cad_css + EXTRA_CSS \
            + "\n/* ---- 한눈에 보기 ---- */\n" + sum_css + "\n/* ---- 구매 목록 ---- */\n" + buy_css
        foot = ('<footer><div class="wrap">모든 수치는 설계 모델과 독립 검증에서 나왔습니다. 원본: docs/01-hardware-design.md(v4 확정본), '
                'hardware/mechanical(sound-requirements.md · key-action-v4 · cad · touchscreen/rev3), hardware/pcb(개정 C), hardware/bom. '
                '실제 구매 목록: 최종 재료 페이지 9CJ3HwhbhoodCAui94g28n.</div></footer>')
        page = (HEAD + f"<style>{css}</style>\n" + header + "\n" + nav + '\n<main class="wrap">' + main + "</main>\n" + foot
                + f"\n<script>{prog['script']}</script>\n<script>{circ_js}{NAVH_JS}{REAR_JS}</script>\n<script>{cad_js}</script>\n")
        out = os.path.join(HERE, "index.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(page)
        if check:
            print("sections:", re.findall(r'<section class="page" id="([^"]+)"', page))
            print("tabs:", re.findall(r'data-to="([^"]+)"', nav))
            print("bytes:", len(page.encode()))
        return out
    css = prog["css"] + "\n/* ---- 재료·절감 선택 (scoped) ---- */\n" + scope_css(cost["own_css"], "#p-cost") \
        + "\n/* ---- 회로도 ---- */\n" + circ_css + "\n" + cad_css + EXTRA_CSS + "\n/* ---- 한눈에 보기 ---- */\n" + sum_css
    foot = (f'<footer><div class="wrap">{prog["foot"]}<br>{cost["foot"]}<br>'
            '회로도: 저장소 hardware/pcb/ (SVG·CSV·생성기), 조사 노트 hardware/pcb/research/.</div></footer>')
    page = (HEAD + f"<style>{css}</style>\n" + header + "\n" + nav + '\n<main class="wrap">' + main + "</main>\n" + foot
            + f"\n<script>{prog['script']}</script>\n<script>{cost['script']}</script>\n<script>{circ_js}{NAVH_JS}{REAR_JS}</script>\n<script>{cad_js}</script>\n")
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    if check:
        print("sections:", re.findall(r'<section class="page" id="([^"]+)"', page))
        print("tabs:", re.findall(r'data-to="([^"]+)"', nav))
        print("bytes:", len(page.encode()))
    return out


if __name__ == "__main__":
    print(build(check="--check" in sys.argv))
