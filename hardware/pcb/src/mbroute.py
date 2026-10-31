"""Control-board (MB) underside wiring: routed on the half-pitch channels of the board's hole lattice, with an independent check.

△33 (2026-10-31, CAD A16): MB is the whole 80 x 120 double-sided perfboard (x22.25~142.25 x y93.3~173.3) lying on printed support
ribs on the module floor (board underside z7.0, floor z5.0). Every pad sits on the hole lattice x = 30.18 + 2.54 i, y = 96.47 + 2.54 j
(BRD-01). Wires run on the underside as single 2651 ribbon strands (OD ~0.9; two crossing strands 1.8 < the 2.0 gap; tails <= 1.0).
A wire travels on the 1.27 grid (hole lines and the half-pitch lines between them) and never passes over a pad that is soldered (a part
lead, a header pin or a wire end of any net); it may pass over an empty hole. Two wires never share a grid segment; they may cross at
right angles (insulated).
Blocked (wire centre within 0.6 of it = wire radius 0.5 + 0.1):
  * the support ribs: front rib (gap x59.5~81.5 for the ribbon), rear rib, side ribs and the rib under the balance-rail strip with
    ONE crossing gap x92.0~114.0 - every wire between the front zone (J301, mux) and the rear zone (Zero, J302, R30x, JP, TP) passes
    there under the rail;
  * the flat ribbon W10x and its strand fan under the front edge (x59.0~81.1, y<=98.3); the strands to the J301 back row rise between
    the front-row pads, so no wire runs along y on those half-pitch lanes (x61.93~79.71, y99.01) - crossing them in x is fine;
  * the C301 1206 between the mux GND / VCC pins, the solder bridges of JP301~JP304, 0.8 mm along the board edge.

Connections per net = minimum spanning tree over the net's pads (Manhattan; a front <-> rear link is costed through the rail gap and
penalised, so each net crosses once); each connection is routed pad to pad (negotiated congestion, then strict A* + rip-up).
Wires join only at pads (no mid-wire splices).
check() re-verifies the result geometrically against the SCH-03 netlist and the CAD keep-outs (sheets.MB): orthogonal segments, no
soldered pad on a segment's interior, no wire on a rib / the ribbon / a strand lane / the edge, no shared segment or slot between wires,
every pad of every net reached and each net connected.
"""
import heapq
import itertools
import math

P0X, P0Y, H = 30.18, 96.47, 1.27           # lattice origin (hole i = 0, j = 0) and half pitch
BOARD = (22.25, 142.25, 93.3, 173.3)
EDGE = 0.8
RIB_CLR = 0.6                              # wire radius 0.5 + 0.1 from a rib face
STRIP_Y = (132.8, 144.0)                   # rib under the balance-rail strip (wires cross it only in the gap)
GAP_X = (92.0, 114.0)


def kx(x):
    return int(round((x - P0X) / H))


def my(y):
    return int(round((y - P0Y) / H))


def X(k):
    return round(P0X + H * k, 2)


def Y(m):
    return round(P0Y + H * m, 2)


def ribs():
    import sheets as S
    return [tuple(r) for r in S.MB["ribs"]]


def ribbon_zone():
    import sheets as S
    x0, x1, y1 = S.MB["ribbon"]
    return (x0, x1, BOARD[2], y1)


def strand_lanes():
    """J301 back-row strands rise between the front-row pads: half-pitch nodes (k, m) of those lanes (no wire runs along y there)."""
    import sheets as S
    m = my(S.RIB_Y[0])
    return {(kx(S.RIB_X0 + 1.27 + 2.54 * c), m) for c in range(8)}


def pads_and_nets():
    """(k, m) -> (ref, pin, net) for every MB pad, from SCH-03 (drawn netlist) + BRD-01 coordinates."""
    import sheets as S
    s = S.sch03()
    s.connectivity()
    import export as EX
    pads = {}
    nets = {}
    for net, pins in s.nets.items():
        for p in sorted(pins):
            ref, num = p.split(".", 1)
            if ref == "C301":
                continue                               # 1206 soldered across the mux GND / VCC header tails (no wire)
            c = EX.mb_coord(ref, num, net)
            if c is None:
                continue
            k, m = kx(c[0]), my(c[1])
            nn = "NC" if net.startswith("~") else net
            pads[(k, m)] = (ref, num, nn)
            if nn != "NC":
                nets.setdefault(nn, []).append((k, m))
    return pads, nets


