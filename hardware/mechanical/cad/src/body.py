"""Toccata rear bar / body - L2 one-piece rear bar (2026-10-01) as Part instances (world coordinates, assembled pose).

Governing spec: spec/body_L2.json ("L2", user request 2026-10-01: '건반과 뒤 부품을 합쳐서 뒤 영역을 최대한 줄이고, 케이블이 밖으로
안 나오게, 스피커는 더 눕히고 작게'), incl. implementation_notes.body.py, pareto_by_angle, risks and w1_acoustic_check (W1 approval
with conditions: pole vent >= 10 mm clear along the axis behind the magnet, grille open area >= 40 % with holes >= D3 and plate
<= 2 mm, grille held by 4 screws, polyester fill loosely through the whole box). Details reused from:
  spec/body_speakers.json        grille hex lattice, driver EVA gasket
  spec/body_centre_unit.json     board hole patterns (v3 boss offsets from each board's corner, re-applied to the L2 boxes)
  spec/keyaction_features_frame.json   cheek extents / M3 seats (anti-vibration bracket, as L1)
The L1 low rear bar generator is kept as src/body_L1.py (spec/body_low_L1.json).

L2 layout (world mm, numbers at ANGLE 40): the rear unit is y214..342.5 behind a 2.0 mm air gap to the key modules (y212); the
module USB cables run in a cable duct y212..241 x z0..27 under the whole rear unit (printed duct roof under the pods, the open
front zone of the centre unit), closed at both ends by printed caps. Speaker pods L x-16..257 / R x965..1238 (inner 250), 8-point
side profile, printed baffle at ANGLE deg from horizontal (user decision 2026-10-01: 40, the first L2 choice was 43 - spec
selected_angle / angle_decision), driver centre (x160.5 / 1061.5, y260, z100.45), top z144.65. Centre unit x260..962, z5..72.85
(lids flush with the key tops z72.85), no front wall (front zone y214..241 open to the duct). Pods sit on the key-bed cheeks' M3
seats through BRK2 pins and are tied to the centre only by 2 M4 thumb screws in rubber sleeves + 2 EVA strips per side (D15).

ONE CONSTANT: every pod number (driver centre, top z, back y, baffle / side / duct-former / cavity polygons, grille trim, slant
frame) is derived from ANGLE with the l2_geom.py rules (sound path 3.5 over (y212, z72.85), grille plate lower edge behind y213,
magnet back rim 3.5 in front of the back ply, top = grille plate over the frame corner + 0.5). The back faces of the pods AND the
centre unit (plan rectangle, R27) are YB from the same rules (43 deg: y341.5, 40 deg: y342.5), so every back-ply-fixed part
(back plies, back plate, shelf back strip, seam rails, end walls / bottom plies' rear edges, lids) moves with it; the other
centre-unit contents keep the spec centre_contents boxes (drawn for the 43 deg back face, centre_contents_check.layout_back_y).

Slanted parts are built in a LOCAL frame (x = world x - driver x, y = into the baffle along -axis (= -w), z = up the slant
(= s), origin = driver centre on the outer face) and turned into the world with rot_x(-(90 - ANGLE)) (see sl()).

NOT in L2 (spec delete list + user 2026-10-01): L1 front strips, XT30 holders, dovetails, latches, L1 front panel / dividers, CU
tray, lid supports + their magnets, key-storage insert, small box + lid, CU lid v2, L1 brackets, the rev 2 (Touch Display 2) touchscreen.
R31 touchscreen rev 3 (user-approved 2026-10-01, governing spec ../touchscreen/rev3/design/CAD_SPEC_rev3.md A..G + numbers.json, poses
and numbers in touchscreen_rev3.py): the printed screen lid CU-SCREENLID gets the hinge blocks, heel stops, ribbon / power hole + wall, clip pad +
pin holes, leg pocket, fold feet, vents and the 5.5 counterbores (rib rule: ribs merge into the filled blocks, x651 stops at the hole
wall); new printed parts in 07_터치스크린: cradle (built in its xr/u/w frame, placed at 25 deg), support leg, window cover, ribbon clip,
optional screen cover; bought M3x20 axles and M2.5x6 screen screws. The folded state (90 deg) is a separate view group ('altview', not in
the one-file assembly / 3MF / GLB). The Waveshare display, the DSI FFC and the GPIO power lead are in electronics.py.
Not modelled: glue, foot screws, plywood screws, grille / driver / board screws, polyester fill (note on the pod back panels).
Cable clips (spec printed list 'CABLE-CLIPS' 8, no positions): 6 under the pod duct roofs (empty in the model) + 2 on the left end
wall holding C-SPK-L; one print file.
Every printed part: kind='print', one body, lies on the bed via to_bed(orient(...)), print folder 05_본체출력물.
Horizontal holes in printed parts are teardrops whose apex points up in the print orientation.
"""
import json
import math
import os
import re

from manifold3d import CrossSection, FillRule, JoinType, Manifold

from cadlib import box, clean, cyl_x, cyl_y, cyl_z, diff, mirror_x, orient, prism_x, prism_y, prism_z, rot_x, rot_y, to_bed, union
from parts import COLORS, Part
import touchscreen_rev3 as TS

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

FOLDER = "05_본체출력물"
SRC = "spec/body_L2.json"
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
MIRROR_X = 611.0          # speaker pods L/R and the joints are mirror images about x = (-16 + 1238) / 2

R_NONE = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_FLIP = rot_x(180)       # top face (max z) on the bed
R_YMIN = rot_x(90)        # print z = world y  -> the min-y face on the bed
R_YMAX = rot_x(-90)       # print z = -world y -> the max-y face on the bed
R_XMIN = rot_y(-90)       # print z = world x  -> the min-x face on the bed
R_XMAX = rot_y(90)        # print z = -world x -> the max-x face on the bed


def _load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


L2 = _load("body_L2.json")
SP = L2["speakers"]
CE = L2["centre"]
JN = L2["joints"]

# ------------------------------------------------------------------ the one angle constant

ANGLE = 40.0              # baffle angle from horizontal (user decision 2026-10-01: 40; was 43 - change only this line, see pareto_by_angle)

# ------------------------------------------------------------------ pod rules (scratchpad l2/final/l2_geom.py, same numbers)

T = 11.5                                          # okoume panel thickness
Y0 = L2["overall"]["rear_unit_y"][0]              # 214 rear-unit front faces (2.0 air behind the module rear walls)
MOD_REAR, MOD_TOP = 212.0, 72.85                  # module / cheek rear wall and top (W1 sound-path reference edge)
ZB = L2["feet"]["box_bottom_z"]                   # 5 box bottoms on 5 mm rubber feet
Z_BOT = ZB + T                                    # 16.5 bottom-ply tops
DUCT_Y = tuple(L2["cable_duct"]["cross_section"]["y"])   # (212, 241) cable duct under the rear unit
DUCT_Z = tuple(L2["cable_duct"]["cross_section"]["z"])   # (0, 27)
FW_T = 6.0                # printed front wall (duct former) thickness
SILL = (5.0, 8.0)         # sill behind the front-wall top (y, z) = glue land under the baffle bottom
ROOF_T = 6.0              # printed duct roof z27..33
RISER = (241.0, 247.0)    # printed riser y (sits on the bottom ply's front edge y241)
GR_S0 = -50.0             # grille plate lower edge (s)
GR_W = (11.0, 13.0)       # grille plate (w)
S_LOW = -54.5             # baffle outer-face lower edge (2.0 below the 105 frame / gasket edge)
TOP_EXTRA = 0.5           # pod top = grille plate over the frame top corner D(52.5, 13) + 0.5
MAG_BACK_CLR = 3.5        # magnet back rim -> back ply inner face
GRILLE_Y_MIN = MOD_REAR + 1.0   # R18: grille plate lower edge behind y213
SIGHT_CLR = 3.5           # design vertical clearance of the 27 deg sound path over (212, 72.85): W1 3.0 + 0.5
TAN27 = math.tan(math.radians(27.0))
SENSOR_YZ = (67.0, 12.9)  # hall elements (D14): sensor row y67, pocket floor z12.189 + 0.75 (element centre); the spec d14 numbers use z8


class PodGeom:
    """speaker pod section (y, z) for a baffle angle th (deg from horizontal).
    Frame: s along the outer face (up the slant, 0 at the driver centre), w along the outward normal (0 on the outer face),
    outward normal n = (-sin th, cos th)."""

    def __init__(self, th):
        self.th = th
        r = math.radians(th)
        self.c, self.s = math.cos(r), math.sin(r)
        c, s = self.c, self.s
        yc = max(GRILLE_Y_MIN - GR_S0 * c + GR_W[1] * s, Y0 - S_LOW * c)
        yc = math.ceil(yc / 0.5) * 0.5
        qy = yc - 47.0 * c
        qz_min = MOD_TOP + SIGHT_CLR - (qy - MOD_REAR) * TAN27
        zc = math.ceil((qz_min + 47.0 * s) / 0.05) * 0.05
        self.C = (yc, zc)
        self.z_top = round(self.D(52.5, GR_W[1])[1] + TOP_EXTRA, 2)
        yb = self.D(42.5, -54.0)[0] + MAG_BACK_CLR + T
        self.y_back = math.ceil(yb / 0.5) * 0.5
        self.F = self.D(S_LOW, 0.0)
        self.z_fb = self.F[1]
        self.s_top = (self.z_top - self.C[1]) / s
        self.Tp = self.D(self.s_top, 0.0)

    def D(self, s_, w):
        return (self.C[0] + s_ * self.c - w * self.s, self.C[1] + s_ * self.s + w * self.c)

    def inner_face_y(self, z):
        p0 = self.D(0.0, -T)
        return p0[0] + (z - p0[1]) * self.c / self.s

    def outer(self):
        return [(Y0, DUCT_Z[1]), (Y0, self.z_fb), self.F, self.Tp, (self.y_back, self.z_top), (self.y_back, ZB),
                (DUCT_Y[1], ZB), (DUCT_Y[1], DUCT_Z[1])]

    def cavity(self):
        yfi, ysl, zsl, zr = Y0 + FW_T, Y0 + FW_T + SILL[0], self.z_fb - SILL[1], DUCT_Z[1] + ROOF_T
        yb, zt = self.y_back - T, self.z_top - T
        return [(yfi, zr), (RISER[1], zr), (RISER[1], ZB + T), (yb, ZB + T), (yb, zt), (self.inner_face_y(zt), zt),
                (self.inner_face_y(self.z_fb), self.z_fb), (ysl, self.z_fb), (ysl, zsl), (yfi, zsl)]

    def baffle_poly(self):
        zt = self.z_top
        yi_t = self.inner_face_y(zt - T)
        return [self.F, self.Tp, (yi_t, zt), (yi_t, zt - T), (self.inner_face_y(self.z_fb), self.z_fb)]

    def duct_former_poly(self):
        """front wall y214..220, sill y220..225, roof z27..33 over y214..247, riser y241..247 z16.5..27 (one simple polygon;
        the spec's vertex list swaps 241/247 and self-intersects - see the part note)."""
        yfi, ysl, zsl, zr = Y0 + FW_T, Y0 + FW_T + SILL[0], self.z_fb - SILL[1], DUCT_Z[1] + ROOF_T
        return [(Y0, DUCT_Z[1]), (RISER[0], DUCT_Z[1]), (RISER[0], ZB + T), (RISER[1], ZB + T), (RISER[1], zr), (yfi, zr),
                (yfi, zsl), (ysl, zsl), (ysl, self.z_fb), (Y0, self.z_fb)]

    def sightline_clear(self, pt):
        """vertical clearance of the 27 deg path (from the cut-out lower edge D(-47, 0) toward -y) over the point (y, z)."""
        qy, qz = self.D(-47.0, 0.0)
        return qz + (qy - pt[0]) * TAN27 - pt[1]

    def perp_clear(self, pt):
        qy, qz = self.D(-47.0, 0.0)
        return (pt[0] - qy) * math.sin(math.radians(27)) + (pt[1] - qz) * math.cos(math.radians(27))


POD = PodGeom(ANGLE)
CA, SA = POD.c, POD.s                                   # cos / sin of ANGLE
TH_V = 90.0 - ANGLE                                     # 50 deg from vertical (at 40)
DRV_YZ = POD.C                                          # (260, 100.45) driver centre on the outer face (at 40; 43: 258.5, 102.25)
SPK_ZT = POD.z_top                                      # 144.65 (43: 148.06)
YB = POD.y_back                                         # 342.5 back faces (pods and centre, rectangle; 43: 341.5)
YBI = YB - T                                            # 331 back-ply inner faces
Z_FB = POD.z_fb                                         # 65.42 baffle bottom / front-wall top
SL_A, SL_B = POD.F, POD.Tp                              # outer face (218.25, 65.42) -> (312.68, 144.65)
SL_LEN = POD.s_top - S_LOW                              # 123.26
TOP_Y0 = POD.inner_face_y(SPK_ZT - T)                   # 316.86 top-ply front edge (butts the baffle top cap)
OUTER = POD.outer()
CAVITY = POD.cavity()
BAFFLE_POLY = POD.baffle_poly()
FORMER_POLY = POD.duct_former_poly()
DRIVER_AXIS = (0.0, -SA, CA)                            # (0, -0.6428, 0.766) out of the baffle, toward the player and up
D = POD.D

SPEC_ANGLE = SP["baffle"]["angle_from_horizontal_deg"]  # spec speakers.* hold the selected angle (L2.selected_angle, 40)
assert abs(L2.get("selected_angle", SPEC_ANGLE) - SPEC_ANGLE) < 1e-9, "spec selected_angle != speakers.baffle angle"
if abs(ANGLE - SPEC_ANGLE) < 1e-9:                      # the derived geometry reproduces the spec (selected angle) to 0.011
    def _close(a, b, tol=0.011):
        return all(abs(p - q) <= tol for p, q in zip(a, b))
    assert _close(DRV_YZ, SP["driver"]["centre_yz"]), DRV_YZ
    assert abs(SPK_ZT - SP["z"][1]) < 1e-9 and abs(YB - SP["y"][1]) < 1e-9
    assert all(_close(p, q) for p, q in zip(OUTER, SP["outer_yz_polygon"]))
    assert all(_close(p, q) for p, q in zip(CAVITY, SP["inner_yz_polygon"]))
    assert all(_close(p, q) for p, q in zip(BAFFLE_POLY, next(p for p in SP["panels"] if "baffle" in p["part"])["yz_polygon"]))
    assert _close(DRIVER_AXIS, SP["driver"]["axis_xyz"], 1e-4)
    assert abs(SL_LEN - SP["baffle"]["slant_length"]) < 0.011

# ------------------------------------------------------------------ plan layout (spec numbers)

SPK_X = {"L": tuple(SP["L"]["x"]), "R": tuple(SP["R"]["x"])}            # (-16, 257) / (965, 1238)
SPK_IX = {"L": tuple(SP["L"]["inner_x"]), "R": tuple(SP["R"]["inner_x"])}   # (-4.5, 245.5) / (976.5, 1226.5)
SX0, SX1 = SPK_IX["L"]
DRV_X = dict(SP["driver"]["x_centre"])                                  # L 160.5 / R 1061.5
CU_X = tuple(CE["x"])                                                   # (260, 962)
CU_IX = tuple(CE["inner_x"])                                            # (271.5, 950.5)
Z_LIDU, Z_LID = CE["walls"]["lid_z"]                                    # 61.35 / 72.85 (lids flush with the key tops)
LIDS = {l["id"]: tuple(l["x"]) for l in CE["lids"]}                     # LID-L 260..501, CU-SCREENLID 501..721, LID-R 721..962
LID_SEAMS = (LIDS["LID-L"][1], LIDS["LID-R"][0])                        # 501 / 721
BP = CE["back_plate_io"]
BP_X = tuple(BP["x"])                                                   # 397.5 .. 538 back-ply window + printed back plate
CC = {c["id"]: c["bbox_x0x1y0y1z0z1"] for c in L2["centre_contents"]}   # centre contents (electronics reads the same list)
# the spec centre_contents boxes were drawn for the 43 deg back face (centre_contents_check.layout_back_y = 341.5). The items that ride
# on the printed back plate move with the back face YB (40 deg: +1.0) - left at the spec y, 1 mm of plate would close the HUSB238
# USB-C mouth and the J501 nose would end 1 mm inside the plate. electronics.py applies the same shift (BACK_PLATE_ITEMS, DY_BACK).
LAYOUT_BACK_Y = L2["centre_contents_check"].get("layout_back_y", YB)
DY_BACK = YB - LAYOUT_BACK_Y                                            # 1.0 at 40 deg, 0 at 43
BACK_PLATE_ITEMS = ("PR-BACKPLATE", "IO-CABLEPASS", "CU-E-PDTRIG", "CU-E-J501BOARD", "CU-E-J501", "CU-E-SWITCH")
for _k in BACK_PLATE_ITEMS:
    _b = CC[_k]
    CC[_k] = [_b[0], _b[1], _b[2] + DY_BACK, _b[3] + DY_BACK, _b[4], _b[5]]
HUB = tuple(L2["cable_duct"]["hub"]["bbox"])                            # (686.5, 914.5, 282, 330, 16.5, 40.5)
TS_YZ = {s: [tuple(v) for v in JN["pods_to_centre"]["screw_yz"][s]] for s in "LR"}   # M4 thumb screws (y, z)
WIRE_YZ = {"L": (243.0, 40.0), "R": (290.0, 40.0)}                      # speaker-lead hole D6 in the pod inner side panel (spec xt30)
WIRE_D, END_HOLE_D = 6.0, 14.0                                          # pod hole D6 (sealed) / end-wall hole D14 (XT30U-F passes)
# end-wall hole D14 (and the clip-plate hole) coaxial with the XT30U-F pocket, NOT on the pod D6 axis (spec: straight across at z40):
# the XT30U-F (10.2 x 5.2, half diagonal 5.72 < 7) slides straight from its pocket through the tunnel to the pod side (service);
# on the spec axis the left clip trapped it (review 2026-10-01). R: 49.5 (pocket axis 51 - 1.5 keeps the wire from the pod D6 z40 in the hole)
END_HOLE_YZ = {"L": (243.0, 44.0), "R": (290.0, 49.5)}
# pigtail numbers quoted in the XT30 clip notes (electronics.py pig_paths builds the path; check_electronics.py keeps these within 2.5):
PIG_SLACK_MM = 35.0       # slack in the 1.5 loose turns inside the end-wall tunnel (helix length - its axial length)
PIG_OUT_MM = 54.0         # pigtail length outside the pod (pod joint face -> XT30U-F back)

# ------------------------------------------------------------------ exports for electronics.py (the other agent)

# XT30U-F pocket in the printed clip on the centre end walls (x0, x1, y0, y1, z0, z1): mouth +x (L) / -x (R) toward the centre
XT30_POCKET = {"L": (274.6, 287.0, 237.7, 248.3, 41.2, 46.8), "R": (935.0, 947.4, 284.7, 295.3, 48.2, 53.8)}
DRIVER_POSE = {s: (DRV_X[s], DRV_YZ[0], DRV_YZ[1]) for s in "LR"}     # centre on the outer face; axis DRIVER_AXIS
SPK_N = DRIVER_AXIS
SPK_U = (0.0, CA, SA)                                                   # up the slant
BOARD_Z = {"PI": Z_BOT + 6.0, "BUCK": Z_BOT + 5.0, "PED": Z_BOT + 5.0, "J702": Z_BOT + 5.0, "AMP": 45.5}   # board undersides
GEOM = {
    "angle_deg": ANGLE, "driver_pose": DRIVER_POSE, "driver_axis": DRIVER_AXIS, "pod_top_z": SPK_ZT, "back_y": YB,
    "back_ply_inner_y": YBI, "front_y": Y0, "duct_y": DUCT_Y, "duct_z": DUCT_Z, "duct_roof_z": (DUCT_Z[1], DUCT_Z[1] + ROOF_T),
    "centre_x": CU_X, "centre_inner_x": CU_IX, "floor_z": Z_BOT, "lid_underside_z": Z_LIDU, "lid_top_z": Z_LID,
    "hub_bbox": HUB, "xt30_pocket": XT30_POCKET, "pod_wire_hole_yz": WIRE_YZ, "end_wall_hole_d": END_HOLE_D, "end_wall_hole_yz": END_HOLE_YZ,
    "board_underside_z": BOARD_Z, "centre_contents": CC, "back_plate_dy": DY_BACK, "back_plate_items": BACK_PLATE_ITEMS,
}

# ------------------------------------------------------------------ geometry helpers


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


def csk_z(cx, cy, z_face, z_end, d_hole=4.5, d_head=8.6):
    """countersunk screw hole from the top face z_face going down to z_end (screw toward -z)."""
    hc = (d_head - d_hole) / 2.0
    cone = Manifold.cylinder(hc + 0.01, d_hole / 2.0 - 0.005, d_head / 2.0 + 0.005, _nseg(d_head)).translate((cx, cy, z_face - hc))
    return union([cyl_z(cx, cy, z_end, z_face, d_hole), cone, cyl_z(cx, cy, z_face, z_face + 3.0, d_head)])


def bed(m, R):
    return to_bed(orient(m, R))


def mx(m):
    """mirror a left-side solid to the right side (speaker pods, joints, bracket)."""
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


def hex_pts(c1, c2, rc):
    """hexagon (corner radius rc) with flats facing +-c1 and corners at +-c2, CCW."""
    return [(c1 + rc * math.cos(math.radians(30 + 60 * k)), c2 + rc * math.sin(math.radians(30 + 60 * k))) for k in range(6)]


def poly_area(p):
    return 0.5 * abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))))


def chamfer_front_top(x0, x1, c=1.0):
    """cut for a c x 45 deg chamfer on the front top edge (y = Y0, z = Z_LID) of a lid."""
    return prism_x([(Y0 - 0.01, Z_LID - c), (Y0 + c, Z_LID + 0.01), (Y0 - 0.01, Z_LID + 0.01)], x0 - 0.01, x1 + 0.01)


R_SL = rot_x(-TH_V)          # local slant frame -> world: local y (into the baffle) -> -n, local z -> up the slant
R_SL_BED = rot_x(180.0 - ANGLE)   # world -> print: the outer face (normal n) faces down on the bed


def sl(m, xc):
    """local slant-frame solid -> world (origin = driver centre on the outer face at x = xc)."""
    return orient(m, R_SL, (xc, DRV_YZ[0], DRV_YZ[1]))


class Out(list):
    def add(self, id, name_ko, name_en, kind, group, solid, color, material="", source="", note="",
            print_name=None, R=None, print_note="", dims=(), folder=None, ps=None, no_print=False):
        """ps: print solid given directly (already on the bed); no_print: a printed part shown a second time - no print file."""
        solid = clean(solid)
        if kind == "print" and not no_print:
            ps = to_bed(ps) if ps is not None else bed(solid, R if R is not None else R_NONE)
        else:
            ps = None
        self.append(Part(id=id, name_ko=name_ko, name_en=name_en, kind=kind, group=group, solid=solid, color=color,
                         material=material, print_name=print_name if kind == "print" else None,
                         print_folder=(folder or FOLDER) if kind == "print" else None, print_solid=ps, print_note=print_note,
                         dims=list(dims), source=source, note=note))


# ------------------------------------------------------------------ speaker pods L / R

DRV_PCD = 115.0
DRV_PIL = [(sx * DRV_PCD / 2 / math.sqrt(2), sz * DRV_PCD / 2 / math.sqrt(2)) for sx in (-1, 1) for sz in (-1, 1)]  # local (x, s)
DRV_INSERT = (5.6, 6.5)                                 # M4 heat-set insert hole D / depth (kept for L69: OD 6 melts in, 0.4 on the diameter)
DRV_INS = (6.0, 3.3, 4.0)                               # L69 ShenzenAV M4x4x6 heat-set insert: OD 6, thread minor bore 3.3 (model), length 4
DRV_SCREW = (12.0, 4.0, 3.0)                            # L70 M4x12 through the driver flange 4 + EVA gasket 3 in front of the baffle face
DRV_SCREW_IN = DRV_SCREW[0] - DRV_SCREW[1] - DRV_SCREW[2]   # 5: bolt length inside the baffle (insert 4 + 1, hole 6.5)
GR_X, GR_RI, GR_SHI = 75.0, 53.0, 57.0                  # grille half width 150, ring inner half 106, upper end (s)
GR_FACE = (-GR_W[1], -GR_W[0])                          # plate in local y (-13 .. -11)
GR_HOLES = [(sx * 64.0, sz * 40.0) for sx in (-1, 1) for sz in (-1, 1)]   # 4 grille screws in the 22-wide side walls
GR_BORDER = 2.0                                         # solid bar at the plate's lower edge and under the trimmed top
GR_MIN_HOLE = 3.0                                       # W1: every grille hole holds a D3 circle
S_PLATE_TOP = (SPK_ZT - DRV_YZ[1] - GR_W[1] * CA) / SA  # 53.23: plate outer face meets the pod top plane
GR_LAT = (GR_S0 + GR_BORDER, S_PLATE_TOP - GR_BORDER)   # lattice band in s (-48 .. 51.23)
GRILLE_STATS = {}


