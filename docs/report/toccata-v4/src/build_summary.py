"""Build src/summary.html: the '요약 · 한눈에 보기' tab (section #p-summary) of the Toccata v4 page, final state.

Every number on the tab is read from a source file and checked here; nothing is typed in by hand except the schedule
(dates from the semester plan / deck v8 slide 21) and plain-language wording.

  purchases     docs/report/toccata-v4/data/final_items.json  (build_items.py; plan C order list of 2026-10-08)
  key action    hardware/mechanical/key-action-v4/model/metrics.json  (W1+ r4.5)
  body/speaker  hardware/mechanical/cad/spec/body_L2.json  (L2, baffle 40 deg)
  touchscreen   hardware/mechanical/touchscreen/rev3/design/numbers.json  (rev 3, Waveshare 7-DSI-TOUCH-C)
  circuit       hardware/pcb/netlist/sheets.json (revision, per-sheet checks), README.md (title/'- 개정:' line, power budget row 17),
                hardware/pcb/netlist/bom.csv, schematic/, board/
  prep lines    docs/report/toccata-v4/fin/prep/lines.json (build_prep.py; counted lines A + B + C, tools D)
  print files   hardware/mechanical/cad/stl/print/<folder>/<name>__<N>개.stl
  CAD solids    build_all.collect() (in memory only, never build_all.main()) - skip with --no-cad

usage: python3 docs/report/toccata-v4/src/build_summary.py [--no-cad]
output: docs/report/toccata-v4/src/summary.html = one <style> block + <section class="page" id="p-summary" hidden>.
The prep tab script fills <div id="sum-prep"></div>; while it is empty the static empty state next to it is shown.
"""
import csv
import glob
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(V4, "..", "..", ".."))
CAD = os.path.join(REPO, "hardware", "mechanical", "cad")
PCB = os.path.join(REPO, "hardware", "pcb")


def rp(*a):
    return os.path.join(REPO, *a)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


W = lambda v: f"{v:,}"
E = html.escape
problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


# ------------------------------------------------------------------ purchases (plan C, ordered 2026-10-08)
FI = load(os.path.join(V4, "data", "final_items.json"))
T = FI["totals"]
EXPECT = {"school_items": 215852, "school_ship": 28700, "personal": 342631, "total": 587183, "budget_school": 200000}   # 10/16 A안 (+PETG 4, +세메다인 1)
for k, v in EXPECT.items():
    check(T[k] == v, f"totals.{k} = {T[k]} (expected {v})")
check(T["school_items"] + T["school_ship"] + T["personal"] == T["total"], "school + ship + personal != total")
check(T["personal_items"] + T["personal_ship"] == T["personal"], "personal items + ship != personal")
check(T["budget_school"] - T["school_items"] == T["school_left"], "school_left mismatch")
check(T["xlsx"] == {"school_items": T["school_items"], "school_ship": T["school_ship"], "personal": T["personal"], "total": T["total"]},
      "final_items totals differ from the xlsx totals recorded in it")
school_all = T["school_items"] + T["school_ship"]
items = FI["items"]
by_src = {}
for it in items:
    by_src.setdefault(it["source"], []).append(it)
cnt = {k: len(v) for k, v in by_src.items()}
check(cnt == FI["counts"]["by_source"], f"source counts {cnt} != counts.by_source {FI['counts']['by_source']}")
check(cnt.get("school") == T["school_lines"] == 29, "school lines")   # 10/14: L66 엘레파츠, SE4 디바이스마트 (학교, 한도 7,852원 초과)
check(cnt.get("personal") == T["personal_lines"] == 19, "personal lines")   # 10/14: + USB NA993 i022, HB466 i226, touchscreen i202 (AliExpress); 10/16: - 합판 i096, 목공본드 i057
check(sum(it["ordered"]["amount"] for it in by_src["school"]) == T["school_items"], "school item amounts != school_items")
check(sum(it["ordered"]["amount"] for it in by_src["personal"]) == T["personal_items"], "personal item amounts != personal_items")
n_check = sum(1 for it in items if not it["optional"])
n_opt = len(items) - n_check
check(n_check == FI["counts"]["checklist"], "checklist line count")
# ------------------------------------------------------------------ prep checklist lines (07 tab, fin/prep/lines.json)
PL = load(os.path.join(V4, "fin", "prep", "lines.json"))
PT = PL["totals"]
PG = {g["id"]: g for g in PL["groups"]}
check(set(PG) == {"parts", "prints", "make", "tools"}, f"prep groups {sorted(PG)}")
check(PT["main_lines"] == PT["parts"]["counted"] + PT["prints"]["counted"] + PT["make"]["counted"], "prep main_lines != A + B + C")
check(PT["all_lines"] == len(PL["lines"]) == sum(PT[g]["lines"] for g in ("parts", "prints", "make", "tools")), "prep all_lines")
check(PT["parts"]["counted"] + PT["tools"]["counted"] == n_check, f"prep A + D counted != final_items checklist {n_check}")
check(PT["parts"]["lines"] + PT["tools"]["lines"] == len(items), "prep A + D lines != final_items total")
PREP_MAIN = PT["main_lines"]
PREP_OPT = PT["parts"]["optional"] + PT["prints"]["optional"]
PREP_SUM = " + ".join(f"{PG[g]['name']} {PT[g]['counted']}" for g in ("parts", "prints", "make")) + f" = {PREP_MAIN}줄"
PREP_TOOLS = f"{PG['tools']['name']} {PT['tools']['counted']}줄"

