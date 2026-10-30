"""Bambu Studio-like support check of the print STLs (2026-10-30, A13).

After A12 the user said: "아치 같이 바닥이 없고 천장이 있는 부분은 다 서포트가 생성이 될거야 ... 서포트는 너가 그리는 형태가
아니라 트리 형태로 서포트가 생성이 되니까" - Bambu Studio puts (tree) supports under every ceiling that has no floor,
bridges and the tops of holes included, and a support body modelled into the STL does not stop that. So a print
counts as support-free only when no layer hangs out past the layer below more than the slicer's threshold allows.

For every STL of stl/print (and stl/print_extra) the solid is sliced the way the slicer does it (0.2 mm layers, the
P1S default). Layer k needs support where it lies more than STEP = h / tan(30 deg) = 0.35 mm outside layer k - 1:
30 deg from horizontal is Bambu Studio's default support threshold (A13 draws its roofs at 45 deg, the balance-rail
lane at 40). Overhang pieces of consecutive layers that touch form one region:
  - a region of one or two layers whose pieces are all no wider than NARROW is a micro-bridge (the top of a small
    hole, a 1.8 mm teardrop flat): the slicer prints it in the air ("remove small overhangs"), listed apart;
  - every other region needs support - a ceiling, a bridge, a slope flatter than 30 deg (thin in each layer but
    stacked over many layers).
TREE_OK: the key tails (beam + thin tail, y146..199) hang over the bed by design (the lever is 0.7 above them);
Bambu's tree support from the build plate holds their outer undersides - counted apart, not a failure. A15: only up to
the thin tail's underside (print z 18.7 white / 30.7 black); a ceiling higher up sits inside the beam (the capstan nut
slot), where a tree would have to grow into the slot, so it is judged like any other ceiling.
BRIDGE_OK: bridges anchored at both ends and under Bambu's 10 mm 'max bridge length' (the key crossbar; A14: the 07 cradle's
window-gable flat, the window cover's hip-roof flat and the slots over its snap beams; A15: the capstan nut slot's ceiling,
5.6 between the flats, with no hole in it) - counted apart, not a failure.

usage: python3 check_support.py [--json out.json] [--all] [name filters...]
       exit 1 if any print needs support; --all also lists the pieces of every file
"""
import collections
import json
import math
import os
import sys

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh, JoinType

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
LAYER = 0.2
ANGLE = 30.0                                   # from horizontal: Bambu Studio's default support threshold
STEP = LAYER / math.tan(math.radians(ANGLE))
MIN_AREA = 0.05                                # mm2 per piece and layer
TOL = 0.02                                     # facet noise of chamfers / teardrops
NARROW = 2.0                                   # micro-bridge width (one or two layers)
# (file prefix, print-frame y from which the key tail starts, highest print z of its outer undersides): white keys start
# at y0, black ones at y54.2; beam underside z15.1 / 16.1, thin tail z18.7 (white; black +12)
TREE_OK = (("stl/print/01_건반/백건_", 145.9, 19.0), ("stl/print/01_건반/흑건_", 91.7, 31.0),
           ("stl/print_extra/예비_건반/백건_", 145.9, 19.0), ("stl/print_extra/예비_건반/흑건_", 91.7, 31.0))


def load(path):
    tm = trimesh.load(path, process=True)
    tm.merge_vertices()
    M = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    if str(M.status()) != "Error.NoError":
        raise SystemExit("check_support: %s is not a closed solid (%s)" % (path, M.status()))
    return M


def _touch(a, b, g=0.5):
    return a[0] <= b[2] + g and b[0] <= a[2] + g and a[1] <= b[3] + g and b[1] <= a[3] + g


def overhangs(M, layer=LAYER, step=STEP, narrow=False):
    """[(z, area, (x0, y0, x1, y1), holes)] of the layer pieces that hang out past the layer below (print frame, bed z = min)
    and need support; narrow=True returns the micro-bridge pieces instead. holes = inner contours of the piece (A15: a
    bridge with a hole in it leaves the hole's rim hanging, so BRIDGE_OK takes only hole-free pieces)."""
    b = M.bounding_box()
    z0, z1 = b[2], b[5]
    pcs, prev = [], None
    for k in range(int(math.ceil((z1 - z0) / layer))):
        z = z0 + (k + 0.5) * layer
        cs = M.slice(z)
        if prev is not None and not cs.is_empty():
            ov = cs - prev.offset(step + TOL, JoinType.Round)
            if not ov.is_empty():
                for piece in ov.decompose():
                    a = piece.area()
                    if a >= MIN_AREA:
                        thin = piece.offset(-NARROW / 2.0, JoinType.Round).is_empty()
                        pcs.append((k, round(z - z0, 2), round(a, 3), tuple(round(v, 2) for v in piece.bounds()), thin,
                                    piece.num_contour() - 1))
        prev = cs
    up = list(range(len(pcs)))

    def find(i):
        while up[i] != i:
            up[i] = up[up[i]]
            i = up[i]
        return i
    by_k = collections.defaultdict(list)
    for i, pc in enumerate(pcs):
        for j in by_k.get(pc[0] - 1, []):
            if _touch(pc[3], pcs[j][3]):
                up[find(i)] = find(j)
        by_k[pc[0]].append(i)
    groups = collections.defaultdict(list)
    for i in range(len(pcs)):
        groups[find(i)].append(i)
    out = []
    for ix in groups.values():
        micro = len({pcs[i][0] for i in ix}) <= 2 and all(pcs[i][4] for i in ix)
        if micro == narrow:
            out += [pcs[i][1:4] + (pcs[i][5],) for i in ix]
    return sorted(out)


