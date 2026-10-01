"""Self-check for body.py (L1 low rear bar, spec/body_low_L1.json).

  python3 check_body.py          # parts table, overlaps (body/body, body/key action, body/electronics), L1 spec probes

(1) every body Part: kind / group / bbox / bodies; printed parts: bed size, z>=0, one body, volume kept by orient, dims,
    print name / folder, Korean name, 추정 notes
(2) pairwise overlaps (a ^ b volume > 0.01 mm3) with a reason for every intended one
(3) L1 numbers (the governing spec) probed on the solids, not on the constants
    + R31 touchscreen (touchscreen/CAD_SPEC.md A..F, numbers.json control values, 22..90 deg swing vs the lid)
The folded-screen 'altview' parts are never checked against the standing-screen parts (two states of the same things).
"""
import itertools
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import body_L1 as body  # noqa: E402  (archived L1 checker: checks the archived L1 generator)
from cadlib import box, cyl_y, cyl_z, diff, union  # noqa: E402

TOL = 0.01

# (regex a, regex b, reason) - intended overlaps (order-free)
INTENDED = [
    (r"^BRK-.-BOLT", r"^BRK-.-NUT", "M3 볼트 ↔ 너트 나사산 물림 (너트 Ø2.5 구멍으로 모델)"),
    (r"^BRK-.-SCREW", r"^SPK.-PLY-FRONT$", "직결피스 8호 13 mm가 스피커 앞 아래 띠(합판)에 7 mm 물림 (합판은 구멍 없이 모델)"),
    (r"^TS-M3X20-HINGE-", r"^CU-LID$", "R31 M3×20 경첩 축이 뚜껑 먼 볼 Ø2.5에 직접 탭 (물림 7.6)"),
    (r"^TS-M3X20-LEG$", r"^TS-CRADLE$", "R31 M3×20 다리 축이 다리 걸이 먼 볼 Ø2.5에 직접 탭 (물림 5.4)"),
    (r"^TS-M3X10-LID", r"^CU-LIDSUP-CU-F[LR]$", "R31 M3×10이 나사형 모서리 받침 Ø2.5에 직접 탭 (물림 6.0)"),
]
INTENDED_E = [
    (r"^SPK.-BAFFLE$", r"^SPK-.$", "유닛 바스켓 Ø94가 컷아웃 Ø94를 지남 (같은 원 - 다각형 근사 오차)"),
    (r"^CU-IOPLATE$", r"^CU-E-SWITCH$", "로커 몸체 13.2×19.2가 같은 크기 구멍에 스냅 끼움 (면 일치)"),
    (r"^SPK.-XT30HOLDER$", r"^C-XT30F-.$", "XT30U-F가 받침 홈 12.6×10.8×5.6에 끼움 (면 일치)"),
    (r"^SPK.-GASKET$", r"^SPK-.$", "가스켓 안 Ø94 = 유닛 바스켓 테두리 Ø94 (같은 원 - 다각형 근사 오차)"),
]


def bbox_overlap(a, b):
    return not any(a[i] > b[i + 3] or b[i] > a[i + 3] for i in range(3))


def other_state(a, b):
    """R31: the folded screen ('altview') and the standing screen are two states of the same parts - never checked
    against each other."""
    return (a.note == "altview") != (b.note == "altview") and "터치" in a.group and "터치" in b.group


def overlaps(A, Bs, same=False):
    res = []
    bbA = [p.solid.bounding_box() for p in A]
    bbB = bbA if same else [p.solid.bounding_box() for p in Bs]
    pairs = itertools.combinations(range(len(A)), 2) if same else ((i, j) for i in range(len(A)) for j in range(len(Bs)))
    for i, j in pairs:
        b = A[j] if same else Bs[j]
        if not bbox_overlap(bbA[i], bbB[j]) or other_state(A[i], b):
            continue
        v = (A[i].solid ^ b.solid).volume()
        if v > TOL:
            res.append((v, A[i], b))
    return res


def classify(res, rules):
    ok, bad = [], []
    for v, a, b in res:
        why = None
        for ra, rb, w in rules:
            if (re.search(ra, a.id) and re.search(rb, b.id)) or (re.search(ra, b.id) and re.search(rb, a.id)):
                why = w
                break
        (ok if why else bad).append((v, a, b, why))
    return ok, bad


def union_bb(ps):
    bs = [p.solid.bounding_box() for p in ps]
    return [min(b[i] for b in bs) for i in range(3)] + [max(b[i + 3] for b in bs) for i in range(3)]


def fmt(b):
    return "x%.2f~%.2f y%.2f~%.2f z%.2f~%.2f (%.2f × %.2f × %.2f)" % (b[0], b[3], b[1], b[4], b[2], b[5], b[3] - b[0], b[4] - b[1], b[5] - b[2])


def hangul(s):
    return any("가" <= ch <= "힣" for ch in s)


def main():
    P = body.build()
    print("=" * 100)
    print("(1) body parts: %d" % len(P))
    print("%-20s %-10s %-12s %s" % ("id", "kind", "group", "bbox (world)"))
    probs = []
    ids = [p.id for p in P]
    if len(set(ids)) != len(ids):
        probs.append("duplicate ids")
    for p in P:
        b = p.solid.bounding_box()
        line = "%-20s %-10s %-12s %s" % (p.id, p.kind, p.group, fmt(b))
        if not hangul(p.name_ko):
            probs.append("%s: name_ko not Korean" % p.id)
        if p.kind == "plywood" and "합판" not in p.material:
            probs.append("%s: plywood material" % p.id)
        if p.kind == "print" and p.print_solid is None:
            line += "  | (altview: no print file)"
            if p.note != "altview" or "접은 상태" not in p.group:
                probs.append("%s: printed part without a print solid" % p.id)
        elif p.kind == "print":
            q = p.print_solid.bounding_box()
            sz = (q[3] - q[0], q[4] - q[1], q[5] - q[2])
            nb = len(p.solid.decompose())
            line += "  | bed %.1f×%.1f×%.1f" % sz
            if nb != 1:
                probs.append("%s: %d bodies" % (p.id, nb))
            if abs(q[2]) > 1e-6 or abs(q[0]) > 1e-6 or abs(q[1]) > 1e-6:
                probs.append("%s: print solid not at the bed origin %s" % (p.id, q[:3]))
            if max(sz) > 256:
                probs.append("%s: bed size %.1f > 256" % (p.id, max(sz)))
            elif max(sz) > 220:
                line += "  (> 220)"
            if abs(p.print_solid.volume() - p.solid.volume()) > 1e-3 * max(1.0, p.solid.volume()):
                probs.append("%s: print volume changed" % p.id)
            if not p.dims:
                probs.append("%s: no dims" % p.id)
            if not p.print_name or p.print_folder != ("07_터치스크린" if p.id.startswith("TS-") else "05_본체출력물"):
                probs.append("%s: print name/folder" % p.id)
            if p.note and "추정" in p.note and not p.note.startswith("추정") and "; 추정" not in p.note and ". 추정" not in p.note:
                probs.append("%s: 추정 note format" % p.id)
        print(line)
    kinds = {}
    for p in P:
        kinds[p.kind] = kinds.get(p.kind, 0) + 1
    print("kinds:", kinds)
    print("print problems:", probs or "none")

    import build_all
    sig = {}
    for p in P:
        if p.kind == "print" and p.print_solid is not None:
            sig.setdefault(build_all.signature(p.print_solid), []).append(p.print_name)
    print("distinct printed shapes: %d" % len(sig))
    for k, v in sig.items():
        print("   %-28s x%d  (%.0f cm3)" % (v[0], len(v), k[0] / 1000.0))

    print("=" * 100)
    print("(2) overlaps > %.2f mm3" % TOL)
    res = overlaps(P, None, same=True)
    ok, bad = classify(res, INTENDED)
    print("body ↔ body: %d intended, %d unexpected" % (len(ok), len(bad)))
    for v, a, b, w in ok:
        print("   ok  %8.2f  %-18s %-18s %s" % (v, a.id, b.id, w))
    for v, a, b, w in bad:
        print("   !!  %8.2f  %-18s %-18s at %s" % (v, a.id, b.id, fmt((a.solid ^ b.solid).bounding_box())))

    import keyaction_parts
    K = keyaction_parts.build_all()
    res = overlaps(P, K)
    ok, bad = classify(res, INTENDED)
    print("body ↔ key action (%d parts): %d intended, %d unexpected" % (len(K), len(ok), len(bad)))
    for v, a, b, w in ok:
        print("   ok  %8.2f  %-18s %-22s %s" % (v, a.id, b.id, w))
    for v, a, b, w in bad:
        print("   !!  %8.2f  %-18s %-22s at %s" % (v, a.id, b.id, fmt((a.solid ^ b.solid).bounding_box())))
    kmax = max(p.solid.bounding_box()[4] for p in K)
    print("   key action max y %.2f (trough starts y212)" % kmax)

    E = None
    if os.path.exists(os.path.join(HERE, "electronics_L1.py")):
        try:
            import electronics_L1 as electronics      # archived L1 pair (electronics.py is L2 now)
            E = electronics.build()
        except Exception as ex:                                     # the other agent may be mid-edit
            print("body ↔ electronics: electronics.build() failed (%s: %s)" % (type(ex).__name__, ex))
        if E is not None:
            res = overlaps(P, E)
            ok, bad = classify(res, INTENDED_E)
            print("body ↔ electronics (%d parts, information): %d intended, %d not intended" % (len(E), len(ok), len(bad)))
            for v, a, b, w in ok:
                print("   ok  %8.2f  %-18s %-18s %s" % (v, a.id, b.id, w))
            for v, a, b, w in sorted(bad, key=lambda r: -r[0]):
                bb = (a.solid ^ b.solid).bounding_box()
                print("   !!  %8.2f  %-18s %-18s at %s" % (v, a.id, b.id, fmt(bb)))

    print("=" * 100)
    print("(3) L1 spec numbers (spec/body_low_L1.json) probed on the solids")
    by = {p.id: p for p in P}
    checks = []

    def chk(label, got, want, tol=0.011):
        good = all(abs(g - w) <= tol for g, w in zip(got, want))
        checks.append(good)
        print("   %s %-60s got %s  want %s" % ("OK" if good else "!!", label, " ".join("%.3f" % g for g in got),
                                              " ".join("%.3f" % w for w in want)))

    def at_least(label, got, lo):
        good = got >= lo
        checks.append(good)
        print("   %s %-60s got %.3f  want >= %.3f" % ("OK" if good else "!!", label, got, lo))

    vol = lambda a, b: (a ^ b).volume()
    B_ = box
    run_checks(P, by, K, E, chk, at_least, vol, B_)
    print("checks: %d OK, %d failed" % (sum(checks), len(checks) - sum(checks)))


