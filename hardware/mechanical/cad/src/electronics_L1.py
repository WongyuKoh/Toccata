"""Toccata electronics as Part instances (world coordinates, assembled pose) - L1 low rear bar (2026-09-30).

Governing layout: spec/body_low_L1.json (L1: rear bar y252..447 on 5 mm feet, open cable trough y212..252 between the key
modules and the rear bar, centre unit x200..1022 z5..88 (inner z16.5..76.5, y263.5..435.5), speaker parts with a 30 deg
slanted printed baffle, driver centre (x90.5 / x1131.5, y282.75, z82.37), axis (-cos30, +sin30) in (y, z)).
The tall v3.2 version of this file is kept as electronics_v3_tall.py.

Sources (the only numeric sources):
  spec/body_low_L1.json           L1 geometry: trough, centre-unit bays, CU-bay shift from v3 (dx 36.05, dy 37, dz -17),
                                  I/O-plate hole x / z46.5, front-panel cable inlet notch, speaker driver pose
  spec/electronics_modules.json   boards / modules / cables inside the 7 octave modules and the 2 end parts (unchanged)
  spec/electronics_rearbar.json   rear-bar electronics, speakers, damper pedal (envelope SIZES)
  spec/body_centre_unit.json      v3 CU-bay re-layout (component POSITIONS / heights, I/O-plate hole layout) -> moved by the
                                  L1 shift (I/O-plate parts: to the L1 hole x and centre z46.5)
  spec/keyaction_features_frame.json  left-cheek headphone-jack pocket (J701) + the PJ-313 envelope (SHOU HAN PJ-313 5JCJ
                                  jack_dims) used for ALL three PJ-313 jacks (J701, J501, J702)

Shown: boards as plain rectangles with their mounting holes / U-slots, and only the bulky parts on them (RP2040-Zero, mux
module, bought modules, jacks, switch, connectors, cables). Omitted on purpose: every spec item/box with show:false, hall
sensors, key magnets and control-board M3x6 screws (keyaction_parts.py emits them), resistors / caps / headers / pads, the
board screws of the CU bay (body parts), the 18 AWG speaker leads, the C14 AUX cables and the power wiring.

R31 touchscreen (../touchscreen/CAD_SPEC.md F, numbers.json, screen_dims/td2_7_mech.png; poses in touchscreen.py): Touch
Display 2 7" envelope (lens, body, lugs, standoffs, DSI connector, J1) in the 25 deg use pose + a folded 'altview' copy, the
300 mm DSI ribbon as a 0.3 x 16 swept strip (Pi CAM/DISP 1 -> 45 deg fold -> under the lid -> hole -> R10.5 hinge loop ->
cradle slot -> 45 deg fold -> DSI connector), the J1 power lead from Pi GPIO 2 / 6 and the Pi 5 CAM/DISP 1 connector.

Module items: world x = 47 + 164.5 (k-1) + local x (k = 1..7). End items: left = world x, right = 1198.5 + x.
"""
import json
import math
import os

import numpy as np
from manifold3d import Manifold

from cadlib import box, cyl_x, cyl_y, cyl_z, diff, prism_x, prism_y, prism_z, union
from parts import COLORS, Part
import touchscreen as TS

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
SRC_L = "spec/body_low_L1.json"


def _load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


L1 = _load("body_low_L1.json")

# ------------------------------------------------------------------ L1 constants (all from body_low_L1.json)

_sh = L1["shift_from_v3"]["cu_bay"]
SHIFT = (_sh["dx"], _sh["dy"], _sh["dz"])                    # v3 CU bay -> L1 CU bay (36.05, 37, -17)
IO = L1["centre"]["io_plate"]
IO_HOLE_Z = IO["holes"]["z"]                                 # 46.5 (v3: z92)
V3_IO_HOLE_Z = 92.0                                          # body_centre_unit PR-IO-PLATE hole centres (all z92)
IO_SHIFT = (SHIFT[0], SHIFT[1], IO_HOLE_Z - V3_IO_HOLE_Z)    # I/O-plate parts: (36.05, 37, -45.5)
IO_Y0, IO_Y1 = IO["y"]                                       # 435.5 .. 447
CU_IN_Z = L1["centre"]["inner_z"]                            # [16.5, 76.5]
CU_IN_Y = L1["centre"]["inner_y"]                            # [263.5, 435.5]
BAYS = L1["centre"]["bays_inner_x"]
LOW_DIV_TOP = CU_IN_Z[0] + L1["centre"]["low_divider_height"]   # 56.5
TROUGH_Y = L1["cable_trough"]["y"]                           # [212, 252]
TROUGH_Z_MAX = L1["cable_trough"]["z"][1]                    # 22 (cables stay low)
INLET_X = (583.0, 733.0)                                     # L1 cable_inlet: front-panel notch x583..733, z16.5..34
INLET_Z = (16.5, 34.0)
FRONT_Y = (L1["rear_bar"]["y"][0], L1["rear_bar"]["y"][0] + L1["rear_bar"]["panel_t"])   # 252 .. 263.5


def sv(x, y, z, s=SHIFT):
    return (x + s[0], y + s[1], z + s[2])


# ------------------------------------------------------------------ small geometry helpers

def bx(b, dx=0.0, dy=0.0, dz=0.0):
    """spec box {x:[..], y:[..], z:[..]} -> solid (optionally shifted)."""
    return box(b["x"][0] + dx, b["x"][1] + dx, b["y"][0] + dy, b["y"][1] + dy, b["z"][0] + dz, b["z"][1] + dz)


def bxs(b, s=SHIFT):
    return bx(b, *s)


def shifted_box(b, s=SHIFT):
    """spec box dict moved by s (dict out)."""
    return {"x": [b["x"][0] + s[0], b["x"][1] + s[0]], "y": [b["y"][0] + s[1], b["y"][1] + s[1]],
            "z": [b["z"][0] + s[2], b["z"][1] + s[2]]}


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


# ------------------------------------------------------------------ board helpers

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


# ------------------------------------------------------------------ module + end-part electronics (unchanged from v3)

def module_parts(M, out, cable_plan):
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
        out.add("%s-C-RIBBON" % tag, "16심 리본 W10%d (SB J201 → MB J301)" % k, "16-core ribbon W10%d" % k, "케이블",
                union([bx(b, X0) for b in rb["boxes"]]), COLORS["cable"], SRC_M + " ribbon; " + rb["source"],
                note="남는 길이(자른 길이 180 − 경로 85)는 접어 둠, 모델에 없음 (spec note)")

        if tag in it["ext_lead"]["modules"]:
            el = it["ext_lead"]
            wid = {"O1": "W403", "O7": "W413"}[tag]
            out.add("%s-C-EXT" % tag, "EXT 연장선 %s (L66 모듈 쪽 150 mm, 6심 22 AWG)" % wid, "EXT lead %s" % wid, "케이블",
                    diff(union([bx(b, X0) for b in el["boxes"]] + [tube(ext_floor_path(tag, X0), 3.0)]),
                         [bx(b, X0) for b in mb["boxes"]]), COLORS["cable"],
                    SRC_M + " ext_lead + xh_left/xh_right (mated XH on the trough floor); " + el["source"],
                    note="추정: 묶음 단면 약 8×2와 띠 안의 x 위치 (spec assumed; spec 상자 y195.4~가 MB 끝 y195.5와 0.1 겹쳐 MB 자리를 뺌); "
                         "뒷벽 구멍(y212)부터 XH 짝까지는 지름 3 선으로 L1 열린 통로(y212~252) 바닥(z0~3)에 눕힘 - 경로는 보기용")

        # USB-C plug + cable to the hub (one part: plug overmold + cable + hub-end USB-A plug)
        up = it["usb_plug"]
        plug = bx(up["boxes"][0], X0)
        cab = tube(cable_plan[tag], CABLE_OD)
        port = HUB_PORT[tag]
        ln = cable_plan["_len"][tag]
        out.add("%s-C-USB" % tag, "USB-C 케이블 W20%d (Coms NA993, %s → 허브)" % (k, tag), "USB cable W20%d %s to hub" % (k, tag),
                "케이블", union([plug, cab, hub_plug(HUB_PORT_X[port])]), COLORS["cable"],
                SRC_M + " usb_plug + usb_cable (bend R25 to y246.8); " + SRC_L + " cable_trough y212..252 z<=22, cable_inlet "
                "x583..733 z16.5..34, low divider top z56.5; " + SRC_R + " usb_hub_710u3; BOM C04 NA993 1 m",
                note="추정: 케이블 OD 3.5; %s, x%.1f에서 앞판 홈으로 z%.1f에 들어와 CU 칸 앞 띠(y%.0f)에서 z%.1f로 올라 "
                     "줄 y%.1f를 따라 낮은 칸막이(윗면 z%.1f)를 넘고, 허브 앞면(y%.1f) 포트 %d(x%.0f, 포트 x = 허브 -x 끝 + 10 + 22i 가정)에 "
                     "USB-A 플러그(16×8×20)로 꽂힘; 길이 = 플러그 %.0f + 경로 %.1f + 허브 플러그 %.0f = %.1f mm (NA993 1 m 이하, 여유 %.1f) "
                     "- 경로는 보기용"
                     % (("R25 굽힘 뒤 통로 바닥 줄 y%.1f (z%.2f)" % (cable_plan["_floor"][tag], FLOOR_Z)) if tag in cable_plan["_floor"]
                        else "R25 굽힘 끝(x%.1f)이 바로 홈 앞이라 바닥으로 내리지 않음" % cable_plan["_turn"][tag],
                        cable_plan["_turn"][tag], INLET_CZ, RISE_Y, LANE_Z, cable_plan["_lane"][tag], LOW_DIV_TOP,
                        HUB_Y, port, HUB_PORT_X[port], MODULE_PLUG_L, ln - MODULE_PLUG_L - HUB_PLUG_L, HUB_PLUG_L, ln,
                        USB_CABLE_MAX - ln))


