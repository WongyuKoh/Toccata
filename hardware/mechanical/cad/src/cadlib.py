"""Toccata CAD kit — small solid-modelling layer on manifold3d (exact booleans, always-manifold output).

Coordinates (same as the design docs):
  x across (module: 0 = C left boundary; world: 0 = A0 left boundary)
  y from the white-key front lip (+ = away from the player)
  z from the desk (0)
Units: mm.

Everything the generators build is a `Solid` (a thin wrapper around manifold3d.Manifold) so the
part files only read like a list of design features.
"""
import math
import os
import struct

import numpy as np
from manifold3d import CrossSection, FillRule, Manifold, OpType, set_circular_segments

set_circular_segments(64)

# ------------------------------------------------------------------ basic solids


def _cs(poly):
    pts = [(float(a), float(b)) for a, b in poly]
    return CrossSection([pts], FillRule.NonZero)


def _cs_multi(polys, rule=FillRule.EvenOdd):
    return CrossSection([[(float(a), float(b)) for a, b in p] for p in polys], rule)


def empty():
    return Manifold()


def prism_x(poly_yz, x0, x1):
    """(y, z) polygon extruded over x0..x1 (the geometry.json 'side' prisms)."""
    h = float(x1) - float(x0)
    if h <= 1e-9:
        return Manifold()
    m = _cs(poly_yz).extrude(h)  # (u=y, v=z, w=0..h)
    # (u, v, w) -> (x0 + w, u, v)
    return m.transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))


def prism_y(poly_xz, y0, y1):
    """(x, z) polygon extruded over y0..y1."""
    h = float(y1) - float(y0)
    if h <= 1e-9:
        return Manifold()
    m = _cs(poly_xz).extrude(h)  # (u=x, v=z, w)
    return m.transform(np.array([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0]], dtype=float))


def prism_z(poly_xy, z0, z1):
    h = float(z1) - float(z0)
    if h <= 1e-9:
        return Manifold()
    return _cs(poly_xy).extrude(h).translate((0, 0, z0))


def box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((float(x0), float(x1)))
    y0, y1 = sorted((float(y0), float(y1)))
    z0, z1 = sorted((float(z0), float(z1)))
    if x1 - x0 <= 1e-9 or y1 - y0 <= 1e-9 or z1 - z0 <= 1e-9:
        return Manifold()
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_z(cx, cy, z0, z1, d, seg=0):
    h = float(z1) - float(z0)
    m = Manifold.cylinder(h, d / 2.0, d / 2.0, seg or _seg(d))
    return m.translate((cx, cy, z0))


def cyl_x(cy, cz, x0, x1, d, seg=0):
    h = float(x1) - float(x0)
    m = Manifold.cylinder(h, d / 2.0, d / 2.0, seg or _seg(d))  # along z
    # z -> x : rotate about y by +90 (z axis goes to +x)
    return m.rotate((0, 90, 0)).translate((x0, cy, cz))


def cyl_y(cx, cz, y0, y1, d, seg=0):
    h = float(y1) - float(y0)
    m = Manifold.cylinder(h, d / 2.0, d / 2.0, seg or _seg(d))
    # z -> +y : rotate about x by -90
    return m.rotate((-90, 0, 0)).translate((cx, y0, cz))


def cone_z(cx, cy, z0, z1, d0, d1, seg=0):
    m = Manifold.cylinder(float(z1) - float(z0), d0 / 2.0, d1 / 2.0, seg or _seg(max(d0, d1)))
    return m.translate((cx, cy, z0))


def _seg(d):
    return int(max(24, min(96, math.ceil(math.pi * d / 0.35))))


def teardrop_x(cy, cz, x0, x1, d):
    """horizontal hole along x printed with the model upright (z up): circle + 45 deg roof point."""
    r = d / 2.0
    pts = []
    n = _seg(d)
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    tip = (cy, cz + r * math.sqrt(2))
    c = _cs(pts)
    t = _cs([(cy - r / math.sqrt(2), cz + r / math.sqrt(2)), (cy + r / math.sqrt(2), cz + r / math.sqrt(2)), tip])
    poly = (c + t).to_polygons()
    return prism_x(poly[0], x0, x1) if len(poly) == 1 else prism_x(max(poly, key=len), x0, x1)


def teardrop_y(cx, cz, y0, y1, d):
    """hole along y printed with z up: circle + 45 deg roof point (apex +z)."""
    r = d / 2.0
    n = _seg(d)
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    c = _cs(pts) + _cs([(cx - r / math.sqrt(2), cz + r / math.sqrt(2)), (cx + r / math.sqrt(2), cz + r / math.sqrt(2)), (cx, cz + r * math.sqrt(2))])
    poly = max(c.to_polygons(), key=len)
    return prism_y(poly, y0, y1)


def hexagon_z(cx, cy, z0, z1, af, rot=0.0):
    """hex prism, across-flats af, flats parallel to x when rot=0."""
    r = af / math.sqrt(3.0)
    pts = [(cx + r * math.cos(math.radians(30 + 60 * i + rot)), cy + r * math.sin(math.radians(30 + 60 * i + rot))) for i in range(6)]
    return prism_z(pts, z0, z1)


def union(items):
    items = [i for i in items if i is not None and not i.is_empty()]
    if not items:
        return Manifold()
    if len(items) == 1:
        return items[0]
    return Manifold.batch_boolean(items, OpType.Add)


