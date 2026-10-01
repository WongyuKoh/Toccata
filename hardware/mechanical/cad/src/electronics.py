"""Toccata electronics as Part instances (world coordinates, assembled pose) - L2 one-piece rear bar (2026-10-01).

Governing layout: spec/body_L2.json ("L2": rear unit y214..body.YB (342.5 at the selected 40 deg) behind a 2.0 mm air gap to the key modules, cable duct y212..241
x z0..27 under the whole rear unit, centre unit x260..962 with lids flush with the key tops z72.85, no front wall (front zone
y214..241 open to the duct), speaker pods with the baffle at body.ANGLE deg from horizontal). The L1 version of this file is kept
as electronics_L1.py, the tall v3.2 one as electronics_v3_tall.py.

Sources (the only numeric sources):
  spec/body_L2.json               centre_contents boxes (every CU-E-* / PB-E-* item and the plug / cable zones, used as given - no
                                  v3 -> L1 shift any more), cable_duct (hub bbox, ports x, port z, port_map, cable table), speakers
                                  (driver model / pose), speakers.xt30, cable_duct.other_leads (power / speaker lead routing)
  body.py (L2)                    the one angle constant: DRIVER_POSE, SPK_N / SPK_U, XT30_POCKET, WIRE_YZ, AMP_HOLES, board posts
  spec/electronics_modules.json   boards / modules / cables inside the 7 octave modules and the 2 end parts (unchanged)
  spec/electronics_rearbar.json   rear-bar electronics, speakers, damper pedal (envelope SIZES)
  spec/keyaction_features_frame.json  left-cheek headphone-jack pocket (J701) + the PJ-313 envelope used for J701 / J501 / J702

Cable routing (my design inside the spec zones, see the part notes): module USB-C plug (y196.8..221.8, axis z14.5) -> R8 turn to x
at y229.5 in front of the bundle -> slope to the cable's level -> jog into the bundle y237.5 (4 levels z2.25 / 6.25 / 10.25 /
14.25, one cable per level wherever they run side by side; the cable that leaves first is always the top one) -> at the hub port x
rise straight up behind the front zone and turn +y into the USB-A plug (y247..282, z28.5). O5 / O6 (short runs) use a front-high
lane y226 z24 over the bundle. The spec's single line 'y236.8 z13' would put every cable in the same place.

Shown: boards as plain rectangles with their mounting holes, only the bulky parts on them, plugs, cables (as round tubes along a
filleted centre line), the power harness (PD trigger -> fuse -> switch -> buck / amp, buck -> Pi / hub) and the speaker leads.
Omitted on purpose: every spec item with show:false, hall sensors, key magnets and control-board screws (keyaction_parts.py emits
them), small board parts, the headphone cables W701 / W702 (their plug zones Z-J702-PLUG / Z-DONGLE-PLUG are kept free), the
optional power-bank cable (Z-BANK-PLUG kept free), cable clips.
R31 touchscreen rev 3 (user-approved 2026-10-01, ../touchscreen/rev3/design/CAD_SPEC_rev3.md + numbers.json via touchscreen_rev3.py): the
Waveshare 7-DSI-TOUCH-C display (connector window on the right, mouths +x - estimated side, spec G-1) in the 25 deg use pose, the DSI FFC
(22P 0.5 mm 300 mm type B) along the spec route through the lid hole and the clip to the Pi 5 CAM/DISP 1 (x589, mouth -x, inserted 2.7)
and the GPIO 2 / 6 power lead; the folded display is a separate 'altview' part (not in the one-file assembly / 3MF / GLB). The Pi 5 model
now carries the two micro-HDMI receptacles (estimated, W1 numbers) that the FFC rests on.

Module items: world x = 47 + 164.5 (k-1) + local x (k = 1..7). End items: left = world x, right = 1198.5 + x.
"""
import json
import math
import os

import numpy as np
from manifold3d import Manifold, Mesh

import body as BODY
import touchscreen_rev3 as TS
from cadlib import box, cyl_x, cyl_y, cyl_z, diff, prism_x, prism_z, union
from parts import COLORS, Part

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

MODULE_W = 164.5
X_O1 = 47.0
X_RIGHT = 1198.5
MIRROR_X = 611.0          # speaker parts L/R are mirror images about x = (-16 + 1238) / 2

PI5_GREEN = "#1f7a3f"
BLACK_PLASTIC = "#222222"
XT30_YELLOW = "#e6b422"
WHITE_PLASTIC = "#ececec"
HUB_GREY = "#3b3f45"
BANK_GREY = "#c9ccd1"
WIRE_RED = "#b03a2e"

G_CU = "CU 칸 전자부"
G_BANK = "보조배터리 칸"
G_CAB = "케이블"

# Raspberry Pi 5 port edge (+x): (id suffix, name_ko, name_en, centre from the power/HDMI edge, width along y, depth along x
# incl. the overhang, height above the PCB). Order from the power/HDMI edge: RJ45, USB-A stack, USB-A stack (Pi 5).
PI_PORT_OVERHANG = 2.5
PI_HDMI_XC = (568.0, 581.5)    # Pi 5 micro-HDMI 0 / 1 centres: 26.0 / 39.5 from the non-port end x542 (Pi 4/5 drawing)
PI_HDMI_W = 7.0                # receptacle width along x (W1 box x562~585 spans both)
PI_PORTS = [
    ("RJ45", "라즈베리파이 5 RJ45 이더넷 잭 (안 씀)", "Raspberry Pi 5 RJ45 Ethernet jack (unused)", 10.25, 16.0, 21.25, 13.5),
    ("USBA1", "라즈베리파이 5 USB-A 2단 (RJ45 옆 - 아래: 동글 젠더)", "Raspberry Pi 5 USB-A stack next to the RJ45 (lower: dongle gender)",
     29.0, 14.5, 17.5, 16.4),
    ("USBA2", "라즈베리파이 5 USB-A 2단 (GPIO 쪽 - 아래: 허브 업스트림 C25, 위는 C25 머리에 가려 비움)",
     "Raspberry Pi 5 USB-A stack at the GPIO edge (lower: hub upstream C25; the upper port sits behind the C25 head)",
     47.0, 14.5, 17.5, 16.4),
]

SRC_M = "spec/electronics_modules.json"
SRC_R = "spec/electronics_rearbar.json"
SRC = "spec/body_L2.json"


def _load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


L2 = _load("body_L2.json")

# ------------------------------------------------------------------ L2 constants (body_L2.json + body.py exports)

CC = {c["id"]: tuple(c["bbox_x0x1y0y1z0z1"]) for c in L2["centre_contents"]}     # (x0, x1, y0, y1, z0, z1)
# back-plate items (HUSB238, J501 board + jack, KCD1, cable pass) ride on the printed back plate, i.e. on the back face body.YB: the
# spec boxes were drawn for the 43 deg back face y341.5, so they move by body.DY_BACK (40 deg: +1.0), as body.py does
for _k in BODY.BACK_PLATE_ITEMS:
    _b = CC[_k]
    CC[_k] = (_b[0], _b[1], _b[2] + BODY.DY_BACK, _b[3] + BODY.DY_BACK, _b[4], _b[5])
BACK_SHIFT_TXT = ("" if abs(BODY.DY_BACK) < 1e-9 else
                  "사양과 다름(작은 고침): 사양 centre_contents 상자보다 y+%.1f - 뒤판 출력물이 %.0f° 규칙으로 바깥면 y%.1f → %.1f로 옮겨 가 "
                  "판에 얹힌 부품도 같이 감 (body.py DY_BACK; 그대로 두면 USB-C 입구 앞을 판이 막음); " % (BODY.DY_BACK, BODY.ANGLE, BODY.LAYOUT_BACK_Y, BODY.YB))
DUCT = L2["cable_duct"]
HUBS = DUCT["hub"]
HUB_X0, HUB_X1, HUB_Y, HUB_BACK, HUB_Z0, HUB_Z1 = HUBS["bbox"]                 # 686.5..914.5, 282 (port face)..330, 16.5..40.5
HUB_PORT_X = [float(v) for v in HUBS["ports_x"]]                                 # 696.5 + 22 i
HUB_Z = HUBS["port_z"]                                                          # 28.5
HUB_PORT = dict(HUBS["port_map"])                                               # PED 2, O3 3, O1 4, O2 5, O4 6, O5 7, O6 8, O7 9
CABLE_SPEC = {c["cable"].split()[0]: c for c in DUCT["cables"]}                  # O1..O7, PED -> path_mm, std_m, ...
DUCT_Y = tuple(DUCT["cross_section"]["y"])                                      # (212, 241)
DUCT_Z = tuple(DUCT["cross_section"]["z"])                                      # (0, 27)
CU_IX = tuple(L2["centre"]["inner_x"])                                           # (271.5, 950.5)
Y0 = L2["overall"]["rear_unit_y"][0]                                            # 214
YBI = BODY.YBI                                                                  # 331 back-ply inner faces (40 deg; 43: 330)
Z_BOT = BODY.Z_BOT                                                              # 16.5 floor (bottom ply top)
Z_LIDU = BODY.Z_LIDU                                                            # 61.35 lid underside

CABLE_OD = 3.5            # NA993 USB-A to C (module spec usb_cable assumed 3.5)
MODULE_PLUG_L = 25.0      # USB-C overmold envelope along y (electronics_modules usb_plug y196.8..221.8)
HUB_PLUG_L = 35.0         # USB-A plug + boot (spec Z-HUB-PLUGS y247..282)
PLUG_Y1 = 221.8           # module plug tail
PLUG_Z = 14.5             # module plug axis
BUNDLE_Y = 237.5          # bundle axis y: 1.75 in front of the pod / centre bottom-ply front edge y241 (cable r 1.75)
LEVEL_Z = {"O4": 2.25, "O2": 6.25, "O7": 6.25, "O1": 10.25, "O3": 14.25}    # pitch 4.0 = OD 3.5 + 0.5
FRONT_LANE = (226.0, 24.0)  # y, z of the front-high lane (O5, O6): 2.45 behind the plug tails, 8.25 over the bundle top
ENTRY_Y = 229.5           # plug -> x turn (R8), in front of the bundle (bundle front face 235.75, gap 2.5)
EXIT_Y1 = HUB_Y - HUB_PLUG_L + 1.0   # 248: the tube ends 1 mm inside the hub plug boot
PWR_D = 3.0               # 2 x 18 AWG pair (red / black) shown as one D3 tube
PIG_D = 2.0               # XT30U-F pigtail: 2 x 18 AWG silicone shown as one D2 line
UP_D = 4.0                # hub upstream cable C25 (Coms NA977 USB 2.0, OD about 4 - estimate)

# ---- C25 Coms NA977 hub upstream cable (purchase list v4, 10/1): USB-A plug angled UP -> straight USB-B, 250 mm incl. the connectors
# (product page "커넥터를 포함한 케이블 길이는 25cm"). Head sizes are photo-scaled estimates (the A shell 12 x 4.5 as the scale).
C25_LEN = 250.0
PI_USBA_LO_DZ = 4.0                    # lower USB-A port axis above the Pi PCB top (the upper one is the stack top - 4)
C25_A_SHELL = 12.0                     # A shell inside the receptacle (counted in the length, not modelled)
C25_A_HEAD = (13.0, 15.0, 9.0)         # A head outside the port face: along +x, width (y), thickness (z, centred on the port axis)
C25_A_BOSS = (8.0, 8.0)                # relief boss D x h on the head top
C25_A_RIBS = (6.5, 8.0)                # ribbed strain relief D x h above the boss -> cable leaves +z
C25_A_RX = 4.5                         # relief axis from the back (+x) face of the head
C25_B_PORT = (319.0, 28.5)             # (y, z) of the hub upstream USB-B port on the hub -x end face (estimate; photo: same end face as DC)
C25_B_SHELL = 10.0                     # B shell inside the receptacle (counted in the length)
C25_B_BODY = (20.0, 16.0, 13.0)        # straight B overmold outside the port: along -x, y, z
C25_B_BOOT = (10.0, 7.0)               # boot length, D
C25_LOOP_Z = 56.5                      # flat slack loop over the hub shelf (tube z54.5..58.5: 1.1 under the screen leads TS-C-PWR z59.6)
C25_OUT_Y = 303.0                      # loop out-leg y (the return leg runs at the B port y)
C25_R = {"rise": 7.0, "skew": 10.0, "u": 8.0, "drop": 6.0}
# ---- hub 5 V DC jack: same -x end face as the upstream B port (W1 10/1, product photo), in front of it
HUB_DC_YZ = (293.0, 28.5)
HUB_DC = (674.5, 686.5, 287.0, 299.0, 23.5, 33.5)        # right-angle DC plug head 12 x 12 x 10 on the hub -x end face, lead leaves +z
HUB_DC_STRAIGHT = (10.0, 5.0, 3.0)     # straight-plug what-if: body D, lead bend R behind it, lead D (check_electronics.py reports the max length)
HUB_DC_STRAIGHT_MAX = 32.0             # longest straight plug (jack face -> end of moulding / boot) that clears the IH190 gender by 0.5 (checked)
TOUCH = 0.05              # tube ends stop 0.05 short of the face they plug into (touch, no overlap)

LENGTHS = {}


# ------------------------------------------------------------------ small geometry helpers

def bx(b, dx=0.0, dy=0.0, dz=0.0):
    """spec box {x:[..], y:[..], z:[..]} -> solid (optionally shifted)."""
    return box(b["x"][0] + dx, b["x"][1] + dx, b["y"][0] + dy, b["y"][1] + dy, b["z"][0] + dz, b["z"][1] + dz)


def ccbox(cid):
    x0, x1, y0, y1, z0, z1 = CC[cid]
    return box(x0, x1, y0, y1, z0, z1)


def shown(items):
    return [i for i in items if i.get("show", True) is not False]


def tube(points, d, seg=16):
    """cable: hull of spheres along a polyline (rounded joints and ends)."""
    r = d / 2.0
    balls = [Manifold.sphere(r, seg).translate(tuple(float(v) for v in p)) for p in points]
    segs = [Manifold.batch_hull([balls[i], balls[i + 1]]) for i in range(len(balls) - 1)]
    return union(segs)


def fillet3(points, r):
    """3D polyline with every interior corner replaced by a circular arc of radius r (number, or one value per point). A corner
    may use a whole end segment but only half of a segment it shares with the next corner, so arcs never overlap."""
    P = [np.array(p, dtype=float) for p in points]
    m = len(P)
    rs = list(r) if isinstance(r, (list, tuple)) else [float(r)] * m
    seg = [float(np.linalg.norm(P[i + 1] - P[i])) for i in range(m - 1)]
    out = [tuple(P[0])]
    for i in range(1, m - 1):
        l1, l2 = seg[i - 1], seg[i]
        if l1 < 1e-9 or l2 < 1e-9 or rs[i] <= 0:
            out.append(tuple(P[i]))
            continue
        d1 = (P[i] - P[i - 1]) / l1
        d2 = (P[i + 1] - P[i]) / l2
        th = math.acos(max(-1.0, min(1.0, float(d1 @ d2))))
        if th < 1e-4:
            out.append(tuple(P[i]))
            continue
        avail1 = l1 if i == 1 else l1 / 2.0
        avail2 = l2 if i == m - 2 else l2 / 2.0
        t = min(rs[i] * math.tan(th / 2.0), avail1, avail2)
        R = t / math.tan(th / 2.0)
        T1 = P[i] - d1 * t
        nrm = d2 - d1 * math.cos(th)
        nrm = nrm / np.linalg.norm(nrm)
        c = T1 + nrm * R
        n = max(3, int(math.ceil(th / (math.pi / 2.0) * 8)))
        for k in range(n + 1):
            ph = th * k / n
            out.append(tuple(c + R * (-nrm * math.cos(ph) + d1 * math.sin(ph))))
    out.append(tuple(P[-1]))
    return out


