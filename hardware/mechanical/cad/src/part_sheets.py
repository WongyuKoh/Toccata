"""Toccata - one dimensioned part drawing per print file + per plywood piece (SVG sheet + DXF + download zip).

Made FROM THE PRINT FILES THEMSELVES (stl/print/**.stl, stl/print_extra/**.stl, loaded byte for byte) and, for the
assembly pose and world coordinates, from the CAD instances of build_all.collect() (same session build as the STLs):

  * the drawing pose = the part as it sits in the instrument (part.solid), squared to the nearest 90 deg pose; a part that
    is tilted in the instrument (lever carriers, 40 deg speaker baffle, screen parts) is drawn untilted and the tilt is
    stated. Parts with no instance in the instrument (tools, jigs, spares, alternatives) are drawn as they lie in the STL
    (spares / alternatives borrow the pose of the file they replace).
  * views (third angle: plan above front, right side right of front) = exact hidden-line drawings of the mesh edges
    (sharp edges > 20 deg + silhouettes), visibility by ray casting against the solid (manifold3d), visible solid,
    hidden dashed; sections = manifold3d slices.
  * every number = measured on the solid: overall size, ordinates of the edges, holes / pockets (slices along x, y, z,
    circle fit, depth by bisection, open / blind ends), wall thicknesses and slot widths (facing edge pairs in the
    sections), slanted face angles. World coordinates of holes via the registration print file -> CAD instance
    (exact vertex correspondence when possible, otherwise rotation search + ICP; residual stated).
  * plywood pieces (kind 'plywood', 10): face view at 1:1 from drawings.flat_piece / piece_memo / ply_spots / ply_jigs
    (D06 logic: datum edges, through / blind holes with depth, edge pockets, screw spots, jigs) + edge views; the DXF has
    the cut outline (layer CUT, true circles) for a CNC / laser shop.

  python3 part_sheets.py                 # everything (sheets, DXF, zips, index, verify)
  python3 part_sheets.py P-01-01 P-PLY-03 # only these codes (no zips / index)
  python3 part_sheets.py --verify        # independent checks only (needs the sheets' JSON written by a full run)

Outputs: ../drawings/parts/svg/<code>.svg, ../drawings/parts/dxf/<code>.dxf, ../drawings/parts/data/<code>.json (measured
numbers), docs/report/toccata-v4/fin/parts/<code>.svg + <code>.zip.b64.txt + index.json + all-STL / all-DXF zips.
Never writes stl/print (build_all.main() does that; this module only calls build_all.collect()).
"""
import collections
import base64
import io
import json
import math
import os
import re
import sys
import time
import zipfile

import numpy as np
from manifold3d import Manifold, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import drawings as DR  # noqa: E402
from drawings import fnum, esc, text_w  # noqa: E402

CAD = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(CAD, "..", "..", ".."))
PDIR = os.path.join(CAD, "drawings", "parts")
FIN = os.path.join(REPO, "docs", "report", "toccata-v4", "fin", "parts")
DATE = "2026-10-08"
BED = (256.0, 256.0)            # P2S build plate (toccata-printer-choice)

# ------------------------------------------------------------------ small geometry helpers


def cube_rotations():
    """the 24 proper rotations that map axes onto axes."""
    out = []
    import itertools
    for perm in itertools.permutations(range(3)):
        for sg in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for i, (j, s) in enumerate(zip(perm, sg)):
                R[i, j] = s
            if np.linalg.det(R) > 0.5:
                out.append(R)
    return out


CUBE = cube_rotations()


def nearest_cube(R):
    return max(CUBE, key=lambda Q: float(np.trace(Q.T @ R)))


def rot_angle(R):
    c = (np.trace(R) - 1.0) / 2.0
    ang = math.degrees(math.acos(max(-1.0, min(1.0, c))))
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    n = np.linalg.norm(ax)
    return ang, (ax / n if n > 1e-9 else np.array([0.0, 0.0, 1.0]))


def affine(R, t):
    M = np.zeros((3, 4))
    M[:, :3] = R
    M[:, 3] = t
    return M


def mesh_arrays(M):
    m = M.to_mesh()
    V = np.asarray(m.vert_properties, float)[:, :3]
    F = np.asarray(m.tri_verts, np.int64)
    # merge coincident vertices (property seams) so every edge has two faces
    key = np.round(V, 5)
    uq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    Vm = np.zeros((len(uq), 3))
    Vm[inv] = V
    F = inv[F]
    ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    return Vm, F[ok]


def stl_manifold(path):
    import trimesh
    tm = trimesh.load(path, process=True)
    tm.merge_vertices()
    M = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    if str(M.status()) != "Error.NoError":
        raise RuntimeError("STL is not a closed solid: %s (%s)" % (path, M.status()))
    return M


def circle_fit(P):
    """algebraic (Kasa) circle fit -> (cx, cy, r, max |residual|)."""
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(P))]
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0], sol[1]
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    res = np.abs(np.hypot(x - cx, y - cy) - r)
    return cx, cy, r, float(res.max()) if len(res) else 0.0


def round_shape(P):
    """closed ring P (n x 2) -> dict(kind 'circle' | 'tear' | None, cx, cy, d, tip) using inlier circle fits."""
    if len(P) < 10:
        return None
    cx, cy, r, mres = circle_fit(P)
    if r <= 0:
        return None
    if mres <= max(0.012, 0.012 * r):
        return dict(kind="circle", cx=cx, cy=cy, d=2 * r, tip=None)
    # teardrop / D-shape: drop the worst point and refit until the rest lies on one circle
    pts = P.copy()
    while len(pts) >= max(8, 0.55 * len(P)):
        cx, cy, r, mres = circle_fit(pts)
        if mres <= max(0.012, 0.012 * r):
            break
        rr = np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r)
        pts = np.delete(pts, int(np.argmax(rr)), axis=0)
    else:
        return None
    if r <= 0 or mres > max(0.012, 0.012 * r):
        return None
    frac = len(pts) / float(len(P))
    ang = np.sort(np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx))
    gaps = np.diff(np.r_[ang, ang[0] + 2 * math.pi])
    span = 360.0 - math.degrees(gaps.max())
    if frac < 0.55 or span < 230:
        return None
    far = P[np.argmax(np.hypot(P[:, 0] - cx, P[:, 1] - cy))]
    return dict(kind="tear", cx=cx, cy=cy, d=2 * r, tip=(float(far[0]), float(far[1])), span=span)


def signed_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def rdp(P, eps):
    """Douglas-Peucker on an open polyline."""
    if len(P) < 3:
        return P
    keep = np.zeros(len(P), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        d = b - a
        L = math.hypot(*d)
        seg = P[i + 1:j]
        if L < 1e-12:
            dist = np.hypot(seg[:, 0] - a[0], seg[:, 1] - a[1])
        else:
            dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(dist))
        if dist[k] > eps:
            keep[i + 1 + k] = True
            stack.append((i, i + 1 + k))
            stack.append((i + 1 + k, j))
    return P[keep]


# ------------------------------------------------------------------ hidden-line views

VIEWS = {
    # name: (direction toward the viewer, u axis, v axis)
    "top": (np.array([0.0, 0.0, 1.0]), 0, 1),
    "front": (np.array([0.0, -1.0, 0.0]), 0, 2),
    "side": (np.array([1.0, 0.0, 0.0]), 1, 2),
    "bottom": (np.array([0.0, 0.0, -1.0]), 0, 1),
}
VIEW_KO = {"top": "평면도 (위에서)", "front": "정면도 (앞에서)", "side": "우측면도 (오른쪽에서)", "bottom": "저면도 (밑에서, 좌우 그대로)"}


class Geo:
    """the part in drawing pose: D (Manifold, min corner at the origin), mesh, edges."""

    def __init__(self, D):
        self.D = D
        b = D.bounding_box()
        self.ext = np.array([b[3] - b[0], b[4] - b[1], b[5] - b[2]])
        self.V, self.F = mesh_arrays(D)
        V, F = self.V, self.F
        n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        a = np.linalg.norm(n, axis=1)
        self.N = n / np.where(a > 0, a, 1)[:, None]
        E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        fid = np.tile(np.arange(len(F)), 3)
        Es = np.sort(E, axis=1)
        key = Es[:, 0] * (len(V) + 1) + Es[:, 1]
        o = np.argsort(key, kind="stable")
        ks = key[o]
        same = np.nonzero(ks[1:] == ks[:-1])[0]
        i0, i1 = o[same], o[same + 1]
        self.E = Es[i0]
        self.f0, self.f1 = fid[i0], fid[i1]
        c = np.einsum("ij,ij->i", self.N[self.f0], self.N[self.f1])
        self.sharp = c < math.cos(math.radians(20.0))
        nav = self.N[self.f0] + self.N[self.f1]
        ln = np.linalg.norm(nav, axis=1)
        self.navg = nav / np.where(ln > 1e-9, ln, 1)[:, None]
        self.diag = float(np.linalg.norm(self.ext)) + 10.0
        self._views = {}

    # ---- visibility
    def _visible(self, P, d):
        """P: (n, 3) points already offset off the surface; True where nothing lies between P and the viewer."""
        out = np.zeros(len(P), bool)
        D = self.D
        far = self.diag * 2
        for i, p in enumerate(P):
            o = p + d * 1e-4
            out[i] = len(D.ray_cast(tuple(o), tuple(o + d * far))) == 0
        return out

    def view(self, name):
        if name in self._views:
            return self._views[name]
        d, iu, iv = VIEWS[name]
        V = self.V
        s0 = self.N[self.f0] @ d
        s1 = self.N[self.f1] @ d
        sil = (s0 * s1 < 0) | ((np.abs(s0) < 1e-9) ^ (np.abs(s1) < 1e-9))
        cand = np.nonzero(self.sharp | sil)[0]
        A = V[self.E[cand, 0]]
        B = V[self.E[cand, 1]]
        Pa = np.c_[A[:, iu], A[:, iv]]
        Pb = np.c_[B[:, iu], B[:, iv]]
        L2 = np.hypot(*(Pb - Pa).T)
        keep = L2 > 1e-4
        cand, A, B, Pa, Pb, L2 = cand[keep], A[keep], B[keep], Pa[keep], Pb[keep], L2[keep]
        off = self.navg[cand] * 0.006
        vis_segs, hid_segs = [], []
        for k in range(len(cand)):
            n = int(min(40, max(2, math.ceil(L2[k] / 0.6) + 1)))
            ts = np.linspace(0.0, 1.0, n)
            ts[0], ts[-1] = 0.02 if n > 2 else 0.05, 0.98 if n > 2 else 0.95
            P3 = A[k] + (B[k] - A[k]) * ts[:, None] + off[k]
            vis = self._visible(P3, d)
            # split at the visibility changes (bisection to 1/16 of a sample step)
            cuts = [0.0]
            states = [bool(vis[0])]
            for i in range(1, n):
                if vis[i] != vis[i - 1]:
                    lo, hi = ts[i - 1], ts[i]
                    for _ in range(5):
                        m = (lo + hi) / 2
                        vm = self._visible((A[k] + (B[k] - A[k]) * m + off[k])[None, :], d)[0]
                        if vm == vis[i - 1]:
                            lo = m
                        else:
                            hi = m
                    cuts.append((lo + hi) / 2)
                    states.append(bool(vis[i]))
            cuts.append(1.0)
            for j, st in enumerate(states):
                t0, t1 = cuts[j], cuts[j + 1]
                if t1 - t0 < 1e-6:
                    continue
                q0 = Pa[k] + (Pb[k] - Pa[k]) * t0
                q1 = Pa[k] + (Pb[k] - Pa[k]) * t1
                (vis_segs if st else hid_segs).append((q0[0], q0[1], q1[0], q1[1]))
        vis_segs = np.array(vis_segs).reshape(-1, 4)
        hid_segs = np.array(hid_segs).reshape(-1, 4)
        vis_segs, hid_segs = clean_segments(vis_segs, hid_segs)
        res = dict(vis=chain(vis_segs), hid=chain(hid_segs), vis_segs=vis_segs, hid_segs=hid_segs,
                   size=(self.ext[iu], self.ext[iv]))
        self._views[name] = res
        return res


def _line_groups(S):
    """segments (n, 4) -> {(theta_q, rho_q): [(t0, t1, k)]}: collinear groups with intervals along the line direction."""
    groups = collections.defaultdict(list)
    for k, (x0, y0, x1, y1) in enumerate(S):
        dx, dy = x1 - x0, y1 - y0
        th = math.atan2(dy, dx)
        if th < -0.0005:
            th += math.pi
        if th >= math.pi - 0.0005:
            th -= math.pi
        ux, uy = math.cos(th), math.sin(th)
        rho = -uy * x0 + ux * y0
        t0, t1 = sorted((ux * x0 + uy * y0, ux * x1 + uy * y1))
        groups[(int(round(math.degrees(th) / 0.05)) % 3600, int(round(rho / 0.004)))].append((t0, t1, th, rho))
    return groups


def _union(iv, tol=0.003):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + tol:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _subtract(iv, cut, tol=0.003):
    out = []
    for a, b in iv:
        segs = [[a, b]]
        for c0, c1 in cut:
            nxt = []
            for s0, s1 in segs:
                if c1 <= s0 + tol or c0 >= s1 - tol:
                    nxt.append([s0, s1])
                    continue
                if c0 > s0 + tol:
                    nxt.append([s0, c0])
                if c1 < s1 - tol:
                    nxt.append([c1, s1])
            segs = nxt
        out += segs
    return [s for s in out if s[1] - s[0] > 0.02]


def clean_segments(vis, hid):
    """merge collinear overlapping segments; remove hidden parts covered by visible lines."""
    gv = _line_groups(vis)
    gh = _line_groups(hid)

    def emit(key_list, store):
        out = []
        for (th, rho, ivs) in key_list:
            ux, uy = math.cos(th), math.sin(th)
            for a, b in ivs:
                out.append((ux * a - uy * rho, uy * a + ux * rho, ux * b - uy * rho, uy * b + ux * rho))
        return np.array(out).reshape(-1, 4)

    vlist, hlist = [], []
    vunion = {}
    for k, lst in gv.items():
        th = float(np.mean([t[2] for t in lst]))
        rho = float(np.mean([t[3] for t in lst]))
        u = _union([(t[0], t[1]) for t in lst])
        vunion[k] = u
        vlist.append((th, rho, u))
    for k, lst in gh.items():
        th = float(np.mean([t[2] for t in lst]))
        rho = float(np.mean([t[3] for t in lst]))
        u = _union([(t[0], t[1]) for t in lst])
        cut = []
        for dk in (-1, 0, 1):
            for dr in (-1, 0, 1):
                cut += vunion.get(((k[0] + dk) % 3600, k[1] + dr), [])
        u = _subtract(u, _union(cut)) if cut else u
        if u:
            hlist.append((th, rho, u))
    return emit(vlist, None), emit(hlist, None)


def chain(S, tol=0.004):
    """segments -> polylines (list of (n, 2) arrays, closed rings repeat the first point)."""
    if len(S) == 0:
        return []
    P = np.vstack([S[:, :2], S[:, 2:]])
    key = np.round(P / tol).astype(np.int64)
    uq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    n = len(S)
    a, b = inv[:n], inv[n:]
    pos = np.zeros((len(uq), 2))
    pos[inv] = P
    adj = collections.defaultdict(list)
    for k in range(n):
        if a[k] == b[k]:
            continue
        adj[a[k]].append((b[k], k))
        adj[b[k]].append((a[k], k))
    used = np.zeros(n, bool)
    out = []

    def walk(start):
        line = [start]
        cur = start
        while True:
            nxt = None
            for (nb, k) in adj[cur]:
                if not used[k]:
                    used[k] = True
                    nxt = nb
                    break
            if nxt is None:
                break
            line.append(nxt)
            cur = nxt
            if len(adj[cur]) != 2:
                break
            if cur == start:
                break
        return line

    for v in list(adj.keys()):
        if len(adj[v]) != 2:
            while any(not used[k] for _, k in adj[v]):
                out.append(walk(v))
    for v in list(adj.keys()):
        while any(not used[k] for _, k in adj[v]):
            out.append(walk(v))
    res = []
    for line in out:
        if len(line) < 2:
            continue
        P = pos[line]
        closed = line[0] == line[-1] and len(line) > 3
        Q = rdp(P, 0.003)
        res.append(dict(pts=Q, closed=closed))
    return res


