"""Toccata v4 W1+ r4.5 key action -> solids.

Source of every shape: ../../key-action-v4/model/geometry.json (the model the 15 drawings are drawn from).
  parts[]  : (y, z) side polygons extruded over an x range; female = cut
  plan[]   : (x, y) polygons / circles
  end_parts: the left (A0 A#0 B0) and right (C8) end parts in their own x (left: world x, right: world x - 1198.5)
Features the prisms do not carry (holes, pockets, nut traps, dovetail flanks, engraving) are added here from
the DESIGN.md tables; their numbers are in FEAT and each carries the table id it comes from.
"""
import json
import math
import os
import re

from manifold3d import Manifold

from cadlib import (clean, box, cyl_x, cyl_y, cyl_z, diff, empty, hexagon_z, prism_x, prism_y, prism_z,
                    teardrop_x, text_xy, union, orient, rot_x, rot_y, rot_z, matmul)

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.normpath(os.path.join(HERE, "..", "..", "key-action-v4", "model", "geometry.json"))
G = json.load(open(GEO))
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec", "keyaction_features.json"))

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
BLACK = {"C#", "D#", "F#", "G#", "A#"}
L_AXIS = (203.25, 33.5)          # S11 lever rod centre (y, z)
K_AXIS = (141.0, 21.5)           # S03 key rod centre (y, z)

# ------------------------------------------------------------------ feature numbers (table ids in comments)
FEAT = {
    # key magnet D5x2 N35 press + CA, flush with the key underside z23.5 (P29, S26, drawing 5)
    "magnet_d": 5.2, "magnet_depth": 2.1,           # spec ka1: D5.2 x 2.1 (v3 S12), press + CA
    # balance-pin groove under the block: printed 3.2 wide, 2.5 deep, y134.0-138.0, open to the front (P32)
    "pin_groove_w": 3.2, "pin_groove_depth": 2.5, "pin_groove_y": (134.0, 138.0),
    # capstan M3 x 6 ISO 7380 + M3 nut trap in the hidden beam (D02, S07, S08, model_v4 'nut trap void')
    "cap_hole_d": 2.8, "cap_hole_z": (26.4, 27.6),   # self-locking bore above the nut (D02, spec ka1)
    "cap_tip_d": 3.3, "cap_tip_z": (21.0, 23.8),     # screw-tip clearance below the nut (spec ka1)
    "nut_af": 5.6, "nut_z": (23.8, 26.4),  # trap = M3 nut 5.5 AF x 2.4 + 0.1 / 0.2 (model_v4, stage-0 C08a)
    # lever hub bore: printed D3.9 -> drill D4.0 (S11); fin boss bores the same (P22, D18)
    "hub_bore_print": 3.9, "fin_bore_print": 3.9,
    # control-board bosses (P35): screw bosses D2.5 blind to z15.4; locating pins D2.8 tip z7.8
    "cb_screw_bore": 2.5, "cb_screw_top": 15.4, "cb_pin_d": 2.8,
    # sensor bar + board fixed with M3x10 self-tapping into the left post (P111 / P36)
    "sb_screws": [(3.0, 61.9), (3.0, 74.6)], "sb_pilot_d": 2.75, "sb_clear_d": 3.4,   # spec ka2
    # balance pins ISO 2338 D2 x 12, top z23.30 (P32) -> blind press hole in the rail
    "bal_pin_hole_d": 1.95,                           # spec ka2: light press for the D2 dowel
    # note name engraved on the carrier side wall (parts_list "옆벽에 음 이름 새김")
    "engrave_depth": 0.4, "engrave_size": 4.0,
    "groove_ext": 2.0,
}
ADJUST = set()


def _load_spec():
    if os.path.exists(SPEC):
        try:
            return json.load(open(SPEC))
        except Exception:
            return None
    return None


SPECJ = _load_spec()
SPECF = None
try:
    SPECF = json.load(open(os.path.join(os.path.dirname(SPEC), "keyaction_features_frame.json")))
except Exception:
    SPECF = None


def note_of(body):
    return body.split(" ", 1)[1]


def is_black(note):
    return note.rstrip("0123456789") in BLACK or note.endswith("#0")


# ------------------------------------------------------------------ prisms
def poly(p, pose):
    if "side" in p:
        return p["side"]
    return p["side_" + pose]


def prisms(parts, pose, skip=()):
    out = []
    for p in parts:
        if any(re.search(s, p["part"]) for s in skip):
            continue
        out.append(prism_x(poly(p, pose), p["x"][0], p["x"][1]))
    return out


def bodies_of(parts):
    b = {}
    for p in parts:
        b.setdefault(p["body"], []).append(p)
    return b


def plan_circle(plan, name):
    for p in plan:
        if p["part"] == name and p.get("circle"):
            return p["circle"]
    return None


# ------------------------------------------------------------------ keys
KEY_BOUGHT = (r"^capstan head$", r"^rest felt$")

# A11 (2026-10-26, user: 실제 백건반은 끝이 둥글다): geometry.json keys are square boxes; the printed keys are cut to
# an envelope with rounded front corners (plan) and rounded top edges. Only material comes off, so no clearance
# shrinks. The top-edge round starts on the top face with a 45 deg flat: printed top face down it never overhangs
# past 45 deg.
KEY_ROUND = {
    "white_corner": 2.0,   # plan radius, the two front corners of the white head skin (y0)
    "white_front": 1.0,    # plan radius, the front-face corners under the lip (front wall y1.5), up to 0.3 under the skin
    "black_corner": 1.5,   # plan radius, the black key's front corners above the white tops (slanted front)
    "black_low": 1.0,      # plan radius, the black key's lower front corners (z < 43.5, between the white tails)
    "top_edge": 0.8,       # the exposed top edges: front and sides (head and tail)
}
_FAR = 260.0               # y past every key's back end
_EPS = 0.001               # white-key envelope offset off the flat key faces (coplanar faces left zero-area seams)


def _rim(rt, n=6):
    """top-edge profile [(u, w)] from the top face to the side: u = in from the side, w = down from the top."""
    c = rt * (1.0 - math.sqrt(0.5))
    pts = [(2.0 * c, 0.0)]
    for i in range(n + 1):
        f = math.radians(45.0 * (1.0 - i / float(n)))
        pts.append((rt - rt * math.cos(f), rt - rt * math.sin(f)))
    return pts                                                         # ends at (0, rt) on the side


