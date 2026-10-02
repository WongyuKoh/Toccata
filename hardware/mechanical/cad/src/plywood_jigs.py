#!/usr/bin/env python3
"""Toccata L2 - 3D-printed drilling jigs for the okoume plywood pieces (new 2026-10-02; how to use: cad/jigs/README.md).

    build()                                # -> [{name, solid, qty, required, note}] for build_all.py, which writes
                                           #    required -> stl/print/08_합판지그/, optional -> stl/print_extra/선택_합판지그/
    python3 src/plywood_jigs.py            # table only (size, rough grams / minutes); writes nothing
    python3 src/plywood_jigs.py --write D  # write the STLs to D/08_합판지그 + D/선택_합판지그 (same names as build_all)
    python3 src/check_plywood_jigs.py      # writes to a temp dir, then watertight / bed size / bores measured back from the
                                           # STLs vs the body.py model

Every hole position is read from body.py (the CAD model that is built), never typed again here:
  TS_YZ (thumb-screw axes = L73 insert pilots in the pod inner panels = rubber-sleeve holes in the end walls), WIRE_YZ (pod D6),
  END_HOLE_YZ (end-wall D14 XT30 hole), MAG_BACK_X / MAG_END (edge + lid magnet seats), LIDL_SLOTS / LIDR_SLOTS / BACK_SLOTS /
  BOT_SLOTS_BUCK / BOT_SLOTS_PI (4 mm vent slots), panel extents (Y0, YB, YBI, ZB, Z_LIDU, Z_LID, CU_X, CU_IX, LIDS, RISER, DUCT_Z).

Jigs (all PETG, 0.2 mm layers, no supports):
  J-a1/a2  pod inner side panel L / R (joint face)  - L73 insert pilots D5.8 x 8 blind + speaker-wire hole D6 through
  J-a3/a4  centre end wall L / R (inner face)        - rubber-sleeve holes D8 through + XT30 pilot D4 (opened to D14 afterwards)
           all four register on the front edge above the 27 x 22 duct notch and on the bottom edge behind it, with the SAME (u, v)
           numbers, so the end-wall holes and the pod holes are coaxial; a key block fills the notch (the jig only sits flat on the
           face that the drawing calls L or R) and the end-wall jigs carry a guard over the end-wall top edge (they cannot sit on a pod
           panel - the XT30 pilot can never go into a sealed speaker box)
  J-a5     D14 marking disc (pin in the D4 pilot, trace the XT30 circle)
  J-b      edge magnet-seat saddles, gaps 11.3 / 11.6 / 11.9 / 12.2 (take the tightest that slides on) - D8 guide centred in the
           11.5 edge, sight grooves for a pencil line (back ply top edge 30 / 120 / 473 / 675, end walls u61)
  J-c1/c2  lid L / R underside magnet templates (3 seats each, registered on the back edge + the end over the end wall; a 2 mm
           tongue drops into one exhaust slot drilled with J-d first, so a plain-rectangle lid takes the template one way only;
           2 mm, not 3: the drilled slot is only ~3.2 clear (cusps + slider play) and lid R's slot is set from the OTHER end, so the
           tongue must also take a +-0.5 lid-length error - verified 2026-10-02)
  J-d1..4  4 mm slot templates: frame (fences on the board edges, clamped once) + slider (D4.2 guides at 4p) + shim p:
           passes A (0), B (2p), C (p), D (3p) -> D4 holes at pitch p <= 2.0 along every slot (cusps <= 0.27 nominal, <= 0.30
           with the +0.1 travel allowance for a window printed 0..0.2 short); a pin in the frame window lets the slider in one way
           J-d1 lid L (6), J-d2 lid R (10), J-d3 back ply (8, registered on the end far from the window), J-d4 bottom ply (6 + 8,
           back edge + a pencil line 200 from the left end)
  J-e      depth gauges (set the bit stick-out from the chuck = chuck stop on the guide top, or a tape flag: insert 5.8 & 5.5
           -> 8, thin board (<= 11.3, the 11.3 saddle slides on) 5.8 -> 7.6, magnet 8 -> 3.2, cone 118 deg)
           + test guides (through) for trying the bits / insert / magnet fit on an offcut first
  J-f      (optional) sanding stick for the 4 mm slots: 2.0 blade, sandpaper on one face (no needle file needed)

Frames: each jig is built in its USE frame (u, v, w): w = 0 is the drilled wood face, +w out of it (toward the drill),
u x v = w; the placements map the use frame to the world (body.py coordinates) for the checks; the print frame puts the jig on
the bed without supports.  Guide length from the wood face to the guide top = GUIDE (14) for every bore, so one gauge per
bit/depth works for every jig.  Printed holes come out small: bore = bit + BORE_CLR, ream once with the same bit.
"""
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl_toccata"))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from manifold3d import Manifold  # noqa: E402

from cadlib import box, cone_z, cyl_z, diff, orient, prism_x, prism_z, rot_x, text_xy, union, write_stl  # noqa: E402
import body as B  # noqa: E402   (read-only: the model numbers)

PRINT_SUB, EXTRA_SUB = "08_합판지그", "선택_합판지그"     # build_all: stl/print/<PRINT_SUB>, stl/print_extra/<EXTRA_SUB>

