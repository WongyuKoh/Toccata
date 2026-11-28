"""3D data for the rod-cut-jig simulation of the guide (step 02): model/rodjig.json.

Meshes straight from hardware/mechanical/cad/src/rod_cut_jig.py (the same solids as the STLs in
stl/print/10_봉절단지그), in jig coordinates: x along the rod (0 = the plug stub tip = rod stop, the saw slot near
face at x = L), y across, z up from the desk. The plug is stored in its installed pose (flange on the stop-block
outer face, stub pointing +x into the bore). Positions int16 at 0.01 mm, indices uint16, one base64 blob.

usage: python3 make_rodjig.py      (writes ../model/rodjig.json)
"""
import base64
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "hardware", "mechanical", "cad", "src"))
import rod_cut_jig as R  # noqa: E402
from cadlib import mesh_arrays, orient  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "model", "rodjig.json"))
Q = 0.01


def main():
    J = R.J
    blob, meshes = bytearray(), {}

    def add(name, solid):
        v, f = mesh_arrays(solid)
        assert len(v) < 65536
        q = np.round(v / Q).astype(np.int16)
        o = len(blob)
        blob.extend(q.tobytes())
        if len(blob) % 4:
            blob.extend(b"\0" * (4 - len(blob) % 4))
        oi = len(blob)
        blob.extend(f.astype(np.uint16).tobytes())
        if len(blob) % 4:
            blob.extend(b"\0" * (4 - len(blob) % 4))
        meshes[name] = {"v": [o, len(v)], "i": [oi, int(f.size)]}

    jigs = []
    for key, L, who, count, rng in R.LENGTHS:
        add("jig" + key, R.jig(key, L, who, count, rng))
        jigs.append({"key": key, "L": L, "who": who.replace("_", " "), "count": count, "range": rng,
                     "file": "봉절단지그_%s_%s__1개.stl" % (key, who)})
    # plug: printed flange-down (z0..flange_t), stub up; installed = stub along +x, flange outer face at x = -(stub + flange_t)
    p = R.plug()                                       # z: 0 .. flange_t + stub
    rot = ((0, 0, 1), (0, -1, 0), (1, 0, 0))           # proper rotation: local z -> +x, local x -> +z (pull tab up), y -> -y
    ps = orient(p, rot)
    ps = ps.translate((-(J["stub"] + J["flange_t"]), 0, J["ax_z"]))
    add("plug", ps)
    data = {"q": Q, "blob": base64.b64encode(bytes(blob)).decode(), "meshes": meshes, "jigs": jigs,
            "J": {k: J[k] for k in ("ax_z", "bore", "stub", "kerf", "slot_floor", "blk_top", "out", "plate_w", "flange_t", "win")}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print(OUT, os.path.getsize(OUT), "bytes")
    b = ps.bounding_box()
    print("plug bbox", [round(x, 2) for x in b])


if __name__ == "__main__":
    main()
