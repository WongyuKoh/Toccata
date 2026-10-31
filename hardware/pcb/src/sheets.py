"""Toccata circuit sheets (design data + drawing). Run build.py to regenerate outputs."""
from sch import (Sheet, sym_R, sym_C, sym_hall, sym_box, sym_conn, sym_jumper, sym_fuse,
                 sym_switch, sym_switch_dpst, sym_speaker, sym_jack, sym_plug, sym_conn2, sym_tp, sym_conn_pos)
import parts as P

TOTAL = 15
KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NET = {k: "HALL_" + k.replace("#", "S") for k in KEYS}           # HALL_C, HALL_CS, ...
RIBBON = ["+3V3", "GND"] + ["HALL_" + k.replace("#", "S") for k in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]] + ["GND", "+3V3"]
SENSOR_X = [7.431, 21.215, 35.250, 49.285, 63.070, 77.359, 90.573, 104.037, 117.500, 130.964, 144.427, 157.641]


POWER = ("GND", "+3V3", "+3V3_O1", "+3V3_O7", "+12V8", "+5V1", "+5V_PI")

# ------------------------------------------------------------------ R31 touchscreen (rev C, 2026-10-01)
# B1 = Waveshare 7-DSI-TOUCH-C, powered from the Pi 40-pin header (pin 2 = 5 V, pin 6 = GND).
REV_C = dict(rev="C", date="2026-10-01")
# ------------------------------------------------------------------ △17 battery input (rev D, 2026-10-07)
# User decision 2026-10-07 (R33): USB-C PD (HUSB238 A601 + 65 W charger / PD power bank) -> LiFePO4 pack BT601.
REV_D = dict(rev="D", date="2026-10-07")
# ------------------------------------------------------------------ rev E (2026-10-08): final purchases (plan C) + physical sheets
# BE163 board pieces, Adafruit 4876 EXT pair, KCD1-104 as two poles in parallel, ATO blade fuse holder, C24 Pi lead, J502 pads,
# AUX halves, wire lengths from the CAD (cad_extract.py); new sheets BRD-03 (PED board) .. BRD-06 (signal harnesses).
REV_E = dict(rev="E", date="2026-10-08")
BATT = dict(
    model="LiFePO4 12.8 V 6 Ah",
    v_nom=12.8, v_min=10.0, v_max=14.6,   # bus range: BMS low-voltage cut (typ.) .. charger end voltage
    wh=76.8, usable=0.9,                   # 12.8 V x 6 Ah; about 90 % usable
    buck_min_v=7.0,                        # XL4016 at 5.1 V out, 3-5 A: VIN >= VOUT + about 2 V (research/power.md 2)
    amp_pvcc=(4.5, 26),                    # TPA3118D2 PVCC (△32 HW-720; the board is labelled 12-28 V)
    amp_w_ch=8.0, amp_w_ch_20v=20.0,       # 8 ohm BTL, 1 % THD: about 8 W/ch at 12.8 V, about 20 W/ch at 20 V
    amp_eff=0.8,                           # amp input = output / 0.8 at clipping (efficiency incl. idle, conservative)
    fuse_a=5.0,
)
DISP = dict(
    model="Waveshare 7-DSI-TOUCH-C",
    power_w=2.15,            # purchase list No.135 / Waveshare wiki: about 2.15 W from the GPIO 5 V
    v=5.0,                   # screen input voltage used for the current
    jumper_m=0.20,           # silicone jumpers 20 cm (F/F, then M/M) per conductor
    jumper_awg26_ohm_m=0.1339,  # 26 AWG copper, ohm per metre
    ffc_mm=300,              # GUOCONN 22P 0.5 mm 300 mm B-type (reverse); A-type bought as insurance
    overlay="dtoverlay=vc4-kms-dsi-waveshare-panel-v2,7_0_inch_c",
)
# SCH-06 rev B budget inputs (unchanged) + D19 peak basis of rev C (52 W at 20 V, kept only to show the old amp share)
BUDGET_IN = dict(pi_w=7.7, pi_a=1.5, hub_w=2.0, hub_a=0.4, dongle_w=0.5, dongle_a=0.1, eff=0.90,
                 amp_avg_w=(2.0, 6.0), peak_basis_w=52.0, pi_v=5.1)