# ============================================================================ parameters (change here, re-run)
PLY_T = B.T                    # 11.5 okoume (model); real boards vary -> J-b comes in 4 gaps
SADDLE_GAPS = (11.3, 11.6, 11.9, 12.2)
BIT_INSERT = B.QS_HOLE[0]      # 5.8  L73 Norelem 07653-04 pilot (README: 5.5 if loose)
BIT_INSERT_ALT = 5.5
BIT_WIRE = B.WIRE_D            # 6.0  speaker lead hole (pod inner panel, sealed later)
BIT_SLEEVE = B.SLV[0]          # 8.0  rubber sleeve hole (end walls)
BIT_PILOT = 4.0                # 4.0  XT30 pilot (owned HSS SD 4.0), opened to D14 afterwards
BIT_MAG = B.MAG[0]             # 8.0  magnet seat
BIT_SLOT = 4.0                 # 4.0  vent slots
DEPTH_INSERT = B.QS_HOLE[1]    # 8.0  full-diameter depth of the blind insert hole
DEPTH_INSERT_THIN = 7.6        # board <= 11.3 (the 11.3 saddle slides on): 7.6 + 1.74 tip leaves >= 1.66 at 11.0 (rule >= 1.5)
DEPTH_MAG = B.MAG[2]           # 3.2  full-diameter depth of the magnet seat
POINT_DEG = 118.0              # HSS twist drill point angle (the gauges' cone)
BORE_CLR = 0.2                 # guide bore = bit + 0.2 (prints ~0.1-0.2 small; ream once with the same bit)
GUIDE = 14.0                   # guide length: wood face -> guide top (>= 12)
PLATE_T = 4.0                  # top plate of the table jigs (J-a, J-c) / slider plate
FRAME_T = 5.0                  # slot frame plate (lies on the wood, guides the slider)
WALL = 3.0                     # guide boss wall
FENCE_T = 4.0                  # fence thickness
FENCE_DROP = 7.0               # fence / key / guard length below the wood face (< 11.5)
GUARD_CLR = 1.0                # end-wall guard above the end-wall top edge
PAD_D = 10.0                   # extra contact pads (table jigs)
ENGRAVE = 0.8                  # engraved labels (use-top face = bed face in print)
RAISE = 0.6                    # raised labels (slider tab, printed face up)
SLOT_PMAX = 2.0                # target hole pitch along a slot (D4: cusp 0.27 at 2.0; 0.30 at 2.107)
SLOT_END = 2.0                 # first / last hole centre 2.0 inside the slot ends (D4 stays inside the slot length)
SLIDER_M = 2.5                 # slider wall beyond the bore ends (t)
SLIDER_MC = 4.5                # slider wall beyond the outer rows (c)
SLIDE_CLR = 0.15               # slider <-> frame window, each side (c)
TRAVEL_EXTRA = 0.1             # window travel = 3p + 0.1 (printed windows come out ~0.1-0.2 short)
FRAME_B = 8.0                  # frame border
KEY_PIN = (2.5, 2.0)           # frame pin (t length = travel + 2.5, c protrusion) in the slider window -> the slider fits one way only
SHIM_W, SHIM_HANDLE = 24.0, 8.0
SLOT_KEY_W = 2.0               # J-c tongue width (drilled slot clear width ~3.2 after cusps + slider c-play; +-0.5 lid length on J-c2)
DISC_T = 2.5                   # J-a5 disc thickness (label engraved 0.8 in the visible face -> 1.7 floor >= 1.6 wall)
SIGHT_U = 200.0                # bottom ply: pencil line 200 mm from the LEFT end
SADDLE_L, SADDLE_C, SADDLE_D = 30.0, 4.5, 10.0
XT30_D = B.END_HOLE_D          # 14

R_FLIP = rot_x(180.0)          # use-top face down on the bed
R_NONE = np.eye(3)


def bore(bit):
    return round(bit + BORE_CLR, 3)


def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def engrave(s, size, u, v, top, rot=0.0, heavy=False, halign="center", valign="center"):
    return text_xy(s, size, ENGRAVE + 0.02, x=u, y=v, z=top - ENGRAVE, halign=halign, valign=valign, rot=rot, heavy=heavy)


def raised(s, size, u, v, top, rot=0.0, heavy=False, halign="center", valign="center"):
    return text_xy(s, size, RAISE + 0.01, x=u, y=v, z=top - 0.01, halign=halign, valign=valign, rot=rot, heavy=heavy)


def frame_R(u, v):
    """3x3 matrix with columns = world directions of local u, v, w (w = u x v)."""
    u, v = np.array(u, float), np.array(v, float)
    return np.column_stack([u, v, np.cross(u, v)])


class Jig:
    def __init__(self, key, file, title, local, R_print=R_NONE, placements=None, bores=None, meta=None):
        self.key, self.file, self.title, self.local = key, file, title, local
        self.R_print = np.array(R_print, float)
        self.placements = placements or {}      # name -> (R 3x3, origin 3) local -> world
        self.bores = bores or []                # dicts: name, u, v, d (bore), bit, kind, target (world point), axis (world dir)
        self.meta = meta or {}
        m = orient(local, self.R_print)
        x0, y0, z0, _, _, _ = m.bounding_box()
        self.t_print = np.array([-x0, -y0, -z0])
        self.printed = m.translate(tuple(self.t_print))

    def to_print(self, p_local):
        return self.R_print @ np.asarray(p_local, float) + self.t_print

    def world(self, name, p_local):
        R, o = self.placements[name]
        return np.asarray(R) @ np.asarray(p_local, float) + np.asarray(o)

    def world_solid(self, name):
        R, o = self.placements[name]
        M = np.zeros((3, 4))
        M[:, :3] = R
        M[:, 3] = o
        return self.local.transform(M)


# ============================================================================ model numbers -> board coordinates
Y0, YB, YBI, ZB = B.Y0, B.YB, B.YBI, B.ZB
NOTCH_P = B.RISER[0] - Y0                  # 27  duct notch depth from the front edge
NOTCH_V = B.DUCT_Z[1] - ZB                 # 22  duct notch height from the bottom edge
POD_DEPTH = YB - Y0                        # 128.5
POD_FRONT_TOP = B.Z_FB - ZB                # 60.42 front edge of the pod side panel (then the 4.25 step + 40 deg slant)
END_DEPTH = YBI - Y0                       # 117
END_TOP = B.Z_LIDU - ZB                    # 56.35
X_POD_FACE = {"L": B.SPK_X["L"][1], "R": B.SPK_X["R"][0]}       # 257 / 965 pod inner-panel joint faces
X_END_IN = {"L": B.CU_IX[0], "R": B.CU_IX[1]}                   # 271.5 / 950.5 end-wall inner faces
SGN = {"L": 1.0, "R": -1.0}                                     # local u = SGN * (y - 214)


def pv(y, z):
    return (y - Y0, z - ZB)


# ============================================================================ J-a  side panel / end wall jigs

