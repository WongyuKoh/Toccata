"""R31 touchscreen rev 3 (B1 on L2) -- drawing geometry.

Every coordinate used by the sheets is read from the rev-3 design (../../design/numbers.json, which geom3.py computed from
the ONE placement block of the final L2 file) or derived here from those numbers by the same formulas the design scripts
use (geom3.py / draw3.py / CAD_SPEC_rev3.md).  Context (rear bar walls, speaker pods, feet) comes from the final L2 files
(../../L2_cu.json and the copy ctx/body_L2.json of hardware/mechanical/cad/spec/body_L2.json); the wiring designators
come from the circuit session's netlist (ctx/cables.csv, netlist.csv, bom.csv = copies of touch3/pcb/netlist).

Frames: world x (A0 left boundary), y (from the white-key front lip, away from the player), z (up from the desk);
cradle xr = x - XC, u = from the glass bottom edge up the screen, w = from the glass front face backward.
"""
import csv
import hashlib
import json
import math
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
T3 = os.path.normpath(os.path.join(HERE, "..", ".."))
DESIGN = os.path.join(T3, "design")
F_NUM = os.path.join(DESIGN, "numbers.json")
F_SPEC = os.path.join(DESIGN, "CAD_SPEC_rev3.md")
F_L2 = os.path.join(T3, "L2_cu.json")
F_L2P = os.path.join(T3, "L2_cu_provisional.json")
F_BODY = os.path.join(HERE, "ctx", "body_L2.json")

N = json.load(open(F_NUM))
L2 = json.load(open(F_L2 if os.path.exists(F_L2) else F_L2P))
BODY = json.load(open(F_BODY))
SPEC = open(F_SPEC).read()


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


SOURCES = {os.path.relpath(p, T3): md5(p) for p in (F_NUM, F_SPEC, F_L2 if os.path.exists(F_L2) else F_L2P, F_BODY)}

PL = N["placement"]
XC = PL["x_centre"]
LID = PL["lid"]
KO = PL["keepout"]
S = N["screen"]
CR = N["cradle"]
HG = N["hinge"]
LG = N["leg"]
PK = LG["pocket"]
FO = N["fold"]
HO = N["hole"]
CL = N["clip"]
V = N["vents"]
PI = N["pi5"]
RB = N["ribbon"]
PW = N["power_wire"]
CK = N["checks"]
ST = N["stability"]
EYE = N["eye"]
CTX = N["context"]
POSE = N["poses"]
PTS = N["points"]
H = tuple(HG["axis_yz"])
UA, WA = HG["axis_cradle_uw"]
TH_USE, TH_HEEL, TH_FOLD = HG["tilt_use_deg"], HG["heel_contact_deg"], 90.0
DATE = N["date"]
REV = str(N.get("revision", N["rev"])).split()[0]          # '3a' (design fix round) -> the drawings show that revision
REV_TXT = f"Toccata R31 터치스크린 수정 {REV}판 (B1 · L2) · 도면 고침 1 · {DATE}"

CHECKS = []          # (item, ok, detail) consistency checks run while the sheets are drawn (logged in drawings.json)


def check(item, ok, detail=""):
    CHECKS.append(dict(item=item, ok=bool(ok), detail=str(detail)))
    return ok


# ------------------------------------------------------------------ poses
def P(u, w, th):
    """cradle (u, w) -> world (y, z) at tilt th (deg from vertical, backward), same formula as geom3.P."""
    t = math.radians(th)
    du, dw = u - UA, w - WA
    return (H[0] + du * math.sin(t) + dw * math.cos(t), H[1] + du * math.cos(t) - dw * math.sin(t))


def M_of(th):
    return {TH_USE: POSE["cradle_use"], TH_HEEL: POSE["cradle_heel"], TH_FOLD: POSE["cradle_fold"]}[th]


for _th in (TH_USE, TH_HEEL, TH_FOLD):          # the formula must reproduce the design's 4x4 pose matrices
    _M = np.array(M_of(_th), float)
    for (_u, _w) in ((CR["u"][0], CR["w"][0]), (CR["u"][1], CR["w"][1]), (30.0, 16.5)):
        _q = _M @ np.array([0.0, _u, _w, 1.0])
        _p = P(_u, _w, _th)
        check(f"pose {_th:g} deg matrix = formula (u{_u:g} w{_w:g})", abs(_q[1] - _p[0]) < 0.02 and abs(_q[2] - _p[1]) < 0.02,
              f"{_q[1]:.3f},{_q[2]:.3f} vs {_p[0]:.3f},{_p[1]:.3f}")


def PW3(xr, u, w, th):
    y, z = P(u, w, th)
    return (XC + xr, y, z)


def tf(poly, th):
    return [P(u, w, th) for (u, w) in poly]


def to_local(y, z, th):
    """inverse of P: world (y, z) -> cradle (u, w) at tilt th."""
    t = math.radians(th)
    dy, dz = y - H[0], z - H[1]
    return (UA + dy * math.sin(t) + dz * math.cos(t), WA + dy * math.cos(t) - dz * math.sin(t))


# ------------------------------------------------------------------ small geometry helpers
def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def circle(c, r, n=48):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def arc(c, r, a0, a1, n=24):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def hull(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _dseg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2_ = dx * dx + dy * dy
    t = 0.0 if L2_ == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2_))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def inside(p, poly):
    x, y = p
    ins = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            ins = not ins
    return ins