def end_parts(M, out):
    it = {i["id"]: i for i in M["end_items"]}
    for iid, side, dx, tag in (("el_board", "왼쪽", 0.0, "EL"), ("er_board", "오른쪽", X_RIGHT, "ER")):
        b = it[iid]
        out.add("%s-E-BOARD" % tag, b["name_ko"], b["name_en"], "끝 부속 %s 전자부" % side, board_with_cuts(b, dx),
                COLORS["pcb_perf"], SRC_M + " " + iid + "; " + b["source"],
                note="추정: U홈 Ø3.4가 왼쪽 끝으로 열림 (spec assumed)", material="FR4 만능기판")
    for iid, dx, tag in (("el_lead", 0.0, "EL"), ("er_lead", X_RIGHT, "ER")):
        b = it[iid]
        out.add("%s-C-LEAD" % tag, b["name_ko"], b["name_en"], "케이블",
                union([bx(q, dx) for q in shown(b["boxes"])] + [tube(lead_floor_path(tag), 2.0)]),
                COLORS["cable"], SRC_M + " " + iid + " + xh_left/xh_right lead drop (y212..231, trough floor); " + b["source"],
                note="추정: 뒷벽 노치(y212)에서 통로 바닥으로 내려 XH 짝 끝면까지 지름 2 선으로 표시 (실제는 폭 %s 리본 띠) - 경로는 보기용"
                     % ("6.35" if tag == "EL" else "3.81"))
    for iid, tag in (("xh_left", "L"), ("xh_right", "R")):
        b = it[iid]
        out.add("C-XH-%s" % tag, b["name_ko"], b["name_en"], "케이블", union([bx(q) for q in shown(b["boxes"])]),
                "#f2f2ee", SRC_M + " " + iid + "; " + b["source"] + "; L1: 열린 통로 y212~252 안 (그대로)",
                note="추정: 느슨한 커넥터 - 위치·높이·길이 (spec assumed: " + b["assumed_note"][:120] + ")")


# ------------------------------------------------------------------ cable plan (module USB cables, PED, upstream)

CABLE_OD = 3.5            # NA993 OD not published (module spec usb_cable assumed 3.5)
FLOOR_Z = CABLE_OD / 2.0  # lying on the desk in the open trough
USB_CABLE_MAX = 1000.0    # Coms NA993 USB-A to C, 1 m (BOM C04)
MODULE_PLUG_L = 25.0      # USB-C overmold envelope along y (electronics_modules usb_plug y196.8..221.8)
HUB_PLUG_L = 20.0         # USB-A overmold at the hub (hub_plug below)
ARC_Y1 = 246.8            # end of the R25 bend (module spec usb_cable sweep, circuit_r44)
ARC_Z = 14.5              # plug axis height (usb_plug z10.7..18.3)
# trough floor lanes (y of the cable axis on the desk). The cable that bends last before the inlet takes the rear lane
# so its drop from the bend (z14.5, y246.8) never comes down on a lane already on the floor (4.0 apart = OD + 0.5).
FLOOR_LANE = {"O1": 240.3, "O2": 244.3, "O3": 248.3, "O7": 240.3, "O6": 244.3, "O5": 248.3}
# x where each cable turns +y into the front-panel notch (x583..733): the rear lane turns first, O4 goes straight in after
# its bend (x599.5); the left group stays >= 5 left of O4, the right group right of O4's bend (x<=624.5 + r)
INLET_TURN_X = {"O3": 586.5, "O2": 590.75, "O1": 595.0, "O4": 599.5, "O7": 632.0, "O6": 636.5, "O5": 641.0}
INLET_CZ = 19.5           # cable axis through the notch: tray top z16.5 + r 1.75 + 1.25 (notch z16.5..34)
APPROACH_Y = 250.5        # axis y where the cable reaches INLET_CZ, still in the trough (y <= 252 - r)
CLIMB_Z = 16.0            # floor-lane cables rise vertically at their lane y to here before turning into the notch
RISE_Y = 270.0            # vertical rise inside the CU bay front strip (v3 keep-out inlet_rise y226.5..240 + 37 = y263.5..277)
LANE_Z = 60.5             # lanes over the CU bay: low divider top z56.5 + r 1.75 + 2.25; top z62.25 under the lid (z76.5)
DROP_Z = 56.5             # drops toward the hub pass 4.0 under the lanes (OD 3.5 + 0.5) and 3.0 over the power-bank max
                          # envelope top z53.5 (v3 PR-PB-HOLDER battery_pocket z70.5 - 17)
# lane y over the CU bay (pitch 4.5): a cable that rises further left takes a lane further back (+y), so no +y leg crosses
# another cable's lane
LANE_Y = {"O5": 288.0, "O6": 292.5, "O7": 297.0, "O4": 301.5, "O1": 306.0, "O2": 310.5, "O3": 315.0, "PED": 352.0}
UP_LANE_Y = 408.0         # hub upstream lane (behind everything, clear of the lid corner supports y417.5..)

# hub 710U3 lying flat against the power-bank bay back wall (L1 task: y387.5..435.5): 228 x 48 x 24, x782..1010 (0.5 from
# the right end panel x1010.5 - the bay x761.8..1010.5 is 248.7 wide, so the upstream plug + its bend only fit at the -x end
# with an up-angled plug, see hub_upstream_plug)
HUB_L, HUB_W, HUB_H = 228.0, 48.0, 24.0
HUB_BACK = CU_IN_Y[1]                         # 435.5 (bay inner rear face)
HUB_Y = HUB_BACK - HUB_W                      # 387.5 front face (downstream ports face -y)
HUB_X1 = BAYS["power_bank"][1] - 0.5          # 1010.0
HUB_X0 = HUB_X1 - HUB_L                       # 782.0
HUB_Z0 = CU_IN_Z[0]                           # 16.5 (bay floor = bottom panel top)
HUB_Z = HUB_Z0 + 16.5                         # port centre 33.0 (v3: z50 on a z33.5 floor)
HUB_PORT_X = [HUB_X0 + 10.0 + 22.0 * i for i in range(10)]   # 792 .. 990 (v3 assumption: 10 from the end, pitch 22)
# port use: the two longest runs (O1 from the far left, O7 from the far right) take the ports nearest the low divider
HUB_PORT = {"O1": 0, "O7": 1, "O6": 2, "O2": 3, "O3": 4, "O4": 5, "O5": 6, "PED": 7}
HUB_UP_YZ = (HUB_Y + HUB_W / 2.0, HUB_Z0 + HUB_H / 2.0)       # upstream port centre on the -x end face (411.5, 28.5)

XH_L = (52.0, 69.4)       # electronics_modules xh_left  x (y222..240, z0..6)
XH_R = (1160.0, 1177.4)   # electronics_modules xh_right x
XH_Y = 231.0              # middle of the XH housing (y222..240)


def ext_floor_path(tag, X0):
    """EXT lead from the module rear-wall opening (local x82..91, z5..10.7 at y212) down to the trough floor and along it
    to the module-side end face of the XH pair (O1 -> -x to X402 at x69.4, O7 -> +x to X412 at x1160)."""
    x = X0 + 86.5
    r = 1.5
    if tag == "O1":
        return [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, r), (x - 8.0, 226.0, r), (XH_L[1] + r, XH_Y, r)]
    return [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, r), (x + 8.0, 226.0, r), (XH_R[0] - r, XH_Y, r)]


def lead_floor_path(tag):
    """EL / ER flat lead from the end-part rear-wall notch (z5..5.89 at y212) down to the trough floor and to the
    end-part side of the XH pair (EL -> x52, ER -> x1177.4)."""
    r = 1.0
    if tag == "EL":
        x = (14.825 + 21.175) / 2.0
        return [(x, 212.0, 6.0), (x, 213.0, 6.0), (x, 216.0, r), (x + 6.0, 226.0, r), (XH_L[0] - r, XH_Y, r)]
    x = X_RIGHT + (8.885 + 12.695) / 2.0
    return [(x, 212.0, 6.0), (x, 213.0, 6.0), (x, 216.0, r), (x - 6.0, 226.0, r), (XH_R[1] + r, XH_Y, r)]


def hub_plug(xh):
    """USB-A plug overmold 16 x 8 x 20 in front of the hub face (assumed)."""
    return box(xh - 8.0, xh + 8.0, HUB_Y - HUB_PLUG_L, HUB_Y, HUB_Z - 4.0, HUB_Z + 4.0)


def hub_drop(xh, lane, lane_z=LANE_Z):
    """from the lane (z60.5) straight down to z56.5 (4.0 under the other lanes), +y over the power bank to y357.5
    (2.25 behind its max envelope y353.5 + r), down, and +y into the plug on the hub front face."""
    yd = 357.5
    return [(xh, lane, lane_z), (xh, lane, DROP_Z), (xh, yd, DROP_Z), (xh, yd, HUB_Z + 7.0),
            (xh, HUB_Y - HUB_PLUG_L - 5.0, HUB_Z), (xh, HUB_Y - HUB_PLUG_L - 0.5, HUB_Z)]


