"""A19 (2026-11-16) no drill anywhere in the one-octave build: every hole is printed to its final size.

The user, after A18 (lever hub D4.3 / fin bosses D4.5 already printed to take the D4 rod undrilled):
  '드릴 대신에 3D 프린팅에서 반지름을 1mm 씩 늘리는 식으로 할거야'
The holes that still needed the D4.0 / D1.9..2.0 drill were all press / locating holes - the bench-jig rod stubs (T1a K, L),
the dummy-lever hub (T2) and the balance-pin holes (rail, end-piece beds, jig spare pin). A plain bore 1 mm bigger in
radius would let a rod stub flop (the jig would no longer put the key where the frame does) and drop the D2 pins, so:
  * press / locating holes: the bore is the old radius + 1 mm (as the user asked) and three vertical crush ribs bring the
    grip back to the old drilled size. The rod / pin shaves the rib tips instead of a drill shaving the whole hole, so the
    FDM size error no longer matters and nothing is drilled.
      - balance pins (rail, end-piece beds): D1.95 -> bore D3.95, rib tips D1.95 (pin D2: light press)
      - T1a spare pin: D1.9 -> bore D3.9, rib tips D1.9
      - T1a K stub: D3.9 -> bore D5.9, rib tips D3.9; the two K posts grow 1.0 each way in y and 1.0 up so the walls
        stay 0.65 (posts sit outside every key, X 12.3..16.3)
      - T1a L stub: bore D4.8 only (wall 0.65): the key's thin tail passes 1.2 in front of the L posts, so they cannot grow
        forward; the posts grow 1.0 up for the roof. Rib tips D3.9.
  * running fit: the T2 dummy-lever hub turns on the L stub like a real lever -> D4.3, the A18 lever hub size, no ribs.
  * the capstan nut slot's 0.4 membrane is pierced by the M3 screw itself (no D3 drill fallback any more).
Ribs: 3 per hole, base 1.2 / tip 0.5 (pins 1.0 / 0.4), along the print z for vertical holes. Horizontal teardrop holes
(T1a K, L, printed upright) take one fin hanging from the roof (V tip, 45 deg faces) and two ribs at 240 / 300 deg whose
undersides stay 40 deg from horizontal - support-free (check_support 30 deg).
The bench tools come from key-action-v4/printables/tools (r4.4, read-only here); build_all writes the A19 versions of
T1a and T2 from those STLs (print frame) instead of copying them.
"""
import math
import os

from cadlib import box, cyl_z, diff, prism_x, prism_y, prism_z, teardrop_x, teardrop_y, union

A19_ON = True
A19 = {
    "r_add": 1.0,                                          # the user's '+1 mm radius'
    "rib_base": 1.2, "rib_tip": 0.5,                       # rod ribs (T1a K, L)
    "pin_rib_base": 1.0, "pin_rib_tip": 0.4,               # pin ribs
    "pin_tip": 1.95, "pin_bore": 3.95,                     # balance pin holes (FEAT bal_pin_hole_d = the old drilled size)
    "jig_pin_tip": 1.9, "jig_pin_bore": 3.9,               # T1a spare pin
    "k_tip": 3.9, "k_bore": 5.9, "k_grow": 1.0, "k_top": 27.0,
    "l_tip": 3.9, "l_bore": 4.8, "l_top": 38.0,
    "t2_hub": 4.3,
}
TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "key-action-v4", "printables", "tools", "stl"))