def budget():
    """Power budget, rev D (battery 12.8 V) with the R31 display: all derived numbers of SCH-06 and README △17.
    The amp average (2~6 W) is kept from the 20 V table (conservative: the new ceiling is about 4 dB lower)."""
    import math
    b = BUDGET_IN
    t = BATT
    d_w = DISP["power_w"]
    d_a = d_w / DISP["v"]
    five_old = b["pi_w"] + b["hub_w"] + b["dongle_w"]
    five_new = five_old + d_w
    loss_old = five_old / b["eff"] - five_old
    loss_new = five_new / b["eff"] - five_new
    avg = [five_new + loss_new + a for a in b["amp_avg_w"]]
    base_old = five_old + loss_old                 # non-amp input power, rev B
    base_new = five_new + loss_new                 # non-amp input power, with the display
    # amp at 12.8 V: clips at about 8 W/ch instead of about 20 W/ch -> the level ceiling drops by
    amp_db = 10 * math.log10(t["amp_w_ch"] / t["amp_w_ch_20v"])           # about -4 dB
    amp_old = b["peak_basis_w"] - base_old         # rev C: amp share of the D19 52 W peak at 20 V
    amp_lo = amp_old * t["amp_w_ch"] / t["amp_w_ch_20v"]                   # same share, scaled to the 12.8 V clip power
    amp_hi = 2 * t["amp_w_ch"] / t["amp_eff"]      # 2 x 8 W at clipping / 0.8 (conservative)
    peak_lo, peak = base_new + amp_lo, base_new + amp_hi
    run = [t["wh"] * t["usable"] / x for x in avg]                         # hours, [light, heavy]
    pi_in_a = (b["pi_w"] + b["dongle_w"] + d_w) / b["pi_v"]
    drop = 2 * DISP["jumper_m"] * 2 * DISP["jumper_awg26_ohm_m"] * d_a   # 2 jumpers in series, out and back
    v = t["v_nom"]
    return dict(disp_w=d_w, disp_a=d_a, five_new=five_new, loss_old=loss_old, loss_new=loss_new, base_new=base_new,
                avg=avg, avg_a=[x / v for x in avg], amp_avg_a=[a / v for a in b["amp_avg_w"]],
                amp_db=amp_db, amp_old=amp_old, amp_lo=amp_lo, amp_hi=amp_hi,
                peak=peak, peak_a=peak / v, peak_lo=peak_lo, peak_lo_a=peak_lo / v, peak_a_min_v=peak / t["v_min"],
                run=run, pi_in_a=pi_in_a, drop_v=drop)


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
              "MB", qty="MB × 7", basis="v4 W1+ r4.5", **REV_E)
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
        s.text(353, py + 0.8, ["GND (XH 1번)", "EXT1 → C12", "EXT2 → C13", "EXT3 → C14", "EXT4 → C15", "3V3 (XH 6번)"][i], "notes", size=2.0)
    import harness as _H
    s.text(318, 68.5, "O1·O7만 Adafruit 4876 플러그 선 %d / %d mm → XH 6P (SCH-04)" % (_H.EXT_CUT["O1"], _H.EXT_CUT["O7"]), "notes", size=2.0)
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
        f"1. △33 기판: 양면 만능기판 80 × 120 통째로(Coms BE163 30 × 42 구멍 — 자르지 않음, 구멍·나사 없음), {MBX['board']}.",
        "    모듈 바닥 자리에 놓고 따로 출력한 밸런스 레일이 맨 띠 y132.0~144.8을 눌러 잡는다(CAD A16, BRD-01 주 2).",
        "2. 앞 구역(J301·A302, 부품 ≤ z17.27)과 뒤 구역(A301·J302·R301~R304·JP·TP, ≤ z20.9) 사이 맨 띠(줄 j 14~19)에는 부품·패드가 없다.",
        "    앞↔뒤 아랫면 선은 레일 밑 띠 리브의 틈 x92.0~114.0으로만(BRD-08). 기판 밑 2.0: 다리·핀 끝 ≤ 1.0, 아랫면 선은 리본 가닥.",
        f"3. RP2040-Zero: {MBX['zero']}, USB-C +y (리셉터클 가운데 x83.38 → 플러그·케이블이 곧게 뒷벽 개구 x76.45~91.55로).",
        "    몰드(2.5)가 그대로인 보통 핀 헤더로 세운다 — 밑면 칩·수정·LDO와 기판 사이 1.2 (캡톤 없음). 위로 F|F# 핀 밑변 z18.0.",
        f"4. A302 먹스 모듈: 긴 쪽을 x로 눕혀 채널 줄을 앞에 ({MBX['mux']}) → BRD-01. J301 리본은 아랫면에서 꽂아 윗면 납땜, J302는 윗면 납땜.",
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
    col = {1: "XH 1번", 6: "XH 6번"}
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
              "EL · ER", qty="EL × 1 · ER × 1", basis="v4 W1+ r4.5 끝 부속", **REV_E)
    e = {}
    s.box(14, 22, 380, 94, "EL — 왼쪽 끝 부속 센서 기판 (x1.0~46.5 × y60.65~75.89, 45.5 × 15.24 mm, 6행) — BRD-02 배치")
    _end_board(s, e, 22, "L", [("A0", "EL_A0", 1), ("A#0", "EL_AS0", 2), ("B0", "EL_B0", 3)],
               401, 401, 401, "J401", 401, "+3V3_EL")
    s.box(14, 120, 380, 94, "ER — 오른쪽 끝 부속 센서 기판 (로컬 x1.0~23.0 × y60.65~75.89, 22.0 × 15.24 mm, 6행) — BRD-02 배치")
    _end_board(s, e, 120, "R", [("C8", "ER_C8", 1)], 411, 411, 411, "J411", 411, "+3V3_ER")
    s.para(15, 220, [
        "주  1. 끝 부속 센서도 SCH-02와 같다: DRV5055A2 + 100 nF(센서 옆). W1 자석 x: 왼쪽 부속(x0~47) A0 10.287, A#0 26.927, B0 40.141, 오른쪽 부속(로컬 x0~23.5) C8 11.75.",
        "        기판은 W1 r4.2 끝 부속 센서 바(왼 x0.5~46.5, 오른 x0.5~23.0) 안: EL x1.0~46.5, ER x1.0~23.0 (SB와 같은 6행 15.24). 리드 구멍 A0 13.33, A#0 31.11, B0 43.81, C8 15.87.",
        "     2. 커넥터: Adafruit 4876 JST-XH 호환 6P 짝(각 약 20 cm, 26 AWG) — 플러그 선은 모듈 쪽 150, 소켓 선은 끝 부속 쪽 50으로 자름. ‘>>’ = 맞물림(KiCad 연결 아님 →",
        "        양쪽에 같은 넷 이름). +3V3_EL·+3V3_ER은 각각 O1·O7 제어 기판의 3V3 레일이다(프로젝트 전원 심볼로 추가).",
        "     3. △6 XH 위치 = J302 EXT 패드 번호: 1 = GND, 2~5 = 먹스 C12~C15, 6 = 3V3. 선 색이 아니라 하우징 번호로 구분 —",
        "        자르기 전에 양쪽에 번호 테이프, 납땜 뒤 끝에서 끝까지 통전 확인. 선 만들기·자르는 길이 = BRD-06.",
        "     4. △3 C404·C412 10 µF: 3V3가 긴 선 끝(EL 150 + 350 mm, ER 150 + 300 mm)이라 벌크 콘덴서 추가.",
        "     5. △8 R401~R403·R411 1 kΩ 1206 칩(아랫면, △13): 센서 바가 기판 윗면을 덮어 리드형 저항을 둘 자리가 없다 — OUT 구멍과 바로 뒤 행(y72.08) 사이.",
        "        센서 OUT 바로 뒤에서 약 0.6 m 선 용량을 떼어 낸다(TI: OUT에 C 직결 금지). MB의 100 kΩ 풀다운과 함께",
        "        끝 부속을 빼면 EXT = 0 V. 펌웨어: O1 C12~C14 → MIDI 21~23, O7 C12 → 108, 0.15 V 아래면 센서 없음.",
        "     6. W401·W411 길(W1 r4.4, r4.5 그대로): 패드(아랫면) → 기판 밑 → 뒤 받침 리브 틈 → 패드 줄 뒤 y77.39 안에서 EL x14.83~21.18 · ER x8.89~12.70으로 모음",
        "        → 바닥(건반 밑) → 끝 부속 밸런스 레일 밑 차선(z5~10; EL x13.53~22.48, ER x7.59~14.00) → 뒷벽 홈(z5~12) → 뒤 케이블 통로의 X401·X411.",
        "        순서: 리본 가닥을 J401/J411에 납땜 → 기판·센서 바 고정 → 자유 끝을 리브 틈·차선·뒷벽 홈으로 꿴 뒤, 뒤 통로에서 L66 소켓 선(50 mm)과",
        "        이어 열수축(C10). XH 하우징(폭 약 17)은 차선·홈을 못 지나므로 먼저 달지 않는다. 아랫면 칩·납땜 ≤ 1.8 mm(기판 밑 2.0).",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch04)


# ------------------------------------------------------------------ SCH-05
def sch05(ring_r="20"):
    s = Sheet("SCH-05", 5, TOTAL, "페달 보드 (PB) + 댐퍼 페달 센서 (PS)",
              "댐퍼(서스테인) 페달 1개(R24). 페달 안 홀센서가 발판 자석 거리를 재고, PED 보드 RP2040-Zero가 CC64 0~127(하프페달)로 보낸다. 기판 자리는 BRD-03.",
              "PB · PS", qty="PB × 1 · PS × 1", basis="v4 W1+ · R24", **REV_E)
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
    s.box(106, 22, 78, 80, "뒤판 출력물 — 페달 잭 기판 (J501 조각)")
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
    # rev E: the jack sits on its own perfboard scrap on the back plate; W502 (4 ribbon strands) lands on the PB pads J502
    x, y = s.pin("J501", "TN")
    s.wire((x, y), (x + 5, y))
    s.pwr(x + 5, y, "GND")
    s.chg(x + 10.5, y - 0.5, 9)
    s.wire(jt, (jt[0] + 3, jt[1]))
    s.label(jt[0] + 3, jt[1], "PED_TIP", "R")
    s.wire(jr, (jr[0] + 3, jr[1]))
    s.label(jr[0] + 3, jr[1], "PED_VCC", "R", up=False)
    s.wire(js, (js[0] + 5, js[1]))
    s.pwr(js[0] + 5, js[1], "GND")
    exp_add(e, "GND", "J501.TN")
    exp_add(e, "PED_TIP", "J501.T")
    exp_add(e, "PED_VCC", "J501.R")
    exp_add(e, "GND", "J501.S")
    s.text(108, 97.0, "W502: J501 → PB J502, 리본 가닥 4개 (BRD-06)", "cabt", size=2.0)
    s.chg(196.5, 36.5, 19)
    # --- PB board
    s.box(188, 22, 208, 110, "PB — 페달 보드 70 × 50 (8 × 12 양면 기판 조각, CU 칸 안) — 자리: BRD-03")
    jp = sym_conn_pos("Conn_01x04", 5, [(1, 0), (3, 2), (2, 3), (4, 4)], side="R", width=9)
    s.place(jp, "J502", "W502 패드 1×4", 190, jt[1] - 2.5, ref_at=(0, -1.2), val_at=(0, 29.6), meta=dict(bomkey="PADS"))
    for n, nm in ((1, "T"), (3, "R"), (2, "TN"), (4, "S")):
        px_, py_ = s.pin("J502", n)
        s.text(191.0, py_ + 0.8, nm, "pinname", size=2.0)
    s.place(sym_R(), "R501", "1k", 215.0, jt[1], rot=90, ref_at=(0, -3.0, "middle"), val_at=(0, 4.9, "middle"))
    s.place(sym_R(), "R502", "100k", 215.0, jt[1] - 12.5, rot=90, ref_at=(0, -3.0, "middle"), val_at=(0, 4.9, "middle"))
    s.place(sym_R(), "R503", ring_r + "Ω", 215.0, jr[1], rot=90,
            ref_at=(0, 5.0, "middle"), val_at=(0, 8.0, "middle"), part="100Ω ×5 병렬", part_at=(0, 10.3, "middle"))
    L = lambda ref: min((s.pin(ref, 1), s.pin(ref, 2)), key=lambda p: p[0])
    Rr = lambda ref: max((s.pin(ref, 1), s.pin(ref, 2)), key=lambda p: p[0])
    num = lambda ref, pt: "1" if s.pin(ref, 1) == pt else "2"
    j1, j3, j2, j4 = s.pin("J502", 1), s.pin("J502", 3), s.pin("J502", 2), s.pin("J502", 4)
    s.wire(j1, L("R501"))
    s.wire((j1[0] + 1.75, j1[1]), (j1[0] + 1.75, L("R502")[1]), L("R502"))
    s.wire(j3, L("R503"))
    s.label(j1[0] + 1.75, j1[1] - 6.0, "PED_TIP", "U")
    s.label(j3[0] + 0.5, j3[1], "PED_VCC", "R")
    s.wire(j2, (j2[0] + 1.5, j2[1]), (j2[0] + 1.5, j4[1]))
    s.wire(j4, (j4[0] + 1.5, j4[1]))
    s.pwr(j4[0] + 1.5, j4[1], "GND")
    exp_add(e, "PED_TIP", "J502.1")
    exp_add(e, "GND", "J502.2", "J502.4")
    exp_add(e, "PED_VCC", "J502.3")
    s.wire(Rr("R503"), (Rr("R503")[0] + 7.5, jr[1]))
    s.pwr(Rr("R503")[0] + 7.5, jr[1], "+3V3")
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
    s.chg(215.0, jr[1] + 13.5, 4)
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
        "3. W502: J501 조각 → PB J502 (1 T, 2 TN, 3 R, 4 S), 리본 가닥 4개(BRD-06). △9 TN을 GND에: 플러그가 없으면 팁이 GND에 붙어 0 V (RN은 안 씀).",
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
        "    P601(C24) ← +5V1에서 온다 → 넷 이름 +5V_PI(전원 심볼).",
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
    T = BATT
    s = Sheet("SCH-06", 6, TOTAL, "전원 (CU)",
              "전지 입력 하나(R33): LiFePO4 12.8 V 6 Ah → XT60 → 5 A 퓨즈 → 스위치(두 회로 나란히) → 12.8 V 버스 → 앰프 + 5.1 V 강압 → Pi 5 · 허브 · 화면(Pi GPIO 5 V, R31). 배선 경로는 BRD-04, 자르는 길이는 BRD-05.",
              "CU 전원", qty="CU × 1", basis="v4 W1+ · R31 · R33", **REV_E)
    e = {}
    # △17 (rev D) BT601 LiFePO4 pack (KiCad Device:Battery, 1 = +, 2 = -) with its XT60 female lead (X605)
    pk = sym_box("LiFePO4_pack", [], [(1, "+", "pwr"), (2, "−", "pwr")], width=26, cls="mod", rows=2)
    for cx in (4.0, 10.0):                                   # two cell glyphs (long + short plate)
        pk.line(cx, 3.5, cx, 11.5, "bodyl")
        pk.line(cx + 2.0, 5.5, cx + 2.0, 9.5, "bodyl")
    pk.line(6.0, 7.5, 10.0, 7.5, "bodyl")
    s.place(pk, "BT601", f"{T['model']}", 16, 40, val_at=(0, 18.5),
            part=f"{T['wh']} Wh · BMS 내장 (받으면 확인)", part_at=(0, 20.8), meta=dict(bomkey="BATT"))
    s.chg(44, 37.5, 17)
    xf_, xm = 62.0, 69.5
    s.place(sym_conn("XT60-F", 2, side="L", width=6, rev=True), "X605", "XT60 암", xf_, 42.5,
            ref_at=(0, -2.2), val_at=(-1, 17.5), part="팩 리드 끝", part_at=(-1, 19.8), meta=dict(bomkey="XT60F"))
    s.place(sym_conn("XT60-M", 2, side="R", width=6, rev=True), "X606", "XT60 수", xm, 42.5,
            ref_at=(0, -2.2), val_at=(1, 17.5), part="W601 (L80)", part_at=(1, 19.8), meta=dict(bomkey="XT60M"))
    s.mate("X605", "X606", at=(xf_ + 6.3, 42.5 + 12.3))
    s.text(xf_ + 3.6, 42.5 + 3.3, "+", "pinnameh", size=2.3)
    s.text(xf_ + 3.6, 42.5 + 8.3, "−", "pinnameh", size=2.3)
    for k, pb in ((1, "1"), (2, "2")):                       # BT601 + -> X605 2, BT601 - -> X605 1
        s.wire(s.pin("BT601", k), s.pin("X605", "2" if k == 1 else "1"))
    vx, vy = s.pin("X606", 2)                                # + row (y45)
    gx, gy = s.pin("X606", 1)                                # - row (y50)
    s.label(49.0, vy, "VBAT", "R")
    exp_add(e, "VBAT", "BT601.1", "X605.2", "X606.2")
    exp_add(e, "GND", "BT601.2", "X605.1", "X606.1")
    s.wire((xf_ - 7.5, gy), (xf_ - 7.5, gy + 4.0))
    s.pwr(xf_ - 7.5, gy + 4.0, "GND")
    s.para(16, 66.0, [
        "충전: 스위치 끄고 뚜껑 L을 열어 사용자 LiFePO4 충전기(14.4 V)를 팩 DC 5.5×2.1 입력에 (XT60은 꽂아 둔 채).",
        "충전하며 연주하지 않는다(충전기가 부하 동시 사용을 밝힌 경우만 예외).",
        "벤치 시험: 전지 대신 12 V SMPS(XT60 암 L81)를 X606에.",
        "둘을 함께 꽂지 않는다. SMPS 선 극성은 멀티미터로 먼저 확인.",
        f"W601: X606 리드 {HN.LEAD_W601} mm + 홀더 꼬리 {HN.STUB12} mm (이은 전체 ≤ {HN.W601_MAX} mm) → 빨강 = F601 꼬리와 이음, 검정 = ★ 강압 IN−까지",
    ], "notes", size=2.0, lh=2.8)
    # △18 mis-mating guard: speaker joints are XT60 too
    s.chg(18.0, 82.2, 18)
    s.para(22, 83.0, [
        "잘못 꽂기 방지: 스피커 접속(SCH-07 X703~X706)도 XT60. 여기에 전원을 꽂으면 12.8 V DC가",
        "BTL 출력·보이스 코일에 걸린다(6.2 Ω에 약 2 A, 스피커 과열).",
        "전원 XT60(팩 리드 X605·W601 X606·벤치 L81) = 빨강 수축, 스피커 XT60 = 파랑 수축 + ‘SPK’.",
        f"W601은 홀더 −x 끝에서 XT60 뒤끝까지 {HN.W601_MAX} mm 이하(꼬리 {HN.STUB12} + 리드 {HN.LEAD_W601} − 겹침 10) → 왼쪽 스피커 XT60(직선 {HN.W601_NEED_L:.1f} mm)에 닿지 않는다.",
    ], "notes", size=2.0, lh=2.8)
    # fuse + switch
    fx, swx = 100.0, 130.0
    s.place(sym_fuse(), "F601", "5 A ATO 블레이드", fx, vy, ref_at=(0, -3.0, "middle"), val_at=(0, 5.0, "middle"),
            part="ATC/ATO 홀더 (보유)", part_at=(0, 7.2, "middle"))
    s.wire((vx, vy), s.pin("F601", 1))
    # rev E: KCD1-104 = DPST, both poles in parallel (inputs 1+3, outputs 2+4) - KiCad Switch:SW_DPST
    s.place(sym_switch_dpst(), "SW601", "KCD1-104", swx, vy, ref_at=(0, -4.2, "middle"), val_at=(0, 15.0, "middle"),
            part="두 회로 나란히 · 뒤판 출력물", part_at=(0, 17.2, "middle"))
    s.wire(s.pin("F601", 2), s.pin("SW601", 1))
    s.wire((swx - 10.0, vy), (swx - 10.0, vy + 10.0), s.pin("SW601", 3))
    s.wire(s.pin("SW601", 4), (swx + 10.0, vy + 10.0), (swx + 10.0, vy))
    s.chg(swx + 14.5, vy + 8.0, 20)
    s.label(vx + 1.5, vy, "VBAT", "R")
    s.label(s.pin("F601", 2)[0] + 1, vy, "VBAT_F", "R")
    exp_add(e, "VBAT", "F601.1")
    exp_add(e, "VBAT_F", "F601.2", "SW601.1", "SW601.3")
    s.wire((gx, gy), (gx + 3.5, gy))
    s.pwr(gx + 3.5, gy, "GND")
    # 12.8 V bus (10.0 ~ 14.6 V)
    bx = 185
    s.wire(s.pin("SW601", 2), (bx, vy))
    s.pwr(bx - 5, vy, "+12V8")
    s.text(143, vy + 5.0, f"버스 {T['v_min']:.1f}~{T['v_max']:.1f} V (공칭 {T['v_nom']} V)", "notes", size=2.0)
    s.regions["power"] = (9.0, 20.0, 411.0, 178.0)
    s.regions["display"] = (9.0, 178.6, 411.0, 253.0)
    exp_add(e, "+12V8", "SW601.2", "SW601.4")
    # A602 buck
    bk = sym_box("XL4016_module", [(1, "IN+"), None, (2, "IN-")], [(3, "OUT+"), None, (4, "OUT-")], width=30, cls="mod", rows=3)
    s.place(bk, "A602", "XL4016 강압 → 5.1 V", 195, 80, val_at=(0, 23.5), part="XH-M401 (L58) · 가변저항으로 5.10 V 맞춤", part_at=(0, 25.8))
    i1, i2 = s.pin("A602", 1), s.pin("A602", 2)
    s.wire((bx, vy), (bx, i1[1]), i1)
    s.wire(i2, (i2[0] - 7.5, i2[1]))
    s.pwr(i2[0] - 7.5, i2[1], "GND")
    s.text(i2[0] - 30, i2[1] + 7.5, "★ 별 접지점: 강압 IN− 단자", "noteb", size=2.3)
    exp_add(e, "+12V8", "A602.1")
    exp_add(e, "GND", "A602.2")
    # 12.8 V to amp (sheet 7)
    s.wire((bx, vy), (bx + 55, vy))
    s.pwr(bx + 55, vy, "+12V8")
    s.text(bx + 58, vy + 0.8, "→ SCH-07 A702 DC 잭 (W602c)", "notes", size=2.0)
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
    s.place(pl, "P601", "USB-C 측면 꺾임 (C24 BT663)", px0, 55, val_at=(0, 23.5), part="A 끝을 잘라 2선 → Pi 5 USB-C (W603)", part_at=(0, 25.8),
            meta=dict(bomkey="C24"))
    s.place(pl2, "P602", "일자 DC 플러그 (허브 어댑터 선)", px0, 95, val_at=(0, 23.5), part="→ 허브 DC 입력 (W604, L17 부속)", part_at=(0, 25.8),
            meta=dict(bomkey="HUBDC"))
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
    for i, (ref, net) in enumerate((("TP601", "+12V8"), ("TP602", "+5V1"), ("TP603", "GND"))):
        tx, ty = 110 + i * 20, 118
        s.place(sym_tp(), ref, "", tx, ty, ref_at=(1.8, -3.2), hide_val=True)
        if net == "GND":
            s.wire((tx, ty), (tx, ty + 2.5)); s.pwr(tx, ty + 2.5, "GND")
        else:
            s.wire((tx, ty), (tx, ty + 2.5), (tx - 5, ty + 2.5)); s.pwr(tx - 5, ty + 2.5, net)
        exp_add(e, net, f"{ref}.1")
    # current budget table (rev D: battery 12.8 V; R31 screen kept)
    I = BUDGET_IN
    v = f"{T['v_nom']} V"
    rows = [["Pi 5 (FluidSynth, USB 장치 포함)", "5.1 V", f"약 {I['pi_a']} A (최대 5 A 한도)", f"{f1(I['pi_w'])} W"],
            ["허브 + RP2040 8개 + 센서 89개", "5.1 V", f"약 {I['hub_a']} A", f"{f1(I['hub_w'])} W"],
            ["USB 동글 (Pi 포트)", "5 V", f"약 {I['dongle_a']} A", f"{f1(I['dongle_w'])} W"],
            ["화면 A605 (Pi 헤더 2번, 밝기 100 %)", f"{DISP['v']:.0f} V", f"약 {B['disp_a']:.2f} A", f"{B['disp_w']:.2f} W"],
            [f"강압 효율 {I['eff'] * 100:.0f} % 손실", "", "", f"{f1(B['loss_new'])} W"],
            ["앰프 평균 (피아노 음악, 보수적 추정)", v, f"약 {B['amp_avg_a'][0]:.2f}~{B['amp_avg_a'][1]:.2f} A",
             f"{I['amp_avg_w'][0]:.0f}~{I['amp_avg_w'][1]:.0f} W"],
            ["합계 (평균)", v + " 입력", f"약 {f1(B['avg_a'][0])}~{f1(B['avg_a'][1])} A",
             f"약 {f1(B['avg'][0])}~{f1(B['avg'][1])} W"],
            [f"순간 최대 (최저음 강타, 앰프 2 × {T['amp_w_ch']:.0f} W ÷ {T['amp_eff']})", v + " 입력", f"약 {f1(B['peak_a'])} A",
             f"약 {f1(B['peak'])} W"],
            ["같은 순간 최대, 전지 끝 (BMS 차단 직전)", f"{T['v_min']:.1f} V", f"약 {f1(B['peak_a_min_v'])} A",
             f"퓨즈 {T['fuse_a']:.0f} A ATO"],
            [f"연주 시간 ({T['wh']} Wh × {T['usable']} ÷ 평균)", "", "", f"약 {f1(B['run'][1])}~{f1(B['run'][0])} h"]]
    ty_end = s.table(15, 135, ["부하", "전압", "전류", "전력"], rows, [70, 22, 44, 20],
                     title=f"전원 예산 (R31 · R33 계산, {T['model']} = {T['wh']} Wh)")
    s.chg(174.5, 135 + 4.2 + 3.3 * 4 + 1.8, 16)
    s.chg(174.5, 135 + 4.2 + 3.3 * 7 + 1.8, 17)
    s.para(190, 135, [
        "주",
        f"1. BT601 {T['model']}({T['wh']} Wh), BMS 내장(받으면 확인). 버스 {T['v_min']:.1f}~{T['v_max']:.1f} V: 강압은 5.1 V에 약 {T['buck_min_v']:.0f} V 이상,",
        f"    앰프 칩 PVCC {T['amp_pvcc'][0]}~{T['amp_pvcc'][1]} V(HW-720 표기 12~28 V)라 범위 전체에서 동작하고 BMS 저전압 차단(보통 약 {T['v_min']:.0f} V)까지 켜져 있다. XT60은 모양으로 극성이 정해진다.",
        "2. 충전은 스위치를 끄고 LiFePO4 충전기(14.4 V)를 팩 DC 5.5×2.1 입력에(XT60은 꽂아 둔 채). 충전기가 부하 동시 사용을 밝히지 않으면 충전하며 연주하지 않는다.",
        "    벤치 시험: 전지 대신 12 V SMPS(XT60 암 L81)를 X606에 — 둘을 함께 꽂지 않는다. SMPS 쪽 선 극성은 멀티미터로 먼저 확인.",
        f"3. F601 5 A ATO 블레이드(사용자 보유 홀더, 12 AWG 꼬리 둘 다 홀더 끝에서 {HN.STUB12} mm로 잘라 16 AWG에 납땜 + 수축): X606 바로 뒤 + 선. 전지는 단락 전류가 커서 퓨즈 + BMS가 막는다.",
        "    SW601 = KCD1-104(4핀 DPST, 사용자 보유): 켬 상태 통전으로 한 회로의 두 단자를 찾고, 입력 둘(1·3)·출력 둘(2·4)을 짧은 선으로 묶는다. DC 차단 정격 미공개 → 소리를 멈춘 뒤 끈다.",
        "4. Pi 5에는 P601(USB-C 2선 리드)로 5.1 V만 넣는다. GPIO 5V 핀 급전·동시 급전 금지(D16). 화면은 헤더에서 받아 감(주 9).",
        "5. 허브는 딸린 5 V 어댑터 선을 잘라 플러그 쪽(P602)을 강압 모듈에 물린다. 극성은 멀티미터로 확인.",
        "6. △5 GND는 한 점(★ 강압 IN− 단자)에서 모은다: 전지 −(W601 검정)·앰프 GND 선이 여기서만 만난다 (검토 R7, 험 방지).",
        f"7. 첫 연결 전: 강압 출력을 무부하로 5.10~5.15 V에 맞추고 가변저항을 고정(접착) — 출고값은 입력(최대 {T['v_max']} V)까지 나올 수 있다(R6).",
        "    C24 빨강 = +, 허브 선 중심 = + 를 멀티미터로 확인. Pi 헤더 핀 2–6이 부하 때 5.0 V 이상. 12.8 V·5.1 V 선 = 16 AWG(18 AWG도 됨).",
        "8. 스위치로 끄면 Pi가 갑자기 꺼진다 → 읽기 전용 오버레이 파일 시스템 권장(R13). 스위치를 10번 켜고 끄며 BMS가 끊기지 않는지 확인(R12).",
        f"△17 순간 최대 = 앰프 2 × {T['amp_w_ch']:.0f} W ÷ {T['amp_eff']} = {B['amp_hi']:.1f} W + 나머지 {f1(B['base_new'])} W = 약 {f1(B['peak'])} W.",
        f"    앰프 최대 출력 약 {T['amp_w_ch']:.0f} W/ch(8 Ω, 1 % THD, 입력 약 0.13 Vrms) — 찌그러지지 않게 소프트웨어 음량 상한을 둔다(SCH-07 주 4).",
    ], size=2.1, lh=3.0)
    _display_band(s, e, 180.0)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch06)


