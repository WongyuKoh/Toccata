"""Self-check for electronics.py (L1 low rear bar, spec/body_low_L1.json).

  python3 check_electronics.py

(1) lists every electronics Part (kind / group / bodies / bbox),
(2) pairwise overlaps (a ^ b volume > 0.01 mm3): electronics x electronics, electronics x key action,
    electronics x body - body.py when it builds the L1 rear bar, otherwise an L1 body proxy built here from the L1 spec
    (+ the v3 centre-unit printed parts moved by the L1 shift). Each overlap is matched to an EXPECTED reason or reported,
(3) L1 checks: overall 1254 x 447, speaker pose on the 30 deg baffle (flange / axis / magnet clearance to the bottom
    panel), CU-bay parts in their shifted spec boxes, I/O-plate parts at the L1 hole x / z46.5 and under the lid z76.5,
    module USB cable lengths (plug 25 + path + hub plug 20 <= 1000), cables low in the trough (z<=22), through the
    front-panel notch, over the low divider, hub against the back wall, XT30 pairs at the speaker fronts, J701, pedal,
    R31 touchscreen (display pose / folded altview, DSI ribbon path + length + hinge-loop radius, J1 power lead).
"""
import json
import math
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

T0 = time.time()
TOL = 0.01          # mm3 overlap threshold
EPS = 0.02          # mm bbox tolerance

# (regex a, regex b, reason, max volume or None) - a/b match either order
EXPECTED = [
    # electronics x electronics
    (r"-C-USB$|^C-USB-PED$", r"-E-ZERO$|^CU-E-PEDZERO$", "USB-C 플러그 금속 쉘이 Zero 리셉터클 안으로 들어감 (의도)", None),
    (r"^CU-E-GENDER$", r"^CU-E-PI5-USBA1$", "젠더 USB-A 플러그가 Pi USB-A 포트 안으로 들어감 (의도)", None),
    (r"^C-USB-UPSTREAM$", r"^CU-E-PI5-USBA2$", "업스트림 USB-A 플러그가 Pi 포트 안으로 들어감 (의도)", None),
    (r"^CU-E-DONGLE$", r"^CU-E-GENDER$", "동글 USB-C 플러그가 젠더 C 소켓 안으로 들어감 (의도)", None),
    (r"^C-XT30M-", r"^C-XT30F-", "XT30 수·암 짝맞춤 (의도)", None),
    (r"^TS-C-DSI$", r"^TS-E-TD2$", "R31 리본 끝이 화면 DSI 커넥터(ZIF, 입구 -x)에 3 mm 꽂힘 (의도)", 20.0),
    (r"^TS-C-DSI$", r"^CU-E-PI5-DISP1$", "R31 리본 끝이 Pi 5 CAM/DISP 1 커넥터(ZIF)에 0.5 mm 꽂힘 (의도)", 5.0),
    # electronics x key action
    (r"-E-MB$", r"-B-controlboardscrew", "M3×6 나사 몸통이 기판 구멍 Ø3.2를 지남 (다각형 근사)", None),
    (r"-E-MB$", r"-FRAME$", "프레임 위치 핀 Ø2.8 ↔ 기판 구멍 Ø3.0 (의도, 다각형 근사)", None),
    # electronics x body: the basket Ø94 passes the Ø94 cut-out / gasket hole (same diameter, polygon approximation)
    (r"^SPK-[LR]$", r"BAFFLE|baffle|경사|GASKET|gasket|가스켓", "바스켓 Ø94가 컷아웃·가스켓 구멍 Ø94를 지남 (다각형 근사)", 5.0),
]

SPEC_CONFLICTS = []


def load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


def bb(p):
    if not hasattr(p, "_bb"):
        p._bb = p.solid.bounding_box()
    return p._bb


def boxes_touch(a, b):
    return not any(a[i] > b[i + 3] + 1e-6 or b[i] > a[i + 3] + 1e-6 for i in range(3))


def overlap(a, b):
    if not boxes_touch(bb(a), bb(b)):
        return 0.0
    return (a.solid ^ b.solid).volume()


def reason(a, b, table, v=0.0):
    ka, kb = a.id + " " + a.name_ko, b.id + " " + b.name_ko
    for row in table:
        ra, rb, why = row[0], row[1], row[2]
        vmax = row[3] if len(row) > 3 else None
        if vmax is not None and v > vmax:
            continue
        if (re.search(ra, a.id) and (re.search(rb, b.id) or re.search(rb, kb))) or \
           (re.search(ra, b.id) and (re.search(rb, a.id) or re.search(rb, ka))):
            return why
    return None


# ------------------------------------------------------------------ L1 body proxy (while body.py is not the L1 body)

class Proxy:
    def __init__(self, id, name_ko, solid):
        self.id, self.name_ko, self.solid, self.note, self.kind = id, name_ko, solid, "", "proxy"


