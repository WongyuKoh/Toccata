"""04 3D 모델 tab of the merged Toccata page (docs/report/toccata-v4/index.html, section id p-cad).

Writes, next to this file (hardware/mechanical/cad/viewer/):
  toccata_viewer.glb  viewer mesh: ONE glTF node per part (node name = Part.id) for all parts of build_all.collect(), including the
                      folded touchscreen (note 'altview') and the floor pedal (note 'offdesk'). Shapes that are equal up to a
                      translation (within 0.005 mm) share one mesh; positions are uint16 per mesh (KHR_mesh_quantization, step =
                      extent / 65535 per axis, <= 0.011 mm), indices uint16. Root node 'Toccata' turns the model's z-up millimetres
                      into glTF y-up metres, so other viewers open it at real size; cad.js ignores the root and works in mm.
  parts.json          part table + viewer data: groups, explode vectors, inside-view flags, key press sets, the fold spec,
                      view presets, 3D dimension lines, focus sets ("부분별로 보기"), overall box
  assets.json         which files merge.py ships next to the page (glb -> cad/toccata.glb.b64.txt, parts -> cad/parts.json)
  cad.html            the tab section <section class="page" id="p-cad" hidden>
Hand-written (not generated): cad.css, cad.js.

Every number comes from the solids of build_all.collect() (the same solids as stl/print and manifest.json), the key-action
geometry (key-action-v4/model/geometry.json + DESIGN.md S24 settled dip angles) and touchscreen_rev3.py (fold pose).
Never runs build_all.main() (that wipes stl/print).

    python3 hardware/mechanical/cad/viewer/gen_viewer.py      (~10 s)
build_all.main() also calls main() after a full build.
"""
import collections
import hashlib
import html
import json
import math
import os
import re
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(CAD, "..", "..", ".."))
sys.path.insert(0, os.path.join(CAD, "src"))

import body  # noqa: E402
import touchscreen_rev3 as TS  # noqa: E402
import make_readme  # noqa: E402
from annotate_parts import family_of, merged_dims  # noqa: E402
from cadlib import mesh_arrays  # noqa: E402

GLB_NAME = "toccata_viewer.glb"
KIND = collections.OrderedDict([("print", "출력"), ("bought", "구매"), ("electronics", "전자"), ("consumable", "소모품"), ("plywood", "합판")])
X_O4 = 47 + 164.5 * 3

# ---- key action (key-action-v4/model/geometry.json key_points; DESIGN.md S24 / results.txt r4.4 dip export) -------------
KEY_AXIS = (141.0, 21.5)          # K: key rod axis (y, z)
LEVER_AXIS = (203.25, 33.5)       # L: lever rod axis (y, z)
# settled 1 N bottom with the pad, front-point angle about K (white / black)
KEY_DIP = {"w": 4.05, "b": 6.08}
# lever settled dip 10.750 / 8.971 deg minus its rest angle b_rest -1.090 / -0.552 deg (metrics.json b_rest_w / b_rest_b)
LEVER_DIP = {"w": 11.84, "b": 9.52}

# ---- explode (mm at slider 100 %), model coordinates ------------------------------------------------------------------------
EX_REAR = 250.0                   # rear unit moves back
EX_LID = 130.0                    # side lids up
EX_SCREEN = 200.0                 # screen lid + touchscreen up
BAFFLE_N = (0.0, -math.sin(math.radians(body.ANGLE)), math.cos(math.radians(body.ANGLE)))   # outward normal of the 40 deg baffle
MOD_RX = re.compile(r"^(O[1-7]|EL|ER)-(.*)$")


def f(v, nd=2):
    return make_readme.f(v, nd)


def esc(s):
    return html.escape(str(s), quote=True)


def explode_vec(p):
    """explode offset (dx, dy, dz) at 100 % for one part."""
    pid = p.id
    if p.note == "offdesk":
        return (0.0, 0.0, 0.0)
    m = MOD_RX.match(pid)
    if m:
        rest = m.group(2)
        if rest.startswith("C-USB"):
            return (0.0, EX_REAR / 2, -35.0)
        if rest.startswith(("C-RIBBON", "C-EXT", "C-LEAD", "SENSORBAR", "SBSCREW", "B-controlboardscrew")):
            return (0.0, 0.0, -70.0)
        if rest.startswith("E-J701"):
            return (0.0, 0.0, 0.0)
        if rest.startswith("E-"):
            return (0.0, 0.0, -70.0)
        if rest.startswith(("KEY-", "CAPSTAN-", "NUT-", "MAGNET-", "B-keyrod")):
            return (0.0, 0.0, 70.0)
        if rest.startswith(("LEVER-", "STEEL-", "FELTSTRIP-", "SPRING-", "B-leverrod", "PLUG")):
            return (0.0, 0.0, 140.0)
        if rest.startswith(("PADBAR", "B-upstoppad", "CURTAIN")):
            return (0.0, 0.0, 210.0)
        return (0.0, 0.0, 0.0)
    if pid.startswith("C-XH-"):
        return (0.0, 0.0, -70.0)
    if pid.startswith("BRK2-"):
        return (0.0, EX_REAR / 2, 0.0)
    dx, dy, dz = 0.0, EX_REAR, 0.0
    if pid in ("LID-L", "LID-R") or pid.startswith("CU-MAG-LID-"):
        dz += EX_LID
    elif pid == "CU-SCREENLID" or pid.startswith(("CU-M3X10-", "TS-")):
        dz += EX_SCREEN
    elif re.match(r"^SPK[LR]-(GRILLE|BAFFLE|INS-|GASKET)", pid):
        k = 140.0 if "GRILLE" in pid else 50.0 if "GASKET" in pid else 90.0
        dy += BAFFLE_N[1] * k
        dz += BAFFLE_N[2] * k
    elif re.match(r"^SPK[LR]-PLY-SIDEOUT$", pid) or pid.startswith("DUCT-CAP-"):
        dx += -70.0 if pid.endswith(("L", "-L")) or pid.startswith("SPKL") else 70.0
    elif pid in ("CU-PLY-BACK", "PR-BACKPLATE", "CU-E-J501BOARD", "CU-E-J501", "CU-E-SWITCH") or re.match(r"^SPK[LR]-PLY-BACK$", pid):
        dy += 70.0
    elif pid.startswith("FOOT-"):
        dz -= 40.0
    return (dx, dy, dz)


