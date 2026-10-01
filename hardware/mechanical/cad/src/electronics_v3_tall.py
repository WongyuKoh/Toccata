"""Toccata electronics as Part instances (world coordinates, assembled pose).

Sources (the only numeric sources):
  spec/electronics_modules.json   boards / modules / cables inside the 7 octave modules and the 2 end parts
  spec/electronics_rearbar.json   rear-bar electronics, speakers, damper pedal (envelope SIZES)
  spec/body_centre_unit.json      CU-bay re-layout (component POSITIONS / heights, I/O-plate hole positions)
  spec/keyaction_features_frame.json  left-cheek headphone-jack pocket (J701) + the PJ-313 envelope (SHOU HAN PJ-313 5JCJ
                                  jack_dims) used for ALL three PJ-313 jacks (J701, J501, J702)
  spec/body_speakers.json         XT30 holders (XT30 pair positions)

Shown: boards as plain rectangles with their mounting holes / U-slots (no 2.54 grid - "perfboard = just a
rectangle"), and only the bulky parts on them (RP2040-Zero, mux module, bought modules, jacks, switch,
connectors, cables). Omitted on purpose: every spec item/box with show:false, hall sensors (their pockets are in
the sensor bar), key magnets and control-board M3x6 screws (keyaction_parts.py emits them), resistors / caps /
headers / pads, the board screws of the CU bay (fasteners F05..F10 of body_centre_unit.json - body parts).

Module items: world x = 47 + 164.5 (k-1) + local x (k = 1..7). End items: left = world x, right = 1198.5 + x.
"""
import json
import math
import os

from manifold3d import Manifold

from cadlib import box, cyl_x, cyl_y, cyl_z, diff, prism_x, prism_y, union
from parts import COLORS, Part

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

MODULE_W = 164.5
X_O1 = 47.0
X_RIGHT = 1198.5

PI5_GREEN = "#1f7a3f"
BLACK_PLASTIC = "#222222"
XT30_YELLOW = "#e6b422"
WHITE_PLASTIC = "#ececec"
HUB_GREY = "#3b3f45"
BANK_GREY = "#c9ccd1"

# Raspberry Pi 5 port edge (+x): (id suffix, name_ko, name_en, centre from the power/HDMI edge, width along y, depth along x
# incl. the overhang, height above the PCB). Order from the power/HDMI edge: RJ45, USB-A stack, USB-A stack (Pi 5).
PI_PORT_OVERHANG = 2.5
PI_PORTS = [
    ("RJ45", "라즈베리파이 5 RJ45 이더넷 잭 (안 씀)", "Raspberry Pi 5 RJ45 Ethernet jack (unused)", 10.25, 16.0, 21.25, 13.5),
    ("USBA1", "라즈베리파이 5 USB-A 2단 (RJ45 옆 - 아래: 동글 젠더)", "Raspberry Pi 5 USB-A stack next to the RJ45 (lower: dongle gender)",
     29.0, 14.5, 17.5, 16.4),
    ("USBA2", "라즈베리파이 5 USB-A 2단 (GPIO 쪽 - 위: 허브 업스트림)", "Raspberry Pi 5 USB-A stack at the GPIO edge (upper: hub upstream)",
     47.0, 14.5, 17.5, 16.4),
]

SRC_M = "spec/electronics_modules.json"
SRC_R = "spec/electronics_rearbar.json"
SRC_C = "spec/body_centre_unit.json"


def _load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


# ------------------------------------------------------------------ small geometry helpers

def bx(b, dx=0.0, dy=0.0, dz=0.0):
    """spec box {x:[..], y:[..], z:[..]} -> solid (optionally shifted)."""
    return box(b["x"][0] + dx, b["x"][1] + dx, b["y"][0] + dy, b["y"][1] + dy, b["z"][0] + dz, b["z"][1] + dz)


def cyl(c, dx=0.0, dy=0.0, dz=0.0):
    """spec cylinder {axis, center, d, range} -> solid."""
    a, (p, q), d, (r0, r1) = c["axis"], c["center"], c["d"], c["range"]
    if a == "z":
        return cyl_z(p + dx, q + dy, r0 + dz, r1 + dz, d)
    if a == "y":
        return cyl_y(p + dx, q + dz, r0 + dy, r1 + dy, d)
    return cyl_x(p + dy, q + dz, r0 + dx, r1 + dx, d)


def shown(items):
    return [i for i in items if i.get("show", True) is not False]


def tube(points, d, seg=16):
    """cable: hull of spheres along a polyline (rounded joints and ends)."""
    r = d / 2.0
    balls = [Manifold.sphere(r, seg).translate(tuple(float(v) for v in p)) for p in points]
    segs = [Manifold.batch_hull([balls[i], balls[i + 1]]) for i in range(len(balls) - 1)]
    return union(segs)


def arc_pts(cx, cy, z, r, a0, a1, n=10):
    """points on an arc in the xy plane at height z, angles in degrees."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), z) for i in range(n + 1)]


def notched_envelope(x0, x1, y0, y1, z0, z1, c):
    """parts envelope of a bought module with its 4 corner squares (c x c) left free for the screws."""
    return diff(box(x0, x1, y0, y1, z0, z1),
                [box(x0 - 1, x0 + c, y0 - 1, y0 + c, z0 - 1, z1 + 1), box(x1 - c, x1 + 1, y0 - 1, y0 + c, z0 - 1, z1 + 1),
                 box(x0 - 1, x0 + c, y1 - c, y1 + 1, z0 - 1, z1 + 1), box(x1 - c, x1 + 1, y1 - c, y1 + 1, z0 - 1, z1 + 1)])


def stadium_xz(cx, cz, w, h, ang_deg):
    """slot outline (length w along the direction ang, width h) in the xz plane."""
    r = h / 2.0
    L = (w - h) / 2.0
    a = math.radians(ang_deg)
    ux, uz = math.cos(a), math.sin(a)
    pts = []
    for end, sgn in ((1, 1), (-1, -1)):
        ex, ez = cx + ux * L * end, cz + uz * L * end
        base = math.atan2(uz, ux) - math.pi / 2 if end == 1 else math.atan2(uz, ux) + math.pi / 2
        for i in range(17):
            t = base + math.pi * i / 16
            pts.append((ex + r * math.cos(t), ez + r * math.sin(t)))
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


# ------------------------------------------------------------------ board helpers

def board_with_cuts(item, dx=0.0):
    """union of the item's boxes minus its cut cylinders / u_slot_cut boxes (module / end-part boards)."""
    solid = union([bx(b, dx) for b in item["boxes"]])
    # cut cylinders / U-slot boxes span exactly the board thickness: extend them 0.01 so the boolean is clean
    b0 = min(b["z"][0] for b in item["boxes"]) - 0.01
    b1 = max(b["z"][1] for b in item["boxes"]) + 0.01
    cuts = [cyl_z(c["center"][0] + dx, c["center"][1], b0, b1, c["d"])
            for c in item.get("cylinders", []) if c.get("cut") and c["axis"] == "z"]
    cuts += [box(b["x"][0] + dx - 0.01, b["x"][1] + dx, b["y"][0], b["y"][1], b0, b1)
             for b in item.get("u_slot_cut", []) if b.get("cut")]
    return diff(solid, cuts)