def _rib_poly(cx, cy, ang, r_wall, r_tip, base, tip, ext=0.4):
    """trapezoid rib from the bore wall (radius r_wall, width base; carried ext further into the wall) to the tip
    (radius r_tip, width tip), on the ray at angle ang (deg) from the centre (cx, cy)."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)                   # outward
    px, py = -uy, ux                                     # across
    k = (base - tip) / 2.0 / max(r_wall - r_tip, 1e-6)   # half-width growth per mm outward
    r_out = r_wall + ext
    h_out = base / 2.0 + k * ext
    return [(cx + ux * r_tip + px * tip / 2, cy + uy * r_tip + py * tip / 2),
            (cx + ux * r_out + px * h_out, cy + uy * r_out + py * h_out),
            (cx + ux * r_out - px * h_out, cy + uy * r_out - py * h_out),
            (cx + ux * r_tip - px * tip / 2, cy + uy * r_tip - py * tip / 2)]


def ribbed_hole_z(cx, cy, z0, z1, d_bore, d_tip, base, tip, a0=90.0):
    """CUT for a vertical press hole: bore d_bore minus three ribs (tips on d_tip). Subtract it from a solid that is
    solid there: the ribs stay."""
    ribs = [prism_z(_rib_poly(cx, cy, a0 + 120 * i, d_bore / 2, d_tip / 2, base, tip), z0 - 0.02, z1 + 0.02) for i in range(3)]
    return diff(cyl_z(cx, cy, z0, z1, d_bore), ribs)


def pin_hole(cx, cy, z0, z1):
    """A19 balance-pin hole (rail, end-piece beds): bore D3.95, 3 crush ribs to D1.95 (pin D2). Old: cyl D1.95 + drill."""
    if not A19_ON:
        return cyl_z(cx, cy, z0, z1, A19["pin_tip"])
    return ribbed_hole_z(cx, cy, z0, z1, A19["pin_bore"], A19["pin_tip"], A19["pin_rib_base"], A19["pin_rib_tip"])


def _teardrop_ribs_yz(cy, cz, d_bore, d_tip, base, tip):
    """(y, z) polygons of the ribs of a horizontal teardrop hole printed with z up: two ribs at 240 / 300 deg, one fin
    hanging from the roof with a 45 deg V tip."""
    rb, rt = d_bore / 2.0, d_tip / 2.0
    out = [_rib_poly(cy, cz, a, rb, rt, base, tip) for a in (240.0, 300.0)]
    apex = cz + rb * math.sqrt(2) + 0.4
    h = tip / 2.0
    out.append([(cy, cz + rt), (cy + h, cz + rt + h), (cy + base / 2, apex), (cy - base / 2, apex), (cy - h, cz + rt + h)])
    return out


def ribbed_teardrop_x(cy, cz, x0, x1, d_bore, d_tip, base, tip):
    """(cut, ribs) for a horizontal press hole along x: cut the teardrop, then add the ribs back (clipped to the bore)."""
    cut = teardrop_x(cy, cz, x0, x1, d_bore)
    ribs = union([prism_x(p, x0, x1) for p in _teardrop_ribs_yz(cy, cz, d_bore, d_tip, base, tip)])
    return cut, ribs ^ teardrop_x(cy, cz, x0, x1, d_bore + 0.3)


def ribbed_teardrop_y(cx, cz, y0, y1, d_bore, d_tip, base, tip):
    """(cut, ribs) for a horizontal press hole along y (the coupon)."""
    cut = teardrop_y(cx, cz, y0, y1, d_bore)
    ribs = union([prism_y(p, y0, y1) for p in _teardrop_ribs_yz(cx, cz, d_bore, d_tip, base, tip)])
    return cut, ribs ^ teardrop_y(cx, cz, y0, y1, d_bore + 0.3)


# ------------------------------------------------------------------ the bench tools (print frame of the r4.4 STLs)
# T1a bench jig STL: print = (X + 36, y + 8, z - 3)   (X = x - the key's pin x; model y, z)
# T2 capstan gauge STL: print = (y - 119, z - 28.9, X + 6.3)   (printed on its -X side)
J_OFF = (36.0, 8.0, -3.0)
K = (141.0, 21.5)
L = (203.25, 33.5)


def _load(fn):
    import numpy as np
    import trimesh
    from manifold3d import Manifold, Mesh
    tm = trimesh.load(os.path.join(TOOLS, fn), process=True)
    tm.merge_vertices()
    M = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    if str(M.status()) != "Error.NoError":
        raise RuntimeError("no_drill: %s is not a closed solid" % fn)
    return M


def _jp(x, y, z):
    return (x + J_OFF[0], y + J_OFF[1], z + J_OFF[2])


def bench_jig():
    """T1a with A19 holes, in its print frame (bed z0)."""
    m = _load("tool_bench_jig.stl")
    g = A19["k_grow"]
    adds, cuts, ribs = [], [], []
    # K posts X +-12.3..16.3, y138.40..143.6, z5..26 -> y137.40..144.6, z..27
    for (xa, xb) in ((-16.3, -12.3), (12.3, 16.3)):
        a = _jp(xa, 138.40 - g, 5.0)
        b = _jp(xb, 143.6 + g, A19["k_top"])
        adds.append(box(a[0], b[0], a[1], b[1], a[2], b[2]))
    # L posts X +-6.8..10.8, y200.20..207.5, z5..37 -> top 38 (front stays: the key tail passes 1.2 in front)
    for (xa, xb) in ((-10.8, -6.8), (6.8, 10.8)):
        a = _jp(xa, 200.20, 5.0)
        b = _jp(xb, 207.5, A19["l_top"])
        adds.append(box(a[0], b[0], a[1], b[1], a[2], b[2]))
    m = union([m] + adds)
    # K bore X -16.31..15.3 (right end blind, 1.0 wall), L bore X -10.81..9.8
    for (c, xr, d, t) in ((K, (-16.31, 15.3), A19["k_bore"], A19["k_tip"]), (L, (-10.81, 9.8), A19["l_bore"], A19["l_tip"])):
        p0 = _jp(xr[0], c[0], c[1])
        p1 = _jp(xr[1], c[0], c[1])
        cu, ri = ribbed_teardrop_x(p0[1], p0[2], p0[0], p1[0], d, t, A19["rib_base"], A19["rib_tip"])
        cuts.append(cu)
        ribs.append(ri)
    # spare balance pin X0, y135.3, z10.3..19.0 (rail block top)
    p = _jp(0.0, 135.3, 10.3)
    cuts.append(ribbed_hole_z(p[0], p[1], p[2], 19.01 + J_OFF[2], A19["jig_pin_bore"], A19["jig_pin_tip"],
                              A19["pin_rib_base"], A19["pin_rib_tip"]))
    return union([diff(m, cuts)] + ribs)


def capstan_gauge():
    """T2 (dummy lever) with the A19 hub bore D4.3 (running fit on the L stub), in its print frame."""
    m = _load("tool_capstan_gauge.stl")
    u, v = L[0] - 119.0, L[1] - 28.9                     # hub axis = print z
    return diff(m, [cyl_z(u, v, -0.5, 13.1, A19["t2_hub"])])


TOOL_NOTE = {
    "tool_bench_jig.stl": "; A19 드릴 없음: K 봉 토막 구멍 Ø5.9(반지름 +1)·L 구멍 Ø4.8(앞에 건반 꼬리가 1.2 앞을 지나 더 못 키움)에 "
                          "크러시 리브 3줄(끝 Ø3.9) - Ø4 봉 토막을 눌러 넣으면 리브 끝이 깎이며 꽉 물림. K 기둥은 y로 1.0씩·위로 1.0, "
                          "L 기둥은 위로 1.0 키움(벽 0.65). 예비 밸런스 핀 구멍 Ø3.9 + 리브(끝 Ø1.9)",
    "tool_capstan_gauge.stl": "; A19 드릴 없음: 허브 구멍 Ø4.3(레버 허브와 같은 돌아가는 맞춤) - L 봉 토막에서 자유롭게 돎",
}


def tool_solids():
    """{STL name in key-action-v4/printables/tools/stl: A19 solid} for build_all."""
    if not A19_ON:
        return {}
    return {"tool_bench_jig.stl": bench_jig(), "tool_capstan_gauge.stl": capstan_gauge()}