def j_a(kind, side):
    """kind 'pod' (pod inner side panel, joint face) or 'end' (centre end wall, inner face). Built in board coordinates
    (p = distance from the front edge, v = from the bottom edge), then mirrored to u = -p for R."""
    s = SGN[side]
    if kind == "pod":
        holes = [dict(name="insert%d" % (k + 1), p=pv(*yz)[0], v=pv(*yz)[1], bit=BIT_INSERT, kind="blind",
                      depth=DEPTH_INSERT, label="5.8 막힘") for k, yz in enumerate(B.TS_YZ[side])]
        wy, wz = B.WIRE_YZ[side]
        holes.append(dict(name="wire", p=pv(wy, wz)[0], v=pv(wy, wz)[1], bit=BIT_WIRE, kind="through", label="6 관통"))
        x_face = X_POD_FACE[side]
        depth, top_v = POD_DEPTH, POD_FRONT_TOP
    else:
        holes = [dict(name="sleeve%d" % (k + 1), p=pv(*yz)[0], v=pv(*yz)[1], bit=BIT_SLEEVE, kind="through", label="8 관통")
                 for k, yz in enumerate(B.TS_YZ[side])]
        ey, ez = B.END_HOLE_YZ[side]
        holes.append(dict(name="xt30", p=pv(ey, ez)[0], v=pv(ey, ez)[1], bit=BIT_PILOT, kind="through", label="4 안내"))
        x_face = X_END_IN[side]
        depth, top_v = END_DEPTH, END_TOP
    for h in holes:
        h["d"] = bore(h["bit"])
        h["boss"] = h["d"] + 2 * WALL
    p_end = 118.0
    v_plate = 56.0
    plate = [rect(-FENCE_T, p_end, -FENCE_T, v_plate)]
    guard = None
    if kind == "end":
        g0 = END_TOP + GUARD_CLR
        guard = (8.0, 60.0, g0, g0 + FENCE_T)
        plate.append(rect(guard[0], guard[1], v_plate - 1.0, guard[3]))
    pads = [(60.0, 7.0), (112.0, 7.0), (60.0, 50.0), (6.0, 50.0)]
    # lightening / viewing windows (hand-placed clear of every boss and pad by >= 2.9)
    win = {("pod", "L"): [(38, 92, 15, 41)], ("pod", "R"): [(38, 64, 15, 41)],
           ("end", "L"): [(38, 89, 15, 41)], ("end", "R"): [(30, 64, 15, 36)]}[(kind, side)]
    fences = [(-FENCE_T, 0.0, NOTCH_V + 1.0, 55.0),                    # front fence (front edge above the notch)
              (NOTCH_P + 1.0, 114.0, -FENCE_T, 0.0)]                   # bottom fence (bottom edge behind the notch)
    # key block in the 27 x 22 notch: 2.5 clear of the sawn 27 edge, 6 clear of the 22 edge.  It reaches u24.5 > 22, so the jig
    # cannot sit turned 90 deg on the other face either (fences swapped: the key would land on the wood beside a 22-wide notch)
    key = (6.0, NOTCH_P - 2.5, 4.0, NOTCH_V - 6.0)
    pl = union([prism_z(p, GUIDE - PLATE_T, GUIDE) for p in plate])
    pl = diff(pl, [prism_z(rect(*w), GUIDE - PLATE_T - 1, GUIDE + 1) for w in win])
    parts = [pl]
    top_in = GUIDE - 1.0                                # bosses / pads end inside the plate (no coplanar top-face slivers)
    parts += [cyl_z(h["p"], h["v"], 0.0, top_in, h["boss"]) for h in holes]
    parts += [cyl_z(a, b, 0.0, top_in, PAD_D) for (a, b) in pads]
    parts += [box(f[0], f[1], f[2], f[3], -FENCE_DROP, GUIDE) for f in fences]
    parts.append(box(key[0], key[1], key[2], key[3], -FENCE_DROP, GUIDE))
    if guard:
        parts.append(box(guard[0], guard[1], guard[2], guard[3], -FENCE_DROP, GUIDE))
    m = union(parts)
    m = diff(m, [cyl_z(h["p"], h["v"], -1.0, GUIDE + 1.0, h["d"]) for h in holes])
    if s < 0:
        m = m.mirror((1, 0, 0))
    # labels (readable from +w with u to the right, for L and R alike)
    title = {"pod": "옆판 %s" % side, "end": "끝벽 %s" % side}[kind]
    sub = {"pod": "이음면 (가운데 쪽)", "end": "안쪽 면 (가운데 쪽)"}[kind]
    tp = 66.0 if side == "L" else 45.0                  # title clear of the bore labels (R: wire / XT30 at p76)
    cuts = [engrave(title, 7.0, s * tp, 50.5, GUIDE), engrave(sub, 4.0, s * tp, 44.0, GUIDE)]
    cuts.append(engrave("◀앞" if s > 0 else "앞▶", 4.5, s * 8.0, 30.0, GUIDE))
    cuts.append(engrave("통로홈", 4.0, s * 12.0, 8.0, GUIDE))
    for h in holes:
        up = h["v"] + h["boss"] / 2.0 + 0.2 < v_plate - 4.5
        lv = h["v"] + h["boss"] / 2.0 + 2.6 if up else h["v"] - h["boss"] / 2.0 - 2.6
        cuts.append(engrave(h["label"], 3.6, s * h["p"], lv, GUIDE))
    m = diff(m, cuts)
    R = frame_R((0, s, 0), (0, 0, 1))                   # u = s*y, v = z, w = s*x  (toward the centre for L and R)
    origin = (x_face, Y0, ZB)
    bores = []
    for h in holes:
        u = s * h["p"]
        bores.append(dict(name=h["name"], u=u, v=h["v"], d=h["d"], bit=h["bit"], kind=h["kind"], depth=h.get("depth"),
                          world=(x_face, Y0 + h["p"], ZB + h["v"]), axis=(1.0, 0.0, 0.0)))
    placements = {"use": (R, origin)}
    # wrong placements the jig must NOT sit on (checks): the other face of a panel (datum corner = back-bottom corner),
    # and for the end-wall jig: a pod inner panel of the same side (the guard lands on the pod face)
    Rw = frame_R((0, -s, 0), (0, 0, 1))
    if kind == "pod":
        placements["wrong_face"] = (Rw, (B.SPK_IX["L"][1] if side == "L" else B.SPK_IX["R"][0], YB, ZB))
    else:
        placements["wrong_face"] = (Rw, (B.CU_X[0] if side == "L" else B.CU_X[1], YBI, ZB))
        placements["on_pod_panel"] = (R, (X_POD_FACE[side], Y0, ZB))
    no = {"pod": 1, "end": 3}[kind] + (0 if side == "L" else 1)
    fname = "J-a%d_%s_%s__1개.stl" % (no, {"pod": "스피커안쪽옆판", "end": "끝벽"}[kind], side)
    meta = dict(kind=kind, side=side, depth=depth, top_v=top_v, guard=guard, key=key, fences=fences, holes=holes)
    return Jig("J-a%d" % no, fname, "%s %s" % (title, sub), m, R_FLIP, placements, bores, meta)


