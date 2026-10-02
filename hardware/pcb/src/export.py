"""CSV exports: netlist, BOM (with KiCad symbol/footprint), cables, RP2040 pad map, MB wiring list."""
import csv
import math
import os
import re

import parts as P
import sheets as S

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "netlist")

# board of each sheet and how many are built
BOARDS = {
    "SCH-02": [("SB", 7)],
    "SCH-03": [("MB", 7)],
    "SCH-04": [("EL", 1), ("ER", 1)],
    "SCH-05": [("PB", 1), ("PS", 1)],
    "SCH-06": [("CU", 1)],
    "SCH-07": [("CU", 1)],
}

EXCL = "보드 밖 (Exclude from board)"

# (symbol name, value regex) -> (BOM key, KiCad symbol, footprint)
KICAD = [
    ("DRV5055", None, "DRV5055", "Sensor_Magnetic:DRV5055A2xLPGxQ1 (Value = DRV5055A2QLPG)",
     "Package_TO_SOT_THT:TO-92_Inline_W4.0mm_Horizontal_FlatSideUp → 2.54 간격으로 복사 수정"),
    ("C", r"100n", "C100n", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    ("C", r"10µ", "C10u", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    ("C", r"1µ", "C1u", "Device:C", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm (리드 간격 실측)"),
    ("R", r"^1k$", "R1k", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    ("R", r"^100k$", "R100k", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    ("R", r"20Ω", "R100", "Device:R (Value 20R = 100 Ω ×5 병렬)", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal ×5"),
    ("RP2040-Zero", None, "ZERO", "dj505/RP2040-Zero-KiCAD : RP2040-Zero (3V3 핀을 power_out으로)",
     "bobu01/RP2040-Zero-Kicad-Footprint-1mm 또는 dj505 풋프린트를 1.0 mm 드릴로 복사 (핀 헤더용, 번호는 dj505 그대로)"),
    ("CD74HC4067_module", None, "MUX", "Toccata:CD74HC4067_Breakout (직접 만듦, 핀 1~16 C0~C15, 17~24 J2)",
     "Toccata:CD74HC4067_Breakout_40.6x17.8 (행 간격 15.24) 또는 PinHeader_1x16 + PinHeader_1x08"),
    ("Conn_02x08_Odd_Even", None, "RIBBON", "Connector_Generic:Conn_02x08_Odd_Even",
     "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical (패드만, 리본 직접 납땜)"),
    ("Conn_01x06", None, "PADS6", "Connector_Generic:Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical (패드만)"),
    ("JST_XH_6P", None, "JSTXH", "Connector_Generic:Conn_01x06", EXCL + " — 선 대 선 커넥터"),
    ("Conn_pads", None, "PADS", "Connector_Generic:Conn_01x0N (J401 = 01x05, J411 = 01x03)", "Connector_PinHeader_2.54mm:PinHeader_1x05 / 1x03_P2.54mm_Vertical (패드만)"),
    ("SolderJumper_2_Open", None, "JP", "Jumper:SolderJumper_2_Open", "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm (만능기판: 두 구멍 브리지)"),
    ("SolderJumper_2_Bridged", None, "JP", "Jumper:SolderJumper_2_Bridged", "Jumper:SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm (만능기판: 두 구멍 납땜)"),
    ("TestPoint", None, "TP", "Connector:TestPoint", "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm"),
    ("PJ-313", None, "PJ313", "Connector_Audio:AudioJack3_SwitchTR (핀 번호 = T, TN, R, RN, S)",
     "직접 만듦 Toccata:Jack_3.5mm_PJ-313 — 패드 이름을 T/TN/R/RN/S로 (통전 검사로 확인)"),
    ("Plug_TRS", None, "PLUG", "Connector_Audio:AudioPlug3", EXCL),
    ("Fuse", None, "FUSE", "Device:Fuse", EXCL + " — 인라인 홀더 BU914"),
    ("SW_SPST", None, "SW", "Switch:SW_SPST", EXCL + " — I/O 판"),
    ("Speaker", None, "SPK", "Device:Speaker (핀 1 = +)", EXCL),
    ("XT30U-M", None, "XT30M", "Connector:Conn_01x02_Pin", "Connector_AMASS:AMASS_XT30U-M_1x02_P5.0mm_Vertical (패드 1 = −) · " + EXCL),
    ("XT30U-F", None, "XT30F", "Connector:Conn_01x02_Socket", "Connector_AMASS:AMASS_XT30U-F_1x02_P5.0mm_Vertical (패드 1 = −) · " + EXCL),
    ("USB_C_Plug_USB2.0", None, "MT666", "Connector:USB_C_Plug_USB2.0 (A4 VBUS, A1 GND만 사용 — A5·B5·A6·A7·S1에 NC 표시)", EXCL),
    ("Barrel_Plug", None, "HUB", "Connector_Generic:Conn_01x02 (1 = 중심 +, 2 = 슬리브)", EXCL + " — 허브 어댑터 선"),
    ("HUSB238_module", None, "PDTRIG", "Toccata:HUSB238_Trigger (1·2 VOUT+, 3·4 GND)", EXCL),
    ("XL4016_module", None, "BUCK", "Toccata:XL4016_Buck (1 IN+, 2 IN−, 3 OUT+, 4 OUT−)", EXCL),
    ("XH-A232", None, "AMP", "Toccata:XH-A232 (1 L, 2 G, 3 R, 4 VCC, 5 GND, 6 L+, 7 L−, 8 R+, 9 R−)", EXCL),
    ("Apple_USB-C_dongle", None, "DONGLE", "Toccata:USB_Audio_Dongle (T, R, S)", EXCL),
    # △16 (rev C) R31 screen harness — every part is off-board (cable ends and bought modules)
    ("RPi5_Header", None, "PI5", "Toccata:RaspberryPi5 유닛 B = 40핀 헤더 (2 = 5V, 6 = GND만 그림; 4 = 5V 안 씀)", EXCL + " — Pi 5 보드"),
    ("Waveshare_7-DSI-TOUCH-C", None, "DISP7C", "Toccata:Waveshare_7-DSI-TOUCH-C (1 = 5V, 2 = GND: MX1.25 2핀. DSI 22핀은 선 목록 W605)", EXCL + " — 화면 모듈"),
    ("Dupont_FF", None, "JMPFF", "Connector_Generic:Conn_01x02 (1 = 빨강 5 V, 2 = 검정 GND)", EXCL + " — 점퍼 선 끝 (1핀 하우징 ×2)"),
    ("Dupont_MM", None, "JMPMM", "Connector_Generic:Conn_01x02 (1 = 빨강 5 V, 2 = 검정 GND)", EXCL + " — 점퍼 선 끝 (1핀 ×2)"),
    ("Housing_2.54_3P", None, "DPWR", "Connector_Generic:Conn_01x03 (1 = 빨강 5 V, 2 = 빈 칸 NC, 3 = 검정 GND)", EXCL + " — 동봉 전원선 끝"),
    ("MX1.25_2P", None, "DPWR2", "Connector_Generic:Conn_01x02 (1 = 5 V, 2 = GND — 우리 번호, 빨강 = 1)", EXCL + " — 동봉 전원선 끝"),
]

# fitted only on some boards (MB variants)
FIT = {"R301": "O1·O7", "R302": "O1", "R303": "O1", "R304": "없음 (비움)",
       "JP301": "O1·O3·O5·O7 닫음", "JP302": "O2·O3·O6·O7 닫음", "JP303": "O4~O7 닫음", "JP304": "모두 열림 (PB는 JP504)",
       "J302": "O1·O7만 L66 모듈 쪽 리드(W403·W413)를 아랫면에서 납땜, O2~O6 비움"}
FIT_COUNT = {"R301": 2, "R302": 1, "R303": 1, "R304": 0}


def kicad_for(sym, value):
    for sname, vre, key, ks, fp in KICAD:
        if sym == sname and (vre is None or re.search(vre, value or "")):
            return key, ks, fp
    return "", "", ""


def write_csv(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def board_of(sheet, ref):
    b = BOARDS.get(sheet.code)
    if not b:
        return "", 0
    if sheet.code == "SCH-04":
        return ("EL", 1) if ref[1:3] == "40" or ref.startswith("X40") or ref.startswith("J40") else ("ER", 1)
    if sheet.code == "SCH-05":
        return ("PS", 1) if ref.endswith("551") else ("PB", 1) if not ref.startswith("P501") else ("PS", 1)
    return b[0]


def export(built):
    net_rows, bom_rows, pinmap = [], [], []
    for s, path in built:
        if not getattr(s, "nets", None):
            continue
        for net, pins in sorted(s.nets.items()):
            for p in sorted(pins):
                ref, num = p.split(".", 1)
                name = s.pins[(ref, num)]["name"]
                brd, _ = board_of(s, ref)
                net_rows.append([s.code, brd, net if not net.startswith("~") else f"(이름 없음 {net[1:]})", ref, num, name])
        agg = {}
        for ref, m in s.parts.items():
            if ref.startswith("EXT") and s.code == "SCH-06":
                continue
            brd, n = board_of(s, ref)
            key, ks, fp = kicad_for(m.get("symbol"), m.get("value"))
            key = m.get("bomkey", key)       # △16: same symbol, different purchase line (cable end vs. other end)
            if s.code == "SCH-04" and key == "R1k":
                # △13: the sensor bar covers the whole top of the EL/ER board -> 1206 chip on the underside
                key, fp = "R1k1206", "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder (아랫면)"
            code, desc, shop = P.BOM.get(key, ("", "", "")) if key else ("", "", "")
            per = 5 if key == "R100" else 1
            if s.code == "SCH-03" and ref in FIT_COUNT:
                total = FIT_COUNT[ref]
            else:
                total = n * per
            bom_rows.append([s.code, brd, ref, m.get("value", ""), desc or m.get("symbol"), n, per, total,
                             FIT.get(ref, ""), ks, fp, code, shop])
            if key == "ZERO":
                c2, d2, sh2 = P.BOM["HDRZ"]
                bom_rows.append([s.code, brd, ref + "-HDR", "1×9 ×2", d2, n, 18, n * 18,
                                 "좌·우 열만 (아래 줄 없음), 몰드 뺌", "—", "Connector_PinHeader_2.54mm (풋프린트는 A 줄 참조)", c2, sh2])
            if key == "MUX":
                c2, d2, sh2 = P.BOM["HDR"]
                bom_rows.append([s.code, brd, ref + "-HDR", "1×16 + 1×8", d2, n, 24, n * 24,
                                 "모듈에 수 헤더가 들어 있으면 안 삼", "—", "Connector_PinHeader_2.54mm (풋프린트는 A 줄 참조)", c2, sh2])
            if key == "FUSE":
                c2, d2, sh2 = P.BOM["FUSEH"]
                bom_rows.append([s.code, brd, ref + "-HLD", "5×20 mm", d2, n, 1, n,
                                 "", "—", EXCL + " — 선 사이", c2, sh2])
    # RP2040 pad map
    for n, nm in P.RP2040_ZERO:
        use = {"GP26": "MUX_SIG / PED_ADC", "GP2": "MUX_S0", "GP3": "MUX_S1", "GP4": "MUX_S2", "GP5": "MUX_S3",
               "GP6": "ID0", "GP7": "ID1", "GP8": "ID2", "GP14": "PED_SEL", "3V3": "+3V3", "GND": "GND",
               "5V": "연결 금지 (USB VBUS)"}.get(nm, "NC")
        hx, hy = P.RP2040_HOLE[n]
        pinmap.append([n, P.WS_P1[nm], nm, P.RP2040_EDGE[n], f"{hx:.2f}", f"{hy:.2f}", use])
    write_csv("netlist.csv", ["도면", "보드", "넷", "부품", "핀", "핀 이름"], net_rows)
    write_csv("bom.csv", ["도면", "보드", "부품", "값", "부품 설명", "보드 수", "보드당", "전체 수량", "실장 조건",
                          "KiCad 심볼", "KiCad 풋프린트", "구매 목록 코드", "구매처"], bom_rows)
    write_csv("cables.csv", ["W", "종류", "길이", "한쪽", "다른 쪽", "심선", "구매 목록 코드"], [list(c) for c in S.CABLES])
    write_csv("rp2040_zero_pads.csv", ["패드 (dj505)", "Waveshare P1", "이름", "가장자리", "구멍 x (mm)", "구멍 y (mm, USB 가장자리 기준)", "Toccata 용도"], pinmap)
    mux = [[n, nm, "J1" if n <= 16 else "J2", n if n <= 16 else n - 16] for n, nm in P.MUX_CH + P.MUX_CTRL]
    write_csv("mux_module_pins.csv", ["심볼 핀", "이름", "모듈 헤더", "헤더 핀"], mux)
    wiring_mb(built)
    return net_rows, bom_rows


def mb_coord(ref, num, net):
    if ref == "A301":
        return S.zero_hole(int(num))
    if ref == "A302":
        name = dict(P.MUX_CH + P.MUX_CTRL)[int(num)]
        return S.mux_hole(name)
    if ref == "J301":
        n = int(num)
        return S.RIB_X0 + 2.54 * ((n - 1) // 2), S.RIB_Y[(n - 1) % 2]
    if ref == "J302":
        return S.EXT_X0 + 2.54 * (int(num) - 1), S.EXT_Y
    if ref in S.JP_POS:
        x, y = S.JP_POS[ref]
        return (x + 2.54, y) if net == "GND" else (x, y)
    if ref in S.R_EXT:
        x, y = S.R_EXT[ref]
        return (x, y) if num == "1" else (x + 7.62, y)
    if ref in S.TP_POS:
        return S.TP_POS[ref]
    return None


def crosses_slot(ca, cb):
    """True if a straight link would pass over the W1 r4.3 keep-out (x81.22~85.42, y<=173.2)."""
    kx0, kx1, _, ky1 = S.MB["keep"]
    return min(ca[0], cb[0]) < kx1 and max(ca[0], cb[0]) > kx0 and min(ca[1], cb[1]) < ky1


def wiring_mb(built):
    """Point-to-point wire list for the control board: per net a minimum spanning tree (Manhattan length),
    with a penalty for links that would cross the r4.3 keep-out (x81.22~85.42, y<=173.2): those go behind it, under the Zero."""
    s = [b[0] for b in built if b[0].code == "SCH-03"][0]
    rows = []
    for net, pins in sorted(s.nets.items()):
        pts = []
        for p in sorted(pins):
            ref, num = p.split(".", 1)
            if ref == "C301":
                continue
            c = mb_coord(ref, num, net)
            if c:
                pts.append((p, c))
        if len(pts) < 2:
            continue

        def cost(a, b):
            ca, cb = a[1], b[1]
            L = abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
            return L + (200 if crosses_slot(ca, cb) else 0)
        inside = [pts[0]]
        rest = pts[1:]
        while rest:
            best = min(((cost(i, r), i, r) for i in inside for r in rest), key=lambda t: t[0])
            _, pa, pb = best
            ca, cb = pa[1], pb[1]
            L = abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
            memo = "금지 구역을 건너야 함 → 제로 밑(y≥174.86, 핀 줄 사이 반 칸)으로 돌림" if crosses_slot(ca, cb) else ""
            rows.append([net, pa[0], f"{ca[0]:.2f}", f"{ca[1]:.2f}", pb[0], f"{cb[0]:.2f}", f"{cb[1]:.2f}", f"{L:.0f}", memo])
            inside.append(pb)
            rest.remove(pb)
    write_csv("wiring_MB.csv", ["넷", "시작", "x", "y", "끝", "x", "y", "직각 길이 (mm)", "메모"], rows)
    return rows
