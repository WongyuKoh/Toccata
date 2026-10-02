"""Toccata rear bar / body - L1 LOW rear bar (2026-09-30) as Part instances (world coordinates, assembled pose).

Governing spec: spec/body_low_L1.json - user request '뒷바 높이를 건반과 비슷하게' + sound-requirements R30 (speakers face
the player, front baffle's upper part tilted back 30 deg, no up-firing, inner volume >= 2.9 L; W1 acoustic check passed:
2.95 L on the inner faces, aim 28..39 deg, D14 226 mm). Details are reused from the tall v3.2 version
(src/body_v3_tall.py) and its specs:
  spec/body_speakers.json        driver CW-100B25 data, grille lattice, gasket, XT30U-F pocket size, toggle latch L64
  spec/body_centre_unit.json     CU tray / CU lid / I/O plate / lid supports / power-bank holder / key-storage insert /
                                 small-parts box, moved by L1 shift_from_v3 (dx +36.05, dy +37, dz -17 for the bay
                                 contents; lids and wall tops -34)
  spec/keyaction_features_frame.json   cheek extents (anti-vibration bracket)

L1 layout (all numbers from body_low_L1.json unless marked 추정 in the Part notes):
  rear bar y252..447 on 5 mm rubber feet (box bottoms z5); OPEN cable trough y212..252 between the key modules and the
  rear bar (nothing of the body above z72 there; cables stay low z<=22); overall 1254 x 447
  speaker parts L x-16..197 / R x1025..1238, z5..134: pentagon side panels (y252,z5)(447,5)(447,134)(312.5,134)(252,29.11),
  back 190x129, top, bottom, lower front strip (okoume 11.5), printed 30 deg baffle, outer face (y252,z29.11)->(312.5,133.89),
  driver 1.0 above the slant middle at (y282.75, z82.37), axis (-cos30, +sin30) in (y,z)
  centre unit x200..1022 z5..88 (inner z16.5..76.5, y263.5..435.5); 3 mm EVA joint gaps x197..200 / x1022..1025 (D15)

Slanted parts are built in a LOCAL frame (x = world x - driver x, y = into the baffle along -axis, z = up the slant,
origin = driver centre on the outer face) and turned into the world with rot_x(-30) (see sl()).

R31 touchscreen (2026-09-30, governing spec ../touchscreen/CAD_SPEC.md A..F + numbers.json, shared poses in touchscreen.py):
  CU-LID is now 'CU 뚜껑 v2' (hinge blocks at the axis y290 z96, ribbon hole x592..614 y292..298, leg pocket, 4 fold feet,
  2 front M3x10 screws; printed rib face down); CU-FL / CU-FR corner supports are screw type (no magnets there);
  new printed parts in 07_터치스크린: cradle (built in its u/w/x frame, placed at 25 deg), support leg, window cover,
  2 ribbon clips, optional screen cover; folded (transport) copies carry note='altview' in group
  '터치스크린 (접은 상태, 별도 보기)' (no print file of their own, left out of the one-file assembly / 3MF / GLB / viewer).

Not modelled: plywood-to-plywood glue, wood screws other than the bracket screw, foot screws, block / holder / tray /
I/O / insert 13 mm screws, latch M3x10 screws, board screws.
Every printed part: kind='print', one body, lies on the bed via to_bed(orient(...)), print folder 05_본체출력물.
Horizontal holes in printed parts are teardrops whose apex points up in the print orientation.
"""
import json
import re
import math
import os

from manifold3d import CrossSection, FillRule, Manifold

from cadlib import box, cyl_x, cyl_y, cyl_z, diff, mirror_x, orient, prism_x, prism_y, prism_z, rot_x, to_bed, union
from parts import COLORS, Part
import touchscreen as TS

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

FOLDER = "05_본체출력물"
SRC_L1 = "spec/body_low_L1.json"
SRC_S = "spec/body_speakers.json"
SRC_C = "spec/body_centre_unit.json"
SRC_F = "spec/keyaction_features_frame.json"

G_SPK = {"L": "스피커 파트 L", "R": "스피커 파트 R"}
G_CU = "가운데 유닛"
G_CUP = "CU 칸 출력물"
G_JOIN = "뒷바 이음·발"
G_BR = "방진 브래킷"

PETG = "PETG 회색"
PLY = "오꾸메 합판 11.5T"
MIRROR_X = 611.0          # speaker parts L/R and the joints are mirror images about x = (-16 + 1238) / 2

R_NONE = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_FLIP = rot_x(180)       # top face (max z) on the bed
R_YMIN = rot_x(90)        # print z = world y  -> the min-y face on the bed
R_YMAX = rot_x(-90)       # print z = -world y -> the max-y face on the bed


def _load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


L1 = _load("body_low_L1.json")

# ------------------------------------------------------------------ L1 numbers

T = L1["rear_bar"]["panel_t"]                           # 11.5
Y_TR = tuple(L1["cable_trough"]["y"])                   # (212, 252) open cable trough
Y_RB = tuple(L1["rear_bar"]["y"])                       # (252, 447)
ZB = L1["feet"]["box_bottom_z"]                         # 5.0  box bottoms on 5 mm feet
Z_TROUGH_MAX = 72.0                                     # trough_rule: nothing above z72 in y212..252
SPK = L1["speaker"]
SPK_X = {"L": tuple(SPK["L"]["x"]), "R": tuple(SPK["R"]["x"])}      # (-16, 197) / (1025, 1238)
SPK_ZT = SPK["z"][1]                                    # 134
SX0, SX1 = SPK_X["L"][0] + T, SPK_X["L"][1] - T         # -4.5 .. 185.5  inner x (190), speaker L
SL_A = tuple(SPK["front"]["slant_outer_face"]["from_yz"])    # (252.0, 29.11)
SL_LEN = SPK["front"]["slant_outer_face"]["length"]     # 121
C30, S30 = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
# exact 30 deg face: the spec's to_yz (312.5, 133.89) and driver z81.5 are the same points rounded (133.8995 / 81.5048);
# using the exact values keeps the driver seat, gasket and grille flat on the printed face (no 0.005 mm skew)
SL_B = (SL_A[0] + S30 * SL_LEN, SL_A[1] + C30 * SL_LEN)
assert all(abs(a - b) < 0.011 for a, b in zip(SL_B, SPK["front"]["slant_outer_face"]["to_yz"]))
DRV = SPK["driver"]
DRV_S = SL_LEN / 2.0 + 1.0                              # driver centre 1.0 above the slant middle (61.5): magnet 2.0 over the bottom panel
DRV_YZ = (SL_A[0] + S30 * DRV_S, SL_A[1] + C30 * DRV_S)  # (282.75, 82.37) = spec centre_yz
assert all(abs(a - b) < 0.011 for a, b in zip(DRV_YZ, DRV["centre_yz"]))
DRV_X = dict(DRV["x_centre"])                           # L 90.5 / R 1131.5
PENT = [(252.0, ZB), (447.0, ZB), (447.0, SPK_ZT), (312.5, SPK_ZT), (SL_A[0], SL_A[1])]   # side-panel pentagon (y, z)
TOP_Y0 = 325.8          # top panel front edge: the baffle carries the corner y312.5..325.8 (inner face meets z134 at y325.84)
Z_BOT_TOP = ZB + T      # 16.5 bottom panels' top face
Z_TOP_UNDER = SPK_ZT - T    # 122.5 speaker top panel underside

CU = L1["centre"]
CU_X = tuple(CU["x"])                                   # (200, 1022)
CU_Z = tuple(CU["z"])                                   # (5, 88)
CU_IZ = tuple(CU["inner_z"])                            # (16.5, 76.5)
CU_IY = tuple(CU["inner_y"])                            # (263.5, 435.5)
BAYS = {k: tuple(v) for k, v in CU["bays_inner_x"].items()}
X_DIV = (BAYS["divider"][0] + BAYS["divider"][1]) / 2.0          # 556.05 bottom_L / tray / back_L / I-O joint line
X_LDIV = (BAYS["low_divider"][0] + BAYS["low_divider"][1]) / 2.0  # 756.05
TRAY_X = (X_DIV + 0.2, X_LDIV - 0.2)                    # 556.25 .. 755.85 (0.2 each side, as v3)
NOTCH = (583.0, 733.0, CU_IZ[0], 34.0)                  # front-panel cable inlet notch x0, x1, z0, z1
SH = L1["shift_from_v3"]["cu_bay"]
DX, DY, DZ = SH["dx"], SH["dy"], SH["dz"]               # CU bay contents v3 -> L1
DZ_TOP = CU_IZ[1] - 110.5                               # -34: wall tops / lids v3 z110.5 -> L1 z76.5
IO = CU["io_plate"]
IO_HZ = IO["holes"]["z"]                                # 46.5
IO_HX = {"J501": IO["holes"]["pedal_jack_J501_x"], "SW": IO["holes"]["switch_KCD1_x"],
         "USBC": IO["holes"]["usb_c_input_x"], "PASS": IO["holes"]["cable_pass_x"]}
JOINT_T = L1["joint_eva"]["t"]                          # 3.0 EVA gap

# exported for electronics.py (the other agent): speaker-side XT30U-F pocket (x0, x1, y0, y1, z0, z1), mouth toward the CU
XT30_POCKET = {"L": (183.4, 196.0, 240.2, 251.0, 25.0, 30.6)}
XT30_POCKET["R"] = (2 * MIRROR_X - 196.0, 2 * MIRROR_X - 183.4, 240.2, 251.0, 25.0, 30.6)
DRIVER_POSE = {s: (DRV_X[s], DRV_YZ[0], DRV_YZ[1]) for s in "LR"}     # centre on the outer face; axis (0, -C30, S30)
DRIVER_AXIS = (0.0, -C30, S30)

# ------------------------------------------------------------------ geometry helpers


def B(b, dx=0.0, dy=0.0, dz=0.0):
    """spec box {x:[..], y:[..], z:[..]} -> solid (optionally shifted)."""
    return box(b["x"][0] + dx, b["x"][1] + dx, b["y"][0] + dy, b["y"][1] + dy, b["z"][0] + dz, b["z"][1] + dz)


def _nseg(d):
    return int(max(24, min(96, math.ceil(math.pi * d / 0.35))))


def _hull2d(pts):
    """convex hull, counter-clockwise (monotone chain)."""
    pts = sorted(set((round(a, 9), round(b, 9)) for a, b in pts))
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


def tear_pts(c1, c2, d, apex=None):
    """circle (+ 45 deg roof point toward `apex`, a 2D direction in the same plane) as a CCW polygon."""
    n = _nseg(d)
    r = d / 2.0
    pts = [(c1 + r * math.cos(2 * math.pi * i / n), c2 + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    if apex is not None:
        ax, ay = apex
        L = math.hypot(ax, ay)
        pts.append((c1 + ax / L * r * math.sqrt(2.0), c2 + ay / L * r * math.sqrt(2.0)))
    return _hull2d(pts)


def _prism(axis, poly, a0, a1):
    return {"x": prism_x, "y": prism_y, "z": prism_z}[axis](poly, a0, a1)


def hole(axis, c1, c2, a0, a1, d, apex=None):
    """round hole along axis ('x': c=(y,z), 'y': c=(x,z), 'z': c=(x,y)); apex = teardrop roof direction or None."""
    return _prism(axis, tear_pts(c1, c2, d, apex), a0, a1)


def slot_hole(axis, p, q, a0, a1, d, apex=None):
    """hull of two (teardrop) circles at p and q (2D points in the axis plane)."""
    return _prism(axis, _hull2d(tear_pts(p[0], p[1], d, apex) + tear_pts(q[0], q[1], d, apex)), a0, a1)


def stadium_y(cx, cz, w, h, y0, y1):
    """stadium opening w (x) x h (z) through y0..y1."""
    r = (w - h) / 2.0
    return slot_hole("y", (cx - r, cz), (cx + r, cz), y0, y1, h)


def csk_y(cx, cz, y_face, y_end, d_hole=4.5, d_head=8.6, apex=None):
    """countersunk screw hole along +y: head cone at the face y_face (screw goes toward +y), shank to y_end (teardrop
    toward `apex` in (x, z) when the hole lies horizontal in the print)."""
    cone = Manifold.cylinder((d_head - d_hole) / 2.0 + 0.01, d_head / 2.0, d_hole / 2.0 - 0.005, _nseg(d_head))
    cone = cone.rotate((-90, 0, 0)).translate((cx, y_face - 0.01, cz))
    return union([hole("y", cx, cz, y_face - 0.5, y_end, d_hole, apex=apex), cone, cyl_y(cx, cz, y_face - 6.0, y_face, d_head)])


def bed(m, R):
    return to_bed(orient(m, R))


def mx(m):
    """mirror a left-side solid to the right side (speaker parts, joints, bracket)."""
    return mirror_x(m, MIRROR_X)


def mxv(x):
    return 2 * MIRROR_X - x


def mdims(dims):
    """mirror (axis, a, b, label, lane) dims of a left part to the right part."""
    out = []
    for (a, p, q, lab, ln) in dims:
        if a == "x":
            p, q = sorted((mxv(p), mxv(q)))
        out.append((a, p, q, lab, ln))
    return out


R_SL = rot_x(-30.0)       # local slant frame -> world: local y (into the baffle) -> (0, cos30, -sin30), local z -> (0, sin30, cos30)
R_SL_BED = rot_x(120.0)   # world -> print: the outer face (normal (0, -cos30, sin30)) faces down on the bed


def sl(m, xc):
    """local slant-frame solid -> world (origin = driver centre on the outer face at x = xc)."""
    return orient(m, R_SL, (xc, DRV_YZ[0], DRV_YZ[1]))


def face_pt(s):
    """(y, z) of the outer baffle face, s mm up the slant from its bottom edge (y252, z29.11)."""
    return (SL_A[0] + S30 * s, SL_A[1] + C30 * s)


class Out(list):
    def add(self, id, name_ko, name_en, kind, group, solid, color, material="", source="", note="",
            print_name=None, R=None, print_note="", dims=(), folder=None, ps=None, no_print=False):
        """ps: print solid given directly (already on the bed); no_print: a printed part shown a second time (the
        folded 'altview' copy) - no print file of its own."""
        if kind == "print" and not no_print:
            ps = to_bed(ps) if ps is not None else bed(solid, R if R is not None else R_NONE)
        else:
            ps = None
        self.append(Part(id=id, name_ko=name_ko, name_en=name_en, kind=kind, group=group, solid=solid, color=color,
                         material=material, print_name=print_name if kind == "print" else None,
                         print_folder=(folder or FOLDER) if kind == "print" else None, print_solid=ps, print_note=print_note,
                         dims=list(dims), source=source, note=note))


# ------------------------------------------------------------------ speaker parts L / R

def baffle_poly():
    """baffle cross-section (y, z), CCW: outer face A->B (spec), bottom on the front strip (z29.11), inner face 11.5
    behind the outer face, top cap filling the corner in front of the top panel (y312.5..325.8, z122.5..134)."""
    iy, iz = T * C30, -T * S30                          # outer -> inner offset (+9.96, -5.75)

    def inner_y(z):
        s = (z - SL_A[1] - iz) / C30
        return SL_A[0] + S30 * s + iy
    return [SL_A, (inner_y(SL_A[1]), SL_A[1]), (inner_y(Z_TOP_UNDER), Z_TOP_UNDER), (TOP_Y0, Z_TOP_UNDER),
            (TOP_Y0, SPK_ZT), (SL_A[0] + (SPK_ZT - SL_A[1]) * S30 / C30, SPK_ZT)]      # corner on the exact 30 deg face


def cavity_poly():
    """speaker inner air section (y, z) on the inner faces (driver not subtracted)."""
    bp = baffle_poly()
    F, E = bp[1], bp[2]
    return [(Y_RB[1] - T, Z_BOT_TOP), (Y_RB[1] - T, Z_TOP_UNDER), E, F, (Y_RB[0] + T, SL_A[1]), (Y_RB[0] + T, Z_BOT_TOP)][::-1]


def poly_area(p):
    return 0.5 * abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))))


DRV_PCD = 115.0
DRV_PIL = [(sx * DRV_PCD / 2 / math.sqrt(2), sz * DRV_PCD / 2 / math.sqrt(2)) for sx in (-1, 1) for sz in (-1, 1)]  # local (x, z)
GR_X, GR_ZLO, GR_ZHI = 75.0, -57.0, 57.0                # grille outer: 150 in x, 114 along the slant (s 4.5..118.5)
GR_RI = 53.0                                            # ring inner half size (frame 105 + 0.5 each side)
GR_FACE = (-13.0, -11.0)                                # grille face plate (local y), ring -11..0 on the baffle face
GR_HOLES = [(sx * 64.0, sz * 40.0) for sx in (-1, 1) for sz in (-1, 1)]   # grille screws in the 22-wide side walls
WIRE_X, WIRE_S = 180.4, 11.0                            # speaker-wire hole (L): x, s along the slant


