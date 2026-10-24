"""3D model of the rev E circuit for the '01 회로도' tab: hardware/pcb/page/circuit3d.json (page.py ships it as fin/circuit/circuit3d.json).

usage:  python3 model3d.py          -> ../page/circuit3d.json + a short report (page.py calls build() itself)

No new geometry is made up here. Every board outline, hole, pad, part and wire is read from what the drawings and the CAD already use:
  * pads and nets: mbroute.pads_and_nets() (MB = SCH-03 + BRD-01), boards3.sb_pads() (SB), sheets.END_BOARDS (EL / ER, as BRD-02),
    netlist/pads_PB.csv (PB, BRD-03), netlist/pads_small.csv (J702 / J501 / PS, BRD-07); pad nets cross-checked with netlist.csv
  * underside wires: netlist/wiring_MB.csv, wiring_SB.csv, wiring_PB.csv, wiring_small.csv, the bare SB buses (boards3.SB_BUS) and the
    EL / ER strands of BRD-02 (straight, as drawn)
  * part bodies and heights: CAD spec hardware/mechanical/cad/spec/electronics_modules.json (MB, Zero, mux, ribbon, USB plug, SB, EL / ER,
    DRV5055 in the sensor-bar pockets) and keyaction_features_frame.json (J701 pocket)
  * centre unit: netlist/cad_centre.json (CAD outlines, boxes, wire centre lines, fixing points) and harness.py (conductor colours)
Where a source only gives an envelope (Zero top parts, modules, jacks) the model shows the envelope. Places that depend on the received
part (PJ-313 legs, the W502 path, the RP2040 chip spot on the Zero) are drawn and marked '추정'.

Coordinates: mm, z up from the desk. Module scene = module-local x (world x = 47 + 164.5 (k - 1) + x); EL / ER = end-part local x
(ER shown beside EL); the rest in world x as the CAD.
JSON objects (short keys, the viewer src/circuit3d.js builds the meshes):
  {k:'b', b:[x0,y0,z0,x1,y1,z1]}                box          {k:'c', a:'x'|'y'|'z', p:[u,v], r, s:[s0,s1]}   cylinder
  {k:'t', p:[[x,y,z]..], r}                     tube         {k:'e', p:[[x,y]..] | [[[x,y]..]..], z:[z0,z1]}  prism (outline + holes)
  {k:'B', p:[[x,y]..], z:[z0,z1], h:[[x,y]..], m:[[x,y,d]..]}  perfboard: outline, lattice holes (texture), drilled holes
  {k:'p', p:[x,y], z:[z0,z1], s:'b'|'t'|'bt'}   pad + solder     {k:'l', p:[x,y,z], t}                         label
  common: c colour, i info key, g layer (board / part / pad / wire / cable / ctx), n net, o opacity, w '주석 맨선' | '피복 가닥' ...
"""
import csv
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ROOT, "..", ".."))
NL = os.path.join(ROOT, "netlist")
OUT = os.path.join(ROOT, "page", "circuit3d.json")
SPEC = os.path.join(REPO, "hardware", "mechanical", "cad", "spec")
sys.path.insert(0, HERE)

import boards2 as B2   # noqa: E402
import boards3 as B3   # noqa: E402
import harness as HN   # noqa: E402
import mbroute as MR   # noqa: E402
import sheets as S     # noqa: E402

REV = "E"
X_O1, MODULE_W = 47.0, 164.5
X_RIGHT = 1198.5                      # ER local x0 (world)
ER_SHOW_DX = 60.0                     # ER drawn beside EL in the end-part scene

# physical colours (CAD palette where the CAD has one: electronics.COLORS)
C = dict(perf="#c8a45a", perf_side="#a8863f", pcb_blue="#2a5caa", pcb_green="#2f7d4f", pcb_dark="#1f3f2c", chip="#1d1d1f",
         kapton="#d08a2a", header="#222326", pin="#d8c27a", solder="#c9ccd2", copper="#c9894b", tin="#c9ccd2", res="#d8c49a",
         res_body100k="#d8c49a", cap1206="#b98b5a", capend="#c9ccd2", mlcc="#3d6fb5", ribbon="#a7adb8", ribbon_red="#c0392b",
         usb="#2b2b2b", shell="#b8bec6", cable="#3a3a3a", jack="#202124", hall="#1d1d1f", lead="#c0c6cc", ctx="#7d858f",
         bar="#6b8fb5", screw="#5a5f66", xt60="#e0b020", fuse="#d9473a", battery="#24427a", pi="#2e7d32", hub="#1f2227",
         dongle="#eceef1", amp="#2a5caa", buck="#2a5caa", heat="#9aa3ad", ffc="#b8862f", ply="#d9b98b", printed="#7d858f",
         wire_wht="#e6e8ec", shrink_red="#c0392b", shrink_blu="#1f5fbf")
BANDS = {"1k": ["#7a4a1e", "#111", "#c0392b"], "100k": ["#7a4a1e", "#111", "#e8c61a"], "100": ["#7a4a1e", "#111", "#7a4a1e"]}


def r2(v):
    return round(float(v), 2)


def col(net):
    return B3.ncol(net)


class Scene:
    def __init__(self, sid, title, sub, frame, short=None):
        self.d = dict(id=sid, t=title, st=short or title, s=sub, f=frame, objs=[], views={}, notes=[])

    def add(self, **o):
        o = {k: v for k, v in o.items() if v is not None}
        self.d["objs"].append(o)
        return o

    def box(self, b, c, i=None, g="part", n=None, o=None, w=None):
        x0, y0, z0, x1, y1, z1 = b
        return self.add(k="b", b=[r2(min(x0, x1)), r2(min(y0, y1)), r2(min(z0, z1)), r2(max(x0, x1)), r2(max(y0, y1)), r2(max(z0, z1))],
                        c=c, i=i, g=g, n=n, o=o, w=w)

    def cyl(self, a, p, r, s, c, i=None, g="part", n=None, o=None):
        return self.add(k="c", a=a, p=[r2(p[0]), r2(p[1])], r=r2(r) if r >= 0.05 else round(r, 3), s=[r2(min(s)), r2(max(s))], c=c, i=i, g=g,
                        n=n, o=o)

    def tube(self, pts, r, c, i=None, g="wire", n=None, w=None, o=None):
        q = [[r2(x), r2(y), r2(z)] for x, y, z in pts]
        q = [p for k, p in enumerate(q) if k == 0 or p != q[k - 1]]
        if len(q) < 2:
            return None
        return self.add(k="t", p=q, r=round(r, 3), c=c, i=i, g=g, n=n, w=w, o=o)

    def prism(self, poly, z, c, i=None, g="part", o=None, n=None):
        return self.add(k="e", p=poly, z=[r2(z[0]), r2(z[1])], c=c, i=i, g=g, o=o, n=n)

    def board(self, poly, z, holes, c, i, mholes=(), side=None):
        return self.add(k="B", p=[[r2(x), r2(y)] for x, y in poly], z=[r2(z[0]), r2(z[1])], h=[[r2(x), r2(y)] for x, y in holes],
                        m=[[r2(x), r2(y), r2(d)] for x, y, d in mholes], c=c, cs=side or C["perf_side"], i=i, g="board")

    def pad(self, x, y, z, n, i, s="b"):
        return self.add(k="p", p=[r2(x), r2(y)], z=[r2(z[0]), r2(z[1])], n=real_net(n), i=i, s=s, g="pad")

    def label(self, p, t, lv=1):
        return self.add(k="l", p=[r2(v) for v in p], t=t, lv=lv)

    def view(self, name, box, az=-35, el=38, default=False):
        self.d["views"][name] = dict(b=[r2(v) for v in box], az=az, el=el)
        if default:
            self.d["v0"] = name

    def note(self, t):
        self.d["notes"].append(t)


