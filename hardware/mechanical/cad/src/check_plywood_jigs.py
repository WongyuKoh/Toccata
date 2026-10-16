#!/usr/bin/env python3
"""Self-check for plywood_jigs.py (build_all writes them to stl/print/08_합판지그).

  python3 src/check_plywood_jigs.py      # writes every jig with plywood_jigs.write_files() to a temp dir and checks those STLs

2026-10-07: the lids, end walls and pod inner panels are printed, the plywood vents are D8 grids -> J-a / J-c / slot J-d / J-f are gone.
(1) every STL written: watertight + consistent winding (trimesh), one body, volume = generator solid, footprint <= 250 x 250,
    lies on z = 0; the jig set is J-b x4, J-d3, J-d4, J-e (nothing for the printed lids / end walls / pod panels)
(2) every guide bore MEASURED BACK FROM THE STL (section at mid guide length, least-squares circle) vs its target in the print
    frame (<= 0.05) and its diameter (bit + 0.2)
(3) the measured bore axes taken to the world (the jig placed on its board) vs the holes MEASURED FROM THE body.py MODEL MESHES
    (back ply D8 vents + top-edge magnet seats, bottom ply D8 vents): <= 0.05; every model hole of those boards has its bore
(4) placement: jig ^ board = 0 (sits on the board), fences touch the datum edges and the guides / pads touch the face (board moved
    0.05 toward each); J-b gaps vs an 11.5 edge
(6) J-e gauge: full-diameter seat depth below the top (cone measured from the STL) = GUIDE + target depth
(7) minimum wall >= 1.6 measured from the STLs (inward rays from surface samples; text side walls in the 0.85 label skin are
    reported but not failed)
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
    keys = sorted(j.key for j in jigs)
    want_keys = sorted(["J-b%.1f" % g for g in PJ.SADDLE_GAPS] + ["J-d3", "J-d4", "J-e"])
    print(ok(keys == want_keys and not PJ.OPTIONAL, "jig set"), "jig set (2026-10-07): %s - no J-a / J-c / slot J-d / J-f (lids, end walls, "
          "pod inner panels printed; plywood vents D8)" % ", ".join(keys))
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
    vent_e = {}
    MEAS = {}      # (jig key, bore name) -> (local point on axis, measured diameter)
    worst = 0.0
    for j in jigs:
        if not j.bores:
            continue
        tm = TM[j.key]
        for b in j.bores:
            w_mid = (PJ.GUIDE_THRU if j.key.startswith("J-d") else PJ.GUIDE) / 2.0
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
            good = e <= TOL and abs(2 * r - b["d"]) <= TOL
            if j.key.startswith("J-d"):
                ok(good, "%s %s bore" % (j.key, b["name"]))
                vent_e.setdefault(j.key, []).append((e, 2 * r, good))
                continue                    # 50 vent bores: summarised below
            print(ok(good, "%s %s bore" % (j.key, b["name"])),
                  "%-7s %-8s bit %.1f  bore D%.3f (design %.2f)  centre error %.4f" % (j.key, b["name"], b["bit"], 2 * r, b["d"], e))
    for k_, v_ in vent_e.items():
        print(ok(all(g for _, _, g in v_) and len(v_) == len(byk[k_].bores), "%s bores" % k_),
              "%-7s %d bores D%.2f: max centre error %.4f, diameters %.3f..%.3f" % (k_, len(v_), byk[k_].bores[0]["d"], max(e for e, _, _ in v_),
                                                                              min(d for _, d, _ in v_), max(d for _, d, _ in v_)))
    print("   worst bore centre error (all %d bores) %.4f mm" % (len(MEAS), worst))

    # ------------------------------------------------------------------ (3) world coordinates vs the model meshes
    print("\n== (3) bore axes in the world (jig on its board) vs the holes measured from the body.py model")
    o = B.Out()
    B.cu_panels(o)
    BOARD = {p.id: p.solid for p in o if p.kind == "plywood"}
    BTM = {k: tm_from_manifold(v) for k, v in BOARD.items()}
    for jk in ("J-d3", "J-d4"):
        j = byk[jk]
        bk = j.meta["board"]
        R, org = j.placements["use"]
        errs = []
        for b in j.bores:
            loc, dm = MEAS[(jk, b["name"])]
            wpt = np.asarray(R) @ loc + np.asarray(org)
            axis = np.asarray(R) @ np.array([0, 0, 1.0])
            c, dm_model = model_hole(BTM[bk], np.array(b["world"], float), axis, PJ.BIT_VENT, -PJ.PLY_T / 2.0)
            if c is None:
                errs.append((99.0, b["name"], 0.0))
                continue
            errs.append((perp_dist(wpt, c, axis), b["name"], dm_model))
        # every D8 vent of the model board has a bore (count the round holes of the board section at mid thickness)
        wdir = np.asarray(R)[:, 2]
        pts = section_pts(BTM[bk], np.asarray(org, float) - wdir * PJ.PLY_T / 2.0, wdir)
        n_model = len(B.BACK_HOLES) if bk == "CU-PLY-BACK" else len(B.BOT_HOLES_BUCK) + len(B.BOT_HOLES_PI)
        worst = max(e for e, _, _ in errs)
        print(ok(worst <= TOL and len(errs) == n_model and len(pts) > 0, "%s world" % jk),
              "%-5s on %-13s %d bores vs %d model holes D%.2f..%.2f: worst off-axis %.4f (%s)" % (
                  jk, bk, len(errs), n_model, min(d_ for _, _, d_ in errs), max(d_ for _, _, d_ in errs), worst,
                  max(errs)[1]))
    # J-b saddles on every back-ply edge seat (one variant is enough for the axis; all gaps share it)
    jb = byk["J-b11.6"]
    loc, _ = MEAS[("J-b11.6", "mag")]
    for pn, (R, org) in jb.placements.items():
        wpt = np.asarray(R) @ loc + np.asarray(org)
        axis = np.asarray(R) @ np.array([0, 0, 1.0])
        c, dmod = model_hole(BTM["CU-PLY-BACK"], org, axis, PJ.BIT_MAG, -PJ.DEPTH_MAG / 2.0)
        e = perp_dist(wpt, c, axis)
        print(ok(e <= TOL, "J-b %s" % pn), "J-b     %-6s on %-13s saddle axis (%.3f, %.3f) | model pocket D%.2f (%.3f, %.3f) | off-axis %.4f" % (
            pn, "CU-PLY-BACK", wpt[0], wpt[1], dmod, c[0], c[1], e))
    print(ok(len(jb.placements) == len(B.MAG_BACK_X["L"]) + len(B.MAG_BACK_X["R"]), "J-b seats"),
          "J-b seats: %d (back-ply top edge only; the end-wall seats are printed now)" % len(jb.placements))

    # ------------------------------------------------------------------ (4) placement / contact
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
        "J-d3": ("CU-PLY-BACK", [("오른쪽 끝", (1, 0, 0)), ("윗모서리", (0, 0, 1)), ("바깥면", (0, 1, 0))]),
        "J-d4": ("CU-PLY-BOTTOM", [("뒤 모서리", (0, 1, 0)), ("윗면", (0, 0, 1))]),
    }
    for key, (bk, shifts) in DAT.items():
        jm = placed(key, "use")
        board = BOARD[bk]
        ov = (jm ^ board).volume()
        res = [(nm, touch(jm, board, sh)) for nm, sh in shifts]
        good = ov <= 0.01 and all(v > 0.01 for _, v in res)
        print(ok(good, "%s placement" % key), "%-6s on %-13s overlap %.3f mm3; touches %s" % (
            key, bk, ov, ", ".join("%s %.2f" % (nm, v) for nm, v in res)))
    # J-d4: the plate edge on the pencil line (u = SIGHT_U from the left end) is the x datum
    j4 = byk["J-d4"]
    pb = placed("J-d4", "use").bounding_box()
    print(ok(abs(pb[0] - (B.CU_IX[0] + PJ.SIGHT_U)) < 0.01, "J-d4 sight"), "J-d4   plate edge x%.2f = left end x%.1f + %.0f (pencil line)"
          % (pb[0], B.CU_IX[0], PJ.SIGHT_U))
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

    # ------------------------------------------------------------------ (6) J-e
    print("\n== (6) J-e depth gauge (cone 118 deg measured from the STL)")
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
        if j.key == "J-e":
            skins = [(PJ.GAUGE_H - ENGRAVE_SKIN, PJ.GAUGE_H), (PJ.GUIDE - ENGRAVE_SKIN, PJ.GUIDE)]
        side = np.abs(nrm[:, 2]) < 0.9
        txt = np.zeros(len(pts), bool)
        for z0, z1 in skins:
            txt |= side & (pts[:, 2] >= z0 - 1e-6) & (pts[:, 2] <= z1 + 1e-6)
        mn = float(th[~txt].min()) if np.any(~txt) else float("inf")
        print(ok(mn >= WALL_MIN, "%s wall" % j.key), "%-7s min wall %.2f (label text side walls excluded: %d samples)" % (j.key, mn, int(txt.sum())))

    print("\n%s: %d problem(s)" % ("PASS" if not FAIL else "FAIL", len(FAIL)))
    for f in FAIL:
        print("  -", f)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