def bdist(p, poly):
    """distance from p to the boundary of the closed polygon."""
    return min(_dseg(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def poly_gap(A, B):
    """signed gap between two closed polygons: > 0 = clear (smallest boundary distance), <= 0 = touching / overlapping
    (minus the deepest vertex of either polygon inside the other)."""
    pen = 0.0
    for p in A:
        if inside(p, B):
            pen = max(pen, bdist(p, B))
    for p in B:
        if inside(p, A):
            pen = max(pen, bdist(p, A))
    if pen > 1e-9:
        return -pen
    if any(_cross(A[i], A[(i + 1) % len(A)], B[j], B[(j + 1) % len(B)]) for i in range(len(A)) for j in range(len(B))):
        return -1e-3
    return min(min(bdist(p, B) for p in A), min(bdist(p, A) for p in B))


def hausdorff(A, B):
    return max(max(bdist(p, B) for p in A), max(bdist(p, A) for p in B))


def spec_nums(pattern, group_count=2):
    """numbers of the first CAD_SPEC_rev3.md match (for cross-checks of values the spec states in words)."""
    m = re.search(pattern, SPEC)
    if not m:
        return None
    return [float(m.group(i + 1)) for i in range(group_count)]


# ------------------------------------------------------------------ screen (cradle frame)
GX = S["glass"][0] / 2                 # glass half width 83.05
GH = S["glass"][1]                     # 101
GB = S["body"]                         # 8
ACT_XR = [S["active_x"][0] - XC, S["active_x"][1] - XC]
ACT_U = S["active_u"]
HOLE_XR, HOLE_U = S["holes"]["xr"], S["holes"]["u"]

# ------------------------------------------------------------------ cradle (local); walls follow CAD_SPEC C-1
U0, U1 = CR["u"]
W0, W1 = CR["w"]
XR0, XR1 = CR["xr"]
RIM, CLR = CR["rim"], CR["clr"]
XIN = GX + CLR                          # inner face of the side walls 83.35
PL_IN, PL_OUT = CR["plate"]            # 10.5 / 13
RIB0, RIB1 = CR["rib"]                 # 13 / 16
WALLS_CR = CR["walls"]                 # 3a: bottom wall inner face u0 (glass rests on it), top gap 0.5, side gap 0.3
BOT_IN = WALLS_CR["bottom_u"][1]
TOP_IN = WALLS_CR["top_u"][0]
TOP_GAP = TOP_IN - GH
BOT_T = BOT_IN - U0
check("walls (numbers cradle.walls) = glass + gaps: bottom u0, top gap 0.5, side inner face = glass/2 + 0.3",
      abs(BOT_IN - 0.0) < 1e-9 and abs(TOP_GAP - WALLS_CR["top_gap"]) < 1e-6 and abs(WALLS_CR["side_inner_xr"] - XIN) < 1e-6
      and abs(TOP_IN - (U1 - RIM)) < 1e-6, f"u{BOT_IN} / top {TOP_IN} gap {TOP_GAP:.2f} / side {XIN}")
check("cradle outer width = glass + 2 (clr + rim)", abs((XR1 - XR0) - (S["glass"][0] + 2 * (CLR + RIM))) < 1e-6, XR1 - XR0)
CH = CR["rib_relief_at_cheeks"]["chamfer"]
BO = CR["bosses"]
check("bosses joined to the side walls (numbers bosses.fill_to_side_wall)",
      all(abs(abs(f_[0 if xb < 0 else 1]) - XIN) < 1e-6 and abs(abs(f_[1 if xb < 0 else 0]) - abs(xb)) < 1e-6
          for xb, f_ in zip(BO["xr"], BO["fill_to_side_wall"]["xr"])) and abs(BO["fill_to_side_wall"]["width_u"] - BO["d"]) < 1e-6)
INSP = CR["insp"]
GR = CR["groove"]
HP = CR["hold_pad"]
FSQ = CR["fold_square"]
PADS = CR["pads"]
XRIB = CR["cross_ribs_u"]
RIB_T = CR["rib_t"]                     # rib thickness 2.0
check("rib thickness (numbers) stated in CAD_SPEC C-9", f"두께 {RIB_T:g}" in SPEC or f"두께 {RIB_T:.1f}" in SPEC, RIB_T)
NOTCH = CR["notch"]                    # 3a: relief notch in the bottom wall for the bottom-edge feature of the screen
check("bottom-wall notch clears the bottom-edge feature on both sides (numbers notch_margin)",
      abs((NOTCH["feature_xr"][0] - NOTCH["xr"][0]) - N["checks"]["notch_margin"][0]) < 0.01
      and abs((NOTCH["xr"][1] - NOTCH["feature_xr"][1]) - N["checks"]["notch_margin"][1]) < 0.01
      and min(N["checks"]["notch_margin"]) > 2.0, N["checks"]["notch_margin"])
check("notch cuts the whole bottom wall (u) in front of the ear attachment (w < 8)",
      abs(NOTCH["u"][0] - U0) < 1e-6 and abs(NOTCH["u"][1] - BOT_IN) < 1e-6 and NOTCH["w"][1] <= CR["w_screen_back"] + 1e-6)
CHW = LG["channel"]                    # leg channel walls
# window surround rib: 1.8 outside the window (C-5), rib 2.0 thick
WIN_RIB_OFF = spec_nums(r"창 둘레 리브는 창보다 (\d+(?:\.\d+)?) mm 밖", 1)[0]
WRIB_IN = [INSP["xr"][0] - WIN_RIB_OFF, INSP["xr"][1] + WIN_RIB_OFF, INSP["u"][0] - WIN_RIB_OFF, INSP["u"][1] + WIN_RIB_OFF]
WRIB_OUT = [WRIB_IN[0] - RIB_T, WRIB_IN[1] + RIB_T, WRIB_IN[2] - RIB_T, WRIB_IN[3] + RIB_T]
COVER = INSP["cover"]
check("cover flange (1.5) < window rib offset (1.8)", COVER["flange"] < WIN_RIB_OFF, f"{COVER['flange']} < {WIN_RIB_OFF}")

# hinge ears (xr ranges) and the ear side profile (u, w).  3a: the profile is numbers cradle.ear.profile_uw = the convex hull
# of the hub R4.2 around the axis, the bottom attachment (u-2.5, w8..13) and the ONE heel point (no second lobe point).
EAR_L, EAR_R = HG["left"]["ear"], HG["right"]["ear"]
HEEL_REL22 = tuple(HG["heel_rel22"])
HEEL_R = math.hypot(*HEEL_REL22)
check("heel radius = numbers heel_R", abs(HEEL_R - HG["heel_R"]) < 0.01, HEEL_R)


def heel_world(th, extra=0.0):
    a22 = math.atan2(HEEL_REL22[1], HEEL_REL22[0])
    a = a22 - math.radians(th - TH_HEEL) + extra
    return (H[0] + HEEL_R * math.cos(a), H[1] + HEEL_R * math.sin(a))


EARD = CR["ear"]
EAR_PROFILE = [tuple(p) for p in EARD["profile_uw"]]
HEEL_TIP_LOCAL = tuple(EARD["heel_uw"])
EAR_TAN = dict(lower=tuple(EARD["lower_edge"][1]), back=tuple(EARD["back_edge"][1]))      # hub tangent points
check("heel point at 22 deg = heel_contact_yz", math.dist(heel_world(TH_HEEL), HG["heel_contact_yz"]) < 0.02, heel_world(TH_HEEL))
check("ear heel point (numbers) = heel contact pulled back to the cradle frame at 22 deg",
      math.dist(to_local(*HG["heel_contact_yz"], TH_HEEL), HEEL_TIP_LOCAL) < 0.02, to_local(*HG["heel_contact_yz"], TH_HEEL))
_ear_hull = hull(circle((UA, WA), HG["ear_hub_R"], 720) + [(U0, CR["w_screen_back"]), (U0, WA), HEEL_TIP_LOCAL])
check("ear profile = hull(hub R4.2, bottom attachment, heel point) (CAD_SPEC C-12)", hausdorff(EAR_PROFILE, _ear_hull) < 0.05,
      f"{hausdorff(EAR_PROFILE, _ear_hull):.3f}")
check("ear heel point is the lowest ear point at 22 deg", abs(min(P(u, w, TH_HEEL)[1] for u, w in EAR_PROFILE) - HG["heel_contact_yz"][1]) < 0.02)
HEEL_STOP = dict(y=list(HG["heel_block"]["y"]), z=list(HG["heel_block"]["z"]))


def ear_block_gap(profile, th, with_wall=True):
    """signed gap (world y-z) of the drawn ear outline (and the bottom wall over the slot) to the heel stop block and the
    slot floor (lid top) at tilt th."""
    obst = [rect(HEEL_STOP["y"][0], HEEL_STOP["y"][1], LID["top_z"] - 6.0, HEEL_STOP["z"][1]),
            rect(LID["y"][0], LID["y"][1], LID["top_z"] - 6.0, LID["top_z"])]
    parts = [profile] + ([[(U0, W0), (BOT_IN, W0), (BOT_IN, W1), (U0 + CH, W1), (U0, W1 - CH)]] if with_wall else [])
    return min(poly_gap(tf(p_, th), ob) for p_ in parts for ob in obst)


_th_sweep = [TH_HEEL + 0.25 * i for i in range(int(round((TH_FOLD - TH_HEEL) / 0.25)) + 1)]
EAR_GAP22 = ear_block_gap(EAR_PROFILE, TH_HEEL)
EAR_GAP_25_90 = min(ear_block_gap(EAR_PROFILE, t) for t in _th_sweep if t >= TH_USE - 1e-9)
EAR_GAP_22_25 = min(ear_block_gap(EAR_PROFILE, t) for t in _th_sweep if t <= TH_USE + 1e-9)
check("ear + bottom wall vs heel stop block: touching at 22 deg (>= -0.02), >= 0.3 at 25..90 deg (drawn outline, 0.25 deg steps)",
      EAR_GAP22 >= -0.02 and EAR_GAP_25_90 >= 0.3 and EAR_GAP_22_25 >= -0.02, f"22: {EAR_GAP22:.2f}, 25~90: {EAR_GAP_25_90:.2f}")
check("ear gaps = numbers ear.check", abs(EAR_GAP22 - EARD["check"]["gap_at_22"]) < 0.03 and abs(EAR_GAP_25_90 - EARD["check"]["min_gap_25_90"]) < 0.03,
      f"{EAR_GAP22:.2f}/{EAR_GAP_25_90:.2f} vs {EARD['check']['gap_at_22']}/{EARD['check']['min_gap_25_90']}")
_old = hull(circle((UA, WA), HG["ear_hub_R"], 720) + [(U0, CR["w_screen_back"]), (U0, WA), HEEL_TIP_LOCAL, tuple(EARD["check"]["rev3_first_lobe"]["lobe_uw"])])
EAR_OLD_GAP = (ear_block_gap(_old, TH_HEEL, False), ear_block_gap(_old, TH_USE, False))
check("the same test catches the rev-3 first ear (extra lobe point): negative at 22 and 25 deg", EAR_OLD_GAP[0] < -1.0 and EAR_OLD_GAP[1] < -1.0,
      f"{EAR_OLD_GAP[0]:.2f} / {EAR_OLD_GAP[1]:.2f}")

# leg clevis on the cradle back: lug profile = hull(R3.8 around the pivot, plate-back base); the +u side (print bed side,
# the cradle prints standing on its top edge u103.5) is a 45 deg chamfer tangent to the R3.8 boss (C-13 "아래쪽 45° 모따기")
LEGP = tuple(LG["pivot_cradle_uw"])            # (30, 16.5)
CLV = LG["clevis"]
_c45 = LEGP[0] + LEGP[1] + CLV["R"] * math.sqrt(2)            # tangent line u + w = c
LUG_PROFILE = hull(circle(LEGP, CLV["R"], 72) + [(LEGP[0] - CLV["R"], RIB0), (_c45 - RIB0, RIB0)])
LUG_U = [LEGP[0] - CLV["R"], _c45 - RIB0]
CLIPD = LG["clip"]


def lug_ok():
    return check("leg channel starts at the lug (u_p - R)", abs(CHW["u"][0] - (LEGP[0] - CLV["R"])) < 0.01, CHW["u"][0])


lug_ok()
# leg (own frame): along its length s from the pivot (0) to the tip (L), thickness t, width b, ends R = t/2
LEG_L, LEG_B, LEG_T = LG["length"], LG["section"][0], LG["section"][1]
LEG_R = LEG_T / 2
LEG_HOLE = float(re.match(r"(\d+(?:\.\d+)?)", CLV["hole_near"]).group(1))       # 3.3 thru
FAR_HOLE = float(re.match(r"(\d+(?:\.\d+)?)", CLV["hole_far"]).group(1))        # 2.5
FAR_HOLE_DEPTH = float(re.search(r"x (\d+(?:\.\d+)?)", CLV["hole_far"]).group(1))
FAR_ENGAGE = float(re.search(r"engages (\d+(?:\.\d+)?)", CLV["hole_far"]).group(1))
AXLE = LG["axle"]                                                                 # M3x20 ISO 7380, head D5.7 x 1.65
AXLE_L = AXLE["L"]
check("leg axle length = the M3x20 named in the clevis note", "M3x20" in CLV["hole_far"] and abs(AXLE_L - 20.0) < 1e-9)
AX_HEAD = dict(d=AXLE["head_d"], h=AXLE["head_h"])
check("leg clevis: M3x20 from the near lug engages the far lug as stated",
      abs((CLV["near"][0] + AXLE_L) - CLV["far"][0] - FAR_ENGAGE) < 0.01, (CLV["near"][0] + AXLE_L) - CLV["far"][0])


def leg_outline(piv, tip):
    """leg side outline (world y, z): capsule of radius t/2 around the pivot-tip segment."""
    dy, dz = tip[0] - piv[0], tip[1] - piv[1]
    L = math.hypot(dy, dz)
    a = math.degrees(math.atan2(dz, dy))
    return arc(tip, LEG_R, a - 90, a + 90, 16) + arc(piv, LEG_R, a + 90, a + 270, 16)


# ------------------------------------------------------------------ lid additions (world)
KP = HG["knuckle_profile"]


def knuckle_profile(n=40):
    """(y, z) of a lid knuckle cheek: trapezoid lid top -> axis height, plus R5.5 around the axis (upper half)."""
    top = arc(H, KP["R"], 0, 180, n)
    return [(KP["base_y"][1], KP["base_z"])] + top + [(KP["base_y"][0], KP["base_z"])]


check("knuckle trapezoid meets the R5.5 at the axis height", abs((KP["at_axis_y"][1] - KP["at_axis_y"][0]) / 2 - KP["R"]) < 0.01)
# knuckle x-ranges (world) = XC + hinge-set xr; ear slot = between the cheeks
def kn_x(side):
    s = HG[side]
    return dict(near=[XC + s["near_cheek"][0], XC + s["near_cheek"][1]], far=[XC + s["far_cheek"][0], XC + s["far_cheek"][1]],
                ear=[XC + s["ear"][0], XC + s["ear"][1]], all=[XC + s["xr"][0], XC + s["xr"][1]], screw_from=s["screw_from"])


KNL, KNR = kn_x("left"), kn_x("right")
SLOT = {side: sorted([min(k["near"][1], k["far"][1]) if side == "left" else min(k["near"][0], k["far"][0]),
                      max(k["near"][0], k["far"][0]) if side == "left" else max(k["near"][1], k["far"][1])])
        for side, k in (("left", KNL), ("right", KNR))}
# slot between the cheeks: left = near cheek right face .. far cheek left face
SLOT["left"] = [KNL["near"][1], KNL["far"][0]]
SLOT["right"] = [KNR["far"][1], KNR["near"][0]]
KN_GAP = SLOT["left"][1] - KNL["ear"][1]
check("ear slot gap each side 0.2", abs((KNL["ear"][0] - SLOT["left"][0]) - 0.2) < 1e-6 and abs(KN_GAP - 0.2) < 1e-6, KN_GAP)
# 3a wording: 귀 = the cradle ear (8.0), 귀 홈 = the lid slot between the cheeks (8.4)
check("귀 / 귀 홈 x = numbers hinge.ear_x / ear_slot_x",
      all(abs(a - b) < 1e-6 for s in ("left", "right") for a, b in zip((KNL if s == "left" else KNR)["ear"] + SLOT[s], HG["ear_x"][s] + HG["ear_slot_x"][s])))
# heel stop block: in the ear slot, from the knuckle base front to (axis y - 2) (draw3.py / CAD_SPEC A-1: y217.55~224.55)
check("heel stop block (numbers heel_block) = knuckle base front .. axis y - 2, lid top .. heel_stop_z",
      abs(HEEL_STOP["y"][0] - KP["base_y"][0]) < 1e-6 and abs(HEEL_STOP["y"][1] - (H[0] - 2.0)) < 1e-6
      and abs(HEEL_STOP["z"][0] - LID["top_z"]) < 1e-6 and abs(HEEL_STOP["z"][1] - HG["heel_stop_z"]) < 1e-6)
_sp = spec_nums(r"y(\d+\.\d+)~(\d+\.\d+)\. 22°에서 귀의 뒤꿈치")
check("heel stop y range = CAD_SPEC A-1", _sp and abs(_sp[0] - HEEL_STOP["y"][0]) < 0.01 and abs(_sp[1] - HEEL_STOP["y"][1]) < 0.01, _sp)
check("heel contact inside the stop block", HEEL_STOP["y"][0] <= HG["heel_contact_yz"][0] <= HEEL_STOP["y"][1])
# knuckle axle: M3x20 from the near (outer) cheek; far cheek tapped 2.5
KN_NEAR_HOLE = 3.3
KN_FAR_HOLE = 2.5
_kn = spec_nums(r"가까운 볼 Ø(\d+\.\d+) 관통, 먼 볼 Ø(\d+\.\d+)")
check("knuckle holes = CAD_SPEC A-1", _kn == [KN_NEAR_HOLE, KN_FAR_HOLE], _kn)
KN_ENGAGE = (KNL["near"][0] + 20.0) - KNL["far"][0]
check("M3x20 engages the far cheek 7.6 (CAD_SPEC)", abs(KN_ENGAGE - 7.6) < 0.01, KN_ENGAGE)
KN_FILL = dict(y=[KP["base_y"][0], KP["base_y"][1]], z=[LID["bed_z"], LID["top_z"] - LID["plate_t"]])

# hole wall and pocket block
HOLE_WALL = [HO["x"][0] - HO["wall"], HO["x"][1] + HO["wall"], HO["y"][0] - HO["wall"], HO["y"][1] + HO["wall"]]
POCKET_PROFILE = [(PK["ramp_front_y"], LID["top_z"]), (PK["ramp_end_y"], PK["bottom_z"]), (PK["back_wall_y"], PK["bottom_z"]),
                  (PK["back_wall_y"], LID["top_z"])]
RAMP_DEG = math.degrees(math.atan2(LID["top_z"] - PK["bottom_z"], PK["ramp_end_y"] - PK["ramp_front_y"]))
check("pocket ramp 30 deg", abs(RAMP_DEG - 30.0) < 0.1, RAMP_DEG)
FEET = N["fold_feet_detail"]
FEET_SZ = f"{FEET[0]['x'][1] - FEET[0]['x'][0]:g}×{FEET[0]['y'][1] - FEET[0]['y'][0]:g}"
SCREWS = [(x, y) for y in PL["lid_screw"]["y"] for x in PL["lid_screw"]["x"]]
LS = N["lid_screw"]                                               # 3a: counterbore / insert values (A-7, estimates)
_lsh = re.search(r"Ø(\d+(?:\.\d+)?) × (\d+(?:\.\d+)?)", LS["screw"])
LID_SCREW = dict(d_cbore=LS["cbore_d"], screw_L=float(re.search(r"M3x(\d+)", LS["screw"]).group(1)), engage_est=LS["insert_engage"],
                 cbore_depth=LS["cbore_depth"], hole_d=LS["hole_d"], boss_d=LS["boss_d"], tip_z=LS["tip_z"], seat_z=LS["head_seat_z"],
                 head_d=float(_lsh.group(1)), head_h=float(_lsh.group(2)), rail_floor=LS["rail_floor_under_hole"], insert_hole=LS["insert_hole_depth"])
check("lid screw counterbore depth = lid thickness - (screw L - insert engagement) (A-7 rule)",
      abs(LID_SCREW["cbore_depth"] - ((LID["top_z"] - LID["bed_z"]) - (LID_SCREW["screw_L"] - LID_SCREW["engage_est"]))) < 1e-6
      and abs(LID_SCREW["seat_z"] - (LID["top_z"] - LID_SCREW["cbore_depth"])) < 1e-6
      and abs(LID_SCREW["tip_z"] - (LID_SCREW["seat_z"] - LID_SCREW["screw_L"])) < 1e-6, LID_SCREW["cbore_depth"])
check("lid screw x/y = placement block", LS["x"] == PL["lid_screw"]["x"] and LS["y"] == PL["lid_screw"]["y"])
LID_SCREW["rail_z"] = LS["rail_z"]
LID_SCREW["hole_bottom"] = LS["rail_z"][1] - LID_SCREW["insert_hole"]
check("lid screw: rail top = lid bed, insert hole bottom = rail floor + 1.5, screw tip >= 0.5 above the hole bottom",
      abs(LS["rail_z"][1] - LID["bed_z"]) < 1e-6 and abs(LID_SCREW["hole_bottom"] - LS["rail_z"][0] - LID_SCREW["rail_floor"]) < 1e-6
      and LID_SCREW["tip_z"] - LID_SCREW["hole_bottom"] >= 0.5 - 1e-6, f"tip {LID_SCREW['tip_z']} / hole bottom {LID_SCREW['hole_bottom']:.2f}")
PIN_HOLE = [CL["pin_hole_d"], CL["pin_hole_depth"]]
PIN_D = CL["pin_d"]
CLIP_SIZE = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)", CL["clip"])[:2]] + [CL["t"]]       # 30 x 12 x 3
CLIP_Z, CLAMP_Z = CL["clip_z"], CL["clamp_z"]
WG = CL["wire_groove"]
check("clip pin length = hole depth - 0.5 (numbers pin_len)", abs(CL["pin_len"] - (PIN_HOLE[1] - 0.5)) < 1e-9, CL["pin_len"])
check("clip clamps the ribbon at the lid bed: clip top + ribbon = bed z; ribbon run z = clamp middle",
      abs(CLIP_Z[1] - CLAMP_Z[0]) < 1e-6 and abs(CLAMP_Z[1] - LID["bed_z"]) < 1e-6 and abs(CLAMP_Z[1] - CLAMP_Z[0] - N["ribbon"]["ffc_t"]) < 1e-6
      and abs(N["ribbon"]["z_run"] - (CLAMP_Z[0] + CLAMP_Z[1]) / 2) < 0.01)

# ------------------------------------------------------------------ rear bar / speakers (context, final L2)
C_ = BODY["centre"]
WALLS = C_["walls"]
FLOOR_ZONE = C_["floor_zone"]
FRONT_ZONE = C_["front_zone"]
SPK = BODY["speakers"]
DRV = SPK["driver"]
BAFFLE = SPK["baffle"]
FEET_RB = BODY["feet"]
check("L2 lid z (body_L2) = placement lid", abs(WALLS["lid_z"][1] - LID["top_z"]) < 1e-6 and abs(WALLS["lid_z"][0] - LID["bed_z"]) < 0.01)
check("L2 rear face = placement", abs(C_["y"][1] - PL["rear_face_y"]) < 1e-6)
check("speaker top (body_L2) = placement", abs(SPK["z"][1] - PL["speaker_top_z"]) < 1e-6)
# sound-path rule (L2): 27 deg line from the lower edge of the D94 cone must pass >= 3 above (y212, z72.85)
CONE_D = float(re.search(r"Ø(\d+)", L2["sound_path_rule"]).group(1))
SP_DEG = float(re.search(r"(\d+) deg", L2["sound_path_rule"]).group(1))
SP_MIN = float(re.search(r">= (\d+(?:\.\d+)?) mm", L2["sound_path_rule"]).group(1))
_bs = math.radians(BAFFLE["angle_from_horizontal_deg"])
CONE_LOW = (DRV["centre_yz"][0] - CONE_D / 2 * math.cos(_bs), DRV["centre_yz"][1] - CONE_D / 2 * math.sin(_bs))


def sound_line_z(y):
    return CONE_LOW[1] + (CONE_LOW[0] - y) * math.tan(math.radians(SP_DEG))


SP_CLEAR_DWG = sound_line_z(KO["module_rear_y"]) - KO["z_min"]
SR = N["sound_rule"]
SP_CLEAR = SR["clear_above_module_edge"]                  # one value everywhere (numbers); the drawing recomputes it
check("sound path 27 deg line >= 3 above (y212, z72.85); drawing = numbers sound_rule",
      SP_CLEAR_DWG >= SP_MIN and abs(SP_CLEAR_DWG - SP_CLEAR) < 0.03 and math.dist(CONE_LOW, SR["cone_lower_edge_yz"]) < 0.03,
      f"{SP_CLEAR_DWG:.3f} vs {SP_CLEAR}")
# the screen never reaches the speaker x-ranges (plan)
SPK_X = L2["speakers_x"]
check("screen x inside the gap between the speakers", SPK_X["L"][1] < CR["x"][0] and CR["x"][1] < SPK_X["R"][0])
# plan sound paths from the REAL driver centres (body_L2) to the two ears (numbers.context ear estimate)
EARS = [(CTX["player_x"] - CTX["ear_dx"], CTX["eye"][0]), (CTX["player_x"] + CTX["ear_dx"], CTX["eye"][0])]
DRV_PLAN = [(DRV["x_centre"]["L"], DRV["centre_yz"][0]), (DRV["x_centre"]["R"], DRV["centre_yz"][0])]
SCR_RECT = N["screen_rect_plan"]


def seg_rect(a, b, r):
    x0, y0, x1, y1 = r
    best = 1e9
    for i in range(2001):
        t = i / 2000
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        best = min(best, math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)))
    return best


