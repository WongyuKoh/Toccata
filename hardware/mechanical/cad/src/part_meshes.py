"""Print-unit meshes for the 3D views of the 03 tab (docs/report/toccata-v4/src/tabs/partdwg, 2026-10-30).

Every sheet in fin/parts/index.json has one print STL. Each STL is welded, quantized to uint16 inside its own box
and written as base64 into one JSON file per folder: fin/parts3d/g-<group>.json
    {"v": 1, "parts": {code: {"b": [x0, y0, z0, x1, y1, z1], "p": b64 uint16 xyz, "i": b64 indices, "i4": bool,
                              "nv": vertices, "nt": triangles, "na": triangles of the part itself}}}
Triangles from index na on are coloured apart by the page ("sup" says what they are): since A13 (2026-10-30) the faces
that Bambu Studio's support touches - the key tails' underside (tree support from the build plate, check_support.TREE_OK)
or, in a print that still needs support, its overhangs ("need"). The A12 print aids (tear-off comb, bed posts) are gone;
a second body in a file below AID_MAX of the main volume would still be put there (a bigger one stops the build).

fin/parts3d/index.json
    files   code -> mesh file
    parts   code -> {g group, n name, q quantity, m material, ids assembly ids}; groups: group -> codes in sheet order
    xf      code -> print -> world of the sheet's reference instance (data/<code>.json W, Q, o): world = R p + t,
            R row-major 3 x 3 (mm, z up, the CAD / GLB frame)
    split   assembly id -> codes, for CAD solids printed in several pieces (CU-PLY-BOTTOM, CU-PLY-BACK): the page
            draws those pieces from their STL instead of the one GLB node
    hide    assembly ids the 04 tab does not show in the playing pose (fold-only TS-*-FOLD, floor group)
    unmapped  print-kind assembly ids that no sheet lists (expected: none)

usage: python3 hardware/mechanical/cad/src/part_meshes.py   (~10 s; part_sheets.py runs it after write_tab)
"""
import base64
import collections
import json
import math
import os
import sys

import numpy as np
import trimesh
from trimesh import graph

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(CAD)))
PAGE = os.path.join(REPO, "docs", "report", "toccata-v4")
OUT_REL = "fin/parts3d"
OUT = os.path.join(PAGE, OUT_REL)
PDATA = os.path.join(CAD, "drawings", "parts", "data")
AID_MAX = 0.15


def stl_path(f):
    return os.path.join(REPO, f) if f.startswith("hardware/") else os.path.join(CAD, f)


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


def support_faces(m, rel):
    """A13: faces that face the bed flatter than Bambu's 30 deg threshold, above the first layer, where check_support
    still finds overhangs - the key tails (Bambu tree support from the plate) or a print that still needs support."""
    import check_support as CS
    M = CS.load(stl_path(rel))
    need, tree = CS.split_tree(rel, CS.overhangs(M))
    need, _br = CS.split_bridges(rel, need)
    if not (need or tree):
        return None, None
    n, c = m.face_normals, m.triangles_center
    down = (n[:, 2] < -math.cos(math.radians(CS.ANGLE)) + 1e-6) & (c[:, 2] > m.bounds[0][2] + 0.25)
    near = np.zeros(len(c), bool)
    zc = c[:, 2] - m.bounds[0][2]
    for z, _a, (x0, y0, x1, y1), _h in (need or tree):       # A15: by layer too (the nut slot's ceiling is over the tail's box)
        near |= ((c[:, 0] > x0 - 0.6) & (c[:, 0] < x1 + 0.6) & (c[:, 1] > y0 - 0.6) & (c[:, 1] < y1 + 0.6)
                 & (np.abs(zc - z) < 0.6))
    return down & near, ("need" if need else "tree")


