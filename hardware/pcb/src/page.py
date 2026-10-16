"""Builds the '01 회로도' tab (section #p-circuit) of the merged Toccata page, per part, from the built sheets and CSVs.

usage: python3 page.py   (after build.py)
  -> hardware/pcb/page/circuit.html, circuit.css, circuit.js, assets.txt
  -> docs/report/toccata-v4/fin/circuit/*.csv + toccata-circuit-revE.zip.b64.txt (download bundle, base64 because the
     artifact host does not serve .zip)
Sheets are published by merge.py as sch/<name>.svg (it copies hardware/pcb/schematic and board).
"""
import base64
import csv
import html
import io
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as HN  # noqa: E402
import purchase as PU  # noqa: E402
import sheets as S  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ROOT, "..", ".."))
OUT = os.path.join(ROOT, "page")
FIN = os.path.join(REPO, "docs", "report", "toccata-v4", "fin", "circuit")
E = html.escape
REV = "E"
ZIPNAME = "toccata-circuit-revE.zip"


def read_csv(name):
    with open(os.path.join(ROOT, "netlist", name), encoding="utf-8-sig") as f:
        return list(csv.reader(f))


SHEETS_JSON = json.load(open(os.path.join(ROOT, "netlist", "sheets.json"), encoding="utf-8"))
CHK = tuple(sum(v.get("checks", {}).get(k, 0) for v in SHEETS_JSON.values()) for k in ("errors", "overlaps", "board"))


def sheet_src(code):
    return "sch/" + SHEETS_JSON[code]["file"]


def table(header, rows, mono=(), cls=""):
    h = "".join(f"<th>{E(str(c))}</th>" for c in header)
    b = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            c = "" if c is None else str(c)
            cells.append(f'<td class="num">{E(c)}</td>' if i in mono else f"<td>{E(c)}</td>")
        b.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="tbl{(" " + cls) if cls else ""}"><table><thead><tr>{h}</tr></thead><tbody>{"".join(b)}</tbody></table></div>'


def zbar(src, label="크게 보기 (SVG) ↗"):
    return ('<span class="zbar" role="group" aria-label="확대"><button type="button" data-z="1" aria-pressed="true">맞춤</button>'
            '<button type="button" data-z="2" aria-pressed="false">2배</button><button type="button" data-z="3" aria-pressed="false">3배</button>'
            f'<a class="mono" href="{src}" target="_blank" rel="noopener">{label}</a></span>')


def fig(fid, code, title, cap):
    src = sheet_src(code)
    rev = SHEETS_JSON[code]["rev"]
    return (f'<figure class="sheet csheet" id="{fid}"><div class="cap"><span><b>{E(code)} · {E(title)}</b> '
            f'<span class="mono">개정 {E(rev)}</span></span>{zbar(src)}</div>'
            f'<div class="dwimg"><img src="{src}" alt="{E(code + " " + title)}" loading="lazy" decoding="async" width="1680" height="1188"></div>'
            f'<figcaption class="small muted">{E(cap)}</figcaption></figure>')


def crop(fid, code, region, title, cap):
    """part of a sheet: an inline SVG viewBox over the published sheet (href set by circuit.js when the tab is opened)."""
    src = sheet_src(code)
    x0, y0, x1, y1 = SHEETS_JSON[code]["regions"][region]
    w, h = x1 - x0, y1 - y0
    return (f'<figure class="sheet csheet" id="{fid}"><div class="cap"><span><b>{E(code)} · {E(title)}</b> '
            f'<span class="mono">부분</span></span>{zbar(src, "전체 도면 (SVG) ↗")}</div>'
            f'<div class="dwimg crop"><svg viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" role="img" aria-label="{E(code + " " + title)}" '
            f'style="aspect-ratio:{w:.1f}/{h:.1f}"><rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#fff"/>'
            f'<image data-href="{src}" x="0" y="0" width="420" height="297" preserveAspectRatio="none"/></svg></div>'
            f'<figcaption class="small muted">{E(cap)}</figcaption></figure>')


# ------------------------------------------------------------------ BOM rows per part
BOM = read_csv("bom.csv")
BH = BOM[0]


SHOWN = set()


def bom_rows(pred):
    out = []
    for k, r in enumerate(BOM[1:]):
        if pred(r):
            SHOWN.add(k)
            st = r[13] if len(r) > 13 else ""
            out.append([r[2], r[3], r[4], r[7], r[9], r[10], r[11], st])
    return out


def bom_block(fid, title, rows):
    n = len(rows)
    return (f'<details class="spec cbom" id="{fid}"><summary>부품표 — {E(title)} ({n}줄)</summary>'
            + table(["부품", "값", "설명", "전체 수량", "KiCad 심볼", "KiCad 풋프린트", "구매 코드", "구매 상태 (최종 목록)"], rows, mono=(0, 3, 6))
            + "</details>")


def cable_block(part_ids, bought_ids=()):
    by = {h["id"]: h for h in HN.HARNESS}
    rows = []
    for i in part_ids:
        h = by[i]
        cols = " · ".join(f"{c[0]} {c[2]}" for c in h["cond"]) if len(h["cond"]) <= 6 else f"{len(h['cond'])}심 (BRD-06 표)"
        rows.append([i, h["cable"], f"{h['a'][0]} → {h['b'][0]}", HN.path_cell(h), h["cut_txt"],
                     h["shrink"] or "—", cols])
    for b in HN.BOUGHT:
        if b["id"] in bought_ids:
            rows.append([b["id"], b["cable"], f"{b['a']} → {b['b']}", b["path"], "산 그대로 (자르지 않음)", "—", b["note"]])
    return table(["W", "선", "끝 → 끝", "CAD 경로 · 길이 (mm)", "자르는 길이", "수축 튜브", "심 · 넷"], rows, mono=(0, 3))


def notes_block(ids):
    by = {h["id"]: h for h in HN.HARNESS}
    li = []
    for i in ids:
        for n in by[i].get("notes", []):
            li.append(f"<li><b class=\"mono\">{E(i)}</b> {E(n)}</li>")
    return f'<ul class="flow small">{"".join(li)}</ul>' if li else ""


def flow(items):
    return '<ol class="flow">' + "".join(f"<li>{x}</li>" for x in items) + "</ol>"


def part(pid, no, title, qty, what, body):
    return (f'<section class="circ-part" id="{pid}" aria-labelledby="{pid}-h"><h3 id="{pid}-h"><span class="no">{E(no)}</span>{E(title)}</h3>'
            f'<div class="circ-what"><p>{what}</p><span class="pill circ-qty">{E(qty)}</span></div>{body}'
            f'<p class="small circ-top"><a href="#circuit-parts">파트 목록으로 ↑</a></p></section>')


def h4(t):
    return f'<h4 class="sub4">{E(t)}</h4>'


# ------------------------------------------------------------------ pin / terminal tables
def ribbon_rows():
    return [[c[0], "빨간 줄" if c[0] == 1 else "", c[2], "J201." + c[3], "J301." + c[4]] for c in HN.HARNESS[0]["cond"]]


def xh_rows():
    out = []
    for tag, mod, keys in (("EL", "O1", [("A0", "EL_A0", 21), ("A#0", "EL_AS0", 22), ("B0", "EL_B0", 23)]), ("ER", "O7", [("C8", "ER_C8", 108)])):
        pos = {1: ("GND", "—", "—"), 6: ("+3V3_" + tag, "—", "—")}
        for k, (key, net, midi) in enumerate(keys):
            pos[2 + k] = (net, f"C{12+k}", f"{key} = {midi}")
        for n in range(1, 7):
            net, ch, md = pos.get(n, ("(비움)", f"C{10+n}", "—"))
            jpad = {1: "J401.1" if tag == "EL" else "J411.1", 6: "J401.5" if tag == "EL" else "J411.3"}.get(n)
            if tag == "EL" and 2 <= n <= 4:
                jpad = f"J401.{n}"
            if tag == "ER" and n == 2:
                jpad = "J411.2"
            out.append([tag, n, net, jpad or "—", f"{mod} J302-{n}", ch, md])
    return out


def power_terms():
    sw = HN.PTS.get("sw_lugs", {})
    return [["X605 / X606 XT60", "1", "−  (GND)", "KiCad 패드 1 = −. 모양으로 극성이 정해짐, 실물 표시로 확인"],
            ["X605 / X606 XT60", "2", "+  (VBAT)", "빨강 리드"],
            ["F601 ATO 홀더", "−x 꼬리", "VBAT", f"12 AWG, 홀더 끝에서 {HN.STUB12} mm로 잘라(R15 굽힘 뒤에 이음) S1에서 W601 빨강 리드({HN.LEAD_W601} mm)와 이음"],
            ["F601 ATO 홀더", "+x 꼬리", "VBAT_F", f"12 AWG, 홀더 끝에서 {HN.STUB12} mm로 잘라 S3에서 W602a 16 AWG 빨강({HN.W602A_16} mm)과 이음"],
            ["SW601 KCD1-104", "1 / 3", "VBAT_F (입력)", f"단자 열 x{sw.get('x', 443.25):.2f} / {sw.get('x2', 433.75):.2f}, 아래 z{sw.get('z_in', 33.9):.1f} (CAD 가정)"],
            ["SW601 KCD1-104", "2 / 4", "+12V8 (출력)", f"위 z{sw.get('z_out', 43.1):.1f} · 한 회로 짝은 통전으로 확인"],
            ["A602 XL4016", "IN+ / IN−", "+12V8 / GND ★", "IN− = 별 접지점 (전지 −, 앰프 GND)"],
            ["A602 XL4016", "OUT+ / OUT−", "+5V1 / GND", "무부하 5.10~5.15 V로 맞춘 뒤 연결"],
            ["P601 USB-C (C24)", "A4 / A1", "+5V1 / GND", "데이터선은 잘라 막음"],
            ["P602 DC 플러그", "중심 / 슬리브", "+5V1 / GND", "극성 멀티미터 확인"],
            ["A702 XH-A232", "4 VCC / 5 GND", "+12V8 / GND", "PVCC 8~26 V (전지 10.0~14.6 V). VCC·GND는 스피커 단자 반대 가장자리 — 받은 보드로 확인"]]


