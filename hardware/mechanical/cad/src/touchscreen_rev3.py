"""R31 touchscreen rev 3 (3a) - shared numbers and poses for body.py (printed parts, screws) and electronics.py (display, cables).

Governing spec: hardware/mechanical/touchscreen/rev3/design/CAD_SPEC_rev3.md (W1 session, rev 3a approved by the user 2026-10-01, sections
A..G) with its numbers file rev3/design/numbers.json (read here; the "placement" block holds the L2 values W1 designed against) and the
drawings rev3/drawings/t01..t06. Screen: Waveshare 7-DSI-TOUCH-C, glass 166.10 x 101.00, body 8.0, M2.5 corner holes 154 x 88
(touchscreen/screen_dims/ws_7-DSI-TOUCH-C-details-size.jpg). The rev 2 (Touch Display 2) module stays as touchscreen.py (frozen, imported by the L1 archives body_L1 / electronics_L1 / check_*_L1).

Cradle frame (spec 0 / F): xr = world x - XC (611), u = from the glass bottom edge up the screen, w = from the glass front face backward.
The hinge axis is cradle (u -9, w 13) = world (y226.55, z81.35). A pose is the tilt theta back from vertical:
    world = M(theta) . [xr, u, w, 1],  M = [[1, 0, 0, XC], [0, s, c, AY - UA s - WA c], [0, c, -s, AZ - UA c + WA s]]
use 25 deg, heel contact 22 deg, folded (transport) 90 deg. (xr, u, w) is a left-handed frame (det -1): solids built in it come out as
the real part in the world (manifold flips the winding); print solids are always taken from the WORLD solid with a proper rotation
(print_R_*), never from the local build.
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TS_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "touchscreen", "rev3"))
SRC_SPEC = "touchscreen/rev3/design/CAD_SPEC_rev3.md (3a)"
SRC_NUM = "touchscreen/rev3/design/numbers.json (3a)"
SRC_DRW = "touchscreen/rev3/drawings/t01~t06"
SRC_SCR = "touchscreen/screen_dims/ws_7-DSI-TOUCH-C-details-size.jpg (Waveshare 도면)"

with open(os.path.join(TS_DIR, "design", "numbers.json")) as _fh:
    N = json.load(_fh)
assert str(N.get("revision", "")).startswith("3a"), N.get("revision")

PL = N["placement"]
XC = PL["x_centre"]                                    # 611
AX_Y, AX_Z = N["hinge"]["axis_yz"]                     # 226.55, 81.35
AX_U, AX_W = N["hinge"]["axis_cradle_uw"]              # -9, 13
TILT_USE = N["hinge"]["tilt_use_deg"]                  # 25
TILT_HEEL = N["hinge"]["heel_contact_deg"]             # 22
TILT_FOLD = 90.0
KEEP_Y, KEEP_Z = PL["keepout"]["y_max"], PL["keepout"]["z_min"]   # nothing at y <= 215 with z >= 72.85
LID_TOP, LID_BED, LID_PLATE = PL["lid"]["top_z"], PL["lid"]["bed_z"], PL["lid"]["plate_t"]   # 72.85 / 61.35 / 3

SC = N["screen"]
GLASS = tuple(SC["glass"])                             # 166.1 x 101.0
BODY_T = SC["body"]                                    # 8.0
CR = N["cradle"]
HG = N["hinge"]
LG = N["leg"]
POINTS = N["points"]
CHECKS = N["checks"]

CR_XR = tuple(CR["xr"])                                # -85.35 .. 85.35
CR_U = tuple(CR["u"])                                  # -2.5 .. 103.5
CR_W = tuple(CR["w"])                                  # -1 .. 16
PLATE_W = tuple(CR["plate"])                           # 10.5 .. 13
RIB_W = tuple(CR["rib"])                               # 13 .. 16
WALLS = CR["walls"]
EAR = CR["ear"]
EAR_PROFILE = [tuple(p) for p in EAR["profile_uw"]]    # convex outline (u, w), heel first
BOSS = CR["bosses"]
NOTCH = CR["notch"]
GROOVE = CR["groove"]
INSP = CR["insp"]
HOLD_PAD = CR["hold_pad"]
PADS = CR["pads"]
CROSS_RIBS_U = tuple(CR["cross_ribs_u"])               # 24, 80
RIB_T = CR["rib_t"]                                    # 2
CHANNEL = LG["channel"]
CLEVIS = LG["clevis"]
LCLIP = LG["clip"]
CHAMFER_C2 = CR["rib_relief_at_cheeks"]["chamfer"]     # 2.0 at (u-2.5, w16)

KNUCKLE = HG["knuckle_profile"]                        # R5.5, base y217.55..235.55 z72.85, y221.05..232.05 at the axis
HEEL_BLOCK = HG["heel_block"]                          # y217.55..224.55, z72.85..76.35 in the ear slots
HOLE = N["hole"]                                       # ribbon / power hole 22 x 6, wall 2, edge R1
CLIP = N["clip"]                                       # clip pad, pins, clip plate, wire groove
VENTS = [tuple(s) for s in N["vents"]["slots"]]        # (x0, x1, y0, y1)
POCKET = LG["pocket"]
FOLD_FEET = N["fold_feet_detail"]
LID_SCREW = N["lid_screw"]
RIBBON = N["ribbon"]
PWIRE = N["power_wire"]
PI5 = N["pi5"]


def hinge_x(side, key):
    """world x range of a hinge feature: side 'left' / 'right', key far_cheek / ear / ear_slot / near_cheek."""
    a, b = HG[side][key]
    return (XC + a, XC + b)


def rot(theta):
    t = math.radians(theta)
    return math.sin(t), math.cos(t)


def M(theta=TILT_USE):
    """3 x 4 matrix: cradle (xr, u, w) -> world (x, y, z), determinant -1."""
    s, c = rot(theta)
    return np.array([[1, 0, 0, XC],
                     [0, s, c, AX_Y - AX_U * s - AX_W * c],
                     [0, c, -s, AX_Z - AX_U * c + AX_W * s]], dtype=float)


# the design's pose matrices (numbers.json poses) must be reproduced exactly
for _k, _th in (("cradle_use", TILT_USE), ("cradle_heel", TILT_HEEL), ("cradle_fold", TILT_FOLD)):
    assert np.abs(np.array(N["poses"][_k], float)[:3] - M(_th)).max() < 0.01, _k


def place(m, theta=TILT_USE):
    return m.transform(M(theta))


def pt(u, w, theta=TILT_USE):
    """cradle (u, w) -> world (y, z) in the pose theta."""
    s, c = rot(theta)
    return (AX_Y + (u - AX_U) * s + (w - AX_W) * c, AX_Z + (u - AX_U) * c - (w - AX_W) * s)


def inv(y, z, theta=TILT_USE):
    """world (y, z) -> cradle (u, w) in the pose theta."""
    s, c = rot(theta)
    dy, dz = y - AX_Y, z - AX_Z
    return (AX_U + dy * s + dz * c, AX_W + dy * c - dz * s)


def world_pt(xr, u, w, theta=TILT_USE):
    y, z = pt(u, w, theta)
    return (XC + xr, y, z)


def world_dir(dxr, du, dw, theta=TILT_USE):
    s, c = rot(theta)
    return (dxr, du * s + dw * c, du * c - dw * s)


def print_R_top_down(theta=TILT_USE):
    """proper rotation world -> print for a solid in pose theta: print z = -u (the top edge u103.5 on the bed, ears up)."""
    s, c = rot(theta)
    return [[1, 0, 0], [0, -c, s], [0, -s, -c]]


def print_R_w_down(theta=TILT_USE):
    """proper rotation world -> print: print z = +w (the -w face on the bed, +w side up)."""
    s, c = rot(theta)
    return [[-1, 0, 0], [0, s, c], [0, c, -s]]


for _th in (TILT_USE, TILT_FOLD):                       # both print rotations are proper (det +1) and map u / w as stated
    for _R in (print_R_top_down(_th), print_R_w_down(_th)):
        assert abs(np.linalg.det(np.array(_R, float)) - 1.0) < 1e-9
    _Mu = M(_th)[:, 1]
    _Mw = M(_th)[:, 2]
    assert abs(np.array(print_R_top_down(_th))[2] @ _Mu + 1.0) < 1e-9 and abs(np.array(print_R_w_down(_th))[2] @ _Mw - 1.0) < 1e-9

# leg (use pose): axis = cradle (u30, w16.5) at 25 deg, foot = spec tip
LEG_PIVOT_UW = tuple(LG["pivot_cradle_uw"])            # (30, 16.5)
LEG_AX_YZ = pt(*LEG_PIVOT_UW, TILT_USE)                # (246.20, 115.22)
LEG_TIP_YZ = tuple(LG["tip_yz"])                       # (297.7, 72.35)
LEG_L = LG["length"]                                   # 67
LEG_X = tuple(LG["x"])                                 # 606 .. 616
LEG_T = LG["section"][1]                               # 6 (the 10 is along x)
_d = (LEG_TIP_YZ[0] - LEG_AX_YZ[0], LEG_TIP_YZ[1] - LEG_AX_YZ[1])
LEG_LEN_MODEL = math.hypot(*_d)
LEG_DIR = (_d[0] / LEG_LEN_MODEL, _d[1] / LEG_LEN_MODEL)
LEG_ANGLE = math.degrees(math.atan2(-LEG_DIR[1], LEG_DIR[0]))   # below horizontal
LEG_N = (-LEG_DIR[1], LEG_DIR[0])                                 # thickness direction (up-ish) in (y, z)
assert abs(LEG_LEN_MODEL - LEG_L) < 0.02 and abs(LEG_ANGLE - LG["angle_deg"]) < 0.02