def body_proxy():
    """L1 body envelopes: speaker parts (5 okoume panels + slanted baffle with the Ø94 cut-out + EVA gasket ring), centre
    unit (panels, front-panel notch x583..733 z16.5..34, divider, low divider z..56.5, lids z76.5..88), CU tray and I/O plate
    (v3 printed parts moved by the L1 shift, plate holes at the L1 x / z46.5), lid corner supports 18x18x12 under z76.5,
    power-bank holder (v3 moved by the shift), EVA joint strips, trough brackets. Feet, grilles and XT30 holders are left
    out (positions not in the L1 spec)."""
    from cadlib import box, cyl_x, cyl_y, cyl_z, diff, prism_x, union
    import electronics_L1 as E           # archived L1 checker: checks the archived L1 generators
    L1 = load("body_low_L1.json")
    C = load("body_centre_unit.json")
    dx, dy, dz = E.SHIFT
    out = []

    def bx(b, s=(0, 0, 0)):
        return box(b["x"][0] + s[0], b["x"][1] + s[0], b["y"][0] + s[1], b["y"][1] + s[1], b["z"][0] + s[2], b["z"][1] + s[2])

    def mir(m):
        return m.mirror((1, 0, 0)).translate((2 * E.MIRROR_X, 0, 0))

    # ---- speaker parts (L built, R mirrored)
    sp = L1["speaker"]
    xo0, xo1 = sp["L"]["x"]
    t = L1["rear_bar"]["panel_t"]
    xi0, xi1 = xo0 + t, xo1 - t                                  # inner x -4.5 .. 185.5 (190)
    y0, y1 = L1["rear_bar"]["y"]
    z0, z1 = sp["z"]
    sl = sp["front"]["slant_outer_face"]
    (ya, za), (yb, zb) = sl["from_yz"], sl["to_yz"]
    n = E.SPK_N
    iy, iz = -t * n[1], -t * n[2]                                # inner offset (+9.96, -5.75)
    pent = [(y0, z0), (y1, z0), (y1, z1), (yb, z1), (ya, za)]
    cx, cy, cz = E.SPK_C["L"]
    cut = E.Manifold.cylinder(t + 2.0, 47.0, 47.0, 96).translate((0, 0, -t - 1.0)).transform(E.spk_frame(cx, cy, cz))
    gasket = diff(box(-52.5, 52.5, -52.5, 52.5, 0.0, E.GASKET_T), [cyl_z(0, 0, -0.1, E.GASKET_T + 0.1, 94.0)]) \
        .transform(E.spk_frame(cx, cy, cz))
    spk = [("SIDEOUT", "스피커 옆판(바깥)", prism_x(pent, xo0, xi0)),
           ("SIDEIN", "스피커 옆판(가운데 쪽)", prism_x(pent, xi1, xo1)),
           ("BOTTOM", "스피커 아랫판", box(xi0, xi1, y0, y1 - t, z0, z0 + t)),
           ("STRIP", "스피커 앞 세운 띠", box(xi0, xi1, y0, y0 + t, z0 + t, za)),
           ("BAFFLE", "스피커 경사 배플(출력)", diff(prism_x([(ya, za), (yb, zb), (yb + iy, zb + iz), (ya + iy, za + iz)], xi0, xi1), [cut])),
           ("TOP", "스피커 윗판", box(xi0, xi1, 316.0, y1 - t, z1 - t, z1)),
           ("BACK", "스피커 뒤판", box(xi0, xi1, y1 - t, y1, z0, z1)),
           ("GASKET", "유닛 EVA 가스켓 3T", gasket)]
    for tag, nm, sol in spk:
        out.append(Proxy("PX-SPKL-" + tag, nm + " L", sol))
        out.append(Proxy("PX-SPKR-" + tag, nm + " R", mir(sol)))
    for (xa, xb) in ((197.0, 200.0), (1022.0, 1025.0)):
        out.append(Proxy("PX-EVA-%.0f" % xa, "이음 EVA 3T 띠", box(xa, xb, y0, y1, z0, 88.0)))
    out.append(Proxy("PX-BRACKET-L", "방진 브래킷 L (통로 건넘, 대용)", box(-16.0, -0.7, 212.0, 252.0, 8.0, 16.0)))
    out.append(Proxy("PX-BRACKET-R", "방진 브래킷 R (통로 건넘, 대용)", box(1222.0, 1238.0, 212.0, 252.0, 8.0, 16.0)))

    # ---- centre unit panels
    ce = L1["centre"]
    X0, X1 = ce["x"]
    Z0, Z1 = ce["z"]
    zi0, zi1 = ce["inner_z"]
    yi0, yi1 = ce["inner_y"]
    bays = ce["bays_inner_x"]
    tx0, tx1 = ce["cu_tray"]["x"]
    out += [Proxy("PX-CU-BOTTOM-L", "가운데 아랫판 왼쪽", box(X0, tx0, y0, y1, Z0, zi0)),
            Proxy("PX-CU-BOTTOM-R", "가운데 아랫판 오른쪽", box(tx1, X1, y0, y1, Z0, zi0)),
            Proxy("PX-CU-FRONT", "가운데 앞판 (케이블 홈 x583~733 z16.5~34)",
                  diff(box(X0, X1, y0, y0 + t, zi0, Z1), [box(E.INLET_X[0], E.INLET_X[1], y0 - 1, y0 + t + 1, zi0 - 0.01, E.INLET_Z[1])])),
            Proxy("PX-CU-BACK-L", "가운데 뒤판 왼쪽", box(X0, tx0, yi1, y1, zi0, Z1)),
            Proxy("PX-CU-BACK-R", "가운데 뒤판 오른쪽", box(tx1, X1, yi1, y1, zi0, Z1)),
            Proxy("PX-CU-END-L", "가운데 끝판 왼쪽", box(*bays["end_L"], yi0, yi1, zi0, zi1)),
            Proxy("PX-CU-END-R", "가운데 끝판 오른쪽", box(*bays["end_R"], yi0, yi1, zi0, zi1)),
            Proxy("PX-CU-DIV", "칸막이(보관함 ↔ CU)", box(*bays["divider"], yi0, yi1, zi0, zi1)),
            Proxy("PX-CU-LOWDIV", "낮은 칸막이(CU ↔ 보조배터리)", box(*bays["low_divider"], yi0, yi1, zi0, E.LOW_DIV_TOP)),
            Proxy("PX-CU-LIDS", "뚜껑들 z76.5~88", box(bays["end_L"][1], bays["end_R"][0], yi0, yi1, zi1, Z1))]
    # lid corner supports 18x18x12 under the lids, 4 per bay
    for bay in ("key_storage", "cu", "power_bank"):
        bx0, bx1 = bays[bay]
        for (xa, xb) in ((bx0, bx0 + 18.0), (bx1 - 18.0, bx1)):
            for (ya_, yb_) in ((yi0, yi0 + 18.0), (yi1 - 18.0, yi1)):
                out.append(Proxy("PX-LIDSUP-%s-%.0f-%.0f" % (bay, xa, ya_), "뚜껑 모서리 받침 18×18×12", box(xa, xb, ya_, yb_, zi1 - 12.0, zi1)))

    # ---- CU tray (v3 PR-CU-TRAY moved by the shift; solid 11.5 plate + bosses)
    pr = {q["id"]: q for q in C["printed"]}
    f = {q["name"]: q for q in pr["PR-CU-TRAY"]["features"]}
    adds = [box(tx0, tx1, y0, y1, Z0, zi0)]
    for nm in ("pi5_bosses", "amp_bosses", "buck_bosses", "amp_input_jack_board_bosses"):
        q = f[nm]
        adds += [cyl_z(x + dx, y + dy, q["z"][0] + dz, q["z"][1] + dz, q.get("od", 7.0)) for (x, y) in q["at"]]
    q = f["ped_board_standoffs"]
    adds += [cyl_z(x + dx, y + dy, zi0, 38.5 + dz, 6.0) for (x, y) in q["screw_at"] + q["pin_at"]]
    adds += [cyl_z(x + dx, y + dy, 38.5 + dz, 41.0 + dz, 2.8) for (x, y) in q["pin_at"]]
    q = f["foot_screw_bosses"]
    adds += [cyl_z(x + dx, y + dy, zi0, q["z"][1] + dz, q["d"]) for (x, y) in q["at"]]
    adds += [bx(tab["box"], E.SHIFT) for tab in f["divider_screw_tabs"]["tabs"]]
    cr = f["fuse_holder_cradle"]["box"]
    yc, zc = 311.0 + dy, 40.5 + dz
    adds.append(diff(bx(cr, E.SHIFT), [cyl_x(yc, zc, cr["x"][0] + dx - 1, cr["x"][1] + dx + 1, f["fuse_holder_cradle"]["inner_d"]),
                                        box(cr["x"][0] + dx - 1, cr["x"][1] + dx + 1, yc - 5.25, yc + 5.25, zc, cr["z"][1] + dz + 1)]))
    out.append(Proxy("PX-CU-TRAY", "CU 트레이 (v3 + L1 이동)", union(adds)))

    # ---- I/O plate (x556.05..756.05, y435.5..447, z16.5..76.5; skin 2 at y445..447; holes at z46.5)
    io = ce["io_plate"]
    ix0, ix1 = io["x"]
    iy0, iy1 = io["y"]
    iz0, iz1 = io["z"]
    hz = io["holes"]["z"]
    ho = io["holes"]
    iof = {q["name"]: q for q in pr["PR-IO-PLATE"]["features"]}
    led = iof["pedal_jack_hole"]["mount"]["box"]
    lx0, lx1 = led["x"][0] + dx, led["x"][1] + dx
    ly0 = led["y"][0] + dy
    ledge_top = hz - 2.5 - 1.6
    blk = iof["usb_c_input"]["pocket"]
    iosh = E.IO_SHIFT
    parts = [box(ix0, ix1, iy1 - 2.0, iy1, iz0, iz1),                       # skin
             box(ix0, ix1, iy0, iy1, iz0, iz0 + 4.0), box(ix0, ix1, iy0, iy1, iz1 - 4.0, iz1),
             box(ix0, 564.8, iy0, iy1, iz0, iz1), box(747.3, ix1, iy0, iy1, iz0, iz1),
             box(lx0, lx1, ly0, iy1 - 2.0 + 0.01, ledge_top - 8.0, ledge_top),
             diff(bx(blk["block"], iosh), [bx(blk["cavity"], iosh), box(blk["cavity"]["x"][0] + iosh[0], blk["cavity"]["x"][1] + iosh[0],
                                                                            blk["block"]["y"][0] + iosh[1] - 0.1, blk["cavity"]["y"][1] + iosh[1],
                                                                            blk["cavity"]["z"][0] + iosh[2], blk["cavity"]["z"][1] + iosh[2])])]
    cuts = [cyl_y(ho["pedal_jack_J501_x"], hz, iy1 - 3, iy1 + 1, 6.5),
            box(ho["switch_KCD1_x"] - 6.6, ho["switch_KCD1_x"] + 6.6, iy1 - 3, iy1 + 1, hz - 9.6, hz + 9.6),
            box(ho["usb_c_input_x"] - 6.75, ho["usb_c_input_x"] + 6.75, iy1 - 3, iy1 + 1, hz - 4.0, hz + 4.0),
            box(ho["cable_pass_x"] - 9, ho["cable_pass_x"] + 9, iy0 - 1, iy1 + 1, hz - 5.5, hz + 5.5)]
    out.append(Proxy("PX-CU-IOPLATE", "I/O 판 (L1 대용)", diff(union(parts), cuts)))

    # ---- power-bank holder (v3 PR-PB-HOLDER moved by the shift)
    h = pr["PR-PB-HOLDER"]["geometry"]
    hp = [bx(h["base"]["box"], E.SHIFT), bx(h["left_stop_wall"], E.SHIFT), bx(h["front_stop_wall"], E.SHIFT)]
    hk = h["strap"]["right_hook"]["box"]
    hp.append(box(hk["x"][0] + dx, hk["x"][1] + dx, hk["y"][0] + dy - 2, hk["y"][1] + dy + 2, hk["z"][0] + dz, hk["z"][1] + dz))
    hp += [cyl_z(x + dx, y + dy, 33.5 + dz, 36.5 + dz, 10) for (x, y) in h["screw_pads"]["at"]]
    out.append(Proxy("PX-PBHOLDER", "보조배터리 받침 (v3 + L1 이동)", union(hp)))
    return out


