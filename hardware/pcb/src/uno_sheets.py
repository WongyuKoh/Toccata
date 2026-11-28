"""Toccata circuit — Arduino version (U1, 2026-11-23): ONE Arduino Uno R3 + a laptop instead of 8 RP2040-Zero + Pi 5.

The Raspberry Pi version (rev E, sheets.py) stays as it is. This module draws the sheets that differ:
  U-01 system + cable list + what changes, U-02 octave control board MB-U, U-03 bus board UB + Uno + pedal input,
  U-04 power + audio. SB (SCH-02), EL·ER (SCH-04), the pedal sensor PS and the audio chain from J701 on are the same
  boards; their supply net is +5V_B instead of +3V3.
Run build_uno.py (same checks as build.py: nets re-derived from the drawing, text overlaps).
"""
import math

from sch import Sheet, sym_R, sym_C, sym_box, sym_conn, sym_conn2, sym_fuse, sym_switch_dpst, sym_plug, sym_tp, sym_conn_pos
import parts as P
import harness as HN

REV_U = dict(rev="U1", date="2026-11-23")
TOTAL = 4
BASIS = "rev E + 아두이노 U1"
KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NET = {k: "HALL_" + k.replace("#", "S") for k in KEYS}
PWR = ("GND", "+5V_B", "+12V8")
# SB ribbon (SCH-02 J201 = SCH-03 J301), supply now +5V_B
RIBBON = ["+5V_B", "GND"] + [NET[k] for k in KEYS] + ["GND", "+5V_B"]
# MB-U J303 -> 10-wire ribbon -> UB J80m (IDC 2x5: wire n = pin n)
BUS = ["GND", "MUX_SIG", "GND", "MUX_S0", "MUX_S1", "MUX_S2", "MUX_S3", "MUX_EN", "+5V_B", "GND"]
BUS_TXT = ["GND", "SIG (먹스 출력)", "GND (SIG 옆 차폐)", "S0", "S1", "S2", "S3", "EN (LOW = 켜짐)", "+5V_B (센서·먹스)", "GND"]
UNO_EN = {m: "D%d" % (5 + m) for m in range(1, 8)}          # O1 = D6 .. O7 = D12
UNO_S = {k: "D%d" % (2 + k) for k in range(4)}             # S0 = D2 .. S3 = D5
SENS_MA = (3.0, 5.0)                                       # WSH137 at 5 V: typ / max (datasheet, research/hall.md)
N_SENS = 7 * 12 + 4 + 1                                    # 84 + EL 3 + ER 1 + pedal


def ribbon_cut(tag):
    """W80m cut length: the CAD path of the USB cable it replaces (MB -> hub port, plug included) + 80, up to 50 mm."""
    p = HN.usb_len(tag) or 1000.0
    return int(math.ceil((p + 80.0) / 50.0) * 50)


CUTS = {m: ribbon_cut("O%d" % m) for m in range(1, 8)}


def nend(s, x, y, name, side="R", up=True):
    if name in PWR:
        s.pwr(x, y, name)
    else:
        s.label(x, y, name, side, up=up)


def ex(e, net, *pins):
    e.setdefault(net, []).extend(pins)


def hr(s, ref, val, x, y, **kw):
    """Horizontal resistor centred at (x, y); returns (left pin, right pin)."""
    s.place(sym_R(), ref, val, x, y, rot=90, ref_at=kw.get("ref_at", (0, -3.0, "middle")),
            val_at=kw.get("val_at", (0, 4.9, "middle")), hide_val=kw.get("hide_val", False))
    a, b = s.pin(ref, 1), s.pin(ref, 2)
    return (a, b) if a[0] < b[0] else (b, a)


def pnum(s, ref, pt):
    return "1" if s.pin(ref, 1) == pt else "2"


def mux_sym():
    left = [(P.mux_pin(f"C{i}"), f"C{i}") for i in range(16)]
    R = ["SIG", None, "S0", "S1", "S2", "S3", None, "EN", None, "VCC", "GND"]
    right = [None if n is None else (P.mux_pin(n), n) for n in R]
    return sym_box("CD74HC4067_module", left, right, width=30, cls="mod", rows=16)


def uno_sym():
    L = ["VIN", "5V", "3V3", "GND", "AREF", "IOREF", "RESET", None, "A0", "A1", "A2", "A3", "A4", "A5"]
    R = [f"D{i}" for i in range(14)] + ["GND2"]
    left = [None if n is None else (n, n) for n in L]
    right = [(n, "GND" if n == "GND2" else n) for n in R]
    return sym_box("Arduino_UNO_R3", left, right, width=34, cls="mod", rows=15)


def power_budget():
    lo, hi = (N_SENS * a / 1000.0 for a in SENS_MA)
    w5 = [5.1 * lo, 5.1 * hi]
    buck = [w / 0.85 for w in w5]                 # XL4016 at a light load: assume 85 %
    amp = (2.0, 6.0)                              # same conservative amp average as SCH-06
    tot = [buck[0] + amp[0], buck[1] + amp[1]]
    run = [76.8 * 0.9 / t for t in tot]
    return dict(a=(lo, hi), w5=w5, tot=tot, run=run)