SOUND_PATHS = [dict(src=s, ear=e, dist=seg_rect(s, e, SCR_RECT)) for s in DRV_PLAN for e in EARS]
SOUND_MIN_DWG = min(p["dist"] for p in SOUND_PATHS)
SOUND_MIN = CK["sound_paths_min"]
check("plan sound paths clear the screen; driver centres + nearest distance = numbers (one value)",
      SOUND_MIN > 50 and abs(SOUND_MIN_DWG - SOUND_MIN) < 0.1 and [list(p) for p in DRV_PLAN] == PL["speakers_plan"],
      f"{SOUND_MIN_DWG:.2f} vs {SOUND_MIN}")

# ------------------------------------------------------------------ swept envelope 22..90 deg (keep-out check, drawn on t01)
SWEEP_TH = np.linspace(TH_HEEL, TH_FOLD, 69)
CORNERS = [(U0, W0), (U0, W1 - CH), (U0 + CH, W1), (U1, W0), (U1, W1)]


def sweep_min_y():
    best = (1e9, None)
    for th in SWEEP_TH:
        for (u, w) in CORNERS + EAR_PROFILE:
            y = P(u, w, th)[0]
            if y < best[0]:
                best = (y, (th, u, w))
    return best


SWEEP_MIN = sweep_min_y()
check("sweep 22..90: every cradle/ear point behind the keep-out line", SWEEP_MIN[0] > KO["y_max"], f"{SWEEP_MIN[0]:.2f} at {SWEEP_MIN[1]}")
check("sweep min y = numbers all_min_y", abs(SWEEP_MIN[0] - N["all_min_y"]) < 0.05, f"{SWEEP_MIN[0]:.3f} vs {N['all_min_y']}")