def body_is_l1(B):
    """body.py builds the L1 rear bar when its parts reach the L1 depth (y > 440) and none stand above z140."""
    if not B:
        return False
    ymax = max(p.solid.bounding_box()[4] for p in B if p.note != "offdesk")
    zmax = max(p.solid.bounding_box()[5] for p in B if p.note != "offdesk" and "터치" not in p.group)   # R31 screen stands to z222.6
    return ymax > 440.0 and zmax < 140.0


def fmt(b):
    return "x%.2f..%.2f y%.2f..%.2f z%.2f..%.2f" % (b[0], b[3], b[1], b[4], b[2], b[5])


def inside(b, box, tol=EPS):
    return (b[0] >= box["x"][0] - tol and b[3] <= box["x"][1] + tol and b[1] >= box["y"][0] - tol and b[4] <= box["y"][1] + tol
            and b[2] >= box["z"][0] - tol and b[5] <= box["z"][1] + tol)


def slab(m, axis, a0, a1):
    """part of m with a0 <= coord <= a1 along axis (0 x, 1 y, 2 z); bbox or None."""
    nv = [0, 0, 0]
    nv[axis] = 1
    s = m.trim_by_plane(tuple(nv), a0)
    nv[axis] = -1
    s = s.trim_by_plane(tuple(nv), -a1)
    return None if s.is_empty() else s.bounding_box()