gaps = by_src.get("gap", [])
aircon_issue = next((i for i in FI["issues"] if i["id"] == "aircon"), None)
gap_issue = next((i for i in FI["issues"] if gaps and i["id"] == gaps[0]["id"]), None)

# ------------------------------------------------------------------ key action (W1+ r4.5)
MT = load(rp("hardware", "mechanical", "key-action-v4", "model", "metrics.json"))["metrics"]
dw_w, dw_b = round(MT["dw_white_g"], 1), round(MT["dw_black_g"], 1)
uw_w, uw_b = round(MT["uw_white_g"], 1), round(MT["uw_black_g"], 1)
rep_w, rep_b = round(MT["rep_hz_white"], 1), round(MT["rep_hz_black"], 1)
check((dw_w, dw_b) == (51.9, 51.0), f"DW {dw_w}/{dw_b}")

# ------------------------------------------------------------------ body + speakers (L2, 40 deg)
B = load(os.path.join(CAD, "spec", "body_L2.json"))
ov = B["overall"]
width = ov["x"][1] - ov["x"][0]
depth = ov["y"][1] - ov["y"][0]
spk_top = ov["z_max"]
behind = ov["depth_behind_keys"]
ang = B["speakers"]["baffle"]["angle_from_horizontal_deg"]
vol = B["speakers"]["inner_volume"]["gross_L"]
check((width, depth, spk_top, ang) == (1254.0, 342.5, 144.65, 40.0), f"body {width} x {depth}, z{spk_top}, {ang} deg")
check(abs(vol - 2.16) < 0.005, f"speaker volume {vol}")
DRIVER = "CW-100B25" if "CW-100B25" in B["speakers"]["driver"]["model"] else B["speakers"]["driver"]["model"]
LID_TOP = 72.85                                    # checked against LID-L / LID-R / O*-FRAME solids below

# ------------------------------------------------------------------ touchscreen (rev 3)
N = load(rp("hardware", "mechanical", "touchscreen", "rev3", "design", "numbers.json"))
tilt = N["hinge"]["tilt_use_deg"]
ax_y, ax_z = N["hinge"]["axis_yz"]
fold_top = N["folded_top"]
check(tilt == 25.0 and (ax_y, ax_z) == (226.55, 81.35), "touchscreen hinge")
check("1024x600" in N["screen"]["model"] and "7-DSI-TOUCH-C" in N["screen"]["model"], "touchscreen model")

# ------------------------------------------------------------------ circuit (revision + power budget)
# Revision and per-sheet check results come from hardware/pcb/netlist/sheets.json (written by hardware/pcb/src/build.py);
# the README title line and its '- 개정:' history line must agree with it.
readme = open(os.path.join(PCB, "README.md"), encoding="utf-8").read()
SHEETS = load(os.path.join(PCB, "netlist", "sheets.json"))
REV, REV_DATE = max((s["rev"], s["date"]) for s in SHEETS.values())
sheet_err = {k: s["checks"] for k, s in SHEETS.items() if any(v != 0 for v in s["checks"].values())}
check(not sheet_err, f"circuit sheets with check results != 0: {sheet_err}")
m_title = re.search(r"^# .*— 개정 ([A-Z])\s*$", readme, re.M)
check(bool(m_title) and m_title.group(1) == REV, f"README title revision {m_title.group(1) if m_title else '?'} != sheets.json {REV}")
rev_line = next((ln for ln in readme.splitlines() if ln.startswith("- 개정:")), "")
revs = re.findall(r"\b([A-Z]) (?:(\d{4})-)?(\d{2})-(\d{2})\b", rev_line)
check(bool(revs), "circuit revision line ('- 개정:') not found in hardware/pcb/README.md")
if revs:
    r_last = revs[-1]
    check((r_last[0], f"{r_last[2]}-{r_last[3]}") == (REV, REV_DATE[5:]),
          f"README '- 개정:' last entry {r_last} != sheets.json {REV} {REV_DATE}")
# the power budget (battery input, R33) was set in revision D (README row 17); no later row may restate it
later_power = [ln[:12] for ln in readme.splitlines() if re.match(r"\| (1[89]|2\d) \|", ln) and re.search(r"평균 약 [0-9.]+~[0-9.]+ W|연주 시간|[0-9.]+ Wh", ln)]
REV_LABEL = f"개정 {REV} ({int(REV_DATE[5:7])}/{int(REV_DATE[8:10])})"
check(not later_power, f"README rows after 17 restate the power budget: {later_power}")
row17 = next((ln for ln in readme.splitlines() if ln.startswith("| 17 |")), "")
m_avg = re.search(r"평균 약 ([0-9.]+)~([0-9.]+) W", row17)
m_peak = re.search(r"순간 최대 약 ([0-9.]+) W", row17)
m_life = re.search(r"약 ([0-9.]+)~([0-9.]+)시간", row17)
check(bool(m_avg and m_peak and m_life and "76.8 Wh" in row17), "power budget in README row 17")
P_AVG = f"{m_avg.group(1)}~{m_avg.group(2)}" if m_avg else "?"
P_PEAK = m_peak.group(1) if m_peak else "?"
P_LIFE = f"{m_life.group(1)}~{m_life.group(2)}" if m_life else "?"
check(P_LIFE == "3.5~4.4", f"battery life {P_LIFE}")
n_sch = len(glob.glob(os.path.join(PCB, "schematic", "SCH-*.svg")))
n_brd = len(glob.glob(os.path.join(PCB, "board", "BRD-*.svg")))
check((n_sch, n_brd) == (sum(k.startswith("SCH-") for k in SHEETS), sum(k.startswith("BRD-") for k in SHEETS)),
      f"sheet SVGs {n_sch} + {n_brd} != sheets.json {len(SHEETS)}")