def path_len(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def notched_envelope(x0, x1, y0, y1, z0, z1, c):
    """parts envelope of a bought module with its 4 corner squares (c x c) left free for the screws."""
    return diff(box(x0, x1, y0, y1, z0, z1),
                [box(x0 - 1, x0 + c, y0 - 1, y0 + c, z0 - 1, z1 + 1), box(x1 - c, x1 + 1, y0 - 1, y0 + c, z0 - 1, z1 + 1),
                 box(x0 - 1, x0 + c, y1 - c, y1 + 1, z0 - 1, z1 + 1), box(x1 - c, x1 + 1, y1 - c, y1 + 1, z0 - 1, z1 + 1)])


def board(x0, x1, y0, y1, z0, z1, holes):
    """plain board with round holes [(x, y, d)]."""
    return diff(box(x0, x1, y0, y1, z0, z1), [cyl_z(x, y, z0 - 0.01, z1 + 0.01, d) for (x, y, d) in holes])


def stadium_pts(cx, cy, w, h, ang_deg):
    """slot outline (length w along the direction ang, width h) in a plane."""
    r = h / 2.0
    L = (w - h) / 2.0
    a = math.radians(ang_deg)
    ux, uy = math.cos(a), math.sin(a)
    pts = []
    for end in (1, -1):
        ex, ey = cx + ux * L * end, cy + uy * L * end
        base = math.atan2(uy, ux) - math.pi / 2 if end == 1 else math.atan2(uy, ux) + math.pi / 2
        for i in range(17):
            t = base + math.pi * i / 16
            pts.append((ex + r * math.cos(t), ey + r * math.sin(t)))
    return pts


PJ313_SRC = ("spec/keyaction_features_frame.json cheeks.headphone_jack.jack_dims (SHOU HAN PJ-313 5JCJ, LCSC C668607: "
             "body 6.0 W × 11.5 L × 5.0 H, nose Ø5.0 × 2.5, axis 2.5 above the base) - one envelope for J701 / J501 / J702")


def pj313(d, cx, axis_z, face_y, nose_dir):
    """PJ-313 3.5 mm jack, one envelope for every PJ-313 in the instrument (d = jack_dims of the frame spec).
    face_y = plane of the body front face (where the nose starts); nose_dir = -1: nose toward -y, body behind it (+y);
    +1: nose toward +y, body in front of it (-y). Base = axis_z - axis_above_base; pins below the base are omitted."""
    base = axis_z - d["axis_above_base"]
    W, L, H, nl = d["body_W"], d["body_L"], d["body_H"], d["nose_L"]
    if nose_dir < 0:
        body = box(cx - W / 2, cx + W / 2, face_y, face_y + L, base, base + H)
        nose = cyl_y(cx, axis_z, face_y - nl, face_y, d["nose_d"])
    else:
        body = box(cx - W / 2, cx + W / 2, face_y - L, face_y, base, base + H)
        nose = cyl_y(cx, axis_z, face_y, face_y + nl, d["nose_d"])
    return union([body, nose])


class Out(list):
    def add(self, id, name_ko, name_en, group, solid, color, source, note="", kind="electronics", material=""):
        self.append(Part(id=id, name_ko=name_ko, name_en=name_en, kind=kind, group=group, solid=solid,
                         color=color, material=material, source=source, note=note))


# ------------------------------------------------------------------ board helpers (module / end-part boards)

def board_with_cuts(item, dx=0.0):
    """union of the item's boxes minus its cut cylinders / u_slot_cut boxes (module / end-part boards)."""
    solid = union([bx(b, dx) for b in item["boxes"]])
    b0 = min(b["z"][0] for b in item["boxes"]) - 0.01
    b1 = max(b["z"][1] for b in item["boxes"]) + 0.01
    cuts = [cyl_z(c["center"][0] + dx, c["center"][1], b0, b1, c["d"])
            for c in item.get("cylinders", []) if c.get("cut") and c["axis"] == "z"]
    cuts += [box(b["x"][0] + dx - 0.01, b["x"][1] + dx, b["y"][0], b["y"][1], b0, b1)
             for b in item.get("u_slot_cut", []) if b.get("cut")]
    return diff(solid, cuts)


# ------------------------------------------------------------------ module USB cable plan (bundle in the duct -> hub)

def module_plug_x(k):
    return X_O1 + MODULE_W * (k - 1) + 84.0


def hub_plug(xh):
    """USB-A overmold 16 x 8 x 18 against the hub port face + strain-relief boot D7 x 17 (plug + boot 35, spec Z-HUB-PLUGS)."""
    return union([box(xh - 8.0, xh + 8.0, HUB_Y - 18.0, HUB_Y, HUB_Z - 4.0, HUB_Z + 4.0),
                  cyl_y(xh, HUB_Z, HUB_Y - HUB_PLUG_L, HUB_Y - 17.99, 7.0)])


def cable_path(tag):
    """(corner points, fillet radii, kind) of the module USB cable tag (plug tail -> hub plug boot)."""
    k = int(tag[1])
    xm = module_plug_x(k)
    xp = HUB_PORT_X[HUB_PORT[tag]]
    s = 1.0 if xp > xm else -1.0
    if tag in LEVEL_Z:                                   # bundle y237.5: enter from the front, leave upward on top
        z = LEVEL_Z[tag]
        pts = [(xm, PLUG_Y1 - 0.5, PLUG_Z), (xm, ENTRY_Y, PLUG_Z), (xm + 20 * s, ENTRY_Y, PLUG_Z), (xm + 40 * s, ENTRY_Y, z),
               (xm + 52 * s, BUNDLE_Y, z), (xp, BUNDLE_Y, z), (xp, BUNDLE_Y, HUB_Z), (xp, EXIT_Y1, HUB_Z)]
        rad = [0, 8.0, 10.0, 10.0, 10.0, 10.0, 9.5, 0]
        kind = "bundle"
    else:                                                # front-high lane y226 z24 (short runs O5 / O6)
        fy, fz = FRONT_LANE
        pts = [(xm, PLUG_Y1 - 0.5, PLUG_Z), (xm, fy, PLUG_Z), (xm + 10 * s, fy, fz), (xp, fy, fz), (xp, fy + 10.0, HUB_Z),
               (xp, EXIT_Y1, HUB_Z)]
        rad = [0, 4.5, 8.0, 8.0, 8.0, 0]
        kind = "front"
    return pts, rad, kind


def cable_plan():
    """module USB cables: filleted centre lines + lengths (plug 25 + path + hub plug 35)."""
    plan = {"_len": {}, "_path": {}, "_xhub": {}, "_kind": {}}
    for k in range(1, 8):
        t = "O%d" % k
        pts, rad, kind = cable_path(t)
        fp = fillet3(pts, rad)
        plan[t] = fp
        plan["_path"][t] = path_len(fp)
        plan["_len"][t] = MODULE_PLUG_L + path_len(fp) - 0.5 - 1.0 + HUB_PLUG_L     # the tube starts 0.5 in the plug, ends 1 in the boot
        plan["_xhub"][t] = HUB_PORT_X[HUB_PORT[t]]
        plan["_kind"][t] = kind
    return plan


# ------------------------------------------------------------------ module + end-part electronics (unchanged from v3 / L1)

def ext_floor_path(tag, X0):
    """EXT lead from the module rear-wall opening (local x82..91, z5..10.7 at y212) down to the duct floor and along it to the
    module-side end face of the XH pair (O1 -> -x to X402 at x69.4, O7 -> +x to X412 at x1160)."""
    x = X0 + 86.5
    r = 1.5
    if tag == "O1":
        return [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, r), (x - 8.0, 226.0, r), (XH_L[1] + r, XH_Y, r)]
    return [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, r), (x + 8.0, 226.0, r), (XH_R[0] - r, XH_Y, r)]


def lead_floor_path(tag):
    """EL / ER flat lead from the end-part rear-wall notch (z5..5.89 at y212) down to the duct floor and to the end-part side
    of the XH pair (EL -> x52, ER -> x1177.4)."""
    r = 1.0
    if tag == "EL":
        x = (14.825 + 21.175) / 2.0
        return [(x, 212.0, 6.0), (x, 213.0, 6.0), (x, 216.0, r), (x + 6.0, 226.0, r), (XH_L[0] - r, XH_Y, r)]
    x = X_RIGHT + (8.885 + 12.695) / 2.0
    return [(x, 212.0, 6.0), (x, 213.0, 6.0), (x, 216.0, r), (x - 6.0, 226.0, r), (XH_R[1] + r, XH_Y, r)]


XH_L = (52.0, 69.4)       # electronics_modules xh_left  x (y222..240, z0..6)
XH_R = (1160.0, 1177.4)   # electronics_modules xh_right x
XH_Y = 231.0              # middle of the XH housing (y222..240)


def module_parts(M, out, plan):
    it = {i["id"]: i for i in M["module_items"]}
    for k in range(1, 8):
        X0 = X_O1 + MODULE_W * (k - 1)
        g = "O%d 전자부" % k
        tag = "O%d" % k

        mb = it["mb_board"]
        out.add("%s-E-MB" % tag, "제어 기판 MB (5×7 양면 만능기판, 70×50×1.6) %s" % tag,
                "control board MB (perfboard 70x50x1.6) " + tag, g, board_with_cuts(mb, X0), COLORS["pcb_perf"],
                SRC_M + " mb_board; " + mb["source"], material="FR4 만능기판")

        sb = it["sb_board"]
        out.add("%s-E-SB" % tag, "센서 기판 SB (6행 양면 도트 띠 161.6 × 15.24 × 1.6) %s" % tag,
                "sensor board SB " + tag, g, board_with_cuts(sb, X0), COLORS["pcb_perf"],
                SRC_M + " sb_board; " + sb["source"],
                note="추정: U홈이 왼쪽 끝으로 열림 (spec assumed: " + sb["assumed_note"] + ")", material="FR4 만능기판")

        z = it["zero"]
        out.add("%s-E-ZERO" % tag, "RP2040-Zero (A301), 핀 헤더로 세움 %s" % tag, "RP2040-Zero (A301) " + tag, g,
                union([bx(b, X0) for b in z["boxes"]]), COLORS["pcb_blue"], SRC_M + " zero; " + z["source"],
                note="추정: 윗면 부품 덩어리 x75.64~92.64 y172.5~189.5 z≤16.3과 밑면 칩 덩어리 z10.6~11.9 (spec assumed 분할); "
                     "핀 헤더 1×9 ×2는 작은 부품이라 뺌")

        mx = it["mux"]
        mxb = [b for b in mx["boxes"] if "SSOP" not in b["label"]]
        out.add("%s-E-MUX" % tag, "CD74HC4067 16채널 먹스 모듈 (A302), 핀 헤더로 세움 %s" % tag,
                "CD74HC4067 mux module (A302) " + tag, g, union([bx(b, X0) for b in mxb]), COLORS["pcb_green"],
                SRC_M + " mux; " + mx["source"],
                note="추정: 헤더 몰드 2.5 높이 (spec assumed: " + mx["assumed_note"] + ")")

        rb = it["ribbon"]
        out.add("%s-C-RIBBON" % tag, "16심 리본 W10%d (SB J201 → MB J301)" % k, "16-core ribbon W10%d" % k, G_CAB,
                union([bx(b, X0) for b in rb["boxes"]]), COLORS["cable"], SRC_M + " ribbon; " + rb["source"],
                note="남는 길이(자른 길이 180 − 경로 85)는 접어 둠, 모델에 없음 (spec note)")

        if tag in it["ext_lead"]["modules"]:
            el = it["ext_lead"]
            wid = {"O1": "W403", "O7": "W413"}[tag]
            out.add("%s-C-EXT" % tag, "EXT 연장선 %s (L66 모듈 쪽 150 mm, 6심 22 AWG)" % wid, "EXT lead %s" % wid, G_CAB,
                    diff(union([bx(b, X0) for b in el["boxes"]] + [tube(ext_floor_path(tag, X0), 3.0)]),
                         [bx(b, X0) for b in mb["boxes"]]), COLORS["cable"],
                    SRC_M + " ext_lead + xh_left/xh_right (mated XH on the duct floor); " + el["source"] + "; " + SRC
                    + " cable_duct.other_leads (O1/O7 EXT leads 그대로 통로 바닥)",
                    note="추정: 묶음 단면 약 8×2와 띠 안의 x 위치 (spec assumed; spec 상자 y195.4~가 MB 끝 y195.5와 0.1 겹쳐 MB 자리를 뺌); "
                         "뒷벽 구멍(y212)부터 XH 짝까지는 지름 3 선으로 L2 통로(y212~241, 스피커 밑) 바닥(z0~3)에 눕힘 - 경로는 보기용")

        # USB-C plug + cable to the hub (one part: plug overmold + cable + hub-end USB-A plug)
        up = it["usb_plug"]
        plug = bx(up["boxes"][0], X0)
        port = HUB_PORT[tag]
        xh = HUB_PORT_X[port]
        ln = plan["_len"][tag]
        cs = CABLE_SPEC[tag]
        std = cs["std_m"] * 1000.0
        if plan["_kind"][tag] == "bundle":
            dev = ("사양과 다름(작은 고침): 사양 선 '플러그 → R15 → y236.8·z13 줄 → 포트 x에서 올라감'은 나란히 달리는 선이 모두 한 자리에 겹침 → "
                   "묶음 y%.1f 4층(z2.25·6.25·10.25·14.25, 0.5 틈), 굽힘은 통로 깊이 때문에 플러그 뒤 R8, 허브 쪽 R9.5 이하; " % BUNDLE_Y)
            how = ("플러그 뒤 y%.1f에서 R8로 꺾여 묶음 앞(y%.1f)을 x로 달리며 z%.1f → z%.2f로 옮긴 뒤 묶음 y%.1f의 %s층 z%.2f로 들어가 "
                   "허브 포트 x%.1f에서 위로 서고 R9.5로 +y (묶음 맨 위라 다른 선을 넘지 않음)"
                   % (PLUG_Y1, ENTRY_Y, PLUG_Z, LEVEL_Z[tag], BUNDLE_Y, {2.25: "1", 6.25: "2", 10.25: "3", 14.25: "4"}[LEVEL_Z[tag]],
                      LEVEL_Z[tag], xh))
        else:
            dev = ("사양과 다름(작은 고침): 사양 선 'y236.8·z13 줄'이 아니라 묶음 위 앞쪽 줄 - 묶음에 넣으면 포트에서 위로 빠질 때 O5가 O2·O4 "
                   "밑이어야 해서 5층이 필요한데 5층째(z18.25)는 J702·동글 3.5 mm 플러그 자리(z17~) 밑에 들어가지 않음; 짧은 선 O5·O6만 따로; ")
            how = ("짧은 선이라 묶음 위 앞쪽 줄 y%.0f z%.0f를 달려(묶음 윗면 z16 위 8) 포트 x%.1f에서 묶음을 넘어 +y" % (FRONT_LANE + (xh,)))
        out.add("%s-C-USB" % tag, "USB-C 케이블 W20%d (Coms NA993 계열 %.1f m, %s → 허브 포트 %d)" % (k, cs["std_m"], tag, port),
                "USB cable W20%d %s to hub port %d" % (k, tag, port), G_CAB, union([plug, tube(plan[tag], CABLE_OD), hub_plug(xh)]),
                COLORS["cable"],
                SRC_M + " usb_plug (y196.8~221.8, 축 z14.5); " + SRC + " cable_duct (통로 y212~241 z0~27, hub ports_x / port_z 28.5 / "
                "port_map, cables %s: path %d mm, %.1f m) + centre_contents Z-HUB-PLUGS (USB-A 플러그+부트 35, y247~282) / Z-HUB-DROPS"
                % (cs["cable"], cs["path_mm"], cs["std_m"]),
                note=dev + "추정: 케이블 OD 3.5; %s; 길이 = 플러그 %.0f + 경로 %.1f + 허브 플러그 %.0f = %.1f mm (사양 %d, 표준 %.1f m, 여유 %.0f ≥ 40) "
                     "- 선은 통로·앞 공간 안에서만 (배기 홈·건반 뒤 2 mm 틈으로 조금 보임), 경로는 보기용 (묶을 때는 끈·벨크로 - 지붕 밑 케이블 "
                     "집게에는 끼우지 않음)"
                     % (how, MODULE_PLUG_L, ln - MODULE_PLUG_L - HUB_PLUG_L, HUB_PLUG_L, ln, cs["path_mm"], cs["std_m"], std - ln))


