"""Collect the final build files into 최종본/ (2026-10-06).

usage: python3 docs/make_final.py [--pdf]
- Copies the current drawings, print STLs, design docs, assembly guides and deck from their working
  folders into 최종본/02_… ~ 06_… (those folders are wiped and rebuilt; 01_구매목록 is left alone —
  it is written by hardware/bom/final-bom/build_order_xlsx.py).
- Relative links in the copied .md files are rewritten to keep working from the new place.
- --pdf also builds 02_도면/Toccata_도면집_최종.pdf (every sheet at its own size, bookmarks) and
  03_설계서/하드웨어_설계서_v4.pdf. Needs Google Chrome (headless) and pandoc; run outside the sandbox.
The working folders stay the source of truth: change a drawing there, then rerun this script.
"""
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(REPO, "최종본")
MECH = "hardware/mechanical"
KA = MECH + "/key-action-v4"
CAD = MECH + "/cad"
TS = MECH + "/touchscreen/rev3"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MANAGED = ["02_도면", "03_설계서", "04_3D출력_STL", "05_조립·제작", "06_발표자료"]

# (group folder, group title, [(source, title)])
KA_TITLES = ["백건 측면 단면 (D)", "흑건 측면 단면 (C#)", "옥타브 모듈 평면도", "모듈 가로 단면 (레버 구역)", "백건 부품도",
             "흑건 부품도", "레버 캐리어 + 강철 블록 부품도", "프레임 부품도", "패드 바 + 업스톱 패드 + 가림판 띠 + 비틀림 스프링",
             "끝 부속 (왼쪽 A0·A#0·B0, 오른쪽 C8) 평면", None, "건반 하나 빼기 순서", "레버 봉 끝 마개",
             "출력 공구 (벤치 지그 · 높이 블록 · 캡스턴 게이지 · 핀 높이 게이지)", "단계 0 시편·지그"]
KA_FILES = ["d01_white_D_side", "d02_black_Csharp_side", "d03_octave_plan", "d04_module_cross_sections", "d05_white_key_part",
            "d06_black_key_part", "d07_lever_carrier_steel", "d08_frame", "d09_pad_bar_curtain_spring", "d10_end_parts",
            "d11_overall_layout", "d12_key_removal", "d13_rod_plug_tools", "d14_printed_tools", "d15_stage0_coupons"]