check(n_sch >= 7 and n_brd >= 6, f"sheets {n_sch} + {n_brd}")
m_conn = re.search(r"(\d+)장 모두 연결 오류 0", readme)
check(m_conn is not None, "connectivity check line ('N장 모두 연결 오류 0') in hardware/pcb/README.md")
CONN_N = int(m_conn.group(1)) if m_conn else 0
check(CONN_N == n_sch + n_brd == len(SHEETS), f"README connectivity check covers {CONN_N} sheets; folders hold {n_sch} + {n_brd}")
bomq = {"DRV5055": 0, "RP2040-Zero": 0, "4067": 0}
with open(os.path.join(PCB, "netlist", "bom.csv"), encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        for k in bomq:
            if r["값"].startswith(k) or (k == "4067" and r["값"].startswith("CD74HC4067")):
                bomq[k] += int(r["전체 수량"])
check(bomq == {"DRV5055": 89, "RP2040-Zero": 8, "4067": 7}, f"circuit bom {bomq}")

# ------------------------------------------------------------------ print files (stl/print)
TOOLS = {"06_출력공구"}
JIGS = {"08_합판지그", "09_기판지그"}   # 08 gone since 2026-10-16 (A안: no plywood)
pf = {"inst_files": 0, "inst_parts": 0, "tools": 0, "jigs": 0}
for f in glob.glob(os.path.join(CAD, "stl", "print", "*", "*.stl")):
    folder = os.path.basename(os.path.dirname(f))
    m = re.search(r"__(\d+)개\.stl$", f)
    q = int(m.group(1)) if m else 1
    if folder in TOOLS:
        pf["tools"] += q
    elif folder in JIGS:
        pf["jigs"] += q
    else:
        pf["inst_files"] += 1
        pf["inst_parts"] += q
# 10/16 A안: + 판 10장 (12 파일), - 합판 지그 7; 10/29 A12: + 레버틀 3 파일 (9), 가이드 탭 2 파일 (88), 레버 덮개 1 파일 (88)
check(pf == {"inst_files": 98, "inst_parts": 495, "tools": 4, "jigs": 2}, f"stl/print {pf}")
S0 = load(rp("hardware", "mechanical", "key-action-v4", "printables", "stage0", "stage0_geometry.json"))
s0_files = len(glob.glob(rp("hardware", "mechanical", "key-action-v4", "printables", "stage0", "stl", "*.stl")))
s0_pieces = sum(p["qty"] for p in S0["parts"])
s0_tests = [k for k in S0["tests"] if k.isdigit()]
s0_extra = [k for k in S0["tests"] if not k.isdigit()]
check((len(S0["parts"]), s0_files, s0_pieces, len(s0_tests), len(s0_extra)) == (34, 34, 36, 21, 3),
      f"stage0 {len(S0['parts'])} parts / {s0_files} stl / {s0_pieces} pcs / {len(s0_tests)}+{len(s0_extra)} tests")
check("약 8 W/ch" in row17, "amp 8 W/ch at 12.8 V")
check(not any(it["id"] in ("i096", "i057") for it in items), "plywood sheet and wood glue dropped (10/16 A안)")

# ------------------------------------------------------------------ CAD solids (optional, ~4 s)
n_cad = 1567                                       # 10/29 A12 +185 (레버틀 9, 가이드 탭 88, 레버 덮개 88), 10/30 A13 -88 (캡스턴 너트), A14 +3 (유리 턱 띠 L·R + 접은 보기)
SCREEN_UP_TOP = 189.23                             # CAD value (max z of the TS-* solids in the use pose); re-measured below
if "--no-cad" not in sys.argv:
    sys.path.insert(0, os.path.join(CAD, "src"))
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))
    import build_all  # noqa: E402  (collect() only; build_all.main() would wipe stl/print)
    parts = build_all.collect()
    n_cad = len(parts)
    check(n_cad == 1567, f"CAD parts {n_cad}")
    P = {p.id: p for p in parts}
    use = [p for p in parts if not (p.note or "").startswith("altview") and p.id != "PEDAL-DAMPER"]
    bb = [p.solid.bounding_box() for p in use]
    x0, y0 = min(b[0] for b in bb), min(b[1] for b in bb)
    x1, y1 = max(b[3] for b in bb), max(b[4] for b in bb)
    check((round(x0, 2), round(x1, 2), round(y0, 2), round(y1, 2)) == (-16.0, 1238.0, 0.0, 342.5), f"CAD footprint {x0} {x1} {y0} {y1}")
    for pid in ("LID-L", "LID-R", "O1-CAGE", "O7-CAGE"):           # A12: the top plate is on the lever cage
        check(abs(P[pid].solid.bounding_box()[5] - LID_TOP) < 0.01, f"{pid} top z")
    check(abs(P["SPKL-PLY-SIDEOUT"].solid.bounding_box()[5] - spk_top) < 0.01, "speaker top z")
    check(abs(P["TS-CRADLE-FOLD"].solid.bounding_box()[5] - fold_top) < 0.01, "folded screen top z")
    ts_up = max(p.solid.bounding_box()[5] for p in use if p.id.startswith("TS-"))
    check(abs(ts_up - SCREEN_UP_TOP) < 0.01, f"screen up top z {ts_up}")
    SCREEN_UP_TOP = round(ts_up, 2)
    keys = [p for p in parts if re.search(r"-KEY-", p.id) and p.kind == "print"]
    check(len(keys) == 88, f"keys in CAD {len(keys)}")
    check(sum(1 for p in parts if p.kind == "plywood") == 0, "no plywood pieces in CAD (10/16 A안)")
    bat = P["BAT-LFP"].solid.bounding_box()
    check(tuple(round(bat[i + 3] - bat[i], 2) for i in range(3)) == (140.0, 72.0, 35.0), "battery box")

