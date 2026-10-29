"""Tab "11 한 옥타브 조립" (#p-asm) from the standalone guide docs/report/octave-assembly/index.html.

The standalone page (artifact U6CnesuxwRDptj9u7QfwCY) is the source; this script turns its body into the fragment
contract of merge.py: one <section class="page" id="p-asm" hidden>, ids prefixed asm-, classes prefixed a- (the page
has its own .note/.tbl/.flow), inner <section> -> <article>, and asset paths moved to the page's own copies:
  img/<render>.webp   -> fin/asm/<render>.webp   (copied here)
  photo/<id>.webp     -> img/bom/<id>.jpg        (the purchase-list photos the page already ships)
  dwg/d*.svg          -> dwg/d*.svg, dwg/BRD-*.svg -> sch/BRD-*.svg
The step figures are live 3D boxes (data-v3d): the model data model/octave.json is copied to fin/asm/octave.json and
script.js = ticks.js (step ticks + drawing viewer, hand-written) + ../../../../octave-assembly/viewer3d.js (the same
3D viewer as the standalone page). style.css is hand-written for the page tokens; rerun this after editing the
standalone guide, its viewer or src/make_models.py.

usage: python3 build_section.py
"""
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))           # docs/report/toccata-v4
SRC = os.path.normpath(os.path.join(PAGE, "..", "octave-assembly"))
FIN = os.path.join(PAGE, "fin", "asm")


def between(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


def main():
    s = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
    head = between(s, '<p class="lead" style="max-width:72ch">', "</header>")
    body = between(s, '<div class="cols">', '<div class="lb"')
    lb = between(s, '<div class="lb"', "\n<script>")
    h = head + "\n" + body + lb

    h = h.replace("<section ", "<article ").replace("</section>", "</article>")
    h = re.sub(r'\sid="([^"]+)"', r' id="asm-\1"', h)
    h = re.sub(r'href="#([^"]+)"', r'href="#asm-\1"', h)
    h = re.sub(r'data-s="([^"]+)"', r'data-s="asm-\1"', h)
    h = re.sub(r'class="([^"]+)"', lambda m: 'class="%s"' % " ".join("a-" + c for c in m.group(1).split()), h)
    h = re.sub(r'src="img/([^"]+)"', r'src="fin/asm/\1"', h)
    h = re.sub(r'src="photo/(\w+)\.webp"', r'src="img/bom/\1.jpg"', h)
    h = re.sub(r'data-d="(BRD-[^"]+)"', r'data-d="sch/\1"', h)
    h = re.sub(r'data-d="(d\d\d[^"]+)"', r'data-d="dwg/\1"', h)
    # one <main> per page: the guide's column becomes a div
    h = h.replace('<main data-v3d-src="model/octave.json">', '<div class="a-main" data-v3d-src="fin/asm/octave.json">', 1)
    h = h.replace("</main>", "</div>", 1)

    sec = ('<section class="page" id="p-asm" hidden aria-labelledby="asm-h">\n'
           '<h2 id="asm-h">11 한 옥타브 조립</h2>\n'
           '<p class="a-src">따로 연 페이지: <a href="https://claude.ai/artifact/U6CnesuxwRDptj9u7QfwCY">한 옥타브 조립 가이드</a> '
           '(같은 내용, 작업대에서 휴대폰으로 보기 좋게)</p>\n'
           + h.strip() + "\n</section>\n")
    open(os.path.join(HERE, "section.html"), "w", encoding="utf-8").write(sec)

    os.makedirs(FIN, exist_ok=True)
    assets = []
    for n in sorted(set(re.findall(r'\ssrc="fin/asm/([^"]+)"', sec))):
        shutil.copyfile(os.path.join(SRC, "img", n), os.path.join(FIN, n))
        assets.append("fin/asm/" + n)
    shutil.copyfile(os.path.join(SRC, "model", "octave.json"), os.path.join(FIN, "octave.json"))
    assets.append("fin/asm/octave.json")
    assets += sorted(set(re.findall(r'src="(img/bom/[^"]+)"', sec)))
    assets += sorted(set(re.findall(r'data-d="([^"]+)"', sec)))
    miss = [a for a in assets if not os.path.isfile(os.path.join(PAGE, a))]
    if miss:
        raise SystemExit("asm: missing assets %s" % miss)
    js = open(os.path.join(HERE, "ticks.js"), encoding="utf-8").read().rstrip() + "\n\n" + \
        open(os.path.join(SRC, "viewer3d.js"), encoding="utf-8").read().rstrip() + "\n"
    open(os.path.join(HERE, "script.js"), "w", encoding="utf-8").write(js)
    open(os.path.join(HERE, "assets.txt"), "w", encoding="utf-8").write(
        "# written by build_section.py\n" + "\n".join(assets) + "\n")
    print("asm: section %d bytes, %d assets" % (len(sec.encode()), len(assets)))


if __name__ == "__main__":
    main()