def build_grille(S):
    """grille in the local slant frame: plate y-13..-11 (w11..13) from s-50 (NO lower ring wall: the 27 deg sound path passes
    under the plate edge), side walls 22 wide and the upper ring wall standing on the baffle face (w0..11); hex lattice from
    body_speakers.json, only cells that hold a D3 circle (W1)."""
    gr = next(p for p in S["printed"] if p["id"] == "spk_grille")
    lat = gr["lattice"]
    af, pitch = lat["across_flats"], lat["pitch"]
    fy0, fy1 = GR_FACE
    solid = box(-GR_X, GR_X, fy0, 0.0, GR_S0, GR_SHI)
    cuts = [box(-GR_RI, GR_RI, fy1, 0.01, GR_S0 - 0.01, GR_RI)]      # ring opening, open at the bottom
    s0, s1 = GR_LAT
    region = CrossSection([[(-GR_RI, s0), (GR_RI, s0), (GR_RI, s1), (-GR_RI, s1)]], FillRule.NonZero)
    disc = CrossSection([tear_pts(0.0, 0.0, 94.0)], FillRule.NonZero)
    rc = af / math.sqrt(3.0)
    dv = pitch * math.sqrt(3.0) / 2.0
    nrow = int(max(abs(s0), abs(s1)) / dv) + 2
    open_a, open_disc, ncell = 0.0, 0.0, 0
    for j in range(-nrow, nrow + 1):
        off = (pitch / 2.0) if (j % 2) else 0.0
        for i in range(-int(GR_RI / pitch) - 2, int(GR_RI / pitch) + 3):
            u, v = i * pitch + off, j * dv
            c = CrossSection([hex_pts(u, v, rc)], FillRule.NonZero) ^ region
            if c.is_empty() or c.offset(-GR_MIN_HOLE / 2.0, JoinType.Round).is_empty():
                continue                                             # partial cells narrower than D3 stay closed
            open_a += c.area()
            open_disc += (c ^ disc).area()
            ncell += 1
            for poly in c.to_polygons():
                if len(poly) >= 3:
                    cuts.append(prism_y([tuple(q) for q in poly], fy0 - 0.01, fy1 + 0.01))
    for (hx, hz) in GR_HOLES:
        cuts.append(cyl_y(hx, hz, fy0 - 0.01, 0.01, 4.5))
    GRILLE_STATS.update({"cells": ncell, "open_frac_lattice": open_a / region.area(), "open_frac_d94": open_disc / disc.area(),
                         "lattice_area": region.area(), "af": af, "pitch": pitch})
    return diff(solid, cuts)


def side_in_panel(side):
    """inner side panel (centre-unit side): M4 L73 thread-insert pilot holes D5.8 x 8 blind from the joint face (QS_HOLE; 3.5 of ply under
    the full-diameter bottom, >= 1.5 under the drill point) + sealed wire hole D6."""
    x0, x1 = (SPK_IX["L"][1], SPK_X["L"][1]) if side == "L" else (SPK_X["R"][0], SPK_IX["R"][0])
    face = x1 if side == "L" else x0
    sgn = -1.0 if side == "L" else 1.0
    dq = QS_HOLE[1]
    cuts = [cyl_x(y, z, min(face, face + sgn * dq) - (0.01 if side == "R" else 0.0), max(face, face + sgn * dq) + (0.01 if side == "L" else 0.0), QS_HOLE[0])
            for (y, z) in TS_YZ[side]]
    wy, wz = WIRE_YZ[side]
    cuts.append(cyl_x(wy, wz, x0 - 0.01, x1 + 0.01, WIRE_D))
    return diff(prism_x(OUTER, x0, x1), cuts)


def speaker_parts(S, out):
    g_ko = {"SIDEOUT": "옆판(바깥쪽)", "SIDEIN": "옆판(가운데 유닛 쪽)", "BACK": "뒤판", "TOP": "윗판", "BOTTOM": "아랫판"}
    g_en = {"SIDEOUT": "side panel (outer)", "SIDEIN": "side panel (centre-unit side)", "BACK": "back panel", "TOP": "top panel",
            "BOTTOM": "bottom panel"}
    left = {
        "SIDEOUT": prism_x(OUTER, SPK_X["L"][0], SX0),
        "BACK": box(SX0, SX1, YBI, YB, ZB, SPK_ZT),
        "TOP": box(SX0, SX1, TOP_Y0, YBI, SPK_ZT - T, SPK_ZT),
        "BOTTOM": box(SX0, SX1, RISER[0], YBI, ZB, Z_BOT),
    }
    op = " ".join("(%.2f,%.2f)" % p for p in OUTER)
    cut_txt = {
        "SIDEOUT": "%.1f×%.2f 판에서 직선 자르기: %.0f° 경사 1번 + 앞 턱 + 통로 홈 y214~241 × z5~27 → 8점 %s" % (YB - Y0, SPK_ZT - ZB, ANGLE, op),
        "SIDEIN": "바깥쪽 옆판과 같은 8점 모양 + M4 나사산 인서트(L73) 구멍 Ø%.1f × %.0f 2개 (가운데 쪽 면에서, 막힘) + 스피커선 구멍 Ø6" % QS_HOLE,
        "BACK": "%.0f×%.2f (옆판 사이 y%.0f~%.1f, z5~%.2f)" % (SX1 - SX0, SPK_ZT - ZB, YBI, YB, SPK_ZT),
        "TOP": "%.0f×%.2f (y%.2f~%.0f, 앞 모서리는 출력 앞판 윗마개에 맞댐)" % (SX1 - SX0, YBI - TOP_Y0, TOP_Y0, YBI),
        "BOTTOM": "%.0f×%.0f (y241~%.0f, z5~16.5, 앞 모서리 y241 = 통로 뒷벽 아래)" % (SX1 - SX0, YBI - RISER[0], YBI),
    }
    fill = ("흡음솜(폴리에스터 약 35 g/통)은 상자 전체에 느슨하게 채움 (W1 2026-10-01: 가운데 포함, 686 Hz x 방향 모드 억제; "
            "유닛 뒤 10 mm와 자석 뒤 폴 벤트 축 방향 10 mm 이상은 비움 - 모델에 없음)")
    for side in "LR":
        g = G_SPK[side]
        for tag in ("SIDEOUT", "SIDEIN", "BACK", "TOP", "BOTTOM"):
            if tag == "SIDEIN":
                m = side_in_panel(side)
            else:
                m = left[tag] if side == "L" else mx(left[tag])
            note = ""
            if tag == "SIDEIN":
                ins = " · ".join("y%.0f z%.0f" % p for p in TS_YZ[side])
                note = ("사양과 다름(작은 고침): 10/1 구매 목록 L73(Norelem 07653-04 나사산 인서트 M4, 겉 Ø%.1f × 길이 %.0f)에 맞춤 - 인서트 구멍 %s - "
                        "Ø6.5 × 8 → Ø%.1f × %.0f (이음면에서 막힘; 오꾸메 자투리에 Ø%.1f로 먼저 시험 - 헐거우면 Ø5.5); 제조사 최소 구멍 깊이 %.0f 충족; "
                        "밀폐 규칙: 옆판 %.1f에서 지름 부분 바닥 밑 %.1f, 드릴 끝(118° 원뿔 1.8 / 목공 뿔 비트 촉 약 2, %.1f로 잡음) 밑 %.1f ≥ %.1f 남음 - "
                        "깊이 멈춤(테이프 표시 %.0f mm)으로 뚫음; 스피커선 구멍 Ø6 y%.0f z%.0f (선을 넣고 본드로 밀봉, EVA 띠 사이)"
                        % (INS[0], INS[2], ins, QS_HOLE[0], QS_HOLE[1], QS_HOLE[0], QS_MIN_DEPTH, T, T - QS_HOLE[1], QS_POINT,
                           T - QS_HOLE[1] - QS_POINT, QS_MIN_PLY, QS_HOLE[1], WIRE_YZ[side][0], WIRE_YZ[side][1]))
            elif tag == "BACK":
                note = fill
            out.add("SPK%s-PLY-%s" % (side, tag), "스피커 파트 %s %s" % (side, g_ko[tag]), "speaker pod %s %s" % (side, g_en[tag]),
                    "plywood", g, m, COLORS["plywood"], PLY,
                    source=SRC + " speakers.panels / plywood_cut_list (재단 %s)" % cut_txt[tag], note=note)

    # ---- printed ANGLE-deg baffle (left, then mirrored)
    baf = prism_x(BAFFLE_POLY, SX0, SX1)
    cuts = [cyl_y(0.0, 0.0, -1.0, T + 1.5, SP["driver"].get("cutout_d", 94.0))]
    cuts += [cyl_y(px, pz, -0.5, DRV_INSERT[1], DRV_INSERT[0]) for (px, pz) in DRV_PIL]
    cuts += [cyl_y(hx, hz, -0.5, 9.0, 3.4) for (hx, hz) in GR_HOLES]
    baf = diff(baf, [sl(c, DRV_X["L"]) for c in cuts])
    bp = " ".join("(%.2f,%.2f)" % p for p in BAFFLE_POLY)
    for side in "LR":
        m = baf if side == "L" else mx(baf)
        xa, xb = (SX0, SX1) if side == "L" else (mxv(SX1), mxv(SX0))
        cx = DRV_X[side]
        pil_x = sorted(cx + p[0] for p in DRV_PIL)
        dims = [("x", xa, xb, "앞판 폭 250 (옆판 사이)", 0), ("x", cx - 47, cx + 47, "구멍 Ø94 (x%.1f)" % cx, 1),
                ("x", pil_x[0], pil_x[-1], "M4 인서트 L69 Ø6×4 PCD115 45° (구멍 Ø5.6 깊이 6.5)", 2),
                ("x", cx - 64, cx + 64, "그릴 파일럿 128 (Ø3.4 깊이 9)", 3),
                ("y", SL_A[0], TOP_Y0, "앞 아래 끝 y%.2f → 윗마개 y%.2f" % (SL_A[0], TOP_Y0), 0),
                ("y", SL_A[0], DRV_YZ[0], "유닛 중심 y%.2f" % DRV_YZ[0], 1),
                ("z", SL_A[1], SPK_ZT, "z%.2f → %.2f (경사 %.0f°, 바깥면 %.2f)" % (SL_A[1], SPK_ZT, ANGLE, SL_LEN), 0),
                ("z", SL_A[1], DRV_YZ[1], "유닛 중심 z%.2f" % DRV_YZ[1], 1), ("z", SPK_ZT - T, SPK_ZT, "윗마개 11.5 (윗판 앞)", 2)]
        out.add("SPK%s-BAFFLE" % side, "스피커 앞판(배플, %.0f° 경사) %s" % (ANGLE, side), "speaker baffle (printed, %.0f deg) %s" % (ANGLE, side),
                "print", G_SPK[side], m, COLORS["printed_body"], "PETG (검정 또는 회색)",
                source=SRC + " speakers.panels 앞판 yz_polygon %s, baffle %.0f° (수평에서), 경사 길이 %.2f, 두께 11.5, 폭 250; driver centre "
                             "(x%.1f, y%.2f, z%.2f) 구멍 Ø94, 인서트 M4 4개 PCD115, 그릴 나사 4" % (bp, ANGLE, SL_LEN, cx, DRV_YZ[0], DRV_YZ[1]),
                note="사양 그대로: 아래면 z%.2f가 통로 틀의 앞벽·턱(y214~225) 위에 MS 폴리머로 붙음, 윗마개가 윗판 앞(y%.2f)까지; "
                     "추정: M4 열압입 인서트 구멍 Ø%.1f × %.1f (그대로) - 구매 목록 L69 (ShenzenAV M4x4x6: 바깥 Ø%.0f × 길이 %.0f)를 인두로 "
                     "면까지 (지름 %.1f 물림, 보통 범위), 유닛은 M4×12(L70)로 플랜지 %.0f + 가스켓 %.0f을 지나 앞판에 %.0f 들어감 → 인서트 %.0f를 다 "
                     "물고 %.0f 더 나감, 끝은 구멍 바닥 %.1f 위 (구멍 안); 8.1 긴 인서트는 아래 구멍이 밑면 z%.2f에 너무 가까움; 아래 인서트 구멍 바닥과 "
                     "상자 안 사이 2.78 - 인서트를 더 밀어 넣거나 M4×12보다 긴 나사를 쓰면 밀폐가 뚫림), 그릴 파일럿 Ø3.4 × 9 (x ±64, 경사 ±40 = "
                     "그릴 옆벽 가운데, 8호 19 mm 이하 - 아래 파일럿 끝과 상자 안 사이 2.15); 선 구멍은 L2에서 앞판이 아닌 안쪽 옆판에 있음"
                     % (Z_FB, TOP_Y0, DRV_INSERT[0], DRV_INSERT[1], DRV_INS[0], DRV_INS[2], DRV_INS[0] - DRV_INSERT[0], DRV_SCREW[1], DRV_SCREW[2],
                        DRV_SCREW_IN, DRV_INS[2], DRV_SCREW_IN - DRV_INS[2], DRV_INSERT[1] - DRV_SCREW_IN, Z_FB),
                print_name="스피커앞판_경사배플_" + side, R=R_SL_BED,
                print_note="바깥면(유닛·그릴 면)을 베드에 눕혀 출력 (250 × 약 125 × 11.5, 브림 필수 - 256 판에 3 mm씩 여유). "
                           "윗마개의 윗면은 수평에서 %.0f° 기운 짧은 내민 면(베드 쪽 3 mm), 서포트 없음. 인서트·파일럿은 베드 면에서 막힌 구멍. "
                           "벽 4줄 + 채움 30~40 %%. 휘면 사양 risks대로 2조각(혀-홈 + MS 폴리머, 누설 시험). 옆판 사이에 끼워 둘레를 "
                           "목공본드/MS 폴리머로 밀봉. 베드에 닿는 앞 아래 모서리 F(250 길이)는 %.0f° 칼날 모서리라 첫 층이 거칠게 나옴 - 출력 뒤 줄로 "
                           "다듬음; Ø94 구멍 아래쪽은 상자 안쪽 밑면(y229~236)으로 조금 뚫려 나오는데 밀폐와 상관없음(붙이는 면 y218.6~225은 그대로)"
                           % (ANGLE, ANGLE),
                dims=dims)

    # ---- L69 M4 heat-set inserts in the baffle (local slant frame: outer face y = 0, into the baffle +y), flush with the face
    ins_l = [sl(diff(cyl_y(px, pz, 0.0, DRV_INS[2], DRV_INS[0]), [cyl_y(px, pz, -0.01, DRV_INS[2] + 0.01, DRV_INS[1])]), DRV_X["L"])
             for (px, pz) in DRV_PIL]
    for side in "LR":
        for k, m in enumerate(ins_l):
            out.add("SPK%s-INS-%d" % (side, k + 1), "M4 열압입 인서트 L69 (ShenzenAV M4x4x6, 바깥 Ø%.0f × %.0f, 스피커 앞판 %s %d)" % (DRV_INS[0], DRV_INS[2], side, k + 1),
                    "M4 heat-set insert L69 (M4x4x6) in the baffle %s %d" % (side, k + 1), "bought", G_SPK[side], m if side == "L" else mx(m),
                    COLORS["metal"], "황동",
                    source=SRC + " speakers.driver 고정 (인서트 M4 4개 PCD115) + 구매 목록 v4 L69 (ShenzenAV 황동 인서트너트 M4x4x6, 엘레파츠) / L70 "
                                 "(유두 렌치볼트 M4×12)",
                    note="추정: 바깥 Ø%.0f × 길이 %.0f를 앞판의 구멍 Ø%.1f × %.1f에 인두로 면까지 넣음 (지름 %.1f 물림 - 모델은 겹침으로 보여 줌, 더 밀어 "
                         "넣지 않음), 나사산 안지름 Ø%.1f로 모델; M4×12(L70, 모델에 없음)는 유닛 플랜지 %.0f + EVA 가스켓 %.0f을 지나 %.0f 들어가 인서트 "
                         "%.0f를 지나 %.0f 더 나감 - 끝은 구멍 바닥 %.1f 위라 구멍 안 (가스켓 3이 약 2로 눌리면 약 6 들어가 바닥까지 약 0.5 - M4×12 이하만 씀; M4×14면 7 들어가 구멍 깊이 6.5를 넘어 밀폐면 2.78을 뚫음)"
                         % (DRV_INS[0], DRV_INS[2], DRV_INSERT[0], DRV_INSERT[1], DRV_INS[0] - DRV_INSERT[0], DRV_INS[1], DRV_SCREW[1], DRV_SCREW[2],
                            DRV_SCREW_IN, DRV_INS[2], DRV_SCREW_IN - DRV_INS[2], DRV_INSERT[1] - DRV_SCREW_IN))

    # ---- grille (identical L / R: built in the slant frame, trimmed at the pod top)
    G = build_grille(S)
    st = GRILLE_STATS
    for side in "LR":
        cx = DRV_X[side]
        gw = sl(G, cx) ^ box(cx - 100, cx + 100, 150.0, 400.0, 0.0, SPK_ZT)
        lo = D(GR_S0, GR_W[1])
        out.add("SPK%s-GRILLE" % side, "스피커 육각 그릴 (아래 링 벽 없음, %.0f° 경사면용) %s" % (ANGLE, side),
                "hex grille without the lower ring wall (slant) " + side,
                "print", G_SPK[side], gw, COLORS["printed_body"], "PETG 회색 또는 검정",
                source=SRC + " speakers.panels 그릴 (L1 육각 격자, 판 w11~13, s-50~+%.1f, 윗면 z%.2f에서 잘림, 옆벽 22, 아래 링 벽 없음) + "
                             "w1_acoustic_check.grille (개구율 ≥40 %%, 구멍 ≥Ø3, 판 ≤2, 나사 4); " % (S_PLATE_TOP, SPK_ZT)
                       + SRC_S + " spk_grille lattice (육각 맞은편 %.0f · 피치 %.1f)" % (st["af"], st["pitch"]),
                note="사양 그대로: 바깥 150 (x) × 경사 s%.0f~%.2f(판 바깥면, 윗면 z%.2f에서 잘림), 판 두께 2 (w11~13), 옆벽 22 (x ±53~75), "
                     "아래 링 벽 없음 → 27° 소리 길이 판 아래 모서리 D(-50,11) 밑으로 지나감, 판 아래 모서리 y%.2f (≥213, R18); "
                     "사양과 다름(작은 고침): 위 링 벽 s%.0f~%.0f (w0~11)은 L1 그릴에서 그대로 둠 → 출력 150 × %.0f × 13 (사양 print_size %.2f는 판 s-50~+%.2f만) - "
                     "링 윗변이 앞판 면에 닿아 그릴이 떨리지 않음, 105 프레임과 0.5, 윗면 z%.2f 아래; "
                     "추정: 판 아래 끝과 잘린 윗끝에 막힌 띠 %.0f mm (격자 s%.2f~%.2f) - 아래 띠는 27° 선이 판을 지나는 가장 낮은 곳이라 유닛 콘 맨 아래 "
                     "약 1 mm가 27°에서 가려짐 (W1이 승인한 판 예외 - 43°에서 0.94, %.0f°에서 선이 판 아래 모서리 밑 %.2f - 는 판이 격자라는 전제, 음향 영향은 작음), "
                     "가장자리 칸은 Ø3 원이 들어가는 것만 뚫음 → 구멍 %d개, "
                     "개구율 %.1f %% (격자 %.0f × %.1f) · Ø94 앞 %.1f %% (W1 ≥40 %%); 그릴 고정 4-Ø4.5 (x ±64, 경사 ±40), 8호 19 mm → 앞판 파일럿 "
                     "물림 6 (25 mm는 파일럿 끝 2.15 아래 밀폐면을 뚫음 - 19 mm 이하); 링 안쪽 106 = 유닛 프레임 105 + 0.5씩"
                     % (GR_S0, S_PLATE_TOP, SPK_ZT, lo[0], GR_RI, GR_SHI, GR_SHI - GR_S0, S_PLATE_TOP - GR_S0, S_PLATE_TOP, SPK_ZT, GR_BORDER,
                        GR_LAT[0], GR_LAT[1], ANGLE, POD.perp_clear(D(GR_S0, GR_W[0])), st["cells"],
                        100 * st["open_frac_lattice"], 2 * GR_RI, GR_LAT[1] - GR_LAT[0], 100 * st["open_frac_d94"]),
                print_name="스피커그릴_경사", R=R_SL_BED,
                print_note="그릴 판을 베드에 두고 옆벽·위 링 벽(11)을 위로 세워 출력. 잘린 윗면은 수평에서 %.0f° 기운 내민 면(높이 13, 짧음) - "
                           "서포트 없이 됨, 아래쪽 면이 조금 거칠 수 있음. 직결피스 8호 19 mm ×4로 앞판 파일럿에 (W1: 떨리지 않게 4개 모두)" % ANGLE,
                dims=[("x", cx - GR_X, cx + GR_X, "그릴 150", 0), ("x", cx - GR_RI, cx + GR_RI, "링 안쪽 106 (아래는 열림)", 1),
                      ("x", cx - 64, cx + 64, "고정 구멍 128 (Ø4.5)", 2),
                      ("y", lo[0], D(GR_S0, 0.0)[0], "판 아래 모서리 y%.2f (≥213)" % lo[0], 0),
                      ("z", D(GR_S0, 0.0)[1], SPK_ZT, "s-50 → z%.2f에서 자름" % SPK_ZT, 0),
                      ("z", lo[1], D(GR_S0, 0.0)[1] if D(GR_S0, 0.0)[1] > lo[1] else lo[1] + 0.01, "판 아래 모서리 z%.2f" % lo[1], 1)])

    # ---- driver EVA gasket (knife cut)
    gk = next(p for p in S["printed"] if p["id"] == "spk_gasket")
    gm = diff(box(-52.5, 52.5, -3.0, 0.0, -52.5, 52.5),
              [cyl_y(0, 0, -3.01, 0.01, gk["dims"]["inner_dia"])] + [cyl_y(px, pz, -3.01, 0.01, 4.8) for (px, pz) in DRV_PIL])
    for side in "LR":
        out.add("SPK%s-GASKET" % side, gk["name_ko"] + " " + side, "driver EVA gasket 3T " + side, "consumable", G_SPK[side],
                sl(gm, DRV_X[side]), COLORS["rubber"], gk["material"],
                source=SRC_S + " printed spk_gasket (105×105×3, 안 Ø94) → " + SRC + " speakers.panels 가스켓 (L1 그대로) 경사면 위 유닛 자리",
                note="추정: 안쪽 Ø94·바깥 105×105, 나사 자리 4-Ø4.8 PCD115 - EVA 3T 자투리를 칼로 재단, 앞판 바깥면 위(법선 0~3)")

    # ---- printed duct former (front wall + sill + duct roof + riser = the sealed box's front and lower walls)
    fp = " ".join("(%.2f,%.2f)" % p for p in FORMER_POLY)
    fm = prism_x(FORMER_POLY, SX0, SX1)
    for side in "LR":
        m = fm if side == "L" else mx(fm)
        xa, xb = (SX0, SX1) if side == "L" else (mxv(SX1), mxv(SX0))
        out.add("SPK%s-DUCTFORMER" % side, "스피커 통로 틀 (앞벽·턱·통로 지붕·세움벽, 출력) %s" % side,
                "speaker duct former (front wall, sill, duct roof, riser; printed) " + side, "print", G_SPK[side], m,
                COLORS["printed_body"], PETG,
                source=SRC + " speakers.panels 통로 틀 (앞벽 y214~220 z27~%.2f, 턱 y220~225 z%.2f~%.2f, 통로 지붕 z27~33 (y214~247), "
                             "세움벽 y241~247 z16.5~27, 두께 6) + printed_parts SPK-DUCTFORMER" % (Z_FB, Z_FB - SILL[1], Z_FB),
                note="사양과 다름(작은 고침): 사양 yz_polygon의 꼭짓점 순서가 241/247을 바꿔 적어 스스로 꼬이고(자기 교차) 지붕 끝 "
                     "y241~247 z27~33 (6×6)이 비어 상자가 새게 됨 → 설명대로 '지붕 y214~247 + 세움벽 y241~247'로 만듦: %s "
                     "(바깥 치수·안 부피 단면 %.0f mm²는 그대로)" % (fp, poly_area(CAVITY)),
                print_name="스피커통로틀", R=R_XMIN,
                print_note="끝면(x 방향 면, 단면 33 × %.2f)을 베드에 세워 출력, 높이 250 - 브림 5 mm, 느린 속도(얇은 벽 6이 250 높이). "
                           "서포트 없음(단면 그대로 올라감). 옆판 사이에 끼워 앞벽 윗면·턱 위에 앞판을 MS 폴리머로, 세움벽 밑은 아랫판 앞 모서리에 "
                           "본드" % (Z_FB - Z_BOT),
                dims=[("x", xa, xb, "폭 250", 0), ("y", Y0, RISER[1], "통로 지붕 y214~247", 0), ("y", Y0, Y0 + FW_T, "앞벽 6", 1),
                      ("y", Y0 + FW_T, Y0 + FW_T + SILL[0], "턱 5", 2), ("y", RISER[0], RISER[1], "세움벽 6", 3),
                      ("z", Z_BOT, Z_FB, "z16.5 → %.2f" % Z_FB, 0), ("z", DUCT_Z[1], DUCT_Z[1] + ROOF_T, "통로 지붕 z27~33", 1),
                      ("z", Z_FB - SILL[1], Z_FB, "턱 8", 2)])


# ------------------------------------------------------------------ cable duct: side caps, pod sockets

CAP_T = 3.0
CAP_Z = (1.0, DUCT_Z[1])                                # 26 tall (spec print size 3 x 27 x 26)
CAP_NOTCH = (Y0, 223.3, CAP_Z[0], 19.0)                 # y0, y1, z0, z1: open to the bottom - clears the bracket leg, grommet and
                                                        # bolt head by >= 1 and lets the pod lift straight off the bracket