def j_a5_disc():
    """D14 marking disc: pin D3.8 into the D4 pilot, trace the XT30 hole circle with a fine pencil."""
    m = union([cyl_z(0, 0, 0, DISC_T, XT30_D), cyl_z(0, 0, DISC_T, DISC_T + 5.0, 3.8)])
    # label on the bed face = the face you see in use (the pin side lies on the wood); mirrored so it reads from that side
    lab = text_xy("14", 3.5, ENGRAVE + 0.02, x=0.0, y=0.0, z=-0.02, halign="center", valign="center", heavy=True).mirror((1, 0, 0))
    m = diff(m, [lab])
    return Jig("J-a5", "J-a5_XT30_Ø14_표시원판__1개.stl", "XT30 Ø14 표시 원판", m, R_NONE, {}, [],
               dict(note="pin in the D4 pilot"))


# ============================================================================ J-b  edge magnet-seat saddles

def j_b(gap):
    L, C, D = SADDLE_L, SADDLE_C, SADDLE_D
    hw = gap / 2.0 + C
    body = box(-L / 2, L / 2, -hw, hw, 0.0, GUIDE)
    cheeks = [box(-L / 2, L / 2, gap / 2.0, hw, -D, 0.01), box(-L / 2, L / 2, -hw, -gap / 2.0, -D, 0.01)]
    m = union([body] + cheeks)
    d = bore(BIT_MAG)
    cuts = [cyl_z(0, 0, -D - 1, GUIDE + 1, d)]
    # lead-in chamfers on the inner bottom edges of the cheeks (0.8 x 45)
    for sg in (1, -1):
        y = sg * gap / 2.0
        cuts.append(prism_x([(y, -D - 0.01), (y + sg * 0.8, -D - 0.01), (y, -D + 0.8)], -L / 2 - 1, L / 2 + 1))
    # sight marks at u = 0: V groove down both cheek outer faces, 2 x 2 notch in the cheek bottoms, line across the top
    for sg in (1, -1):
        yo = sg * hw
        cuts.append(prism_z([(-0.8, yo + sg * 0.01), (0.8, yo + sg * 0.01), (0.0, yo - sg * 0.8)], -D - 1, GUIDE + 1))
        cuts.append(box(-1.0, 1.0, min(sg * gap / 2.0, yo) - 0.01, max(sg * gap / 2.0, yo) + 0.01, -D - 0.01, -D + 2.0))
        cuts.append(box(-0.4, 0.4, min(sg * (d / 2 + 1.0), yo + sg * 0.01), max(sg * (d / 2 + 1.0), yo + sg * 0.01),
                        GUIDE - ENGRAVE, GUIDE + 0.01))
    cuts.append(engrave("%.1f" % gap, 4.2, 10.0, 0.0, GUIDE, rot=90.0, heavy=True))
    cuts.append(engrave("자석", 4.2, -10.5, 0.0, GUIDE, rot=90.0))
    m = diff(m, cuts)
    pos = {}
    for k, x in enumerate(B.MAG_BACK_X["L"] + B.MAG_BACK_X["R"]):
        pos["back%d" % (k + 1)] = (frame_R((1, 0, 0), (0, 1, 0)), (x, (YBI + YB) / 2.0, B.Z_LIDU))
    for sd in "LR":
        mx_, my_ = B.MAG_END[sd]
        pos["end_%s" % sd] = (frame_R((0, 1, 0), (-1, 0, 0)), (mx_, my_, B.Z_LIDU))
    bores = [dict(name="mag", u=0.0, v=0.0, d=d, bit=BIT_MAG, kind="blind", depth=DEPTH_MAG, axis=(0, 0, 1.0))]
    fname = "J-b_모서리자석새들_틈%.1f__1개.stl" % gap
    return Jig("J-b%.1f" % gap, fname, "모서리 자석 새들 (틈 %.1f)" % gap, m, R_FLIP, pos, bores, dict(gap=gap))


# ============================================================================ J-c  lid underside magnet templates