# ------------------------------------------------------------------ tolerances (drawing rule; FDM PETG on the P2S)
TOL = dict(
    general="±0.3",            # printed outline, untoleranced
    axis_pos="±0.2",           # hinge axis y / z in the lid; pivot of the leg on the cradle
    hole_axle="+0.1 / 0 (드릴 Ø3.3)",
    hole_tap="±0.1 (M3 직접 탭)",
    slot_gap="+0.1 / 0",       # cheek - ear gaps 0.2
    fold_feet="±0.2",
    heel_stop="+0 / −0.3 (깎아 맞춤)",
    glass_seat="+0.2 / 0",
    boss_face="0 / −0.2",
    pocket="+0.3 / 0",
    boss_pitch="±0.2",         # screen corner-hole pitch 154 x 88 on the cradle bosses
)


# ------------------------------------------------------------------ cradle solid model: prisms (xr range) x (u, w) polygons
def wall_poly(u_in, chamfer=True):
    """bottom wall / side wall profile from U0 to u_in with the C2 chamfer at the bottom-back edge (u0, w16)."""
    c = CH if chamfer else 0.0
    return [(U0, W0), (u_in, W0), (u_in, W1), (U0 + c, W1), (U0, W1 - c)]


def cradle_prisms(xribs=None):
    """(name, [xr0, xr1], (u, w) polygon, kind)  kind: add / sub / boss.  Every value from numbers.json (tgeo names)."""
    pr = []
    for s in (-1, 1):
        pr.append(("옆벽", sorted([s * XIN, s * XR1]), wall_poly(U1), "add"))
    pr.append(("아래 벽", [-XIN, XIN], wall_poly(BOT_IN), "add"))
    pr.append(("위 벽", [-XIN, XIN], rect(TOP_IN, U1, W0, W1), "add"))
    pr.append(("뒷판", [-XIN, XIN], rect(BOT_IN, TOP_IN, PL_IN, PL_OUT), "add"))
    cw = CHW["xr_walls"]
    for uu in (XRIB if xribs is None else xribs):
        pr.append(("가로 리브", [-XIN, cw[0][0]], rect(uu - RIB_T / 2, uu + RIB_T / 2, RIB0, RIB1), "add"))
        pr.append(("가로 리브", [cw[1][1], XIN], rect(uu - RIB_T / 2, uu + RIB_T / 2, RIB0, RIB1), "add"))
    wi, wo = WRIB_IN, WRIB_OUT
    pr.append(("창 둘레 리브", [wo[0], wi[0]], rect(wo[2], wo[3], RIB0, RIB1), "add"))
    pr.append(("창 둘레 리브", [wi[1], wo[1]], rect(wo[2], wo[3], RIB0, RIB1), "add"))
    pr.append(("창 둘레 리브", [wi[0], wi[1]], rect(wo[2], wi[2], RIB0, RIB1), "add"))
    pr.append(("창 둘레 리브", [wi[0], wi[1]], rect(wi[3], wo[3], RIB0, RIB1), "add"))
    for w_ in cw:
        pr.append(("다리 길 벽", list(w_), rect(CHW["u"][0], CHW["u"][1], CHW["w"][0], CHW["w"][1]), "add"))
    for p in PADS:
        pr.append(("뒤 패드", list(p["xr"]), rect(p["u"][0], p["u"][1], RIB0, RIB1), "add"))
    for side in ("left", "right"):
        pr.append(("경첩 귀", list(HG[side]["ear"]), EAR_PROFILE, "add"))
    pr.append(("다리 걸이 (가까운 볼)", list(CLV["near"]), LUG_PROFILE, "add"))
    pr.append(("다리 걸이 (먼 볼)", list(CLV["far"]), LUG_PROFILE, "add"))
    for b in CLIPD["xr_bodies"]:
        pr.append(("다리 클립", list(b), rect(CLIPD["u"][0], CLIPD["u"][1], RIB0, CLIPD["back_w"]), "add"))
        hook = [b[0] - CLIPD["catch"], b[0]] if b[0] > 0 else [b[1], b[1] + CLIPD["catch"]]
        pr.append(("클립 턱", hook, rect(CLIPD["u"][0], CLIPD["u"][1], CLIPD["catch_from_w"], CLIPD["back_w"]), "add"))
    pr.append(("누름 패드", list(HP["xr"]), rect(HP["u"][0], HP["u"][1], HP["w"][0], HP["w"][1]), "add"))
    for xb in BO["xr"]:
        web = sorted([xb, math.copysign(XIN, xb)])
        for ub in BO["u"]:
            pr.append(("보스 붙임", web, rect(ub - BO["d"] / 2, ub + BO["d"] / 2, BO["face_w"], RIB1), "add"))
    # cuts
    pr.append(("점검창", list(INSP["xr"]), rect(INSP["u"][0], INSP["u"][1], PL_IN - 0.05, PL_OUT + 0.05), "sub"))
    pr.append(("아래 홈", list(GR["xr"]), rect(U0 - 0.2, GR["u"][1], GR["w"][0], W1 + 0.2), "sub"))
    pr.append(("아래 벽 홈", list(NOTCH["xr"]), rect(NOTCH["u"][0] - 0.2, NOTCH["u"][1] + 0.01, NOTCH["w"][0] - 0.2, NOTCH["w"][1]), "sub"))
    return pr