def inside_hide(p):
    """True = hidden by 내부 보기 (lids, screen, baffles / grilles, speaker outer walls, key tops, pad bars, curtains)."""
    pid = p.id
    if pid in ("LID-L", "LID-R", "CU-SCREENLID") or pid.startswith(("CU-MAG-LID-", "CU-M3X10-", "TS-", "DUCT-CAP-")):
        return True
    if re.match(r"^SPK[LR]-(GRILLE|BAFFLE|INS-|GASKET|PLY-SIDEOUT|PLY-TOP)", pid):
        return True
    m = MOD_RX.match(pid)
    if m and m.group(2).startswith(("KEY-", "CAPSTAN-", "NUT-", "MAGNET-", "PADBAR", "B-upstoppad", "CURTAIN")):
        return True
    return False


def group_section(g):
    if g == "댐퍼 페달 (바닥)":
        return "floor"
    if "접은 상태" in g:
        return "alt"
    if re.match(r"^O[1-7] 전자부$", g) or g in ("CU 칸 전자부", "케이블", "끝 부속 왼쪽 전자부", "끝 부속 오른쪽 전자부"):
        return "elec"
    if re.match(r"^O[1-7] ", g):
        return "mod"
    if g.startswith("끝 부속"):
        return "end"
    if g == "터치스크린":
        return "ts"
    return "body"


SECTION_TITLE = collections.OrderedDict([("mod", "건반 모듈 O1~O7"), ("end", "끝 부속 (A0~B0, C8)"), ("body", "뒷바 (스피커·가운데 유닛)"),
                                         ("elec", "전자 부품·케이블"), ("ts", "터치스크린"), ("floor", "바닥 (기본 숨김)")])
LAYERS = ["백건", "흑건", "레버", "프레임", "구매품", "전자부"]


# ------------------------------------------------------------------ GLB writer
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def write_glb(parts, path):
    """one node per part (index i + 1, name = id), shared meshes for translated copies, uint16 quantised positions."""
    bin_ = bytearray()

    def add_view(data, target):
        while len(bin_) % 4:
            bin_.append(0)
        off = len(bin_)
        bin_.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    views, accessors, meshes, materials, nodes = [], [], [], [], []
    mat_of = {}
    geo = {}           # signature -> list of (canonical local verts, pos accessor, idx accessor, scale)
    mesh_of = {}       # (geo key, color) -> mesh index
    stats = {"shared": 0, "unique": 0, "tris": 0, "max_err": 0.0, "max_step": 0.0}
    for p in parts:
        v, fc = mesh_arrays(p.solid)
        v = np.asarray(v, dtype=np.float64)
        fc = np.asarray(fc, dtype=np.int64)
        mn = v.min(axis=0)
        loc = v - mn
        ext = loc.max(axis=0)
        sig = (len(v), len(fc), hashlib.sha1(fc.astype(np.uint32).tobytes()).hexdigest(), tuple(np.round(ext, 1)))
        hit = None
        for cand in geo.get(sig, []):
            err = float(np.abs(cand[0] - loc).max())
            if err < 0.005:
                hit = cand
                stats["max_err"] = max(stats["max_err"], err)
                break
        if hit is None:
            scale = np.where(ext > 0, ext / 65535.0, 1.0)
            q = np.clip(np.round(loc / scale), 0, 65535).astype(np.uint16)
            qerr = float(np.abs(q * scale - loc).max())
            stats["max_step"] = max(stats["max_step"], float(scale.max()))
            pad = np.zeros((len(q), 4), dtype=np.uint16)
            pad[:, :3] = q
            pv = add_view(pad.tobytes(), 34962)
            views[pv]["byteStride"] = 8
            accessors.append({"bufferView": pv, "componentType": 5123, "type": "VEC3", "count": int(len(q)),
                              "min": [int(x) for x in q.min(axis=0)], "max": [int(x) for x in q.max(axis=0)]})
            pa = len(accessors) - 1
            if len(v) <= 65535:
                iv = add_view(fc.astype(np.uint16).ravel().tobytes(), 34963)
                accessors.append({"bufferView": iv, "componentType": 5123, "type": "SCALAR", "count": int(fc.size)})
            else:
                iv = add_view(fc.astype(np.uint32).ravel().tobytes(), 34963)
                accessors.append({"bufferView": iv, "componentType": 5125, "type": "SCALAR", "count": int(fc.size)})
            ia = len(accessors) - 1
            hit = (loc, pa, ia, scale, qerr)
            geo.setdefault(sig, []).append(hit)
            stats["unique"] += 1
            stats["tris"] += int(len(fc))
            stats["max_err"] = max(stats["max_err"], qerr)
        else:
            stats["shared"] += 1
        col = p.color.lstrip("#").lower()
        if col not in mat_of:
            rgb = [srgb_to_linear(int(col[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]
            materials.append({"name": "c" + col, "pbrMetallicRoughness": {"baseColorFactor": [round(c, 5) for c in rgb] + [1.0],
                                                                           "metallicFactor": 0.0, "roughnessFactor": 0.8}})
            mat_of[col] = len(materials) - 1
        mk = (hit[1], col)
        if mk not in mesh_of:
            meshes.append({"name": p.id, "primitives": [{"attributes": {"POSITION": hit[1]}, "indices": hit[2], "mode": 4,
                                                          "material": mat_of[col]}],
                           "extras": {"qscale": [float(s) for s in hit[3]]}})
            mesh_of[mk] = len(meshes) - 1
        nodes.append({"name": p.id, "mesh": mesh_of[mk], "translation": [round(float(c), 4) for c in mn],
                      "scale": [float(s) for s in hit[3]]})
    root = {"name": "Toccata", "rotation": [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)], "scale": [0.001, 0.001, 0.001],
            "children": list(range(1, len(nodes) + 1)),
            "extras": {"units": "mm (root scales to m)", "coords": "x across (0 = A0 left end), y from the white-key front lip "
                       "backwards, z up from the desk; root turns z-up into glTF y-up", "parts": len(nodes)}}
    while len(bin_) % 4:
        bin_.append(0)
    gltf = {"asset": {"version": "2.0", "generator": "Toccata gen_viewer.py"}, "scene": 0, "scenes": [{"nodes": [0]}],
            "nodes": [root] + nodes, "meshes": meshes, "materials": materials, "accessors": accessors, "bufferViews": views,
            "buffers": [{"byteLength": len(bin_)}], "extensionsUsed": ["KHR_mesh_quantization"],
            "extensionsRequired": ["KHR_mesh_quantization"]}
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    while len(js) % 4:
        js += b" "
    total = 12 + 8 + len(js) + 8 + len(bin_)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A))
        fh.write(js)
        fh.write(struct.pack("<II", len(bin_), 0x004E4942))
        fh.write(bytes(bin_))
    stats["bytes"] = total
    stats["meshes"] = len(meshes)
    return stats