def end_parts(M, out):
    it = {i["id"]: i for i in M["end_items"]}
    for iid, side, dx, tag in (("el_board", "왼쪽", 0.0, "EL"), ("er_board", "오른쪽", X_RIGHT, "ER")):
        b = it[iid]
        out.add("%s-E-BOARD" % tag, b["name_ko"], b["name_en"], "끝 부속 %s 전자부" % side, board_with_cuts(b, dx),
                COLORS["pcb_perf"], SRC_M + " " + iid + "; " + b["source"],
                note="추정: U홈 Ø3.4가 왼쪽 끝으로 열림 (spec assumed)", material="FR4 만능기판")
    for iid, dx, tag in (("el_lead", 0.0, "EL"), ("er_lead", X_RIGHT, "ER")):
        b = it[iid]
        out.add("%s-C-LEAD" % tag, b["name_ko"], b["name_en"], G_CAB,
                union([bx(q, dx) for q in shown(b["boxes"])] + [tube(lead_floor_path(tag), 2.0)]),
                COLORS["cable"], SRC_M + " " + iid + " + xh_left/xh_right lead drop (y212..231, duct floor); " + b["source"]
                + "; " + SRC + " cable_duct.other_leads (EL/ER 리드 + XH 그대로, 스피커 밑 통로 안)",
                note="추정: 뒷벽 노치(y212)에서 통로 바닥으로 내려 XH 짝 끝면까지 지름 2 선으로 표시 (실제는 폭 %s 리본 띠) - 경로는 보기용"
                     % ("6.35" if tag == "EL" else "3.81"))
    for iid, tag in (("xh_left", "L"), ("xh_right", "R")):
        b = it[iid]
        out.add("C-XH-%s" % tag, b["name_ko"], b["name_en"], G_CAB, union([bx(q) for q in shown(b["boxes"])]),
                "#f2f2ee", SRC_M + " " + iid + "; " + b["source"] + "; L2: 스피커 밑 통로 y212~241 안 (그대로)",
                note="추정: 느슨한 커넥터 - 위치·높이·길이 (spec assumed: " + b["assumed_note"][:120] + ")")


# ------------------------------------------------------------------ centre unit: Pi 5, dongle, boards (spec centre_contents boxes)

def pi_parts(out):
    x0, x1, y0, y1, zb0, ztop = CC["CU-E-PI5"]
    zb1 = zb0 + 1.6
    holes = [(x0 + 3.5, y0 + 3.5, 2.7), (x0 + 61.5, y0 + 3.5, 2.7), (x0 + 3.5, y1 - 3.5, 2.7), (x0 + 61.5, y1 - 3.5, 2.7)]
    pcb = board(x0, x1, y0, y1, zb0, zb1, holes)
    hdr = box(x0 + 32.5 - 25.4, x0 + 32.5 + 25.4, y1 - 3.5 - 2.54, y1 - 3.5 + 2.54, zb1, zb1 + 8.5)
    hs = box(x0 + 21.5, x0 + 36.5, y0 + 17.5, y0 + 32.5, zb1, zb1 + 8.0)
    hd = TS.PI5["hdmi"]                                         # micro-HDMI x2 (estimated, W1 rev 3: x562~585 y262~269.5 top z27.3)
    hdmi = [box(xc - PI_HDMI_W / 2, xc + PI_HDMI_W / 2, hd["y"][0], hd["y"][1], zb1 - 0.01, hd["top_z"]) for xc in PI_HDMI_XC]
    out.add("CU-E-PI5", "라즈베리파이 5 2GB", "Raspberry Pi 5 2GB", G_CU, union([pcb, hdr, hs] + hdmi), PI5_GREEN,
            SRC + " centre_contents CU-E-PI5 (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 6 mm 받침 위, USB/RJ45 끝 +x, GPIO 가장자리 +y); "
            % (x0, x1, y0, y1, zb0, ztop) + SRC_R + " pi5 (L01)",
            note="추정: GPIO 헤더 2×20 (가장자리 3.5, 비포트 쪽 끝에서 32.5 중심, 윗면 z%.1f)과 SoC 방열판 15×15×8 위치; 구멍 Ø2.7 4개 "
                 "58×49 (보드 모서리에서 3.5 - body.py 받침 기둥 CU-POST-PI 자리); micro-HDMI 2개 (-y 가장자리, 중심 x%.1f · %.1f, 폭 %.1f, "
                 "y%.1f~%.1f, 윗면 z%.1f - Pi 5 도면 26 · 39.5 mm, W1 3판 추정 상자 x562~585 안; 화면 리본이 안 쓰는 HDMI 위에 얹힘); USB-C 전원은 작아서 뺌"
                 % (zb1 + 8.5, PI_HDMI_XC[0], PI_HDMI_XC[1], PI_HDMI_W, TS.PI5["hdmi"]["y"][0], TS.PI5["hdmi"]["y"][1], TS.PI5["hdmi"]["top_z"]))
    face = x1 + PI_PORT_OVERHANG
    ports = {}
    for key, name_ko, name_en, yc_off, w, depth, h in PI_PORTS:
        yc = y0 + yc_off
        ports[key] = yc
        out.add("CU-E-PI5-" + key, name_ko, name_en, G_CU, box(face - depth, face, yc - w / 2, yc + w / 2, zb1, zb1 + h), COLORS["metal"],
                SRC + " centre_contents CU-E-PI5-%s; " % key + SRC_R + " pi5 box 'USB-A x2 stacks + RJ45 block' (tallest 16.5 above the PCB, "
                "overhang 2.5)",
                note="추정: Pi 5 포트 가장자리 순서(전원·HDMI 가장자리 쪽부터 RJ45, USB-A 2단, USB-A 2단)와 중심(전원 가장자리에서 "
                     "RJ45 10.25 · USB-A 29 · 47, Pi 3B+ 도면 값 - Pi 5 도면으로 확인), 크기 RJ45 16×21.25×13.5, USB-A 2단 14.5×17.5×16.4, "
                     "보드 끝에서 2.5 튀어나옴(x%.1f); 이 포트 중심 y%.2f" % (face, yc))
    d = CC["CU-E-PI5-DISP1"]
    out.add("CU-E-PI5-DISP1", "라즈베리파이 5 CAM/DISP 1 커넥터 (22핀 0.5 mm)", "Raspberry Pi 5 CAM/DISP 1 connector", G_CU,
            ccbox("CU-E-PI5-DISP1"), BLACK_PLASTIC,
            SRC + " centre_contents CU-E-PI5-DISP1 (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, DSI 리본이 화면 뚜껑으로 곧게 올라감 - Z-DSI)" % d,
            note="추정: 둘 중 -x 쪽 커넥터를 CAM/DISP 1로 표시(보드 글씨로 확인), 높이 4.0; 화면 DSI 리본(TS-C-DSI)이 입구 x589(−x 쪽)로 2.7 꽂힘, "
                 "리본은 Z-DSI x582~600 y262~280 z28.1~61.35 안의 기둥 x583으로 내려옴")
    return {"face": face, "y_s1": ports["USBA1"], "y_s2": ports["USBA2"], "zb1": zb1, "z_lo": zb1 + PI_USBA_LO_DZ, "z_up": zb1 + 16.4 - 4.0}


DONGLE_SOCK = (650.0, 21.75, 262.1, 25.0, 10.5)     # socket axis x, z (lying on the floor), front end y, length, D


def dongle_parts(out, pi):
    face, ys = pi["face"], pi["y_s1"]
    g = CC["CU-E-GENDER"]
    out.add("CU-E-GENDER", "IH190 USB-C(F)→USB-A(M) ㄱ자 젠더 (L52)", "Coms IH190 left-angle gender (L52)", G_CU, ccbox("CU-E-GENDER"),
            BLACK_PLASTIC, SRC + " centre_contents CU-E-GENDER (x%.1f~%.1f y%.0f~%.0f z%.1f~%.1f, USB-A 2단 1의 아래 포트); " % g
            + SRC_R + " usb_dongle (gender 18×16×6.5)",
            note="추정: RJ45 옆 USB-A 2단(중심 y%.0f)의 아래 포트에 꽂음 (A 플러그 면 x%.1f = 포트 면); C 소켓이 -y를 향함" % (ys, face))
    gy0 = g[2]
    hz0, hz1 = 25.75, 31.75
    head = box(632.0, 640.5, gy0 - 17.5, gy0 + 6.5, hz0, hz1)                         # 17.5 outside + 6.5 plug in the gender
    sx, sz, sy0, sl, sd = DONGLE_SOCK
    sock = cyl_y(sx, sz, sy0, sy0 + sl, sd)
    hx = (632.0 + 640.5) / 2.0
    zf = Z_BOT + 1.5 + 0.05
    loop = tube(fillet3([(hx, gy0 - 17.0, (hz0 + hz1) / 2.0), (hx, 263.6, 27.0), (hx, 263.6, zf), (hx, 300.0, zf), (sx, 300.0, zf),
                         (sx, 300.0, sz), (sx, sy0 + sl + 0.5, sz)], [0, 1.5, 1.4, 5.0, 5.0, 5.0, 0]), 3.0)
    d = CC["CU-E-DONGLE"]
    out.add("CU-E-DONGLE", "Apple USB-C → 3.5 mm 어댑터 (L51)", "Apple USB-C to 3.5 mm adapter (L51)", G_CU, union([head, sock, loop]),
            WHITE_PLASTIC,
            SRC + " centre_contents CU-E-DONGLE (x%.1f~%.1f y%.1f~%.0f z%.1f~%.1f, 바닥에 눕힘, 소켓 -y) + Z-DONGLE-PLUG (W701 3.5 mm 플러그 "
            "x644~656 y222~262.1); " % d + SRC_R + " usb_dongle (head 8.5×6×24 incl. plug, jack head ~Ø10.5×25, cable ~7 cm)",
            note="추정: 머리 8.5 × 6 × 24 (6.5는 젠더 C 소켓 안)가 젠더에서 -y로, 약 7 cm 선이 바닥(z16.5)으로 내려가 젠더·머리 밑을 +y로 지나 "
                 "x%.0f에서 -y로 돌아 3.5 mm 소켓 머리(Ø%.1f × %.0f, 축 x%.0f z%.2f, 앞 끝 y%.1f - 바닥에 닿음)의 +y 끝에 들어감; "
                 "W701은 소켓 -y 끝에 꽂힘 (모델에 없음, Z-DONGLE-PLUG 비움)" % (sx, sd, sl, sx, sz, sy0))


