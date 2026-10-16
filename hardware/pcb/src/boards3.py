"""Rev E (2026-10-08, review fixes) physical sheets and wiring lists:

  BRD-07  small boards: J702 amp-input board (30 x 25), J501 pedal-jack scrap (25 x 24), PS pedal sensor scrap (7 x 5 holes) - every
          hole on the 2.54 lattice with model / local coordinates, the routed underside wires and a route check against SCH-05 / SCH-07;
          J701 headphone jack (no board: it sits in the left cheek pocket of the CAD and the two AUX halves are soldered to its legs).
  BRD-08  control board MB underside wiring (seen from below = mirror image of BRD-01), routes from mbroute.py + check.
  SB      OUT -> J201 point-to-point list (wiring_SB.csv) and the routes drawn on BRD-02.

PJ-313 legs are not on the 2.54 lattice (SHOU HAN PJ-313 5JCJ drawing: legs at 1.8 / 3.2 / 3.5 mm steps, two locating pegs D1.0 6.0
apart - CAD spec keyaction_features_frame.json headphone_jack.jack_dims). So each jack board has a dashed 'jack field' where the legs
go in whatever holes they meet (bend slightly or open the hole to D1.3), and fixed collector pads T / R / S next to it: the board wiring
starts at the collector pads and is fully drawn; only the 3 short leg -> collector links depend on the received jack.
"""
import math

import harness as HN

NETC = {"GND": "#1d2433", "AGND": "#4a5568", "+3V3": "#c0392b", "PED_VCC": "#b86e00", "PED_TIP": "#1f5fbf", "HP_TN_L": "#1f5fbf",
        "HP_RN_R": "#7a3fb0", "AMP_IN_L": "#2e8b57", "AMP_IN_R": "#b0306a", "N1": "#2e8b57", "MUX_SIG": "#b86e00",
        "PED_SEL": "#d4a017"}


def ncol(net):
    if net in NETC:
        return NETC[net]
    if net.startswith("HALL_"):
        return "#1f5fbf"
    if net.startswith("EXT"):
        return "#2e8b57"
    if net.startswith("MUX_S"):
        return "#7a3fb0"
    if net.startswith("ID"):
        return "#8a5a00"
    return "#555"


# ====================================================================== generic route check
def _on_seg(p, a, b, tol=0.01):
    return min(a[0], b[0]) - tol <= p[0] <= max(a[0], b[0]) + tol and min(a[1], b[1]) - tol <= p[1] <= max(a[1], b[1]) + tol


def _on_poly(p, poly):
    return any(_on_seg(p, a, b) for a, b in zip(poly, poly[1:]))


def _same(p, q, tol=0.01):
    return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol


def _seg_cross(a, b, c, d):
    """intersection point of two axis-parallel segments (or None; collinear overlap -> one shared point)."""
    if abs(a[0] - b[0]) < 0.01 and abs(c[1] - d[1]) < 0.01:          # ab vertical, cd horizontal
        p = (a[0], c[1])
    elif abs(a[1] - b[1]) < 0.01 and abs(c[0] - d[0]) < 0.01:        # ab horizontal, cd vertical
        p = (c[0], a[1])
    else:                                                              # parallel: shared point if they touch
        for p in (a, b, c, d):
            if _on_seg(p, a, b) and _on_seg(p, c, d):
                return p
        return None
    return p if (_on_seg(p, a, b) and _on_seg(p, c, d)) else None


def route_check(pads, routes, keep=(), zones=(), bare=()):
    """pads: {(x, y): (ref, pin, net)}; routes: {net: [polyline, ...]} (axis-parallel, model mm); keep: rects (x0, x1, y0, y1) no wire
    may enter; zones: rects no wire may enter either (jack leg fields); bare: {(net, k)} = polyline k of net is tinned BARE wire (soldered
    wherever it meets a pad), every other polyline is an INSULATED strand (joined only at its two stripped ends). Returns problems.
    Rules (rev E review):
      * segments axis-parallel; no wire over a pad of another net; no wire in a keep-out;
      * an insulated strand may not pass over a pad of its own net mid-run either (nothing joins it there) - end the strand on the pad;
      * an insulated strand end joins: the pad under it, the end of another strand there, or a bare wire of its net passing there;
        an end that joins nothing is a problem, an end on another net's bare wire / joint is a short;
      * bare wires of different nets may not touch; bare wires of one net that touch are joined;
      * every net with 2+ pads on the board is ONE group (union-find over the joints above) - nets without wires are checked too."""
    probs = []
    par = {}

    def f(a):
        while par.setdefault(a, a) != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def u(a, b):
        par[f(a)] = f(b)
    W = []                                             # (net, k, poly, is_bare)
    for net, polys in routes.items():
        for k, poly in enumerate(polys):
            W.append((net, k, poly, (net, k) in bare))
    touched = set()
    for wi, (net, k, poly, isb) in enumerate(W):
        f(("w", wi))
        for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
            if abs(x0 - x1) > 0.01 and abs(y0 - y1) > 0.01:
                probs.append("%s: diagonal segment (%.2f,%.2f)-(%.2f,%.2f)" % (net, x0, y0, x1, y1))
            for (a0, a1, b0, b1) in list(keep) + list(zones):
                if max(x0, x1) > a0 and min(x0, x1) < a1 and max(y0, y1) > b0 and min(y0, y1) < b1:
                    probs.append("%s wire enters a keep-out at (%.1f..%.1f, %.1f..%.1f)" % (net, a0, a1, b0, b1))
        ends = (poly[0], poly[-1])
        for (px, py), (ref, pin, pnet) in pads.items():
            if not _on_poly((px, py), poly):
                continue
            if pnet != net:
                probs.append("%s wire crosses %s.%s (%s) at (%.2f,%.2f)" % (net, ref, pin, pnet, px, py))
            elif isb or any(_same((px, py), e) for e in ends):
                u(("w", wi), ("p", (px, py)))
                touched.add((px, py))
            else:
                probs.append("%s insulated strand %d passes over %s.%s mid-run without a joint at (%.2f,%.2f) - end the strand on the pad "
                             "or use tinned bare wire" % (net, k + 1, ref, pin, px, py))
    # strand ends and bare-bare contacts
    for wi, (net, k, poly, isb) in enumerate(W):
        kind = "bare wire" if isb else "strand"
        for e in (poly[0], poly[-1]):
            ok = any(_same(e, p) for p in pads)
            for wj, (net2, k2, poly2, isb2) in enumerate(W):
                if wj == wi or not _on_poly(e, poly2):
                    continue
                at_end = _same(e, poly2[0]) or _same(e, poly2[-1])
                if net2 != net:
                    if isb2 or at_end:
                        probs.append("%s %s %d end (%.2f,%.2f) lands on %s (%s) - short" % (net, kind, k + 1, e[0], e[1], net2,
                                                                                         "bare wire" if isb2 else "strand end"))
                    else:
                        probs.append("%s %s %d end (%.2f,%.2f) lies under the %s strand %d" % (net, kind, k + 1, e[0], e[1], net2, k2 + 1))
                elif isb2 or at_end:
                    u(("w", wi), ("w", wj))
                    ok = True
                else:
                    probs.append("%s %s %d end (%.2f,%.2f) lies on the middle of insulated strand %d - no joint there"
                                 % (net, kind, k + 1, e[0], e[1], k2 + 1))
            if not ok:
                probs.append("%s %s %d end (%.2f,%.2f) joins nothing (no pad, wire end or bare wire)" % (net, kind, k + 1, e[0], e[1]))
        if not isb:
            continue
        for wj in range(wi + 1, len(W)):
            net2, k2, poly2, isb2 = W[wj]
            if not isb2:
                continue
            hit = None
            for a, b in zip(poly, poly[1:]):
                for c, d in zip(poly2, poly2[1:]):
                    hit = hit or _seg_cross(a, b, c, d)
            if hit is None:
                continue
            if net2 != net:
                probs.append("bare %s and bare %s touch at (%.2f,%.2f) - short" % (net, net2, hit[0], hit[1]))
            else:
                u(("w", wi), ("w", wj))
    # one group per net (every net with 2+ pads)
    bynet = {}
    for p, (ref, pin, net) in pads.items():
        if net and net != "NC" and not net.startswith("~"):
            bynet.setdefault(net, []).append((p, ref, pin))
    for net, lst in sorted(bynet.items()):
        if len(lst) < 2:
            continue
        if net not in routes:
            probs.append("net %s has %d pads on the board but no wire" % (net, len(lst)))
            continue
        for p, ref, pin in lst:
            if p not in touched:
                probs.append("pad %s.%s (%s) not reached" % (ref, pin, net))
        groups = {f(("p", p)) for p, ref, pin in lst}
        if len(groups) > 1:
            probs.append("net %s split into %d groups" % (net, len(groups)))
    return probs