# ------------------------------------------------------------------ module + end-part electronics

def module_parts(M, out, cable_plan):
    it = {i["id"]: i for i in M["module_items"]}
    for k in range(1, 8):
        X0 = X_O1 + MODULE_W * (k - 1)
        g = "O%d 전자부" % k
        tag = "O%d" % k

        # control board MB (70 x 50 perfboard with the fin slot + 2 screw holes + 2 pin holes)
        mb = it["mb_board"]
        out.add("%s-E-MB" % tag, "제어 기판 MB (5×7 양면 만능기판, 70×50×1.6) %s" % tag,
                "control board MB (perfboard 70x50x1.6) " + tag, g, board_with_cuts(mb, X0), COLORS["pcb_perf"],
                SRC_M + " mb_board; " + mb["source"], material="FR4 만능기판")

        # sensor board SB (strip under the sensor bar, 2 U-slots at the left end)
        sb = it["sb_board"]
        out.add("%s-E-SB" % tag, "센서 기판 SB (6행 양면 도트 띠 161.6 × 15.24 × 1.6) %s" % tag,
                "sensor board SB " + tag, g, board_with_cuts(sb, X0), COLORS["pcb_perf"],
                SRC_M + " sb_board; " + sb["source"],
                note="추정: U홈이 왼쪽 끝으로 열림 (spec assumed: " + sb["assumed_note"] + ")", material="FR4 만능기판")

        # RP2040-Zero on pin headers: PCB + underside chip block (fills the 1.3 gap, rests on the MB) + top parts + USB-C
        z = it["zero"]
        out.add("%s-E-ZERO" % tag, "RP2040-Zero (A301), 핀 헤더로 세움 %s" % tag, "RP2040-Zero (A301) " + tag, g,
                union([bx(b, X0) for b in z["boxes"]]), COLORS["pcb_blue"], SRC_M + " zero; " + z["source"],
                note="추정: 윗면 부품 덩어리 x75.64~92.64 y172.5~189.5 z≤16.3과 밑면 칩 덩어리 z10.6~11.9 (spec assumed 분할); "
                     "핀 헤더 1×9 ×2는 작은 부품이라 뺌")

        # CD74HC4067 mux module: PCB + the two header plastic spacers (chip on top = small, omitted)
        mx = it["mux"]
        mxb = [b for b in mx["boxes"] if "SSOP" not in b["label"]]
        out.add("%s-E-MUX" % tag, "CD74HC4067 16채널 먹스 모듈 (A302), 핀 헤더로 세움 %s" % tag,
                "CD74HC4067 mux module (A302) " + tag, g, union([bx(b, X0) for b in mxb]), COLORS["pcb_green"],
                SRC_M + " mux; " + mx["source"],
                note="추정: 헤더 몰드 2.5 높이 (spec assumed: " + mx["assumed_note"] + ")")

        # 16-core ribbon SB J201 -> MB J301
        rb = it["ribbon"]
        out.add("%s-C-RIBBON" % tag, "16심 리본 W10%d (SB J201 → MB J301)" % k, "16-core ribbon W10%d" % k, "케이블",
                union([bx(b, X0) for b in rb["boxes"]]), COLORS["cable"], SRC_M + " ribbon; " + rb["source"],
                note="남는 길이(자른 길이 180 − 경로 85)는 접어 둠, 모델에 없음 (spec note)")

        # EXT lead (O1, O7 only): spec boxes inside the module + a simple tube on the passage floor to its XH pair
        if tag in it["ext_lead"]["modules"]:
            el = it["ext_lead"]
            wid = {"O1": "W403", "O7": "W413"}[tag]
            out.add("%s-C-EXT" % tag, "EXT 연장선 %s (L66 모듈 쪽 150 mm, 6심 22 AWG)" % wid, "EXT lead %s" % wid, "케이블",
                    diff(union([bx(b, X0) for b in el["boxes"]] + [tube(ext_floor_path(tag, X0), 3.0)]),
                         [bx(b, X0) for b in mb["boxes"]]), COLORS["cable"],
                    SRC_M + " ext_lead + xh_left/xh_right (mated XH on the passage floor); " + el["source"],
                    note="추정: 묶음 단면 약 8×2와 띠 안의 x 위치 (spec assumed; spec 상자 y195.4~가 MB 끝 y195.5와 0.1 겹쳐 MB 자리를 뺌); 뒷벽 구멍(y212)부터 XH 짝까지는 "
                         "지름 3 선으로 통로 바닥(z0~3)에 눕혀 XT30 받침(z8~22) 밑으로 지나게 함 - 경로는 보기용")

        # USB-C plug + cable to the hub (one part: plug overmold + cable + hub-end USB-A plug)
        up = it["usb_plug"]
        plug = bx(up["boxes"][0], X0)
        cab = tube(cable_plan[tag], 3.5)
        hub_plug = cable_plan[tag + "_hubplug"]
        port = HUB_PORT[tag]
        ln = cable_plan["_len"][tag]
        out.add("%s-C-USB" % tag, "USB-C 케이블 W20%d (Coms NA993, %s → 허브)" % (k, tag), "USB cable W20%d %s to hub" % (k, tag),
                "케이블", union([plug, cab, hub_plug]), COLORS["cable"],
                SRC_M + " usb_plug + usb_cable (bend R25, run y246.8); " + SRC_C + " inlet / keep_out inlet_rise / low divider crossing; "
                + SRC_R + " cables_simple (hub plug z50) + usb_hub_710u3 note (hub against the back wall y350.5..398.5); BOM C04 NA993 1 m",
                note="추정: 케이블 OD 3.5, 통로 바닥 줄(y246.8/250.8/254.8), CU 칸 입구 y231.75로 올라와 z93에서 낮은 칸막이를 넘어 "
                     "허브 앞면(y%.1f, z%.0f) 포트 %d(x%.0f, 허브 포트 x760+22i 가정 - 입구 쪽 -x 끝부터 O7·O6·O1·O2·O3·O4·O5·PED)에 "
                     "USB-A 플러그(16×8×20)로 꽂힘; 길이 = 플러그 25 + 경로 %.1f + 허브 플러그 20 = %.1f mm (NA993 1 m 이하, 여유 %.1f) - 경로는 보기용"
                     % (HUB_Y, HUB_Z, port, HUB_PORT_X[port], ln - MODULE_PLUG_L - HUB_PLUG_L, ln, USB_CABLE_MAX - ln))