if problems:
    print("CHECK FAILED:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

# ================================================================== page text
SPEC = [
    ("건반", "88건반", "A0~C8 · 옥타브 모듈 7개(12건반씩) + 끝 부속 2개(A0·A#0·B0 / C8)"),
    ("본체 크기", f"{width:g} × {depth:g} mm", f"폭 × 깊이 · 건반 뒤 뒷바 {behind:g} mm"),
    ("높이", f"z{LID_TOP:g} · z{spk_top:g}", f"가운데 뚜껑 윗면(건반 모듈 뒷벽과 같은 높이) · 스피커 윗면"),
    ("누르는 힘", f"{dw_w:.1f} / {dw_b:.1f} g", f"백건 / 흑건 · 올라오는 힘 {uw_w:.1f} / {uw_b:.1f} g · 연타 {rep_w:.1f} / {rep_b:.1f} Hz"),
    ("화면", "7인치 1024×600", f"Waveshare 7-DSI-TOUCH-C · {tilt:g}° 세움(꼭대기 z{SCREEN_UP_TOP:g}) · 접으면 z{fold_top:g}"),
    ("전원", "LiFePO4 12.8 V 6 Ah", f"76.8 Wh · 평균 {P_AVG} W, 순간 최대 {P_PEAK} W · 약 {P_LIFE}시간"),
    ("스피커", f"4인치 × 2 · 앞판 {ang:g}°", f"{DRIVER} 8 Ω · 밀폐 {vol:.2f} L · TPA3110 12.8 V에서 약 8 W/채널"),
    ("회로", REV_LABEL,
     f"회로도 {n_sch}장 + 기판·배선도 {n_brd}장 · 자동 검사 {CONN_N}장 모두 오류 0 · 홀센서 {bomq['DRV5055']} · RP2040-Zero {bomq['RP2040-Zero']}"),
    ("출력 (합판 없음)", f"{pf['inst_files']}종 {pf['inst_parts']}개",
     f"악기 출력 STL(PETG) · 공구 {pf['tools']} · 지그 {pf['jigs']} · 10/16부터 뒷바 판도 모두 출력 (가운데 아랫판·뒤판은 반턱 3토막)"),
]
spec_html = "".join(f'<div class="sum-kv"><span class="sum-k">{E(a)}</span><b class="sum-v">{E(b)}</b>'
                    f'<span class="sum-d">{E(c)}</span></div>' for a, b, c in SPEC)

MAPS = [
    ("circuit", "01", "회로도", f"파트별 상세 회로도 {n_sch}장(시스템·센서 기판·제어 기판·끝 부속·페달·전원·오디오)과 기판 배치·배선도 {n_brd}장. 핀 번호까지 확대해 봅니다."),
    ("dwg", "02", "설계도", "앞·뒤·위·아래·왼쪽·오른쪽 6방향 외형도와 내부 단면도. 치수는 CAD 입체에서 잰 mm 값입니다."),
    ("partdwg", "03", "부품 도면·출력 파일", f"출력 부품마다 치수 도면과 STL. 악기 {pf['inst_files']}종 {pf['inst_parts']}개 + 공구 {pf['tools']} + 지그 {pf['jigs']}."),
    ("cad", "04", "3D 모델", f"설계도와 같은 CAD 모델(부품 {W(n_cad)}개)을 돌려 보며 파트별로 봅니다."),
    ("sim", "05", "동작 시뮬레이션", "건반을 누를 때 레버·스프링·자석이 움직이는 모습과 센서 값의 변화."),
    ("parts", "06", "부품·사용처", f"최종 물건 {len(items)}줄의 사진·규격·개수와, 모델 위에 표시한 들어가는 자리."),
    ("prep", "07", "준비 체크", f"물건·출력물·가공 줄마다 필요한 개수 중 준비한 개수를 적고 전체 준비율을 봅니다({PREP_SUM})."),
    ("design", "08", "건반 액션 원리", "시소 건반 + 강철 무게 레버 + 비틀림 스프링(W1+ r4.5)의 구조와 누르는 힘."),
    ("build", "09", "출력·조립", "출력 순서와 설정, 모듈부터 본체까지 조립 순서."),
    ("check", "10", "검증·남은 위험", "자동 검사 결과, 단계 0 시험 21가지, 아직 남은 위험."),
]
maps_html = "".join(
    f'<a class="sum-map" href="#{tid}"><span class="sum-mapno">{no}</span><span class="sum-mapbody">'
    f'<b>{E(t)}</b><span>{E(d)}</span></span><span class="sum-maparr" aria-hidden="true">→</span></a>'
    for tid, no, t, d in MAPS)

SRC_TILES = [
    ("school", "학교 지원 구매", f"물건값 {W(T['school_items'])}원"),
    ("personal", "사비 구매", f"물건값 {W(T['personal_items'])}원"),
    ("owned", "가진 것", "Pi 5·화면·배터리·허브·앰프·PETG 등"),
    ("tool", "가진 공구", "인두·드릴·캘리퍼스 등"),
    ("gap", "준비처 없음", "바로 아래 안내"),
]
src_html = "".join(f'<div class="kf sum-kf{" sum-kf-gap" if k == "gap" and cnt.get(k) else ""}"><b>{cnt.get(k, 0)}<small>줄</small></b>'
                   f'<span class="sum-kfl">{E(lab)}</span><span class="sum-kfd">{E(d)}</span></div>' for k, lab, d in SRC_TILES if k != "gap" or cnt.get(k))

gap_html = ""
if gaps:
    g = gaps[0]
    gap_html = (f'<div class="note warn sum-gap" id="sum-gap"><b>아직 준비처가 없는 물건 {len(gaps)}줄.</b> '
                f'{E(g["name"])} {g["qty_need"]}{E(g["unit"])}({E(g["id"])}). '
                + ('센서 기판 띠(161.6 × 15.24 mm) 7개와 끝 부속·J702·J501·페달 센서 조각을 이 판에서 자릅니다. '
                   '가진 Coms BE163(80 × 120)으로는 120 mm보다 긴 띠가 나오지 않으므로 따로 사야 합니다.'
                   if g["id"] == "i081" and "161.6 × 15.24" in g["where"] else E(g.get("check_on_arrival") or ""))
                + (' 예: 메카솔루션 양면 만능기판 2,200원 × 2.' if g["id"] == "i081" and gap_issue and "메카솔루션" in gap_issue["text"] else '')
                + ' 자세한 자리는 <a href="#parts">06 부품·사용처</a>에 있습니다.</div>')
aircon_html = ""
air_need = [it for it in by_src.get("aircon", []) if not it["optional"]]
air_opt = cnt.get("aircon", 0) - len(air_need)


def short(n):
    return re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)", "", n)).strip()