def path_len(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def cable_plan():
    """module USB cables: plug -> R25 bend at z14.5 -> (O1..O3, O5..O7) down to a floor lane in the open trough -> along x to
    the inlet turn x -> up to z19.5 by y250.5 -> through the front-panel notch -> vertical rise at y270 to z60.5 -> +y to the
    lane -> +x over the CU bay and the low divider -> drop to the hub port. O4 enters the notch straight after its bend."""
    x_hub = {t: HUB_PORT_X[i] for t, i in HUB_PORT.items()}
    plan = {"_len": {}, "_lane": dict(LANE_Y), "_xhub": x_hub, "_floor": dict(FLOOR_LANE), "_turn": dict(INLET_TURN_X)}
    for k in range(1, 8):
        t = "O%d" % k
        xc = X_O1 + MODULE_W * (k - 1) + 84.0
        s = 1.0 if k <= 3 else -1.0
        cx = xc + 25.0 * s
        pts = arc_pts(cx, 221.8, ARC_Z, 25.0, 180.0, 90.0) if s > 0 else arc_pts(cx, 221.8, ARC_Z, 25.0, 0.0, 90.0)
        xe = INLET_TURN_X[t]
        if t != "O4":
            xb = cx                                  # bend end x (y246.8)
            # along the floor lane to the turn x, up at the lane y to z16 (clear of the tray front corner y252 z16.5), then
            # forward-up into the notch
            pts += [(xb + 25.0 * s, FLOOR_LANE[t], FLOOR_Z), (xe, FLOOR_LANE[t], FLOOR_Z), (xe, FLOOR_LANE[t], CLIMB_Z)]
        pts += [(xe, APPROACH_Y, INLET_CZ), (xe, FRONT_Y[1] + 1.0, INLET_CZ), (xe, RISE_Y, INLET_CZ + 5.5),
                (xe, RISE_Y, LANE_Z - 4.5), (xe, RISE_Y + 4.5, LANE_Z), (xe, LANE_Y[t], LANE_Z), (x_hub[t], LANE_Y[t], LANE_Z)]
        pts += hub_drop(x_hub[t], LANE_Y[t])[1:]
        plan[t] = pts
        plan["_len"][t] = MODULE_PLUG_L + path_len(pts) + HUB_PLUG_L
    return plan


# ------------------------------------------------------------------ rear bar CU bay (v3 layout moved by SHIFT)

def rearbar_parts(R, C, out):
    tray = next(p for p in C["printed"] if p["id"] == "PR-CU-TRAY")
    feat = {f["name"]: f for f in tray["features"]}
    comp = {c["name_ko"]: c["box"] for c in tray["components"]}
    io = next(p for p in C["printed"] if p["id"] == "PR-IO-PLATE")
    iof = {f["name"]: f for f in io["features"]}
    g = "CU 칸 전자부"
    dx, dy, dz = SHIFT
    sft = "L1 이동 (x+%.2f, y+%.0f, z%.0f) - %s shift_from_v3" % (dx, dy, dz, SRC_L)

    # ---- Raspberry Pi 5 (v3 x531..616 y336..392 board z39.5..41.1 -> L1 x567.05..652.05 y373..429 z22.5..24.1)
    pb = shifted_box(comp["라즈베리파이 5"])
    x0, x1, y0, y1 = pb["x"][0], pb["x"][1], pb["y"][0], pb["y"][1]
    zb0, zb1 = 39.5 + dz, 41.1 + dz
    bosses = [(p[0] + dx, p[1] + dy) for p in feat["pi5_bosses"]["at"]]
    pcb = diff(box(x0, x1, y0, y1, zb0, zb1), [cyl_z(p[0], p[1], zb0 - 0.01, zb1 + 0.01, 2.7) for p in bosses])
    hdr = box(x0 + 32.5 - 25.4, x0 + 32.5 + 25.4, y1 - 3.5 - 2.54, y1 - 3.5 + 2.54, zb1, zb1 + 8.5)
    hs = box(x0 + 21.5, x0 + 36.5, y0 + 17.5, y0 + 32.5, zb1, zb1 + 8.0)
    out.add("CU-E-PI5", "라즈베리파이 5 2GB", "Raspberry Pi 5 2GB", g, union([pcb, hdr, hs]), PI5_GREEN,
            SRC_C + " PR-CU-TRAY components/pi5_bosses (v3 x531..616 y336..392, board z39.5..41.1); " + sft + "; " + SRC_R + " pi5 (L01)",
            note="추정: GPIO 헤더 2×20 (가장자리 3.5, 비포트 쪽 끝에서 32.5 중심)과 SoC 방열판 15×15×8 (L02 높이 미표기) 위치; "
                 "USB-C 전원·micro-HDMI(-y 가장자리)는 작아서 뺌; L1 자리 x%.2f~%.2f y%.0f~%.0f 기판 z%.1f~%.1f" % (x0, x1, y0, y1, zb0, zb1))
    face = x1 + PI_PORT_OVERHANG
    ports = {}
    for key, name_ko, name_en, yc_off, w, depth, h in PI_PORTS:
        yc = y0 + yc_off
        ports[key] = yc
        out.add("CU-E-PI5-" + key, name_ko, name_en, g,
                box(face - depth, face, yc - w / 2, yc + w / 2, zb1, zb1 + h), COLORS["metal"],
                SRC_C + " PR-CU-TRAY pi5_bosses note (USB/Ethernet end faces +x, power/HDMI edge faces -y); " + sft + "; "
                + SRC_R + " pi5 box 'USB-A x2 stacks + RJ45 block' (tallest 16.5 above the PCB, overhang 2.5)",
                note="추정: Pi 5 포트 가장자리 순서(전원·HDMI 가장자리 쪽부터 RJ45, USB-A 2단, USB-A 2단)와 중심(전원 가장자리에서 "
                     "RJ45 10.25 · USB-A 29 · 47, Pi 3B+ 도면 값 - Pi 5 도면으로 확인), 크기 RJ45 16×21.25×13.5, USB-A 2단 14.5×17.5×16.4, "
                     "보드 끝에서 2.5 튀어나옴(x%.2f); 이 포트 중심 y%.2f" % (face, yc))
    y_s1, y_s2 = ports["USBA1"], ports["USBA2"]

    # ---- USB dongle (L51) + IH190 gender (L52): gender in the LOWER port of the USB-A stack next to the RJ45
    gy0, gy1 = y_s1 - 8.0, y_s1 + 8.0
    gender = box(face, face + 18.0, gy0, gy1, 42.5 + dz, 49.0 + dz)
    out.add("CU-E-GENDER", "IH190 USB-C(F)→USB-A(M) ㄱ자 젠더 (L52)", "Coms IH190 left-angle gender (L52)", g, gender,
            BLACK_PLASTIC, SRC_R + " usb_dongle (gender 18×16×6.5); " + SRC_C + " keep_out pi_usb_plugs (v3 x616..662 y336..392 z39.5..75); " + sft,
            note="추정: RJ45 옆 USB-A 2단(중심 y%.0f)의 아래 포트(z%.1f~%.1f)에 꽂음, y%.0f~%.0f; C 소켓이 -y(RJ45 앞 빈자리)를 향함"
                 % (y_s1, 42.5 + dz, 49.0 + dz, gy0, gy1))
    head = box(621.0 + dx, 629.5 + dx, gy0 - 17.5, gy0 + 6.5, 42.75 + dz, 48.75 + dz)
    sock = cyl_y(651.25 + dx, 38.75 + dz, 345.0 + dy, 370.0 + dy, 10.5)
    loop = tube([sv(625.25, 339.5 + 0.5, 45.75), sv(626.5, 337.6, 41.0), sv(632.0, 338.0, 36.0), sv(640.0, 345.0, 35.0),
                 sv(641.5, 372.0, 35.0), sv(647.0, 377.5, 36.5), sv(651.25, 376.0, 38.75), sv(651.25, 369.5, 38.75)], 3.0)
    out.add("CU-E-DONGLE", "Apple USB-C → 3.5 mm 어댑터 (L51)", "Apple USB-C to 3.5 mm adapter (L51)", g,
            union([head, sock, loop]), WHITE_PLASTIC,
            SRC_R + " usb_dongle (head 8.5×6×24 incl. plug, jack head ~Ø10.5×25, cable ~7 cm); " + SRC_C + " keep_out pi_usb_plugs; " + sft,
            note="추정: 머리가 젠더 C 소켓에 꽂혀 -y로 (RJ45 앞 빈자리), 케이블은 트레이 윗면(z%.1f)으로 내려가 젠더 밑을 지나 +y로 돌아 "
                 "3.5 mm 소켓 머리(트레이 위 y 방향 x%.0f~%.0f y%.0f~%.0f)의 +y 끝에 들어감 - 모두 트레이 keep-out 안; "
                 "케이블 ① W701은 소켓 -y 끝에 꽂힘 - 케이블 ①·②는 모델에 없음"
                 % (CU_IN_Z[0], 646.0 + dx, 656.5 + dx, 345.0 + dy, 370.0 + dy))
    pi_ports = {"face": face, "y_s1": y_s1, "y_s2": y_s2, "zb1": zb1}

    # ---- XH-A232 amp
    ab = shifted_box(comp["앰프 보드"])
    amp_b = diff(box(ab["x"][0], ab["x"][1], ab["y"][0], ab["y"][1], 38.5 + dz, 40.1 + dz),
                 [cyl_z(p[0] + dx, p[1] + dy, 38.49 + dz, 40.11 + dz, 3.2) for p in feat["amp_bosses"]["at"]])
    amp_e = notched_envelope(ab["x"][0], ab["x"][1], ab["y"][0], ab["y"][1], 40.1 + dz, ab["z"][1], 7.0)
    out.add("CU-E-AMP", "XH-A232 (HW-404) TPA3110 2×15 W 앰프 보드", "XH-A232 (HW-404) TPA3110D2 amplifier board", g,
            union([amp_b, amp_e]), COLORS["pcb_blue"],
            SRC_C + " PR-CU-TRAY amp_bosses / components (v3 x664..710 y334..388 z38.5..52.5); " + sft + "; " + SRC_R + " amp_xh_a232 (L53)",
            note="추정: 부품은 모서리 7×7(나사 자리)을 뺀 한 덩어리 z%.1f~%.1f; 구멍 Ø3.2는 보스 자리 - 받은 보드로 확인" % (40.1 + dz, ab["z"][1]))

    # ---- XL4016 buck
    kb = shifted_box(comp["5.1 V 강압 모듈"])
    buck_b = diff(box(kb["x"][0], kb["x"][1], kb["y"][0], kb["y"][1], 38.5 + dz, 40.1 + dz),
                  [cyl_z(p[0] + dx, p[1] + dy, 38.49 + dz, 40.11 + dz, 3.2) for p in feat["buck_bosses"]["at"]])
    buck_e = notched_envelope(kb["x"][0], kb["x"][1], kb["y"][0], kb["y"][1], 40.1 + dz, kb["z"][1], 6.5)
    out.add("CU-E-BUCK", "XL4016 강압 모듈 XH-M401 (20 V → 5.1 V)", "XL4016 buck module XH-M401", g, union([buck_b, buck_e]),
            COLORS["pcb_blue"], SRC_C + " PR-CU-TRAY buck_bosses / components (v3 x608..668.8 y246..286.3 z38.5..67.5); " + sft + "; "
            + SRC_R + " buck_xl4016 (60.8×40.3×29, L58)",
            note="추정: 방열판 2·코일·캐패시터를 모서리 6.5×6.5를 뺀 한 덩어리(z%.1f~%.1f)로 표시" % (40.1 + dz, kb["z"][1]))

    # ---- PED pedal board PB
    pf = feat["ped_board_standoffs"]
    ped_b = diff(box(531.0 + dx, 601.0 + dx, 244.0 + dy, 294.0 + dy, 38.5 + dz, 40.1 + dz),
                 [cyl_z(p[0] + dx, p[1] + dy, 38.49 + dz, 40.11 + dz, 3.2) for p in pf["screw_at"]]
                 + [cyl_z(p[0] + dx, p[1] + dy, 38.49 + dz, 40.11 + dz, 3.0) for p in pf["pin_at"]])
    out.add("CU-E-PEDBOARD", "PED 페달 보드 (5×7 cm 만능기판 70×50)", "PED pedal board PB (5x7 perfboard)", g, ped_b, COLORS["pcb_perf"],
            SRC_C + " PR-CU-TRAY ped_board_standoffs (v3 board x531..601 y244..294 z38.5..40.1, M3 Ø3.2 ×2, pin Ø3.0 ×2); " + sft
            + "; " + SRC_R + " ped_board", material="FR4 만능기판")
    return comp, feat, iof, pi_ports


PED_SHIFT = (578.0 - 75.14 + SHIFT[0], 262.0 - 172.0 + SHIFT[1], 40.1 - 10.6 + SHIFT[2])   # MB Zero layout -> PED board (USB +y)


def ped_zero_parts(M, out):
    it = {i["id"]: i for i in M["module_items"]}
    z = it["zero"]
    dx, dy, dz = PED_SHIFT
    out.add("CU-E-PEDZERO", "RP2040-Zero (PED 보드, 페달용)", "RP2040-Zero on the PED board", "CU 칸 전자부",
            union([bx(b, dx, dy, dz) for b in z["boxes"]]), COLORS["pcb_blue"], SRC_M + " zero (same part/stack as the MB); SEV2; "
            + SRC_L + " shift_from_v3",
            note="추정: PED 보드 위, USB가 +y (v3 자리 x578~596 y262~285.5를 L1 이동), MB와 같은 1.3 틈 핀 헤더 실장")
    plug = bx(it["usb_plug"]["boxes"][0], dx, dy, dz)
    pb = plug.bounding_box()
    cxp, pz = (pb[0] + pb[3]) / 2.0, (pb[2] + pb[5]) / 2.0
    xh = HUB_PORT_X[HUB_PORT["PED"]]
    ly = LANE_Y["PED"]
    pts = [(cxp, pb[4] - 0.5, pz), (cxp, ly, pz + 4.0), (cxp, ly, LANE_Z), (xh, ly, LANE_Z)]
    pts += [(xh, 357.5, DROP_Z - 1.5)] + hub_drop(xh, ly)[3:]
    ln = MODULE_PLUG_L + path_len(pts) + HUB_PLUG_L
    out.add("C-USB-PED", "USB-C 케이블 W208 (PED 보드 → 허브)", "USB cable W208 PED board to hub", "케이블",
            union([plug, tube(pts, CABLE_OD), hub_plug(xh)]), COLORS["cable"],
            SRC_R + " ped_board (USB 8가닥 = 모듈 7 + PED 1) + usb_hub_710u3; " + SRC_L + " low divider top z56.5",
            note="추정: PED Zero USB-C 플러그 뒤(y%.1f)에서 y%.0f로 올라 z%.1f 줄로 낮은 칸막이를 넘어 허브 앞면(y%.1f) 포트 %d(x%.0f)에 꽂힘; "
                 "길이 약 %.0f mm - 경로는 보기용" % (pb[4], ly, LANE_Z, HUB_Y, HUB_PORT["PED"], xh, ln))
    return ln


def cu_small_parts(R, C, F, out, comp, feat, iof):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    g = "CU 칸 전자부"
    dx, dy, dz = SHIFT
    sft = "L1 이동 (x+%.2f, y+%.0f, z%.0f)" % (dx, dy, dz)
    iox, ioy, ioz = IO_SHIFT
    iosft = "L1 I/O 판 구멍 x (v3 + %.2f), 구멍 중심 z%.1f (%s centre.io_plate.holes)" % (iox, IO_HOLE_Z, SRC_L)

    # ---- amp input jack board J702 + PJ-313 at the rear edge facing +y
    jf = feat["amp_input_jack_board_bosses"]
    b = shifted_box(jf["board"])
    jb = diff(bx(b), [cyl_z(p[0] + dx, p[1] + dy, b["z"][0] - 0.01, b["z"][1] + 0.01, 3.2) for p in jf["at"]])
    out.add("CU-E-J702BOARD", "앰프 입력 잭 기판 (만능기판 조각 30×25, J702 + 80 Hz RC)", "amp input jack board J702 (perfboard scrap)", g,
            jb, COLORS["pcb_perf"], SRC_C + " PR-CU-TRAY amp_input_jack_board_bosses (v3 board x676..706 y246..271 z38.5..40.1); " + sft,
            note="추정: 기판 구멍 Ø3.2 (M3×10 → Ø2.7 보스); RC 부품은 작아서 뺌", material="FR4 만능기판")
    d = F["cheeks"]["headphone_jack"]["jack_dims"]
    jx, jy1 = 691.0 + dx, b["y"][1]
    jz = b["z"][1] + d["axis_above_base"]
    out.add("CU-E-J702", "앰프 입력 잭 PJ-313 (J702)", "amp input jack PJ-313 (J702)", g, pj313(d, jx, jz, jy1, +1), BLACK_PLASTIC,
            SRC_C + " amp_input_jack_board_bosses note (jack on the rear edge at v3 x691 facing +y); " + sft + "; " + PJ313_SRC,
            note="추정: 몸체 x%.2f~%.2f y%.1f~%.0f z%.1f~%.1f(기판 윗면), 축 z%.1f, 코 Ø%.0f가 기판 뒤끝 y%.0f에서 y%.1f까지 - 받은 부품으로 확인"
                 % (jx - d["body_W"] / 2, jx + d["body_W"] / 2, jy1 - d["body_L"], jy1, b["z"][1], b["z"][1] + d["body_H"], jz,
                    d["nose_d"], jy1, jy1 + d["nose_L"]))

    # ---- fuse holder BU914 in its cradle
    fb = shifted_box(comp["퓨즈 홀더"])
    fy = (fb["y"][0] + fb["y"][1]) / 2.0
    fz = (fb["z"][0] + fb["z"][1]) / 2.0
    out.add("CU-E-FUSE", "BU914 인라인 퓨즈 홀더 + 5 A T 퓨즈", "Coms BU914 inline fuse holder + 5 A T fuse", g,
            cyl_x(fy, fz, fb["x"][0], fb["x"][1], fb["y"][1] - fb["y"][0]), BLACK_PLASTIC,
            SRC_C + " PR-CU-TRAY components 퓨즈 홀더 (v3 x632..678 y306..316 z35.5..45.5) + fuse_holder_cradle (inner Ø10.5); " + sft
            + "; " + SRC_R + " fuse_holder_bu914",
            note="추정: 지름 10 (받침 Ø10.5에 맞춤; electronics_rearbar는 Ø12×45 추정) - 받은 홀더로 확인, 선은 뺌")

    # ---- I/O plate (L1: y435.5..447, z16.5..76.5; holes at z46.5): pedal jack J501 on its scrap board on the plate ledge
    ph = iof["pedal_jack_hole"]
    cxj = IO["holes"]["pedal_jack_J501_x"]
    czj = IO_HOLE_Z
    led = shifted_box(ph["mount"]["box"], (iox, ioy, 0.0))    # x / y of the v3 ledge moved; z follows the jack axis
    zt = czj - d["axis_above_base"]                           # board top z44.0
    zbb = zt - 1.6                                            # board bottom z42.4 = required ledge top
    jbrd = diff(box(led["x"][0], led["x"][1], led["y"][0], led["y"][1], zbb, zt),
                [cyl_z(551.0 + iox, 392.0 + ioy, zbb - 0.01, zt + 0.01, 3.2), cyl_z(569.0 + iox, 402.0 + ioy, zbb - 0.01, zt + 0.01, 3.2)])
    out.add("CU-E-J501BOARD", "페달 잭 기판 (만능기판 조각 25×24, J501)", "pedal jack J501 perfboard scrap", g, jbrd, COLORS["pcb_perf"],
            SRC_C + " PR-IO-PLATE pedal_jack_hole mount (v3 ledge x547.5..572.5 y384..408, M3×10 at (551,392)/(569,402)); " + iosft
            + "; board z from the PJ-313 axis: z46.5 − 2.5 − 1.6; " + PJ313_SRC,
            note="추정: 기판 x%.2f~%.2f y%.0f~%.0f z%.1f~%.1f (잭 축 z%.1f − 축 높이 %.1f = 기판 윗면 %.1f) → I/O 판 잭 선반 윗면은 z%.1f "
                 "이어야 함; 기판 구멍 Ø3.2" % (led["x"][0], led["x"][1], led["y"][0], led["y"][1], zbb, zt, czj, d["axis_above_base"],
                                             zt, zbb), material="FR4 만능기판")
    skin = next(p for p in C["printed"] if p["id"] == "PR-IO-PLATE")["structure"]["outer_skin_y"]   # v3 [408, 410]
    fy_ = skin[1] + ioy - d["nose_L"]                         # body front face 444.5, nose tip flush with the outer face y447
    out.add("CU-E-J501", "페달 잭 PJ-313 (J501, I/O 판)", "pedal jack PJ-313 (J501) in the I/O plate", g,
            pj313(d, cxj, czj, fy_, +1), BLACK_PLASTIC,
            "position " + SRC_L + " centre.io_plate.holes pedal_jack_J501_x %.2f, z%.1f; v3 " % (cxj, czj) + SRC_C
            + " PR-IO-PLATE pedal_jack_hole (Ø6.5 through the 2.0 skin); " + PJ313_SRC,
            note="추정: 몸체 x%.2f~%.2f y%.1f~%.1f z%.1f~%.1f (기판 위), 축 = 구멍 중심 x%.2f z%.1f; 몸체 앞면 y%.1f(바깥 판 안쪽면 y%.0f와 "
                 "0.5 틈)라 코 Ø%.0f×%.1f 끝이 바깥면 y%.0f과 같은 면 - 받은 부품으로 확인"
                 % (cxj - d["body_W"] / 2, cxj + d["body_W"] / 2, fy_ - d["body_L"], fy_, zt, zt + d["body_H"], cxj, czj, fy_,
                    skin[0] + ioy, d["nose_d"], d["nose_L"], skin[1] + ioy))

    # ---- I/O plate: KCD1-101A rocker. v3 modelled one 13.2 x 19.2 x 21 box; in L1 the plate hole (x646.05, z46.5) puts that
    # box 1.25 into the Pi 5 GPIO-edge USB-A stack (y..427.25, z..40.5), so the rearbar spec's split is used:
    # housing 13 behind the bezel + two 4.8 quick-connect lugs 8 long (spec 'KCD1 typical body depth ~13 + lugs 8')
    sw = rb["power_switch_kcd1"]
    cxs, czs = IO["holes"]["switch_KCD1_x"], IO_HOLE_Z
    bez, body = sw["boxes"][0], sw["boxes"][1]
    bw, bh = bez["x"][1] - bez["x"][0], bez["z"][1] - bez["z"][0]
    dw, dh = body["x"][1] - body["x"][0], body["z"][1] - body["z"][0]
    by1 = body["y"][1] + ioy                                   # 447 (plate outer face)
    hb0 = by1 - 13.0                                           # housing back face y434
    lb0 = by1 - (body["y"][1] - body["y"][0])                  # lug tips y426
    lugs = [box(cxs - 2.4, cxs + 2.4, lb0, hb0 + 0.01, zl - 0.4, zl + 0.4) for zl in (czs - 4.0, czs + 4.0)]
    sws = union([box(cxs - bw / 2, cxs + bw / 2, bez["y"][0] + ioy, bez["y"][1] + ioy, czs - bh / 2, czs + bh / 2),
                 box(cxs - dw / 2, cxs + dw / 2, hb0, by1 + 0.01, czs - dh / 2, czs + dh / 2)] + lugs)
    out.add("CU-E-SWITCH", "KCD1-101A 로커 스위치 (I/O 판)", "KCD1-101A rocker switch", g, sws, BLACK_PLASTIC,
            SRC_R + " power_switch_kcd1 (bezel 15×21×2 outside the plate, body 13.2×19.2 = 'depth ~13 + lugs 8', 4.8 lugs); position "
            + SRC_L + " centre.io_plate.holes switch_KCD1_x %.2f, z%.1f (rocker vertical, cut-out 13.2×19.2 as v3)" % (cxs, czs),
            note="추정: 몸통 13.2×19.2×13 (y%.0f~%.0f) + 4.8×0.8 단자 2개 8 길이 (y%.0f~%.0f, z%.1f/%.1f 중심) - v3의 21 깊이 상자는 "
                 "Pi 5 GPIO 쪽 USB-A 2단(y..%.2f, z..%.1f)과 1.25 겹쳐서 spec 설명대로 몸통+단자로 나눔; 아래 단자와 USB-A 2단 윗면 틈 약 1.6 → "
                 "납땜 후 선을 위로 꺾음(파스톤 단자 끼우면 닿음) - 받은 스위치로 확인; 베젤이 뒤판 바깥으로 2 mm 나옴(y%.0f~%.0f)"
                 % (hb0, by1, lb0, hb0, czs - 4.0, czs + 4.0, 373.0 + 47.0 + 7.25, 24.1 + 16.4, bez["y"][0] + ioy, bez["y"][1] + ioy))

    # ---- I/O plate: USB-C power input = HUSB238 PD trigger in the plate pocket (x696.05, z46.5)
    pd = rb["pd_trigger_husb238"]["boxes"][0]
    cxu = IO["holes"]["usb_c_input_x"]
    cav = shifted_box(iof["usb_c_input"]["pocket"]["cavity"], IO_SHIFT)
    pw = pd["x"][1] - pd["x"][0]
    pl = pd["y"][1] - pd["y"][0]
    ph_ = pd["z"][1] - pd["z"][0]
    ye = cav["y"][1]                                   # receptacle mouth flush with the skin inner face y445
    zc = (cav["z"][0] + cav["z"][1]) / 2.0             # 46.5
    z0 = zc - ph_ / 2.0
    pcb_ = box(cxu - pw / 2, cxu + pw / 2, ye - pl, ye, z0, z0 + 1.2)
    rcpt = box(cxu - 4.47, cxu + 4.47, ye - 7.3, ye, z0 + 1.2, z0 + ph_)
    out.add("CU-E-PDTRIG", "HUSB238 PD 트리거 + USB-C 전원 입력 (L57, I/O 판 포켓)", "HUSB238 USB-C PD trigger (L57) in the I/O-plate pocket", g,
            union([pcb_, rcpt]), COLORS["pcb_blue"],
            SRC_R + " pd_trigger_husb238 (10×16.4×4.4); position " + SRC_L + " usb_c_input_x %.2f, z%.1f; v3 pocket cavity moved to "
            "x%.2f..%.2f y%.1f..%.0f z%.1f..%.1f" % (cxu, IO_HOLE_Z, cav["x"][0], cav["x"][1], cav["y"][0], cav["y"][1], cav["z"][0], cav["z"][1]),
            note="추정: 기판 1.2 + USB-C 리셉터클 8.94×7.3×3.2 (+y 끝)로 나눔")


def hub_bank_parts(R, C, out):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    g = "보조배터리 칸"
    h = rb["usb_hub_710u3"]["boxes"][0]
    assert abs((h["x"][1] - h["x"][0]) - HUB_L) < 1e-6 and abs((h["y"][1] - h["y"][0]) - HUB_W) < 1e-6
    out.add("PB-E-HUB", "NEXTU 710U3 10포트 유전원 USB 허브", "NEXTU 710U3 10-port powered USB hub", g,
            box(HUB_X0, HUB_X1, HUB_Y, HUB_BACK, HUB_Z0, HUB_Z0 + HUB_H), HUB_GREY,
            SRC_R + " usb_hub_710u3 (228×48×24 flat on the bay floor, L17; v3 A18 taped to the back wall); " + SRC_L
            + " centre.bays_inner_x power_bank %s, inner y..435.5, floor z16.5" % BAYS["power_bank"],
            note="추정: 포트 위치 미확인 - 아래 포트 10개를 앞면(y%.1f, -y 쪽) x%.0f+22i, z%.1f에, 업스트림을 -x 끝면(y%.1f z%.1f)에 둔 것으로 표시; "
                 "허브를 칸 오른쪽 끝판에서 0.5 띄움(x%.0f~%.0f) - 칸 폭 248.7에서 허브 228을 빼면 20.7뿐이라 곧은 업스트림 플러그(20)+굽힘이 "
                 "안 들어가 ㄱ자(위로 꺾인) 플러그로 표시 (C-USB-UPSTREAM)" % (HUB_Y, HUB_PORT_X[0], HUB_Z, HUB_UP_YZ[0], HUB_UP_YZ[1],
                                                                          HUB_X0, HUB_X1))
    pbx = rb["power_bank_mt65"]["boxes"][0]
    hold = shifted_box(next(p for p in C["printed"] if p["id"] == "PR-PB-HOLDER")["geometry"]["battery_pocket"])
    L = pbx["x"][1] - pbx["x"][0]
    W = pbx["y"][1] - pbx["y"][0]
    T = pbx["z"][1] - pbx["z"][0]
    x0, y0, z0 = hold["x"][0], hold["y"][0], hold["z"][0]
    out.add("PB-E-BANK", "모루이 MT-65 보조배터리 (20000 mAh, 65 W)", "Morui MT-65 65 W 20000 mAh power bank (optional O07)", g,
            box(x0, x0 + L, y0, y0 + W, z0, z0 + T), BANK_GREY,
            SRC_R + " power_bank_mt65 (105×71×32); " + SRC_C + " PR-PB-HOLDER battery_pocket moved by the L1 CU shift "
            "(front-left corner stop x%.2f / y%.1f, floor z%.1f)" % (x0, y0, z0),
            note="추정: 받침(본체 담당)이 v3 자리에서 CU와 같이 (x+36.05, y+37, z−17) 옮겨진다고 보고 앞·왼쪽 멈춤벽에 붙임 "
                 "(x%.2f~%.2f y%.1f~%.1f z%.1f~%.1f); 선택품(O07)" % (x0, x0 + L, y0, y0 + W, z0, z0 + T))


def hub_upstream(out, pi):
    """Pi 5 USB-A (UPPER port of the GPIO-edge stack) -> up over the amp -> lane y408 z60.5 over the low divider -> down into an
    up-angled USB plug on the hub -x end face."""
    face, ys = pi["face"], pi["y_s2"]
    zc = pi["zb1"] + 16.4 - 4.0                              # upper port centre (stack top - 4)
    up = box(face, face + 25.0, ys - 8.0, ys + 8.0, zc - 4.0, zc + 4.0)
    uy, uz = HUB_UP_YZ
    # right-angle plug: nose/body 16 along x into the end face, head turned up to z44 (cable leaves upward)
    ra = union([box(HUB_X0 - 16.0, HUB_X0, uy - 8.0, uy + 8.0, uz - 4.0, uz + 4.0),
                box(HUB_X0 - 16.0, HUB_X0 - 6.0, uy - 8.0, uy + 8.0, uz + 3.99, 44.0)])
    xr = HUB_X0 - 11.0
    xu = face + 30.5
    pts = [(face + 24.5, ys, zc), (xu, ys, zc + 4.5), (xu, ys - 7.0, LANE_Z - 5.0), (xu + 3.0, UP_LANE_Y, LANE_Z),
           (xr, UP_LANE_Y, LANE_Z), (xr, uy, 52.0), (xr, uy, 43.5)]
    ln = 25.0 + path_len(pts) + 16.0
    out.add("C-USB-UPSTREAM", "USB 허브 업스트림 케이블 W209 (허브 → Pi 5 USB-A)", "hub upstream cable W209 (hub to Pi 5 USB-A)", "케이블",
            union([up, tube(pts, 4.0), ra]), COLORS["cable"],
            SRC_C + " keep_out pi_usb_plugs (hub upstream plug W209 + L52 gender + L51 dongle) moved by the L1 shift; " + SRC_R
            + " cables_simple 'hub upstream → Pi USB-A'; " + SRC_L + " low divider top z56.5",
            note="추정: Pi 5 GPIO 쪽 USB-A 2단(중심 y%.0f)의 위 포트(z%.1f~%.1f)에 곧은 USB-A 플러그 25, 허브 -x 끝면(x%.0f, y%.1f z%.1f)에는 "
                 "ㄱ자(위로 꺾인) 플러그 16×16×8 + 머리 z44까지 - 곧은 플러그는 칸 폭이 모자람 (허브 228 + 20 + 굽힘 > 248.7) → "
                 "ㄱ자 업스트림 케이블/젠더 필요(BOM 확인); OD 4, z%.1f 줄(y%.0f)로 낮은 칸막이를 넘음; 길이 약 %.0f mm"
                 % (ys, zc - 4.0, zc + 4.0, HUB_X0, uy, uz, LANE_Z, UP_LANE_Y, ln))
    return ln


# ------------------------------------------------------------------ XT30 pairs (speaker lines) at the speaker front faces

# L1 speaker.xt30: holders in the trough on the speaker front face (y <= 252), clear of the module USB cables (floor, z<=22).
# The speaker-side XT30U-F sits in the holder pocket the body generator exports (body.XT30_POCKET = (x0, x1, y0, y1, z0, z1),
# mouth toward the centre unit); if body.py cannot be imported the fallback pose below is used (female on edge in front of
# the speaker front face, centre z32, x168..180.4 - clear of the grille zone x..165.5).
XT30_FALLBACK = {"L": (168.0, 180.6, 244.1, 249.7, 26.7, 37.3)}
XT30_FALLBACK["R"] = (2 * MIRROR_X - 180.6, 2 * MIRROR_X - 168.0, 244.1, 249.7, 26.7, 37.3)


def xt30_pockets():
    try:
        import body_L1 as _body            # archived L1 pair (body.py is L2 now)
        pk = getattr(_body, "XT30_POCKET")
        return {s: tuple(float(v) for v in pk[s]) for s in "LR"}, "body.py XT30_POCKET"
    except Exception as ex:                     # body.py missing / mid-edit
        return dict(XT30_FALLBACK), "fallback (body.py XT30_POCKET 없음: %s)" % type(ex).__name__


def xt30_parts(R, out):
    rb = {i["id"]: i for i in R["rearbar_items"]}
    pair = rb["xt30_pair_L"]["boxes"][0]
    fw = pair["y"][1] - pair["y"][0]                    # 10.2 face width
    ft = pair["z"][1] - pair["z"][0]                    # 5.2 face thickness
    LF, LM, ENG = 12.4, 13.7, 5.6                       # female / male length, engaged length (BOM L61 / audio.md §4)
    pockets, psrc = xt30_pockets()
    for side in "LR":
        x0, x1, y0, y1, z0, z1 = pockets[side]
        yc, zc = (y0 + y1) / 2.0, (z0 + z1) / 2.0
        # face 10.2 x 5.2 oriented like the pocket cross-section (longer side of the pocket gets the 10.2)
        hy, hz = (fw / 2, ft / 2) if (y1 - y0) >= (z1 - z0) else (ft / 2, fw / 2)
        if side == "L":                                 # mouth +x (toward the centre unit)
            mouth = x1
            fem = box(mouth - LF, mouth, yc - hy, yc + hy, zc - hz, zc + hz)
            mal = box(mouth, mouth + LM - ENG, yc - hy, yc + hy, zc - hz, zc + hz)
        else:
            mouth = x0
            fem = box(mouth, mouth + LF, yc - hy, yc + hy, zc - hz, zc + hz)
            mal = box(mouth - (LM - ENG), mouth, yc - hy, yc + hy, zc - hz, zc + hz)
        src = (SRC_R + " xt30_pair_%s (face 10.2×5.2, M 13.7 + F 12.4 − 5.6 engaged); position %s pocket %s = %s speaker.xt30 "
               "(통로 안 스피커 앞면 y≤252, USB 선을 막지 않는 높이)" % (side, psrc, side, SRC_L))
        out.add("C-XT30F-%s" % side, "XT30U-F 암 (스피커 쪽, XT30 받침 %s 안)" % side, "XT30U-F female in holder " + side, "케이블",
                fem, XT30_YELLOW, src,
                note="추정: 몸체를 10.2×5.2×12.4 상자로; 받침 홈(x%.1f~%.1f y%.1f~%.1f z%.1f~%.1f) 가운데, 입구를 홈 입구 x%.1f(가운데 유닛 쪽)에 맞춤"
                     % (x0, x1, y0, y1, z0, z1, mouth))
        out.add("C-XT30M-%s" % side, "XT30U-M 수 (앰프 쪽, 가운데 유닛 쪽으로 꽂힘) %s" % side, "XT30U-M male (mated) " + side, "케이블",
                mal, XT30_YELLOW, src, note="추정: 암 속으로 들어간 5.6은 빼고 밖에 보이는 8.1만 표시; 18 AWG 선은 뺌")


# ------------------------------------------------------------------ speakers on the 30 deg slanted baffles

SPK = L1["speaker"]["driver"]
SPK_C = {"L": (SPK["x_centre"]["L"], SPK["centre_yz"][0], SPK["centre_yz"][1]),
         "R": (SPK["x_centre"]["R"], SPK["centre_yz"][0], SPK["centre_yz"][1])}
_A = math.radians(L1["speaker"]["front"]["slant_outer_face"]["angle_from_vertical_deg"])
SPK_N = (0.0, -math.cos(_A), math.sin(_A))       # driver axis (out of the baffle, toward the player and up)
SPK_U = (0.0, math.sin(_A), math.cos(_A))        # up the slant
GASKET_T = 3.0                                   # EVA gasket 3T between the outer face and the flange (L1 driver.mount)


def spk_frame(cx, cy, cz):
    """local (a = x, b = up the slant, w = along the axis, 0 at the baffle outer face) -> world."""
    M = np.array([[1.0, SPK_U[0], SPK_N[0], cx],
                  [0.0, SPK_U[1], SPK_N[1], cy],
                  [0.0, SPK_U[2], SPK_N[2], cz]])
    return M


def speaker_local(R):
    sp = R["speakers"][0]
    fl = sp["boxes"][0]
    frame = fl["x"][1] - fl["x"][0]                    # 105
    ft = fl["y"][1] - fl["y"][0]                       # 4
    cyls = {c["name"].split()[0]: c for c in sp["cylinders"]}
    basket, magnet = cyls["basket"], cyls["magnet"]
    bd, md = basket["d"], magnet["d"]                  # 94, 85
    b_len = basket["range"][1] - basket["range"][0]    # 37 (v3 y215..252)
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
                  "magnet_w": (-(b_len + m_len), -b_len)}