# ------------------------------------------------------------------ SCH-07
def sch07():
    s = Sheet("SCH-07", 7, TOTAL, "오디오 (CU)",
              "Pi 5 → USB 동글(DAC) → 왼쪽 볼 헤드폰 잭(노멀 접점) → 앰프 입력 잭 → 약 80~93 Hz RC → HW-720 (TPA3118D2) → XT60 → 스피커 2개. 헤드폰을 꽂으면 앰프 입력이 끊긴다(R15).",
              "CU 오디오", qty="CU × 1", basis="v4 W1+ · R25 · R33", **REV_E)
    e = {}
    plug = sym_plug()
    # dongle block with its 3.5 mm jack contacts (T,R,S)
    dg = sym_box("Apple_USB-C_dongle", [], [("T", "L"), ("R", "R"), ("S", "GND")], width=26, cls="mod", rows=3)
    s.place(dg, "A701", "Apple USB-C → 3.5 mm (MW2Q3)", 18, 40, val_at=(0, 23.5), part="USB DAC · 헤드폰 앰프 (L51)", part_at=(0, 25.8))
    s.cable((31, 40), (31, 31), text="USB-C → X701 일자 젠더 → Pi 5 USB-A (허브 거치지 않음)", at=(18, 28.5), anchor="start")
    s.chg(14.4, 27.6, 31)      # △31 (2026-10-26): straight gender instead of the IH190 right-angle one
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
    s.text(18, 72, "W701: BC256 3 m를 반으로 자른 1.5 m (C14) — 잘린 끝을 J701에", "cabt", size=2.0)
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
    s.place(plug, "P702", "W702 플러그", 215, 40, ref_at=(0, -2.2), val_at=(0, 19.5), part="BC256 반쪽 (C14)", part_at=(0, 21.8))
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
    # △32 (2026-10-26): the user's HW-720 (TPA3118D2) - XH 3P input INR / GND / INL, DC 5.5x2.1 jack, screw terminals OUTL / OUTR
    amp = sym_box("HW-720", [("1", "INR"), ("2", "GND"), ("3", "INL"), None, ("4", "DC+"), ("5", "DC-")],
                  [("6", "OUTL+"), ("7", "OUTL-"), None, ("8", "OUTR+"), ("9", "OUTR-")], width=24, cls="mod", rows=6)
    ax, ay = 348, 40
    s.place(amp, "A702", "HW-720 (사용자 보유)", ax, ay, val_at=(0, 38.5), part="TPA3118D2 · BTL: 스피커 − 선을 GND에 묶지 않음", part_at=(-12, 40.8))
    s.chg(ax + 27.5, ay - 2.5, 32)
    for pin, net in (("3", "AMP_IN_L"), ("1", "AMP_IN_R")):
        x, y = s.pin("A702", pin)
        s.wire((x, y), (x - 7.5, y))
        s.label(x - 7.5, y, net, "L")
        exp_add(e, net, f"A702.{pin}")
    x, y = s.pin("A702", "2"); s.wire((x, y), (x - 7.5, y)); s.label(x - 7.5, y, "AGND", "L"); exp_add(e, "AGND", "A702.2")
    s.chg(x - 27, y - 1.5, 10)
    x, y = s.pin("A702", "4"); s.wire((x, y), (x - 10, y)); s.pwr(x - 10, y, "+12V8"); exp_add(e, "+12V8", "A702.4")
    x, y = s.pin("A702", "5"); s.wire((x, y), (x - 3.5, y)); s.pwr(x - 3.5, y, "GND"); exp_add(e, "GND", "A702.5")
    for pin, net in (("6", "SPK_L_P"), ("7", "SPK_L_N"), ("8", "SPK_R_P"), ("9", "SPK_R_N")):
        x, y = s.pin("A702", pin)
        s.wire((x, y), (x + 5, y))
        s.label(x + 5, y, net, "R")
        exp_add(e, net, f"A702.{pin}")
    s.text(316.5, 64.5, "+12V8: SCH-06", "notes", size=1.9)
    s.text(316.5, 67.1, f"PVCC {BATT['v_min']:.0f}~{BATT['v_max']} V (전지)", "notes", size=1.9)
    s.chg(339.5, 61.5, 17)
    # speakers
    s.box(14, 150, 216, 80, "스피커 파트 연결 (R26: XT60 꽂았다 뺌 △18, D13: 직렬 콘덴서 없음)")
    for i, (side, pnet, nnet, xm, xf_, ls) in enumerate((("L", "SPK_L_P", "SPK_L_N", "X703", "X704", "LS701"),
                                                          ("R", "SPK_R_P", "SPK_R_N", "X705", "X706", "LS702"))):
        y0 = 165 + i * 32
        # △18: XT60 like the battery; blue heat-shrink + "SPK" (power XT60s are red, see note 8)
        s.place(sym_conn("XT60-M", 2, side="L", width=6, rev=True), xm, "XT60 수 SPK", 70, y0, ref_at=(0, -2.2), val_at=(-16, 14.5),
                meta=dict(bomkey="XT60M_SPK"))
        s.place(sym_conn("XT60-F", 2, side="R", width=6, rev=True), xf_, "XT60 암 SPK", 77.5, y0, ref_at=(0, -2.2), val_at=(1, 14.5),
                meta=dict(bomkey="XT60F_SPK"))
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
        if i == 0:
            s.chg(90.0, y0 - 4.5, 18)
        _sl, _pg = HN.L("SPK-" + side), HN.L("PIG-" + side)
        s.text(20, y0 + 19.5, (f"W70{3+2*i}: 앰프 → XT60 수 경로 {_sl:.0f} mm · W70{4+2*i}: XT60 암 → 유닛 {_pg:.0f} mm (CAD, BRD-05)"
                               if _sl else f"W70{3+2*i} · W70{4+2*i}: BRD-05"), "cabt", size=2.0)
    s.para(240, 150, [
        "주",
        "1. 동글 A701은 젠더 X701로 Pi 5 USB-A에 직결(허브 경유 금지). ALSA hw:CARD=<이름>,DEV=0, 48 kHz 전용(D7).",
        "2. J701(왼쪽 볼): 동글 신호가 T·R 스프링으로, TN·RN 노멀이 앰프로. 헤드폰을 꽂으면 노멀이 떨어진다(R15).",
        "    ‘PJ-313’ 이름만으로 노멀 접점·핀 번호가 보장되지 않는다 → 도착 즉시 통전 검사(플러그 없음: T–TN, R–RN 닫힘).",
        "3. HPF: 1 µF ×2 병렬(2 µF) 직렬 + 1 kΩ 병렬. 보드 입력(볼륨 + 이득 저항, 미공개)과 겹쳐 fc ≈ 80~93 Hz.",
        "    △10 AGND: 잭 슬리브·1 kΩ는 앰프 XH GND 핀으로만 모은다.",
        f"4. △32 A702 = HW-720(TPA3118D2), 이득은 보드 저항으로 정해져 미공개. △17 PVCC {BATT['v_nom']} V(전지): 8 Ω에서 약 {BATT['amp_w_ch']:.0f} W/ch.",
        "    동글은 0.5~1 Vrms라 소프트웨어 음량 상한 필수 — 최대 출력에서 찌그러지지 않게 ALSA Headphone·FluidSynth synth.gain 상한 + synth.limiter.",
        "    보드 볼륨(칩 앞): 뚜껑을 열고 노브를 꽂아 낮게 시작해 한 번 맞춘 뒤 노브를 뺀다(꽂아 두면 z62.5 > 뚜껑 밑 z61.35). 스피커 25 W 보호(D18).",
        "5. XT60(△18, 전지와 같은 커넥터): KiCad 패드 1 = −, 2 = + (실물 +/− 표시로 확인). 좌우 같은 방향으로 납땜해 위상을 맞춘다.",
        "6. BTL: OUTL−·OUTR−를 GND나 서로에 묶지 않는다. 스피커선은 쌍마다 꼬고 리본·EXT 선에서 30 mm 이상(D14).",
        "7. 스피커 Re를 잰다: 6~7 Ω = 8 Ω 유닛, 3~3.5 Ω면 4 Ω 판매분(출력·발열 재검토).",
        "8. △18 잘못 꽂기 방지: 커넥터가 모두 XT60이라 전지·벤치 12 V를 스피커 XT60에 꽂을 수 있다 → 12.8 V DC가",
        "    BTL 출력·보이스 코일에 걸림(6.2 Ω에 약 2 A, 스피커 과열). 전원 XT60(팩 리드·W601·벤치 L81) = 빨강 수축,",
        f"    스피커 XT60(X703~X706) = 파랑 수축 + ‘SPK’. W601은 홀더 끝에서 XT60 뒤끝까지 {HN.W601_MAX} mm 이하라 왼쪽 집게({HN.W601_NEED_L:.1f} mm)까지 닿지 않는다.",
        "    스피커 XT60에 전원을 꽂지 않는다. XT60 정격(30 A)은 스피커 전류보다 훨씬 커서 전기적 손해는 없다.",
    ], size=2.2)
    s.frame()
    s.expected = e
    return s


