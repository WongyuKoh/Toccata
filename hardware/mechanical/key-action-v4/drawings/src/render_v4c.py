"""Toccata v4 W1+ r4.4 — drawing 14 (printed tools) and drawing 15 (stage-0 coupons / fixtures).

Data : drawing 14 = ../final/tools/tools_geometry.json (tools.*.side / plan prisms, dims T01~T29, model_values);
       the key D / C# phantoms and the frame rail are from ../final/geometry.json (kit).
       drawing 15 = ../final/stage0/stage0_geometry.json (parts: bbox, key_dims, print text, stl path) — the views are
       hidden-line projections of the STL files that stage0_geometry.json lists (same generator run); every number
       written on the sheet is read from stage0_geometry.json (bbox, key_dims, qty, mass).
Draw : a tool prism is (y, z) side polygon x [x0, x1] (or (X, y) plan polygon x [z0, z1]); a projection is painted
       far-to-near (painter's order on x1 / z1), ops add / sub / ref / add_post as in the generator; a section is the
       raster CSG (add - sub + add_post) of the prisms cut by the plane.  Nothing is typed by hand.
run  : called from render_v4.py main (sheets 14, 15).
"""
import json
import math
import os
import re
import struct

import contourpy
import numpy as np
from PIL import Image, ImageDraw

import kit
from kit import (View, fmt_mm, pids, hpoly, fill_rings, stroke_rings, union_rings, rect, bbox, yslice, ordz, ordy,
                 panel_title, note_lines, page, F2, body, pts, fixed, _rdp, circle_pts, scalebar, table)

V4 = kit.V4
TG = json.load(open(os.path.join(V4, "final", "tools", "tools_geometry.json")))
S0DIR = os.path.join(V4, "final", "stage0")
S0 = json.load(open(os.path.join(S0DIR, "stage0_geometry.json")))
TD = {d["id"]: d for d in TG["dims"]}
MV = TG["model_values"]
SHEETS = []
USED_T = set()


def F(v, nd=2):
    return fmt_mm(v, nd)


def T(tid):
    """cite a tool dimension id (T01..T29) -> the id (recorded as used)."""
    assert tid in TD, tid
    USED_T.add(tid)
    return tid


def tnums(tid, field="value"):
    USED_T.add(tid)
    v = TD[tid][field]
    return [float(v)] if isinstance(v, (int, float)) else kit.nums(v)


def tool(name):
    return TG["tools"][name]


def tpart(tl, name, kind="side"):
    for p in tool(tl)[kind]:
        if p["name"].startswith(name):
            return p
    raise KeyError((tl, name, kind))


def tparts(tl, prefix, kind="side"):
    return [p for p in tool(tl)[kind] if p["name"].startswith(prefix)]


# ------------------------------------------------------------------ raster CSG (add - sub + add_post)
def csg_rings(adds, subs=(), posts=(), res=0.02, eps=0.01):
    polys = [p for p in list(adds) + list(subs) + list(posts) if len(p) >= 3]
    if not polys or not adds:
        return []
    allp = np.concatenate([np.asarray(p, float) for p in polys])
    u0, v0 = allp.min(0) - 5 * res
    u1, v1 = allp.max(0) + 5 * res
    W = int((u1 - u0) / res) + 3
    H = int((v1 - v0) / res) + 3
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    tr = lambda p: [((u - u0) / res - 0.5, (v1 - v) / res - 0.5) for u, v in p]
    for p in adds:
        d.polygon(tr(p), fill=255)
    for p in subs:
        d.polygon(tr(p), fill=0)
    for p in posts:
        d.polygon(tr(p), fill=255)
    a = np.asarray(im, dtype=float)
    gen = contourpy.contour_generator(z=a, line_type="Separate")
    rings = []
    for L in gen.lines(127.5):
        w = [(u0 + (c + 1) * res, v1 - (r + 1) * res) for c, r in L]
        if len(w) >= 4:
            rings.append(_rdp(w, eps))
    return rings


