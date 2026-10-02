#!/usr/bin/env python3
"""Self-check for plywood_jigs.py (build_all writes them to stl/print/08_합판지그 + stl/print_extra/선택_합판지그).

  python3 src/check_plywood_jigs.py      # writes every jig with plywood_jigs.write_files() to a temp dir and checks those STLs

(1) every STL written: watertight + consistent winding (trimesh), one body, volume = generator solid, footprint <= 250 x 250,
    lies on z = 0
(2) every guide bore MEASURED BACK FROM THE STL (section at mid guide length, least-squares circle) vs its target in the print
    frame (<= 0.05) and its diameter (bit + 0.2)
(3) the measured bore axes taken to the world (the jig placed on its board) vs the hole axes MEASURED FROM THE body.py MODEL MESHES
    (pod inner panels, end walls, back ply, lids): <= 0.05; J-a pod-panel bores vs end-wall bores coaxial
(4) placement: jig ^ board = 0 (sits on the board), fences touch the datum edges and the guides / pads touch the face (board moved
    0.05 toward each); wrong placements are blocked (J-a on the other face of a panel, end-wall jig on a pod panel: key / guard
    lands on the wood; slider turned 180 deg: the frame pin blocks it)
(5) slots: window / slider / shim measured from the STLs -> the 4 pass positions -> D4 hole centres per slot vs the slot measured
    from the model (on the centre line, inside the ends, max pitch -> cusp <= 0.30), hole count
(6) J-e gauges: full-diameter seat depth below the top (cone measured from the STL) = GUIDE + target depth
(7) minimum wall >= 1.6 measured from the STLs (inward rays from surface samples; text side walls in the 0.85 label skin and the
    shim blades, whose thickness IS the pass step p, are reported but not failed)
(8) J-c slot tongue vs the drilled slot: clearance per side >= 0.5 at the narrowest slot width (4 - 2 cusp - 2 slider play)
"""
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl_toccata"))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from manifold3d import Manifold, Mesh  # noqa: E402

import body as B  # noqa: E402
import plywood_jigs as PJ  # noqa: E402
from cadlib import mesh_arrays  # noqa: E402

TOL = 0.05
FAIL = []


def ok(cond, msg):
    if not cond:
        FAIL.append(msg)
    return "OK " if cond else "NG "


def load(path):
    return trimesh.load(path, force="mesh", process=True)


def to_manifold(tm):
    v = np.asarray(tm.vertices, dtype=np.float32)
    f = np.asarray(tm.faces, dtype=np.uint32)
    return Manifold(Mesh(vert_properties=v, tri_verts=f))


def tm_from_manifold(m):
    v, f = mesh_arrays(m)
    return trimesh.Trimesh(vertices=v, faces=f, process=True)


WALL_MIN = 1.6
ENGRAVE_SKIN = PJ.ENGRAVE + 0.05


def wall_rays(tm, n):
    """wall thickness at surface samples: inward ray along -normal to the first face it LEAVES the solid through (hits on faces
    that the ray enters are grazing artefacts at edges and are skipped)."""
    rng_state = np.random.get_state()
    np.random.seed(1)
    pts, fi = trimesh.sample.sample_surface_even(tm, n, radius=0.15)
    np.random.set_state(rng_state)
    nrm = tm.face_normals[fi]
    org = pts - nrm * 1e-3
    loc, ir, it = tm.ray.intersects_location(org, -nrm, multiple_hits=True)
    th = np.full(len(pts), np.inf)
    good = np.einsum("ij,ij->i", tm.face_normals[it], -nrm[ir]) > 0.05      # the ray leaves the solid through this face
    d = np.linalg.norm(loc - org[ir], axis=1)
    for r, dd in zip(ir[good], d[good]):
        if dd < th[r]:
            th[r] = dd
    return th, nrm, pts


def M34(R, t):
    A = np.zeros((3, 4))
    A[:, :3] = R
    A[:, 3] = t
    return A


def inv(R, t):
    R = np.asarray(R, float)
    return R.T, -R.T @ np.asarray(t, float)


def section_pts(tm, origin, normal):
    seg = trimesh.intersections.mesh_plane(tm, np.asarray(normal, float), np.asarray(origin, float))
    if len(seg) == 0:
        return np.zeros((0, 3))
    return seg.reshape(-1, 3)


