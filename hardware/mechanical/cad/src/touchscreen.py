"""ARCHIVE (frozen 2026-10-01, rev 2 Touch Display 2 numbers; imported by the L1 archives - the L2 build uses touchscreen_rev3.py) - R31 touchscreen - shared numbers and poses for body.py (printed parts, screws) and electronics.py (display, cables).

Governing spec: hardware/mechanical/touchscreen/CAD_SPEC.md (W1 session, revision 2, 2026-09-30) with its numbers file
touchscreen/numbers.json (read here) and the official Touch Display 2 7" drawing touchscreen/screen_dims/td2_7_mech.png.

Cradle frame (CAD_SPEC C): u = from the glass bottom edge up the screen, w = from the glass front face backward, x = world x.
The hinge axis is cradle (u -9, w 16) = world (y290, z96). A pose is the tilt theta back from vertical:
    y = 290 + (u + 9) sin(theta) + (w - 16) cos(theta)
    z =  96 + (u + 9) cos(theta) - (w - 16) sin(theta)
use 25 deg, heel contact 22 deg, folded (transport) 90 deg. (x, u, w) is a left-handed frame, so the local -> world map
has determinant -1: solids built in (x, u, w) come out as the real part in the world; print solids are always taken from
the WORLD solid with a proper rotation (print_R_*), never from the local build.
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TS_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "touchscreen"))
SRC_SPEC = "touchscreen/CAD_SPEC.md"
SRC_NUM = "touchscreen/numbers.json"
SRC_DRW = "touchscreen/screen_dims/td2_7_mech.png (공식 TD2 7인치 도면)"

# W1 may move the rev 2 (TD2) files into touchscreen/rev2_td2/ - read from there first, else the old place
_REV2 = os.path.join(TS_DIR, "rev2_td2")
if os.path.exists(os.path.join(_REV2, "numbers.json")):
    TS_DIR = _REV2
with open(os.path.join(TS_DIR, "numbers.json")) as _fh:
    N = json.load(_fh)

AX_Y, AX_Z = N["hinge"]["axis_yz"]                     # 290, 96
AX_U, AX_W = N["hinge"]["axis_cradle_uw"]              # -9, 16
TILT_USE = N["hinge"]["tilt_use_deg"]                  # 25
TILT_HEEL = N["hinge"]["heel_contact_deg"]             # 22
TILT_FOLD = 90.0
HEEL_YZ = tuple(N["hinge"]["heel_contact_yz"])         # (283, 88)
HEEL_R = N["hinge"]["heel_R"]                          # 10.63

CR_X = tuple(N["cradle"]["x"])                         # 559.04 .. 752.96
CR_U = tuple(N["cradle"]["u"])                         # -2.5 .. 122.74
CR_W = tuple(N["cradle"]["w"])                         # -1 .. 16
GLASS = tuple(N["screen"]["glass"])                    # 189.32 x 120.24
GLASS_X = tuple(N["screen"]["glass_x"])                # 561.34 .. 750.66
X_C = N["screen"]["x_centre"]                          # 656
DSI = N["screen"]["dsi"]                               # x_centre 638.66, open_x 629.7, u 52.1..68.1
J1 = N["screen"]["j1"]                                 # x 647..658, u 36.5..43

HINGE = {s: N["hinge"][s] for s in ("left", "right")}  # far / ear / near x ranges, screw from +x
KNUCKLE_R = N["hinge"]["knuckle_profile"]["top_R"]      # 5.5
KN_Z88 = tuple(N["hinge"]["knuckle_profile"]["base_z88_y"])   # 281 .. 299
KN_Z96 = tuple(N["hinge"]["knuckle_profile"]["at_z96_y"])     # 284.5 .. 295.5
HOLE_X = tuple(N["hole"]["x"])                         # 592 .. 614 (ribbon + power wire)
HOLE_Y = tuple(N["hole"]["y"])                         # 292 .. 298

LEG = N["leg"]
LEG_PIVOT_UW = tuple(LEG["pivot_cradle_uw"])           # (20, 19.5)
LEG_TIP_YZ = tuple(LEG["tip_yz"])                      # (394.4, 87.5)
LEG_L = LEG["length"]                                  # 95
LEG_X = tuple(LEG["x"])                                # 651 .. 661
LEG_T = LEG["section"][1]                              # 6 (the 10 is along x)
LEG_STOW_TIP_U = LEG["stow_tip_u"]                     # 118
POCKET = LEG["pocket"]                                 # back wall y397.4, bottom z84.5, ramp from y388.34, x649..663
FOLD_FEET = [tuple(f) for f in N["fold_feet"]]         # (x0, x1, y0, y1), z88..96

# CAD_SPEC numbers that are not in numbers.json
LID_Z0, LID_ZS0, LID_Z1 = 76.5, 85.5, 88.0            # CU lid underside / top-skin bottom / top
WALL_X, WALL_U = 2.0, 2.2                              # cradle side walls 2.0; bottom / top walls = 2.5 - 0.3 and 122.74 - 120.54
GLASS_GAP = 0.3
BACK_W = (9.4, 12.4)                                   # C2 back plate (lug face w9.4 = body 6.42 + lug 3.0, drawing estimate)
LUG_X = (586.0, 726.0)                                 # C3
LUG_U = (24.77, 95.48)
STANDOFF_X = (618.21, 676.21)                          # C4 (Pi 5 hole pattern 58 x 49 on the TD2 back)
STANDOFF_U = (35.62, 84.62)
WIN_UP = (596.0, 666.0, 46.0, 74.0)                    # C5 inspection window: upper part (x0, x1, u0, u1)
WIN_LO = (640.0, 666.0, 30.0, 46.0)                    #                        lower part (J1)
RIB_U = (20.0, 108.0)                                  # C6 cross ribs, w12.4..16
SLOT = (592.0, 614.0, -2.5, 3.0, 8.0, 16.0)            # C7 bottom open slot (x0, x1, u0, u1, w0, w1)
EAR_T = 8.0                                            # C8
EAR_HOLE = 3.3
CLEVIS = {"near": (646.7, 650.7), "far": (661.3, 667.3), "R": 3.8}   # C9
LCLIP = {"u": (105.0, 111.0), "x": ((647.5, 650.5), (661.5, 664.5)), "w": (16.0, 22.5), "lip": 0.5}   # C10
RCLIP_SEAT_CR = (597.0, 613.0, 10.0, 20.0)             # C11 ribbon-clip seat inside the cradle (x0, x1, u0, u1)
RCLIP_SEAT_LID = (605.0, 320.0)                        # A8 ribbon-clip seat under the lid (x, y), 30 x 12
RCLIP = (30.0, 12.0, 3.0)                              # E
RIBBON_W = 16.0
RIBBON_X = (597.0, 613.0)                              # ribbon lane in the lid hole and in the cradle


def rot(theta):
    t = math.radians(theta)
    return math.sin(t), math.cos(t)


def pt(u, w, theta=TILT_USE):
    """cradle (u, w) -> world (y, z) in the pose theta."""
    s, c = rot(theta)
    return (AX_Y + (u - AX_U) * s + (w - AX_W) * c, AX_Z + (u - AX_U) * c - (w - AX_W) * s)


def inv(y, z, theta=TILT_USE):
    """world (y, z) -> cradle (u, w) in the pose theta."""
    s, c = rot(theta)
    dy, dz = y - AX_Y, z - AX_Z
    return (AX_U + dy * s + dz * c, AX_W + dy * c - dz * s)


def M(theta=TILT_USE):
    """3 x 4 matrix: cradle (x, u, w) -> world (x, y, z), determinant -1."""
    s, c = rot(theta)
    return np.array([[1, 0, 0, 0],
                     [0, s, c, AX_Y - AX_U * s - AX_W * c],
                     [0, c, -s, AX_Z - AX_U * c + AX_W * s]], dtype=float)


def place(m, theta=TILT_USE):
    return m.transform(M(theta))


def world_pt(x, u, w, theta=TILT_USE):
    y, z = pt(u, w, theta)
    return (x, y, z)


def print_R_top_down(theta=TILT_USE):
    """proper rotation world -> print for a solid in pose theta: print z = -u (the top edge u122.74 on the bed)."""
    s, c = rot(theta)
    return [[1, 0, 0], [0, -c, s], [0, -s, -c]]


def print_R_back_down(theta=TILT_USE):
    """proper rotation world -> print: print z = -w (the +w face on the bed, -w side up)."""
    s, c = rot(theta)
    return [[1, 0, 0], [0, s, c], [0, -c, s]]


# leg (use pose): axis = cradle (u20, w19.5) at 25 deg, foot = spec tip
LEG_AX_YZ = pt(*LEG_PIVOT_UW, TILT_USE)
_d = (LEG_TIP_YZ[0] - LEG_AX_YZ[0], LEG_TIP_YZ[1] - LEG_AX_YZ[1])
LEG_LEN_MODEL = math.hypot(*_d)
LEG_DIR = (_d[0] / LEG_LEN_MODEL, _d[1] / LEG_LEN_MODEL)
LEG_ANGLE = math.degrees(math.atan2(-LEG_DIR[1], LEG_DIR[0]))   # below horizontal
LEG_N = (-LEG_DIR[1], LEG_DIR[0])                                 # thickness direction (up-ish) in (y, z)