def as_curves(polys):
    """polylines -> drawing primitives: circles (closed rings on a circle), arcs, polylines."""
    out = []
    for pl in polys:
        P = pl["pts"]
        if pl["closed"] and len(P) >= 13:
            cx, cy, r, mres = circle_fit(P[:-1])
            if r > 0.05 and mres <= max(0.006, 0.006 * r):
                out.append(("circle", (cx, cy, r)))
                continue
        if not pl["closed"] and len(P) >= 7:
            cx, cy, r, mres = circle_fit(P)
            if r > 0.05 and mres <= max(0.006, 0.006 * r):
                a0 = math.atan2(P[0][1] - cy, P[0][0] - cx)
                a1 = math.atan2(P[-1][1] - cy, P[-1][0] - cx)
                am = math.atan2(P[len(P) // 2][1] - cy, P[len(P) // 2][0] - cx)
                # sweep direction through the middle point
                def norm(a):
                    return a % (2 * math.pi)
                ccw = norm(am - a0) < norm(a1 - a0)
                sweep = norm(a1 - a0) if ccw else norm(a0 - a1)
                if sweep < math.radians(350):
                    out.append(("arc", (cx, cy, r, a0, a1, ccw, P[0], P[-1])))
                    continue
        out.append(("poly", P))
    return out


# ------------------------------------------------------------------ print file -> CAD instance (world pose)


def kabsch(A, B):
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    t = cb - R @ ca
    return R, t


def register(print_m, world_m, print_part_m=None):
    """rigid transform print coords -> world coords (R, t, residual mm, method).
    1) the CAD print solid and the world solid share the vertex list -> exact Kabsch;
    2) otherwise rotation search over the 24 axis poses + ICP on surface samples (trimesh)."""
    src = print_part_m if print_part_m is not None else print_m
    a = np.asarray(src.to_mesh().vert_properties, float)[:, :3]
    b = np.asarray(world_m.to_mesh().vert_properties, float)[:, :3]
    if a.shape == b.shape and len(a) >= 4:
        R, t = kabsch(a, b)
        res = float(np.abs(a @ R.T + t - b).max())
        if res < 0.02:
            return R, t, res, "kabsch"
    import trimesh
    Vw, Fw = mesh_arrays(world_m)
    tw = trimesh.Trimesh(Vw, Fw, process=False)
    Vp, Fp = mesh_arrays(print_m)
    tp = trimesh.Trimesh(Vp, Fp, process=False)
    rng = np.random.default_rng(7)
    pts, _ = trimesh.sample.sample_surface(tp, 600, seed=7)
    cw = tw.bounds.mean(0)
    best = None
    for Q in CUBE:
        P = pts @ Q.T
        c0 = (tp.bounds @ Q.T)
        cp = (c0.min(0) + c0.max(0)) / 2
        T = np.eye(4)
        T[:3, :3] = Q
        T[:3, 3] = cw - cp
        q = pts[rng.choice(len(pts), 150, replace=False)] @ Q.T + (cw - cp)
        _, dist, _ = trimesh.proximity.closest_point(tw, q)
        sc = float(np.mean(dist))
        if best is None or sc < best[0]:
            best = (sc, T)
    cands = sorted([best])
    out = None
    for sc, T0 in cands:
        M, tr, cost = trimesh.registration.icp(pts, tw, initial=T0, threshold=1e-7, max_iterations=60, reflection=False, scale=False)
        if out is None or cost < out[2]:
            out = (M[:3, :3], M[:3, 3], cost)
    R, t = out[0], out[1]
    # trimmed refinement: drop samples that have no partner (print-only support tabs, the thicker 5T pad wedge)
    for keep_d in (0.3, 0.08, 0.03):
        _, dist, _ = trimesh.proximity.closest_point(tw, pts @ R.T + t)
        sel = pts[dist < keep_d]
        if len(sel) < 60:
            break
        T0 = np.eye(4)
        T0[:3, :3], T0[:3, 3] = R, t
        M, _tr, _c = trimesh.registration.icp(sel, tw, initial=T0, threshold=1e-8, max_iterations=60, reflection=False, scale=False)
        R, t = M[:3, :3], M[:3, 3]
    _, dist, _ = trimesh.proximity.closest_point(tw, pts @ R.T + t)
    share = float(np.mean(dist < 0.02))
    return R, t, float(np.median(dist)), "icp, %d %% of the surface within 0.02" % round(100 * share)


FOLDER_NO = collections.OrderedDict([
    ("01_건반", "01"), ("02_레버캐리어", "02"), ("03_프레임", "03"), ("04_센서바·패드바·가림판·마개", "04"), ("05_본체출력물", "05"),
    ("06_출력공구", "06"), ("07_터치스크린", "07"), ("08_합판지그", "08"), ("09_기판지그", "09")])
FOLDER_KO = {"01": "01 건반", "02": "02 레버 캐리어", "03": "03 프레임", "04": "04 센서 바·패드 바·가림판·마개", "05": "05 본체 출력물",
             "06": "06 출력 공구", "07": "07 터치스크린", "08": "08 합판 지그", "09": "09 기판 지그", "PLY": "합판 (재단)",
             "EX": "선택·대안·예비"}
NOTE_ORDER = ["C", "C#·D#", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#·A#0", "A#", "B", "A0", "A#0", "B0", "C8"]


def _note_key(name):
    m = re.search(r"_([A-G][#·A-G0-9]*)$", name)
    if m and m.group(1) in NOTE_ORDER:
        return NOTE_ORDER.index(m.group(1))
    return 99


def collect_items(man):
    """manifest print rows -> ordered items with codes (P-<folder>-<nn>, P-EX-<nn>)."""
    rows = man["print"]
    items = []
    by_folder = collections.OrderedDict((k, []) for k in FOLDER_NO)
    extra = []
    for i, r in enumerate(rows):
        if r.get("extra") or r["folder"].startswith("@extra/"):
            extra.append((i, r))
        else:
            by_folder.setdefault(r["folder"], []).append((i, r))
    for folder, lst in by_folder.items():
        no = FOLDER_NO.get(folder, "99")
        if no in ("01", "02"):
            lst = sorted(lst, key=lambda t: (0 if t[1]["name"].startswith("백건") else 1, _note_key(t[1]["name"]), t[0]))
        for n, (i, r) in enumerate(lst, 1):
            items.append(dict(code="P-%s-%02d" % (no, n), group=no, row=r, kind="print"))
    sub_order = ["@extra/예비_건반", "@extra/대안_패드바_PORON6T용", "@extra/선택_화면덮개"]
    extra = sorted(extra, key=lambda t: (sub_order.index(t[1]["folder"]) if t[1]["folder"] in sub_order else 9,
                                         0 if t[1]["name"].startswith("백건") else 1, _note_key(t[1]["name"]), t[0]))
    for n, (i, r) in enumerate(extra, 1):
        items.append(dict(code="P-EX-%02d" % n, group="EX", row=r, kind="print"))
    return items


# ------------------------------------------------------------------ holes / pockets / walls / slots / angles (measured)

AX = "xyz"
PLANE_AX = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}     # slice axis -> the two in-plane axes (DR.sec returns these)


def slice_polys(D, axis, c):
    return [np.asarray(p, float) for p in DR.sec(D, axis, c).to_polygons() if len(p) >= 3]


def _vlevels(V, axis_i, lo, hi):
    """the vertex planes along one axis (rounded to 0.001). The bounds get a 0.002 tolerance: the STL is float32, so the
    top face of a part 44.85 high sits at 44.849998 and rounds to 44.85 > ext (it used to be dropped, and with it the
    whole top interval: blind holes / pockets that start at the top face were never sliced)."""
    ev = np.unique(np.round(V[:, axis_i], 3))
    return ev[(ev >= lo - 0.002) & (ev <= hi + 0.002)]


def _levels(V, axis_i, lo, hi, cap=2000):
    """one slice level in the middle of EVERY interval between neighbouring vertex planes (between two planes the section
    of a triangle mesh only moves linearly, so one level per interval sees every inner ring). The cap is far above the
    biggest part (1225 intervals) so nothing is skipped; past it the widest intervals + a uniform grid are kept."""
    ev = _vlevels(V, axis_i, lo, hi)
    mids = [(a + b) / 2 for a, b in zip(ev[:-1], ev[1:]) if b - a > 0.03]
    if len(mids) > cap:
        # keep the midpoints of the widest gaps + a uniform grid snapped to midpoints
        gaps = sorted([(b - a, (a + b) / 2) for a, b in zip(ev[:-1], ev[1:]) if b - a > 0.03], reverse=True)
        keep = set(round(m, 4) for _, m in gaps[:cap // 2])
        arr = np.array(mids)
        for g in np.linspace(lo, hi, cap // 2 + 2)[1:-1]:
            keep.add(round(float(arr[np.argmin(np.abs(arr - g))]), 4))
        mids = sorted(keep)
    return np.array(mids)


def _inner_rings(polys):
    return [p for p in polys if signed_area(p) < 0]


def _point_in_polys(polys, u, v):
    """even-odd point test against all rings."""
    inside = False
    for P in polys:
        x, y = P[:, 0], P[:, 1]
        x2, y2 = np.roll(x, -1), np.roll(y, -1)
        cond = (y > v) != (y2 > v)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = x + (v - y) * (x2 - x) / (y2 - y)
        inside ^= bool(np.sum(cond & (u < xi)) % 2)
    return inside


def round_fits_box(rs, u0, u1, v0, v1):
    """a fitted circle only describes the ring when it matches the ring's own extent: the circle lies inside the ring's
    bounding box and at least one box side equals the diameter (a circle: both; a teardrop: the side across the tip; a
    D-shape is not used in Toccata). A big opening with rounded corners or a letter with a curved stroke can pass the
    inlier fit with a circle far bigger than the ring itself (P-03-01 lever bay 39.16 x 63.85 'Ø71.48') -> rejected."""
    d = rs["d"]
    r = d / 2.0
    tol = max(0.1, 0.01 * d)          # a polygon circle: the box can be d·cos(pi/n) across flats
    w, h = u1 - u0, v1 - v0
    inside = (rs["cx"] - r >= u0 - tol and rs["cx"] + r <= u1 + tol and rs["cy"] - r >= v0 - tol and rs["cy"] + r <= v1 + tol)
    side = abs(w - d) <= tol or abs(h - d) <= tol
    if rs["kind"] == "circle":
        side = abs(w - d) <= tol and abs(h - d) <= tol
    return inside and side


def describe_ring(P):
    """inner ring -> feature descriptor."""
    rs = round_shape(P)
    u0, v0 = P.min(0)
    u1, v1 = P.max(0)
    a = abs(signed_area(P))
    if rs is not None and not round_fits_box(rs, u0, u1, v0, v1):
        rs = None
    if rs is not None:
        return dict(shape="tear" if rs["kind"] == "tear" else "round", cu=rs["cx"], cv=rs["cy"], d=rs["d"], w=u1 - u0, h=v1 - v0,
                    u0=u0, u1=u1, v0=v0, v1=v1, area=a, tip=rs.get("tip"))
    # 'rect' only for a true rectangle (ledges, notches, rounded corners -> 'other': box + outline in the hole CSV)
    rect = a > 0.998 * (u1 - u0) * (v1 - v0)
    return dict(shape="rect" if rect else "other", cu=(u0 + u1) / 2, cv=(v0 + v1) / 2, d=None, w=u1 - u0, h=v1 - v0,
                u0=u0, u1=u1, v0=v0, v1=v1, area=a, tip=None)


def _fkey(f):
    q = lambda x: int(round(x / 0.05))
    if f["shape"] in ("round", "tear"):
        return (f["shape"], q(f["cu"]), q(f["cv"]), q(f["d"]))
    return (f["shape"], q(f["u0"]), q(f["u1"]), q(f["v0"]), q(f["v1"]))


def _match(f, g):
    if f["shape"] != g["shape"]:
        return False
    if f["shape"] in ("round", "tear"):
        return abs(f["cu"] - g["cu"]) < 0.08 and abs(f["cv"] - g["cv"]) < 0.08 and abs(f["d"] - g["d"]) < 0.08
    return all(abs(f[k] - g[k]) < 0.08 for k in ("u0", "u1", "v0", "v1"))


def _cont(g, f):
    """can ring f (next level) continue the track whose last ring is g? -> score or None."""
    if g["shape"] != f["shape"]:
        return None
    dc = math.hypot(f["cu"] - g["cu"], f["cv"] - g["cv"])
    if f["shape"] in ("round", "tear"):
        dd = abs(f["d"] - g["d"])
        if dc < 0.05 and dd < max(3.0, 0.8 * g["d"]):          # coaxial: cylinder -> cone -> counterbore
            return dc + 0.1 * dd
        if dc < 1.5 and dd < 1.5 and dc < 0.6 * max(g["d"], 0.5) + 0.2:
            return dc + dd
        return None
    if abs(f["w"] - g["w"]) < 0.12 and abs(f["h"] - g["h"]) < 0.12 and dc < 1.5:
        return dc
    if dc < 0.08 and f["area"] > 0.2 * g["area"] and g["area"] > 0.2 * f["area"] and f["shape"] == "other":
        return 2.0 + abs(f["area"] - g["area"]) / max(g["area"], 1e-6)
    # an opening with one slanted wall (ramp): three sides of the box stay, one moves -> the same void (one 'cavity' entry
    # over its whole depth instead of one short piece per vertex interval)
    same_sides = sum(abs(f[k] - g[k]) < 0.05 for k in ("u0", "u1", "v0", "v1"))
    if same_sides >= 3 and dc < 3.0 and f["area"] > 0.5 * g["area"] and g["area"] > 0.5 * f["area"]:
        return 4.0 + dc
    return None


def _same(f, g, tol=0.03):
    if f["shape"] != g["shape"]:
        return False
    if f["shape"] in ("round", "tear"):
        return abs(f["d"] - g["d"]) < tol and math.hypot(f["cu"] - g["cu"], f["cv"] - g["cv"]) < tol
    return all(abs(f[k] - g[k]) < tol for k in ("u0", "u1", "v0", "v1"))


def find_holes(G):
    """holes and closed pockets along x, y and z: inner rings of slices tracked level to level, split into straight
    pieces (constant section: cylinder / prism), cones (diameter changes: countersinks, chamfers), slanted pieces
    (centre moves) and changing cavities; exact ends of the straight pieces by bisection; end type 'open' (to air or
    into another void) / 'closed' (material: blind bottom)."""
    D, V, ext = G.D, G.V, G.ext
    out = []
    for ai, axis in enumerate(AX):
        ev = _vlevels(V, ai, 0.0, ext[ai])
        lv = _levels(V, ai, 0.0, ext[ai])
        if len(lv) == 0:
            continue

        def snap(c, a, b):
            """the end of a constant piece lies on a vertex plane between its last level in and the first level out: the one
            nearest to the bisection result (the bisection alone stops where the ring differs by 0.06, e.g. 0.03 up a 90 deg
            countersink)."""
            k = ev[(ev >= min(a, b) - 1e-6) & (ev <= max(a, b) + 1e-6)]
            return float(k[np.argmin(np.abs(k - c))]) if len(k) else c

        def plane_below(c):
            k = ev[ev <= c + 1e-9]
            return float(k[-1]) if len(k) else 0.0

        def plane_above(c):
            k = ev[ev >= c - 1e-9]
            return float(k[0]) if len(k) else float(ext[ai])
        tracks = []
        for li, c in enumerate(lv):
            descs = [describe_ring(P) for P in _inner_rings(slice_polys(D, axis, c))]
            descs = sorted([f for f in descs if f["area"] >= 0.3], key=lambda f: -f["area"])
            alive = [t for t in tracks if t["lv"][-1] == li - 1]
            claimed = set()
            for f in descs:
                best = None
                for t in alive:
                    if id(t) in claimed:
                        continue
                    sc = _cont(t["f"][-1], f)
                    if sc is not None and (best is None or sc < best[0]):
                        best = (sc, t)
                if best:
                    best[1]["lv"].append(li)
                    best[1]["f"].append(f)
                    claimed.add(id(best[1]))
                else:
                    t = dict(lv=[li], f=[f])
                    tracks.append(t)
                    claimed.add(id(t))

        def present(f, c, tol=0.06):
            for P in _inner_rings(slice_polys(D, axis, c)):
                if _same(f, describe_ring(P), tol):
                    return True
            return False

        def refine(f, c_in, c_out):
            a, b = c_out, c_in
            for _ in range(14):
                m = (a + b) / 2
                if present(f, m):
                    b = m
                else:
                    a = m
            return (a + b) / 2

        for t in tracks:
            fs, ls = t["f"], t["lv"]
            # split into runs of 'the same' section
            runs = [[0]]
            for j in range(1, len(fs)):
                if _same(fs[j], fs[runs[-1][-1]]):
                    runs[-1].append(j)
                else:
                    runs.append([j])
            # a run is a straight piece when its section holds over >= 0.12 (bisection between the neighbouring levels)
            pieces = []
            for r in runs:
                f = fs[r[0]]
                c_in0, c_in1 = lv[ls[r[0]]], lv[ls[r[-1]]]
                c_out0 = lv[ls[r[0]] - 1] if ls[r[0]] > 0 else 0.0
                c_out1 = lv[ls[r[-1]] + 1] if ls[r[-1]] + 1 < len(lv) else ext[ai]
                lo_r = refine(f, c_in0, c_out0)
                hi_r = refine(fs[r[-1]], c_in1, c_out1)
                if hi_r - lo_r >= (0.12 if f["shape"] in ("round", "tear") else 0.25):
                    pieces.append(dict(kind="const", idx=list(r), lo=snap(lo_r, c_in0, c_out0), hi=snap(hi_r, c_in1, c_out1)))
                elif pieces and pieces[-1]["kind"] == "var":
                    pieces[-1]["idx"] += r
                    pieces[-1]["hi"] = hi_r
                else:
                    pieces.append(dict(kind="var", idx=list(r), lo=lo_r, hi=hi_r))
            for pi, pc in enumerate(pieces):
                i0, i1 = pc["idx"][0], pc["idx"][-1]
                f0, f1 = fs[i0], fs[i1]
                if pc["kind"] == "const":
                    lo, hi = pc["lo"], pc["hi"]
                    feat = dict(f0, kind="straight")
                else:
                    # a changing piece (cone, slanted bore, cavity) runs between vertex planes: from the plane below its first
                    # level (or the end of the straight piece before it) to the plane above its last level (or the start of
                    # the next straight piece). A countersink that opens in a face therefore ends IN that face (P-05-19:
                    # z1.957~4.0, not z1.985~3.008 where the bisection of one middle level stopped).
                    lo = pieces[pi - 1]["hi"] if pi > 0 else plane_below(lv[ls[i0]])
                    hi = pieces[pi + 1]["lo"] if pi + 1 < len(pieces) else plane_above(lv[ls[i1]])
                    if hi - lo < 1e-3:
                        continue

                    def ring_at(c, f):
                        best = None
                        for P in _inner_rings(slice_polys(D, axis, c)):
                            g = describe_ring(P)
                            dc = math.hypot(g["cu"] - f["cu"], g["cv"] - f["cv"])
                            if g["shape"] == f["shape"] and dc < 1.5 and (best is None or dc < best[0]):
                                best = (dc, g)
                        return best[1] if best else f
                    g0, g1 = ring_at(lo + 0.01, f0), ring_at(hi - 0.01, f1)

                    def d_end(c, sgn, f):
                        """diameter AT the end plane c: two rings just inside, extrapolated linearly to c."""
                        e1, e2 = 0.004, min(0.1, (hi - lo) / 2)
                        s1, s2 = ring_at(c + sgn * e1, f), ring_at(c + sgn * e2, f)
                        if not s1.get("d") or not s2.get("d") or e2 <= e1 + 1e-6:
                            return (s1.get("d") or f["d"])
                        return s1["d"] + (s1["d"] - s2["d"]) * e1 / (e2 - e1)
                    if f0["shape"] in ("round", "tear"):
                        moved = math.hypot(g1["cu"] - g0["cu"], g1["cv"] - g0["cv"])
                        if moved < 0.05 and abs(g1["d"] - g0["d"]) > 0.05:
                            d_lo, d_hi = d_end(lo, 1, f0), d_end(hi, -1, f1)
                            # a cone that continues a straight neighbour starts at its diameter (no step)
                            if pi > 0 and pieces[pi - 1]["kind"] == "const" and abs(fs[pieces[pi - 1]["idx"][-1]]["d"] - d_lo) < 0.3:
                                d_lo = fs[pieces[pi - 1]["idx"][-1]]["d"]
                            if pi + 1 < len(pieces) and pieces[pi + 1]["kind"] == "const" and abs(fs[pieces[pi + 1]["idx"][0]]["d"] - d_hi) < 0.3:
                                d_hi = fs[pieces[pi + 1]["idx"][0]]["d"]
                            dm = max(d_lo, d_hi)
                            feat = dict(f0, kind="cone", d=dm, d_lo=d_lo, d_hi=d_hi, cu=g0["cu"], cv=g0["cv"], w=dm, h=dm,
                                        u0=g0["cu"] - dm / 2, u1=g0["cu"] + dm / 2, v0=g0["cv"] - dm / 2, v1=g0["cv"] + dm / 2)
                        else:
                            feat = dict(f0, kind="slant", d=(g0["d"] + g1["d"]) / 2, cu=g0["cu"], cv=g0["cv"], cu1=g1["cu"], cv1=g1["cv"])
                    else:
                        u0 = min(fs[j]["u0"] for j in pc["idx"])
                        u1 = max(fs[j]["u1"] for j in pc["idx"])
                        v0 = min(fs[j]["v0"] for j in pc["idx"])
                        v1 = max(fs[j]["v1"] for j in pc["idx"])
                        same_size = all(abs(fs[j]["w"] - f0["w"]) < 0.12 and abs(fs[j]["h"] - f0["h"]) < 0.12 for j in pc["idx"])
                        if same_size:
                            feat = dict(f0, kind="slant", cu=g0["cu"], cv=g0["cv"], cu1=g1["cu"], cv1=g1["cv"])
                        else:
                            feat = dict(f0, kind="cavity", shape="other", u0=u0, u1=u1, v0=v0, v1=v1, w=u1 - u0, h=v1 - v0,
                                        cu=(u0 + u1) / 2, cv=(v0 + v1) / 2, area=max(fs[j]["area"] for j in pc["idx"]))
                ends = []
                for zc, sgn, fe in ((lo, -1, f0), (hi, 1, f1)):
                    probe = zc + sgn * 0.05
                    if probe <= 0.0 or probe >= ext[ai]:
                        ends.append("open")
                        continue
                    pl = slice_polys(D, axis, probe)
                    ends.append("closed" if _point_in_polys(pl, fe["cu"], fe["cv"]) else "open")
                feat.update(axis=axis, lo=lo, hi=hi, depth=hi - lo, ends=ends)
                # a changing piece thinner than 0.25 (chamfer slices, flare steps) is no table entry of its own
                feat["thin"] = bool(pc["kind"] == "var" and hi - lo < 0.25)
                if pc["kind"] == "var" and f0["shape"] in ("rect", "other"):
                    feat["single"] = len(pc["idx"]) == 1
                    feat["grow"] = bool(abs(g0["w"] - g1["w"]) > 0.12 or abs(g0["h"] - g1["h"]) > 0.12)
                out.append(feat)
    # drop non-round features that duplicate the same void seen along another axis (closed cavities)
    res = []
    for h in out:
        if h["shape"] in ("rect", "other"):
            dup = False
            for j, g in enumerate(res):
                if g["shape"] in ("rect", "other") and g["axis"] != h["axis"] and not g.get("thin"):
                    A, B = _box3(g), _box3(h)
                    # the same void seen along two axes: the boxes cover each other (overlap > half of the BIGGER extent in
                    # x, y and z). A small piece that only touches a big void is a void of its own (the hollow under a
                    # white key front used to vanish behind the 6.8-deep front pocket seen along y)
                    if all(min(A[1][i], B[1][i]) - max(A[0][i], B[0][i]) > 0.5 * max(A[1][i] - A[0][i], B[1][i] - B[0][i]) for i in range(3)):
                        dup = True
                        # keep the view that holds more of the void (bigger box): P-02-13's slanted slot seen along z
                        # (z4.31~7.93) instead of the shorter piece seen along y
                        vol = lambda b_: float(np.prod(np.array(b_[1]) - np.array(b_[0])))
                        if not h.get("thin") and vol(B) > vol(A):
                            res[j] = h
                        break
            if dup:
                continue
        res.append(h)
    for h in res:
        h["isl"], h["outline"] = void_profile(D, h)
    return res


def void_profile(D, h):
    """at mid depth: the solid islands standing inside a pocket / opening (outer rings of the slice inside the hole ring)
    [(u0, u1, v0, v1)] and the hole's own outline (simplified to 0.005, part datum) for the CSV. P-05-16: the 38 x 36
    pocket at (49.5, 21) holds a 20.4 x 18 block, its twin at (89.5, 21) does not."""
    mid = (h["lo"] + h["hi"]) / 2
    pl = slice_polys(D, h["axis"], mid)
    hole = None
    for P in _inner_rings(pl):
        u0, v0 = P.min(0)
        u1, v1 = P.max(0)
        e = max(abs(u0 - h["u0"]), abs(u1 - h["u1"]), abs(v0 - h["v0"]), abs(v1 - h["v1"]))
        if h.get("kind") in ("cone", "slant", "cavity"):
            e = math.hypot((u0 + u1) / 2 - h["cu"], (v0 + v1) / 2 - h["cv"])
        if e < 0.3 and (hole is None or e < hole[0]):
            hole = (e, P)
    if hole is None:
        return [], []
    H = hole[1]
    Hc = np.vstack([H, H[:1]])
    outline = [(round(float(u), 3), round(float(v), 3)) for u, v in rdp(Hc, 0.005)[:-1]]
    hu0, hv0 = H.min(0)
    hu1, hv1 = H.max(0)
    out = []
    for P in pl:
        if signed_area(P) <= 0 or abs(signed_area(P)) < 0.05:
            continue
        u0, v0 = P.min(0)
        u1, v1 = P.max(0)
        if u0 >= hu0 - 1e-6 and u1 <= hu1 + 1e-6 and v0 >= hv0 - 1e-6 and v1 <= hv1 + 1e-6 and _point_in_polys([H], float(P[0, 0]), float(P[0, 1])):
            out.append(tuple(round(float(q), 3) for q in (u0, u1, v0, v1)))
    return sorted(out), outline


def _box3(h):
    iu, iv = PLANE_AX[h["axis"]]
    ia = AX.index(h["axis"])
    lo = [0.0] * 3
    hi = [0.0] * 3
    lo[iu], hi[iu] = h["u0"], h["u1"]
    lo[iv], hi[iv] = h["v0"], h["v1"]
    lo[ia], hi[ia] = h["lo"], h["hi"]
    return lo, hi


def box3_swept(h):
    """3D box (drawing coords) of a void, for a slanted piece over its whole run (start and end outline)."""
    lo, hi = _box3(h)
    if h.get("kind") == "slant" and "cu1" in h:
        iu, iv = PLANE_AX[h["axis"]]
        du, dv = h["cu1"] - h["cu"], h["cv1"] - h["cv"]
        lo[iu], hi[iu] = min(lo[iu], lo[iu] + du), max(hi[iu], hi[iu] + du)
        lo[iv], hi[iv] = min(lo[iv], lo[iv] + dv), max(hi[iv], hi[iv] + dv)
    return [[round(float(q), 4) for q in lo], [round(float(q), 4) for q in hi]]


def hole_point(h, at="lo"):
    """3D point (drawing coords) on the hole axis at its lo / hi / mid end."""
    iu, iv = PLANE_AX[h["axis"]]
    ia = AX.index(h["axis"])
    p = [0.0, 0.0, 0.0]
    p[iu], p[iv] = h["cu"], h["cv"]
    p[ia] = {"lo": h["lo"], "hi": h["hi"], "mid": (h["lo"] + h["hi"]) / 2}[at]
    return np.array(p)


def facing_pairs(polys, max_gap=25.0):
    """wall thicknesses (material between antiparallel edges) and gaps (air between facing edges) in a section:
    rays from edge sample points along the inward / outward normal to the first other edge. -> (walls, gaps):
    lists of (width, p0, p1, length weight)"""
    segs = []
    for P in polys:
        ccw = signed_area(P) > 0
        n = len(P)
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            d = b - a
            L = math.hypot(*d)
            if L < 0.3:
                continue
            t = d / L
            nout = np.array([t[1], -t[0]]) if ccw else np.array([-t[1], t[0]])   # outward (material on the left of a CCW ring)
            segs.append((a, b, L, nout))
    if not segs:
        return [], []
    A = np.array([s[0] for s in segs])
    B = np.array([s[1] for s in segs])
    NO = np.array([s[3] for s in segs])
    walls, gaps = [], []
    for k, (a, b, L, nout) in enumerate(segs):
        ns = int(min(6, max(1, L // 2)))
        for j in range(ns):
            t = (j + 0.5) / ns
            p = a + (b - a) * t
            for sgn, store in ((-1, walls), (1, gaps)):
                r = nout * sgn
                # ray p + s r vs all segments
                e = B - A
                den = r[0] * e[:, 1] - r[1] * e[:, 0]
                w = A - p
                with np.errstate(divide="ignore", invalid="ignore"):
                    s = (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / den
                    u = (w[:, 0] * r[1] - w[:, 1] * r[0]) / den
                ok = (np.abs(den) > 1e-9) & (s > 1e-4) & (u >= -1e-6) & (u <= 1 + 1e-6)
                ok[k] = False
                if not ok.any():
                    continue
                i = int(np.argmin(np.where(ok, s, np.inf)))
                dist = float(s[i])
                if dist > max_gap:
                    continue
                if float(NO[i] @ nout) > -0.985 or dist < 0.1:   # the edge hit must face back (antiparallel)
                    continue
                store.append((dist, p, p + r * dist, L / ns))
    return walls, gaps


def summarize_widths(items, nd=2, top=6):
    """[(w, p0, p1, wt)] -> [(w rounded, total length, example (p0, p1))] most frequent first."""
    agg = collections.OrderedDict()
    for w, p0, p1, wt in items:
        k = round(w, nd)
        if k not in agg:
            agg[k] = [0.0, (p0, p1)]
        agg[k][0] += wt
    lst = sorted(((k, v[0], v[1]) for k, v in agg.items()), key=lambda t: -t[1])
    return lst[:top]


# ------------------------------------------------------------------ measured features of one part (drawing pose)

FACE_KO = {(2, 1): "윗면(+z)", (2, -1): "밑면(-z)", (1, -1): "앞면(-y)", (1, 1): "뒷면(+y)", (0, -1): "왼쪽 면(-x)", (0, 1): "오른쪽 면(+x)"}
AXIS_VIEW = {"z": "top", "y": "front", "x": "side"}


def face_of(vec):
    i = int(np.argmax(np.abs(vec)))
    return FACE_KO[(i, 1 if vec[i] > 0 else -1)]


ENGR_MAX_DEPTH = 1.05     # the CAD engraves 0.4 (key action parts, pad bars), 0.5 (T2), 0.6 (perfboard jigs), 0.8 (plywood jigs)


def open_to_air(G, h):
    """True when the one open end of a void looks straight out of the part along its axis (nothing in the way): letters
    are cut into an outside face; a nut slot that opens into a crossing bore does not."""
    ia = AX.index(h["axis"])
    sgn = 1.0 if h["ends"][1] == "open" else -1.0
    p = hole_point(h, "hi" if sgn > 0 else "lo")
    p[ia] += sgn * 0.05
    d = np.zeros(3)
    d[ia] = sgn
    return bool(G._visible(p[None, :], d)[0])


def engraving(h, G=None, others=()):
    """engraved letters / marks: a straight void of any outline (letter strokes, 'O' rings that fit a circle, dots),
    at most 1.05 deep, at most 8 x 8, cut into one face that looks straight out to the air, and not stacked on a deeper
    void on the same axis line (a counterbore / nut slot step is not a letter)."""
    if h.get("kind") != "straight" or h["depth"] > ENGR_MAX_DEPTH or h["ends"].count("open") != 1:
        return False
    if max(h["w"], h["h"]) > 8.0 or h.get("area", 0) >= 25:
        return False
    for g in others:
        if g is not h and g["axis"] == h["axis"] and g["depth"] > ENGR_MAX_DEPTH and math.hypot(g["cu"] - h["cu"], g["cv"] - h["cv"]) < 0.2:
            return False
    return G is None or open_to_air(G, h)


def fragment(h):
    """short pieces of a changing void that are not a hole of their own: the tip of a tapering notch or the closed end of
    a hollow that opens elsewhere (one vertex interval, the outline grows or shrinks, not closed at both ends), and short
    (<= 1.05) slanted / changing slivers next to a bigger void. Their geometry is in the views and sections."""
    if h.get("thin"):
        return True
    if h.get("kind") not in ("slant", "cavity"):
        return False
    if h["depth"] <= ENGR_MAX_DEPTH and max(h["w"], h["h"]) <= 8.0:
        return True
    # one vertex interval only, not an inner cavity: a tapering tip (outline grows) or the closed end of a hollow that
    # opens elsewhere (black key front: y1.2~2.03, then open to the underside)
    return bool(h.get("single") and h["ends"] != ["closed", "closed"] and (h.get("grow") or "closed" in h["ends"]))


def ordinate_candidates(view_res, axis_k, lo, hi):
    """coordinates of the long straight visible edges perpendicular to the u (axis_k 0) / v (1) axis -> {coord: length}."""
    out = collections.defaultdict(float)
    for x0, y0, x1, y1 in view_res["vis_segs"]:
        if axis_k == 0 and abs(x1 - x0) < 1e-3 and abs(y1 - y0) >= 1.2:
            out[round((x0 + x1) / 2, 2)] += abs(y1 - y0)
        elif axis_k == 1 and abs(y1 - y0) < 1e-3 and abs(x1 - x0) >= 1.2:
            out[round((y0 + y1) / 2, 2)] += abs(x1 - x0)
    return out


def merge_coords(dicts, lo, hi, tol=0.06):
    allc = collections.defaultdict(float)
    for d in dicts:
        for c, w in d.items():
            allc[c] += w
    cs = sorted(allc)
    groups = []
    for c in cs:
        if groups and c - groups[-1][-1] <= tol:
            groups[-1].append(c)
        else:
            groups.append([c])
    out = []
    for g in groups:
        w = sum(allc[c] for c in g)
        c = max(g, key=lambda q: allc[q])
        out.append((c, w))
    return out


def slanted(view_res, min_len=2.5):
    """straight visible runs that are neither horizontal nor vertical: [(angle 0..90 from the u axis, p0, p1, length)]."""
    out = []
    for pl in view_res["vis"]:
        P = pl["pts"]
        if len(P) < 2:
            continue
        for i in range(len(P) - 1):
            a, b = P[i], P[i + 1]
            d = b - a
            L = math.hypot(*d)
            if L < min_len:
                continue
            ang = math.degrees(math.atan2(abs(d[1]), abs(d[0])))
            if ang < 0.5 or ang > 89.5:
                continue
            # not a chord of an arc: the neighbours turn sharply (or the run ends)
            def turn(p, q, r):
                u, v = q - p, r - q
                lu, lv = math.hypot(*u), math.hypot(*v)
                if lu < 1e-9 or lv < 1e-9:
                    return 180.0
                c = max(-1.0, min(1.0, float(u @ v) / (lu * lv)))
                return math.degrees(math.acos(c))
            t0 = turn(P[i - 1], a, b) if i > 0 else 180.0
            t1 = turn(a, b, P[i + 2]) if i + 2 < len(P) else 180.0
            if pl["closed"] and i == 0 and len(P) > 2:
                t0 = turn(P[-2], a, b)
            if t0 < 8.0 or t1 < 8.0:
                continue
            out.append((ang, a, b, L))
    return out


def choose_sections(G, holes):
    """1 or 2 cutting planes: through the most hole / pocket centres, else through the middle of the longest side."""
    ext = G.ext
    cands = []
    real = [h for h in holes if not h.get("engr") and not h.get("frag")]
    for h in real:
        iu, iv = PLANE_AX[h["axis"]]
        for pi, c in ((iu, h["cu"]), (iv, h["cv"])):
            if 0.2 < c < ext[pi] - 0.2:
                cands.append((AX[pi], round(c, 2)))
    scored = []
    for (ax, c) in set(cands):
        pi = AX.index(ax)
        n = 0
        wsum = 0.0
        for h in real:
            iu, iv = PLANE_AX[h["axis"]]
            for q, cc in ((iu, h["cu"]), (iv, h["cv"])):
                if q == pi and abs(cc - c) < 0.06:
                    n += 1
                    wsum += (h["d"] or min(h["w"], h["h"])) * h["depth"]
        # prefer planes that show depth (hole axis in the plane) and that cut the part through its bulk
        scored.append((n, wsum, ax, c))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    out = []
    if scored:
        out.append((scored[0][2], scored[0][3]))
    # a second plane: perpendicular to the first through the most holes, else the long-side middle plane
    hor = sorted(((ext[0], "x"), (ext[1], "y")), reverse=True)
    long_ax = hor[0][1]
    mid = ("y" if long_ax == "x" else "x")
    # middle plane perpendicular to the short horizontal side shows the long profile
    mid_plane = (mid, round(ext[AX.index(mid)] / 2, 2))
    if not out:
        out.append(mid_plane)
    else:
        for n, w, ax, c in scored[1:]:
            if ax != out[0][0] and n >= 2:
                out.append((ax, c))
                break
        else:
            if out[0][0] != mid_plane[0]:
                out.append(mid_plane)
    res = []
    for ax, c in out[:2]:
        pl = slice_polys(G.D, ax, c)
        if not pl:
            continue
        allp = np.vstack(pl)
        mn = allp.min(0)
        res.append(dict(axis=ax, c=c, polys=[P - mn for P in pl], off=mn.tolist()))
    return res


def analyse(G):
    """everything measured for the sheet: views, holes, sections, walls / slots, slanted faces, ordinates."""
    t0 = time.time()
    A = dict(ext=G.ext.copy())
    A["views"] = {nm: G.view(nm) for nm in ("top", "front", "side")}
    hs = find_holes(G)
    for h in hs:
        h["engr"] = engraving(h, G, hs)
        h["frag"] = (not h["engr"]) and fragment(h)
    A["engr"] = [h for h in hs if h["engr"]]
    A["frag"] = [h for h in hs if h["frag"]]
    A["holes"] = sorted([h for h in hs if not h["engr"] and not h["frag"]],
                        key=lambda h: ({"straight": 0, "cone": 1, "slant": 2, "cavity": 3}.get(h.get("kind"), 0), {"round": 0, "tear": 1, "rect": 2, "other": 3}[h["shape"]],
                                       AX.index(h["axis"]), round(h["lo"], 1), round(h["cv"], 1), round(h["cu"], 1)))
    A["sections"] = choose_sections(G, hs)
    for s in A["sections"]:
        walls, gaps = facing_pairs(s["polys"])
        s["walls"] = summarize_widths(walls)
        s["gaps"] = summarize_widths(gaps)
        allp = np.vstack(s["polys"])
        s["size"] = tuple(float(v) for v in allp.max(0))
    ang = collections.OrderedDict()
    for nm, v in A["views"].items():
        for a, p, q, L in slanted(v):
            k = round(a, 1)
            if k not in ang or ang[k][3] < L:
                ang[k] = (nm, p, q, L)
    A["angles"] = ang
    A["t"] = time.time() - t0
    return A


# ------------------------------------------------------------------ sheet

SIZES = [("A3", 420.0, 297.0), ("A2", 594.0, 420.0), ("A1", 841.0, 594.0)]
SCALES = [10.0, 5.0, 2.0, 1.0, 0.5, 0.2]
TD, TL, TN, TS, TH = 2.5, 2.8, 2.4, 2.15, 3.6          # text: dims, labels, notes, table, headings (sheet mm)

PCSS = """
.pv{fill:none;stroke:#141a26;stroke-width:.35;stroke-linejoin:round;stroke-linecap:round}
.ph2{fill:none;stroke:#5b6578;stroke-width:.2;stroke-dasharray:1.4 .7}
.pcl{fill:none;stroke:#6b7690;stroke-width:.18;stroke-dasharray:5 1 1 1}
.pcut{fill:none;stroke:#1d2433;stroke-width:.5;stroke-dasharray:6 1.2 1.2 1.2}
.psec{fill:url(#hp);stroke:#141a26;stroke-width:.35;stroke-linejoin:round}
.pbed{fill:#f4f6f9;stroke:#8a96ab;stroke-width:.2}
.pfoot{fill:#dfe6ef;stroke:#39404d;stroke-width:.2}
.pnum{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace}
.datum{fill:none;stroke:#15803d;stroke-width:.9;stroke-linecap:round;stroke-opacity:.9}
.tg{fill:#15803d}
"""


def sc_txt(k):
    if k >= 1:
        return "%s:1" % fnum(k)
    return "1:%s" % fnum(1.0 / k)


class PSheet(DR.Sheet):
    def __init__(self, code, name, size):
        self.code, self.name = code, name
        self.size_name, self.w, self.h = size
        self.file = code
        self.scale_txt = ""
        self.L = {k: [] for k in DR.LAYERS}
        self.tboxes = []
        self.used = set()
        self.views = []
        self.defs = []

    def svg(self):
        W, H = self.w, self.h
        s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="0 0 %g %g">' % (W, H, W, H),
             "<title>Toccata %s %s</title>" % (self.code, esc(self.name)),
             "<defs><style>%s%s</style>%s%s</defs>" % (DR.CSS, PCSS, DR.DEFS, "".join(self.defs)),
             '<rect class="bg" x="0" y="0" width="%g" height="%g"/>' % (W, H),
             '<rect class="frame" x="10" y="10" width="%g" height="%g"/>' % (W - 20, H - 20)]
        for k in DR.LAYERS:
            if self.L[k]:
                s.append('<g id="%s">' % k)
                s.extend(self.L[k])
                s.append("</g>")
        s.append("</svg>")
        return "\n".join(s)


class VBox:
    """a view on the sheet: world (u, v) in [0, wu] x [0, wv] at scale k, top-left at sheet (X, Y)."""

    def __init__(self, k, wu, wv, X, Y):
        self.k, self.wu, self.wv, self.X, self.Y = k, wu, wv, X, Y
        self.w, self.h = k * wu, k * wv

    def P(self, u, v):
        return (self.X + self.k * u, self.Y + self.k * (self.wv - v))

    @property
    def rect(self):
        return (self.X, self.Y, self.X + self.w, self.Y + self.h)


def path_d(polys, vb):
    out = []
    for P in polys:
        q = [vb.P(u, v) for u, v in P]
        out.append("M" + " ".join("%.2f %.2f" % t for t in q))
    return "".join(out)


def emit_lines(sh, vb, res, layer="geo"):
    """visible + hidden lines of a view (circles / arcs as SVG primitives). Returns the DXF-ready curve lists."""
    curves = {"vis": as_curves(res["vis"]), "hid": as_curves(res["hid"])}
    for kind, cls in (("hid", "ph2"), ("vis", "pv")):
        polys = []
        for typ, g in curves[kind]:
            if typ == "circle":
                cx, cy, r = g
                x, y = vb.P(cx, cy)
                sh.add(layer, '<circle class="%s" cx="%.2f" cy="%.2f" r="%.3f"/>' % (cls, x, y, r * vb.k))
            elif typ == "arc":
                cx, cy, r, a0, a1, ccw, p0, p1 = g
                x0, y0 = vb.P(*p0)
                x1, y1 = vb.P(*p1)
                sweep = ((a1 - a0) if ccw else (a0 - a1)) % (2 * math.pi)
                large = 1 if sweep > math.pi else 0
                # world ccw = sheet cw (y flips): SVG sweep-flag 0
                sh.add(layer, '<path class="%s" d="M%.2f %.2f A%.3f %.3f 0 %d %d %.2f %.2f"/>'
                       % (cls, x0, y0, r * vb.k, r * vb.k, large, 0 if ccw else 1, x1, y1))
            else:
                polys.append(g)
        if polys:
            sh.add(layer, '<path class="%s" d="%s"/>' % (cls, path_d(polys, vb)))
    return curves


def _tbox(x, y, s, size, anchor):
    w = text_w(s, size)
    x0 = x if anchor == "start" else (x - w / 2 if anchor == "middle" else x - w)
    return (x0, y - 0.78 * size, x0 + w, y + 0.22 * size)


def collides(sh, box, pad=0.3):
    if box[0] < 10.5 or box[1] < 10.5 or box[2] > sh.w - 10.5 or box[3] > sh.h - 10.5:
        return True
    for (bb, _s) in sh.tboxes:
        if box[0] < bb[2] + pad and bb[0] < box[2] + pad and box[1] < bb[3] + pad and bb[1] < box[3] + pad:
            return True
    return False


def dim_across(sh, p, q, text, size=TD):
    """dimension across a wall / gap (sheet points p, q): line with outside arrows + text beside one end. Skipped (False)
    when the text would land on other text or off the sheet (the value stays in the notes)."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    for (e, s_) in ((q, 1), (p, -1)):
        vx, vy = ux * s_, uy * s_
        b = (e[0] + vx * 3.2, e[1] + vy * 3.2)
        tx, ty = b[0] + vx * 0.8, b[1] + vy * 0.8
        anchor = "start" if vx > 0.3 else ("end" if vx < -0.3 else "middle")
        ty = ty + (0.35 * size if abs(vy) < 0.7 else (size if vy > 0 else -0.4))
        box = _tbox(tx, ty, text, size, anchor)
        if collides(sh, box):
            continue
        a_ = (p[0] - ux * 3.2, p[1] - uy * 3.2)
        b_ = (q[0] + ux * 3.2, q[1] + uy * 3.2)
        sh.line([a_, b_], "dm", "dim")
        sh.arrow(p, a_, size=1.6)
        sh.arrow(q, b_, size=1.6)
        sh.text(tx, ty, text, size, anchor, cls="td")
        return True
    return False


def angle_mark(sh, vb, a, b, ang, size=TD):
    """angle of the straight edge a-b against the nearer view axis, arc at the lower / left end."""
    pa, pb = (a, b) if (a[1], a[0]) <= (b[1], b[0]) else (b, a)
    d = np.array(pb) - np.array(pa)
    ref_h = ang <= 45.0
    if ref_h:
        r_dir = np.array([1.0 if d[0] >= 0 else -1.0, 0.0])
        shown = ang
    else:
        r_dir = np.array([0.0, 1.0 if d[1] >= 0 else -1.0])
        shown = 90.0 - ang
    L = float(np.hypot(*d))
    R = min(9.0, max(4.0, 0.45 * L * vb.k))
    x, y = vb.P(*pa)
    a0 = math.atan2(-r_dir[1], r_dir[0])           # sheet angles (y down)
    a1 = math.atan2(-d[1], d[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    pts = [(x + R * math.cos(a0 + da * i / 16), y + R * math.sin(a0 + da * i / 16)) for i in range(17)]
    ref_end = (x + (R + 2.5) * math.cos(a0), y + (R + 2.5) * math.sin(a0))
    am = a0 + da / 2
    tx, ty = x + (R + 1.6) * math.cos(am), y + (R + 1.6) * math.sin(am)
    anchor = "start" if math.cos(am) > 0.2 else ("end" if math.cos(am) < -0.2 else "middle")
    lab = "%s°" % fnum(shown, 1)
    if collides(sh, _tbox(tx, ty + 0.35 * size, lab, size, anchor)):
        return None
    sh.line([(x, y), ref_end], "ex", "dim")
    sh.line(pts, "dm", "dim")
    sh.text(tx, ty + 0.35 * size, lab, size, anchor, cls="td")
    return shown


def pick_ordinates(cands, lo, hi, length_mm, k, size=TD, must=()):
    """[(coord, weight)] -> sorted coordinates to label: always the ends, then by weight while the labels fit."""
    nmax = min(42, max(2, int(length_mm / (size * 1.32))))
    ends = [c for c in must]
    rest = sorted([t for t in cands if all(abs(t[0] - e) > 0.05 for e in ends) and t[1] >= 1.5], key=lambda t: -t[1])
    chosen = list(ends)
    for c, w in rest:
        if len(chosen) >= nmax:
            break
        chosen.append(c)
    return sorted(chosen), max(0, len(rest) + len(ends) - len(chosen))


def hole_groups(holes):
    """identical holes (shape, size, axis, depth range, ends) -> groups, numbered H1.. in order."""
    groups = collections.OrderedDict()
    for h in holes:
        if h["shape"] in ("round", "tear"):
            key = (h.get("kind"), h["shape"], round(h["d"], 2), round(h.get("d_lo", 0), 2), h["axis"], round(h["lo"], 2), round(h["hi"], 2), tuple(h["ends"]))
        else:
            key = (h.get("kind"), h["shape"], round(h["w"], 2), round(h["h"], 2), h["axis"], round(h["lo"], 2), round(h["hi"], 2), tuple(h["ends"]))
        if h.get("kind") in ("slant", "cavity"):
            key = key + (round(h["cu"], 1), round(h["cv"], 1))
        # holes of one group must be the same void: islands inside (relative to the hole centre) are part of the key
        key = key + (tuple((round(a - h["cu"], 2), round(b - h["cu"], 2), round(c - h["cv"], 2), round(d - h["cv"], 2))
                           for a, b, c, d in h.get("isl", [])),)
        groups.setdefault(key, []).append(h)
    out = []
    for i, (key, hs) in enumerate(groups.items(), 1):
        out.append(dict(no="H%d" % i, holes=hs, h=hs[0]))
    return out


def _hnum(no):
    return int(no[1:])


def tag_label(members):
    """[(group, hole)] on one spot -> 'H1', 'H5 ×12', 'H1/H3', 'H4~H8', 'H2/H3 ×4' (same count), 'H2, H3 ×6' (mixed)."""
    cnt = collections.OrderedDict()
    for g, _h in members:
        cnt.setdefault(g["no"], len(g["holes"]))
    nos = sorted(cnt, key=_hnum)
    ns = [cnt[n] for n in nos]
    if len(nos) == 1:
        return nos[0] + (" ×%d" % ns[0] if ns[0] > 3 else "")
    many = [n for n in ns if n > 3]
    if many and len(set(ns)) > 1:
        return ", ".join(n + (" ×%d" % c if c > 3 else "") for n, c in zip(nos, ns))
    nums = [_hnum(n) for n in nos]
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j == i:
            parts.append("H%d" % nums[i])
        elif j == i + 1:
            parts.append("H%d/H%d" % (nums[i], nums[j]))
        else:
            parts.append("H%d~H%d" % (nums[i], nums[j]))
        i = j + 1
    return "/".join(parts) + (" ×%d" % ns[0] if many else "")


def tag_clusters(groups, tol=0.3):
    """the hole tags of a sheet: one per hole (only the first hole when a group has more than 3). Holes on one axis line
    in the same view (counterbore, cone + bore, one bore cut into depth pieces: centres within `tol` mm) share ONE tag,
    e.g. 'H1/H3', so labels never sit on top of each other."""
    req = []
    for g in groups:
        hs = g["holes"]
        for h in (hs if len(hs) <= 3 else hs[:1]):
            req.append((g, h))
    out = []
    for g, h in req:
        nm = AXIS_VIEW[h["axis"]]
        for c in out:
            if c["view"] == nm and math.hypot(c["cu"] - h["cu"], c["cv"] - h["cv"]) <= tol:
                if all(gg["no"] != g["no"] for gg, _ in c["members"]):
                    c["members"].append((g, h))
                break
        else:
            out.append(dict(view=nm, cu=h["cu"], cv=h["cv"], members=[(g, h)]))
    for c in out:
        c["label"] = tag_label(c["members"])
    return out


def place_text(sh, cands, s, size, xmax=None, bold=False, cls="", halo=True):
    """first candidate (x, y, anchor[, leader pts]) whose text box is free -> drawn + registered. When none is free the
    first candidate is used (and the layout check reports it). Returns the index used (-1 = forced)."""
    for i, c in enumerate(cands):
        x, y, anc = c[:3]
        box = _tbox(x, y, s, size, anc)
        if xmax is not None and box[2] > xmax:
            continue
        if collides(sh, box):
            continue
        if len(c) > 3 and c[3]:
            sh.line(c[3], "ld", "lead")
        sh.text(x, y, s, size, anc, cls=cls, bold=bold, halo=halo)
        return i
    x, y, anc = cands[0][:3]
    sh.text(x, y, s, size, anc, cls=cls, bold=bold, halo=halo)
    return -1


def tag_cands(sh, vb, c, size):
    """candidate spots for a hole tag around its outline (sheet coords): the 4 diagonal corners, the 4 sides, inside a
    big opening, then on a short leader further out."""
    k = vb.k
    hs = [h for _g, h in c["members"]]
    rnd = [h for h in hs if h["shape"] in ("round", "tear") and h.get("d") and h["d"] <= 1.1 * max(h["w"], h["h"])]
    out = []
    lab_w = text_w(c["label"], size)
    if rnd and len(rnd) == len(hs):
        r = max(h["d"] for h in rnd) / 2 * k
        x, y = vb.P(c["cu"], c["cv"])
        dirs = [45, 135, -45, -135, 0, 180, 90, -90]
        for extra in (0.0, 3.5, 7.0):
            for a in dirs:
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                if extra == 0.0 and a == 45:
                    px, py = x + r * 0.72 + 0.6, y - r * 0.72 - 0.6        # the classic spot (upper right)
                else:
                    px, py = x + (r + 0.6 + extra) * ca, y - (r + 0.6 + extra) * sa
                anc = "start" if ca > 0.3 else ("end" if ca < -0.3 else "middle")
                by = py if sa > 0.3 else (py + 0.78 * size if sa < -0.3 else py + 0.3 * size)
                lead = None
                if extra:
                    lead = [(x + r * ca, y - r * sa), (px - 0.4 * ca, py + 0.4 * sa)]
                out.append((px, by, anc, lead))
        return out
    # outline box of the biggest member
    u0 = min(h["u0"] for h in hs)
    u1 = max(h["u1"] for h in hs)
    v0 = min(h["v0"] for h in hs)
    v1 = max(h["v1"] for h in hs)
    X0, Y0 = vb.P(u0, v1)          # top-left on the sheet
    X1, Y1 = vb.P(u1, v0)          # bottom-right
    out += [(X1 + 0.6, Y0 - 0.6, "start", None), (X0 - 0.6, Y0 - 0.6, "end", None),
            (X1 + 0.6, Y1 + 0.6 + 0.78 * size, "start", None), (X0 - 0.6, Y1 + 0.6 + 0.78 * size, "end", None)]
    if X1 - X0 > lab_w + 2.0 and Y1 - Y0 > size + 2.0:
        out += [(X0 + 0.8, Y0 + 0.8 + 0.78 * size, "start", None), (X1 - 0.8, Y0 + 0.8 + 0.78 * size, "end", None),
                (X0 + 0.8, Y1 - 0.8, "start", None), (X1 - 0.8, Y1 - 0.8, "end", None)]
    out += [(X1 + 0.6, (Y0 + Y1) / 2 + 0.3 * size, "start", None), (X0 - 0.6, (Y0 + Y1) / 2 + 0.3 * size, "end", None)]
    for extra in (3.5, 7.0):
        for (cx_, cy_, sx, sy) in ((X1, Y0, 1, -1), (X0, Y0, -1, -1), (X1, Y1, 1, 1), (X0, Y1, -1, 1)):
            px, py = cx_ + sx * extra * 0.7, cy_ + sy * extra * 0.7
            anc = "start" if sx > 0 else "end"
            by = py if sy < 0 else py + 0.78 * size
            out.append((px, by, anc, [(cx_, cy_), (px - 0.3 * sx, py - 0.3 * sy)]))
    return out


def size_txt(h):
    return _size_txt(h) + (" +섬" if h.get("isl") else "")


def isl_txt(h):
    """'안에 섬 20.4×18 (x 37.1~57.5 · y 3.55~21.55)' for each solid island standing in the void (mid depth)."""
    iu, iv = PLANE_AX[h["axis"]]
    return " · ".join("섬 %s×%s (%s %s~%s, %s %s~%s)" % (fnum(b - a, 2), fnum(d - c, 2), AX[iu], fnum(a, 2), fnum(b, 2), AX[iv], fnum(c, 2), fnum(d, 2))
                      for a, b, c, d in h.get("isl", []))


def _size_txt(h):
    if h.get("kind") == "cone":
        return "원뿔 Ø%s→Ø%s" % (fnum(h["d_lo"], 2), fnum(h["d_hi"], 2))
    if h.get("kind") == "cavity":
        return "빈 곳 %s×%s" % (fnum(h["w"], 2), fnum(h["h"], 2))
    if h.get("kind") == "slant":
        base = ("Ø%s" % fnum(h["d"], 2)) if h["shape"] in ("round", "tear") else ("%s×%s" % (fnum(h["w"], 2), fnum(h["h"], 2)))
        return "비스듬 " + base
    if h["shape"] == "round":
        return "Ø%s" % fnum(h["d"], 2)
    if h["shape"] == "tear":
        return "Ø%s 눈물방울" % fnum(h["d"], 2)
    if h["shape"] == "rect":
        return "사각 %s×%s" % (fnum(h["w"], 2), fnum(h["h"], 2))
    return "모양 %s×%s" % (fnum(h["w"], 2), fnum(h["h"], 2))


def depth_txt(h, ext):
    a = h["axis"]
    lo, hi = h["lo"], h["hi"]
    e0, e1 = h["ends"]
    rng = "%s %s~%s" % (a, fnum(lo, 2), fnum(hi, 2))
    if e0 == "open" and e1 == "open":
        thru = lo < 0.02 and hi > ext[AX.index(a)] - 0.02
        return rng + (" 관통" if thru else " 열림")
    if e0 == "closed" and e1 == "closed":
        return rng + " 속 빈 곳"
    face = ("+" if e1 == "open" else "-") + a
    return "%s 면에서 %s 막힘" % (face, fnum(hi - lo, 2)) + " (%s)" % rng


def uv_txt(h):
    iu, iv = PLANE_AX[h["axis"]]
    if h.get("kind") == "slant":
        return "%s %s→%s · %s %s→%s" % (AX[iu], fnum(h["cu"], 1), fnum(h["cu1"], 1), AX[iv], fnum(h["cv"], 1), fnum(h["cv1"], 1))
    return "%s %s · %s %s" % (AX[iu], fnum(h["cu"], 2), AX[iv], fnum(h["cv"], 2))


def entry_point(h):
    """drawing-coords point on the hole axis at its open end (lo when both / none are open)."""
    e0, e1 = h["ends"]
    return hole_point(h, "hi" if (e1 == "open" and e0 != "open") else "lo")


def world_of(ctx_map, p):
    if ctx_map is None:
        return None
    M = ctx_map["W"]
    return M[:, :3] @ p + M[:, 3]


def wtxt(w):
    return "—" if w is None else "%s, %s, %s" % (fnum(w[0], 2), fnum(w[1], 2), fnum(w[2], 2))


def bed_sketch(sh, x, y, w, Mp, face_txt, size=TS):
    """print orientation: the STL footprint on the build plate + its side profile."""
    bx = 34.0
    k = bx / max(BED)
    sh.rect(x, y, x + bx, y + bx, "pbed", "over")
    b = Mp.bounding_box()
    fp = DR.proj(Mp, "z")
    ox = x + (bx - (b[3] - b[0]) * k) / 2 - b[0] * k
    oy = y + (bx + (b[4] - b[1]) * k) / 2 + b[1] * k
    d = []
    for P in fp.to_polygons():
        P = np.asarray(P, float)
        d.append("M" + " ".join("%.2f %.2f" % (ox + u * k, oy - v * k) for u, v in P) + "Z")
    sh.add("over", '<path class="pfoot" fill-rule="evenodd" d="%s"/>' % "".join(d))
    sh.text(x + bx / 2, y + bx + 3.2, "베드 %s × %s (위에서)" % (fnum(BED[0]), fnum(BED[1])), size - 0.2, "middle", halo=False)
    # side profile (seen from the front of the printer)
    px0 = x + bx + 6
    pw = w - bx - 6
    ext = (b[3] - b[0], b[5] - b[2])
    kk = min(pw / max(ext[0], 1e-6), 24.0 / max(ext[1], 1e-6))
    pr = DR.proj(Mp, "y")
    base_y = y + 28.0
    d = []
    for P in pr.to_polygons():
        P = np.asarray(P, float)
        d.append("M" + " ".join("%.2f %.2f" % (px0 + (u - b[0]) * kk, base_y - (v - b[2]) * kk) for u, v in P) + "Z")
    sh.add("over", '<path class="pfoot" fill-rule="evenodd" d="%s"/>' % "".join(d))
    sh.line([(px0 - 2, base_y + 0.4), (px0 + ext[0] * kk + 2, base_y + 0.4)], "vis", "over")
    sh.text(px0, base_y + 3.6, "옆에서 (%s) · 출력 높이 %s" % (("1:%s" % fnum(1 / kk, 1)) if kk < 1 else ("%s:1" % fnum(kk, 1)), fnum(ext[1], 2)), size - 0.2, halo=False)
    lines = sh.wrap(face_txt, w, size)
    yy = y + bx + 7.0
    for ln in lines:
        sh.text(x, yy, ln, size, halo=False)
        yy += size * 1.38
    return yy


def title_block(sh, x0, y0, W, it, scale_txt, note_lines):
    """bottom of the right column. Returns the top y used (block is drawn downward from y0)."""
    r = it["row"] if it["kind"] == "print" else None
    H = 11 + 8 + 7 + 7 + 8 + 3.2 + len(note_lines) * 2.9 + 2.5 + 6
    y0 = sh.h - 10 - H
    sh.rect(x0, y0, x0 + W, y0 + H, "grid", "over")
    yy = y0
    sh.text(x0 + 2.5, yy + 7.6, "Toccata 부품도", 4.6, bold=True, halo=False)
    sh.text(x0 + W - 2.5, yy + 8.0, it["code"], 5.4, "end", bold=True, halo=False)
    yy += 11
    sh.line([(x0, yy), (x0 + W, yy)], "grid", "over")
    nm = it["name_ko"]
    sh.text(x0 + 2.5, yy + 5.6, nm, 3.6 if text_w(nm, 3.6) < W - 6 else 2.8, bold=True, halo=False)
    yy += 8
    sh.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
    cols = [("척도", scale_txt), ("단위", "mm"), ("용지", sh.size_name), ("날짜", DATE)]
    cw = W / len(cols)
    for i, (a, b) in enumerate(cols):
        sh.text(x0 + 2 + i * cw, yy + 2.6, a, 1.9, cls="tm", halo=False)
        sh.text(x0 + 2 + i * cw, yy + 6.0, b, 2.4, halo=False)
        if i:
            sh.line([(x0 + i * cw, yy), (x0 + i * cw, yy + 7)], "grid2", "over")
    yy += 7
    sh.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
    cols = [("수량 (악기 1대)", it["qty_txt"]), ("재료·색", it["material"]), ("부피" if it["kind"] == "ply" else "질량 (속 100 %)", it["mass_txt"])]
    cws = [W * 0.28, W * 0.40, W * 0.32]
    xx = x0
    for (a, b), c in zip(cols, cws):
        sh.text(xx + 2, yy + 2.6, a, 1.9, cls="tm", halo=False)
        sh.text(xx + 2, yy + 6.0, b, 2.4 if text_w(b, 2.4) < c - 3 else 1.9, halo=False)
        if xx > x0:
            sh.line([(xx, yy), (xx, yy + 7)], "grid2", "over")
        xx += c
    yy += 7
    sh.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
    sh.text(x0 + 2, yy + 2.6, "파일", 1.9, cls="tm", halo=False)
    sh.text(x0 + 10, yy + 2.8, it["file_disp"], 2.0 if text_w(it["file_disp"], 2.0) < W - 12 else 1.6, halo=False, check=False)
    sh.text(x0 + 10, yy + 6.3, it.get("file2", ""), 1.8, cls="tm", halo=False, check=False)
    yy += 8
    sh.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
    sh.text(x0 + 2, yy + 2.8, "가공 메모" if it["kind"] == "ply" else "출력·가공 메모", 1.9, cls="tm", halo=False)
    yy += 3.2
    for ln in note_lines:
        yy += 2.9
        sh.text(x0 + 2, yy, ln, 2.1, halo=False)
    yy += 2.5
    sh.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
    sh.text(x0 + 2, yy + 4.2, "모든 선과 숫자는 출력 파일의 입체에서 잼 (src/part_sheets.py) · 3각법", 1.9, cls="tm", halo=False)
    return y0


# ------------------------------------------------------------------ layout

COLW = {"A3": 150.0, "A2": 175.0, "A1": 190.0, "A0": 210.0}
BAND = 7.0 + 9.5          # ordinate band (tick + label "000.00")


def _place_sections(secs, rects, k):
    """shelf packing of the section blocks into the free rectangles; returns [(sec, ks, X, Y)] or None."""
    out = []
    cur = [dict(r=r, x=r[0], y=r[1], rowh=0.0) for r in rects]
    for s in secs:
        a, b = s["size"]
        done = False
        for ks in [q for q in SCALES if k < q <= 5 * k and max(a, b) * q <= 70] + [q for q in SCALES if q <= k][:3]:
            bw, bh = max(a * ks + 18.0, 70.0), b * ks + 22.0
            for c in cur:
                x0, y0, x1, y1 = c["r"]
                if x1 - x0 < bw or y1 - y0 < bh:
                    continue
                x, y = c["x"], c["y"]
                if x + bw > x1:
                    x, y = x0, y + c["rowh"] + 2.0
                    c["rowh"] = 0.0
                if y + bh > y1 or x + bw > x1:
                    continue
                out.append((s, ks, x, y))
                c["x"], c["y"] = x + bw + 2.0, y
                c["rowh"] = max(c["rowh"], bh)
                done = True
                break
            if done:
                break
        if not done:
            return None
    return out


def plan(A, size, k_max=10.0):
    name, W, H = size
    Cw = COLW[name]
    vx0, vy0 = 12.0, 12.0
    vx1, vy1 = W - 10.0 - Cw - 6.0, H - 12.0
    X, Y, Z = A["ext"]
    secs = A["sections"]
    for drop in (0, 1, 2):
        use = secs[:len(secs) - drop] if drop else secs
        if drop and not secs:
            break
        for k in [q for q in SCALES if q <= k_max]:
            wid = BAND + X * k + 14 + Y * k + 12
            hei = BAND + Y * k + 10 + Z * k + 17
            if wid > vx1 - vx0 or hei > vy1 - vy0:
                continue
            XT, YT = vx0 + BAND, vy0 + BAND
            YF = YT + Y * k + 10
            XS = XT + X * k + 14
            rects = [(XT + X * k + 16, vy0, vx1, YF - 5), (XS + Y * k + 12, YF - 2, vx1, vy1),
                     (vx0, YF + Z * k + 19, vx1, vy1)]
            pl = _place_sections(use, rects, k)
            if pl is None:
                continue
            return dict(size=size, k=k, XT=XT, YT=YT, YF=YF, XS=XS, secs=pl, Cw=Cw, vx1=vx1, dropped=drop)
    return None


SEC_LET = "ABCDEFG"


def draw_views(sh, L, A, ctx_map, it):
    """the three views + ordinates + overall dims + hole labels + angles + section lines and blocks. Returns DXF data."""
    k = L["k"]
    X, Y, Z = A["ext"]
    V = A["views"]
    vbT = VBox(k, X, Y, L["XT"], L["YT"])
    vbF = VBox(k, X, Z, L["XT"], L["YF"])
    vbS = VBox(k, Y, Z, L["XS"], L["YF"])
    boxes = {"top": vbT, "front": vbF, "side": vbS}
    dx = {"views": {}, "secs": [], "ords": {}, "dims": []}
    for nm, vb in boxes.items():
        dx["views"][nm] = emit_lines(sh, vb, V[nm])
    # titles
    sh.text(vbT.X, vbT.Y + vbT.h + 6.2, VIEW_KO["top"], TL, bold=True)
    sh.text(vbF.X, vbF.Y + vbF.h + 13.2, VIEW_KO["front"], TL, bold=True)
    sh.text(vbS.X, vbS.Y + vbS.h + 13.2, VIEW_KO["side"], TL, bold=True)
    # overall dims
    sh.dim_h(vbF.X, vbF.X + vbF.w, vbF.Y + vbF.h + 6.0, fnum(X, 2), ext=[(vbF.X, vbF.Y + vbF.h), (vbF.X + vbF.w, vbF.Y + vbF.h)], size=TD)
    sh.dim_v(vbT.Y, vbT.Y + vbT.h, vbT.X + vbT.w + 6.0, fnum(Y, 2), ext=[(vbT.X + vbT.w, vbT.Y), (vbT.X + vbT.w, vbT.Y + vbT.h)], size=TD)
    sh.dim_h(vbS.X, vbS.X + vbS.w, vbS.Y + vbS.h + 6.0, fnum(Y, 2), ext=[(vbS.X, vbS.Y + vbS.h), (vbS.X + vbS.w, vbS.Y + vbS.h)], size=TD)
    sh.dim_v(vbS.Y, vbS.Y + vbS.h, vbS.X + vbS.w + 6.0, fnum(Z, 2), ext=[(vbS.X + vbS.w, vbS.Y), (vbS.X + vbS.w, vbS.Y + vbS.h)], size=TD)
    dx["dims"] = [("x", X), ("y", Y), ("z", Z)]
    # ordinates
    cx = merge_coords([ordinate_candidates(V["top"], 0, 0, X), ordinate_candidates(V["front"], 0, 0, X)], 0, X)
    cy = merge_coords([ordinate_candidates(V["top"], 1, 0, Y), ordinate_candidates(V["side"], 0, 0, Y)], 0, Y)
    cz = merge_coords([ordinate_candidates(V["front"], 1, 0, Z), ordinate_candidates(V["side"], 1, 0, Z)], 0, Z)
    ox, mx = pick_ordinates(cx, 0, X, vbT.w + 10, k, must=(0.0, round(X, 2)))
    oy, my = pick_ordinates(cy, 0, Y, vbT.h + 7, k, must=(0.0, round(Y, 2)))
    oz, mz = pick_ordinates(cz, 0, Z, vbF.h + 6, k, must=(0.0, round(Z, 2)))
    sh.ordinates_h([(vbT.P(c, 0)[0], None, fnum(c, 2)) for c in ox], vbT.Y - 1.0, -1, size=TD, lo=vbT.X - 6, hi=vbT.X + vbT.w + 4)
    sh.ordinates_v([(vbT.P(0, c)[1], None, fnum(c, 2)) for c in oy], vbT.X - 1.0, -1, size=TD, lo=vbT.Y - 4, hi=vbT.Y + vbT.h + 3.2)
    sh.ordinates_v([(vbF.P(0, c)[1], None, fnum(c, 2)) for c in oz], vbF.X - 1.0, -1, size=TD, lo=vbF.Y - 3.2, hi=vbF.Y + vbF.h + 3)
    sh.text(vbT.X + vbT.w + 1.5, vbT.Y - BAND + 2.0, "x 좌표", TS, cls="tm", halo=False)
    # every candidate edge coordinate (the sheet shows what fits; the rest goes to the DXF layer DIM_MORE + coordinate CSV)
    printed = {"x": ox, "y": oy, "z": oz}
    allc = {}
    for a_, cands, ext_ in (("x", cx, X), ("y", cy, Y), ("z", cz, Z)):
        lst = [(round(float(c), 2) + 0.0, round(float(w), 2)) for c, w in cands]          # + 0.0: no '-0.00'
        for e_ in (0.0, round(ext_, 2)):
            if all(abs(c - e_) > 0.05 for c, _ in lst):
                lst.append((e_, 0.0))
        allc[a_] = sorted((c, w, any(abs(c - p) <= 0.05 for p in printed[a_])) for c, w in lst)
    n_all = sum(len(v) for v in allc.values())
    n_on = sum(1 for v in allc.values() for t in v if t[2])
    dx["ords"] = {"x": ox, "y": oy, "z": oz, "missing": n_all - n_on}
    dx["ords_all"] = allc
    if n_all > n_on:
        it["ord_note"] = ("모서리 좌표 %d개는 시트에서 생략 (시트 %d개 · 전부 %d개) — 전부 좌표 CSV (_좌표.csv)와 DXF 레이어 DIM_MORE에 있음"
                          % (n_all - n_on, n_on, n_all))
    else:
        it["ord_note"] = "모서리 좌표 %d개 전부 시트에 있음 (좌표 CSV · DXF에도 같음)" % n_all
    # angles first (max 3 per view, longest edge of each angle): a mark has one spot, a tag has many
    nang = collections.Counter()
    for a_, (nm, p, q, Ln) in sorted(A["angles"].items(), key=lambda t: -t[1][3]):
        if nang[nm] >= 3 or Ln * k < 4.0:
            continue
        if angle_mark(sh, boxes[nm], p, q, a_) is not None:
            nang[nm] += 1
    # hole tags (view along the hole axis): holes on one axis line share one tag; each tag goes to the first free spot
    # around its hole (registered, so the layout check sees them)
    forced = 0
    for c in A["tag_clusters"]:
        vb = boxes[c["view"]]
        if place_text(sh, tag_cands(sh, vb, c, TS), c["label"], TS, xmax=L["vx1"], cls="tr") < 0:
            forced += 1
    dx["tags_forced"] = forced
    # section lines in the views + section blocks
    for i, (s, ks, bx, by) in enumerate(L["secs"]):
        let = SEC_LET[i]
        s["let"] = let
        ax, c = s["axis"], s["c"]
        if ax == "x":
            vb, horiz = vbT, False
        elif ax == "y":
            vb, horiz = vbT, True
        else:
            vb, horiz = vbF, True
        if horiz:
            p0, p1 = vb.P(0, c), vb.P(vb.wu, c)
            a_ = (p0[0] - 4, p0[1])
            b_ = (p1[0] + 4, p1[1])
            # viewing direction: y section seen from the front (-y -> +y): arrows point up the sheet (+v); z: down (-v)
            sg = -1 if ax == "y" else 1
            arr = [((a_[0] + 1.5, a_[1]), (a_[0] + 1.5, a_[1] + sg * 3.5)), ((b_[0] - 1.5, b_[1]), (b_[0] - 1.5, b_[1] + sg * 3.5))]
        else:
            p0, p1 = vb.P(c, 0), vb.P(c, vb.wv)
            a_ = (p0[0], p0[1] + 4)
            b_ = (p1[0], p1[1] - 4)
            arr = [((a_[0], a_[1] - 1.5), (a_[0] - 3.5, a_[1] - 1.5)), ((b_[0], b_[1] + 1.5), (b_[0] - 3.5, b_[1] + 1.5))]
        sh.line([a_, b_], "pcut", "over")
        for (frm, tip) in arr:
            sh.line([frm, tip], "secl", "over")
            sh.arrow(tip, frm, size=1.6, layer="over", cls="seca")
        for (frm, tip) in arr:
            # the letter beside its arrow tip: first free spot (registered, so dimensions / tags placed later avoid it)
            if horiz:
                sg_ = 1 if tip[1] > frm[1] else -1
                cands = [(tip[0] + 1.2, tip[1] + 0.9, "start"), (tip[0] - 1.2, tip[1] + 0.9, "end"),
                         (tip[0] + 1.2, tip[1] + sg_ * 2.6 + 0.9, "start"), (tip[0] - 1.2, tip[1] + sg_ * 2.6 + 0.9, "end"),
                         (tip[0], tip[1] + (0.78 * TL + 1.0 if sg_ > 0 else -1.0), "middle")]
            else:
                sg_ = 1 if tip[0] > frm[0] else -1
                cands = [(tip[0] - 1.0, tip[1] - 1.0, "end"), (tip[0] - 1.0, tip[1] + 0.78 * TL + 1.0, "end"),
                         (tip[0] + 1.0, tip[1] - 1.0, "start"), (tip[0] + 1.0, tip[1] + 0.78 * TL + 1.0, "start"),
                         (tip[0] + sg_ * 2.0, tip[1] + 0.3 * TL, "start" if sg_ > 0 else "end")]
            place_text(sh, cands, let, TL, xmax=L["vx1"] + 2.0, bold=True)
        # block
        a, b = s["size"]
        vbs = VBox(ks, a, b, bx + 8.0, by + 8.0)
        d = []
        for P in s["polys"]:
            d.append("M" + " ".join("%.2f %.2f" % vbs.P(u, v) for u, v in P) + "Z")
        sh.add("geo", '<path class="psec" fill-rule="evenodd" d="%s"/>' % "".join(d))
        lab = "%s-%s 단면 (%s = %s)%s" % (let, let, ax, fnum(c, 2), "" if ks == k else "  %s" % sc_txt(ks))
        y_lab = vbs.Y + vbs.h + 6.5
        # reserve the label line, then the walls / gaps (two most common of each) where their text fits
        sh.tboxes.append(((vbs.X, y_lab - 0.78 * TL, vbs.X + text_w(lab, TL), y_lab + 3.8), "_reserve"))
        for kind, lst in (("wall", s["walls"][:2]), ("gap", s["gaps"][:2])):
            for w_, wt, (p_, q_) in lst:
                if w_ * ks < 0.4:
                    continue
                dim_across(sh, vbs.P(*p_), vbs.P(*q_), fnum(w_, 2), size=TS)
        sh.tboxes = [t for t in sh.tboxes if t[1] != "_reserve"]
        sh.text(vbs.X, y_lab, lab, TL, bold=True)
        iu, iv = PLANE_AX[ax]
        sh.text(vbs.X, y_lab + 3.5, "그림 왼쪽 아래 = %s %s · %s %s (부품 기준)" % (AX[iu], fnum(s["off"][0], 2), AX[iv], fnum(s["off"][1], 2)),
                TS - 0.2, cls="tm")
        dx["secs"].append(dict(let=let, axis=ax, c=c, ks=ks, polys=s["polys"], size=(a, b), off=s["off"]))
    return dx, boxes


def column_content(sh, x, y, W, it, A, ctx_map, dry=False):
    """right column: info, print orientation, hole table, notes. Returns the bottom y."""
    if dry:
        sh = _DrySheet(sh)
    yy = y + 4.0
    sh.text(x, yy, it["name_ko"], 4.0, bold=True, halo=False)
    yy += 5.0
    ply = it["kind"] == "ply"
    info = ["%s · %s" % (it["code"], FOLDER_KO[it["group"]]),
            "크기 (도면 자세) %s × %s × %s" % tuple(fnum(v, 2) for v in A["ext"]),
            ("재단 직사각형 %s × %s, 두께 %s" % (fnum(it["fp"]["W"], 2), fnum(it["fp"]["H"], 2), fnum(it["fp"]["T"], 2))) if ply else
            ("출력 파일 크기 %s × %s × %s (STL 그대로)" % tuple(fnum(v, 2) for v in it["print_ext"]))]
    for ln in info:
        sh.text(x, yy, ln, TN, halo=False)
        yy += TN * 1.4
    yy += 1.5
    if ply:
        for ln in sh.wrap(it["face_txt"], W - 2, TS):
            sh.text(x, yy, ln, TS, halo=False)
            yy += TS * 1.38
        yy += 1.0
    else:
        sh.text(x, yy, "출력 자세", TN + 0.4, bold=True, halo=False)
        yy += 2.0
        yy = bed_sketch(sh, x, yy, W, it["Mp"], it["face_txt"], size=TS) + 2.0
    # hole table
    groups = A["groups"]
    rows = []
    for g in groups:
        hs = g["holes"]
        h = hs[0]
        for j, hh in enumerate(hs if len(hs) <= 4 else hs[:1]):
            w = world_of(ctx_map, entry_point(hh))
            rows.append([g["no"] if j == 0 else "", size_txt(hh) if j == 0 else "", depth_txt(hh, A["ext"]) if j == 0 else "",
                         str(len(hs)) if j == 0 else "", uv_txt(hh), wtxt(w)])
        if len(hs) > 4:
            rows.append(["", "", "", "", "나머지 %d개: 아래 배치" % (len(hs) - 1), ""])
    yy += 2.0
    if rows:
        sh.text(x, yy, "구멍·포켓 (부품 기준 = 도면 자세의 최소 모서리 0,0,0)", TN + 0.3, bold=True, halo=False)
        yy += 1.5
        cols = [("번호", 8.0, "start"), ("모양·크기", 22.0, "start"), ("방향·깊이", 34.0, "start"), ("개", 5.0, "middle"),
                ("중심 (부품 기준)", 34.0, "start"), ("월드 (입구 중심)", W - 103.0, "start")]
        maxrows = int((sh.h - 10 - 60 - yy) / 3.3) if not dry else 999
        if len(rows) > maxrows > 4:
            cut = len(rows) - maxrows + 1
            rows = rows[:maxrows - 1] + [["", "", "", "", "… %d줄 더: holes.csv · DXF" % cut, ""]]
            it["table_cut"] = cut
        yy = sh.table(x, yy, cols, rows, size=TS - 0.15, rh=3.3) + 3.0
    else:
        sh.text(x, yy, "구멍·포켓: 없음 (x·y·z 모든 꼭짓점 평면 사이를 잘라 봄: 닫힌 안쪽 윤곽 없음)", TN, halo=False)
        yy += 4.0
    # notes
    notes = list(it["notes_extra_pre"])
    # the edge-coordinate line is only known after the views are drawn: the dry run reserves a line of the longest form
    notes.append(it.get("ord_note") or "모서리 좌표 000개는 시트에서 생략 (시트 000개 · 전부 000개) — 전부 좌표 CSV (_좌표.csv)와 DXF 레이어 DIM_MORE에 있음")
    shared = [c["label"] for c in A.get("tag_clusters", []) if len(c["members"]) > 1]
    if shared:
        notes.append("한 꼬리표 = 같은 축 위에 겹친 구멍 (계단·원뿔+구멍·깊이 구간; 표에는 따로): " + " · ".join(shared))
    for g in groups:
        if len(g["holes"]) > 4:
            for t in pattern_text2([dict(hh, d=hh["d"] or 0, round=hh["shape"] == "round") for hh in g["holes"]]):
                notes.append("%s 배치 (%s면): %s" % (g["no"], {"x": "y·z", "y": "x·z", "z": "x·y"}[g["h"]["axis"]], t))
    for g in groups:
        if g["h"].get("isl"):
            notes.append("%s 안에 서 있는 섬 (빈 곳 가운데 깊이에서 잼, 부품 기준): %s" % (g["no"], isl_txt(g["h"])))
    for s in A["sections"]:
        if "let" not in s:
            continue
        if s["walls"]:
            notes.append("%s-%s 단면 벽 두께: %s" % (s["let"], s["let"], " · ".join(fnum(w, 2) for w, _, _ in s["walls"][:5])))
        if s["gaps"]:
            notes.append("%s-%s 단면 홈·틈 폭: %s" % (s["let"], s["let"], " · ".join(fnum(w, 2) for w, _, _ in s["gaps"][:5])))
    if A["angles"]:
        notes.append("경사면 (뷰 축에서 잰 각): " + " · ".join("%s° (%s)" % (fnum(a_ if a_ <= 45 else 90 - a_, 1), VIEW_KO[v[0]].split(" ")[0])
                                                    for a_, v in list(A["angles"].items())[:8]))
    if A["engr"]:
        e = A["engr"]
        notes.append("새김 글자 (깊이 %s, %s 방향 면에 새김) %d곳 — 구멍 번호를 매기지 않음" % ("·".join(sorted(set(fnum(h["depth"], 2) for h in e))),
                                                                "·".join(sorted(set(h["axis"] for h in e))), len(e)))
    if A.get("frag"):
        f_ = A["frag"]
        notes.append("짧은 경사 조각 %d곳 (깊이 %s~%s, 다른 곳으로 열리는 빈 곳의 끝·가는 틈) — 표에서 뺌, 모양은 그림과 단면에 있음"
                     % (len(f_), fnum(min(h["depth"] for h in f_), 2), fnum(max(h["depth"] for h in f_), 2)))
    notes += it["notes_extra"]
    yy += 1.0
    sh.text(x, yy, "치수 메모", TN + 0.3, bold=True, halo=False)
    yy += 0.5
    for ln in notes:
        for i, wl in enumerate(sh.wrap(ln, W - 3, TN - 0.1)):
            yy += (TN - 0.1) * 1.38
            sh.text(x + (0 if i == 0 else 2.5), yy, ("· " if i == 0 else "") + wl, TN - 0.1, halo=False)
    return yy + 2.0


class _DrySheet:
    """measures the column without drawing (same wrap / table maths)."""

    def __init__(self, sh):
        self.h, self.w = sh.h, sh.w
        self._sh = sh

    def text(self, *a, **k):
        return None

    def wrap(self, s, w, size):
        return self._sh.wrap(s, w, size)

    def table(self, x, y, cols, rows, size=TS, rh=3.3, head=True):
        return y + (len(rows) + 1) * rh

    def rect(self, *a, **k):
        pass

    def line(self, *a, **k):
        pass

    def add(self, *a, **k):
        pass


# ------------------------------------------------------------------ one print item

AXN = {0: "x", 1: "y", 2: "z"}


class Ctx:
    def __init__(self, parts=None):
        import build_all
        self.parts = parts if parts is not None else build_all.collect()
        self.man = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
        self.by_file = collections.defaultdict(list)
        pf = {p["id"]: p["print_file"] for p in self.man["parts"]}
        for p in self.parts:
            f = pf.get(p.id)
            if f and p.kind == "print":
                self.by_file[f].append(p)
        self.maps = {}


def counterpart_file(r):
    f = r["folder"]
    if f == "@extra/예비_건반":
        return "stl/print/01_건반/" + os.path.basename(r["file"]).split("__")[0] + "__"
    if f == "@extra/대안_패드바_PORON6T용":
        return "stl/print/04_센서바·패드바·가림판·마개/" + r["name"].replace("_PORON6T용", "") + "__"
    return None


def prepare_print(it, ctx):
    r = it["row"]
    it["name_ko"] = r["name_ko"]
    it["file"] = r["file"]
    it["file_disp"] = r["file"]
    it["qty"] = r["qty"]
    extra = it["group"] == "EX"
    it["qty_txt"] = ("선택 %d개" if extra else "%d개") % r["qty"]
    it["material"] = r["material"] or "PETG"
    m = r["mass_g_solid_petg"]
    it["mass_txt"] = "%s g" % fnum(m, 1) + (" (출력 약 %s g)" % fnum(r["mass_g_print_est"], 0) if r.get("mass_g_print_est") else "")
    it["note"] = r["note"]
    path = os.path.join(CAD, r["file"])
    Mp = stl_manifold(path)
    it["Mp"] = Mp
    b = Mp.bounding_box()
    it["print_ext"] = (b[3] - b[0], b[4] - b[1], b[5] - b[2])
    inst = ctx.by_file.get(r["file"], [])
    cpf = counterpart_file(r)
    via = None
    if not inst and cpf:
        for f, lst in ctx.by_file.items():
            if f.startswith(cpf):
                inst, via = lst, f
                break
    mp = None
    notes_pre, notes = [], []
    if inst:
        key = via if (via and r["folder"] == "@extra/예비_건반") else r["file"]
        if key in ctx.maps:
            R, t, res, meth = ctx.maps[key]
        else:
            same = inst[0].print_solid is not None and via is None
            R, t, res, meth = register(Mp, inst[0].solid, inst[0].print_solid if same else None)
            ctx.maps[key] = (R, t, res, meth)
        Q = nearest_cube(R)
        tilt, tax = rot_angle(R @ Q.T)
    else:
        Q, R, t, tilt, tax = np.eye(3), None, None, 0.0, None
    Dm = Mp.transform(affine(Q, [0, 0, 0]))
    bb = Dm.bounding_box()
    o = np.array(bb[:3])
    D = Dm.translate(tuple(-o))
    if R is not None:
        RQ = R @ Q.T
        W = np.zeros((3, 4))
        W[:, :3] = RQ
        W[:, 3] = RQ @ o + t
        mp = dict(W=W, inst=inst[0].id, res=res, meth=meth, tilt=tilt)
    it["map"] = mp
    it["Q"] = Q
    it["o"] = o
    down = Q @ np.array([0.0, 0.0, -1.0])
    face = face_of(down)
    ft = "베드에 닿는 면 = 도면의 %s" % face + (" (뒤집어 출력)" if face.startswith("윗면") else "")
    if R is None:
        ft += ". 조립에 들어가지 않는 출력물이라 도면 자세 = STL 자세"
    it["face_txt"] = ft
    if mp is not None:
        if tilt < 0.05:
            notes_pre.append("월드 좌표 = 부품 기준 + (%s, %s, %s) — 기준 개체 %s%s"
                             % (fnum(mp["W"][0, 3], 2), fnum(mp["W"][1, 3], 2), fnum(mp["W"][2, 3], 2), inst[0].id,
                                " (01 건반 파일과 같은 모양)" if r["folder"] == "@extra/예비_건반" else ""))
        else:
            i = int(np.argmax(np.abs(tax)))
            sgn = "+" if tax[i] > 0 else "-"
            notes_pre.append("조립에서는 도면 자세를 %s%s축 둘레로 %s° 돌린 자세 (기준 개체 %s). 그림은 기울기를 뺀 바른 자세, 표의 월드 좌표는 "
                             "실제(기울어진) 자리" % (sgn, AX[i], fnum(tilt, 2), inst[0].id))
        if meth.startswith("icp"):
            notes.append("출력 파일 → 조립 개체 맞춤: 회전 탐색 + ICP (%s, 중앙 오차 %s)%s" % (meth.split(", ", 1)[1].replace("of the surface within", "면이"),
                                                                              fnum(res, 4),
                                                                              " — 출력 파일에만 있는 떼는 지지대·5T 쐐기는 짝이 없음" if r["folder"].startswith(("02", "04", "@extra/대안")) else ""))
        ids = [p.id for p in inst]
        if len(ids) > 1 and r["folder"] != "@extra/예비_건반":
            pos = []
            for p in inst[:16]:
                bw = p.solid.bounding_box()
                pos.append("%s (x %s)" % (p.id, fnum(bw[0], 1)))
            notes.append("개체 %d개: %s%s" % (len(ids), " · ".join(pos), " …" if len(ids) > 16 else ""))
    else:
        if r["folder"].startswith("06"):
            notes.append("건반 액션 조립 공구 (key-action-v4/printables/tools) — 악기에 들어가지 않음")
        elif r["folder"].startswith(("08", "09")):
            notes.append("가공 지그 (cad/jigs/README.md) — 악기에 들어가지 않음, 월드 좌표 없음")
    if r["folder"].startswith("02"):
        notes.append("파일에는 강철 칸 가운데 떼는 지지대가 들어 있음 (그림에도 보임) — 출력 후 떼어 냄")
    if r["folder"].startswith("04") and "패드바" in r["name"]:
        notes.append("이 파일은 구매한 PORON 5T용 (쐐기 1.0 두꺼움). 조립 모델은 설계 6T, 6T용 파일은 선택·대안 묶음")
    it["notes_extra_pre"] = notes_pre
    it["notes_extra"] = notes
    G = Geo(D)
    it["G"] = G
    A = analyse(G)
    for i, s in enumerate(A["sections"]):
        s["let"] = SEC_LET[i]
    A["groups"] = hole_groups(A["holes"])
    A["tag_clusters"] = tag_clusters(A["groups"])
    it["A"] = A
    return it


def pattern_text2(hs):
    """drawings.pattern_text with sizes to 0.01 (it groups by 0.1: twelve Ø1.95 holes printed as 'Ø2 ×11 · Ø1.9')."""
    groups = collections.OrderedDict()
    for h in hs:
        key = ("Ø%s" % fnum(round(h["d"], 2), 2)) if h["round"] else ("%s×%s" % (fnum(round(h["w"], 2), 2), fnum(round(h["h"], 2), 2)))
        groups.setdefault(key, []).append(h)
    lines = []

    def pitch_txt(c):
        d = np.diff(c)
        return ("간격 %s" % fnum(d.mean(), 2)) if np.ptp(d) < 0.05 else "간격 " + "·".join(fnum(x, 2) for x in d)

    for key, g in groups.items():
        if len(g) == 1:
            lines.append("%s : 중심 (%s, %s)" % (key, fnum(g[0]["cu"], 2), fnum(g[0]["cv"], 2)))
            continue
        rows = collections.OrderedDict()
        for h in sorted(g, key=lambda h: (round(h["cv"], 1), h["cu"])):
            rows.setdefault(round(h["cv"], 1), []).append(h)
        cols = collections.OrderedDict()
        for h in sorted(g, key=lambda h: (round(h["cu"], 1), h["cv"])):
            cols.setdefault(round(h["cu"], 1), []).append(h)
        if len(cols) == 1:
            cv = sorted(h["cv"] for h in g)
            lines.append("%s ×%d : 세로 중심 %s~%s %s, 가로 중심 %s" % (key, len(g), fnum(cv[0], 2), fnum(cv[-1], 2), pitch_txt(cv), fnum(g[0]["cu"], 2)))
            continue
        rk = [tuple(round(h["cu"], 1) for h in r) for r in rows.values()]
        if len(rows) > 1 and len(cols) > 1 and len(set(rk)) == 1:
            cu = [h["cu"] for h in list(rows.values())[0]]
            cv = sorted(rows.keys())
            lines.append("%s ×%d : %d열 × %d줄 — 가로 중심 %s (%s) · 세로 중심 %s~%s %s"
                         % (key, len(g), len(cu), len(cv), "·".join(fnum(c_, 2) for c_ in cu), pitch_txt(cu), fnum(cv[0], 2), fnum(cv[-1], 2), pitch_txt(cv)))
            continue
        parts_ = []
        for cv, r in rows.items():
            cu = sorted(h["cu"] for h in r)
            if len(cu) == 1:
                parts_.append("(%s, %s)" % (fnum(cu[0], 2), fnum(cv, 2)))
            else:
                parts_.append("%d개 가로 중심 %s~%s %s · 세로 중심 %s" % (len(cu), fnum(cu[0], 2), fnum(cu[-1], 2), pitch_txt(cu), fnum(cv, 2)))
        lines.append("%s ×%d : " % (key, len(g)) + " / ".join(parts_))
    return lines


def note_lines(sh, it, W):
    return sh.wrap(it["note"] or "—", W - 4, 2.1)


def build_sheet(it):
    A = it["A"]
    ply = it["kind"] == "ply"
    sizes = SIZES + ([("A0", 1189.0, 841.0)] if ply else [])
    res = []
    it.pop("ord_note", None)
    for size in sizes:
        L = plan(A, size, k_max=1.0 if ply else 10.0)
        if L is None or (ply and L["k"] < 1.0):
            continue
        sh = PSheet(it["code"], it["name_ko"], size)
        Cw = L["Cw"]
        nl = note_lines(sh, it, Cw)
        tb_h = 11 + 8 + 7 + 7 + 8 + 3.2 + len(nl) * 2.9 + 2.5 + 6
        saved = A["sections"]
        A["sections"] = [s for s, _, _, _ in L["secs"]]
        y_end = column_content(sh, sh.w - 10 - Cw, 12.0, Cw, it, A, it["map"], dry=True)
        A["sections"] = saved
        res.append((size, L, y_end <= sh.h - 10 - tb_h - 3))
    if not res:
        raise RuntimeError("%s: no sheet fits" % it["code"])
    fit = [t for t in res if t[2]]
    if fit:
        target = min(max(t[1]["k"] for t in fit), 1.0)
        size, L, _ = next(t for t in fit if t[1]["k"] >= target - 1e-9)
    else:
        size, L, _ = max(res, key=lambda t: (t[0][1], t[1]["k"]))
    sh = PSheet(it["code"], it["name_ko"], size)
    A["sections"] = [s for s, _, _, _ in L["secs"]]
    sh.scale_txt = sc_txt(L["k"]) + ("" if all(ks == L["k"] for _, ks, _, _ in L["secs"]) else " (단면 따로 적음)")
    dx, boxes = draw_views(sh, L, A, it["map"], it)
    if ply:
        ply_overlay(sh, it, boxes)
    Cw = L["Cw"]
    cx = sh.w - 10 - Cw
    sh.line([(cx - 3, 10), (cx - 3, sh.h - 10)], "grid2", "over")
    nl = note_lines(sh, it, Cw)
    tb_y = title_block(sh, cx, 0, Cw, it, sh.scale_txt, nl)
    y_end = column_content(sh, cx, 12.0, Cw, it, A, it["map"])
    it["col_overflow"] = max(0.0, y_end - (tb_y - 2))
    it["L"] = L
    it["dx"] = dx
    it["overlaps"] = sh.check()
    return sh


# ------------------------------------------------------------------ DXF (1:1, mm, R2010)

DXF_LAYERS = [("VISIBLE", 7, "CONTINUOUS", 35), ("HIDDEN", 8, "HIDDEN", 18), ("SECTION", 5, "CONTINUOUS", 25),
              ("DIM", 4, "CONTINUOUS", 13), ("DIM_MORE", 3, "CONTINUOUS", 13), ("TEXT", 7, "CONTINUOUS", 18),
              ("CENTER", 1, "CENTER", 13)]
# ezdxf's setup=True has no 'HIDDEN' linetype (only DASHED*, CENTER*, ...): define it, scaled for 1:1 mm part drawings
# (dash 2.0, gap 1.0 at $LTSCALE 1 -> a Ø3 hole still shows 3 dashes). Without it the layer fell back to CONTINUOUS.
HIDDEN_LT = ("HIDDEN", [3.0, 2.0, -1.0], "Hidden __ __ __ __ __ (2.0 / 1.0 mm)")


def dxf_doc():
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    doc.header["$LTSCALE"] = 1.0
    if HIDDEN_LT[0] not in doc.linetypes:
        doc.linetypes.add(HIDDEN_LT[0], HIDDEN_LT[1], description=HIDDEN_LT[2])
    for nm, col, lt, lw in DXF_LAYERS:
        if lt not in doc.linetypes:
            raise RuntimeError("DXF linetype %s missing" % lt)
        if nm not in doc.layers:
            doc.layers.add(nm, color=col, linetype=lt, lineweight=lw)
    if "KR" not in doc.styles:
        doc.styles.add("KR", font="malgun.ttf")
    ds = doc.dimstyles.duplicate_entry("EZDXF", "TOCCATA")
    ds.dxf.dimtxt = 2.5
    ds.dxf.dimasz = 2.0
    ds.dxf.dimexo = 1.0
    ds.dxf.dimexe = 1.2
    ds.dxf.dimdec = 2
    ds.dxf.dimzin = 8
    ds.dxf.dimtxsty = "KR"
    ds.dxf.dimlfac = 1.0
    ds.dxf.dimgap = 0.8
    return doc


def dxf_curves(msp, curves, ox, oy, layer_vis="VISIBLE", layer_hid="HIDDEN"):
    for kind, layer in (("vis", layer_vis), ("hid", layer_hid)):
        for typ, g in curves.get(kind, []):
            if typ == "circle":
                cx, cy, r = g
                msp.add_circle((cx + ox, cy + oy), r, dxfattribs={"layer": layer})
            elif typ == "arc":
                cx, cy, r, a0, a1, ccw, p0, p1 = g
                s_, e_ = (a0, a1) if ccw else (a1, a0)
                msp.add_arc((cx + ox, cy + oy), r, math.degrees(s_), math.degrees(e_), dxfattribs={"layer": layer})
            else:
                pts = [(float(u) + ox, float(v) + oy) for u, v in g]
                if len(pts) >= 2:
                    msp.add_lwpolyline(pts, dxfattribs={"layer": layer})


def dxf_text(msp, x, y, s, h=2.5, layer="TEXT", align=None, rot=0.0):
    t = msp.add_text(s, height=h, dxfattribs={"layer": layer, "style": "KR", "rotation": rot})
    t.set_placement((x, y))
    return t


def write_dxf(path, it, extra_layers=None):
    """views + sections at 1:1 in their third-angle places (gap 30 mm), overall + ordinate dimensions as DIMENSION
    entities, hole table and title as text. Returns the file size."""
    A, dx = it["A"], it["dx"]
    X, Y, Z = A["ext"]
    gap = 30.0
    doc = dxf_doc()
    msp = doc.modelspace()
    org = {"top": (0.0, Z + gap), "front": (0.0, 0.0), "side": (X + gap, 0.0)}
    for nm, (ox, oy) in org.items():
        dxf_curves(msp, dx["views"][nm], ox, oy)
        dxf_text(msp, ox, oy - 12.0 if nm != "top" else oy - 8.0, VIEW_KO[nm], 3.0)
    dim = dict(dimstyle="TOCCATA", dxfattribs={"layer": "DIM"})
    # overall
    for p1, p2, base, ang in (((0, 0), (X, 0), (0, -6), 0), ((X, Z + gap), (X, Z + gap + Y), (X + 8, 0), 90),
                              ((X + gap, 0), (X + gap + Y, 0), (0, -6), 0), ((X + gap + Y, 0), (X + gap + Y, Z), (X + gap + Y + 8, 0), 90)):
        try:
            msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=ang, **dim).render()
        except Exception:
            pass
    # ordinates (origin = the view's datum corner)
    ords = dx["ords"]
    oxT, oyT = org["top"]

    def stagger(cs, base=8.0, levels=3):
        """leader lengths base / +7 / +14 ... so labels of close coordinates (< 3.2 mm) do not sit on each other."""
        out, prev, lvl = [], None, 0
        for c in sorted(cs):
            lvl = (lvl + 1) % levels if (prev is not None and c - prev < 3.2) else 0
            out.append((c, base + 7.0 * lvl))
            prev = c
        return out

    def put_ords(cs, layer, base, levels):
        d_ = dict(dimstyle="TOCCATA", dxfattribs={"layer": layer})
        n_ = 0
        for ax_, lst in cs.items():
            for c, off in stagger(lst, base, levels):
                try:
                    if ax_ == "x":
                        msp.add_ordinate_x_dim(feature_location=(oxT + c, oyT + Y), offset=(0, off), origin=(oxT, oyT), **d_).render()
                    elif ax_ == "y":
                        msp.add_ordinate_y_dim(feature_location=(oxT, oyT + c), offset=(-off, 0), origin=(oxT, oyT), **d_).render()
                    else:
                        msp.add_ordinate_y_dim(feature_location=(0, c), offset=(-off, 0), origin=(0, 0), **d_).render()
                    n_ += 1
                except Exception:
                    pass
        return n_
    # the ordinates printed on the sheet (layer DIM) + every other edge coordinate of the views (layer DIM_MORE, further
    # out: the DXF has no layout limit, so nothing measured is left out)
    n_dim = put_ords({a_: ords[a_] for a_ in "xyz"}, "DIM", 8.0, 3)
    more = {a_: [c for c, _w, on in dx["ords_all"][a_] if not on] for a_ in "xyz"}
    n_more = put_ords(more, "DIM_MORE", 32.0, 4)
    it["dxf_ords"] = (n_dim, n_more)
    # sections to the right of the side view
    sx = X + gap + Y + gap + 10
    sy = 0.0
    for s in dx["secs"]:
        a, b = s["size"]
        paths = [[(float(u) + sx, float(v) + sy) for u, v in P] for P in s["polys"]]
        for P in paths:
            msp.add_lwpolyline(P, close=True, dxfattribs={"layer": "SECTION"})
        try:
            h = msp.add_hatch(dxfattribs={"layer": "SECTION"})
            h.set_pattern_fill("ANSI31", scale=0.5)
            for P in paths:
                h.paths.add_polyline_path(P, is_closed=True)
        except Exception:
            pass
        iu, iv = PLANE_AX[s["axis"]]
        dxf_text(msp, sx, sy - 8.0, "%s-%s 단면 (%s = %s), 왼쪽 아래 = %s %s · %s %s" % (s["let"], s["let"], s["axis"], fnum(s["c"], 2),
                                                                             AX[iu], fnum(s["off"][0], 2), AX[iv], fnum(s["off"][1], 2)), 3.0)
        sy += b + gap
    # hole table + notes as text below the front view
    ty = -30.0
    dxf_text(msp, 0, ty, "%s  %s  (%s)" % (it["code"], it["name_ko"], it["file"]), 3.5)
    ty -= 6
    dxf_text(msp, 0, ty, "수량 %s · 재료 %s · 질량 %s · 단위 mm · 1:1 · 원점 = 도면 자세 최소 모서리" % (it["qty_txt"], it["material"], it["mass_txt"]), 2.5)
    ty -= 6
    dxf_text(msp, 0, ty, "레이어: VISIBLE 보이는 선 · HIDDEN 숨은 선 (점선) · SECTION 단면 · DIM 시트의 치수 (%d) · DIM_MORE 시트에서 뺀 모서리 좌표 (%d) · TEXT"
             % (n_dim, n_more), 2.5)
    ty -= 6
    for g in A["groups"]:
        for hh in g["holes"]:
            w = world_of(it["map"], entry_point(hh))
            dxf_text(msp, 0, ty, "%s  %s  %s  중심 %s  월드 %s%s" % (g["no"], size_txt(hh), depth_txt(hh, A["ext"]), uv_txt(hh), wtxt(w),
                                                           ("  " + isl_txt(hh)) if hh.get("isl") else ""), 2.2)
            ty -= 3.6
    if A["engr"]:
        dxf_text(msp, 0, ty, "새김 글자 %d곳 (깊이 %s) — 구멍 번호 없음" % (len(A["engr"]), "·".join(sorted(set(fnum(h["depth"], 2) for h in A["engr"])))), 2.2)
        ty -= 3.6
    for ln in (it["note"] or "").split(". "):
        if ln.strip():
            dxf_text(msp, 0, ty, ln.strip()[:200], 2.2)
            ty -= 3.6
    if extra_layers:
        extra_layers(doc, msp)
    doc.saveas(path)
    return os.path.getsize(path)


def holes_csv(it):
    A = it["A"]
    out = io.StringIO()
    out.write("no,shape,kind,size,axis,from,to,depth,ends,u_axis,u,v_axis,v,world_x,world_y,world_z,"
              "box_u0,box_u1,box_v0,box_v1,d_from,d_to,islands_u0_u1_v0_v1,outline_u_v_mid_depth\n")
    rows = [(g["no"], h) for g in A["groups"] for h in g["holes"]]
    rows += [("새김", h) for h in A["engr"]]
    for no, h in rows:
        iu, iv = PLANE_AX[h["axis"]]
        w = world_of(it["map"], entry_point(h))
        shape_txt = size_txt(h) if no != "새김" else "새김 글자 %s×%s" % (fnum(h["w"], 2), fnum(h["h"], 2))
        outline = " ".join("%.3f:%.3f" % (u, v) for u, v in h.get("outline", [])) if h["shape"] in ("other", "rect") or h.get("isl") else ""
        out.write("%s,%s,%s,%s,%s,%.3f,%.3f,%.3f,%s,%s,%.3f,%s,%.3f,%s,%.3f,%.3f,%.3f,%.3f,%s,%s,%s,%s\n" % (
            no, h["shape"], h.get("kind", ""), shape_txt.replace(",", " "), h["axis"], h["lo"], h["hi"], h["depth"],
            "/".join(h["ends"]), AX[iu], h["cu"], AX[iv], h["cv"], ",".join("%.3f" % q for q in w) if w is not None else ",,",
            h["u0"], h["u1"], h["v0"], h["v1"],
            "%.3f" % h["d_lo"] if h.get("kind") == "cone" else "", "%.3f" % h["d_hi"] if h.get("kind") == "cone" else "",
            " ".join("%.3f:%.3f:%.3f:%.3f" % t for t in h.get("isl", [])), outline))
    return out.getvalue()


def ords_csv(it):
    """every edge coordinate the views found (sheet ordinates + the ones left off the sheet), part datum, + the world
    coordinate on the matching world axis when the part sits square in the instrument."""
    dx = it["dx"]
    mp = it["map"]
    out = io.StringIO()
    out.write("axis,coord_mm,edge_length_mm,on_sheet,dxf_layer,world_axis,world_mm\n")
    for a_ in "xyz":
        i = AX.index(a_)
        for c, w, on in dx["ords_all"][a_]:
            wa, wv = "", ""
            if mp is not None and mp["tilt"] < 0.05:
                col = mp["W"][:, i]
                j = int(np.argmax(np.abs(col)))
                if abs(abs(col[j]) - 1.0) < 1e-6:
                    wa, wv = AX[j], "%.3f" % (float(np.sign(col[j]) * c + mp["W"][j, 3]) + 0.0)
            out.write("%s,%.2f,%.2f,%s,%s,%s,%s\n" % (a_, c + 0.0, w, "yes" if on else "no", "DIM" if on else "DIM_MORE", wa, wv))
    return out.getvalue()


# ------------------------------------------------------------------ plywood pieces

PLY_ORDER = ["SPKL-PLY-SIDEOUT", "SPKR-PLY-SIDEOUT", "SPKL-PLY-BACK", "SPKR-PLY-BACK", "SPKL-PLY-TOP", "SPKR-PLY-TOP",
             "SPKL-PLY-BOTTOM", "SPKR-PLY-BOTTOM", "CU-PLY-BACK", "CU-PLY-BOTTOM"]
PLY_Q = {"z": np.eye(3), "y": np.array([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]]), "x": np.array([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]])}


def ply_context(ctx):
    if hasattr(ctx, "ply"):
        return ctx.ply
    M = DR.Model(ctx.parts)
    plys = [p for p in M.rear if p.kind == "plywood"]
    fps = {p.id: DR.flat_piece(M, p) for p in plys}
    spots = DR.ply_spots(M, list(fps.values()))
    jigs = DR.ply_jigs(M, list(fps.values()))
    info = {}
    for pid, fp in fps.items():
        inf = DR.piece_memo(fp, M)
        inf["spots"] = spots.get(pid, [])
        info[pid] = inf
    ctx.ply = dict(M=M, fps=fps, info=info, jigs=jigs, by={p.id: p for p in plys})
    return ctx.ply


def ply_items(ctx):
    if not any(p.kind == "plywood" for p in ctx.parts):
        return []                 # 2026-10-16 (A안): no plywood - the former panels are print files with their own sheets
    pc = ply_context(ctx)
    out = []
    for n, pid in enumerate([q for q in PLY_ORDER if q in pc["by"]] + sorted(q for q in pc["by"] if q not in PLY_ORDER), 1):
        out.append(dict(code="P-PLY-%02d" % n, group="PLY", kind="ply", pid=pid))
    return out


def prepare_ply(it, ctx):
    pc = ply_context(ctx)
    M, p = pc["M"], pc["by"][it["pid"]]
    fp, inf = pc["fps"][p.id], pc["info"][p.id]
    it["name_ko"] = DR.short(p.name_ko).replace("스피커 파트 ", "스피커 ")
    it["file"] = None
    it["file_disp"] = "합판 조각 (출력 파일 없음) · CAD %s" % p.id
    it["qty"] = 1
    it["qty_txt"] = "1장"
    it["material"] = "오꾸메 합판 %sT" % fnum(fp["T"], 1)
    vol = p.solid.volume() / 1000.0
    it["mass_txt"] = "부피 %s cm³" % fnum(vol, 1)
    Q = PLY_Q[fp["ax"]]
    Dm = p.solid.transform(affine(Q, [0, 0, 0]))
    bb = Dm.bounding_box()
    o = np.array(bb[:3])
    D = Dm.translate(tuple(-o))
    W = np.zeros((3, 4))
    W[:, :3] = Q.T
    W[:, 3] = Q.T @ o
    it["map"] = dict(W=W, inst=p.id, res=0.0, meth="exact", tilt=0.0)
    it["Q"], it["o"] = Q, o
    it["Mp"] = D
    it["print_ext"] = (bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2])
    drawn = DR.DRAWN_FACE[fp["ax"]]
    face_up = DR.face_name(M, fp, drawn)
    # shop sizes with 2 decimals, the same numbers as D06 (139.65, 56.35, 14.14)
    it["face_txt"] = "합판: 평면도 = '%s'이 위인 면 (D06와 같음). 가게에서 직사각형 %s × %s로 자르고, 나머지는 집에서" % (face_up, fnum(fp["W"], 2), fnum(fp["H"], 2))
    jt = DR.jig_line(M, fp, pc["jigs"].get(p.id, []), inf)
    sps = inf["spots"]
    pre = ["판 좌표 u·v = 평면도의 x·y (원점 = 초록 기준 모서리의 만나는 점 = 입체 (%s, %s) %s 면)" % (fnum(fp["org"][0], 2), fnum(fp["org"][1], 2),
                                                                                  {"x": "y·z", "y": "x·z", "z": "x·y"}[fp["ax"]]),
           "이 면이 위: %s · 반대 면: %s · 두께 %s" % (face_up, DR.face_name(M, fp, 1 - drawn), fnum(fp["T"], 2))]
    notes = []
    for m in inf["memo"]:
        notes.append("윤곽: " + m)
    for t in inf["notes"]:
        notes.append(t)
    if jt:
        notes.append("지그: " + jt)
    if sps:
        by = collections.OrderedDict()
        for sp in sps:
            by.setdefault((sp["kind"], sp["what"], sp["fi"]), []).append(sp)
        for (kind, what, fi), ss in by.items():
            notes.append("나사 자리 ⊕ %s %s ×%d (%s에서 박음, 송곳): %s" % (what, DR.SPOT_KIND[kind], len(ss), DR.face_name(M, fp, fi),
                                                                " · ".join("(%s, %s)" % (fnum(sp["u"], 1), fnum(sp["v"], 1)) for sp in sorted(ss, key=lambda t: (t["u"], t["v"])))))
    notes.append("DXF: CUT = 바깥 윤곽 + 관통 구멍 (원), DRILL_BLIND = 막힘 구멍 (깊이 글자), MARK = 나사 자리, 나머지 = 세 방향 그림 (1:1, mm)")
    it["notes_extra_pre"] = pre
    it["notes_extra"] = notes
    it["note"] = ("가게: 직사각형 %s × %s (두께 %s)으로만 자름. 경사·따냄은 톱, 구멍은 지그 (cad/jigs/README.md). 자르자마자 조각 이름·L 끝·'%s'를 연필로 씀"
                  % (fnum(fp["W"], 2), fnum(fp["H"], 2), fnum(fp["T"], 2), face_up))
    it["fp"], it["inf"] = fp, inf
    G = Geo(D)
    it["G"] = G
    A = analyse(G)
    for i, s in enumerate(A["sections"]):
        s["let"] = SEC_LET[i]
    A["groups"] = hole_groups(A["holes"])
    A["tag_clusters"] = tag_clusters(A["groups"])
    it["A"] = A
    return it


def ply_overlay(sh, it, boxes):
    """D06 marks on the face view: datum edges, screw spots."""
    vb = boxes["top"]
    fp, inf = it["fp"], it["inf"]
    outer = inf["outer"]
    n = len(outer)
    for j in range(n):
        pa, pb = outer[j], outer[(j + 1) % n]
        if (abs(pa[0]) < 0.01 and abs(pb[0]) < 0.01) or (abs(pa[1]) < 0.01 and abs(pb[1]) < 0.01):
            sh.line([vb.P(*pa), vb.P(*pb)], "datum", "over")
    drawn = DR.DRAWN_FACE[fp["ax"]]
    for sp in inf["spots"]:
        x, y = vb.P(sp["u"], sp["v"])
        sh.spot(x, y, cls="spot" if sp["fi"] == drawn else "spoth", r=1.0)
    sh.text(vb.X + text_w(VIEW_KO["top"], TL) + 6.0, vb.Y + vb.h + 6.2, "초록 굵은 선 = 기준 모서리 (u·v를 재는 곳) · ⊕ = 나사 자리 (점선 = 반대 면)", TS, cls="tg", halo=False)


def ply_dxf_layers(it):
    def add(doc, msp):
        for nm, col, lt in (("CUT", 1, "CONTINUOUS"), ("DRILL_BLIND", 6, "HIDDEN"), ("MARK", 30, "CONTINUOUS")):
            if nm not in doc.layers:
                doc.layers.add(nm, color=col, linetype=lt)
        fp, inf = it["fp"], it["inf"]
        A = it["A"]
        X, Y, Z = A["ext"]
        # the cut profile goes beside the views (x offset) so it can be sent alone: origin = datum corner
        ox = -(fp["W"] + 60.0)
        oy = Z + 30.0
        msp.add_lwpolyline([(float(u) + ox, float(v) + oy) for u, v in inf["outer"]], close=True, dxfattribs={"layer": "CUT"})
        for h in inf["thru"]:
            if h["round"]:
                msp.add_circle((h["cu"] + ox, h["cv"] + oy), h["d"] / 2, dxfattribs={"layer": "CUT"})
            else:
                msp.add_lwpolyline([(h["u0"] + ox, h["v0"] + oy), (h["u1"] + ox, h["v0"] + oy), (h["u1"] + ox, h["v1"] + oy), (h["u0"] + ox, h["v1"] + oy)],
                                   close=True, dxfattribs={"layer": "CUT"})
        for h in inf["blind"]:
            if h["round"]:
                msp.add_circle((h["cu"] + ox, h["cv"] + oy), h["d"] / 2, dxfattribs={"layer": "DRILL_BLIND"})
            dxf_text(msp, h["cu"] + ox + (h["d"] or h["w"]) / 2 + 1, h["cv"] + oy, "깊이 %s" % fnum(h["depth"], 1), 2.0, layer="DRILL_BLIND")
        for pk in inf["pockets"]:
            msp.add_lwpolyline([(pk["u0"] + ox, pk["v0"] + oy), (pk["u1"] + ox, pk["v0"] + oy), (pk["u1"] + ox, pk["v1"] + oy), (pk["u0"] + ox, pk["v1"] + oy)],
                               close=True, dxfattribs={"layer": "DRILL_BLIND"})
        for sp in inf["spots"]:
            msp.add_circle((sp["u"] + ox, sp["v"] + oy), 1.0, dxfattribs={"layer": "MARK"})
            msp.add_line((sp["u"] + ox - 1.6, sp["v"] + oy), (sp["u"] + ox + 1.6, sp["v"] + oy), dxfattribs={"layer": "MARK"})
            msp.add_line((sp["u"] + ox, sp["v"] + oy - 1.6), (sp["u"] + ox, sp["v"] + oy + 1.6), dxfattribs={"layer": "MARK"})
        dxf_text(msp, ox, oy - 8.0, "재단 윤곽 (CUT, 1:1, 원점 = 기준 모서리)", 3.0, layer="CUT")
    return add


# ------------------------------------------------------------------ outputs: sheet, DXF, zip, index

def safe_name(s):
    s = s.replace("#", "s").replace("·", "-").replace("/", "-").replace(" ", "_")
    return re.sub(r"[^0-9A-Za-z가-힣._\-Ø]", "", s)


def write_item(it, verbose=True):
    """sheet SVG, DXF, measured JSON, download zip (base64 text) for one item; returns the index row."""
    t0 = time.time()
    for d in ("svg", "dxf", "data"):
        os.makedirs(os.path.join(PDIR, d), exist_ok=True)
    os.makedirs(FIN, exist_ok=True)
    sh = build_sheet(it)
    svg = sh.svg()
    code = it["code"]
    p_svg = os.path.join(PDIR, "svg", code + ".svg")
    open(p_svg, "w", encoding="utf-8").write(svg)
    open(os.path.join(FIN, code + ".svg"), "w", encoding="utf-8").write(svg)
    p_dxf = os.path.join(PDIR, "dxf", code + ".dxf")
    write_dxf(p_dxf, it, ply_dxf_layers(it) if it["kind"] == "ply" else None)
    csv = holes_csv(it)
    base = "Toccata_%s_%s" % (code, safe_name(it["name_ko"]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        if it["kind"] == "print":
            stl_path = os.path.join(CAD, it["file"])
            z.write(stl_path, os.path.basename(it["file"]))
            stl_name, stl_bytes = os.path.basename(it["file"]), os.path.getsize(stl_path)
        else:
            import trimesh
            Vd, Fd = mesh_arrays(it["G"].D)
            sb = trimesh.Trimesh(Vd, Fd, process=False).export(file_type="stl")
            stl_name = "%s_합판조각_참고.stl" % safe_name(it["name_ko"])
            z.writestr(stl_name, sb)
            stl_bytes = len(sb)
        z.write(p_dxf, base + ".dxf")
        z.writestr(base + ".svg", svg)
        z.writestr(base + "_구멍표.csv", "\ufeff" + csv)
        z.writestr(base + "_좌표.csv", "\ufeff" + ords_csv(it))
        z.writestr("읽어보기.txt", readme_txt(it, stl_name, base))
    zb = buf.getvalue()
    b64 = base64.b64encode(zb).decode("ascii")
    open(os.path.join(FIN, code + ".zip.b64.txt"), "w").write(b64)
    A = it["A"]
    r = it.get("row") or {}
    data = dict(code=code, name=it["name_ko"], kind=it["kind"], group=it["group"], folder=r.get("folder", "합판"),
                file=it["file"], qty=it["qty"], material=it["material"], ext=[round(float(v), 3) for v in A["ext"]],
                print_ext=[round(float(v), 3) for v in it["print_ext"]], Q=it["Q"].tolist(), o=[float(v) for v in it["o"]],
                W=None if it["map"] is None else it["map"]["W"].tolist(), inst=None if it["map"] is None else it["map"]["inst"],
                tilt=0.0 if it["map"] is None else float(it["map"]["tilt"]),
                sheet=sh.size_name, scale=it["L"]["k"], sections=[dict(axis=s["axis"], c=s["c"], let=s["let"]) for s in A["sections"]],
                ords=it["dx"]["ords"], holes=[dict(no=g["no"], shape=h["shape"], kind=h.get("kind"), axis=h["axis"], cu=float(h["cu"]), cv=float(h["cv"]),
                                                    d=None if h.get("d") is None else float(h["d"]), w=float(h["w"]), h=float(h["h"]),
                                                    lo=float(h["lo"]), hi=float(h["hi"]), ends=h["ends"],
                                                    box=[float(h["u0"]), float(h["u1"]), float(h["v0"]), float(h["v1"])], box3=box3_swept(h),
                                                    d_lo=None if h.get("d_lo") is None else float(h["d_lo"]),
                                                    d_hi=None if h.get("d_hi") is None else float(h["d_hi"]),
                                                    isl=[list(t) for t in h.get("isl", [])],
                                                    world=None if it["map"] is None else [float(q) for q in world_of(it["map"], entry_point(h))])
                                               for g in A["groups"] for h in g["holes"]],
                engr=[dict(axis=h["axis"], depth=float(h["depth"]), box3=box3_swept(h)) for h in A["engr"]],
                frag=[dict(axis=h["axis"], depth=float(h["depth"]), box3=box3_swept(h)) for h in A.get("frag", [])],
                ords_all={a_: [[c, w, bool(on)] for c, w, on in it["dx"]["ords_all"][a_]] for a_ in "xyz"},
                tags=[c["label"] for c in it["A"]["tag_clusters"]], tags_forced=it["dx"].get("tags_forced", 0),
                dxf_ords=list(it.get("dxf_ords", (0, 0))),
                overlaps=it["overlaps"], col_overflow=it["col_overflow"], table_cut=it.get("table_cut", 0), ords_missing=it["dx"]["ords"]["missing"],
                t=round(time.time() - t0 + A["t"], 2))
    json.dump(data, open(os.path.join(PDIR, "data", code + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    row = dict(code=code, name=it["name_ko"], kind=it["kind"], group=it["group"], group_ko=FOLDER_KO[it["group"]],
               folder=r.get("folder", "합판"), qty=it["qty"], qty_txt=it["qty_txt"], material=it["material"],
               file=("hardware/mechanical/cad/" + it["file"]) if it["file"] else None, stl_name=stl_name,
               size_mm=[round(float(v), 2) for v in it["print_ext"]], draw_ext=[round(float(v), 2) for v in A["ext"]],
               mass_g=r.get("mass_g_solid_petg"), mass_g_print_est=r.get("mass_g_print_est"), print_min_est=r.get("print_min_est"),
               volume_cm3=round(it["G"].D.volume() / 1000.0, 2), note=it["note"], extra=it["group"] == "EX",
               ids=list(r.get("ids") or ([it["pid"]] if it["kind"] == "ply" else [])),
               svg="fin/parts/%s.svg" % code, zip="fin/parts/%s.zip.b64.txt" % code, zip_name=base + ".zip",
               bytes=dict(svg=len(svg.encode("utf-8")), zip=len(zb), zip_b64=len(b64), stl=stl_bytes, dxf=os.path.getsize(p_dxf)),
               sheet=sh.size_name, scale=sc_txt(it["L"]["k"]), holes=len(data["holes"]), hole_groups=len(A["groups"]),
               sections=len(A["sections"]))
    if verbose:
        print("%-9s %-28s %s %-5s holes %3d  svg %4d KB  zip %4d KB  overlaps %d  overflow %.0f  %.1fs" % (
            code, it["name_ko"][:28], sh.size_name, sc_txt(it["L"]["k"]), len(data["holes"]), len(svg) // 1024, len(zb) // 1024,
            len(it["overlaps"]), it["col_overflow"], time.time() - t0 + A["t"]))
    return row


def readme_txt(it, stl_name, base):
    lines = ["Toccata %s %s" % (it["code"], it["name_ko"]), "",
             "들어 있는 것:",
             "  %s  - %s" % (stl_name, "출력 파일 (stl/print 또는 print_extra의 파일과 바이트까지 같음)" if it["kind"] == "print" else "합판 조각의 3D (참고용, 출력 안 함)"),
             "  %s.dxf  - 같은 도면 (1:1, mm, R2010; 레이어 VISIBLE/HIDDEN/SECTION/DIM/TEXT%s)" % (base, "/CUT/DRILL_BLIND/MARK" if it["kind"] == "ply" else ""),
             "  %s.svg  - 도면 시트 (100 %%로 인쇄하면 적힌 척도 그대로)" % base,
             "  %s_구멍표.csv  - 구멍·포켓 표 (부품 기준 좌표 + 월드 좌표, 윤곽 상자, 원뿔 지름, 안에 선 섬, '모양' 윤곽 꼭짓점; 새김 글자는 번호 '새김')" % base,
             "  %s_좌표.csv  - 세 그림에서 찾은 모서리 좌표 전부 (시트에 적은 것 + 자리가 없어 뺀 것, on_sheet 열)" % base,
             "",
             "DXF 레이어: VISIBLE 보이는 선 · HIDDEN 숨은 선 (점선 HIDDEN, 2.0/1.0 mm) · SECTION 단면 (빗금) · DIM 시트에 적은 치수 · "
             "DIM_MORE 시트에서 뺀 모서리 좌표 (전부) · TEXT 글자%s" % (" · CUT 재단 윤곽 · DRILL_BLIND 막힘 구멍 · MARK 나사 자리" if it["kind"] == "ply" else ""),
             "",
             "수량: %s · 재료: %s · %s" % (it["qty_txt"], it["material"], it["mass_txt"]),
             "메모: %s" % (it["note"] or "-"), "",
             "좌표: 부품 기준 = 도면 자세의 최소 모서리 (0, 0, 0). 월드 = x 가로 (0 = A0 왼쪽 끝), y 흰 건반 앞 끝에서 뒤로, z 책상에서 위로.",
             "원본: hardware/mechanical/cad/src/part_sheets.py (출력 파일의 입체에서 잼), %s" % DATE]
    return "\r\n".join(lines)


def all_items(ctx):
    items = collect_items(ctx.man)
    return items + ply_items(ctx)


def prepare(it, ctx):
    return prepare_print(it, ctx) if it["kind"] == "print" else prepare_ply(it, ctx)


def package_all(rows):
    """index.json + the all-STL zip (the build's Toccata_출력STL_전체.zip as it is) + all DXF zip, base64."""
    os.makedirs(FIN, exist_ok=True)
    zp = os.path.join(CAD, "Toccata_출력STL_전체.zip")
    zb = open(zp, "rb").read()
    open(os.path.join(FIN, "all_stl.zip.b64.txt"), "w").write(base64.b64encode(zb).decode("ascii"))
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if n.endswith(".stl")]
        zsz = {n: z.getinfo(n).file_size for n in names}
    # check against stl/print on disk
    disk = {}
    for root, _d, fns in os.walk(os.path.join(CAD, "stl", "print")):
        for fn in fns:
            if fn.endswith(".stl"):
                full = os.path.join(root, fn)
                disk[os.path.relpath(full, os.path.join(CAD, "stl"))] = os.path.getsize(full)
    stl_zip_ok = disk == zsz
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for r in rows:
            z.write(os.path.join(PDIR, "dxf", r["code"] + ".dxf"), "%s/%s.dxf" % (safe_name(r["group_ko"]), r["zip_name"][:-4]))
        z.writestr("읽어보기.txt", "Toccata 부품 도면 DXF 전체 (%d개, 1:1, mm, R2010). 이름 = 도면 번호_부품 이름. %s" % (len(rows), DATE))
    db = buf.getvalue()
    open(os.path.join(FIN, "all_dxf.zip.b64.txt"), "w").write(base64.b64encode(db).decode("ascii"))
    idx = dict(date=DATE, source="hardware/mechanical/cad/src/part_sheets.py", units="mm",
               coords="world: x across (0 = A0 left end of the key bed), y from the white-key front lip, z from the desk; part datum = min corner of the drawing pose",
               groups=[dict(id=g, name=FOLDER_KO[g]) for g in list(FOLDER_NO.values()) + ["PLY", "EX"]],
               all_stl=dict(path="fin/parts/all_stl.zip.b64.txt", name="Toccata_출력STL_전체.zip", bytes=len(zb), files=len(names), matches_stl_print=stl_zip_ok),
               all_dxf=dict(path="fin/parts/all_dxf.zip.b64.txt", name="Toccata_부품도면_DXF_전체.zip", bytes=len(db), files=len(rows)),
               by_file={r["file"]: r["code"] for r in rows if r["file"]},
               parts=rows)
    json.dump(idx, open(os.path.join(FIN, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return idx


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    codes = [a for a in argv if not a.startswith("--")]
    if "--tab" in argv:     # 2026-10-30: only the tab fragment + fin/parts3d, from fin/parts/index.json and verify.json (no sheets)
        idx = json.load(open(os.path.join(FIN, "index.json"), encoding="utf-8"))
        write_tab(idx)
        write_meta(idx, json.load(open(os.path.join(PDIR, "verify.json"), encoding="utf-8")), idx["parts"])
        print("tab + 3D meshes rebuilt from fin/parts/index.json (%d parts)" % len(idx["parts"]))
        return [], []
    t0 = time.time()
    ctx = Ctx()
    print("collect %.1fs" % (time.time() - t0))
    items = all_items(ctx)
    rows = []
    fails = []
    for it in items:
        if codes and it["code"] not in codes:
            continue
        try:
            prepare(it, ctx)
            rows.append(write_item(it))
        except Exception as ex:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            fails.append((it["code"], repr(ex)))
        for k in ("G", "A", "dx", "Mp"):
            it.pop(k, None)
    if not codes:
        idx = package_all(rows)
        print("index: %d parts, all STL zip %d KB (matches stl/print: %s), all DXF zip %d KB"
              % (len(rows), idx["all_stl"]["bytes"] // 1024, idx["all_stl"]["matches_stl_print"], idx["all_dxf"]["bytes"] // 1024))
        write_tab(idx)
        ver = verify(ctx)
        print("verify:", ver["totals"])
        for c, r in ver["parts"].items():
            if r["fails"]:
                print("  ", c, r["fails"][:4])
        write_meta(idx, ver, rows)
    print("done %d items in %.0fs, failures %s" % (len(rows), time.time() - t0, fails or "none"))
    return rows, fails



# ------------------------------------------------------------------ tab fragment (docs/report/toccata-v4/src/tabs/partdwg)

TAB = os.path.join(REPO, "docs", "report", "toccata-v4", "src", "tabs", "partdwg")


def _kb(n):
    return ("%s MB" % fnum(n / 1048576.0, 1)) if n >= 1048576 else ("%d KB" % max(1, round(n / 1024.0)))


def write_tab(idx, checks=None):
    import html as H
    e = lambda s: H.escape(str(s), quote=True)
    rows = idx["parts"]
    inst_groups = ("01", "02", "03", "04", "05", "07")
    inst = [r for r in rows if r["group"] in inst_groups]
    tools = [r for r in rows if r["group"] in ("06", "08", "09")]
    extra = [r for r in rows if r["group"] == "EX"]
    ply = [r for r in rows if r["group"] == "PLY"]
    n_inst = sum(r["qty"] for r in inst)
    mass_inst = sum((r["mass_g"] or 0) * r["qty"] for r in inst)
    jig_min = sum(r["print_min_est"] or 0 for r in tools)
    jig_g = sum(r["mass_g_print_est"] or 0 for r in tools)
    out = []
    w = out.append
    w('<section class="page" id="p-partdwg" hidden>')
    w('<h2>부품 도면·출력 파일</h2>')
    w('<p class="lede">출력하는 파일마다, 그리고 합판 조각마다 치수 도면을 한 장씩 만들었습니다. 모든 선과 숫자는 출력 파일(STL)과 CAD 입체에서 직접 쟀습니다. '
      '카드의 <b>파일 받기</b>를 누르면 STL·DXF·SVG·구멍표·좌표표가 든 zip 하나를 받습니다. DXF는 1:1(mm)이라 CAD에 바로 불러올 수 있습니다. '
      '카드의 <b>3D</b>를 누르면 그 STL 하나가 베드에 놓인 모양(= 한 번에 뽑는 단위)과 악기 안에 들어가는 자리를 3D로 봅니다.</p>')
    w('<div class="kfs">')
    for big, small in (("%d장" % len(rows), "도면 (출력 파일 %d + 합판 조각 %d)" % (len(rows) - len(ply), len(ply))),
                       ("%d파일 · %d개" % (len(inst), n_inst), "악기에 들어가는 출력물 (01~05, 07)"),
                       ("%s kg" % fnum(mass_inst / 1000.0, 2), "악기 출력물 PETG 합계 (속 100 %% 계산값)"),
                       ("%d파일" % len(tools), "공구·지그 (06 · 08 · 09), 지그 출력 약 %d분 · %d g 추정" % (round(jig_min), round(jig_g))),
                       ("%d조각" % len(ply), "합판 (오꾸메 11.5T 400 × 1200 한 장)"),
                       ("%d파일" % len(extra), "선택·대안·예비 (stl/print_extra)")):
        w('<div class="kf"><b>%s</b><span>%s</span></div>' % (e(big), e(small).replace("%%", "%")))
    w('</div>')
    # 3D overview (2026-10-30): the instrument painted by print file (script.js V3, fin/parts3d by part_meshes.py)
    w('<div class="card partdwg-ov" id="partdwg-ov">')
    w('<div class="partdwg-ovhead"><h3>출력 단위 3D</h3><p class="small muted">악기 전체를 <b>출력 파일(STL)마다 다른 색</b>으로 칠했습니다. '
      '색은 묶음(건반·레버·프레임 …)마다 계열이 같고 파일마다 밝기가 다릅니다. 같은 파일을 여러 개 뽑는 조각은 같은 색이고, 회색 반투명은 사서 쓰는 부품입니다. '
      '조각을 누르면 어떤 파일을 몇 개 뽑는지 나오고, 위의 묶음 거르기를 고르면 그 묶음만 칠합니다. <b>벌려 보기</b>는 겹쳐 있는 출력물 '
      '(바닥틀 · 가이드탭 · 레버틀 · 레버 · 건반, 뚜껑)을 위로 띄워 나눠 보여 줍니다.</p></div>')
    w('<div class="partdwg-ovstage" id="partdwg-ovstage" role="img" aria-label="악기 전체 3D, 출력 파일마다 다른 색">'
      '<p class="partdwg-v3load">3D 모델을 불러오는 중…</p></div>')
    w('<div class="partdwg-ovbar"><button type="button" data-v3="ex" aria-pressed="false">벌려 보기</button>'
      '<button type="button" data-v3="buy" aria-pressed="true">산 부품</button><button type="button" data-v3="home">처음 시점</button>'
      '<span class="small muted partdwg-v3hint"></span></div>')
    w('<div class="partdwg-ovleg small"></div>')
    w('<div class="partdwg-ovinfo small" aria-live="polite">조각을 누르면 그 조각을 뽑는 출력 파일이 나옵니다.</div>')
    w('</div>')
    w('<div class="note"><b>읽는 법.</b> 3각법입니다: 평면도(위에서) 아래에 정면도(앞에서), 그 오른쪽에 우측면도(오른쪽에서)가 있습니다. '
      '보이는 선은 실선, 숨은 선은 점선입니다. 파란 숫자는 <b>부품 기준 좌표</b>로, 원점은 도면 자세에서 가장 작은 모서리(0, 0, 0)입니다. '
      '도면 자세는 악기 안에 놓인 자세입니다(기울어 붙는 부품은 기울기를 빼고 그리고 각도를 적음). 구멍표의 <b>월드 좌표</b>는 악기 전체 좌표 '
      '(x 가로, 0 = A0 왼쪽 끝 · y 흰 건반 앞 끝에서 뒤로 · z 책상에서 위로)입니다. 출력할 때 베드에 놓는 자세는 각 도면 오른쪽 위 그림에 있습니다. '
      '같은 축 위에 겹친 구멍(계단 구멍, 원뿔+구멍)은 꼬리표 하나에 함께 적습니다(예: H1/H3). 시트에 자리가 모자라 뺀 모서리 좌표는 개수를 시트 메모에 적었고, '
      'zip의 <b>좌표 CSV</b>와 DXF 레이어 <b>DIM_MORE</b>에 전부 있습니다. DXF의 숨은 선은 HIDDEN 점선 레이어입니다.</div>')
    w('<div class="card partdwg-all"><div><b>한 번에 받기</b><p class="small muted">출력할 파일 전부(stl/print, %d개)와 도면 DXF 전부(%d개)입니다.</p></div>'
      % (idx["all_stl"]["files"], idx["all_dxf"]["files"]))
    w('<div class="partdwg-allbtns">')
    w('<button type="button" class="partdwg-btn" data-act="dl" data-zip="%s" data-zipname="%s" data-zipbytes="%d">전체 STL zip <span class="mono">%s</span></button>'
      % (e(idx["all_stl"]["path"]), e(idx["all_stl"]["name"]), idx["all_stl"]["bytes"], _kb(idx["all_stl"]["bytes"])))
    w('<button type="button" class="partdwg-btn" data-act="dl" data-zip="%s" data-zipname="%s" data-zipbytes="%d">전체 DXF zip <span class="mono">%s</span></button>'
      % (e(idx["all_dxf"]["path"]), e(idx["all_dxf"]["name"]), idx["all_dxf"]["bytes"], _kb(idx["all_dxf"]["bytes"])))
    w('</div><p class="small partdwg-msg" aria-live="polite"></p></div>')
    # filters
    counts = collections.Counter(r["group"] for r in rows)
    w('<div class="partdwg-tools">')
    w('<div class="partdwg-chips" role="group" aria-label="묶음으로 거르기">')
    w('<button type="button" data-g="all" aria-pressed="true">전체 <span class="n">%d</span></button>' % len(rows))
    for g in [x["id"] for x in idx["groups"]]:
        if counts.get(g):
            lab = {"PLY": "합판", "EX": "선택·대안·예비"}.get(g, FOLDER_KO[g])
            w('<button type="button" data-g="%s" aria-pressed="false">%s <span class="n">%d</span></button>' % (g, e(lab), counts[g]))
    w('</div>')
    w('<label class="partdwg-search"><span class="partdwg-sr">부품 찾기</span><input type="search" id="partdwg-q" autocomplete="off" '
      'placeholder="이름·번호·파일 찾기 (예: 백건, P-05, XT60)"></label>')
    w('</div>')
    w('<p class="small muted" id="partdwg-count" aria-live="polite">%d장 보임</p>' % len(rows))
    w('<div id="partdwg-list">')
    cur = None
    for r in rows:
        if r["group"] != cur:
            if cur is not None:
                w('</div>')
            cur = r["group"]
            lab = FOLDER_KO[cur]
            sub = {"PLY": "D06 재단도의 조각을 하나씩, 1:1", "EX": "stl/print_extra — 구매 목록대로면 뽑지 않음 (예비 건반은 필요할 때)",
                   "06": "건반 액션 조립 공구", "08": "합판 구멍 지그 (cad/jigs/README.md)", "09": "BE163 만능기판 자르기·뚫기 지그"}.get(cur, "stl/print/" + r["folder"])
            w('<h3 class="partdwg-gh" data-g="%s">%s <span class="small muted">%s · %d장</span></h3>' % (cur, e(lab), e(sub), counts[cur]))
            w('<div class="partdwg-grid" data-g="%s">' % cur)
        q = " ".join([r["code"], r["name"], r["name"].replace(" ", ""), r["file"] or "", r["material"], " ".join(r["ids"][:8])]).lower()
        size = " × ".join(fnum(v, 2) for v in r["draw_ext"])
        mass = ("%s g" % fnum(r["mass_g"], 1)) if r["mass_g"] is not None else "—"
        if r.get("mass_g_print_est"):
            mass += " (출력 약 %s g)" % fnum(r["mass_g_print_est"], 0)
        if r["kind"] == "ply":
            mass = "부피 %s cm³" % fnum(r["volume_cm3"], 1)
        w('<article class="partdwg-card" id="partdwg-%s" data-g="%s" data-q="%s" data-code="%s" data-name="%s" data-file="%s" data-svg="%s" data-zip="%s" data-zipname="%s" data-zipbytes="%d" data-place="%d">'
          % (r["code"], r["group"], e(q), r["code"], e(r["name"]), e(r["file"] or ""), e(r["svg"]), e(r["zip"]), e(r["zip_name"]), r["bytes"]["zip"],
             1 if r["ids"] else 0))
        w('<button type="button" class="partdwg-thumb" data-act="view" aria-label="%s %s 도면 크게 보기"><img src="%s" alt="%s %s 부품도 (%s, %s)" loading="lazy" decoding="async"></button>'
          % (r["code"], e(r["name"]), e(r["svg"]), r["code"], e(r["name"]), r["sheet"], r["scale"]))
        w('<div class="partdwg-body">')
        w('<div class="partdwg-code mono">%s · %s %s%s</div>' % (r["code"], r["sheet"], r["scale"], " · 선택" if r["extra"] else ""))
        w('<h4>%s</h4>' % e(r["name"]))
        w('<dl class="partdwg-dl"><dt>수량</dt><dd>%s</dd><dt>크기</dt><dd class="mono">%s</dd><dt>%s</dt><dd>%s</dd><dt>재료</dt><dd>%s</dd><dt>구멍·포켓</dt><dd>%d</dd></dl>'
          % (e(r["qty_txt"]), size, "부피" if r["kind"] == "ply" else "질량", e(mass), e(r["material"]), r["holes"]))
        w('<div class="partdwg-file mono">%s</div>' % e(r["file"] or ("합판 조각 · CAD " + ", ".join(r["ids"]))))
        if r["note"]:
            w('<details class="spec"><summary>%s</summary><p class="small">%s</p></details>' % ("가공 메모" if r["kind"] == "ply" else "출력 메모", e(r["note"])))
        w('<div class="partdwg-act"><button type="button" class="partdwg-btn" data-act="view">도면 크게</button>'
          '<button type="button" class="partdwg-btn" data-act="v3d" aria-label="%s %s 3D로 보기">3D</button>'
          '<button type="button" class="partdwg-btn pri" data-act="dl">파일 받기 <span class="mono">.zip %s</span></button></div>'
          % (r["code"], e(r["name"]), _kb(r["bytes"]["zip"])))
        w('<p class="small partdwg-msg" aria-live="polite"></p>')
        w('</div></article>')
    w('</div>')
    w('</div>')
    w('<p class="small muted partdwg-empty" hidden>찾는 부품이 없습니다. 거르기를 "전체"로 바꾸거나 다른 낱말로 찾아 보세요.</p>')
    # viewer
    w('<div class="partdwg-viewer" id="partdwg-viewer" hidden role="dialog" aria-modal="true" aria-labelledby="partdwg-vtitle">')
    w('<div class="partdwg-vbar"><b id="partdwg-vtitle"></b>'
      '<span class="partdwg-mode" role="group" aria-label="보기"><button type="button" data-m="dwg" aria-pressed="true">도면</button>'
      '<button type="button" data-m="print" aria-pressed="false">3D 출력 모양</button><button type="button" data-m="place" aria-pressed="false">3D 조립 자리</button></span>'
      '<span class="partdwg-zoom" role="group" aria-label="확대"><button type="button" data-z="1" aria-pressed="true">맞춤</button>'
      '<button type="button" data-z="2" aria-pressed="false">2배</button><button type="button" data-z="4" aria-pressed="false">4배</button></span>'
      '<span class="partdwg-vnav"><button type="button" data-v="prev" aria-label="이전 도면">이전</button><button type="button" data-v="next" aria-label="다음 도면">다음</button></span>'
      '<a class="partdwg-vopen" id="partdwg-vopen" href="#" target="_blank" rel="noopener">새 탭에서 SVG ↗</a>'
      '<button type="button" class="partdwg-vclose" data-v="close">닫기</button></div>')
    w('<div class="partdwg-vbody" id="partdwg-vbody"><img id="partdwg-vimg" alt=""></div>')
    w('<div class="partdwg-v3d" id="partdwg-v3d" hidden role="img" aria-label="부품 3D">'
      '<p class="partdwg-v3load">3D 모델을 불러오는 중…</p><div class="partdwg-v3info small" aria-live="polite"></div>'
      '<div class="partdwg-v3btns"><button type="button" data-v3="home">처음 시점</button>'
      '<button type="button" data-v3="ex" aria-pressed="false">벌려 보기</button><button type="button" data-v3="buy" aria-pressed="true">산 부품</button></div>'
      '<p class="partdwg-v3hint small"></p></div>')
    w('</div>')
    w('<p class="small muted">원본: hardware/mechanical/cad/src/part_sheets.py (출력 파일 + build_all.collect() 입체) → hardware/mechanical/cad/drawings/parts/ (svg · dxf · data). '
      '%s 기준.</p>' % DATE)
    w('</section>')
    os.makedirs(TAB, exist_ok=True)
    open(os.path.join(TAB, "section.html"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    assets = []
    for r in rows:
        assets += [r["svg"], r["zip"]]
    assets += [idx["all_stl"]["path"], idx["all_dxf"]["path"], "fin/parts/index.json"]
    import part_meshes
    assets += part_meshes.assets(part_meshes.build(idx)) + ["cad/toccata.glb.b64.txt"]      # 3D views (2026-10-30)
    open(os.path.join(TAB, "assets.txt"), "w", encoding="utf-8").write("\n".join(assets) + "\n")
    return len(out)


def write_meta(idx, ver, rows):
    t = ver["totals"]
    data = [json.load(open(os.path.join(PDIR, "data", r["code"] + ".json"), encoding="utf-8")) for r in rows]
    ovl = sum(len(d["overlaps"]) for d in data)
    cut = [d["code"] for d in data if d["table_cut"]]
    fails = {c: r["fails"] for c, r in ver["parts"].items() if r["fails"]}
    total = 0
    for root, _d, fns in os.walk(FIN):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in fns)
    notes = [
        "Built by hardware/mechanical/cad/src/part_sheets.py (python3 hardware/mechanical/cad/src/part_sheets.py; ~3 min). Never runs build_all.main(); only build_all.collect().",
        "%d sheets: %d print files (stl/print 01-09 incl. 06 tools, 08 plywood jigs, 09 perfboard jigs) + %d print_extra files (group EX) + %d plywood pieces (group PLY)."
        % (len(rows), sum(1 for r in rows if r["group"] not in ("EX", "PLY")), sum(1 for r in rows if r["group"] == "EX"), sum(1 for r in rows if r["group"] == "PLY")),
        "FIXES 2026-10-08 (review): (1) DXF layer HIDDEN now uses a real dashed linetype HIDDEN (defined in the file: dash 2.0 / gap 1.0 mm; ezdxf setup has no HIDDEN, it used to fall back to CONTINUOUS); plywood DRILL_BLIND too. "
        "(2) hole tags: holes on one axis line in the same view share ONE tag (e.g. 'H1/H3', 'H4~H8'), every tag/section letter is placed at the first free spot around its hole (8 corners/sides, inside big openings, then short leaders) and registered in the layout check; the sheet notes list the shared tags. "
        "(3) every edge coordinate the views found is kept: the sheet notes say how many were left off ('모서리 좌표 N개는 시트에서 생략 ...'), all of them are in <base>_좌표.csv in each zip (axis, coord, edge length, on_sheet, world axis/value) and as ordinate DIMENSIONs on DXF layer DIM_MORE. "
        "(4) plywood shop rectangles printed with 2 decimals like D06 (139.65, 56.35, 14.14) in sheet, DXF text and readme. (5) zip readme had literal '\\r\\n' and the CSVs a literal '\\ufeff' (escaping bug): now real CRLF and BOM; file names keep '-' (C#·D# -> Cs-Ds). "
        "(6) style.css: chips and main buttons min-height 44px under pointer:coarse. "
        "Card ids: partdwg-<code> (P-01-01 .. P-09-02, P-EX-01..21, P-PLY-01..10). Other tabs map a print file to its code with fin/parts/index.json by_file (key = 'hardware/mechanical/cad/stl/print/...') or window.toccata.partdwg.codeOf(file); window.toccata.partdwg.open(code) opens the viewer.",
        "FIXES 2026-10-08 round 2 (review 'hole tables'): (a) the slice levels lost the TOP vertex interval of every part (float32 top face 44.849998 vs vertex plane rounded to 44.85 > ext) and capped the levels at 320: now one level in every interval (no cap below 2000), so blind holes that start at the top face are found -- P-05-17/18 Ø4.2 x 4.5 insert holes (world x506|716, y246/322, z61.35) and P-05-12/13 magnet pocket Ø8 teardrop x 3.2 at (5.75, 61) (world 265.75|956.25, 275) are in the tables; the '없음' claim is gone. "
        "(b) a fitted circle must match the ring's own box (circle inside the box, one side = Ø, both for 'round'): the P-03-01/02 lever bay (39.16x63.85, 45.6x63.85) and the P-06-03 pocket (40.4x19.4) are no longer 'Ø71/Ø75/Ø41 teardrop'; 'rect' only for true rectangles (area > 99.8 % of the box), others 'other' with box + bbox centre, and the outline at mid depth in the CSV. "
        "(c) engraved letters (any outline incl. 'O' rings and dots, <= 1.05 deep at the CAD depths 0.4/0.5/0.6/0.8, <= 8 x 8, one end open straight to the air, not stacked on a deeper void) get no hole number: P-02 note names, P-04 pad bar labels, P-06/08/09 tool and jig labels; the sheet note says '새김 글자 (깊이 ..) N곳' and the CSV lists them as '새김'. "
        "(d) cones/changing pieces run between vertex planes and their Ø is taken AT the end planes: P-05-19 / P-05-21 countersinks Ø4.5->Ø8.59, z1.957~4.0 (was Ø6.59, z1.985~3.008); straight ends snap to the vertex plane (1.957, not 1.985). "
        "(e) islands standing in a pocket are measured and part of the group key: P-05-16 H8 '사각 38x36 +섬' (island 20.4x18 at x37.1~57.5, y3.55~21.55) is split from its empty twin (the reviewer's '20.4x18 pocket' is that solid island, the opening itself is 38x36). "
        "(f) pattern notes print sizes to 0.01 (P-03-01 'H3 Ø1.95 x12', was 'Ø2 x11 · Ø1.9'). (g) the duplicate filter only drops a void seen along two axes when the boxes cover each other (> half of the bigger extent): the key hollows that used to vanish behind a small front pocket are listed. (h) pieces thinner than 0.25 and slivers of voids that open elsewhere are counted in a note ('짧은 경사 조각'), not numbered. ",
        "PUBLISH: the page must declare capabilities {downloads: true} for the zip buttons (claude.use('downloads') -> save({filename:'*.zip', data: Blob})); without it the buttons show the file name/size and a note.",
        "3D (2026-10-30, user: '부품 도면을 보는 곳에도 3D 모델링을 둬서 3D 프린팅을 어떤 단위로 하는 건지 볼 수 있게'): the viewer has three modes "
        "(도면 / 3D 출력 모양 = the STL on the 256 x 256 P1S bed as it prints, print aids such as the key combs and the bed posts in orange / "
        "3D 조립 자리 = the instrument with this file's instances in blue), every card has a 3D button, and the overview card '출력 단위 3D' paints "
        "the whole instrument by print file (hue per folder, lightness per file; group chips filter it; 벌려 보기 lifts the stacked prints). "
        "Data: fin/parts3d/g-<group>.json + index.json from part_meshes.py (run by write_tab; ids printed in pieces, CU-PLY-BOTTOM / CU-PLY-BACK, "
        "are drawn from their piece STLs placed by body.lap_pieces), assembly = the 04 tab's cad/toccata.glb.b64.txt. "
        "python3 part_sheets.py --tab rebuilds only the fragment + meshes from fin/parts/index.json (seconds).",
        "Assets: %d files in fin/parts (%s MB): per part <code>.svg (sheet, lazy <img>) + <code>.zip.b64.txt (STL exact bytes + DXF + SVG + hole CSV + readme), all_stl.zip.b64.txt (= hardware/mechanical/cad/Toccata_출력STL_전체.zip, matches stl/print: %s), all_dxf.zip.b64.txt, index.json."
        % (len(os.listdir(FIN)), fnum(total / 1048576.0, 1), idx["all_stl"]["matches_stl_print"]),
        "CHECKS (independent, trimesh instead of manifold3d; drawings/parts/verify.json): %d/%d parts pass. bbox of the STL in drawing pose vs sheet size: %d parts, max err %s mm; "
        "%d ordinate values each lie on a vertex plane of the STL (tol 0.011); %d straight round holes re-measured by trimesh section + own circle fit (centre and Ø, tol max(0.02, 0.03 %% of Ø)), max err %s mm; "
        "world placement: %d parts drawing box mapped by W == CAD instance bbox (tol 0.02), %d hole middles mapped to world are not inside the CAD instance; every zip holds the exact STL bytes (sha1), DXF parses with units mm and layers VISIBLE/HIDDEN/SECTION/DIM/DIM_MORE/TEXT; every SVG parses as XML. "
        "New checks: all %d edge coordinates (sheet + %d left off the sheet, = coordinate CSV rows = DXF DIM_MORE dimension count per part) lie on STL vertex planes; DXF layer HIDDEN uses a linetype with gaps (no CONTINUOUS) on every file; "
        "independent text-box overlap over EVERY <text> of every sheet SVG (not only the registered boxes; same font metric): %d overlapping pairs in total, %d involving hole tags, %d sheets with any overlap; readme CRLF and CSV BOM checked in every zip. "
        "Round-2 checks (trimesh, independent of the finder's levels): %d straight holes/pockets of the tables re-measured on a section at mid depth, outline box max err %s mm, and every 'Ø' / 'teardrop' word checked against that box; "
        "completeness: %d closed inner loops of dense sections (every vertex plane +-0.3 inside the part + a 1 mm grid, x/y/z) -> %d not inside a listed hole, engraving or fragment."
        % (t.get("parts", 0) - t.get("parts_failed", 0), t.get("parts", 0), t.get("bbox", 0),
           fnum(max(r.get("bbox_err", 0) for r in ver["parts"].values()), 4), t.get("ords", 0), t.get("holes", 0),
           fnum(max(r.get("hole_err", 0) for r in ver["parts"].values()), 4), t.get("world_bbox", 0), t.get("world_holes", 0),
           t.get("ords_all", 0), t.get("ords_more", 0), t.get("text_overlaps", 0), t.get("tag_overlaps", 0), t.get("sheets_with_overlaps", 0),
           t.get("boxes", 0), fnum(max(r.get("box_err", 0) for r in ver["parts"].values()), 4), t.get("loops", 0), t.get("loops_uncovered", 0)),
        "Failures: %s." % (json.dumps(fails, ensure_ascii=False) if fails else "none"),
        "Layout self-check (registered text boxes incl. hole tags and section letters, drawings.Sheet.check): %d overlaps left over all sheets; tags with no free spot (forced): %d; dimensions / angle marks whose text would collide are skipped (their values stay in the notes); hole tables cut (rest in holes.csv/DXF): %s."
        % (ovl, sum(d.get("tags_forced", 0) for d in data), ", ".join(cut) or "none"),
        "Limits: hole finder = closed inner rings of x/y/z slices (holes open to a side, e.g. the sideways M3 nut slot at the white-key tail, show in the views / sections, not in the table); 'other' outlines are given as box + centre on the sheet and as the full outline in the hole CSV; islands are measured at mid depth; engraved letters are counted in the notes, not numbered; "
        "lever carrier files contain the breakaway support (drawn, noted); 04 pad bars are the PORON 5T files (the assembly model is the 6T design, world coords via ICP on the common faces); "
        "tools/jigs have no world coords; plywood sheets reuse drawings.py D06 logic (flat_piece, piece_memo, ply_spots, ply_jigs).",
    ]
    meta = dict(tab="partdwg", notes=" ".join(notes), capabilities={"downloads": True},
                api="window.toccata.partdwg = {open(code, mode), codeOf(file)}; mode 'dwg' (default) | 'print' | 'place'",
                index="fin/parts/index.json",
                checks=dict(totals=t, failures=fails, overlaps=ovl))
    json.dump(meta, open(os.path.join(TAB, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return meta


# ------------------------------------------------------------------ independent checks

def svg_text_overlaps(svg_text, tol=0.15):
    """every <text> of a sheet SVG (not only the boxes the layout registered) -> overlapping pairs [(a, b, class a, class b)].
    Boxes from the same font metric as the layout (drawings.text_w); text along slanted dimension lines is skipped."""
    import xml.etree.ElementTree as ET
    ns = "{http://www.w3.org/2000/svg}"
    B = []
    for t in ET.fromstring(svg_text).iter(ns + "text"):
        s_ = "".join(t.itertext())
        x, y, size = float(t.get("x")), float(t.get("y")), float(t.get("font-size"))
        anc = t.get("text-anchor", "start")
        m = re.match(r"rotate\(([-\d.]+)", t.get("transform", ""))
        rot = float(m.group(1)) if m else 0.0
        w = text_w(s_, size)
        if rot == 0:
            x0 = x if anc == "start" else (x - w / 2 if anc == "middle" else x - w)
            b = (x0, y - 0.78 * size, x0 + w, y + 0.22 * size)
        elif abs(rot + 90) < 1e-6:
            y0, y1 = {"start": (y - w, y), "end": (y, y + w)}.get(anc, (y - w / 2, y + w / 2))
            b = (x - 0.78 * size, y0, x + 0.22 * size, y1)
        else:
            continue
        B.append((b, s_, t.get("class", "")))
    bad = []
    for i in range(len(B)):
        a, sa, ca = B[i]
        for j in range(i + 1, len(B)):
            b, sb, cb = B[j]
            if a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol:
                bad.append((sa, sb, ca, cb))
    return bad


def tm_inner_loops(tm, axis, heights):
    """trimesh sections along one axis at the given heights -> per height [(P (n, 2) in the in-plane axes, area)] of the
    loops that bound a void (odd nesting depth). Independent of manifold3d and of the finder's levels."""
    i = AX.index(axis)
    iu, iv = PLANE_AX[axis]
    n = np.zeros(3)
    n[i] = 1.0
    secs = tm.section_multiplane(plane_origin=[0.0, 0.0, 0.0], plane_normal=n, heights=list(map(float, heights)))
    out = []
    for s_ in secs:
        if s_ is None:
            out.append([])
            continue
        T = np.asarray(s_.metadata["to_3D"])
        loops = []
        for L in s_.discrete:
            L = np.asarray(L, float)
            if len(L) < 4:
                continue
            P3 = (T[:3, :3] @ np.c_[L, np.zeros(len(L))].T).T + T[:3, 3]
            P = P3[:, [iu, iv]]
            if np.allclose(P[0], P[-1]):
                P = P[:-1]
            loops.append(P)
        if not loops:
            out.append([])
            continue
        bb = np.array([[P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()] for P in loops])
        res = []
        for k, P in enumerate(loops):
            par = 0
            inside_bb = (bb[:, 0] <= bb[k, 0] + 1e-6) & (bb[:, 1] >= bb[k, 1] - 1e-6) & (bb[:, 2] <= bb[k, 2] + 1e-6) & (bb[:, 3] >= bb[k, 3] - 1e-6)
            inside_bb[k] = False
            for j in np.nonzero(inside_bb)[0]:
                if _point_in_polys([loops[j]], float(P[0, 0]), float(P[0, 1])):
                    par += 1
            if par % 2 == 1:
                res.append((P, abs(signed_area(P))))
        out.append(res)
    return out


def verify(ctx=None, codes=None):
    """re-measure with trimesh (not manifold3d): bounding boxes, round-hole centres + diameters (trimesh sections + own circle
    fit), ordinates on real vertex planes, world placement (the drawing box mapped by W vs the CAD instance bbox, hole
    middle not inside the instance), zip = exact STL bytes, SVG / DXF parse. -> dict written to drawings/parts/verify.json."""
    import hashlib
    import trimesh
    import ezdxf
    import xml.etree.ElementTree as ET
    idx = json.load(open(os.path.join(FIN, "index.json"), encoding="utf-8"))
    rows = {r["code"]: r for r in idx["parts"]}
    by_id = {}
    if ctx is not None:
        by_id = {p.id: p for p in ctx.parts}
    res = collections.OrderedDict()
    tot = collections.Counter()
    for code, r in rows.items():
        if codes and code not in codes:
            continue
        d = json.load(open(os.path.join(PDIR, "data", code + ".json"), encoding="utf-8"))
        rep = dict(code=code, name=r["name"], fails=[])
        Q, o = np.array(d["Q"]), np.array(d["o"])
        if d["kind"] == "print":
            tm = trimesh.load(os.path.join(CAD, d["file"]), process=True)
        else:
            p = by_id.get(d["inst"])
            if p is None:
                continue
            V, F = mesh_arrays(p.solid)
            tm = trimesh.Trimesh(V, F, process=True)
        T = np.eye(4)
        T[:3, :3] = Q
        T[:3, 3] = -o
        tm.apply_transform(T)
        ext = tm.bounds[1] - tm.bounds[0]
        e_bb = float(np.abs(ext - np.array(d["ext"])).max())
        e_min = float(np.abs(tm.bounds[0]).max())
        rep["bbox_err"] = round(max(e_bb, e_min), 4)
        tot["bbox"] += 1
        if rep["bbox_err"] > 0.01:
            rep["fails"].append("bbox %.4f" % rep["bbox_err"])
        # ordinates lie on vertex planes
        V = tm.vertices
        bad = 0
        n_ord = 0
        for ax, i in (("x", 0), ("y", 1), ("z", 2)):
            for c in d["ords"][ax]:
                n_ord += 1
                if np.abs(V[:, i] - c).min() > 0.011:
                    bad += 1
        rep["ords"] = n_ord
        rep["ords_bad"] = bad
        tot["ords"] += n_ord
        if bad:
            rep["fails"].append("%d ordinates off vertex planes" % bad)
        # every edge coordinate (sheet + DIM_MORE / coordinate CSV) lies on a vertex plane too
        bad_all, n_all, n_more = 0, 0, 0
        for ax, i in (("x", 0), ("y", 1), ("z", 2)):
            for c, _w, on in d.get("ords_all", {}).get(ax, []):
                n_all += 1
                n_more += 0 if on else 1
                if np.abs(V[:, i] - c).min() > 0.011:
                    bad_all += 1
        rep["ords_all"] = n_all
        rep["ords_more"] = n_more
        tot["ords_all"] += n_all
        tot["ords_more"] += n_more
        if bad_all:
            rep["fails"].append("%d coordinate-CSV values off vertex planes" % bad_all)
        # round straight holes: trimesh section at mid depth, interior rings, circle fit
        hc = 0
        herr = 0.0
        for h in d["holes"]:
            if h["shape"] != "round" or h["kind"] != "straight":
                continue
            ia = AX.index(h["axis"])
            iu, iv = PLANE_AX[h["axis"]]
            mid = (h["lo"] + h["hi"]) / 2
            n = np.zeros(3)
            n[ia] = 1.0
            org = np.zeros(3)
            org[ia] = mid
            sec_ = tm.section(plane_origin=org, plane_normal=n)
            if sec_ is None:
                rep["fails"].append("%s: no section" % h["no"])
                continue
            best = None
            for ent in sec_.discrete:
                P = np.asarray(ent)[:, [iu, iv]]
                if len(P) < 8:
                    continue
                cx, cy, rr, mres = circle_fit(P[:-1] if np.allclose(P[0], P[-1]) else P)
                dd = math.hypot(cx - h["cu"], cy - h["cv"]) + abs(2 * rr - h["d"])
                if best is None or dd < best[0]:
                    best = (dd, cx, cy, 2 * rr)
            if best is None:
                rep["fails"].append("%s: no ring" % h["no"])
                continue
            e = max(abs(best[1] - h["cu"]), abs(best[2] - h["cv"]), abs(best[3] - h["d"]))
            herr = max(herr, e)
            hc += 1
            if e > max(0.02, 3e-4 * h["d"]):          # float32 STL: 0.02 or 0.03 % of the diameter
                rep["fails"].append("%s: hole off by %.3f" % (h["no"], e))
        rep["holes_checked"] = hc
        rep["hole_err"] = round(herr, 4)
        tot["holes"] += hc
        # every straight hole / pocket of the table: its outline box re-measured on a trimesh section at mid depth, and the
        # shape word checked against that box ('round' = as wide as Ø both ways; 'teardrop' = one side = Ø and the circle
        # inside the box) -> catches 'Ø71 teardrop' for a 39 x 64 opening
        nb, berr = 0, 0.0
        for h in d["holes"]:
            if h["kind"] != "straight" or "box" not in h:
                continue
            mid = (h["lo"] + h["hi"]) / 2
            lp = tm_inner_loops(tm, h["axis"], [mid])[0]
            if not lp:
                rep["fails"].append("%s: no inner loop at mid depth" % h["no"])
                continue
            hb = np.array(h["box"])
            bb = min((np.array([P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()]) for P, _a in lp),
                     key=lambda b: float(np.abs(b - hb).max()))
            e = float(np.abs(bb - hb).max())
            berr = max(berr, e)
            nb += 1
            if e > 0.02:
                rep["fails"].append("%s: box off by %.3f" % (h["no"], e))
            w_, h_ = bb[1] - bb[0], bb[3] - bb[2]
            if h["shape"] in ("round", "tear"):
                tol = max(0.1, 0.01 * h["d"])
                if h["shape"] == "round" and (abs(w_ - h["d"]) > tol or abs(h_ - h["d"]) > tol):
                    rep["fails"].append("%s: 'Ø%.2f' but the outline is %.2f x %.2f" % (h["no"], h["d"], w_, h_))
                if h["shape"] == "tear" and (min(abs(w_ - h["d"]), abs(h_ - h["d"])) > tol or min(w_, h_) < h["d"] - tol):
                    rep["fails"].append("%s: 'Ø%.2f teardrop' but the outline is %.2f x %.2f" % (h["no"], h["d"], w_, h_))
        rep["boxes_checked"] = nb
        rep["box_err"] = round(berr, 4)
        tot["boxes"] += nb
        # completeness: dense trimesh sections (every vertex plane +-0.3 inside the part + a 1 mm grid, along x, y and z);
        # every closed inner loop (>= 0.3 mm2) must sit in a reported hole / pocket, engraving or listed fragment
        boxes = [h["box3"] for h in d["holes"] if "box3" in h] + [e_["box3"] for e_ in d.get("engr", [])] + [f_["box3"] for f_ in d.get("frag", [])]
        B0 = np.array([b[0] for b in boxes]).reshape(-1, 3) - 0.15
        B1 = np.array([b[1] for b in boxes]).reshape(-1, 3) + 0.15
        unc, nl = [], 0
        for ax in "xyz":
            i = AX.index(ax)
            iu, iv = PLANE_AX[ax]
            ext_i = float(tm.bounds[1][i])
            planes = np.unique(np.round(V[:, i], 3))
            cand = np.r_[planes - 0.3, planes + 0.3, np.arange(0.5, ext_i, 1.0)]
            cand = np.unique(np.round(cand[(cand > 0.05) & (cand < ext_i - 0.05)], 3))
            near = np.abs(planes[np.clip(np.searchsorted(planes, cand), 0, len(planes) - 1)] - cand)
            near = np.minimum(near, np.abs(planes[np.clip(np.searchsorted(planes, cand) - 1, 0, len(planes) - 1)] - cand))
            cand = cand[near > 0.003]
            for c, lp in zip(cand, tm_inner_loops(tm, ax, cand)):
                for P, a_ in lp:
                    if a_ < 0.3:
                        continue
                    nl += 1
                    p3 = np.zeros(3)
                    p3[i] = c
                    p3[iu], p3[iv] = (P[:, 0].min() + P[:, 0].max()) / 2, (P[:, 1].min() + P[:, 1].max()) / 2
                    if len(boxes) and bool(np.any(np.all((p3 >= B0) & (p3 <= B1), axis=1))):
                        continue
                    unc.append([ax, round(float(c), 3), [round(float(q), 2) for q in p3],
                                round(float(np.ptp(P[:, 0])), 2), round(float(np.ptp(P[:, 1])), 2), round(float(a_), 2)])
        rep["loops_checked"] = nl
        rep["loops_uncovered"] = len(unc)
        tot["loops"] += nl
        tot["loops_uncovered"] += len(unc)
        if unc:
            rep["uncovered"] = unc[:12]
            rep["fails"].append("%d inner loops of the dense sections not in the hole table / engravings / fragments" % len(unc))
        # world placement
        if d["W"] is not None and d["inst"] in by_id:
            W = np.array(d["W"])
            p = by_id[d["inst"]]
            wb = np.array(p.solid.bounding_box())
            if d["tilt"] < 0.05 and d["kind"] == "print" and not d["folder"].startswith(("02", "04", "@extra/대안")):
                corners = np.array([[x, y, z] for x in (0, d["ext"][0]) for y in (0, d["ext"][1]) for z in (0, d["ext"][2])])
                wc = corners @ W[:, :3].T + W[:, 3]
                e = float(max(np.abs(wc.min(0) - wb[:3]).max(), np.abs(wc.max(0) - wb[3:]).max()))
                rep["world_bbox_err"] = round(e, 4)
                tot["world_bbox"] += 1
                if e > 0.02:
                    rep["fails"].append("world bbox %.3f" % e)
            Vw, Fw = mesh_arrays(p.solid)
            tw = trimesh.Trimesh(Vw, Fw, process=False)
            inside = 0
            nh = 0
            for h in d["holes"]:
                if h["shape"] != "round" or h["kind"] != "straight" or (h["d"] or 0) < 1.5:
                    continue
                pm = hole_point(h, "mid")
                wp = W[:, :3] @ pm + W[:, 3]
                nh += 1
                if tw.contains([wp])[0]:
                    inside += 1
            rep["world_holes"] = nh
            rep["world_holes_in_material"] = inside
            tot["world_holes"] += nh
            if inside:
                rep["fails"].append("%d hole centres inside the CAD instance" % inside)
        # zip / svg / dxf
        b64 = open(os.path.join(FIN, code + ".zip.b64.txt")).read()
        zb = base64.b64decode(b64)
        with zipfile.ZipFile(io.BytesIO(zb)) as z:
            names = z.namelist()
            if d["kind"] == "print":
                stl_in = z.read(os.path.basename(d["file"]))
                same = hashlib.sha1(stl_in).hexdigest() == hashlib.sha1(open(os.path.join(CAD, d["file"]), "rb").read()).hexdigest()
                rep["zip_stl_identical"] = same
                if not same:
                    rep["fails"].append("zip STL differs")
            dxf_name = [n for n in names if n.endswith(".dxf")][0]
            doc = ezdxf.read(io.StringIO(z.read(dxf_name).decode("utf-8", "replace")))
            lays = set(l.dxf.name for l in doc.layers)
            need = {"VISIBLE", "HIDDEN", "SECTION", "DIM", "DIM_MORE", "TEXT"}
            if not need <= lays:
                rep["fails"].append("dxf layers missing %s" % (need - lays))
            rep["dxf_units"] = doc.header.get("$INSUNITS")
            if rep["dxf_units"] != 4:
                rep["fails"].append("dxf units")
            # hidden edges must be dashed: layer HIDDEN uses linetype HIDDEN, defined with a gap
            lt_name = doc.layers.get("HIDDEN").dxf.linetype
            lt = doc.linetypes.get(lt_name) if lt_name in doc.linetypes else None
            gaps = [t.value for t in lt.pattern_tags.tags if t.code == 49 and t.value < 0] if lt is not None and lt.pattern_tags else []
            rep["dxf_hidden_linetype"] = "%s (%s)" % (lt_name, "dashed" if gaps else "SOLID")
            if lt_name.upper() == "CONTINUOUS" or not gaps:
                rep["fails"].append("dxf HIDDEN layer not dashed (%s)" % lt_name)
            msp_ = doc.modelspace()
            n_hid = sum(1 for e in msp_ if e.dxf.layer == "HIDDEN" and (e.dxf.get("linetype", "BYLAYER").upper() == "BYLAYER"))
            n_hid_all = sum(1 for e in msp_ if e.dxf.layer == "HIDDEN")
            if n_hid != n_hid_all:
                rep["fails"].append("dxf hidden entities override the layer linetype")
            n_more_dxf = sum(1 for e in msp_.query("DIMENSION") if e.dxf.layer == "DIM_MORE")
            rep["dxf_dim_more"] = n_more_dxf
            if n_more_dxf != n_more:
                rep["fails"].append("dxf DIM_MORE %d != omitted coordinates %d" % (n_more_dxf, n_more))
            # coordinate CSV = every coordinate; readme / CSVs with real line breaks and a real BOM
            ccsv = [n for n in names if n.endswith("_좌표.csv")]
            if not ccsv:
                rep["fails"].append("zip without coordinate CSV")
            else:
                raw = z.read(ccsv[0]).decode("utf-8")
                if not raw.startswith("\ufeff") or raw.count("\n") != n_all + 1:
                    rep["fails"].append("coordinate CSV rows %d != %d" % (raw.count("\n") - 1, n_all))
            rd = z.read("읽어보기.txt").decode("utf-8")
            if "\\r\\n" in rd or "\r\n" not in rd:
                rep["fails"].append("readme line breaks")
            hcsv = [n for n in names if n.endswith("_구멍표.csv")][0]
            if not z.read(hcsv).decode("utf-8").startswith("\ufeff"):
                rep["fails"].append("hole CSV BOM")
        svg_txt = open(os.path.join(FIN, code + ".svg"), encoding="utf-8").read()
        ET.fromstring(svg_txt)
        if svg_txt != open(os.path.join(PDIR, "svg", code + ".svg"), encoding="utf-8").read():
            rep["fails"].append("fin SVG != drawings SVG")
        ov = svg_text_overlaps(svg_txt)
        rep["text_overlaps"] = len(ov)
        rep["tag_overlaps"] = sum(1 for q in ov if "tr" in q[2].split() or "tr" in q[3].split())
        if ov:
            rep["overlap_pairs"] = [[q[0], q[1]] for q in ov[:10]]
        tot["text_overlaps"] += len(ov)
        tot["tag_overlaps"] += rep["tag_overlaps"]
        tot["sheets_with_overlaps"] += 1 if ov else 0
        res[code] = rep
        tot["parts"] += 1
        if rep["fails"]:
            tot["parts_failed"] += 1
    out = dict(date=DATE, totals=dict(tot), parts=res)
    json.dump(out, open(os.path.join(PDIR, "verify.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    main()