def axle_clearance(xribs=None, with_plate=False):
    """leg axle M3x20 ISO 7380 inserted from -x: the head (D5.7 x 1.65 on the near-cheek outer face) and the whole screw
    on its way in (swept head cylinder xr near0 - L - head_h .. near0) against every drawn back prism (the near cheek it
    seats on excluded).  3-D gap = hypot(x gap, (u, w) gap of the circle R = head/2 around the pivot)."""
    near0 = CLV["near"][0]
    boxes = dict(head=[near0 - AX_HEAD["h"], near0], path=[near0 - AXLE_L - AX_HEAD["h"], near0])
    r = AX_HEAD["d"] / 2
    circ = circle(LEGP, r, 72)
    res = {}
    for key, (x0, x1) in boxes.items():
        best = (1e9, "")
        for name, xr, poly, kind in cradle_prisms(xribs):
            if kind != "add" or name.startswith("다리 걸이 (가까운") or (name == "뒷판" and not with_plate):
                continue
            dx = max(0.0, xr[0] - x1, x0 - xr[1])
            duw = poly_gap(circ, poly)
            gap = math.hypot(dx, max(duw, 0.0)) if (dx > 1e-9 or duw > 0) else duw
            if gap < best[0]:
                best = (gap, name)
        res[key] = best
    return res


AXLE_GAP = axle_clearance()
AXLE_GAP_PLATE = axle_clearance(with_plate=True)["path"]     # the head passes 0.65 over the plate back face (w13)
AXLE_GAP_U30 = axle_clearance([LEGP[0], XRIB[1]])            # regression: the rev-3 first rib on the axle line
check("leg axle head + insertion path over the plate back face >= 0.5", AXLE_GAP_PLATE[0] >= 0.5, f"{AXLE_GAP_PLATE[0]:.2f} ({AXLE_GAP_PLATE[1]})")
check("leg axle head + insertion path clear every back rib/pad/boss by >= 0.5 (drawn prisms) and = numbers axle_check",
      min(AXLE_GAP["head"][0], AXLE_GAP["path"][0]) >= 0.5 and abs(AXLE_GAP["head"][0] - CR["axle_check"]["min_head_gap"]) < 0.05
      and abs(AXLE_GAP["path"][0] - CR["axle_check"]["min_path_gap"]) < 0.05,
      f"head {AXLE_GAP['head'][0]:.2f} ({AXLE_GAP['head'][1]}), path {AXLE_GAP['path'][0]:.2f} ({AXLE_GAP['path'][1]})")
check("the same test catches a cross rib on the axle line u30 (rev-3 first)", AXLE_GAP_U30["head"][0] < -1.0,
      f"{AXLE_GAP_U30['head'][0]:.2f} ({AXLE_GAP_U30['head'][1]})")
check("low cross rib rule: u = pivot u - lug R - 1.2 - rib/2 (floor)",
      abs(XRIB[0] - math.floor(LEGP[0] - CLV["R"] - 1.2 - RIB_T / 2)) < 1e-9, XRIB[0])


def boss_section(xr0):
    """(adds, subs) of the D8 bosses (axis along w) cut by the plane xr = xr0."""
    adds, subs = [], []
    for xb in BO["xr"]:
        dx = abs(xr0 - xb)
        for ub in BO["u"]:
            if dx < BO["d"] / 2:
                h = math.sqrt((BO["d"] / 2) ** 2 - dx ** 2)
                adds.append(rect(ub - h, ub + h, BO["face_w"], RIB1))
            if dx < BO["hole_d"] / 2:
                h = math.sqrt((BO["hole_d"] / 2) ** 2 - dx ** 2)
                subs.append(rect(ub - h, ub + h, BO["face_w"] - 0.05, BO["seat_w"]))
            if dx < BO["cbore_d"] / 2:
                h = math.sqrt((BO["cbore_d"] / 2) ** 2 - dx ** 2)
                subs.append(rect(ub - h, ub + h, BO["seat_w"], RIB1 + 0.05))
    return adds, subs