def soldered(pd):
    """True if the pad carries solder (part lead / header pin / wire). The Zero's bottom row 19~23 has no header -> empty hole."""
    ref, num, net = pd
    if ref == "A301" and int(num) >= 19:
        return False
    return True


def _in_rect(x, y, r, e=0.0):
    x0, x1, y0, y1 = r
    return x0 - e < x < x1 + e and y0 - e < y < y1 + e


def blocked_nodes(pads):
    import sheets as S
    bl = set()
    x0, x1, y0, y1 = BOARD
    kmin, kmax = kx(x0) - 2, kx(x1) + 2
    mmin, mmax = my(y0) - 2, my(y1) + 2
    R = ribs()
    rz = ribbon_zone()
    for k in range(kmin, kmax + 1):
        for m in range(mmin, mmax + 1):
            x, y = X(k), Y(m)
            if x < x0 + EDGE or x > x1 - EDGE or y < y0 + EDGE or y > y1 - EDGE:
                bl.add((k, m))
            elif any(_in_rect(x, y, r, RIB_CLR) for r in R):
                bl.add((k, m))
            elif _in_rect(x, y, rz, 0.05):
                bl.add((k, m))
    # solder bridges JP301~JP304 (node between the two holes) and the C301 1206 (between mux GND and VCC)
    for ref, (sig, gnd) in S.JP_PADS.items():
        bl.add((kx((sig[0] + gnd[0]) / 2), my((sig[1] + gnd[1]) / 2)))
    g = S.mux_hole("GND")
    v = S.mux_hole("VCC")
    bl.add((kx((g[0] + v[0]) / 2), my((g[1] + v[1]) / 2)))
    return bl, (kmin, kmax, mmin, mmax)


def is_hole(n):
    return n[0] % 2 == 0 and n[1] % 2 == 0


DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
LANE = -1                                   # pseudo wire id of the reserved J301 strand lanes (axis 'V')


