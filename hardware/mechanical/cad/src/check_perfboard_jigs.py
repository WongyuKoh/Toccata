#!/usr/bin/env python3
"""Self-check for perfboard_jigs.py (build_all writes it to stl/print/09_기판지그; A16: only the PED jig P-PED is left).

  python3 src/check_perfboard_jigs.py      # writes the jigs to a temp dir and checks those STLs

(1) every STL: watertight, one body, on z = 0, size
(2) guide bores MEASURED BACK FROM THE STL (section at mid plate, least-squares circle) in the use frame vs the fixing points:
    centre <= 0.05, D = bit + 0.2; and the same points measured from the electronics.py model board (CU-E-PEDBOARD holes) <= 0.05
(3) registration pins measured from the STL: on a grid hole centre (<= 0.02), D0.9 in the D1.0 hole, >= 2.0 from every cut line,
    clear of the bores
(4) cut edges: plate section = the board outline (0..70 x 0..50, <= 0.02)
(5) BE163 layout: two 70 x 50 pieces on the 30 x 42 grid with a waste strip >= 1.0 between the cuts (one PED + one spare)
"""
import math
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl_toccata"))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from manifold3d import Manifold, Mesh  # noqa: E402

import perfboard_jigs as PB  # noqa: E402
from cadlib import box  # noqa: E402

TOL = 0.05
FAIL = []
N_OK = [0]


def ok(cond, msg):
    if not cond:
        FAIL.append(msg)
    else:
        N_OK[0] += 1
    print("%s %s" % ("OK " if cond else "NG ", msg))


def to_manifold(tm):
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32), tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def circle_fit(pts):
    P = np.asarray(pts, float)
    A = np.column_stack([2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))])
    b = (P ** 2).sum(1)
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]
    return cx, cy, 2 * math.sqrt(c + cx * cx + cy * cy)


def poly_area(p):
    p = np.asarray(p)
    return 0.5 * (np.dot(p[:, 0], np.roll(p[:, 1], 1)) - np.dot(p[:, 1], np.roll(p[:, 0], 1)))


def model_holes():
    """fixing holes measured from the electronics.py boards (world x, y, D): MB of O1 (minus its module x offset) and the PED board."""
    import electronics as E
    parts = {p.id: p for p in E.build()}
    out = {}
    for pid, key in (("CU-E-PEDBOARD", "P-PED"),):
        m = parts[pid].solid
        bb = m.bounding_box()
        cs = m.slice((bb[2] + bb[5]) / 2.0)
        hs = []
        for poly in cs.to_polygons():
            if abs(poly_area(poly)) < 20.0:
                cx, cy, d = circle_fit(poly)
                hs.append((cx, cy, d))
        out[key] = (hs, bb)
    return out


