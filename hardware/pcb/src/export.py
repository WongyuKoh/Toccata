"""CSV exports: netlist, BOM (with KiCad symbol/footprint), cables, RP2040 pad map, MB wiring list."""
import csv
import math
import os
import re

import harness as HN
import parts as P
import purchase as PU
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
     "dj505/RP2040-Zero-KiCAD 풋프린트를 복사해 드릴만 1.0 mm로 (핀 헤더용, 패드 번호는 dj505 심볼과 같음 — 다른 라이브러리 풋프린트는 번호가 다를 수 있어 쓰지 않음)"),
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
    ("Fuse", None, "FUSE", "Device:Fuse (Value = 5A ATO)", EXCL + " — ATC/ATO 블레이드 인라인 홀더 (사용자 보유, 선 사이)"),
    ("SW_DPST", None, "SW", "Switch:SW_DPST (1–2 회로 A, 3–4 회로 B — 두 회로 나란히)", EXCL + " — 뒤판 출력물 패널 구멍 19 × 13"),
    ("SW_SPST", None, "SW", "Switch:SW_SPST", EXCL),
    ("Conn_01x04", None, "PADS", "Connector_Generic:Conn_01x04 (1 T, 2 TN, 3 R, 4 S)", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical (패드만, 선 직접 납땜)"),
    ("Speaker", None, "SPK", "Device:Speaker (핀 1 = +)", EXCL),
    # △18 speaker joints X703~X706 = XT60 (value contains "SPK"); must come before the general XT60 rows
    ("XT60-M", r"SPK", "XT60M_SPK", "Connector:Conn_01x02_Pin (1 = −, 2 = +)", "Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical (패드 1 = −, 실물 표시로 확인) · " + EXCL + " — 앰프 쪽 스피커 리드"),
    ("XT60-F", r"SPK", "XT60F_SPK", "Connector:Conn_01x02_Socket (1 = −, 2 = +)", "Connector_AMASS:AMASS_XT60-F_1x02_P7.20mm_Vertical (패드 1 = −, 실물 표시로 확인) · " + EXCL + " — 스피커 피그테일"),
    ("USB_C_Plug_USB2.0", None, "C24", "Connector:USB_C_Plug_USB2.0 (A4 VBUS, A1 GND만 사용 — A5·B5·A6·A7·S1에 NC 표시)", EXCL + " — C24 BT663 플러그"),
    ("Barrel_Plug", None, "HUBDC", "Connector_Generic:Conn_01x02 (1 = 중심 +, 2 = 슬리브)", EXCL + " — 허브 어댑터 선"),
    # △17 (rev D) battery input: pack + XT60 pair, all off-board
    ("LiFePO4_pack", None, "BATT", "Device:Battery (1 = +, 2 = −; Value = LiFePO4 12.8V 6Ah)", EXCL + " — 전지 팩 (BMS 내장)"),
    ("XT60-F", None, "XT60F", "Connector:Conn_01x02_Socket (1 = −, 2 = +)", "Connector_AMASS:AMASS_XT60-F_1x02_P7.20mm_Vertical (패드 1 = −, 실물 표시로 확인) · " + EXCL + " — 팩 리드"),
    ("XT60-M", None, "XT60M", "Connector:Conn_01x02_Pin (1 = −, 2 = +)", "Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical (패드 1 = −, 실물 표시로 확인) · " + EXCL + " — W601 하네스"),
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
        if ref.endswith("551") or ref == "P501":
            return ("PS", 1)
        if ref == "J501":
            return ("J501 조각", 1)
        return ("PB", 1)
    if sheet.code == "SCH-07":
        if ref == "J701":
            return ("J701 (볼 포켓, 기판 없음)", 1)
        if ref in ("J702", "C701", "C702", "C703", "C704", "R701", "R702"):
            return ("J702 기판", 1)
        return ("CU", 1)
    return b[0]


# boards themselves and the off-schematic parts that the board / wiring sheets name (BRD-04..06): one BOM row each
EXTRA = [
    # (sheet, board, ref, value, BOM key, per board, boards, fit, KiCad symbol, footprint)
    ("SCH-02", "SB", "PCB-SB", "161.6 × 15.24 6행", "PERF1218", 1, 7, "12 × 18 기판을 띠로 자름", "—", "Edge.Cuts x1.0~162.6 × y60.65~75.89 (BRD-02)"),
    ("SCH-03", "MB", "PCB-MB", "70 × 50", "PERF", 1, 7, "BE163 한 장에서 두 조각 (지그 P-MB)", "—", "Edge.Cuts x47.25~117.25 × y145.5~195.5, 홈 x81.92~84.72 × y≤172 (BRD-01)"),
    ("SCH-04", "EL", "PCB-EL", "45.5 × 15.24 6행", "PERF1218", 1, 1, "12 × 18 기판 띠", "—", "Edge.Cuts x1.0~46.5 (BRD-02)"),
    ("SCH-04", "ER", "PCB-ER", "22.0 × 15.24 6행", "PERF1218", 1, 1, "12 × 18 기판 띠", "—", "Edge.Cuts x1.0~23.0 (BRD-02)"),
    ("SCH-05", "PB", "PCB-PB", "70 × 50", "PERF", 1, 1, "BE163 조각 (지그 P-PED)", "—", "Edge.Cuts x426.5~476.5 × y244~314, 90° 돌림 (BRD-03)"),
    ("SCH-05", "J501 조각", "PCB-J501", "25 × 24 (9 × 9 구멍)", "PERF1218", 1, 1, "12 × 18 기판 자투리", "—", "x450~475 × y316.5~340.5, 구멍·패드 BRD-07"),
    ("SCH-05", "PS", "PCB-PS", "7 × 5 구멍 (17.78 × 12.7)", "PERF1218", 1, 1, "12 × 18 자투리", "—", "로컬 구멍·배선 BRD-07"),
    ("SCH-07", "J702 기판", "PCB-J702", "30 × 25 (12 × 10 구멍)", "PERF1218", 1, 1, "12 × 18 기판 자투리", "—", "x505~535 × y255~280, 나사 Ø3.2 (508, 258)·(532, 277), 구멍·배선 BRD-07"),
    ("SCH-06", "CU", "A604", "NEXTU 710U3", "HUB", 1, 1, "", "—", EXCL + " — 허브 (SCH-01 블록)"),
    ("SCH-07", "CU", "X701", "IH190 젠더", "GENDER", 1, 1, "", "—", EXCL + " — 동글 → Pi USB-A"),
    ("SCH-01", "CU", "W201~W208", "USB-A → C " + " · ".join("%s ×%d" % (HN.m_txt(m), sum(1 for v in HN.USB_BUY.values() if v == m))
                                                         for m in sorted(set(HN.USB_BUY.values()), reverse=True)), "USBAC", 1, 8, HN.usb_group_txt() + " · W208 " + HN.m_txt(HN.USB_BUY.get("PED", 0.5)), "—", EXCL + " — 선"),
    ("SCH-01", "CU", "W209", "USB-A → B 25 cm", "C25", 1, 1, "", "—", EXCL + " — 선"),
    ("SCH-06", "CU", "W605", "FFC 22P 300 B형", "FFC22B", 1, 1, "A형은 보험 (같은 수)", "—", EXCL + " — 선"),
    ("SCH-07", "CU", "W703~W706 선", "16 AWG 2심", "SPKW", 1, 1, "18 AWG도 됨", "—", EXCL + " — 선"),
    ("SCH-01", "전체", "열수축", "빨강 · 파랑 포함", "SHRINK", 1, 1, "XT60 색 표시", "—", "—"),
]


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
            st = PU.status(key)["text"] if key else ""
            bom_rows.append([s.code, brd, ref, m.get("value", ""), desc or m.get("symbol"), n, per, total,
                             FIT.get(ref, ""), ks, fp, code, shop, st])
            if key == "ZERO":
                c2, d2, sh2 = P.BOM["HDRZ"]
                bom_rows.append([s.code, brd, ref + "-HDR", "1×9 ×2", d2, n, 18, n * 18,
                                 "좌·우 열만 (아래 줄 없음), 몰드 뺌", "—", "Connector_PinHeader_2.54mm (풋프린트는 A 줄 참조)", c2, sh2,
                                 PU.status("HDRZ")["text"]])
            if key == "MUX":
                c2, d2, sh2 = P.BOM["HDR"]
                bom_rows.append([s.code, brd, ref + "-HDR", "1×16 + 1×8", d2, n, 24, n * 24,
                                 "모듈에 수 헤더가 들어 있으면 안 삼", "—", "Connector_PinHeader_2.54mm (풋프린트는 A 줄 참조)", c2, sh2,
                                 PU.status("HDR")["text"]])
            if key == "FUSE":
                c2, d2, sh2 = P.BOM["FUSEH"]
                bom_rows.append([s.code, brd, ref + "-HLD", "ATC/ATO 인라인", d2, n, 1, n,
                                 "12 AWG 꼬리를 16 AWG에 이음", "—", EXCL + " — 선 사이", c2, sh2, PU.status("FUSEH")["text"]])
    # RP2040 pad map
    for n, nm in P.RP2040_ZERO:
        use = {"GP26": "MUX_SIG / PED_ADC", "GP2": "MUX_S0", "GP3": "MUX_S1", "GP4": "MUX_S2", "GP5": "MUX_S3",
               "GP6": "ID0", "GP7": "ID1", "GP8": "ID2", "GP14": "PED_SEL", "3V3": "+3V3", "GND": "GND",
               "5V": "연결 금지 (USB VBUS)"}.get(nm, "NC")
        hx, hy = P.RP2040_HOLE[n]
        pinmap.append([n, P.WS_P1[nm], nm, P.RP2040_EDGE[n], f"{hx:.2f}", f"{hy:.2f}", use])
    for (sc, brd, ref, val, key, per, nb, fit, ks, fp) in EXTRA:
        code, desc, shop = P.BOM[key]
        bom_rows.append([sc, brd, ref, val, desc, nb, per, nb * per, fit, ks, fp, code, shop, PU.status(key)["text"]])
    write_csv("netlist.csv", ["도면", "보드", "넷", "부품", "핀", "핀 이름"], net_rows)
    write_csv("bom.csv", ["도면", "보드", "부품", "값", "부품 설명", "보드 수", "보드당", "전체 수량", "실장 조건",
                          "KiCad 심볼", "KiCad 풋프린트", "구매 목록 코드", "구매처", "구매 상태 (최종 목록)"], bom_rows)
    write_csv("cables.csv", ["W", "선", "자르는 길이 (mm)", "한쪽", "다른 쪽", "심", "구매 목록 코드"], [list(c) for c in S.CABLES])
    write_csv("harness.csv", ["W", "이름", "선", "심 번호", "색", "넷", "끝 A", "A 핀", "끝 B", "B 핀", "CAD 경로 (mm)", "자르는 길이",
                              "수축 튜브", "경로 근거"], HN.harness_rows())
    import boards2 as B2
    import boards3 as B3
    write_csv("wiring_PB.csv", ["넷", "선 번호", "경로 (모델 좌표 x, y)", "직각 길이 (mm)", "선"], B2.wiring_pb_rows())
    write_csv("wiring_SB.csv", ["선 (센서 OUT / 버스)", "건반", "넷", "시작 구멍 x", "시작 구멍 y", "J201 핀", "핀 x", "핀 y", "줄", "경로 (모듈 좌표 x, y)", "길이 (mm)"],
              B3.wiring_sb_rows())
    write_csv("wiring_small.csv", ["기판", "넷", "경로 (x, y)", "길이 (mm)", "선"], B3.wiring_small_rows())
    write_csv("pads_small.csv", ["기판", "부품", "핀", "넷", "i (c)", "j (r)", "x", "y", "좌표"], B3.pads_small_rows())
    write_csv("pads_PB.csv", ["부품", "핀", "넷", "x", "y", "격자 i (u 방향)", "격자 j (v 방향)", "지그 u = y − 244", "지그 v = 476.5 − x"],
              B2.pb_pad_rows())
    pin_tables()
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
    """Control-board underside wires, routed on the lattice by mbroute.py (BRD-08): one row per wire with every corner point."""
    import boards3 as B3
    rows = B3.wiring_mb_rows()
    write_csv("wiring_MB.csv", ["번호", "넷", "시작", "x", "y", "끝", "x", "y", "경로 (꺾인 점, 모듈 좌표)", "길이 (mm)", "꺾임 수"], rows)
    return rows


KEYS12 = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(midi):
    return KEYS12[midi % 12] + str(midi // 12 - 1)


def mux_map_rows():
    """mux channel -> key / MIDI note for every octave module (firmware table)."""
    rows = []
    for ch in range(16):
        r = [f"C{ch}"]
        for k in range(1, 8):
            if ch < 12:
                m = 24 + 12 * (k - 1) + ch
                r.append(f"{note_name(m)} = {m}")
            elif k == 1 and ch <= 14:
                m = 21 + (ch - 12)
                r.append(f"EXT{ch-11} {note_name(m)} = {m}")
            elif k == 7 and ch == 12:
                r.append("EXT1 C8 = 108")
            else:
                r.append("—")
        rows.append(r)
    return rows


def zero_rows():
    """RP2040-Zero pad -> net on the MB (all 7) and on the PB."""
    mb = {"GP26": "MUX_SIG (ADC0)", "GP2": "MUX_S0", "GP3": "MUX_S1", "GP4": "MUX_S2", "GP5": "MUX_S3", "GP6": "ID0 (JP301)",
          "GP7": "ID1 (JP302)", "GP8": "ID2 (JP303)", "GP14": "PED_SEL (JP304 열림)", "3V3": "+3V3 (센서·먹스·EXT 급전)", "GND": "GND",
          "5V": "연결 금지 (USB VBUS)"}
    pb = {"GP26": "PED_ADC (ADC0)", "GP14": "PED_SEL (JP504 닫음 = GND)", "3V3": "+3V3 (R503 → 페달 링)", "GND": "GND",
          "5V": "연결 금지 (USB VBUS)"}
    rows = []
    for n, nm in P.RP2040_ZERO:
        hx, hy = P.RP2040_HOLE[n]
        rows.append([n, P.WS_P1[nm], nm, P.RP2040_EDGE[n], mb.get(nm, "NC"), pb.get(nm, "NC"),
                     "헤더" if n <= 18 else "헤더 없음 (아래 줄)", f"{hx:.2f}", f"{hy:.2f}"])
    return rows


def id_rows():
    rows = []
    for m in range(1, 8):
        b = S.ID_BITS[m]
        rows.append([f"O{m}", "닫음" if b[0] else "—", "닫음" if b[1] else "—", "닫음" if b[2] else "—", "열림", f"Toccata O{m}",
                     f"{24 + 12 * (m - 1)} ({note_name(24 + 12 * (m - 1))})", HN.HUB_PORTS.get(f"O{m}", "")])
    rows.append(["PED", "—", "—", "—", "닫음 (JP504)", "Toccata PED", "CC64", HN.HUB_PORTS.get("PED", "")])
    return rows


def sb_rows():
    rows = []
    for i, k in enumerate(S.KEYS):
        col = min(0.63 + 2.54 * j for j in range(1, 70) if 0.63 + 2.54 * j >= S.SENSOR_X[i] + 3.0)
        rows.append([f"U{201+i}", k, f"{S.SENSOR_X[i]:.3f}", f"{col:.2f}", f"C{201+i}", S.NET[k], f"C{i}", i + 3])
    return rows


def pin_tables():
    write_csv("pins_rp2040.csv", ["패드 (dj505)", "Waveshare P1", "이름", "가장자리", "MB O1~O7 넷", "PB 넷", "헤더", "구멍 x", "구멍 y (USB 가장자리 기준)"],
              zero_rows())
    write_csv("mux_map.csv", ["먹스 채널"] + [f"O{k}" for k in range(1, 8)], mux_map_rows())
    write_csv("id_jumpers.csv", ["보드", "JP301 GP6", "JP302 GP7", "JP303 GP8", "JP304/JP504 GP14", "USB 이름", "C 건반 MIDI", "허브 포트"], id_rows())
    write_csv("sb_sensors.csv", ["센서", "건반", "소자 x", "리드 구멍 x", "100 nF", "넷", "먹스 채널", "리본 심"], sb_rows())


def check_refs(built, bom_rows):
    """every refdes printed on the board / wiring sheets must have a BOM row (W cable ids excluded)."""
    import re
    refs = {r[2] for r in bom_rows}
    for r in list(refs):
        if r.startswith("R503"):
            refs.add("R503")
    miss = {}
    for s, path in built:
        if not s.code.startswith("BRD"):
            continue
        txt = open(path, encoding="utf-8").read()
        for t in re.findall(r">([^<]*)</text>", txt):
            # refdes = prefix + sheet number x 100 + n (2xx..7xx); product names like XH-A232 or Coms BT663 are not refdes
            for tok in re.findall(r"(?<![\w-])(?:A|BT|C|F|J|JP|LS|P|R|SW|TP|U|X)[2-7]\d{2}\b", t):
                if tok in ("BT663",):
                    continue
                if tok not in refs:
                    miss.setdefault(s.code, set()).add(tok)
    return {k: sorted(v) for k, v in miss.items()}