def audio_terms():
    return [["J701 (헤드폰, 왼쪽 볼)", "T · TN · R · RN · S", "DAC_L · HP_TN_L · DAC_R · HP_RN_R · AGND", "플러그 없음: T–TN, R–RN 닫힘"],
            ["J702 (앰프 입력)", "T · R · S (TN·RN 안 씀)", "HP_TN_L · HP_RN_R · AGND", "T·R·S 다리 → 모음 패드(BRD-07). PJ-313 번호는 판매자마다 달라 글자로 찾음"],
            ["J702 기판 출력", "L · G · R", "AMP_IN_L · AGND · AMP_IN_R", "T → 1 µF ×2(나란히) → L, R → 1 µF ×2 → R, 1 kΩ 출력 → G (약 93 Hz)"],
            ["A702 입력", "1 L · 2 G · 3 R", "AMP_IN_L · AGND · AMP_IN_R", "W707"],
            ["A702 출력", "6 L+ · 7 L− · 8 R+ · 9 R−", "SPK_L_P · SPK_L_N · SPK_R_P · SPK_R_N", "BTL — − 선을 GND에 묶지 않음. 4개 모두 한 가장자리에 한 줄"],
            ["X703~X706 XT60 SPK", "1 − · 2 +", "SPK_x_N · SPK_x_P", "파랑 수축 + SPK"]]


def ts_terms():
    return [["A603 Pi 5 40핀 헤더", "2 (5 V) · 6 (GND)", "+5V_PI · GND", "4번 5 V는 안 씀"],
            ["P603 · X601 (W606 F/F 끝)", "1 빨강 · 2 검정", "+5V_PI · GND", "헤더 핀 2·6에 꽂음"],
            ["X602 · X603 (W607 M/M 끝)", "1 빨강 · 2 검정", "+5V_PI · GND", ""],
            ["X604 (동봉선 2.54 3핀)", "1 빨강 · 2 빈 칸 · 3 검정", "+5V_PI · NC · GND", "받으면 통전으로 확인"],
            ["P604 → A605 (MX1.25 2핀)", "1 · 2", "+5V_PI · GND", "우리 번호 (빨강 = 1)"],
            ["W605 DSI FFC", "1 ↔ 1 … 22 ↔ 22", "DSI · I2C (터치)", "Pi 5 CAM/DISP 1 ↔ A605, B형(반대면)"]]


CHECKS = [
    ("전지 BT601", "무부하 전압 약 13.0~13.4 V (10 V 아래면 쓰지 않음). 라벨로 BMS(4S, 저전압 차단 약 10 V, 연속 5 A 이상)를 확인. 처음 다 쓸 때 꺼지기 직전 버스 전압을 적어 둔다."),
    ("XT60 극성·색", f"W601을 만든 뒤 빨강 = +인지 멀티미터로. 홀더 −x 끝에서 XT60 뒤끝까지 이은 길이가 {HN.W601_MAX} mm 이하인지 자로 잰다(꼬리 {HN.STUB12} + 리드 {HN.LEAD_W601} − 겹침 10 ≈ {HN.W601_TOTAL}). 전원 XT60(팩 리드·W601·벤치 L81) = 빨강 수축, 스피커 XT60(X703~X706) = 파랑 수축 + ‘SPK’. 스피커 XT60에 전원을 꽂지 않는다."),
    ("ATO 퓨즈 홀더", f"5 A ATO(주황, 표준 칼날 — 미니 아님)가 들어가는지. 12 AWG 꼬리 두 개가 홀더 끝에서 {HN.STUB12} mm보다 긴지(둘 다 {HN.STUB12} mm로 잘라 R15 굽힘 뒤에서 16 AWG와 이음). 받침 2개에 꼭지가 눌러 끼워지는지(CAD 가정 꼭지 Ø8)."),
    ("KCD1-104", "켬 상태에서 0 Ω인 단자 짝 두 개(= 두 회로)를 찾는다. 짝의 한쪽끼리(입력), 다른 쪽끼리(출력)를 W602j로 묶고, 끈 상태에서 입력–출력이 열려 있는지 확인. 스위치를 10번 켜고 끄며 BMS가 끊기지 않는지(R12)."),
    ("XL4016", "무부하로 5.10~5.15 V에 맞추고 가변저항을 고정한 뒤 연결. C24 빨강 = +, 허브 플러그 중심 = + 확인."),
    ("PJ-313 ×3", "플러그 없음: T–TN, R–RN 닫힘. 다섯 다리의 글자(T·TN·R·RN·S)를 통전으로 찾아 표시한다. 다리 간격이 2.54가 아니면 BRD-07 잭 자리(점선)에서 구부리거나 구멍을 Ø1.3으로 넓힌다."),
    ("RP2040-Zero ×8", "LDO 표시(5핀 RT9013·ME6217)를 본다. O1 3V3 전류 60~130 mA. 부팅이 불안하면 XOSC 지연 64. USB-C가 오른쪽 모서리에서 4.67 mm인지 재 본다."),
    ("USB-A → C ×8", "산 선을 자리별로 나눈다: NA993 1 m ×2 → W201·W202, HB466 50 cm ×6 → W203~W208. W205·W206은 CAD 0.3 m 자리라 남는 약 20 cm를 통로에서 묶는다. 데이터선인지(BOOTSEL로 RPI-RP2 드라이브가 뜨는지) 본다. C 쪽 몰드 ≤ 12.5 × 7.6 × 25 (W1 시험 19)."),
    ("Adafruit 4876 ×2", "플러그 선·소켓 선의 하우징 번호 1~6을 양쪽 끝에서 통전으로 맞춘다(선 색은 공개되지 않음). 1 = GND, 6 = 3V3로 쓴다."),
    ("센서", "자석 없이 OUT 1.59~1.71 V, S극을 표시면에 가까이 하면 오른다. 건반을 얹은 쉼 백 ≈1.78 · 흑 ≈1.72 V, 바닥 백 ≈2.31 · 흑 ≈2.39 V (±10 %). EXT를 빼면 0.15 V 아래."),
    ("페달", "꽂은 상태 링–슬리브 3.05 V 이상, 뺀 상태 GP26 약 0 V."),
    ("앰프 XH-A232", "스피커 단자 L+·L−·R+·R−가 한 가장자리, VCC·GND가 반대 가장자리인지 보고 W602c·W703·W705의 남는 선(50 mm 여유)을 앰프 옆에서 묶는다. 36 dB 이득 확인(칩 5·6번 핀 > 2 V). 소프트웨어 음량 상한은 최대 출력 약 8 W/ch(입력 약 0.13 Vrms)에서 찌그러지지 않게. 스피커 Re 6~7 Ω(4 Ω 판매분 주의)."),
    ("허브 710U3", "10포트 중 1개는 충전 전용, 포트마다 ON/OFF 스위치. ① 충전 전용 포트를 찾는다(표시, 또는 Zero 하나를 꽂아 장치로 안 보이는 포트). ② 그 포트가 0·1번이면 그대로, 2~9번이면 그 보드를 1번(또는 0번)으로 옮기고 아래 '허브 포트 옮김' 표로 선 길이를 본다. ③ 쓰는 8개 포트 스위치를 켠다. ④ Pi 선을 뺐을 때 Pi 5 V 핀 0 V(역급전 없음). 딸린 DC 플러그가 잭 면에서 32 mm보다 길면 ㄱ자 DC 플러그 선이 필요."),
    ("화면", "동봉선 2.54 3핀 = 1 빨강 · 2 빈 칸 · 3 검정인지 통전 뒤 점퍼 연결. 최대 부하에서 vcgencmd get_throttled = 0x0. config.txt: " + S.DISP["overlay"] + "."),
]