def speaker_parts(R, out):
    local, info = speaker_local(R)
    assert abs(info["depth"] - SPK["depth_total"]) < 1e-6
    for side in "LR":
        sp = next(s for s in R["speakers"] if s["id"].endswith(side))
        cx, cy, cz = SPK_C[side]
        body = local.transform(spk_frame(cx, cy, cz))
        mlow = cz + info["magnet_w"][0] * SPK_N[2] - info["md"] / 2 * SPK_U[2]
        out.add("SPK-%s" % side, sp["name_ko"], sp["name_en"], "스피커 유닛", body, COLORS["speaker"],
                SRC_R + " speakers %s (flange 105×105×4 with 4 slots Ø4.8×6.8 on PCD 115; basket Ø94 × 37; magnet Ø85×17; depth 61); "
                "pose " % sp["id"] + SRC_L + " speaker.driver (centre x%.1f y%.2f z%.1f on the slanted outer face, axis (-cos30, +sin30), "
                "front-mounted: flange 4 + EVA gasket 3 on the face)" % (cx, cy, cz),
                note="추정: 플랜지를 경사 바깥면에서 가스켓 3 앞(법선 방향 %.0f~%.0f)에, 바스켓 테두리를 가스켓 구멍 안으로 이어 한 덩어리로; "
                     "자석이 바깥면 뒤 37~54, 가장 낮은 곳은 자석 뒷면 아래 모서리 z%.2f (아랫판 윗면 z16.5 위 %.2f - 유닛을 경사 가운데에서 1.0 올려 목표 +2 충족); "
                     "콘 오목면(Ø90→Ø34, 깊이 24)과 더스트캡은 보기용" % (GASKET_T, GASKET_T + info["ft"], mlow, mlow - CU_IN_Z[0]))
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


