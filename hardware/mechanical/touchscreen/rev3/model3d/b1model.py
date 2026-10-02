"""R31 rev 3 (B1 = Waveshare 7-DSI-TOUCH-C) - 3D preview model for review BEFORE the CAD session builds it.

Library: every solid of the touchscreen group + a simplified L2 context, built with the CAD kit (cad_copy/src/cadlib.py,
manifold3d). All sizes come from ../design/numbers.json (rev 3 design) and the final L2 json (../L2_cu.json, falls back
to ../L2_cu_provisional.json); the speaker-pod outline comes from cad_copy/spec/body_L2.json (the file L2_cu.json names
as its source). Estimates that neither file gives are collected in EST (each one is printed in the report).

Frames (rev-2 convention):
  world  x across from the A0 left boundary, y away from the player from the white-key front lip, z up from the desk
  cradle xr = x - XC, u = from the glass bottom edge up the screen, w = from the glass front face backward
  world = M(theta) @ [xr, u, w, 1]  (det -1; manifold3d flips the winding itself)
"""
import hashlib
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
T3 = os.path.normpath(os.path.join(HERE, ".."))
CAD = os.path.join(T3, "cad_copy")
sys.path.insert(0, os.path.join(CAD, "src"))

from manifold3d import CrossSection, FillRule, Manifold, Mesh  # noqa: E402
from cadlib import box, cyl_z, prism_x, prism_y, union, diff  # noqa: E402

# ------------------------------------------------------------------ inputs
L2_FINAL = os.path.join(T3, "L2_cu.json")
L2_PROV = os.path.join(T3, "L2_cu_provisional.json")
L2_PATH = L2_FINAL if os.path.exists(L2_FINAL) else L2_PROV
L2_IS_FINAL = L2_PATH == L2_FINAL
L2 = json.load(open(L2_PATH))
L2_MD5 = hashlib.md5(open(L2_PATH, "rb").read()).hexdigest()
BL2_PATH = os.path.join(CAD, "spec", "body_L2.json")
BL2 = json.load(open(BL2_PATH))
N_PATH = os.path.join(T3, "design", "numbers.json")
N = json.load(open(N_PATH))
N_MD5 = hashlib.md5(open(N_PATH, "rb").read()).hexdigest()
PL = N["placement"]
assert str(N.get("revision", "")).startswith("3a"), ("numbers.json revision", N.get("revision"))

SRC = {"numbers": "touch3/design/numbers.json (수정 3판 3a)", "numbers_md5": N_MD5, "revision": N["revision"], "l2": os.path.relpath(L2_PATH, T3) + (" (확정)" if L2_IS_FINAL else " (잠정)"),
       "body_l2": "cad_copy/spec/body_L2.json (스피커 옆모양)", "l2_md5": L2_MD5}

# consistency: the design must have been computed from the same L2 file
assert os.path.basename(PL["source"]) == os.path.basename(L2_PATH), ("numbers.json placement source", PL["source"], L2_PATH)
_zone = L2["touchscreen_lid_zone_for_W1"]
assert [float(v) for v in _zone["x"]] == PL["lid"]["x"] and [float(v) for v in _zone["y"]] == PL["lid"]["y"]
assert abs(_zone["top_z"] - PL["lid"]["top_z"]) < 1e-9 and abs(L2["speakers_top_z"] - PL["speaker_top_z"]) < 1e-9
assert BL2["centre"]["x"] == L2["centre"]["x"] and BL2["overall"]["z_max"] == L2["speakers_top_z"]

# ------------------------------------------------------------------ placement block (the ONE block every coordinate uses)
XC = PL["x_centre"]
LID_X, LID_Y = PL["lid"]["x"], PL["lid"]["y"]
LID_TOP, LID_T, LID_BED = PL["lid"]["top_z"], PL["lid"]["plate_t"], PL["lid"]["bed_z"]
AY, AZ = PL["hinge_axis_yz"]
KEEP = PL["keepout"]
HG, CR, SC, LG = N["hinge"], N["cradle"], N["screen"], N["leg"]
UA, WA = HG["axis_cradle_uw"]
TH_USE, TH_HEEL, TH_FOLD = HG["tilt_use_deg"], HG["heel_contact_deg"], 90.0
assert tuple(HG["axis_yz"]) == (AY, AZ)

# estimates not given by numbers.json / L2 json (all shown in the report as 추정)
EST = {
    "screen_back_recess": 2.0,        # depth of the connector window in the screen back (drawing shows a window, depth unknown)
    "zif_h": 2.0,                     # 22P 0.5 mm ZIF body height above the recess floor (typical 2.0)
    "mx_h": 2.0,                      # MX1.25 2P horizontal header height (typical ~2)
    "ribbon_mouth_w": 7.0,            # ribbon centre at the ZIF mouth = recess floor + zif_h / 2
    "screen_hole_depth": 4.0,         # M2.5 thread depth in the screen corners (unknown: design rule uses min(depth-0.5, 4))
    "m25_head": (4.5, 1.8),           # M2.5x6 head dia x height
    "m3_head": (5.7, 1.65),           # ISO 7380 M3 button head (as v13)
    "lid_rib_t": 2.0, "lid_wall_t": 3.0,
    "lid_ribs_x": (541.0, 611.0, 681.0),   # lid underside ribs along y (CAD decides; kept clear of slots / blocks)
    "lid_ribs_y": (262.0, 290.0),          # lid underside ribs along x
    "tab_w": (2.0, 6.0),              # w range of the small feature on the glass bottom edge (drawing gives xr / proud only)
    "insert_od": 4.2,                 # M3 heat-set insert outer dia in the seam rail (numbers.json gives length 4 / hole depth 4.5 only)
    "stack": 0.27,                    # layer offset of a folded ribbon (0.9 x thickness, so the union stays one piece)
    "ramp_from_recess": (5.5, 1.0),   # ribbon / lead climb from the recess (w7) onto the screen back between u30.2+5.5 .. u30.2+1.0
    "lid_boss_d": 8.0,
    "wire_d": 1.1, "wire_pitch": 1.3, # silicone jumper / MX1.25 lead
    "dupont": (2.5, 2.5, 14.0),       # F/F jumper housing on a GPIO pin
    "grille_d": 115.0, "grille_t": 2.0,
    "feet_d": 28.0,
    "gpio_pin_above_base": 6.0,       # 2.54 header: pin tip 6.0 above the 2.5 plastic base (board top 24.1 + 2.5 + 6.0 = 32.6)
    "pi_board_t": 1.6,
    "cover_dome_skin": 1.2,
    "loop_len": N["ribbon"]["in_cradle_parts"]["hinge_loop"],
}


def M(theta):
    """3 x 4: cradle (xr, u, w) -> world (x, y, z) at tilt theta (back from vertical)."""
    t = math.radians(theta)
    s, c = math.sin(t), math.cos(t)
    return np.array([[1, 0, 0, XC],
                     [0, s, c, AY - UA * s - WA * c],
                     [0, c, -s, AZ - UA * c + WA * s]], dtype=float)


def M4(theta):
    m = np.eye(4)
    m[:3] = M(theta)
    return m


# the design's pose matrices must be reproduced exactly
for _k, _th in (("cradle_use", TH_USE), ("cradle_heel", TH_HEEL), ("cradle_fold", TH_FOLD)):
    assert np.abs(np.array(N["poses"][_k], float) - M4(_th)).max() < 0.01, _k


def to_world(p, theta):
    xr, u, w = p
    return M(theta) @ np.array([xr, u, w, 1.0])


def dir_world(d, theta):
    return M(theta)[:, :3] @ np.array(d, float)