def j_c(side):
    """board coords (p, q): p from the datum end (L: left end x260, R: right end x962) along the back edge, q from the back edge
    toward the front; local u = p, v = q (L) / -q (R); w = out of the underside (world -z)."""
    a, b = B.LIDS["LID-%s" % side]
    yc = (YBI + YB) / 2.0
    mags = [(x, yc) for x in B.MAG_BACK_X[side]] + [B.MAG_END[side]]
    if side == "L":
        pq = [(x - a, YB - y) for (x, y) in mags]
    else:
        pq = [(b - x, YB - y) for (x, y) in mags]
    d = bore(BIT_MAG)
    boss = d + 2 * WALL
    # slot key: a SLOT_KEY_W-wide tongue that drops into one exhaust slot (drilled first with J-d) -> the template sits on the underside at
    # the right corner only (a plain 241 x 128.5 board would take it at any corner / face).  Slot = the J-d slot nearest the back
    # (lid L: x459..489 y324..328) / nearest the datum end (lid R: x744..748 y288..328); 0.5 clear of the slot walls (cusps 0.27)
    if side == "L":
        x0_, x1_, y0_ = B.LIDL_SLOTS[-1]
        sp0, sp1, sq0, sq1 = x0_ - a, x1_ - a, YB - (y0_ + 4.0), YB - y0_
        key = (sp0 + 5.0, sp1 - 5.0, (sq0 + sq1) / 2.0 - SLOT_KEY_W / 2.0, (sq0 + sq1) / 2.0 + SLOT_KEY_W / 2.0)
    else:
        x0_, y0_, y1_ = B.LIDR_SLOTS[0]
        sp0, sp1, sq0, sq1 = b - (x0_ + 4.0), b - x0_, YB - y1_, YB - y0_
        key = ((sp0 + sp1) / 2.0 - SLOT_KEY_W / 2.0, (sp0 + sp1) / 2.0 + SLOT_KEY_W / 2.0, sq0 + 5.5, sq0 + 19.5)
    p_far = max(max(p for p, _ in pq) + boss / 2.0 + 1.0, key[1] + 4.0)
    q_far = max(q for _, q in pq) + boss / 2.0 + 1.0
    e = -FENCE_T + 1.0                                  # plate edge 1 inside the fence outer faces (no coplanar T-junction slivers)
    plate = [rect(e, p_far, e, 14.0), rect(e, 14.0, e, q_far),
             [(14.0, 14.0), (64.0, 14.0), (14.0, 64.0)],
             rect(key[0] - 4.0, key[1] + 4.0, 10.0, key[3] + 4.0)]
    pads = [(32.0, 32.0), (p_far - 6.0, 9.0)] if side == "R" else [(32.0, 32.0), (190.0, 7.0)]
    if side == "R":
        pads.append((128.0, 9.0))
    fences = [(3.0, p_far, -FENCE_T, 0.0), (-FENCE_T, 0.0, 3.0, q_far)]
    pl = union([prism_z(p, GUIDE - PLATE_T, GUIDE) for p in plate])
    top_in = GUIDE - 1.0                                # bosses / pads end inside the plate (no coplanar top-face slivers)
    parts = [pl] + [cyl_z(p, q, 0.0, top_in, boss) for (p, q) in pq] + [cyl_z(p, q, 0.0, top_in, PAD_D) for (p, q) in pads]
    parts += [box(f[0], f[1], f[2], f[3], -FENCE_DROP, GUIDE) for f in fences]
    parts.append(box(key[0], key[1], key[2], key[3], -FENCE_DROP, GUIDE))
    m = union(parts)
    m = diff(m, [cyl_z(p, q, -1.0, GUIDE + 1.0, d) for (p, q) in pq])
    sv = 1.0 if side == "L" else -1.0
    if sv < 0:
        m = m.mirror((0, 1, 0))
    # labels: readable from +w (looking at the underside), u to the right
    cuts = []
    rail_mid = (pq[0][0] + pq[1][0]) / 2.0 if side == "L" else 128.0 + 42.0
    cuts.append(engrave("뚜껑 %s 밑면" % side, 6.0, rail_mid, sv * 6.5, GUIDE))
    if side == "R":
        cuts.append(engrave("뒤 모서리에 댐", 4.5, 70.0, sv * 6.5, GUIDE))
    end_txt = "왼쪽 끝" if side == "L" else "오른쪽 끝"
    cuts.append(engrave(end_txt, 4.5, 5.0, sv * 40.0, GUIDE, rot=90.0 if sv > 0 else -90.0))
    cuts.append(engrave("자석 8↓3.2", 4.0, 30.0, sv * 22.0, GUIDE))
    cuts.append(engrave("홈", 4.0, (key[0] + key[1]) / 2.0, sv * (key[2] + key[3]) / 2.0, GUIDE,
                        rot=0.0 if side == "L" else 90.0))
    if side == "L":
        cuts.append(engrave("뒤 모서리에 댐", 4.5, 165.0, sv * 6.5, GUIDE))
    m = diff(m, cuts)
    if side == "L":
        R = frame_R((1, 0, 0), (0, -1, 0))
        origin = (a, YB, B.Z_LIDU)
    else:
        R = frame_R((-1, 0, 0), (0, 1, 0))
        origin = (b, YB, B.Z_LIDU)
    bores = [dict(name="mag%d" % (k + 1), u=p, v=sv * q, d=d, bit=BIT_MAG, kind="blind", depth=DEPTH_MAG,
                  world=(mags[k][0], mags[k][1], B.Z_LIDU), axis=(0, 0, 1.0)) for k, (p, q) in enumerate(pq)]
    no = 1 if side == "L" else 2
    return Jig("J-c%d" % no, "J-c%d_뚜껑%s_밑면자석__1개.stl" % (no, side), "뚜껑 %s 밑면 자석" % side, m, R_FLIP,
               {"use": (R, origin)}, bores, dict(pq=pq, fences=fences, key=key, side=side))


# ============================================================================ J-d  slot templates (frame + slider + shim)

def slot_groups():
    """each group: local frame (u, v, w = drilled face normal), t-axis (along the slots) and c-axis, slots in (t, c)."""
    g = []
    # lid L - from the top face; datums: right end (seam to the screen lid, x501) + back edge
    a, b = B.LIDS["LID-L"]
    sl = [(b - (x1 - SLOT_END), b - (x0 + SLOT_END), YB - (y0 + 2.0), (b - x1, b - x0)) for (x0, x1, y0) in B.LIDL_SLOTS]
    g.append(dict(key="J-d1", name="뚜껑L", title="뚜껑 L 배기 홈", board="LID-L", face="윗면",
                  R=frame_R((-1, 0, 0), (0, -1, 0)), origin=(b, YB, B.Z_LID), t_axis=("u", 1), c_fence=True,
                  slots=[dict(t0=t0, t1=t1, c=c, slot_t=st, groupname="뚜껑L") for (t0, t1, c, st) in sl],
                  datum_t="오른쪽 끝 (화면 뚜껑 쪽, x501)", datum_c="뒤 모서리"))
    # lid R - top face; datums: left end (x721) + back edge
    a, b = B.LIDS["LID-R"]
    sl = [(YB - (y1 - SLOT_END), YB - (y0 + SLOT_END), x0 + 2.0 - a, (YB - y1, YB - y0)) for (x0, y0, y1) in B.LIDR_SLOTS]
    g.append(dict(key="J-d2", name="뚜껑R", title="뚜껑 R 배기 홈", board="LID-R", face="윗면",
                  R=frame_R((1, 0, 0), (0, 1, 0)), origin=(a, YB, B.Z_LID), t_axis=("v", -1), c_fence=True,
                  slots=[dict(t0=t0, t1=t1, c=c, slot_t=st) for (t0, t1, c, st) in sl],
                  datum_t="뒤 모서리", datum_c="왼쪽 끝 (화면 뚜껑 쪽, x721)"))
    # back ply - outer face; datums: right end (x962, the end FAR from the back-plate window) + top edge
    sl = [(B.Z_LIDU - (z1 - SLOT_END), B.Z_LIDU - (z0 + SLOT_END), B.CU_X[1] - (x0 + 2.0), (B.Z_LIDU - z1, B.Z_LIDU - z0))
          for (x0, z0, z1) in B.BACK_SLOTS]
    g.append(dict(key="J-d3", name="뒤판", title="가운데 뒤판 환기 홈", board="CU-PLY-BACK", face="바깥면 (뒤에서 보이는 면)",
                  R=frame_R((-1, 0, 0), (0, 0, 1)), origin=(B.CU_X[1], YB, B.Z_LIDU), t_axis=("v", -1), c_fence=True,
                  slots=[dict(t0=t0, t1=t1, c=c, slot_t=st) for (t0, t1, c, st) in sl],
                  datum_t="윗모서리", datum_c="창에서 먼 쪽 끝 (오른쪽 끝, x962)"))
    # bottom ply - top face; datums: back edge + pencil line SIGHT_U from the left end (x271.5)
    x_left = B.CU_IX[0]
    sl = [(YBI - (y1 - SLOT_END), YBI - (y0 + SLOT_END), x0 + 2.0 - x_left, (YBI - y1, YBI - y0))
          for (x0, y0, y1) in B.BOT_SLOTS_BUCK + B.BOT_SLOTS_PI]
    g.append(dict(key="J-d4", name="아랫판", title="가운데 아랫판 흡기 홈", board="CU-PLY-BOTTOM", face="윗면",
                  R=frame_R((1, 0, 0), (0, 1, 0)), origin=(x_left, YBI, B.Z_BOT), t_axis=("v", -1), c_fence=False,
                  slots=[dict(t0=t0, t1=t1, c=c, slot_t=st) for (t0, t1, c, st) in sl],
                  datum_t="뒤 모서리", datum_c="왼쪽 끝에서 %.0f mm 연필선" % SIGHT_U))
    for gr in g:
        S = [round(s_["t1"] - s_["t0"], 6) for s_ in gr["slots"]]
        assert max(S) - min(S) < 1e-6, (gr["key"], S)
        S = S[0]
        K = int(math.ceil((S / SLOT_PMAX + 1.0) / 4.0))
        gr["S"], gr["K"], gr["p"] = S, K, S / (4 * K - 1)
        gr["n_holes"] = 4 * K
    return g