def _pip(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def _samples(poly, n=9):
    u0, u1, v0, v1 = bbox(poly)
    out = []
    for i in range(n):
        for j in range(n):
            q = (u0 + (u1 - u0) * (i + 0.5) / n, v0 + (v1 - v0) * (j + 0.5) / n)
            if _pip(q, poly):
                out.append(q)
    return out or [((u0 + u1) / 2, (v0 + v1) / 2)]


# ------------------------------------------------------------------ projections of a tool (exact: solid = side prism ∩ plan prism)
def _ivs_and(a, b):
    out = []
    for p0, p1 in a:
        for q0, q1 in b:
            lo, hi = max(p0, q0), min(p1, q1)
            if hi > lo + 1e-9:
                out.append((lo, hi))
    return out


def _ivs_or(ivs):
    out = []
    for lo, hi in sorted(ivs):
        if out and lo <= out[-1][1] + 1e-9:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def _ivs_minus(a, b):
    out = []
    for lo, hi in a:
        cur = [(lo, hi)]
        for q0, q1 in b:
            nxt = []
            for c0, c1 in cur:
                if q1 <= c0 + 1e-9 or q0 >= c1 - 1e-9:
                    nxt.append((c0, c1))
                    continue
                if q0 > c0 + 1e-9:
                    nxt.append((c0, q0))
                if q1 < c1 - 1e-9:
                    nxt.append((q1, c1))
            cur = nxt
        out += cur
    return out


def solids(tl, skip=()):
    """a tool's parts as solids = extrude(side (y, z) over x) ∩ extrude(plan (X, y) over z), paired by name."""
    plan = {p["name"]: p for p in tool(tl)["plan"]}
    # r4.5 fix: a prism extruded along y (front kind 'py', e.g. the T09 readout-post trapezoid) carries its true (X, z)
    # outline; sections at y use it instead of the x-range x z-range box
    front = {p["name"]: p for p in tool(tl).get("front", []) if p.get("kind") == "py"}
    out = []
    for p in tool(tl)["side"]:
        if any(p["name"].startswith(s_) for s_ in skip):
            continue
        q = plan[p["name"]]
        fr = front.get(p["name"])
        out.append(dict(name=p["name"], op=p["op"], S=[tuple(t) for t in p["side"]], x=tuple(p["x"]),
                        Q=[(t[1], t[0]) for t in q["plan"]], z=tuple(q["z"]),       # Q as (y, X) for slicing at y
                        F=[tuple(t) for t in fr["front"]] if fr else None, Fy=tuple(fr["y"]) if fr else None))
    return out


def _col(sol, y, view):
    """(row intervals, depth intervals) of a solid on the column at y: side view rows = z, depth = X;
    plan view rows = X, depth = z."""
    zi = _ivs_and(yslice(sol["S"], y), [sol["z"]])
    xi = _ivs_and(yslice(sol["Q"], y), [sol["x"]])
    return (zi, xi) if view == "side" else (xi, zi)


MATCLS = {"print": "m-print2", "steel": "m-steel"}


def render_solids(v, P, sols, view, u0, u1, r0, r1, res=0.03, hidden=True, flip_rows=False, transpose=False, tol=0.25):
    """exact hidden-surface projection of the solids (add - sub) + add_post + ref, seen from +X (view 'side',
    u = y, rows = z) or from +z (view 'plan', u = y, rows = X drawn at v = -X when flip_rows; transpose -> u = X).
    Visible column segments are grouped into faces (union-find): coplanar segments of one material join, and a
    curved surface of one part joins while its depth changes by < tol between neighbours.  Each face is filled and
    outlined; subs / refs not fully in sight get a hidden (dashed) outline."""
    nu = int(math.ceil((u1 - u0) / res)) + 1
    nr = int(math.ceil((r1 - r0) / res)) + 1
    segs = []                        # (iu, ia, ib, cls, owner, top)
    vis_px = {i: 0 for i in range(len(sols))}
    tot_px = {i: 0 for i in range(len(sols))}
    col_segs = []
    for iu in range(nu):
        y = u0 + (iu + 0.5) * res
        cols = [(i, s_) + _col(s_, y, view) for i, s_ in enumerate(sols)]
        cols = [c for c in cols if c[2] and c[3]]
        here = []
        if cols:
            br = sorted(set([r0, r1] + [e for c in cols for iv in c[2] for e in iv]))
            for a_, b_ in zip(br, br[1:]):
                if b_ <= a_ + 1e-9:
                    continue
                m = (a_ + b_) / 2
                cov = [c for c in cols if any(lo <= m <= hi for lo, hi in c[2])]
                if not cov:
                    continue
                A = _ivs_or([iv for c in cov if c[1]["op"] == "add" for iv in c[3]])
                Sb = _ivs_or([iv for c in cov if c[1]["op"] == "sub" for iv in c[3]])
                mat = [(hi, "print", None) for lo, hi in _ivs_minus(A, Sb)]
                mat += [(hi, "print", ("p", c[0])) for c in cov if c[1]["op"] == "add_post" for lo, hi in c[3]]
                mat += [(hi, "steel", ("r", c[0])) for c in cov if c[1]["op"] == "ref" for lo, hi in c[3]]
                ia, ib = int(round((a_ - r0) / res)), int(round((b_ - r0) / res))
                if ib <= ia:
                    continue
                for c in cov:
                    if c[1]["op"] in ("sub", "ref"):
                        tot_px[c[0]] += ib - ia
                if not mat:
                    for c in cov:
                        if c[1]["op"] == "sub":
                            vis_px[c[0]] += ib - ia
                    continue
                top, cl, who = max(mat, key=lambda t: t[0])
                if who is None:                                     # which surface: a pocket floor (sub) or an add's face
                    who = next((("s", c[0]) for c in cov if c[1]["op"] == "sub" and any(abs(top - lo) < 1e-6 for lo, hi in c[3])), None) or \
                        next((("a", c[0]) for c in cov if c[1]["op"] == "add" and any(abs(top - hi) < 1e-6 for lo, hi in c[3])), ("a", -1))
                for c in cov:
                    if c[1]["op"] == "sub" and any(top <= lo + 1e-6 for lo, hi in c[3]):
                        vis_px[c[0]] += ib - ia
                if who[0] == "r":
                    vis_px[who[1]] += ib - ia
                here.append([iu, ia, ib, cl, who, top])
        col_segs.append(here)
    # union-find over segments
    flat = [sg for cs in col_segs for sg in cs]
    idx = {}
    k = 0
    for cs in col_segs:
        for sg in cs:
            idx[id(sg)] = k
            k += 1
    par = list(range(k))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def join(p_, q_):
        a_, b_ = find(idx[id(p_)]), find(idx[id(q_)])
        if a_ != b_:
            par[a_] = b_

    def same(p_, q_):
        if p_[3] != q_[3]:
            return False
        if abs(p_[5] - q_[5]) < 1e-4:
            return True
        return p_[4] == q_[4] and abs(p_[5] - q_[5]) < tol
    for cs in col_segs:
        for p_, q_ in zip(cs, cs[1:]):
            if q_[1] == p_[2] and same(p_, q_):
                join(p_, q_)
    for c0, c1 in zip(col_segs, col_segs[1:]):
        for p_ in c0:
            for q_ in c1:
                if q_[1] < p_[2] and p_[1] < q_[2] and same(p_, q_):
                    join(p_, q_)
    lab = np.zeros((nr, nu), np.int32)
    fid, fcls = {}, {}
    for sg in flat:
        r = find(idx[id(sg)])
        if r not in fid:
            fid[r] = len(fid) + 1
            fcls[fid[r]] = sg[3]
        lab[sg[1]:sg[2], sg[0]] = fid[r]
    for f_ in sorted(fid.values()):
        mask = (lab == f_)
        ys_, xs_ = np.nonzero(mask)
        if not len(ys_):
            continue
        a0, a1, b0, b1 = ys_.min(), ys_.max(), xs_.min(), xs_.max()
        sub_ = np.zeros((a1 - a0 + 3, b1 - b0 + 3))
        sub_[1:-1, 1:-1] = mask[a0:a1 + 1, b0:b1 + 1]
        gen = contourpy.contour_generator(z=sub_, line_type="Separate")
        rings = []
        for Lc in gen.lines(0.5):
            w = []
            for cc, rr in Lc:
                uu = u0 + (b0 + cc - 1 + 0.5) * res
                vv = r0 + (a0 + rr - 1 + 0.5) * res
                vv = -vv if flip_rows else vv
                w.append((vv, uu) if transpose else (uu, vv))
            if len(w) >= 4:
                rings.append(_rdp(w, res * 0.6))
        cl = fcls[f_]
        fill_rings(v, rings, MATCLS[cl], P["steel"] if cl == "steel" else None)
    if hidden:
        for i, s_ in enumerate(sols):
            if s_["op"] in ("sub", "ref") and tot_px[i] and vis_px[i] < 0.98 * tot_px[i]:
                poly = s_["S"] if view == "side" else [(a_, -b_ if flip_rows else b_) for a_, b_ in s_["Q"]]
                v.poly([(b_, a_) for a_, b_ in poly] if transpose else poly, cls="hid")


def project(v, P, tl, kind, skip=(), res=0.03, **kw):
    """side (from +X, u = y, v = z) or plan (from +z, u = y, v = -X) projection of a tool."""
    sols = solids(tl, skip)
    if kind == "side":
        ys = [q[0] for s_ in sols for q in s_["S"]]
        zs = [q[1] for s_ in sols for q in s_["S"]]
        render_solids(v, P, sols, "side", min(ys) - 0.5, max(ys) + 0.5, min(zs) - 0.5, max(zs) + 0.5, res=res)
    else:
        ys = [q[0] for s_ in sols for q in s_["Q"]]
        xs = [q[1] for s_ in sols for q in s_["Q"]]
        render_solids(v, P, sols, "plan", min(ys) - 0.5, max(ys) + 0.5, min(xs) - 0.5, max(xs) + 0.5, res=res, flip_rows=True)
    return sols


def section(v, P, tl, plane, value, res=0.01, hatch=True, ref_cls="m-steel"):
    """section of a tool at y = value (u = X, v = z): each solid's cut = X intervals (plan slice) x z intervals
    (side slice) — raster CSG (add - sub + add_post), cut hatch; refs (steel) on top."""
    adds, subs, posts, refs = [], [], [], []
    for s_ in solids(tl):
        zi, xi = _col(s_, value, "side")
        if s_.get("F") and zi and xi and s_["Fy"][0] <= value <= s_["Fy"][1]:
            {"add": adds, "sub": subs, "add_post": posts, "ref": refs}[s_["op"]].append((s_["F"], s_))
            continue
        for x0, x1 in xi:
            for z0, z1 in zi:
                r = rect(x0, x1, z0, z1)
                {"add": adds, "sub": subs, "add_post": posts, "ref": refs}[s_["op"]].append((r, s_))
    rings = csg_rings([a for a, _ in adds], [a for a, _ in subs], [a for a, _ in posts], res=res, eps=res * 0.6)
    fill_rings(v, rings, "m-print2", P["print"] if hatch else None)
    for r, p in refs:
        hpoly(v, r, ref_cls, P["steel"])
    return adds, subs, posts, refs


def zspan(tl, name, kind="side"):
    p = tpart(tl, name, kind)
    b = bbox([tuple(q) for q in p[kind]])
    return b


def ordX(v, feats, col, side="right", **kw):
    """X ordinates of a top view drawn with v = -X: feats [(X, u_feature, label)] -> labels 'X value  label'
    (features at the same X merged first, their labels joined)."""
    m = {}
    for X, u, lab in feats:
        k = round(X, 6)
        if k in m:
            m[k][1] = max((m[k][1], u), key=lambda q: abs(col - q))
            if lab and lab not in m[k][2]:
                m[k][2].append(lab)
        else:
            m[k] = [X, u, [lab] if lab else []]
    ordz(v, [(-X, u, f"X {F(X)}" + (f"  {' · '.join(labs)}" if labs else "")) for X, u, labs in m.values()], col, side=side, raw=True, **kw)


def dimtxt(val, tid=None, nd=2, pre=""):
    return f"{pre}{F(val, nd)}" + (f" ({T(tid)})" if tid else "")


# ================================================================== drawing 14: printed tools
def sheet_tools14():
    import render_v4 as R
    K, L = MV["K"], MV["L"]
    zd, zp = MV["z_datum"], MV["z_plate"]
    # ------------------------------------------------ 1. bench jig T1 — side (from +X), key D rest + T2 in use / parked
    jig = "bench_jig"
    sp = tool(jig)["side"]
    ys = [q[0] for p in sp for q in p["side"]]
    zs = [q[1] for p in sp for q in p["side"]]
    Y0, Y1 = min(ys), max(ys)
    Z0, Z1 = min(zs), max(zs)
    # r4.5 fix: the sheet is laid out <= 1536 px wide (it was 1874 -> every text 7.3~7.7 px high at 1600 px); the
    # margins are in px (label room), the scale fills the rest of the 1516 px row
    ML1, MR1 = 150.0, 340.0
    S = (1508.0 - ML1 - MR1) / (Y1 - Y0)            # + 2 x 4 px pad = 1516
    sv = View(Y0 - ML1 / S, Z0 - 2, Y1 + MR1 / S, Z1 + 10, px_width=(Y1 - Y0) * S + ML1 + MR1, pad_px=4)
    P = pids(sv)
    # key D at rest (phantom) and the capstan gauge in use / parked (phantom) — the jig's job
    kd = [pts(p) for p in body("key D") if p["part"] not in ("capstan head",)]
    stroke_rings(sv, union_rings(kd, res=0.04), "kph")
    cg = tool("capstan_gauge")
    cg_add = [[tuple(q) for q in p["side"]] for p in cg["side"] if p["op"] in ("add", "add_post")]
    stroke_rings(sv, union_rings(cg_add, res=0.04), "phan")
    project(sv, P, jig, "side", res=0.03)
    # centre marks K, L
    for c in (K, L):
        sv.cl(c[0] - 4, c[1], c[0] + 4, c[1])
        sv.cl(c[0], c[1] - 4, c[0], c[1] + 4)
    g = lambda n: bbox([tuple(q) for q in tpart(jig, n)["side"]])
    base, railb, shelf = g("base plate"), g("rail block"), g("rest shelf")
    kpost, lpost, zpw, zpb = g("K post L"), g("L post L"), g("zero pad white L"), g("zero pad black L")
    ledge, park, pin = g("readout ledge post"), g("parking post"), g("balance pin D2x12")
    calib = g("calibration rod")
    calib_x = tpart(jig, "calibration rod")["x"]
    zpw_poly = [tuple(q) for q in tpart(jig, "zero pad white L")["side"]]
    groove_z = sorted(set(q[1] for q in zpw_poly))[-2]          # zero-pad groove floor (side profile: base, floor, lip)
    col = Y1 + 3.0
    ordz(sv, [(zd, base[1], f"지그 밑면 = 프레임 밑면 = 기준 ({T('T01')}); 출력 높이 = z − {F(zd, 1)}"),
              (zp, base[1], f"받침판 윗면 = 프레임 바닥 윗면 ({T('T02')})"),
              (railb[3], railb[1], f"레일 블록 윗면 = 프레임 레일 ({T('T03')})"),
              (shelf[3], shelf[1], f"쉼 선반 = 프레임 선반 S10 ({T('T06')})"),
              (K[1], K[0] + 3, f"K 봉 중심 ({T('T05')})"),
              (pin[3], pin[1], f"예비 핀 꼭대기 ({T('T04')})"),
              (kpost[3], kpost[1], "K 기둥 윗면"),
              (groove_z, zpw[1], f"영점 받침 홈 바닥 ({T('T08')})"),
              (zpw[3], zpw[1], "영점 받침 턱"),
              (calib[3], zpw[1], f"교정봉 윗면 = 캡스턴 꼭대기 S08 ({T('T08')})"),
              (L[1], L[0] + 3, f"L 봉 중심 = 프레임 레버 봉 S11 ({T('T07')}) · 주차 기둥 윗면 ({T('T10')})"),
              (lpost[3], lpost[1], "L 기둥 윗면"),
              (ledge[3], ledge[1], f"읽기 턱 = 가짜 레버 바늘 윗면 b = 0 ({T('T09')})")],
         col, gap_px=12.5, label_px=9.2, lo=Z0 - 1)
    ordy(sv, [(base[0], base[2], "받침판 앞"), (ledge[0], zp, f"읽기 턱 ({T('T09')})"), (ledge[1], zp, ""),
              (railb[0], zp, f"레일 앞면 ({T('T03')})"), (MV["pin_y"], zp, "핀"), (railb[1], zp, ""),
              (K[0], zp, "K"), (kpost[1], zp, ""),
              (zpb[0], zp, "흑 영점"), (MV["caps"]["black"], zp, "흑 캡스턴"), (zpb[1], zp, ""),
              (zpw[0], zp, "백 영점"), (MV["caps"]["white"], zp, "백 캡스턴"), (zpw[1], zp, ""),
              (shelf[0], zp, f"선반 ({T('T06')})"), (shelf[1], zp, ""), (lpost[0], zp, "L 기둥"),
              (L[0], zp, "L"), (lpost[1], zp, ""), (park[0], zp, f"주차 ({T('T10')})"), (park[1], zp, ""),
              (base[1], base[2], "받침판 끝")],
         Z0 - 1.2, gap_px=12.0, label_px=9)
    panel_title(sv, Y0 - ML1 / S + 1, Z1 + 10 - sv.px(13),
                f"T1 벤치 지그 — 옆에서 (+X 쪽) · 회색 점선 = 쉼 자세의 백건 D, 보라 1점 쇄선 = T2 가짜 레버 (쓰는 자세 b = 0; 안 쓸 때는 {F(cg['parked_b_deg'], 1)}° 젖혀 주차 기둥에)",
                size_px=12)
    # ------------------------------------------------ 2. bench jig plan (u = y, v = X)
    pl = tool(jig)["plan"]
    Xs = [q[0] for p in pl for q in p["plan"]]
    X0, X1 = min(Xs), max(Xs)
    pv = View(Y0 - ML1 / S, -X1 - 3, Y1 + MR1 / S, -X0 + 16, px_width=(Y1 - Y0) * S + ML1 + MR1, pad_px=4)
    Pp = pids(pv)
    project(pv, Pp, jig, "plan", res=0.03)
    pv.cl(Y0 - 2, 0.0, Y1 + 2, 0.0)
    gp = lambda n: bbox([(q[1], q[0]) for q in tpart(jig, n, "plan")["plan"]])       # (y0, y1, X0, X1)
    kpL, kpR, lpL, lpR = gp("K post L"), gp("K post R"), gp("L post L"), gp("L post R")
    zwL, zwR, sh, pk, ld, rod_k, rod_l = gp("zero pad white L"), gp("zero pad white R"), gp("rest shelf"), gp("parking post"), \
        gp("readout ledge post"), gp("K rod stub"), gp("L rod stub")
    bp = gp("base plate")
    ordX(pv, [(bp[2], bp[1], f"받침판 ({T('T02')})"), (bp[3], bp[1], ""), (lpL[2], lpL[1], f"L 기둥 ({T('T07')})"), (lpL[3], lpL[1], ""),
              (lpR[2], lpR[1], ""), (lpR[3], lpR[1], ""), (rod_l[2], rod_l[1], "L 봉 토막"), (rod_l[3], rod_l[1], "L 봉 토막 (오른쪽 막힘)"),
              (sh[2], sh[1], f"선반 ({T('T06')})"), (sh[3], sh[1], ""), (pk[2], pk[1], f"주차 ({T('T10')})"), (pk[3], pk[1], ""),
              (zwL[2], zwL[1], f"영점 받침 ({T('T08')})"), (zwL[3], zwL[1], ""), (zwR[2], zwR[1], ""), (zwR[3], zwR[1], "")],
         col, gap_px=12.0, label_px=9)
    # r4.5 fix: the readout post is a trapezoid in (X, z): from above, the top face ends at X = xt1 and the brace slopes
    # down to its foot -> the crease line across the post (the box projection does not show it)
    fr_ld0 = next(q for q in tool(jig)["front"] if q["name"].startswith("readout ledge post"))
    fq0 = [tuple(t) for t in fr_ld0["front"]]
    xt1_ = max(t[0] for t in fq0 if abs(t[1] - max(u[1] for u in fq0)) < 1e-6)
    pv.line(fr_ld0["y"][0], -xt1_, fr_ld0["y"][1], -xt1_, cls="vis")
    ordX(pv, [(kpL[2], kpL[0], f"K 기둥 ({T('T05')})"), (kpL[3], kpL[0], ""), (kpR[2], kpR[0], ""), (kpR[3], kpR[0], ""),
              (rod_k[2], rod_k[0], "K 봉 토막"), (rod_k[3], rod_k[0], "K 봉 토막 (오른쪽 막힘)"),
              (ld[2], ld[0], f"읽기 턱 기둥 발 ({T('T09')})"), (xt1_, ld[0], "윗면 끝 (D-D)"), (ld[3], ld[0], ""), (0.0, bp[0], "= 그 건반의 밸런스 핀")],
         Y0 - 1.5, side="left", gap_px=12.0, label_px=9)
    panel_title(pv, Y0 - ML1 / S + 1, -X0 + 16 - pv.px(13),
                f"T1 벤치 지그 — 위에서 · X = x − 그 건반의 밸런스 핀 x (모든 건반이 같은 지그: 핀 홈을 X 0에) · 점선 = 기둥 속 봉 구멍 Ø3.9 → Ø4.0 드릴",
                size_px=12)
    # ------------------------------------------------ 3. jig sections (X-z) at K, at the white zero pad, at L
    secs = []
    # r4.5 fix: + D-D through the readout-ledge post (T09): its (X, z) section is a trapezoid (tools_geometry front 'py')
    fr_ld = next(q for q in tool(jig)["front"] if q["name"].startswith("readout ledge post"))
    for tag, yy, ttl in (("A", K[0], f"A-A y{F(K[0])} (K 봉)"), ("B", MV["caps"]["white"], f"B-B y{F(MV['caps']['white'])} (백 영점 받침 + 교정봉)"),
                         ("C", L[0], f"C-C y{F(L[0])} (L 봉)"), ("D", (fr_ld["y"][0] + fr_ld["y"][1]) / 2, f"D-D y{F((fr_ld['y'][0] + fr_ld['y'][1]) / 2)} (읽기 턱 기둥)")):
        S3 = 5.6
        zz = [z for p in sp for (z0, z1) in yslice([tuple(q) for q in p["side"]], yy) for z in (z0, z1)]
        zt = max(zz)
        if tag == "D":
            S3 = 3.6
            fxs = [t[0] for t in fr_ld["front"]]
            xa, xb = min(fxs) - 2.0, max(fxs) + 2.0
            xv = View(xa, Z0 - 1, xb + 150 / S3, zt + 9, px_width=(xb - xa) * S3 + 150, pad_px=4)
            Px = pids(xv)
            i0_ = kit.clip_begin(xv)
            adds, subs, posts, refs = section(xv, Px, jig, "y", yy)
            kit.clip_end(xv, i0_, xa, xb, Z0 - 1, zt + 2, frame=False)
            fq = [tuple(t) for t in fr_ld["front"]]
            ztop, xl0 = max(t[1] for t in fq), min(t[0] for t in fq)
            xt1 = max(t[0] for t in fq if abs(t[1] - ztop) < 1e-6)
            zkn = min(t[1] for t in fq if abs(t[0] - xt1) < 1e-6)
            xft = max(t[0] for t in fq)
            ordz(xv, [(zd, xb - 1.0, "밑면 (T01)"), (zp, xft, "받침판"), (zkn, xt1, "버팀 시작"), (ztop, xt1, f"읽기 턱 ({T('T09')})")],
                 xb + 0.5, gap_px=12, label_px=9, lo=Z0 - 1)
            ordy(xv, [(xl0, zp, ""), (xt1, zp, "윗면 끝"), (xft, zp, "버팀 끝")], Z0 - 0.8, gap_px=12, label_px=9, prefix="X ")
            panel_title(xv, xa + 0.5, zt + 9 - xv.px(13), f"{ttl} — 사다리꼴 ({T('T09')})", size_px=11)
            secs.append(xv)
            continue
        xv = View(X0 - 2, Z0 - 1, X1 + 34, zt + 9, px_width=(X1 - X0 + 36) * S3, pad_px=4)
        Px = pids(xv)
        adds, subs, posts, refs = section(xv, Px, jig, "y", yy)
        xv.cl(0.0, Z0 - 0.5, 0.0, zt + 2)
        feats = [(zd, X1, "밑면 (T01)"), (zp, X1, "받침판")]
        xfe = []
        if tag == "A":
            bo = next(p for r, p in subs if p["name"].startswith("K bore"))
            rd = next(p for r, p in refs if p["name"].startswith("K rod"))
            feats += [(K[1], kpR[3], f"K ({T('T05')})"), (kpost[3], kpR[3], "기둥 윗면")]      # r4.5 fix: to the post edge
            xfe = [(kpL[2], zp, "기둥"), (kpL[3], zp, ""), (kpR[2], zp, "기둥"), (kpR[3], zp, ""),
                   (rd["x"][0], K[1] - 2, "봉 토막"), (rd["x"][1], K[1] - 2, "막힌 구멍 끝")]
            xv.dim_h(rd["x"][0], rd["x"][1], kpost[3] + 3.5, text=f"봉 토막 {F(rd['x'][1] - rd['x'][0], 1)}",
                     ext_from=(K[1] + 2, K[1] + 2), size_px=9.5)
            xv.dim_h(rd["x"][1], kpR[3], kpost[3] + 1.2, text=f"벽 {F(kpR[3] - rd['x'][1], 1)}", ext_from=(K[1], kpost[3]), size_px=9, tpos="right")
        elif tag == "B":
            feats += [(groove_z, zwR[3], f"홈 바닥 ({T('T08')})"), (calib[3], calib_x[1], "교정봉 윗면 = 캡스턴 꼭대기")]
            xfe = [(zwL[2], zp, "영점 받침"), (zwL[3], zp, ""), (zwR[2], zp, "영점 받침"), (zwR[3], zp, "")]
        else:
            rd = next(p for r, p in refs if p["name"].startswith("L rod"))
            feats += [(L[1], lpR[3], f"L ({T('T07')})"), (lpost[3], lpR[3], "기둥 윗면")]
            xfe = [(lpL[2], zp, "기둥"), (lpL[3], zp, ""), (lpR[2], zp, "기둥"), (lpR[3], zp, ""),
                   (rd["x"][0], L[1] - 2, "봉 토막"), (rd["x"][1], L[1] - 2, "막힌 구멍 끝")]
            xv.dim_h(rd["x"][0], rd["x"][1], lpost[3] + 3.5, text=f"봉 토막 {F(rd['x'][1] - rd['x'][0], 1)}",
                     ext_from=(L[1] + 2, L[1] + 2), size_px=9.5)
        ordz(xv, feats, X1 + 2, gap_px=12, label_px=9, lo=Z0 - 1)
        ordy(xv, xfe, Z0 - 0.8, gap_px=12, label_px=9, prefix="X ")
        panel_title(xv, X0 - 1.5, zt + 9 - xv.px(13), f"{ttl} — 앞에서 본 단면", size_px=11.5)
        secs.append(xv)
    # ------------------------------------------------ 4. height block (T11~T15): side (v, z) + plan (u, v)
    hb = "height_block"
    hs = tool(hb)["side"]
    hv_ = [q[0] for p in hs for q in p["side"]]
    hz_ = [q[1] for p in hs for q in p["side"]]
    S4 = 6.2
    hv = View(min(hv_) - 3, zp - 2, max(hv_) + 44, max(hz_) + 8, px_width=(max(hv_) - min(hv_) + 47) * S4, pad_px=4)
    Ph = pids(hv)
    project(hv, Ph, hb, "side", res=0.02)
    lands = [(tpart(hb, n), tid) for n, tid in (("land W+", "T11"), ("land W-", "T12"), ("land B+", "T13"), ("land B-", "T14"))]
    feats = [(zp, max(hv_), f"블록 밑 = 지그 받침판 윗면 z{F(zp, 1)}")]
    for p, tid in lands:
        b = bbox([tuple(q) for q in p["side"]])
        lab = re.search(r"land (\S+)", p["name"]).group(1)
        feats.append((b[3], b[1], f"{lab} ({T(tid)}) = 받침판 위 {F(b[3] - zp)}"))
    ordz(hv, feats, max(hv_) + 1.5, gap_px=12.5, label_px=9, lo=zp - 1)
    wb = bbox([tuple(q) for q in tpart(hb, "web")["side"]])
    ordy(hv, [(bbox([tuple(q) for q in p["side"]])[0], zp, re.search(r"land (\S+)", p["name"]).group(1)) for p, _ in lands] +
         [(bbox([tuple(q) for q in lands[-1][0]["side"]])[1], zp, "")], zp - 1.2, gap_px=12, label_px=9, prefix="v ")
    w15 = tnums("T15")[0]
    panel_title(hv, min(hv_) - 2.5, max(hz_) + 8 - hv.px(13), f"T1 높이 블록 — 옆 (v = 블록 앞끝에서) · 창 ±{F(w15)} ({T('T15')})", size_px=11.5)
    # plan of the block
    hp = View(-3, min(hv_) - 3, 10 + 30, max(hv_) + 8, px_width=(10 + 33) * S4, pad_px=4)
    Php = pids(hp)
    for p in tool(hb)["plan"]:
        poly = [tuple(q) for q in p["plan"]]
        hpoly(hp, poly, "m-print2")
    ub = bbox([tuple(q) for p in tool(hb)["plan"] for q in p["plan"]])
    hp.dim_h(ub[0], ub[1], ub[3] + 2.2, text=f"두께 {F(ub[1] - ub[0], 1)}", ext_from=(ub[3], ub[3]), size_px=9)
    hp.text(ub[0] - hp.px(6), ub[2] + 1, "건반 옆면에 대는 면 (u 0)", cls="tx-s", anchor="start", size_px=9, rot=-90)
    ordz(hp, [(bbox([tuple(q) for q in p["plan"]])[2], ub[1], re.search(r"land (\S+)", p["name"]).group(1) if "land" in p["name"] else "")
              for p in tool(hb)["plan"] if "land" in p["name"]] + [(ub[3], ub[1], "")] +
             [(bbox([tuple(q) for q in tpart(hb, "land W-", "plan")["plan"]])[3], ub[1], "웹")], ub[1] + 1.5, gap_px=11.5, label_px=9, prefix="v ")
    panel_title(hp, -2.5, max(hv_) + 8 - hp.px(13), "위에서 (u × v)", size_px=11)
    # ------------------------------------------------ 5. capstan bench gauge T2 (dummy lever): side, plan, section at the pocket
    cgn = "capstan_gauge"
    cs = cg["side"]
    cy_ = [q[0] for p in cs for q in p["side"]]
    cz_ = [q[1] for p in cs for q in p["side"]]
    S5 = 6.2
    cv = View(min(cy_) - 4, min(cz_) - 3, max(cy_) + 60, max(cz_) + 12, px_width=(max(cy_) - min(cy_) + 64) * S5, pad_px=4)
    Pc = pids(cv)
    kd_t = [pts(p) for p in body("key D") if p["part"] not in ("capstan head",)]
    rings_k = union_rings(kd_t, res=0.04)
    i0 = kit.clip_begin(cv)
    stroke_rings(cv, rings_k, "kph")
    hpoly(cv, pts(next(p for p in body("key D") if p["part"] == "capstan head")), "m-steel", Pc["steel"])
    kit.clip_end(cv, i0, min(cy_) - 4, max(cy_) + 2, min(cz_) - 3, max(cz_) + 4, frame=False)
    project(cv, Pc, cgn, "side", res=0.02)
    cv.cl(L[0] - 6, L[1], L[0] + 6, L[1])
    cv.cl(L[0], L[1] - 6, L[0], L[1] + 6)
    gc = lambda n: bbox([tuple(q) for q in tpart(cgn, n)["side"]])
    bod, hub_, pock, st_, beak, blade, lipt, lipb = gc("body"), gc("hub R"), gc("steel pocket"), gc("steel SS400"), gc("beak"), \
        gc("pointer blade"), gc("snap lip top"), gc("snap lip bottom")
    zc = MV["z_c"]
    # r4.5 fix: the beak underside is the lowest z of the beak prism IN FRONT of the body (y < body front); its bbox
    # minimum z53.39 is only the 0.01 overlap seam with the body top z53.4 (geometry note, tools/make_tools.py)
    beak_under = min(q[1] for q in tpart(cgn, "beak")["side"] if q[0] < bod[0] - 1e-6)
    ordz(cv, [(hub_[2], hub_[1], "허브 밑"), (zc, bod[1], f"밑면 = 캡스턴 꼭대기에 닿는 면 ({T('T17')})"), (pock[2], pock[1], f"강철 주머니 ({T('T18')})"),
              (L[1], hub_[1], f"L = 허브 구멍 Ø3.9 → Ø4.0 ({T('T16')})"), (pock[3], pock[1], ""), (bod[3], max(q[0] for q in tpart(cgn, "body")["side"] if abs(q[1] - bod[3]) < 1e-6), "몸통 윗면"),
              (beak_under, (beak[0] + bod[0]) / 2, f"부리 밑 = 흑건 윗면 + {F(beak_under - MV['black_top'], 1)} ({T('T20')})"), (blade[2], blade[1], "바늘"),
              (blade[3], blade[1], f"바늘 윗면 = 읽기 턱 ({T('T21')})")],
         max(cy_) + 2, gap_px=12.5, label_px=9, lo=min(cz_) - 2)
    ordy(cv, [(beak[0], beak_under, f"부리·바늘 ({T('T20')})"), (blade[1], blade[2], ""), (bod[0], zc, f"앞면 ({T('T19')})"),
              (pock[0], zc, "주머니"), (st_[0], zc, "강철"), (MV["caps"]["white"], zc, "백 캡스턴"),
              (st_[1], zc, ""), (pock[1], zc, ""), (bod[1], zc, "밑면 끝"), (L[0], hub_[2], "L"), (hub_[1], L[1], "허브")],
         min(cz_) - 1.5, gap_px=12, label_px=9)
    amp = TG["dummy_lever"]["per_colour"]
    panel_title(cv, min(cy_) - 3, max(cz_) + 12 - cv.px(13),
                f"T2 캡스턴 벤치 게이지 (가짜 레버) — 옆, 쓰는 자세 b = 0 · 회색 점선 = 백건 D · 확대 백 {F(amp['white']['amp'])}·흑 {F(amp['black']['amp'])}배 ({T('T22')})",
                size_px=11.5)
    # section through the pocket (X-z)
    ysec = (st_[0] + st_[1]) / 2
    cxs = [x for p in cs for x in p["x"]]
    S6 = 10.0
    ev = View(min(cxs) - 2, zc - 3, max(cxs) + 34, bod[3] + 8, px_width=(max(cxs) - min(cxs) + 36) * S6, pad_px=4)
    Pe = pids(ev)
    ad_, sb_, po_, rf_ = section(ev, Pe, cgn, "y", ysec)
    bx = next(p for r, p in ad_ if p["name"].startswith("body"))["x"]
    px_ = next(p for r, p in sb_ if p["name"].startswith("steel pocket"))["x"]
    sx_ = next(p for r, p in rf_ if p["name"].startswith("steel"))["x"]
    ordz(ev, [(zc, bx[1], "밑면"), (pock[2], bx[1], "주머니"), (st_[2], bx[1], "강철"), (st_[3], bx[1], ""), (pock[3], bx[1], ""),
              (bod[3], bx[1], ""), (lipb[3], bx[1], "아래 립"), (lipt[2], bx[1], "위 립")], max(cxs) + 1.5, gap_px=11.5, label_px=9, lo=zc - 2)
    ordy(ev, [(bx[0], zc, "몸통"), (px_[0], zc, "주머니"), (sx_[0], zc, "강철"), (sx_[1], zc, ""), (bx[1], zc, "")], zc - 1.2,
         gap_px=11.5, label_px=9, prefix="X ")
    panel_title(ev, min(cxs) - 1.5, bod[3] + 8 - ev.px(13), f"D-D y{F(ysec)} 단면 (+X로 열린 주머니)", size_px=11)
    # plan of the gauge (u = y, v = X)
    cpl = cg["plan"]
    cX = [q[0] for p in cpl for q in p["plan"]]
    cpv = View(min(cy_) - 4, -max(cX) - 3, max(cy_) + 60, -min(cX) + 12, px_width=(max(cy_) - min(cy_) + 64) * S5, pad_px=4)
    Pcp = pids(cpv)
    project(cpv, Pcp, cgn, "plan", res=0.02)
    gpp = lambda n: bbox([(q[1], q[0]) for q in tpart(cgn, n, "plan")["plan"]])
    bdp, bl_ = gpp("body"), gpp("pointer blade")
    ordX(cpv, [(bdp[2], bdp[1], "몸통 −X (출력 때 베드 면)"), (0.0, bdp[1], "레버 중심"), (bdp[3], bdp[1], "몸통 +X"),
               (bl_[3], bl_[1], f"바늘 끝 ({T('T21')})")], max(cy_) + 2, gap_px=12, label_px=9)
    cpv.cl(min(cy_) - 2, 0.0, max(cy_) + 1, 0.0)
    panel_title(cpv, min(cy_) - 3, -min(cX) + 12 - cpv.px(13), "T2 — 위에서 (점선 = 속의 강철 주머니·허브 구멍)", size_px=11)
    # ------------------------------------------------ 6. balance-pin height gauge T3: side, section at the pin, plan
    pg = "pin_gauge"
    ps = tool(pg)["side"]
    py_ = [q[0] for p in ps for q in p["side"]]
    pz_ = [q[1] for p in ps for q in p["side"]]
    rail_z, pin_top = MV["z_rail_low"], MV["pin_top"]
    S7 = 17.0
    gv = View(min(py_) - 1.5, 10.0, max(py_) + 13.5, max(pz_) + 3, px_width=(max(py_) - min(py_) + 15) * S7, pad_px=4)
    Pg = pids(gv)
    # the frame rail under the gauge (geometry.json, x = key D pin) as phantom outline
    xp = kit.plan_item("key D balance pin")["circle"][0]
    rails = [p for p in fixed() if p["part"].startswith("balance rail") and kit.cut_x(p, xp)]
    i0 = kit.clip_begin(gv)
    stroke_rings(gv, union_rings([pts(p) for p in rails], res=0.01), "kph")
    kit.clip_end(gv, i0, min(py_) - 1.5, max(py_) + 1.5, 10.0, max(pz_) + 3, frame=False)
    project(gv, Pg, pg, "side", res=0.005)
    gg = lambda n: bbox([tuple(q) for q in tpart(pg, n)["side"]])
    fb, rb, rr, roof, fence, pb, bore = gg("front body"), gg("rear body + land"), gg("rear body (0.3"), gg("roof"), gg("fence"), \
        gg("press block"), gg("press bore")
    # r4.5 fix: the front is two prisms now ('front body' y132.00-132.30(+0.01 overlap) + 'front foot = land on the rail
    # top' y132.30-133.85, T24): dimension their union, not the 0.01 CSG overlap
    ffo = [bbox([tuple(q) for q in p_["side"]]) for p_ in tparts(pg, "front foot")]
    if ffo:
        fb = (min(fb[0], ffo[0][0]), max(fb[1], ffo[0][1]), min(fb[2], ffo[0][2]), max(fb[3], ffo[0][3]))
    go, nogo = gg("GO roof right"), gg("NO-GO roof right")
    ordz(gv, [(fence[2], fence[1], f"울타리 밑 ({T('T25')})"), (rail_z, rr[1], f"발 = 레일 윗면 ({T('T24')})"), (rr[2], rr[1], "뒤 몸통 (레일 포켓 위 0.3)"),
              (nogo[2], rr[1], f"NO-GO 천장 ({T('T29')})"), (bore[3], rr[1], f"멈춤 면 = 핀 꼭대기 P32 ({T('T26')})"),
              (go[2], rr[1], f"GO 천장 ({T('T28')})"), (roof[2], rr[1], f"열린 홈 천장 ({T('T27')})"), (fb[3], rr[1], "윗면")],
         max(py_) + 0.6, gap_px=12.5, label_px=9, lo=10.5)
    ordy(gv, [(fence[0], fence[2], "울타리"), (fb[0], fence[2], "앞 몸통"), (MV["rail_front_y"], rail_z, f"레일 앞면 = 앞 발 ({T('T24')})"),
              (fb[1], rail_z, "앞 발 끝"), (MV["pin_y"], rail_z, "핀"),
              (rb[0], rail_z, "뒤 발"), (rb[1], rail_z, ""), (rr[1], rail_z, "")], 10.5, gap_px=12, label_px=9)
    panel_title(gv, min(py_) - 1.2, max(pz_) + 3 - gv.px(13), "T3 핀 높이 게이지 — 옆 (+X 쪽)", size_px=11)
    # front section at the pin (u = X, v = z)
    pxs = [x for p in ps for x in p["x"]]
    S8 = 11.8
    fv = View(min(pxs) - 2, 10.0, max(pxs) + 40, max(pz_) + 5, px_width=(max(pxs) - min(pxs) + 42) * S8, pad_px=4)
    Pf = pids(fv)
    # neighbour pins (tools model_values: x_pin of the keys either side of D) as phantom, the rail top line
    xs_pin = sorted(k["x_pin"] for k in MV["keys"].values())
    xd = MV["keys"]["D"]["x_pin"]
    nb = [x - xd for x in xs_pin if 0 < abs(x - xd) < max(pxs)]
    pinr = gg("balance pin D2 (target)")
    pinx = tpart(pg, "balance pin D2 (target)")["x"]
    for dx in nb:
        fv.poly(rect(dx + pinx[0], dx + pinx[1], pinr[2], pin_top), cls="kph")
    fv.line(min(pxs) - 1.5, rail_z, max(pxs) + 1.5, rail_z, cls="phan")
    section(fv, Pf, pg, "y", MV["pin_y"], res=0.01)
    fv.cl(0.0, 11.0, 0.0, max(pz_) + 1)
    gox = tpart(pg, "GO roof right")["x"]
    ngx = tpart(pg, "NO-GO roof right")["x"]
    pbx = tpart(pg, "press block")["x"]
    brx = tpart(pg, "press bore")["x"]
    ordz(fv, [(rail_z, max(pxs), f"레일 윗면 ({T('T24')})"), (nogo[2], max(pxs), f"NO-GO ({T('T29')}): 핀이 여기서 멈춰야"),
              (pin_top, max(pxs), f"핀 꼭대기 목표 P32 = 멈춤 면 ({T('T26')})"), (go[2], max(pxs), f"GO ({T('T28')}): 핀이 밑으로 지나가야"),
              (roof[2], max(pxs), f"홈 천장 ({T('T27')})"), (fb[3], max(pxs), "")], max(pxs) + 1.5, gap_px=12.5, label_px=9, lo=10.5)
    ordy(fv, [(-gox[1], rail_z, "GO"), (-gox[0], rail_z, "NO-GO"), (-ngx[0], rail_z, ""), (pbx[0], rail_z, "누름 블록"),
              (brx[0], rail_z, f"구멍 Ø{F(brx[1] - brx[0], 1)}"), (brx[1], rail_z, ""), (pbx[1], rail_z, ""),
              (ngx[0], rail_z, "NO-GO"), (gox[0], rail_z, "GO"), (gox[1], rail_z, "")] +
         [(dx, pinr[2], "이웃 핀") for dx in nb], 10.5, gap_px=12, label_px=9, prefix="X ")
    fv.dim_v(rail_z, pin_top, -gox[1] - 0.8, text=f"{F(pin_top - rail_z)}", ext_from=(-gox[1], -gox[1]), size_px=9.5)
    panel_title(fv, min(pxs) - 1.5, max(pz_) + 5 - fv.px(13),
                f"T3 — 핀 자리 y{F(MV['pin_y'])} 단면 (앞에서) · 점선 = 이웃 건반 핀 (핀 간격 모델 값) · 합격 = 핀 꼭대기 z{F(nogo[2])}~{F(go[2])}",
                size_px=11)
    # plan of the pin gauge (u = y ... drawn u = X, v = y for a long thin plan)
    ppl = tool(pg)["plan"]
    gpv = View(min(pxs) - 2, min(py_) - 2, max(pxs) + 40, max(py_) + 6, px_width=(max(pxs) - min(pxs) + 42) * S8, pad_px=4)
    Pgp = pids(gpv)
    sols_pg = solids(pg)
    render_solids(gpv, Pgp, sols_pg, "plan", min(py_) - 0.5, max(py_) + 0.5, min(pxs) - 0.5, max(pxs) + 0.5, res=0.01, transpose=True)
    gpv.cl(0.0, min(py_) - 1, 0.0, max(py_) + 1)
    ordz(gpv, [(fence[0], max(pxs), "울타리"), (fb[0], max(pxs), "앞 발"), (roof[0], max(pxs), "홈"), (roof[1], max(pxs), ""),
               (rr[1], max(pxs), "뒤")], max(pxs) + 1.5, gap_px=11, label_px=9, prefix="y ")
    gpv.dim_h(min(pxs), max(pxs), max(py_) + 1.5, text=f"길이 {F(max(pxs) - min(pxs), 1)} (u {F(min(pxs), 1)}~{F(max(pxs), 1)}, {T('T24')})",
              ext_from=(max(py_), max(py_)), size_px=9.5)
    panel_title(gpv, min(pxs) - 1.5, max(py_) + 6 - gpv.px(13), "T3 — 위에서 (쓸 때 윗면; 출력은 뒤집어)", size_px=11)
    # ------------------------------------------------ notes: print data, mass, what each sets
    pr = TG["print"]
    nm = {"bench_jig": "T1 벤치 지그", "height_block": "T1 높이 블록", "capstan_gauge": "T2 캡스턴 게이지", "pin_gauge": "T3 핀 높이 게이지"}
    cols = ["공구", "출력 크기 (mm)", "벽", "채움", "질량", "시간"]
    tk = ("bench_jig", "height_block", "capstan_gauge", "pin_gauge")
    rows = [[nm[k], " × ".join(kit.FX(b, 1) for b in pr[k]["bbox"]), f"{pr[k]['walls']}", f"{F(pr[k]['infill'] * 100, 0)} %",
             f"{kit.FX(pr[k]['mass_g'], 1)} g", f"{F(pr[k]['time_min'], 0)}분"] for k in tk]      # r4.5 fix 3: fixed 1 decimal
    nv = View(0, -410, 1480, 0, px_width=1480, pad_px=6)
    yb = table(nv, 6, -8, cols, rows, [150, 170, 60, 70, 80, 80], row_px=18, size_px=9.8)
    lines = [f"출력 {nm[k]}: {pr[k]['orient']} · 층 {pr[k]['layer']}" for k in tk] + [
        f"합계 {F(TG['total_mass_g'], 1)} g · {F(TG['total_time_min'], 0)}분, PETG · 서포트 없음 · 모든 공구가 256 베드에 들어감. 끼워 쓰는 것 (구매 없음): 봉 토막 K {F(rod_k[1] - rod_k[0], 1)} · L {F(rod_l[1] - rod_l[0], 1)} · 교정봉 {F(calib[1] - calib[0], 1)} (건반 봉과 같은 Ø4), 예비 밸런스 핀 1, 레버용 강철 블록 1.",
        f"기준: 지그 밑면 z{F(zd, 1)} = 프레임 밑면 ({T('T01')}) — K·L 봉 중심, 쉼 선반 z{F(MV['z_shelf'], 3)}, 레일 블록 z{F(railb[3], 1)}이 프레임과 같은 층에서 반올림되도록 프레임과 같은 층 높이로 출력.",
        f"T1: 건반을 K 봉 토막에 노치로 얹고 쉼 펠트를 선반에 → 모듈과 같은 쉼 자세. 높이 블록을 받침판 위에 세워 건반 앞 윗면이 땅 W−/W+ (흑 B−/B+) 사이면 합격 (창 ±{F(w15)}, 펀칭 1장 = 앞 {F(MV['punch_front'], 2)}).",
        f"T2: 강철 블록을 주머니에 스냅, 허브를 L 봉 토막에 → 밑면 z{F(zc, 1)}이 캡스턴 꼭대기를 실제 레버 모멘트로 누름 ({TD['T23']['value']} {TD['T23']['unit']}, {T('T23')}). 바늘 윗면이 읽기 턱과 손톱으로 같은 높이면 캡스턴 z{F(zc, 1)}.",
        f"   영점: 교정봉을 영점 받침 홈에 → 바늘 = 읽기 턱 확인. 1/8회전({F(MV['turn8'], 4)}) = 바늘 백 {F(amp['white']['per8'])} · 흑 {F(amp['black']['per8'])}. 쓰지 않을 때는 뒤로 젖혀 주차 기둥에 기댐 ({F(cg['parked_b_deg'], 1)}°).",
        f"T3: 울타리를 레일 앞면에 대고 누름 구멍으로 핀을 멈춤 면 z{F(pin_top)}까지 눌러 넣음 → GO 구간(천장 z{F(go[2])}) 밑으로 지나가고 NO-GO 구간(천장 z{F(nogo[2])})에서 걸리면 합격.",
        f"숫자 = tools_geometry.json (T01~T29 = 공구 치수표) · 모양 = 같은 파일의 옆·위 프리즘 (tools/make_tools.py, STL과 같은 값) · 건반·레일 점선 = geometry.json.",
    ]
    note_lines(nv, lines, 6, yb - 20, line_px=16, size_px=10)
    rows_ = [[sv], [pv], secs[:2] + secs[3:4], [secs[2], hv, hp], [cv, ev], [cpv], [gv, fv], [gpv], [nv]]
    base = os.path.join(kit.HERE, "d14_printed_tools")
    page(rows_, base, "도면 14. 출력 공구 (벤치 지그 · 높이 블록 · 캡스턴 게이지 · 핀 높이 게이지)",
         "단위 mm · 숫자 = tools_geometry.json (괄호 = 공구 치수표 T01~T29) · 좌표: X = x − 그 건반의 밸런스 핀 x, y·z = 모델 (z = 책상에서) · "
         "연녹 = 출력 공구, 회색 빗금 = 끼워 쓰는 강철(봉 토막·핀·강철 블록), 가는 점선 = 숨은 구멍·속 부분")
    SHEETS.append(dict(n=14, title_ko="출력 공구 (벤치 지그 · 높이 블록 · 캡스턴 게이지 · 핀 높이 게이지)",
                       caption_ko=(f"출력 공구 4개(T1 벤치 지그 + 높이 블록, T2 캡스턴 벤치 게이지 = 가짜 레버, T3 밸런스 핀 높이 게이지)의 실제 모양과 치수. "
                                   f"지그는 옆·위·단면 넷(A-A K 봉, B-B 영점 받침·교정봉, C-C L 봉, D-D 읽기 턱 기둥 = 사다리꼴, r4.5 고침): 밑면 z{F(zd, 1)} = 프레임 밑면이 기준이고, K 봉 중심 ({F(K[0])}, {F(K[1])}), "
                                   f"쉼 선반 z{F(MV['z_shelf'], 3)}, L 봉 ({F(L[0])}, {F(L[1])}), 읽기 턱 z{F(ledge[3], 1)}을 세운다. 높이 블록 땅 W {F(tnums('T12')[0])}~{F(tnums('T11')[0])} · "
                                   f"B {F(tnums('T14')[0])}~{F(tnums('T13')[0])}. 가짜 레버는 밑면 z{F2(MV['z_c'])}으로 캡스턴을 실제 레버 모멘트로 누르고 바늘로 {F(amp['white']['amp'])}배 확대해 읽는다 "
                                   f"(r4.4 고침 2b: 밑면·교정봉 윗면 = 정착 쉼 캡스턴 꼭대기 백 z{F(MV['crown_settled']['white'], 3)} · 흑 z{F(MV['crown_settled']['black'], 3)}의 가운데, 건반 좌표 z{F(MV['z_c_key'], 1)}가 아님). "
                                   f"핀 게이지는 레일 윗면 z{F(rail_z, 1)}에 서서 핀 꼭대기를 z{F(pin_top)}(GO {F(go[2])} / NO-GO {F(nogo[2])})로 맞춘다. "
                                   f"합계 {F(TG['total_mass_g'], 1)} g · {F(TG['total_time_min'], 0)}분. 숫자는 모두 tools_geometry.json(T01~T29)."),
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))


# ================================================================== drawing 15: stage-0 coupons / fixtures
def stl_load(path):
    """triangles (n, 3, 3) of a binary or ASCII STL."""
    b = open(path, "rb").read()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        return np.array(re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", b), float).reshape(-1, 3, 3)
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84)
    return a["v"].reshape(-1, 3, 3).astype(float)


# view -> (u axis, v axis, depth axis, depth sign): third-angle projection, part in its print pose (z0 = bed)
VIEWS = {"top": (0, 1, 2, 1.0), "front": (0, 2, 1, -1.0), "right": (1, 2, 0, 1.0)}


class Mesh:
    """an STL as welded vertices, faces, unit normals and its edges (with the two faces of each manifold edge)."""

    def __init__(self, T):
        nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        L = np.linalg.norm(nrm, axis=1)
        keep = L > 1e-10
        T, nrm, L = T[keep], nrm[keep], L[keep]
        self.T = T
        self.N = nrm / L[:, None]
        V = T.reshape(-1, 3)
        self.V, inv = np.unique(np.round(V, 4), axis=0, return_inverse=True)
        self.F = inv.reshape(-1, 3)
        E = np.sort(np.concatenate([self.F[:, [0, 1]], self.F[:, [1, 2]], self.F[:, [2, 0]]]), axis=1)
        fi = np.tile(np.arange(len(self.F)), 3)
        self.E, einv, cnt = np.unique(E, axis=0, return_inverse=True, return_counts=True)
        order = np.argsort(einv.ravel(), kind="stable")
        start = np.concatenate([[0], np.cumsum(cnt)[:-1]])
        self.fa = fi[order[start]]
        self.fb = np.where(cnt == 2, fi[order[np.minimum(start + 1, len(order) - 1)]], -1)
        self.manifold = cnt == 2


def mesh_view(mesh, view, r, crease_deg=24.0, tol=0.03):
    """hidden-line projection of a mesh: (silhouette rings, visible segments, hidden segments, grid info).
    Z-buffer of the front-facing triangles at r mm; edges drawn = creases (dihedral > crease_deg), view contours
    (front / back facing change) and non-manifold edges; each edge is sampled at r / 2 against the buffer (hidden when
    it lies behind the surface by more than tol + the local depth range, so steep faces do not hide their own edges)."""
    from scipy.ndimage import maximum_filter, minimum_filter
    ua, va, da, ds = VIEWS[view]
    P = mesh.T[:, :, [ua, va, da]].copy()
    P[:, :, 2] *= ds
    dirv = np.zeros(3)
    dirv[da] = ds
    facing = mesh.N @ dirv
    u0, v0 = P[:, :, 0].min() - 2 * r, P[:, :, 1].min() - 2 * r
    u1, v1 = P[:, :, 0].max() + 2 * r, P[:, :, 1].max() + 2 * r
    W, H = int(math.ceil((u1 - u0) / r)) + 1, int(math.ceil((v1 - v0) / r)) + 1
    zb = np.full((H, W), -np.inf)
    for t in P[facing > 1e-6]:
        a, b, c = t
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        i0 = max(int(math.ceil((t[:, 0].min() - u0) / r - 0.5)), 0)
        i1 = min(int(math.floor((t[:, 0].max() - u0) / r - 0.5)), W - 1)
        j0 = max(int(math.ceil((t[:, 1].min() - v0) / r - 0.5)), 0)
        j1 = min(int(math.floor((t[:, 1].max() - v0) / r - 0.5)), H - 1)
        if i1 < i0 or j1 < j0:
            continue
        xs = u0 + (np.arange(i0, i1 + 1) + 0.5) * r
        ys = v0 + (np.arange(j0, j1 + 1) + 0.5) * r
        X, Y = np.meshgrid(xs, ys)
        w1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
        w2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
        w3 = 1 - w1 - w2
        ins = (w1 >= -1e-7) & (w2 >= -1e-7) & (w3 >= -1e-7)
        if not ins.any():
            continue
        d = w1 * a[2] + w2 * b[2] + w3 * c[2]
        sub = zb[j0:j1 + 1, i0:i1 + 1]
        np.maximum(sub, np.where(ins, d, -np.inf), out=sub)
    mask = np.isfinite(zb)
    # silhouette rings (world u, v)
    pad = np.zeros((H + 2, W + 2))
    pad[1:-1, 1:-1] = mask
    rings = []
    for Lc in contourpy.contour_generator(z=pad, line_type="Separate").lines(0.5):
        w = [(u0 + (cc - 1 + 0.5) * r, v0 + (rr - 1 + 0.5) * r) for cc, rr in Lc]
        if len(w) >= 4:
            rings.append(_rdp(w, r * 0.6))
    # edges to draw
    Nf = mesh.N
    fa, fb, man = mesh.fa, mesh.fb, mesh.manifold
    fbs = np.where(man, fb, fa)
    crease = np.einsum("ij,ij->i", Nf[fa], Nf[fbs]) < math.cos(math.radians(crease_deg))
    front = facing > 1e-6
    contour = front[fa] != front[fbs]
    sel = (~man) | crease | contour
    A = mesh.V[mesh.E[sel, 0]][:, [ua, va, da]] * np.array([1, 1, ds])
    B = mesh.V[mesh.E[sel, 1]][:, [ua, va, da]] * np.array([1, 1, ds])
    L2 = np.hypot(B[:, 0] - A[:, 0], B[:, 1] - A[:, 1])
    ok = L2 > 1e-4
    A, B, L2 = A[ok], B[ok], L2[ok]
    zc = np.where(mask, zb, 0.0)
    zmax3 = maximum_filter(np.where(mask, zb, np.inf), size=3, mode="constant", cval=np.inf)
    zmin3 = minimum_filter(np.where(mask, zb, -np.inf), size=3, mode="constant", cval=-np.inf)
    rng = zmax3 - zmin3                                   # inf next to the silhouette / a see-through hole
    vis, hid = [], []
    for a, b, L in zip(A, B, L2):
        n = max(2, int(math.ceil(L / (0.5 * r))) + 1)
        t = np.linspace(0.0, 1.0, n)
        pu = a[0] + (b[0] - a[0]) * t
        pv = a[1] + (b[1] - a[1]) * t
        pd = a[2] + (b[2] - a[2]) * t
        ii = np.clip(((pu - u0) / r).astype(int), 0, W - 1)
        jj = np.clip(((pv - v0) / r).astype(int), 0, H - 1)
        m = mask[jj, ii]
        hidden = m & (pd < zc[jj, ii] - tol - rng[jj, ii])
        # runs of equal state -> sub-segments
        k0 = 0
        for k in range(1, n + 1):
            if k == n or hidden[k] != hidden[k0]:
                ta, tb = t[k0], t[k - 1]
                if k0 > 0:
                    ta = (t[k0 - 1] + t[k0]) / 2
                if k < n:
                    tb = (t[k - 1] + t[k]) / 2
                seg = (a[0] + (b[0] - a[0]) * ta, a[1] + (b[1] - a[1]) * ta, a[0] + (b[0] - a[0]) * tb, a[1] + (b[1] - a[1]) * tb)
                (hid if hidden[k0] else vis).append(seg)
                k0 = k
    return dict(rings=rings, vis=vis, hid=hid, u0=u0, v0=v0, r=r, mask=mask)


def seg_path(v, segs, ox, oy):
    """one path for many segments; coincident segments (e.g. the top and bottom edge of a wall seen from above)
    are written once; 0.01 mm is far below a pixel at these scales."""
    seen, out = set(), []
    for a, b, c, d in segs:
        p, q = (round(a + ox, 2), round(-(b + oy), 2)), (round(c + ox, 2), round(-(d + oy), 2))
        k = (p, q) if p <= q else (q, p)
        if k in seen or p == q:
            continue
        seen.add(k)
        out.append(f"M{p[0]:g},{p[1]:g}L{q[0]:g},{q[1]:g}")
    return "".join(out)


def _wrap(v, s, width, size_px):
    """split s into lines no wider than width (world), breaking after a space / comma / slash when possible."""
    out, cur = [], ""
    for ch in s:
        if v.text_w(cur + ch, size_px) > width and cur:
            k = max(cur.rfind(" "), cur.rfind(","), cur.rfind("/"), cur.rfind("·"))
            if k > len(cur) * 0.5:
                out.append(cur[:k + 1].rstrip())
                cur = cur[k + 1:].lstrip() + ch
            else:
                out.append(cur)
                cur = ch
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def mask_extent(mv, axis, end):
    """world coordinate (other axis) of the silhouette pixel nearest the low side at the extreme column / row:
    axis 'u' -> at the min / max u column, the lowest v; axis 'v' -> at the min / max v row, the leftmost u."""
    m, r = mv["mask"], mv["r"]
    js, is_ = np.nonzero(m)
    if axis == "u":
        i = is_.min() if end == "lo" else is_.max()
        return mv["v0"] + (js[is_ == i].min() + 0.5) * r
    j = js.min() if end == "lo" else js.max()
    return mv["u0"] + (is_[js == j].min() + 0.5) * r


def cell_stage0(p, test_title, set_tag, CW=480.0, HD=250.0):
    """one part: front / top / right projections of its STL (third angle), overall bbox dimensions, the numbers of
    stage0_geometry.json (key_dims, print, qty, mass, volume) as text."""
    X, Y, Z = p["bbox"]
    T = stl_load(os.path.join(S0DIR, p["stl"]))
    mesh = Mesh(T)
    lo = T.reshape(-1, 3).min(0)
    Lm, Gfr, Rm, Gtf = 62.0, 40.0, 10.0, 26.0
    s = min((CW - Lm - Gfr - Rm) / (X + Y), (HD - Gtf) / (Y + Z), 16.0)
    r = min(max(0.5 / s, 0.02), 0.2)
    px = lambda q: q / s
    # layout (world mm at this cell's scale): front view lower-left at (0, 0), top view above, right view beside
    title_lines_px = 16.0
    v = View(-px(Lm), -px(400), px(CW - Lm), px(60), px_width=CW, pad_px=4)
    Pp = pids(v)
    top_v = Z + px(Gtf) + Y                                  # top edge of the top view
    # numbers of the part: in the empty quadrant (right of the top view, above the right view) when it is wide and
    # tall enough, else on lines under the title
    info = [f"시험 {test_title}", f"수량 {p['qty']} · {F(p['mass_g_solid'], 1)} g · {F(p['volume_cm3'], 2)} cm³ · 설정 {set_tag}",
            f"외곽 {F(X)} × {F(Y)} × {F(Z)} (x × y × z)"]
    qw_px = CW - Lm - Rm - (X * s + Gfr)
    qh_px = Gtf + Y * s
    lines_q = [w_ for s_ in info for w_ in _wrap(v, s_, px(qw_px), 9.0)]
    in_quad = qw_px >= 170 and len(lines_q) * 13 + 6 <= qh_px
    if not in_quad:
        lines_q = [w_ for s_ in info for w_ in _wrap(v, s_, px(CW - 8), 9.0)]
    head_h = 0.0 if in_quad else len(lines_q) * 13 + 4
    name_lines = _wrap(v, f"{p['id']}  {p['name_ko']}", px(CW - 8), 11.5)
    y_title = top_v + px(head_h + 14 + title_lines_px * (len(name_lines) - 1)) + px(10)
    v.v1 = y_title + px(16)
    for i, ln_ in enumerate(name_lines):
        v.text(-px(Lm - 4), y_title - i * px(title_lines_px), ln_, cls="ttl", anchor="start", size_px=11.5)
    if in_quad:
        qu, qv = X + px(Gfr), top_v - px(10)
    else:
        qu, qv = -px(Lm - 4), y_title - (len(name_lines) - 1) * px(title_lines_px) - px(16)
    for i, s_ in enumerate(lines_q):
        v.text(qu, qv - i * px(13), s_, cls="lt" if s_.startswith("시험") else "tx-s", anchor="start", size_px=9.0)
    views = {}
    for nm, (ox, oy) in (("front", (0.0, 0.0)), ("top", (0.0, Z + px(Gtf))), ("right", (X + px(Gfr), 0.0))):
        mv = mesh_view(mesh, nm, r)
        ua, va = VIEWS[nm][0], VIEWS[nm][1]
        du, dv = -lo[ua], -lo[va]                             # part min corner -> view origin
        rings = [[(a + du + ox, b + dv + oy) for a, b in rg] for rg in mv["rings"]]
        fill_rings(v, rings, "m-print2", None, outline=False)
        if mv["hid"]:
            v.el.append(f'<path class="hid" d="{seg_path(v, mv["hid"], du + ox, dv + oy)}"/>')
        if mv["vis"]:
            v.el.append(f'<path class="ln" d="{seg_path(v, mv["vis"], du + ox, dv + oy)}"/>')
        mv["off"] = (du + ox, dv + oy)
        views[nm] = mv
    # overall dimensions (numbers = stage0_geometry.json bbox)
    fr, tp = views["front"], views["top"]
    ext_lo = mask_extent(fr, "u", "lo") + fr["off"][1]
    ext_hi = mask_extent(fr, "u", "hi") + fr["off"][1]
    v.dim_h(0.0, X, -px(16), text=F(X), ext_from=(ext_lo, ext_hi), size_px=9.5)
    zl = mask_extent(fr, "v", "lo") + fr["off"][0]
    zh = mask_extent(fr, "v", "hi") + fr["off"][0]
    short = lambda L: "left" if L * s < 34 else None          # short span: horizontal label beside the line
    v.dim_v(0.0, Z, -px(18), text=F(Z), ext_from=(zl, zh), size_px=9.5, tpos=short(Z))
    yl = mask_extent(tp, "v", "lo") + tp["off"][0]
    yh = mask_extent(tp, "v", "hi") + tp["off"][0]
    v.dim_v(Z + px(Gtf), Z + px(Gtf) + Y, -px(18), text=F(Y), ext_from=(yl, yh), size_px=9.5, tpos=short(Y))
    v.text(X / 2, -px(34), "앞", cls="tx-s", size_px=9)
    v.text(X, Z + px(Gtf / 2 - 3), "위", cls="tx-s", anchor="end", size_px=9)
    v.text(X + px(Gfr) + Y / 2, -px(12), "오른쪽", cls="tx-s", size_px=9)
    # key dims + print text under the views
    ty = -px(52)
    body_ = _wrap(v, f"치수: {p['key_dims']}", px(CW - 8), 9.2) + _wrap(v, f"출력: {p['print_ko']}", px(CW - 8), 9.2)
    for i, s_ in enumerate(body_):
        v.text(-px(Lm - 4), ty - i * px(12.5), s_, cls="lt" if s_.startswith("치수") else "tx-s", anchor="start", size_px=9.2)
    v.v0 = ty - (len(body_) - 1) * px(12.5) - px(8)
    return v, len(mesh.T), sum(len(m["hid"]) for m in views.values())


def zoom_stl(pid, view, win, s_px, title):
    """enlarged hidden-line projection of one stage-0 STL (raw STL coordinates of that view), clipped to win."""
    p = next(q for q in S0["parts"] if q["id"] == pid)
    mesh = Mesh(stl_load(os.path.join(S0DIR, p["stl"])))
    u0, u1, v0, v1 = win
    v = View(u0 - 70 / s_px, v0 - 150 / s_px, u1 + 170 / s_px, v1 + 30 / s_px, px_width=(u1 - u0) * s_px + 240, pad_px=4)
    mv = mesh_view(mesh, view, max(0.5 / s_px, 0.015))
    i0 = kit.clip_begin(v)
    fill_rings(v, mv["rings"], "m-print2", None, outline=False)
    if mv["hid"]:
        v.el.append(f'<path class="hid" d="{seg_path(v, mv["hid"], 0.0, 0.0)}"/>')
    if mv["vis"]:
        v.el.append(f'<path class="ln" d="{seg_path(v, mv["vis"], 0.0, 0.0)}"/>')
    # r4.5 fix 3: the projected edges are recorded as strokes, so label placement (kit.tail_text) can avoid them
    v.segs += [(a, b, c, d) for a, b, c, d in list(mv["vis"] or []) + list(mv["hid"] or [])
               if u0 - 1 <= min(a, c) and max(a, c) <= u1 + 1 and v0 - 1 <= min(b, d) and max(b, d) <= v1 + 1]
    kit.clip_end(v, i0, u0, u1, v0, v1)
    panel_title(v, u0 - 65 / s_px, v1 + 14 / s_px, title, size_px=11.5)
    return v


def _dim_al(v, a, b, off_px, text, size_px=9.5):
    """aligned dimension a-b (same drawing as render_v4.dim_aligned)."""
    import render_v4 as R4
    R4.dim_aligned(v, a, b, off_px, text, size_px=size_px)


def spring_rig_details():
    """r4.5 fix: enlarged views of the spring rig (test 8 / 13): C06b = the model's own hub pocket section (pieces A + B:
    pocket, captured short-leg groove with its blind end in the web stub, insertion slot along the leg, long-leg window)
    on a 2.0 hub spacer, seen from above (the print frame mirrors the lever frame: (u, v) = (y - Ly, -(z - Lz))), and
    C06a's rear-wall groove mouth seen from the front (groove on the long leg x, width x depth about the rod axis).
    Numbers = geometry.json solved.spring (the replica is the model's hub) and stage0_geometry.json key_dims."""
    sp = kit.SOL["spring"]
    slg = sp["short_leg_groove"]
    L_ = kit.G["key_points"]["white D"]["L"]
    vec = lambda d: (math.cos(math.radians(d)), -math.sin(math.radians(d)))      # lever-frame direction -> print frame
    add = lambda *ps: (sum(p_[0] for p_ in ps), sum(p_[1] for p_ in ps))
    mul = lambda k, p_: (k * p_[0], k * p_[1])
    rel = lambda q: (q[0] - L_[0], -(q[1] - L_[1]))                                # model (y, z) -> print (u, v)
    # --- C06b, top view (X, Y), hub centre at the STL origin; the web stub is clipped at R10.5
    p06b = next(q for q in S0["parts"] if q["id"] == "C06b")
    m_r = re.search(r"R([\d.]+)에서 자름", p06b["key_dims"])
    R_cut = float(m_r.group(1)) if m_r else 10.5
    m_h = re.search(r"허브 R([\d.]+)", p06b["key_dims"]) or re.search(r"허브 Ø([\d.]+)", p06b["key_dims"])
    r_hub = float(m_h.group(1)) if "허브 R" in m_h.group(0) else float(m_h.group(1)) / 2
    su = 32.0
    win = (-R_cut - 0.3, 6.6, -R_cut - 0.3, 6.6)
    vb = zoom_stl("C06b", "top", win, su, "C06b 확대 (위에서, r4.5 고침): 모델 주머니 단면 복제 — 가둠 홈·넣는 슬롯·긴 다리 창 (출력 자세 = 레버의 거울상)")
    vb.cl(win[0] + 0.3, 0, win[1] - 0.3, 0)
    vb.cl(0, win[2] + 0.3, 0, win[3] - 0.3)
    rp = sp["pocket"][0] / 2
    vb.dim_h(-rp, rp, 5.9, text=f"주머니 Ø{F(sp['pocket'][0])} × {F(sp['pocket'][1])}", ext_from=(0.0, 0.0), size_px=9.5)
    # insertion slot (lever frame 316.83 deg -> print 43.17 deg): 6.5 across at 4.9 along, one real wall (-3.25)
    a_s = sp.get("insertion_slot_deg", sp["slot_deg_lever_frame"])
    t_s, n_s = vec(a_s), vec(a_s + 90.0)
    fa, fb = sp["slot_faces"]
    A_, B_ = add(mul(fa, n_s), mul(4.9, t_s)), add(mul(fb, n_s), mul(4.9, t_s))
    tf_ = math.sqrt(max(r_hub ** 2 - fb * fb, 0.0))
    W_ = add(mul(fb, n_s), mul(tf_, t_s))                                           # the -3.25 wall meets the hub circle
    vb.line(W_[0] + t_s[0] * vb.px(2), W_[1] + t_s[1] * vb.px(2), B_[0], B_[1], cls="ex")
    vb.line(*add(mul(fa, n_s), mul(math.sqrt(max(rp * rp - fa * fa, 0.0)), t_s)), *A_, cls="phan")
    _dim_al(vb, A_, B_, 0, "")
    cl_end = 6.2
    vb.cl(0, 0, *mul(cl_end, t_s))
    mid = add(mul(0.5, add(A_, B_)), mul(cl_end - 4.9 + vb.px(5), t_s))     # r4.5 fix 3: text starts past the centre line's end
    kit.halo1(vb, mid[0], mid[1] - vb.px(1), f"넣는 슬롯 {F(fa - fb)} (±{F2(fa)}, {F(a_s)}° 거울상)", cls="dt", anchor="start", size_px=9.5, dy_px=3.5)
    # long-leg window (35 deg, upper face +2.6) mirrored
    a_w, f_w = slg.get("window", sp.get("window", [35.0, 2.6]))
    t_w, n_w = vec(a_w), vec(a_w + 90.0)
    vb.cl(0, 0, *mul(cl_end, t_w))
    Wc, Wf = mul(5.2, t_w), add(mul(5.2, t_w), mul(f_w, n_w))
    vb.line(*add(mul(f_w, n_w), mul(math.sqrt(max(r_hub ** 2 - f_w * f_w, 0.0)), t_w)), *Wf, cls="ex")
    _dim_al(vb, Wc, Wf, 0, "")
    We = add(mul(cl_end, t_w), mul(vb.px(5), t_w))                          # r4.5 fix 3: past the centre line's end
    kit.halo1(vb, We[0], We[1] - vb.px(1), f"긴 다리 창 {F(a_w)}° 윗면 +{F(f_w)} (거울상)", cls="dt", anchor="start", size_px=9.5, dy_px=3.5)
    # captured groove: faces nn from the axis along the band normal (band_deg + 90), mirrored; blind end at ss1
    bd = slg.get("band_deg", slg["leg_dir"])
    t_g, n_g = vec(bd), vec(bd + 90.0)
    nn1_ = slg["nn"][1]
    taken_ = []
    for k_, r_ in enumerate(slg["nn"]):
        _dim_al(vb, (0.0, 0.0), mul(r_, n_g), 10 + 24 * k_, "")
    for k_, r_ in enumerate(slg["nn"]):
        # r4.5 fix 3: value outboard past the groove-face arrowhead (tail of the dimension line), in the first clear
        # spot (no edge / centre line / other label through it), white halo
        Bk = add(mul(r_, n_g), mul(vb.px(10 + 24 * k_), (n_g[1], -n_g[0])))
        kit.tail_text(vb, Bk, n_g, F2(r_), (nn1_ - r_) + vb.px(10), (nn1_ - r_) + vb.px(120), taken=taken_)
    band = [rel(q) for q in slg["band"]]
    tip_ = rel(slg["O"])
    vb.circle(tip_[0], tip_[1], vb.px(2.4), cls="dot")
    kit.leader_to(vb, *mul(0.5, add(band[2], band[3])), win[0] + 0.6, -R_cut + 2.0,
                  f"막힌 끝 (다리 끝 + 0.3), 축에서 {F2(slg['tip_r'] + 0.3)} 안쪽", size_px=9)
    note_lines(vb, [f"가둠 홈 폭 {F2(slg.get('width', slg['nn'][1] - slg['nn'][0]))}: 축에서 {F2(slg['nn'][0])}~{F2(slg['nn'][1])}, 레버 {F2(bd)}° 방향 (출력 자세 거울상 {F2(-bd % 360)}°), ss {kit.FR(slg['ss'][0], slg['ss'][1])}",
                    f"모델 허브(model_v4.hub_pocket_poly 조각 A + B)를 그대로 복제, R{F(R_cut)}에서 자름 — 웹 조각 속 막힌 끝·안 면·바깥 면이 생산 레버와 같음",
                    f"시험 13: 짧은 다리 끝을 가둠 홈 입구에 대고 홈을 따라 밀면 코일이 넣는 슬롯으로 주머니에 앉고 다리가 막힌 끝까지 (3/3)"],
               win[0] - 60 / su, win[2] - 20 / su, line_px=14, size_px=9.5)
    # --- C06a, front view (X = y - Ly, Z = print height) around the groove boss
    y_bot = sp["groove"][0] + sp["groove"][4]
    uf, ub = sp["groove"][0] - L_[0], y_bot - L_[0]
    p06 = next(q for q in S0["parts"] if q["id"] == "C06a")
    m_ = re.search(r"폭 ([\d.]+) \((?:긴 다리|코일 가운데) x([\d.]+) ±([\d.]+)", p06["key_dims"])
    xw, xl, xh = (float(t_) for t_ in m_.groups())
    va = zoom_stl("C06a", "front", (uf - 1.6, uf + 7.4, 2.4, 11.4), 40.0, f"C06a 확대 (앞에서, r4.5 고침): 뒷벽 홈 입구 — 폭 {F(sp['groove'][3])} × 깊이 {F(sp['groove'][4])}, 긴 다리 x")
    # the groove's print-height range, read from the STL: the groove bottom plane X = ub carries its edges
    Vq = Mesh(stl_load(os.path.join(S0DIR, p06["stl"]))).V
    zq = Vq[np.abs(Vq[:, 0] - ub) < 2e-3][:, 2]
    zg0, zg1 = float(zq.min()), float(zq.max())
    va.dim_v(zg0, zg1, uf - 0.9, text=F(zg1 - zg0), ext_from=(uf, uf), size_px=9.5)
    va.dim_h(uf, ub, zg1 + 1.6, text=f"{F(ub - uf)} = 홈 바닥 y{F2(y_bot)}", ext_from=(zg1, zg1), size_px=9.5)
    note_lines(va, [f"보스 면 = 모델 뒷벽 보스 면 y{F(sp['groove'][0])} (봉 축에서 {F2(uf)}), 홈 z{F(sp['groove'][1])}~{F(sp['groove'][2])}",
                    f"홈 가운데 = 긴 다리 x{F(xl)} ± {F(xh)} (코일 가운데 + {F(sp.get('groove_dx', 0.8))}, 모듈 뒷벽 홈과 같음, P18)"],
               uf - 1.6 - 60 / 40.0, 2.4 - 20 / 40.0, line_px=14, size_px=9.5)
    return [vb, va]


def c17_plan(W_px=976.0, s=3.1):
    """r4.5 fix 3: C17a (test 21 support comb) enlarged plan, drawn beside its 3-view cell.
    Part = hidden-line projection of the C17a STL from above (STL = model x, y: the comb's x0 is the module's x0).
    Numbers of the comb (tooth x edges, tooth width, fin lines, rear bar, rail-free span, height) = stage0_geometry.json
    analysis.C17 (the same run's key_dims text quotes them rounded); test label / pass / deflections = tests[21].
    The module footprint over it (phantom): balance rail, board hatch, F|F# fin + keel = geometry.json plan (the model
    the stage-0 generator read) - stage0_geometry.json does not carry them."""
    p = next(q for q in S0["parts"] if q["id"] == "C17a")
    A = S0["analysis"]["C17"]
    tk = next(k for k, t in S0["tests"].items() if "C17a" in t["parts"])
    t21 = S0["tests"][tk]
    dz = t21["design"]
    X, Y, Z = p["bbox"]
    teeth, bar, free, lines = A["teeth"], A["rear_bar"], A["rail_free"], A["fin_lines"]
    rail = kit.plan_item("balance rail")["poly"]
    hatch_ = next(q for q in kit.PLAN if q["part"].startswith("floor hatch"))["poly"]
    keel = next(q for q in kit.PLAN if q["part"].startswith("F|F# fin keel"))["poly"]
    kx0, kx1, ky0, ky1 = bbox(keel)
    fin_ff = next(q["poly"] for q in kit.PLAN if q["part"] == "fin" and bbox(q["poly"])[0] <= kx0 and kx1 <= bbox(q["poly"])[1])
    rx0, rx1, ry0, ry1 = bbox(rail)
    hx0, hx1, hy0, hy1 = bbox(hatch_)
    # the comb must leave the rail span and the hatch free (what the generator asserts), and its x0 is the module's
    assert teeth[1][1] < hx0 and teeth[2][0] > hx1 and bar[2] > hy1 and abs(free[0] - teeth[1][1]) < 1e-6 and abs(free[1] - teeth[2][0]) < 1e-6
    assert not any(a_ < kx1 and kx0 < b_ for a_, b_ in teeth), "a tooth under the F|F# keel"
    Lm, Tm = 96.0, 70.0
    Rm = W_px - Lm - X * s
    px = lambda q: q / s
    v = View(-px(Lm), -px(120), X + px(Rm), Y + px(Tm), px_width=W_px, pad_px=4)
    # the part (STL projection, same drawing as the 3-view cells)
    mesh = Mesh(stl_load(os.path.join(S0DIR, p["stl"])))
    lo = mesh.T.reshape(-1, 3).min(0)
    assert np.allclose(lo, 0.0, atol=1e-6), lo            # STL in model x, y (no offset)
    mv = mesh_view(mesh, "top", max(0.5 / s, 0.02))
    # where the module must hang free over the desk (paper strip passes): rail span between the teeth + board hatch
    free_zone = [(free[0], ry0), (free[1], ry0), (free[1], ry1), (free[0], ry1)]
    for poly in (free_zone, hatch_):
        v.el.append(f'<polygon class="zone" style="stroke:none" points="{" ".join(v.P(a, b) for a, b in poly)}"/>')
    fill_rings(v, mv["rings"], "m-print2", None, outline=False)
    if mv["hid"]:
        v.el.append(f'<path class="hid" d="{seg_path(v, mv["hid"], 0.0, 0.0)}"/>')
    if mv["vis"]:
        v.el.append(f'<path class="ln" d="{seg_path(v, mv["vis"], 0.0, 0.0)}"/>')
    v.segs += list(mv["vis"] or [])
    # module footprint over the comb (phantom): balance rail, board hatch, F|F# fin + keel; fin lines = centre lines
    for poly in (rail, hatch_, fin_ff, keel):
        v.poly([tuple(q) for q in poly], cls="phan")
    for xl in lines:
        v.cl(xl, -px(6), xl, Y + px(6))
    # --- dimensions: overall (bbox), teeth x (ordinates), tooth width, rail-free span, tooth length + rear bar
    v.dim_h(0.0, X, Y + px(24), text=f"{F(X)} = 뒤 막대 x{F(bar[0])}~{F(bar[1])}", ext_from=(Y, Y), size_px=9.5)
    v.dim_v(0.0, Y, -px(64), text=F(Y), ext_from=(0.0, 0.0), size_px=9.5)
    # the left edge x0 runs straight from y0 to the back (tooth 1 + bar): y209 is taken from the bar's front edge at
    # tooth 1's inner face (x3), the extension line crosses that tooth
    v.dim_v(0.0, bar[2], -px(30), text=f"{F(bar[2])} 이 길이", ext_from=(0.0, teeth[0][1]), size_px=9.5)
    v.dim_v(bar[2], bar[3], -px(30), text=F(bar[3] - bar[2]), ext_from=(teeth[0][1], 0.0), size_px=9.5, tpos="left")
    feats = [(e, 0.0, "") for t_ in teeth for e in t_] + [(xl, -px(6), "핀 선") for xl in lines]
    boxes = kit.ordy(v, feats, -px(16), side="below", gap_px=12.5, label_px=9.5, prefix="x", nd=2)
    y_tw = 0.30 * ry0
    v.dim_h(teeth[1][0], teeth[1][1], y_tw, text=f"이 폭 {F(A['tooth_w'])} (4개 모두)", ext_from=(y_tw, y_tw), size_px=9.5, tpos="right")
    y_fr = ry0 - px(14)
    v.dim_h(free[0], free[1], y_fr, text=f"{F(free[1] - free[0])} 레일 밑 빔 (x{F(free[0])}~{F(free[1])})",
            ext_from=(y_fr, y_fr), size_px=9.5)
    # --- labels of the module footprint (right column), leaders to the features; the hatch outline's main back edge
    # and the notch behind it (USB receptacle) are read from the plan polygon
    hy_main = max(q[1] for q in hatch_ if abs(q[0] - hx0) < 1e-6)
    notch = sorted(q[0] for q in hatch_ if abs(q[1] - hy1) < 1e-6)
    uL = X + px(46)
    lab = [(((free[0] + free[1]) / 2 + px(40), (ry0 + ry1) / 2), ry1 - px(2),
            [f"밸런스 레일 y{F(ry0)}~{F(ry1)} (모델): 핀 선의 이에만 얹힘"]),
           (((kx0 + kx1) / 2, (ky0 + ky1) / 2), ky1 + px(24),
            [f"F|F# 킬 y{F(ky0)}~{F(ky1)} · 핀 앞끝 y{F(bbox(fin_ff)[2])}", "기판 구멍 안: 이 없음 (받치면 레일 가운데를 받침)"]),
           ((hx1 - px(20), (hy0 + hy_main) / 2 + px(10)), (hy0 + hy_main) / 2 + px(10),
            [f"기판 구멍 x{F(hx0)}~{F(hx1)} · y{F(hy0)}~{F(hy_main)} (바닥 없음)",
             f"(x{F(notch[0])}~{F(notch[-1])}은 y{F(hy1)}까지): 밑은 빔"]),
           ((X - px(40), (bar[2] + bar[3]) / 2), Y - px(4), [f"뒤 막대 y{F(bar[2])}~{F(bar[3])} = 뒷벽 밑"])]
    for (fu, fv), tv, ls_ in lab:
        kit.leader_to(v, fu, fv, uL, tv, ls_[0], size_px=9.5)
        for i_, s_ in enumerate(ls_[1:], 1):
            v.text(uL + px(7.5), tv - i_ * px(13), s_, cls="lt", anchor="start", size_px=9.5, dy_px=3.8)
    # --- notes under the ordinates: test 21 + why nothing sits under the rail / hatch
    EF = lambda k: F(dz[k], 3)
    notes = [(f"시험 {t21['no']} {t21['title_ko']}", "ttl"),
             (f"합격: {t21['pass_ko']}", "lt"),
             (f"C17a 역할: {p['purpose_ko']}.", "tx-s"),
             (f"왜 레일·기판 구멍 밑이 빈가: 쓰임에서는 패드가 윗판을 밑에서 밀어 올려 F|F# 핀·킬이 밸런스 레일 뒷면을 위로 당기고, 레일은 핀 선 사이에서 들린다. "
              f"모듈을 바닥 EVA에 둔 채 위에서 누르면 레일·바닥 띠가 EVA에 얹혀 레일이 단단한 것처럼 읽힌다 (E·F {EF('EF_rail_rigid')} mm) — 약한 레일도 합격이 나온다.", "tx-s"),
             (f"그래서 빗은 핀 선 {len(lines)}줄(이 폭 {F(A['tooth_w'])})과 뒷벽(뒤 막대)만 받치고, 레일 밑 x{F(free[0])}~{F(free[1])}과 기판 구멍 밑은 비운다. 모델이 선형이므로 위에서 누른 정하중이 쓰임과 같은 레일 휨을 만든다. "
              f"구멍 가장자리를 받치면 레일이 거기서 물린 셈 (E·F {EF('EF_rail_hatch_clamped')} mm), 구멍 안의 F|F# 핀·킬 발을 받치면 레일 가운데를 받치는 셈이다.", "tx-s"),
             (f"모델(레일 = 핀 선 위 연속 보) E·F {EF('EF_model')} mm, 레일이 이웃 핀 선 사이 단순 지지뿐이면 {EF('EF_rail_simply_supported')} mm (한계 {F(dz['limit'], 2)} 넘음) — 이 시험이 둘을 가른다. "
              f"확인: {t21['csv'][-1][2]}.", "tx-s"),
             (f"빗 높이 {F(A['h'])} = 바닥 EVA 대신 (EVA 뗌) · 하중 {'-'.join(dz['keys'])} 여섯 자리 × {F(dz['F'], 0)} N = {F(A['kg'], 1)} kg", "tx-s"),
             ("보라 1점 쇄선 = 모듈 (geometry.json plan) · 연주황 = 책상에서 떠 있어야 하는 곳 · 가는 1점 쇄선 = 핀 선", "tx-s")]
    ty = min(b_[2] for b_ in boxes) - px(18)
    k = 0
    for s_, cls_ in notes:
        for ln_ in _wrap(v, s_, px(W_px - 16), 9.5):
            v.text(-px(Lm - 6), ty - k * px(14), ln_, cls=cls_, anchor="start", size_px=10.5 if cls_ == "ttl" else 9.5)
            k += 1
    v.v0 = ty - (k - 1) * px(14) - px(8)
    panel_title(v, -px(Lm - 6), Y + px(Tm - 16),
                f"C17a 평면 확대 (위에서) — 시험 {t21['no']} 받침 빗: 이 {len(teeth)}개는 핀 선 밑, 뒤 막대는 뒷벽 밑, 레일·기판 구멍 밑은 빔", size_px=11.5)
    return v


def sheet_stage0():
    tests = S0["tests"]
    order = [str(t) for t in sorted((int(k) for k in tests if k.isdigit()))] + [k for k in tests if not k.isdigit()]
    tag = {}
    for p in S0["parts"]:
        tag.setdefault(p["settings"], f"S{len(tag) + 1}")
    # r4.5: the coupons grouped by what they test (one sheet section each); a part used by several tests is drawn once,
    # in the first section that uses it; tests not named here fall into a last section (nothing is dropped)
    sections = [("가. 업스톱 경로 — 패드·앞 펠트·윗판 처짐·패드 바 잎·층간 강도·윗판 브리지", ["1", "2", "3", "4", "12", "15", "16"]),
                ("나. 건반 — 스냅 노치·가이드 탭 천·DW/UW·밸런스 핀 압입·캡스턴 너트 트랩·펠트 두께", ["5", "6", "7", "P", "C", "T"]),
                (f"다. 레버 — 비틀림 스프링 (r4.5 미스미 {kit.SOL['spring']['part']})·스프링 넣기 (가둠 홈)·강철 블록 접착 (MS 폴리머)",
                 ["8", "13", "20"]),
                ("라. 회로 맞춤 — USB-C 케이블 몰드 게이지", ["19"]),
                ("마. 첫 모듈 정하중 — 받침 빗 (핀 선·뒷벽만 받침, 레일·기판 구멍 밑은 빔)", ["21"])]
    named = {k for _, ks in sections for k in ks}
    rest_ = [k for k in order if k not in named and tests[k]["parts"] != ["-"]]
    if rest_:
        sections.append(("바. 기타 시험", rest_))
    rows_ = []
    seen = set()
    cells = []
    for title_, keys_ in sections:
        sec = []
        for k in keys_:
            if k not in tests:
                continue
            t = tests[k]
            for pid in t["parts"]:
                p = next((q for q in S0["parts"] if q["id"] == pid), None)
                if p is None or pid in seen:
                    continue
                seen.add(pid)
                other = [str(tests[j]["no"]) for j in order if j != k and pid in tests[j]["parts"]]
                ttl = f"{t['no']} {t['title_ko']}" + (f" (시험 {', '.join(other)}에도 씀)" if other else "")
                sec.append(cell_stage0(p, ttl, tag[p["settings"]]))
        if not sec:
            continue
        hv = View(0, -34, 1480, 0, px_width=1480, pad_px=4)
        hv.line(4, -30, 1476, -30, cls="dm")
        hv.text(6, -20, f"{title_} — 부품 {len(sec)}개 (시험 {', '.join(str(tests[k]['no']) for k in keys_ if k in tests)})", cls="ttl", anchor="start", size_px=14)
        rows_.append([hv])
        rows_ += [[c[0] for c in sec[i:i + 3]] for i in range(0, len(sec), 3)]
        if "8" in keys_:                     # r4.5: the spring rig's new features enlarged (C06b hub replica, C06a groove)
            rows_.append(spring_rig_details())
        if "21" in keys_ and any(c_[0] is rows_[-1][0] for c_ in sec) and len(rows_[-1]) == 1:
            rows_[-1].append(c17_plan())     # r4.5 fix 3: C17a plan enlarged beside its 3-view cell (test 21)
        cells += sec
    missing = [p["id"] for p in S0["parts"] if p["id"] not in seen]
    assert not missing, missing
    # notes: tests (pass numbers), settings legend
    nv = View(0, -700, 1480, 0, px_width=1480, pad_px=6)
    lines = ["시험별 합격 기준 (stage0_geometry.json tests; 절차·측정법·결과별 모델 수정은 stage0_procedure.md):"]
    no_parts = []
    for k in order:
        t = tests[k]
        if t["parts"] == ["-"]:
            no_parts.append(f"{t['no']} {t['title_ko']}")
            continue
        lines += _wrap(nv, f"  시험 {t['no']} {t['title_ko']} — {' · '.join(t['parts'])} — 합격: {t['pass_ko']}", 1460, 10)
    lines += _wrap(nv, "  부품 없이 조립 건반으로 하는 시험: " + " · ".join(no_parts), 1460, 10)
    lines.append("출력 설정:")
    for st, tg in tag.items():
        lines += _wrap(nv, f"  {tg} = {st}", 1460, 10)
    lines.append(f"STL {len(S0['parts'])}개 = stage0/stl (생성기 {S0['generator']}, 모델 {S0['model_version']}, {S0['created']}) · 베드 {' × '.join(F(b, 0) for b in S0['bed_mm'])} 안에 모두 들어감"
                 if all(p["fits_bed"] for p in S0["parts"]) else "베드에 안 들어가는 부품 있음: " + ", ".join(p["id"] for p in S0["parts"] if not p["fits_bed"]))
    note_lines(nv, lines, 6, -14, line_px=15.5, size_px=10)
    nv.v0 = -14 - len(lines) * 15.5 - 6
    rows_.append([nv])
    base = os.path.join(kit.HERE, "d15_stage0_coupons")
    page(rows_, base, "도면 15. 단계 0 시편·지그",
         "단위 mm · 숫자 = stage0_geometry.json (외곽 = bbox, 치수·출력 글 = key_dims·print_ko, 수량·질량·부피) · 그림 = 같은 생성기 실행의 STL을 투영한 3각법 "
         "(앞 · 위 · 오른쪽, 출력 자세: z0 = 베드) · 실선 = 보이는 모서리, 가는 점선 = 숨은 모서리, 연녹 = 출력 부품")
    n_parts = len(S0["parts"])
    n_tests = sum(1 for k in order if tests[k]["parts"] != ["-"])
    kor_n = {3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱"}
    c17a = S0["analysis"]["C17"]
    c17t = next(t for t in tests.values() if "C17a" in t["parts"])
    ffy = bbox(next(q for q in kit.PLAN if q["part"].startswith("F|F# fin keel"))["poly"])[3]
    SHEETS.append(dict(n=15, title_ko="단계 0 시편·지그",
                       caption_ko=(f"단계 0 시험 키트의 출력 부품 {n_parts}개(시험 {n_tests}가지)를 무엇을 시험하는지에 따라 {kor_n[len(sections)]} 묶음(업스톱 경로 · 건반 · 레버·스프링·강철 접착 · 회로 맞춤 · 첫 모듈 정하중{' · 기타' if rest_ else ''})으로 나눠 그린 부품도 (r4.5 고침: C06a 뒷벽 홈 2.4·보스 4.4를 긴 다리 x(코일 가운데 +0.8)에, C06b = 모델 주머니 단면(가둠 홈 폭 0.7·넣는 슬롯 6.5·긴 다리 창) + 허브 받침 2.0, 봉 18, 시험 13 = 가둠 홈에 스프링 넣기; 다 묶음 아래에 C06b 주머니 단면(위에서)과 C06a 홈 입구(앞에서)를 크게 그려 치수. "
                                   f"r4.5 고침 3: 마 묶음 = 시험 {c17t['no']} 받침 빗 C17a — 3각법 칸 옆에 평면을 크게 그려 이 {len(c17a['teeth'])}개(폭 {F(c17a['tooth_w'])} × 길이 {F(c17a['rear_bar'][2])})의 x 가장자리·핀 선 x{' / '.join(F(x_) for x_ in c17a['fin_lines'])}, 뒤 막대 y{F(c17a['rear_bar'][2])}~{F(c17a['rear_bar'][3])}(뒷벽 밑), 레일 밑 빔 x{F(c17a['rail_free'][0])}~{F(c17a['rail_free'][1])}의 폭을 치수하고, "
                                   f"모듈 발자국(밸런스 레일, 기판 구멍, F|F# 핀 앞끝 y{F(ffy)}·킬 — geometry.json plan)을 보라 1점 쇄선으로 겹쳐 레일·기판 구멍 밑을 왜 비우는지(위에서 누른 정하중 = 쓰임과 같은 레일 휨) 적음). 부품마다 출력 자세(z0 = 베드)의 앞·위·오른쪽 3각법 투영"
                                   f"(STL에서 보이는 모서리는 실선, 숨은 모서리는 점선)과 외곽 치수 x × y × z, 그 아래 key_dims(구멍·날·간격 등 부품 치수)와 출력 방향 글, "
                                   f"오른쪽 위에 시험 번호·수량·질량·설정 기호. 맨 아래는 시험별 합격 기준과 출력 설정 {len(tag)}종. 숫자는 모두 stage0_geometry.json (C17a 평면에 겹친 모듈 발자국만 geometry.json plan)."),
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))
    return cells


if __name__ == "__main__":
    import sys
    which = [int(a) for a in sys.argv[1:]] or [14, 15]
    if 14 in which:
        sheet_tools14()
    if 15 in which:
        sheet_stage0()
    print("T ids used:", ", ".join(sorted(USED_T)))