def need_str(it):
    """'<short name> <amount> (p<page of the aircon order>)'. A line cut from longer stock
    ('(... 2 m 중 52 mm)' in the name) shows the cut length, not '1가닥'."""
    nm = short(it["name"])
    cut = re.search(r"중\s*(\d+(?:\.\d+)?)\s*mm\)", it["name"])
    if cut:
        amt = f"{nm} {cut.group(1)} mm"
    elif it["unit"] == "m":
        amt = nm if re.search(r"\d m$", nm) else f"{nm} {it['qty_need']:g} m"
    else:
        amt = f"{nm} {it['qty_need']:g}{it['unit']}"
    pg = re.findall(r"\bp(\d+)\b", it.get("pack_note") or "")
    return amt + (f" (p{pg[0]})" if pg else "")



NEXT = [
    ("10/12 주 ~ 11/8", "단계 0 재료 시험",
     f"시편 {len(S0['parts'])}종 {s0_pieces}개(key-action-v4/printables/stage0)와 출력 공구 {pf['tools']}개를 먼저 뽑고 시험 {len(s0_tests)}가지와 확인 {len(s0_extra)}가지(밸런스 핀 압입·캡스턴 박기·펠트 두께; 캡스턴은 A13부터 너트 없이 첫 건반 빔에서)를 합니다. 9가지는 첫 모듈로 합니다."),
    ("11/1 무렵", "첫 옥타브 모듈 O4",
     "모듈 1개(출력 약 47시간)를 뽑아 조립·납땜하고 PC로 첫 소리를 냅니다. 시험 21(첫 모듈 정하중)을 통과하면 나머지를 뽑습니다."),
    ("10/26 ~ 12/6", "나머지 출력 약 380시간",
     "프린터 1대로 하루 약 11~13시간. 본체·스피커·화면 받침을 먼저, 모듈은 11월부터 뽑고 나오는 대로 조립합니다. 시간은 발표 일정표 어림이며 슬라이서 합계로 다시 봅니다."),
    ("12/13까지", "88건반 통합",
     "출력 판 상자·배터리·스피커·터치스크린을 붙이고 88건반 소리 시험을 합니다."),
    ("12/14 주", "발표·시연", "88건반 연주와 리듬게임 MVP(서장 + 1장)를 보여 줍니다."),
]
next_html = "".join(f'<li><span class="sum-when">{E(w)}</span><b class="sum-what">{E(t)}</b><span class="sum-how">{E(d)}</span></li>'
                    for w, t, d in NEXT)