SHEETS.append(sch07)


# ------------------------------------------------------------------ board placement helpers
def grid(i0, n, x0=0.63, p=2.54):
    return [x0 + p * (i0 + k) for k in range(n)]


# ------------------------------------------------------------------ control board MB (△33, 2026-10-31 = CAD A16)
# The user (2026-10-31): "80 120 으로 설계를 다시 만들어줄 수 있어? ... 기판을 바닥으로 내려도 돼". MB is now the WHOLE 80 x 120 double-sided
# perfboard - uncut, undrilled, no screws - lying in a pocket on the module floor under the keys (CAD keyaction.py A16, spec
# electronics_modules.json mb_board); the separately printed balance rail lies on its bare strip and holds it down. SCH-03 (the netlist)
# is unchanged: only placement, routing, drawings, 3D model and texts. Module-local mm: x across, y from the white-key front lip, z from
# the desk.
MB = dict(x0=22.25, x1=142.25, y0=93.3, y1=173.3, zb=7.0, zt=8.6,      # outline; underside on the floor ribs z5~7.0 (2.0 over the
          floor=5.0,                                                  # floor z5.0: room for two crossing ribbon strands), top z8.6
          strip=(132.0, 144.8),                                       # balance rail y132.3~144.5 + 0.3: no parts, pads or top wires
          rail=(1.45, 163.05, 132.3, 144.5, 8.6, 19.0),               # the separate rail print (context), bottom = board top
          front=(93.3, 132.0), rear=(144.8, 173.3), zmax=(17.27, 20.9),   # zones and their part height limits (keys above)
          # printed support ribs under the board (z5~7.0): no solder joint and no wire on them
          ribs=[(22.45, 59.5, 93.5, 95.4), (81.5, 142.05, 93.5, 95.4),          # front rib, gap x59.5~81.5 for the ribbon
                (22.45, 142.05, 171.2, 173.1),                                  # rear rib
                (22.45, 28.8, 93.5, 173.1), (135.7, 142.05, 93.5, 173.1),       # side ribs
                (28.8, 92.0, 132.8, 144.0), (114.0, 135.7, 132.8, 144.0)],      # rib under the rail strip, ONE crossing gap
          front_gap=(59.5, 81.5), gap=(92.0, 114.0),
          lips=(8.5, 0.3),                                            # edge lips of the pocket: top z8.5, 0.3 clearance
          fins=[(40.76, 42.56), (123.03, 124.83)], fin_y=(144.5, 174.9), fin_z=9.5,   # cage fins 2 / 4 lowered over the board
          ffs=(82.42, 84.22, 144.5, 209.0, 18.0),                     # F|F# fin over the Zero and the USB plug: x, y, lower edge z
          ribbon=(59.0, 81.1, 98.3),                                  # flat ribbon + strand fan under the front edge: x0, x1, y<=
          tails=1.0,                                                  # every lead / pin tail <= 1.0 below the board (z >= 6.0)
          strand=0.9)                                                 # underside wire = a single 2651 ribbon strand (OD ~0.9)
