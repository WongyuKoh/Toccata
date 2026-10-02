"""Self-check for body.py.

  python3 check_body.py          # parts table, overlaps (body/body, body/key action, body/electronics), bbox checks

(1) every body Part: kind / group / bbox / bodies; printed parts: bed size, z>=0, one body, volume kept by orient
(2) pairwise overlaps (a ^ b volume > 0.01 mm3) with a reason for every intended one
(3) the overall numbers the specs give
"""
import itertools
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import body  # noqa: E402

TOL = 0.01

# (regex a, regex b, reason) - intended overlaps (order-free)
INTENDED = [
    (r"^BRK-.-BOLT", r"^BRK-.-NUT", "M3 볼트 ↔ 너트 나사산 물림 (너트 Ø2.5 구멍으로 모델)"),
    (r"^BRK-.-SCREW", r"^SPK.-PLY-BOTTOM$", "직결피스 8호 13 mm가 스피커 아랫판(합판)에 9 mm 물림 (합판은 구멍 없이 모델)"),
]
INTENDED_E = [
    (r"^SPK.-BAFFLE$", r"^SPK-.$", "유닛 바스켓 Ø94가 컷아웃 Ø94를 지남 (같은 원 - 다각형 근사 오차)"),
    (r"^CU-IOPLATE$", r"^CU-E-SWITCH$", "로커 몸체 13.2×19.2가 같은 크기 구멍에 스냅 끼움 (면 일치)"),
]


def bbox_overlap(a, b):
    return not any(a[i] > b[i + 3] or b[i] > a[i + 3] for i in range(3))


def overlaps(A, Bs, same=False):
    res = []
    bbA = [p.solid.bounding_box() for p in A]
    bbB = bbA if same else [p.solid.bounding_box() for p in Bs]
    pairs = itertools.combinations(range(len(A)), 2) if same else ((i, j) for i in range(len(A)) for j in range(len(Bs)))
    for i, j in pairs:
        b = A[j] if same else Bs[j]
        if not bbox_overlap(bbA[i], bbB[j]):
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