def to_local(y, z, theta):
    t = math.radians(theta)
    s, c = math.sin(t), math.cos(t)
    dy, dz = y - AY, z - AZ
    return (UA + dy * s + dz * c, WA + dy * c - dz * s)


def place(m, theta):
    return m.transform(M(theta))


# ------------------------------------------------------------------ 2D helpers
def _cs(pts):
    return CrossSection([[(float(a), float(b)) for a, b in pts]], FillRule.NonZero)


def circle_pts(cx, cy, r, n=64):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def hull2(pts):
    return [tuple(p) for p in CrossSection.hull_points([(float(a), float(b)) for a, b in pts]).to_polygons()[0]]


def poly_union(*polys):
    cs = _cs(polys[0])
    for p in polys[1:]:
        cs = cs + _cs(p)
    out = cs.to_polygons()
    assert len(out) == 1
    return [tuple(p) for p in out[0]]


def cyl_along(axis, c1, c2, a0, a1, d, n=48):
    """cylinder along 'x' (c = (y, z)), 'y' (c = (x, z)) or 'z' (c = (x, y))."""
    pts = circle_pts(c1, c2, d / 2.0, n)
    return {"x": prism_x, "y": prism_y, "z": lambda p, a, b: _prism_z(p, a, b)}[axis](pts, a0, a1)


def _prism_z(poly, z0, z1):
    return _cs(poly).extrude(float(z1) - float(z0)).translate((0, 0, float(z0)))


# ------------------------------------------------------------------ swept strips / tubes (ribbon, wires)
def fillet(points, R, n=10):
    """polyline -> polyline with every corner replaced by an arc of radius R (clipped to half the neighbouring segments)."""
    P = [np.array(p, float) for p in points]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u1 = (b - a) / np.linalg.norm(b - a)
        u2 = (c - b) / np.linalg.norm(c - b)
        cosang = float(np.clip(u1 @ u2, -1, 1))
        phi = math.acos(cosang)
        if phi < 1e-4:
            out.append(b)
            continue
        d = R * math.tan(phi / 2)
        d = min(d, 0.49 * np.linalg.norm(b - a), 0.49 * np.linalg.norm(c - b))
        r = d / math.tan(phi / 2)
        p0, p1 = b - u1 * d, b + u2 * d
        bis = (u2 - u1)
        bis = bis / np.linalg.norm(bis)
        ctr = b + bis * (r / math.cos(phi / 2))
        v0, v1 = p0 - ctr, p1 - ctr
        for k in range(n + 1):
            t = k / n
            # slerp between v0 and v1
            om = math.acos(float(np.clip(v0 @ v1 / (np.linalg.norm(v0) * np.linalg.norm(v1)), -1, 1)))
            if om < 1e-9:
                v = v0
            else:
                v = (math.sin((1 - t) * om) * v0 + math.sin(t * om) * v1) / math.sin(om)
            out.append(ctr + v)
    out.append(P[-1])
    # drop duplicates
    clean = [out[0]]
    for p in out[1:]:
        if np.linalg.norm(p - clean[-1]) > 1e-6:
            clean.append(p)
    return clean


def _closed_tube_mesh(rings):
    """rings: list of (k, 3) arrays (same k), consecutive stations -> closed Manifold."""
    k = len(rings[0])
    V = np.vstack(rings)
    F = []
    for i in range(len(rings) - 1):
        for j in range(k):
            a, b = i * k + j, i * k + (j + 1) % k
            c, d = (i + 1) * k + (j + 1) % k, (i + 1) * k + j
            F += [(a, b, c), (a, c, d)]
    # caps (fan around a centre vertex)
    c0 = len(V)
    c1 = c0 + 1
    V = np.vstack([V, rings[0].mean(axis=0), rings[-1].mean(axis=0)])
    last = (len(rings) - 1) * k
    for j in range(k):
        F.append((c0, (j + 1) % k, j))
        F.append((c1, last + j, last + (j + 1) % k))
    F = np.array(F, dtype=np.int64)
    tri = V[F]
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
    if vol < 0:
        F = F[:, ::-1]
    m = Manifold(Mesh(vert_properties=V.astype(np.float32), tri_verts=F.astype(np.uint32)))
    return m


def sweep_rect(points, wdir, width, thick):
    """flat strip (ribbon): centreline points, width direction (one vector or one per point)."""
    P = [np.array(p, float) for p in points]
    W = [np.array(wdir, float)] * len(P) if np.ndim(wdir) == 1 else [np.array(v, float) for v in wdir]
    rings = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
        t = t / np.linalg.norm(t)
        w = W[i] - (W[i] @ t) * t
        w = w / np.linalg.norm(w)
        n = np.cross(t, w)
        hw, ht = width / 2.0, thick / 2.0
        rings.append(np.array([p + w * hw + n * ht, p - w * hw + n * ht, p - w * hw - n * ht, p + w * hw - n * ht]))
    return _closed_tube_mesh(rings)


def sweep_tube(points, d, seg=10):
    P = [np.array(p, float) for p in points]
    T = []
    for i in range(len(P)):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        T.append(t / np.linalg.norm(t))
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    w = ref - (ref @ T[0]) * T[0]
    w /= np.linalg.norm(w)
    rings = []
    for i, p in enumerate(P):
        w = w - (w @ T[i]) * T[i]
        w /= np.linalg.norm(w)
        n = np.cross(T[i], w)
        rings.append(np.array([p + (d / 2) * (math.cos(2 * math.pi * k / seg) * w + math.sin(2 * math.pi * k / seg) * n) for k in range(seg)]))
    return _closed_tube_mesh(rings)


def bezier_loop(p0, t0, p3, t3, length, n=40):
    """cubic Bezier from p0 (leaving along t0) to p3 (arriving along t3) whose arc length = length."""
    p0, p3, t0, t3 = (np.array(v, float) for v in (p0, p3, t0, t3))

    def pts(k):
        c1, c2 = p0 + t0 * k, p3 - t3 * k
        ts = np.linspace(0, 1, n + 1)[:, None]
        return (1 - ts) ** 3 * p0 + 3 * (1 - ts) ** 2 * ts * c1 + 3 * (1 - ts) * ts ** 2 * c2 + ts ** 3 * p3

    def L(k):
        q = pts(k)
        return float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum())
    lo, hi = 0.0, 60.0
    if L(lo) > length:
        return pts(lo), L(lo)
    for _ in range(60):
        mid = (lo + hi) / 2
        if L(mid) < length:
            lo = mid
        else:
            hi = mid
    return pts(lo), L(lo)


# ------------------------------------------------------------------ screen dummy (local)
GW, GH = SC["glass"]
BODY = SC["body"]
AX0, AX1 = (v - XC for v in SC["active_x"])
AU0, AU1 = SC["active_u"]
WIN = SC["window"]
REC0 = BODY - EST["screen_back_recess"]


def screen_local():
    gx0, gx1 = -GW / 2, GW / 2
    front = 0.2
    body = union([box(gx0, gx1, 0, GH, front, BODY),
                  box(SC["emboss"]["xr"][0], SC["emboss"]["xr"][1], SC["emboss"]["u"][0], SC["emboss"]["u"][1], BODY - 0.01, BODY + SC["emboss"]["h"])])
    cuts = [box(WIN["xr"][0], WIN["xr"][1], WIN["u"][0], WIN["u"][1], REC0, BODY + 0.01)]
    for xr in SC["holes"]["xr"]:
        for u in SC["holes"]["u"]:
            cuts.append(cyl_along("z", xr, u, BODY - EST["screen_hole_depth"], BODY + 0.01, 2.5))
    body = diff(body, cuts)
    bezel = diff(box(gx0, gx1, 0, GH, 0, front), [box(AX0, AX1, AU0, AU1, -0.01, front + 0.01)])
    active = box(AX0, AX1, AU0, AU1, 0, front)
    f, p = SC["fpc"], SC["pwr"]
    zif = box(f["xr"][0], f["xr"][1], f["u"][0], f["u"][1], REC0, REC0 + EST["zif_h"])
    mx = box(p["xr"][0], p["xr"][1], p["u"][0], p["u"][1], REC0, REC0 + EST["mx_h"])
    nt = CR["notch"]
    tab = box(nt["feature_xr"][0], nt["feature_xr"][1], -nt["feature_proud"], 0.01, EST["tab_w"][0], EST["tab_w"][1])
    return {"body": body, "bezel": bezel, "active": active, "zif": zif, "mx": mx, "tab": tab}


