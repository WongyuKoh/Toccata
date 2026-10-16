"""Builds the tab '02 설계도' (section.html) and copies its runtime files into docs/report/toccata-v4/fin/dwg/.

  python3 docs/report/toccata-v4/src/tabs/dwg/build_section.py

Inputs: hardware/mechanical/cad/drawings/final/*.svg + checks.json (written by hardware/mechanical/cad/src/drawings_final.py),
the reused published copies dwg/d01..d15 (key action, d11 left out) and rear/D01..D05 + R01..R03 (rear unit) of this page.
Outputs: section.html (this folder), ../../../fin/dwg/<the 12 new sheets>.svg + checks.json, assets.txt.
Only this folder and fin/dwg/ are written.
"""
import html
import json
import os
import re
import shutil
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))          # docs/report/toccata-v4
ROOT = os.path.normpath(os.path.join(PAGE, "..", "..", ".."))           # repo root
FINAL = os.path.join(ROOT, "hardware", "mechanical", "cad", "drawings", "final")
FIN = os.path.join(PAGE, "fin", "dwg")
PARTS_DATA = os.path.join(ROOT, "hardware", "mechanical", "cad", "drawings", "parts", "data")

E = html.escape

# code, file, name, scale, paper, what it shows (index), caption (1-3 sentences)
NEW = [
    ("E01", "E01_front.svg", "정면도", "1:2.5 · 확대 1:1, 1:1.5", "A2", "연주자 쪽에서 본 전체, 볼·헤드폰 잭, O4 건반 앞, 화면",
     "연주자 자리에서 본 사용 상태입니다 (1:2.5). 전체 폭 1254 (x−16~1238), 건반 바닥 윗면 z72.85, 스피커 윗면 z144.65, 화면 위 끝 z189.23입니다. "
     "확대 A는 볼 L과 헤드폰 잭 J701 구멍 (5.19 × 6.28, 중심 x−8.34 z20.54), 확대 B는 O4 건반 앞모습 (흰 건반 폭 22.04, 피치 23.5, 검은 건반 머리 폭 10.4), 확대 C (1:1.5)는 화면입니다."),
    ("E02", "E02_rear.svg", "배면도", "1:2.5 · 확대 1:1", "A2", "뒤에서 본 전체, I/O 판 구멍 (KCD1 13.2 × 19.2)·환기 구멍 좌표",
     "뒤에서 본 모습입니다 (1:2.5, 오른쪽 스피커가 왼쪽에 보임). 확대 C (1:1)와 표에 로커 스위치 끼움 구멍 13.2 × 19.2 (뒤판 출력물의 스위치 판 2 mm 관통, 중심 x438.5 z38.5)와 "
     "바깥 테두리 오목 자리 15.4 × 21.4 × 깊이 2, 페달 잭 Ø6.3 (x462.5 z40.5), 루버 54 × 3 × 6, 앰프 뒤 환기 구멍 Ø8 × 10 (x742~841, 간격 11)을 적었습니다."),
    ("E03", "E03_left.svg", "좌측면도", "1:1 · 확대 2:1", "A2", "왼쪽 끝에서 본 옆모습, 깊이·높이·각도",
     "왼쪽 끝에서 본 옆모습입니다 (1:1). 전체 깊이 342.5 = 건반 모듈 212 + 공기 틈 2 + 뒷바 128.5, 스피커 앞판 40°, 화면 25° (경첩 축 y226.55 z81.35). "
     "확대 E (2:1)는 건반 뒤 틈, 케이블 통로 입구, 방진 브래킷입니다."),
    ("E04", "E04_right.svg", "우측면도", "1:1 · 확대 2:1", "A2", "오른쪽 끝에서 본 옆모습",
     "오른쪽 끝에서 본 옆모습입니다 (1:1, 연주자는 왼쪽). 숫자는 E03과 같은 기준이고, 오른쪽 볼·스피커 R 바깥 옆판·브래킷 R이 보입니다."),
    ("E05", "E05_top.svg", "평면도", "1:2.5 · 가운데 1:1.5", "A2", "위에서 본 전체, 뚜껑 배기 홈·나사 자리",
     "위에서 본 사용 상태입니다 (1:2.5). 아래 확대 (1:1.5)는 가운데 유닛 윗면입니다: 뚜껑 L (x260~501), 화면 뚜껑 (x501.5~720.5), 뚜껑 R (x721~962)의 배기 홈과 "
     "화면 뚜껑 나사 자리 Ø6.5 네 곳 (x506·716, y246·322)."),
    ("E06", "E06_bottom.svg", "저면도", "1:2.5 · 가운데 1:1.5", "A2", "아래에서 본 전체, 고무발·흡기 구멍 좌표",
     "아래에서 본 모습입니다 (1:2.5, 연주자 쪽이 위). 고무발 28 × 5 14개의 중심과 가운데 유닛 아랫판 흡기 구멍 Ø8 40개 (강압 컨버터 밑 12 + Pi 5 밑 28)를 "
     "1:1.5 확대와 글에 적었습니다."),
    ("E07", "E07_folded.svg", "화면 접은 상태", "1:2.5 · 단면 1:1", "A2", "운반할 때 (정면·평면·x611 단면)",
     "화면을 접은 운반 상태입니다 (정면·평면 1:2.5, 화면 가운데 x611 단면 1:1). 받침 위 끝은 z95.35로 스피커 윗면 z144.65보다 49.3 낮고, 받침다리는 받침 뒤 클립에 끼웁니다."),
    ("I01", "I01_inside_plan.svg", "내부 평면도", "1:1.5 · 스피커 L 1:1", "A1", "뚜껑·화면·스피커 윗판·앞판을 뗀 안 전체, 번호표",
     "뚜껑 L·R, 화면 뚜껑, 화면, 스피커 윗판·앞판·그릴·가스켓을 뗀 평면입니다 (1:1.5, 스피커 L 안은 1:1). "
     "번호마다 부품 이름, 코드 (06 탭 물건 번호 i····u··, 출력·합판은 03 탭 부품 도면 번호 P-), 수량, 좌표 범위를 오른쪽 표에 적었습니다."),
    ("I02", "I02_centre_detail.svg", "가운데 유닛 내부 상세", "1:1", "A1", "칸 경계, 모든 모듈 좌표, 기둥 P1~P14, y290 단면",
     "가운데 유닛 안을 1:1로 그렸습니다. 칸 A·B·D·E·F 경계, 모든 모듈의 좌표, 보드 받침 기둥 P1~P14의 중심·높이·구멍, 아랫판 흡기 구멍, "
     "y290 단면 (배터리·강압·Pi 5·허브·앰프의 높이)이 있습니다."),
    ("I03", "I03_long_sections.svg", "전체 길이 단면", "1:2.5 · 확대 1:1", "A1", "y67 센서 줄과 y260 스피커 축으로 자른 긴 단면",
     "A-A (y67)는 홀 센서 줄을 따라 자른 건반 전체 단면이고 (1:2.5, 확대 A 1:1), B-B (y260)는 스피커 유닛 가운데를 지나는 단면입니다 (1:2.5, 확대 B 가운데 유닛 1:1). "
     "잘린 면은 빗금, 그 뒤는 보이는 그대로입니다."),
    ("I04", "I04_side_section.svg", "측면 단면 (O4 D 건반)", "1:1", "A2", "건반 액션 + 뒷바 + 가운데 유닛을 한 번에 자른 옆 단면",
     "O4 D 건반 가운데 (x575.75)에서 자른 옆 단면입니다 (1:1). 건반·레버·스프링·센서·제어 기판과 화면 뚜껑·화면·Pi 5·아랫판·뒤판의 앞뒤 관계와 높이를 한 장에 보여 줍니다. "
     "패드 바는 조립 모델(설계 6T) 크기로 그렸고, 뽑는 STL은 구매한 PORON 5T + 펠트 1T에 맞춰 쐐기가 1.0 두껍습니다 (패드 면 위치는 같음, 도면 안 ※ 주)."),
    ("I05", "I05_module_plan.svg", "건반 모듈 내부 평면 (O4)", "1:1", "A2", "건반·레버를 뺀 모듈 안, 모듈 부품 수량",
     "O4 모듈 (x540.5~709)을 위에서 본 내부입니다 (1:1). ①은 건반을 빼고 z54에서 자른 레버·스프링·강철, ②는 레버도 빼고 z30에서 자른 센서 바·센서 기판·제어 기판·"
     "RP2040-Zero·4067·리본·USB입니다. 오른쪽 표는 모듈 하나의 부품 수량입니다."),
]
KA = [
    # n, file, name, index text (short, own text: never cut from the caption), caption
    (1, "d01_white_D_side.svg", "백건 측면 단면 (D)", "백건 D 옆 단면 (모듈 안 x35.25), 쉬는 자세 · 누른 자세",
     "백건 D를 밸런스 핀·자석 중심 (모듈 안 x35.25)에서 자른 옆 단면입니다. 실선은 쉬는 자세, 주황 점선은 끝까지 누른 자세입니다. "
     "확대 A~D에 봉·핀, 캡스턴·스프링, 업스톱, 앞 멈춤 치수가 있습니다."),
    (2, "d02_black_Csharp_side.svg", "흑건 측면 단면 (C#)", "흑건 C# 옆 단면 (모듈 안 x21.22)",
     "흑건 C#를 밸런스 핀·자석 중심 (모듈 안 x21.22)에서 자른 옆 단면입니다. 읽는 법은 도면 1과 같습니다."),
    (3, "d03_octave_plan.svg", "옥타브 모듈 평면도", "C~B 모듈을 z54에서 자른 평면, 레버·핀·패드 바의 y 좌표",
     "C~B 모듈을 z54에서 잘라 위에서 본 평면입니다. 레버 중심, 핀, 패드 바, 기판 자리, y 좌표가 있습니다."),
    (4, "d04_module_cross_sections.svg", "모듈 가로 단면 (레버 구역)", "레버 구역 가로 단면 넷 (y203.25 · y176 · y157.25 등)",
     "레버 구역을 가로로 자른 단면 넷입니다 (레버 봉 y203.25, 패드 가운데 y176, y157.25 등). 핀 둘레 놀음과 기판 위 부품 높이를 봅니다."),
    (5, "d05_white_key_part.svg", "백건 부품도", "백건 부품도 (길이 199, 가로 단면 6, 백건 7종 x 범위)",
     "백건 (D 기준) 부품도입니다. 전체 길이 199, 측면 단면, 평면, 가로 단면 6개와 백건 7종의 x 범위 표가 있습니다."),
    (6, "d06_black_key_part.svg", "흑건 부품도", "흑건 부품도 (길이 144.8, 흑건 5종 x 범위)",
     "흑건 (C# 기준) 부품도입니다. 전체 길이 144.8, 가로 단면과 흑건 5종의 x 범위 표가 있습니다."),
    (7, "d07_lever_carrier_steel.svg", "레버 캐리어 + 강철 블록 부품도", "레버 캐리어 (백·흑 공통)와 강철 블록 9 × 19 × 40",
     "레버 (백·흑 공통 1종)와 강철 블록 9 × 19 × 40의 부품도입니다. 측면 단면, 평면, 가로 단면 7개와 확대 E·F가 있습니다."),
    (8, "d08_frame.svg", "프레임 부품도", "모듈 프레임 (윗판 z72.85) 평면 · 측면 단면 5 · 가로 단면 6",
     "모듈 프레임 한 덩어리 (윗판 z72.85 포함)의 부품도입니다. 평면, 측면 단면 다섯, 가로 단면 여섯과 형상 표가 있습니다."),
    (9, "d09_pad_bar_curtain_spring.svg", "패드 바 · 업스톱 패드 · 가림판 띠 · 비틀림 스프링",
     "패드 바, 업스톱 패드, 가림판 띠, 비틀림 스프링 C-UA90R5-3-0.5",
     "작은 부품입니다: 패드 바, 쐐기 자리, 업스톱 패드 (설계 펠트 1T + 폼 6T), 가림판 띠, 비틀림 스프링 (미스미 C-UA90R5-3-0.5, 다리를 22.3 / 8.0으로 자름). "
     "구매한 업스톱 폼은 PORON 5T라서, 뽑는 패드 바 STL은 쐐기가 1.0 두껍습니다 (패드 면 위치는 같음, I04 주)."),
    (10, "d10_end_parts.svg", "끝 부속 (왼쪽 A0·A#0·B0, 오른쪽 C8)", "끝 부속 왼쪽 · 오른쪽 평면, 건반별 레버 x · 캡스턴 y 표",
     "끝 부속 두 개의 평면, 패드 줄 가로 단면, 끝 패드 바, 건반별 레버 x·캡스턴 y 표입니다."),
    (12, "d12_key_removal.svg", "건반 하나 빼기 순서", "백건 D 하나를 도구 없이 빼는 순서 ⓪~⑤",
     "백건 D 하나를 도구 없이 빼는 단계 ⓪~⑤입니다 (가림판 띠 → 패드 바 → 레버 들기 → 건반 빼기)."),
    (13, "d13_rod_plug_tools.svg", "레버 봉 끝 마개", "레버 봉 Ø4 × 161.4와 두 끝 (출력 마개 · 막힌 구멍)",
     "레버 봉 Ø4 (길이 161.4)가 핀 다섯 장을 지나는 단면과 두 끝 (왼쪽 출력 마개, 오른쪽 막힌 구멍)입니다."),
    (14, "d14_printed_tools.svg", "출력 공구", "출력 공구 넷 (벤치 지그, 높이 블록, 캡스턴 게이지, 핀 높이 게이지)",
     "출력 공구 넷 (벤치 지그 + 높이 블록, 캡스턴 벤치 게이지, 밸런스 핀 높이 게이지)의 실제 치수입니다."),
    (15, "d15_stage0_coupons.svg", "단계 0 시편·지그", "단계 0 시험 키트 출력 부품 34개 (시험 18가지)",
     "단계 0 시험 키트의 출력 부품 34개 (시험 18가지)를 다섯 묶음으로 나눈 부품도입니다."),
]
REAR = [
    # n, stem, name, scale, index text, caption
    (1, "D01_plan", "전체 평면 (뚜껑·화면 뗌)", "1:2.5 · 1:1.5", "뚜껑과 화면을 뗀 평면 (1:2.5), 가운데 유닛 확대 (1:1.5), 안 물건 번호표",
     "뚜껑과 화면을 뗀 평면 (1:2.5)과 가운데 유닛 확대 (1:1.5), 안 물건 번호표입니다. 점선은 스피커·바닥 밑에 숨은 케이블 통로, 고무발, 볼 핀입니다."),
    (2, "D02_speaker_section", "스피커 단면", "1:1 · 5:1", "왼쪽 스피커를 유닛 가운데 (x160.5)에서 자른 단면, 40° 앞판",
     "왼쪽 스피커를 유닛 가운데 (x160.5)에서 자른 단면입니다 (1:1). 40° 앞판, 판, 유닛, 그릴, 케이블 통로, 안 부피, 27° 소리 길 여유 (확대 A 5:1)가 있습니다."),
    (3, "D03_centre_sections", "가운데 유닛 단면 2개", "1:1", "가운데 유닛 옆 단면 둘 (Pi 5 · 화면 / 허브 · 앰프), 흡기·배기 넓이",
     "가운데 유닛을 두 곳에서 자른 옆 단면입니다 (1:1). B-B는 Pi 5와 화면, C-C는 허브와 앰프를 지나고, 흡기·배기 홈 넓이를 적었습니다."),
    (4, "D04_rear_elevation", "뒷면 입면 - I/O 판", "1:2.5 · 2:1", "뒤에서 본 입면 (1:2.5)과 I/O 판 확대 (2:1)",
     "뒤에서 본 입면 (1:2.5)과 I/O 판 확대 (2:1)입니다. 로커 스위치, 페달 잭, 루버의 크기와 중심, XT60 잘못 꽂기 막기 메모가 있습니다."),
    (5, "D05_touchscreen", "터치스크린 (사용 25° / 뒤꿈치 22° / 접은 상태)", "1:1", "터치스크린 옆 단면 (사용 25° · 22° · 접은 상태), 경첩 축",
     "터치스크린 옆 단면입니다 (1:1). 경첩 축, 가장 앞·가장 높은 점, 접은 높이, 모듈 쪽 지킴선이 있습니다."),
    # D06 합판 재단도 dropped 2026-10-16 (A안: every former plywood panel is printed)
]
RENDERS = [("R01", "R01_front.png", "앞 3/4 (사용 상태)"), ("R02", "R02_rear_left.png", "뒤 왼쪽 3/4"), ("R03", "R03_folded.png", "앞 3/4 (화면 접음, 운반)")]