def board_parts(M, F, out):
    d = F["cheeks"]["headphone_jack"]["jack_dims"]
    # ---- XH-A232 amp on the shelf pads
    x0, x1, y0, y1, z0, z1 = CC["CU-E-AMP"]
    amp_b = board(x0, x1, y0, y1, z0, z0 + 1.6, [(x, y, 3.2) for (x, y) in BODY.AMP_HOLES])
    amp_e = notched_envelope(x0, x1, y0, y1, z0 + 1.6, z1, 7.0)
    out.add("CU-E-AMP", "XH-A232 (HW-404) TPA3110 2×15 W 앰프 보드", "XH-A232 (HW-404) TPA3110D2 amplifier board", G_CU,
            union([amp_b, amp_e]), COLORS["pcb_blue"],
            SRC + " centre_contents CU-E-AMP (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 선반 위 2 mm 받침); " % CC["CU-E-AMP"] + SRC_R + " amp_xh_a232 (L53)",
            note="추정: 부품은 모서리 7×7(나사 자리)을 뺀 한 덩어리 z%.1f~%.1f; 구멍 Ø3.2는 body.py 선반의 앰프 받침 자리 (%s) - 받은 보드로 확인; "
                 "전원 단자·스피커 L 단자는 -x 끝(y313 / y318), 스피커 R 단자는 +x 끝(y293)으로 가정"
                 % (z0 + 1.6, z1, " · ".join("%.1f,%.1f" % p for p in BODY.AMP_HOLES)))
    # ---- XL4016 buck
    x0, x1, y0, y1, z0, z1 = CC["CU-E-BUCK"]
    bh = [(x0 + 3.2, y0 + 3.2, 3.2), (x1 - 3.2, y0 + 3.2, 3.2), (x0 + 3.2, y1 - 3.2, 3.2), (x1 - 3.2, y1 - 3.2, 3.2)]
    out.add("CU-E-BUCK", "XL4016 강압 모듈 XH-M401 (20 V → 5.1 V)", "XL4016 buck module XH-M401", G_CU,
            union([board(x0, x1, y0, y1, z0, z0 + 1.6, bh), notched_envelope(x0, x1, y0, y1, z0 + 1.6, z1, 6.5)]), COLORS["pcb_blue"],
            SRC + " centre_contents CU-E-BUCK (x%.1f~%.1f y%.1f~%.0f z%.1f~%.1f, 5 mm 받침, 루버 앞); " % CC["CU-E-BUCK"] + SRC_R
            + " buck_xl4016 (60.8×40.3×29, L58)",
            note="추정: 방열판 2·코일·캐패시터를 모서리 6.5×6.5를 뺀 한 덩어리(z%.1f~%.1f)로 표시, 구멍 Ø3.2 모서리에서 3.2 (body.py "
                 "CU-POST-BUCK 자리); 입력 단자 -x 끝(x%.1f y306), 출력 단자 앞면(-y, x529.5) 가정" % (z0 + 1.6, z1, x0))
    # ---- PED pedal board
    x0, x1, y0, y1, z0, z1 = CC["CU-E-PEDBOARD"]
    ph = [(x0 + 4, y0 + 4, 3.2), (x1 - 4, y1 - 4, 3.2), (x1 - 4, y0 + 4, 3.0), (x0 + 4, y1 - 4, 3.0)]
    out.add("CU-E-PEDBOARD", "PED 페달 보드 (5×7 cm 만능기판 70×50)", "PED pedal board PB (5x7 perfboard)", G_CU, board(x0, x1, y0, y1, z0, z1, ph),
            COLORS["pcb_perf"], SRC + " centre_contents CU-E-PEDBOARD (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 5 mm 받침); " % CC["CU-E-PEDBOARD"]
            + SRC_R + " ped_board",
            note="추정: 나사 구멍 Ø3.2 (x%.0f y%.0f · x%.0f y%.0f), 위치 핀 구멍 Ø3.0 (x%.0f y%.0f · x%.0f y%.0f) - body.py CU-POST-PED 자리"
                 % (ph[0][0], ph[0][1], ph[1][0], ph[1][1], ph[2][0], ph[2][1], ph[3][0], ph[3][1]), material="FR4 만능기판")
    # ---- PED Zero: the module MB Zero layout turned 180 deg (USB -y), lowered onto the PED board top
    z = {i["id"]: i for i in M["module_items"]}["zero"]
    zx0, zx1, zy0, zy1, zz0, zz1 = CC["CU-E-PEDZERO"]
    lx1 = max(b["x"][1] for b in z["boxes"])
    ly1 = max(b["y"][1] for b in z["boxes"])
    lz0 = min(b["z"][0] for b in z["boxes"])
    # 180 deg about z: world x = zx0 + (lx1 - local x), world y = zy0 + (ly1 - local y); z lowered onto the board top
    ped_rot = (lambda b: box(zx0 + (lx1 - b["x"][1]), zx0 + (lx1 - b["x"][0]), zy0 + (ly1 - b["y"][1]), zy0 + (ly1 - b["y"][0]),
                             b["z"][0] - lz0 + zz0, b["z"][1] - lz0 + zz0))
    out.add("CU-E-PEDZERO", "RP2040-Zero (PED 보드, 페달용)", "RP2040-Zero on the PED board", G_CU, union([ped_rot(b) for b in z["boxes"]]),
            COLORS["pcb_blue"], SRC + " centre_contents CU-E-PEDZERO (x%.0f~%.0f y%.0f~%.1f z%.1f~%.1f, USB-C -y); " % CC["CU-E-PEDZERO"] + SRC_M
            + " zero (same part / stack as the MB)",
            note="추정: MB의 Zero 배치(핀 헤더 1.3 틈)를 180° 돌려 PED 보드 위에 (USB-C 리셉터클 -y, 중심 x%.2f z%.1f)" %
                 (zx0 + (lx1 - 84.0), 14.5 - lz0 + zz0))
    ped_axis = (zx0 + (lx1 - 84.0), 14.5 - lz0 + zz0)
    # ---- J702 amp input jack board + PJ-313 facing -y
    x0, x1, y0, y1, z0, z1 = CC["CU-E-J702BOARD"]
    jh = [(x0 + 3.0, y0 + 3.0, 3.2), (x1 - 3.0, y1 - 3.0, 3.2)]
    out.add("CU-E-J702BOARD", "앰프 입력 잭 기판 (만능기판 조각 30×25, J702 + 80 Hz RC)", "amp input jack board J702 (perfboard scrap)", G_CU,
            board(x0, x1, y0, y1, z0, z1, jh), COLORS["pcb_perf"],
            SRC + " centre_contents CU-E-J702BOARD (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 5 mm 받침)" % CC["CU-E-J702BOARD"],
            note="추정: 구멍 Ø3.2 두 곳 (body.py CU-POST-J702 자리); RC 부품은 작아서 뺌", material="FR4 만능기판")
    j = CC["CU-E-J702"]
    jx = (j[0] + j[1]) / 2.0
    jz = z1 + d["axis_above_base"]
    out.add("CU-E-J702", "앰프 입력 잭 PJ-313 (J702)", "amp input jack PJ-313 (J702)", G_CU, pj313(d, jx, jz, j[2] + d["nose_L"], -1), BLACK_PLASTIC,
            SRC + " centre_contents CU-E-J702 (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 코 -y) + Z-J702-PLUG (W702 3.5 mm 플러그 y222~255); " % j + PJ313_SRC,
            note="추정: 몸체 y%.1f~%.0f, 코 Ø%.0f가 기판 앞끝 y%.0f까지, 축 z%.1f - W702 플러그는 모델에 없음 (Z-J702-PLUG 비움)"
                 % (j[2] + d["nose_L"], j[3], d["nose_d"], j[2], jz))
    # ---- fuse holder BU914 in its cradle
    f = CC["CU-E-FUSE"]
    fy, fz = (f[2] + f[3]) / 2.0, (f[4] + f[5]) / 2.0
    out.add("CU-E-FUSE", "BU914 인라인 퓨즈 홀더 + 5 A T 퓨즈", "Coms BU914 inline fuse holder + 5 A T fuse", G_CU,
            cyl_x(fy, fz, f[0], f[1], f[3] - f[2]), BLACK_PLASTIC,
            SRC + " centre_contents CU-E-FUSE (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 바닥에 집게로); " % f + SRC_R + " fuse_holder_bu914",
            note="추정: 지름 10 (body.py 받침 Ø%.1f에 눌러 끼움) - 받은 홀더로 확인; 양끝 선은 C-PWR-IN / C-PWR-FUSE" % BODY.FUSE_BORE)
    # ---- back plate I/O: J501 board + jack, KCD1, HUSB238
    x0, x1, y0, y1, z0, z1 = CC["CU-E-J501BOARD"]
    out.add("CU-E-J501BOARD", "페달 잭 기판 (만능기판 조각 25×24, J501)", "pedal jack J501 perfboard scrap", G_CU, box(x0, x1, y0, y1, z0, z1),
            COLORS["pcb_perf"], SRC + " centre_contents CU-E-J501BOARD (x%.0f~%.0f y%.1f~%.1f z%.1f~%.0f, 뒤판 출력물 선반 위)" % CC["CU-E-J501BOARD"],
            note=BACK_SHIFT_TXT + "추정: PR-BACKPLATE 잭 선반(윗면 z%.1f)에 MS 폴리머 (구멍 없이)" % z0, material="FR4 만능기판")
    j = CC["CU-E-J501"]
    jx = (j[0] + j[1]) / 2.0
    out.add("CU-E-J501", "페달 잭 PJ-313 (J501, 뒤판 출력물)", "pedal jack PJ-313 (J501) in the printed back plate", G_CU,
            pj313(d, jx, z1 + d["axis_above_base"], j[3] - d["nose_L"], +1), BLACK_PLASTIC,
            SRC + " centre_contents CU-E-J501 (x%.1f~%.1f y%.1f~%.1f z%.0f~%.0f) + centre.back_plate_io pedal_jack_J501_D6 (462.5, 40.5); " % j
            + PJ313_SRC,
            note=BACK_SHIFT_TXT + "추정: 기판 위(z%.0f), 축 z%.1f = 판 구멍 중심, 코 끝이 바깥면 y%.1f과 같은 면 - 받은 부품으로 확인" % (z1, z1 + d["axis_above_base"], j[3]))
    s = CC["CU-E-SWITCH"]
    kx, kz = L2["centre"]["back_plate_io"]["holes_xz"]["rocker_KCD1_13.2x19.2"]
    yb1 = BODY.YB
    ys = yb1 - 2.0                      # bezel in the 2 mm recess, flush with the outer face
    hb0 = ys - 13.0                     # housing 13 deep behind the bezel
    lb0 = hb0 - 8.0                     # quick-connect lugs 8 long
    sws = union([box(s[0], s[1], ys, yb1, s[4], s[5]), box(kx - 6.6, kx + 6.6, hb0, ys + 0.01, kz - 9.6, kz + 9.6)]
                + [box(kx - 2.4, kx + 2.4, lb0, hb0 + 0.01, zl - 0.4, zl + 0.4) for zl in (kz - 4.0, kz + 4.0)])
    out.add("CU-E-SWITCH", "KCD1-101A 로커 스위치 (뒤판 출력물)", "KCD1-101A rocker switch in the printed back plate", G_CU, sws, BLACK_PLASTIC,
            SRC + " centre_contents CU-E-SWITCH (x%.0f~%.0f y%.0f~%.1f z%.0f~%.0f, 2 mm 오목 자리에 테두리 → y%.1f와 같은 면) + "
            "back_plate_io rocker_KCD1 (438.5, 38.5); " % (tuple(s) + (yb1,)) + SRC_R + " power_switch_kcd1 (bezel 15×21×2, body 13.2×19.2 'depth ~13 + lugs 8')",
            note=BACK_SHIFT_TXT + "추정: 테두리 15×21×2 (y%.1f~%.1f, 오목 자리 안), 몸통 13.2×19.2×13 (y%.1f~%.1f, 판 구멍에 스냅), 4.8×0.8 단자 2개 8 길이 "
                 "(y%.1f~%.1f, z%.1f / %.1f) - 받은 스위치로 확인" % (ys, yb1, hb0, ys, lb0, hb0, kz - 4.0, kz + 4.0))
    SW_LUGS.update({"x": kx, "y_tip": lb0, "z_in": kz - 4.0, "z_out": kz + 4.0})
    p = CC["CU-E-PDTRIG"]
    cxu = (p[0] + p[1]) / 2.0
    pcb_ = box(p[0], p[1], p[2], p[3], p[4], p[4] + 1.2)
    rcpt = box(cxu - 4.47, cxu + 4.47, p[3] - 7.3, p[3], p[4] + 1.2, p[5])
    out.add("CU-E-PDTRIG", "HUSB238 PD 트리거 + USB-C 전원 입력 (L57, 뒤판 출력물 주머니)", "HUSB238 USB-C PD trigger (L57) in the back-plate pocket",
            G_CU, union([pcb_, rcpt]), COLORS["pcb_blue"],
            SRC + " centre_contents CU-E-PDTRIG (x%.0f~%.0f y%.1f~%.1f z%.1f~%.1f, 입구가 바깥면에서 2 안) + back_plate_io usb_c_pd_input (421, 38); "
            % p + SRC_R + " pd_trigger_husb238 (10×16.4×4.4)",
            note=BACK_SHIFT_TXT + "추정: 기판 1.2 + USB-C 리셉터클 8.94×7.3×3.2 (+y 끝, 입구 y%.1f); 출력 선은 -y 끝(y%.1f)에서 C-PWR-IN" % (p[3], p[2]))
    return ped_axis


SW_LUGS = {}


# ------------------------------------------------------------------ hub, power bank

def hub_bank_parts(R, out):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    h = rb["usb_hub_710u3"]["boxes"][0]
    assert abs((h["x"][1] - h["x"][0]) - (HUB_X1 - HUB_X0)) < 1e-6 and abs((h["y"][1] - h["y"][0]) - (HUB_BACK - HUB_Y)) < 1e-6
    out.add("PB-E-HUB", "NEXTU 710U3 10포트 유전원 USB 허브", "NEXTU 710U3 10-port powered USB hub", G_CU,
            box(HUB_X0, HUB_X1, HUB_Y, HUB_BACK, HUB_Z0, HUB_Z1), HUB_GREY,
            SRC_R + " usb_hub_710u3 (228×48×24); " + SRC + " centre_contents PB-E-HUB / cable_duct.hub (x%.1f~%.1f y%.0f~%.0f z%.1f~%.1f, "
            "바닥에 뒤판에 붙여, 포트 -y)" % (HUB_X0, HUB_X1, HUB_Y, HUB_BACK, HUB_Z0, HUB_Z1),
            note="사양과 다름(작은 고침): W1 10/1 제품 사진대로 업스트림 USB 3.0 B 포트와 5 V DC 잭이 같은 끝면 → 둘 다 -x 끝면(x%.1f, Pi·강압 쪽)에 둠 "
                 "(사양 cable_duct.hub: 업스트림 -x 끝면 ㄱ자 플러그 · DC +x 끝면 추정) - Pi 업스트림(C25)과 5.1 V 선이 가장 짧고, 허브는 그대로 "
                 "바닥에 뒤판에 붙여 모듈 선은 -y 면으로; 추정: 아래 포트 10개를 앞면(y%.0f, -y 쪽) x%.1f+22i, z%.1f에, B 포트 y%.0f z%.1f (뒤쪽), "
                 "DC 잭 y%.0f z%.1f (앞쪽) - 끝면 안 자리는 받은 허브로 확인; 포트 0·1(화면 뚜껑 아래)은 비움"
                 % (HUB_X0, HUB_Y, HUB_PORT_X[0], HUB_Z, C25_B_PORT[0], C25_B_PORT[1], HUB_DC_YZ[0], HUB_DC_YZ[1]))
    b = CC["PB-E-BANK"]
    pbx = rb["power_bank_mt65"]["boxes"][0]
    assert abs((b[1] - b[0]) - (pbx["x"][1] - pbx["x"][0])) < 1e-6 and abs((b[5] - b[4]) - (pbx["z"][1] - pbx["z"][0])) < 1e-6
    out.add("PB-E-BANK", "모루이 MT-65 보조배터리 (20000 mAh, 65 W)", "Morui MT-65 65 W 20000 mAh power bank (optional O07)", G_BANK,
            ccbox("PB-E-BANK"), BANK_GREY,
            SRC_R + " power_bank_mt65 (105×71×32); " + SRC + " centre_contents PB-E-BANK (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, USB-C 끝 +x, "
            "CU-PBHOLDER 안)" % b,
            note="추정: 받침 바닥(z18.5) 위, 둘레 0.5 틈; 선택품(O07) - ㄱ자 USB-C 선(Z-BANK-PLUG → 케이블 통과 → 뒤판 USB-C 입력)은 모델에 없음")


def c25_geom(pi):
    """C25 (Coms NA977) pieces: A head (up-angled, in the LOWER port of the GPIO-edge stack), B plug (straight, hub -x end face) and the
    cable centre line with the flat slack loop sized so the whole cable is C25_LEN (connectors included)."""
    face, ys, za = pi["face"], pi["y_s2"], pi["z_lo"]
    hx, hw, ht = C25_A_HEAD
    xr = face + hx - C25_A_RX                                           # relief axis x
    z_top = za + ht / 2.0 + C25_A_BOSS[1] + C25_A_RIBS[1]               # relief top (cable leaves +z)
    by, bz = C25_B_PORT
    x_b1 = HUB_X0 - C25_B_BODY[0]                                       # overmold -x end
    x_b0 = x_b1 - C25_B_BOOT[0]                                         # boot end (cable enters +x)
    xd = x_b0 - C25_R["drop"]                                           # drop column x
    r = C25_R

    def pts(x_far):
        return fillet3([(xr, ys, z_top - 0.5), (xr, ys, C25_LOOP_Z), (xr + 13.5, C25_OUT_Y, C25_LOOP_Z), (x_far, C25_OUT_Y, C25_LOOP_Z),
                        (x_far, by, C25_LOOP_Z), (xd, by, C25_LOOP_Z), (xd, by, bz), (x_b0 + 0.5, by, bz)],
                       [0, r["rise"], r["skew"], r["u"], r["u"], r["drop"], r["drop"], 0])
    a_len = C25_A_SHELL + (xr - face) + (z_top - za)                    # shell tip -> relief top along the plug
    b_len = C25_B_SHELL + C25_B_BODY[0] + C25_B_BOOT[0]                 # shell tip -> boot end
    lo, hi = xd + 30.0, 760.0
    for _ in range(60):                                                 # path length grows with x_far: bisection to C25_LEN
        mid = (lo + hi) / 2.0
        if a_len + path_len(pts(mid)) - 1.0 + b_len < C25_LEN:
            lo = mid
        else:
            hi = mid
    x_far = (lo + hi) / 2.0
    P = pts(x_far)
    return {"face": face, "ys": ys, "za": za, "xr": xr, "z_top": z_top, "x_b0": x_b0, "x_b1": x_b1, "xd": xd, "x_far": x_far, "pts": P,
            "a_len": a_len, "b_len": b_len, "cable": path_len(P) - 1.0, "len": a_len + path_len(P) - 1.0 + b_len,
            "zones": {"Z-C25-A": (face, face + hx, ys - hw / 2, ys + hw / 2, za - ht / 2, z_top),
                      "Z-C25-LOOP": (xr - UP_D / 2, x_far + UP_D / 2, C25_OUT_Y - UP_D / 2, by + UP_D / 2,
                                     z_top - 0.5 - UP_D / 2, C25_LOOP_Z + UP_D / 2),
                      "Z-C25-DROP": (xd - UP_D / 2, x_b0, by - UP_D / 2, by + UP_D / 2, bz - UP_D / 2, C25_LOOP_Z + UP_D / 2),
                      "Z-C25-B": (x_b0, HUB_X0, by - C25_B_BODY[1] / 2, by + C25_B_BODY[1] / 2, bz - C25_B_BODY[2] / 2, bz + C25_B_BODY[2] / 2)}}


C25 = {}