# ------------------------------------------------------------------ cradle (local)
X0, X1 = CR["xr"]
U0, U1 = CR["u"]
W0, W1 = CR["w"]
PLI, PLO = CR["plate"]
RIM, CLR = CR["rim"], CR["clr"]
WL = CR["walls"]
IX0, IX1 = -WL["side_inner_xr"], WL["side_inner_xr"]      # side walls: glass + 0.3 each side
IU0, IU1 = WL["bottom_u"][1], WL["top_u"][0]              # 3a: glass bottom edge rests on the bottom wall (u0); top gap 0.5
assert abs(IX1 - (GW / 2 + WL["side_gap"])) < 1e-6 and abs(IU1 - (GH + WL["top_gap"])) < 1e-6 and IU0 == WL["bottom_gap"]
assert WL["bottom_u"][0] == U0 and WL["top_u"][1] == U1 and WL["front_w"] == W0
CH = LG["channel"]
BO = CR["bosses"]
INS = CR["insp"]
NOTCH = CR["notch"]
RIB_T = CR["rib_t"]
EAR = CR["ear"]


def ear_profile():
    """(u, w) outline of the hinge ear = numbers.json cradle.ear.profile_uw (3a: hull of hub R4.2, bottom attachment u-2.5 w8..13
    and the heel point only). Used as given - no trimming."""
    pts = [tuple(p) for p in EAR["profile_uw"]]
    h = hull2(pts)
    assert len(h) == len(pts), "ear profile must be convex (as defined)"
    return pts, tuple(EAR["heel_uw"])


def ear_profile_rev3_first():
    """the ear outline of the first rev-3 drawings (extra lobe point) - only used to show that the check catches it."""
    pts = [tuple(p) for p in EAR["profile_uw"]] + [tuple(EAR["check"]["rev3_first_lobe"]["lobe_uw"])]
    return hull2(pts)


def clevis_profile():
    cu, cw = LG["pivot_cradle_uw"]
    r = LG["clevis"]["R"]
    return hull2(circle_pts(cu, cw, r, 64) + [(cu - r, PLO - 0.01), (cu + r * math.sqrt(2.0), PLO - 0.01)])


def cradle_local(ear_pts=None):
    add = [diff(box(X0, X1, U0, U1, W0, W1), [box(IX0, IX1, IU0, IU1, W0 - 0.01, PLI), box(IX0, IX1, IU0, IU1, PLO, W1 + 0.01)])]
    cw0, cw1 = CH["xr_walls"][0][0], CH["xr_walls"][1][1]           # -7.3 .. 7.3 (leg channel)
    for ur in CR["cross_ribs_u"]:
        add.append(box(IX0 - 0.01, cw0, ur - RIB_T / 2, ur + RIB_T / 2, PLO - 0.01, W1))
        add.append(box(cw1, IX1 + 0.01, ur - RIB_T / 2, ur + RIB_T / 2, PLO - 0.01, W1))
    for (a, b) in CH["xr_walls"]:
        add.append(box(a, b, CH["u"][0], IU1 + 0.01, PLO - 0.01, W1))
    # rib ring round the inspection window, 1.8 outside it (cover ledge 1.5 + 0.3)
    wx0, wx1 = INS["xr"]
    wu0, wu1 = INS["u"]
    g, t = 1.8, 2.0
    add.append(diff(box(wx0 - g - t, wx1 + g + t, wu0 - g - t, wu1 + g + t, PLO - 0.01, W1),
                    [box(wx0 - g, wx1 + g, wu0 - g, wu1 + g, PLO - 0.02, W1 + 0.01)]))
    for p in CR["pads"]:
        add.append(box(p["xr"][0], p["xr"][1], p["u"][0], p["u"][1], PLO - 0.01, W1))
    bw0, bw1 = BO["w"]
    fw = BO["fill_to_side_wall"]
    for xr in BO["xr"]:
        for u in BO["u"]:
            add.append(cyl_along("z", xr, u, bw0, bw1, BO["d"]))
        # 3a: each boss joined to the side wall by a block 8 wide (u) over w8..16
        fx = next(r for r in fw["xr"] if r[0] <= xr <= r[1])
        for u in BO["u"]:
            add.append(box(fx[0] - (0.01 if fx[0] < 0 else 0), fx[1] + (0.01 if fx[1] > 0 else 0),
                           u - fw["width_u"] / 2, u + fw["width_u"] / 2, bw0, bw1))
    hp = CR["hold_pad"]
    add.append(box(hp["xr"][0], hp["xr"][1], hp["u"][0], hp["u"][1], hp["w"][0], PLI + 0.01))
    ep, _ = ear_profile() if ear_pts is None else (ear_pts, None)
    for side in ("left", "right"):
        e0, e1 = HG[side]["ear"]
        add.append(prism_x(ep, e0, e1))
    cp = clevis_profile()
    add += [prism_x(cp, *LG["clevis"]["near"]), prism_x(cp, *LG["clevis"]["far"])]
    cl = LG["clip"]
    for (a, b) in cl["xr_bodies"]:
        add.append(box(a, b, cl["u"][0], cl["u"][1], PLO - 0.01, cl["back_w"]))
    lip = cl["catch"]
    add.append(box(cl["xr_bodies"][0][1], cl["xr_bodies"][0][1] + lip, cl["u"][0], cl["u"][1], cl["catch_from_w"], cl["back_w"]))
    add.append(box(cl["xr_bodies"][1][0] - lip, cl["xr_bodies"][1][0], cl["u"][0], cl["u"][1], cl["catch_from_w"], cl["back_w"]))
    cr = union(add)
    cuts = []
    gr = CR["groove"]
    cuts.append(box(gr["xr"][0], gr["xr"][1], gr["u"][0] - 0.01, gr["u"][1], gr["w"][0], gr["w"][1] + 0.01))
    # 3a: bottom-wall notch for the small feature on the glass bottom edge (through the wall, front part only)
    cuts.append(box(NOTCH["xr"][0], NOTCH["xr"][1], NOTCH["u"][0] - 0.01, NOTCH["u"][1] + 0.01, NOTCH["w"][0] - 0.01, NOTCH["w"][1]))
    cuts.append(box(wx0, wx1, wu0, wu1, PLI - 0.01, W1 + 0.01))
    for xr in BO["xr"]:
        for u in BO["u"]:
            cuts.append(cyl_along("z", xr, u, BO["face_w"] - 0.01, W1 + 0.01, BO["hole_d"]))
            cuts.append(cyl_along("z", xr, u, BO["seat_w"], W1 + 0.01, BO["cbore_d"]))
    ch = CR["rib_relief_at_cheeks"]["chamfer"]
    cuts.append(prism_x([(U0 - 0.01, W1 - ch), (U0 - 0.01, W1 + 0.01), (U0 + ch, W1 + 0.01)], X0 - 0.01, X1 + 0.01))
    for side in ("left", "right"):
        e0, e1 = HG[side]["ear"]
        cuts.append(cyl_along("x", UA, WA, e0 - 0.01, e1 + 0.01, 3.3))
    pu, pw = LG["pivot_cradle_uw"]
    cuts.append(cyl_along("x", pu, pw, LG["clevis"]["near"][0] - 0.01, LG["clevis"]["near"][1] + 0.01, 3.3))
    cuts.append(cyl_along("x", pu, pw, LG["clevis"]["far"][0] - 0.01, LG["clevis"]["far"][1] + 0.01, 2.5))
    return diff(cr, cuts)