def duct_caps(out):
    x0 = SPK_X["L"][0]
    cap = diff(box(x0, x0 + CAP_T, Y0, DUCT_Y[1], CAP_Z[0], CAP_Z[1]),
               [box(x0 - 0.01, x0 + CAP_T + 0.01, CAP_NOTCH[0] - 0.01, CAP_NOTCH[1], CAP_NOTCH[2] - 0.01, CAP_NOTCH[3])])
    for side in "LR":
        m = cap if side == "L" else mx(cap)
        xa, xb = (x0, x0 + CAP_T) if side == "L" else (mxv(x0 + CAP_T), mxv(x0))
        out.add("DUCT-CAP-%s" % side, "통로 옆 마개 %s (스피커 바깥 옆판 홈에 붙임)" % side, "cable-duct side cap " + side, "print",
                G_SPK[side], m, COLORS["printed_body"], PETG,
                source=SRC + " printed_parts DUCT-CAP (3 × 27 × 26, 스피커 바깥 옆판 홈에 붙임, 브래킷 판 자리 따냄) + cable_duct.ends "
                             "(옆에서 선이 보이지 않음)",
                note="사양과 다름(작은 고침): 따낸 자리 y214~237 × z7~15 → y%.1f~%.1f × z%.0f~%.0f (아래가 열림) - 사양대로면 마개의 z7 아래 "
                     "띠가 브래킷 판 밑에 걸려 스피커를 핀에서 곧게 들어 올릴 수 없음; 브래킷 팔은 핀 쪽 x≥-1.2에만 있어 마개(x%.0f~%.0f)와 겹치는 것은 "
                     "세움 다리(y212.5~218, z8~18)·그로밋 뒤 플랜지·볼트 머리(y≤222.25)뿐, 1 mm 여유; 옆에서 보이는 틈은 다리 앞뒤 작은 자리뿐; "
                     "추정: 마개 z1~27 (책상 위 1), 옆판 홈의 뒷면(y241)·윗면(z27)에 MS 폴리머로 붙임"
                     % (CAP_NOTCH[0], CAP_NOTCH[1], CAP_NOTCH[2], CAP_NOTCH[3], xa, xb),
                print_name="통로옆마개", R=R_XMIN,                  # same orientation L / R: the mirror image of a flat plate is the same print
                print_note="넓은 면을 베드에 눕혀 출력(두께 3). 서포트 없음",
                dims=[("x", xa, xb, "두께 3", 0), ("y", Y0, DUCT_Y[1], "27 (y214~241)", 0), ("y", CAP_NOTCH[0], CAP_NOTCH[1], "따냄 %.1f" % (CAP_NOTCH[1] - CAP_NOTCH[0]), 1),
                      ("z", CAP_Z[0], CAP_Z[1], "26 (z1~27)", 0), ("z", CAP_NOTCH[2], CAP_NOTCH[3], "따냄 z%.0f~%.0f (아래 열림)" % CAP_NOTCH[2:], 1)])


PIN_XY = {"L": (2.5, 230.0)}                            # spec x0.5 / 1221.5 -> 2 mm inboard (bolt / hex-key path of the right grommet)
PIN_XY["R"] = (mxv(PIN_XY["L"][0]), PIN_XY["L"][1])
PIN_D, PIN_Z = 6.0, (14.0, 24.0)
SOCK_Z = (17.0, DUCT_Z[1])                              # socket block under the duct roof
SOCK_HOLE = (6.5, 26.0)                                 # hole D, blind top (2.0 over the pin top)
SOCK_SLOT = 11.0                                        # R: x slot 6.5 x 11


def pod_sockets(out):
    for side in "LR":
        px, py = PIN_XY[side]
        bx0, bx1 = (px - 5.5, px + 5.5) if side == "L" else (SPK_IX["R"][1] - 15.0, SPK_IX["R"][1])   # R: 15 long, ends at the side panel
        blk = box(bx0, bx1, py - 6.0, py + 6.0, SOCK_Z[0], SOCK_Z[1])
        if side == "L":
            h = cyl_z(px, py, SOCK_Z[0] - 0.01, SOCK_HOLE[1], SOCK_HOLE[0])
            kind = "둥근 구멍 Ø6.5"
        else:
            e = (SOCK_SLOT - SOCK_HOLE[0]) / 2.0
            h = slot_hole("z", (px - e, py), (px + e, py), SOCK_Z[0] - 0.01, SOCK_HOLE[1], SOCK_HOLE[0])
            kind = "x 방향 긴 구멍 6.5 × 11"
        m = diff(blk, [h])
        out.add("POD-SOCKET-%s" % side, "스피커 핀 소켓 블록 %s (%s)" % (side, kind), "pod pin socket block %s" % side, "print", G_SPK[side], m,
                COLORS["printed_body"], PETG,
                source=SRC + " joints.rear_unit_to_key_bed (L 둥근 소켓 Ø6.5 / R x 방향 긴 소켓 6.5×11, 1221 mm 사이 공차 ±2.3; 통로 지붕 아래에 "
                             "붙인 출력 블록 - 밀폐 상자를 뚫지 않음, 핀과 소켓 바닥 사이 2 mm) + printed_parts POD-SOCKET (11 × 12 × 10, z17~27)",
                note="사양과 다름(작은 고침): 핀·소켓 x를 사양 x%.1f → x%.1f로 2 mm 안쪽 (브래킷 참고)%s; 추정: 블록 x%.1f~%.1f × 12 × 10을 통로 "
                     "지붕 밑면 z27에 MS 폴리머로 붙임 (옆판 안면 안), 구멍 윗끝 z%.0f = 핀 끝 z24 + 2"
                     % (0.5 if side == "L" else 1221.5, px, "" if side == "L" else "; R 블록 길이 11 → 15 - 사양 11 블록에 긴 구멍 11이면 양끝 벽이 0이 됨 "
                        "(구멍 양옆 벽 %.2f / %.2f)" % (px - 2.25 - 3.25 - bx0, bx1 - (px + 2.25 + 3.25)), bx0, bx1, SOCK_HOLE[1]),
                print_name="핀소켓_%s" % ("둥근" if side == "L" else "긴구멍"), R=R_FLIP,
                print_note="붙이는 윗면(z27)을 베드에, 구멍이 위로 열림. 서포트 없음",
                dims=[("x", bx0, bx1, "%.0f" % (bx1 - bx0), 0), ("x", px - (SOCK_SLOT / 2 if side == "R" else 3.25), px + (SOCK_SLOT / 2 if side == "R" else 3.25),
                                                            kind, 1),
                      ("y", py - 6, py + 6, "12", 0), ("z", SOCK_Z[0], SOCK_Z[1], "z17~27", 0), ("z", SOCK_Z[0], SOCK_HOLE[1], "구멍 9 (z17~26)", 1)])


# ------------------------------------------------------------------ BRK2: anti-vibration bracket with the pod pin

BRK_SEAT_X = {"L": (-11.80, -4.88), "R": (1226.88, 1233.80)}   # cheek M3 seats (keyaction_parts.cheek_features)
BRK_Z = 12.0
BRK2_Z0 = 8.0                                                  # spec: plate z8~14 (above the headphone cables z3..7.5)
BRK2_PLATE_T = 6.0
BRK2_LEG_TOP = 18.0                                            # grommet pocket D6.5 at z12 -> z15.25, + 2.75
BRK2_LEG = (212.5, 215.5, 217.1, 218.0)                        # leg front, web front, web back, leg back (y) - as L1
BRK2_X = (-15.5, 6.5)                                          # leg x: cheek x0 + 0.5 .. behind EL (EL lead from x13.5)
BRK2_ARM = (-1.2, 6.5, BRK2_LEG[3], 236.5)                     # arm x0, x1, y0, y1 (x>=-1.2 keeps the right bolt path free)


def brk_note(side, opened):
    """BRK2 note with the numbers of its own side (R = mirror of L)."""
    lx0, lx1 = BRK2_X
    ax0, ax1, ay0, ay1 = BRK2_ARM
    hx = sorted(BRK_SEAT_X["L"])[-1]
    head = (hx - 2.85, hx + 2.85)
    px = PIN_XY[side][0]
    if side == "L":
        spec_px, leg, arm, hd, lead = 0.5, (lx0, lx1), (ax0, ax1), head, "EL 리드 노치 x13.5와 %.1f" % (13.5 - lx1)
        opn = ", ".join(opened)
    else:
        spec_px, leg, arm, hd = 1221.5, (mxv(lx1), mxv(lx0)), (mxv(ax1), mxv(ax0)), (mxv(head[1]), mxv(head[0]))
        lead = "ER 리드 노치 x1212.5와 %.1f" % (mxv(lx1) - 1212.5)
        opn = ", ".join(re.sub(r"x(-?\d+\.\d+)", lambda m_: "x%.2f" % mxv(float(m_.group(1))), o).replace(" -x", " +X").replace(" +x", " -x").replace(" +X", " +x")
                        for o in opened)
    return ("사양과 다름(작은 고침): 핀 x%.1f → x%.1f - 사양 자리면 핀 판(팔)이 안쪽 그로밋 M3 볼트의 머리(Ø5.7, x%.2f~%.2f)와 렌치 길을 막아 "
            "볼트를 넣고 조일 수 없음; 팔을 볼트 머리 길에서 0.8 띄우고 핀을 2 mm 안쪽으로(핀 사이 1217, R 긴 소켓 공차 그대로), 소켓도 같이 "
            "옮김; 추정: 세움 다리 x%.1f~%.1f y212.5~218 z8~18 (L1 그로밋 자리: 웹 1.6에 허리 구멍 Ø4.2, 플랜지 자리 Ø6.5 - %s), 팔 x%.1f~%.1f "
            "y218~%.1f z8~14 + 45° 받침, 핀 Ø6 z14~24; 다리 밑 z8은 헤드폰 선(z3~7.5) 위 0.5, %s 떨어짐"
            % (spec_px, px, hd[0], hd[1], leg[0], leg[1], opn, arm[0], arm[1], ay1, lead))


def bracket(F, out):
    cheeks = F["cheeks"]
    YF, YW0, YW1, YBK = BRK2_LEG
    G_FL, G_WAIST, G_BORE, G_LEN = 6.0, 4.0, 3.2, 8.6
    POCKET, WEB_HOLE = 6.5, 4.2
    lx0, lx1 = BRK2_X
    ax0, ax1, ay0, ay1 = BRK2_ARM
    px, py = PIN_XY["L"]
    holes = sorted(BRK_SEAT_X["L"])
    solid = union([box(lx0, lx1, YF, YBK, BRK2_Z0, BRK2_LEG_TOP),
                   box(ax0, ax1, ay0 - 0.01, ay1, BRK2_Z0, BRK2_Z0 + BRK2_PLATE_T),
                   prism_x([(ay0 - 0.01, BRK2_Z0 + BRK2_PLATE_T - 0.01), (ay0 + 4.0, BRK2_Z0 + BRK2_PLATE_T - 0.01),
                            (ay0 - 0.01, BRK2_LEG_TOP)], ax0, ax1),                      # 45 deg fillet leg -> arm
                   cyl_z(px, py, PIN_Z[0] - 0.01, PIN_Z[1], PIN_D)])
    cuts = []
    opened = []
    r = POCKET / 2.0
    apx = (0, 1)                                                                          # printed z up: teardrop apex +z
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
        for (ya, yb) in ((YF - 0.01, YW0), (YW1, YBK + 0.01)):
            if ext:
                for e in ext:
                    cuts.append(slot_hole("y", (hxc, BRK_Z), (e, BRK_Z), ya, yb, POCKET, apex=apx))
            else:
                cuts.append(hole("y", hxc, BRK_Z, ya, yb, POCKET, apex=apx))
        cuts.append(hole("y", hxc, BRK_Z, YW0 - 0.01, YW1 + 0.01, WEB_HOLE, apex=apx))
    brkL = diff(solid, cuts)
    brkR = mx(brkL)
    pitch = holes[-1] - holes[0]
    for side in "LR":
        brk = brkL if side == "L" else brkR
        pxs, pys = PIN_XY[side]
        dims = [("x", lx0, lx1, "세움 다리 %.1f (볼 x-16+0.5 → EL 뒤 x%.1f)" % (lx1 - lx0, lx1), 0),
                ("x", holes[0], holes[-1], "볼트 간격 %.2f (볼 너트 자리)" % pitch, 1),
                ("x", ax0, ax1, "팔 %.1f (오른쪽 볼트 머리 길 x≤-2.03 밖)" % (ax1 - ax0), 2),
                ("x", lx0, px, "핀 x%.1f" % px, 3),
                ("y", YF, YBK, "세움 다리 5.5 (볼과 0.5 띄움)", 0), ("y", YW0, YW1, "그로밋 웹 1.6", 1),
                ("y", YF, ay1, "전체 y212.5~%.1f" % ay1, 2), ("y", YF, py, "핀 y%.0f" % py, 3),
                ("z", BRK2_Z0, PIN_Z[1], "전체 z8~24", 0), ("z", BRK2_Z0, BRK_Z, "그로밋 z12", 1),
                ("z", BRK2_Z0, BRK2_Z0 + BRK2_PLATE_T, "판 z8~14", 2), ("z", PIN_Z[0], PIN_Z[1], "핀 Ø6 z14~24", 3)]
        if side == "R":
            dims = mdims(dims)
        out.add("BRK2-%s" % side, "방진 브래킷 %s (끝 부속 볼 ↔ 스피커 핀, L2)" % side, "anti-vibration bracket %s with the pod pin (L2)" % side,
                "print", G_BR, brk, COLORS["printed_body"], "PETG 회색",
                source=SRC + " joints.rear_unit_to_key_bed (BRK2: 볼 뒷면 M3 자리 y212 z12 x-11.80/-4.88 · 1226.88/1233.80에 L42 그로밋 + M3×16, "
                             "L1 그대로; 판 z8~14; 세운 핀 Ø6 z14~24 L x0.5 / R x1221.5, y230) + printed_parts BRK2 (22 × 24 × 16); "
                       + SRC_F + " cheeks + bracket.proposal_v4 (그로밋 웹 1.6)",
                note=brk_note(side, opened),
                print_name="방진브래킷2_" + side, R=R_NONE,
                print_note="밑면(z8)을 베드에, 핀이 위로 서도록 출력(서포트 없음). 그로밋 자리·웹 구멍(y 방향)은 눈물방울(꼭짓점 위) - 자리 밑 바닥은 "
                           "0.75 (베드 위 첫 3~4층, 그대로 둠), 자리 윗부분은 3 mm 내민 지붕. 벽 4줄 + 채움 "
                           "40 % (핀은 꽉). 그로밋을 웹에 끼우고 M3×16 볼트 ×2를 볼의 너트에 조인 뒤(스피커를 올리기 전) 스피커 소켓을 핀에 내려 끼움",
                dims=dims)
        seats = sorted(BRK_SEAT_X[side])
        for i, hxc in enumerate(seats):
            gm = union([cyl_y(hxc, BRK_Z, 212.0, YW0, G_FL), cyl_y(hxc, BRK_Z, YW0, YW1, G_WAIST), cyl_y(hxc, BRK_Z, YW1, 212.0 + G_LEN, G_FL)])
            gm = diff(gm, [cyl_y(hxc, BRK_Z, 211.99, 212.0 + G_LEN + 0.01, G_BORE)])
            out.add("BRK2-%s-GROM%d" % (side, i + 1), "실리콘 방진 그로밋 M3 (L42, 1.6 판용 홈)", "M3 silicone anti-vibration grommet (L42)",
                    "bought", G_BR, gm, COLORS["rubber"], "실리콘", source="hardware/bom L42; " + SRC_F + " bracket.proposal_v4",
                    note="추정: 플랜지 Ø6 × 3.5 + 허리 Ø4 × 1.6 + 플랜지 Ø6 × 3.5 = 길이 8.6, 구멍 Ø3.2; 앞 플랜지가 볼 뒷면 y212에 닿음 (L1 그대로)")
            yb0 = 212.0 + G_LEN
            bolt = union([cyl_y(hxc, BRK_Z, yb0 - 16.0, yb0, 3.0), cyl_y(hxc, BRK_Z, yb0, yb0 + 1.65, 5.7)])
            out.add("BRK2-%s-BOLT%d" % (side, i + 1), "M3×16 둥근머리 볼트 ISO 7380 (방진 브래킷)", "M3x16 button head bolt (bracket)",
                    "bought", G_BR, bolt, COLORS["stainless"], "SUS",
                    source=SRC_F + " bracket.proposal_v4 hardware; 길이 16 = 그로밋 8.6 + 볼 속 7.4 (L1 그대로)",
                    note="추정: 머리 Ø5.7 × 1.65 (ISO 7380), 육각 렌치 2 mm는 뒤(+y)에서 - 스피커를 올리기 전에 조임")
            rc = 5.5 / math.sqrt(3.0)
            nut = diff(prism_y(hex_pts(hxc, BRK_Z, rc), 205.05, 207.45), [cyl_y(hxc, BRK_Z, 205.0, 207.5, 2.5)])
            out.add("BRK2-%s-NUT%d" % (side, i + 1), "M3 육각 너트 (볼의 너트 홈에 압입, 방진 브래킷)", "M3 hex nut in the cheek pocket",
                    "bought", G_BR, nut, COLORS["stainless"], "SUS", source=SRC_F + " bracket.proposal_v4 nut_pocket",
                    note="추정: 볼 너트 홈 천장 z15.2 (볼트 축 z12 + 꼭짓점 3.175) - L1 그대로")


# ------------------------------------------------------------------ joints pod <-> centre: EVA strips, M4 thumb screws

EVA_ROWS = [((243.0, 339.0), (8.0, 26.0)), ((216.0, 339.0), (48.0, 70.0))]   # spec: z8~26 y243~339, z48~70 y216~339
JOINT_GAP = {"L": (SPK_X["L"][1], CU_X[0]), "R": (CU_X[1], SPK_X["R"][0])}   # (257, 260) / (962, 965)
TS_HEAD = (10.0, 6.5)          # knurled thumb-screw head D x h (envelope; L72 head D8 x 6 fits inside)
TS_LEN = 20.0                  # M4 x 20 (L72)
SLV = (8.0, 4.2, 1.5)          # rubber sleeve OD, ID, protrusion into the centre past the end-wall inner face (sleeve = end wall + 1.5)
INS = (6.5, 3.3, 6.0)          # L73 = Norelem 07653-04 self-tapping thread insert (steel, cutting bore): M4, OD 6.5, pitch 0.8, length 6; thread minor bore 3.3 (model)
QS_HOLE = (5.8, 8.0)           # insert pilot D (W1: start D5.8 in okoume, D5.5 if loose) / full-diameter depth from the pod joint face (blind - sealed box)
QS_POINT = 2.0                 # drill-point allowance below the full-diameter depth (118 deg HSS D6: 1.80; brad-point spur about 2)
QS_MIN_DEPTH = 8.0             # Norelem 07653-04 minimum blind-hole depth (maker) - the 8 deep hole meets it
QS_MIN_PLY = 1.5               # sealed-box rule: ply left under the deepest point of the blind hole


def joints(out):
    outer_cs = CrossSection([[tuple(p) for p in OUTER]], FillRule.NonZero)
    for side in "LR":
        g0, g1 = JOINT_GAP[side]
        for i, ((ya, yb), (za, zb)) in enumerate(EVA_ROWS):
            rect = CrossSection([[(ya, za), (yb, za), (yb, zb), (ya, zb)]], FillRule.NonZero)
            polys = (rect ^ outer_cs).to_polygons()
            m = union([prism_x([tuple(q) for q in p], g0, g1) for p in polys if len(p) >= 3])
            m = diff(m, [cyl_x(y, z, g0 - 0.01, g1 + 0.01, 10.0) for (y, z) in TS_YZ[side] if z + 5.0 > za + 0.5 and z - 5.0 < zb - 0.5])
            clipped = abs((rect ^ outer_cs).area() - rect.area()) > 0.01
            out.add("JOIN-EVA-%s%d" % (side, i + 1), "EVA 3T 띠 (이음 틈, %s %s)" % (side, "아래" if i == 0 else "위"),
                    "EVA 3T strip in the joint gap %s %d" % (side, i + 1), "consumable", G_JOIN, m, COLORS["rubber"], "EVA 3T (MEV1)",
                    source=SRC + " joints.pods_to_centre (3 mm 틈에 EVA 3T 띠 2줄: z8~26은 y243~339, z48~70은 y216~339; 나사 자리에 Ø10 구멍)",
                    note="사양 그대로: x%.0f~%.0f, y%.0f~%.0f z%.0f~%.0f, 나사 자리 Ø10 구멍%s; 추정: 스피커 안쪽 옆판 바깥면에 붙임"
                         % (g0, g1, ya, yb, za, zb, ("; 사양과 다름(작은 고침): 위 띠의 앞 위 모서리를 옆판 모양(%.0f° 경사)으로 잘라 옆판 밖 공중에 "
                                                      "뜨지 않게 함 (y216~224 z65~70)" % ANGLE) if clipped else ""))
        # thumb screws, rubber sleeves, wood inserts
        pod_face = g0 if side == "L" else g1                 # 257 / 965 pod inner-panel joint face
        wall_in = CU_IX[0] if side == "L" else CU_IX[1]       # 271.5 / 950.5 end-wall inner face
        sg = 1.0 if side == "L" else -1.0                     # +x from the pod toward the centre (L)
        for k, (y, z) in enumerate(TS_YZ[side]):
            wall_out = g1 if side == "L" else g0                   # 260 / 962 end-wall joint face
            x_slv0, x_slv1 = wall_out, wall_in + sg * SLV[2]
            x_head0, x_head1 = x_slv1, x_slv1 + sg * TS_HEAD[1]
            x_tip = x_slv1 - sg * TS_LEN
            x_ins0, x_ins1 = pod_face, pod_face - sg * INS[2]
            slv = diff(cyl_x(y, z, min(x_slv0, x_slv1), max(x_slv0, x_slv1), SLV[0]),
                       [cyl_x(y, z, min(x_slv0, x_slv1) - 0.01, max(x_slv0, x_slv1) + 0.01, SLV[1])])
            ts = union([cyl_x(y, z, min(x_head0, x_head1), max(x_head0, x_head1), TS_HEAD[0]),
                        cyl_x(y, z, min(x_tip, x_slv1), max(x_tip, x_slv1) + (0.01 if side == "L" else 0.0) - (0.0 if side == "L" else 0.01), 4.0)])
            ins = diff(cyl_x(y, z, min(x_ins0, x_ins1), max(x_ins0, x_ins1), INS[0]),
                       [cyl_x(y, z, min(x_ins0, x_ins1) - 0.01, max(x_ins0, x_ins1) + 0.01, INS[1])])
            where = "%s y%.0f z%.0f" % ("앞" if k == 0 else "뒤", y, z)
            reach = abs(x_slv1 - pod_face)                         # 16: sleeve end -> pod joint face
            out.add("JOIN-TS-%s%d" % (side, k + 1), "M4×20 손잡이볼트 L72 (평로렛, 스피커 ↔ 가운데 %s %s)" % (side, where),
                    "M4x20 thumb screw L72 (pod to centre) %s %d" % (side, k + 1), "bought", G_JOIN, ts, COLORS["stainless"], "SUS304",
                    source=SRC + " joints.pods_to_centre (M4 나비나사 2개, 가운데 안에서 끝벽의 Ø8 고무 슬리브를 지나 스피커 안쪽 옆판의 M4 목재 "
                                 "인서트로, 막힘; screw_yz) + bom_changes (M4 나비나사 ×4) + 구매 목록 v4 L72 (평로렛 손잡이볼트 M4×20, 머리 Ø8 × 6)",
                    note="추정: 머리 자리 Ø10 × 6.5 (L72 머리 Ø8 × 6이 그 안, 사양 자리 Z-TS 10 × 10 × 10 안), 몸통 M4 × 20 (슬리브 끝 → 이음면 %.0f, "
                         "L73 인서트(길이 %.0f)에 %.1f 물림; M4×22면 %.1f 물림, 끝이 구멍 바닥 %.1f 위; 길이 %.0f면 끝이 구멍 바닥(지름 부분 %.0f 깊이)에 닿고 "
                         "그보다 길면 밑 %.1f mm 밀폐 판을 누름 → 최대 M4×22), 머리는 고무 슬리브 끝에만 닿음 (D15: 나무·출력물에 쇠가 닿지 않음)"
                         % (reach, INS[2], TS_LEN - reach, 22.0 - reach, QS_HOLE[1] - (22.0 - reach), reach + QS_HOLE[1], QS_HOLE[1],
                            T - QS_HOLE[1]))
            out.add("JOIN-SLV-%s%d" % (side, k + 1), "고무 슬리브 OD8 ID4.2 (끝벽 구멍, %s %s)" % (side, where),
                    "rubber sleeve OD8 ID4.2 (end-wall hole) %s %d" % (side, k + 1), "bought", G_JOIN, slv, COLORS["rubber"], "고무",
                    source=SRC + " joints.pods_to_centre (끝벽의 Ø8 고무 슬리브, EVA 띠 나사 자리 Ø10) + bom_changes (고무 슬리브(그로밋) ×4)",
                    note="추정: 고무 호스 OD8 ID4.2를 %.1f 길이로 잘라 끝벽 Ø8 구멍에 끼움 (바깥면과 같은 높이) - 가운데 쪽으로 %.1f 나와 나사 머리를 "
                         "받음; 틈 3은 건너지 않음 (나사를 빼면 EVA 띠가 슬리브에 걸리지 않고 스피커가 곧게 들림), 나사 몸통 Ø4는 EVA 띠 Ø10 구멍을 지남"
                         % (abs(x_slv1 - x_slv0), SLV[2]))
            out.add("JOIN-INS-%s%d" % (side, k + 1), "M4 나사산 인서트 Norelem 07653-04 (L73, 겉 Ø%.1f × %.0f, 스피커 안쪽 옆판, %s %s)" % (INS[0], INS[2], side, where),
                    "M4 self-tapping thread insert Norelem 07653-04 (L73) D%.1f x %.0f %s %d" % (INS[0], INS[2], side, k + 1), "bought", G_JOIN, ins,
                    COLORS["metal"], "강",
                    source=SRC + " joints.pods_to_centre (M4 목재 인서트, 8 깊이 막힘) + bom_changes (M4 목재 인서트 ×4) + 구매 목록 v4 L73 "
                                 "(Norelem 07653-04 셀프 태핑 나사산 인서트, 스틸, 컷팅 보어형, M4, 겉지름 6.5, 피치 0.8, 길이 6, 최소 구멍 깊이 8; 나비엠알오 g/3544290)",
                    note="10/1 구매 목록 L73에 맞춤 - 겉 Ø%.1f × 길이 %.0f를 구멍 Ø%.1f × %.0f에 돌려 넣음 (옆판 면과 같은 높이까지만, 밑에 %.0f mm 빈 곳) - "
                         "모델은 겉나사가 구멍 벽을 반지름 %.2f 파고드는 것을 겹침으로 보여 줌, 나사산 안지름 Ø3.3 (손잡이볼트 Ø4와 겹침 = 나사산 물림); "
                         "구멍은 Ø%.1f에서 시작해 오꾸메 자투리에 시험 (헐거우면 Ø5.5 - 나무는 눌림); 제조사 최소 구멍 깊이 %.0f = 이 구멍 깊이; "
                         "슬롯형(07652)은 최소 깊이 10이고 나사를 잠가 손으로 푸는 손잡이볼트에 맞지 않아 쓰지 않음"
                         % (INS[0], INS[2], QS_HOLE[0], QS_HOLE[1], QS_HOLE[1] - INS[2], (INS[0] - QS_HOLE[0]) / 2.0, QS_HOLE[0], QS_MIN_DEPTH))