def kb(path):
    return max(1, round(os.path.getsize(path) / 1024))


def img_wh(path):
    """intrinsic size in CSS px, written as width/height on every <img> so the layout is fixed before the lazy images load
    (deep links such as #dwg-i05 or #rd6 land on the sheet). SVG: width/height attributes (mm at 96 dpi) or viewBox; PNG: IHDR."""
    if path.endswith(".png"):
        with open(path, "rb") as fh:
            head = fh.read(24)
        return struct.unpack(">II", head[16:24])
    with open(path, encoding="utf-8") as fh:
        root = re.search(r"<svg\b[^>]*>", fh.read(4096)).group(0)

    def attr(nm):
        m = re.search(r'\s%s="([\d.]+)(mm|px)?"' % nm, root)
        if not m:
            return None
        v = float(m.group(1))
        return v * 96.0 / 25.4 if m.group(2) == "mm" else v
    w, h = attr("width"), attr("height")
    if w is None or h is None:
        vb = [float(t) for t in re.search(r'viewBox="([^"]+)"', root).group(1).replace(",", " ").split()]
        w, h = vb[2], vb[3]
    return int(round(w)), int(round(h))


def ply_rows():
    """D06 piece labels (P1~P6, only used on that sheet) -> part-sheet codes P-PLY-xx of the 03 tab, matched by piece name."""
    s = open(os.path.join(PAGE, "rear", "D06_plywood_cuts.svg"), encoding="utf-8").read()
    texts = [html.unescape(re.sub(r"<[^>]+>", "", t)) for t in re.findall(r"<text[^>]*>(.*?)</text>", s, re.S)]
    pieces = []
    for t in texts:
        m = re.match(r"^(P\d+) (.+?) ×(\d+)\s+\((1:\d+)\)$", t.strip())
        if m and m.group(1) not in [p[0] for p in pieces]:
            pieces.append((m.group(1), m.group(2), int(m.group(3))))
    sheets = []
    for f in sorted(os.listdir(PARTS_DATA)):
        if f.startswith("P-PLY-") and f.endswith(".json"):
            d = json.load(open(os.path.join(PARTS_DATA, f), encoding="utf-8"))
            sheets.append((d["code"], d["name"], d.get("inst", "")))

    def base(nm):
        return re.sub(r"\s+(L·R|L|R)(?=\s|\(|$)", "", nm).replace(" ", "")
    rows = []
    for lab, nm, n in pieces:
        hit = [(c, snm) for c, snm, _ in sheets if base(snm) == base(nm)]
        if len(hit) != n:
            raise SystemExit("D06 %s %s: %d part sheets found, %d expected" % (lab, nm, len(hit), n))
        rows.append((lab, nm, n, hit))
    if sum(len(r[3]) for r in rows) != len(sheets):
        raise SystemExit("D06 pieces do not cover every P-PLY sheet")
    return rows