def axle_holes(xr0):
    subs = []
    for side in ("left", "right"):
        e = HG[side]["ear"]
        if e[0] <= xr0 <= e[1]:
            subs.append(circle((UA, WA), KN_NEAR_HOLE / 2, 40))
    if CLV["near"][0] <= xr0 <= CLV["near"][1]:
        subs.append(circle(LEGP, LEG_HOLE / 2, 40))
    if CLV["far"][0] <= xr0 <= CLV["far"][1]:
        subs.append(circle(LEGP, FAR_HOLE / 2, 40))
    return subs


def cradle_section(xr0):
    """(add polygons, sub polygons) of the cradle cut by the plane xr = xr0 (local u, w)."""
    adds, subs = [], []
    for name, xr, poly, kind in cradle_prisms():
        if xr[0] - 1e-9 <= xr0 <= xr[1] + 1e-9:
            (adds if kind == "add" else subs).append(poly)
    ba, bs = boss_section(xr0)
    adds += ba
    subs += bs + axle_holes(xr0)
    return adds, subs


def cradle_behind(xr0):
    """polygons of the prisms entirely on the -x side of the plane (seen beyond the cut, looking toward -x)."""
    out = []
    for name, xr, poly, kind in cradle_prisms():
        if kind == "add" and xr[1] < xr0 - 1e-9:
            out.append(poly)
    for xb in BO["xr"]:
        if xb + BO["d"] / 2 < xr0:
            for ub in BO["u"]:
                out.append(rect(ub - BO["d"] / 2, ub + BO["d"] / 2, BO["face_w"], RIB1))
    return out


def screen_section(xr0):
    polys = []
    if abs(xr0) <= GX:
        polys.append(rect(0.0, GH, 0.0, GB))
        em = S["emboss"]
        if em["xr"][0] <= xr0 <= em["xr"][1]:
            polys.append(rect(em["u"][0], em["u"][1], GB, GB + em["h"]))
    return polys


# ------------------------------------------------------------------ plan helpers (world x, y)
CONTENTS = {c["id"]: c for c in BODY["centre_contents"]}


def bbox_xy(cid):
    b = CONTENTS[cid]["bbox_x0x1y0y1z0z1"]
    return b[0], b[1], b[2], b[3]


def bbox_z(cid):
    b = CONTENTS[cid]["bbox_x0x1y0y1z0z1"]
    return b[4], b[5]


RB_W = RB["ffc_w"]


def ribbon_route():
    """named points of numbers.ribbon waypoints: hole top, run level under the lid (hole bottom), 45 deg fold corner (y run
    -> x run), drop column top, drop bottom (landing on the micro-HDMI), end of the landing, DISP1 mouth.  Found by the
    shape of the path (not by a fixed count) so a changed route fails loudly."""
    wp = [tuple(q) for q in RB["waypoints"]]
    hole, run0 = wp[0], wp[1]
    assert abs(hole[0] - run0[0]) < 1e-6 and abs(hole[1] - run0[1]) < 1e-6 and run0[2] < hole[2], "ribbon: first piece must go straight down the hole"
    i = 2
    corner = wp[i]
    assert abs(corner[0] - run0[0]) < 1e-6 and abs(corner[2] - run0[2]) < 1e-6, "ribbon: +y run expected under the lid"
    drop = wp[i + 1]
    assert abs(drop[1] - corner[1]) < 1e-6 and abs(drop[2] - corner[2]) < 1e-6, "ribbon: x run expected after the 45 deg fold"
    rest = wp[i + 2:]
    drop_b = rest[0]
    assert abs(drop_b[0] - drop[0]) < 1e-6 and drop_b[2] < drop[2], "ribbon: vertical drop expected in the column"
    mouth = rest[-1]
    land = rest[1:-1]
    return dict(hole=hole, run0=run0, corner=corner, drop=drop, drop_b=drop_b, land=land, mouth=mouth)


def ribbon_plan_rects():
    """ribbon band under the lid (plan) from numbers.ribbon waypoints."""
    r = ribbon_route()
    h = RB_W / 2
    run0, corner, drop, mouth = r["run0"], r["corner"], r["drop"], r["mouth"]
    return dict(run_y=rect(run0[0] - h, run0[0] + h, run0[1], corner[1] + h),
                run_x=rect(min(drop[0], corner[0]) - h, max(drop[0], corner[0]) + h, corner[1] - h, corner[1] + h),
                fold=(corner[0], corner[1]), drop=(drop[0], drop[1]),
                into=rect(min(drop[0], mouth[0]), max(drop[0], mouth[0]), mouth[1] - h, mouth[1] + h), hole=(r["hole"][0], r["hole"][1]),
                run_x_len=abs(corner[0] - drop[0]), run_y_len=abs(corner[1] - run0[1]))


RR = ribbon_route()
RI = RB["route_info"]
check("ribbon pieces under the lid = waypoint distances (run y, run x, drop, landing, approach)",
      abs(abs(RR["corner"][1] - RR["run0"][1]) - RB["parts"]["run_y"]) < 0.01 and abs(abs(RR["corner"][0] - RR["drop"][0]) - RB["parts"]["run_x"]) < 0.01
      and abs((RR["drop"][2] - RR["drop_b"][2]) - RB["parts"]["drop"]) < 0.01
      and len(RR["land"]) == 1 and abs(math.dist(RR["drop_b"], RR["land"][0]) - RB["parts"]["over_obstacle"]) < 0.01
      and abs(math.dist(RR["land"][-1], RR["mouth"]) - RB["parts"]["into_mouth"]) < 0.01)
_app = math.degrees(math.atan2(RR["land"][-1][2] - RR["mouth"][2], RR["mouth"][0] - RR["land"][-1][0])) if RR["land"] else None
check("ribbon lands on the micro-HDMI top and enters the mouth at the stated angle (route_info)",
      RR["land"] and abs(RR["drop_b"][2] - RI["z_land"]) < 1e-6 and abs(RI["z_land"] - PI["hdmi"]["top_z"] - RB["ffc_t"] / 2) < 0.01
      and abs(_app - RI["approach_deg"]) < 0.05, f"{_app:.2f} deg")
check("drop column x = mouth - (stiffener 3.0 + R3) (route_info rule)",
      abs(RR["drop"][0] - (PI["disp1"]["mouth"][0] + PI["disp1"]["mouth_dir"][0] * (3.0 + RB["bend_R"]))) < 0.01, RR["drop"][0])
check("Pi end insertion = min(3.5, connector depth - 0.3)", abs(RB["pi_end_insert"] - min(3.5, PI["disp1"]["depth"] - 0.3)) < 1e-6, RB["pi_end_insert"])


GP2, GP6 = PI["gpio_pin2"], PI["gpio_pin6"]
PIN_PITCH = (GP6[0] - GP2[0]) / 2.0


def _slice(poly, u0):
    """w intervals of a closed (u, w) polygon on the line u = u0."""
    ws = []
    n = len(poly)
    for i in range(n):
        (a1, b1), (a2, b2) = poly[i], poly[(i + 1) % n]
        if (a1 <= u0 < a2) or (a2 <= u0 < a1):
            ws.append(b1 + (b2 - b1) * (u0 - a1) / (a2 - a1))
    ws.sort()
    return [(ws[i], ws[i + 1]) for i in range(0, len(ws) - 1, 2)]


