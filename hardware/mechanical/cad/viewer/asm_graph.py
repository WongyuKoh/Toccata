"""Contact graph of the CAD assembly for the 04 tab's 조립 순서 보기 (2026-10-30).

The user asked for an assembly simulation: pick a part, then the parts fastened or connected to it come in one at a
time, and following the connections part by part ends in the whole instrument. The page does the walk (breadth first
from the picked part); this module writes the graph it walks, viewer/asm.json (merge.py ships it as cad/asm.json).

Two parts are connected when their solids touch, overlap (a screw in its hole, a press fit) or stand within GAP of each
other (a clearance fit, a glue gap): manifold min_gap over bounding-box candidate pairs, on the same part list and order
as parts.json, leaving out the folded altview copies. Every edge gets
  - a kind: 0 fastener (one end is a screw / bolt / nut / insert / balance pin / grommet by its Korean name),
    1 fit (the solids overlap), 2 touch (gap <= TOUCH), 3 gap (up to GAP), 4 near (links each connected component to
    the closest part of another, so that every part can be reached);
  - the reason from the checks' tables of intended overlaps when one matches (check_body INTENDED*, check_interf
    EXPECTED, check_electronics EXPECTED);
  - for each end the direction it comes in from when the other end already stands in place (a unit vector in model
    coordinates; the candidates are +-x / +-y / +-z and, for a part turned off the axes, the normals of its biggest
    flat faces): the free ones are those along which the part's own outline, swept away from it past the
    other part, misses the other part. A fastener comes along its long axis from its head end (the end whose slice is
    bigger), or for a symmetric one (nut, insert, pin) from the free end most away from the other part; any other
    part takes the viewer's explode direction if free, then the free vertical one on its side of the other part
    (from below when it sits lower), then the free one most away from the other part. With none free: the direction
    most away from the other part.

asm.json = {"v": 1, "gap": GAP, "n": parts, "e": [[i, j, kind, value, reason or -1, dir_i, dir_j]], "d": [[dx, dy, dz]],
            "r": [reasons], "m": [module index per part or -1], "mods": [module names], "stats": {...}}
dir_i / dir_j index "d" (unit vectors, model coordinates).
value = the gap in mm (kinds 2..4) or the overlap in mm3 (kinds 0, 1).
"""
import json
import math
import os
import re
import sys
import time

import numpy as np
from manifold3d import JoinType

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

GAP = 0.65          # connected below this gap: glue gaps 0.05, clearance fits 0.2-0.3, a key on its rod / guide tab / balance pin
                    # 0.53 / 0.55 / 0.60; neighbouring keys stand 1.46 apart
TOUCH = 0.02        # touching
FIT_MIN = 0.05      # mm3 of overlap that counts as a fit (screw threads, press fits, the intended overlaps of the checks)
FASTENER = re.compile(r"나사|볼트|너트|인서트|밸런스 핀|그로밋|리벳")
AX6 = [np.array(d, float) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]


def rot_to_z(d):
    """3 x 4 proper rotation taking the unit vector d to +z."""
    d = np.asarray(d, float) / np.linalg.norm(d)
    a = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(a, d)
    e1 /= np.linalg.norm(e1)
    M = np.zeros((3, 4))
    M[:, :3] = np.array([e1, np.cross(d, e1), d])
    return M


def modules(data):
    """module index per part: O1..O7, the two end parts, the rear (speakers, centre unit, battery, cables), the
    touchscreen, the damper pedal - the page's 'same module' scope."""
    names, idx = [], {}

    def mod_of(gname, gs):
        m = re.match(r"^(O\d|끝 부속 (?:왼쪽|오른쪽))", gname)
        if m:
            return m.group(1)
        if gs == "ts":
            return "터치스크린"
        if gs == "floor":
            return "댐퍼 페달"
        if gs == "alt":
            return None
        return "뒷부분 (스피커·가운데 유닛)"
    out = []
    for p in data["parts"]:
        g = data["groups"][p["g"]]
        m = mod_of(g["n"], g.get("s"))
        if m is None or p.get("a"):
            out.append(-1)
            continue
        if m not in idx:
            idx[m] = len(names)
            names.append(m)
        out.append(idx[m])
    return out, names


