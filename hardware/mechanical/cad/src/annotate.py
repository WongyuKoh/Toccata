"""Dimension marks as solid geometry, so an STL viewer / slicer shows the numbers next to the part.

A dimension = two extension lines + a dimension line with arrowheads + the value as raised text.
Everything is thin (LINE mm wide, DEPTH mm tall) so it reads like a drawing laid around the part.
These files are for looking at, never for printing (the README says so and the file names end in _치수).
"""
import math

import numpy as np

from cadlib import box, orient, prism_z, text_xy, union

LINE = 0.35
DEPTH = 0.35


def _fmt(v):
    s = ("%.2f" % v).rstrip("0").rstrip(".")
    return s


def _seg_xy(p0, p1, w=LINE, z=0.0, h=DEPTH):
    """thin bar between two xy points lying at height z."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return None
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    pts = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
    if (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[1][1]) - (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[1][0]) < 0:
        pts = pts[::-1]
    return prism_z(pts, z, z + h)


def _arrow_xy(tip, direction, size, z=0.0, h=DEPTH):
    ux, uy = direction
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    bx, by = tip[0] - ux * size, tip[1] - uy * size
    nx, ny = -uy * size * 0.35, ux * size * 0.35
    pts = [tip, (bx + nx, by + ny), (bx - nx, by - ny)]
    area = (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[0][0])
    if area < 0:
        pts = pts[::-1]
    return prism_z(pts, z, z + h)


def dim2d(p0, p1, offset, text=None, size=3.0, z=0.0, ext_gap=0.8):
    """linear dimension in the XY plane between p0 and p1 (2D points), drawn `offset` mm to the left of
    the p0->p1 direction (negative = right). Returns a solid lying on z..z+DEPTH."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return None
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    s = 1 if offset >= 0 else -1
    a0 = (x0 + nx * offset, y0 + ny * offset)
    a1 = (x1 + nx * offset, y1 + ny * offset)
    items = []
    # extension lines
    for (px, py), (ax, ay) in (((x0, y0), a0), ((x1, y1), a1)):
        e0 = (px + nx * s * ext_gap, py + ny * s * ext_gap)
        e1 = (ax + nx * s * 1.2, ay + ny * s * 1.2)
        items.append(_seg_xy(e0, e1, z=z))
    arrow = min(size * 0.9, L / 3.0)
    items.append(_seg_xy((a0[0] + ux * arrow * 0.8, a0[1] + uy * arrow * 0.8), (a1[0] - ux * arrow * 0.8, a1[1] - uy * arrow * 0.8), z=z))
    items.append(_arrow_xy(a0, (-ux, -uy), arrow, z=z))
    items.append(_arrow_xy(a1, (ux, uy), arrow, z=z))
    label = text if text is not None else _fmt(L)
    if label == "":
        return union([i for i in items if i is not None])
    ang = math.degrees(math.atan2(uy, ux))
    if ang > 90.0 or ang <= -90.0:
        ang -= 180.0
    mx, my = (a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2
    # put the text on the outer side of the dimension line
    tx, ty = mx + nx * s * (size * 0.35 + 0.6), my + ny * s * (size * 0.35 + 0.6)
    t = text_xy(label, size, DEPTH, 0, 0, 0, "center", "center", rot=ang)
    items.append(t.translate((tx + nx * s * size * 0.3, ty + ny * s * size * 0.3, z)))
    return union([i for i in items if i is not None])


def leader(p0, p1, z=0.0):
    return _seg_xy(p0, p1, w=LINE * 0.7, z=z)


def label2d(s, x, y, size=3.0, z=0.0, halign="left"):
    return text_xy(s, size, DEPTH, x, y, z, halign, "center")


def to_plane(m, plane, origin=(0, 0, 0)):
    """map a drawing made in XY onto another plane: 'xy' (top, +z up), 'xz' (front, viewed from -y),
    'yz' (side, viewed from +x)."""
    if plane == "xy":
        R = np.eye(3)
    elif plane == "xz":      # X -> x, Y -> z, extrude (Z) -> -y  (readable from the front, -y)
        R = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    elif plane == "yz":      # X -> y, Y -> z, extrude -> +x     (readable from +x)
        R = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]
    else:
        raise ValueError(plane)
    return orient(m, R, origin)