# hole lattice: BE163 30 x 42 holes, assumed centred (margins 7.93 / 3.17). Pads only on i = 1..40, j = 1..28, so a 28 x 40 board
# (the 8 x 12 cm boards bought for the rest) gives the same layout about the board centre (82.25, 133.3).
LAT_X, LAT_Y = 30.18, 96.47
LAT_N = (42, 30)
LAT_USE = (1, 40, 1, 28)
ZONE_J = dict(front=(1, 13), strip=(14, 19), rear=(20, 28))
FIN_I = (4, 5, 36, 37)                # no top-side part in these columns of the rear zone (fins 2 / 4 at z9.5)


def lat(i):
    return round(LAT_X + 2.54 * i, 2)


def latj(j):
    return round(LAT_Y + 2.54 * j, 2)


def lat_ij(x, y):
    return int(round((x - LAT_X) / 2.54)), int(round((y - LAT_Y) / 2.54))


# RP2040-Zero A301: USB-C toward +y, on standard headers WITH the 2.5 mold (PCB z11.1~12.1, underside chips 1.2 above the board)
ZX, ZY = 74.52, 169.18               # left edge, USB edge
ZERO_ORIGIN = (ZX, ZY)               # module-local (0,0) = top-left at the USB edge; local +y -> board -y
USB_RX = (78.91, 87.85)              # receptacle 8.94 wide, 4.67 from the right edge (Waveshare): centre x83.38
USB_RY = (163.18, 170.48)            # protrudes ~1.3 past the Zero edge (1.0~1.5, check on the part)
PLUG = (77.13, 89.63, 170.48, 195.48, 9.9, 17.5)    # cable overmold limit 12.5 x 25 x 7.6 (centre x83.38 z13.7)
WALL_OPEN = (76.45, 91.55)           # rear-wall opening: the USB cable and the EXT lead leave the module here
# A302 4067 module: long axis +x, channel row in front (C0 at the left), control row behind it
MUX_ORIGIN = (82.25, 100.28)         # module corner (C0 end, front edge)
MUX_W, MUX_D = 40.64, 17.78
RIB_X0, RIB_Y = lat(12), (latj(1), latj(2))       # J301 2x8: odd pins front row y99.01, even back row y101.55, x60.66~78.44
RIB_C = round(RIB_X0 + 3.5 * 2.54, 2)             # J301 centre x69.55 (the ribbon runs centred x70.48 like SB J201)
EXT_X0, EXT_Y = lat(27), latj(28)                 # J302 1x6 along x, pin 1 = GND at the left, soldered from the top
# ID / PED jumpers: (signal pad, GND pad) - two-hole solder bridges on the underside
JP_PADS = {"JP301": ((lat(26), latj(22)), (lat(27), latj(22))), "JP302": ((lat(26), latj(21)), (lat(27), latj(21))),
           "JP303": ((lat(26), latj(20)), (lat(27), latj(20))), "JP304": ((lat(16), latj(20)), (lat(15), latj(20)))}
R_EXT = {f"R{300+n}": (lat(29), latj(29 - 2 * n)) for n in range(1, 5)}   # 100k pull-downs lying flat, pin 1 left, 7.62 pitch
TP_POS = {"TP301": (lat(14), latj(27)), "TP302": (lat(15), latj(27)), "TP303": (lat(16), latj(27))}


def f2(v):
    return f"{v:.2f}"


MBX = dict(board=f"x{f2(MB['x0'])}~{f2(MB['x1'])} × y{MB['y0']}~{MB['y1']}",
           mux=f"x{f2(MUX_ORIGIN[0])}~{f2(MUX_ORIGIN[0] + MUX_W)} × y{f2(MUX_ORIGIN[1])}~{f2(MUX_ORIGIN[1] + MUX_D)}",
           rib=f"x{f2(RIB_X0)}~{f2(RIB_X0 + 7 * 2.54)} × y{f2(RIB_Y[0])}/{f2(RIB_Y[1])}",
           ext=f"x{f2(EXT_X0)}~{f2(EXT_X0 + 5 * 2.54)} × y{f2(EXT_Y)}",
           zero=f"x{f2(ZX)}~{f2(ZX + 18)} × y{f2(ZY - 23.5)}~{f2(ZY)}",
           usb=f"x{f2(USB_RX[0])}~{f2(USB_RX[1])} × y{f2(USB_RY[0])}~{f2(USB_RY[1])}",
           rext=f"x{f2(lat(29))}→{f2(lat(29) + 7.62)} × y{f2(latj(21))}~{f2(latj(27))}",
           jp=f"x{f2(lat(26))}/{f2(lat(27))} × y{f2(latj(20))}~{f2(latj(22))} · JP304 x{f2(lat(16))}/{f2(lat(15))}",
           tp=f"x{f2(lat(14))}~{f2(lat(16))} × y{f2(latj(27))}")


def zero_hole(n):
    lx, ly = P.RP2040_HOLE[n]
    return round(ZERO_ORIGIN[0] + lx, 2), round(ZERO_ORIGIN[1] - ly, 2)


def mux_hole(name):
    """4067 module pin -> board xy: u along +x and w along +y from the module corner (channel row C0..C15, control row behind)."""
    n = P.mux_pin(name)
    if n <= 16:
        u, w = 1.27 + 2.54 * (n - 1), 1.27
    else:
        u, w = 11.43 + 2.54 * (n - 17), 16.51
    return round(MUX_ORIGIN[0] + u, 2), round(MUX_ORIGIN[1] + w, 2)


def jp_hole(ref, net):
    sig, gnd = JP_PADS[ref]
    return gnd if net == "GND" else sig


def mb_pad_xy(ref, num, net=None):
    """board xy of one MB pad (SCH-03 ref / pin), None for parts without a pad (C301 sits across the mux GND / VCC tails)."""
    if ref == "A301":
        return zero_hole(int(num))
    if ref == "A302":
        return mux_hole(dict(P.MUX_CH + P.MUX_CTRL)[int(num)])
    if ref == "J301":
        n = int(num)
        return round(RIB_X0 + 2.54 * ((n - 1) // 2), 2), RIB_Y[(n - 1) % 2]
    if ref == "J302":
        return round(EXT_X0 + 2.54 * (int(num) - 1), 2), EXT_Y
    if ref in JP_PADS:
        return jp_hole(ref, net)
    if ref in R_EXT:
        x, y = R_EXT[ref]
        return (x, y) if str(num) == "1" else (round(x + 7.62, 2), y)
    if ref in TP_POS:
        return TP_POS[ref]
    return None


def _tx(s, x, y, txt, cls="pinname", anchor="start", fs=None, layer="text"):
    """small label with an explicit font size (the sheet CSS classes have fixed sizes); not in the overlap check."""
    import html as _h
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    st = f' style="font-size:{fs}px"' if fs else ""
    s.out[layer].append(f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}"{a}{st}>{_h.escape(str(txt))}</text>')


def _hatch(o, x0, y0, x1, y1, step=3.0, col="#c2410c", w=.25, op=.45):
    """45 degree hatch lines clipped to a sheet rectangle (x0 < x1, y0 < y1)."""
    h = y1 - y0
    t = x0 - h
    while t < x1:
        ax, ay, bx, by = t, y1, t + h, y0
        if ax < x0:
            ay -= x0 - ax
            ax = x0
        if bx > x1:
            by += bx - x1
            bx = x1
        if bx > ax:
            o.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}"/>')
        t += step


def mb_frame_draw(s, X, Y, mirror=False, top=True):
    """common MB context for BRD-01 (top view) / BRD-08 (underside, mirrored): board, lattice, rail strip, ribs, fins."""
    o = s.out["body"]
    x0b, x1b, y0b, y1b = MB["x0"], MB["x1"], MB["y0"], MB["y1"]

    def R(a0, a1, b0, b1):                   # model rect -> sheet rect (x, y, w, h)
        xa, xb = sorted((X(a0), X(a1)))
        ya, yb = sorted((Y(b0), Y(b1)))
        return xa, ya, xb - xa, yb - ya
    x, y, w, h = R(x0b, x1b, y0b, y1b)
    o.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    i0, i1, j0, j1 = LAT_USE
    for i in range(LAT_N[0]):
        for j in range(LAT_N[1]):
            used = i0 <= i <= i1 and j0 <= j <= j1
            o.append(f'<circle cx="{X(lat(i)):.2f}" cy="{Y(latj(j)):.2f}" r=".32" fill="{"#b9cdb6" if used else "#dbe7d8"}"/>')
    # balance-rail strip (top side): hatched, no parts / pads / top wires; the rail outline itself dashed
    sy0, sy1 = MB["strip"]
    x, y, w, h = R(x0b, x1b, sy0, sy1)
    o.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#fde2d8" fill-opacity=".55"/>')
    _hatch(o, x, y, x + w, y + h)
    rx0, rx1, ry0, ry1 = MB["rail"][:4]
    ext = 4.0 / 2.0
    x, y, w, h = R(max(rx0, x0b - ext), min(rx1, x1b + ext), ry0, ry1)
    o.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="none" stroke="#6b7690" stroke-width=".45" stroke-dasharray="2.4 1.2"/>')
    # support ribs under the board (dashed = hidden on the top view)
    dash_r = ' stroke-dasharray="1.6 .9"' if top else ""
    op_r = .10 if top else .22
    for (a0, a1, b0, b1) in MB["ribs"]:
        x, y, w, h = R(a0, a1, b0, b1)
        o.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#6b7690" fill-opacity="{op_r}" '
                 f'stroke="#6b7690" stroke-width=".3"{dash_r}/>')
    # frame fins over the board: fins 2 / 4 lowered to z9.5 behind the rail, the F|F# fin at z18.0
    fy0, fy1 = MB["fin_y"]
    dash_f = "" if top else ' stroke-dasharray="1.2 .7"'
    op_f = .55 if top else .25
    for (a0, a1) in MB["fins"]:
        x, y, w, h = R(a0, a1, fy0, min(fy1, y1b + 7.8))
        o.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#9aa6b8" fill-opacity="{op_f}" '
                 f'stroke="#6b7690" stroke-width=".3"{dash_f}/>')
    fa, fb, fc, fd, fz = MB["ffs"]
    x, y, w, h = R(fa, fb, fc, min(fd, y1b + 7.8))
    o.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#9aa6b8" fill-opacity=".22" stroke="#6b7690" '
             f'stroke-width=".3" stroke-dasharray="1.6 .8"/>')


