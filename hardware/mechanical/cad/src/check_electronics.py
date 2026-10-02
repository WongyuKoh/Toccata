"""Self-check for electronics.py (L2 one-piece rear bar, spec/body_L2.json).

  python3 check_electronics.py

(1) every electronics Part: kind / group / bbox / bodies, watertight exported mesh, Korean name, 추정 note format; the R31 touchscreen
    rev 3 parts come from touchscreen_rev3.py (rev 3a numbers); the folded-screen 'altview' parts are never checked against the standing ones,
(2) pairwise overlaps (a ^ b volume > 0.01 mm3): electronics x electronics, electronics x key action, electronics x body (body.py
    L2). Every overlap is matched to an EXPECTED reason or reported,
(3) L2 checks (implementation_notes.check_electronics.py + the task list):
    - every CU-E-* / PB-E-* item at / inside its spec centre_contents bbox, plugs inside their Z-* zones, keep-out zones free,
    - centre items inside the centre inner space (x271.5..950.5, y214..body.YBI, z <= 61.35 under the lids; back-plate I/O to body.YB;
      40 deg: 331 / 342.5, 43 deg: 330 / 341.5),
      no item in the front zone below z27, items >= 1.0 apart and cables >= 0.5 from unrelated parts (min gap on the solids),
    - hub: spec bbox, ports -y at x696.5 + 22 i, plugs per port_map, plug zone in front of the shelf (not under it) under LID-R,
    - cables: lengths vs the spec table and <= standard length - 40, every rear-unit cable inside the body envelope (duct y212..241
      z0..27, centre unit, joint holes, pod cavities) and not crossing any solid, nothing above z18.3 in the 2 mm air gap,
    - drivers: pose / axis (body.py ANGLE), magnet >= 2 mm from every pod wall (back ply target 3.5), pole vent >= 10 mm free along
      the axis, basket <-> sill, normal depth, D14 (magnet centre >= 100 from the sensor row, nearest steel reported), the spec's
      27 deg sound path (flange / gasket corners >= 3.0 under it, grille plate edge = spec exception),
    - XT30 pairs in the end-wall clips, pigtails through the sealed D6 pod hole and the D14 end-wall hole into the pod, speaker
      leads and the power harness ending on their terminals,
(4) R31 touchscreen rev 3 (touchscreen/rev3/design/CAD_SPEC_rev3.md C, F, G + numbers.json points / ribbon / power_wire / pi5):
    display pose and fit in the cradle, DSI FFC route (lid hole, clip clamp, drop column in Z-DSI, 2.7 into CAM/DISP 1) and length,
    Pi heatsink / micro-HDMI clearance on the CAD Pi pose, power leads (hole, clip groove, GPIO 2 / 6), keep-out over the modules,
    sound paths to the ears past the screen, Pi orientation vs the CAD connector box.
"""
import itertools
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
    (r"^CU-E-DONGLE$", r"^CU-E-GENDER$", "동글 USB-C 플러그(6.5)가 젠더 C 소켓 안으로 들어감 (의도)", 400.0),
    (r"^C-XT30M-", r"^C-XT30F-", "XT30 수·암 짝맞춤 (면 닿음)", 0.5),
    # electronics x key action
    (r"-E-MB$", r"-B-controlboardscrew", "M3×6 나사 몸통이 기판 구멍 Ø3.2를 지남 (다각형 근사)", None),
    (r"-E-MB$", r"-FRAME$", "프레임 위치 핀 Ø2.8 ↔ 기판 구멍 Ø3.0 (의도, 다각형 근사)", None),
    # electronics x body
    (r"^SPK-[LR]$", r"^SPK[LR]-(BAFFLE|GASKET)$", "바스켓 Ø94가 앞판 구멍·가스켓 구멍 Ø94를 지남 (같은 원 - 다각형 근사)", 5.0),
    (r"^C-XT30F-", r"^XT30-CLIP-", "XT30U-F가 집게 홈에 끼움 (면 닿음)", 0.5),
    (r"^CU-E-SWITCH$", r"^PR-BACKPLATE$", "KCD1 몸통 13.2×19.2가 같은 크기 구멍에 스냅 (면 닿음)", 0.5),
    # R31 touchscreen rev 3
    (r"^TS-C-DSI$", r"^TS-E-SCREEN$", "R31 리본 끝이 화면 ZIF에 3.5 꽂힘 (의도)", 15.0),
    (r"^TS-C-DSI$", r"^CU-E-PI5-DISP1$", "R31 리본 끝이 Pi 5 CAM/DISP 1에 2.7 꽂힘 (의도)", 12.0),
    (r"^TS-C-PWR-(RED|BLK)$", r"^TS-E-SCREEN$", "R31 전원선 끝이 화면 MX1.25에 2 들어감 (의도)", 3.0),
    (r"^TS-C-PWR-(RED|BLK)$", r"^CU-E-PI5$", "R31 F 점퍼 하우징이 GPIO 핀 2·6에 끼움 (헤더 상자는 핀 끝까지 한 덩어리로 모델)", 40.0),
    (r"^TS-E-SCREEN$", r"^TS-M25-\d$", "R31 M2.5×6이 화면 모서리 구멍에 나사산을 냄 (물림 3, 구멍 안지름 Ø2.2로 모델)", 5.0),
]

SPEC_CONFLICTS = []


def load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


def bb(p):
    if not hasattr(p, "_bb"):
        p._bb = p.solid.bounding_box()
    return p._bb


def boxes_touch(a, b, gap=0.0):
    return not any(a[i] > b[i + 3] + gap + 1e-6 or b[i] > a[i + 3] + gap + 1e-6 for i in range(3))


def overlap(a, b):
    if not boxes_touch(bb(a), bb(b)):
        return 0.0
    return (a.solid ^ b.solid).volume()


def reason(a, b, table, v=0.0):
    for row in table:
        ra, rb, why = row[0], row[1], row[2]
        vmax = row[3] if len(row) > 3 else None
        if vmax is not None and v > vmax:
            continue
        if (re.search(ra, a.id) and re.search(rb, b.id)) or (re.search(ra, b.id) and re.search(rb, a.id)):
            return why
    return None


def fmt(b):
    return "x%.2f..%.2f y%.2f..%.2f z%.2f..%.2f" % (b[0], b[3], b[1], b[4], b[2], b[5])


def cfmt(c):
    return "x%.2f..%.2f y%.2f..%.2f z%.2f..%.2f" % tuple(c)


def inside(b, c, tol=EPS):
    """bbox b (manifold order) inside the spec box c = (x0, x1, y0, y1, z0, z1)."""
    return (b[0] >= c[0] - tol and b[3] <= c[1] + tol and b[1] >= c[2] - tol and b[4] <= c[3] + tol and b[2] >= c[4] - tol
            and b[5] <= c[5] + tol)


def same(b, c, tol=EPS):
    return all(abs(v - w) <= tol for v, w in zip((b[0], b[3], b[1], b[4], b[2], b[5]), c))


def slab(m, axis, a0, a1):
    """bbox of the part of m with a0 <= coord <= a1 along axis (0 x, 1 y, 2 z), or None."""
    nv = [0, 0, 0]
    nv[axis] = 1
    s = m.trim_by_plane(tuple(nv), a0)
    nv[axis] = -1
    s = s.trim_by_plane(tuple(nv), -a1)
    return None if s.is_empty() else s.bounding_box()


def hangul(s):
    return any("가" <= ch <= "힣" for ch in s)


def watertight(m):
    import trimesh
    from cadlib import mesh_arrays, tidy
    v, f = mesh_arrays(tidy(m))
    t = trimesh.Trimesh(vertices=v, faces=f, process=True)
    return bool(t.is_watertight and t.is_winding_consistent and t.is_volume)