def clean(m, min_vol=0.5):
    """drop sliver shells (|volume| < min_vol mm3) left where two model arcs nearly coincide."""
    comps = m.decompose()
    keep = [c for c in comps if c.volume() > min_vol]
    if len(keep) == len(comps):
        return m
    return union(keep)


def diff(a, cuts):
    cuts = [c for c in cuts if c is not None and not c.is_empty()]
    if not cuts:
        return a
    return a - union(cuts)


def inter(a, b):
    return a ^ b


def mirror_x(m, x=0.0):
    return m.mirror((1, 0, 0)).translate((2 * x, 0, 0))


def bbox(m):
    b = m.bounding_box()
    return tuple(round(v, 4) for v in b)


def volume(m):
    return m.volume()

# ------------------------------------------------------------------ text (glyph outlines -> solid)


_FONT = None
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def _font():
    global _FONT
    if _FONT is None:
        from matplotlib.font_manager import FontProperties
        _FONT = FontProperties(fname=FONT_PATH, weight="bold")
    return _FONT


_HEAVY = None
HEAVY_PATH = "/System/Library/Fonts/Supplemental/Arial Black.ttf"


def _heavy():
    global _HEAVY
    if _HEAVY is None:
        from matplotlib.font_manager import FontProperties
        _HEAVY = FontProperties(fname=HEAVY_PATH)
    return _HEAVY


def text_polys(s, size, heavy=False):
    from matplotlib.textpath import TextPath
    tp = TextPath((0, 0), s, size=size, prop=_heavy() if heavy else _font())
    polys = [p for p in tp.to_polygons() if len(p) >= 3]
    return polys


def text_xy(s, size, depth, x=0.0, y=0.0, z=0.0, halign="left", valign="baseline", rot=0.0, heavy=False):
    """raised text lying in the XY plane, base at z, height depth (+z). rot in degrees about z.
    heavy=True uses Arial Black (strokes about 0.19 x size) for text that is printed on a part."""
    polys = text_polys(s, size, heavy)
    if not polys:
        return Manifold()
    cs = _cs_multi(polys)
    if heavy:
        from manifold3d import JoinType
        cs = cs.offset(0.06, JoinType.Round)      # thin Arial Black bars ('#', '0', '8') up to about 0.5 for a 0.4 nozzle
    (x0, y0, x1, y1) = cs.bounds()
    dx = {"left": -x0, "center": -(x0 + x1) / 2, "right": -x1}[halign]
    dy = {"baseline": 0.0, "bottom": -y0, "center": -(y0 + y1) / 2, "top": -y1}[valign]
    cs = cs.translate((dx, dy))
    if rot:
        cs = cs.rotate(rot)
    return cs.extrude(depth).translate((x, y, z))


def orient(m, R, t=(0, 0, 0)):
    """apply a 3x3 rotation R then translation t."""
    M = np.zeros((3, 4))
    M[:, :3] = np.array(R, dtype=float)
    M[:, 3] = t
    return m.transform(M)


def rot_x(deg):
    a = math.radians(deg)
    return [[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]


def rot_y(deg):
    a = math.radians(deg)
    return [[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]]


def rot_z(deg):
    a = math.radians(deg)
    return [[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]]


def matmul(*Rs):
    out = np.eye(3)
    for R in Rs:
        out = out @ np.array(R, dtype=float)
    return out


def to_bed(m):
    """translate so the solid sits on z=0 with its xy bounding box starting at (0, 0)."""
    x0, y0, z0, x1, y1, z1 = m.bounding_box()
    return m.translate((-x0, -y0, -z0))

# ------------------------------------------------------------------ STL out


def mesh_arrays(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    f = np.asarray(mesh.tri_verts, dtype=np.int64)
    return v, f


def tidy(m):
    """merge sliver edges left by coplanar booleans (zero-area faces upset some STL checkers); stays manifold."""
    try:
        t = m.simplify(0.0005)
        if not t.is_empty() and abs(t.volume() - m.volume()) < 1e-3 * max(1.0, m.volume()):
            return t
    except Exception:
        pass
    return m


def write_stl(m, path, header=""):
    """binary STL; header (ASCII, <= 80 bytes) carries the part id and bbox."""
    v, f = mesh_arrays(tidy(m))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1)
    # drop zero-height slivers: manifold keeps them as separate topology, but in a triangle-soup STL they become
    # zero-volume shells / 4-face edges that mesh checkers (and some slicers) flag as non-watertight
    emax = np.max(np.stack([np.linalg.norm(tri[:, i] - tri[:, (i + 1) % 3], axis=1) for i in range(3)]), axis=0)
    keep = ln / np.maximum(emax, 1e-12) > 1e-6
    tri, n, ln, f = tri[keep], n[keep], ln[keep], f[keep]
    ln[ln == 0] = 1
    n = n / ln[:, None]
    h = header.encode("ascii", "replace")[:80].ljust(80, b" ")
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n
    rec["v"] = tri
    with open(path, "wb") as fh:
        fh.write(h)
        fh.write(struct.pack("<I", len(f)))
        fh.write(rec.tobytes())
    return len(f)


def check_solid(m):
    """manifold3d output is watertight by construction; report genus / tri count / empties."""
    return {
        "empty": m.is_empty(),
        "tris": m.num_tri(),
        "genus": m.genus(),
        "volume_mm3": round(m.volume(), 2),
        "parts": len(m.decompose()),
        "bbox": bbox(m) if not m.is_empty() else None,
    }