CHANGES = [
    ("A", "2026-09-28", "첫 판: 센서·제어·끝 부속·페달·전원·오디오 회로 + 배치 2장 (△1~△12: 10 µF 추가, EXT 풀다운·직렬 1 kΩ, R503 20 Ω, 별 접지, AGND 분리 등)"),
    ("B", "2026-09-29", "W1 r4.5 기구와 대조 (△13~△15): EL·ER 1 kΩ을 1206 칩으로, 제어 기판 고정 = 매단 보스 + 밑에서 M3×6, 제로 x75.14 (USB 가운데 = 선반 홈 가운데)"),
    ("C", "2026-10-01", "터치스크린 Waveshare 7-DSI-TOUCH-C (△16): Pi 헤더 2·6번 → 점퍼 2단 → 동봉선, DSI FFC 22핀 B형"),
    ("D", "2026-10-07", "전원 입력을 LiFePO4 12.8 V 전지로 (△17), 스피커 접속도 XT60 + 색 표시 (△18)"),
    ("E", "2026-10-08", "최종 구매에 맞춤 + 기판·배선 도면 6장 추가 (△19~△26) + 2차 검토 고침 (△27~△30, 아래)"),
]
DELTA_E = [
    ("19", "SCH-05 · BRD-03", "PB에 W502 패드 J502(1×4: T·TN·R·S). 페달 잭 J501은 뒤판 출력물 위 자기 조각에", "KiCad PB 프로젝트에 선 받을 자리가 필요"),
    ("20", "SCH-06 · BRD-05", "SW601 = KCD1-104(DPST) 두 회로 나란히(1+3 입력, 2+4 출력, W602j). F601 = 5 A ATO, 사용자 ATC/ATO 홀더. P601 = C24 BT663", "사용자 보유 부품으로 바뀜"),
    ("21", "SCH-07 · BRD-05", f"W707(J702 기판 → 앰프 입력 L·G·R)에 번호. W701·W702 = BC256 3 m 한 가닥을 반으로, W701은 플러그 뒤끝에서 {HN.W701_CUT / 1000:.1f} m로 자르고 남는 토막에서 W707", "빠져 있던 선, 최종 구매"),
    ("22", "BRD-03", "페달 보드 배치를 지그 P-PED 격자에. A501은 CAD 상자보다 x −0.55 · y −1.62 (핀이 구멍에 들어가는 가장 가까운 자리)", "BE163 격자"),
    ("23", "BOM · BRD-01·06", "MB·PB = BE163 조각, SB·EL·ER·자투리 = 12 × 18 기판, EXT = Adafruit 4876 짝, 10 µF = 삼성 CL31A106KOHNNNE, USB 선은 1 / 0.5 / 0.3 m (CAD)", "최종 구매 목록 (plan C) · CAD"),
    ("24", "BRD-07", "작은 기판 J702·J501·PS의 구멍·배선을 2.54 격자에 그리고 SCH-05·07과 자동 대조. J702는 잭 T·R 다리 → 1 µF → 출력(TN·RN 비움). J701은 기판 없이 볼 포켓에서 다리에 직접 납땜", "검토: J702 메모가 1 µF를 TN·RN에 잇게 적혀 있었음 (앰프 무음)"),
    ("25", "SCH-06·07 · BRD-04·05", f"W601: 홀더 −x 끝 → XT60 뒤끝 전체 {HN.W601_MAX} mm 이하 = 꼬리 {HN.STUB12} + 리드 {HN.LEAD_W601} − 겹침 10 (잘못 꽂기 방지 여유 유지). W602c·W703·W705 +50 mm (앰프 단자는 한 가장자리)", "검토: 리드만 68 mm로 자르면 왼쪽 스피커 XT60에 닿을 수 있음"),
    ("26", "BRD-02 · BRD-08", "SB OUT → J201 12가닥, MB 아랫면 49가닥을 격자 위 경로로(납땜 패드 위를 지나지 않음, 검사). BRD-08 = MB 아랫면 거울상", "검토: 점 대 점 목록만으로는 다른 넷 패드 위를 지나는 선이 있었음"),
    ("27", "BRD-02 · wiring_SB.csv", "SB에 J201 전원 4가닥: J201.1·16 → 3V3 버스(y64.46), J201.2·15 → GND 버스(y67.00). 반 칸 기둥으로 OUT 줄과 GND 버스를 구멍 사이로 건넘. 확인 'J201.1/16 ↔ 센서 핀 1 = 0 Ω, J201.2/15 ↔ 핀 2 = 0 Ω'. OUT 짝수 핀 6가닥도 y70.81 줄로 와서 J201 옆에서만 뒤 리브 띠(y73.2~75.5, 틈 x59~82)에 들어가게 다시 그림", "검토: 리본의 3V3·GND가 J201까지만 오고 센서 버스에 이어지지 않았음 (센서 84개 무전원). 짝수 핀 선이 받침 리브 위(y73.35)를 지나 기판이 뜰 뻔함"),
    ("28", "BRD-03 · BRD-07", "피복 가닥은 두 끝에서만 잇는다: PB GP26 → R501.1 → C501.1, R501.2 → R502.2 → J502.1 → TP501(맨선), J502.4(슬리브) → GND 맨선. J702 C703.1 → R702.1 → W707 R. 배선 검사가 피복 가닥을 끝에서만 잇고 넷마다 한 덩어리인지 봄", "검토: 가닥 중간의 패드가 이어지지 않아 GP26에 페달 신호가 안 가고 잭 슬리브가 GND에 안 붙었음"),
    ("29", "SCH-07 · BRD-04·05", f"W701 경로 = CAD 약 {HN.W701_PATH:.0f} mm(볼 홈 → 통로 → 동글) → 플러그 뒤끝에서 {HN.W701_CUT / 1000:.1f} m로 자름, 남는 토막에서 W707. W702 경로 약 {HN.W702_PATH:.0f} mm(1.5 m 그대로)", "검토: '약 0.7 m' 경로와 0.9 m 자르기는 플러그를 빼면 짧았음"),
    ("30", "SCH-06 · BRD-04·05", f"12 AWG 홀더 꼬리 둘 다 {HN.STUB12} mm(R15 굽힘 23.5 + 이음 자리 12) — 이음이 굽힘 뒤에. W602a 16 AWG {HN.W602A_16} mm, W601 리드 {HN.LEAD_W601} mm(전체 약 {HN.W601_TOTAL} ≤ {HN.W601_MAX}), 검정 연장 {HN.BLACK_EXT} mm", "검토: 꼬리 24 + 95 − 겹침 10은 KCD1 탭에 3~6 mm 모자라고 이음이 R15 굽힘 안에 들어감"),
]


def kicad_steps():
    return flow([
        "<b>프로젝트를 보드별로</b>: octave-sensor(SB), octave-control(MB), end-parts(EL·ER), pedal-board(PB + J501 조각), pedal-sensor(PS), amp-input(J702 기판), 문서용 cu-wiring(전원·오디오·화면 — 모두 보드 밖). 한 PCB에 7장을 넣지 않는다.",
        "<b>라이브러리</b>: 부품표의 KiCad 심볼·풋프린트 열을 따른다. 직접 만들 것 = Toccata:CD74HC4067_Breakout, PJ-313 풋프린트(패드 이름 T/TN/R/RN/S, 다리 자리는 받은 잭으로), 모듈 심볼(XL4016, XH-A232, 동글, RaspberryPi5 헤더 유닛, Waveshare 7-DSI-TOUCH-C), 전원 심볼 +12V8 · +5V1 · +5V_PI · +3V3_EL · +3V3_ER.",
        "<b>RP2040-Zero</b> = dj505/RP2040-Zero-KiCAD 심볼과 같은 라이브러리의 풋프린트를 복사해 드릴만 1.0 mm로(패드 번호 = 이 도면). 다른 라이브러리 풋프린트는 패드 번호가 다를 수 있어 쓰지 않는다. 3V3 핀은 power_out. DRV5055 = Sensor_Magnetic:DRV5055A2xLPGxQ1, Value DRV5055A2QLPG.",
        "<b>번호</b>: Annotate → First free after sheet number × 100, X 위치순 — 이 도면과 같은 번호가 나온다. R503은 KiCad에서 한 부품(Value 20R), 실물은 100 Ω 5개.",
        "<b>ERC</b>: 선으로 들어오는 전원(SB +3V3, +3V3_EL·_ER, PB의 +3V3 출력, PS의 PED_VCC, +12V8, +5V1, +5V_PI, 각 GND)에 PWR_FLAG. GND는 로컬 라벨이 아니라 전원 심볼.",
        "<b>SW601</b> = Switch:SW_DPST(1–2 회로 A, 3–4 회로 B)를 입력 1·3, 출력 2·4로 묶는다. 맞물린 커넥터(&gt;&gt;)는 KiCad에서 연결이 아니므로 양쪽 핀에 같은 넷 이름.",
        f"<b>외곽·구멍</b>: 제어 기판 = BRD-01 (홈 x{S.MB['slot'][0]:.2f}~{S.MB['slot'][1]:.2f} × y≤{S.MB['slot'][3]}, 금지 x{S.MB['keep'][0]:.2f}~{S.MB['keep'][1]:.2f} × y≤{S.MB['keep'][3]}), 센서 기판·끝 부속 = BRD-02, 페달 보드 = BRD-03(구멍 표 pads_PB.csv), J702·J501·PS = BRD-07(pads_small.csv). 격자는 2.54, 모든 구멍 좌표가 표에 있다.",
        "<b>배선 확인</b>: KiCad 넷리스트를 netlist.csv(그린 도면에서 다시 계산한 값)와 비교한다. 만능기판 배선은 wiring_MB.csv(BRD-08) · wiring_SB.csv · wiring_PB.csv · wiring_small.csv의 경로(꺾인 점 좌표).",
    ])


FILES = [("bom.csv", "부품표 (KiCad 심볼·풋프린트·구매 상태)"), ("netlist.csv", "넷리스트 (도면·보드·넷·부품·핀)"),
         ("harness.csv", "선 심 하나하나 (양 끝 핀·색·자르는 길이)"), ("cables.csv", "선 목록 W (USB 선은 선마다 길이)"),
         ("wiring_MB.csv", "제어 기판 아랫면 배선 (꺾인 점, BRD-08)"), ("wiring_SB.csv", "센서 기판 OUT → J201 배선"),
         ("wiring_PB.csv", "페달 보드 아랫면 배선"), ("pads_PB.csv", "페달 보드 구멍 좌표"),
         ("wiring_small.csv", "J702·PS 배선 (BRD-07)"), ("pads_small.csv", "J702·J501·PS 구멍 좌표 (BRD-07)"),
         ("pins_rp2040.csv", "RP2040-Zero 패드 → 넷 (MB · PB)"), ("mux_map.csv", "먹스 채널 → 건반·MIDI"),
         ("id_jumpers.csv", "ID 점퍼 · USB 이름 · 허브 포트"), ("sb_sensors.csv", "센서 자리"), ("mux_module_pins.csv", "4067 모듈 핀"),
         ("rp2040_zero_pads.csv", "RP2040-Zero 구멍 좌표")]