def cover_local():
    """inspection-window cover: plug (window - 0.2, plate depth - 0.2), flange (window + 1.5, 2 thick on w13), dome over the fold."""
    wx0, wx1 = INS["xr"]
    wu0, wu1 = INS["u"]
    cv = INS["cover"]
    fl, fit, t = cv["flange"], cv["plug_under"], cv["t"]
    dm = cv["dome"]
    sk = EST["cover_dome_skin"]
    plug = box(wx0 + fit, wx1 - fit, wu0 + fit, wu1 - fit, PLI + fit, PLO + 0.01)
    flange = box(wx0 - fl, wx1 + fl, wu0 - fl, wu1 + fl, PLO, PLO + t)
    dome = box(dm["xr"][0] - sk, dm["xr"][1] + sk, dm["u"][0] - sk, dm["u"][1] + sk, PLO, dm["inner_to_w"] + sk)
    hollow = box(dm["xr"][0], dm["xr"][1], dm["u"][0], dm["u"][1], PLI - 0.1, dm["inner_to_w"])
    return diff(union([plug, flange, dome]), [hollow])


# ------------------------------------------------------------------ leg
PIV_UW = tuple(LG["pivot_cradle_uw"])
LEG_T = LG["section"][1]
LEG_R = LEG_T / 2.0
LEG_X = LG["x"]


def capsule_x(a, b, x0, x1, r=LEG_R, hole_at=None):
    solid = prism_x(hull2(circle_pts(a[0], a[1], r, 48) + circle_pts(b[0], b[1], r, 48)), x0, x1)
    if hole_at is not None:
        solid = diff(solid, [cyl_along("x", hole_at[0], hole_at[1], x0 - 0.01, x1 + 0.01, 3.3)])
    return solid


def leg_world_use():
    piv = to_world((0, PIV_UW[0], PIV_UW[1]), TH_USE)[1:]
    tip = tuple(LG["tip_yz"])
    return capsule_x(piv, tip, *LEG_X, hole_at=piv), piv, tip


POCKET = LG["pocket"]


def pocket_profile():
    """(y, z) polyline of the lid top with the leg pocket: top -> 30 deg ramp -> floor -> back wall (C0.5) -> top."""
    zt = LID_TOP
    return [(POCKET["ramp_front_y"] - 30.0, zt), (POCKET["ramp_front_y"], zt), (POCKET["ramp_end_y"], POCKET["bottom_z"]),
            (POCKET["back_wall_y"], POCKET["bottom_z"]), (POCKET["back_wall_y"], zt - 0.5), (POCKET["back_wall_y"] + 0.5, zt),
            (POCKET["back_wall_y"] + 30.0, zt)]


def _seg_dist(p, a, b):
    p, a, b = (np.array(v, float) for v in (p, a, b))
    ab = b - a
    t = float(np.clip((p - a) @ ab / (ab @ ab), 0, 1))
    return float(np.linalg.norm(p - (a + t * ab)))


def _segseg(a, b, c, d, n=60):
    return min(_seg_dist(a + (b - a) * k / n, c, d) for k in range(n + 1))


def leg_hang(theta):
    """leg hanging from its pivot at tilt theta, turned (steeper) until it first touches the pocket (capsule R3)."""
    piv = np.array(to_world((0, PIV_UW[0], PIV_UW[1]), theta)[1:])
    prof = [np.array(p) for p in pocket_profile()]
    L = LG["length"]
    best = None
    for k in range(0, 9001):
        phi = math.radians(10.0 + k * 0.01)
        tip = piv + L * np.array([math.cos(phi), -math.sin(phi)])
        d = min(_segseg(piv, tip, prof[i], prof[i + 1], 30) for i in range(len(prof) - 1))
        if d <= LEG_R + 1e-3:
            best = (math.degrees(phi), tip)
            break
    ang, tip = best
    return capsule_x(tuple(piv), tuple(tip), *LEG_X, hole_at=tuple(piv)), tuple(piv), tuple(tip), ang


def leg_local_stowed():
    pu, pw = PIV_UW
    return capsule_x((pu, pw), (pu + LG["length"], pw), LG["xr"][0], LG["xr"][1], hole_at=(pu, pw))


# ------------------------------------------------------------------ screws / axles
def button_x(yc, zc, x_face, length, toward, d=3.0, head=None):
    hd, hh = head or EST["m3_head"]
    if toward > 0:
        return union([cyl_along("x", yc, zc, x_face - hh, x_face, hd), cyl_along("x", yc, zc, x_face, x_face + length, d, 32)])
    return union([cyl_along("x", yc, zc, x_face, x_face + hh, hd), cyl_along("x", yc, zc, x_face - length, x_face, d, 32)])


def hinge_axles_world():
    out = []
    for side in ("left", "right"):
        h = HG[side]
        near = h["near_cheek"]
        if h["screw_from"] == "-x":
            out.append((side, button_x(AY, AZ, XC + near[0], 20.0, +1)))
        else:
            out.append((side, button_x(AY, AZ, XC + near[1], 20.0, -1)))
    return out


AXL = LG["axle"]
assert AXL["from_side"] == "-x"


def leg_axle_local(dx=0.0):
    """M3x20 ISO 7380 leg axle, head on the near cheek outer face (xr-9.3), put in from -x. dx < 0: pulled out by |dx| (insertion)."""
    pu, pw = PIV_UW
    return button_x(pu, pw, LG["clevis"]["near"][0] + dx, AXL["L"], +1, head=(AXL["head_d"], AXL["head_h"]))


def leg_axle_path_local():
    """the room the axle needs on its way in from -x: head dia over the whole screw length outside the near cheek."""
    pu, pw = PIV_UW
    x1 = LG["clevis"]["near"][0]
    return cyl_along("x", pu, pw, x1 - AXL["L"] - AXL["head_h"], x1, AXL["head_d"])


def m25_local():
    hd, hh = EST["m25_head"]
    out = []
    for xr in BO["xr"]:
        for u in BO["u"]:
            sw = BO["seat_w"]
            out.append(union([cyl_along("z", xr, u, sw, sw + hh, hd, 32), cyl_along("z", xr, u, sw - 6.0, sw, 2.4, 24)]))
    return out


LS = N["lid_screw"]
assert LS["x"] == PL["lid_screw"]["x"] and LS["y"] == PL["lid_screw"]["y"]
assert abs(LS["head_seat_z"] - (LID_TOP - LS["cbore_depth"])) < 1e-6 and abs(LS["tip_z"] - (LS["head_seat_z"] - 10.0)) < 1e-6


def lid_screw_xy():
    return [(x, y) for y in LS["y"] for x in LS["x"]]


def lid_screws_world():
    """M3x10 ISO 7380: head on the counterbore floor (A-7: z67.35), tip z57.35."""
    hd, hh = EST["m3_head"]
    z_seat = LS["head_seat_z"]
    return [union([cyl_z(x, y, z_seat, z_seat + hh, hd), cyl_z(x, y, LS["tip_z"], z_seat, 3.0)]) for (x, y) in lid_screw_xy()]