# ------------------------------------------------------------------ fold spec (touchscreen 25 deg use -> 90 deg folded)
def rot_yz(v, ang, y0, z0):
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    v = np.array(v, dtype=float)
    dy, dz = v[:, 1] - y0, v[:, 2] - z0
    v[:, 1] = y0 + dy * c - dz * s
    v[:, 2] = z0 + dy * s + dz * c
    return v


def fold_spec(parts, idx):
    """cradle-attached parts turn about the hinge axis by -(90 - 25); the leg first swings back onto the cradle about its own
    pivot by 65 + LEG_ANGLE (lies along u), then rides with the cradle. At 100 % the exact folded solids ('altview') replace them."""
    ang = -(TS.TILT_FOLD - TS.TILT_USE)
    leg_ang = (TS.TILT_FOLD - TS.TILT_USE) + TS.LEG_ANGLE
    alt = [p.id for p in parts if p.note == "altview"]
    use = [a[:-5] for a in alt if a.endswith("-FOLD") and a[:-5] in idx]
    move = [p.id for p in parts if p.id.startswith("TS-") and p.note != "altview" and p.id not in ("TS-LEG", "TS-RCLIP")
            and not p.id.startswith(("TS-M3X20-HINGE", "TS-C-"))]
    hide = [p.id for p in parts if p.id.startswith("TS-C-")]
    opt = [a for a in alt if not a.endswith("-FOLD")]            # optional screen cover (stl/print_extra), not drawn
    # self-check: the moved use solids land on the folded solids
    byid = {p.id: p for p in parts}
    worst = 0.0
    for u in use:
        v, _ = mesh_arrays(byid[u].solid)
        if u == "TS-LEG":
            v = rot_yz(v, leg_ang, TS.LEG_AX_YZ[0], TS.LEG_AX_YZ[1])
        w = rot_yz(v, ang, TS.AX_Y, TS.AX_Z)
        b = np.array(byid[u + "-FOLD"].solid.bounding_box())
        worst = max(worst, float(np.abs(np.r_[w.min(0), w.max(0)] - b).max()))
    assert worst < 0.1, "fold transform does not land on the altview solids (%.3f mm)" % worst
    return {"axis": [TS.AX_Y, TS.AX_Z], "ang": round(ang, 4),
            "leg": {"i": idx["TS-LEG"], "pivot": [round(TS.LEG_AX_YZ[0], 4), round(TS.LEG_AX_YZ[1], 4)], "ang": round(leg_ang, 4)},
            "move": [idx[i] for i in move], "use": [idx[i] for i in use], "alt": [idx[i] for i in alt if i not in opt],
            "opt": [idx[i] for i in opt], "hide": [idx[i] for i in hide], "check_mm": round(worst, 3)}


# ------------------------------------------------------------------ key press sets
def key_sets(parts, idx):
    out = []
    for p in parts:
        m = re.match(r"^(O[1-7]|EL|ER)-KEY-(\w+)$", p.id)
        if not m:
            continue
        pre, s = m.group(1), m.group(2)
        black = p.name_ko.startswith("흑건")
        kk = [idx[i] for i in ("%s-KEY-%s" % (pre, s), "%s-CAPSTAN-%s" % (pre, s), "%s-NUT-%s" % (pre, s), "%s-MAGNET-%s" % (pre, s)) if i in idx]
        ll = [idx[i] for i in ("%s-LEVER-%s" % (pre, s), "%s-STEEL-%s" % (pre, s), "%s-FELTSTRIP-%s" % (pre, s), "%s-SPRING-%s" % (pre, s)) if i in idx]
        assert len(kk) == 4 and len(ll) == 4, p.id
        out.append({"n": p.name_ko.split()[-1], "b": 1 if black else 0, "k": kk, "l": ll})
    out.sort(key=lambda r: min(parts[i].solid.bounding_box()[0] for i in r["k"][:1]))
    return out