# ------------------------------------------------------------------ feet (5 mm rubber, i039 28x5)

FOOT_MOVE = {-2.0: 6.0, 1224.0: 1216.0}          # outer pod feet: spec x-2 / 1224 -> x6 / 1216 (screw 10.5 from the bottom-ply end, not 2.5)
FOOT_SCREW = (4.2, 13.0)                          # 8호 thread D, length (13 mm or shorter: the tip stays 1.5 under the ply top)


def foot_positions():
    """[(group, (x, y), spec (x, y))] - spec feet.positions_xy with the outer pod feet moved inboard (see FOOT_MOVE)."""
    pos = L2["feet"]["positions_xy"]
    rows = [("스피커 L", p) for p in pos["pod_L"]] + [("가운데 유닛", p) for p in pos["centre"]] + [("스피커 R", p) for p in pos["pod_R"]]
    return [(g, (FOOT_MOVE.get(float(x), float(x)), float(y)), (float(x), float(y))) for g, (x, y) in rows]


def feet(out):
    h = L2["feet"]["h"]
    foot0 = diff(cyl_z(0, 0, 0.0, h, 28.0), [cyl_z(0, 0, -0.01, h + 0.01, 4.5), cyl_z(0, 0, -0.01, 2.0, 9.0)])
    for i, (grp, (x, y), (sx, sy)) in enumerate(foot_positions()):
        moved = abs(x - sx) > 1e-9
        pod = grp.startswith("스피커")
        if moved:
            edge = SX0 if sx < 611 else SPK_IX["R"][1]
            txt = ("사양과 다름(작은 고침): 바깥 발 x%.0f → x%.0f - 사양 자리면 8호 나사 축이 스피커 아랫판 끝(x%.1f)에서 %.1f라 나사(Ø%.1f)와 끝면 "
                   "사이 나무가 %.1f만 남아 쪼개지거나 옆판 접착면으로 샘; 옮기면 %.1f (뒤 모서리 y%.0f에서 %.0f과 비슷), Ø28 발은 아직 바깥 옆판 밑까지 닿음; "
                   % (sx, x, edge, abs(sx - edge), FOOT_SCREW[0], abs(sx - edge) - FOOT_SCREW[0] / 2, abs(x - edge), YBI, YBI - y))
        else:
            txt = "사양 그대로: (x%.0f, y%.0f); " % (x, y)
        seal = (" 스피커 아랫판은 밀폐 상자 바닥이므로 나사 구멍에 MS 폴리머를 한 방울 넣고 조임 (16 mm 이상이면 상자 안으로 뚫림)" if pod else "")
        out.add("FOOT-%02d" % (i + 1), "피스고무발 28×5 (i039 화성고무, %s)" % grp, "rubber foot 28x5 (i039)", "bought", G_JOIN,
                foot0.translate((x, y, 0.0)), COLORS["rubber"], "고무",
                source=SRC + " feet.positions_xy (화성고무 피스고무발 28×5, i039, 14개, 8호 13 mm 나사; 모든 발은 통로 뒤 y≥248)",
                note=txt + "추정: 머리 자리 Ø9 깊이 2로 표시, 8호 13 mm 이하로 아랫판(11.5)에 고정 - 끝이 z15.0, 판 윗면보다 1.5 아래." + seal)


# ------------------------------------------------------------------ centre unit plywood + lid magnets

MAG = (8.0, 3.0, 3.2)                                              # magnet D, h, pocket depth
MAG_BACK_X = {"L": (290.0, 380.0), "R": (733.0, 935.0)}           # back-ply top-edge magnets (L: left of the back-plate window)
MAG_END = {"L": ((CU_X[0] + CU_IX[0]) / 2.0, 275.0), "R": ((CU_IX[1] + CU_X[1]) / 2.0, 275.0)}   # end-wall top-edge magnet
BOT_SLOTS_BUCK = [(486.0 + 8.0 * i, 292.0, 326.0) for i in range(6)]            # (x0, y0, y1), 4 wide
BOT_SLOTS_PI = [(546.0 + (622.0 - 546.0 - 4.0) / 7.0 * i, 273.0, 307.0) for i in range(8)]
SLOT_PITCH = 8.0                                                                # 4 wide slots, 4 mm slats (a 2.5 slat breaks in okoume)
BACK_SLOTS = [(745.0 + SLOT_PITCH * i, 42.0, 57.0) for i in range(8)]            # (x0, z0, z1), 4 wide, behind the amp (x745..805)
LIDL_SLOTS = [(459.0, 489.0, 284.0 + SLOT_PITCH * i) for i in range(6)]         # (x0, x1, y0), 4 deep in y (y284..328)
LIDR_SLOTS = [(744.0 + 8.0 * i, 288.0, 328.0) for i in range(10)]               # (x0, y0, y1), 4 wide in x
FILLET_SKIP = [(500.0, 512.0), (710.0, 722.0)]                                  # no R3 under the seam posts


def fillet_cut(y0, z1, r, x0, x1):
    arc = [(y0 + r + r * math.cos(math.radians(a)), z1 - r + r * math.sin(math.radians(a))) for a in [90 + 90 * i / 12.0 for i in range(13)]]
    poly = [(y0 - 0.01, z1 + 0.01)] + [(y0 + r, z1 + 0.01)] + arc[1:] + [(y0 - 0.01, z1 - r)]
    return prism_x(poly, x0, x1)


def mag_pocket_down(x, y, z_top):
    return cyl_z(x, y, z_top - MAG[2], z_top + 0.01, MAG[0])


def mag_pocket_up(x, y, z_bot):
    return cyl_z(x, y, z_bot - 0.01, z_bot + MAG[2], MAG[0])


def cu_panels(out):
    # ---- bottom
    x0, x1 = CU_IX
    fl = []
    segs = [(x0 - 0.01, FILLET_SKIP[0][0]), (FILLET_SKIP[0][1], FILLET_SKIP[1][0]), (FILLET_SKIP[1][1], x1 + 0.01)]
    fl = [fillet_cut(RISER[0], Z_BOT, 3.0, a, b) for (a, b) in segs]
    sl_ = [box(a, a + 4.0, b, c, ZB - 0.01, Z_BOT + 0.01) for (a, b, c) in BOT_SLOTS_BUCK + BOT_SLOTS_PI]
    bot = diff(box(x0, x1, RISER[0], YBI, ZB, Z_BOT), fl + sl_)
    out.add("CU-PLY-BOTTOM", "가운데 유닛 아랫판", "centre unit bottom", "plywood", G_CU, bot, COLORS["plywood"], PLY,
            source=SRC + " plywood_cut_list PLY-CU-BOTTOM (679×%.0f, 끝벽 사이 x271.5~950.5, y241~%.0f, 앞 모서리 R3, 강압·Pi 아래 흡기 홈) + "
                         "centre.vents.intake (홈 4×34: 강압 아래 6, Pi 아래 8)" % (YBI - RISER[0], YBI),
            note="사양 그대로: x%.1f~%.1f y241~%.0f z5~16.5; 추정: 흡기 홈 4×34 강압 아래 x%.0f~%.0f (사양 x482~534에서 보드 기둥 Ø7 자리를 피해 "
                 "양끝 4 mm씩 안쪽) y292~326 6개, Pi 아래 x546~622 y273~307 8개 (합 %.0f mm²); 앞 윗모서리 R3은 뚜껑 이음 기둥 자리(x500~512, "
                 "710~722)만 빼고 (케이블이 넘어가는 곳)" % (x0, x1, YBI, BOT_SLOTS_BUCK[0][0], BOT_SLOTS_BUCK[-1][0] + 4, 4 * 34 * 14))
    # ---- end walls (L-shaped: duct notch), XT30 hole D14, sleeve holes D8, magnet pocket
    for side in "LR":
        a, b = (CU_X[0], CU_IX[0]) if side == "L" else (CU_IX[1], CU_X[1])
        wy, wz = END_HOLE_YZ[side]
        mxy = MAG_END[side]
        cuts = [box(a - 0.01, b + 0.01, Y0 - 0.01, RISER[0], ZB - 0.01, DUCT_Z[1]), cyl_x(wy, wz, a - 0.01, b + 0.01, END_HOLE_D)]
        cuts += [cyl_x(y, z, a - 0.01, b + 0.01, SLV[0]) for (y, z) in TS_YZ[side]]
        cuts.append(mag_pocket_down(mxy[0], mxy[1], Z_LIDU))
        m = diff(box(a, b, Y0, YBI, ZB, Z_LIDU), cuts)
        out.add("CU-PLY-END-%s" % side, "가운데 유닛 끝벽 %s (ㄴ자)" % side, "centre unit end wall %s (L-shaped)" % side, "plywood", G_CU, m,
                COLORS["plywood"], PLY,
                source=SRC + " plywood_cut_list PLY-CU-END (%.0f×56.35 = y214~%.0f × z5~61.35에서 통로 홈 y214~241 × z5~27을 뺌, XT30 선 구멍 Ø14, "
                             "나비나사 구멍 Ø8(고무 슬리브) 2개) + centre.lids (LID 자석 끝벽 윗모서리 1)" % (YBI - Y0, YBI),
                note="사양 그대로: x%.1f~%.1f, 나비나사 구멍 %s; 사양과 다름(작은 고침): XT30 구멍 Ø14 중심 y%.0f z%.0f → y%.0f z%.1f - "
                     "스피커 옆판 선 구멍(z%.0f)과 곧게 건너는 사양 자리에서는 끝벽 집게 홈의 XT30U-F가 구멍으로 빠지지 않아(%s) "
                     "스피커를 뗄 수 없음 → %s (F 모서리 반지름 5.72 < 7, 곧게 밀려 나감); 꼬리선은 틈에서 %.1f 올라감; "
                     "추정: 자석 자리 Ø8 × 3.2 윗모서리 (x%.2f y%.0f)"
                     % (a, b, " · ".join("y%.0f z%.0f" % p for p in TS_YZ[side]), WIRE_YZ[side][0], WIRE_YZ[side][1], wy, wz,
                        WIRE_YZ[side][1],
                        "L: 모서리 반지름 8.3 > 7" if side == "L" else "R: 홈 축 z%.0f가 구멍 z%.0f 위로 %.0f - 홈이 구멍 밖" % (
                            (XT30_POCKET["R"][4] + XT30_POCKET["R"][5]) / 2, WIRE_YZ["R"][1], (XT30_POCKET["R"][4] + XT30_POCKET["R"][5]) / 2 - WIRE_YZ["R"][1]),
                        "구멍을 집게 홈과 같은 축으로 올림" if side == "L" else "구멍을 집게 홈 축보다 %.1f 아래까지 올림 (옆판 구멍에서 오는 꼬리가 구멍 안에 남게)" % (
                            (XT30_POCKET["R"][4] + XT30_POCKET["R"][5]) / 2 - wz),
                        wz - WIRE_YZ[side][1], mxy[0], mxy[1]))
    # ---- back ply (window for the printed back plate, amp vents, magnet pockets)
    cuts = [box(BP_X[0], BP_X[1], YBI - 0.01, YB + 0.01, Z_BOT, Z_LIDU + 0.01)]
    cuts += [box(a, a + 4.0, YBI - 0.01, YB + 0.01, z0, z1) for (a, z0, z1) in BACK_SLOTS]
    cuts += [mag_pocket_down(x, (YBI + YB) / 2.0, Z_LIDU) for s in "LR" for x in MAG_BACK_X[s]]
    back = diff(box(CU_X[0], CU_X[1], YBI, YB, ZB, Z_LIDU), cuts)
    out.add("CU-PLY-BACK", "가운데 유닛 뒤판", "centre unit back panel", "plywood", G_CU, back, COLORS["plywood"], PLY,
            source=SRC + " plywood_cut_list PLY-CU-BACK (702×56.35, x260~962, y%.0f~%.1f, z5~61.35; 뒤판 출력물 창 x397.5~538 × z16.5~61.35, "
                         "위가 열림; 앰프 뒤 환기 홈 8개 4×15) + centre.lids (자석 뒤판 윗모서리 2씩)" % (YBI, YB),
            note="사양 그대로: 창 x%.1f~%.0f z16.5~61.35 (뚜껑이 덮음); 추정: 환기 홈 8개 4×15 x%.0f~%.1f z%.0f~%.0f (간격 8, 홈 사이 나무 4; "
                 "앰프 x742~796 뒤, 윗모서리까지 4.35 남김), 자석 자리 Ø8 × 3.2 윗모서리 x%s (L은 창 왼쪽)"
                 % (BP_X[0], BP_X[1], BACK_SLOTS[0][0], BACK_SLOTS[-1][0] + 4, BACK_SLOTS[0][1], BACK_SLOTS[0][2],
                    "/".join("%.0f" % x for s in "LR" for x in MAG_BACK_X[s])))
    # ---- lids L / R (okoume, magnets, exhaust slots)
    for lid, side in (("LID-L", "L"), ("LID-R", "R")):
        a, b = LIDS[lid]
        cuts = [chamfer_front_top(a, b)]
        if side == "L":
            cuts += [box(x0_, x1_, y0_, y0_ + 4.0, Z_LIDU - 0.01, Z_LID + 0.01) for (x0_, x1_, y0_) in LIDL_SLOTS]
            slot_txt = ("배기 홈 6 × (4×30) x%.0f~%.0f y%.0f~%.0f, 간격 %.0f (홈 사이 나무 4 - 2.5면 오꾸메가 부러짐; 강압 쪽; 레일 x491~511 위는 피함)"
                        % (LIDL_SLOTS[0][0], LIDL_SLOTS[0][1], LIDL_SLOTS[0][2], LIDL_SLOTS[-1][2] + 4, SLOT_PITCH))
        else:
            cuts += [box(x0_, x0_ + 4.0, y0_, y1_, Z_LIDU - 0.01, Z_LID + 0.01) for (x0_, y0_, y1_) in LIDR_SLOTS]
            slot_txt = "배기 홈 10 × (4×40) x%.0f~%.0f y%.0f~%.0f (앰프·허브 위)" % (LIDR_SLOTS[0][0], LIDR_SLOTS[-1][0] + 4, LIDR_SLOTS[0][1], LIDR_SLOTS[0][2])
        mags = [(x, (YBI + YB) / 2.0) for x in MAG_BACK_X[side]] + [MAG_END[side]]
        cuts += [mag_pocket_up(x, y, Z_LIDU) for (x, y) in mags]
        m = diff(box(a, b, Y0, YB, Z_LIDU, Z_LID), cuts)
        out.add(lid, "가운데 유닛 뚜껑 %s (오꾸메, 자석 3쌍)" % side, "centre unit lid %s (okoume, 3 magnet pairs)" % side, "plywood", G_CU, m,
                COLORS["plywood"], PLY,
                source=SRC + " centre.lids %s (x%.0f~%.0f, 오꾸메 11.5, 자석 8×3 3쌍: 뒤판 윗모서리 2, 끝벽 윗모서리 1) + plywood_cut_list "
                             "PLY-CU-LID-%s (241×%.1f, 윗면 z72.85 = 건반 윗면, 앞 윗모서리 1×45° 모따기) + centre.vents.exhaust" % (lid, a, b, side, YB - Y0),
                note="사양 그대로: x%.0f~%.0f y214~%.1f z%.2f~%.2f, 앞 윗모서리 1×45°; 추정: %s, 자석 자리 Ø8 × 3.2 밑면 (%s)"
                     % (a, b, YB, Z_LIDU, Z_LID, slot_txt, " · ".join("x%.2f y%.2f" % p for p in mags)))
        for k, (x, y) in enumerate(mags):
            ply_z = Z_LIDU - 0.2 - MAG[1]
            out.add("CU-MAG-PLY-%s%d" % (side, k + 1), "네오디뮴 자석 Ø8×3 N35 (L65) — %s 윗모서리 %s%d" % ("끝벽" if k == 2 else "뒤판", side, k + 1),
                    "magnet 8x3 N35 in the %s top edge %s%d" % ("end wall" if k == 2 else "back ply", side, k + 1), "bought", G_CU,
                    cyl_z(x, y, ply_z, ply_z + MAG[1], MAG[0]), COLORS["magnet"], "N35",
                    source=SRC + " centre.lids %s fix (자석 8×3 3쌍)" % lid,
                    note="추정: 합판 윗모서리 Ø8 × 3.2 자리 바닥에 순간접착제, 윗면이 합판 윗면보다 0.2 아래")
            lid_z = Z_LIDU + 0.2
            out.add("CU-MAG-LID-%s%d" % (side, k + 1), "네오디뮴 자석 Ø8×3 N35 (L65) — 뚜껑 %s 밑면 %d" % (side, k + 1),
                    "magnet 8x3 N35 in the lid %s underside %d" % (side, k + 1), "bought", G_CU,
                    cyl_z(x, y, lid_z, lid_z + MAG[1], MAG[0]), COLORS["magnet"], "N35",
                    source=SRC + " centre.lids %s fix (자석 8×3 3쌍)" % lid,
                    note="추정: 뚜껑 밑면 Ø8 × 3.2 자리에 순간접착제 (0.2 들어감) → 짝 자석과 틈 0.4, 극은 서로 당기게")


# ------------------------------------------------------------------ CU screen lid (L2 lid + R31 touchscreen rev 3 additions, spec A)

LID_SEAM_GAP = 0.5                               # screen lid 0.5 short at each seam (spec x501..721 butts both okoume lids with 0 play)
SLID_X = (LIDS["CU-SCREENLID"][0] + LID_SEAM_GAP, LIDS["CU-SCREENLID"][1] - LID_SEAM_GAP)   # 501.5 .. 720.5
SLID_PLATE, SLID_WALL, SLID_RIB = 3.0, 3.0, 2.0
SLID_RIB_X = [531.0, 571.0, 611.0, 651.0, 691.0]
SLID_RIB_Y = [254.0, 290.0]
SLID_SCREWS = [(506.0, 246.0), (506.0, 322.0), (716.0, 246.0), (716.0, 322.0)]   # spec: rail inserts, front 2 over the posts y246, back y322
SLID_CB = (TS.LID_SCREW["cbore_d"], TS.LID_SCREW["cbore_depth"])   # 6.5 x 5.5 (rev 3 A-7: head seat z67.35, M3x10 tip z57.35)
SLID_SLOTS = [tuple(s) for s in TS.VENTS]        # rev 3 A-6: 8 x (34 x 4), x564~598 / 624~658, y300~325 (x0, x1, y0, y1)
SLID_RIBBON = (TS.HOLE["x"][0], TS.HOLE["x"][1], TS.HOLE["y"][0], TS.HOLE["y"][1])   # rev 3 A-2: 22 x 6 x635.35~657.35 y228.55~234.55
SLID_HOLE_WALL = TS.HOLE["wall"]
assert tuple(TS.LID_SCREW["x"]) == (506.0, 716.0) and tuple(TS.LID_SCREW["y"]) == (246.0, 322.0)
assert abs(Z_LID - SLID_CB[1] - TS.LID_SCREW["head_seat_z"]) < 1e-9 and abs(Z_LIDU - TS.LID_BED) < 1e-9 and abs(Z_LID - TS.LID_TOP) < 1e-9
KN_SIDES = ("left", "right")


