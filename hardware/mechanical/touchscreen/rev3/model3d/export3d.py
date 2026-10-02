"""Write the rev-3 B1 preview model: per-part STLs (world / assembly pose), GLBs and a small local viewer.

  stl/use/     25 deg use state (leg foot in the pocket)        <- the assembly pose
  stl/heel22/  22 deg (heel on the stop block, leg resting on the pocket ramp)
  stl/fold/    90 deg folded transport state (leg clipped on the cradle back)
  stl/context/ simplified L2 rear bar ('L2 잠정 외형') + Pi 5 + L2 contents (boxes)
  touch_B1_use.glb   touchscreen group (use) + nearby context (L2 simplified, modules O3..O5)
  touch_B1_fold.glb  same, folded
  viewer_B1.html     local three.js viewer (both states in one embedded GLB, toggle)
  parts_manifest.json
"""
import base64
import json
import os

import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

import b1model as B
from cadlib import mesh_arrays
from meshclean import clean_arrays


def write_arrays(v, f, path, header):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ln[ln == 0] = 1
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n / ln[:, None]
    rec["v"] = tri
    with open(path, "wb") as fh:
        fh.write(header.encode("ascii", "replace")[:80].ljust(80, b" "))
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(rec.tobytes())

HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "stl")
GLB_UNITS = ["O3", "O4", "O5"]


def watertight(path):
    """re-read the written STL the way a slicer does (vertices merged by position): closed and every edge on exactly 2 faces?"""
    m = trimesh.load(path, process=True)
    return bool(m.is_watertight), bool(m.is_winding_consistent)


def write_parts(parts, sub):
    rows = []
    for p in parts:
        path = os.path.join(STL, sub, p.id + ".stl")
        b = p.solid.bounding_box()
        v, f, ok, nbad = clean_arrays(p.solid)
        write_arrays(v, f, path, "Toccata R31 rev3a B1 %s %s world mm (preview only, not a print file)" % (p.id, sub))
        wt, wc = watertight(path)
        rows.append({"id": p.id, "name_ko": p.name, "kind": p.kind, "color": p.color, "material": p.material,
                     "file": os.path.relpath(path, HERE), "bbox": [round(v, 2) for v in b], "volume_mm3": round(p.solid.volume(), 1),
                     "watertight": wt, "winding_ok": wc})
    return rows


_mats = {}


def _mat(color, alpha=1.0):
    k = (color, alpha)
    if k not in _mats:
        c = color.lstrip("#")
        rgba = [int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0, alpha]
        _mats[k] = PBRMaterial(name="c%s_%d" % (c, int(alpha * 100)), baseColorFactor=rgba, metallicFactor=0.0, roughnessFactor=0.7,
                               alphaMode="BLEND" if alpha < 1 else "OPAQUE")
    return _mats[k]


def add_solid(scene, name, solid, color):
    v, f = mesh_arrays(solid)
    m = trimesh.Trimesh(vertices=v.astype(np.float32), faces=f, process=False)
    m.visual = trimesh.visual.TextureVisuals(material=_mat(color))
    scene.add_geometry(m, node_name=name, geom_name=name)


def add_stl(scene, name, path, color):
    m = trimesh.load(path, process=True)
    m.visual = trimesh.visual.TextureVisuals(material=_mat(color))
    scene.add_geometry(m, node_name=name, geom_name=name)


def context_scene(scene):
    for p in B.context_parts():
        if p.id == "L2-FEET":
            continue
        add_solid(scene, "ctx__" + p.id, p.solid, p.color)
    for (f, c, n) in B.module_stls(GLB_UNITS):
        add_stl(scene, "ctx__" + n, f, c)


def main():
    use, use_info = B.touch_parts(B.TH_USE)
    heel, heel_info = B.touch_parts(B.TH_HEEL)
    fold, fold_info = B.touch_parts(B.TH_FOLD)
    ctx = B.context_parts()
    man = {"src": B.SRC, "frames": "world mm: x from the A0 left boundary, y from the white-key front lip (away from the player), z from the desk",
           "poses": {"use": B.TH_USE, "heel22": B.TH_HEEL, "fold": B.TH_FOLD},
           "pose_info": {"use": use_info, "heel22": heel_info, "fold": fold_info},
           "estimates": B.EST,
           "parts": {"use": write_parts(use, "use"), "heel22": write_parts(heel, "heel22"), "fold": write_parts(fold, "fold"),
                     "context": write_parts(ctx, "context")},
           "context_note": "L2 잠정 외형: 확정 L2 값(L2_cu.json + body_L2.json)으로 만든 단순 모양 - 판·홈·그릴은 CAD가 정함",
           "stl_note": "미리보기 전용 STL (출력용 아님). 출력 STL은 CAD 세션이 만듦."}
    json.dump(man, open(os.path.join(HERE, "parts_manifest.json"), "w"), ensure_ascii=False, indent=1,
              default=lambda o: [float(x) for x in o] if isinstance(o, (tuple, list, np.ndarray)) else float(o))
    for tag, parts in (("use", use), ("fold", fold)):
        sc = trimesh.Scene()
        context_scene(sc)
        for p in parts:
            add_solid(sc, "%s__%s" % (tag, p.id), p.solid, p.color)
        sc.export(os.path.join(HERE, "touch_B1_%s.glb" % tag))
    # combined for the viewer (context once, both states)
    sc = trimesh.Scene()
    context_scene(sc)
    for tag, parts in (("use", use), ("fold", fold)):
        for p in parts:
            add_solid(sc, "%s__%s" % (tag, p.id), p.solid, p.color)
    glb = sc.export(file_type="glb")
    names = {p.id: p.name for p in use + fold + ctx}
    html = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
    html = html.replace("__GLB_B64__", base64.b64encode(glb).decode()).replace("__NAMES__", json.dumps(names, ensure_ascii=False))
    html = html.replace("__SRC__", "수치: %s · %s · 뒷바는 L2 잠정 외형" % (B.SRC["numbers"], B.SRC["l2"]))
    open(os.path.join(HERE, "viewer_B1.html"), "w", encoding="utf-8").write(html)
    for f in ("touch_B1_use.glb", "touch_B1_fold.glb", "viewer_B1.html"):
        print(f, round(os.path.getsize(os.path.join(HERE, f)) / 1e6, 2), "MB")
    print("stl", sum(len(v) for v in man["parts"].values()), "files")
    bad = [(k, r["id"]) for k, v in man["parts"].items() for r in v if not r["watertight"]]
    print("not watertight:", bad)


if __name__ == "__main__":
    main()