def reason_tables():
    """(regex a, regex b, reason) from the checks' intended-overlap tables."""
    rows = []
    try:
        import check_body
        for name in ("INTENDED", "INTENDED_E", "INTENDED_CC"):
            rows += [(r[0], r[1], r[2]) for r in getattr(check_body, name, [])]
    except Exception as ex:  # noqa: BLE001
        print("asm_graph: check_body tables not read (%s)" % ex)
    try:
        import check_electronics
        rows += [(r[0], r[1], r[2]) for r in check_electronics.EXPECTED]
    except Exception as ex:  # noqa: BLE001
        print("asm_graph: check_electronics table not read (%s)" % ex)
    try:
        src = open(os.path.join(SRC, "check_interf.py"), encoding="utf-8").read()
        block = src[src.index("EXPECTED = ["):src.index("]\n", src.index("EXPECTED = ["))]
        rows += [tuple(t) for t in re.findall(r'\(r"([^"]+)", r"([^"]+)", "([^"]+)"\)', block)]
    except Exception as ex:  # noqa: BLE001
        print("asm_graph: check_interf table not read (%s)" % ex)
    out = []
    for ra, rb, w in rows:
        # check_interf names unit parts by bare words: 'controlboard' would also catch the board's screws
        ra, rb = (re.sub(r"\bcontrolboard\b", "controlboard(?!screw)", x) for x in (ra, rb))
        w = clean_reason(w)
        if w:
            out.append((ra, rb, w))
    return out


def clean_reason(w):
    """the assembly half of a check's reason: drop the notes on modelling error (polygon approximation, rounding); a
    reason that is only about that error says nothing about the joint and is dropped."""
    if "계산 오차" in w:
        return ""
    w = re.sub(r"\s*\([^()]*(근사|오차)[^()]*\)", "", w)
    w = re.sub(r"\s*(다각형 )?근사 오차.*$", "", w)
    return w.strip(" -,;")


def mesh_of(c):
    m = SOL[c].to_mesh()
    return np.asarray(m.vert_properties, float)[:, :3], np.asarray(m.tri_verts, np.int64)


EXTRA = {}


def extra_dirs(c):
    """the normals of a tilted part's biggest flat faces (+ their opposites): a part turned off the axes (the 25 deg
    touchscreen, the 40 deg speaker front) slides along its own faces, not along x / y / z."""
    if c in EXTRA:
        return EXTRA[c]
    v, t = mesh_of(c)
    n = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    ar = np.linalg.norm(n, axis=1)
    ok = ar > 1e-9
    n, ar = n[ok] / ar[ok, None], ar[ok] / 2.0
    acc = {}
    for k, nn, aa in zip(map(tuple, np.round(n * 20).astype(int)), n, ar):
        s_ = acc.setdefault(k, [np.zeros(3), 0.0])
        s_[0] += nn * aa
        s_[1] += aa
    cl = sorted(((w / max(1e-9, np.linalg.norm(w)), a) for w, a in acc.values()), key=lambda q: -q[1])
    top = cl[0][1] if cl else 0.0
    out = []
    for w, a in cl[:6]:
        if a < 0.15 * top or np.abs(w).max() > math.cos(math.radians(10.0)):
            continue
        for d in (w, -w):
            if not any(np.dot(d, q) > 0.996 for q in out):
                out.append(d)
    EXTRA[c] = out[:6]
    return EXTRA[c]


def cands(c):
    return AX6 + extra_dirs(c)


def free_dirs(c, p, cache):
    """candidate directions along which part c can leave part p: c's outline, projected along the direction and
    extruded from c's far face to past p, misses p."""
    out = []
    for d in cands(c):
        M = rot_to_z(d)
        key = (c,) + tuple(np.round(d, 4))
        if key not in cache:
            cr = SOL[c].transform(M)
            cs = cr.project()
            cs = cs.offset(-0.05, JoinType.Miter) if not cs.is_empty() else cs
            cache[key] = (cs, cr.bounding_box()[5])
        cs, ztop = cache[key]
        pr = SOL[p].transform(M)
        z1 = pr.bounding_box()[5] + 0.1
        if cs.is_empty() or z1 <= ztop + 0.05:
            out.append(d)
            continue
        prism = cs.extrude(z1 - ztop).translate((0.0, 0.0, ztop + 0.03))
        if prism.min_gap(pr, 0.05) > 0.01:
            out.append(d)
    return out