def knuckle_poly():
    """A-1 cheek side profile (y, z): R5.5 round the axis + trapezoid y217.55~235.55 at z72.85 -> y221.05~232.05 at the axis."""
    kp = TS.KNUCKLE
    r = kp["R"]
    n = 72
    circ = [(TS.AX_Y + r * math.cos(2 * math.pi * i / n), TS.AX_Z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    trap = [(kp["base_y"][0], Z_LID - 0.01), (kp["base_y"][1], Z_LID - 0.01), (kp["at_axis_y"][1], TS.AX_Z), (kp["at_axis_y"][0], TS.AX_Z)]
    cs = CrossSection([circ], FillRule.NonZero) + CrossSection([trap], FillRule.NonZero)
    polys = cs.to_polygons()
    assert len(polys) == 1
    return [tuple(p) for p in polys[0]]


def ribbon_hole_poly(y0, y1, z0, z1, r=1.0, n=8):
    """A-2 hole section (y, z) with R1 on the top and bottom edges (the cut flares out by r at both faces). The arc chords that meet the
    lid faces are extended past the face (to z0 - e / z1 + e) so no cutter vertex lies on a face plane (no zero-area triangles)."""
    def arc(cy, cz, a0, a1):
        return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

    def ext(p_on, p_next, zt):
        (ya, za), (yb, zb) = p_on, p_next
        t = (zt - za) / (zb - za)
        return (ya + t * (yb - ya), zt)
    e = 0.05
    br = arc(y1 + r, z0 + r, 270, 180)                      # bottom right: face point -> wall point
    tr = arc(y1 + r, z1 - r, 180, 90)                       # top right: wall -> face
    tl = arc(y0 - r, z1 - r, 90, 0)                         # top left: face -> wall
    bl = arc(y0 - r, z0 + r, 0, -90)                        # bottom left: wall -> face
    return ([ext(bl[-1], bl[-2], z0 - e), ext(br[0], br[1], z0 - e)] + br[1:] + tr[:-1] + [ext(tr[-1], tr[-2], z1 + e), ext(tl[0], tl[1], z1 + e)]
            + tl[1:] + bl[:-1])


def pocket_cut_poly():
    """A-3 leg pocket (y, z): 30 deg ramp (y290.43, z72.85) -> (y296.49, z69.35), floor z69.35 to the back wall y300.7, C0.5 top edge."""
    pk = TS.POCKET
    t30 = math.tan(math.radians(30.0))
    yb, zb = pk["back_wall_y"], pk["bottom_z"]
    c = TS.LG["pocket_edge_C"]
    return [(pk["ramp_front_y"] - 0.3 / t30, Z_LID + 0.3), (pk["ramp_front_y"], Z_LID), (pk["ramp_end_y"], zb), (yb, zb),
            (yb, Z_LID - c), (yb + c, Z_LID), (yb + c, Z_LID + 0.3)]


def screen_lid(out):
    x0, x1 = SLID_X
    zp = Z_LID - SLID_PLATE
    kp = TS.KNUCKLE
    add = [box(x0, x1, Y0, YB, zp, Z_LID),
           diff(box(x0, x1, Y0, YB, Z_LIDU, zp + 0.01), [box(x0 + SLID_WALL, x1 - SLID_WALL, Y0 + SLID_WALL, YB - SLID_WALL, Z_LIDU - 0.01, zp + 0.02)])]
    for rx in SLID_RIB_X:
        add.append(box(rx - SLID_RIB / 2, rx + SLID_RIB / 2, Y0 + SLID_WALL - 0.01, YB - SLID_WALL + 0.01, Z_LIDU, zp + 0.01))
    for ry in SLID_RIB_Y:
        add.append(box(x0 + SLID_WALL - 0.01, x1 - SLID_WALL + 0.01, ry - SLID_RIB / 2, ry + SLID_RIB / 2, Z_LIDU, zp + 0.01))
    for (sx, sy) in SLID_SCREWS:
        add.append(box(max(x0, sx - 5.0), min(x1, sx + 5.0), sy - 6.0, sy + 6.0, Z_LIDU, zp + 0.01))
    # rev 3: blocks filled down to the print-bed plane z61.35 (A-1 hinge blocks, A-2 hole wall, A-3 pocket block, A-5 clip pad); the ribs
    # that run into them merge with them, the x651 rib stops at the hole wall (the hole is cut through the wall)
    hx = {s: (TS.XC + TS.HG[s]["xr"][0], TS.XC + TS.HG[s]["xr"][1]) for s in KN_SIDES}     # 538.6~559.0 / 663.0~683.4
    for s in KN_SIDES:
        add.append(box(hx[s][0], hx[s][1], kp["base_y"][0], kp["base_y"][1], Z_LIDU, zp + 0.01))
    hw = SLID_HOLE_WALL
    rx0, rx1, ry0, ry1 = SLID_RIBBON
    add.append(box(rx0 - hw, rx1 + hw, ry0 - hw, ry1 + hw, Z_LIDU, zp + 0.01))
    pb = TS.POCKET["block"]
    add.append(box(pb["x"][0], pb["x"][1], pb["y"][0], pb["y"][1], Z_LIDU, zp + 0.01))
    cp = TS.CLIP["pad"]
    assert abs(cp["z"][0] - Z_LIDU) < 1e-9
    add.append(box(cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], Z_LIDU, zp + 0.01))
    # on top: hinge cheeks (far + near per side), heel stop blocks in the ear slots, fold feet (+ rear lips)
    kn = knuckle_poly()
    for s in KN_SIDES:
        for ck in ("far_cheek", "near_cheek"):
            a, b = TS.hinge_x(s, ck)
            add.append(prism_x(kn, a, b))
        ea, eb = TS.hinge_x(s, "ear_slot")
        hb = TS.HEEL_BLOCK
        add.append(box(ea - 0.01, eb + 0.01, hb["y"][0], hb["y"][1], Z_LID - 0.01, hb["z"][1]))
    for f_ in TS.FOLD_FEET:
        add.append(box(f_["x"][0], f_["x"][1], f_["y"][0], f_["y"][1], Z_LID - 0.01, f_["z"][1]))
        if f_["rear"]:
            add.append(box(f_["x"][0], f_["x"][1], f_["lip"]["y"][0], f_["lip"]["y"][1], Z_LID - 0.01, f_["lip"]["z"][1]))
    lid = union(add)
    cuts = [chamfer_front_top(x0, x1)]
    for (sx, sy) in SLID_SCREWS:
        cuts += [cyl_z(sx, sy, Z_LIDU - 0.01, Z_LID + 0.01, TS.LID_SCREW["hole_d"]), cyl_z(sx, sy, Z_LID - SLID_CB[1], Z_LID + 0.01, SLID_CB[0])]
    cuts += [box(a, b, c, d, zp - 0.01, Z_LID + 0.01) for (a, b, c, d) in SLID_SLOTS]
    cuts.append(prism_x(ribbon_hole_poly(ry0, ry1, Z_LIDU, Z_LID, TS.HOLE["edge_R"]), rx0, rx1))
    cuts.append(prism_x(pocket_cut_poly(), TS.POCKET["x"][0], TS.POCKET["x"][1]))
    for (px, py) in TS.CLIP["pins"]:
        cuts.append(cyl_z(px, py, Z_LIDU - 0.01, Z_LIDU + TS.CLIP["pin_hole_depth"], TS.CLIP["pin_hole_d"]))
    for s in KN_SIDES:                                       # M3x20 axle: near cheek D3.3 clearance, far cheek D2.5 tapped (teardrop, apex up = +z)
        for ck, d in (("near_cheek", 3.3), ("far_cheek", 2.5)):
            a, b = TS.hinge_x(s, ck)
            cuts.append(hole("x", TS.AX_Y, TS.AX_Z, a - 0.01, b + 0.01, d, apex=(0, 1)))
    lid = diff(lid, cuts)
    fl, fr = TS.hinge_x("left", "far_cheek"), TS.hinge_x("right", "far_cheek")
    nl, nr = TS.hinge_x("left", "near_cheek"), TS.hinge_x("right", "near_cheek")
    el, er = TS.hinge_x("left", "ear_slot"), TS.hinge_x("right", "ear_slot")
    pk = TS.POCKET
    ff = TS.FOLD_FEET
    out.add("CU-SCREENLID", "CU 화면 뚜껑 (터치스크린 3판 경첩·다리 주머니·리본 구멍, 출력)",
            "CU screen lid (printed, touchscreen rev 3 hinges, leg pocket, ribbon hole)", "print",
            G_CUP, lid, COLORS["printed_body"], "PETG",
            source=SRC + " centre.lids CU-SCREENLID (x501~721, PETG 출력 판 3 + 갈비, M3×10 4개: 레일 인서트 앞 2는 기둥 위 y246, 뒤 2는 y322) + "
                         "printed_parts CU-SCREENLID; " + TS.SRC_SPEC + " A-1~A-9 (경첩 받침·뒤꿈치 멈춤 블록, 리본·전원선 구멍 22×6 + 벽 2, "
                         "다리 주머니, 접이 받침 발 4 + 턱, 리본 클립 덩어리·핀 구멍, 배기 홈 8 × 34×4, 나사 자리파기 Ø6.5 × 5.5, 갈비 규칙) + "
                         + TS.SRC_NUM + " hinge / hole / clip / vents / leg.pocket / fold_feet_detail / lid_screw + " + TS.SRC_DRW + " (t02·t04)",
            note=("사양과 다름(작은 고침): ① x%.0f~%.0f → x%.1f~%.1f (이음마다 %.1f 틈) - 사양대로면 오꾸메 뚜껑 L·R(재단 ±0.5)과 출력 뚜껑이 틈 0으로 "
                  "맞닿아 조금만 커도 세 장이 나란히 들어가지 않음; ② 뒤끝 y%.1f (사양 자리 블록 y%.1f는 %.0f° 뒤판 - %.0f°에서 뒤판이 %.1f 뒤로 감; "
                  "화면 쪽 값은 모두 사양 그대로, 접은 받침 뒤끝 y%.2f와 뒤끝 사이 %.2f); ③ 나사 자리는 CAD L2 보스 10 × 12 (사양 A-7의 Ø8 기둥을 "
                  "덮음), 구멍 Ø3.4 + 위에서 Ø6.5 × 5.5 자리파기 (머리 자리 z%.2f, 머리 밑 살 6.0); ④ 배기 홈 밑의 갈비 x571·x651은 그대로 둠 "
                  "(홈 34 중 2 mm만 가림, 출력 때 갈비가 판을 받침); ⑤ 출력 방향이 자리만 잡은 판(윗면을 베드에)과 반대 - 경첩 볼·발이 윗면에 있어 "
                  "사양 A-9대로 갈비 면(z%.2f)을 베드에. "
                  "갈비 규칙(사양 A 머리말): 갈비 x%s · y%s (두께 2, z%.2f~%.2f)는 아래 덩어리와 만나는 곳에서 그 덩어리에 합침 - 경첩 받침 밑 채움 "
                  "x%.1f~%.1f · %.1f~%.1f y%.2f~%.2f, 구멍 벽 x%.2f~%.2f y%.2f~%.2f, 클립 덩어리 x%.2f~%.2f y%.2f~%.2f, 주머니 덩어리 x%.0f~%.0f "
                  "y%.2f~%.2f (모두 z%.2f까지 채움); x651 갈비는 구멍을 지나므로 구멍 둘레 벽 앞(y%.2f)과 뒤(y%.2f)에서 끊김. 클립 핀 자리(%s)와 "
                  "접이 발 자리(윗면)는 갈비와 겹치지 않음. "
                  "경첩 받침 2개(뚜껑과 한 몸): 왼쪽 가까운 볼 x%.1f~%.1f (Ø3.3 관통) · 귀 홈 x%.1f~%.1f · 먼 볼 x%.1f~%.1f (Ø2.5 관통 = M3×20 직접 탭 7.6), "
                  "오른쪽 먼 볼 x%.1f~%.1f · 귀 홈 x%.1f~%.1f · 가까운 볼 x%.1f~%.1f, 볼 옆모양 축 (y%.2f, z%.2f) R%.1f + 사다리꼴 z72.85에서 y%.2f~%.2f; "
                  "뒤꿈치 멈춤 블록 귀 홈 x · y%.2f~%.2f · z72.85~%.2f; 리본·전원선 구멍 x%.2f~%.2f y%.2f~%.2f 관통, 위아래 모서리 R%.0f, 둘레 벽 %.0f; "
                  "다리 주머니 x%.0f~%.0f: 30° 경사 (y%.2f, z72.85) → (y%.2f, z%.2f), 바닥 z%.2f, 뒷벽 y%.1f (위 모서리 C%.1f); "
                  "접이 받침 발 16 × 16 × 5.5 (z72.85~%.2f) x%.0f~%.0f · %.0f~%.0f, y%.2f~%.2f · %.2f~%.2f, 뒤 발 뒤 턱 y%.2f~%.2f z72.85~%.2f (발과 틈 0.5); "
                  "리본 클립 핀 구멍 Ø%.1f × %.0f 밑에서 (%s); 배기 홈 %s; 자석 없음 (D14)"
                  % (LIDS["CU-SCREENLID"][0], LIDS["CU-SCREENLID"][1], x0, x1, LID_SEAM_GAP, YB, TS.PL["lid"]["y"][1], TS.PL["sound_rule"]["baffle_deg"], ANGLE,
                     YB - TS.PL["lid"]["y"][1], TS.POINTS["fold"]["cr_top_front"][0], YB - TS.POINTS["fold"]["cr_top_front"][0],
                     Z_LID - SLID_CB[1], Z_LIDU,
                     "/".join("%.0f" % v for v in SLID_RIB_X), "/".join("%.0f" % v for v in SLID_RIB_Y), Z_LIDU, zp,
                     hx["left"][0], hx["left"][1], hx["right"][0], hx["right"][1], kp["base_y"][0], kp["base_y"][1],
                     rx0 - hw, rx1 + hw, ry0 - hw, ry1 + hw, cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], pb["x"][0], pb["x"][1],
                     pb["y"][0], pb["y"][1], Z_LIDU, ry0 - hw, ry1 + hw, " · ".join("x%.2f y%.2f" % tuple(p) for p in TS.CLIP["pins"]),
                     nl[0], nl[1], el[0], el[1], fl[0], fl[1], fr[0], fr[1], er[0], er[1], nr[0], nr[1], TS.AX_Y, TS.AX_Z, kp["R"],
                     kp["base_y"][0], kp["base_y"][1], TS.HEEL_BLOCK["y"][0], TS.HEEL_BLOCK["y"][1], TS.HEEL_BLOCK["z"][1],
                     rx0, rx1, ry0, ry1, TS.HOLE["edge_R"], hw, pk["x"][0], pk["x"][1], pk["ramp_front_y"], pk["ramp_end_y"], pk["bottom_z"],
                     pk["bottom_z"], pk["back_wall_y"], TS.LG["pocket_edge_C"], ff[0]["z"][1], ff[0]["x"][0], ff[0]["x"][1], ff[2]["x"][0],
                     ff[2]["x"][1], ff[0]["y"][0], ff[0]["y"][1], ff[1]["y"][0], ff[1]["y"][1], ff[1]["lip"]["y"][0], ff[1]["lip"]["y"][1],
                     ff[1]["lip"]["z"][1], TS.CLIP["pin_hole_d"], TS.CLIP["pin_hole_depth"],
                     " · ".join("(%.2f, %.2f)" % tuple(p) for p in TS.CLIP["pins"]),
                     " · ".join("x%.0f~%.0f y%.0f~%.0f" % s for s in SLID_SLOTS[:2]) + " … y%.0f~%.0f" % (SLID_SLOTS[-1][2], SLID_SLOTS[-1][3]))),
            print_name="CU화면뚜껑_터치3판", R=R_NONE,
            print_note="갈비 면(z%.2f)을 베드에, 윗면·경첩 볼·발이 위 (사양 A-9). 경첩 받침·구멍 벽·클립 덩어리·주머니 덩어리·나사 보스가 모두 베드까지 "
                       "채워져 서포트 없음; 판은 갈비 위 브리지(갈비 간격 40 이하). 경첩 축 구멍(가까운 볼 Ø3.3, 먼 볼 Ø2.5)은 물방울(꼭짓점 위)로 뽑고 "
                       "드릴 Ø3.3 / Ø2.5로 다듬음(먼 볼은 M3×20이 직접 탭). 클립 핀 구멍 Ø3.1 × 5는 베드 쪽에서 열림. 약 0 g" % Z_LIDU,
            dims=[("x", x0, x1, "%.0f (x%.1f~%.1f, 이음 틈 0.5씩)" % (x1 - x0, x0, x1), 0), ("x", nl[0], fl[1], "경첩 L 20.4 (x%.1f~%.1f)" % (nl[0], fl[1]), 1),
                  ("x", fr[0], nr[1], "경첩 R 20.4 (x%.1f~%.1f)" % (fr[0], nr[1]), 2), ("x", rx0, rx1, "리본 구멍 22 (x%.2f~%.2f)" % (rx0, rx1), 3),
                  ("x", pk["x"][0], pk["x"][1], "다리 주머니 14", 4), ("x", SLID_SLOTS[0][0], SLID_SLOTS[1][1], "배기 홈 34 + 34", 5),
                  ("y", Y0, YB, "%.1f" % (YB - Y0), 0), ("y", kp["base_y"][0], kp["base_y"][1], "경첩 볼 밑 y%.2f~%.2f (축 y%.2f)" % (kp["base_y"][0], kp["base_y"][1], TS.AX_Y), 1),
                  ("y", ry0, ry1, "구멍 6 (y%.2f~%.2f)" % (ry0, ry1), 2), ("y", pk["ramp_front_y"], pk["back_wall_y"], "주머니 경사 → 뒷벽 y%.1f" % pk["back_wall_y"], 3),
                  ("y", SLID_SCREWS[0][1], SLID_SCREWS[1][1], "나사 y246 / y322", 4), ("y", SLID_SLOTS[0][2], SLID_SLOTS[-1][3], "배기 홈 y300~325", 5),
                  ("z", Z_LIDU, Z_LID, "11.5 (z61.35~72.85)", 0), ("z", Z_LID, TS.AX_Z, "경첩 축 z%.2f" % TS.AX_Z, 1),
                  ("z", Z_LID, TS.AX_Z + kp["R"], "볼 윗끝 z%.2f" % (TS.AX_Z + kp["R"]), 2), ("z", Z_LID, ff[0]["z"][1], "접이 발 5.5", 3)])
    p = out[-1]
    p.print_note = p.print_note.replace("약 0 g", "약 %.0f g" % (p.solid.volume() / 1000.0 * 1.27))


# ------------------------------------------------------------------ seam post-rails (+ M3 inserts, screen-lid screws)

RAIL_W, RAIL_T = 20.0, 6.0
POST = 10.0
INS3 = (4.5, 2.6, 4.0, 4.5)       # M3 heat-set insert OD (L71 ShenzenAV M3x4x4.5: OD 4.5), thread minor bore, length; hole depth
INS3_HOLE = 4.0                   # hole D in the rail (kept: the OD 4.5 insert melts in, 0.5 on the diameter)


def seam_rails(out):
    for i, xs in enumerate(LID_SEAMS):
        sx = SLID_SCREWS[0][0] if i == 0 else SLID_SCREWS[2][0]            # 506 / 716 screw x (middle of the lid's 10 mm on the rail)
        px0, px1 = (xs, xs + POST) if i == 0 else (xs - POST, xs)          # post under the front insert
        rz0 = Z_LIDU - RAIL_T
        m = union([box(xs - RAIL_W / 2, xs + RAIL_W / 2, Y0, YBI, rz0, Z_LIDU), box(px0, px1, 241.0, 251.0, Z_BOT, rz0 + 0.01)])
        m = diff(m, [cyl_z(sx, sy, Z_LIDU - INS3[3], Z_LIDU + 0.01, INS3_HOLE) for (sx_, sy) in SLID_SCREWS if abs(sx_ - sx) < 1e-6])
        spec_post = CC["PR-SEAMPOST-%d" % (i + 1)]
        out.add("SEAM-POSTRAIL-%d" % (i + 1), "뚜껑 이음 레일 + 기둥 %d (출력, x%.0f 이음)" % (i + 1, xs), "lid seam rail + post %d (printed)" % (i + 1),
                "print", G_CUP, m, COLORS["printed_body"], PETG,
                source=SRC + " centre_contents PR-SEAMRAIL-%d (x%.0f~%.0f y214~330 z55.35~61.35) + PR-SEAMPOST-%d (10×10, y241~251, z16.5~55.35, "
                             "기둥 위 M3 인서트) + printed_parts SEAM-POSTRAIL (%.0f × 20 × 44.85)"
                       % (i + 1, xs - RAIL_W / 2, xs + RAIL_W / 2, i + 1, YBI - Y0),
                note="사양과 다름(작은 고침): 기둥 x%.0f~%.0f → x%.0f~%.0f - 화면 뚜껑 나사(x%.0f = 뚜껑이 레일에 얹힌 10 mm의 가운데)가 사양 "
                     "기둥(이음선 x%.0f 가운데)의 모서리에 걸려 '기둥 위 인서트'가 안 됨; 추정: M3 열압입 인서트 L71 (바깥 Ø4.5 × 4, 구멍 Ø4 × 4.5) "
                     "레일 윗면 y246·y322; 레일 뒤 끝면은 %s 안면(y%.0f)에 MS 폴리머, 기둥 밑은 아랫판에 MS 폴리머 (기둥 자리는 아랫판 R3 모서리 없음)%s"
                     % (spec_post[0], spec_post[1], px0, px1, sx, xs, "PR-BACKPLATE" if i == 0 else "뒤판", YBI,
                        "" if abs(DY_BACK) < 1e-9 else "; 레일은 뒤판까지 y214~%.0f (사양 상자 y214~%.0f는 43° 뒤판 기준, 뒤판이 %.1f 뒤로 감)"
                        % (YBI, CC["PR-SEAMRAIL-%d" % (i + 1)][3], DY_BACK)),
                print_name="뚜껑이음레일기둥_%d" % (i + 1), R=R_FLIP,
                print_note="레일 윗면(z61.35)을 베드에, 기둥이 위로 서도록 출력(서포트 없음). 인서트는 베드 쪽 면(= 윗면)에서 인두로 넣음",
                dims=[("x", xs - RAIL_W / 2, xs + RAIL_W / 2, "레일 20", 0), ("x", px0, px1, "기둥 10", 1),
                      ("y", Y0, YBI, "레일 %.0f (y214~%.0f)" % (YBI - Y0, YBI), 0), ("y", 241.0, 251.0, "기둥 y241~251", 1),
                      ("z", Z_BOT, Z_LIDU, "44.85 (z16.5~61.35)", 0), ("z", rz0, Z_LIDU, "레일 6", 1)])
    for k, (sx, sy) in enumerate(SLID_SCREWS):
        z_head = Z_LID - SLID_CB[1]
        ins = diff(cyl_z(sx, sy, Z_LIDU - INS3[2], Z_LIDU, INS3[0]), [cyl_z(sx, sy, Z_LIDU - INS3[2] - 0.01, Z_LIDU + 0.01, INS3[1])])
        out.add("SEAM-INS-%d" % (k + 1), "M3 열압입 인서트 L71 (ShenzenAV M3x4x4.5, 바깥 Ø%.1f × %.0f, 뚜껑 이음 레일, 화면 뚜껑 나사 %d)"
                % (INS3[0], INS3[2], k + 1), "M3 heat-set insert L71 (M3x4x4.5, seam rail) %d" % (k + 1),
                "bought", G_CUP, ins, COLORS["metal"], "황동",
                source=SRC + " centre.lids CU-SCREENLID fix (레일 인서트) + 구매 목록 v4 L71 (ShenzenAV 황동 인서트너트 M3x4x4.5 × 6 = 4 + 예비 2)",
                note="추정: 바깥 Ø%.1f × 높이 %.0f를 레일 구멍 Ø%.1f × %.1f에 인두로 면까지 (지름 %.1f 물림 - 모델은 겹침으로 보여 줌; 레일을 붙이기 전에 "
                     "넣음), 나사산 안지름 Ø%.1f로 모델 (나사 Ø3과 겹침 = 나사산 물림); 6개 사서 4개 쓰고 2개 예비"
                     % (INS3[0], INS3[2], INS3_HOLE, INS3[3], INS3[0] - INS3_HOLE, INS3[1]))
        scr = union([cyl_z(sx, sy, z_head, z_head + 1.65, 5.7), cyl_z(sx, sy, z_head - 10.0, z_head, 3.0)])
        out.add("CU-M3X10-%d" % (k + 1), "M3×10 둥근머리 렌치볼트 (화면 뚜껑 고정 %d)" % (k + 1), "M3x10 button head bolt (screen lid) %d" % (k + 1),
                "bought", G_CUP, scr, COLORS["stainless"], "SUS304", source=SRC + " centre.lids CU-SCREENLID (M3×10 4개)",
                note="추정: 머리 Ø5.7 × 1.65 (ISO 7380), 자리파기 바닥 z%.2f, 몸통 z%.2f~%.2f → 인서트에 %.1f 물림"
                     % (z_head, z_head - 10.0, z_head, INS3[2]))


# ------------------------------------------------------------------ R31 touchscreen rev 3 (3a): cradle, leg, small parts, screws

FOLDER_TS = "07_터치스크린"
G_TS = "터치스크린"
G_TSF = "터치스크린 (접은 상태, 별도 보기)"
ALT = "altview"
M3_HEAD = (TS.LG["axle"]["head_d"], TS.LG["axle"]["head_h"])   # ISO 7380 M3 button head 5.7 x 1.65
M25_HEAD = (4.5, 1.8)        # 추정: M2.5x6 button / pan head (spec table: M2.5x6 x4)
M25_LEN = 6.0
PAD_CH = 3.0                 # 45 deg chamfer on the +u (bed-side in print) face of the 4 back pads = rib height w13..16
COVER_TABS = (18.0, 24.0)    # cover snap beams xr range: root at xr18 (plug body), free end xr24 (clear of the ZIF, ribbon lane, wire lane)
COVER_BEAM = (1.0, 2.0, 0.5)  # snap beam along xr: thickness (u, bends in the print layer plane), height (w10.5..12.5), slot under the flange
COVER_BUMP = (0.4, 3.0)      # bump near the beam's free end: out (u) beyond the plug face, length along xr (xr20.8..23.8, 0.2 short of the end)
COVER_BUMP_W = (0.4, 0.05)   # bump profile along w: 45 deg lead-in rise, flat; then a 45 deg removal ramp (ramp >= 0.2 from the groove top corner)
COVER_BUMP_LIFT = 0.05       # bump starts 0.05 above the plug face w10.5 (w10.55..11.40 inside the 10.5..11.5 groove): a bump edge lying on the
#                              beam's bed edge left a collinear sliver triangle (open edges in the STL after write_stl drops it)
COVER_GROOVE = (0.5, 1.0)    # plate window-wall groove for the bump: depth (u), height (w from the plate inner face)
COVER_SNAP = (COVER_BUMP[0] - 0.2, 1.5 * COVER_BEAM[0] * (COVER_BUMP[0] - 0.2) / (COVER_TABS[1] - 0.2 - COVER_BUMP[1] / 2 - COVER_TABS[0]) ** 2)
#                              (interference vs the window wall with the plug 0.2 under, cantilever strain 3 d t / (2 L^2) at the bump centre)
CR_C2 = 2.2                  # C-10 bottom-back chamfer: numbers.json says C2 (2D gap 0.59); C2 gives 0.54 in 3D at 90 deg, C2.2 keeps >= 0.59
BOSS_CB_CAP = 3.10           # M2.5 counterbore D5.5 teardrop cut flat at 3.10 from the axis: roof corners 3.199 from the axis -> boss R4 leaves >= 0.80 everywhere (3.2 left 0.73 at the corners)
SCREEN_COVER = (173.0, 108.0, 3.0)
EAR_INTO_WALL = 0.05         # ear attachment face pushed 0.05 into the bottom wall (no coincident faces)
PLI, PLO = TS.PLATE_W        # 10.5 / 13 back plate


def ear_poly():
    """C-12 ear side profile (u, w) = numbers.json cradle.ear.profile_uw, the attachment edge u-2.5 moved 0.05 into the wall."""
    pts = [((u + EAR_INTO_WALL) if abs(u - TS.CR_U[0]) < 1e-9 else u, w) for (u, w) in TS.EAR_PROFILE]
    h = _hull2d(pts)
    assert len(h) == len(pts), "ear profile must stay convex"
    return h


def clevis_poly():
    """C-13 leg-hanger cheek (u, w): R3.8 round (u30, w16.5) joined to the plate, 45 deg underside on the +u (down in print) side: the
    straight edge is the 45 deg tangent u + w = 30 + 16.5 + 3.8 sqrt2 (exact tangent point added to the polygon), so it meets the plate
    w13 at u38.87 (spec C-13 / t03 B-B 'u38.87 걸이 끝 (45°)')."""
    cu, cw = TS.LEG_PIVOT_UW
    r = TS.CLEVIS["R"]
    k = cu + cw + r * math.sqrt(2.0)                                   # u + w on the 45 deg tangent
    tang = (cu + r / math.sqrt(2.0), cw + r / math.sqrt(2.0))
    return _hull2d(tear_pts(cu, cw, 2 * r) + [tang, (cu - r, PLO - 0.01), (k - (PLO - 0.01), PLO - 0.01)])


CLEVIS_END_U = TS.LEG_PIVOT_UW[0] + TS.LEG_PIVOT_UW[1] + TS.CLEVIS["R"] * math.sqrt(2.0) - PLO   # 38.87: the 45 deg underside meets w13
C2_GAP_AT_C2 = 0.541         # measured (this CAD and W1's 3D model): C2 corner vs hinge cheek at 90 deg; CR_C2 = 2.2 gives 0.617