def zbar(svg_href, png_href=None, save=None):
    links = '<a class="mono" href="%s" target="_blank" rel="noopener">크게 보기 (SVG) ↗</a>' % E(svg_href)
    if png_href:
        links += ' · <a class="mono" href="%s" target="_blank" rel="noopener">PNG ↗</a>' % E(png_href)
    sv = ""
    if save:
        sv = ('<span class="dwg-sv"><button type="button" class="dwg-save" data-file="%s" data-size="%s">SVG 저장</button>'
              '<span class="dwg-msg small" role="status" aria-live="polite"></span></span>' % (E(save[0]), save[1]))
    return ('<span class="zbar" role="group" aria-label="확대"><button type="button" data-z="1" aria-pressed="true">맞춤</button>'
            '<button type="button" data-z="2">2배</button><button type="button" data-z="3">3배</button>%s</span>%s' % (links, sv))


def ply_table():
    trs = []
    for lab, nm, n, hit in ply_rows():
        links = " · ".join('<a class="mono" href="#partdwg-%s">%s</a> <span class="small muted">%s</span>' % (E(c), E(c), E(snm)) for c, snm in hit)
        trs.append('<tr><td class="mono">%s</td><td>%s</td><td class="num">%d</td><td>%s</td></tr>' % (E(lab), E(nm), n, links))
    return ('<div class="tbl dwg-ply" id="dwg-ply"><table><caption class="small">D06 조각 이름 → 03 탭 부품 도면 번호 (합판은 모두 i096 오꾸메 한 장)</caption>'
            '<thead><tr><th>D06 조각</th><th>이름</th><th>수</th><th>03 탭 부품 도면</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(trs))


def figure(fid, title, img_src, alt, caption, svg_href, png=None, save=None, extra_cls=""):
    data = (' data-png="%s" data-svg="%s"' % (E(png), E(svg_href))) if png else ""
    w, h = img_wh(os.path.join(PAGE, img_src))
    return ('<figure class="sheet csheet%s" id="%s"><div class="cap"><span><b>%s</b></span>%s</div>'
            '<div class="dwimg"><img src="%s"%s width="%d" height="%d" alt="%s" loading="lazy" decoding="async"></div>'
            '<figcaption class="small muted">%s</figcaption></figure>'
            % (extra_cls, fid, E(title), zbar(svg_href, png, save), E(img_src), data, w, h, E(alt), E(caption)))


def main():
    os.makedirs(FIN, exist_ok=True)
    assets = []
    for code, f, *_ in NEW:
        shutil.copyfile(os.path.join(FINAL, f), os.path.join(FIN, f))
        assets.append("fin/dwg/" + f)
    shutil.copyfile(os.path.join(FINAL, "checks.json"), os.path.join(FIN, "checks.json"))
    assets.append("fin/dwg/checks.json")
    checks = json.load(open(os.path.join(FINAL, "checks.json"), encoding="utf-8"))
    n_chk = len(checks["checks"])
    n_ok = sum(1 for c in checks["checks"] if c["ok"])

    idx = []
    def row(code, name, scale, paper, what, href):
        idx.append('<tr><td class="mono">%s</td><td>%s</td><td class="mono">%s</td><td class="mono">%s</td><td>%s</td><td><a class="mono" href="#%s">보기</a></td></tr>'
                   % (E(code), E(name), E(scale), E(paper), E(what), E(href)))
    idx.append('<tr class="dwg-ih"><th colspan="6">전체 6방향 · 접은 상태 (새 도면)</th></tr>')
    for code, f, name, scale, paper, what, cap in NEW[:7]:
        row(code, name, scale, paper, what, "dwg-" + code.lower())
    idx.append('<tr class="dwg-ih"><th colspan="6">내부 (새 도면)</th></tr>')
    for code, f, name, scale, paper, what, cap in NEW[7:]:
        row(code, name, scale, paper, what, "dwg-" + code.lower())
    idx.append('<tr class="dwg-ih"><th colspan="6">건반 액션 부품도 (도면 1~15, 11 없음)</th></tr>')
    for n, f, name, what, cap in KA:
        row("도면 %d" % n, name, "도면에 적힘", "-", what, "dwg%d" % n)
    idx.append('<tr class="dwg-ih"><th colspan="6">뒷부분 (D01~D05)</th></tr>')
    for n, f, name, scale, what, cap in REAR:
        row("D%02d" % n, name, scale, "A2", what, "rd%d" % n)
    idx.append('<tr class="dwg-ih"><th colspan="6">렌더 (그림자 넣은 3D 그림)</th></tr>')
    for code, f, name in RENDERS:
        row(code, name, "-", "-", "전체 모습", "dwg-" + code.lower())

    g_ext, g_int, g_ka, g_rear, g_ren = [], [], [], [], []
    for i, (code, f, name, scale, paper, what, cap) in enumerate(NEW):
        href = "fin/dwg/" + f
        fig = figure("dwg-" + code.lower(), "%s · %s (%s, %s)" % (code, name, scale, paper), href, "%s %s" % (code, name), cap, href,
                     save=(href, kb(os.path.join(FIN, f))))
        (g_ext if i < 7 else g_int).append(fig)
    for n, f, name, what, cap in KA:
        href = "dwg/" + f
        g_ka.append(figure("dwg%d" % n, "도면 %d · %s" % (n, name), href, name, cap, href, save=(href, kb(os.path.join(PAGE, href)))))
        assets.append(href)
    for n, stem, name, scale, what, cap in REAR:
        svg, png = "rear/%s.svg" % stem, "rear/%s.png" % stem
        g_rear.append(figure("rd%d" % n, "D%02d · %s (%s)" % (n, name, scale), png, "D%02d %s" % (n, name), cap, svg, png=png,
                             save=(svg, kb(os.path.join(PAGE, svg))), extra_cls=" dwg-pz") + "")
        assets += [svg, png]
    for code, f, name in RENDERS:
        href = "rear/" + f
        w, h = img_wh(os.path.join(PAGE, href))
        g_ren.append('<figure class="sheet dwg-ren" id="dwg-%s"><div class="cap"><span><b>%s · %s</b></span><a class="mono" href="%s" target="_blank" rel="noopener">크게 보기 ↗</a></div>'
                     '<div class="dwimg"><img src="%s" width="%d" height="%d" alt="%s" loading="lazy" decoding="async"></div></figure>'
                     % (code.lower(), code, E(name), E(href), E(href), w, h, E(name)))
        assets.append(href)

    chips = [("ext", "전체 6방향", len(g_ext)), ("int", "내부", len(g_int)), ("ka", "건반 액션", len(g_ka)), ("rear", "뒷부분", len(g_rear)), ("ren", "렌더", len(g_ren))]
    out = []
    out.append('<section class="page" id="p-dwg" hidden>')
    out.append('<h2>02 설계도</h2>')
    out.append('<p class="lede">악기 전체를 여섯 방향에서 본 도면, 안을 보여 주는 내부 도면, 건반 액션 부품도, 뒷부분 도면을 한곳에 모았습니다. '
               '모든 선과 숫자는 출력 STL을 만든 CAD 입체에서 바로 계산했습니다. 단위는 mm이고, 좌표의 기준은 x0 = A0 왼쪽 끝, y0 = 흰 건반 앞 끝, z0 = 책상입니다.</p>')
    out.append('<div class="note">SVG는 A2 (594 × 420) 또는 A1 (841 × 594) 크기라 100 %로 출력하면 적힌 척도가 맞습니다. '
               'CAD에 SVG를 가져올 때는 1 단위 = 1 mm로 가져온 뒤 그 도면의 척도를 곱합니다 (1:2.5면 2.5배). '
               '부품을 그대로 뽑을 때는 도면이 아니라 03 탭의 STL 파일을 씁니다 — 도면의 숫자와 같은 입체입니다.</div>')
    out.append('<div class="kfs">'
               '<div class="kf"><b>12장</b><span>새 도면 E01~E07 · I01~I05</span></div>'
               '<div class="kf"><b>1254 × 342.5</b><span>전체 폭 × 깊이 (mm)</span></div>'
               '<div class="kf"><b>z189.23</b><span>가장 높은 곳 (화면 받침 위 끝)</span></div>'
               '<div class="kf"><b>%d / %d</b><span>도면 숫자와 STL·manifest 대조 일치</span></div></div>' % (n_ok, n_chk))
    out.append('<h3 id="dwg-index"><span class="no">목록</span>도면 목록</h3>')
    out.append('<div class="tbl dwg-idx"><table><thead><tr><th>번호</th><th>이름</th><th>척도</th><th>종이</th><th>무엇을 보여 주나</th><th>바로 가기</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(idx))
    out.append('<details class="spec dwg-chk" id="dwg-checks"><summary>도면 숫자 대조 %d개 (%d개 일치) 보기</summary>'
               '<p class="small muted">도면에 적은 숫자를 지난 빌드가 쓴 stl/assembly·stl/print 파일과 manifest.json의 바깥 상자, 사양 값과 비교한 결과입니다 (허용 차 0.006 mm).</p>'
               '<div class="tbl"><table><thead><tr><th>도면</th><th>숫자</th><th>도면 값</th><th>대조 값</th><th>대조 원본</th><th>결과</th></tr></thead><tbody class="dwg-chkbody">'
               '<tr><td colspan="6" class="muted">열면 불러옵니다.</td></tr></tbody></table></div></details>' % (n_chk, n_ok))
    out.append('<div class="dwg-chips" role="group" aria-label="도면 묶음">%s</div>'
               % "".join('<button type="button" data-grp="%s" aria-pressed="%s">%s <span class="num">%d</span></button>' % (g, "true" if g == "ext" else "false", t, n) for g, t, n in chips))
    out.append('<div class="dwg-grp" data-grp="ext" id="dwg-g-ext"><h3><span class="no">E</span>전체 6방향 (사용 상태) · 접은 상태</h3>'
               '<p class="small muted">밖에서 보이는 것만 그렸습니다 (숨은 선 없음). 가려진 것은 내부 묶음에서 봅니다.</p>%s</div>' % "".join(g_ext))
    out.append('<div class="dwg-grp" data-grp="int" id="dwg-g-int" hidden><h3><span class="no">I</span>내부</h3>'
               '<p class="small muted">뚜껑을 뗀 평면과 단면입니다. 단면의 잘린 면은 빗금이고, 그 뒤는 보이는 그대로입니다.</p>%s</div>' % "".join(g_int))
    out.append('<div class="dwg-grp" data-grp="ka" id="dwg-g-ka" hidden><h3><span class="no">KA</span>건반 액션 부품도 (W1+ r4.5)</h3>'
               '<p class="small muted">좌표 모델 geometry.json에서 그린 도면입니다. 실선은 쉬는 자세, 주황 점선은 끝까지 누른 자세입니다.</p>%s</div>' % "".join(g_ka))
    out.append('<div class="dwg-grp" data-grp="rear" id="dwg-g-rear" hidden><h3><span class="no">D</span>뒷부분 (L2 · 스피커 앞판 40° · 터치스크린 3판)</h3>'
               '<p class="small muted">맞춤·2배는 PNG, 3배는 SVG를 보여 줍니다 (선명함).</p>%s</div>' % "".join(g_rear))
    out.append('<div class="dwg-grp" data-grp="ren" id="dwg-g-ren" hidden><h3><span class="no">R</span>렌더</h3>'
               '<p class="small muted">같은 CAD 입체를 조립 색으로 칠한 그림입니다. 치수는 위 도면에서 읽습니다.</p><div class="dwg-rgrid">%s</div></div>' % "".join(g_ren))
    out.append('</section>')
    with open(os.path.join(HERE, "section.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    with open(os.path.join(HERE, "assets.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(assets) + "\n")
    print("section.html + assets.txt (%d files), fin/dwg: %d files" % (len(assets), len(os.listdir(FIN))))


if __name__ == "__main__":
    main()