def headphone_jack(F, R, out):
    hj = F["cheeks"]["headphone_jack"]
    d = hj["jack_dims"]
    pk = hj["pocket"]
    cx, az = pk["centre_x"], pk["axis_z"]
    y0 = pk["front_wall"]["y"][1]
    out.add("EL-E-J701", "헤드폰 잭 PJ-313 (J701, 왼쪽 볼 앞면)", "headphone jack PJ-313 (J701) in the left cheek", "끝 부속 왼쪽 전자부",
            pj313(d, cx, az, y0, -1), BLACK_PLASTIC,
            "spec/keyaction_features_frame.json cheeks.headphone_jack (pocket centre x-8.34, axis z20, cavity y2.5..14.2, nose Ø5.0 through y0..2.5); "
            + PJ313_SRC + "; " + SRC_R + " headphone_jack_j701",
            note="추정: 포켓 위치·축 높이 z20 (frame spec assumed); 다리(밑 3.2)와 케이블 ①·②는 뺌")


# ------------------------------------------------------------------ R31 touchscreen: TD2 7" display, DSI ribbon, J1 power lead

G_TSE = "터치스크린 전자부"
G_TSF = "터치스크린 (접은 상태, 별도 보기)"
TD2_LENS_T = 0.7                                   # drawing: 0.7 lens
TD2_BODY = (168.55, 99.71, 6.42)                   # drawing: metal back 168.55 x 99.71, lens front -> body back 6.42 (14.92 - 8.5)
TD2_BODY_OFF = (6.45, 10.265)                      # drawing: body 6.45 from the glass edge at the +x end (portrait top), centred in u
TD2_LUG = (9.0, 14.0, 3.0)                         # 추정: lug bracket x 9 (numbers: x581.5..590.5), u 14 (drawing ~15 at the body), 3.0 tall
TD2_STANDOFF = (5.0, 14.92)                        # drawing: Ø5.0 standoffs to 14.92 from the lens front
TD2_DSI_T = 2.0                                    # drawing: adapter area 2.0 behind the body
TD2_J1_T = 2.6                                     # 추정
RIB_T = 0.3                                        # FFC thickness (추정)
RIB_W_IN = 9.2                                     # ribbon centre w in the cradle (0.2 in front of the back plate w9.4)
RIB_W_CLIP = 9.95                                  # in the clip channel (recess floor w10.1)
PI_DISP1 = (614.0, 617.0, 374.0, 389.0, 4.0)       # numbers/cable: Pi 5 MIPI connector x614..617, y374..389; height 4 추정
WIRE_D = 2.0                                       # 2 jumper wires side by side, round envelope (추정)