def rail_inserts_world():
    """M3 heat-set inserts in the seam-rail top (CAD's L2 part; length = insert_engage, est.). Tube with a 2.6 core so the
    screw's thread engagement shows as a small overlap."""
    rt = LS["rail_z"][1]
    return [diff(cyl_z(x, y, rt - LS["insert_engage"], rt, EST["insert_od"]), [cyl_z(x, y, rt - LS["insert_engage"] - 0.01, rt + 0.01, 2.6)])
            for (x, y) in lid_screw_xy()]


# ------------------------------------------------------------------ CU screen lid (B1 version, world)
KP = HG["knuckle_profile"]
HOLE = N["hole"]
CLIP = N["clip"]


def knuckle_profile():
    circ = circle_pts(AY, AZ, KP["R"], 72)
    trap = [(KP["base_y"][0], LID_TOP - 0.01), (KP["base_y"][1], LID_TOP - 0.01), (KP["at_axis_y"][1], AZ), (KP["at_axis_y"][0], AZ)]
    return poly_union(circ, trap)


def ribbon_hole_poly(y0, y1, z0, z1, r=1.0, n=8):
    def arc(cy, cz, a0, a1):
        return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    e = 0.05
    p = [(y0 - r, z0 - e), (y1 + r, z0 - e), (y1 + r, z0)]
    p += arc(y1 + r, z0 + r, 270, 180)[1:]
    p += arc(y1 + r, z1 - r, 180, 90)
    p += [(y1 + r, z1 + e), (y0 - r, z1 + e), (y0 - r, z1)]
    p += arc(y0 - r, z1 - r, 90, 0)[1:]
    p += arc(y0 - r, z0 + r, 0, -90)
    return p


def pocket_cut_poly():
    t30 = math.tan(math.radians(30.0))
    zt = LID_TOP
    yb = POCKET["back_wall_y"]
    zb = POCKET["bottom_z"]
    return [(POCKET["ramp_front_y"] - 0.3 / t30, zt + 0.3), (POCKET["ramp_front_y"], zt), (POCKET["ramp_end_y"], zb), (yb, zb),
            (yb, zt - 0.5), (yb + 0.5, zt), (yb + 0.5, zt + 0.3)]


def lid_world():
    x0, x1 = LID_X
    y0, y1 = LID_Y
    zp0 = LID_TOP - LID_T
    wt, rt = EST["lid_wall_t"], EST["lid_rib_t"]
    add = [box(x0, x1, y0, y1, zp0, LID_TOP),
           diff(box(x0, x1, y0, y1, LID_BED, zp0 + 0.01), [box(x0 + wt, x1 - wt, y0 + wt, y1 - wt, LID_BED - 0.01, zp0 + 0.02)])]
    for rx in EST["lid_ribs_x"]:
        add.append(box(rx - rt / 2, rx + rt / 2, y0 + wt - 0.01, y1 - wt + 0.01, LID_BED, zp0 + 0.01))
    for ry in EST["lid_ribs_y"]:
        add.append(box(x0 + wt - 0.01, x1 - wt + 0.01, ry - rt / 2, ry + rt / 2, LID_BED, zp0 + 0.01))
    for (x, y) in lid_screw_xy():
        add.append(cyl_z(x, y, LID_BED, zp0 + 0.01, LS["boss_d"]))
    # filled blocks down to the print-bed plane (v13 rule)
    for side in ("left", "right"):
        hx = HG[side + "_x"]
        add.append(box(hx[0], hx[1], KP["base_y"][0], KP["base_y"][1], LID_BED, zp0 + 0.01))
    wall = HOLE["wall"]
    add.append(box(HOLE["x"][0] - wall, HOLE["x"][1] + wall, HOLE["y"][0] - wall, HOLE["y"][1] + wall, LID_BED, zp0 + 0.01))
    pb = POCKET["block"]
    add.append(box(pb["x"][0], pb["x"][1], pb["y"][0], pb["y"][1], pb["z"][0], zp0 + 0.01))
    cp = CLIP["pad"]
    add.append(box(cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], cp["z"][0], zp0 + 0.01))
    # on top: knuckle cheeks, heel stop blocks, fold feet (+ rear lips)
    kp = knuckle_profile()
    for side in ("left", "right"):
        h = HG[side]
        for ck in ("far_cheek", "near_cheek"):
            add.append(prism_x(kp, XC + h[ck][0], XC + h[ck][1]))
        ea, eb = HG["ear_slot_x"][side]
        hb = HG["heel_block"]
        add.append(box(ea - 0.01, eb + 0.01, hb["y"][0], hb["y"][1], hb["z"][0] - 0.01, hb["z"][1]))
    for f in N["fold_feet_detail"]:
        add.append(box(f["x"][0], f["x"][1], f["y"][0], f["y"][1], f["z"][0] - 0.01, f["z"][1]))
        if f["rear"]:
            add.append(box(f["x"][0], f["x"][1], f["lip"]["y"][0], f["lip"]["y"][1], LID_TOP - 0.01, f["lip"]["z"][1]))
    lid = union(add)
    cuts = [prism_x([(y0 - 0.01, LID_TOP - 1.0), (y0 - 0.01, LID_TOP + 0.01), (y0 + 1.0, LID_TOP + 0.01)], x0 - 0.01, x1 + 0.01)]
    for s in N["vents"]["slots"]:
        cuts.append(box(s[0], s[1], s[2], s[3], zp0 - 0.01, LID_TOP + 0.01))
    cuts.append(prism_x(ribbon_hole_poly(HOLE["y"][0], HOLE["y"][1], LID_BED, LID_TOP, HOLE["edge_R"]), HOLE["x"][0], HOLE["x"][1]))
    cuts.append(prism_x(pocket_cut_poly(), POCKET["x"][0], POCKET["x"][1]))
    for (px, py) in CLIP["pins"]:
        cuts.append(cyl_z(px, py, LID_BED - 0.01, LID_BED + CLIP["pin_hole_depth"], CLIP["pin_hole_d"]))
    for (x, y) in lid_screw_xy():
        cuts += [cyl_z(x, y, LID_BED - 0.01, LID_TOP + 0.01, LS["hole_d"]), cyl_z(x, y, LS["head_seat_z"], LID_TOP + 0.01, LS["cbore_d"])]
    for side in ("left", "right"):
        h = HG[side]
        cuts.append(cyl_along("x", AY, AZ, XC + h["near_cheek"][0] - 0.01, XC + h["near_cheek"][1] + 0.01, 3.3))
        cuts.append(cyl_along("x", AY, AZ, XC + h["far_cheek"][0] - 0.01, XC + h["far_cheek"][1] + 0.01, 2.5))
    return diff(lid, cuts)


def ribbon_clip_world():
    """E-2 (3a): 30x12x3 under the clip pad (z58.05~61.05, the ribbon is clamped in the 0.3 gap z61.05~61.35), 2 pins
    dia 3.0 x 4.5 on the top face, power-wire groove x652.6~656.1 x 1.8 deep along y in the top face."""
    cp = CLIP["pad"]
    z0, z1 = CLIP["clip_z"]
    assert abs(z1 - z0 - CLIP["t"]) < 1e-6 and abs(CLIP["clamp_z"][1] - cp["z"][0]) < 1e-6 and abs(CLIP["clamp_z"][0] - z1) < 1e-6
    gv = CLIP["wire_groove"]
    plate = diff(box(cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], z0, z1),
                 [box(gv["x"][0], gv["x"][1], cp["y"][0] - 0.01, cp["y"][1] + 0.01, z1 - gv["depth"], z1 + 0.01)])
    pins = [cyl_z(px, py, z1 - 0.01, z1 + CLIP["pin_len"], CLIP["pin_d"]) for (px, py) in CLIP["pins"]]
    return union([plate] + pins)