def build_grille(S):
    """grille + spacer ring in the local slant frame (face plate y-13..-11, ring y-11..0 standing on the baffle face)."""
    gr = next(p for p in S["printed"] if p["id"] == "spk_grille")
    lat = gr["lattice"]
    af, pitch = lat["across_flats"], lat["pitch"]
    fy0, fy1 = GR_FACE
    solid = box(-GR_X, GR_X, fy0, 0.0, GR_ZLO, GR_ZHI)
    cuts = [box(-GR_RI, GR_RI, fy1, 0.01, -GR_RI, GR_RI)]
    rc = af / math.sqrt(3.0)
    sq = CrossSection([[(-GR_RI, -GR_RI), (GR_RI, -GR_RI), (GR_RI, GR_RI), (-GR_RI, GR_RI)]], FillRule.NonZero)
    dv = pitch * math.sqrt(3.0) / 2.0
    nrow = int(GR_RI / dv) + 2
    for j in range(-nrow, nrow + 1):
        off = (pitch / 2.0) if (j % 2) else 0.0
        for i in range(-nrow - 1, nrow + 2):
            u, v = i * pitch + off, j * dv
            pts = [(u + rc * math.cos(math.radians(30 + 60 * k)), v + rc * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
            c = CrossSection([pts], FillRule.NonZero) ^ sq
            if c.area() < 3.0:
                continue
            for poly in c.to_polygons():
                if len(poly) >= 3:
                    cuts.append(prism_y([tuple(q) for q in poly], fy0 - 0.01, fy1 + 0.01))
    for (hx, hz) in GR_HOLES:
        cuts.append(cyl_y(hx, hz, fy0 - 0.01, 0.01, 4.5))
    return diff(solid, cuts)


def speaker_parts(S, out):
    g_ko = {"SIDEOUT": "옆판(바깥쪽)", "SIDEIN": "옆판(가운데 유닛 쪽)", "BACK": "뒤판", "TOP": "윗판", "BOTTOM": "아랫판",
            "FRONT": "앞 아래 띠(세운 부분)"}
    g_en = {"SIDEOUT": "side panel (outer)", "SIDEIN": "side panel (centre-unit side)", "BACK": "back panel", "TOP": "top panel",
            "BOTTOM": "bottom panel", "FRONT": "lower front strip"}
    lens = {"TOP": Y_RB[1] - T - TOP_Y0, "BOTTOM": Y_RB[1] - T - Y_RB[0], "FRONT": SL_A[1] - Z_BOT_TOP}
    left = {
        "SIDEOUT": prism_x(PENT, SPK_X["L"][0], SX0),
        "SIDEIN": prism_x(PENT, SX1, SPK_X["L"][1]),
        "BACK": box(SX0, SX1, Y_RB[1] - T, Y_RB[1], ZB, SPK_ZT),
        "TOP": box(SX0, SX1, TOP_Y0, Y_RB[1] - T, Z_TOP_UNDER, SPK_ZT),
        "BOTTOM": box(SX0, SX1, Y_RB[0], Y_RB[1] - T, ZB, Z_BOT_TOP),
        "FRONT": box(SX0, SX1, Y_RB[0], Y_RB[0] + T, Z_BOT_TOP, SL_A[1]),
    }
    cut_txt = {
        "SIDEOUT": "195×129 판에서 앞 위 모서리를 곧게 한 번 자른 오각형 (y252,z5)(447,5)(447,134)(312.5,134)(252,29.11)",
        "SIDEIN": "195×129 판에서 앞 위 모서리를 곧게 한 번 자른 오각형 (바깥쪽 옆판과 같은 모양)",
        "BACK": "190×129 (옆판 사이, 아랫판·윗판 뒤를 막음)",
        "TOP": "190×%.1f (y%.1f~435.5, 앞 모서리는 출력 앞판 윗부분에 맞닿음)" % (lens["TOP"], TOP_Y0),
        "BOTTOM": "190×%.1f (y252~435.5)" % lens["BOTTOM"],
        "FRONT": "190×%.2f (z16.5~29.11, 두께 11.5 - 아랫판 위에 세움)" % lens["FRONT"],
    }
    for side in "LR":
        g = G_SPK[side]
        for tag in ("SIDEOUT", "SIDEIN", "BACK", "TOP", "BOTTOM", "FRONT"):
            m = left[tag] if side == "L" else mx(left[tag])
            ko = g_ko[tag]
            if side == "R" and tag.startswith("SIDE"):
                ko = g_ko[tag]
            out.add("SPK%s-PLY-%s" % (side, tag), "스피커 파트 %s %s" % (side, ko), "speaker part %s %s" % (side, g_en[tag]),
                    "plywood", g, m, COLORS["plywood"], PLY,
                    source=SRC_L1 + " speaker.panels / front.vertical_part (재단 %s)" % cut_txt[tag],
                    note=("추정: 윗판 앞 모서리 y%.1f - 출력 앞판이 y312.5~%.1f 윗모서리(60° 각)를 채워 날 끝이 생기지 않게 함 (안 부피 변화 없음)"
                          % (TOP_Y0, TOP_Y0)) if tag == "TOP" else "")

    # ---- printed slanted baffle (left, then mirrored)
    poly = baffle_poly()
    baf = prism_x(poly, SX0, SX1)
    cuts = [cyl_y(0.0, 0.0, -1.0, T + 1.5, DRV["cutout_d"])]
    cuts += [cyl_y(px, pz, -0.5, 10.0, 3.4) for (px, pz) in DRV_PIL]
    cuts += [cyl_y(hx, hz, -0.5, 9.0, 3.4) for (hx, hz) in GR_HOLES]
    cuts.append(cyl_y(WIRE_X - DRV_X["L"], WIRE_S - DRV_S, -0.5, T + 1.5, 6.0))
    baf = diff(baf, [sl(c, DRV_X["L"]) for c in cuts])
    fy, fz = face_pt(WIRE_S)
    for side in "LR":
        m = baf if side == "L" else mx(baf)
        xa, xb = (SX0, SX1) if side == "L" else (mxv(SX1), mxv(SX0))
        cx = DRV_X[side]
        wx = WIRE_X if side == "L" else mxv(WIRE_X)
        pil_x = sorted(cx + p[0] for p in DRV_PIL)
        dims = [("x", xa, xb, "앞판 폭 190 (옆판 사이)", 0), ("x", cx - 47, cx + 47, "컷아웃 Ø94", 1),
                ("x", pil_x[0], pil_x[-1], "유닛 파일럿 PCD115 45° (Ø3.4 깊이 10)", 2),
                ("x", cx - 64, cx + 64, "그릴 파일럿 128 (Ø3.4 깊이 9)", 3),
                ("x", min(wx, xb if side == "L" else xa), max(wx, xb if side == "L" else xa), "선 구멍 Ø6 x%.1f" % wx, 4),
                ("y", SL_A[0], TOP_Y0, "앞 아래 끝 y252 → 윗모서리 y%.1f" % TOP_Y0, 0), ("y", SL_A[0], DRV_YZ[0], "유닛 중심 y282.75", 1),
                ("y", SL_A[0], poly[1][0], "밑면 %.2f (띠 위)" % (poly[1][0] - SL_A[0]), 2),
                ("z", SL_A[1], SPK_ZT, "z29.11 → 134 (경사 30°, 바깥면 길이 121)", 0), ("z", SL_A[1], DRV_YZ[1], "유닛 중심 z82.37 (경사 가운데 +1.0)", 1),
                ("z", Z_TOP_UNDER, SPK_ZT, "윗모서리 11.5 (윗판 앞)", 2)]
        out.add("SPK%s-BAFFLE" % side, "스피커 앞판(배플, 30° 경사) %s" % side, "speaker baffle (printed, 30 deg slant) " + side,
                "print", G_SPK[side], m, COLORS["printed_body"], "PETG (검정 또는 회색)",
                source=SRC_L1 + " speaker.front.slant_outer_face (y252,z29.11)→(312.5,133.89), 30°, 두께 11.5, 옆판 사이 x 안폭 190; "
                "driver centre (y282.75, z82.37) x%.1f, 컷아웃 Ø94; " % cx + SRC_S + " spkL_baffle (유닛 파일럿 Ø3.4 깊이 10 PCD115 45°, "
                "그릴 파일럿 Ø3.4 깊이 9, 선 구멍 Ø6)",
                note="추정: 파일럿·선 구멍은 경사면 좌표(면에 수직)로 - 유닛 파일럿 PCD115 45° (경사 방향·x 방향 ±40.66), 그릴 파일럿 "
                     "(x ±64, 경사 ±40 = 그릴 링의 22 폭 옆벽 가운데); 추정: 스피커선 구멍 Ø6 x%.1f, 경사 s%.0f (면 위 y%.1f z%.1f) - "
                     "가운데 유닛 쪽 모서리에서 %.1f (구멍 벽 %.1f), 아래 띠 뒤 모서리(y263.5 z29.11)와 2 이상; 선은 바로 아래 XT30 받침의 "
                     "위로 열린 선 홈으로 내려감; 추정: 윗모서리는 윗판 앞(y%.1f)까지 채운 덩어리(60° 모서리, 날 끝 없음); "
                     "밑면(z29.11)은 앞 아래 띠 윗면에 본드, 옆은 옆판에 본드(밀봉)"
                     % (wx, WIRE_S, fy, fz, SX1 - WIRE_X, SX1 - WIRE_X - 3.0, TOP_Y0),
                print_name="스피커앞판_경사배플_" + side, R=R_SL_BED,
                print_note="바깥면(유닛·그릴 면)을 베드에 눕혀 출력 - 경사면이 평평한 판이 됨(190×약 125, 두께 11.5 + 윗모서리 덩어리). "
                           "서포트 없음(윗모서리·밑면은 베드 면에서 60°/30° 경사). 파일럿은 베드 면에서 막힌 구멍. 벽 4줄 + 채움 30~40 % "
                           "(그리드/자이로이드). 옆판 사이에 끼워 둘레를 목공본드(오공 205)로 밀봉, 선 구멍은 선을 넣은 뒤 본드로 막음",
                dims=dims)

    # ---- grille + ring (identical L / R: built in the slant frame, trimmed at the box top z134)
    G = build_grille(S)
    for side in "LR":
        cx = DRV_X[side]
        gw = sl(G, cx) ^ box(cx - 100, cx + 100, 150.0, 400.0, 0.0, SPK_ZT)
        s0, s1 = DRV_S + GR_ZLO, DRV_S + GR_ZHI
        out.add("SPK%s-GRILLE" % side, "스피커 육각 그릴 + 스페이서 링 (경사면용) %s" % side, "hex grille + spacer ring (slant) " + side,
                "print", G_SPK[side], gw, COLORS["printed_body"], "PETG 회색 또는 검정",
                source=SRC_L1 + " speaker.driver.mount (그릴은 콘 구멍과 나사 머리를 덮고 경사 방향 ≤118, x ≤150, 법선 방향 ≤15, "
                                "통로 쪽은 z22~72) ; " + SRC_S + " spk_grille (육각 맞은편 10 · 살 1.8 · 피치 11.8, 그릴 면 2.0)",
                note="추정: 바깥 150 (x) × 114 (경사, s%.1f~%.1f), 링 안쪽 106×106 (유닛 프레임 105 + 0.5씩), 링 높이 11 + 그릴 면 2 = "
                     "면에서 13 (≤15) - 유닛 플랜지 4 + 가스켓 3 = 7 위의 8호 둥근머리(약 3) 윗면 10과 그릴 면 뒤 11 사이 1.0; "
                     "링 옆벽 22 (x)·위아래 벽 4 (경사); 그릴 고정 4-Ø4.5 (x ±64, 경사 ±40), 8호 19 mm → 앞판 물림 6 (파일럿 깊이 9 안); "
                     "추정: 링 위 벽의 바깥 앞 모서리를 z134(상자 윗면)에서 수평으로 잘라 상자 위로 나오지 않게 함; "
                     "그릴 아래 끝은 통로 쪽 y%.1f z%.1f~%.1f (z22 위·z72 아래)"
                     % (s0, s1, face_pt(s0)[0] - 13 * C30, face_pt(s0)[1], face_pt(s0)[1] + 13 * S30),
                print_name="스피커그릴_경사링", R=R_SL_BED,
                print_note="그릴 면을 베드에 두고 링(11)을 위로 세워 출력. 링 위 벽의 잘린 면은 30° 기울기라 서포트 없음. "
                           "직결피스 8호 19 mm ×4로 앞판 파일럿에",
                dims=[("x", cx - GR_X, cx + GR_X, "그릴 150", 0), ("x", cx - GR_RI, cx + GR_RI, "링 안쪽 106", 1),
                      ("x", cx - 64, cx + 64, "고정 구멍 128 (Ø4.5)", 2),
                      ("z", face_pt(s0)[1], min(SPK_ZT, face_pt(s1)[1] + 13 * S30), "경사 114 (s%.1f~%.1f), z134에서 자름" % (s0, s1), 0),
                      ("y", face_pt(s0)[0] - 13 * C30, face_pt(s0)[0], "면에서 13 (링 11 + 그릴 면 2)", 0)])

    # ---- driver EVA gasket (knife cut)
    gk = next(p for p in S["printed"] if p["id"] == "spk_gasket")
    gm = diff(box(-52.5, 52.5, -3.0, 0.0, -52.5, 52.5),
              [cyl_y(0, 0, -3.01, 0.01, gk["dims"]["inner_dia"])] + [cyl_y(px, pz, -3.01, 0.01, 4.8) for (px, pz) in DRV_PIL])
    for side in "LR":
        out.add("SPK%s-GASKET" % side, gk["name_ko"] + " " + side, "driver EVA gasket 3T " + side, "consumable", G_SPK[side],
                sl(gm, DRV_X[side]), COLORS["rubber"], gk["material"],
                source=SRC_S + " printed spk_gasket (105×105×3, 안 Ø94, 4-Ø4.8 PCD115) → " + SRC_L1 + " 경사면 위 유닛 자리",
                note="추정: 안쪽 Ø94·바깥 105×105 (spec assumed) - EVA 3T 자투리를 칼로 재단, 경사 앞판 바깥면 위(법선 0~3)")


# ------------------------------------------------------------------ XT30 holders (in the trough, on the speaker front strip)

XT_PAD = (150.0, 176.0, 247.0, 252.0, 18.5, 31.0)      # screw pad on the front strip (x0, x1, y0, y1, z0, z1)
XT_BODY = (176.0, 196.0, 238.0, 252.0, 22.5, 33.0)     # pocket housing
XT_SLOT = (177.4, 183.4, 242.0, 250.0, 25.0, 33.01)    # open-top wire slot behind the pocket, under the baffle wire hole
XT_SCREWS = [(156.0, 23.0), (169.0, 23.0)]              # (x, z) 8-ho 13 mm countersunk along +y into the strip


def xt30_holders(out):
    b = XT_BODY
    pk = XT30_POCKET["L"]
    hold = union([box(*XT_PAD), box(*b)])
    cuts = [box(pk[0], pk[1] + 0.01, pk[2], pk[3], pk[4], pk[5]), box(*XT_SLOT)]
    cuts += [csk_y(x, z, XT_PAD[2], XT_PAD[3] + 0.01) for (x, z) in XT_SCREWS]
    hold = diff(hold, cuts)
    dims = [("x", XT_PAD[0], b[1], "전체 46", 0), ("x", pk[0], pk[1], "홈 12.6 (XT30U-F 12.4)", 1),
            ("x", XT_SCREWS[0][0], XT_SCREWS[1][0], "나사 간격 13 (접시 자리 Ø8.6)", 2), ("x", XT_SLOT[0], XT_SLOT[1], "선 홈 6", 3),
            ("y", b[2], b[3], "14", 0), ("y", pk[2], pk[3], "홈 10.8", 1), ("y", XT_PAD[2], XT_PAD[3], "나사 판 5", 2),
            ("z", XT_PAD[4], b[5], "z18.5~33", 0), ("z", pk[4], pk[5], "홈 5.6", 1), ("z", XT_PAD[4], XT_PAD[5], "나사 판 z18.5~31", 2)]
    for side in "LR":
        m = hold if side == "L" else mx(hold)
        out.add("SPK%s-XT30HOLDER" % side, "XT30 받침 %s (통로 안, 스피커 앞 아래 띠에)" % side, "XT30 holder " + side, "print", G_SPK[side],
                m, COLORS["printed_body"], PETG,
                source=SRC_L1 + " speaker.xt30 (통로 안 스피커 앞면 y≤252, 모듈 USB 선 z≤22 · O1 x124.75~137.25 → +x · O7 x1111~1123.5 → −x "
                                "를 막지 않는 높이); " + SRC_S + " xt30_holder_L (홈 12.6×10.8×5.6 = XT30U-F 10.2×5.2×12.4 + 여유)",
                note="추정: 새 모양 - 홈 몸통 x%.0f~%.0f y238~252 z22.5~33 (입구 %s, 가운데 유닛 쪽), 나사 판 x%.0f~%.0f y247~252 z18.5~31 "
                     "(그릴 아래면과 1.8 이상). 바닥 z22.5 / 나사 판 밑 z18.5 - 케이블(O1 윗면 z16.25, 바닥 선)은 밑으로 지나감. "
                     "직결피스 8호 13 mm 접시머리 ×2를 +y로 앞 아래 띠(오꾸메, z16.5~29.11)에 (판 5 + 합판 8, 띠 11.5 안에서 멈춤 - 밀폐 유지), "
                     "나사 z23 = 띠 높이 가운데. 스피커선: 앞판 선 구멍(x%.1f, 받침 바로 위)에서 나와 위로 열린 선 홈(x%.1f~%.1f)으로 "
                     "내려가 홈 뒤끝의 XT30U-F 납땜 컵에"
                     % ((b[0], b[1], "+x" if side == "L" else "−x", XT_PAD[0], XT_PAD[1], WIRE_X, XT_SLOT[0], XT_SLOT[1]) if side == "L" else
                        (mxv(b[1]), mxv(b[0]), "−x", mxv(XT_PAD[1]), mxv(XT_PAD[0]), mxv(WIRE_X), mxv(XT_SLOT[1]), mxv(XT_SLOT[0]))),
                print_name="XT30받침_" + side, R=R_YMAX,
                print_note="뒷면(y252, 띠에 닿는 면)을 베드에. 홈 천장은 브리지 5.6, 접시 자리는 위로 열림 - 서포트 없음. "
                           "XT30U-F는 선을 먼저 홈에 넣어 납땜한 뒤 입구 쪽에서 밀어 넣음(뜨거운 본드 한 방울)",
                dims=dims if side == "L" else mdims(dims))


# ------------------------------------------------------------------ feet (5 mm rubber, i039 28x5)

FEET = [("스피커 L", 4.0, 272.0), ("스피커 L", 177.0, 272.0), ("스피커 L", 4.0, 427.0), ("스피커 L", 177.0, 427.0),
        ("가운데 유닛", 220.0, 272.0), ("가운데 유닛", 220.0, 427.0), ("가운데 유닛 (CU 트레이)", 200.0 + 456.05, 336.0),
        ("가운데 유닛 (CU 트레이)", 200.0 + 456.05, 416.0), ("가운데 유닛", 1002.0, 272.0), ("가운데 유닛", 1002.0, 427.0),
        ("스피커 R", mxv(177.0), 272.0), ("스피커 R", mxv(4.0), 272.0), ("스피커 R", mxv(177.0), 427.0), ("스피커 R", mxv(4.0), 427.0)]
TRAY_FEET = [(656.05, 336.0), (656.05, 416.0)]          # = v3 tray foot bosses (620, 299)/(620, 379) + (dx, dy)


def feet(out):
    h = L1["feet"]["h"]
    foot0 = diff(cyl_z(0, 0, 0.0, h, 28.0), [cyl_z(0, 0, -0.01, h + 0.01, 4.5), cyl_z(0, 0, -0.01, 2.0, 9.0)])
    for i, (grp, x, y) in enumerate(FEET):
        out.add("FOOT-%02d" % (i + 1), "피스고무발 28×5 (i039 화성고무, %s)" % grp, "rubber foot 28x5 (i039)", "bought", G_JOIN,
                foot0.translate((x, y, 0.0)), COLORS["rubber"], "고무",
                source=SRC_L1 + " feet (화성고무 피스고무발 28×5, BOM i039; 상자 밑면 z5)",
                note="추정: 자리 = 상자 모서리에서 약 20 안쪽 (스피커 x4/177 y272/427, 가운데 x220/1002 y272/427 + CU 트레이 밑 2개 = v3 "
                     "트레이 고무발 보스 자리 +dx/dy); 머리 자리 Ø9 깊이 2로 표시, 8호 13 mm로 고정 (스피커 아랫판 11.5 안에서 멈춤)")


# ------------------------------------------------------------------ joints: EVA strips, dovetail blocks, toggle latches

JX_S, JX_C = SPK_X["L"][1], CU_X[0]                     # 197 speaker face / 200 centre face (left joint)
JY0 = Y_RB[1]                                           # 447 back face
JT = 14.0                                               # block thickness y447..461
JYC = JY0 + JT / 2.0                                    # 454 dovetail centre
DT_ROOT, DT_TIP, DT_DEPTH, DT_CL, DT_TIPGAP = 5.0, 8.0, 4.0, 0.2, 0.5
FB = (157.0, JX_S, 10.0, 84.0)                          # female block (speaker side): x0, x1, z0, z1
MB = (JX_C, 240.0, 18.0, 76.0)                          # male block (centre side)
FB_SCREWS = [(163.0, 18.0), (163.0, 76.0), (178.0, 18.0), (178.0, 76.0)]
MB_SCREWS = [(208.0, 24.0), (208.0, 67.5), (232.0, 24.0), (232.0, 67.5)]   # counterbore teardrops stay inside z18..76
LATCH_ZC = 47.0
LATCH_Y = JY0 + JT                                      # 461 latch seat face
CATCH_HOLES = [(JX_C - 23.8, LATCH_ZC - 6.25), (JX_C - 23.8, LATCH_ZC + 6.25)]
BODY_HOLES = [(JX_C + 22.0, LATCH_ZC - 5.25), (JX_C + 22.0, LATCH_ZC + 5.25)]
EVA_STRIPS = [(254.0, 445.0, 8.0, 28.0), (282.0, 445.0, 52.0, 72.0)]   # (y0, y1, z0, z1) per joint


def latch_left():
    """L64 toggle latch at the left joint (closed): v3 shape moved from (joint x164, face y418, z35) to (centre face x200,
    block face y461, z47). body on the centre block, catch on the speaker block."""
    dx, dy, dz = JX_C - 164.0, LATCH_Y - 418.0, LATCH_ZC - 35.0
    zc = 35.0
    body = union([
        diff(box(165.0, 191.0, 418.0, 419.2, zc - 12.6, zc + 12.6), [cyl_y(186.0, zc + s * 5.25, 417.99, 419.21, 4.0) for s in (-1, 1)]),
        box(172.0, 181.0, 419.2, 420.2, zc - 4.0, zc + 4.0),
        box(150.0, 181.0, 420.2, 428.0, zc - 4.0, zc + 4.0),
        box(149.0, 151.0, 421.0, 422.0, zc - 7.5, zc + 7.5),
        box(141.0, 151.0, 421.0, 422.0, zc - 7.5, zc - 6.5),
        box(141.0, 151.0, 421.0, 422.0, zc + 6.5, zc + 7.5),
        box(141.0, 142.3, 421.0, 422.0, zc - 7.5, zc + 7.5),
    ])
    catch = union([
        diff(box(137.0, 148.8, 418.0, 419.2, zc - 11.65, zc + 11.65), [cyl_y(140.2, zc + s * 6.25, 417.99, 419.21, 4.0) for s in (-1, 1)]),
        box(145.3, 146.8, 419.2, 426.8, zc - 6.0, zc + 6.0),
        box(143.3, 146.8, 425.6, 426.8, zc - 6.0, zc + 6.0),
    ])
    return body.translate((dx, dy, dz)), catch.translate((dx, dy, dz))


def dt_poly(half_root, half_tip, x_root, x_tip, x_ext0, x_ext1):
    """dovetail plan polygon (x, y) around y = JYC: flank from (x_root, +-half_root) to (x_tip, +-half_tip), extended with the
    same flank to x_ext0 (beyond the tip) and x_ext1 (beyond the root)."""
    k = (half_tip - half_root) / (x_tip - x_root)
    h0 = half_root + k * (x_ext0 - x_root)
    h1 = half_root + k * (x_ext1 - x_root)
    pts = [(x_ext0, JYC - h0), (x_ext1, JYC - h1), (x_ext1, JYC + h1), (x_ext0, JYC + h0)]
    return _hull2d(pts)


def joints(out):
    # ---- EVA 3T strips in the 3 mm gaps (glued on the speaker side panel)
    for side in "LR":
        for i, (y0, y1, z0, z1) in enumerate(EVA_STRIPS):
            m = box(JX_S, JX_C, y0, y1, z0, z1)
            m = m if side == "L" else mx(m)
            out.add("JOIN-EVA-%s%d" % (side, i + 1), "EVA 3T 띠 (이음 틈, %s %s)" % (side, "아래" if i == 0 else "위"),
                    "EVA 3T strip in the joint gap %s %d" % (side, i + 1), "consumable", G_JOIN, m, COLORS["rubber"], "EVA 3T (MEV1)",
                    source=SRC_L1 + " joint_eva (W1 D15: 3 mm EVA 3T 띠를 이음면에, 가운데 유닛 폭 822)",
                    note="추정: 띠 2개 %.0f×20 (z%.0f~%.0f, y%.0f~%.0f) - 스피커 옆판 바깥면(x%s)에 붙임; 위 띠는 경사 앞 모서리 뒤에서 시작"
                         % (y1 - y0, z0, z1, y0, y1, "197" if side == "L" else "1025"))

    # ---- female block (speaker side) and male block (centre side), both on the back face y447, slide along z
    x0, x1, z0, z1 = FB
    fem = box(x0, x1, JY0, JY0 + JT, z0, z1)
    groove = dt_poly(DT_ROOT / 2 + DT_CL, DT_TIP / 2 + DT_CL, JX_S, JX_S - DT_DEPTH, JX_S - DT_DEPTH - DT_TIPGAP, JX_S + 0.5)
    cuts = [prism_z(groove, z0 - 0.01, z1 + 0.01)]
    for (sx, sz) in FB_SCREWS:
        cuts.append(hole("y", sx, sz, JY0 - 0.01, JY0 + JT + 0.01, 4.5, apex=(0, 1)))
        cuts.append(hole("y", sx, sz, JY0 + 3.0, JY0 + JT + 0.01, 9.0, apex=(0, 1)))
    for (hx, hz) in CATCH_HOLES:
        cuts.append(hole("y", hx, hz, LATCH_Y - 10.0, LATCH_Y + 0.01, 2.75, apex=(0, 1)))
    fem = diff(fem, cuts)
    x0, x1, z0, z1 = MB
    tongue = dt_poly(DT_ROOT / 2, DT_TIP / 2, JX_S, JX_S - DT_DEPTH, JX_S - DT_DEPTH, JX_S)
    neck = box(JX_S - 0.01, JX_C + 0.01, JYC - DT_ROOT / 2, JYC + DT_ROOT / 2, z0, z1)
    male = union([box(x0, x1, JY0, JY0 + JT, z0, z1), prism_z(tongue, z0, z1), neck])
    cuts = []
    for (sx, sz) in MB_SCREWS:
        cuts.append(hole("y", sx, sz, JY0 - 0.01, JY0 + JT + 0.01, 4.5, apex=(0, 1)))
        cuts.append(hole("y", sx, sz, JY0 + 3.0, JY0 + JT + 0.01, 9.0, apex=(0, 1)))
    for (hx, hz) in BODY_HOLES:
        cuts.append(hole("y", hx, hz, LATCH_Y - 10.0, LATCH_Y + 0.01, 2.75, apex=(0, 1)))
    male = diff(male, cuts)
    why = ("추정: L1은 상자 밑이 고무발 5 mm뿐이라 v3처럼 밑면에 블록을 달 수 없고, 스피커 파트 앞은 경사면·통로(z72 위 금지, 선 z≤22)라 "
           "도브테일·래치를 뒷면(y447)으로 옮김: 뒷면에서 %.0f 튀어나옴(블록 y447~%.0f, 잠근 래치 ~y%.0f). "
           "도브테일은 z 방향으로 미끄러짐(스피커 파트를 위에서 내려 끼움, 홈은 위아래가 열림): 수 = 목 %.0f(틈 3을 건넘) + 머리 뿌리 %.0f·끝 %.0f·깊이 %.0f, "
           "암 홈 = 틈 0.2씩 + 끝 %.1f 여유 - x로는 EVA 띠가 눌릴 만큼 헐겁게(진동 격리 D15), y는 잡음. 틈 3 mm 기준(암 홈이 3 mm 바깥, spec joint_eva)"
           % (JT + 10.0, JY0 + JT, LATCH_Y + 10.0, JOINT_T, DT_ROOT, DT_TIP, DT_DEPTH, DT_TIPGAP))
    fdims = [("x", FB[0], FB[1], "40 (스피커 뒤판 위, 이음면 x197까지)", 0), ("x", JX_S - DT_DEPTH - DT_TIPGAP, JX_S, "홈 깊이 4.5", 1),
             ("x", FB_SCREWS[0][0], FB_SCREWS[2][0], "나사 x163/178 (Ø4.5 + 자리 Ø9)", 2),
             ("y", JY0, JY0 + JT, "두께 14 (뒷면 y447에서)", 0), ("y", JYC - DT_TIP / 2 - DT_CL, JYC + DT_TIP / 2 + DT_CL, "홈 끝 8.4", 1),
             ("z", FB[2], FB[3], "74 (z10~84)", 0), ("z", LATCH_ZC - 6.25, LATCH_ZC + 6.25, "래치 걸이 파일럿 12.5 (z47 중심)", 1)]
    mdims_ = [("x", JX_S - DT_DEPTH, MB[1], "수 머리 4 + 목 3 + 판 40", 0), ("x", JX_S - DT_DEPTH, JX_S, "머리 4 (뿌리 5·끝 8)", 1),
              ("x", MB_SCREWS[0][0], MB_SCREWS[2][0], "나사 x208/232", 2),
              ("y", JY0, JY0 + JT, "두께 14", 0), ("y", JYC - DT_TIP / 2, JYC + DT_TIP / 2, "머리 끝 8", 1),
              ("z", MB[2], MB[3], "58 (z18~76, 뒤판 z16.5~76.5 안)", 0), ("z", LATCH_ZC - 5.25, LATCH_ZC + 5.25, "래치 본체 파일럿 10.5", 1)]
    for side in "LR":
        out.add("JOIN-DT-%sS" % side, "뒷바 결합 도브테일 블록 %s — 스피커 파트 쪽(암) + 래치 걸이 받침 (뒷면)" % side,
                "rear-bar dovetail block %s, speaker side (female, back face)" % side, "print", G_JOIN, fem if side == "L" else mx(fem),
                COLORS["printed_body"], PETG,
                source=SRC_L1 + " joint_eva (3 mm EVA 틈, 도브테일·래치는 3 mm 틈 기준) ; " + SRC_S + " dovetail_L_speaker (도브테일 2개 + 래치 걸이 "
                                "받침, 8호 13 mm, M3×10)",
                note=why + ". 추정: 스피커 뒤판(y435.5~447)에 8호 13 mm ×4 (자리 Ø9 깊이 11 → PETG 3 + 합판 10, 뒤판 11.5 안에서 멈춤 - 밀폐), "
                           "옆판 뒤 끝면(x185.5~197)에는 박지 않음; 래치 걸이 M3×10 자가 탭 ×2 (파일럿 Ø2.75 깊이 10)",
                print_name="도브테일블록_%s_스피커쪽" % side, R=R_NONE,
                print_note="밑면(z10)을 베드에 세워 출력: 도브테일 홈이 수직(서포트 없음), 나사·파일럿 구멍은 눈물방울. 벽 4줄 + 채움 25 %. "
                           "EVA 띠는 이음 틈(x197~200)에만 붙이고 블록에는 붙이지 않음",
                dims=fdims if side == "L" else mdims(fdims))
        out.add("JOIN-DT-%sC" % side, "뒷바 결합 도브테일 블록 %s — 가운데 유닛 쪽(수) + 래치 본체 받침 (뒷면)" % side,
                "rear-bar dovetail block %s, centre side (male, back face)" % side, "print", G_JOIN, male if side == "L" else mx(male),
                COLORS["printed_body"], PETG,
                source=SRC_L1 + " joint_eva ; " + SRC_S + " dovetail_L_centre (수 도브테일 + 래치 본체 받침, 8호 13 mm, M3×10)",
                note=why + ". 추정: 가운데 유닛 뒤판(y435.5~447, z16.5~76.5)에 8호 13 mm ×4 (x208/232 z24/67.5 - 래치 본체 판 z34.4~59.6을 피함); "
                           "래치 본체 M3×10 자가 탭 ×2 (파일럿 Ø2.75 깊이 10)",
                print_name="도브테일블록_%s_가운데쪽" % side, R=R_NONE,
                print_note="밑면(z18)을 베드에 세워 출력: 수 도브테일이 수직(서포트 없음). 벽 4줄 + 채움 25 %",
                dims=mdims_ if side == "L" else mdims(mdims_))

    body, catch = latch_left()
    for side in "LR":
        m = union([body, catch])
        if side == "R":
            m = mx(m)
        out.add("JOIN-LATCH-%s" % side, "토글 래치 L64 (매미고리 1-20, SUS304) — 본체 + 걸이 %s" % side,
                "toggle latch L64 (body + catch) " + side, "bought", G_JOIN, m, COLORS["stainless"], "SUS304",
                source=SRC_S + " latch (잠근 길이 54, 본체 43.3×25.2×10 2-Ø4 간격 10.5, 걸이 23.3×11.8×8.8 2-Ø4 간격 12.5)",
                note="추정: 상자 여러 개로 단순화; v3 모양을 뒷면 도브테일 블록 면 y%.0f, z중심 %.0f로 옮김 (본체 x%.0f~%.0f 가운데 쪽, 걸이 x%.0f~%.1f 스피커 쪽%s); "
                     "잠근 래치가 뒤로 y%.0f까지 나옴"
                     % (LATCH_Y, LATCH_ZC, JX_C + 1, JX_C + 27, JX_C - 27, JX_C - 15.2, "" if side == "L" else ", R은 x611 대칭", LATCH_Y + 10.0))


# ------------------------------------------------------------------ v4 anti-vibration bracket for L1

BRK_SEAT_X = {"L": (-11.80, -4.88), "R": (1226.88, 1233.80)}   # cheek M3 seats (keyaction_parts.cheek_features)
BRK_CABLE_NOTCH_L = (-13.0, -3.7, 2.9, 8.0)                    # headphone cables W701/W702 exit x-12.6..-4.1 z3..7.5
BRK_Z = 12.0
BRK_LEG_Z0 = 7.6            # leg ends at the grommet-pocket floor: nothing hangs on the 1.6 web, the headphone cables pass under it
BRK_LEG = (212.5, 215.5, 217.1, 218.0)                         # leg front, web front, web back, leg back (y)
BRK_BAR = (-3.2, 22.0, 30.0)                                   # bar x1 (x0 = leg x0), z0, z1: crosses the trough over the cables
BRK_PAD = (-4.5, 7.5, 246.0, 252.0, 18.5, 30.0)                # screw pad on the speaker front strip
BRK_SCREW = (2.0, 23.0)                                        # (x, z) 8-ho 13 mm countersunk along +y into the strip


def bracket(F, out):
    """printed bracket: vertical leg on the cheek rear face (grommets at z12, as v4) + a bar at z22..30 across the open trough
    (cables pass below) + a pad on the speaker front strip at y252 with one countersunk 8-ho 13 mm screw (+y)."""
    cheeks = F["cheeks"]
    YF, YW0, YW1, YB = BRK_LEG
    G_FL, G_WAIST, G_BORE, G_LEN = 6.0, 4.0, 3.2, 8.6
    POCKET, WEB_HOLE = 6.5, 4.2
    cx0, cx1 = cheeks["left"]["x"]
    lx0, lx1 = cx0 + 0.5, cx1 - 0.5
    holes = sorted(BRK_SEAT_X["L"])
    bx1, bz0, bz1 = BRK_BAR
    px0, px1, py0, py1, pz0, pz1 = BRK_PAD
    solid = union([box(lx0, lx1, YF, YB, BRK_LEG_Z0, bz1), box(lx0, bx1, YF, Y_TR[1], bz0, bz1), box(px0, px1, py0, py1, pz0, pz1),
                   prism_x([(YB - 0.01, bz0 - 3.0), (YB + 3.0, bz0 + 0.01), (YB - 0.01, bz0 + 0.01)], lx0, lx1)])   # 3 fillet
    cuts = []
    opened = []
    r = POCKET / 2.0
    for i, hxc in enumerate(holes):
        wl, wr = (hxc - r) - lx0, lx1 - (hxc + r)
        ext = []
        if wl < 0.8:
            ext.append(lx0 - 2.0)
            opened.append("x%.2f -x" % hxc)
        if wr < 0.8:
            ext.append(lx1 + 2.0)
            opened.append("x%.2f +x" % hxc)
        if i + 1 < len(holes) and (holes[i + 1] - r) - (hxc + r) < 0.8:
            ext.append(holes[i + 1])
            opened.append("x%.2f↔x%.2f 이어짐" % (hxc, holes[i + 1]))
        for (ya, yb) in ((YF - 0.01, YW0), (YW1, YB + 0.01)):
            if ext:
                for e in ext:
                    cuts.append(slot_hole("y", (hxc, BRK_Z), (e, BRK_Z), ya, yb, POCKET, apex=(0, -1)))
            else:
                cuts.append(hole("y", hxc, BRK_Z, ya, yb, POCKET, apex=(0, -1)))
        cuts.append(hole("y", hxc, BRK_Z, YW0 - 0.01, YW1 + 0.01, WEB_HOLE, apex=(0, -1)))
    sx, sz = BRK_SCREW
    cuts.append(csk_y(sx, sz, py0, py1 + 0.01, apex=(0, -1)))          # horizontal in the print: teardrop, apex world -z = up
    brkR = mx(diff(solid, cuts))
    nx0, nx1, nz0, nz1 = BRK_CABLE_NOTCH_L
    brkL = diff(solid, cuts)            # the leg now ends at z7.4, so the W701/W702 exit (z3..7.5) is free without a notch
    pitch = holes[-1] - holes[0]
    for side in "LR":
        brk = brkL if side == "L" else brkR
        dims = [("x", lx0, lx1, "세움 다리 %.2f (볼 안쪽 0.5씩)" % (lx1 - lx0), 0),
                ("x", holes[0], holes[-1], "볼트 간격 %.2f (볼 너트 자리)" % pitch, 1),
                ("x", lx0, px1, "전체 %.1f (나사 판 x%.1f까지)" % (px1 - lx0, px1), 2),
                ("x", lx0, sx, "나사 x%.1f" % sx, 3),
                ("y", YF, YB, "세움 다리 5.5 (볼과 0.5 띄움)", 0), ("y", YW0, YW1, "그로밋 웹 1.6", 1),
                ("y", YF, Y_TR[1], "통로를 건넘 y212.5~252", 2), ("y", py0, py1, "나사 판 6", 3),
                ("z", BRK_LEG_Z0, bz1, "전체 z7.6~30", 0), ("z", BRK_LEG_Z0, BRK_Z, "그로밋 z12", 1), ("z", bz0, bz1, "건넘 막대 z22~30 (선 위)", 2),
                ("z", pz0, pz1, "나사 판 z18.5~30", 3)]
        if side == "R":
            dims = mdims(dims)
        out.add("BRK-%s" % side, "방진 브래킷 %s (끝 부속 볼 ↔ 스피커 파트, L1)" % side, "anti-vibration bracket %s (L1)" % side,
                "print", G_BR, brk, COLORS["printed_body"], "PETG 회색",
                source=SRC_L1 + " bracket (볼 뒷면 y212 z12 M3 자리 x−11.80/−4.88 · 1226.88/1233.80 ↔ 스피커 앞 아래 y252, 그로밋은 볼 쪽, "
                                "세움 다리는 z7.4부터라 헤드폰 선 x−12.6~−4.1 z3~7.5가 밑으로 지나감, EL 리드 x13.5~22.5 피함); keyaction_parts.py cheek_features; "
                       + SRC_F + " bracket.proposal_v4 (그로밋 웹 1.6)",
                note="추정: L1용 새 모양 - 세움 다리 x%.2f~%.2f y212.5~218 z7.6~30 (볼 뒷면에서 0.5 띄워 그로밋만 닿게, 다리 밑은 비워 선이 지나감; 그로밋 자리는 v4와 같음: "
                     "웹 1.6에 허리 구멍 Ø4.2, 양쪽 플랜지 자리 Ø6.5 - %s), 건넘 막대 x%.1f~%.1f y212.5~252 z22~30 (통로 바닥 선 z≤22 위로, z72 아래), "
                     "나사 판 x%.1f~%.1f y246~252 z18.5~30을 스피커 앞 아래 띠(오꾸메 z16.5~29.11) 앞면에 대고 직결피스 8호 13 mm 접시머리 1개 "
                     "(x%.1f z%.0f, +y; 판 6 + 합판 7, 띠 안에서 멈춤). 막대는 나사 머리 앞을 비움(x≤%.1f). "
                     "%s는 EL 리드 노치(x13.5~22.5)와 %.1f, R은 ER 리드(x1206.1~1212.5)와 %.1f 떨어짐. %s"
                     % ((lx0, lx1, ", ".join(opened), lx0, bx1, px0, px1, sx, sz, bx1, "L", 13.5 - px1, mxv(px1) - 1212.5,
                         "헤드폰 선 두 가닥(x−12.6~−4.1 z3~7.5)은 세움 다리 밑으로 지나감") if side == "L" else
                        (mxv(lx1), mxv(lx0), ", ".join(re.sub(r"x(-?\d+\.\d+)", lambda m_: "x%.2f" % mxv(float(m_.group(1))), o) for o in opened),
                         mxv(bx1), mxv(lx0), mxv(px1), mxv(px0), mxv(sx), sz, mxv(bx1), "L",
                         13.5 - px1, mxv(px1) - 1212.5, "")),
                print_name="방진브래킷_" + side, R=R_FLIP,
                print_note="윗면(z30, 다리·막대·나사 판이 같은 면)을 베드에, 세움 다리가 위로. 그로밋·나사 구멍은 눈물방울, 접시 자리는 45° 원뿔(서포트 없음)%s. "
                           "그로밋을 웹에 끼우고 M3×16 볼트 ×2를 볼의 눌러 넣은 M3 너트에; 나사 판은 접시머리 8호 13 mm로 스피커 앞 아래 띠에"
                           % "",
                dims=dims)
        seats = sorted(BRK_SEAT_X[side])
        for i, hxc in enumerate(seats):
            gm = union([cyl_y(hxc, BRK_Z, 212.0, YW0, G_FL), cyl_y(hxc, BRK_Z, YW0, YW1, G_WAIST), cyl_y(hxc, BRK_Z, YW1, 212.0 + G_LEN, G_FL)])
            gm = diff(gm, [cyl_y(hxc, BRK_Z, 211.99, 212.0 + G_LEN + 0.01, G_BORE)])
            out.add("BRK-%s-GROM%d" % (side, i + 1), "실리콘 방진 그로밋 M3 (L42, 1.6 판용 홈)", "M3 silicone anti-vibration grommet (L42)",
                    "bought", G_BR, gm, COLORS["rubber"], "실리콘", source="hardware/bom L42; " + SRC_F + " bracket.proposal_v4",
                    note="추정: 플랜지 Ø6 × 3.5 + 허리 Ø4 × 1.6 + 플랜지 Ø6 × 3.5 = 길이 8.6, 구멍 Ø3.2; 앞 플랜지가 볼 뒷면 y212에 닿음")
            yb0 = 212.0 + G_LEN
            bolt = union([cyl_y(hxc, BRK_Z, yb0 - 16.0, yb0, 3.0), cyl_y(hxc, BRK_Z, yb0, yb0 + 1.65, 5.7)])
            out.add("BRK-%s-BOLT%d" % (side, i + 1), "M3×16 둥근머리 볼트 ISO 7380 (방진 브래킷)", "M3x16 button head bolt (bracket)",
                    "bought", G_BR, bolt, COLORS["stainless"], "SUS",
                    source=SRC_F + " bracket.proposal_v4 hardware; 길이 16 = 그로밋 8.6 + 볼 속 7.4",
                    note="추정: 머리 Ø5.7 × 1.65 (ISO 7380)")
            rc = 5.5 / math.sqrt(3.0)
            nut = diff(prism_y(hex_pts(hxc, BRK_Z, rc), 205.05, 207.45), [cyl_y(hxc, BRK_Z, 205.0, 207.5, 2.5)])
            out.add("BRK-%s-NUT%d" % (side, i + 1), "M3 육각 너트 (볼의 너트 홈에 압입, 방진 브래킷)", "M3 hex nut in the cheek pocket",
                    "bought", G_BR, nut, COLORS["stainless"], "SUS", source=SRC_F + " bracket.proposal_v4 nut_pocket",
                    note="추정: 볼 너트 홈 천장 z15.2 (볼트 축 z12 + 꼭짓점 3.175)")
        scx = sx if side == "L" else mxv(sx)
        cone = Manifold.cylinder((8.4 - 4.2) / 2.0, 8.4 / 2.0, 4.2 / 2.0, 48).rotate((-90, 0, 0)).translate((scx, py0, sz))
        scr = union([cone, cyl_y(scx, sz, py0 + (8.4 - 4.2) / 2.0 - 0.01, py0 + 13.0, 4.2)])
        out.add("BRK-%s-SCREW" % side, "직결피스 8호 13 mm 접시머리 (방진 브래킷 → 스피커 앞 아래 띠)", "8-ho 13 mm countersunk self-drilling screw",
                "bought", G_BR, scr, COLORS["stainless"], "SUS",
                source="task: 스피커 파트 앞(y252)에 8호 직결피스 1개; 물림 13 − 6 = 7 < 띠 두께 11.5 (밀폐 유지)",
                note="추정: 접시머리 Ø8.4")


def hex_pts(c1, c2, rc):
    """hexagon (corner radius rc) with flats facing +-c1 and corners at +-c2, CCW."""
    return [(c1 + rc * math.cos(math.radians(30 + 60 * k)), c2 + rc * math.sin(math.radians(30 + 60 * k))) for k in range(6)]


# ------------------------------------------------------------------ centre unit plywood (11 panels)

def cu_panels(out):
    y0, y1 = Y_RB
    z0, z1 = CU_Z
    iz0, iz1 = CU_IZ
    iy0, iy1 = CU_IY
    bl, br = X_DIV, X_LDIV
    P = [
        ("P01", "바닥 왼쪽", "bottom_L", box(CU_X[0], bl, y0, y1, z0, iz0), "%.2f×195" % (bl - CU_X[0]), "끝판·앞판·뒤판 왼쪽·칸막이 반 밑"),
        ("P02", "바닥 오른쪽", "bottom_R", box(br, CU_X[1], y0, y1, z0, iz0), "%.2f×195" % (CU_X[1] - br), "앞판·뒤판 오른쪽·끝판·낮은 칸막이 반 밑"),
        ("P03", "뚜껑 왼쪽", "lid_L", box(CU_X[0], bl, y0, y1, iz1, z1), "%.2f×195" % (bl - CU_X[0]), "들어 여는 뚜껑, 모서리 받침 자석 2"),
        ("P04", "뚜껑 오른쪽", "lid_R", box(br, CU_X[1], y0, y1, iz1, z1), "%.2f×195" % (CU_X[1] - br), "들어 여는 뚜껑, 모서리 받침 자석 2"),
        ("P05", "앞판", "front", diff(box(CU_X[0], CU_X[1], y0, y0 + T, iz0, iz1), [box(NOTCH[0], NOTCH[1], y0 - 0.01, y0 + T + 0.01, iz0 - 0.01, NOTCH[3])]),
         "822×60, 아래 모서리에 케이블 입구 홈 %.0f×%.1f (x%.0f~%.0f z%.1f~%.0f, 곧은 자름 3번)" % (NOTCH[1] - NOTCH[0], NOTCH[3] - NOTCH[2], NOTCH[0], NOTCH[1], NOTCH[2], NOTCH[3]),
         "바닥·CU 트레이 위, 뚜껑이 윗모서리에 얹힘"),
        ("P06", "뒤판 왼쪽", "back_L", box(CU_X[0], bl, y1 - T, y1, iz0, iz1), "%.2f×60" % (bl - CU_X[0]), "오른쪽 끝면 x%.2f에 I/O 판" % bl),
        ("P07", "뒤판 오른쪽", "back_R", box(br, CU_X[1], y1 - T, y1, iz0, iz1), "%.2f×60" % (CU_X[1] - br), "왼쪽 끝면 x%.2f에 I/O 판" % br),
        ("P08", "끝판 왼쪽", "end_L", box(CU_X[0], BAYS["end_L"][1], iy0, iy1, iz0, iz1), "172×60", "앞판·뒤판 사이, 바깥면 x200에 EVA 띠"),
        ("P09", "끝판 오른쪽", "end_R", box(BAYS["end_R"][0], CU_X[1], iy0, iy1, iz0, iz1), "172×60", "앞판·뒤판 사이, 바깥면 x1022에 EVA 띠"),
        ("P10", "칸막이(건반 보관함 ↔ CU 칸)", "divider", box(BAYS["divider"][0], BAYS["divider"][1], iy0, iy1, iz0, iz1), "172×60",
         "x%.2f 중심: 반은 바닥 왼쪽, 반은 CU 트레이 위" % bl),
        ("P11", "낮은 칸막이(CU 칸 ↔ 보조배터리 칸)", "low_divider", box(BAYS["low_divider"][0], BAYS["low_divider"][1], iy0, iy1, iz0,
                                                               iz0 + CU["low_divider_height"]),
         "172×%.0f" % CU["low_divider_height"], "위 20 mm 틈으로 USB 선이 넘어감"),
    ]
    for pid, ko, en, m, cut, joins in P:
        out.add("CU-PLY-%s" % pid, "가운데 유닛 " + ko, "centre unit " + en, "plywood", G_CU, m, COLORS["plywood"], PLY,
                source=SRC_L1 + " centre (x200~1022 y252~447 z5~88, 안 z16.5~76.5 y263.5~435.5, bays_inner_x, low_divider_height 40, "
                                "cable_inlet, lids); 구조는 " + SRC_C + " panels CU-%s (재단 %s)" % (pid, cut),
                note="%s; 추정: 판 짜임은 v3와 같음 (벽은 바닥 위, 뚜껑은 벽 윗모서리 위, 끝판·칸막이는 앞판·뒤판 사이)" % joins)


# ------------------------------------------------------------------ CU tray

TRAY_RIB_PITCH = 40.0


def tray_rib_positions(x0, x1, y0, y1, wall, rt, pitch=None):
    """rib centre lines: along-y ribs symmetric about the tray centre, along-x ribs at y0 + k * pitch."""
    p = TRAY_RIB_PITCH if pitch is None else pitch
    xc = (x0 + x1) / 2.0
    xs = []
    k = 0
    while True:
        d = (k + 0.5) * p
        if xc + d + rt / 2 >= x1 - wall:
            break
        xs += [xc - d, xc + d]
        k += 1
    ys = []
    y = y0 + p
    while y + rt / 2 < y1 - wall:
        ys.append(y)
        y += p
    return sorted(round(v, 3) for v in xs), ys


def tray_tabs(fe):
    """v3 A8 (left tabs moved between the PED board and the Pi) then the L1 shift."""
    out = []
    for t in fe["divider_screw_tabs"]["tabs"]:
        t = json.loads(json.dumps(t))
        if t["side"] == "left":
            if t["box"]["y"][0] < 300:
                t["box"]["y"] = [298.0, 314.0]
                t["hole_center"][1] = 306.0
            else:
                t["box"]["y"] = [318.0, 334.0]
                t["hole_center"][1] = 326.0
        for a, d in (("x", DX), ("y", DY), ("z", DZ)):
            t["box"][a] = [t["box"][a][0] + d, t["box"][a][1] + d]
        t["hole_center"] = [t["hole_center"][0] + DX, t["hole_center"][1] + DY, t["hole_center"][2] + DZ]
        out.append(t)
    return out


def _pts(at):
    return [(px + DX, py + DY) for (px, py) in at]


def cu_tray(C, out):
    Tr = next(p for p in C["printed"] if p["id"] == "PR-CU-TRAY")
    st = Tr["structure"]
    fe = {f["name"]: f for f in Tr["features"]}
    x0, x1 = TRAY_X
    y0, y1 = Y_RB
    z0, z1 = ZB, CU_IZ[0]
    zs0 = st["top_skin_z"][0] + DZ                     # 13.5
    wall = st["perimeter_wall"]
    rt = st["underside_ribs"]["t"]
    add = [box(x0, x1, y0, y1, zs0, z1),
           diff(box(x0, x1, y0, y1, z0, zs0 + 0.01), [box(x0 + wall, x1 - wall, y0 + wall, y1 - wall, z0 - 0.01, zs0 + 0.02)])]
    rxs, rys = tray_rib_positions(x0, x1, y0, y1, wall, rt)
    for rx in rxs:
        add.append(box(rx - rt / 2, rx + rt / 2, y0 + wall - 0.01, y1 - wall + 0.01, z0, zs0 + 0.01))
    for ry in rys:
        add.append(box(x0 + wall - 0.01, x1 - wall + 0.01, ry - rt / 2, ry + rt / 2, z0, zs0 + 0.01))
    fb = fe["foot_screw_bosses"]
    fb_top = fb["z"][1] + DZ                            # 21.0
    for (px, py) in _pts(fb["at"]):
        add.append(cyl_z(px, py, z0, zs0 + 0.01, 22.0))
        add.append(cyl_z(px, py, z1 - 0.01, fb_top, fb["d"]))
    pi = fe["pi5_bosses"]
    pi_top = pi["z"][1] + DZ
    add += [cyl_z(px, py, z1 - 0.01, pi_top, pi["od"]) for (px, py) in _pts(pi["at"])]
    for nm in ("amp_bosses", "buck_bosses", "amp_input_jack_board_bosses"):
        f = fe[nm]
        for (px, py) in _pts(f["at"]):
            add.append(cyl_z(px, py, z1 - 0.01, f["z"][1] + DZ, f["od"]))
            add.append(cyl_z(px, py, z0, zs0 + 0.01, 9.0))
    ped = fe["ped_board_standoffs"]
    ped_top = ped["z"][1] + DZ
    pedpts = _pts(ped["screw_at"]) + _pts(ped["pin_at"])
    add += [cyl_z(px, py, z1 - 0.01, ped_top, ped["od"]) for (px, py) in pedpts]
    add += [cyl_z(px, py, ped_top - 0.01, ped_top + 2.5, 2.8) for (px, py) in _pts(ped["pin_at"])]
    tabs = tray_tabs(fe)
    add += [B(t["box"]) for t in tabs]
    fc = fe["fuse_holder_cradle"]
    fy, fz = 311.0 + DY, 40.5 + DZ
    add.append(diff(B(fc["box"], DX, DY, DZ), [cyl_x(fy, fz, fc["box"]["x"][0] + DX - 0.01, fc["box"]["x"][1] + DX + 0.01, fc["inner_d"])]))
    tray = union(add)

    cuts = []
    # front-top edge chamfer 2 under the front-panel notch (cables from the trough bend over it into the bay)
    nx0, nx1 = NOTCH[0], NOTCH[1]
    cuts.append(prism_x([(y0 - 0.01, z1 - 2.0), (y0 + 2.0, z1 + 0.01), (y0 - 0.01, z1 + 0.01)], nx0, nx1))
    cuts += [cyl_z(px, py, z0 - 0.01, fb_top - 1.0, fb["pilot"]) for (px, py) in _pts(fb["at"])]
    cuts += [cyl_z(px, py, pi_top - pi["tap_depth"], pi_top + 0.01, pi["tap"]) for (px, py) in _pts(pi["at"])]
    for nm in ("amp_bosses", "buck_bosses", "amp_input_jack_board_bosses"):
        f = fe[nm]
        dep = f.get("pilot_depth", 10.0)
        cuts += [cyl_z(px, py, f["z"][1] + DZ - dep, f["z"][1] + DZ + 0.01, f["pilot"]) for (px, py) in _pts(f["at"])]
    cuts += [cyl_z(px, py, ped_top - 5.0, ped_top + 0.01, 2.5) for (px, py) in _pts(ped["screw_at"])]
    for t in tabs:
        hx, hy, hz = t["hole_center"]
        cuts.append(hole("x", hy, hz, t["box"]["x"][0] - 0.01, t["box"]["x"][1] + 0.01, 4.5, apex=(0, 1)))
    an = fe["cable_tie_anchors"]
    sw, slen = an["slot"][1], an["slot"][0]
    anchors = [(ax, ay + (280.0 - 243.0 - DY)) for (ax, ay) in _pts(an["at"])]     # y280: 16.5 behind the front panel
    for (ax, ay) in anchors:
        for s in (-1, 1):
            cuts.append(box(ax + s * 2.6 - sw / 2, ax + s * 2.6 + sw / 2, ay - slen / 2, ay + slen / 2, zs0 - 0.01, z1 + 0.01))
    for tx in (642.0 + DX, 668.0 + DX):
        for (ya, yb) in ((301.5 + DY, 303.1 + DY), (318.9 + DY, 320.5 + DY)):
            cuts.append(box(tx - 1.4, tx + 1.4, ya, yb, zs0 - 0.01, z1 + 0.01))
    tray = diff(tray, cuts)

    pic = _pts(pi["at"])
    out.add("CU-TRAY", "CU 트레이", "CU tray (printed bay floor)", "print", G_CUP, tray, COLORS["printed_body"], "PETG 회색/검정",
            source=SRC_L1 + " centre.cu_tray (x556.05~756.05 z5~16.5, 이전과 같은 구조, 위치만 옮김) + shift_from_v3 (dx +36.05, dy +37, dz −17); "
                   + SRC_C + " PR-CU-TRAY (윗판 3.0, 테 4.0, 밑 리브 2.0 피치 40, 부품 보스 = 재배치 좌표)",
            note="추정: v3 트레이를 L1 칸으로 옮김 - 모든 보스·탭·받침·고무발 보스 (+36.05, +37, −17); v3 트레이 관통 케이블 입구(x540~700)는 "
                 "없앰(L1은 앞판 홈 x583~733 z16.5~34로 선이 들어옴) → 그 앞 윗모서리를 2 mm 모따기(선이 넘어가는 자리); "
                 "케이블 타이 고리는 y280 (앞판 안면에서 16.5, x%s); 리브 x%s·y%s; 탭 A8 (왼쪽 탭 y335~351·355~371 = PED 기판과 Pi 사이)"
                 % ("/".join("%.2f" % a[0] for a in anchors), "/".join("%.2f" % v for v in rxs), "/".join("%.0f" % v for v in rys)),
            print_name="CU트레이", R=R_NONE,
            print_note="밑(리브 쪽)을 베드에, 보스가 위. 윗판(z13.5~16.5)은 리브 칸 40×40을 브리지로 덮음 - 두꺼운 브리지 켬, "
                       "브리지 유량 0.9~0.95, 속도 20~30 mm/s, 팬 100 %. 처지면 body.py TRAY_RIB_PITCH를 줄여 다시 생성. "
                       "199.6×195 (220 베드 OK). 칸막이 탭 구멍은 눈물방울. 13 mm 피스 ×4로 칸막이·낮은 칸막이 옆면에",
            dims=[("x", x0, x1, "199.6 (합판 틈 0.2씩)", 0), ("x", pic[0][0], pic[1][0], "Pi 보스 58", 1),
                  ("x", nx0, nx1, "앞 모따기 = 앞판 홈 150", 2), ("x", x0, TRAY_FEET[0][0], "고무발 보스 x656.05", 3),
                  ("y", y0, y1, "195", 0), ("y", TRAY_FEET[0][1], TRAY_FEET[1][1], "고무발 보스 80", 1), ("y", y0, 280.0, "타이 고리 y280", 2),
                  ("z", z0, z1, "11.5 (z5~16.5)", 0), ("z", zs0, z1, "윗판 3.0", 1), ("z", z1, pi_top, "Pi 보스 6", 2),
                  ("z", z0, fb_top, "고무발 보스 16", 3)])


# ------------------------------------------------------------------ CU lid

LID_SUP = 18.0, 12.0     # corner support size (x, y) / height


def lid_support_boxes():
    """12 corner supports (tag, x0, x1, y0, y1, magnet). KS bay: all four in the side bay (the spare-key stack z16.5..75.3
    fills the key bay up to 1.2 under the lid)."""
    s = LID_SUP[0]
    iy0, iy1 = CU_IY
    ks_wall_x1 = BAYS["key_storage"][0] + 201.3 + 1.2   # 414.0 insert wall +x face
    bays = [("KS", ks_wall_x1, BAYS["key_storage"][1]), ("CU", BAYS["cu"][0], BAYS["cu"][1]), ("PB", BAYS["power_bank"][0], BAYS["power_bank"][1])]
    out = []
    for tag, x0, x1 in bays:
        out += [(tag + "-FL", x0, x0 + s, iy0, iy0 + s, True), (tag + "-FR", x1 - s, x1, iy0, iy0 + s, False),
                (tag + "-RL", x0, x0 + s, iy1 - s, iy1, False), (tag + "-RR", x1 - s, x1, iy1 - s, iy1, True)]
    return out


LID_SCREW_XY = [(570.8, 272.5), (741.3, 272.5)]           # A6 lid front screws (centres of CU-FL / CU-FR)
LID_SCREW_CB = (6.5, 7.5)                                  # counterbore dia / depth from the top (4.0 left under the head)
POCKET_RAMP_Y0_SPEC = TS.POCKET["ramp_front_y"]            # 388.34 (spec A4)
POCKET_RAMP_Y0 = 383.5                                     # 추정: moved forward so the 6 mm leg underside clears it by about 0.4
POCKET_BLOCK = (646.05, 666.0, 384.0, 402.0)               # A4 solid block under the pocket (x from 646.05 = slot edge)
HOLE_FRAME = (589.0, 617.0, 289.0, 301.0)                  # 추정: solid walls round the ribbon hole (under the skin)
RCLIP_PAD = (589.0, 619.5, 314.0, 326.0)                   # 추정: flat seat pad under the lid for the ribbon clip
RCLIP_PIN_DX = 12.0                                        # clip pins +-12 (between the vent slots, clear of the ribbon)
RCLIP_LID_X = 604.05                                       # 추정: clip centre (pins at x592.05 / 616.05 = webs between slots)
RCLIP_SEAT_Y = TS.RCLIP_SEAT_LID[1]                        # A8 seat y320
SLOT_Y0 = 302.0                                            # A1 slot front end y297 -> y301 in the spec; y302 keeps its 3 mm web (hinge feet reach y299)
SLOT_FILL = ((652.05, 660.05), 384.0)                      # A1 these two slots end at y384 (leg pocket)


def knuckle_poly():
    """A2 cheek side profile (y, z): R5.5 round the axis + trapezoid (z96: y284.5..295.5, z88: y281..299), base 0.01 into
    the lid top."""
    r = TS.KNUCKLE_R
    n = 72
    circ = CrossSection([[(TS.AX_Y + r * math.cos(2 * math.pi * i / n), TS.AX_Z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]],
                        FillRule.NonZero)
    trap = CrossSection([[(TS.KN_Z88[0], CU_Z[1] - 0.01), (TS.KN_Z88[1], CU_Z[1] - 0.01), (TS.KN_Z96[1], TS.AX_Z), (TS.KN_Z96[0], TS.AX_Z)]],
                        FillRule.NonZero)
    polys = (circ + trap).to_polygons()
    assert len(polys) == 1
    return [tuple(p) for p in polys[0]]


def ribbon_hole_poly(y0, y1, z0, z1, r=1.0, n=8):
    """(y, z) section of a through hole y0..y1 whose four x-parallel edges (top and bottom faces) are rounded R r."""
    def arc(cy, cz, a0, a1):
        return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
                for i in range(n + 1)]
    e = 0.05
    p = [(y0 - r, z0 - e), (y1 + r, z0 - e), (y1 + r, z0)]
    p += arc(y1 + r, z0 + r, 270, 180)[1:]          # bottom back edge
    p += arc(y1 + r, z1 - r, 180, 90)
    p += [(y1 + r, z1 + e), (y0 - r, z1 + e), (y0 - r, z1)]
    p += arc(y0 - r, z1 - r, 90, 0)[1:]             # top front edge
    p += arc(y0 - r, z0 + r, 0, -90)
    return p


def pocket_poly(ramp_y0):
    """A4 leg pocket section (y, z): 30 deg front ramp from (ramp_y0, z88) down to the floor z84.5, floor to the vertical back
    wall y397.4, C0.5 on the back wall's top edge; open above z88."""
    zt = CU_Z[1]
    zb = TS.POCKET["bottom_z"]
    yb = TS.POCKET["back_wall_y"]
    t30 = math.tan(math.radians(30.0))
    y_floor = ramp_y0 + (zt - zb) / t30
    return [(ramp_y0 - 0.3 / t30, zt + 0.3), (ramp_y0, zt), (y_floor, zb), (yb, zb), (yb, zt - 0.5), (yb + 0.5, zt), (yb + 0.5, zt + 0.3)]


def cu_lid(C, out):
    """CU 뚜껑 v2 (CAD_SPEC A): the v3-derived printed lid + R31 hinge blocks, ribbon hole, leg pocket, fold feet, front screws."""
    L = next(p for p in C["printed"] if p["id"] == "PR-CU-LID")
    st = L["structure"]
    x0, x1 = L["box"]["x"][0] + DX, L["box"]["x"][1] + DX        # 556.55 .. 755.55
    y0, y1 = Y_RB
    z0, z1 = CU_IZ[1], CU_Z[1]                                     # 76.5 .. 88
    zs0 = st["top_skin_z"][0] + DZ_TOP                             # 85.5
    wall = st["perimeter_wall"]
    rt = st["underside_ribs"]["t"]
    add = [box(x0, x1, y0, y1, zs0, z1),
           diff(box(x0, x1, y0, y1, z0, zs0 + 0.01), [box(x0 + wall, x1 - wall, y0 + wall, y1 - wall, z0 - 0.01, zs0 + 0.02)])]
    rx_ = [v + DX for v in (564.0, 604.0, 644.0, 684.0)]
    ry_ = [v + DY for v in (255.0, 295.0, 335.0, 375.0)]
    for rx in rx_:
        add.append(box(rx - rt / 2, rx + rt / 2, y0 + wall - 0.01, y1 - wall + 0.01, z0, zs0 + 0.01))
    for ry in ry_:
        add.append(box(x0 + wall - 0.01, x1 - wall + 0.01, ry - rt / 2, ry + rt / 2, z0, zs0 + 0.01))
    for (tag, a0, a1, b0, b1, mag) in lid_support_boxes():
        if tag.startswith("CU"):
            add.append(box(max(a0, x0), min(a1, x1), b0, b1, z0, zs0 + 0.01))
    # solid under the new features (all down to z76.5 = the bed side, no floating undersides)
    for s in ("left", "right"):
        h = TS.HINGE[s]
        add.append(box(h["x"][0], h["x"][1], 278.0, 300.0, z0, zs0 + 0.01))          # A2 under the hinge block
    add.append(box(HOLE_FRAME[0], HOLE_FRAME[1], HOLE_FRAME[2], HOLE_FRAME[3], z0, zs0 + 0.01))
    add.append(box(POCKET_BLOCK[0], POCKET_BLOCK[1], POCKET_BLOCK[2], POCKET_BLOCK[3], z0, zs0 + 0.01))
    add.append(box(RCLIP_PAD[0], RCLIP_PAD[1], RCLIP_PAD[2], RCLIP_PAD[3], z0, zs0 + 0.01))
    # on top: hinge cheeks (far / near), fold feet
    kp = knuckle_poly()
    for s in ("left", "right"):
        h = TS.HINGE[s]
        add += [prism_x(kp, h["far"][0], h["far"][1]), prism_x(kp, h["near"][0], h["near"][1])]
    for (fx0, fx1, fy0, fy1) in TS.FOLD_FEET:
        add.append(box(fx0, fx1, fy0, fy1, z1 - 0.01, z1 + 8.0))
    lid = union(add)

    vs = next(f for f in L["features"] if f["name"] == "vent_slots")
    sw = vs["slot"][0]
    xf = vs["x_first"] + DX
    yb_ = vs["y"][1] + DY                                          # 397
    cuts = []
    xs_slots = [xf + i * vs["pitch_x"] for i in range(vs["count"])]
    for xc in xs_slots:
        ye = SLOT_FILL[1] if any(abs(xc - v) < 0.01 for v in SLOT_FILL[0]) else yb_
        cuts.append(box(xc - sw / 2, xc + sw / 2, SLOT_Y0, ye, z0 - 0.01, z1 + 0.01))
    cuts.append(prism_x(ribbon_hole_poly(TS.HOLE_Y[0], TS.HOLE_Y[1], z0, z1), TS.HOLE_X[0], TS.HOLE_X[1]))
    for (hx, hy) in LID_SCREW_XY:
        cuts += [cyl_z(hx, hy, z0 - 0.01, z1 + 0.01, 3.4), cyl_z(hx, hy, z1 - LID_SCREW_CB[1], z1 + 0.01, LID_SCREW_CB[0])]
    cuts.append(prism_x(pocket_poly(POCKET_RAMP_Y0), TS.POCKET["x"][0], TS.POCKET["x"][1]))
    for dxp in (-RCLIP_PIN_DX, RCLIP_PIN_DX):
        cuts.append(cyl_z(RCLIP_LID_X + dxp, RCLIP_SEAT_Y, z0 - 0.01, z0 + 5.0, 3.1))
    for s in ("left", "right"):
        h = TS.HINGE[s]
        cuts.append(hole("x", TS.AX_Y, TS.AX_Z, h["near"][0] - 0.01, h["near"][1] + 0.01, TS.EAR_HOLE, apex=(0, 1)))
        cuts.append(hole("x", TS.AX_Y, TS.AX_Z, h["far"][0] - 0.01, h["far"][1] + 0.01, 2.5, apex=(0, 1)))
    lid = diff(lid, cuts)
    hl, hr = TS.HINGE["left"], TS.HINGE["right"]
    out.add("CU-LID", "CU 뚜껑 v2 (화면 경첩·다리 주머니, 출력)", "CU lid v2 (printed, touchscreen hinges + leg pocket)", "print", G_CUP, lid,
            COLORS["printed_body"], "PETG",
            source=SRC_L1 + " centre.lids (CU 뚜껑은 출력, z76.5~88); " + SRC_C + " PR-CU-LID (윗판 2.5, 테 3.0, 리브 2.0 피치 40, "
                   "통풍 슬롯 4 폭 피치 8); " + TS.SRC_SPEC + " A1~A9 (R31, D22·D23·D24) + " + TS.SRC_NUM + " hinge / hole / leg.pocket / fold_feet",
            note="추정: v3 뚜껑을 x+36.05, y+37, z−34로 옮긴 틀(x%.2f~%.2f, 틈 0.5씩, 리브 x%s · y%s) 위에 R31 기능을 더함; "
                 "추정: 다리 주머니 앞 경사 시작을 사양 y%.2f → y%.1f로 당김 - 사양대로면 사용 상태 다리(두께 6, 20.5°)의 밑면이 "
                 "y384.5~388.3에서 뚜껑 윗면을 최대 약 1.4 mm 파고듦(경사 30°·바닥 z84.5·뒷벽 y397.4는 그대로, 다리 밑면과 틈 약 0.19); "
                 "추정: 주머니 밑 덩어리·경첩 밑 채움·리본 구멍 둘레 벽(x589~617 y289~301)·클립 자리 판(x589~619.5 y314~326)은 모두 "
                 "z76.5(베드 쪽)까지 채움 - 사양의 'z80까지'는 리브 면을 베드에 둘 때 떠 있는 밑면이 되어 서포트가 필요함; "
                 "추정: 리본 클립 자리는 판 밑 막힌 구멍 Ø3.1 깊이 5 두 개(x%.2f·%.2f, y%.0f - 슬롯 사이 살), 클립 핀 Ø3.0을 끼움; "
                 "추정: 먼 볼 Ø2.5 × 8 = 볼 폭 8이라 관통; 앞 나사 자리파기 Ø6.5 × 7.5는 CU-FL·CU-FR 위 받침 면(18×18)에 냄"
                 % (x0, x1, "/".join("%.2f" % v for v in rx_), "/".join("%.0f" % v for v in ry_), POCKET_RAMP_Y0_SPEC, POCKET_RAMP_Y0,
                    RCLIP_LID_X - RCLIP_PIN_DX, RCLIP_LID_X + RCLIP_PIN_DX, RCLIP_SEAT_Y),
            print_name="CU뚜껑_v2", R=R_NONE,
            print_note="리브 면(z76.5)을 베드에 두고 출력(기존 방법 h는 윗면의 경첩 받침·받침 발 때문에 못 씀). 윗판(z85.5~88)은 리브 칸 "
                       "40×40을 브리지로 덮음 - 브리지 속도를 낮춤(20~30 mm/s, 팬 100 %). 경첩 볼의 x 방향 구멍(Ø3.3 관통, Ø2.5 × 8)은 "
                       "물방울(꼭짓점 위)로 뽑고 드릴 Ø3.3 / Ø2.5로 다듬음. 서포트 없음. 약 205 g, 약 8시간. "
                       "앞 모서리 2곳을 M3×10 둥근머리로 나사형 모서리 받침(CU-FL·CU-FR)에 조임. 뒤 오른쪽 자석(CU-RR)은 그대로",
            dims=[("x", x0, x1, "199 (틈 0.5씩)", 0), ("x", xs_slots[0] - sw / 2, xs_slots[-1] + sw / 2, "통풍 슬롯 15 × 4, 피치 8", 1),
                  ("x", TS.HOLE_X[0], TS.HOLE_X[1], "리본·전원선 구멍 22 (y292~298, R1)", 2),
                  ("x", hl["x"][0], hl["x"][1], "왼쪽 경첩 받침 20.4 (먼 볼 8 + 0.2 + 귀 8 + 0.2 + 가까운 볼 4)", 3),
                  ("x", hr["x"][0], hr["x"][1], "오른쪽 경첩 받침 20.4", 4),
                  ("x", TS.POCKET["x"][0], TS.POCKET["x"][1], "다리 주머니 14", 5),
                  ("x", LID_SCREW_XY[0][0], LID_SCREW_XY[1][0], "앞 나사 Ø3.4 + 자리파기 Ø6.5×7.5, 170.5", 6),
                  ("y", y0, y1, "195", 0), ("y", SLOT_Y0, yb_, "슬롯 y302~397", 1), ("y", TS.KN_Z88[0], TS.KN_Z88[1], "경첩 볼 밑 y281~299 (축 y290)", 2),
                  ("y", POCKET_RAMP_Y0, TS.POCKET["back_wall_y"], "주머니 (30° 경사 → 바닥 z84.5 → 뒷벽 y397.4)", 3),
                  ("z", z0, z1, "11.5 (z76.5~88)", 0), ("z", zs0, z1, "윗판 2.5", 1), ("z", z1, TS.AX_Z + TS.KNUCKLE_R, "경첩 볼 (축 z96, R5.5)", 2),
                  ("z", z1, z1 + 8.0, "접이 받침 발 16×16×8", 3)])


# ------------------------------------------------------------------ I/O plate (60 tall, holes at z46.5)

IO_X = TRAY_X                                                     # 556.25 .. 755.85
IO_Y = (Y_RB[1] - T, Y_RB[1])                                     # 435.5 .. 447
IO_Z = tuple(IO["z"])                                             # 16.5 .. 76.5
IO_SKIN = 2.0
IO_TABS_Z = [(22.0, 34.0), (42.0, 54.0)]                          # right tabs stay under the low-divider top z56.5
JACK_LEDGE = (583.55, 608.55, 421.0, IO_Y[1] - IO_SKIN, IO_HZ - 2.5 - 1.6 - 8.0, IO_HZ - 2.5 - 1.6)   # top z42.4


def io_plate(C, out):
    P = next(p for p in C["printed"] if p["id"] == "PR-IO-PLATE")
    fe = {f["name"]: f for f in P["features"]}
    x0, x1 = IO_X
    y0, y1 = IO_Y
    z0, z1 = IO_Z
    ys0 = y1 - IO_SKIN                                           # 445
    fw = P["structure"]["perimeter_frame"]["w"]
    rt = P["structure"]["ribs"]["t"]
    txl = BAYS["cu"][0] + 3.0                                    # 564.8 left tab face
    txr = BAYS["cu"][1] - 3.0                                    # 747.3
    tabs = []
    for (za, zb) in IO_TABS_Z:
        tabs.append(("left", (BAYS["cu"][0], txl, y0 - 20.0, y0, za, zb)))
        tabs.append(("right", (txr, BAYS["cu"][1], y0 - 20.0, y0, za, zb)))
    add = [box(x0, x1, ys0, y1, z0, z1), box(x0, x1, y0, y1, z0, z0 + fw), box(x0, x1, y0, y1, z1 - fw, z1),
           box(x0, txl, y0, y1, z0, z1), box(txr, x1, y0, y1, z0, z1)]
    ribs_x = [v + DX for v in (540.0, 585.0, 635.0, 680.0)]
    for rx in ribs_x:
        add.append(box(rx - rt / 2, rx + rt / 2, y0, ys0 + 0.01, z0, z1))
    ribs_z = (28.0, 66.0)
    for rz in ribs_z:
        add.append(box(x0, x1, y0, ys0 + 0.01, rz - rt / 2, rz + rt / 2))
    lx0, lx1, ly0, ly1, lz0, lz1 = JACK_LEDGE
    add.append(box(lx0, lx1, ly0, ly1 + 0.01, lz0, lz1))
    for gx in (lx0 + 1.5, lx1 - 1.5):                            # gussets 14 deep (stay behind the Pi 5 edge y429)
        add.append(prism_x([(ys0 + 0.01, lz0 - 12.0), (ys0 + 0.01, lz0 + 0.01), (ys0 - 14.0, lz0 + 0.01)], gx - 0.8, gx + 0.8))
    uc = fe["usb_c_input"]
    blk = uc["pocket"]["block"]
    ub = (blk["x"][0] + DX, blk["x"][1] + DX, blk["y"][0] + DY, ys0 + 0.01, IO_HZ - 5.0, IO_HZ + 5.0)
    add.append(box(*ub))
    add += [box(*b) for (_, b) in tabs]
    plate = union(add)

    cuts = []
    pj = fe["pedal_jack_hole"]
    cuts.append(cyl_y(IO_HX["J501"], IO_HZ, ys0 - 0.01, y1 + 0.01, pj["d"]))
    ledge_pil = [(551.0 + DX, 392.0 + DY), (569.0 + DX, 402.0 + DY)]
    for (hx, hy) in ledge_pil:
        cuts.append(hole("z", hx, hy, lz1 - 7.0, lz1 + 0.01, 2.7, apex=(0, -1)))
    swf = fe["power_switch_hole"]
    w, h = swf["size_xz"]
    cuts.append(box(IO_HX["SW"] - w / 2, IO_HX["SW"] + w / 2, ys0 - 0.01, y1 + 0.01, IO_HZ - h / 2, IO_HZ + h / 2))
    cuts.append(stadium_y(IO_HX["USBC"], IO_HZ, uc["size_xz"][0], uc["size_xz"][1], ys0 - 0.01, y1 + 0.01))
    cav = uc["pocket"]["cavity"]
    cuts.append(box(cav["x"][0] + DX, cav["x"][1] + DX, ub[2] - 0.01, ys0 + 0.01, IO_HZ - 2.4, IO_HZ + 2.4))
    cp = fe["cable_pass_hole"]
    cuts.append(stadium_y(IO_HX["PASS"], IO_HZ, cp["size_xz"][0], cp["size_xz"][1], y0 - 0.01, y1 + 0.01))
    for side, b in tabs:
        cuts.append(hole("x", (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0, b[0] - 0.01, b[1] + 0.01, 4.5, apex=(-1, 0)))
    plate = diff(plate, cuts)
    out.add("CU-IOPLATE", "I/O 판", "I/O plate (printed CU-bay back wall)", "print", G_CUP, plate, COLORS["printed_body"], "PETG",
            source=SRC_L1 + " centre.io_plate (x556.05~756.05 y435.5~447 z16.5~76.5; 구멍 z46.5: 페달 잭 J501 x596.05, 스위치 KCD1 x646.05, "
                            "USB-C x696.05, 선 통과 x736.05; J501 받침은 축 z46.5 = PJ-313 축 2.5 + 기판 1.6); " + SRC_C + " PR-IO-PLATE "
                            "(바깥 판 2.0, 테 4.0, 리브 2.0, 잭 Ø6.5, 스위치 13.2×19.2, USB-C 13.5×8 + PD 트리거 포켓, 선 통과 18×11)",
            note="추정: 판 x%.2f~%.2f (틈 0.2씩), 60 높이 (뚜껑이 윗면에도 얹힘); 리브 x%s·z28/66 (구멍 z36.9~56.1 피함); "
                 "칸막이 탭 4개 z22~34·42~54 (오른쪽은 낮은 칸막이 윗면 z56.5 아래), 탭 구멍 Ø4.5 y%.1f; 잭 선반 x%.2f~%.2f y%.0f~%.0f z%.1f~%.1f "
                 "(선반 위 기판 1.6 + PJ-313 축 2.5 = z46.5), 선반 받침 삼각 2개는 14 깊이로 줄여 Pi 5 가장자리(y429) 뒤에 둠; "
                 "PD 트리거 포켓 블록 x%.2f~%.2f z41.5~51.5"
                 % (x0, x1, "/".join("%.2f" % v for v in ribs_x), y0 - 10.0, lx0, lx1, ly0, ly1, lz0, lz1, ub[0], ub[1]),
            print_name="IO판", R=R_YMAX,
            print_note="바깥면(y447)을 베드에. 스위치·잭·USB-C 구멍은 수직, 탭 구멍·선반 파일럿은 눈물방울 - 서포트 없음. "
                       "13 mm 피스 ×4로 칸막이·낮은 칸막이 뒤끝 옆면에",
            dims=[("x", x0, x1, "199.6", 0), ("x", x0, IO_HX["J501"], "페달 잭 x596.05 (Ø6.5)", 1), ("x", x0, IO_HX["SW"], "스위치 x646.05 (13.2×19.2)", 2),
                  ("x", x0, IO_HX["USBC"], "USB-C x696.05 (13.5×8)", 3), ("x", x0, IO_HX["PASS"], "선 통과 x736.05 (18×11)", 4),
                  ("y", y0, y1, "11.5", 0), ("y", ys0, y1, "바깥 판 2.0", 1), ("y", ly0, ly1, "잭 선반 24", 2),
                  ("z", z0, z1, "60", 0), ("z", z0, IO_HZ, "구멍 중심 z46.5", 1), ("z", lz0, lz1, "선반 8 (윗면 z42.4)", 2)])


# ------------------------------------------------------------------ lid corner supports + magnets

SCREW_SUP_TAGS = ("CU-FL", "CU-FR")    # R31 CAD_SPEC B: screw type (the lid front is screwed, D23)
SCREW_SUP_HOLE = (2.5, 10.0)            # centre hole dia / depth from the top

def lid_supports(C, out):
    S = next(p for p in C["printed"] if p["id"] == "PR-LID-SUP")
    pk = S["part"]["magnet_pocket"]
    sx, sy, sz = S["part"]["size"]
    top = CU_IZ[1]                                              # 76.5
    base = diff(box(-sx / 2, sx / 2, -sy / 2, sy / 2, top - sz, top), [cyl_z(0, 0, top - pk["depth"], top + 0.01, pk["d"])])
    screw_base = diff(box(-sx / 2, sx / 2, -sy / 2, sy / 2, top - sz, top), [cyl_z(0, 0, top - SCREW_SUP_HOLE[1], top + 0.01, SCREW_SUP_HOLE[0])])
    mag = cyl_z(0, 0, 0, 3.0, 8.0)
    z_sup = top - pk["depth"]                                   # 70.3
    for (tag, x0, x1, y0, y1, magnet) in lid_support_boxes():
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        ks = tag.startswith("KS")
        if tag in SCREW_SUP_TAGS:
            # R31 (CAD_SPEC B, D23): the lid front corners are screwed - screw-type support, no magnet
            out.add("CU-LIDSUP-%s" % tag, "뚜껑 모서리 받침(나사형) %s" % tag, "lid corner support, screw type " + tag, "print", G_CUP,
                    screw_base.translate((cx, cy, 0.0)), COLORS["printed_body"], "PETG",
                    source=TS.SRC_SPEC + " B (18×18×12, 자석 포켓 없음, 윗면 가운데 Ø2.5 × 10, MS 폴리머 접착, D23); 자리 " + SRC_C
                           + " PR-LID-SUP → 윗면 z76.5",
                    note="추정: Ø2.5 구멍에 M3×10 둥근머리가 직접 탭을 냄(뚜껑 4.0 + 받침 물림 6.0); 모서리 두 면(앞판 안면 y263.5, "
                         "%s)을 목공본드 대신 MS 폴리머(세메다인 슈퍼X)로 붙임 - PVA는 PETG에 잘 붙지 않음"
                         % ("칸막이 x561.8 면" if tag.endswith("FL") else "낮은 칸막이 x750.3 면"),
                    print_name="뚜껑모서리받침_나사형", R=R_NONE,
                    print_note="밑면을 베드에, Ø2.5 구멍이 위(수직). 서포트 없음. 2개 (CU-FL·CU-FR). MS 폴리머로 합판 모서리에 붙임",
                    dims=[("x", x0, x1, "18", 0), ("y", y0, y1, "18", 0), ("z", top - sz, top, "12 (z64.5~76.5)", 0),
                          ("z", top - SCREW_SUP_HOLE[1], top, "Ø2.5 깊이 10", 1)])
            continue
        out.add("CU-LIDSUP-%s" % tag, "뚜껑 모서리 받침(자석 자리) %s" % tag, "lid corner support " + tag, "print", G_CUP,
                base.translate((cx, cy, 0.0)), COLORS["printed_body"], "PETG",
                source=SRC_C + " PR-LID-SUP (18×18×12, 포켓 Ø8.2 깊이 6.2) → 윗면 z76.5 (" + SRC_L1 + " lids z76.5~88)",
                note="추정: 받침 크기 18×18×12·포켓 깊이 6.2 (spec assumed); 모서리 두 면에 목공본드%s"
                     % ("; 건반 보관함 칸은 예비 건반 2층(z16.5~75.3)이 칸을 채우므로 받침 4개를 모두 옆 칸(x414~550.3)에 둠 - "
                        "왼쪽 2개는 보관함 칸막이(출력 벽 x412.8~414) +x 면과 앞·뒤판에 붙임" if ks else ""),
                print_name="뚜껑모서리받침", R=R_NONE,
                print_note="밑면을 베드에, 자석 포켓이 위. 10개 모두 포켓, 5개(대각)에 자석 - R31로 CU 칸 앞 2개(CU-FL·CU-FR)는 나사형 받침으로 바뀜",
                dims=[("x", x0, x1, "18", 0), ("x", cx - pk["d"] / 2, cx + pk["d"] / 2, "포켓 Ø8.2", 1),
                      ("y", y0, y1, "18", 0), ("z", top - sz, top, "12 (z64.5~76.5)", 0), ("z", top - pk["depth"], top, "포켓 깊이 6.2", 1)])
        if magnet:
            out.add("CU-MAG-SUP-%s" % tag, "네오디뮴 자석 Ø8×3 N35 (L65) — 받침 포켓 바닥 %s" % tag,
                    "magnet 8x3 N35 in support " + tag, "bought", G_CUP, mag.translate((cx, cy, z_sup)), COLORS["magnet"], "N35",
                    source=SRC_C + " PR-LID-SUP magnet_method (z70.3~73.3); F12")
            out.add("CU-MAG-LID-%s" % tag, "네오디뮴 자석 Ø8×3 N35 (L65) — 뚜껑 밑면 %s" % tag,
                    "magnet 8x3 N35 on the lid underside " + tag, "bought", G_CUP, mag.translate((cx, cy, top - 3.0)), COLORS["magnet"], "N35",
                    source=SRC_C + " PR-LID-SUP magnet_method (뚜껑 밑면 z76.5에 붙여 포켓 위 z73.5~76.5로 내려옴, 틈 0.2); F12")


# ------------------------------------------------------------------ power-bank holder

def pb_holder(C, out):
    H = next(p for p in C["printed"] if p["id"] == "PR-PB-HOLDER")
    g = H["geometry"]
    sp = g["screw_pads"]
    st = g["strap"]
    hk = st["right_hook"]["box"]
    add = [B(g["base"]["box"], DX, DY, DZ), B(g["left_stop_wall"], DX, DY, DZ), B(g["front_stop_wall"], DX, DY, DZ)]
    add += [cyl_z(px, py, sp["z"][0] + DZ, sp["z"][1] + DZ, sp["d"]) for (px, py) in _pts(sp["at"])]
    add.append(box(hk["x"][0] + DX, hk["x"][1] + DX, hk["y"][0] - 2.0 + DY, hk["y"][1] + 2.0 + DY, hk["z"][0] + DZ - 0.01, hk["z"][1] + DZ))
    hold = union(add)
    cuts = [cyl_z(px, py, sp["z"][0] + DZ - 0.01, sp["z"][1] + DZ + 0.01, sp["hole"]) for (px, py) in _pts(sp["at"])]
    ls = st["left_slot"]
    lx, ly, lz = ls["center"]
    wy, wz = ls["size_yz"]
    lw = g["left_stop_wall"]["x"]
    cuts.append(box(lw[0] + DX - 0.01, lw[1] + DX + 0.01, ly + DY - wy / 2, ly + DY + wy / 2, lz + DZ - wz / 2, lz + DZ + wz / 2))
    rs = st["right_hook"]
    cuts.append(box(hk["x"][0] + DX - 0.01, hk["x"][1] + DX + 0.01, hk["y"][0] + DY, hk["y"][1] + DY, rs["slot_z"][0] + DZ, rs["slot_z"][1] + DZ))
    hold = diff(hold, cuts)
    bx_ = H["box"]
    z0 = bx_["z"][0] + DZ
    out.add("CU-PBHOLDER", "보조배터리 받침 + 끈 고리", "power-bank holder + strap hook", "print", G_CUP, hold, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-PB-HOLDER (바닥 190×100×2; 멈춤벽 왼쪽·앞; 나사 받침 Ø10×3 ×4 구멍 Ø4.5; 끈 슬롯 22×3 / 고리 슬롯 22×4) "
                           "+ " + SRC_L1 + " shift_from_v3 (+36.05, +37, −17)",
            note="추정: v3 받침을 그대로 옮김 (x%.2f~%.2f y%.1f~%.1f, 보조배터리 칸 x761.8~1010.5 안, 낮은 칸막이에서 5.25) - 보조배터리 최대 "
                 "170×85×35는 z18.5~53.5 (뚜껑 밑 z76.5 아래); 오른쪽 끈 고리 양옆 2 mm 기둥 (v3와 같음). 끈(20 mm 벨크로)은 BOM에 없음"
                 % (bx_["x"][0] + DX, bx_["x"][1] + DX, bx_["y"][0] + DY, bx_["y"][1] + DY),
            print_name="보조배터리받침", R=R_NONE,
            print_note="바닥을 베드에. 끈 슬롯은 브리지 22. 서포트 없음. 13 mm 피스 ×4로 바닥 오른쪽 합판에 (물림 10)",
            dims=[("x", bx_["x"][0] + DX, bx_["x"][1] + DX, "190", 0), ("x", 741.0 + DX, 911.0 + DX, "배터리 칸 170", 1),
                  ("y", bx_["y"][0] + DY, bx_["y"][1] + DY, "100", 0), ("y", 231.5 + DY, 316.5 + DY, "배터리 칸 85", 1),
                  ("z", z0, z0 + 2.0, "바닥 2", 0), ("z", z0, z0 + 17.0, "멈춤벽 17", 1), ("z", z0, hk["z"][1] + DZ, "끈 고리 22", 2)])


# ------------------------------------------------------------------ spare-key storage insert + small-parts box

KS_WALL_X0 = BAYS["key_storage"][0] + 201.3            # 412.8 (DESIGN 13: key bay 201.3 + insert wall 1.2 + side bay 136.3)
KS_WALL_TOP = CU_IZ[1] - 1.0                           # 75.5: 1.0 under the lid, above the 2-layer stack top z75.3


def ks_insert(C, out):
    K = next(p for p in C["printed"] if p["id"] == "PR-KS-INSERT")
    g = K["geometry"]
    gu = g["gussets"]
    dxk = KS_WALL_X0 - g["wall"]["x"][0]               # 36.0 (key bay starts at x211.5 = v3 175.5 + 36)
    y0, y1 = g["wall"]["y"][0] + DY, g["wall"]["y"][1] + DY
    z0 = CU_IZ[0]
    wl = KS_WALL_X0 + 1.2
    fz = z0 + 3.0
    add = [box(KS_WALL_X0, wl, y0, y1, z0, KS_WALL_TOP), box(wl, g["flange"]["x"][1] + dxk, y0, y1, z0, fz)]
    for gy in gu["y"]:
        add.append(prism_y([(wl - 0.01, fz - 0.01), (wl + gu["size_xz"][0], fz - 0.01), (wl - 0.01, fz + gu["size_xz"][1])],
                           gy + DY - gu["t"] / 2, gy + DY + gu["t"] / 2))
    ins = union(add)
    sh = g["screw_holes"]
    ins = diff(ins, [cyl_z(px + dxk, py + DY, z0 - 0.01, fz + 0.01, sh["d"]) for (px, py) in sh["at"]])
    out.add("CU-KSINSERT", "예비 건반 보관함 칸막이(출력)", "spare-key storage insert wall", "print", G_CUP, ins, COLORS["printed_body"], "PETG",
            source=SRC_L1 + " centre.key_storage (예비 건반 2층 58.8, 안 높이 60, 칸 201.3 + 칸막이 1.2 + 옆 칸 136.3, DESIGN 13); "
                   + SRC_C + " PR-KS-INSERT (벽 1.2, 플랜지 20×3, 삼각 보강 1.2 ×3, 4-Ø4.5)",
            note="추정: 벽 x%.1f~%.1f y%.1f~%.1f z16.5~%.1f (뚜껑 밑 1.0, 건반 2층 윗면 z75.3보다 0.2 높음), 플랜지·보강·나사 자리는 v3 spec 제안을 옮김; "
                 "옆 칸 앞·뒤 모서리 받침 2개(x414~432)가 이 벽 +x 면에 붙음" % (KS_WALL_X0, wl, y0, y1, KS_WALL_TOP),
            print_name="보관함칸막이", R=R_NONE,
            print_note="플랜지를 베드에, 벽이 서도록(171.6×21.2 바닥, 높이 59). 서포트 없음. 13 mm 피스 ×4로 바닥 왼쪽 합판에",
            dims=[("x", KS_WALL_X0, g["flange"]["x"][1] + dxk, "21.2", 0), ("x", KS_WALL_X0, wl, "벽 1.2", 1), ("y", y0, y1, "171.6 (앞뒤 0.2씩)", 0),
                  ("z", z0, KS_WALL_TOP, "59 (뚜껑 밑 1)", 0), ("z", z0, fz, "플랜지 3", 1)])


def small_box(C, out):
    Sb = next(p for p in C["printed"] if p["id"] == "PR-SMALL-BOX")
    g = Sb["geometry"]
    bx_ = Sb["box"]
    x0, x1 = bx_["x"][0] + DX, bx_["x"][1] + DX
    y0, y1 = bx_["y"][0] + DY, bx_["y"][1] + DY
    Z0 = CU_IZ[0]
    H = g["outer"][2]
    wall, floor_t, lid_t = g["wall"], g["floor"], 1.6
    zr = Z0 + H - lid_t
    body = diff(box(x0, x1, y0, y1, Z0, zr), [box(x0 + wall, x1 - wall, y0 + wall, y1 - wall, Z0 + floor_t, zr + 0.01)])
    div_t, div_top = 1.2, zr - 3.5
    iw = (x1 - x0 - 2 * wall)
    divs = [box(x0 + wall + iw * k / 3.0 - div_t / 2, x0 + wall + iw * k / 3.0 + div_t / 2, y0 + wall - 0.01, y1 - wall + 0.01,
                Z0 + floor_t - 0.01, div_top) for k in (1, 2)]
    divs.append(box(x0 + wall - 0.01, x1 - wall + 0.01, (y0 + y1) / 2 - div_t / 2, (y0 + y1) / 2 + div_t / 2, Z0 + floor_t - 0.01, div_top))
    body = union([body] + divs)
    out.add("CU-SMALLBOX", "작은 부품 통", "small-parts box", "print", G_CUP, body, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-SMALL-BOX (80×60×30, 벽 1.6, 바닥 1.2, 칸 3×2, 끼움 뚜껑 1.6 + 치마 3) + " + SRC_L1 + " shift (+36.05, +37)",
            note="추정: 옆 칸 바닥 왼쪽 합판 위 x%.2f~%.2f y%.0f~%.0f z16.5~46.5 (v3 자리를 옮김); 통 몸 28.4 + 뚜껑 1.6 = 30" % (x0, x1, y0, y1),
            print_name="작은부품통", R=R_NONE, print_note="바닥을 베드에. 서포트 없음. 밸런스 핀·캡스턴 나사·센서 자석·PET 심 보관",
            dims=[("x", x0, x1, "80", 0), ("y", y0, y1, "60", 0), ("z", Z0, zr, "몸 28.4", 0), ("z", Z0, Z0 + floor_t, "바닥 1.2", 1)])
    cl, sk_t, sk_h = 0.2, 1.2, 3.0
    lid = union([box(x0, x1, y0, y1, zr, zr + lid_t),
                 diff(box(x0 + wall + cl, x1 - wall - cl, y0 + wall + cl, y1 - wall - cl, zr - sk_h, zr + 0.01),
                      [box(x0 + wall + cl + sk_t, x1 - wall - cl - sk_t, y0 + wall + cl + sk_t, y1 - wall - cl - sk_t, zr - sk_h - 0.01, zr + 0.02)])])
    out.add("CU-SMALLBOX-LID", "작은 부품 통 뚜껑", "small-parts box lid", "print", G_CUP, lid, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-SMALL-BOX lid (끼움 1.6 + 치마 3)",
            note="추정: 치마는 통 안쪽에 끼움(틈 0.2, 두께 1.2) - 바깥 80×60 유지",
            print_name="작은부품통_뚜껑", R=R_FLIP, print_note="윗면을 베드에, 치마가 위. 서포트 없음",
            dims=[("x", x0, x1, "80", 0), ("y", y0, y1, "60", 0), ("z", zr - sk_h, zr + lid_t, "4.6 (치마 3)", 0)])


# ------------------------------------------------------------------ R31 touchscreen: cradle, leg, small parts, screws

FOLDER_TS = "07_터치스크린"
G_TS = "터치스크린"
G_TSF = "터치스크린 (접은 상태, 별도 보기)"
ALT = "altview"
EAR_R = 4.5                  # 추정: material round the ear axis (spec: R4.2 or more)
CLEVIS_U_MAX = 28.3          # 추정: clevis 45 deg chamfer stops 0.2 before the cover ledge (window 30 - 1.5)
LCLIP_LIP_W = (22.5, 23.3)   # 추정: catch lip over the stowed leg's back face (w22.5), 0.8 tall with a 45 deg lead-in
RCLIP_CR = (606.0, 15.0, 7.1)   # 추정: cradle ribbon clip centre x, u and its front face w (sits in a 0.7 recess, w7.1..10.1)
RCLIP_RECESS = 0.7
RCLIP_RECESS_UM = 2.0       # 추정: recess 2.0 longer than the clip at each u end (the ribbon steps 0.75 into it there)
RCLIP_CHANNEL = (18.0, 0.3)  # 추정: ribbon channel on the clip's seat face (width, depth)
RCLIP_PIN = (3.0, 4.0, 3.1)  # 추정: clip pins dia / length, seat hole dia
COVER_T = 2.0
COVER_LEDGE = 1.5
COVER_FIT = 0.2
COVER_PLUG = 1.5             # 추정: plug depth into the 3.0 back plate (stops 1.5 short of the ribbon zone)
COVER_TABS = [((620.0, 630.0), "top"), ((648.0, 658.0), "bottom")]   # 추정: 2 snap tabs (latches) on the long edges
SCREEN_COVER = (196.0, 128.0, 3.0)
M3_HEAD = (5.7, 1.65)        # ISO 7380 M3 button head (as the bracket bolts)
M25_HEAD = (4.5, 1.8)        # 추정: TD2 kit M2.5 screw head
M25_LEN = 4.5                # 추정: kit screw length (spec G: >= 4.5)


def _cap(p, q, d):
    return _hull2d(tear_pts(p[0], p[1], d) + tear_pts(q[0], q[1], d))


def ear_poly():
    """C8 ear side profile (u, w): from the cradle bottom wall (u-2.5..-0.3, w8..16) to the axis (u-9, w16) with R4.5 round it,
    plus the heel point = world (y283, z88) seen in the 22 deg pose (R10.63 from the axis)."""
    hu, hw = TS.inv(TS.HEEL_YZ[0], TS.HEEL_YZ[1], TS.TILT_HEEL)
    pts = [(-2.5, 8.05), (-2.5, 15.95), (-0.35, 8.05), (-0.35, 15.95), (hu, hw)] + tear_pts(TS.AX_U, TS.AX_W, 2 * EAR_R)   # 0.05 inside the wall: no coincident faces
    return _hull2d(pts), (hu, hw)


def clevis_poly():
    """C9 leg-hanger cheek profile (u, w): R3.8 round (u20, w19.5), joined to the back plate / u20 rib, 45 deg underside
    (+u = down in the print) cut at u28.3 (cover ledge)."""
    cu, cw = TS.LEG_PIVOT_UW
    r = TS.CLEVIS["R"]
    wb1 = TS.BACK_W[1]
    t = (cu + cw) + r * math.sqrt(2.0)            # 45 deg tangent line u + w = t on the +u side
    return _hull2d(tear_pts(cu, cw, 2 * r) + [(cu - r, wb1 - 0.01), (CLEVIS_U_MAX, wb1 - 0.01), (CLEVIS_U_MAX, min(t - CLEVIS_U_MAX, cw))])


def cradle_local():
    """C1..C11 in the cradle frame (x, u, w)."""
    X0, X1 = TS.CR_X
    U0, U1 = TS.CR_U
    W0, W1 = TS.CR_W
    ix0, ix1 = X0 + TS.WALL_X, X1 - TS.WALL_X                      # 561.04 .. 750.96
    iu0, iu1 = -TS.GLASS_GAP, TS.GLASS[1] + TS.GLASS_GAP           # -0.3 .. 120.54
    wb0, wb1 = TS.BACK_W
    add = [diff(box(X0, X1, U0, U1, W0, W1), [box(ix0, ix1, iu0, iu1, W0 - 0.01, wb0), box(ix0, ix1, iu0, iu1, wb1, W1 + 0.01)])]
    for ur in TS.RIB_U:
        add.append(box(ix0 - 0.01, ix1 + 0.01, ur - 1.0, ur + 1.0, wb1 - 0.01, W1))
    # hinge ears, trimmed by the z88 plane in the 22 deg pose (heel)
    ep, _h = ear_poly()
    s22, c22 = TS.rot(TS.TILT_HEEL)
    for s in ("left", "right"):
        e0, e1 = TS.HINGE[s]["ear"]
        ear = prism_x(ep, e0, e1).trim_by_plane((0.0, c22, -s22), (TS.HEEL_YZ[1] - TS.AX_Z) + TS.AX_U * c22 - TS.AX_W * s22)
        add.append(ear)
    # leg hanger (clevis) cheeks
    cp = clevis_poly()
    add += [prism_x(cp, *TS.CLEVIS["near"]), prism_x(cp, *TS.CLEVIS["far"])]
    # leg clip jaws: from the back plate, 45 deg gusset down to the top wall, catch lip 0.5 inward
    (lu0, lu1) = TS.LCLIP["u"]
    jaw = [(lu0, wb1 - 0.01), (lu0, TS.LCLIP["w"][1]), (lu1, TS.LCLIP["w"][1]), (iu1 + 0.06, TS.LCLIP["w"][1] - (iu1 + 0.06 - lu1)),
           (iu1 + 0.06, wb1 - 0.01)]
    (jl0, jl1), (jr0, jr1) = TS.LCLIP["x"]
    jl1, jr0 = 650.7, 661.3          # 추정 (verify r31): spec jaws x650.5/661.5 + lip 0.5 met the leg sides with 0 catch
    add += [prism_x(jaw, jl0, jl1), prism_x(jaw, jr0, jr1)]
    lw0, lw1 = LCLIP_LIP_W
    lip = 0.8                        # catch 0.8 from a 0.3 gap = 0.5 over the stowed leg (x651..661)
    # the catch starts 0.02 behind the stowed leg's back face (w22.5) so it hooks behind the leg without touching it
    add.append(prism_y([(jl0, lw0 - 0.01), (jl1, lw0 - 0.01), (jl1, lw0 + 0.02), (jl1 + lip, lw0 + 0.02), (jl1 + lip, lw0 + 0.3),
                        (jl1, lw1), (jl0, lw1)], lu0, lu1))
    add.append(prism_y([(jr0 - lip, lw0 + 0.02), (jr0, lw0 + 0.02), (jr0, lw0 - 0.01), (jr1, lw0 - 0.01), (jr1, lw1), (jr0, lw1),
                        (jr0 - lip, lw0 + 0.3)], lu0, lu1))
    for (px0, px1) in ((566.0, 582.0), (730.0, 746.0)):          # 추정: folded, u53..69 lands on the front fold feet (A5)
        add.append(box(px0, px1, 53.0, 69.0, wb1 - 0.01, W1))
    cr = union(add)

    ap = (0, -1)                                                    # teardrop apex: -u = up in the print (top edge on the bed)
    cuts = []
    for x in TS.LUG_X:
        for u in TS.LUG_U:
            cuts += [hole("z", x, u, wb0 - 0.01, wb1 + 0.01, 2.7, apex=ap), hole("z", x, u, wb0 + 1.5, wb1 + 0.01, 5.0, apex=ap)]
    for x in TS.STANDOFF_X:
        for u in TS.STANDOFF_U:
            cuts.append(hole("z", x, u, wb0 - 0.01, wb1 + 0.01, 7.0, apex=ap))
    wx0, wx1, wu0, wu1 = TS.WIN_UP
    lx0, lx1, lu0_, lu1_ = TS.WIN_LO
    cuts += [box(wx0, wx1, wu0, wu1, wb0 - 0.01, wb1 + 0.01), box(lx0, lx1, lu0_, lu1_ + 0.01, wb0 - 0.01, wb1 + 0.01)]
    for (tx0, tx1), side in COVER_TABS:                             # latch grooves in the window wall (front 1.2 of the plate)
        if side == "top":
            cuts.append(box(tx0 - 0.4, tx1 + 0.4, wu1 - 0.01, wu1 + 0.5, wb0 - 0.01, wb0 + 1.2))
        else:
            cuts.append(box(tx0 - 0.4, tx1 + 0.4, lu0_ - 0.5, lu0_ + 0.01, wb0 - 0.01, wb0 + 1.2))
    sx0, sx1, su0, su1, sw0, sw1 = TS.SLOT
    cuts.append(box(sx0, sx1, su0 - 0.01, su1, sw0, sw1 + 0.01))
    cx, cu, cw = RCLIP_CR
    L_, Wd, H_ = TS.RCLIP
    cuts.append(box(cx - L_ / 2 - 0.2, cx + L_ / 2 + 0.2, cu - Wd / 2 - RCLIP_RECESS_UM, cu + Wd / 2 + RCLIP_RECESS_UM, wb0 - 0.01, wb0 + RCLIP_RECESS))
    for dxp in (-RCLIP_PIN_DX, RCLIP_PIN_DX):
        cuts.append(hole("z", cx + dxp, cu, wb0 + RCLIP_RECESS - 0.01, wb1 + 0.01, RCLIP_PIN[2], apex=ap))
    for s in ("left", "right"):
        e0, e1 = TS.HINGE[s]["ear"]
        cuts.append(hole("x", TS.AX_U, TS.AX_W, e0 - 0.01, e1 + 0.01, TS.EAR_HOLE, apex=(-1, 0)))
    pu, pw = TS.LEG_PIVOT_UW
    cuts.append(hole("x", pu, pw, TS.CLEVIS["near"][0] - 0.01, TS.CLEVIS["near"][1] + 0.01, 3.3, apex=(-1, 0)))
    cuts.append(hole("x", pu, pw, TS.CLEVIS["far"][0] - 0.01, TS.CLEVIS["far"][1] + 0.01, 2.5, apex=(-1, 0)))
    return diff(cr, cuts)



def cover_local():
    """E inspection-window cover: 2 mm flange (window + 1.5, lies on the plate's back face w12.4), plug (window - 0.2, 1.5 deep),
    2 snap tabs with 0.4 bumps into the window-wall grooves."""
    wx0, wx1, wu0, wu1 = TS.WIN_UP
    lx0, lx1, lu0, lu1 = TS.WIN_LO
    wb0, wb1 = TS.BACK_W
    e, f = COVER_LEDGE, COVER_FIT
    fl = union([box(wx0 - e, wx1 + e, wu0 - e, wu1 + e, wb1, wb1 + COVER_T), box(lx0 - e, lx1 + e, lu0 - e, lu1 + e, wb1, wb1 + COVER_T)])
    plug = union([box(wx0 + f, wx1 - f, wu0 + f, wu1 - f, wb1 - COVER_PLUG, wb1 + 0.01), box(lx0 + f, lx1 - f, lu0 + f, wu0 + 1.0, wb1 - COVER_PLUG, wb1 + 0.01)])
    rel, tabs = [], []
    for (tx0, tx1), side in COVER_TABS:
        if side == "top":
            ue = wu1 - f
            rel.append(box(tx0 - 1.0, tx1 + 1.0, ue - 2.0, ue + 0.01, wb1 - COVER_PLUG - 0.01, wb1 + 0.005))
            tabs += [box(tx0, tx1, ue - 1.0, ue, wb0 + 0.2, wb1 + 0.05), box(tx0, tx1, ue - 0.01, ue + 0.4, wb0 + 0.2, wb0 + 1.0)]
        else:
            ue = lu0 + f
            rel.append(box(tx0 - 1.0, tx1 + 1.0, ue - 0.01, ue + 2.0, wb1 - COVER_PLUG - 0.01, wb1 + 0.005))
            tabs += [box(tx0, tx1, ue, ue + 1.0, wb0 + 0.2, wb1 + 0.05), box(tx0, tx1, ue - 0.4, ue + 0.01, wb0 + 0.2, wb0 + 1.0)]
    return union([fl, diff(plug, rel)] + tabs)


def rclip_canon():
    """E ribbon clip 30 x 12 x 3 (canonical: seat face z3 up): ribbon channel on the seat face, 2 pins into the seat holes."""
    L_, Wd, H_ = TS.RCLIP
    cw_, cd = RCLIP_CHANNEL
    plate = diff(box(-L_ / 2, L_ / 2, -Wd / 2, Wd / 2, 0.0, H_), [box(-cw_ / 2, cw_ / 2, -Wd / 2 - 0.01, Wd / 2 + 0.01, H_ - cd, H_ + 0.01)])
    return union([plate] + [cyl_z(dxp, 0.0, H_ - 0.01, H_ + RCLIP_PIN[1], RCLIP_PIN[0]) for dxp in (-RCLIP_PIN_DX, RCLIP_PIN_DX)])


def m3_button_x(yc, zc, x_face, length, toward):
    """ISO 7380 M3 button head bolt along x: head outside x_face, shank `length` toward +1 / -1."""
    hd, hh = M3_HEAD
    if toward > 0:
        return union([cyl_x(yc, zc, x_face - hh, x_face, hd), cyl_x(yc, zc, x_face, x_face + length, 3.0)])
    return union([cyl_x(yc, zc, x_face, x_face + hh, hd), cyl_x(yc, zc, x_face - length, x_face, 3.0)])


def touch_parts(out):
    th = TS.TILT_USE
    src_c = TS.SRC_SPEC + " C (받침 좌표 u·w·x, C1~C13) + " + TS.SRC_NUM + " cradle / hinge / leg / points.use"
    # ---- cradle (use pose + folded altview)
    crl = cradle_local()
    cr = TS.place(crl, th)
    cb = cr.bounding_box()
    _e, heel_uw = ear_poly()
    out.add("TS-CRADLE", "화면 받침(크래들)", "touchscreen cradle", "print", G_TS, cr, COLORS["printed_body"], "PETG",
            source=src_c,
            note="추정: 옆벽 2.0 · 위아래 벽 2.2(유리 틈 0.3), 가로 리브 두께 2.0 (u19~21, u107~109); 귀 축 둘레 살 R%.1f, 뒤꿈치 점 = 22° 상태 "
                 "world (y283, z88) = 받침 (u%.2f, w%.2f), 22°에서 z88 평면으로 자름; 다리 걸이 볼의 45° 모따기는 점검창 덮개 턱(u28.5) 앞 "
                 "u%.1f에서 자름(볼 밑 약 4 mm는 짧은 내민 면); 다리 클립 턱 기둥은 뒷판(w12.4)부터, 밑(+u)은 45° 받침으로 윗벽에 이음, 걸림 턱 "
                 "w%.1f~%.1f; 리본 클립 자리는 뒷판 앞면에 0.7 파낸 자리(x%.1f~%.1f u%.1f~%.1f) + 핀 구멍 Ø3.1 2개 관통; 점검창 걸쇠 홈 0.5 "
                 "(창 벽 앞 1.2); 다리 걸이 먼 볼 Ø2.5는 '× 6 막힌 구멍'이 볼 폭 6과 같아 관통으로 모델"
                 % (EAR_R, heel_uw[0], heel_uw[1], CLEVIS_U_MAX, LCLIP_LIP_W[0], LCLIP_LIP_W[1], RCLIP_CR[0] - 15.2, RCLIP_CR[0] + 15.2,
                    RCLIP_CR[1] - 6 - RCLIP_RECESS_UM, RCLIP_CR[1] + 6 + RCLIP_RECESS_UM),
            print_name="화면받침_크래들", R=TS.print_R_top_down(th), folder=FOLDER_TS,
            print_note="윗변(u122.74 면)을 베드에 세워 출력, 경첩 귀가 위(높이 약 %.0f). 러그·스탠드오프·핀 구멍(w 방향)과 귀·다리 걸이 구멍"
                       "(x 방향)은 물방울(꼭짓점 위)로 뽑고 드릴로 다듬음(러그 Ø2.7, 귀 Ø3.3, 다리 걸이 Ø3.3 / Ø2.5). 다리 걸이·다리 클립은 "
                       "45° 모따기로 서포트 없음. 점검창 윗변은 브리지(44 + 26). 유리 받침 턱(u−2.5~−0.3, 앞이 트인 주머니 바닥, 폭 190 × 깊이 10.4)은 "
                       "출력 때 떠 있으니 그 밑에만 트리 서포트(앞이 트여 있어 떼기 쉬움). 속 꽉 채움 약 113 g, 약 5시간. 러그 면 w9.4는 받은 화면으로 재서 맞춤"
                       % (141.8,),
            dims=[("x", TS.CR_X[0], TS.CR_X[1], "받침 폭 193.92 (유리 189.32 + 틈 0.3 + 옆벽 2.0)", 0),
                  ("x", TS.WIN_UP[0], TS.WIN_UP[1], "ㄴ자 점검창 윗부분 70 (u46~74)", 1),
                  ("x", TS.WIN_LO[0], TS.WIN_LO[1], "점검창 아랫부분 26 (u30~46, J1)", 2),
                  ("x", TS.HINGE["left"]["ear"][0], TS.HINGE["right"]["ear"][1], "경첩 귀 8 두 개 (x624.2~632.2 · 712~720)", 3),
                  ("x", TS.LUG_X[0], TS.LUG_X[1], "러그 구멍 140 (Ø2.7, 뒤 Ø5 자리파기)", 4),
                  ("x", TS.SLOT[0], TS.SLOT[1], "아래 트인 홈 22 (리본 + 전원선)", 5),
                  ("y", cb[1], cb[4], "25°: 가장 앞 y%.2f → 가장 뒤 y%.2f" % (cb[1], cb[4]), 0),
                  ("z", cb[2], cb[5], "25°: 뒤꿈치 z%.2f → 가장 높은 곳 z%.2f" % (cb[2], cb[5]), 0)])
    p = out[-1]
    q = p.print_solid.bounding_box()
    p.print_note = p.print_note.replace("높이 약 0", "높이 약 %.0f" % (q[5] - q[2]))
    out.add("TS-CRADLE-FOLD", "화면 받침(크래들) - 접은 상태", "touchscreen cradle, folded", "print", G_TSF, TS.place(crl, TS.TILT_FOLD),
            COLORS["printed_body"], "PETG", source=src_c + "; 추정 없이 C12 접은 상태(90°: y296.5~421.74, z96~113) - 같은 부품의 다른 자세",
            note=ALT, print_name="화면받침_크래들", folder=FOLDER_TS, no_print=True)

    # ---- leg (use pose in the world, folded = stowed on the cradle back)
    A = TS.LEG_AX_YZ
    tip = TS.LEG_TIP_YZ
    lx0, lx1 = TS.LEG_X
    leg = diff(prism_x(_cap(A, tip, TS.LEG_T), lx0, lx1), [hole("x", A[0], A[1], lx0 - 0.01, lx1 + 0.01, 3.3, apex=TS.LEG_N)])
    Rleg = [[1, 0, 0], [0, TS.LEG_DIR[0], TS.LEG_DIR[1]], [0, TS.LEG_N[0], TS.LEG_N[1]]]
    out.add("TS-LEG", "받침다리", "touchscreen support leg", "print", G_TS, leg, COLORS["printed_body"], "PETG",
            source=TS.SRC_SPEC + " D (10 × 6, 축 구멍 Ø3.3 중심 → 발끝 중심 95.0, 양 끝 R3 = 전체 101; 사용 상태 축 (y305.43, z120.8), "
                   "발끝 (y394.4, z87.5), 수평에서 20.5°) + " + TS.SRC_NUM + " leg",
            note="추정: 축은 받침 (u20, w19.5)을 25°로 돌린 점 (y%.2f, z%.2f), 발끝은 사양 점 → 축~발끝 %.3f, 수평에서 %.2f°; 발(R3)은 주머니 "
                 "바닥 z84.5와 뒷벽 y397.4에 닿음" % (A[0], A[1], TS.LEG_LEN_MODEL, TS.LEG_ANGLE),
            print_name="받침다리", R=Rleg, folder=FOLDER_TS,
            print_note="넓은 면(10 × 101)을 베드에 눕혀 출력(높이 6). 축 구멍 Ø3.3은 물방울(꼭짓점 위)로 뽑고 드릴 Ø3.3로 다듬음. 양 끝 R3의 "
                       "아래쪽은 짧은 내민 부분. 벽 4줄 이상(속 거의 꽉). 약 7 g, 약 30분",
            dims=[("x", lx0, lx1, "다리 폭 10 (볼 사이 틈 0.3씩)", 0), ("y", A[0], tip[0], "축 y%.2f → 발끝 y%.1f" % (A[0], tip[0]), 0),
                  ("z", tip[1], A[1], "발끝 z%.1f → 축 z%.2f (20.5°)" % (tip[1], A[1]), 0)])
    pu, pw = TS.LEG_PIVOT_UW
    leg_f = prism_x(_cap((pu, pw), (pu + TS.LEG_L, pw), TS.LEG_T), lx0, lx1)
    leg_f = diff(leg_f, [hole("x", pu, pw, lx0 - 0.01, lx1 + 0.01, 3.3)])
    out.add("TS-LEG-FOLD", "받침다리 - 접은 상태 (받침 뒤 클립)", "support leg, stowed", "print", G_TSF, TS.place(leg_f, TS.TILT_FOLD),
            COLORS["printed_body"], "PETG", source=TS.SRC_SPEC + " D 접은 상태: 받침 뒤 w16.5~22.5, u17~118 (클립 u105~111)",
            note=ALT, print_name="받침다리", folder=FOLDER_TS, no_print=True)

    # ---- inspection-window cover
    cov = TS.place(cover_local(), th)
    out.add("TS-WINCOVER", "점검창 덮개 (ㄴ자)", "inspection-window cover (L-shaped)", "print", G_TS, cov, COLORS["printed_body"], "PETG",
            source=TS.SRC_SPEC + " C5 (창: 윗부분 x596~666 u46~74, 아랫부분 x640~666 u30~46; 덮개는 창 + 1.5 사방, 2 mm 판, 끼움부는 "
                   "창 − 0.2, 걸쇠 2개) + E (윗부분 73×31 + 아랫부분 29×17.5)",
            note="추정: 끼움부 깊이 1.5(w10.9~12.4, 리본 쪽으로 더 들어가지 않음); 걸쇠 = 끼움부 가장자리의 탄성 혀 2개(폭 10, 두께 1, "
                 "뒤에 1 mm 틈) 끝에 0.4 돌기 → 창 벽 앞쪽의 0.5 홈에 걸림(윗변 x620~630, 아랫변 x648~658); 덮개는 뒷판 뒷면(w12.4)에 얹혀 "
                 "w14.4까지 - 리브 끝 w16 안",
            print_name="점검창덮개", R=TS.print_R_back_down(th), folder=FOLDER_TS,
            print_note="바깥면(2 mm 판 뒷면)을 베드에, 끼움부·걸쇠 혀가 위. 서포트 없음. 약 5 g",
            dims=[("x", TS.WIN_UP[0] - COVER_LEDGE, TS.WIN_UP[1] + COVER_LEDGE, "윗부분 73 (창 70 + 1.5씩)", 0),
                  ("x", TS.WIN_LO[0] - COVER_LEDGE, TS.WIN_LO[1] + COVER_LEDGE, "아랫부분 29", 1)])

    # ---- ribbon clips (same printed shape x2): under the lid and inside the cradle
    rc = rclip_canon()
    rc_ps = to_bed(rc)
    L_, Wd, H_ = TS.RCLIP
    rc_lid = rc.translate((RCLIP_LID_X, RCLIP_SEAT_Y, CU_IZ[1] - H_))
    cx, cu, cw = RCLIP_CR
    rc_cr = TS.place(rc.translate((cx, cu, cw)), th)
    rc_src = TS.SRC_SPEC + " E (리본 클립 2개 30×12×3) + A8 (뚜껑 밑 (x605, y320) 둘레 30×12) / C11 (받침 안 u10~20, x597~613)"
    for pid, ko, sol, where in (("TS-RCLIP-LID", "리본 클립 (뚜껑 밑)", rc_lid,
                                 "뚜껑 밑 x%.2f~%.2f y314~326 z73.5~76.5 - 핀 x%.2f·%.2f (통풍 슬롯 사이 살)"
                                 % (RCLIP_LID_X - 15, RCLIP_LID_X + 15, RCLIP_LID_X - RCLIP_PIN_DX, RCLIP_LID_X + RCLIP_PIN_DX)),
                                ("TS-RCLIP-CR", "리본 클립 (받침 안)", rc_cr,
                                 "받침 안 x%.0f~%.0f u%.0f~%.0f w%.1f~%.1f - 러그(x581.5~590.5)를 피해 사양 x605에서 +1 옮김" % (cx - 15, cx + 15, cu - 6, cu + 6, cw, cw + 3))):
        out.add(pid, ko, "DSI ribbon clip", "print", G_TS, sol, COLORS["printed_body"], "PETG", source=rc_src,
                note="추정: 판 30×12×3, 자리 쪽 면에 리본 홈 %.0f × %.1f(리본 16 + 여유), 핀 Ø%.1f × %.0f 두 개(간격 %.0f)가 자리 구멍 Ø%.1f에 "
                     "끼움(헐거우면 핀에 순간접착제 한 방울); %s" % (RCLIP_CHANNEL[0], RCLIP_CHANNEL[1], RCLIP_PIN[0], RCLIP_PIN[1], 2 * RCLIP_PIN_DX,
                                                        RCLIP_PIN[2], where),
                print_name="리본클립", ps=rc_ps, folder=FOLDER_TS,
                print_note="넓은 면을 베드에, 핀·리본 홈이 위. 서포트 없음. 2개, 약 1 g씩",
                dims=[("x", sol.bounding_box()[0], sol.bounding_box()[3], "30", 0)])

    # ---- optional screen cover (only used folded -> altview group, but printed)
    sx, sy_, st = SCREEN_COVER
    fy0, fy1 = TS.pt(TS.CR_U[0], 0, TS.TILT_FOLD)[0], TS.pt(TS.CR_U[1], 0, TS.TILT_FOLD)[0]
    fyc = (fy0 + fy1) / 2.0
    ztop = TS.pt(0, TS.CR_W[0], TS.TILT_FOLD)[1]                  # 113: cradle rim (w-1) folded
    scov = box(TS.X_C - sx / 2, TS.X_C + sx / 2, fyc - sy_ / 2, fyc + sy_ / 2, ztop, ztop + st)
    out.add("TS-SCREENCOVER", "화면 덮개 (선택, 접은 화면 위)", "screen cover (optional, on the folded screen)", "print", G_TSF, scov,
            COLORS["printed_body"], "PETG",
            source=TS.SRC_SPEC + " E (선택: 화면 덮개 196×128×3, 접은 화면 위, 받침 테두리에 얹힘); 자리 x%.0f~%.0f y%.2f~%.2f z%.0f~%.0f "
                   "(접은 받침 테두리 z113 위, 가운데 맞춤)" % (TS.X_C - sx / 2, TS.X_C + sx / 2, fyc - sy_ / 2, fyc + sy_ / 2, ztop, ztop + st),
            note=ALT, print_name="화면덮개_선택", R=R_NONE, folder=FOLDER_TS,
            print_note="선택 부품(접은 화면을 덮을 때만). 평판을 베드에. 약 45 g. 사용 상태 조립에는 없음(접은 상태 보기에만 있음)",
            dims=[("x", TS.X_C - sx / 2, TS.X_C + sx / 2, "196", 0), ("y", fyc - sy_ / 2, fyc + sy_ / 2, "128", 0), ("z", ztop, ztop + st, "3", 0)])

    # ---- screws (bought)
    ax_y, ax_z = TS.AX_Y, TS.AX_Z
    for s in ("left", "right"):
        h = TS.HINGE[s]
        scr = m3_button_x(ax_y, ax_z, h["near"][1], 20.0, -1)
        out.add("TS-M3X20-HINGE-%s" % s[0].upper(), "M3×20 둥근머리 렌치볼트 (화면 경첩 축 %s)" % ("왼쪽" if s == "left" else "오른쪽"),
                "M3x20 button head bolt (hinge axis)", "bought", G_TS, scr, COLORS["stainless"], "SUS304",
                source=TS.SRC_SPEC + " A2 (나사는 +x 쪽 가까운 볼에서, 먼 볼 Ø2.5에 물림 7.6) + design.json added_materials M3×20 ×4 "
                       "(경첩 2 + 다리 축 1 + 예비 1)",
                note="추정: 머리 Ø5.7 × 1.65 (ISO 7380); 몸통 x%.1f~%.1f, 먼 볼(x%.1f~%.1f)에 %.1f 물림"
                     % (h["near"][1] - 20, h["near"][1], h["far"][0], h["far"][1], h["far"][1] - (h["near"][1] - 20)))
    lg = TS.place(m3_button_x(pu, pw, TS.CLEVIS["near"][0], 20.0, +1), th)
    out.add("TS-M3X20-LEG", "M3×20 둥근머리 렌치볼트 (받침다리 축)", "M3x20 button head bolt (leg axis)", "bought", G_TS, lg, COLORS["stainless"],
            "SUS304", source=TS.SRC_SPEC + " C9 (가까운 볼 x646.7~650.7 Ø3.3 관통 → 먼 볼 x661.3~667.3 Ø2.5, 물림 5.4)",
            note="추정: -x 쪽 가까운 볼에서 넣음(몸통 x646.7~666.7), 머리 Ø5.7 × 1.65; 예비 1개는 모델에 없음")
    for i, (hx, hy) in enumerate(LID_SCREW_XY):
        z_head = CU_Z[1] - LID_SCREW_CB[1]                           # 80.5 counterbore floor
        scr = union([cyl_z(hx, hy, z_head, z_head + M3_HEAD[1], M3_HEAD[0]), cyl_z(hx, hy, z_head - 10.0, z_head, 3.0)])
        out.add("TS-M3X10-LID%d" % (i + 1), "M3×10 둥근머리 렌치볼트 (CU 뚜껑 앞 고정 %s)" % ("왼쪽" if i == 0 else "오른쪽"),
                "M3x10 button head bolt (CU lid front)", "bought", G_CUP, scr, COLORS["stainless"], "SUS304",
                source=TS.SRC_SPEC + " A6 (Ø3.4 관통, 위에서 Ø6.5 × 7.5 자리파기, 머리 밑 4.0) + B (받침 Ø2.5 × 10) - 구매 목록 L34 +4",
                note="추정: 머리 Ø5.7 × 1.65 (ISO 7380), 몸통 z70.5~80.5 → 받침 Ø2.5에 6.0 물림")
    k = 0
    for x in TS.LUG_X:
        for u in TS.LUG_U:
            k += 1
            wb0, wb1 = TS.BACK_W
            zc = wb0 + 1.5
            scr = union([cyl_z(x, u, zc, zc + M25_HEAD[1], M25_HEAD[0]), cyl_z(x, u, zc - M25_LEN, zc, 2.5)])
            out.add("TS-M25-LUG%d" % k, "M2.5 나사 (화면 러그, TD2 동봉)", "M2.5 screw (TD2 lug, supplied with the display)", "bought", G_TS,
                    TS.place(scr, th), COLORS["stainless"], "강",
                    source=TS.SRC_SPEC + " C3 (러그 구멍 Ø2.7, 뒤에서 Ø5 자리파기, 남는 두께 1.5, 동봉 M2.5) + G (나사 길이 4.5 이상)",
                    note="추정: 머리 Ø4.5 × 1.8, 길이 4.5 (받침 1.5 + 러그 3.0) - 동봉 나사 길이는 받은 뒤 확인; x%.0f u%.2f" % (x, u))


# ------------------------------------------------------------------ entry point

def build():
    S = _load("body_speakers.json")
    C = _load("body_centre_unit.json")
    F = _load("keyaction_features_frame.json")
    out = Out()
    speaker_parts(S, out)
    xt30_holders(out)
    feet(out)
    joints(out)
    bracket(F, out)
    cu_panels(out)
    cu_tray(C, out)
    cu_lid(C, out)
    io_plate(C, out)
    lid_supports(C, out)
    pb_holder(C, out)
    ks_insert(C, out)
    small_box(C, out)
    touch_parts(out)
    return list(out)


if __name__ == "__main__":
    ps = build()
    for p in ps:
        b = p.solid.bounding_box()
        print("%-22s %-11s %-12s %3d  %s" % (p.id, p.kind, p.group, len(p.solid.decompose()), " ".join("%.2f" % v for v in b)))
    print(len(ps), "parts")