def hub_upstream(out, pi):
    """C25 Coms NA977: up-angled USB-A in the LOWER port of the Pi 5 GPIO-edge stack (the head rises 20.5 above the port axis - from the
    upper port the relief top would be z57, 4.35 under the lid, no room to turn the cable) -> flat slack loop over the hub shelf ->
    straight USB-B into the upstream port on the hub -x end face."""
    g = c25_geom(pi)
    C25.clear()
    C25.update(g)
    face, ys, za, xr = g["face"], g["ys"], g["za"], g["xr"]
    hx, hw, ht = C25_A_HEAD
    head = box(face, face + hx, ys - hw / 2, ys + hw / 2, za - ht / 2, za + ht / 2)
    z1 = za + ht / 2
    boss = cyl_z(xr, ys, z1 - 0.01, z1 + C25_A_BOSS[1], C25_A_BOSS[0])
    ribs = cyl_z(xr, ys, z1 + C25_A_BOSS[1] - 0.01, g["z_top"], C25_A_RIBS[0])
    by, bz = C25_B_PORT
    bbody = box(g["x_b1"], HUB_X0, by - C25_B_BODY[1] / 2, by + C25_B_BODY[1] / 2, bz - C25_B_BODY[2] / 2, bz + C25_B_BODY[2] / 2)
    boot = cyl_x(by, bz, g["x_b0"], g["x_b1"] + 0.01, C25_B_BOOT[1])
    ln = g["len"]
    out.add("C-USB-UPSTREAM", "USB 허브 업스트림 선 C25 (Coms NA977, A 상향 꺾임 → B 곧음, 25 cm)", "hub upstream cable C25 (Coms NA977, up-angled A to straight B, 25 cm)",
            G_CAB, union([head, boss, ribs, tube(g["pts"], UP_D), boot, bbody]), COLORS["cable"],
            "구매 목록 v4 C25 ([NA977] Coms USB Type A to Type B 25cm, USB 2.0 A 상향꺾임, 엘레파츠 4314354: 커넥터 포함 250 mm, B 곧음) + "
            + SRC + " centre_contents CU-E-PI5-USBA2 / PB-E-HUB + cable_duct.hub.upstream; " + SRC_R + " cables_simple 'hub upstream → Pi USB-A'",
            note="사양과 다름(작은 고침): 10/1 구매 목록 C25에 맞춤 - 사양 Z-UP-PLUG(위 포트, 곧은 A) · Z-UP-BEND(S자) · Z-HUB-UP(허브 -x 끝면 위로 꺾인 플러그) 대신 "
                 "A 쪽이 위로 꺾이고 B가 곧은 C25로 - (1) A 머리는 Pi GPIO 쪽 USB-A 2단의 아래 포트(축 y%.0f z%.1f)에: 위로 꺾인 머리가 포트 축에서 %.1f "
                 "올라가 위 포트(z%.1f)에 꽂으면 끝이 z%.1f, 뚜껑 밑(z%.2f)까지 %.2f라 선을 꺾을 수 없음 → 아래 포트면 끝 z%.1f, 위 포트는 머리에 가려 비움; "
                 "(2) 선은 위로 나와 R%.0f로 +x, z%.1f(위 화면 전원선 TS-C-PWR z59.6 밑)에서 허브 선반 위로 가 x%.1f에서 R%.0f U자로 돌아와 x%.1f에서 "
                 "R%.0f로 내려가 (3) 허브 -x 끝면의 업스트림 B 포트(y%.0f z%.1f)에 곧은 B 플러그(몸 %.0f + 부트 %.0f, x%.1f~%.1f)로 들어감; 추정: A 머리 "
                 "%.0f × %.0f × %.0f (포트 면 x%.1f부터) + 뿌리 Ø%.0f × %.0f + 주름 Ø%.1f × %.0f (사진 비례, A 쉘 12 × 4.5 기준), B 몸 %.0f × %.0f × %.0f, 선 OD %.0f; "
                 "길이: A %.1f (쉘 12 포함) + 선 %.1f + B %.1f (쉘 10 포함) = %.0f (제품 250) - 남는 선은 선반 위 납작한 U자(z%.1f, x%.0f까지, 화면 뚜껑 "
                 "이음 레일 x711 앞)로, 케이블 타이 없이 눕힘. '상향'은 혀가 위인 보통 가로 포트에서 위 - Pi 5 USB-A 2단은 두 포트가 같은 방향이라 위로 감 "
                 "(받으면 먼저 Pi에 꽂아 위로 가는지 확인 - 아래로 꺾이는 선은 어느 포트에서도 머리가 바닥 z16.5에 닿아 못 씀)"
                 % (ys, za, g["z_top"] - za, pi["z_up"], pi["z_up"] + g["z_top"] - za, Z_LIDU, Z_LIDU - (pi["z_up"] + g["z_top"] - za), g["z_top"],
                    C25_R["rise"], C25_LOOP_Z, g["x_far"], C25_R["u"], g["xd"] + C25_R["drop"], C25_R["drop"], by, bz, C25_B_BODY[0], C25_B_BOOT[0],
                    g["x_b0"], HUB_X0, hx, hw, ht, face, C25_A_BOSS[0], C25_A_BOSS[1], C25_A_RIBS[0], C25_A_RIBS[1], C25_B_BODY[0], C25_B_BODY[1],
                    C25_B_BODY[2], UP_D, g["a_len"], g["cable"], g["b_len"], ln, C25_LOOP_Z, g["x_far"] + UP_D / 2))
    return ln


# ------------------------------------------------------------------ PED cable (PED Zero -> front-zone lane -> hub port 2)

def ped_cable(M, out, ped_axis):
    it = {i["id"]: i for i in M["module_items"]}
    pb = it["usb_plug"]["boxes"][0]
    cx, cz = ped_axis
    z = {i["id"]: i for i in M["module_items"]}["zero"]
    zx0 = CC["CU-E-PEDZERO"][0]
    lx1 = max(b["x"][1] for b in z["boxes"])
    zy0 = CC["CU-E-PEDZERO"][2]
    ly1 = max(b["y"][1] for b in z["boxes"])
    lz0 = min(b["z"][0] for b in z["boxes"])
    zz0 = CC["CU-E-PEDZERO"][4]
    plug = box(zx0 + (lx1 - pb["x"][1]), zx0 + (lx1 - pb["x"][0]), zy0 + (ly1 - pb["y"][1]), zy0 + (ly1 - pb["y"][0]),
               pb["z"][0] - lz0 + zz0, pb["z"][1] - lz0 + zz0)
    b = plug.bounding_box()
    ly = (CC["Z-PED-LANE"][2] + CC["Z-PED-LANE"][3]) / 2.0
    lz = (CC["Z-PED-LANE"][4] + CC["Z-PED-LANE"][5]) / 2.0
    xh = HUB_PORT_X[HUB_PORT["PED"]]
    pts = fillet3([(cx, b[1] + 0.5, cz), (cx, 217.5, cz), (cx + 13.0, 217.5, cz + 5.0), (cx + 27.0, ly, lz), (CC["Z-PED-LANE"][1] - 1.0, ly, lz),
                   (xh, 236.0, HUB_Z), (xh, EXIT_Y1, HUB_Z)], [0, 5.0, 5.0, 5.0, 6.0, 6.0, 0])
    ln = MODULE_PLUG_L + path_len(pts) - 0.5 - 1.0 + HUB_PLUG_L
    cs = CABLE_SPEC["PED"]
    sol = union([plug, tube(pts, CABLE_OD), hub_plug(xh)])
    ymin = sol.bounding_box()[1]
    zy0 = min(CC["Z-PED-PLUG"][2], CC["Z-PED-LANE"][2])
    out.add("C-USB-PED", "USB-C 케이블 W208 (PED 보드 → 허브 포트 %d, %.1f m)" % (HUB_PORT["PED"], cs["std_m"]), "USB cable W208 PED board to hub",
            G_CAB, sol, COLORS["cable"],
            SRC_R + " ped_board (USB 8가닥 = 모듈 7 + PED 1); " + SRC + " centre_contents Z-PED-PLUG (x442.75~455.25 y222~247 z22~30) + Z-PED-LANE "
            "(x455.25~732 y222~232 z33~41) + cable_duct.cables PED (path %d mm, %.1f m)" % (cs["path_mm"], cs["std_m"]),
            note="사양과 다름(작은 고침): 사양 Z-PED-PLUG z22~30은 리셉터클 축 z26 가정 - 사양 PEDZERO 상자 z23.1~28.8의 Zero는 축 z%.1f이라 "
                 "플러그 z%.1f~%.1f, 위로 0.8 나옴 (위는 비어 있음, PED 줄은 z33부터); 사양과 다름(작은 고침): 플러그 + 부트 25 mm 뒤의 굽힘이 y%.2f까지 "
                 "나옴 - 사양 Z-PED-PLUG·Z-PED-LANE 앞끝 y%.0f보다 %.2f 앞 (x443~472 z23~36, 그 자리 앞 공간은 비어 있고 뒷바 앞면 y214 안; USB 선을 "
                 "그보다 좁게 굽힐 수 없음); 추정: PED Zero USB-C(축 x%.2f)의 곧은 플러그 y%.1f~%.1f가 -y로, "
                 "y217.5에서 +x로 꺾여 올라 앞 공간 줄 y%.0f z%.0f를 달려 x%.0f에서 묶음 위로 내려와 허브 포트 %d(x%.1f)로; "
                 "길이 %.1f mm (사양 %d, 표준 %.1f m, 여유 %.0f) - 경로는 보기용"
                 % (cz, b[2], b[5], ymin, zy0, zy0 - ymin, cx, b[1], b[4], ly, lz, CC["Z-PED-LANE"][1] - 1.0, HUB_PORT["PED"], xh, ln, cs["path_mm"],
                    cs["std_m"], cs["std_m"] * 1000 - ln))
    return ln


# ------------------------------------------------------------------ power harness (roughly as spec cable_duct.other_leads.power)

def pwr_paths():
    """filleted centre lines of the power harness (dict name -> list of polylines)."""
    e = PWR_D / 2.0 + TOUCH
    p = CC["CU-E-PDTRIG"]
    f = CC["CU-E-FUSE"]
    fy, fz = (f[2] + f[3]) / 2.0, (f[4] + f[5]) / 2.0
    bk = CC["CU-E-BUCK"]
    amp = CC["CU-E-AMP"]
    kx, ky, kin, kout = SW_LUGS["x"], SW_LUGS["y_tip"], SW_LUGS["z_in"], SW_LUGS["z_out"]
    cl = C24_COLLAR
    dc = HUB_DC
    P = {}
    # HUSB238 output (-y end of the board) -> fuse holder left end (lead through the open end of the cradle bore)
    pz = p[4] + 0.6
    P["IN"] = [fillet3([((p[0] + p[1]) / 2, p[2] - e, pz), ((p[0] + p[1]) / 2, 318.0, pz), (412.0, 318.0, 26.0), (401.0, 318.0, fz),
                        (401.0, fy, fz), (f[0] - e, fy, fz)], [0, 3.0, 4.0, 3.0, 3.0, 0])]
    # fuse holder right end -> KCD1 input lug (lower)
    P["FUSE"] = [fillet3([(f[1] + e, fy, fz), (456.5, fy, fz), (456.5, fy, 31.0), (kx, 312.0, 33.0), (kx, ky - e, kin)],
                         [0, 2.5, 3.0, 3.0, 0])]
    # KCD1 output lug (upper) -> buck IN (-x end face, y306) + 20 V feed along the back lane to the amp (-x end face, y313)
    s0 = (kx, ky - e, kout)
    P["20V"] = [fillet3([s0, (kx, 313.5, kout), (450.0, 306.0, 38.0), (bk[0] - e, 306.0, 36.5)], [0, 2.5, 4.0, 0]),
                fillet3([s0, (kx, 314.5, kout + 2.0), (kx, 314.5, 51.0), (443.0, 324.0, 53.0), (733.0, 324.0, 53.0), (733.0, 313.0, 52.0),
                         (amp[0] - e, 313.0, 52.0)], [0, 1.5, 3.0, 4.0, 3.0, 3.0, 0])]
    # buck OUT (front face, x529.5) -> C24 (BT663) side-angled USB-C at the Pi -y edge (lead leaves -x through the collar) + hub 5 V DC
    # (right-angle plug on the hub -x end face, lead leaves +z); both ends run 1 mm into the collar / plug head (one part with them)
    o = (529.5, bk[2] - e, 36.0)
    xdc, ydc = (dc[0] + dc[1]) / 2.0, (dc[2] + dc[3]) / 2.0
    P["5V"] = [fillet3([o, (529.5, 283.0, 36.0), (529.5, 262.0, 36.0), (537.0, cl[2], 28.0), (cl[0] + 1.0, cl[2], cl[3])], [0, 3.0, 5.0, 4.0, 0]),
               fillet3([o, (529.5, 285.0, 40.0), (529.5, 285.0, 48.5), (xdc - 8.0, 285.0, 48.5), (xdc, ydc, 48.5), (xdc, ydc, dc[5] - 1.0)],
                       [0, 2.0, 3.0, 4.0, 4.0, 0])]
    return P


# C24 Coms BT663 (purchase list v4, 10/1): USB-C plug angled to the SIDE (the lead leaves along the wide face), 20 cm, A end cut off,
# red / black to the buck output. Head photo-scaled from the 8.25 C shell (estimate): 14 along the exit direction x 12 along the
# insertion x 7 thick; the C shell (6.5) is inside the Pi receptacle (USB-C centre x553.2 = 11.2 from the Pi end x542, axis z25.7).
C24_HEAD = (546.0, 560.0, 250.0, 262.0, 22.2, 29.2)      # inside the spec keep-out Z-PI-PWR x546~560 y249~262 z22~31
C24_COLLAR = (542.5, 546.0, 254.0, 25.7, 4.5)            # strain-relief collar x0, x1, y, z, D - the lead leaves -x (toward the buck)


def power_parts(out):
    P = pwr_paths()
    LENGTHS.update({"PWR-" + k: sum(path_len(q) for q in v) for k, v in P.items()})
    src = SRC + " cable_duct.other_leads.power (USB-C PD 입력 → HUSB238 → 퓨즈(x405~451) → KCD1 → 20 V를 강압(D칸)과 앰프(선반)로; 5.1 V는 " \
                "강압 → Pi(C24), 허브 DC) + centre_contents Z-SPKLEAD-L (뒤 줄 y322~330 z51~55)"
    tb = lambda k: union([tube(q, PWR_D, 12) for q in P[k]])
    ln = LENGTHS
    out.add("C-PWR-IN", "전원선 HUSB238 → 퓨즈 홀더 (18 AWG 빨강·검정)", "power lead PD trigger to fuse holder", G_CAB, tb("IN"), WIRE_RED, src,
            note="추정: 두 가닥을 Ø3 한 줄로; PD 기판 -y 끝에서 앞으로 나와 y318을 따라 내려가 x401에서 퓨즈 홀더 왼쪽 끝으로 (받침 구멍 끝이 열림, "
                 "Z-BANK-PLUG z26 아래); 약 %.0f mm - 경로는 보기용" % ln["PWR-IN"])
    out.add("C-PWR-FUSE", "전원선 퓨즈 홀더 → KCD1 입력 단자 (18 AWG)", "power lead fuse holder to the KCD1 input lug", G_CAB, tb("FUSE"), WIRE_RED, src,
            note="추정: 퓨즈 홀더 오른쪽 끝에서 x456.5로 나와 받침 위로 올라 KCD1 아래 단자(z%.1f) 끝에 납땜 (J501 선반 y315.5 앞); 약 %.0f mm"
                 % (SW_LUGS["z_in"], ln["PWR-FUSE"]))
    out.add("C-PWR-20V", "20 V 선 KCD1 → 강압 입력 + 앰프 전원 (18 AWG, 한 단자에서 두 갈래)", "20 V harness: KCD1 to buck input and amp", G_CAB,
            tb("20V"), WIRE_RED, src,
            note="추정: KCD1 위 단자(z%.1f)에서 두 갈래 - (1) 강압 -x 끝면 입력 단자(x%.1f y306 z36.5), (2) 위로 올라 뒤 줄 y324 z53 (뒤판을 따라, "
                 "강압 윗면 z50.5 위 1, 뚜껑 이음 레일 밑 0.85)을 x733까지 가서 앰프 -x 끝면 전원 단자(y313 z52); 약 %.0f mm"
                 % (SW_LUGS["z_out"], CC["CU-E-BUCK"][0], ln["PWR-20V"]))
    h = C24_HEAD
    cl = C24_COLLAR
    mt = union([box(*h), cyl_x(cl[2], cl[3], cl[0], cl[1] + 0.01, cl[4])])
    dc = box(*HUB_DC)
    l_pi = path_len(pwr_paths()["5V"][0])
    out.add("C-PWR-5V", "5.1 V 선 강압 → Pi 5 (C24 BT663 측면 꺾임 USB-C) + 허브 DC (ㄱ자 DC 플러그, 허브 -x 끝면)",
            "5.1 V harness: buck to Pi 5 (C24 BT663 side-angled USB-C) and hub DC (right-angle plug, hub -x end face)", G_CAB,
            union([tb("5V"), mt, dc]), WIRE_RED,
            src + " + Z-PI-PWR (x546~560 y249~262 z22~31) + 구매 목록 v4 C24 ([BT663] Coms USB-C 측면꺾임 20 cm, A 쪽을 잘라 빨강·검정을 강압 출력에) "
                  "/ L17 허브 DC (딸린 5 V 어댑터 선의 플러그 쪽)",
            note="사양과 다름(작은 고침): W1 10/1 - 허브 DC를 +x 끝면(Z-HUB-DC)에서 업스트림 B 포트와 같은 -x 끝면으로 옮겨 선반 앞 줄(Z-PWR-LANE)을 쓰지 않음; "
                 "추정: 강압 앞면 출력 단자(x529.5 z36)에서 두 갈래 - (1) J702 기판 위(z36)를 지나 Pi -y 가장자리의 C24 측면 꺾임 USB-C 머리 "
                 "%.0f×%.0f×%.0f (x%.0f~%.0f y%.0f~%.0f z%.1f~%.1f, 사양 지킴 자리 Z-PI-PWR 14×13×9 안) + 꼬리 Ø%.1f (x%.1f~%.0f) - 선이 -x(강압 쪽)로 "
                 "나오게 꽂음 (USB-C는 뒤집으면 +x), 강압 단자까지 경로 약 %.0f mm - 20 cm 선의 A 쪽을 자를 때 30~40 mm 여유만 남김; (2) y285 z48.5 "
                 "(Pi USB-A 위 6.5, Z-DSI y280 뒤 3.5)를 x%.1f까지 가서 허브 -x 끝면의 ㄱ자 DC 플러그 머리 12×12×10 (x%.1f~%.1f y%.0f~%.0f z%.1f~%.1f, "
                 "잭 y%.0f z%.1f, 선이 위로 나옴)로 내려옴; 곧은 DC 플러그는 잭 면에서 몰드 끝까지 %.0f mm 이하이고 선을 바로 위로 R%.0f로 꺾을 때만 "
                 "들어감 (그보다 길면 Pi 쪽 젠더 IH190 x647.5에 닿음, check_electronics.py); 전체 약 %.0f mm"
                 % (h[1] - h[0], h[3] - h[2], h[5] - h[4], h[0], h[1], h[2], h[3], h[4], h[5], cl[4], cl[0], cl[1], l_pi,
                    (HUB_DC[0] + HUB_DC[1]) / 2.0, HUB_DC[0], HUB_DC[1], HUB_DC[2], HUB_DC[3], HUB_DC[4], HUB_DC[5], HUB_DC_YZ[0], HUB_DC_YZ[1],
                    HUB_DC_STRAIGHT_MAX, HUB_DC_STRAIGHT[1], ln["PWR-5V"]))