def build():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIN, exist_ok=True)
    SHOWN.clear()
    net = read_csv("netlist.csv")
    named = {r[2] for r in net[1:] if not r[2].startswith("(이름 없음")}
    pins_z = read_csv("pins_rp2040.csv")
    muxm = read_csv("mux_map.csv")
    idj = read_csv("id_jumpers.csv")
    sbs = read_csv("sb_sensors.csv")
    pads_pb = read_csv("pads_PB.csv")
    wpb = read_csv("wiring_PB.csv")
    wmb = read_csv("wiring_MB.csv")
    wsb = read_csv("wiring_SB.csv")
    psm = read_csv("pads_small.csv")
    wsm = read_csv("wiring_small.csv")
    muxp = read_csv("mux_module_pins.csv")
    B = S.budget()
    n_sheets = len(SHEETS_JSON)
    n_sch = sum(1 for k in SHEETS_JSON if k.startswith("SCH"))
    n_cab, n_rows = HN.wire_count()
    usb_txt = HN.usb_group_txt() + " · W208 " + HN.m_txt(HN.USB_BUY.get("PED", 0.5))
    body_parts = []

    # ---------------- 시스템
    body = (fig("circuit-sch-01", "SCH-01", "시스템 연결도", "모든 파트·보드와 선(W 번호), 선 목록. 파트 사이는 모두 꽂았다 빼는 커넥터(R26). USB 선 옆 숫자 = 선 길이.")
            + h4("USB 장치와 허브 포트")
            + table(["보드", "JP301 GP6", "JP302 GP7", "JP303 GP8", "GP14 점퍼", "USB 이름", "C 건반 MIDI", "허브 포트"], idj[1:], mono=(0, 7))
            + '<p class="small muted">허브 포트 번호는 −x 끝(Pi 쪽)부터 0~9, 0·1은 비움 (CAD cable_duct.hub.port_map). 동글은 허브를 거치지 않고 Pi에 바로(X701).</p>'
            + h4("허브 포트 옮김 (충전 전용 포트가 2~9번일 때)")
            + '<p class="small">710U3는 10포트 중 1개가 충전 전용이라 그 포트에 꽂은 보드는 장치로 보이지 않습니다. 충전 전용 포트가 2~9번이면 그 보드를 1번(또는 0번)으로 옮깁니다. '
              '옮긴 뒤 길이는 CAD 경로에서 가로 길이만 바꾼 추정이고, 선 길이 − 40 mm보다 길면 더 긴 선으로 바꿉니다. 쓰는 8개 포트의 스위치는 켭니다.</p>'
            + table(["W", "보드", "지금 포트", "선", "CAD 길이 (mm)", "한계 (선 − 40)", "1번 포트로 옮기면", "0번 포트로 옮기면"], HN.hub_move_rows(), mono=(0, 2, 4, 5, 6, 7))
            + h4("산 그대로 꽂는 선")
            + cable_block([], tuple(b["id"] for b in HN.BOUGHT if b["part"] in ("mb", "pwr", "ts", "aud") or b["id"] == "W208"))
            + bom_block("circuit-sys-bom", "시스템 (USB 선)", bom_rows(lambda r: r[2] in ("W201~W208",))))
    body_parts.append(part("circuit-sys", "A", "시스템 연결", f"보드 6종 · 선 {n_cab}가닥",
                           "건반 모듈 7개의 제어 기판과 페달 보드가 USB-MIDI 장치가 되어 허브에 모이고, 허브는 Pi 5로 갑니다. Pi 5가 소리를 만들어 USB 동글 → 헤드폰 잭 → 앰프 → 스피커로 보냅니다. 전원은 가운데 유닛의 LiFePO4 전지 하나입니다.",
                           body))

    # ---------------- 센서 기판 SB
    wsb_rows = [[r[0], r[1], r[2], f"({r[3]}, {r[4]})", f"{r[5]} ({r[6]}, {r[7]})", r[8], r[9], r[10]] for r in wsb[1:]]
    n_sb_out = sum(1 for r in wsb[1:] if r[0].startswith("U"))
    n_sb_pwr = len(wsb) - 1 - n_sb_out
    body = (fig("circuit-sch-02", "SCH-02", "옥타브 센서 기판 (SB ×7)", "DRV5055A2 ×12 (U201~U212, 핀 1 VCC · 2 GND · 3 OUT), 센서마다 100 nF, 버스 양 끝 10 µF, 리본 16심 2×8 블록 J201.")
            + crop("circuit-brd-02-sb", "BRD-02", "sb", "센서 기판 배치 (SB)", "161.6 × 15.24 띠: 센서 리드 구멍 열, 3V3·GND·OUT 행, 100 nF·10 µF 자리(아랫면), 리본 블록, OUT → J201 배선(파란 점선)과 J201 전원 4가닥(빨강 = 3V3, 검정 = GND), 고정 U홈. 모듈 좌표 mm.")
            + bom_block("circuit-sb-bom", "SB 한 장 (×7)", bom_rows(lambda r: r[0] == "SCH-02"))
            + h4("센서 자리와 채널")
            + table(["센서", "건반", "소자 x", "리드 구멍 x", "100 nF", "넷", "먹스 채널", "리본 심"], sbs[1:], mono=(0, 2, 3, 4, 5, 6, 7))
            + h4(f"J201 배선 (아랫면 피복 단선 {n_sb_out + n_sb_pwr}가닥 = OUT {n_sb_out} + 전원 {n_sb_pwr}, wiring_SB.csv)")
            + '<p class="small muted">J201: 1번 = 앞줄 왼쪽, 홀수 = 앞줄 y72.08 · 짝수 = 뒷줄 y74.62, 핀 x = 61.59 + 2.54·⌊(n−1)/2⌋. OUT 선은 모두 반 칸 줄 y70.81을 나란히 눕혀 오고, 짝수로 가는 선은 핀 바로 옆 반 칸 기둥에서 앞줄을 구멍 사이로 건너 반 칸 줄 y73.35로 1.27만 갑니다. '
              '기판은 받침 리브(앞 y61.0~62.8, 뒤 y73.2~75.5 — 뒤는 x59~82만 열림) 위에 바로 놓이므로 리브 띠 위에는 아랫면 선이 없어야 합니다(BRD-02 점선 띠, 자동 검사). '
              '<b>전원 4가닥</b>: J201.1·16(3V3) → 3V3 버스, J201.2·15(GND) → GND 버스. 리본의 3V3·GND는 이 4가닥으로만 센서 버스에 이어집니다. 3V3 가닥은 GND 버스를 구멍 사이(반 칸)로 건너고, 끝은 버스가 지나는 빈 구멍에서 버스와 함께 납땜합니다.</p>'
            + table(["선 (센서 / 버스)", "건반", "넷", "시작 구멍 (x, y)", "J201 핀 (x, y)", "줄", "경로 (꺾인 점)", "길이"], wsb_rows, mono=(0, 2, 3, 4, 6, 7))
            + h4("리본 W101~W107 심 배정 (J201 ↔ J301, 같은 번호)")
            + table(["심", "표시", "넷", "SB", "MB"], ribbon_rows(), mono=(0, 2, 3, 4))
            + h4("선") + cable_block(["W101~W107"]) + notes_block(["W101~W107"])
            + h4("만드는 순서와 확인")
            + flow(["12 × 18 양면 만능기판에서 6행 띠 161.6 × 15.24를 자른다(x1.0~162.6 — 오른쪽 턱 기둥과 0.4).",
                    "아랫면 먼저: 센서마다 100 nF 1206(3V3–GND 패드 사이), 버스 양 끝 10 µF(C213 x8.25, C214 x158.11). 아랫면 부품·납땜 ≤ 1.8 mm.",
                    "3V3(y64.46)·GND(y67.00) 버스를 아랫면 주석선으로 x8.25~160.65. OUT(y69.54) → J201은 위 표의 경로대로 피복 단선 12가닥, 이어서 J201 전원 4가닥(J201.1·16 → 3V3 버스, J201.2·15 → GND 버스).",
                    "센서: 표시면을 위로 눕혀 리드를 +x로, 1.40~3.44 mm에서 2.54 간격으로 벌려 꺾어 구멍(소자 x + 3.0 이상 첫 격자)에 꽂는다. 납땜 뒤 다리 1 mm 아래로.",
                    "리본 16심을 J201에 아랫면 납땜(1번 = 빨간 줄 = 앞줄 왼쪽).",
                    "확인: 3V3–GND 단락 없음, J201.1·J201.16 ↔ U201 핀 1 = 0 Ω, J201.2·J201.15 ↔ U201 핀 2 = 0 Ω, J201 핀 n과 센서 OUT 사이 0 Ω(표) → 3.3 V 넣고 자석 없이 OUT 1.59~1.71 V, S극을 가까이 하면 오름."]))
    body_parts.append(part("circuit-sb", "B", "센서 기판 SB", "×7 (모듈마다 1장)",
                           "건반 12개 밑 자석의 거리를 홀센서 DRV5055 12개가 전압으로 바꿉니다. 출력 12선과 3V3·GND 두 가닥씩을 16심 리본으로 제어 기판에 보냅니다.", body))

    # ---------------- 제어 기판 MB
    zr = [[r[0], r[1], r[2], r[3], r[4], r[6], r[7], r[8]] for r in pins_z[1:]]
    body = (fig("circuit-sch-03", "SCH-03", "옥타브 제어 기판 (MB ×7)", "RP2040-Zero(A301)가 4067 모듈(A302)의 SIG를 GP26(ADC0)로 읽고 GP2~GP5로 채널을 고른다. GP6~GP8 ID 점퍼, GP14 PED 점퍼, EXT 풀다운, 테스트 포인트.")
            + fig("circuit-brd-01", "BRD-01", "제어 기판 배치 (MB, 위에서 봄)", "BE163에서 자른 70 × 50: 모든 구멍 = 제로 핀 격자(x = 76.52 + 2.54i, y = 173.59 + 2.54j). W1 홈·금지 구역·매단 보스·바닥 구멍.")
            + fig("circuit-brd-08", "BRD-08", "제어 기판 아랫면 배선 (아래에서 봄, 거울상)", f"피복 단선 {len(wmb) - 1}가닥을 1.27 격자 위 경로로: 납땜 패드·금지 구역·나사 머리 위를 지나지 않고 두 선이 한 칸을 같이 쓰지 않음(자동 검사). 선 번호 = 아래 표.")
            + bom_block("circuit-mb-bom", "MB 한 장 (×7, 실장 조건 열 참고)", bom_rows(lambda r: r[0] == "SCH-03"))
            + h4("RP2040-Zero 패드 → 넷 (MB 7장 공통)")
            + table(["패드 dj505", "WS P1", "이름", "가장자리", "MB 넷", "헤더", "구멍 x", "구멍 y"], zr, mono=(0, 1, 2, 6, 7))
            + h4("먹스 채널 → 건반 (펌웨어 표, MIDI 번호)")
            + table(muxm[0], muxm[1:], mono=tuple(range(8)))
            + h4("ID 점퍼 (닫음 = GND 납땜 브리지 = 1)")
            + table(idj[0], idj[1:], mono=(0, 7))
            + f'<details class="spec cbom" id="circuit-mb-wire"><summary>아랫면 배선 경로 (wiring_MB.csv, {len(wmb) - 1}가닥 — BRD-08 번호)</summary>'
            + table(wmb[0], wmb[1:], mono=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)) + "</details>"
            + '<details class="spec cbom" id="circuit-mb-mux"><summary>4067 모듈 핀 (심볼 핀 ↔ 모듈 헤더)</summary>' + table(muxp[0], muxp[1:], mono=(0, 3)) + "</details>"
            + h4("선") + cable_block(["W101~W107", "W403", "W413"], tuple("W20%d" % k for k in range(1, 8)))
            + h4("만드는 순서와 확인")
            + flow(["BE163을 지그 P-MB로 70 × 50 + 홈 2.8 × 26.5를 긋고 꺾는다. 나사 Ø3.2 (50.0, 149.0)·(114.5, 192.5), 위치 핀 Ø3.0 (114.5, 149.0)·(50.0, 192.5)을 안내 구멍으로 먼저.",
                    "C301(먹스 VCC–GND, 아랫면 1206) → 아랫면 배선(BRD-08 번호 순서는 주 4). 금지 구역 x81.22~85.42 × y≤173.2는 제로 밑 y≥174.86에서만 건넌다.",
                    "먹스 헤더 1×16 + 1×8, 제로 헤더 1×9 ×2(몰드 뺌, 아래 줄 없음) → 제로 밑면에 캡톤 → 모듈 납땜. R301(O1·O7)~R303(O1)은 붙여 눕힘.",
                    "ID 점퍼: O 번호에 맞춰 JP301~JP303 납땜 브리지(표). JP304는 열어 둔다.",
                    "J301 리본·J302(O1·O7만) 플러그 선을 <b>모듈에 넣기 전에</b> 아랫면에서 납땜 → 모듈을 뒤집어 바닥 구멍으로 넣고 M3×6 ×2(밑에서).",
                    "확인: 3V3–GND 단락 없음, ID 핀–GND 0 Ω/열림이 표와 같음 → USB를 꽂으면 'Toccata O1'~'O7'로 보임."]))
    body_parts.append(part("circuit-mb", "C", "제어 기판 MB", "×7 (ID 점퍼만 다름)",
                           "RP2040-Zero가 4067 먹스로 센서 12개와 끝 부속 입력 4개(EXT)를 ADC 하나로 차례로 읽어 USB-MIDI로 보냅니다. 7장 모두 같은 기판이고 ID 점퍼로 몇 번째 옥타브인지 정합니다.", body))

    # ---------------- 끝 부속
    body = (fig("circuit-sch-04", "SCH-04", "끝 부속 센서 기판 (EL · ER) + EXT", "A0·A#0·B0는 O1, C8은 O7의 EXT(먹스 C12~)로. 1 kΩ은 아랫면 1206(△13). XH 위치 1 = GND … 6 = 3V3.")
            + crop("circuit-brd-02-end", "BRD-02", "end", "끝 부속 EL·ER 기판 배치", "EL 45.5 × 15.24, ER 22.0 × 15.24 — 센서·아랫면 1206 부품·리드 패드·필요한 리브 틈.")
            + crop("circuit-brd-06-ext", "BRD-06", "left", "리본·EXT 선 만들기", "W101~W107 리본, W401·W411 리드 + 소켓 선, W403·W413 플러그 선(Adafruit 4876).")
            + bom_block("circuit-end-bom", "EL · ER", bom_rows(lambda r: r[0] == "SCH-04"))
            + h4("EXT 커넥터 위치")
            + table(["끝", "XH", "넷", "끝 부속 패드", "제어 기판 패드", "먹스", "건반 = MIDI"], xh_rows(), mono=(1, 2, 3, 4, 5))
            + h4("선") + cable_block(["W401", "W403", "W411", "W413"]) + notes_block(["W401", "W403", "W411"])
            + h4("만드는 순서와 확인")
            + flow(["12 × 18 기판에서 EL 45.5 × 15.24, ER 22.0 × 15.24 띠(6행)를 자른다. 부품은 모두 아랫면: 100 nF, 1 kΩ(OUT → y72.08), 10 µF.",
                    "리본 가닥(EL 5, ER 3)을 J401/J411에 납땜 → 기판·센서 바 고정 → 자유 끝을 리브 틈·레일 밑 차선·뒷벽 홈으로 꿴다(XH 하우징은 못 지나감).",
                    "뒤 통로에서 Adafruit 4876 소켓 선(50 mm)과 가닥마다 이어 수축 튜브. 하우징 번호 = J302 패드 번호.",
                    "확인: 끝 부속을 꽂으면 O1 C12~C14 / O7 C12에서 센서 값, 빼면 0.15 V 아래(100 kΩ 풀다운)."]))
    body_parts.append(part("circuit-end", "D", "끝 부속 EL · ER", "EL ×1 · ER ×1",
                           "88건반 중 옥타브 모듈 밖의 네 건반(왼쪽 A0·A#0·B0, 오른쪽 C8)의 센서입니다. 끝 부속을 떼어 보관할 수 있게 JST-XH 6핀으로 O1·O7 제어 기판의 EXT 입력에 잇습니다.", body))

    # ---------------- 페달
    zped = [[r[0], r[2], r[5]] for r in pins_z[1:] if r[5] != "NC"]
    psm_ped = [r for r in psm[1:] if r[0] in ("J501 조각", "PS 조각")]
    body = (fig("circuit-sch-05", "SCH-05", "페달 보드 (PB) + 댐퍼 페달 센서 (PS)", "페달 안 DRV5055 → R551 1 kΩ → 3 m TRS → J501(TN = GND) → W502 → J502 → 1 kΩ + 100 nF → GP26. 링 급전 20 Ω, 팁 100 kΩ, GP14 = GND.")
            + fig("circuit-brd-03", "BRD-03", "페달 보드 배치 (PB)", "BE163 70 × 50 (지그 P-PED), 모든 구멍 좌표와 아랫면 배선(굵은 실선 = 주석 맨선, 지나는 패드마다 납땜 · 점선 = 리본 가닥, 두 끝만). 배선 검사: SCH-05와 일치.")
            + crop("circuit-brd-07-j501", "BRD-07", "j501", "J501 페달 잭 조각", "25 × 24 자투리(9 × 9 구멍): 잭 자리(점선)와 W502 앞 패드 T·TN·R·S 좌표.")
            + crop("circuit-brd-07-ps", "BRD-07", "ps", "PS 페달 안 센서 조각", "7 × 5 구멍(로컬 좌표): U551·C551·R551과 W501 패드, 아랫면 맨선. 배선 검사: SCH-05와 일치.")
            + crop("circuit-brd-06-ped", "BRD-06", "ped", "페달 선 만들기", "W501 3 m 스테레오(페달 쪽 잘라 납땜), W502 리본 가닥 4개.")
            + bom_block("circuit-ped-bom", "PB · PS · J501 조각", bom_rows(lambda r: r[0] == "SCH-05"))
            + h4("PB 구멍 표 (모델 좌표 · 지그 u, v · 격자 i, j)")
            + table(pads_pb[0], pads_pb[1:], mono=(0, 1, 2, 3, 4, 5, 6, 7, 8))
            + h4("PB 아랫면 배선")
            + table(wpb[0], wpb[1:], mono=(0, 1, 2, 3))
            + h4("J501 조각 · PS 조각 구멍 (BRD-07)")
            + table(psm[0], psm_ped, mono=(1, 2, 3, 4, 5, 6, 7))
            + h4("A501 쓰는 핀") + table(["패드", "이름", "PB 넷"], zped, mono=(0, 1))
            + h4("선") + cable_block(["W501", "W502"], ("W208",)) + notes_block(["W501", "W502"])
            + h4("만드는 순서와 확인")
            + flow(["BE163을 지그 P-PED로 70 × 50 긋고 꺾기, 나사 Ø3.2 (430.5, 248)·(472.5, 310), 위치 핀 Ø3.0 (472.5, 248)·(430.5, 310).",
                    "BRD-03 배치표대로 R501·R502·R503(100 Ω ×5)·C501·JP504 → 아랫면 배선 → 헤더(몰드 뺌) → 캡톤 → A501. 주석 맨선(GND 레일·버스·R501.2 → R502.2 → J502.1 줄·짧은 다리)은 지나는 패드마다 납땜하고, 리본 가닥은 두 끝만 벗겨 끝의 패드·맨선에 납땜한다(가닥 중간은 아무것도 잇지 않음).",
                    "J501 조각(BRD-07): PJ-313을 잭 자리에 꽂고 다리 T·TN·R·S → 앞 패드 → W502 4가닥으로 J502와 잇고 → 조각을 뒤판 잭 선반에 MS 폴리머로.",
                    "페달: 마이크로스위치 배선을 떼고 발판 밑에 자석(S극 아래), 바닥판에 PS 조각(BRD-07: U551·C551·R551) + W501 끝(팁 → c6 r4, 링 → c6 r1, 슬리브 → c6 r2).",
                    "확인: A501 전 GP26 패드 ↔ R501.1 = 0 Ω, J502.1 ↔ TP501 = 0 Ω, J502.2·J502.4 ↔ GND = 0 Ω, J502.3–3V3 = 20 Ω, J502.1–GND = 100 kΩ. USB 연결 → 'Toccata PED', 페달 꽂으면 링 3.05 V 이상, 빼면 GP26 ≈ 0 V."]))
    body_parts.append(part("circuit-ped", "E", "페달 PB · PS", "PB ×1 · PS ×1 · J501 조각",
                           "댐퍼 페달 안 홀센서가 발판 자석의 거리를 재고, 가운데 유닛의 페달 보드 RP2040-Zero가 CC64 0~127(하프페달)로 보냅니다. 페달은 3 m 스테레오 선으로 뒤판 잭에 꽂습니다.", body))

    # ---------------- 전원
    pwr_refs = {"BT601", "X605", "X606", "F601", "F601-HLD", "SW601", "A602", "P601", "P602", "TP601", "TP602", "TP603", "A604", "W209", "열수축"}
    budget_rows = [["평균 (피아노 음악)", f"약 {B['avg'][0]:.1f}~{B['avg'][1]:.1f} W", f"약 {B['avg_a'][0]:.1f}~{B['avg_a'][1]:.1f} A @ 12.8 V"],
                   ["순간 최대 (최저음 강타)", f"약 {B['peak']:.1f} W", f"약 {B['peak_a']:.1f} A (10 V에서 약 {B['peak_a_min_v']:.1f} A)"],
                   ["연주 시간 (76.8 Wh × 0.9)", f"약 {B['run'][1]:.1f}~{B['run'][0]:.1f} 시간", "퓨즈 5 A ATO"],
                   ["Pi 5 USB-C 입력 (화면 포함)", f"약 {B['pi_in_a']:.1f} A @ 5.1 V", "get_throttled = 0x0 확인"]]
    body = (crop("circuit-sch-06-pwr", "SCH-06", "power", "전원 (CU)", "전지 BT601 → XT60 → F601 5 A ATO → SW601(두 회로 나란히, △20) → +12V8 → A602 강압 5.1 V(Pi 5·허브) + 앰프. 별 접지 = 강압 IN−. 전원 예산 표.")
            + fig("circuit-brd-04", "BRD-04", "가운데 유닛 배선도", "CAD 투영: 위 1 : 2 전체, 아래 1 : 1 전원 구석. 선마다 W 번호·CAD 경로·자르는 길이·수축 튜브 색.")
            + crop("circuit-brd-05-pwr", "BRD-05", "power", "전원 하네스 만들기", "W601~W604: 양 끝·핀·색·이음(S1~S3)·자르는 길이.")
            + crop("circuit-brd-05-sw", "BRD-05", "switch", "KCD1-104 단자", "안에서 뒤판을 본 단자 배치와 W602j 연결.")
            + bom_block("circuit-pwr-bom", "전원 (열수축 튜브 포함)", bom_rows(lambda r: r[2] in pwr_refs))
            + h4("단자와 넷") + table(["부품", "단자", "넷", "메모"], power_terms(), mono=(1,))
            + h4("전원 예산 (SCH-06 표)") + table(["항목", "값", "메모"], budget_rows, mono=(1, 2))
            + h4("선") + cable_block(["W601", "W602a", "W602j", "W602b", "W602c", "W603", "W604"], ("W209",))
            + notes_block(["W601", "W602a", "W602j", "W602b", "W602c", "W603", "W604"])
            + h4("만드는 순서와 확인")
            + flow(["전지: 무부하 전압과 BMS를 먼저 확인(‘받으면 확인’ 표).",
                    f"W601: 홀더 −x 꼬리를 홀더 끝에서 {HN.STUB12} mm로 자르고, XT60 수 리드 빨강·검정을 {HN.LEAD_W601} mm로 자른다. 빨강 → S1(10 mm 꼬아 납땜, R15 굽힘 뒤) → 꼬리, 검정 → S2 → 16 AWG 검정 연장 {HN.BLACK_EXT} mm → ★. "
                    f"이은 뒤 홀더 끝에서 XT60 뒤끝까지 {HN.W601_MAX} mm 이하인지 잰다(약 {HN.W601_TOTAL} mm). 빨강 수축.",
                    f"W602a: 홀더 +x 꼬리 {HN.STUB12} mm → S3(겹침 = 홀더 끝에서 {HN.STUB12 - HN.SPLICE_OVL}~{HN.STUB12} mm, R15 굽힘 뒤) → 16 AWG 빨강 {HN.W602A_16} mm → SW601-1. KCD1 짝 확인 뒤 W602j(1–3, 2–4).",
                    "XL4016을 벤치 12 V(SMPS + XT60 암 어댑터)로 무부하 5.10~5.15 V에 맞추고 가변저항 고정 → W602b·W602c 연결(W602c는 앰프 단자 자리에 맞춰 남는 선을 묶음).",
                    "W603(C24 A 끝을 자른 빨강·검정) → OUT+/−, W604(허브 DC) → OUT+/−. 극성 확인 뒤 Pi·허브 연결.",
                    "확인: 스위치 끔에서 +12V8 = 0 V, 켬에서 전지 전압. TP602 = 5.1 V. Pi 헤더 핀 2–6 부하 때 5.0 V 이상."]))
    body_parts.append(part("circuit-pwr", "F", "전원", "CU ×1 (보드 밖 배선)",
                           "LiFePO4 12.8 V 6 Ah 전지 하나로 악기 전체를 켭니다. XT60 → 5 A 퓨즈 → 로커 스위치 → 12.8 V 버스에서 앰프로 바로 가고, XL4016이 5.1 V로 낮춰 Pi 5와 USB 허브에 줍니다. 충전은 팩의 DC 잭으로 따로 합니다.", body))

    # ---------------- 오디오
    aud_refs = lambda r: r[0] == "SCH-07" or r[2] in ("X701", "W703~W706 선")
    psm_j7 = [r for r in psm[1:] if r[0] == "J702 기판"]
    wsm_j7 = [r for r in wsm[1:] if r[0] == "J702"]
    body = (fig("circuit-sch-07", "SCH-07", "오디오 (CU)", "동글 → 볼 헤드폰 잭 J701(노멀) → J702 → 1 µF×2 + 1 kΩ(AGND) → XH-A232 → XT60 SPK → CW-100B25 ×2 (BTL). 앰프 PVCC = +12V8.")
            + crop("circuit-brd-05-aud", "BRD-05", "audio", "오디오 선 만들기", "W701·W702(BC256 반쪽), W707(J702 → 앰프 입력), W703·W705(앰프 → XT60 수 SPK), W704·W706(스피커 꼬리선).")
            + crop("circuit-brd-07-j702", "BRD-07", "j702", "J702 앰프 입력 기판", "30 × 25(12 × 10 구멍, 모델 좌표): 잭 T·R·S 다리 → 모음 패드 → 1 µF ×2 → 출력 패드 L·G·R, 1 kΩ → G. TN·RN 다리는 비움. 실선 = 주석 맨선, 점선 = 피복 가닥(두 끝만). 배선 검사: SCH-07과 일치.")
            + crop("circuit-brd-07-j701", "BRD-07", "j701", "J701 헤드폰 잭 (볼 포켓, 기판 없음)", "CAD 포켓 단면: 잭을 밑에서 넣고 다리에 W701·W702를 바로 납땜.")
            + bom_block("circuit-aud-bom", "오디오", bom_rows(aud_refs))
            + h4("잭·단자와 넷") + table(["부품", "단자", "넷", "메모"], audio_terms())
            + h4("J702 기판 구멍과 배선 (BRD-07)")
            + table(psm[0], psm_j7, mono=(1, 2, 3, 4, 5, 6, 7))
            + table(wsm[0], wsm_j7, mono=(1, 2, 3))
            + h4("선") + cable_block(["W701", "W702", "W707", "W703", "W705", "W704", "W706"], ("X701",))
            + notes_block(["W701", "W702", "W707", "W703", "W705", "W704"])
            + h4("만드는 순서와 확인")
            + flow(["PJ-313 3개의 다리 글자(T·TN·R·RN·S)를 통전으로 찾는다. J701은 왼쪽 볼 포켓(기판 없음, 다리에 직접 납땜), J702는 J702 기판(BRD-07)에.",
                    f"BC256 3 m를 가운데에서 잘라 두 반쪽: W701은 플러그 뒤끝(선이 몰드에서 나오는 곳)에서 {HN.W701_CUT / 1000:.1f} m로 자르고(CAD 경로 약 {HN.W701_PATH:.0f} mm → J701 T·R·S), 남는 약 {(HN.W707_FROM - 40) / 1000:.2f} m에서 W707(300)을 자른다. 자르기 전에 볼 홈 → 통로 → 동글 경로에 대 본다. W702(J701 TN·RN·S → 플러그, 경로 약 {HN.W702_PATH:.0f} mm)는 1.5 m 반쪽 그대로.",
                    "J702 기판: 잭 T·R·S 다리 → 모음 패드, T 모음 → C701·C702(나란히) → 패드 L, R 모음 → C703·C704 → 패드 R, R701·R702 1 kΩ은 출력 → G(AGND 줄). TN·RN 다리는 어디에도 잇지 않는다. AGND는 앰프 IN G에서만 GND와 만남.",
                    "W703·W705: 앰프 스피커 단자 → XT60 수 SPK 리드와 이음(50 mm 여유 — 단자 자리는 받은 보드로), W704·W706: XT60 암 리드 → 상자 안 짧은 선 → 유닛. 모두 파랑 수축 + SPK, 좌우 같은 방향(+ = 빨강).",
                    "확인: T 모음–L 패드 열림, C703.1 ↔ R702.1 ↔ W707 R 패드 = 0 Ω, L–G = 1 kΩ, R–G = 1 kΩ, 스피커 Re 6~7 Ω, 헤드폰을 꽂으면 스피커가 꺼짐. 소프트웨어 음량 상한은 최대 출력 약 8 W/ch(입력 약 0.13 Vrms)에서 찌그러지지 않게."]))
    body_parts.append(part("circuit-aud", "G", "오디오", "CU ×1 · 스피커 ×2",
                           "Pi 5의 소리가 Apple USB-C 동글(DAC)로 나와 왼쪽 볼의 헤드폰 잭을 거칩니다. 헤드폰이 없으면 노멀 접점으로 앰프 입력 잭에 가서 약 93 Hz 아래를 줄인 뒤 TPA3110 앰프가 스피커 두 개를 울립니다.", body))

    # ---------------- 터치스크린
    ts_refs = {"A603", "P603", "X601", "X602", "X603", "X604", "P604", "A605", "W605"}
    body = (crop("circuit-sch-06-ts", "SCH-06", "display", "화면 A605 전원 · DSI", "Pi 40핀 헤더 2·6번 → W606 F/F → W607 M/M → 동봉선 3핀 → MX1.25 → A605. DSI = W605 FFC 22핀 B형.")
            + crop("circuit-brd-06-ts", "BRD-06", "ts", "화면 전원 점퍼", "W606·W607 점퍼(산 그대로, 제품 길이 200)와 W608 동봉선의 핀.")
            + bom_block("circuit-ts-bom", "터치스크린", bom_rows(lambda r: r[2] in ts_refs))
            + h4("핀과 넷") + table(["부품", "핀", "넷", "메모"], ts_terms(), mono=(1,))
            + h4("선") + cable_block(["W606", "W607", "W608"], ("W605",))
            + h4("만드는 순서와 확인")
            + flow(["동봉 전원선의 2.54 3핀이 1 빨강 · 2 빈 칸 · 3 검정인지 통전으로 확인한 뒤 점퍼를 꽂는다. 꽂는 곳 3곳은 수축 튜브.",
                    "W605 FFC(B형)를 Pi 5 CAM/DISP 1과 화면 ZIF에 1 ↔ 1로. 경로 약 245 mm(300 mm 선).",
                    f"config.txt에 <code>{E(S.DISP['overlay'])}</code> (CAM/DISP 0이면 <code>,dsi0</code>).",
                    f"확인: 화면 쪽 5 V를 부하 때 잰다(점퍼 왕복 강하 약 {B['drop_v']:.2f} V). 최대 부하에서 vcgencmd get_throttled = 0x0. 화면 켬·끔에서 센서 유휴 흔들림을 다시 잰다(D14)."]))
    body_parts.append(part("circuit-ts", "H", "터치스크린", "A605 ×1",
                           f"7인치 Waveshare 7-DSI-TOUCH-C가 Pi 5의 DSI 리본으로 화면과 터치를 받고, 전원 5 V(약 {B['disp_w']:.2f} W)는 Pi 40핀 헤더 2·6번에서 점퍼 두 단으로 받습니다. 화면에는 다른 5 V를 넣지 않습니다.",
                           body))

    # BOM coverage: every bom.csv row must appear in one part section
    missing = [BOM[1 + k][2] for k in range(len(BOM) - 1) if k not in SHOWN]
    if missing:
        print("page: BOM rows not shown in any section:", missing)
    n_parts = len(BOM) - 1

    p = []
    p.append('<section class="page" id="p-circuit" hidden>')
    p.append('<h2>회로도 — 파트별 상세</h2>')
    p.append('<p class="lede">악기 전자부를 파트별로 나눴습니다. 파트마다 하는 일, 회로도, 기판·배선 도면, 부품표(KiCad 심볼·풋프린트와 최종 구매 상태), '
             '선 만드는 길이, 핀 표, 만드는 순서와 확인을 한곳에 모았습니다. 부품 번호·핀 번호·넷 이름·값·구멍 좌표가 모두 있어 KiCad나 만능기판으로 그대로 옮길 수 있고, '
             '가운데 유닛 배선과 선 길이는 CAD 모델에서 잰 값입니다.</p>')
    p.append('<div class="kfs">'
             f'<div class="kf"><b>{n_sheets}장</b><span>회로도 {n_sch} + 기판·배선 {n_sheets - n_sch} (A3, 개정 {REV})</span></div>'
             f'<div class="kf"><b>{n_parts}줄</b><span>부품표 — 파트별 표에 모두 나옴{"" if not missing else " (빠진 줄 %d)" % len(missing)}</span></div>'
             f'<div class="kf"><b>{len(named)}개</b><span>이름 있는 넷 (그린 도면에서 다시 계산)</span></div>'
             f'<div class="kf"><b>{n_cab}가닥</b><span>선 (표 {n_rows}줄, 젠더 X701 포함) · 자르는 길이 = CAD 경로 + 20</span></div>'
             f'<div class="kf"><b>{CHK[0]} · {CHK[1]} · {CHK[2]}</b><span>연결 오류 · 글자 겹침 · 기판 배선 검사 ({n_sheets}장 자동 검사)</span></div>'
             '</div>')
    chips = [("circuit-sys", "시스템", "SCH-01"), ("circuit-sb", "센서 기판 SB", "×7"), ("circuit-mb", "제어 기판 MB", "×7"), ("circuit-end", "끝 부속 EL·ER", "×2"),
             ("circuit-ped", "페달 PB·PS", "×1"), ("circuit-pwr", "전원", "CU"), ("circuit-aud", "오디오", "CU"), ("circuit-ts", "터치스크린", "CU"),
             ("circuit-arrive", "받으면 확인", str(len(CHECKS))), ("circuit-kicad", "KiCad로", "8단계"), ("circuit-files", "파일 받기", "CSV · ZIP")]
    p.append('<nav class="circ-chips" id="circuit-parts" aria-label="회로 파트">' + "".join(
        f'<a href="#{a}">{E(t)} <span class="q">{E(q)}</span></a>' for a, t, q in chips) + '</nav>')
    p.append('<p class="small muted">도면 색: 초록 선 = 배선, 갈색 테두리 = 부품, 파란 상자 = 산 모듈, 점선 갈색 = 케이블, 노란 △ = 처음 글 사양 대비 바꾼 곳(번호는 맨 아래 표). '
             '"&gt;&gt;" = 맞물린 커넥터(KiCad에서는 연결이 아니라 양쪽에 같은 넷 이름). 도면은 "2배·3배"로 페이지 안에서 확대해 옆으로 넘겨 봅니다. '
             f'USB 선 길이: {E(usb_txt)}.</p>')
    p += body_parts
    p.append('<section class="circ-part" id="circuit-arrive" aria-labelledby="circuit-arrive-h"><h3 id="circuit-arrive-h"><span class="no">I</span>부품이 오면 먼저 확인할 것</h3>'
             + table(["항목", "확인"], CHECKS) + '<p class="small circ-top"><a href="#circuit-parts">파트 목록으로 ↑</a></p></section>')
    p.append('<section class="circ-part" id="circuit-kicad" aria-labelledby="circuit-kicad-h"><h3 id="circuit-kicad-h"><span class="no">J</span>KiCad로 옮기는 순서</h3>'
             + kicad_steps() + '<p class="small circ-top"><a href="#circuit-parts">파트 목록으로 ↑</a></p></section>')
    fz = os.path.join(FIN, ZIPNAME + ".b64.txt")
    p.append('<section class="circ-part" id="circuit-files" aria-labelledby="circuit-files-h"><h3 id="circuit-files-h"><span class="no">K</span>파일 받기</h3>'
             f'<p>KiCad로 옮길 때 쓰는 표입니다. 묶음 ZIP에는 도면 {n_sheets}장(SVG)과 아래 표 전부, 설명(README)이 들어 있습니다.</p>'
             '<div class="circ-dl">'
             f'<button type="button" class="circ-dlbtn" data-dl="fin/circuit/{ZIPNAME}.b64.txt" data-name="{ZIPNAME}" data-kind="zip" '
             'data-repo="hardware/pcb/ (schematic/ · board/ · netlist/ · README.md)">도면 + 표 묶음 ZIP 받기</button>'
             '</div><div class="tbl"><table><thead><tr><th>파일</th><th>내용</th><th></th></tr></thead><tbody>'
             + "".join(f'<tr><td class="num">{E(f)}</td><td>{E(d)}</td><td><button type="button" class="circ-dlbtn small" data-dl="fin/circuit/{E(f)}" '
                       f'data-name="toccata-{E(f)}" data-kind="csv" data-repo="hardware/pcb/netlist/{E(f)}">받기</button></td></tr>' for f, d in FILES)
             + '</tbody></table></div><p class="small muted" id="circuit-dl-status" role="status" aria-live="polite"></p>'
             '<p class="small muted">저장소 위치: <span class="mono">hardware/pcb/</span> — schematic/(SCH-01~07), board/(BRD-01~08), netlist/(CSV, cad_centre.json, mb_routes.json), '
             'src/(생성기: build.py → 도면·CSV, page.py → 이 탭), README.md(규칙·변경·KiCad). 받은 파일 이름은 앞에 toccata-가 붙습니다(저장소 파일 이름은 그 뒤 부분).</p>'
             '<p class="small circ-top"><a href="#circuit-parts">파트 목록으로 ↑</a></p></section>')
    p.append('<section class="circ-part" id="circuit-changes" aria-labelledby="circuit-changes-h"><h3 id="circuit-changes-h"><span class="no">L</span>개정과 바꾼 점</h3>'
             + table(["개정", "날짜", "바뀐 것"], CHANGES, mono=(0, 1))
             + h4("개정 E에서 바꾼 곳 (도면의 △19~△30)")
             + table(["△", "도면", "바꾼 것", "이유"], DELTA_E, mono=(0,))
             + '<p class="small muted">△1~△18의 자세한 내용은 저장소 hardware/pcb/README.md에 있습니다. 근거: TI DRV5055 SBAS640C, TI CD74HC4067, RP2040 데이터시트(E11), '
               'Waveshare RP2040-Zero 위키·회로도, SparkFun BOB-09056, TI TPA3110D2, AMASS XT60, KiCad 9/10 라이브러리, hardware/pcb/research/.</p></section>')
    p.append('</section>')
    frag = "\n".join(p)
    with open(os.path.join(OUT, "circuit.html"), "w", encoding="utf-8") as f:
        f.write(frag)
    with open(os.path.join(OUT, "circuit.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    with open(os.path.join(OUT, "circuit.js"), "w", encoding="utf-8") as f:
        f.write(JS)
    # runtime assets: CSVs + ZIP (base64 text) into docs/report/toccata-v4/fin/circuit/
    assets = []
    for fname, _ in FILES:
        shutil.copyfile(os.path.join(ROOT, "netlist", fname), os.path.join(FIN, fname))
        assets.append("fin/circuit/" + fname)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for sub in ("schematic", "board", "netlist"):
            for fn in sorted(os.listdir(os.path.join(ROOT, sub))):
                if fn.endswith((".svg", ".csv", ".json")):
                    z.write(os.path.join(ROOT, sub, fn), f"toccata-circuit-revE/{sub}/{fn}")
        z.write(os.path.join(ROOT, "README.md"), "toccata-circuit-revE/README.md")
    with open(fz, "w", encoding="ascii") as f:
        f.write(base64.b64encode(buf.getvalue()).decode("ascii"))
    assets.append("fin/circuit/" + ZIPNAME + ".b64.txt")
    sheet_assets = ["sch/" + v["file"] for v in SHEETS_JSON.values()]
    with open(os.path.join(OUT, "assets.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sheet_assets + assets) + "\n")
    print("page:", len(frag), "chars;", len(sheet_assets), "sheets;", len(assets), "assets; zip", len(buf.getvalue()), "bytes; BOM rows shown",
          len(SHOWN), "/", n_parts)


CSS = """
/* ---- shared by every drawing tab: zoom bar on .csheet (circuit.js toggles .z2 / .z3 page-wide). Inside .sheet the tokens are
   the light sheet palette, so these stay paper-white in both themes. ---- */
.csheet .cap{align-items:center}
.zbar{display:inline-flex;gap:4px;align-items:center;flex-wrap:wrap}
.zbar button{font:inherit;font-size:12px;line-height:1.2;border:1px solid var(--rule-2);background:var(--card);color:var(--ink);border-radius:6px;padding:4px 9px;min-height:30px;cursor:pointer}
.zbar button[aria-pressed="true"]{background:var(--ink);color:var(--card);border-color:var(--ink)}
.zbar a{margin-left:6px;white-space:nowrap}
.csheet .dwimg img{min-width:720px}
.csheet.z2 .dwimg img{width:2000px;min-width:0;max-width:none}
.csheet.z3 .dwimg img{width:3000px;min-width:0;max-width:none}
@media (pointer:coarse){.zbar button{min-height:44px;min-width:44px}}
/* ---- 01 회로도 ---- */
#p-circuit .circ-chips{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px}
#p-circuit .circ-chips a{display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:6px 14px;border:1px solid var(--rule-2);border-radius:999px;background:var(--card);color:var(--ink);text-decoration:none;font-size:14px}
#p-circuit .circ-chips a:hover{border-color:var(--blue);color:var(--blue)}
#p-circuit .circ-chips a .q{font-family:var(--mono);font-size:11.5px;color:var(--ink-3)}
#p-circuit .circ-part{border-top:1px solid var(--rule);margin-top:30px;padding-top:4px;scroll-margin-top:calc(var(--navh,50px) + 12px)}
#p-circuit .circ-part > h3{margin-top:18px}
#p-circuit .circ-what{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 14px;align-items:start}
#p-circuit .circ-what > *{min-width:0}
#p-circuit .circ-what p{margin:0 0 6px;color:var(--ink-2)}
#p-circuit .circ-qty{font-family:var(--mono);white-space:nowrap;justify-self:start}
#p-circuit .circ-top{margin:10px 0 0}
#p-circuit .sheet,#p-circuit [id^="circuit-"]{scroll-margin-top:calc(var(--navh,50px) + 12px)}
#p-circuit .dwimg.crop svg{display:block;width:100%;min-width:720px;height:auto}
#p-circuit .csheet.z2 .dwimg.crop svg{width:2000px;min-width:0;max-width:none}
#p-circuit .csheet.z3 .dwimg.crop svg{width:3000px;min-width:0;max-width:none}
#p-circuit details.cbom{margin:10px 0;border:1px solid var(--rule);border-radius:10px;background:var(--card);padding:6px 10px}
#p-circuit details.cbom summary{font-size:14px;color:var(--ink);font-weight:600;min-height:32px;display:flex;align-items:center}
#p-circuit details.cbom .tbl{margin:8px 0 4px}
#p-circuit details.cbom table{font-size:12px}
#p-circuit .tbl td{font-size:12.5px}
#p-circuit .tbl td.num{white-space:normal;overflow-wrap:anywhere}
#p-circuit .sub4{margin:18px 0 6px}
#p-circuit ul.flow{list-style:disc}
#p-circuit .circ-dl{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
#p-circuit .circ-dlbtn{font:inherit;font-size:14px;min-height:44px;padding:8px 16px;border-radius:8px;border:1px solid var(--ink);background:var(--ink);color:var(--paper);cursor:pointer}
#p-circuit .circ-dlbtn.small{font-size:13px;min-height:44px;padding:6px 12px;background:var(--card);color:var(--ink);border-color:var(--rule-2)}
#p-circuit .circ-dlbtn:disabled{opacity:.55;cursor:progress}
#p-circuit .circ-dlbtn:focus-visible,#p-circuit .circ-chips a:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
@media (max-width:620px){
  #p-circuit .circ-what{grid-template-columns:minmax(0,1fr)}
  #p-circuit .circ-chips a{font-size:13px;padding:6px 12px}
}
@media (prefers-reduced-motion:reduce){#p-circuit *{scroll-behavior:auto!important;transition:none!important}}
"""

JS = r"""
(function(){
  // zoom bars: page-wide (every drawing tab uses the same .zbar / .csheet markup)
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('.zbar button') : null; if(!b) return;
    var f = b.closest('.csheet'); if(!f) return;
    var z = b.getAttribute('data-z');
    f.classList.remove('z2', 'z3'); if(z !== '1') f.classList.add('z' + z);
    f.querySelectorAll('.zbar button').forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
  });
  var sec = document.getElementById('p-circuit'); if(!sec) return;
  // sheet crops: inline SVG <image> would load at once; give it its href only when the tab is first shown
  var started = false;
  function start(){
    if(started || sec.hidden) return; started = true;
    sec.querySelectorAll('image[data-href]').forEach(function(im){ im.setAttribute('href', im.getAttribute('data-href')); });
  }
  try { new MutationObserver(start).observe(sec, {attributes: true, attributeFilter: ['hidden']}); } catch(err) {}
  start();
  // downloads (window.claude downloads capability; CSV as text, the ZIP is shipped as base64 text)
  var status = sec.querySelector('#circuit-dl-status');
  function say(t){ if(status) status.textContent = t; }
  sec.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('button[data-dl]') : null; if(!b) return;
    var file = b.getAttribute('data-dl'), name = b.getAttribute('data-name'), kind = b.getAttribute('data-kind');
    var repo = b.getAttribute('data-repo') || 'hardware/pcb/';
    var use = window.claude && typeof window.claude.use === 'function' ? window.claude.use : null;
    if(!use){ say('이 화면에서는 파일 받기를 쓸 수 없습니다. 같은 내용이 저장소 ' + repo + '에 있습니다.'); return; }
    b.disabled = true; say(name + ' 준비 중…');
    Promise.resolve().then(function(){ return use.call(window.claude, 'downloads'); }).then(function(dl){
      if(!dl || typeof dl.save !== 'function') throw {code: 'unavailable'};
      return fetch(file).then(function(r){
        if(!r.ok) throw {code: 'fetch ' + r.status};
        if(kind === 'zip') return r.text().then(function(t){
          var bin = atob(t.replace(/\s+/g, '')), u = new Uint8Array(bin.length);
          for(var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
          return new Blob([u], {type: 'application/zip'});
        });
        return r.arrayBuffer().then(function(a){ return new Blob([a], {type: 'text/csv'}); });
      }).then(function(blob){ return dl.save({filename: name, data: blob}); });
    }).then(function(){ say(name + ' 저장을 요청했습니다.'); }, function(err){
      var c = String((err && (err.code || err.name || err.message)) || '');
      if(/declin|cancel|abort|denied/i.test(c)) say('저장을 취소했습니다.');
      else if(c === 'unavailable') say('이 화면에서는 파일 받기를 쓸 수 없습니다. 같은 내용이 저장소 ' + repo + '에 있습니다.');
      else say('받기에 실패했습니다 (' + c + ').');
    }).then(function(){ b.disabled = false; });
  });
})();
"""

if __name__ == "__main__":
    build()