class Router:
    def __init__(self):
        self.pads, self.nets = pads_and_nets()
        self.blocked, self.box = blocked_nodes(self.pads)
        self.solder = {n for n, pd in self.pads.items() if soldered(pd)}
        self.reserved = strand_lanes()
        self.edge_use = {}          # frozenset(n1, n2) -> wire id
        self.node_use = {n: [(LANE, "V")] for n in self.reserved}   # node -> list of (wire id, 'H' | 'V' | 'T')
        self.wires = []             # dict(net, a, b, path=[nodes])

    def inside(self, n):
        kmin, kmax, mmin, mmax = self.box
        return kmin <= n[0] <= kmax and mmin <= n[1] <= mmax

    def route(self, net, a, b):
        """A* from pad a to pad b against the committed wires; returns node list or None."""
        BEND, CROSS = 1.6, 2.5
        tk, tm = b
        best = {(a, None): 0.0}
        came = {}
        cnt = itertools.count()
        openq = [(abs(a[0] - tk) + abs(a[1] - tm), next(cnt), 0.0, a, None)]
        while openq:
            f, _, g, n, d = heapq.heappop(openq)
            if n == b:
                path = [n]
                st = (n, d)
                while st in came:
                    st = came[st]
                    path.append(st[0])
                return path[::-1]
            if g > best.get((n, d), 1e9) + 1e-9:
                continue
            for dd in DIRS:
                nn = (n[0] + dd[0], n[1] + dd[1])
                if not self.inside(nn) or nn in self.blocked and nn != b:
                    continue
                if nn in self.solder and nn != b:
                    continue
                if n in self.solder and n != a:
                    continue
                e = frozenset((n, nn))
                if e in self.edge_use:
                    continue
                cost = 1.0 if not is_hole(nn) else 1.15      # prefer the half-pitch lines between holes
                if d is not None and dd != d:
                    # no turning on a node another wire (or a strand lane) passes / ends on
                    if n in self.node_use and n != a:
                        continue
                    cost += BEND
                # entering a node used by another wire: only a straight perpendicular crossing
                if nn != b and nn in self.node_use:
                    uses = self.node_use[nn]
                    my_ax = "H" if dd[1] == 0 else "V"
                    if any(u[1] == "T" or u[1] == my_ax for u in uses):
                        continue
                    cost += CROSS
                ng = g + cost
                st = (nn, dd)
                if ng < best.get(st, 1e9) - 1e-9:
                    best[st] = ng
                    came[st] = (n, d)
                    h = abs(nn[0] - tk) + abs(nn[1] - tm)
                    heapq.heappush(openq, (ng + h, next(cnt), ng, nn, dd))
        return None

    def uncommit(self, wid):
        w = self.wires[wid]
        for n1, n2 in zip(w["path"], w["path"][1:]):
            self.edge_use.pop(frozenset((n1, n2)), None)
        for n in w["path"][1:-1]:
            lst = [u for u in self.node_use.get(n, []) if u[0] != wid]
            if lst:
                self.node_use[n] = lst
            else:
                self.node_use.pop(n, None)

    def commit(self, net, a, b, path, wid=None):
        if wid is None:
            wid = len(self.wires)
            self.wires.append(dict(net=net, a=a, b=b, path=path))
        else:
            self.wires[wid] = dict(net=net, a=a, b=b, path=path)
        for n1, n2 in zip(path, path[1:]):
            self.edge_use[frozenset((n1, n2))] = wid
        for i, n in enumerate(path):
            if i == 0 or i == len(path) - 1:
                continue
            prev, nxt = path[i - 1], path[i + 1]
            d1 = (n[0] - prev[0], n[1] - prev[1])
            d2 = (nxt[0] - n[0], nxt[1] - n[1])
            ax = "T" if d1 != d2 else ("H" if d1[1] == 0 else "V")
            self.node_use.setdefault(n, []).append((wid, ax))


def zone(y):
    """0 = front zone (J301, mux), 1 = under the rail strip, 2 = rear zone (Zero, J302, R30x, JP, TP)."""
    return 0 if y < STRIP_Y[0] else (2 if y > STRIP_Y[1] else 1)


def gap_cols():
    """x of the free grid columns through the strip-rib gap."""
    return [X(k) for k in range(kx(GAP_X[0]) - 1, kx(GAP_X[1]) + 2) if GAP_X[0] + RIB_CLR <= X(k) <= GAP_X[1] - RIB_CLR]


def mst(pts, single=()):
    """minimum spanning tree of a net's pads. Pads in `single` (the J301 block: each hole has one exit toward +y, the ribbon strands
    take the front) get one wire each where the net allows: links between two of them are penalised."""
    g0, g1 = min(gap_cols()), max(gap_cols())

    def cost(a, b):
        xa, ya, xb, yb = X(a[0]), Y(a[1]), X(b[0]), Y(b[1])
        pen = 40 if (a in single and b in single) else 0
        if zone(ya) != zone(yb):                       # front <-> rear: through the rail gap, and only once per net
            lo, hi = min(xa, xb), max(xa, xb)
            dx = (2 * g0 - xa - xb) if hi < g0 else ((xa + xb - 2 * g1) if lo > g1 else hi - lo)
            return (dx + abs(ya - yb)) / H + 40 + pen
        return (abs(xa - xb) + abs(ya - yb)) / H + pen
    inside, rest, out = [pts[0]], list(pts[1:]), []
    while rest:
        c, a, b = min(((cost(i, r), i, r) for i in inside for r in rest), key=lambda t: t[0])
        out.append((a, b))
        inside.append(b)
        rest.remove(b)
    return out


def _axis(dd):
    return "H" if dd[1] == 0 else "V"