def _ring(cx, cy, a0, a1, rc, prof, n=16):
    """points of a plan corner (centre cx, cy, radius rc, angles a0..a1 deg) swept with prof [(u, z)]."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / float(n))
        for (u, z) in prof:
            out.append((cx + (rc - u) * math.cos(a), cy + (rc - u) * math.sin(a), z))
    return out


def _rimmed(a0, a1, zt, zb, rim):
    """(a, z) section a0..a1 x zb..zt, both top corners rounded by rim (counter-clockwise)."""
    return ([(a0, zb), (a1, zb)] + [(a1 - u, zt - w) for (u, w) in reversed(rim)]
            + [(a0 + u, zt - w) for (u, w) in rim])


def _front_rounded(x0, x1, y0, y1, r, n=16):
    """(x, y) rectangle with only its two front (y0) corners rounded by r (counter-clockwise)."""
    arc = lambda cx, a0: [(cx + r * math.cos(math.radians(a0 + 90.0 * i / n)), y0 + r + r * math.sin(math.radians(a0 + 90.0 * i / n)))
                          for i in range(n + 1)]
    return arc(x1 - r, 270.0) + [(x1, y1), (x0, y1)] + arc(x0 + r, 180.0)


def _corner_cut(x, y, r, side, n=16):
    """(x, y) region outside an R r round at a key's front corner (side face x, front face y, material at +y and,
    side = 1, at +x / side = -1, at -x), reaching 1 mm past both faces (counter-clockwise)."""
    q = ([(-1.0, -1.0), (r, -1.0), (r, 0.0)]
         + [(r + r * math.cos(math.radians(270.0 - 90.0 * i / n)), r + r * math.sin(math.radians(270.0 - 90.0 * i / n)))
            for i in range(1, n)]
         + [(0.0, r), (-1.0, r)])
    q = [(x + side * u, y + v) for (u, v) in q]
    return q if side > 0 else q[::-1]


def key_rounding(parts):
    """(envelope, cuts): a printed key = (its prisms - cuts) ^ envelope (A11), from the key's own skin / wall prisms.
    Built in the key's own x (0 = its leftmost wall, values rounded) so keys of one shape get the same hull and still
    share one print file. Every envelope face that is not a round lies outside the key or on a key face it ends with:
    an envelope edge drawn across a flat key face left zero-area triangles that opened seams in the STL."""
    by = {p["part"]: p for p in parts}
    rim = _rim(KEY_ROUND["top_edge"])
    if "skin head" in by:                                              # white key: head + tail
        xr = by["skin head"]["x"][0]
        lx = lambda x: round(x - xr, 6)
        hx0, hx1 = map(lx, by["skin head"]["x"])
        tx0, tx1 = map(lx, by["skin tail"]["x"])
        hs = poly(by["skin head"], "rest")
        yf, yr = min(q[0] for q in hs), max(q[0] for q in hs)          # 0 / 50
        zs, zt = min(q[1] for q in hs), max(q[1] for q in hs)          # 41.5 / 43.5
        yw = min(q[0] for q in poly(by["front wall"], "rest"))        # 1.5, front face under the lip
        rc, e = KEY_ROUND["white_corner"], _EPS
        # the envelope stands _EPS off the key's flat faces (sides, top, lip front): no face of it lies in a key face
        prof = [(u - e, zt + e - w) for (u, w) in rim] + [(-e, -5.0)]  # full height: the walls stand 1.5 behind the lip
        # the head's rear step edge (under the black key's front) stays square: rounding it too left near-coincident
        # vertices where it met the side round and the tail's side
        pts = (_ring(hx0 + rc, yf + rc, 180.0, 270.0, rc + e, prof) + _ring(hx1 - rc, yf + rc, 270.0, 360.0, rc + e, prof)
               + [(hx0 + u, yr + e, z) for (u, z) in prof] + [(hx1 - u, yr + e, z) for (u, z) in prof])
        head = Manifold.hull_points(pts)
        ye = max(q[0] for q in poly(by["skin tail"], "rest"))         # 147, the skin's back end
        tail = prism_y(_rimmed(tx0 - e, tx1 + e, zt + e, -5.0, rim), yr - 5.0, ye + 1.0)
        env = union([head, tail, box(tx0 - 20.0, tx1 + 20.0, ye + 0.5, _FAR, -5.0, zt + 1.0)])
        # front-face corners under the lip: cut up to 0.3 under the skin so the cut never meets the lip's underside
        # plane z41.5 (that 0.3 sits 1.5 behind the lip's front, out of sight)
        rw, zc = KEY_ROUND["white_front"], zs - 0.3
        cuts = [prism_z(_corner_cut(hx0, yw, rw, 1), 20.0, zc), prism_z(_corner_cut(hx1, yw, rw, -1), 20.0, zc)]
        return env.translate((xr, 0.0, 0.0)), [c.translate((xr, 0.0, 0.0)) for c in cuts]
    sk = by["skin"]                                                    # black key
    xr = by["wall L low"]["x"][0]
    lx = lambda x: round(x - xr, 6)
    bx0, bx1 = map(lx, sk["x"])
    zt = max(q[1] for q in poly(sk, "rest"))                           # 55.5
    lx0, lx1 = 0.0, lx(by["wall R low"]["x"][1])
    zl = max(q[1] for q in poly(by["wall L low"], "rest"))            # 43.5, the white tops
    fw = poly(by["front wall"], "rest")
    ya = min(q[0] for q in fw if abs(q[1] - zl) < 1e-6)               # slanted front face y54.2 at z43.5 ...
    yb = min(q[0] for q in fw if abs(q[1] - zt) < 1e-6)               # ... y55.2 at z55.5
    slant = lambda z: ya + (yb - ya) * (z - zl) / (zt - zl)
    rc, rt = KEY_ROUND["black_corner"], KEY_ROUND["top_edge"]
    z0 = zl - 0.5
    top = [(u, zt - w) for (u, w) in rim]
    cyt, cyb = slant(zt - rt) + rc, slant(z0) + rc
    pts = (_ring(bx0 + rc, cyt, 180.0, 270.0, rc, top) + _ring(bx1 - rc, cyt, 270.0, 360.0, rc, top)
           + _ring(bx0 + rc, cyb, 180.0, 270.0, rc, [(0.0, z0)]) + _ring(bx1 - rc, cyb, 270.0, 360.0, rc, [(0.0, z0)])
           + [(bx0 + u, _FAR, z) for (u, z) in top + [(0.0, z0)]] + [(bx1 - u, _FAR, z) for (u, z) in top + [(0.0, z0)]])
    upper = Manifold.hull_points(pts)
    rl = KEY_ROUND["black_low"]
    lower = prism_z(_front_rounded(lx0, lx1, ya, ya + rl + 1.0, rl), -5.0, zl)
    ys = max(q[0] for q in poly(sk, "rest") if q[1] > zt - 1e-6)     # 144.3: the skin steps down under the curtain
    keep = [box(lx0 - 20.0, lx1 + 20.0, ya + rl + 1.0, _FAR, -5.0, zl),   # the hidden tail (some sit off the walls in x)
            box(lx0 - 20.0, lx1 + 20.0, ys, _FAR, -5.0, zt + 1.0)]      # rear wall / step under the curtain
    return union([upper, lower] + keep).translate((xr, 0.0, 0.0)), []


def key_points(parts, fixed, note):
    """magnet / balance pin / capstan centres (x, y) from the prisms: magnet boss centre at y67 (P29),
    the fixed 'balance pin D2 <note>' prism, and the capstan head prism (x centre, y of its top point)."""
    mb = [p for p in parts if p["part"] == "magnet boss"]
    mag = None
    if mb:
        mag = ((mb[0]["x"][0] + mb[0]["x"][1]) / 2.0, 67.0)
    pin = None
    for p in fixed:
        if p["part"] == "balance pin D2 %s" % note:
            ys = [q[0] for q in p["side"]]
            pin = ((p["x"][0] + p["x"][1]) / 2.0, (min(ys) + max(ys)) / 2.0)
    cap = None
    hd = [p for p in parts if p["part"] == "capstan head"]
    if hd:
        top = max(hd[0]["side_rest"], key=lambda q: q[1])
        cap = ((hd[0]["x"][0] + hd[0]["x"][1]) / 2.0, top[0])
    return mag, pin, cap


def key_solid(parts, fixed, note):
    """printed key (PETG) in module/end-part coordinates, design pose (side_rest)."""
    env, rcuts = key_rounding(parts)                                   # A11 rounded corners
    m = diff(union(prisms(parts, "rest", KEY_BOUGHT)), rcuts) ^ env
    cuts = []
    mag, pin, cap = key_points(parts, fixed, note)
    z_under = 23.5                                                     # S02 key underside
    if mag:
        cuts.append(cyl_z(mag[0], mag[1], z_under - 1.0, z_under + FEAT["magnet_depth"], FEAT["magnet_d"]))
    if pin:
        w = FEAT["pin_groove_w"]
        y0, y1 = FEAT["pin_groove_y"]
        zb = 22.3                                                      # block underside (drawing 5)
        cuts.append(box(pin[0] - w / 2, pin[0] + w / 2, y0 - 1.0, y1, zb - 1.0, zb + FEAT["pin_groove_depth"]))
    if cap:
        cx, cy = cap[0], cap[1]
        beam = [p for p in parts if p["part"] == "beam"][0]
        bx0, bx1 = beam["x"]
        z0n, z1n = FEAT["nut_z"]
        af = FEAT["nut_af"]
        # D2.8 self-locking bore above the nut, D3.3 tip clearance below it (D02, spec ka1)
        cuts.append(cyl_z(cx, cy, FEAT["cap_hole_z"][0] - 0.01, FEAT["cap_hole_z"][1], FEAT["cap_hole_d"]))
        cuts.append(cyl_z(cx, cy, FEAT["cap_tip_z"][0], FEAT["cap_tip_z"][1] + 0.01, FEAT["cap_tip_d"]))
        # nut trap: hex pocket (AF 5.6, flats facing +-y) centred on the screw + side slot out of the +x beam face
        cuts.append(hexagon_z(cx, cy, z0n, z1n, af, rot=30))
        cuts.append(box(cx, bx1 + 1.0, cy - af / 2, cy + af / 2, z0n, z1n))
    return clean(diff(m, cuts))


def key_bought(parts, fixed, note):
    """capstan screw (ISO 7380 head prism + M3 shank), M3 nut, magnet, felts - for the assembly."""
    out = {}
    head = [p for p in parts if p["part"] == "capstan head"]
    mag, pin, cap = key_points(parts, fixed, note)
    if head and cap:
        h = head[0]
        out["capstan"] = union([prism_x(h["side_rest"], *h["x"]), cyl_z(cap[0], cap[1], 23.3, 29.36, 3.0)])
        out["nut"] = hexagon_z(cap[0], cap[1], FEAT["nut_z"][0] + 0.1, FEAT["nut_z"][0] + 2.5, 5.5, rot=30)
    if mag:
        out["magnet"] = cyl_z(mag[0], mag[1], 23.5, 25.5, 5.0)
    felt = [p for p in parts if p["part"] == "rest felt"]
    if felt:
        out["rest felt"] = union([prism_x(felt[0]["side_rest"], *felt[0]["x"])])
    return out


# ------------------------------------------------------------------ levers
LEVER_BOUGHT = (r"^felt strip$", r"^steel block")


_MOD_CORE = [p for p in G["parts"] if p["body"] == "lever C" and p["part"].startswith("carrier core")][0]
_MOD_STEEL = [p for p in G["parts"] if p["body"] == "lever C" and p["part"].startswith("steel block")][0]


def _rot_yz(poly, deg):
    a = math.radians(deg)
    c, s_ = math.cos(a), math.sin(a)
    out = []
    for (y, z) in poly:
        dy, dz = y - L_AXIS[0], z - L_AXIS[1]
        out.append((L_AXIS[0] + dy * c - dz * s_, L_AXIS[1] + dy * s_ + dz * c))
    return out


def lever_normalize(parts):
    """end-part levers carry only posed polygons and no steel prism: rebuild side_rigid0 by rotating
    side_rest back about L (the carrier section is common to every lever, P11) and add the steel block."""
    if any("side_rigid0" in p for p in parts) and any(p["part"].startswith("steel block") for p in parts):
        return parts
    core = [p for p in parts if p["part"].startswith("carrier core")][0]
    ang = lambda q: math.atan2(q[1] - L_AXIS[1], q[0] - L_AXIS[0])
    rest_deg = math.degrees(ang(core["side_rest"][0]) - ang(_MOD_CORE["side_rigid0"][0]))
    out = []
    for p in parts:
        q = dict(p)
        q["side_rigid0"] = _rot_yz(p["side_rest"], -rest_deg)
        out.append(q)
    x0, x1 = core["x"]
    st = {"body": core["body"], "part": "steel block SS400 9x19x40 (inside the carrier, rebuilt)", "moving": True,
          "x": [x0 + 0.1, x1 - 0.1], "side_rigid0": _MOD_STEEL["side_rigid0"],
          "side_rest": _rot_yz(_MOD_STEEL["side_rigid0"], rest_deg)}
    out.append(st)
    return out


def lever_rest_angle(parts):
    st = [p for p in parts if p["part"].startswith("steel block")][0]
    a, r = st["side_rigid0"][0], st["side_rest"][0]
    ang = lambda q: math.atan2(q[1] - L_AXIS[1], q[0] - L_AXIS[0])
    return math.degrees(ang(r) - ang(a))


def rotate_about_L(m, deg):
    return m.translate((0, -L_AXIS[0], -L_AXIS[1])).rotate((deg, 0, 0)).translate((0, L_AXIS[0], L_AXIS[1]))


def lever_solid(parts, note, engrave=None, collars=None):
    """printed lever carrier at lever angle 0 (side_rigid0), module coordinates.
    collars = (left, right) hub-collar lengths; None keeps the geometry.json collars (P14). The CAD uses the
    A5 layout (every pair on the lower-x lever's +x side) so each carrier lies flat on its -x face."""
    skip = LEVER_BOUGHT + ((r"^hub collar$",) if collars is not None else ())
    m = union(prisms(parts, "rigid0", skip))
    st = [p for p in parts if p["part"].startswith("steel block")][0]
    core = [p for p in parts if p["part"].startswith("carrier core")][0]
    xs0, xs1 = core["x"]                              # pocket 9.2 = steel 9.0 + 2 x 0.10 bond (P11)
    ys = [q[0] for q in st["side_rigid0"]]
    zs = [q[1] for q in st["side_rigid0"]]
    # end-part levers (steel rebuilt by lever_normalize): the rear snap lips end exactly on the pocket's top-rear
    # edge (y189.65), which left a 4-face pinch edge in the STL -> run the pocket 0.02 past it (bond gap only)
    y_back = max(ys) + (0.02 if "rebuilt" in st["part"] else 0.0)
    pocket = box(xs0, xs1, min(ys), y_back, min(zs) - 0.5, max(zs) + 0.005)   # open at the bottom (steel snaps in from below)
    hubs = [p for p in parts if p["part"] == "hub"]
    hx0 = min(p["x"][0] for p in hubs)
    hx1 = max(p["x"][1] for p in hubs)
    if collars is not None:
        cl, cr = collars
        adds = []
        if cl > 1e-6:
            adds.append(cyl_x(L_AXIS[0], L_AXIS[1], hx0 - cl, hx0 + 0.01, 6.0))
        if cr > 1e-6:
            adds.append(cyl_x(L_AXIS[0], L_AXIS[1], hx1 - 0.01, hx1 + cr, 6.0))
        m = union([m] + adds)
        bx0, bx1 = hx0 - cl, hx1 + cr
    else:
        cps = [p for p in parts if p["part"].startswith("hub")]
        bx0 = min(p["x"][0] for p in cps)
        bx1 = max(p["x"][1] for p in cps)
    bore = cyl_x(L_AXIS[0], L_AXIS[1], bx0 - 1, bx1 + 1, FEAT["hub_bore_print"])
    cuts = [pocket, bore]
    if engrave:
        # note name on the outer +x face of the web (3.8 thick there; the 0.7 pocket wall carries the bond line):
        # centre (y194.8, z36.8), size 3.2, 0.4 deep, reads upright from +x (spec ka1)
        size = 4.6
        t = text_xy(engrave, size, FEAT["engrave_depth"] + 0.2, 0, 0, 0, "center", "center", heavy=True)
        b = t.bounding_box()
        k = min(1.0, 8.0 / (b[3] - b[0]), 5.2 / (b[4] - b[1]))
        if k < 1.0:
            t = text_xy(engrave, size * k, FEAT["engrave_depth"] + 0.2, 0, 0, 0, "center", "center", heavy=True)
        t = orient(t, [[0, 0, -1], [1, 0, 0], [0, 1, 0]], (hx1 + 0.2, 194.7, 36.7))
        cuts.append(t)
    return clean(diff(m, cuts))


def _lever_cover_items(parts):
    """A12: the far (+x) carrier side wall in front of the web (y < 190.3) with the +x snap lips (top y153..163 behind the
    front cap, top y184..190, bottom y165..176.5). Lying on the -x wall the carrier printed this wall as a 40 mm roof
    over the steel pocket, the lips hanging under it (the old breakaway rib held its middle)."""
    wall = [p for p in parts if p["part"].startswith("carrier side wall R")][0]
    core = [p for p in parts if p["part"].startswith("carrier core")][0]
    xm = (core["x"][0] + core["x"][1]) / 2.0
    items = [prism_x(wall["side_rigid0"], *wall["x"]) ^ box(wall["x"][0] - 1, wall["x"][1] + 1, 140.0, COVER_Y1, 0.0, 80.0)]
    for p in parts:
        if (p["part"].startswith("carrier top snap lip R") or p["part"] == "bottom lip") and p["x"][0] > xm:
            m = prism_x(p["side_rigid0"], *p["x"])
            if "y150-163" in p["part"]:
                m = m ^ box(p["x"][0] - 1, p["x"][1] + 1, COVER_CAP_Y, 200.0, 0.0, 80.0)   # the front cap y150..153 stays on the body
            items.append(m)
    return items


COVER_Y1 = 190.3       # cover ends at the +x web (y190.3..203.25), which stays on the body with the hub
COVER_CAP_Y = 153.0    # front cap (full width, y150..153) stays on the body


def lever_cover_solid(parts):
    """A12 lever cover = carrier +x wall + its lips, lever angle 0 (side_rigid0), module coordinates."""
    return clean(union(_lever_cover_items(parts)))


_COVER_CANON = []


def lever_cover_print():
    """the one print shape of every lever cover: the module lever C cover (the carrier section is common to every lever,
    P11; the end-part levers come back from their rest pose 0.005..0.009 off it, lever_normalize)."""
    if not _COVER_CANON:
        _COVER_CANON.append(lever_cover_solid([p for p in G["parts"] if p["body"] == "lever C"]))
    return _COVER_CANON[0]


def lever_body_solid(parts, note, engrave=None, collars=None):
    """A12 lever carrier body = lever_solid minus the cover: the steel pocket is open on +x, so the body prints on its
    -x wall with nothing over the pocket (no breakaway rib)."""
    m = lever_solid(parts, note, engrave=engrave, collars=collars)
    ADJUST.add("A12")
    return clean(diff(m, [union(_lever_cover_items(parts))]))


def lever_print_support(parts):
    """DESIGN 15 '강철 칸 안에 지지대 1개(z 틈 0.2)': breakaway rib across the pocket at mid-span (y169.4..170.6), from the
    near (-x, bed) side wall up to 0.2 under the far wall, z33.5..51.5; 0.4-wide root for the first 0.6 so it snaps off.
    Print file only (the assembly has no rib). Remove and sand flush before bonding the steel."""
    core = [p for p in parts if p["part"].startswith("carrier core")][0]
    x0, x1 = core["x"]
    rib = union([box(x0 + 0.6 - 0.01, x1 - 0.2, 169.4, 170.6, 33.5, 51.5),
                 box(x0 - 0.01, x0 + 0.6, 169.8, 170.2, 33.5, 51.5)])
    return rib


def lever_bought(parts, pose="rest"):
    out = {}
    st = [p for p in parts if p["part"].startswith("steel block")][0]
    out["steel"] = prism_x(st["side_" + pose], *st["x"])
    fe = [p for p in parts if p["part"] == "felt strip"]
    if fe:
        out["felt strip"] = prism_x(fe[0]["side_" + pose], *fe[0]["x"])
    return out


# ------------------------------------------------------------------ springs (MISUMI C-UA90R5-3-0.5, bought)
def spring_solid(parts, dx=0.0):
    """coil (hollow, ID 5.0 around the D4 rod) + both legs, at rest; dx shifts it along x (end parts)."""
    out = []
    coil = None
    for p in parts:
        m = prism_x(p["side_rest"] if "side_rest" in p else p["side"], p["x"][0] + dx, p["x"][1] + dx)
        if "coil" in p["part"]:
            poly = p["side_rest"] if "side_rest" in p else p["side"]
            cy = sum(q[0] for q in poly) / len(poly)
            cz = sum(q[1] for q in poly) / len(poly)
            m = diff(m, [cyl_x(cy, cz, p["x"][0] + dx - 1, p["x"][1] + dx + 1, 5.0)])
        out.append(m)
    return union(out)


# ------------------------------------------------------------------ fixed parts -> printed groups
FRAME_RX = [r"^floor", r"^white front rail$", r"^tab ", r"^keeper hook", r"^black stop rail", r"^black tab base",
            r"^balance rail", r"^rod end stop post", r"^rear shelf", r"^shelf rib", r"^fin", r"^top plate",
            r"^pad bar rail", r"^rear wall", r"^spring groove boss", r"dovetail", r"^control-board boss",
            r"^control-board locating pin", r"^sensor board support", r"^sensor-bar ledge", r"^cheek", r"^end cheek",
            r"^bracket", r"^jack", r"cheek"]
SENSORBAR_RX = [r"^sensor bar"]
PADBAR_RX = [r"^pad bar(?! rail)", r"^pad wedge"]
CURTAIN_RX = [r"^cover curtain"]
PLUG_RX = [r"^lever rod end plug"]
BOUGHT_RX = [r"felt", r"^key rod", r"^lever rod D4", r"^balance pin", r"^control board", r"^board ", r"^board part",
             r"^control-board screw", r"^sensor board (SB|EL|ER)", r"^J4[01]1 lead", r"^lead ", r"^underside wire", r"^USB-C plug", r"^up-stop pad", r"^fin boss bore",
]


def classify(name):
    for grp, rxs in (("plug", PLUG_RX), ("sensorbar", SENSORBAR_RX), ("curtain", CURTAIN_RX),
                     ("padbar", PADBAR_RX)):
        if any(re.search(r, name) for r in rxs):
            return grp
    if re.search(r"^(fin boss bore|spring groove cut|spring groove entry)", name):
        return "female"
    if any(re.search(r, name) for r in BOUGHT_RX):
        return "bought"
    if any(re.search(r, name) for r in FRAME_RX):
        return "frame"
    return "unknown"


def fixed_groups(parts):
    g = {}
    for p in parts:
        if p["body"] != "fixed":
            continue
        if p.get("female"):
            g.setdefault("female", []).append(p)
            continue
        g.setdefault(classify(p["part"]), []).append(p)
    return g


DOVE_M = {"front": ([(0.0, 8.0), (4.0, 6.5), (4.0, 15.5), (0.0, 14.0)], (3.0, 8.5)),
          "rear": ([(0.0, 199.5), (4.0, 198.0), (4.0, 207.0), (0.0, 205.5)], (3.0, 17.0))}
DOVE_F = {"front": ([(0.0, 7.893), (4.1, 6.356), (4.1, 15.644), (0.0, 14.107)], (3.0, 8.8)),
          "rear": ([(0.0, 199.393), (4.1, 197.856), (4.1, 207.144), (0.0, 205.607)], (3.0, 17.3))}
# A6: v4 has no material around the rear female groove (only the 2 mm floor) -> printed block under the shelf
REAR_FEMALE_BLOCK = (0.0, 6.1, 195.9, 209.0, 3.0, 18.05)


def dovetail_male_at(x_face):
    out = []
    for k, (poly, (z0, z1)) in DOVE_M.items():
        out.append(prism_z([((x_face - 0.01) if x == 0 else (x_face + x), y) for (x, y) in poly], z0, z1))
    return out


def dovetail_female_at(x_face):
    out = []
    for k, (poly, (z0, z1)) in DOVE_F.items():
        out.append(prism_z([(x_face - 0.01 + x, y) for (x, y) in poly], z0 - 0.5, z1))
    return out


def frame_solid(fx, plan, extra_cuts=(), extra_adds=()):
    """printed frame (프레임) from its prisms, with the D6 bosses / D2.8 pins made round and the holes cut."""
    adds, cuts = [], []
    has_female = False
    for p in fx["frame"]:
        n = p["part"]
        if n.startswith("control-board locating pin"):
            continue                                   # re-made round below
        if "dovetail" in n and "female" in n:
            has_female = True                          # the box is the groove envelope, not material
            continue
        adds.append(prism_x(p["side"], *p["x"]))
    males = [p for p in fx["frame"] if "dovetail male root" in p["part"]]
    if males:
        adds += dovetail_male_at(max(p["x"][1] for p in males))
    if has_female:
        x0b, x1b, y0b, y1b, z0b, z1b = REAR_FEMALE_BLOCK
        adds.append(box(x0b, x1b, y0b, y1b, z0b, z1b))
        cuts += dovetail_female_at(0.0)
        ADJUST.add("A6")
    # control-board locating pins D2.8, hanging z7.8..10.6 (P35)
    for c in [q for q in plan if q["part"].startswith("control-board locating pin")]:
        adds.append(cyl_z(c["circle"][0], c["circle"][1], 7.8, 10.7, FEAT["cb_pin_d"]))
    for c in [q for q in plan if q["part"].startswith("control-board screw")]:
        cuts.append(cyl_z(c["circle"][0], c["circle"][1], 10.0, FEAT["cb_screw_top"], FEAT["cb_screw_bore"]))
    # female prisms: spring grooves + chamfers as drawn; fin boss bores printed D3.9 teardrop (drill D4.0)
    for p in fx.get("female", []):
        if p["part"].startswith("fin boss bore"):
            cuts.append(teardrop_x(L_AXIS[0], L_AXIS[1], p["x"][0] - 0.01, p["x"][1] + 0.01, FEAT["fin_bore_print"]))
        else:
            cuts.append(prism_x(p["side"], *p["x"]))
            if p["part"].startswith("spring groove cut"):
                # CAD adjustment A2: the long leg (P18 line y205.87 z32.91 -> y210.75 z54.50, wire 0.5) crosses the
                # rear-wall face y209 at z46.76, 0.24 under the groove start z47 -> it would bite 0.3 into the wall
                # over z45.6..47. Carry the groove 2.0 lower in the rear wall only (y209..211), same x width.
                ys = [q[0] for q in p["side"]]
                zs = [q[1] for q in p["side"]]
                cuts.append(box(p["x"][0], p["x"][1], 209.0 - 0.01, max(ys), min(zs) - FEAT["groove_ext"], min(zs) + 0.01))
                ADJUST.add("A2")
    # balance pin holes (press, D2 x 12 pin, top z23.30 -> bottom z11.30) at y135.3 (P32)
    for p in fx["bought"]:
        if p["part"].startswith("balance pin D2"):
            ys = [q[0] for q in p["side"]]
            zs = [q[1] for q in p["side"]]
            cx = (p["x"][0] + p["x"][1]) / 2
            cy = (min(ys) + max(ys)) / 2
            cuts.append(cyl_z(cx, cy, min(zs), 19.5, FEAT["bal_pin_hole_d"]))    # bottom z11.3 = pin bottom (P32)
    # sensor bar / board M3x10 self-tapping pilots in the left post (P111)
    for (sx, sy) in FEAT["sb_screws"]:
        cuts.append(cyl_z(sx, sy, 2.99, 7.01, FEAT["sb_pilot_d"]))       # through (tip reaches z3.6); the bottom EVA covers it
    # black keeper hooks end at y80.5 while their tab starts at y80.8 (P31, model gap 0.3): bridge them
    tabs = {p["part"].split(" ", 1)[1]: p for p in fx["frame"] if p["part"].startswith("tab ")}
    for p in fx["frame"]:
        if p["part"].startswith("keeper hook "):
            nt = p["part"].split(" ", 2)[2]
            t = tabs.get(nt)
            if not t:
                continue
            hy1 = max(q[0] for q in p["side"])
            ty0 = min(q[0] for q in t["side"])
            if ty0 - hy1 > 1e-6:
                hz = [q[1] for q in p["side"]]
                adds.append(box(p["x"][0], p["x"][1], hy1 - 0.2, ty0 + 0.2, min(hz), max(hz)))
                BRIDGED.append(p["part"])
    # hairline seams: pad-bar rail webs stop 0.12..0.13 short of the 0.1-thinner front extension of the fins
    # (P12 / P13) -> fill gaps under 0.2 over the common y/z span so the print has no ragged slit
    rails = [p for p in fx["frame"] if p["part"] == "pad bar rail"]
    fins = [p for p in fx["frame"] if p["part"] == "fin"]
    for r in rails:
        ry = [q[0] for q in r["side"]]
        rz = [q[1] for q in r["side"]]
        for f_ in fins:
            fy = [q[0] for q in f_["side"]]
            fz = [q[1] for q in f_["side"]]
            for (a0, a1, b0, b1) in ((r["x"][1], f_["x"][0], None, None), (f_["x"][1], r["x"][0], None, None)):
                gap = a1 - a0
                if 1e-6 < gap < 0.2:
                    y0_, y1_ = max(min(ry), min(fy)), min(max(ry), max(fy))
                    z0_, z1_ = max(min(rz), min(fz)), min(max(rz), max(fz))
                    if y1_ > y0_ and z1_ > z0_:
                        # 0.01 inside the common span so no edge of the fill lands on an edge of the fin / rail
                        # (coincident edges became 4-face edges in the STL)
                        adds.append(box(a0 - 0.01, a1 + 0.01, y0_ + 0.01, y1_ - 0.01, z0_ + 0.01, z1_ - 0.01))
    m = union(adds + list(extra_adds))
    return clean(diff(m, cuts + list(extra_cuts)))


BRIDGED = []


def sensor_pockets(side):
    """hall-sensor pockets + lead grooves + D0.9 lead holes (v3 D04/D05/S23/S24/P110, BRD-02 rev B; spec ka2)."""
    if not SPECF:
        return []
    sb = SPECF["sensor_bar"]
    if side is None:
        items = [dict(p, lead_x=p["lead_holes"][0]["x"]) for p in sb["pockets_module"]]
    else:
        items = [p for p in sb["pockets_end_parts"] if p["part"].startswith("left" if side == "left" else "right")]
    cuts = []
    for p in items:
        zf = p["pocket_floor_z"]
        cuts.append(box(p["pocket_x"][0], p["pocket_x"][1], p["pocket_y"][0], p["pocket_y"][1], zf, 14.5))
        cuts.append(box(p["lead_groove_x"][0], p["lead_groove_x"][1], p["lead_groove_y"][0], p["lead_groove_y"][1], zf, 14.5))
        for y in (64.46, 67.0, 69.54):
            cuts.append(cyl_z(p["lead_x"], y, 8.0, zf + 0.01, 0.9))
    return cuts


def sensorbar_solid(fx, side=None):
    m = union([prism_x(p["side"], *p["x"]) for p in fx.get("sensorbar", [])])
    cuts = [cyl_z(sx, sy, 7.0, 14.0, FEAT["sb_clear_d"]) for (sx, sy) in FEAT["sb_screws"]]
    cuts += sensor_pockets(side)
    return clean(diff(m, cuts))


def curtain_solid(fx):
    return union([prism_x(p["side"], *p["x"]) for p in fx.get("curtain", [])])


def plug_solid(fx):
    return union([prism_x(p["side"], *p["x"]) for p in fx.get("plug", [])])


PAD_LABELS = {"패드바_칸1": "1 C·C#·D", "패드바_칸2": "2 D#·E·F", "패드바_칸3": "3 F#·G·G#", "패드바_칸4": "4 A·A#·B",
              "패드바_끝부속_왼쪽": "L A0·A#0·B0", "패드바_끝부속_오른쪽": "R C8"}


def pad_label(nm, x0, x1):
    """bay name debossed 0.4 in the bar top face over y148.5..160 (spec ka2; reads from above). A12: the top face is
    the seat plane z67.35 (was z68.85)."""
    s_ = PAD_LABELS.get(nm)
    if not s_:
        return None
    size = 4.2
    t = text_xy(s_, size, 0.6, 0, 0, 0, "center", "center", rot=90)
    b = t.bounding_box()
    if b[3] - b[0] > (x1 - x0) - 2 or b[4] - b[1] > 11.0:
        k = min(((x1 - x0) - 2) / (b[3] - b[0]), 11.0 / (b[4] - b[1]))
        t = text_xy(s_, size * k, 0.6, 0, 0, 0, "center", "center", rot=90)
    t = text_xy(s_, size, 0.6, 0, 0, 0, "center", "center", heavy=True)
    b = t.bounding_box()
    k = min(1.0, ((x1 - x0) - 2) / (b[3] - b[0]), 9.0 / (b[4] - b[1]))
    if k < 1.0:
        t = text_xy(s_, size * k, 0.6, 0, 0, 0, "center", "center", heavy=True)
    return t.translate(((x0 + x1) / 2, 154.25, PAD_SEAT_A12 - 0.4))


PAD_NORMAL = {"w": tuple(G["key_points"]["white D"]["pad_face"]["normal"]),
              "b": tuple(G["key_points"]["black C#"]["pad_face"]["normal"])}


def thicker_wedge(s, extra):
    """move the wedge's pad face (its two lowest points) down by `extra` along the pad normal (PORON 5T variant)."""
    zs = sorted(q[1] for q in s)
    lo = set(zs[:2])
    n = PAD_NORMAL["w"] if abs(s[0][1] - s[1][1]) > 2.2 else PAD_NORMAL["b"]
    return [((y - n[0] * extra, z - n[1] * extra) if z in lo else (y, z)) for (y, z) in s]


def padbar_a12_poly(p):
    """A12 (2026-10-29): a pad bar that prints with no support, top face on the bed. The bar top is one plane, the
    plate seat z67.35 (the old front part stood 1.5 higher, at the plate's z68.85, which left the seat part hanging
    1.5 over the bed). The front part (in front of the lower step y165.5) is 1.0 thick so it stays 1.55 above the
    lever fingernail tab at ff; it no longer touches the plate - only the seat part over the pads does. The leaf
    tongue moves up 0.9 so its top is flush with the bar top in the printed (free) state; its tip nub reaches down
    to the rail lip as before, and the plate has a 0.6 groove over the leaf travel (frame_split)."""
    n, s = p["part"], p["side"]
    ys = [q[0] for q in s]
    if n == "pad bar" or n.startswith("pad bar (edge strip, front"):
        y_low = min(q[0] for q in s if abs(q[1] - PAD_SEAT_A12 + 1.5) < 1e-6)
        yf, yr = min(ys), max(ys)
        zt, zf, zb = PAD_SEAT_A12, PAD_SEAT_A12 - PAD_FRONT_T, PAD_SEAT_A12 - 1.5
        return [(yf, zf), (y_low, zf), (y_low, zb), (yr, zb), (yr, zt), (yf, zt)]
    if n.startswith("pad bar grip"):
        return [(min(ys), PAD_SEAT_A12 - 2.5), (max(ys), PAD_SEAT_A12 - 2.5), (max(ys), PAD_SEAT_A12), (min(ys), PAD_SEAT_A12)]
    if n.startswith("pad bar leaf"):
        return [(y, z) if z < PAD_SEAT_A12 - 1.75 else (y, z + 0.9) for (y, z) in s]
    return s


PAD_SEAT_A12 = 67.35       # plate underside over the pads (solved z_seat)
PAD_FRONT_T = 1.0          # A12 front part of the bar


def padbar_solids(fx, ranges, names, free=True, wedge_extra=0.0):
    """split the pad-bar prisms into bars by x range; the installed (0.3 lifted) leaf tongue is
    printed straight: tip dropped back by the 0.3 preload (P13). A12: flat top, leaf flush with it."""
    out = {}
    for (x0, x1), nm in zip(ranges, names):
        items, leaves, slots = [], [], []
        for p in fx.get("padbar", []):
            if p["x"][0] >= x0 - 0.01 and p["x"][1] <= x1 + 0.01:
                s = padbar_a12_poly(p)
                ADJUST.add("A12")
                if p["part"].startswith("pad wedge") and wedge_extra:
                    s = thicker_wedge(s, wedge_extra)
                if p["part"].startswith("pad bar leaf"):
                    if free:
                        s = free_leaf(s)
                    leaves.append(prism_x(s, *p["x"]))
                    ys = [q[0] for q in p["side"]]
                    # widen the cut-out around the tongue from 0.4 to 0.6 (sides and tip), root (rear) stays attached
                    slots.append(box(p["x"][0] - 0.6, p["x"][1] + 0.6, min(ys) - 0.6, max(ys) - 0.3, 60.0, 70.0))
                    continue
                items.append(prism_x(s, *p["x"]))
        m = union(items)
        if slots:
            m = union([diff(m, slots)] + leaves)
        lab = pad_label(nm, x0, x1)
        if lab is not None:
            m = diff(m, [lab])
        out[nm] = clean(m)
    return out


def free_leaf(s, lift=0.3, root_y=183.0, tip_y=175.8):
    L = root_y - tip_y
    out = []
    for (y, z) in s:
        u = max(0.0, min(1.0, (root_y - y) / L))
        d = lift * (3 * u * u - u ** 3) / 2.0          # cantilever deflection shape, 1 at the tip
        out.append((y, z - d))
    return out


# ------------------------------------------------------------------ dovetails (v3 drawing 6, v4 boxes)
def dovetail_male(face_x, yc, z0, z1, root=6.0, tip=9.0, depth=4.0):
    """tongue standing out of the +x face at face_x: width root at the face, tip at face_x + depth."""
    pts = [(face_x - 0.01, yc - root / 2), (face_x + depth, yc - tip / 2), (face_x + depth, yc + tip / 2), (face_x - 0.01, yc + root / 2)]
    return prism_z(pts, z0, z1)


def dovetail_female(face_x, yc, z0, z1, root=6.0, tip=9.0, depth=4.0, clr=0.2):
    """groove into the -x face (face at face_x, going +x), open at the bottom, closed above z1."""
    r, t = root + 2 * clr, tip + 2 * clr
    pts = [(face_x - 0.01, yc - r / 2), (face_x + depth + clr, yc - t / 2), (face_x + depth + clr, yc + t / 2), (face_x - 0.01, yc + r / 2)]
    return prism_z(pts, z0 - 0.01, z1)


# ------------------------------------------------------------------ A12 (2026-10-29): prints with no support
# The user printed one octave and found the supports hard to get off (under the frame's top plate ~88 g per module,
# in the lever pocket, under the pad bar seat). A12 splits the parts so that every face prints on the bed, as a
# wall or as a short bridge:
#   frame  -> bed (floor, rails, balance rail; printed upright) + cage (top plate, fins, rear wall, shelf; printed on its
#             back) + guide tabs (tab + keeper hook, printed on the side, glued into sockets in the bed)
#   lever  -> body + cover (the +x wall with its lips), bonded with the steel (lever_body_solid / lever_cover_solid)
#   pad bar -> one flat top plane, leaf flush with it (padbar_a12_poly)
#   keys   -> unchanged (one piece is the strongest), a tear-off comb under the hidden beam (key_print_support)
from cadlib import _cs, _seg  # noqa: E402

CAGE_RX = [r"^fin$", r"^fin boss$", r"^fin keel", r"^top plate", r"^pad bar rail$", r"^pad bar rail lip$", r"^rear wall",
           r"^spring groove boss", r"^rear shelf$", r"^shelf rib$", r"^control-board boss.*shelf rib"]
TAB_RX = r"^(tab |keeper hook )"
A12 = {
    "clr": 0.15,          # side clearance: cage fin feet in the bed slots, tab tenons in their sockets
    "tenon": 5.0,         # guide-tab tenon depth into the white front rail / black tab base
    "tenon_key": 1.0,     # tenon starts 1.0 behind the tab front, so a tab only goes in the right way round
    "slot_h": 2.5,        # bed ribs either side of a cage fin foot, z5 -> 7.5
    "usb_open": (76.45, 91.55),   # rear-wall USB-C opening narrowed to the shelf gap (plug envelope x77.75..90.25)
    "groove": 0.6,        # pad-bar leaf groove in the plate underside over the leaf travel
    "gap": 0.2,           # air gap of the print-only tear-off supports (comb, posts) to the part
}
# cage -> bed screws, modules only (M3 x 10 self-tapping from under the bed floor; glue may be used as well):
#   'wall' = D boss on the rear wall under the shelf, between shelf ribs; 'fin' = pointed boss on fins 2 and 4
CAGE_SCREWS = [(29.0, 203.0, "wall"), (143.0, 203.0, "wall"), (41.66, 160.5, "fin"), (123.925, 160.5, "fin")]
SCREW = {"boss_d": 6.4, "pilot": 2.5, "clear": 3.4, "top": 14.0}


def _ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if a > 0 else pts[::-1]


def _point_shape(cx, cy, r, ux, uy):
    """circle (cx, cy, r) + a 45 deg point toward the unit direction (ux, uy) (polygon, counter-clockwise)."""
    n = _seg(2 * r)
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    px, py = -uy, ux
    s = r / math.sqrt(2)
    tri = _ccw([(cx + ux * s + px * s, cy + uy * s + py * s), (cx + ux * s - px * s, cy + uy * s - py * s),
                (cx + ux * r * math.sqrt(2), cy + uy * r * math.sqrt(2))])
    return max((_cs(_ccw(pts)) + _cs(tri)).to_polygons(), key=len)


def teardrop_x_apex(cy, cz, x0, x1, d, apex=(-1.0, 0.0)):
    """cylinder / hole along x with a 45 deg point toward apex = (dy, dz): the cage prints with -y up."""
    return prism_x(_point_shape(cy, cz, d / 2.0, apex[0], apex[1]), x0, x1)


def pointed_z(cx, cy, z0, z1, d, tip=(0.0, 1.0), cut=None):
    """cylinder along z with a 45 deg point toward tip = (dx, dy), so it prints lying on its side; cut = largest distance
    of the point from the axis (a locating pin that must still enter its round hole)."""
    m = prism_z(_point_shape(cx, cy, d / 2.0, tip[0], tip[1]), z0, z1)
    if cut is not None:
        big = 50.0
        if abs(tip[1]) > 0.5:
            yb = cy + tip[1] * cut
            m = m ^ box(cx - big, cx + big, min(yb, cy - big), max(yb, cy + big), z0 - 1, z1 + 1)
        else:
            xb = cx + tip[0] * cut
            m = m ^ box(min(xb, cx - big), max(xb, cx + big), cy - big, cy + big, z0 - 1, z1 + 1)
    return m


def _upper_z(polys, y):
    """highest z of the (y, z) polygons on the vertical line y (None if no polygon spans y)."""
    best = None
    for pts in polys:
        for i in range(len(pts)):
            (ya, za), (yb, zb) = pts[i], pts[(i + 1) % len(pts)]
            if min(ya, yb) - 1e-9 <= y <= max(ya, yb) + 1e-9 and abs(yb - ya) > 1e-9:
                z = za + (zb - za) * (y - ya) / (yb - ya)
                best = z if best is None else max(best, z)
    return best


def key_print_support(parts, black):
    """A12 tear-off comb under the hidden beam and the thin tail of a key printed top face down (print file only, not
    in the assembly): a 0.8 blade on the beam axis plus cross ribs every 8 mm (beam width - 1.0), standing on the bed
    with a 0.2 air gap under the beam (+ for a black key a 1.2 pad under the 0.6 skin step behind y144.3). Nothing is
    fused to the key, so the comb lifts off in one piece."""
    by = {p["part"]: p for p in parts}
    beam = [p for p in parts if p["part"] == "beam"][0]
    tail = [p for p in parts if p["part"] == "thin tail"]
    polys = [beam["side_rest"]] + [t["side_rest"] for t in tail]
    zbed = max(q[1] for p in parts if p["part"].startswith("skin") for q in poly(p, "rest"))
    gap = A12["gap"]
    y0, y1 = 147.3, max(q[0] for pts in polys for q in pts) - 1.0
    cx = (beam["x"][0] + beam["x"][1]) / 2.0
    w = beam["x"][1] - beam["x"][0]
    ys = [y0 + i * 0.25 for i in range(int((y1 - y0) / 0.25) + 1)] + [y1]
    # highest beam / tail top within +-0.5 of each sample (the beam -> thin tail step near y192.4 is vertical)
    top = lambda y: max(z for z in (_upper_z(polys, y + d) for d in (-0.5, -0.25, 0.0, 0.25, 0.5)) if z is not None)
    lo = [(y, top(y) + gap) for y in ys]
    blade = prism_x(_ccw(lo + [(y1, zbed), (y0, zbed)]), cx - 0.4, cx + 0.4)
    ribs = []
    yr = y0 + 2.0
    while yr < y1 - 1.0:
        zr = max(top(yr - 0.4), top(yr + 0.4)) + gap
        ribs.append(box(cx - (w - 1.0) / 2, cx + (w - 1.0) / 2, yr - 0.4, yr + 0.4, zr, zbed))
        yr += 8.0
    out = [blade] + ribs
    if black and "skin" in by:
        sk = poly(by["skin"], "rest")
        z_step = min(q[1] for q in sk if q[0] > 144.0 and q[1] > 54.0)          # skin top behind y144.3 (54.1)
        out.append(box(by["skin"]["x"][0] + 0.5, by["skin"]["x"][1] - 0.5, 144.5, 146.8, z_step + gap, zbed))
    return union(out)


def _is_cage(name):
    return any(re.search(r, name) for r in CAGE_RX)


def _cage_poly(p):
    """fin outlines on the cage: the +y facing steps would hang when the cage prints on its back -> 45 deg slope
    (F|F# fin: foot z3 to y170.7 then z21.5 = a gusset down to the keel; end fins: notch over the dovetail block)."""
    s = [tuple(q) for q in p["side"]]
    if p["part"] != "fin":
        return s
    out = []
    for i, (y, z) in enumerate(s):
        nxt = s[(i + 1) % len(s)]
        if abs(nxt[0] - y) < 1e-9 and z < 6.0 and (round(y, 3), round(nxt[1], 3)) in ((170.7, 21.5), (196.7, 19.0)):
            out.append((y - (nxt[1] - z), z))
            continue
        if (round(y, 3), round(z, 3)) == (167.5, 68.85):
            out.append((168.0, 68.85))     # fin top steps up at the plate step y168 (the model's 0.5 slope left a sliver under the plate)
            continue
        out.append((y, z))
    return out


def frame_split(fx, plan, extra_cuts=(), extra_adds=(), side=None):
    """A12 frame in three kinds of part, unit (local) coordinates, assembled pose:
      bed   : floor, white front rail, black stop rails / tab bases, sensor-bar post + ledges, balance rail, dovetails,
              front board bosses, cheek (end parts), sockets for the guide tabs, slot ribs for the cage fin feet
      cage  : top plate (+ pad-bar rails), fins (+ lever-rod bosses), rear wall, rear shelf + ribs, rear board bosses
      tabs  : [(note, 'white'|'black', solid)] tab + keeper hook (hook as wide as the tab) + tenon
      posts : print-only tear-off posts under the two front board bosses (they hang off the balance rail)
    The geometry is the monolithic frame's (frame_solid) apart from the joint features and the print slopes."""
    clr = A12["clr"]
    bed_adds, cage_adds, bed_cuts, cage_cuts, tabs = [], [], [], [], []
    has_female = False
    tab_by, hook_by = {}, {}
    for p in fx["frame"]:
        n = p["part"]
        if n.startswith("control-board locating pin"):
            continue
        if re.search(TAB_RX, n):
            if n.startswith("keeper hook"):
                hook_by[n.split(" ", 2)[2]] = p
            else:
                tab_by[n.split(" ", 1)[1]] = p
            continue
        if "dovetail" in n and "female" in n:
            has_female = True
            continue
        if not _is_cage(n):
            bed_adds.append(prism_x(p["side"], *p["x"]))
            continue
        ys = [q[0] for q in p["side"]]
        zs = [q[1] for q in p["side"]]
        if n.startswith("control-board boss"):
            # rear board bosses hung off one shelf rib: carried back to the rear wall so they stand on it in print
            cage_adds.append(box(p["x"][0], p["x"][1], min(ys), 209.0 + 0.01, min(zs), max(zs)))
        elif n == "fin boss":
            # lever-rod boss, pointed toward +y (down on the bed when the cage prints on its back)
            cage_adds.append(teardrop_x_apex((max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2, p["x"][0], p["x"][1],
                                             max(ys) - min(ys), apex=(1.0, 0.0)))
        elif n.startswith("rear wall") and side is None and abs(min(zs) - 21.0) < 1e-6:
            # wall over the USB-C opening x74..94 z5..21: opening narrowed to the shelf gap, so the shelf and the shelf
            # ribs beside it stand on the wall (the first layers of the cage)
            cage_adds.append(prism_x(p["side"], *p["x"]))
            uo = A12["usb_open"]
            cage_adds.append(box(p["x"][0], uo[0], min(ys), max(ys), 5.0, 21.0 + 0.01))
            cage_adds.append(box(uo[1], p["x"][1], min(ys), max(ys), 5.0, 21.0 + 0.01))
        else:
            cage_adds.append(prism_x(_cage_poly(p), *p["x"]))
    males = [p for p in fx["frame"] if "dovetail male root" in p["part"]]
    if males:
        bed_adds += dovetail_male_at(max(p["x"][1] for p in males))
    if has_female:
        x0b, x1b, y0b, y1b, z0b, z1b = REAR_FEMALE_BLOCK
        bed_adds.append(box(x0b, x1b, y0b, y1b, z0b, z1b))
        bed_cuts += dovetail_female_at(0.0)
        ADJUST.add("A6")
    # control-board pins and screw bores: front pair on the bed (rail bracket), rear pair on the cage (shelf rib)
    for c in [q for q in plan if q["part"].startswith("control-board locating pin")]:
        cx, cy = c["circle"][0], c["circle"][1]
        if cy < 170.0:
            bed_adds.append(cyl_z(cx, cy, 7.8, 10.7, FEAT["cb_pin_d"]))
        else:
            # lies sideways on the cage's back: pointed toward +y, point cut at r1.45 (board hole D3.0)
            cage_adds.append(pointed_z(cx, cy, 7.8, 10.7, FEAT["cb_pin_d"], tip=(0.0, 1.0), cut=1.45))
    for c in [q for q in plan if q["part"].startswith("control-board screw")]:
        cx, cy = c["circle"][0], c["circle"][1]
        if cy < 170.0:
            bed_cuts.append(cyl_z(cx, cy, 10.0, FEAT["cb_screw_top"], FEAT["cb_screw_bore"]))
        else:
            cage_cuts.append(pointed_z(cx, cy, 10.0, FEAT["cb_screw_top"], FEAT["cb_screw_bore"], tip=(0.0, -1.0)))
    for p in fx.get("female", []):
        if p["part"].startswith("fin boss bore"):
            cage_cuts.append(teardrop_x_apex(L_AXIS[0], L_AXIS[1], p["x"][0] - 0.01, p["x"][1] + 0.01, FEAT["fin_bore_print"]))
        else:
            cage_cuts.append(prism_x(p["side"], *p["x"]))
            if p["part"].startswith("spring groove cut"):
                ys = [q[0] for q in p["side"]]
                zs = [q[1] for q in p["side"]]
                cage_cuts.append(box(p["x"][0], p["x"][1], 209.0 - 0.01, max(ys), min(zs) - FEAT["groove_ext"], min(zs) + 0.01))
                ADJUST.add("A2")
    for p in fx["bought"]:
        if p["part"].startswith("balance pin D2"):
            ys = [q[0] for q in p["side"]]
            zs = [q[1] for q in p["side"]]
            bed_cuts.append(cyl_z((p["x"][0] + p["x"][1]) / 2, (min(ys) + max(ys)) / 2, min(zs), 19.5, FEAT["bal_pin_hole_d"]))
    for (sx, sy) in FEAT["sb_screws"]:
        bed_cuts.append(cyl_z(sx, sy, 2.99, 7.01, FEAT["sb_pilot_d"]))
    # hairline seams rail web <-> fin (as frame_solid), on the cage
    rails = [p for p in fx["frame"] if p["part"] == "pad bar rail"]
    fins = [p for p in fx["frame"] if p["part"] == "fin"]
    for r in rails:
        ry, rz = [q[0] for q in r["side"]], [q[1] for q in r["side"]]
        for f_ in fins:
            fy, fz = [q[0] for q in f_["side"]], [q[1] for q in f_["side"]]
            for (a0, a1) in ((r["x"][1], f_["x"][0]), (f_["x"][1], r["x"][0])):
                if 1e-6 < a1 - a0 < 0.2:
                    y0_, y1_ = max(min(ry), min(fy)), min(max(ry), max(fy))
                    z0_, z1_ = max(min(rz), min(fz)), min(max(rz), max(fz))
                    if y1_ > y0_ and z1_ > z0_:
                        cage_adds.append(box(a0 - 0.01, a1 + 0.01, y0_ + 0.01, y1_ + 0.01, z0_ + 0.01, z1_ - 0.01))
    # ---- guide tabs (tab + keeper hook as wide as the tab + tenon), printed on the side; sockets in the bed
    for key, t in tab_by.items():
        ys, zs = [q[0] for q in t["side"]], [q[1] for q in t["side"]]
        ty0, ty1, tz0, tz1 = min(ys), max(ys), min(zs), max(zs)
        h = hook_by[key]
        hy0 = min(q[0] for q in h["side"])
        hz0 = min(q[1] for q in h["side"] if q[0] < ty0 - 0.5)          # hook underside z28.6
        fillet = any(abs(q[0] - (ty0 - 0.3)) < 1e-6 for q in h["side"])  # white: (14.5, 28.6)-(14.8, 27.7) root fillet
        zt0, yk = tz0 - A12["tenon"], ty0 + A12["tenon_key"]
        pts = [(yk, zt0), (ty1, zt0), (ty1, tz1), (hy0, tz1), (hy0, hz0)]
        pts += [(ty0 - 0.3, hz0), (ty0, hz0 - 0.9)] if fillet else [(ty0, hz0)]
        pts += [(ty0, tz0), (yk, tz0)]
        # one print file per colour: width to 0.1 (black tabs are 6.89..6.90 in the model), same centre
        xc, wt = (t["x"][0] + t["x"][1]) / 2.0, round(t["x"][1] - t["x"][0], 1)
        tx0, tx1 = xc - wt / 2.0, xc + wt / 2.0
        tabs.append((key, "black" if tz0 > 11.5 else "white", prism_x(_ccw(pts), tx0, tx1)))
        bed_cuts.append(box(tx0 - clr, tx1 + clr, yk - clr, ty1 + clr, zt0 - 0.3, tz0 + 0.01))
    # ---- slot ribs on the bed either side of each cage fin foot standing on the floor (not the F|F# fin over the hatch)
    floors = [p for p in fx["frame"] if p["part"].startswith("floor")]
    fl0, fl1 = min(p["x"][0] for p in floors), max(p["x"][1] for p in floors)
    for f_ in fins:
        pf = _cage_poly(f_)
        if abs(min(q[1] for q in pf) - 5.0) > 1e-6:
            continue
        foot = [q[0] for q in pf if abs(q[1] - 5.0) < 1e-6]
        for (xa, xb) in ((f_["x"][0] - clr - 1.0, f_["x"][0] - clr), (f_["x"][1] + clr, f_["x"][1] + clr + 1.0)):
            if xa < fl0 + 0.2 or xb > fl1 - 0.2:
                continue                                   # unit edge: the neighbour's fin (or nothing) is there
            bed_adds.append(box(xa, xb, min(foot) + 1.0, min(max(foot), 195.0), 5.0 - 0.01, 5.0 + A12["slot_h"]))
    # ---- cage -> bed screws (modules)
    if side is None:
        for (sx, sy, kind) in CAGE_SCREWS:
            r = SCREW["boss_d"] / 2.0
            if kind == "wall":
                cage_adds.append(union([cyl_z(sx, sy, 5.0, SCREW["top"], SCREW["boss_d"]), box(sx - r, sx + r, sy, 209.0 + 0.01, 5.0, SCREW["top"])]))
            else:
                cage_adds.append(pointed_z(sx, sy, 5.0, SCREW["top"], SCREW["boss_d"], tip=(0.0, 1.0)))
                bed_cuts.append(box(sx - r - 1.5, sx + r + 1.5, sy - r - 0.5, sy + r * math.sqrt(2) + 0.5, 4.98, 5.0 + A12["slot_h"] + 0.1))
            cage_cuts.append(pointed_z(sx, sy, 5.0 - 0.01, SCREW["top"] - 1.0, SCREW["pilot"], tip=(0.0, -1.0)))
            bed_cuts.append(cyl_z(sx, sy, 2.9, 5.1, SCREW["clear"]))
    # ---- pad-bar leaf grooves in the plate underside over the leaf travel (A12 leaf is flush with the bar top)
    for p in fx.get("padbar", []):
        if p["part"].startswith("pad bar leaf"):
            cage_cuts.append(box(p["x"][0] - 0.2, p["x"][1] + 0.2, 167.9, 183.4, PAD_SEAT_A12 - 0.01, PAD_SEAT_A12 + A12["groove"]))
    # ---- print-only tear-off posts under the front board bosses (and the locating pin hanging under one of them)
    posts = []
    for c in [q for q in plan if q["part"].startswith("control-board boss") and q["circle"][1] < 170.0]:
        cx = c["circle"][0]
        x0p, x1p, y0p, y1p = cx - 2.6, cx + 2.6, 145.0, 151.6
        ztop = 10.6 - A12["gap"]
        ring = diff(box(x0p, x1p, y0p, y1p, 3.0, ztop), [box(x0p + 0.8, x1p - 0.8, y0p + 0.8, y1p - 0.8, 2.9, ztop + 0.1)])
        extra = []
        for q in plan:
            if q["part"].startswith("control-board locating pin") and abs(q["circle"][0] - cx) < 1.0 and q["circle"][1] < 170.0:
                px, py = q["circle"][0], q["circle"][1]
                extra += [cyl_z(px, py, 3.0, 7.8 - A12["gap"], 2.0), box(x0p + 0.4, x1p - 0.4, py - 0.3, py + 0.3, 3.0, 6.0)]
        posts.append(union([ring] + extra))
    if side is not None:
        # end parts: the rear wall stops 0.4 short of the end fin by the cheek; on the cage's back that fin end would
        # hang 3 mm over the bed -> carry the wall out to the fin's outer face (it sits in the cheek recess)
        walls = [p for p in fx["frame"] if p["part"].startswith("rear wall")]
        rw0, rw1 = min(p["x"][0] for p in walls), max(p["x"][1] for p in walls)
        fx0, fx1 = min(p["x"][0] for p in fins), max(p["x"][1] for p in fins)
        if fx0 < rw0:
            cage_adds.append(box(fx0, rw0 + 0.01, 208.99, 212.0, 5.0, 72.85))
        if fx1 > rw1:
            cage_adds.append(box(rw1 - 0.01, fx1, 208.99, 212.0, 5.0, 72.85))
    bed = union(bed_adds + list(extra_adds))
    cage = union(cage_adds)
    if side is not None:
        # end parts: the cheek stays whole on the bed (its outer face and top are the instrument's end panel); the cage
        # stops at the outer face of its end fin, which with the plate edge and the rod boss sits in a recess in the cheek
        fx0 = min(p["x"][0] for p in fins)
        fx1 = max(p["x"][1] for p in fins)
        cheek = [p for p in fx["frame"] if p["part"] == "cheek"]
        if cheek and cheek[0]["x"][0] < fx0 + 1.0:
            cage = cage ^ box(fx0, 1e3, -1e3, 1e3, -1e3, 1e3)
        elif cheek:
            cage = cage ^ box(-1e3, fx1, -1e3, 1e3, -1e3, 1e3)
        # recess = one box over the cheek's inner face: from the cage's end fin face (+ clr) to just past the cheek face,
        # plate front - clr .. rear face, floor top z5 .. top (open at the top and the back; 0.15 joint line there)
        y0r = min(min(q[0] for q in p["side"]) for p in fx["frame"] if p["part"].startswith("top plate")) - clr
        if cheek and cheek[0]["x"][0] < fx0 + 1.0:
            rx0, rx1 = fx0 - clr, cheek[0]["x"][1] + 0.001
        elif cheek:
            rx0, rx1 = cheek[0]["x"][0] - 0.001, fx1 + clr
        else:
            rx0 = rx1 = 0.0
        if rx1 > rx0:
            bed = bed - box(rx0, rx1, y0r, 213.0, 5.0, 74.0)
    bed = clean(diff(bed, bed_cuts + list(extra_cuts)))
    cage = clean(diff(cage, cage_cuts))
    ADJUST.add("A12")
    return {"bed": bed, "cage": cage, "tabs": tabs, "posts": posts}