SHEETS = [
    ("1_건반액션", "건반 액션 W1+ r4.5",
     [(f"{KA}/drawings/{f}.svg", f"d{i + 1:02d} {t}") for i, (f, t) in enumerate(zip(KA_FILES, KA_TITLES)) if t]),  # d11 = L1·v3 rear bar, replaced by D01·D02
    ("2_본체_뒷부분", "본체 L2 (뒷바·스피커·가운데 유닛)",
     [(f"{CAD}/drawings/{f}.svg", t) for f, t in [
         ("D01_plan", "D01 전체 평면"), ("D02_speaker_section", "D02 스피커 단면 (앞판 40°)"),
         ("D03_centre_sections", "D03 가운데 유닛 단면 2개"), ("D04_rear_elevation", "D04 뒷면 입면 (I/O 판)"),
         ("D05_touchscreen", "D05 터치스크린: 사용 25° / 뒤꿈치 22° / 접은 상태")]]),  # D06 합판 재단도 dropped 2026-10-16 (A안: all panels printed)
    ("3_터치스크린", "터치스크린 3판 (Waveshare 7-DSI-TOUCH-C)",
     [(f"{TS}/drawings/{f}.svg", t) for f, t in [
         ("t01_assembly_side", "t01 조립 옆 단면 (x611)"), ("t02_lid_plan", "t02 가운데 뚜껑 평면"), ("t03_cradle_part", "t03 화면 받침 부품도"),
         ("t04_lid_changes", "t04 가운데 뚜껑 변경 (3a판)"), ("t05_leg_small_parts", "t05 받침다리 · 작은 부품"),
         ("t06_wiring", "t06 배선 (DSI 리본 · 화면 전원)")]]),
    ("4_회로도", "회로도 개정 C",
     [(f"hardware/pcb/{f}.svg", t) for f, t in [
         ("schematic/SCH-01_system", "SCH-01 시스템 연결도"), ("schematic/SCH-02_sensor_board", "SCH-02 옥타브 센서 기판 (SB ×7)"),
         ("schematic/SCH-03_control_board", "SCH-03 제어 기판 (MB)"), ("schematic/SCH-04_end_parts", "SCH-04 끝 부속"),
         ("schematic/SCH-05_pedal", "SCH-05 페달"), ("schematic/SCH-06_power", "SCH-06 전원"), ("schematic/SCH-07_audio", "SCH-07 오디오"),
         ("board/BRD-01_control_board_placement", "BRD-01 제어 기판 배치"), ("board/BRD-02_sensor_board_placement", "BRD-02 센서 기판 배치")]]),
]
COPIES = [  # (source, destination under 최종본) — folders are copied whole
    (f"{CAD}/renders", "02_도면/5_렌더"),
    ("docs/01-hardware-design.md", "03_설계서/01_하드웨어_설계서_v4.md"),
    (f"{MECH}/sound-requirements.md", "03_설계서/02_요구사항_R1-R32_D1-D24.md"),
    (f"{KA}/README.md", "03_설계서/03_건반액션_요약_r4.5.md"),
    (f"{KA}/DESIGN.md", "03_설계서/04_건반액션_설계문서_r4.5.md"),
    ("hardware/pcb/README.md", "03_설계서/05_회로_설명_개정C.md"),
    ("hardware/pcb/netlist/bom.csv", "03_설계서/05_회로_부품표_bom.csv"),
    ("hardware/pcb/netlist/wiring_MB.csv", "03_설계서/05_회로_배선표_wiring_MB.csv"),
    ("hardware/pcb/netlist/cables.csv", "03_설계서/05_회로_케이블표_cables.csv"),
    (f"{TS}/design/CAD_SPEC_rev3.md", "03_설계서/06_터치스크린_사양_rev3.md"),
    ("docs/02-rhythm-game-design.md", "03_설계서/07_리듬게임_기획서.md"),
    (f"{KA}/printables/stage0/stl", "04_3D출력_STL/00_단계0_시험출력"),
    (f"{CAD}/stl/print", "04_3D출력_STL/본출력"),
    (f"{CAD}/stl/print_extra", "04_3D출력_STL/선택·대안·예비"),
    (f"{CAD}/Toccata_출력STL_전체.zip", "04_3D출력_STL/Toccata_출력STL_전체.zip"),
    (f"{CAD}/Toccata_한옥타브_출력STL.zip", "04_3D출력_STL/Toccata_한옥타브_출력STL.zip"),
    (f"{CAD}/Toccata_전체조립.3mf", "04_3D출력_STL/전체조립_보기용/Toccata_전체조립.3mf"),
    (f"{CAD}/Toccata_전체조립.glb", "04_3D출력_STL/전체조립_보기용/Toccata_전체조립.glb"),
    (f"{CAD}/README.md", "05_조립·제작/01_CAD_출력·조립_안내.md"),
    (f"{CAD}/jigs/README.md", "05_조립·제작/02_지그_사용법.md"),
    (f"{KA}/printables/stage0/stage0_procedure.md", "05_조립·제작/03_단계0_시험_절차서.md"),
    (f"{KA}/printables/stage0/stage0_results_template.csv", "05_조립·제작/03_단계0_시험_결과표.csv"),
    (f"{KA}/printables/tools/tools.md", "05_조립·제작/04_출력공구_사용법.md"),
    ("docs/report/Toccata_발표자료_v8.pptx", "06_발표자료/Toccata_발표자료_v8.pptx"),
]


def copy(src, dst, placed):
    s, d = os.path.join(REPO, src), os.path.join(OUT, dst)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    if os.path.isdir(s):
        shutil.copytree(s, d, ignore=shutil.ignore_patterns(".DS_Store", ".claude", "__pycache__"))
    else:
        shutil.copy2(s, d)
    placed[os.path.normpath(src)] = os.path.normpath(dst)


def relink(md_dst, md_src, placed):
    """Rewrite relative links of a copied .md so they resolve from 최종본/<md_dst>."""
    text = open(os.path.join(OUT, md_dst), encoding="utf-8").read()
    sbase, dbase = os.path.dirname(md_src), os.path.dirname(os.path.join("최종본", md_dst))

    def fix(m):
        t = m.group(2)
        if re.match(r"^[a-z]+:", t) or t.startswith("#") or t.startswith("/"):
            return m.group(0)
        path, _, anc = t.partition("#")
        rp = os.path.normpath(os.path.join(sbase, path))
        target = rp
        for s, d in sorted(placed.items(), key=lambda x: -len(x[0])):
            if rp == s or rp.startswith(s + "/"):
                target = os.path.join("최종본", d + rp[len(s):])
                break
        new = os.path.relpath(target, dbase) + ("/" if path.endswith("/") else "")
        return m.group(1) + "(" + new + ("#" + anc if anc else "") + ")"
    text = re.sub(r"(\]|\]\s)\(([^)\s]+)\)", fix, text)
    note = f"> 최종본 사본 (2026-10-06). 원본: `{md_src}` — 고칠 때는 원본을 고치고 `docs/make_final.py`를 다시 돌립니다.\n\n"
    open(os.path.join(OUT, md_dst), "w", encoding="utf-8").write(note + text)