def route_soft(r, net, a, b, occ, hist, pres):
    """A* where every grid node has an H slot and a V slot (a straight pass uses one, a turn uses both); a slot already used by
    another wire is allowed but costs pres * use + its history (negotiated congestion, PathFinder). Strand lanes are hard."""
    tk, tm = b
    cnt = itertools.count()
    openq = [(abs(a[0] - tk) + abs(a[1] - tm), next(cnt), 0.0, a, None)]
    best = {(a, None): 0.0}
    came = {}

    def slot_cost(n, ax):
        u = occ.get((n, ax), 0)
        return hist.get((n, ax), 0.0) + pres * u
    while openq:
        f, _, g, n, d = heapq.heappop(openq)
        if n == b:
            path = [n]
            st = (n, d)
            while st in came:
                st = came[st]
                path.append(st[0])
            return path[::-1]
        if g > best.get((n, d), math.inf) + 1e-9:
            continue
        for dd in DIRS:
            nn = (n[0] + dd[0], n[1] + dd[1])
            if not r.inside(nn) or (nn in r.blocked and nn != b):
                continue
            if nn in r.solder and nn != b:
                continue
            if n in r.solder and n != a:
                continue
            if nn in r.reserved and _axis(dd) == "V":
                continue                                    # along a J301 strand lane
            cost = 1.0 if not is_hole(nn) else 1.15
            if d is not None and dd != d:
                if n in r.reserved:
                    continue                                # no turn on a strand lane
                cost += 1.6 + slot_cost(n, _axis(d) if _axis(dd) != _axis(d) else _axis(dd))   # turning takes n's other slot
                cost += slot_cost(n, _axis(dd))
            if nn != b:
                cost += slot_cost(nn, _axis(dd))
            ng = g + cost
            st = (nn, dd)
            if ng < best.get(st, math.inf) - 1e-9:
                best[st] = ng
                came[st] = (n, d)
                heapq.heappush(openq, (ng + abs(nn[0] - tk) + abs(nn[1] - tm), next(cnt), ng, nn, dd))
    return None


def slots_of(path):
    """(node, axis) slots a path uses (not its two end pads)."""
    out = []
    for i in range(1, len(path) - 1):
        n = path[i]
        d1 = (n[0] - path[i - 1][0], n[1] - path[i - 1][1])
        d2 = (path[i + 1][0] - n[0], path[i + 1][1] - n[1])
        if d1 == d2:
            out.append((n, _axis(d1)))
        else:
            out += [(n, "H"), (n, "V")]
    return out


def route_all(iters=60):
    """negotiated-congestion routing of every MST connection, then strict commit + rip-up improvement."""
    base = Router()
    j301 = {n for n, pd in base.pads.items() if pd[0] == "J301"}
    conns = []
    for net, pts in sorted(base.nets.items()):
        if len(pts) >= 2:
            for a, b in mst(sorted(pts), j301):
                conns.append((net, a, b))
    conns.sort(key=lambda c: abs(c[1][0] - c[2][0]) + abs(c[1][1] - c[2][1]))
    hist, paths = {}, {}
    pres = 0.6
    for it in range(iters):
        occ = {}
        for i, c in enumerate(conns):
            if i in paths:
                for sl in slots_of(paths[i]):
                    occ[sl] = occ.get(sl, 0) + 1
        for i, (net, a, b) in enumerate(conns):
            if i in paths:
                for sl in slots_of(paths[i]):
                    occ[sl] -= 1
            p = route_soft(base, net, a, b, occ, hist, pres)
            if p is None:                          # keep the old path (and its slots) - occ must stay exact
                for sl in slots_of(paths.get(i, [])):
                    occ[sl] = occ.get(sl, 0) + 1
                continue
            paths[i] = p
            for sl in slots_of(p):
                occ[sl] = occ.get(sl, 0) + 1
        over = [sl for sl, u in occ.items() if u > 1]
        if not over and len(paths) == len(conns):
            break
        for sl in over:
            hist[sl] = hist.get(sl, 0.0) + 1.0
        pres = min(pres * 1.5, 200.0)              # capped: unbounded costs overflow the search
    r = Router()
    fail = []
    for i, (net, a, b) in enumerate(conns):
        p = paths.get(i)
        if p is None or any(sl for sl in slots_of(p) if _slot_taken(r, sl)) or any(frozenset(e) in r.edge_use for e in zip(p, p[1:])):
            p = r.route(net, a, b)                 # strict retry against what is already committed
        if p is None:
            fail.append((net, a, b))
        else:
            r.commit(net, a, b, p)
    if not fail:
        improve(r)
    return r, fail