def mesh_entry(path, rel=None):
    m = trimesh.load(path, process=True)
    lab = graph.connected_component_labels(m.face_adjacency, node_count=len(m.faces))
    n = int(lab.max()) + 1
    vols = [abs(m.submesh([np.where(lab == k)[0]], append=True).volume) for k in range(n)]
    main = int(np.argmax(vols))
    for k in range(n):
        if k != main and vols[k] > AID_MAX * vols[main]:
            raise SystemExit("part_meshes: %s has a second body of %.0f mm3 (main %.0f) - not a print aid"
                             % (path, vols[k], vols[main]))
    late = lab != main                                       # print aids (none since A13)
    sup, kind = support_faces(m, rel) if rel else (None, None)
    if sup is not None:
        late = late | sup                                    # faces the slicer's support touches
    order = np.argsort(late, kind="stable")                  # the part's own faces first, then aids / support faces
    F = m.faces[order]
    lo, hi = m.bounds
    ext = np.where(hi - lo > 0, hi - lo, 1.0)
    q = np.round((m.vertices - lo) / ext * 65535).astype("<u2")
    i4 = len(m.vertices) > 65535
    idx = F.astype("<u4" if i4 else "<u2")
    return dict(b=[round(float(v), 4) for v in list(lo) + list(hi)], p=b64(q), i=b64(idx), i4=i4,
                nv=int(len(m.vertices)), nt=int(len(F)), na=int(np.sum(~late)), sup=kind)