# ------------------------------------------------------------------ DSI ribbon + power wire
RB = N["ribbon"]
PW = N["power_wire"]
FFC_W, FFC_T = RB["ffc_w"], RB["ffc_t"]
FOLD_SQ = CR["fold_square"]
LANE_XR = ((FOLD_SQ["xr"][0] + FOLD_SQ["xr"][1]) / 2)
W_FLAT = BODY + FFC_T / 2 + 0.0          # ribbon lying on the screen back (w8.0..8.3)


def _loop(theta, start_local_uw, xr_start, x_end, y_end, z_end):
    """hinge loop: from the cradle groove bottom (leaving along -u) to the lid hole top (entering along -z)."""
    p0 = to_world((xr_start, start_local_uw[0], start_local_uw[1]), theta)
    t0 = dir_world((0, -1, 0), theta)
    p3 = np.array([x_end, y_end, z_end])
    t3 = np.array([0, 0, -1.0])
    pts, L = bezier_loop(p0, t0, p3, t3, EST["loop_len"])
    return pts, L


def ribbon_parts(theta):
    """returns dict of world solids and the centreline pieces (for checks)."""
    wm = EST["ribbon_mouth_w"]
    f = SC["fpc"]
    ins = RB["screen_end_insert"]
    uc = f["pin_u_centre"]
    fx0, fx1 = FOLD_SQ["xr"]
    fu0, fu1 = FOLD_SQ["u"]
    # A: from inside the ZIF (insert) +x to the far edge of the fold square, width along u
    a_loc = [(f["mouth_xr"] - ins, uc, wm), (fx1, uc, wm)]
    a_w = [to_world(p, theta) for p in a_loc]
    A = sweep_rect(a_w, dir_world((0, 1, 0), theta), FFC_W, FFC_T)
    # roll (R3) at the 45 deg fold line, clipped to the fold square footprint
    R = RB["fold_roll_R"]
    d = np.array([fx1 - fx0, fu0 - fu1, 0.0])
    Ld = float(np.linalg.norm(d))
    ang = math.degrees(math.atan2(d[1], d[0]))
    tube = Manifold.cylinder(Ld + 2 * R, R, R, 48).rotate((0, 90, 0)).translate((-R, 0, 0))
    tube = tube - Manifold.cylinder(Ld + 2 * R + 1, R - FFC_T, R - FFC_T, 48).rotate((0, 90, 0)).translate((-R - 0.5, 0, 0))
    tube = tube.rotate((0, 0, ang)).translate((fx0, fu1, wm + R - FFC_T / 2))
    tube = tube ^ box(fx0, fx1, fu0, fu1, wm - FFC_T, wm + 2 * R + 0.2)
    ROLL = place(tube, theta)
    # B: down -u along the lane (width along x), on top of A in the fold square, then onto the screen back, out of the groove
    wb = wm + EST["stack"]
    rec_u = WIN["u"][0]
    r0, r1 = EST["ramp_from_recess"]
    b_loc = [(LANE_XR, fu1, wb), (LANE_XR, rec_u + r0, wb), (LANE_XR, rec_u + r1, W_FLAT), (LANE_XR, U0, W_FLAT)]
    b_world = [to_world(p, theta) for p in b_loc]
    hx = (HOLE["x"][0] + HOLE["x"][1]) / 2
    hy = (HOLE["y"][0] + HOLE["y"][1]) / 2
    loop, Lloop = _loop(theta, (U0, W_FLAT), LANE_XR, hx, hy, LID_TOP)
    wp = RB["waypoints"]
    zr = RB["z_run"]
    fold2 = (wp[2][0], wp[2][1])
    # under the lid: down the hole, R3 to +y at z_run, to the far edge (+y) of the fold square
    under = [np.array(wp[0], float), np.array(wp[1], float), np.array([wp[2][0], wp[2][1] + FFC_W / 2, zr])]
    chain = list(b_world[:-1]) + list(loop) + under[1:]
    chain = fillet(chain, RB["bend_R"], 8)
    B = sweep_rect(chain, (1.0, 0.0, 0.0), FFC_W, FFC_T)
    # C: crease-folded under B (z - stack), run -x (width along y), drop in the column x583 (mouth - stiffener 3 - R3),
    # 3a: R3 bend that lands on the unused micro-HDMI edge and runs straight (19.93 deg) into the CAM/DISP 1 mouth, inserted 2.7
    zc = zr - EST["stack"]
    D1 = N["pi5"]["disp1"]
    assert tuple(D1["mouth_dir"]) == (-1, 0), "model handles the x-facing mouth of the final L2 (rot 0)"
    d_in = np.array([1.0, 0.0, 0.0])
    xdrop = wp[3][0]
    mouth_p = np.array(wp[-1], float)
    assert abs(mouth_p[0] - D1["mouth"][0]) < 1e-6 and abs(mouth_p[2] - D1["z"]) < 1e-6
    if len(wp) == 7:                                        # column -> land on the HDMI edge -> straight into the mouth
        q = np.array(wp[-2], float)
        corner = mouth_p + (xdrop - mouth_p[0]) / (q[0] - mouth_p[0]) * (q - mouth_p)
    else:
        corner = np.array([xdrop, fold2[1], mouth_p[2]])
    c_pts = [np.array([fold2[0] + FFC_W / 2, fold2[1], zc]), np.array([xdrop, fold2[1], zc]), corner, mouth_p,
             mouth_p + d_in * RB["pi_end_insert"]]
    c_chain = fillet(c_pts, RB["bend_R"], 8)
    C = sweep_rect(c_chain, (0.0, 1.0, 0.0), FFC_W, FFC_T)
    solid = union([A, ROLL, B, C])
    # centreline length: A to the fold-square centre + roll (pi R) + B and C less the half-width run-outs past the fold centres
    plen = lambda q: float(np.sum(np.linalg.norm(np.diff(np.array(q, float), axis=0), axis=1)))  # noqa: E731
    fc = (fx0 + fx1) / 2
    length = (fc - a_loc[0][0]) + math.pi * R + (plen(chain) - (fu1 - uc) - FFC_W / 2) + (plen(c_chain) - FFC_W / 2)
    paths = [[np.asarray(p, float) for p in a_w], [np.asarray(p, float) for p in chain], [np.asarray(p, float) for p in c_chain]]
    return {"solid": solid, "loop_pts": loop, "loop_len": Lloop, "chain": chain, "length": length, "paths": paths,
            "pi_corner": corner, "pi_end": c_chain[-1], "c_chain": c_chain}