def tc_box(gr, t0, t1, c0, c1, w0, w1):
    ax, sg = gr["t_axis"]
    if ax == "u":
        return box(sg * t0, sg * t1, c0, c1, w0, w1)
    return box(c0, c1, sg * t0, sg * t1, w0, w1)


def tc_pt(gr, t, c):
    ax, sg = gr["t_axis"]
    return (sg * t, c) if ax == "u" else (c, sg * t)


def j_d(gr):
    p, K = gr["p"], gr["K"]
    d = bore(BIT_SLOT)
    rows = gr["slots"]
    bores_tc = [(r["t0"] + 4 * p * k, r["c"]) for r in rows for k in range(K)]
    ts = [t for t, _ in bores_tc]
    cs = [c for _, c in bores_tc]
    s_t0, s_t1 = min(ts) - d / 2 - SLIDER_M, max(ts) + d / 2 + SLIDER_M
    s_c0, s_c1 = min(cs) - d / 2 - SLIDER_MC, max(cs) + d / 2 + SLIDER_MC
    tab = 9.0                                                       # label tab on the slider (c-max side, plate only)
    travel = 3 * p + TRAVEL_EXTRA
    w_t0, w_t1 = s_t0, s_t1 + travel
    w_c0, w_c1 = s_c0 - SLIDE_CLR, s_c1 + tab + SLIDE_CLR
    # ---------------- slider (local: wood face w=0, its near end at t = s_t0 when pushed to the A/C wall)
    blocks = []
    if gr["key"] == "J-d4":                                         # two blocks (BUCK / PI rows), plate between
        for grp in (rows[:len(B.BOT_SLOTS_BUCK)], rows[len(B.BOT_SLOTS_BUCK):]):
            gt = [r["t0"] + 4 * p * k for r in grp for k in range(K)]
            gc = [r["c"] for r in grp]
            blocks.append(tc_box(gr, min(gt) - d / 2 - SLIDER_M, max(gt) + d / 2 + SLIDER_M,
                                 max(s_c0, min(gc) - d / 2 - SLIDER_MC), max(gc) + d / 2 + SLIDER_MC, 0.0, GUIDE))
        blocks.append(tc_box(gr, s_t0, s_t1, s_c0, s_c1, 0.0, PLATE_T))
    else:
        blocks.append(tc_box(gr, s_t0, s_t1, s_c0, s_c1, 0.0, GUIDE))
    blocks.append(tc_box(gr, s_t0, s_t1, s_c1 - 0.01, s_c1 + tab, 0.0, PLATE_T))
    sld = union(blocks)
    pin_len = travel + KEY_PIN[0]                                   # longer than the travel: a slider turned 180 deg hits it anywhere
    notch_t1 = s_t0 + pin_len + travel + 0.5
    cuts = [tc_box(gr, s_t0 - 0.01, notch_t1, s_c0 - 0.01, s_c0 + KEY_PIN[1] + 0.3, -0.01, GUIDE + 0.01)]
    cuts += [cyl_z(*tc_pt(gr, t, c), -1.0, GUIDE + 1.0, d) for (t, c) in bores_tc]
    # elephant-foot relief: 0.4 x 0.4 step round the bottom perimeter (the slider prints wood-face down and must slide freely)
    EF = 0.4
    cuts.append(diff(tc_box(gr, s_t0 - 1, s_t1 + 1, s_c0 - 1, s_c1 + tab + 1, -0.01, EF),
                     [tc_box(gr, s_t0 + EF, s_t1 - EF, s_c0 + EF, s_c1 + tab - EF, -0.02, EF + 0.01)]))
    sld = diff(sld, cuts)
    lab_c = s_c1 + tab / 2.0
    lab_t = (s_t0 + s_t1) / 2.0
    lu, lv = tc_pt(gr, lab_t, lab_c)
    rot = 0.0 if gr["t_axis"][0] == "u" else 90.0
    sld = union([sld, raised(gr["name"], 4.5, lu, lv, PLATE_T, rot=rot)])
    # ---------------- frame (lies on the wood, fences on the datum edges, window + pin)
    f_t0 = -FENCE_T
    f_t1 = w_t1 + FRAME_B
    if gr["c_fence"]:
        f_c0 = -FENCE_T
    else:
        f_c0 = SIGHT_U
    f_c1 = w_c1 + FRAME_B
    fr = tc_box(gr, f_t0, f_t1, f_c0, f_c1, 0.0, FRAME_T)
    fr = union([fr, tc_box(gr, -FENCE_T, 0.0, f_c0 + 3.0 if gr["c_fence"] else f_c0, f_c1, -FENCE_DROP, FRAME_T)])
    if gr["c_fence"]:
        fr = union([fr, tc_box(gr, 3.0, f_t1, -FENCE_T, 0.0, -FENCE_DROP, FRAME_T)])
    fcuts = [tc_box(gr, w_t0, w_t1, w_c0, w_c1, -1.0, FRAME_T + 1.0)]
    if gr["key"] == "J-d3":                                         # lighten the long bar to the end fence
        fcuts.append(tc_box(gr, 6.0, w_t1 - 2.0, 12.0, w_c0 - 8.0, -1.0, FRAME_T + 1.0))
    CH = 0.5
    fcuts.append(Manifold.batch_hull([tc_box(gr, w_t0, w_t1, w_c0, w_c1, FRAME_T - CH, FRAME_T - CH + 0.01),
                                      tc_box(gr, w_t0 - CH - 0.3, w_t1 + CH + 0.3, w_c0 - CH - 0.3, w_c1 + CH + 0.3,
                                             FRAME_T + 0.3, FRAME_T + 0.31)]))
    fr = diff(fr, fcuts)
    fr = union([fr, tc_box(gr, w_t0 - 0.01, w_t0 + pin_len, w_c0 - 0.01, w_c0 + KEY_PIN[1], 0.0, FRAME_T - CH)])
    # frame labels (engraved on the use-top w = FRAME_T; bed side in print)
    tl = []
    big = "%s %s" % (gr["title"] if gr["key"] == "J-d3" else gr["name"], gr["face"].split(" ")[0])
    name_rot = 90.0 if gr["t_axis"][0] == "u" else 0.0
    tl.append(engrave(big, 5.0, *tc_pt(gr, f_t1 - FRAME_B / 2.0 - 0.5, (w_c0 + w_c1) / 2.0 if gr["key"] != "J-d3" else 80.0),
                      FRAME_T, rot=name_rot))
    ac_c = w_c0 - 4.5 if (w_c0 - f_c0) > 9.0 else w_c1 + 4.0
    for txt, tt in (("A·C", w_t0 + 3.0), ("B·D", w_t1 - 3.0)):
        tl.append(engrave(txt, 3.6, *tc_pt(gr, tt, ac_c), FRAME_T, rot=rot, heavy=True))
    if not gr["c_fence"]:
        tl.append(engrave("▼%.0f" % SIGHT_U, 4.0, *tc_pt(gr, f_t1 - 3.5, f_c0 + 6.0), FRAME_T))
        tl.append(engrave("▼%.0f" % SIGHT_U, 4.0, *tc_pt(gr, 1.0, f_c0 + 6.0), FRAME_T))
    fr = diff(fr, tl)
    # ---------------- shim p (blade in the gap at either window end; handle rests on the frame border)
    sh = union([box(0.0, p, -SHIM_W / 2, SHIM_W / 2, 0.0, FRAME_T), box(-SHIM_HANDLE, p, -SHIM_W / 2, SHIM_W / 2, FRAME_T, FRAME_T + 3.0)])
    short = {"J-d1": "뚜L", "J-d2": "뚜R", "J-d3": "뒤", "J-d4": "아래"}[gr["key"]]
    sh = diff(sh, [engrave("%s %.2f" % (short, p), 3.2, (p - SHIM_HANDLE) / 2.0, 0.0, FRAME_T + 3.0, rot=90.0)])
    # ---------------- placements (frame on the board; slider at the 4 pass offsets; local frame = board frame)
    R, o = gr["R"], np.array(gr["origin"], float)
    ax, sg = gr["t_axis"]
    tdir = (R[:, 0] if ax == "u" else R[:, 1]) * sg
    offs = {"A": 0.0, "B": travel - p, "C": p, "D": travel}
    pl_frame = {"use": (R, o)}
    pl_slider = {k: (R, o + tdir * v) for k, v in offs.items()}
    bores = [dict(name="r%dk%d" % (i // K + 1, i % K), u=tc_pt(gr, t, c)[0], v=tc_pt(gr, t, c)[1], d=d, bit=BIT_SLOT,
                  kind="through", t=t, c=c) for i, (t, c) in enumerate(bores_tc)]
    meta = dict(group=gr, slider_t=(s_t0, s_t1), slider_c=(s_c0, s_c1 + tab), window_t=(w_t0, w_t1), window_c=(w_c0, w_c1),
                travel=travel, p=p, K=K, offsets=offs, tdir=tdir, pin_len=pin_len)
    k = gr["key"]
    jf = Jig(k + "a", "%sa_%s_홈틀__1개.stl" % (k, gr["name"]), "%s 틀" % gr["title"], fr, R_FLIP, pl_frame, [], meta)
    js = Jig(k + "b", "%sb_%s_홈슬라이더__1개.stl" % (k, gr["name"]), "%s 슬라이더" % gr["title"], sld, R_NONE, pl_slider, bores, meta)
    jsh = Jig(k + "c", "%sc_%s_홈심_%.2f__1개.stl" % (k, gr["name"], p), "%s 심 %.2f" % (gr["title"], p), sh, R_FLIP, {}, [],
              dict(p=p, group=gr))
    return [jf, js, jsh]


# ============================================================================ J-e  depth gauges + test guides

def cone_depth(dbit):
    return (dbit / 2.0) / math.tan(math.radians(POINT_DEG / 2.0))


GAUGES = [("인서트5.8", "인5.8", BIT_INSERT, DEPTH_INSERT), ("인서트5.8얇은판", "얇5.8", BIT_INSERT, DEPTH_INSERT_THIN),
          ("인서트5.5", "인5.5", BIT_INSERT_ALT, DEPTH_INSERT), ("자석8", "자8", BIT_MAG, DEPTH_MAG)]
TESTS = [("5.8", BIT_INSERT), ("5.5", BIT_INSERT_ALT), ("6", BIT_WIRE), ("8", BIT_MAG), ("4", BIT_PILOT)]
GAUGE_H = 26.0


def j_e():
    W = 24.0
    xs_g = [9.0, 25.0, 41.0, 58.0]
    gx1 = 68.0
    xs_t = [gx1 + 9.0 + 12.0 * i for i in range(len(TESTS))]
    tx1 = xs_t[-1] + 9.0
    m = union([box(0, gx1, 0, W, 0, GAUGE_H), box(gx1 - 0.01, tx1, 0, W, 0, GUIDE)])
    cuts = []
    gauges = []
    for (name, label, bit, dep), x in zip(GAUGES, xs_g):
        d = bore(bit)
        zc = GAUGE_H - (GUIDE + dep)                       # cylinder bottom = full-diameter depth below the guide
        ch = (d / 2.0) / math.tan(math.radians(POINT_DEG / 2.0))
        cuts.append(cyl_z(x, 15.0, zc, GAUGE_H + 1, d))
        cuts.append(cone_z(x, 15.0, zc - ch, zc + 0.001, 0.0, d))
        gauges.append(dict(name=name, x=x, y=15.0, d=d, bit=bit, depth=dep, z_cyl_bottom=zc, cone=ch,
                           stickout=GUIDE + dep))
        cuts.append(engrave(label, 3.4, x, 5.0, GAUGE_H))
    for (name, bit), x in zip(TESTS, xs_t):
        cuts.append(cyl_z(x, 15.0, -1.0, GUIDE + 1, bore(bit)))
        cuts.append(engrave(name, 3.8, x, 5.0, GUIDE, heavy=True))
    cuts.append(engrave("깊이", 4.0, 26.0, 21.5, GAUGE_H))
    m = diff(m, cuts)
    tests = [dict(name=n, x=x, y=15.0, d=bore(b), bit=b) for (n, b), x in zip(TESTS, xs_t)]
    return Jig("J-e", "J-e_깊이게이지·시험블록__1개.stl", "깊이 게이지 + 시험 구멍 블록", m, R_NONE, {}, [],
               dict(gauges=gauges, tests=tests, gauge_h=GAUGE_H))


# ============================================================================ J-f  sanding stick (optional)

STICK_T = 2.0                  # blade: 2.0 + one sheet of #120 paper on double-sided tape (~0.5) < 3.17 narrowest J-d slot


def j_f():
    """flat stick for cleaning the 4 mm slots: handle 60 x 20 x 8, blade 120 x 10 x 2.0 (paper on one face, flip for the other wall)."""
    m = union([box(0, 60.0, 0, 20.0, 0, 8.0), box(59.99, 180.0, 5.0, 15.0, 0, STICK_T)])
    m = diff(m, [engrave("사포 한쪽", 4.0, 30.0, 10.0, 8.0, heavy=True)])
    return Jig("J-f", "J-f_홈다듬기_사포막대__1개.stl", "4 mm 홈 사포 막대 (선택)", m, R_NONE, {}, [], dict(blade_t=STICK_T))


# ============================================================================ build

OPTIONAL = {"J-f"}             # everything else is needed for the hand-drilling plan (README: cad/jigs/README.md)


def make_jigs():
    jigs = []
    for kind in ("pod", "end"):
        for side in "LR":
            jigs.append(j_a(kind, side))
    jigs.append(j_a5_disc())
    jigs += [j_b(g) for g in SADDLE_GAPS]
    jigs += [j_c("L"), j_c("R")]
    for gr in slot_groups():
        jigs += j_d(gr)
    jigs.append(j_e())
    jigs.append(j_f())
    return jigs


def _note(j):
    k = j.key
    if k.startswith("J-a5"):
        t = "XT30 Ø14 원 그리기: 핀을 끝벽 Ø4 안내 구멍에 꽂고 연필로 원"
    elif k.startswith("J-a"):
        t = "%s: 앞·아래 울타리를 따낸 구석 두 모서리에 대고 뚫음" % j.title
    elif k.startswith("J-b"):
        t = "%s: 4개 중 꼭 맞는 하나만 씀 (11.3이 끼면 얇은 판 → J-e '얇5.8')" % j.title
    elif k.startswith("J-c"):
        t = "%s: J-d로 배기 홈을 먼저 뚫고, 혀를 홈에 넣어 댐" % j.title
    elif k.startswith("J-d"):
        t = "%s: 틀 + 슬라이더 + 심 한 벌, A·B·C·D 4번 뚫기" % j.title
    elif k == "J-e":
        t = "깊이 게이지(척을 멈춤으로 쓰는 날 길이 맞추기) + 자투리 시험 구멍 — 가장 먼저 뽑음"
    else:
        t = j.title
    return t + ". PETG 0.2 mm, 서포트 없음, STL 방향 그대로 (cad/jigs/README.md)"


def build():
    """for build_all.py: [{name, solid (Manifold in print orientation), qty, required, note}] - name without __N개."""
    out = []
    for j in make_jigs():
        assert j.file.endswith("__1개.stl"), j.file
        out.append(dict(name=j.file[:-len("__1개.stl")], solid=j.printed, qty=1, required=j.key not in OPTIONAL,
                        note=_note(j), key=j.key))
    return out


def write_files(root, jigs=None):
    """write every jig like build_all does: root/08_합판지그 (required), root/선택_합판지그 (optional). -> {key: path}"""
    jigs = jigs if jigs is not None else make_jigs()
    paths = {}
    for j in jigs:
        sub = EXTRA_SUB if j.key in OPTIONAL else PRINT_SUB
        path = os.path.join(root, sub, j.file)
        b = j.printed.bounding_box()
        write_stl(j.printed, path, "Toccata %s %.1fx%.1fx%.1f" % (j.key, b[3], b[4], b[5]))
        paths[j.key] = path
    return paths


def est_print(m):
    """rough P2S PETG estimate: 3 walls (1.26), 5 top/bottom layers (1.0), 15 % infill; ~9 mm3/s + 2.5 s per layer."""
    V = m.volume()
    A = m.surface_area()
    shell = min(V, A * 1.1)
    printed = shell + 0.15 * (V - shell)
    g = printed / 1000.0 * 1.27
    h = m.bounding_box()[5]
    minutes = printed / 9.0 / 60.0 + h / 0.2 * 2.5 / 60.0 + 3.0
    return g, minutes


if __name__ == "__main__":
    js = make_jigs()
    if "--write" in sys.argv:
        root = sys.argv[sys.argv.index("--write") + 1]
        for k, pth in write_files(root, js).items():
            print("wrote", pth)
    tot_g = tot_m = 0.0
    for j in js:
        b = j.printed.bounding_box()
        g, mi = est_print(j.printed)
        tot_g += g
        tot_m += mi
        print("%-7s %-3s %-46s %6.1f x %6.1f x %5.1f  bodies %d  ~%5.1f g  ~%4.0f min" % (
            j.key, "opt" if j.key in OPTIONAL else "req", j.file, b[3], b[4], b[5], len(j.printed.decompose()), g, mi))
    print("total ~%.0f g, ~%.1f h" % (tot_g, tot_m / 60.0))
    for gr in slot_groups():
        print(gr["key"], gr["name"], "S=%.2f K=%d p=%.4f holes/slot=%d slots=%d" % (gr["S"], gr["K"], gr["p"], gr["n_holes"], len(gr["slots"])))