# ------------------------------------------------------------------ XT30 pairs (end-wall clips) + speaker leads

def xt30_pockets():
    pk = BODY.XT30_POCKET
    return {s: tuple(float(v) for v in pk[s]) for s in "LR"}, "body.py XT30_POCKET"


XT30_LF, XT30_LM, XT30_ENG = 12.4, 13.7, 5.6          # female / male length, engaged length (BOM L61 / audio.md §4)


def xt30_poses(R):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    pair = rb["xt30_pair_L"]["boxes"][0]
    fw = pair["y"][1] - pair["y"][0]                    # 10.2 face width
    ft = pair["z"][1] - pair["z"][0]                    # 5.2 face thickness
    pockets, psrc = xt30_pockets()
    res = {}
    for side in "LR":
        x0, x1, y0, y1, z0, z1 = pockets[side]
        yc, zc = (y0 + y1) / 2.0, (z0 + z1) / 2.0
        hy, hz = (fw / 2, ft / 2) if (y1 - y0) >= (z1 - z0) else (ft / 2, fw / 2)
        if side == "L":                                 # mouth +x (toward the centre)
            mouth = x1
            fem = (mouth - XT30_LF, mouth)
            mal = (mouth, mouth + XT30_LM - XT30_ENG)
        else:
            mouth = x0
            fem = (mouth, mouth + XT30_LF)
            mal = (mouth - (XT30_LM - XT30_ENG), mouth)
        res[side] = {"pocket": pockets[side], "yc": yc, "zc": zc, "hy": hy, "hz": hz, "fem": fem, "mal": mal, "mouth": mouth, "psrc": psrc}
    return res


def xt30_parts(R, out):
    P = xt30_poses(R)
    for side in "LR":
        q = P[side]
        x0, x1, y0, y1, z0, z1 = q["pocket"]
        yc, zc, hy, hz = q["yc"], q["zc"], q["hy"], q["hz"]
        fem = box(q["fem"][0], q["fem"][1], yc - hy, yc + hy, zc - hz, zc + hz)
        mal = box(q["mal"][0], q["mal"][1], yc - hy, yc + hy, zc - hz, zc + hz)
        cc = CC["C-XT30-%s" % side]
        src = (SRC_R + " xt30_pair_%s (face 10.2×5.2, M 13.7 + F 12.4 − 5.6 engaged); position %s %s = %s centre_contents C-XT30-%s "
               "(x%.1f~%.1f y%.0f~%.0f z%.0f~%.0f, 끝벽 집게) + speakers.xt30" % (side, q["psrc"], side, SRC, side, cc[0], cc[1], cc[2], cc[3], cc[4], cc[5]))
        out.add("C-XT30F-%s" % side, "XT30U-F 암 (스피커 꼬리, 끝벽 집게 %s 안)" % side, "XT30U-F female (pod pigtail) in the end-wall clip " + side, G_CAB,
                fem, XT30_YELLOW, src,
                note="추정: 몸체를 10.2×5.2×12.4 상자로; 집게 홈(x%.1f~%.1f y%.1f~%.1f z%.1f~%.1f) 가운데, 입구를 홈 입구 x%.1f(가운데 쪽)에 맞춤; "
                     "꼬리 선은 C-SPKPIG-%s" % (x0, x1, y0, y1, z0, z1, q["mouth"], side))
        out.add("C-XT30M-%s" % side, "XT30U-M 수 (앰프 선, 가운데 쪽에서 꽂힘) %s" % side, "XT30U-M male (amp lead, mated) " + side, G_CAB,
                mal, XT30_YELLOW, src, note="추정: 암 속으로 들어간 5.6은 빼고 밖에 보이는 8.1만 표시; 앰프 선은 C-SPK-%s" % side)
    return P


SPKL_WALL_Y = 256.0            # C-SPK-L leaves the left end wall here (clip plate y<=252.5 in front, power bank y>=254 behind)


def spk_lead_paths(P):
    """amp -> XT30M centre lines (L: back lane y328 z53 + down the left end wall; R: over the shelf y293 z49.5)."""
    e = PWR_D / 2.0 + TOUCH
    amp = CC["CU-E-AMP"]
    L, Rr = P["L"], P["R"]
    tipL = (L["mal"][1] + e, L["yc"], L["zc"])
    tipR = (Rr["mal"][0] - e, Rr["yc"], Rr["zc"])
    xw = BODY.CU_IX[0] + BODY.CLIP_SEAT + 0.1                # 275.1: on the slot floor of the two end-wall cable clips
    # leaves the wall at y256 (just behind the XT30 clip plate y<=252.5, top z54) and runs diagonally in front of the power bank
    # (x286.. y254..; at x286 the lead is at y~250.5) to x301 over the XT30U-M, then drops to its back end (review 2026-10-01: the old
    # corner y260 -> (301, 246, 52) passed 0.57 over the bank's front-left corner)
    pl = fillet3([(amp[0] - e, 318.0, 52.0), (737.0, 318.0, 52.0), (737.0, 328.0, 53.0), (xw, 328.0, 53.0), (xw, SPKL_WALL_Y, 53.0),
                  (301.0, L["yc"], 53.0), (301.0, L["yc"], L["zc"]), tipL], [0, 3.0, 3.0, 8.0, 6.0, 3.0, 3.0, 0])
    pr = fillet3([(amp[1] + e, 293.0, 49.5), (915.0, 293.0, 49.5), (922.0, Rr["yc"], Rr["zc"]), tipR], [0, 4.0, 3.0, 0])
    return {"L": pl, "R": pr}


PIG_COIL = (4.5, 1.5)          # slack coil in the end-wall tunnel: centre-line radius, turns (about 35 mm of slack in the coil; about 54 mm
                               # of tail outside the pod - LENGTHS PIG-SLACK-* / PIG-OUT-*, quoted as body.PIG_SLACK_MM / PIG_OUT_MM)


COIL_X = {"L": (270.0, 262.0), "R": (951.5, 959.5)}   # coil x span inside the end-wall tunnel (end wall x260..271.5 / 950.5..962)


def coil_slack(side):
    """slack held by the tunnel coil: helix length - its axial length (mm)."""
    x0, x1 = COIL_X[side]
    ey, ez = BODY.END_HOLE_YZ[side]
    return path_len(_helix(x0, x1, ey, ez, PIG_COIL[0], 90.0, PIG_COIL[1])) - abs(x1 - x0)


