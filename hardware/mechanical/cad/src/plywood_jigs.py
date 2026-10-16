#!/usr/bin/env python3
"""Toccata L2 - 3D-printed drilling jigs for the okoume plywood pieces (new 2026-10-02; how to use: cad/jigs/README.md).

2026-10-07 (user: '드릴을 써야되는 부분을 최소한으로 줄여줘'): the lids, the centre end walls and the two pod inner side panels are printed now
(holes, slots, magnet seats and the M4 insert holes come out of the printer), and the vents left in the plywood are D8 hole grids. So the
jigs for the pod inner panels / end walls (J-a1..a5), the lid magnets (J-c1/c2), the lid slots (J-d1/d2) and the 4 mm slot sanding stick
(J-f) are gone; J-d3 / J-d4 are plain D8 hole templates (no slider / shim); J-b only serves the 4 back-ply top-edge magnet seats; J-e keeps
the magnet depth gauge and the D8 / D4 test guides.

    build()                                # -> [{name, solid, qty, required, note}] for build_all.py, which writes
                                           #    required -> stl/print/08_합판지그/ (optional ones -> stl/print_extra/선택_합판지그/: none now)
    python3 src/plywood_jigs.py            # table only (size, rough grams / minutes); writes nothing
    python3 src/plywood_jigs.py --write D  # write the STLs to D/08_합판지그 (same names as build_all)
    python3 src/check_plywood_jigs.py      # writes to a temp dir, then watertight / bed size / bores measured back from the
                                           # STLs vs the body.py model

Every hole position is read from body.py (the CAD model that is built), never typed again here:
  MAG_BACK_X (back-ply top-edge magnet seats), BACK_HOLES / BOT_HOLES_BUCK / BOT_HOLES_PI (D8 vent grids), VENT_D, panel extents
  (Y0, YB, YBI, ZB, Z_LIDU, Z_BOT, CU_X, CU_IX).

Jigs (all PETG, 0.2 mm layers, no supports):
  J-b      edge magnet-seat saddles, gaps 11.3 / 11.6 / 11.9 / 12.2 (take the tightest that slides on) - D8 guide centred in the
           11.5 edge, sight grooves for a pencil line (back ply top edge 30 / 120 / 473 / 675)
  J-d3     back ply D8 amp-vent template: fences on the right end (x962, far from the back-plate window) and the top edge, outer face
  J-d4     bottom ply D8 intake template: fence on the back edge, plate edge on a pencil line 200 from the left end, top face
  J-e      depth gauge (magnet 8 -> 3.2, set the bit stick-out from the chuck = chuck stop on the guide top, cone 118 deg)
           + test guides (through, D8 and D4) for trying the bits / magnet fit on an offcut first

Frames: each jig is built in its USE frame (u, v, w): w = 0 is the drilled wood face, +w out of it (toward the drill),
u x v = w; the placements map the use frame to the world (body.py coordinates) for the checks; the print frame puts the jig on
the bed without supports.  Guide length from the wood face to the guide top = GUIDE (14) for the blind magnet seats (one depth
gauge), GUIDE_THRU (10) for the through vent holes.  Printed holes come out small: bore = bit + BORE_CLR, ream once with the same bit.
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
BIT_MAG = B.MAG[0]             # 8.0  magnet seat
BIT_VENT = B.VENT_D            # 8.0  vent holes (back ply, bottom ply)
BIT_PILOT = 4.0                # 4.0  owned HSS SD 4.0: a 1~2 mm start for the D8 bit (less wander), test guide
DEPTH_MAG = B.MAG[2]           # 3.2  full-diameter depth of the magnet seat
POINT_DEG = 118.0              # HSS twist drill point angle (the gauge's cone)
BORE_CLR = 0.2                 # guide bore = bit + 0.2 (prints ~0.1-0.2 small; ream once with the same bit)
GUIDE = 14.0                   # guide length for the blind magnet seats: wood face -> guide top (the J-e gauge is set for it)
GUIDE_THRU = 10.0              # guide length of the through-hole templates J-d3 / J-d4
PLATE_T = 4.0                  # top plate of the templates
WALL = 3.0                     # guide boss wall
FENCE_T = 4.0                  # fence thickness
FENCE_DROP = 7.0               # fence length below the wood face (< 11.5)
PAD_D = 10.0                   # extra contact pads
ENGRAVE = 0.8                  # engraved labels (use-top face = bed face in print)
SIGHT_U = 200.0                # bottom ply: pencil line 200 mm from the LEFT end (x471.5) - the J-d4 plate edge sits on it
SADDLE_L, SADDLE_C, SADDLE_D = 30.0, 4.5, 10.0

R_FLIP = rot_x(180.0)          # use-top face down on the bed
R_NONE = np.eye(3)


def bore(bit):
    return round(bit + BORE_CLR, 3)


def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def engrave(s, size, u, v, top, rot=0.0, heavy=False, halign="center", valign="center"):
    return text_xy(s, size, ENGRAVE + 0.02, x=u, y=v, z=top - ENGRAVE, halign=halign, valign=valign, rot=rot, heavy=heavy)


def frame_R(u, v):
    """3x3 matrix with columns = world directions of local u, v, w (w = u x v)."""
    u, v = np.array(u, float), np.array(v, float)
    return np.column_stack([u, v, np.cross(u, v)])


class Jig:
    def __init__(self, key, file, title, local, R_print=R_NONE, placements=None, bores=None, meta=None):
        self.key, self.file, self.title, self.local = key, file, title, local
        self.R_print = np.array(R_print, float)
        self.placements = placements or {}      # name -> (R 3x3, origin 3) local -> world
        self.bores = bores or []                # dicts: name, u, v, d (bore), bit, kind, world (world point on the face), axis
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


Y0, YB, YBI, ZB = B.Y0, B.YB, B.YBI, B.ZB


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
    bores = [dict(name="mag", u=0.0, v=0.0, d=d, bit=BIT_MAG, kind="blind", depth=DEPTH_MAG, axis=(0, 0, 1.0))]
    fname = "J-b_모서리자석새들_틈%.1f__1개.stl" % gap
    return Jig("J-b%.1f" % gap, fname, "모서리 자석 새들 (틈 %.1f)" % gap, m, R_FLIP, pos, bores, dict(gap=gap))


# ============================================================================ J-d3 / J-d4  D8 vent-hole templates

def vent_template(key, name, title, board, face, R, origin, holes_uv, fences, sight=None, pads=(), labels=()):
    """plate (GUIDE_THRU - PLATE_T .. GUIDE_THRU) over the holes + bosses D(8.2 + 2 WALL) down to the wood face + pads + fences that drop
    FENCE_DROP past the face onto the datum edges. holes_uv: [(name, u, v, world point on the face)]. sight: (u, (v0, v1)) - a plate
    edge to put on a pencil line (no fence there)."""
    d = bore(BIT_VENT)
    boss = d + 2 * WALL
    us = [u for _, u, _, _ in holes_uv]
    vs = [v for _, _, v, _ in holes_uv]
    e = 1.0                                                     # plate edge 1 inside the fence outer faces (no coplanar slivers)
    u0 = min(min(us) - boss / 2 - 3.0, min([f[0] + e for f in fences if f[1] - f[0] <= FENCE_T + 1e-6] or [1e9]))
    if sight is not None:
        u0 = sight[0]
    u1 = max(us) + boss / 2 + 3.0
    v0 = min(vs) - boss / 2 - 3.0
    v1 = max(max(vs) + boss / 2 + 3.0, max([f[3] - e for f in fences if f[3] - f[2] <= FENCE_T + 1e-6] or [-1e9]))
    top = GUIDE_THRU
    parts = [box(u0, u1, v0, v1, top - PLATE_T, top)]
    top_in = top - 1.0
    parts += [cyl_z(u, v, 0.0, top_in, boss) for _, u, v, _ in holes_uv]
    parts += [cyl_z(u, v, 0.0, top_in, PAD_D) for (u, v) in pads]
    parts += [box(f[0], f[1], f[2], f[3], -FENCE_DROP, top) for f in fences]
    m = union(parts)
    cuts = [cyl_z(u, v, -1.0, top + 1.0, d) for _, u, v, _ in holes_uv]
    cuts += [engrave(t, sz, u, v, top, rot=r_) for (t, sz, u, v, r_) in labels]
    m = diff(m, cuts)
    bores = [dict(name=n, u=u, v=v, d=d, bit=BIT_VENT, kind="through", world=tuple(float(c) for c in w), axis=tuple(float(c) for c in np.asarray(R)[:, 2]))
             for (n, u, v, w) in holes_uv]
    meta = dict(board=board, face=face, fences=fences, sight=sight, plate=(u0, u1, v0, v1), holes=holes_uv, n=len(holes_uv))
    return Jig(key, "%s_%s_Ø8구멍판__1개.stl" % (key, name), title, m, R_FLIP, {"use": (R, origin)}, bores, meta)


def j_d3():
    """back ply, outer face (y = YB, w = +y): u = 962 - x (from the right end, the end FAR from the back-plate window), v = z - 61.35 (up from
    the top edge; the board is at v < 0)."""
    R = frame_R((-1, 0, 0), (0, 0, 1))
    origin = (B.CU_X[1], YB, B.Z_LIDU)
    holes = [("h%d" % (k + 1), B.CU_X[1] - x, z - B.Z_LIDU, (x, YB, z)) for k, (x, z) in enumerate(B.BACK_HOLES)]
    us = [u for _, u, _, _ in holes]
    vmin = min(v for _, _, v, _ in holes) - (bore(BIT_VENT) / 2 + WALL) - 3.0
    u_far = max(us) + bore(BIT_VENT) / 2 + WALL + 3.0
    fences = [(-FENCE_T, 0.0, vmin, FENCE_T - 1.0),                 # end fence on the right end x962 (to the plate's lower edge)
              (3.0, u_far, 0.0, FENCE_T)]                           # top-edge fence over the top edge z61.35
    pads = [(8.0, -8.0), (60.0, -8.0)]
    vm = min(v for _, _, v, _ in holes)
    labels = [("뒤판 바깥면 Ø8", 5.0, 60.0, vm - 1.0, 0.0), ("오른쪽 끝 ▶", 4.0, 30.0, vm + 6.0, 0.0)]
    return vent_template("J-d3", "뒤판_앰프환기", "가운데 뒤판 앰프 환기 Ø8 구멍판", "CU-PLY-BACK", "바깥면 (뒤에서 보이는 면)", R, origin, holes,
                         fences, pads=pads, labels=labels)


def j_d4():
    """bottom ply, top face (z = Z_BOT, w = +z): u = x - 271.5 (from the left end), v = y - 331 (the board is at v < 0); back-edge fence,
    plate edge u = SIGHT_U on a pencil line 200 from the left end."""
    R = frame_R((1, 0, 0), (0, 1, 0))
    x_left = B.CU_IX[0]
    origin = (x_left, YBI, B.Z_BOT)
    hs = B.BOT_HOLES_BUCK + B.BOT_HOLES_PI
    holes = [("%s%d" % ("b" if k < len(B.BOT_HOLES_BUCK) else "p", k + 1), x - x_left, y - YBI, (x, y, B.Z_BOT)) for k, (x, y) in enumerate(hs)]
    u_far = max(u for _, u, _, _ in holes) + bore(BIT_VENT) / 2 + WALL + 3.0
    fences = [(SIGHT_U + 3.0, u_far, 0.0, FENCE_T)]                 # back-edge fence over the back edge y331
    vmin = min(v for _, _, v, _ in holes)
    pads = [(SIGHT_U + 6.0, -8.0), (SIGHT_U + 6.0, vmin - 3.0)]
    labels = [("아랫판 윗면 Ø8", 5.0, SIGHT_U + 80.0, -8.0, 0.0), ("▼%.0f" % SIGHT_U, 4.0, SIGHT_U + 6.0, -18.0, 0.0),
              ("▼%.0f" % SIGHT_U, 4.0, SIGHT_U + 6.0, vmin + 4.0, 0.0)]
    return vent_template("J-d4", "아랫판_흡기", "가운데 아랫판 흡기 Ø8 구멍판", "CU-PLY-BOTTOM", "윗면", R, origin, holes, fences,
                         sight=(SIGHT_U, (vmin, 0.0)), pads=pads, labels=labels)


# ============================================================================ J-e  depth gauge + test guides

def cone_depth(dbit):
    return (dbit / 2.0) / math.tan(math.radians(POINT_DEG / 2.0))


GAUGES = [("자석8", "자8", BIT_MAG, DEPTH_MAG)]                    # (name, short, bit, depth)
TESTS = [("8", BIT_MAG), ("4", BIT_PILOT)]
GAUGE_H = 26.0


def j_e():
    W = 24.0
    xs_g = [10.0]
    gx1 = 21.0
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
    cuts.append(engrave("깊이", 4.0, 10.5, 21.0, GAUGE_H))
    m = diff(m, cuts)
    tests = [dict(name=n, x=x, y=15.0, d=bore(b), bit=b) for (n, b), x in zip(TESTS, xs_t)]
    return Jig("J-e", "J-e_깊이게이지·시험블록__1개.stl", "깊이 게이지 + 시험 구멍 블록", m, R_NONE, {}, [],
               dict(gauges=gauges, tests=tests, gauge_h=GAUGE_H))


# ============================================================================ build

OPTIONAL = set()               # every jig here is needed for the hand-drilling plan (README: cad/jigs/README.md)


def make_jigs():
    jigs = [j_b(g) for g in SADDLE_GAPS]
    jigs += [j_d3(), j_d4()]
    jigs.append(j_e())
    return jigs


def _note(j):
    k = j.key
    if k.startswith("J-b"):
        t = "%s: 4개 중 손으로 밀어 끼워지는 가장 좁은 하나만 씀 (뒤판 윗모서리 자석 자리 4)" % j.title
    elif k.startswith("J-d"):
        t = "%s: 울타리를 기준 모서리에 대고 Ø8 %d개 관통 (밑에 자투리)" % (j.title, j.meta["n"])
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