def end_parts(M, out):
    it = {i["id"]: i for i in M["end_items"]}
    # boards
    for iid, side, dx, tag in (("el_board", "왼쪽", 0.0, "EL"), ("er_board", "오른쪽", X_RIGHT, "ER")):
        b = it[iid]
        out.add("%s-E-BOARD" % tag, b["name_ko"], b["name_en"], "끝 부속 %s 전자부" % side, board_with_cuts(b, dx),
                COLORS["pcb_perf"], SRC_M + " " + iid + "; " + b["source"],
                note="추정: U홈 Ø3.4가 왼쪽 끝으로 열림 (spec assumed)", material="FR4 만능기판")
    # leads: spec boxes inside the end part + a thin strip on the passage floor to the XH pair (xh_* lead box is show:false)
    for iid, dx, tag in (("el_lead", 0.0, "EL"), ("er_lead", X_RIGHT, "ER")):
        b = it[iid]
        out.add("%s-C-LEAD" % tag, b["name_ko"], b["name_en"], "케이블",
                union([bx(q, dx) for q in shown(b["boxes"])] + [tube(lead_floor_path(tag), 2.0)]),
                COLORS["cable"], SRC_M + " " + iid + " + xh_left/xh_right lead drop (y212..231, passage floor); " + b["source"],
                note="추정: 뒷벽 노치(y212)에서 통로 바닥으로 내려 XH 짝 끝면까지 지름 2 선으로 표시 (실제는 폭 %s 리본 띠) - 경로는 보기용"
                     % ("6.35" if tag == "EL" else "3.81"))
    # JST-XH mated pairs (world coords; the show:false lead box is omitted)
    for iid, tag in (("xh_left", "L"), ("xh_right", "R")):
        b = it[iid]
        out.add("C-XH-%s" % tag, b["name_ko"], b["name_en"], "케이블", union([bx(q) for q in shown(b["boxes"])]),
                "#f2f2ee", SRC_M + " " + iid + "; " + b["source"],
                note="추정: 느슨한 커넥터 - 위치·높이·길이 (spec assumed: " + b["assumed_note"][:120] + ")")


# ------------------------------------------------------------------ cable plan (module USB cables, PED, upstream)

RISE_Y = 231.75           # CU tray inlet: opening into the bay y226.5..237 (front panel y215..226.5 over the slot)
TOP_Z = 93.0              # over the low divider (top z90.5) and under the lid corner supports (z98.5)
FLOOR_Z = 1.75            # OD 3.5 lying on the desk in the cable channel
RISE_CHAMFER = 12.0       # 45 deg corner where the rise meets the z93 run (inside keep-out inlet_rise, clear of the lid supports)
# hub 710U3 taped to the power-bank bay back wall (v3 A18 / BOM L17; electronics_rearbar usb_hub_710u3 note
# "alternative y350.5-398.5 (touching the wall)"): 228 x 48 x 24 lying flat, x750..978 (drawing 10), y350.5..398.5
HUB_BACK = 398.5          # power-bank bay inner rear face (back_R CU-P07 front face)
HUB_Y = HUB_BACK - 48.0   # hub front face y350.5 - the downstream ports face -y into the bay
HUB_Z = 50.0              # plug height at the hub (electronics_rearbar cables_simple)
HUB_PORT_X = [760.0 + 22.0 * i for i in range(10)]   # 10 downstream ports on the front face, pitch 22 (assumed)
# port use: O7 / O6 (longest runs, from the right end) take the two ports nearest the CU tray inlet (hub -x end),
# then O1 (the other long run), O2, O3, O4, O5, PED; ports 8, 9 spare
HUB_PORT = {"O7": 0, "O6": 1, "O1": 2, "O2": 3, "O3": 4, "O4": 5, "O5": 6, "PED": 7}
USB_CABLE_MAX = 1000.0    # Coms NA993 USB-A to C, 1 m (BOM C04)
MODULE_PLUG_L = 25.0      # USB-C overmold envelope along y (electronics_modules usb_plug y196.8..221.8)
HUB_PLUG_L = 20.0         # USB-A overmold at the hub (hub_plug below)


XH_L = (52.0, 69.4)       # electronics_modules xh_left  x (y222..240, z0..6)
XH_R = (1160.0, 1177.4)   # electronics_modules xh_right x
XH_Y = 231.0              # middle of the XH housing (y222..240)


def ext_floor_path(tag, X0):
    """EXT lead from the module rear-wall opening (local x82..91, z5..10.7 at y212) down to the passage floor and
    along it to the module-side end face of the XH pair (O1 -> -x to X402 at x69.4, O7 -> +x to X412 at x1160).
    The first two points keep the tube above the opening floor z5 until it has left the rear wall (y>212)."""
    x = X0 + 86.5
    r = 1.5
    if tag == "O1":
        return [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, r), (x - 8.0, 226.0, r), (XH_L[1] + r, XH_Y, r)]
    return [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, r), (x + 8.0, 226.0, r), (XH_R[0] - r, XH_Y, r)]


def lead_floor_path(tag):
    """EL / ER flat lead from the end-part rear-wall notch (z5..5.89 at y212) down to the passage floor and to the
    end-part side of the XH pair (EL -> x52, ER -> x1177.4)."""
    r = 1.0
    if tag == "EL":
        x = (14.825 + 21.175) / 2.0
        return [(x, 212.0, 6.0), (x, 213.0, 6.0), (x, 216.0, r), (x + 6.0, 226.0, r), (XH_L[0] - r, XH_Y, r)]
    x = X_RIGHT + (8.885 + 12.695) / 2.0
    return [(x, 212.0, 6.0), (x, 213.0, 6.0), (x, 216.0, r), (x - 6.0, 226.0, r), (XH_R[1] + r, XH_Y, r)]


def hub_plug(xh):
    """USB-A plug overmold 16 x 8 x 20 in front of the hub face (assumed)."""
    return box(xh - 8.0, xh + 8.0, HUB_Y - 20.0, HUB_Y, HUB_Z - 4.0, HUB_Z + 4.0)


def hub_approach(xh, lane):
    """drop from the z93 lane (step down to z84 first, under the other lanes) to the plug on the hub front face.
    The middle point stays behind y322.5 below z75 so the cable clears the battery-holder max envelope
    (PR-PB-HOLDER battery_pocket y..316.5, z..70.5) by more than the cable radius."""
    ya = max(322.5, min(lane, 326.0))
    return [(xh, lane, TOP_Z), (xh, lane, 84.0), (xh, ya, 72.5), (xh, HUB_Y - HUB_PLUG_L, HUB_Z)]