# ================================================================== U-02 octave control board MB-U
def u02():
    s = Sheet("U-02", 2, TOTAL, "옥타브 제어 기판 MB-U (아두이노 버전)",
              "RP2040-Zero를 빼고 4067 먹스만 남긴 기판. 센서 12개 + EXT 4채널을 먹스 하나로 골라 리본 10심(J303)으로 가운데 UB·우노에 보낸다. O1~O7 7장이 모두 같다(ID 점퍼 없음).",
              "MB-U", qty="MB-U × 7", basis=BASIS, **REV_U)
    e = {}
    j = sym_conn2("Conn_02x08_Odd_Even", 8, width=12)
    s.place(j, "J301", "리본 16심 입력 2×8", 45, 30, ref_at=(0, -2.2), val_at=(0, 44.0))
    for i, nm in enumerate(RIBBON):
        px, py = s.pin("J301", i + 1)
        d = -1 if (i + 1) % 2 else 1
        L = 20 if nm in PWR else 5
        s.wire((px, py), (px + d * L, py))
        nend(s, px + d * L, py, nm, "L" if d < 0 else "R")
        ex(e, nm, f"J301.{i+1}")
    s.text(22, 81.5, "← SB J201 (SCH-02 그대로, 리본 선 n = 핀 n)", "cabt", size=2.2)
    mx, my = 110, 30
    s.place(mux_sym(), "A302", "CD74HC4067 16채널 먹스 모듈", mx, my, val_at=(0, 90.5), part_at=(0, 92.8),
            part="파츠파츠 PP-A324 (Pi 버전과 같은 자리) · VCC = +5V_B")
    for i in range(16):
        px, py = s.pin("A302", P.mux_pin(f"C{i}"))
        s.wire((px, py), (px - 7.5, py))
        net = NET[KEYS[i]] if i < 12 else f"EXT{i-11}"
        s.label(px - 7.5, py, net, "L")
        ex(e, net, f"A302.{P.mux_pin(f'C{i}')}")
    sx, sy = s.pin("A302", P.mux_pin("SIG"))
    s.wire((sx, sy), (sx + 10, sy)); s.label(sx + 10, sy, "MUX_SIG", "R"); ex(e, "MUX_SIG", f"A302.{P.mux_pin('SIG')}")
    for k in range(4):
        px, py = s.pin("A302", P.mux_pin(f"S{k}"))
        s.wire((px, py), (px + 10, py)); s.label(px + 10, py, f"MUX_S{k}", "R")
        ex(e, f"MUX_S{k}", f"A302.{P.mux_pin(f'S{k}')}")
    px, py = s.pin("A302", P.mux_pin("EN"))
    s.wire((px, py), (px + 10, py)); s.label(px + 10, py, "MUX_EN", "R"); ex(e, "MUX_EN", f"A302.{P.mux_pin('EN')}")
    s.text(px + 1.5, py + 3.6, "Pi 버전은 GND · 여기는 우노가 고름", "notes", size=1.9)
    vx, vy = s.pin("A302", P.mux_pin("VCC"))
    gx, gy = s.pin("A302", P.mux_pin("GND"))
    s.wire((vx, vy), (vx + 20, vy))
    s.pwr(vx + 7.5, vy, "+5V_B")
    s.place(sym_C(), "C301", "100n", vx + 20, vy + 5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.wire((gx, gy), (gx + 5, gy)); s.pwr(gx + 5, gy, "GND")
    s.pwr(vx + 20, vy + 10, "GND")
    ex(e, "+5V_B", f"A302.{P.mux_pin('VCC')}", "C301.1")
    ex(e, "GND", f"A302.{P.mux_pin('GND')}", "C301.2")
    # J303 bus pads (ribbon soldered here; IDC socket only at the UB end)
    jx, jy = 236, 30
    s.place(sym_conn("Conn_01x10", 10, side="L", width=6), "J303", "버스 패드 1×10 (2.54)", jx, jy,
            ref_at=(0, -2.2), val_at=(-6, 54.5), part="10심 리본을 바로 납땜 (주 2)", part_at=(-6, 56.8))
    for i, nm in enumerate(BUS):
        px, py = s.pin("J303", i + 1)
        L = 32 if nm in PWR else 7.5
        s.wire((px, py), (px - L, py))
        nend(s, px - L, py, nm, "L")
        ex(e, nm, f"J303.{i+1}")
        s.text(jx + 9, py + 0.8, BUS_TXT[i], "notes", size=2.0)
    s.cable((jx + 3, jy + 50), (jx + 3, jy + 58))
    s.text(196, jy + 63, "W80m 리본 10심 → UB J80m (U-03)", "cabt", size=2.2)
    s.text(196, jy + 66.2, "뒷벽 개구 x76.45~91.55로 나감", "notes", size=2.0)
    # J302 EXT (same pads as rev E, pin 6 = +5V_B)
    jn = ["GND", "EXT1", "EXT2", "EXT3", "EXT4", "+5V_B"]
    s.place(sym_conn("Conn_01x06", 6, side="L", width=6), "J302", "EXT 패드 1×6 (2.54)", 345, 30,
            ref_at=(0, -2.2), val_at=(-6, 34.5))
    for i, nm in enumerate(jn):
        px, py = s.pin("J302", i + 1)
        L = 20 if nm in PWR else 7.5
        s.wire((px, py), (px - L, py))
        nend(s, px - L, py, nm, "L")
        ex(e, nm, f"J302.{i+1}")
        s.text(353, py + 0.8, ["GND (XH 1번)", "EXT1 → C12", "EXT2 → C13", "EXT3 → C14", "EXT4 → C15 (비움)", "+5V_B (XH 끝번)"][i], "notes", size=2.0)
    s.text(318, 68.5, "O1·O7만: EXT 선·끝 부속 SCH-04 그대로 (전원만 5 V)", "notes", size=2.0)
    s.box(282, 80, 114, 42, "EXT 풀다운 (rev E △8 그대로) — O1: R301~R303, O7: R301만")
    for n in range(1, 5):
        x0 = 292.5 + (n - 1) * 26
        rp = f"R{300+n}"
        s.label(x0, 90, f"EXT{n}", "R")
        s.wire((x0, 90), (x0, 92.5))
        s.place(sym_R(), rp, "100k", x0, 100, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
        s.pwr(*s.pin(rp, 2), "GND")
        ex(e, f"EXT{n}", f"{rp}.1")
        ex(e, "GND", f"{rp}.2")
    s.text(286, 118.5, "끝 부속을 빼도 EXT가 뜨지 않게 (0.15 V 아래 = 센서 없음)", "notes", size=1.9)
    for i, (ref, net) in enumerate((("TP301", "+5V_B"), ("TP302", "GND"), ("TP303", "MUX_SIG"))):
        tx, ty = 150 + i * 12.5, 112.5
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        if net == "GND":
            s.wire((tx, ty), (tx, ty + 2.5)); s.pwr(tx, ty + 2.5, "GND")
        elif net == "+5V_B":
            s.wire((tx, ty), (tx, ty + 2.5), (tx - 5, ty + 2.5)); s.pwr(tx - 5, ty + 2.5, "+5V_B")
        else:
            s.wire((tx, ty), (tx, ty + 5)); s.label(tx, ty + 5, net, "R", up=False)
        ex(e, net, f"{ref}.1")
    rows = []
    for m in range(1, 8):
        extx = {1: "C12~14 → A0·A#0·B0 (21~23)", 7: "C12 → C8 (108)"}.get(m, "—")
        part = {1: "J302 + R301~R303", 7: "J302 + R301"}.get(m, "없음")
        rows.append([f"O{m}", f"W80{m} · {CUTS[m]}", f"J80{m}", f"{UNO_EN[m]}", f"{24+12*(m-1)}~{35+12*(m-1)}", extx, part])
    s.table(15, 132, ["보드", "리본 · 자르는 길이", "UB 포트", "우노 EN 핀", "MIDI C~B", "EXT 입력", "EXT 부품"],
            rows, [11, 32, 15, 20, 20, 46, 32], title="모듈별 — 기판은 7장 모두 같고, 어느 UB 포트에 꽂느냐가 번호를 정한다", mono_cols=(0,))
    pm = [[str(i + 1), BUS[i], BUS_TXT[i]] for i in range(10)]
    s.table(15, 172, ["J303 / IDC", "넷", "뜻"], pm, [20, 24, 46], title="버스 리본 10심 (빨간 줄 = 1번)", mono_cols=(0, 1))
    s.para(190, 132, [
        "주",
        "1. rev E MB(80 × 120 통짜 BE163)에서 A301 RP2040-Zero·핀 헤더·JP301~JP304(ID·PED 점퍼)를 뺀다. 먹스·J301·J302·R301~R304·C301 자리는 그대로.",
        "    이미 조립한 MB: 제로를 헤더째 뽑고, 먹스 EN–GND 점퍼선(rev E)을 끊어 J303.8로 잇는다. 제로 자리에 J303 패드 10개를 둔다.",
        "2. J303: 10심 리본을 기판에 바로 납땜(커넥터 없음, 높이 문제 없음). 리본은 제로 USB 케이블이 지나던 뒷벽 개구(폭 15.1)로 나간다 — 리본 폭 12.7.",
        "    리본 끝은 우노 쪽에서만 IDC 2×5 소켓을 눌러 끼운다. 모듈을 뺄 때는 UB 쪽 소켓을 뽑는다(Pi 버전의 허브 포트와 같은 역할).",
        "3. 전원: 센서·먹스·끝 부속 모두 +5V_B(전지 → XL4016 5.1 V, UB에서 나눔). WSH137은 3~12 V에서 동작, 사양표도 5 V 기준.",
        f"    5 V에서 약 2.5 V(0 mT) + 약 45 mV/mT. 센서 {N_SENS}개 × {SENS_MA[0]:.0f}~{SENS_MA[1]:.0f} mA = 약 {N_SENS*SENS_MA[0]/1000:.2f}~{N_SENS*SENS_MA[1]/1000:.2f} A — 우노 5 V(USB 0.5 A)로는 부족해 버스에서 받는다.",
        "4. EN: 먹스 모듈 안에 EN–GND 10 kΩ 풀다운이 있다 → 리본을 뽑거나 우노가 리셋 중이면 켜짐. UB의 SIG 1 kΩ(R841~R847)가 서로 부딪는 전류를 막는다.",
        "5. 모듈 번호(O1~O7)는 기판이 아니라 UB 포트가 정한다 → 리본 끝 소켓에 O 번호를 적어 둔다. 바꿔 꽂으면 음이 옥타브째 바뀔 뿐 고장은 아니다.",
        "6. 펌웨어(firmware/uno): EN 하나만 LOW → S0~S3 → 변환. 옥타브를 바꿀 때 첫 변환은 버린다. 유령 거름·재무장 규칙은 rev E SCH-03 주 9 그대로.",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


# ================================================================== U-03 bus board UB + Arduino Uno + pedal input
def u03():
    s = Sheet("U-03", 3, TOTAL, "버스 기판 UB + Arduino Uno + 페달 입력",
              "옥타브 리본 7개를 받아 S0~S3를 나누고 EN을 하나씩, SIG를 하나로 모아 우노 A0에. 페달 잭은 우노 A1에 바로. 우노는 USB로 노트북에 — 노트북이 음원·게임을 돌린다.",
              "UB · A801", qty="UB × 1 · Uno × 1", basis=BASIS, **REV_U)
    e = {}
    ux, uy = 160, 30
    s.place(uno_sym(), "A801", "Arduino Uno R3 (정품 또는 CH340 호환)", ux, uy, val_at=(0, 84.5), part_at=(0, 86.8),
            part="가운데 유닛 Pi 자리 · USB-B → 노트북 (W811)")
    up = lambda n: s.pin("A801", n)  # noqa: E731
    for n in ("VIN", "3V3", "AREF", "IOREF", "RESET", "A3", "A4", "A5", "D0", "D1", "D13"):
        s.nc(*up(n))
    x, y = up("5V"); s.nc(x, y)
    s.text(x - 3, y - 1.0, "5V: 버스에 잇지 않음", "notes", anchor="end", size=1.9)
    for g in ("GND", "GND2"):
        x, y = up(g)
        d = -1 if g == "GND" else 1
        s.wire((x, y), (x + d * 5, y)); s.pwr(x + d * 5, y, "GND"); ex(e, "GND", f"A801.{g}")
    s.text(ux + 44, uy + 8.0, "D0·D1 = USB 시리얼(115200)", "notes", size=1.9)
    s.text(ux + 44, uy + 73.0, "D13 = 보드 LED", "notes", size=1.9)
    # D2..D12 -> 1 k series -> bus nets
    for k in range(4):
        n = UNO_S[k]
        x, y = up(n)
        a, b = hr(s, f"R80{k+1}", "1k", x + 15, y, ref_at=(-6.2, -0.9, "end"), hide_val=True)
        s.wire((x, y), a)
        s.wire(b, (b[0] + 4, y)); s.label(b[0] + 4, y, f"MUX_S{k}", "R")
        ex(e, f"~U_{n}", f"A801.{n}", f"R80{k+1}.{pnum(s, f'R80{k+1}', a)}")
        ex(e, f"MUX_S{k}", f"R80{k+1}.{pnum(s, f'R80{k+1}', b)}")
    for m in range(1, 8):
        n = UNO_EN[m]
        x, y = up(n)
        ref = f"R81{m}"
        a, b = hr(s, ref, "1k", x + 15, y, ref_at=(-6.2, -0.9, "end"), hide_val=True)
        s.wire((x, y), a)
        s.wire(b, (b[0] + 4, y)); s.label(b[0] + 4, y, f"EN_O{m}", "R")
        ex(e, f"~U_{n}", f"A801.{n}", f"{ref}.{pnum(s, ref, a)}")
        ex(e, f"EN_O{m}", f"{ref}.{pnum(s, ref, b)}")
    s.text(ux + 52, uy + 2.0, "R801~R804 · R811~R817 = 1 kΩ", "notes", size=1.9)
    # A0 <- R808 2.2k <- SIG_BUS ; A1 <- PED_ADC ; A2 <- V_MON
    x, y = up("A0")
    a, b = hr(s, "R808", "2.2k", x - 15, y, ref_at=(0, -3.0, "middle"), hide_val=True)
    s.text(x - 15, y - 6.0, "2.2 kΩ", "val", anchor="middle", size=2.4)
    s.wire(b, (x, y)); s.wire(a, (a[0] - 4, y)); s.label(a[0] - 4, y, "SIG_BUS", "L")
    ex(e, "~U_A0", "A801.A0", f"R808.{pnum(s, 'R808', b)}")
    ex(e, "SIG_BUS", f"R808.{pnum(s, 'R808', a)}")
    x, y = up("A1"); s.wire((x, y), (x - 29, y)); s.label(x - 29, y, "PED_ADC", "L", up=False); ex(e, "PED_ADC", "A801.A1")
    x, y = up("A2"); s.wire((x, y), (x - 29, y)); s.label(x - 29, y, "V_MON", "L", up=False); ex(e, "V_MON", "A801.A2")
    # SIG merge box
    s.box(14, 22, 84, 50, "SIG 합치기 — 포트마다 1 kΩ (먹스끼리 부딪힘 방지)")
    bx = 72.0
    for m in range(1, 8):
        y = 32.5 + (m - 1) * 5
        ref = f"R84{m}"
        s.label(22, y, f"SIG_O{m}", "R")
        a, b = hr(s, ref, "1k", 47.5, y, ref_at=(0, -0.9, "middle"), hide_val=True)
        s.wire((22, y), a)
        s.wire(b, (bx, y))
        ex(e, f"SIG_O{m}", f"{ref}.{pnum(s, ref, a)}")
        ex(e, "SIG_BUS", f"{ref}.{pnum(s, ref, b)}")
    s.wire((bx, 32.5), (bx, 62.5))
    s.wire((bx, 47.5), (bx + 10, 47.5)); s.label(bx + 10, 47.5, "SIG_BUS", "R")
    s.text(18, 68.5, "R841~R847 = 1 kΩ · SIG_BUS → R808 2.2 kΩ → A0", "notes", size=1.9)
    # pedal input (was the PB board of rev E: R501/R502/C501/R503 -> R805/R806/C801/R807)
    s.box(14, 78, 112, 62, "페달 입력 (rev E PB 보드 대신, 부품 값 그대로)")
    jp = sym_conn_pos("Conn_01x04", 5, [(1, 0), (3, 2), (2, 3), (4, 4)], side="R", width=9)
    jx, jy = 20, 92
    s.place(jp, "J808", "W808 패드 1×4", jx, jy, ref_at=(0, -1.2), val_at=(0, 29.6))
    for n, nm in ((1, "T"), (3, "R"), (2, "TN"), (4, "S")):
        s.text(jx + 1.0, s.pin("J808", n)[1] + 0.8, nm, "pinname", size=2.0)
    t_ = s.pin("J808", 1); r_ = s.pin("J808", 3); tn_ = s.pin("J808", 2); sl_ = s.pin("J808", 4)
    for p_ in (tn_, sl_):
        s.wire(p_, (p_[0] + 3, p_[1])); s.pwr(p_[0] + 3, p_[1], "GND")
    ex(e, "GND", "J808.2", "J808.4")
    a, b = hr(s, "R805", "1k", 62.5, t_[1])
    s.wire(t_, a)
    s.wire(b, (95, t_[1])); s.label(95, t_[1], "PED_ADC", "R")
    s.place(sym_C(), "C801", "100n", 85, t_[1] + 7.5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.wire((85, t_[1]), s.pin("C801", 1)); s.pwr(*s.pin("C801", 2), "GND")
    s.place(sym_R(), "R806", "100k", 52, t_[1] + 7.5, ref_at=(-3.2, -0.6, "end"), val_at=(-3.2, 2.4, "end"))
    s.wire((52, t_[1]), s.pin("R806", 1)); s.pwr(*s.pin("R806", 2), "GND")
    ex(e, "~PED_TIP", "J808.1", f"R805.{pnum(s, 'R805', a)}", "R806.1")
    ex(e, "PED_ADC", f"R805.{pnum(s, 'R805', b)}", "C801.1")
    ex(e, "GND", "C801.2", "R806.2")
    a, b = hr(s, "R807", "20Ω", 62.5, 125.0)
    s.wire(r_, (r_[0] + 11, r_[1]), (r_[0] + 11, 125.0), a)
    s.wire(b, (80, 125.0)); s.pwr(80, 125.0, "+5V_B")
    ex(e, "~PED_VCC", "J808.3", f"R807.{pnum(s, 'R807', a)}")
    ex(e, "+5V_B", f"R807.{pnum(s, 'R807', b)}")
    s.text(18, 136.5, "R807 = 100 Ω × 5 병렬 (rev E R503). 잭을 꽂는 순간 링–슬리브 단락 전류 제한", "notes", size=1.9)
    # power in + divider + test points
    s.box(268, 22, 128, 62, "버스 전원 입력 + 감시")
    pj = sym_conn("Conn_01x02", 2, side="R", width=6)
    s.place(pj, "J809", "전원 패드 1×2", 272, 33, ref_at=(0, -2.2), val_at=(0, 14.0), part="W810 ← A602 OUT (U-04)", part_at=(0, 16.3))
    p1, p2 = s.pin("J809", 1), s.pin("J809", 2)
    s.wire(p1, (300, p1[1])); s.pwr(290, p1[1], "+5V_B")
    s.wire(p2, (p2[0] + 6, p2[1])); s.pwr(p2[0] + 6, p2[1], "GND")
    ex(e, "+5V_B", "J809.1"); ex(e, "GND", "J809.2")
    s.place(sym_C(True), "C802", "10µ", 300, p1[1] + 5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.place(sym_C(), "C803", "100n", 312.5, p1[1] + 5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.wire((300, p1[1]), (312.5, p1[1]), s.pin("C803", 1))
    s.pwr(*s.pin("C802", 2), "GND"); s.pwr(*s.pin("C803", 2), "GND")
    ex(e, "+5V_B", "C802.1", "C803.1"); ex(e, "GND", "C802.2", "C803.2")
    s.place(sym_R(), "R831", "10k", 340, 40, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.place(sym_R(), "R832", "10k", 340, 60, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.wire(s.pin("R831", 1), (340, 30.5)); s.pwr(340, 30.5, "+5V_B")
    s.wire(s.pin("R831", 2), s.pin("R832", 1))
    s.wire((340, 50), (350, 50)); s.label(350, 50, "V_MON", "R")
    s.pwr(*s.pin("R832", 2), "GND")
    ex(e, "+5V_B", "R831.1"); ex(e, "V_MON", "R831.2", "R832.1"); ex(e, "GND", "R832.2")
    s.text(344, 56.5, "≈ 2.55 V = 켜짐", "notes", size=1.9)
    for i, (ref, net) in enumerate((("TP801", "+5V_B"), ("TP802", "GND"), ("TP803", "SIG_BUS"))):
        tx, ty = 362 + i * 11, 66
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        if net == "GND":
            s.wire((tx, ty), (tx, ty + 2.5)); s.pwr(tx, ty + 2.5, "GND")
        elif net == "+5V_B":
            s.wire((tx, ty), (tx, ty + 2.5), (tx - 4, ty + 2.5)); s.pwr(tx - 4, ty + 2.5, "+5V_B")
        else:
            s.wire((tx, ty), (tx, ty + 5)); s.label(tx, ty + 5, net, "R", up=False)
        ex(e, net, f"{ref}.1")
    # ports J801..J807 (2x5 box headers; IDC wire n = pin n)
    s.box(14, 145, 382, 56, "옥타브 포트 J801~J807 — 2×5 박스 헤더, 리본 W801~W807의 IDC 소켓이 꽂힘 (빨간 줄 = 1번)")
    for m in range(1, 8):
        x0 = 32 + (m - 1) * 53.5
        ref = f"J80{m}"
        s.place(sym_conn2("Conn_02x05_Odd_Even", 5, pitch=7.0, width=10), ref, f"O{m} · W80{m} {CUTS[m]}", x0, 155,
                ref_at=(0, -1.4), val_at=(-6, 40.0))
        for i, nm in enumerate(BUS):
            px, py = s.pin(ref, i + 1)
            odd = (i + 1) % 2 == 1
            net = {"MUX_SIG": f"SIG_O{m}", "MUX_EN": f"EN_O{m}"}.get(nm, nm)
            d = -1 if odd else 1
            if net in PWR:
                L = 4 if net == "GND" else 6
                s.wire((px, py), (px + d * L, py)); s.pwr(px + d * L, py, net)
            else:
                L = 3
                s.wire((px, py), (px + d * L, py)); s.label(px + d * L, py, net, "L" if odd else "R")
            ex(e, net, f"{ref}.{i+1}")
    s.text(18, 199.0, "S0~S3는 7개 포트가 같은 선(R801~R804 뒤). EN_Om · SIG_Om은 포트마다 따로. GND 4가닥 중 3·10은 SIG 옆 차폐.", "notes", size=1.9)
    # pin table
    pm = [["D0 · D1", "USB 시리얼", "노트북 (115200)", "—"],
          ["D2~D5", "MUX_S0~S3", "출력 → 1 kΩ → 7 포트 공통", "R801~R804"],
          ["D6~D12", "EN_O1~EN_O7", "출력, 하나만 LOW (D6 = O1)", "R811~R817"],
          ["D13", "LED", "상태 (보드 LED)", "—"],
          ["A0", "SIG_BUS", "아날로그 입력 (먹스 7개 합침)", "R808 · R841~R847"],
          ["A1", "PED_ADC", "아날로그 입력 (페달 CC64)", "R805 · R806 · C801"],
          ["A2", "V_MON", "버스 5 V 감시 (½ 분압)", "R831 · R832"],
          ["A3~A5", "—", "연결 안 함", "—"],
          ["5V", "—", "연결 금지 (+5V_B와 묶지 않음)", "—"],
          ["GND", "GND", "UB GND (듀폰 2가닥)", "—"]]
    s.table(15, 206, ["우노 핀", "넷", "쓰임", "UB 부품"], pm, [20, 25, 55, 32], title="Arduino Uno 핀 배정 (W809 듀폰 점퍼 M/M 20 cm로 UB와 연결)", mono_cols=(0, 1))
    s.para(150, 206, [
        "주",
        "1. UB = 만능기판 조각 약 70 × 90 (BE163 남는 것). 허브가 있던 선반에 놓고, 우노는 Pi 자리에 양면 테이프·벨크로.",
        "    우노 디지털 헤더는 0.16″ 어긋나 만능기판 실드가 안 맞는다 → 듀폰 점퍼 16가닥(W809)으로 잇는다.",
        "2. 접지 하나: 우노 GND = UB GND = 버스 GND = 전지 −(★). 우노 5V는 USB에서 오고 +5V_B와 묶지 않는다(둘이 싸우지 않게).",
        "3. 켜는 순서: 노트북 USB → 전지 스위치. 끌 때 반대. 버스가 꺼지면 펌웨어가 A2로 알고 D2~D12를 입력(높은 임피던스)으로 바꾼다.",
        "4. 노트북: firmware/uno를 올리고 sw/toccata-bridge가 시리얼 → 가상 MIDI ‘Toccata Uno’. 음원·게임은 노트북에서(sw/README.md).",
        "5. 읽는 속도: 88건반 + 페달을 ADC 하나로 → 약 600~700회/초(계산). Pi 버전(옥타브마다 약 9,000회/초)보다 느려 세기는 더 거칠다.",
    ], size=2.15)
    s.frame()
    s.expected = e
    return s


# ================================================================== U-04 power + audio
def u04():
    B = power_budget()
    s = Sheet("U-04", 4, TOTAL, "전원 · 오디오 (아두이노 버전)",
              "전지 → 퓨즈 → 스위치 → 12.8 V 버스 → 앰프 + XL4016 5.1 V → UB(센서·먹스). Pi·허브·화면 전원선은 없다. 소리는 노트북 이어폰 단자 → J701부터 rev E SCH-07 그대로.",
              "CU 전원·오디오", qty="CU × 1", basis=BASIS, **REV_U)
    e = {}
    pk = sym_box("LiFePO4_pack", [], [(1, "+", "pwr"), (2, "−", "pwr")], width=26, cls="mod", rows=2)
    for cx in (4.0, 10.0):
        pk.line(cx, 3.5, cx, 11.5, "bodyl")
        pk.line(cx + 2.0, 5.5, cx + 2.0, 9.5, "bodyl")
    s.place(pk, "BT601", "LiFePO4 12.8 V (rev E 그대로)", 16, 40, val_at=(0, 18.5), part="XT60 X605⇄X606 · W601", part_at=(0, 20.8))
    s.place(sym_conn("XT60-F", 2, side="L", width=6, rev=True), "X605", "XT60 암", 62, 42.5, ref_at=(0, -2.2), val_at=(-1, 17.5))
    s.place(sym_conn("XT60-M", 2, side="R", width=6, rev=True), "X606", "XT60 수", 69.5, 42.5, ref_at=(0, -2.2), val_at=(1, 17.5))
    s.mate("X605", "X606", at=(68.3, 54.8))
    for k in (1, 2):
        s.wire(s.pin("BT601", k), s.pin("X605", "2" if k == 1 else "1"))
    vx, vy = s.pin("X606", 2)
    gx, gy = s.pin("X606", 1)
    ex(e, "VBAT", "BT601.1", "X605.2", "X606.2")
    ex(e, "GND", "BT601.2", "X605.1", "X606.1")
    s.wire((gx, gy), (gx + 3.5, gy)); s.pwr(gx + 3.5, gy, "GND")
    fx, swx = 100.0, 130.0
    s.place(sym_fuse(), "F601", "5 A ATO", fx, vy, ref_at=(0, -3.0, "middle"), val_at=(0, 5.0, "middle"))
    s.wire((vx, vy), s.pin("F601", 1))
    s.label(vx + 1.5, vy, "VBAT", "R")
    ex(e, "VBAT", "F601.1")
    s.place(sym_switch_dpst(), "SW601", "KCD1-104", swx, vy, ref_at=(0, -4.2, "middle"), val_at=(0, 15.0, "middle"))
    s.wire(s.pin("F601", 2), s.pin("SW601", 1))
    s.wire((swx - 10.0, vy), (swx - 10.0, vy + 10.0), s.pin("SW601", 3))
    s.wire(s.pin("SW601", 4), (swx + 10.0, vy + 10.0), (swx + 10.0, vy))
    s.label(s.pin("F601", 2)[0] + 1, vy, "VBAT_F", "R")
    ex(e, "VBAT_F", "F601.2", "SW601.1", "SW601.3")
    bx = 185
    s.wire(s.pin("SW601", 2), (bx, vy))
    s.pwr(bx - 5, vy, "+12V8")
    ex(e, "+12V8", "SW601.2", "SW601.4")
    bk = sym_box("XL4016_module", [(1, "IN+"), None, (2, "IN-")], [(3, "OUT+"), None, (4, "OUT-")], width=30, cls="mod", rows=3)
    s.place(bk, "A602", "XL4016 강압 → 5.1 V", 195, 80, val_at=(0, 23.5), part="rev E 그대로 · 5.10 V 맞춤", part_at=(0, 25.8))
    i1, i2 = s.pin("A602", 1), s.pin("A602", 2)
    s.wire((bx, vy), (bx, i1[1]), i1)
    s.wire(i2, (i2[0] - 7.5, i2[1])); s.pwr(i2[0] - 7.5, i2[1], "GND")
    s.text(i2[0] - 30, i2[1] + 7.5, "★ 별 접지점: 강압 IN−", "noteb", size=2.3)
    ex(e, "+12V8", "A602.1"); ex(e, "GND", "A602.2")
    s.wire((bx, vy), (bx + 55, vy)); s.pwr(bx + 55, vy, "+12V8")
    s.text(bx + 58, vy + 0.8, "→ A702 앰프 DC (W602c, SCH-07 그대로)", "notes", size=2.0)
    o1, o2 = s.pin("A602", 3), s.pin("A602", 4)
    s.wire(o2, (o2[0] + 7.5, o2[1])); s.pwr(o2[0] + 7.5, o2[1], "GND")
    s.wire(o1, (o1[0] + 12.5, o1[1])); s.pwr(o1[0] + 12.5, o1[1], "+5V_B")
    ex(e, "GND", "A602.4"); ex(e, "+5V_B", "A602.3")
    s.text(o1[0] + 27, o1[1] + 0.8, "W810 → UB J809 (U-03) · 길이 = rev E W604(허브 DC) 자리", "cabt", size=2.0)
    s.para(o1[0] + 27, o1[1] + 5.5, ["Pi(W603)·허브(W604)·화면(W606~W608) 전원선은 만들지 않는다.",
                                     "rev E에서 만든 W604가 있으면 플러그를 잘라 J809에 납땜."], "notes", size=2.0)
    for i, (ref, net) in enumerate((("TP601", "+12V8"), ("TP602", "+5V_B"), ("TP603", "GND"))):
        tx, ty = 110 + i * 20, 118
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        if net == "GND":
            s.wire((tx, ty), (tx, ty + 2.5)); s.pwr(tx, ty + 2.5, "GND")
        else:
            s.wire((tx, ty), (tx, ty + 2.5), (tx - 5, ty + 2.5)); s.pwr(tx - 5, ty + 2.5, net)
        ex(e, net, f"{ref}.1")
    # audio: laptop headphone out -> W701 -> J701 (rest = SCH-07)
    s.box(14, 140, 200, 56, "소리 — 노트북 → J701 (나머지는 rev E SCH-07 그대로)")
    lp = sym_box("Laptop_3.5mm", [], [("T", "L"), ("R", "R"), ("S", "GND")], width=30, cls="mod", rows=3)
    s.place(lp, "A901", "노트북 이어폰 단자", 20, 152, val_at=(0, 23.5), part="단자가 없으면 A701 동글을 노트북에", part_at=(0, 25.8))
    s.place(sym_plug(), "P701", "W701 플러그", 90, 152, mirror=True, ref_at=(-9, -2.2), val_at=(-9, 19.5))
    s.mate("A901", "P701", at=(74.5, 148.5))
    for nm, net in (("T", "DAC_L"), ("R", "DAC_R"), ("S", "AGND")):
        x, y = s.pin("A901", nm)
        s.wire((x, y), (x + 1, y)); s.label(x + 1, y, net, "R")
        x, y = s.pin("P701", nm)
        s.wire((x, y), (x + 10, y)); s.label(x + 10, y, net, "R")
        ex(e, net, f"P701.{nm}", f"A901.{nm}")
    s.text(122, 156.0, "W701 → J701 헤드폰 잭 (왼쪽 볼)", "cabt", size=2.0)
    s.text(122, 159.0, "→ W702 → J702 → HPF → A702 → 스피커", "cabt", size=2.0)
    s.para(18, 183.5, ["W701(1.0 m)은 Pi 자리까지만 닿는다 → 노트북까지 3.5 mm 연장선(수–암) 1.5~2 m를 더한다.",
                       "노트북 소리 크기를 70~80 %로 두고 앰프 노브로 맞춘다(동글보다 출력이 크다 — 찌그러짐 주의)."], "notes", size=2.0, lh=2.8)
    rows = [["센서 89개 + 먹스 7개 (5.1 V)", "5.1 V", f"약 {B['a'][0]:.2f}~{B['a'][1]:.2f} A", f"{B['w5'][0]:.1f}~{B['w5'][1]:.1f} W"],
            ["강압 손실 (효율 85 % 가정)", "", "", f"{B['w5'][0]/0.85-B['w5'][0]:.1f}~{B['w5'][1]/0.85-B['w5'][1]:.1f} W"],
            ["앰프 평균 (SCH-06과 같은 보수적 추정)", "12.8 V", "약 0.16~0.47 A", "2~6 W"],
            ["합계 (평균)", "12.8 V 입력", f"약 {B['tot'][0]/12.8:.2f}~{B['tot'][1]/12.8:.2f} A", f"약 {B['tot'][0]:.1f}~{B['tot'][1]:.1f} W"],
            ["연주 시간 (76.8 Wh × 0.9 ÷ 평균)", "", "", f"약 {B['run'][1]:.0f}~{B['run'][0]:.0f} h"],
            ["우노 (노트북 USB에서)", "5 V USB", "약 0.05 A", "전지와 무관"]]
    s.table(222, 140, ["부하", "전압", "전류", "전력"], rows, [70, 20, 34, 24], title="전원 예산 (아두이노 버전 — Pi·허브·화면 약 12 W가 빠짐)")
    s.para(222, 170, [
        "주",
        "1. 전지·퓨즈·스위치·강압·앰프·스피커·별 접지(★)는 rev E SCH-06·07과 같다(선 길이도 같음).",
        "2. 접지 고리: 노트북 USB GND와 이어폰 GND가 둘 다 이 GND에 닿는다. 노트북을 충전하며 칠 때",
        "    ‘웅’ 소리가 나면 3.5 mm 접지 고리 차단기를 W701 앞에 끼운다(또는 충전기를 뺀다).",
        "3. 강압 출력을 무부하로 5.10~5.15 V에 맞춘 뒤 W810을 잇는다(rev E 순서 그대로).",
    ], size=2.15)
    s.frame()
    s.expected = e
    return s


# ================================================================== U-01 system
CHANGES_OUT = [
    ["A603 Raspberry Pi 5 + W603(전원선)", "노트북이 대신"],
    ["A605 7인치 터치 화면 + W605~W608", "노트북 화면"],
    ["A604 USB 허브 + W604 · W209", "UB 버스 기판"],
    ["A301 RP2040-Zero × 7 · A501 × 1 + 핀 헤더", "Arduino Uno 1개"],
    ["W201~W208 USB 선 8개", "W801~W807 리본 10심"],
    ["PB 페달 보드 (R501~R503 · C501 · J502)", "UB 페달 입력 (같은 값)"],
    ["JP301~JP304 ID 점퍼", "UB 포트 번호"],
    ["A701 동글 · X701 젠더", "노트북 이어폰 단자"],
]
CHANGES_IN = [
    ["A801 Arduino Uno R3 (정품/호환) + USB-B 선 1.5~2 m (W811)", "1 + 1"],
    ["UB 만능기판 조각 약 70 × 90 (BE163 남는 것)", "1"],
    ["2×5 박스 헤더 (J801~J807) + IDC 2×5 소켓", "7 + 7"],
    ["10심 리본 1.27 mm (W801~W807, 합 %d mm)" % sum(CUTS.values()), "약 4 m"],
    ["저항 1 kΩ (R801~R805 · R811~R817 · R841~R847)", "19"],
    ["저항 2.2 kΩ (R808) · 10 kΩ (R831 · R832)", "1 · 2"],
    ["100 kΩ R806 · 100 Ω × 5 = R807 · 100 nF C801 · C803 · 10 µF C802", "PB 것 옮김 + 1"],
    ["듀폰 점퍼 M/M 20 cm (W809)", "16"],
    ["3.5 mm 연장선 수–암 1.5~2 m (노트북 → W701)", "1"],
]


def u01():
    s = Sheet("U-01", 1, TOTAL, "시스템 연결도 — 아두이노 버전 (노트북에서 실행)",
              "Pi 버전(rev E)과 같은 건반·센서·전원·스피커에 RP2040 8개 + Pi 5 대신 Arduino Uno 1개 + 노트북. 센서는 그대로 두고 연결만 바꾼다. 회로 U-02~U-04.",
              "전체", qty="O1~O7 · EL · ER · UB · CU", basis=BASIS, **REV_U)

    def blk(x, y, w, h, title, lines=(), cls="mod"):
        s.rect(x, y, w, h, cls, "body")
        s.text(x + 1.5, y + 4.2, title, "ref", size=2.6)
        for i, t in enumerate(lines):
            s.text(x + 1.5, y + 7.6 + i * 2.8, t, "notes", size=2.0)

    blk(14, 26, 30, 30, "EL 왼쪽 끝", ["A0·A#0·B0", "센서 3 (5 V)", "헤드폰 잭 J701"])
    for i in range(7):
        x = 50 + i * 43
        blk(x, 26, 39, 30, f"O{i+1} (C{i+1}~B{i+1})", ["건반 12 · SB 센서 12", "MB-U: 먹스 4067만", "(RP2040 없음)", f"→ UB J80{i+1}"])
        s.cable((x + 19.5, 56), (x + 19.5, 96))
        s.text(x + 21, 78, f"W80{i+1}", "cabt", size=2.1)
        s.text(x + 21, 81.2, f"{CUTS[i+1]} mm", "notes", size=2.0)
    blk(353, 26, 44, 30, "ER 오른쪽 끝", ["C8", "센서 1 (5 V)"])
    s.cable((44, 36), (50, 36)); s.cable((342, 36), (353, 36))
    s.text(22, 62, "EXT → O1 먹스 C12~C14", "cabt", size=2.0)
    s.text(330, 62, "EXT → O7 먹스 C12", "cabt", size=2.0)
    blk(50, 96, 300, 16, "UB 버스 기판 (허브 자리) — 포트 J801~J807 = O1~O7, 페달 J808, 전원 J809",
        ["S0~S3 공통(1 kΩ) · EN 포트마다(1 kΩ, 하나만 켬) · SIG 포트마다 1 kΩ → 한 줄 → 2.2 kΩ → 우노 A0 · +5V_B 나눔",
         "리본 10심: GND · SIG · GND · S0 · S1 · S2 · S3 · EN · +5V_B · GND (모듈 쪽 납땜, UB 쪽 IDC 소켓)"])
    blk(360, 72, 37, 22, "J501 페달 잭", ["rev E 그대로", "→ W808 → UB J808"])
    s.cable((378.5, 94), (378.5, 104), (350, 104))
    blk(360, 118, 37, 18, "PS 댐퍼 페달", ["WSH137 + 1 kΩ", "그대로 (5 V)"])
    s.cable((378.5, 118), (378.5, 94))
    s.text(380, 113, "W501", "cabt", size=2.0)
    blk(50, 132, 64, 30, "A801 Arduino Uno R3 (Pi 자리)", ["D2~D5 → S0~S3 · D6~D12 → EN O1~O7", "A0 ← SIG · A1 ← 페달 · A2 ← 5 V 감시",
                                                        "firmware/uno: 약 600~700회/초 스캔", "USB 시리얼 115200: MIDI 바이트 + ‘#’ 글"])
    s.cable((80, 112), (80, 132)); s.text(82, 123, "W809 듀폰 16", "cabt", size=2.0)
    blk(132, 132, 92, 30, "노트북 (macOS · Windows · Linux)", ["sw/toccata-bridge: 시리얼 → 가상 MIDI ‘Toccata Uno’",
                                                            "FluidSynth 피아노 (sw/toccata-midi synth)", "리듬게임 (sw/toccata-game)",
                                                            "이어폰 단자 → 3.5 mm 연장선 → W701"])
    s.cable((114, 147), (132, 147)); s.text(115, 145.5, "W811 USB", "cabt", size=2.0)
    blk(241, 132, 50, 22, "J701 → CU 트레이", ["헤드폰 잭 (EL 볼) · J702", "HPF · A702 HW-720"])
    s.cable((224, 150), (241, 150)); s.text(226, 148.5, "W701", "cabt", size=2.0)
    blk(310, 132, 38, 12, "LS701 왼쪽", ["CW-100B25 8 Ω"], "body")
    blk(310, 148, 38, 12, "LS702 오른쪽", ["CW-100B25 8 Ω"], "body")
    s.cable((291, 138), (310, 138)); s.cable((291, 152), (310, 152))
    blk(125, 172, 40, 16, "BT601 LiFePO4 전지", ["12.8 V · 76.8 Wh", "XT60 → W601"])
    blk(175, 172, 34, 16, "F601 5 A · SW601", ["rev E 그대로"])
    blk(220, 172, 38, 16, "A602 XL4016 → 5.1 V", ["★ 별 접지점 IN−"])
    s.cable((165, 180), (175, 180)); s.cable((209, 180), (220, 180))
    s.cable((214.5, 180), (214.5, 168), (266, 168), (266, 154)); s.text(230, 166.5, "W602c +12V8 → 앰프", "cabt", size=2.1)
    s.cable((258, 180), (355, 180), (355, 112), (350, 112)); s.text(290, 178.5, "W810 +5V_B → UB J809", "cabt", size=2.1)
    s.text(16, 176.5, "켜는 순서: 노트북 USB → 전지 스위치", "cabt", size=2.2)
    s.text(16, 180.5, "끌 때: 전지 스위치 → USB", "notes", size=2.0)
    rows = [[f"W80{m}", "10심 리본 1.27 mm", f"{CUTS[m]}", f"O{m} MB-U J303 (납땜)", f"UB J80{m} (IDC 2×5)"] for m in range(1, 8)]
    rows += [["W808", "페달 잭 → UB (리본 4가닥)", "재서 +30", "J501", "UB J808"],
             ["W809", "듀폰 점퍼 M/M 20 cm × 16", "산 그대로", "우노 헤더", "UB 핀"],
             ["W810", "5.1 V → UB (16~18 AWG 2심)", "rev E W604 자리", "A602 OUT+ · OUT−", "UB J809"],
             ["W811", "USB-A(또는 C) → B 1.5~2 m", "산 그대로", "노트북", "우노 USB-B"]]
    s.table(14, 198, ["W", "선", "자르는 길이 (mm)", "한쪽", "다른 쪽"], rows, [14, 52, 26, 36, 30],
            title="새 선 (나머지 W501 · W601~W602 · W701~W707은 rev E 그대로)", rh=3.0)
    s.table(180, 198, ["빠지는 것 (Pi 버전에만)", "대신"], CHANGES_OUT, [72, 40], title="Pi 버전에서 빠지는 것", rh=3.0)
    s.table(14, 241, ["더하는 것 (아두이노 버전)", "수량"], CHANGES_IN, [118, 26], title="새로 필요한 것", rh=3.0)
    s.para(300, 198, [
        "주",
        "1. 그대로: SB × 7 · EL · ER · PS, MB 기판·먹스·J301·J302,",
        "    전지·퓨즈·스위치·강압·앰프·스피커·잭, 모든 출력물.",
        "2. 센서 전원 3.3 V → 5.1 V(+5V_B). 부품은 같다.",
        "3. Pi 버전으로 되돌리기: 제로를 다시 꽂고 EN을 GND,",
        "    USB 선·허브·Pi를 다시 연결(펌웨어는 각자 따로).",
        "4. Pi 버전 옥타브 기판도 허브를 노트북에 꽂으면",
        "    그대로 노트북에서 돈다(USB-MIDI, 브리지 불필요).",
    ], size=2.0, lh=2.9)
    s.frame()
    s.expected = {}
    return s


def u05_rows():
    """Parts to add (used by the page and bom_uno.csv)."""
    return CHANGES_IN


SHEETS = [u01, u02, u03, u04]