def run_checks(P, by, K, E, chk, at_least, vol, B_):
    # ---------------- overall
    shell = [p for p in P if p.kind == "plywood" or p.id.endswith("BAFFLE") or p.id in ("CU-TRAY", "CU-LID", "CU-IOPLATE")]
    b = union_bb(shell)
    chk("rear bar shell x -16..1238 (1254), y252..447, z5..134", (b[0], b[3], b[3] - b[0], b[1], b[4], b[2], b[5]),
        (-16, 1238, 1254, 252, 447, 5, 134))
    allb = union_bb(shell + K)
    chk("key action + rear bar shell: 1254 x 447", (allb[3] - allb[0], allb[4] - allb[1]), (1254, 447))
    allp = union_bb(P)
    print("   ..  everything of body.py: %s  (behind y447: dovetail blocks + latches only)" % fmt(allp))
    behind = [p.id for p in P if p.solid.bounding_box()[4] > 447.001]
    chk("parts behind the back face y447 = 4 dovetail blocks + 2 latches", (len(behind), float(all(re.match(r"^JOIN-(DT|LATCH)", i) for i in behind))), (6, 1))

    # ---------------- speaker boxes
    for s, x0, x1 in (("L", -16, 197), ("R", 1025, 1238)):
        sp = [p for p in P if p.id.startswith("SPK%s-PLY" % s) or p.id == "SPK%s-BAFFLE" % s]
        b = union_bb(sp)
        chk("speaker box %s x%g..%g y252..447 z5..134" % (s, x0, x1), b, (x0, 252, 5, x1, 447, 134))
        # inner air volume on the inner faces (driver not subtracted)
        ix0, ix1 = (body.SX0, body.SX1) if s == "L" else (body.mxv(body.SX1), body.mxv(body.SX0))
        env = B_(ix0, ix1, 252.0, 447.0, 5.0, 134.0)
        solid_baffle = body.prism_x(body.baffle_poly(), ix0, ix1)     # undrilled baffle (cutout closed by the driver, holes by glue)
        rest = diff(env, [p.solid for p in sp if not p.id.endswith("BAFFLE")] + [solid_baffle])
        comps = [c for c in rest.decompose() if c.bounding_box()[1] > 262.0 and c.bounding_box()[4] < 436.0 and c.volume() > 1e5]
        v = sum(c.volume() for c in comps) / 1e6
        at_least("speaker %s inner volume (L, inner faces, driver not subtracted)" % s, v, 2.9)
        chk("speaker %s cavity is one closed air body" % s, (len(comps),), (1,))
        chk("speaker %s side panel pentagon cut 11.5 x 195 x 129" % s,
            [by["SPK%s-PLY-SIDEOUT" % s].solid.bounding_box()[i + 3] - by["SPK%s-PLY-SIDEOUT" % s].solid.bounding_box()[i] for i in range(3)],
            (11.5, 195, 129))
        pent = by["SPK%s-PLY-SIDEOUT" % s].solid
        chk("speaker %s side panel area = pentagon (y252,5)(447,5)(447,134)(312.5,134)(252,29.11)" % s,
            (pent.volume() / 11.5,), (body.poly_area(body.PENT),), tol=0.5)

    # ---------------- slant, driver seat, grille (local slant frame probes)
    import numpy as np
    for s in "LR":
        cx = body.DRV_X[s]
        baf = by["SPK%s-BAFFLE" % s].solid
        sl = lambda m: body.sl(m, cx)
        chk("baffle %s cutout Ø94 on the driver axis (Ø93.8 empty through 11.5)" % s, (vol(baf, sl(cyl_y(0, 0, -0.5, 12.0, 93.8))),), (0.0,))
        ring = diff(cyl_y(0, 0, 0.5, 11.0, 100.0), [cyl_y(0, 0, 0.4, 11.1, 94.4)])
        at_least("baffle %s material around the cutout (Ø94.4..100 ring, mm3)" % s, vol(baf, sl(ring)), 0.97 * math.pi / 4 * (100 ** 2 - 94.4 ** 2) * 10.5)
        pil = union([cyl_y(px, pz, 0.2, 9.8, 3.2) for (px, pz) in body.DRV_PIL])
        chk("baffle %s driver pilots PCD115 45° open 10 deep" % s, (vol(baf, sl(pil)),), (0.0,))
        pil_end = union([cyl_y(px, pz, 10.1, 11.4, 3.2) for (px, pz) in body.DRV_PIL])
        at_least("baffle %s driver pilots blind (solid 10.1..11.4 behind them)" % s, vol(baf, sl(pil_end)), 0.95 * 4 * math.pi * 1.6 ** 2 * 1.3)
        gp = union([cyl_y(hx, hz, 0.2, 8.8, 3.2) for (hx, hz) in body.GR_HOLES])
        chk("baffle %s grille pilots open 9 deep" % s, (vol(baf, sl(gp)),), (0.0,))
        wx = body.WIRE_X if s == "L" else body.mxv(body.WIRE_X)
        wh = cyl_y(wx - cx, body.WIRE_S - body.DRV_S, -0.2, 11.7, 5.8)
        chk("baffle %s speaker-wire hole Ø6 open through (x%.1f, s%.0f)" % (s, wx, body.WIRE_S), (vol(baf, sl(wh)),), (0.0,))
        strip = by["SPK%s-PLY-FRONT" % s].solid
        chk("wire hole %s clear of the plywood front strip (hole Ø6+2 vs strip)" % s,
            (vol(strip, sl(cyl_y(wx - cx, body.WIRE_S - body.DRV_S, -0.2, 14.0, 10.0))),), (0.0,))
        # driver envelope (CW-100B25): flange 105 sq x4 on the 3 mm gasket, basket Ø93.6 to 57 deep, magnet Ø85x17 at the back
        drv = union([B_(-52.5, 52.5, -7.0, -3.0, -52.5, 52.5), cyl_y(0, 0, -3.0, 54.0 - 17.0, 93.6), cyl_y(0, 0, 54.0 - 17.0, 54.0, 85.0)])
        drv_w = sl(drv)
        panels = union([p.solid for p in P if p.id.startswith("SPK%s-PLY" % s)])
        chk("driver %s envelope clear of the plywood panels" % s, (vol(drv_w, panels),), (0.0,))
        chk("driver %s envelope clear of the baffle (basket Ø93.6 in the Ø94 cutout)" % s, (vol(drv_w, baf),), (0.0,))
        mag = sl(cyl_y(0, 0, 37.0, 54.0, 85.0)).bounding_box()
        at_least("driver %s magnet bottom above the bottom panel top z16.5 (mm clear)" % s, mag[2] - 16.5, 1.0)
        at_least("driver %s magnet rear clear of the back panel y435.5 (mm)" % s, 435.5 - mag[4], 20.0)
        gr = by["SPK%s-GRILLE" % s].solid
        # local frame of the grille: (world - T) * R
        v, f = None, None
        from cadlib import mesh_arrays
        v, f = mesh_arrays(gr)
        loc = (v - np.array([cx, body.DRV_YZ[0], body.DRV_YZ[1]])) @ np.array(body.R_SL)
        ext = loc.max(axis=0) - loc.min(axis=0)
        chk("grille %s <= 150 in x, <= 118 along the slant, <= 15 off the face" % s,
            (float(ext[0] <= 150.01), float(ext[2] <= 118.01), float(-loc[:, 1].min() <= 15.01)), (1, 1, 1))
        chk("grille %s stands on the slant face (local y max 0) inside s 0..121" % s,
            (round(loc[:, 1].max(), 3), float(loc[:, 2].min() + body.DRV_S >= 0), float(loc[:, 2].max() + body.DRV_S <= 121)), (0.0, 1, 1))
        heads = union([cyl_y(px, pz, -10.5, -7.0, 8.0) for (px, pz) in body.DRV_PIL])     # 8-ho pan heads + 0.5 clearance
        chk("grille %s clears the driver flange and screw heads by >= 0.5" % s, (vol(gr, sl(union([heads, drv]))),), (0.0,))
        cover = B_(-47.0, 47.0, -12.9, -11.1, -47.0, 47.0)            # grille face plate over the Ø94 cone opening
        at_least("grille %s face plate covers the cone (bars over Ø94, fraction)" % s, vol(gr, sl(cover)) / (94 * 94 * 1.8), 0.15)
        chk("grille %s not above the box top z134" % s, (gr.bounding_box()[5] <= 134.0 + 1e-6,), (1,))
        gk = by["SPK%s-GASKET" % s].solid
        chk("gasket %s 3 mm on the slant face (under the flange)" % s, (vol(gk, drv_w), vol(gk, baf)), (0.0, 0.0))

    # ---------------- trough rules
    mine = [p for p in P]
    hi = B_(-20.0, 1242.0, 212.0, 252.0, body.Z_TROUGH_MAX, 400.0)
    v = sum(vol(p.solid, hi) for p in mine)
    chk("nothing of body.py in the trough y212..252 above z72", (v,), (0.0,))
    front = B_(-30.0, 1250.0, -10.0, 212.0, -5.0, 300.0)
    intr = [(p.id, vol(p.solid, front)) for p in mine if bbox_overlap(p.solid.bounding_box(), front.bounding_box())]
    intr = [(i, w) for (i, w) in intr if w > TOL]
    chk("only bracket bolts / nuts reach into y<212 (the cheek; grommet flanges touch y212)",
        (float(all(re.match(r"^BRK-.-(BOLT|NUT)", i) for i, w in intr)), len(intr)), (1, 8))
    low = B_(-20.0, 1242.0, 212.0, 252.0, 0.0, 22.0)
    lows = sorted(set(p.id for p in mine if vol(p.solid, low) > TOL))
    print("   ..  parts below z22 in the trough (cable zone): %s" % ", ".join(lows))
    chk("in the cable zone z<22 only the bracket and the 2 screw pads / XT30 pads", (float(all(re.match(r"^(BRK-[LR](-GROM\d|-BOLT\d|-SCREW)?|SPK.-XT30HOLDER)$", i) for i in lows)),), (1,))
    floor = B_(-20.0, 1242.0, 212.0, 252.0, 0.0, 18.49)
    lowf = sorted(set(p.id for p in mine if vol(p.solid, floor) > TOL))
    chk("below z18.5 in the trough only the bracket legs (at the cheek) + grommets/bolts", (float(all(re.match(r"^BRK-[LR](-GROM\d|-BOLT\d)?$", i) for i in lowf)),), (1,))
    for s in "LR":
        brk = by["BRK-%s" % s].solid
        lb = (brk ^ B_(-100, 1300, 218.1, 252.0, 0.0, 18.49)).volume()
        chk("bracket %s: nothing below z18.5 behind its leg (y>218)" % s, (lb,), (0.0,))
    # module USB cables (spec cable_trough note): O1 plug x124.75..137.25 y196.8..221.8, R25 bend to y246.8 then +x;
    # O7 plug x1111..1123.5 then -x. Tube OD 3.5 at z14.5 (plug axis) and on the floor (z1.75)
    cab = union([B_(124.75, 137.25, 212.0, 221.8, 10.7, 18.3), B_(1111.0, 1123.5, 212.0, 221.8, 10.7, 18.3),
                 B_(131.0, 583.0, 245.05, 248.55, 0.0, 16.25), B_(733.0, 1117.0, 245.05, 248.55, 0.0, 16.25)])
    chk("module USB cable lane y245..248.6 z<=16.25 (O1 → CU, O7 → CU) clear", (sum(vol(p.solid, cab) for p in mine),), (0.0,))
    chk("left cheek headphone exit x-12.6..-4.1 z3..7.5 open behind y212 (bracket leg starts z7.6)",
        (vol(by["BRK-L"].solid, B_(-12.6, -4.1, 212.0, 252.0, 3.0, 7.5)),), (0.0,))
    chk("EL lead notch x13.5..22.5 / ER x1206.1..1212.5 lanes clear (y212..252, cable zone z0..22)",
        (sum(vol(p.solid, union([B_(13.5, 22.5, 212.0, 252.0, 0.0, 22.0), B_(1206.1, 1212.5, 212.0, 252.0, 0.0, 22.0)])) for p in mine),), (0.0,))
    for s, c0, c1 in (("L", -16.0, -0.68), ("R", 1222.68, 1238.0)):
        bb = by["BRK-%s" % s].solid
        leg = bb ^ B_(c0 - 5, c1 + 5, 212.4, 218.1, 2.9, 18.9)
        lb_ = leg.bounding_box()
        chk("bracket %s vertical leg 0.5 inside the cheek, y212.5..218 from z7.6 (cables pass under)" % s, (lb_[0], lb_[3], lb_[1], lb_[4], lb_[2]), (c0 + 0.5, c1 - 0.5, 212.5, 218, 7.6))
        chk("bracket %s reaches the speaker front y252, top z30" % s, (bb.bounding_box()[4], bb.bounding_box()[5]), (252, 30))
        got = sorted(round((by["BRK-%s-GROM%d" % (s, i)].solid.bounding_box()[0] + by["BRK-%s-GROM%d" % (s, i)].solid.bounding_box()[3]) / 2, 2)
                     for i in (1, 2))
        chk("bracket %s grommets on the cheek M3 seats" % s, got, sorted(body.BRK_SEAT_X[s]))
        scr = by["BRK-%s-SCREW" % s].solid
        stp = by["SPK%s-PLY-FRONT" % s].solid
        at_least("bracket %s screw bite in the front strip (mm3 ~ Ø4.2 x 7)" % s, vol(scr, stp), 0.9 * math.pi * 2.1 ** 2 * 7.0)
        chk("bracket %s screw stays inside the 11.5 strip (tip y<263.5)" % s, (float(scr.bounding_box()[4] < 263.5),), (1,))
        chk("bracket %s pad touches the strip face (y252) without overlap" % s, (vol(bb, stp), bb.bounding_box()[4]), (0.0, 252.0))

    # ---------------- XT30 holders
    for s in "LR":
        h = by["SPK%s-XT30HOLDER" % s].solid
        pk = body.XT30_POCKET[s]
        pb = B_(pk[0] + 0.05, pk[1] - 0.05, pk[2] + 0.05, pk[3] - 0.05, pk[4] + 0.05, pk[5] - 0.05)
        chk("XT30 holder %s pocket 12.6 x 10.8 x 5.6 empty" % s, ((h ^ pb).volume(), pk[1] - pk[0], pk[3] - pk[2], pk[5] - pk[4]), (0.0, 12.6, 10.8, 5.6))
        mouth = pk[1] if s == "L" else pk[0]
        chk("XT30 holder %s mouth faces the centre unit at x%.0f (open face)" % (s, mouth),
            (vol(h, B_(mouth - 0.5 if s == "L" else mouth - 0.01, mouth + 0.01 if s == "L" else mouth + 0.5, pk[2] + 0.1, pk[3] - 0.1, pk[4] + 0.1, pk[5] - 0.1)),), (0.0,))
        hb = h.bounding_box()
        chk("XT30 holder %s in the trough on the speaker front (y<=252), z18.5..33" % s, (hb[4], hb[2], hb[5]), (252.0, 18.5, 33.0))
        gr = by["SPK%s-GRILLE" % s].solid
        chk("XT30 holder %s clear of the grille and the baffle" % s, (vol(h, gr), vol(h, by["SPK%s-BAFFLE" % s].solid)), (0.0, 0.0))
        wx = body.WIRE_X if s == "L" else body.mxv(body.WIRE_X)
        sx0, sx1 = (body.XT_SLOT[0], body.XT_SLOT[1]) if s == "L" else (body.mxv(body.XT_SLOT[1]), body.mxv(body.XT_SLOT[0]))
        chk("XT30 holder %s wire slot (open top) right under the baffle wire hole x" % s, (float(sx0 < wx < sx1),), (1,))

    # ---------------- centre unit
    cu = union_bb([p for p in P if p.id.startswith("CU-PLY")] + [by["CU-IOPLATE"], by["CU-TRAY"]])
    lpb = (by["CU-LID"].solid ^ B_(550, 760, 250, 450, 0, 88.0)).bounding_box()          # R31: lid plate without the hinge cheeks / feet
    cu = [min(cu[0], lpb[0]), min(cu[1], lpb[1]), min(cu[2], lpb[2]), max(cu[3], lpb[3]), max(cu[4], lpb[4]), max(cu[5], lpb[5])]
    chk("centre unit 822 x 195 x 83 at x200 y252 z5", (cu[0], cu[1], cu[2], cu[3] - cu[0], cu[4] - cu[1], cu[5] - cu[2]), (200, 252, 5, 822, 195, 83))
    walls = [by["CU-PLY-P%02d" % i].solid.bounding_box() for i in (5, 6, 7, 8, 9, 10)]
    chk("walls z16.5..76.5 (inner height 60)", (min(w[2] for w in walls), max(w[5] for w in walls)), (16.5, 76.5))
    chk("low divider 40 tall (z16.5..56.5)", (by["CU-PLY-P11"].solid.bounding_box()[5] - by["CU-PLY-P11"].solid.bounding_box()[2],), (40.0,))
    bays = body.BAYS
    for pid, key in (("P08", "end_L"), ("P10", "divider"), ("P11", "low_divider"), ("P09", "end_R")):
        bb = by["CU-PLY-%s" % pid].solid.bounding_box()
        chk("panel %s x = bay %s %s" % (pid, key, bays[key]), (bb[0], bb[3]), bays[key])
    fr = by["CU-PLY-P05"].solid
    chk("front notch x583..733 z16.5..34 empty, front solid above z34", (vol(fr, B_(583.01, 732.99, 252.0, 263.5, 16.5, 33.99)),
                                                                          vol(fr, B_(583.01, 732.99, 252.0, 263.5, 34.01, 76.5))),
        (0.0, 149.98 * 11.5 * 42.49), tol=1.0)
    tb = by["CU-TRAY"].solid.bounding_box()
    chk("CU tray x556.25..755.85 y252..447 z5 (base 11.5)", (tb[0], tb[3], tb[1], tb[4], tb[2]), (556.25, 755.85, 252, 447, 5))
    lb = by["CU-LID"].solid.bounding_box()
    chk("CU lid v2 x556.55..755.55 z76.5.. (hinge cheeks to z96+5.5 = 101.5)", (lb[0], lb[3], lb[2], lb[5]), (556.55, 755.55, 76.5, 101.5))
    lp = (by["CU-LID"].solid ^ B_(550, 760, 250, 450, 0, 88.0)).bounding_box()
    chk("CU lid v2 plate 199 x 195 x 11.5 (z76.5..88)", (lp[3] - lp[0], lp[4] - lp[1], lp[2], lp[5]), (199.0, 195.0, 76.5, 88.0))
    io = by["CU-IOPLATE"].solid
    ib = io.bounding_box()
    chk("I/O plate x556.25..755.85 y..447 z16.5..76.5 (60 tall)", (ib[0], ib[3], ib[4], ib[2], ib[5]), (556.25, 755.85, 447, 16.5, 76.5))
    hz = body.IO_HZ
    for nm, x, d in (("J501", body.IO_HX["J501"], 6.3), ("SW", body.IO_HX["SW"], 12.9), ("USBC", body.IO_HX["USBC"], 7.8), ("PASS", body.IO_HX["PASS"], 10.8)):
        chk("I/O hole %s at x%.2f z46.5 open through the skin" % (nm, x), (vol(io, cyl_y(x, hz, 445.01, 447.1, d)),), (0.0,))
    lz1 = body.JACK_LEDGE[5]
    chk("J501 ledge top + board 1.6 + PJ-313 axis 2.5 = z46.5", (lz1 + 1.6 + 2.5,), (46.5,))
    for (x, y) in body.TRAY_FEET:
        fp = [p for p in P if p.id.startswith("FOOT-") and abs((p.solid.bounding_box()[0] + p.solid.bounding_box()[3]) / 2 - x) < 0.01
              and abs((p.solid.bounding_box()[1] + p.solid.bounding_box()[4]) / 2 - y) < 0.01]
        chk("tray foot boss at (%.2f, %.0f) has a foot under it" % (x, y), (len(fp),), (1,))
    # CU tray bosses moved by shift_from_v3 (probe the Pi boss tops z22.5 and the tap holes)
    C = body._load("body_centre_unit.json")
    Tr = next(p for p in C["printed"] if p["id"] == "PR-CU-TRAY")
    fe = {f["name"]: f for f in Tr["features"]}
    tr = by["CU-TRAY"].solid
    for (px, py) in fe["pi5_bosses"]["at"]:
        x, y = px + body.DX, py + body.DY
        chk("tray Pi boss (%.2f, %.0f) top z22.5, tap Ø2.2 open" % (x, y), (tr.bounding_box()[5] >= 22.5, vol(tr, cyl_z(x, y, 22.4, 22.6, 5.8)) > 0,
                                                                          vol(tr, cyl_z(x, y, 15.0, 22.5, 2.0))), (1, 1, 0.0))

    # ---------------- feet / joints / latches
    feet = [p.solid.bounding_box() for p in P if p.id.startswith("FOOT-")]
    chk("feet 14 at z0..5, 28 dia", (len(feet), min(b[2] for b in feet), max(b[5] for b in feet), feet[0][3] - feet[0][0]), (14, 0, 5, 28))
    boxes = [("스피커 L", -16.0, 197.0), ("가운데", 200.0, 1022.0), ("스피커 R", 1025.0, 1238.0)]
    for nm, x0, x1 in boxes:
        n = sum(1 for b in feet if x0 <= (b[0] + b[3]) / 2 <= x1)
        chk("feet under %s (>= 4, inside its footprint)" % nm, (float(n >= 4),), (1,))
    for s, (a, b_) in (("L", (197.0, 200.0)), ("R", (1022.0, 1025.0))):
        gap = B_(a + 0.001, b_ - 0.001, 0.0, 500.0, 0.0, 200.0)
        inside = sorted(set(p.id for p in P if vol(p.solid, gap) > TOL))
        chk("joint gap %s x%.0f..%.0f holds only the EVA strips, the dovetail neck and the latch" % (s, a, b_),
            (float(all(re.match(r"^JOIN-(EVA|DT-.C|LATCH)", i) for i in inside)), float(any(i.startswith("JOIN-EVA") for i in inside))), (1, 1))
        fem, male = by["JOIN-DT-%sS" % s].solid, by["JOIN-DT-%sC" % s].solid
        chk("dovetail %s: male in the female groove with play (±0.15 y, +0.4 into the groove, no touch)" % s,
            (vol(fem, male), vol(fem, male.translate((0, 0.15, 0))), vol(fem, male.translate((0, -0.15, 0))),
             vol(fem, male.translate((-0.4 if s == "L" else 0.4, 0, 0)))), (0, 0, 0, 0))
        at_least("dovetail %s: pulling apart 1.5 mm is blocked by the head (mm3)" % s,
                 vol(fem, male.translate((1.5 if s == "L" else -1.5, 0, 0))), 10.0)
        chk("dovetail %s: speaker part lifts off upward (female slides up free)" % s,
            (vol(fem.translate((0, 0, 80.0)), male),), (0.0,))
        lt = by["JOIN-LATCH-%s" % s].solid.bounding_box()
        chk("latch %s on the block faces y461, spans the gap" % s, (lt[1], float(lt[0] < a and lt[3] > b_)), (461.0, 1))

    # ---------------- centre-unit contents
    ks_l1 = B_(212.5, 411.8, 269.35, 429.65, 16.5, 39.9)
    ks_l2 = B_(212.5, 411.8, 279.6, 419.4, 39.9, 75.3)
    chk("spare-key 2-layer stack (58.8) clear of every body part", (sum(vol(p.solid, union([ks_l1, ks_l2])) for p in P if not p.id.startswith("CU-PLY")),), (0.0,))
    ki = by["CU-KSINSERT"].solid.bounding_box()
    chk("key-storage insert wall x412.8, top z75.5 (>= stack 75.3, lid 76.5)", (ki[0], ki[5]), (412.8, 75.5))
    run_checks_r31(P, by, E, chk, at_least, vol, B_)
    sups = [p for p in P if p.id.startswith("CU-LIDSUP")]
    chk("12 lid corner supports, tops z76.5", (len(sups), max(p.solid.bounding_box()[5] for p in sups), min(p.solid.bounding_box()[5] for p in sups)), (12, 76.5, 76.5))
    bank = B_(741.0 + body.DX, 911.0 + body.DX, 231.5 + body.DY, 316.5 + body.DY, 35.5 + body.DZ, 70.5 + body.DZ)
    chk("power bank max envelope 170x85x35 clear of the holder / supports / panels", (sum(vol(p.solid, bank) for p in P),), (0.0,))
    # CU bay component envelopes (body_centre_unit components moved by shift_from_v3) - information
    comps = [c for c in Tr["components"] if "power-bank" not in c["name"] and "hub" not in c["name"].lower()
             and "PD trigger" not in c["name"] and "KCD1" not in c["name"] and "pedal jack" not in c["name"]]
    print("   ..  CU bay component envelopes (v3 boxes + shift) vs body parts (information):")
    for c in comps:
        env = body.B(c["box"], body.DX, body.DY, body.DZ)
        hits = [(p.id, vol(p.solid, env)) for p in P if vol(p.solid, env) > TOL]
        print("       %-40s %s  %s" % (c["name"][:40], fmt(env.bounding_box()), ", ".join("%s %.1f" % h for h in hits) or "clear"))



