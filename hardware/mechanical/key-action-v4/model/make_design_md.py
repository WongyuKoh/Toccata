#!/usr/bin/env python3
"""DESIGN.md (Korean) for round 4 from metrics.json + geometry.json + parts_list.json (+ final_r3/metrics.json for the
r3 -> r4 comparison).  Design numbers are read from the JSON files written by run_all.py; literal numbers are only the
r3 verifier's values (marked '검증자'), the r4 study values (marked '연구'), published measurements in section 0 and
stage-0 test targets."""
import json, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_v4 as _M4          # r4.4 fix 2: parameters added in fix 2 (not in metrics 'params')
from export_geo import hu, pf   # r4.4 doc: the one rounding rule (half away from zero at the shown precision, Decimal) for every number in this document

OUT = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(OUT, "metrics.json")))
G = json.load(open(os.path.join(OUT, "geometry.json")))
PLJ = json.load(open(os.path.join(OUT, "parts_list.json")))
R3 = json.load(open(os.path.join(OUT, "..", "final_r3", "metrics.json")))
# r4.4 doc (open issues 4-6): the printed tools, the stage-0 kit and the USB-C cable research, read from their own outputs
TL = json.load(open(os.path.join(OUT, "tools", "tools_geometry.json")))
S0 = json.load(open(os.path.join(OUT, "stage0", "stage0_geometry.json")))
CB = json.load(open(os.path.join(OUT, "..", "cable", "result.json")))
CBR = CB["candidates"][0]                      # the recommended cable (CVILUX DH-20M50052; only one verified and inside the limit)
assert CBR["fits"] and CBR["dims_verified"] and sum(1 for c_ in CB["candidates"] if c_["fits"]) == 1
TLP = TL["print"]
# r4.4 doc retry 2: stage-0 kit totals from stage0_geometry.json (qty-weighted); print estimate = solid mass for the 100 % infill
# coupons, x the tools' 40 % infill factor (tools_geometry.json print.bench_jig.fill_f) for the others
S0N = len(S0["parts"])
S0Q = sum(p_.get("qty", 1) for p_ in S0["parts"])
S0MULTI = [p_ for p_ in S0["parts"] if p_.get("qty", 1) > 1]
S0V = sum(p_["volume_cm3"] * p_.get("qty", 1) for p_ in S0["parts"])
S0G = sum(p_["mass_g_solid"] * p_.get("qty", 1) for p_ in S0["parts"])
S0FF = TL["print"]["bench_jig"]["fill_f"]
S0SOLID = lambda p_: "채움 100 % (질량" in p_["settings"]
S0EST = 10.0 * hu(0.1 * sum(p_["mass_g_solid"] * p_.get("qty", 1) * (1.0 if S0SOLID(p_) else S0FF) for p_ in S0["parts"]), 0)
S0IDS = pf("%s~%s", (S0["parts"][0]["id"], S0["parts"][-1]["id"]))
S0CNT = pf("%d종 %d개", (S0N, S0Q)) if S0Q != S0N else pf("%d개", S0N)
S0MUL = ", ".join(pf("%s는 %d개", (p_["id"], p_["qty"])) for p_ in S0MULTI)
S0C3 = S0["analysis"]["C03"]
S0R = S0C3["ratio_chord"]                      # the kit's pass rule r = E_eff / E_PETG (rounded as the procedure prints it)
S0E = S0["tests"]["3"]["design"]["E_PETG"]
S0C17 = S0["analysis"]["C17"]                  # r4.5 fix 3: test 21 support comb + dead-load bounds on the tested chord
assert all(p_["watertight"] for p_ in S0["parts"]), [p_["id"] for p_ in S0["parts"] if not p_["watertight"]]
S0KD = {k_: v_["k_chord"] for k_, v_ in S0C3["chord_k_vs_plate_dz"].items()}
MODEL_TAG = lambda d_: os.path.basename(os.path.normpath(d_))
PLJ_TOOL = [p_ for p_ in PLJ["parts"] if p_["name"].startswith("출력 공구")][0]
TLD = {d_["id"]: d_ for d_ in TL["dims"]}
TDL = TL["dummy_lever"]
PR = R["params"]
# r4.5 fix round: model parameters used below that run_all does not copy into metrics "params" (same model file)
for _k in ("fin_keel", "fin_keel_front", "spring_groove_dx", "spring_window", "z_c"):
    PR.setdefault(_k, _M4.P.get(_k))
M = R["metrics"]
H = R["heights"]
DY = R["dyn"]
dw, db = DY["white"], DY["black"]
W, B = R["white"], R["black"]
ST = R["stress"]
PL = ST["plate"]
LR = ST["lever_rod"]
MA = R["mass"]
TO = R["totals"]
CL = R["clear"]
NM = CL["named"]
AD = R["adjust"]
RM = R["removal"]
RP = R["removal_paths"]
LD = R["lever_drop"]
SW = R["service_swing"]
SE = R["sens"]
SP = R["spring"]
SIM = R["simplify"]
EP = R["end_parts"]
CD = R["chord_dyn"]
SEAT = R["seat"]
DIMS = {d_["id"]: d_ for d_ in G["dims"]}
KP = {k: {p["point"]: p for p in v["points"]} for k, v in G["key_points"].items()}
M3 = R3["metrics"]
L = []


def w(s=""):
    L.append(s)


def f1(x):
    return pf("%.1f", x)


def f2(x):
    return pf("%.2f", x)


def f3(x):
    return pf("%.3f", x)


def fh(x, n=2):
    """r4.4: half away from zero at n decimals (13.525 -> 13.53) - export_geo.hu, the one rule."""
    return pf(pf("%%.%df", n), x)


def fz(x, n=2):
    """r4.4 doc: hu-rounded number without trailing zeros (11.50 -> 11.5, 6.00 -> 6)."""
    t_ = fh(x, n)
    return t_.rstrip("0").rstrip(".") if "." in t_ else t_


def pct(x):
    return pf("%.0f %%", (100 * x))


def krw(x):
    return "{:,}".format(int(hu(x, 0)))


def skrw(x):
    return ("+" if x >= 0 else "−") + krw(abs(x))


def esc(x):
    """table cell: escape the pipe of names like F|F#."""
    return str(x).replace("|", "\\|")


TR = [("sensor-bar ledge lip front (frame, v3 P112; underside z13.6 = bar top)", "센서 바 오른쪽 턱 립(앞, v3 P112)"),
      ("sensor-bar ledge lip rear (frame, v3 P112; underside z13.6 = bar top)", "센서 바 오른쪽 턱 립(뒤, v3 P112)"),
      ("sensor-bar ledge post front (frame, v3 P112)", "센서 바 오른쪽 턱 기둥(앞, v3 P112)"), ("sensor-bar ledge post rear (frame, v3 P112)", "센서 바 오른쪽 턱 기둥(뒤, v3 P112)"),
      ("USB-C plug envelope", "USB-C 플러그"), ("board part: ", "기판 부품: "), ("board components, rear strip", "기판 부품 선반 앞 띠"),
      ("(left module)", "(왼쪽 모듈)"), ("(right module)", "(오른쪽 모듈)"), ("(module)", "(모듈)"), ("key rod SUS304 D4", "건반 봉 Ø4"), ("key ", "건반 "), ("lever ", "레버 "),
      ("carrier side wall L", "캐리어 왼 옆벽"), ("carrier side wall R", "캐리어 오른 옆벽"), ("carrier core (steel bottom)", "캐리어 가운데(강철 밑면)"),
      ("felt strip (own lever)", "펠트 띠(자기 레버)"), ("felt strip", "펠트 띠"), ("thin tail", "얇은 꼬리"), ("skin head", "헤드 윗판"), ("skin tail", "꼬리 윗판"),
      ("tail wall L", "꼬리 왼 옆벽"), ("tail wall R", "꼬리 오른 옆벽"), ("wall L low", "왼 옆벽 아래"), ("wall L up", "왼 옆벽 위"), ("wall R low", "오른 옆벽 아래"), ("rear wall (over USB opening)", "뒷벽(USB 위)"),
      ("rest felt", "쉼 펠트"), ("block web", "블록 웹"), ("carrier top snap lip", "캐리어 윗 스냅 립"), ("pad bar rail lip", "패드 바 레일 립"),
      ("lever rod end plug (printed, pressed flush)", "레버 봉 끝 마개"), ("lever rod D4 SUS304", "레버 봉 Ø4"), ("fin boss bore D4.0 (printed D3.9, drilled; lever rod inside)", "핀 보스 구멍 Ø4.0"), ("crossbar", "크로스바"), ("capstan head", "캡스턴 머리"), ("balance block", "밸런스 블록"), ("fingernail tab", "손톱 턱"),
      ("balance rail cradle", "밸런스 레일 봉 받침"), ("balance rail (lowered under the blocks)", "밸런스 레일(블록 밑 낮춘 곳)"), ("balance rail", "밸런스 레일"),
      ("rod end stop post", "봉 끝 멈춤 기둥"), ("balance pin D2", "밸런스 핀 Ø2"), ("sensor bar", "센서 바"), ("board components (<= z20)", "기판 부품(z20 이하)"),
      ("cover curtain hook", "가림판 걸이"), ("cover curtain", "가림판 띠"), ("keeper hook", "키퍼 훅"), ("rear dovetail (female groove, neighbour male inside)", "뒤 도브테일(암 홈)"),
      ("rear dovetail male root", "뒤 도브테일(수)"), ("top plate (ledge + bridge)", "윗판"), ("pad bar rail", "패드 바 레일"), ("pad bar grip", "패드 바 손잡이"), ("pad bar", "패드 바"),
      ("pad wedge", "패드 쐐기"), ("up-stop pad", "업스톱 패드"), ("rear shelf (thin over the USB plug)", "뒤 선반(USB 위 얇은 곳)"),
      ("magnet boss", "자석 보스"), ("hub collar", "허브 칼라"), ("bottom lip", "아래 립"), ("guide rib", "가이드 리브"), ("cheek", "볼"),
      ("control-board screw M3x6 head D5.7 x 3.0 envelope (ISO 7380 L35 / DIN 912, on the board)", "제어 기판 나사 M3×6 머리"), ("control-board stand-off", "제어 기판 받침"),
      ("control-board locating pin", "제어 기판 위치 핀"), ("sensor board support", "센서 기판 받침"), ("sensor board", "센서 기판"), ("control board", "제어 기판"),
      ("CD74HC4067 module on pin headers (<= z20)", "4067 모듈(z20 이하)"), ("rear wall (over the lead notch z5-12)", "뒷벽(리드 홈 위)"),
      ("RP2040-Zero on pin headers (PCB z11.9-12.9, top parts <= z16.3)", "RP2040-Zero(핀 헤더 위)"), ("shelf rib", "선반 리브"),
      ("rear wall", "뒷벽"), ("fin boss", "핀 보스"), ("fin", "핀"), ("hub", "허브"), ("web", "웹"), ("beam", "빔"), ("floor", "바닥판"), ("tab ", "탭 "), (" vs ", " ↔ ")]
POSE = {"rest": "쉼", "dip": "바닥", "ff": "ff 최대", "over": "복귀 넘침", "-": "", "": ""}


def _land_ko(s_):
    """r4.5 circuit 2nd (item 10): short Korean name of a lever landing (metrics lever_drop / circuit_r44.drop 'onto')."""
    s_ = s_ or "-"
    if s_.startswith("control-board boss"):
        return "기판 위 매단 보스(" + ("나사 보스" if "screw" in s_ else "위치 핀 보스") + ")"
    if s_.startswith("board part: CD74HC4067"):
        return "4067 모듈 윗면(z20)"
    if s_ == "control board":
        return "기판 윗면(z10.6)"
    if s_ == "floor":
        return "바닥판"
    return s_.split(" (")[0]


def tr(x):
    x = str(x)
    for a_, b_ in TR:
        x = x.replace(a_, b_)
    return x


CASEK = {"pp": "누름 0.8 N", "mf": "누름 1.5 N", "ff_push": "누름 3 N", "push6": "누름 6 N", "release": "1 N 정착에서 뗌",
         "ff_rel": "1.0 m/s, 뗌", "ff_h1.00": "1.0 m/s, 1 N 누른 채", "chord20_rel": "2.0 m/s(ABUSE 화음 속도), 뗌", "chord20_h1.00": "2.0 m/s, 1 N 누른 채",
         "cons_rel": "여유 확인: 손가락 시작 1.5 m/s, 뗌", "cons_h0.45": "여유 확인, 0.45 N 누른 채", "cons_h1.00": "여유 확인, 1 N 누른 채"}


def casek(k):
    if k in CASEK:
        return CASEK[k]
    if k.startswith("play_"):
        return "PLAY 1.5 m/s, " + ("뗌" if k.endswith("rel") else pf("%s N 누른 채", k.split("_h")[1]))
    if k.startswith("abuse_"):
        return "ABUSE 2.5 m/s, " + ("뗌" if k.endswith("rel") else pf("%s N 누른 채", k.split("_h")[1]))
    return k


def mx(col, pre, key):
    return max(v[key] for k, v in DY[col].items() if isinstance(v, dict) and k.startswith(pre) and key in v and v[key] is not None)


def mn(col, pre, key):
    return min(v[key] for k, v in DY[col].items() if isinstance(v, dict) and k.startswith(pre) and key in v and v[key] is not None)


play_up = R["upstop_peaks"]["play"]
ab_up = R["upstop_peaks"]["abuse"]
ch_up = R["upstop_peaks"]["chord20"]
n3p, n3b, n4p, n4b = SIM["n"]
r3s = SIM["r3"]
gh = R["ghost"]
ghs = R["ghost_summary"]
R41 = R["r41"]
AS = R["assembly"]
VAR = R["variants"]
CHG = G.get("changes_this_round", [])
kmin_key = min(SEAT["k_keys"], key=lambda k_: SEAT["k_keys"][k_])

# ============================================================================================ title
# r4.4: the r4.3 record (its intro paragraph and section 1d) is copied verbatim from the r4.3 document - regenerating it from the
# r4.4 model would silently show r4.4 values (F / F# landing) in a historical section
D43 = open(os.path.join(OUT, "work_r4r4", "DESIGN.r4_3.md")).read()
R43M = json.load(open(os.path.join(OUT, "work_r4r4", "metrics.r4_3.json")))
INTRO43 = [l_ for l_ in D43.split("\n") if l_.startswith("**r4.3**")][0]
SEC1D43 = D43[D43.index("## 1d."):D43.index("## 2. ")].rstrip("\n")
# r4.4 step 2 (circuit request 7): C301 is a 1206 chip on the underside, not a leaded part - the only edit of the r4.3 text
assert SEC1D43.count("C301(리드형 적층 세라믹)") == 1
SEC1D43 = SEC1D43.replace("C301(리드형 적층 세라믹)", "C301(1206 칩, 아랫면 — r4.4 글 고침: r4.3 글은 ‘리드형 적층 세라믹’)")
C44 = R["c44"]
w("# Toccata v4 건반 액션 W1+ — 상세 설계 r4.5 회로 2차 대조 (r4 + 검증 1회차 + 도면 형상 지적 + 제어 기판 인터페이스 + 남은 문제 고침 + 비틀림 스프링 기성품 + 스프링 가둠·킬 고침 + 회로 2차 대조, 단일 모델)")
w()
w("2026-09-29 (r4.5 회로 2차 대조; r4.5 고침 2026-09-28) · 모든 수치는 `model_v4.py`를 돌리는 `run_all.py`가 만든 `metrics.json`·`geometry.json`·`parts_list.json`에서 `make_design_md.py`가 옮겼다. "
  "r3 값은 `final_r3/metrics.json`에서 읽었다. 치수 번호(P·K·S·D·A)는 `geometry.json`의 `dims`와 같다. 단위 mm·g·N·ms. z = 0 책상, y = 0 백건 립 앞끝(+y 뒤쪽), "
  "x = 0 모듈 C 왼쪽 명목 경계. 대표 건반은 백건 D, 흑건 C#. ‘연구’가 붙은 숫자는 r4 단순화 연구(업스톱·건반 유지·감사) 보고의 값이고, ‘검증자’가 붙은 숫자는 r3 검증 보고의 값이다.")
w()
w(pf("사용자 요청은 \"뺄 수 있는 부품은 다 빼고 더 작게\"였다. r4는 r3 검증에서 나온 문제 18건(major 8, minor 10)을 모두 고치면서, 업스톱 레일·손나사 8개·접시 스프링 72장·탭 강철 띠 4개·"
  "위치 핀·커버 자석·흑건 납·경화 샤프트·황동 부싱·C-링·L 블록·패드 홀더 17개·스프링 자리판·강철 모따기·드라이버·빼기 고리를 모두 없앴다. "
  "모듈 한 개의 부품 수는 %d개에서 %d개로, 무게는 %.2f kg에서 %.2f kg으로, 맨 위 높이는 z%.1f(손나사 머리 z%.1f)에서 z%.2f로, 기본 구성 비용 변화는 %s원에서 %s원으로 줄었다.", (n3p + n3b, n4p + n4b, r3s["module_kg"], M["module_mass_kg"], r3s["cover"], r3s["heads"], M["cover_top_z_mm"], skrw(r3s["cost"]), skrw(M["base_cost_delta_krw"]))))
w()
w(pf("**r4.1**: r4 검증 1회차(물리 major 2 · minor 4, 기하 major 2 · minor 6)를 반영했다. 부품은 늘리지 않았다. 바뀐 것은 펌웨어 거름 문턱(1.2 → %.1f m/s), F|F# 핀이 만능기판 앞 홈을 지나 바닥에 닿게 한 것(6건반 화음 자리 %.0f → %.0f N/mm), "
  "조립 순서(레버 먼저), 흑건 뒤끝 윗면 낮춤, 패드 바 레일 앞으로 연장·립·예하중 잎, 캐리어 윗 립 끊음, 칼라 0.05 짧게, 스프링 홈 보스다. 판정과 숫자는 1a장, 형상 변경 목록은 1b장.", (PR["ghost_v_note"], R3["metrics"].get("seat_k_chord", 196.0) if False else 196.0, SEAT["k_chord"])))
w()
R42 = R["r42"]
w(pf("**r4.2**: 도면을 그리던 사람이 찾은 형상 문제 7건(검증자가 못 본 것)을 이 모델로 다시 재서 고쳤다(1c장). 부품은 늘리지 않았다. 패드 바 계단을 윗판 홈 끝보다 %.1f 앞으로(r4.1은 윗판과 1.5×1.5 겹침), 윗판 계단과 바 뒤끝을 y%.1f로(쐐기·패드 ↔ 계단 %.2f / %.2f), "
  "레일을 L 레일(립 %.1f×%.1f, 바 밑 %.1f 겹침) + 바 가장자리 출력 잎 혀로, 손톱 턱을 R3 모서리에 붙임, 허브 스프링 주머니에 코일·다리 홈(짧은 다리는 홈 면에 얹힘), 뒷벽 스프링 홈을 보스 밑까지, 끝 부속의 자기 쐐기·센서 바·스프링 홈을 geometry에 넣음. "
  "윗판 계단이 1.5 뒤로 가서 가장 무른 패드 자리가 1559 → %.0f N/mm(동역학 자리 1550 → %.0f)로 약간 물러졌고, 모든 동역학을 다시 돌렸다.", (PR["bar_joggle_clear"], PR["plate_step_y"], R42["gaps_module"]["pad wedge to plate step"][0], R42["gaps_module"]["up-stop pad to plate step"][0], PR["rail_lip"], PR["rail_lip_t"],
     PR["rail_lip"] - 0.3, min(SEAT["k_keys"].values()), SEAT["k_min"])))
w()
Q43 = R["r43"]
LND = {k_: v_ for k_, v_ in Q43["land"].items() if v_["frac"] < 1 - 1e-9}
SLD = SE[Q43["land_lab"]]
w(INTRO43)
w()
Q44 = R["r44"]
RT = R["steel_retention"]["peaks"]
LS4 = Q44["land_sum"]
w(pf("**r4.4**: 사용자 요청 \"남은 문제 부분을 고쳐줄래\"에 따라 r4.3의 남은 형상 문제 3건을 고쳤다(1e장). 부품은 늘리지 않았고 제어 기판 인터페이스(회로 세션 소유)는 그대로다. "
  "(1) 레버 윗 스냅 립의 앞 구간 뒤끝이 1 N 바닥·ff에서 패드 옆 %.2f(공차 뒤 %.2f)까지 들어가던 것을, 앞 립을 y%.0f까지 줄이고(패드와 %.2f) 뒤 립을 y%.0f~%.0f로 늘려(캡스턴이 강철 뒤끝을 밀어 올리는 힘을 받는 립, 뿌리 응력 %.1f → %.1f MPa) 고쳤고, "
  "립·핀 보스 구멍·레버 봉·봉 마개를 geometry.json과 스윕에 넣었다(레버 질량 모델이 립을 두 번 세던 것을 고치니 ff가 0.02° 커져 칸 가장자리 레버 ↔ 레일 웹이 1.30이 되어, 레일 웹 앞 아래 모서리를 %.1f 모따기). "
  "(2) F·F# 쉼 펠트 착지(%.0f / %.0f %%)로 F·F# 자기 복귀 넘침 자세를 구해 스윕하니 %d쌍이 1.3 미만(최소 %.2f: 홈 위로 나온 F 펠트 ↔ USB 플러그, F# 건반 ↔ 자기 레버)이라, 두 펠트를 홈 가장자리에서 자르고 F#는 흑 꼬리 끝까지 넓혀(%.0f / %.0f %% 착지) "
  "0쌍; 6건반 화음 자리(%.0f N/mm) 동역학의 모든 PLAY 목표 통과 — 출력 부품은 바뀌지 않았다. (3) 건반 누른 자세 내보내기를 두 색 모두 1 N 정착 바닥(패드 있음)으로 바꾸고 강체 바닥은 `side_dip_rigid`로 따로 두었다(스윕은 둘 다 검사). 모듈 스윕 최소 %.2f(공차 뒤 %.2f).", (CL["lip43"]["d"], CL["lip43"]["d"] - 0.3, PR["lip_segs"][0][1], CL["lip44"]["pad"], PR["lip_segs"][1][0], PR["lip_segs"][1][1], RT["play"]["sig_rear_r43"], RT["play"]["sig_rear"],
     PR["rail_front_chamfer"], 100 * Q44["land43"]["F"]["frac"], 100 * Q44["land43"]["F#"]["frac"], CL["r43_felts"]["n_bad"], CL["r43_felts"]["min"],
     100 * Q44["land"]["F"]["frac"], 100 * Q44["land"]["F#"]["frac"], Q44["k_ch"], M["min_clearance_mm"], M["min_clearance_after_tol_mm"])))
w()
_so = C44["standoffs"]
w(pf("**r4.4 회로 대조**: 회로 세션이 r4.3 모델을 회로도와 맞춰 보고 보낸 기구 요청 7건(`hardware/pcb/README.md` 끝)을 이 모델로 하나씩 재서 모두 넣었다(1d-2장). "
  "BRD-01 부품을 제로 핀 격자(x = %.2f + 2.54i)로, J301은 아랫면 납땜이라 16심 리본이 기판 밑 z%.0f~%.0f로, USB-C 플러그 면을 y%.1f로(몰드 y%.1f~%.1f), 프레임에 제어 기판 받침 4개(나사 받침 2 + 출력 위치 핀 2, M3×6 머리 ↔ 레일 %.2f · 리브 %.2f), "
  "센서 기판 받침(v3 P111·P113)을 모델에 넣고 뒤 리브 틈을 x%.0f~%.0f로(리본 양옆 %.2f / %.2f), 끝 부속 EL·ER에 기판 받침·뒤 리브 틈·리드 차선(레일 밑 z%.0f~%.0f)·뒷벽 홈(z%.0f~%.0f). "
  "산 부품은 모듈당 제어 기판 나사 M3×6 2개(v3.2 구매 목록 L35에 이미 있어 비용 0). 모든 틈 규칙을 지키고(모듈 스윕 %d쌍, 끝 부속 %d / %d쌍, 1.3 미만 0), 동역학·강도에 닿는 부품은 바뀌지 않았다.", (C44["zero"]["lattice_x"][0], PR["ribbon_under_z"][0], PR["ribbon_under_z"][1], PR["usb_y"][0], PR["usb_y"][0], PR["usb_y"][1],
     min(q_["rail_top"] for q_ in _so if q_["kind"] == "screw"), min(q_["rib_top"] for q_ in _so if q_["kind"] == "screw"), PR["sb_rib_gap"][0], PR["sb_rib_gap"][1],
     C44["ribbon"]["sb_gap_margins"][0], C44["ribbon"]["sb_gap_margins"][1], PR["lead_lane_z"][0], PR["lead_lane_z"][1], PR["lead_notch_z"][0], PR["lead_notch_z"][1],
     CL["n_pairs"], CL["end_parts"]["left"]["n"], CL["end_parts"]["right"]["n"])))
w()
w(pf("**r4.4 남은 문제 4~7**(`report_r4/open_issues.r4_3.json` 번호): (4) USB-C 케이블: C 쪽 몰드 세 치수가 공개 실측으로 확인되고 동결 한계 안에 드는 선은 CVILUX DH-20M50052 하나다(%.2f × %.2f × %.2f, 1d-3장). "
     "(5) RP2040-Zero 높이 한계는 그대로다(회로 쪽 조립 규칙, 18장). "
     "(6) 문서: 모든 표와 치수의 반올림을 한 규칙으로 맞췄다(5장 머리). 13·15장을 부품표와 맞췄다. 출력 공구 %d개를 실제 치수로 넣었다(10.1장). "
     "(7) 시험 가정: 단계 0 시험 키트로 출력 시편 %s와 절차, 합격 숫자, 결과마다 바꿀 모델 값을 모았다(17.1장). 이 문서 작업으로 바뀐 모델 수치는 없다.",
     (CBR["plug_w_mm"], CBR["plug_t_mm"], CBR["plug_l_mm"], len(TLP), S0CNT)))
w()
P4 = _M4.P
SRf = R["steel_retention"]
WPf = SRf["wall_plate"]
# r4.4 fix 2b: the fix-2 history rows show the mechanical shear against the epoxy limits they were written for
BDf = {k_: dict(v_, tau=v_.get("tau_mech", v_["tau"]), limit=P4["bond_tau_epoxy"] / (P4["bond_sf_play"] if k_ == "play" else P4["bond_sf_rare"])) for k_, v_ in SRf["bond"].items()}
KSf, RPf = R["key_shift"]["shift"], R["key_shift"]["pocket"]
w(pf("**r4.4 고침 2**: r4.4 검증(물리 2, 기하 2, 출력물 4 major)을 반영했다(1e장 끝 ‘고침 2’). (1) **강철 블록을 캐리어에 에폭시로 접착한다** — 새 옆벽 판 모델로 재니 스냅 립만으로는 매 음(PLAY 1.5 m/s, 캐리어 → 강철 %.1f N)에 립 선이 한쪽 %.2f~%.2f 벌어지고(물림 1.0) 옆벽 립 뿌리가 층 안 %.1f MPa(한계 12)라 버티지 못한다; 접착 전단은 매 음 %.3f MPa. "
     "산 것은 2액형 에폭시 한 통(소모품, 약 6,000원)뿐이고 출력·구매 부품은 늘지 않았다. (2) 스윕에 레버 축 놀음·패드 바 옆 놀음·건반 노치가 봉에 앉고 파고드는 만큼을 넣었다: 패드 구간 옆벽 윗단을 강철 윗면보다 %.1f 낮춤, 레버-레버 칼라 한 개 %.2f 이상, 핀 보스 +%.2f, "
     "밸런스 레일 블록 밑 포켓(%s), F·F# 꼬리 밑면 %.1f 올림 — 모듈 스윕 최소 %.2f(공차 뒤 %.2f). (3) 핀 게이지 순서(누른 핀마다 바로 확인, 망치 금지)와 T3 뒤 발, 단계 0 시험 20(C16a·b), 3a 굽힘 띠(경간 100), 치수 글(S08·D02·A08·D11)·부품표 공구 행을 고쳤다. 회로 인터페이스는 그대로다.",
     (RT["play"]["B"], WPf["play_a0.50_clamped"]["spread_max"], WPf["play_a0.50_pinned"]["spread_max"], WPf["play_a0.50_pinned"]["s_root"], BDf["play"]["tau"],
      P4["wall_drop_pad"], P4["collar_min"], P4["boss_extra"], " / ".join(pf("%s z%.2f, y%.1f 뒤", (("백" if c_ == "white" else "흑"), q_["z"], q_["y"])) for c_, q_ in RPf.items() if q_),
      P4["tail_relief"]["F"][2], M["min_clearance_mm"], M["min_clearance_after_tol_mm"])))
w()
# r4.4 fix 2b
F2B = R["fix2b"]
BI2 = R["board_insert"]
BD2 = R["steel_retention"]["bond"]
_r0f = os.path.join(OUT, "work_f2b", "metrics.pre_f2b.json")
R0 = json.load(open(_r0f)) if os.path.exists(_r0f) else R
w(pf("**r4.4 고침 2b**: 고침 2를 넣은 모델을 다시 검증한 지적(기하 critical 1 · major 1, 물리 major 2, 출력물 major 2)을 모두 이 모델로 다시 재서 받아들였다(1e장 끝 ‘고침 2b’). "
     "(1) **제어 기판을 넣을 길이 없었다**: 한 덩어리 프레임에서 F|F# 핀 발이 바닥~윗판을 기판의 앞이 열린 홈으로 지나고, 홈 뒤 기판 띠 위에 핀이 매달려 있어 기판이 위·앞·뒤 어디로도 못 들어간다. "
     "기판 밑 바닥을 뚫고(x%.2f~%.2f y%.1f~%.1f) 기판을 **밑에서** 곧게 올려 넣는다: 핀 발은 바닥 대신 **킬**(핀 판을 홈 안에서 밸런스 레일 뒷면까지 z%.0f~%.0f로 이음)로 붙고, 받침 4개는 기판 **위에 매단 보스**(앞 2 레일, 뒤 2 리브·선반)가 되며 M3×6은 밑에서 조인다 — 길 위 최소 %.2f, 6건반 화음 자리 %.0f N/mm(고침 2 %.0f). "
     "(2) 강철 접착을 **MS 폴리머(탄성)**로 바꾸고 옆벽을 %.1f로(주머니 %.1f, 접착층 한쪽 %.2f): 5분 에폭시는 PETG·강철 열팽창 차이로 ΔT %.0f K에 가장자리 전단 %.2f MPa라 떨어진다 → 매 음 하중 %.3f + 열 %.3f MPa(허용 %.3f). "
     "(3) 스윕 자세에 **최악 재료(합격선 밖)의 PLAY 복귀 넘침·ff**를 넣고 E·G 꼬리 밑면 0.1, F는 y176부터 0.15 올림. (4) 캡스턴 벤치 게이지(T2)의 기준을 정착 쉼 꼭대기 z%.2f로(z31.0은 캡스턴을 %.3f / %.3f 높게 맞췄음). (5) 12장 PET 심 방향을 바로잡음. "
     "부품은 늘지 않았다(소모품 에폭시 → MS 폴리머). 회로 인터페이스의 고정값·기판 구멍·홈·부품 자리는 그대로이고, 기판을 고정하는 방법만 바뀌었다(BRD-01 주 8의 글은 회로 세션이 고칠 것).",
     tuple(F2B["hatch"]) + (F2B["keel"][1], F2B["keel"][2], BI2["min"], R["seat"]["k_chord"], R0["seat"]["k_chord"], F2B["side_wall"], P4["lever_w"] - 2 * F2B["side_wall"], P4["bond_t"],
      P4["bond_dT"][0], R["steel_retention"]["thermal"]["day_%.2f" % P4["bond_t"]]["epoxy"], BD2["play"]["tau_mech"], BD2["play"]["tau_th"], BD2["play"]["limit"],
      F2B["crown_T2"], P4["z_c"] - F2B["crown_rest"]["white"], P4["z_c"] - F2B["crown_rest"]["black"])))
w()

# r4.5: the MISUMI spring (section 1f); old = the r4.4 export (work_r45/metrics.r4_4.json)
R44 = json.load(open(os.path.join(OUT, "work_r45", "metrics.r4_4.json")))
_P44, _R4244, _LEG44 = R44["params"], R44["r42"], R44["assembly"]["spring_leg"]          # r4.5: the r4.2 drafter row (1c) keeps the D05 values it was written for
G44 = json.load(open(os.path.join(OUT, "geometry.r4_4.json")))
RQ = {k_: json.load(open(os.path.join(OUT, "work_r45", "requester", f_))) for k_, f_ in (("geo", "spring_geo.json"), ("par", "spring_params.json"), ("base", "phys_base.json"), ("mis", "phys_misumi.json"))}
SP45 = R["spring"]
R45 = R["r45"]
NT45 = R["r42"]["spring_slot"]["notch"]
IN45 = R45["insert"]
HN45 = R45["hub"]
CAT45 = PR["spring_cat"]
S044 = G44["solved"]["spring"]
# r4.5 fix round: the r4.5 record (its intro paragraph and section 1f) is copied verbatim from the r4.5 document - regenerating it
# from the fixed model would show the captured-groove values in a historical section
D45 = open(os.path.join(OUT, "work_r45b", "DESIGN.r4_5a.md")).read()
INTRO45 = [l_ for l_ in D45.split("\n") if l_.startswith("**r4.5**")][0]
SEC1F45 = D45[D45.index("## 1f."):D45.index("## 2. ")].rstrip("\n")
w(INTRO45 + pf(" *(r4.5 고침에서 짧은 다리는 %.1f mm로 바뀌었다. 두 다리는 %.1f / %.1f mm로 자른다 — 1f-2장.)*", (_M4.P["spring_short_leg"], _M4.P["spring_leg"], _M4.P["spring_short_leg"])))
w()
FLT = SP45["float"]
F45 = FLT["r4.5 as built (short leg 2.5 on one face), mu 0.0"]
FROT = [v_ for k_, v_ in FLT.items() if k_.startswith("notch rotated") and k_.endswith("mu 0.3")][0]
F5 = [v_ for k_, v_ in FLT.items() if k_.startswith("short leg 5.0") and k_.endswith("mu 0.3")][0]
CPT = SP45["capture"]
KXL = R["assembly"]["keyless_x"]
KRL = R["keel_rail"]
w(pf("**r4.5 고침**: r4.4 고침 2b와 r4.5 스프링을 다시 검증한 지적(스프링 major 1 · minor 2, 고침 minor 3)을 이 모델로 다시 재서 모두 받아들였다(1f-2장). 부품은 늘지 않았다. "
     "(1) **코일이 봉 위에서 뜬다**: 짧은 다리 2.5가 홈의 한 면에만 기대면 다리 힘이 코일(ID %.1f)을 Ø4 봉 쪽으로 %.2f 밀어 다리가 면에서 떨어지고 스프링이 %.1f° 풀려 쉼 토크 %.2f → %.2f N·mm — 백 립 DW %.1f g · 흑 DW %.1f g(< 47), 흑 바닥 UW 마찰 2배 %.1f g(< 20)로 PLAY 목표 3개 불합격. "
     "짧은 다리를 %.1f mm로 길게 잘라 폭 %.2f **가둠 홈**(허브 벽을 지나 웹 안 막힌 끝)에 넣어, 다리 끝과 주머니 가장자리 두 점(팔 %.2f)이 짝 힘(쉼 %.2f N)으로 토크를 받게 했다: 코일은 제 다리에 매달려 봉과 %.2f 떨어지고(손 25°에서 %.2f), 쉼 토크 %.2f N·mm, 봉 마찰 없음. "
     "스프링은 짧은 다리 끝부터 홈을 따라 넣는다(넣는 슬롯 %.0f°, 긴 다리 창 %.0f°). 뒷벽 홈·보스를 긴 다리 x(%+.1f)에 맞춰 건반 뺀 레버의 다리가 코일·레버 놀음을 더해도 홈에 걸린다(여유 %.2f). "
     "(2) **킬 뿌리의 레일이 단단한 땅이 아니다**: 레일 + 바닥 띠를 핀 선 사이 보로 넣으니 r4.4 킬로는 화음 자리 %.1f N/mm(< %.0f) → F|F# 핀 앞끝을 y152 → **y%.1f**로 당기고 킬(z%.0f~%.1f, 건반 F 블록과 %.2f)을 %.1f로 짧게 해 %.1f N/mm; 첫 모듈 정하중 확인(6 × 60 N, E·F ≤ %.2f mm)을 단계 0에 넣음. "
     "(3) 글 고침: T2 기준 z%.2f, 접착은 10장 4단계, 고침 2b 레버 질량, 설계 %.0f, 얇은 쐐기의 되돌림, D#~G# 레버 떨어짐을 실제 착지로. 도면 작성자 메모(도구 T2·T24·T09 프리즘, 뒷벽 홈 잘라낸 부품·입구 모따기, 떨어짐 자세의 스프링 다리)도 내보냄에 넣었다.",
     (PR["spring_ID"], F45["shift"], F45["unwind"], PR["spring_T0"], F45["T_rest"], F45["keys"]["D"]["DW_lip"], F45["keys"]["C#"]["DW"], F45["keys"]["C#"]["UW_bottom_2f"],
      PR["spring_short_leg"], CPT["width"], CPT["arm"], CPT["F_couple_rest"], CPT["gap_rest"], CPT["gap_hand"], SP45["states"]["rest"]["T"], NT45["slot_deg"], PR["spring_window"][0], PR["spring_groove_dx"], KXL["margin"],
      KRL["k_chord_keel18"], PR["seat_k_chord_req"], KRL["fin_front"], PR["fin_keel"][1], PR["fin_keel"][2], (KRL.get("keel_clear") or {}).get("d", -1.0), KRL["fin_front"] - PR["fin_keel"][0], KRL["k_chord"], KRL["dead"]["limit"],
      R["fix2b"]["crown_T2"], SEAT["k_chord"])))
w()
C45 = R["c45"]
L8 = C45["ledge"]
GSM = R["ghost_summary"]
DQ = C45["drop"]
w(pf("**r4.5 회로 2차 대조**: 회로 세션이 r4.5 저장소 사본을 회로도(개정 B)와 다시 맞춰 보고 보낸 ‘2차 요청’(`hardware/pcb/README.md`) 가운데 8~11을 이 모델로 재서 고쳤다(1d-2장 끝 표). 12(구매 목록 글)·13(리본 차선을 바꾸면 알림)은 다른 곳에서 한다. "
     "부품은 늘지 않았고 회로 인터페이스(리본 차선 x%.0f~%.0f z5~10, 센서·제어 기판, 플러그)는 그대로다. "
     "(8) **센서 바 오른쪽 턱(v3 P112)이 r4 내보냄에서 빠져 있었다** — 바 오른쪽 끝을 잡는 것이 없었다(모듈을 뒤집어 기판을 넣을 때 바·기판이 왼쪽 나사에만 매달림). 프레임에 되살림: 두 조각 y%.1f~%.1f · y%.1f~%.1f, 립 x%.1f~%.1f z%.1f~%.1f(밑면 = 바 윗면), 기둥 x%.1f~%.1f; "
     "가장 가까운 움직이는 부품 %.2f(%s). (9) **유령 거름 글을 모델(gfilter)·SCH-03 주 9와 같게**: note-on부터 %.0f ms 안에 재무장하면 의심, 첫 다시 눌림이 note-on부터 %.0f ms 안이면 속도 비로 판정. "
     "재무장하는 %d건을 note-on 뒤 %.1f s까지 돌리니 스스로 다시 닿는 것 %d건 — %.2f~%.2f N 손가락이 건반을 뜬 자리(자석 %.0f~%.0f %%)에 붙잡고(흔들림은 %.0f ms까지), 그 뒤는 모델 마찰 정칙화의 기어내림(자석 ≤ %.4f m/s)뿐. "
     "(10) 11장 6단계 등 착지 글을 실제 착지로(D#·G# 매단 보스 %.2f°, F#·G 기판 윗면 %.2f / %.2f°, E·F 4067 %.2f°). (11) 끝 부속 EL 바닥에 모듈 기판 구멍 자르기가 새어 생긴 틈 x46.25~46.8 × y144.5~196.5를 없앰.",
     (PR["ribbon_x"][0], PR["ribbon_x"][1], PR["sb_ledge_y"][0][0], PR["sb_ledge_y"][0][1], PR["sb_ledge_y"][1][0], PR["sb_ledge_y"][1][1], PR["sb_ledge"][0], PR["sb_ledge"][1], PR["sb_ledge"][3], PR["sb_ledge"][4],
      PR["sb_ledge"][1], PR["sb_ledge"][2], L8["sweep"]["d"], tr(L8["sweep"]["a"] + " " + L8["sweep"]["part_a"]) + " " + POSE.get(L8["sweep"]["pose_a"], L8["sweep"]["pose_a"]),
      PR["ghost_win"], PR["ghost_rep_max"], len(GSM["armed"]), PR["ghost_long"] / 1000.0, len(GSM["relanded"]), 0.45, 0.50, 100 * GSM["frac_end"][0], 100 * GSM["frac_end"][1], GSM["settle_max"], GSM["creep_max"],
      DQ["D#"]["deg"], DQ["F#"]["deg"], DQ["G"]["deg"], DQ["E"]["deg"])))
w()

# ============================================================================================ 0
w("## 0. 하중 기준, 목표, 결과")
w()
w("### 0.1 하중 기준과 근거")
w()
w("- **근거 1 — Askenfelt & Jansson (1991)**, *From touch to string vibrations II: The motion of the key and hammer*, J. Acoust. Soc. Am. 90(5):2383–2393. "
  "KTH 강의 요약(https://www.speech.kth.se/music/5_lectures/askenflt/motions.html)에서 확인: 메조포르테에서 건반 최대 속도 약 0.3~0.5 m/s, 포르테에서도 1 m/s를 거의 넘지 않음, "
  "해머 속도는 건반 속도의 약 5배(포르테 해머 약 5 m/s).")
w("- **근거 2 — Goebl, Bresin & Galembo (2005)**, *Touch and temporal behavior of grand piano actions*, J. Acoust. Soc. Am. 118(2):1154–1165 "
  "(https://iwk.mdw.ac.at/goebl/papers/Goebl-Bresin-Galembo_JASA2005_PianoAction.pdf 본문에서 확인): 2300여 음을 측정했고, 치는 터치(struck)의 최대 해머 속도는 거의 8 m/s"
  "(가장 센 타건: Steinway G6 7.5, Yamaha G6 7.8, Bösendorfer C4 7.6 m/s), 누르는 터치(pressed)는 5 m/s를 거의 넘지 않았다. 실제 연주에서 흔한 세기는 해머 0.7~1.25 m/s. "
  "근거 1의 5배 비율로 나누면 가장 센 타건의 건반 속도는 7.8 / 5 ≈ 1.56 m/s이다.")
w(pf("- **PLAY 한계**: 건반 **앞끝** 속도 %.1f m/s(앞 펠트에 닿는 순간 = 행정 중 최대 속도). 한 건반, 굴린 화음과 동시 화음 6건반까지, 손가락을 떼거나 0.45~2 N으로 누른 채. "
  "모든 기능 목표(DW·UW·연타·복귀·노치 들림·키퍼·유령·이음·센서·틈)를 지켜야 한다. 모델은 이 앞끝 속도가 되도록 타건 시작 속도를 풀었다(손가락 점에서 백 %.2f, 흑 %.2f m/s). "
  "여유 확인으로 손가락 점 1.5 m/s에서 시작하는 경우(앞끝 약 2.0 m/s)도 계산했다(‘여유 확인’ 행).", (PR["v_play"], dw["v0_play"], db["v0_play"])))
w(pf("- **ABUSE 한계**: 한 건반 %.1f m/s, 6건반 동시 %.1f m/s(앞끝). 손상만 없으면 된다: 항복 없음, 10^4회 피로 한계 아래, 제자리 영구 이탈 없음(건반이 들렸다 다시 앉는 것은 됨), "
  "조정 풀림 없음. 노치 들림은 빠짐 들림 %.2f mm의 절반(%.2f)까지, 유령은 펌웨어가 걸러내면 된다.", (PR["v_abuse"], PR["v_abuse_chord"], PR["lift_popout"], PR["lift_abuse"])))
w(pf("- **PETG 응력 한계(r3 기준 유지)**: 층간(핀·벽처럼 세워 출력한 부분의 세로 인장) 매 음 %.0f MPa, 드문 하중(6건반 화음·ABUSE, 10^4회 이하) %.0f MPa; 층 안(윗판 굽힘, 건반 빔·꼬리) 매 음 %.0f MPa, 드문 하중 %.0f MPa; "
  "상시(쉼) 2 MPa.", (PR["s_cyc"], PR["s_rare"], PR["s_cyc_in"], PR["s_rare_in"])))
w(pf("- **펌웨어 유령 거름(U6, r4.1 고침; r4.5 회로 2차: 글을 모델 gfilter·SCH-03 주 9와 같게)**: 같은 건반에서 앞끝 %.1f m/s 이상인 **어떤 음**이든, 그 note-on(모델: 앞 펠트에 닿는 순간)부터 %.0f ms 안에 건반이 재무장선(자석 복귀 %.0f %%)을 넘으면 의심 상태가 된다. "
  "그 뒤 **note-on부터 %.0f ms 안에** 닿는 첫 다시 눌림의 내려오는 속도(손가락 점)가 앞 음 속도의 %.0f %% 미만(최대 %.2f m/s)이면 버린다; %.0f ms가 지나면 의심을 풀고 다음 눌림은 보통 음이다. "
  "모델에서 재무장하는 %d건은 note-on 뒤 %.1f s까지 돌려도 스스로 다시 닿는 것이 %d건이다(7.4) — %.0f ms는 흔들림이 멈추는 가장 늦은 %.0f ms의 약 2배이고, 단계 0 시험 11에서 펌웨어 기록의 유령 다시 눌림 시각으로 확인한다. "
  "r4.0의 문턱 1.2 m/s는 0.8~1.1 m/s 화음의 유령(내려옴 0.03~0.17 m/s)을 통과시켰다(검증자). "
  "대가: 진짜 연타라도 건반이 %.0f ms 안에 재무장한 뒤 note-on부터 %.0f ms 안에 앞 음의 1/4보다 느리게 다시 치면 모든 세기에서 버려진다(예: 1.0 m/s 뒤 0.25 m/s 미만).",
  (PR["ghost_v_note"], PR["ghost_win"], 100 * PR["rearm"], PR["ghost_rep_max"], 100 * PR["ghost_ratio"], PR["ghost_v_desc"], PR["ghost_rep_max"], len(GSM["armed"]), PR["ghost_long"] / 1000.0, len(GSM["relanded"]),
   PR["ghost_rep_max"], GSM["settle_max"], PR["ghost_win"], PR["ghost_rep_max"])))
w()
w("### 0.2 목표 대비 결과")
w()
w("| 구간 | 목표 (모델 안의 판정식) | 결과 (백 / 흑) | 판정 |")
w("|---|---|---|---|")
for c in R["checks"]:
    c = dict(c)
    if c["check"].startswith("패드 쐐기·패드 ↔ 윗판 계단·레일"):
        # r4.4 doc: run_all wrote this value with '%.2f' (the same stored 1.425 printed as 1.42 and 1.43); re-rendered with the one rule
        _g42 = R["r42"]
        c["value"] = pf("쐐기 %.2f, 패드 %.2f (끝 부속 %.2f)", (_g42["gaps_module"]["pad wedge"][0], _g42["gaps_module"]["up-stop pad"][0],
                                                          min(_g42["gaps_end"][s_]["pad wedge"][0] for s_ in ("left", "right"))))
    w(pf("| %s | %s | %s | %s |", (c["group"], esc(c["check"]), esc(c["value"]), "통과" if c["ok"] else "**불합격**")))
w(pf("| 참고 | 유효 질량 m_eff | %.1f / %.1f g (r3 %.1f / %.1f) | 가벼운 레버 + 스프링 |", (M["m_eff_white_g"], M["m_eff_black_g"], M3["m_eff_white_g"], M3["m_eff_black_g"])))
w(pf("| 참고 | 앞/뒤 힘 비 DW(y90)/DW(y13) | %.2f (y90 %.1f g) | 단계 0 느낌 판정 |", (M["front_back_ratio"], W["DW_y90"])))
w(pf("| 참고 | 마찰 2배 DW | %.1f / %.1f g | 55 g을 넘음 (r3도 %.1f / %.1f) — 18장 |", (W["DW_2f"], B["DW_2f"], R3["white"]["DW_2f"], R3["black"]["DW_2f"])))
w(pf("| 참고 | 1 N으로 누른 바닥 (레버가 패드에 먼저) | 건반 앞이 펠트 위 %+.2f / %+.2f mm | 2 N이면 펠트에 닿음 |", (H["held_pad_front_w"], H["held_pad_front_b"])))
w(pf("| 참고 | 모듈 맨 위 높이 (v3 z59, r3 커버 z78.0·머리 z80.7) | z%.2f, 그 위에 아무것도 없음 | ≤ z74 목표 통과 |", M["cover_top_z_mm"]))
w(pf("| 참고 | 모듈 무게 (r3 %.2f kg) | %.2f kg | ≤ 1.6 kg 목표 통과 |", (r3s["module_kg"], M["module_mass_kg"])))
w(pf("| 참고 | 부품 수 / 모듈 (출력 + 구매) | %d + %d = %d (r3 %d + %d = %d) | |", (n4p, n4b, n4p + n4b, n3p, n3b, n3p + n3b)))
w(pf("| 참고 | 필라멘트·출력 시간 (88건반, 서포트 포함) | %.2f kg · %.0f h (r3 %.2f kg · %.0f h) | 윗판 서포트 때문에 약간 늘어남 |", (M["filament_kg"], M["print_h"], r3s["filament"], r3s["print_h"])))
w(pf("| 참고 | 금속 (88건반) | %.2f kg (r3 %.2f kg) | |", (M["metal_kg_88"], r3s["metal"])))
w(pf("| 참고 | 기본 구성 비용 변화 (한도 100만 원) | %s원 → 기본 %s원 (r3 %s원) | 한도 안 |", (skrw(M["base_cost_delta_krw"]), krw(R["cost"]["base_bom"]), skrw(r3s["cost"]))))
w()

# ============================================================================================ 1
w("## 1. r3의 문제 8건(major)과 10건(minor) — 무엇이었고 r4에서 어떻게 됐나")
w()
w("r3 검증(`context/r3_findings.json`)은 물리·동역학 렌즈에서 major 2건, 기하·조립 렌즈에서 major 6건을 냈다. 아래 ‘문제’ 칸은 r3가 실제로 틀렸던 점, ‘r4’ 칸은 지금 모델의 값이다.")
w()
w("| # | 문제 (r3) | r4 해결 |")
w("|---|---|---|")
w(pf("| 1 | 업스톱 패드 높이(S15)를 건반이 아직 튀는 320 ms 시점에서 잡았다. 실제로 만들면 백 레버가 0.71 mm 먼저 패드에 닿아, 연타 13.1~13.2 Hz(마찰 2배 12.2~12.4, 목표 13.3 미달), "
  "합격선 재료에서 백 노치 들림 0.237 mm와 키퍼 접촉, 흑 캡스턴·빔 하중 약 2배(검증자). | 1 N으로 1.4 s 누른 **진짜 정착** 상태(끝에서 레버 각속도 1e-6 rad/ms 미만)에서 패드 면을 잡는다(S15). "
  "모든 동역학·조정·끝 부속이 이 기준이다. 연타 %.1f / %.1f Hz, 마찰 2배 %.1f / %.1f Hz. |", (M["rep_hz_white"], M["rep_hz_black"], M["rep_hz_white_2x_friction"], M["rep_hz_black_2x_friction"])))
w(pf("| 2 | 스냅 노치 판정식 ‘떼어내는 힘 < 최소 빠짐 힘 4 N’이 모델 자신의 입술 법칙과 맞지 않았다: 그 법칙으로 빠짐 힘은 약 2.0 N, 뒤집힌 채 약 8.7 g 충격이면 빠진다(검증자). | "
  "판정을 **들림**으로만 바꿨다(RET-2): PLAY ≤ %.2f, ABUSE ≤ %.2f(빠짐 %.2f의 절반). 결과: PLAY 한 건반 %.3f / 6건반 화음 %.3f, ABUSE 한 건반 %.3f / 6건반 화음(2.0 m/s) %.3f. 빠짐 힘은 덜걱 방지로만 보고, 단계 0 반지름 쿠폰(R2.50~2.60)에서 %.0f~%.0f N을 고른다. |", (PR["lift_play"], PR["lift_abuse"], PR["lift_popout"], max(M["key_lift_play_mm"], M["key_lift_grid_mm"]), M["key_lift_chord_mm"], M["key_lift_abuse_mm"], M["key_lift_chord_abuse_mm"], PR["snap_F_min"], PR["snap_F"])))
w(pf("| 3 | 끝 부속 이음을 만들 수 없었다: 이음 쪽 핀 보스가 모듈 핀과 0.95 mm 겹치고, 오른쪽 핀이 도브테일 홈을 막고, 도브테일이 내보내지지 않았고, 끝 부속 스윕에 이웃 모듈이 없었다(검증자). | "
  "이음 핀 보스를 안쪽으로만(왼쪽 x%.2f~%.2f, 오른쪽 x%.2f~%.2f), 이음 핀을 도브테일 홈 앞 1.3·위 1.7에서 멈춤, 앞 연장 0.1 얇게, 왼쪽은 수·오른쪽은 암 도브테일을 내보냄. "
  "끝 부속 스윕에 이웃 모듈의 건반 3개·레버 3개·고정 부품을 넣었다: 최소 %.2f / %.2f(공차 뒤), 이음매 고정-고정 %.2f / %.2f. |", (EP["left"]["fins"][1][0] - EP["left"]["boss_len"][1][0], EP["left"]["fins"][1][1], EP["right"]["fins"][0][0], EP["right"]["fins"][0][1] + EP["right"]["boss_len"][0][1],
     CL["end_parts"]["left"]["min"] - 0.3, CL["end_parts"]["right"]["min"] - 0.3,
     CL["end_parts"]["left"]["seam_fixed"][0], CL["end_parts"]["right"]["seam_fixed"][0])))
w(pf("| 4 | 흑건 가이드 탭 7.5 + 천 0.5T 양쪽 = 8.5가 흑건 낮은 벽 사이 8.0에 들어가 한쪽 0.25 억지끼움(걸림); 천이 없으면 놀음 ±0.25(검증자). | 흑 탭을 %.1f로 좁혀 천 양쪽 = 7.9, 벽 사이 %.1f에서 ±%.2f(RET-5). 흑-백 건반 틈 %.2f. 천 두께는 3칸 맞춤 쿠폰으로 고름. |", (PR["tab_w_b"], 8.0, PR["tab_play"], NM["흑건 ↔ 이웃 백건"]["d"])))
w(pf("| 5 | 선택 보조 스프링을 만들 수 없었다: 자리 Ø7이 6.0 틈에 안 들어가고, 컵이 5.9 mm 움직여 33° 기울고, P18과 D05가 달랐다(검증자). | "
  "압축 스프링을 없애고 레버 봉 위 **비틀림 스프링**(A2)을 기본으로 달았다(r4.5: 미스미 기성품): SUS304-WPB d%.1f, ID %.1f, 몸통 %.2f권, 코일은 허브 주머니, 긴 다리는 뒷벽 홈, 짧은 다리는 허브 홈. 응력 최대 %.0f MPa(Su의 %.0f %%). "
  "이 스프링이 DW %.1f g 중 %.1f g을 낸다. |", (PR["spring_d"], PR["spring_ID"], PR["spring_n"], max(v["sigma"] for v in SP["states"].values()), 100 * max(v["sigma"] for v in SP["states"].values()) / SP["Su"], W["DW"], W["DW"] - W["DW_nospring"])))
w(pf("| 6 | 조정을 제자리에서 할 수 없었다: 캡스턴에 손이 닿지 않아 1/8회전마다 커버·손나사 8개·레일·건반을 빼고 24 h 뒤 다시 조여야 했다(검증자). | "
  "업스톱 시점은 그 칸 패드 바를 앞으로 빼서 패드 밑 PET 심 0.1로(한 장 = 건반 앞 %.2f mm), DW는 강철 앞 윗면 퍼티로(1 g = %+.2f g), 캡스턴은 건반을 넣기 전 벤치 게이지에서, "
  "높이는 벤치 지그의 펀칭으로. 나사·드라이버·다시 조이기 없음. |", (AD["white_shim"]["front_mm"], AD["white_putty_steel"])))
w(pf("| 7 | 계단 밸런스 블록의 입술 벽이 강철 밸런스 핀에서 0.19~0.26 mm뿐이고 스윕에서 빠져 있었다(검증자). | 핀을 1.2 mm 앞으로(y%.1f), 홈 y%.1f~%.1f, 블록 앞 y%.1f, 레일 앞 y%.1f(RET-4): 핀 ↔ 입술 벽 %.2f, 홈 뒤끝 %.2f(모든 자세). |", (PR["pin_y"], PR["slot_y"][0], PR["slot_y"][1], PR["block_y"][0], PR["rail_front_y"], CL["pin_lip_wall"], CL["pin_slot"])))
w(pf("| 8 | 치수표 D11에 패드 e ≤ 0.12(r2 값)가 남아 있었다. 합격선은 0.07이고, e 0.10~0.12 패드면 유령 97~99 %%를 펌웨어가 못 거른다(검증자). | "
  "D11 = ‘패드 실효 e ≤ %.2f (캡 모양 60 g 추 2.5 m/s 낙하, 설계 %.2f), 25 %% 압축 %.2f MPa, 패드 자리 강성 ≥ %.0f N/mm(100 N에 %.2f mm), 6건반 화음 자리 ≥ %.0f N/mm’(U7). r4.4: e를 재는 기준 방법은 17.1장의 C01 진자대(모델 `pad_e` 정의)다. |", (PR["pad_e_pass"], PR["pad_e"], H["sigma25"], PR["seat_k_req"], 100.0 / PR["seat_k_req"], PR["seat_k_chord_req"])))
w()
w("minor 10건:")
w()
w("| 문제 (r3) | r4 |")
w("|---|---|")
w(pf("| 유령 격자가 0.6 N부터였다; 0.45~0.55 N 가벼운 누름에서 70~99 %%, ‘오름 < 60 %%’ 거름은 못 잡음(검증자) | 0.45·0.5·0.55·0.6·0.8·1·2 N 모두 계산. 한 건반 PLAY 최대 %.0f %%, 6건반 화음 자리에서는 재무장하지만 새 규칙(속도 비)이 모두 버림: 재무장 %d건, 못 거른 것 %d건 |", (100 * M["ghost_play_single_max"], M["ghost_armed"], M["ghost_not_dropped"])))
w(pf("| 노치 들림·키퍼 판정이 접촉 감쇠의 시작 속도 하한(V0_FLOOR 0.02)에 달렸다(검증자) | 0.02와 0.1 둘 다 계산(7장 표). v_floor 0.1에서 PLAY 들림 %.3f / %.3f, 키퍼 %.2f / %.2f |", (SE["v_floor 0.1"]["white"]["lift_play"], SE["v_floor 0.1"]["black"]["lift_play"], SE["v_floor 0.1"]["white"]["keep_play"], SE["v_floor 0.1"]["black"]["keep_play"])))
w("| 손나사 예하중을 막는 것이 없었다(검증자) | 손나사·접시 스프링 자체가 없다. 패드 힘은 패드 → 패드 바 → 윗판으로 압축만 전달 |")
w(pf("| 마찰 2배에서 DW·바닥 UW가 목표 밖(검증자: DW 56.0 / 55.3, 흑 바닥 UW 16.9) | 바닥 UW(마찰 2배)는 스프링으로 %.1f / %.1f g(≥ 20 통과). 마찰 2배 DW %.1f / %.1f g은 여전히 55 초과(18장) |", (W["UW_bottom_2f"], B["UW_bottom_2f"], W["DW_2f"], B["DW_2f"])))
w(pf("| 흰 앞 펠트 ↔ 크로스바·리브 0.876(검증자) | 펠트를 y%.1f~%.1f로 잘라 %.2f(공차 뒤 %.2f) |", (PR["w_felt_y"][0], PR["w_felt_y"][1], CL["fixed_fixed"]["felt_crossbar_min"], CL["fixed_fixed"]["felt_crossbar_min"] - 0.3)))
w(pf("| 가림판 ↔ 꼬리 윗판이 노치 들림을 빼고 1.31(검증자) | 가림판 밑 z%.1f, 들림을 넣은 ff 자세로 %.2f |", (H["z_curtain_w"], NM["건반 ↔ 가림판 띠"]["d"])))
w(pf("| 예비 보관함 길이 여유 0(검증자) | 건반 칸 %.1f(1.0 + 199.3 + 1.0) + 칸막이 1.2 + 옆 칸 %.1f |", (R["spare_bay"]["key_zone"], R["spare_bay"]["side_zone"])))
w(pf("| 건반 빼기가 도구 없이가 아니었다(드라이버·고리), 흑건은 양옆 백건을 먼저 빼야 하고, 접시 스프링이 따로 놀고, L 블록을 잊으면 레버가 떨어짐(검증자) | "
  "도구 없음: 가림판·패드 바를 손으로 빼고, 레버는 손톱 턱으로(%.2f N), 건반은 손톱으로(%.1f N). 흑건은 양옆 백건 먼저(조립은 흑건 먼저). 나사·접시 스프링 없음. "
  "L 블록 없음: 건반이 빠진 레버는 바닥판(%.1f~%.1f°)이나 기판 쪽(4067·매단 보스·기판 윗면, %.1f~%.1f°) 위에 %.2f N으로 놓인다 |", (RM["white"]["F_tab"], RM["white"]["pull_N"],
     min(LD[k_]["drop_deg"] for k_ in ("C", "C#", "D", "A", "A#", "B")), max(LD[k_]["drop_deg"] for k_ in ("C", "C#", "D", "A", "A#", "B")),
     min(LD[k_]["drop_deg"] for k_ in ("D#", "E", "F", "F#", "G", "G#")), max(LD[k_]["drop_deg"] for k_ in ("D#", "E", "F", "F#", "G", "G#")), LD["E"]["F_rest"])))
w(pf("| 빼기 때 레버 각 창이 좁았다(0.9°)(검증자) | 패드 바를 빼면 레버가 윗판까지 %.1f°까지 올라감; 빼기에 필요한 각 %.1f° / %.1f° → 창 %.1f° |", (min(SW.values()), RM["white"]["lever_angle_needed_deg"], RM["black"]["lever_angle_needed_deg"], min(SW.values()) - RM["white"]["lever_angle_needed_deg"])))
w(pf("| 표·글 불일치: P10 오프셋 기준, 봉 멈춤 기둥 1.0×1.4, 커버 자석 튀어나옴, 높이 z78/80.7(검증자) | P10을 실제 꼬리 중심 기준 %.2f로, 멈춤 기둥 1.0×2.0, 자석·커버판 없음, 맨 위 z%.2f |", (R["layout"]["max_offset_tail"], M["cover_top_z_mm"])))
w()

# ============================================================================================ 1a / 1b (r4.1)
CSW = R41["chord_sweep"]
cs_max = lambda col, mat: max(q[1] for q in CSW[pf("%s_%s", (col, mat))])
cs_arg = lambda col, mat: max(CSW[pf("%s_%s", (col, mat))], key=lambda q: q[1])[0]
cs_keep = lambda col, mat: min(q[2] for q in CSW[pf("%s_%s", (col, mat))])
ghg = {k: v for k, v in gh.items() if k.startswith("gridc_")}
ghg_armed = [v for v in ghg.values() if v["armed"]]
ghg_lim = [(v["v_desc"], min(PR["ghost_v_desc"], PR["ghost_ratio"] * v["v_note"])) for v in ghg_armed]
gh_margin = min([lim - d for d, lim in ghg_lim] + [9.9])
SL = AS["slide"]
sl_str = min(q["straight"][0] for k_, q in SL.items() if "straight" in q)
sl_str3 = min(q["straight_3shims"][0] for k_, q in SL.items() if "straight_3shims" in q)
sl_pr = min(q["pressed"][0] for q in SL.values())
sl_pr3 = min(q["pressed_3shims"][0] for k_, q in SL.items() if "pressed_3shims" in q)
INS = AS["insert"]
LEG = AS["spring_leg"]
STR = R41["strip"]
ED = R41["end_dyn"]
e015, e025, fb1 = SE["pad e 0.15"], SE["pad e 0.25"], SE["fallback 1: pad e 0.15, gap -0.60/-0.65, E 1.4"]
pvf = SE["pass lines + v_floor 0.1"]
lipb = mx("black", "play_", "lip_peak")
lipb_w = max(v["lip_pull"] for v in [SE[k_]["black"] for k_ in ("pass lines together (pad e 0.07, E 0.7, front e 0.22)", "worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)")])
w("## 1a. r4 검증 1회차 지적과 해결 (r4.0 → r4.1)")
w()
w("지적마다 먼저 이 모델로 다시 계산해 보았다. 받아들인 것과 고친 방식, 받아들이지 않은 부분을 숫자로 적는다. 다시 돌린 범위: 한 모듈(대표 백 D·흑 C#, 끝 건반 A0·C8), PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45~2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악, "
  "6건반 화음 자리 1.0~1.5 m/s(0.05 간격)·유령 격자 0.5~1.5 m/s(0.1 간격). 옥타브 모듈은 모두 같아 되풀이하지 않았다.")
w()
w("| # | 지적 (검증자) | 다시 계산 (이 모델) | 판정 | r4.1 해결과 결과 |")
w("|---|---|---|---|---|")
rows1a = [
    ("물리 M1", "유령 거름 문턱 1.2 m/s 때문에 0.8~1.1 m/s 6건반 화음의 0.45~0.6 N 누름 유령(재무장 50~101 %, 내려옴 0.03~0.17 m/s)이 걸러지지 않는다",
     "r4.0 화음 자리(196 N/mm) 1.0 m/s 0.45 N 백 101 %, 0.5 N 99 % 재현(검증자 표와 같음)", "수용",
     pf("펌웨어만 고침: 문턱 1.2 → %.1f m/s, 규칙 ‘%.0f ms 안, 앞 음 속도의 %.0f %% 미만(최대 %.2f)’. 새 화음 자리 %.0f N/mm에서 0.5~1.5 m/s × 0.45~2 N 격자 %d경우: 재무장 %d건, 모두 버림(한계와의 여유 최소 %.2f m/s). 전체 %d경우 중 못 버린 것 %d건.", (PR["ghost_v_note"], PR["ghost_win"], 100 * PR["ghost_ratio"], PR["ghost_v_desc"], R41["k_ch"], len(ghg), len(ghg_armed), gh_margin, M["ghost_cases"], M["ghost_not_dropped"]))),
    ("물리 M2", "기판 위 D#~G# 6건반 화음에서 노치 들림이 1.2~1.4 m/s에 0.216~0.238 (1.5 m/s의 0.126은 국소 최소); 무르고 감쇠 없는 자리(196 N/mm)가 원인",
     "r4.0 자리 203 N/mm, 백 D 뗌: 1.3 m/s 0.226, 1.35 m/s 0.232, v_floor 0.1이면 1.5 m/s 0.266 (검증자 0.227 / 0.238 / 0.262와 같음)", "수용",
     pf("F|F# 핀이 만능기판 앞쪽 홈(x%.2f~%.2f, y%.1f~%.1f, 부품 없음)을 지나 y%.0f~%.0f에서 바닥에 닿게 함 → 6건반 화음 자리 %.0f N/mm(가장 무른 화음은 이제 C~F), 한 건반 자리 최소 %.0f N/mm. "
     "1.0~1.5 m/s 0.05 간격 최대 들림: 공칭 %.3f / %.3f, 합격선 재료 %.3f / %.3f (백 / 흑), 키퍼 최소 %.2f. 대가: F|F# 핀이 하중을 더 받아 핀 윗 이음 층간 응력이 6건반 PLAY 화음 %.1f MPa(r4.0 %.1f), 2.0 m/s 화음 %.1f MPa(r4.0 %.1f; 한계 15). 대안 ‘D#~G# 칸 틈 −0.6’은 기각: 공칭은 0.223, v_floor 0.1이면 0.282에 키퍼 −0.03(r4.1 탐색).", (G["solved"]["fins"][2][0] - PR["board_slot_clear"], G["solved"]["fins"][2][1] + PR["board_slot_clear"], PR["board_y"][0], PR["board_slot_y1"], PR["fin_slot_y"][0], 171.0,
        R41["k_ch"], SEAT["k_min"], cs_max("white", "nom"), cs_max("black", "nom"), cs_max("white", "passline"), cs_max("black", "passline"), min(cs_keep("white", "nom"), cs_keep("white", "passline")),
        M["fin_top_play_chord_mpa"], 4.9, M["fin_top_abuse_chord_mpa"], 6.7))),
    ("물리 m1", "합격선 재료 + v_floor 0.1 한 건반 들림 0.205(묶어서 안 돌림); 흑건은 들림 0.06에서도 입술 모서리가 1.5~3.5 N으로 닿으니 ‘입술이 일하지 않음’은 틀림",
     pf("r4.0 자리에서 0.205 재현; r4.1 자리에서 같은 조합 %.3f / %.3f; 흑 PLAY 입술 힘 %.2f N(최대 조합 %.2f N)", (pvf["white"]["lift_play"], pvf["black"]["lift_play"], lipb, lipb_w)), "수용",
     "묶은 조합을 표에 넣음(7.2). ‘입술이 일하지 않음’ 문구를 모두 지우고 노치는 들림으로만 판정(S04). 단계 0 시험 10에 흑건 입술 천 마모(PLAY 10^5회, 천 닳아 뚫림 없음) 추가. 형상 변경 없음."),
    ("물리 m2", "모든 여유가 패드 실효 e ≤ 0.07에 달렸는데 그런 재료를 이름으로 대지 않았다",
     pf("r4.1 자리에서 e 0.15: 백 들림 %.3f, 0.45 N 유령 %s, 흑 ABUSE %.3f; e 0.25: %.3f / %s / %.3f", (e015["white"]["lift_play"], pct(e015["white"]["ghost045"]), e015["black"]["lift_abuse"],
                                                                                    e025["white"]["lift_play"], pct(e025["white"]["ghost045"]), e025["black"]["lift_abuse"])), "수용 (일부 남음)",
     pf("후보를 이름과 자료값으로 적음: Sorbothane(점탄성 PU) 카탈로그 Lupke 반발 10~15 %%(자유 낙하 e ≈ 0.32~0.39), 충격 에너지 흡수 최대 94.7 %%(e ≈ 0.23) (https://www.sorbothane.com/technical-data/material-properties/). 곧 판 하나의 자유 반발로는 0.07에 못 미치므로 "
     "e는 레버 + 패드 + 펠트 면 + 자리 계에서 단계 0 시험 1로 먼저 잰다. 번호 붙인 대안(부품 추가 없음): ① e 0.10~0.15 → 틈 −0.60 / −0.65 + 폼 E 1.4: 들림 %.3f / %.3f, 흑 ABUSE %.3f, 연타 %.1f / %.1f Hz. 18장 위험으로 남김.", (fb1["white"]["lift_play"], fb1["black"]["lift_play"], fb1["black"]["lift_abuse"], fb1["white"]["rep"], fb1["black"]["rep"]))),
    ("물리 m3", "제자리 조정(10장 8번)에 잴 수 있는 합격 기준이 없다",
     pf("종이 띠 0.05가 앞 펠트 위에서 물리기 시작하는 누름 힘(백 틈 −0.30 / −0.40 / −0.50): %s N", " / ".join(pf("%.2f", STR[pf("white_%.2f", g_)]["F_pinch"]) if STR[pf("white_%.2f", g_)]["F_pinch"] else "-" for g_ in (-0.30, -0.40, -0.50))),
     "수용", pf("12장 표에 넣음: 백은 0.05 종이 띠가 %s N에서 미끄러지고 %s N에서 물리면 합격, 흑은 %s / %s N.", tuple(pf("%.2f", v) if v else "-" for v in (STR["white_-0.30"]["F_pinch"], STR["white_-0.50"]["F_pinch"], STR["black_-0.35"]["F_pinch"], STR["black_-0.55"]["F_pinch"])))),
    ("물리 m4", "패드 바가 레일 안에서 FDM 놀음만큼 처져, 매번 들려 올라가 딸깍", "레일과 바가 x로 겹치지 않아 모델에 바를 받치는 것이 없었음(확인)", "수용",
     "바 뒤 계단 양쪽에 출력 예하중 잎(0.6×4×8, 0.3 눌림 ≈ 0.25 N = 바 무게의 9배)이 바를 레일 립(도브테일 밑, 새로 내보냄)에 대고 윗판 쪽으로 밀어 올림; 단계 0 점검에 ‘바 상하 놀음 없음’. 부품 추가 없음. "
     "(r4.2: 잎과 립이 글로만 있었고 립이 0.2 두께·0.3 겹침이라 1c장에서 형상으로 다시 만듦)"),
    ("물리 m5", "글·값 불일치: 거름 상한 0.45 / 0.40, 자리 합격선 900 / 830, §1의 ABUSE 0.320(화음 값), S15 평행 기준", "모두 확인", "수용",
     pf("상한 %.2f 하나로, 자리 합격선 %.0f N/mm(0.12 mm) 하나로, §1 2번에 한 건반 / 화음을 나눠 적음, S15를 ‘패드 없는 1 N 정착 바닥(%.2f°)과 평행, 실제 바닥 %.2f°에서 %.2f° 기움’으로.", (PR["ghost_v_desc"], PR["seat_k_req"], H["held_b_w"], H["held_pad_b_w"], H["held_b_w"] - H["held_pad_b_w"]))),
    ("기하 M1", "윗판이 한 몸이 된 뒤 10장 순서(건반 먼저, 레버 나중)로는 흑 레버가 자기 흑건 위를 못 지나감(창 13.3 < 단면 20), 스프링을 단 레버는 풀린 다리가 뒷벽을 뚫어 쉼 자세로 못 놓음",
     pf("2D C-공간(0.25 mm, 피치 −40~60°): 건반을 다 넣으면 C#·D·E·G# 레버 모두 %s; 건반이 없으면 %d / %d 도달", ("막힘" if not any(INS[n_]["keys_first"]["ok"] for n_ in ("C#", "D", "E", "G#")) else "일부 도달",
                                                                                       sum(1 for q in INS.values() if q["no_keys"]["ok"]), len(INS))), "수용",
     "10장을 ‘레버 먼저, 건반 나중’으로 다시 씀. 레버 넣기 C-공간 검사를 run_all에 넣음(모든 레버와 끝 부속 A0·A#0·C8 도달). 다리는 손가락으로 감아 홈 입구(0.5×45°)에 걸고 놓음. 건반은 이미 검사한 빼기 경로의 반대로 넣음."),
    ("기하 M2", "패드 바를 뺄 때(모든 건반 빼기·심 조정) 흑 패드 아래 모서리 z55.40이 흑건 뒤끝 윗면 z55.5를 침(−0.10), 15~23 mm 사이 바를 받치는 것이 없음",
     pf("r4.0 형상: 곧게 당기면 %.2f(검증자 −0.10과 같음, r4.1 탐색)", -0.096), "수용 (보완)",
     pf("제안대로 흑건 윗면을 가림판 밑(y%.1f~147)만 z%.1f로(입술 0.6), 레일을 y%.0f까지 앞으로 늘림(바가 레일 높이 유지). 그러나 곧게만 당기면 마지막 0.5 mm에서 패드의 비스듬한 아래 모서리가 흑건 윗면 턱 모서리(y%.1f)를 %.2f로 스침(심 3장 %.2f) — 검증자의 1.30은 가장 낮은 꼭짓점만 본 값. "
     "그래서 절차를 ‘앞부분이 윗판에서 나온 21.5 mm부터 바를 윗판 홈 천장에 밀어 올린 채 뺌’으로 정하고 그 경로를 검사: 최소 %.2f(심 3장 %.2f). 대가: 레일 립 때문에 칸 가장자리 레버의 서비스 들어올림 17.75° → %.1f°(빼기에 필요 %.1f°). "
     "(r4.2 모델로 다시: 곧게 당기면 %.2f — 잎 돌기가 립 앞끝을 지나면 바가 립까지 0.3 내려앉으므로 — 밀어 올림 절차는 %.2f / 심 3장 %.2f)", (PR["black_skin_step"][0], PR["black_skin_step"][1], PR["rail_y0"], PR["black_skin_step"][0], 0.022, -0.274, 1.30, 1.21, min(SW.values()), RM["white"]["lever_angle_needed_deg"], sl_str, sl_pr, sl_pr3))),
    ("기하 m1", "비틀림 스프링이 geometry에 없음; 건반 빠진 레버(−31.3°)는 자유각 −30°를 지나 다리가 0.8 홈에서 0.48 빠짐, 자유각 공차 ±5°면 빠질 수 있음",
     pf("r4.1 보스 입구(y%.1f) 기준 다리 끝: 공칭 %.2f 안, 자유각 −25°이면 %.2f(음수 = 입구 앞)", (_P44["spring_groove"][0], _LEG44["C_+0"]["in_groove"], _LEG44["C_+5"]["in_groove"])), "수용",
     pf("뒷벽 면에 출력 보스(레버마다, y%.1f~209, 폭 %.1f)를 두어 홈을 깊이 %.1f(바닥 y209.8 그대로, 걸린 다리 그대로) + 입구 %.1f×45°로. 공칭 −31.3°에서 풀린 다리 끝이 입구 안 %.2f. 자유각 −25°(공차 끝)면 입구 앞 %.2f에 있다가 레버가 올라갈 때 입구 경사가 다시 받아 줌. "
     "주머니·짧은 다리 구멍·다리 방향·홈을 P18에 내보냄. 바닥 멈춤 기둥 안은 기각(레버 떨어짐 각이 바뀌어 검사한 빼기 경로가 바뀜). (r4.4까지의 D05 값 — r4.5는 보스 4.4, 홈 2.4 × 3.2, 풀린 다리 끝 입구 안 %.2f, 1f장)", (209.0 - _P44["spring_boss"][2], _P44["spring_boss"][0], _P44["spring_groove"][4], _P44["spring_lead_in"], _LEG44["C_+0"]["in_groove"], -_LEG44["C_+5"]["in_groove"], LEG["C_+0"]["in_groove"]))),
    ("기하 m2", "캐리어 ‘1종’이 아니다(칼라가 위치마다 다름, 15종), 패드 바 6종, 예비 레버·바가 한 자리에만 맞음", pf("위치 %d곳, 서로 다른 칼라 짝 %d종", (len(VAR["carriers"]), VAR["n_carriers"])), "수용",
     "부품표에 칼라 표(위치별)와 패드 바 6종을 적고, 캐리어 옆벽·바 손잡이에 음 이름을 새김. 완성 예비 레버 2·예비 바 1은 없애고 위치별 파일로 필요할 때 출력(예비 강철 2·스프링 12는 유지)."),
    ("기하 m3", "패드 바 뒤끝 y183.0, 멈춤(윗판 계단)은 y183.5: 매 음 +y 힘으로 0.5 뒤로 밀려 백 틈 −0.40 → 약 −0.30; 도브테일 언더컷이 안 내보내짐", "확인", "수용",
     pf("바를 0.5 늘려 y146.5~183.5(뒤끝이 계단에 닿음) → 모델 위치 = 실제 위치. 레일 립(언더컷) 내보냄. 조정 전 ‘바를 끝까지 밀어 넣기’ 명시. (r4.2: 계단과 바 뒤끝을 y%.1f로 다시 옮김, 1c장)", PR["plate_step_y"])),
    ("기하 m4", "패드와 캐리어 윗 립 사이 x 0.7, 스윕에서 뺀 짝; 공차가 쌓이면 립이 폼 옆을 물음", "확인", "수용",
     pf("윗 립을 y%.0f~%.0f에서 끊음(강철은 y150~%.0f·%.0f~186 립과 앞벽이 잡음). 짝을 스윕에 넣음: 캐리어 옆벽 ↔ 패드 %.2f.", (PR["lip_gap_y"][0], PR["lip_gap_y"][1], PR["lip_gap_y"][0], PR["lip_gap_y"][1], CL["lip_pad"]))),
    ("기하 m5", "C-링을 없앤 뒤 칸마다 축 놀음 0.32, 출력 면 9개", "0.32 확인", "수용",
     pf("칼라마다 %.2f 짧게 → 칸마다 놀음 %s. 조립 때 레버가 제 무게로 자유롭게 도는지 확인, 아니면 칼라 면 사포질.", (PR["collar_short"], " / ".join(pf("%.2f", q) for q in R["axial_play"])))),
    ("기하 m6", "빠진 것·글 불일치: 레버 봉 마개, 출력 공구, 2.0 육각 렌치, 끝 부속 봉 길이, P26 걸이 립 y, §1·U6·§18 값", "확인", "수용",
     pf("마개·출력 공구 3종·육각 렌치를 부품표에; 레버 봉 끝 부속 %.1f / %.1f; P26 = y%.1f~%.1f; 나머지 글 고침.", (VAR["rodL_end"]["left"], VAR["rodL_end"]["right"], PR["curtain_y"][1], PR["ledge_y0"] + PR["curtain_hook"][0]))),
]
for r_ in rows1a:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w("## 1b. 형상 변경 (geometry.json `changes_this_round`: r4.5 고침 → r4.5 회로 2차, r4.5 → r4.5 고침, r4.4 → r4.5, r4.4 고침 2b, 고침 2, 고침 4회차 r4.3 → r4.4, 3회차 r4.2 → r4.3, 2회차 r4.1 → r4.2, 1회차 r4.0 → r4.1)")
w()
w("r4.5 고침 행만 이 판에서 새로 썼다. r4.5 행은 r4.5 때 내보낸 값(`geometry.r4_5a.json`), r4.4 행(고침 2b·고침 2·4회차)은 r4.4 때 내보낸 값을 그대로 옮겼고(`geometry.r4_4.json`; 접착 단계 번호만 ‘10 step 4’로 고침), 1~3회차 행은 r4.3 때 내보낸 값이다.")
w()
w("| 회차 | 부품 | 치수 번호 | 전 | 후 | 이유 |")
w("|---|---|---|---|---|---|")
for c_ in CHG:
    w(pf("| %s | %s | %s | %s | %s | %s |", tuple(esc(x) for x in (c_.get("round", ""), c_["part"], c_["dim"], c_["old"], c_["new"], c_["why"]))))
w()
w("## 1c. 도면 작성자 형상 지적과 해결 (r4.1 → r4.2)")
w()
w(pf("도면 작성자는 r4.0 `geometry.json`(고침 1회차 전)으로 그렸다. 그래서 지적마다 먼저 r4.1 형상(`geometry.r4_1.json`)에서 다시 재고, r4.1에서 이미 고쳐진 부분은 숫자로 기각했다. "
  "다시 돌린 범위: 한 모듈(옥타브 모듈은 모두 같다)과 끝 부속 이음매 — 고정 부품 겹침(0.02 mm 격자, 모듈·끝 부속), 스윕(모듈 %d쌍, 끝 부속 %d / %d쌍), 패드 바 넣고 빼기 경로, 레버 넣기, 서비스 들어올림, 스프링 다리 범위. "
  "윗판 계단을 옮겨 패드 자리가 바뀌었으므로 동역학과 화음·유령 격자도 모두 다시 돌렸다(`run_all.py` 한 번).", (CL["n_pairs"], CL["end_parts"]["left"]["n"], CL["end_parts"]["right"]["n"])))
w()
w("| # | 지적 (도면) | 다시 잰 값 (r4.1 형상) | 판정 | r4.2 해결과 결과 |")
w("|---|---|---|---|---|")
G2, GE = R42["gaps_module"], R42["gaps_end"]
_pb = [q_ for q_ in PLJ["parts"] if q_["name"].startswith("패드 바")][0]["unit_g"]
_pd = [q_ for q_ in PLJ["parts"] if q_["name"].startswith("업스톱 패드")][0]["unit_g"]
BAR_G = _pb + 3 * _pd
LEAF_X = 2 * G2["leaf_F"] / (BAR_G * 9.80665e-3)          # leaf force (both leaves) / weight of the bar with its pads
SLT = R42["spring_slot"]
ESt = {nm_: q_ for s_ in ("left", "right") for nm_, q_ in EP[s_]["stat"].items()}
rows1c = [
    ("도면 1", "패드 바 앞부분(y146.5~169.5, z67.3~68.8)이 윗판 홈 끝(y167.5~168.0에서 z68.8 → 67.3)과 1.5×1.5 겹침(2.56 mm²), 모듈 4개·끝 부속 2개 모두",
     "r4.1 geometry에서 0.02 mm 격자로 2.50 mm² (y167.54~169.48, z67.32~68.78), 모듈과 양 끝 부속 모두 — 바 계단(윗 y169.5 / 아래 y168.0)이 홈 끝 y168.0보다 뒤. r4.1의 패드 바 빼기 검사는 윗판·레일을 ‘설계 미끄럼’이라 건너뛰어 못 봄", "수용",
     pf("바의 계단을 앞으로: 윗 계단 y%.1f(홈 끝 y%.1f보다 %.1f 앞), 아래 계단 y%.1f. 윗판 홈 끝과 계단 면은 geometry에서 수직 면(0.5 mm 표본 경사 없앰). 겹침 검사(모듈 %d, 끝 부속 %d / %d)와 ‘넣고 빼는 내내 바 ↔ 윗판·레일’ 검사(최소 %.2f = 접촉)를 run_all에 넣음. "
     "빼기 절차의 밀어 올림(21.5 mm)은 이제 윗 계단이 윗판 앞면보다 1.0 앞일 때라 윗판과 겹치지 않음(r4.1은 21.5 mm에서 앞부분이 윗판 앞 1.5 mm와 겹쳤음). "
     "도면 작성자의 `_chk_ff.py`(사본, `work_r4r2/drafter_chk/`)로 새 geometry를 다시 보면 패드 바 겹침 0; 남는 것은 밸런스 핀 ↔ 밸런스 레일(15.2 mm², 핀을 압입하는 구멍이 모델에 없을 뿐인 설계 압입).", (R42["y_bar_joggle"], H["y_bar_step"], PR["bar_joggle_clear"], R42["y_bar_joggle"] - PR["pad_bar_t"], len(R42["fit_module"]), len(R42["fit_end"]["left"]), len(R42["fit_end"]["right"]), R42["slide_fit"][0]))),
    ("도면 2", "바를 받치는 것이 없다: 레일은 1.0×1.7 블록, 바 옆 0.3 틈, 가장자리 밑 립 없음; P13의 ‘도브테일 폭 1.0, 높이 1.2’가 geometry에 없음",
     "r4.0 형상 기준 지적. r4.1에는 립이 있었지만 0.6 폭 × 0.2 두께(z65.60~65.80), 바 밑 겹침 0.3 — ±0.3 공차면 0; 예하중 잎은 글로만; 레일 높이는 1.2가 아니라 1.7", "일부 수용",
     pf("L 레일: 웹 1.0(z%.2f까지) + 립 %.1f×%.1f(z%.2f~%.2f, y%.1f~%.1f), 바 가장자리 밑 %.1f 겹침(공차 뒤 %.1f). 바 가장자리마다 출력 잎 혀 %.1f×%.1f×%.0f(y%.0f~%.0f, 뿌리 뒤), 앞 끝 돌기가 립을 딛고 %.1f 눌려 잎마다 %.2f N으로 바를 윗판 자리(z%.2f)에 밀어 올림 — 모두 geometry 부품. "
     "립은 y%.1f부터(y160부터면 칸 가장자리 레버의 서비스 들어올림이 15.5° → 14.5°): 들어올림 %.1f°. 두 잎의 힘 = 패드 붙은 바 무게(%.1f g)의 %.1f배. 대가: 잎 상시 굽힘 %.1f MPa(공차 +0.3이면 %.1f)가 2 MPa 크리프 선을 넘어 예하중이 풀릴 수 있음 — 반으로 풀려도 %.1f배라 바는 자리에 남음; 17장 시험, 18장 위험. P13 글을 ‘L 레일 + 립 + 잎’으로 고침.", (H["z_seat"] - PR["bar_rail"][1], PR["rail_lip"], PR["rail_lip_t"], H["z_seat"] - PR["bar_rail"][1], H["z_seat"] - PR["pad_bar_t"] - PR["bar_leaf_gap"], PR["rail_lip_y0"], PR["plate_step_y"],
        G2["lip_under_bar"], G2["lip_under_bar"] - 0.3, PR["bar_leaf"][0], PR["bar_leaf"][1], PR["bar_leaf"][2], PR["bar_leaf_y"][0], PR["bar_leaf_y"][1], PR["bar_leaf"][3], G2["leaf_F"], H["z_seat"],
        PR["rail_lip_y0"], min(SW.values()), BAR_G, LEAF_X, G2["leaf_sigma"], G2["leaf_sigma_max_tol"], LEAF_X / 2))),
    ("도면 3", "쐐기·패드가 바 뒤끝(y183.0)보다 뒤로 나옴(y183.38 / 183.17); 윗판 계단 면(y183.5~184.0)까지 쐐기 D 0.24, 패드 D 0.45, 쐐기 C# 0.45, 패드 C# 0.72 — 1.0 미만",
     "튀어나옴은 r4.1에서 이미 없음(바 뒤끝 y183.5 > 183.38 / 183.17): 기각. 계단 틈은 r4.1에도 그대로: 내보낸 0.5 경사 면까지 0.235 / 0.443 / 0.444 / 0.712(도면 값과 같음), 설계 의도인 수직 면 y183.5까지는 0.12 / 0.33", "일부 수용",
     pf("윗판 계단과 바 뒤끝을 y183.5 → %.1f로(바 길이 %.1f): 쐐기 뒤끝 ↔ 계단 %.2f, 패드 %.2f, 쐐기·패드 ↔ 레일 립 %.2f(끝 부속 %.2f). 바 뒤끝만 계단에 닿는다. 대가: 윗판이 두꺼운 곳이 1.5 뒤로 가서 가장 무른 패드 자리 1559 → %.0f N/mm, 6건반 화음 자리 %.0f N/mm — 동역학을 이 값으로 다시 돌렸고 모든 목표 통과(0.2장).", (PR["plate_step_y"], PR["pad_bar_y"][1] - PR["pad_bar_y"][0], G2["pad wedge to plate step"][0], G2["up-stop pad to plate step"][0], G2["pad wedge"][0], min(GE[s_]["pad wedge"][0] for s_ in GE), min(SEAT["k_keys"].values()), SEAT["k_chord"]))),
    ("도면 4", "손톱 턱(y148.2~149.2, z51.5~53.0)이 R3 앞 모서리와 떨어져 떠 있음(0.42~1.35), 따로 출력됨",
     "r4.1 레버 형상에서 턱 ↔ 캐리어 거리 0.37 (턱은 사각형, 캐리어 앞 윗모서리는 R3 원호라 z51.5에서 y149.60, z52.5에서 y150.54). 질량 모델(lever_body)은 이미 모서리를 꽉 채워 계산하고 있었음", "수용",
     pf("턱을 밑면 z51.5 위의 R3 모서리까지 채운 한 몸 모양으로(앞면 y148.2 그대로): 턱 ↔ 캐리어 %.3f(≤ 0 = 붙음). 턱 바깥 윤곽은 그대로라 스윕·빼기 경로 값 변화 없음, 질량 모델 그대로.", R42["tab_core"])),
    ("도면 5", "비틀림 스프링을 조립할 수 없다: Ø6.1×3.0 주머니가 R4.3 허브에 사방이 막힘, 긴 다리가 나갈 홈 없음(−2.97°~+17.75°, 약 21°), 짧은 다리 구멍 위치·지름 없음",
     "r4.1 geometry의 허브는 속이 찬 R4.3 원(주머니도 없음); P18 글의 ‘지름 방향 입구’·‘구멍 Ø0.7’은 위치가 없고, 축 방향 짧은 다리는 지름 방향으로 코일을 넣으면 구멍에 들어갈 수 없음. 게다가 r4.1 뒷벽 홈(z50~58)은 보스(z47부터) 밑 3 mm를 남겨, 다리가 보스를 뚫고 지나감(접선 다리 z44.9, 반지름 다리 z48.3에서 보스 면에 닿음)", "수용",
     pf("허브의 주머니 구간(레버 x ±1.5)을 따로 내보냄: 레버 기준 %.0f° 방향 평행 홈(축에서 +%.2f / −%.2f, 폭 %.1f)이 허브 벽을 뚫어 코일(OD 5.5)이 봉을 넣기 전에 들어감. 긴 다리는 코일 뒤쪽 접선(y%.2f z%.2f) → 홈 바닥 끝(y%.2f z%.2f), 레버 %.1f°~%.1f° 내내 홈 안(면까지 최소 %.2f + 선 반지름 + 0.2). "
     "짧은 다리는 %.1f로 줄이고(r4.1 3) 접선에서 %.1f° 바깥으로 굽혀 끝이 홈 위 면에 얹힘(면 끝까지 %.2f 남음; 구멍 없음, 되돌림 토크가 이 면으로). 뒷벽 홈을 보스 밑면(z%.0f)까지 열어 다리가 z%.2f에서 보스 면을 지나 밑에서 홈으로 들어감. 스프링은 모든 레버 자세의 부품(‘spring X’)으로 geometry에 넣음. (r4.4까지의 D05 값 — r4.5는 미스미 스프링: 홈 폭 6.5, 짧은 다리는 새 짧은 다리 홈, 1f장)", (_P44["spring_slot"][0], _P44["spring_slot"][1], _P44["spring_slot"][2], _P44["spring_slot"][1] + _P44["spring_slot"][2], _R4244["spring_rest"]["long_leg"][0][0], _R4244["spring_rest"]["long_leg"][0][1], _R4244["spring_rest"]["tip"][0], _R4244["spring_rest"]["tip"][1],
        _R4244["spring_b_range"][0], _R4244["spring_b_range"][1], _R4244["spring_slot"]["margin"], _P44["spring_short_leg"], _R4244["spring_slot"]["short_bend_deg"], _R4244["spring_slot"]["short_tip_to_face_end"], _P44["spring_groove"][1], _R4244["spring_slot"]["leg_z_at_boss_face"]))),
    ("도면 6", "끝 부속에 스프링 다리 홈 없음; 끝 부속 쐐기가 모듈과 같음(14장은 A0 −0.05, B0 +0.01, C8 −0.08을 요구); 끝 부속 센서 바 없음(부품표는 2개)",
     "r4.1 end_parts: 스프링 홈 보스는 있으나(왼 3, 오른 1) 홈과 평면이 없음; 쐐기 4개가 모듈 백·흑 쐐기와 똑같음; 센서 바 없음 — 모두 확인", "수용",
     "끝 부속 건반마다 자기 1 N 정착 바닥에 평행한 자기 패드 면(끝 부속 동역학이 쓰던 면 그대로)으로 쐐기를 만듦: " +
     ", ".join(pf("%s %.3f~%.3f(모듈 대비 %+.3f / %+.3f)", (nm_, q_["wedge"][0], q_["wedge"][1], q_["wedge_delta"][0], q_["wedge_delta"][1])) for nm_, q_ in ESt.items()) +
     pf("; A0·C8 쐐기 얇은 끝이 0.3 아래(한 층 0.2 이상이라 출력 가능); 쐐기 뒤끝 ↔ 계단 %.2f / %.2f(왼 / 오). 센서 바: 왼쪽 x0.5~46.5(A#0 낮은 구간 x19.93~33.93), 오른쪽 x0.5~23.0. 스프링 홈(y207.8~209.8 z%.0f~%.0f)과 평면을 end_parts에 넣음. 끝 부속 스윕 최소 %.2f / %.2f, 겹침 0.", (GE["left"]["pad wedge to plate step"][0], GE["right"]["pad wedge to plate step"][0], PR["spring_groove"][1], PR["spring_groove"][2], CL["end_parts"]["left"]["min"], CL["end_parts"]["right"]["min"]))),
    ("도면 7", "치수표 글 불일치: P15 ‘y186 뒤 z60.80’ vs 계단 y183.5; P26 걸이 립 y145.5~147.0 vs 부품 y145.5~148.0; D07 두 번째 아래 립 ‘192.0~190.0’(거꾸로, 없는 부품); 패드 면 길이 12.24 vs 재단 6×12",
     "P26은 r4.1에서 이미 y145.5~148.0(부품과 같음): 기각. P15(y186은 바 뒤끝 + 3을 쓴 글), D07(펠트 끝~강철 뒤를 거꾸로 씀), 패드(면 길이 = 12 / cos 11.33° = 12.24, 흑 12.17)는 확인", "일부 수용",
     pf("P15: 홈 끝 y%.1f·계단 y%.1f(둘 다 수직 면) 뒤 z%.2f. D07: 아래 립은 y165~176.5 하나, 강철 뒤 아래는 뒤 바닥 y190.8~192.5. P16·부품표·D16: 패드·PET 심 재단 6 × %.1f(면 길이). P13·P18·S13·D05·D08도 새 형상대로.", (H["y_bar_step"], PR["plate_step_y"], H["plate_rear"], R["pad_cut_len"]))),
]
for r_ in rows1c:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()

# ============================================================================================ 1d (r4.3)
w(SEC1D43)
w()
w("(1d장 위 글은 r4.3 문서의 글을 그대로 옮겼다 — C301 한 곳만 고침. F·F# 쉼 펠트는 r4.4에서 바뀌었다 — 1e장. r4.3 이후 회로 쪽 값은 아래 1d-2.)")
w()
# ============================================================================================ 1d-2 (r4.4 circuit cross-check)
w("### 1d-2. 회로 세션 대조 요청 (r4.4)")
w()
_zq, _uq, _rq, _sq, _dq = C44["zero"], C44["usb"], C44["ribbon"], C44["screw"], C44["drop"]
_scr = [q_ for q_ in C44["standoffs"] if q_["kind"] == "screw"]
_pin = [q_ for q_ in C44["standoffs"] if q_["kind"] == "pin"]
# r4.4 fix 2b: the r4.4 circuit row keeps the floor stand-off it was written for (D6 x z5-9, M3x6 from above into the floor)
_zf0, _zb0, _zb1 = PR["z_floor"][1], PR["board_z"][0], PR["board_z"][1]
_so0 = dict(stack=(_zb1 - _zb0, _zb0 - _zf0, _zf0 - PR["standoff_bore"][1]), length=PR["board_screw"][2], tip_z=_zb1 - PR["board_screw"][2], bore_z=PR["standoff_bore"][1],
            bore_below_tip=(_zb1 - PR["board_screw"][2]) - PR["standoff_bore"][1], floor_under_bore=PR["standoff_bore"][1] - PR["z_floor"][0], engage=_zb0 - (_zb1 - PR["board_screw"][2]),
            past=max(max(PR["board_x"][0] - (x_ - 3.0), (x_ + 3.0) - PR["board_x"][1], PR["board_y"][0] - (y_ - 3.0), (y_ + 3.0) - PR["board_y"][1], 0.0) for x_, y_, k_ in PR["board_standoffs"]))
_E, _Rr = C44["ends"]["left"], C44["ends"]["right"]
_FAN = dict(left_rib=min(d_ for d_, n_ in _E["path_list"] if n_.startswith("sensor board support rib rear")),
            right_post=min(d_ for d_, n_ in _Rr["path_list"] if n_.startswith("sensor board support post")))
_bvf = R["r43"]["board_vs_frame"]
_bpm = CL["fixed_fixed"]["board_parts_min"]
_bpn = CL["fixed_fixed"]["board_parts_min_name"]
w(pf("회로 세션(`hardware/pcb`, 소유자)이 r4.3 모델을 회로도·BRD-01·BRD-02와 대조하고 W1 기구 쪽에 넣어 달라고 한 7건(`hardware/pcb/README.md` ‘W1 기구 쪽에 요청한 것’)을 이 모델에서 하나씩 쟀다. "
  "7건 모두 모델 값과 맞아 받아들였다(3번은 실제로 사는 나사가 v3.2 L35 스텐 유두 렌치볼트 = ISO 7380 머리 Ø5.7이라 회로가 가정한 Ø5.5보다 머리 여유가 0.1 작지만 1.3 이상; 4번은 EL 리드를 패드 줄에서 기판 뒤끝 + 1.5 안에 모아 A#0 흑 탭 받침과 1.3 이상; 7번은 도면 12 글에 G#를 더하고 O1·O7의 G를 따로 적음). 다시 돌린 범위: 이 요청이 닿는 모든 고정 부품 검사(기판 부품 ↔ 건반·레버·핀 홈·금지 구역·패드 바 레일, 받침·M3 머리 ↔ 레일·리브, 기판 밑 리본과 차선, 플러그 y 전 구간 ↔ 선반 홈·뒷벽 개구, "
  "끝 부속 리드 차선·뒷벽 홈, SB 리브 틈), 모듈 스윕 %d쌍(새 고정 부품 포함), 끝 부속 스윕 %d / %d쌍, 고정 부품 겹침·이음 검사, 건반 뺀 레버 떨어짐; 모든 계산은 `run_all.py` 한 번. "
  "움직이는 부품·윗판·핀·패드 자리는 바뀌지 않아 동역학·8.1장(윗판 FE)은 그대로다(받침·리브는 바닥 위 보스라 윗판 하중 길이 아님).", (CL["n_pairs"], CL["end_parts"]["left"]["n"], CL["end_parts"]["right"]["n"])))
w()
w("| # | 회로 쪽 요청 | 이 모델에서 잰 값 | 판정 | r4.4 반영과 결과 |")
w("|---|---|---|---|---|")
rows1d2 = [
    ("회로 1", "BRD-01 부품을 2.54 격자로(제로 핀 격자 x = 76.52 + 2.54i): 제로 x75.14~93.14(+0.14, Waveshare 치수도상 USB-C가 오른쪽 모서리에서 4.67), 4067 x54.93~72.71 × y152.0~192.64, J301 x61.28~79.06 y148.19/150.73 아랫면 납땜 → 리본은 기판 밑 z5~9(차선 안에서는 가운데 x70.48, J301 쪽 끝 6 mm만 0.31 비낌), J302 x94.30~107.00 y193.91, 리셉터클 x79.53~88.47 그대로",
     pf("리셉터클 가운데 x%.2f = 선반 홈 가운데 x%.2f(홈 양옆 %.2f / %.2f 그대로). 이름 붙은 BRD-01 부품 ↔ 출력 프레임 최소 %.2f(%s), 4067 ↔ 금지 구역 %.2f, J302 ↔ 선반 리브 앞면 %.2f. "
     "리본 %.2f 폭이 차선 x%.0f~%.0f 가운데 x%.2f에서 양옆 %.2f / %.2f; J301 가운데 x%.2f라 끝 %.0f mm만 %+.2f — 레일 뒷면 y%.1f 뒤(기판 밑)라 차선 여유는 그대로. 기판 밑 리본(z%.0f~%.0f, 높이 %.1f) ↔ F|F# 핀 발 %.2f, ↔ 받침 (50,149) %.2f, 금지 구역 밖 %.2f. "
     "건반 빔·꼬리 ↔ 기판 부품 스윕 %.2f(%s %s)", (_zq["rcpt_centre"], _zq["slot_centre"], _uq["slot_margins"][0], _uq["slot_margins"][1], _bpm[0], tr(_bpn.replace("board part: ", "") + " vs " + _bpm[1]), _zq["mux_to_keepout"], _zq["j302_to_rib"],
        _rq["width"], _rq["lane"][0], _rq["lane"][1], _rq["xc"], _rq["lane_margins"][0], _rq["lane_margins"][1], _rq["j301_c"], PR["ribbon_j301"][1], _rq["shift"], PR["rail_y"][1],
        _rq["under_z"][0], _rq["under_z"][1], _rq["height_under"], _rq["to_fin"], _rq["to_standoff"], _rq["to_keepout"],
        NM["건반 빔·꼬리 ↔ 제어 기판 부품"]["d"], tr(NM["건반 빔·꼬리 ↔ 제어 기판 부품"]["a"]), POSE.get(NM["건반 빔·꼬리 ↔ 제어 기판 부품"]["pose_a"], NM["건반 빔·꼬리 ↔ 제어 기판 부품"]["pose_a"]))),
     "수용",
     pf("P27에 격자 값(치수 표), geometry의 이름 붙은 기판 부품을 새 자리로; J301은 윗면 납땜 자국(z%.1f 이하)과 새 부품 ‘J301 리본(기판 밑, z%.0f~%.0f)’ 둘로; 평면에 기판 밑 리본·SB → 차선 리본·J201 패드.", (PR["ribbon_z"], PR["ribbon_under_z"][0], PR["ribbon_under_z"][1]))),
    ("회로 2", "리셉터클이 제로 가장자리 밖으로 약 1.3(1.0~1.5) → 플러그 면 y196.8, 몰드 y196.8~221.8, 리셉터클 y189.5~196.8",
     pf("선반 홈 양옆 %.2f / %.2f — 선반 y%.1f~%.1f 내내(x로만 정해지므로 y 이동과 무관), 리브 %.2f / %.2f, F|F# 핀 %.2f, 뒷벽 개구 x %.2f / %.2f · 위 %.2f(y%.0f~%.0f 내내), "
     "뒤 케이블 통로 y%.0f~%.0f(v3 A13): 끝 y%.1f + 굽힘 %.0f = y%.1f(%.1f 남음, r4.3 %.1f), 통로 위 %.1f. 리셉터클 ↔ 홈 가장자리 %.2f, 리브 %.2f, 윗면 z%.1f ≤ 선반 앞 띠 z%.1f. 건반 꼬리·쉼 펠트 ↔ 플러그 스윕 %.2f(%s)", (_uq["slot_margins"][0], _uq["slot_margins"][1], _uq["plug_under_shelf_y"][0], _uq["plug_under_shelf_y"][1], _uq["rib_margins"][0], _uq["rib_margins"][1], Q43["usb"]["each"]["fin"],
        _uq["wall_x_margins"][0], _uq["wall_x_margins"][1], _uq["wall_z_margin"], _uq["wall_y"][0], _uq["wall_y"][1], _uq["passage"][0], _uq["passage"][1], _uq["y"][1], _uq["bend"],
        _uq["y"][1] + _uq["bend"], _uq["passage_spare"], 258.0 - (_uq["y_r43"][1] + _uq["bend"]), _uq["passage_top"], _uq["rcpt_slot_margins"][0], _uq["rcpt_rib_margins"][0], _uq["rcpt"][5], PR["comp_rear"][1],
        NM["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["d"], tr(NM["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["a"]))),
     "수용", pf("P24 = y%.1f~%.1f(x·z 그대로). 선반 홈·뒷벽 개구는 바꿀 필요 없음.", tuple(PR["usb_y"]))),
    ("회로 3", "프레임에 제어 기판 받침 4개 Ø6 × z5~9: 나사 받침 (50.0,149.0)·(114.5,192.5)에 Ø2.5 구멍을 바닥 속 z4.2까지(M3×6), 출력 위치 핀 (114.5,149.0)·(50.0,192.5) Ø2.8(기판 위 1.2); v3 P114 자리는 M3 머리 Ø5.5가 레일 0.75·리브 1.05라 옮김",
     pf("M3×6 = v3.2 구매 목록 L35 ‘스텐 유두 렌치볼트 M3 × 6mm’(ISO 7380 버튼헤드, 머리 Ø%.1f × %.2f; 모델은 머리 외곽 Ø%.1f × %.1f로 잡아 DIN 912 Ø5.5 × 3.0도 덮음) 머리 ↔ 밸런스 레일 뒷면 %.2f, ↔ 선반 리브 %.2f(리브 축 위로 재면 %.2f; 회로 값 1.75 / 1.55는 Ø5.5), "
     "머리 가장자리가 기판 모서리 x%.2f / %.2f 밖으로 %.2f(머리 밑면은 기판 위, 나사 구멍 Ø3.2 둘레 기판 %.2f); "
     "위치 핀 ↔ 레일 %.2f, ↔ 리브 %.2f; 받침·머리·핀 ↔ 가장 가까운 BRD-01 부품 %.2f, ↔ 핀(지느러미) %.2f; 받침 Ø6은 기판 가장자리 밖으로 %.2f(받침은 기판 밑). "
     "나사 길이: 기판 %.1f + 받침 %.1f + 바닥 %.1f = %.1f, 끝 z%.1f, 구멍 끝 z%.1f(%.1f 남음), 구멍 밑 바닥 %.1f, 물림 %.1f. 건반·레버 ↔ 머리 스윕 %.2f", (PR["board_screw_real"][0], PR["board_screw_real"][1], PR["board_screw"][0], PR["board_screw"][1], min(q_["rail_top"] for q_ in _scr), min(q_["rib_top"] for q_ in _scr),
        min(q_["rib_top_axis"] for q_ in _scr if q_["rib_top_axis"] is not None), PR["board_x"][0], PR["board_x"][1], max(0.0, -min(q_["in_board"] for q_ in _scr)),
        min(q_["edge_ring"] for q_ in _scr), min(q_["rail_top"] for q_ in _pin), min(q_["rib_top"] for q_ in _pin), min(q_["part_min"][0] for q_ in C44["standoffs"]),
        min(q_["fin"] for q_ in C44["standoffs"]), _so0["past"], _so0["stack"][0], _so0["stack"][1], _so0["stack"][2], _so0["length"], _so0["tip_z"],
        _so0["bore_z"], _so0["bore_below_tip"], _so0["floor_under_bore"], _so0["engage"], C44.get("sweep_head", 0.0))),
     "수용 (부품 추가: 모듈당 나사 2)",
     "P35(새 치수), 프레임 출력에 받침 4·위치 핀 2(geometry 고정 부품 + 평면 원). 부품표에 ‘제어 기판 나사 M3×6 스텐 유두 렌치볼트(ISO 7380)’ 모듈당 2, 합계 14 — v3.2 구매 목록 L35(20개 800원)로 이미 기본 구성에 있어 비용 변화 0; 모듈 구매 부품 수 +2(r3 수 249에도 없던 v3.2 부품). "
     "r4.4 고침 2b: 바닥 받침 위로는 기판을 넣을 길이 없어(검증 critical) 같은 네 자리의 보스를 기판 위에 매달고 나사를 밑에서 조임 — 1e장 ‘고침 2b’, P35."),
    ("회로 4", "끝 부속 EL·ER: 센서 기판 받침(기둥 x0.5~6.0 + 앞·뒤 리브 = v3 P111~P113), 뒤 리브 틈 EL x15~38 · ER x6~16(리드 패드 J401 x18.41~28.57, J411 x8.25~13.33, y74.62), 리드 길 = 레일 밑 차선 z5~10(EL 5심 6.35, ER 3심 3.81 + 양옆 1.3) + 뒷벽 홈 z5~12. EL 기판 x1.0~46.5, ER x1.0~23.0",
     pf("EL 기판 x%.1f~%.1f가 센서 바 x%.1f~%.1f 안, ER x%.1f~%.1f가 x%.1f~%.1f 안. 뒤 리브 틈: 패드(±0.9) 여유 EL %.2f / %.2f, ER %.2f / %.2f; 아랫면 선이 리브 띠(y%.1f)에 드는 x — EL %s → %.2f / %.2f(B0 선 x%.2f), ER %s → %.2f / %.2f. "
     "리드 차선(레일 밑): EL %d심 %.2f + 1.3×2 = %.2f, x%s~%s(리드 가운데 x%.2f: A#0 흑 탭 받침 x22.93~30.93 y79~93이 바닥에 있어 그 왼쪽으로 %.2f 비껴 감; 차선 위 밸런스 핀 없음), "
     "ER %d심 %.2f + 2.6 = %.2f, x%s~%s(J411 가운데; C8 핀 밑 레일 %.1f — 모듈 리본 차선의 E·F 핀과 같음). 뒷벽 홈 같은 x z%.0f~%.0f: 뒤 도브테일과 %.2f / %.2f, 끝 핀과 %.2f / %.2f. "
     "리드 길(패드 줄에서 y%.2f까지 모음 + 곧은 길) ↔ 바닥 부품 최소 EL %.2f / ER %.2f(차선·홈 옆 레일·뒷벽 = 1.3; 모음 ↔ 뒤 리브 끝 %.2f, ER 받침 기둥 %.2f; 1차 시도 그림의 y78.89 모음은 탭 받침 모서리와 0.76). 끝 부속 스윕 최소 %.2f / %.2f(1.3 미만 0)", (_E["board"][0], _E["board"][1], _E["bar"][0], _E["bar"][1], _Rr["board"][0], _Rr["board"][1], _Rr["bar"][0], _Rr["bar"][1], _E["pad_margins"][0], _E["pad_margins"][1], _Rr["pad_margins"][0], _Rr["pad_margins"][1],
        PR["sb_rib_rear"][0], "/".join(pf("%.2f", v_) for v_ in _E["wire_cross"]), _E["wire_margins"][0], _E["wire_margins"][1], max(_E["wire_cross"]), "/".join(pf("%.2f", v_) for v_ in _Rr["wire_cross"]),
        _Rr["wire_margins"][0], _Rr["wire_margins"][1], _E["cores"], _E["lead_w"], _E["lane_w"], fh(_E["lane"][0]), fh(_E["lane"][1]), _E["lead_xc"], _E["fan_tab"],
        _Rr["cores"], _Rr["lead_w"], _Rr["lane_w"], fh(_Rr["lane"][0]), fh(_Rr["lane"][1]), _Rr["pins_over_lane"][0][2] if _Rr["pins_over_lane"] else 0.0, _E["notch_z"][0], _E["notch_z"][1],
        _E["dovetail_gap"], _Rr["dovetail_gap"], _E["fin_gap"], _Rr["fin_gap"], _E["fan_y"], _E["path_min"][0], _Rr["path_min"][0], _FAN["left_rib"], _FAN["right_post"],
        CL["end_parts"]["left"]["min"], CL["end_parts"]["right"]["min"])),
     "수용 (차선 x는 W1이 정함)",
     pf("A02·A03 치수, geometry 끝 부속에 센서 기판·받침 기둥·앞 리브·뒤 리브(틈)·레일 밑 차선(레일 밑면 z%.0f)·뒷벽 홈(‘rear wall (over the lead notch)’) + 평면(리드 패드·아랫면 선·리드 길·차선·홈). "
     "리드 길: 패드(아랫면) → 기판 밑 → 뒤 리브 틈 → 바닥(건반 밑; y%.2f까지 EL은 x%s~%s, ER은 x%s~%s로 모음) → 레일 밑 차선 → 바닥 → 뒷벽 홈 → 뒤 통로의 X401·X411.", (PR["lead_lane_z"][1], _E["fan_y"], fh(_E["lead"][0]), fh(_E["lead"][1]), fh(_Rr["lead"][0]), fh(_Rr["lead"][1])))),
    ("회로 5", "SB 뒤 받침 리브 틈 x60~82 → x59~82 (리본 x60.32~80.64가 왼쪽 0.32)",
     pf("v3 틈 x60~82면 리본 양옆 %.2f / %.2f; x59~82면 %.2f / %.2f(= 리본 차선); J201 패드(±0.9) %.2f / %.2f", (_rq["sb_gap_margins_r43"][0], _rq["sb_gap_margins_r43"][1], _rq["sb_gap_margins"][0], _rq["sb_gap_margins"][1], _rq["j201_margins"][0], _rq["j201_margins"][1])),
     "수용", pf("P36(새 치수): v3 센서 기판 받침(기둥 x%.1f~%.1f, 앞·뒤 리브 x%.1f~%.1f, 윗면 z%.1f)과 센서 기판을 모델·geometry에 넣고 뒤 리브를 x%.0f~%.0f에서 끊음.", (PR["sb_post"][0], PR["sb_post"][1], PR["sb_rib_x"][0], PR["sb_rib_x"][1], PR["sb_board"][4], PR["sb_rib_gap"][0], PR["sb_rib_gap"][1]))),
    ("회로 6", "금지 구역 끝을 y172.0으로 줄이거나, 제로 PCB가 y172.0~173.2에 걸치는 것을 P23에 적기",
     pf("제로 PCB(z%.1f~%.1f, 핀 헤더 위)가 x%.2f~%.2f × y%.1f~%.1f에 걸침; 헤더 열 x%.2f / x%.2f는 금지 구역 밖. 제로 앞 모서리 ↔ 핀 발 뒷면 %.2f, 제로 윗면 부품 ↔ 매달린 핀 밑면(z%.1f) %.2f — 두 안 모두 1.3을 지킴", (_zq["pcb_z"][0], _zq["pcb_z"][1], _zq["overhang"][0], _zq["overhang"][1], _zq["overhang"][2], _zq["overhang"][3], _zq["lattice_x"][0], _zq["lattice_x"][-1], _zq["foot_gap"], _zq["hung_fin_z"], _zq["to_hung_fin"])),
     "수용 (둘째 안)",
     pf("금지 구역은 만능기판 위 핀·패드·배선을 위한 것이라 y%.1f 그대로(홈 끝 잘린 면에서 %.1f; 잘린 면 바로 뒤 패드는 떨어지기 쉬움). P23에 ‘제로 PCB만 걸침, 그 안에 핀·패드·배선 없음’을 적음 — BRD-01 글과 같음.", (_zq["keepout"][3], PR["board_slot_keepout"]))),
    ("회로 7", "글: 1d장 C301은 1206 칩(리드형 아님). 도면 12: D#·F#·G 레버는 z20 한계가 아니라 기판 윗면에 떨어짐",
     pf("C301: 회로 BOM대로 1206 칩(아랫면). 건반 뺀 레버를 실제 BRD-01 부품·받침 머리·핀으로 떨어뜨리면: %s. z20 한계(어디에나 z20 부품이 있다고 볼 때)로는 %s", ("; ".join(pf("%s %.2f°(%s)", (k_, v_["actual"], _land_ko(v_["onto"]))) for k_, v_ in _dq.items())
        + pf("; O1·O7의 G는 R301(누운 1/4 W, Ø2.5 가정) 위 %.1f°", _dq["G"]["o17"]),
        ", ".join(pf("%s %.1f°", (k_, v_["generic"])) for k_, v_ in _dq.items()))),
     "수용 (O1·O7의 G는 R301; r4.5 회로 2차 고침: D#·G#는 기판 윗면이 아니라 매단 보스 위)",
     pf("1d장 C301 글 고침(위). 11장 6번 글을 실제 떨어짐으로 고침; 도면 12(도면 작성자)는 이 값으로 고쳐야 한다. 가장 깊은 떨어짐은 여전히 바닥판 %.2f°(%s)라 스프링 다리 검사 범위는 그대로.",
        (max(LD[k_]["drop_deg"] for k_ in ("C", "C#", "D", "A", "A#", "B")), "·".join(k_ for k_ in ("C", "C#", "D", "A", "A#", "B") if LD[k_]["drop_deg"] >= max(LD[q_]["drop_deg"] for q_ in ("C", "C#", "D", "A", "A#", "B")) - 1e-9)))),
]
for r_ in rows1d2:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w(pf("회로 쪽에 알릴 것(인터페이스): (1) 끝 부속 리드 차선 EL x%s~%s, ER x%s~%s(레일 밑 z%.0f~%.0f, 뒷벽 홈 z%.0f~%.0f 같은 x) — 리드는 패드 줄에서 기판 뒤끝 + %.1f(y%.2f) 안에 모아 EL x%s~%s, ER x%s~%s로(EL은 A#0 흑 탭 받침 왼쪽 %.2f). "
  "(2) 제어 기판 나사는 v3.2 L35 스텐 유두 렌치볼트(ISO 7380) 머리 Ø%.1f × %.2f(윗면 z%.2f; 모델 외곽 Ø%.1f × %.1f): 회로 △14의 Ø5.5 가정보다 머리 여유가 0.1 작아 레일 %.2f, 리브 %.2f(축 위 %.2f), 머리가 기판 모서리 밖 %.2f — "
  "DIN 912(Ø5.5 × 3.0)로 사면 회로 값 그대로. (3) 금지 구역은 y%.1f 그대로(P23에 제로 걸침을 적음). (4) O1·O7의 G 레버는 건반을 빼면 R301 위에 %.2f N으로 놓인다.", (fh(_E["lane"][0]), fh(_E["lane"][1]), fh(_Rr["lane"][0]), fh(_Rr["lane"][1]), PR["lead_lane_z"][0], PR["lead_lane_z"][1], PR["lead_notch_z"][0], PR["lead_notch_z"][1], PR["lead_fan"], _E["fan_y"],
     fh(_E["lead"][0]), fh(_E["lead"][1]), fh(_Rr["lead"][0]), fh(_Rr["lead"][1]), _E["fan_tab"],
     PR["board_screw_real"][0], PR["board_screw_real"][1], PR["board_z"][1] + PR["board_screw_real"][1], PR["board_screw"][0], PR["board_screw"][1],
     min(q_["rail_top"] for q_ in _scr), min(q_["rib_top"] for q_ in _scr), min(q_["rib_top_axis"] for q_ in _scr if q_["rib_top_axis"] is not None), max(0.0, -min(q_["in_board"] for q_ in _scr)),
     _zq["keepout"][3], _dq["G"]["F_rest"])))
w()
# r4.5 circuit 2nd cross-check (hardware/pcb README '2차 요청' 8-11)
_ef = C45["el_floor"]["now"]
_gl = [gh[k_] for k_ in GSM["armed"]]
w("**r4.5 회로 2차 대조** (2026-09-29, `hardware/pcb/README.md` ‘2차 요청’): 회로 세션이 r4.5 사본을 회로도 개정 B와 다시 맞춰 본 요청 가운데 8~11. 12(구매 목록 글)와 13(단계 0 시험 21 뒤 리본 차선을 바꾸면 알림)은 다른 곳에서 한다. 모든 값은 `run_all.py` 한 번(Q3절, E2절).")
w()
w("| # | 회로 쪽 요청 | 이 모델에서 잰 값 | 판정 | 바꾼 것과 결과 |")
w("|---|---|---|---|---|")
rows2nd = [
    ("8", "센서 바 오른쪽 턱(v3 P112, x161.5~164.5 × y59.0~63.4 · y70.6~77.5, 밑면 z13.6)을 모델에 넣거나, 턱 없이 바 오른쪽 끝을 무엇이 잡는지 P36에 적기",
     pf("r4.5 geometry에 턱이 없음 — 바·기판(x0.5~%.1f)의 오른쪽 끝을 잡는 것이 없었다: 왼쪽 M3×10 2개(x3.0)와 리브(z%.1f 받침, x%.1f까지)뿐이라, 모듈을 뒤집어 제어 기판을 넣을 때(10장 1단계) 바·기판이 왼쪽 나사에만 매달린다. 모델이 출발한 v3 프레임 질량 175 g에는 턱이 들어 있고 r4 내보냄에서만 빠졌다",
        (L8["bar_end"], PR["sb_board"][4], PR["sb_rib_x"][1])),
     "받아들임 (모델에 넣음)",
     pf("P36·고정 부품·평면·스윕: 두 조각 y%.1f~%.1f · y%.1f~%.1f(B 센서 리드 줄 y%.1f~%.1f와 %.1f / %.1f), 각각 ㄱ자 — 립 x%.1f~%.1f z%.1f~%.1f(밑면 = 백 구간 바 윗면 z%.1f, 바 끝을 %.1f 덮음, %.1f mm²), 기둥 x%.1f~%.1f 바닥 z%.1f부터(바 끝과 %.1f, 기판 끝과 %.1f). "
        "x 끝은 v3 164.5가 아니라 %.1f(r4 이음 면 0.2 들임, 핀·윗판과 같음). 립은 B 리드 구멍 열 x%.2f에서 %.2f. 가장 가까운 움직이는 부품 %.2f(공차 뒤 %.2f, %s); 이음매 너머 고정 부품: 이웃 모듈 %.2f(%s), 끝 부속 ER %.2f; 기판 부품 구역(아랫면 C214 x%.1f~%.1f, J201) 밖. "
        "바·기판은 모듈을 따로 둔 채 1.5 mm 왼쪽에 내려놓고 오른쪽으로 밀어 턱 밑에 넣은 뒤 왼쪽 나사를 조인다(v3 절차). 끝 부속 바(EL %.1f mm, ER %.1f mm)는 턱 없이 같은 왼쪽 M3 2개 + 리브(짧고, 기판 넣기로 뒤집지 않음)",
        (PR["sb_ledge_y"][0][0], PR["sb_ledge_y"][0][1], PR["sb_ledge_y"][1][0], PR["sb_ledge_y"][1][1], L8["lead_y"][0], L8["lead_y"][1], L8["lead_y_gaps"][0], L8["lead_y_gaps"][1],
         PR["sb_ledge"][0], PR["sb_ledge"][1], PR["sb_ledge"][3], PR["sb_ledge"][4], PR["bar_top_w"], L8["over_bar"], L8["held_area"], PR["sb_ledge"][1], PR["sb_ledge"][2], PR["z_floor"][1], L8["post_to_bar"], L8["post_to_board"],
         PR["sb_ledge"][2], L8["B_lead_col"], L8["lip_to_B_col"], L8["sweep"]["d"], L8["sweep_after_tol"], tr(L8["sweep"]["a"] + " " + L8["sweep"]["part_a"]) + " " + POSE.get(L8["sweep"]["pose_a"], L8["sweep"]["pose_a"]),
         L8["neighbour_module"][0], tr(L8["neighbour_module"][2] or "-"), L8["end_part_ER"][0], L8["c214"][0], L8["c214"][1],
         L8["ends"]["left"]["bar"][1] - L8["ends"]["left"]["bar"][0], L8["ends"]["right"]["bar"][1] - L8["ends"]["right"]["bar"][0]))),
    ("9", "유령 거름(U6) 글을 run_all.py gfilter와 같게(창 = note-on부터 재무장까지 250 ms), 무장된 28건을 1 s 이상 돌려 유령이 다시 닿는 시각(ghost_reland)으로 ‘다시 눌림 시각 상한’ 정하기",
     pf("맞음: 글(0.1)은 ‘%.0f ms 안에 다시 눌림’, gfilter는 ‘note-on부터 재무장이 %.0f ms 안’(다시 눌림 시각은 안 봄). 게다가 누른 채 계산이 %.0f ms에서 끝나 다시 닿음은 한 번도 계산 안에 없었다(내려옴 0.00 = 아직 안 내려옴). "
        "재무장 %d건을 note-on 뒤 %.1f s까지 다시 돌리면: 스스로 다시 닿는 것 %d건%s; 재무장 %.1f ms 안, 흔들림 멈춤 ≤ %.0f ms, 끝 자석 위치 %.0f~%.0f %%, 끝 기어내림 ≤ %.4f m/s(자석; 모델 마찰이 0.2 mm/s 아래에서 비례라 생기는 값)%s",
        (PR["ghost_win"], PR["ghost_win"], 320.0, len(GSM["armed"]), PR["ghost_long"] / 1000.0, len(GSM["relanded"]), (pf(" (가장 늦게 %.0f ms)", GSM["reland_max"]) if GSM["relanded"] else ""), GSM["t_arm_max"], GSM["settle_max"],
         100 * GSM["frac_end"][0], 100 * GSM["frac_end"][1], GSM["creep_max"], (pf(" → 그 속도로 가장 빨라도 %.1f s 뒤 바닥", GSM["land_est_min"] / 1000.0) if GSM["land_est_min"] else ""))),
     "받아들임",
     pf("글(0.1·0.2·7.3·7.4·18장, 시험 11)과 gfilter를 SCH-03 주 9 형태 + **다시 눌림 시각 상한 = note-on부터 %.0f ms**로. 기구는 상한을 정하지 않는다(0.45~0.5 N 손가락이 건반을 뜬 자리에 붙잡아 유령이 스스로 오지 않음) — 유령 다시 눌림은 손가락이 만든다. "
        "%.0f ms = 흔들림이 멈추는 가장 늦은 %.0f ms의 약 2배; 단계 0 시험 11의 펌웨어 기록에서 유령 다시 눌림이 %.0f ms를 넘으면 창 = (가장 늦은 것 + 100 ms). 못 거른 것 %d / %d",
        (PR["ghost_rep_max"], PR["ghost_rep_max"], GSM["settle_max"], PR["ghost_rep_max"], len(GSM["not_dropped"]), GSM["n"]))),
    ("10", "DESIGN 11장 6단계 글: D#·G# 레버는 기판 윗면이 아니라 매단 보스 위(16.75°)",
     "맞음: 글은 ‘D#·F#·G·G#가 기판 윗면(z10.6, 16.8~24.0°)’, geometry(`circuit_r44.drop`)·도면 12는 " + "; ".join(pf("%s %.2f°(%s)", (k_, DQ[k_]["deg"], _land_ko(DQ[k_]["onto"]))) for k_ in ("D#", "E", "F", "F#", "G", "G#")),
     "받아들임",
     "11장 6단계, 10장 5단계, 1장 L 블록 행, 1d-2 회로 7 판정 글을 이 값으로(바뀐 수치 없음)"),
    ("11", "끝 부속 EL 바닥에 모듈 기판 구멍 자르기가 새어 생긴 틈 x46.25~46.8 × y144.5~196.5 없애기",
     "맞음: `end_fixed_prisms`가 모듈 바닥(기판 구멍 x46.25~118.25 y144.5~196.5가 잘린 조각들)을 끝 부속 x0.2~46.8로 잘라 그 틈이 EL 바닥에 남았다(EL엔 제어 기판이 없음)",
     "받아들임",
     pf("끝 부속은 기판 구멍 없는 모듈 바닥을 받는다(구멍은 모듈에만): EL 바닥 %s, 구멍 %s; ER %s. 질량은 이미 구멍 없이 셈",
        (" · ".join(pf("x%.2f~%.2f y%.0f~%.0f", tuple(q_)) for q_ in _ef["left"]["pieces"]), ("없음" if not _ef["left"]["gaps"] else str(_ef["left"]["gaps"])), " · ".join(pf("x%.2f~%.2f y%.0f~%.0f", tuple(q_)) for q_ in _ef["right"]["pieces"])))),
]
for r_ in rows2nd:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w(pf("회로 쪽에 알릴 것: 인터페이스 값은 하나도 바뀌지 않았다(리본 차선 x%.0f~%.0f z5~10, SB x%.1f~%.1f, EL·ER 기판·리드 차선, 제어 기판·바닥 구멍·보스, 플러그 z%.1f~%.1f). "
     "BRD-02의 점선 턱은 실선으로: x%.1f~%.1f(x164.5가 아니라 이음 면에서 0.2 안) × y%.1f~%.1f · y%.1f~%.1f, 밑면 z%.1f. SCH-03 주 9의 ‘다시 눌리는 시각 상한’ = note-on부터 %.0f ms.",
     (PR["ribbon_x"][0], PR["ribbon_x"][1], PR["sb_board"][0], PR["sb_board"][1], PR["usb_z"][0], PR["usb_z"][1], PR["sb_ledge"][0], PR["sb_ledge"][2], PR["sb_ledge_y"][0][0], PR["sb_ledge_y"][0][1],
      PR["sb_ledge_y"][1][0], PR["sb_ledge_y"][1][1], PR["sb_ledge"][3], PR["ghost_rep_max"])))
w()
w(pf("**회로 v10 뒤 (2026-09-29).** 회로 세션이 BRD-02에 턱을 그리면서 SB 만능기판 오른끝을 x162.9 → **x%.1f**(으)로 0.3 줄였다. 손으로 자른 기판은 ±0.3이 나므로, 바를 턱 밑으로 밀 때 기둥(x%.1f)에 걸리지 않게 하려는 것이다. 기판 끝 ↔ 턱 기둥 0.1 → %.1f, B 센서 리드 패드(x160.65)와는 1 mm 넘게 남는다. 센서 바는 x162.9 그대로다. 모델 `sb_board`만 바꿨고 run_all을 다시 돌렸다: 판정 45개 통과, 바뀐 값은 SB 기판 끝과 이 틈뿐.", (PR["sb_board"][1], PR["sb_ledge"][1] if len(PR["sb_ledge"]) > 1 else 163.0, 163.0 - PR["sb_board"][1])))
w()
# ============================================================================================ 1d-3 (r4.4 open issue 4: USB-C cable)
w("### 1d-3. USB-C 케이블 — 한계 안에 드는 실제 선 (r4.4, 남은 문제 4)")
w()
_uw, _ut = PR["usb_x"][1] - PR["usb_x"][0], PR["usb_z"][1] - PR["usb_z"][0]
w(pf("**한계(동결, 회로 세션 소유)**: C 쪽 몰드 폭 ≤ %.1f, 두께 ≤ %.1f, 부트를 포함한 길이 ≤ 25. 곧은 플러그, 데이터선이어야 한다. 플러그는 z%.1f~%.1f, 면 y%.1f(몰드 y%.1f~%.1f)에 놓인다. "
     "플러그는 선반 홈 가장자리와 %.2f 떨어져 있다. 이 한계는 바꾸지 않았다.", (_uw, _ut, PR["usb_z"][0], PR["usb_z"][1], PR["usb_y"][0], PR["usb_y"][0], PR["usb_y"][1], Q43["usb"]["each"]["rear shelf"])))
w()
w("**무엇을 잇나**: 선 목록 `hardware/pcb/netlist/cables.csv`. 모듈 O1~O7의 RP2040-Zero에서 USB 허브(NEXTU 710U3, 다운스트림이 USB-A)까지 USB-A(수) → USB-C(수) 1 m 선 7가닥(W201~W207), "
  "페달 보드에 같은 선 1가닥(W208). 모두 8가닥이고 USB 2.0이다. 허브 쪽이 USB-A라 C-C 선은 못 쓴다. 몰드 한계가 걸리는 것은 모듈 7가닥이다. 끝 부속 EL·ER에는 USB가 없다.")
w()
w("**지금 구매 목록 줄(v4 22번 줄, C04)**: Coms NA993 USB-A → C 1 m, 1,620원 × 8 = 12,960원(엘레파츠). 판매 페이지와 제조사 상세 이미지에 C 쪽 몰드 치수가 없다. "
  "사진으로 재면 폭 약 11.3, 길이 약 19.5지만 두께를 알 수 없다. 그래서 ‘확인 안 됨’이다(목록 메모의 ‘≤ 12.5 × 7.5 × 25’도 확인된 값이 아니다).")
w()
w("| 후보 | 판매처 | C 몰드 폭 × 두께 × 길이 | 치수 출처 | 판정 | 8개 (배송 포함) |")
w("|---|---|---|---|---|---|")
_CBV = {True: "맞음", False: "맞지 않음"}
for c_ in CB["candidates"]:
    _dim = (pf("%s × %s × %s%s", (fz(c_["plug_w_mm"]), fz(c_["plug_t_mm"]), "" if c_["dims_verified"] else "약 ", fz(c_["plug_l_mm"])))) if c_["plug_t_mm"] else \
        (pf("꺾임 몸체 %s × (두께 미공개) × %s", (fz(c_["plug_w_mm"]), fz(c_["plug_l_mm"]))))
    if "CNC" in c_["name"]:
        _vd = "못 씀: 충전 전용(데이터선 없음)"
    elif "ㄱ자" in c_["name"]:
        _vd = "못 씀: 꺾임 몸체가 프레임 안에서 꺾일 자리 없음"
    elif c_["fits"]:
        _vd = "**맞음 (권장)**"
    else:
        _vd = "맞지 않음: 길이 > 25" + ("(추정값)" if not c_["dims_verified"] else "(부트 포함)")
    _src = c_["dims_source"].split(":")[0].split("(")[0].strip()
    w(pf("| %s | %s | %s | %s%s | %s | %s |", (esc(c_["name"].split(" — ")[0]), c_["store"].split(" (")[0], _dim, _src, "" if c_["dims_verified"] else " (길이는 축척 추정)", _vd,
                                                krw(c_["qty_needed"] * c_["price_krw"] + c_["shipping_krw"]))))
w()
_cb8 = CBR["qty_needed"] * CBR["price_krw"] + CBR["shipping_krw"]
w(pf("**권장**: C04 줄을 **CVILUX DH-20M50052** 8개로 바꾼다(DigiKey Korea 2987-DH-20M50052-ND, USB 2.0 A(수) → C(수) 곧은 플러그, 1 m, 차폐). "
     "몰드 치수(%.2f × %.2f × %.2f)는 DigiKey TechForum ‘Overmold size of the USB-C male end’에 지원 담당이 캘리퍼로 잰 사진 4장으로 확인된다. 제조사 도면에는 금속 쉘 6.65, 케이블 Ø3.5, 데이터 꼬임쌍만 있다. "
     "몰드가 플러그 가운데라고 보면 선반 홈 가장자리 틈이 1.30에서 약 1.57로, 건반 꼬리·쉼 펠트와 플러그 윗면의 틈이 1.38에서 약 1.97로 는다. 길이는 25보다 4 짧다. "
     "값: 1개 %s원 × 8 + 배송 %s원 = %s원(지금 NA993보다 %s원). 10개면 22,009원 + 배송으로 예비 2개가 생긴다. 디지키에서 6만 원 넘게 함께 사면 배송비가 없다. 인터페이스는 바꾸지 않는다.",
     (CBR["plug_w_mm"], CBR["plug_t_mm"], CBR["plug_l_mm"], krw(CBR["price_krw"]), krw(CBR["shipping_krw"]), krw(_cb8), skrw(_cb8 - 12960))))
w()
w("**확인과 대안**: (1) 받으면 캘리퍼로 C 쪽 몰드를 잰다. 폭(로고 돌기 포함 최댓값) ≤ 12.5, 두께 ≤ 7.6, 부트 포함 길이 ≤ 25, 몰드가 금속 쉘 가운데(좌우·위아래 차이 ≤ 0.6)여야 한다. "
  "데이터선인지는 RP2040-Zero의 BOOTSEL을 누른 채 PC에 꽂아 RPI-RP2 드라이브가 뜨는지로 본다. (2) 단계 0 키트의 C13a 몰드 게이지(12.5 × 7.6 창, 길이 25)에 끝까지 들어가야 한다. "
  "최종 확인은 17장 시험 19다. (3) 몰드를 칼이나 줄로 깎지 않는다(차폐와 스트레인 릴리프가 드러나 끊긴다). "
  "(4) 확인된 선을 못 구하면 인터페이스 완화를 회로 세션에 요청한다: 길이만 ‘딱딱한 몰드 ≤ 25, 부트 포함 ≤ 35’(뒷벽 밖은 열린 통로). 그러면 NETmate NM-GCM01BN(8개 23,040원, 엘레파츠 합배송)이 가장 싸다. "
  "폭·두께는 늘리지 않는다(선반 홈을 넓히면 F·F# 쉼 펠트 착지가 줄어든다). 알리익스프레스는 몰드 치수를 공개한 판매 페이지를 찾지 못했다. 자료: `../cable/result.json`, `../cable/img/`.")
w()
# ============================================================================================ 1e (r4.4)
w("## 1e. r4.3 → r4.4 남은 문제 해결")
w()
w("남은 문제 7건 가운데 형상 1~3은 이 장에서 다룬다. 4(USB-C 케이블)는 1d-3장, 5(RP2040-Zero 높이 한계)는 18장, 6(문서)은 5장 머리(반올림)·13·15장(부품표와 맞춤)·10.1장(출력 공구), 7(시험 가정)은 17.1장(단계 0 키트)이다.")
w()
w(pf("r4.3의 남은 문제(`report_r4/open_issues.r4_3.json`) 중 형상 3건. 다시 돌린 범위: 한 모듈(옥타브 모듈은 모두 같다; 대표 백 D·흑 C#, 착지 문제는 F·F# 자기 건반), 바뀐 캐리어·봉 마개가 닿는 끝 부속 A0·C8; "
  "PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45 / 1 / 2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악; 모든 계산은 `run_all.py` 한 번(스윕 모듈 %d쌍, 끝 부속 %d / %d쌍). 부품은 늘리지 않았다. "
  "고침 1회차에서 제어 기판 인터페이스는 하나도 바뀌지 않았다(회로 세션 대조로 바뀐 값은 1d-2장): USB-C 플러그 %.1f × %.1f × 25 (z%.1f~%.1f), 선반 홈 x%.2f~%.2f(플러그와 %.2f), 제로 윗면 부품 z%.1f 이하·y%.1f~%.1f 띠 z%.1f 이하, 선반 밑면 z%.2f, 뒷벽 개구 z%.0f~%.0f, 금지 구역 x%.2f~%.2f × y%.1f까지.", (CL["n_pairs"], CL["end_parts"]["left"]["n"], CL["end_parts"]["right"]["n"], PR["usb_x"][1] - PR["usb_x"][0], PR["usb_z"][1] - PR["usb_z"][0], PR["usb_z"][0], PR["usb_z"][1],
     Q43["usb"]["slot"][0], Q43["usb"]["slot"][1], Q43["usb"]["each"]["rear shelf"], PR["zero_z"][2], PR["comp_rear"][0], PR["board_y"][1], PR["comp_rear"][1], H["z_shelf"] - 2.0,
     PR["usb_wall_open"][2], PR["usb_wall_open"][3], G["solved"]["fins"][2][0] - PR["board_slot_keepout"], G["solved"]["fins"][2][1] + PR["board_slot_keepout"], PR["board_slot_y1"] + PR["board_slot_keepout"])))
w()
ZS = R["steel_retention"]["zones"]
ZS43 = R["steel_retention"]["zones_r43"]
w("### 문제 1 — 레버 윗 스냅 립이 패드 옆으로 들어감 (+ 립·핀 보스 구멍·봉 마개를 geometry·스윕에)")
w()
w(pf("다시 잰 값: r4.3 윗 립(0.8×1.0, 레버 좌표 y150~168·184~186, 강철 윗면 위 x ±3.7~4.5)을 이 모델에 넣고 자기 패드(x ±3.0, 월드 y170~182)와 모든 자세로 쟀다. x 틈은 0.70인데 레버 요(±%.2f, 캐리어 앞에서)를 빼면 %.2f이고, "
  "레버가 1 N 바닥(%.2f°)만 가도 앞 립 뒤끝 모서리(y168 z53)가 월드 y%.2f z%.2f — 패드 y 구간 안 — 로 올라와 y·z로 겹친다: 최소 %.2f(공차 뒤 %.2f, 규칙 1.0). 강체 바닥·ff에서도 같다. 뒤 립(y184~186)은 패드와 %.1f 이상.", (0.10, CL["lip43"]["d"], R["heights"]["held_pad_b_w"], CL["lip43"]["corner"][0], CL["lip43"]["corner"][1], CL["lip43"]["d"], CL["lip43"]["d"] - 0.3, 3.2)))
w()
w("| 항목 | r4.3 | r4.4 |")
w("|---|---|---|")
rows_ = [
    ("앞 윗 립 (레버 좌표)", "y150~168 (y150~153은 전폭 뚜껑)", pf("y%.0f~%.0f (같은 뚜껑) — 5.0 짧게", tuple(PR["lip_segs"][0]))),
    ("뒤 윗 립", "y184~186 (길이 2)", pf("y%.0f~%.0f (길이 %.0f, 뒷벽까지)", (PR["lip_segs"][1][0], PR["lip_segs"][1][1], ZS["L_rear"]))),
    (pf("옆벽 윗단 z%.0f", (PR["z_st"] + PR["lip"])), "y150~168, y184~186", pf("립과 같은 구간만 (그 사이 z%.0f)", PR["z_st"])),
    ("립 ↔ 자기 패드 (모든 자세)", pf("%.2f (공차 뒤 %.2f) — %s 자세, 레버 %s", (CL["lip43"]["d"], CL["lip43"]["d"] - 0.3, POSE.get(CL["lip43"]["pose"], CL["lip43"]["pose"]), CL["lip43"]["lever"])),
     pf("%.2f (공차 뒤 %.2f)", (CL["lip44"]["pad"], CL["lip44"]["pad"] - 0.3))),
    ("립 ↔ 패드 바·레일", "검사 안 됨", pf("%.2f (공차 뒤 %.2f)", (CL["lip44"]["rail"], CL["lip44"]["rail"] - 0.3))),
    ("립이 geometry.json·스윕에", "없음 (옆벽 윤곽 안, 글에만)", pf("레버 부품 `carrier top snap lip L/R y…` — 모든 자세(쉼·1 N 바닥·강체 바닥·ff·복귀 넘침·서비스); 스윕 최소 %.2f (%s)", (CL["lip44"]["min"], tr(CL["lip44"]["pair"])))),
    ("핀 보스 구멍·레버 봉·봉 마개", "글만 (‘Ø3.9 → Ø4.0 드릴’, ‘마개 1.2’, ‘막힌 벽 1.2’)",
     pf("고정 부품 `fin boss bore D4.0`(핀 %d장, 오른쪽 끝 핀은 x%.1f까지 막힘), `lever rod D4` x%.1f~%.1f, `lever rod end plug` x%.1f~%.1f(끝 핀 면과 같게), 평면도 포함; 끝 부속은 이음 쪽 핀에 마개; "
     "축 놀음 %.2f + %.2f(봉 ±0.2면 %.2f~%.2f); 스윕에서 가장 가까운 움직이는 부품 %.2f", (CL["rod"]["n_bores"], CL["rod"]["blind_end"], CL["rod"]["rod"][0], CL["rod"]["rod"][1], CL["rod"]["plug"][0], CL["rod"]["plug"][1], CL["rod"]["play_left"], CL["rod"]["play_right"],
        CL["rod"]["play_left"] + CL["rod"]["play_right"] - 0.2, CL["rod"]["play_left"] + CL["rod"]["play_right"] + 0.2, CL["rod"]["sweep_min"][0]))),
    ("모듈 스윕 최소 (공차 뒤)", pf("%.2f (%.2f) — 립 빠짐", (R43M["clear"]["min"], R43M["clear"]["min"] - 0.3)), pf("%.2f (%.2f), %d쌍 중 1.3 미만 %d", (M["min_clearance_mm"], M["min_clearance_after_tol_mm"], CL["n_pairs"], CL["n_bad"]))),
]
for r_ in rows_:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w(pf("레버 질량 모델은 r4.3까지 윗 립을 y150~186 전체로(끊긴 구간까지) 세고 옆벽 윗단도 전 구간 z53으로 셌다. 고치니 레버가 57.21 → 57.13 g으로 가벼워졌고(고침 2의 옆벽 낮춤까지 넣은 지금 값 %.2f g), ff 최대각이 %.2f° → %.2f°로 커지고, 칸 가장자리 레버 옆벽 ↔ 패드 바 레일 웹 앞 아래 모서리(y%.0f z%.2f)가 1.32 → 1.30이 되었다. "
  "그 모서리를 %.1f×45° 모따기해(패드 바는 그 위 z%.2f 위로만 지나감) %.2f(공차 뒤 %.2f). 가벼워진 레버의 여파로 DW 목표에 맞춘 캡스턴 y가 백 %.2f → %.2f, 흑 %.2f → %.2f, "
  "1 N 정착 바닥에 맞춘 패드 면·출력 쐐기가 %.3f 이하로 바뀌었다(고침 2의 선반 +0.05 포함; 1b장 ‘solved values’ 두 행).", (W["lever_g"], R43M["heights"]["b_ff_w"], H["b_ff_w"], PR["rail_y0"], H["z_seat"] - PR["bar_rail"][1],
     PR["rail_front_chamfer"], H["z_seat"] - PR["bar_rail"][1] + PR["rail_front_chamfer"], NM["레버 ↔ 패드 바·레일"]["d"], NM["레버 ↔ 패드 바·레일"]["after_tol"],
     R43M["white"]["y_cap"], W["y_cap"], R43M["black"]["y_cap"], B["y_cap"],
     max(abs(H["wedge"]["w"][0] - R43M["heights"]["wedge"]["w"][0]), abs(H["wedge"]["w"][1] - R43M["heights"]["wedge"]["w"][1]), abs(H["wedge"]["b"][0] - R43M["heights"]["wedge"]["b"][0]),
         abs(H["pad_face_w"][0] - R43M["heights"]["pad_face_w"][0]), abs(H["pad_face_w"][1] - R43M["heights"]["pad_face_w"][1])))))
w()
w(pf("**강철 블록 유지 (숫자로).** 강철은 밑에서 끼워 아래 립을 넘기고(스냅), 위로는 앞 뚜껑(y150~153, 전폭 9 × 1.0) + 윗 립, 앞뒤는 앞벽·뒷벽, 옆은 옆벽이 막는다 — 아래 립 쪽 말고는 기하로 갇혀 있다. "
  "힘은 4-DOF 동역학의 매 스텝에서 강철을 떼어 놓고 구했다: 캡스턴 펠트와 패드는 강철에 바로 닿으므로, 레버의 각가속도로 강철이 따라가는 데 필요한 힘·모멘트를 캐리어가 준다. 이것을 세 구역(윗 앞 = 뚜껑 + 앞 립, 윗 뒤 = 뒤 립, 아래 = 아래 립; 각 면적 중심 y%.1f / %.1f / %.2f)으로 나눴다. "
  "립 뿌리 굽힘은 층간(캐리어는 옆벽을 베드에 눕혀 출력): σ = 3 F a / (L t²), a = 물림 폭의 절반(고른 접촉, 상한). 한계: 매 음 %.0f MPa, 화음·ABUSE %.0f MPa.", (ZS["yf"], ZS["yr"], ZS["yb"], PR["s_cyc"], PR["s_rare"])))
w()
w("| 구역 | r4.3 립: 최대 힘 → 뿌리 응력 (PLAY / 화음 / ABUSE) | r4.4 립 | 판정 |")
w("|---|---|---|---|")
w(pf("| 윗 앞 (뚜껑 + 앞 립 %.0f → %.0f) | %.1f / %.1f / %.1f N → 립만 %.1f / %.1f / %.1f MPa | %.1f / %.1f / %.1f N → 립만 %.1f / %.1f / %.1f MPa (뚜껑 몫을 빼지 않은 상한) | 통과 |", (ZS43["L_front"], ZS["L_front"], RT["play"]["T_front_r43"], RT["chord"]["T_front_r43"], RT["abuse"]["T_front_r43"], RT["play"]["sig_front_r43"], RT["chord"]["sig_front_r43"], RT["abuse"]["sig_front_r43"],
     RT["play"]["T_front"], RT["chord"]["T_front"], RT["abuse"]["T_front"], RT["play"]["sig_front"], RT["chord"]["sig_front"], RT["abuse"]["sig_front"])))
w(pf("| 윗 뒤 (뒤 립 %.0f → %.0f) | %.1f / %.1f / %.1f N → **%.1f** / %.1f / %.1f MPa (매 음 5 초과) | %.1f / %.1f / %.1f N → %.1f / %.1f / %.1f MPa | 통과 (r4.3은 매 음 초과였음) |", (ZS43["L_rear"], ZS["L_rear"], RT["play"]["T_rear_r43"], RT["chord"]["T_rear_r43"], RT["abuse"]["T_rear_r43"], RT["play"]["sig_rear_r43"], RT["chord"]["sig_rear_r43"], RT["abuse"]["sig_rear_r43"],
     RT["play"]["T_rear"], RT["chord"]["T_rear"], RT["abuse"]["T_rear"], RT["play"]["sig_rear"], RT["chord"]["sig_rear"], RT["abuse"]["sig_rear"])))
w(pf("| 아래 립 (1.0×1.0, 길이 %.1f, 바꾸지 않음) | %.1f / %.1f / %.1f N | %.1f / %.1f / %.1f N → **%.1f** / %.1f / %.1f MPa (뿌리 쪽 접촉이면 %.1f / %.1f / %.1f) | ABUSE 통과, 매 음은 상한 %.1f가 5를 넘음 → 18장·단계 0 시험 20 |", (ZS["L_bottom"], RT["play"]["B_r43"], RT["chord"]["B_r43"], RT["abuse"]["B_r43"], RT["play"]["B"], RT["chord"]["B"], RT["abuse"]["B"], RT["play"]["sig_bottom"], RT["chord"]["sig_bottom"], RT["abuse"]["sig_bottom"],
     RT["play"]["sig_bottom_root"], RT["chord"]["sig_bottom_root"], RT["abuse"]["sig_bottom_root"], RT["play"]["sig_bottom"])))
w()
_CW = dict(white="백", black="흑", single="한 건반", chord="화음 자리", chord20="2.0 m/s 화음", release="1 N에서 뗌", press="누름", nom="공칭", passline="합격선", worst="최악", rel="뗌")


def _case_ko(c_):
    out_ = []
    for t_ in str(c_).split():
        if t_.startswith("v") and t_[1:2].isdigit():
            out_.append(t_[1:] + " m/s")
        elif t_.startswith("h") and t_[1:2].isdigit():
            out_.append(pf("%.2g N 누름", float(t_[1:])))
        else:
            out_.append(_CW.get(t_, t_ + (" N" if t_.replace(".", "").isdigit() else "")))
    return " ".join(out_)


w(pf("- 가장 큰 경우: 윗 앞 %s, 윗 뒤 %s, 아래 %s. 윗 뒤 립 힘은 캡스턴이 강철 뒤끝(y188)을 밀어 올리고 봉이 허브를 당겨 내리는 짝힘이라 캡스턴이 미는 매 음 생긴다 — r4.3의 2 mm 립은 이 힘에 층간 %.1f MPa였다(검사하지 않았음). "
  "아래 립 힘은 패드가 강철 윗면을 누를 때 봉 반력이 캐리어를 통해 강철을 받치는 힘이다.", (_case_ko(RT["abuse"]["case"].get("T_front", "")), _case_ko(RT["play"]["case"].get("T_rear", "")), _case_ko(RT["abuse"]["case"].get("B", "")), RT["play"]["sig_rear_r43"])))
w(pf("- 취급·운반: 강철 %.2f N. %.0f MPa(드문 하중)에 닿는 충격은 위로(모듈 뒤집힘) 뒤 립 %.0f g, 앞 립 %.0f g(뚜껑 빼고), 아래로 %.0f g. 뒤집어 둔 상태(1 g)면 뒤 립에 %.2f N.", (RT["transport"]["weight_N"], PR["s_rare"], RT["transport"]["n_up_rear"], RT["transport"]["n_up_front"], RT["transport"]["n_down"], RT["transport"]["weight_N"] * (ZS["yf"] - ZS["com"][0]) / (ZS["yf"] - ZS["yr"]))))
w()
w(pf("### 문제 2 — F·F# 쉼 펠트 부분 착지 (복귀 넘침 자세 스윕, 약한 6건반 화음 자리 %.0f N/mm 동역학)", Q44["k_ch"]))
w()
w(pf("다시 잰 값: F·F#를 자기 건반 몸체·자기 착지 비율(쉼 펠트 접촉 강성 × 착지 폭 / 8.0, r4.3의 방법)로 화음 자리(%.0f N/mm)에서 PLAY 격자, ABUSE 2.5 m/s(요청대로 화음 자리, 그리고 한 건반 자리 %.0f), ABUSE 2.0 m/s 화음(%.0f), 뗌(마찰 1·2배)을 공칭·합격선·최악 재료로 돌렸다. "
  "동역학 목표는 r4.3 펠트로도 통과했지만, 무른 착지 때문에 복귀 때 꼬리가 더 깊이 내려가고 레버가 더 내려간다. 그 복귀 넘침 자세(공칭 + 합격선; r4.3처럼 PLAY + ABUSE 한 건반에 화음 자리 PLAY를 더함, 레버 여유 0.25°는 전과 같음)로 모듈을 스윕하니 **%d쌍이 1.3 미만**: %s. "
  "ABUSE 6건반 화음(2.0 m/s)과 요청한 화음 자리 2.5 m/s의 복귀 넘침은 ABUSE 규칙(손상 없음 = 닿지 않음)으로 따로 쟀다.", (Q44["k_ch"], SEAT["k_min"], Q44["k_ch_ab"], CL["r43_felts"]["n_bad"], "; ".join(pf("%s %s ↔ %s%s %.2f", (tr(q_["a"]), tr(q_["part_a"]), tr(q_["b"]), (" " + tr(q_["part_b"])) if q_["part_b"] else "", q_["d"])) for q_ in CL["r43_felts"]["bad"]))))
w()
w(pf("고침(부품 추가 없음, 출력 부품 그대로, 회로 인터페이스 그대로): USB 홈에 걸리던 두 쉼 펠트를 **홈 가장자리에서 자르고 반대쪽으로 꼬리 끝까지** 붙인다 — F는 흰 꼬리가 빔과 같은 8.0이라 x%.2f~%.2f(착지 그대로 %.0f %%, 홈 위로 나오던 %.2f를 없앰), "
  "F#는 흑 꼬리가 10.0이라 x%.2f~%.2f까지 넓혀 착지 %.0f → %.0f %%. 탐색한 다른 안: F 얇은 꼬리에 쉼 발(2.5면 착지 91 %%) — F를 앞으로 뽑을 때 발이 E 건반 꼬리 옆벽을 침(뽑기 경로 −4.99), 1.0 이하면 착지 이득이 작음; F# 발 2.0(80 %%) — 굴림 되돌림/넘김 비 1.03.", (Q44["land"]["F"]["felt"][0], Q44["land"]["F"]["felt"][1], 100 * Q44["land"]["F"]["frac"], Q44["land43"]["F"]["felt"][1] - Q44["land"]["F"]["felt"][1],
     Q44["land"]["F#"]["felt"][0], Q44["land"]["F#"]["felt"][1], 100 * Q44["land43"]["F#"]["frac"], 100 * Q44["land"]["F#"]["frac"])))
w()
L43, L44 = Q44["land43"], Q44["land"]
def _ls(tag_, nm_, mat_):
    return LS4[pf("%s_%s_%s", (tag_, nm_, mat_))]
w("| 항목 | r4.3 | r4.4 |")
w("|---|---|---|")
rows2 = []
for nm_ in ("F", "F#"):
    rows2.append((pf("%s 쉼 펠트 / 선반에 앉는 폭", nm_), pf("x%.2f~%.2f / x%.2f~%.2f (%.0f %%, 반력이 레버 선에서 %+.2f)", (L43[nm_]["felt"][0], L43[nm_]["felt"][1], L43[nm_]["segs"][0][0], L43[nm_]["segs"][0][1], 100 * L43[nm_]["frac"], L43[nm_]["dx"])),
                  pf("x%.2f~%.2f / 전부 (%.0f %%, %+.2f)", (L44[nm_]["felt"][0], L44[nm_]["felt"][1], 100 * L44[nm_]["frac"], L44[nm_]["dx"]))))
for nm_ in ("F", "F#"):
    rows2.append((pf("%s 복귀 넘침 (건반 / 레버, 여유 포함)", nm_), pf("%.3f° / %.2f°", tuple(Q44["over_key_r43"][nm_])), pf("%.3f° / %.2f°", tuple(Q44["over_key"][nm_]))))
rows2.append(("그 자세로 모듈 스윕", pf("1.3 미만 %d쌍, 최소 %.2f (공차 뒤 %.2f)", (CL["r43_felts"]["n_bad"], CL["r43_felts"]["min"], CL["r43_felts"]["min"] - 0.3)),
              pf("1.3 미만 0쌍; F·F# 복귀 넘침 쌍 최소 %.2f (공차 뒤 %.2f, %s %s ↔ %s %s)", (CL["over_ff"]["d"], CL["over_ff"]["d"] - 0.3, tr(CL["over_ff"]["a"]), tr(CL["over_ff"]["part_a"]), tr(CL["over_ff"]["b"]), tr(CL["over_ff"]["part_b"])))))
for mat_, lab_ in (("nom", "공칭"), ("passline", "합격선"), ("worst", "최악(합격선 밖)")):
    rows2.append((pf("화음 자리 PLAY 0.5~1.5 m/s, %s: 들림 / 키퍼 (F · F#)", lab_),
                  pf("%.3f / %.2f · %.3f / %.2f", (_ls("r43", "F", mat_)["lift_play"], _ls("r43", "F", mat_)["keep_play"], _ls("r43", "F#", mat_)["lift_play"], _ls("r43", "F#", mat_)["keep_play"])),
                  pf("%.3f / %.2f · %.3f / %.2f", (_ls("r44", "F", mat_)["lift_play"], _ls("r44", "F", mat_)["keep_play"], _ls("r44", "F#", mat_)["lift_play"], _ls("r44", "F#", mat_)["keep_play"]))))
rows2.append(("유령 (0.45~2 N 누름, 공칭·합격선·최악): 재무장 → 거름", pf("재무장 %d, 못 거른 것 %d", (sum(_ls("r43", n_, m_)["ghost_armed"] for n_ in ("F", "F#") for m_ in ("nom", "passline", "worst")),
                                                                                      sum(_ls("r43", n_, m_)["ghost_not_dropped"] for n_ in ("F", "F#") for m_ in ("nom", "passline", "worst")))),
              pf("재무장 %d, 못 거른 것 %d (최대 %.0f %%, 내려옴 ≤ %.2f m/s)", (sum(_ls("r44", n_, m_)["ghost_armed"] for n_ in ("F", "F#") for m_ in ("nom", "passline", "worst")),
                                                             sum(_ls("r44", n_, m_)["ghost_not_dropped"] for n_ in ("F", "F#") for m_ in ("nom", "passline", "worst")),
                                                             100 * max(_ls("r44", n_, m_)["ghost_max"] for n_ in ("F", "F#") for m_ in ("nom", "passline")),
                                                             max(_ls("r44", n_, m_)["ghost_desc_max"] for n_ in ("F", "F#") for m_ in ("nom", "passline", "worst"))))))
rows2.append(("연타 / 끝까지 복귀 (화음 자리, 마찰 1배 · 2배, F · F#)",
              pf("%.1f · %.1f Hz / %.1f · %.1f ms · %.1f · %.1f Hz / %.1f · %.1f ms", (_ls("r43", "F", "nom")["rep"], _ls("r43", "F", "nom")["rep_2f"], _ls("r43", "F", "nom")["t100"], _ls("r43", "F", "nom")["t100_2f"],
                                                                            _ls("r43", "F#", "nom")["rep"], _ls("r43", "F#", "nom")["rep_2f"], _ls("r43", "F#", "nom")["t100"], _ls("r43", "F#", "nom")["t100_2f"])),
              pf("%.1f · %.1f Hz / %.1f · %.1f ms · %.1f · %.1f Hz / %.1f · %.1f ms", (_ls("r44", "F", "nom")["rep"], _ls("r44", "F", "nom")["rep_2f"], _ls("r44", "F", "nom")["t100"], _ls("r44", "F", "nom")["t100_2f"],
                                                                            _ls("r44", "F#", "nom")["rep"], _ls("r44", "F#", "nom")["rep_2f"], _ls("r44", "F#", "nom")["t100"], _ls("r44", "F#", "nom")["t100_2f"]))))
rows2.append(("ABUSE 들림 최대 (모든 재료·경우, F · F#)", pf("%.3f · %.3f", (max(_ls("r43", "F", m_)["lift_abuse"] for m_ in ("nom", "passline", "worst")), max(_ls("r43", "F#", m_)["lift_abuse"] for m_ in ("nom", "passline", "worst")))),
              pf("%.3f · %.3f (한계 0.40)", (max(_ls("r44", "F", m_)["lift_abuse"] for m_ in ("nom", "passline", "worst")), max(_ls("r44", "F#", m_)["lift_abuse"] for m_ in ("nom", "passline", "worst"))))))
rows2.append(("ABUSE 복귀 넘침 (2.0 m/s 6건반 화음, 요청한 화음 자리 2.5 m/s; 건반 / 레버, F · F#) → 스윕", "—",
              pf("%.3f° / %.2f° · %.3f° / %.2f° → 최소 %.2f, 공차 뒤 %.2f > 0: 닿지 않음 (ABUSE = 손상 없음; %s %s ↔ %s%s)", (tuple(Q44["over_key_brief"]["F"]) + tuple(Q44["over_key_brief"]["F#"]) + (CL["over_brief"]["d"], CL["over_brief"]["d"] - 0.3, tr(CL["over_brief"]["a"]), tr(CL["over_brief"]["part_a"]), tr(CL["over_brief"]["b"]),
                 (" " + tr(CL["over_brief"]["part_b"])) if CL["over_brief"]["part_b"] else "")))))
rows2.append(("굴림 되돌림/넘김 비 (쉼, F · F#)", pf("%.2f · %.2f", (R43M["stress"]["roll"]["F"]["ratio_rest"], R43M["stress"]["roll"]["F#"]["ratio_rest"])),
              pf("%.2f · %.2f (1 이상 = 굴지 않음)", (ST["roll"]["F"]["ratio_rest"], ST["roll"]["F#"]["ratio_rest"]))))
rows2.append(("착지 짝힘 상한 → 가이드 탭 (F · F#)", pf("%.2f · %.2f N", (R43M["r43"]["land_tab"]["F"]["tab_N"], R43M["r43"]["land_tab"]["F#"]["tab_N"])),
              pf("%.2f · %.2f N (탭 천이 받음)", (Q43["land_tab"]["F"]["tab_N"], Q43["land_tab"]["F#"]["tab_N"]))))
rows2.append(("USB 홈 옆 선반 응력", pf("%.1f MPa", R43M["stress"]["shelf_usb"]), pf("%.1f MPa", ST["shelf_usb"])))
rows2.append(("색별 복귀 넘침 자세 (건반 / 레버, 백 · 흑)", pf("%.3f° / %.2f° · %.3f° / %.2f° (주 동역학만)", (R43M["heights"]["a_over_w"], R43M["heights"]["b_over_w"], R43M["heights"]["a_over_b"], R43M["heights"]["b_over_b"])),
              pf("%.3f° / %.2f° · %.3f° / %.2f° (PLAY 화음 자리·격자, 합격선 재료 포함)", (H["a_over_w"], H["b_over_w"], H["a_over_b"], H["b_over_b"]))))
for r_ in rows2:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w("### 문제 3 — 흑건(과 백건) 누른 자세 내보내기")
w()
DPk = CL["dip"]
w(pf("다시 잰 값: r4.3 `poses_for`는 건반 ‘dip’를 max(1 N 정착 각, 강체 각)으로 잡아, 레버가 패드에 먼저 닿는 두 색 모두 **강체** 각을 내보냈다(백도 %.2f°가 아니라 %.2f°). 레버 ‘dip’는 이미 1 N 정착(패드 있음)이었다.", (DPk["white"]["held"], DPk["white"]["rigid"])))
w()
w("| 항목 | r4.3 | r4.4 |")
w("|---|---|---|")
for r_ in (("건반 `side_dip` (백 / 흑)", pf("강체 %.2f° / %.2f° (K 둘레 회전)", (DPk["white"]["rigid"], DPk["black"]["rigid"])),
            pf("1 N 정착(패드 있음)의 평면 상태 그대로: %.2f° / %.2f° 회전 + 노치가 봉에 앉음(K가 (%+.3f, %+.3f) / (%+.3f, %+.3f)) = 앞끝 기준 %.2f° / %.2f°; 앞끝 z%.2f / z%.2f (강체 z%.2f / z%.2f)", (DPk["white"]["held"], DPk["black"]["held"], DPk["white"]["notch_dy"], DPk["white"]["notch_dz"], DPk["black"]["notch_dy"], DPk["black"]["notch_dz"], DPk["white"]["front_angle"], DPk["black"]["front_angle"],
               DPk["white"]["front_z_held"], DPk["black"]["front_z_held"], DPk["white"]["front_z_rigid"], DPk["black"]["front_z_rigid"]))),
           ("건반 `side_dip_rigid`", "없음", pf("강체 %.2f° / %.2f° (새 필드; 끝 부속 건반도)", (DPk["white"]["rigid"], DPk["black"]["rigid"]))),
           ("레버 `side_dip` / `side_dip_rigid`", pf("정착 %.2f° / %.2f°, 강체 %.2f° / %.2f°", (DPk["white"]["lever_held"], DPk["black"]["lever_held"], DPk["white"]["lever_rigid"], DPk["black"]["lever_rigid"])),
            "같음 (끝 부속 레버에도 `side_dip_rigid`, 비틀림 스프링에도)"),
           ("스윕 자세", "쉼·dip(강체)·ff·복귀 넘침", "쉼·dip(정착)·dip_rigid·ff·복귀 넘침 (자기 건반·레버 짝은 같은 이름끼리)"),
           ("바꾼 곳", "", "`model_v4.poses_for`, `clearance_sweep`, `export_geo` (건반·끝 부속 건반·스프링), geometry `meta.note`, 치수 S24")):
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
# ---------------------------------------------------------------- r4.4 fix 2
w("### 고침 2 — r4.4 검증 지적과 해결 (다시 잰 값, 받아들임 / 기각)")
w()
w("검증 3렌즈(물리·기하·출력물)의 major 8건을 이 모델에서 먼저 다시 재고 고쳤다. 다시 돌린 범위: 한 모듈(대표 백 D·흑 C#, 착지·꼬리는 F·F#), 바뀐 칼라·보스·레일이 닿는 끝 부속; PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45 / 1 / 2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악 — `run_all.py` 한 번. 새 모델 함수: `carrier_wall_plate`(옆벽 판), `steel_bond`, `lever_float`, `with_bar_play`, `key_pose_shifts`, `rail_pockets`.")
w()
_fl = CL["lever_float"]
_flmax = max(max(v_) for v_ in _fl.values())
_ksw, _ksb = KSf["w"], KSf["b"]
_ll = CL["cls_min"].get("lever-lever", {}).get("d", float("nan"))
_nm_rail = NM.get("건반 블록 ↔ 밸런스 레일(낮춘 곳·받침)", {})
_S03 = S0["analysis"]["C03"]["strip"]
WPOCK_ = pf("y%.1f 뒤 z%.2f", (RPf["white"]["y"], RPf["white"]["z"])) if RPf.get("white") else "포켓 없음"
rows_f2 = [
    ("물리 1", "아래 스냅 립이 매 음 한계(층간 5 MPa)를 넘는데 0.2장 행은 ‘통과’; 압연 평철 모서리 R0.5면 a 0.5 → 0.75라 6.7 → 10.1 MPa",
     pf("캐리어 → 강철 힘(아래 립) PLAY %.1f / ABUSE %.1f N; 고른 접촉 %.1f MPa, R0.5 모서리 %.1f MPa — 맞음. 더 나쁜 것: 립 하중이 0.8 옆벽 밖으로 치우쳐 옆벽 립 뿌리가 층 안 %.1f MPa(판 모델 최대 %.1f; 한계 12)", (RT["play"]["B"], RT["abuse"]["B"], RT["play"]["sig_bottom"], 1.5 * RT["play"]["sig_bottom"], WPf["play_a0.50_pinned"]["s_root"], WPf["play_a0.50_pinned"]["s_plate"])),
     "받아들임",
     pf("강철 두 19×40 옆면을 2액형 에폭시로 옆벽에 접착(면적 %.0f mm²): 전단 매 음 %.3f, 화음 %.3f, ABUSE %.3f MPa(허용 %.2f / %.2f = 에폭시 %.1f ÷ %.0f / %.0f). 립은 굳는 동안만 잡는다. 0.2장 행을 접착 기준으로 바꾸고 스냅만의 숫자도 적음. "
        "기각한 안: 아래 립 앞으로 y153까지(끼울 때 앞벽에서 3.8 떨어진 곳이 1.0 벌어져야 해 변형률 약 8 %% — 부러짐), 1.2 두께(립 뿌리 %.1f로 내려가도 옆벽 립 뿌리는 %.1f), 판에서 자른 직각 강철(접착이면 필요 없음)",
        (SRf["bond_geo"]["area"], BDf["play"]["tau"], BDf["chord"]["tau"], BDf["abuse"]["tau"], BDf["play"]["limit"], BDf["abuse"]["limit"], P4["bond_tau_epoxy"], P4["bond_sf_play"], P4["bond_sf_rare"],
         RT["play"]["sig_bottom"] / 1.44, 6 * WPf["play_a0.50_pinned"]["q"] * (0.4 + 0.6) / 0.64))),
    ("물리 2", "빠짐(스냅 풀림) 검사가 없음: 옆벽이 벌어지는 강성 약 5 N/mm, 비탈 11~27°면 빠짐; 운반 218 g는 굽힘만",
     pf("옆벽 판 모델(0.5 격자, 앞·뒷벽 핀 / 고정, 앞 뚜껑이 윗단을 묶음, 강철이 안쪽을 막음): 립 선 벌어짐 PLAY %.2f~%.2f, ABUSE %.2f~%.2f, 1.5×ABUSE %.2f~%.2f (물림 1.0), 비탈 %.0f~%.0f° — 스냅만으로는 매 음에 빠질 수 있음", (WPf["play_a0.50_clamped"]["spread_max"], WPf["play_a0.50_pinned"]["spread_max"], WPf["abuse_a0.50_clamped"]["spread_max"], WPf["abuse_a0.50_pinned"]["spread_max"],
        WPf["abuse_x1.5_a0.50_clamped"]["spread_max"], WPf["abuse_x1.5_a0.50_pinned"]["spread_max"], WPf["play_a0.50_clamped"]["flank_deg"], WPf["play_a0.50_pinned"]["flank_deg"])),
     "받아들임",
     pf("위 접착(벌어짐 0). 충격 %.0f g까지 접착이 드문 하중 한계 안. 단계 0 시험 20(C16a 생산 캐리어 3 + C16b 받침): 스냅만 빠짐 힘(모델 %s N), 접착 %.0f N 10 s × 3에 움직임 ≤ 0.05, 1 m 낙하. "
        "기각한 안: 강철 밑 다리(바닥)로 두 옆벽 묶기 + 위에서 넣기(앞 뚜껑 y150~153·뒤 립 y184~190이 앞·뒷벽 바로 옆이라 0.8 벌릴 수 없고, 바닥이 있으면 밑으로도 못 넣음), 되물림 경사 립(평평한 강철 면은 립 끝 모서리에만 닿아 힘 방향이 그대로 수직)",
        (SRf["bond_shock_g"], " ~ ".join(pf("%.0f", RT["play"]["B"] / v_) for v_ in sorted((WPf["play_a0.50_clamped"]["spread_max"], WPf["play_a0.50_pinned"]["spread_max"]), reverse=True)), 1.5 * RT["abuse"]["B"]))),
    ("기하 1", "흑 블록 앞 뺨 ↔ 밸런스 레일: 내보낸 1 N 바닥 1.27, 동역학 1.23~1.25 — 스윕은 K 둘레 회전만",
     pf("노치가 봉에 앉음/파고듦(K에서, dz): 쉼 백 %+.3f / 흑 %+.3f, 1 N 바닥 %+.3f / %+.3f, ff(모든 동역학 최저) %+.3f / %+.3f, 복귀 넘침 %+.3f / %+.3f — 맞음; 흑 립 구간 가장 낮은 점 z%.3f(%s)", (_ksw["rest"][1], _ksb["rest"][1], _ksw["dip"][1], _ksb["dip"][1], _ksw["ff"][1], _ksb["ff"][1], _ksw["over"][1], _ksb["over"][1],
        RPf["black"]["zmin"] if RPf.get("black") else float("nan"), RPf["black"]["pose"] if RPf.get("black") else "-")),
     "받아들임",
     pf("스윕과 내보내기가 같은 평면 상태(회전 + 노치 이동)를 쓴다(ff·복귀 넘침은 동역학 최저; 1 N 손가락 격자에서 ff 노치가 더 파고들어 백 블록도 1.3 아래로 감). 흑건 블록 밑 레일을 y%.1f 뒤로 z%.2f까지 포켓(검증자 제안 y137.4면 포켓 앞 모서리 ↔ 블록 모서리 1.29라 y%.1f), 백건은 " + WPOCK_ + "; 핀 줄은 z%.1f 그대로 → 블록 ↔ 레일 %.2f. T3 뒤 발을 y%.1f에서 끝냄. "
        "여파: 노치 이동을 넣으니 F·F# 꼬리 ↔ 제어 기판 부품 구역(z20, 회로 인터페이스)이 복귀 넘침에서 1.24~1.25 → F·F# 빔·얇은 꼬리 밑면 y%.0f~%.1f을 %.1f 올림(꼬리 응력 ×%.3f)",
        (RPf["black"]["y"], RPf["black"]["z"], RPf["black"]["y"], H["z_rail_low"], _nm_rail.get("d", float("nan")), RPf["black"]["y"] - 0.1, P4["tail_relief"]["F"][0], P4["tail_relief"]["F"][1], P4["tail_relief"]["F"][2],
         (P4["tail_top"] - P4["beam_z"][0]) ** 2 / (P4["tail_top"] - P4["beam_z"][0] - P4["tail_relief"]["F"][2]) ** 2) if RPf.get("black") else ())),
    ("기하 2", "레버 축 놀음(칸마다 0.50)이 스윕에 없음: 옆벽 ↔ 패드 1.01(패드 바 ±0.3이면 0.71), A#|B 칼라 합 1.40 → 1.20",
     pf("한쪽 축 놀음 최대 %.3f(칸 가장자리 레버); 고침 1 옆벽(윗단 = 강철 윗면)이면 옆벽 ↔ 자기 패드 %.2f — 맞음. 더 찾은 것: 보스 쪽으로 떠밀린 레버 ↔ 핀 1.30(요 포함, 딱 경계)", (_flmax, CL["lip_pad_fix1"])),
     "받아들임 (고친 방법은 다름)",
     pf("스윕에 레버 한쪽 놀음(칼라·보스 사슬), 이웃 레버는 둘 사이 빈 틈만, 패드 바 무리(패드·쐐기·띠·잎·손잡이) ±%.1f. 패드 구간 옆벽 윗단을 강철 윗면 −%.1f로(옆벽이 패드 면 밑으로 지나감) → %.2f; 칼라 한 개 %.2f 이상(짝 %.2f; 검증자 0.75는 복귀 넘침에서 1.298) → 레버 ↔ 레버 %.2f; 핀 보스 +%.2f → 칸 놀음 %s. "
        "기각한 안: 패드 폭 6.0 → 5.2 + 패드 바 놀음 0.1(패드 강성이 바뀌어 업스톱 동역학을 다시 해야 하고, 바 놀음 0.3은 빼기 절차의 틈)",
        (P4["pad_bar_clear"], P4["wall_drop_pad"], CL["lip_pad"], P4["collar_min"], 2 * P4["collar_min"], _ll, P4["boss_extra"], " / ".join(pf("%.2f", q_) for q_ in R["axial_play"])))),
    ("출력물 1", "T3 GO/NO-GO를 핀을 다 누른 뒤에 하면 다른 핀이 가운데 블록·반대쪽 NO-GO에 걸려 낮은 핀을 못 잡음",
     "피치 13.05~14.61, 막대 52, 가운데 막음 |u| < 3, NO-GO 16~20 — 맞음", "받아들임",
     "누른 핀마다 바로(오른쪽 이웃 핀을 꽂기 전) +X로 옮겨 |<GO로 확인, 프레임 한 장씩; 엄지·바이스로 누르고 망치 금지(80 N에서 멈춤 면 25~40 MPa) — tools.md·10.1장"),
    ("출력물 2", "단계 0 키트에 시험 20이 없음", "순서·기록표·‘19개’ 글에 20 없음 — 맞음", "받아들임",
     pf("시험 20 = 강철 유지(C16a 생산 캐리어를 모델에서 그대로 3개, C16b 받침): 스냅만 빠짐 힘, 접착 %.0f N·1 m 낙하, 10^5회는 캠 필요(시험 10처럼); 순서 3번 다음, ‘20개’", 1.5 * RT["abuse"]["B"])),
    ("출력물 3", "남은 문제 5(공구)가 DESIGN·부품표에서 닫히지 않음(S08 ‘2.5 단’, D02, 부품표 3 × 15 g)",
     "문서 세션이 10.1·12장·조립 단계는 이미 고침; 남은 것은 S08·D02·A08·D11 글(`export_geo.py`)과 부품표 공구 행(`run_all.py`) — 맞음", "받아들임",
     pf("S08·D02(1/8회전 = 바늘 %.2f / %.2f)·A08·D11 글을 고치고, 부품표 공구 행을 tools_geometry.json에서 %d개 합계 %.1f g로", (TDL["per_colour"]["white"]["per8"], TDL["per_colour"]["black"]["per8"], len(TLP), sum(v_["mass_g"] for v_ in TLP.values())))),
    ("출력물 4", "3a 굽힘 띠: 경간 60에서 판정이 다이얼 0.018 mm에 걸림(접촉 3곳 포함)", "k 70.1 N/mm, 18 N에 0.257 mm, 합격선 0.275 — 맞음", "받아들임",
     pf("띠 %.0f×%.0f×%.1f, 경간 %.0f(k %.1f N/mm, 18 N에 %.2f mm); 다이얼은 C03c 가운데 Ø4 구멍으로 띠 윗면에 직접(검증자 안의 ‘받침 밑 구멍’은 다이얼이 받침 밑에 서야 해 누름 코 구멍으로 바꿈); 기울기는 3번 평균",
        (_S03["span"] + 20.0, _S03["b"], _S03["t"], _S03["span"], _S03["k_pred"], 18.0 / _S03["k_pred"]))),
]
w("| 지적 | 요지 | 다시 잰 값 | 판정 | 고친 것 / 기각한 안 |")
w("|---|---|---|---|---|")
for r_ in rows_f2:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w(pf("모든 틈(고침 2 스윕: 레버 축 놀음 + 패드 바 놀음 + 노치 이동): 모듈 %d쌍 중 1.3 미만 %d, 최소 %.2f(공차 뒤 %.2f); 끝 부속 %d / %d쌍. 동역학·강도에 닿는 것은 레버 질량(옆벽 낮춤, 레버 %.2f g)과 F·F# 꼬리뿐이고 0.2장 목표는 모두 다시 판정했다.",
     (CL["n_pairs"], CL["n_bad"], CL["min"], CL["min_after_tol"], CL["end_parts"]["left"]["n"], CL["end_parts"]["right"]["n"], W["lever_g"])))
w()
# ---------------------------------------------------------------------------------------------------- r4.4 fix 2b
w("### 고침 2b — r4.4 재검증 지적과 해결 (고침 2 뒤 다시 잰 값)")
w()
_th = R["steel_retention"]["thermal"]
_cr = F2B["crown_rest"]
_ov2 = H.get("over_f2", {})
_okf2 = R["r44"].get("over_key_f2", R["r44"]["over_key"])
_bf = [q_ for q_ in CL["closest"] if q_["a"].startswith("key ") and q_["b"].startswith(("board components", "board part"))]
_bmin = min(_bf, key=lambda q_: q_["d"]) if _bf else None
_ke = {k_: R["plate"][k_]["chord" if k_ != "abuse" else "single"] for k_ in ("play", "abuse_chord20", "abuse")}
_ke1 = R["plate"]["play"]["single"]
_so2 = R["c44"]["standoffs"]
_wr = H["wedge"]
w(pf("고침 2를 넣은 모델을 검증 3렌즈가 다시 재서 기하 critical 1 · major 1, 물리 major 2, 출력물 major 2를 냈다. 모두 이 모델에서 먼저 다시 쟀고 모두 맞아 받아들였다(기각한 지적 없음, 고치는 방법을 바꾼 것은 표에 적음). "
     "다시 돌린 범위: 한 모듈(대표 백 D·흑 C#, 꼬리는 E·F·F#·G), 끝 부속 A0·C8(캐리어 옆벽이 닿음); PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45 / 1 / 2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악 — `run_all.py` 한 번(%.0f s). "
     "새 모델 함수: `board_boss_rects`, `board_insert_check`, `bond_thermal`; 바뀐 함수: `plate_fe`(킬), `fixed_prisms`·`fin_poly`(바닥 구멍·킬·매단 보스), `board_prisms`(부품 구역을 보스 둘레 1.3 비움), `lever_body`·`lever_prisms`(옆벽 0.7·립 0.9·접착막), `circuit_c44_checks`. "
     "고치기 전 보관 `geometry.r4_4b.json`, `work_f2b/*.pre_f2b.*`, 패치 `work_f2b/patch_*_f2b.py`.", R["timing"]["total_s"]))
w()
rows_f2b = [
    ("기하 critical", "제어 기판을 한 덩어리 프레임에 넣을 길이 없음: F|F# 핀 발(x82.52~84.12, y152~170.7)이 바닥~윗판, 기판 홈은 앞이 열림(x81.92~84.72, y145.5~172), 홈 뒤 기판 띠 위에 핀이 z21.5부터 매달림, 윗판이 덮음, 기판 뒤 여유 1.3",
     pf("맞음: 핀 발이 홈에 들어가려면 기판이 %.1f 뒤에서 앞으로 와야 하는데 뒤는 선반 리브 앞면까지 %.1f; 옆모습(x = 핀 두께)에서 홈 뒤 띠의 자리(y170.7~196.8 × z5~21.5)는 핀 발·매단 핀·리브·바닥으로 사방이 막혀 있고, 기판을 옆으로 밀면 홈 옆이 핀 발에 걸림. 10장 조립 순서에 기판 단계가 없었음",
        (PR["fin_slot_y"][1] - PR["board_y"][0], PR["rib_y0"] - PR["board_y"][1])),
     "받아들임",
     pf("바닥을 기판 밑에서 뚫음(x%.2f~%.2f y%.1f~%.1f, 리셉터클 뒤 x%.2f~%.2f는 y%.1f까지): 모듈을 뒤집어 기판을 곧게 넣고(홈이 핀 발·킬을 따라감) 매단 보스 4개(D6, 같은 구멍 자리; 앞 2 = 밸런스 레일 뒷면에서 받침, 윗면 z%.1f; 뒤 2 = 리브 x50·x116 앞면과 선반 밑면 z%.2f)에 닿으면 M3×6 2개를 밑에서(머리는 기판 밑), 위치 핀 2개는 보스에서 기판 구멍으로 아래로. "
        "핀 발은 킬(y%.1f~152, z%.0f~%.0f)로 레일에 붙음. 넣는 길 검사 `board_insert_check`: 기판·BRD-01 부품을 밑에서 곧게 올릴 때 길 위 프레임 최소 %.2f(%s), 바닥 구멍 1.0, 레일 1.0, 멈춤 = 보스 4개(기판 윗면 z%.1f 닿음), 핀 반경 놀음 %.2f. 부품 추가 없음. "
        "기각한 안: 바닥 쟁반(검증자 권장 (a), 출력 +1/모듈이고 핀 발의 위로 당김을 쟁반이 받아야 함), 홈을 뒤로 열기(b, 제로·리셉터클을 핀 선 밖으로 = 회로 인터페이스 변경), 핀 발을 따로(c, +1/모듈), 출력을 멈추고 기판을 넣기(기판을 다시 뺄 수 없음)",
        tuple(F2B["hatch"]) + tuple(F2B["notch"]) + (P4["board_boss"][0], F2B["bosses"][2][5], F2B["keel"][0], F2B["keel"][1], F2B["keel"][2], BI2["min"], BI2["pair"][1].split(" (")[0], PR["board_z"][1], BI2["pin_play"]))),
    ("물리 major 1", "접착(에폭시)이 PETG(60e-6/K)·강철(11.7e-6/K) 열팽창 차이를 받지 못함 — 5분 에폭시 G 700, 접착층 0.1이면 가장자리 전단 ΔT 10/20/30 K에 1.6/3.2/4.9 MPa; 시험 20은 실온만",
     pf("맞음(전단 지연, 40 mm ≫ 지연 길이): 5분 에폭시 ΔT %.0f K 접착층 %.2f / %.2f → %.2f / %.2f MPa, ΔT %.0f K → %.2f / %.2f MPa (설계 강도 %.1f). 스냅만으로는 못 버티므로(고침 2) 접착이 떨어지면 강철이 빠짐",
        (P4["bond_dT"][0], P4["bond_t"], 0.05, _th["day_%.2f" % P4["bond_t"]]["epoxy"], _th["day_0.05"]["epoxy"], P4["bond_dT"][1], _th["rare_%.2f" % P4["bond_t"]]["epoxy"], _th["rare_0.05"]["epoxy"], P4["bond_tau_epoxy"])),
     "받아들임",
     pf("MS 폴리머(하이브리드) 탄성 접착제(G 약 %.0f MPa, 설계 겹침 전단 %.1f MPa — 단계 0 시험 20): 열 전단 ΔT %.0f / %.0f K, 접착층 %.2f → %.3f / %.3f, 가장 얇은 %.2f → %.3f / %.3f MPa. `steel_bond` 판정에 열 항을 더함: 매 음 하중 %.3f + 열(ΔT %.0f, %.2f) %.3f = %.3f ≤ %.3f, ABUSE %.3f + 열(ΔT %.0f) %.3f = %.3f ≤ %.3f MPa. 패드 봉우리에서 강철 미끄럼 %.4f mm. 시험 20에 5 ↔ 45 °C 3번(냉장고·따뜻한 물)을 넣음. "
        "기각한 안: 강화(유연) 에폭시 G ≤ 50 MPa(구하기·표시값 확인이 어려움; MS 폴리머는 철물점 실란트)",
        (P4["bond_G"], P4["bond_tau"], P4["bond_dT"][0], P4["bond_dT"][1], P4["bond_t"], _th["day_%.2f" % P4["bond_t"]]["ms"], _th["rare_%.2f" % P4["bond_t"]]["ms"], P4["bond_t_min"], _th["day_%.2f" % P4["bond_t_min"]]["ms"], _th["rare_%.2f" % P4["bond_t_min"]]["ms"],
         BD2["play"]["tau_mech"], P4["bond_dT"][0], P4["bond_t_min"], BD2["play"]["tau_th"], BD2["play"]["tau"], BD2["play"]["limit"], BD2["abuse"]["tau_mech"], P4["bond_dT"][1], BD2["abuse"]["tau_th"], BD2["abuse"]["tau"], BD2["abuse"]["limit"], BD2["play"]["slip"]))),
    ("물리 major 2", "접착층이 없음: 주머니 10.6 − 2 × 0.8 = 9.0 = 강철이라 에폭시가 들어갈 틈이 없고, 10장 3단계에는 접착이 없으며 부품표·16장은 ‘끼운 뒤 접착’(시험 20만 먼저 바름)",
     pf("맞음: geometry 옆벽 x28.735~29.535 / 38.535~39.335, 강철 x29.535~38.535. 접착막이 옆벽을 밀면 레버 폭이 늘어 레버 ↔ 레버 %.2f가 줄어듦", (R0["clear"]["cls_min"]["lever-lever"]["d"],)),
     "받아들임",
     pf("옆벽 %.1f → %.1f(주머니 %.1f = 강철 %.1f + 접착층 %.2f × 2; 레버 겉폭 %.1f 그대로), 윗 립 %.1f → %.1f(안쪽 모서리 x ±%.1f 그대로 = 패드와 틈 그대로), 아래 립 안쪽 x ±3.5 그대로; 강철 두께 %.1f~%.1f만(캘리퍼스). 순서는 시험 20과 같게: 사포·알코올 → 강철 두 면에 얇게 바름 → 밑에서 스냅 → 나온 것 닦음 → 24 h(10장 4단계 — r4.5 고침: 기판 단계가 1단계로 들어가 번호가 밀림, 부품표, 16장). "
        "레버 %.2f → 57.05 g(옆벽 −, 접착막 +; r4.5 56.97, r4.5 고침 %.2f). 기각한 안: 레버 폭 10.8(옆벽 0.8 유지) — 레버 ↔ 레버 %.2f가 %.2f로",
        (P4["carrier_wall"], F2B["side_wall"], P4["lever_w"] - 2 * F2B["side_wall"], P4["steel_w"], P4["bond_t"], P4["lever_w"], 0.8, F2B["lip_over"], P4["lever_w"] / 2 - F2B["side_wall"] - F2B["lip_over"], P4["steel_w"] - 0.1, P4["steel_w"] + 0.1,
         R0["white"]["lever_g"], W["lever_g"], R0["clear"]["cls_min"]["lever-lever"]["d"], R0["clear"]["cls_min"]["lever-lever"]["d"] - 0.2))),
    ("기하 major", "스윕 자세가 공칭(+합격선) 재료뿐: 최악 재료 PLAY 1.5 m/s 뗌에서 백 건반 −0.458°(자세 −0.414), E·G 얇은 꼬리 ↔ 기판 부품 구역 1.279(공차 뒤 0.979), F 자기 최악 −0.533°에서 빔 ↔ 4067 1.295",
     pf("맞음(재현: 고침 2 모델에 최악 자세를 넣은 스윕): E·G 얇은 꼬리 ↔ 부품 구역 1.27, E ↔ 4067 1.28, F 빔 ↔ 부품 구역·4067 1.30 — 1.3 미만 5쌍. 흑은 최악이 더 얕음(흑 %.3f° / 레버 %.2f°)", (H["a_over_b"], H["b_over_b"])),
     "받아들임",
     pf("스윕 ‘over’·‘ff’ 자세에 최악 재료의 PLAY 격자·화음 스윕(F·F#는 자기 착지의 최악 PLAY)을 더함: 백 건반 %.3f → %.3f°, 레버 %.2f → %.2f°; F %.3f / %.2f → %.3f / %.2f°. E·G 빔·얇은 꼬리 밑면 y184~195.8 0.1, F는 y176~195.8 0.15 올림(회로 인터페이스 z20 그대로; 꼬리 응력 ×%.3f / ×%.3f). "
        "결과: 모듈 %d쌍 중 1.3 미만 %d, 최소 %.2f(공차 뒤 %.2f); 건반 ↔ 기판 부품 최소 %s",
        (_ov2.get("w", (float("nan"),) * 2)[0], H["a_over_w"], _ov2.get("w", (float("nan"),) * 2)[1], H["b_over_w"], _okf2["F"][0], _okf2["F"][1], R["r44"]["over_key"]["F"][0], R["r44"]["over_key"]["F"][1],
         (P4["tail_top"] - P4["beam_z"][0]) ** 2 / (P4["tail_top"] - P4["beam_z"][0] - 0.1) ** 2, (P4["tail_top"] - P4["beam_z"][0]) ** 2 / (P4["tail_top"] - P4["beam_z"][0] - 0.15) ** 2,
         CL["n_pairs"], CL["n_bad"], CL["min"], CL["min_after_tol"], (pf("%.2f (%s %s ↔ %s)", (_bmin["d"], _bmin["a"], _bmin["part_a"], _bmin["b"].split(" (")[0])) if _bmin else "-")))),
    ("출력물 major 1", "캡스턴 벤치 게이지(T2)가 꼭대기를 z31.0(건반 좌표)으로 맞춤 — 지그 위 건반도 노치 천에 가라앉아 모델의 정착 쉼 꼭대기는 30.892 / 30.912: 캡스턴이 0.108 / 0.088 높게(1/8회전 1.73 / 1.41번), 업스톱 틈 −0.40 → 약 −0.73",
     pf("맞음: 정착 쉼(4-DOF, 레버가 캡스턴에) 꼭대기 백 %.3f · 흑 %.3f (건반 좌표 z%.1f보다 %.3f / %.3f 낮음 = 1/8회전 %.2f / %.2f번)", (_cr["white"], _cr["black"], P4["z_c"], P4["z_c"] - _cr["white"], P4["z_c"] - _cr["black"], (P4["z_c"] - _cr["white"]) / 0.0625, (P4["z_c"] - _cr["black"]) / 0.0625)),
     "받아들임 (고친 방법은 다름)",
     pf("가짜 레버 밑면과 지그 영점 받침(교정봉 윗면)을 정착 쉼 꼭대기 한 면 z%.2f로(백 %+.3f, 흑 %+.3f = 1/8회전의 %.2f / %.2f); 바늘 ↔ 읽기 턱 ‘같은 높이’ 규칙과 교정은 그대로. `make_tools.py`가 모델 쉼 상태로 계산, 지그 틈 검사도 정착한 건반으로. S08 글 고침. "
        "기각한 안: 읽기 턱 3단(0 · W · B, 검증자 안) — 한 면이면 같은 높이 규칙 하나로 백·흑을 다 읽고 교정봉이 그 면을 바로 확인함",
        (F2B["crown_T2"], F2B["crown_T2"] - _cr["white"], F2B["crown_T2"] - _cr["black"], abs(F2B["crown_T2"] - _cr["white"]) / 0.0625, abs(F2B["crown_T2"] - _cr["black"]) / 0.0625))),
    ("출력물 major 2", "12장 종이 띠 규칙의 심 방향이 반대: ‘먼저 물리면 심을 빼고, 늦게 물리면 넣는다’ — 심 한 장은 패드 면 0.1 아래 = 레버가 먼저 닿음 = 틈이 더 음수 = 띠가 더 큰 힘에서 물림",
     pf("맞음: 모델 띠 물림 힘 백 틈 −0.30 / −0.40 / −0.50 → %s / %s / %s N (틈이 음수일수록 큰 힘); 단계 0 키트(시험 T·1)는 이미 맞는 방향", tuple(pf("%.2f", R["r41"]["strip"]["white_%.2f" % g_]["F_pinch"]) if R["r41"]["strip"]["white_%.2f" % g_]["F_pinch"] else "-" for g_ in (-0.30, -0.40, -0.50))),
     "받아들임",
     pf("12장: 먼저(작은 힘에) 물리면 심을 넣고, 늦게 물리면 심을 뺀다; 뺄 심이 없으면 그 칸 패드 바를 쐐기 0.1 얇게 다시 출력 — r4.5 고침: 쐐기 얇은 끝이 0.40 미만인 자리(백 %.3f, 끝 부속 A0·B0·C8)는 쐐기를 그대로 두고 그 패드 자리의 바 밑면을 0.1 올려(바 %.1f → %.1f) 다시 출력하거나 패드 펠트를 0.1 얇은 것으로. 기각한 안: 모든 패드 밑에 기본 심 1장 + 쐐기 0.1 얇게 — 가장 얇은 백 쐐기 %.2f가 출력 최소 %.1f 아래로", (_wr["w"][0], P4["pad_bar_t"], P4["pad_bar_t"] - 0.1, _wr["w"][0], P4["pad_wedge_min"]))),
]
w("| 지적 | 요지 | 다시 잰 값 | 판정 | 고친 것 / 기각한 안 |")
w("|---|---|---|---|---|")
for r_ in rows_f2b:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w(pf("**킬과 기판 받침의 숫자.** 윗판 FE(킬 뿌리 = 레일 + 바닥 띠를 핀 선 사이 보로 — r4.5 고침; 고침 2b는 레일에 고정, 핀 발은 z%.0f까지 깊은 보): 6건반 화음 자리 PLAY %.0f N/mm(고침 2 바닥 가정 %.0f), ABUSE 화음 %.0f; 한 건반 자리 F %.0f · F# %.0f N/mm(고침 2 %.0f · %.0f), 가장 무른 자리 %.0f(동역학 값 그대로). "
     "킬 굽힘(층 안) 한 건반 PLAY %.2f, 6건반 PLAY %.2f, ABUSE 화음 %.2f MPa, 전단 %.2f / %.2f / %.2f MPa(층간 기준 5 / 15 안). 핀 윗단 이음 인장 PLAY 화음 %.2f MPa(고침 2 %.2f). "
     "바닥 구멍 때문에 프레임이 %.1f g 가벼워짐(보스·킬 포함). 보스 ↔ 가장 가까운 BRD-01 부품 %.2f, M3 머리 ↔ 레일 %.2f · 리브 %.2f(리브 축 %.2f), 나사 = 기판 %.1f + 보스 %.1f(끝 z%.1f, 구멍 끝 z%.1f), 위치 핀 끝 z%.1f. "
     "r4.5 고침: 고침 2b의 ‘레일 자체의 휨은 모델에 없다 — 단계 0 시험의 화음 자리 합격선 %.0f N/mm로 본다’는 틀렸다(시험 3은 띠의 E만 잼) — 레일 휨은 이제 모델에 있고(1f-2장) 첫 모듈 정하중(조립 시험 21)으로 잰다.",
     (PR["z_floor"][0], R["seat"]["k_chord"], R0["seat"]["k_chord"], R["chord_dyn"]["k_abuse"], R["seat"]["k_keys"]["F"], R["seat"]["k_keys"]["F#"], R0["seat"]["k_keys"]["F"], R0["seat"]["k_keys"]["F#"], R["seat"]["k_min"],
      _ke1.get("keel_sigma", 0), _ke["play"].get("keel_sigma", 0), _ke["abuse_chord20"].get("keel_sigma", 0), _ke1.get("keel_tau", 0), _ke["play"].get("keel_tau", 0), _ke["abuse_chord20"].get("keel_tau", 0),
      R["plate"]["play"]["chord"]["fin_top"], R0["plate"]["play"]["chord"]["fin_top"], -(MA["frame_parts"].get("floor_board_hatch", 0) + MA["frame_parts"].get("fin_keel", 0) + MA["frame_parts"].get("board_bosses", 0)),
      min(q_["part_min"][0] for q_ in _so2), min(q_["rail_top"] for q_ in _so2 if q_["kind"] == "screw"), min(q_["rib_top"] for q_ in _so2 if q_["kind"] == "screw"),
      min(q_["rib_top_axis"] for q_ in _so2 if q_["kind"] == "screw" and q_["rib_top_axis"] is not None), R["c44"]["screw"]["stack"][0], R["c44"]["screw"]["stack"][1], R["c44"]["screw"]["tip_z"], R["c44"]["screw"]["bore_top"],
      R["c44"]["pins"]["tip_z"], PR["seat_k_chord_req"])))
w()
# ============================================================================================ 1f (r4.5, frozen) + 1f-2 (r4.5 fix round)
_h1f, _b1f = SEC1F45.split("\n", 1)
w(_h1f)
w()
w(pf("> 이 장은 r4.5 기록 그대로다. r4.5 고침에서 짧은 다리를 %.1f mm로 길게 잘라 가둠 홈에 넣었다(1f-2장). 지금 두 다리는 %.1f / %.1f mm로 자른다. 이 장의 ‘짧은 다리 2.5’는 r4.5 값이다.",
     (_M4.P["spring_short_leg"], _M4.P["spring_leg"], _M4.P["spring_short_leg"])))
w(_b1f)
w()
R45A = json.load(open(os.path.join(OUT, "work_r45b", "metrics.r4_5a.json")))
G45A = json.load(open(os.path.join(OUT, "geometry.r4_5a.json")))
M45A = R45A["metrics"]
N45A = G45A["solved"]["spring"]["short_leg_groove"]
CTL = SP45["capture_tol"]
w("### 1f-2. r4.5 → r4.5 고침: 검증 지적 다시 재기와 해결")
w()
w("r4.4 고침 2b를 검증한 사람(‘고침’ 렌즈)과 r4.5 스프링을 검증한 사람(‘스프링’ 렌즈)의 지적 6건을 먼저 이 모델로 다시 재고 판정했다. 모든 판정은 모듈 하나(백 최악 D, 흑 C#, 착지 문제의 F·F#)로, PLAY 0.5/1.0/1.5 m/s × 누름 0.45/1/2 N + 뗌, ABUSE 2.5 m/s, 재료 공칭 + 최악이다. 부품은 늘지 않았다.")
w()
w("| 지적 | 요지 | 다시 잰 값 | 판정 | 고친 것 / 기각한 안 |")
w("|---|---|---|---|---|")
_PART_KO = {"balance block": "밸런스 블록", "skin tail": "윗면 꼬리", "rear wall": "뒷벽", "tail wall R": "꼬리 오른 벽", "skin head": "윗면 머리"}
_POSE_KO = {"over": "복귀 넘침", "dip_rigid": "강체 바닥", "dip": "1 N 바닥", "ff": "ff 최저", "rest": "쉼"}
_pk = lambda d_, k_: (lambda v_: _PART_KO.get(v_, v_) if k_ == "part" else (_POSE_KO.get(v_, v_) if k_ == "pose" else v_))((d_ or {}).get(k_, "?"))
rows_45b = [
    ("스프링 major", "코일(ID 5.0)이 Ø4 봉 위에서 약 0.44 뜸: 짧은 다리 2.5가 한 면에만 기대 다리 힘 합 1.56 N이 코일을 56° 쪽 봉으로 밀고, 다리가 면에서 떨어져 11° 풀림 → 쉼 4.19 → 2.49 N·mm, PLAY 목표 3개 불합격(립 DW, 흑 DW, 흑 바닥 UW 마찰 2배); 코일-봉 마찰 이력은 모델 밖",
     pf("맞음 — 모델에 뜸 평형을 넣음(`spring_pose` ‘face’: 코일이 다리 힘 합 방향으로 봉에 닿고, 짧은 다리 끝이 면에 다시 닿을 때까지 풀림; 코일 반지름은 감긴 각을 따라). r4.5 그대로: 밀림 %.2f(%.0f° 쪽), 풀림 %.1f°, 쉼 %.2f / 바닥 %.2f N·mm(검증자 2.49 / 4.57: 이 모델은 감길수록 줄어드는 ID도 셈), "
        "봉 힘 %.2f / %.2f N; D DW %.1f, 립 y0 %.1f(< 47), UW %.1f; C# DW %.1f(< 47), 바닥 UW 마찰 2배 %.1f(< 20) → 불합격 3개 확인",
        (F45["shift"], F45["dir"], F45["unwind"], F45["T_rest"], F45["T_bottom"], F45["N_rest"], F45["N_bottom"], F45["keys"]["D"]["DW"], F45["keys"]["D"]["DW_lip"], F45["keys"]["D"]["UW"], F45["keys"]["C#"]["DW"], F45["keys"]["C#"]["UW_bottom_2f"])),
     "받아들임 (고친 방법은 다름)",
     pf("짧은 다리를 %.1f로 잘라 폭 %.2f 가둠 홈에(아래 표). 검증자 안 ① 홈을 %.1f° 돌림 — 쉼 토크는 돌아오나 코일이 봉을 %.1f N으로 문질러 μ 0.3이면 흑 바닥 UW 마찰 2배 %.1f(μ 0.1이어도 %.1f) 불합격; ② 짧은 다리 5 + %.1f° 돌림 — μ 0.3 %.1f 불합격; ③ 다리 힘이 코일을 주머니 벽으로 밀게 — 힘 방향(%.0f°)이 코일 슬롯 열림 안이라 벽이 없음. "
        "테스트 8(C06b = 모델 주머니 단면, 진짜 Ø4 봉)이 이것을 잰다",
        (PR["spring_short_leg"], CPT["width"], FROT["rot"], FROT["N_bottom"], FROT["keys"]["C#"]["UW_bottom_2f"], [v_ for k_, v_ in FLT.items() if k_.startswith("notch rotated") and k_.endswith("mu 0.1")][0]["keys"]["C#"]["UW_bottom_2f"], F5["rot"], F5["keys"]["C#"]["UW_bottom_2f"], F45["dir"]))),
    ("스프링 minor 1", "건반 뺀 레버의 긴 다리를 다시 걸 때 x 여유가 거의 없음: 뒷벽 홈(2.4)이 레버 중심에, 다리는 x +0.8; 코일 축 놀음 ±0.44 + 레버 놀음 0.405 → 다리 중심 최대 1.65, 홈이 받는 폭 1.45",
     pf("맞음: 받는 폭 %.2f(반폭 %.1f + 입구 %.1f − 선 반지름 %.2f), 코일 축 놀음 %.3f + 레버 놀음 %.3f → 레버 중심 홈이면 여유 %.2f(음수)", (KXL["catch"], PR["spring_groove"][3] / 2, PR["spring_lead_in"], PR["spring_d"] / 2, KXL["coil_axial"], KXL["lever_float"], KXL["margin_r45"])),
     "받아들임",
     pf("뒷벽 홈·보스(4.4)를 긴 다리 x(레버 %+.1f)에 맞춤(`spring_groove_dx`) → 여유 %.2f. 풀린 다리 검사에 코일 뜸(가둠 홈 따라 봉까지 %.2f / 막힌 끝까지 %.1f, 홈 안 기울기 ±%.2f°)을 넣음: −31.3° 레버 공칭 입구 안 %.2f(뜸 넣고 %.2f), 자유각 +5°면 %.2f(뜸 넣고 %.2f) — 입구 밖이어도 x가 맞아 다시 넣을 때 모따기가 받음",
        (PR["spring_groove_dx"], KXL["margin"], (PR["spring_ID"] - PR["rod_L"]) / 2, PR["spring_notch"][2], NT45["theta_c"], LEG["C_+0"]["in_groove"], LEG["C_+0"]["in_groove_float"], LEG["C_+5"]["in_groove"], LEG["C_+5"]["in_groove_float"]))),
    ("스프링 minor 2", "시험 8 되돌림 ‘±5° 넘으면 홈 바닥 y를 0.367 mm/° 옮김’은 더 감는 쪽으로 못 함: 홈 바닥 y211.0 뒤 뒷벽 1.0뿐",
     pf("맞음: 홈 바닥 y%.1f, 뒷벽 끝 y%.0f → %.1f 남음; 껍질 0.4를 두면 %.1f 더 깊게 = +%.1f°", (PR["spring_groove"][0] + PR["spring_groove"][4], _M4.P["rear_wall"][1], _M4.P["rear_wall"][1] - PR["spring_groove"][0] - PR["spring_groove"][4], S0["analysis"]["C06"]["deeper_max"], S0["analysis"]["C06"]["deeper_max"] / (S0["analysis"]["C06"]["arm"] * math.pi / 180))),
     "받아들임",
     pf("시험 8 결과표를 한쪽 한계로 고침: 더 감기는 홈 바닥 깊게 %.1f까지(+%.1f°), 그보다 모자라면 `spring_notch_rot`(가둠 홈을 CW로 돌려 캐리어 다시 출력) 또는 스프링 다시 주문; 덜 감기는 홈 바닥 얕게(보스 안에서 자유)", (S0["analysis"]["C06"]["deeper_max"], S0["analysis"]["C06"]["deeper_max"] / (S0["analysis"]["C06"]["arm"] * math.pi / 180)))),
    ("고침 minor 1", "킬 뿌리가 밸런스 레일 뒷면에 ‘고정’: 그 면은 바닥 구멍 앞 가장자리이고 레일(핀 선 사이 약 82, 리본 차선 위는 9 높이)은 단단한 땅이 아님; 1e장은 단계 0 합격선이 이를 본다고 했지만 시험 3은 띠의 E만 잼",
     pf("맞음: `rail_keel_root` — 레일(y%.1f~%.1f, z%.0f~%.2f) + 바닥 띠를 x 방향 보로(리본 차선 위는 위아래가 따로), 모듈 핀 선에서 단순 지지·비틀림 멈춤, EVA 받침 없음 → kv %.0f N/mm, kr %.0f N·mm/rad, 뒷면에서 %.0f N/mm; 킬 z18이면 화음 자리 %.1f N/mm(< %.0f; 레일 고정 %.1f). 6건반 PLAY 킬 굽힘 %.2f MPa",
        (_M4.P["rail_front_y"], _M4.P["rail_y"][1], _M4.P["z_floor"][0], KRL["rail"].get("rail_top", 0.0), KRL["rail"].get("kv", 0.0), KRL["rail"].get("kr", 0.0), KRL["rail"].get("k_face", 0.0), KRL["k_chord_keel18"], PR["seat_k_chord_req"], KRL["k_chord_rigid"], KRL["keel_sigma_keel18"])),
     "받아들임",
     pf("F|F# 핀(바닥 밑면 z%.0f부터 윗판까지) 앞끝 y152 → **y%.1f**(건반 %s %s까지 %.2f, %s 자세), 킬 y%.1f~%.1f(길이 %.1f, 이전 %.1f) z%.0f~**%.1f**(건반 %s %s까지 %.2f, %s 자세) → 화음 자리 **%.1f N/mm**(%.1f %% 여유; 가장 무른 화음이 다시 %s), 킬 굽힘 %.2f MPa, 첫 모듈 정하중 E·F %.3f mm. "
        "이 판의 첫 시도(킬만 z21로)는 %.1f N/mm였지만 건반 %s %s까지 %.2f(%s 자세, 1.3 미만; ABUSE 복귀 넘침은 공차 뒤 접촉)라 버렸다; 핀 앞끝을 y152에 둔 채 킬을 한계 z%.1f로 하면 %.1f(< %.0f). "
        "레일 받침의 범위: 해치 가장자리에 고정 %.1f, 핀 선 사이 단순 지지만(연속·EVA 없음) %.1f(E·F %.3f mm, 불합격) — 모델 값(핀 선 연속, EVA 없음)은 그 사이다. 하한이 합격선 아래이므로 단계 0에 **조립 시험 21 첫 모듈 정하중**(6 × 60 N, E·F ≤ %.2f mm; 하중 방향은 아래 ‘r4.5 고침 3’)을 넣고 1e장 문장을 고침. "
        "기각한 안: 레일 앞 치마(비틀림 축이 앞으로 가 오히려 떨어짐), 레일 뒷면을 바닥 구멍 위로 늘리기(기판 넣는 길·부품 구역과 겹침), 킬 T 날개(기판 홈 안이라 x로 못 넓힘)",
        (PR["fin_keel"][1], KRL["fin_front"], (KRL.get("fin_clear") or {}).get("key", "?").replace("key ", ""), _pk(KRL.get("fin_clear"), "part"), (KRL.get("fin_clear") or {}).get("d", -1.0), _pk(KRL.get("fin_clear"), "pose"),
         PR["fin_keel"][0], KRL["fin_front"], KRL["fin_front"] - PR["fin_keel"][0], 152.0 - PR["fin_keel"][0], PR["fin_keel"][1], PR["fin_keel"][2],
         (KRL.get("keel_clear") or {}).get("key", "?").replace("key ", ""), _pk(KRL.get("keel_clear"), "part"), (KRL.get("keel_clear") or {}).get("d", -1.0), _pk(KRL.get("keel_clear"), "pose"),
         KRL["k_chord"], 100 * (KRL["k_chord"] / PR["seat_k_chord_req"] - 1), "-".join(R["plate"]["play"]["chord"].get("k_eq_keys", [])), R["plate"]["play"]["chord"].get("keel_sigma", 0.0), KRL["dead"]["EF_max"],
         KRL["k_chord_keel21"], (KRL.get("keel21_clear") or {}).get("key", "?").replace("key ", ""), _pk(KRL.get("keel21_clear"), "part"), (KRL.get("keel21_clear") or {}).get("d", -1.0), _pk(KRL.get("keel21_clear"), "pose"),
         PR["fin_keel"][2], KRL["k_chord_front152"], PR["seat_k_chord_req"], KRL["k_chord_hatch"], KRL["k_chord_fins_span"], KRL["EF_fins_span"] or -1.0, KRL["dead"]["limit"]))),
    ("고침 minor 2", "고침 2b·단계 번호가 남긴 낡은 글: (a) 10.1 T2 행 ‘z31.0’, 부품표 캡스턴 ‘z31.0’ (b) 접착은 10장 4단계인데 3곳이 3단계 (c) 고침 2b 행 레버 57.02 → 56.97(56.97은 r4.5 값) (d) 단계 0 ‘설계 492’",
     "맞음: T2 게이지·S08·T17은 z30.90으로 맞음; 10장 단계 1이 기판 넣기라 접착은 4단계; 고침 2b 레버 57.05 g; 화음 자리는 r4.5 모델 " + pf("%.1f(이 판 %.1f — 킬 고침)", (R45A["seat"]["k_chord"], SEAT["k_chord"])),
     "받아들임",
     pf("(a) T2 행·부품표를 정착 쉼 z%.2f(건반 좌표 z%.1f)로 (b) 시험 20.3·부품표 강철 행·고침 2b 형상 행을 4단계로 (c) ‘57.02 → 57.05 g (r4.5 56.97, r4.5 고침 %.2f)’ (d) 단계 0 글을 모델 값으로(지금 %.0f)", (R["fix2b"]["crown_T2"], PR["z_c"], W["lever_g"], SEAT["k_chord"]))),
    ("고침 minor 3", "12장 ‘뺄 심이 없으면 쐐기 0.1 얇게 다시 출력’은 가장 얇은 백 쐐기(0.349 → 0.249)에서 출력 최소 0.3 아래",
     pf("맞음: 백 쐐기 얇은 끝 %.3f, 끝 부속 A0 %.3f · B0 %.3f · C8 %.3f; 흑 %.3f는 됨", (G["solved"]["wedge"]["w"][0], G["end_parts"]["left"]["pad_faces"]["A0"]["wedge"][0], G["end_parts"]["left"]["pad_faces"]["B0"]["wedge"][0], G["end_parts"]["right"]["pad_faces"]["C8"]["wedge"][0], G["solved"]["wedge"]["b"][0])),
     "받아들임",
     pf("쐐기 얇은 끝 < 0.40인 자리는 쐐기를 그대로 두고 그 패드 자리의 바 밑면을 0.1 올려(바 %.1f → %.1f) 다시 출력하거나 펠트를 0.1 얇게(12장·1e장 글)", (P4["pad_bar_t"], P4["pad_bar_t"] - 0.1))),
]
for r_ in rows_45b:
    w(pf("| %s |", " | ".join(esc(x) for x in r_)))
w()
w("**코일 뜸 — 후보 비교 (모델 `spring_pose`·`spring_T_table`, T(b)와 봉 힘 N(b)을 statics에 넣음; 이력 = μ N r_봉, 마찰 2배면 두 배).** 합격선: DW 47~55 g, 립 y0 ≥ 47 g, UW ≥ 20 g(바닥, 마찰 2배 포함).")
w()
w("| 안 | μ 코일-봉 | 쉼 / 바닥 토크 (N·mm) | 풀림 (°) | 봉 힘 쉼 / 바닥 (N) | 이력 바닥 (N·mm) | D DW / 립 / UW (g) | C# DW / UW (g) | 마찰 2배 D DW / C# 바닥 UW (g) |")
w("|---|---|---|---|---|---|---|---|---|")
for lab_, q_ in FLT.items():
    mu_ = lab_.rsplit("mu ", 1)[1] if "mu " in lab_ else "- (봉에 안 닿음)"
    nm_ = lab_.rsplit(", mu", 1)[0]
    nm_ = (nm_.replace("r4.5 as built (short leg 2.5 on one face)", "r4.5 그대로 (짧은 다리 2.5, 한 면)").replace("short leg 5.0 + ", "짧은 다리 5.0 + ").replace("notch rotated", "홈 돌림").replace("(short leg 2.5)", "(다리 2.5)").replace("r4.5 fix 2 captured short leg", "**r4.5 고침: 가둠 짧은 다리**").replace("(groove", "(홈").replace("deg", "°"))
    w(pf("| %s | %s | %.2f / %.2f | %.1f | %.2f / %.2f | %.2f | %.1f / %.1f / %.1f | %.1f / %.1f | %.1f / %.1f |",
         (nm_, mu_, q_["T_rest"], q_["T_bottom"], q_["unwind"], q_["N_rest"], q_["N_bottom"], q_["H_bottom"], q_["keys"]["D"]["DW"], q_["keys"]["D"]["DW_lip"], q_["keys"]["D"]["UW"],
          q_["keys"]["C#"]["DW"], q_["keys"]["C#"]["UW"], q_["keys"]["D"]["DW_2f"], q_["keys"]["C#"]["UW_bottom_2f"])))
w()
w(pf("**가둠 홈 (새 형상, P18).** 짧은 다리(%.1f, 곧게)는 코일 접선(레버 기준 %.2f°, y%.2f z%.2f)에서 끝 y%.2f z%.2f(축에서 %.2f)까지 간다. 홈은 짐 받은 다리를 CW로 %.2f° 돌린 띠(%.2f° 방향, 폭 %.2f = 선 %.1f + 놀음 %.2f)로, 축에서 잰 두 면 %.3f / %.3f, 주머니 안 %.1f에서 허브 벽을 지나 웹 안 막힌 끝(다리 끝 너머 %.1f)까지 판다(웹 밑면 %.2f 깎음). "
     "짐을 받으면 다리 끝이 바깥 면(y%.2f z%.2f)에, 다리 몸이 안쪽 면의 주머니 가장자리(y%.2f z%.2f)에 닿아 두 점(팔 %.2f)이 짝 힘으로 토크를 받는다: 쉼 %.2f N, 손 25° %.2f N. 긴 다리 힘(쉼 약 0.2 N)은 두 점 힘의 차이와 마찰(또는 막힌 끝)이 받으므로 코일은 봉에 닿지 않는다 — 봉과 틈 쉼 %.3f, 바닥 %.3f, 손 25° %.3f(긴 다리 힘의 홈 방향 성분은 막힌 끝 쪽이고 두 점 마찰로 잡으려면 μ %.2f면 된다; 미끄러져 다리 끝이 막힌 끝에 닿아도 봉과 틈 %.3f 이상). "
     "짧은 다리가 길어져(가둔 다리의 굽힘 길이 2 s_E + l_s) k_t %.3f → **%.3f N·mm/rad**, 자유각 %.2f → **%.2f°**(b = 0 토크 %.2f 그대로), 바닥 토크 %.2f → %.2f, 손 25° %.2f → %.2f N·mm(카탈로그 55° 토크의 %.0f %% → %.0f %%). "
     "주머니 구간은 넣는 슬롯(짧은 다리를 따라 %.2f°, 면 ±%.2f)과 긴 다리 창(%.0f° 방향 윗면 +%.1f)이 뒤쪽으로 이어진 열림이 되고, 두 조각 A(웹 쪽: 두 닿는 점) · B(아래 고리: 다리 힘 없음)로 남는다.",
     (PR["spring_short_leg"], NT45["alpha_s"], NT45["Q"][0], NT45["Q"][1], NT45["T"][0], NT45["T"][1], NT45["tip_r"], NT45["theta_c"], NT45["band_deg"], NT45["width"], PR["spring_d"], NT45["play"], NT45["nn"][0], NT45["nn"][1],
      NT45["ss"][0], PR["spring_notch"][2], NT45["web_cut_depth"], NT45["O"][0], NT45["O"][1], NT45["E"][0], NT45["E"][1], NT45["arm"], CPT["F_couple_rest"], CPT["F_couple_hand"], CPT["gap_rest"], CPT["gap_bottom"], CPT["gap_hand"], CPT["mu_req_max"], CPT["gap_slid_min"],
      R45A["spring"]["kt"], PR["spring_kt"], R45A["spring"]["free_deg"], PR["spring_free_deg"], PR["spring_T0"], R45A["spring"]["states"]["bottom"]["T"], SP45["states"]["bottom"]["T"], R45A["spring"]["states"]["hand 25 deg"]["T"], SP45["states"]["hand 25 deg"]["T"],
      100 * R45A["spring"]["hand_over_cat"], 100 * SP45["hand_over_cat"], NT45["slot_deg"], PR["spring_slot"][2], PR["spring_window"][0], PR["spring_window"][1])))
w()
w("| 홈이 출력된 폭 (설계 대비) | 놀음 | 다리 기울기 변화 | 쉼 토크 (N·mm) | 봉과 틈 (쉼) |")
w("|---|---|---|---|---|")
for k_, q_ in CTL.items():
    w(pf("| %s | %.2f%s | %+.2f° | %.2f | %.3f |", (k_, q_["play"], "" if q_["feasible"] else " (선이 안 들어감)", q_["dtheta"], q_["T0"], q_["gap_left"])))
w()
_ilo = R45["insert_lo"]
w(pf("**넣기와 창.** 봉을 꿰기 전, 자유 상태 스프링을 짧은 다리 끝부터 홈 중심선을 따라 밀어 넣는 길(0.02 걸음)에서 짧은 다리 ↔ 홈 면 %.3f(홈이 0.10 / 0.15 좁게 나오면 %.3f / %.3f), 코일 ↔ 조각 A %.2f · B %.2f, 긴 다리(자유 방향 %.1f°) ↔ A %.2f · B %.2f → %s. "
     "긴 다리는 레버 %.1f°~%.1f° 내내 창 안(면까지 %.2f + 선 반지름 + 0.2; 가장 좁은 곳은 손 들기 25°). 허브·웹: ABUSE 층 안 %.2f MPa(Kt 2, 한계 25), PLAY %.2f(한계 12).",
     (IN45["short_A"][0], _ilo["-0.1"] if "-0.1" in _ilo else _ilo.get(-0.1, 0.0), _ilo["-0.15"] if "-0.15" in _ilo else _ilo.get(-0.15, 0.0), IN45["per"]["coil|A"][0], IN45["per"]["coil|B"][0], IN45["long_free_dir"],
      IN45["per"]["long leg|A"][0], IN45["per"]["long leg|B"][0], "지나감" if IN45["clear"] else "막힘", R["r42"]["spring_b_range"][0], R["r42"]["spring_b_range"][1], R["r42"]["spring_slot"]["margin"],
      HN45["abuse"]["section"]["sigma_kt"], HN45["play"]["section"]["sigma_kt"])))
w()
def _onto_ko(s_):
    """r4.5 fix round: short Korean name of a lever-drop landing (metrics lever_drop 'onto')."""
    s_ = s_ or "-"
    if s_.startswith("control-board boss"):
        return "기판 보스(" + ("나사 보스" if "screw" in s_ else "위치 핀 보스") + ", 레일 뒷면 브래킷)"
    if s_.startswith("board part: "):
        return s_[12:].split(" (")[0].replace(" module on pin headers", " 모듈(핀 헤더 위)")
    if s_ == "control board":
        return "기판 윗면"
    return s_.split(" (")[0]


w(pf("**레버 떨어짐 = 실제 착지(도면 작성자).** `metrics.lever_drop`이 이제 `circuit_r44.drop`과 같은 계산(이름 있는 BRD-01 부품·보스·기판)이다: " + "; ".join(pf("%s %.2f°(%s)", (k_, LD[k_]["drop_deg"], _onto_ko(LD[k_]["onto"]))) for k_ in ("D#", "E", "F", "F#", "G", "G#"))
     + pf(". 바닥판 위 레버(C·D 등)는 %.2f°로 그대로다.", LD["D"]["drop_deg"]), ()))
w()
w("**도면 작성자 형상 메모 처리.**")
w()
w("| 메모 | 처리 |")
w("|---|---|")
for a_, b_ in (
        ("metrics lever_drop이 z20 일반 구역 착지", "run_all이 실제 착지(`lever_drop(actual=True)`)를 씀 — 위 문단, 11장"),
        ("짧은 다리 홈이 레버 D 기준 하나뿐(흑은 쉼 각이 약 0.5° 다름)", "홈은 레버 좌표 값 그대로 두고 `solved.spring.rest_deg_per_lever`에 레버마다 쉼 각을 내보냄(주머니 구간 단면은 레버 부품으로 이미 레버마다 돌려 나감)"),
        ("C06a 입구가 발 벽 뒤라 숨은 선으로만 보임", "모델 잘못 아님(메모 그대로). C06a 홈은 이제 다리 x(코일 가운데 +0.8)"),
        ("kit.MAT_FIXED에 ‘control-board boss’ 항목이 없음", "도면 쪽 `kit.py`(도면 작성자 폴더)라 이 판에서 고치지 않음 — 이름이 ‘control-board boss’로 시작하는 프레임 부품이라 프레임 분류가 맞음"),
        ("T2 부리 프리즘이 몸통 윗면과 0.01 겹쳐 부리 밑이 z53.39", "부리(손잡이) 밑면 z57.5 한 프리즘 + ‘beak web to the body top (0.01 into the body)’ 따로"),
        ("T24 ‘앞 발 y132.3~133.85’와 프리즘 이름이 다름", "프리즘을 ‘front body (y132.00~132.30)’ + ‘front foot = land on the rail top (y132.30~…)’로 나누고 T24 글에 앞 몸통을 적음"),
        ("T09 기둥이 프리즘 투영으로는 한 덩어리", "tools_geometry에 프리즘마다 (X, z) `front` 윤곽을 더함 — T09 기둥은 사다리꼴(윗면 8, 밑 17); T09 글에 적음"),
        ("뒷벽 스프링 홈이 잘라낸 부품으로 안 나감", "geometry `parts`에 ‘spring groove cut …’(female) 추가, 끝 부속도"),
        ("P18 입구 모따기 0.5×45°가 없음", "‘spring groove entry chamfer …’(female, 옆모습 + 앞모습 `front`) 추가"),
        ("스프링 다리가 빼기·떨어짐 자세로 안 나감", "스프링 부품에 `side_drop`(레버를 lever_drop 각으로; 자유각 아래에서 긴 다리가 레버와 함께 돎)을 더함; `side_service` = 빼기 자세")):
    w("| " + esc(a_) + " | " + esc(b_) + " |")
w()
w("**결과 (r4.5 → r4.5 고침, run_all 전체 다시 돌림).**")
w()
w("| 항목 | r4.5 | r4.5 고침 | 변화 |")
w("|---|---|---|---|")
def _row45(lab_, o_, n_, f_="%.2f"):
    w(pf("| %s | " + f_ + " | " + f_ + " | %+.2f |", (lab_, o_, n_, n_ - o_)))
for lab_, c_ in (("백", "white"), ("흑", "black")):
    _row45("DW " + lab_ + " (g)", R45A[c_]["DW"], R[c_]["DW"])
    _row45("UW " + lab_ + " (g)", R45A[c_]["UW"], R[c_]["UW"])
    _row45("바닥 UW 마찰 2배 " + lab_ + " (g, ≥ 20)", R45A[c_]["UW_bottom_2f"], R[c_]["UW_bottom_2f"])
    _row45("스프링 토크 바닥 " + lab_ + " (N·mm)", R45A[c_]["spring_T_bottom"], R[c_]["spring_T_bottom"])
_row45("레버 (g)", R45A["white"]["lever_g"], W["lever_g"])
for k_, lab_ in (("rep_hz_white", "연타 백 (Hz)"), ("rep_hz_black", "연타 흑 (Hz)"), ("rep_hz_white_2x_friction", "연타 마찰 2배 백 (Hz, ≥ 13.3)"), ("rep_hz_black_2x_friction", "연타 마찰 2배 흑 (Hz)"),
                 ("full_return_white_ms", "끝까지 복귀 백 (ms)"), ("key_lift_play_mm", "노치 들림 PLAY (mm)"), ("min_clearance_mm", "모듈 스윕 최소 (mm)"), ("min_clearance_after_tol_mm", "공차 뒤 (mm)"), ("module_mass_kg", "모듈 무게 (kg)")):
    _row45(lab_, M45A[k_], M[k_], "%.3f" if k_ in ("key_lift_play_mm", "module_mass_kg") else "%.2f")
_row45("6건반 화음 자리 (N/mm, ≥ 460)", R45A["seat"]["k_chord"], SEAT["k_chord"], "%.1f")
_nchk45 = [c_ for c_ in R["checks"] if not c_["ok"]]
w()
w(pf("0장 판정 %d개 가운데 불합격 %d개%s. 기본 구성 비용 변화 %s원(r4.5 %s원, 스프링은 같은 부품을 길게 자름).", (len(R["checks"]), len(_nchk45), (": " + "; ".join(c_["check"] for c_ in _nchk45)) if _nchk45 else "", skrw(R["cost"]["delta"]), skrw(R45A["cost"]["delta"]))))
w()
# r4.5 fix 3: independent verification of the fix round - procedure and text only (no design number or geometry changed)
_c17 = S0C17["dead_seats"]
_s0p = {p_["id"]: p_ for p_ in S0["parts"]}
w("**r4.5 고침 3 — 재검증 지적 (절차·글만 고침).** 설계 수치와 형상(모듈·건반·레버)은 바뀌지 않았다. run_all은 다시 돌리지 않았다. 단계 0 키트에 C17a 한 개가 늘었다.")
w()
w("| 지적 | 무엇이 틀렸나 | 고친 것 |")
w("|---|---|---|")
for r_ in (
    ("시험 21 하중 방향 (major)",
     pf("시험 21이 바닥 EVA 위의 모듈에서 윗판 윗면을 눌렀다. 쓰임에서는 패드가 윗판을 밑에서 밀어 F|F# 핀·킬이 레일 뒷면을 들어 올린다. 위에서 누르면 레일·바닥 띠(z%.0f~%.0f)가 EVA(z%.0f~%.0f)에 얹혀, 레일 자체가 약해도 단단한 레일(E·F %.3f mm)처럼 읽힌다. "
        "그래서 불합격 쪽 하한(이웃 핀 선 사이 단순 지지, %.3f mm)도 합격으로 나올 수 있었다. 위 표의 ‘EVA가 레일을 받쳐 실제는 더 단단하다’는 아래로 누를 때만 맞다",
        (_M4.P["z_floor"][0], _M4.P["z_floor"][1], _M4.P["z_eva"][0], _M4.P["z_eva"][1], _c17["rigid"]["EF"], _c17["fins_span"]["EF"])),
     pf("시험 21을 쓰임 방향으로 고쳤다. 모듈을 새 단계 0 부품 **C17a 받침 빗**(높이 %.0f, 폭 %.0f인 이 %d개가 핀 선 x%s 밑, 뒤 막대가 뒷벽 밑; 레일 밑 x%.1f~%.1f와 기판 구멍 밑은 빔, %.1f × %.1f, %.1f cm³)에 얹고 위에서 누른다. "
        "모델이 선형이라 쓰임과 같은 레일 휨이다. 합격선 E·F ≤ %.2f mm는 그대로다(모델 %.3f). 두 끝 값은 시험이 누르는 %s 화음 값이다(위 표의 %.3f는 단순 지지일 때 가장 무른 %s 화음 값). ‘먼저 EVA 닿음 확인’ 되돌림과 ‘EVA가 더 단단하게 함’ 문장을 지웠다(17장 21번, 18장, 위 표)",
        (S0C17["h"], S0C17["tooth_w"], len(S0C17["fin_lines"]), " / ".join(f1(v_) for v_ in S0C17["fin_lines"]), S0C17["rail_free"][0], S0C17["rail_free"][1],
         _s0p["C17a"]["bbox"][0], _s0p["C17a"]["bbox"][1], _s0p["C17a"]["volume_cm3"], S0C17["limit"], _c17["fins"]["EF"], "-".join(S0C17["keys"]),
         S0C17["fins_span_weakest"]["EF"], "-".join(S0C17["fins_span_weakest"]["keys"])))),
    ("단계 0 되돌림이 설계와 어긋남",
     "17장 정하중 줄의 ‘킬 뿌리 더 키움’: 킬은 이미 건반 F와 1.3 한계다. 17장 3번의 ‘F|F# 핀이 바닥에 닿는지 확인, 핀 밑면 덧댐’: r4.4 고침 2b부터 기판 밑 바닥은 구멍이고 핀은 킬로만 레일에 붙는다. 17장 스프링 넣기 줄은 r4.5의 한 면 홈 글이었다",
     "정하중 되돌림 = 잰 k_ch로 화음 자리 동역학을 다시 보고, 그래도 불합격이면 회로 세션과 리본 차선 위 레일 높이를 다시 정함(시험 21과 같음). 3번 되돌림 = 윗판 채움 100 % 또는 `plate_t` +0.6~1.2(17.1장 시험 3 표), 킬·레일 이음은 시험 21. "
     "스프링 넣기 = 가둠 홈 순서(시험 13). 정하중 줄은 9번에 끼어 있어 10~21번이 키트 번호와 하나씩 어긋났다 — 표 끝 21번으로 옮겨 번호를 키트와 맞췄다"),
    ("핀 발 y152 글",
     pf("결과 파일(results.txt)과 부품표 프레임 줄이 F|F# 핀 발을 y152~%.1f로 적었다. 핀 앞끝은 r4.5 고침에서 y%.1f(`keel_front`)다", (PR["fin_slot_y"][1], R["keel_rail"]["fin_front"])),
     pf("두 곳을 `keel_front`로 찍음: y%.1f~%.1f (run_all.py; results.txt·parts_list.json·metrics.json은 같은 모델이라 그 글만 고침)", (R["keel_rail"]["fin_front"], PR["fin_slot_y"][1]))),
    ("C06b STL이 닫힌 몸이 아님",
     pf("허브 받침 원기둥(Ø%.1f = 허브 R%.1f)의 꼭짓점이 주머니 단면이 허브 원에서 웹으로 꺾이는 점(0, −%.1f)과 겹쳐 Z7.01에 비다양체 모서리가 생겼다", (2 * _M4.P["hub_R"], _M4.P["hub_R"], _M4.P["hub_R"])),
     pf("허브 받침을 Ø%.1f로(허브 안 0.05). 단계 0 STL %d개가 모두 닫힌 몸이다(make_stage0 검사, trimesh로도 확인)", (2 * _M4.P["hub_R"] - 0.1, len(S0["parts"])))),
):
    w(pf("| %s |", " | ".join(esc(x_) for x_ in r_)))
w()

# ============================================================================================ 2
w("## 2. r3 → r4 단순화")
w()
w("### 2.1 전후 비교 (모듈 한 개, 표시가 없으면)")
w()
w("| 항목 | r3 | r4 | 변화 |")
w("|---|---|---|---|")
w(pf("| 출력 부품 수 | %d | %d | %+d |", (n3p, n4p, n4p - n3p)))
w(pf("| 구매 부품 수 (캡스턴 나사·너트, 접시 스프링 낱개로) | %d | %d | %+d |", (n3b, n4b, n4b - n3b)))
w(pf("| 부품 수 합 | %d | %d | %+d (%.0f %%) |", (n3p + n3b, n4p + n4b, n4p + n4b - n3p - n3b, 100.0 * (n4p + n4b - n3p - n3b) / (n3p + n3b))))
w(pf("| 악기당 공구 | 드라이버 Ø30, 빼기 고리, M3 탭, Ø3 H7 리머 | Ø4.0 드릴, 육각 렌치 2.0(캡스턴, 벤치에서만), 출력 공구 %d개(벤치 지그 받침·높이 블록·캡스턴 벤치 게이지·밸런스 핀 높이 게이지, 10.1장) | |", len(TLP)))
w(pf("| 모듈 무게 | %.2f kg | %.2f kg | %+.0f g |", (r3s["module_kg"], M["module_mass_kg"], 1000 * (M["module_mass_kg"] - r3s["module_kg"]))))
w(pf("| 맨 위 높이 | 커버 z%.1f, 손나사 머리 z%.1f | 윗판 z%.2f (그 위 없음) | %+.1f mm |", (r3s["cover"], r3s["heads"], M["cover_top_z_mm"], M["cover_top_z_mm"] - r3s["heads"])))
w(pf("| 기본 구성 비용 변화 (88건반) | %s원 | %s원 | %s원 |", (skrw(r3s["cost"]), skrw(M["base_cost_delta_krw"]), skrw(M["base_cost_delta_krw"] - r3s["cost"]))))
w(pf("| 금속 (88건반) | %.2f kg | %.2f kg | %+.2f kg |", (r3s["metal"], M["metal_kg_88"], M["metal_kg_88"] - r3s["metal"])))
w(pf("| 필라멘트 (88건반, 서포트 포함) | %.2f kg · %.0f h | %.2f kg · %.0f h | %+.2f kg |", (r3s["filament"], r3s["print_h"], M["filament_kg"], M["print_h"], M["filament_kg"] - r3s["filament"])))
w(pf("| 88건반 본체 무게 | %.1f kg | %.1f kg | |", (R3["totals"]["body_kg"], TO["body_kg"])))
w(pf("| 유효 질량 m_eff (백 / 흑) | %.1f / %.1f g | %.1f / %.1f g | 가볍게 느껴짐 |", (r3s["meff_w"], r3s["meff_b"], M["m_eff_white_g"], M["m_eff_black_g"])))
w("| 조립 뒤 다시 조이기 | 24 h 뒤, 운반 뒤 손나사 8개 | 없음 | |")
w()
w("출력 부품 수 내역 (모듈): r3 = " + ", ".join(pf("%s %d", kv) for kv in SIM["r3_printed"].items()) + "; r4 = " + ", ".join(pf("%s %d", kv) for kv in SIM["r4_printed"].items()) + ".")
w("구매 부품 수 내역 (모듈): r3 = " + ", ".join(pf("%s %d", kv) for kv in SIM["r3_bought"].items()) + "; r4 = " + ", ".join(pf("%s %d", kv) for kv in SIM["r4_bought"].items()) + ".")
w()
w("### 2.2 뺀 것과 그 값")
w()
w("| 뺀 것 (r3) | 대신 (r4) | 성능 대가 (숫자) |")
w("|---|---|---|")
w(pf("| 업스톱 레일 SS400 3T×60 (231 g), 손나사 8, 접시 스프링 72, 탭 강철 띠 4 + 주머니, 드라이버, 24 h 다시 조이기 | 프레임 윗판(r3 브리지를 y%.1f까지 앞으로 늘림) + 핀 칸마다 패드 바 1개(모듈 4) | "
  "패드 자리 강성 건반마다 %.0f~%.0f N/mm(연구: r3 레일+나사+브리지 433~816; r4.1은 F\\|F# 핀이 기판 홈을 지나 바닥에 닿음, r4.4 고침 2b부터 킬로 밸런스 레일에). 6건반 동시 화음에서는 자리마다 %.0f N/mm로 물러져 가벼운 누름(0.45~0.6 N)에서 재무장 → 펌웨어 거름 필수. "
  "이음이 없으니 ‘이음 열림’ 문제 자체가 없음 |", (PR["ledge_y0"], min(SEAT["k_keys"].values()), max(SEAT["k_keys"].values()), CD["k"])))
w("| 먼지 커버 판 + 위치 핀 2 + 자석 2 | 가림판 띠 1개(윗판 앞 턱에 걸침) | 윗판 윗면이 겉면이 됨. 운반할 때 가림판은 걸려 있을 뿐이라 모듈을 뒤집지 않는다 |")
w(pf("| 흑건 납 5 g × 5 + 추 칸 + 출력 뚜껑 + 에폭시 | 없음 | 흑 노치 들림 PLAY %.3f, ABUSE %.3f(한계 0.40); 흑건은 1 N에서 펠트 위 %.2f mm에 멈춤(레버가 패드에 먼저) |", (mx("black", "play_", "lift_max"), mx("black", "abuse_", "lift_max"), H["held_pad_front_b"])))
w(pf("| 강철 블록 9×50×21.5 (75.8 g) | 9×19×40 (%.1f g) + 비틀림 스프링 12 | 스프링 12개가 늘어남(r4.5: 미스미 기성품 %s, 두 다리를 잘라 씀; 100 × 310원). 행정 중간 DW가 %.1f g까지 오름(쉼 %.1f). 대신 m_eff %.1f → %.1f g, 연타 여유가 커짐 |", (W["steel_g"], PR["spring_cat"]["part"], W["DW_max_stroke"], W["DW"], r3s["meff_w"], M["m_eff_white_g"])))
w(pf("| 경화 SUJ2 Ø3 + 황동 부싱 5 + H7 리머 | SUS304 Ø4 (건반 봉과 같은 4 m 봉), 출력 보스 Ø3.9 → Ø4.0 드릴 | 레버 봉 마찰 %.2f g(r3 0.71 g). 6건반 화음 봉 응력 %.0f MPa, ABUSE %.0f MPa로 풀림재 항복 205 아래; 보스 지압 %.1f MPa(ABUSE) |", (W["fr"]["lever_rod"], LR["play"]["chord"]["sigma"], M["rod_abuse_mpa"], LR["abuse"]["chord"]["boss_bearing"])))
w(pf("| 간격 C-링 8 | 허브 칼라(캐리어와 한 몸, r4.1: 0.05씩 짧게) | 칸마다 축 놀음 %s; 캐리어가 위치마다 달라짐(%d곳, 이름 새김) |", (" / ".join(pf("%.2f", q) for q in R["axial_play"]), len(VAR["carriers"]))))
w(pf("| L 서비스 블록 12 (조립) + 3 (보관) | 없음 (r4.1 조립 순서: 레버 먼저, 건반 나중) | 빠진 건반의 레버는 바닥판이나 기판 부품 위에 %.2f N으로 놓인다; 다시 넣을 때 손톱 턱으로 든다 |", LD["E"]["F_rest"]))
w("| 패드 홀더 12 + 흑 스페이서 5 | 패드 바에 출력한 쐐기 | 없음. 건반마다 조정은 PET 심 |")
w("| 스프링 자리판 12 (빈 선택품, 만들 수 없던 것) | 비틀림 스프링 (기본) | 12개 추가 |")
w("| 강철 앞 윗모서리 2×45° 줄 모따기 (88번) + R3 캡 접점 | 패드가 드러난 강철 윗면에 닿음 | 없음 |")
w(pf("| 출력 빼기 고리 | 손톱 + 레버 손톱 턱 | 건반 뒤 턱 당김 %.1f N(스냅 %.0f N; R2.50 쿠폰이면 %.1f N) |", (RM["white"]["pull_N"], PR["snap_F"], RM["white"]["pull_N_snap_hi"])))
w()
w("### 2.3 단순화 연구 안: 채택 / 기각")
w()
w("세 연구(업스톱 U1~U10, 건반 유지 RET-1~10, 모듈 감사 A1~A12)의 안을 하나씩 판정했다. 연구들은 서로 다른 레버·패드를 가정했으므로, 채택한 안들은 이 모델에서 한꺼번에 다시 계산했다.")
w()
w("| 안 | 내용 | 판정 | 이유 (숫자) |")
w("|---|---|---|---|")
rows = [
    ("U1", "패드 면을 1 N 진짜 정착에서 잡음", "채택", "r3 major 1의 해결. 1.4 s 누른 뒤 레버 각속도 1e-6 rad/ms 미만에서 읽음"),
    ("U2", "레버가 패드에 먼저 닿는 틈, 보조 스프링 삭제", "일부 채택",
     pf("레버 먼저는 채택하되 백 %+.2f / 흑 %+.2f(연구 −0.8 / −0.6은 무거운 r3 레버용). 스프링은 A1·A2의 비틀림 스프링으로 대신 — 가벼운 레버는 스프링 없이 연타 13.46 / 12.50 Hz(마찰 2배)로 불합격(r4 탐색)", (PR["gap_us_w"], PR["gap_us_b"]))),
    ("U3", "패드 접점을 강철 윗면으로, 미세셀 우레탄 4T + 펠트 1T", "고쳐서 채택",
     pf("접점은 채택(모따기·캡 벽 조건 삭제). 폼 %.0fT, 패드 y%.0f~%.0f로 바꿈: 뒤로 10 mm 옮기면 윗판이 두꺼운 곳에 가까워 자리 강성 1.7배, 폼 6T는 자리가 물러도 유령이 덜함(950 N/mm, 0.45 N: 4T 67 %%, 6T 32 %%, r4 탐색)", (PR["pad_foam"], PR["pad_y"][0], PR["pad_y"][1]))),
    ("U4", "흑건 납 삭제", "채택", pf("흑 ABUSE 들림 %.3f ≤ 0.40", mx("black", "abuse_", "lift_max"))),
    ("U5", "레일·나사·접시 스프링·띠·핀·자석 삭제, 프레임 받침판 + 패드 바", "채택 (고쳐서)",
     pf("패드 바를 계단형으로(앞부분은 윗판 홈 속 1.5 높게 → 레버 앞 모서리와 틈), L 레일(웹 + 립)에 끼우고 가장자리 잎 혀로 자리에 밀어 올림(r4.2). 맨 위 z%.2f", M["cover_top_z_mm"])),
    ("U6", "펌웨어 유령 거름 (250 ms, 0.30 m/s, 25 %)", "고쳐서 채택",
     pf("고정 0.30 대신 ‘앞 음 속도의 25 %%, 최대 %.2f’(ABUSE 화음 유령 내려옴 최대 %.2f); r4.1: 앞 음 문턱 1.2 → %.1f m/s(검증자 물리 M1)", (PR["ghost_v_desc"], max(v["v_desc"] for k, v in gh.items() if v["armed"]), PR["ghost_v_note"]))),
    ("U7", "D11 e ≤ 0.07, 자리 강성 조건, 단계 0 처짐 시험", "채택", pf("D11 고침(r3 major 8). 자리 합격선 %.0f N/mm(100 N에 %.2f mm; r4.0 설계값, 모든 PLAY 목표 통과), 6건반 화음 %.0f N/mm; r4.1 설계 %.0f / %.0f", (PR["seat_k_req"], 100.0 / PR["seat_k_req"], PR["seat_k_chord_req"], SEAT["k_min"], SEAT["k_chord"]))),
    ("U8", "R3 캡 접점 유지 + 폼 7T", "기각", "연구: 맨 위 z77.3(목표 z74 초과), 흑 ABUSE 들림 0.373"),
    ("U9", "레일 유지, 접시 스프링 없이 손 조임 너트·쿼터턴", "기각", "연구: PETG가 5~10 µm 앉으면 예하중 ≈ 0 → 한 건반 PLAY에서도 이음이 열림"),
    ("U10", "레일 + 접시 스프링 유지, U1~U4만", "기각", "연구: 부품이 줄지 않고 z78.0 / 80.7"),
    ("RET-1", "흑건 납 삭제, 흑 캡스턴 다시 풂", "채택", pf("흑 캡스턴 y%.2f (가벼운 레버로 다시 풂)", B["y_cap"])),
    ("RET-2", "스냅 판정을 들림으로 (PLAY ≤ 0.20, ABUSE ≤ 0.40), 반지름 쿠폰", "채택", "r3 major 2의 해결"),
    ("RET-3", "키퍼 틈 1.2 → 1.5", "채택", pf("PLAY 키퍼 최소 %.2f(합격선 재료 %.2f)", (M["keeper_gap_min_mm"], M["keeper_gap_sets_mm"]))),
    ("RET-4", "밸런스 핀 1.2 앞으로", "채택", pf("r3 major 7의 해결, 핀 ↔ 입술 벽 %.2f", CL["pin_lip_wall"])),
    ("RET-5", "흑 탭 7.5 → 6.9", "채택", "r3 major 4의 해결"),
    ("RET-6", "흑 패드 강성 하한 (ABUSE 들림 0.40)", "채택 (형태 바꿈)", pf("패드가 폼이 되어 합격선을 ‘폼 E ≥ 0.7 MPa, e ≤ 0.07’로 적음. 그 조합에서 흑 ABUSE 들림 %.3f", SE["pass lines together (pad e 0.07, E 0.7, front e 0.22)"]["black"]["lift_abuse"])),
    ("RET-7", "도구 없는 빼기(레버를 손으로 듦), 고리·L 블록 삭제, 조립 순서", "고쳐서 채택",
     pf("윗판은 남으므로 레버를 손톱 턱으로 듦(%.2f N), 레버는 윗판에 닿을 때까지 %.1f°. L 블록은 보관용 3개도 없앰", (RM["white"]["F_tab"], min(SW.values())))),
    ("RET-8", "스냅 없이 열린 노치", "기각", "연구: 무른 패드에서 ABUSE 흑 들림 1.27 mm(빠짐)"),
    ("RET-9", "닫힌 구멍 + 빼는 봉", "기각", "연구: 건반 하나를 빼려면 봉을 12건반에서 뽑아야 함"),
    ("RET-10", "늘 닿는 키퍼 / 틈 없는 입술", "기각", "연구: 키퍼 무접촉 목표 위반, 출력 공차에 민감"),
    ("A1", "강철 9×19×40 + 스프링 기본", "채택", pf("모듈 강철 −%.0f g, m_eff %.1f → %.1f", (12 * (r3s["steel_block"] - W["steel_g"]), r3s["meff_w"], M["m_eff_white_g"]))),
    ("A2", "비틀림 보조 스프링", "채택", "r3 major 5의 해결"),
    ("A3", "레버 봉 SUS304 Ø4 (냉간인발)", "채택 (조건 풂)", pf("r4 하중에서 ABUSE %.0f MPa < 풀림재 205 → 냉간인발 지정 불필요", M["rod_abuse_mpa"])),
    ("A4", "흑건 납 삭제", "채택", "U4·RET-1과 같음"),
    ("A5", "C-링 → 허브 칼라, L 블록 삭제", "채택", ""),
    ("A6", "높이 z74 (레일 밑면 패드 + 얇은 노브 너트)", "목표만 채택", pf("레일 대신 윗판으로 z%.2f", M["cover_top_z_mm"])),
    ("A7", "고정 방식에 달린 삭제 목록", "U5로 대신", "띠·접시 스프링·핀·자석은 삭제, 브리지는 윗판이 되어 남음"),
    ("A8", "질량·부품·비용 합", "정보", pf("r4 실제: %.2f kg, %d개, %s원", (M["module_mass_kg"], n4p + n4b, skrw(M["base_cost_delta_krw"])))),
    ("A9", "보관함 칸 나눔", "채택", "r3 minor 해결"),
    ("A10", "앞 펠트 y1.5~9.0", "채택", "r3 minor 해결"),
    ("A11", "가림판 z45.5", "채택", "r4는 가림판을 1.0 앞으로도 옮김(레버 손톱 턱과 틈)"),
    ("A12", "손 닿는 조정", "고쳐서 채택", "PET 심은 레일이 아니라 빼낸 패드 바의 패드 밑에"),
]
for a_, b_, c_, d_ in rows:
    w(pf("| %s | %s | %s | %s |", tuple(esc(x) for x in (a_, b_, c_, d_))))
w()

# ============================================================================================ 3
w("## 3. 원리 (r4)")
w()
w(pf("- 건반은 Ø4 SUS304 봉 위의 짧은 시소다(봉 중심 K = (%.1f, %.1f)). 스냅 노치(S04)가 봉을 223° 감싸고, 앞으로 옮긴 밸런스 핀(y%.1f)이 건반 뒤쪽 x를 잡는다.", (141.0, 21.5, PR["pin_y"])))
w(pf("- 숨은 빔의 M3 버튼헤드 캡스턴(백 y%.2f · 흑 y%.2f)이 레버 밑 펠트 띠를 들어 올린다. 레버 = 출력 캐리어(폭 10.6, 허브 칼라 일체 — 칼라 길이만 위치마다 다름) + SS400 평철 9×19×40(%.1f g, 모따기 없음), "
  "SUS304 Ø4 봉에 매달린다(L = (203.25, 33.5)). 허브 가운데 비틀림 스프링(r4.5: 미스미 %s, 두 다리를 잘라 k_t %.2f N·mm/rad, b = 0에서 %.1f° 감김)이 강철을 아래로 민다.", (W["y_cap"], B["y_cap"], W["steel_g"], PR["spring_cat"]["part"], PR["spring_kt"], -PR["spring_free_deg"])))
w(pf("- 쉬는 동안 레버 무게와 스프링이 캡스턴을 %.2f N(흑 %.2f N)으로 눌러 쉼 펠트가 뒤 선반(z%.3f)에 앉는다. 플라스틱 상시 응력은 최대 %.2f MPa. 예하중이 걸린 이음이 하나도 없다.", (W["N"], B["N"], H["z_shelf"], M["max_rest_stress_mpa"])))
w(pf("- 누르면 레버의 드러난 강철 윗면(윗 립 사이 7.4)이 패드(폼 %.0fT + 펠트 %.0fT, 폭 %.0f, y%.0f~%.0f)에 먼저 닿고(백 %+.2f, 흑 %+.2f mm) 곧 건반이 앞 펠트에 닿는다. "
  "패드 면은 1 N 정착 바닥의 강철 윗면과 평행(%.1f° / %.1f°)이라 폼이 고르게 눌린다. 패드는 패드 바의 출력 쐐기에 붙어 있고, 패드 바는 윗판 밑 L 레일(웹 + 립)에 끼워져 가장자리의 출력 잎 혀가 립을 딛고 바를 윗판 자리에 밀어 올린다. 패드 힘은 윗판에 **누르는 힘**으로만 전한다.", (PR["pad_foam"], PR["pad_felt"], PR["pad_w"], PR["pad_y"][0], PR["pad_y"][1], PR["gap_us_w"], PR["gap_us_b"], H["held_b_w"], H["held_b_b"])))
w(pf("- 윗판(프레임과 한 몸, z%.2f)은 r3 브리지를 y%.1f까지 늘린 것이다. 핀 5장과 뒷벽이 받친다. 기판 위 F|F# 핀은 r4.1부터 만능기판 앞쪽 홈을 지나 y%.1f~%.1f에서 내려가고(r4.4 고침 2b: 기판 밑 바닥이 뚫려 있어 바닥 대신 킬로 밸런스 레일 뒷면에 붙음 — 기판은 밑에서 넣음; r4.5 고침: 이 핀만 앞끝 y%.1f, 킬 y%.1f~%.1f z%.0f~%.1f), r4.3부터 그 뒤는 뒷벽까지 매달려 있다(뒤 선반은 USB 플러그 위가 뚫려 있음). 먼지 커버는 윗판 앞 턱에 걸친 가림판 띠 하나다.", (M["cover_top_z_mm"], PR["ledge_y0"], KRL["fin_front"], PR["fin_slot_y"][1], KRL["fin_front"], P4["fin_keel"][0], KRL["fin_front"], P4["fin_keel"][1], P4["fin_keel"][2])))
w(pf("- 손을 떼면 레버 무게 + 스프링이 캡스턴을 눌러 건반을 되돌린다(연타 %.1f / %.1f Hz). 건반과 레버 사이에 홈이 없어 유격이 없다.", (M["rep_hz_white"], M["rep_hz_black"])))
w(pf("- v3 앞 훅은 크로스바 위 %.1f mm의 ‘닿지 않는 키퍼’다. 센서는 자석 Ø5×2(y67), 2.5 m/s 과다 누름에서도 간격 %.2f mm(≥ 3.0).", (PR["keeper_gap"], M["min_sensor_gap_mm"])))
w()

# ============================================================================================ 4
w("## 4. 부품 — 개수와 질량 (`parts_list.json`)")
w()
w("| 부품 | 종류 | 사양 | 모듈당 | 88건반 전체 (예비 포함) | 개당 질량 g | 비고 |")
w("|---|---|---|---|---|---|---|")
# r4.4 doc: (a) the carrier's hub-collar list is re-formatted here with the one rounding rule (parts_list.json's run_all text uses '%.2f':
# C 0.955 -> 0.95); (b) the printed-tool row is taken from tools/tools_geometry.json (parts_list.json still has the r4.3 estimate 3 x 15 g)
_cvl = list(R["layout"]["collars"].items()) + [kv_ for s_ in ("left", "right") for kv_ in EP[s_]["collars"].items()]
_cvs = "; ".join(pf("%s %.2f/%.2f", (k_, v_[0], v_[1])) for k_, v_ in _cvl)
PL_STALE = []
for p in PLJ["parts"]:
    p = dict(p)
    if p["name"].startswith("레버 캐리어") and "위치마다 다름: " in p["spec"]:
        a_ = p["spec"].index("위치마다 다름: ") + len("위치마다 다름: ")
        b_ = p["spec"].index("), 스프링", a_)
        assert [t_.split(" ")[0] for t_ in p["spec"][a_:b_].split("; ")] == [k_ for k_, v_ in _cvl]
        if p["spec"][a_:b_] != _cvs:
            _chg = [(o_, n_) for o_, n_ in zip(p["spec"][a_:b_].split("; "), _cvs.split("; ")) if o_ != n_]
            PL_STALE.append(pf("레버 캐리어 칼라 길이 %d곳(예: %s → %s)", (len(_chg), _chg[0][0], _chg[0][1].split(" ")[1])))
        p["spec"] = p["spec"][:a_] + _cvs + p["spec"][b_:]
    if p["name"].startswith("출력 공구"):
        _tg = sum(v_["mass_g"] for v_ in TLP.values())
        if p["total"] != len(TLP) or abs(p["unit_g"] * p["total"] - _tg) > 1.0:
            PL_STALE.append(pf("‘출력 공구’ 행 %d개 × %.1f g → %d개 합계 %.0f g", (p["total"], p["unit_g"], len(TLP), _tg)))
        p.update(name="출력 공구 (악기당 1벌, 10.1장)", spec="벤치 지그 받침(T1a), 높이 블록(T1b), 캡스턴 벤치 게이지 = 가짜 레버(T2), 밸런스 핀 높이 게이지(T3) — 형상·기준·쓰는 법·출력은 10.1장",
                 total=len(TLP), unit_g=" / ".join(pf("%.1f", v_["mass_g"]) for v_ in TLP.values()),
                 note=pf("악기당; 합계 %.0f g, 약 %.0f시간", (_tg, sum(v_["time_min"] for v_ in TLP.values()) / 60))
                 + (pf(" (parts_list.json은 아직 r4.3 추정 %d개 × %.0f g)", (PLJ_TOOL["total"], PLJ_TOOL["unit_g"])) if PL_STALE and PL_STALE[-1].startswith("‘출력 공구’") else ""))
    w(pf("| %s | %s | %s | %s | %s | %s | %s |", tuple(esc(x) for x in (p["name"], p["kind"], p["spec"], p["per_module"], p["total"], p["unit_g"], p["note"]))))
w()
w(pf("모듈 출력 %.0f g + 서포트 %.0f g, 모듈 무게 %.2f kg. 88건반 본체 약 %.1f kg(v3 4.5 kg, r3 %.1f kg). 강철 블록 90개 %.2f kg, 봉 %.2f kg.", (MA["module_print_g"], MA["supports_module_g"], M["module_mass_kg"], TO["body_kg"], R3["totals"]["body_kg"], TO["steel_kg_88"], TO["rods_kg"])))
w()

# ============================================================================================ 5
w("## 5. 치수표 (geometry.json `dims`와 같은 번호)")
w()
_geo_rule = DIMS["P14"]["value"] == "; ".join(pf("%s %.2f/%.2f", (k_, v_[0], v_[1])) for k_, v_ in R["layout"]["collars"].items())
_noise = [(d_["id"], m_.group(1)) for d_ in G["dims"] for f_ in ("item", "value", "unit", "ref", "note") for m_ in re.finditer(r"(?<![\d.])(\d+\.\d{7,})", str(d_[f_]))]
_c02 = [c_ for c_ in R["checks"] if c_["check"].startswith("패드 쐐기·패드 ↔ 윗판 계단·레일")][0]["value"]
w("**반올림 (r4.4, 한 규칙)**: 이 문서의 모든 표·글과 geometry.json의 치수는 보인 자리에서 반올림한다. 딱 절반이면 0에서 먼 쪽으로 올린다(0.955 → 0.96, 13.525 → 13.53, −0.955 → −0.96). "
  "도우미는 하나다. `export_geo.hu`가 Decimal로 먼저 소수 6자리에서 이진 오차를 없애고 이 규칙으로 자른다. `export_geo.pf`는 모든 `%.Nf` 서식의 숫자를 `hu`로 거친다(이 판부터 `%s`로 찍는 목록 안의 실수도 소수 6자리로 줄임). "
  "`make_design_md.py`와 `export_geo.py`의 모든 숫자 서식이 이 둘을 쓴다. metrics.json은 소수 6자리로 저장된다(`run_all.py`의 `clean`, r4.4 고침 2). 그래서 이 문서가 저장값에서 찍은 숫자와 모델 참값 사이에 끝자리 차이가 없다.")
w()
w(pf("**규칙 밖에 남은 글**: `run_all.py`가 직접 쓰는 글(results.txt, metrics.json `checks`의 결과 글, parts_list.json 사양 글 대부분)은 아직 옛 `%%` 서식이다. 참값이 딱 절반이면 끝자리가 1 작게 보일 수 있다. 이 판에서 그런 곳은 둘이다. "
     "(1) 0.2장 ‘패드 쐐기·패드’ 행: run_all 글은 ‘%s’이고, 이 문서는 저장값 %.3f를 규칙대로 다시 썼다(%.2f). (2) 건반 뺀 레버가 떨어지는 각: 0.25° 격자라 참값이 딱 절반이다. results.txt는 30.2° · 13.2°, 이 문서는 30.3° · 13.3°다. "
     "부품표의 칼라 길이 글은 r4.4 고침 2부터 `export_geo.pf`로 써서 이 문서와 같다.", (_c02, R["r42"]["gaps_module"]["pad wedge"][0], R["r42"]["gaps_module"]["pad wedge"][0]))
  + (pf(" geometry.json `dims`의 %s 비고에는 목록을 옛 방식으로 찍은 이진 값(%s)이 남아 있다. 아래 표에서는 소수 6자리로 줄여 보인다(%s). 다음 `run_all.py`에서 새 `pf`로 없어진다.",
        ("·".join(sorted(set(i_ for i_, _ in _noise))), ", ".join(v_ for _, v_ in _noise), ", ".join(repr(hu(float(v_), 6)) for _, v_ in _noise))) if _noise else ""))
w()
# r4.4 doc retry 2: the cells this rule changes FOR THE CURRENT MODEL (work_doc44/r3: dims_cmp.py rebuilds the dims table from the model and
# compares it in the r4.3 format; run_md_old.py renders this document in the r4.3 format; build_round_cells.py pairs the numbers)
_rcp = os.path.join(OUT, "work_doc44", "r3", "round_cells.json")
if os.path.exists(_rcp):
    _rc = json.load(open(_rcp, encoding="utf-8"))
    w(pf("**이 규칙으로 바뀐 칸 (지금 모델, 옛 `%%` 서식 → 규칙; 모델 수치는 같음)**: geometry.json 치수 %d칸 — %s. 이 문서의 글 %d칸 — %s. "
         "기록은 `work_doc44/r3/round_cells.json`이다. 치수는 지금 모델에서 치수표를 다시 만들어 옛 서식과 비교했다(`dims_cmp.py`). 글은 이 문서를 옛 서식으로 다시 그려 비교했다(`run_md_old.py`). "
         "r4.4 고침 2 전의 목록(`work_doc44/round_cells.json`)과 다른 것은 모델 값이 바뀌었기 때문이다(칼라 0.76 이상, 쐐기 +0.04, metrics 6자리).",
         (len(_rc["dims"]), "; ".join(pf("%s %s → %s", tuple(c_)) for c_ in _rc["dims_grouped"]),
          len(_rc["doc"]), "; ".join(pf("%s %s → %s", tuple(c_)) for c_ in _rc["doc_grouped"]))))
    w()
_dn = lambda x_: re.sub(r"(?<![\d.])(\d+\.\d{7,})", lambda m_: repr(hu(float(m_.group(1)), 6)), str(x_))
for grp, title in (("P", "평면 P"), ("K", "건반별 평면 K"), ("S", "측면 S"), ("D", "상세 D"), ("A", "배치 A")):
    w("### " + title)
    w()
    w("| 번호 | 항목 | 값 | 단위 | 기준 | 비고 |")
    w("|---|---|---|---|---|---|")
    for d_ in G["dims"]:
        if d_["group"] == grp:
            w(pf("| %s | %s | %s | %s | %s | %s |", tuple(esc(_dn(x)) for x in (d_["id"], d_["item"], d_["value"], d_["unit"], d_["ref"], d_["note"]))))
    w()
# r4.4 doc: dims text written before the r4.4 tools / parts list (export_geo.py text, not changed here) - say which cell is older
_old = []
if "2.5 단" in DIMS["S08"]["note"]:
    _old.append("S08 비고의 ‘벤치 게이지(높이 2.5 단)’ → r4.4는 캡스턴 벤치 게이지 = 가짜 레버 T2(바늘 ↔ 읽기 턱)로 맞춘다(10.1장)")
if "레버 2" in DIMS["A08"]["note"]:
    _old.append("A08 비고의 ‘레버 2 · 패드 바 1’ → 부품표대로 레버·패드 바는 예비를 두지 않는다(13장)")
if "60 g" in DIMS["D11"]["note"] + str(DIMS["D11"]["value"]) + DIMS["D11"]["ref"]:
    _old.append("D11의 ‘60 g 추 낙하’ 패드 반발 측정 → 17장·17.1장의 C01 진자대(모델 `pad_e` 정의)가 기준")
if _old:
    w("**치수 글 가운데 r4.4 공구·부품표보다 오래된 것** (geometry.json 글, `export_geo.py`에서 고칠 것): " + "; ".join(_old) + ".")
    w()
w("### 주요 점 좌표 (y, z): 쉼 → 바닥(강체) → 1 N 정착 바닥(패드 있음) → ff 최대")
w()
for k, v in G["key_points"].items():
    w(pf("**%s** (a_dip %.2f°, b_dip %.2f°; 패드 면 기울기 %.2f°, 틈 %+.2f)", (k, v["a_dip"] * 57.29578, v["b_dip"] * 57.29578, v["pad_face"]["tilt_deg"], v["pad_face"]["gap"])))
    w()
    w("| 점 | 쉼 | 바닥(강체) | 1 N 정착 바닥 | ff 최대 |")
    w("|---|---|---|---|---|")
    for p in v["points"]:
        w(pf("| %s | %s | %s | %s | %s |", (p["point"], tuple(p["rest"]), tuple(p["dip_rigid"]), tuple(p["bottom_held_1N"]), tuple(p["ff"]))))
    w()

# ============================================================================================ 6
w("## 6. 힘·관성·복귀")
w()
w("| 항목 | 백 (D) | 흑 (C#) |")
w("|---|---|---|")
w(pf("| 캡스턴 y | %.2f | %.2f |", (W["y_cap"], B["y_cap"])))
w(pf("| 건반 / 레버 질량 | %.2f / %.2f g (강철 %.2f) | %.2f / %.2f g |", (W["key_g"], W["lever_g"], W["steel_g"], B["key_g"], B["lever_g"])))
w(pf("| BW / DW / UW | %.1f / %.1f / %.1f g | %.1f / %.1f / %.1f g |", (W["BW"], W["DW"], W["UW"], B["BW"], B["DW"], B["UW"])))
w(pf("| 마찰 (건반 봉 + 레버 봉 + 캡스턴 + 가이드) | %.2f = %.2f + %.2f + %.2f + %.2f g | %.2f = %.2f + %.2f + %.2f + %.2f g |", (W["friction"], W["fr"]["key_rod"], W["fr"]["lever_rod"], W["fr"]["capstan"], W["fr"]["guide"], B["friction"], B["fr"]["key_rod"], B["fr"]["lever_rod"], B["fr"]["capstan"], B["fr"]["guide"])))
w(pf("| 스프링 몫 (DW에서) | %.1f g (스프링 없으면 DW %.1f) | %.1f g (%.1f) |", (W["DW"] - W["DW_nospring"], W["DW_nospring"], B["DW"] - B["DW_nospring"], B["DW_nospring"])))
w(pf("| 스프링 토크 쉼 / 바닥 | %.2f / %.2f N·mm | %.2f / %.2f N·mm |", (W["spring_T_rest"], W["spring_T_bottom"], B["spring_T_rest"], B["spring_T_bottom"])))
w(pf("| 행정 따라 DW (0 / 25 / 50 / 75 / 100 %%) | %s | %s |", (" / ".join(f1(c[2]) for c in W["curve"]), " / ".join(f1(c[2]) for c in B["curve"]))))
w(pf("| 행정 따라 UW | %s | %s |", (" / ".join(f1(c[3]) for c in W["curve"]), " / ".join(f1(c[3]) for c in B["curve"]))))
w(pf("| 마찰 2배 DW / 바닥 UW | %.1f / %.1f g | %.1f / %.1f g |", (W["DW_2f"], W["UW_bottom_2f"], B["DW_2f"], B["UW_bottom_2f"])))
w(pf("| m_eff (건반 + 레버) | %.1f (%.1f + %.1f) g | %.1f (%.1f + %.1f) g |", (W["meff"], W["meff_key"], W["meff_lev"], B["meff"], B["meff_key"], B["meff_lev"])))
w(pf("| t50 / 끝까지 (1.2 s 정착 1 N에서 뗌) | %.1f / %.1f ms → %.1f Hz | %.1f / %.1f ms → %.1f Hz |", (dw["t50"], dw["t100"], dw["rep"], db["t50"], db["t100"], db["rep"])))
w(pf("| 마찰 2배 | %.1f / %.1f ms → %.1f Hz | %.1f / %.1f ms → %.1f Hz |", (dw["t50_2f"], dw["t100_2f"], dw["rep_2f"], db["t50_2f"], db["t100_2f"], db["rep_2f"])))
w()
w(pf("백 립(y0) DW %.1f g, y90 DW %.1f g → 앞/뒤 비 %.2f. 비틀림 스프링(r4.5 미스미 %s, r4.5 고침: 짧은 다리 %.1f를 가둠 홈에): 코일 몸통 강성 %.2f N·mm/rad(자른 다리 포함 %.3f), C %.1f, 바닥에서 안지름 %.2f — 코일은 가둔 다리에 매달려 봉과 쉼 %.2f · 바닥 %.2f 떨어짐(봉 마찰 없음).", (W["DW_lip"], W["DW_y90"], M["front_back_ratio"], PR["spring_cat"]["part"], PR["spring_short_leg"], SP["k_coil"], PR["spring_kt"], SP["C"], SP["ID_bottom"], SP["capture"]["gap_rest"], SP["capture"]["gap_bottom"])))
w()

# ============================================================================================ 7
w("## 7. 4-DOF 타건 시뮬레이션")
w()
w(pf("모델: 건반 = 봉 위의 자유 평면 강체(스냅 노치·입술 마찰·키퍼), 레버 = 봉 위 1자유도 + 비틀림 스프링, 패드 = 강철 윗면과 평행한 폼 층(기울기 %.1f°)을 패드 자리 스프링(%.0f N/mm = 모듈에서 가장 무른 %s 자리)과 직렬로. "
  "모든 PLAY·ABUSE 경우의 패드 자리는 가장 무른 건반 값이다(보수적).", (H["held_b_w"], SEAT["k_min"], kmin_key)))
w()
w("### 7.1 PLAY / ABUSE (설계 재료)")
w()
w("| 경우 | 앞끝 m/s | 노치 들림 (백 / 흑) | 키퍼 틈 | 패드 힘 N | 캡스턴 N | 레버 봉 N | 자석 오름 |")
w("|---|---|---|---|---|---|---|---|")
for k in [k_ for k_ in dw if isinstance(dw[k_], dict) and "lift_max" in dw[k_] and k_ != "release_f2"]:
    a_, b_ = dw[k], db[k]
    w(pf("| %s | %s | %.3f / %.3f | %.2f / %.2f | %.0f / %.0f | %.1f / %.1f | %.0f / %.0f | %s / %s |", (casek(k), pf("%.2f", a_["v_front_bottom"]) if a_["v_front_bottom"] else "-", a_["lift_max"], b_["lift_max"], a_["keep_gap_min"], b_["keep_gap_min"],
         a_["up_peak"], b_["up_peak"], a_["cap_peak"], b_["cap_peak"], a_["RL_peak"], b_["RL_peak"], pct(a_["ghost_frac"]), pct(b_["ghost_frac"]))))
w()
w("### 7.2 재료·자리·수치 민감도 (PLAY 1.5, ABUSE 2.5 m/s)")
w()
w("| 조합 | PLAY 들림 (백 / 흑) | 키퍼 | 패드 N | 유령 0.45 N | ABUSE 들림 | 연타 Hz |")
w("|---|---|---|---|---|---|---|")
for lab, row in SE.items():
    a_, b_ = row["white"], row["black"]
    w(pf("| %s | %.3f / %.3f | %.2f / %.2f | %.0f / %.0f | %s / %s | %s / %s | %s / %s |", (lab, a_["lift_play"], b_["lift_play"], a_["keep_play"], b_["keep_play"], a_["up_play"], b_["up_play"],
         "-" if a_["ghost045"] is None else pct(a_["ghost045"]), "-" if b_["ghost045"] is None else pct(b_["ghost045"]),
         "-" if a_["lift_abuse"] is None else f3(a_["lift_abuse"]), "-" if b_["lift_abuse"] is None else f3(b_["lift_abuse"]),
         "-" if a_["rep"] is None else f1(a_["rep"]), "-" if b_["rep"] is None else f1(b_["rep"]))))
w()
w(pf("‘합격선’ 조합(패드 e 0.07, 폼 E 0.7 MPa, 앞 펠트 e 0.22)까지는 PLAY 들림 %.3f ≤ 0.20, 키퍼 %.2f > 0(접촉 법칙 하한 공칭 0.02). 모델 하한 v_floor 0.1은 재료가 아니라 모델 불확실성이라 따로 적는다: "
  "혼자 %.3f, 합격선 재료와 묶어 %.3f / %.3f(검증자 물리 m1의 묶은 조합; r4.0 자리 830에서는 0.205였고 r4.1 자리 %.0f에서 0.20 아래). 합격선 밖 최악(패드 e 0.10, E 0.7, 앞 펠트 e 0.28, v_floor 0.1)은 들림 %.3f, 키퍼 %.2f — 단계 0에서 걸러야 할 재료다. "
  "패드 e 0.15 / 0.25(단계 0 시험 1의 대안 판단용): 백 들림 %.3f / %.3f, 흑 ABUSE 들림 %.3f / %.3f, 백 ABUSE 키퍼 %.2f / %.2f.", (M["key_lift_play_sets_mm"], M["keeper_gap_sets_mm"], SE["v_floor 0.1"]["white"]["lift_play"], SE["pass lines + v_floor 0.1"]["white"]["lift_play"], SE["pass lines + v_floor 0.1"]["black"]["lift_play"], SEAT["k_min"],
     M["key_lift_play_worst_mm"], M["keeper_gap_worst_mm"], SE["pad e 0.15"]["white"]["lift_play"], SE["pad e 0.25"]["white"]["lift_play"], SE["pad e 0.15"]["black"]["lift_abuse"], SE["pad e 0.25"]["black"]["lift_abuse"],
     SE["pad e 0.15"]["white"]["keep_abuse"], SE["pad e 0.25"]["white"]["keep_abuse"])))
w()
w(pf("PLAY 속도 격자(한 건반, 자리 %.0f N/mm, 공칭 / 최악 재료):", SEAT["k_min"]))
w()
w("| 앞끝 m/s, 누름 | 백 들림 / 키퍼 / 자석 (공칭) | 흑 (공칭) | 백 (최악) | 흑 (최악) |")
w("|---|---|---|---|---|")
SGR = R41["single_grid"]
for k_ in SGR["white_nom"]:
    q_ = [SGR[c_].get(k_) for c_ in ("white_nom", "black_nom", "white_worst", "black_worst")]
    w(pf("| %s | %s |", (k_.replace("_rel", ", 뗌").replace("_h", ", ") + ("" if k_.endswith("rel") else " N"),
                       " | ".join((pf("%.3f / %.2f / %s", (v["lift_max"], v["keep_gap_min"], pct(v["ghost_frac"])))) if v else "-" for v in q_))))
w()
w(pf("끝 건반(자기 캡스턴·자기 정착 바닥·자기 패드 쐐기, 자리 %s N/mm):", ", ".join(pf("%s %.0f", (n_, R41["seat_end"][n_])) for n_ in ("A0", "C8"))))
w()
w("| 건반 | 재료 | 1.5 m/s 뗌 들림 / 키퍼 | 0.45 N 자석 | 1.0 N 자석 | 2.5 m/s 들림 | 연타 Hz (마찰 2배) | 끝까지 ms |")
w("|---|---|---|---|---|---|---|---|")
for n_ in ("A0", "C8"):
    for mat_ in ("nom", "worst"):
        q_ = ED[n_][mat_]
        w(pf("| %s | %s | %.3f / %.2f | %s | %s | %.3f | %.1f (%.1f) | %.1f |", (n_, "공칭" if mat_ == "nom" else "최악", q_["1.5_rel"]["lift_max"], q_["1.5_rel"]["keep_gap_min"], pct(q_["1.5_h0.45"]["ghost_frac"]),
                                                                        pct(q_["1.5_h1.00"]["ghost_frac"]), q_[pf("%.1f_rel", PR["v_abuse"])]["lift_max"], q_["release"]["rep"], q_["release_f2"]["rep"], q_["release_f2"]["t100"])))
w()
w("### 7.3 6건반 동시 화음 (윗판이 함께 휨)")
w()
w(pf("윗판 FE에서 6건반이 한꺼번에 누르면 자리가 %.0f N/mm로 물러진다(한 건반일 때 최소 %.0f; 가장 무른 화음은 %s). r4.0은 기판 위 F|F# 핀이 매달려 있어 D#~G# 화음이 196~203 N/mm였고, 그 자리에 저장된 에너지가 레버로 돌아와 "
  "1.2~1.4 m/s 화음에서 들림이 0.216~0.238까지 올랐다(검증자 물리 M2, 이 모델로 재현). r4.1은 그 핀을 만능기판 앞쪽 홈으로 바닥에 닿게 했다. 화음 자리를 1.0~1.5 m/s, 0.05 간격으로 훑은 들림(뗌):", (CD["k"], SEAT["k_min"], "-".join(PL["play"]["chord"].get("k_eq_keys", [])))))
w()
w("| 재료 | 백 최대 들림 (그때 속도) / 키퍼 최소 | 흑 | 1.0 → 1.5 m/s 백 들림 |")
w("|---|---|---|---|")
for mat_, lab_ in (("nom", "공칭"), ("passline", "합격선"), ("vf01", "v_floor 0.1 (모델)"), ("pass_vf01", "합격선 + v_floor 0.1"), ("worst", "합격선 밖 최악")):
    w(pf("| %s | %.3f (%.2f) / %.2f | %.3f (%.2f) / %.2f | %s |", (lab_, cs_max("white", mat_), cs_arg("white", mat_), cs_keep("white", mat_), cs_max("black", mat_), cs_arg("black", mat_), cs_keep("black", mat_),
                                                             " ".join(pf("%.3f", q[1]) for q in CSW[pf("white_%s", mat_)][::2]))))
w()
w(pf("공칭·합격선 재료에서는 모든 속도에서 0.20 아래다. 모델 하한 v_floor 0.1(모델 불확실성)과 묶으면 1.45~1.5 m/s 화음에서 %.3f까지 오른다 — 0.20을 %.3f 넘어 입술이 잠깐 닿는 정도이고 ABUSE 한계 0.40과는 멀다. 이 모서리는 18장에 남긴다. "
  "아래는 화음 자리에서 누른 채 경우(PLAY 1.5 / 1.2 m/s, ABUSE 2.0 m/s):", (M["key_lift_chord_vf01_mm"], M["key_lift_chord_vf01_mm"] - PR["lift_play"])))
w()
w("| 누름 | 백 들림 / 키퍼 / 자석 / 내려옴 m/s | 흑 |")
w("|---|---|---|")
for k in CD["res"]["white"]:
    a_, b_ = CD["res"]["white"][k], CD["res"]["black"][k]
    w(pf("| PLAY 1.5, %s | %.3f / %.2f / %s / %.2f | %.3f / %.2f / %s / %.2f |", (k.replace("play_", ""), a_["lift_max"], a_["keep_gap_min"], pct(a_["ghost_frac"]), a_["ghost_v_desc"],
                                                                             b_["lift_max"], b_["keep_gap_min"], pct(b_["ghost_frac"]), b_["ghost_v_desc"])))
for k in CD["res_abuse"]["white"]:
    a_, b_ = CD["res_abuse"]["white"][k], CD["res_abuse"]["black"][k]
    w(pf("| ABUSE 2.0 (자리 %.0f), %s | %.3f / %.2f / %s / %.2f | %.3f / %.2f / %s / %.2f |", (CD["k_abuse"], k.replace("play_", ""), a_["lift_max"], a_["keep_gap_min"], pct(a_["ghost_frac"]), a_["ghost_v_desc"],
                                                                                           b_["lift_max"], b_["keep_gap_min"], pct(b_["ghost_frac"]), b_["ghost_v_desc"])))
w()
gdp = max([v["v_desc"] for k, v in gh.items() if v["armed"] and k.startswith(("chord_", "chord12_"))] + [0.0])
gda = max([v["v_desc"] for k, v in gh.items() if v["armed"] and k.startswith("chord20_")] + [0.0])
w(pf("화음 자리에서는 가벼운 누름의 건반이 기계적으로 재무장선을 넘는다. 이 유령들은 천천히 내려오므로(PLAY 1.5 m/s 화음 최대 %.2f m/s < 25 %% = %.3f; ABUSE 2.0 m/s 화음 최대 %.2f < 상한 %.2f) 거름 규칙이 버린다. "
  "0.5~1.5 m/s 전체 격자는 7.4. 진짜 음이 버려지는 경우는 ‘어떤 음(≥ %.1f m/s) 뒤 %.0f ms 안에 건반이 재무장하고, note-on부터 %.0f ms 안에 같은 건반을 앞 음의 1/4보다 느리게 다시 치는’ 때다(모든 세기).", (gdp, PR["ghost_ratio"] * PR["v_play"], gda, PR["ghost_v_desc"], PR["ghost_v_note"], PR["ghost_win"], PR["ghost_rep_max"])))
w()
w("### 7.4 유령 재타건과 펌웨어 거름")
w()
w(pf("재무장선 %.0f %%, 거름 문턱 %.1f m/s(r4.1). 창(r4.5 회로 2차, SCH-03 주 9와 같음): note-on부터 %.0f ms 안에 재무장 → note-on부터 %.0f ms 안에 닿는 첫 다시 눌림을 속도 비(%.0f %%, 최대 %.2f m/s)로 판정. "
     "계산한 %d경우(한 건반 0.5 / 1.0 / 1.5 m/s 공칭·최악 재료, 6건반 화음 자리 0.5~1.5 m/s, 끝 건반, 재료 조합) 중 기계적으로 재무장하는 것 %d건, 거름이 못 버리는 것 %d건. "
     "재무장한 경우는 note-on 뒤 %.1f s까지 이어 돌려 유령이 다시 닿는지 봤다(아래 표; 칸의 ‘내려옴’도 이 긴 계산의 값).", (100 * PR["rearm"], PR["ghost_v_note"], PR["ghost_win"], PR["ghost_rep_max"], 100 * PR["ghost_ratio"], PR["ghost_v_desc"],
                                                                                                   ghs["n"], len(ghs["armed"]), len(ghs["not_dropped"]), PR["ghost_long"] / 1000.0)))
w()
w(pf("6건반 화음 자리(%.0f N/mm) 유령 격자, 칸 = 자석 오름 %% / 내려옴 m/s (굵게 = 재무장 → 거름이 버림, ✗ = 못 버림). 1.15 m/s 아래는 손가락 1 N으로 쳐서 앞끝 속도를 맞췄다 "
  "(r4.0처럼 3 N으로 누르면 백은 0.99, 흑은 1.11 m/s 아래로 내려가지 않는다; 모든 격자 타건에서 목표와의 차 ≤ %.3f m/s):", (R41["k_ch"], R["r41_vf_err"])))
w()
for col_ in ("white", "black"):
    w(pf("**%s**", ("백 D" if col_ == "white" else "흑 C#")))
    w()
    w("| 앞끝 m/s | " + " | ".join(pf("%.2f N", h_) for h_ in (0.45, 0.5, 0.6, 0.8, 1.0, 2.0)) + " |")
    w("|---|" + "---|" * 6)
    for v_ in [hu(0.5 + 0.1 * i_, 1) for i_ in range(11)]:
        cells = []
        for h_ in (0.45, 0.5, 0.6, 0.8, 1.0, 2.0):
            q_ = gh.get(pf("gridc_%s_%.1f_h%.2f", (col_, v_, h_)))
            if q_ is None:
                cells.append("-")
                continue
            t_ = pf("%.0f / %.2f", (100 * q_["frac"], q_["v_desc"]))
            cells.append((pf("**%s**", t_) if q_["dropped"] else pf("**%s ✗**", t_)) if q_["armed"] else t_)
        w(pf("| %.1f | %s |", (v_, " | ".join(cells))))
    w()
w("그 밖의 재무장 경우:")
w()
w("| 경우 | 자석 오름 | 내려옴 m/s | 결과 |")
w("|---|---|---|---|")
for k, v in gh.items():
    if not k.startswith("gridc_") and (v["armed"] or v["frac"] >= 0.3):
        w(pf("| %s | %s | %.2f | %s |", (k, pct(v["frac"]), v["v_desc"], ("버림" if v["dropped"] else "**못 버림**") if v["armed"] else "재무장 안 함")))
w()
w(pf("**재무장 %d건의 긴 계산(r4.5 회로 2차, note-on 뒤 %.1f s까지)** — 재무장 = 자석이 50 %%를 넘은 시각, 흔들림 멈춤 = 자석이 10 ms에 행정의 1 %%보다 더 움직인 마지막 시각, 모두 note-on부터 ms:", (len(ghs["armed"]), PR["ghost_long"] / 1000.0)))
w()
w("| 경우 | 최대 오름 | 재무장 | 흔들림 멈춤 | 다시 닿음 | 끝 자석 위치 | 끝 기어내림 m/s (자석, − = 올라감) | 판정 |")
w("|---|---|---|---|---|---|---|---|")
for k in ghs["armed"]:
    v = gh[k]
    w(pf("| %s | %s | %.1f | %s | %s | %s | %.5f | %s |", (esc(k), pct(v["frac"]), v["t_arm"] or 0.0, (pf("%.0f", v["settle"]) if v["settle"] is not None else "-"),
                                                     (pf("%.0f ms", v["reland"]) if v["reland"] is not None else pf("없음 (%.0f ms까지)", v["t_run"])), pct(v["frac_end"] or 0.0), (v["creep"] if abs(v["creep"] or 0.0) >= 5e-6 else 0.0),
                                                     ("유령 안 옴" if v["reland"] is None else ("버림" if v["dropped"] else "**못 버림**")))))
w()
w(pf("**다시 눌림 시각 상한.** 모델에서 재무장한 유령은 스스로 다시 닿지 않는다(%d / %d, %.1f s까지): 0.45~0.50 N 손가락은 UW(%.1f / %.1f g ≈ %.2f / %.2f N)와 DW 사이 마찰 띠 안이라 건반을 뜬 자리(자석 %.0f~%.0f %%)에 붙잡는다. 흔들림은 %.0f ms 안에 멈추고(재무장은 %.1f ms 안), 그 뒤 움직임은 모델 마찰 정칙화(0.2 mm/s 아래 비례)의 기어내림 ≤ %.4f m/s(자석)뿐이다%s. "
     "그래서 창의 상한은 기구가 아니라 손가락이 정한다 — 펌웨어 상수 **%.0f ms(note-on부터)** = 흔들림이 멈추는 가장 늦은 시각의 약 2배. 단계 0 시험 11에서 펌웨어가 의심 상태의 다시 눌림 시각을 기록해, 유령(원치 않은 다시 눌림)이 %.0f ms를 넘으면 창을 (가장 늦은 것 + 100 ms)로 늘린다(대가: 그만큼 느린 진짜 재타건이 더 버려짐). "
     "창이 지난 뒤 기어내려 닿는 건반이 음을 내지 않게 하려면(선택, 펌웨어만) 두 문턱 사이 시간에 상한을 둔다: 자석 %.2f m/s(백 앞끝 약 %.2f m/s)보다 느린 눌림은 음 없음 — 모델 기어내림의 약 %.0f배, PLAY 격자에서 가장 느린 0.5 m/s 음(자석 %.2f m/s)의 1/%.0f.",
     (len(GSM["relanded"]), len(GSM["armed"]), PR["ghost_long"] / 1000.0, W["UW"], B["UW"], W["UW"] * 9.81e-3, B["UW"] * 9.81e-3, 100 * GSM["frac_end"][0], 100 * GSM["frac_end"][1], GSM["settle_max"], GSM["t_arm_max"], GSM["creep_max"],
      (pf(" — 그대로 가면 가장 빨라도 %.1f s 뒤 닿는다", GSM["land_est_min"] / 1000.0) if GSM["land_est_min"] else ""), PR["ghost_rep_max"], PR["ghost_rep_max"],
      0.01, 0.01 * 1.91, 0.01 / max(GSM["creep_max"], 1e-9), 0.5 / 1.91, (0.5 / 1.91) / 0.01)))
w()
w("### 7.5 운반 기울임과 스냅")
w()
w("| 자세 | 백 노치 들림 | 흑 | 눕힌 뒤 앞 높이 변화 |")
w("|---|---|---|---|")
for ang in (90, -90, -120, 180):
    a_ = R["tilt"][pf("white_%d_mu0.25", ang)]
    b_ = R["tilt"][pf("black_%d_mu0.25", ang)]
    w(pf("| %+d° | %.2f | %.2f | %+.3f / %+.3f |", (ang, a_["notch_lift"], b_["notch_lift"], a_["reseat_front_dz"], b_["reseat_front_dz"])))
w()
w(pf("정적으로는 뒤집혀도(180°) 들림 %.2f < 빠짐 %.2f. 입술 법칙의 빠짐 힘 1.99 N이면 뒤집힌 채 약 %.1f g 충격에서 백건이 빠질 수 있다 → 모듈은 바로 세우거나 뒤 모서리로 세워 옮긴다(RET-2 운반 규칙).", (R["tilt"]["white_180_mu0.25"]["notch_lift"], PR["lift_popout"], R["snap"]["shock_g_upside"])))
w()

# ============================================================================================ 8
w("## 8. 강도·하중")
w()
w(pf("### 8.1 윗판과 핀 (그릴리지 FE, 1 mm 격자; 기판 위 F·F# 사이 핀은 y%.1f~%.1f에서 기판 홈을 지나 z%.0f까지 깊은 보이고 킬(y%.1f~%.1f, z%.0f~%.1f)로 밸런스 레일 뒷면에 붙음 — r4.4 고침 2b, 바닥이 뚫림; r4.5 고침: 킬 뿌리는 레일 + 바닥 띠 보(핀 선 연속, EVA 없음), 핀 앞끝 y152 → y%.1f; 그 뒤는 뒷벽까지 깊은 보 — r4.3: USB 터널 위도 매달림)",
     (KRL["fin_front"], PR["fin_slot_y"][1], P4["z_floor"][0], P4["fin_keel"][0], KRL["fin_front"], P4["fin_keel"][1], P4["fin_keel"][2], KRL["fin_front"])))
w()
w("건반마다 패드 자리 강성(100 N): " + ", ".join(pf("%s %.0f", kv) for kv in SEAT["k_keys"].items()) + " N/mm.")
w()
w("| 하중 | 경우 | 패드 힘 합 N | 윗판 (층 안) MPa | 핀 윗 이음 (층간) MPa | 뒷벽 N/mm | 자리 처짐 최대 mm |")
w("|---|---|---|---|---|---|---|")
for lab, labk in (("play", "PLAY 1.5"), ("abuse_chord20", "ABUSE 2.0"), ("abuse", "ABUSE 2.5")):
    for kind, q in PL[lab].items():
        w(pf("| %s | %s | %.0f | %.1f | %.1f | %.2f | %.2f |", (labk, "한 건반" if kind == "single" else "6건반 동시", q["total"], q["sigma"], q["fin_top"], q["wall_q"], q["seat_max"])))
w()
w(pf("패드 힘(실제 수직력): PLAY %.0f / %.0f N, 2.0 m/s %.0f / %.0f N, ABUSE %.0f / %.0f N (r3는 손가락 시작 1.5 m/s에서 138 / 159 N). 패드 밑 지압 %.2f MPa, 폼 최대 압축 %.0f %% / %.0f %%(치밀화 80 %%).", tuple(list(play_up) + list(ch_up) + list(ab_up) + [ST["pad_bearing"], 100 * H["pad_comp_ratio_w"], 100 * H["pad_comp_ratio_b"]])))
w()
w("### 8.2 레버 봉·핀 보스")
w()
w("| 하중 | 봉 반력 (백 / 흑) | 6건반 굽힘 | 처짐 | 핀 반력 → 보스 지압 | 한 건반 최악 |")
w("|---|---|---|---|---|---|")
for lab, q in LR.items():
    lab = {"play": "PLAY 1.5", "chord20": "2.0 m/s 화음", "abuse": "ABUSE 2.5"}[lab]
    w(pf("| %s | %.0f / %.0f N | %.0f MPa | %.3f | %.0f N → %.1f MPa | %.0f MPa |", (lab, q["RL"][0], q["RL"][1], q["chord"]["sigma"], q["chord"]["defl"], q["chord"]["fin_R"], q["chord"]["boss_bearing"], q["single"]["sigma"])))
w()
w(pf("r4.5 고침 가둠 홈 자리의 허브·웹(1f-2장): ABUSE 층 안 %.2f MPa(홈 모서리 Kt 2 포함; 홈이 없던 r4.4 단면 %.2f), 전단 %.2f; PLAY %.2f; 짧은 다리의 두 닿는 점은 모두 웹 쪽 조각 A(층 안), 손 25°에서 %.2f N씩(d × d에 %.1f MPa); 아래 고리 조각 B는 다리 힘을 받지 않음; 봉은 양옆 온전한 허브에만 기대어 ABUSE 지압 %.2f MPa.",
     (R["r45"]["hub"]["abuse"]["section"]["sigma_kt"], R["r45"]["hub"]["abuse"]["section"]["sigma_full"], R["r45"]["hub"]["abuse"]["section"]["tau"], R["r45"]["hub"]["play"]["section"]["sigma_kt"],
      R["r45"]["hub"]["abuse"]["F_couple"], R["r45"]["hub"]["abuse"]["contact_p"], R["r45"]["hub"]["abuse"]["hub_bearing"])))
w()
w("### 8.3 건반과 상시 응력")
w()
rs = ST["rest"]
w(pf("- 숨은 빔: PLAY %.1f MPa(캡스턴 %.1f N), ABUSE %.1f MPa. 얇은 꼬리: 백 %.1f / 흑 %.1f MPa(층 안, 매 음). USB 홈 옆 선반(F·F# 쉼 펠트 착지, r4.3) %.1f MPa.", (ST["beam_peak"], ST["cap_peak"], ST["beam_abuse"], ST["tail"]["white"]["s_play"], ST["tail"]["black"]["s_play"], ST["shelf_usb"])))
w(pf("- 쉼 상시: 꼬리 %.2f / %.2f, 빔 %.2f, 노치 단면 %.2f MPa, 스프링 다리 홈 %.2f MPa → 최대 %.2f MPa.", (rs["white"]["tail"], rs["black"]["tail"], rs["white"]["beam"], rs["white"]["notch_section"], rs["spring_leg"]["groove_p"], rs["max"])))
w("- 건반 굴림(되돌리는 / 넘기는 모멘트): " + ", ".join(pf("%s %.1f/%.1f", (k, v["ratio_rest"], v["ratio_stroke"])) for k, v in ST["roll"].items()) + ".")
w()

# ============================================================================================ 9
w("## 9. 틈 (±0.3 공차, 공칭 1.3 이상)")
w()
w(pf("모듈 스윕 %d쌍, 1.3 미만 %d. 최소 %.2f(공차 뒤 %.2f).", (CL["n_pairs"], CL["n_bad"], CL["min"], CL["min_after_tol"])))
w()
w("| 짝 | 최소 | 공차 뒤 | 자세 |")
w("|---|---|---|---|")
for lab, q in NM.items():
    w(pf("| %s | %.2f | %.2f | %s [%s, %s] ↔ %s [%s %s] |", (lab, q["d"], q["after_tol"], tr(q["a"]), tr(q["part_a"]), POSE.get(q["pose_a"], q["pose_a"]), tr(q["b"]), tr(q["part_b"]), POSE.get(q["pose_b"], q["pose_b"]))))
w()
w(pf("설계 접촉·맞춤(따로 보고): 크로스바 ↔ 탭 뒤쪽 y 멈춤 %.2f, 흰 앞 펠트 ↔ 크로스바·리브 %.2f, 밸런스 핀 ↔ 입술 벽 %.2f / 홈 뒤끝 %.2f, 캐리어 옆벽 ↔ 패드(r4.1: 윗 립을 패드 옆에서 끊어 스윕에 넣음) %.2f, "
  "USB 플러그(r4.3 z%.1f~%.1f) ↔ 선반 홈·리브·핀·뒷벽 %.2f, 제어 기판 부품(BRD-01) ↔ 프레임 %.2f, 이웃 도브테일 홈 ↔ 끝 핀 %.2f.", (CL["crossbar_tab_min"], CL["fixed_fixed"]["felt_crossbar_min"], CL["pin_lip_wall"], CL["pin_slot"], CL["lip_pad"], PR["usb_z"][0], PR["usb_z"][1], CL["fixed_fixed"]["usb_plug_min"][0],
     min(v_[0] for v_ in R["r43"]["board_vs_frame"].values()), CL["fixed_fixed"]["dovetail_zone_vs_end_fin"][0])))
w()
for s in ("left", "right"):
    q = CL["end_parts"][s]
    w(pf("- 끝 부속 %s: %d쌍, 1.3 미만 %d, 최소 %.2f (%s); 볼과 %.2f; 이음매 너머 움직이는 부품 %.2f, 고정-고정 %.2f (%s), 도브테일 맞춤 %.2f.", ("왼쪽" if s == "left" else "오른쪽", q["n"], q["n_bad"], q["min"], tr(q["min_pair"]), q["cheek"], q["seam_moving"], q["seam_fixed"][0], tr(q["seam_fixed"][1]), q["seam_dovetail"][0])) + pf(" 이음 면(핀·윗판·가림판) %.2f = 모듈 이음과 같은 0.4 (0.2씩 들여 뜀).", q["seam_face"][0]))
w()

# ============================================================================================ 10
w("## 10. 조립 순서")
w()
w("r4.1(검증자 기하 M1): 윗판이 프레임과 한 몸이라 **레버를 건반보다 먼저** 넣는다. 건반을 먼저 넣으면 흑 레버가 자기 흑건 위를 지나갈 창이 13.3 mm뿐이라(레버 단면 ≥ 20) 못 들어간다. "
  "run_all의 레버 넣기 C-공간 검사(0.25 mm, 피치 −40~60°): 건반이 없으면 " + ", ".join(pf("%s %s", (n_, "도달" if q_["no_keys"]["ok"] else "막힘")) for n_, q_ in INS.items()) +
  "; 건반이 다 있으면 " + ", ".join(pf("%s %s", (n_, "도달" if q_["keys_first"]["ok"] else "막힘")) for n_, q_ in INS.items() if q_["keys_first"]) + ".")
w()
steps = [
    pf("**제어 기판 먼저 (r4.4 고침 2b)**: 리본(J301)·EXT 선을 납땜한 기판을 넣는다. 모듈을 뒤집어 놓고, 기판을 부품 쪽이 프레임 안을 보게 들어 홈을 F|F# 핀 발·킬에 맞춘 뒤 바닥 구멍(x%.2f~%.2f y%.1f~%.1f)으로 곧게 밀어 넣는다(길 위 최소 %.2f). "
       "기판이 매단 보스 4개에 닿고 위치 핀 2개가 구멍(반경 놀음 %.2f)에 들어가면 M3×6 2개를 밑에서 %s에 조인다(머리는 기판 밑, 육각 렌치 2.0). 리본은 밸런스 레일 밑 차선으로 센서 기판 쪽에 둔다. 다시 뒤집는다. "
       "**센서 바·기판(r4.5 회로 2차)**: 리본(J201)을 납땜한 센서 기판을 센서 바에 붙인 덩어리를 모듈 하나만 둔 채(왼쪽 이웃 없이) 1.5 mm 왼쪽에 내려놓아 기판을 기둥·리브에 얹고, 오른쪽으로 밀어 바 끝을 오른쪽 턱(P36, 립 밑면 z%.1f) 밑에 넣은 뒤 왼쪽 M3×10 자가 탭 2개를 조인다(v3 절차). 턱이 오른쪽 끝을 잡으므로 모듈을 뒤집어도 바가 나사에만 매달리지 않는다.",
       tuple(R["fix2b"]["hatch"]) + (R["board_insert"]["min"], R["board_insert"]["pin_play"], "·".join(pf("(%.1f, %.1f)", (q_["x"], q_["y"])) for q_ in R["c44"]["standoffs"] if q_["kind"] == "screw"), PR["sb_ledge"][3])),
    pf("벤치에서: 프레임에 밸런스 핀을 핀 높이 게이지(T3)로 압입하고(꼭대기 z%.2f) GO/NO-GO로 z%.2f~%.2f인지 본다(10.1장). 봉 받침에 건반 봉을 놓고 멈춤 기둥 사이에 둔다. 앞 펠트(y%.1f~%.1f)·흑 멈춤 펠트·키퍼 펠트를 붙인다. 가이드 탭에 천 0.5T(쿠폰으로 두께 확인).",
       ((PR["block_step_z"] + 1.0, PR["block_step_z"] + 1.0 - 0.1, PR["block_step_z"] + 1.0 + 0.1) + tuple(PR["w_felt_y"]))),
    pf("벤치 지그(T1)와 가짜 레버(T2)로 건반마다 맞춘다(10.1장): 가짜 레버를 캡스턴에 얹어 실제 쉼 하중(캡스턴 힘 백 %.2f / 흑 %.2f N)을 준 채, 먼저 높이 블록으로 앞 높이를 창 ±0.15 안에 쉼 펀칭으로 맞추고(한 장 = 앞 %.2f), "
       "그다음 캡스턴을 바늘 ↔ 읽기 턱으로 맞춘다(1/8회전 = 바늘 %.2f / %.2f mm, 육각 렌치 2.0). 쉼 선반은 z%.3f. 건반은 아직 프레임에 넣지 않는다.",
       (TDL["per_colour"]["white"]["F_cap"], TDL["per_colour"]["black"]["F_cap"], AD["levelling_front_per_punching"], TDL["per_colour"]["white"]["per8"], TDL["per_colour"]["black"]["per8"], H["z_shelf"])),
    pf("레버마다(위치 이름이 새겨진 캐리어): **강철 접착(r4.4 고침 2b)** — 강철 9×19×40(두께 %.1f~%.1f인지 캘리퍼스로)의 두 19×40 옆면과 캐리어 옆벽 안쪽을 #120 사포 → 알코올, 강철 두 옆면에 MS 폴리머를 얇게(블록당 약 0.2 mL) 펴 바르고 밑에서 끼운다(스냅: 아래 립이 걸림, 접착층 한쪽 %.2f). 윗 립·아래 립·펠트 자리로 나온 것은 바로 닦고 24시간 굳힌다. 그다음 펠트 띠 2T(흑연)를 붙인다. **스프링(r4.5)**: 미스미 %s의 두 암을 경선 니퍼로 잘라(긴 다리 코일 중심에서 끝까지 %.1f = 코일을 떠나는 점에서 %.2f, 짧은 다리 %.1f, 굽히지 않음; 끝 거스러미는 줄로) **긴 다리가 코일의 +x(오른쪽) 끝**에 오게 들고(r4.5 고침) 짧은 다리 끝을 가둠 홈(폭 %.2f, 레버 기준 %.0f° 방향) 입구에 대어 홈을 따라 끝까지 밀어 넣는다 — 코일은 넣는 슬롯(%.0f°)으로 주머니에 들어가 앉는다(뒤집으면 짧은 다리가 홈에 맞지 않음). 0.5 선이 안 들어가면 홈을 0.5 날로 다듬는다. 넣는 슬롯이 뒤·아래로 열려 있어 코일이 제 무게로 다시 미끄러져 나올 수 있으므로, 봉을 꿸 때까지 이쑤시개(Ø2)를 허브 구멍과 코일에 꽂아 두고 봉이 그 레버에 오기 직전에 뽑는다. 긴 다리는 창 밖으로 자유 상태.", (P4["steel_w"] - 0.1, P4["steel_w"] + 0.1, P4["bond_t"], PR["spring_cat"]["part"], PR["spring_leg"], SP45["l_long"], PR["spring_short_leg"], NT45["width"], NT45["band_deg"], NT45["slot_deg"])),
    pf("**건반이 없는 프레임**에 레버를 앞에서 하나씩 밀어 넣어 허브를 레버 봉 선(L)에 맞춘다. 레버 앞은 바닥판(C·C#·D·A·A#·B, %.2f°)이나 기판 쪽(E·F 4067 모듈 %.2f°, D#·G# 기판 위 매단 보스 %.2f°, F#·G 기판 윗면 %.2f / %.2f°)에 놓인다. 긴 다리가 뒷벽을 먼저 치면 손가락으로 감아 누른 채 넣는다.",
       (-LD["C"]["drop_deg"], -LD["E"]["drop_deg"], -LD["D#"]["drop_deg"], -LD["F#"]["drop_deg"], -LD["G"]["drop_deg"])),
    pf("Ø4 레버 봉을 왼쪽 끝 핀부터 핀 보스·허브(칼라끼리 맞닿음)·스프링 코일에 손으로 허브를 맞추며 꿴다. 왼쪽 마개(출력)를 넣는다. 레버마다 제 무게로 자유롭게 도는지 본다(아니면 칼라 면 사포질; 칸마다 축 놀음 %s).", " / ".join(pf("%.2f", q) for q in R["axial_play"])),
    pf("긴 다리를 뒷벽 보스의 홈(긴 다리 x %+.1f에 맞춤, 입구 %.1f×45°, r4.2: 보스 밑면에서 열려 다리가 밑에서 들어감)에 건다: 바닥판 위 레버(%.1f°)는 다리가 홈 입구 안 %.2f에 거의 풀린 채 놓이고, 기판 위 레버(D#~G#, %.1f~%.1f°)는 손가락으로 약 %.0f° 감아 입구에 대고 놓는다. 레버 위는 비어 있어 손이 들어간다.", (PR["spring_groove_dx"], PR["spring_lead_in"], LD["C"]["angle_deg"], LEG["C_+0"]["in_groove"], max(LD[k_]["angle_deg"] for k_ in ("D#", "E", "F", "F#", "G", "G#")), min(LD[k_]["angle_deg"] for k_ in ("D#", "E", "F", "F#", "G", "G#")), max(LD[k_]["angle_deg"] for k_ in ("D#", "E", "F", "F#", "G", "G#")) - PR["spring_free_deg"])),
    pf("**흑건 5개를 먼저**, 그다음 백건 7개를 넣는다: 건반마다 그 레버를 손톱 턱으로 %.1f°까지 들고, 11장 빼기 경로(검사함)의 반대로 — 비스듬히 밀어 넣고, 3 mm 뒤로 밀고, 블록을 핀 위에 내려 스냅(블록 위를 누름). 레버를 놓으면 캡스턴에 앉는다.", R["params"]["BH"]),
    pf("패드(폼 6T + 펠트 1T, 6×%.1f)를 패드 바 쐐기에 붙이고(바 6종, 손잡이 이름 확인), 패드 바를 L 레일에 **뒤 멈춤(y%.1f)까지** 밀어 넣는다: 가장자리 잎 혀의 돌기가 y%.1f부터 립에 올라탄다. 바가 위아래로 놀지 않는지(잎 예하중) 확인.", (R["pad_cut_len"], PR["plate_step_y"], PR["rail_lip_y0"])),
    "12장 종이 띠 기준으로 건반마다 바닥을 확인하고 필요하면 패드 밑 PET 심(0.1)으로 업스톱 시점을 맞춘다.",
    "가림판 띠를 윗판 앞 턱에 건다. 끝 부속(A0·A#0·B0, C8)도 같은 순서(A#0 레버 넣기 도달 확인됨).",
]
for i, s_ in enumerate(steps, 1):
    w(pf("%d. %s", (i, s_)))
w()
# ============================================================================================ 10.1 printed tools (r4.4, open issue 6)
w("### 10.1 출력 공구 — 벤치 지그 · 높이 블록 · 캡스턴 벤치 게이지(가짜 레버) · 밸런스 핀 높이 게이지 (r4.4)")
w()
_sv, _tw, _tb = TL["service"], TDL["per_colour"]["white"], TDL["per_colour"]["black"]
_mv = TL["model_values"]
_tg = sum(v_["mass_g"] for v_ in TLP.values())
_tt = sum(v_["time_min"] for v_ in TLP.values())
w(pf("`tools/make_tools.py`가 모델 값에서 만든다. 치수 T01~T29는 `tools/tools_geometry.json`, 설명과 옆모습 틈 표는 `tools/tools.md`, 출력 파일은 `tools/stl/`. 출력물 %d개, 합계 약 %.0f g, 약 %.0f시간. "
     "새로 살 것은 없다: 건반 봉과 같은 4 m 봉에서 자른 봉 토막 3개(K 31.6, L 20.6, 교정봉 31.6), 100개 묶음에서 남는 밸런스 핀 1개, 설치 전에 빌려 쓰는 레버 강철 블록 1개.", (len(TLP), _tg, _tt / 60)))
w()
w(pf("**왜 가짜 레버인가(가장 중요한 발견).** 건반은 앞이 무겁다(무게중심 y%.1f, 봉 y%.1f). 그래서 벤치에서는 무언가가 꼬리를 눌러야 쉼 선반에 앉는데, 그 힘에 따라 건반 높이가 달라진다. "
     "손가락으로 0.3~5 N을 누르면 백건 앞 높이가 %+.2f~%+.2f mm 달라진다. 펀칭 1장(%.2f)보다 크다. 그래서 r4.3 글의 ‘빔 윗면 위 2.5 단 게이지’ 대신 캡스턴 게이지를 **가짜 레버**로 만들었다. "
     "지그의 L 봉 토막에 끼워 실제 레버와 같은 모멘트(%.2f N·mm, 실제 %.2f)로 캡스턴을 누른다. 캡스턴 힘은 백 %.2f N(실제 %.2f), 흑 %.2f N(실제 %.2f)이고, 남는 앞 높이 차이는 %.3f / %.3f mm다.",
     (_sv["white"]["key_com"][0], _mv["K"][0], _tw["finger_03"], _tw["finger_5"], _mv["punch_front"], TDL["M_Nmm"], _sv["white"]["M"], _tw["F_cap"], _tw["F_service"], _tb["F_cap"], _tb["F_service"], _tw["front_err"], _tb["front_err"])))
w()
w(pf("**기준은 책상이 아니라 프레임 자리다.** 지그 밑면 = 프레임 밑면 z%.1f(출력 높이 = z − %.1f). K 봉 토막 구멍 중심 (%.1f, %.1f), 쉼 선반 윗면 z%.3f, L 봉 토막 (%.2f, %.1f). "
     "핀 게이지는 레일 윗면 z%.1f과 레일 앞면 y%.1f에 댄다. 교정용 영점 받침(교정봉 윗면 z%.1f = 캡스턴 꼭대기)이 지그와 가짜 레버를 한 번에 교정한다.",
     (_mv["z_datum"], _mv["z_datum"], _mv["K"][0], _mv["K"][1], _mv["z_shelf"], _mv["L"][0], _mv["L"][1], _mv["z_rail_low"], _mv["rail_front_y"], _mv["z_c"])))
w()
_TROW = [("bench_jig", "T1a", "벤치 지그 (받침)", "건반 1개를 모듈 프레임과 같은 자리에 올린다: K 봉 토막, 쉼 선반, 예비 밸런스 핀(x 위치), 가짜 레버용 L 봉 토막, 영점 받침, 읽기 턱 기둥, 주차 기둥. 모듈 건반 12개와 끝 A0·A#0·B0·C8에 모두 쓴다",
          ("T02", "T05", "T06", "T07", "T08", "T09")),
         ("height_block", "T1b", "높이 블록", "받침판(z5.0)에 세워 건반 머리 옆면에 붙이고 손톱으로 땅 높이와 비교한다. 높으면 펀칭 1장 더, 낮으면 1장 뺀다",
          ("T11", "T12", "T13", "T14", "T15")),
         ("capstan_gauge", "T2", "캡스턴 벤치 게이지 (가짜 레버)", "L 봉 토막에 끼워 실제 레버와 같은 모멘트로 캡스턴을 누른다. 캡스턴 꼭대기 z" + pf("%.2f", R["fix2b"]["crown_T2"]) + "(정착 쉼; 건반 좌표 z" + pf("%.1f", PR["z_c"]) + ")를 부리 끝 바늘로 확대해 읽는다. 캡스턴을 돌릴 때는 주차 기둥으로 젖혀 둔다",
          ("T17", "T18", "T22", "T23")),
         ("pin_gauge", "T3", "밸런스 핀 높이 게이지", "발은 레일 윗면, 울타리는 레일 앞면에 대고 핀을 멈춤 면까지 눌러 넣는다. 막대 끝으로 GO는 지나가고 NO-GO에서 멈추면 합격",
          ("T24", "T26", "T28", "T29"))]
w("| 공구 | 하는 일 | 주요 치수 (번호 = tools_geometry.json `dims`) | 출력 (PETG, 서포트 없음) | g | 분 |")
w("|---|---|---|---|---|---|")
for k_, id_, nm_, job_, ds_ in _TROW:
    q_ = TLP[k_]
    _dd = "; ".join(pf("%s %s %s", (d_, TLD[d_]["item"], TLD[d_]["value"])) for d_ in ds_)
    w(pf("| %s %s | %s | %s | %s; 층 %s; 채움 %.0f %%, 벽 %d; 크기 %s | %.1f | %.0f |",
         (id_, nm_, job_, esc(_dd), q_["orient"], q_["layer"], 100 * q_["infill"], q_["walls"], " × ".join(fz(v_, 1) for v_ in q_["bbox"]), q_["mass_g"], q_["time_min"])))
w()
w(pf("모두 256 × 256 베드에 들어간다(가장 큰 지그 %s × %s). 220 × 220 베드에서는 지그를 대각선으로 놓는다(45°에서 %.0f × %.0f).",
     (fz(TLP["bench_jig"]["bbox"][0], 1), fz(TLP["bench_jig"]["bbox"][1], 1), (TLP["bench_jig"]["bbox"][0] + TLP["bench_jig"]["bbox"][1]) * 0.70711, (TLP["bench_jig"]["bbox"][0] + TLP["bench_jig"]["bbox"][1]) * 0.70711)))
w()
w("**쓰는 법**")
w()
_pt = _mv["pin_top"]
_use = [
    "준비(한 번): 네 개를 출력한다(지그는 프레임과 같은 층 설정). Ø4.0 드릴로 지그 K·L 구멍과 가짜 레버 허브를 뚫는다. 봉 토막 3개를 자르고 끝을 다듬는다. 강철 블록 1개를 가짜 레버 주머니에 눌러 끼운다(스냅 립). "
    "예비 밸런스 핀 1개를 T3으로 지그 핀 구멍에 눌러 넣는다 — 이것이 T3의 첫 검증이다.",
    pf("교정(한 번): 건반이 없는 지그의 영점 받침(백 y%.2f, 흑 y%.2f) 홈에 교정봉을 놓고 가짜 레버를 내린다. 바늘 윗면과 읽기 턱이 손톱으로 같은 높이면 끝이다. 다르면 높은 쪽을 한 번 사포질한다. "
       "백·흑 두 자리의 차이가 흑 1/8회전(바늘 %.2f)보다 크면 가짜 레버 밑면을 평평하게 다듬는다.", (_mv["caps"]["white"], _mv["caps"]["black"], _tb["per8"])),
    pf("밸런스 핀(T3, 프레임마다, 모듈을 잇기 전, 조립 1단계): 왼쪽 핀부터. 핀을 구멍에 세우고 누름 구멍을 핀 위에, 울타리를 레일 앞면에 댄다. 발이 레일 윗면에 닿을 때까지 엄지나 바이스로 누른다(망치 금지: 멈춤 면이 파여 모든 핀이 낮아짐). "
       "**누른 핀은 바로, 오른쪽 이웃 핀을 꽂기 전에** 게이지를 +X로 옮겨 그 핀이 왼쪽 끝 |<GO로 들어오게 민다: GO는 지나가고 NO-GO에서 멈춰야 한다(꼭대기 z%.2f~%.2f). GO에서 막히면 다시 누르고, NO-GO를 지나가면 조금 뽑아 다시 누른다. "
       "핀을 다 누른 뒤에는 다른 핀이 게이지에 걸려 확인할 수 없다(r4.4 고침 2).", (_pt - 0.1, _pt + 0.1)),
    pf("건반마다(T1 + T2, 조립 2단계): 가짜 레버를 주차 기둥에 젖혀 두고 건반 노치를 K 봉 토막에 끼운다. 가짜 레버를 캡스턴에 내린다 — 손으로 건반을 누르지 않는다. "
       "**높이 먼저**: 높이 블록을 머리 옆면에 붙이고 손톱으로 +/− 땅을 본다(백 %.2f / %.2f, 흑 %.2f / %.2f). 높으면 펀칭 1장 더, 낮으면 1장 뺀다(한 장 = 앞 %.2f). "
       "**캡스턴 나중**: 바늘이 낮으면 캡스턴을 풀고, 높으면 조인다. 돌릴 때는 가짜 레버를 젖히고 육각 렌치를 위에서 넣는다. 1/8회전 = 바늘 %.2f(백) / %.2f(흑) mm(확대 %.2f / %.2f배).",
       (float(TLD["T11"]["value"]), float(TLD["T12"]["value"]), float(TLD["T13"]["value"]), float(TLD["T14"]["value"]), _mv["punch_front"], _tw["per8"], _tb["per8"], _tw["amp"], _tb["amp"])),
    "출력 검증: 지그는 캘리퍼로 밑면 → K 봉 토막 윗면 20.50, 쉼 선반 윗면 17.05, 영점 홈 바닥 24.00, 읽기 턱 62.50(각 ±0.05). 높이 블록 38.65 / 38.35 / 50.65 / 50.35(각 ±0.03). "
    "핀 게이지는 발 면 → 누름 구멍 바닥 4.30, GO 천장 4.40, NO-GO 천장 4.20(각 ±0.05).",
]
for i_, u_ in enumerate(_use, 1):
    w(pf("%d. %s", (i_, u_)))
w()
_kc = TL["checks"]["key_clearance_min"]
_kmin = min(v_["min"] for v_ in _kc.values())
_dcap = (W["y_cap"] - _mv["caps"]["white"], B["y_cap"] - _mv["caps"]["black"])
_roof = min(v_ for k_, v_ in TL["checks"]["pin_gauge_on_frame_D"].items() if "roof over the open channel" in k_)
_tlm = MODEL_TAG(TL["meta"]["model_dir"])
w(pf("**틈과 주의.** 모듈 건반 12개와 끝 부속 4개의 쉼 자세에서 지그·가짜 레버와 최소 %.2f(설계 접촉 제외). 핀 게이지를 프레임에 놓으면 이웃 핀과 %.1f, 봉 받침 능선과 %.2f(손 공구라 움직이는 부품 규칙 밖). "
     "지그 선반은 온전하므로 F·F#는 프레임에서 약 0.1 높게 쉰다 — 창 ±0.15 안이다. 지그는 프레임 한 대의 자리만 재현하므로 모든 프레임과 지그를 같은 프린터·같은 층 설정으로 뽑는다. ",
     (_kmin, _roof, TL["checks"]["pin_gauge_rear_face_to_cradle_ridge"]))
  + (pf("공구는 지금 모델(`%s`, %s, `tools_geometry.json` meta)로 만들었다. 영점 받침 자리 = 모델 캡스턴 y(백 %.2f, 흑 %.2f, 차이 %+.2f / %+.2f).", (_tlm, TL["meta"]["round"], W["y_cap"], B["y_cap"], _dcap[0], _dcap[1]))
     if _tlm == "final" else
     pf("공구는 `%s` 모델로 만들었다. 지금 모델과 캡스턴 y가 백 %+.2f, 흑 %+.2f 다르다(%.2f / %.2f). 영점 받침 홈(폭 4.6) 안이면 그대로 쓰고, `MODEL_DIR=final`로 다시 만들면 맞춰진다.", (_tlm, _dcap[0], _dcap[1], W["y_cap"], B["y_cap"]))))
w()

# ============================================================================================ 11
w("## 11. 건반 하나 빼기 (도구 없음, 모든 단계를 충돌 검사함)")
w()
rw, rb = RM["white"], RM["black"]
w("1. 가림판 띠를 들어낸다.")
w(pf("2. 그 건반이 있는 핀 칸의 패드 바를 앞 손잡이로 잡아 수평으로 당긴다. 잎 돌기가 립 앞끝(y%.1f)을 지나면(%.1f mm) 바가 0.3 내려앉아 아래 부분이 립에 얹히고, 립이 %.1f mm까지 받친다. 바 앞부분이 윗판에서 나온 뒤(%.1f mm)부터는 바를 윗판 쪽으로 밀어 올린 채(홈 천장, +1.5) 끝까지 뺀다: "
  "패드와 건반·레버·핀 사이 최소 %.2f(PET 심 3장 %.2f). 곧게만 당기면 끝에서 흑 패드 모서리가 흑건 윗면 턱 모서리와 %.2f(흑건 뒤끝은 가림판 밑 y%.1f~147에서 z%.1f로 낮춤)라 밀어 올림을 꼭 한다. 그 칸 레버 3개가 자유로워진다.", (PR["rail_lip_y0"], PR["bar_leaf_y"][0] + PR["bar_leaf_bump"] - PR["rail_lip_y0"], PR["plate_step_y"] - PR["rail_lip_y0"], PR["bar_raise_pull"], sl_pr, sl_pr3, sl_str, PR["black_skin_step"][0], PR["black_skin_step"][1])))
w(pf("3. 한 손 손톱으로 그 건반 레버의 손톱 턱(캐리어 앞 위)을 들어 윗판에 닿을 때까지 올린다(%.1f°, 힘 %.2f N). 빼기에 필요한 각은 백 %.1f°, 흑 %.1f°.", (min(SW.values()), rw["F_tab"], rw["lever_angle_needed_deg"], rb["lever_angle_needed_deg"])))
w(pf("4. 다른 손 손톱을 건반 뒤 윗판 턱(y146~147) 밑에 걸어 위로 당긴다: 백 %.1f N / 흑 %.1f N(스냅 %.0f N 기준; R2.50 쿠폰이면 %.1f N). 건반이 쉼 패드를 축으로 들렸다가 키퍼에 걸려, 뒤 노치 입술이 봉 위로 %.1f 올라온다. 블록은 핀 위로 %.2f.", (rw["pull_N"], rb["pull_N"], PR["snap_F"], rw["pull_N_snap_hi"], PR["removal_lip_clear"], rw["pin_clear"])))
w("5. 3 mm 앞으로 밀고, 앞을 2°(흑 5°) 들고, 앞으로 뽑는다. 흑건은 양옆 백건을 먼저 뺀다.")
_dq = C44["drop"]
w(pf("6. 레버를 내려놓는다. 건반이 빠진 레버는 %.2f N으로 놓인다: 기판 밖(C·C#·D·A·A#·B)은 바닥판(%.2f~%.2f° 떨어짐), 기판 위는 실제 BRD-01 배치로 E·F가 4067 모듈 윗면(z20, %.2f / %.2f°), "
  "D#·G#가 기판 위에 매단 보스(Ø%.0f, 레일 뒷면 브래킷 — D#는 나사 보스, G#는 위치 핀 보스; %.2f / %.2f°), F#·G가 기판 윗면(z%.1f, %.2f / %.2f°) — "
  "O1·O7에서는 G가 R301 위(%.2f°). (부품 한계 z20을 기판 전체에 두고 재면 %.1f~%.1f°.) 이때 스프링은 자유각을 지나 풀리지만 다리 끝은 보스 홈 입구 안 %.2f에 남는다(자유각 공차 −25°이면 입구 앞 %.2f → 레버를 들면 입구 경사가 다시 받음). "
  "다시 넣을 때는 3번처럼 레버를 들고 반대 순서로, 패드 바는 뒤 멈춤까지 민다.", (LD["E"]["F_rest"], min(LD[k_]["drop_deg"] for k_ in ("C", "C#", "D", "A", "A#", "B")), max(LD[k_]["drop_deg"] for k_ in ("C", "C#", "D", "A", "A#", "B")),
     _dq["E"]["actual"], _dq["F"]["actual"], PR["standoff_d"], _dq["D#"]["actual"], _dq["G#"]["actual"], PR["board_z"][1], _dq["F#"]["actual"], _dq["G"]["actual"],
     _dq["G"]["o17"], min(v_["generic"] for v_ in _dq.values()), max(v_["generic"] for v_ in _dq.values()), LEG["C_+0"]["in_groove"], -LEG["C_+5"]["in_groove"])))
w()
w("| 건반 | 당겨 올림 | 3 mm 밀기 | 기울임 | 뽑기 | 가장 가까운 짝 |")
w("|---|---|---|---|---|---|")
for k, v in RP.items():
    w(pf("| %s%s | %.2f | %.2f | %.2f | %.2f | %s |", (k, (pf(" (양옆 %s 먼저)", "+".join(v["removed"]))) if v["removed"] else "", v["pull_up"][0], v["slide_3mm"][0], v["tilt"][0], v["draw_out"][0], tr(v["draw_out"][1]))))
w()
w(pf("레버를 윗판 멈춤 %.1f°보다 0.5° 낮은 %.1f°로 잡고 검사했다.", (min(SW.values()), R["params"]["BH"])))
w()

# ============================================================================================ 12
w("## 12. 조정 절차 (모두 손으로)")
w()
w("| 조정 | 어디서 | 한 단위의 효과 (백 / 흑) |")
w("|---|---|---|")
w(pf("| 업스톱 시점 | 가림판 → 패드 바를 빼서, 패드와 쐐기 사이에 PET 심 0.1 넣고 빼기 | 레버가 %.2f° / %.2f° 일찍 = 건반 앞 %.2f / %.2f mm |", (AD["white_shim"]["db0_deg"], AD["black_shim"]["db0_deg"], AD["white_shim"]["front_mm"], AD["black_shim"]["front_mm"])))
w(pf("| DW | 가림판을 들고 강철 앞 윗면(패드 앞)에 텅스텐 퍼티 | 1 g = %+.2f / %+.2f g (건반 앞에 붙이면 %+.2f / %+.2f g) |", (AD["white_putty_steel"], AD["black_putty_steel"], AD["white_putty_front"], AD["black_putty_front"])))
w(pf("| 캡스턴 | 건반을 넣기 전 벤치 지그 + 가짜 레버 T2(10.1장): 바늘 ↔ 읽기 턱 (1/8회전 = 캡스턴 0.0625 = 바늘 %.2f / %.2f mm) | DW %+.2f / %+.2f g, 바닥 캡 높이 %+.2f / %+.2f mm |",
     (TDL["per_colour"]["white"]["per8"], TDL["per_colour"]["black"]["per8"], AD["white_0.125"]["dDW"], AD["black_0.125"]["dDW"], AD["white_0.125"]["dcap"], AD["black_0.125"]["dcap"])))
w(pf("| 건반 높이 | 벤치 지그의 쉼 펀칭, 높이 블록 T1b로 확인 (창 ±0.15) | 0.1 mm 한 장 = 건반 앞 %.2f mm |", AD["levelling_front_per_punching"]))
w()
fp_ = lambda k_: (pf("%.2f", STR[k_]["F_pinch"])) if STR[k_]["F_pinch"] else "-"
w(pf("**업스톱 시점 합격 기준 (r4.1, 종이 띠)**: 패드 바를 뒤 멈춤까지 민 뒤, 두께 0.05 종이 띠(영수증 종이 등)를 건반 앞 펠트 위(백 y3~9, 흑 앞 모서리 밑)에 놓고 건반 앞(백 y13, 흑 앞 + 10)을 추로 누른다. "
  "모델에서 띠가 물리기 시작하는 힘: 백 틈 −0.30 / −0.40(설계) / −0.50 → %s / %s / %s N, 흑 −0.35 / −0.45 / −0.55 → %s / %s / %s N. "
  "**합격: 백은 %s N에서 띠가 미끄러지고 %s N에서 물림, 흑은 %s N에서 미끄러지고 %s N에서 물림**(= 설계 틈 ±0.1). 먼저(작은 힘에) 물리면(틈이 덜 음수) 패드 밑에 심을 넣고, 늦게 물리면(틈이 더 음수) 심을 뺀다(한 장 = 패드 면 0.1 아래 = 레버가 %.2f° 먼저 닿음; r4.4 고침 2b: r4.4 고침 2까지 방향이 반대였음). 뺄 심이 없으면 그 칸 패드 바를 쐐기 0.1 얇게 다시 출력한다 — 단 쐐기 얇은 끝이 0.40 미만인 자리(백 쐐기 %.3f~, 끝 부속 A0·B0·C8)는 0.1 얇게 하면 출력 최소 %.1f 아래라, 쐐기를 그대로 두고 그 패드 자리의 바 밑면을 0.1 올려(바 %.1f → %.1f) 다시 출력하거나 패드 펠트를 0.1 얇은 것으로 바꾼다(r4.5 고침).", (fp_("white_-0.30"), fp_("white_-0.40"), fp_("white_-0.50"), fp_("black_-0.35"), fp_("black_-0.45"), fp_("black_-0.55"),
     fp_("white_-0.30"), fp_("white_-0.50"), fp_("black_-0.35"), fp_("black_-0.55"), AD["white_shim"]["db0_deg"], G["solved"]["wedge"]["w"][0], P4["pad_wedge_min"], P4["pad_bar_t"], P4["pad_bar_t"] - 0.1)))
w()

# ============================================================================================ 13
w("## 13. 예비 건반 보관함 (R29, 안치수 338.8 × 172 × 77)")
w()
sb = R["spare_bay"]
_pl = {p_["name"]: p_ for p_ in PLJ["parts"]}
_sp = lambda pre_, need_: [p_["total"] - need_ for n_, p_ in _pl.items() if n_.startswith(pre_)][0]
_spw, _spb = _sp("백건", 52), _sp("흑건", 36)
w(pf("건반 칸 %.1f(여유 1.0 + 건반 199.3 + 여유 1.0) + 칸막이 %.1f + 옆 칸 %.1f. 예비 건반은 부품표대로 백 %d개(모듈 7 + A0·B0·C8), 흑 %d개(모듈 5 + A#0)다. "
     "1층 백건 7개 %.1f × %.1f, 2층 흑 5 + A#0 + A0·B0·C8 %.1f × %.1f, 쌓은 높이 %.1f / 77, 폭 여유 한쪽 %.2f.",
     (sb["key_zone"], sb["divider"], sb["side_zone"], _spw, _spb, sb["layer1"][1], sb["layer1"][2], sb["layer2"][1], sb["layer2"][2], sb["stack"], sb["width_margin"])))
w()
w(pf("옆 칸(%.1f × 172 × 77)에는 부품표의 예비를 넣는다: 강철 블록 %d, Ø4 봉 %d(건반 봉 %d + 레버 봉 %d, 길이 161.4를 172 깊이 방향으로), 업스톱 패드 %d, 비틀림 스프링 %d, "
     "작은 부품 통(밸런스 핀 %d, 캡스턴 나사·너트 %d벌, 센서 자석 %d, PET 심).",
     (sb["side_zone"], _sp("강철 블록", 88), _sp("건반 봉", 9) + _sp("레버 봉 SUS", 9), _sp("건반 봉", 9), _sp("레버 봉 SUS", 9), _sp("업스톱 패드", 88), _sp("비틀림", 88 + 4),          # r4.5: 4 springs go to the stage-0 tests 8 / 13
      _sp("밸런스 핀", 88), _sp("캡스턴", 88), _sp("센서 자석", 88))))
w()
_small = [k_ for k_ in ("height_block", "capstan_gauge", "pin_gauge") if max(TLP[k_]["bbox"][:2]) <= 172 and min(TLP[k_]["bbox"][:2]) <= sb["side_zone"] and min(TLP[k_]["bbox"]) <= 77]
w(pf("레버 캐리어(%d곳)와 패드 바(6종)는 위치마다 달라 예비를 두지 않는다(부품표). 필요할 때 위치별 파일로 출력한다(캐리어 약 20분). "
     "출력 공구 가운데 높이 블록·가짜 레버·핀 게이지는 옆 칸에 들어간다(가장 큰 것 %s × %s). 벤치 지그(%s × %s)는 들어가지 않아 따로 둔다.",
     (len(VAR["carriers"]), fz(max(max(TLP[k_]["bbox"][:2]) for k_ in _small), 1), fz(min(TLP["capstan_gauge"]["bbox"][:2]), 1), fz(TLP["bench_jig"]["bbox"][0], 1), fz(TLP["bench_jig"]["bbox"][1], 1))))
assert len(_small) == 3
w()

# ============================================================================================ 14
w("## 14. 끝 부속")
w()
for s in ("left", "right"):
    e = EP[s]
    w(pf("- %s: 레버 x %s; 핀 %s; 핀 보스(왼/오) %s; 허브 칼라 %s; 패드 자리 %s N/mm; 모든 건반 2.5 m/s 동시에 윗판 %.1f MPa, 핀 이음 %.1f MPa.", ("왼쪽 (A0·A#0·B0)" if s == "left" else "오른쪽 (C8)", ", ".join(pf("%s %.2f", kv) for kv in e["levers"].items()), ", ".join(pf("x%.1f~%.1f", tuple(f_)) for f_ in e["fins"]),
         ", ".join(pf("%.2f/%.2f", tuple(b_)) for b_ in e["boss_len"]), ", ".join(pf("%s %.2f/%.2f", (k_, v_[0], v_[1])) for k_, v_ in e["collars"].items()),
         ", ".join(pf("%s %.0f", kv) for kv in e["loads"]["seat_k"].items()), e["loads"]["sigma"], e["loads"]["fin_top"])))
    for nm, q in e["stat"].items():
        w(pf("  - %s: 캡스턴 y%.2f, DW %.1f, UW %.1f, m_eff %.1f; 모듈 패드 면을 그대로 쓰면 자기 정착 바닥에서 강철 ↔ 패드 면 %+.2f (설계 %+.2f) → r4.2: 자기 면(기울기 %.2f°)으로 쐐기 %.3f~%.3f 출력 (모듈 %.3f~%.3f, %+.3f / %+.3f)", (nm, q["y_cap"], q["DW"], q["UW"], q["meff"], q["gap_to_face"], q["gap_design"], q["face_tilt_deg"], q["wedge"][0], q["wedge"][1], q["wedge_module"][0], q["wedge_module"][1], q["wedge_delta"][0], q["wedge_delta"][1])))
    w(pf("  - 센서 바 %s, 스프링 홈 보스 %d, 겹침 %d, 스윕 최소 %.2f", ("x0.5~46.5 (A#0 낮은 구간)" if s == "left" else "x0.5~23.0", len(e["levers"]), len(R42["fit_end"][s]), CL["end_parts"][s]["min"])))
w("- r4.3: 끝 부속에는 제어 기판·RP2040-Zero·USB가 없다(센서는 O1·O7이 EXT로 읽음). 뒤 선반과 뒷벽은 모듈 것을 x74~94 밖에서 잘라 쓰므로 바뀐 것이 없고, 끝 부속 스윕·겹침 검사도 새 모델로 다시 돌렸다.")
for s_, nm_ in (("left", "EL"), ("right", "ER")):
    q_ = C44["ends"][s_]
    w(pf("- r4.4 %s: 센서 기판 x%.1f~%.1f(센서 바 안), 받침 기둥 x%.1f~%.1f + 앞·뒤 리브 x%.1f~%.1f(z%.1f까지), 뒤 리브 틈 x%.0f~%.0f; 리드 %d심은 패드(아랫면) → 틈 → 바닥(y%.2f까지 모음) → 레일 밑 차선 x%s~%s(z%.0f~%.0f) → 뒷벽 홈(z%.0f~%.0f) → 뒤 통로 %s.", (nm_, q_["board"][0], q_["board"][1], PR["sb_post"][0], PR["sb_post"][1], q_["rib_x"][0], q_["rib_x"][1], PR["sb_board"][4], q_["gap"][0], q_["gap"][1], q_["cores"], q_["fan_y"], fh(q_["lane"][0]), fh(q_["lane"][1]),
         q_["lane_z"][0], q_["lane_z"][1], q_["notch_z"][0], q_["notch_z"][1], "X401" if s_ == "left" else "X411")))
w()

# ============================================================================================ 15
w("## 15. 출력 계획")
w()
# r4.4 doc: rows named and counted like parts_list.json; orientation text from run_all's print plan (metrics mass.print_plan), the pad-bar leaf
# size from P (the print-plan text said 0.6x4x8), plus the end-part frames, rod plugs and printed tools that the plan did not list
_pp = {p_[0].split(" (")[0]: p_ for p_ in MA["print_plan"]}
_kw = MA["key_g"]
_wk = [v_ for k_, v_ in _kw.items() if "#" not in k_]
_ek = {k_: q_["key_g"] for s_ in ("left", "right") for k_, q_ in EP[s_]["stat"].items()}
_bl = PR["bar_leaf"]
_plq = lambda pre_: [p_ for p_ in PLJ["parts"] if p_["name"].startswith(pre_)][0]
_pbar = _pp["패드 바"][1]
assert "뒤 계단 양쪽에 예하중 잎 0.6×4×8" in _pbar
_pbar = _pbar.replace("뒤 계단 양쪽에 예하중 잎 0.6×4×8", pf("양쪽 가장자리에 예하중 잎 혀 %.1f×%.1f×%.0f(%.1f 눌림, 레일 립 위)", tuple(_bl)))
_cg = {}
for k_, v_ in VAR["carriers"].items():
    _cg.setdefault(tuple(v_), []).append(k_)
_cshare = " / ".join("·".join(v_) for v_ in _cg.values() if len(v_) > 1)
_frm15 = _pp["프레임"][1]
assert "패드 바 레일(도브테일)은 윗판에 붙어 있음" in _frm15
_frm15 = _frm15.replace("패드 바 레일(도브테일)은 윗판에 붙어 있음", "패드 바 L 레일(웹 + 립, P13)은 윗판과 한 몸")
rows15 = [
    (pf("백건 (7종 + 끝 A0·B0·C8), %d개", _plq("백건")["total"]), _pp["백건"][1],
     pf("모듈 %.2f(평균, %.2f~%.2f) + 서포트 %.1f; 끝 A0 %.1f · B0 %.1f · C8 %.1f", (sum(_wk) / len(_wk), min(_wk), max(_wk), MA["support_white_g"], _ek["A0"], _ek["B0"], _ek["C8"]))),
    (pf("흑건 (4종: C#·D#은 같음, + 끝 A#0), %d개", _plq("흑건")["total"]), _pp["흑건"][1], pf("%.2f + 서포트 %.1f; 끝 A#0 %.1f", (_kw["C#"], MA["support_black_g"], _ek["A#0"]))),
    (pf("레버 캐리어 (위치 %d곳, 칼라 %d종 — %s는 칼라가 같음, 옆벽에 음 이름 새김), %d개", (len(VAR["carriers"]), len(_cg), _cshare, _plq("레버 캐리어")["total"])),
     _pp["레버 캐리어"][1] + pf(" r4.5: 주머니 구간의 짧은 다리 홈(허브 벽을 뚫는 %.1f 폭, x 방향 = 쌓는 방향)은 서포트 없이 나오고, 주머니 Ø%.1f는 한 층 위에서 다리(bridge)로 덮인다", (PR["spring_pocket"][1], PR["spring_pocket"][0])), pf("%.2f", MA["lever_carrier_g"])),
    (pf("프레임 (모듈), %d개", _plq("프레임")["total"]), _frm15, pf("%.1f + 서포트 %.0f", (MA["frame_g"], MA["support_plate_g"]))),
    (pf("끝 부속 프레임 (왼쪽 A0~B0, 오른쪽 C8), %d개", _plq("끝 부속 프레임")["total"]), "모듈 프레임과 같은 방향(바로 세워, 윗판 밑 트리 서포트). 볼(cheek)·도브테일·이음 핀 보스를 함께 출력",
     pf("%.1f(부품표 값, 왼쪽 폭 47 기준) + 서포트", _plq("끝 부속 프레임")["unit_g"])),
    (pf("패드 바 (6종: 모듈 칸 1~4 + 끝 부속 왼·오), %d개", _plq("패드 바")["total"]), _pbar, pf("%.2f(모듈 4개 평균)", sum(MA["pad_bars_g"]) / len(MA["pad_bars_g"]))),
    (pf("레버 봉 끝 마개, %d개", _plq("레버 봉 끝 마개")["total"]), pf("끝면을 베드에(원판 Ø4.0 × %.1f). 이음 쪽 핀 보스 구멍에 핀 면과 같게 눌러 끼움", PR["rod_L_plug"]) if "rod_L_plug" in PR else "끝면을 베드에(원판 Ø4.0). 이음 쪽 핀 보스 구멍에 핀 면과 같게 눌러 끼움",
     pf("%.2f", _plq("레버 봉 끝 마개")["unit_g"])),
    (pf("가림판 띠, %d개", _plq("가림판 띠")["total"]), _pp["가림판 띠"][1], pf("%.1f", MA["curtain_g"])),
    (pf("센서 바, %d개", _plq("센서 바")["total"]), _pp["센서 바"][1], pf("%.0f", MA["sensor_bar_g"])),
    (pf("출력 공구 (악기당 1벌), %d개", len(TLP)), "10.1장 표(모두 서포트 없음)", " / ".join(pf("%.1f", v_["mass_g"]) for v_ in TLP.values())),
]
w("| 부품 (88건반 전체 개수, 예비 포함) | 방향·서포트 | 개당 g |")
w("|---|---|---|")
for r_ in rows15:
    w(pf("| %s | %s | %s |", tuple(esc(x_) for x_ in r_)))
w()
w(pf("88건반 전체(모듈 7 + 끝 부속 + v3 기타 출력 + 예비 세트): 필라멘트 %.2f kg, %.0f h(15 g/h). 윗판 밑 서포트가 모듈마다 %.0f g이다(핀 사이 39 mm를 서포트 없이 브리지로 뽑으면 88건반에서 약 %.1f kg 줄어듦 — 단계 0 시험 16). "
     "이 합계에 출력 공구(%.0f g, 약 %.0f시간)와 단계 0 키트(추정 약 %.0f g, 15 g/h로 약 %.0f시간; 속을 꽉 채우면 %.0f g, 17.1장)는 들어 있지 않다. "
     "악기 부품은 모두 220 × 220 베드에 들어간다. 출력 공구와 단계 0 키트는 256 × 256 베드 기준이다(220 베드에서는 벤치 지그만 대각선으로).",
     (M["filament_kg"], M["print_h"], MA["support_plate_g"], 7 * MA["support_plate_g"] / 1000, sum(v_["mass_g"] for v_ in TLP.values()), sum(v_["time_min"] for v_ in TLP.values()) / 60, S0EST, S0EST / 15.0, S0G)))
w()

# ============================================================================================ 16
w("## 16. 비용 (v3.2 대비)")
w()
co = R["cost"]
w("| 구분 | 품목 | 수량 × 단가 | 금액 | 근거 |")
w("|---|---|---|---|---|")
for n_, q, u, src in co["items"]:
    if "다리 3/22.3" in n_:
        n_ = n_.replace("다리 3/22.3", pf("다리 %.1f/%.1f", (_M4.P["spring_short_leg"], _M4.P["spring_leg"])))
    w(pf("| 추가 | %s | %d × %s | %s | %s |", (n_, q, krw(u), krw(q * u), src)))
for n_, q, u in co["removed_items"]:
    w(pf("| 삭제 | %s | %d × %s | −%s | 추정 |", (n_, q, krw(u), krw(q * u))))
for n_, c in co["consumables"]:
    w(pf("| 소모품 | %s | | %s | 추정 |", (n_, krw(c))))
for n_, c, src in co["optional"]:
    w(pf("| 선택 | %s | | %s | %s |", (n_, krw(c), src)))
w()
w(pf("기본 구성 변화(소모품 %s원 제외) +%s − %s = %s원 → %s원(한도 1,000,000, r3 %s원). 가격은 모두 추정이다.", (krw(sum(c_ for _, c_ in co["consumables"])), krw(co["add"]), krw(co["removed"]), skrw(co["delta"]), krw(co["base_bom"]), skrw(r3s["cost"]))))
w()
w(pf("r4.5: 비틀림 스프링은 미스미 %s 100개 × 310원(282원 + VAT 10 %%) = 31,000원(r4.4 주문 제작 추정 100 × 200 = 20,000원), 다리 200곳을 자를 경선(피아노선) 니퍼 15,000원(추정)을 새로 넣었다 → 기본 구성 변화 %s → %s원.", (PR["spring_cat"]["part"], skrw(R44["cost"]["delta"]), skrw(R["cost"]["delta"]))))
w()
w(pf("r4.4: 출력 공구는 살 것이 없다(봉 토막·핀·강철은 위 목록의 것을 씀). USB-C 선을 CVILUX DH-20M50052로 바꾸면 회로 쪽 구매 목록(C04 줄)이 %s원이다 — 이 표(W1 액션) 밖이다(1d-3장).",
     skrw(CBR["qty_needed"] * CBR["price_krw"] + CBR["shipping_krw"] - 12960)))
w()

# ============================================================================================ 17
w("## 17. 단계 0 시험 계획 (합격 / 불합격 숫자)")
w()
w("시편: 프레임 조각 S1(모듈 x0~85, 건반 C~F, 핀 3개, 윗판·패드 바 포함) + 봉 2 + 레버(강철·스프링) + 패드. r4.3 글의 ‘D·D#·E 3건반 조각’은 C# 자리가 없고 패드 바 두 칸에 걸쳐 S1으로 바꿨다(FE로 S1의 C# 자리 강성은 모듈과 0.7 % 차이, 17.1장). "
  "출력 시편·지그는 17.1장의 단계 0 키트다.")
w()
w("| # | 시험 | 방법 | 합격 | 불합격이면 |")
w("|---|---|---|---|---|")
tests = [
    ("패드 반발 (가장 먼저)", "레버(강철 + 캐리어)를 패드 바에 붙인 패드로 PLAY 속도에 휘둘러 되튐 각속도를 240 fps로 잼(계 전체 e). 후보: ① 미세셀 우레탄(PORON 계열) 6T + 펠트 1T, ② Sorbothane 계열 점탄성 PU 시트(카탈로그 Lupke 반발 10~15 %, 곧 판 하나의 자유 낙하 e ≈ 0.32~0.39), ③ ① 위에 부틸 고무 1T",
     pf("실효 e ≤ %.2f (설계 %.2f)", (PR["pad_e_pass"], PR["pad_e"])),
     pf("① e 0.10~0.15: 쐐기를 다시 뽑아 틈 −0.60 / −0.65 + 폼 E 1.4 (계산: e 0.15에서 백 들림 %.3f, 흑 ABUSE %.3f, 연타 %.1f / %.1f Hz, 0.45 N 유령 %s / %s는 모두 거름). ② e > 0.15: 다른 후보로(e 0.25면 백 들림 %.3f, 흑 ABUSE %.3f로 한계 끝, 백 ABUSE 키퍼 %.2f)", (fb1["white"]["lift_play"], fb1["black"]["lift_abuse"], fb1["white"]["rep"], fb1["black"]["rep"], pct(fb1["white"]["ghost045"]), pct(fb1["black"]["ghost045"]),
        e025["white"]["lift_play"], e025["black"]["lift_abuse"], e025["white"]["keep_abuse"]))),
    ("패드 강성", "패드를 강철 조각으로 눌러 힘-눌림", pf("25 %% 압축 %.2f MPa ± 30 %% (E 0.7~1.4 MPa)", H["sigma25"]), pf("두께·등급 교체. E 0.7이면 흑 ABUSE 들림 %.3f", SE["pad E 0.7 (softer foam)"]["black"]["lift_abuse"])),
    ("패드 자리 처짐", pf("윗판 %s 자리에 100 N, 그리고 C~F 6자리에 60 N씩, 다이얼 게이지", kmin_key), pf("한 자리 ≤ %.2f mm (%.0f N/mm, 설계 %.0f), 6자리 각 ≤ %.2f mm (%.0f N/mm, 설계 %.0f)", (100.0 / PR["seat_k_req"], PR["seat_k_req"], SEAT["k_min"], 60.0 / PR["seat_k_chord_req"], PR["seat_k_chord_req"], SEAT["k_chord"])),
     "띠 E가 낮으면 윗판 채움 100 % 다시, 그래도면 `plate_t` +0.6~1.2(17.1장 시험 3 표); 킬·레일 이음은 시험 21로 본다(F|F# 핀은 바닥에 서지 않고 킬로 레일에 붙음 — r4.4 고침 2b부터 기판 밑 바닥은 구멍)"),
    ("앞 펠트", "강철 공 낙하 + 누름", "실효 e ≤ 0.22", "PU를 두껍게"),
    ("스냅 노치 반지름 쿠폰", "R2.50 / 2.525 / 2.55 / 2.575 / 2.60에 천 0.5T, 빠짐 힘(용수철 저울)과 끼운 채 DW 변화", pf("빠짐 %.0f~%.0f N, DW 변화 ≤ 0.5 g", (PR["snap_F_min"], PR["snap_F"])), "다음 반지름"),
    ("탭 천 쿠폰", pf("흑 탭 %.1f + 천 0.4 / 0.5 / 0.6T를 벽 사이 8.0에", PR["tab_w_b"]), "걸림 없이 옆 놀음 ≤ 0.1", "천 두께 바꿈"),
    ("DW/UW", "y13(흑 앞 + 10)에 저울·추", "DW 47~55 g(립 y0 ≥ 47), UW ≥ 20 g", "퍼티; 스프링 다리 홈 위치"),
    ("비틀림 스프링 (r4.5 미스미, r4.5 고침 가둠 홈)", "C06 시험대로(C06b = 모델 주머니 단면, 진짜 Ø4 봉 — 코일 뜸도 잼) 쉼·바닥 토크, k_t, 자유각; 손 들기 25°로 1시간 둔 뒤 자유각 다시; 가둠 홈 폭(0.5 날)", pf("쉼 %.2f, 바닥 %.2f N·mm ± 15 %%, 자유각 %.1f ± 5°, 1시간 뒤 자유각 변화 ≤ 2°", (W["spring_T_rest"], W["spring_T_bottom"], PR["spring_free_deg"])), pf("덜 감김: 뒷벽 홈 바닥 깊게 ≤ %.1f mm(+%.1f°), 더 모자라면 `spring_notch_rot`(가둠 홈을 돌려 캐리어 다시 출력); 더 감김: 홈 바닥 얕게; 1시간 뒤 자유각이 줄면 손 들기를 카탈로그 토크 한계 각 아래로(18장)", (S0["analysis"]["C06"]["deeper_max"], S0["analysis"]["C06"]["deeper_max"] / (S0["analysis"]["C06"]["arm"] * math.pi / 180)))),
    ("복귀 시간", "240 fps, 1 N 1 s 누른 뒤 뗌; 건반 뺀 레버를 다시 들어 스프링 다리가 홈에 다시 걸리는지", "t50 ≤ 37.6 ms, 끝까지 ≤ 60 ms; 다리 10번 모두 다시 걸림", "스프링 감는 각 +10°; 홈 입구 경사 키움"),
    ("노치 들림 + 입술 천 마모", pf("노치 옆 흰 점 240 fps, 1.5 / 2.5 m/s급 뗌·누름 10회, 6건반 화음 1.0~1.5 m/s; 흑건 하나를 PLAY 1.5 m/s로 10^5회(흑은 들림 0.06에서도 입술 모서리가 %.1f N 안팎으로 닿음)", lipb),
     "PLAY ≤ 0.20, ABUSE ≤ 0.40, 빠지지 않음; 입술 천 닳아 뚫림 없음, 빠짐 힘 변화 ≤ 30 %", "패드·앞 펠트를 합격선 쪽으로; 천을 두꺼운 것으로"),
    ("유령", "1.5 / 1.0 / 0.8 m/s 뒤 0.45·0.6·1 N 누름, 6건반 화음 0.8~1.5 m/s, 거름 켜고 끔; 펌웨어가 의심 상태의 다시 눌림 시각(note-on부터)을 기록",
     pf("거름(문턱 %.1f m/s, 재무장 %.0f ms, 다시 눌림 %.0f ms)을 켜면 재타건 없음; 기록된 유령 다시 눌림 ≤ %.0f ms", (PR["ghost_v_note"], PR["ghost_win"], PR["ghost_rep_max"], PR["ghost_rep_max"])),
     pf("거름 비율 25 → 30 %%; 유령 다시 눌림이 %.0f ms를 넘으면 창 = 가장 늦은 것 + 100 ms", PR["ghost_rep_max"])),
    ("패드 바 놀음·빼기", pf("패드 바를 뒤 멈춤까지 넣고 위아래로 흔듦 — 넣은 직후와 40 °C 1주 뒤(잎 상시 굽힘 %.1f MPa의 크리프); 빼기를 흑 칸에서 10번(%.1f mm부터 밀어 올림)", (R42["gaps_module"]["leaf_sigma"], PR["bar_raise_pull"])),
     "상하 놀음 없음(잎이 바를 자리에 밀어 올림), 패드 펠트가 흑건에 닿은 자국 없음", "잎 눌림 0.3 → 0.5 또는 잎 두께 0.8; 그래도 늘어지면 바 윗면을 사포로 맞춰 레일에 빡빡하게(손 맞춤)"),
    ("스프링 넣기 (r4.5 고침 가둠 홈)", "C16a 캐리어 3개에 짧은 다리 끝부터 가둠 홈을 따라 스프링을 밀어 넣음(긴 다리 +x 끝), 봉을 꿰고 긴 다리를 뒷벽 홈에 밑에서 넣음; 레버를 −31°~+18°로 돌림",
     S0["tests"]["13"]["pass_ko"], "; ".join(pf("%s → %s", (o_["range"], o_["param"])) for o_ in S0["tests"]["13"]["outcomes"])),
    ("종이 띠 시점", "12장 기준(0.05 띠)", "백·흑 모두 합격 띠 안", "PET 심"),
    ("피로", "Z 방향 핀-윗판 이음 시편 반복 인장", pf("PLAY 한 건반 %.1f MPa 10^6회, 화음 %.1f MPa 10^4회 균열 없음", (M["fin_top_play_single_mpa"], M["fin_top_play_chord_mpa"])), "이음 모서리 살 3 mm"),
    ("윗판 출력", "모듈 프레임 조각을 서포트 없이 브리지", "핀 사이 39 mm 브리지가 처짐 ≤ 0.3", pf("트리 서포트 (%.0f g)", MA["support_plate_g"])),
    ("느낌", pf("직접 쳐 봄: y90 %.0f g, 1 N에서 흑 바닥 %.2f mm 부드러움", (W["DW_y90"], H["held_pad_front_b"])), "받아들일 만함", "흑 틈 −0.45 → −0.3"),
    ("90° 세움", "모듈 조각을 뒤로 세웠다 눕힘", "모든 건반 제자리(앞 높이 ±0.2)", "쿠폰 반지름을 한 단계 작게"),
    ("USB 케이블 맞춤 (r4.3)", "뒤 선반 홈·뒷벽 개구가 있는 프레임 뒤 조각 + 핀 헤더에 세운 RP2040-Zero에 실제 USB-C 케이블을 10번 꽂고 뺌",
     pf("몰드 ≤ %.1f × %.1f(z%.1f~%.1f), 홈 가장자리·리브·핀과 1 mm 이상 떨어짐, 케이블이 뒤 통로로 꺾여도 리셉터클을 비틀지 않음", (PR["usb_x"][1] - PR["usb_x"][0], PR["usb_z"][1] - PR["usb_z"][0], PR["usb_z"][0], PR["usb_z"][1])),
     pf("1d-3장의 확인된 선(CVILUX DH-20M50052, %.2f × %.2f × %.2f)으로 바꿈", (CBR["plug_w_mm"], CBR["plug_t_mm"], CBR["plug_l_mm"]))),
    ("강철 유지 (r4.4 고침 2·2b: 탄성 접착)", pf("C16a(생산 캐리어 C, 3개) + C16b 받침: 스냅만(1개) 강철을 누름 코로 눌러 빠지는 힘을 잼(모델 %s N); MS 폴리머로 접착한 2개를 24 h 굳히고 5 ↔ 45 °C 3번 뒤 %.0f N(ABUSE의 1.5배)으로 10 s × 3, 1 m 낙하 3번; 10^5회(매 음 %.0f N)는 캠 장치 또는 완성 모듈 1주 연주 뒤 다시",
                                           (" ~ ".join(pf("%.0f", R["steel_retention"]["peaks"]["play"]["B"] / v_) for v_ in sorted((R["steel_retention"]["wall_plate"]["play_a0.50_clamped"]["spread_max"], R["steel_retention"]["wall_plate"]["play_a0.50_pinned"]["spread_max"]), reverse=True)),
                                            1.5 * R["steel_retention"]["peaks"]["abuse"]["B"], R["steel_retention"]["peaks"]["play"]["B"])),
     "접착: 온도 순환 뒤에도 강철이 캐리어에 대해 0.05 mm 넘게 움직이지 않음, 흰 줄·균열·들뜸 없음, 낙하 뒤 그대로",
     "접착면 사포질·탈지 다시, PETG 프라이머 + 같은 MS 폴리머 또는 다른 MS 폴리머 제품(단단한 에폭시는 안 됨 — 열팽창); 그래도 안 되면 옆벽 0.7 → 1.0(레버 폭 11.2, 배치 다시)"),
    # r4.5 fix 3 (verifier major): service direction - the module stands on the C17a comb (fin lines + rear wall only), load from above
    ("첫 모듈 정하중 (r4.5 고침; 하중 방향은 r4.5 고침 3)",
     pf("조립한 첫 모듈을 C17a 받침 빗에 얹음: 핀 선 x%s 밑과 뒷벽 밑만 받침, 레일 밑 x%.1f~%.1f와 기판 구멍 밑은 빔, 모듈 밑 EVA는 뗌. %s 여섯 패드 자리 위 윗판에 6 × %.0f N(%.1f kg) 판재·물통, 다이얼로 E·F 자리 처짐. "
        "쓰임에서는 패드가 윗판을 밑에서 밀어 킬이 레일을 들어 올린다. 모델이 선형이라 이 받침에서 위로부터 누르면 같은 레일 휨이다",
        (" / ".join(f1(v_) for v_ in S0C17["fin_lines"]), S0C17["rail_free"][0], S0C17["rail_free"][1], "-".join(S0C17["keys"]), S0C17["F"], S0C17["kg"])),
     pf("E·F ≤ %.2f mm (모델 %.3f; 레일 받침의 두 끝: 단단 %.3f, 이웃 핀 선 사이 단순 지지 %.3f — 불합격)", (S0C17["limit"], S0C17["dead_seats"]["fins"]["EF"], S0C17["dead_seats"]["rigid"]["EF"], S0C17["dead_seats"]["fins_span"]["EF"])),
     pf("run_all의 화음 자리 강성 `k_ch`를 잰 값(%.0f N ÷ 처짐)으로 바꿔 화음 자리 동역학(들림 0.20, 키퍼, 유령)을 다시 봄; 그래도 불합격이면 회로 세션과 리본 차선 위 레일 높이를 다시 정함(킬 z%.1f과 핀 앞끝 y%.1f은 이미 건반 F와 1.3 한계)",
        (S0C17["F"], PR["fin_keel"][2], R["keel_rail"]["fin_front"]))),
]
assert tests[7][0].startswith("비틀림 스프링") and tests[8][0] == "복귀 시간" and tests[19][0].startswith("강철 유지") and tests[20][0].startswith("첫 모듈 정하중")   # row no. = stage-0 test no.
for i, t in enumerate(tests, 1):
    w(pf("| %d | %s | %s | %s | %s |", ((i,) + tuple(esc(x_) for x_ in t))))
w()
# ============================================================================================ 17.1 stage-0 kit (r4.4, open issue 7)
w("### 17.1 단계 0 시험 키트 (r4.4, 남은 문제 7)")
w()
_bb = max(S0["parts"], key=lambda p_: max(p_["bbox"][:2]))
w(pf("여기서는 아무도 물리 시험을 할 수 없다. 그래서 집에 있는 도구로 위 시험을 할 수 있게 출력 시편, 재는 법, 합격 숫자, 결과마다 바꿀 모델 값을 모았다. "
     "`stage0/make_stage0.py`가 지금 모델(`%s`, %s, metrics.json)에서 만들었고, 모델에 없는 값은 ‘제안’이라고 적었다. "
     "위 %d개 시험에 모델 밖 시험 3개를 더했다: P 밸런스 핀 압입, C 캡스턴 너트 트랩, T 펠트·천 두께. "
     "출력 시편은 %s다(%s%s). 모두 PETG, 서포트 없음, 닫힌 몸 STL이다. 256 × 256 베드에 들어가고, 가장 큰 것(%s)이 %s × %s라 220 베드에도 들어간다. "
     "속을 꽉 채우면 PETG %.0f g(%.0f cm³)다. 채움 40 %% 부품을 공구와 같은 계수 %.2f로 줄이면 약 %.0f g, 15 g/h로 약 %.0f시간이다(추정). "
     "시험 20(강철 유지, r4.4 고침 2)은 C16a(생산 캐리어를 모델에서 그대로)·C16b로 한다.",
     (MODEL_TAG(S0["model_dir"]), S0["model_version"], len(tests), S0CNT, S0IDS, ("; " + S0MUL) if S0MUL else "", _bb["id"], fz(max(_bb["bbox"][:2]), 1), fz(min(_bb["bbox"][:2]), 1),
      S0G, S0V, S0FF, S0EST, S0EST / 15.0)))
w()
w("- 절차: `stage0/stage0_procedure.md` (준비물, 출력 설정, 시험마다 재는 법·계산·합격·결과 표). 결과 기록표: `stage0/stage0_results_template.csv`(판정 O/X). "
  "시편 치수·합격선·결과 대응: `stage0/stage0_geometry.json`. 시편 파일: `stage0/stl/<ID>.stl`, 두 방향 그림 `stage0/png/`, OpenSCAD 원본 `stage0/scad/`.")
w("- 결과를 모델에 넣는 법: 기록표를 채우고, 바뀐 값만 `model_v4.py`의 `P`에 넣고, `run_all.py`를 다시 돌려 0.2장의 목표가 모두 통과인지 본다. 통과하지 않으면 아래 표의 다음 대안으로 간다. "
  "모델에 아직 없는 값(시험 P의 핀 구멍 Ø, 시험 C의 너트 홈 폭·잠김 구멍 Ø)은 새 매개변수로 넣고 geometry에 내보낸다.")
w()
_kd = S0["tests"]["3"]["design"]
_c04 = {r_["R"]: r_ for r_ in S0["analysis"]["C04"]["rows"]}
w(pf("**키트를 만들며 찾은 것.** (1) 6건반 화음 자리의 여유가 %.1f %%뿐이다(설계 %.0f, 합격선 %.0f N/mm). 출력한 윗판의 실효 E가 %.0f MPa(모델 %.0f의 %.1f %%)보다 낮으면 불합격이다. 그래서 굽힘 띠 C03a를 시험 3의 핵심으로 넣었다. "
     "(2) 시험 3 시편은 S1(C~F)이다(위). (3) 패드 반발을 재는 방법이 D11(60 g 추를 2.5 m/s로 떨어뜨림)과 17장(레버를 휘두름)에서 다르다. 모델 정의(`PadTable.calibrate`: 레버 혼자, 단단한 자리, PLAY 각속도)에 맞춰 C01 진자대를 기준으로 삼았다. "
     "θ0 150°에서 PLAY 각속도의 %.0f %%가 나오고, 마찰 보정 식에서 레버 질량과 무게중심이 지워진다. (4) 노치 R2.525 이하는 입술이 닿는 들림(%.3f)이 PLAY 최대 들림(0.161)보다 작아, 그 R을 고르면 들림 판정을 다시 세워야 한다. R2.55 흑 추정 빠짐 힘은 %.2f N이다.",
     (100 * (1 - S0R), _kd["seat_k_chord"], PR["seat_k_chord_req"], S0E * S0R, S0E, 100 * S0R, 100 * [r_ for r_ in S0["analysis"]["C01"]["release_table"] if r_["theta0"] == 150][0]["omega_ratio_play"],
      _c04[2.525]["touch"], _c04[2.55]["F_est_white"] * S0["analysis"]["C04"]["w_black"] / S0["analysis"]["C04"]["w_white"])))
w()
w("| 시험 | 시편 (`stage0/stl/`) | 합격 | 결과 → 모델에서 바꿀 값 |")
w("|---|---|---|---|")
_pid = {p_["id"]: p_ for p_ in S0["parts"]}
for k_, t_ in S0["tests"].items():
    _ps = [x_ for x_ in t_["parts"] if x_ in _pid]
    _pc = " · ".join(pf("%s %s", (x_, _pid[x_]["name_ko"].split(" (")[0])) for x_ in _ps) if _ps else "조립 모듈"
    _oc = "; ".join(pf("%s → %s", (o_["range"], o_["param"])) for o_ in t_["outcomes"] if o_.get("param")) or "17장 표의 ‘불합격이면’"
    if k_ == "19":
        _oc = pf("게이지 안 들어감 → 1d-3장의 확인된 선 CVILUX DH-20M50052(%.2f × %.2f × %.2f)로 바꿈(회로 인터페이스는 고정; `stage0_geometry.json` 시험 19의 ‘몰드 폭 ≤ 11 케이블로’는 이것으로 바뀜)", (CBR["plug_w_mm"], CBR["plug_t_mm"], CBR["plug_l_mm"]))
    if k_ == "3":
        # r4.4 doc retry 2: the kit wrote the thicker-plate options with the fix-2-before z_top 72.80; re-rendered with this model's z_top
        _zt = H["z_top"]
        assert "(z_top 73.4)" in _oc and "(z_top 74.0 = 높이 목표 끝)" in _oc, _oc
        _oc = _oc.replace("(z_top 73.4)", pf("(z_top %.2f)", _zt + 0.6)).replace("(z_top 74.0 = 높이 목표 끝)", pf("(z_top %.2f — 높이 목표 z74를 %.2f 넘음, +%.2f까지)", (_zt + 1.2, _zt + 1.2 - 74.0, 74.0 - _zt)))
    _pass = t_["pass_ko"].replace("아래 환산표", "절차 파일의 환산표")
    w(pf("| %s %s | %s | %s | %s |", (k_, esc(t_["title_ko"]), esc(_pc), esc(_pass), esc(_oc))))
w()

# ============================================================================================ 18
w("## 18. 남은 위험")
w()
risks = [
    pf("**6건반 동시 화음의 유령은 펌웨어에 기댄다.** r4.1에서 화음 자리가 %.0f N/mm로 굳었어도 0.45~0.6 N 가벼운 누름은 기계적으로 재무장한다(7.4). 거름 규칙(문턱 %.1f m/s, 25 %%, note-on부터 재무장 %.0f ms · 다시 눌림 %.0f ms)이 모두 버리지만(한계와의 여유 최소 %.2f m/s), 규칙을 끄면 유령이 난다. "
    "모델에서는 재무장한 건반이 %.1f s 안에 스스로 다시 닿지 않아(뜬 채 붙잡힘) 창 %.0f ms는 손가락의 다시 눌림을 기준으로 잡은 값이다 — 단계 0 시험 11 기록으로 확인. "
    "대가: 재무장 뒤 note-on부터 %.0f ms 안에 앞 음의 1/4보다 느린 진짜 재타건은 모든 세기에서 버려진다.", (SEAT["k_chord"], PR["ghost_v_note"], PR["ghost_win"], PR["ghost_rep_max"], gh_margin, PR["ghost_long"] / 1000.0, PR["ghost_rep_max"], PR["ghost_rep_max"])),
    pf("**모델 하한 v_floor 0.1 모서리.** 접촉 감쇠의 시작 속도 하한을 0.1로 두면 6건반 화음 1.45~1.5 m/s에서 들림 %.3f(0.20 초과 %.3f, 입술이 잠깐 닿음), 한 건반은 %.3f. 공칭 하한 0.02와 모든 합격선 재료에서는 0.20 아래다. 단계 0 시험 10(화음 포함)으로 확인한다.", (M["key_lift_chord_vf01_mm"], M["key_lift_chord_vf01_mm"] - PR["lift_play"], M["key_lift_vf01_single_mm"])),
    pf("**패드 재료값(가장 큰 위험).** 모든 결과는 계 실효 e %.2f(합격선 %.2f), 폼 E %.1f MPa 가정이다. 카탈로그 재료 하나의 자유 반발은 이보다 크다(Sorbothane Lupke 반발 10~15 %% → e ≈ 0.32~0.39). e 0.15면 백 0.45 N 유령 %s(거름), 흑 ABUSE 들림 %.3f; e 0.25면 백 PLAY 들림 %.3f(0.20 초과), 백 ABUSE 키퍼 %.2f(닿음), 흑 ABUSE %.3f(한계). 대안 ①(틈 −0.60 / −0.65 + E 1.4)은 e 0.15에서 들림 %.3f / ABUSE %.3f로 되돌린다. 단계 0 시험 1을 가장 먼저 한다.", (PR["pad_e"], PR["pad_e_pass"], PR["pad_E"], pct(e015["white"]["ghost045"]), e015["black"]["lift_abuse"], e025["white"]["lift_play"], e025["white"]["keep_abuse"], e025["black"]["lift_abuse"], fb1["white"]["lift_play"], fb1["black"]["lift_abuse"])),
    pf("**만능기판 홈.** F|F# 핀이 바닥에 닿으려면 기판 앞쪽에 폭 %.1f, 깊이 %.1f의 홈을 내고 x%.2f~%.2f(y%.1f~%.1f, r4.3: 핀 면에서 1.2)에 부품·배선·리본 헤더를 두지 않아야 한다(BRD-01은 지킴). 기판 배치를 이미 만들었다면 이 띠를 옮겨야 한다. 홈을 못 내면 화음 자리가 196 N/mm로 돌아가 r4.0의 화음 들림(1.3~1.4 m/s 0.23)이 되살아난다.", (G["solved"]["fins"][2][1] - G["solved"]["fins"][2][0] + 2 * PR["board_slot_clear"], PR["board_slot_y1"] - PR["board_y"][0], G["solved"]["fins"][2][0] - PR["board_slot_keepout"], G["solved"]["fins"][2][1] + PR["board_slot_keepout"], PR["board_y"][0], PR["board_slot_y1"] + PR["board_slot_keepout"])),
    pf("**제어 기판 인터페이스(r4.3, 회로 쪽 확인 필요).** (1) USB-C 케이블 몰드는 %.1f × %.1f × 25(z%.1f~%.1f) 이하여야 한다. 지금 구매 목록의 Coms NA993은 몰드 치수가 공개되지 않아 확인이 안 된다. "
    "몰드가 실측으로 확인되고 한계 안에 드는 CVILUX DH-20M50052로 바꾸기를 권한다(1d-3장, +27,784원). 받은 선은 캘리퍼·C13a 게이지·시험 19로 확인한다. "
    "(2) RP2040-Zero 윗면 부품과 헤더 핀 끝은 z%.1f 이하, 기판 뒤끝 y%.1f~%.1f 띠의 모든 것은 z%.1f 이하여야 한다(선반 밑면 z%.2f와 1.3). "
    "(3) EXT 선(O1·O7)은 아랫면 납땜 → 기판 밑 → USB 터널 플러그 밑으로만 나갈 수 있다(J302 뒤 선반 밑 칸은 뒷벽이 막힘). "
    "(4) 금지 구역 x%.2f~%.2f, y%.1f~%.1f(만능기판 위 핀·패드·배선; r4.4: 제로 PCB만 y172.0~173.2에 걸침 — P23). (5) F·F# 쉼 펠트가 %s만 앉아 두 건반이 약 0.1 높게 쉬므로 펀칭으로 맞춘다. "
    "(6) F|F# 핀 밑면(z%.1f)이 발 뒤 y%.1f에서 뒷벽 y%.0f까지 %.1f mm 다리(bridge)가 된다(r4.2는 얇은 선반까지 25.8 mm) — 윗판 밑 트리 서포트와 함께 받쳐 출력한다.", (PR["usb_x"][1] - PR["usb_x"][0], PR["usb_z"][1] - PR["usb_z"][0], PR["usb_z"][0], PR["usb_z"][1], PR["zero_z"][2], PR["comp_rear"][0], PR["board_y"][1], PR["comp_rear"][1], H["z_shelf"] - 2.0,
       G["solved"]["fins"][2][0] - PR["board_slot_keepout"], G["solved"]["fins"][2][1] + PR["board_slot_keepout"], PR["board_y"][0], PR["board_slot_y1"] + PR["board_slot_keepout"],
       " / ".join(pf("%s %.0f %%", (k_, 100 * v_["frac"])) for k_, v_ in R["r43"]["land"].items() if v_["frac"] < 1 - 1e-9),
       PR["comp_zmax"] + 1.5, PR["fin_slot_y"][1], 209.0, 209.0 - PR["fin_slot_y"][1]))
    + " (7) r4.4: 끝 부속 리드 W401·W411은 뒤 리브 틈 → 바닥 → 레일 밑 차선 → 뒷벽 홈으로만 나간다(EL은 A#0 흑 탭 받침 왼쪽); 리드를 차선 밖으로 두면 레일·뒷벽에 막힌다.",
    pf("**마찰 2배 DW %.1f / %.1f g은 55 g을 넘는다.** r3와 같은 수준이다. 단계 0 마찰이 계산의 2배에 가까우면 캡스턴 펠트에 PTFE 필름, 가이드 천을 얇게.", (W["DW_2f"], B["DW_2f"])),
    pf("**흑건 바닥이 부드럽다.** 1 N에서 흑건 앞이 펠트 위 %.2f mm에 멈추고 2 N에서 닿는다(레버가 패드에 먼저). 느낌 판정에서 거슬리면 흑 틈을 −0.3으로(ABUSE 들림 연구값 0.30).", H["held_pad_front_b"]),
    pf("**비틀림 스프링은 미스미 기성품(%s), 두 다리를 잘라 쓴다(r4.5).** 자른 다리 길이가 곧 강성이다(긴 다리 1 mm → k_t 약 %.1f %%). 자유각 공차가 ±5°를 넘으면 건반 뺀 레버(−31.3°)에서 다리가 홈 입구 앞 %.2f까지 나온다(입구 경사가 다시 받음; 단계 0 시험 9). "
       "r4.5 고침: 짧은 다리를 가둠 홈(폭 %.2f)에 넣어 예하중은 홈이 정한다 — 홈이 %.2f 넓게 나오면 쉼 토크 %.2f → %.2f N·mm(DW 약 %.1f g), 봉과 틈 %.2f; %.2f 좁으면 %.2f N·mm, 더 좁으면 선이 들어가지 않아 0.5 날로 다듬는다(시험 8·13). "
       "두 닿는 점(다리 끝·주머니 가장자리, 손 25°에서 %.2f N)의 PETG 모서리가 오래 눌려 크리프하면 쉼 토크가 조금 준다 — 시험 8의 1시간 뒤 다시 재기로 본다.",
       (PR["spring_cat"]["part"], 100 * (1.0 / (3 * math.pi * (PR["spring_ID"] + PR["spring_d"]))) / R["spring"]["N_e"], -LEG["C_+5"]["in_groove"], R["spring"]["capture"]["width"], 0.3, PR["spring_T0"], R["spring"]["capture_tol"]["+0.30"]["T0"],
        (PR["spring_T0"] - R["spring"]["capture_tol"]["+0.30"]["T0"]) * (W["DW"] - W["DW_nospring"]) / W["spring_T_rest"], R["spring"]["capture_tol"]["+0.30"]["gap_left"], 0.15, R["spring"]["capture_tol"]["-0.15"]["T0"],
        R["spring"]["capture"]["F_couple_hand"])),
    pf("**킬 뿌리와 밸런스 레일(r4.5 고침).** 화음 자리 %.1f N/mm는 레일 + 바닥 띠를 모듈 핀 선에서 받친 연속 보(앞 바닥판 없음)로 본 값이고 합격선 %.0f의 %.2f배다. 레일이 단단하면 %.1f, 해치 가장자리 고정이면 %.1f, 이웃 핀 선 사이 단순 지지만이면 %.1f(불합격). "
       "쓰임에서는 패드가 윗판을 밑에서 밀어 킬이 레일을 들어 올린다. 그래서 레일 밑 바닥 EVA는 레일을 돕지 못한다. 킬(z%.1f)과 핀 앞끝(y%.1f)은 이미 건반 F와의 1.3 한계라 더 키울 수 없다. "
       "첫 모듈 정하중(단계 0 시험 21)은 모듈을 C17a 받침 빗(핀 선과 뒷벽만 받침)에 얹고 위에서 눌러 쓰임과 같은 레일 휨을 잰다(r4.5 고침 3). %s 여섯 자리 × %.0f N에서 E·F 처짐은 모델 %.3f, 레일이 단단하면 %.3f, 단순 지지만이면 %.3f mm이고 합격은 ≤ %.2f mm다. "
       "넘으면 run_all의 화음 자리 강성 `k_ch`를 잰 값(60 N ÷ 처짐)으로 바꿔 화음 자리 동역학(들림 0.20, 키퍼, 유령)을 다시 보고, 불합격이면 리본 차선 위 레일(9 높이)이 원인이므로 회로 세션과 차선 높이를 다시 정한다.",
       (R["keel_rail"]["k_chord"], PR["seat_k_chord_req"], R["keel_rail"]["k_chord"] / PR["seat_k_chord_req"], R["keel_rail"]["k_chord_rigid"], R["keel_rail"]["k_chord_hatch"], R["keel_rail"]["k_chord_fins_span"],
        PR["fin_keel"][2], R["keel_rail"]["fin_front"], "-".join(S0C17["keys"]), S0C17["F"], S0C17["dead_seats"]["fins"]["EF"], S0C17["dead_seats"]["rigid"]["EF"], S0C17["dead_seats"]["fins_span"]["EF"], S0C17["limit"])),
    pf("**스프링 손 들기 토크가 카탈로그 55° 토크를 넘는다(r4.5).** 건반을 뺄 때 레버를 손으로 25°까지 들면 감긴 각 %.1f°는 카탈로그 최대 사용각 %.0f° 안이지만, 다리를 짧게 잘라 강성이 커서 토크 %.2f N·mm가 카탈로그 55° 토크 %.2f의 %.0f %%(응력 %.0f MPa, 카탈로그 한계 %.0f MPa, Su의 %.0f %%)다. "
       "11장 빼기 절차가 드는 각은 %.1f°(감긴 각 %.1f°, 토크 %.2f N·mm)라 카탈로그 55° 토크 이하이고, 55° 토크가 되는 레버 각은 %.1f°다 — 25°는 손으로 더 든 경우다. 영구 변형이 생기면 자유각이 줄어 쉼 토크가 준다. 단계 0 시험 8에서 25°로 1시간 둔 뒤 자유각 변화 ≤ 2°를 본다. 넘으면 들어올림을 %.1f° 아래로 지키라고 11장에 적는다.",
       (R["spring"]["states"]["hand 25 deg"]["wound"], PR["spring_cat"]["max_deg"], R["spring"]["states"]["hand 25 deg"]["T"], R["spring"]["cat"]["T_max"], 100 * R["spring"]["hand_over_cat"], R["spring"]["states"]["hand 25 deg"]["sigma"], R["spring"]["cat"]["sigma_max"],
        100 * R["spring"]["states"]["hand 25 deg"]["sigma"] / 2150, PR["BH"], PR["BH"] - PR["spring_free_deg"], PR["spring_kt"] * math.radians(PR["BH"] - PR["spring_free_deg"]),
        math.floor(10 * (math.degrees(R["spring"]["cat"]["T_max"] / PR["spring_kt"]) + PR["spring_free_deg"])) / 10, math.floor(10 * (math.degrees(R["spring"]["cat"]["T_max"] / PR["spring_kt"]) + PR["spring_free_deg"])) / 10)),
    pf("**패드 바를 곧게만 당기면** 끝에서 흑 패드 펠트 모서리가 흑건 윗면 턱과 %.2f(PET 심 3장이면 %.2f) — r4.2는 잎 돌기가 립을 떠나면 바가 0.3 내려앉기 때문. 절차(%.1f mm부터 밀어 올림)를 지키면 %.2f.", (sl_str, sl_str3, PR["bar_raise_pull"], sl_pr)),
    pf("**패드 바 잎 혀의 크리프(r4.2).** 잎(%.1f×%.1f×%.0f)이 %.1f 눌린 채 %.1f MPa(공차 +0.3이면 %.1f)로 늘 굽어 있어 2 MPa 크리프 선을 넘는다. PETG가 풀리면 예하중이 줄어든다: 두 잎의 힘은 처음에 패드 붙은 바 무게의 %.1f배라 반으로 풀려도 %.1f배, %.0f %% 넘게 풀려야 바가 0.3까지 처져 딸깍할 수 있다(동역학·틈에는 영향 없음, 소리만). 2 MPa 아래로 낮추면 휨이 0.01 mm대라 FDM 공차를 못 받는다. 단계 0 시험(40 °C 1주)으로 보고, 늘어지면 잎 두께 0.8 또는 손 맞춤.", (PR["bar_leaf"][0], PR["bar_leaf"][1], PR["bar_leaf"][2], PR["bar_leaf"][3], R42["gaps_module"]["leaf_sigma"], R42["gaps_module"]["leaf_sigma_max_tol"], LEAF_X, LEAF_X / 2, 100 * (1 - 1 / LEAF_X))),
    pf("**끝 부속 쐐기 얇은 끝(r4.2).** A0 %.2f, C8 %.2f로 설계 최소 0.3 아래다(한 층 0.2 이상이라 출력은 됨). 출력이 안 되면 끝 부속 패드 바의 그 건반 자리만 바 밑면을 0.1 올려(바 1.4T) 쐐기를 0.1 두껍게 한다 — 패드 면은 그대로.", (ESt["A0"]["wedge"][0], ESt["C8"]["wedge"][0])),
    pf("**윗판 밑 서포트 %.0f g/모듈.** 핀 사이 브리지 출력이 되면 없앨 수 있다.", MA["support_plate_g"]),
    pf("**강철 블록은 접착으로 잡는다(r4.4 고침 2).** 스냅 립만으로는 옆벽(r4.4 고침 2b부터 0.7)이 버티지 못한다: 매 음 %.1f N에 립 선이 한쪽 %.2f~%.2f 벌어지고(물림 1.0, 판 모델의 앞·뒷벽 받침 고정 ~ 핀) 옆벽 립 뿌리가 층 안 %.1f MPa(한계 12), 아래 립 뿌리 층간 %.1f MPa(한계 5). "
       "그래서 두 옆면을 MS 폴리머(탄성)로 붙인다(r4.4 고침 2b; 5분 에폭시는 열팽창 차이로 떨어짐): 전단 매 음 하중 %.3f + 열 %.3f MPa(허용 %.2f). PETG 부착 강도(설계 %.1f MPa)와 G 약 %.0f MPa는 가정이다 — 단계 0 시험 20(온도 순환 포함). 접착이 떨어지면 강철이 아래로 빠져 건반 빔 위에 걸린다(날아가지 않음). 강철을 바꾸려면 캐리어를 새로 뽑는다(20분).",
       (R["steel_retention"]["peaks"]["play"]["B"], R["steel_retention"]["wall_plate"]["play_a0.50_clamped"]["spread_max"], R["steel_retention"]["wall_plate"]["play_a0.50_pinned"]["spread_max"],
        R["steel_retention"]["wall_plate"]["play_a0.50_pinned"]["s_root"], R["steel_retention"]["peaks"]["play"]["sig_bottom"], R["steel_retention"]["bond"]["play"]["tau_mech"], R["steel_retention"]["bond"]["play"]["tau_th"], R["steel_retention"]["bond"]["play"]["limit"], _M4.P["bond_tau"], _M4.P["bond_G"])),
    pf("**축 놀음이 줄었다(r4.4 고침 2).** 칼라 한 개 %.2f 이상·핀 보스 +%.2f로 칸 놀음이 %s. 가장 좁은 A 칸(%.2f)에서 레버가 제 무게로 돌지 않으면 칼라 면을 사포질한다.",
       (_M4.P["collar_min"], _M4.P["boss_extra"], " / ".join(pf("%.2f", q_) for q_ in R["axial_play"]), min(R["axial_play"]))),
    pf("**F·F# 쉼 펠트 착지(r4.4).** F는 여전히 %.0f %%만 앉는다(흰 꼬리 폭 = 빔, 쉼 발은 뽑기 때 E와 부딪혀 기각). F#는 %.0f %%로 늘었지만 쉼 반력이 레버 선에서 %+.2f로 멀어져 굴림 되돌림/넘김 비 %.2f(r4.3 %.2f), 착지 짝힘 상한 %.2f N(r4.3 %.2f)이 탭 천으로 간다. "
    "ABUSE 복귀 넘침(2.0 m/s 화음, 요청한 화음 자리 2.5 m/s)에서는 F·F# 틈이 %.2f(공차 뒤 %.2f)까지 줄지만 닿지 않는다. 단계 0 시험 10의 화음 타건을 F~A# 칸에서도 본다.", (100 * R["r44"]["land"]["F"]["frac"], 100 * R["r44"]["land"]["F#"]["frac"], R["r44"]["land"]["F#"]["dx"], ST["roll"]["F#"]["ratio_rest"], R43M["stress"]["roll"]["F#"]["ratio_rest"],
       Q43["land_tab"]["F#"]["tab_N"], R43M["r43"]["land_tab"]["F#"]["tab_N"], CL["over_brief"]["d"], CL["over_brief"]["d"] - 0.3)),
]
_kd = S0["tests"]["3"]["design"]
_zt = H["z_top"]
risks += [
    pf("**화음 자리 여유 %.1f %%(r4.4 단계 0 키트에서 드러남).** 6건반 화음 자리 %.0f N/mm는 합격선 %.0f의 %.2f배다. 출력한 윗판의 실효 E가 %.0f MPa(모델 %.0f의 %.1f %%)보다 낮으면 합격선 아래로 간다. "
       "시험 1 다음에 시험 3a(C03a 굽힘 띠)를 한다. 낮으면 윗판 채움 100 %%, 그래도 낮으면 윗판을 +0.6 / +1.2 두껍게 한다(FE 화음 자리 %.0f / %.0f N/mm, z_top %.2f / %.2f). "
       "+1.2는 높이 목표 z74를 %.2f 넘으므로 +%.2f까지만 쓴다. 키트 파일(`stage0_procedure.md`·`stage0_geometry.json`)의 ‘z_top 73.4 / 74.0’은 고침 2 전 z_top 72.80 기준이라 17.1장 표에서 고쳐 적었다.",
       (100 * (1 - S0R), _kd["seat_k_chord"], PR["seat_k_chord_req"], SEAT["k_chord"] / PR["seat_k_chord_req"], S0E * S0R, S0E, 100 * S0R, S0KD["0.6"], S0KD["1.2"], _zt + 0.6, _zt + 1.2,
        _zt + 1.2 - 74.0, 74.0 - _zt)),
    pf("**벤치 지그는 프레임 한 대의 자리만 재현한다(r4.4 출력 공구).** 지그와 7개 모듈 프레임을 같은 프린터·같은 층 설정으로 뽑아야 쉼 선반과 봉 높이가 같은 층에서 반올림된다. "
       "공구와 단계 0 키트는 r4.4 고침 2 모델(`MODEL_DIR=final`)로 다시 만들었다(공구의 캡스턴 y와 모델 차이 %+.2f / %+.2f).", (W["y_cap"] - TL["model_values"]["caps"]["white"], B["y_cap"] - TL["model_values"]["caps"]["black"])),
    pf("**출력 공구와 단계 0 키트는 아직 뽑아 본 적이 없다(r4.4).** 치수는 모델에서 나오지만 층 반올림과 수축은 첫 출력에서 캘리퍼로 본다(10.1장 쓰는 법 5, `stage0/stage0_procedure.md` 출력 설정). "
       "키트 무게 약 %.0f g과 시간 약 %.0f시간은 채움 계수로 낸 추정이다(속을 꽉 채우면 %.0f g).", (S0EST, S0EST / 15.0, S0G)),
]
for r_ in risks:
    w("- " + r_)
w()

# ============================================================================================ 19
w("## 19. 파일")
w()
w("- `model_v4.py` — 단일 모델 (r4.0 조각은 `src/`; r4.1 고침은 `model_v4.py`에 바로 넣었고 `src/`는 r4.0 그대로). `run_all.py` — 모든 계산. `export_geo.py` — geometry.json. `make_design_md.py` — 이 문서.")
w("- r4.0 결과 보관: `geometry.r4_0.json`, `work_r4r1/*.r4_0.*`. r4.1 탐색 스크립트: `work_r4r1/`. r4.1 결과 보관: `geometry.r4_1.json`, `work_r4r2/*.r4_1.*`; r4.2 고침 스크립트·검사: `work_r4r2/`. "
  "r4.2 결과 보관: `geometry.r4_2.json`, `work_r4r3/*.r4_2.*`; r4.3 고침(회로 인터페이스) 패치: `work_r4r3/patch_*_r43.py`. "
  "r4.3 결과 보관: `geometry.r4_3.json`, `work_r4r4/*.r4_3.*`; r4.4 고침(남은 문제 1~3) 패치: `work_r4r4/patch_*_r44*.py`, 탐색 스크립트 `work_r4r4/x*.py`. "
  "r4.4 회로 대조 전 보관: `geometry.r4_4_pre_circuit.json`, `work_c44/*.r4_4_pre_circuit.*`; 회로 대조 검사 `model_v4.circuit_c44_checks`, 탐색 `work_c44/c*.py`.")
w("- `results.txt` · `metrics.json` · `geometry.json` · `parts_list.json` — 결과. r3는 `../final_r3/`, 도면 r3는 `../drawings_r3/`.")
w("- r4.4 `tools/` — 출력 공구(10.1장): `make_tools.py` 생성기, `tools.md` 설명, `tools_geometry.json`(치수 T01~T29, 옆모습·평면, 가짜 레버 하중·확대비, 틈 검사), `stl/` 4개, `scad/`, `png/`.")
w("- r4.4 `stage0/` — 단계 0 시험 키트(17.1장): `make_stage0.py`, `stage0_procedure.md` 절차, `stage0_geometry.json`(시편·합격선·결과 대응), `stage0_results_template.csv` 기록표, " + pf("`stl/` %s %d개 파일(%s)", (S0IDS, S0N, S0MUL or "모두 1개씩")) + ", `png/`, `scad/`.")
_dw = os.path.join(OUT, "..", "drawings")
_d1415 = sorted(f_ for f_ in (os.listdir(_dw) if os.path.isdir(_dw) else []) if re.match(r"d1[45]_.*\.svg$", f_))
w("- r4.4 `../cable/result.json`, `../cable/img/` — USB-C 케이블 조사(1d-3장). `../drawings/` — 도면 1~13(d01~d13 .svg/.png)"
  + (("과 r4.4 새 도면 " + ", ".join("`" + f_ + "`" for f_ in _d1415) + "(도면 세션).") if _d1415 else
     "과 r4.4 새 도면 14·15(도면 세션 담당 — 이 문서를 만들 때 아직 폴더에 없었다; 공구·키트 치수는 `tools/tools_geometry.json`·`stage0/stage0_geometry.json`)."))
w("- r4.4 문서 작업: `work_doc44/` — 반올림 도우미로 서식을 바꾼 스크립트 `pf_transform.py`, 패치 `patch_doc44_*.py`, 바꾸기 전 보관 `*.pre_doc44.*`, "
  "반올림으로 바뀐 칸 기록 `round_cells.json`(고침 2 전 모델), 새 서식 geometry.json을 만든 모델 사본 실행 `sb2/`와 비교 `cmp_sandbox2.json`(모델 수치 같음 확인). "
  "고침 2 뒤 다시 맞춤: `work_doc44/r3/` — `patch_doc44_r3.py`·`patch_doc44_r3b.py`(이 판의 글 고침), `patch_export_r3.py`(`pf`가 `%s` 실수도 줄임), `dims_cmp.py`·`run_md_old.py`·`build_round_cells.py` → `round_cells.json`(5장 머리, 지금 모델), 고치기 전 보관 `make_design_md.start.py`·`DESIGN.start.md`.")
if PL_STALE or _old:
    w("- 알려진 글 차이(다음 `run_all.py`에서 고칠 것): parts_list.json(`run_all.py`) — " + "; ".join(PL_STALE + ["사양 글은 아직 ‘%.2f’ 서식", "metrics `spare_bay.mass_kg`는 강철 블록을 4개로 셈(부품표 예비 2)"]) +
      ("; geometry.json 글(`export_geo.py`) — " + ", ".join(o_.split(" → ")[0] for o_ in _old) if _old else "") + ".")
w("- r4.4 고침 2: 고치기 전 보관 `geometry.r4_4a.json`, `work_f2/*.pre_f2`; 패치 `work_f2/patch_*_f2.py`, 탐색 `work_f2/t*.py`, 옆벽 판 모델 `model_v4.carrier_wall_plate`; 첫 전체 실행 기록 `work_f2/*.run1.*`(끝 부속 A#0 블록 ↔ 레일 1.20이 남아 포켓 x 구간을 블록 ± 받침 틈으로 넓히고 다시 돌림).")
w("- r4.5 회로 2차 대조: 고치기 전 보관 `geometry.r4_5c.json`, `work_r45d/*.pre.py`; 패치 `work_r45d/patch_*.py`, 긴 유령 시험 `work_r45d/t_ghost.py`, 고침 확인 `work_r45d/t_fix.py`; 결과 `metrics.json`의 `c45`·`ghost_summary`, geometry.json의 `circuit_r45`.")
w("- geometry.json에 합친 도면 쪽 고침: " + "; ".join(G["patches_merged"]) + ".")
w()

open(os.path.join(OUT, "DESIGN.md"), "w").write("\n".join(L) + "\n")
print(pf("wrote DESIGN.md (%d lines)", len(L)))