def wire_parts(theta):
    """two leads (5 V red / GND black) MX1.25 -> lane -> hinge loop -> lid hole -> under the lid -> GPIO 2 / 6 (+ housings)."""
    p = SC["pwr"]
    uc = (p["u"][0] + p["u"][1]) / 2
    lane = CR["wire_xr"]
    lx = (lane[0] + lane[1]) / 2
    wm = EST["ribbon_mouth_w"]
    wfl = BODY + EST["wire_d"] / 2 + 0.05
    rec_u = WIN["u"][0]
    wp = PW["waypoints"]
    gp2, gp6 = N["pi5"]["gpio_pin2"], N["pi5"]["gpio_pin6"]
    hd = EST["dupont"]
    z_house_top = N["pi5"]["gpio_top_z"] - EST["gpio_pin_above_base"] + hd[2]
    out, lens, paths = [], [], []
    for k, sgn in ((0, -1), (1, +1)):
        off = sgn * EST["wire_pitch"] / 2
        r0, r1 = EST["ramp_from_recess"]
        loc = [(p["mouth_xr"] - 2.0, uc + off, wm), (lx + off, uc + off, wm), (lx + off, rec_u + r0, wm), (lx + off, rec_u + r1, wfl), (lx + off, U0, wfl)]
        wl = [to_world(q, theta) for q in loc]
        loop, _ = _loop(theta, (U0, wfl), lx + off, wp[0][0] + off, wp[0][1], wp[0][2])
        gx = (gp2, gp6)[k][0]
        under = [np.array([wp[1][0] + off, wp[1][1], wp[1][2]]), np.array([wp[2][0] + off, wp[2][1] + off, wp[2][2]]),
                 np.array([gx, wp[3][1] + off, wp[3][2]]), np.array([gx, wp[3][1], z_house_top])]
        chain = fillet(list(wl[:-1]) + list(loop) + under, 2.0, 6)
        out.append(sweep_tube(chain, EST["wire_d"], 10))
        lens.append(float(np.sum(np.linalg.norm(np.diff(np.array(chain, float), axis=0), axis=1))))
        paths.append([np.asarray(q, float) for q in chain])
    housings = [box(g[0] - hd[0] / 2, g[0] + hd[0] / 2, g[1] - hd[1] / 2, g[1] + hd[1] / 2, z_house_top - hd[2], z_house_top) for g in (gp2, gp6)]
    return {"red": out[0], "black": out[1], "housings": union(housings), "lengths": lens, "paths": paths}


# ------------------------------------------------------------------ L2 context (simplified, 'L2 잠정 외형')
def l2_context():
    C = L2["centre"]
    wl = C["walls"]
    items = []
    ply = "#d9b98b"
    sp = BL2["speakers"]
    poly = [tuple(p) for p in sp["outer_yz_polygon"]]
    for side in ("L", "R"):
        items.append(("L2-POD-" + side, "스피커 통 " + side + " (L2 잠정 외형)", ply, prism_x(poly, *sp[side]["x"])))
        dr = sp["driver"]
        ax = np.array(dr["axis_xyz"], float)
        xc = dr["x_centre"][side]
        cyz = dr["centre_yz"]
        g = Manifold.cylinder(EST["grille_t"], EST["grille_d"] / 2, EST["grille_d"] / 2, 96)
        # cylinder along +z -> along the outward baffle normal ax (rotate about x)
        tilt = math.degrees(math.atan2(-ax[1], ax[2]))      # angle from +z toward -y
        g = g.rotate((tilt, 0, 0)).translate((xc, cyz[0], cyz[1]))
        items.append(("L2-GRILLE-" + side, "스피커 그릴 " + side + " (L2 잠정)", "#2b2b2b", g))
    y0, y1 = C["y"]
    z_b = C["z"][0]
    zl0 = wl["lid_z"][0]
    nt = wl["end_wall_notch"]
    notch_y, notch_z = (214.0, 241.0), (5.0, 27.0)
    assert "y214~241" in nt and "z5~27" in nt
    end = []
    for k in ("end_L", "end_R"):
        a, b = wl[k]
        end.append(diff(box(a, b, y0, y1, z_b, zl0), [box(a - 0.01, b + 0.01, notch_y[0] - 0.01, notch_y[1], notch_z[0] - 0.01, notch_z[1])]))
    ix0, ix1 = C["inner_x"]
    back = box(ix0, ix1, wl["back_y"][0], wl["back_y"][1], z_b, zl0)
    fz = C["floor_zone"]
    bottom = box(ix0, ix1, fz["y"][0], wl["back_y"][0], wl["bottom_z"][0], wl["bottom_z"][1])
    items.append(("L2-CU-BOX", "가운데 유닛 벽·바닥 (L2 잠정 외형)", ply, union(end + [back, bottom])))
    for lid in C["lids"]:
        if lid["id"] == "CU-SCREENLID":
            continue
        items.append(("L2-" + lid["id"], lid["id"] + " 옆 뚜껑 (L2 잠정)", "#c9a877", box(lid["x"][0], lid["x"][1], y0, y1, zl0, LID_TOP)))
    rt = LS["rail_z"][1]
    for c in L2["centre_contents"]:
        if c.get("kind") == "wall" and c["id"].startswith("PR-SEAM"):
            b = c["bbox_x0x1y0y1z0z1"]
            holes = [cyl_z(x, y, rt - LS["insert_hole_depth"], b[5] + 0.01, EST["insert_od"]) for (x, y) in lid_screw_xy()
                     if b[0] < x < b[1] and b[2] < y < b[3] and abs(b[5] - rt) < 1e-6]
            items.append(("L2-" + c["id"], c["id"] + " (L2 잠정)", "#9aa3ad", diff(box(*b), holes) if holes else box(*b)))
    for i, ins in enumerate(rail_inserts_world()):
        items.append(("L2-INSERT-%d" % (i + 1), "M3 인서트 (레일, CAD 부품, 길이 %.0f 추정)" % LS["insert_engage"], "#c8a24a", ins))
    for c in L2["centre_contents"]:
        if c.get("kind") == "item" and not c["id"].startswith("CU-E-PI5"):
            b = c["bbox_x0x1y0y1z0z1"]
            items.append(("L2-" + c["id"], c["id"] + " (L2 잠정)", "#5d6b61", box(*b)))
    ft = BL2["feet"]
    fs = []
    for grp in ft["positions_xy"].values():
        for (fx, fy) in grp:
            fs.append(cyl_z(fx, fy, 0.0, ft["h"], EST["feet_d"], 32))
    items.append(("L2-FEET", "고무발 (L2 잠정)", "#333333", union(fs)))
    return items


def pi_parts():
    P = N["pi5"]
    bt = P["board_top_z"]
    parts = [("PI5-BOARD", "Pi 5 기판", "#2f7d4f", box(P["board_x"][0], P["board_x"][1], P["board_y"][0], P["board_y"][1], bt - EST["pi_board_t"], bt))]
    d1 = P["cad_disp1"]
    parts.append(("PI5-DISP1", "Pi 5 CAM/DISP 1", "#e8e0c8", box(d1["x"][0], d1["x"][1], d1["y"][0], d1["y"][1], bt, d1["z"][1])))
    parts.append(("PI5-DISP0", "Pi 5 CAM/DISP 0", "#e8e0c8", box(P["disp0"]["x"][0], P["disp0"]["x"][1], P["disp0"]["y"][0], P["disp0"]["y"][1], bt, d1["z"][1])))
    parts.append(("PI5-HDMI", "Pi 5 HDMI 2개 (추정 자리)", "#b8b8b8", box(P["hdmi"]["x"][0], P["hdmi"]["x"][1], P["hdmi"]["y"][0], P["hdmi"]["y"][1], bt, P["hdmi"]["top_z"])))
    parts.append(("PI5-HEATSINK", "Pi 5 방열판 (추정 자리)", "#8a8f98", box(P["heatsink"]["x"][0], P["heatsink"]["x"][1], P["heatsink"]["y"][0], P["heatsink"]["y"][1], bt, P["heatsink"]["top_z"])))
    g2, g6 = P["gpio_pin2"], P["gpio_pin6"]
    pitch = (g6[0] - g2[0]) / 2.0                                    # pins 2, 4, 6 along +x
    base_top = P["gpio_top_z"] - EST["gpio_pin_above_base"]
    parts.append(("PI5-GPIO", "Pi 5 GPIO 40핀", "#1d1d1f", box(g2[0] - pitch / 2, g2[0] + 19 * pitch + pitch / 2, g2[1] - 1.5 * pitch, g2[1] + pitch / 2, bt, base_top)))
    for c in L2["centre_contents"]:
        if c["id"] in ("CU-E-PI5-RJ45", "CU-E-PI5-USBA1", "CU-E-PI5-USBA2"):
            parts.append(("PI5-" + c["id"][9:], "Pi 5 " + c["id"][9:], "#b8b8b8", box(*c["bbox_x0x1y0y1z0z1"])))
    return parts