def run_checks_r31(P, by, E, chk, at_least, vol, B_):
    """R31 touchscreen (touchscreen/CAD_SPEC.md A..F, numbers.json) probed on the solids."""
    import touchscreen as TS
    from cadlib import cyl_x
    print("   --  R31 touchscreen (CAD_SPEC A..F)")
    lid = by["CU-LID"].solid
    full = lambda m, b: abs(vol(m, b) - b.volume()) < 1e-3 * max(1.0, b.volume())

    # ---- A. CU lid v2
    xs = [596.05 + 8 * i for i in range(15)]
    open_ = sum(vol(lid, B_(x - 1.9, x + 1.9, 302.1, (383.9 if x in (652.05, 660.05) else 396.9), 76.4, 88.1)) for x in xs)
    chk("A1 15 vent slots 4 wide x596.05..708.05 open y302..397 (spec y301 + 1 for the 3 mm web) (x652.05/660.05 to y384)", (open_,), (0.0,))
    chk("A1 slot front end at y302 (3 mm web y299..302 solid)", (float(all(full(lid, B_(x - 1.9, x + 1.9, 299.1, 301.9, 85.6, 86.9)) for x in xs)),), (1,))
    chk("A1 slots x652.05/660.05 filled y384..397 (pocket floor + block under it)",
        (float(all(full(lid, B_(x - 1.9, x + 1.9, 391.0, 397.3, 80.0, 84.4)) for x in (652.05, 660.05))),), (1,))
    for s in ("left", "right"):
        h = TS.HINGE[s]
        f0, f1 = h["far"]
        n0, n1 = h["near"]
        e0, e1 = h["ear"]
        chk("A2 %s hinge block x%.1f..%.1f: far %.1f..%.1f + 0.2 + ear slot %.1f..%.1f + 0.2 + near %.1f..%.1f"
            % (s, f0, n1, f0, f1, e0, e1, n0, n1),
            (vol(lid, B_(f0 - 1.0, f0 - 0.01, 285, 295, 88.5, 101)), float(full(lid, B_(f0 + 0.1, f1 - 0.1, 289.0, 291.0, 99.0, 101.3))),
             vol(lid, B_(f1 + 0.01, n0 - 0.01, 280, 300, 88.01, 110)), float(full(lid, B_(n0 + 0.1, n1 - 0.1, 289.0, 291.0, 99.0, 101.3))),
             vol(lid, B_(n1 + 0.01, n1 + 1.0, 285, 295, 88.5, 101))), (0, 1, 0, 1, 0))
        chk("A2 %s cheek profile: R5.5 top z101.5, trapezoid z88 y281..299 / z96 y284.5..295.5" % s,
            (vol(lid, B_(n0, n1, 289.8, 290.2, 101.52, 102)), float(vol(lid, B_(n0, n1, 289.8, 290.2, 101.2, 101.45)) > 0),
             float(full(lid, B_(n0 + 0.1, n1 - 0.1, 281.1, 298.9, 88.0, 88.2))), vol(lid, B_(n0, n1, 280.0, 280.9, 88.01, 88.3)),
             vol(lid, B_(n0, n1, 295.6, 300, 95.9, 96.1))), (0, 1, 1, 0, 0))
        chk("A2 %s axis y290 z96: near Ø3.3 through, far Ø2.5 through (8), material round both" % s,
            (vol(lid, cyl_x(290, 96, n0 - 0.1, n1 + 0.1, 3.2)), vol(lid, cyl_x(290, 96, f0 - 0.1, f1 + 0.1, 2.4)),
             float(vol(lid, cyl_x(290, 96, f0, f1, 5.0)) > 0.8 * 3.1416 / 4 * (25 - 6.25) * 8)), (0, 0, 1))
        chk("A2 %s heel stop face = lid top z88 at y281..286 in the ear slot, solid below (y278..300 filled)" % s,
            (float(full(lid, B_(e0 + 0.1, e1 - 0.1, 281.0, 286.0, 76.6, 88.0))), float(full(lid, B_(f0 + 0.1, n1 - 0.1, 278.1, 299.9, 76.6, 85.4)))), (1, 1))
    chk("A3 ribbon / power hole x592..614 y292..298 open through z76.5..88", (vol(lid, B_(592.01, 613.99, 292.01, 297.99, 76.4, 88.1)),), (0.0,))
    chk("A3 hole edges R1 (top and bottom, x-parallel): corner square 1x1 is 21.5 % removed",
        tuple(round(1 - vol(lid, B_(600, 606, ya, yb, za, zb)) / 6.0, 2) for (ya, yb, za, zb) in
              ((291, 292, 87, 88), (298, 299, 87, 88), (291, 292, 76.5, 77.5), (298, 299, 76.5, 77.5))), (0.21, 0.21, 0.21, 0.21), tol=0.015)
    pk = TS.POCKET
    chk("A4 leg pocket x649..663: floor z84.5 (y%.2f..397.4) open, vertical back wall y397.4" % 390.06,
        (vol(lid, B_(649.01, 662.99, 390.2, 397.39, 84.51, 88.1)), float(full(lid, B_(649.5, 662.5, 390.2, 397.3, 83.5, 84.49))),
         float(full(lid, B_(649.5, 662.5, 397.41, 399.0, 84.6, 87.4))), vol(lid, B_(649.01, 662.99, 397.41, 397.89, 88.0 - 0.001, 88.0))), (0, 1, 1, 0))
    import body_L1 as _b
    t30 = math.tan(math.radians(30))
    y0r = _b.POCKET_RAMP_Y0
    zr = lambda y: 88.0 - (y - y0r) * t30
    chk("A4 30 deg front ramp from (y%.2f, z88) (spec y%.2f moved forward, see note) to (y%.2f, z84.5)" % (y0r, _b.POCKET_RAMP_Y0_SPEC, y0r + 3.5 / t30),
        tuple(float(full(lid, B_(650, 662, y - 0.05, y + 0.05, 83.0, zr(y) - 0.1))) + float(vol(lid, B_(650, 662, y - 0.05, y + 0.05, zr(y) + 0.1, 88.2)) == 0)
              for y in (385.0, 387.0, 389.5)), (2, 2, 2))
    chk("A4 solid block x646..666 y384..402 under the pocket, down to z76.5 (spec z80: no floating underside)",
        (float(full(lid, B_(646.2, 665.8, 384.2, 401.8, 76.6, 84.4))),), (1,))
    leg = by["TS-LEG"].solid
    chk("A4/D leg foot seated: no overlap, touches the floor (-0.05 z) and the back wall (+0.05 y)",
        (vol(leg, lid), float(vol(leg.translate((0, 0, -0.05)), lid) > 0.01), float(vol(leg.translate((0, 0.05, 0)), lid) > 0.01)), (0, 1, 1))
    chk("A4 spec ramp (y388.34) would cut into the leg underside (reason for the move)", (float(_b.POCKET_RAMP_Y0 < _b.POCKET_RAMP_Y0_SPEC),), (1,))
    chk("A5 4 fold feet 16x16x8 z88..96", tuple(float(full(lid, B_(a + 0.01, b - 0.01, c + 0.01, d - 0.01, 88.0, 95.99))) for (a, b, c, d) in TS.FOLD_FEET),
        (1, 1, 1, 1))
    for (hx, hy) in _b.LID_SCREW_XY:
        chk("A6 front screw (%.1f, %.1f): Ø3.4 through, Ø6.5 x 7.5 counterbore, 4.0 left under the head" % (hx, hy),
            (vol(lid, cyl_z(hx, hy, 76.4, 88.1, 3.3)), vol(lid, cyl_z(hx, hy, 80.51, 88.1, 6.4)),
             float(full(lid, diff(cyl_z(hx, hy, 76.51, 80.49, 6.3), [cyl_z(hx, hy, 76.4, 80.6, 3.6)])))), (0, 0, 1))
    chk("A7 no CU-FL / CU-FR magnets; CU-RR magnets kept (741.3, 426.5)",
        (float(any(k in by for k in ("CU-MAG-SUP-CU-FL", "CU-MAG-LID-CU-FL", "CU-MAG-SUP-CU-FR", "CU-MAG-LID-CU-FR"))),
         float("CU-MAG-LID-CU-RR" in by and "CU-MAG-SUP-CU-RR" in by)), (0, 1))
    mb = by["CU-MAG-LID-CU-RR"].solid.bounding_box()
    chk("A7 CU-RR lid magnet centre (741.3, 426.5)", ((mb[0] + mb[3]) / 2, (mb[1] + mb[4]) / 2), (741.3, 426.5))
    chk("A8 ribbon-clip seat under the lid round (x605, y320): 2 blind Ø3.1 x 5 holes, flat pad at z76.5",
        tuple(vol(lid, cyl_z(x, 320.0, 76.4, 81.49, 3.0)) for x in (_b.RCLIP_LID_X - 12, _b.RCLIP_LID_X + 12))
        + (float(vol(lid, B_(589.2, 619.3, 314.2, 325.8, 81.6, 85.4)) > 0.4 * 30 * 11.6 * 3.8),), (0, 0, 1))
    chk("A9 lid printed rib face (z76.5) on the bed", (by["CU-LID"].print_solid.bounding_box()[5], ), (25.0,))

    # ---- B. screw-type corner supports
    for tag in ("CU-FL", "CU-FR"):
        sp = by["CU-LIDSUP-%s" % tag]
        b = sp.solid.bounding_box()
        cx, cy = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2
        chk("B %s screw support 18x18x12, Ø2.5 x 10 centre hole, no magnet pocket, folder 05" % tag,
            (b[3] - b[0], b[4] - b[1], b[5] - b[2], vol(sp.solid, cyl_z(cx, cy, 66.51, 76.6, 2.4)), float(full(sp.solid, cyl_z(cx, cy, 64.6, 66.45, 2.4))),
             float(full(sp.solid, diff(cyl_z(cx, cy, 70.4, 76.4, 8.2), [cyl_z(cx, cy, 70.3, 76.5, 2.7)]))), float(sp.print_folder == "05_본체출력물")),
            (18, 18, 12, 0, 1, 1, 1))
        chk("B %s under the lid screw hole (%.1f, %.1f)" % (tag, cx, cy), (cx, cy), _b.LID_SCREW_XY[0] if tag == "CU-FL" else _b.LID_SCREW_XY[1])
        at_least("B M3x10 thread bite in %s (mm3, Ø3 over Ø2.5 x 6)" % tag, vol(by["TS-M3X10-LID%d" % (1 if tag == "CU-FL" else 2)].solid, sp.solid), 8.0)
    chk("B 10 magnet-type supports + 2 screw-type", (sum(1 for p in P if p.id.startswith("CU-LIDSUP") and "자석" in p.name_ko),
                                                   sum(1 for p in P if p.id.startswith("CU-LIDSUP") and "나사형" in p.name_ko)), (10, 2))

    # ---- C. cradle
    crl = _b.cradle_local()
    X0, X1 = TS.CR_X
    cb = crl.bounding_box()
    body_ = crl ^ B_(X0 - 1, 616.0, -3.0, 130.0, -2.0, 30.0)
    bb_ = body_.bounding_box()
    chk("C1 outer x559.04..752.96 (193.92), u-2.5..122.74, w-1..16 (body, left of the ears)", (cb[0], cb[3], bb_[1], bb_[4], bb_[2], bb_[5]),
        (559.04, 752.96, -2.5, 122.74, -1.0, 16.0))
    chk("C1 glass pocket x561.04..750.96 u-0.3..120.54 w-1..9.4 empty (glass + 0.3, walls 2.0 / 2.2, wall front 1.0 ahead of the glass)",
        (vol(crl, B_(561.05, 750.95, -0.29, 120.53, -1.1, 9.39)), float(full(crl, B_(559.05, 561.03, 0, 120, -0.99, 15.99)))), (0, 1))
    chk("C2 back plate w9.4..12.4 (3.0)", (float(full(crl, B_(690, 710, 90, 100, 9.41, 12.39))), vol(crl, B_(690, 710, 90, 100, 12.41, 15.99))), (1, 0))
    for x in TS.LUG_X:
        for u in TS.LUG_U:
            chk("C3 lug hole (%.0f, u%.2f) Ø2.7 through, Ø5 counterbore from the back, 1.5 left" % (x, u),
                (vol(crl, cyl_z(x, u, 9.3, 12.5, 2.6)), vol(crl, cyl_z(x, u, 10.91, 12.5, 4.9)),
                 float(full(crl, diff(cyl_z(x, u, 9.45, 10.85, 4.8), [cyl_z(x, u, 9.4, 10.9, 4.0)])))), (0, 0, 1))
    chk("C4 4 Pi-standoff clearances Ø7 at x618.21/676.21 u35.62/84.62",
        (sum(vol(crl, cyl_z(x, u, 9.3, 12.5, 6.9)) for x in TS.STANDOFF_X for u in TS.STANDOFF_U),), (0.0,))
    chk("C5 L-shaped window: x596..666 u46..74 + x640..666 u30..46 through the back plate",
        (vol(crl, B_(596.01, 665.99, 46.01, 73.99, 9.3, 12.5)), vol(crl, B_(640.01, 665.99, 30.01, 46.1, 9.3, 12.5)),
         float(full(crl, B_(595.0, 595.9, 50, 70, 9.5, 12.3))), float(full(crl, B_(630, 639.9, 31, 45, 9.5, 12.3)))), (0, 0, 1, 1))
    chk("C6 cross ribs u20 / u108 at w12.4..16", tuple(float(full(crl, B_(565, 595, u - 0.95, u + 0.95, 12.45, 15.95))) for u in TS.RIB_U), (1, 1))
    behind = [(559.0, 624.19), (632.21, 646.69), (667.31, 711.99), (720.01, 753.0)]
    chk("C6 nothing behind w16 except ears, leg hanger and leg clip", (sum(vol(crl, B_(a, b, -30, 130, 16.01, 40)) for a, b in behind),), (0.0,))
    chk("C7 bottom open slot x592..614 u-2.5..3 w8..16 (open to the back)", (vol(crl, B_(592.01, 613.99, -2.6, 2.99, 8.01, 16.1)),), (0.0,))
    for s in ("left", "right"):
        e0, e1 = TS.HINGE[s]["ear"]
        eb = (crl ^ B_(e0 - 0.1, e1 + 0.1, -30, -2.51, -2, 30)).bounding_box()
        chk("C8 %s ear x%.1f..%.1f (8.0), axis (u-9, w16) Ø3.3 open, material >= R4.2" % (s, e0, e1),
            (eb[0], eb[3], vol(crl, cyl_x(-9.0, 16.0, e0 - 0.1, e1 + 0.1, 3.2)), float(full(crl, diff(cyl_x(-9.0, 16.0, e0 + 0.01, e1 - 0.01, 8.4), [cyl_x(-9.0, 16.0, e0, e1, 5.0)])))),
            (e0, e1, 0, 1))
    pu, pw = TS.LEG_PIVOT_UW
    chk("C9 leg hanger: near x646.7..650.7 Ø3.3, far x661.3..667.3 Ø2.5, leg gap x651..661 free (0.3 each side), R3.8 round (u20, w19.5)",
        (vol(crl, cyl_x(pu, pw, 646.6, 650.8, 3.2)), vol(crl, cyl_x(pu, pw, 661.2, 667.4, 2.4)), vol(crl, B_(650.71, 661.29, 14.0, 26.0, 16.01, 24.0)),
         float(vol(crl, B_(647, 650.5, 19.9, 20.1, 23.1, 23.25)) > 0), vol(crl, B_(646.5, 667.5, 19.9, 20.1, 23.35, 24.0))), (0, 0, 0, 1, 0))
    chk("C9 hanger 45 deg underside stops at u%.1f (cover ledge u28.5)" % _b.CLEVIS_U_MAX,
        (vol(crl, B_(646.7, 667.3, _b.CLEVIS_U_MAX + 0.01, 28.5, 12.41, 30)),), (0.0,))
    chk("C10 leg clip jaws x647.5..650.7 / x661.3..664.5 (0.3 gap) at u105..111, catch 0.8 inward = 0.5 over the leg at w22.52..",
        (float(full(crl, B_(647.6, 650.6, 105.1, 110.9, 16.1, 22.4))), float(full(crl, B_(661.4, 664.4, 105.1, 110.9, 16.1, 22.4))),
         float(full(crl, B_(650.71, 651.49, 105.1, 110.9, 22.55, 22.75))), float(full(crl, B_(660.51, 661.29, 105.1, 110.9, 22.55, 22.75))),
         vol(crl, B_(651.0, 661.0, 17.0, 118.0, 16.5, 22.5))), (1, 1, 1, 1, 0))
    rc = _b.RCLIP_CR
    chk("C11 ribbon-clip seat inside (recess 0.7 + 2 Ø3.1 pin holes, round x%.0f u%.0f; lane x597..613 u10..20 covered)" % (rc[0], rc[1]),
        (vol(crl, B_(597, 613, 10, 20, 9.3, 10.09)), sum(vol(crl, cyl_z(rc[0] + d, rc[1], 10.0, 12.5, 3.0)) for d in (-12, 12))), (0, 0))
    wc = TS.place(crl, 25.0).bounding_box()
    w22 = TS.place(crl, 22.0).bounding_box()
    w90b = (TS.place(crl, 90.0) ^ B_(558, 616, 0, 500, 0, 300)).bounding_box()
    c25 = TS.place(crl, 25.0)
    front = c25.trim_by_plane((0, -1, 0), -(wc[1] + 0.02)).bounding_box()
    rearb = (c25 ^ B_(558, 616, 0, 500, 0, 300))
    rb = rearb.bounding_box()
    rear = rearb.trim_by_plane((0, 1, 0), rb[4] - 0.02).bounding_box()
    chk("C12 25 deg: front-most (y277.34, z109.08)", (wc[1], front[2] + 0.02), (277.34, 109.08), tol=0.03)
    chk("C12 25 deg: rear-most of the body (y345.68, z215.40), top z222.58", (rb[4], rear[5] - 0.02, wc[5]), (345.68, 215.40, 222.58), tol=0.03)
    print("   ..  25 deg whole cradle incl. the leg-clip jaws (w..23.3): rear-most y%.2f" % wc[4])
    heel22 = TS.place(crl, 22.0).trim_by_plane((0, 0, -1), -(w22[2] + 0.02)).bounding_box()
    chk("C12 22 deg: front-most y276.67, heel touches (y283, z88)", (w22[1], w22[2], heel22[1]), (276.67, 88.0, 283.0), tol=0.02)
    chk("C8 heel 0.38 above the lid at 25 deg", (wc[2] - 88.0,), (0.38,), tol=0.01)
    chk("C12 folded 90 deg: y296.5..421.74, z96..113 (body)", (w90b[1], w90b[4], w90b[2], w90b[5]), (296.5, 421.74, 96.0, 113.0))
    sweep = [(th, vol(TS.place(crl, th), lid)) for th in [22.0 + 0.5 * i for i in range(137)]]
    chk("C12 swing 22..90 deg (0.5 steps) never cuts the lid / hinge cheeks / fold feet", (max(v for th, v in sweep),), (0.0,), tol=1e-3)
    ps = by["TS-CRADLE"].print_solid
    q = ps.bounding_box()
    chk("C13 printed standing on the top edge (u122.74 face on the bed; bed x 193.92, y = w-1..23.3 incl. hanger / clip), height <= 256",
        (q[3] - q[0], q[4] - q[1], float(q[5] - q[2] <= 256), float(vol(ps, B_(q[0], q[3], q[1], q[4], 0.0, 0.5)) > 0.9 * 193.92 * 17 * 0.5)),
        (193.92, 24.3, 1, 1))
    print("   ..  cradle print height %.1f (spec about 131: the ear heel reaches u%.2f)" % (q[5] - q[2], _b.ear_poly()[1][0]))

    # ---- D. leg
    A = TS.LEG_AX_YZ
    lb = leg.bounding_box()
    chk("D leg axis (y305.43, z120.8), foot (y394.4, z87.5), 95.0, 20.5 deg", (A[0], A[1], TS.LEG_LEN_MODEL, TS.LEG_ANGLE), (305.43, 120.80, 95.0, 20.5),
        tol=0.03)
    chk("D leg x651..661, foot R3: lowest z84.5, rear-most y397.4; axis hole Ø3.3 open", (lb[0], lb[3], lb[2], lb[4], vol(leg, cyl_x(A[0], A[1], 650, 662, 3.2))),
        (651, 661, 84.5, 397.4, 0), tol=0.02)
    lq = by["TS-LEG"].print_solid.bounding_box()
    chk("D leg printed flat on the wide face: 101 x 10 x 6", tuple(sorted((lq[3] - lq[0], lq[4] - lq[1], lq[5] - lq[2]), reverse=True)) + (lq[5] - lq[2],),
        (101.0, 10.0, 6.0, 6.0), tol=0.02)
    lf = by["TS-LEG-FOLD"].solid.bounding_box()
    chk("D leg stowed on the cradle back: y316..417, z89.5..95.5 (w16.5..22.5, u17..118), clear of the folded cradle and the lid",
        (lf[1], lf[4], lf[2], lf[5], vol(by["TS-LEG-FOLD"].solid, by["TS-CRADLE-FOLD"].solid), vol(by["TS-LEG-FOLD"].solid, lid)),
        (316, 417, 89.5, 95.5, 0, 0), tol=0.02)
    chk("D leg vs cradle (use) no overlap", (vol(leg, by["TS-CRADLE"].solid),), (0.0,))

    # ---- E. small parts
    cov = by["TS-WINCOVER"]
    cq = cov.print_solid.bounding_box()
    chk("E window cover: flange 73 (x594.5..667.5), plate 2 + plug 1.5 + tabs; no overlap with the cradle",
        (cov.solid.bounding_box()[0], cov.solid.bounding_box()[3], vol(cov.solid, by["TS-CRADLE"].solid)), (594.5, 667.5, 0.0))
    fl = (TS.place(_b.cover_local(), 25.0))
    fll = _b.cover_local() ^ B_(500, 800, -10, 130, 12.4, 14.4)
    fb = fll.bounding_box()
    chk("E cover flange L: upper 73 x 31 (u44.5..75.5) + lower 29 x 17.5 (x638.5..667.5 from u28.5), 2 thick",
        (fb[3] - fb[0], fb[4] - 44.5, fb[1], fb[5] - fb[2], (fll ^ B_(500, 800, 28.5, 44.4, 0, 20)).bounding_box()[0]), (73.0, 31.0, 28.5, 2.0, 638.5))
    rcl = by["TS-RCLIP-LID"]
    rq = rcl.print_solid.bounding_box()
    chk("E ribbon clips x2 30 x 12 x 3 (+ pins 4), one print file", (rq[3] - rq[0], rq[4] - rq[1], rq[5] - rq[2],
                                                                  float(rcl.print_name == by["TS-RCLIP-CR"].print_name)), (30.0, 12.0, 7.0, 1))
    chk("E lid clip: under the lid z73.5..76.5, pins in the seat holes (no overlap)", (rcl.solid.bounding_box()[2], vol(rcl.solid, lid)), (73.5, 0.0))
    chk("E cradle clip: in the recess, no overlap with the cradle", (vol(by["TS-RCLIP-CR"].solid, by["TS-CRADLE"].solid),), (0.0,))
    sc = by["TS-SCREENCOVER"].solid.bounding_box()
    chk("E screen cover 196 x 128 x 3 on the folded rim z113 (altview)", (sc[3] - sc[0], sc[4] - sc[1], sc[2], sc[5], float(by["TS-SCREENCOVER"].note == "altview")),
        (196, 128, 113, 116, 1))

    # ---- F. assembly rules
    ts = [p for p in P if p.id.startswith("TS-")]
    alt = [p.id for p in ts if p.note == "altview"]
    chk("F folded state = separate 'altview' parts in group '터치스크린 (접은 상태, 별도 보기)'",
        (float(sorted(alt) == ["TS-CRADLE-FOLD", "TS-LEG-FOLD", "TS-SCREENCOVER"]),
         float(all(by[i].group == "터치스크린 (접은 상태, 별도 보기)" for i in alt))), (1, 1))
    chk("F printed touchscreen parts in 07_터치스크린, lid + supports in 05",
        (float(all(p.print_folder == "07_터치스크린" for p in ts if p.kind == "print")),
         float(by["CU-LID"].print_folder == "05_본체출력물")), (1, 1))
    tb = union_bb([p for p in ts if p.id not in ("TS-SCREENCOVER",) and not p.id.startswith("TS-M3X10")])
    chk("F screen, hinges, leg inside x559..753 (plywood lids x<=556.05 / x>=756.05 open)", (float(tb[0] >= 559.0 - 1e-6), float(tb[3] <= 753.0 + 1e-6)), (1, 1))
    chk("F screen cover inside the CU lid x556.55..755.55", (float(sc[0] >= 556.55), float(sc[3] <= 755.55)), (1, 1))
    allts = union_bb([p for p in ts if not p.id.startswith("TS-M3X10")])
    chk("F trough rule: every touchscreen part (lid screws aside) behind y276.67 (y212..252 free), before y447", (float(allts[1] >= 276.66), float(allts[4] <= 447)), (1, 1))
    fz = max(by[i].solid.bounding_box()[5] for i in ("TS-CRADLE-FOLD", "TS-LEG-FOLD"))
    chk("F folded height z113 <= speaker top z134", (fz,), (113.0,))
    if E:
        eb = {p.id: p for p in E}
        if "TS-E-TD2" in eb:
            chk("F display inside the cradle (no overlap), folded display on the folded cradle (no overlap)",
                (vol(eb["TS-E-TD2"].solid, by["TS-CRADLE"].solid), vol(eb["TS-E-TD2-FOLD"].solid, by["TS-CRADLE-FOLD"].solid)), (0.0, 0.0))

if __name__ == "__main__":
    main()