def cradle_section_u(u0):
    """(add, sub) rectangles in the (xr, w) plane of the cradle cut by u = u0 (bosses as w-axis cylinders)."""
    adds, subs = [], []
    for name, xr, poly, kind in cradle_prisms():
        for (w0, w1) in _slice(poly, u0):
            (adds if kind == "add" else subs).append(rect(xr[0], xr[1], w0, w1))
    for xb in BO["xr"]:
        for ub in BO["u"]:
            du = abs(u0 - ub)
            if du < BO["d"] / 2:
                h = math.sqrt((BO["d"] / 2) ** 2 - du ** 2)
                adds.append(rect(xb - h, xb + h, BO["face_w"], RIB1))
            if du < BO["hole_d"] / 2:
                h = math.sqrt((BO["hole_d"] / 2) ** 2 - du ** 2)
                subs.append(rect(xb - h, xb + h, BO["face_w"] - 0.05, BO["seat_w"]))
            if du < BO["cbore_d"] / 2:
                h = math.sqrt((BO["cbore_d"] / 2) ** 2 - du ** 2)
                subs.append(rect(xb - h, xb + h, BO["seat_w"], RIB1 + 0.05))
    # holes along x through the lugs / ears when the plane passes the axis
    if abs(u0 - LEGP[0]) < 1e-6:
        subs.append(rect(CLV["near"][0] - 0.05, CLV["near"][1] + 0.05, LEGP[1] - LEG_HOLE / 2, LEGP[1] + LEG_HOLE / 2))
        subs.append(rect(CLV["far"][0] - 0.05, CLV["far"][1] + 0.05, LEGP[1] - FAR_HOLE / 2, LEGP[1] + FAR_HOLE / 2))
    if abs(u0 - UA) < 1e-6:
        for side in ("left", "right"):
            e = HG[side]["ear"]
            subs.append(rect(e[0] - 0.05, e[1] + 0.05, WA - KN_NEAR_HOLE / 2, WA + KN_NEAR_HOLE / 2))
    return adds, subs


EAR_U = [min(p[0] for p in EAR_PROFILE), max(p[0] for p in EAR_PROFILE)]
EAR_W = [min(p[1] for p in EAR_PROFILE), max(p[1] for p in EAR_PROFILE)]
LUG_W = [RIB0, LEGP[1] + CLV["R"]]
M25_HEAD = dict(d=4.5, h=2.5)        # ISO 4762 M2.5 socket head (for the phantom only)
M3_HEAD = dict(AX_HEAD)              # 3a: the four M3x20 are ISO 7380 (button head D5.7 x 1.65), same bag for hinges and leg


def spec_tag(section, n):
    """change tag (【새로】/【변경】/【그대로】...) of item n in CAD_SPEC_rev3.md section 'A' / 'C' / 'E' ('' if untagged)."""
    heads = [m.start() for m in re.finditer(r"^## ", SPEC, re.M)] + [len(SPEC)]
    a = SPEC.index(f"## {section}.")
    b = min(h for h in heads if h > a)
    m = re.search(rf"^{n}\) (【[^】]+】)?", SPEC[a:b], re.M)
    return (m.group(1) or "") if m else ""


PRINT_H_CRADLE = U1 - EAR_U[0]
check("print height standing on the top edge = u103.5 - heel u (drawn ear) = numbers print_height = CAD_SPEC C-17",
      abs(PRINT_H_CRADLE - CR["print_height"]) < 0.01 and f"높이는 {CR['print_height']:g}" in SPEC, PRINT_H_CRADLE)


# ------------------------------------------------------------------ small parts (t05)
DJ = json.load(open(os.path.join(DESIGN, "design.json")))
HW = {}
for m in re.finditer(r"(M\d(?:\.\d)?×\d+) [×+](\d+)", DJ["materials_note"]):
    HW[m.group(1)] = int(m.group(2))
_sc = spec_nums(r"화면 덮개 (\d+)×(\d+)×(\d+)", 3)
SCREEN_COVER = dict(size=_sc)
PRINTED = DJ["printed_parts"]
# inspection-window cover (CAD_SPEC E-1): plug = window minus plug_under on each side (interpretation), thickness = plate;
# flange = window plus 'flange' on each side, thickness t; dome cavity (rolled ribbon fold) to inner_to_w, skin 1.2
_skin = spec_nums(r"바깥 살 (\d+(?:\.\d+)?)", 1)
COV = dict(plug=[INSP["xr"][0] + COVER["plug_under"], INSP["xr"][1] - COVER["plug_under"], INSP["u"][0] + COVER["plug_under"], INSP["u"][1] - COVER["plug_under"]],
           plug_w=[PL_IN, PL_OUT], flange=[INSP["xr"][0] - COVER["flange"], INSP["xr"][1] + COVER["flange"], INSP["u"][0] - COVER["flange"], INSP["u"][1] + COVER["flange"]],
           flange_w=[PL_OUT, PL_OUT + COVER["t"]], cav=[COVER["dome"]["xr"][0], COVER["dome"]["xr"][1], COVER["dome"]["u"][0], COVER["dome"]["u"][1]],
           cav_w=[PL_IN, COVER["dome"]["inner_to_w"]], skin=_skin[0] if _skin else 1.2)
COV["dome"] = [COV["cav"][0] - COV["skin"], COV["cav"][1] + COV["skin"], COV["cav"][2] - COV["skin"], COV["cav"][3] + COV["skin"]]
COV["dome_w"] = [PL_OUT, COV["cav_w"][1] + COV["skin"]]
check("cover flange stays inside the window rib (flange < rib offset)", COV["flange"][0] > WRIB_IN[0] and COV["flange"][1] < WRIB_IN[1])
check("cover dome inside the plug outline", COV["dome"][0] >= COV["plug"][0] and COV["dome"][1] <= COV["plug"][1] and COV["dome"][2] >= COV["plug"][2] and COV["dome"][3] <= COV["plug"][3])
# ribbon clip (CAD_SPEC E-2, v13 deviation 4): 30 x 12 x 3 with two pins D3.0 into the lid holes D3.1 x 5
CLIP_PART = dict(L=CLIP_SIZE[0], W=CLIP_SIZE[1], T=CLIP_SIZE[2], pin_d=PIN_D, pin_dx=abs(CL["pins"][1][0] - CL["pins"][0][0]) / 2,
                 pin_len=CL["pin_len"], hole=PIN_HOLE)
check("clip pins inside the clip", CLIP_PART["pin_dx"] + PIN_D / 2 < CLIP_PART["L"] / 2)
check("ribbon between the clip pins", CLIP_PART["pin_dx"] - PIN_D / 2 > RB_W / 2)
PW_X = PW["waypoints"][0][0]
HOLE_XC = (HO["x"][0] + HO["x"][1]) / 2
check("power wire lane between the ribbon edge and the right pin", HOLE_XC + RB_W / 2 < PW_X < CL["pins"][1][0] - PIN_D / 2,
      f"{HOLE_XC + RB_W / 2:.2f} < {PW_X} < {CL['pins'][1][0] - PIN_D / 2:.2f}")
CLIP_RIB_EDGE, CLIP_PIN_EDGE = HOLE_XC + RB_W / 2, CL["pins"][1][0] - PIN_D / 2
check("clip wire groove: wire lane inside the groove, groove between the ribbon edge and the pin (numbers ribbon_edge_x / pin_edge_x)",
      WG["x"][0] < PW_X < WG["x"][1] and WG["x"][0] > CLIP_RIB_EDGE and WG["x"][1] < CLIP_PIN_EDGE
      and abs(CLIP_RIB_EDGE - CL["ribbon_edge_x"]) < 0.01 and abs(CLIP_PIN_EDGE - CL["pin_edge_x"]) < 0.01,
      f"rib {CLIP_RIB_EDGE:.2f} | groove {WG['x']} | pin {CLIP_PIN_EDGE:.2f}")
check("power wire runs in the clip groove (z between the groove floor and the clip top)",
      CLIP_Z[1] - WG["depth"] < PW["waypoints"][1][2] < CLIP_Z[1], PW["waypoints"][1][2])


