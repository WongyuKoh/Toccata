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
    m = union(prisms(parts, "rest", KEY_BOUGHT))
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
    """bay name debossed 0.4 in the bar top face z68.85 over y148.5..160 (spec ka2; reads from above)."""
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
    return t.translate(((x0 + x1) / 2, 154.25, 68.85 - 0.4))


PAD_NORMAL = {"w": tuple(G["key_points"]["white D"]["pad_face"]["normal"]),
              "b": tuple(G["key_points"]["black C#"]["pad_face"]["normal"])}


def thicker_wedge(s, extra):
    """move the wedge's pad face (its two lowest points) down by `extra` along the pad normal (PORON 5T variant)."""
    zs = sorted(q[1] for q in s)
    lo = set(zs[:2])
    n = PAD_NORMAL["w"] if abs(s[0][1] - s[1][1]) > 2.2 else PAD_NORMAL["b"]
    return [((y - n[0] * extra, z - n[1] * extra) if z in lo else (y, z)) for (y, z) in s]


def padbar_solids(fx, ranges, names, free=True, wedge_extra=0.0):
    """split the pad-bar prisms into bars by x range; the installed (0.3 lifted) leaf tongue is
    printed straight: tip dropped back by the 0.3 preload (P13)."""
    out = {}
    for (x0, x1), nm in zip(ranges, names):
        items, leaves, slots = [], [], []
        for p in fx.get("padbar", []):
            if p["x"][0] >= x0 - 0.01 and p["x"][1] <= x1 + 0.01:
                s = p["side"]
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