# ------------------------------------------------------------------ dimension lines (model coordinates)
def dims():
    yb, zt, y0 = body.YB, body.SPK_ZT, body.Y0
    dy0, dy1 = body.DUCT_Y
    F, T = body.SL_A, body.SL_B
    P = TS.POINTS
    xs = TS.XC + TS.CR_XR[1] + 14.0
    yf, zf = P["use"]["cr_bot_front"]
    yt, zt2 = P["use"]["cr_top_front"]
    return [
        {"t": "1254 전체 가로", "a": [-16, -45, 0], "b": [1238, -45, 0], "ea": [-16, 0, 0], "eb": [1238, 0, 0]},
        {"t": "%s 전체 깊이" % f(yb), "a": [-70, 0, 0], "b": [-70, yb, 0], "ea": [-16, 0, 0], "eb": [-16, yb, 0]},
        {"t": "212 건반 모듈 깊이", "a": [1290, 0, 0], "b": [1290, 212, 0], "ea": [1238, 0, 0], "eb": [1238, 212, 0]},
        {"t": "케이블 통로 y%s~%s" % (f(dy0, 0), f(dy1, 0)), "a": [1290, dy0, 0], "b": [1290, dy1, 0], "ea": [1238, dy0, 0], "eb": [1238, dy1, 0]},
        {"t": "%s 뒷바 (y%s~%s)" % (f(yb - y0), f(y0, 0), f(yb)), "a": [1340, y0, 0], "b": [1340, yb, 0], "ea": [1238, y0, 0], "eb": [1238, yb, 0]},
        {"t": "164.5 옥타브 모듈 O4", "a": [X_O4, -20, 72.85], "b": [X_O4 + 164.5, -20, 72.85], "ea": [X_O4, 0, 72.85], "eb": [X_O4 + 164.5, 0, 72.85]},
        {"t": "z%s 건반 윗면 = 가운데 뚜껑" % f(body.Z_LID), "a": [611, yb + 12, 0], "b": [611, yb + 12, body.Z_LID]},
        {"t": "z%s 스피커 윗면" % f(zt), "a": [1260, yb, 0], "b": [1260, yb, zt]},
        {"t": "%s° 스피커 앞판 (경사 %s)" % (f(body.ANGLE, 1), f(body.SL_LEN)), "a": [-32, F[0], F[1]], "b": [-32, T[0], T[1]],
         "ea": [-16, F[0], F[1]], "eb": [-16, T[0], T[1]]},
        {"t": "케이블 통로 z%s~%s" % (f(body.DUCT_Z[0], 0), f(body.DUCT_Z[1], 0)), "a": [611, dy0 - 1, 0], "b": [611, dy0 - 1, body.DUCT_Z[1]]},
        {"t": "z43.5 백건 윗면", "a": [-40, 20, 0], "b": [-40, 20, 43.5]},
        {"t": "z%s 화면 받침 윗끝 (25°)" % f(zt2), "a": [xs, yt, TS.LID_TOP], "b": [xs, yt, zt2],
         "ea": [TS.XC + TS.CR_XR[1], yt, zt2], "eb": [xs, yt, zt2], "ts": 1},
        {"t": "y%s 화면 가장 앞" % f(yf), "a": [xs, 212.0, zf], "b": [xs, yf, zf], "ea": [TS.XC + TS.CR_XR[1], yf, zf], "eb": [xs, yf, zf], "ts": 1},
        {"t": "경첩 축 y%s z%s" % (f(TS.AX_Y), f(TS.AX_Z)), "a": [TS.XC - 140, TS.AX_Y, TS.LID_TOP], "b": [TS.XC - 140, TS.AX_Y, TS.AX_Z], "ts": 1},
    ]


# ------------------------------------------------------------------ view presets and focus sets
def views():
    """direction from the target to the eye (model coordinates); o = orthographic by default."""
    return collections.OrderedDict([
        ("front34", {"t": "앞 3/4", "d": [-871, -1100, 720], "o": 0}),
        ("back34", {"t": "뒤 3/4", "d": [-1131, 750, 600], "o": 0}),
        ("front", {"t": "정면", "d": [0, -1, 0], "o": 1}),
        ("back", {"t": "배면", "d": [0, 1, 0], "o": 1}),
        ("left", {"t": "좌측면", "d": [-1, 0, 0], "o": 1}),
        ("right", {"t": "우측면", "d": [1, 0, 0], "o": 1}),
        ("top", {"t": "평면 (위)", "d": [0, 0, 1], "o": 1}),
        ("bottom", {"t": "밑면 (아래)", "d": [0, 0, -1], "o": 1}),
    ])


