"""3D data for the step figures of the one-octave guide: model/octave.json.

The O4 module parts come from the CAD assembly GLB (one node per part id). Each part is stored once
(positions as int16 at 0.01 mm in module coordinates = x from the module's left edge, y from the white-key
front, z from the desk; indices as uint16 per part), all in one base64 blob. "views" lists, per figure of the
guide, which parts are shown, in which colour (parts already in place are faded toward grey, the new parts of
the step keep their colour), how transparent (the frame is a ghost where it would hide the levers), how far an
exploded part is moved, and the start camera. The selection rules are the same as src/render_steps.py.

usage: python3 make_models.py      (writes ../model/octave.json)
"""
import base64
import json
import os

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
CAD = os.path.join(ROOT, "hardware", "mechanical", "cad")
OUT = os.path.normpath(os.path.join(HERE, "..", "model", "octave.json"))
X0 = 540.5          # O4 module left edge in world x
Q = 0.01            # mm per int16 step


def has(*keys):
    return lambda i: any(k in i for k in keys)


FRAME = has("O4-FRAME", "O4-CAGE", "O4-TAB-")          # A12 (2026-10-29): bed + lever cage + guide tabs
BED = has("O4-FRAME")
CAGE = has("O4-CAGE")
TABS = has("O4-TAB-")
PINS = has("balancepin")
KEYROD = has("keyrodSUS")
FELTS = has("whitefrontfelt", "blackfrontfelt", "keeperfelt")
BOARD = has("O4-E-MB", "O4-E-ZERO", "O4-E-MUX", "controlboardscrew")
SENSOR = has("O4-E-SB", "O4-SENSORBAR", "SBSCREW")
LEVER = has("O4-LEVER-", "O4-LEVERCOVER-", "O4-STEEL-", "O4-FELTSTRIP-", "O4-SPRING-")
LEVROD = has("leverrodD4", "O4-PLUG")
KEYPART = has("O4-KEY-", "O4-CAPSTAN-", "O4-NUT-", "O4-MAGNET-", "O4-RESTFELT-")   # A15: the capstan nut is back
BLACK = lambda i: i.endswith("s") and KEYPART(i)
WHITE = lambda i: (not i.endswith("s")) and KEYPART(i)
PADS = has("PADBAR", "upstoppad")
CURTAIN = has("O4-CURTAIN")
EVA = has("O4-EVA")
ALL = lambda i: True

FRONT = (-140, -260, 260, 85, 110, 30)
REAR = (330, 520, 300, 85, 110, 30)
BELOW = (-280, -360, -520, 90, 125, 20)
SIDE = (-230, 430, 260, 80, 150, 30)

# figure: (shown, new = full colour, ghost ids, camera)
STEPS = {
    "s1_frame": (lambda i: FRAME(i) or PINS(i) or KEYROD(i) or FELTS(i), lambda i: PINS(i) or KEYROD(i) or FELTS(i), (), FRONT),
    # A13 (2026-10-30): the board sits on 4 posts on the closed hatch floor, screwed from above before the lever cage goes on
    "s2_board": (lambda i: BED(i) or TABS(i) or PINS(i) or KEYROD(i) or FELTS(i) or BOARD(i), BOARD, (), REAR),
    "s3_sensor": (lambda i: FRAME(i) or PINS(i) or KEYROD(i) or FELTS(i) or SENSOR(i), SENSOR, (), FRONT),
    "s4_levers": (lambda i: FRAME(i) or BOARD(i) or SENSOR(i) or LEVER(i), LEVER, ("O4-FRAME", "O4-CAGE"), REAR),
    "s5_levrod": (lambda i: FRAME(i) or BOARD(i) or SENSOR(i) or LEVER(i) or LEVROD(i), LEVROD, ("O4-FRAME", "O4-CAGE"), SIDE),
    "s6_black": (lambda i: not (WHITE(i) or PADS(i) or CURTAIN(i) or EVA(i)), BLACK, (), FRONT),
    "s7_white": (lambda i: not (PADS(i) or CURTAIN(i) or EVA(i)), WHITE, (), FRONT),
    "s8_pads": (lambda i: not (CURTAIN(i) or EVA(i)), PADS, ("O4-FRAME", "O4-CAGE"), REAR),
    "s9_curtain": (lambda i: not EVA(i), CURTAIN, (), FRONT),
    "s10_done": (ALL, EVA, (), BELOW),
}