def main():
    import electronics_L1 as E           # archived L1 checker: checks the archived L1 generators
    import keyaction_parts
    P_ = E.build()
    Ep = P_
    K = keyaction_parts.build_all()
    B, body_msg = [], ""
    body_path = os.path.join(HERE, "body_L1.py")
    if os.path.exists(body_path):
        try:
            import body_L1 as body
            B = body.build()
            if not body_is_l1(B):
                body_msg = "body.py는 아직 v3 (높은 뒷바) - L1 대용 상자로 검사"
                B = []
        except Exception as ex:          # the body agent may be mid-edit
            body_msg = "body.py import/build 실패 (%s: %s) - L1 대용 상자로 검사" % (type(ex).__name__, str(ex)[:80])
            B = []
    X = [] if B else body_proxy()
    t_build = time.time() - T0
    ok = True
    spec_issues = []

    # ------------------------------------------------------------------ (1) list
    print("=" * 100)
    print("(1) electronics parts: %d   (key action %d, body %s)   build %.1f s" % (len(Ep), len(K), ("%d (body.py L1)" % len(B)) if B else body_msg, t_build))
    ids = [p.id for p in Ep]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        ok = False
        print("  ! duplicate ids:", dup)
    clash = sorted(set(ids) & ({p.id for p in K} | {p.id for p in B}))
    if clash:
        ok = False
        print("  ! ids also used by other generators:", clash)
    for p in Ep:
        n = len(p.solid.decompose())
        flag = "" if n == 1 else "  ! %d bodies" % n
        if n != 1:
            ok = False
        if p.kind not in ("electronics", "bought", "consumable"):
            ok = False
            flag += "  ! kind"
        print("  %-16s %-11s %-18s %s  vol %9.1f%s%s" % (p.id, p.kind, p.group, fmt(bb(p)), p.solid.volume(),
                                                        "  [" + p.note + "]" if p.note == "offdesk" else "", flag))
    groups = {}
    for p in Ep:
        groups[p.group] = groups.get(p.group, 0) + 1
    print("  groups:", ", ".join("%s %d" % kv for kv in groups.items()))
    no_est = [p.id for p in Ep if p.note and p.note != "offdesk" and not p.note.startswith("추정:") and "추정" in p.note]
    if no_est:
        ok = False
        print("  ! notes with 추정 not at the start:", no_est)

    # ------------------------------------------------------------------ (2) overlaps
    print("=" * 100)
    print("(2) overlaps > %.2f mm3" % TOL)
    onsite = [p for p in Ep if p.note != "offdesk"]

    def same_state(a, b):
        # R31: the folded screen ('altview') and the standing screen are two states of the same parts
        return not ((a.note == "altview") != (b.note == "altview") and "터치" in a.group and "터치" in b.group)
    sets = [("전자 x 전자", [(a, b) for i, a in enumerate(onsite) for b in onsite[i + 1:] if same_state(a, b)]),
            ("전자 x 건반 동작부", [(a, b) for a in onsite for b in K])]
    if B:
        sets.append(("전자 x 몸체 (body.py L1)", [(a, b) for a in onsite for b in B if b.note != "offdesk" and same_state(a, b)]))
    else:
        sets.append(("전자 x 몸체 L1 대용 (%d개)" % len(X), [(a, b) for a in onsite for b in X]))
    for title, pairs in sets:
        exp, conf, bad = [], [], []
        for a, b in pairs:
            v = overlap(a, b)
            if v <= TOL:
                continue
            w = reason(a, b, EXPECTED, v)
            c = reason(a, b, SPEC_CONFLICTS, v)
            (exp if w else conf if c else bad).append((v, a, b, w or c))
        print("  -- %s: expected %d, spec conflicts %d, UNEXPECTED %d" % (title, len(exp), len(conf), len(bad)))
        for v, a, b, w in sorted(exp, key=lambda r: -r[0]):
            print("     ok   %9.3f  %-16s ^ %-26s %s" % (v, a.id, b.id, w))
        for v, a, b, w in sorted(conf, key=lambda r: -r[0]):
            print("     SPEC %9.3f  %-16s ^ %-26s %s" % (v, a.id, b.id, w))
        for v, a, b, w in sorted(bad, key=lambda r: -r[0]):
            ok = False
            ib = (a.solid ^ b.solid).bounding_box()
            print("     !!   %9.3f  %-16s ^ %-26s (%s) at %s" % (v, a.id, b.id, b.name_ko[:40], fmt(ib)))

    # ------------------------------------------------------------------ (3) L1 checks
    print("=" * 100)
    print("(3) L1 checks")
    P = {p.id: p for p in Ep}
    L1 = load("body_low_L1.json")
    C = load("body_centre_unit.json")
    F = load("keyaction_features_frame.json")
    tray = next(q for q in C["printed"] if q["id"] == "PR-CU-TRAY")
    comp = {c["name_ko"]: c["box"] for c in tray["components"]}
    io = next(q for q in C["printed"] if q["id"] == "PR-IO-PLATE")
    iof = {f["name"]: f for f in io["features"]}
    dx, dy, dz = E.SHIFT
    res = []

    def chk(label, cond, detail=""):
        nonlocal ok
        res.append(("ok" if cond else "!!", label, detail))
        if not cond:
            ok = False

    def info(label, detail=""):
        res.append(("..", label, detail))

    def spec(label, detail=""):
        res.append(("SPEC", label, detail))
        spec_issues.append(label)

    def union_bb(ps):
        bs = [bb(p) for p in ps]
        return [min(b[i] for b in bs) for i in range(3)] + [max(b[i] for b in bs) for i in range(3, 6)]

    # ---- overall
    allp = [p for p in K + Ep + (B or X) if p.note != "offdesk"]
    ob = union_bb(allp)
    info("overall (key action + electronics + %s, off-desk pedal excluded) %.2f x %.2f x %.2f" % ("body.py" if B else "L1 대용",
         ob[3] - ob[0], ob[4] - ob[1], ob[5] - ob[2]), fmt(ob))
    eb = union_bb(onsite)
    chk("electronics inside x-16..1238", eb[0] >= -16 - EPS and eb[3] <= 1238 + EPS, fmt(eb))
    chk("electronics y >= 0 (front lip), z >= 0 (desk)", eb[1] >= -EPS and eb[2] >= -EPS, fmt(eb))
    ov = L1["overall"]["y"][1]
    over_back = [p.id + " y..%.2f" % bb(p)[4] for p in onsite if bb(p)[4] > ov + EPS]
    chk("only the KCD1 bezel (2 mm, outside the plate as in v3) behind the back face y%.0f" % ov, over_back == ["CU-E-SWITCH y..%.2f" % (ov + 2)],
        ", ".join(over_back) or "none")

    # ---- speakers on the slanted baffle
    drv = L1["speaker"]["driver"]
    n, u = np.array(E.SPK_N), np.array(E.SPK_U)
    zbot = L1["centre"]["inner_z"][0]          # bottom panel top z16.5 (speaker bottom panel z5..16.5 too)
    for side in "LR":
        pid = "SPK-" + side
        cx, cy, cz = E.SPK_C[side]
        v, _f = __import__("cadlib").mesh_arrays(P[pid].solid)
        rel = v - np.array([cx, cy, cz])
        w = rel @ n
        bpos = rel @ u
        chk("%s centre x%.1f (bbox) and flange ±52.5 in x / up the slant" % (pid, cx),
            abs((bb(P[pid])[0] + bb(P[pid])[3]) / 2 - cx) < 0.05 and abs(bpos.max() - 52.5) < 0.05 and abs(bpos.min() + 52.5) < 0.05,
            "b %.2f..%.2f" % (bpos.min(), bpos.max()))
        chk("%s along the axis (-cos30, +sin30): flange front w+%.1f (gasket 3 + flange 4), magnet back w%.1f, depth 61"
            % (pid, E.GASKET_T + 4, E.GASKET_T + 4 - drv["depth_total"]),
            abs(w.max() - (E.GASKET_T + 4)) < 0.02 and abs(w.min() - (E.GASKET_T + 4 - drv["depth_total"])) < 0.02,
            "w %.3f..%.3f" % (w.min(), w.max()))
        mlow = bb(P[pid])[2]
        chk("%s magnet low corner z%.2f clears the bottom panel top z%.1f" % (pid, mlow, zbot), mlow >= zbot, "gap %.2f" % (mlow - zbot))
        if mlow < zbot + 2.0 - EPS:
            back = -(E.GASKET_T + 4 - drv["depth_total"])
            spec("%s magnet low corner z%.2f < spec target z%.1f (16.5 + 2). L1 why_centre_z uses the magnet CENTRE 52.5 behind the "
                 "axis origin (C_z − 26.25 − 36.8 = %.2f). Front-mounted (gasket 3 + flange 4 on the face) the magnet spans %.0f..%.0f behind "
                 "the face and its lowest point is the rear-face corner: C_z − %.0f·sin30 − 42.5·cos30 = %.2f. Target met with the driver "
                 "centre at z ≥ %.2f (+%.2f = %.2f up the slant; grille zone then %.2f of 60.5 up the slant)"
                 % (pid, mlow, zbot + 2, drv["centre_yz"][1] - 26.25 - 36.8, back - 17, back, back, mlow, drv["centre_yz"][1] + zbot + 2 - mlow,
                    zbot + 2 - mlow, (zbot + 2 - mlow) / u[2], 59 + (zbot + 2 - mlow) / u[2]), "")
        xin = (-16 + 11.5, 197 - 11.5) if side == "L" else (1025 + 11.5, 1238 - 11.5)
        m = P[pid].solid
        cn = float(np.array([cx, cy, cz]) @ n)
        t_b = L1["rear_bar"]["panel_t"]
        b = m.trim_by_plane(tuple(-n), t_b - cn).bounding_box()        # part behind the baffle inner face (w <= -11.5)
        chk("%s behind the baffle inside the speaker-box inner x%.1f..%.1f, z%.1f..%.1f, y <= %.1f"
            % (pid, xin[0], xin[1], zbot, 134 - t_b, 447 - t_b),
            b[0] >= xin[0] and b[3] <= xin[1] and b[2] >= zbot and b[5] <= 134 - t_b and b[4] <= 447 - t_b, fmt(b))
        bf = m.trim_by_plane(tuple(n), cn).bounding_box()                # part in front of the outer face (w >= 0)
        sl = L1["speaker"]["front"]["slant_outer_face"]
        chk("%s flange + rim in front of the face stay on the slant (outer face z%.2f..%.2f) and within x%.1f..%.1f"
            % (pid, sl["from_yz"][1], sl["to_yz"][1], xin[0], xin[1]),
            bf[2] >= sl["from_yz"][1] and bf[5] <= sl["to_yz"][1] and bf[0] >= xin[0] and bf[3] <= xin[1], fmt(bf))
        # width in x at a plane through the basket (w=-20) and the magnet (w=-45)
        for wv, dia, lbl in ((-20.0, drv["cutout_d"], "basket"), (-45.0, drv["magnet"]["d"], "magnet")):
            pc = np.array([cx, cy, cz]) + wv * n
            s = m.trim_by_plane(tuple(n), float(pc @ n) - 0.5).trim_by_plane(tuple(-n), -(float(pc @ n) + 0.5)).bounding_box()
            chk("%s %s Ø%.0f at w%.0f (x width)" % (pid, lbl, dia, wv), abs((s[3] - s[0]) - dia) < 0.3, "%.2f" % (s[3] - s[0]))
        # trough rule: the part in the trough (y <= 252) stays between z22 and z72
        tb = slab(m, 1, 200.0, 252.0)
        if tb:
            chk("%s: part in the trough y<252 (flange low edge) between z22 and z72, protrudes <= 15 along the normal" % pid,
                tb[2] >= 22 and tb[5] <= 72, fmt(tb))
    # ---- CU bay parts vs shifted body_centre_unit component boxes
    cu_map = [("CU-E-PI5", "라즈베리파이 5"), ("CU-E-AMP", "앰프 보드"), ("CU-E-BUCK", "5.1 V 강압 모듈"),
              ("CU-E-PEDBOARD", "페달 보드"), ("CU-E-PEDZERO", "페달 보드"), ("CU-E-J702BOARD", "앰프 입력 잭 기판"),
              ("CU-E-J702", "앰프 입력 잭 기판"), ("CU-E-FUSE", "퓨즈 홀더"), ("PB-E-BANK", "보조배터리(최대)")]
    jd = F["cheeks"]["headphone_jack"]["jack_dims"]
    for pid, cname in cu_map:
        b = bb(P[pid])
        box = E.shifted_box(comp[cname])
        if pid == "CU-E-J702":
            box["y"] = [box["y"][0], box["y"][1] + jd["nose_L"]]
        chk("%s inside moved CU-spec box '%s' %s" % (pid, cname, fmt([box["x"][0], box["y"][0], box["z"][0], box["x"][1], box["y"][1], box["z"][1]])),
            inside(b, box), fmt(b))
    pb5 = bb(P["CU-E-PI5"])
    chk("CU-E-PI5 board = v3 x531..616 y336..392 z39.5 moved by (%.2f, %.0f, %.0f)" % (dx, dy, dz),
        abs(pb5[0] - 531 - dx) < EPS and abs(pb5[1] - 336 - dy) < EPS and abs(pb5[2] - 39.5 - dz) < EPS, fmt(pb5))
    pp = [bb(P["CU-E-PI5-" + k]) for k in ("RJ45", "USBA1", "USBA2")]
    yc = [(q[1] + q[4]) / 2 for q in pp]
    chk("Pi 5 port order from the power/HDMI edge y%.0f: RJ45 < USB-A 1 < USB-A 2 (y %s)" % (pb5[1], " / ".join("%.2f" % v for v in yc)),
        pb5[1] < pp[0][1] and yc[0] < yc[1] < yc[2] and pp[2][4] <= pb5[4] + EPS)
    chk("Pi 5 port faces = board edge + 2.5", all(abs(q[3] - pb5[3] - 2.5) < EPS for q in pp), " ".join("%.2f" % q[3] for q in pp))
    gb = bb(P["CU-E-GENDER"])
    chk("CU-E-GENDER in the LOWER port of the USB-A stack next to the RJ45", abs((gb[1] + gb[4]) / 2 - yc[1]) < EPS and gb[5] < pp[1][5] - 6
        and abs(gb[0] - pp[1][3]) < EPS, fmt(gb))
    upb = slab(P["C-USB-UPSTREAM"].solid, 0, pp[2][3] - 1, pp[2][3] + 24.0)
    chk("C-USB-UPSTREAM straight plug in the UPPER port of the GPIO-edge stack", upb[1] <= yc[2] <= upb[4] and upb[2] >= pp[2][5] - 8.0 - EPS
        and upb[5] <= pp[2][5] + EPS, fmt(upb))
    ko = E.shifted_box(next(k for k in tray["keep_out"] if k["name"] == "pi_usb_plugs")["box"])
    for pid, b in (("CU-E-GENDER", gb), ("CU-E-DONGLE", bb(P["CU-E-DONGLE"])), ("C-USB-UPSTREAM plug (x<=%.0f)" % ko["x"][1], upb)):
        chk("%s plan inside moved keep-out pi_usb_plugs x%.2f..%.2f y%.0f..%.0f" % (pid, ko["x"][0], ko["x"][1], ko["y"][0], ko["y"][1]),
            b[0] >= ko["x"][0] - EPS and b[3] <= ko["x"][1] + EPS and b[1] >= ko["y"][0] - EPS and b[4] <= ko["y"][1] + EPS, fmt(b))
    # PJ-313 envelopes
    want = (jd["body_W"], jd["body_L"] + jd["nose_L"], jd["body_H"])
    for pid in ("EL-E-J701", "CU-E-J501", "CU-E-J702"):
        b = bb(P[pid])
        got = (b[3] - b[0], b[4] - b[1], b[5] - b[2])
        chk("%s PJ-313 envelope %.1f x %.1f x %.1f" % (pid, *want), all(abs(g_ - w_) < EPS for g_, w_ in zip(got, want)), "%.2f x %.2f x %.2f" % got)
    b, jb2 = bb(P["CU-E-J702"]), bb(P["CU-E-J702BOARD"])
    chk("CU-E-J702 base on its board top z%.1f, nose from the rear edge y%.0f, x%.2f" % (jb2[5], jb2[4], 691 + dx),
        abs(b[2] - jb2[5]) < EPS and abs(b[4] - jb2[4] - jd["nose_L"]) < EPS and abs((b[0] + b[3]) / 2 - 691 - dx) < EPS, fmt(b))
    # ---- I/O plate parts: L1 hole x, centre z46.5, under the lid
    ho = L1["centre"]["io_plate"]["holes"]
    hz = ho["z"]
    b, jb1 = bb(P["CU-E-J501"]), bb(P["CU-E-J501BOARD"])
    chk("CU-E-J501 axis x%.2f z%.1f (base on its board top z%.1f), nose tip = plate outer face y447" % (ho["pedal_jack_J501_x"], hz, jb1[5]),
        abs((b[0] + b[3]) / 2 - ho["pedal_jack_J501_x"]) < EPS and abs(jb1[5] + jd["axis_above_base"] - hz) < EPS and abs(b[2] - jb1[5]) < EPS
        and abs(b[4] - 447) < EPS, fmt(b))
    info("J501 board bottom z%.2f = required I/O-plate ledge top (ledge x%.2f..%.2f y%.0f..%.0f, body agent)" % (jb1[2], jb1[0], jb1[3], jb1[1], jb1[4]))
    for pid, key in (("CU-E-SWITCH", "switch_KCD1_x"), ("CU-E-PDTRIG", "usb_c_input_x")):
        b = bb(P[pid])
        chk("%s centred on L1 hole %s x%.2f z%.1f" % (pid, key, ho[key], hz),
            abs((b[0] + b[3]) / 2 - ho[key]) < 0.05 and abs((b[2] + b[5]) / 2 - hz) < 0.35, fmt(b))
    cav = E.shifted_box(iof["usb_c_input"]["pocket"]["cavity"], E.IO_SHIFT)
    chk("CU-E-PDTRIG inside the moved PD pocket cavity %s" % fmt([cav["x"][0], cav["y"][0], cav["z"][0], cav["x"][1], cav["y"][1], cav["z"][1]]),
        inside(bb(P["CU-E-PDTRIG"]), cav), fmt(bb(P["CU-E-PDTRIG"])))
    for pid in ("CU-E-J501", "CU-E-J501BOARD", "CU-E-SWITCH", "CU-E-PDTRIG"):
        chk("%s top z%.2f under the lid z76.5" % (pid, bb(P[pid])[5]), bb(P[pid])[5] <= 76.5)
    # KCD1 lug vs Pi USB-A stack
    sw = P["CU-E-SWITCH"].solid
    lug = slab(sw, 1, 426.0, 433.9)
    st = pp[2]
    info("KCD1 lower lug z%.2f..  vs Pi GPIO-edge USB-A stack top z%.2f: gap %.2f (plan overlap x%.2f..%.2f y%.2f..%.2f) - solder the "
         "lugs, faston receptacles would touch" % (lug[2], st[5], lug[2] - st[5], max(lug[0], st[0]), min(lug[3], st[3]), max(lug[1], st[1]),
                                                    min(lug[4], st[4])))
    # ---- cables
    cp = E.cable_plan()
    for t in sorted(cp["_len"]):
        ln = cp["_len"][t]
        chk("%s-C-USB length %.1f mm <= %.0f (plug 25 + path %.1f + hub plug 20; hub port %d x%.0f)"
            % (t, ln, E.USB_CABLE_MAX, ln - 45, E.HUB_PORT[t], cp["_xhub"][t]), ln <= E.USB_CABLE_MAX)
    info("C-USB-PED length about %.0f mm, C-USB-UPSTREAM about %.0f mm" % (E.LENGTHS["PED"], E.LENGTHS["UPSTREAM"]))
    tr_y = L1["cable_trough"]["y"]
    usb = ["O%d-C-USB" % k for k in range(1, 8)]
    for pid in usb + ["O1-C-EXT", "O7-C-EXT", "EL-C-LEAD", "ER-C-LEAD", "C-XH-L", "C-XH-R"]:
        tb = slab(P[pid].solid, 1, tr_y[0], tr_y[1])
        if tb:
            chk("%s in the trough y%.0f..%.0f stays low z <= %.0f" % (pid, tr_y[0], tr_y[1], L1["cable_trough"]["z"][1]),
                tb[5] <= L1["cable_trough"]["z"][1] + EPS, fmt(tb))
    for pid in usb:
        nb = slab(P[pid].solid, 1, 252.0, 263.5)
        chk("%s through the front-panel notch x%.0f..%.0f z%.1f..%.0f" % (pid, E.INLET_X[0], E.INLET_X[1], E.INLET_Z[0], E.INLET_Z[1]),
            nb[0] >= E.INLET_X[0] and nb[3] <= E.INLET_X[1] and nb[2] >= E.INLET_Z[0] and nb[5] <= E.INLET_Z[1], fmt(nb))
    for pid in usb + ["C-USB-PED", "C-USB-UPSTREAM"]:
        db = slab(P[pid].solid.trim_by_plane((0, 1, 0), L1["centre"]["inner_y"][0]), 0, *L1["centre"]["bays_inner_x"]["low_divider"])
        chk("%s crosses the low divider over its top z%.1f" % (pid, E.LOW_DIV_TOP), db[2] >= E.LOW_DIV_TOP, "z%.2f.." % db[2])
    tro = [p.id for p in onsite if (lambda s: s is not None and s[5] > 72.0)(slab(p.solid, 1, tr_y[0], tr_y[1]))]
    chk("trough rule: nothing above z72 in y%.0f..%.0f" % tuple(tr_y), not tro, ", ".join(tro) or "none")
    # ---- rear-bar bays
    ce = L1["centre"]
    bays = ce["bays_inner_x"]
    cub = {"x": bays["cu"], "y": [ce["inner_y"][0], ce["y"][1] + 2.0], "z": ce["inner_z"]}
    for p in Ep:
        if p.group == "CU 칸 전자부":
            chk("%s inside the CU bay x%.1f..%.1f y%.1f..447 (+2 bezel) z%.1f..%.1f" % (p.id, cub["x"][0], cub["x"][1], cub["y"][0], *cub["z"]),
                inside(bb(p), cub), fmt(bb(p)))
    pbay = {"x": bays["power_bank"], "y": ce["inner_y"], "z": ce["inner_z"]}
    for pid in ("PB-E-HUB", "PB-E-BANK"):
        chk("%s inside the power-bank bay x%.1f..%.1f" % (pid, *bays["power_bank"]), inside(bb(P[pid]), pbay), fmt(bb(P[pid])))
    hb = bb(P["PB-E-HUB"])
    chk("PB-E-HUB 228x48x24 flat against the back wall y387.5..435.5 on the floor z16.5",
        abs(hb[1] - 387.5) < EPS and abs(hb[4] - 435.5) < EPS and abs(hb[2] - 16.5) < EPS and abs(hb[5] - 40.5) < EPS
        and abs(hb[3] - hb[0] - 228) < EPS, fmt(hb))
    for pid in usb + ["C-USB-PED", "C-USB-UPSTREAM"]:
        chk("%s under the lid z76.5" % pid, bb(P[pid])[5] <= ce["inner_z"][1], "z..%.2f" % bb(P[pid])[5])
    # ---- XT30 at the speaker fronts (female in the holder pocket, pair in the trough above the cables)
    pockets, psrc = E.xt30_pockets()
    for side in "LR":
        x0, x1, y0, y1, z0, z1 = pockets[side]
        fb = bb(P["C-XT30F-" + side])
        chk("C-XT30F-%s inside the %s pocket x%.1f..%.1f y%.1f..%.1f z%.1f..%.1f, mouth at the pocket end" % (side, psrc, x0, x1, y0, y1, z0, z1),
            inside(fb, {"x": [x0, x1], "y": [y0, y1], "z": [z0, z1]}) and (abs(fb[3] - x1) < EPS if side == "L" else abs(fb[0] - x0) < EPS), fmt(fb))
        mb = bb(P["C-XT30M-" + side])
        chk("C-XT30M-%s toward the centre unit, in the trough y<=252 above the cables (z >= %.0f)" % (side, L1["cable_trough"]["z"][1]),
            (mb[0] >= fb[3] - EPS if side == "L" else mb[3] <= fb[0] + EPS) and mb[4] <= 252 + EPS and min(mb[2], fb[2]) >= L1["cable_trough"]["z"][1],
            fmt(mb))
    # ---- J701, pedal, modules
    cavj = F["cheeks"]["headphone_jack"]["pocket"]["body_cavity"]
    b = bb(P["EL-E-J701"])
    chk("EL-E-J701 inside the cheek cavity, nose from y0", b[0] >= cavj["x"][0] and b[3] <= cavj["x"][1] and b[2] >= cavj["z"][0]
        and b[5] <= cavj["z"][1] and abs(b[1]) < EPS and b[4] <= cavj["y"][1], fmt(b))
    pb_ = bb(P["PEDAL-DAMPER"])
    chk("PEDAL-DAMPER note=offdesk and below the desk", P["PEDAL-DAMPER"].note == "offdesk" and pb_[5] < 0, fmt(pb_))
    for k in range(1, 8):
        X0 = 47 + 164.5 * (k - 1)
        b = bb(P["O%d-E-MB" % k])
        chk("O%d-E-MB at local x47.25..117.25" % k, abs(b[0] - X0 - 47.25) < EPS and abs(b[3] - X0 - 117.25) < EPS, fmt(b))
    keyside = [p.id for p in onsite if bb(p)[4] < 212.0 + EPS and not re.match(r"^(O\d|EL|ER)-", p.id)]
    chk("only module / end-part electronics live in y<212", not keyside, ", ".join(keyside) or "none")


    # ---- R31 touchscreen (touchscreen/CAD_SPEC.md F, numbers.json points)
    import touchscreen as TS
    from cadlib import box as _box, cyl_z as _cyl_z
    NP = TS.N["points"]
    vol = lambda a, b: (a ^ b).volume()
    td = P["TS-E-TD2"]
    tb = bb(td)
    gb, gt, gc = NP["use"]["glass_bottom"], NP["use"]["glass_top"], NP["use"]["glass_centre"]
    chk("TS-E-TD2 25 deg: glass x561.34..750.66, bottom edge (y%.2f z%.2f) = front-most, top edge (y%.2f z%.2f) = highest" % (*gb, *gt),
        abs(tb[0] - 561.34) < EPS and abs(tb[3] - 750.66) < EPS and abs(tb[1] - gb[0]) < 0.02 and abs(tb[5] - gt[1]) < 0.02, fmt(tb))
    cy_, cz_ = TS.pt(TS.GLASS[1] / 2.0, 0.0, TS.TILT_USE)
    chk("TS-E-TD2 glass centre x656 (y%.2f z%.2f) on the lens" % tuple(gc), abs(cy_ - gc[0]) < 0.02 and abs(cz_ - gc[1]) < 0.02
        and vol(td.solid, TS.place(_box(655, 657, 59.1, 61.1, 0.05, 0.6), TS.TILT_USE)) > 0.99 * 2 * 2 * 0.55, "y%.2f z%.2f" % (cy_, cz_))
    ftb = bb(P["TS-E-TD2-FOLD"])
    fg = NP["fold"]
    chk("TS-E-TD2-FOLD altview: glass y%.2f..%.2f face up at z%.0f, standoffs down to z%.2f (lid top z88)" % (fg["glass_bottom"][0], fg["glass_top"][0],
        fg["glass_bottom"][1], 112 - 14.92), P["TS-E-TD2-FOLD"].note == "altview" and abs(ftb[1] - fg["glass_bottom"][0]) < 0.02
        and abs(ftb[4] - fg["glass_top"][0]) < 0.02 and abs(ftb[5] - 112.0) < 0.02, fmt(ftb))
    import electronics_L1 as _E
    tl = _E.td2_local()[0]
    chk("TS-E-TD2 DSI connector x%.2f..%.2f u52.1..68.1 (opens -x), J1 x647..658 u36.5..43, 4 lugs at w6.4..9.4, standoffs to w14.92"
        % (TS.DSI["open_x"], 2 * TS.DSI["x_centre"] - TS.DSI["open_x"]),
        vol(tl, _box(TS.DSI["open_x"] + 0.1, 2 * TS.DSI["x_centre"] - TS.DSI["open_x"] - 0.1, 52.2, 68.0, 6.5, 8.3)) > 0.99 * 17.7 * 15.8 * 1.8
        and vol(tl, _box(647.1, 657.9, 36.6, 42.9, 6.5, 8.9)) > 0.99 * 10.8 * 6.3 * 2.4
        and tl.bounding_box()[5] <= 14.92 + EPS and all(vol(tl, _box(x - 4.4, x - 1.5, u - 6.9, u + 6.9, 6.5, 9.39)) > 0 for x in TS.LUG_X for u in TS.LUG_U))
    if B:
        Bb = {p.id: p for p in B}
        cr = Bb["TS-CRADLE"].solid
        s25, c25 = TS.rot(TS.TILT_USE)
        chk("TS-E-TD2 inside the cradle: no overlap, lugs touch the back plate w9.4 (shift +0.05 w overlaps), glass 0.3 from the walls",
            vol(td.solid, cr) < TOL and vol(td.solid.translate((0, 0.05 * c25, -0.05 * s25)), cr) > 0.01
            and vol(td.solid.translate((0.28, 0, 0)), cr) < TOL and vol(td.solid.translate((0.35, 0, 0)), cr) > 0.01)
    rib = P["TS-C-DSI"]
    L_rib = E.LENGTHS["DSI"]
    chk("TS-C-DSI length %.0f mm <= 285 (spec G: paper strip) and 300 cable (margin %.0f)" % (L_rib, 300 - L_rib), L_rib <= 285.0)
    hs = slab(rib.solid, 2, 77.0, 87.5)
    chk("TS-C-DSI through the lid hole x592..614 y292..298", hs is not None and hs[0] >= 592 and hs[3] <= 614 and hs[1] >= 292 and hs[4] <= 298, fmt(hs))
    up = slab(rib.solid, 2, 88.5, 300.0)
    chk("TS-C-DSI above the lid in the lane x597..613 up to the 45 deg fold, then +x to the connector (x..%.1f)" % (TS.DSI["open_x"] + 3.0),
        up[0] >= 597.0 - EPS and up[3] <= TS.DSI["open_x"] + 3.0 + 0.2, fmt(up))
    lp = _E.ribbon_paths()["loop"]
    bay_x = slab(rib.solid, 2, 0, 76.6)[3]
    info("TS-C-DSI in the CU bay max x%.1f -> amp / speaker leads (x>=700) %.0f mm away; loop above the lid about %.0f mm"
         % (bay_x, 700 - bay_x, _E._path_len(lp)))
    # bend radius of the hinge loop (centre-line polyline)
    rmin = 1e9
    for a, b_, c in zip(lp[:-2], lp[1:-1], lp[2:]):
        ab, bc, ac = math.dist(a, b_), math.dist(b_, c), math.dist(a, c)
        area2 = abs((b_[0] - a[0]) * (c[1] - a[1]) - (b_[1] - a[1]) * (c[0] - a[0]))
        if area2 > 1e-9:
            rmin = min(rmin, ab * bc * ac / (2 * area2))
    chk("TS-C-DSI hinge loop smallest bend radius R%.1f >= R10 (D24)" % rmin, rmin >= 10.0 - 0.05)
    pw = P["TS-C-POWER"]
    L_pw = E.LENGTHS["TD2_POWER"]
    chk("TS-C-POWER path %.0f mm <= jumpers 400 mm (+ TD2 kit lead)" % L_pw, L_pw <= 400.0)
    hs = slab(pw.solid, 2, 77.0, 87.5)
    chk("TS-C-POWER through the lid hole beside the ribbon (x592..596, y292..298)", hs is not None and hs[0] >= 592 and hs[3] <= 596 and hs[1] >= 292
        and hs[4] <= 298, fmt(hs))
    gp = slab(pw.solid, 2, 32.0, 41.0)
    chk("TS-C-POWER housing on Pi GPIO pins 2 / 6 (x574.15..581.77 y425.5..428.1), left of the J501 ledge x583.55", gp[0] >= 574.1 and gp[3] <= 583.5
        and gp[1] >= 425.4 and gp[4] <= 428.2, fmt(gp))
    wz = slab(pw.solid.trim_by_plane((0, 0, -1), -TS.LID_Z0), 1, 310.0, 430.0)
    chk("TS-C-POWER along the left wall at z<=56, under the rear corner support (z64.5), y310..430", wz[5] < 64.5, fmt(wz))
    if B:
        ov = [(b_.id, vol(pw.solid, b_.solid)) for b_ in B if b_.note != "offdesk" and b_.note != "altview" and boxes_touch(bb(pw), bb(b_))]
        info("TS-C-POWER / TS-C-DSI clear of every body part: %s" % (", ".join("%s %.3f" % o for o in ov if o[1] > TOL) or "yes"))
    chk("CU-E-PI5-DISP1 next to the Pi 5 HDMI edge (x614..617, y374..389, on the board top z24.1)", abs(bb(P["CU-E-PI5-DISP1"])[2] - 24.1) < EPS
        and abs(bb(P["CU-E-PI5-DISP1"])[0] - 614.0) < EPS)
    chk("R31 altview parts only in group '터치스크린 (접은 상태, 별도 보기)'", all(p.group == "터치스크린 (접은 상태, 별도 보기)" for p in Ep if p.note == "altview")
        and [p.id for p in Ep if p.note == "altview"] == ["TS-E-TD2-FOLD"])

    for st_, label, det in res:
        print("  %-4s %s  %s" % (st_, label, det))
    print("=" * 100)
    print("RESULT:", "PASS" if ok else "ISSUES (see !! lines)", "- spec-level issues: %d (SPEC lines)" % len(spec_issues),
          "  total %.1f s" % (time.time() - T0))


if __name__ == "__main__":
    main()