# ------------------------------------------------------------------ wiring (t06): circuit designators from the netlist copies
def _csv(name):
    with open(os.path.join(HERE, "ctx", name), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


CABLES = {r["W"]: r for r in _csv("cables.csv")}
BOM = {r["부품"]: r for r in _csv("bom.csv") if r["도면"] == "SCH-06"}
NETS = [r for r in _csv("netlist.csv") if r["도면"] == "SCH-06" and r["넷"] in ("+5V_PI", "GND")]


def pin_of(part, net):
    for r in NETS:
        if r["부품"] == part and r["넷"] == net:
            return r["핀"]
    return ""


POWER_CHAIN = ["A603", "P603", "X601", "X602", "X603", "X604", "P604", "A605"]
check("power chain parts all in the SCH-06 BOM", all(p in BOM for p in POWER_CHAIN) or all(p in BOM for p in POWER_CHAIN[1:]), [p for p in POWER_CHAIN if p not in BOM])
check("X604 pin 1 = +5V, pin 3 = GND (netlist)", pin_of("X604", "+5V_PI") == "1" and pin_of("X604", "GND") == "3")
check("A605 pin 1 = 5V, pin 2 = GND (netlist)", pin_of("A605", "+5V_PI") == "1" and pin_of("A605", "GND") == "2")
JUMPER_MM = [float(v) * 10 for v in re.findall(r"(\d+) cm", CABLES["W606"]["길이"] + " " + CABLES["W607"]["길이"])]
WS_EST = [PW["available"][0] - sum(JUMPER_MM), PW["available"][1] - sum(JUMPER_MM)]
check("W606 + W607 = 400 mm and the WS lead estimate = available - 400", abs(sum(JUMPER_MM) - 400.0) < 1e-6, WS_EST)
# DSI FFC developed length, in order along the cable from the screen ZIF to the Pi ZIF
RIBSEG = []
_ic = RB["in_cradle_parts"]
_up = RB["parts"]
for key, lab, kind in (("screen_insert", "화면 ZIF 안", "ins"), ("screen_exit_to_fold", "입구 → 접기", "run"), ("fold_square", "접기 자리", "fold"),
                       ("fold_roll_allowance", "접기 말림", "fold"), ("descend_to_cradle_bottom", "받침 안 내려감", "run"), ("depth_jog", "홈으로", "run"),
                       ("hinge_loop", "경첩 고리", "loop")):
    RIBSEG.append(dict(L=_ic[key], lab=lab, kind=kind, src="in_cradle_parts." + key))
_UPSEG = (("through_lid", "뚜껑 구멍", "run"), ("down_to_run", "뚜껑 밑으로", "bend"), ("run_y", "+y 길", "run"), ("fold_roll_allowance", "45° 접기", "fold"),
          ("run_x", "−x 길", "run"), ("drop", "기둥 안 내려감", "run"), ("over_obstacle", "HDMI 위", "run"), ("into_mouth", "입구로", "run"),
          ("corner_rounding", "굽힘 모서리 보정", "corr"))
check("every numbers ribbon.parts key has a drawing label (no silent new piece)", set(_up) == {k for k, _, _ in _UPSEG}, sorted(set(_up) ^ {k for k, _, _ in _UPSEG}))
for key, lab, kind in _UPSEG:
    RIBSEG.append(dict(L=_up.get(key, 0.0), lab=lab, kind=kind, src="parts." + key))
RIBSEG.append(dict(L=RB["pi_end_insert"], lab="Pi ZIF 안", kind="ins", src="pi_end_insert"))
check("ribbon segments sum = numbers ribbon total", abs(sum(s["L"] for s in RIBSEG) - RB["total"]) < 0.05, f"{sum(s['L'] for s in RIBSEG):.2f} vs {RB['total']}")
PWSEG = [("mx_exit_to_wire_lane", "MX1.25 → 선 길"), ("down_to_cradle_bottom", "받침 안 내려감"), ("hinge_loop", "경첩 고리"),
         ("lid_top_to_run", "뚜껑 윗면 → 클립 홈"), ("run_to_gpio", "뚜껑 밑 → GPIO"), ("dupont_and_slack", "핀 꽂기·여유")]
check("every numbers power_wire.parts key has a drawing label", set(PW["parts"]) == {k for k, _ in PWSEG}, sorted(set(PW["parts"]) ^ {k for k, _ in PWSEG}))
check("power wire segments sum = numbers total", abs(sum(PW["parts"].get(k, 0.0) for k, _ in PWSEG) - PW["total"]) < 0.05)
_wp = PW["waypoints"]
_pw_len = sum(math.dist(_wp[i], _wp[i + 1]) for i in range(len(_wp) - 1))
check("power wire: lid top -> run -> GPIO pieces = waypoint polyline length (each piece counted once)",
      abs(_pw_len - (PW["parts"]["lid_top_to_run"] + PW["parts"]["run_to_gpio"])) < 0.05, f"{_pw_len:.2f}")


# ------------------------------------------------------------------ context sizes parsed from the L2 text fields
_ft = re.search(r"(\d+)×(\d+)", FEET_RB["type"])
FOOT_D = float(_ft.group(1))
DUCT = BODY["cable_duct"]["cross_section"]
M25_L = float(re.search(r"M2\.5x(\d+)", BO["screw"]).group(1))


# ------------------------------------------------------------------ Pi 5 orientation read from the L2 note (not assumed)
_pi_ct = CONTENTS["CU-E-PI5"]
_m1 = re.search(r"USB/RJ45 end\s*([+-][xy])", _pi_ct["name"] + " " + _pi_ct.get("note", ""))
_m2 = re.search(r"GPIO edge\s*([+-][xy])", _pi_ct["name"] + " " + _pi_ct.get("note", ""))
_ax = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}
PI_ROT_DWG = None
if _m1 and _m2:
    ex, ey = _ax[_m1.group(1)], _ax[_m2.group(1)]
    PI_ROT_DWG = int(round(math.degrees(math.atan2(ex[1], ex[0])))) % 360
check("Pi 5 rotation parsed from the L2 note (body_L2 CU-E-PI5) = numbers pi5.rot_deg", PI_ROT_DWG is not None and PI_ROT_DWG == PI["rot_deg"] % 360,
      f"note '{_pi_ct['name']}' -> {PI_ROT_DWG}")
_d1c = CONTENTS["CU-E-PI5-DISP1"]["bbox_x0x1y0y1z0z1"]
check("drawn CAM/DISP 1 box within 1.5 of the CAD box; mouth on the -x face when mouth_dir = -x",
      max(abs(PI["disp1"]["x"][0] - _d1c[0]), abs(PI["disp1"]["x"][1] - _d1c[1]), abs(PI["disp1"]["y"][0] - _d1c[2]), abs(PI["disp1"]["y"][1] - _d1c[3])) <= 1.5
      and abs(PI["disp1"]["mouth"][0] - (PI["disp1"]["x"][0] if PI["disp1"]["mouth_dir"][0] < 0 else PI["disp1"]["x"][1])) < 1e-6, _d1c)
DIR_TXT = {(1, 0): "+x", (-1, 0): "−x", (0, 1): "+y", (0, -1): "−y"}
MOUTH_TXT = DIR_TXT[tuple(PI["disp1"]["mouth_dir"])]
check("placement pi5_mipi mouth_dir = pi5.disp1 mouth_dir", tuple(PL["pi5_mipi"]["mouth_dir"]) == tuple(PI["disp1"]["mouth_dir"]))

# ------------------------------------------------------------------ leg deploy / stow order (numbers leg.swing), re-measured
SWING = LG["swing"]
_edge = [(PK["back_wall_y"], LID["top_z"] - LG["pocket_edge_C"]), (PK["back_wall_y"] + LG["pocket_edge_C"], LID["top_z"])]
SW_D = {k: min(_dseg(tuple(SWING[k]["pivot"]), *_edge), math.dist(SWING[k]["pivot"], _edge[0])) for k in ("at_25", "at_22")}
FOOT_REACH = LEG_L + LEG_R
check("leg swing: back-wall top edge (C0.5) nearer than the foot reach at 25 deg, farther at 22 deg (numbers leg.swing)",
      SW_D["at_25"] < FOOT_REACH < SW_D["at_22"] and abs(SW_D["at_25"] - SWING["at_25"]["back_edge_dist"]) < 0.03
      and abs(SW_D["at_22"] - SWING["at_22"]["back_edge_dist"]) < 0.03 and abs(FOOT_REACH - SWING["at_25"]["foot_reach"]) < 1e-6,
      f"25: {SW_D['at_25']:.2f} / 22: {SW_D['at_22']:.2f} vs reach {FOOT_REACH}")
check("leg pivot at 22 deg = pose formula", math.dist(P(LEGP[0], LEGP[1], TH_HEEL), LG["pivot22_yz"]) < 0.02)

# ------------------------------------------------------------------ plan footprint of the standing cradle / sight lines (numbers)
FP = N["footprint_y"]
check("footprint 25 deg front/rear and 22 deg front = pose formula", abs(min(P(u, w, TH_USE)[0] for u, w in CORNERS) - FP["front_25"]) < 0.02
      and abs(max(P(u, w, TH_USE)[0] for u, w in CORNERS) - FP["rear_25"]) < 0.02 and abs(min(P(u, w, TH_HEEL)[0] for u, w in CORNERS + EAR_PROFILE) - FP["front_22"]) < 0.02)
SVC = N["service_O4"]
STUD = N["variants"]["corner_studs_bored"]
BODY_MD5_OK = md5(F_BODY)[:8] == PL["body_L2"]["md5"][:8]
check("drawing context body_L2.json = the design copy (numbers placement.body_L2 md5)", BODY_MD5_OK, md5(F_BODY)[:8])