def main():
    S = {s["key"]: s for s in PB.specs()}
    tmp = tempfile.mkdtemp(prefix="toccata_pbjig_")
    paths = PB.write_files(tmp)
    mh = model_holes()
    for key, path in paths.items():
        s = S[key]
        W, H = s["size"]
        print("== %s  %s" % (key, os.path.basename(path)))
        tm = trimesh.load(path, force="mesh", process=True)
        b = tm.bounds
        ok(tm.is_watertight and tm.is_winding_consistent and len(tm.split(only_watertight=False)) == 1 and abs(b[0][2]) < 1e-6,
           "%s: watertight, one body, on the bed (z0); %.1f x %.1f x %.1f, volume %.1f cm3" % (key, *(b[1] - b[0]), tm.volume / 1000))
        _m, _p, t = PB.make(s)
        M = to_manifold(tm)
        R = np.asarray(PB.R_PRINT, float)
        A = np.zeros((3, 4))
        A[:, :3] = R.T
        A[:, 3] = -R.T @ t
        U = M.transform(A)                                    # back to the use frame
        # (4) outline + slot
        sec = U.slice(PB.PLATE_T / 2.0)
        x0, y0, x1, y1 = sec.bounds()
        ok(max(abs(x0), abs(y0), abs(x1 - W), abs(y1 - H)) <= 0.02,
           "%s cut edges = board outline 0..%.1f x 0..%.1f (measured %.3f..%.3f x %.3f..%.3f)" % (key, W, H, x0, x1, y0, y1))
        polys = sec.to_polygons()
        outer = max(polys, key=lambda p: abs(poly_area(p)))
        if s["slot"]:
            a, b_, c, d = s["slot"]
            win = U ^ box(a + 0.03, b_ - 0.03, -1.0, d - 0.03, 0.05, PB.PLATE_T - 0.05)
            sides = [U ^ box(a - 0.25, a - 0.05, 0.05, d - 0.05, 0.05, PB.PLATE_T - 1.0), U ^ box(b_ + 0.05, b_ + 0.25, 0.05, d - 0.05, 0.05, PB.PLATE_T - 1.0),
                     U ^ box(a + 0.05, b_ - 0.05, d + 0.05, d + 0.25, 0.05, PB.PLATE_T - 1.0)]
            vs_ = [p for p in outer if a - 0.02 <= p[0] <= b_ + 0.02 and 0.0 < p[1] <= d + 0.02]
            ok(win.volume() < 1e-3 and all(v_.volume() > 0.05 for v_ in sides)
               and any(abs(p[0] - a) < 0.01 and abs(p[1] - d) < 0.01 for p in vs_) and any(abs(p[0] - b_) < 0.01 and abs(p[1] - d) < 0.01 for p in vs_),
               "%s slot window x%.3f~%.3f (u%.3f~%.3f) to y%.1f (v%.1f) open to the front edge, plate on both sides and behind its end - "
               "the knife follows the slot outline" % (key, a + s["origin"][0], b_ + s["origin"][0], a, b_, d + s["origin"][1], d))
        # (2) bores
        holes = [p for p in polys if p is not outer and abs(poly_area(p)) < 30.0]
        meas = [circle_fit(p) for p in holes]
        bad = []
        for h in s["holes"]:
            best = min(meas, key=lambda c: math.hypot(c[0] - h["u"], c[1] - h["v"])) if meas else (1e9, 1e9, 0)
            e = math.hypot(best[0] - h["u"], best[1] - h["v"])
            dd = best[2] - (h["bit"] + PB.BORE_CLR)
            if e > TOL or abs(dd) > 0.05:
                bad.append("%s (%.2f,%.2f) err %.3f dD %.3f" % (h["kind"], h["u"], h["v"], e, dd))
        ok(not bad and len(meas) == len(s["holes"]),
           "%s guide bores measured from the STL at the fixing points (<= %.2f): %s" % (
               key, TOL, "; ".join("%s D%.1f -> bore %.1f at (%.2f, %.2f) = world (%.2f, %.2f)" % (
                   "M3 나사" if h["kind"] == "screw" else "위치 핀", h["bit"], h["bit"] + PB.BORE_CLR, h["u"], h["v"], h["world"][0], h["world"][1])
                   for h in s["holes"])) + ("  " + "; ".join(bad) if bad else ""))
        # the same points measured from the electronics.py board model
        hs, bb = mh[key]
        errs = []
        for h in s["holes"]:
            wx, wy = h["world"]
            near = min(hs, key=lambda c: math.hypot(c[0] - wx, c[1] - wy))
            errs.append((math.hypot(near[0] - wx, near[1] - wy), abs(near[2] - h["bit"])))
        ok(all(e <= TOL and dd <= 0.1 for e, dd in errs) and len(hs) == 4,
           "%s fixing points = the holes measured from the electronics.py board (%s): max %.3f, D within %.2f" % (
               key, "CU-E-PEDBOARD", max(e for e, _ in errs), max(d_ for _, d_ in errs)))
        # (3) pins
        ps = U.slice(-PB.PIN_L / 2.0).to_polygons()
        pins = [circle_fit(p) for p in ps]
        us, vs = PB.grid_nodes(s)
        offg, bad = [], []
        for (cu, cv, d) in pins:
            gi = min(range(len(us)), key=lambda i: abs(us[i] - cu))
            gj = min(range(len(vs)), key=lambda j: abs(vs[j] - cv))
            e = math.hypot(us[gi] - cu, vs[gj] - cv)
            if e > 0.02 or abs(d - PB.PIN_D) > 0.05:
                offg.append("(%.2f,%.2f) %.3f D%.2f" % (cu, cv, e, d))
            edge = min(cu, W - cu, cv, H - cv)
            if s["slot"]:
                a, b_, c, dd_ = s["slot"]
                if cv < dd_ + PB.MIN_PIN_EDGE:
                    edge = min(edge, abs(cu - a), abs(cu - b_))
            bore = min(math.hypot(cu - h["u"], cv - h["v"]) - (h["bit"] + PB.BORE_CLR) / 2 for h in s["holes"])
            if edge < PB.MIN_PIN_EDGE - 1e-6 or bore < PB.MIN_PIN_BORE - 1e-6:
                bad.append("(%.2f,%.2f) edge %.2f bore %.2f" % (cu, cv, edge, bore))
        on_brd = True
        ok(len(pins) == len(PB.pin_nodes(s)) >= 4 and not offg and not bad and on_brd,
           "%s registration pins D%.1f x %.1f (into the D%.1f holes): %d on grid hole centres (<= 0.02)%s, >= %.1f from cut lines / slot, "
           ">= %.1f from the bores: %s" % (key, PB.PIN_D, PB.PIN_L, PB.SHEET["hole_d"], len(pins),
                                            " (outline edges u0 / v0 mid-gap)",
                                            PB.MIN_PIN_EDGE, PB.MIN_PIN_BORE, " ".join("(%.2f,%.2f)" % (c[0], c[1]) for c in pins))
           + ("  " + "; ".join(offg + bad) if offg or bad else ""))
        ok(PB.PIN_L < PB.SHEET["t"], "%s pins %.1f long < board %.1f (do not poke through)" % (key, PB.PIN_L, PB.SHEET["t"]))
    # (5) sheet layout
    for a, b_ in (("P-PED", "P-PED"),):
        L = PB.sheet_layout(S[a], S[b_])
        ok(L["fits"] and L["strip"] >= 1.0,
           "BE163 %s x %s (%d x %d holes): %s + %s fit - columns %d of %d (first column %.2f from the left cut, sheet margin about %.2f), rows %d + %d spare + %d = %d "
           "of %d (waste strip %.2f between the two cuts)" % (PB.SHEET["w"], PB.SHEET["h"], PB.SHEET["cols"], PB.SHEET["rows"], a, b_, L["cols_used"],
                                                             PB.SHEET["cols"], L["a"]["u_first"], L["margin_u"], L["a"]["rows"], L["gap_rows"], L["b"]["rows"],
                                                             L["rows_used"], PB.SHEET["rows"], L["strip"]))
    print(".. boards (A16): MB 7 whole sheets (no jig) + PED %d piece -> 1 more sheet, its second 70 x 50 is a spare" % S["P-PED"]["qty_boards"])
    print()
    print("checks: %d OK, %d failed" % (N_OK[0], len(FAIL)))
    if FAIL:
        print("FAIL:\n  " + "\n  ".join(FAIL))
        sys.exit(1)


if __name__ == "__main__":
    main()