def _helix(x0, x1, cy, cz, r, th0, turns, n_per_turn=24):
    """helix points along x from x0 to x1 around (cy, cz), starting at angle th0 (deg, 0 = +y, 90 = +z)."""
    n = max(2, int(math.ceil(turns * n_per_turn)))
    pts = []
    for k in range(n + 1):
        t = k / float(n)
        a = math.radians(th0 + 360.0 * turns * t)
        pts.append((x0 + (x1 - x0) * t, cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def pig_paths(P):
    """XT30U-F pigtail centre lines: F back -> clip-plate hole -> 1.5 loose turns in the end-wall tunnel D14 (coaxial with the clip
    pocket) -> 3 mm gap -> pod side-panel hole D6 (sealed) -> inside the pod to the driver terminal (basket +x / -x side, w-16)."""
    e = PIG_D / 2.0 + TOUCH
    out = {}
    n = np.array(BODY.SPK_N)
    rc, turns = PIG_COIL
    for side in "LR":
        q = P[side]
        wy, wz = BODY.WIRE_YZ[side]
        ey, ez = BODY.END_HOLE_YZ[side]
        cx, cy, cz = BODY.DRIVER_POSE[side]
        sgn = 1.0 if side == "L" else -1.0                     # terminal on the basket side facing the centre unit
        term = np.array([cx, cy, cz]) + sgn * np.array([47.0 + e, 0.0, 0.0]) + (-16.0) * n
        if side == "L":
            fb = q["fem"][0]                                   # F back x274.6, tail exits -x into the plate hole
            coil = _helix(COIL_X["L"][0], COIL_X["L"][1], ey, ez, rc, 90.0, turns)
            head = [(fb - e, q["yc"], q["zc"])]
            tail = [(257.0, wy, wz), (244.0, wy, wz), tuple(term)]
            rad = [0] * (len(head) + len(coil)) + [1.5, 5.0, 0]
        else:
            fb = q["fem"][1]                                   # F back x947.4, tail exits +x into the plate hole
            coil = _helix(COIL_X["R"][0], COIL_X["R"][1], ey, ez, rc, 90.0, turns)
            head = [(fb + e, q["yc"], q["zc"])]
            tail = [(962.5, wy, 43.6), (965.5, wy, 41.2), (978.0, wy, wz), tuple(term)]
            rad = [0] * (len(head) + len(coil)) + [0.8, 0.8, 5.0, 0]
        out[side] = fillet3(head + coil + tail, rad)
    return out


def pig_outside_len(side, pts=None, P=None):
    """length of the pigtail outside the pod (from the pod inner-panel joint face to the F back)."""
    if pts is None:
        pts = pig_paths(P)[side]
    face = BODY.SPK_X["L"][1] if side == "L" else BODY.SPK_X["R"][0]
    ln = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        (xa, xb) = (a[0], b[0])
        outside = (lambda x: x >= face) if side == "L" else (lambda x: x <= face)
        if outside(xa) and outside(xb):
            ln += math.dist(a, b)
        elif outside(xa) != outside(xb):
            t = (face - xa) / (xb - xa)
            m = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            ln += math.dist(a, m) if outside(xa) else math.dist(m, b)
    return ln


def speaker_leads(out, P):
    SL = spk_lead_paths(P)
    PG = pig_paths(P)
    for side in "LR":
        LENGTHS["SPK-" + side] = path_len(SL[side])
        LENGTHS["PIG-" + side] = path_len(PG[side])
    out.add("C-SPK-L", "스피커선 L (앰프 → XT30U-M L, 18 AWG 2가닥)", "speaker lead L (amp to XT30U-M L)", G_CAB, tube(SL["L"], PWR_D, 12), COLORS["cable"],
            SRC + " centre_contents Z-SPKLEAD-L (뒤 줄 y322~330 z51~55: 앰프 → XT30 L + 20 V) + Z-SPKLEAD-L2 (x271.5~284 y236~330 z50~58, 끝벽을 따라) "
            "+ cable_duct.other_leads.speaker",
            note="추정: Ø3 한 줄로; 앰프 -x 끝면 L 단자(y318 z52)에서 뒤 줄 y328 z53 (20 V 선 y324 뒤)을 x275까지, 끝벽 L 안면을 따라 "
                 "(케이블 집게 2개 y262~282·286~306의 홈 바닥, x275.1) y%.0f까지 앞으로 와 (XT30 집게 판 y≤252.5 뒤) 보조배터리 앞(배터리 y254~)을 "
                 "비스듬히 x301까지 z53으로 건넌 뒤 내려와 XT30U-M L 뒤끝(+x)으로 들어감 - 배터리를 곧게 들어 빼도 닿지 않음; 약 %.0f mm"
                 % (SPKL_WALL_Y, LENGTHS["SPK-L"]))
    out.add("C-SPK-R", "스피커선 R (앰프 → XT30U-M R, 18 AWG 2가닥)", "speaker lead R (amp to XT30U-M R)", G_CAB, tube(SL["R"], PWR_D, 12), COLORS["cable"],
            SRC + " centre_contents Z-SPKLEAD-R (x796~927 y286~296 z45~52, 선반 위) + cable_duct.other_leads.speaker",
            note="추정: Ø3 한 줄로; 앰프 +x 끝면 R 단자(y293 z49.5)에서 선반 위 y293 z49.5를 x915까지, XT30U-M R 뒤끝(-x)으로; 약 %.0f mm" % LENGTHS["SPK-R"])
    for side in "LR":
        wy, wz = BODY.WIRE_YZ[side]
        ey, ez = BODY.END_HOLE_YZ[side]
        LENGTHS["PIG-OUT-" + side] = pig_outside_len(side, PG[side])
        LENGTHS["PIG-SLACK-" + side] = coil_slack(side)
        out.add("C-SPKPIG-%s" % side, "스피커 꼬리선 %s (XT30U-F 꼬리 150 → 유닛 단자)" % side, "pod pigtail %s (XT30U-F tail to the driver)" % side, G_CAB,
                tube(PG[side], PIG_D, 12), COLORS["cable"],
                SRC + " speakers.xt30 (스피커 선 XT30U-F 꼬리 150이 안쪽 옆판의 밀봉 구멍 Ø6 (y%.0f z%.0f, EVA 띠 사이)으로 나와 3 mm 틈을 건너 가운데 "
                      "끝벽 구멍 Ø14로 들어가 끝벽 집게의 짝과 꽂힘); body.py WIRE_YZ / END_HOLE_YZ / XT30_POCKET / DRIVER_POSE" % (wy, wz),
                note="추정: 2가닥을 Ø2 한 줄로 (보기용); 암 뒤끝에서 집게 판 구멍 → 끝벽 구멍 Ø14 (y%.0f z%.1f, %s) 안에 느슨하게 %.1f바퀴 "
                     "(지름 약 %.0f) 감긴 여유 → 틈 → 스피커 옆판 구멍 Ø6 (y%.0f z%.0f, 본드로 밀봉) → 상자 안에서 유닛 바스켓 %s쪽 단자(유닛 축에서 x %.0f, "
                     "바깥면 뒤 16)까지 약 %.0f mm (꼬리 150; 스피커 밖 %.0f mm - 스피커를 약 10 mm 들고 15 mm 바깥으로 밀어도 F가 집게에 남음; "
                     "남는 선은 상자 안 흡음솜 속에)"
                     % (ey, ez, "집게 홈과 같은 축" if abs(ez - (BODY.XT30_POCKET[side][4] + BODY.XT30_POCKET[side][5]) / 2) < 0.05
                        else "집게 홈 축 z%.1f보다 %.1f 아래" % ((BODY.XT30_POCKET[side][4] + BODY.XT30_POCKET[side][5]) / 2,
                                                           (BODY.XT30_POCKET[side][4] + BODY.XT30_POCKET[side][5]) / 2 - ez),
                        PIG_COIL[1], 2 * PIG_COIL[0], wy, wz, "+x" if side == "L" else "-x", 47.0 + PIG_D / 2, LENGTHS["PIG-" + side],
                        LENGTHS["PIG-OUT-" + side]))


# ------------------------------------------------------------------ speakers on the slanted baffles (body.py pose)

SPK_N = tuple(BODY.SPK_N)                        # driver axis (out of the baffle, toward the player and up)
SPK_U = tuple(BODY.SPK_U)                        # up the slant
SPK_C = {s: tuple(BODY.DRIVER_POSE[s]) for s in "LR"}
GASKET_T = 3.0                                   # EVA gasket 3T between the outer face and the flange
DRV_DEPTH = 61.0                                 # speakers.driver.model 'CW-100B25 ... 깊이 61 = 플랜지 4 포함'


def spk_frame(cx, cy, cz):
    """local (a = x, b = up the slant, w = along the axis, 0 at the baffle outer face) -> world."""
    return np.array([[1.0, SPK_U[0], SPK_N[0], cx],
                     [0.0, SPK_U[1], SPK_N[1], cy],
                     [0.0, SPK_U[2], SPK_N[2], cz]])


def speaker_local(R):
    sp = R["speakers"][0]
    fl = sp["boxes"][0]
    frame = fl["x"][1] - fl["x"][0]                    # 105
    ft = fl["y"][1] - fl["y"][0]                       # 4
    cyls = {c["name"].split()[0]: c for c in sp["cylinders"]}
    basket, magnet = cyls["basket"], cyls["magnet"]
    bd, md = basket["d"], magnet["d"]                  # 94, 85
    b_len = basket["range"][1] - basket["range"][0]    # 37
    m_len = magnet["range"][1] - magnet["range"][0]    # 17
    w_f0, w_f1 = GASKET_T, GASKET_T + ft               # flange 3..7 in front of the face
    flange = box(-frame / 2, frame / 2, -frame / 2, frame / 2, w_f0, w_f1)
    cx0, cz0 = sp["center_xz"]
    slots = []
    for (sx, sz) in sp["mount_holes"]["centers_xz"]:
        a, b = sx - cx0, sz - cz0
        ang = math.degrees(math.atan2(b, a))
        slots.append(prism_z(stadium_pts(a, b, 6.8, 4.8, ang), w_f0 - 0.01, w_f1 + 0.01))
    flange = diff(flange, slots)
    rim = Manifold.cylinder(w_f0 + 0.02, bd / 2, bd / 2, 96).translate((0, 0, -0.01))
    bsk = Manifold.cylinder(b_len + 0.01, bd / 2, bd / 2, 96).translate((0, 0, -b_len))
    mag = Manifold.cylinder(m_len + 0.01, md / 2, md / 2, 96).translate((0, 0, -b_len - m_len))
    body = union([flange, rim, bsk, mag])
    recess = Manifold.cylinder(24.0, 17.0, 45.0, 96).translate((0, 0, w_f1 - 24.0 + 0.01))
    cap = Manifold.cylinder(5.5, 17.0, 10.0, 64).translate((0, 0, w_f1 - 24.5))
    body = union([diff(body, [recess]), cap])
    depth = w_f1 + b_len + m_len
    return body, {"frame": frame, "ft": ft, "bd": bd, "md": md, "w_front": w_f1, "w_back": -(b_len + m_len), "depth": depth,
                  "magnet_w": (-(b_len + m_len), -b_len), "basket_w": (-b_len, 0.0)}


def speaker_parts(R, out):
    local, info = speaker_local(R)
    assert abs(info["depth"] - DRV_DEPTH) < 1e-6
    for side in "LR":
        sp = next(s for s in R["speakers"] if s["id"].endswith(side))
        cx, cy, cz = SPK_C[side]
        body = local.transform(spk_frame(cx, cy, cz))
        mlow = cz + info["magnet_w"][0] * SPK_N[2] - info["md"] / 2 * SPK_U[2]
        mc = np.array([cx, cy, cz]) + (info["magnet_w"][0] + info["magnet_w"][1]) / 2.0 * np.array(SPK_N)
        out.add("SPK-%s" % side, sp["name_ko"], sp["name_en"], "스피커 유닛", body, COLORS["speaker"],
                SRC_R + " speakers %s (flange 105×105×4 with 4 slots Ø4.8×6.8 on PCD 115; basket Ø94 × 37; magnet Ø85×17; depth 61); pose "
                % sp["id"] + SRC + " speakers.driver + body.py DRIVER_POSE / SPK_N (ANGLE %.1f°: 중심 x%.1f y%.2f z%.2f, 축 (0, %.4f, %.4f), 앞에서 달기: "
                "가스켓 3 + 플랜지 4가 바깥면 위)" % (BODY.ANGLE, cx, cy, cz, SPK_N[1], SPK_N[2]),
                note="추정: 플랜지를 경사 바깥면에서 가스켓 3 앞(법선 방향 %.0f~%.0f)에, 바스켓 테두리를 가스켓 구멍 안으로 이어 한 덩어리로; "
                     "자석이 바깥면 뒤 37~54 (자석 중심 y%.2f z%.2f), 가장 낮은 곳 z%.2f (아랫판 윗면 z%.1f 위 %.2f); 자석 뒤 폴 벤트는 모델에 없음 "
                     "(축 방향 10 mm 이상 비움 - W1); 콘 오목면(Ø90→Ø34, 깊이 24)과 더스트캡은 보기용"
                     % (GASKET_T, GASKET_T + info["ft"], mc[1], mc[2], mlow, Z_BOT, mlow - Z_BOT))
    return info


def pedal_part(R, out):
    p = R["pedal"]
    b = p["boxes"][0]
    x0, x1 = b["x"]
    y0, y1 = b["y"]
    z0, z1 = b["z"]
    poly = [(y0, z0), (y1, z0), (y1, z1), (y1 - 30.0, z1), (y0, z0 + 25.0)]
    out.add("PEDAL-DAMPER", p["name_ko"], p["name_en"], "댐퍼 페달 (바닥)", prism_x(poly, x0, x1), "#1d1d1f",
            SRC_R + " pedal (76×240×65, floor z-720 for a 720 mm desk, plan x640..716 y-400..-160 from drawing 7). "
            "추정: 쐐기 모양(뒤쪽 경첩이 높음), 책상 높이 720", note="offdesk")


def headphone_jack(F, out):
    hj = F["cheeks"]["headphone_jack"]
    d = hj["jack_dims"]
    pk = hj["pocket"]
    cx, az = pk["centre_x"], pk["axis_z"]
    y0 = pk["front_wall"]["y"][1]
    out.add("EL-E-J701", "헤드폰 잭 PJ-313 (J701, 왼쪽 볼 앞면)", "headphone jack PJ-313 (J701) in the left cheek", "끝 부속 왼쪽 전자부",
            pj313(d, cx, az, y0, -1), BLACK_PLASTIC,
            "spec/keyaction_features_frame.json cheeks.headphone_jack (pocket centre x-8.34, axis z20, cavity y2.5..14.2, nose Ø5.0 through y0..2.5); "
            + PJ313_SRC + "; " + SRC_R + " headphone_jack_j701",
            note="추정: 포켓 위치·축 높이 z20 (frame spec assumed); 다리(밑 3.2)와 케이블 ①·②(W701/W702)는 뺌")


# ------------------------------------------------------------------ R31 touchscreen rev 3: Waveshare 7-DSI-TOUCH-C, DSI FFC, GPIO power lead

G_TS = "터치스크린"
G_TSF = "터치스크린 (접은 상태, 별도 보기)"
SCREEN_BLACK = "#15181c"
FFC_ORANGE = "#e0a030"
TS_EST = {
    "recess": 2.0,          # depth of the connector window in the screen back (drawing shows the window, depth unknown)
    "zif_h": 2.0,           # 22P 0.5 mm ZIF body height on the recess floor
    "mx_h": 2.0,            # MX1.25 2P horizontal header height
    "hole_depth": 4.0,      # M2.5 thread depth in the screen corners (unknown; spec G-2 measures it)
    "hole_minor": 2.2,      # M2.5 thread minor dia (the screw D2.5 overlaps it = thread engagement)
    "tab_w": (2.0, 6.0),    # w range of the small feature on the glass bottom edge (drawing gives xr / proud only)
    "stack": 0.27,          # layer offset of a folded ribbon (0.9 x thickness, so the folds stay one piece)
    "ramp": (5.5, 1.0),     # ribbon / lead climb from the recess (w7) onto the screen back between u30.2+5.5 .. u30.2+1.0
    "wire_d": 1.1,          # silicone jumper / MX1.25 lead OD
    "wire_pitch": 1.3,      # the two leads side by side (0.2 apart, W1 model); each lead is its own part (no tube-tube boolean)
    "dupont": (2.5, 2.5, 14.0),   # F/F jumper housing on a GPIO pin
    "pin_above_base": 6.0,  # 2.54 header pin tip above the plastic base (CAD header box top z32.6 = pin tips)
}


def _fillet(points, R, n=10):
    """polyline -> polyline with every corner replaced by an arc of radius R (clipped to 0.49 of the neighbouring segments)."""
    P = [np.array(p, float) for p in points]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u1 = (b - a) / np.linalg.norm(b - a)
        u2 = (c - b) / np.linalg.norm(c - b)
        phi = math.acos(float(np.clip(u1 @ u2, -1, 1)))
        if phi < 1e-4:
            out.append(b)
            continue
        d = min(R * math.tan(phi / 2), 0.49 * np.linalg.norm(b - a), 0.49 * np.linalg.norm(c - b))
        r = d / math.tan(phi / 2)
        p0, p1 = b - u1 * d, b + u2 * d
        bis = (u2 - u1) / np.linalg.norm(u2 - u1)
        ctr = b + bis * (r / math.cos(phi / 2))
        v0, v1 = p0 - ctr, p1 - ctr
        om = math.acos(float(np.clip(v0 @ v1 / (np.linalg.norm(v0) * np.linalg.norm(v1)), -1, 1)))
        for k in range(n + 1):
            t = k / n
            out.append(v0 + ctr if om < 1e-9 else ctr + (math.sin((1 - t) * om) * v0 + math.sin(t * om) * v1) / math.sin(om))
    out.append(P[-1])
    clean = [out[0]]
    for p in out[1:]:
        if np.linalg.norm(p - clean[-1]) > 1e-6:
            clean.append(p)
    return clean


def _tube_mesh(rings):
    """consecutive cross-section rings (same vertex count) -> closed Manifold (end caps fanned round the ring centres)."""
    k = len(rings[0])
    V = np.vstack(rings)
    F = []
    for i in range(len(rings) - 1):
        for j in range(k):
            a, b = i * k + j, i * k + (j + 1) % k
            c, d = (i + 1) * k + (j + 1) % k, (i + 1) * k + j
            F += [(a, b, c), (a, c, d)]
    c0, c1 = len(V), len(V) + 1
    V = np.vstack([V, rings[0].mean(axis=0), rings[-1].mean(axis=0)])
    last = (len(rings) - 1) * k
    for j in range(k):
        F.append((c0, (j + 1) % k, j))
        F.append((c1, last + j, last + (j + 1) % k))
    F = np.array(F, dtype=np.int64)
    tri = V[F]
    if np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() < 0:
        F = F[:, ::-1]
    return Manifold(Mesh(vert_properties=V.astype(np.float32), tri_verts=F.astype(np.uint32)))


def sweep_rect(points, wdir, width, thick):
    """flat strip (FFC): centreline points, width direction (one vector, projected square to the path)."""
    P = [np.array(p, float) for p in points]
    rings = []
    for i, p in enumerate(P):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        t = t / np.linalg.norm(t)
        w = np.array(wdir, float) - (np.array(wdir, float) @ t) * t
        w = w / np.linalg.norm(w)
        n = np.cross(t, w)
        hw, ht = width / 2.0, thick / 2.0
        rings.append(np.array([p + w * hw + n * ht, p - w * hw + n * ht, p - w * hw - n * ht, p + w * hw - n * ht]))
    return _tube_mesh(rings)


def sweep_tube(points, d, seg=10):
    """round lead along a polyline (parallel-transported frame)."""
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
    return _tube_mesh(rings)


def bezier_loop(p0, t0, p3, t3, length, n=40):
    """cubic Bezier from p0 (leaving along t0) to p3 (arriving along t3) whose arc length = length (the spec hinge loop)."""
    p0, p3, t0, t3 = (np.array(v, float) for v in (p0, p3, t0, t3))

    def pts(k):
        c1, c2 = p0 + t0 * k, p3 - t3 * k
        ts = np.linspace(0, 1, n + 1)[:, None]
        return (1 - ts) ** 3 * p0 + 3 * (1 - ts) ** 2 * ts * c1 + 3 * (1 - ts) * ts ** 2 * c2 + ts ** 3 * p3

    def L(k):
        return float(np.linalg.norm(np.diff(pts(k), axis=0), axis=1).sum())
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


def _plen(q):
    return float(np.sum(np.linalg.norm(np.diff(np.array(q, float), axis=0), axis=1)))


def screen_local():
    """Waveshare 7-DSI-TOUCH-C in the cradle frame (x = xr, y = u, z = w): glass / body 166.1 x 101.0 x 8.0, back emboss, connector
    window (recess) with the 22P ZIF and the MX1.25 power header (mouths +x, estimated side), M2.5 corner holes 154 x 88, bottom tab."""
    gw, gh = TS.GLASS
    bt = TS.BODY_T
    em = TS.SC["emboss"]
    win = TS.SC["window"]
    rec0 = bt - TS_EST["recess"]
    body = union([box(-gw / 2, gw / 2, 0.0, gh, 0.0, bt), box(em["xr"][0], em["xr"][1], em["u"][0], em["u"][1], bt - 0.01, bt + em["h"])])
    cuts = [box(win["xr"][0], win["xr"][1], win["u"][0], win["u"][1], rec0, bt + 0.01)]
    for xr in TS.SC["holes"]["xr"]:
        for u in TS.SC["holes"]["u"]:
            cuts.append(cyl_z(xr, u, bt - TS_EST["hole_depth"], bt + 0.01, TS_EST["hole_minor"]))
    f, p = TS.SC["fpc"], TS.SC["pwr"]
    nt = TS.NOTCH
    tw = TS_EST["tab_w"]
    return union([diff(body, cuts),
                  box(f["xr"][0], f["xr"][1], f["u"][0], f["u"][1], rec0 - 0.01, rec0 + TS_EST["zif_h"]),
                  box(p["xr"][0], p["xr"][1], p["u"][0], p["u"][1], rec0 - 0.01, rec0 + TS_EST["mx_h"]),
                  box(nt["feature_xr"][0], nt["feature_xr"][1], -nt["feature_proud"], 0.01, tw[0], tw[1])])


def ffc_path(theta=None):
    """DSI FFC (22P 0.5 mm, 11.7 x 0.3) world solid + centreline pieces + developed length (spec C-6, C-18, A-2, A-5, ribbon.waypoints)."""
    th = TS.TILT_USE if theta is None else theta
    RB = TS.RIBBON
    W, T = RB["ffc_w"], RB["ffc_t"]
    wm = (TS.BODY_T - TS_EST["recess"]) + TS_EST["zif_h"] / 2.0            # w7: ribbon at the ZIF mouth
    f = TS.SC["fpc"]
    fx0, fx1 = TS.CR["fold_square"]["xr"]
    fu0, fu1 = TS.CR["fold_square"]["u"]
    uc = f["pin_u_centre"]
    U0 = TS.CR_U[0]
    wflat = TS.BODY_T + T / 2.0                                              # lying on the screen back (w8.0..8.3)
    M_ = TS.M(th)

    def W_(p):
        return M_ @ np.array([p[0], p[1], p[2], 1.0])

    def D_(d):
        return M_[:, :3] @ np.array(d, float)
    # A: from inside the ZIF (insert 3.5) along +x to the far edge of the fold square (width along u); every piece of a fold stops / starts
    # GAP inside its neighbour so no two faces of the union are coplanar (no zero-area triangles)
    GAP = 0.1
    a_loc = [(f["mouth_xr"] - RB["screen_end_insert"], uc, wm), (fx1 - GAP, uc, wm)]
    A = sweep_rect([W_(q) for q in a_loc], D_((0, 1, 0)), W, T)
    # 45 deg fold: R3 roll at the fold line, clipped to the fold square (shown as the rolled crease of the spec)
    R = RB["fold_roll_R"]
    dvec = (fx1 - fx0, fu0 - fu1)
    Ld = math.hypot(*dvec)
    ang = math.degrees(math.atan2(dvec[1], dvec[0]))
    tube = Manifold.cylinder(Ld + 2 * R, R, R, 48).rotate((0, 90, 0)).translate((-R, 0, 0))
    tube = tube - Manifold.cylinder(Ld + 2 * R + 1, R - T, R - T, 48).rotate((0, 90, 0)).translate((-R - 0.5, 0, 0))
    tube = tube.rotate((0, 0, ang)).translate((fx0, fu1, wm + R - T / 2))
    ins = 0.05
    roll = TS.place(tube ^ box(fx0 + ins, fx1 - ins, fu0 + ins, fu1 - ins, wm - T, wm + 2 * R + 0.2), th)
    # B: down -u along the lane (width along x) on top of A, onto the screen back, out of the groove, hinge loop, lid hole, +y under the lid
    lane = (fx0 + fx1) / 2.0
    wb = wm + TS_EST["stack"]
    rec_u = TS.SC["window"]["u"][0]
    r0, r1 = TS_EST["ramp"]
    b_loc = [(lane, fu1 - GAP, wb), (lane, rec_u + r0, wb), (lane, rec_u + r1, wflat), (lane, U0, wflat)]
    b_w = [W_(q) for q in b_loc]
    wp = [np.array(q, float) for q in RB["waypoints"]]
    zr = RB["z_run"]
    loop, Lloop = bezier_loop(b_w[-1], D_((0, -1, 0)), wp[0], np.array([0, 0, -1.0]), RB["in_cradle_parts"]["hinge_loop"])
    under = [wp[1], np.array([wp[2][0], wp[2][1] + W / 2.0 - GAP, zr])]
    chain = _fillet(list(b_w[:-1]) + list(loop) + under, RB["bend_R"], 8)
    B = sweep_rect(chain, (1.0, 0.0, 0.0), W, T)
    # C: crease-folded under B (z - stack), run -x (width along y), drop in the column x583, R3 onto the micro-HDMI, 19.93 deg into CAM/DISP 1
    zc = zr - TS_EST["stack"]
    mouth = wp[-1]
    q = wp[-2]
    xdrop = wp[3][0]
    corner = mouth + (xdrop - mouth[0]) / (q[0] - mouth[0]) * (q - mouth)
    c_pts = [np.array([wp[2][0] + W / 2.0 - GAP, wp[2][1], zc]), np.array([xdrop, wp[2][1], zc]), corner, mouth,
             mouth + np.array([1.0, 0.0, 0.0]) * RB["pi_end_insert"]]
    c_chain = _fillet(c_pts, RB["bend_R"], 8)
    C = sweep_rect(c_chain, (0.0, 1.0, 0.0), W, T)
    solid = union([A, roll, B, C])
    fc = (fx0 + fx1) / 2.0
    # developed length: A to the fold-square centre + roll (pi R) + B from the square centre (chain starts GAP below the square edge) to
    # the under-lid fold centre + C from that fold centre (sharp crease there; the spec's roll allowance is added separately)
    length = (fc - a_loc[0][0]) + math.pi * R + (_plen(chain) - (fu1 - GAP - uc) - (W / 2.0 - GAP)) + (_plen(c_chain) - (W / 2.0 - GAP))
    return {"solid": solid, "loop": loop, "loop_len": Lloop, "chain": chain, "c_chain": c_chain, "length": length,
            "length_with_lid_roll": length + RB["parts"]["fold_roll_allowance"], "corner": corner, "a_world": [W_(q) for q in a_loc]}


def power_lead(theta=None):
    """screen power lead (MX1.25 2P -> Waveshare 3P cable -> M/M -> F/F jumpers -> GPIO 2 (5 V) / 6 (GND)): 2 leads D1.1 side by side
    (pitch 1.3), each ending in its F jumper housing on its pin (spec C-18, A-5 clip groove, power_wire.waypoints)."""
    th = TS.TILT_USE if theta is None else theta
    p = TS.SC["pwr"]
    uc = (p["u"][0] + p["u"][1]) / 2.0
    lane = TS.CR["wire_xr"]
    lx = (lane[0] + lane[1]) / 2.0
    wm = (TS.BODY_T - TS_EST["recess"]) + TS_EST["mx_h"] / 2.0
    d = TS_EST["wire_d"]
    wfl = TS.BODY_T + d / 2.0 + 0.05
    rec_u = TS.SC["window"]["u"][0]
    r0, r1 = TS_EST["ramp"]
    U0 = TS.CR_U[0]
    wp = [np.array(q, float) for q in TS.PWIRE["waypoints"]]
    gp = (TS.PI5["gpio_pin2"], TS.PI5["gpio_pin6"])
    hd = TS_EST["dupont"]
    z_house_top = TS.PI5["gpio_top_z"] - TS_EST["pin_above_base"] + hd[2]           # 40.6
    M_ = TS.M(th)

    def W_(q):
        return M_ @ np.array([q[0], q[1], q[2], 1.0])
    tubes, lens = [], []
    for k, sgn in ((0, -1), (1, +1)):
        off = sgn * TS_EST["wire_pitch"] / 2.0
        loc = [(p["mouth_xr"] - 2.0, uc + off, wm), (lx + off, uc + off, wm), (lx + off, rec_u + r0, wm), (lx + off, rec_u + r1, wfl), (lx + off, U0, wfl)]
        wl = [W_(q) for q in loc]
        loop, _ = bezier_loop(wl[-1], M_[:, :3] @ np.array([0, -1.0, 0]), np.array([wp[0][0] + off, wp[0][1], wp[0][2]]), np.array([0, 0, -1.0]),
                              TS.RIBBON["in_cradle_parts"]["hinge_loop"])
        gx = gp[k][0]
        under = [np.array([wp[1][0] + off, wp[1][1], wp[1][2]]), np.array([wp[2][0] + off, wp[2][1] + off, wp[2][2]]),
                 np.array([gx, wp[3][1] + off, wp[3][2]]), np.array([gx, wp[3][1], z_house_top - 1.0])]
        chain = _fillet(list(wl[:-1]) + list(loop) + under, 2.0, 6)
        g = gp[k]
        house = box(g[0] - hd[0] / 2, g[0] + hd[0] / 2, g[1] - hd[1] / 2, g[1] + hd[1] / 2, z_house_top - hd[2], z_house_top)
        tubes.append(union([sweep_tube(chain, d, 10), house]))
        lens.append(_plen(chain))
    return {"solids": tubes, "lengths": lens, "house_top": z_house_top}


def touch_parts(out):
    th = TS.TILT_USE
    scl = screen_local()
    src = (TS.SRC_SCR + ": 유리 166.10 × 101.00, 두께 8.0, 보이는 영역 154.58 × 86.42 (아래 테두리 9.65), M2.5 모서리 구멍 154 × 88; "
           + TS.SRC_NUM + " screen (창 xr17.35~43.55 u30.2~70.5, DSI ZIF xr17.85~23.25 u36.5~52.4 입구 +x, MX1.25 xr19.35~24.35 u56.6~65.2, "
           "뒤 볼록판 xr-56.65~14.35 u32.2~71.0 높이 2.1, 아래 끝 돌기 xr54.99~59.24 0.85) + " + TS.SRC_SPEC + " C-4, F (25° 사용 상태)")
    out.add("TS-E-SCREEN", "Waveshare 7-DSI-TOUCH-C 7인치 DSI 정전식 터치 화면", "Waveshare 7-DSI-TOUCH-C 7-inch DSI capacitive touch display", G_TS,
            TS.place(scl, th), SCREEN_BLACK, src,
            note="추정: 커넥터 방향 - 화면 앞에서 볼 때 커넥터 창이 오른쪽, 입구 +x (사양 G-1: 사진 3장으로 판단, 받으면 확인; 반대면 창·홈·구멍·클립을 "
                 "x611 기준으로 뒤집음); 창 깊이 %.1f, ZIF 높이 %.1f, MX1.25 높이 %.1f, 모서리 구멍 깊이 %.1f (안지름 Ø%.1f로 모델 - 나사산 물림), "
                 "아래 끝 돌기 w%.0f~%.0f; 유리 아래 끝 u0이 받침 아래 벽에 얹힘, 뒷면 w8이 보스 4개에 닿음"
                 % (TS_EST["recess"], TS_EST["zif_h"], TS_EST["mx_h"], TS_EST["hole_depth"], TS_EST["hole_minor"], TS_EST["tab_w"][0], TS_EST["tab_w"][1]))
    out.add("TS-E-SCREEN-FOLD", "Waveshare 7-DSI-TOUCH-C - 접은 상태", "Waveshare 7-DSI-TOUCH-C, folded", G_TSF, TS.place(scl, TS.TILT_FOLD),
            SCREEN_BLACK, src + "; C-16 접은 상태 (유리 위로, y235.55~336.55 z94.35)", note="altview")
    rb = ffc_path(th)
    LENGTHS["DSI"] = rb["length"]
    LENGTHS["DSI_WITH_LID_ROLL"] = rb["length_with_lid_roll"]
    RB = TS.RIBBON
    out.add("TS-C-DSI", "DSI FFC 22핀 0.5 mm 300 mm B형 (GUOCONN, 화면 → Pi 5 CAM/DISP 1)", "DSI FFC 22-pin 0.5 mm 300 mm type B (screen -> Pi 5 CAM/DISP 1)",
            G_TS, rb["solid"], FFC_ORANGE,
            TS.SRC_SPEC + " C-6·C-7·C-18 (화면 ZIF 입구 +x → 45° 말아 접기 R3 → −u → 아래 홈 → 경첩 고리 23.04 → 뚜껑 구멍 → 뚜껑 밑 z61.2 +y → 45° 접기 "
            "→ −x → 기둥 x583 → HDMI 위 z27.45 → 19.93°로 입구, 2.7 꽂음) + " + TS.SRC_NUM + " ribbon (waypoints, ribbon_table) + t06",
            note="추정: 폭 %.1f × 두께 %.1f; 받침 안 ZIF 입구 w%.0f, 접힌 겹 사이 %.2f(한 몸), 화면 창에서 w%.2f로 올라 화면 뒷면에 붙음; 고리는 길이 %.2f 3차 "
                 "베지어; 뚜껑 밑 접기는 날카로운 접기로 그림(말아 접기 여유 %.2f는 길이에 더함); 펼친 길이 모델 %.1f (+ 뚜껑 밑 말아 접기 %.1f = %.1f) / "
                 "W1 계산 %.2f / 케이블 %.0f; 화면 ZIF에 %.1f, Pi 쪽 CAM/DISP 1에 %.1f 꽂음"
                 % (RB["ffc_w"], RB["ffc_t"], (TS.BODY_T - TS_EST["recess"]) + TS_EST["zif_h"] / 2.0, TS_EST["stack"], TS.BODY_T + RB["ffc_t"] / 2.0,
                    rb["loop_len"], RB["parts"]["fold_roll_allowance"], rb["length"], RB["parts"]["fold_roll_allowance"], rb["length_with_lid_roll"],
                    RB["total"], RB["cable"], RB["screen_end_insert"], RB["pi_end_insert"]))
    pl = power_lead(th)
    LENGTHS["TS_POWER"] = max(pl["lengths"])
    hd = TS_EST["dupont"]
    for k, (tag, ko, en, col, pin) in enumerate((("RED", "빨강 5 V", "red 5 V", WIRE_RED, 2), ("BLK", "검정 GND", "black GND", BLACK_PLASTIC, 6))):
        out.add("TS-C-PWR-" + tag, "화면 전원선 %s (MX1.25 → 3핀 선 → 점퍼 → Pi GPIO %d번)" % (ko, pin),
                "display power lead %s (MX1.25 -> jumpers -> Pi GPIO pin %d)" % (en, pin), G_TS, pl["solids"][k], col,
                TS.SRC_SPEC + " C-18 (전원선: 입구 +x → 리본 옆 xr40.45~43.45 → 같은 홈·고리·구멍 x654.35 → 클립 전원선 홈 z60.15 → +y → −x → GPIO 2·6) + "
                + TS.SRC_NUM + " power_wire (waypoints, chain: 화면 MX1.25 → Waveshare 3핀 선 → 점퍼 M/M 20 cm → F/F 20 cm → GPIO 2 빨강 / 6 검정) + t06",
                note="추정: 선 Ø%.1f, 두 가닥 간격 %.1f (화면 안·클립 홈 안에서 나란히), 화면 쪽 끝은 MX1.25 안 2 mm, Pi 쪽 F 점퍼 하우징 %.1f × %.1f × %.0f가 "
                     "핀 %d에 (헤더 받침 위 z%.1f~%.1f - 헤더 상자는 핀 끝까지 한 덩어리라 겹침); 길이 모델 %.1f (하우징 윗면 아래 1까지) + 하우징·핀 %.0f + "
                     "꽂는 여유 15 ≈ %.0f / W1 계산 %.2f / 있는 길이 %.0f~%.0f (점퍼 20 cm × 2 + Waveshare 3핀 선 약 100~150)"
                     % (TS_EST["wire_d"], TS_EST["wire_pitch"], hd[0], hd[1], hd[2], pin, pl["house_top"] - hd[2], pl["house_top"], pl["lengths"][k],
                        pl["house_top"] - TS.PI5["gpio_top_z"] + 1.0, pl["lengths"][k] + pl["house_top"] - TS.PI5["gpio_top_z"] + 1.0 + 15.0,
                        TS.PWIRE["total"], TS.PWIRE["available"][0], TS.PWIRE["available"][1]))


# ------------------------------------------------------------------ entry point

def build():
    M = _load("electronics_modules.json")
    R = _load("electronics_rearbar.json")
    F = _load("keyaction_features_frame.json")
    out = Out()
    LENGTHS.clear()
    plan = cable_plan()
    module_parts(M, out, plan)
    end_parts(M, out)
    pi = pi_parts(out)
    dongle_parts(out, pi)
    ped_axis = board_parts(M, F, out)
    LENGTHS.update(plan["_len"])
    LENGTHS["PED"] = ped_cable(M, out, ped_axis)
    LENGTHS["UPSTREAM"] = hub_upstream(out, pi)
    hub_bank_parts(R, out)
    power_parts(out)
    P = xt30_parts(R, out)
    speaker_leads(out, P)
    speaker_parts(R, out)
    headphone_jack(F, out)
    pedal_part(R, out)
    touch_parts(out)
    return list(out)


if __name__ == "__main__":
    ps = build()
    for p in ps:
        b = p.solid.bounding_box()
        print("%-18s %-12s %-14s %6d  %s" % (p.id, p.kind, p.group, len(p.solid.decompose()), " ".join("%.2f" % v for v in b)))
    print(len(ps), "parts")
    print("lengths:", {k: round(v, 1) for k, v in LENGTHS.items()})
