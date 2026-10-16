"""Every cable / harness of Toccata rev E (one source for SCH-01's cable list, BRD-04..06, cables.csv, harness.csv, the page).

Lengths: 'path' = centre-line length of the route in the built CAD (cad_extract.py -> netlist/cad_centre.json, electronics.py
LENGTHS); 'cut' = what to cut. Rule for wires soldered at both ends: cut = CAD path + 20 mm (5 mm strip at each end + 10 mm slack),
rounded up to 5 mm. A splice (S1, S2 ...) = strands twisted 10 mm, soldered, 20 mm heat-shrink over it.
Where the CAD does not model a route the value is marked 'est' (estimate) and says from what.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAD_JSON = os.path.normpath(os.path.join(HERE, "..", "netlist", "cad_centre.json"))


def _cad():
    try:
        with open(CAD_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


CAD = _cad()
LEN = dict(CAD["lengths"]) if CAD else {}
PTS = dict(CAD["points"]) if CAD else {}


def L(key, default=None):
    return LEN.get(key, default)


def cut(path, extra=20.0):
    """cut length rounded up to 5 mm."""
    if path is None:
        return None
    return int(math.ceil((path + extra) / 5.0) * 5)


# wire colours used in the drawings (hex) and their Korean names
COL = {"red": ("#c0392b", "빨강"), "blk": ("#1d2433", "검정"), "wht": ("#9aa3b2", "흰색"), "grn": ("#2e8b57", "초록"),
       "blu": ("#1f5fbf", "파랑"), "ylw": ("#d4a017", "노랑"), "gry": ("#7e889a", "회색"), "rib": ("#8a96ab", "리본 회색"),
       "rst": ("#c0392b", "리본 1번 (빨간 줄)"), "shd": ("#6b7690", "차폐")}

RIBBON = ["+3V3", "GND", "HALL_C", "HALL_CS", "HALL_D", "HALL_DS", "HALL_E", "HALL_F", "HALL_FS", "HALL_G", "HALL_GS", "HALL_A",
          "HALL_AS", "HALL_B", "GND", "+3V3"]

_sw = PTS.get("sw_lugs", {})
_mm = PTS.get("mismate", {})
_fe = PTS.get("fh_ends", {})
HARNESS_CUT_XT60 = _mm.get("cut")            # 67.6 = CAD electronics.mismate(): whole C-PWR-IN path (holder -x end -> XT60 back) + 10
SPLICE_OVL = 10                               # twisted overlap of a splice
# Both 12 AWG holder stubs: cut = R15 bend (CAD 12 AWG leg 23.5) + CAD splice zone (12.0 / 12.4) -> 36 from the holder end, so the 10 mm
# twist overlap (26..36) sits AFTER the bend, inside the splice zone the CAD keeps (holder end + 2.15 + 23.5 = 25.65 .. 37.65). A 24 mm stub
# would put the splice at 14..24, inside the R15 arc that the 12 AWG must not be bent tighter than (rev E review).
STUB12 = int(math.ceil(max(L("PWR-IN-12", 23.5) + L("PWR-IN-SPLICE", 12.4), L("PWR-FUSE-12", 23.5) + L("PWR-FUSE-SPLICE", 12.0))))
E12_IN, E12_OUT = _fe.get("e12_in", 2.15), _fe.get("e12_out", 2.15)   # CAD centre line starts this far off each holder end


def ceil5(v):
    return int(math.ceil(v / 5.0 - 1e-9) * 5)


def floor5(v):
    return int(math.floor(v / 5.0 + 1e-9) * 5)


# W601 is built from three pieces: the holder's -x 12 AWG stub, a 10 mm twisted splice, the XT60-M 16 AWG lead (pre-soldered to the XT60).
# The 67.6 limit is for the WHOLE assembled length (holder -x end -> XT60 back): lead = rule cut(16 AWG path), capped so that
# stub + lead - overlap stays <= the limit.
W601_MAX = int(round(HARNESS_CUT_XT60)) if HARNESS_CUT_XT60 else 68  # 68
LEAD_W601 = min(cut(L("PWR-IN-16")) if LEN else 45, floor5(W601_MAX - STUB12 + SPLICE_OVL))   # min(45, 40) = 40
W601_TOTAL = STUB12 + LEAD_W601 - SPLICE_OVL                        # 66 assembled
W601_NEED = round(E12_IN + (L("PWR-IN", 57.6)), 1)                   # 59.75: holder end -> XT60 back along the CAD path
W601_NEED_L = _mm.get("need", {}).get("L", 94.4)                     # straight line holder end -> left speaker XT60 female back
# W602a: the 16 AWG piece starts at the stub's overlap (STUB12 - 10 from the holder end) and must reach the KCD1 input tab: CAD path end
# (holder end + 2.15 + 12 AWG 23.5 + splice 12.0 + 16 AWG 74.8, wire end 1.55 short of the tab tip) + 5 laid on the 4.8 mm tab; + 10 slack.
try:
    SW_TIP_GAP = round(_sw["y_tip"] - CAD["paths"]["PWR"]["FUSE"][-1][-1][1], 2)   # 318.3 - 316.75 = 1.55
except Exception:
    SW_TIP_GAP = 1.55
W602A_REACH = round(E12_OUT + L("PWR-FUSE", 110.3) + SW_TIP_GAP + 5, 1)            # about 119 from the holder end
W602A_16 = ceil5(W602A_REACH - (STUB12 - SPLICE_OVL) + 10)                           # 105
BLACK_RETURN = None if not LEN else round(L("PWR-IN") + L("PWR-FUSE") + L("PWR-BUS-BUCK"), 1)
# W601 black: XT60-M black lead (cut to LEAD_W601 with the red) -> S2 -> 16 AWG black extension to the star point (buck IN-): the
# extension covers BLACK_RETURN - (lead - overlap), + 5 in the screw terminal + 10 slack.
BLACK_EXT = ceil5(BLACK_RETURN - (LEAD_W601 - SPLICE_OVL) + 5 + 10) if BLACK_RETURN else 195
# W701 / W702: CAD route (cad_extract.py, paths.HP): J701 legs -> cheek groove -> duct floor -> plug rear (right-angle, upper bound)
W701_PATH = L("HP-W701")                      # about 905
W702_PATH = L("HP-W702")                      # about 779
# W701 cut from the plug rear (where the cable leaves the moulding): route + 20 (strip + slack) + 50 (the route is an estimate), up to 50 mm
W701_CUT = int(math.ceil(((W701_PATH or 905) + 20 + 50) / 50.0) * 50)            # 1000
W707_FROM = 1500 - W701_CUT                    # the rest of the 1.5 m half behind the plug (minus the plug itself) -> W707 300

# XH-A232 pads: research/audio.md 1.1 (product photo) - L+ L- R+ R- in one row on ONE edge, VCC/GND on the opposite edge, input P1 at
# the other edge's left. The CAD (electronics.py) assumes L at the -x end and R at the +x end, so one speaker lead (and maybe the power
# pair) is up to one board length (54 mm) longer than modelled -> 50 mm more on W602c, W703, W705 until the CAD places the pads.
AMP_MARGIN = 50
AMP_NOTE = ("앰프 단자 자리는 받은 보드로 확인: 스피커 L+·L−·R+·R− 4개는 한 가장자리에 한 줄, VCC·GND는 반대 가장자리(research/audio.md 1.1). "
            "CAD는 L·R 단자를 앰프 양 끝에 두고 길이를 쟀으므로 50 mm를 더 잘랐다 — 남는 선은 앰프 옆에서 묶는다.")


def H(**k):
    k.setdefault("kind", "make")
    k.setdefault("notes", [])
    k.setdefault("splices", [])
    k.setdefault("shrink", "")
    k.setdefault("path_src", "")
    return k


HARNESS = [
    # ------------------------------------------------------------------ signal: module ribbons
    H(id="W101~W107", part="sb", title="센서 리본 (모듈마다 1장 × 7)", cable="EUNSUNG 2651-16P 16심 28 AWG, 1.27 피치", bom="RIBBON",
      a=("J201", "SB 2×8 구멍 (아랫면 납땜)"), b=("J301", "MB 2×8 구멍 (아랫면 납땜)"),
      cond=[(n + 1, "rst" if n == 0 else "rib", RIBBON[n], str(n + 1), str(n + 1)) for n in range(16)],
      path=85.0, path_src="CAD O1-C-RIBBON (리본 차선 x59~82, 중심 x70.48)", cut_txt="180 × 7 (남는 95는 차선 안에서 접어 둠)", qty=7,
      notes=["1번 심(빨간 줄) = J201·J301 1번 구멍. 홀수 = 앞줄.", "J301 쪽 끝 6 mm만 가닥을 갈라 0.31 비껴 꽂는다(BRD-01 주 7).",
             "가닥 끝 1.5 mm 벗겨 납 먹임 → 아랫면에서 납땜, 끝을 1 mm 아래로 자름(기판 밑 틈 2.0)."]),
    # ------------------------------------------------------------------ end parts
    H(id="W401", part="end", title="EL 리드 (리본 5가닥) + X401 소켓 선", cable="2651-16P에서 5가닥 + Adafruit 4876 소켓 선(26 AWG) 50 mm",
      bom="RIBBON · JSTXH", a=("J401", "EL 패드 1×5 (아랫면)"), b=("X401", "JST-XH 6P 소켓 (끝 부속 쪽)"),
      cond=[(1, "rib", "GND", "1", "1"), (2, "rib", "EL_A0", "2", "2"), (3, "rib", "EL_AS0", "3", "3"), (4, "rib", "EL_B0", "4", "4"),
            (5, "rib", "+3V3_EL", "5", "6")],
      path=None, path_src="회로 사양 350 (리드 길: 패드 → 레일 밑 차선 EL x13.53~22.48 → 뒷벽 홈 → 통로 바닥)", cut_txt="리본 350 + 소켓 선 50",
      splices=[("S-EL", "리본 가닥 ↔ 소켓 선 5가닥 (뒤 통로에서, 수축 튜브 각각)")],
      notes=["XH 하우징(폭 약 17)은 차선·홈을 못 지나므로 리본을 먼저 꿰고 뒤 통로에서 소켓 선과 잇는다(SCH-04 주 6).",
             "소켓 선 5번(빈 칸)은 잘라 낸다. 선 색은 받은 선으로 확인 — 위치 번호로만 잇는다."]),
    H(id="W403", part="end", title="O1 EXT 플러그 선 (X402)", cable="Adafruit 4876 플러그 선 6심 26 AWG → 150 mm로 자름", bom="JSTXH",
      a=("O1 J302", "MB EXT 패드 1×6 (아랫면)"), b=("X402", "JST-XH 6P 플러그 (모듈 쪽)"),
      cond=[(1, "gry", "GND", "1", "1"), (2, "gry", "EL_A0 (EXT1)", "2", "2"), (3, "gry", "EL_AS0 (EXT2)", "3", "3"),
            (4, "gry", "EL_B0 (EXT3)", "4", "4"), (5, "gry", "EXT4 (비움)", "5", "5"), (6, "gry", "+3V3", "6", "6")],
      path=None, path_src="회로 사양 150 (기판 밑 → USB 플러그 밑 → 뒷벽 개구 → 통로)", cut_txt="150 (약 20 cm 선에서)",
      notes=["J302는 기판을 모듈에 넣기 전에 아랫면에서 납땜(BRD-01 주 8).", "1 = GND … 6 = 3V3. 선 색이 아니라 하우징 번호로 확인."]),
    H(id="W411", part="end", title="ER 리드 (리본 3가닥) + X411 소켓 선", cable="2651-16P에서 3가닥 + Adafruit 4876 소켓 선 50 mm",
      bom="RIBBON · JSTXH", a=("J411", "ER 패드 1×3 (아랫면)"), b=("X411", "JST-XH 6P 소켓 (끝 부속 쪽)"),
      cond=[(1, "rib", "GND", "1", "1"), (2, "rib", "ER_C8", "2", "2"), (3, "rib", "+3V3_ER", "3", "6")],
      path=None, path_src="회로 사양 300 (레일 밑 차선 ER x7.59~14.00 → 뒷벽 홈 → 통로)", cut_txt="리본 300 + 소켓 선 50",
      splices=[("S-ER", "리본 가닥 ↔ 소켓 선 3가닥")], notes=["소켓 선 3·4·5번은 잘라 낸다."]),
    H(id="W413", part="end", title="O7 EXT 플러그 선 (X412)", cable="Adafruit 4876 플러그 선 6심 → 150 mm", bom="JSTXH",
      a=("O7 J302", "MB EXT 패드 1×6"), b=("X412", "JST-XH 6P 플러그"),
      cond=[(1, "gry", "GND", "1", "1"), (2, "gry", "ER_C8 (EXT1)", "2", "2"), (3, "gry", "EXT2 (비움)", "3", "3"),
            (4, "gry", "EXT3 (비움)", "4", "4"), (5, "gry", "EXT4 (비움)", "5", "5"), (6, "gry", "+3V3", "6", "6")],
      path=None, path_src="회로 사양 150", cut_txt="150", notes=["O7은 R301(100 kΩ) 하나만 실장."]),
    # ------------------------------------------------------------------ pedal
    H(id="W501", part="ped", title="페달 선 (3 m 스테레오, 페달 쪽 잘라 납땜)", cable="Coms BC256 3.5 mm TRS 3 m", bom="TRS3M",
      a=("PS", "페달 안 센서 조각 (팁 → R551, 링 → VCC, 슬리브 → GND)"), b=("P501", "TRS 플러그 → J501"),
      cond=[(1, "wht", "PED_TIP (팁)", "R551", "T"), (2, "red", "PED_VCC (링)", "U551.1", "R"), (3, "shd", "GND (슬리브)", "U551.2", "S")],
      path=None, path_src="책상 앞 바닥의 페달 → 뒤판 J501 (실제 놓는 자리에 따름)", cut_txt="플러그 쪽 3 m 그대로, 페달 쪽 끝만 자름",
      notes=["속선 색은 판매처 미공개 — 자른 뒤 플러그 팁·링·슬리브와 통전으로 맞춘다.", "페달 안에서 케이블 타이로 당김 방지."]),
    H(id="W502", part="ped", title="페달 잭 → PB (리본 가닥 4개)", cable="2651-16P 가닥 4개 (SE12)", bom="RIBBONW",
      a=("J501", "PJ-313 T·TN·R·S (잭 조각)"), b=("J502", "PB 패드 1×4"),
      cond=[(1, "rib", "PED_TIP", "T", "1"), (2, "rib", "GND", "TN", "2"), (3, "rib", "PED_VCC", "R", "3"), (4, "rib", "GND", "S", "4")],
      path=None, path_src="추정: J501 기판(z36.4~38, y316.5~) → PB J502 (y308.77, z23.1) 직선 약 20 mm, 판 모서리를 돌아 약 40",
      cut_txt="80", notes=["J501 조각은 뒤판 출력물 잭 선반에 MS 폴리머로 붙인다. 붙이기 전에 W502를 납땜."]),
    # ------------------------------------------------------------------ power (R33 battery input)
    H(id="W601", part="pwr", title="전지 하네스 (X606 XT60 수)", cable="AMASS XT60-M 16 AWG 실리콘 리드 (L80)", bom="XT60M",
      a=("X606", "XT60 수 → 팩 리드 X605에 꽂음"), b=("F601 · ★", "빨강 → S1 → 홀더 −x 꼬리 / 검정 → S2 → ★ A602 IN−"),
      cond=[(1, "red", "VBAT (+)", "2 (+)", "S1 → F601"), (2, "blk", "GND (−)", "1 (−)", "S2 → ★")],
      path=L("PWR-IN"), path_src="CAD C-PWR-IN: 홀더 −x 끝 → 12 AWG 꼬리 %.1f + 이음 %.1f + 16 AWG %.1f → XT60 수 뒤끝" % (L("PWR-IN-12", 0), L("PWR-IN-SPLICE", 12.4), L("PWR-IN-16", 0)),
      cut_txt="리드 %d (빨강·검정) + 홀더 꼬리 %d → 이은 전체 약 %d (≤ %d)" % (LEAD_W601, STUB12, W601_TOTAL, W601_MAX),
      shrink="빨강 (전원 XT60)", splices=[("S1", "빨강 리드 ↔ 홀더 −x 꼬리 (홀더 끝에서 %d~%d, R15 굽힘 뒤)" % (STUB12 - SPLICE_OVL, STUB12)),
                                          ("S2", "검정 리드 ↔ 검정 연장 %d → ★" % BLACK_EXT)],
      notes=["잘못 꽂기 방지: 홀더 −x 끝에서 XT60 수 뒤끝까지 이은 전체 길이가 %d mm 이하여야 왼쪽 스피커 XT60 암(직선 %.1f mm, CAD)에 닿지 않는다. "
             "꼬리 %d + 리드 %d − 겹침 %d = 약 %d mm (CAD 경로 %.1f보다 약 %d 김 = 여유). 이은 뒤 자로 재서 %d mm를 넘으면 리드를 줄인다."
             % (W601_MAX, W601_NEED_L, STUB12, LEAD_W601, SPLICE_OVL, W601_TOTAL, W601_NEED, round(W601_TOTAL - W601_NEED), W601_MAX),
             "꼬리 %d = R15 굽힘 %.1f + 이음 자리 %.1f(CAD): 10 mm 겹침이 굽힘 뒤에 온다. 꼬리를 짧게 자르면 이음이 굽힘 안에 들어가 12 AWG를 R15보다 좁게 꺾게 된다."
             % (STUB12, L("PWR-IN-12", 23.5), L("PWR-IN-SPLICE", 12.4)),
             "검정은 빨강을 따라 W602a·W602b와 나란히 ★(강압 IN− 단자)까지 (경로 합 약 %s mm)." % (BLACK_RETURN or "208")]),
    H(id="W602a", part="pwr", title="퓨즈 → 스위치 (빨강)", cable="홀더 12 AWG 꼬리 + 16 AWG 빨강", bom="FUSEH · SPKW",
      a=("F601", "홀더 +x 꼬리 (12 AWG)"), b=("SW601-1", "KCD1-104 입력 단자 (회로 A)"),
      cond=[(1, "red", "VBAT_F", "+x 꼬리", "1")],
      path=L("PWR-FUSE"), path_src="CAD C-PWR-FUSE: 12 AWG %.1f + 이음 %.1f + 16 AWG %.1f → KCD1 입력 탭" % (L("PWR-FUSE-12", 0), L("PWR-FUSE-SPLICE", 12.0), L("PWR-FUSE-16", 0)),
      cut_txt="홀더 +x 꼬리 %d (R15 굽힘 %.1f + 이음 자리 %.1f) + 16 AWG 빨강 %d" % (STUB12, L("PWR-FUSE-12", 23.5), L("PWR-FUSE-SPLICE", 12.0), W602A_16),
      splices=[("S3", "홀더 12 AWG 꼬리 %d ↔ 16 AWG 빨강 (겹침 = 홀더 끝에서 %d~%d mm, 굽힘 뒤)" % (STUB12, STUB12 - SPLICE_OVL, STUB12))],
      notes=["12 AWG는 R15보다 좁게 꺾지 않는다 — 이음(납땜 + 수축 튜브)은 굽힘이 끝난 뒤에 둔다.",
             "닿는 길이: 꼬리 %d + 16 AWG %d − 겹침 %d = %d (필요: 홀더 끝에서 KCD1 입력 탭 끝까지 CAD %.1f + 탭 위 5 = %.1f)."
             % (STUB12, W602A_16, SPLICE_OVL, STUB12 + W602A_16 - SPLICE_OVL, W602A_REACH - 5, W602A_REACH),
             "KCD1 단자(4.8 × 0.8 탭)에 납땜하고 수축 튜브로 덮는다."]),
    H(id="W602j", part="pwr", title="스위치 두 회로 나란히 (짧은 선 2개)", cable="16 AWG 빨강 2토막", bom="SPKW",
      a=("SW601-1 · 2", "회로 A 입력·출력"), b=("SW601-3 · 4", "회로 B 입력·출력"),
      cond=[(1, "red", "VBAT_F", "1", "3"), (2, "red", "+12V8", "2", "4")],
      path=9.5, path_src="CAD CU-E-SWITCH: 단자 열 간격 9.5 (x433.75 / 443.25)", cut_txt="30 × 2",
      notes=["먼저 켬 상태에서 0 Ω인 단자 짝(한 회로)을 멀티미터로 찾는다. 짝의 한쪽끼리(입력), 다른 쪽끼리(출력)를 잇는다.",
             "짝을 잘못 잡아 입력·출력을 묶으면 스위치가 끄지 못한다 — 끈 상태에서 1–2 사이가 열려 있는지 마지막에 확인."]),
    H(id="W602b", part="pwr", title="스위치 → 강압 입력 (빨강)", cable="16 AWG 빨강", bom="SPKW",
      a=("SW601-2", "KCD1 출력 단자"), b=("A602 IN+", "XL4016 입력 나사 단자"),
      cond=[(1, "red", "+12V8", "2", "IN+")], path=L("PWR-BUS-BUCK"), path_src="CAD C-PWR-BUS 갈래 1",
      cut_txt=str(cut(L("PWR-BUS-BUCK"))), notes=["스위치 출력 단자 한 곳에서 W602b·W602c 두 선이 나간다."]),
    H(id="W602c", part="pwr", title="스위치 → 앰프 전원 (+ ★ → 앰프 GND)", cable="16 AWG 빨강 + 검정, 꼬아서", bom="SPKW",
      a=("SW601-2 · ★", "빨강 = KCD1 출력, 검정 = 강압 IN− (★)"), b=("A702 VCC · GND", "앰프 전원 단자"),
      cond=[(1, "red", "+12V8", "2", "VCC"), (2, "blk", "GND", "★", "GND")],
      path=L("PWR-BUS-AMP"), path_src="CAD C-PWR-BUS 갈래 2 (뒤판 따라 y325 z53, x443 → 733)",
      cut_txt="빨강 %s · 검정 %s (앰프 단자 여유 %d 포함)"
              % (cut(L("PWR-BUS-AMP")) + AMP_MARGIN, (cut(L("PWR-BUS-AMP", 0) - 34.5 + 19.0) + AMP_MARGIN) if LEN else "약 380", AMP_MARGIN),
      notes=["검정 선은 CAD에 따로 그려져 있지 않다(한 줄로 그림). ★에서 위로 올라가 x≈478부터 빨강을 따라간다.", AMP_NOTE]),
    H(id="W603", part="pwr", title="5.1 V → Pi 5 (C24 측면 꺾임 USB-C)", cable="Coms BT663 20 cm, A 끝을 잘라 빨강·검정만", bom="C24",
      a=("A602 OUT+ · OUT−", "강압 출력 나사 단자"), b=("P601", "USB-C 측면 꺾임 → Pi 5 전원 포트"),
      cond=[(1, "red", "+5V1 (VBUS)", "OUT+", "A4"), (2, "blk", "GND", "OUT−", "A1")],
      path=L("PWR-5V-PI"), path_src="CAD C-PWR-5V 갈래 1 (선이 −x로 나오게 꽂음)", cut_txt="플러그 머리에서 약 %s mm 남기고 A 쪽을 자름 (경로 + 30~40)" % (cut(L("PWR-5V-PI"), 35) if LEN else "80"),
      notes=["데이터선(흰·초록)은 짧게 잘라 따로 수축 튜브로 막는다.", "빨강 = + 인지 멀티미터로 확인한 뒤 단자에 물린다."]),
    H(id="W604", part="pwr", title="5.1 V → 허브 DC", cable="허브 5 V 어댑터 선의 플러그 쪽 (ㄱ자 DC 플러그)", bom="HUBDC",
      a=("A602 OUT+ · OUT−", "강압 출력 나사 단자 (W603과 같은 단자)"), b=("P602", "DC 플러그 → 허브 −x 끝면 잭"),
      cond=[(1, "red", "+5V1 (중심 +)", "OUT+", "중심"), (2, "blk", "GND", "OUT−", "슬리브")],
      path=L("PWR-5V-HUB"), path_src="CAD C-PWR-5V 갈래 2 (y285 z48.5 → 허브 끝면)", cut_txt=str(cut(L("PWR-5V-HUB"))),
      notes=["곧은 플러그는 잭 면에서 몰드 끝까지 %s mm 이하일 때만 들어간다(CAD 확인). 길면 ㄱ자 DC 플러그 선." % (PTS.get("hub", {}).get("dc_straight_max", 32)),
             "중심 = + 인지 멀티미터로 확인."]),
    # ------------------------------------------------------------------ audio
    H(id="W701", part="aud", title="동글 → 헤드폰 잭 (AUX 반쪽 ①)", cable="Coms BC256 3 m를 반으로 자른 1.5 m (차폐 3심)", bom="TRS15",
      a=("P701", "3.5 mm 플러그 → 동글 A701"), b=("J701", "PJ-313 T · R · S (왼쪽 볼)"),
      cond=[(1, "wht", "DAC_L (팁)", "T", "T"), (2, "red", "DAC_R (링)", "R", "R"), (3, "shd", "AGND (슬리브)", "S", "S")],
      path=W701_PATH, path_src="CAD 경로(선은 모델에 없음, 직각 경로 = 위쪽 어림): J701 다리 z14.3 → 볼 홈(x−12.6~−4.1, z2.5~7.5) y8 → 212.5 → "
                               "통로 바닥(z1.75) y222 → x650 → 동글 플러그 뒤끝 y222 z21.75까지 올라감 = %.0f mm" % (W701_PATH or 905),
      cut_txt="1.5 m 반쪽을 플러그 뒤끝(선이 몰드에서 나오는 곳)에서 %.1f m로 자름 (경로 %.0f + 벗김·여유 20 + 추정 여유 50) — 남는 약 %.2f m에서 W707"
              % (W701_CUT / 1000.0, W701_PATH or 905, (W707_FROM - 40) / 1000.0),
      notes=["끝 부속 쪽 끝을 J701에 납땜, 가운데 쪽 플러그만 남긴다.", "속선 색은 플러그 팁·링과 통전으로 맞춘다.",
             "자르기 전에 실제 경로(볼 홈 → 통로 → 동글)에 대 보고, 모자라면 W707을 다른 선에서 만든다(W701이 먼저)."]),
    H(id="W702", part="aud", title="헤드폰 잭 노멀 → 앰프 입력 잭 (AUX 반쪽 ②)", cable="BC256 반쪽 1.5 m", bom="TRS15",
      a=("J701", "PJ-313 TN · RN · S"), b=("P702", "3.5 mm 플러그 → J702"),
      cond=[(1, "wht", "HP_TN_L (팁)", "TN", "T"), (2, "red", "HP_RN_R (링)", "RN", "R"), (3, "shd", "AGND (슬리브)", "S", "S")],
      path=W702_PATH, path_src="CAD 경로(직각, 위쪽 어림): J701 다리 → 볼 홈 → 통로 바닥 y222 → x520 → J702 플러그 뒤끝 y222 z25.6 = %.0f mm" % (W702_PATH or 779),
      cut_txt="1.5 m 반쪽 그대로 (남는 약 %.1f m는 통로에서 묶음)" % ((1460 - (W702_PATH or 779)) / 1000.0),
      notes=["헤드폰을 꽂으면 TN·RN이 떨어져 앰프 입력이 끊긴다(R15)."]),
    H(id="W707", part="aud", title="J702 기판 → 앰프 입력 (L · G · R)", cable="W701을 자르고 남는 약 %.2f m 차폐 3심에서 300" % ((W707_FROM - 40) / 1000.0), bom="TRS15",
      a=("J702 기판", "AMP_IN_L · AGND · AMP_IN_R 패드"), b=("A702 IN", "앰프 입력 L · G · R"),
      cond=[(1, "wht", "AMP_IN_L", "L", "1 L"), (2, "shd", "AGND", "G", "2 G"), (3, "red", "AMP_IN_R", "R", "3 R")],
      path=None, path_src="추정: J702 기판(x520 y268) → 앰프 입력 P1, 직선 약 226 (P1 자리 = 받은 보드)",
      cut_txt="약 300 (W701 자른 나머지에서; 앰프 입력 P1 자리는 받은 보드로 확인)",
      notes=["SCH-07의 AMP_IN_L/R·AGND를 잇는 선(rev E에서 선 번호를 줌).", "차폐(AGND)는 앰프 IN G 한쪽에서만 GND와 만난다(△10)."]),
    H(id="W703", part="aud", title="앰프 L± → XT60 수 SPK (L)", cable="16 AWG 2심 (18 AWG도 됨) + XT60-M 리드 100", bom="SPKW · XT60M_SPK",
      a=("A702 L+ · L−", "앰프 스피커 단자 L+·L− (받은 보드로 자리 확인)"), b=("X703", "XT60 수 SPK → 끝벽 집게 L"),
      cond=[(1, "red", "SPK_L_P", "L+", "2 (+)"), (2, "blk", "SPK_L_N", "L−", "1 (−)")],
      path=L("SPK-L"), path_src="CAD C-SPK-L (뒤 줄 y328.5 → 끝벽 L을 따라 앞으로, 끝 100은 XT60 리드)",
      cut_txt="앰프 선 %s (앰프 단자 여유 %d 포함) + XT60 리드 100 그대로" % ((cut(L("SPK-L", 0) - 100) + AMP_MARGIN) if LEN else "약 580", AMP_MARGIN),
      shrink="파랑 + ‘SPK’",
      splices=[("S-L", "앰프 선 ↔ XT60-M 16 AWG 리드")], notes=["쌍마다 꼬고 리본·EXT 선에서 30 mm 이상 떨어뜨린다(D14).", AMP_NOTE]),
    H(id="W705", part="aud", title="앰프 R± → XT60 수 SPK (R)", cable="16 AWG 2심 짧은 토막 + XT60-M 리드 100", bom="SPKW · XT60M_SPK",
      a=("A702 R+ · R−", "앰프 스피커 단자 R+·R− (받은 보드로 자리 확인)"), b=("X705", "XT60 수 SPK → 끝벽 집게 R"),
      cond=[(1, "red", "SPK_R_P", "R+", "2 (+)"), (2, "blk", "SPK_R_N", "R−", "1 (−)")],
      path=L("SPK-R"), path_src="CAD C-SPK-R (선반 위 y293 z49.5)",
      cut_txt="앰프 선 %s (앰프 단자 여유 %d 포함) + XT60 리드 100" % ((cut(L("SPK-R", 0) - 100) + AMP_MARGIN) if LEN else "90", AMP_MARGIN),
      shrink="파랑 + ‘SPK’", splices=[("S-R", "앰프 선 ↔ XT60-M 리드")], notes=["좌우 같은 방향(+ = 빨강)으로 납땜해 위상을 맞춘다.", AMP_NOTE]),
    H(id="W704", part="aud", title="스피커 꼬리선 L (XT60 암 SPK)", cable="XT60-F 16 AWG 리드 100 + 상자 안 짧은 선", bom="XT60F_SPK · SPKW",
      a=("X704", "XT60 암 SPK (끝벽 집게 L 안)"), b=("LS701", "CW-100B25 단자 + · −"),
      cond=[(1, "red", "SPK_L_P", "2 (+)", "+"), (2, "blk", "SPK_L_N", "1 (−)", "−")],
      path=L("PIG-L"), path_src="CAD C-SPKPIG-L (끝벽 Ø19 안 1.5바퀴 여유 35 mm 포함)",
      cut_txt="XT60 리드 100 그대로 + 짧은 선 %s" % (cut(L("PIG-L", 0) - 100) if LEN else "55"), shrink="파랑 + ‘SPK’",
      splices=[("S-PL", "XT60 리드 ↔ 짧은 선 (스피커 상자 안, 흡음솜 속)")],
      notes=["리드가 옆판 구멍 Ø6을 지나야 하므로 XT60을 집게에 끼우기 전에 구멍에 꿴다. 구멍은 본드로 밀봉."]),
    H(id="W706", part="aud", title="스피커 꼬리선 R (XT60 암 SPK)", cable="XT60-F 리드 100 + 짧은 선", bom="XT60F_SPK · SPKW",
      a=("X706", "XT60 암 SPK (끝벽 집게 R 안)"), b=("LS702", "CW-100B25 단자 + · −"),
      cond=[(1, "red", "SPK_R_P", "2 (+)", "+"), (2, "blk", "SPK_R_N", "1 (−)", "−")],
      path=L("PIG-R"), path_src="CAD C-SPKPIG-R", cut_txt="XT60 리드 100 + 짧은 선 %s" % (cut(L("PIG-R", 0) - 100) if LEN else "50"),
      shrink="파랑 + ‘SPK’", splices=[("S-PR", "XT60 리드 ↔ 짧은 선 (상자 안)")]),
    # ------------------------------------------------------------------ touchscreen (bought jumpers + the screen's own cable)
    H(id="W606", part="ts", title="화면 전원 점퍼 F/F (Pi 헤더 쪽)", cable="실리콘 점퍼 26 AWG 20 cm F/F 빨강 + 검정", bom="JMPFF", kind="buy",
      a=("P603", "Pi 40핀 헤더 2번(5 V)·6번(GND)"), b=("X601", "F/F 다른 끝 ⇄ X602"),
      cond=[(1, "red", "+5V_PI", "핀 2", "1"), (2, "blk", "GND", "핀 6", "2")], path=None, path_label="제품 길이 200",
      path_src="제품 길이 200 mm (CAD 경로 아님 — 화면 전원 전체 경로는 W608 TS-C-PWR)", cut_txt="자르지 않음"),
    H(id="W607", part="ts", title="화면 전원 점퍼 M/M", cable="실리콘 점퍼 26 AWG 20 cm M/M 빨강 + 검정", bom="JMPMM", kind="buy",
      a=("X602", "M/M 끝 → X601"), b=("X603", "M/M 끝 → 동봉선 3핀 1·3"),
      cond=[(1, "red", "+5V_PI", "1", "1"), (2, "blk", "GND", "2", "3")], path=None, path_label="제품 길이 200",
      path_src="제품 길이 200 mm (CAD 경로 아님)", cut_txt="자르지 않음"),
    H(id="W608", part="ts", title="화면 동봉 전원선", cable="Waveshare 동봉 MX1.25 2핀 → 2.54 3핀", bom="DPWR", kind="buy",
      a=("X604", "2.54 3핀 하우징 (1 빨강 · 2 빈 칸 · 3 검정)"), b=("P604", "MX1.25 2핀 → 화면 A605"),
      cond=[(1, "red", "+5V_PI", "1", "1"), (2, "blk", "GND", "3", "2")], path=L("TS_POWER"),
      path_src="CAD TS-C-PWR (화면 MX1.25 → … → Pi 핀 2·6 전체, 있는 길이 500~550)", cut_txt="자르지 않음",
      notes=["3핀 하우징 배열은 받은 뒤 통전 검사로 확인한 뒤 점퍼를 꽂는다."]),
]

# short cut-length text for tables (same numbers as cut_txt)
_SHORT = {
    "W101~W107": "180 × 7", "W401": "350 + 50", "W403": "150", "W411": "300 + 50", "W413": "150", "W501": "3 m (끝만 자름)",
    "W502": "80", "W601": "리드 %d + 꼬리 %d (전체 ≤ %d)" % (LEAD_W601, STUB12, W601_MAX), "W602a": "꼬리 %d + %d" % (STUB12, W602A_16),
    "W602j": "30 × 2", "W602b": str(cut(L("PWR-BUS-BUCK"))),
    "W602c": "%s / %s" % (cut(L("PWR-BUS-AMP")) + AMP_MARGIN, cut(L("PWR-BUS-AMP", 0) - 34.5 + 19.0) + AMP_MARGIN),
    "W603": "%s 남김" % cut(L("PWR-5V-PI"), 35), "W604": str(cut(L("PWR-5V-HUB"))), "W701": "%.1f m (플러그 뒤)" % (W701_CUT / 1000.0), "W702": "1.5 m", "W707": "약 300",
    "W703": "%s + 리드 100" % (cut(L("SPK-L", 0) - 100) + AMP_MARGIN), "W705": "%s + 리드 100" % (cut(L("SPK-R", 0) - 100) + AMP_MARGIN),
    "W704": "리드 100 + %s" % cut(L("PIG-L", 0) - 100), "W706": "리드 100 + %s" % cut(L("PIG-R", 0) - 100),
    "W606": "20 cm", "W607": "20 cm", "W608": "동봉",
} if LEN else {}
for _h in HARNESS:
    _h["cut_short"] = _SHORT.get(_h["id"], _h["cut_txt"])

# bought cables that are only plugged (no cutting / soldering)
HUB_PORTS = PTS.get("hub", {}).get("port_map", {"PED": 2, "O3": 3, "O1": 4, "O2": 5, "O4": 6, "O5": 7, "O6": 8, "O7": 9})
HUB_PORT_X = PTS.get("hub", {}).get("ports_x", [696.5 + 22 * i for i in range(10)])


def _usb_std():
    """standard length (m) the CAD chose for each USB-A -> C cable (spec cable_duct.cables std_m): O1/O2 1.0, O3/O4/O7/PED 0.5, O5/O6 0.3."""
    d = PTS.get("usb_std_m")
    if d:
        return {k: float(v) for k, v in d.items()}
    try:                                       # fallback: read the CAD spec itself
        spec = os.path.normpath(os.path.join(HERE, "..", "..", "mechanical", "cad", "spec", "body_L2.json"))
        with open(spec, encoding="utf-8") as f:
            cab = json.load(f)["cable_duct"]["cables"]
        return {c["cable"].split()[0]: float(c["std_m"]) for c in cab}
    except Exception:
        return {"O1": 1.0, "O2": 1.0, "O3": 0.5, "O4": 0.5, "O5": 0.3, "O6": 0.3, "O7": 0.5, "PED": 0.5}


USB_STD = _usb_std()
# 10/14 bought (사비, 엘레파츠): NA993 1 m for the 1 m routes, HB466 50 cm for every shorter route
# (no straight 30 cm A -> C data cable at 엘레파츠, so O5/O6 take 0.5 m and tie the slack in the duct)
USB_BUY = {t: (1.0 if m >= 1 else 0.5) for t, m in USB_STD.items()}
USB_MODEL = {1.0: "Coms NA993", 0.5: "Coms HB466"}
USB_W = {"O%d" % k: "W20%d" % k for k in range(1, 8)}
USB_W["PED"] = "W208"


def m_txt(m):
    return ("%g m" % m) if m >= 1 else ("%.1f m" % m)


def usb_len(tag):
    return L("USB-" + tag) if tag != "PED" else L("PED")


def usb_group_txt():
    """'W201·W202 1 m · W203·W204·W207 0.5 m · W205·W206 0.3 m' (module cables only)."""
    by = {}
    for k in range(1, 8):
        by.setdefault(USB_BUY["O%d" % k], []).append("W20%d" % k)
    return " · ".join("%s %s" % ("·".join(v), m_txt(m)) for m, v in sorted(by.items(), reverse=True))


BOUGHT = []
for _k in range(1, 8):
    _t = "O%d" % _k
    _m = USB_BUY.get(_t, 1.0)
    _ln = usb_len(_t)
    BOUGHT.append(dict(
        id="W20%d" % _k, group="W201~W207", part="mb", cable="%s USB-A → C %s" % (USB_MODEL[_m], m_txt(_m)), bom="USBAC", std_m=_m,
        a="허브 포트 %s" % HUB_PORTS.get(_t, "?"), b="%s RP2040-Zero USB-C" % _t,
        path=("%.1f" % _ln) if _ln else "?",
        note=("CAD 길이(플러그 포함) %.0f ≤ %s − 40 (CAD 경로 기준 %s). C 쪽 몰드 ≤ 12.5 × 7.6 × 25. 남는 선은 통로에서 끈·벨크로로 묶음 (집게에 끼우지 않음)"
              % (_ln or 0, m_txt(_m), m_txt(USB_STD.get(_t, 1.0))))))
BOUGHT += [
    dict(id="W208", part="ped", cable="%s USB-A → C %s" % (USB_MODEL[USB_BUY.get("PED", 0.5)], m_txt(USB_BUY.get("PED", 0.5))), bom="USBAC", std_m=USB_BUY.get("PED", 0.5),
         a="허브 포트 %s" % HUB_PORTS.get("PED", 2), b="PB RP2040-Zero USB-C", path="%.1f" % L("PED", 0),
         note="CAD 길이 %.0f ≤ %s − 40. 앞 공간 줄 y227 z37을 따라감" % (L("PED", 0), m_txt(USB_BUY.get("PED", 0.5)))),
    dict(id="W209", part="pwr", cable="Coms NA977 USB-A(상향 꺾임) → B 25 cm (C25)", bom="C25", a="Pi 5 USB-A (GPIO 쪽 2단의 아래)",
         b="허브 업스트림 B (−x 끝면)", path="%.0f (커넥터 포함 제품 길이)" % L("UPSTREAM", 250), note="위 포트는 머리에 가려 비움"),
    dict(id="W605", part="ts", cable="GUOCONN FFC 22핀 0.5 mm 300 mm B형 (A형은 보험)", bom="FFC22B", a="Pi 5 CAM/DISP 1",
         b="A605 DSI 22핀", path="%.1f (+ 뚜껑 밑 말아 접기 9.4 = %.1f)" % (L("DSI", 0), L("DSI_WITH_LID_ROLL", 0)), note="22심 1 ↔ 1"),
    dict(id="X701", part="aud", cable="Coms IH190 USB-C(F) → USB-A(M) ㄱ자 젠더", bom="GENDER", a="동글 A701", b="Pi 5 USB-A (RJ45 옆 2단의 아래)",
         path="—", note="허브를 거치지 않음 (D7)", adapter=True),
]

# hub NEXTU 710U3: 10 ports, ONE of them charge-only, an ON/OFF switch per port (final_items i093). Ports 0 and 1 are left free so a
# board can move off the charge-only port. Length if a board moves to another port: only the run along x changes (the cable runs along
# the duct / front lane in x and rises at the port), so L' = L - |x_port - x_start| + |x_new - x_start| (estimate).
USB_START_X = dict(PTS.get("usb_start_x", {}))
USB_START_X.setdefault("PED", 458.0)            # PED board: Zero USB axis x457.59 (BRD-03)


def usb_len_at(tag, port):
    ln = usb_len(tag)
    if ln is None:
        return None
    x0 = USB_START_X.get(tag)
    xc = HUB_PORT_X[HUB_PORTS[tag]]
    xn = HUB_PORT_X[port]
    if x0 is None:
        return ln
    return ln - abs(xc - x0) + abs(xn - x0)


def hub_move_rows():
    """per board: port, cable, CAD length, length at port 1 / port 0, does the same cable still fit (<= std - 40)."""
    rows = []
    for tag in sorted(HUB_PORTS, key=lambda t: HUB_PORTS[t]):
        m = USB_BUY.get(tag, 1.0)
        lim = m * 1000 - 40
        l1, l0 = usb_len_at(tag, 1), usb_len_at(tag, 0)

        def ok(v):
            if v is None:
                return "?"
            if v <= lim:
                return "%.0f (그대로)" % v
            need = next((x for x in (0.5, 1.0) if v <= x * 1000 - 40), None)
            return "%.0f → %s 선" % (v, m_txt(need)) if need else "%.0f (1 m도 모자람)" % v
        rows.append([USB_W[tag], tag, HUB_PORTS[tag], m_txt(m), "%.0f" % (usb_len(tag) or 0), "%.0f" % lim, ok(l1), ok(l0)])
    return rows


def path_cell(h):
    """CAD path for a table cell: the centre-line length, or the label for wires the CAD does not route (e.g. '제품 길이 200')."""
    return ("%.1f" % h["path"]) if h.get("path") is not None else h.get("path_label", "—")


def wire_count():
    """(cables, table rows): W101~W107 = 7 ribbons, W201~W207 = 7 USB, W602j = 2 short wires; the X701 adapter is not a wire."""
    import re
    n = 0
    for h in HARNESS + [b for b in BOUGHT if not b.get("adapter")]:
        m = re.match(r"W(\d+)~W(\d+)$", h["id"])
        n += (int(m.group(2)) - int(m.group(1)) + 1) if m else (2 if h["id"] == "W602j" else 1)
    return n, len(HARNESS) + len(BOUGHT)


def by_part(part):
    return [h for h in HARNESS if h["part"] == part], [b for b in BOUGHT if b["part"] == part]


def harness_rows():
    """flat rows for harness.csv: one per conductor."""
    rows = []
    for h in HARNESS:
        for (n, col, net, pa, pb) in h["cond"]:
            rows.append([h["id"], h["title"], h["cable"], n, COL[col][1], net, h["a"][0], pa, h["b"][0], pb,
                         "" if h.get("path") is None else "%.1f" % h["path"], h["cut_txt"], h["shrink"], h["path_src"]])
    return rows