CHECK = [
    ("배터리", "무부하 13.0~13.4 V인지, 선이 나오는 면·높이(가정: +x 끝면 y275 / y299, z34)와 DC 충전 커넥터 높이 8.85 mm 이하인지 봅니다. 다르면 배터리 틀(05)을 뽑기 전에 고칩니다."),
    ("충전기", "출력 표기가 14.4~14.6 V인 LiFePO4용인지 봅니다. 납축·리튬이온용은 쓰지 않습니다."),
    ("퓨즈 홀더", "40.1 × 11.1 × 33.8 mm, 꼭지 Ø8가 받침(Ø8.3)에 눌러 끼워지는지 봅니다. 퓨즈는 5 A ATO 칼날형입니다."),
    ("화면", "뒷면 DSI 커넥터 방향과 외곽 166.10 × 101.00 mm를 봅니다. 화면 받침(07)은 실물을 본 뒤 뽑습니다."),
    ("허브 DC 플러그", "곧은 플러그가 잭 면에서 32 mm 이하인지 봅니다. 길면 ㄱ자 DC 플러그 선이 따로 필요합니다."),
    ("PORON", "두께 5 mm면 stl/print/04의 패드 바를 그대로 뽑습니다(5T용으로 만듦). 6T가 오면 stl/print_extra의 6T용 패드 바를 뽑습니다."),
    ("M4 열 인서트", "앞판용 바깥 Ø6 × 길이 4가 8개, 이음용 Ø6 × 6이 4개인지 봅니다. 출력 구멍 Ø5.6 × 6.5에 인두로 면까지만 넣습니다(드릴 구멍 없음)."),
]
check_html = "".join(f'<li><b>{E(a)}</b> {E(b)}</li>' for a, b in CHECK)

split_label = (f"학교 {W(school_all)}원(물건 {W(T['school_items'])} + 배송 {W(T['school_ship'])}), "
               f"사비 {W(T['personal'])}원(물건 {W(T['personal_items'])} + 배송 {W(T['personal_ship'])})")

CSS = r"""
#p-summary{--sum-a:var(--s1);--sum-b:var(--s2)}
#p-summary .sum-status{display:flex;flex-wrap:wrap;gap:6px 10px;margin:-8px 0 18px}
#p-summary .sum-status .pill{font-family:var(--mono);font-size:11.5px}
#p-summary .sum-status .pill.ok{border-color:var(--good);color:var(--good);background:var(--tint-green)}
#p-summary h3.sum-h{font-size:17px;margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--ink)}
#p-summary .sum-hero{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:16px;align-items:start}
@media (max-width:900px){#p-summary .sum-hero{grid-template-columns:minmax(0,1fr)}}
#p-summary .sum-hero>*{min-width:0}
#p-summary .sum-fig{margin:0;background:var(--card);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
#p-summary .sum-fig img{display:block;width:100%;height:auto;aspect-ratio:1800/1100;object-fit:cover}
#p-summary .sum-fig figcaption{font-size:12.5px;color:var(--ink-2);padding:8px 12px 10px;max-width:none}
#p-summary .sum-thumbs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--rule);border-top:1px solid var(--rule)}
#p-summary .sum-thumbs figure{margin:0;background:var(--card);min-width:0}
#p-summary .sum-thumbs img{display:block;width:100%;height:auto;aspect-ratio:1800/1100;object-fit:cover}
#p-summary .sum-thumbs figcaption{font-size:12px;color:var(--ink-3);padding:4px 10px 8px}
#p-summary .sum-side{display:flex;flex-direction:column;gap:12px}
#p-summary .sum-card{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:14px 16px;min-width:0}
#p-summary .sum-cardhead{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
#p-summary .sum-lab{font-size:12.5px;color:var(--ink-3)}
#p-summary .sum-big{font-family:var(--mono);font-size:32px;line-height:1.15;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;margin:2px 0 10px}
#p-summary .sum-big small{font-size:15px;margin-left:2px;color:var(--ink-2);font-weight:500}
#p-summary .sum-split{display:flex;gap:2px;height:14px;margin:0 0 10px}
#p-summary .sum-seg{display:block;min-width:4px}
#p-summary .sum-seg:first-child{border-radius:4px 0 0 4px}
#p-summary .sum-seg:last-child{border-radius:0 4px 4px 0}
#p-summary .sum-seg.a,#p-summary .sum-sw.a{background:var(--sum-a)}
#p-summary .sum-seg.b,#p-summary .sum-sw.b{background:var(--sum-b)}
#p-summary .sum-split:hover .sum-seg{opacity:.55}
#p-summary .sum-split .sum-seg:hover{opacity:1}
#p-summary .sum-cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media (max-width:420px){#p-summary .sum-cols{grid-template-columns:minmax(0,1fr)}}
#p-summary .sum-col{min-width:0}
#p-summary .sum-colh{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--ink-2)}
#p-summary .sum-sw{width:10px;height:10px;border-radius:2px;flex:none}
#p-summary .sum-colv{display:block;font-family:var(--mono);font-size:18px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;margin:1px 0 4px}
#p-summary .sum-col dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 8px;margin:0;font-size:12.5px}
#p-summary .sum-col dt{color:var(--ink-3)}
#p-summary .sum-col dd{margin:0;color:var(--ink-2);font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
#p-summary .sum-col dd small{font-family:var(--sans);color:var(--ink-3)}
#p-summary .sum-fine{font-size:12.5px;color:var(--ink-3);margin:10px 0 0;max-width:none}
#p-summary .sum-gapline{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--ink);background:var(--tint-amber);border-left:3px solid var(--amber);border-radius:0 8px 8px 0;padding:8px 10px;margin:10px 0 0}
#p-summary .sum-gapline a{color:var(--ink);font-weight:600}
#p-summary #sum-prep{min-width:0}
#p-summary #sum-prep:empty{display:none}
#p-summary #sum-prep:not(:empty)+.sum-prepempty{display:none}
#p-summary .sum-prepempty p{font-size:13.5px;color:var(--ink-2);margin:6px 0 10px}
#p-summary .sum-preptrack{height:10px;border-radius:5px;background:var(--rule);margin:8px 0 4px}
#p-summary .sum-prepnum{font-family:var(--mono);font-size:12.5px;color:var(--ink-3)}
#p-summary .sum-btn{display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:0 14px;border:1px solid var(--rule-2);border-radius:8px;text-decoration:none;color:var(--blue-ink);font-size:13.5px;background:var(--card)}
#p-summary .sum-btn:hover{border-color:var(--blue)}
#p-summary .sum-specs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
@media (max-width:900px){#p-summary .sum-specs{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:520px){#p-summary .sum-specs{grid-template-columns:minmax(0,1fr)}}
#p-summary .sum-kv{background:var(--card);padding:11px 14px;display:flex;flex-direction:column;gap:2px;min-width:0}
#p-summary .sum-k{font-size:12px;color:var(--ink-3)}
#p-summary .sum-v{font-family:var(--mono);font-size:17px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
#p-summary .sum-d{font-size:12.5px;color:var(--ink-2);line-height:1.5}
#p-summary .sum-maps{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(250px,100%),1fr));gap:10px}
#p-summary .sum-map{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:start;min-height:44px;background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 14px;text-decoration:none;color:var(--ink)}
#p-summary .sum-map:hover{border-color:var(--blue)}
#p-summary .sum-mapno{font-family:var(--mono);font-size:12px;color:var(--ink-3);padding-top:2px}
#p-summary .sum-mapbody{display:flex;flex-direction:column;gap:2px;min-width:0}
#p-summary .sum-mapbody b{font-size:15px}
#p-summary .sum-mapbody span{font-size:12.5px;color:var(--ink-2);line-height:1.5}
#p-summary .sum-maparr{color:var(--blue-ink);font-family:var(--mono);padding-top:1px}
#p-summary .sum-src .kfs{grid-template-columns:repeat(auto-fit,minmax(min(150px,100%),1fr));margin:6px 0 10px}
#p-summary .sum-kf b{font-size:22px}
#p-summary .sum-kf b small{font-family:var(--sans);font-size:12px;font-weight:500;color:var(--ink-3);margin-left:2px}
#p-summary .sum-kf .sum-kfl{display:block;font-size:13px;color:var(--ink);margin-top:2px}
#p-summary .sum-kf .sum-kfd{display:block;font-size:12px;color:var(--ink-3)}
#p-summary .sum-kf-gap{background:var(--tint-amber)}
#p-summary .sum-kf-gap b{color:var(--amber)}
#p-summary .sum-next{list-style:none;margin:0;padding:0;background:var(--card);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
#p-summary .sum-next li{display:grid;grid-template-columns:128px 168px minmax(0,1fr);gap:12px;padding:10px 14px;border-top:1px solid var(--rule);font-size:13.5px}
#p-summary .sum-next li:first-child{border-top:0}
@media (max-width:720px){#p-summary .sum-next li{grid-template-columns:minmax(0,1fr);gap:2px}}
#p-summary .sum-when{font-family:var(--mono);font-size:12.5px;color:var(--blue-ink);padding-top:1px}
#p-summary .sum-how{color:var(--ink-2)}
#p-summary .sum-checks{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:5px;font-size:13.5px;color:var(--ink-2);max-width:88ch}
#p-summary .sum-checks b{color:var(--ink);font-weight:600;margin-right:2px}
#p-summary .sum-foot{font-size:12.5px;color:var(--ink-3);margin-top:22px;max-width:none;overflow-wrap:anywhere}
#p-summary .sum-foot code{font-family:var(--mono);font-size:12px}
"""