def fit_circle(xy):
    x, y = xy[:, 0], xy[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = -(x * x + y * y)
    D, E, F = np.linalg.lstsq(A, b, rcond=None)[0]
    cx, cy = -D / 2, -E / 2
    return np.array([cx, cy]), math.sqrt(max(cx * cx + cy * cy - F, 0.0))


def circle_near(pts2, c, d, band=0.45):
    r = np.linalg.norm(pts2 - np.asarray(c), axis=1)
    sel = pts2[np.abs(r - d / 2.0) < band]
    if len(sel) < 8:
        return None, None, len(sel)
    cc, rr = fit_circle(sel)
    return cc, rr, len(sel)


def basis(axis):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    e1 = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = e1 - a * (a @ e1)
    e1 /= np.linalg.norm(e1)
    return a, e1, np.cross(a, e1)


def model_hole(tm, point, axis, d, depth_into):
    """hole in a model board: section perpendicular to `axis` at point + axis*depth_into; circle near point -> world centre."""
    a, e1, e2 = basis(axis)
    o = np.asarray(point, float) + a * depth_into
    pts = section_pts(tm, o, a)
    p2 = np.column_stack([(pts - o) @ e1, (pts - o) @ e2])
    c, r, n = circle_near(p2, (0.0, 0.0), d, band=0.6)
    if c is None:
        return None, None
    return o + e1 * c[0] + e2 * c[1], 2 * r


def perp_dist(p, q, axis):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    d = np.asarray(p, float) - np.asarray(q, float)
    return float(np.linalg.norm(d - a * (a @ d)))


def main():
    jigs = PJ.make_jigs()
    byk = {j.key: j for j in jigs}
    import tempfile
    root = tempfile.mkdtemp(prefix="toccata_jigs_")
    paths = PJ.write_files(root, jigs)
    files = sorted(os.path.relpath(p, root) for p in paths.values())
    print("== (1) STL files written to", root, "(%s required + %s optional)" % (
        sum(1 for j in jigs if j.key not in PJ.OPTIONAL), sum(1 for j in jigs if j.key in PJ.OPTIONAL)))
    api = PJ.build()
    names_ok = (len(api) == len(jigs) and all(d["name"] + "__1개.stl" == j.file and d["required"] == (j.key not in PJ.OPTIONAL)
                                               and abs(d["solid"].volume() - j.printed.volume()) < 1e-6 for d, j in zip(api, jigs)))
    print(ok(names_ok and len(files) == len(set(files)) == len(jigs), "file set"),
          "files %d = generator %d, build() names/required/solids consistent: %s" % (len(files), len(jigs), names_ok))
    TM = {}
    for j in jigs:
        tm = load(paths[j.key])
        TM[j.key] = tm
        ext = tm.bounds[1] - tm.bounds[0]
        nb = len(tm.split(only_watertight=False))
        good = (tm.is_watertight and tm.is_winding_consistent and nb == 1 and ext[0] <= 250.0 and ext[1] <= 250.0
                and abs(tm.bounds[0][2]) < 1e-3 and abs(tm.volume - j.printed.volume()) < 1e-3 * max(1.0, tm.volume))
        print(ok(good, j.file), "%-44s %6.1f x %6.1f x %5.1f  watertight %s winding %s bodies %d  vol %.1f (solid %.1f)" % (
            j.file, ext[0], ext[1], ext[2], tm.is_watertight, tm.is_winding_consistent, nb, tm.volume, j.printed.volume()))

    print("\n== (2) guide bores measured from the STLs (print frame, section at mid guide length)")
    MEAS = {}      # (jig key, bore name) -> (local point on axis, measured diameter)
    worst = 0.0
    for j in jigs:
        if not j.bores:
            continue
        tm = TM[j.key]
        for b in j.bores:
            w_mid = PJ.GUIDE / 2.0
            P = j.to_print((b["u"], b["v"], w_mid))
            pts = section_pts(tm, P, (0, 0, 1))
            c, r, n = circle_near(pts[:, :2], P[:2], b["d"])
            if c is None:
                print(ok(False, "%s %s no circle" % (j.key, b["name"])), j.key, b["name"], "no circle found (%d pts)" % n)
                continue
            e = float(np.linalg.norm(c - P[:2]))
            worst = max(worst, e)
            Pm = np.array([c[0], c[1], P[2]])
            Rinv, tinv = inv(j.R_print, j.t_print)
            loc = Rinv @ Pm + tinv
            MEAS[(j.key, b["name"])] = (loc, 2 * r)
            if j.key[:4] in ("J-d1", "J-d2", "J-d3", "J-d4"):
                continue                    # 288 slot bores: summarised below
            print(ok(e <= TOL and abs(2 * r - b["d"]) <= TOL, "%s %s bore" % (j.key, b["name"])),
                  "%-7s %-8s bit %.1f  bore D%.3f (design %.2f)  centre error %.4f" % (j.key, b["name"], b["bit"], 2 * r, b["d"], e))
    slot_e = [float(np.linalg.norm(np.array(j.to_print((b["u"], b["v"], 0))[:2]) -
                                   np.array(j.to_print(MEAS[(j.key, b["name"])][0])[:2])))
              for j in jigs if j.key[:4] in ("J-d1", "J-d2", "J-d3", "J-d4") for b in j.bores if (j.key, b["name"]) in MEAS]
    nslot = sum(len(j.bores) for j in jigs if j.key[:4] in ("J-d1", "J-d2", "J-d3", "J-d4"))
    print(ok(len(slot_e) == nslot and max(slot_e) <= TOL, "slot bores"), "slider bores D4.2: %d/%d measured, max centre error %.4f"
          % (len(slot_e), nslot, max(slot_e) if slot_e else -1))
    print("   worst bore centre error (all %d bores) %.4f mm" % (len(MEAS), max(worst, max(slot_e) if slot_e else 0)))

    # ------------------------------------------------------------------ (3) world coordinates vs the model meshes
    print("\n== (3) bore axes in the world (jig on its board) vs the holes measured from the body.py model")
    o = B.Out()
    B.cu_panels(o)
    BOARD = {p.id: p.solid for p in o}
    BOARD["POD-L"] = B.side_in_panel("L")
    BOARD["POD-R"] = B.side_in_panel("R")
    BTM = {k: tm_from_manifold(v) for k, v in BOARD.items()}
    board_of = {"J-a1": "POD-L", "J-a2": "POD-R", "J-a3": "CU-PLY-END-L", "J-a4": "CU-PLY-END-R", "J-c1": "LID-L", "J-c2": "LID-R"}
    world_axes = {}
    for jk, bk in board_of.items():
        j = byk[jk]
        R, org = j.placements["use"]
        for b in j.bores:
            loc, dm = MEAS[(jk, b["name"])]
            wpt = np.asarray(R) @ loc + np.asarray(org)
            axis = np.asarray(R) @ np.array([0, 0, 1.0])
            world_axes[(jk, b["name"])] = (wpt, axis)
            # model hole: probe inside the hole (blind pockets: half their depth; through: mid thickness)
            dmodel = next(v for k_, v in (("insert", PJ.BIT_INSERT), ("wire", PJ.BIT_WIRE), ("sleeve", PJ.BIT_SLEEVE),
                                          ("xt30", PJ.XT30_D), ("mag", PJ.BIT_MAG)) if b["name"].startswith(k_))
            face_pt = np.array(b["world"], float)
            depth_in = -(b.get("depth") or PJ.PLY_T) / 2.0           # into the wood = -w
            c, dm_model = model_hole(BTM[bk], face_pt, axis, dmodel, depth_in)
            if c is None:
                print(ok(False, "%s %s model hole" % (jk, b["name"])), jk, b["name"], "model hole not found")
                continue
            e = perp_dist(wpt, c, axis)
            print(ok(e <= TOL, "%s %s world" % (jk, b["name"])),
                  "%-5s %-8s on %-13s jig axis (%.3f, %.3f, %.3f) | model hole D%.2f at (%.3f, %.3f, %.3f) | off-axis %.4f" % (
                      jk, b["name"], bk, wpt[0], wpt[1], wpt[2], dm_model, c[0], c[1], c[2], e))
    # coaxiality pod inner panel <-> end wall (the same screw axis)
    for sd, ja, je in (("L", "J-a1", "J-a3"), ("R", "J-a2", "J-a4")):
        for k in (1, 2):
            pa, ax = world_axes[(ja, "insert%d" % k)]
            pe, _ = world_axes[(je, "sleeve%d" % k)]
            e = perp_dist(pa, pe, ax)
            print(ok(e <= TOL, "coax %s %d" % (sd, k)), "coaxial %s screw %d: pod insert bore (J-%s) vs end-wall sleeve bore (J-%s): %.4f mm "
                  "(screw axis y%.0f z%.0f)" % (sd, k, ja[2:], je[2:], e, B.TS_YZ[sd][k - 1][0], B.TS_YZ[sd][k - 1][1]))
    # J-b saddles on every edge seat (one variant is enough for the axis; all gaps share it)
    jb = byk["J-b11.6"]
    loc, _ = MEAS[("J-b11.6", "mag")]
    for pn, (R, org) in jb.placements.items():
        wpt = np.asarray(R) @ loc + np.asarray(org)
        axis = np.asarray(R) @ np.array([0, 0, 1.0])
        bk = "CU-PLY-BACK" if pn.startswith("back") else "CU-PLY-END-%s" % pn[-1]
        c, dmod = model_hole(BTM[bk], org, axis, PJ.BIT_MAG, -PJ.DEPTH_MAG / 2.0)
        e = perp_dist(wpt, c, axis)
        print(ok(e <= TOL, "J-b %s" % pn), "J-b     %-6s on %-13s saddle axis (%.3f, %.3f) | model pocket D%.2f (%.3f, %.3f) | off-axis %.4f" % (
            pn, bk, wpt[0], wpt[1], dmod, c[0], c[1], e))

    # ------------------------------------------------------------------ (4) placement / contact / fool-proofing
    print("\n== (4) placement on the boards (STL meshes taken back to the world)")
    MAN = {}
    for j in jigs:
        m = to_manifold(TM[j.key])
        Rinv, tinv = inv(j.R_print, j.t_print)
        MAN[j.key] = m.transform(M34(Rinv, tinv))              # back to the local (use) frame

    def placed(key, pname):
        R, org = byk[key].placements[pname]
        return MAN[key].transform(M34(R, org))

    def touch(jm, board, shift):
        return (jm ^ board.translate(tuple(np.asarray(shift) * 0.05))).volume()

    DAT = {  # key: (board, [named shifts toward the fences / face])
        "J-a1": ("POD-L", [("앞 모서리", (0, -1, 0)), ("아래 모서리", (0, 0, -1)), ("면", (1, 0, 0))]),
        "J-a2": ("POD-R", [("앞 모서리", (0, -1, 0)), ("아래 모서리", (0, 0, -1)), ("면", (-1, 0, 0))]),
        "J-a3": ("CU-PLY-END-L", [("앞 모서리", (0, -1, 0)), ("아래 모서리", (0, 0, -1)), ("면", (1, 0, 0))]),
        "J-a4": ("CU-PLY-END-R", [("앞 모서리", (0, -1, 0)), ("아래 모서리", (0, 0, -1)), ("면", (-1, 0, 0))]),
        "J-c1": ("LID-L", [("뒤 모서리", (0, 1, 0)), ("왼쪽 끝", (-1, 0, 0)), ("밑면", (0, 0, -1))]),
        "J-c2": ("LID-R", [("뒤 모서리", (0, 1, 0)), ("오른쪽 끝", (1, 0, 0)), ("밑면", (0, 0, -1))]),
        "J-d1a": ("LID-L", [("오른쪽 끝", (1, 0, 0)), ("뒤 모서리", (0, 1, 0)), ("윗면", (0, 0, 1))]),
        "J-d2a": ("LID-R", [("왼쪽 끝", (-1, 0, 0)), ("뒤 모서리", (0, 1, 0)), ("윗면", (0, 0, 1))]),
        "J-d3a": ("CU-PLY-BACK", [("오른쪽 끝", (1, 0, 0)), ("윗모서리", (0, 0, 1)), ("바깥면", (0, 1, 0))]),
        "J-d4a": ("CU-PLY-BOTTOM", [("뒤 모서리", (0, 1, 0)), ("윗면", (0, 0, 1))]),
    }
    for key, (bk, shifts) in DAT.items():
        jm = placed(key, "use")
        board = BOARD[bk]
        ov = (jm ^ board).volume()
        res = [(nm, touch(jm, board, sh)) for nm, sh in shifts]
        good = ov <= 0.01 and all(v > 0.01 for _, v in res)
        print(ok(good, "%s placement" % key), "%-6s on %-13s overlap %.3f mm3; touches %s" % (
            key, bk, ov, ", ".join("%s %.2f" % (nm, v) for nm, v in res)))
    for key, pn, bk, why in (("J-a1", "wrong_face", "POD-L", "옆판 L 반대 면(상자 안쪽 면)"),
                             ("J-a2", "wrong_face", "POD-R", "옆판 R 반대 면(상자 안쪽 면)"),
                             ("J-a3", "wrong_face", "CU-PLY-END-L", "끝벽 L 반대 면(이음면)"),
                             ("J-a4", "wrong_face", "CU-PLY-END-R", "끝벽 R 반대 면(이음면)"),
                             ("J-a3", "on_pod_panel", "POD-L", "끝벽 지그를 스피커 옆판 L에"),
                             ("J-a4", "on_pod_panel", "POD-R", "끝벽 지그를 스피커 옆판 R에")):
        ov = (placed(key, pn) ^ BOARD[bk]).volume()
        print(ok(ov > 50.0, "%s %s blocked" % (key, pn)), "%-5s %-28s blocked: key/guard in the wood %.0f mm3 (cannot sit flat)" % (key, why, ov))
    # J-a: every way to put a jig on a panel face (2 faces x 4 in-plane turns, datum corner on the panel's bounding-box corner)
    #      -> only the intended placement may sit flat with both fences on edges
    def fits(key, bk):
        j = byk[key]
        s_ = PJ.SGN[j.meta["side"]]
        bb = BOARD[bk].bounding_box()
        res = []
        for nx in (1.0, -1.0):
            wv = np.array([nx, 0, 0])
            for ud in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                u = np.array(ud, float)
                v = np.cross(wv, u)
                R = np.column_stack([u, v, wv])
                board_dirs = (s_ * u, v)                   # the board lies toward +s*u and +v from the datum corner
                org = np.array([bb[3] if nx > 0 else bb[0], 0.0, 0.0])
                for ax in (1, 2):
                    lo, hi = bb[ax], bb[ax + 3]
                    comp = sum(d[ax] for d in board_dirs)
                    org[ax] = lo if comp > 0 else hi
                jm = MAN[key].transform(M34(R, org))
                ov = (jm ^ BOARD[bk]).volume()
                t1 = touch(jm, BOARD[bk], -board_dirs[0])
                t2 = touch(jm, BOARD[bk], -board_dirs[1])
                if ov <= 1.0 and t1 > 0.01 and t2 > 0.01:
                    res.append((nx, ud))
        return res
    for key, bk, exp in (("J-a1", "POD-L", 1), ("J-a2", "POD-R", 1), ("J-a3", "CU-PLY-END-L", 1), ("J-a4", "CU-PLY-END-R", 1),
                         ("J-a3", "POD-L", 0), ("J-a4", "POD-R", 0), ("J-a1", "CU-PLY-END-L", 1), ("J-a2", "CU-PLY-END-R", 1)):
        f = fits(key, bk)
        want = byk[key].placements["use"][0][:, 2][0]
        right = all(abs(nx - want) < 1e-9 and ud == ((0, 1, 0) if PJ.SGN[byk[key].meta["side"]] > 0 else (0, -1, 0)) for nx, ud in f)
        note = {0: "어느 방향으로도 앉지 않음", 1: "한 가지 방향으로만 앉음"}.get(len(f), "%d 가지 방향으로 앉음" % len(f))
        extra = " (옆판 지그가 끝벽에도 맞음 - 허용: 지름 5.8 막힌 구멍·Ø6 구멍만, 아래 README)" if key in ("J-a1", "J-a2") and bk.startswith("CU") else ""
        print(ok(len(f) == exp and (exp == 0 or right), "%s on %s placements" % (key, bk)),
              "%-5s on %-13s 8 ways tried (2 faces x 4 turns, datum corner on the panel corner): %s%s" % (key, bk, note, extra))
    # J-c: 2 faces x 4 turns at every lid corner -> only the underside / datum corner (the slot key needs the drilled exhaust slot)
    for key, bk in (("J-c1", "LID-L"), ("J-c2", "LID-R")):
        j = byk[key]
        sv = 1.0 if j.meta["side"] == "L" else -1.0
        bb = BOARD[bk].bounding_box()
        f = []
        for nz in (1.0, -1.0):
            wv = np.array([0, 0, nz])
            for ud in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
                u = np.array(ud, float)
                v = np.cross(wv, u)
                R = np.column_stack([u, v, wv])
                dirs = (u, sv * v)
                org = np.array([0.0, 0.0, bb[5] if nz > 0 else bb[2]])
                for ax in (0, 1):
                    org[ax] = bb[ax] if sum(d_[ax] for d_ in dirs) > 0 else bb[ax + 3]
                jm = MAN[key].transform(M34(R, org))
                ov = (jm ^ BOARD[bk]).volume()
                jb = jm.bounding_box()
                over = max(bb[0] - jb[0], bb[1] - jb[1], jb[3] - bb[3], jb[4] - bb[4])   # sticks out past the lid outline
                if ov <= 1.0 and over <= PJ.FENCE_T + 0.01 and touch(jm, BOARD[bk], -dirs[0]) > 0.01 and \
                        touch(jm, BOARD[bk], -dirs[1]) > 0.01:
                    f.append((nz, ud))
        Ru = np.asarray(j.placements["use"][0])
        right = len(f) == 1 and f[0][0] == Ru[2, 2] and tuple(int(round(x)) for x in Ru[:, 0]) == f[0][1]
        print(ok(right, "%s placements" % key), "%-5s on %-13s 8 ways tried (2 faces x 4 turns, datum corner on the lid corner, not sticking out past the lid): %s "
              "(홈 열쇠가 배기 홈에 들어가야 앉음 - J-d로 홈을 먼저)" % (key, bk, "한 가지 방향으로만 앉음" if right else "%d 가지" % len(f)))
    # saddles: every gap >= board sits; 11.3 does not fit an 11.5 board; contact on the edge
    for g in PJ.SADDLE_GAPS:
        jk = "J-b%.1f" % g
        jm = placed(jk, "back1")
        ov = (jm ^ BOARD["CU-PLY-BACK"]).volume()
        tz = touch(jm, BOARD["CU-PLY-BACK"], (0, 0, 1))
        exp_fit = g >= PJ.PLY_T
        good = (ov <= 0.01 and tz > 0.01) if exp_fit else ov > 1.0
        print(ok(good, "%s fit" % jk), "%-8s on an 11.5 edge: %s (overlap %.2f mm3, seat contact %.2f); cheek play %.2f per side" % (
            jk, "sits" if ov <= 0.01 else "too narrow for 11.5 - for a thinner board", ov, tz, (g - PJ.PLY_T) / 2.0))

    # ------------------------------------------------------------------ (5) slots
    print("\n== (5) slot templates: passes A/B/C/D from the measured frame window, slider and shim -> D4 holes vs the model slots")
    for gr in PJ.slot_groups():
        k = gr["key"]
        jf, js, jsh = byk[k + "a"], byk[k + "b"], byk[k + "c"]
        meta = js.meta
        p = meta["p"]
        ax, sg = gr["t_axis"]

        def to_tc(loc):
            u, v = loc[0], loc[1]
            return (sg * u, v) if ax == "u" else (sg * v, u)

        # window walls (frame section at mid plate height, local w = 2.5)
        Rinv, tinv = inv(jf.R_print, jf.t_print)
        P0 = jf.to_print((0, 0, PJ.FRAME_T / 2.0))
        pts = section_pts(TM[jf.key], P0, (0, 0, 1))
        loc = (Rinv @ pts.T).T + tinv
        tc = np.array([to_tc(q) for q in loc])
        (wt0, wt1), (wc0, wc1) = meta["window_t"], meta["window_c"]
        mid = (tc[:, 1] > wc0 + 4.0) & (tc[:, 1] < wc1 - 1.0)
        near = tc[mid & (np.abs(tc[:, 0] - wt0) < 0.6), 0]
        far = tc[mid & (np.abs(tc[:, 0] - wt1) < 0.6), 0]
        W0, W1 = float(np.median(near)), float(np.median(far))
        # slider ends (section at local w = 2)
        Rinv2, tinv2 = inv(js.R_print, js.t_print)
        P1 = js.to_print((0, 0, 2.0))
        pts = section_pts(TM[js.key], P1, (0, 0, 1))
        loc = (Rinv2 @ pts.T).T + tinv2
        tc = np.array([to_tc(q) for q in loc])
        (st0, st1), (sc0, sc1) = meta["slider_t"], meta["slider_c"]
        mid = (tc[:, 1] > sc0 + 4.0) & (tc[:, 1] < sc1 - 1.0)
        S0 = float(np.median(tc[mid & (np.abs(tc[:, 0] - st0) < 0.6), 0]))
        S1 = float(np.median(tc[mid & (np.abs(tc[:, 0] - st1) < 0.6), 0]))
        # shim blade thickness (print frame: blade z 3..8 -> section z 5.5)
        tmsh = TM[jsh.key]
        pts = section_pts(tmsh, (0, 0, 5.5), (0, 0, 1))
        shim = float(np.ptp(pts[:, 0]))
        offs = {"A": W0 - S0, "B": (W1 - shim) - S1, "C": (W0 + shim) - S0, "D": W1 - S1}
        travel = (W1 - W0) - (S1 - S0)
        print(ok(abs(shim - p) <= TOL and abs(travel - meta["travel"]) <= TOL, "%s window/shim" % k),
              "%s %-4s p %.4f: window %.3f..%.3f, slider %.3f..%.3f -> travel %.3f (3p+%.1f = %.3f), shim %.3f; offsets A %.3f B %.3f C %.3f D %.3f"
              % (k, gr["name"], p, W0, W1, S0, S1, travel, PJ.TRAVEL_EXTRA, meta["travel"], shim, offs["A"], offs["B"], offs["C"], offs["D"]))
        # slider bores (measured) per slot row
        bores = [(b, MEAS[(js.key, b["name"])][0]) for b in js.bores]
        # model slots: section the board at mid thickness, points -> group local (t, c)
        bk = gr["board"]
        Rg, og = np.asarray(gr["R"]), np.asarray(gr["origin"], float)
        wdir = Rg[:, 2]
        mid_pt = og - wdir * PJ.PLY_T / 2.0
        pts = section_pts(BTM[bk], mid_pt, wdir)
        locb = (Rg.T @ (pts - og).T).T
        tcb = np.array([to_tc(q) for q in locb])
        worst_c = worst_end = max_gap = 0.0
        nh_tot = 0
        good = True
        for i, s in enumerate(gr["slots"]):
            ta, tb = s["slot_t"]
            sel = tcb[(tcb[:, 0] > ta - 0.6) & (tcb[:, 0] < tb + 0.6) & (np.abs(tcb[:, 1] - s["c"]) < 2.6)]
            mt0, mt1 = float(sel[:, 0].min()), float(sel[:, 0].max())
            mc = float((sel[:, 1].min() + sel[:, 1].max()) / 2.0)
            mw = float(sel[:, 1].max() - sel[:, 1].min())
            rowb = [to_tc(lc) for b, lc in bores if b["name"].startswith("r%dk" % (i + 1))]
            holes = sorted(t + offs[ps] for (t, c) in rowb for ps in "ABCD")
            cs = [c for (t, c) in rowb]
            gaps = np.diff(holes)
            worst_c = max(worst_c, max(abs(c - mc) for c in cs))
            end_err = max(mt0 + PJ.SLOT_END - holes[0], holes[-1] - (mt1 - PJ.SLOT_END) - PJ.TRAVEL_EXTRA)
            worst_end = max(worst_end, end_err)
            max_gap = max(max_gap, float(gaps.max()))
            nh_tot += len(holes)
            good &= len(holes) == gr["n_holes"] and abs(mw - 4.0) < 0.01 and gaps.min() > 0.5
        cusp = 2.0 - math.sqrt(max(4.0 - (max_gap / 2.0) ** 2, 0.0))
        good &= worst_c <= TOL and worst_end <= TOL and cusp <= 0.30
        print(ok(good, "%s slots" % k), "   %d slots x %d holes = %d: off the slot centre line max %.4f, past the slot-end limit max %.4f "
              "(D pass carries the +%.1f travel allowance: an exactly printed window makes the slot %.1f longer), max pitch %.3f -> cusp %.3f"
              % (len(gr["slots"]), gr["n_holes"], nh_tot, worst_c, worst_end, PJ.TRAVEL_EXTRA, PJ.TRAVEL_EXTRA, max_gap, cusp))
        # passes: slider / shim / frame never overlap; slider turned 180 deg is blocked by the pin
        fm = MAN[jf.key]
        sm = MAN[js.key]
        tdir_loc = np.array([sg, 0, 0]) if ax == "u" else np.array([0, sg, 0])
        ovs = [(fm ^ sm.translate(tuple(tdir_loc * offs[ps]))).volume() for ps in "ABCD"]
        tA = (fm ^ sm.translate(tuple(tdir_loc * (offs["A"] - 0.05)))).volume()
        tD = (fm ^ sm.translate(tuple(tdir_loc * (offs["D"] + 0.05)))).volume()
        b0 = sm.bounding_box()
        cx, cy = (b0[0] + b0[3]) / 2.0, (b0[1] + b0[4]) / 2.0
        rot = sm.translate((-cx, -cy, 0)).rotate((0, 0, 180)).translate((cx, cy, 0))
        ov_rot = min((fm ^ rot.translate(tuple(tdir_loc * d))).volume() for d in np.linspace(0, meta["travel"], 9))
        good = max(ovs) <= 0.01 and tA > 0.01 and tD > 0.01 and ov_rot > 1.0
        print(ok(good, "%s passes" % k), "   slider in the frame at A/B/C/D: overlap max %.3f mm3; touches the A·C wall %.2f / B·D wall %.2f; "
              "turned 180 deg: pin overlap %.1f mm3 (blocked)" % (max(ovs), tA, tD, ov_rot))

    # ------------------------------------------------------------------ (6) J-e
    print("\n== (6) J-e depth gauges (cone 118 deg measured from the STL)")
    je = byk["J-e"]
    tm = TM["J-e"]
    for gdef in je.meta["gauges"]:
        x, y, d = gdef["x"], gdef["y"], gdef["d"]
        zc = gdef["z_cyl_bottom"]
        rad = []
        for z in (zc - 0.6, zc - 1.2):
            pts = section_pts(tm, (0, 0, z), (0, 0, 1))
            c, r, n = circle_near(pts[:, :2], (x, y), 2 * ((z - (zc - gdef["cone"])) * math.tan(math.radians(PJ.POINT_DEG / 2))), band=0.5)
            rad.append((z, r))
        (z1, r1), (z2, r2) = rad
        slope = (r1 - r2) / (z1 - z2)                         # dr/dz of the cone
        z_seat = z1 + (gdef["bit"] / 2.0 - r1) / slope        # where the cone radius = the bit radius -> the bit's lip corners
        stick = je.meta["gauge_h"] - z_seat
        target = PJ.GUIDE + gdef["depth"]
        ang = 2 * math.degrees(math.atan(slope))
        print(ok(abs(stick - target) <= 0.1 and abs(ang - PJ.POINT_DEG) < 2.0, "J-e %s" % gdef["name"]),
              "%-8s bore D%.2f: bit lip corners seat %.3f below the top (GUIDE %.0f + %.1f = %.1f; +%.3f from the 0.1 bore clearance), cone %.1f deg"
              % (gdef["name"], d, stick, PJ.GUIDE, gdef["depth"], target, stick - target, ang))

    # ------------------------------------------------------------------ (7) minimum wall
    print("\n== (7) minimum wall (rays from 15000 surface samples per STL, limit %.1f)" % WALL_MIN)
    for j in jigs:
        tm = TM[j.key]
        th, nrm, pts = wall_rays(tm, 15000)
        flipped = abs(j.R_print[2, 2] + 1.0) < 1e-9
        skins = [(0.0, ENGRAVE_SKIN)] if flipped else []
        if j.key == "J-a5":
            skins = [(0.0, ENGRAVE_SKIN)]
        if j.key == "J-e":
            skins = [(PJ.GAUGE_H - ENGRAVE_SKIN, PJ.GAUGE_H), (PJ.GUIDE - ENGRAVE_SKIN, PJ.GUIDE)]
        if j.key == "J-f":
            skins = [(8.0 - ENGRAVE_SKIN, 8.0)]                 # handle top label
        if j.key.endswith("b") and j.key[:3] == "J-d":
            skins = [(PJ.PLATE_T - 0.05, PJ.PLATE_T + PJ.RAISE + 0.05)]
        side = np.abs(nrm[:, 2]) < 0.9
        txt = np.zeros(len(pts), bool)
        for z0, z1 in skins:
            txt |= side & (pts[:, 2] >= z0 - 1e-6) & (pts[:, 2] <= z1 + 1e-6)
        is_shim = j.key.endswith("c") and j.key[:3] == "J-d"
        mn = float(th[~txt].min()) if np.any(~txt) else float("inf")
        lim = min(WALL_MIN, j.meta["p"] - 0.01) if is_shim else WALL_MIN
        note = " (shim blade = pass step p %.2f: thickness is the function, print as is)" % j.meta["p"] if is_shim and mn < WALL_MIN else ""
        print(ok(mn >= lim, "%s wall" % j.key), "%-7s min wall %.2f (label text side walls excluded: %d samples)%s" % (j.key, mn, int(txt.sum()), note))
    # ------------------------------------------------------------------ (8) J-c tongue in the drilled slot
    print("\n== (8) J-c slot tongue vs the J-d slot (narrowest clear width = 4 - 2 cusp - 2 slider play)")
    groups = {g["key"]: g for g in PJ.slot_groups()}
    for key, gk in (("J-c1", "J-d1"), ("J-c2", "J-d2")):
        j = byk[key]
        k0, k1, k2, k3 = j.meta["key"]
        # tongue measured from the STL taken back to the local frame: section 3.5 below the wood face
        polys = [np.asarray(q) for q in MAN[key].slice(-PJ.FENCE_DROP / 2.0).to_polygons()]
        sv = 1.0 if j.meta["side"] == "L" else -1.0
        cand = [q for q in polys if abs(q[:, 0].min() - k0) < 0.05 and abs(q[:, 0].max() - k1) < 0.05]
        tw = None
        if cand:
            q = cand[0]
            tw = min(q[:, 0].max() - q[:, 0].min(), q[:, 1].max() - q[:, 1].min())
        gr = groups[gk]
        pmax = gr["p"] + PJ.TRAVEL_EXTRA
        cusp = 2.0 - math.sqrt(4.0 - (pmax / 2.0) ** 2)
        clear_w = PJ.BIT_SLOT - 2.0 * cusp - 2.0 * PJ.SLIDE_CLR
        cl = (clear_w - tw) / 2.0 if tw is not None else -1.0
        why = ("lid L: tongue across the slot is set from the back edge by both J-d1 and J-c1" if key == "J-c1" else
               "lid R: J-d2 sets the slot from the screen-lid end, J-c2 from the far end -> the clearance also takes the lid length error")
        print(ok(tw is not None and cl >= 0.5, "%s tongue" % key), "%-5s tongue %.2f wide (measured), slot clear width %.2f -> %.2f per side (%s)" % (
            key, tw if tw is not None else float("nan"), clear_w, cl, why))

    print("\n%s: %d problem(s)" % ("PASS" if not FAIL else "FAIL", len(FAIL)))
    for f in FAIL:
        print("  -", f)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