def path_len(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def cable_plan():
    """non-crossing paths: a cable that rises further left takes a lane further back (+y) over the CU bay; each cable
    drops to its hub port below the z93 lanes (z84 and lower), so a drop crossing another lane in plan is 9+ mm under it."""
    rise_x = {"O3": 580.0, "O2": 584.5, "O1": 589.0, "O4": 599.5, "O7": 641.0, "O6": 645.5, "O5": 650.0}
    lane = {"O3": 336.0, "O2": 331.5, "O1": 327.0, "PED": 318.0, "O4": 313.5, "O7": 309.0, "O6": 304.5, "O5": 300.0}
    run_y = {"O1": 254.8, "O2": 250.8, "O3": 246.8, "O5": 246.8, "O6": 250.8, "O7": 254.8}
    x_hub = {t: HUB_PORT_X[i] for t, i in HUB_PORT.items()}
    plan = {"_len": {}}
    for k in range(1, 8):
        t = "O%d" % k
        xc = X_O1 + MODULE_W * (k - 1) + 84.0
        s = 1.0 if k <= 3 else -1.0
        # bend R25 in the passage at z14.5 (module spec usb_cable sweep): centre (xc + 25 s, 221.8)
        cx = xc + 25.0 * s
        if s > 0:
            pts = arc_pts(cx, 221.8, 14.5, 25.0, 180.0, 90.0)
        else:
            pts = arc_pts(cx, 221.8, 14.5, 25.0, 0.0, 90.0)
        xr = rise_x[t]
        if t == "O4":
            pts += [(xr, 240.0, 15.5), (xr, RISE_Y, 20.0)]
        else:
            x_floor = cx + 50.0 * s     # ~50 mm to reach the passage floor
            pts += [(x_floor, run_y[t], FLOOR_Z), (xr, run_y[t], FLOOR_Z), (xr, RISE_Y, FLOOR_Z)]
        pts += [(xr, RISE_Y, TOP_Z - RISE_CHAMFER), (xr, RISE_Y + RISE_CHAMFER, TOP_Z), (xr, lane[t], TOP_Z), (x_hub[t], lane[t], TOP_Z)]
        pts += hub_approach(x_hub[t], lane[t])[1:]
        plan[t] = pts
        plan[t + "_hubplug"] = hub_plug(x_hub[t])
        # cable length = module plug overmold + path (plug end y221.8 -> hub plug end) + hub plug overmold
        plan["_len"][t] = MODULE_PLUG_L + path_len(pts) + HUB_PLUG_L
    plan["_lane"] = lane
    plan["_xhub"] = x_hub
    return plan


# ------------------------------------------------------------------ rear bar (CU bay, power-bank bay, I/O plate, speakers, pedal)

def rearbar_parts(R, C, F, S, out, plan):
    tray = next(p for p in C["printed"] if p["id"] == "PR-CU-TRAY")
    feat = {f["name"]: f for f in tray["features"]}
    comp = {c["name_ko"]: c["box"] for c in tray["components"]}
    io = next(p for p in C["printed"] if p["id"] == "PR-IO-PLATE")
    iof = {f["name"]: f for f in io["features"]}
    g = "CU 칸 전자부"

    # ---- Raspberry Pi 5 (position / heights: centre-unit re-layout; envelope split: electronics_rearbar)
    pb = comp["라즈베리파이 5"]                           # x531..616 y336..392 z39.5..57.5
    x0, x1, y0, y1 = pb["x"][0], pb["x"][1], pb["y"][0], pb["y"][1]
    zb0, zb1 = 39.5, 41.1                               # board z39.5..41.1 (feature pi5_bosses note)
    pcb = diff(box(x0, x1, y0, y1, zb0, zb1), [cyl_z(p[0], p[1], zb0 - 0.01, zb1 + 0.01, 2.7) for p in feat["pi5_bosses"]["at"]])
    # GPIO header 2x20 on the +y edge (row 3.5 from the edge, centred 32.5 from the non-port edge) - Pi drawing
    hdr = box(x0 + 32.5 - 25.4, x0 + 32.5 + 25.4, y1 - 3.5 - 2.54, y1 - 3.5 + 2.54, zb1, zb1 + 8.5)
    # SoC passive heatsink (L02): 15 x 15, top <= 10 above the PCB (rearbar top envelope)
    hs = box(x0 + 21.5, x0 + 36.5, y0 + 17.5, y0 + 32.5, zb1, zb1 + 8.0)
    out.add("CU-E-PI5", "라즈베리파이 5 2GB", "Raspberry Pi 5 2GB", g, union([pcb, hdr, hs]), PI5_GREEN,
            SRC_C + " PR-CU-TRAY components/pi5_bosses (x531..616 y336..392, board z39.5..41.1); " + SRC_R + " pi5 (L01)",
            note="추정: GPIO 헤더 2×20 (가장자리 3.5, 비포트 쪽 끝에서 32.5 중심)과 SoC 방열판 15×15×8 (L02 높이 미표기) 위치; "
                 "USB-C 전원·micro-HDMI(-y 가장자리)는 작아서 뺌")
    # ---- Pi 5 port edge (+x, x616): from the power/HDMI edge (-y, y336) RJ45, USB-A stack 1, USB-A stack 2
    # (Pi 5 layout: Ethernet next to the power/HDMI edge, both USB-A stacks toward the GPIO edge). Three separate parts
    # (each is its own soldered component; one part per housing keeps every part one body).
    face = x1 + PI_PORT_OVERHANG                          # port faces x618.5
    ports = {}
    for key, name_ko, name_en, yc_off, w, depth, h in PI_PORTS:
        yc = y0 + yc_off
        ports[key] = yc
        out.add("CU-E-PI5-" + key, name_ko, name_en, g,
                box(face - depth, face, yc - w / 2, yc + w / 2, zb1, zb1 + h), COLORS["metal"],
                SRC_C + " PR-CU-TRAY pi5_bosses note (USB/Ethernet end at x616 faces +x, power/HDMI edge y336 faces -y; ports to z57.5); "
                + SRC_R + " pi5 box 'USB-A x2 stacks + RJ45 block' (tallest 16.5 above the PCB, overhang 2.5)",
                note="추정: Pi 5 포트 가장자리 순서(전원·HDMI 가장자리 쪽부터 RJ45, USB-A 2단, USB-A 2단)와 중심(전원 가장자리에서 "
                     "RJ45 10.25 · USB-A 29 · 47, Pi 3B+ 도면 값 - Pi 5 도면으로 확인), 크기 RJ45 16×21.25×13.5, USB-A 2단 14.5×17.5×16.4, "
                     "보드 끝에서 2.5 튀어나옴(x%.1f); 이 포트 중심 y%.2f" % (face, yc))
    y_s1, y_s2 = ports["USBA1"], ports["USBA2"]           # y365, y383

    # ---- USB dongle (L51) + IH190 gender (L52): gender in the LOWER port of the USB-A stack next to the RJ45
    gy0, gy1 = y_s1 - 8.0, y_s1 + 8.0                     # 16 wide on the port centre y365 -> y357..373
    gender = box(face, face + 18.0, gy0, gy1, 42.5, 49.0)
    out.add("CU-E-GENDER", "IH190 USB-C(F)→USB-A(M) ㄱ자 젠더 (L52)", "Coms IH190 left-angle gender (L52)", g, gender,
            BLACK_PLASTIC, SRC_R + " usb_dongle (gender 18×16×6.5); " + SRC_C + " keep_out pi_usb_plugs x616..662 y336..392 z39.5..75 "
            "(components 'USB 동글 + 젠더' y340..360 is where the Pi 5 RJ45 sits - superseded)",
            note="추정: RJ45 옆 USB-A 2단(중심 y%.0f)의 아래 포트(z42.5~49)에 꽂음, y%.0f~%.0f; C 소켓이 -y(RJ45 앞 빈자리)를 향함" % (y_s1, gy0, gy1))
    # dongle: USB-C plug 6.5 into the gender socket, head toward -y in front of the (unused) RJ45, cable drops onto the
    # tray (z33.5) under the gender, runs +y and turns into the 3.5 mm socket head lying on the tray along y
    # (x646..656.5, mouth at y345 for cable ① W701) - everything inside the tray keep-out pi_usb_plugs (x616..662 y336..392)
    head = box(621.0, 629.5, gy0 - 17.5, gy0 + 6.5, 42.75, 48.75)
    sock = cyl_y(651.25, 38.75, 345.0, 370.0, 10.5)
    loop = tube([(625.25, gy0 - 17.0, 45.75), (626.5, 337.6, 41.0), (632.0, 338.0, 36.0), (640.0, 345.0, 35.0),
                 (641.5, 372.0, 35.0), (647.0, 377.5, 36.5), (651.25, 376.0, 38.75), (651.25, 369.5, 38.75)], 3.0)
    out.add("CU-E-DONGLE", "Apple USB-C → 3.5 mm 어댑터 (L51)", "Apple USB-C to 3.5 mm adapter (L51)", g,
            union([head, sock, loop]), WHITE_PLASTIC,
            SRC_R + " usb_dongle (head 8.5×6×24 incl. plug, jack head ~Ø10.5×25, cable ~7 cm); " + SRC_C + " keep_out pi_usb_plugs",
            note="추정: 머리 x621~629.5 y%.1f~%.1f z42.75~48.75 (C 플러그 6.5가 젠더 소켓 안), 케이블은 트레이 윗면으로 내려가 "
                 "젠더 밑(z33.5~36.5)을 지나 +y로 돌아 3.5 mm 소켓 머리(트레이 위 y 방향 x646~656.5 y345~370)의 +y 끝에 들어감 - "
                 "모두 트레이 keep-out x616~662 y336~392 안; 케이블 ① W701은 소켓 -y 끝에 꽂힘 - 케이블 ①·②는 모델에 없음"
                 % (gy0 - 17.5, gy0 + 6.5))
    pi_ports = {"face": face, "y_s1": y_s1, "y_s2": y_s2}

    # ---- XH-A232 amp (x664..710 y334..388, 46 along x; board z38.5..40.1, parts to z52.5)
    ab = comp["앰프 보드"]
    amp_b = diff(box(ab["x"][0], ab["x"][1], ab["y"][0], ab["y"][1], 38.5, 40.1),
                 [cyl_z(p[0], p[1], 38.49, 40.11, 3.2) for p in feat["amp_bosses"]["at"]])
    amp_e = notched_envelope(ab["x"][0], ab["x"][1], ab["y"][0], ab["y"][1], 40.1, ab["z"][1], 7.0)
    out.add("CU-E-AMP", "XH-A232 (HW-404) TPA3110 2×15 W 앰프 보드", "XH-A232 (HW-404) TPA3110D2 amplifier board", g,
            union([amp_b, amp_e]), COLORS["pcb_blue"],
            SRC_C + " PR-CU-TRAY amp_bosses / components (x664..710 y334..388 z38.5..52.5); " + SRC_R + " amp_xh_a232 (54×46×14, L53)",
            note="추정: 부품은 모서리 7×7(나사 자리)을 뺀 한 덩어리 z40.1~52.5; 구멍 Ø3.2는 보스 자리(모서리 3.5 안) - 받은 보드로 확인")

    # ---- XL4016 buck (x608..668.8 y246..286.3, board z38.5..40.1, top z67.5)
    kb = comp["5.1 V 강압 모듈"]
    buck_b = diff(box(kb["x"][0], kb["x"][1], kb["y"][0], kb["y"][1], 38.5, 40.1),
                  [cyl_z(p[0], p[1], 38.49, 40.11, 3.2) for p in feat["buck_bosses"]["at"]])
    buck_e = notched_envelope(kb["x"][0], kb["x"][1], kb["y"][0], kb["y"][1], 40.1, kb["z"][1], 6.5)
    out.add("CU-E-BUCK", "XL4016 강압 모듈 XH-M401 (20 V → 5.1 V)", "XL4016 buck module XH-M401", g, union([buck_b, buck_e]),
            COLORS["pcb_blue"], SRC_C + " PR-CU-TRAY buck_bosses / components (x608..668.8 y246..286.3 z38.5..67.5); "
            + SRC_R + " buck_xl4016 (60.8×40.3×29, L58)",
            note="추정: 방열판 2·코일·캐패시터를 모서리 6.5×6.5를 뺀 한 덩어리(z40.1~67.5)로 표시")

    # ---- PED pedal board PB (5x7 perfboard 70 x 50 at x531..601 y244..294, board z38.5..40.1) + RP2040-Zero
    pf = feat["ped_board_standoffs"]
    ped_b = diff(box(531.0, 601.0, 244.0, 294.0, 38.5, 40.1),
                 [cyl_z(p[0], p[1], 38.49, 40.11, 3.2) for p in pf["screw_at"]] + [cyl_z(p[0], p[1], 38.49, 40.11, 3.0) for p in pf["pin_at"]])
    out.add("CU-E-PEDBOARD", "PED 페달 보드 (5×7 cm 만능기판 70×50)", "PED pedal board PB (5x7 perfboard)", g, ped_b, COLORS["pcb_perf"],
            SRC_C + " PR-CU-TRAY ped_board_standoffs (board x531..601 y244..294 z38.5..40.1, M3 Ø3.2 ×2, pin Ø3.0 ×2); " + SRC_R + " ped_board",
            material="FR4 만능기판")
    return comp, feat, iof, pi_ports


PED_SHIFT = (578.0 - 75.14, 262.0 - 172.0, 40.1 - 10.6)   # MB Zero layout moved onto the PED board (USB edge +y)


def ped_zero_parts(M, out):
    it = {i["id"]: i for i in M["module_items"]}
    z = it["zero"]
    dx, dy, dz = PED_SHIFT
    zb = z["boxes"]
    out.add("CU-E-PEDZERO", "RP2040-Zero (PED 보드, 페달용)", "RP2040-Zero on the PED board", "CU 칸 전자부",
            union([bx(b, dx, dy, dz) for b in zb]), COLORS["pcb_blue"], SRC_M + " zero (same part/stack as the MB) ; SEV2",
            note="추정: PED 보드 위 x578~596 y262~285.5, USB가 +y (Pi 전원·HDMI 플러그 자리 x531~580과 입구 상승 구역을 피함), "
                 "MB와 같은 1.3 틈 핀 헤더 실장")
    plug = bx(it["usb_plug"]["boxes"][0], dx, dy, dz)     # x580.61..593.11 y286.8..311.8 z40.2..47.8
    cxp = (plug.bounding_box()[0] + plug.bounding_box()[3]) / 2.0
    xh = HUB_PORT_X[HUB_PORT["PED"]]
    pts = [(cxp, 311.3, 44.0), (cxp, 314.0, 48.0), (594.0, 318.0, 62.0), (594.0, 318.0, TOP_Z), (xh, 318.0, TOP_Z)]
    pts += hub_approach(xh, 318.0)[1:]
    ln = MODULE_PLUG_L + path_len(pts) + HUB_PLUG_L
    out.add("C-USB-PED", "USB-C 케이블 W208 (PED 보드 → 허브)", "USB cable W208 PED board to hub", "케이블",
            union([plug, tube(pts, 3.5), hub_plug(xh)]), COLORS["cable"],
            SRC_R + " ped_board (USB 8가닥 = 모듈 7 + PED 1) + usb_hub_710u3 note (hub y350.5..398.5); " + SRC_C + " low-divider crossing",
            note="추정: PED Zero USB-C 플러그에서 위로 올라 z93으로 칸막이를 넘어 허브 앞면(y%.1f) 포트 %d(x%.0f)에 꽂힘; "
                 "길이 약 %.0f mm - 경로는 보기용" % (HUB_Y, HUB_PORT["PED"], xh, ln))


def cu_small_parts(R, C, F, out, comp, feat, iof):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    g = "CU 칸 전자부"

    # ---- amp input jack board J702 (x676..706 y246..271, board z38.5..40.1) + PJ-313 at the rear edge x691 facing +y
    jf = feat["amp_input_jack_board_bosses"]
    b = jf["board"]
    jb = diff(bx(b), [cyl_z(p[0], p[1], 38.49, 40.11, 3.2) for p in jf["at"]])
    out.add("CU-E-J702BOARD", "앰프 입력 잭 기판 (만능기판 조각 30×25, J702 + 80 Hz RC)", "amp input jack board J702 (perfboard scrap)", g,
            jb, COLORS["pcb_perf"], SRC_C + " PR-CU-TRAY amp_input_jack_board_bosses (board x676..706 y246..271 z38.5..40.1)",
            note="추정: 기판 구멍 Ø3.2 (M3×10 → Ø2.7 보스); RC 부품은 작아서 뺌", material="FR4 만능기판")
    # PJ-313 (same envelope as J701 / J501): body on the board top, nose over the rear edge y271 facing +y
    d = F["cheeks"]["headphone_jack"]["jack_dims"]
    jx, jy1 = 691.0, b["y"][1]
    jz = b["z"][1] + d["axis_above_base"]               # axis z42.6
    out.add("CU-E-J702", "앰프 입력 잭 PJ-313 (J702)", "amp input jack PJ-313 (J702)", g, pj313(d, jx, jz, jy1, +1), BLACK_PLASTIC,
            SRC_C + " amp_input_jack_board_bosses note (jack on the rear edge y271 at x691 facing +y); " + PJ313_SRC,
            note="추정: 몸체 x%.0f~%.0f y%.1f~%.0f z%.1f~%.1f(기판 윗면), 축 z%.1f, 코 Ø%.0f가 기판 뒤끝 y%.0f에서 y%.1f까지 - 받은 부품으로 확인"
                 % (jx - d["body_W"] / 2, jx + d["body_W"] / 2, jy1 - d["body_L"], jy1, b["z"][1], b["z"][1] + d["body_H"], jz,
                    d["nose_d"], jy1, jy1 + d["nose_L"]))

    # ---- fuse holder BU914 in its cradle (centre-unit component box x632..678 y306..316 z35.5..45.5)
    fb = comp["퓨즈 홀더"]
    fy = (fb["y"][0] + fb["y"][1]) / 2.0
    fz = (fb["z"][0] + fb["z"][1]) / 2.0
    out.add("CU-E-FUSE", "BU914 인라인 퓨즈 홀더 + 5 A T 퓨즈", "Coms BU914 inline fuse holder + 5 A T fuse", g,
            cyl_x(fy, fz, fb["x"][0], fb["x"][1], fb["y"][1] - fb["y"][0]), BLACK_PLASTIC,
            SRC_C + " PR-CU-TRAY components 퓨즈 홀더 + fuse_holder_cradle (inner Ø10.5); " + SRC_R + " fuse_holder_bu914",
            note="추정: 지름 10 (가운데 유닛 받침 Ø10.5에 맞춤; electronics_rearbar는 Ø12×45 추정) - 받은 홀더로 확인, 선은 뺌")

    # ---- I/O plate: pedal jack J501 (hole centre x560 z92) on its scrap board on the printed ledge
    # the jack axis must be the hole centre z92 and the PJ-313 axis is 2.5 above its base = the board top, so the board
    # lies at z87.9..89.5 and the printed ledge top has to be z87.9 (spec ledge top z87.5 -> +0.4, body agent)
    ph = iof["pedal_jack_hole"]
    cxj, czj = ph["center_xz"]
    led = ph["mount"]["box"]
    zt = czj - d["axis_above_base"]                     # board top z89.5
    zbb = zt - 1.6                                      # board bottom z87.9 = required ledge top
    jbrd = diff(box(led["x"][0], led["x"][1], led["y"][0], led["y"][1], zbb, zt),
                [cyl_z(551.0, 392.0, zbb - 0.01, zt + 0.01, 3.2), cyl_z(569.0, 402.0, zbb - 0.01, zt + 0.01, 3.2)])
    out.add("CU-E-J501BOARD", "페달 잭 기판 (만능기판 조각 25×24, J501)", "pedal jack J501 perfboard scrap", g, jbrd, COLORS["pcb_perf"],
            SRC_C + " PR-IO-PLATE pedal_jack_hole mount (ledge x547.5..572.5 y384..408, M3×10 at (551,392)/(569,402)); board z from the "
            "PJ-313 axis: z92 − 2.5 − 1.6; " + PJ313_SRC,
            note="추정: 기판 z%.1f~%.1f (잭 축 z%.0f − 축 높이 %.1f = 기판 윗면 %.1f) → I/O 판 잭 선반 윗면은 z%.1f 이어야 함 "
                 "(spec 선반 윗면 z%.1f, %.1f 올림); 기판 구멍 Ø3.2"
                 % (zbb, zt, czj, d["axis_above_base"], zt, zbb, led["z"][1], zbb - led["z"][1]), material="FR4 만능기판")
    # nose tip flush with the plate outer face y410 (plate skin y408..410, hole Ø6.5): body front face y407.5
    skin = next(p for p in C["printed"] if p["id"] == "PR-IO-PLATE")["structure"]["outer_skin_y"]   # [408, 410]
    fy = skin[1] - d["nose_L"]
    out.add("CU-E-J501", "페달 잭 PJ-313 (J501, I/O 판)", "pedal jack PJ-313 (J501) in the I/O plate", g,
            pj313(d, cxj, czj, fy, +1), BLACK_PLASTIC,
            "position " + SRC_C + " PR-IO-PLATE pedal_jack_hole (x560, z92, Ø6.5 through the 2.0 skin y408..410); " + PJ313_SRC,
            note="추정: 몸체 x%.0f~%.0f y%.1f~%.1f z%.1f~%.1f (기판 위), 축 = 구멍 중심 x%.0f z%.0f; 몸체 앞면 y%.1f(바깥 판 안쪽면 y408과 "
                 "0.5 틈)라 코 Ø%.0f×%.1f 끝이 바깥면 y410과 같은 면 - 받은 부품으로 확인"
                 % (cxj - d["body_W"] / 2, cxj + d["body_W"] / 2, fy - d["body_L"], fy, zt, zt + d["body_H"], cxj, czj, fy,
                    d["nose_d"], d["nose_L"]))

    # ---- I/O plate: KCD1-101A rocker (hole centre x610 z92, 13.2 x 19.2 cut-out)
    sw = rb["power_switch_kcd1"]
    cxs, czs = iof["power_switch_hole"]["center_xz"]
    bez, body = sw["boxes"][0], sw["boxes"][1]
    bw, bh = bez["x"][1] - bez["x"][0], bez["z"][1] - bez["z"][0]
    dw, dh = body["x"][1] - body["x"][0], body["z"][1] - body["z"][0]
    sws = union([box(cxs - bw / 2, cxs + bw / 2, bez["y"][0], bez["y"][1], czs - bh / 2, czs + bh / 2),
                 box(cxs - dw / 2, cxs + dw / 2, body["y"][0], body["y"][1], czs - dh / 2, czs + dh / 2)])
    out.add("CU-E-SWITCH", "KCD1-101A 로커 스위치 (I/O 판)", "KCD1-101A rocker switch", g, sws, BLACK_PLASTIC,
            SRC_R + " power_switch_kcd1 (bezel 15×21×2 outside y410..412, body 13.2×19.2 × 21 deep); position " + SRC_C + " power_switch_hole (x610, z92)",
            note="추정: 몸체 깊이 21(단자 포함) - 베젤이 뒤판 바깥으로 2 mm 나옴(y410~412)")

    # ---- I/O plate: USB-C power input = HUSB238 PD trigger in the plate pocket (x660, z92)
    pd = rb["pd_trigger_husb238"]["boxes"][0]
    cxu, czu = iof["usb_c_input"]["center_xz"]
    cav = iof["usb_c_input"]["pocket"]["cavity"]
    pw = pd["x"][1] - pd["x"][0]                       # 10
    pl = pd["y"][1] - pd["y"][0]                       # 16.4
    ph_ = pd["z"][1] - pd["z"][0]                      # 4.4
    ye = cav["y"][1]                                   # receptacle mouth flush with the skin inner face y408
    zc = (cav["z"][0] + cav["z"][1]) / 2.0             # 92.0
    z0 = zc - ph_ / 2.0
    pcb_ = box(cxu - pw / 2, cxu + pw / 2, ye - pl, ye, z0, z0 + 1.2)
    rcpt = box(cxu - 4.47, cxu + 4.47, ye - 7.3, ye, z0 + 1.2, z0 + ph_)
    out.add("CU-E-PDTRIG", "HUSB238 PD 트리거 + USB-C 전원 입력 (L57, I/O 판 포켓)", "HUSB238 USB-C PD trigger (L57) in the I/O-plate pocket", g,
            union([pcb_, rcpt]), COLORS["pcb_blue"],
            SRC_R + " pd_trigger_husb238 (10×16.4×4.4); position " + SRC_C + " PR-IO-PLATE usb_c_input pocket (cavity x654.8..665.2 y391.2..408 z89.6..94.4, mouth y408)",
            note="추정: 기판 1.2 + USB-C 리셉터클 8.94×7.3×3.2 (+y 끝)로 나눔")


def hub_bank_parts(R, C, out):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    g = "보조배터리 칸"
    h = rb["usb_hub_710u3"]["boxes"][0]
    dy = HUB_BACK - h["y"][1]                           # +6: from drawing 10 (y344.5..392.5) back against the wall
    out.add("PB-E-HUB", "NEXTU 710U3 10포트 유전원 USB 허브", "NEXTU 710U3 10-port powered USB hub", g, bx(h, dy=dy), HUB_GREY,
            SRC_R + " usb_hub_710u3 (228×48×24 flat on the bay floor, x750..978 z33.5..57.5, L17; note 'v3 assembly text: taped to the back "
            "wall, y350.5-398.5')" + "; v3 A18 / BOM L17 (보조배터리 칸 뒷벽에 양면테이프)",
            note="추정: 포트 위치 미확인 - 아래 포트 10개를 앞면(y%.1f, -y 쪽) x760+22i, z%.0f에 둔 것으로 표시, 업스트림은 +x 끝면; "
                 "도면 10 위치(y344.5~392.5, 뒷벽 앞 6 mm)가 아니라 v3 본문·BOM대로 뒷벽(y%.1f)에 붙임" % (HUB_Y, HUB_Z, HUB_BACK))
    pbx = rb["power_bank_mt65"]["boxes"][0]
    hold = next(p for p in C["printed"] if p["id"] == "PR-PB-HOLDER")["geometry"]["battery_pocket"]
    L = pbx["x"][1] - pbx["x"][0]
    W = pbx["y"][1] - pbx["y"][0]
    x0, y0 = hold["x"][0], hold["y"][0]
    out.add("PB-E-BANK", "모루이 MT-65 보조배터리 (20000 mAh, 65 W)", "Morui MT-65 65 W 20000 mAh power bank (optional O07)", g,
            box(x0, x0 + L, y0, y0 + W, pbx["z"][0], pbx["z"][1]), BANK_GREY,
            SRC_R + " power_bank_mt65 (105×71×32); " + SRC_C + " PR-PB-HOLDER (battery pushed into the front-left corner stop x741 / y231.5, floor z35.5)",
            note="추정: 받침의 앞·왼쪽 멈춤벽에 붙인 자리(x741~846 y231.5~302.5); 도면 10 위치는 x750~855 y238.5~309.5. 선택품(O07)")


def xt30_parts(S, R, out):
    """female half in the holder pocket (mouth at the joint face), male half toward the centre unit."""
    rb = {i["id"]: i for i in R["rearbar_items"]}
    pair = rb["xt30_pair_L"]["boxes"][0]
    face_y = pair["y"][1] - pair["y"][0]                # 10.2
    face_z = pair["z"][1] - pair["z"][0]                # 5.2
    LF, LM, ENG = 12.4, 13.7, 5.6                       # female / male length, engaged length (BOM L61 / audio.md §4)
    hold = {p["id"]: p for p in S["printed"] if p["id"].startswith("xt30_holder")}
    for side, hid in (("L", "xt30_holder_L"), ("R", "xt30_holder_R")):
        pk = hold[hid]["pocket"]["world"]
        yc = (pk["y"][0] + pk["y"][1]) / 2.0
        zc = (pk["z"][0] + pk["z"][1]) / 2.0
        if side == "L":
            mouth = pk["x"][1]                          # x164, opening +x
            fem = box(mouth - LF, mouth, yc - face_y / 2, yc + face_y / 2, zc - face_z / 2, zc + face_z / 2)
            mal = box(mouth, mouth + LM - ENG, yc - face_y / 2, yc + face_y / 2, zc - face_z / 2, zc + face_z / 2)
        else:
            mouth = pk["x"][0]                          # x1058, opening -x
            fem = box(mouth, mouth + LF, yc - face_y / 2, yc + face_y / 2, zc - face_z / 2, zc + face_z / 2)
            mal = box(mouth - (LM - ENG), mouth, yc - face_y / 2, yc + face_y / 2, zc - face_z / 2, zc + face_z / 2)
        src = SRC_R + " xt30_pair_%s (face 10.2×5.2, M 13.7 + F 12.4 − 5.6 engaged); position spec/body_speakers.json %s pocket" % (side, hid)
        out.add("C-XT30F-%s" % side, "XT30U-F 암 (스피커 쪽, XT30 받침 %s 안)" % side, "XT30U-F female in holder " + side, "케이블",
                fem, XT30_YELLOW, src, note="추정: 몸체를 10.2×5.2×12.4 상자로; 입구를 받침 이음면(x%.0f)에 맞춤" % mouth)
        out.add("C-XT30M-%s" % side, "XT30U-M 수 (앰프 쪽, 가운데 유닛 쪽으로 꽂힘) %s" % side, "XT30U-M male (mated) " + side, "케이블",
                mal, XT30_YELLOW, src, note="추정: 암 속으로 들어간 5.6은 빼고 밖에 보이는 8.1만 표시; 18 AWG 선(10 cm)은 뺌")


def speaker_parts(R, out):
    for sp in R["speakers"]:
        side = sp["id"][-1]
        cx, cz = sp["center_xz"]
        fl = sp["boxes"][0]
        flange = bx(fl)
        slots = []
        for (sx, sz) in sp["mount_holes"]["centers_xz"]:
            ang = math.degrees(math.atan2(sz - cz, sx - cx))
            slots.append(prism_y(stadium_xz(sx, sz, 6.8, 4.8, ang), fl["y"][0] - 0.01, fl["y"][1] + 0.01))
        flange = diff(flange, slots)
        cyls = {c["name"].split()[0]: c for c in sp["cylinders"]}
        basket, magnet = cyls["basket"], cyls["magnet"]
        y0 = fl["y"][0]
        # basket rim continues from the flange back face through the gasket opening (y212..215, EVA inner Ø94 = basket Ø94)
        rim = cyl_y(cx, cz, fl["y"][1] - 0.01, basket["range"][0] + 0.01, basket["d"])
        body = union([flange, rim, cyl(basket), cyl(magnet)])
        # visual cone recess + dust cap (front view reads as a speaker, not a block); the spec "dust cap / cone mouth"
        # Ø70 y212..222 (visual, assumed) is replaced by this recess + cap
        recess = Manifold.cylinder(24.0, 45.0, 17.0, 96).rotate((-90, 0, 0)).translate((cx, y0 - 0.01, cz))
        cap = Manifold.cylinder(5.5, 17.0, 10.0, 64).rotate((90, 0, 0)).translate((cx, y0 + 24.5, cz))   # 0.5 into the recess floor
        body = union([diff(body, [recess]), cap])
        out.add("SPK-%s" % side, sp["name_ko"], sp["name_en"], "스피커 유닛", body, COLORS["speaker"],
                SRC_R + " speakers %s (flange 105×105×4 y208..212 with 4 slots Ø4.8×6.8 on PCD 115; basket Ø94 y215..252; magnet Ø85×17 y252..269; centre x%.0f z%.0f)" % (sp["id"], cx, cz),
                note="추정: 바스켓 테두리를 가스켓 구멍(y212~215) 안으로 이어 한 덩어리로; 콘 오목면(Ø90→Ø34, 깊이 24)과 더스트캡은 보기용")


def pedal_part(R, out):
    p = R["pedal"]
    b = p["boxes"][0]
    x0, x1 = b["x"]
    y0, y1 = b["y"]
    z0, z1 = b["z"]
    # wedge: base plate + pedal plate rising toward the hinge end (+y, away from the player)
    poly = [(y0, z0), (y1, z0), (y1, z1), (y1 - 30.0, z1), (y0, z0 + 25.0)]
    out.add("PEDAL-DAMPER", p["name_ko"], p["name_en"], "댐퍼 페달 (바닥)", prism_x(poly, x0, x1), "#1d1d1f",
            SRC_R + " pedal (76×240×65, floor z-720 for a 720 mm desk, plan x640..716 y-400..-160 from drawing 7). "
            "추정: 쐐기 모양(뒤쪽 경첩이 높음), 책상 높이 720", note="offdesk")


# ------------------------------------------------------------------ headphone jack J701 in the left cheek

def headphone_jack(F, R, out):
    hj = F["cheeks"]["headphone_jack"]
    d = hj["jack_dims"]
    pk = hj["pocket"]
    cx, az = pk["centre_x"], pk["axis_z"]
    y0 = pk["front_wall"]["y"][1]                       # body starts behind the 2.5 front wall, nose through it
    out.add("EL-E-J701", "헤드폰 잭 PJ-313 (J701, 왼쪽 볼 앞면)", "headphone jack PJ-313 (J701) in the left cheek", "끝 부속 왼쪽 전자부",
            pj313(d, cx, az, y0, -1), BLACK_PLASTIC,
            "spec/keyaction_features_frame.json cheeks.headphone_jack (pocket centre x-8.34, axis z20, cavity y2.5..14.2, nose Ø5.0 through y0..2.5); "
            + PJ313_SRC + "; " + SRC_R + " headphone_jack_j701",
            note="추정: 포켓 위치·축 높이 z20 (frame spec assumed); 다리(밑 3.2)와 케이블 ①·②는 뺌")


# ------------------------------------------------------------------ entry point

def build():
    M = _load("electronics_modules.json")
    R = _load("electronics_rearbar.json")
    C = _load("body_centre_unit.json")
    F = _load("keyaction_features_frame.json")
    S = _load("body_speakers.json")
    out = Out()
    plan = cable_plan()
    module_parts(M, out, plan)
    end_parts(M, out)
    comp, feat, iof, pi = rearbar_parts(R, C, F, S, out, plan)
    ped_zero_parts(M, out)
    cu_small_parts(R, C, F, out, comp, feat, iof)
    # hub upstream cable: Pi USB-A (UPPER port of the stack at the GPIO edge, y383) -> hub +x end face (x978, y centre of
    # the hub against the back wall = y374.5)
    face, ys = pi["face"], pi["y_s2"]
    hy = HUB_Y + 24.0                                   # hub y centre 374.5
    up = box(face, face + 25.0, ys - 8.0, ys + 8.0, 49.5, 57.5)
    hub_end = box(978.0, 998.0, hy - 8.0, hy + 8.0, HUB_Z - 4.0, HUB_Z + 4.0)
    pts = [(face + 24.5, ys, 53.5), (652.0, ys, 60.0), (656.0, 376.0, 80.0), (656.0, 372.0, TOP_Z), (1008.0, 372.0, TOP_Z),
           (1008.0, hy, 60.0), (998.0 - 0.5, hy, HUB_Z)]
    out.add("C-USB-UPSTREAM", "USB 허브 업스트림 케이블 W209 (허브 → Pi 5 USB-A)", "hub upstream cable W209 (hub to Pi 5 USB-A)", "케이블",
            union([up, tube(pts, 4.0), hub_end]), COLORS["cable"],
            SRC_C + " keep_out pi_usb_plugs (x616..662: hub upstream plug W209 + L52 gender + L51 dongle); " + SRC_R + " cables_simple 'hub upstream → Pi USB-A'",
            note="추정: Pi 5 USB-A 2단 중 GPIO 쪽 스택(중심 y%.0f)의 위 포트(z49.5~57.5)와 허브 +x 끝면(y%.1f)에 USB-A 플러그(16×8×25·20), "
                 "OD 4, z93으로 칸막이를 넘음 - RJ45 옆 스택의 아래 포트는 동글 젠더" % (ys, hy))
    hub_bank_parts(R, C, out)
    xt30_parts(S, R, out)
    speaker_parts(R, out)
    headphone_jack(F, R, out)
    pedal_part(R, out)
    return list(out)


if __name__ == "__main__":
    ps = build()
    for p in ps:
        b = p.solid.bounding_box()
        print("%-18s %-12s %-14s %6d  %s" % (p.id, p.kind, p.group, len(p.solid.decompose()), " ".join("%.1f" % v for v in b)))
    print(len(ps), "parts")