def main():
    import electronics as E
    import body
    import keyaction_parts
    import touchscreen_rev3 as TS
    from cadlib import box, cyl_x, cyl_z, prism_x, union
    Ep = E.build()
    B = body.build()
    K = keyaction_parts.build_all()
    t_build = time.time() - T0
    ok = True
    res = []
    spec_issues = []

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

    # ------------------------------------------------------------------ (1) list
    print("=" * 110)
    print("(1) electronics parts: %d   (key action %d, body %d - body.py L2, ANGLE %.1f)   build %.1f s" % (len(Ep), len(K), len(B), body.ANGLE, t_build))
    ids = [p.id for p in Ep]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    chk("electronics ids unique", not dup, ", ".join(dup) or "")
    clash = sorted(set(ids) & ({p.id for p in K} | {p.id for p in B}))
    chk("electronics ids not used by the key action / body generators", not clash, ", ".join(clash))
    probs = []
    for p in Ep:
        n = len(p.solid.decompose())
        flag = ""
        if n != 1:
            probs.append("%s %d bodies" % (p.id, n))
            flag += "  ! %d bodies" % n
        if p.kind not in ("electronics", "bought", "consumable"):
            probs.append("%s kind %s" % (p.id, p.kind))
        if not hangul(p.name_ko) or not p.name_en or not p.group or not p.source:
            probs.append("%s name / group / source" % p.id)
        if p.note and p.note not in ("offdesk",) and "추정" in p.note and not p.note.startswith("추정") and "; 추정" not in p.note:
            probs.append("%s 추정 note format" % p.id)
        if p.solid.is_empty() or str(p.solid.status()).split(".")[-1] != "NoError":
            probs.append("%s empty / status" % p.id)
        elif min(c.volume() for c in p.solid.decompose()) < 0.5:
            probs.append("%s sliver shell" % p.id)
        print("  %-16s %-11s %-16s %s  vol %9.1f%s%s" % (p.id, p.kind, p.group, fmt(bb(p)), p.solid.volume(),
                                                         "  [" + p.note + "]" if p.note == "offdesk" else "", flag))
    n_wt = sum(1 for p in Ep if watertight(p.solid))
    chk("every part: one body, kind electronics, Korean name / group / source, 추정 note format, no sliver", not probs, "; ".join(probs[:8]))
    chk("every part: exported mesh watertight (trimesh)", n_wt == len(Ep), "%d / %d" % (n_wt, len(Ep)))
    groups = {}
    for p in Ep:
        groups[p.group] = groups.get(p.group, 0) + 1
    print("  groups:", ", ".join("%s %d" % kv for kv in groups.items()))
    ts_ids = sorted(i for i in ids if re.match(r"^TS-", i))
    src_e = open(os.path.join(HERE, "electronics.py")).read()
    chk("R31 rev 3 touchscreen parts from touchscreen_rev3.py (numbers %s): %s; altview only the folded display" % (TS.N["revision"][:2], ", ".join(ts_ids)),
        ts_ids == ["TS-C-DSI", "TS-C-PWR-BLK", "TS-C-PWR-RED", "TS-E-SCREEN", "TS-E-SCREEN-FOLD"] and re.search(r"^import touchscreen_rev3 as TS", src_e, re.M) is not None
        and [p.id for p in Ep if p.note == "altview"] == ["TS-E-SCREEN-FOLD"] and "rev3" in TS.TS_DIR)

    def other_state(a, b):
        """R31: the folded screen ('altview') and the standing screen are two states of the same parts - never checked against each other."""
        return (a.note == "altview") != (b.note == "altview") and "터치" in a.group and "터치" in b.group

    # ------------------------------------------------------------------ (2) overlaps
    print("=" * 110)
    print("(2) overlaps > %.2f mm3" % TOL)
    onsite = [p for p in Ep if p.note != "offdesk"]
    sets = [("전자 x 전자", [(a, b) for i, a in enumerate(onsite) for b in onsite[i + 1:] if not other_state(a, b)]),
            ("전자 x 건반 동작부", [(a, b) for a in onsite for b in K]),
            ("전자 x 몸체 (body.py L2)", [(a, b) for a in onsite for b in B if b.note != "offdesk" and not other_state(a, b)])]
    for title, pairs in sets:
        exp, bad = [], []
        for a, b in pairs:
            v = overlap(a, b)
            if v <= TOL:
                continue
            w = reason(a, b, EXPECTED, v)
            (exp if w else bad).append((v, a, b, w))
        chk("%s: no unexpected overlap" % title, not bad, "expected %d, UNEXPECTED %d" % (len(exp), len(bad)))
        print("  -- %s: expected %d, UNEXPECTED %d" % (title, len(exp), len(bad)))
        for v, a, b, w in sorted(exp, key=lambda r: -r[0])[:12]:
            print("     ok   %9.3f  %-16s ^ %-24s %s" % (v, a.id, b.id, w))
        if len(exp) > 12:
            print("     ok   (%d more)" % (len(exp) - 12))
        for v, a, b, w in sorted(bad, key=lambda r: -r[0]):
            ib = (a.solid ^ b.solid).bounding_box()
            print("     !!   %9.3f  %-16s ^ %-24s (%s) at %s" % (v, a.id, b.id, b.name_ko[:30], fmt(ib)))

    # ------------------------------------------------------------------ (3) L2 checks
    print("=" * 110)
    print("(3) L2 checks")
    P = {p.id: p for p in Ep}
    Bb = {p.id: p for p in B}
    L2 = load("body_L2.json")
    F = load("keyaction_features_frame.json")
    CC = E.CC

    # ---- spec centre_contents items
    exact = ["CU-E-PI5", "CU-E-PI5-RJ45", "CU-E-PI5-USBA1", "CU-E-PI5-USBA2", "CU-E-PI5-DISP1", "CU-E-GENDER", "CU-E-AMP", "CU-E-BUCK",
             "CU-E-PEDBOARD", "CU-E-PEDZERO", "CU-E-J702BOARD", "CU-E-J702", "CU-E-FUSE", "CU-E-J501BOARD", "CU-E-J501", "CU-E-PDTRIG",
             "PB-E-HUB", "PB-E-BANK"]
    items = [c["id"] for c in L2["centre_contents"] if c["kind"] in ("item", "io") and re.match(r"^(CU-E|PB-E)-", c["id"])]
    miss = [i for i in items if i not in P]
    chk("every spec CU-E-* / PB-E-* item has a part with the same id (%d)" % len(items), not miss, ", ".join(miss))
    for cid in items:
        if cid not in P:
            continue
        b = bb(P[cid])
        shift = " (spec box y+%.1f: rides on the back plate, back face y%.1f)" % (body.DY_BACK, body.YB) if cid in body.BACK_PLATE_ITEMS and body.DY_BACK else ""
        if cid in exact:
            chk("%s at its spec bbox %s (spec rounded to 0.1)%s" % (cid, cfmt(CC[cid]), shift), same(b, CC[cid], 0.06), fmt(b))
        elif cid == "CU-E-SWITCH":                       # bezel flush with the back face body.YB (E.CC already moved by body.DY_BACK)
            c = CC[cid]
            chk("%s inside its spec bbox %s%s, bezel flush with y%.1f" % (cid, cfmt(c), shift, body.YB),
                inside(b, c) and abs(b[4] - body.YB) < EPS, fmt(b))
        else:
            chk("%s inside its spec bbox %s" % (cid, cfmt(CC[cid])), inside(b, CC[cid]), fmt(b))
    # plugs inside their zones
    def part_slab_in(pid, axis, a0, a1, zone, tol=0.2, label=None):
        s = slab(P[pid].solid, axis, a0, a1)
        good = s is not None and inside(s, CC[zone], tol)
        chk(label or ("%s (%s %.1f..%.1f) inside %s %s" % (pid, "xyz"[axis], a0, a1, zone, cfmt(CC[zone]))), good, fmt(s) if s else "none")
        return s
    zped = CC["Z-PED-PLUG"]
    s = slab(P["C-USB-PED"].solid.trim_by_plane((-1, 0, 0), -(zped[1] + 1.0)), 1, zped[2] + 0.01, zped[3] - 0.01)
    chk("C-USB-PED plug in Z-PED-PLUG x/y (%s), z within 1.0 of the zone" % cfmt(zped),
        s is not None and s[0] >= zped[0] - 0.2 and s[3] <= zped[1] + 0.2 and s[1] >= zped[2] - EPS and s[4] <= zped[3] + EPS
        and s[2] >= zped[4] - EPS and s[5] <= zped[5] + 1.0, fmt(s) if s else "")
    if s is not None and s[5] > zped[5] + EPS:
        spec("Z-PED-PLUG z%.0f..%.0f assumes the PED Zero receptacle axis at z26; the spec's own CU-E-PEDZERO box z23.1..28.8 puts the "
             "module Zero stack's receptacle at z27.0, so the 7.6 plug spans z%.2f..%.2f (0.8 over the zone top; nothing above it, the PED "
             "lane starts at z33)" % (zped[4], zped[5], s[2], s[5]))
    # C24 (Coms BT663) side-angled USB-C head at the Pi -y edge, lead out toward -x (the buck)
    mth = slab(P["C-PWR-5V"].solid.trim_by_plane((1, 0, 0), E.C24_HEAD[0]).trim_by_plane((-1, 0, 0), -570.0), 1, 248.9, 262.1)
    chk("C24 BT663 side-angled USB-C head (C-PWR-5V, x>=546) %.0f x %.0f x %.1f inside Z-PI-PWR %s, lead out -x through the collar x%.1f..%.0f"
        % (E.C24_HEAD[1] - E.C24_HEAD[0], E.C24_HEAD[3] - E.C24_HEAD[2], E.C24_HEAD[5] - E.C24_HEAD[4], cfmt(CC["Z-PI-PWR"]), E.C24_COLLAR[0], E.C24_COLLAR[1]),
        mth is not None and inside(mth, CC["Z-PI-PWR"], 0.05) and E.C24_COLLAR[1] <= CC["Z-PI-PWR"][0] + EPS, fmt(mth) if mth else "")
    def mbb(c):
        return (c[0], c[2], c[4], c[1], c[3], c[5])
    near_pi = [p.id for p in onsite if p.id not in ("C-PWR-5V", "CU-E-PI5") and boxes_touch(bb(p), mbb(CC["Z-PI-PWR"]), 0.5)
               and p.solid.min_gap(box(*CC["Z-PI-PWR"]), 0.5) < 0.5]
    chk("Z-PI-PWR keep-out x546..560 y249..262 z22..31 holds only the C24 head (the 14 x 13 x 9 box fits the BT663 head + 0..1 / 2 spare in y / z)",
        not near_pi, ", ".join(near_pi))
    # C25 (Coms NA977) hub upstream: up-angled A in the LOWER port of the GPIO-edge stack, straight B in the hub -x end face, 250 incl. plugs
    up = P["C-USB-UPSTREAM"].solid
    ub = up.bounding_box()
    g = E.C25
    zall = union([box(*[v + (-EPS if i % 2 == 0 else EPS) for i, v in enumerate(z)]) for z in g["zones"].values()])
    vo = (up - zall).volume()
    chk("C-USB-UPSTREAM (C25) inside its zones %s" % ", ".join("%s %s" % (k, cfmt(v)) for k, v in g["zones"].items()), vo <= TOL,
        "outside %.3f mm3, %s" % (vo, fmt(ub)))
    s2 = P["CU-E-PI5-USBA2"].solid.bounding_box()
    chk("C25 A head in the LOWER port of the GPIO-edge stack (axis z%.1f, stack z%.1f..%.1f) at the port face x%.1f; relief top z%.1f; "
        "upper port would put it at z%.1f, %.2f under the lid (no room for the cable turn)"
        % (g["za"], s2[2], s2[5], g["face"], g["z_top"], g["z_top"] - g["za"] + (s2[5] - 4.0), E.Z_LIDU - (g["z_top"] - g["za"] + (s2[5] - 4.0))),
        abs(g["za"] - (s2[2] + E.PI_USBA_LO_DZ)) < EPS and abs(ub[0] - s2[3]) < EPS and g["z_top"] - g["za"] + (s2[5] - 4.0) + E.UP_D / 2 + 3.0 > E.Z_LIDU - 0.5)
    chk("C25 length %.1f = product 250 incl. connectors (A %.1f + cable %.1f + B %.1f), loop x<=%.2f in front of the seam rail x711"
        % (g["len"], g["a_len"], g["cable"], g["b_len"], ub[3]), abs(g["len"] - E.C25_LEN) < 0.5 and ub[3] <= 711.0 - 2.0)
    tsw = [p for p in onsite if re.match(r"^TS-C-PWR-", p.id)]
    gts = min(up.min_gap(p.solid, 3.0) for p in tsw)
    chk("C25 under the lid: top z%.2f <= lid underside z%.2f - 2, >= 0.5 from the screen power leads TS-C-PWR (%.2f)" % (ub[5], E.Z_LIDU, gts),
        ub[5] <= E.Z_LIDU - 2.0 and gts >= 0.5)
    hb_ = bb(P["PB-E-HUB"])
    bpl = slab(up.trim_by_plane((0, 0, -1), -40.5), 0, E.HUB_X0 - E.C25_B_BODY[0], E.HUB_X0)            # below the hub top: the plug only
    dch = slab(P["C-PWR-5V"].solid.trim_by_plane((0, 0, -1), -40.5), 0, E.HUB_DC[0], E.HUB_X0)
    chk("hub upstream B port and DC jack on the SAME end face (W1 10/1 product photo): -x end x%.1f, B plug y%.0f..%.0f, DC head y%.0f..%.0f, both "
        "within the end face y%.0f..%.0f z%.1f..%.1f and apart" % (E.HUB_X0, bpl[1], bpl[4], dch[1], dch[4], hb_[1], hb_[4], hb_[2], hb_[5]),
        bpl is not None and dch is not None and abs(bpl[3] - E.HUB_X0) < EPS and abs(dch[3] - E.HUB_X0) < EPS and bpl[1] >= hb_[1] - EPS and bpl[4] <= hb_[4] + EPS
        and dch[1] >= hb_[1] - EPS and dch[4] <= hb_[4] + EPS and bpl[2] >= hb_[2] - EPS and bpl[5] <= hb_[5] + EPS and dch[2] >= hb_[2] - EPS
        and dch[5] <= hb_[5] + EPS and (bpl[1] > dch[4] or dch[1] > bpl[4]))
    hdc = P["C-PWR-5V"].solid.trim_by_plane((1, 0, 0), 600.0)
    zdc = union([box(*E.HUB_DC), box(E.HUB_DC[0] - 0.5, E.HUB_DC[1], 281.5, E.HUB_DC[3], E.HUB_DC[5] - EPS, 50.0 + EPS)])
    vo = (hdc.trim_by_plane((1, 0, 0), E.HUB_DC[0] - 0.5) - zdc).volume()
    chk("hub DC right-angle plug head %s on the hub -x end face, lead rises from its top to z48.5 (x>=674)" % cfmt(E.HUB_DC), vo <= TOL,
        "outside %.3f mm3" % vo)
    # what-if: a STRAIGHT DC plug (body D10 on the jack axis, lead bending up R5 right behind it) - longest body that keeps >= 0.5
    sd, sr, sl_ = E.HUB_DC_STRAIGHT
    yj, zj = E.HUB_DC_YZ
    others = [p for p in onsite if p.id not in ("C-PWR-5V", "PB-E-HUB") and boxes_touch(bb(p), (600, 270, 15, 690, 320, 60))]
    best = 0.0
    for L in [20.0 + 0.5 * i for i in range(41)]:
        xe = E.HUB_X0 - L
        tail = E.tube(E.fillet3([(xe, yj, zj), (xe - sr, yj, zj), (xe - sr, yj, 48.5)], [0, sr, 0]), sl_)
        plug = union([cyl_x(yj, zj, xe, E.HUB_X0, sd), tail])
        if all(plug.min_gap(p.solid, 0.6) >= 0.5 for p in others):
            best = L
        else:
            break
    chk("hub DC what-if: a STRAIGHT plug (D%.0f body on the jack axis, lead bent up R%.0f right behind it) fits up to %.1f mm from the jack face to the "
        "end of its moulding / boot (= E.HUB_DC_STRAIGHT_MAX %.0f quoted in the notes / README); longer hits the IH190 gender - then the modelled "
        "right-angle plug" % (sd, sr, best, E.HUB_DC_STRAIGHT_MAX), abs(best - E.HUB_DC_STRAIGHT_MAX) <= 0.5)
    usb = ["O%d-C-USB" % k for k in range(1, 8)] + ["C-USB-PED"]
    zp = CC["Z-HUB-PLUGS"]
    for pid in usb:
        s = slab(P[pid].solid, 1, zp[2], zp[3])
        chk("%s hub-end USB-A plug + boot (y%.0f..%.0f) inside Z-HUB-PLUGS" % (pid, zp[2], zp[3]), s is not None and inside(s, zp), fmt(s))
    zd = CC["Z-HUB-DROPS"]
    for pid in usb:
        s = slab(P[pid].solid.trim_by_plane((0, -1, 0), -zd[3]).trim_by_plane((0, 1, 0), zd[2]), 0, zd[0], zd[1])
        if s is not None:
            chk("%s in x%.0f..%.0f, y<%.0f stays inside Z-HUB-DROPS (z<=%.0f)" % (pid, zd[0], zd[1], zd[3], zd[5]), inside(s, zd), fmt(s))
    part_slab_in("C-USB-PED", 0, CC["Z-PED-LANE"][0] + 25.0, CC["Z-PED-LANE"][1] - 2.0, "Z-PED-LANE")
    for pid in ("C-SPK-L", "C-PWR-20V"):
        part_slab_in(pid, 0, 480.0, 730.0, "Z-SPKLEAD-L")
    part_slab_in("C-SPK-L", 0, CC["Z-SPKLEAD-L2"][0], CC["Z-SPKLEAD-L2"][1] - 3.0, "Z-SPKLEAD-L2", tol=0.6)
    part_slab_in("C-SPK-R", 0, CC["Z-SPKLEAD-R"][0] + 3.0, CC["Z-SPKLEAD-R"][1] - 12.0, "Z-SPKLEAD-R")
    s = slab(P["C-PWR-5V"].solid, 0, E.HUB_X0 + 0.01, 950.0)
    chk("C-PWR-5V ends at the hub -x end face (nothing in front of the shelf / at the +x end any more; spec Z-PWR-LANE / Z-HUB-DC unused)", s is None,
        fmt(s) if s else "")
    # keep-out zones (not modelled plugs / W1 screen / joints) free of electronics
    own = {"Z-DSI": r"^TS-C-DSI$", "Z-GPIO-LEAD": r"^TS-C-PWR-(RED|BLK)$"}           # rev 3: the zone's own cable may (and does) run in it
    for zid, why in (("Z-DSI", "W1 DSI ribbon"), ("Z-GPIO-LEAD", "W1 screen power lead"), ("Z-J702-PLUG", "W702 3.5 mm plug"),
                     ("Z-DONGLE-PLUG", "W701 3.5 mm plug"), ("Z-BANK-PLUG", "power-bank right-angle plug"), ("Z-TS-L1", "thumb screw"),
                     ("Z-TS-L2", "thumb screw"), ("Z-TS-R1", "thumb screw"), ("Z-TS-R2", "thumb screw")):
        zb = box(CC[zid][0], CC[zid][1], CC[zid][2], CC[zid][3], CC[zid][4], CC[zid][5])
        hit = [(p.id, (p.solid ^ zb).volume()) for p in onsite if boxes_touch(bb(p), zb.bounding_box())]
        hit = [h for h in hit if h[1] > TOL]
        mine = [h for h in hit if zid in own and re.match(own[zid], h[0])]
        hit = [h for h in hit if h not in mine]
        chk("keep-out %s (%s) %s free of other electronics%s" % (zid, why, cfmt(CC[zid]), (" - holds %s" % ", ".join("%s %.1f mm3" % h for h in mine)) if zid in own else ""),
            not hit and (zid not in own or bool(mine)), ", ".join("%s %.2f" % h for h in hit))

    # ---- centre space
    cx0, cx1 = E.CU_IX
    for pid in items:
        if pid not in P:
            continue
        b = bb(P[pid])
        io = pid in ("CU-E-PDTRIG", "CU-E-SWITCH", "CU-E-J501BOARD", "CU-E-J501")
        yhi = body.YB if io else E.YBI
        chk("%s inside the centre inner space x%.1f..%.1f y%.0f..%.1f z%.1f..%.2f%s" % (pid, cx0, cx1, E.Y0, yhi, E.Z_BOT, E.Z_LIDU,
                                                                                    " (back-plate I/O)" if io else ""),
            b[0] >= cx0 - EPS and b[3] <= cx1 + EPS and b[1] >= E.Y0 - EPS and b[4] <= yhi + EPS and b[2] >= E.Z_BOT - EPS and b[5] <= E.Z_LIDU + EPS)
    front_items = [pid for pid in items if pid in P and slab(P[pid].solid, 1, E.Y0, E.DUCT_Y[1] - 0.01) is not None
                   and slab(P[pid].solid, 1, E.Y0, E.DUCT_Y[1] - 0.01)[2] < E.DUCT_Z[1]]
    chk("no item in the front zone y214..241 below z27 (spec rule; only cables there)", not front_items, ", ".join(front_items))

    # ---- min gaps between rear-unit electronics (solids)
    related = [("CU-E-PI5", "CU-E-PI5-"), ("CU-E-PI5-USBA1", "CU-E-GENDER"), ("CU-E-GENDER", "CU-E-DONGLE"), ("CU-E-J702BOARD", "CU-E-J702"),
               ("CU-E-J501BOARD", "CU-E-J501"), ("CU-E-PEDBOARD", "CU-E-PEDZERO"), ("C-XT30F-", "C-XT30M-"),
               ("C-PWR-IN", "CU-E-PDTRIG"), ("C-PWR-IN", "CU-E-FUSE"), ("C-PWR-FUSE", "CU-E-FUSE"), ("C-PWR-FUSE", "CU-E-SWITCH"),
               ("C-PWR-20V", "CU-E-SWITCH"), ("C-PWR-20V", "CU-E-BUCK"), ("C-PWR-20V", "CU-E-AMP"), ("C-PWR-5V", "CU-E-BUCK"),
               ("C-PWR-5V", "CU-E-PI5"), ("C-PWR-5V", "PB-E-HUB"), ("C-SPK-L", "CU-E-AMP"), ("C-SPK-R", "CU-E-AMP"), ("C-SPK-L", "C-XT30M-L"),
               ("C-SPK-R", "C-XT30M-R"), ("C-SPKPIG-L", "C-XT30F-L"), ("C-SPKPIG-R", "C-XT30F-R"), ("C-SPKPIG-L", "SPK-L"),
               ("C-SPKPIG-R", "SPK-R"), ("-C-USB", "PB-E-HUB"), ("C-USB-PED", "CU-E-PEDZERO"), ("C-USB-UPSTREAM", "CU-E-PI5-USBA2"),
               ("C-USB-UPSTREAM", "PB-E-HUB"), ("C-XH-", "-C-EXT"), ("C-XH-", "-C-LEAD"), ("C-USB-PED", "PB-E-HUB"),
               ("C-USB-PED", "CU-E-PEDBOARD"), ("O1-C-EXT", "O1-C-USB"), ("O7-C-EXT", "O7-C-USB")]

    def rel(a, b):
        return any((a.startswith(x) or x in a) and (b.startswith(y) or y in b) or (b.startswith(x) or x in b) and (a.startswith(y) or y in a)
                   for x, y in related)
    rear = [p for p in onsite if re.match(r"^(CU-E|PB-E|C-|O\d-C-USB|O\d-C-EXT|EL-C-LEAD|ER-C-LEAD|SPK-)", p.id)]
    tight, gaps_bad = [], []
    for a, b in itertools.combinations(rear, 2):
        if rel(a.id, b.id) or not boxes_touch(bb(a), bb(b), 1.5):
            continue
        g = a.solid.min_gap(b.solid, 1.5)
        cable = a.id.startswith(("C-", "O")) or b.id.startswith(("C-", "O"))
        need = 0.5 if cable else 1.0
        tight.append((g, a.id, b.id))
        if g < need - 1e-6:
            gaps_bad.append("%s / %s %.2f < %.1f" % (a.id, b.id, g, need))
    tight.sort()
    chk("rear-unit electronics: unrelated items >= 1.0 apart, cables >= 0.5 from unrelated parts (solid min gap)", not gaps_bad, "; ".join(gaps_bad[:6]))
    info("tightest electronics gaps", ", ".join("%s/%s %.2f" % (a, b, g) for g, a, b in tight[:8]))
    bt = []
    for a in rear:
        for b_ in B:
            if boxes_touch(bb(a), bb(b_), 0.5):
                g = a.solid.min_gap(b_.solid, 0.5)
                if g < 0.5:
                    bt.append((g, a.id, b_.id))
    bt.sort()
    info("electronics <-> body closer than 0.5 (contacts: plugs on terminals, boards on posts, items on the floor / in pockets)",
         ", ".join("%s/%s %.2f" % (a, b, g) for g, a, b in bt[:14]) + (" (+%d)" % (len(bt) - 14) if len(bt) > 14 else ""))

    # ---- hub
    hb = bb(P["PB-E-HUB"])
    hs = L2["cable_duct"]["hub"]
    chk("PB-E-HUB = cable_duct.hub bbox, on the floor z%.1f, back face %.2f from the back ply y%.1f (spec box drawn for the 43 deg back ply y330)" % (body.Z_BOT, body.YBI - hb[4], body.YBI),
        same(hb, hs["bbox"]) and abs(hb[2] - body.Z_BOT) < EPS and -EPS <= body.YBI - hb[4] <= 1.0 + EPS, fmt(hb))
    chk("hub ports -y at x696.5 + 22 i (spec ports_x)", E.HUB_PORT_X == [696.5 + 22.0 * i for i in range(10)], " ".join("%.1f" % v for v in E.HUB_PORT_X))
    shelf = CC["PR-HUBSHELF"]
    lid_r = next(l for l in L2["centre"]["lids"] if l["id"] == "LID-R")["x"]
    for pid in usb:
        t = pid.split("-")[0] if pid != "C-USB-PED" else "PED"
        xh = hs["ports_x"][hs["port_map"][t]]
        s = slab(P[pid].solid, 1, zp[2] + 0.5, zp[3])
        chk("%s plug in hub port %d (x%.1f), in front of the shelf (y<=%.0f, not under it) and under LID-R x%.0f..%.0f"
            % (pid, hs["port_map"][t], xh, shelf[2], lid_r[0], lid_r[1]),
            s is not None and abs((s[0] + s[3]) / 2 - xh) < 0.05 and s[4] <= shelf[2] + EPS and s[0] >= lid_r[0] and s[3] <= lid_r[1], fmt(s))

    # ---- cables: lengths
    cp = E.cable_plan()
    print("  cable lengths (model = plug 25 + path + hub plug 35):")
    print("    %-6s %-5s %8s %8s %6s %8s %s" % ("cable", "port", "spec", "model", "std", "slack", "route"))
    for t in ["O%d" % k for k in range(1, 8)] + ["PED"]:
        cs = E.CABLE_SPEC[t]
        ln = E.LENGTHS[t]
        std = cs["std_m"] * 1000.0
        print("    %-6s %-5d %8d %8.1f %6.0f %8.1f %s" % (t, cs["hub_port"], cs["path_mm"], ln, std, std - ln, cp["_kind"].get(t, "front zone lane")))
        chk("%s USB-C length %.1f <= standard %.1f m - 40 (spec path %d)" % (t, ln, cs["std_m"], cs["path_mm"]), ln <= std - 40.0)
        if abs(ln - cs["path_mm"]) > 40:
            spec("%s modelled length %.0f differs from the spec estimate %d by more than 40" % (t, ln, cs["path_mm"]))
    info("other leads (path, mm)", ", ".join("%s %.0f" % (k, v) for k, v in E.LENGTHS.items() if not re.match(r"^(O\d|PED)$", k)))
    chk("pod pigtails (XT30U-F tail 150) reach the driver: path <= 140", E.LENGTHS["PIG-L"] <= 140 and E.LENGTHS["PIG-R"] <= 140,
        "L %.0f  R %.0f" % (E.LENGTHS["PIG-L"], E.LENGTHS["PIG-R"]))

    # ---- cables: inside the body envelope (nothing visible from above / behind)
    cav = prism_x(body.CAVITY, body.SX0, body.SX1)
    allowed = [box(body.SPK_X["L"][0] + 3.0, body.SPK_X["R"][1] - 3.0, E.DUCT_Y[0], E.DUCT_Y[1], E.DUCT_Z[0], E.DUCT_Z[1]),
               box(cx0, cx1, E.Y0, E.DUCT_Y[1], 0.0, E.Z_LIDU), box(cx0, cx1, E.DUCT_Y[1], E.YBI, E.Z_BOT, E.Z_LIDU),
               box(body.BP_X[0], body.BP_X[1], E.YBI, body.YB, E.Z_BOT, E.Z_LIDU), cav, body.mx(cav)]
    for side in "LR":
        wy, wz = body.WIRE_YZ[side]
        ey, ez = body.END_HOLE_YZ[side]
        pf = body.SPK_X["L"][1] if side == "L" else body.SPK_X["R"][0]          # pod joint face 257 / 965
        xa, xb = (body.SPK_IX["L"][1], pf) if side == "L" else (pf, body.SPK_IX["R"][0])
        allowed.append(cyl_x(wy, wz, xa, xb, body.WIRE_D))                         # sealed pod hole D6
        ga, gb = (pf, cx0) if side == "L" else (cx1, pf)
        allowed.append(box(ga, gb, wy - body.END_HOLE_D / 2, wy + body.END_HOLE_D / 2, min(wz, ez) - body.END_HOLE_D / 2,
                           max(wz, ez) + body.END_HOLE_D / 2))                     # 3 mm joint gap between the two holes
        ta, tb = (body.CU_X[0], cx0) if side == "L" else (cx1, body.CU_X[1])
        allowed.append(cyl_x(ey, ez, ta, tb, body.END_HOLE_D))                     # end-wall tunnel D14 (slack coil)
    for k in range(1, 8):
        X0 = 47.0 + 164.5 * (k - 1)
        allowed.append(box(X0 + 77.75, X0 + 90.25, 196.8, 212.01, 10.7, 18.3))
    ALLOWED = union(allowed)
    cab = [p for p in onsite if re.match(r"^(C-|O\d-C-USB|O\d-C-EXT|EL-C-LEAD|ER-C-LEAD|CU-E-|PB-E-)", p.id)]
    outside = []
    for p in cab:
        m = p.solid
        if re.match(r"^(O\d-C-EXT|EL-C-LEAD|ER-C-LEAD)$", p.id):
            m = m.trim_by_plane((0, 1, 0), E.DUCT_Y[0])
        v = (m - ALLOWED).volume()
        if v > TOL:
            outside.append("%s %.2f at %s" % (p.id, v, fmt((m - ALLOWED).bounding_box())))
    chk("every rear-unit cable / item inside the body envelope: duct y212..241 z0..27 (x-13..1235 between the caps), centre unit "
        "(front zone, floor zone, back-plate window), end-wall / pod-panel holes, pod cavities (%d parts)" % len(cab), not outside, "; ".join(outside[:5]))
    gap_parts = [(p.id, s[5]) for p in onsite for s in [slab(p.solid, 1, 212.0, 214.0)] if s is not None and not re.match(r"^(O\d|EL|ER)-", p.id)]
    zmax_gap = max([s[5] for p in onsite for s in [slab(p.solid, 1, 212.01, 213.99)] if s is not None] or [0.0])
    chk("2 mm air gap y212..214: only module plugs / leads, top z%.1f <= 18.3 (%.1f below the key top z72.85 - only a glimpse from above)"
        % (zmax_gap, 72.85 - zmax_gap), zmax_gap <= 18.3 + EPS and not gap_parts, ", ".join("%s %.1f" % g for g in gap_parts))
    duct_pod = [p.id for p in cab for x0_, x1_ in ((body.SPK_X["L"][0], body.SPK_X["L"][1]), (body.SPK_X["R"][0], body.SPK_X["R"][1]))
                for s in [slab(p.solid.trim_by_plane((0, -1, 0), -E.DUCT_Y[1]), 0, x0_, x1_)] if s is not None and s[5] > E.DUCT_Z[1] + EPS
                and not p.id.startswith("C-SPKPIG")]
    chk("under the pods every cable stays under the duct roof z27", not duct_pod, ", ".join(duct_pod))

    # module USB cable bundle: one cable per level wherever they run side by side
    lv = E.LEVEL_Z
    runs = {t: sorted((E.module_plug_x(int(t[1])), E.HUB_PORT_X[E.HUB_PORT[t]])) for t in lv}
    clash_lv = [(a, b) for a, b in itertools.combinations(lv, 2) if lv[a] == lv[b] and not (runs[a][1] + 25 < runs[b][0] or runs[b][1] + 25 < runs[a][0])]
    chk("bundle y%.1f: cables sharing a level never run side by side (%s)" % (E.BUNDLE_Y, ", ".join("%s z%.2f" % kv for kv in sorted(lv.items(), key=lambda kv: kv[1]))),
        not clash_lv, str(clash_lv))
    top_ok = []
    for t in lv:
        xp = E.HUB_PORT_X[E.HUB_PORT[t]]
        others = [u for u in lv if u != t and runs[u][0] - 1 <= xp <= runs[u][1] + 1]
        top_ok.append(all(lv[u] < lv[t] for u in others))
    chk("each bundle cable leaves upward at its port x on top of the cables still running there", all(top_ok))

    # ---- drivers
    n = np.array(body.SPK_N)
    u = np.array(body.SPK_U)
    Rj = load("electronics_rearbar.json")
    loc, dinfo = E.speaker_local(Rj)
    pods = {s: [p for p in B if re.match(r"^SPK%s-(PLY-|BAFFLE|DUCTFORMER)" % s, p.id)] for s in "LR"}
    G = body.PodGeom(body.ANGLE)                                    # l2_geom rules at the built angle (references below)
    g_back = body.YBI - G.D(42.5, -54.0)[0]                         # magnet back rim corner -> back ply inner face
    g_mc = G.D(0.0, -45.5)
    sel_ang = L2.get("selected_angle", L2["speakers"]["baffle"]["angle_from_horizontal_deg"])
    w1_acc = L2.get("angle_decision", {}).get("w1_flange_corner_accepted_mm") if abs(sel_ang - body.ANGLE) < 1e-9 else None
    for side in "LR":
        pid = "SPK-" + side
        C = np.array(body.DRIVER_POSE[side])
        m = P[pid].solid
        from cadlib import mesh_arrays
        v, _f = mesh_arrays(m)
        rel_ = v - C
        w = rel_ @ n
        s_ = rel_ @ u
        a_ = rel_[:, 0]
        chk("%s centre = body.DRIVER_POSE x%.1f y%.2f z%.2f, axis (0, %.4f, %.4f) = %.0f deg from vertical (ANGLE %.1f)"
            % (pid, C[0], C[1], C[2], n[1], n[2], 90 - body.ANGLE, body.ANGLE),
            abs(a_.max() - 52.5) < 0.05 and abs(a_.min() + 52.5) < 0.05 and abs(s_.max() - 52.5) < 0.05 and abs(s_.min() + 52.5) < 0.05,
            "a %.2f..%.2f s %.2f..%.2f" % (a_.min(), a_.max(), s_.min(), s_.max()))
        chk("%s along the axis: flange front w+7 (gasket 3 + flange 4), magnet back w-54 (depth 61)" % pid,
            abs(w.max() - 7.0) < 0.02 and abs(w.min() + 54.0) < 0.02, "w %.3f..%.3f" % (w.min(), w.max()))
        cn = float(C @ n)
        mag = m.trim_by_plane(tuple(-n), -cn + 37.0)                         # w <= -37
        gaps = {p.id: mag.min_gap(p.solid, 20.0) for p in pods[side]}
        gmin = min(gaps.items(), key=lambda kv: kv[1])
        chk("%s magnet D85 >= 2.0 from every pod wall (closest %s %.2f)" % (pid, gmin[0], gmin[1]), gmin[1] >= 2.0)
        back = gaps["SPK%s-PLY-BACK" % side]
        chk("%s magnet back rim -> back ply %.2f (rules %.2f at %.0f deg, target 3.5)" % (pid, back, g_back, body.ANGLE), back >= 3.5 - 0.02 and abs(back - g_back) < 0.05)
        bsk = m.trim_by_plane(tuple(n), cn - 37.0).trim_by_plane(tuple(-n), -cn)   # -37 <= w <= 0
        gs = bsk.min_gap(Bb["SPK%s-DUCTFORMER" % side].solid, 20.0)
        chk("%s basket D94 -> front-wall sill (duct former) %.2f >= 2.0 (spec %.2f at %.0f deg)" % (
            pid, gs, L2["speakers"]["driver_clearances_mm"]["basket_D94_generators"]["front-wall sill rear face (y225)"], sel_ang), gs >= 2.0)
        podu = union([p.solid for p in pods[side]])
        o = C - 54.01 * n
        hits_ = podu.ray_cast(tuple(o), tuple(o - 150.0 * n))
        free = min(h.distance for h in hits_) * 150.0 if hits_ else 150.0
        vent = cyl_z(0, 0, 0, 10.0, 10.0).transform(np.array([[1.0, u[0], -n[0], o[0]], [0.0, u[1], -n[1], o[1]], [0.0, u[2], -n[2], o[2]]]))
        vv = sum((vent ^ p.solid).volume() for p in B if boxes_touch(bb(p), vent.bounding_box()))
        chk("%s pole vent (W1): %.1f mm free along the axis behind the magnet (>= 10), a D10 x 10 vent core cuts no body part" % (pid, free),
            free >= 10.0 and vv <= TOL, "overlap %.3f" % vv)
        c0 = C + 0.01 * n
        hits2 = podu.ray_cast(tuple(c0), tuple(c0 - 200.0 * n))
        depth = min(h.distance for h in hits2) * 200.0 - 0.01 if hits2 else 0.0
        chk("%s inside depth along the normal from the outer face %.1f >= 72 (spec %.1f at %.0f deg)" % (
            pid, depth, L2["speakers"]["driver_clearances_mm"]["inside_depth_along_normal_from_outer_face"], sel_ang), depth >= 72.0)
        mc = C + (dinfo["magnet_w"][0] + dinfo["magnet_w"][1]) / 2.0 * n
        dmc = math.hypot(mc[1] - body.SENSOR_YZ[0], mc[2] - body.SENSOR_YZ[1])
        dv = np.hypot(v[:, 1] - body.SENSOR_YZ[0], v[:, 2] - body.SENSOR_YZ[1])
        i = int(np.argmin(dv))
        chk("%s D14: magnet centre (y%.2f z%.2f) %.1f from the hall elements (y%.0f z%.1f) >= 100 (rules %.1f to z8)" % (pid, mc[1], mc[2], dmc,
            body.SENSOR_YZ[0], body.SENSOR_YZ[1], math.hypot(g_mc[0] - 67.0, g_mc[1] - 8.0)), dmc >= 100.0)
        chk("%s D14: nearest steel point (y%.2f z%.2f) %.1f from the hall elements >= 100 (spec %.1f to z8 at %.0f deg)" % (
            pid, v[i, 1], v[i, 2], dv[i], L2["speakers"]["d14"]["nearest_steel_point_mm"], sel_ang), dv[i] >= 100.0)
        # 27 deg sound path (spec speakers.sightline: from D(-47, 0) toward the player, vertical clearances)
        q = np.array(body.D(-47.0, 0.0))
        tan27 = math.tan(math.radians(27.0))

        def under(solid, s_max, x_half):
            """smallest vertical distance under the path of the solid's points with s <= s_max (within x_half of the axis)."""
            vv_, _ = mesh_arrays(solid.trim_by_plane((1, 0, 0), C[0] - x_half).trim_by_plane((-1, 0, 0), -(C[0] + x_half)))
            r_ = vv_ - C
            sel = (r_ @ u) <= s_max + 1e-6
            if not sel.any():
                return None
            yz = vv_[sel][:, 1:]
            zl = q[1] + (q[0] - yz[:, 0]) * tan27
            return float(np.min(zl - yz[:, 1]))
        cf = under(m, -52.49, 47.0)
        cg = under(Bb["SPK%s-GASKET" % side].solid, -52.49, 47.0)
        r_fl = G.sightline_clear(G.D(-52.5, 7.0))
        fl_min = 3.0 if r_fl >= 3.0 else (w1_acc - 0.02 if w1_acc else 3.0)   # W1 strict 3.0; at the selected angle W1 accepted its corner value
        chk("%s 27 deg path: flange lower corner D(-52.5, 7) %.2f under it (>= %.2f; rules %.2f at %.0f deg%s)" % (
            pid, cf, fl_min, r_fl, body.ANGLE, ", W1 accepted %.2f" % w1_acc if w1_acc and r_fl < 3.0 else ""), cf is not None and cf >= fl_min)
        if cf is not None and cf < 3.0:
            spec("%s flange corner %.2f under the 27 deg path at ANGLE %.1f < W1 strict 3.0 (%s)" % (
                pid, cf, body.ANGLE, "W1 accepted %.2f, spec angle_decision" % w1_acc if w1_acc else "pareto_by_angle: needs W1's acceptance"))
        chk("%s 27 deg path: EVA gasket lower corner D(-52.5, 3) %.2f under it (>= 3.0, rules %.2f)" % (pid, cg, G.sightline_clear(G.D(-52.5, 3.0))),
            cg is not None and cg >= 3.0)
        gr = Bb["SPK%s-GRILLE" % side].solid
        gv, _ = mesh_arrays(gr.trim_by_plane((1, 0, 0), C[0] - 47.0).trim_by_plane((-1, 0, 0), -(C[0] + 47.0)))
        rg = gv - C
        sel = (rg @ u) <= -49.99
        above = float(np.min(gv[sel][:, 2] - (q[1] + (q[0] - gv[sel][:, 1]) * tan27))) if sel.any() else None
        info("%s 27 deg path passes under the grille plate's lower edge D(-50, 11): %.2f vertical = %.2f perpendicular (rules %.2f; 0.94 at 43 deg - "
             "perforated plate, no lower ring wall: W1 approved exception)" % (pid, above, above * math.cos(math.radians(27.0)), G.perp_clear(G.D(-50.0, 11.0))))
        mod = q[1] + (q[0] - 212.0) * tan27 - 72.85
        chk("%s 27 deg path over the module rear top edge (y212, z72.85): %.3f >= 3.0 (rules %.3f, key action)" % (pid, mod, G.sightline_clear((212.0, 72.85))),
            mod >= 3.0 and abs(mod - G.sightline_clear((212.0, 72.85))) < 1e-6)
        info("%s magnet gaps to the pod walls: %s" % (pid, ", ".join("%s %.2f" % (k.split("-", 1)[1], g) for k, g in sorted(gaps.items(), key=lambda kv: kv[1]))))

    # ---- XT30 pairs, pigtails, speaker leads, power harness
    pockets, psrc = E.xt30_pockets()
    for side in "LR":
        x0, x1, y0, y1, z0, z1 = pockets[side]
        fb = bb(P["C-XT30F-" + side])
        chk("C-XT30F-%s inside the %s clip pocket x%.1f..%.1f y%.1f..%.1f z%.1f..%.1f, mouth at the pocket end toward the centre"
            % (side, psrc, x0, x1, y0, y1, z0, z1),
            inside(fb, (x0, x1, y0, y1, z0, z1)) and (abs(fb[3] - x1) < EPS if side == "L" else abs(fb[0] - x0) < EPS), fmt(fb))
        mb = bb(P["C-XT30M-" + side])
        chk("C-XT30M-%s mated from the centre side, pair inside the spec C-XT30-%s box %s (male tail 0.1 past: body pocket + 8.1)" % (side, side, cfmt(CC["C-XT30-" + side])),
            (abs(mb[0] - fb[3]) < EPS if side == "L" else abs(mb[3] - fb[0]) < EPS) and inside(mb, CC["C-XT30-" + side], 0.15) and inside(fb, CC["C-XT30-" + side]), fmt(mb))
        pg = P["C-SPKPIG-" + side].solid
        wy, wz = body.WIRE_YZ[side]
        xa, xb = (body.SPK_IX["L"][1], body.SPK_X["L"][1]) if side == "L" else (body.SPK_X["R"][0], body.SPK_IX["R"][0])
        s = slab(pg, 0, xa, xb)
        hole_ok = s is not None and max(abs(s[1] - wy), abs(s[4] - wy), abs(s[2] - wz), abs(s[5] - wz)) <= body.WIRE_D / 2
        chk("C-SPKPIG-%s passes the sealed D%.0f pod side-panel hole (y%.0f z%.0f) x%.1f..%.1f" % (side, body.WIRE_D, wy, wz, xa, xb), hole_ok, fmt(s) if s else "")
        ea, eb = (body.CU_X[0], cx0) if side == "L" else (cx1, body.CU_X[1])
        ey, ez = body.END_HOLE_YZ[side]
        s = slab(pg, 0, ea, eb)
        inhole = (pg ^ box(ea, eb, 0, 400, 0, 200)) - cyl_x(ey, ez, ea - 1, eb + 1, body.END_HOLE_D)
        chk("C-SPKPIG-%s passes the D%.0f end-wall hole (y%.0f z%.1f) x%.1f..%.1f with its slack coil inside the hole" % (side, body.END_HOLE_D, ey, ez, ea, eb),
            s is not None and inhole.volume() <= TOL, fmt(s) if s else "")
        chk("C-SPKPIG-%s: %.1f mm of tail outside the pod (>= 45: the pod lifts 10 and slides 15 outboard with the XT30U-F still in its clip)"
            % (side, E.LENGTHS["PIG-OUT-" + side]), E.LENGTHS["PIG-OUT-" + side] >= 45.0)
        cavm = cav if side == "L" else body.mx(cav)
        inpod = pg.trim_by_plane((-1, 0, 0), -xa) if side == "L" else pg.trim_by_plane((1, 0, 0), xb)
        chk("C-SPKPIG-%s: the part inside the pod stays in the sealed cavity and ends at the driver" % side,
            (inpod - cavm).volume() <= TOL and pg.min_gap(P["SPK-" + side].solid, 1.0) <= 0.1, "outside %.3f" % (inpod - cavm).volume())
    ends = [("C-PWR-IN", "CU-E-PDTRIG"), ("C-PWR-IN", "CU-E-FUSE"), ("C-PWR-FUSE", "CU-E-FUSE"), ("C-PWR-FUSE", "CU-E-SWITCH"),
            ("C-PWR-20V", "CU-E-SWITCH"), ("C-PWR-20V", "CU-E-BUCK"), ("C-PWR-20V", "CU-E-AMP"), ("C-PWR-5V", "CU-E-BUCK"),
            ("C-PWR-5V", "PB-E-HUB"), ("C-PWR-5V", "CU-E-PI5"), ("C-SPK-L", "CU-E-AMP"), ("C-SPK-L", "C-XT30M-L"), ("C-SPK-R", "CU-E-AMP"),
            ("C-SPK-R", "C-XT30M-R"), ("C-SPKPIG-L", "C-XT30F-L"), ("C-SPKPIG-R", "C-XT30F-R"), ("C-USB-PED", "CU-E-PEDZERO"),
            ("C-USB-PED", "PB-E-HUB"), ("C-USB-UPSTREAM", "CU-E-PI5-USBA2"), ("C-USB-UPSTREAM", "PB-E-HUB")] + \
           [("O%d-C-USB" % k, "O%d-E-ZERO" % k) for k in range(1, 8)] + [("O%d-C-USB" % k, "PB-E-HUB") for k in range(1, 8)]
    bad_end = []
    for a, b in ends:
        g = P[a].solid.min_gap(P[b].solid, 1.0)
        if g > 0.1:
            bad_end.append("%s/%s %.2f" % (a, b, g))
    chk("every cable ends on its terminal / plug face (gap <= 0.1): %d ends" % len(ends), not bad_end, "; ".join(bad_end))
    # pigtail numbers quoted in the XT30 clip notes (body.PIG_SLACK_MM / PIG_OUT_MM) = the modelled path
    sl_ = [E.LENGTHS["PIG-SLACK-" + s_] for s_ in "LR"]
    po_ = [E.LENGTHS["PIG-OUT-" + s_] for s_ in "LR"]
    notes_ok = all(("여유 약 %.0f mm" % body.PIG_SLACK_MM) in Bb["XT30-CLIP-" + s_].note and ("스피커 밖 꼬리 약 %.0f mm" % body.PIG_OUT_MM) in Bb["XT30-CLIP-" + s_].note
                   for s_ in "LR")
    chk("XT30 clip notes quote the pigtail as modelled: coil slack %.1f / %.1f ~ %.0f, outside the pod %.1f / %.1f ~ %.0f (within 2.5)"
        % (sl_[0], sl_[1], body.PIG_SLACK_MM, po_[0], po_[1], body.PIG_OUT_MM),
        notes_ok and all(abs(v - body.PIG_SLACK_MM) <= 2.5 for v in sl_) and all(abs(v - body.PIG_OUT_MM) <= 2.5 for v in po_))
    # power bank (optional, velcro): >= 1.5 from the speaker lead C-SPK-L and lifts straight out of its holder
    bank = P["PB-E-BANK"].solid
    gb = bank.min_gap(P["C-SPK-L"].solid, 5.0)
    near = sorted(((bank.min_gap(p.solid, 5.0), p.id) for p in onsite if p.id != "PB-E-BANK" and boxes_touch(bb(p), bb(P["PB-E-BANK"]), 5.0)))
    chk("PB-E-BANK <-> C-SPK-L %.2f >= 1.5 (the lead crosses in front of the bank, not over its corner)" % gb, gb >= 1.5,
        "closest: " + ", ".join("%s %.2f" % (i, g) for g, i in near[:4]))
    lids = r"^(LID-|CU-SCREENLID$|CU-MAG-LID-|CU-M3X10-)"
    lift_hit = []
    for dz in (1.0, 5.0, 10.0, 20.0, 30.0, 40.0):
        m_ = bank.translate((0, 0, dz))
        for p in [q for q in onsite if q.id != "PB-E-BANK"] + [q for q in B if not re.match(lids, q.id)]:
            if boxes_touch(bb(p), m_.bounding_box()) and (p.solid ^ m_).volume() > TOL:
                lift_hit.append("%s at +%.0f" % (p.id, dz))
    chk("PB-E-BANK lifts 40 mm straight out of its holder (lids off, plug out) without touching a cable, item or body part",
        not lift_hit, ", ".join(sorted(set(lift_hit))[:6]))

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
        chk("O%d-E-MB at local x47.25..117.25 (module electronics unchanged)" % k, abs(b[0] - X0 - 47.25) < EPS and abs(b[3] - X0 - 117.25) < EPS, fmt(b))
    keyside = [p.id for p in onsite if bb(p)[4] < 212.0 + EPS and not re.match(r"^(O\d|EL|ER)-", p.id)]
    chk("only module / end-part electronics live in y<212", not keyside, ", ".join(keyside) or "none")
    allb = [p for p in K + Ep + B if p.note != "offdesk"]
    ob = [min(bb(p)[i] for p in allb) for i in range(3)] + [max(bb(p)[i] for p in allb) for i in range(3, 6)]
    info("overall (key action + electronics + body, off-desk pedal excluded) %.2f x %.2f x %.2f" % (ob[3] - ob[0], ob[4] - ob[1], ob[5] - ob[2]), fmt(ob))
    eb = [min(bb(p)[i] for p in onsite) for i in range(3)] + [max(bb(p)[i] for p in onsite) for i in range(3, 6)]
    chk("electronics inside the plan rectangle x-16..1238 y0..%.1f and above the desk" % body.YB,
        eb[0] >= -16 - EPS and eb[3] <= 1238 + EPS and eb[1] >= -EPS and eb[4] <= body.YB + EPS and eb[2] >= -EPS, fmt(eb))

    # ------------------------------------------------------------------ (4) R31 touchscreen rev 3
    print("=" * 110)
    print("(4) R31 touchscreen rev 3 (touchscreen/rev3/design/CAD_SPEC_rev3.md C, F, G + numbers.json)")
    NP = TS.POINTS
    R31E = {}
    scr = P["TS-E-SCREEN"]
    sb = bb(scr)
    gb, gt = TS.pt(0.0, 0.0), TS.pt(TS.GLASS[1], 0.0)
    ac = TS.pt(sum(TS.SC["active_u"]) / 2.0, 0.0)
    chk("TS-E-SCREEN 25 deg: glass x%.2f~%.2f, bottom edge (y%.2f z%.2f) = front-most, top edge (y%.2f z%.2f) = highest, active centre (y%.2f z%.2f) "
        "(numbers points.use)" % (TS.SC["glass_x"][0], TS.SC["glass_x"][1], gb[0], gb[1], gt[0], gt[1], ac[0], ac[1]),
        abs(sb[0] - TS.SC["glass_x"][0]) < EPS and abs(sb[3] - TS.SC["glass_x"][1]) < EPS and abs(sb[1] - NP["use"]["glass_bottom"][0]) < EPS
        and abs(sb[5] - NP["use"]["glass_top"][1]) < EPS and math.dist(gb, NP["use"]["glass_bottom"]) < EPS and math.dist(gt, NP["use"]["glass_top"]) < EPS
        and math.dist(ac, NP["use"]["act_centre"]) < EPS, fmt(sb))
    fs = slab(P["TS-E-SCREEN-FOLD"].solid, 2, NP["fold"]["glass_bottom"][1] - 0.3, NP["fold"]["glass_bottom"][1])
    chk("TS-E-SCREEN-FOLD altview: glass face up at z%.2f, y%.2f~%.2f (numbers points.fold)" % (NP["fold"]["glass_bottom"][1], NP["fold"]["glass_bottom"][0],
        NP["fold"]["glass_top"][0]), P["TS-E-SCREEN-FOLD"].note == "altview" and fs is not None and abs(fs[1] - NP["fold"]["glass_bottom"][0]) < EPS
        and abs(fs[4] - NP["fold"]["glass_top"][0]) < EPS and abs(bb(P["TS-E-SCREEN-FOLD"])[5] - NP["fold"]["glass_bottom"][1]) < EPS, fmt(fs) if fs else "")
    import body as _bd
    crl = _bd.cradle_local()
    scl = E.screen_local()
    side = scl.min_gap(crl ^ box(TS.WALLS["side_inner_xr"] - 0.01, 90, 1.0, 100.0, -2, TS.BOSS["face_w"] - 0.1), 1.0)
    top = scl.min_gap(crl ^ box(-90, 90, TS.WALLS["top_u"][0] - 0.01, 104, -2, 9), 1.0)
    tabg = (scl ^ box(TS.NOTCH["feature_xr"][0] - 0.1, TS.NOTCH["feature_xr"][1] + 0.1, -2, 0.0, -2, 9)).min_gap(crl, 3.0)
    chk("C-1/C-3 display in the cradle: no overlap; glass bottom on the bottom wall u0 and back on the 4 bosses w8 (shift 0.05 overlaps); side gap %.2f "
        "(0.3), top gap %.2f (0.5); bottom-edge feature in the notch %.2f clear (W1 2.0, margins x %.2f / %.2f)"
        % (side, top, tabg, TS.NOTCH["feature_xr"][0] - TS.NOTCH["xr"][0], TS.NOTCH["xr"][1] - TS.NOTCH["feature_xr"][1]),
        (scl ^ crl).volume() <= TOL and (scl.translate((0, -0.05, 0)) ^ crl).volume() > 0.05 and (scl.translate((0, 0, 0.05)) ^ crl).volume() > 0.05
        and abs(side - TS.WALLS["side_gap"]) < 0.01 and abs(top - TS.WALLS["top_gap"]) < 0.01 and tabg >= 1.9)
    rib = P["TS-C-DSI"].solid
    RB = TS.RIBBON
    hx0, hx1, hy0, hy1 = TS.HOLE["x"][0], TS.HOLE["x"][1], TS.HOLE["y"][0], TS.HOLE["y"][1]
    hs = slab(rib, 2, TS.LID_BED + 0.05, TS.LID_TOP - 0.05)
    chk("TS-C-DSI through the lid hole x%.2f~%.2f y%.2f~%.2f (lid z%.2f~%.2f)" % (hx0, hx1, hy0, hy1, TS.LID_BED, TS.LID_TOP),
        hs is not None and inside(hs, (hx0, hx1, hy0, hy1, TS.LID_BED, TS.LID_TOP)), fmt(hs) if hs else "")
    cp = TS.CLIP["pad"]
    cs = slab(rib.trim_by_plane((0, 0, -1), -62.0), 1, cp["y"][0] + 0.05, cp["y"][1] - 0.05)
    chk("TS-C-DSI clamped under the clip pad: z%.2f~%.2f (clip top z%.2f, pad bottom z%.2f), x%.2f~%.2f" % (TS.CLIP["clamp_z"][0], TS.CLIP["clamp_z"][1],
        TS.CLIP["clip_z"][1], cp["z"][0], TS.CLIP["ribbon_edge_x"] - RB["ffc_w"], TS.CLIP["ribbon_edge_x"]),
        cs is not None and abs(cs[2] - TS.CLIP["clamp_z"][0]) < EPS and abs(cs[5] - TS.CLIP["clamp_z"][1]) < EPS and abs(cs[3] - TS.CLIP["ribbon_edge_x"]) < EPS
        and abs(cs[0] - (TS.CLIP["ribbon_edge_x"] - RB["ffc_w"])) < EPS, fmt(cs) if cs else "")
    wp = RB["waypoints"]
    ds = slab(rib, 2, 31.0, 57.5)                                       # the straight column between the two R3 bends
    chk("TS-C-DSI drop column x%.0f (= mouth x%.0f - stiffener 3 - R3) inside Z-DSI %s, width along y%.2f~%.2f" % (wp[3][0], wp[-1][0], cfmt(CC["Z-DSI"]),
        wp[3][1] - RB["ffc_w"] / 2, wp[3][1] + RB["ffc_w"] / 2),
        ds is not None and inside(ds, CC["Z-DSI"]) and abs((ds[0] + ds[3]) / 2 - wp[3][0]) < EPS, fmt(ds) if ds else "")
    d1 = P["CU-E-PI5-DISP1"].solid
    ins_ = (rib ^ d1).bounding_box()
    chk("TS-C-DSI Pi end: into CAM/DISP 1 at the mouth x%.0f (mouth -x) by %.1f (connector depth 3 - 0.3), centre z%.1f" % (wp[-1][0], RB["pi_end_insert"], wp[-1][2]),
        abs(ins_[0] - wp[-1][0]) < EPS and abs(ins_[3] - (wp[-1][0] + RB["pi_end_insert"])) < EPS
        and abs((ins_[2] + ins_[5]) / 2 - wp[-1][2]) < 0.05, fmt(ins_))
    pi = P["CU-E-PI5"].solid
    hd = TS.PI5["hdmi"]
    hdmi_box = box(E.PI_HDMI_XC[1] - E.PI_HDMI_W / 2, E.PI_HDMI_XC[1] + E.PI_HDMI_W / 2, hd["y"][0], hd["y"][1], 24.1, hd["top_z"])
    g_hdmi = rib.min_gap(hdmi_box, 2.0)
    pib = CC["CU-E-PI5"]
    hs_cad = box(pib[0] + 21.5, pib[0] + 36.5, pib[2] + 17.5, pib[2] + 32.5, 24.1, 32.1)          # the CAD Pi model's SoC heatsink (electronics.pi_parts)
    hsw = TS.PI5["heatsink"]
    hs_w1 = box(hsw["x"][0], hsw["x"][1], hsw["y"][0], hsw["y"][1], 24.1, hsw["top_z"])
    g_cad = rib.min_gap(hs_cad, 20.0)
    g_w1 = rib.min_gap(hs_w1, 20.0)
    o_w1 = (rib ^ hs_w1).volume()
    R31E["heatsink_gap_cad"], R31E["heatsink_gap_w1box"], R31E["heatsink_overlap_w1box"], R31E["hdmi_gap"] = g_cad, g_w1, o_w1, g_hdmi
    chk("TS-C-DSI vs the Pi heatsink on the L2 Pi pose (CAD Pi model: SoC heatsink x%.1f~%.1f y%.1f~%.1f): gap %.2f >= 0.5; on W1's estimated heatsink box "
        "x%.0f~%.0f y%.0f~%.0f the ribbon would touch it (gap %.2f, overlap %.2f mm3; spec G-8 estimate y -0.35 / x -0.15)"
        % (pib[0] + 21.5, pib[0] + 36.5, pib[2] + 17.5, pib[2] + 32.5, g_cad, hsw["x"][0], hsw["x"][1], hsw["y"][0], hsw["y"][1], g_w1, o_w1), g_cad >= 0.5)
    chk("TS-C-DSI rests on the unused micro-HDMI 1 (estimated top z%.1f): gap %.2f, no overlap with the Pi" % (hd["top_z"], g_hdmi),
        g_hdmi <= 0.1 and (rib ^ pi).volume() <= TOL)
    L_m, L_r = E.LENGTHS["DSI"], E.LENGTHS["DSI_WITH_LID_ROLL"]
    chk("TS-C-DSI developed length %.1f (+ lid fold roll %.2f = %.1f) vs W1 %.2f (diff %.1f) and the 300 mm cable (margin %.1f >= 30; spec G-5: measure with a 12 mm paper strip)"
        % (L_m, RB["parts"]["fold_roll_allowance"], L_r, RB["total"], L_r - RB["total"], RB["cable"] - L_r), RB["cable"] - L_r >= 30.0 and abs(L_r - RB["total"]) < 5.0)
    rb_ = bb(P["TS-C-DSI"])
    lp = [np.array(q) for q in E.ffc_path()["loop"]]
    chord = float(np.linalg.norm(lp[-1] - lp[0]))
    info("TS-C-DSI hinge loop: length %.2f (spec %.2f), chord %.2f from the cradle groove (w8.15) to the lid hole top (spec %.2f from its groove exit point), "
         "front-most y%.2f" % (E.ffc_path()["loop_len"], RB["loop"]["length"], chord, RB["loop"]["chord"]["use"], float(min(q[1] for q in lp))))
    chk("TS-C-DSI forward-most y%.2f >= keep-out y%.0f + 1 (numbers cables_fwd_min_y %.2f est.)" % (rb_[1], TS.KEEP_Y, TS.CHECKS["cables_fwd_min_y"]), rb_[1] >= TS.KEEP_Y + 1.0)
    cov_u = Bb["TS-WINCOVER"].solid
    hp = TS.place(box(TS.HOLD_PAD["xr"][0], TS.HOLD_PAD["xr"][1], TS.HOLD_PAD["u"][0], TS.HOLD_PAD["u"][1], TS.HOLD_PAD["w"][0], TS.HOLD_PAD["w"][1]))
    chk("TS-C-DSI in the cradle: under the hold pad gap %.2f (= 0.3), clear of the cradle / window cover / clip / lid (no overlap)" % rib.min_gap(hp, 1.0),
        abs(rib.min_gap(hp, 1.0) - 0.3) < 0.02 and all((rib ^ Bb[i].solid).volume() <= TOL for i in ("TS-CRADLE", "TS-WINCOVER", "TS-RCLIP", "CU-SCREENLID"))
        and (rib ^ cov_u).volume() <= TOL)
    pw = TS.PWIRE
    for tag, pin in (("RED", "gpio_pin2"), ("BLK", "gpio_pin6")):
        w_ = P["TS-C-PWR-" + tag].solid
        s_h = slab(w_, 2, TS.LID_BED + 0.05, TS.LID_TOP - 0.05)
        s_c = slab(w_.trim_by_plane((0, 0, -1), -62.0), 1, cp["y"][0] + 0.05, cp["y"][1] - 0.05)
        gv = TS.CLIP["wire_groove"]
        g = TS.PI5[pin]
        hb = slab(w_, 2, TS.PI5["gpio_top_z"] - 6.0, TS.PI5["gpio_top_z"])
        chk("TS-C-PWR-%s: through the lid hole beside the ribbon (x>=%.2f), in the clip groove x%.1f~%.1f above its floor z%.2f, F housing on GPIO pin %s (%.2f, %.2f)"
            % (tag, TS.CLIP["ribbon_edge_x"] + 0.5, gv["x"][0], gv["x"][1], TS.CLIP["clip_z"][1] - gv["depth"], pin[-1], g[0], g[1]),
            s_h is not None and inside(s_h, (TS.CLIP["ribbon_edge_x"] + 0.5, hx1, hy0, hy1, TS.LID_BED, TS.LID_TOP)) and s_c is not None
            and inside(s_c, (gv["x"][0], gv["x"][1], cp["y"][0], cp["y"][1], TS.CLIP["clip_z"][1] - gv["depth"], cp["z"][0])) and hb is not None
            and abs((hb[0] + hb[3]) / 2 - g[0]) < EPS and abs((hb[1] + hb[4]) / 2 - g[1]) < EPS,
            "hole %s / clip %s" % (fmt(s_h) if s_h else "-", fmt(s_c) if s_c else "-"))
    gr_ = slab(P["TS-C-PWR-RED"].solid, 2, CC["Z-GPIO-LEAD"][4] + 0.01, 58.5)
    chk("TS-C-PWR drop to the GPIO inside Z-GPIO-LEAD %s; leads %.1f / %.1f + housing + pin 9 + slack 15 = %.0f vs W1 %.2f, available %.0f~%.0f"
        % (cfmt(CC["Z-GPIO-LEAD"]), E.LENGTHS["TS_POWER"], E.LENGTHS["TS_POWER"], E.LENGTHS["TS_POWER"] + 24.0, pw["total"], pw["available"][0], pw["available"][1]),
        all(inside(slab(P["TS-C-PWR-" + t].solid, 2, CC["Z-GPIO-LEAD"][4] + 0.01, 58.5), CC["Z-GPIO-LEAD"], 0.05) for t in ("RED", "BLK"))
        and E.LENGTHS["TS_POWER"] + 24.0 <= pw["available"][0], fmt(gr_) if gr_ else "")
    gw = min(P["TS-C-PWR-" + t].solid.min_gap(rib, 3.0) for t in ("RED", "BLK"))
    gl = min(P["TS-C-PWR-" + t].solid.min_gap(Bb[i].solid, 3.0) for t in ("RED", "BLK") for i in ("CU-SCREENLID", "TS-RCLIP"))
    info("TS-C-PWR gaps: to the ribbon %.2f (W1 0.97), to the lid / clip %.2f (W1 0.35)" % (gw, gl))
    tse = [p for p in Ep if p.id.startswith("TS-") and p.note != "altview"]
    keep = box(-20, 1240, -10, TS.KEEP_Y, TS.KEEP_Z, 400)
    kv = sum((p.solid ^ keep).volume() for p in tse)
    chk("R31 keep-out: no display / cable (use pose) at y<=%.0f with z>=%.2f (front-most %.2f)" % (TS.KEEP_Y, TS.KEEP_Z, min(bb(p)[1] for p in tse)), kv <= TOL)
    # Pi orientation vs the CAD connector box (spec 3a: 'L2 글 USB/RJ45 end +x, GPIO edge +y' -> rot 0, within 0.4)
    dpi, d1c = TS.PI5["disp1"], CC["CU-E-PI5-DISP1"]
    hdr = (pib[0] + 32.5 - 25.4 + 1.27, pib[3] - 3.5 + 1.27)
    chk("Pi 5 pose (L2 CAD) = W1 rev 3 pose: CAM/DISP 1 x%.0f~%.0f y%.0f~%.0f (W1 x%.0f~%.0f y%.0f~%.0f, mouth x%.0f -x), GPIO pin 2 (%.2f, %.2f) = W1 (%.2f, %.2f), "
        "pin tips z%.1f" % (d1c[0], d1c[1], d1c[2], d1c[3], dpi["x"][0], dpi["x"][1], dpi["y"][0], dpi["y"][1], dpi["mouth"][0], hdr[0], hdr[1],
                            TS.PI5["gpio_pin2"][0], TS.PI5["gpio_pin2"][1], pib[5]),
        max(abs(d1c[0] - dpi["x"][0]), abs(d1c[1] - dpi["x"][1]), abs(d1c[2] - dpi["y"][0]), abs(d1c[3] - dpi["y"][1])) <= TS.PI5["disp1_vs_cad"]
        and abs(hdr[0] - TS.PI5["gpio_pin2"][0]) < EPS and abs(hdr[1] - TS.PI5["gpio_pin2"][1]) < EPS and abs(pib[5] - TS.PI5["gpio_top_z"]) < EPS)
    # sound paths (plan): every driver -> ear line passes the standing screen's plan rectangle by >= 200 (W1 248.58 at 43 deg)
    rect = (bb(Bb["TS-CRADLE"])[0], min(bb(Bb["TS-CRADLE"])[1], 216.0), bb(Bb["TS-CRADLE"])[3], TS.POCKET["back_wall_y"])
    ears = [(TS.XC - 75.0, -350.0), (TS.XC + 75.0, -350.0)]

    def seg_rect(a, b_, r):
        best = 1e9
        for t in np.linspace(0, 1, 2001):
            x = a[0] + (b_[0] - a[0]) * t
            y = a[1] + (b_[1] - a[1]) * t
            dx = max(r[0] - x, 0, x - r[2])
            dy = max(r[1] - y, 0, y - r[3])
            best = min(best, math.hypot(dx, dy))
        return best
    sp = [seg_rect((body.DRIVER_POSE[s_][0], body.DRIVER_POSE[s_][1]), e_, rect) for s_ in "LR" for e_ in ears]
    R31E["sound_paths_min"] = min(sp)
    chk("R31 sound paths (plan): driver centres (x%.1f / %.1f, y%.2f at %.0f deg) -> ears (x%.0f / %.0f, y-350) pass the screen rectangle x%.2f~%.2f y%.2f~%.2f by "
        ">= %.2f (W1 %.2f with y258.5 at 43 deg)" % (body.DRIVER_POSE["L"][0], body.DRIVER_POSE["R"][0], body.DRIVER_POSE["L"][1], body.ANGLE, ears[0][0], ears[1][0],
                                                       rect[0], rect[2], rect[1], rect[3], min(sp), TS.CHECKS["sound_paths_min"]), min(sp) >= 200.0)
    chk("R31 D14: no magnet in the display, cradle, leg or cables (all TS-* parts)", not [p.id for p in Ep + B if p.id.startswith("TS-") and "자석" in p.name_ko])
    info("R31 measured: " + ", ".join("%s %.3f" % kv_ for kv_ in R31E.items()))

    n_ok = sum(1 for r in res if r[0] == "ok")
    n_bad = sum(1 for r in res if r[0] == "!!")
    for st_, label, det in res:
        print("  %-4s %s  %s" % (st_, label, det))
    print("=" * 110)
    print("RESULT:", "PASS" if ok else "ISSUES (see !! lines)", "- checks %d OK, %d failed, spec-level notes %d (SPEC lines)" % (n_ok, n_bad, len(spec_issues)),
          "  total %.1f s" % (time.time() - T0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