# (file prefix, print-frame y0, y1, max x width, None or print-frame (x0, x1, z0, z1)): bridges anchored at both ends and shorter than
# Bambu Studio's default 'max bridge length' 10 mm get no support - the key's keeper crossbar (8.6 between the guide ribs; the keeper felt
# over it leaves no room for a roof), white keys y10.5..14, black keys y76.5..80 - 54.2; A14: the 07 cradle's window gable flat (9 at u22.75,
# the plate 2.5 thick), the window cover's hip-roof flat (9 x 9) and the slots over its two snap beams (7 x 2.3).
# A15: the capstan nut slot's ceiling (the 0.4 membrane over the slot, first layer print z20.0 white / 32.0 black): the bridge
# runs in y between the hex flats (5.6, y188.34 +- 2.8 white, 180.31 - 54.2 +- 2.8 black), so the y window holds the span;
# its x width is the slot's length out to the open +x face (~7).
_NUT_W, _NUT_B = (-1.0, 40.0, 19.9, 20.3), (-1.0, 40.0, 31.9, 32.3)
BRIDGE_OK = (("stl/print/01_건반/백건_", 10.3, 14.2, 9.0, None), ("stl/print/01_건반/흑건_", 22.1, 26.0, 9.0, None),
             ("stl/print_extra/예비_건반/백건_", 10.3, 14.2, 9.0, None), ("stl/print_extra/예비_건반/흑건_", 22.1, 26.0, 9.0, None),
             ("stl/print/01_건반/백건_", 185.4, 191.3, 7.5, _NUT_W), ("stl/print/01_건반/흑건_", 123.3, 128.9, 7.5, _NUT_B),
             ("stl/print_extra/예비_건반/백건_", 185.4, 191.3, 7.5, _NUT_W), ("stl/print_extra/예비_건반/흑건_", 123.3, 128.9, 7.5, _NUT_B),
             ("stl/print/07_터치스크린/화면받침_크래들", 7.5, 10.5, 9.2, (110.9, 120.3, 80.0, 81.8)),
             ("stl/print/07_터치스크린/점검창덮개", 26.5, 34.0, 2.6, (0.5, 32.0, 2.4, 3.2)),
             ("stl/print/07_터치스크린/점검창덮개", 17.8, 27.3, 9.2, (8.6, 18.2, 6.8, 7.6)))


def split_bridges(rel, ov):
    """(pieces that need support, short two-sided bridges in BRIDGE_OK)."""
    ok = []
    for pre, y0, y1, w, win in BRIDGE_OK:
        if rel.startswith(pre):
            ok += [o for o in ov if o not in ok and o[3] == 0 and o[2][1] >= y0 and o[2][3] <= y1 and o[2][2] - o[2][0] <= w
                   and (win is None or (win[0] <= o[2][0] and o[2][2] <= win[1] and win[2] <= o[0] <= win[3]))]
    return [o for o in ov if o not in ok], ok


def split_tree(rel, ov):
    """(pieces that need support, pieces of the key tail that Bambu's tree support from the plate holds)."""
    for pre, y0, z1 in TREE_OK:
        if rel.startswith(pre):
            held = [o for o in ov if o[2][1] >= y0 and o[0] <= z1]
            return [o for o in ov if o not in held], held
    return ov, []


def print_files(filters=()):
    rows = []
    for top in ("print", "print_extra"):
        root = os.path.join(CAD, "stl", top)
        for d, _s, fns in sorted(os.walk(root)):
            for fn in sorted(fns):
                if fn.endswith(".stl"):
                    p = os.path.join(d, fn)
                    rel = os.path.relpath(p, CAD)
                    if not filters or any(f in rel for f in filters):
                        rows.append(rel)
    return rows


def main(argv):
    out_json = None
    if "--json" in argv:
        i = argv.index("--json")
        out_json = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    show_all = "--all" in argv
    filters = [a for a in argv if not a.startswith("--")]
    res = {}
    bad = tree = 0
    for rel in print_files(filters):
        M = load(os.path.join(CAD, rel))
        need, tr = split_tree(rel, overhangs(M))
        need, br = split_bridges(rel, need)
        micro = overhangs(M, narrow=True)
        res[rel] = dict(area=round(sum(o[1] for o in need), 2), pieces=len(need), worst=sorted(need, key=lambda t: -t[1])[:12],
                        tree_area=round(sum(o[1] for o in tr), 2), micro=len(micro), bridges=len(br))
        bad += bool(need)
        tree += bool(tr)
        if need or show_all:
            print("%-62s %4d pieces %9.2f mm2%s" % (rel, len(need), res[rel]["area"],
                                                    "  (+ tree %.0f mm2)" % res[rel]["tree_area"] if tr else ""))
            for z, a, bb, nh in res[rel]["worst"][:6 if not show_all else 12]:
                print("      z%7.2f  %8.2f mm2  x%.1f~%.1f y%.1f~%.1f%s" % (z, a, bb[0], bb[2], bb[1], bb[3], "  (%d holes)" % nh if nh else ""))
    print("check_support: %d files, %d need support, %d key tails on Bambu tree support (layer %.2f, %g deg = %.3f mm a layer)"
          % (len(res), bad, tree, LAYER, ANGLE, STEP))
    if out_json:
        json.dump(dict(layer=LAYER, angle=ANGLE, step=STEP, min_area=MIN_AREA, narrow=NARROW, files=res), open(out_json, "w"),
                  ensure_ascii=False, indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
