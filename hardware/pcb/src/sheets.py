"""Toccata circuit sheets (design data + drawing). Run build.py to regenerate outputs."""
from sch import (Sheet, sym_R, sym_C, sym_hall, sym_box, sym_conn, sym_jumper, sym_fuse,
                 sym_switch, sym_speaker, sym_jack, sym_plug, sym_conn2, sym_tp, sym_conn_pos)
import parts as P

TOTAL = 9
KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NET = {k: "HALL_" + k.replace("#", "S") for k in KEYS}           # HALL_C, HALL_CS, ...
RIBBON = ["+3V3", "GND"] + ["HALL_" + k.replace("#", "S") for k in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]] + ["GND", "+3V3"]
SENSOR_X = [7.431, 21.215, 35.250, 49.285, 63.070, 77.359, 90.573, 104.037, 117.500, 130.964, 144.427, 157.641]


POWER = ("GND", "+3V3", "+3V3_O1", "+3V3_O7", "+20V", "+5V1", "+5V_PI")

# ------------------------------------------------------------------ R31 touchscreen (rev C, 2026-10-01)
# B1 = Waveshare 7-DSI-TOUCH-C, powered from the Pi 40-pin header (pin 2 = 5 V, pin 6 = GND).
REV_C = dict(rev="C", date="2026-10-01")
DISP = dict(
    model="Waveshare 7-DSI-TOUCH-C",
    power_w=2.15,            # purchase list No.135 / Waveshare wiki: about 2.15 W from the GPIO 5 V
    v=5.0,                   # screen input voltage used for the current
    jumper_m=0.20,           # silicone jumpers 20 cm (F/F, then M/M) per conductor
    jumper_awg26_ohm_m=0.1339,  # 26 AWG copper, ohm per metre
    ffc_mm=300,              # GUOCONN 22P 0.5 mm 300 mm B-type (reverse); A-type bought as insurance
    overlay="dtoverlay=vc4-kms-dsi-waveshare-panel-v2,7_0_inch_c",
)
# SCH-06 rev B budget inputs (unchanged) + D19 peak basis (52 W, the larger value than the rev B table's 50 W)
BUDGET_IN = dict(pi_w=7.7, pi_a=1.5, hub_w=2.0, hub_a=0.4, dongle_w=0.5, dongle_a=0.1, eff=0.90,
                 amp_avg_w=(2.0, 6.0), amp_avg_a=(0.1, 0.3), peak_basis_w=52.0, bus_v=20.0, pi_v=5.1,
                 supply_w=60.0, small_supply_w=45.0)


def budget():
    """Power budget with the R31 display (all derived numbers of SCH-06 rev C and README △16)."""
    b = BUDGET_IN
    d_w = DISP["power_w"]
    d_a = d_w / DISP["v"]
    five_old = b["pi_w"] + b["hub_w"] + b["dongle_w"]
    five_new = five_old + d_w
    loss_old = five_old / b["eff"] - five_old
    loss_new = five_new / b["eff"] - five_new
    avg = [five_new + loss_new + a for a in b["amp_avg_w"]]
    base_old = five_old + loss_old                 # non-amp input power, rev B
    base_new = five_new + loss_new                 # non-amp input power, with the display
    amp_peak = b["peak_basis_w"] - base_old        # amp share of the D19 peak
    peak = amp_peak + base_new                      # = 52 + display / efficiency
    db = lambda x: 10 ** (x / 10.0)
    cut1 = amp_peak * db(-1) + base_new
    cut2 = amp_peak * db(-2) + base_new
    cut1_off = amp_peak * db(-1) + base_old
    pi_in_a = (b["pi_w"] + b["dongle_w"] + d_w) / b["pi_v"]
    drop = 2 * DISP["jumper_m"] * 2 * DISP["jumper_awg26_ohm_m"] * d_a   # 2 jumpers in series, out and back
    return dict(disp_w=d_w, disp_a=d_a, five_new=five_new, loss_old=loss_old, loss_new=loss_new,
                avg=avg, avg_a=[x / b["bus_v"] for x in avg], peak=peak, peak_a=peak / b["bus_v"],
                margin=b["supply_w"] - peak, amp_peak=amp_peak, cut1=cut1, cut2=cut2, cut1_off=cut1_off,
                pi_in_a=pi_in_a, drop_v=drop, small=b["small_supply_w"])


def net_end(s, x, y, name, side="R"):
    """End a wire stub with a power symbol (power nets) or a local label (signals)."""
    if name in POWER:
        s.pwr(x, y, name)
    else:
        s.label(x, y, name, side)


def exp_add(e, net, *pins):
    e.setdefault(net, []).extend(pins)