def world_xf(code):
    p = os.path.join(PDATA, code + ".json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    if d.get("W") is None:
        return None
    W, Q, o = np.array(d["W"]), np.array(d["Q"]), np.array(d["o"])
    R = W[:, :3] @ Q
    t = W[:, 3] - W[:, :3] @ o
    return dict(R=[round(float(v), 9) for v in R.ravel()], t=[round(float(v), 4) for v in t], inst=d["inst"])


# CAD solids printed in pieces (2026-10-16 A안) have no sheet transform: part_sheets registers a print file to a whole
# instance. body.lap_pieces cuts the panel at SPLIT_X with LAP-long half laps, body.py turns piece k by R (below, as in
# its pieces=[...]) and the STL sits on the bed at its min corner, so world = R^T p + (piece world min - min(R^T p)).
PIECES = {"CU-PLY-BOTTOM": ("R_NONE", "R_FLIP", "R_NONE"), "CU-PLY-BACK": ("R_YMIN", "R_YMAX", "R_YMIN")}


def glb_vertices(node_id):
    """world vertices of one node of the 04 tab's GLB (uint16 KHR_mesh_quantization, node scale + translation)."""
    import struct
    b = base64.b64decode(open(os.path.join(PAGE, "cad", "toccata.glb.b64.txt")).read())
    jl = struct.unpack("<I", b[12:16])[0]
    J = json.loads(b[20:20 + jl])
    bin_ = b[28 + jl:]
    nd = next(n for n in J["nodes"] if n.get("name") == node_id)
    a = J["accessors"][J["meshes"][nd["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
    v = J["bufferViews"][a["bufferView"]]
    st = (v.get("byteStride") or 6) // 2
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    u = np.frombuffer(bin_, dtype="<u2", count=st * (a["count"] - 1) + 3, offset=off)
    q = np.stack([u[i::st][:a["count"]] for i in range(3)], axis=1).astype(float)
    return q * np.array(nd.get("scale", [1, 1, 1])) + np.array(nd.get("translation", [0, 0, 0]))


def piece_xf(split, boxes):
    """print -> world for the pieces of every split id; checked against the GLB solid: the pieces tile its box and
    their vertex planes along x (holes, edges) are the solid's own planes."""
    import body
    out = {}
    for pid, codes in split.items():
        Rs = PIECES[pid]
        b = boxes[pid]
        s1, s2 = body.SPLIT_X
        h = body.LAP / 2.0
        xs = [(b[0], s1 + h), (s1 - h, s2 + h), (s2 - h, b[3])]
        gx = np.unique(glb_vertices(pid)[:, 0])

        def on_planes(xs_):         # within 0.03 of a GLB vertex plane (uint16 steps of the GLB are ~0.011 mm here)
            j = np.clip(np.searchsorted(gx, xs_), 1, len(gx) - 1)
            return np.minimum(np.abs(gx[j] - xs_), np.abs(gx[j - 1] - xs_)) <= 0.03
        for k, code in enumerate(sorted(codes)):
            R = np.array(getattr(body, Rs[k]), dtype=float).round(12)
            P = trimesh.load(stl_path(PIECE_FILES[code]), process=True).vertices @ R      # R^T p, row vectors
            t = np.array([xs[k][0], b[1], b[2]]) - P.min(0)
            W = P + t
            lo, hi = W.min(0), W.max(0)
            want = np.array([xs[k][0], b[1], b[2], xs[k][1], b[4], b[5]])
            err = float(np.abs(np.r_[lo, hi] - want).max())
            px = np.unique(np.round(W[:, 0], 3))
            inner = px[(px > xs[k][0] + 0.2) & (px < xs[k][1] - 0.2) & (np.abs(px - s1) > h + 0.2) & (np.abs(px - s2) > h + 0.2)]
            hit = float(on_planes(inner).mean()) if len(inner) else 1.0
            if err > 0.02 or hit < 0.98:
                raise SystemExit("part_meshes: piece %s of %s does not fit the GLB solid (box err %.3f, x planes %.0f %%)"
                                 % (code, pid, err, 100 * hit))
            out[code] = dict(R=[round(float(v), 9) for v in R.T.ravel()], t=[round(float(v), 4) for v in t], inst=pid,
                             piece=k + 1, check=dict(box_err=round(err, 4), x_planes=round(hit, 3)))
    return out


PIECE_FILES = {}


def assembly_lists(ids_of):
    """ids the 04 tab hides in the playing pose + print-kind ids no sheet lists (from the 04 tab's cad/parts.json)."""
    D = json.load(open(os.path.join(PAGE, "cad", "parts.json"), encoding="utf-8"))
    floor = {gi for gi, g in enumerate(D["groups"]) if g.get("s") == "floor"}
    hide = sorted(p["id"] for p in D["parts"] if p.get("a") or p["g"] in floor)
    unmapped = sorted(p["id"] for p in D["parts"] if p["k"] == "print" and p["id"] not in ids_of and p["id"] not in hide)
    return hide, unmapped


def build(idx=None):
    if idx is None:
        idx = json.load(open(os.path.join(PAGE, "fin", "parts", "index.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    groups = collections.OrderedDict()
    files, xf, aids, meta = {}, {}, {}, {}
    ids_of = collections.defaultdict(list)
    for r in idx["parts"]:
        rel = r["file"] if not r["file"].startswith("hardware/") else os.path.relpath(os.path.join(REPO, r["file"]), CAD)
        e = mesh_entry(stl_path(r["file"]), rel)
        g = r["group"]
        groups.setdefault(g, {})[r["code"]] = e
        files[r["code"]] = "%s/g-%s.json" % (OUT_REL, g.lower())
        meta[r["code"]] = dict(g=g, n=r["name"], q=r["qty"], m=r["material"], ids=r["ids"])
        w = world_xf(r["code"])
        if w is not None:
            xf[r["code"]] = w
        if e["na"] < e["nt"]:
            aids[r["code"]] = e["nt"] - e["na"]
        for i in r["ids"]:
            ids_of[i].append(r["code"])
        PIECE_FILES[r["code"]] = r["file"]
    for fn in os.listdir(OUT):
        if fn.startswith("g-") and fn.endswith(".json"):
            os.remove(os.path.join(OUT, fn))
    sizes = {}
    for g, parts in groups.items():
        p = os.path.join(PAGE, files[next(iter(parts))])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(dict(v=1, parts=parts), f, separators=(",", ":"))
        sizes[os.path.basename(p)] = os.path.getsize(p)
    split = {i: c for i, c in sorted(ids_of.items()) if len(c) > 1}
    D = json.load(open(os.path.join(PAGE, "cad", "parts.json"), encoding="utf-8"))
    boxes = {p["id"]: p["b"] for p in D["parts"]}
    xf.update(piece_xf(split, boxes))
    for i, cs in split.items():
        miss = [c for c in cs if c not in xf]
        if miss:
            raise SystemExit("part_meshes: %s is printed in pieces %s but %s have no world transform" % (i, cs, miss))
    hide, unmapped = assembly_lists(ids_of)
    index = dict(v=1, date="2026-10-30", source="hardware/mechanical/cad/src/part_meshes.py", files=files, parts=meta,
                 groups={g: list(p) for g, p in groups.items()}, xf=xf, split=split, hide=hide, unmapped=unmapped,
                 aids=aids, bytes=sizes)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    return index


def assets(index):
    return sorted(set(index["files"].values())) + [OUT_REL + "/index.json"]


if __name__ == "__main__":
    ix = build()
    tri = sum(1 for _ in ix["files"])
    print("part_meshes: %d parts in %d files (%s KB), %d with print aids, %d world transforms, split %s, hide %d, unmapped %s"
          % (tri, len(ix["bytes"]), round(sum(ix["bytes"].values()) / 1024), len(ix["aids"]), len(ix["xf"]),
             {k: len(v) for k, v in ix["split"].items()}, len(ix["hide"]), ix["unmapped"] or "none"))
    sys.exit(0)