# ====================================================================== sources
def read_csv(name):
    with open(os.path.join(NL, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_rows(name):
    with open(os.path.join(NL, name), encoding="utf-8-sig") as f:
        return list(csv.reader(f))


PT_RX = re.compile(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")


def parse_path(s):
    return [(float(a), float(b)) for a, b in PT_RX.findall(s)]


def load_spec():
    with open(os.path.join(SPEC, "electronics_modules.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {i["id"]: i for i in d["module_items"] + d["end_items"]}


def load_jack_spec():
    with open(os.path.join(SPEC, "keyaction_features_frame.json"), encoding="utf-8") as f:
        d = json.load(f)
    return d["cheeks"]["headphone_jack"]


def bx(b):
    return [b["x"][0], b["y"][0], b["z"][0], b["x"][1], b["y"][1], b["z"][1]]


# netlist pins: (board, ref, pin) -> net ; ref -> board(s)
NET_ROWS = read_csv("netlist.csv")
PIN_NET = {}
for _r in NET_ROWS:
    PIN_NET[(_r["보드"], _r["부품"], _r["핀"])] = _r["넷"]


def pin_net(board, ref, pin):
    return PIN_NET.get((board, ref, str(pin)))


def real_net(net):
    """None for pads that carry no net: 'NC', '연결 금지 (…)' (pads_PB.csv), unnamed '~…' nets of the drawn netlist."""
    if not net or net == "NC" or net.startswith(("연결 금지", "~")):
        return None
    return net


# ====================================================================== info (click panel)
INFO = {}


def info(key, title, lines):
    if key and key not in INFO:
        INFO[key] = dict(t=title, d=[x for x in lines if x])


def bom_info():
    rows = read_csv("bom.csv")
    by = {}
    for r in rows:
        by.setdefault(r["부품"], []).append(r)
    for ref, rs in by.items():
        r = rs[0]
        boards = sorted({x["보드"] for x in rs})
        pins = sorted({(p["핀"], p["넷"]) for p in NET_ROWS if p["부품"] == ref and p["보드"] in boards},
                      key=lambda t: (len(t[0]), t[0]))
        pin_txt = ", ".join("%s → %s" % (p, n if not n.startswith("~") else "(이름 없음)") for p, n in pins[:24])
        info(ref, "%s · %s" % (ref, r["값"]), [
            r["부품 설명"],
            "보드 %s · %s장 × %s = %s개" % ("/".join(boards), r["보드 수"], r["보드당"], r["전체 수량"]),
            ("실장: " + r["실장 조건"]) if r["실장 조건"] else "",
            "핀: " + pin_txt if pin_txt else "",
            "KiCad: " + r["KiCad 풋프린트"] if r["KiCad 풋프린트"] else "",
            "구매: %s %s · %s" % (r["구매 목록 코드"], r["구매처"], r["구매 상태 (최종 목록)"]),
            "도면 " + r["도면"],
        ])
    return by


def cable_info():
    rows = read_csv("cables.csv")
    for r in rows:
        info(r["W"], "%s · %s" % (r["W"], r["선"]), ["%s → %s" % (r["한쪽"], r["다른 쪽"]), "자르는 길이: " + r["자르는 길이 (mm)"] + " mm",
                                                       "심: " + r["심"], "구매 목록: " + r["구매 목록 코드"]])


# ====================================================================== shape helpers
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def lattice(xs, ys, inside=None):
    return [(x, y) for x in xs for y in ys if inside is None or inside(x, y)]


def corner_u_outline(x0, x1, y0, y1, ux, uy0, uy1, r):
    """Board rectangle with two U-slots open to the left edge x0 (SB / EL / ER: slot centres (ux, uy0) front, (ux, uy1) rear, radius r;
    both circles reach past the front / rear edge, so each slot is a corner notch with a round inner end)."""
    pts = []
    # front-left notch: from the left edge at y = uy0 + r, around the circle (90 deg -> where it meets the front edge y0)
    a_end = math.asin(max(-1.0, min(1.0, (y0 - uy0) / r)))
    pts.append((x0, uy0 + r))
    pts.append((ux, uy0 + r))
    for k in range(1, 13):
        a = math.pi / 2 - (math.pi / 2 - a_end) * k / 12.0
        pts.append((ux + r * math.cos(a), uy0 + r * math.sin(a)))
    pts.append((x1, y0))
    pts.append((x1, y1))
    a_st = math.asin(max(-1.0, min(1.0, (y1 - uy1) / r)))
    for k in range(0, 13):
        a = a_st - (a_st + math.pi / 2) * k / 12.0
        pts.append((ux + r * math.cos(a), uy1 + r * math.sin(a)))
    pts.append((x0, uy1 - r))
    return pts


def resistor(sc, ref, p1, p2, zt, value, g="part", zb=None, n=None, lift=1.25):
    """axial resistor lying on the top face: body D2.5 x 6.3 centred between the two holes, leads bent down through the board."""
    (x1, y1), (x2, y2) = p1, p2
    zc = zt + lift
    ax = "x" if abs(x2 - x1) >= abs(y2 - y1) else "y"
    L = abs(x2 - x1) if ax == "x" else abs(y2 - y1)
    bl = min(6.3, L - 1.0)
    if ax == "x":
        xm, y = (x1 + x2) / 2.0, y1
        sc.cyl("x", (y, zc), 1.25, (xm - bl / 2, xm + bl / 2), C["res"], i=ref, g=g)
        for k, bc in enumerate(BANDS.get(value, [])):
            u = xm - bl / 2 + 0.9 + 0.75 * k
            sc.cyl("x", (y, zc), 1.29, (u, u + 0.4), bc, i=ref, g=g)
        for xe, xp in ((xm - bl / 2, min(x1, x2)), (xm + bl / 2, max(x1, x2))):
            sc.tube([(xe, y, zc), (xp + (0.6 if xp < xe else -0.6), y, zc), (xp, y, zc - 0.6), (xp, y, (zb if zb is not None else zt - 1.6) - 1.0)],
                    0.25, C["lead"], i=ref, g=g)
    else:
        ym, x = (y1 + y2) / 2.0, x1
        sc.cyl("y", (x, zc), 1.25, (ym - bl / 2, ym + bl / 2), C["res"], i=ref, g=g)
        for k, bc in enumerate(BANDS.get(value, [])):
            u = ym - bl / 2 + 0.9 + 0.75 * k
            sc.cyl("y", (x, zc), 1.29, (u, u + 0.4), bc, i=ref, g=g)
        for ye, yp in ((ym - bl / 2, min(y1, y2)), (ym + bl / 2, max(y1, y2))):
            sc.tube([(x, ye, zc), (x, yp + (0.6 if yp < ye else -0.6), zc), (x, yp, zc - 0.6), (x, yp, (zb if zb is not None else zt - 1.6) - 1.0)],
                    0.25, C["lead"], i=ref, g=g)


def chip1206(sc, ref, p1, p2, zb, under=True, g="part"):
    """1206 across two holes (3.2 x 1.6 x 0.9) on the underside (under=True: hangs below zb) or the top."""
    (x1, y1), (x2, y2) = p1, p2
    xm, ym = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    ax = "x" if abs(x2 - x1) >= abs(y2 - y1) else "y"
    z0, z1 = (zb - 0.9, zb) if under else (zb, zb + 0.9)
    if ax == "x":
        sc.box([xm - 1.0, ym - 0.8, z0, xm + 1.0, ym + 0.8, z1], C["cap1206"], i=ref, g=g)
        sc.box([xm - 1.6, ym - 0.8, z0, xm - 1.0, ym + 0.8, z1], C["capend"], i=ref, g=g)
        sc.box([xm + 1.0, ym - 0.8, z0, xm + 1.6, ym + 0.8, z1], C["capend"], i=ref, g=g)
    else:
        sc.box([xm - 0.8, ym - 1.0, z0, xm + 0.8, ym + 1.0, z1], C["cap1206"], i=ref, g=g)
        sc.box([xm - 0.8, ym - 1.6, z0, xm + 0.8, ym - 1.0, z1], C["capend"], i=ref, g=g)
        sc.box([xm - 0.8, ym + 1.0, z0, xm + 0.8, ym + 1.6, z1], C["capend"], i=ref, g=g)


def spec_1206(sc, ref, b):
    """a 1206 from a CAD spec box (the box is the part + solder envelope): body + two end terminations along the long side."""
    x0, y0, z0, x1, y1, z1 = bx(b)
    if (y1 - y0) >= (x1 - x0):
        sc.box([x0, y0 + 0.5, z0, x1, y1 - 0.5, z1], C["cap1206"], i=ref)
        sc.box([x0, y0, z0, x1, y0 + 0.5, z1], C["capend"], i=ref)
        sc.box([x0, y1 - 0.5, z0, x1, y1, z1], C["capend"], i=ref)
    else:
        sc.box([x0 + 0.5, y0, z0, x1 - 0.5, y1, z1], C["cap1206"], i=ref)
        sc.box([x0, y0, z0, x0 + 0.5, y1, z1], C["capend"], i=ref)
        sc.box([x1 - 0.5, y0, z0, x1, y1, z1], C["capend"], i=ref)


def hall(sc, ref, item, xo, dx=0.0, net_out=None, nets=("+3V3", "GND")):
    """DRV5055 LPG lying marked face up in its sensor-bar pocket, leads +x, bent down at the lead column xo through the bar and the
    board (CAD spec hall_* / el_hall_* boxes: body, lead band, down band)."""
    b0 = bx(item["boxes"][0])
    body = [b0[0] + dx, b0[1], b0[2], b0[3] + dx, b0[4], b0[5]]
    sc.box(body, C["hall"], i=ref)
    zl = (item["boxes"][1]["z"][0] + item["boxes"][1]["z"][1]) / 2.0
    zt = item["boxes"][2]["z"][0]
    bx1 = body[3]
    d = (xo + dx) - bx1
    for yb, yt in ((65.73, 64.46), (67.0, 67.0), (68.27, 69.54)):
        sc.tube([(bx1, yb, zl), (bx1 + 0.45 * d, yb, zl), (xo + dx - 0.05, yt, zl), (xo + dx, yt, zl - 0.5), (xo + dx, yt, zt)], 0.2,
                C["lead"], i=ref, g="part")


def strand(sc, pts, net, i, bare=False, r=None):
    """one underside wire: tinned bare (silver, thin) or an insulated strand (net colour)."""
    if bare:
        return sc.tube(pts, r or 0.26, C["tin"], i=i, g="wire", n=net, w="주석 맨선")
    return sc.tube(pts, r or 0.34, col(net), i=i, g="wire", n=net, w="피복 가닥")


def down_ends(poly, z_under, z_board):
    """a 2D underside route -> 3D: runs at z_under, rises into the board at both ends."""
    pts = [(poly[0][0], poly[0][1], z_board)] + [(x, y, z_under) for x, y in poly] + [(poly[-1][0], poly[-1][1], z_board)]
    return pts


# ====================================================================== octave module (SB + ribbon + MB), module-local x
def scene_module(SP, BOM):
    sc = Scene("module", "옥타브 모듈 (O1 기준): 센서 기판 SB → 리본 → 제어 기판 MB",
               "모듈 로컬 좌표 (세계 x = 47 + 164.5 × (k − 1) + x). 7개 모듈이 같은 기판이고 ID 점퍼·EXT만 다릅니다.", "module",
               "옥타브 모듈 SB·MB")
    # ---------------------------------------------------------------- SB (z7.0~8.6)
    sbb = SP["sb_board"]["boxes"][0]
    zb0, zb1 = sbb["z"]
    y0, y1 = sbb["y"]
    outline = corner_u_outline(sbb["x"][0], sbb["x"][1], y0, y1, 3.0, 61.9, 74.6, 1.7)
    rows = SP["sb_board"]["hole_grid"]["y"]
    cols = [0.63 + 2.54 * i for i in range(1, 70) if sbb["x"][0] + 0.6 < 0.63 + 2.54 * i < sbb["x"][1] - 0.6]
    sc.board(outline, (zb0, zb1), lattice(cols, rows, lambda x, y: math.hypot(x - 3.0, y - 61.9) > 2.2 and math.hypot(x - 3.0, y - 74.6) > 2.2),
             C["perf"], "PCB-SB")
    info("PCB-SB", "센서 기판 SB (6행 양면 도트 띠 161.6 × 15.24 × 1.6)", [
        "모듈마다 1장 (×7). 줄: y61.92 예비 · 64.46 3V3 버스 · 67.00 GND 버스 · 69.54 OUT · 72.08 / 74.62 리본 J201.",
        "센서 바(출력물)가 기판 윗면을 덮어서 기판 부품은 모두 아랫면에 있습니다(1206). 센서는 바의 홈 안에 눕혀 리드를 아래로 꽂습니다.",
        "고정: 왼쪽 U홈 M3×10 ×2 (3.0, 61.9)·(3.0, 74.6), 앞·뒤 받침 리브 위 (W1 P36).", "도면 BRD-02, SCH-02"])
    sc.label(((sbb["x"][0] + sbb["x"][1]) / 2, y0 - 2.5, zb1), "SB 센서 기판", 0)
    # sensors
    keys = list(zip(S.KEYS, S.SENSOR_X))
    hall_ids = ["hall_C", "hall_Cs", "hall_D", "hall_Ds", "hall_E", "hall_F", "hall_Fs", "hall_G", "hall_Gs", "hall_A", "hall_As", "hall_B"]
    pads = B3.sb_pads()
    xo_of = {}
    for (xp, yp), (ref, pin, net) in pads.items():
        if ref.startswith("U2") and pin == "3":
            xo_of[ref] = xp
    for k, ((key, xk), hid) in enumerate(zip(keys, hall_ids)):
        ref = "U%d" % (201 + k)
        hall(sc, ref, SP[hid], xo_of[ref])
        sc.label((xk, 67.0, SP[hid]["boxes"][0]["z"][1] + 1.0), "%s %s" % (ref, key), 2)
    # underside 1206s: C201..C212 under the sensor lead columns, C213 / C214 at the bus ends
    und = SP["sb_underside"]["boxes"]
    for k in range(12):
        spec_1206(sc, "C%d" % (201 + k), und[k])
    spec_1206(sc, "C213", und[12])
    spec_1206(sc, "C214", und[13])
    # pads (solder on the underside; J201 = ribbon strands soldered from below)
    for (xp, yp), (ref, pin, net) in pads.items():
        sc.pad(xp, yp, (zb0, zb1), net, "%s.%s" % (ref, pin), "b")
    # bare buses + 16 strands (wiring_SB.csv)
    zu = zb0 - 0.32
    for net, poly in B3.SB_BUS.items():
        strand(sc, [(x, y, zu + 0.05) for x, y in poly], net, "BUS-SB-" + net, bare=True)
    info("BUS-SB-+3V3", "SB 3V3 버스 (주석 맨선)", ["아랫면 y64.46을 따라 x8.25 → 160.65, 지나는 센서 VCC 패드마다 납땜.", "BRD-02"])
    info("BUS-SB-GND", "SB GND 버스 (주석 맨선)", ["아랫면 y67.00을 따라 x8.25 → 160.65, 지나는 센서 GND 패드마다 납땜.", "BRD-02"])
    sbrows = read_csv("wiring_SB.csv")
    for k, r in enumerate(sbrows):
        poly = parse_path(r["경로 (모듈 좌표 x, y)"])
        lane = [(x, y + ((k - 5.5) * 0.12 if abs(y - 70.81) < 0.01 else 0.0)) for x, y in poly]
        wid = "SBW-%d" % (k + 1)
        strand(sc, down_ends(lane, zu - 0.05 - 0.04 * (k % 3), zb0), r["넷"], wid)
        info(wid, "SB 아랫면 선 %s → J201.%s" % (r["선 (센서 OUT / 버스)"], r["J201 핀"]),
             ["넷 %s · 피복 단선 %s mm" % (r["넷"], r["길이 (mm)"]), "경로: " + r["경로 (모듈 좌표 x, y)"], "wiring_SB.csv · BRD-02"])
    # support ribs + sensor bar (context)
    for (a0, a1, b0, b1) in B3.SB_RIBS:
        sc.box([a0, b0, 5.0, a1, b1, zb0], C["ctx"], i="CTX-RIB", g="ctx", o=0.35)
    info("CTX-RIB", "SB 받침 리브 (프레임, W1 P36)", ["윗면 z7.0 = 기판 밑면. 뒤 리브는 x59~82(리본 틈)만 열려 있어 아랫면 선은 그 안에서만 뒤 띠를 지납니다."])
    sc.box([0.5, 59.0, zb1, 162.9, 77.5, 13.6], C["bar"], i="CTX-BAR", g="ctx", o=0.12)
    info("CTX-BAR", "센서 바 (출력물, 윤곽만)", ["기판 윗면을 덮는 출력물. 센서는 바의 홈(백건 z12.19 · 흑건 z9.66)에 눕혀 넣고 리드를 바 구멍 Ø0.9와 기판에 꽂습니다.",
                                           "여기서는 바깥 윤곽 상자만 흐리게 보입니다 (홈·턱 모양은 04 3D 모델)."])
    # ---------------------------------------------------------------- ribbon W101 (flat on the floor) + strands into J201 / J301
    rb = SP["ribbon"]["boxes"]
    xr0, xr1 = rb[1]["x"]
    for b in rb[1:3]:
        x0, y0_, z0, x1, y1_, z1 = bx(b)
        sc.box([x0, y0_, z0, x1, y1_, z1], C["ribbon"], i="W101~W107", g="cable")
        sc.box([x0, y0_, z1, x0 + 0.9, y1_, z1 + 0.02], C["ribbon_red"], i="W101~W107", g="cable")
    zf = rb[1]["z"][1] - 0.45
    for n in range(1, 17):
        cx = xr0 + 0.635 + 1.27 * (n - 1)
        net = S.RIBBON[n - 1]
        # SB end: J201 pad (from below) -> folds down through the rib gap to the flat ribbon at y77.5
        px, py = 61.59 + 2.54 * ((n - 1) // 2), (72.08 if n % 2 else 74.62)
        sc.tube([(px, py, zb0), (px, py, zb0 - 0.7), (cx, 76.0, zf + 0.6), (cx, 77.5, zf)], 0.22, C["ribbon"] if n > 1 else C["ribbon_red"],
                i="W101~W107", g="cable", n=net)
        # MB end: last ~6 mm split, shifted -0.31, soldered into J301 from below
        qx, qy = S.RIB_X0 + 2.54 * ((n - 1) // 2), S.RIB_Y[(n - 1) % 2]
        sc.tube([(cx, 144.5, zf), (cx - 0.31, 145.6, zf + 0.3), (qx, qy - 1.2, 7.6), (qx, qy, 9.0)], 0.22,
                C["ribbon"] if n > 1 else C["ribbon_red"], i="W101~W107", g="cable", n=net)
    sc.label((70.48, 110.0, 6.5), "리본 W101 (16심)", 0)
    # ---------------------------------------------------------------- MB (z9.0~10.6)
    mb_scene_parts(sc, SP, X0=0.0, detail=True)
    sc.view("모듈 전체", [0, 58, 4, 165, 236, 22], az=-28, el=42, default=True)
    sc.view("SB 확대", [0, 58, 4, 165, 80, 15], az=-20, el=48)
    sc.view("SB 아랫면", [0, 58, 4, 165, 80, 15], az=-20, el=-52)
    sc.view("MB 확대", [46, 144, 4, 118, 200, 20], az=-30, el=45)
    sc.view("MB 아랫면", [46, 144, 4, 118, 200, 20], az=-30, el=-55)
    sc.view("MB 위", [46, 144, 4, 118, 200, 20], az=0, el=89)
    sc.note("ID 점퍼는 O1 = JP301 닫음, R301~R303 100 kΩ와 J302 EXT는 O1·O7에만 (O7은 R301만). 다른 모듈은 같은 자리를 비웁니다.")
    sc.note("센서 바·받침 리브·매단 보스는 위치만 흐리게(주변 출력물). 센서가 기판보다 떠 있는 것은 바의 홈 안에 눕혀 있기 때문입니다.")
    return sc


def mb_scene_parts(sc, SP, X0=0.0, detail=True):
    """the control board MB of one module (O1 parts list): board, Zero, mux, headers, J301 / J302 pads, R30x, JP, TP, C301, screws, USB
    plug + EXT lead, underside wiring."""
    def X(x):
        return x + X0
    mbb = SP["mb_board"]["boxes"]
    z0, z1 = mbb[0]["z"]
    sl = S.MB["slot"]
    outline = [(S.MB["x0"], S.MB["y0"]), (sl[0], S.MB["y0"]), (sl[0], sl[3]), (sl[1], sl[3]), (sl[1], S.MB["y0"]), (S.MB["x1"], S.MB["y0"]),
               (S.MB["x1"], S.MB["y1"]), (S.MB["x0"], S.MB["y1"])]
    holes = lattice([S.lat(-11 + i) for i in range(27)], [148.19 + 2.54 * j for j in range(19)],
                    lambda x, y: not (S.MB["keep"][0] - 0.6 < x < S.MB["keep"][1] + 0.6 and y < S.MB["keep"][3] + 0.6)
                    and min(math.hypot(x - a, y - b) for a, b, _ in S.MB["standoffs"]) > 2.4)
    mh = [(a, b, 3.2 if "M3" in t else 3.0) for a, b, t in S.MB["standoffs"]]
    sc.board([(X(x), y) for x, y in outline], (z0, z1), [(X(x), y) for x, y in holes], C["perf"], "PCB-MB", mholes=[(X(a), b, d) for a, b, d in mh])
    info("PCB-MB", "제어 기판 MB (Coms BE163에서 자른 70 × 50 × 1.6)", [
        "모듈마다 1장 (×7). 모든 구멍이 RP2040-Zero 핀 격자 x = 76.52 + 2.54 i, y = 173.59 + 2.54 j 위.",
        "앞 홈 x81.92~84.72 × y≤172 (F|F# 핀 발·킬이 지나감), 금지 구역 x81.22~85.42 × y≤173.2.",
        "고정: 매단 Ø6 보스 4개 — M3×6 ISO 7380 2개를 밑에서 (50, 149)·(114.5, 192.5), 위치 핀 2개 (114.5, 149)·(50, 192.5).",
        "도면 BRD-01 (윗면), BRD-08 (아랫면 배선), SCH-03"])
    sc.label((X(82.0), 143.0, z1), "MB 제어 기판", 0)
    pads, _nets = MR.pads_and_nets()
    # ---- Zero A301 on header pins (PCB z11.9~12.9)
    zb = SP["zero"]["boxes"]
    sc.box(shift(bx(zb[0]), X0), C["pcb_blue"], i="A301")
    sc.box(shift(bx(zb[1]), X0), C["kapton"], i="A301", o=0.85)
    sc.box(shift(bx(zb[2]), X0), C["pcb_blue"], i="A301", o=0.18)
    sc.box(shift(bx(zb[3]), X0), C["shell"], i="A301")
    cx, cy = (zb[2]["x"][0] + zb[2]["x"][1]) / 2.0, (zb[2]["y"][0] + zb[2]["y"][1]) / 2.0 - 1.5
    sc.box([X(cx - 3.5), cy - 3.5, 12.9, X(cx + 3.5), cy + 3.5, 13.8], C["chip"], i="A301-CHIP")
    info("A301-CHIP", "RP2040 칩 (자리 어림)", ["제로 윗면 부품(RP2040·플래시·BOOT/RESET·LED)은 높이 한계 z16.3 상자(흐린 파랑) 안에 있습니다. 칩 자리는 어림입니다."])
    sc.label((X(84.0), 184.0, 16.8), "A301 RP2040-Zero", 1)
    # ---- mux A302 (header spacers, module PCB, chip)
    mx = SP["mux"]["boxes"]
    sc.box(shift(bx(mx[0]), X0), C["header"], i="A302")
    sc.box(shift(bx(mx[1]), X0), C["header"], i="A302")
    sc.box(shift(bx(mx[2]), X0), C["pcb_green"], i="A302")
    sc.box(shift(bx(mx[3]), X0), C["chip"], i="A302")
    sc.label((X(63.8), 172.0, 17.2), "A302 4067 먹스", 1)
    # ---- pins of the two modules, pads, other parts
    for (k, m), (ref, num, net) in sorted(pads.items()):
        x, y = MR.X(k), MR.Y(m)
        nn = None if net == "NC" else net
        pid = "%s.%s" % (ref, num)
        if ref == "A301":
            if int(num) <= 18:
                sc.box([X(x) - 0.32, y - 0.32, 7.0, X(x) + 0.32, y + 0.32, 16.3], C["pin"], i=pid, n=nn)
            else:
                pid = pid                                                 # bottom row 19~23: no header, empty hole
            sc.pad(X(x), y, (z0, z1), nn, pid, "b" if int(num) <= 18 else "")
        elif ref == "A302":
            sc.box([X(x) - 0.32, y - 0.32, 7.6, X(x) + 0.32, y + 0.32, 19.1], C["pin"], i=pid, n=nn)
            sc.pad(X(x), y, (z0, z1), nn, pid, "b")
        elif ref in ("J301", "J302"):
            sc.pad(X(x), y, (z0, z1), nn, pid, "b")
        elif ref.startswith("R30"):
            sc.pad(X(x), y, (z0, z1), nn, pid, "b" if ref in ("R301", "R302", "R303") else "")
        elif ref.startswith("JP"):
            sc.pad(X(x), y, (z0, z1), nn, pid, "b")
        elif ref.startswith("TP"):
            sc.pad(X(x), y, (z0, z1), nn, pid, "bt")
            sc.add(k="c", a="x", p=[r2(y), r2(z1 + 1.6)], r=1.1, s=[r2(X(x) - 0.25), r2(X(x) + 0.25)], c=C["tin"], i=pid, g="part", n=nn, ring=1)
        else:
            sc.pad(X(x), y, (z0, z1), nn, pid, "b")
    # R301~R303 (O1), R304 place left empty
    for ref, (x, y) in S.R_EXT.items():
        if ref in ("R301", "R302", "R303"):
            resistor(sc, ref, (X(x), y), (X(x + 7.62), y), z1, "100k", zb=z0)
    # ID jumpers: O1 = JP301 closed (solder bridge on the underside)
    for ref, (x, y) in S.JP_POS.items():
        closed = ref == "JP301"
        if closed:
            sc.box([X(x) - 0.4, y - 0.55, z0 - 0.55, X(x + 2.54) + 0.4, y + 0.55, z0], C["solder"], i=ref)
    # C301 1206 across the mux GND / VCC header tails (underside)
    g_, v_ = S.mux_hole("GND"), S.mux_hole("VCC")
    chip1206(sc, "C301", (X(g_[0]), g_[1]), (X(v_[0]), v_[1]), z0 - 0.25)
    # screws from below + locating pins (frame) + hung bosses (context)
    for (a, b, t) in S.MB["standoffs"]:
        if "M3" in t:
            sc.cyl("z", (X(a), b), 2.85, (7.35, z0), C["screw"], i="L35")
            sc.cyl("z", (X(a), b), 1.4, (z0, 15.0), C["screw"], i="L35", g="ctx", o=0.5)
        else:
            sc.cyl("z", (X(a), b), 1.4, (7.8, 17.0), C["ctx"], i="CTX-PIN", g="ctx", o=0.5)
    info("L35", "M3×6 ISO 7380 (유두 렌치볼트) — MB 고정", ["밑에서 매단 보스(Ø2.5 막힌 구멍, z15.4까지 탭)에. 머리 Ø5.7 × 1.65 (z7.35~9.0).", "구매 목록 L35"])
    info("CTX-PIN", "위치 핀 Ø2.8 (프레임)", ["매단 보스에서 내려와 기판 Ø3.0 구멍에 들어감 (끝 z7.8)."])
    for (a0, a1, b0, b1) in S.MB["boss_rects"]:
        sc.box([X(a0), b0, 10.6, X(a1), b1, 17.0], C["ctx"], i="CTX-BOSS", g="ctx", o=0.18)
    info("CTX-BOSS", "매단 보스 받침 (프레임, W1 r4.5)", ["기판 위 Ø6 보스 4개의 받침 6 × 7.5. 둘레 1.3은 부품 없음 (모서리 x≤54.3 · x≥110.2)."])
    # USB plug + cable stub
    sc.box(shift(bx(SP["usb_plug_shell"]["boxes"][0]), X0), C["shell"], i="W201")
    sc.box(shift(bx(SP["usb_plug"]["boxes"][0]), X0), C["usb"], i="W201", g="cable")
    sc.cyl("y", (X(84.0), 14.5), 1.75, (221.8, 234.0), C["cable"], i="W201", g="cable")
    sc.label((X(84.0), 226.0, 19.5), "W201 USB → 허브", 1)
    # EXT lead (O1 / O7): six strands down from J302, -x under the board, then +y under the USB plug to the rear wall
    for n in range(1, 7):
        x = S.EXT_X0 + 2.54 * (n - 1)
        net = pin_net("MB", "J302", n) or ""
        xe = 86.0 + 0.55 * (n - 1)
        sc.tube([(X(x), S.EXT_Y, z0), (X(x), S.EXT_Y, 6.4), (X(x) - 0.4, S.EXT_Y + 0.6, 6.0), (X(xe), S.EXT_Y + 0.6, 6.0), (X(xe), 212.0, 6.0)],
                0.27, "#7e889a", i="W403", g="cable", n=net)
    # underside wiring (BRD-08 / wiring_MB.csv): insulated single-core, joins only at pads
    zu = z0 - 0.42
    for k, r in enumerate(read_csv("wiring_MB.csv")):
        poly = parse_path(r["경로 (꺾인 점, 모듈 좌표)"])
        wid = "MBW-%s" % r["번호"]
        strand(sc, down_ends([(X(x), y) for x, y in poly], zu - 0.07 * (k % 3), z0), r["넷"], wid, r=0.3)
        info(wid, "MB 아랫면 선 %s: %s → %s" % (r["번호"], r["시작"], r["끝"]),
             ["넷 %s · 피복 단선 %s mm · 꺾임 %s" % (r["넷"], r["길이 (mm)"], r["꺾임 수"]), "경로: " + r["경로 (꺾인 점, 모듈 좌표)"],
              "wiring_MB.csv · BRD-08"])


def shift(b, dx):
    return [b[0] + dx, b[1], b[2], b[3] + dx, b[4], b[5]]


# ====================================================================== end parts EL / ER
def scene_end(SP):
    sc = Scene("end", "끝 부속 센서 기판 EL (A0 · A#0 · B0) · ER (C8)",
               "끝 부속 로컬 좌표. ER은 보기 위해 EL 오른쪽에 옮겨 둠 (실제로는 악기 오른쪽 끝, 세계 x = 1198.5 + x).", "end", "끝 부속 EL·ER")
    for tag, dx in (("EL", 0.0), ("ER", ER_SHOW_DX)):
        Bd = S.END_BOARDS[tag]
        board = "EL" if tag == "EL" else "ER"
        it = SP["el_board" if tag == "EL" else "er_board"]["boxes"][0]
        zb0, zb1 = it["z"]
        y0, y1 = it["y"]
        outline = corner_u_outline(it["x"][0], it["x"][1], y0, y1, 3.0, 61.9, 74.6, 1.7)
        cols = [0.63 + 2.54 * i for i in range(1, 20) if 1.0 + 0.6 < 0.63 + 2.54 * i < Bd["x1"] - 0.6]
        rows = [61.92, 64.46, 67.00, 69.54, 72.08, 74.62]
        sc.board([(x + dx, y) for x, y in outline], (zb0, zb1),
                 [(x + dx, y) for x, y in lattice(cols, rows, lambda x, y: math.hypot(x - 3.0, y - 61.9) > 2.2 and math.hypot(x - 3.0, y - 74.6) > 2.2)],
                 C["perf"], "PCB-" + tag)
        info("PCB-" + tag, "%s 센서 기판 (6행 띠 %s × 15.24)" % (tag, "45.5" if tag == "EL" else "22.0"), [
            "끝 부속 센서 바 안 (EL x1.0~46.5, ER 로컬 x1.0~23.0). 줄은 SB와 같음.",
            "센서 바가 윗면을 덮어 100 nF · 1 kΩ · 10 µF 모두 1206 아랫면 (△13).", "리드 %s → 뒤 통로 XH (SCH-04 주 6)" % ("W401 5심" if tag == "EL" else "W411 3심"),
            "도면 BRD-02 (끝 부속 칸), SCH-04"])
        sc.label((it["x"][0] + dx + 4, y0 - 2.5, zb1), "%s 기판" % tag, 0)
        sc.box([Bd["bar"][0] + dx, 59.0, zb1, Bd["bar"][1] + dx, 77.5, 13.6], C["bar"], i="CTX-BAR-END", g="ctx", o=0.12)
        jx = Bd["jx"]
        hall_items = ["el_hall_A0", "el_hall_As0", "el_hall_B0"] if tag == "EL" else ["er_hall_C8"]
        last = max(S.end_col(k[2]) for k in Bd["keys"])
        for (u, key, xk, cref, rref), hid in zip(Bd["keys"], hall_items):
            colx = S.end_col(xk)
            hall(sc, u, SP[hid], colx, dx=dx)
            sc.label((xk + dx, 67.0, SP[hid]["boxes"][0]["z"][1] + 1.0), "%s %s" % (u, key), 2)
            for y, pin in ((64.46, "1"), (67.00, "2"), (69.54, "3")):
                sc.pad(colx + dx, y, (zb0, zb1), pin_net(board, u, pin), "%s.%s" % (u, pin), "b")
            sc.pad(colx + dx, 72.08, (zb0, zb1), pin_net(board, rref, "1"), "%s.1" % rref, "b")
            chip1206(sc, cref, (colx + dx, 64.46), (colx + dx, 67.00), zb0)
            chip1206(sc, rref, (colx + dx, 69.54), (colx + dx, 72.08), zb0)
        chip1206(sc, Bd["bulk"], (8.25 + dx, 64.46), (8.25 + dx, 67.00), zb0)
        for y, pin in ((64.46, "1"), (67.00, "2")):
            sc.pad(8.25 + dx, y, (zb0, zb1), pin_net(board, Bd["bulk"], pin), "%s.%s" % (Bd["bulk"], pin), "b")
        zu = zb0 - 0.32
        rail = "+3V3_EL" if tag == "EL" else "+3V3_ER"
        strand(sc, [(8.25 + dx, 64.46, zu), (last + dx, 64.46, zu)], rail, "BUS-%s-3V3" % tag, bare=True)
        strand(sc, [(8.25 + dx, 67.00, zu), (last + dx, 67.00, zu)], "GND", "BUS-%s-GND" % tag, bare=True)
        info("BUS-%s-3V3" % tag, "%s 3V3 버스 (주석 맨선)" % tag, ["아랫면 y64.46, x8.25 → %.2f" % last])
        info("BUS-%s-GND" % tag, "%s GND 버스 (주석 맨선)" % tag, ["아랫면 y67.00, x8.25 → %.2f" % last])
        for n, x in enumerate(jx, 1):
            sc.pad(x + dx, 74.62, (zb0, zb1), pin_net(board, Bd["jref"], n), "%s.%d" % (Bd["jref"], n), "b")
        wires = [((jx[0], 67.00), (jx[0], 74.62), "GND"), ((jx[-1], 64.46), (jx[-1], 74.62), rail)]
        for k, (u, key, xk, cref, rref) in enumerate(Bd["keys"]):
            wires.append(((S.end_col(xk), 72.08), (jx[1 + k], 74.62), pin_net(board, rref, "1")))
        for k, (a, b_, net) in enumerate(wires):
            wid = "%sW-%d" % (tag, k + 1)
            strand(sc, down_ends([(a[0] + dx, a[1]), (b_[0] + dx, b_[1])], zu - 0.1, zb0), net, wid)
            info(wid, "%s 아랫면 선: (%.2f, %.2f) → %s 패드" % (tag, a[0], a[1], Bd["jref"]), ["넷 %s · 피복 단선 (BRD-02 끝 부속 칸, 점 대 점)" % net])
        # lead strands: down from the J pads inside the rear-rib gap, gathered, flat on the floor toward the rear wall
        gx0 = 14.825 if tag == "EL" else 8.885
        wid = "W401" if tag == "EL" else "W411"
        for n, x in enumerate(jx, 1):
            g = gx0 + 0.635 + 1.27 * (n - 1)
            net = pin_net(board, Bd["jref"], n)
            sc.tube([(x + dx, 74.62, zb0), (x + dx, 74.62, zb0 - 1.0), (x + dx, 75.6, 6.0), (g + dx, 77.39, 5.45), (g + dx, 96.0, 5.45)], 0.24,
                    C["ribbon"] if n > 1 else C["ribbon_red"], i=wid, g="cable", n=net)
        sc.label((gx0 + dx + 3.0, 92.0, 6.5), "%s → 뒤 통로 XH" % wid, 1)
        for (a0, a1, b0, b1) in ([(6.0, Bd["gap"][0], 73.2, 75.5), (Bd["gap"][1], Bd["x1"], 73.2, 75.5), (6.0, Bd["x1"] - 0.5, 61.0, 62.8)]):
            if a1 > a0:
                sc.box([a0 + dx, b0, 5.0, a1 + dx, b1, zb0], C["ctx"], i="CTX-RIB", g="ctx", o=0.35)
    info("CTX-BAR-END", "끝 부속 센서 바 (출력물, 윤곽만)", ["EL 바 x0.5~46.5 (A#0 낮은 구간 x19.93~33.93), ER 바 로컬 x0.5~23.0. 센서는 바의 홈에 눕혀 있습니다."])
    info("CTX-RIB", "받침 리브 (프레임)", ["윗면 z7.0 = 기판 밑면. 뒤 리브 틈(EL x15~38, ER x6~16)으로 리드가 내려갑니다."])
    sc.view("EL · ER", [0, 58, 4, 85, 98, 15], az=-25, el=45, default=True)
    sc.view("아랫면", [0, 58, 4, 85, 80, 15], az=-25, el=-55)
    sc.view("EL 확대", [0, 58, 4, 48, 80, 15], az=-25, el=45)
    sc.view("ER 확대", [ER_SHOW_DX, 58, 4, ER_SHOW_DX + 24, 80, 15], az=-25, el=45)
    sc.note("10 µF C404 · C412 자리(x8.25)는 C412가 CAD 사양에서 '어림'입니다. 리드는 y96에서 자름 (실제로는 레일 밑 차선 → 뒷벽 홈 → 뒤 통로 XH).")
    return sc


# ====================================================================== pedal: PB + J501 scrap + PS
def scene_pedal():
    sc = Scene("pedal", "페달: PED 보드 PB + J501 잭 조각 + 페달 안 센서 PS",
               "가운데 유닛 세계 좌표 (PB x426.5~476.5 · y244~314). PS는 페달 안에 있어 보기 위해 PB 옆에 둠.", "world", "페달 PB·J501·PS")
    z0, z1 = B2.PB_Z
    bx0, bx1, by0, by1 = B2.PB_BOX
    holes = lattice([B2.pb_x(j) for j in range(20)], [B2.pb_y(i) for i in range(28)],
                    lambda x, y: min(math.hypot(x - a, y - b) for a, b, _, _ in B2.PB_HOLES) > 2.2)
    sc.board(rect(bx0, by0, bx1, by1), (z0, z1), holes, C["perf"], "PCB-PB", mholes=[(a, b, d) for a, b, d, _ in B2.PB_HOLES])
    info("PCB-PB", "PED 페달 보드 PB (BE163에서 자른 70 × 50)", [
        "가운데 유닛 바닥 5 mm 기둥 위 (z21.5~23.1). 격자 x = 475.23 − 2.54 j, y = 245.27 + 2.54 i (지그 P-PED).",
        "A501 RP2040-Zero (180° 돌림, USB-C −y) · R501 1 kΩ · R502 100 kΩ · R503 100 Ω × 5 = 20 Ω · C501 100 nF · JP504 닫음.",
        "도면 BRD-03, SCH-05"])
    sc.label((bx0 + 4, by0 - 3.0, z1), "PB 페달 보드", 0)
    pads = read_csv("pads_PB.csv")
    pp = {}
    for r in pads:
        pp.setdefault(r["부품"], {})[r["핀"]] = (float(r["x"]), float(r["y"]), r["넷"])
    # A501 Zero: CAD box snapped to the lattice (BRD-03 △22), 180 deg (USB-C toward -y), pin headers 1.3 gap
    zx0 = 449.0 + B2.ZERO_SNAP[0]
    zy_r = 244.0 + B2.ZERO_SNAP[1]                     # receptacle face
    zp0 = z1 + 1.3
    sc.box([zx0, zy_r + 1.3, zp0, zx0 + 18.0, zy_r + 1.3 + 23.5, zp0 + 1.0], C["pcb_blue"], i="A501")
    sc.box([zx0 + 0.5, zy_r + 7.3, zp0 + 1.0, zx0 + 17.5, zy_r + 24.3, zp0 + 4.4], C["pcb_blue"], i="A501", o=0.18)
    sc.box([zx0 + 2.06, zy_r + 1.3 + 5.5, z1, zx0 + 15.96, zy_r + 1.3 + 23.0, zp0], C["kapton"], i="A501", o=0.85)
    sc.box([zx0 + 4.67, zy_r, zp0 + 1.0, zx0 + 13.61, zy_r + 7.3, zp0 + 4.2], C["shell"], i="A501")
    sc.box([zx0 + 5.5, zy_r + 12.0, zp0 + 1.0, zx0 + 12.5, zy_r + 19.0, zp0 + 1.9], C["chip"], i="A301-CHIP")
    sc.label((zx0 + 9, zy_r + 14, zp0 + 5.0), "A501 RP2040-Zero", 1)
    for pin, (x, y, net) in pp["A501"].items():
        sc.box([x - 0.32, y - 0.32, z0 - 2.0, x + 0.32, y + 0.32, zp0 + 3.4], C["pin"], i="A501.%s" % pin, n=real_net(net))
    # W208 USB-C plug stub toward -y
    sc.box([zx0 + 4.92, zy_r - 25.0, zp0 + 0.8, zx0 + 13.36, zy_r - 0.05, zp0 + 4.4], C["usb"], i="W208", g="cable")
    sc.label((zx0 + 9, zy_r - 14, zp0 + 6.0), "W208 USB → 허브 포트 2", 1)
    for ref, d in pp.items():
        for pin, (x, y, net) in d.items():
            s = "bt" if ref.startswith("TP") else "b"
            sc.pad(x, y, (z0, z1), net, "%s.%s" % (ref, pin), s)
    # parts
    resistor(sc, "R501", pp["R501"]["1"][:2], pp["R501"]["2"][:2], z1, "1k", zb=z0)
    resistor(sc, "R502", pp["R502"]["1"][:2], pp["R502"]["2"][:2], z1, "100k", zb=z0)
    for s_ in "abcde":
        resistor(sc, "R503", pp["R503" + s_]["1"][:2], pp["R503" + s_]["2"][:2], z1, "100", zb=z0)
    chip1206(sc, "C501", pp["C501"]["1"][:2], pp["C501"]["2"][:2], z0 - 0.25)
    a, b = pp["JP504"]["1"][:2], pp["JP504"]["2"][:2]
    sc.box([a[0] - 0.55, min(a[1], b[1]) - 0.4, z0 - 0.55, a[0] + 0.55, max(a[1], b[1]) + 0.4, z0], C["solder"], i="JP504")
    for tp in ("TP501", "TP502"):
        x, y, net = pp[tp]["1"]
        sc.add(k="c", a="x", p=[r2(y), r2(z1 + 1.6)], r=1.1, s=[r2(x - 0.25), r2(x + 0.25)], c=C["tin"], i=tp, g="part", n=net, ring=1)
    # underside wires (wiring_PB.csv)
    zu = z0 - 0.4
    for k, r in enumerate(read_csv("wiring_PB.csv")):
        poly = parse_path(r["경로 (모델 좌표 x, y)"])
        bare = "맨선" in r["선"]
        wid = "PBW-%s-%s" % (r["넷"], r["선 번호"])
        strand(sc, down_ends(poly, zu - (0.0 if bare else 0.12), z0), r["넷"], wid, bare=bare)
        info(wid, "PB 아랫면 %s %s (%s)" % (r["넷"], r["선 번호"], r["선"]),
             ["%s · %s mm" % (r["선"], r["직각 길이 (mm)"]), "경로: " + r["경로 (모델 좌표 x, y)"],
              "주석 맨선은 지나는 패드마다 납땜, 리본 가닥은 두 끝만." , "wiring_PB.csv · BRD-03"])
    # posts + screws (context)
    for hx, hy, d, t in B2.PB_HOLES:
        if "나사" in t:
            sc.cyl("z", (hx, hy), 3.0, (16.5, z0), C["printed"], i="CTX-POST", g="ctx", o=0.45)
            sc.cyl("z", (hx, hy), 2.75, (z1, z1 + 1.65), C["screw"], i="CTX-POST", g="ctx")
        else:
            sc.cyl("z", (hx, hy), 3.0, (16.5, z0), C["printed"], i="CTX-POST", g="ctx", o=0.45)
            sc.cyl("z", (hx, hy), 1.4, (z0, z1 + 2.0), C["printed"], i="CTX-POST", g="ctx", o=0.6)
    info("CTX-POST", "기둥 (가운데 유닛 아랫판 출력물)", ["PB · J702 기판은 5 mm 기둥 위. M3 나사 2개 + 위치 핀 2개."])
    # ---- J501 scrap (z36.4~38.0) + jack + W502 strands (estimated path) + W501 stub
    jb = B3.J5_BOX
    jz0, jz1 = HN.PTS.get("j501_board", [450.0, 475.0, 316.5, 340.5, 36.4, 38.0])[4:6]
    sc.board(rect(jb[0], jb[2], jb[1], jb[3]), (jz0, jz1), lattice([B3.j5x(i) for i in range(9)], [B3.j5y(j) for j in range(9)]), C["perf"], "PCB-J501")
    info("PCB-J501", "J501 페달 잭 조각 (25 × 24, 9 × 9 구멍)", ["뒤판 출력물 위 (z36.4~38.0). 잭 다리 → 앞 패드 1 T · 2 TN · 3 R · 4 S (피복 가닥, 받은 잭 다리에서 가장 짧게).",
                                                         "도면 BRD-07, SCH-05"])
    jk = B3.J5_JACK
    sc.box([jk[0], jk[2], jz1, jk[1], jk[3] - 2.5, jz1 + 5.0], C["jack"], i="J501")
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, jz1 + 2.5), 2.5, (jk[3] - 2.5, jk[3]), C["jack"], i="J501")
    sc.box([B3.J5_FIELD[0], B3.J5_FIELD[2], jz1, B3.J5_FIELD[1], B3.J5_FIELD[3], jz1 + 0.05], "#f0a830", i="J5-FIELD", g="ctx", o=0.35)
    info("J5-FIELD", "잭 다리 자리 (추정)", ["PJ-313 다리 간격은 2.54가 아니어서 이 칸 안에서 가장 가까운 구멍으로 구부려 꽂습니다. 다리 글자는 통전 검사로 찾음."])
    sc.label(((jk[0] + jk[1]) / 2, jk[3] + 2.0, jz1 + 7.0), "J501 페달 잭", 1)
    smalls = read_csv("pads_small.csv")
    j5p = [(float(r["x"]), float(r["y"]), r["넷"], r["핀"]) for r in smalls if r["기판"].startswith("J501")]
    for x, y, net, pin in j5p:
        sc.pad(x, y, (jz0, jz1), net, "W502.%s" % pin, "b")
    pbj = sorted(pp["J502"].items())
    for (pin, (x, y, net)), (xa, ya, _n, _p) in zip(pbj, sorted(j5p, key=lambda t: t[3])):
        sc.tube([(x, y, z0), (x, y, z0 - 1.2), (x, by1 + 2.0, z0 - 1.2), (x, by1 + 2.0, jz0 - 1.0), (xa, ya - 1.0, jz0 - 1.0), (xa, ya, jz0)], 0.24,
                C["ribbon"] if pin != "1" else C["ribbon_red"], i="W502", g="cable", n=net)
    sc.label((452.0, 315.0, 30.0), "W502 (경로 추정)", 1)
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, jz1 + 2.5), 1.9, (jk[3] + 8.0, jk[3] + 26.0), C["cable"], i="W501", g="cable")
    sc.label(((jk[0] + jk[1]) / 2, jk[3] + 22.0, jz1 + 6.0), "W501 → 페달 (3 m)", 1)
    # ---- PS pedal sensor scrap (local frame), shown beside the PB
    ox, oy, oz = 392.0, 300.0, 21.5
    ps = [(float(r["x"]), float(r["y"]), r["넷"], r["부품"], r["핀"]) for r in smalls if r["기판"].startswith("PS")]
    pz0, pz1 = oz, oz + 1.6
    sc.board(rect(ox - 1.27, oy - 1.27, ox + 6 * 2.54 + 1.27, oy + 4 * 2.54 + 1.27), (pz0, pz1),
             lattice([ox + 2.54 * c for c in range(7)], [oy + 2.54 * r for r in range(5)]), C["perf"], "PCB-PS")
    info("PCB-PS", "PS 페달 안 센서 조각 (7 × 5 구멍)", ["페달 안 자석 아래 (실제 위치는 페달 몸통 안 — 여기서는 PB 옆에 둠). U551은 표시면을 위로 눕혀 리드를 +x로.",
                                                      "로컬 좌표 (왼쪽 아래 구멍 = 0, 0). 도면 BRD-07, SCH-05"])
    sc.label((ox + 7.0, oy - 4.0, pz1), "PS (페달 안, 보기 위해 옆에)", 0)
    for x, y, net, ref, pin in ps:
        sc.pad(ox + x, oy + y, (pz0, pz1), None if net.startswith("U551 OUT") else net, "%s.%s" % (ref, pin), "b")
    sc.box([ox + 5.08 - 1.75 - 3.15, oy + 5.08 - 2.0, pz1, ox + 5.08 - 1.75, oy + 5.08 + 2.0, pz1 + 1.52], C["hall"], i="U551")
    for yb, yt in ((-1.27, 2.54), (0.0, 5.08), (1.27, 7.62)):
        sc.tube([(ox + 5.08 - 1.75, oy + 5.08 + yb, pz1 + 0.76), (ox + 5.08 - 0.6, oy + yt, pz1 + 0.76), (ox + 5.08, oy + yt, pz1 + 0.3),
                 (ox + 5.08, oy + yt, pz0 - 1.0)], 0.2, C["lead"], i="U551")
    chip1206(sc, "C551", (ox + 7.62, oy + 2.54), (ox + 7.62, oy + 5.08), pz0 - 0.25)
    resistor(sc, "R551", (ox + 7.62, oy + 7.62), (ox + 15.24, oy + 7.62), pz1, "1k", zb=pz0)
    for k, r in enumerate([q for q in read_csv("wiring_small.csv") if q["기판"] == "PS"]):
        poly = [(ox + x, oy + y) for x, y in parse_path(r["경로 (x, y)"])]
        net = r["넷"] if not r["넷"].startswith("U551 OUT") else None
        wid = "PSW-%d" % (k + 1)
        strand(sc, down_ends(poly, pz0 - 0.4, pz0), net, wid, bare=True)
        info(wid, "PS 아랫면 %s (주석 맨선)" % r["넷"], ["%s mm · 경로 %s (로컬)" % (r["길이 (mm)"], r["경로 (x, y)"]), "wiring_small.csv · BRD-07"])
    for k, (pin, cc) in enumerate((("T", C["wire_wht"]), ("R", C["shrink_red"]), ("S", "#6b7690"))):
        x, y = [(ox + q[0], oy + q[1]) for q in ps if q[3] == "W501" and q[4] == pin][0]
        sc.tube([(x, y, pz0), (x, y, pz0 - 1.0), (x + 4.0, y, pz0 - 1.5), (ox + 26.0, oy + 5.08, pz0 - 1.5)], 0.35, cc, i="W501", g="cable",
                n=[q[2] for q in ps if q[3] == "W501" and q[4] == pin][0])
    sc.view("PB · J501 · PS", [388, 238, 14, 480, 345, 45], az=-30, el=45, default=True)
    sc.view("PB 아랫면", [424, 240, 14, 480, 318, 30], az=-30, el=-55)
    sc.view("PB 위", [424, 240, 14, 480, 318, 30], az=0, el=89)
    sc.view("J501 · W502", [440, 300, 15, 480, 345, 45], az=35, el=30)
    sc.view("PS 확대", [388, 296, 15, 422, 314, 26], az=-25, el=45)
    sc.note("W502(J502 → J501)의 실제 경로는 판 모서리를 돌아 약 40 mm로 '추정'입니다. 잭 다리 위치는 받은 잭에 따릅니다 (주황 칸).")
    return sc


# ====================================================================== J702 amp-input board (+ J701 note)
def scene_j702():
    sc = Scene("j702", "앰프 입력 기판 J702 (30 × 25, 80 Hz RC)", "가운데 유닛 세계 좌표 (x505~535 · y255~280 · z21.5~23.1).", "world", "앰프 입력 J702")
    jb = B3.J7_BOX
    z0, z1 = HN.PTS.get("j702_board", {}).get("box", [505.0, 535.0, 255.0, 280.0, 21.5, 23.1])[4:6]
    sc.board(rect(jb[0], jb[2], jb[1], jb[3]), (z0, z1), lattice([B3.j7x(i) for i in range(B3.J7_NI)], [B3.j7y(j) for j in range(B3.J7_NJ)],
                                                                lambda x, y: min(math.hypot(x - a, y - b) for a, b in B3.J7_HOLES) > 2.2),
             C["perf"], "PCB-J702", mholes=[(a, b, 3.2) for a, b in B3.J7_HOLES])
    info("PCB-J702", "J702 앰프 입력 기판 (만능기판 조각 30 × 25, 12 × 10 구멍)", [
        "헤드폰 잭 노멀(W702) → J702 → C701·C702 / C703·C704 1 µF 나란히 + R701 · R702 1 kΩ (80 Hz 고역 통과) → W707 → 앰프 입력.",
        "잭 TN · RN 다리는 고정용으로만 납땜. 도면 BRD-07, SCH-07"])
    sc.label((jb[0] + 3, jb[2] - 3.0, z1), "J702 기판", 0)
    jk = B3.J7_JACK
    sc.box([jk[0], jk[2] + 2.5, z1, jk[1], jk[3], z1 + 5.0], C["jack"], i="J702")
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, z1 + 2.5), 2.5, (jk[2], jk[2] + 2.5), C["jack"], i="J702")
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, z1 + 2.5), 1.8, (jk[2] - 0.01, jk[2] + 0.2), "#000000", i="J702")
    fz = B3.J7_FIELD
    sc.box([fz[0], fz[2], z1, fz[1], fz[3], z1 + 0.05], "#f0a830", i="J7-FIELD", g="ctx", o=0.35)
    info("J7-FIELD", "잭 다리 자리 (추정)", ["PJ-313 다리(1.8 · 3.2 · 3.5 간격)는 격자에 맞지 않아 이 칸 안의 가장 가까운 구멍에 꽂고, T · R · S 다리만 모음 패드까지 짧은 피복 가닥으로 잇습니다."])
    sc.label(((jk[0] + jk[1]) / 2, jk[2] - 1.5, z1 + 7.0), "J702 PJ-313 ← W702", 1)
    smalls = [r for r in read_csv("pads_small.csv") if r["기판"].startswith("J702")]
    pp = {}
    for r in smalls:
        pp.setdefault(r["부품"], {})[r["핀"]] = (float(r["x"]), float(r["y"]), r["넷"])
        sc.pad(float(r["x"]), float(r["y"]), (z0, z1), r["넷"], "%s.%s" % (r["부품"], r["핀"]), "b")
    # 1 uF radial MLCC (blue dipped, 5.0 x 2.5 body standing), leads 5.08 along y
    for ref in ("C701", "C702", "C703", "C704"):
        (xa, ya, _), (xb, yb, _) = pp[ref]["1"], pp[ref]["2"]
        xm, ym = (xa + xb) / 2.0, (ya + yb) / 2.0
        sc.box([xm - 1.2, ym - 2.5, z1 + 2.2, xm + 1.2, ym + 2.5, z1 + 6.6], C["mlcc"], i=ref)
        for yy in (ya, yb):
            sc.tube([(xm, yy, z1 + 2.4), (xm, yy, z0 - 1.0)], 0.25, C["lead"], i=ref)
    resistor(sc, "R701", pp["R701"]["1"][:2], pp["R701"]["2"][:2], z1, "1k", zb=z0)
    resistor(sc, "R702", pp["R702"]["1"][:2], pp["R702"]["2"][:2], z1, "1k", zb=z0)
    # jack legs -> collector pads (depend on the jack): short dashed-style strands from the field edge
    for pin, (x, y, net) in pp["J702"].items():
        fx = min(max(x, fz[0] + 0.6), fz[1] - 0.6)
        fy = min(y, fz[3] - 0.6)
        sc.tube([(fx, fy, z0), (fx, fy, z0 - 0.9), (x, y, z0 - 0.9), (x, y, z0)], 0.3, col(net), i="J7-LEG-" + pin, g="wire", n=net, w="피복 가닥 (추정)")
        info("J7-LEG-" + pin, "잭 %s 다리 → %s 모음 패드 (추정)" % (pin, pin), ["받은 잭의 다리 자리에서 가장 짧게 피복 가닥 1가닥. 넷 " + net])
    zu = z0 - 0.4
    for k, r in enumerate([q for q in read_csv("wiring_small.csv") if q["기판"] == "J702"]):
        poly = parse_path(r["경로 (x, y)"])
        bare = "맨선" in r["선"]
        wid = "J7W-%d" % (k + 1)
        strand(sc, down_ends(poly, zu - (0.0 if bare else 0.12), z0), r["넷"], wid, bare=bare)
        info(wid, "J702 아랫면 %s (%s)" % (r["넷"], r["선"]), ["%s mm · 경로 %s" % (r["길이 (mm)"], r["경로 (x, y)"]), "wiring_small.csv · BRD-07"])
    # W707 to the amp input (L / G / R), stub toward +y; W702 plug in front
    for pin, cc in (("L", C["wire_wht"]), ("G", "#6b7690"), ("R", C["shrink_red"])):
        x, y, net = pp["W707"][pin]
        sc.tube([(x, y, z0), (x, y, z0 - 1.0), (x, jb[3] + 2.0, z0 - 1.0), (x + (519.0 - x) * 0.6, jb[3] + 14.0, z0 + 1.0)], 0.35, cc, i="W707",
                g="cable", n=net)
    sc.label((519.0, jb[3] + 12.0, z1 + 3.0), "W707 → 앰프 입력", 1)
    pl = HN.PTS.get("hp_route", {}).get("j702_plug", [520.0, 222.0, 25.6])
    sc.cyl("y", (pl[0], z1 + 2.5), 1.75, (jk[2] - 14.0, jk[2] - 0.5), C["shell"], i="W702", g="cable")
    sc.cyl("y", (pl[0], z1 + 2.5), 3.0, (jk[2] - 30.0, jk[2] - 14.0), C["usb"], i="W702", g="cable")
    for hx, hy in B3.J7_HOLES:
        sc.cyl("z", (hx, hy), 3.0, (16.5, z0), C["printed"], i="CTX-POST", g="ctx", o=0.45)
        sc.cyl("z", (hx, hy), 2.75, (z1, z1 + 1.65), C["screw"], i="CTX-POST", g="ctx")
    sc.view("J702", [503, 246, 14, 537, 296, 32], az=-30, el=45, default=True)
    sc.view("W702 플러그까지", [500, 222, 14, 540, 296, 32], az=-30, el=45)
    sc.view("아랫면", [503, 253, 14, 537, 282, 26], az=-30, el=-55)
    sc.view("위", [503, 253, 14, 537, 282, 26], az=0, el=89)
    sc.note("C701~C704는 리드형 적층 세라믹 1 µF (몸통 5 × 2.5 어림). 잭 다리 → 모음 패드 3가닥은 받은 잭에 따라 '추정'입니다.")
    return sc