HEAD = {}


def fastener_dir(c):
    """(long axis, head end sign) of a fastener: the axis is the principal axis of its vertices; the head is the end
    whose slice 15 % in is 1.3 times the other's (0 for a nut / insert / pin)."""
    if c in HEAD:
        return HEAD[c]
    v, _t = mesh_of(c)
    w, V = np.linalg.eigh(np.cov((v - v.mean(0)).T))
    ax = V[:, int(np.argmax(w))]
    j = int(np.argmax(np.abs(ax)))
    if abs(ax[j]) > 0.999:                       # snap an axis-aligned fastener exactly
        ax = AX6[2 * j]
    areas = []
    for d in (ax, -ax):
        r = SOL[c].transform(rot_to_z(d))
        z0, z1 = r.bounding_box()[2], r.bounding_box()[5]
        areas.append(r.slice(z1 - 0.15 * (z1 - z0)).area())
    sg = 1 if areas[0] > 1.3 * max(1e-9, areas[1]) else (-1 if areas[1] > 1.3 * max(1e-9, areas[0]) else 0)
    HEAD[c] = (ax, sg)
    return HEAD[c]


def pick_dir(c, p, free, fast, expl):
    """the coming-in direction (unit vector) of c with p in place (see the module text)."""
    bc, bp = BB[c], BB[p]
    away = (bc[:3] + bc[3:]) / 2.0 - (bp[:3] + bp[3:]) / 2.0

    def isfree(d):
        return any(np.dot(d, q) > 0.999 for q in free)
    if fast:
        ax, sg = fastener_dir(c)
        if sg:
            return ax * sg
        f = [d for d in (ax, -ax) if isfree(d)] or [ax, -ax]
        return max(f, key=lambda d: float(np.dot(d, away)))
    if not free:
        return max(AX6, key=lambda d: float(np.dot(d, away)))
    e = np.array(expl or (0, 0, 0), float)
    if np.linalg.norm(e) > 1e-6:
        de = max(AX6, key=lambda d: float(np.dot(d, e)))
        if isfree(de):
            return de
    for d in ((AX6[5], AX6[4]) if away[2] < 0 else (AX6[4], AX6[5])):
        if isfree(d):
            return d
    return max(free, key=lambda d: float(np.dot(d, away)))


SOL, BB = [], None