def svg_size(path):
    head = open(path, encoding="utf-8").read(4000)
    tag = re.search(r"<svg[^>]*>", head).group(0)
    w = re.search(r'\swidth="([\d.]+)(mm|px)?"', tag)
    h = re.search(r'\sheight="([\d.]+)(mm|px)?"', tag)
    return f"{w.group(1)}{w.group(2) or 'px'}", f"{h.group(1)}{h.group(2) or 'px'}"


def chrome_pdf(html_text, pdf_path, tmp, timeout=420):
    """Print an HTML page to PDF with headless Chrome in a throw-away profile.
    With a fresh profile Chrome writes the PDF and then may keep running, so poll for the file and stop it
    (same trick as hardware/mechanical/cad/src/drawings.py svg_to_png)."""
    src = os.path.join(tmp, "page.html")
    open(src, "w", encoding="utf-8").write(html_text)
    prof = tempfile.mkdtemp(prefix="tocpdf_", dir=tmp)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                             "--disable-extensions", "--disable-sync", "--disable-background-networking", "--no-pdf-header-footer",
                             "--user-data-dir=" + prof, "--print-to-pdf=" + pdf_path, "file://" + src],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t_end, last, stable = time.time() + timeout, -1, 0
    try:
        while time.time() < t_end:
            if os.path.exists(pdf_path):
                sz = os.path.getsize(pdf_path)
                stable = stable + 1 if (sz > 1000 and sz == last) else 0
                last = sz
                if stable >= 4:
                    break
            elif proc.poll() is not None:
                break
            time.sleep(0.5)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
    if not (os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000):
        raise RuntimeError("Chrome did not write " + pdf_path)