def focus_sets(parts, idx):
    ids = [p.id for p in parts]
    by_group = collections.defaultdict(list)
    for p in parts:
        by_group[p.group].append(p.id)

    def rx(*pats):
        r = re.compile("|".join(pats))
        return [i for i in ids if r.search(i)]

    def grp(*names):
        out = []
        for n in names:
            out += by_group.get(n, [])
        return out

    def exist(lst):
        return [i for i in lst if i in idx]

    one_key = exist(["O4-KEY-C", "O4-CAPSTAN-C", "O4-NUT-C", "O4-MAGNET-C", "O4-RESTFELT-C", "O4-LEVER-C", "O4-STEEL-C", "O4-FELTSTRIP-C",
                     "O4-SPRING-C", "O4-B-keeperfelt-C", "O4-B-balancepinD2-C", "O4-B-upstoppad-C"])
    sets = [
        ("건반 하나 (C4: 건반·레버·부속 12개)", one_key, "front34"),
        ("옥타브 모듈 O4 (C4~B4)", [i for g in by_group if re.match(r"^O4 ", g) for i in by_group[g]], None),
        ("왼쪽 끝 부속 (A0~B0)", [i for g in by_group if g.startswith("끝 부속 왼쪽") for i in by_group[g]], None),
        ("오른쪽 끝 부속 (C8)", [i for g in by_group if g.startswith("끝 부속 오른쪽") for i in by_group[g]], None),
        ("센서 바·센서 기판·건반 자석", rx(r"-SENSORBAR$", r"-E-SB$", r"^E[LR]-E-BOARD$", r"-SBSCREW\d$", r"-MAGNET-"), None),
        ("제어 기판 MB × 7 (RP2040-Zero·먹스)", rx(r"^O\d-E-(MB|ZERO|MUX)$", r"-B-controlboardscrew", r"^O\d-C-RIBBON$"), None),
        ("레버·토션 스프링·강철 블록", rx(r"-LEVER-", r"-STEEL-", r"-SPRING-", r"-FELTSTRIP-", r"-B-leverrod"), None),
        ("스피커 L 통", grp("스피커 파트 L") + exist(["SPK-L", "C-SPKPIG-L"]), None),
        ("스피커 R 통", grp("스피커 파트 R") + exist(["SPK-R", "C-SPKPIG-R"]), None),
        ("가운데 유닛 전체", grp("가운데 유닛", "CU 칸 출력물", "CU 칸 전자부", "배터리 칸"), None),
        ("배터리·전원 12.8 V (퓨즈·스위치·강압)", exist(["BAT-LFP", "CU-BATFRAME", "C-XT60", "C-BAT-LEAD", "C-PWR-IN",
                                                      "CU-E-FUSE", "C-PWR-FUSE", "CU-E-SWITCH", "C-PWR-BUS", "CU-E-BUCK", "C-PWR-5V"])
         + rx(r"^CU-POST-BUCK-"), None),
        ("소리: 앰프·동글·스피커선·XT60", exist(["CU-E-AMP", "CU-E-DONGLE", "CU-E-J702BOARD", "CU-E-J702", "C-SPK-L", "C-SPK-R", "C-XT60F-L",
                                                "C-XT60M-L", "C-XT60F-R", "C-XT60M-R", "XT60-CLIP-L", "XT60-CLIP-R", "C-SPKPIG-L", "C-SPKPIG-R",
                                                "SPK-L", "SPK-R", "PR-HUBSHELF"]) + rx(r"^CU-POST-J702-", r"^CABLE-CLIP-E"), None),
        ("Pi 5·USB 허브·페달 보드", rx(r"^CU-E-PI5", r"^CU-POST-PI-", r"^CU-POST-PED-", r"^CU-E-PED", r"^C-USB-", r"^O\d-C-USB$")
         + exist(["PB-E-HUB", "CU-E-GENDER", "CU-E-J501BOARD", "CU-E-J501"]), None),
        ("터치스크린 (25°)", [i for i in rx(r"^TS-") if parts[idx[i]].note != "altview"] + exist(["CU-SCREENLID"]) + rx(r"^CU-M3X10-"), None),
        ("케이블 전체", grp("케이블") + rx(r"^TS-C-"), None),
        # 2026-10-16 (A안): the former okoume panels are printed - same 10 parts (the two long centre panels print in 3 pieces each)
        ("옛 합판 10장 (10/16부터 출력)", rx(r"^SPK[LR]-PLY-(SIDEOUT|BACK|TOP|BOTTOM)$") + exist(["CU-PLY-BOTTOM", "CU-PLY-BACK"]), None),
        ("고무발·이음 볼트·방진 브래킷", grp("뒷바 이음·발", "방진 브래킷"), None),
    ]
    out = []
    for (t, lst, v) in sets:
        seen = []
        for i in lst:
            if i in idx and i not in seen:
                seen.append(i)
        assert seen, t
        d = {"t": t, "ix": [idx[i] for i in seen]}
        if v:
            d["v"] = v
        out.append(d)
    # section shortcuts: keep x < value (or z < value) and look at the cut
    xl = body.DRV_X["L"]
    out += [
        {"t": "건반 액션 옆 단면 (D4, x%s)" % f(X_O4 + 35.25), "sec": {"ax": "x", "v": round(X_O4 + 35.25, 2), "flip": 0}, "v": "right",
         "box": [X_O4 + 35.25, -5, 0, X_O4 + 35.25, 347, 192]},
        {"t": "스피커 L 단면 (유닛 가운데 x%s)" % f(xl), "sec": {"ax": "x", "v": xl, "flip": 0}, "v": "right",
         "box": [xl, 200, 0, xl, 347, 150]},
        {"t": "화면 경첩·받침다리 단면 (x%s)" % f(TS.XC), "sec": {"ax": "x", "v": TS.XC, "flip": 0}, "v": "right",
         "box": [TS.XC, 200, 0, TS.XC, 347, 192]},
        {"t": "가운데 유닛 평면 단면 (z45)", "sec": {"ax": "z", "v": 45.0, "flip": 0}, "v": "top", "box": [255, 205, 0, 967, 347, 45]},
    ]
    return out


# ------------------------------------------------------------------ BOM references in part names
def bom_index():
    p = os.path.join(ROOT, "hardware", "bom", "final-bom", "data.json")
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for it in d.get("items", []):
        rec = [it.get("id", ""), it.get("code", ""), it.get("t") or it.get("n", "")]
        out[it.get("id", "")] = rec
        if it.get("code"):
            out[it["code"]] = rec
    return out


TOKEN_RX = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{1,3}\d{1,3})(?![A-Za-z0-9])")


def bom_refs(name, bidx):
    out = []
    for t in TOKEN_RX.findall(name):
        r = bidx.get(t)
        if r and r not in out:
            out.append(r)
    return out[:3]