def main(parts=None, data=None):
    global SOL, BB
    t0 = time.time()
    if parts is None:
        import build_all
        parts = build_all.collect()
    if data is None:
        data = json.load(open(os.path.join(HERE, "parts.json"), encoding="utf-8"))
    by = {p.id: p for p in parts}
    recs = data["parts"]
    n = len(recs)
    SOL = [by[r["id"]].solid for r in recs]
    BB = np.array([s.bounding_box() for s in SOL], float)
    use = [i for i, r in enumerate(recs) if not r.get("a")]
    names = [r["n"] for r in recs]
    ids = [r["id"] for r in recs]
    fast = [bool(FASTENER.search(nm)) for nm in names]
    # ---- candidate pairs (boxes within GAP), then manifold min_gap
    lo, hi = BB[:, :3] - GAP, BB[:, 3:] + GAP
    order = sorted(use, key=lambda i: lo[i, 0])
    cand = []
    for a, i in enumerate(order):
        for j in order[a + 1:]:
            if lo[j, 0] > hi[i, 0]:
                break
            if lo[j, 1] <= hi[i, 1] and lo[i, 1] <= hi[j, 1] and lo[j, 2] <= hi[i, 2] and lo[i, 2] <= hi[j, 2]:
                cand.append((min(i, j), max(i, j)))
    reasons = reason_tables()
    rlist, rix = [], {}
    dlist, dmap = [], {}

    def dix(d):
        k = tuple(round(float(x), 3) + 0.0 for x in d)
        if k not in dmap:
            dmap[k] = len(dlist)
            dlist.append(list(k))
        return dmap[k]
    edges = []
    cache = {}
    for i, j in cand:
        g = SOL[i].min_gap(SOL[j], GAP)
        if g >= GAP:
            continue
        val = round(float(g), 3)
        kind = 3 if g > TOUCH else 2
        if g <= 1e-9:
            v = (SOL[i] ^ SOL[j]).volume()
            if v > FIT_MIN:
                kind, val = 1, round(float(v), 2)
        if fast[i] or fast[j]:
            kind = 0 if kind in (1, 2) else kind
        why = -1
        for ra, rb, w in reasons:
            if (re.search(ra, ids[i]) and re.search(rb, ids[j])) or (re.search(ra, ids[j]) and re.search(rb, ids[i])):
                if w not in rix:
                    rix[w] = len(rlist)
                    rlist.append(w)
                why = rix[w]
                break
        di = dix(pick_dir(i, j, free_dirs(i, j, cache), fast[i], recs[i].get("e")))
        dj = dix(pick_dir(j, i, free_dirs(j, i, cache), fast[j], recs[j].get("e")))
        edges.append([i, j, kind, val, why, di, dj])
    t_edges = time.time() - t0
    # ---- components -> 'near' links to the closest part of another component (Kruskal over component pairs)
    par = list(range(n))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for e in edges:
        a, b = find(e[0]), find(e[1])
        if a != b:
            par[a] = b
    comps = {}
    for i in use:
        comps.setdefault(find(i), []).append(i)
    n_comp0 = len(comps)
    near = 0
    while len(comps) > 1:
        best = None
        cl = list(comps.values())
        big = max(cl, key=len)
        bset = set(big)
        rest = [i for i in use if i not in bset]
        # nearest box pair between the biggest component and the rest, then the exact gap of the 12 closest
        bA, bR = BB[big], BB[rest]
        dmin = []
        for k, i in enumerate(rest):
            d = np.maximum(0.0, np.maximum(bA[:, :3] - BB[i, 3:], BB[i, :3] - bA[:, 3:]))
            dd = np.sqrt((d ** 2).sum(axis=1))
            m = int(np.argmin(dd))
            dmin.append((float(dd[m]), i, big[m]))
        dmin.sort()
        for dbox, i, j in dmin[:12]:
            g = SOL[i].min_gap(SOL[j], max(dbox + 50.0, 60.0))
            if best is None or g < best[0]:
                best = (g, i, j)
        g, i, j = best
        a, b = min(i, j), max(i, j)
        di = dix(pick_dir(a, b, [], fast[a], recs[a].get("e")))
        dj = dix(pick_dir(b, a, [], fast[b], recs[b].get("e")))
        edges.append([a, b, 4, round(float(g), 2), -1, di, dj])
        near += 1
        ra, rb = find(i), find(j)
        par[ra] = rb
        comps = {}
        for k in use:
            comps.setdefault(find(k), []).append(k)
    mods, mod_names = modules(data)
    kinds = [sum(1 for e in edges if e[2] == k) for k in range(5)]
    stats = {"parts": len(use), "candidates": len(cand), "edges": len(edges), "kinds": kinds, "components_before_near": n_comp0,
             "near_links": near, "reasons": len(rlist), "seconds": round(time.time() - t0, 1), "contact_seconds": round(t_edges, 1)}
    out = {"v": 1, "gap": GAP, "touch": TOUCH, "n": n, "e": edges, "d": dlist, "r": rlist, "m": mods, "mods": mod_names, "stats": stats}
    with open(os.path.join(HERE, "asm.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("asm_graph: %d parts, %d edges (fastener %d, fit %d, touch %d, gap %d, near %d), %d components linked, %d reasons, %.0f s, asm.json %.0f KB"
          % (len(use), len(edges), kinds[0], kinds[1], kinds[2], kinds[3], kinds[4], n_comp0, len(rlist), time.time() - t0,
             os.path.getsize(os.path.join(HERE, "asm.json")) / 1e3))
    return out


if __name__ == "__main__":
    main()
