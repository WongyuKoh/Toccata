#!/usr/bin/env python3
"""Toccata - printed perfboard jig for cutting / drilling the PED board out of a Coms BE163 sheet
(new 2026-10-07, user: no 5x7 perfboards - their own BE163 double-sided 80 x 120, 30 x 42 holes at 2.54, ~1.6 thick; one sheet
gives two PED pieces; since 2026-11-28 each is 71.12 x 49.53 = 28 x 20 holes, see PED_COLS). A16 (2026-10-31, user: "80 120 으로 설계를 다시"): the 7 control boards MB use a whole sheet each, uncut
and undrilled, on the module floor (keyaction.py A16) - the MB jig P-MB is gone; only the PED piece is still cut.
How to use: cad/jigs/README.md section '기판 지그'.

    build()                                  # -> [{name, solid, qty, required, note, key}] for build_all.py -> stl/print/09_기판지그/
    python3 src/perfboard_jigs.py            # table (size, rough grams / minutes) + the BE163 sheet layout
    python3 src/check_perfboard_jigs.py      # pins on grid holes, bores at the fixing points, cut edges on the outline, layout

The jig is a 5 mm plate the size of the board outline, laid on the sheet's top face. Short pins (D0.9 x 1.2) under it drop into
existing grid holes, so the plate registers on the 2.54 grid exactly where the design puts it. Its four side faces ARE the cut lines
(score with a craft knife along them, then snap), and guide bores (bit + 0.2, as the plywood jigs) go through the plate at the 4
fixing points.

Numbers come from the models, not typed again:
  PED electronics.py CU-E-PEDBOARD (x426.5~476.5 y244~314, turned 90 deg): screws D3.2 at (x0+4, y0+4) (x1-4, y1-4), pins D3.0
      at the other corners (the fixing points come from the CAD box; the CUT SIZE comes from the hole counts, PED_COLS x PED_ROWS above:
      71.12 x 49.53, not the CAD box 70 x 50); the two outline edges at the Zero end / left side sit mid-gap (1.27 from the holes)

Use frame (u, v, w): u along the 70 side, v along the 50 side, w = 0 the sheet's top face, +w up through the plate (toward the drill).
PED: (u, v) = (y - 244, 476.5 - x) - the Zero end (USB-C, -y in the world) is u = 0.
Print frame: plate top (labels) on the bed, pins up - no supports.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

from cadlib import cone_z, cyl_z, diff, orient, prism_z, rot_x, text_xy, union, write_stl  # noqa: E402

SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))
PRINT_SUB = "09_기판지그"

PITCH = 2.54
SHEET = dict(name="Coms BE163", w=80.0, h=120.0, cols=30, rows=42, t=1.6, hole_d=1.0)   # user 2026-10-07 (thickness unverified)
# PED cut size by HOLE COUNT (2026-11-28; was the CAD box 70 x 50, which is not a multiple of the 2.54 pitch and sliced the last hole
# column / row): u = 28 hole columns, both edges mid-gap (28 x 2.54 = 71.12); v = 20 hole rows, the back cut runs along the CENTRE LINE of
# row 20 (1.27 + 19 x 2.54 = 49.53, row 20 is halved) - a 20-row mid-gap edge (50.8) would touch the CU-BATFRAME wall (x <= 426.0 at
# y244~258.5) by 0.3 mm, a 19-row one (48.26) leaves only 2.26 from the v46 screw / pin holes to the edge.
# CAD clearance probe (2026-11-28, real meshes): u + 1.12 (y314 -> 315.12) free, v 50 -> 49.53 only shrinks.
PED_COLS = 28
PED_ROWS = 20
PLATE_T = 5.0                       # plate = knife guide height = drill guide length
PIN_D, PIN_L, PIN_TIP = 0.9, 1.2, 0.5     # registration pins: D0.9 into the D1.0 grid holes, 1.2 long (< 1.6 board), tip D0.5
PIN_CHAMFER = 0.4                    # cone length at the pin tip
BORE_CLR = 0.2                       # guide bore = bit + 0.2 (printed holes come out ~0.1-0.2 small; ream once with the same bit)
ENGRAVE = 0.6                        # engraved labels in the use-top face (bed face in print)
MIN_PIN_EDGE = 2.0                   # pin centre >= 2.0 from any cut line / window edge
MIN_PIN_BORE = 2.5                   # pin centre >= bore radius + 2.5 from a guide bore

R_PRINT = rot_x(180.0)               # use-top face on the bed, pins up


def _ped():
    import body as B                                            # read-only: the centre_contents box
    x0, x1, y0, y1 = B.CC["CU-E-PEDBOARD"][:4]                  # 426.5, 476.5, 244, 314
    # same corners as electronics.py CU-E-PEDBOARD / body.py CU-POST-PED: screws (x0+4, y0+4) (x1-4, y1-4), pins at the others
    pts = [(x0 + 4, y0 + 4, 3.2, "screw"), (x1 - 4, y1 - 4, 3.2, "screw"), (x1 - 4, y0 + 4, 3.0, "pin"), (x0 + 4, y1 - 4, 3.0, "pin")]
    holes = [dict(u=y - y0, v=x1 - x, bit=d, kind=k, world=(x, y)) for (x, y, d, k) in pts]
    return dict(key="P-PED", name="P-PED_페달기판지그_PED1장", title="PED 페달 보드 지그", qty_boards=1,
                size=(PED_COLS * PITCH, PITCH / 2 + (PED_ROWS - 1) * PITCH), origin=None, grid0=(PITCH / 2, PITCH / 2), slot=None, holes=holes,
                src="electronics.py / body.py CU-E-PEDBOARD (x%.1f~%.1f y%.0f~%.0f) + CU-POST-PED corners" % (x0, x1, y0, y1))


def grid_nodes(spec):
    """grid hole centres (u, v) inside the outline (centre within the board, hole may be cut by the edge)."""
    W, H = spec["size"]
    gu0, gv0 = spec["grid0"]
    us = [gu0 + PITCH * i for i in range(int((W - gu0) / PITCH) + 1) if gu0 + PITCH * i <= W]
    vs = [gv0 + PITCH * j for j in range(int((H - gv0) / PITCH) + 1) if gv0 + PITCH * j <= H]
    return us, vs


def pin_nodes(spec):
    """(i, j) grid indices of the registration pins: 4 near the corners + 2 in the middle band, clear of the bores / slot / edges."""
    us, vs = grid_nodes(spec)
    W, H = spec["size"]

    def clear(u, v):
        if min(u, W - u, v, H - v) < MIN_PIN_EDGE:
            return False
        for h in spec["holes"]:
            if math.hypot(u - h["u"], v - h["v"]) < (h["bit"] + BORE_CLR) / 2 + MIN_PIN_BORE:
                return False
        if spec["slot"]:
            a, b, c, d = spec["slot"]
            if a - MIN_PIN_EDGE < u < b + MIN_PIN_EDGE and v < d + MIN_PIN_EDGE:
                return False
        return True
    want = [(0.12, 0.15), (0.88, 0.15), (0.12, 0.85), (0.88, 0.85), (0.30, 0.5), (0.70, 0.5)]
    out = []
    for fu, fv in want:
        cand = sorted(((abs(u - fu * W) + abs(v - fv * H), i, j) for i, u in enumerate(us) for j, v in enumerate(vs) if clear(u, v)))
        _, i, j = cand[0]
        if (i, j) not in out:
            out.append((i, j))
    return [(us[i], vs[j], i, j) for (i, j) in out]


def _label_polys(spec):
    """engraved labels in the use-top face (read from above): name + arrow to the front + bore names."""
    W, H = spec["size"]
    top = PLATE_T
    t = []
    dep = ENGRAVE + 0.02

    def eng(s, size, u, v, rot=0.0, heavy=False):
        t.append(text_xy(s, size, dep, x=u, y=v, z=top - ENGRAVE, halign="center", valign="center", rot=rot, heavy=heavy))
    eng("PED", 6.0, W * 0.5, H * 0.64, heavy=True)
    eng("◀USB 끝", 3.6, W * 0.25, H * 0.40)
    eng("BE163", 3.4, W * 0.72, H * 0.40, heavy=True)
    return t


def make(spec):
    W, H = spec["size"]
    plate = prism_z([(0, 0), (W, 0), (W, H), (0, H)], 0.0, PLATE_T)
    cuts = []
    if spec["slot"]:
        a, b, c, d = spec["slot"]
        cuts.append(prism_z([(a, -1.0), (b, -1.0), (b, d), (a, d)], -0.01, PLATE_T + 0.01))     # slot window open to the front edge
    for h in spec["holes"]:
        cuts.append(cyl_z(h["u"], h["v"], -0.01, PLATE_T + 0.01, h["bit"] + BORE_CLR, 48))
        cuts.append(cone_z(h["u"], h["v"], PLATE_T - 0.6, PLATE_T + 0.01, h["bit"] + BORE_CLR, h["bit"] + BORE_CLR + 1.22, 48))  # lead-in
    cuts += _label_polys(spec)
    m = diff(plate, cuts)
    pins = []
    for (u, v, _i, _j) in pin_nodes(spec):
        pins.append(cyl_z(u, v, -(PIN_L - PIN_CHAMFER), 0.01, PIN_D, 24))
        pins.append(cone_z(u, v, -PIN_L, -(PIN_L - PIN_CHAMFER) + 0.001, PIN_TIP, PIN_D, 24))
    m = union([m] + pins)
    p = orient(m, R_PRINT)
    bb = p.bounding_box()
    t = np.array([-bb[0], -bb[1], -bb[2]])
    return m, p.translate(tuple(t)), t


def to_print(p_use, t):
    return np.asarray(R_PRINT, float) @ np.asarray(p_use, float) + t


def from_print(p_print, t):
    return np.asarray(R_PRINT, float).T @ (np.asarray(p_print, float) - t)


def sheet_layout(spec_a, spec_b):
    """two pieces on one BE163 (70 across the 30 columns, 50 along the 42 rows): piece A from the first row, then one spare
    row as a waste strip if the cut lines would come closer than 1.0, piece B; returns rows / cols used and the strip widths."""
    out = {}
    for s in (spec_a, spec_b):
        us, vs = grid_nodes(s)
        out[s["key"]] = dict(cols=len(us), rows=len(vs), u_first=us[0], v_first=vs[0], v_after=s["size"][1] - vs[-1])
    a, b = out[spec_a["key"]], out[spec_b["key"]]
    # A's back cut is a["v_after"] past its last row; B's front cut is b["v_first"] before its first row
    gap_rows = 0
    while True:
        strip = (gap_rows + 1) * PITCH - a["v_after"] - b["v_first"]
        if strip >= 1.0:
            break
        gap_rows += 1
    rows_used = a["rows"] + gap_rows + b["rows"]
    margin_v = (SHEET["h"] - (SHEET["rows"] - 1) * PITCH) / 2.0       # assumed: grid centred on the sheet (the jig does not need it)
    margin_u = (SHEET["w"] - (SHEET["cols"] - 1) * PITCH) / 2.0
    return dict(a=a, b=b, gap_rows=gap_rows, strip=strip, rows_used=rows_used, cols_used=max(a["cols"], b["cols"]),
                margin_u=margin_u, margin_v=margin_v,
                fits=rows_used <= SHEET["rows"] and max(a["cols"], b["cols"]) <= SHEET["cols"]
                and max(a["u_first"], b["u_first"]) <= margin_u and a["v_first"] <= margin_v)


def specs():
    return [_ped()]                  # A16: the control boards MB use whole sheets, no jig


def _note(spec):
    return ("PED 페달 보드 1장용 지그 (71.12 × 49.53 = 구멍 28 × 20): 핀 6개를 시트 구멍에 꽂고 네 옆면을 따라 칼로 긋고 꺾음, 나사 Ø3.2 ×2·핀 구멍 Ø3.0 ×2를 안내 구멍으로 "
            "뚫음 (cad/jigs/README.md '기판 지그'). 제어 기판 MB 7장은 자르지 않고 통째로 씀 (A16). PETG 0.2 mm, 서포트 없음, STL 방향 그대로")


def build():
    out = []
    for s in specs():
        _m, p, _t = make(s)
        out.append(dict(name=s["name"], solid=p, qty=1, required=True, note=_note(s), key=s["key"]))
    return out


def est_print(m):
    """same rough P2S estimate as plywood_jigs.est_print (3 walls, 15 % infill)."""
    V = m.volume()
    A = m.surface_area()
    shell = min(V, A * 1.1)
    printed = shell + 0.15 * (V - shell)
    g = printed / 1000.0 * 1.27
    h = m.bounding_box()[5]
    minutes = printed / 9.0 / 60.0 + h / 0.2 * 2.5 / 60.0 + 3.0
    return g, minutes


def write_files(root):
    paths = {}
    for j in build():
        path = os.path.join(root, PRINT_SUB, "%s__%d개.stl" % (j["name"], j["qty"]))
        write_stl(j["solid"], path, "Toccata %s perfboard jig" % j["key"])
        paths[j["key"]] = path
    return paths


if __name__ == "__main__":
    S = specs()
    for s in S:
        _m, p, _t = make(s)
        b = p.bounding_box()
        g, mi = est_print(p)
        us, vs = grid_nodes(s)
        print("%-6s %-28s %5.1f x %5.1f x %4.1f  ~%4.1f g ~%3.0f min  grid %d x %d (u0 %.2f v0 %.2f)  pins %s" % (
            s["key"], s["name"], b[3], b[4], b[5], g, mi, len(us), len(vs), us[0], vs[0],
            " ".join("(%.2f,%.2f)" % (u, v) for u, v, _i, _j in pin_nodes(s))))
    for a, b in ((S[0], S[0]),):
        L = sheet_layout(a, b)
        print("sheet %s + %s: rows %d (+%d spare, strip %.2f) of %d, cols %d of %d, fits %s" % (
            a["key"], b["key"], L["rows_used"], L["gap_rows"], L["strip"], SHEET["rows"], L["cols_used"], SHEET["cols"], L["fits"]))