GAP_LEDE = f", 아직 준비처가 없는 물건 {len(gaps)}줄은 아래에 따로 적었습니다." if gaps else "."
section = f'''<section class="page" id="p-summary" hidden>
<h2>Toccata 한눈에 보기</h2>
<p class="lede">3D 프린터로 만드는 88건반 디지털 피아노의 최종 설계입니다. 건반 밑 홀센서가 누르는 속도를 재고 Raspberry Pi 5가 소리를 내며, 본체에 스피커 2개, 7인치 터치스크린, 배터리가 들어 있습니다. 재료는 10/8에 주문했고{GAP_LEDE} 이 탭은 핵심 숫자와 구매·준비 상황을 모으고, 아래 카드에서 회로도·설계도·3D 모델·시뮬레이션·부품 사용처로 이어집니다.</p>
<div class="sum-status"><span class="pill ok">재료 주문 10/8</span><span class="pill">CAD 빌드 2026-10-07</span><span class="pill">건반 액션 W1+ r4.5</span><span class="pill">회로 {REV_LABEL}</span><span class="pill">시연 12/14 주</span></div>

<div class="sum-hero">
  <figure class="sum-fig">
    <img src="rear/R01_front.png" width="1800" height="1100" alt="Toccata 앞 3/4 렌더: 88건반, 양 끝 스피커, 가운데에 세운 7인치 화면">
    <figcaption>쓰는 상태(앞 3/4). 건반 모듈 7개 + 끝 부속 2개, 양 끝 스피커(앞판 {ang:g}°), 가운데 화면 {tilt:g}°. 2026-10-07 CAD 빌드의 렌더입니다.</figcaption>
    <div class="sum-thumbs">
      <figure><img src="rear/R02_rear_left.png" width="1800" height="1100" loading="lazy" alt="뒤 왼쪽 3/4 렌더: 출력 뒤판과 가운데 뒤 출력판"><figcaption>뒤 왼쪽 3/4</figcaption></figure>
      <figure><img src="rear/R03_folded.png" width="1800" height="1100" loading="lazy" alt="화면을 뒤로 접은 상태의 렌더"><figcaption>화면을 접은 상태 (윗면 z{fold_top:g})</figcaption></figure>
    </div>
  </figure>
  <div class="sum-side">
    <div class="sum-card sum-buy">
      <div class="sum-cardhead"><span class="eyebrow">구매</span><span class="sum-lab">주문서 2026-10-08</span></div>
      <div class="sum-lab">재료에 든 돈 (학교 + 사비, 배송비 포함)</div>
      <div class="sum-big">{W(T["total"])}<small>원</small></div>
      <div class="sum-split" role="img" aria-label="{E(split_label)}">
        <span class="sum-seg a" style="flex:{school_all} 1 0" title="학교 지원 {W(school_all)}원 = 물건 {W(T['school_items'])} + 배송 {W(T['school_ship'])}"></span>
        <span class="sum-seg b" style="flex:{T['personal']} 1 0" title="사비 {W(T['personal'])}원 = 물건 {W(T['personal_items'])} + 배송 {W(T['personal_ship'])}"></span>
      </div>
      <div class="sum-cols">
        <div class="sum-col"><span class="sum-colh"><i class="sum-sw a"></i>학교 지원</span><span class="sum-colv">{W(school_all)}원</span>
          <dl><dt>물건값</dt><dd>{W(T["school_items"])} <small>({T["school_lines"]}줄)</small></dd>
          <dt>한도</dt><dd>{W(T["budget_school"])} <small>({W(T["school_left"]) + "원 남음" if T["school_left"] >= 0 else W(-T["school_left"]) + "원 초과"})</small></dd>
          <dt>배송비</dt><dd>{W(T["school_ship"])} <small>(학교 부담, 한도 밖)</small></dd></dl></div>
        <div class="sum-col"><span class="sum-colh"><i class="sum-sw b"></i>사비</span><span class="sum-colv">{W(T["personal"])}원</span>
          <dl><dt>물건값</dt><dd>{W(T["personal_items"])} <small>({T["personal_lines"]}줄)</small></dd>
          <dt>배송비</dt><dd>{W(T["personal_ship"])}</dd></dl></div>
      </div>
      {'<p class="sum-gapline"><span>아직 준비처가 없는 물건이 ' + str(len(gaps)) + '줄 있습니다: ' + E(gaps[0]["name"]) + '. <a href="#sum-gap">아래에서 보기</a></span></p>' if gaps else ''}
      <p class="sum-fine">주문서: 최종본/01_구매목록/Toccata_학교_사비_구매목록_2026-10-08.xlsx. 물건마다 사진·규격·쓰는 자리는 06 부품·사용처 탭에 있습니다.</p>
    </div>
    <div class="sum-card sum-prepcard">
      <div class="sum-cardhead"><span class="eyebrow">준비 현황</span><a class="sum-btn" href="#prep">07 준비 체크 열기 →</a></div>
      <div id="sum-prep"></div><div class="sum-prepempty">
        <p>준비 체크 탭에 물건마다 준비한 개수를 적으면 여기에 전체 준비율과 남은 줄이 나옵니다.</p>
        <div class="sum-preptrack" aria-hidden="true"></div>
        <span class="sum-prepnum">준비율은 {E(PREP_SUM)}로 셉니다. {E(PREP_TOOLS)}과 선택·보험 {PREP_OPT}줄은 켜야 들어갑니다.</span>
      </div>
    </div>
  </div>
</div>

<h3 class="sum-h">핵심 숫자</h3>
<div class="sum-specs">{spec_html}</div>

<h3 class="sum-h">최종 도안</h3>
<div class="sum-maps">{maps_html}</div>

{gap_html}

<h3 class="sum-h">다음 할 일</h3>
<ol class="sum-next">{next_html}</ol>

<h3 class="sum-h">물건을 받으면 먼저 확인할 것</h3>
<ul class="sum-checks">{check_html}</ul>

<p class="sum-foot">원본: 재료 <code>docs/report/toccata-v4/data/final_items.json</code> (주문서 xlsx와 합계 같음) · 건반 액션 <code>hardware/mechanical/key-action-v4/model/metrics.json</code> (r4.5) · 본체·스피커 <code>hardware/mechanical/cad/spec/body_L2.json</code> · 화면 <code>hardware/mechanical/touchscreen/rev3/design/numbers.json</code> · 회로 <code>hardware/pcb</code> {REV_LABEL}, 도면별 검사 <code>netlist/sheets.json</code> · 준비 줄 <code>fin/prep/lines.json</code> · 출력 <code>hardware/mechanical/cad/stl/print</code> · 크기·높이는 CAD 입체(부품 {W(n_cad)}개)에서 다시 쟀습니다. 좌표는 mm, x 가로(0 = A0 왼쪽 끝), y 흰건반 앞 끝에서 뒤로, z 책상에서 위로.</p>
</section>'''

out = f"<style>{CSS}</style>\n{section}\n"
dst = os.path.join(HERE, "summary.html")
with open(dst, "w", encoding="utf-8") as fh:
    fh.write(out)
print(f"summary.html {len(out):,} bytes; total {T['total']:,} = school {school_all:,} ({T['school_items']:,} + {T['school_ship']:,}) "
      f"+ personal {T['personal']:,}; lines {cnt}; checklist {n_check}; CAD parts {n_cad}; print {pf}")