def _slot_taken(r, sl):
    n, ax = sl
    for (wid, use) in r.node_use.get(n, []):
        if use == "T" or use == ax:
            return True
    return False


def wcost(path):
    return len(path) + 2 * corners_count(path)


def improve(r, passes=4):
    """rip-up and re-route: each wire (worst first) is removed and routed again with all the others in place; kept if shorter."""
    for _ in range(passes):
        changed = False
        for wid in sorted(range(len(r.wires)), key=lambda i: -wcost(r.wires[i]["path"])):
            w = r.wires[wid]
            old = w["path"]
            r.uncommit(wid)
            p = r.route(w["net"], w["a"], w["b"])
            if p is not None and wcost(p) < wcost(old):
                r.commit(w["net"], w["a"], w["b"], p, wid)
                changed = True
            else:
                r.commit(w["net"], w["a"], w["b"], old, wid)
        if not changed:
            break


def _key(r):
    import hashlib
    import json
    d = json.dumps([sorted((list(k), list(v)) for k, v in r.pads.items()), sorted(map(list, r.blocked)), sorted(map(list, r.reserved)),
                    [P0X, P0Y, H]], sort_keys=True)
    return hashlib.sha1(d.encode()).hexdigest()


def load_or_route(cache_path):
    """routes are cached in netlist/mb_routes.json (keyed by the pads + blocked areas); re-routed when the board changes."""
    import json
    import os
    r0 = Router()
    key = _key(r0)
    try:
        with open(cache_path, encoding="utf-8") as f:
            c = json.load(f)
        if c.get("key") == key:
            for w in c["wires"]:
                path = [tuple(n) for n in w["path"]]
                r0.commit(w["net"], path[0], path[-1], path)
            return r0, []
    except Exception:
        pass
    r, fail = route_all()
    if not fail:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"key": key, "about": "MB underside wire routes (mbroute.py, △33 whole 80 x 120 board) - grid nodes (k, m): "
                                            "x = 30.18 + 1.27 k, y = 96.47 + 1.27 m",
                       "wires": [{"net": w["net"], "path": [list(n) for n in w["path"]]} for w in r.wires]}, f, separators=(",", ":"))
    return r, fail


def corners_count(path):
    return max(0, len(corners(path)) - 2)


def corners(path):
    """node path -> list of corner nodes (start, bends, end)."""
    if len(path) < 3:
        return list(path)
    out = [path[0]]
    for i in range(1, len(path) - 1):
        d1 = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
        d2 = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        if d1 != d2:
            out.append(path[i])
    out.append(path[-1])
    return out