def main():
    P = body.build()
    print("=" * 100)
    print("(1) body parts: %d" % len(P))
    print("%-20s %-10s %-12s %s" % ("id", "kind", "group", "bbox (world)"))
    probs = []
    for p in P:
        b = p.solid.bounding_box()
        line = "%-20s %-10s %-12s %s" % (p.id, p.kind, p.group, fmt(b))
        if p.kind == "print":
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
            if not p.print_name or p.print_folder != "05_본체출력물":
                probs.append("%s: print name/folder" % p.id)
        print(line)
    kinds = {}
    for p in P:
        kinds[p.kind] = kinds.get(p.kind, 0) + 1
    print("kinds:", kinds)
    print("print problems:", probs or "none")

    # distinct printed shapes (same signature as build_all)
    import build_all
    sig = {}
    for p in P:
        if p.kind == "print":
            sig.setdefault(build_all.signature(p.print_solid), []).append(p.print_name)
    print("distinct printed shapes: %d" % len(sig))
    for k, v in sig.items():
        print("   %-28s x%d" % (v[0], len(v)))

    print("=" * 100)
    print("(2) overlaps > %.2f mm3" % TOL)
    res = overlaps(P, None, same=True)
    ok, bad = classify(res, INTENDED)
    print("body ↔ body: %d intended, %d unexpected" % (len(ok), len(bad)))
    for v, a, b, w in ok:
        print("   ok  %8.2f  %-18s %-18s %s" % (v, a.id, b.id, w))
    for v, a, b, w in bad:
        print("   !!  %8.2f  %-18s %-18s" % (v, a.id, b.id))

    import keyaction_parts
    K = keyaction_parts.build_all()
    res = overlaps(P, K)
    ok, bad = classify(res, INTENDED)
    print("body ↔ key action (%d parts): %d intended, %d unexpected" % (len(K), len(ok), len(bad)))
    for v, a, b, w in ok:
        print("   ok  %8.2f  %-18s %-22s %s" % (v, a.id, b.id, w))
    for v, a, b, w in bad:
        print("   !!  %8.2f  %-18s %-22s" % (v, a.id, b.id))
    # near-contact report for the bracket against the cheeks
    for p in P:
        if re.match(r"^BRK-[LR]$", p.id):
            fr = [k for k in K if k.id == ("EL-FRAME" if p.id.endswith("L") else "ER-FRAME")][0]
            print("   %s vs %s: volume %.4f, bracket y0 %.2f (cheek rear face y212)" % (p.id, fr.id, (p.solid ^ fr.solid).volume(),
                                                                                     p.solid.bounding_box()[1]))

    if os.path.exists(os.path.join(HERE, "electronics.py")):
        import electronics
        E = electronics.build()
        res = overlaps(P, E)
        ok, bad = classify(res, INTENDED_E)
        print("body ↔ electronics (%d parts, information): %d intended, %d not intended" % (len(E), len(ok), len(bad)))
        for v, a, b, w in ok:
            print("   ok  %8.2f  %-18s %-18s %s" % (v, a.id, b.id, w))
        for v, a, b, w in bad:
            bb = (a.solid ^ b.solid).bounding_box()
            print("   !!  %8.2f  %-18s %-18s at %s" % (v, a.id, b.id, fmt(bb)))

    print("=" * 100)
    print("(3) spec numbers")
    by = {p.id: p for p in P}
    checks = []

    def chk(label, got, want, tol=0.011):
        good = all(abs(g - w) <= tol for g, w in zip(got, want))
        checks.append(good)
        print("   %s %-46s got %s  want %s" % ("OK" if good else "!!", label, " ".join("%.2f" % g for g in got),
                                              " ".join("%.2f" % w for w in want)))

    shell = [p for p in P if p.kind == "plywood" or p.id.endswith("BAFFLE") or p.id in ("CU-TRAY", "CU-LID", "CU-IOPLATE")]
    b = union_bb(shell)
    chk("rear bar shell x (1254 = -16..1238)", (b[0], b[3], b[3] - b[0]), (-16, 1238, 1254))
    chk("rear bar shell y (195 = 215..410)", (b[1], b[4]), (215, 410))
    import keyaction_parts as kp  # noqa: F811
    kb = union_bb(K)
    allb = union_bb(shell + K)
    chk("instrument key action + rear bar: 1254 x 410", (allb[3] - allb[0], allb[4] - allb[1]), (1254, 410))
    for s, x0, x1 in (("L", -16, 164), ("R", 1058, 1238)):
        b = union_bb([p for p in P if p.id.startswith("SPK%s-PLY" % s) or p.id == "SPK%s-BAFFLE" % s])
        chk("speaker box %s x%g..%g y215..410 z22..232" % (s, x0, x1), b, (x0, 215, 22, x1, 410, 232))
        chk("driver axis %s (cutout centre)" % s, ((by["SPK%s-GRILLE" % s].solid.bounding_box()[0] + by["SPK%s-GRILLE" % s].solid.bounding_box()[3]) / 2,
                                                   (by["SPK%s-GRILLE" % s].solid.bounding_box()[2] + by["SPK%s-GRILLE" % s].solid.bounding_box()[5]) / 2),
            (74 if s == "L" else 1148, 142))
        chk("grille %s y202..215 z77..207 (ring 11)" % s, [by["SPK%s-GRILLE" % s].solid.bounding_box()[i] for i in (1, 4, 2, 5)], (202, 215, 77, 207))
    cu = union_bb([p for p in P if p.id.startswith("CU-PLY")] + [by["CU-LID"], by["CU-IOPLATE"]])
    chk("centre unit 894 x 195 x 100 at x164 y215 z22", (cu[0], cu[1], cu[2], cu[3] - cu[0], cu[4] - cu[1], cu[5] - cu[2]),
        (164, 215, 22, 894, 195, 100))
    tb = by["CU-TRAY"].solid.bounding_box()
    chk("CU tray x520.2..719.8 y215..410 z22 (base 11.5)", (tb[0], tb[3], tb[1], tb[4], tb[2]), (520.2, 719.8, 215, 410, 22))
    lb = by["CU-LID"].solid.bounding_box()
    chk("CU lid x520.5..719.5 z110.5..122", (lb[0], lb[3], lb[2], lb[5]), (520.5, 719.5, 110.5, 122))
    ib = by["CU-IOPLATE"].solid.bounding_box()
    chk("I/O plate x520.2..719.8 y..410 z33.5..110.3", (ib[0], ib[3], ib[4], ib[2], ib[5]), (520.2, 719.8, 410, 33.5, 110.3))
    fz = [p.solid.bounding_box() for p in P if p.id.startswith("FOOT-")]
    sz = [p.solid.bounding_box() for p in P if p.id.startswith("FOOTSP-")]
    chk("feet 14 at z0..18", (len(fz), min(b[2] for b in fz), max(b[5] for b in fz)), (14, 0, 18))
    chk("spacers 14 at z18..22", (len(sz), min(b[2] for b in sz), max(b[5] for b in sz)), (14, 18, 22))
    chk("feet y centres 299 / 379", sorted(set(round((b[1] + b[4]) / 2, 2) for b in fz)), (299, 379))
    for s, c0, c1 in (("L", -16.0, -0.68), ("R", 1222.68, 1238.0)):
        bb = by["BRK-%s" % s].solid
        leg = bb ^ body.box(c0 - 5, c1 + 5, 212.4, 218.1, 2.9, 15.0)     # below the 2.5 fillet (z15.5..18)
        lb_ = leg.bounding_box()
        chk("bracket %s vertical leg 0.5 inside the cheek" % s, (lb_[0], lb_[3], lb_[1], lb_[4], lb_[2]), (c0 + 0.5, c1 - 0.5, 212.5, 218, 3))
        chk("bracket %s horizontal leg z18..22 to y245" % s, (bb.bounding_box()[5], bb.bounding_box()[4]), (22, 245))
    h = by["SPKR-XT30HOLDER"].solid.bounding_box()
    chk("XT30 holder R (spec box, extended back to y243)", h, (1058, 218, 8, 1094, 243, 22))
    h = by["SPKL-XT30HOLDER"].solid.bounding_box()
    print("   ..  XT30 holder L reshaped around the O1 USB-C plug: %s" % fmt(h))
    for s in "LR":
        spec_pocket = (151.4, 222.6, 12.2, 164.0, 233.4, 17.8) if s == "L" else (1058.0, 222.6, 12.2, 1070.6, 233.4, 17.8)
        hp = by["SPK%s-XT30HOLDER" % s].solid
        pb = body.box(spec_pocket[0] + 0.05, spec_pocket[3] - 0.05, spec_pocket[1] + 0.05, spec_pocket[4] - 0.05,
                      spec_pocket[2] + 0.05, spec_pocket[5] - 0.05)
        chk("XT30 holder %s pocket empty at the spec pocket" % s, ((hp ^ pb).volume(),), (0.0,))
    lat = union_bb([by["JOIN-LATCH-L"], by["JOIN-LATCH-R"]])
    print("   ..  latches reach y%.1f, latch seats y410..419.5 (spec: behind the 410 line)" % lat[4])
    extra_checks(P, by, chk)
    print("   ..  electronics switch bezel / latches are the only things behind y410")
    print("checks: %d OK, %d failed" % (sum(checks), len(checks) - sum(checks)))