def brd01():
    import harness as _H
    s = Sheet("BRD-01", 8, TOTAL, "제어 기판 배치 (MB · 위에서 봄)",
              "양면 만능기판 80 × 120 통째로(자르지 않음, 구멍·나사 없음): 모듈 바닥 자리에 놓고 따로 출력한 밸런스 레일이 맨 띠를 눌러 잡는다(CAD A16). "
              "부품 자리·구멍 좌표(모듈 좌표 mm). 아랫면 배선은 BRD-08.",
              "MB", qty="MB × 7", basis="CAD A16 · W1 r4.5", **REV_E)
    S_ = 2.0
    ox, oy = 26.0, 40.0
    x0b, y0b, y1b = MB["x0"], MB["y0"], MB["y1"]
    YT = y1b + 8.0                     # top of the drawing (behind the board's rear edge)

    def X(x):
        return ox + (x - x0b) * S_

    def Y(y):
        return oy + (y1b - y) * S_
    o = s.out["body"]
    mb_frame_draw(s, X, Y)
    s.chg(X(x0b) + 4.5, Y(y1b) + 4.5, 33)
    # ---- labels of the frame context
    _tx(s, X(x0b) + 1.5, Y(139.9), "밸런스 레일 (따로 출력, 점선 y%.1f~%.1f · z%.1f~%.1f, M3×6 ×2는 기판 밖 x11.2 / 154.2)" % MB["rail"][2:], "notes", fs=1.9)
    _tx(s, X(x0b) + 1.5, Y(137.1), "맨 띠 y132.0~144.8 (빗금, 줄 j 14~19): 부품·패드·윗면 선 없음 — 레일이 기판을 눌러 잡는다", "notes", fs=1.9)
    _tx(s, X(103.0), Y(134.2), "띠 리브 틈 x92.0~114.0: 앞↔뒤 아랫면 선 (BRD-08)", "notes", "middle", fs=1.7)
    _tx(s, X(x0b) + 1.5, Y(129.7), "앞 구역 j 1~13 (y99.01~129.49) · 부품 ≤ z17.27", "notes", fs=1.9)
    _tx(s, X(44.0), Y(158.0), "뒤 구역 j 20~28", "notes", fs=1.9)
    _tx(s, X(44.0), Y(156.3), "(y147.27~167.59)", "notes", fs=1.9)
    _tx(s, X(44.0), Y(154.6), "부품 ≤ z20.9", "notes", fs=1.9)
    _tx(s, X(x0b) + 1.5, Y(95.9), "받침 리브 (아랫면, 점선) — 납땜·선 없음, 모든 다리 끝 ≤ 1.0", "notes", fs=1.7)
    for (a0, a1), nm in zip(MB["fins"], ("핀 2", "핀 4")):
        anchor = "end" if a0 < 80 else "start"
        _tx(s, X(a0) - 1.2 if a0 < 80 else X(a1) + 1.2, Y(178.4), f"{nm} 밑변 z{MB['fin_z']:.1f} (y144.5~174.9)", "notes", anchor, fs=1.8)
        _tx(s, X(a0) - 1.2 if a0 < 80 else X(a1) + 1.2, Y(176.4), f"x{a0:.2f}~{a1:.2f} · 열 i {'4·5' if a0 < 80 else '36·37'} 윗면 부품 없음", "notes", anchor, fs=1.8)
    fa, fb = MB["ffs"][:2]
    _tx(s, X(90.4), Y(180.6), f"F|F# 핀 x{fa:.2f}~{fb:.2f} 밑변 z{MB['ffs'][4]:.1f} → y209 (제로·플러그 위)", "notes", fs=1.8)
    # ---- RP2040-Zero A301 (on headers with the 2.5 mold), USB-C receptacle, cable plug stub
    zx0, zy0 = ZERO_ORIGIN
    o.append(f'<rect x="{X(zx0):.2f}" y="{Y(zy0):.2f}" width="{18*S_:.2f}" height="{23.5*S_:.2f}" rx="2" fill="#1f2a44" fill-opacity=".08" stroke="#1f2a44" stroke-width=".45"/>')
    px0, px1, py0, py1 = PLUG[:4]
    o.append(f'<rect x="{X(px0):.2f}" y="{Y(YT):.2f}" width="{(px1-px0)*S_:.2f}" height="{(YT-py0)*S_:.2f}" fill="#2b2b2b" fill-opacity=".14" stroke="#2b2b2b" stroke-width=".35" stroke-dasharray="2 .8"/>')
    o.append(f'<polyline points="{X(px0)-1:.2f},{Y(YT)+1.2:.2f} {X((px0+px1)/2):.2f},{Y(YT)-0.4:.2f} {X(px1)+1:.2f},{Y(YT)+1.2:.2f}" fill="none" stroke="#2b2b2b" stroke-width=".3"/>')
    o.append(f'<rect x="{X(USB_RX[0]):.2f}" y="{Y(USB_RY[1]):.2f}" width="{(USB_RX[1]-USB_RX[0])*S_:.2f}" height="{(USB_RY[1]-USB_RY[0])*S_:.2f}" fill="#c9d0da" stroke="#1f2a44" stroke-width=".3"/>')
    _tx(s, X(px0) - 1.2, Y(175.2), "USB 플러그 몰드 ≤ 12.5 × 7.6 × 25", "notes", "end", fs=1.8)
    _tx(s, X(px0) - 1.2, Y(177.0), f"y{py0:.2f}~{py1:.2f} · z{PLUG[4]:g}~{PLUG[5]:g} → 뒷벽 개구 x{WALL_OPEN[0]:.2f}~{WALL_OPEN[1]:.2f}", "notes", "end", fs=1.8)
    _tx(s, X(83.38), Y(166.6), "USB-C", "notes", "middle", fs=1.7)
    s.text(X(zx0 + 9), Y(zy0 - 12.4), "A301", "ref", "middle", size=2.7, check=False)
    _tx(s, X(zx0 + 9), Y(zy0 - 14.3), "RP2040-Zero", "notes", "middle", fs=1.8)
    _tx(s, X(zx0 + 9), Y(zy0 - 16.0), "몰드 2.5 헤더 위", "notes", "middle", fs=1.7)
    used = ("3V3", "GND", "GP26", "GP2", "GP3", "GP4", "GP5", "GP6", "GP7", "GP8", "GP14")
    for n, nm in P.RP2040_ZERO:
        x, y = zero_hole(n)
        if n >= 19:
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".7" fill="#fff" stroke="#8a96ab" stroke-width=".25" stroke-dasharray=".5 .4"/>')
            continue
        fill = "#c2410c" if nm in used else "#fff"
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.05" fill="{fill}" stroke="#1f2a44" stroke-width=".3"/>')
        if n <= 9:
            _tx(s, X(x) - 1.8, Y(y) + 0.7, nm, "pinname", "end", fs=1.8)
        else:
            _tx(s, X(x) + 1.8, Y(y) + 0.7, nm, "pinname", "start", fs=1.8)
    # ---- A302 4067 module (long axis along x, channel row in front)
    mx0, my0 = MUX_ORIGIN
    o.append(f'<rect x="{X(mx0):.2f}" y="{Y(my0+MUX_D):.2f}" width="{MUX_W*S_:.2f}" height="{MUX_D*S_:.2f}" rx="1" fill="#1f5fbf" fill-opacity=".08" stroke="#1f5fbf" stroke-width=".45"/>')
    for nm in [f"C{i}" for i in range(16)] + ["GND", "VCC", "EN", "S0", "S1", "S2", "S3", "SIG"]:
        x, y = mux_hole(nm)
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.05" fill="#c2410c" stroke="#1f2a44" stroke-width=".3"/>')
        if nm.startswith("C"):
            _tx(s, X(x), Y(y) - 2.0, nm, "pinname", "middle", fs=1.7)
        else:
            _tx(s, X(x), Y(y) + 3.0, nm, "pinname", "middle", fs=1.7)
    s.text(X(mx0 + 20.3), Y(my0 + 9.0) + 0.3, "A302 4067 모듈", "ref", "middle", size=2.7, check=False)
    _tx(s, X(mx0 + 20.3), Y(my0 + 9.0) + 3.3, f"{MUX_W} × {MUX_D} · 채널 줄(C0~C15) 앞, 제어 줄 뒤", "notes", "middle", fs=1.8)
    gx_, gy_ = mux_hole("GND")
    vx_, _ = mux_hole("VCC")
    o.append(f'<rect x="{X(gx_)-1.6:.2f}" y="{Y(gy_)-1.9:.2f}" width="{(vx_-gx_)*S_+3.2:.2f}" height="3.8" fill="none" stroke="#b86e00" stroke-width=".4" stroke-dasharray=".9 .5"/>')
    _tx(s, X(gx_) - 1.6, Y(gy_) + 6.0, "C301 (아랫면, 점선)", "notes", "start", fs=1.7)
    # ---- J301 ribbon 2x8 (soldered from below), the ribbon under the front edge
    for n in range(1, 17):
        x, y = mb_pad_xy("J301", n)
        o.append(f'<rect x="{X(x)-1.2:.2f}" y="{Y(y)-1.2:.2f}" width="2.4" height="2.4" fill="#fff" stroke="#8a5a00" stroke-width=".35"/>')
        _tx(s, X(x), Y(y) + (3.9 if n % 2 else -1.9), str(n), "pinnum", "middle", fs=1.6)
    rb0, rb1 = 70.48 - 10.16, 70.48 + 10.16
    o.append(f'<rect x="{X(rb0):.2f}" y="{Y(MB["ribbon"][2]):.2f}" width="{(rb1-rb0)*S_:.2f}" height="{(MB["ribbon"][2]-y0b)*S_:.2f}" fill="#c9d0da" fill-opacity=".35" stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.4 .8"/>')
    o.append(f'<rect x="{X(rb0):.2f}" y="{Y(y0b):.2f}" width="{(rb1-rb0)*S_:.2f}" height="{9.0:.2f}" fill="#c9d0da" fill-opacity=".7" stroke="#6b7690" stroke-width=".3"/>')
    o.append(f'<line x1="{X(rb0):.2f}" y1="{Y(y0b)+0.4:.2f}" x2="{X(rb0):.2f}" y2="{Y(y0b)+9.0:.2f}" stroke="#c0392b" stroke-width=".8"/>')
    _tx(s, X(70.48), Y(y0b) + 5.4, "리본 W10x ← SB J201 (바닥, 앞 리브 틈 x59.5~81.5)", "cabt", "middle", fs=1.8)
    _tx(s, X(RIB_X0) - 2.2, Y(RIB_Y[0]) + 0.2, "J301", "ref", "end", fs=2.2)
    _tx(s, X(RIB_X0) - 2.2, Y(RIB_Y[0]) + 2.6, "아랫면에서 꽂음", "notes", "end", fs=1.7)
    # ---- EXT 100k pull-downs (lying flat, 7.62 pitch)
    for ref, (x, y) in R_EXT.items():
        extra = ' stroke-dasharray=".8 .5" fill-opacity=".4"' if ref == "R304" else ""
        o.append(f'<rect x="{X(x)+1.6:.2f}" y="{Y(y)-1.25:.2f}" width="{7.62*S_-3.2:.2f}" height="2.5" rx=".8" fill="#f3e3c3" stroke="#8a5a00" '
                 f'stroke-width=".3"{extra}/>')
        for xx in (x, x + 7.62):
            o.append(f'<circle cx="{X(xx):.2f}" cy="{Y(y):.2f}" r="1.05" fill="#c2410c" stroke="#1f2a44" stroke-width=".3"/>')
        n = int(ref[1:]) - 300
        _tx(s, X(x + 7.62) + 1.8, Y(y) + 0.7, f"{ref} EXT{n}" + (" 비움" if ref == "R304" else ""), "pinname", "start", fs=1.7)
    # ---- ID / PED jumpers, test points
    for ref, (sig, gnd) in JP_PADS.items():
        o.append(f'<circle cx="{X(sig[0]):.2f}" cy="{Y(sig[1]):.2f}" r="1.05" fill="#c2410c" stroke="#1f2a44" stroke-width=".3"/>')
        o.append(f'<circle cx="{X(gnd[0]):.2f}" cy="{Y(gnd[1]):.2f}" r="1.05" fill="#1d2433" stroke="#1f2a44" stroke-width=".3"/>')
        if ref == "JP304":
            _tx(s, X(gnd[0]) - 1.8, Y(gnd[1]) + 0.7, "JP304", "pinname", "end", fs=1.7)
        else:
            _tx(s, X(gnd[0]) + 1.8, Y(gnd[1]) + 0.7, ref, "pinname", "start", fs=1.7)
    for ref, (x, y) in TP_POS.items():
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.45" fill="#fff" stroke="#1f5fbf" stroke-width=".5"/>')
    _tx(s, X(TP_POS["TP301"][0]) - 1.2, Y(TP_POS["TP301"][1]) - 2.3, "TP301 · 302 · 303", "pinname", "start", fs=1.7)
    # ---- J302 EXT pads (O1 / O7), the lead from the top over the rear edge
    for i in range(6):
        x = EXT_X0 + 2.54 * i
        o.append(f'<rect x="{X(x)-1.3:.2f}" y="{Y(EXT_Y)-1.3:.2f}" width="2.6" height="2.6" fill="#fff" stroke="#8a5a00" stroke-width=".35"/>')
        o.append(f'<line x1="{X(x):.2f}" y1="{Y(EXT_Y)-1.3:.2f}" x2="{X(x):.2f}" y2="{Y(y1b):.2f}" stroke="#7e889a" stroke-width=".45"/>')
    s.cable((X(105.11), Y(y1b)), (X(105.11), Y(176.6)), (X(86.5), Y(176.6)), (X(86.5), Y(YT)))
    _tx(s, X(106.4), Y(178.7), "W403·W413 (O1·O7) → 뒷벽 개구 (주 8)", "cabt", "start", fs=1.7)
    _tx(s, X(EXT_X0 + 5 * 2.54) + 2.4, Y(EXT_Y) + 0.7, "J302 1 = GND … 6 = 3V3 (윗면 납땜)", "pinname", "start", fs=1.7)
    # ---- rulers
    for x in (22.25, 30.18, 60.66, 74.52, 82.25, 92.0, 114.0, 122.89, 142.25):
        s.line(X(x), Y(y0b) + 9.6, X(x), Y(y0b) + 12.2, "bodyl", "text")
        _tx(s, X(x), Y(y0b) + 14.6, f"x{x:g}", "tblm", "middle", fs=1.7)
    for y in (93.3, 99.01, 101.55, 116.79, 132.0, 144.8, 147.27, 167.59, 173.3):
        s.line(X(x0b) - 1.0, Y(y), X(x0b) - 3.2, Y(y), "bodyl", "text")
        _tx(s, X(x0b) - 3.8, Y(y) + 0.6, f"y{y:g}", "tblm", "end", fs=1.7)
    _tx(s, X(x0b), Y(YT) + 2.0, "뒤 (+y) — USB 케이블 · 뒷벽 쪽", "notes", fs=2.0)
    _tx(s, X(x0b), Y(y0b) + 18.6, "앞 (−y, 연주자 쪽) — 기판 앞 모서리 y93.3 = 검은 건반 탭 받침 뒤 0.3", "notes", fs=2.0)
    # ---- placement table + notes
    rows = [["MB 기판", MBX["board"], "통째로 80 × 120", "구멍·나사 없음"],
            ["A301 RP2040-Zero", MBX["zero"], "핀 i 18·24, j 20~28", "USB-C +y, 몰드 그대로"],
            ["USB-C 리셉터클", MBX["usb"], "가운데 x83.38", "플러그 → 뒷벽 개구"],
            ["A302 4067 모듈", MBX["mux"], "채널 j 2 · 제어 j 8", "C0 왼쪽, 채널 줄 앞"],
            ["J301 리본 2×8", MBX["rib"], "i 12~19, j 1·2", "1 = 앞줄 왼쪽, 아랫면"],
            ["J302 EXT 1×6", MBX["ext"], "i 27~32, j 28", "O1·O7, 윗면 납땜"],
            ["R301~R304", MBX["rext"], "i 29→32, j 27~21", "누워서, R304 비움"],
            ["JP301~JP303", f"x{f2(lat(26))}/{f2(lat(27))} × y{f2(latj(20))}~{f2(latj(22))}", "i 26·27, j 22~20", "왼쪽 = 신호(GP6~8)"],
            ["JP304", f"x{f2(lat(16))}/{f2(lat(15))} × y{f2(latj(20))}", "i 16·15, j 20", "GP14, 열어 둠"],
            ["TP301~303", MBX["tp"], "i 14~16, j 27", "3V3 · GND · SIG"],
            ["C301 (아랫면)", f"x{f2(mux_hole('GND')[0])}~{f2(mux_hole('VCC')[0])} × y{f2(mux_hole('GND')[1])}", "먹스 GND–VCC", "1206 100 nF"]]
    yt = s.table(272, 24, ["부품", "자리 (모듈 좌표)", "격자", "메모"], rows, [25, 46, 31, 36],
                 title="배치표 (격자 x = 30.18 + 2.54·i, y = 96.47 + 2.54·j)")
    s.para(272, yt + 5.5, [
        "주",
        "1. 기판: 양면 만능기판 80 × 120을 자르지 않고 통째로 (Coms BE163 30 × 42 구멍 —",
        "    가진 4장 + 8 × 12 양면 3장, 구매 목록 SE8b). 구멍을 뚫지 않고 나사도 없다. 외곽 x22.25~142.25 ×",
        "    y93.3~173.3. 격자는 BE163 구멍이 판 가운데라고 가정(가장자리 7.93 / 3.17).",
        "    부품은 i 1~40, j 1~28만 → 28 × 40 구멍 판도 가운데 (82.25, 133.3)에 맞추면 같은 배치.",
        "    받으면 판 크기·구멍 수·첫 구멍 위치를 잰다.",
        "2. 놓기 (CAD A16): 모듈 바닥 자리(받침 리브 z5~7.0 + 가장자리 턱 z8.5, 틈 0.3)에 내려놓고",
        "    따로 출력한 밸런스 레일을 맨 띠 위에 얹어 M3×6 ×2(레일 양 끝, 기판 밖)로 조인다.",
        "3. 높이: 기판 z7.0~8.6. 앞 구역 부품 ≤ z17.27(흑건 끝까지 눌렀을 때 건반 밑 z17.77 − 0.5; 먹스 핀 끝 z17.1),",
        "    뒤 구역 ≤ z20.9(건반 꼬리 z21.4 − 0.5). 프레임 핀 2·4는 뒤 구역 위에서 밑변 z9.5 →",
        "    열 i 4·5 · 36·37에는 윗면 부품 없음. F|F# 핀은 밑변 z18.0(제로 윗면 ≤ z15.5, 플러그 ≤ z17.5).",
        "4. 아랫면: 바닥까지 2.0 (z5~7.0). 모든 다리·핀 끝을 1.0 이하로 자른다(z ≥ 6.0).",
        "    받침 리브(점선) 위에는 납땜·선이 없다. 앞↔뒤 아랫면 선은 띠 리브의 틈 x92.0~114.0으로만.",
        "    아랫면 선은 2651 리본 가닥(바깥 지름 약 0.9) — 직각으로 겹치는 곳도 두 겹 1.8 < 2.0 (BRD-08).",
        "5. A301: USB-C +y, 왼쪽 핀 i 18 (1~9 = 5V·GND·3V3·GP29~26·GP15·GP14, USB 쪽부터),",
        "    오른쪽 i 24 (10~18 = GP0~GP8), 줄 j 28 (y167.59) ~ 20. 몰드 2.5가 그대로인 보통 헤더 위:",
        "    PCB z11.1~12.1, 밑면 칩·수정·LDO는 기판에서 1.2 떠 캡톤이 필요 없다. 아래 줄(GP9~13) 헤더 없음.",
        "    리셉터클은 제로 가장자리 밖 약 1.3(1.0~1.5, 실물로 확인) → 플러그 면 y170.48.",
        "6. A302: 긴 쪽을 x로, 채널 줄(C0~C15) 앞. C301 100 nF 1206은 아랫면 GND–VCC 꼬리 사이.",
        "7. J301: 리본은 SB J201에서 바닥을 따라 와 앞 리브 틈으로 기판 앞 모서리 밑을 지나",
        "    아랫면에서 구멍에 꽂고 윗면에서 납땜(이음 ≤ z10.0). 리본 가운데 x70.48, J301 가운데 x69.55 →",
        "    끝 약 6 mm만 가닥을 갈라 −0.93 비껴 꽂는다. 리본 자리(y ≤ 98.3)에는 아랫면 선이 없다.",
        "8. J302 (O1·O7만): 연장선 W403·W413을 윗면에서 납땜 → 기판 뒤 모서리·뒤 턱 위로 →",
        f"    바닥 → 기판 뒤를 −x → USB 플러그 밑(z9.9 아래) → 뒷벽 개구 (자름 W403 {_H.EXT_CUT['O1']} · W413 {_H.EXT_CUT['O7']} mm, BRD-06).",
        "9. R301~R304 100k: 붙여 눕힘(몸통 ≤ z11.1). O1·O7 = R301, O1은 R302·R303 더, R304는 비움.",
        "    ID 점퍼: O 번호에 맞춰 JP301~JP303 두 구멍 납땜 브리지(아랫면, 검정 = GND 쪽). JP304는 열림.",
        "10. 순서 (작업대): 아랫면 배선(BRD-08)·C301 → 헤더·모듈 → R30x·JP → SB·리본(70 mm)·MB를",
        "    한 묶음으로 납땜 → 다리 끝 ≤ 1.0 확인 → 모듈 바닥 자리에 MB를 놓고 남는 리본은 기판 앞",
        "    검은 건반 탭 받침 사이 바닥에 평평하게 접는다 → 밸런스 레일을 얹어 조인다.",
        "11. 건반을 뺀 칸의 레버가 떨어지는 곳 (CAD A16 확인, O1, 레버 봉을 축으로 처음 닿을 때까지):",
        "    C·B → 바닥틀 30.3°, C#·D·D#·E·G#·A·A# → 맨 기판 윗면 26~26.5° (y약 155.5),",
        "    F·F# → 제로 헤더 핀 끝 16.3~16.8° (핀을 자르면 제로 윗면 부품 약 18°),",
        "    G → R303 23.0° (O1만 — O7은 R301이 더 뒤라 안 닿음). 힘 약 0.4 N이라 문제없음:",
        "    R30x는 기판에 붙여 눕히고 리드를 짧게 납땜한다.",
    ], size=2.05)
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
        s.text(X(jx[0]) - 1.5, Y(75.89) - 6.0, f"{B['jref']} 리드 패드 ×{len(jx)} (1 GND … {len(jx)} 3V3)", "cabt", size=1.9, check=False)
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
              "SB · EL · ER", qty="SB × 7 · EL × 1 · ER × 1", basis="v4 W1+ r4.5", **REV_E)
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
    s.text(X(61.59), Y(75.89) - 6.5, "J201 리본 2×8 (x61.6~79.4, y72.08/74.62, 아랫면 납땜) → 뒤 받침 리브 틈 → 바닥 → MB J301 (△33)", "cabt", size=2.1)
    # right ledge (W1 r4.5 P36): two inverted-L pieces, lip x161.5~163.0 over the bar end (z13.6~15.1), post x163.0~164.3 from the floor
    for (ya, yb) in ((59.0, 63.4), (70.6, 77.5)):
        o.append(f'<rect x="{X(161.5):.2f}" y="{Y(yb):.2f}" width="{1.5*S:.2f}" height="{(yb-ya)*S:.2f}" fill="#c9d0da" fill-opacity=".6" stroke="#6b7690" stroke-width=".3"/>')
        o.append(f'<rect x="{X(163.0):.2f}" y="{Y(yb):.2f}" width="{1.3*S:.2f}" height="{(yb-ya)*S:.2f}" fill="#9aa6b8" stroke="#6b7690" stroke-width=".3"/>')
    s.text(X(164.3), Y(58.5) + 16.5, "오른쪽 턱(W1 r4.5 P36): 립 x161.5~163.0 z13.6~15.1(바 끝 위 1.4), 기둥 x163.0~164.3 — 바를 1.5 왼쪽에 놓고 오른쪽으로 밀어 넣은 뒤 왼쪽 M3", "notes", "end", size=2.0)
    # OUT -> J201 wires (underside), from boards3.sb_rows() + route check
    import boards3
    boards3.draw_sb_routes(s, X, Y)
    s.board_check = ["SB: " + p for p in boards3.sb_check()]
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
        "5. 3V3·GND 버스 = 아랫면 주석선 x8.25~160.65. OUT → J201 피복 단선 12가닥(파란 점선) + △27 J201 전원 4가닥(빨강 J201.1·16 → 3V3, 검정 J201.2·15 → GND,",
        "    끝은 버스가 지나는 빈 구멍 ○에 버스와 함께 납땜) — wiring_SB.csv. J201: 홀수 = 앞줄 y72.08, 짝수 = 뒷줄 y74.62, x = 61.59 + 2.54·⌊(n−1)/2⌋.",
        "    OUT 선은 모두 y70.81 줄, 짝수행은 핀 옆 반 칸 기둥에서 앞줄을 건너 y73.35로 1.27만. 받침 리브(점선 띠) 위에는 선이 없고 뒤 리브 띠는 틈 x59~82에서만 건넌다.",
        "    확인: J201.1·16 ↔ U201 핀 1 = 0 Ω, J201.2·15 ↔ U201 핀 2 = 0 Ω, J201 핀 n ↔ 센서 OUT = 0 Ω.",
        "6. 리본 16심은 아랫면에서 2×8 블록에 납땜(선 n = 핀 n, 15 = GND, 16 = 3V3). IDC 2×8 헤더로 바꿔도 번호가 같다.",
        "    리본(중심 x70.48, x60.32~80.64)은 뒤 리브 틈 x59~82(양옆 1.32 / 1.36)로 바닥에 내려가 MB 앞 리브 틈 x59.5~81.5로 기판 밑에 들어간다(△33).",
    ], size=2.2)
    ep = _end_plans(s)
    s.regions["sb"] = (9.0, 20.0, 411.0, 166.5)
    s.regions["end"] = (9.0, 166.5, 411.0, 253.0)
    s.frame()
    s.expected = {}
    return s