# ====================================================================== whole instrument wiring (world)
PAIR = {"red": C["shrink_red"], "blk": "#1d2433"}


def pair_tube(sc, pts, r, cols, i, n=None, gap=None):
    """two conductors side by side along a centre line (offset in the horizontal normal; vertical runs offset in x)."""
    if len(cols) == 1:
        sc.tube(pts, r, cols[0], i=i, g="cable", n=n)
        return
    gap = gap or r * 1.05
    out = [[], []]
    for k, p in enumerate(pts):
        a = pts[max(0, k - 1)]
        b = pts[min(len(pts) - 1, k + 1)]
        tx, ty, tz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        h = math.hypot(tx, ty)
        if h < 1e-6 * (abs(tz) + 1):
            nx, ny = 1.0, 0.0
        else:
            nx, ny = -ty / h, tx / h
        for s, o in ((1, out[0]), (-1, out[1])):
            o.append((p[0] + s * gap * nx, p[1] + s * gap * ny, p[2]))
    sc.tube(out[0], r, cols[0], i=i, g="cable", n=n)
    sc.tube(out[1], r, cols[1], i=i, g="cable", n=n)


def scene_all(SP, CAD, JK):
    sc = Scene("all", "악기 전체 배선 — 모듈 7개 · 끝 부속 · 가운데 유닛",
               "세계 좌표 (x 0 = A0 왼쪽 끝, y = 흰 건반 앞 끝부터 뒤로). 모듈 기판은 덩어리로, 가운데 유닛 기판 셋(PB · J702 · J501)은 부품까지.", "world", "악기 전체 배선")
    parts = CAD["parts"]
    # ---- modules O1..O7: coarse boards / modules / ribbon / USB plug
    for k in range(1, 8):
        X0 = X_O1 + MODULE_W * (k - 1)
        tag = "O%d" % k
        sb = SP["sb_board"]["boxes"][0]
        sc.box(shift(bx(sb), X0), C["perf"], i="PCB-SB", g="board")
        for b in SP["mb_board"]["boxes"]:
            sc.box(shift(bx(b), X0), C["perf"], i="PCB-MB", g="board")
        sc.box(shift(bx(SP["zero"]["boxes"][0]), X0), C["pcb_blue"], i="A301")
        sc.box(shift(bx(SP["zero"]["boxes"][3]), X0), C["shell"], i="A301")
        sc.box(shift(bx(SP["mux"]["boxes"][2]), X0), C["pcb_green"], i="A302")
        for b in SP["ribbon"]["boxes"][1:]:
            sc.box(shift(bx(b), X0), C["ribbon"], i="W101~W107", g="cable")
        sc.box(shift(bx(SP["usb_plug"]["boxes"][0]), X0), C["usb"], i="W20%d" % k, g="cable")
        for hid in ("hall_C", "hall_Cs", "hall_D", "hall_Ds", "hall_E", "hall_F", "hall_Fs", "hall_G", "hall_Gs", "hall_A", "hall_As", "hall_B"):
            sc.box(shift(bx(SP[hid]["boxes"][0]), X0), C["hall"], i="U201")
        sc.label((X0 + 82.0, 140.0, 12.0), tag, 0)
        if tag in ("O1", "O7"):
            for b in SP["ext_lead"]["boxes"]:
                sc.box(shift(bx(b), X0), "#7e889a", i="W403" if tag == "O1" else "W413", g="cable")
            x = X0 + 86.5
            path = ([(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, 1.5), (x - 8.0, 226.0, 1.5), (69.4 + 1.5, 231.0, 1.5)] if tag == "O1" else
                    [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, 1.5), (x + 8.0, 226.0, 1.5), (1160.0 - 1.5, 231.0, 1.5)])
            sc.tube(path, 1.5, "#7e889a", i="W403" if tag == "O1" else "W413", g="cable")
    # ---- end parts: boards, leads to the XH pairs on the passage floor
    for tag, X0, it, lead in (("EL", 0.0, "el_board", "el_lead"), ("ER", X_RIGHT, "er_board", "er_lead")):
        sc.box(shift(bx(SP[it]["boxes"][0]), X0), C["perf"], i="PCB-" + tag, g="board")
        for b in SP[lead]["boxes"]:
            sc.box(shift(bx(b), X0), C["ribbon"], i="W401" if tag == "EL" else "W411", g="cable")
        sc.label((X0 + 12.0, 60.0, 10.0), tag, 0)
    for k_, it in (("EL", "xh_left"), ("ER", "xh_right")):
        b = SP[it]["boxes"]
        sc.box(bx(b[0]), "#f4f1ea", i="XH-" + k_, g="part")
        x0_, x1_ = b[1]["x"]
        xm = (x0_ + x1_) / 2.0
        sc.tube([(xm, 212.0, 3.0), (xm, 216.0, 1.0), (b[0]["x"][0] - 1.0 if k_ == "EL" else b[0]["x"][1] + 1.0, 231.0, 1.0)], 1.0, C["ribbon"],
                i="W401" if k_ == "EL" else "W411", g="cable")
    info("XH-EL", "X401 ⇄ X402 JST-XH 6P (뒤 통로 바닥)", ["EL 리드 W401(소켓) ⇄ O1 EXT W403(플러그). 1 GND · 2~5 EXT1~4 · 6 3V3 (△6)."])
    info("XH-ER", "X411 ⇄ X412 JST-XH 6P (뒤 통로 바닥)", ["ER 리드 W411(소켓) ⇄ O7 EXT W413(플러그)."])
    # ---- headphone jack J701 (left cheek pocket) + AUX halves W701 / W702
    pk = JK["pocket"]
    cav = pk["body_cavity"]
    sc.box([cav["x"][0], cav["y"][0], cav["z"][0], cav["x"][1], cav["y"][1], cav["z"][1]], C["jack"], i="J701")
    sc.cyl("y", (pk["centre_x"], pk["axis_z"]), JK["jack_dims"]["nose_d"] / 2.0, (0.0, cav["y"][0]), C["jack"], i="J701")
    sc.label((pk["centre_x"], 0.0, pk["axis_z"] + 5.0), "J701 헤드폰 잭", 1)
    for w, cc in (("W701", C["wire_wht"]), ("W702", "#c8ccd4")):
        pts = CAD["paths"]["HP"][w]
        sc.tube([tuple(p) for p in pts], 1.75, cc, i=w, g="cable")
    # ---- USB cables (CAD centre lines)
    for k in range(1, 8):
        pts = CAD["paths"]["USB"]["O%d" % k]
        sc.tube([tuple(p) for p in pts], 1.75, C["cable"], i="W20%d" % k, g="cable")
    # ---- centre-unit parts (CAD outlines); the three small boards come from the detail scenes
    # the three small boards come from the detail scenes; the screen leads (DSI FFC, 5 V / GND) rise to the screen on the lid - the CAD
    # gives them only as top-view outlines, so they are left out here (04 3D 모델 has them); W208 / C25 are drawn from their CAD route below
    skip = {"CU-E-PEDBOARD", "CU-E-PEDZERO", "CU-E-J702BOARD", "CU-E-J702", "CU-E-J501BOARD", "CU-E-J501", "TS-C-DSI", "TS-C-PWR-RED",
            "TS-C-PWR-BLK", "C-USB-PED", "C-USB-UPSTREAM"}
    paint = {"BAT-LFP": C["battery"], "C-XT60": C["xt60"], "C-DC": C["jack"], "CU-E-FUSE": C["fuse"], "CU-E-SWITCH": "#1d1d1f",
             "CU-E-BUCK": C["buck"], "CU-E-PI5": C["pi"], "CU-E-PI5-RJ45": C["shell"], "CU-E-PI5-USBA1": C["shell"], "CU-E-PI5-USBA2": C["shell"],
             "CU-E-PI5-DISP1": "#e8e2d0", "CU-E-GENDER": C["shell"], "CU-E-DONGLE": C["dongle"], "PB-E-HUB": C["hub"], "CU-E-AMP": C["amp"],
             "C-XT60F-L": C["xt60"], "C-XT60M-L": C["xt60"], "C-XT60F-R": C["xt60"], "C-XT60M-R": C["xt60"], "C-USB-PED": C["cable"],
             "C-USB-UPSTREAM": C["cable"], "TS-C-DSI": C["ffc"], "TS-C-PWR-RED": C["shrink_red"], "TS-C-PWR-BLK": "#1d2433"}
    tube_ids = {"C-BAT-LEAD": ("BAT", ["red", "blk"]), "C-BAT-DC": ("DC", ["red", "blk"]), "C-PWR-IN": ("IN", ["red", "blk"]),
                "C-PWR-FUSE": ("FUSE", ["red"]), "C-PWR-BUS": ("BUS", None), "C-PWR-5V": ("5V", ["red", "blk"]),
                "C-SPK-L": ("SPK.L", ["red", "blk"]), "C-SPK-R": ("SPK.R", ["red", "blk"]), "C-SPKPIG-L": ("PIG.L", ["red", "blk"]),
                "C-SPKPIG-R": ("PIG.R", ["red", "blk"])}
    wid_of = {"C-BAT-LEAD": "BAT-LEAD", "C-BAT-DC": "BAT-DC", "C-PWR-IN": "W601", "C-PWR-FUSE": "W602a", "C-PWR-5V": "W603", "C-SPK-L": "W703",
              "C-SPK-R": "W705", "C-SPKPIG-L": "W704", "C-SPKPIG-R": "W706", "C-USB-PED": "W208", "C-USB-UPSTREAM": "C-USB-UPSTREAM",
              "TS-C-DSI": "TS-C-DSI", "TS-C-PWR-RED": "W608", "TS-C-PWR-BLK": "W608"}
    for pid, p in parts.items():
        if pid in skip or pid.startswith("O") and pid.endswith("-C-USB"):
            continue
        name = p["name"]
        key = wid_of.get(pid, pid)
        if key not in INFO:
            info(key, name, [p.get("note", "")[:400], "CAD %s · 상자 x%.1f~%.1f y%.1f~%.1f z%.1f~%.1f" % tuple([pid] + [p["bbox"][j] for j in (0, 3, 1, 4, 2, 5)])])
        if pid in tube_ids:
            grp, cols = tube_ids[pid]
            g1, g2 = (grp.split(".") + [None])[:2]
            polys = CAD["paths"]["PWR"][g1] if g2 is None else [CAD["paths"][g1][g2]]
            if grp == "BUS":
                pair_tube(sc, [tuple(q) for q in polys[0]], 0.75, [PAIR["red"]], "W602b")
                pair_tube(sc, [tuple(q) for q in polys[1]], 0.75, [PAIR["red"], PAIR["blk"]], "W602c")
            elif grp == "5V":
                pair_tube(sc, [tuple(q) for q in polys[0]], 0.75, [PAIR[c] for c in cols], "W603")
                pair_tube(sc, [tuple(q) for q in polys[1]], 0.75, [PAIR[c] for c in cols], "W604")
            elif grp in ("IN", "FUSE"):
                # 12 AWG holder tail (D4.2) -> soldered + heat-shrunk splice (D6.5) -> 16 AWG lead (W601: the XT60 M pair)
                sc.tube([tuple(q) for q in polys[0]], 2.1, PAIR["red"], i=key, g="cable")
                sc.tube([tuple(q) for q in polys[1]], 3.25, "#2b2b2b", i=key, g="cable")
                pair_tube(sc, [tuple(q) for q in polys[2]], 0.75, [PAIR[c] for c in cols], key)
            else:
                for pl in polys:
                    pair_tube(sc, [tuple(q) for q in pl], 0.75, [PAIR[c] for c in cols], key)
            continue
        sc.prism(p["poly"], (p["bbox"][2], p["bbox"][5]), paint.get(pid, "#6b7690"), i=key, g="cable" if pid.startswith(("C-", "TS-C")) else "part")
    # W208 PED -> hub port 2 and C25 Pi -> hub upstream: centre lines rebuilt from electronics.ped_cable() / c25_geom() points
    hub = CAD["points"]["hub"]
    for pid in ("C-USB-PED", "C-USB-UPSTREAM"):
        p = parts[pid]
        info(wid_of[pid], p["name"], [p.get("note", "")[:400], "선 중심선은 CAD 경로 점(electronics.ped_cable / c25_geom)에서 다시 그림 (보기용)"])
    cx = 449.0 + B2.ZERO_SNAP[0] + 9.14                           # PED Zero USB-C axis (PB scene, snapped)
    px = hub["ports_x"][hub["port_map"]["PED"]]
    sc.tube([(cx, 217.9, 27.0), (cx, 215.6, 27.0), (cx + 13.0, 215.6, 32.0), (cx + 27.0, 227.0, 37.0), (731.0, 227.0, 37.0),
             (px, 236.0, hub["port_z"]), (px, 248.0, hub["port_z"])], 1.75, C["cable"], i="W208", g="cable")
    for t, port in sorted(hub["port_map"].items(), key=lambda q: q[1]):
        x = hub["ports_x"][port]
        sc.box([x - 6.0, 248.0, hub["port_z"] - 3.5, x + 6.0, hub["bbox"][2], hub["port_z"] + 3.5], C["usb"], i="W208" if t == "PED" else
               "W20%s" % t[1:], g="cable")
    pi = parts["CU-E-PI5-USBA2"]["bbox"]
    face, ys, za = pi[3], (pi[1] + pi[4]) / 2.0, 26.5
    sc.box([face, ys - 7.5, za - 4.5, face + 13.0, ys + 7.5, za + 4.5], C["usb"], i="C-USB-UPSTREAM", g="cable")
    sc.cyl("z", (face + 8.5, ys), 4.0, (za + 4.5, za + 12.5), C["usb"], i="C-USB-UPSTREAM", g="cable")
    xb1, xd, xf = hub["bbox"][0] - 20.0, hub["bbox"][0] - 36.0, parts["C-USB-UPSTREAM"]["bbox"][3] - 2.0
    sc.tube([(face + 8.5, ys, za + 12.5), (face + 8.5, ys, 56.5), (face + 22.0, 303.0, 56.5), (xf, 303.0, 56.5), (xf, 319.0, 56.5),
             (xd, 319.0, 56.5), (xd, 319.0, 28.5), (xb1 - 10.0, 319.0, 28.5)], 2.0, C["cable"], i="C-USB-UPSTREAM", g="cable")
    sc.cyl("x", (319.0, 28.5), 3.5, (xb1 - 10.0, xb1), C["usb"], i="C-USB-UPSTREAM", g="cable")
    sc.box([xb1, 311.0, 22.0, hub["bbox"][0], 327.0, 35.0], C["usb"], i="C-USB-UPSTREAM", g="cable")
    for pid, lab in (("BAT-LFP", "BT601 LiFePO4 12.8 V"), ("CU-E-FUSE", "F601 5 A"), ("CU-E-SWITCH", "SW601"), ("CU-E-BUCK", "A601 XL4016 5.1 V"),
                     ("CU-E-PI5", "Pi 5"), ("PB-E-HUB", "허브 710U3"), ("CU-E-AMP", "A701 TPA3110"), ("CU-E-DONGLE", "동글")):
        b = parts[pid]["bbox"]
        sc.label(((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[5] + 4.0), lab, 0)
    # ---- detailed small boards in place
    for sub in (scene_pedal(), scene_j702()):
        for o in sub.d["objs"]:
            if o.get("k") == "l" and o.get("lv", 1) > 0:
                continue
            if sub.d["id"] == "pedal" and o.get("i", "").startswith(("PCB-PS", "U551", "C551", "R551", "PSW-")) or \
                    (sub.d["id"] == "pedal" and o.get("i") in ("U551", "C551", "R551")):
                continue
            if sub.d["id"] == "pedal" and o.get("i") == "W501" and o.get("k") == "t":
                continue
            if sub.d["id"] == "pedal" and o.get("k") in ("p",) and str(o.get("i", "")).split(".")[0] in ("U551", "C551", "R551", "W501"):
                continue
            sc.d["objs"].append(o)
    # ---- context: centre-unit printed / plywood walls (ghost)
    for c in CAD["context"]:
        sc.prism(c["poly"], (c["bbox"][2], c["bbox"][5]), C["ply"] if c.get("kind") == "plywood" else C["printed"], i="CTX-" + c["id"], g="ctx", o=0.10)
        info("CTX-" + c["id"], c["name"], ["주변 출력물 (흐리게) · CAD " + c["id"]])
    b = parts
    sc.view("전체", [-14, 0, 0, 1232, 346, 60], az=-20, el=50, default=True)
    sc.view("가운데 유닛", [255, 208, 0, 967, 346, 60], az=-25, el=55)
    sc.view("전원 구석", [372, 214, 14, 482, 345, 62], az=-35, el=45)
    sc.view("오디오 · Pi · 허브", [500, 214, 14, 920, 335, 62], az=-25, el=50)
    sc.view("위에서", [-14, 0, 0, 1232, 346, 60], az=0, el=89)
    sc.note("가운데 유닛 뚜껑 · 화면 · 스피커 통은 빼고, 아랫판 · 끝벽 · 뒤판 · 배터리 틀 · 기둥만 흐리게 보입니다. 선은 CAD의 선 중심선 (빨강 + 검정 두 가닥은 옆으로 나란히).")
    sc.note("화면 DSI · 화면 전원선(W606~W608)은 뚜껑 위 화면으로 올라가므로 여기서는 뺐습니다(04 3D 모델에 있음). USB 선은 지름 3.5 어림, 허브 쪽 플러그는 상자.")
    return sc


# ====================================================================== build
def build(write=True):
    t0 = time.time()
    INFO.clear()
    SP = load_spec()
    JK = load_jack_spec()
    with open(os.path.join(NL, "cad_centre.json"), encoding="utf-8") as f:
        CAD = json.load(f)
    bom = bom_info()
    cable_info()
    info("W101~W107", "W101~W107 센서 리본 (16심 28 AWG, 1.27 피치)", ["SB J201 → MB J301, 두 끝 모두 아랫면 납땜. 자르는 길이 180 (경로 85, 남는 95는 차선 안에서 접음).",
                                                                     "1번 심(빨간 줄) = 3V3, 2·15 = GND, 3~14 = HALL_C~B, 16 = 3V3 (△12).", "구매 목록 C05"])
    info("BAT-LEAD", "BT601 팩 XT60 선 (배터리에 딸림)", ["팩 +x 끝면 → 선 꺾는 자리 → 팩 윗면 XT60 암 X605 (빨강 수축)."])
    info("BAT-DC", "BT601 충전 선 (배터리에 딸림)", ["팩 +x 끝면 → 팩 윗면 DC 5.5 × 2.1 충전 입력 (14.4 V)."])
    scenes = [scene_all(SP, CAD, JK), scene_module(SP, bom), scene_end(SP), scene_pedal(), scene_j702()]
    nets = {}
    for s in scenes:
        for o in s.d["objs"]:
            n = o.get("n")
            if n:
                nets[n] = col(n)
            i = o.get("i")
            if i and i not in INFO:
                base = i.split(".")[0]
                if base not in INFO and not i.startswith(("CTX", "J7-", "J5-")):
                    INFO.setdefault(base, dict(t=base, d=[]))
    data = dict(rev=REV, built=time.strftime("%Y-%m-%d %H:%M"), nets=nets, info=INFO, scenes=[s.d for s in scenes],
                src=["hardware/pcb/src/model3d.py", "netlist/*.csv · cad_centre.json", "cad/spec/electronics_modules.json"])
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if write:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(txt)
    rep = dict(bytes=len(txt.encode("utf-8")), seconds=round(time.time() - t0, 2),
               scenes={s.d["id"]: len(s.d["objs"]) for s in scenes}, nets=len(nets), info=len(INFO))
    return data, rep


def check(data):
    """every pad / wire net is a real net of the netlist (or None), every info key the viewer will ask for exists."""
    probs = []
    real = {r["넷"] for r in NET_ROWS}
    for s in data["scenes"]:
        for o in s["objs"]:
            n = o.get("n")
            if n and n not in real:
                probs.append("%s: net %s (%s) not in netlist.csv" % (s["id"], n, o.get("i")))
            i = o.get("i")
            if i and i.split(".")[0] not in data["info"] and i not in data["info"]:
                probs.append("%s: no info for %s" % (s["id"], i))
    return probs


if __name__ == "__main__":
    d, rep = build()
    pr = check(d)
    print("model3d:", rep)
    for p in pr[:40]:
        print("  !", p)
    print("problems:", len(pr))
    sys.exit(1 if pr else 0)