# ------------------------------------------------------------------ assembly
COL = {"cradle": "#5f6b7a", "lid": "#b9c0c8", "leg": "#e07b39", "cover": "#3d8bd4", "screen": "#15181c", "active": "#1f3a5c",
       "conn": "#e8dcc0", "screw": "#c0c6cc", "ribbon": "#e0a030", "red": "#d62828", "black": "#222222", "clip": "#8e6fd1"}

KEY_ONLY = None


class Part3:
    def __init__(self, id, name, kind, color, solid, group="touch", material=""):
        self.id, self.name, self.kind, self.color, self.solid, self.group, self.material = id, name, kind, color, solid, group, material


def touch_parts(theta, leg="auto", explode=None):
    """every touchscreen part in the world at tilt theta. leg: 'use' (25 deg foot in the pocket), 'hang' (resting on the
    pocket at theta), 'stow' (clipped on the cradle back), 'auto' (use at 25, hang at 22..<90 except fold -> stow).
    explode: dict of extra local offsets per part for the exploded view."""
    ex = explode or {}

    def loc(m, key):
        o = ex.get(key)
        return m.translate(o) if o else m
    out = []
    S = screen_local()
    out.append(Part3("TS-SCREEN", "화면 7-DSI-TOUCH-C (더미)", "bought", COL["screen"], place(loc(S["body"], "screen"), theta), material="구매품"))
    out.append(Part3("TS-SCREEN-BEZEL", "화면 유리 테두리", "bought", "#0b0c0e", place(loc(S["bezel"], "screen"), theta)))
    out.append(Part3("TS-SCREEN-ACTIVE", "화면 보이는 영역 154.58×86.42", "bought", COL["active"], place(loc(S["active"], "screen"), theta)))
    out.append(Part3("TS-SCREEN-ZIF", "화면 DSI 22핀 ZIF (추정 위치)", "bought", COL["conn"], place(loc(S["zif"], "screen"), theta)))
    out.append(Part3("TS-SCREEN-MX", "화면 전원 MX1.25 2핀 (추정 위치)", "bought", "#f2f2f2", place(loc(S["mx"], "screen"), theta)))
    out.append(Part3("TS-SCREEN-TAB", "화면 아래 끝 돌기 (도면에서 잰 xr·높이, w는 추정)", "bought", "#9a9a9a", place(loc(S["tab"], "screen"), theta)))
    out.append(Part3("TS-CRADLE", "화면 받침(크래들)", "print", COL["cradle"], place(loc(cradle_local(), "cradle"), theta), material="PETG"))
    out.append(Part3("TS-WINCOVER", "점검창 덮개", "print", COL["cover"], place(loc(cover_local(), "cover"), theta), material="PETG"))
    for i, s in enumerate(m25_local()):
        out.append(Part3("TS-M25-%d" % (i + 1), "M2.5×6 (화면 고정)", "bought", COL["screw"], place(loc(s, "m25"), theta)))
    mode = leg
    if mode == "auto":
        mode = "stow" if theta >= 89.99 else ("use" if abs(theta - TH_USE) < 1e-9 else "hang")
    info = {"leg_mode": mode}
    if mode == "use":
        lg, piv, tip = leg_world_use()
        info.update(leg_pivot=piv, leg_tip=tip)
        if ex.get("leg"):
            lg = lg.translate(ex["leg"])
        out.append(Part3("TS-LEG", "받침다리", "print", COL["leg"], lg, material="PETG"))
    elif mode == "hang":
        lg, piv, tip, ang = leg_hang(theta)
        info.update(leg_pivot=piv, leg_tip=tip, leg_angle=ang)
        out.append(Part3("TS-LEG", "받침다리 (%.0f°에서 매달림)" % theta, "print", COL["leg"], lg, material="PETG"))
    else:
        out.append(Part3("TS-LEG", "받침다리 (접어 끼움)", "print", COL["leg"], place(loc(leg_local_stowed(), "leg_stow"), theta), material="PETG"))
    out.append(Part3("TS-M3X20-LEG", "M3×20 (다리 축)", "bought", COL["screw"], place(loc(leg_axle_local(), "leg_axle"), theta)))
    rb = ribbon_parts(theta)
    info.update(loop_len=rb["loop_len"], loop_min_y=float(np.min(rb["loop_pts"][:, 1])), ffc_len=rb["length"])
    wr = wire_parts(theta)
    info.update(wire_len=wr["lengths"])
    if not ex:
        out.append(Part3("TS-FFC", "DSI 리본 22핀 0.5 mm 300 B형", "bought", COL["ribbon"], rb["solid"]))
        out.append(Part3("TS-PWR-RED", "전원선 5V (빨강)", "bought", COL["red"], wr["red"]))
        out.append(Part3("TS-PWR-BLK", "전원선 GND (검정)", "bought", COL["black"], wr["black"]))
        out.append(Part3("TS-PWR-HOUSING", "점퍼 F 하우징 (GPIO 2·6)", "bought", "#303030", wr["housings"]))
    lidm = lid_world()
    if ex.get("lid"):
        lidm = lidm.translate(ex["lid"])
    out.append(Part3("TS-LID", "가운데 화면 뚜껑 (B1판, L2 뚜껑에 더함)", "print", COL["lid"], lidm, material="PETG"))
    for side, s in hinge_axles_world():
        o = ex.get("axle_" + side)
        out.append(Part3("TS-M3X20-HINGE-" + side[0].upper(), "M3×20 (경첩 축 %s)" % ("왼쪽" if side == "left" else "오른쪽"), "bought", COL["screw"], s.translate(o) if o else s))
    for i, s in enumerate(lid_screws_world()):
        o = ex.get("lidscrew")
        out.append(Part3("TS-M3X10-LID%d" % (i + 1), "M3×10 (뚜껑 고정)", "bought", COL["screw"], s.translate(o) if o else s))
    rc = ribbon_clip_world()
    if ex.get("clip"):
        rc = rc.translate(ex["clip"])
    out.append(Part3("TS-RCLIP", "리본 클립 30×12×3", "print", COL["clip"], rc, material="PETG"))
    return out, info


def context_parts():
    out = []
    for (i, n, c, s) in l2_context():
        out.append(Part3(i, n, "context", c, s, group="l2"))
    for (i, n, c, s) in pi_parts():
        out.append(Part3(i, n, "context", c, s, group="pi"))
    return out


MODULE_GROUPS = ["프레임", "백건", "흑건"]
MODULE_UNITS = ["끝_부속_왼쪽"] + ["O%d" % i for i in range(1, 8)] + ["끝_부속_오른쪽"]
MODULE_COLORS = {"프레임": "#9aa3ad", "백건": "#f4f1ea", "흑건": "#1d1d1f"}


def module_stls(units=None):
    """(path, colour) of the unchanged key-module assembly STLs (modules are the same in L1 and L2)."""
    out = []
    for u in (units or MODULE_UNITS):
        for g in MODULE_GROUPS:
            f = os.path.join(CAD, "stl", "assembly", "%s_%s.stl" % (u, g))
            if os.path.exists(f):
                out.append((f, MODULE_COLORS[g], "%s_%s" % (u, g)))
    return out


def unit_x(u):
    """module x-range from the manifest (for picking the units near the screen)."""
    man = json.load(open(os.path.join(CAD, "manifest.json")))
    g = u.replace("_", " ") + " 프레임"
    bb = [p["bbox"] for p in man["parts"] if p["group"] == g]
    return (min(b[0] for b in bb), max(b[3] for b in bb))