def wlen(poly):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(poly, poly[1:]))


# ====================================================================== J702 amp-input board
J7_BOX = tuple(HN.PTS.get("j702_board", {}).get("box", [505.0, 535.0, 255.0, 280.0])[:4])
J7_HOLES = [tuple(h) for h in HN.PTS.get("j702_board", {}).get("holes", [[508.0, 258.0], [532.0, 277.0]])]
J7_JACK = tuple(HN.PTS.get("j702", [517.0, 523.0, 255.0, 269.0])[:4])


def j7x(i):
    return round(J7_BOX[0] + 1.27 + 2.54 * i, 2)


def j7y(j):
    return round(J7_BOX[2] + 1.27 + 2.54 * j, 2)


J7_NI, J7_NJ = 12, 10                      # 30 x 25 -> 12 x 10 holes, edges mid-gap (1.27 from the outer holes)
# pads (ref, pin) -> (i, j). 'J702' T / R / S = collector pads the jack legs are linked to (the legs themselves sit in the jack field)
J7_PADS = {
    ("J702", "T"): (3, 3), ("J702", "R"): (8, 3), ("J702", "S"): (5, 6),
    ("C701", "2"): (3, 4), ("C701", "1"): (3, 6), ("C702", "2"): (2, 4), ("C702", "1"): (2, 6),
    ("C703", "2"): (8, 4), ("C703", "1"): (8, 6), ("C704", "2"): (9, 4), ("C704", "1"): (9, 6),
    ("R701", "1"): (2, 8), ("R701", "2"): (5, 8), ("R702", "1"): (8, 7), ("R702", "2"): (5, 7),
    ("W707", "L"): (3, 9), ("W707", "G"): (5, 9), ("W707", "R"): (8, 9),
}
J7_NET = {("J702", "T"): "HP_TN_L", ("J702", "R"): "HP_RN_R", ("J702", "S"): "AGND",
          ("C701", "2"): "HP_TN_L", ("C702", "2"): "HP_TN_L", ("C701", "1"): "AMP_IN_L", ("C702", "1"): "AMP_IN_L",
          ("C703", "2"): "HP_RN_R", ("C704", "2"): "HP_RN_R", ("C703", "1"): "AMP_IN_R", ("C704", "1"): "AMP_IN_R",
          ("R701", "1"): "AMP_IN_L", ("R701", "2"): "AGND", ("R702", "1"): "AMP_IN_R", ("R702", "2"): "AGND",
          ("W707", "L"): "AMP_IN_L", ("W707", "G"): "AGND", ("W707", "R"): "AMP_IN_R"}


def _p7(i, j):
    return (j7x(i), j7y(j))


J7_ROUTES = {
    "HP_TN_L": [[_p7(3, 3), _p7(3, 4), _p7(2, 4)]],
    "HP_RN_R": [[_p7(8, 3), _p7(8, 4), _p7(9, 4)]],
    "AMP_IN_L": [[_p7(2, 6), _p7(3, 6)], [_p7(2, 6), _p7(2, 8)], [_p7(3, 6), _p7(3, 9)]],
    "AMP_IN_R": [[_p7(8, 6), _p7(9, 6)], [_p7(8, 6), _p7(8, 7)], [_p7(8, 7), _p7(8, 9)]],     # C703.1 -> R702.1 -> W707 R (two pieces)
    "AGND": [[_p7(5, 6), _p7(5, 9)]],
}
# short bridges / spine = tinned bare wire (soldered at every pad it passes); the rest = insulated strands joined only at their ends
J7_BARE = {("HP_TN_L", 0), ("HP_RN_R", 0), ("AMP_IN_L", 0), ("AMP_IN_R", 0), ("AMP_IN_R", 1), ("AGND", 0)}
J7_FIELD = (j7x(4) - 1.27, j7x(7) + 1.27, J7_BOX[2], j7y(5) + 1.27)                            # jack leg field (no board wiring)
J7_POSTS = [(hx - 3.5, hx + 3.5, hy - 3.5, hy + 3.5) for hx, hy in J7_HOLES]                   # 5 mm posts under the screws (+0.5)


def j7_pads():
    return {_p7(*ij): (ref, pin, J7_NET[(ref, pin)]) for (ref, pin), ij in J7_PADS.items()}


def j7_check():
    import sheets
    probs = route_check(j7_pads(), J7_ROUTES, keep=J7_POSTS, zones=[J7_FIELD], bare=J7_BARE)
    # the board pads must carry exactly the SCH-07 nets (J702 board refs)
    s = sheets.sch07()
    s.connectivity()
    pin_net = {p: n for n, ps in s.nets.items() for p in ps}
    for (ref, pin), net in J7_NET.items():
        if ref == "W707":
            continue
        sn = pin_net.get("%s.%s" % (ref, pin))
        if sn != net:
            probs.append("BRD-07 J702 pad %s.%s = %s but SCH-07 says %s" % (ref, pin, net, sn))
    for p in ("J702.TN", "J702.RN"):
        sn = pin_net.get(p, "")
        if sn and not sn.startswith("~"):
            probs.append("SCH-07 %s is connected (%s) but BRD-07 leaves it empty" % (p, sn))
    return probs


# ====================================================================== J501 pedal-jack scrap (no parts besides the jack)
J5_BOX = tuple(HN.PTS.get("j501_board", [450.0, 475.0, 316.5, 340.5])[:4])
J5_JACK = tuple(HN.PTS.get("j501", [459.5, 465.5, 328.5, 342.5])[:4])


def j5x(i):
    return round(J5_BOX[0] + 1.27 + 2.54 * i, 2)


def j5y(j):
    return round(J5_BOX[2] + 1.27 + 2.54 * j, 2)


J5_NI, J5_NJ = 9, 9                        # 25 x 24 -> 9 x 9 holes (x451.27~471.59, y317.77~338.09)
J5_PADS = {("J502w", "1 T"): (3, 0), ("J502w", "2 TN"): (4, 0), ("J502w", "3 R"): (5, 0), ("J502w", "4 S"): (6, 0)}
J5_NET = {"1 T": "PED_TIP", "2 TN": "GND", "3 R": "PED_VCC", "4 S": "GND"}
J5_FIELD = (j5x(3) - 1.27, j5x(6) + 1.27, j5y(4) - 1.27, J5_BOX[3])


# ====================================================================== PS pedal sensor scrap (local frame, origin = lower-left hole)
def psx(c):
    return round(2.54 * c, 2)


def psy(r):
    return round(2.54 * r, 2)


# U551 lies face up (marked face toward the pedal magnet) with its leads toward +x: then pin 1 (VCC) is at -y, as on the SB (BRD-02 note 2)
PS_PADS = {("U551", "1"): (2, 1), ("U551", "2"): (2, 2), ("U551", "3"): (2, 3), ("C551", "1"): (3, 1), ("C551", "2"): (3, 2),
           ("R551", "2"): (3, 3), ("R551", "1"): (6, 3), ("P501", "T"): (6, 4), ("P501", "R"): (6, 1), ("P501", "S"): (6, 2)}
PS_NET = {("U551", "1"): "PED_VCC", ("U551", "2"): "GND", ("U551", "3"): "N1", ("C551", "1"): "PED_VCC", ("C551", "2"): "GND",
          ("R551", "2"): "N1", ("R551", "1"): "PED_TIP", ("P501", "T"): "PED_TIP", ("P501", "R"): "PED_VCC", ("P501", "S"): "GND"}
PS_ROUTES = {"PED_VCC": [[(psx(2), psy(1)), (psx(6), psy(1))]], "GND": [[(psx(2), psy(2)), (psx(6), psy(2))]],
             "N1": [[(psx(2), psy(3)), (psx(3), psy(3))]], "PED_TIP": [[(psx(6), psy(3)), (psx(6), psy(4))]]}


PS_BARE = {(n, 0) for n in PS_ROUTES}       # all four PS links are short tinned bare wires


def ps_pads():
    return {(psx(c), psy(r)): (ref, pin, PS_NET[(ref, pin)]) for (ref, pin), (c, r) in PS_PADS.items()}


def ps_check():
    import sheets
    probs = route_check(ps_pads(), PS_ROUTES, bare=PS_BARE)
    s = sheets.sch05()
    s.connectivity()
    pin_net = {p: n for n, ps in s.nets.items() for p in ps}
    # N1 = the schematic's anonymous net between U551.3 and R551.2
    for (ref, pin), net in PS_NET.items():
        sn = pin_net.get("%s.%s" % (ref, pin), "")
        want = net if net != "N1" else None
        if want and sn != want:
            probs.append("BRD-07 PS pad %s.%s = %s but SCH-05 says %s" % (ref, pin, net, sn))
        if net == "N1" and not sn.startswith("~"):
            probs.append("BRD-07 PS pad %s.%s should be the U551 OUT - R551 net, SCH-05 says %s" % (ref, pin, sn))
    return probs