# ------------------------------------------------------------------ main
def build_data(parts, man):
    idx = {p.id: i for i, p in enumerate(parts)}
    mp = {p["id"]: p for p in man["parts"]}
    rows = {r["file"]: r for r in man["print"]}
    groups = []
    for p in parts:
        if p.group not in groups:
            groups.append(p.group)
    texts, tix = [], {}

    def T(s):
        s = (s or "").strip()
        if not s:
            return None
        if s not in tix:
            tix[s] = len(texts)
            texts.append(s)
        return tix[s]

    bidx = bom_index()
    bom, bix = [], {}
    recs = []
    for p in parts:
        mrec = mp[p.id]
        b = [round(float(v), 2) for v in p.solid.bounding_box()]
        r = {"id": p.id, "n": p.name_ko, "k": p.kind, "g": groups.index(p.group), "c": p.color.lower(), "b": b}
        if p.material:
            r["m"] = p.material
        pf = mrec.get("print_file")
        if pf and pf in rows:
            row = rows[pf]
            r["f"] = os.path.basename(pf)
            r["fd"] = row["folder"]
            r["q"] = row["qty"]
            r["pm"] = row.get("mass_g_solid_petg")
            t = T(row.get("note"))
            if t is not None:
                r["pn"] = t
        t = T(p.note if p.note not in ("offdesk", "altview") else "")
        if t is not None:
            r["nt"] = t
        t = T(p.source)
        if t is not None:
            r["s"] = t
        d = []
        for (ax, a, bb, lab, ln) in merged_dims(family_of(p), p.dims):
            d.append([lab, ("%.2f" % (bb - a)).rstrip("0").rstrip(".")])
        if d:
            r["d"] = d[:14]
        br = bom_refs(p.name_ko, bidx)
        if br:
            r["r"] = []
            for ref in br:
                key = tuple(ref)
                if key not in bix:
                    bix[key] = len(bom)
                    bom.append(ref)
                r["r"].append(bix[key])
        e = explode_vec(p)
        if any(abs(c) > 1e-9 for c in e):
            r["e"] = [round(c, 3) for c in e]
        if inside_hide(p):
            r["in"] = 1
        if p.note == "altview":
            r["a"] = 1
        if p.note == "offdesk":
            r["o"] = 1
        recs.append(r)
    on = [p for p in parts if p.note not in ("offdesk", "altview")]
    bb = np.array([p.solid.bounding_box() for p in on])
    box = [round(float(v), 2) for v in list(bb[:, :3].min(axis=0)) + list(bb[:, 3:].max(axis=0))]
    gmeta = [{"n": g, "s": group_section(g)} for g in groups]
    data = {
        "v": 2, "units": "mm", "coords": man.get("coords", ""),
        "groups": gmeta, "parts": recs, "txt": texts, "bom": bom, "box": box,
        "keys": key_sets(parts, idx), "fold": fold_spec(parts, idx),
        "press": {"kaxis": list(KEY_AXIS), "laxis": list(LEVER_AXIS), "key": KEY_DIP, "lever": LEVER_DIP},
        "views": views(), "dims": dims(), "sets": focus_sets(parts, idx),
        "kinds": KIND,
    }
    return data, groups