SHEETS += [brd01, brd02]


# ------------------------------------------------------------------ SCH-01 (system interconnect)
# rev E: the cable list is built from harness.py (one source: CAD lengths + cut lengths), bought cables included
import harness as HN  # noqa: E402


def _wkey(c):
    import re
    m = re.match(r"[WX](\d+)([a-z]?)", c[0])
    return (0 if c[0].startswith("W") else 1, int(m.group(1)) if m else 999, m.group(2) if m else "")


def _cables(group_usb=False):
    """cable list rows. group_usb=True folds W201~W207 into one row (SCH-01 table; the per-W length is on the drawing)."""
    rows = []
    codes = lambda keys: " · ".join(dict.fromkeys(P.BOM[k.strip()][0] for k in keys.split("·") if k.strip() in P.BOM and P.BOM[k.strip()][0]))
    for h in HN.HARNESS:
        rows.append((h["id"], h["title"], h["cut_short"], h["a"][0], h["b"][0], "%d심" % len(h["cond"]), codes(h["bom"])))
    seen = set()
    for b in HN.BOUGHT:
        g = b.get("group") if group_usb else None
        if g:
            if g not in seen:
                seen.add(g)
                cnt = {}
                for bb in HN.BOUGHT:
                    if bb.get("group") == g:
                        cnt[bb["std_m"]] = cnt.get(bb["std_m"], 0) + 1
                txt = " · ".join("%s %s ×%d" % (HN.USB_MODEL[m].split()[-1], HN.m_txt(m), n) for m, n in sorted(cnt.items(), reverse=True))
                rows.append((g, "USB-A→C " + txt, "산 그대로", "허브 포트 3~9", "O1~O7 USB-C", "—", codes(b["bom"])))
            continue
        rows.append((b["id"], b["cable"].split(" (")[0], "산 그대로", b["a"].split(" (")[0], b["b"].split(" (")[0], "—", codes(b["bom"])))
    rows.sort(key=_wkey)
    return rows