def extra_checks(P, by, chk):
    """review fixes 2026-09-30 (body.py): each check probes the solids, not the constants."""
    B_ = body.box
    vol = lambda a, b: (a ^ b).volume()
    # 1 bracket: grommets / bolts / nuts on the key-action cheek seats, left cable notch open, grommet seats kept
    for s, xs in (("L", (-11.80, -4.88)), ("R", (1226.88, 1233.80))):
        got = sorted(round((by["BRK-%s-GROM%d" % (s, i)].solid.bounding_box()[0] + by["BRK-%s-GROM%d" % (s, i)].solid.bounding_box()[3]) / 2, 2)
                     for i in (1, 2))
        chk("bracket %s grommet x = cheek seats" % s, got, xs)
        got = sorted(round((by["BRK-%s-NUT%d" % (s, i)].solid.bounding_box()[0] + by["BRK-%s-NUT%d" % (s, i)].solid.bounding_box()[3]) / 2, 2)
                     for i in (1, 2))
        chk("bracket %s nut x = cheek seats" % s, got, xs)
    bl = by["BRK-L"].solid
    chk("bracket L cable notch x-13..-3.7 z2.9..8 empty (all y)", (vol(bl, B_(-13.0, -3.7, 212.4, 218.1, 2.9, 8.0)),), (0.0,))
    web = B_(-15.5, -1.18, 215.5, 217.1, 8.0, 9.0)             # web material under the grommet holes kept
    chk("bracket L web kept z8..9 under the grommets (>1.6x14.3x1 minus teardrop tips)", (min(1.0, vol(bl, web) / 15.0),), (1.0,), tol=0.25)
    chk("bracket R leg bottom not notched (z3..8 full)", (vol(by["BRK-R"].solid, B_(1224.0, 1236.0, 215.5, 217.1, 3.0, 8.0)),),
        (12.0 * 1.6 * 5.0,), tol=0.05)
    # 2 speaker-wire holes: hole open at (140 / 1082, z38), spec x6 / x1216 closed
    for s, x, xold in (("L", 140.0, 6.0), ("R", 1082.0, 1216.0)):
        bf = by["SPK%s-BAFFLE" % s].solid
        chk("baffle %s wire hole Ø6 at x%.0f z38 open" % (s, x), (vol(bf, body.cyl_y(x, 38.0, 214.9, 226.6, 5.8)),), (0.0,))
        chk("baffle %s spec wire hole x%.0f now solid" % (s, xold), (vol(bf, body.cyl_y(xold, 38.0, 215.0, 226.5, 5.8)),),
            (math.pi * 2.9 ** 2 * 11.5,), tol=1.5)
        hb = by["SPK%s-XT30HOLDER" % s].solid.bounding_box()
        chk("wire %s drops in front of the XT30 holder (hole x inside holder x, holder front y218)" % s,
            (float(hb[0] - 20 <= x <= hb[3]), hb[1]), (1.0, 218.0))
    # 3 CU tray pads: solid from z22 under the 10 pilots
    T = next(p for p in body._load("body_centre_unit.json")["printed"] if p["id"] == "PR-CU-TRAY")
    fe = {f["name"]: f for f in T["features"]}
    pads = [(px, py) for nm in ("amp_bosses", "buck_bosses", "amp_input_jack_board_bosses") for (px, py) in fe[nm]["at"]]
    tr = by["CU-TRAY"].solid
    ring = [vol(tr, body.diff(body.cyl_z(px, py, 22.0, 22.5, 8.8), [body.cyl_z(px, py, 21.9, 22.6, 3.0)])) for (px, py) in pads]
    chk("CU tray: %d pilot pads start at z22 (ring area at z22..22.5)" % len(pads), (len(pads), min(ring)),
        (10, math.pi * (4.4 ** 2 - 1.5 ** 2) * 0.5), tol=0.3)
    # 4 XT30 holder R screws >= 4 inside the bottom panel, pocket unchanged (checked above), clear of the O7 cable (electronics)
    hr = by["SPKR-XT30HOLDER"].solid
    for x in (1079.0, 1089.0):
        chk("XT30 holder R screw x%.0f y235 through (Ø4.5 open)" % x, (vol(hr, body.cyl_z(x, 235.0, 7.9, 22.1, 4.3)),), (0.0,))
    chk("XT30 holder R old screw y228 solid above the counterbore", (vol(hr, body.cyl_z(1079.0, 228.0, 19.5, 22.0, 4.3)),),
        (math.pi * 2.15 ** 2 * 2.5,), tol=0.3)
    # 5 dovetail speaker rear ear screw: hole at (124, 389) open, no hole at (142, 403), clear of the foot
    for s in ("L", "R"):
        blk = by["JOIN-DT-%sS" % s].solid
        mx_ = (lambda x: x) if s == "L" else body.mxv
        chk("dovetail %sS rear ear hole x%.0f y389 open" % (s, mx_(124.0)), (vol(blk, body.cyl_z(mx_(124.0), 389.0, 15.9, 22.1, 4.3)),), (0.0,))
        chk("dovetail %sS old hole y403 gone (solid ear there)" % s, (vol(blk, body.cyl_z(mx_(142.0), 403.0, 19.5, 22.0, 4.3)),),
            (math.pi * 2.15 ** 2 * 2.5,), tol=0.3)
    # 6 latch seats 9.5 thick
    for pid in ("JOIN-DT-LS", "JOIN-DT-RS", "JOIN-DT-LC", "JOIN-DT-RC"):
        chk("%s latch seat to y419.5" % pid, (by[pid].solid.bounding_box()[4],), (419.5,))
    # 7 grille face y202..204, ring back y204..215
    g = by["SPKL-GRILLE"].solid
    chk("grille L face ends at y204 (ring interior empty y204.05..215)", (vol(g, B_(74 - 50, 74 + 50, 204.05, 214.99, 142 - 50, 142 + 50)),), (0.0,))
    # 8 notes
    for pid, words in (("SPKL-BAFFLE", ("벽(둘레) 4줄", "30~40 %")), ("JOIN-DT-LS", ("벽 4줄", "채움 25", "EVA")), ("JOIN-DT-LC", ("벽 4줄", "채움 25", "EVA")),
                       ("CU-TRAY", ("TRAY_RIB_PITCH", "브리지"))):
        txt = by[pid].print_note + by[pid].note
        chk("%s notes mention %s" % (pid, "/".join(words)), (float(all(w in txt for w in words)),), (1.0,))
    chk("CU tray note: '처지면 피치 25로' removed", (float("처지면 피치 25로" in by["CU-TRAY"].print_note),), (0.0,))


if __name__ == "__main__":
    main()