# ------------------------------------------------------------------ SCH-02
def sch02():
    s = Sheet("SCH-02", 2, TOTAL, "옥타브 센서 기판 (SB)",
              "건반 12개의 홀센서 DRV5055A2 + 디커플링. 모듈 O1~O7에 같은 기판 7장. 출력 12선 + 3V3·GND 2가닥씩을 리본 16심으로 제어 기판(SCH-03 J301)에 보낸다.",
              "SB", qty="SB × 7", basis="v4 W1+ r4.5")
    e = {}
    y3, yg = 37.5, 87.5  # noqa
    x0 = 37.5
    dx = 30.0
    hall = sym_hall()
    cap = sym_C()
    # buses
    s.pwr(17.5, y3, "+3V3")
    s.wire((17.5, y3), (x0 + 11 * dx + 20, y3))
    s.pwr(17.5, yg, "GND")
    s.wire((17.5, yg), (x0 + 11 * dx + 20, yg))
    for i, k in enumerate(KEYS):
        xs = x0 + i * dx
        u = f"U{201+i}"
        c = f"C{201+i}"
        s.place(hall, u, "DRV5055A2QLPG", xs, 62.5, ref_at=(1.6, -8.4), val_at=None, hide_val=True,
                meta=dict(key=k))
        s.text(xs - 4.8, 76.0, k, "noteb", size=2.8)
        vx, vy = s.pin(u, 1)
        s.wire((vx, vy), (vx, y3))
        gx, gy = s.pin(u, 2)
        s.wire((gx, gy), (gx, yg))
        ox, oy = s.pin(u, 3)
        s.wire((ox, oy), (ox + 2.5, oy))
        s.label(ox + 2.5, oy, NET[k], "R")
        exp_add(e, "+3V3", f"{u}.1")
        exp_add(e, "GND", f"{u}.2")
        exp_add(e, NET[k], f"{u}.3")
        cx = xs - 7.5
        s.place(cap, c, "100n", cx, 70, ref_at=(-1.0, -1.2, "end"), val_at=(-1.0, 2.2, "end"))
        a = s.pin(c, 1)
        b = s.pin(c, 2)
        s.wire(a, (a[0], y3))
        s.wire(b, (b[0], yg))
        exp_add(e, "+3V3", f"{c}.1")
        exp_add(e, "GND", f"{c}.2")
    # bulk caps at both bus ends
    for ref, cx in (("C213", 17.5 + 2.5), ("C214", x0 + 11 * dx + 20)):
        s.place(sym_C(polar=False), ref, "10µ", cx, 70, ref_at=(-1.2 if ref == "C213" else 3.2, -1.2, "end" if ref=="C213" else "start"), val_at=(-1.2 if ref == "C213" else 3.2, 2.2, "end" if ref=="C213" else "start"))
        a, b = s.pin(ref, 1), s.pin(ref, 2)
        s.wire(a, (a[0], y3))
        s.wire(b, (b[0], yg))
        exp_add(e, "+3V3", f"{ref}.1")
        exp_add(e, "GND", f"{ref}.2")
    s.chg(14.5, 58.0, 1)
    # ribbon pads J201 — 2x8 block of 2.54 mm holes, conductor n = pin n (IDC compatible), all 16 wires (R27)
    names = RIBBON
    j = sym_conn2("Conn_02x08_Odd_Even", 8, width=12)
    jx, jy = 330, 105
    s.place(j, "J201", "리본 16심 → 2×8 구멍 (2.54)", jx, jy, ref_at=(0, -2.2), val_at=(-12, 44.5))
    for i, nm in enumerate(names):
        px, py = s.pin("J201", i + 1)
        d = -1 if (i + 1) % 2 else 1
        L = 25 if nm in POWER else 7.5
        s.wire((px, py), (px + d * L, py))
        net_end(s, px + d * L, py, nm, "L" if d < 0 else "R")
        exp_add(e, nm, f"J201.{i+1}")
    s.text(jx - 20, jy - 7.5, "리본 선 번호 = 핀 번호 (1 = 빨간 줄무늬 선, 홀수 = 앞줄)", "notes", size=2.0)
    s.cable((jx + 6, jy + 48), (jx + 6, jy + 58), text="→ SCH-03 J301 (약 180 mm)", at=(jx + 8, jy + 55.5), anchor="start")
    s.chg(jx + 22, jy - 1.5, 12)
    # placement table
    rows = []
    for i, k in enumerate(KEYS):
        rows.append([f"U{201+i}", k, f"{SENSOR_X[i]:.3f}", f"C{201+i}", NET[k], f"C{i}", f"{i+3}"])
    s.table(15, 102, ["센서", "건반", "센서 x (mm)", "100n", "넷", "MUX 채널", "리본 선"],
            rows, [14, 10, 20, 12, 22, 16, 13], title="센서 배치표 (모듈 좌표, 소자 열 y67.00)", mono_cols=(0, 2, 3, 4, 5, 6))
    w1 = [["백건", "10.82 / 5.60 / 5.24", "4.3 / 21.9 / 25.4", "1.78 / 2.31 / 2.41", "2207 → 2862 (최대 2993)"],
          ["흑건", "13.35 / 5.32 / 4.76", "2.4 / 24.6 / 31.3", "1.72 / 2.39 / 2.59", "2138 → 2962 (최대 3212)"]]
    s.table(130, 102, ["W1", "간격 쉼/강체 바닥/과다 mm", "자기장 mT", "OUT V", "ADC (쉼 → 강체 바닥)"], w1,
            [12, 46, 30, 30, 40], title="W1 자석·센서 (자석 Ø5×2 N35, 소자 열 y67 바로 위, S극 아래)", mono_cols=(1, 2, 3, 4))
    s.text(130, 118.5, "W1 r4.5 좌표 모델(geometry.json 2026-09-29, 센서 값은 r4.3과 같음) S26·S30. 자기장은 원판 자석 축 위 식(Br 1.19 T) 근사 ±10 %. 최대 31 mT < A2 선형 ±44 mT.", "notes", size=1.9)
    s.text(130, 121.3, "재무장선 = 자석 복귀 50 %(ADC 중간값이 아님 — ADC는 간격에 비선형). 흑은 1 N에서 강체 바닥보다 0.15 mm 위에 멈춤 → note-on 문턱은 흑 ≈2900 아래로.", "notes", size=1.9)
    s.text(130, 124.1, "재무장(50 %) 백 8.21 mm · ADC ≈2373, 흑 9.34 mm · ≈2282. 1 N 정착 바닥 백 5.52 mm · ≈2890, 흑 5.47 mm · ≈2907.", "notes", size=1.9)
    s.text(130, 126.9, "ADC 코드 2560(E11) 이 행정 안에 있다 → 문턱을 10 LSB 이상 떼거나 보정표. 건반마다 부팅 때 쉼, 보통(1 N) 누름으로 바닥 학습.", "notes", size=1.9)
    s.para(15, 165, [
        "주",
        "1. U201~U212: TI DRV5055A2QLPG (TO-92 LPG). 센서 x = W1 자석 보스 중심(모든 건반 같은 자리, 아래 표). 표시면을 위로 눕혀 센서 바 포켓에 넣고, 리드를 +x로 뺀 뒤 1.40~3.44 mm에서",
        "    2.54 간격으로 벌려 아래로 꺾어 기판 구멍(x = 0.63 + 2.54·i)에 꽂는다. 핀 1 VCC → y64.46, 핀 2 GND → y67.00, 핀 3 OUT → y69.54.",
        "2. C201~C212: 1206 100 nF X7R (CL31B104KCFNNNE), 기판 아랫면 3V3–GND 패드 사이, 각 센서 핀 1·2 바로 옆.",
        "    아랫면 부품·납땜·리드 끝 ≤ 1.8 mm (기판 밑 z7.0 − 바닥 z5.0 = 2.0, W1 r4.5 P36): 칩은 납작하게, 센서 리드는 납땜 뒤 1 mm 이하로 자른다.",
        "3. C213·C214: 10 µF 1206 16 V (버스 양 끝, 구매 목록 L67). △1 글 사양에는 있으나 구매 목록에 없던 부품. 두께 1.6 ± 0.2라 1.8 한계 안.",
        "4. 기판: 양면 도트 만능기판 x1.0~162.6 × y60.65~75.89 (6행; 바 끝 x162.9보다 0.3 짧게 → 오른쪽 턱 기둥 x163.0과 0.4). y64.46 = 3V3 버스, y67.00 = GND, y69.54 = OUT.",
        "5. 고정: M3×10 자가 탭 2 (3.0, 61.9)·(3.0, 74.6) — 구멍 Ø3.4가 기판 앞·뒤 가장자리를 넘으므로 U자 홈으로 판다(BRD-02).",
        "6. △12 리본 16심(3V3·GND 2가닥씩)을 각 OUT 패드에서 아랫면을 따라 J201(2×8)로 모아 W1 리본 차선(x59~82)으로 제어 기판까지.",
        "7. 고정 나사 M3×10(구매 목록 L34, ISO 7380 머리 Ø5.7)은 센서 바 위(z13.6)에서 바·기판 U홈을 지나 받침 기둥(x0.5~6.0)에 조인다(W1 P36) —",
        "    머리는 기판에 닿지 않는다. U홈(Ø3.4) 안 나사 몸통과 3V3 버스(y64.46, 아랫면, x8.25부터)는 떨어져 있다 — 버스 주석을 x6 안쪽으로 번지게 하지 않는다.",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS = [sch02]


# ------------------------------------------------------------------ helpers for modules
def zero_sym(ref_title="RP2040-Zero"):
    L = ["5V", "3V3", "GND", None, "GP26", "GP27", "GP28", "GP29", None, "GP14", "GP15"]
    R = [f"GP{i}" for i in range(14)]
    left = [None if n is None else (P.zero_pin(n), n) for n in L]
    right = [(P.zero_pin(n), n) for n in R]
    return sym_box("RP2040-Zero", left, right, width=34, cls="mod", rows=14)


def mux_sym():
    left = [(P.mux_pin(f"C{i}"), f"C{i}") for i in range(16)]
    R = ["SIG", None, "S0", "S1", "S2", "S3", None, "EN", None, "VCC", "GND"]
    right = [None if n is None else (P.mux_pin(n), n) for n in R]
    return sym_box("CD74HC4067_module", left, right, width=30, cls="mod", rows=16)


ID_BITS = {1: (1, 0, 0), 2: (0, 1, 0), 3: (1, 1, 0), 4: (0, 0, 1), 5: (1, 0, 1), 6: (0, 1, 1), 7: (1, 1, 1)}


# ------------------------------------------------------------------ SCH-03
def sch03(sig_r=None):
    s = Sheet("SCH-03", 3, TOTAL, "옥타브 제어 기판 (MB)",
              "RP2040-Zero가 CD74HC4067 먹스로 센서 12개 + EXT 4채널을 ADC0(GP26) 하나로 읽어 USB-MIDI로 보낸다. 모듈 O1~O7에 7장, ID 점퍼만 다르다.",
              "MB", qty="MB × 7", basis="v4 W1+ r4.5")
    e = {}
    # J301 ribbon in — 2x8 block (same numbering as J201)
    names = RIBBON
    j = sym_conn2("Conn_02x08_Odd_Even", 8, width=12)
    s.place(j, "J301", "리본 16심 입력 2×8", 45, 30, ref_at=(0, -2.2), val_at=(0, 44.0))
    for i, nm in enumerate(names):
        px, py = s.pin("J301", i + 1)
        d = -1 if (i + 1) % 2 else 1
        L = 20 if nm in POWER else 5
        s.wire((px, py), (px + d * L, py))
        net_end(s, px + d * L, py, nm, "L" if d < 0 else "R")
        exp_add(e, nm, f"J301.{i+1}")
    s.text(22, 81.5, "← SCH-02 J201 (리본 선 n = 핀 n)", "cabt", size=2.2)
    # A302 mux module
    mx, my = 110, 30
    s.place(mux_sym(), "A302", "CD74HC4067 16채널 먹스 모듈", mx, my, val_at=(0, 90.5), part_at=(0, 92.8),
            part="파츠파츠 PP-A324 · 모듈 헤더를 기판에 직접 납땜")
    for i in range(16):
        nm = f"C{i}"
        px, py = s.pin("A302", P.mux_pin(nm))
        s.wire((px, py), (px - 7.5, py))
        net = NET[KEYS[i]] if i < 12 else f"EXT{i-11}"
        s.label(px - 7.5, py, net, "L")
        exp_add(e, net, f"A302.{P.mux_pin(nm)}")
    # right side of mux
    sx, sy = s.pin("A302", P.mux_pin("SIG"))
    if sig_r:
        s.wire((sx, sy), (sx + 5, sy))
        s.place(sym_R(), "R301", sig_r, sx + 12.5, sy, rot=90)
        a, b = s.pin("R301", 1), s.pin("R301", 2)
        s.wire((sx + 5, sy), b if b[0] < a[0] else a)
        far = a if a[0] > b[0] else b
        s.wire(far, (far[0] + 5, far[1]))
        s.label(far[0] + 5, far[1], "MUX_SIG", "R")
        s.label(sx + 0.01 + 2.5, sy, "MUX_OUT", "R")
        exp_add(e, "MUX_OUT", f"A302.{P.mux_pin('SIG')}", "R301.2" if b[0] < a[0] else "R301.1")
        exp_add(e, "MUX_SIG", "R301.1" if b[0] < a[0] else "R301.2")
    else:
        s.wire((sx, sy), (sx + 10, sy))
        s.label(sx + 10, sy, "MUX_SIG", "R")
        exp_add(e, "MUX_SIG", f"A302.{P.mux_pin('SIG')}")
    for k in range(4):
        px, py = s.pin("A302", P.mux_pin(f"S{k}"))
        s.wire((px, py), (px + 10, py))
        s.label(px + 10, py, f"MUX_S{k}", "R")
        exp_add(e, f"MUX_S{k}", f"A302.{P.mux_pin(f'S{k}')}")
    px, py = s.pin("A302", P.mux_pin("EN"))
    s.wire((px, py), (px + 7.5, py))
    s.pwr(px + 7.5, py, "GND")
    exp_add(e, "GND", f"A302.{P.mux_pin('EN')}")
    s.text(px + 10, py + 0.8, "EN 항상 LOW = 켜짐", "notes", size=2.0)
    vx, vy = s.pin("A302", P.mux_pin("VCC"))
    gx, gy = s.pin("A302", P.mux_pin("GND"))
    s.wire((vx, vy), (vx + 20, vy))
    s.pwr(vx + 7.5, vy, "+3V3")
    s.place(sym_C(), "C301", "100n", vx + 20, vy + 5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.wire((gx, gy), (gx + 5, gy))
    s.pwr(gx + 5, gy, "GND")
    s.pwr(vx + 20, vy + 10, "GND")
    s.chg(vx + 29, vy + 9.5, 2)
    exp_add(e, "+3V3", f"A302.{P.mux_pin('VCC')}", "C301.1")
    exp_add(e, "GND", f"A302.{P.mux_pin('GND')}", "C301.2")
    # A301 RP2040-Zero
    zx, zy = 215, 30
    s.place(zero_sym(), "A301", "RP2040-Zero", zx, zy, val_at=(0, 80.5), part_at=(0, 82.8),
            part="파츠파츠 PP-A799-2 · 안쪽 구멍에 핀 헤더로 (BRD-01)")
    zp = lambda n: s.pin("A301", P.zero_pin(n))
    x, y = zp("5V"); s.nc(x, y)
    x, y = zp("3V3"); s.wire((x, y), (x - 7.5, y)); s.pwr(x - 7.5, y, "+3V3"); exp_add(e, "+3V3", f"A301.{P.zero_pin('3V3')}")
    x, y = zp("GND"); s.wire((x, y), (x - 5, y)); s.pwr(x - 5, y, "GND"); exp_add(e, "GND", f"A301.{P.zero_pin('GND')}")
    x, y = zp("GP26"); s.wire((x, y), (x - 10, y)); s.label(x - 10, y, "MUX_SIG", "L"); exp_add(e, "MUX_SIG", f"A301.{P.zero_pin('GP26')}")
    s.text(x - 25, y + 3.4, "ADC0", "notes", size=2.0)
    for n in ("GP27", "GP28", "GP29", "GP15", "GP0", "GP1", "GP9", "GP10", "GP11", "GP12", "GP13"):
        x, y = zp(n); s.nc(x, y)
    # GP14 PED select jumper (open on octave boards)
    x, y = zp("GP14")
    s.wire((x, y), (x - 17.5, y))
    s.place(sym_jumper(), "JP304", "열림", x - 22.5, y, ref_at=(0, -3.0, "middle"), val_at=(0, 5.0, "middle"))
    s.label(x - 16.5, y, "PED_SEL", "R", up=True)
    a = s.pin("JP304", 1)
    s.wire(a, (a[0] - 5, a[1]))
    s.pwr(a[0] - 5, a[1], "GND")
    exp_add(e, "PED_SEL", f"A301.{P.zero_pin('GP14')}", "JP304.2")
    exp_add(e, "GND", "JP304.1")
    for k in range(4):
        x, y = zp(f"GP{k+2}")
        s.wire((x, y), (x + 10, y))
        s.label(x + 10, y, f"MUX_S{k}", "R")
        exp_add(e, f"MUX_S{k}", f"A301.{P.zero_pin(f'GP{k+2}')}")
    for k in range(3):
        x, y = zp(f"GP{k+6}")
        ref = f"JP{301+k}"
        s.wire((x, y), (x + 12.5, y))
        s.label(x + 2.5, y, f"ID{k}", "R")
        s.place(sym_jumper(), ref, "", x + 17.5, y, ref_at=(11.5, 0.9), val_at=None, hide_val=True)
        b = s.pin(ref, 2)
        s.wire(b, (b[0] + 2.5, b[1]))
        s.pwr(b[0] + 2.5, b[1], "GND")
        exp_add(e, f"ID{k}", f"A301.{P.zero_pin(f'GP{k+6}')}", f"{ref}.1")
        exp_add(e, "GND", f"{ref}.2")
    s.text(zx + 34 + 5 + 38, zy + 5 * 7 + 0.8, "← ID 점퍼 (아래 표)", "notes", size=2.0)
    # USB
    s.cable((zx + 17, zy), (zx + 17, zy - 9), text="USB-C (모듈 내장) → 허브, SCH-01 W201~W207", at=(zx + 19, zy - 6), anchor="start")
    s.text(zx, zy + 87.6, "GP16 = 기판 WS2812 LED (안 씀) · GP17~25 밑면 패드 (안 씀)", "notes", size=1.9)
    # J302 EXT (△6 order: 1 GND, 2..5 EXT1..4, 6 +3V3)
    jn = ["GND", "EXT1", "EXT2", "EXT3", "EXT4", "+3V3"]
    s.place(sym_conn("Conn_01x06", 6, side="L", width=6), "J302", "EXT 패드 1×6 (2.54)", 345, 30,
            ref_at=(0, -2.2), val_at=(-6, 34.5))
    for i, nm in enumerate(jn):
        px, py = s.pin("J302", i + 1)
        L = 20 if nm in POWER else 7.5
        s.wire((px, py), (px - L, py))
        net_end(s, px - L, py, nm, "L")
        exp_add(e, nm, f"J302.{i+1}")
        s.text(353, py + 0.8, ["GND (검정 끝선)", "EXT1 → C12", "EXT2 → C13", "EXT3 → C14", "EXT4 → C15", "3V3 (빨강 끝선)"][i], "notes", size=2.0)
    s.text(318, 68.5, "O1·O7만 6심 150 mm 연장선 → JST-XH 6P (SCH-04)", "notes", size=2.0)
    s.chg(338, 26.5, 6)
    s.chg(66, 26.5, 12)
    # EXT pull-downs (△8, review R4); the 1 kohm series resistors sit on EL/ER at the sensor (SCH-04)
    s.box(282, 80, 114, 42, "EXT 풀다운 △8 — O1: R301~R303, O7: R301만 실장")
    for n in range(1, 5):
        x0 = 292.5 + (n - 1) * 26
        rp = f"R{300+n}"
        s.label(x0, 90, f"EXT{n}", "R")
        s.wire((x0, 90), (x0, 92.5))
        s.place(sym_R(), rp, "100k", x0, 100, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
        s.pwr(*s.pin(rp, 2), "GND")
        exp_add(e, f"EXT{n}", f"{rp}.1")
        exp_add(e, "GND", f"{rp}.2")
    s.text(286, 118.5, "끝 부속을 빼도 EXT가 뜨지 않게 (0.15 V 아래 = 센서 없음)", "notes", size=1.9)
    # test points (R30)
    for i, (ref, net) in enumerate((("TP301", "+3V3"), ("TP302", "GND"), ("TP303", "MUX_SIG"))):
        tx, ty = 150 + i * 12.5, 112.5
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        if net == "GND":
            s.wire((tx, ty), (tx, ty + 2.5)); s.pwr(tx, ty + 2.5, "GND")
        elif net == "+3V3":
            s.wire((tx, ty), (tx, ty + 2.5), (tx - 5, ty + 2.5)); s.pwr(tx - 5, ty + 2.5, "+3V3")
        else:
            s.wire((tx, ty), (tx, ty + 5)); s.label(tx, ty + 5, net, "R", up=False)
        exp_add(e, net, f"{ref}.1")
    # ID table
    rows = []
    for m in range(1, 8):
        b = ID_BITS[m]
        ext = {1: "C12~14 → A0·A#0·B0 (21~23)", 7: "C12 → C8 (108)"}.get(m, "—")
        rows.append([f"O{m}", "닫음" if b[0] else "—", "닫음" if b[1] else "—", "닫음" if b[2] else "—", "—",
                     f"Toccata O{m}", f"{24+12*(m-1)} (C{m})", ext])
    rows.append(["PED", "—", "—", "—", "JP504 닫음", "Toccata PED", "—", "페달 (SCH-05)"])
    s.table(15, 132, ["보드", "JP301 GP6", "JP302 GP7", "JP303 GP8", "JP304 GP14", "USB 이름", "C 건반 MIDI", "EXT 입력"],
            rows, [11, 17, 17, 17, 18, 24, 22, 46], title="ID 점퍼 (닫음 = GND 납땜 브리지 = 1, GP6 = 비트0)", mono_cols=(0,))
    # pin map table (pad numbers from parts.py: dj505 library / Waveshare P1)
    zp_ = P.zero_pin
    ws = P.WS_P1
    pm = [["GP26 (ADC0)", f"{zp_('GP26')} / {ws['GP26']}", "MUX_SIG", "입력(아날로그)", "먹스 공통 출력"],
          ["GP2~GP5", f"{zp_('GP2')}~{zp_('GP5')} / {ws['GP2']}~{ws['GP5']}", "MUX_S0~S3", "출력", "먹스 채널 선택 (S0 = GP2)"],
          ["GP6·GP7·GP8", f"{zp_('GP6')}~{zp_('GP8')} / {ws['GP6']}~{ws['GP8']}", "ID0~ID2", "입력, 내부 풀업", "모듈 번호 (브리지 = 1)"],
          ["GP14", f"{zp_('GP14')} / {ws['GP14']}", "PED_SEL", "입력, 내부 풀업", "PED 보드만 GND"],
          ["3V3", f"{zp_('3V3')} / {ws['3V3']}", "+3V3", "전원 출력", "센서 + EXT + 먹스 급전"],
          ["GND", f"{zp_('GND')} / {ws['GND']}", "GND", "—", ""],
          ["5V (= USB VBUS)", f"{zp_('5V')} / {ws['5V']}", "—", "연결 금지", "보드끼리 5V 묶지 않는다"],
          ["GP0·1·9~13·15·27~29", "—", "—", "연결 안 함", "×(NC) 표시"]]
    s.table(15, 175, ["핀", "패드 dj505 / WS P1", "넷", "방향", "용도"], pm, [40, 30, 22, 26, 44],
            title="RP2040-Zero 핀 배정 (패드 = dj505 KiCad 라이브러리 번호 / Waveshare 회로도 P1 번호)", mono_cols=(0, 1, 2))
    s.para(190, 132, [
        "주",
        "1. 기판: 양면 만능기판 5×7 cm, x47.25~117.25 × y145.5~195.5, 모듈 바닥 구멍으로 밑에서 넣는다(W1 r4.5). 고정 4곳",
        "    (50.0,149.0)(114.5,149.0)(50.0,192.5)(114.5,192.5) = 매단 보스 — 대각 2곳 M3×6(밑에서), 2곳 위치 핀 (BRD-01 주 8).",
        "2. W1 r4.3: 앞 모서리에서 홈 x81.92~84.72 × y145.5~172.0을 따낸다(F|F# 핀 발·킬이 지나감, r4.5).",
        "    W1 r4.3 금지 구역 x81.22~85.42 × y145.5~173.2에는 부품·배선·리본 패드를 두지 않는다 (제로 PCB만 y172~173.2에 걸침).",
        "3. RP2040-Zero: x75.14~93.14, y172~195.5, USB-C +y (리셉터클 가운데 x84.00 = W1 선반 홈 가운데, BRD-01 주 1).",
        "    밑면 부품 때문에 평평하게 붙지 않는다 → 안쪽 구멍에 핀 헤더(몰드 뺌),"
        "    모듈은 밑면 부품 위(캡톤)에 얹혀 약 1.3 mm 높아진다. W1 r4.3이 뒤 선반에 USB 플러그 홈을 내 1.3 mm 확보(BRD-01 주).",
        f"4. A302 먹스 모듈: W1 기판 홈(F|F# 핀 발이 지나감)을 피해 {MBX['mux'].split(' ×')[0]}에 세로로 → BRD-01 배치. J301 리본은 아랫면 납땜.",
        "5. △2 C301 100 nF: 먹스 모듈 VCC–GND 헤더 핀 옆 (모듈 C1이 사진에 있으나 미확인 → 달아 둔다). EN은 GND에 직접.",
        "6. 펌웨어는 ID별 채널만 읽는다 (O1 C0~C14, O7 C0~C12, O2~O6 C0~C11). O2~O6은 J302·R301~R304 비움.",
        "    △8 끝 부속을 뽑으면 EXT가 떠서 유령 음이 난다 → 100 kΩ 풀다운(여기) + 1 kΩ 직렬(EL·ER 센서 옆, SCH-04).",
        "7. 펌웨어: S0~S3 바꾼 뒤 4 µs(또는 변환 2번 버림) 기다려 변환. 문턱은 ADC 코드 1536·2560·3584에서 10 LSB 이상(E11).",
        "8. 펌웨어: ID 핀은 풀업을 켠 뒤 10 µs 기다려 읽는다. 복제 보드면 PICO_XOSC_STARTUP_DELAY_MULTIPLIER=64.",
        "9. W1 펌웨어 규칙(W1 r4.5 DESIGN 0.1 = gfilter): 재무장선 = 자석 복귀 50 %. 유령 거름(U6) — 같은 건반에서 앞끝 0.3 m/s 이상인",
        "    음의 note-on부터 250 ms 안에 재무장선을 넘으면 의심 상태. note-on부터 500 ms 안에 닿는 첫 다시 눌림의 내려오는 속도(손가락 점)가",
        "    min(0.45 m/s, 앞 음 × 25 %) 미만이면 버리고, 500 ms가 지나면 의심을 풀어 다음 눌림은 보통 음(1 s 뒤 여린 연타는 산다).",
        "    펌웨어는 단계 0 시험 11에서 다시 눌림 시각을 기록 — 500 ms를 넘는 유령이 있으면 창 = 가장 늦은 것 + 100 ms. (선택) 자석 0.01 m/s 미만 느린 통과는 음 없음.",
        "    MCU가 재는 것은 자석(y67) 속도 = 두 문턱 사이 시간. W1 행정비: 앞끝 = 자석 × 1.91(백) / 1.18(흑), 손가락 점 = 자석 × 1.74 / 1.05",
        "    → 자석 단위: 앞 음 0.157 / 0.254 m/s, 재타건 상한 0.259 / 0.429 m/s, 비율 27.5 % / 28.2 % (단계 0 시험 11 불합격 시 30 % → 33.0 / 33.8 %).",
        "    앞 음 속도는 행정 아래쪽(최대 속도) 구간에서 잰다. ADC는 간격에 비선형이라 문턱은 자기장 곡선(또는 건반별 보정표)으로 mm 환산.",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch03)


# ------------------------------------------------------------------ SCH-04
def _end_board(s, e, y0, tag, keys, ubase, cbase, rbase, jref, xref, rail):
    """One end-part sensor board + harness. keys = [(key, net, ext_no)]."""
    y3, yg, yc = y0 + 20, y0 + 70, y0 + 45
    hall, cap = sym_hall(), sym_C()
    xs0, dx = 45, 42.5
    xend = xs0 + dx * (len(keys) - 1) + 32.5
    s.pwr(25, y3, rail)
    s.wire((25, y3), (xend, y3))
    s.pwr(25, yg, "GND")
    s.wire((25, yg), (xend, yg))
    for i, (k, net, ext) in enumerate(keys):
        xs = xs0 + dx * i
        u, c, r = f"U{ubase+i}", f"C{cbase+i}", f"R{rbase+i}"
        s.place(hall, u, "DRV5055A2QLPG", xs, yc, ref_at=(1.6, -8.4), hide_val=True, meta=dict(key=k))
        s.text(xs - 4.8, yc + 13.5, k, "noteb", size=2.8)
        a = s.pin(u, 1); s.wire(a, (a[0], y3))
        b = s.pin(u, 2); s.wire(b, (b[0], yg))
        o = s.pin(u, 3)
        s.place(sym_R(), r, "1k", o[0] + 7.5, o[1], rot=90, ref_at=(0, -3.0, "middle"), val_at=(0, 4.9, "middle"))
        ra = min((s.pin(r, 1), s.pin(r, 2)), key=lambda q: q[0])
        rb = max((s.pin(r, 1), s.pin(r, 2)), key=lambda q: q[0])
        s.wire(rb, (rb[0] + 1, rb[1]))
        s.label(rb[0] + 1, rb[1], net, "R")
        num = lambda q: "1" if s.pin(r, 1) == q else "2"
        exp_add(e, rail, f"{u}.1"); exp_add(e, "GND", f"{u}.2")
        exp_add(e, f"~{u}_OUT", f"{u}.3", f"{r}.{num(ra)}")
        exp_add(e, net, f"{r}.{num(rb)}")
        s.place(cap, c, "100n", xs - 7.5, yc + 7.5, ref_at=(-1.0, -1.2, "end"), val_at=(-1.0, 2.2, "end"))
        a = s.pin(c, 1); s.wire(a, (a[0], y3))
        b = s.pin(c, 2); s.wire(b, (b[0], yg))
        exp_add(e, rail, f"{c}.1"); exp_add(e, "GND", f"{c}.2")
    s.chg(xs0 + 15, yc + 9, 8)
    s.chg(xs0 + 22, yc - 5, 13)
    cb = f"C{cbase+len(keys)}"
    s.place(sym_C(), cb, "10µ", xend, yc + 7.5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    a = s.pin(cb, 1); s.wire(a, (a[0], y3))
    b = s.pin(cb, 2); s.wire(b, (b[0], yg))
    s.chg(xend + 10, yc + 15, 3)
    exp_add(e, rail, f"{cb}.1"); exp_add(e, "GND", f"{cb}.2")
    # XH position map (△6): 1 = GND (black edge), 2..5 = EXT1..4, 6 = 3V3 (red edge) — same as J302 pads
    mod = "O1" if tag == "L" else "O7"
    pre = "EL" if tag == "L" else "ER"
    pos_map = {1: "GND", 6: rail}
    pos_key = {1: "GND", 6: "3V3"}
    for k, net, ext in keys:
        pos_map[ext + 1] = net
        pos_key[ext + 1] = k
    rows, n = [], 0
    for pos in range(1, 7):
        if pos in pos_map:
            n += 1
            rows.append((n, pos_key[pos]))
        else:
            rows.append(None)
    jb = sym_box("Conn_pads", [], rows, width=12, cls="body", pinlen=5, rows=6, top_pad=5)
    jx = 190
    s.place(jb, jref, f"리드선 패드 ×{n}", jx, y0 + 12.5, ref_at=(0, -2.2), val_at=(0, 38.5))
    xa, xb = f"X{xref}", f"X{xref+1}"
    s.place(sym_conn("JST_XH_6P", 6, side="L", width=6), xa, "JST-XH 6P (끝 부속 쪽)", 250, y0 + 15,
            ref_at=(0, -2.2), val_at=(-20, 36.0))
    s.place(sym_conn("JST_XH_6P", 6, side="R", width=6), xb, "JST-XH 6P (모듈 쪽)", 257.5, y0 + 15,
            ref_at=(0, -2.2), val_at=(0, 39.0))
    s.mate(xa, xb, at=(256.3, y0 + 15 + 30 + 2.2))
    for pos in range(1, 7):
        r = rows[pos - 1]
        tx, ty = s.pin(xa, pos)
        if r is None:
            s.nc(tx, ty)
            exp_add(e, f"{pre}_EXT{pos-1}", f"{xa}.{pos}", f"{xb}.{pos}")
            continue
        jx_, jy_ = s.pin(jref, r[0])
        s.wire((jx_, jy_), (tx, ty))
        net = pos_map[pos]
        if net in POWER:
            s.pwr(jx_ + 25, jy_, net)
        else:
            s.label(jx_ + 3, jy_, net, "R")
        exp_add(e, net, f"{jref}.{r[0]}", f"{xa}.{pos}", f"{xb}.{pos}")
    s.cable((jx + 22, y0 + 8.5), (jx + 55, y0 + 8.5), text=None)
    s.text(jx + 22, y0 + 7.0, f"W{xref}: {n}심 {'350' if tag=='L' else '300'} mm", "cabt", size=2.2)
    col = {1: "검정 끝선", 6: "빨강 끝선"}
    for pos in range(1, 7):
        bx, by = s.pin(xb, pos)
        if pos in (1, 6):
            s.wire((bx, by), (bx + 24, by))
            s.pwr(bx + 24, by, "GND" if pos == 1 else rail)
            s.text(bx + 30, by + 0.8, f"→ {mod} J302-{pos} {'GND' if pos == 1 else '3V3'} ({col[pos]})", "notes", size=2.0)
        else:
            nm = pos_map.get(pos, f"{pre}_EXT{pos-1}")
            s.wire((bx, by), (bx + 5, by))
            s.glabel(bx + 5, by, nm, "R")
            s.text(bx + 30, by + 0.8, f"→ {mod} J302-{pos} EXT{pos-1} = 먹스 C{10+pos}" + ("" if pos in pos_map else " (비움)"), "notes", size=2.0)
    s.cable((267.5, y0 + 8.5), (297.5, y0 + 8.5))
    s.text(267.5, y0 + 7.0, f"W{xref+2}: 6심 150 mm → {mod} 제어 기판 EXT (SCH-03 J302)", "cabt", size=2.2)
    s.chg(248, y0 + 9, 6)


def sch04():
    s = Sheet("SCH-04", 4, TOTAL, "끝 부속 센서 기판 (EL · ER) + EXT 연결",
              "왼쪽 끝 부속 A0·A#0·B0 센서 3개는 O1, 오른쪽 C8 센서 1개는 O7 제어 기판의 EXT(먹스 C12~)로 읽는다. 파트 사이는 JST-XH 6핀 잠금 커넥터(R26).",
              "EL · ER", qty="EL × 1 · ER × 1", basis="v4 W1+ r4.5 끝 부속")
    e = {}
    s.box(14, 22, 380, 94, "EL — 왼쪽 끝 부속 센서 기판 (x1.0~46.5 × y60.65~75.89, 45.5 × 15.24 mm, 6행) — BRD-02 배치")
    _end_board(s, e, 22, "L", [("A0", "EL_A0", 1), ("A#0", "EL_AS0", 2), ("B0", "EL_B0", 3)],
               401, 401, 401, "J401", 401, "+3V3_EL")
    s.box(14, 120, 380, 94, "ER — 오른쪽 끝 부속 센서 기판 (로컬 x1.0~23.0 × y60.65~75.89, 22.0 × 15.24 mm, 6행) — BRD-02 배치")
    _end_board(s, e, 120, "R", [("C8", "ER_C8", 1)], 411, 411, 411, "J411", 411, "+3V3_ER")
    s.para(15, 220, [
        "주  1. 끝 부속 센서도 SCH-02와 같다: DRV5055A2 + 100 nF(센서 옆). W1 자석 x: 왼쪽 부속(x0~47) A0 10.287, A#0 26.927, B0 40.141, 오른쪽 부속(로컬 x0~23.5) C8 11.75.",
        "        기판은 W1 r4.2 끝 부속 센서 바(왼 x0.5~46.5, 오른 x0.5~23.0) 안: EL x1.0~46.5, ER x1.0~23.0 (SB와 같은 6행 15.24). 리드 구멍 A0 13.33, A#0 31.11, B0 43.81, C8 15.87.",
        "     2. 커넥터: 밸런스 연장선(JST-XH 6P, 200 mm)을 모듈 쪽 150 · 끝 부속 쪽 50으로 잘라 쓴다. ‘>>’ = 맞물림(KiCad에서는 연결이 아니다 →",
        "        양쪽에 같은 넷 이름). +3V3_EL·+3V3_ER은 각각 O1·O7 제어 기판의 3V3 레일이다(프로젝트 전원 심볼로 추가).",
        "     3. △6 XH 위치 = J302 EXT 패드 번호: 1 = GND(검정 끝선), 2~5 = 먹스 C12~C15, 6 = 3V3(빨강 끝선). 빨강 1 + 검정 5라 위치로만 구분 —",
        "        자르기 전에 양쪽에 번호 테이프, 납땜 뒤 끝에서 끝까지 통전 확인.",
        "     4. △3 C404·C412 10 µF: 3V3가 긴 선 끝(EL 150 + 350 mm, ER 150 + 300 mm)이라 벌크 콘덴서 추가.",
        "     5. △8 R401~R403·R411 1 kΩ 1206 칩(아랫면, △13): 센서 바가 기판 윗면을 덮어 리드형 저항을 둘 자리가 없다 — OUT 구멍과 바로 뒤 행(y72.08) 사이.",
        "        센서 OUT 바로 뒤에서 약 0.6 m 선 용량을 떼어 낸다(TI: OUT에 C 직결 금지). MB의 100 kΩ 풀다운과 함께",
        "        끝 부속을 빼면 EXT = 0 V. 펌웨어: O1 C12~C14 → MIDI 21~23, O7 C12 → 108, 0.15 V 아래면 센서 없음.",
        "     6. W401·W411 길(W1 r4.4, r4.5 그대로): 패드(아랫면) → 기판 밑 → 뒤 받침 리브 틈 → 패드 줄 뒤 y77.39 안에서 EL x14.83~21.18 · ER x8.89~12.70으로 모음",
        "        → 바닥(건반 밑) → 끝 부속 밸런스 레일 밑 차선(z5~10; EL x13.53~22.48, ER x7.59~14.00) → 뒷벽 홈(z5~12) → 뒤 케이블 통로의 X401·X411.",
        "        순서: 리본 가닥을 J401/J411에 납땜 → 기판·센서 바 고정 → 자유 끝을 리브 틈·차선·뒷벽 홈으로 꿴 뒤, 뒤 통로에서 L66 끝 부속 쪽 50 mm 리드와",
        "        이어 열수축(C10). XH 하우징(폭 약 17)은 차선·홈을 못 지나므로 먼저 달지 않는다. 아랫면 칩·납땜 ≤ 1.8 mm(기판 밑 2.0).",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch04)


# ------------------------------------------------------------------ SCH-05
def sch05(ring_r="20"):
    s = Sheet("SCH-05", 5, TOTAL, "페달 보드 (PB) + 댐퍼 페달 센서 (PS)",
              "댐퍼(서스테인) 페달 1개(R24). 페달 안 홀센서가 발판 자석 거리를 재고, PED 보드 RP2040-Zero가 CC64 0~127(하프페달)로 보낸다.",
              "PB · PS", qty="PB × 1 · PS × 1", basis="v4 W1+ · R24")
    e = {}
    # --- pedal sensor (inside the pedal)
    s.box(14, 22, 88, 80, "PS — 페달 안 센서 (만능기판 자투리)")
    s.place(sym_hall(), "U551", "DRV5055A2QLPG", 50, 60, ref_at=(-4.8, -9.2), hide_val=True)
    s.text(38, 76.0, "표시면 위 · 자석 Ø5×2 S극 아래", "notes", size=2.0)
    s.place(sym_C(), "C551", "100n", 32.5, 60, ref_at=(-1.0, -7.2, "end"), val_at=(-1.0, 9.5, "end"))
    a1 = s.pin("U551", 1); c1 = s.pin("C551", 1)
    s.wire(c1, (c1[0], 42.5), (a1[0], 42.5), a1)
    s.wire((a1[0], 42.5), (80, 42.5)); s.label(80, 42.5, "PED_VCC", "R")
    b1 = s.pin("U551", 2); c2 = s.pin("C551", 2)
    s.wire(c2, (c2[0], 85), (b1[0], 85), b1)
    s.wire((b1[0], 85), (80, 85)); s.pwr(80, 85, "GND")
    o = s.pin("U551", 3)
    s.place(sym_R(), "R551", "1k", o[0] + 10, o[1], rot=90, ref_at=(0, -3.0, "middle"), val_at=(0, 4.9, "middle"))
    ra = min((s.pin("R551", 1), s.pin("R551", 2)), key=lambda q: q[0])
    rb = max((s.pin("R551", 1), s.pin("R551", 2)), key=lambda q: q[0])
    s.wire(o, ra)
    s.wire(rb, (80, o[1])); s.label(80, o[1], "PED_TIP", "R")
    s.chg(o[0] + 10, o[1] + 9.5, 7)
    exp_add(e, "PED_VCC", "U551.1", "C551.1")
    exp_add(e, "~PS_OUT", "U551.3", "R551." + ("1" if s.pin("R551", 1) == ra else "2"))
    exp_add(e, "PED_TIP", "R551." + ("1" if s.pin("R551", 1) == rb else "2"))
    exp_add(e, "GND", "U551.2", "C551.2")
    s.text(18, 96.5, "W501 3 m 케이블 쪽 끝을 여기에 납땜 (팁 = OUT, 링 = VCC, 슬리브 = GND)", "cabt", size=2.0)
    # --- I/O plate: cable plug P501 mated into jack J501
    s.box(106, 22, 68, 80, "I/O 판 — 페달 잭")
    s.place(sym_plug(), "P501", "TRS 플러그 (PS 쪽)", 125, 42.5, ref_at=(0, -2.2), val_at=(0, 19.5),
            part="W501 끝 (3 m, L50)", part_at=(0, 21.8))
    for nm, net in (("T", "PED_TIP"), ("R", "PED_VCC"), ("S", "GND")):
        x, y = s.pin("P501", nm)
        s.wire((x, y), (x - 5, y))
        net_end(s, x - 5, y, net, "L")
        exp_add(e, net, f"P501.{nm}")
    s.place(sym_jack(), "J501", "PJ-313 페달 잭", 145, 40, ref_at=(0, -2.2), val_at=(0, 31.5),
            part="L15 ②", part_at=(0, 33.8))
    s.mate("P501", "J501", at=(142.5, 55.0))
    jt, jr, js = s.pin("J501", "T"), s.pin("J501", "R"), s.pin("J501", "S")
    x, y = s.pin("J501", "RN")
    s.nc(x, y)
    x, y = s.pin("J501", "TN")
    s.wire((x, y), (x + 8, y))
    s.pwr(x + 8, y, "GND")
    s.chg(x + 14, y - 0.5, 9)
    exp_add(e, "GND", "J501.TN")
    exp_add(e, "PED_TIP", "J501.T")
    exp_add(e, "PED_VCC", "J501.R")
    exp_add(e, "GND", "J501.S")
    s.text(108, 97.0, "J501 → PB: 짧은 선 4가닥 약 10 cm (T, TN, R, S)", "cabt", size=2.0)
    # --- PB board
    s.box(178, 22, 218, 110, "PB — 페달 보드 5 × 7 cm (CU 칸 안)")
    s.place(sym_R(), "R501", "1k", 207.5, jt[1], rot=90, ref_at=(0, -3.0, "middle"), val_at=(0, 4.9, "middle"))
    s.place(sym_R(), "R502", "100k", 207.5, jt[1] - 12.5, rot=90, ref_at=(0, -3.0, "middle"), val_at=(0, 4.9, "middle"))
    s.place(sym_R(), "R503", ring_r + "Ω", 207.5, jr[1], rot=90,
            ref_at=(0, 5.0, "middle"), val_at=(0, 8.0, "middle"), part="100Ω ×5 병렬", part_at=(0, 10.3, "middle"))
    L = lambda ref: min((s.pin(ref, 1), s.pin(ref, 2)), key=lambda p: p[0])
    Rr = lambda ref: max((s.pin(ref, 1), s.pin(ref, 2)), key=lambda p: p[0])
    num = lambda ref, pt: "1" if s.pin(ref, 1) == pt else "2"
    s.wire(jt, (190, jt[1]), L("R501"))
    s.wire((190, jt[1]), (190, L("R502")[1]), L("R502"))
    s.label(181, jt[1], "PED_TIP", "R")
    s.wire(jr, L("R503"))
    s.label(181, jr[1], "PED_VCC", "R")
    s.wire(Rr("R503"), (Rr("R503")[0] + 7.5, jr[1]))
    s.pwr(Rr("R503")[0] + 7.5, jr[1], "+3V3")
    s.wire(js, (185, js[1]))
    s.pwr(185, js[1], "GND")
    s.place(sym_C(), "C501", "100n", 235, jt[1] + 5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
    s.wire(Rr("R501"), (235, jt[1]), (255, jt[1]))
    s.label(255, jt[1], "PED_ADC", "R")
    s.pwr(235, jt[1] + 10, "GND")
    s.wire(Rr("R502"), (Rr("R502")[0] + 5, Rr("R502")[1]))
    s.pwr(Rr("R502")[0] + 5, Rr("R502")[1], "GND")
    s.chg(Rr("R502")[0] + 10, Rr("R502")[1] - 1, 11)
    exp_add(e, "PED_TIP", "R501." + num("R501", L("R501")), "R502." + num("R502", L("R502")))
    exp_add(e, "PED_ADC", "R501." + num("R501", Rr("R501")), "C501.1")
    exp_add(e, "GND", "C501.2")
    exp_add(e, "GND", "R502." + num("R502", Rr("R502")))
    exp_add(e, "PED_VCC", "R503." + num("R503", L("R503")))
    exp_add(e, "+3V3", "R503." + num("R503", Rr("R503")))
    s.chg(207.5, jr[1] + 13.5, 4)
    # A501 RP2040-Zero
    zx, zy = 320, 35
    s.place(zero_sym(), "A501", "RP2040-Zero", zx, zy, val_at=(0, 80.5), part_at=(0, 82.8),
            part="PED 보드 — USB 이름 'Toccata PED'")
    zp = lambda n: s.pin("A501", P.zero_pin(n))
    x, y = zp("5V"); s.nc(x, y)
    x, y = zp("3V3"); s.wire((x, y), (x - 7.5, y)); s.pwr(x - 7.5, y, "+3V3"); exp_add(e, "+3V3", f"A501.{P.zero_pin('3V3')}")
    x, y = zp("GND"); s.wire((x, y), (x - 5, y)); s.pwr(x - 5, y, "GND"); exp_add(e, "GND", f"A501.{P.zero_pin('GND')}")
    x, y = zp("GP26"); s.wire((x, y), (x - 10, y)); s.label(x - 10, y, "PED_ADC", "L"); exp_add(e, "PED_ADC", f"A501.{P.zero_pin('GP26')}")
    s.text(x - 1, y - 2.4, "ADC0", "notes", size=1.8, check=False) if False else None
    x, y = zp("GP27"); s.nc(x, y)
    x, y = zp("GP14")
    s.wire((x, y), (x - 17.5, y))
    s.place(sym_jumper(bridged=True), "JP504", "닫음 (브리지)", x - 22.5, y, ref_at=(0, -3.0, "middle"), val_at=(0, 5.0, "middle"))
    s.label(x - 16.5, y, "PED_SEL", "R", up=True)
    a = s.pin("JP504", 1); s.wire(a, (a[0] - 5, a[1])); s.pwr(a[0] - 5, a[1], "GND")
    exp_add(e, "PED_SEL", f"A501.{P.zero_pin('GP14')}", "JP504.2")
    exp_add(e, "GND", "JP504.1")
    for n in ["GP28", "GP29", "GP15"] + [f"GP{i}" for i in range(14)]:
        x, y = zp(n); s.nc(x, y)
    s.cable((zx + 17, zy), (zx + 17, zy - 9), text="USB-C → 허브 (CU 칸 안 짧은 선, W208)", at=(zx + 19, zy - 6), anchor="start")
    for i, (ref, net) in enumerate((("TP501", "PED_TIP"), ("TP502", "PED_VCC"))):
        tx, ty = 285 + i * 17.5, 112.5
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        s.wire((tx, ty), (tx, ty + 5)); s.label(tx, ty + 5, net, "R", up=False)
        exp_add(e, net, f"{ref}.1")
    s.para(15, 142, [
        "주",
        "1. 페달(L43)의 마이크로스위치 배선을 떼고, 발판 밑면 발끝 쪽에 자석 Ø5×2(S극 아래)를 붙인다. 바로 아래 바닥판에 U551을 표시면이 위로 오게",
        "    세워 붙인다. 간격: 눌렀을 때 약 4.5 mm, 뗐을 때 12 mm 이상 (약 36 → 2.4 mT, DRV5055A2 선형 범위 안). 발판이 강철이면 최대값 확인.",
        "2. W501: 3 m 스테레오 케이블(L50)의 한쪽 플러그를 잘라 팁 = 센서 OUT, 링 = VCC, 슬리브 = GND로 납땜, 케이블 타이로 당김 방지.",
        "3. J501 → PB: 짧은 선 4가닥 (약 10 cm). △9 TN을 GND에: 플러그가 없으면 팁이 GND에 붙어 0 V (RN은 안 씀).",
        "4. R501 1 kΩ + C501 100 nF: ADC 입력 RC (fc 약 1.6 kHz). △11 R502 100 kΩ 팁→GND (이전 글 사양의 'GP27로 뗀 쪽 전압 구동'은",
        "    GPIO가 0 / 3.3 V만 내므로 불가 → 고정 풀다운). 자석 S극이 표시면을 향해 누르면 OUT이 오른다. 0.15 V 아래 = 페달 없음 → CC64 = 0.",
        "5. △4 R503 20 Ω = 100 Ω ×5 병렬 (이전 사양 0 Ω, 구매 목록의 100 Ω 사용): 플러그를 꽂는 순간이나 TS(모노) 플러그로 링이 GND에 닿아도",
        "    약 165 mA로 제한 → PED 보드가 리셋되지 않는다. 센서 쪽 3.05 V 이상인지 꽂은 상태로 확인 (DRV5055 최소 3.0 V).",
        "6. PED 보드 ID: GP6~GP8 비움(000), JP504 닫음(GP14 = GND) → USB 이름 'Toccata PED'. 소스테누토·소프트 입력 없음(R24).",
        "7. △7 R551 1 kΩ: 센서 OUT 바로 뒤(페달 안). 3 m 케이블 용량(수백 pF)이 OUT에 바로 걸리지 않게 한다 (TI: OUT에 C 직결 금지).",
        "8. P501은 W501 케이블 끝(PS 쪽 부품)이라 KiCad에서는 PS 프로젝트에 둔다. PED_VCC에는 PWR_FLAG.",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch05)


# ------------------------------------------------------------------ SCH-06
def f1(v):
    return f"{v:.1f}"


def _display_band(s, e, y0=180.0):
    """△16 (rev C): R31 screen A605 = Waveshare 7-DSI-TOUCH-C. Power from the Pi 40-pin header pin 2 / pin 6
    through two silicone jumpers (F/F, M/M) and the screen's own MX1.25 -> 2.54 3-pin cable; DSI over W605."""
    B = budget()
    s.box(14, y0, 392, 70, f"화면 A605 전원 · DSI (R31, B1 = {DISP['model']})")
    r0, r1, r2 = y0 + 17.5, y0 + 22.5, y0 + 27.5          # 5 V row, empty row (header pin 4), GND row
    top = r0 - 5.0                                         # module box top (top_pad 5)
    ctop = r0 - 2.5                                        # connector body top (pitch 5, rows 3)
    vy = ctop + 22.5                                       # value text row under the connector bodies
    my = ctop + 15 + 3.4                                   # >> mark row (below the GND symbols)

    def rows_net(x, net5="+5V_PI"):
        s.pwr(x, r0, net5)
        s.pwr(x, r2, "GND")

    # A603 (Pi 5) — only the 40-pin header part is drawn here; the USB-C input is P601 above
    hx = 18.0
    hdr = sym_box("RPi5_Header", [], [(2, "5V"), None, (6, "GND")], width=30, cls="mod", rows=5)
    s.place(hdr, "A603", "Raspberry Pi 5 2GB — 40핀 헤더 유닛", hx, top, hide_val=True, meta=dict(bomkey="PI5"))
    s.text(hx + 1.5, top + 6.3, "Raspberry Pi 5", "val", size=2.4)
    s.para(hx + 1.5, top + 10.0, ["40핀 헤더", "(A603의 한 부분)"], "notes", size=2.0, lh=2.8)
    s.para(hx + 1.5, top + 22.5, ["CAM/DISP 1 (22핀)", "→ W605"], "notes", size=2.0, lh=2.8)
    p2, p6 = s.pin("A603", 2), s.pin("A603", 6)
    stub = p2[0] + 6.0
    s.wire(p2, (stub, r0)); s.wire(p6, (stub, r2))
    rows_net(stub)
    exp_add(e, "+5V_PI", "A603.2"); exp_add(e, "GND", "A603.6")
    # chain of mated pairs (x = left edge of each connector body), wires = cable conductors
    xP603 = stub + 6.0
    s.place(sym_conn_pos("Dupont_FF", 3, [(1, 0), (2, 2)], side="R"), "P603", "F/F 끝 → 핀 2·6", xP603, ctop,
            ref_at=(0, -1.2), val_at=(0, vy - ctop), meta=dict(bomkey="JMPFF"))
    s.mate("A603", "P603", {"2": "1", "6": "2"}, at=(xP603 - 3.0, my))
    L = 30.0                                               # drawn wire length between the cable ends
    xs = {}
    x = xP603 + 6 + 5
    for cab, (ra, sa, ka, va), (rb, sb, kb, vb), pins_a, pins_b, pmap in (
            ("W606", ("X601", "Dupont_FF", "JMPFF2", "F/F 끝"), ("X602", "Dupont_MM", "JMPMM", "M/M 끝"),
             [(1, 0), (2, 2)], [(1, 0), (2, 2)], None),
            ("W607", ("X603", "Dupont_MM", "JMPMM2", "M/M 끝"), ("X604", "Housing_2.54_3P", "DPWR", "2.54 3핀 (동봉선)"),
             [(1, 0), (2, 2)], [(1, 0), (2, 1), (3, 2)], {"1": "1", "2": "3"})):
        xa = x + L + 5
        s.place(sym_conn_pos(sa, 3, pins_a, side="L"), ra, va, xa, ctop, ref_at=(0, -1.2),
                val_at=(6, vy - ctop, "end"), meta=dict(bomkey=ka))
        xb = xa + 7.5
        s.place(sym_conn_pos(sb, 3, pins_b, side="R"), rb, vb, xb, ctop, ref_at=(0, -1.2),
                val_at=(0, vy - ctop), meta=dict(bomkey=kb))
        s.mate(ra, rb, pmap, at=(xa + 6.8, my))
        for row, pa in ((r0, "1"), (r2, "2")):
            s.wire((x, row), s.pin(ra, pa))
        rows_net(x + L / 2)
        s.cable((x + 2, y0 + 10.5), (x + L - 2, y0 + 10.5))
        s.text(x + 2, y0 + 9.0, f"{cab} {'F/F' if cab == 'W606' else 'M/M'} 20 cm", "cabt", size=2.2)
        xs[cab] = (x, xa, xb)
        x = xb + 6 + 5
    s.nc(*s.pin("X604", "2"))
    s.text(s.pin("X604", "2")[0] + 1.2, r1 + 0.8, "빈 칸", "notes", size=1.9)
    # W608 = the screen's own cable: 2.54 3-pin housing (X604) -> MX1.25 2-pin plug (P604)
    xp4 = x + L + 5
    s.place(sym_conn_pos("MX1.25_2P", 3, [(1, 0), (2, 2)], side="L"), "P604", "MX1.25 2핀", xp4, ctop,
            ref_at=(0, -1.2), val_at=(0, vy - ctop), meta=dict(bomkey="DPWR2"))
    s.wire(s.pin("X604", "1"), s.pin("P604", "1"))
    s.wire(s.pin("X604", "3"), s.pin("P604", "2"))
    rows_net(x + (L - 5) / 2)
    s.cable((x + 2, y0 + 10.5), (x + L - 2, y0 + 10.5))
    s.text(x + 2, y0 + 9.0, "W608 동봉 전원선", "cabt", size=2.2)
    # A605 screen module (pins on the left, MX1.25 receptacle)
    ax = xp4 + 6 + 6 + 5 + 5
    scr = sym_box("Waveshare_7-DSI-TOUCH-C", [(1, "5V", "pwr"), None, (2, "GND", "pwr")], [], width=60, cls="mod", rows=5)
    s.place(scr, "A605", DISP["model"], ax, top, hide_val=True, meta=dict(bomkey="DISP7C"))
    s.para(ax + 10, top + 6.3, [DISP["model"]], "val", size=2.4)
    s.para(ax + 10, top + 10.0, ["7인치 1024×600 IPS · 5점 정전식 터치",
                                "터치 = Goodix I2C (W605 리본 안)",
                                f"5 V 약 {B['disp_a']:.2f} A ({B['disp_w']:.2f} W) · 자석 없음 (D14)",
                                "구매 목록 v4touch No.135 · CU 뚜껑 위 받침",
                                "DSI 22핀 0.5 mm ← W605"], "notes", size=2.0, lh=2.8)
    q1, q2 = s.pin("A605", 1), s.pin("A605", 2)
    st2 = q1[0] - 5.0
    s.wire(q1, (st2, r0)); s.wire(q2, (st2, r2))
    rows_net(st2)
    s.mate("P604", "A605", None, at=(xp4 + 6 + 2.6, my))
    s.chg(ax + 56, top - 3.2, 16)
    # expected nets of the whole harness
    for ref, n5, ng in (("P603", "1", "2"), ("X601", "1", "2"), ("X602", "1", "2"), ("X603", "1", "2"),
                        ("X604", "1", "3"), ("P604", "1", "2"), ("A605", "1", "2")):
        exp_add(e, "+5V_PI", f"{ref}.{n5}")
        exp_add(e, "GND", f"{ref}.{ng}")
    # W605 DSI ribbon (drawing only, like the USB cables)
    wy = top + 30 + 9.5
    s.cable((hx + 15, top + 30), (hx + 15, wy), (ax + 30, wy), (ax + 30, top + 30))
    s.text(hx + 18, wy - 1.5, f"W605: DSI FFC 22핀 0.5 mm {DISP['ffc_mm']} mm B형(반대면) — 22심 1 ↔ 1, Pi 5 CAM/DISP 1 → A605 DSI. A형(같은 면)은 보험 (v4touch No.49 · No.50)",
           "cabt", size=2.2)
    s.para(hx, wy + 4.5, [
        "색: 빨강 = 5 V (헤더 핀 2 → P603 1 → … → X604 1 → P604 1), 검정 = GND (핀 6 → … → X604 3 → P604 2). X604 2(가운데)는 빈 칸.",
        "‘>>’ = 꽂는 곳(KiCad에서는 연결이 아님) → 양쪽에 같은 전원 심볼 +5V_PI · GND. 핀 번호 1·2는 우리 규칙(빨강 = 1)."], "notes", size=2.0, lh=2.8)
    # notes (continue the sheet notes 1~8)
    s.para(ax + 66, y0 + 7.5, [
        "주 (화면, R31)",
        "9. A605는 Pi 40핀 헤더 2번(5 V)·6번(GND)에서만 전원을 받는다.",
        "    Pi에서 나가는 방향이라 허용(D16). 화면·연장선에 다른 5 V를",
        "    넣지 않는다. 헤더 2번은 Pi 안에서 USB-C 입력 레일과 같은 선:",
        "    P601(MT666) ← +5V1에서 온다 → 넷 이름 +5V_PI(전원 심볼).",
        "10. 동봉선 2.54 3핀 하우징 = 1 빨강 5 V · 2 빈 칸 · 3 검정 GND",
        "    (Waveshare 연결 사진: 원래 헤더 2·4·6에 바로 꽂는 선).",
        "    받으면 통전 검사로 확인한 뒤 연장선을 꽂는다.",
        f"11. 점퍼 두 단 {DISP['jumper_m'] * 200:.0f} cm(26 AWG) 왕복 강하 약 {B['drop_v']:.2f} V",
        f"    (0.134 Ω/m × {DISP['jumper_m'] * 4:.1f} m × {B['disp_a']:.2f} A). 꽂는 곳 3곳은 열수축(C10).",
        "12. 화면 GND는 Pi에서만(핀 6 + 리본 GND) — 다른 GND에 잇지",
        "    않는다(△5 별 접지 그대로).",
        "13. config.txt 한 줄:",
        f"    {DISP['overlay']}",
        "    (CAM/DISP 0이면 ,dsi0). 밝기 sysfs 0~255.",
        f"14. Pi USB-C 입력 약 {B['pi_in_a']:.1f} A → 최대 부하에서",
        "    vcgencmd get_throttled = 0x0 확인(D16).",
        "15. D14: 화면 켬·끔, 밝기 0·100 %에서 센서 유휴 흔들림을 다시 잰다.",
    ], size=2.0, lh=2.75)


def sch06():
    B = budget()
    s = Sheet("SCH-06", 6, TOTAL, "전원 (CU)",
              "USB-C PD 입력 하나(R28): PD 20 V → 퓨즈 → 스위치 → 20 V 버스 → 앰프 + 5.1 V 강압 → Pi 5 · 허브 · 화면(Pi GPIO 5 V, R31). Pi에는 강압 5 V만(D16).",
              "CU 전원", qty="CU × 1", basis="v4 W1+ · R28 · R31", **REV_C)
    e = {}
    # source (external)
    s.rect(16, 40, 34, 10, "mod", "body")
    s.text(18, 45.8, "65 W PD 충전기 / 보조배터리", "notes", size=2.0)
    s.text(16, 54, "벽: L62 65 W (한 포트만) · 무선: PD 20 V 3.25 A 이상 (D19)", "notes", size=1.9)
    s.text(16, 56.6, "W601: C-C 2 m (C23) / 0.6 m (C22)", "cabt", size=1.9)
    s.cable((50, 45), (80, 45), text="USB-C PD", at=(56, 43.2), anchor="start")
    # A601 PD trigger (4 output pads: 2 x VOUT+ round, 2 x GND square)
    pd = sym_box("HUSB238_module", [], [(1, "VOUT+"), (2, "VOUT+"), None, (3, "GND"), (4, "GND")], width=28, cls="mod", rows=5)
    s.place(pd, "A601", "HUSB238 PD 트리거 → 20 V", 80, 40, val_at=(0, 33.5), part="I/O 판 포켓 (L57) · VSET 패드 모두 열림 = 20 V", part_at=(0, 35.8))
    s.text(81.5, 50.8, "USB-C", "notes", size=2.0)
    v1, v2 = s.pin("A601", 1), s.pin("A601", 2)
    g1, g2 = s.pin("A601", 3), s.pin("A601", 4)
    s.wire(v2, (v2[0] + 3, v2[1]), (v1[0] + 3, v1[1]))
    s.wire(g1, (g1[0] + 3, g1[1]), (g2[0] + 3, g2[1]), g2)
    vx, vy = v1
    gx, gy = g1
    exp_add(e, "+20V_PD", "A601.2")
    exp_add(e, "GND", "A601.4")
    # fuse + switch
    s.place(sym_fuse(), "F601", "5 A T (0218005.MXP)", vx + 22.5, vy, ref_at=(0, -3.0, "middle"), val_at=(0, 5.0, "middle"),
            part="홀더 BU914 (XF601)", part_at=(0, 7.2, "middle"))
    s.wire((vx, vy), s.pin("F601", 1))
    s.place(sym_switch(), "SW601", "KCD1-101A", vx + 55, vy, ref_at=(0, -4.2, "middle"), val_at=(0, 5.0, "middle"),
            part="I/O 판 전원 스위치", part_at=(0, 7.2, "middle"))
    s.wire(s.pin("F601", 2), s.pin("SW601", 1))
    s.label(vx + 3.5, vy, "+20V_PD", "R")
    s.label(s.pin("F601", 2)[0] + 1, vy, "+20V_F", "R")
    exp_add(e, "+20V_PD", "A601.1", "F601.1")
    exp_add(e, "+20V_F", "F601.2", "SW601.1")
    # 20 V bus
    bx = 185
    s.wire(s.pin("SW601", 2), (bx, vy))
    s.pwr(bx - 5, vy, "+20V")
    exp_add(e, "+20V", "SW601.2")
    s.wire((gx + 3, gy), (gx + 8, gy))
    s.pwr(gx + 8, gy, "GND")
    exp_add(e, "GND", "A601.3")
    # A602 buck
    bk = sym_box("XL4016_module", [(1, "IN+"), None, (2, "IN-")], [(3, "OUT+"), None, (4, "OUT-")], width=30, cls="mod", rows=3)
    s.place(bk, "A602", "XL4016 강압 → 5.1 V", 195, 80, val_at=(0, 23.5), part="XH-M401 (L58) · 가변저항으로 5.10 V 맞춤", part_at=(0, 25.8))
    i1, i2 = s.pin("A602", 1), s.pin("A602", 2)
    s.wire((bx, vy), (bx, i1[1]), i1)
    s.wire(i2, (i2[0] - 7.5, i2[1]))
    s.pwr(i2[0] - 7.5, i2[1], "GND")
    s.text(i2[0] - 30, i2[1] + 7.5, "★ 별 접지점: 강압 IN− 단자", "noteb", size=2.3)
    exp_add(e, "+20V", "A602.1")
    exp_add(e, "GND", "A602.2")
    # 20 V to amp (sheet 7)
    s.wire((bx, vy), (bx + 55, vy))
    s.pwr(bx + 55, vy, "+20V")
    s.text(bx + 58, vy + 0.8, "→ SCH-07 A702 VCC (W602)", "notes", size=2.0)
    o1, o2 = s.pin("A602", 3), s.pin("A602", 4)
    s.wire(o2, (o2[0] + 7.5, o2[1]))
    s.pwr(o2[0] + 7.5, o2[1], "GND")
    exp_add(e, "GND", "A602.4")
    # 5V1 distribution
    s.wire(o1, (o1[0] + 30, o1[1]))
    s.pwr(o1[0] + 12.5, o1[1], "+5V1")
    exp_add(e, "+5V1", "A602.3")
    # P601 MT666 -> Pi, P602 DC plug -> hub
    pl = sym_box("USB_C_Plug_USB2.0", [("A4", "VBUS"), None, ("A1", "GND")], [], width=14, cls="body", rows=3)
    pl2 = sym_box("Barrel_Plug", [("1", "+"), None, ("2", "−")], [], width=14, cls="body", rows=3)
    px0 = o1[0] + 45
    s.place(pl, "P601", "USB-C 수 2선 (MT666)", px0, 55, val_at=(0, 23.5), part="→ Pi 5 USB-C 전원 (C24)", part_at=(0, 25.8))
    s.place(pl2, "P602", "DC 플러그 (허브 어댑터 선)", px0, 95, val_at=(0, 23.5), part="→ 허브 DC 입력 (L17)", part_at=(0, 25.8))
    xa = o1[0] + 30
    for ref in ("P601", "P602"):
        pv, pg = ("A4", "A1") if ref == "P601" else ("1", "2")
        a, b = s.pin(ref, pv), s.pin(ref, pg)
        s.wire((xa, o1[1]), (xa, a[1]), a)
        s.wire(b, (b[0] - 5, b[1]))
        s.pwr(b[0] - 5, b[1], "GND")
        exp_add(e, "+5V1", f"{ref}.{pv}")
        exp_add(e, "GND", f"{ref}.{pg}")
    # loads (blocks, drawing only)
    s.rect(px0 + 30, 50, 44, 22, "mod", "body")
    s.text(px0 + 32, 56, "A603 Raspberry Pi 5 2GB (L01)", "ref", size=2.7)
    s.para(px0 + 32, 61, ["USB-C 전원 입력 (5.1 V)", "EEPROM PSU_MAX_CURRENT=5000", "config.txt usb_max_current_enable=1",
                          "헤더 2·6 → 화면 A605 (아래, R31)"], "notes", size=2.0, lh=2.75)
    s.rect(px0 + 30, 90, 44, 22, "mod", "body")
    s.text(px0 + 32, 96, "A604 NEXTU 710U3 허브 (L17)", "ref", size=2.7)
    s.para(px0 + 32, 101, ["DC 입력 5 V (어댑터 대신 5.1 V)", "업스트림 → Pi 5 USB-A", "다운스트림 8 = O1~O7 + PED"], "notes", size=2.0)
    s.cable((px0 + 19, 57.5), (px0 + 30, 57.5))
    s.cable((px0 + 19, 97.5), (px0 + 30, 97.5))
    s.chg(s.pin("A602", 2)[0] - 15, s.pin("A602", 2)[1] + 1, 5)
    for i, (ref, net) in enumerate((("TP601", "+20V"), ("TP602", "+5V1"), ("TP603", "GND"))):
        tx, ty = 110 + i * 20, 118
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        if net == "GND":
            s.wire((tx, ty), (tx, ty + 2.5)); s.pwr(tx, ty + 2.5, "GND")
        else:
            s.wire((tx, ty), (tx, ty + 2.5), (tx - 5, ty + 2.5)); s.pwr(tx - 5, ty + 2.5, net)
        exp_add(e, net, f"{ref}.1")
    # current budget table (rev C: + R31 screen; D19 peak basis 52 W)
    I = BUDGET_IN
    rows = [["Pi 5 (FluidSynth, USB 장치 포함)", "5.1 V", f"약 {I['pi_a']} A (최대 5 A 한도)", f"{f1(I['pi_w'])} W"],
            ["허브 + RP2040 8개 + 센서 89개", "5.1 V", f"약 {I['hub_a']} A", f"{f1(I['hub_w'])} W"],
            ["USB 동글 (Pi 포트)", "5 V", f"약 {I['dongle_a']} A", f"{f1(I['dongle_w'])} W"],
            ["화면 A605 (Pi 헤더 2번, 밝기 100 %)", f"{DISP['v']:.0f} V", f"약 {B['disp_a']:.2f} A", f"{B['disp_w']:.2f} W"],
            [f"강압 효율 {I['eff'] * 100:.0f} % 손실", "", "", f"{f1(B['loss_new'])} W"],
            ["앰프 평균 (피아노 음악, 최대 음량 상한)", "20 V", f"약 {I['amp_avg_a'][0]}~{I['amp_avg_a'][1]} A",
             f"{I['amp_avg_w'][0]:.0f}~{I['amp_avg_w'][1]:.0f} W"],
            ["합계 (평균)", "20 V 입력", f"약 {f1(B['avg_a'][0])}~{f1(B['avg_a'][1])} A",
             f"약 {B['avg'][0]:.0f}~{B['avg'][1]:.0f} W"],
            [f"순간 최대 (최저음 강타, D19 {I['peak_basis_w']:.0f} W + 화면)", "20 V 입력", f"약 {f1(B['peak_a'])} A", f"약 {f1(B['peak'])} W"],
            [f"{I['supply_w']:.0f} W 전원 여유 (D19)", "", "", f"약 {f1(B['margin'])} W"],
            [f"{I['small_supply_w']:.0f} W 전원: 볼륨 상한 −2 dB (−1 dB면 화면 끔)", "20 V 입력", "",
             f"약 {f1(B['cut2'])} W"]]
    ty_end = s.table(15, 135, ["부하", "전압", "전류", "전력"], rows, [70, 22, 44, 20],
                     title="전원 예산 (R28 · R31 계산, 65 W 충전기 / PD 20 V 3 A 보조배터리)")
    s.chg(174.5, 135 + 4.2 + 3.3 * 4 + 1.8, 16)
    s.para(190, 135, [
        "주",
        "1. A601: VSET 납땜 패드 3쌍을 모두 열어 두면 20 V(기본). HUSB238은 ISET 열림 = 3.25 A를 요구해",
        "    20 V 3 A(60 W) 보조배터리·2포트 사용 충전기는 조건을 못 맞춰 15·12 V, 최악 5 V로 떨어진다(검토 R5).",
        "    처음에 전원마다 무부하로 20 V가 나오는지 잰다. 5 V면 강압·앰프가 켜지지 않는다.",
        "2. F601: 5 A 지연형, A601 출력 + 선에 인라인 홀더. SW601은 퓨즈 뒤 20 V 쪽 (앰프와 강압 모듈을 함께 끔).",
        "3. 20 V 배선은 16 AWG 스피커선(C13). 분기: 스위치 출력 한 곳에서 두 선(앰프, 강압)으로 나눈다.",
        "4. Pi 5에는 P601(USB-C 2선 리드)로 5.1 V만 넣는다. GPIO 5V 핀 급전·동시 급전 금지(D16). 화면은 헤더에서 받아 감(주 9).",
        "5. 허브는 딸린 5 V 어댑터 선을 잘라 플러그 쪽(P602)을 강압 모듈에 물린다. 극성은 멀티미터로 확인.",
        "6. △5 GND는 한 점(★ 강압 IN− 단자)에서 모은다: PD GND·앰프 GND 선이 여기서만 만난다 (검토 R7, 험 방지).",
        "7. 첫 연결 전: 강압 출력을 무부하로 5.10~5.15 V에 맞추고 가변저항을 고정(접착) — 출고값은 20 V까지 나올 수 있다(R6).",
        "    MT666 빨강 = +, 허브 선 중심 = + 를 멀티미터로 확인. Pi 헤더 핀 2–6이 부하 때 5.0 V 이상.",
        "8. 스위치로 끄면 Pi가 갑자기 꺼진다 → 읽기 전용 오버레이 파일 시스템 권장(R13).",
        f"△16 예산: 순간 최대 = D19 {I['peak_basis_w']:.0f} W + 화면 {B['disp_w']:.2f} W ÷ {I['eff']:.1f}. {I['small_supply_w']:.0f} W 전원에서 −1 dB면 약 {f1(B['cut1'])} W(넘침),",
        f"    화면을 끄면 약 {f1(B['cut1_off'])} W → −2 dB(약 {f1(B['cut2'])} W), 또는 −1 dB + 화면 끔.",
    ], size=2.2)
    _display_band(s, e, 180.0)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch06)


# ------------------------------------------------------------------ SCH-07
def sch07():
    s = Sheet("SCH-07", 7, TOTAL, "오디오 (CU)",
              "Pi 5 → USB 동글(DAC) → 왼쪽 볼 헤드폰 잭(노멀 접점) → 앰프 입력 잭 → 약 93 Hz RC → XH-A232 (TPA3110) → XT30 → 스피커 2개. 헤드폰을 꽂으면 앰프 입력이 끊긴다(R15).",
              "CU 오디오", qty="CU × 1", basis="v4 W1+ · R25")
    e = {}
    plug = sym_plug()
    # dongle block with its 3.5 mm jack contacts (T,R,S)
    dg = sym_box("Apple_USB-C_dongle", [], [("T", "L"), ("R", "R"), ("S", "GND")], width=26, cls="mod", rows=3)
    s.place(dg, "A701", "Apple USB-C → 3.5 mm (MW2Q3)", 18, 40, val_at=(0, 23.5), part="USB DAC · 헤드폰 앰프 (L51)", part_at=(0, 25.8))
    s.cable((31, 40), (31, 31), text="USB-C → X701 젠더(IH190) → Pi 5 USB-A (허브 거치지 않음)", at=(18, 28.5), anchor="start")
    s.place(plug, "P701", "W701 플러그", 80, 40, mirror=True, ref_at=(-9, -2.2), val_at=(-9, 19.5))
    s.mate("A701", "P701", at=(64.5, 36.5))
    for nm, net in (("T", "DAC_L"), ("R", "DAC_R"), ("S", "AGND")):
        x, y = s.pin("A701", nm)
        s.wire((x, y), (x + 1, y))
        s.label(x + 1, y, net, "R")
        x, y = s.pin("P701", nm)
        s.wire((x, y), (x + 10, y))
        s.label(x + 10, y, net, "R")
        exp_add(e, net, f"P701.{nm}", f"A701.{nm}")
    s.text(18, 72, "W701: 3.5 mm 스테레오 1.5 m (C14) — 볼 쪽 끝을 잘라 J701에 납땜", "cabt", size=2.0)
    # J701 headphone jack (left cheek)
    s.box(112, 22, 76, 78, "왼쪽 볼 — 헤드폰 잭 (R15)")
    s.place(sym_jack(), "J701", "PJ-313 헤드폰 잭", 150, 35, mirror=True, ref_at=(-16, -2.2), val_at=(-16, 31.5),
            part="L15 ①", part_at=(-16, 33.8))
    for nm, net in (("T", "DAC_L"), ("TN", "HP_TN_L"), ("R", "DAC_R"), ("RN", "HP_RN_R"), ("S", "AGND")):
        x, y = s.pin("J701", nm)
        s.wire((x, y), (x - 5, y))
        s.label(x - 5, y, net, "L")
        exp_add(e, net, f"J701.{nm}")
    s.text(116, 83, "플러그 없음: T–TN, R–RN 닫힘 → 앰프로", "notes", size=2.0)
    s.text(116, 85.8, "헤드폰 꽂음: TN·RN 떨어짐 → 앰프 입력 끊김", "notes", size=2.0)
    s.text(116, 95, "W702 볼 쪽 끝 → J701 TN·RN·S 납땜", "cabt", size=2.0)
    # W702 plug -> J702
    s.place(plug, "P702", "W702 플러그", 215, 40, ref_at=(0, -2.2), val_at=(0, 19.5), part="1.5 m (C14)", part_at=(0, 21.8))
    for nm, net in (("T", "HP_TN_L"), ("R", "HP_RN_R"), ("S", "AGND")):
        x, y = s.pin("P702", nm)
        s.wire((x, y), (x - 7.5, y))
        s.label(x - 7.5, y, net, "L")
        exp_add(e, net, f"P702.{nm}")
    # CU tray
    s.box(236, 22, 160, 118, "CU 트레이 — 앰프 입력 잭 + 저음 차단 RC (D18) + 앰프")
    s.place(sym_jack(), "J702", "PJ-313 앰프 입력 잭", 240, 35, ref_at=(0, -2.2), val_at=(0, 31.5),
            part="L15 ③", part_at=(0, 33.8))
    s.mate("P702", "J702", at=(234.5, 55.0))
    for nm, net in (("T", "HP_TN_L"), ("R", "HP_RN_R")):
        x, y = s.pin("J702", nm)
        s.wire((x, y), (x + 7.5, y))
        s.label(x + 7.5, y, net, "R")
        exp_add(e, net, f"J702.{nm}")
    for nm in ("TN", "RN"):
        s.nc(*s.pin("J702", nm))
    x, y = s.pin("J702", "S")
    s.wire((x, y), (x + 7.5, y))
    s.label(x + 7.5, y, "AGND", "R")
    s.chg(x + 22, y - 0.5, 10)
    exp_add(e, "AGND", "J702.S")
    # HPF lanes
    for (ly, pa, pb, rr, nin, nout) in ((82.5, "C701", "C702", "R701", "HP_TN_L", "AMP_IN_L"),
                                        (112.5, "C703", "C704", "R702", "HP_RN_R", "AMP_IN_R")):
        s.label(250, ly, nin, "R")
        s.place(sym_C(), pa, "1µ", 280, ly, rot=90, ref_at=(0, -3.2, "middle"), val_at=(6.5, -1.2, "start"))
        s.place(sym_C(), pb, "1µ", 280, ly + 7.5, rot=90, ref_at=(0, 5.2, "middle"), val_at=(6.5, 3.2, "start"))
        L1 = min((s.pin(pa, 1), s.pin(pa, 2)), key=lambda q: q[0]); R1 = max((s.pin(pa, 1), s.pin(pa, 2)), key=lambda q: q[0])
        L2 = min((s.pin(pb, 1), s.pin(pb, 2)), key=lambda q: q[0]); R2 = max((s.pin(pb, 1), s.pin(pb, 2)), key=lambda q: q[0])
        s.wire((250, ly), L1)
        s.wire((L1[0] - 5, ly), (L1[0] - 5, L2[1]), L2)
        s.wire(R1, (300, ly))
        s.wire(R2, (R2[0] + 5, R2[1]), (R2[0] + 5, ly))
        s.place(sym_R(), rr, "1k", 300, ly + 7.5, ref_at=(3.2, -0.6), val_at=(3.2, 2.4))
        s.wire(s.pin(rr, 2), (s.pin(rr, 2)[0], s.pin(rr, 2)[1] + 2.5), (s.pin(rr, 2)[0] + 5, s.pin(rr, 2)[1] + 2.5))
        s.label(s.pin(rr, 2)[0] + 5, s.pin(rr, 2)[1] + 2.5, "AGND", "R")
        s.wire((300, ly), (315, ly))
        s.label(315, ly, nout, "R")
        nm = lambda ref, q: "1" if s.pin(ref, 1) == q else "2"
        exp_add(e, nin, f"{pa}.{nm(pa, L1)}", f"{pb}.{nm(pb, L2)}")
        exp_add(e, nout, f"{pa}.{nm(pa, R1)}", f"{pb}.{nm(pb, R2)}", f"{rr}.1")
        exp_add(e, "AGND", f"{rr}.2")
        s.text(252, ly + 17.5, "1 µF ×2 병렬 = 2 µF 직렬, 1 kΩ 병렬", "notes", size=1.9)
    # amp
    amp = sym_box("XH-A232", [("1", "L"), ("2", "G"), ("3", "R"), None, ("4", "VCC"), ("5", "GND")],
                  [("6", "L+"), ("7", "L-"), None, ("8", "R+"), ("9", "R-")], width=24, cls="mod", rows=6)
    ax, ay = 348, 40
    s.place(amp, "A702", "XH-A232 (HW-404)", ax, ay, val_at=(0, 38.5), part="TPA3110 · BTL: 스피커 − 선을 GND에 묶지 않음", part_at=(-12, 40.8))
    for pin, net in (("1", "AMP_IN_L"), ("3", "AMP_IN_R")):
        x, y = s.pin("A702", pin)
        s.wire((x, y), (x - 7.5, y))
        s.label(x - 7.5, y, net, "L")
        exp_add(e, net, f"A702.{pin}")
    x, y = s.pin("A702", "2"); s.wire((x, y), (x - 7.5, y)); s.label(x - 7.5, y, "AGND", "L"); exp_add(e, "AGND", "A702.2")
    s.chg(x - 27, y - 1.5, 10)
    x, y = s.pin("A702", "4"); s.wire((x, y), (x - 10, y)); s.pwr(x - 10, y, "+20V"); exp_add(e, "+20V", "A702.4")
    x, y = s.pin("A702", "5"); s.wire((x, y), (x - 3.5, y)); s.pwr(x - 3.5, y, "GND"); exp_add(e, "GND", "A702.5")
    for pin, net in (("6", "SPK_L_P"), ("7", "SPK_L_N"), ("8", "SPK_R_P"), ("9", "SPK_R_N")):
        x, y = s.pin("A702", pin)
        s.wire((x, y), (x + 5, y))
        s.label(x + 5, y, net, "R")
        exp_add(e, net, f"A702.{pin}")
    s.text(318, 64.5, "+20V: SCH-06", "notes", size=1.9)
    # speakers
    s.box(14, 150, 216, 80, "스피커 파트 연결 (R26: XT30 꽂았다 뺌, D13: 직렬 콘덴서 없음)")
    for i, (side, pnet, nnet, xm, xf_, ls) in enumerate((("L", "SPK_L_P", "SPK_L_N", "X703", "X704", "LS701"),
                                                          ("R", "SPK_R_P", "SPK_R_N", "X705", "X706", "LS702"))):
        y0 = 165 + i * 32
        s.place(sym_conn("XT30U-M", 2, side="L", width=6, rev=True), xm, "XT30U-M", 70, y0, ref_at=(0, -2.2), val_at=(-16, 14.5))
        s.place(sym_conn("XT30U-F", 2, side="R", width=6, rev=True), xf_, "XT30U-F", 77.5, y0, ref_at=(0, -2.2), val_at=(1, 14.5))
        s.mate(xm, xf_, at=(76.3, y0 + 12.3))
        s.text(72.2, y0 + 3.3, "+", "pinnameh", size=2.3)
        s.text(72.2, y0 + 8.3, "−", "pinnameh", size=2.3)
        for k, net in ((2, pnet), (1, nnet)):
            x, y = s.pin(xm, k)
            s.wire((x, y), (x - 20, y))
            s.label(x - 20, y, net, "L")
            exp_add(e, net, f"{xm}.{k}", f"{xf_}.{k}")
        s.place(sym_speaker(), ls, f"CW-100B25 8 Ω ({'왼쪽' if side == 'L' else '오른쪽'})", 125, y0 + 5, ref_at=(0, -9.5), val_at=(10, 3.5))
        for k, lsp in ((2, "1"), (1, "2")):
            x, y = s.pin(xf_, k)
            tx, ty = s.pin(ls, lsp)
            s.wire((x, y), (tx, ty))
            s.label(x + 3, y, pnet if lsp == "1" else nnet, "R")
            exp_add(e, pnet if lsp == "1" else nnet, f"{ls}.{lsp}")
        s.text(20, y0 + 19.5, f"W70{3+2*i}: 앰프 → 통로 → XT30 약 0.6 m · W70{4+2*i}: 스피커 파트 안 0.3 m (16 AWG)", "cabt", size=2.0)
    s.para(240, 150, [
        "주",
        "1. 동글 A701은 젠더 X701로 Pi 5 USB-A에 직결(허브 경유 금지). ALSA hw:CARD=<이름>,DEV=0, 48 kHz 전용(D7).",
        "2. J701(왼쪽 볼): 동글 신호가 T·R 스프링으로, TN·RN 노멀이 앰프로. 헤드폰을 꽂으면 노멀이 떨어진다(R15).",
        "    ‘PJ-313’ 이름만으로 노멀 접점·핀 번호가 보장되지 않는다 → 도착 즉시 통전 검사(플러그 없음: T–TN, R–RN 닫힘).",
        "3. HPF: 1 µF ×2 병렬(2 µF) 직렬 + 1 kΩ 병렬. 앰프(36 dB, 입력 9 kΩ)와 겹쳐 실제 fc ≈ 93 Hz.",
        "    80 Hz가 꼭 필요하면 1 kΩ → 1.2 kΩ (구매). △10 AGND: 잭 슬리브·1 kΩ는 앰프 IN G 단자로만 모은다.",
        "4. XH-A232는 36 dB 출고 → 입력 약 0.2 Vrms면 최대 출력. 동글은 0.5~1 Vrms라 소프트웨어 상한 필수",
        "    (ALSA Headphone·FluidSynth synth.gain 상한 + synth.limiter). 스피커 25 W 정격 보호(D18).",
        "5. XT30: 납작한 면 = +, 모따기 면 = − (KiCad 패드 1 = −, 2 = +). 좌우 같은 방향으로 납땜해 위상을 맞춘다.",
        "6. BTL: L−·R−를 GND나 서로에 묶지 않는다. 스피커선은 쌍마다 꼬고 리본·EXT 선에서 30 mm 이상(D14).",
        "7. 스피커 Re를 잰다: 6~7 Ω = 8 Ω 유닛, 3~3.5 Ω면 4 Ω 판매분(출력·발열 재검토).",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch07)


# ------------------------------------------------------------------ board placement helpers
def grid(i0, n, x0=0.63, p=2.54):
    return [x0 + p * (i0 + k) for k in range(n)]


# board fixing (W1 r4.5): 4 hanging Ø6 bosses of the frame on the board top at these points; 2 × M3×6 from below
# (ISO 7380 head Ø5.7 × 1.65 under the board), 2 locating pins. Heads keep 1.3 to the balance-rail rear face y144.5
# and the shelf ribs (front face y196.8, x49.4~50.6 / x115.4~116.6); v3 P114 (49.75,148)… gave 0.75 / 1.05.
MB = dict(x0=47.25, x1=117.25, y0=145.5, y1=195.5,
          standoffs=[(50.0, 149.0, "M3×6 밑에서"), (114.5, 149.0, "위치 핀"), (50.0, 192.5, "위치 핀"), (114.5, 192.5, "M3×6 밑에서")],
          slot=(81.92, 84.72, 145.5, 172.0), keep=(81.22, 85.42, 145.5, 173.2),
          fin=(82.52, 84.12, 148.6, 170.7), keel=(82.52, 84.12, 144.5, 148.6),     # W1 r4.5: 1.6-wide foot + keel (P12), slot gap 0.60
          boss_rects=[(47.0, 53.0, 144.5, 152.0), (111.5, 117.5, 144.5, 152.0), (47.0, 53.0, 189.5, 196.8), (111.5, 117.5, 189.5, 196.8)],
          boss_keep=[(47.25, 54.3, 145.5, 153.3), (110.2, 117.25, 145.5, 153.3), (47.25, 54.3, 188.2, 195.5), (110.2, 117.25, 188.2, 195.5)],
          floor_cut=(46.25, 118.25, 144.5, 196.5), rcpt_cut=(78.53, 89.47, 196.5, 197.8))   # W1 r4.5: floor opening under the board
# RP2040-Zero left edge. Waveshare dimension drawing: USB-C receptacle 4.67 from the right edge (8.94 wide), i.e. 0.14 left
# of centre -> the Zero sits at x75.14 so that the receptacle / plug is centred on the W1 r4.3 shelf slot (x84.0, 1.30 each side)
ZX = 75.14
USB_RX = (ZX + 18.0 - 4.67 - 8.94, ZX + 18.0 - 4.67)   # receptacle x (79.53, 88.47)
USB_RY = (189.5, 196.8)                               # receptacle y: overhangs the Zero / board edge by about 1.3 (1.0~1.5)
ZERO_ORIGIN = (ZX, 195.5)        # module-local (0,0) = top-left with USB edge at y=195.5, local +y -> board -y
# every MB hole sits on the RP2040-Zero pin lattice: x = LAT_X + 2.54 i, y = 173.59 + 2.54 j
LAT_X, LAT_Y = round(ZX + 1.38, 2), 173.59


def lat(i):
    return round(LAT_X + 2.54 * i, 2)


MUX_ORIGIN = (round(lat(-8) - 1.27, 2), 152.0)   # module corner = channel-row edge, C0 end (front); channel row lat(-8), control lat(-2)
RIB_X0, RIB_Y = lat(-6), (148.19, 150.73)     # ribbon 2x8 block: odd row front, even row back
EXT_X0, EXT_Y = lat(7), 193.91                # EXT 1x6 pads along x (rear, next to the USB tunnel)
JP_POS = {"JP301": (lat(8), 181.21), "JP302": (lat(8), 178.67), "JP303": (lat(8), 176.13), "JP304": (lat(8), 173.59)}
R_EXT = {f"R{300+n}": (lat(10), 153.27 + 5.08 * (n - 1)) for n in range(1, 5)}   # 100k pull-downs, lying along +x, 7.62 pitch
TP_POS = {"TP301": (lat(8), 188.83), "TP302": (lat(9), 188.83), "TP303": (lat(10), 188.83)}
RIB_C = RIB_X0 + 3.5 * 2.54                   # J301 centre (the ribbon itself runs centred on SB J201, x70.48)


def f2(v):
    return f"{v:.2f}"


MBX = dict(mux=f"x{f2(MUX_ORIGIN[0])}~{f2(MUX_ORIGIN[0] + 17.78)} × y152.0~192.64",
           rib=f"x{f2(RIB_X0)}~{f2(RIB_X0 + 7 * 2.54)} × y148.19/150.73",
           ext=f"x{f2(EXT_X0)}~{f2(EXT_X0 + 5 * 2.54)} × y193.91",
           zero=f"x{f2(ZX)}~{f2(ZX + 18)} × y172.0~195.5",
           usb=f"x{f2(USB_RX[0])}~{f2(USB_RX[1])} × y{USB_RY[0]}~{USB_RY[1]}",
           rext=f"x{f2(lat(10))}→{f2(lat(10) + 7.62)} × y153.27~168.51",
           jp=f"x{f2(lat(8))}/{f2(lat(9))} × y173.59~181.21",
           tp=f"x{f2(lat(8))}~{f2(lat(10))} × y188.83",
           so="(50.0,149.0)(114.5,149.0)(50.0,192.5)(114.5,192.5)")


def zero_hole(n):
    lx, ly = P.RP2040_HOLE[n]
    return ZERO_ORIGIN[0] + lx, ZERO_ORIGIN[1] - ly


def mux_hole(name):
    n = P.mux_pin(name)
    if n <= 16:
        u, w = 1.27 + 2.54 * (n - 1), 1.27
    else:
        u, w = 11.43 + 2.54 * (n - 17), 16.51
    return MUX_ORIGIN[0] + w, MUX_ORIGIN[1] + u


def brd01():
    s = Sheet("BRD-01", 8, TOTAL, "제어 기판 배치 (MB · 위에서 봄)",
              "5×7 cm 만능기판 위 부품 자리와 구멍 좌표(모듈 좌표 mm). W1 r4.3~r4.5의 앞 홈·금지 구역·높이 구역·바닥 구멍·매단 보스를 지킨 배치. 배선은 netlist/wiring_MB.csv의 점 대 점 목록을 따른다.",
              "MB", qty="MB × 7", basis="v4 W1+ r4.5 P23")
    S = 3.0
    ox, oy = 28, 30

    def X(x):
        return ox + (x - MB["x0"]) * S

    def Y(y):
        return oy + (MB["y1"] - y) * S
    o = s.out["body"]
    # board
    o.append(f'<rect x="{X(MB["x0"]):.2f}" y="{Y(MB["y1"]):.2f}" width="{70*S:.2f}" height="{50*S:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    # perfboard hole grid (approximate, 2.54)
    for gx in [lat(-11 + i) for i in range(27)]:
        for gy in [148.19 + 2.54 * j for j in range(19)]:
            o.append(f'<circle cx="{X(gx):.2f}" cy="{Y(gy):.2f}" r=".35" fill="#b9cdb6"/>')
    # keep-out + slot
    kx0, kx1, ky0, ky1 = MB["keep"]
    o.append(f'<rect x="{X(kx0):.2f}" y="{Y(ky1):.2f}" width="{(kx1-kx0)*S:.2f}" height="{(ky1-ky0)*S:.2f}" fill="#fde2d8" stroke="#c2410c" stroke-width=".3" stroke-dasharray="1.2 .8"/>')
    sx0, sx1, sy0, sy1 = MB["slot"]
    o.append(f'<rect x="{X(sx0):.2f}" y="{Y(sy1):.2f}" width="{(sx1-sx0)*S:.2f}" height="{(sy1-sy0)*S:.2f}" fill="#fff" stroke="#c2410c" stroke-width=".45"/>')
    fx0, fx1, fy0, fy1 = MB["fin"]
    o.append(f'<rect x="{X(fx0):.2f}" y="{Y(fy1):.2f}" width="{(fx1-fx0)*S:.2f}" height="{(fy1-fy0)*S:.2f}" fill="#c9d0da" stroke="#6b7690" stroke-width=".3"/>')
    kx0_, kx1_, ky0_, ky1_ = MB["keel"]
    o.append(f'<rect x="{X(kx0_):.2f}" y="{Y(ky1_):.2f}" width="{(kx1_-kx0_)*S:.2f}" height="{(ky1_-ky0_)*S:.2f}" fill="#9aa6b8" stroke="#6b7690" stroke-width=".3"/>')
    # W1 r4.5 floor opening under the board (the board goes in from below)
    cx0, cx1, cy0, cy1 = MB["floor_cut"]
    rx0, rx1, _, ry1 = MB["rcpt_cut"]
    pts = [(cx0, cy0), (cx1, cy0), (cx1, cy1), (rx1, cy1), (rx1, ry1), (rx0, ry1), (rx0, cy1), (cx0, cy1)]
    o.append('<polygon points="' + " ".join(f"{X(a):.2f},{Y(b):.2f}" for a, b in pts) + '" fill="none" stroke="#6b7690" stroke-width=".3" stroke-dasharray="2 1"/>')
    s.text(X(47.25), Y(145.5) + 27.5, "W1 홈 x81.92~84.72 × y145.5~172.0 (따냄) — F|F# 핀 발 y148.6~170.7 + 킬 y144.5~148.6(레일 뒷면에 붙음)이 지나감(회색)", "notes", size=2.1)
    s.text(X(47.25), Y(145.5) + 36.2, "점선 테두리 = W1 r4.5 바닥 구멍 x46.25~118.25 × y144.5~196.5 (리셉터클 뒤 y197.8까지) — 기판을 밑에서 넣는다", "notes", size=2.1)
    s.text(X(47.25), Y(145.5) + 30.4, "주황 = 금지 x81.22~85.42 × y145.5~173.2 (W1 r4.3): 부품·배선·패드 없음", "notes", size=2.1)
    s.text(X(47.25), Y(145.5) + 33.3, "(y172.0~173.2에는 제로 PCB(z11.9 위)만 걸침 — 핀·패드·배선 없음)", "notes", size=2.1)
    # W1 r4.5 boss brackets (hung from the rail rear face / shelf rib) + the component-free corners around them
    for (a0, a1, b0, b1) in MB["boss_keep"]:
        o.append(f'<rect x="{X(a0):.2f}" y="{Y(b1):.2f}" width="{(a1-a0)*S:.2f}" height="{(b1-b0)*S:.2f}" fill="#fde2d8" fill-opacity=".45" stroke="#c2410c" stroke-width=".25" stroke-dasharray="1 .7"/>')
    for (a0, a1, b0, b1) in MB["boss_rects"]:
        o.append(f'<rect x="{X(a0):.2f}" y="{Y(b1):.2f}" width="{(a1-a0)*S:.2f}" height="{(b1-b0)*S:.2f}" fill="#c9d0da" fill-opacity=".35" stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.2 .7"/>')
    # standoffs
    s.chg(X(50.0), Y(149.0) - 12.0, 14)
    for (x, y, t) in MB["standoffs"]:
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{3.0*S:.2f}" fill="#c9d0da" fill-opacity=".25" stroke="#6b7690" stroke-width=".35" stroke-dasharray="1.2 .7"/>')
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{(1.6 if "M3" in t else 1.5)*S:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".35"/>')
        s.text(X(x), (Y(195.5) - 4.2) if y > 170 else (Y(145.5) + 6.2), t, "notes", "middle", size=2.0)
    # RP2040-Zero
    zx0, zy0 = ZERO_ORIGIN
    o.append(f'<rect x="{X(zx0):.2f}" y="{Y(zy0):.2f}" width="{18*S:.2f}" height="{23.5*S:.2f}" rx="3" fill="#1f2a44" fill-opacity=".10" stroke="#1f2a44" stroke-width=".45"/>')
    o.append(f'<rect x="{X(USB_RX[0]):.2f}" y="{Y(USB_RY[1]):.2f}" width="{(USB_RX[1]-USB_RX[0])*S:.2f}" height="{(USB_RY[1]-USB_RY[0])*S:.2f}" fill="#c9d0da" stroke="#1f2a44" stroke-width=".3"/>')
    s.text(X(zx0 + 9), Y(zy0 - 3.2), "USB-C", "notes", "middle", size=2.1)
    s.chg(X(USB_RX[1]) + 4.5, Y(USB_RY[1]) + 3.0, 15)
    s.text(X(zx0 + 9), Y(zy0 - 12), "A301 RP2040-Zero", "ref", "middle", size=2.7)
    s.text(X(zx0 + 9), Y(zy0 - 14.8), "18 × 23.5, 핀 헤더로", "notes", "middle", size=2.0)
    for n, nm in P.RP2040_ZERO:
        x, y = zero_hole(n)
        used = nm in ("3V3", "GND", "GP26", "GP2", "GP3", "GP4", "GP5", "GP6", "GP7", "GP8", "GP14")
        fill = "#c2410c" if used else "#fff"
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{0.55*S:.2f}" fill="{fill}" stroke="#1f2a44" stroke-width=".3"/>')
        if n <= 9:
            s.text(X(x) - 2.4, Y(y) + 0.8, f"{nm}", "pinname", "end", size=2.0, check=False)
        elif n <= 18:
            s.text(X(x) + 2.4, Y(y) + 0.8, f"{nm}", "pinname", "start", size=2.0, check=False)
        else:
            s.text(X(x), Y(y) + 4.4, nm.replace("GP", ""), "pinname", "middle", size=1.8, check=False)
    # mux module (rotated: long axis along y)
    mx0, my0 = MUX_ORIGIN
    o.append(f'<rect x="{X(mx0):.2f}" y="{Y(my0+40.64):.2f}" width="{17.78*S:.2f}" height="{40.64*S:.2f}" rx="1" fill="#1f5fbf" fill-opacity=".10" stroke="#1f5fbf" stroke-width=".45"/>')
    for (u, w) in ((2.54, 15.24), (38.10, 15.24)):
        o.append(f'<circle cx="{X(mx0+w):.2f}" cy="{Y(my0+u):.2f}" r="{1.65*S:.2f}" fill="none" stroke="#1f5fbf" stroke-width=".3"/>')
    for nm in [f"C{i}" for i in range(16)] + ["GND", "VCC", "EN", "S0", "S1", "S2", "S3", "SIG"]:
        x, y = mux_hole(nm)
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{0.55*S:.2f}" fill="#c2410c" stroke="#1f2a44" stroke-width=".3"/>')
        if nm.startswith("C"):
            s.text(X(x) + 2.3, Y(y) + 0.8, nm, "pinname", "start", size=1.9, check=False)
        else:
            s.text(X(x) - 2.3, Y(y) + 0.8, nm, "pinname", "end", size=1.9, check=False)
    s.text(X(mx0 + 8.9), Y(my0 + 20), "A302", "ref", "middle", size=2.7)
    s.text(X(mx0 + 8.9), Y(my0 + 20) + 3, "4067 모듈", "notes", "middle", size=2.0)
    s.text(X(mx0 + 8.9), Y(my0 + 20) + 5.6, "40.64 × 17.78", "notes", "middle", size=2.0)
    # ribbon 2x8 block
    for i in range(16):
        col, row = i // 2, i % 2
        x, y = RIB_X0 + 2.54 * col, RIB_Y[row]
        o.append(f'<rect x="{X(x)-0.9*S/1.2:.2f}" y="{Y(y)-0.9*S/1.2:.2f}" width="{1.5*S:.2f}" height="{1.5*S:.2f}" fill="#fff" stroke="#8a5a00" stroke-width=".35"/>')
        s.text(X(x), Y(y) + (5.0 if row == 0 else -2.6), str(i + 1), "pinnum", "middle", size=1.9, check=False)
    s.text(X(RIB_X0) - 2, Y(145.5) + 6.2, "J301 리본 2×8 (홀수 = 앞줄, 아랫면 납땜)", "cabt", size=2.1)
    # EXT protection resistors (1/4 W lying, 7.62 pitch)
    for ref, (x, y) in R_EXT.items():
        o.append(f'<rect x="{X(x)+1.5:.2f}" y="{Y(y)-2.4:.2f}" width="{7.62*S-3:.2f}" height="4.8" rx="1" fill="#f3e3c3" stroke="#8a5a00" stroke-width=".3"/>')
        for xx in (x, x + 7.62):
            o.append(f'<circle cx="{X(xx):.2f}" cy="{Y(y):.2f}" r="{0.55*S:.2f}" fill="#c2410c" stroke="#1f2a44" stroke-width=".3"/>')
        n = int(ref[1:]) - 300
        s.text(X(x) - 2.6, Y(y) + 0.8, f"{ref} 100k EXT{n}", "pinname", "end", size=1.8, check=False)
    s.text(X(lat(10)) - 2, Y(171.0), "R301~R304: O1은 1~3, O7은 1만", "notes", size=1.9)
    # C301 on the bottom across mux GND/VCC header pins
    gx_, gy_ = mux_hole("GND")
    o.append(f'<rect x="{X(gx_)-1.4:.2f}" y="{Y(gy_+2.54)-0.6:.2f}" width="2.8" height="{2.54*S+1.2:.2f}" fill="none" stroke="#b86e00" stroke-width=".4" stroke-dasharray=".9 .5"/>')
    s.text(X(gx_) - 2.4, Y(gy_ + 1.27) + 0.8, "C301 (아랫면)", "notes", "end", size=1.8)
    for ref, (x, y) in TP_POS.items():
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{0.75*S:.2f}" fill="#fff" stroke="#1f5fbf" stroke-width=".5"/>')
    s.text(X(lat(8)) - 2.5, Y(188.83) - 3.2, "TP301 3V3 · TP302 GND · TP303 SIG", "pinname", size=1.8, check=False)
    # EXT pads
    for i in range(6):
        x = EXT_X0 + 2.54 * i
        o.append(f'<rect x="{X(x)-1.9:.2f}" y="{Y(EXT_Y)-1.9:.2f}" width="3.8" height="3.8" fill="#fff" stroke="#8a5a00" stroke-width=".35"/>')
        s.text(X(x), Y(EXT_Y) - 3.0, str(i + 1), "pinnum", "middle", size=1.9, check=False)
    s.text(X(EXT_X0 + 6.35), Y(EXT_Y) + 7.0, "J302 EXT 1×6 (1 GND … 6 3V3)", "cabt", "middle", size=2.0)
    # jumpers
    for ref, (x, y) in JP_POS.items():
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{0.55*S:.2f}" fill="#c2410c" stroke="#1f2a44" stroke-width=".3"/>')
        o.append(f'<circle cx="{X(x+2.54):.2f}" cy="{Y(y):.2f}" r="{0.55*S:.2f}" fill="#1d2433" stroke="#1f2a44" stroke-width=".3"/>')
        s.text(X(x + 2.54) + 2.6, Y(y) + 0.8, ref + {"JP301": " GP6", "JP302": " GP7", "JP303": " GP8", "JP304": " GP14 (PED만)"}[ref], "pinname", "start", size=1.9, check=False)
    s.text(X(lat(8)) - 2, Y(183.75), "ID 점퍼: 두 구멍 납땜 브리지 (검정 = GND 쪽)", "notes", size=1.9)
    # axes / dimensions
    for x in (47.25, RIB_X0, ZX, 81.22, 85.42, ZX + 18, 117.25):
        s.line(X(x), Y(145.5) + 8, X(x), Y(145.5) + 13, "bodyl", "text")
        s.text(X(x), Y(145.5) + 16, f"x{x:g}", "tblm", "middle", size=1.8, check=False)
    for y in (145.5, 148.6, 170.7, 173.2, 193.91, 195.5):
        s.line(X(117.25) + 2, Y(y), X(117.25) + 5, Y(y), "bodyl", "text")
        s.text(X(117.25) + 6, Y(y) + 0.7, f"y{y:g}", "tblm", size=1.8, check=False)
    s.text(X(64), Y(195.5) - 4.5, "뒤 (+y, USB 쪽)", "notes", size=2.1)
    s.text(X(47.25), Y(145.5) + 22, "앞 (연주자 쪽) · 리본이 앞에서 들어온다", "notes", size=2.1)
    # placement table
    rows = [["A301 RP2040-Zero", MBX["zero"], "USB-C +y", "좌·우 열 18핀 헤더(몰드 뺌), 아래 줄 없음"],
            ["USB-C 리셉터클", MBX["usb"], "가운데 x84.00", "W1 선반 홈 x76.45~91.55 가운데"],
            ["A302 4067 모듈", MBX["mux"], "C0 앞 · C15 뒤", f"채널 줄 x{f2(lat(-8))} · 제어 줄 x{f2(lat(-2))}"],
            ["J301 리본 2×8", MBX["rib"], "1번 = 앞줄 왼쪽", "아랫면 납땜 · 리본 차선 x59~82"],
            ["R301~R304", MBX["rext"], "누워서, 5.08 간격", "EXT 100k 풀다운"],
            ["JP301~JP304", MBX["jp"], "왼쪽 = 신호", "ID0~2 · PED(열림)"],
            ["TP301~303", MBX["tp"], "", "3V3 · GND · SIG"],
            ["J302 EXT 1×6", MBX["ext"], "1 = 왼쪽", "O1·O7만 연장선(아랫면)"],
            ["고정 4 (매단 보스)", MBX["so"], "", "M3×6 밑에서 2 · 위치 핀 2"]]
    s.table(262, 30, ["부품", "자리 (모듈 좌표)", "방향", "메모"], rows, [26, 56, 22, 44], title="배치표 (모든 구멍 = 제로 핀 격자)")
    s.para(262, 74, [
        "주",
        "1. 좌표 = 모듈 좌표(mm), 기판 5×7 cm. 모든 부품 구멍은 RP2040-Zero 핀 격자",
        f"    x = {f2(LAT_X)} + 2.54·i, y = 173.59 + 2.54·j 위 — 만능기판을 이 격자에 맞춰 자른다.",
        f"    △15 제로 왼쪽 모서리 x{f2(ZX)}: Waveshare 치수도에서 USB-C가 오른쪽 모서리에서 4.67(가운데보다 0.14 왼쪽)이라",
        "    제로를 +0.14 옮겨 리셉터클·플러그 가운데를 W1 선반 홈 가운데 x84.00에 맞춘다(양옆 1.30 그대로).",
        "2. W1 r4.3 금지 구역(주황, x81.22~85.42 × y≤173.2)과 홈. 제로 기판 앞 가장자리 y172.0은",
        "    F|F# 핀 발 뒤끝 y170.7과 1.3 mm — 제로를 −y로 옮기지 않는다. 금지 구역의 y172.0~173.2에는",
        "    제로 PCB(z11.9 위)만 걸친다: 그 안에 헤더 핀·패드·배선 없음(첫 핀 줄 y173.59, 아래 줄 GP9~13은 헤더 없음).",
        "3. 제로는 밑면에 칩·수정·LDO가 있어 평평하게 안 붙는다 → 핀 헤더(몰드 뺌)로 밑면 부품 위(캡톤)에",
        f"    얹는다: PCB z11.9~12.9, 윗면 부품 ≤ z16.3. USB-C 리셉터클 {MBX['usb']} z12.9~16.1(중심 z14.5),",
        "    제로 가장자리 밖으로 약 1.3(1.0~1.5, 실물로 확인) 나온다 → 플러그 면 y약 196.8, 몰드 끝 y약 221.8.",
        "    W1 r4.3은 뒤 선반에 플러그 위 홈(x76.45~91.55, 선반 밑면 z18.05)을 내 플러그(z10.7~18.3)와 1.3 mm.",
        "    헤더 핀 끝: 제로 윗면 위로 나온 끝도 z16.3 이하(y194.5~195.5 띠만 z16.7), 기판 밑 끝은 2 mm 이하로 자른다.",
        "    부품 높이: y145.8~194.5 ≤ z20, 뒤 띠 y194.5~195.5 ≤ z16.7. W1 r4.5는 기판 밑 바닥을 뚫었다(점선: x46.25~118.25 ×",
        "    y144.5~196.5, 리셉터클 뒤 x78.53~89.47은 y197.8까지). 아랫면: 헤더 핀 끝 ≤ 2 mm, C301·배선, 나사 머리 1.65.",
        "4. 빨간 원 = 배선 연결점, 빈 원 = 안 씀. 제로 아래 줄(GP9~13)은 헤더 없음.",
        "5. 배선: 기판 아랫면, 피복 단선. 금지 구역(y≤173.2)을 가로지르지 않도록 제로 밑(y≥174.86, 핀 줄 사이",
        "    반 칸)으로 지나간다. 목록: netlist/wiring_MB.csv.",
        "6. O1·O7 EXT 연장선(W403·W413): J302 아랫면에서 납땜, 기판 밑(z5~9)으로 x≤91까지, USB 플러그 밑(z5~10.7)으로",
        "    뒷벽 개구(x74~94 z5~21)를 지나 뒤 케이블 통로로 (W1 r4.3 경로).",
        "7. J301도 아랫면에서 납땜: 리본은 기판 밑(z5~9)으로 평평하게 앞 모서리 y145.5를 지나 밸런스 레일 밑 차선",
        f"    (x59~82, z5~10)으로 — 기판 위에서 접지 않는다. 리본은 차선 안에서 SB J201과 같은 중심 x70.48로 곧게 두고,",
        f"    J301 쪽 끝 약 6 mm만 가닥을 갈라 {70.48 - RIB_C:.2f} 비껴 꽂는다(J301 중심 x{f2(RIB_C)}) → 차선 여유 1.32 / 1.36 그대로.",
        "    회로 쪽 최소: 리본 한 겹(두께 약 0.9) → 차선 높이 ≥ 2.5, 폭 ≥ 20.32 + 2 × 1.3. W1 단계 0 시험 21(첫 모듈 정하중) 뒤 차선이 바뀌면 다시 정한다.",
        "8. △14 기판 고정(W1 r4.5): 모듈을 뒤집어 기판을 바닥 구멍으로 곧게 올려 넣는다(넣는 길 최소 틈 0.60).",
        "    받침 = 프레임에 매단 Ø6 보스 4개(점선 원, 밑면 z10.6 = 기판 윗면; 앞 2개는 밸런스 레일 뒷면, 뒤 2개는 리브·선반에 붙음).",
        "    나사 2곳 (50.0,149.0)·(114.5,192.5): M3×6을 밑에서 기판 Ø3.2 구멍 → 보스로. 구매 목록 L35 버튼헤드(ISO 7380)",
        "    머리 Ø5.7 × 1.65가 기판 밑 z7.35~9.0에(W1 외곽 Ø5.7 × 3.0): 레일 1.65, 리브 1.54(축 1.45), 기판 모서리 밖 0.10(바닥 구멍 안;",
        "    DIN 912 Ø5.5면 기판 안). 보스 Ø2.5 막힌 구멍 z15.4까지 직접 탭.",
        "    위치 핀 2곳 (114.5,149.0)·(50.0,192.5): Ø2.8 핀이 기판 Ø3.0 구멍으로(놀음 0.10).",
        "    보스 받침(6 × 7.5 / 6 × 7.3, 밑면 z10.6)과 둘레 1.3(주황 모서리 x≤54.3 · x≥110.2)에는 부품 없음:",
        "    4067 ↔ 받침 1.93, R301 리드 ↔ 받침 모서리 2.34.",
        "    J301 리본·J302 리드는 기판을 넣기 전에 아랫면에서 납땜한다(W1 DESIGN 10장 1단계 — 넣은 뒤에는 인두가 PETG 리브·킬 2 mm 옆).",
        "9. 건반을 뺀 칸의 레버가 떨어지는 곳(W1 r4.5): D#·G# = 매단 보스, E·F = 4067 모듈 위(13.25°), F#·G = 기판 윗면,",
        "    O1·O7의 G = R301 위(0.40 N) → R301은 기판에 붙여 눕히고 리드를 짧게 납땜한다.",
    ], size=2.1)
    s.frame()
    s.expected = {}
    return s


SB_X1 = 162.6   # SB right edge: 0.3 short of the bar end x162.9, 0.4 from the W1 r4.5 ledge post x163.0


# end-part sensor boards (EL, ER): same 6-row 15.24 stripe as the SB, inside the W1 r4.2 end-part sensor bars
END_BOARDS = {
    "EL": dict(x1=46.5, bar=(0.5, 46.5), low=(19.927, 33.927),
               keys=[("U401", "A0", 10.287, "C401", "R401"), ("U402", "A#0", 26.927, "C402", "R402"), ("U403", "B0", 40.141, "C403", "R403")],
               bulk="C404", jref="J401", jx=[18.41, 20.95, 23.49, 26.03, 28.57], jnames=["GND", "EL_A0", "EL_AS0", "EL_B0", "+3V3_EL"],
               gap=(15.0, 38.0)),
    "ER": dict(x1=23.0, bar=(0.5, 23.0), low=None,
               keys=[("U411", "C8", 11.75, "C411", "R411")],
               bulk="C412", jref="J411", jx=[8.25, 10.79, 13.33], jnames=["GND", "ER_C8", "+3V3_ER"],
               gap=(6.0, 16.0)),
}


def end_col(xk):
    return round(min(0.63 + 2.54 * i for i in range(1, 70) if 0.63 + 2.54 * i >= xk + 3.0), 2)


def _end_plans(s):
    """BRD-02 insets: EL and ER placement (end-part local x, module y)."""
    o = s.out["body"]
    S = 2.4
    rows_tab = []
    for tag, ox in (("EL", 22), ("ER", 158)):
        B = END_BOARDS[tag]
        oy = 180

        def X(x, ox=ox):
            return ox + x * S

        def Y(y, oy=oy):
            return oy + (77.5 - y) * S
        s.text(X(0), oy - 10.0, f"{tag} — {'왼쪽' if tag == 'EL' else '오른쪽'} 끝 부속 x1.0~{B['x1']:g}"
               + ("" if tag == "EL" else " (로컬, x0 = O7 이음)"), "noteb", size=2.4)
        # sensor bar outline (dashed) + low section
        bx0, bx1 = B["bar"]
        o.append(f'<rect x="{X(bx0):.2f}" y="{Y(77.5):.2f}" width="{(bx1-bx0)*S:.2f}" height="{18.5*S:.2f}" fill="none" stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.2 .8"/>')
        if B["low"]:
            lx0, lx1 = B["low"]
            o.append(f'<rect x="{X(lx0):.2f}" y="{Y(77.5):.2f}" width="{(lx1-lx0)*S:.2f}" height="{18.5*S:.2f}" fill="#6b7690" fill-opacity=".06" stroke="none"/>')
        # rear-rib gap needed under the lead pads (W1)
        gx0, gx1 = B["gap"]
        o.append(f'<rect x="{X(gx0):.2f}" y="{Y(75.5):.2f}" width="{(gx1-gx0)*S:.2f}" height="{2.3*S:.2f}" fill="#fde2d8" stroke="#c2410c" stroke-width=".3" stroke-dasharray="1 .6"/>')
        # board
        o.append(f'<rect x="{X(1.0):.2f}" y="{Y(75.89):.2f}" width="{(B["x1"]-1.0)*S:.2f}" height="{15.24*S:.2f}" fill="#eaf4e8" fill-opacity=".85" stroke="#2d6a3e" stroke-width=".5"/>')
        cols = [0.63 + 2.54 * i for i in range(1, 20) if 1.0 < 0.63 + 2.54 * i < B["x1"]]
        for y in (61.92, 64.46, 67.00, 69.54, 72.08, 74.62):
            for x in cols:
                o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".45" fill="#b9cdb6"/>')
        last = max(end_col(k[2]) for k in B["keys"])
        o.append(f'<line x1="{X(8.25):.2f}" y1="{Y(64.46):.2f}" x2="{X(last):.2f}" y2="{Y(64.46):.2f}" stroke="#c0392b" stroke-width="1.0" stroke-opacity=".55"/>')
        o.append(f'<line x1="{X(8.25):.2f}" y1="{Y(67.00):.2f}" x2="{X(last):.2f}" y2="{Y(67.00):.2f}" stroke="#1d2433" stroke-width="1.0" stroke-opacity=".45"/>')
        for (u, k, xk, c, r) in B["keys"]:
            col = end_col(xk)
            o.append(f'<rect x="{X(xk-1.54):.2f}" y="{Y(69.0):.2f}" width="{3.15*S:.2f}" height="{4.0*S:.2f}" fill="#222" fill-opacity=".8"/>')
            for ly, lt in ((65.73, 64.46), (67.0, 67.0), (68.27, 69.54)):
                o.append(f'<polyline points="{X(xk+1.61):.2f},{Y(ly):.2f} {X(xk+3.0):.2f},{Y(ly):.2f} {X(col):.2f},{Y(lt):.2f}" fill="none" stroke="#777" stroke-width=".35"/>')
            for y, cc in ((64.46, "#c0392b"), (67.00, "#1d2433"), (69.54, "#1f5fbf")):
                o.append(f'<circle cx="{X(col):.2f}" cy="{Y(y):.2f}" r="1.0" fill="{cc}"/>')
            # 100n (3V3-GND) and 1k (OUT -> row 72.08), both 1206 on the underside
            o.append(f'<rect x="{X(col)-0.9:.2f}" y="{Y(67.00)-0.2:.2f}" width="1.8" height="{2.54*S+0.4:.2f}" fill="none" stroke="#b86e00" stroke-width=".35" stroke-dasharray=".8 .5"/>')
            o.append(f'<rect x="{X(col)-0.9:.2f}" y="{Y(72.08)-0.2:.2f}" width="1.8" height="{2.54*S+0.4:.2f}" fill="#fff1c2" fill-opacity=".6" stroke="#8a5a00" stroke-width=".35" stroke-dasharray=".8 .5"/>')
            o.append(f'<circle cx="{X(col):.2f}" cy="{Y(72.08):.2f}" r=".8" fill="#8a5a00"/>')
            s.text(X(xk), Y(75.89) - 2.2, k, "noteb", "middle", size=2.6, check=False)
            s.text(X(xk), Y(60.65) + 4.2, u, "ref", "middle", size=2.2, check=False)
            s.text(X(col) + 1.6, Y(70.8) + 0.8, r, "pinname", "start", size=1.7, check=False)
            rows_tab.append([tag, u, k, f"{xk:.3f}", f"{col:.2f}", f"{c} · {r}", f"{col:.2f}"])
        # bulk cap
        o.append(f'<rect x="{X(8.25)-1.2:.2f}" y="{Y(67.00)-0.4:.2f}" width="2.4" height="{2.54*S+0.8:.2f}" fill="#fff1c2" stroke="#b86e00" stroke-width=".35" stroke-dasharray="1 .6"/>')
        s.text(X(8.25), Y(60.65) + 8.4, B["bulk"] + " 10µ", "ref", "middle", size=2.0)
        # lead pads + underside wires
        jx = B["jx"]
        for n, x in enumerate(jx, 1):
            o.append(f'<rect x="{X(x)-1.3:.2f}" y="{Y(74.62)-1.3:.2f}" width="2.6" height="2.6" fill="#fff" stroke="#8a5a00" stroke-width=".4"/>')
            s.text(X(x), Y(74.62) + 0.7, str(n), "pinnum", "middle", size=1.6, check=False)
        wires = [((jx[0], 67.00), (jx[0], 74.62)), ((jx[-1], 64.46), (jx[-1], 74.62))]
        for i, (u, k, xk, c, r) in enumerate(B["keys"]):
            wires.append(((end_col(xk), 72.08), (jx[1 + i], 74.62)))
        for (a1, a2) in wires:
            o.append(f'<line x1="{X(a1[0]):.2f}" y1="{Y(a1[1]):.2f}" x2="{X(a2[0]):.2f}" y2="{Y(a2[1]):.2f}" stroke="#1f5fbf" stroke-width=".35" stroke-dasharray="1.1 .6"/>')
        s.text(X(jx[0]) - 1.5, Y(75.89) - 6.0, f"{B['jref']} 리드 패드 ×{len(jx)} (1 GND … {len(jx)} 3V3, 아랫면 납땜)", "cabt", size=1.9, check=False)
        # mounting U-notches (same as SB)
        for (x, y, edge) in ((3.0, 61.9, 60.65), (3.0, 74.6, 75.89)):
            y0_, y1_ = min(y, edge), max(y, edge)
            o.append(f'<rect x="{X(x-1.7):.2f}" y="{Y(y1_):.2f}" width="{3.4*S:.2f}" height="{(y1_-y0_)*S:.2f}" fill="#fff" stroke="none"/>')
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{1.7*S:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".35"/>')
    s.table(222, 172, ["보드", "센서", "건반", "소자 x", "리드 구멍 x", "100n · 1k (아랫면)", "구멍 x"], rows_tab, [10, 12, 10, 16, 20, 30, 14],
            title="EL·ER 센서 (SB와 같은 규칙: 소자 x + 3.0 이상 첫 격자)", mono_cols=(1, 3, 4, 6))
    s.para(222, 197, [
        "EL·ER 주",
        "1. 기판 = SB와 같은 6행(y61.92 예비·64.46 3V3·67.00 GND·69.54 OUT·72.08·74.62), W1 r4.2 끝 부속 센서 바 안.",
        "    점선 = 센서 바(흐린 칸 = A#0 낮은 구간 x19.93~33.93). 고정: 왼쪽 U홈 M3×10 ×2(3.0, 61.9)·(3.0, 74.6) + 앞·뒤 리브(오른쪽 턱 없음, W1 P36).",
        "2. 센서 바가 기판 윗면을 덮으므로 부품은 모두 아랫면: 100 nF(3V3–GND)·1 kΩ(OUT → y72.08, △13)·10 µF 모두 1206.",
        "3. 파란 점선 = 아랫면 피복 단선: 1k 끝 → 패드 2~, GND 버스 → 패드 1, 3V3 버스 → 끝 패드.",
        "4. 리드(W401 5심 · W411 3심)는 패드에서 기판 밑으로 뒤쪽(+y). 주황 = 뒤 받침 리브 틈(EL x15~38 — B0 선이 x36에서 리브 띠로",
        "    들어감, ER x6~16). W1 r4.4: y77.39 안에서 EL x14.83~21.18 · ER x8.89~12.70으로 모아 레일 밑 차선 EL x13.53~22.48 · ER x7.59~14.00(z5~10)",
        "    → 뒷벽 홈(z5~12). XH 커넥터는 뒤 통로에서 잇는다(SCH-04 주 6). 아랫면 부품·납땜 ≤ 1.8 mm.",
    ], size=2.0)
    return rows_tab


def brd02():
    s = Sheet("BRD-02", 9, TOTAL, "센서 기판 배치 (SB · EL · ER, 위에서 봄)",
              "SB 161.6 × 15.24 양면 도트 기판: 센서 12개 리드 구멍, 3V3·GND·OUT 행, 디커플링 자리, 리본 2×8 블록, 고정 U홈(모듈 좌표 mm). 아래: 끝 부속 EL·ER 기판.",
              "SB · EL · ER", qty="SB × 7 · EL × 1 · ER × 1", basis="v4 W1+ r4.5")
    S = 2.2
    ox, oy = 40, 60

    def X(x):
        return ox + (x - 0) * S

    def Y(y):
        return oy + (77.5 - y) * S
    o = s.out["body"]
    o.append(f'<rect x="{X(1.0):.2f}" y="{Y(75.89):.2f}" width="{(SB_X1 - 1.0)*S:.2f}" height="{15.24*S:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    rowsy = [61.92, 64.46, 67.00, 69.54, 72.08, 74.62]
    rowname = {61.92: "예비", 64.46: "3V3 버스", 67.00: "GND 버스", 69.54: "OUT", 72.08: "리본 홀수", 74.62: "리본 짝수"}
    cols = [0.63 + 2.54 * i for i in range(1, 65)]
    for y in rowsy:
        for x in cols:
            if 1.0 < x < SB_X1:
                o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".45" fill="#b9cdb6"/>')
        s.text(X(0.0) - 1, Y(y) + 0.8, f"y{y:.2f} {rowname[y]}", "tblm", "end", size=1.8, check=False)
    # buses
    o.append(f'<line x1="{X(8.25):.2f}" y1="{Y(64.46):.2f}" x2="{X(160.65):.2f}" y2="{Y(64.46):.2f}" stroke="#c0392b" stroke-width="1.0" stroke-opacity=".55"/>')
    o.append(f'<line x1="{X(8.25):.2f}" y1="{Y(67.00):.2f}" x2="{X(160.65):.2f}" y2="{Y(67.00):.2f}" stroke="#1d2433" stroke-width="1.0" stroke-opacity=".45"/>')
    tab = []
    for i, (k, xk) in enumerate(zip(KEYS, SENSOR_X)):
        col = min(c for c in cols if c >= xk + 3.0)
        tab.append((f"U{201+i}", k, xk, col))
        # body lying face up, leads toward +x
        o.append(f'<rect x="{X(xk-1.54):.2f}" y="{Y(69.0):.2f}" width="{3.15*S:.2f}" height="{4.0*S:.2f}" fill="#222" fill-opacity=".8"/>')
        for ly, lt in ((65.73, 64.46), (67.0, 67.0), (68.27, 69.54)):
            o.append(f'<polyline points="{X(xk+1.61):.2f},{Y(ly):.2f} {X(xk+3.0):.2f},{Y(ly):.2f} {X(col):.2f},{Y(lt):.2f}" fill="none" stroke="#777" stroke-width=".35"/>')
        for y, c in ((64.46, "#c0392b"), (67.00, "#1d2433"), (69.54, "#1f5fbf")):
            o.append(f'<circle cx="{X(col):.2f}" cy="{Y(y):.2f}" r="1.0" fill="{c}"/>')
        # 100n 1206 on bottom across 3V3-GND at next column
        o.append(f'<rect x="{X(col)-0.9:.2f}" y="{Y(67.00)-0.2:.2f}" width="1.8" height="{2.54*S+0.4:.2f}" fill="none" stroke="#b86e00" stroke-width=".35" stroke-dasharray=".8 .5"/>')
        s.text(X(xk), Y(75.89) - 2.2, k, "noteb", "middle", size=2.6, check=False)
        s.text(X(xk), Y(60.65) + 4.2, f"U{201+i}", "ref", "middle", size=2.2, check=False)
        s.text(X(xk), Y(60.65) + 6.9, f"{xk:.2f}", "tblm", "middle", size=1.8, check=False)
    # bulk caps
    for x, ref in ((8.25, "C213"), (158.11, "C214")):
        o.append(f'<rect x="{X(x)-1.2:.2f}" y="{Y(67.00)-0.4:.2f}" width="2.4" height="{2.54*S+0.8:.2f}" fill="#fff1c2" stroke="#b86e00" stroke-width=".35" stroke-dasharray="1 .6"/>')
        s.text(X(x), Y(60.65) + 11.5, ref + " 10µ", "ref", "middle", size=2.0, check=False)
    # mounting holes
    for (x, y, edge) in ((3.0, 61.9, 60.65), (3.0, 74.6, 75.89)):
        y0_, y1_ = min(y, edge), max(y, edge)
        o.append(f'<rect x="{X(x-1.7):.2f}" y="{Y(y1_):.2f}" width="{3.4*S:.2f}" height="{(y1_-y0_)*S:.2f}" fill="#fff" stroke="none"/>')
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{1.7*S:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".35"/>')
    s.text(X(1.0), Y(75.89) - 6.5, "M3×10 자가 탭 ×2 (3.0, 61.9)·(3.0, 74.6) — 기판 앞·뒤에 U홈 Ø3.4", "notes", size=2.0)
    # ribbon block
    for i in range(16):
        col, row = i // 2, i % 2
        x, y = 61.59 + 2.54 * col, (72.08, 74.62)[row]
        o.append(f'<rect x="{X(x)-1.3:.2f}" y="{Y(y)-1.3:.2f}" width="2.6" height="2.6" fill="#fff" stroke="#8a5a00" stroke-width=".4"/>')
        s.text(X(x), Y(y) + 0.8, str(i + 1), "pinnum", "middle", size=1.6, check=False)
    s.text(X(61.59), Y(75.89) - 6.5, "J201 리본 2×8 (x61.6~79.4, y72.08/74.62, 아랫면 납땜) → 뒤 받침 리브 틈 → 리본 차선 x59~82", "cabt", size=2.1)
    # right ledge (W1 r4.5 P36): two inverted-L pieces, lip x161.5~163.0 over the bar end (z13.6~15.1), post x163.0~164.3 from the floor
    for (ya, yb) in ((59.0, 63.4), (70.6, 77.5)):
        o.append(f'<rect x="{X(161.5):.2f}" y="{Y(yb):.2f}" width="{1.5*S:.2f}" height="{(yb-ya)*S:.2f}" fill="#c9d0da" fill-opacity=".6" stroke="#6b7690" stroke-width=".3"/>')
        o.append(f'<rect x="{X(163.0):.2f}" y="{Y(yb):.2f}" width="{1.3*S:.2f}" height="{(yb-ya)*S:.2f}" fill="#9aa6b8" stroke="#6b7690" stroke-width=".3"/>')
    s.text(X(164.3), Y(58.5) + 16.5, "오른쪽 턱(W1 r4.5 P36): 립 x161.5~163.0 z13.6~15.1(바 끝 위 1.4), 기둥 x163.0~164.3 — 바를 1.5 왼쪽에 놓고 오른쪽으로 밀어 넣은 뒤 왼쪽 M3", "notes", "end", size=2.0)
    # table
    rows = [[u, k, f"{xk:.3f}", f"{col:.2f}", f"C{201+i}", f"{col:.2f}"] for i, (u, k, xk, col) in enumerate(tab)]
    s.table(15, 118, ["센서", "건반", "소자 x", "리드 구멍 x (3행)", "100n", "100n 구멍 x"], rows, [16, 12, 18, 30, 14, 22],
            title="센서 리드 구멍 (x = 소자 x + 3.0 이상 첫 격자 0.63 + 2.54·i)", mono_cols=(0, 2, 3, 4, 5))
    s.para(150, 118, [
        "주",
        "1. 기판 x1.0~162.6 × y60.65~75.89, 6행 2.54 간격(바 끝 x162.9보다 0.3 짧게 — 오른쪽 턱 기둥 x163.0과 0.4, 손으로 자른 공차 ±0.3).",
        "    색 원: 빨강 = 3V3(y64.46), 검정 = GND(y67.00), 파랑 = OUT(y69.54).",
        "2. DRV5055는 표시면(모따기 면, '55A2' 인쇄)을 위로 눕혀 센서 바 포켓에 넣는다. 리드는 +x로 빼서",
        "    1.40~3.44 mm 지점에서 2.54 간격으로 벌려 아래로 꺾는다 — 넓어지는 댐바 부분 아래에서 꺾을 것.",
        "    위에서 봐서 리드가 오른쪽(+x)이면 핀 1(VCC)이 앞(작은 y)이다 → y64.46. 가운데 GND, 뒤 OUT.",
        "3. 확인: 3.3 V를 주고 자석 없이 OUT 1.59~1.71 V, S극을 표시면에 가까이 하면 올라간다. 건반을 얹은 쉼 백 ≈1.78 · 흑 ≈1.72 V.",
        "4. 100 nF 1206: 아랫면, 각 센서 리드 구멍 열의 3V3(y64.46)–GND(y67.00) 패드 사이(점선). 10 µF도 아랫면:",
        "    C213 x8.25(왼쪽 받침 기둥 x0.5~6.0과 U201 리드 x10.79 사이), C214 x158.11. 버스는 x8.25부터.",
        "5. 3V3·GND 버스는 아랫면 주석선. OUT 패드 → 아랫면 단선으로 리본 블록 J201(홀수 앞줄)까지.",
        "6. 리본 16심은 아랫면에서 2×8 블록에 납땜(선 n = 핀 n, 15 = GND, 16 = 3V3). IDC 2×8 헤더로 바꿔도 번호가 같다.",
        "    리본(중심 x70.48, x60.32~80.64)은 뒤 받침 리브(y73.2~75.5)의 틈 x59~82를 지난다(W1 r4.4에서 v3 x60~82를 넓힘,",
        "    양옆 1.32 / 1.36 — 리본 차선과 같음).",
    ], size=2.2)
    ep = _end_plans(s)
    s.frame()
    s.expected = {}
    return s


SHEETS += [brd01, brd02]


# ------------------------------------------------------------------ SCH-01 (system interconnect)
CABLES = [
    # id, kind, length, from, to, conductors, bom
    ("W101~W107", "플랫 리본 2651-16P, 16심 전부 사용", "약 180 mm ×7", "SB J201 (2×8)", "MB J301 (2×8)", "16 (3V3 ×2, GND ×2, 신호 12)", "C05"),
    ("W201~W207", "USB-A → C 1 m (C 쪽 몰드 ≤ 12.5×7.6×25)", "1 m ×7", "허브 다운스트림", "O1~O7 RP2040-Zero USB-C", "USB 2.0", "C04"),
    ("W208", "USB-A → C 1 m (CU 안, 짧게 묶음)", "1 m", "허브 다운스트림", "PB RP2040-Zero USB-C", "USB 2.0", "C04"),
    ("W209", "허브 기본 업스트림 선", "허브 부속", "허브 업스트림", "Pi 5 USB-A", "USB 3.0", "L17"),
    ("W401", "EL 리드 (리본 가닥 5심)", "350 mm", "EL J401 (아랫면)", "X401 XH 6P (끝 부속 쪽 50 mm, 뒤 통로)", "5 (XH 1·2·3·4·6)", "C05 · L66"),
    ("W403", "O1 EXT 연장 6심 (L66 모듈 쪽 150 mm)", "150 mm", "O1 MB J302 (아랫면)", "X402 JST-XH 6P (모듈 쪽)", "6", "L66"),
    ("W411", "ER 리드 (리본 가닥 3심)", "300 mm", "ER J411 (아랫면)", "X411 XH 6P (끝 부속 쪽 50 mm, 뒤 통로)", "3 (XH 1·2·6)", "C05 · L66"),
    ("W413", "O7 EXT 연장 6심 (L66 모듈 쪽 150 mm)", "150 mm", "O7 MB J302 (아랫면)", "X412 JST-XH 6P (모듈 쪽)", "6", "L66"),
    ("W501", "3.5 mm 스테레오 3 m (한쪽 잘라 페달에 납땜)", "3 m", "PS U551 (페달 안)", "P501 → J501 (I/O 판)", "3 (T OUT, R VCC, S GND)", "L50"),
    ("W502", "잭 → PB 단선", "약 10 cm", "J501 T·TN·R·S", "PB", "4", "SE12"),
    ("W601", "USB-C ↔ C PD 60 W", "2 m / 0.6 m", "충전기 / 보조배터리", "A601 USB-C", "PD", "C23 / C22"),
    ("W602", "20 V 배선 16 AWG", "약 1 m", "A601 → F601 → SW601", "A602 IN · A702 VCC", "2", "C13"),
    ("W603", "USB-C 수 2선 (MT666)", "약 25 cm", "A602 OUT", "Pi 5 USB-C", "2 (빨강 +, 검정 −)", "C24"),
    ("W604", "허브 어댑터 선 (잘라 씀)", "약 30 cm", "A602 OUT", "허브 DC 입력", "2 (중심 +)", "L17 부속"),
    # △16 (rev C) R31 screen A605 (B1 Waveshare 7-DSI-TOUCH-C)
    ("W605", f"DSI FFC 22핀 0.5 mm {DISP['ffc_mm']} mm B형(반대면), A형 보험", f"{DISP['ffc_mm']} mm", "Pi 5 CAM/DISP 1", "A605 DSI 22핀", "22 (1 ↔ 1)", "v4touch 49·50"),
    ("W606", "실리콘 점퍼 26 AWG F/F 빨강·검정", f"{DISP['jumper_m'] * 100:.0f} cm ×2", "Pi 헤더 핀 2·6 (P603)", "X601 ⇄ X602", "2 (빨강 5 V, 검정 GND)", "v4touch 51·52"),
    ("W607", "실리콘 점퍼 26 AWG M/M 빨강·검정", f"{DISP['jumper_m'] * 100:.0f} cm ×2", "X602 (X601에 꽂음)", "X603 ⇄ X604 (3핀 1·3)", "2", "v4touch 53·54"),
    ("W608", "화면 동봉 전원선 MX1.25 2핀 → 2.54 3핀", "동봉", "X604 2.54 3핀 하우징", "P604 ⇄ A605 MX1.25 2핀", "2 (가운데 빈 칸)", "v4touch 135"),
    ("W701", "3.5 mm 스테레오 1.5 m (볼 쪽 잘라 납땜)", "1.5 m", "동글 A701 (플러그 P701)", "J701 T·R·S (볼)", "3", "C14"),
    ("W702", "3.5 mm 스테레오 1.5 m (볼 쪽 잘라 납땜)", "1.5 m", "J701 TN·RN·S", "P702 → J702 (CU)", "3", "C14"),
    ("W703·W705", "스피커선 16 AWG, 쌍마다 꼼", "약 0.6 m ×2", "A702 L± / R±", "X703 / X705 XT30U-M", "2 ×2", "C13"),
    ("W704·W706", "스피커선 16 AWG", "약 0.3 m ×2", "X704 / X706 XT30U-F", "LS701 / LS702", "2 ×2", "C13"),
    ("X701", "USB-C(F) → USB-A(M) 젠더", "—", "동글", "Pi 5 USB-A", "—", "L52"),
]


def sch01():
    s = Sheet("SCH-01", 1, TOTAL, "시스템 연결도 (배선 계통)",
              "모든 파트·보드와 그 사이 선(W 번호). 파트 사이는 모두 꽂았다 빼는 커넥터(R26). 각 보드의 회로는 SCH-02~07, 부품 자리는 BRD-01·02.",
              "전체", qty="O1~O7 · EL · ER · PB · CU", basis="v4 W1+ r4.5 · R31", **REV_C)
    o = s.out["body"]

    def blk(x, y, w, h, title, lines=(), cls="mod"):
        s.rect(x, y, w, h, cls, "body")
        s.text(x + 1.5, y + 4.2, title, "ref", size=2.6)
        for i, t in enumerate(lines):
            s.text(x + 1.5, y + 7.6 + i * 2.8, t, "notes", size=2.0)

    def cab(pts, label=None, at=None, anchor="start"):
        s.cable(*pts)
        if label:
            s.text(at[0], at[1], label, "cabt", anchor, size=2.1)
    # key modules row
    blk(14, 26, 30, 30, "EL 왼쪽 끝", ["A0·A#0·B0", "센서 3", "헤드폰 잭 J701"])
    for i in range(7):
        x = 50 + i * 43
        blk(x, 26, 39, 30, f"O{i+1} (C{i+1}~B{i+1})", ["W1 건반 12 · 자석 y67", "SB 센서 12 ─W10%d─" % (i + 1), "MB RP2040 + 4067", f"ID {''.join(str(b) for b in reversed(ID_BITS[i+1]))} · 'Toccata O{i+1}'"])
        cab([(x + 19.5, 56), (x + 19.5, 96)], f"W20{i+1}", (x + 21, 78))
    blk(353, 26, 44, 30, "ER 오른쪽 끝", ["C8", "센서 1"])
    cab([(44, 36), (50, 36)])
    s.text(22, 62, "W401 → X401⇄X402 ← W403", "cabt", size=2.0)
    s.text(22, 64.8, "(O1 EXT = 먹스 C12~C14)", "notes", size=2.0)
    cab([(342, 36), (353, 36)])
    s.text(330, 62, "W413 → X412⇄X411 ← W411", "cabt", size=2.0)
    s.text(330, 64.8, "(O7 EXT = 먹스 C12)", "notes", size=2.0)
    # hub
    blk(50, 96, 300, 14, "A604 NEXTU 710U3 유전원 USB 허브 (L17) — 다운스트림 8: O1~O7 + PED", ["보조배터리 칸 뒤 벽 · 허브에 꽂힌 채 케이블 통로(y215~258)에 놓임"])
    # PED
    blk(360, 72, 37, 22, "PB 페달 보드", ["RP2040-Zero", "'Toccata PED'"])
    cab([(378.5, 94), (378.5, 103), (350, 103)], "W208", (366, 101.5))
    blk(360, 118, 37, 18, "PS 댐퍼 페달", ["DRV5055 + 1 kΩ", "듀로 페달 개조"])
    cab([(378.5, 118), (378.5, 108)], None)
    s.text(380, 113, "W501 3 m → J501", "cabt", size=2.0)
    s.line(377, 110, 380, 106, "bodyl", "text")
    # Pi + audio
    blk(50, 140, 60, 30, "A603 Raspberry Pi 5 2GB", ["FluidSynth, USB-MIDI 8입력 병합(D6)", "USB-A ① ← 허브 (W209)", "USB-A ② ← 동글 (X701 젠더)", "USB-C 전원 ← W603 5.1 V",
                                                      "CAM/DISP 1 → W605 화면 DSI", "헤더 2·6 → W606~W608 화면 5 V"])
    # △16 (rev C) R31 screen
    blk(14, 114, 58, 20, "A605 화면 7인치 (R31)", [f"{DISP['model']}", "1024×600 · 5점 터치 · CU 뚜껑 위", f"Pi 헤더 5 V 약 {budget()['disp_w']:.2f} W"])
    s.chg(68.0, 119.0, 16)
    cab([(20, 134), (20, 162), (50, 162)], "W605 DSI", (22, 160.5))
    cab([(36, 134), (36, 150), (50, 150)], "W606~W608", (34.5, 147.0), "end")
    cab([(80, 110), (80, 140)], "W209", (82, 126))
    blk(125, 140, 46, 16, "A701 USB 동글", ["Apple MW2Q3 (DAC)"])
    cab([(110, 150), (125, 150)], "X701", (112, 148.5))
    blk(185, 140, 42, 22, "J701 헤드폰 잭 (EL 볼)", ["PJ-313 노멀 접점", "헤드폰 꽂으면 스피커 끔"])
    cab([(171, 148), (185, 148)], "W701", (173, 146.5))
    blk(241, 140, 50, 22, "CU 트레이", ["J702 앰프 입력 잭", "2 µF + 1 kΩ HPF (D18)", "A702 XH-A232 (TPA3110)"])
    cab([(227, 150), (241, 150)], "W702", (229, 148.5))
    blk(310, 140, 38, 12, "LS701 왼쪽", ["CW-100B25 8 Ω"], "body")
    blk(310, 156, 38, 12, "LS702 오른쪽", ["CW-100B25 8 Ω"], "body")
    cab([(291, 146), (310, 146)], None)
    cab([(291, 160), (310, 160)], None)
    s.text(292, 138.5, "W703⇄W704", "cabt", size=2.0)
    s.text(292, 172.5, "W705⇄W706 (XT30)", "cabt", size=2.0)
    # power
    blk(125, 180, 40, 16, "A601 PD 트리거 20 V", ["I/O 판 USB-C 입력 (W601)"])
    blk(175, 180, 34, 16, "F601 5 A T · SW601", ["I/O 판 스위치"])
    blk(220, 180, 38, 16, "A602 XL4016 → 5.1 V", ["★ 별 접지점 IN−"])
    cab([(165, 188), (175, 188)], None)
    cab([(209, 188), (220, 188)], None)
    s.text(206, 199.5, "+20V", "cabt", size=2.0)
    cab([(214.5, 188), (214.5, 175), (266, 175), (266, 162)], "W602 +20V → 앰프", (230, 173.5))
    cab([(239, 196), (239, 202), (95, 202), (95, 170)], "W603 5.1 V → Pi USB-C", (120, 205))
    cab([(258, 188), (353, 188), (353, 110), (350, 110)], "W604 5.1 V → 허브 DC", (300, 186.5))
    s.text(16, 184.5, "벽 65 W PD / 보조배터리 → W601", "cabt", size=2.2)
    cab([(16, 188), (125, 188)], None)
    # cable schedule
    rows = [[c[0], c[1], c[2], c[3], c[4], c[5], c[6]] for c in CABLES]
    n2 = 11                                   # rows that fit in table 2 above the title block
    n1 = len(CABLES) - n2
    s.table(14, 212, ["W", "종류", "길이", "한쪽", "다른 쪽", "심선", "BOM"], rows[:n1], [18, 56, 20, 30, 44, 34, 14], title="선 목록 (1/2)", rh=3.0)
    rows2 = [[c[0], c[1], f"{c[3]} → {c[4]}", c[6]] for c in CABLES[n1:]]
    s.table(248, 210, ["W", "종류", "한쪽 → 다른 쪽", "BOM"], rows2, [16, 58, 68, 18], title="선 목록 (2/2)", rh=3.0)
    s.frame()
    s.expected = {}
    s.cable_rows_2 = rows[n1:]
    return s


SHEETS.insert(0, sch01)