CABLES = _cables()                   # one row per cable (cables.csv, page)
CABLES_SHEET = _cables(group_usb=True)


def sch01():
    s = Sheet("SCH-01", 1, TOTAL, "시스템 연결도 (배선 계통)",
              "모든 파트·보드와 그 사이 선(W 번호). 파트 사이는 모두 꽂았다 빼는 커넥터(R26). 회로는 SCH-02~07, 기판 BRD-01~03·07·08, 가운데 유닛 배선 BRD-04, 선 만들기 BRD-05·06.",
              "전체", qty="O1~O7 · EL · ER · PB · CU", basis="v4 W1+ r4.5 · R31 · R33", **REV_E)
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
        s.text(x + 21, 81.2, HN.m_txt(HN.USB_BUY.get(f"O{i+1}", 1.0)), "notes", size=2.0)
    blk(353, 26, 44, 30, "ER 오른쪽 끝", ["C8", "센서 1"])
    cab([(44, 36), (50, 36)])
    s.text(22, 62, "W401 → X401⇄X402 ← W403", "cabt", size=2.0)
    s.text(22, 64.8, "(O1 EXT = 먹스 C12~C14)", "notes", size=2.0)
    cab([(342, 36), (353, 36)])
    s.text(330, 62, "W413 → X412⇄X411 ← W411", "cabt", size=2.0)
    s.text(330, 64.8, "(O7 EXT = 먹스 C12)", "notes", size=2.0)
    # hub
    pm = HN.HUB_PORTS
    blk(50, 96, 300, 14, "A604 NEXTU 710U3 유전원 USB 허브 (L17) — 다운스트림 8: O1~O7 + PED",
        ["가운데 유닛 F칸 바닥, 뒤판에 붙임, 포트 앞쪽 (L2) · 업스트림 B·DC 잭 = −x 끝면",
         "포트 번호(−x부터 0~9): " + " · ".join("%d %s" % (v, k) for k, v in sorted(pm.items(), key=lambda kv: kv[1]))
         + " (0·1 비움) · 1개는 충전 전용 → 0·1번인지 확인, 쓰는 8개 포트 스위치 켬 (BRD-06 주 3)"])
    # PED
    blk(360, 72, 37, 22, "PB 페달 보드", ["RP2040-Zero", "'Toccata PED'"])
    cab([(378.5, 94), (378.5, 103), (350, 103)], "W208 " + HN.m_txt(HN.USB_BUY.get("PED", 0.5)), (362, 101.5))
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
    blk(241, 140, 50, 22, "CU 트레이", ["J702 앰프 입력 잭", "2 µF + 1 kΩ HPF (D18)", "A702 HW-720 (TPA3118D2)"])
    cab([(227, 150), (241, 150)], "W702", (229, 148.5))
    blk(310, 140, 38, 12, "LS701 왼쪽", ["CW-100B25 8 Ω"], "body")
    blk(310, 156, 38, 12, "LS702 오른쪽", ["CW-100B25 8 Ω"], "body")
    cab([(291, 146), (310, 146)], None)
    cab([(291, 160), (310, 160)], None)
    s.text(292, 138.5, "W703⇄W704", "cabt", size=2.0)
    s.text(292, 172.5, "W705⇄W706 (XT60 SPK)", "cabt", size=2.0)
    s.chg(325.0, 172.0, 18)
    # power
    blk(125, 180, 40, 16, "BT601 LiFePO4 전지", [f"{BATT['v_nom']} V 6 Ah · {BATT['wh']} Wh", "BMS 내장 · 뚜껑 L 밑", "XT60 암 → W601"])
    s.chg(161.0, 177.5, 17)
    blk(175, 180, 34, 16, "F601 5 A · SW601", ["ATO 퓨즈 · KCD1-104", "두 회로 나란히"])
    blk(220, 180, 38, 16, "A602 XL4016 → 5.1 V", ["★ 별 접지점 IN−"])
    cab([(165, 188), (175, 188)], None)
    cab([(209, 188), (220, 188)], None)
    s.text(206, 199.5, "+12V8", "cabt", size=2.0)
    cab([(214.5, 188), (214.5, 175), (266, 175), (266, 162)], "W602c +12V8 → 앰프", (230, 173.5))
    cab([(239, 196), (239, 202), (95, 202), (95, 170)], "W603 5.1 V → Pi USB-C", (120, 205))
    cab([(258, 188), (353, 188), (353, 110), (350, 110)], "W604 5.1 V → 허브 DC", (300, 186.5))
    s.text(16, 184.5, "충전: LiFePO4 충전기 → 팩 DC 잭 (연주 중 아님)", "cabt", size=2.2)
    cab([(16, 188), (125, 188)], None)
    s.text(16, 192.5, "벤치: 12 V SMPS → W601 XT60 (전지와 함께 꽂지 않음)", "notes", size=2.0)
    # cable schedule
    rows = [[c[0], c[1], c[2], c[3], c[4], c[5], c[6]] for c in CABLES_SHEET]
    n2 = 11                                   # rows that fit in table 2 above the title block
    n1 = len(CABLES_SHEET) - n2
    s.table(14, 212, ["W", "선", "자르는 길이 (mm)", "한쪽", "다른 쪽", "심", "구매 코드"], rows[:n1], [17, 66, 30, 30, 34, 11, 28],
            title="선 목록 (1/2) — 만드는 법·핀은 BRD-05·06", rh=3.0)
    rows2 = [[c[0], c[1], f"{c[3]} → {c[4]}", c[6]] for c in CABLES_SHEET[n1:]]
    s.table(248, 210, ["W", "선", "한쪽 → 다른 쪽", "코드"], rows2, [17, 62, 64, 17], title="선 목록 (2/2)", rh=3.0)
    s.frame()
    s.expected = {}
    s.cable_rows_2 = rows[n1:]
    return s


SHEETS.insert(0, sch01)

# rev E physical sheets (boards2.py): BRD-03 PED board, BRD-04 centre-unit wiring, BRD-05 / BRD-06 harnesses
import boards2  # noqa: E402

SHEETS += [boards2.brd03, boards2.brd04, boards2.brd05, boards2.brd06]

# review fixes (2026-10-08): BRD-07 small boards (J702 / J501 / PS + J701 direct wiring), BRD-08 MB underside routed wiring
import boards3  # noqa: E402

SHEETS += [boards3.brd07, boards3.brd08]