def build_drawing_pdf(tmp):
    """One Chrome run: page 1 = A4 contents, then every sheet on a page of its own size (named @page rules).
    Sheets go in as <img> data URIs so their ids and <style> rules cannot clash."""
    import base64
    import pymupdf
    css, body, toc, rows = [], [], [(1, "표지 · 목차", 1)], []
    page = 2
    for folder, gtitle, sheets in SHEETS:
        toc.append((1, gtitle, page))
        for src, title in sheets:
            w, h = svg_size(os.path.join(REPO, src))
            b64 = base64.b64encode(open(os.path.join(REPO, src), "rb").read()).decode()
            css.append(f"@page p{page}{{size:{w} {h};margin:0}}.p{page}{{page:p{page};width:{w};height:{h}}}")
            body.append(f'<div class="sh p{page}"><img alt="" src="data:image/svg+xml;base64,{b64}" style="display:block;width:{w};height:{h}"></div>')
            toc.append((2, title, page))
            rows.append((gtitle, title, page, os.path.basename(src)))
            page += 1
    trs, last = [], None
    for g, t, p, f in rows:
        if g != last:
            trs.append(f'<tr class="g"><td colspan="3">{html.escape(g)}</td></tr>')
            last = g
        trs.append(f"<tr><td>{html.escape(t)}</td><td class='f'>{html.escape(f)}</td><td class='n'>{p}</td></tr>")
    cover = ('<div class="cv"><h1>Toccata 도면집 (최종)</h1><p class="sub">2026-10-16 · 건반 액션 W1+ r4.5 · 본체 L2 (스피커 앞판 40°, 판 모두 출력) · 터치스크린 3판 · 회로도 개정 E</p>'
             f'<table>{"".join(trs)}</table>'
             '<p class="nt">페이지마다 원래 도면 크기 그대로입니다(본체 D01~D05는 A2, 회로도는 A3, 건반·터치스크린 도면은 화면용 세로 긴 판). '
             'D·SCH·BRD는 100 %로 출력하면 적힌 척도가 맞습니다. 좌표: x 가로(0 = A0 왼쪽 끝), y 흰건반 앞끝에서 뒤로, z 책상에서 위로, 단위 mm. '
             '도면 11(전체 배치 측면)은 L1·v3 뒷바 그림이라 뺐습니다 — 지금 전체 배치는 D01·D02입니다. 원본 SVG는 이 폴더의 1_~4_ 폴더에 있습니다.</p></div>')
    style = ('html,body{margin:0;padding:0}.sh{break-after:page;overflow:hidden}'
             '@page cover{size:A4;margin:16mm}.cv{page:cover;break-after:page;font-family:"Apple SD Gothic Neo",sans-serif;color:#1d2a31;font-size:9.5pt}'
             '.cv h1{font-size:22pt;margin:0 0 4pt;color:#0B3B4F}.cv .sub{color:#5a6b75;margin:0 0 12pt}'
             '.cv table{width:100%;border-collapse:collapse}.cv td{padding:2.2pt 4pt;border-bottom:.5pt solid #d5dee3}'
             '.cv tr.g td{background:#E7EEF2;font-weight:700;color:#0B3B4F;padding-top:5pt}'
             '.cv .f{color:#5a6b75;font-size:8pt}.cv .n{text-align:right;width:28pt}.cv .nt{margin-top:10pt;color:#5a6b75;font-size:8.5pt}'
             + "".join(css))
    doc = f'<!doctype html><meta charset="utf-8"><title>Toccata 도면집</title><style>{style}</style>{cover}{"".join(body)}'
    raw = os.path.join(tmp, "book_raw.pdf")
    chrome_pdf(doc, raw, tmp)
    book = pymupdf.open(raw)
    while len(book) > 1 and not book[-1].get_text().strip() and not book[-1].get_drawings():
        book.delete_page(-1)                                  # trailing blank page from the last page break
    n_cover = 0
    while n_cover < len(book) and abs(book[n_cover].rect.width - 595.3) < 2 and abs(book[n_cover].rect.height - 841.9) < 2:
        n_cover += 1                                          # contents pages are A4; no sheet is A4
    assert n_cover == 1 and len(book) == page - 1, (len(book), n_cover, page - 1)   # contents must fit one A4 page (its page numbers assume it)
    shift = n_cover - 1
    book.set_toc([(lv, t, p if i == 0 else p + shift) for i, (lv, t, p) in enumerate(toc)])
    book.set_metadata({"title": "Toccata 도면집 (최종)", "subject": "2026-10-06", "author": "Toccata"})
    out = os.path.join(OUT, "02_도면", "Toccata_도면집_최종.pdf")
    book.save(out, garbage=4, deflate=True)
    print("도면집", out, len(book), "pages", os.path.getsize(out) // 1024, "KB")


def build_design_pdf(tmp):
    md = os.path.join(REPO, "docs", "01-hardware-design.md")
    body = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", md], check=True, capture_output=True, text=True).stdout
    css = ('@page{size:A4;margin:14mm 13mm}body{font-family:"Apple SD Gothic Neo",sans-serif;font-size:9.6pt;line-height:1.55;color:#1d2a31}'
           'h1{font-size:18pt;color:#0B3B4F}h2{font-size:13.5pt;color:#0B3B4F;border-bottom:1pt solid #0B6584;padding-bottom:2pt;margin-top:16pt}'
           'h3{font-size:11pt}table{border-collapse:collapse;width:100%;margin:6pt 0;font-size:8.6pt}'
           'th,td{border:.5pt solid #c3d0d7;padding:2.5pt 4pt;vertical-align:top}th{background:#E7EEF2}'
           'code{font-family:Menlo,monospace;font-size:8.4pt;background:#f2f5f7;padding:0 2pt}blockquote{color:#4a5a63;margin:6pt 0;padding-left:8pt;border-left:2pt solid #c3d0d7}'
           'a{color:#0563C1;text-decoration:none}tr{break-inside:avoid}')
    doc = f'<!doctype html><meta charset="utf-8"><title>Toccata 하드웨어 설계서 v4</title><style>{css}</style>{body}'
    out = os.path.join(OUT, "03_설계서", "01_하드웨어_설계서_v4.pdf")
    chrome_pdf(doc, out, tmp)
    print("설계서", out)


def main():
    for m in MANAGED:
        shutil.rmtree(os.path.join(OUT, m), ignore_errors=True)
    placed = {}
    for folder, _, sheets in SHEETS:
        for src, _ in sheets:
            copy(src, f"02_도면/{folder}/{os.path.basename(src)}", placed)
            png = src[:-4] + ".png"
            if os.path.exists(os.path.join(REPO, png)):
                copy(png, f"02_도면/{folder}/{os.path.basename(png)}", placed)
    for src, dst in COPIES:
        copy(src, dst, placed)
    placed[os.path.normpath("hardware/bom/README.md")] = "01_구매목록"
    for src, dst in COPIES:
        if dst.endswith(".md"):
            relink(dst, src, placed)
    if "--pdf" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            build_drawing_pdf(tmp)
            build_design_pdf(tmp)
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print("최종본 files:", n)


if __name__ == "__main__":
    main()