def check(r):
    """independent re-check of the routed wires (geometry from sheets.MB, not the router's blocked set). Returns problems."""
    import sheets as S
    probs = []
    solder = {n for n, pd in r.pads.items() if soldered(pd)}
    R = [tuple(q) for q in S.MB["ribs"]]
    rx0, rx1, ry1 = S.MB["ribbon"]
    lanes = {(round(S.RIB_X0 + 1.27 + 2.54 * c, 2), S.RIB_Y[0]) for c in range(8)}
    bx0, bx1, by0, by1 = S.MB["x0"], S.MB["x1"], S.MB["y0"], S.MB["y1"]
    rw = 0.5                                                    # wire radius (OD <= 1.0)
    seg_owner = {}
    for wid, w in enumerate(r.wires):
        pts = [(X(k), Y(m)) for k, m in corners(w["path"])]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if abs(xa - xb) > 0.01 and abs(ya - yb) > 0.01:
                probs.append("%s: diagonal segment" % w["net"])
            # the wire's footprint (segment +- radius) against the ribs, the ribbon, the board edge
            fx0, fx1, fy0, fy1 = min(xa, xb) - rw, max(xa, xb) + rw, min(ya, yb) - rw, max(ya, yb) + rw
            for q in R:
                if fx0 < q[1] - 0.05 and q[0] + 0.05 < fx1 and fy0 < q[3] - 0.05 and q[2] + 0.05 < fy1:
                    probs.append("%s wire on a support rib x%.1f~%.1f y%.1f~%.1f at (%.2f,%.2f)-(%.2f,%.2f)" % ((w["net"],) + q + (xa, ya, xb, yb)))
            if min(xa, xb) < rx1 and max(xa, xb) > rx0 and min(ya, yb) < ry1:
                probs.append("%s wire under the ribbon / strand fan at (%.2f,%.2f)-(%.2f,%.2f)" % (w["net"], xa, ya, xb, yb))
            if min(xa, xb) < bx0 + EDGE - 0.01 or max(xa, xb) > bx1 - EDGE + 0.01 or min(ya, yb) < by0 + EDGE - 0.01 or max(ya, yb) > by1 - EDGE + 0.01:
                probs.append("%s wire within %.1f of the board edge" % (w["net"], EDGE))
        # interior nodes must not be soldered pads; ends must be pads of the wire's net
        for n in w["path"][1:-1]:
            if n in solder:
                pd = r.pads[n]
                probs.append("%s wire passes over soldered pad %s.%s (%s) at (%.2f, %.2f)" % (w["net"], pd[0], pd[1], pd[2], X(n[0]), Y(n[1])))
            if n in r.blocked:
                probs.append("%s wire in a blocked area at (%.2f, %.2f)" % (w["net"], X(n[0]), Y(n[1])))
        for end in (w["path"][0], w["path"][-1]):
            pd = r.pads.get(end)
            if not pd or pd[2] != w["net"]:
                probs.append("%s wire ends on (%.2f, %.2f) which is %s" % (w["net"], X(end[0]), Y(end[1]), pd))
        for n1, n2 in zip(w["path"], w["path"][1:]):
            if abs(n1[0] - n2[0]) + abs(n1[1] - n2[1]) != 1:
                probs.append("%s: path step is not one grid step" % w["net"])
            e = frozenset((n1, n2))
            if e in seg_owner and seg_owner[e] != wid:
                probs.append("%s shares a segment with %s" % (w["net"], r.wires[seg_owner[e]]["net"]))
            seg_owner[e] = wid
        for (n, ax) in slots_of(w["path"]):
            if (X(n[0]), Y(n[1])) in lanes and ax == "V":
                probs.append("%s wire runs along a J301 strand lane at (%.2f, %.2f)" % (w["net"], X(n[0]), Y(n[1])))
    # node rule: at a node two wires may only cross straight at right angles (no turn on another wire, no parallel share)
    use = {}
    for wid, w in enumerate(r.wires):
        for (n, ax) in slots_of(w["path"]):
            use.setdefault((n, ax), set()).add(wid)
    for (n, ax), ws in use.items():
        if len(ws) > 1:
            probs.append("wires %s share the %s slot at (%.2f, %.2f)" % ("/".join(r.wires[i]["net"] for i in sorted(ws)), ax, X(n[0]), Y(n[1])))
    # every wire between the zones passes the rail strip inside the gap (the rib check above already forbids the rest)
    for w in r.wires:
        for (xa, ya), (xb, yb) in zip([(X(k), Y(m)) for k, m in corners(w["path"])], [(X(k), Y(m)) for k, m in corners(w["path"])][1:]):
            if min(ya, yb) < STRIP_Y[1] and max(ya, yb) > STRIP_Y[0] and not (GAP_X[0] + rw <= min(xa, xb) and max(xa, xb) <= GAP_X[1] - rw):
                probs.append("%s wire under the rail strip outside the gap at x%.2f~%.2f" % (w["net"], min(xa, xb), max(xa, xb)))
    # connectivity per net (union-find over pads joined by wires)
    for net, pts in r.nets.items():
        par = {p: p for p in pts}

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for w in r.wires:
            if w["net"] == net:
                a, b = w["path"][0], w["path"][-1]
                if a in par and b in par:
                    par[f(a)] = f(b)
        roots = {f(p) for p in pts}
        if len(roots) > 1:
            probs.append("net %s not connected (%d groups)" % (net, len(roots)))
    # every pad of the board on the usable lattice i = 1..40, j = 1..28, none on the rail strip / under a lowered fin
    i0, i1, j0, j1 = S.LAT_USE
    for (k, m), pd in r.pads.items():
        i, j = S.lat_ij(X(k), Y(m))
        if not (i0 <= i <= i1 and j0 <= j <= j1):
            probs.append("pad %s.%s outside the lattice i %d..%d, j %d..%d" % (pd[0], pd[1], i0, i1, j0, j1))
        if S.ZONE_J["strip"][0] <= j <= S.ZONE_J["strip"][1]:
            probs.append("pad %s.%s on the balance-rail strip (row %d)" % (pd[0], pd[1], j))
        if j >= S.ZONE_J["rear"][0] and i in S.FIN_I:
            probs.append("pad %s.%s under the lowered fin 2 / 4 (column %d)" % (pd[0], pd[1], i))
    return probs