def _rrect(x0, x1, y0, y1, r, n=8):
    pts = []
    for (cx, cy, a0) in ((x1 - r, y0 + r, 270), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        pts += [(cx + r * math.cos(math.radians(a0 + 90.0 * i / n)), cy + r * math.sin(math.radians(a0 + 90.0 * i / n))) for i in range(n + 1)]
    return pts


def _thick(points, t, n=8):
    """planar thick polyline (capsules of width t between consecutive 2D points), CCW polygons for prism_*."""
    from manifold3d import CrossSection, FillRule
    r = t / 2.0
    caps = []
    for (a, b) in zip(points[:-1], points[1:]):
        pts = [(a[0] + r * math.cos(2 * math.pi * i / n), a[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        pts += [(b[0] + r * math.cos(2 * math.pi * i / n), b[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        caps.append(CrossSection([pts], FillRule.NonZero).hull())
    cs = caps[0]
    for c in caps[1:]:
        cs = cs + c
    return cs


def _prism_cs(cs, axis, a0, a1):
    solids = [{"x": prism_x, "y": prism_y, "z": prism_z}[axis]([tuple(p) for p in poly], a0, a1) for poly in cs.to_polygons()]
    return union(solids)


def _bezier(p0, p1, p2, p3, n=16):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _path_len(pts):
    return sum(math.dist(a, b) for a, b in zip(pts[:-1], pts[1:]))


def td2_local():
    """Touch Display 2 7" envelope in the cradle frame (x, u, w): lens, metal body, 4 lugs (M2.5, hole Ø2.6), 4 Ø5 standoffs,
    DSI connector (opens -x) and J1."""
    gx0, gx1 = TS.GLASS_X
    gu1 = TS.GLASS[1]
    lens = prism_z(_rrect(gx0, gx1, 0.0, gu1, 8.0), 0.0, TD2_LENS_T)
    bw, bh, bt = TD2_BODY
    bx1 = gx1 - TD2_BODY_OFF[0]
    bx0 = bx1 - bw
    bu0 = TD2_BODY_OFF[1]
    body = box(bx0, bx1, bu0, bu0 + bh, TD2_LENS_T - 0.01, bt)
    wl0, wl1 = TS.BACK_W[0] - TD2_LUG[2], TS.BACK_W[0]
    lugs, lug_holes = [], []
    for x in TS.LUG_X:
        for u in TS.LUG_U:
            lugs.append(box(x - TD2_LUG[0] / 2, x + TD2_LUG[0] / 2, u - TD2_LUG[1] / 2, u + TD2_LUG[1] / 2, wl0 - 0.01, wl1))
            lug_holes.append(cyl_z(x, u, bt - 0.6, wl1 + 0.01, 2.6))          # screw seat, 0.6 into the body (screw tip room)
    sd, sw = TD2_STANDOFF
    stand = [cyl_z(x, u, bt - 0.01, sw, sd) for x in TS.STANDOFF_X for u in TS.STANDOFF_U]
    dx0 = TS.DSI["open_x"]
    dx1 = 2 * TS.DSI["x_centre"] - dx0
    du0, du1 = TS.DSI["u"]
    dsi = box(dx0, dx1, du0, du1, bt - 0.01, bt + TD2_DSI_T)
    j1 = box(TS.J1["x"][0], TS.J1["x"][1], TS.J1["u"][0], TS.J1["u"][1], bt - 0.01, bt + TD2_J1_T)
    return diff(union([lens, body, dsi, j1] + lugs + stand), lug_holes), (bx0, bx1, bu0, bu0 + bh), (dx0, dx1)


def fillet(points, r, n=6):
    """2D polyline with every interior corner replaced by a circular arc of radius r (reduced where the segments are short)."""
    out = [points[0]]
    for i in range(1, len(points) - 1):
        A, B, C = points[i - 1], points[i], points[i + 1]
        l1, l2 = math.dist(A, B), math.dist(B, C)
        d1 = ((B[0] - A[0]) / l1, (B[1] - A[1]) / l1)
        d2 = ((C[0] - B[0]) / l2, (C[1] - B[1]) / l2)
        cr = d1[0] * d2[1] - d1[1] * d2[0]
        th = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
        if th < 1e-6:
            out.append(B)
            continue
        rr = min(r, 0.49 * min(l1, l2) / math.tan(th / 2))
        t = rr * math.tan(th / 2)
        T1 = (B[0] - d1[0] * t, B[1] - d1[1] * t)
        nrm = (-d1[1], d1[0]) if cr > 0 else (d1[1], -d1[0])
        c = (T1[0] + nrm[0] * rr, T1[1] + nrm[1] * rr)
        a0 = math.atan2(T1[1] - c[1], T1[0] - c[0])
        sgn = 1.0 if cr > 0 else -1.0
        out += [(c[0] + rr * math.cos(a0 + sgn * th * k / n), c[1] + rr * math.sin(a0 + sgn * th * k / n)) for k in range(n + 1)]
    out.append(points[-1])
    return out


def loop_r(p0, p1, phi1, R=10.5, n=10):
    """hinge loop in (y, z): from p0 heading +z to p1 heading phi1 (deg from +z toward -y) as straight s0 + arc R (turning toward
    -y by a) + straight L + arc R (back to phi1); a chosen to keep both straights longest."""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    f1 = math.radians(phi1)
    best = None
    for k in range(1, 700):
        a = f1 + math.radians(0.1 * k)
        if a > math.radians(85):
            break
        L = (-dy - R * (1 + math.cos(f1) - 2 * math.cos(a))) / math.sin(a)
        s0 = dz - R * (2 * math.sin(a) - math.sin(f1)) - L * math.cos(a)
        if L >= 0 and s0 >= 0 and (best is None or min(L, s0) > best[0]):
            best = (min(L, s0), a, L, s0)
    if best is None:
        return None
    _, a, L, s0 = best
    pts = [p0, (p0[0], p0[1] + s0)]
    c1 = (pts[-1][0] - R, pts[-1][1])
    pts += [(c1[0] + R * math.cos(a * k / n), c1[1] + R * math.sin(a * k / n)) for k in range(1, n + 1)]
    q = (pts[-1][0] - L * math.sin(a), pts[-1][1] + L * math.cos(a))
    pts.append(q)
    c2 = (q[0] + R * math.cos(a), q[1] + R * math.sin(a))
    pts += [(c2[0] - R * math.cos(a - (a - f1) * k / n), c2[1] - R * math.sin(a - (a - f1) * k / n)) for k in range(1, n + 1)]
    return pts


RIB_LOOP_R = 10.5            # D24: hinge loop R10 or more


def ribbon_paths(theta=TS.TILT_USE):
    """DSI ribbon centre lines: Pi part (x, z) swept over y, main part (y, z) swept over x597..613 (from the Pi fold through the
    lid hole and the hinge loop into the cradle slot), in-cradle rise (u, w), in-cradle run to the connector (x, w).
    Corners are filleted: R2 at the Pi exit (design.json), R3 where the ribbon is held, R10.5 in the hinge loop (D24)."""
    rx0, rx1 = TS.RIBBON_X
    py0 = (PI_DISP1[2] + PI_DISP1[3]) / 2.0 - TS.RIBBON_W / 2.0      # 373.5 .. 389.5
    zp = 35.15                                                        # over the heatsink z32.1 / HDMI, design 'z35'
    e = RIB_T / 2.0
    pi_xz = fillet([(PI_DISP1[0] + 0.5, 25.4), (610.5, 25.4), (610.5, zp), (rx0 + e, zp)], 2.0)
    zf = zp + 0.27                                                    # second layer of the 45 deg fold
    zl = TS.LID_Z0 - e                                               # 76.35 under the lid (in the clip channel)
    yv = 296.0                                                       # vertical run in the lid hole y292..298
    ent_uw = fillet([(-3.5, 14.6), (-0.8, 11.6), (1.6, RIB_W_IN), (7.6, RIB_W_IN), (8.3, RIB_W_CLIP), (21.7, RIB_W_CLIP), (22.4, RIB_W_IN),
                     (TS.DSI["u"][1], RIB_W_IN)], 3.0)
    pw = TS.pt(*ent_uw[0], theta)
    q1 = TS.pt(*ent_uw[1], theta)
    phi1 = math.degrees(math.atan2(-(q1[0] - pw[0]), q1[1] - pw[1]))
    loop = loop_r((yv, TS.LID_Z1), pw, phi1, RIB_LOOP_R)
    lower = fillet([(py0 + TS.RIBBON_W - e, zf), (372.0, zf), (338.0, zl), (yv + 3.0 + 3.0, zl), (yv, zl), (yv, TS.LID_Z1)], 3.0)
    main_yz = lower + loop[1:]
    run_xw = fillet([(rx0 + e, RIB_W_IN - RIB_T + 0.02), (622.0, RIB_W_IN - RIB_T + 0.02), (628.2, 7.45), (TS.DSI["open_x"] + 3.0, 7.45)], 3.0)
    return {"pi_xz": pi_xz, "pi_y": (py0, py0 + TS.RIBBON_W), "main_yz": main_yz, "cr_uw": ent_uw, "run_xw": run_xw,
            "run_u": tuple(TS.DSI["u"]), "loop": loop, "loop_R": RIB_LOOP_R}


def ribbon_solid(theta=TS.TILT_USE):
    P = ribbon_paths(theta)
    rx0, rx1 = TS.RIBBON_X
    pi = _prism_cs(_thick(P["pi_xz"], RIB_T), "y", *P["pi_y"])
    main = _prism_cs(_thick(P["main_yz"], RIB_T), "x", rx0, rx1)
    cr = _prism_cs(_thick(P["cr_uw"], RIB_T), "x", rx0, rx1)
    run = _prism_cs(_thick(P["run_xw"], RIB_T), "y", *P["run_u"])
    sol = union([pi, main, TS.place(union([cr, run]), theta)])
    # centre-line length, 45 deg folds counted at the fold centres (x605 over the Pi, u60.1 in the cradle), ZIF insertions left out
    xf = (rx0 + rx1) / 2.0
    ufc = (TS.DSI["u"][0] + TS.DSI["u"][1]) / 2.0
    pts_cr = [TS.pt(u, w, theta) for (u, w) in P["cr_uw"]]
    ln = {"pi": _path_len(P["pi_xz"]) - 0.5 - (xf - rx0 - RIB_T / 2.0),
          "main": _path_len(P["main_yz"]) - (P["main_yz"][0][0] - (P["pi_y"][0] + P["pi_y"][1]) / 2.0),
          "cradle": _path_len(pts_cr) - (TS.DSI["u"][1] - ufc),
          "run": _path_len(P["run_xw"]) - (xf - rx0 - RIB_T / 2.0) - 3.0, "loop": _path_len(P["loop"])}
    ln["total"] = ln["pi"] + ln["main"] + ln["cradle"] + ln["run"]
    return sol, ln


def power_lead(theta=TS.TILT_USE):
    """J1 power lead (world): 2 jumper housings on Pi GPIO 2 (5 V) / 6 (GND), up to z50, forward along the left wall at z55, into
    the lid hole beside the ribbon (x593.8, y293.3), hinge loop, cradle slot, behind the glass border (u5) to x652.5, up the gap
    to the J1 plug."""
    hx = (574.15, 581.77)
    hy = (426.8 - 1.27, 426.8 + 1.27)
    hz0 = 32.6
    housing = box(hx[0], hx[1], hy[0], hy[1], hz0, hz0 + 8.0)
    xw, yw = 593.8, 293.3
    bay = [(577.96, 426.8, hz0 + 7.5), (577.96, 426.8, 50.0), (570.0, 421.0, 55.0), (567.5, 410.0, 55.0), (567.5, 306.0, 55.0),
           (569.5, 300.0, 65.5), (590.0, 294.5, 66.5), (xw, yw, 71.0), (xw, yw, TS.LID_Z1)]
    ent_uw = [(-3.5, 12.5), (1.0, 8.5), (3.5, 5.0)]
    pw = TS.pt(*ent_uw[0], theta)
    p1 = TS.pt(*ent_uw[1], theta)
    L = math.dist(pw, p1)
    dirw = ((p1[0] - pw[0]) / L, (p1[1] - pw[1]) / L)
    loop = _bezier((yw, TS.LID_Z1), (yw, TS.LID_Z1 + 4.0), (pw[0] - 4.0 * dirw[0], pw[1] - 4.0 * dirw[1]), pw)
    loop3 = [(xw, y, z) for (y, z) in loop[1:]]
    cr_local = [(xw, u, w) for (u, w) in ent_uw] + [(598.0, 5.0, 4.0), (648.0, 5.0, 4.0), (652.5, 7.0, 6.5), (652.5, 10.0, 7.9),
                                                   (652.5, 31.5, 7.9)]
    cr_world = [TS.world_pt(x, u, w, theta) for (x, u, w) in cr_local]
    pts = bay + loop3 + cr_world[1:]
    wire = tube(pts, WIRE_D, seg=12)
    plug = TS.place(box(648.5, 656.5, 31.0, TS.J1["u"][0], 6.6, 9.2), theta)
    ln = sum(math.dist(a, b) for a, b in zip(pts[:-1], pts[1:]))
    return union([housing, wire, plug]), ln


def touch_parts(out):
    th = TS.TILT_USE
    td2, bodyx, (dx0, dx1) = td2_local()
    src_td2 = (TS.SRC_DRW + ": 유리 189.32 × 120.24 R8, 렌즈 0.7, 몸체 168.55 × 99.71 (유리 끝에서 6.45 · 10.265), 몸체 뒤 6.42, 러그 3.0, "
               "Ø5.0 스탠드오프 끝 14.92; " + TS.SRC_NUM + " screen (DSI x638.66, 입구 -x x629.7, u52.1~68.1; J1 x647~658 u36.5~43); "
               + TS.SRC_SPEC + " F (25° 사용 상태, 받침 안)")
    out.add("TS-E-TD2", "라즈베리파이 Touch Display 2 7인치 (SC1635)", "Raspberry Pi Touch Display 2 7-inch (SC1635)", G_TSE,
            TS.place(td2, th), BLACK_PLASTIC, src_td2,
            note="추정: 러그 9 × 14 × 3.0 (x581.5~590.5 등), 러그 나사 자리 Ø2.6, DSI 커넥터 %.1f~%.1f × u52.1~68.1 × 2.0, J1 두께 2.6; "
                 "몸체 x%.2f~%.2f u%.3f~%.3f; 가로로 놓아 DSI가 -x 쪽, J1이 아래 - 받은 화면으로 확인" % (dx0, dx1, *bodyx))
    out.add("TS-E-TD2-FOLD", "Touch Display 2 7인치 - 접은 상태", "Touch Display 2 7-inch, folded", G_TSF, TS.place(td2, TS.TILT_FOLD),
            BLACK_PLASTIC, src_td2 + "; C12 접은 상태 (유리 y299~419.24, z112)", note="altview")
    rib, rl = ribbon_solid(th)
    LENGTHS["DSI"] = rl["total"]
    out.add("TS-C-DSI", "DSI 리본 300 mm (FIT0997, Pi CAM/DISP 1 → 화면)", "DSI FPC ribbon 300 mm (FIT0997)", G_TSE, rib,
            WHITE_PLASTIC,
            TS.SRC_SPEC + " A3·A8·C7·C11·F + design.json cable (Pi 커넥터 ±x 출구 → 위로 → -x로 x605에서 45° 접기 → 앞으로 올라 뚜껑 밑 → "
            "구멍 x592~614 y292~298 → 경첩 고리 → 받침 아래 트인 홈 → 받침 안 x597~613로 올라감 → u52~68에서 45° 접기 → +x로 DSI 커넥터); D24",
            note="추정: 두께 0.3, 폭 16 (Pi 쪽도 16으로 표시); Pi 쪽 CAM/DISP 1은 x614~617 커넥터(-x 면에서 나옴)로 가정; 뚜껑 밑에서는 "
                 "리브 밑면(z76.5)에 붙어 클립 홈으로 지나감 - 사양 경로의 'z66'은 뚜껑 밑 클립(y320)과 맞지 않아 뚜껑 밑면을 따르게 함; "
                 "구멍 안 y%.1f로 올라감, 받침 안은 w%.2f(클립 자리 w%.2f); 길이 약 %.0f mm (Pi %.0f + 칸 안 %.0f + 고리 %.0f + 받침 안 %.0f + "
                 "커넥터까지 %.0f) / 300" % (296.0, RIB_W_IN, RIB_W_CLIP, rl["total"], rl["pi"], rl["main"] - rl["loop"], rl["loop"],
                                           rl["cradle"], rl["run"]))
    lead, ll = power_lead(th)
    LENGTHS["TD2_POWER"] = ll
    out.add("TS-C-POWER", "화면 전원선 (Pi GPIO 2·6번 → J1, 점퍼 F/F + M/M 20 cm)", "display power lead (Pi GPIO pins 2 / 6 to J1)",
            G_TSE, lead, "#c0392b",
            "design.json cable 전원선 (GPIO 2번 5 V·6번 GND x575~581 y426.8 → z50 → 왼쪽 벽 z50~60 → y301 → x594로 리본 옆 → 뚜껑 구멍 → 고리 → "
            "받침 아래 홈 → 유리 테두리 뒤 칸 u0~10 → x652 → J1); " + TS.SRC_SPEC + " A3·C7; D16",
            note="추정: 두 가닥을 Ø2 한 줄로, 핀 위 암 하우징 7.6 × 2.5 × 8 (2·4·6번 자리를 덮는 한 덩어리), J1 플러그 8 × 5.5 × 2.6이 "
                 "-u 쪽에서 꽂힘; 벽 쪽 길 x567.5 z55, 구멍 안 x593.8 y293.3; 경로 길이 약 %.0f mm" % ll)
    out.add("CU-E-PI5-DISP1", "라즈베리파이 5 CAM/DISP 1 커넥터 (22핀 0.5 mm)", "Raspberry Pi 5 CAM/DISP 1 connector", "CU 칸 전자부",
            box(PI_DISP1[0], PI_DISP1[1], PI_DISP1[2], PI_DISP1[3], 24.1, 24.1 + PI_DISP1[4]), BLACK_PLASTIC,
            "design.json cable (Pi 5 도면에서 커넥터 두 개 x614~617 · x620~623, y374~389, 긴 변이 y 방향)",
            note="추정: 둘 중 x614~617을 CAM/DISP 1로 표시(보드 글씨로 확인), 높이 4.0")


# ------------------------------------------------------------------ entry point

LENGTHS = {}


def build():
    M = _load("electronics_modules.json")
    R = _load("electronics_rearbar.json")
    C = _load("body_centre_unit.json")
    F = _load("keyaction_features_frame.json")
    out = Out()
    plan = cable_plan()
    module_parts(M, out, plan)
    end_parts(M, out)
    comp, feat, iof, pi = rearbar_parts(R, C, out)
    LENGTHS.update(plan["_len"])
    LENGTHS["PED"] = ped_zero_parts(M, out)
    cu_small_parts(R, C, F, out, comp, feat, iof)
    LENGTHS["UPSTREAM"] = hub_upstream(out, pi)
    hub_bank_parts(R, C, out)
    xt30_parts(R, out)
    speaker_parts(R, out)
    headphone_jack(F, R, out)
    pedal_part(R, out)
    touch_parts(out)
    return list(out)


if __name__ == "__main__":
    ps = build()
    for p in ps:
        b = p.solid.bounding_box()
        print("%-18s %-12s %-14s %6d  %s" % (p.id, p.kind, p.group, len(p.solid.decompose()), " ".join("%.1f" % v for v in b)))
    print(len(ps), "parts")
    print("lengths:", {k: round(v, 1) for k, v in LENGTHS.items()})