def tear_cap_pts(c1, c2, d, apex, cap):
    """teardrop toward `apex` with the roof point cut flat at `cap` from the centre (flat width 2 (r sqrt2 - cap))."""
    r = d / 2.0
    ax, ay = apex
    L = math.hypot(ax, ay)
    ax, ay = ax / L, ay / L
    px, py = -ay, ax
    h = r * math.sqrt(2.0) - cap
    n = _nseg(d)
    pts = [(c1 + r * math.cos(2 * math.pi * i / n), c2 + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts = [q for q in pts if (q[0] - c1) * ax + (q[1] - c2) * ay <= cap]
    pts += [(c1 + cap * ax + h * px, c2 + cap * ay + h * py), (c1 + cap * ax - h * px, c2 + cap * ay - h * py)]
    return _hull2d(pts)


def cradle_local():
    """C-1..C-15 in the cradle frame (x = xr, y = u, z = w)."""
    X0, X1 = TS.CR_XR
    U0, U1 = TS.CR_U
    W0, W1 = TS.CR_W
    IX = TS.WALLS["side_inner_xr"]                                     # 83.35
    IU0, IU1 = TS.WALLS["bottom_u"][1], TS.WALLS["top_u"][0]           # 0 / 101.5
    rt = TS.RIB_T
    add = [diff(box(X0, X1, U0, U1, W0, W1), [box(-IX, IX, IU0, IU1, W0 - 0.01, PLI), box(-IX, IX, IU0, IU1, PLO, W1 + 0.01)])]
    cw0, cw1 = TS.CHANNEL["xr_walls"][0][0], TS.CHANNEL["xr_walls"][1][1]       # -7.3 / 7.3: cross ribs cut at the leg channel
    for ur in TS.CROSS_RIBS_U:
        add.append(box(-IX - 0.01, cw0, ur - rt / 2, ur + rt / 2, PLO - 0.01, W1))
        add.append(box(cw1, IX + 0.01, ur - rt / 2, ur + rt / 2, PLO - 0.01, W1))
    for (a, b) in TS.CHANNEL["xr_walls"]:                             # channel walls start 0.5 inside the clevis cheeks (same shape, no
        add.append(box(a, b, TS.CHANNEL["u"][0] + 0.5, IU1 + 0.01, PLO - 0.01, W1))   # coplanar face with the cheek's u26.2 edge)
    wx0, wx1 = TS.INSP["xr"]
    wu0, wu1 = TS.INSP["u"]
    g, t = 1.8, 2.0                                                    # rib ring 1.8 outside the window (cover ledge 1.5 + 0.3), 2 thick
    add.append(diff(box(wx0 - g - t, wx1 + g + t, wu0 - g - t, wu1 + g + t, PLO - 0.01, W1), [box(wx0 - g, wx1 + g, wu0 - g, wu1 + g, PLO - 0.02, W1 + 0.01)]))
    for pd in TS.PADS:                                                 # pads with the 45 deg chamfer on the +u face (support-free)
        u0p, u1p = pd["u"]
        add.append(prism_x([(u0p, PLO - 0.01), (u1p, PLO - 0.01), (u1p, PLO), (u1p - PAD_CH, W1), (u0p, W1)], pd["xr"][0], pd["xr"][1]))
    bw0, bw1 = TS.BOSS["w"]
    fw = TS.BOSS["fill_to_side_wall"]
    for xr in TS.BOSS["xr"]:
        fx = next(r for r in fw["xr"] if r[0] <= xr <= r[1])
        for u in TS.BOSS["u"]:
            add.append(cyl_z(xr, u, bw0, bw1, TS.BOSS["d"]))
            add.append(box(fx[0] - (0.01 if fx[0] < 0 else 0), fx[1] + (0.01 if fx[1] > 0 else 0), u - fw["width_u"] / 2, u + fw["width_u"] / 2, bw0, bw1))
    hp = TS.HOLD_PAD
    add.append(box(hp["xr"][0], hp["xr"][1], hp["u"][0], hp["u"][1], hp["w"][0], PLI + 0.01))
    ep = ear_poly()
    for s in KN_SIDES:
        e0, e1 = TS.HG[s]["ear"]
        add.append(prism_x(ep, e0, e1))
    cp = clevis_poly()
    add += [prism_x(cp, *TS.CLEVIS["near"]), prism_x(cp, *TS.CLEVIS["far"])]
    cl = TS.LCLIP
    bw = cl["back_w"]
    bt = [(cl["u"][0], PLO - 0.01), (cl["u"][0], bw), (cl["u"][1], bw), (cl["u"][1] + (bw - PLO), PLO - 0.01)]   # clip body + 45 deg buttress (+u)
    for (a, b) in cl["xr_bodies"]:
        add.append(prism_x(bt, a, b))
    lip = cl["catch"]
    add.append(box(cl["xr_bodies"][0][1] - 0.01, cl["xr_bodies"][0][1] + lip, cl["u"][0], cl["u"][1], cl["catch_from_w"], bw))
    add.append(box(cl["xr_bodies"][1][0] - lip, cl["xr_bodies"][1][0] + 0.01, cl["u"][0], cl["u"][1], cl["catch_from_w"], bw))
    cr = union(add)

    ap_w = (0, -1)                                                     # teardrop apex: -u = up in the print (top edge on the bed)
    ap_x = (-1, 0)
    cuts = []
    gr = TS.GROOVE
    cuts.append(box(gr["xr"][0], gr["xr"][1], U0 - 0.01, gr["u"][1], gr["w"][0], W1 + 0.01))
    nt = TS.NOTCH
    cuts.append(box(nt["xr"][0], nt["xr"][1], U0 - 0.01, nt["u"][1] + 0.01, W0 - 0.01, nt["w"][1]))
    cuts.append(box(wx0, wx1, wu0, wu1, PLI - 0.01, PLO + 0.01))
    tx0, tx1 = COVER_TABS
    gd, gh = COVER_GROOVE
    cuts.append(box(tx0 - 0.4, tx1 + 0.4, wu0 - gd, wu0 + 0.01, PLI - 0.01, PLI + gh))          # cover latch grooves (window walls)
    cuts.append(box(tx0 - 0.4, tx1 + 0.4, wu1 - 0.01, wu1 + gd, PLI - 0.01, PLI + gh))
    for xr in TS.BOSS["xr"]:
        for u in TS.BOSS["u"]:
            cuts.append(hole("z", xr, u, TS.BOSS["face_w"] - 0.01, W1 + 0.01, TS.BOSS["hole_d"], apex=ap_w))
            cuts.append(prism_z(tear_cap_pts(xr, u, TS.BOSS["cbore_d"], ap_w, BOSS_CB_CAP), TS.BOSS["seat_w"], W1 + 0.01))
    ch = CR_C2
    cuts.append(prism_x([(U0 - 0.01, W1 - ch), (U0 - 0.01, W1 + 0.01), (U0 + ch, W1 + 0.01)], X0 - 0.01, X1 + 0.01))
    for s in KN_SIDES:
        e0, e1 = TS.HG[s]["ear"]
        cuts.append(hole("x", TS.AX_U, TS.AX_W, e0 - 0.01, e1 + 0.01, 3.3, apex=ap_x))
    pu, pw = TS.LEG_PIVOT_UW
    cuts.append(hole("x", pu, pw, TS.CLEVIS["near"][0] - 0.01, TS.CLEVIS["near"][1] + 0.01, 3.3, apex=ap_x))
    cuts.append(hole("x", pu, pw, TS.CLEVIS["far"][0] - 0.01, TS.CLEVIS["far"][1] + 0.01, 2.5, apex=ap_x))
    return diff(cr, cuts)


def cover_local():
    """E-1 inspection-window cover: plug (window - 0.2, plate 2.5), flange (window + 1.5, 2 thick on w13), dome over the ribbon fold
    (inside xr26.25..39.95 u36.95..50.65 to w15.2, skin 1.2), 2 snap beams along xr (root xr18 in the plug body, free end xr24, 1.0 thick
    in u, w10.5..12.5 with a 0.5 slot under the flange) whose end bumps (0.4 out, 45 deg lead-in and 45 deg removal ramp) catch the
    plate's window-wall grooves. Bending is in u = in the print layer plane; 0.2 interference at the bump centre xr22.3, 4.3 from the root, gives about 1.6 % strain (COVER_SNAP)."""
    wx0, wx1 = TS.INSP["xr"]
    wu0, wu1 = TS.INSP["u"]
    cv = TS.INSP["cover"]
    fl, fit, t = cv["flange"], cv["plug_under"], cv["t"]
    dm = cv["dome"]
    sk = 1.2
    plug = box(wx0 + fit, wx1 - fit, wu0 + fit, wu1 - fit, PLI, PLO + 0.01)
    flange = box(wx0 - fl, wx1 + fl, wu0 - fl, wu1 + fl, PLO, PLO + t)
    dome = box(dm["xr"][0] - sk, dm["xr"][1] + sk, dm["u"][0] - sk, dm["u"][1] + sk, PLO, dm["inner_to_w"] + sk)
    hollow = box(dm["xr"][0], dm["xr"][1], dm["u"][0], dm["u"][1], PLI - 0.1, dm["inner_to_w"])
    tx0, tx1 = COVER_TABS
    bt, bht, slot = COVER_BEAM
    bo, bl = COVER_BUMP
    lead, flat = COVER_BUMP_W
    ub, ut = wu0 + fit, wu1 - fit                                         # plug u faces 33.2 / 68.8
    rel = [box(tx0, tx1 + 1.0, ub - 0.01, ub + 2.0, PLI - 0.01, PLO), box(tx0, tx1 + 1.0, ut - 2.0, ut + 0.01, PLI - 0.01, PLO)]
    w_top = PLI + bht                                                     # beam top w12.5, slot w12.5..13 under the flange
    beams = [box(tx0 - 0.01, tx1, ub, ub + bt, PLI, w_top), box(tx0 - 0.01, tx1, ut - bt, ut, PLI, w_top)]
    wb = PLI + COVER_BUMP_LIFT
    wl, wf, wt = wb + lead, wb + lead + flat, wb + 2 * lead + flat       # 10.95 / 11.00 / 11.40
    bump_lo = [(ub + 0.3, wb), (ub + 0.3, wt), (ub, wt), (ub - bo, wf), (ub - bo, wl), (ub, wb)]        # 0.3 into the beam (no 0.01 slivers)
    bump_hi = [(ut - 0.3, wb), (ut, wb), (ut + bo, wl), (ut + bo, wf), (ut, wt), (ut - 0.3, wt)]
    bumps = [prism_x(_hull2d(bp), tx1 - bl - 0.2, tx1 - 0.2) for bp in (bump_lo, bump_hi)]
    return union([diff(union([plug, flange, dome]), [hollow] + rel)] + beams + bumps)


def leg_capsule(a, b, x0, x1, hole_at=None, apex=None):
    """10 x 6 leg with R3 ends between the axle centre a and the foot centre b (2D (y, z)) over x0..x1, axle hole D3.3."""
    solid = prism_x(_hull2d(tear_pts(a[0], a[1], TS.LEG_T) + tear_pts(b[0], b[1], TS.LEG_T)), x0, x1)
    if hole_at is not None:
        solid = diff(solid, [hole("x", hole_at[0], hole_at[1], x0 - 0.01, x1 + 0.01, 3.3, apex=apex)])
    return solid


def m3_button_x(yc, zc, x_face, length, toward, head=M3_HEAD):
    """ISO 7380 M3 button head bolt along x: head outside x_face, shank `length` toward +1 / -1."""
    hd, hh = head
    if toward > 0:
        return union([cyl_x(yc, zc, x_face - hh, x_face, hd), cyl_x(yc, zc, x_face, x_face + length, 3.0)])
    return union([cyl_x(yc, zc, x_face, x_face + hh, hd), cyl_x(yc, zc, x_face - length, x_face, 3.0)])


def rclip_world():
    """E-2 ribbon clip 30 x 12 x 3 under the clip pad (z58.05..61.05; the ribbon is clamped in the 0.3 gap z61.05..61.35), 2 pins
    D3.0 x 4.5 on the top face (holes D3.1 x 5), power-wire groove x652.6~656.1 x 1.8 along y in the top face."""
    cp = TS.CLIP["pad"]
    z0, z1 = TS.CLIP["clip_z"]
    gv = TS.CLIP["wire_groove"]
    plate = diff(box(cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], z0, z1),
                 [box(gv["x"][0], gv["x"][1], cp["y"][0] - 0.01, cp["y"][1] + 0.01, z1 - gv["depth"], z1 + 0.01)])
    pins = [cyl_z(px, py, z1 - 0.01, z1 + TS.CLIP["pin_len"], TS.CLIP["pin_d"]) for (px, py) in TS.CLIP["pins"]]
    return union([plate] + pins)


def touch_parts(out):
    th = TS.TILT_USE
    src_c = (TS.SRC_SPEC + " C-1~C-18 (받침 좌표 xr·u·w) + " + TS.SRC_NUM + " cradle / hinge / leg / points + " + TS.SRC_DRW
             + " (t03 받침 부품도) + " + TS.SRC_SCR)
    # ---- cradle (use pose + folded altview)
    crl = cradle_local()
    cr = TS.place(crl, th)
    cb = cr.bounding_box()
    pu, pw = TS.LEG_PIVOT_UW
    cl = TS.LCLIP
    out.add("TS-CRADLE", "화면 받침(크래들) — Waveshare 7-DSI-TOUCH-C용", "touchscreen cradle (Waveshare 7-DSI-TOUCH-C)", "print", G_TS, cr,
            COLORS["printed_body"], "PETG", source=src_c,
            note=("사양과 다름(작은 고침): ① 뒤 패드 4개의 +u 면(출력 때 베드 쪽 아래로 향함)을 45° × %.0f 모따기 - 사양 C-17 '패드는 45° 모따기로 "
                  "서포트 없이'; 접혔을 때 받침 발에 얹히는 면은 16 × %.0f (u%.0f~%.0f · u%.0f~%.0f), 뒤 발의 턱(y322.05)과 1.5 이상; ② 다리 클립 몸 "
                  "u%.0f~%.0f의 +u 쪽에 45° 받침(w%.2f → u%.2f에서 뒷판)을 붙임 - 같은 이유, 접은 다리·뚜껑과 닿지 않음; ③ 점검창 벽(뒷판, 창 아래·위 "
                  "가장자리) xr%.0f~%.0f에 덮개 걸쇠 홈 %.1f × 앞쪽 %.1f - 사양 E-1 '걸쇠 2개(모양은 CAD 재량)'의 짝; ④ 귀 붙는 면을 아래 벽 안으로 "
                  "%.2f 넣음(면 겹침 없이 한 몸); ⑤ 아래 뒤 모서리 모따기 C%.0f → C%.1f - C%.0f면 90°에서 경첩 볼과 %.2f (W1 3D 모델도 0.541, 0.59는 2D 값), "
                  "C%.1f로 사양 C-10의 %.2f 이상을 지킴; ⑥ 보스 Ø%.1f 자리파기 물방울 꼭짓점을 축에서 %.1f로 평평하게 자름 - 보스가 R4라 꼭짓점(%.2f)까지 "
                  "파면 살이 %.2f만 남음, 자르면 %.1f (평평한 천장 폭 %.2f 브리지). "
                  "그대로: 바깥 xr±85.35 (x%.2f~%.2f) u-2.5~103.5 w-1~16; 아래 벽 안쪽 u0(유리 얹힘), 위 벽 u101.5(위 틈 0.5), 옆벽 안쪽 xr±83.35(틈 0.3); "
                  "뒷판 w%.1f~%.1f; 보스 Ø8 (xr±77, u6.5 · 94.5) w8~16 + 옆벽까지 폭 8 채움, 구멍 Ø%.1f, 뒤(w16)에서 Ø%.1f 자리파기 → 머리 자리 w%.0f; "
                  "아래 벽 홈 xr48~66 u-2.5~0 w-1~8; 점검창 xr15.5~45 u33~69 + 둘레 갈비 1.8 밖; 누름 패드 xr26.75~39.45 u8~16 w8.6~10.5; 아래 트인 홈 "
                  "xr25.75~44.95 u-2.5~3 w8~16; 가로 갈비 u%s (다리 길 xr±7.3에서 끊음); 다리 길 벽 xr±5.3~7.3 u26.2~; 귀 x%.1f~%.1f · %.1f~%.1f "
                  "(옆모양 = numbers.json ear.profile_uw, 축 (u%.0f, w%.0f) Ø3.3, 뒤꿈치 (u%.2f, w%.2f)); 다리 걸이 가까운 볼 xr%.1f~%.1f Ø3.3 · 먼 볼 "
                  "xr%.1f~%.1f Ø2.5 (×6 막힘 = 볼 폭 6이라 관통), 축 (u%.0f, w%.1f) R%.1f, +u 쪽 밑면 45° (뒷판 w13에서 u%.2f, t03 B-B u38.87); 다리 클립 xr±5.3~8.5 u%.0f~%.0f, 걸림 0.8 (w%.2f~%.2f); "
                  "25°에서 가장 앞 y%.2f, 가장 높은 z%.2f, 가장 뒤 y%.2f"
                  % (PAD_CH, 16 - PAD_CH, TS.PADS[0]["u"][0], TS.PADS[0]["u"][1] - PAD_CH, TS.PADS[1]["u"][0], TS.PADS[1]["u"][1] - PAD_CH,
                     cl["u"][0], cl["u"][1], cl["back_w"], cl["u"][1] + cl["back_w"] - PLO, COVER_TABS[0], COVER_TABS[1], COVER_GROOVE[0],
                     COVER_GROOVE[1], EAR_INTO_WALL, TS.CHAMFER_C2, CR_C2, TS.CHAMFER_C2, C2_GAP_AT_C2, CR_C2,
                     TS.CR["rib_relief_at_cheeks"]["gap_after"], TS.BOSS["cbore_d"], BOSS_CB_CAP, TS.BOSS["cbore_d"] / 2 * math.sqrt(2.0),
                     TS.BOSS["d"] / 2 - TS.BOSS["cbore_d"] / 2 * math.sqrt(2.0), TS.BOSS["d"] / 2 - BOSS_CB_CAP,
                     2 * (TS.BOSS["cbore_d"] / 2 * math.sqrt(2.0) - BOSS_CB_CAP), TS.XC + TS.CR_XR[0], TS.XC + TS.CR_XR[1], PLI, PLO, TS.BOSS["hole_d"], TS.BOSS["cbore_d"],
                     TS.BOSS["seat_w"], "·".join("%.0f" % u for u in TS.CROSS_RIBS_U), TS.hinge_x("left", "ear")[0], TS.hinge_x("left", "ear")[1],
                     TS.hinge_x("right", "ear")[0], TS.hinge_x("right", "ear")[1], TS.AX_U, TS.AX_W, TS.EAR["heel_uw"][0], TS.EAR["heel_uw"][1],
                     TS.CLEVIS["near"][0], TS.CLEVIS["near"][1], TS.CLEVIS["far"][0], TS.CLEVIS["far"][1], pu, pw, TS.CLEVIS["R"], CLEVIS_END_U, cl["u"][0],
                     cl["u"][1], cl["catch_from_w"], cl["back_w"], cb[1], cb[5], cb[4])),
            print_name="화면받침_크래들", R=TS.print_R_top_down(th), folder=FOLDER_TS,
            print_note="윗변(u103.5 면)을 베드에 세워 출력, 귀가 위 (높이 약 0, 사양 119.76). 귀 축·다리 걸이 구멍(x 방향)과 보스 구멍(w 방향)은 "
                       "물방울(꼭짓점 위)로 뽑고 드릴로 다듬음(귀·가까운 볼 Ø3.3, 먼 볼 Ø2.5, 보스 Ø2.8; 보스 자리파기 Ø5.5는 물방울 위를 평평하게 자른 모양, "
                       "%.2f 브리지). 다리 걸이 볼(밑면 45°, 뒷판에서 u38.87)·다리 클립·뒤 패드는 45° 면이라 서포트 없음; 가로 갈비·창 둘레 갈비·보스는 3 mm 이하 짧은 내민 면. 아래 벽(u−2.5~0)의 앞 턱 w−1~10.5(유리가 얹히는 면)는 출력 때 "
                       "지붕이 되므로 그 밑(유리 주머니 안, 앞이 트여 떼기 쉬움)에만 트리 서포트. 약 0 g, 약 3.7시간(W1 추정)" % (2 * (TS.BOSS["cbore_d"] / 2 * math.sqrt(2.0) - BOSS_CB_CAP),),
            dims=[("x", TS.XC + TS.CR_XR[0], TS.XC + TS.CR_XR[1], "받침 폭 170.7 (유리 166.1 + 틈 0.3 + 옆벽 2)", 0),
                  ("x", TS.XC + TS.BOSS["xr"][0], TS.XC + TS.BOSS["xr"][1], "M2.5 보스 154 (화면 구멍)", 1),
                  ("x", TS.XC + TS.INSP["xr"][0], TS.XC + TS.INSP["xr"][1], "점검창 29.5 (u33~69)", 2),
                  ("x", TS.hinge_x("left", "ear")[0], TS.hinge_x("right", "ear")[1], "경첩 귀 8 두 개 (x542.8~550.8 · 671.2~679.2)", 3),
                  ("x", TS.XC + TS.GROOVE["xr"][0], TS.XC + TS.GROOVE["xr"][1], "아래 트인 홈 19.2 (리본 + 전원선)", 4),
                  ("x", TS.XC + TS.NOTCH["xr"][0], TS.XC + TS.NOTCH["xr"][1], "아래 벽 홈 18 (화면 돌기)", 5),
                  ("y", cb[1], cb[4], "25°: 가장 앞 y%.2f → 가장 뒤 y%.2f" % (cb[1], cb[4]), 0),
                  ("z", cb[2], cb[5], "25°: 뒤꿈치 z%.2f → 가장 높은 곳 z%.2f" % (cb[2], cb[5]), 0)])
    p = out[-1]
    q = p.print_solid.bounding_box()
    p.print_note = p.print_note.replace("높이 약 0", "높이 %.2f" % (q[5] - q[2])).replace("약 0 g", "약 %.0f g" % (p.solid.volume() / 1000.0 * 1.27))
    out.add("TS-CRADLE-FOLD", "화면 받침(크래들) - 접은 상태", "touchscreen cradle, folded", "print", G_TSF, TS.place(crl, TS.TILT_FOLD),
            COLORS["printed_body"], "PETG", source=src_c + "; C-16 접은 상태 (90°: y233.05~339.05, z78.35~95.35) - 같은 부품의 다른 자세",
            note=ALT, print_name="화면받침_크래들", folder=FOLDER_TS, no_print=True)

    # ---- leg (use pose in the world, folded = stowed on the cradle back)
    A = TS.LEG_AX_YZ
    tip = TS.LEG_TIP_YZ
    lx0, lx1 = TS.LEG_X
    leg = leg_capsule(A, tip, lx0, lx1, hole_at=A, apex=TS.LEG_N)
    Rleg = [[1, 0, 0], [0, TS.LEG_DIR[0], TS.LEG_DIR[1]], [0, TS.LEG_N[0], TS.LEG_N[1]]]
    src_l = TS.SRC_SPEC + " D (10 × 6, 축 구멍 Ø3.3 중심 → 발끝 중심 67, 양 끝 R3 = 전체 73) + " + TS.SRC_NUM + " leg (pivot_cradle_uw, tip_yz, swing)"
    out.add("TS-LEG", "받침다리", "touchscreen support leg", "print", G_TS, leg, COLORS["printed_body"], "PETG", source=src_l,
            note="사용 상태: 축 = 받침 (u%.0f, w%.1f)을 25°로 돌린 (y%.2f, z%.2f), 발끝 (y%.2f, z%.2f) → 축~발끝 %.2f, 수평 아래 %.2f°; 발(R3)은 주머니 바닥 "
                 "z%.2f와 뒷벽 y%.1f에 닿음. 넣고 뺄 때는 화면을 22°(뒤꿈치)에 댄 채 (사양 D: 25°에서 내리면 뒷벽 위 모서리를 0.66 긁음); 자석 없음"
                 % (pu, pw, A[0], A[1], tip[0], tip[1], TS.LEG_LEN_MODEL, TS.LEG_ANGLE, TS.POCKET["bottom_z"], TS.POCKET["back_wall_y"]),
            print_name="받침다리", R=Rleg, folder=FOLDER_TS,
            print_note="넓은 면(73 × 10)을 베드에 눕혀 출력(높이 6). 축 구멍 Ø3.3은 물방울(꼭짓점 위)로 뽑고 드릴 Ø3.3로 다듬음. 벽 4줄 이상(속 거의 꽉). "
                       "약 5 g, 약 20분",
            dims=[("x", lx0, lx1, "다리 폭 10 (볼 사이 틈 0.3씩)", 0), ("y", A[0], tip[0], "축 y%.2f → 발끝 y%.1f" % (A[0], tip[0]), 0),
                  ("z", tip[1], A[1], "발끝 z%.2f → 축 z%.2f (%.2f°)" % (tip[1], A[1], TS.LEG_ANGLE), 0)])
    leg_f = leg_capsule((pu, pw), (pu + TS.LEG_L, pw), TS.LG["xr"][0], TS.LG["xr"][1], hole_at=(pu, pw))
    out.add("TS-LEG-FOLD", "받침다리 - 접은 상태 (받침 뒤 클립)", "support leg, stowed", "print", G_TSF, TS.place(leg_f, TS.TILT_FOLD),
            COLORS["printed_body"], "PETG", source=src_l + "; 접은 상태: 받침 뒤 w13.5~19.5, u27~100 (클립 u87~93)",
            note=ALT, print_name="받침다리", folder=FOLDER_TS, no_print=True)

    # ---- inspection-window cover (use + folded)
    cvl = cover_local()
    cov = TS.place(cvl, th)
    cvd = TS.INSP["cover"]
    src_v = TS.SRC_SPEC + " C-5 (창 xr15.5~45 u33~69) + E-1 (끼움부 = 창 − 0.2, 두께 = 뒷판 2.5, 턱 1.5 크게 두께 2, 볼록 자리 안 w15.2, 걸쇠 2개) + t05"
    out.add("TS-WINCOVER", "점검창 덮개 (리본 접힘 자리 볼록)", "inspection-window cover (domed over the ribbon fold)", "print", G_TS, cov,
            COLORS["printed_body"], "PETG", source=src_v,
            note="사양 그대로: 끼움부 xr%.1f~%.1f u%.1f~%.1f w%.1f~%.1f, 턱 xr%.1f~%.1f u%.1f~%.1f w%.0f~%.0f, 볼록 자리 안 xr%.2f~%.2f u%.2f~%.2f (w%.1f까지, 살 1.2 → "
                 "바깥 w%.1f); 추정(사양 E-1 '걸쇠 2개, 모양은 CAD 재량'): 걸쇠 = 끼움부 아래·위 끝의 xr 방향 탄성 보 2개 (뿌리 xr%.0f = 끼움부 몸, "
                 "자유 끝 xr%.0f, 두께 %.1f (u) × 높이 %.1f (w%.1f~%.1f), 뒤·끝 틈 1, 턱 밑 틈 %.1f) 끝 쪽 xr%.1f~%.1f의 돌기 %.1f (45° 들어가는 경사 + 45° 빼는 경사, "
                 "높이 w%.2f~%.2f)가 뒷판 창 벽 홈 %.1f × %.1f에 걸림; 끼움 %.1f, 휨은 출력 층 안(u) 방향, 변형률 약 %.1f%% (PETG 항복 3~4%%보다 작게) - "
                 "처음 안(뒷판 쪽 w 방향 혀, 길이 2.1)은 약 6.8%%라 금 갈 위험으로 바꿈"
                 % (TS.INSP["xr"][0] + cvd["plug_under"], TS.INSP["xr"][1] - cvd["plug_under"], TS.INSP["u"][0] + cvd["plug_under"],
                    TS.INSP["u"][1] - cvd["plug_under"], PLI, PLO, TS.INSP["xr"][0] - cvd["flange"], TS.INSP["xr"][1] + cvd["flange"],
                    TS.INSP["u"][0] - cvd["flange"], TS.INSP["u"][1] + cvd["flange"], PLO, PLO + cvd["t"], cvd["dome"]["xr"][0], cvd["dome"]["xr"][1],
                    cvd["dome"]["u"][0], cvd["dome"]["u"][1], cvd["dome"]["inner_to_w"], cvd["dome"]["inner_to_w"] + 1.2, COVER_TABS[0], COVER_TABS[1],
                    COVER_BEAM[0], COVER_BEAM[1], PLI, PLI + COVER_BEAM[1], COVER_BEAM[2], COVER_TABS[1] - 0.2 - COVER_BUMP[1], COVER_TABS[1] - 0.2,
                    COVER_BUMP[0], PLI + COVER_BUMP_LIFT, PLI + COVER_BUMP_LIFT + 2 * COVER_BUMP_W[0] + COVER_BUMP_W[1], COVER_GROOVE[0], COVER_GROOVE[1], COVER_SNAP[0],
                    COVER_SNAP[1] * 100.0),
            print_name="점검창덮개", R=TS.print_R_w_down(th), folder=FOLDER_TS,
            print_note="끼움부 면(w10.5, 볼록 자리 속이 열린 면)을 베드에, 턱·볼록 자리가 위. 턱은 끼움부보다 1.7 내밀어 짧은 내민 면, 볼록 자리 천장은 "
                       "13.7 브리지, 걸쇠 보 위 턱은 2 × 7 브리지 - 서포트 없음. 걸쇠 보는 벽 2줄(0.42) 이상으로 꽉 채움. 약 0 g",
            dims=[("x", TS.XC + TS.INSP["xr"][0] - cvd["flange"], TS.XC + TS.INSP["xr"][1] + cvd["flange"], "턱 32.5 (창 29.5 + 1.5씩)", 0),
                  ("x", TS.XC + cvd["dome"]["xr"][0] - 1.2, TS.XC + cvd["dome"]["xr"][1] + 1.2, "볼록 16.1", 1)])
    p = out[-1]
    p.print_note = p.print_note.replace("약 0 g", "약 %.0f g" % (p.solid.volume() / 1000.0 * 1.27))
    out.add("TS-WINCOVER-FOLD", "점검창 덮개 - 접은 상태", "inspection-window cover, folded", "print", G_TSF, TS.place(cvl, TS.TILT_FOLD),
            COLORS["printed_body"], "PETG", source=src_v, note=ALT, print_name="점검창덮개", folder=FOLDER_TS, no_print=True)

    # ---- ribbon clip under the lid
    rc = rclip_world()
    cp = TS.CLIP["pad"]
    gv = TS.CLIP["wire_groove"]
    out.add("TS-RCLIP", "리본 클립 (뚜껑 밑, 전원선 홈)", "DSI ribbon clip under the lid (power-wire groove)", "print", G_TS, rc, COLORS["printed_body"], "PETG",
            source=TS.SRC_SPEC + " A-5 (클립 덩어리, 밑에서 Ø3.1 × 5 구멍 2개) + E-2 (30 × 12 × 3, z58.05~61.05, 핀 Ø3 × 4.5, 전원선 홈 x652.6~656.1 깊이 1.8) + t05",
            note="사양 그대로: 판 x%.2f~%.2f y%.2f~%.2f z%.2f~%.2f, 핀 Ø%.1f × %.1f (%s, 구멍 Ø%.1f × %.0f보다 0.5 짧음), 전원선 홈 x%.1f~%.1f 깊이 %.1f "
                 "(y 방향 끝까지); 리본(x640.50~652.20)은 평평한 면이 뚜껑 밑면 z61.35에 눌러 잡음 (틈 0.3 = 리본 두께); 핀이 헐거우면 순간접착제 한 방울"
                 % (cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], TS.CLIP["clip_z"][0], TS.CLIP["clip_z"][1], TS.CLIP["pin_d"], TS.CLIP["pin_len"],
                    " · ".join("(%.2f, %.2f)" % tuple(q_) for q_ in TS.CLIP["pins"]), TS.CLIP["pin_hole_d"], TS.CLIP["pin_hole_depth"],
                    gv["x"][0], gv["x"][1], gv["depth"]),
            print_name="리본클립", R=R_NONE, folder=FOLDER_TS,
            print_note="넓은 면(30 × 12)을 베드에, 핀·전원선 홈이 위. 서포트 없음. 약 1 g",
            dims=[("x", cp["x"][0], cp["x"][1], "30 (핀 간격 24)", 0), ("y", cp["y"][0], cp["y"][1], "12", 0),
                  ("z", TS.CLIP["clip_z"][0], TS.CLIP["clip_z"][1] + TS.CLIP["pin_len"], "3 + 핀 4.5", 0)])

    # ---- optional screen cover (only used folded -> altview group, but printed)
    sx, sy_, st = SCREEN_COVER
    fy0, fy1 = TS.pt(TS.CR_U[0], 0, TS.TILT_FOLD)[0], TS.pt(TS.CR_U[1], 0, TS.TILT_FOLD)[0]
    fyc = (fy0 + fy1) / 2.0
    ztop = TS.pt(0, TS.CR_W[0], TS.TILT_FOLD)[1]                  # 95.35: cradle rim (w-1) folded
    scov = box(TS.XC - sx / 2, TS.XC + sx / 2, fyc - sy_ / 2, fyc + sy_ / 2, ztop, ztop + st)
    out.add("TS-SCREENCOVER", "화면 덮개 (선택, 접은 화면 위)", "screen cover (optional, on the folded screen)", "print", G_TSF, scov,
            COLORS["printed_body"], "PETG",
            source=TS.SRC_SPEC + " E-3 (선택: 화면 덮개 173×108×3, 접은 화면 위, 받침 테두리에 얹힘); 자리 x%.1f~%.1f y%.2f~%.2f z%.2f~%.2f "
                   "(접은 받침 테두리 z%.2f 위, 가운데 맞춤)" % (TS.XC - sx / 2, TS.XC + sx / 2, fyc - sy_ / 2, fyc + sy_ / 2, ztop, ztop + st, ztop),
            note=ALT, print_name="화면덮개_선택", R=R_NONE, folder=FOLDER_TS,
            print_note="선택 부품(접은 화면을 덮을 때만). 평판을 베드에. 약 70 g. 사용 상태 조립에는 없음(접은 상태 보기에만 있음)",
            dims=[("x", TS.XC - sx / 2, TS.XC + sx / 2, "173", 0), ("y", fyc - sy_ / 2, fyc + sy_ / 2, "108", 0), ("z", ztop, ztop + st, "3", 0)])

    # ---- screws (bought)
    src_s = TS.SRC_SPEC + " A-1 (나사는 바깥쪽 가까운 볼에서, 먼 볼 Ø2.5 × 8 직접 탭, 물림 7.6) + t05 표 (M3×20 4개: 경첩 2 + 다리 축 1 + 예비 1)"
    for s in KN_SIDES:
        n0, n1 = TS.hinge_x(s, "near_cheek")
        f0, f1 = TS.hinge_x(s, "far_cheek")
        if TS.HG[s]["screw_from"] == "-x":
            scr = m3_button_x(TS.AX_Y, TS.AX_Z, n0, 20.0, +1)
            bite = (n0 + 20.0) - f0
        else:
            scr = m3_button_x(TS.AX_Y, TS.AX_Z, n1, 20.0, -1)
            bite = f1 - (n1 - 20.0)
        out.add("TS-M3X20-HINGE-%s" % s[0].upper(), "M3×20 둥근머리 렌치볼트 (화면 경첩 축 %s)" % ("왼쪽" if s == "left" else "오른쪽"),
                "M3x20 button head bolt (hinge axle %s)" % s, "bought", G_TS, scr, COLORS["stainless"], "SUS304", source=src_s,
                note="사양 그대로: ISO 7380 머리 Ø5.7 × 1.65, %s 쪽 가까운 볼(x%.1f~%.1f)에서 넣어 먼 볼(x%.1f~%.1f) Ø2.5에 %.1f 물림 (축 y%.2f z%.2f), "
                     "육각 L렌치 2.0; 머리가 볼에 닿은 뒤 약 1/4바퀴 풀어 둠 (귀가 제 무게로 돌아야 함, PETG 탭 마찰로 풀리지 않음)"
                     % (TS.HG[s]["screw_from"], n0, n1, f0, f1, bite, TS.AX_Y, TS.AX_Z))
    ax = TS.LG["axle"]
    lg = TS.place(m3_button_x(pu, pw, TS.CLEVIS["near"][0], ax["L"], +1), th)
    out.add("TS-M3X20-LEG", "M3×20 둥근머리 렌치볼트 (받침다리 축)", "M3x20 button head bolt (leg axle)", "bought", G_TS, lg, COLORS["stainless"],
            "SUS304", source=TS.SRC_SPEC + " C-13 (가까운 볼 xr-9.3~-5.3 Ø3.3 관통 → 먼 볼 xr5.3~11.3 Ø2.5, 물림 5.4; −x에서 넣음, 머리 Ø5.7 × 1.65)",
            note="사양 그대로: 몸통 xr%.1f~%.1f (x%.1f~%.1f), 먼 볼에 %.1f 물림, 머리는 가까운 볼 바깥 면 xr%.1f에; 예비 1개는 모델에 없음; "
                 "머리가 볼에 닿은 뒤 약 1/4바퀴 풀어 둠 (다리가 제 무게로 돌아야 함)"
                 % (TS.CLEVIS["near"][0], TS.CLEVIS["near"][0] + ax["L"], TS.XC + TS.CLEVIS["near"][0], TS.XC + TS.CLEVIS["near"][0] + ax["L"],
                    TS.CLEVIS["near"][0] + ax["L"] - TS.CLEVIS["far"][0], TS.CLEVIS["near"][0]))
    k = 0
    sw = TS.BOSS["seat_w"]
    for xr in TS.BOSS["xr"]:
        for u in TS.BOSS["u"]:
            k += 1
            scr = union([cyl_z(xr, u, sw, sw + M25_HEAD[1], M25_HEAD[0]), cyl_z(xr, u, sw - M25_LEN, sw, 2.5)])
            out.add("TS-M25-%d" % k, "M2.5×6 둥근머리 나사 (화면 모서리 구멍 %d)" % k, "M2.5x6 screw (screen corner hole %d)" % k, "bought", G_TS,
                    TS.place(scr, th), COLORS["stainless"], "강",
                    source=TS.SRC_SPEC + " C-3 (보스 Ø8 w8~16, 구멍 Ø2.8, 뒤에서 Ø5.5 자리파기 → 머리 자리 w11, M2.5×6 물림 3)",
                    note="추정: 머리 Ø%.1f × %.1f; 몸통 w%.0f~%.0f → 화면 구멍(w8부터)에 %.0f 물림; 구멍 깊이는 받은 화면에서 잼 (사양 G-2: 물림 = min(깊이 − 0.5, 4), "
                         "얕으면 와셔); xr%.0f u%.1f" % (M25_HEAD[0], M25_HEAD[1], sw - M25_LEN, sw, TS.BOSS["face_w"] - (sw - M25_LEN), xr, u))