def sub(prefix, note):
    return lambda i: any(i == "O4-%s-%s" % (k, note) for k in prefix)


KEYP = ("KEY", "CAPSTAN", "NUT", "MAGNET", "RESTFELT")
LEVP = ("LEVER", "LEVERCOVER", "STEEL", "FELTSTRIP", "SPRING")
KEY_EX = {"MAGNET": (0, 0, -14), "CAPSTAN": (0, 0, 16), "NUT": (16, 0, 0), "RESTFELT": (0, 0, -12)}
LEV_EX = {"STEEL": (0, 0, -30), "FELTSTRIP": (0, 0, -50), "SPRING": (18, 0, 0), "LEVERCOVER": (16, 0, -30)}
SUBS = {
    "k_white": (sub(KEYP, "D"), KEY_EX, (265, -235, -150, 35, 110, 28)),
    "k_black": (sub(KEYP, "Ds"), KEY_EX, (270, -170, -150, 49, 120, 30)),
    "l_lever": (sub(LEVP, "D"), LEV_EX, (230, 70, -60, 40, 175, 10)),
    # A12 frame in three prints: bed, guide tabs lifted 28, lever cage lifted 48
    "s0_split": (FRAME, {"CAGE": (0, 0, 48), "TAB": (0, 0, 28)}, (-170, -250, 300, 85, 110, 35)),
}


def fade(c, k=0.55):
    r, g, b = (int(c[j:j + 2], 16) for j in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(v + (225 - v) * k) for v in (r, g, b))


def main():
    man = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
    info = {p["id"]: p for p in man["parts"] if p["group"].startswith("O4")}
    sc = trimesh.load(os.path.join(CAD, "Toccata_전체조립.glb"), force="scene")
    meshes = {}
    for node in sc.graph.nodes_geometry:
        if node in info:
            T, g = sc.graph[node]
            m = sc.geometry[g].copy()
            m.apply_transform(T)
            meshes[node] = m
    missing = sorted(set(info) - set(meshes))
    if missing:
        raise SystemExit("octave model: parts missing in the GLB: %s" % missing)

    ids = sorted(meshes)
    pos, idx, parts = [], [], []
    vo = io = 0
    for i in ids:
        m = meshes[i]
        v = np.round((m.vertices - [X0, 0, 0]) / Q)
        if np.abs(v).max() > 32767 or len(m.vertices) > 65535:
            raise SystemExit("octave model: %s does not fit int16/uint16" % i)
        pos.append(v.astype("<i2").ravel())
        idx.append(np.asarray(m.faces, dtype="<u2").ravel())
        parts.append({"id": i, "name": info[i]["name_ko"], "c": info[i]["color"],
                      "vo": vo, "vn": len(m.vertices), "io": io, "in": int(m.faces.size)})
        vo += len(m.vertices)
        io += int(m.faces.size)
    pos = np.concatenate(pos)
    idx = np.concatenate(idx)
    blob = pos.tobytes() + idx.tobytes()
    at = {p["id"]: k for k, p in enumerate(parts)}

    views = {}
    for name, (sel, new, ghost, cam) in STEPS.items():
        rows = []
        for i in ids:
            if not sel(i):
                continue
            c = info[i]["color"] if new(i) else fade(info[i]["color"])
            rows.append([at[i], c, 0.22 if i in ghost else 1, 0, 0, 0])
        views[name] = {"parts": rows, "cam": cam}
    for name, (sel, ex, cam) in SUBS.items():
        rows = []
        for i in ids:
            if sel(i):
                d = ex.get(i.split("-")[1], (0, 0, 0))
                rows.append([at[i], info[i]["color"], 1] + list(d))
        views[name] = {"parts": rows, "cam": cam}

    out = {"about": "Toccata O4 module, mm, x from the module left edge, y from the white-key front, z from the desk; "
                    "int16 positions x %.2f mm then uint16 indices per part (base64 'bin'). Built by make_models.py." % Q,
           "q": Q, "nv": int(vo), "ni": int(io), "parts": parts, "views": views,
           "bin": base64.b64encode(blob).decode("ascii")}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("octave model: %d parts, %d vertices, %d triangles, %d views, %.0f KB"
          % (len(parts), vo, io // 3, len(views), os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