def gap_use(r):
    """wires that cross the balance-rail strip (front <-> rear) and the x where they cross."""
    out = []
    for w in r.wires:
        cs = [(X(k), Y(m)) for k, m in corners(w["path"])]
        for (xa, ya), (xb, yb) in zip(cs, cs[1:]):
            if abs(xa - xb) < 0.01 and min(ya, yb) < STRIP_Y[0] and max(ya, yb) > STRIP_Y[1]:
                out.append((w["net"], xa))
    return out


def wire_rows(r):
    """rows for wiring_MB.csv and the BRD-08 table: net, from pad, to pad, corner points, length."""
    rows = []
    order = sorted(range(len(r.wires)), key=lambda i: (r.wires[i]["net"], r.pads[r.wires[i]["a"]][0], r.pads[r.wires[i]["a"]][1]))
    for n, i in enumerate(order, 1):
        w = r.wires[i]
        a, b = r.pads[w["a"]], r.pads[w["b"]]
        cs = corners(w["path"])
        L = sum(abs(X(p[0]) - X(q[0])) + abs(Y(p[1]) - Y(q[1])) for p, q in zip(cs, cs[1:]))
        rows.append(dict(no=n, net=w["net"], a="%s.%s" % (a[0], a[1]), b="%s.%s" % (b[0], b[1]),
                         ax=X(w["a"][0]), ay=Y(w["a"][1]), bx=X(w["b"][0]), by=Y(w["b"][1]),
                         pts=[(X(k), Y(m)) for k, m in cs], length=L, bends=len(cs) - 2, wid=i))
    return rows


_CACHE = {}


def get():
    if "r" not in _CACHE:
        import os
        r, fail = load_or_route(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "netlist", "mb_routes.json")))
        _CACHE["r"] = r
        _CACHE["fail"] = fail
        _CACHE["probs"] = check(r) + ["unrouted %s (%.2f,%.2f)-(%.2f,%.2f)" % (n, X(a[0]), Y(a[1]), X(b[0]), Y(b[1])) for n, a, b in fail]
        _CACHE["rows"] = wire_rows(r)
    return _CACHE["r"], _CACHE["rows"], _CACHE["probs"]


def stats():
    r, rows, probs = get()
    g = gap_use(r)
    return dict(wires=len(rows), length=round(sum(w["length"] for w in rows), 1), gap=len(g), gap_x=sorted(x for _, x in g),
                gap_nets=sorted(n for n, _ in g), problems=len(probs))


if __name__ == "__main__":
    import time
    t = time.time()
    r, rows, probs = get()
    print("wires", len(rows), "problems", len(probs), "%.1f s" % (time.time() - t))
    print("stats", stats())
    for p in probs[:30]:
        print("  ", p)
    for w in rows[:80]:
        print(w["no"], w["net"], w["a"], "->", w["b"], "%.1f" % w["length"], w["bends"], " ".join("(%.2f,%.2f)" % p for p in w["pts"]))