# ------------------------------------------------------------------ printed back plate (I/O + louvres)

BP_Z = (Z_BOT, Z_LIDU)
BP_SKIN = 2.0
BP_HOLES = {k: tuple(v) for k, v in BP["holes_xz"].items()}   # cable_pass_D12, usb_c_pd_input_HUSB238, rocker_KCD1, pedal_jack_J501_D6
BP_LOUV = [(z, z + 3.0) for z in (18.0, 23.0, 28.0, 33.0, 38.0, 43.0)]   # louvre slots x480..534 (spec x480~536, z18~46)
BP_LOUV_X = (480.0, 534.0)
BP_TABS = [(400.0, 414.0, 407.0, 322.0), (452.0, 474.0, 466.0, 311.5)]   # bottom tabs x0, x1, screw x, screw y (y316..skin, z16.5..20.5)
BP_TAB_Y0 = 316.0                                               # tab front y (left screw y322: 9 from the floor's back edge y331 at 40)
# right tab: the J501 ledge (x449..476.5 y315.5..339.5 z30..36.4, same print) covers the whole tab x452..474, so a screw there cannot
# be driven (review 2026-10-01: first material 9.5 over the head). A tongue x459.5..472.5 runs forward to y304 and carries the screw
# at y311.5: its D6 driver path (y308.5..314.5) passes 1.0 in front of the ledge / J501 board; the tongue stays 6.5 off the fuse
# cradle (x<=453) and 1.5 off the fuse lead riser (x456.5). Not a hole through the ledge: that leaves a 2 mm strip at the ledge front
# edge and puts the screw under the glued J501 board (no service access).
BP_TONGUE = (459.5, 472.5, 304.0)                               # right-tab tongue x0, x1, front y
BP_WEBS = (452.0, 472.0)                                        # J501-ledge webs x (2 wide, skin -> ledge, over the tab x452..474)
DRIVER_D, DRIVER_L = 6.0, 80.0                                  # driver shaft used by check_body's screw-access test


def back_plate(out):
    x0, x1 = BP_X
    z0, z1 = BP_Z
    ys = YB - BP_SKIN                                               # 340.5 skin inner face (40 deg)
    pcx, pcz = BP_HOLES["cable_pass_D12"]
    ux, uz = BP_HOLES["usb_c_pd_input_HUSB238"]
    kx, kz = BP_HOLES["rocker_KCD1_13.2x19.2"]
    jx, jz = BP_HOLES["pedal_jack_J501_D6"]
    pd = CC["CU-E-PDTRIG"]
    jb = CC["CU-E-J501BOARD"]
    add = [box(x0, x1, ys, YB, z0, z1),                                                   # outer skin 2
           box(x0, x1, YBI, YB, z1 - 4.0, z1), box(x0, x1, YBI, YB, z0, z0 + 1.5),        # top frame 4, bottom frame 1.5
           box(x0, x0 + 2.0, YBI, YB, z0, z1), box(x1 - 2.0, x1, YBI, YB, z0, z1),        # side frames 2
           box(kx - 10.5, kx + 10.5, ys - 2.0, ys + 0.01, kz - 13.5, kz + 13.5),          # switch panel (2 behind the skin)
           box(ux - 8.5, ux + 8.5, YBI, ys + 0.01, uz - 5.0, uz + 5.0),                   # PD-trigger pocket block
           box(jb[0] - 1.0, jb[1] + 1.5, jb[2], ys + 0.01, 30.0, jb[4]),                  # J501 board ledge (top = board underside)
           ]
    for gx in BP_WEBS:                                  # ledge webs: rise straight from the skin in print (no overhang), tie ledge <-> tab
        add.append(box(gx, gx + 2.0, 320.0, ys + 0.01, 20.5 - 0.01, 30.01))
    for (a, b, sx, sy) in BP_TABS:
        add.append(box(a, b, BP_TAB_Y0, ys + 0.01, z0, 20.5))
    add.append(box(BP_TONGUE[0], BP_TONGUE[1], BP_TONGUE[2], BP_TAB_Y0 + 0.01, z0, 20.5))   # right-tab tongue (screw out of the ledge shadow)
    plate = union(add)
    cuts = [cyl_y(pcx, pcz, YBI - 0.01, YB + 0.01, 12.0)]
    cuts += [stadium_y(ux, uz, 13.0, 7.5, ys - 0.01, YB + 0.01),
             box(pd[0] - 0.2, pd[1] + 0.2, YBI - 0.01, pd[3], pd[4] - 0.2, pd[5] + 0.2)]        # USB-C mouth + board pocket
    cuts += [box(kx - 6.6, kx + 6.6, ys - 2.01, YB + 0.01, kz - 9.6, kz + 9.6),
             box(kx - 7.7, kx + 7.7, ys, YB + 0.01, kz - 10.7, kz + 10.7)]                      # KCD1 13.2 x 19.2 + 2 mm bezel recess
    cuts.append(cyl_y(jx, jz, ys - 0.01, YB + 0.01, 6.3))
    cuts += [box(BP_LOUV_X[0], BP_LOUV_X[1], ys - 0.01, YB + 0.01, za, zb) for (za, zb) in BP_LOUV]
    for (a, b, sx, sy) in BP_TABS:
        cuts.append(csk_z(sx, sy, 20.5, z0 - 0.01))
    plate = diff(plate, cuts)
    out.add("PR-BACKPLATE", "뒤판 출력물 (I/O·루버 판)", "printed back plate (I/O + louvres)", "print", G_CUP, plate, COLORS["printed_body"], PETG,
            source=SRC + " centre.back_plate_io (x397.5~538 y%.0f~%.1f z16.5~61.35; 구멍 x/z: 케이블 통과 Ø12 (405, 38), USB-C PD 입력 (421, 38), "
                         "KCD1 13.2×19.2 (438.5, 38.5) 2 mm 오목 자리에 테두리 → y%.1f와 같은 면, J501 Ø6 (462.5, 40.5); 루버 x480~536 z18~46) + "
                         "centre_contents CU-E-PDTRIG / CU-E-J501BOARD / CU-E-SWITCH" % (YBI, YB, YB),
            note=("" if abs(DY_BACK) < 1e-9 else "사양과 다름(작은 고침): 판에 얹히는 HUSB238·J501 기판·J501·KCD1 자리와 판 주머니·잭 받침을 사양 상자보다 "
                 "y+%.1f (뒤판이 %.0f° 규칙으로 y%.1f → %.1f로 옮겨 감; 사양 그대로면 USB-C 입구 앞을 판 %.1f mm가 막음); " % (
                     DY_BACK, ANGLE, LAYOUT_BACK_Y, YB, DY_BACK)) + "추정: 바깥 판 2 (y%.1f~%.1f) + 테 (위 4 · 아래 1.5 · 옆 2)" % (ys, YB) + " - 뚜껑 L·화면 뚜껑이 윗면에 얹혀 누름; KCD1은 2 mm 판에 끼우고 "
                 "테두리(15.4×21.4)는 바깥면과 같은 높이; USB-C 입구 13 × 7.5 (바깥 판), HUSB238 주머니 x%.1f~%.1f z%.1f~%.1f (입구가 바깥면에서 2 "
                 "안); J501 기판 받침 x%.0f~%.1f y%.1f~%.1f 윗면 z%.1f (기판 밑) + 세운 받침벽 2 (x%s, 2 두께, y320~%.1f z20.5~30: 바깥 판에서 곧게 "
                 "올라 받침과 뒤 탭을 이음 - 출력 때 내민 면 없음); 루버 x%.0f~%.0f (사양 536 → 옆 테 2를 남김) z18~46 3×6; 바닥 탭 2개 (x400~414, "
                 "452~474, y%.0f~%.1f, z16.5~20.5)에 접시 8호 13 mm를 아랫판으로: 왼쪽 (%.0f, %.0f) (아랫판 뒤 모서리 y%.0f에서 %.0f), 오른쪽은 J501 받침이 "
                 "탭 전체를 덮어 드라이버가 닿지 않으므로 탭에서 앞으로 낸 혀 x%.1f~%.1f y%.0f~316의 (%.0f, %.1f) - 드라이버 Ø6 길이 받침·J501 기판 앞 "
                 "1.0 (check_body.py가 나사마다 Ø6 × 80 드라이버 길을 확인) - 창 옆은 틈 없이 끼움"
                 % (pd[0] - 0.2, pd[1] + 0.2, pd[4] - 0.2, pd[5] + 0.2, jb[0] - 1.0, jb[1] + 1.5, jb[2], ys, jb[4],
                    "/".join("%.0f~%.0f" % (g, g + 2) for g in BP_WEBS), ys, BP_LOUV_X[0], BP_LOUV_X[1], BP_TAB_Y0, ys,
                    BP_TABS[0][2], BP_TABS[0][3], YBI, YBI - BP_TABS[0][3], BP_TONGUE[0], BP_TONGUE[1], BP_TONGUE[2], BP_TABS[1][2], BP_TABS[1][3]),
            print_name="뒤판출력물_IO", R=R_YMAX,
            print_note="바깥면(y%.1f)을 베드에. 구멍·루버는 수직, 스위치 테두리 자리 2 mm는 베드 쪽 오목(작은 브리지). 잭 받침·탭·오른쪽 탭의 "
                       "혀(탭보다 좁음)는 위로 섬 - 서포트 없음. 벽 3줄 + 채움 25 %%" % YB,
            dims=[("x", x0, x1, "140.5 (창 x397.5~538)", 0), ("x", x0, pcx, "케이블 통과 x405 Ø12", 1), ("x", x0, ux, "USB-C x421", 2),
                  ("x", x0, kx, "KCD1 x438.5", 3), ("x", x0, jx, "J501 x462.5 Ø6.3", 4), ("x", BP_LOUV_X[0], BP_LOUV_X[1], "루버 54", 5),
                  ("y", YBI, YB, "11.5", 0), ("y", ys, YB, "바깥 판 2", 1), ("y", jb[2], YBI, "잭 받침 %.1f 앞으로" % (YBI - jb[2]), 2),
                  ("y", BP_TONGUE[2], YB, "오른쪽 탭 혀 y%.0f (나사 y%.1f)" % (BP_TONGUE[2], BP_TABS[1][3]), 3),
                  ("z", z0, z1, "44.85 (z16.5~61.35)", 0), ("z", z0, 38.0, "구멍 중심 z38", 1), ("z", 18.0, 46.0, "루버 z18~46", 2)])


# ------------------------------------------------------------------ hub shelf (+ amp pads), power-bank holder, XT30 clips

AMP_HOLES = [(745.5, 286.5), (792.5, 286.5), (745.5, 325.5), (792.5, 325.5)]   # XH-A232 54 x 46, holes 3.5 in (v3 amp_bosses)
SHELF_SCREW_Z = 46.0                     # bracket screw axis (D3 x 12~13 pan head, head D6 or less, seat D6.5 x 4)
SHELF_GROOVE = (7.0, 0.8)                # relief groove in the shelf top in front of each bracket: width, depth (floor 1.2 left)


def hub_shelf(out):
    sh = CC["PR-HUBSHELF"]
    b1, b2 = CC["PR-SHELFBRK-1"], CC["PR-SHELFBRK-2"]
    zt = sh[5]
    add = [box(sh[0], sh[1], sh[2], sh[3], sh[4], zt), box(b1[0], b1[1], b1[2], YBI, b1[4], b1[5]), box(b2[0], b2[1], b2[2], YBI, b2[4], b2[5]),
           box(sh[0], sh[1], sh[3] - 0.01, YBI, sh[4], zt)]                            # shelf back strip to the back ply
    add += [cyl_z(x, y, zt - 0.01, zt + 2.0, 7.0) for (x, y) in AMP_HOLES]
    m = union(add)
    cuts = [cyl_z(x, y, sh[4] - 0.01, zt + 2.01, 2.7) for (x, y) in AMP_HOLES]
    for b in (b1, b2):
        cx = (b[0] + b[1]) / 2.0
        cb_ = diff(hole("y", cx, SHELF_SCREW_Z, b[2] - 0.01, b[2] + 4.0, 6.5, apex=(0, 1)),
                   [box(cx - 5.0, cx + 5.0, b[2] - 1.0, b[2] + 5.0, b[5] - 0.8, b[5] + 2.0)])
        cuts += [hole("y", cx, SHELF_SCREW_Z, b[2] - 0.01, YBI + 0.01, 3.4, apex=(0, 1)), cb_]      # head seat capped 0.8 under the top z50
        # head / driver relief groove in the shelf top in front of the bracket (review 2026-10-01: the D6 head on the z46 axis reaches
        # z43.0, 0.5 below the shelf top z43.5, and scraped the shelf for ~12 mm while the screw was driven)
        cuts.append(box(cx - SHELF_GROOVE[0] / 2.0, cx + SHELF_GROOVE[0] / 2.0, sh[2] - 0.01, b[2] + 0.01, zt - SHELF_GROOVE[1], zt + 0.01))
    m = diff(m, cuts)
    out.add("PR-HUBSHELF", "허브 위 선반 + 뒤판 받침 2 + 앰프 받침 4 (출력)", "hub shelf with 2 brackets and 4 amp pads (printed)", "print", G_CUP, m,
            COLORS["printed_body"], PETG,
            source=SRC + " centre_contents PR-HUBSHELF (224×47×2, x688~912 y282~329 z41.5~43.5) + PR-SHELFBRK-1/2 (x688~698 / 902~912, y322~330, "
                         "z41.5~50, 뒤판에 나사) + CU-E-AMP (앰프 2 mm 받침 위 z45.5) + printed_parts PR-HUBSHELF",
            note="추정: 선반 뒤 %.0f mm(y%.0f~%.0f)를 뒤판까지 이어 한 몸, 앰프 받침 Ø7 × 2 (구멍 Ø2.7 관통, 앰프 구멍 3.5 안쪽 가정 = v3 amp_bosses, "
                 "받은 앰프로 재서 옮김) - 사양 STANDOFFS의 '앰프 2 mm 받침'을 선반에 붙임; 받침마다 뒤판으로 Ø3 × 12~13 둥근머리 목재 나사 (머리 Ø6 이하; "
                 "x%s z%.0f, 구멍 Ø3.4, 머리 자리 Ø6.5 × 4 눈물방울 - 꼭지를 윗면 0.8 아래 z49.2에서 자름 → 합판 물림 약 9); 머리(아래 끝 z%.1f)가 선반 "
                 "윗면 z%.1f보다 낮아 받침 앞 선반 윗면에 머리·드라이버 길 홈 %.0f × %.1f (y%.0f~%.0f, 바닥 %.1f 남음) - 나사를 조일 때 머리가 선반을 긁지 않음. "
                 "8호(Ø4.2, 머리 Ø8)는 10 × 8 받침에 들어가지 않음; 허브 윗면 z40.5와 1 mm (처지면 허브가 받침)"
                 % (YBI - sh[3], sh[3], YBI, "/".join("%.0f" % ((b[0] + b[1]) / 2) for b in (b1, b2)), SHELF_SCREW_Z, SHELF_SCREW_Z - 3.0, zt,
                    SHELF_GROOVE[0], SHELF_GROOVE[1], sh[2], b1[2], zt - sh[4] - SHELF_GROOVE[1]),
            print_name="허브선반", R=R_NONE,
            print_note="선반 밑면(z41.5)을 베드에, 받침·앰프 받침이 위. 서포트 없음 (뒤판 나사 구멍은 눈물방울, 머리 길 홈은 윗면)",
            dims=[("x", sh[0], sh[1], "224", 0), ("x", AMP_HOLES[0][0], AMP_HOLES[1][0], "앰프 구멍 47", 1),
                  ("y", sh[2], YBI, "%.0f (y%.0f~%.0f)" % (YBI - sh[2], sh[2], YBI), 0), ("y", AMP_HOLES[0][1], AMP_HOLES[2][1], "앰프 구멍 39", 1),
                  ("z", sh[4], b1[5], "z41.5~50", 0), ("z", sh[4], zt, "선반 2", 1), ("z", zt, zt + 2.0, "앰프 받침 2", 2)])