def main(parts=None):
    import build_all
    if parts is None:
        parts = build_all.collect()
    man = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
    ids_c, ids_m = [p.id for p in parts], [p["id"] for p in man["parts"]]
    assert ids_c == ids_m, "manifest.json is older than the generators: rebuild the CAD first"
    data, groups = build_data(parts, man)
    glb_path = os.path.join(HERE, GLB_NAME)
    st = write_glb(parts, glb_path)
    b64 = 4 * ((st["bytes"] + 2) // 3)
    data["glb"] = {"bytes": st["bytes"], "b64": b64, "meshes": st["meshes"], "unique": st["unique"], "tris": st["tris"],
                   "max_err_mm": round(st["max_err"], 4)}
    with open(os.path.join(HERE, "parts.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(HERE, "assets.json"), "w", encoding="utf-8") as fh:
        json.dump({"glb": "hardware/mechanical/cad/viewer/" + GLB_NAME, "parts": "hardware/mechanical/cad/viewer/parts.json",
                   "publish": {"cad/parts.json": "hardware/mechanical/cad/viewer/parts.json",
                               "cad/toccata.glb.b64.txt": "base64 text of hardware/mechanical/cad/viewer/" + GLB_NAME},
                   "page": {"section": "hardware/mechanical/cad/viewer/cad.html", "css": "hardware/mechanical/cad/viewer/cad.css",
                            "js": "hardware/mechanical/cad/viewer/cad.js"},
                   "scripts": ["https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js (loaded by cad.js on first open)"],
                   "capabilities": {"downloads": "optional: the 3D 모델 저장 button uses window.claude.use('downloads') to save "
                                                 "Toccata_assembly.zip; without it the button shows a note"},
                   "api": "window.toccata.cad.focus(sel, label, opts) -> Promise<count>; sel = exact id | id prefix (a string that is not an "
                          "exact id, or ends with '*') | array of those | function(rec) -> bool; opts {view, keepView, inside}. Opens #cad, "
                          "waits for the model, ghosts the rest at 15 %, frames the camera, shows label + 모두 보기. Also clear(), ready(), "
                          "parts() -> Promise<[{id, name, kind, group, bbox, file, folder, qty, material, bom, note}]>, press(id), sets. "
                          "window.toccata.three = shared Promise for three.js r128."}, fh, ensure_ascii=False, indent=1)
    write_html(parts, man, data, groups, st)
    print("parts %d  groups %d  glb %.2f MB (b64 %.2f MB, %d meshes, %d unique shapes, %d tris, max err %.4f mm)  parts.json %.0f KB  fold check %.3f mm"
          % (len(parts), len(groups), st["bytes"] / 1e6, b64 / 1e6, st["meshes"], st["unique"], st["tris"], st["max_err"],
             os.path.getsize(os.path.join(HERE, "parts.json")) / 1e3, data["fold"]["check_mm"]))
    return data


# ------------------------------------------------------------------ the section
def write_html(parts, man, data, groups, st):
    recs = data["parts"]
    on = [r for r in recs if not r.get("a") and not r.get("o")]
    kinds = collections.Counter(r["k"] for r in on)
    pr = [r for r in man["print"] if not r.get("extra") and not r.get("variant")]
    n_files = len(pr)
    n_print = sum(r["qty"] for r in pr)
    n_white = sum(1 for k in data["keys"] if not k["b"])
    n_black = sum(1 for k in data["keys"] if k["b"])
    box = data["box"]
    top_z = box[5]
    H = []
    a = H.append
    a('<section class="page" id="p-cad" hidden>')
    a('<h2>3D 모델</h2>')
    a('<p class="lede">설계도와 같은 CAD 입체 %s개를 조립한 자리 그대로 띄운 모델입니다. 출력 STL, 도면, 이 모델은 모두 같은 생성기'
      '(<code>hardware/mechanical/cad/src</code>)에서 나오므로 치수가 같습니다. 부품을 누르면 이름·크기·재료·출력 파일이 나오고, '
      '건반을 누르면 설계 각도대로 내려갑니다. 단면, 분해, 내부 보기, 화면 접기로 안쪽을 볼 수 있습니다.</p>' % format(len(recs), ","))
    a('<div class="kfs">')
    for b_, s_ in [(format(len(on), ","), "조립 부품 (페달·접은 화면 제외)"), ("%d" % len(data["keys"]), "건반 (백 %d · 흑 %d)" % (n_white, n_black)),
                   ("%s × %s" % (f(box[3] - box[0]), f(box[4] - box[1])), "전체 가로 × 깊이 mm"),
                   ("z%s" % f(top_z), "가장 높은 점 (화면 25°)"), ("z%s · %s°" % (f(body.SPK_ZT), f(body.ANGLE, 0)), "스피커 윗면 · 앞판"),
                   ("%d개" % n_print, "출력 부품 (%d개 파일)" % n_files), ("%d" % kinds.get("electronics", 0), "전자 부품·케이블")]:
        a('<div class="kf"><b>%s</b><span>%s</span></div>' % (esc(b_), esc(s_)))
    a('</div>')

    # ---- viewer
    a('<div class="cadv" id="cad-viewer">')
    a('<div class="cadmain">')
    a('<div class="cadbar"><span class="cadlbl" id="cad-l-view">방향</span>'
      '<div class="seg cadseg" role="group" aria-labelledby="cad-l-view">')
    for k, v in data["views"].items():
        a('<button type="button" data-cad-view="%s" aria-pressed="%s">%s</button>' % (k, "true" if k == "front34" else "false", esc(v["t"])))
    a('</div><div class="seg cadseg" role="group" aria-label="투영"><button type="button" data-cad-proj="persp" aria-pressed="true">원근</button>'
      '<button type="button" data-cad-proj="ortho" aria-pressed="false">정투영</button></div></div>')
    a('<div class="cadbar">'
      '<button type="button" class="cadtog" id="cad-inside" aria-pressed="false">내부 보기</button>'
      '<button type="button" class="cadtog" id="cad-fold" aria-pressed="false">화면 접기</button>'
      '<button type="button" class="cadtog" id="cad-press" aria-pressed="true">건반 누르기</button>'
      '<button type="button" class="cadtog" id="cad-scale">한 옥타브 차례로</button>'
      '<button type="button" class="cadtog" id="cad-edges" aria-pressed="true">모서리 선</button>'
      '<button type="button" class="cadtog" id="cad-dims" aria-pressed="false">치수</button>'
      '<label class="cadrange" for="cad-explode"><span>분해</span><input type="range" id="cad-explode" min="0" max="100" step="1" value="0">'
      '<output id="cad-explode-out" for="cad-explode">0 %</output></label></div>')
    a('<div class="cadbar cadsecbar"><span class="cadlbl" id="cad-l-sec">단면</span>'
      '<div class="seg cadseg" role="group" aria-labelledby="cad-l-sec">'
      '<button type="button" data-cad-sec="off" aria-pressed="true">끔</button><button type="button" data-cad-sec="x" aria-pressed="false">x 가로</button>'
      '<button type="button" data-cad-sec="y" aria-pressed="false">y 깊이</button><button type="button" data-cad-sec="z" aria-pressed="false">z 높이</button></div>'
      '<input type="range" id="cad-sec" min="%s" max="%s" step="0.25" value="%s" aria-label="단면 위치 (mm)" disabled>'
      '<output id="cad-sec-out" for="cad-sec">끔</output>'
      '<label class="cadchk"><input type="checkbox" id="cad-sec-flip"> 반대쪽 남김</label>'
      '<button type="button" class="cadtog" id="cad-sec-look" disabled>자른 면 보기</button></div>'
      % (f(box[0]), f(box[3]), f(X_O4 + 35.25)))
    a('<div class="cadstage" id="cad-stage">'
      '<canvas tabindex="0" aria-label="Toccata 전체 조립 3D. 끌어서 돌리고, 휠이나 두 손가락으로 확대합니다. 화살표 키 = 돌리기, Shift+화살표 = 옮기기, + − = 확대."></canvas>'
      '<svg class="cadover" aria-hidden="true"></svg>'
      '<div class="cadload" role="status" aria-live="polite"><p class="cadload-t">이 탭을 열면 3D 모델(약 %s MB)을 불러옵니다.</p>'
      '<div class="cadprog" aria-hidden="true"><i></i></div><button type="button" class="cadtog cadretry" hidden>다시 시도</button></div>'
      '<div class="cadfocus" hidden><span class="cadfocus-t"></span><button type="button" class="cadfocus-x">모두 보기</button></div>'
      '<div class="cadviewlbl" aria-live="polite"></div>'
      '<div class="cadhint">끌기 = 돌리기 · 오른쪽 끌기·두 손가락 = 옮기기 · 휠·모으기 = 확대 · 누르기 = 부품 정보</div>'
      '</div>' % f(data["glb"]["b64"] / 1e6, 1))
    a('<p class="small muted cadnote">좌표: x 가로 (0 = A0 왼쪽 끝), y 흰 건반 앞 끝에서 뒤로, z 책상에서 위로, 단위 mm. '
      '정투영에서는 오른쪽 아래 막대가 실제 길이입니다. 단면에서 잘린 면은 붉게 칠해집니다. '
      '건반은 1 N으로 끝까지 눌러 멈춘 자세(백건 %s°, 흑건 %s°, 건반 봉 축 y%s z%s)까지 내려가고, 레버는 레버 봉 축(y%s z%s)을 중심으로 '
      '%s° / %s° 올라갑니다 (레버 각은 건반 각에 비례하게 그림). 화면 접기는 경첩 축(y%s z%s)을 중심으로 %s° 돌린 뒤 접은 상태 입체로 바꿉니다 '
      '(선택 부품인 화면 덮개와 화면 선은 접은 상태에서 그리지 않음).</p>'
      % (f(KEY_DIP["w"]), f(KEY_DIP["b"]), f(KEY_AXIS[0], 0), f(KEY_AXIS[1], 1), f(LEVER_AXIS[0]), f(LEVER_AXIS[1], 1),
         f(LEVER_DIP["w"]), f(LEVER_DIP["b"]), f(TS.AX_Y), f(TS.AX_Z), f(TS.TILT_FOLD - TS.TILT_USE, 0)))
    a('</div>')  # cadmain
    a('<div class="cadside">')
    a('<div class="cadinfo" aria-live="polite"><p class="cadempty">부품을 누르면 이름·크기·재료·출력 파일이 여기에 나옵니다.</p></div>')
    a('<details class="cadbox" open><summary>부분별로 보기</summary><div class="cadsets">')
    for i, s in enumerate(data["sets"]):
        if "sec" in s:
            a('<button type="button" class="cadset cadset-sec" data-cad-set="%d"><span>%s</span><em>단면</em></button>' % (i, esc(s["t"])))
        else:
            a('<button type="button" class="cadset" data-cad-set="%d"><span>%s</span><em class="mono">%d</em></button>' % (i, esc(s["t"]), len(s["ix"])))
    a('</div></details>')
    a('<details class="cadbox"><summary>종류·모듈 층</summary><div class="cadchips" role="group" aria-label="종류">')
    for k, n in KIND.items():
        a('<button type="button" class="cadchip" data-cad-kind="%s" aria-pressed="true">%s <span class="mono">%d</span></button>' % (k, n, kinds.get(k, 0)))
    a('</div><div class="cadchips" role="group" aria-label="건반 모듈 층 (O1~O7, 끝 부속)">')
    for ly in LAYERS:
        n = sum(1 for r in on if groups[r["g"]].endswith(" " + ly))
        a('<button type="button" class="cadchip" data-cad-layer="%s" aria-pressed="true">%s <span class="mono">%d</span></button>' % (esc(ly), esc(ly), n))
    a('</div></details>')
    cnt = collections.Counter(r["g"] for r in recs)
    a('<details class="cadbox"><summary>그룹 (%d)</summary><div class="cadgtools"><button type="button" data-cad-gall>모두 켬</button>'
      '<button type="button" data-cad-gnone>모두 끔</button><button type="button" data-cad-gshow>숨긴 부품 다시</button></div><div class="cadglist">'
      % sum(1 for g in data["groups"] if g["s"] != "alt"))
    for sk, st_ in SECTION_TITLE.items():
        gi = [i for i, g in enumerate(data["groups"]) if g["s"] == sk]
        if not gi:
            continue
        a('<p class="cadgh">%s</p>' % esc(st_))
        for i in gi:
            a('<label><input type="checkbox" data-cad-g="%d"%s><span>%s</span><em class="mono">%d</em></label>'
              % (i, "" if sk == "floor" else " checked", esc(data["groups"][i]["n"]), cnt[i]))
    a('</div></details>')
    a('</div>')  # cadside
    a('</div>')  # cadv

    # ---- files
    a('<h3 id="cad-files">파일</h3>')
    a('<div class="tbl cadfiles"><table><thead><tr><th>파일 (저장소)</th><th>무엇</th></tr></thead><tbody>')
    for k, v in [("hardware/mechanical/cad/viewer/%s" % GLB_NAME, "이 탭의 3D 모델 (부품마다 노드 1개, 이름 = 부품 id, %s MB). 다른 GLB 뷰어에서도 실제 크기(m)로 열립니다." % f(st["bytes"] / 1e6, 1)),
                 ("hardware/mechanical/cad/Toccata_전체조립.3mf", "색·이름이 붙은 전체 조립 (슬라이서·3D 뷰어용)"),
                 ("hardware/mechanical/cad/stl/assembly/", "그룹별 조립 STL과 Toccata_전체조립.stl (조립 좌표, mm)"),
                 ("hardware/mechanical/cad/stl/print/", "출력용 STL %d개 파일 · 부품 %d개 (파일 이름 끝 = 출력 개수, 베드에 놓인 방향)" % (n_files, n_print)),
                 ("hardware/mechanical/cad/manifest.json", "부품마다 id·이름·종류·그룹·외곽·출력 파일"),
                 ("hardware/mechanical/cad/viewer/parts.json", "이 탭의 부품표 (외곽, 출력 파일·개수, 메모, 분해·단면·누르기 자료)")]:
        a('<tr><td><code>%s</code></td><td>%s</td></tr>' % (esc(k), esc(v)))
    a('</tbody></table></div>')
    a('<div class="cadsave"><button type="button" class="cadtog" id="cad-save">3D 모델 저장 (GLB를 zip으로)</button>'
      '<span class="small muted" id="cad-save-msg">Toccata_assembly.zip · 약 %s MB</span></div>' % f(st["bytes"] / 1e6, 1))
    est = make_readme.grouped_notes(dict(man, parts=[p for p in man["parts"] if p["kind"] != "print" and p.get("note") != "offdesk"]), "추정")
    a('<details class="spec cadest"><summary>받은 부품을 재서 확인할 추정 치수 (%d)</summary>' % len(est))
    a('<p class="small muted">구매품·전자 부품 가운데 판매처에 치수가 없어 모델에서 정한 값입니다. 받은 부품을 재 보고 다르면 '
      '<code>hardware/mechanical/cad/spec/*.json</code>이나 생성기의 값을 고친 뒤 다시 만듭니다. 출력 부품의 치수는 정해진 값이라 이 목록에 없습니다.</p><ul class="small">')
    for (name, txt, c, nvar) in est:
        a('<li><b>%s</b> — %s%s</li>' % (esc(name), esc(txt), esc(" (같은 부품 %d개)" % c) if nvar > 1 or c > 1 else ""))
    a('</ul></details>')
    a('</section>')
    with open(os.path.join(HERE, "cad.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(H) + "\n")


if __name__ == "__main__":
    main()