# ====================================================================== SB: OUT -> J201
# W1 r4.5 P36 (geometry.json plan): the SB lies on its support ribs (top z7.0 = board underside) - front rib y61.0~62.8 and rear rib
# y73.2~75.5 over x6.0~158.5, the rear rib open only at x59.0~82.0 (ribbon gap). No underside wire may lie on a rib: wires cross the rear
# band y73.2~75.5 only inside the gap (wire centre >= 0.5 from the gap edges = about half a 1 mm insulated strand).
SB_RIBS = [(6.0, 158.5, 61.0, 62.8), (6.0, 59.0, 73.2, 75.5), (82.0, 158.5, 73.2, 75.5)]
SB_RIB_KEEP = [(a0 - 0.5, a1 + 0.5, b0 - 0.5, b1 + 0.5) for (a0, a1, b0, b1) in SB_RIBS]


def sb_rows():
    """12 OUT wires of the sensor board (BRD-02): OUT hole (lead column, y69.54) -> J201 pin. All run along the half-pitch lane y70.81
    (between the OUT row and the J201 front row, clear of both ribs). Odd pins = front row y72.08: drop from the lane onto the pin.
    Even pins = back row y74.62: leave the lane at the half-pitch column right beside the target pin (xp -/+ 1.27, between two front-row
    pins), cross the front row there, take the half-pitch lane y73.35 for 1.27 and rise onto the pin - so the wire is inside the rear-rib
    band y73.2~75.5 only within the ribbon gap x59~82 (rev E review 2: the old even-pin lane y73.35 ran on the rib over most of the board).
    Pin x = 61.59 + 2.54 * floor((n - 1) / 2)."""
    import sheets as S
    cols = [0.63 + 2.54 * i for i in range(1, 65)]
    rows = []
    for i, (k, xk) in enumerate(zip(S.KEYS, S.SENSOR_X)):
        xo = round(min(c for c in cols if c >= xk + 3.0), 2)
        net = S.NET[k]
        n = S.RIBBON.index(net) + 1
        xp = round(61.59 + 2.54 * ((n - 1) // 2), 2)
        yp = 72.08 if n % 2 else 74.62
        if n % 2:
            poly = [(xo, 69.54), (xo, 70.81), (xp, 70.81), (xp, 72.08)]
        else:
            xc = round(xp - 1.27 if xo < xp else xp + 1.27, 2)
            poly = [(xo, 69.54), (xo, 70.81), (xc, 70.81), (xc, 73.35), (xp, 73.35), (xp, 74.62)]
        rows.append(dict(u="U%d" % (201 + i), key=k, net=net, pin=n, xo=xo, yo=69.54, xp=xp, yp=yp, poly=poly, length=wlen(poly)))
    return rows


# J201 power pins 1 / 16 (+3V3) and 2 / 15 (GND) -> the sensor buses (rev E review: without these four links the ribbon brings 3V3 / GND
# to J201 but nothing joins J201 to the buses). Insulated strands on half-pitch lanes / free columns: they cross the OUT lanes y70.81 /
# y73.35 and the bare GND bus between holes (3V3 links), never over another net's pad, and end in an empty bus hole (the stripped end
# is soldered there together with the bus wire).
SB_BUS = {"+3V3": [(8.25, 64.46), (160.65, 64.46)], "GND": [(8.25, 67.00), (160.65, 67.00)]}   # tinned bare buses (BRD-02)
_J1X = 61.59                          # J201 column 1 (pins 1 / 2)
_J8X = round(61.59 + 2.54 * 7, 2)     # J201 column 8 (pins 15 / 16) = 79.37


def sb_pwr_rows():
    """J201.1 / .15 (front row, y72.08 - below the rear rib) go out sideways along the front row; J201.2 / .16 (back row, on the rib band)
    first drop through the gap on the half-pitch column next to J201 (x60.32 / x80.64, inside x59~82) and only then turn."""
    h = 1.27
    links = [
        (1, "+3V3", [(_J1X, 72.08), (_J1X - 3 * h, 72.08), (_J1X - 3 * h, 65.73), (_J1X - 4 * h, 65.73), (_J1X - 4 * h, 64.46)]),
        (2, "GND", [(_J1X, 74.62), (_J1X - h, 74.62), (_J1X - h, 68.27), (_J1X - 2 * h, 68.27), (_J1X - 2 * h, 67.00)]),
        (15, "GND", [(_J8X, 72.08), (_J8X + 4 * h, 72.08), (_J8X + 4 * h, 67.00)]),
        (16, "+3V3", [(_J8X, 74.62), (_J8X + h, 74.62), (_J8X + h, 65.73), (_J8X, 65.73), (_J8X, 64.46)]),
    ]
    rows = []
    for n, net, poly in links:
        poly = [(round(x, 2), round(y, 2)) for x, y in poly]
        bus = "3V3 버스" if net == "+3V3" else "GND 버스"
        rows.append(dict(u=bus, key="—", net=net, pin=n, xo=poly[-1][0], yo=poly[-1][1], xp=poly[0][0], yp=poly[0][1],
                         poly=list(reversed(poly)), length=wlen(poly)))
    return rows


def sb_pads():
    import sheets as S
    pads = {}
    cols = [0.63 + 2.54 * i for i in range(1, 65)]
    for i, (k, xk) in enumerate(zip(S.KEYS, S.SENSOR_X)):
        xo = round(min(c for c in cols if c >= xk + 3.0), 2)
        pads[(xo, 64.46)] = ("U%d" % (201 + i), "1", "+3V3")
        pads[(xo, 67.00)] = ("U%d" % (201 + i), "2", "GND")
        pads[(xo, 69.54)] = ("U%d" % (201 + i), "3", S.NET[k])
    for n in range(1, 17):
        pads[(round(61.59 + 2.54 * ((n - 1) // 2), 2), 72.08 if n % 2 else 74.62)] = ("J201", str(n), S.RIBBON[n - 1])
    for x, ref in ((8.25, "C213"), (158.11, "C214")):
        pads[(x, 64.46)] = (ref, "1", "+3V3")
        pads[(x, 67.00)] = (ref, "2", "GND")
    return pads


def sb_routes():
    """(routes, bare): the 12 OUT strands, the 4 power strands and the two bare buses - every net on the SB is checked."""
    routes, bare = {}, set()
    for net, poly in SB_BUS.items():
        routes.setdefault(net, []).append(poly)
        bare.add((net, len(routes[net]) - 1))
    for r in sb_rows() + sb_pwr_rows():
        routes.setdefault(r["net"], []).append(r["poly"])
    return routes, bare


def sb_check():
    routes, bare = sb_routes()
    # U-notch holes for the M3 screws at (3.0, 61.9) / (3.0, 74.6), D3.4 + 0.5; the support ribs under the board (W1 P36)
    keep = [(3.0 - 2.2, 3.0 + 2.2, 61.9 - 2.2, 61.9 + 2.2), (3.0 - 2.2, 3.0 + 2.2, 74.6 - 2.2, 74.6 + 2.2)] + SB_RIB_KEEP
    probs = route_check(sb_pads(), routes, keep=keep, bare=bare)
    # SCH-02: J201 power pins must sit on the nets the ribbon carries
    import sheets as S
    for r in sb_pwr_rows():
        if S.RIBBON[r["pin"] - 1] != r["net"]:
            probs.append("J201.%d link drawn as %s but the ribbon carries %s" % (r["pin"], r["net"], S.RIBBON[r["pin"] - 1]))
    return probs


def draw_sb_routes(s, X, Y):
    """BRD-02 overlay: the support ribs (dashed bands), the 12 OUT wires (underside, dashed blue) + the 4 J201 power links (dashed red =
    3V3, black = GND). Wires bundled on lane y70.81 are drawn 0.1 mm apart so each stays visible (the lane itself is the half-pitch line
    given in wiring_SB.csv)."""
    o = s.out["body"]
    for (a0, a1, b0, b1) in SB_RIBS:            # support ribs under the board (W1 P36): no underside wire on them
        o.append(f'<rect x="{X(a0):.2f}" y="{Y(b1):.2f}" width="{(a1-a0)*2.2:.2f}" height="{(b1-b0)*2.2:.2f}" fill="#6b7690" fill-opacity=".10" '
                 f'stroke="#6b7690" stroke-width=".25" stroke-dasharray="1.0 .6"/>')
    rows = sb_rows()
    for k, r in enumerate(rows):
        dy = (k - 5.5) * 0.10                   # wires bundled on lane y70.81 drawn 0.1 apart so each stays visible
        d = " ".join("%.2f,%.2f" % (X(x), Y(y + (dy if abs(y - 70.81) < 0.01 else 0))) for x, y in r["poly"])
        o.append(f'<polyline points="{d}" fill="none" stroke="#1f5fbf" stroke-width=".35" stroke-dasharray="1.1 .5" stroke-opacity=".9"/>')
    for r in sb_pwr_rows():
        d = " ".join("%.2f,%.2f" % (X(x), Y(y)) for x, y in r["poly"])
        o.append(f'<polyline points="{d}" fill="none" stroke="{ncol(r["net"])}" stroke-width=".5" stroke-dasharray="1.1 .5" stroke-opacity=".95"/>')
        x, y = r["poly"][0]
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".75" fill="none" stroke="{ncol(r["net"])}" stroke-width=".35"/>')


# ====================================================================== BRD-07
def brd07():
    from sheets import TOTAL, REV_E
    from sch import Sheet
    s = Sheet("BRD-07", 14, TOTAL, "작은 기판 (J702 · J501 · PS) + 헤드폰 잭 J701",
              "모든 구멍 = 2.54 격자(기판 모서리는 구멍 사이 가운데). 배선은 아랫면. 잭 다리는 격자에 맞지 않아 점선 칸(잭 자리)에 꽂고 T·R·S 모음 패드까지 짧게 잇는다.",
              "J702 · J501 · PS · J701", qty="각 1", basis="SCH-05 · SCH-07 · CAD", **REV_E)
    o = s.out["body"]
    s.board_check = []

    def holes(X, Y, xs, ys, skip=()):
        for x in xs:
            for y in ys:
                if any(a0 <= x <= a1 and b0 <= y <= b1 for (a0, a1, b0, b1) in skip):
                    o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".45" fill="#e3ebe1"/>')
                else:
                    o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".5" fill="#b9cdb6"/>')

    def pad(X, Y, x, y, net, r=1.15, sq=False):
        c = ncol(net)
        if sq:
            o.append(f'<rect x="{X(x)-1.4:.2f}" y="{Y(y)-1.4:.2f}" width="2.8" height="2.8" fill="#fff" stroke="{c}" stroke-width=".6"/>')
        else:
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{r}" fill="{c}" stroke="#1f2a44" stroke-width=".25"/>')

    def wires(X, Y, routes, bare=()):
        for net, polys in routes.items():
            for k, poly in enumerate(polys):
                b = (net, k) in bare
                d = " ".join("%.2f,%.2f" % (X(x), Y(y)) for x, y in poly)
                dash = "" if b else ' stroke-dasharray="1.4 .7"'
                o.append(f'<polyline points="{d}" fill="none" stroke="{ncol(net)}" stroke-width="{1.0 if b else 0.6}" stroke-linecap="round" '
                         f'stroke-linejoin="round" stroke-opacity=".85"{dash}/>')

    # ------------------------------------------------------------ J702 board, 3 : 1, top view (front -y at the bottom)
    S3 = 3.0
    x0b, x1b, y0b, y1b = J7_BOX
    ox, oy = 26.0, 34.0

    def X7(x):
        return ox + (x - x0b) * S3

    def Y7(y):
        return oy + (y1b - y) * S3
    s.text(ox - 6.0, oy - 6.5, "J702 앰프 입력 기판 (12 × 18 자투리 30 × 25, 3 : 1, 위에서 봄)", "noteb", size=2.6)
    o.append(f'<rect x="{X7(x0b):.2f}" y="{Y7(y1b):.2f}" width="{(x1b-x0b)*S3:.2f}" height="{(y1b-y0b)*S3:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    for (a0, a1, b0, b1) in J7_POSTS:
        o.append(f'<rect x="{X7(a0+0.5):.2f}" y="{Y7(b1-0.5):.2f}" width="{6*S3:.2f}" height="{6*S3:.2f}" fill="#c9d0da" fill-opacity=".35" '
                 f'stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.2 .7"/>')
    holes(X7, Y7, [j7x(i) for i in range(J7_NI)], [j7y(j) for j in range(J7_NJ)], skip=J7_POSTS)
    for (hx, hy) in J7_HOLES:
        o.append(f'<circle cx="{X7(hx):.2f}" cy="{Y7(hy):.2f}" r="{1.6*S3:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".4"/>')
    fx0, fx1, fy0, fy1 = J7_FIELD
    o.append(f'<rect x="{X7(fx0):.2f}" y="{Y7(fy1):.2f}" width="{(fx1-fx0)*S3:.2f}" height="{(fy1-fy0)*S3:.2f}" fill="#fff6db" fill-opacity=".6" '
             f'stroke="#b86e00" stroke-width=".4" stroke-dasharray="1.6 .8"/>')
    jx0, jx1, jy0, jy1 = J7_JACK
    o.append(f'<rect x="{X7(jx0):.2f}" y="{Y7(jy1):.2f}" width="{(jx1-jx0)*S3:.2f}" height="{(jy1-jy0-2.5)*S3:.2f}" fill="#222" fill-opacity=".55"/>')
    o.append(f'<rect x="{X7((jx0+jx1)/2-2.5):.2f}" y="{Y7(jy0+2.5):.2f}" width="{5*S3:.2f}" height="{2.5*S3:.2f}" fill="#222" fill-opacity=".4"/>')
    s.text(X7((jx0 + jx1) / 2), Y7(262.5), "J702", "ref", "middle", size=2.4, check=False)
    s.text(X7((jx0 + jx1) / 2), Y7(262.5) + 2.8, "PJ-313", "notes", "middle", size=1.8, check=False)
    s.text(X7(fx1) + 1.0, Y7(256.6), "← 잭 자리 (점선, 다리 5개)", "notes", "start", size=1.7, check=False)
    # caps (radial, standing) and resistors (lying 7.62)
    for ref in ("C701", "C702", "C703", "C704"):
        (x1, y1_), (x2, y2_) = _p7(*J7_PADS[(ref, "1")]), _p7(*J7_PADS[(ref, "2")])
        o.append(f'<rect x="{X7(x1)-1.25:.2f}" y="{Y7(max(y1_, y2_))+1.4:.2f}" width="2.5" height="{abs(y1_-y2_)*S3-2.8:.2f}" rx=".9" '
                 f'fill="#f3e3c3" fill-opacity=".85" stroke="#8a5a00" stroke-width=".3"/>')
    for ref in ("R701", "R702"):
        (x1, y1_), (x2, y2_) = _p7(*J7_PADS[(ref, "1")]), _p7(*J7_PADS[(ref, "2")])
        o.append(f'<rect x="{X7(min(x1, x2))+1.6:.2f}" y="{Y7(y1_)-1.25:.2f}" width="{abs(x1-x2)*S3-3.2:.2f}" height="2.5" rx=".8" '
                 f'fill="#f3e3c3" fill-opacity=".85" stroke="#8a5a00" stroke-width=".3"/>')
    wires(X7, Y7, J7_ROUTES, J7_BARE)
    for (ref, pin), ij in J7_PADS.items():
        x, y = _p7(*ij)
        pad(X7, Y7, x, y, J7_NET[(ref, pin)], sq=ref in ("J702", "W707"))
    # leg -> collector links (depend on the received jack): dashed amber from the field edge
    for (pin, tgt) in (("T", (3, 3)), ("R", (8, 3)), ("S", (5, 6))):
        tx, ty = _p7(*tgt)
        sx_ = fx0 if pin == "T" else (fx1 if pin == "R" else tx)
        sy_ = ty if pin != "S" else fy1
        o.append(f'<line x1="{X7(sx_):.2f}" y1="{Y7(sy_):.2f}" x2="{X7(tx):.2f}" y2="{Y7(ty):.2f}" stroke="#b86e00" stroke-width=".6" stroke-dasharray=".8 .6"/>')
    labs = [("T", (3, 3), -2.6, 0.8, "end"), ("R", (8, 3), 2.6, 0.8, "start"), ("S", (5, 6), 2.4, 3.6, "start"),
            ("C702", (2, 5), -2.2, 0.8, "end"), ("C701", (3, 5), 1.8, 0.8, "start"), ("C703", (8, 5), -1.8, 0.8, "end"),
            ("C704", (9, 5), 2.2, 0.8, "start"), ("R701", (3.5, 8), 0.0, -2.0, "middle"), ("R702", (6.5, 7), 0.0, -2.0, "middle"),
            ("L", (3, 9), 0.0, 4.4, "middle"), ("G", (5, 9), 0.0, 4.4, "middle"), ("R", (8, 9), 0.0, 4.4, "middle")]
    for t, (i, j), dx, dy, a in labs:
        s.text(X7(j7x(i)) + dx, Y7(j7y(j)) + dy, t, "pinnum" if len(t) == 1 else "ref", a, size=1.9 if len(t) == 1 else 2.0, check=False)
    s.text(X7(j7x(5)), Y7(y1b) - 1.6, "W707 → 앰프 IN (L · G · R)", "cabt", "middle", size=1.9, check=False)
    s.text(X7(j7x(5.5)), Y7(y0b) + 4.0, "앞 (−y) · 잭 코 → W702 플러그", "notes", "middle", size=1.9, check=False)
    for i in (0, 3, 5, 8, 11):
        s.text(X7(j7x(i)), Y7(y0b) + 8.0, "%.2f" % j7x(i), "tblm", "middle", size=1.55, check=False)
    for j in (0, 3, 6, 9):
        s.text(X7(x0b) - 1.5, Y7(j7y(j)) + 0.6, "%.2f" % j7y(j), "tblm", "end", size=1.55, check=False)
    for (hx, hy) in J7_HOLES:
        s.text(X7(hx), Y7(hy) + (7.4 if hy < 270 else -6.0), "Ø3.2 (%g, %g)" % (hx, hy), "notes", "middle", size=1.7, check=False)
    s.regions["j702"] = (14.0, 24.0, 124.0, Y7(y0b) + 10.0)
    # J702 tables
    rows = []
    for (ref, pin), ij in J7_PADS.items():
        x, y = _p7(*ij)
        rows.append(["%s.%s" % (ref, pin) if ref not in ("J702", "W707") else ("J702 %s 모음" % pin if ref == "J702" else "W707 %s" % pin),
                     J7_NET[(ref, pin)], "%d, %d" % ij, "%.2f" % x, "%.2f" % y])
    yt = s.table(128, 24, ["패드", "넷", "i, j", "x", "y"], rows, [22, 18, 10, 13, 13],
                 title="J702 구멍 (x = 506.27 + 2.54·i, y = 256.27 + 2.54·j)", mono_cols=(0, 1, 2, 3, 4), rh=2.75)
    wr = []
    for net, polys in J7_ROUTES.items():
        for k, poly in enumerate(polys):
            wr.append([net, " → ".join("(%.2f, %.2f)" % p for p in poly), "%.1f" % wlen(poly), "맨선" if (net, k) in J7_BARE else "피복"])
    yt2 = s.table(206, 24, ["넷", "경로 (모델 좌표)", "길이", "선"], wr, [17, 145, 10, 10],
                  title="J702 아랫면 배선", mono_cols=(0, 1, 2), rh=2.75)
    p7 = j7_check()
    s.board_check += ["J702: " + p for p in p7]
    s.para(206, yt2 + 3.5, [
        "J702 배선 검사: SCH-07 넷과 같고, 넷마다 한 덩어리(피복은 두 끝에서만 이음), 다른 넷 패드·기둥·잭 자리를 안 지남 (문제 %d)" % len(p7),
        "1. 잭 다리 → 모음 패드: T 다리 → T 모음(513.89, 263.89), R 다리 → R 모음(526.59, 263.89), S 다리 → S 모음(518.97, 271.51).",
        "    다리가 닿는 구멍에서 가장 짧게 피복 가닥(리본 1가닥)으로. TN·RN 다리는 고정용으로만 납땜하고 아무 데도 잇지 않는다.",
        "    헤드폰을 꽂아도 앰프 입력이 끊기지 않게 J702는 T·R·S만 쓴다(노멀은 J701에서만 씀).",
        "2. 1 µF ×2를 한 채널에 나란히(C701·C702, C703·C704 — 몸통이 닿아도 됨), 1 kΩ은 출력 → AGND(S·G 줄).",
        "3. 순서: 저항·콘덴서 → 아랫면 맨선(실선: 짧은 다리·AGND 줄, 지나는 패드마다 납땜) → △28 피복선(점선, 두 끝만) → 잭 → 모음 패드 링크 → W707(차폐 = G).",
        "4. 확인: T 모음–L 패드 사이 열림(콘덴서), C703.1–R702.1–W707 R 패드 0 Ω, L–G = 1 kΩ, R–G = 1 kΩ, S 모음–G = 0 Ω.",
    ], "notes", size=1.85, lh=2.55)
    # ------------------------------------------------------------ J501 scrap, 3 : 1
    x0b, x1b, y0b, y1b = J5_BOX
    ox5, oy5 = 26.0, 140.0

    def X5(x):
        return ox5 + (x - x0b) * S3

    def Y5(y):
        return oy5 + (y1b - y) * S3
    s.text(ox5 - 6.0, oy5 - 6.5, "J501 페달 잭 조각 (12 × 18 자투리 25 × 24, 3 : 1, 위에서 봄)", "noteb", size=2.6)
    o.append(f'<rect x="{X5(x0b):.2f}" y="{Y5(y1b):.2f}" width="{(x1b-x0b)*S3:.2f}" height="{(y1b-y0b)*S3:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    holes(X5, Y5, [j5x(i) for i in range(J5_NI)], [j5y(j) for j in range(J5_NJ)])
    fx0, fx1, fy0, fy1 = J5_FIELD
    o.append(f'<rect x="{X5(fx0):.2f}" y="{Y5(fy1):.2f}" width="{(fx1-fx0)*S3:.2f}" height="{(fy1-fy0)*S3:.2f}" fill="#fff6db" fill-opacity=".6" '
             f'stroke="#b86e00" stroke-width=".4" stroke-dasharray="1.6 .8"/>')
    jx0, jx1, jy0, jy1 = J5_JACK
    o.append(f'<rect x="{X5(jx0):.2f}" y="{Y5(min(jy1, y1b + 2.0)):.2f}" width="{(jx1-jx0)*S3:.2f}" height="{(min(jy1, y1b+2.0)-jy0)*S3:.2f}" fill="#222" fill-opacity=".55"/>')
    s.text(X5((jx0 + jx1) / 2), Y5(333.0), "J501", "ref", "middle", size=2.4, check=False)
    s.text(X5(fx1) + 1.5, Y5(fy1 - 3.0), "잭 자리 · 코 → 뒤판 Ø6 (+y)", "notes", "start", size=1.75, check=False)
    for (ref, pin), ij in J5_PADS.items():
        x, y = j5x(ij[0]), j5y(ij[1])
        pad(X5, Y5, x, y, J5_NET[pin], sq=True)
        s.text(X5(x), Y5(y) + 4.6, pin.split()[1], "pinnum", "middle", size=1.8, check=False)
        o.append(f'<line x1="{X5(x):.2f}" y1="{Y5(fy0):.2f}" x2="{X5(x):.2f}" y2="{Y5(y):.2f}" stroke="#b86e00" stroke-width=".6" stroke-dasharray=".8 .6"/>')
    s.text(X5(j5x(4.5)), Y5(y0b) + 8.4, "앞 (−y) → W502 4가닥 → PB J502 1·2·3·4", "cabt", "middle", size=1.9, check=False)
    s.regions["j501"] = (14.0, oy5 - 10.0, 124.0, Y5(y0b) + 11.0)
    rows5 = [["W502 %s" % pin, J5_NET[pin], "%d, %d" % ij, "%.2f" % j5x(ij[0]), "%.2f" % j5y(ij[1])] for (ref, pin), ij in J5_PADS.items()]
    yt5 = s.table(128, 134, ["패드", "넷", "i, j", "x", "y"], rows5, [18, 17, 10, 13, 13],
                  title="J501 조각 구멍 (x = 451.27 + 2.54·i, y = 317.77 + 2.54·j)", mono_cols=(0, 1, 2, 3, 4), rh=2.75)
    s.para(128, yt5 + 3.5, [
        "1. 잭 다리 T·TN·R·S → 같은 글자의 앞 패드까지 피복 가닥",
        "    (점선, 받은 잭 다리에서 가장 짧게). RN은 고정용으로만 납땜.",
        "2. W502 4가닥을 앞 패드에 아랫면에서 납땜 → PB J502 1·2·3·4.",
        "3. 뒤판 출력물 잭 선반(윗면 z36.4)에 MS 폴리머 (나사 없음).",
        "4. 확인: 플러그 없이 T–TN 0 Ω, 페달 플러그를 꽂으면 열림.",
    ], "notes", size=1.85, lh=2.55)
    # ------------------------------------------------------------ PS pedal sensor scrap, 4 : 1 (local frame)
    S4 = 4.0
    oxp, oyp = 136.0, 226.0

    def XP(x):
        return oxp + x * S4

    def YP(y):
        return oyp - y * S4
    s.text(oxp - 6.0, oyp - 12.7 * S4 + 0.5, "PS 페달 센서 조각 (7 × 5 구멍, 4 : 1, 로컬 mm)", "noteb", size=2.6)
    o.append(f'<rect x="{XP(-1.27):.2f}" y="{YP(11.43):.2f}" width="{17.78*S4:.2f}" height="{12.7*S4:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    holes(XP, YP, [psx(c) for c in range(7)], [psy(r) for r in range(5)])
    o.append(f'<rect x="{XP(-1.0):.2f}" y="{YP(7.0):.2f}" width="{4.0*S4:.2f}" height="{4.0*S4:.2f}" fill="#222" fill-opacity=".55"/>')
    s.text(XP(1.0), YP(9.6), "U551 표시면 위", "notes", "middle", size=1.8, check=False)
    for ly, py in ((3.81, psy(1)), (5.08, psy(2)), (6.35, psy(3))):
        o.append(f'<polyline points="{XP(3.0):.2f},{YP(ly):.2f} {XP(3.6):.2f},{YP(ly):.2f} {XP(psx(2)):.2f},{YP(py):.2f}" fill="none" stroke="#777" stroke-width=".4"/>')
    (x1, y1_), (x2, y2_) = (psx(3), psy(3)), (psx(6), psy(3))
    o.append(f'<rect x="{XP(x1)+1.8:.2f}" y="{YP(y1_)-1.3:.2f}" width="{(x2-x1)*S4-3.6:.2f}" height="2.6" rx=".8" fill="#f3e3c3" fill-opacity=".85" stroke="#8a5a00" stroke-width=".3"/>')
    o.append(f'<rect x="{XP(psx(3))-1.0:.2f}" y="{YP(psy(2))+1.2:.2f}" width="2.0" height="{2.54*S4-2.4:.2f}" fill="none" stroke="#b86e00" stroke-width=".4" stroke-dasharray=".9 .5"/>')
    wires(XP, YP, PS_ROUTES, {(n, 0) for n in PS_ROUTES})
    for (ref, pin), (c, r) in PS_PADS.items():
        pad(XP, YP, psx(c), psy(r), PS_NET[(ref, pin)], sq=ref == "P501")
    for t, x, y, a in (("VCC 1", psx(2), psy(1), "end"), ("GND 2", psx(2), psy(2), "end"), ("OUT 3", psx(2), psy(3), "end")):
        s.text(XP(x) - 1.8, YP(y) - 1.6, t, "pinnum", a, size=1.7, check=False)
    for t, (c, r) in (("링 R", (6, 1)), ("슬리브 S", (6, 2)), ("팁 T", (6, 4))):
        s.text(XP(psx(c)) + 2.6, YP(psy(r)) + 0.7, t, "pinnum", "start", size=1.8, check=False)
    s.text(XP(psx(4.5)), YP(psy(3)) - 2.4, "R551 1 kΩ", "ref", "middle", size=1.9, check=False)
    s.text(XP(psx(3)) + 1.8, YP(psy(1.5)) + 0.7, "C551", "ref", "start", size=1.8, check=False)
    s.text(XP(-1.27), YP(-1.27) + 4.0, "원점 = 왼쪽 아래 구멍 (0, 0) · 구멍 x = 2.54·c, y = 2.54·r", "notes", "start", size=1.75, check=False)
    s.regions["ps"] = (oxp - 8.0, YP(12.7) - 4.0, oxp + 17.78 * S4 + 30.0, YP(-1.27) + 6.0)
    pp = ps_check()
    s.board_check += ["PS: " + p for p in pp]
    rowsp = [["%s.%s" % (ref, pin) if ref != "P501" else "W501 %s" % pin, PS_NET[(ref, pin)].replace("N1", "U551 OUT–R551"), "%d, %d" % cr,
              "%.2f" % psx(cr[0]), "%.2f" % psy(cr[1])] for (ref, pin), cr in PS_PADS.items()]
    ytp = s.table(214, 170, ["패드", "넷", "c, r", "x", "y"], rowsp, [16, 26, 9, 10, 10],
                  title="PS 구멍 (로컬)", mono_cols=(0, 2, 3, 4), rh=2.75)
    s.para(214, ytp + 3.5, [
        "PS 배선 검사: SCH-05와 같음 (문제 %d)" % len(pp),
        "아랫면 맨선: VCC 줄 r1, GND 줄 r2,",
        "OUT → R551 (c2 → c3), 팁 (c6 r3 → r4).",
        "C551 1206 = 아랫면 c3의 r1–r2 사이.",
        "U551 리드 1·2·3 = c2 r1·r2·r3",
        "(표시면 위, 리드 +x → 1번이 −y, SB와 같음).",
        "W501: 팁 → c6 r4, 링 → c6 r1, 슬리브 → c6 r2.",
        "크기·구멍은 이 그림대로 — 페달 바닥판에",
        "붙일 자리만 현장에서 정함(MS 폴리머).",
    ], "notes", size=1.85, lh=2.55)
    # ------------------------------------------------------------ J701 headphone jack (no board): side section of the cheek pocket
    oxj, oyj, Sj = 264.0, 104.0, 2.0        # y (model) -> right, z -> up

    def XJ(y):
        return oxj + y * Sj

    def ZJ(z):
        return oyj + (22.6 - z) * Sj
    s.text(oxj - 4.0, oyj - 14.0, "J701 헤드폰 잭 — 왼쪽 볼 포켓 (기판 없음, 2 : 1, 옆 단면 y–z)", "noteb", size=2.6)
    cav, slot, chan = (2.5, 14.2, 17.4, 22.6), (2.5, 14.2, 3.0, 17.4), (14.2, 40.0, 3.0, 8.0)
    o.append(f'<rect x="{XJ(0):.2f}" y="{ZJ(26.0):.2f}" width="{40*Sj:.2f}" height="{23.0*Sj:.2f}" fill="#f1f3f6" stroke="#b6bfcc" stroke-width=".3"/>')
    for (a0, a1, b0, b1) in (cav, slot, chan):
        o.append(f'<rect x="{XJ(a0):.2f}" y="{ZJ(b1):.2f}" width="{(a1-a0)*Sj:.2f}" height="{(b1-b0)*Sj:.2f}" fill="#fff" stroke="#8a96ab" stroke-width=".3"/>')
    o.append(f'<rect x="{XJ(2.5):.2f}" y="{ZJ(22.5):.2f}" width="{11.5*Sj:.2f}" height="{5.0*Sj:.2f}" fill="#222" fill-opacity=".6"/>')
    o.append(f'<rect x="{XJ(0):.2f}" y="{ZJ(22.5):.2f}" width="{2.5*Sj:.2f}" height="{5.0*Sj:.2f}" fill="#222" fill-opacity=".35"/>')
    for k, yy in enumerate((4.3, 7.5, 11.0)):
        o.append(f'<rect x="{XJ(yy)-0.5:.2f}" y="{ZJ(17.5):.2f}" width="1.0" height="{3.2*Sj:.2f}" fill="#b86e00"/>')
    o.append(f'<path d="M{XJ(12):.2f},{ZJ(13.5):.2f} C{XJ(14):.2f},{ZJ(9):.2f} {XJ(16):.2f},{ZJ(6):.2f} {XJ(40):.2f},{ZJ(5.5):.2f}" fill="none" stroke="#6b7690" stroke-width="1.6"/>')
    o.append(f'<path d="M{XJ(9):.2f},{ZJ(13.5):.2f} C{XJ(12):.2f},{ZJ(7):.2f} {XJ(16):.2f},{ZJ(4.5):.2f} {XJ(40):.2f},{ZJ(4.2):.2f}" fill="none" stroke="#9aa3b2" stroke-width="1.6"/>')
    s.text(XJ(0), ZJ(26.0) - 1.6, "J701 PJ-313 (몸통 y2.5~14 · z17.5~22.5, 축 z20, 코 y0~2.5)", "notes", "start", size=1.7, check=False)
    s.text(XJ(0) - 1.0, ZJ(20.0) + 0.6, "볼 앞면 y0", "notes", "end", size=1.7, check=False)
    s.text(XJ(16.0), ZJ(12.0), "선 홈 x−10.34~−6.34 · z3~8 → 뒤 통로", "notes", "start", size=1.65, check=False)
    s.text(XJ(0), ZJ(3.0) + 3.4, "밑에서 넣는 틈 z3~17.4 (바닥 3T 판이 덮음)", "notes", "start", size=1.65, check=False)
    s.regions["j701"] = (oxj - 8.0, oyj - 12.0, oxj + 40 * Sj + 8.0, ZJ(3.0) + 6.0)
    jr = [["W701 흰색", "DAC_L", "T"], ["W701 빨강", "DAC_R", "R"], ["W701 차폐", "AGND", "S"],
          ["W702 흰색", "HP_TN_L", "TN"], ["W702 빨강", "HP_RN_R", "RN"], ["W702 차폐", "AGND", "S (W701 차폐와 함께)"]]
    yj = s.table(350, 92, ["선", "넷", "J701 다리"], jr, [16, 16, 26], title="J701 다리 연결", mono_cols=(1,), rh=2.75)
    s.para(262, ZJ(3.0) + 9.0, [
        "J701: 기판 없이 볼 포켓(CAD 몸통 칸 x−11.49~−5.19 · y2.5~14.2 · z17.4~22.6)에",
        "밑에서 넣고 핫멜트·순간접착제 한 방울로 고정(CAD 사양). 다리(몸통 밑 3.2)에",
        "W701·W702 속선을 바로 납땜 → 각각 수축 튜브 → 선 홈(z3~8)으로 뒤 통로까지.",
        "납땜 전에 통전 검사로 T·TN·R·RN·S를 표시(플러그 없음: T–TN, R–RN 닫힘).",
        "헤드폰을 꽂으면 TN·RN이 떨어져 스피커가 꺼진다(R15).",
    ], "notes", size=1.85, lh=2.55)
    # ------------------------------------------------------------ common notes
    s.para(14.0, 241.0, [
        "주",
        "1. 기판: 양면 만능기판(12 × 18 cm, 2.54)에서 자른다. 모서리는 구멍 사이 가운데 — 바깥 구멍이 모서리에서 1.27. J702 나사 Ø3.2는 CAD 자리(왼쪽·앞 모서리에서 3.0, 3.0 / 27.0, 22.0)에 뚫고,",
        "    받침 기둥(점선 네모) 위의 구멍은 쓰지 않는다. J501·PS는 나사 없이 MS 폴리머.",
        "2. PJ-313 다리 간격은 2.54가 아니다(SHOU HAN PJ-313 도면: 1.8 · 3.2 · 3.5 mm, 위치 돌기 Ø1.0 두 개 6.0 간격). 점선 칸 안에서 다리를 가장 가까운 구멍으로",
        "    살짝 구부려 꽂거나 Ø1.3으로 넓힌다. 다리 글자(T·TN·R·RN·S)는 통전 검사로 먼저 찾는다 — 판매자마다 번호가 다르다.",
        "3. 굵은 실선 = 주석 입힌 맨선(이웃 구멍 사이), 점선 = 피복 가닥(리본 1가닥). 선은 빈 구멍 위는 지나도 되지만 다른 넷 패드 위는 지나지 않는다(검사).",
        "4. 이 도면의 패드·넷은 SCH-05·SCH-07과 자동 대조한다(build.py 출력). 문제 0이어야 도면이 만들어진다.",
    ], size=1.95, lh=2.7)
    s.frame()
    s.expected = {}
    return s


# ====================================================================== BRD-08 MB underside wiring (mirror view)
def brd08():
    from sheets import TOTAL, REV_E
    import sheets as S
    from sch import Sheet
    import mbroute as MR
    r, rows, probs = MR.get()
    s = Sheet("BRD-08", 15, TOTAL, "제어 기판 아랫면 배선 (MB · 아래에서 봄 — 좌우 거울상)",
              "BRD-01 기판을 뒤집어 본 그림(왼쪽·오른쪽이 바뀜). 피복 단선 %d가닥: 패드에서 시작해 1.27 격자 위로만, 납땜 패드 위는 지나지 않음. 경로 = netlist/wiring_MB.csv." % len(rows),
              "MB", qty="MB × 7", basis="BRD-01 · SCH-03 · mbroute.py", **REV_E)
    s.board_check = list(probs)
    SC = 3.0
    ox, oy = 22.0, 34.0
    x0, x1, y0, y1 = MR.BOARD

    def X(x):                     # mirrored: world +x to the LEFT
        return ox + (x1 - x) * SC

    def Y(y):
        return oy + (y1 - y) * SC
    o = s.out["body"]
    o.append(f'<rect x="{X(x1):.2f}" y="{Y(y1):.2f}" width="{(x1-x0)*SC:.2f}" height="{(y1-y0)*SC:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    # slot (cut) + keep-out
    kx0, kx1, ky0, ky1 = S.MB["keep"]
    o.append(f'<rect x="{X(kx1):.2f}" y="{Y(ky1):.2f}" width="{(kx1-kx0)*SC:.2f}" height="{(ky1-ky0)*SC:.2f}" fill="#fde2d8" stroke="#c2410c" stroke-width=".3" stroke-dasharray="1.2 .8"/>')
    sx0, sx1, sy0, sy1 = S.MB["slot"]
    o.append(f'<rect x="{X(sx1):.2f}" y="{Y(sy1):.2f}" width="{(sx1-sx0)*SC:.2f}" height="{(sy1-sy0)*SC:.2f}" fill="#fff" stroke="#c2410c" stroke-width=".45"/>')
    # part outlines on the other side (faint): Zero, mux, resistors
    zx0, zy1 = S.ZERO_ORIGIN
    o.append(f'<rect x="{X(zx0+18):.2f}" y="{Y(zy1):.2f}" width="{18*SC:.2f}" height="{23.5*SC:.2f}" rx="3" fill="none" stroke="#1f2a44" stroke-width=".35" stroke-dasharray="2 1" stroke-opacity=".5"/>')
    mx0, my0 = S.MUX_ORIGIN
    o.append(f'<rect x="{X(mx0+17.78):.2f}" y="{Y(my0+40.64):.2f}" width="{17.78*SC:.2f}" height="{40.64*SC:.2f}" rx="1" fill="none" stroke="#1f5fbf" stroke-width=".35" stroke-dasharray="2 1" stroke-opacity=".5"/>')
    s.text(X(zx0 + 9), Y(zy1) + 6.0, "A301 (윗면)", "notes", "middle", size=1.9, check=False)
    s.text(X(mx0 + 8.9), Y(my0 + 20), "A302 (윗면)", "notes", "middle", size=1.9, check=False)
    # screw heads / pins (underside)
    for (a, b) in MR.SCREWS:
        o.append(f'<circle cx="{X(a):.2f}" cy="{Y(b):.2f}" r="{2.85*SC:.2f}" fill="#c9d0da" fill-opacity=".45" stroke="#6b7690" stroke-width=".35" stroke-dasharray="1.2 .7"/>')
        o.append(f'<circle cx="{X(a):.2f}" cy="{Y(b):.2f}" r="{1.6*SC:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".35"/>')
        s.text(X(a), Y(b) + (10.6 if b < 170 else -9.6), "M3×6 머리 Ø5.7", "notes", "middle", size=1.8, check=False)
    for (a, b) in MR.PINS:
        o.append(f'<circle cx="{X(a):.2f}" cy="{Y(b):.2f}" r="{1.5*SC:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".35"/>')
        s.text(X(a), Y(b) + (7.4 if b < 170 else -6.2), "위치 핀", "notes", "middle", size=1.8, check=False)
    # lattice holes
    for k in range(MR.kx(x0), MR.kx(x1) + 1):
        for m in range(MR.my(y0), MR.my(y1) + 1):
            if k % 2 == 0 and m % 2 == 0:
                x, y = MR.X(k), MR.Y(m)
                if x0 + 0.6 < x < x1 - 0.6 and y0 + 0.6 < y < y1 - 0.6 and not (sx0 <= x <= sx1 and y <= sy1):
                    o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".38" fill="#b9cdb6"/>')
    # wires
    for w in rows:
        d = " ".join("%.2f,%.2f" % (X(x), Y(y)) for x, y in w["pts"])
        o.append(f'<polyline points="{d}" fill="none" stroke="{ncol(w["net"])}" stroke-width=".55" stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".9"/>')
    # pads (soldered)
    for (k, m), (ref, num, net) in r.pads.items():
        if not MR.soldered((ref, num, net)):
            continue
        x, y = MR.X(k), MR.Y(m)
        c = ncol(net) if net != "NC" else "#fff"
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.25" fill="{c}" stroke="#1f2a44" stroke-width=".3"/>')
    # wire numbers at the middle of the longest segment
    for w in rows:
        segs = list(zip(w["pts"], w["pts"][1:]))
        a, b = max(segs, key=lambda t: abs(t[0][0] - t[1][0]) + abs(t[0][1] - t[1][1]))
        mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        o.append(f'<rect x="{X(mx_)-1.9:.2f}" y="{Y(my_)-1.3:.2f}" width="3.8" height="2.4" rx=".6" fill="#fff" fill-opacity=".9" stroke="{ncol(w["net"])}" stroke-width=".25"/>')
        s.text(X(mx_), Y(my_) + 0.6, str(w["no"]), "pinnum", "middle", size=1.6, check=False)
    # pin names for the module columns (mirrored side)
    import parts as P
    names = dict(P.RP2040_ZERO)
    for n in range(1, 19):
        x, y = S.zero_hole(n)
        side = 2.0 if n <= 9 else -2.0                      # mirror: the left column (1~9) is on the RIGHT in this view
        s.text(X(x) + side, Y(y) - 1.5, names[n], "pinname", "start" if side > 0 else "end", size=1.5, check=False)
    for nm in ["C%d" % i for i in range(16)] + ["GND", "VCC", "EN", "S0", "S1", "S2", "S3", "SIG"]:
        x, y = S.mux_hole(nm)
        side = -2.0 if nm.startswith("C") else 2.0
        s.text(X(x) + side, Y(y) - 1.5, nm, "pinname", "end" if side < 0 else "start", size=1.5, check=False)
    for i in range(16):
        x, y = S.RIB_X0 + 2.54 * (i // 2), S.RIB_Y[i % 2]
        s.text(X(x), Y(y) + (4.4 if i % 2 == 0 else -2.4), str(i + 1), "pinnum", "middle", size=1.5, check=False)
    s.text(X(S.RIB_X0 + 8.89), Y(y0) + 9.0, "J301 리본 (1 = 앞줄, 이 그림에서는 오른쪽 끝)", "cabt", "middle", size=1.9, check=False)
    for i in range(6):
        s.text(X(S.EXT_X0 + 2.54 * i), Y(S.EXT_Y) - 2.4, str(i + 1), "pinnum", "middle", size=1.5, check=False)
    s.text(X(S.EXT_X0 + 6.35), Y(y1) - 2.2, "J302 EXT (1 = GND)", "cabt", "middle", size=1.9, check=False)
    for ref, (x, y) in S.JP_POS.items():
        s.text(X(x + 2.54) - 2.2, Y(y) + 0.6, ref, "pinname", "end", size=1.5, check=False)
    for ref, (x, y) in S.R_EXT.items():
        s.text(X(x + 7.62) - 2.0, Y(y) + 0.6, ref + ".2", "pinname", "end", size=1.5, check=False)
        s.text(X(x) + 2.0, Y(y) + 0.6, ref + ".1", "pinname", "start", size=1.5, check=False)
    for ref, (x, y) in S.TP_POS.items():
        s.text(X(x), Y(y) - 2.0, ref, "pinname", "middle", size=1.3, check=False)
    # rulers
    for x in (47.25, 56.20, 61.28, 71.44, 76.52, 81.22, 85.42, 91.76, 101.92, 109.54, 117.25):
        s.line(X(x), Y(y0) + 2.0, X(x), Y(y0) + 4.0, "bodyl", "text")
        s.text(X(x), Y(y0) + 6.2, "x%g" % x, "tblm", "middle", size=1.5, check=False)
    for y in (145.5, 148.19, 153.27, 163.43, 173.59, 183.75, 193.91, 195.5):
        s.line(X(x0) + 2.0, Y(y), X(x0) + 4.0, Y(y), "bodyl", "text")
        s.text(X(x0) + 4.8, Y(y) + 0.6, "y%g" % y, "tblm", "start", size=1.5, check=False)
    s.text(X(x1), Y(y1) - 6.5, "뒤 (+y, USB 쪽) · 아래에서 봄: 모델 +x가 왼쪽", "notes", "start", size=2.0, check=False)
    s.text(X(x1), Y(y0) + 13.0, "앞 (연주자 쪽, −y) · 리본이 들어옴", "notes", "start", size=2.0, check=False)
    # wire table (two columns)
    tr = [[str(w["no"]), w["net"], w["a"], w["b"], "%.1f" % w["length"], str(w["bends"])] for w in rows]
    half = (len(tr) + 1) // 2
    cols = ["번호", "넷", "시작", "끝", "길이", "꺾임"]
    wd = [8, 17, 17, 17, 10, 8]
    yt = s.table(250, 24, cols, tr[:half], wd, title="아랫면 배선 %d가닥 (꺾인 점 좌표 = wiring_MB.csv)" % len(rows), mono_cols=(0, 1, 2, 3, 4, 5), rh=2.75)
    s.table(332, 28.2, cols, tr[half:], wd, mono_cols=(0, 1, 2, 3, 4, 5), rh=2.75)
    s.para(14.0, 200.0, [
        "주",
        "배선 검사: SCH-03 넷 %d개를 모두 잇고, 납땜 패드 위·W1 금지 구역·나사 머리·위치 핀·JP 브리지·C301 자리를 지나지 않으며, 두 선이 한 칸을 같이 쓰지 않음 (문제 %d)"
        % (len(r.nets), len(probs)),
        "1. 선: 피복 단선(리본 가닥 또는 0.5 mm 랩 선). 꺾인 점은 모두 1.27 격자 위(구멍 사이 반 칸 또는 빈 구멍). 납땜할 패드 위는 지나지 않는다 — 빈 구멍 위는 지나도 된다.",
        "    선끼리 직각으로 겹치는 곳은 피복이라 괜찮다(같은 칸을 나란히 쓰지 않음). 같은 넷의 여러 선은 패드에서만 만난다.",
        "2. W1 금지 구역(x81.22~85.42, y≤173.2)과 홈은 제로 밑 y≥174.86에서만 건넌다(MUX_S0·EXT 등). C301은 먹스 GND–VCC 핀 사이 아랫면 1206.",
        "3. JP301~JP303은 O 번호에 맞춰 납땜 브리지(BRD-01 표), JP304는 열림. 브리지 자리(두 구멍 사이)에는 선이 없다.",
        "4. 순서: C301 → 짧은 선(ID·JP·EXT 풀다운 GND) → 먹스–리본 12가닥 → 긴 선(EXT·MUX·3V3·GND) → J301 리본·J302 리드 → 확인(3V3–GND 단락 없음, 표의 넷마다 통전).",
        "5. 이 그림은 아래에서 본 것: 왼쪽·오른쪽이 BRD-01과 반대. 패드 이름(A301 핀·먹스 핀·J301 번호)을 보고 맞춘다. 모듈 7장 모두 같은 배선.",
        "6. EXT4(먹스 C15)는 지금 어느 보드도 쓰지 않는다(R304 비움, XH 5번 빈 칸): %s번 선은 넣어도 되고 빼도 된다. EXT2·EXT3은 O1만 쓰지만 7장을 같게 만든다."
        % "·".join(str(w["no"]) for w in rows if w["net"] == "EXT4"),
    ], size=1.95, lh=2.7)
    s.regions["mbu"] = (14.0, 24.0, 244.0, 196.0)
    s.frame()
    s.expected = {}
    return s


def wiring_mb_rows():
    import mbroute as MR
    r, rows, probs = MR.get()
    return [[w["no"], w["net"], w["a"], "%.2f" % w["ax"], "%.2f" % w["ay"], w["b"], "%.2f" % w["bx"], "%.2f" % w["by"],
             " → ".join("(%.2f,%.2f)" % p for p in w["pts"]), "%.1f" % w["length"], w["bends"]] for w in rows]


def wiring_sb_rows():
    return [[r["u"], r["key"], r["net"], "%.2f" % r["xo"], "%.2f" % r["yo"], "J201.%d" % r["pin"], "%.2f" % r["xp"], "%.2f" % r["yp"],
             "앞줄 (홀수)" if r["pin"] % 2 else "뒷줄 (짝수)", " → ".join("(%.2f,%.2f)" % p for p in r["poly"]), "%.1f" % r["length"]]
            for r in sb_rows() + sb_pwr_rows()]


def wiring_small_rows():
    out = []
    for board, routes, bare in (("J702", J7_ROUTES, J7_BARE), ("PS", PS_ROUTES, PS_BARE)):
        for net, polys in routes.items():
            for k, poly in enumerate(polys):
                out.append([board, net if net != "N1" else "U551 OUT–R551", " → ".join("(%.2f,%.2f)" % p for p in poly), "%.1f" % wlen(poly),
                            "주석 맨선" if (net, k) in bare else "피복 가닥"])
    return out


def pads_small_rows():
    out = []
    for (ref, pin), ij in J7_PADS.items():
        x, y = _p7(*ij)
        out.append(["J702 기판", ref, pin, J7_NET[(ref, pin)], ij[0], ij[1], "%.2f" % x, "%.2f" % y, "모델 좌표"])
    for (ref, pin), ij in J5_PADS.items():
        out.append(["J501 조각", "W502", pin, J5_NET[pin], ij[0], ij[1], "%.2f" % j5x(ij[0]), "%.2f" % j5y(ij[1]), "모델 좌표"])
    for (ref, pin), cr in PS_PADS.items():
        out.append(["PS 조각", ref if ref != "P501" else "W501", pin, PS_NET[(ref, pin)].replace("N1", "U551 OUT–R551"), cr[0], cr[1],
                    "%.2f" % psx(cr[0]), "%.2f" % psy(cr[1]), "로컬 (왼쪽 아래 구멍 = 0, 0)"])
    return out