PB_SCREWS = [(289.0, 272.0), (388.0, 272.0), (289.0, 307.0), (388.0, 307.0)]   # csk 8호 13 into the floor: >= 10 from the foot screws
PB_FLOOR = 2.0                                                                  # holder floor (screw heads flush with its top)


def pb_holder(out):
    x0, x1, y0, y1, z0, z1 = CC["CU-PBHOLDER"]
    w, fl = 1.5, PB_FLOOR
    add = [box(x0, x1, y0, y1, z0, z0 + fl), box(x0, x0 + w, y0, y1, z0, z1), box(x1 - w, x1, y0, y1, z0, z1),
           box(x0, x1, y0, y0 + w, z0, z1), box(x0, x1, y1 - w, y1, z0, z1)]
    m = union(add)
    xm = (x0 + x1) / 2.0
    pz = CC["Z-BANK-PLUG"]
    cuts = [box(pz[0] - 0.5, x1 + 0.01, pz[2] - 2.0, y1 + 0.01, pz[4] - 0.5, z1 + 0.01),               # plug / cable notch in the +x corner
            box(xm - 11.0, xm + 11.0, y0 - 0.01, y0 + w + 0.01, z0 + fl, z0 + fl + 3.0),           # strap slots 22 x 3
            box(xm - 11.0, xm + 11.0, y1 - w - 0.01, y1 + 0.01, z0 + fl, z0 + fl + 3.0)]
    cuts += [csk_z(x, y, z0 + fl, z0 - 0.01) for (x, y) in PB_SCREWS]
    m = diff(m, cuts)
    bank = CC["PB-E-BANK"]
    out.add("CU-PBHOLDER", "보조배터리 받침 (바닥 2, 벽 1.5 × 14, 끈 구멍)", "power-bank holder (printed tray)", "print", G_CUP, m,
            COLORS["printed_body"], PETG,
            source=SRC + " centre_contents CU-PBHOLDER (x284~393 y252~327 z16.5~30.5, 바닥 2, 벽 1.5 × 14, 끈 구멍) + PB-E-BANK (Morui MT-65 "
                         "105×71×32, 선택 O07, USB-C 끝 +x) + Z-BANK-PLUG",
            note="추정: 배터리 둘레 0.5 틈 (배터리 x%.0f~%.0f y%.0f~%.0f), +x 벽과 뒤 벽 끝(x390.5~)은 ㄱ자 USB-C 플러그·선 자리(Z-BANK-PLUG "
                 "z26~43)에서 0.5 띄워 y276부터 z25.5로 낮춤, 끈 구멍 22 × 3 (앞·뒤 벽 바닥, 20 mm 벨크로가 배터리 밑·위를 감음 - BOM에 없음), 바닥 접시 8호 13 mm 4곳 %s "
                 "(모서리 y257/322가 아님: 가운데 아랫판의 고무발 나사 (292, 262)·(292, 320)와 축 사이 10 이상)"
                 % (bank[0], bank[1], bank[2], bank[3], " · ".join("(%.0f, %.0f)" % q for q in PB_SCREWS)),
            print_name="보조배터리받침", R=R_NONE, print_note="바닥을 베드에. 끈 구멍은 브리지 22. 서포트 없음",
            dims=[("x", x0, x1, "109", 0), ("x", bank[0], bank[1], "배터리 105", 1), ("y", y0, y1, "75", 0), ("y", bank[2], bank[3], "배터리 71", 1),
                  ("z", z0, z1, "14", 0), ("z", z0, z0 + fl, "바닥 2", 1)])


def xt30_clips(out):
    for side in "LR":
        pk = XT30_POCKET[side]
        wy, wz = END_HOLE_YZ[side]                                   # plate hole = end-wall hole, coaxial with the pocket (L) / 1.5 under (R)
        hr = END_HOLE_D / 2.0
        if side == "L":
            pa, pb_ = CU_IX[0], CU_IX[0] + 3.0                       # plate x271.5..274.5 on the end-wall inner face
            ca, cb = pb_, pk[1]                                      # cradle x274.5..287
            y0_, y1_ = pk[2] - 1.7, pk[3] + 1.7                      # 236 .. 250
            pz0, pz1 = 28.0, wz + hr + 3.0                           # plate z28..54 (under the hole too: glue land; 3 over the hole)
            qy0, qy1 = wy - hr - 2.5, wy + hr + 2.5                  # plate y: 2.5 wall beside the D14 hole
            fz0 = pk[4] - 1.2                                        # floor z40
        else:
            pa, pb_ = CU_IX[1] - 3.0, CU_IX[1]                       # plate x947.5..950.5
            ca, cb = pk[0], pa                                       # cradle x935..947.5
            y0_, y1_ = pk[2] - 1.7, pk[3] + 1.7                      # 283 .. 297
            pz0, pz1 = wz - hr - 3.0, wz + hr + 3.0                  # plate z39.5..59.5 (3 around the hole, lid underside 61.35)
            qy0, qy1 = wy - hr - 2.5, wy + hr + 2.5
            fz0 = pk[4] - 1.2                                        # floor z47
        top = pk[5] + 1.2
        add = [box(pa, pb_, qy0, qy1, pz0, pz1),
               box(min(ca, cb) - 0.01, max(ca, cb) + 0.01, y0_, y1_, fz0, pk[4]),                  # floor
               box(min(ca, cb) - 0.01, max(ca, cb) + 0.01, y0_, pk[2], fz0, top),                  # side walls
               box(min(ca, cb) - 0.01, max(ca, cb) + 0.01, pk[3], y1_, fz0, top),
               box(min(ca, cb) - 0.01, max(ca, cb) + 0.01, pk[2] - 0.01, pk[2] + 1.0, pk[5], top),  # snap lips 1 over the connector
               box(min(ca, cb) - 0.01, max(ca, cb) + 0.01, pk[3] - 1.0, pk[3] + 0.01, pk[5], top)]
        for (a, b) in ((y0_, pk[2]), (pk[3], y1_)):         # side walls run down to the plate below the hole: 45 deg gussets (in print the
            if side == "L":                                  # walls / floor start over the D14 hole and would hang in the air)
                add.append(prism_y([(pb_ - 0.01, pz0), (pb_ - 0.01, fz0 + 0.01), (pb_ + (fz0 - pz0), fz0 + 0.01)], a, b))
            else:
                add.append(prism_y([(pa + 0.01, pz0), (pa + 0.01, fz0 + 0.01), (pa - (fz0 - pz0), fz0 + 0.01)], a, b))
        m = union(add)
        m = diff(m, [cyl_x(wy, wz, pa - 0.01, pb_ + 0.01, END_HOLE_D)])
        cc = CC["C-XT30-%s" % side]
        fy, fz = (pk[2] + pk[3]) / 2.0, (pk[4] + pk[5]) / 2.0
        rmax = math.hypot(5.1, 2.6 + abs(fz - wz))
        out.add("XT30-CLIP-%s" % side, "XT30 짝 집게 %s (끝벽 안쪽, 출력)" % side, "XT30 pair clip on the end wall %s (printed)" % side, "print",
                G_CUP, m, COLORS["printed_body"], PETG,
                source=SRC + " centre_contents C-XT30-%s (x%.1f~%.1f y%.0f~%.0f z%.0f~%.0f) + speakers.xt30 (스피커 꼬리 XT30U-F가 끝벽 구멍 Ø14로 "
                             "들어가 끝벽 집게의 짝과 꽂힘) + printed_parts XT30-CLIP (24 × 14 × 10)" % ((side,) + tuple(cc)),
                note="사양과 다름(작은 고침): 끝벽에 붙는 판의 구멍 Ø14와 끝벽 구멍을 y%.0f z%.1f로 (사양은 스피커 옆판 선 구멍 z40과 곧게) - 홈의 "
                     "XT30U-F(모서리 반지름 %.2f < 7)가 홈에서 끝벽 쪽으로 곧게 밀려 판 %.0f + 끝벽 11.5 터널로 들어가고 스피커 쪽으로 빠짐 (L은 사양 자리에서 "
                     "모서리가 판·끝벽에 걸려 빠지지 않았음)%s; 추정: XT30U-F 홈 %.1f × %.1f × %.1f (x%.1f~%.1f, 10.2 × 5.2 × 12.4 + 0.2씩), 입구 %s"
                     "(가운데 쪽)으로 앰프 선 XT30U-M이 꽂힘, 홈 위 걸림 턱 1 × 1.2 (위에서 눌러 끼움); 홈에는 축 방향 멈춤이 없음 - 홈 뒤가 터널로 열려 있어야 "
                     "스피커를 뗄 때 F가 터널로 빠짐, 그래서 홈 안의 F에 M을 대고 밀면 F가 터널로 밀려 들어감 → 짝 꽂기: F를 홈 입구로 가운데 쪽에 당겨 꺼내 "
                     "(꼬리 여유 약 %.0f mm) 손으로 M을 끝까지 꽂고, 짝을 다시 가져와 F 앞면을 홈 입구에 맞춰 위에서 걸림 턱 밑으로 눌러 끼움; 뽑기는 거꾸로 "
                     "(짝을 입구로 꺼낸 뒤 손으로 뽑음); 옆벽 밑에 45° 받침 2개를 판의 구멍 아래 부분까지 (출력 때 옆벽·바닥이 구멍 위에 뜨지 않게); 끝벽에 붙는 판 "
                     "x%.1f~%.1f y%.1f~%.1f z%.1f~%.1f (구멍 둘레 2.5~3), MS 폴리머로 붙임; 스피커 꼬리의 여유 약 %.0f mm는 터널 안에 느슨하게 1.5바퀴 감김 "
                     "(C-SPKPIG, 스피커 밖 꼬리 약 %.0f mm)"
                     % (wy, wz, rmax, pb_ - pa, "; 판 위끝을 z%.0f까지 올려 구멍 위 3을 남김" % pz1 if side == "L" else "; R 선 홈은 없앰(꼬리가 구멍으로 곧게 감)",
                        pk[3] - pk[2], pk[5] - pk[4], pk[1] - pk[0], pk[0], pk[1], "+x" if side == "L" else "−x", PIG_SLACK_MM, pa, pb_, qy0, qy1, pz0, pz1,
                        PIG_SLACK_MM, PIG_OUT_MM),
                print_name="XT30집게_" + side, R=R_XMIN if side == "L" else R_XMAX,
                print_note="끝벽에 붙는 판을 베드에, 홈이 위로 서도록 출력(서포트 없음)",
                dims=[("x", min(pa, ca), max(pb_, cb), "%.1f" % (max(pb_, cb) - min(pa, ca)), 0), ("x", pk[0], pk[1], "홈 12.4", 1),
                      ("y", qy0, qy1, "판 %.0f" % (qy1 - qy0), 0), ("y", pk[2], pk[3], "홈 10.6", 1), ("z", pz0, max(pz1, top), "z%.1f~%.1f" % (pz0, max(pz1, top)), 0),
                      ("z", pk[4], pk[5], "홈 5.6", 1), ("z", wz - hr, wz + hr, "구멍 Ø14 z%.1f" % wz, 2)])


# ------------------------------------------------------------------ board posts (spec STANDOFFS) + fuse cradle

def _board_posts():
    """(tag, id suffix, x, y, top z, D, hole D, hole depth, pin) from the centre_contents boxes + v3 boss offsets (body_centre_unit)."""
    pi = CC["CU-E-PI5"]
    bk = CC["CU-E-BUCK"]
    pb = CC["CU-E-PEDBOARD"]
    jb = CC["CU-E-J702BOARD"]
    rows = []
    for k, (x, y) in enumerate([(pi[0] + 3.5, pi[2] + 3.5), (pi[0] + 61.5, pi[2] + 3.5), (pi[0] + 3.5, pi[3] - 3.5), (pi[0] + 61.5, pi[3] - 3.5)]):
        rows.append(("PI", k + 1, x, y, BOARD_Z["PI"], 6.0, 2.2, 5.0, False))
    for k, (x, y) in enumerate([(bk[0] + 3.2, bk[2] + 3.2), (bk[1] - 3.2, bk[2] + 3.2), (bk[0] + 3.2, bk[3] - 3.2), (bk[1] - 3.2, bk[3] - 3.2)]):
        rows.append(("BUCK", k + 1, x, y, BOARD_Z["BUCK"], 7.0, 2.7, 4.0, False))
    for k, (x, y, pin) in enumerate([(pb[0] + 4, pb[2] + 4, False), (pb[1] - 4, pb[3] - 4, False), (pb[1] - 4, pb[2] + 4, True), (pb[0] + 4, pb[3] - 4, True)]):
        rows.append(("PED", k + 1, x, y, BOARD_Z["PED"], 6.0, 2.5, 4.0, pin))
    for k, (x, y) in enumerate([(jb[0] + 3.0, jb[2] + 3.0), (jb[1] - 3.0, jb[3] - 3.0)]):
        rows.append(("J702", k + 1, x, y, BOARD_Z["J702"], 7.0, 2.7, 4.0, False))
    return rows


POST_NAMES = {"PI": ("라즈베리파이 5", "Pi 5", "M2.5×6 자가 탭 (구멍 Ø2.2 × 5, 기판 1.6 → 물림 4.4, 바닥 1.0)"),
              "BUCK": ("강압 XL4016", "buck XL4016", "M3×5 자가 탭 (구멍 Ø2.7 × 4, 기판 1.6 → 물림 3.4, 바닥 1.0 - 6 mm 이상은 바닥을 뚫고 기둥을 밀어 올림)"),
              "PED": ("페달 보드 PED", "PED board", "M3×5 자가 탭 (구멍 Ø2.5 × 4, 바닥 1.0) / 위치 핀 Ø2.8 × 2.5"),
              "J702": ("앰프 입력 잭 기판 J702", "J702 board", "M3×5 자가 탭 (구멍 Ø2.7 × 4, 바닥 1.0)")}


FUSE_BORE = 10.3          # fuse-holder cradle bore (spec 10.5 left a 0.75 floor; the BU914 holder is D10)


def board_posts(out):
    for (tag, k, x, y, zt, d, hd, hdep, pin) in _board_posts():
        m = cyl_z(x, y, Z_BOT, zt, d)
        if pin:
            m = union([m, cyl_z(x, y, zt - 0.01, zt + 2.5, 2.8)])
        else:
            m = diff(m, [cyl_z(x, y, zt - hdep, zt + 0.01, hd)])
        ko, en, scr = POST_NAMES[tag]
        h = zt - Z_BOT
        out.add("CU-POST-%s-%d" % (tag, k), "보드 받침 기둥 (%s, %.0f mm%s)" % (ko, h, ", 위치 핀" if pin else ""),
                "board post (%s, %.0f mm%s)" % (en, h, ", locating pin" if pin else ""), "print", G_CUP, m, COLORS["printed_body"], PETG,
                source=SRC + " printed_parts STANDOFFS (Pi 6 mm, 강압·PED·J702 5 mm) + centre_contents (보드 상자) + " + SRC_C
                       + " PR-CU-TRAY pi5/buck/ped/amp_input_jack_board bosses (구멍 = 보드 모서리에서 같은 거리)",
                note="추정: 기둥 Ø%.0f × %.0f (x%.1f y%.1f), %s - 보드에 먼저 나사로 달고 기둥 밑을 아랫판에 MS 폴리머로 붙임(스스로 자리 잡음); "
                     "사양의 '받침 판'(90×60) 대신 낱개 기둥 - 아랫판 흡기 홈을 막지 않음" % (d, h, x, y, scr),
                print_name="보드받침기둥_%s_Ø%.0f_%.0fmm%s" % ({"PI": "Pi", "BUCK": "나사", "J702": "나사", "PED": "PED"}[tag], d, h, "_핀" if pin else ""),
                R=R_NONE, print_note="밑면을 베드에 세워 출력, 채움 100 %. 서포트 없음",
                dims=[("x", x - d / 2, x + d / 2, "Ø%.0f" % d, 0), ("z", Z_BOT, zt + (2.5 if pin else 0.0), "%.1f" % (zt + (2.5 if pin else 0) - Z_BOT), 0)])
    # fuse cradle (BU914 inline holder clipped to the floor)
    fu = CC["CU-E-FUSE"]
    ay, az = (fu[2] + fu[3]) / 2.0, (fu[4] + fu[5]) / 2.0
    ri = FUSE_BORE
    x0, x1 = fu[0] - 2.0, fu[1] + 2.0
    top = az + 3.0
    wall = 1.85
    m = diff(box(x0, x1, ay - ri / 2 - wall, ay + ri / 2 + wall, Z_BOT, top), [cyl_x(ay, az, x0 - 0.01, x1 + 0.01, ri)])
    out.add("CU-FUSECRADLE", "퓨즈 홀더 받침 (BU914, 눌러 끼움)", "fuse-holder cradle (BU914)", "print", G_CUP, m, COLORS["printed_body"], PETG,
            source=SRC + " centre_contents CU-E-FUSE (x405~451 y301~311 z17.5~27.5, 바닥에 집게로) + printed_parts STANDOFFS; " + SRC_C
                   + " PR-CU-TRAY fuse_holder_cradle (U 받침 안지름 10.5 + 타이 홈 2)",
            note="사양과 다름(작은 고침): 안지름 10.5 → %.1f, 타이 홈 2 없앰 - 사양대로면 받침 밑 바닥이 0.75이고 타이 홈(2.1)이 그 바닥을 칼날처럼 뚫음; "
                 "Ø%.1f이면 바닥 %.2f, 홀더는 눌러 끼움 + MS 폴리머 한 점으로 충분; 추정: 받침 x%.0f~%.0f y%.2f~%.2f z16.5~%.1f, 축 (y%.0f, z%.1f) - 위가 %.1f만 "
                 "열려 Ø10 홀더를 눌러 끼움, 아랫판에 MS 폴리머"
                 % (ri, ri, az - ri / 2 - Z_BOT, x0, x1, ay - ri / 2 - wall, ay + ri / 2 + wall, top, ay, az, 2 * math.sqrt((ri / 2) ** 2 - (top - az) ** 2)),
            print_name="퓨즈홀더받침", R=R_NONE, print_note="밑면을 베드에. 서포트 없음",
            dims=[("x", x0, x1, "%.0f" % (x1 - x0), 0), ("y", ay - ri / 2 - wall, ay + ri / 2 + wall, "%.0f" % (ri + 2 * wall), 0), ("z", Z_BOT, top, "%.1f" % (top - Z_BOT), 0)])


# ------------------------------------------------------------------ cable clips (spec printed_parts CABLE-CLIPS 8)

CLIP_L, CLIP_W, CLIP_H, CLIP_BASE = 20.0, 10.0, 8.0, 2.0          # spec print size 20 x 10 x 8
CLIP_SLOT, CLIP_MOUTH = 4.5, 3.0                                  # U slot for ONE D3.5 cable (two need 7), snap mouth 3.0
CLIP_ROOF = {"L": [40.0, 105.0, 180.0]}                           # under the pod duct roof (x centres), y226..236 z19..27
CLIP_ROOF["R"] = [mxv(x) for x in CLIP_ROOF["L"]]
CLIP_ROOF_Y = 231.0
CLIP_WALL = [272.0, 296.0]                                        # left end wall inner face: y centres, holding C-SPK-L at z53
CLIP_WALL_Z = 53.0
CLIP_SEAT = CLIP_BASE + 1.5                                       # D3 lead centre above the glue face (sits on the slot floor)


def clip_local():
    """one clip, glue face on z0, slot along x open to +z: section (y, z) extruded x -10..10."""
    h2, m2, w2 = CLIP_SLOT / 2.0, CLIP_MOUTH / 2.0, CLIP_W / 2.0
    zl0 = CLIP_H - 1.5 - (h2 - m2) - (h2 - m2)                      # lip: 45 deg under-chamfer, 0.7 flat, 45 deg entry
    sec = [(-w2, 0.0), (w2, 0.0), (w2, CLIP_H), (h2 - 0.05, CLIP_H), (m2, CLIP_H - (h2 - 0.05 - m2)), (m2, zl0 + (h2 - m2)),
           (h2, zl0), (h2, CLIP_BASE), (-h2, CLIP_BASE), (-h2, zl0), (-m2, zl0 + (h2 - m2)), (-m2, CLIP_H - (h2 - 0.05 - m2)),
           (-(h2 - 0.05), CLIP_H), (-w2, CLIP_H)]
    return prism_x(sec, -CLIP_L / 2.0, CLIP_L / 2.0)


def cable_clips(out):
    c = clip_local()
    ps = to_bed(c)
    R_WALL = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]                      # local z -> +x (off the wall), local x -> y (along the lead), local y -> z
    pn = "붙이는 면(20 × 10)을 베드에, 홈이 위로. 걸림 턱 밑은 45° - 서포트 없음. 8개를 한 판에"
    for side in "LR":
        for k, xc in enumerate(CLIP_ROOF[side]):
            m = orient(c, rot_x(180.0), (xc, CLIP_ROOF_Y, DUCT_Z[1]))
            out.add("CABLE-CLIP-%s%d" % (side, k + 1), "케이블 집게 (통로 지붕 밑, 스피커 %s %d)" % (side, k + 1),
                    "cable clip under the duct roof, pod %s %d" % (side, k + 1), "print", G_SPK[side], m, COLORS["printed_body"], PETG,
                    source=SRC + " printed_parts CABLE-CLIPS (8개, 20 × 10 × 8, '통로 지붕 아래·끝벽 케이블 집게', 자리 없음)",
                    note="추정: 사양에 자리가 없어 통로 지붕 밑면 z27에 붙여 z%.0f~27, y%.0f~%.0f (x%.0f~%.0f)에 둠 - 묶음 윗면 z16.25보다 %.2f 위라 "
                         "모델에서는 비어 있음; 처지는 EL·ER 리드나 헤드폰 선을 끼우는 자리 - 집게는 스피커에 붙어 있으므로 스피커를 약 10 mm 든 뒤 "
                         "(더 들거나 옆으로 밀기 전에) 지붕 집게에 끼운 선을 모두 빼냄, 남기면 선이 스피커와 같이 들림; "
                         "홈 %.1f (Ø3.5 선 1가닥 - 2가닥은 홈 7이 필요), 입구 %.1f 걸림 턱, MS 폴리머로 붙임"
                         % (DUCT_Z[1] - CLIP_H, CLIP_ROOF_Y - CLIP_W / 2, CLIP_ROOF_Y + CLIP_W / 2, xc - CLIP_L / 2, xc + CLIP_L / 2,
                            DUCT_Z[1] - CLIP_H - 16.25, CLIP_SLOT, CLIP_MOUTH),
                    print_name="케이블집게", ps=ps, print_note=pn,
                    dims=[("x", xc - CLIP_L / 2, xc + CLIP_L / 2, "20", 0), ("y", CLIP_ROOF_Y - CLIP_W / 2, CLIP_ROOF_Y + CLIP_W / 2, "10 (홈 4.5, 입구 3)", 0),
                          ("z", DUCT_Z[1] - CLIP_H, DUCT_Z[1], "8 (지붕 밑)", 0)])
    for k, yc in enumerate(CLIP_WALL):
        m = orient(c, R_WALL, (CU_IX[0], yc, CLIP_WALL_Z))
        out.add("CABLE-CLIP-E%d" % (k + 1), "케이블 집게 (끝벽 L 안쪽, 스피커선 %d)" % (k + 1), "cable clip on the left end wall %d" % (k + 1),
                "print", G_CUP, m, COLORS["printed_body"], PETG,
                source=SRC + " printed_parts CABLE-CLIPS (8개, 20 × 10 × 8, '통로 지붕 아래·끝벽 케이블 집게', 자리 없음) + centre_contents "
                             "Z-SPKLEAD-L2 (x271.5~284 y236~330 z50~58, 끝벽을 따라 내려오는 스피커선)",
                note="추정: 끝벽 L 안면 x%.1f에 붙여 y%.0f~%.0f z%.0f~%.0f - 끝벽을 따라 앞으로 오는 스피커선 C-SPK-L (x%.1f z%.0f)을 홈 바닥에 잡음 "
                     "(나비나사 머리 y310~320·XT30 집게 판 y≤252.5을 피함); 홈 %.1f, 입구 %.1f 걸림 턱, MS 폴리머로 붙임"
                     % (CU_IX[0], yc - CLIP_L / 2, yc + CLIP_L / 2, CLIP_WALL_Z - CLIP_W / 2, CLIP_WALL_Z + CLIP_W / 2, CU_IX[0] + CLIP_SEAT + 0.1,
                        CLIP_WALL_Z, CLIP_SLOT, CLIP_MOUTH),
                print_name="케이블집게", ps=ps, print_note=pn,
                dims=[("y", yc - CLIP_L / 2, yc + CLIP_L / 2, "20", 0), ("z", CLIP_WALL_Z - CLIP_W / 2, CLIP_WALL_Z + CLIP_W / 2, "10 (홈 4.5)", 0),
                      ("x", CU_IX[0], CU_IX[0] + CLIP_H, "8 (끝벽에서)", 0)])


# ------------------------------------------------------------------ entry point

def build():
    S = _load("body_speakers.json")
    F = _load("keyaction_features_frame.json")
    out = Out()
    speaker_parts(S, out)
    duct_caps(out)
    pod_sockets(out)
    bracket(F, out)
    joints(out)
    feet(out)
    cu_panels(out)
    screen_lid(out)
    seam_rails(out)
    touch_parts(out)
    back_plate(out)
    hub_shelf(out)
    pb_holder(out)
    xt30_clips(out)
    board_posts(out)
    cable_clips(out)
    return list(out)


if __name__ == "__main__":
    ps = build()
    for p in ps:
        b = p.solid.bounding_box()
        print("%-22s %-11s %-12s %3d  %s" % (p.id, p.kind, p.group, len(p.solid.decompose()), " ".join("%.2f" % v for v in b)))
    print(len(ps), "parts")
    print("grille", GRILLE_STATS)
