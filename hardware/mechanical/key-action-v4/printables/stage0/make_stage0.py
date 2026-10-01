#!/usr/bin/env python3
"""Toccata v4 W1+ - stage-0 test kit (issue 6 of round r4.4).

Builds a ready-to-print coupon / fixture kit for every test of DESIGN.md section 17 from the single model:
  - stage0_geometry.json      coupon / fixture dimensions (ids C01a ..), model values used, pass lines, sensitivities
  - stl/*.stl                 one file per printed part, already in print orientation (z up = build direction)
  - png/*.png                 quick render of every STL (read back from the STL, not from the SCAD source)
  - scad/*.scad               generated OpenSCAD sources
  - stage0_procedure.md       Korean step-by-step procedure with results tables
  - stage0_results_template.csv

Usage:  MODEL_DIR=<folder with model_v4.py + metrics.json> python make_stage0.py
MODEL_DIR defaults to ../ (scratchpad/v4/final).  Nothing is written outside this script's folder.

Every number a test cites is read or computed here from model_v4 (P, build_geo, plate_fe, lever_body, PadTable,
notch_block_poly, leaf / spring parameters) or from MODEL_DIR/metrics.json (sensitivities, results).  Numbers that the
model does not have (e.g. the balance-pin press-fit force) are marked 'proposal' in the outputs.
"""
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.abspath(os.environ.get("MODEL_DIR", os.path.join(HERE, "..")))
sys.path.insert(0, MODEL_DIR)
sys.dont_write_bytecode = True
import numpy as np            # noqa: E402
import model_v4 as M          # noqa: E402

OPENSCAD = os.environ.get("OPENSCAD", "/opt/homebrew/bin/openscad")
OUT_STL, OUT_PNG, OUT_SCAD = (os.path.join(HERE, d) for d in ("stl", "png", "scad"))
for d in (OUT_STL, OUT_PNG, OUT_SCAD):
    os.makedirs(d, exist_ok=True)

P = M.P
MET = json.load(open(os.path.join(MODEL_DIR, "metrics.json")))
T0 = time.time()
G = M.build_geo(P)                           # solved design (~10 s): pad tables, plate profile, seat stiffness
KEYS, LAY = G["keys"], G["lay"]
GN = M.G                                     # N per g
BED = (256.0, 256.0, 256.0)                  # P2S build volume
RHO = M.RHO_PETG


def r_(v, n=2):
    """round half away from zero at n decimals (one rule for every number this script prints)."""
    if v is None:
        return None
    q = 10.0 ** n
    return math.copysign(math.floor(abs(v) * q + 0.5) / q, v)


def f_(v, n=2):
    return ("%." + str(n) + "f") % r_(v, n)


# ============================================================================ OpenSCAD helpers
HDR = "$fn = 64;\n"


def pts_(pts):
    return "[" + ",".join("[%.4f,%.4f]" % (float(a), float(b)) for a, b in pts) + "]"


def ext(pts, z0, z1):
    """2-D polygon (print X, Y) extruded over print z0..z1."""
    return "translate([0,0,%.4f]) linear_extrude(height=%.4f) polygon(%s);\n" % (z0, z1 - z0, pts_(pts))


def box(x0, x1, y0, y1, z0, z1):
    return "translate([%.4f,%.4f,%.4f]) cube([%.4f,%.4f,%.4f]);\n" % (x0, y0, z0, x1 - x0, y1 - y0, z1 - z0)


def cyl(x, y, z0, z1, d, fn=64):
    return "translate([%.4f,%.4f,%.4f]) cylinder(h=%.4f, d=%.4f, $fn=%d);\n" % (x, y, z0, z1 - z0, d, fn)


def teardrop2d(d, point_deg=90.0):
    """2-D teardrop whose point is toward point_deg (2-D angle): a horizontal hole prints without support when the point
    is toward the build direction."""
    r = d / 2
    return "union(){circle(d=%.4f, $fn=48); rotate(%.3f) square([%.4f,%.4f]);}\n" % (d, point_deg - 45.0, r, r)


def text_(s, x, y, ztop, size=3.0, depth=0.6, halign="center", rot=0.0):
    """engraved label on a face at print height ztop (read from +z)."""
    return ("translate([%.4f,%.4f,%.4f]) rotate([0,0,%.2f]) linear_extrude(height=%.4f) "
            "text(\"%s\", size=%.3f, font=\"Liberation Sans:style=Bold\", halign=\"%s\", valign=\"center\");\n"
            % (x, y, ztop - depth, rot, depth + 0.2, s, size, halign))


def diff(a, *b):
    return "difference(){\n" + a + "".join(b) + "}\n"


def uni(*a):
    return "union(){\n" + "".join(a) + "}\n"


def arc_pts(c, r, a0, a1, n=48):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def annulus_sector(c, r0, r1, a0, a1, n=96):
    return arc_pts(c, r1, a0, a1, n) + arc_pts(c, r0, a1, a0, n)


def rotp(p, a, c=(0.0, 0.0)):
    ca, sa = math.cos(a), math.sin(a)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + ca * x - sa * y, c[1] + sa * x + ca * y)


def hull2d(pts):
    """convex hull (monotone chain) of 2-D points."""
    P_ = sorted(set((round(a, 6), round(b, 6)) for a, b in pts))
    if len(P_) < 3:
        return P_
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p_ in P_:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p_) <= 0:
            lo.pop()
        lo.append(p_)
    for p_ in reversed(P_):
        while len(up) >= 2 and cr(up[-2], up[-1], p_) <= 0:
            up.pop()
        up.append(p_)
    return lo[:-1] + up[:-1]


def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def poly_centroid(pts):
    A = poly_area(pts)
    cx = cy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        c = x0 * y1 - x1 * y0
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    return A, (cx / (6 * A), cy / (6 * A))


def poly_I(pts, c):
    """polar second moment (per unit thickness) of a simple polygon about point c (mm^4)."""
    Ix = Iy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i][0] - c[0], pts[i][1] - c[1]
        x1, y1 = pts[(i + 1) % len(pts)][0] - c[0], pts[(i + 1) % len(pts)][1] - c[1]
        cr = x0 * y1 - x1 * y0
        Ix += (y0 * y0 + y0 * y1 + y1 * y1) * cr
        Iy += (x0 * x0 + x0 * x1 + x1 * x1) * cr
    return abs(Ix + Iy) / 12.0


PARTS = []       # every printed part (dict)
TESTS = {}       # test number -> dict (method, pass, outcomes ...)


def part(pid, name_ko, test, scad, print_ko, key_dims, purpose_ko, qty=1, settings=None, extra=None):
    d = dict(id=pid, name_ko=name_ko, test=test, scad=scad, print_ko=print_ko, key_dims=key_dims, purpose_ko=purpose_ko,
             qty=qty, settings=settings or "PETG, 0.2 층, 벽 3, 윗/아랫면 5층, 채움 40 % 자이로이드, 서포트 없음")
    d.update(extra or {})
    PARTS.append(d)
    return d


SOLID = "PETG, 0.2 층, 벽 4, 채움 100 % (질량·관성을 모델과 맞춤), 서포트 없음"
LIKE_FRAME = "PETG, 생산 프레임과 같은 슬라이서 설정 (층·벽·채움 그대로), 서포트 없음"
LIKE_KEY = "PETG, 생산 건반과 같은 슬라이서 설정 (윗면을 베드에, 층 0.2), 서포트 없음"


# ============================================================================ C01 pad rebound pendulum (test 1)
def c01():
    """Real lever geometry (steel 9x19x40 at the model position on a D4 rod) swung by gravity into the pad on a rigid
    seat.  The rig is the machine's (y, z) plane rotated so that at the first-contact angle b0 the arm's centre of
    mass hangs straight down: the contact happens at the bottom of the swing, e = sqrt(rebound energy / drop energy)."""
    L = P["L"]
    pt = G["pad_w"]                                            # white pad table: face, first contact b0, e calibration
    b0 = pt.b0
    # --- test arm (lever frame at b = 0, machine y z): steel pocket, 2 mm frame, open top over the pad zone, web, hub
    s0, s1 = P["y_steel_front"], P["y_steel_rear"]
    zs, zt = P["z_sb"], P["z_st"]
    fw = 2.0
    top_open = (s0 + 3.0, 187.0)                               # the model's exposed steel top starts 3 mm behind the front
    frame = [(s0 - fw, zs - fw), (s1 + fw, zs - fw), (s1 + fw, zt + fw), (top_open[1], zt + fw), (top_open[1], zt),
             (top_open[0], zt), (top_open[0], zt + fw), (s0 - fw, zt + fw)]
    pocket = [(s0 - 0.05, zs - 0.05), (s1 + 0.05, zs - 0.05), (s1 + 0.05, zt + 0.05), (s0 - 0.05, zt + 0.05)]
    hub_R, bore = 5.5, 3.9
    web = [(s1 + fw - 0.5, L[1] - 4.0), (L[0], L[1] - 4.0), (L[0], L[1] + 4.0), (s1 + fw - 0.5, L[1] + 4.0)]
    thick = P["steel_w"]                                       # arm 9.0 thick = the steel width (steel faces flush)
    # mass properties without the pointer (solid PETG, frame minus pocket), then point the pointer away from the CG
    A_fr, c_fr = poly_centroid(frame)
    A_pk, c_pk = poly_centroid(pocket)
    A_web, c_web = poly_centroid(web)
    hub = [(L[0] + hub_R * math.cos(2 * math.pi * i / 64), L[1] + hub_R * math.sin(2 * math.pi * i / 64)) for i in range(64)]
    A_hub, c_hub = poly_centroid(hub)
    m_st = P["steel_w"] * P["steel_h"] * P["steel_len"] * M.RHO_ST
    c_st = ((s0 + s1) / 2, (zs + zt) / 2)
    comps = [(A_fr * thick * RHO, c_fr, poly_I(frame, L) * thick * RHO),
             (-A_pk * thick * RHO, c_pk, -poly_I(pocket, L) * thick * RHO),
             (A_web * thick * RHO * 0.8, c_web, poly_I(web, L) * thick * RHO * 0.8),    # web overlaps hub/frame ~20 %
             (A_hub * thick * RHO, c_hub, poly_I(hub, L) * thick * RHO),
             (m_st, c_st, m_st * ((P["steel_len"] ** 2 + P["steel_h"] ** 2) / 12 + (c_st[0] - L[0]) ** 2 + (c_st[1] - L[1]) ** 2))]
    m0 = sum(c[0] for c in comps)
    cg0 = (sum(c[0] * c[1][0] for c in comps) / m0, sum(c[0] * c[1][1] for c in comps) / m0)
    dirp = (L[0] - cg0[0], L[1] - cg0[1])
    nn = math.hypot(*dirp)
    dirp = (dirp[0] / nn, dirp[1] / nn)
    ptr_r0, ptr_r1, ptr_w = 6.2, 28.0, 1.6        # short pointer: its sweep stays inside the pad block (r >= ~31)
    nrm = (-dirp[1], dirp[0])
    pointer = [(L[0] + dirp[0] * r + nrm[0] * s * ptr_w / 2, L[1] + dirp[1] * r + nrm[1] * s * ptr_w / 2)
               for r, s in ((ptr_r0, -1), (ptr_r1, -1), (ptr_r1, 1), (ptr_r0, 1))]
    A_pt, c_pt = poly_centroid(pointer)
    comps.append((A_pt * thick * RHO, c_pt, poly_I(pointer, L) * thick * RHO))
    m = sum(c[0] for c in comps)
    cg = (sum(c[0] * c[1][0] for c in comps) / m, sum(c[0] * c[1][1] for c in comps) / m)
    I = sum(c[2] for c in comps)
    rcg = math.hypot(cg[0] - L[0], cg[1] - L[1])
    # machine lever (for comparison / the model's calibration speed)
    lev = G["Aw"].lev
    IL, mL, cgL = G["Aw"].IL, lev.m, lev.com
    jj = G["Aw"].j(G["Aw"].a_dip - 1e-4)[0]
    w0 = jj * P["v_play"] / (G["Aw"].K[0] - G["Aw"].front[0])       # rad/ms, PadTable.calibrate
    # --- rig transform: machine world -> rig (u, v), rod axis at the origin; arm CG straight down at b0
    cgw = M.rot(cg, L, -b0)
    psi = -math.pi / 2 - math.atan2(cgw[1] - L[1], cgw[0] - L[0])

    def to_rig(p):
        return rotp((p[0] - L[0], p[1] - L[1]), psi)

    def arm_rig(poly, theta):
        """arm polygon (lever frame) at rig angle theta from contact (theta > 0 = away from the pad = CCW)."""
        return [rotp(to_rig(M.rot(p, L, -b0)), theta) for p in poly]
    # pad face, pad (7 thick), pad plate (4 thick) and the seat block, in rig coordinates
    n_r = rotp(pt.n, psi)
    t_r = rotp(pt.t, psi)
    ref = to_rig(pt.ref)
    u0, u1 = pt.u0, pt.u1                                    # pad extent along the face (from pad_y)
    uc = 0.5 * (u0 + u1)
    fc = (ref[0] + uc * t_r[0], ref[1] + uc * t_r[1])        # pad face centre
    hpad = P["pad_h"]
    tpl = 4.0
    L_plate = 20.0
    lip_w = 3.0
    back = hpad + tpl
    Q = lambda s, k: (fc[0] + s * t_r[0] + k * n_r[0], fc[1] + s * t_r[1] + k * n_r[1])
    pad_poly = [Q(-6.0, 0.0), Q(6.0, 0.0), Q(6.0, hpad), Q(-6.0, hpad)]
    plate_poly = [Q(-L_plate / 2, hpad), Q(L_plate / 2, hpad), Q(L_plate / 2, back), Q(-L_plate / 2, back)]
    blk_face = [Q(-L_plate / 2 - lip_w, hpad + 0.5), Q(L_plate / 2 + lip_w, hpad + 0.5), Q(L_plate / 2 + lip_w, back + 16.0),
                Q(-L_plate / 2 - lip_w, back + 16.0)]
    H_ax = 70.0                                              # rod axis above the foot top
    foot_v = -H_ax
    # block: hull of the face block and a patch on the foot below it
    fx = [p[0] for p in blk_face]
    foot_patch = [(min(fx) - 4, foot_v), (min(fx) + 10, foot_v), (min(fx) + 10, foot_v + 4), (min(fx) - 4, foot_v + 4)]
    channel = [Q(-L_plate / 2 - 0.15, hpad - 0.2), Q(L_plate / 2 + 0.15, hpad - 0.2), Q(L_plate / 2 + 0.15, back + 0.02),
               Q(-L_plate / 2 - 0.15, back + 0.02)]
    # --- clearance sweep of the arm against the block (+ pad plate + pad) over the free-swing and release range
    arm_polys = [frame, web, pointer]
    arm_convex = frame + web
    blocks = [blk_face]

    blk_hull = hull2d(blk_face + foot_patch)

    def min_clear(theta, with_pad):
        obs = [blk_hull] + ([plate_poly, pad_poly] if with_pad else [])
        return min(M.poly_dist(arm_rig(pp, theta), o) for pp in (frame, web, hub, pointer) for o in obs)
    # angle where the steel top (with the pad removed) would reach the pad plate channel region
    th_free = []
    for th in np.arange(0.0, -30.01, -0.5):
        th_free.append((float(th), min_clear(math.radians(th), False)))
    th_lim = min([th for th, d in th_free if d > 1.0])        # most negative angle that keeps >= 1.0 mm
    rel_clear = min(min_clear(math.radians(th), True) for th in np.arange(5.0, 160.01, 2.5))
    r_blk_min = min(math.hypot(*q) for q in blk_hull)
    # the steel top touches the pad face at theta = 0 by construction: check the face gap along n at contact
    # (penetration 0 at the first-contact angle b0)
    # --- energy / speed tables
    mgr = m * GN * rcg                                      # N mm
    om = lambda th0: math.sqrt(2 * mgr * (1 - math.cos(math.radians(th0))) / I)   # rad/ms
    v_c = lambda th0: om(th0) * math.hypot(*to_rig((pt.ref[0], pt.ref[1])))       # contact point speed m/s
    rel_rows = []
    for th0 in (60, 90, 120, 150):
        row = dict(theta0=th0, omega=r_(om(th0) * 1000, 1), omega_ratio_play=r_(om(th0) / w0, 2))
        for e in (0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30):
            c = 1 - e * e * (1 - math.cos(math.radians(th0)))
            row["e%.2f" % e] = r_(math.degrees(math.acos(c)), 1)
        rel_rows.append(row)
    # friction: coulomb decrement per half swing (small angle) for a friction torque Tf
    dtheta_per_Tf = 2.0 / mgr                               # rad per (N mm)
    # --- scale ring (pointer angle = 90 deg + theta in rig coordinates)
    th_rng = (-20.0, 160.0)
    ring = (19.0, min(30.0, r_blk_min - 1.5))              # scale ring behind the arm, inside the pad block radius
    geo = dict(psi_deg=math.degrees(psi), b0_deg=math.degrees(b0), fc=fc, n=n_r, t=t_r, H_ax=H_ax,
               arm=dict(frame=frame, pocket=pocket, web=web, hub_R=hub_R, bore=bore, pointer=pointer, thick=thick))
    # ------------------------------------------------------------------ SCAD: C01a stand (print: bracket back on the bed)
    xb0, xb1 = -4.0, 0.0                                     # bracket plate (rig x)
    x_arm0 = 6.5
    x_arm1 = x_arm0 + thick
    x_c = 0.5 * (x_arm0 + x_arm1)
    pl_w = 11.0                                              # pad plate width (x); pad 6 wide centred
    x_ledge = x_c - pl_w / 2
    x_blk1 = x_arm1 + 5.5
    zp = lambda x: x - xb0                                   # rig x -> print z
    br_outline = [(-60.0, foot_v - 5.0), (60.0, foot_v - 5.0), (60.0, 0.0)] + arc_pts((0, 0), 38.0, 0.0, 180.0, 60) + [(-60.0, 0.0)]
    s = HDR
    body = ext(br_outline, zp(xb0), zp(xb1))
    body += ext([(-78.0, foot_v - 5.0), (78.0, foot_v - 5.0), (78.0, foot_v), (-78.0, foot_v)], zp(xb0), zp(60.0))
    for ug in (-56.0, 20.0, 52.0):
        body += ("hull(){" + box(ug - 2, ug + 2, foot_v, foot_v + 0.01, zp(xb1) - 0.01, zp(45.0)).strip()
                 + box(ug - 2, ug + 2, foot_v, foot_v + 40.0, zp(xb1) - 0.01, zp(xb1)).strip() + "}\n")
    body += cyl(0, 0, zp(xb1) - 0.01, zp(x_arm0 - 0.5), 12.0)
    ring_pts = annulus_sector((0, 0), ring[0], ring[1], 90 + th_rng[0] - 3, 90 + th_rng[1] + 3, 120)
    body += ext(ring_pts, zp(xb1) - 0.01, zp(6.0))
    body += "hull(){\n" + ext(blk_face, zp(xb0), zp(x_blk1)) + ext(foot_patch, zp(xb0), zp(x_blk1)) + "}\n"
    cuts = cyl(0, 0, -1, zp(x_arm0) + 1, bore)
    cuts += ext(channel, zp(x_ledge), zp(x_blk1) + 1)
    for th in range(int(th_rng[0]), int(th_rng[1]) + 1, 2):
        a = math.radians(90 + th)
        rl = ring[0] + (5.5 if th % 10 == 0 else 3.5)
        w = 0.4
        pa = [(ring[0] - 0.5) * math.cos(a), (ring[0] - 0.5) * math.sin(a)]
        pb = [rl * math.cos(a), rl * math.sin(a)]
        nx, ny = -math.sin(a) * w / 2, math.cos(a) * w / 2
        cuts += ext([(pa[0] + nx, pa[1] + ny), (pb[0] + nx, pb[1] + ny), (pb[0] - nx, pb[1] - ny), (pa[0] - nx, pa[1] - ny)], zp(6.0) - 0.6, zp(6.0) + 0.2)
        if th % 20 == 0:
            rt = ring[1] - 2.2
            cuts += text_(str(th), rt * math.cos(a), rt * math.sin(a), zp(6.0), size=2.2, depth=0.4, rot=th)
    cuts += text_("C01a", 40.0, foot_v + 12.0, zp(xb1), size=6.0)
    s += diff(uni(body), cuts)
    part("C01a", "패드 반발 진자대 (받침·눈금판·패드 자리)", 1, s,
         "브래킷 뒷면을 베드에 (눈금판·보스·패드 블록·발이 위로 솟음). 서포트 없음",
         "브래킷 120×113×4 + 발 156×64, 봉 축 높이 %.1f (발 윗면에서), 봉 구멍 Ø%.1f (출력 → Ø4.0 드릴, 봉 압입), 눈금 반지름 %.0f~%.0f, 2° 눈금 θ %d~%d°"
         % (H_ax, bore, ring[0], ring[1], th_rng[0], th_rng[1]),
         "레버(강철)를 중력으로 휘둘러 단단한 자리 위 패드에 치게 하고, 되튄 높이(각)로 실효 e를 잰다",
         settings="PETG, 0.2 층, 벽 4, 채움 40 % (패드 블록은 채움 100 % 권장: 슬라이서 수정자), 서포트 없음")
    # ------------------------------------------------------------------ C01b test arm (print: back face on the bed)
    s = HDR
    arm = uni(ext(frame, 0, thick), ext(web, 0, thick), ext(hub, 0, thick), ext(pointer, 0, thick))
    s += diff(arm, ext(pocket, -1, thick + 1), cyl(L[0], L[1], -1, thick + 1, bore),
              "")
    part("C01b", "시험 레버 (강철 9×19×40 자리, 허브 Ø3.9, 지침)", 1, s,
         "옆면(두께 9 방향)을 베드에. 강철 칸은 관통, 윗면이 패드 구간 y%.0f~%.0f에서 열림" % top_open,
         "두께 %.1f, 강철 칸 %.1f×%.1f (강철 40×19 + 0.1), 허브 Ø%.1f 구멍 Ø%.1f, 지침 끝 반지름 %.0f; 질량 %s g(강철 포함), 무게중심 반지름 %s, 관성 %s g·mm²"
         % (thick, P["steel_len"] + 0.1, P["steel_h"] + 0.1, 2 * hub_R, bore, ptr_r1, f_(m, 1), f_(rcg, 2), f_(I, 0)),
         "모델 레버와 같은 자리(봉 L 기준)에 강철을 잡는 시험 레버. 강철은 옆에서 밀어 넣고 순간접착제 한 방울",
         settings=SOLID)
    # ------------------------------------------------------------------ C01c pad plate (x2), C01d rod collar (x2)
    s = HDR
    for k in range(2):
        s += box(k * 26.0, k * 26.0 + L_plate, 0, pl_w, 0, tpl)
    s = HDR + diff(uni(s[len(HDR):]), "".join(box(k * 26.0 + L_plate / 2 - 6.0, k * 26.0 + L_plate / 2 + 6.0, pl_w / 2 - 3.0, pl_w / 2 + 3.0,
                                                 tpl - 0.3, tpl + 1) for k in range(2)))
    part("C01c", "패드 받침판 (2개: 후보 재료마다 1개)", 1, s, "넓은 면을 베드에",
         "%.0f×%.0f×%.0f, 윗면에 패드 자리 표시 6×12 (0.3 깊이)" % (L_plate, pl_w, tpl),
         "패드(폼 6T + 펠트 1T, 6×12)를 붙여 C01a 홈에 위에서 밀어 넣는다(단단한 자리). 마찰 시험 때 빼낸다", qty=1, settings=SOLID)
    s = HDR
    for k in range(2):
        s += diff(cyl(k * 12.0, 0, 0, 3.0, 9.0), cyl(k * 12.0, 0, -1, 4, bore))
    part("C01d", "봉 끝 칼라 (2개)", 1, s, "눕혀서", "Ø9×3, 구멍 Ø%.1f (Ø4 봉에 끼움)" % bore, "시험 레버가 봉에서 빠지지 않게", settings=SOLID)
    res = dict(arm_mass=m, arm_cg=cg, arm_rcg=rcg, arm_I=I, lever_model=dict(m=mL, cg=cgL, IL=IL), w0=w0, psi=psi, b0=b0,
               th_free_lim=th_lim, rel_clear=rel_clear, table=rel_rows, dtheta_per_Tf=dtheta_per_Tf, mgr=mgr,
               omega=dict((str(t), om(t)) for t in (60, 90, 120, 150)), v_contact=dict((str(t), v_c(t)) for t in (60, 90, 120, 150)),
               x=dict(bracket=(xb0, xb1), arm=(x_arm0, x_arm1), ledge=x_ledge, block_top=x_blk1), rod_len=24.0,
               pad_face_centre=fc, pad_normal=n_r, ring=ring, th_rng=th_rng, e_check=pt.e_check, pad_c=pt.c)
    return res


# ============================================================================ C02 pad compression jig (test 2)
def c02():
    A = P["pad_w"] * (P["pad_y"][1] - P["pad_y"][0])
    h = P["pad_h"]
    E, eD = P["pad_E"], P["pad_epsD"]
    F_of = lambda d, E_: A * M.foam_sigma(np.array([d / h]), E_, eD)[0]
    rows = []
    for d in (0.35, 0.7, 1.05, 1.4, 1.75, 2.1):
        rows.append(dict(d=d, eps=r_(d / h, 3), F07=r_(F_of(d, 0.7), 1), F10=r_(F_of(d, 1.0), 1), F14=r_(F_of(d, 1.4), 1)))
    sig25 = M.foam_sigma(np.array([0.25]), E, eD)[0]
    # jig
    bx, by = 60.0, 60.0
    ti, tj = 14.0 + 0.4, 22.0 + 0.4      # tube bore for the 14 x 22 plunger
    wall = 2.4
    ped = (12.0, 20.0, 2.0)
    s = HDR
    body = box(0, bx, 0, by, 0, 4.0)
    cx, cy = bx / 2, by / 2
    body += box(cx - ti / 2 - wall, cx + ti / 2 + wall, cy - tj / 2 - wall, cy + tj / 2 + wall, 4.0 - 0.01, 4.0 + 22.0)
    cut = box(cx - ti / 2, cx + ti / 2, cy - tj / 2, cy + tj / 2, 4.0, 40.0)
    ped_b = box(cx - ped[0] / 2, cx + ped[0] / 2, cy - ped[1] / 2, cy + ped[1] / 2, 4.0 - 0.01, 4.0 + ped[2])
    rec = box(cx - 3.2, cx + 3.2, cy - 6.2, cy + 6.2, 4.0 + ped[2] - 1.0, 10)
    s += diff(uni(diff(uni(body), cut), ped_b), rec, text_("C02 pad", cx, 7.0, 4.0, size=4))
    # reference pad for the caliper depth rod at the corner (8, 8) = base top z4
    part("C02a", "패드 압축 지그 (바탕·안내 통)", 2, s, "바닥을 베드에",
         "바탕 %.0f×%.0f×4, 안내 통 안치수 %.1f×%.1f 높이 22, 패드 자리 6.4×12.4×1 (받침 %.0f×%.0f×%.0f 위)" % (bx, by, ti, tj, *ped),
         "패드 한 장(6×12×7)을 누름 막대로 눌러 힘-눌림 곡선을 잰다")
    s = HDR
    body = box(0, 80, 0, 80, 0, 3.0) + box(40 - 7.0, 40 + 7.0, 40 - 11.0, 40 + 11.0, 2.99, 3.0 + 24.0)
    s += diff(uni(body), cyl(8.0, 8.0, -1, 5, 4.2), text_("C02b", 60, 12, 3.0, size=4))
    part("C02b", "패드 압축 누름 막대 (추 받침판 80×80)", 2, s, "받침판을 베드에 (막대가 위로)",
         "막대 14×22×24 (바닥 면이 패드를 누름), 받침판 80×80×3, 모서리 Ø4.2 구멍 = 버니어 깊이 막대 구멍 (C02a 바탕 윗면까지 잼)",
         "받침판 위에 물병·쌀 봉지(무게를 저울로 잼)를 올려 누른다", settings=SOLID)
    return dict(area=A, h=h, E=E, epsD=eD, sig25=sig25, F25=A * sig25, rows=rows,
                F25_band=(F_of(0.25 * h, 0.7), F_of(0.25 * h, 1.4)), ped_h=ped[2], plunger=(14.0, 22.0, 24.0))


# ============================================================================ C03 plate stiffness (test 3)
def c03():
    fins = LAY["fins"]
    lev = LAY["levers"]
    prof = G["plate_under"]
    yy = [p[0] for p in prof]
    zz = [p[1] for p in prof]
    zu = lambda y: float(np.interp(y, yy, zz))
    tof = lambda y: G["z_top"] - zu(y)
    yl = G["y_load_b"]
    xs_c = lev["C#"]
    fw, fy = 9.0, 19.0                         # steel block standing on its 9 x 19 end = the load foot
    x_dial = xs_c + fw / 2 + 2.5
    out = {}
    for lab, xr, fl in (("module", (0.2, 164.3), fins), ("S1 (x0.2~84.3, C~F)", (0.2, 84.3), fins[:3])):
        xs, ys, res = M.plate_fe(P, list(fl), [[(xs_c, yl, 100.0, fy, fw)], [(xs_c, yl, 100.0, P["pad_y"][1] - P["pad_y"][0], P["pad_w"])]],
                                 tof, zu, x0=xr[0], x1=xr[1])
        W = res[0]["w"]
        i = int(np.argmin(abs(xs - x_dial)))
        j = int(np.argmin(abs(ys - yl)))
        seat = M.seat_at(xs, ys, W, xs_c, yl, fw, fy)
        seat_pad = M.seat_at(xs, ys, res[1]["w"], xs_c, yl, P["pad_w"], P["pad_y"][1] - P["pad_y"][0])
        out[lab] = dict(w_dial_100N=float(W[i, j]), k_dial=100.0 / float(W[i, j]), w_seat_100N=seat, k_seat_block=100.0 / seat,
                        k_seat_pad=100.0 / seat_pad)
    # chord seat vs plate thickness (plate FE, PLAY pad forces) - sensitivity for the 'fail' branch
    Fw, Fb = MET["upstop_peaks"]["play"]
    chord = {}
    for dz in (0.0, 0.6, 1.2):
        g2 = dict(G)
        g2["z_top"] = G["z_top"] + dz
        pl = M.plate_loads(P, g2, Fw, Fb, fins, lev, KEYS)
        chord[dz] = dict(k_chord=pl["chord"]["k_eq"], k_single=pl["single"]["k_eq"])
    # 3-point bend strip (E_eff of the printed top plate)
    t = P["plate_t"]
    # r4.4 fix 2 (verifier printables major): 120 x 12 x 5.5 on a 100 span (L/t 18): the 2 -> 20 N signal is ~1.2 mm, so the
    # line contacts on the layer ridges stay < 1 % of it; the dial reads the strip itself through a hole in the nose
    b, Ls = 12.0, 100.0
    Ib = b * t ** 3 / 12
    Gm = M.E_PETG / (2 * (1 + 0.38))
    k_beam = 1.0 / (Ls ** 3 / (48 * M.E_PETG * Ib) + Ls / (4 * (5.0 / 6.0) * Gm * b * t))      # bending + shear
    ratio_single = P["seat_k_req"] / MET["seat"]["k_min"]
    ratio_chord = P["seat_k_chord_req"] / MET["seat"]["k_chord"]
    # --- strips (x3)
    s = HDR
    for k in range(3):
        y0 = k * 16.0
        s += diff(box(0, Ls + 20.0, y0, y0 + b, 0, t), text_("C03a-%d t%s" % (k + 1, f_(t, 1)), 8.0, y0 + b / 2, t, size=3.0, halign="left"))
    part("C03a", "윗판 굽힘 띠 (3개)", 3, s, "넓은 면을 베드에 (윗판처럼 층이 수평)",
         "%.0f×%.0f×%s (윗판 패드 구간 두께 plate_t), 받침 간격 %.0f" % (Ls + 20.0, b, f_(t, 1), Ls),
         "윗판을 출력하는 설정 그대로 뽑아 3점 굽힘으로 실효 굽힘 탄성률 E를 잰다 (모델 E %.0f MPa)" % M.E_PETG, settings=LIKE_FRAME)
    # --- 3-point bend base + load nose
    s = HDR
    prof2 = lambda cy: "hull(){translate([0,%.3f,12]) rotate([0,90,0]) cylinder(h=30, r=2.0, $fn=48); translate([0,%.3f,0]) cube([30,10,1]);}\n" % (cy, cy - 5.0)
    Lb = Ls + 20.0
    body = box(0, 30, 0, Lb, 0, 4.0) + prof2(Lb / 2 - Ls / 2) + prof2(Lb / 2 + Ls / 2)
    s += diff(uni(body), text_("C03b span %.0f" % Ls, 15, Lb / 2, 4.0, size=3.5, rot=90))
    part("C03b", "3점 굽힘 받침 (R2 두 날, 간격 %.0f)" % Ls, 3, s, "바닥을 베드에 (날은 x 방향 프리즘)",
         "바탕 30×%.0f×4, R2 날 높이 12 (바탕 윗면에서), 날 간격 %.0f" % (Lb, Ls), "굽힘 띠를 올려 가운데를 누름")
    s = HDR
    s += diff(uni(box(0, 24, 0, 24, 0, 3.0), "hull(){translate([0,12,11]) rotate([0,90,0]) cylinder(h=24, r=2.0, $fn=48); translate([0,7,2.99]) cube([24,10,1]);}\n"),
              cyl(12.0, 12.0, -1.0, 20.0, 4.0))
    part("C03c", "누름 코 (R2 날 + 손가락 받침 24×24, 가운데 Ø4 다이얼 구멍)", 3, s, "평평한 윗판을 베드에 (날이 위)",
         "24×24×3 판 + R2 날(가운데 Ø4 구멍으로 둘로 나뉨), 전체 높이 13", "띠 가운데를 손가락으로 누름. 다이얼 게이지 끝은 가운데 Ø4 구멍으로 띠 윗면에 직접 댐 (r4.4 고침 2)")
    # --- dial gauge stands (low: coupon, high: frame section)
    for pid, hz, lab in (("C03d", 45.0, "낮은 (굽힘 띠용)"), ("C03e", 105.0, "높은 (프레임 조각 윗판용)")):
        # print frame: X along the arm, Y = use height, Z = use sideways (16 thick); stem hole along Y (use vertical)
        th_ = 16.0
        prof = [(0, 0), (60, 0), (60, 6), (14, 6), (14, hz), (58, hz), (58, hz + 12), (2, hz + 12), (2, 6), (0, 6)]
        s = HDR
        body = ext(prof, 0, th_)
        # rotate([-90,0,0]) maps 2-D +y to print -Z: point the teardrop to 2-D 270 deg = print +Z (build direction)
        cuts = "translate([46,%.3f,6]) rotate([-90,0,0]) linear_extrude(height=14) %s" % (hz - 1.0, teardrop2d(8.15, 270.0))
        cuts += box(45.5, 46.5, hz - 1, hz + 13, 6.0, th_ + 1)                 # split: stem hole -> top face (vertical slot)
        cuts += "translate([46.6,%.3f,12.6]) rotate([0,90,0]) cylinder(h=12, d=3.3, $fn=32);\n" % (hz + 6.0)   # M3 clearance
        cuts += "translate([36,%.3f,12.6]) rotate([0,90,0]) cylinder(h=10, d=2.7, $fn=32);\n" % (hz + 6.0)    # M3 self-tapping
        cuts += text_(pid, 8.0, 3.0, th_, size=3.2)
        s += diff(body, cuts)
        part(pid, "다이얼 게이지 스탠드, " + lab, 3, s,
             "옆면(두께 16)을 베드에. Ø8 줄기 구멍은 눈물방울(위 뾰족), 구멍에서 윗면까지 1.0 틈 + M3 나사(가로, Ø2.7에 자가 탭)",
             "바닥 60×16 (저울판 위), 기둥 높이 %.0f, 팔 끝 Ø8.15 줄기 조임 (M3×12 한 개)" % hz,
             "다이얼 게이지(0.01 mm, 줄기 Ø8)를 저울판에 세워 처짐을 잰다")
    return dict(fe=out, x_dial=x_dial, x_seat=xs_c, y_load=yl, foot=(fw, fy), chord_vs_dz=chord, t=t, b=b, span=Ls,
                k_beam=k_beam, ratio_single=ratio_single, ratio_chord=ratio_chord, E=M.E_PETG)


# ============================================================================ C16 carrier + steel retention (test 20, r4.4 fix 2)
def c16():
    """production lever carrier (position C) straight from model_v4.lever_prisms, printed like production (side wall on the
    bed), and a slotted base that carries the carrier by its side walls while the steel is pressed down through the slot."""
    col = tuple(G["collars"]["C"])
    prs = [q for q in M.lever_prisms(P, 0.0, col) if q[0] != "felt strip"]
    xmin = min(q[1] for q in prs)
    xmax = max(q[2] for q in prs)
    y_off, z_off = P["y_lever_front"] - P["nail_tab"][0] - 2.0, P["z_sb"] - P["lip"] - 2.0
    Y_ = lambda y: y - y_off
    Z_ = lambda z: z - z_off
    hw = P["steel_w"] / 2
    # 2-D cuts before the extrusion (robust): the lever-rod bore D3.9 in every prism, the steel cavity in the core
    bore2 = "translate([%.4f,%.4f]) circle(d=3.9, $fn=48);" % (Y_(P["L"][0]), Z_(P["L"][1]))
    cav2 = "translate([%.4f,%.4f]) square([%.4f,%.4f]);" % (Y_(P["y_steel_front"]), Z_(P["z_sb"]), P["steel_len"], P["steel_h"])
    body = ""
    for tag, x0, x1, poly in prs:
        # 0.02 x-overlap: neighbouring prisms that only touch on a face fuse into one manifold solid
        z0_, z1_ = max(0.0, x0 - xmin - 0.02), min(x1 - xmin + 0.02, xmax - xmin)
        cut_ = bore2 + (cav2 if tag.startswith("carrier core") else "")
        if tag.startswith("carrier top snap lip") and max(y for y, z in poly) >= P["y_steel_rear"] - 1e-9:
            # the rear lip's rear-bottom edge only touches the rear wall's top corner (y190, z52): run it 0.05 into the wall
            poly = [(y + 0.05, z - (0.2 if z <= P["z_st"] + 1e-9 else 0.0)) if y >= P["y_steel_rear"] - 1e-9 else (y, z) for y, z in poly]
        body += "translate([0,0,%.4f]) linear_extrude(height=%.4f) difference(){polygon(%s); %s}\n" % (z0_, z1_ - z0_, pts_([(Y_(y), Z_(z)) for y, z in poly]), cut_)
    s = HDR + uni(body)
    ZS_ = MET["steel_retention"]
    WP_ = ZS_.get("wall_plate", {})
    part("C16a", "레버 캐리어 (C 자리, 생산 부품 그대로, 3개)", 20, s,
         "생산처럼 옆벽을 베드에 (허브 구멍이 세로), 강철 칸 안 지지대 1개(z 틈 0.2) — 생산 캐리어와 같은 설정",
         "폭 %.1f, 강철 칸 %.0f×%.0f×%.0f, 아래 립 1.0×1.0 y%.0f~%.1f, 윗 립 %.1f×%.1f, 허브 Ø3.9 (Ø4.0 드릴)" % (P["lever_w"], P["steel_len"], P["steel_w"], P["steel_h"], P["lip_front_y"], P["felt_c_y"][0], P["lip_over"], P["lip"]),
         "강철이 스냅만으로 버티는지(모델: 버티지 못함) / 접착하면 버티는지", qty=3, settings="PETG, 생산 캐리어와 같은 슬라이서 설정")
    # slotted base: the walls stand on it beside a slot the steel can drop through; top = the walls' bottom z
    zb_ = P["z_sb"] - P["lip"]
    y0b, y1b = P["y_steel_front"] - 4.0, P["y_steel_rear"] + 2.0          # ends before the hub (it hangs below the walls)
    sb = HDR + diff(box(-20.0, 20.0, y0b, y1b, 0.0, 8.0), box(-(hw + 0.3), hw + 0.3, y0b - 1, y1b + 1, -1.0, 9.0),
                    text_("C16b", -12.0, (y0b + y1b) / 2, 8.0, size=3.5, rot=90))
    part("C16b", "강철 누름 받침 (옆벽을 받치고 가운데 %.1f 홈으로 강철이 내려감)" % (2 * hw + 0.6), 20, sb, "바닥을 베드에",
         "40×%.0f×8, 가운데 홈 폭 %.1f (강철 9.0 + 0.3씩); 캐리어 옆벽 밑면(z%.0f)이 윗면에 얹힘, 허브는 받침 뒤로 나감" % (y1b - y0b, 2 * hw + 0.6, zb_),
         "강철 윗면(패드 자리 y%.0f~%.0f)을 눌러 강철 ↔ 캐리어 힘을 아래 립(또는 접착)으로 보냄" % tuple(P["pad_y"]))
    return dict(collars=col, B_play=ZS_["peaks"]["play"]["B"], B_abuse=ZS_["peaks"]["abuse"]["B"],
                spread_play=[WP_.get("play_a0.50_clamped", {}).get("spread_max"), WP_.get("play_a0.50_pinned", {}).get("spread_max")],
                bond=ZS_.get("bond", {}), bond_area=ZS_.get("bond_geo", {}).get("area"))


# ============================================================================ C04 snap-notch radius coupons (test 5)
def notch_geom(R):
    """lip geometry of the cloth-lined snap notch for a printed radius R (run_all.py 'snap law' formulas)."""
    Rn = R - P["cloth"]
    r = P["rod_k"] / 2
    bl = P["block_lift"]
    lip_h = math.sqrt(Rn ** 2 - bl ** 2)
    off = abs(bl - (Rn - r))                 # lip corner below the rod centre when the key rests on the rod
    clear = math.hypot(lip_h, off) - r
    touch = off - math.sqrt(max(0.0, r * r - lip_h * lip_h)) if lip_h < r else None
    popout = off
    interf = r - lip_h                        # radial interference the lips must pass at the equator (per side)
    return dict(Rn=Rn, lip_h=lip_h, clear=clear, touch=touch, popout=popout, interf=interf)


def c04():
    radii = (2.50, 2.525, 2.55, 2.575, 2.60)
    g0 = notch_geom(P["notch_R"])
    rows = []
    for R in radii:
        gg = notch_geom(R)
        est = MET["snap"]["F_model"] * (max(gg["interf"], 0.0) / g0["interf"]) ** 1.5
        rows.append(dict(R=R, clear=gg["clear"], touch=gg["touch"], popout=gg["popout"], interf=gg["interf"], F_est_white=est))
    wd = M.block_x(P, KEYS["D"])
    wb = M.block_x(P, KEYS["C#"])
    w_white, w_black = wd[1] - wd[0], wb[1] - wb[0]
    lift_play_max = MET["white"]["b_dip"] and max(MET["dyn"]["white"]["play_rel"]["lift_max"], 0)
    for colour, w in (("white", w_white), ("black", w_black)):
        s = HDR
        for k, R in enumerate(radii):
            P2 = dict(P)
            P2["notch_R"] = R
            poly = M.notch_block_poly(P2)
            ztop = P["block_top"] + 3.0              # handle plate 3 thick above the block top
            X0 = k * (w + 15.0)
            # print frame: X = x (block width), Y = key y, Z = ztop - key z (block top on the bed, notch opens upward)
            pp = [(y, ztop - z) for y, z in poly]
            ys = [p[0] for p in pp]
            blk = ("translate([%.4f,0,0]) rotate([90,0,90]) linear_extrude(height=%.4f) polygon(%s);\n"
                   % (X0, w, pts_([(y - 140.0, z) for y, z in pp])))
            hy0, hy1 = min(ys) - 140.0 - 7.0, max(ys) - 140.0 + 7.0
            handle = box(X0 - 5.5, X0 + w + 5.5, hy0, hy1, 0, 3.0)
            holes = cyl(X0 - 2.75, 0.0, -1, 5, 2.6) + cyl(X0 + w + 2.75, 0.0, -1, 5, 2.6)
            lab = ("%.3f" % R).rstrip("0")
            s += diff(uni(handle, blk), holes, text_(lab, X0 + w / 2, hy0 + 3.2, 3.0, size=2.4))
        part("C04" + ("a" if colour == "white" else "b"), "스냅 노치 반지름 쿠폰 (%s, R2.50~2.60, 5개)" % ("백건 블록 폭" if colour == "white" else "흑건 블록 폭"), 5, s,
             "건반처럼 뒤집어 (블록 윗면 = 손잡이 판을 베드에, 노치가 출력 맨 위의 열린 홈)",
             "블록 폭 %s (%s), 블록 y%.1f~%.1f, 노치 R = %s, 블록 밑면 봉 중심 아래 %.2f, 계단 z%.1f, 손잡이 판 3T + 줄 구멍 Ø3 두 개"
             % (f_(w, 2), "백 D" if colour == "white" else "흑 C#", P["block_y"][0], P["block_y"][1], " / ".join(("%.3f" % R).rstrip("0") for R in radii),
                -P["block_lift"], P["block_step_z"]),
             "노치에 부싱 천 0.5T를 붙이고 Ø4 봉에서 위로 당겨 빠짐 힘을 잰다. 1~2 N이 되는 반지름을 건반에 쓴다", settings=LIKE_KEY)
    # rod holder
    s = HDR
    body = box(0, 90, 0, 60, 0, 3.0)
    for xu in (45 - w_white / 2 - 5.0, 45 + w_white / 2 + 2.0):
        body += box(xu, xu + 3.0, 22, 38, 2.99, 3.0 + 26.0)
    hole = ("translate([-1,30,%.3f]) rotate([90,0,90]) linear_extrude(height=92) %s" % (3.0 + 20.0, teardrop2d(4.05, 90.0).strip()) + "\n")
    s += diff(uni(body), hole, text_("C04c rod", 20, 10, 3.0, size=4))
    part("C04c", "봉 받침 (당김 시험용, 저울 위)", 5, s, "바닥을 베드에, 봉 구멍은 눈물방울",
         "바탕 90×60×3 (날개에 1 kg 추를 얹음), 기둥 2개 간격 %.1f, Ø4.05 봉 구멍 중심 높이 23" % (w_white + 3.0),
         "Ø4 봉 토막(40)을 끼우고 쿠폰을 봉에 끼워 위로 당긴다")
    return dict(rows=rows, w_white=w_white, w_black=w_black, g0=g0, lift_play=P["lift_play"], lift_abuse=P["lift_abuse"])


# ============================================================================ C05 guide tab / cloth (test 6)
def c05():
    bl = [P["tab_w_b"] - 0.1, P["tab_w_b"], P["tab_w_b"] + 0.1]
    wh = [P["tab_w"] - 0.1, P["tab_w"], P["tab_w"] + 0.1]
    s = HDR
    body = box(0, 66, 0, 22, 0, 3.0)
    x = 4.0
    labs = ""
    for w in bl + wh:
        body += box(x, x + w, 6.0, 16.0, 2.99, 3.0 + 12.0)
        labs += text_(f_(w, 1), x + w / 2, 3.0, 3.0, size=2.2)
        x += w + 3.5
    s += diff(uni(body), labs)
    part("C05a", "가이드 탭 날 (프레임 쪽, 흑 %s / 백 %s)" % ("·".join(f_(w, 1) for w in bl), "·".join(f_(w, 1) for w in wh)), 6, s,
         "바닥을 베드에, 날이 수직 (프레임처럼)", "날 6개 두께 %s, 길이 10, 높이 12" % " / ".join(f_(w, 1) for w in bl + wh),
         "날 양면에 부싱 천(0.4 / 0.5 / 0.6T)을 붙여 건반 홈 쿠폰에 넣는다", settings=LIKE_FRAME)
    s = HDR
    for k, (gap, lab) in enumerate(((P["b_wall_in"], "B"), (P["rib_in"], "W"))):
        X0 = k * 22.0
        wl = P["wall"]
        body = box(X0, X0 + gap + 2 * wl, 0, 14.0, 0, 2.0) + box(X0, X0 + wl, 0, 14.0, 1.99, 2.0 + 12.0) + box(X0 + gap + wl, X0 + gap + 2 * wl, 0, 14.0, 1.99, 2.0 + 12.0)
        s += diff(uni(body), text_("%s%s" % (lab, f_(gap, 1)), X0 + wl + gap / 2, 7.0, 2.0, size=2.4, rot=90))
    part("C05b", "건반 홈 쿠폰 (흑 벽 사이 %s, 백 갈비 사이 %s)" % (f_(P["b_wall_in"], 1), f_(P["rib_in"], 1)), 6, s,
         "건반처럼 뒤집어 (윗판 쪽을 베드에, 홈이 위로 열림)", "벽 1.2, 홈 폭 %s / %s, 길이 14, 깊이 12" % (f_(P["b_wall_in"], 1), f_(P["rib_in"], 1)),
         "천 붙인 탭 날에 끼워 옆 놀음·걸림을 본다 (쿠폰 무게 = 모델 가이드 끌림 0.02 N 판정)", settings=LIKE_KEY)
    return dict(black=bl, white=wh, cloth=P["tab_cloth"], slot_b=P["b_wall_in"], slot_w=P["rib_in"], tab_play=P["tab_play"],
                guide_drag=P["guide_drag"])


# ============================================================================ C06 torsion spring rig (test 8)
def c06():
    L = P["L"]
    sg = P["spring_groove"]
    y_bot = sg[0] + sg[4]                           # groove bottom (loaded leg bears here)
    ytip = y_bot - P["spring_d"] / 2
    rho = P["spring_leg"]
    ztip = L[1] + math.sqrt(rho * rho - (ytip - L[0]) ** 2)
    arm = ztip - L[1]                               # moment arm of the groove force (along y) about the rod
    kt, bf = P["spring_kt"], P["spring_free_deg"]
    states = MET["spring"]["states"]
    Rd = 20.0
    rows = []
    for b in (-20, -10, 0, 5, 10, 12.6, 16, 20, 25):
        T = M.spring_pose(P, float(b))["T"]           # r4.5 fix round: the model's T(b) (captured short leg, coil radius follows the wind)
        rows.append(dict(b=b, T=T, grams=T / (Rd * GN), F_groove=T / arm))
    # --- C06a bracket (rig coords = machine (y - Ly, z - Lz); print: bracket back on the bed, +x up)
    xb0, xb1 = -4.0, 0.0
    zp = lambda x: x - xb0
    foot_v = -40.0
    outline = arc_pts((0, 0), 32.0, -60, 240, 60) + [(-60.0, foot_v - 5.0), (8.0, foot_v - 5.0), (8.0, -27.7)]
    outline = [(-60.0, foot_v - 5.0), (8.0, foot_v - 5.0), (8.0, -27.7)] + arc_pts((0, 0), 29.0, -73, 250, 80)
    s = HDR
    body = ext(outline, zp(xb0), zp(xb1))
    body += ext([(-60.0, foot_v - 5.0), (8.0, foot_v - 5.0), (8.0, foot_v), (-60.0, foot_v)], zp(xb1) - 0.01, zp(40.0))
    body += cyl(0, 0, zp(xb1) - 0.01, zp(1.0), 8.0)
    # groove boss (machine rear-wall boss face y207.8, groove to the model bottom, z47 .. 58), coil centre plane x = 2.7
    # r4.5: groove sg[3] wide centred on the coil (the long leg leaves the coil's +x end at +0.8 and rises straight), walls 1.0
    # on the far side like the model boss (spring_boss[0] = groove + 2 x 1.0); r4.4: one-sided 1.2 ledge
    x_leg = 2.7 + P.get("spring_groove_dx", 0.0)     # r4.5 fix 2: groove on the long leg (coil centre plane x 2.7 + 0.8), like the module boss
    u_face, u_bot = sg[0] - L[0], y_bot - L[0]
    v0, v1 = sg[1] - L[1], sg[2] - L[1]
    xg0, xg1 = x_leg - sg[3] / 2, x_leg + sg[3] / 2
    body += box(u_face, u_face + 6.0, v0, v1 + 3.0, zp(xb1) - 0.01, zp(x_leg + P["spring_boss"][0] / 2))
    ring = (22.5, 29.0)
    body += ext(annulus_sector((0, 0), ring[0], ring[1], 112.0, 248.0, 80), zp(xb1) - 0.01, zp(7.8))
    cuts = cyl(0, 0, -1, zp(1.0) + 1, 3.9)
    cuts += box(u_face - 0.01, u_bot, v0 - 0.01, v1 + 3.1, zp(xg0), zp(xg1))
    for b in range(-40, 36, 2):
        a = math.radians(180.0 - b)
        if not (112.5 <= 180.0 - b <= 247.5):
            continue
        rl = ring[0] + (3.8 if b % 10 == 0 else 2.3)
        w = 0.35
        pa = (ring[0] - 0.3) * math.cos(a), (ring[0] - 0.3) * math.sin(a)
        pb = rl * math.cos(a), rl * math.sin(a)
        nx, ny = -math.sin(a) * w / 2, math.cos(a) * w / 2
        cuts += ext([(pa[0] + nx, pa[1] + ny), (pb[0] + nx, pb[1] + ny), (pb[0] - nx, pb[1] - ny), (pa[0] - nx, pa[1] - ny)], zp(7.8) - 0.5, zp(7.8) + 0.2)
        if b % 10 == 0:
            cuts += text_(str(b), (ring[1] - 1.0) * math.cos(a), (ring[1] - 1.0) * math.sin(a), zp(7.8), size=1.6, depth=0.35, rot=180.0 - b - 90.0)
    s += diff(uni(body), cuts)
    part("C06a", "비틀림 스프링 시험대 (브래킷·뒷벽 홈 복제·레버 각 눈금)", 8, s,
         "브래킷 뒷면을 베드에 (홈 보스·눈금 고리·발이 위로)",
         "봉 축 높이 %.0f (발 윗면에서), Ø3.9 구멍 (→ Ø4.0 드릴, 봉 압입), 홈 바닥 y%.2f (축에서 %.2f), 폭 %.1f (긴 다리 x%.1f ±%.1f = 코일 가운데 +0.8, r4.5 고침 2), z%.1f~%.1f = 모델 뒷벽 홈, 눈금 b −40~+34° (2°)"
         % (-foot_v, y_bot, u_bot, sg[3], x_leg, sg[3] / 2, sg[1], sg[2]),
         "스프링 긴 다리를 모델과 같은 뒷벽 홈에 걸고, 짧은 다리는 북(허브 복제)에 걸어 레버 각별 토크를 추로 잰다")
    # --- C06b drum: hub replica + disk R 21 with a thread groove at r 20.  r4.5 fix 2: the hub part is the model's own pocket
    # section (model_v4.hub_pocket_poly: pieces A + B = ring + web stub, with the pocket, the insertion slot along the short
    # leg, the long-leg window and the captured short-leg groove with its blind end in the web), clipped to R 10.5
    s = HDR
    Dp, tp = P["spring_pocket"]
    # print frame: Z = 11.2 - x (disk front face on the bed): disk Z 0..5 (rig x 6.2..11.2), hub spacer Z 5..7 (x 4.2..6.2: the
    # groove boss of C06a, now on the long leg at x 3.5 +- 2.2, stays 0.5 off the disk), pocket section Z 7..10 (x 1.2..4.2); the
    # print frame mirrors the lever frame: (u, v) = (y - Ly, -(z - Lz))
    disk = cyl(0, 0, 0, 5.0, 42.0, 128)
    # r4.5 fix 3 (verifier): the spacer is 0.05 inside the hub radius.  At R 4.3 its 64-gon had a vertex at (0, -4.3), exactly
    # the corner where the pocket section's outline leaves the hub circle for the web -> 4 non-manifold edges at Z 7.01
    spacer = cyl(0, 0, 4.99, 7.01, 2 * P["hub_R"] - 0.1)
    groove = ("rotate_extrude($fn=128) translate([20.0,2.5]) polygon([[0,-0.6],[1.6,-2.2],[1.6,2.2],[0,0.6]]);\n")
    NG = M.spring_notch_geo(P)
    pcs = M.hub_pocket_poly(P, M.lever_web_poly(P))
    sect = "intersection(){\n" + uni(*[ext([(q[0] - L[0], -(q[1] - L[1])) for q in pc_], 7.0, 10.0) for pc_ in pcs]) + cyl(0, 0, 6.9, 10.1, 21.0, 96) + "}\n"
    bore = cyl(0, 0, -1, 12, 4.1)
    tie = cyl(18.0 * math.cos(math.radians(-100)), 18.0 * math.sin(math.radians(-100)), -1, 6, 1.6)   # rig +100 deg (top): thread over the top, off the +y side
    mark = box(-21.5, -17.5, -0.35, 0.35, 5.0 - 0.6, 5.2)       # pointer line at lever-frame angle 180 deg (mirrored: -X)
    s += diff(uni(disk, spacer, sect), groove, bore, tie, mark, text_("C06b", 0, -10, 5.0, size=3.0))
    part("C06b", "스프링 북 (허브 주머니·가둠 홈·넣는 슬롯·긴 다리 창 복제 + 실 감는 북 R20)", 8, s,
         "북 앞면을 베드에 (허브가 위)",
         "북 Ø42 (실 홈 바닥 반지름 20.0) + 허브 받침 2.0, 모델 주머니 단면(허브 R%.1f + 웹 조각, R10.5에서 자름) Z7~10: 주머니 Ø%.1f×%.1f, 짧은 다리 가둠 홈 폭 %.2f(%.2f° 방향, 축에서 %.2f~%.2f, 막힌 끝), 넣는 슬롯 %.1f° ±%.2f, 긴 다리 창 %.0f° +%.1f (r4.5 고침 2), 구멍 Ø4.1"
         % (P["hub_R"], Dp, tp, NG["width"], (NG["short"]["alpha_s"] - 90.0 - NG["theta_c"]) % 360.0, NG["c_i"], NG["c_o"], NG["slot_deg"], P["spring_slot"][2], P["spring_window"][0], P["spring_window"][1]),
         "봉에서 돌며 짧은 다리를 가둔다(생산 레버와 같은 두 점 짝 힘). 실을 북 홈에 감아 오른쪽(+y)으로 내려 추 컵(C14)을 단다", settings=SOLID)
    return dict(arm=arm, tip=(ytip, ztip), kt=kt, free=bf, Rd=Rd, rows=rows, states=states, k_coil=MET["spring"]["k_coil"], notch=dict(alpha_s=NG["short"]["alpha_s"], nn=(NG["c_i"], NG["c_o"]), leg_dir=(NG["short"]["alpha_s"] - 90.0) % 360.0, width=NG["width"],
                                                                                                 band_deg=(NG["short"]["alpha_s"] - 90.0 - NG["theta_c"]) % 360.0, slot_deg=NG["slot_deg"], theta_c=NG["theta_c"], arm=NG["arm"]),
                groove_x=(xg0, xg1), skin_min=0.4, deeper_max=P["rear_wall"][1] - (sg[0] + sg[4]) - 0.4,
                tol_p30=-MET["spring"]["capture_tol"]["+0.30"]["dT"] if "capture_tol" in MET["spring"] else 0.0,
                DW_per_T=(MET["white"]["DW"] - MET["white"]["DW_nospring"]) / MET["white"]["spring_T_rest"],
                x_leg=x_leg, foot=-foot_v)


# ============================================================================ C07 balance pin press fit
def c07():
    ds = (1.80, 1.85, 1.90, 1.95, 2.00)
    z_rail = MET["heights"]["z_rail_low"]
    z_pin_top = P["block_step_z"] + P["pin_engage"]
    prot = z_pin_top - z_rail
    depth = P["pin_len"] - prot
    s = HDR
    blen = 70.0
    body = box(0, blen, 0, P["rail_y"][1] - P["rail_front_y"], 0, z_rail - P["z_floor"][1])
    hz = z_rail - P["z_floor"][1]
    cuts = ""
    for k, d in enumerate(ds):
        x = 8.0 + k * 13.5
        cuts += cyl(x, (P["rail_y"][1] - P["rail_front_y"]) / 2 + 1.5, -1, hz + 1, d, 48)
        cuts += text_(f_(d, 2), x, 2.6, hz, size=2.3)
    s += diff(body, cuts)
    part("C07a", "밸런스 핀 압입 레일 쿠폰 (구멍 Ø1.80~2.00, 5개)", "P", s, "바닥을 베드에 (구멍이 수직, 프레임 레일처럼)",
         "레일 조각 %.0f×%.1f×%.1f (z%.0f~%.1f = 모델 레일 낮은 부분), 관통 구멍 %s" % (blen, P["rail_y"][1] - P["rail_front_y"], hz, P["z_floor"][1], z_rail,
                                                                           " / ".join(f_(d, 2) for d in ds)),
         "Ø2×12 핀을 높이 게이지로 %s 돌출까지 눌러 넣으며 누름 힘·흔들림을 본다" % f_(prot, 2), settings=LIKE_FRAME)
    s = HDR
    s += diff(box(0, 30, 0, 10, 0, 8.0), cyl(15, 5, -1, prot, 2.4, 32), text_("%s" % f_(prot, 2), 15, 5, 8.0, size=3.5))
    part("C07b", "핀 돌출 게이지 (%s)" % f_(prot, 2), "P", s, "밑면을 베드에 (Ø2.4 막힌 구멍이 아래로 열림)",
         "30×10×8, 밑면에서 Ø2.4 구멍 깊이 %s = 핀 꼭대기 z%s − 레일 윗면 z%s" % (f_(prot, 2), f_(z_pin_top, 2), f_(z_rail, 2)),
         "핀 머리에 씌워 게이지 밑면이 레일에 닿을 때까지 누른다")
    return dict(ds=ds, z_rail=z_rail, z_pin_top=z_pin_top, prot=prot, depth=depth, yaw_pin=P["yaw_pin"])


# ============================================================================ C08 capstan nut trap
def c08():
    yc = MET["white"]["y_cap"]
    zc = P["z_c"]
    z_head_bot = zc - P["cap_k"]
    zt0, zt1 = 23.8, 26.4                    # nut trap void (key_body mass model)
    variants = [(5.6, 2.8), (5.7, 2.8), (5.8, 2.8), (5.6, 2.7), (5.6, 2.9)]
    s = HDR
    base_t = 3.0
    zb0, zcap = P["beam_z"][0], P["beam_z_cap"]
    H = zcap - zb0
    # print frame: Z = (zcap + base_t) - z  (beam top on the base plate, like the key printed top-down)
    Z = lambda z: zcap + base_t - z
    body = box(0, 5 * 16.0 + 6.0, 0, 26.0, 0, base_t)
    cuts = ""
    for k, (wn, dh) in enumerate(variants):
        X0 = 6.0 + k * 16.0
        xc = X0 + P["beam_w"] / 2
        body += box(X0, X0 + P["beam_w"], 3.0, 23.0, base_t - 0.01, Z(zb0))
        cuts += cyl(xc, 13.0, -1, base_t + 0.01, 7.0)                       # capstan head / hex key access
        cuts += cyl(xc, 13.0, Z(zt0) - 0.01, Z(zb0) + 1, 3.3)                 # screw tip clearance below the nut
        cuts += cyl(xc, 13.0, base_t - 0.01, Z(zt1) + 0.01, dh, 32)           # self-locking hole (above the nut)
        cuts += box(xc - wn / 2, X0 + P["beam_w"] + 1, 13.0 - wn / 2, 13.0 + wn / 2, Z(zt1), Z(zt0))   # side-open nut slot
        cuts += text_(str(k + 1), xc, 24.6, base_t, size=2.2)
    s += diff(uni(body), cuts)
    part("C08a", "캡스턴 너트 트랩 빔 쿠폰 (5종)", "C", s, "건반처럼 뒤집어 (빔 윗면 = 바탕 판을 베드에); 너트 홈 천장은 5.6~5.8 브리지",
         "빔 폭 %.1f, z%.1f~%.1f (캡스턴 자리), 너트 홈 z%.1f~%.1f 옆에서 열림: 1) %s" % (P["beam_w"], zb0, zcap, zt0, zt1,
                                                                                ", ".join("%d) 홈 %s / 구멍 Ø%s" % (i + 1, f_(w, 1), f_(d, 1)) for i, (w, d) in enumerate(variants))[3:]),
         "M3 너트를 옆에서 끼우고 M3×6 버튼헤드를 위 Ø구멍으로 돌려 넣어 자가 잠김 토크·유지를 본다", settings=LIKE_KEY)
    adj = MET.get("adjust", {})
    return dict(y_cap=yc, z_head_top=zc, z_head_bot=z_head_bot, trap=(zt0, zt1), variants=variants, pitch=0.5, eighth=0.0625, adjust=adj)


# ============================================================================ C09 felt / cloth thickness gauge
def c09():
    s = HDR
    body = box(0, 34, 0, 70, 0, 4.0) + box(6, 28, 13, 35, 3.99, 5.0)
    # gantry over the presser end (y 50..60): legs outside the presser width 24 (x 5..29)
    body += box(0, 4, 50, 60, 3.99, 27.0) + box(30, 34, 50, 60, 3.99, 27.0) + box(0, 34, 50, 60, 24.0, 27.0)
    s += diff(uni(body), cyl(17, 55, 23, 28, 4.0), text_("C09a", 17, 6, 4.0, size=4))
    part("C09a", "두께 측정 받침 (22×22 자리 + 깊이 막대 다리)", "T", s, "바닥을 베드에 (다리 윗판 12 브리지)",
         "바탕 34×70×4, 자리 22×22×1, 다리 윗면 z27, 깊이 막대 구멍 Ø4 (y55)", "시편을 자리에 놓고 누름판(C09b)을 얹어 다리 위에서 버니어 깊이 막대로 잰다")
    s = HDR
    body = box(0, 24, 0, 60, 0, 4.0) + box(2, 22, 10, 30, 3.99, 6.0)
    s += diff(uni(body), box(12 - 4.75, 12 + 4.75, 0, 40.5, -1, 1.5))
    part("C09b", "누름판 (발 20×20, 강철 블록 자리)", "T", s, "누름판 윗면을 베드에 (발이 위, 강철 자리 홈은 바닥 쪽 1.5 깊이)",
         "판 24×60×4 + 발 20×20×2, 강철 블록(9×40 면) 자리 9.5×40.5×1.5", "빈 누름판 / 강철 1개 / 강철 2개로 누르는 압력 3단계")
    felts = [("앞 펠트 (백)", P["felt_front"], "front", "w_felt"), ("쉼 펠트", P["rest_felt"], "rest", None), ("키퍼 펠트", P["keeper_felt"], "keeper", None),
             ("캡스턴 펠트", P["felt_c"], "cap", None), ("패드 펠트", P["pad_felt"], "pad felt", None), ("패드 폼", P["pad_foam"], "foam", None),
             ("부싱 천", P["cloth"], "cloth", None)]
    return dict(felts=felts, foot=20.0)


# ============================================================================ C10 pad-bar leaf creep
def c10():
    t, w, Ll, pre = P["bar_leaf"]
    bump = P["bar_leaf_bump"]
    gap = P["bar_leaf_gap"]
    bump_h = gap + pre
    I = w * t ** 3 / 12
    F = 3 * M.E_PETG * I * pre / Ll ** 3
    sig = 3 * M.E_PETG * t * pre / (2 * Ll ** 2)
    sig_tol = 3 * M.E_PETG * t * (pre + M.TOL) / (2 * Ll ** 2)
    bar_mass = MET.get("mass", {}).get("pad_bar") if isinstance(MET.get("mass"), dict) else None
    s = HDR
    for k in range(3):
        X0 = k * 14.0
        body = box(X0, X0 + 10.0, 0, 10.0, 0, P["pad_bar_t"])                       # root block (bar thickness)
        body += box(X0 + (10.0 - w) / 2, X0 + (10.0 + w) / 2, 9.99, 10.0 + Ll, 0, t)    # tongue, printed flat (bar prints flat)
        body += box(X0 + (10.0 - w) / 2, X0 + (10.0 + w) / 2, 10.0 + Ll - bump, 10.0 + Ll, t - 0.01, t + bump_h)
        s += diff(uni(body), text_(str(k + 1), X0 + 5.0, 5.0, P["pad_bar_t"], size=3.0))
    part("C10a", "패드 바 잎 혀 쿠폰 (3개)", 12, s, "패드 바처럼 넓은 면을 베드에 (혀 0.6 = 3층)",
         "뿌리 10×10×%.1f, 혀 %.1f×%.1f×%.1f, 끝 돌기 %.1f 길이 × %.1f 높이 (설치 휨 %.1f + 틈 %.1f)" % (P["pad_bar_t"], w, Ll, t, bump, bump_h, pre, gap),
         "돌기를 0.3 (공차 끝 0.6) 눌린 채 40 °C 1주 두고, 전후 잎 힘을 0.1 g 저울로 잰다", settings=LIKE_FRAME.replace("프레임", "패드 바"))
    s = HDR
    # creep fixture: 2 stations; root pad at z = 4 (top), tip ledge at z = 4 - bump_h + defl (bump faces down)
    body = box(0, 48, 0, 26, 0, 2.0)
    cuts = ""
    for k, defl in enumerate((pre, pre + M.TOL)):
        X0 = 3.0 + k * 23.0
        body += box(X0, X0 + 12.0, 2, 13.0, 1.99, 4.0)                                # root seat (root 10x10 sits here)
        body += box(X0 + 2.0, X0 + 10.0, 13.0 + Ll - bump - 0.5, 13.0 + Ll + 1.5, 1.99, 4.0 - bump_h + defl)   # tip ledge
        cuts += text_(f_(defl, 1), X0 + 6.0, 7.5, 4.0, size=3.0)
    s += diff(uni(body), cuts)
    part("C10b", "잎 크리프 받침 (0.3 / 0.6 눌림 두 자리)", 12, s, "바닥을 베드에",
         "뿌리 자리 윗면 z4, 돌기 받침 윗면 z%s / z%s (돌기 %s 아래에서 %s / %s 올림)" % (f_(4.0 - bump_h + pre, 2), f_(4.0 - bump_h + pre + M.TOL, 2), f_(bump_h, 1), f_(pre, 1), f_(pre + M.TOL, 1)),
         "쿠폰을 돌기가 아래로 가게 얹고 뿌리 위에 강철 블록 1개를 올려 누른다 (잎 힘 %s N ≪ 강철 0.53 N)" % f_(F, 2))
    s = HDR
    body = box(0, 30, 0, 24, 0, 3.0) + box(0, 30, 0, 12, 2.99, 12.0)
    s += diff(uni(body), text_("C10c", 15, 18, 3.0, size=4))
    part("C10c", "잎 힘 측정 받침 (뿌리 물림 턱 높이 12)", 12, s, "바닥을 베드에",
         "30×24×3 판 + 30×12×9 턱 (턱 윗면에 쿠폰 뿌리를 강철 블록으로 눌러 혀가 저울판 위로 나감)",
         "턱을 저울 옆 탁자에 두고 PET 심을 한 장씩 빼며 돌기를 저울판에 0.3 누른다")
    return dict(t=t, w=w, L=Ll, pre=pre, bump=bump, bump_h=bump_h, F=F, sig=sig, sig_tol=sig_tol, grams=F / GN)


# ============================================================================ C11 top-plate bridge print coupon (test 16)
def c11():
    fins = LAY["fins"]
    bays = M.bays(fins)
    spans = [b - a for a, b in bays]
    ib = int(np.argmax(spans))
    xa, xb = fins[ib][0], fins[ib + 1][1]
    g2 = dict(G)
    for k_ in ("z_rail_low", "z_block_min"):                 # set by finish_geo (needs the dynamics): read back from metrics
        g2.setdefault(k_, MET["heights"][k_])
    for k_ in ("b_ff_w", "b_ff_b", "b_over_w", "b_over_b", "a_ff_w", "a_ff_b"):
        g2.setdefault(k_, math.radians(MET["heights"][k_]))
    F = M.fixed_prisms(P, g2)
    keep = []
    zcut = 50.0
    for tag, x0, x1, poly in F:
        grp = M.print_group(tag)
        if grp != "frame" or not tag.startswith(("top plate", "fin", "rear wall", "spring groove boss", "pad bar rail")):
            continue
        if tag.startswith("fin boss"):
            continue
        lo, hi = max(x0, xa), min(x1, xb)
        if hi - lo < 1e-6:
            continue
        zmax = max(z for y, z in poly)
        if zmax <= zcut:
            continue
        keep.append((tag, lo, hi, poly))
    # print frame: X = x - xa + 6, Y = y - 146.5 + 2, Z = z - (zcut - 2.5)
    zf = zcut - 2.5
    X = lambda x: x - xa + 6.0
    Y = lambda y: y - 144.5
    s = HDR
    parts_s = ""
    for tag, lo, hi, poly in keep:
        pp = [(Y(y), z - zf) for y, z in poly]
        parts_s += ("intersection(){translate([%.4f,0,0]) rotate([90,0,90]) linear_extrude(height=%.4f) polygon(%s);"
                    " translate([-10,-10,%.4f]) cube([400,400,200]);}\n" % (X(lo), hi - lo, pts_(pp), zcut - zf))
    # floor strips under the two fins and the rear wall (window between them so the underside can be probed)
    fy0, fy1 = P["fin_y"]
    rw0, rw1 = P["rear_wall"]
    floor = box(X(fins[ib][0]) - 5.0, X(fins[ib][1]) + 3.0, Y(fy0), Y(rw1), 0, 2.5)
    floor += box(X(fins[ib + 1][0]) - 3.0, X(fins[ib + 1][1]) + 5.0, Y(fy0), Y(rw1), 0, 2.5)
    floor += box(X(fins[ib][0]) - 5.0, X(fins[ib + 1][1]) + 5.0, Y(rw0) - 6.0, Y(rw1), 0, 2.5)
    s += uni(parts_s, floor)
    part("C11a", "윗판 브리지 출력 쿠폰 (핀 사이 %s, 모델 프레임 그대로 z%.0f 위)" % (f_(spans[ib], 2), zcut), 16, s,
         "바로 세워 (프레임처럼), 서포트 없이 — 시험 자체가 서포트 없는 브리지",
         "핀 x%s~%s / x%s~%s (칸 %d, 폭 %s), 윗판 y%.1f~%.1f (밑면 z%s / %s / %s), L 레일·립·스프링 홈 보스 포함, z%.0f 아래는 잘라 바닥 띠 2.5"
         % (f_(fins[ib][0], 2), f_(fins[ib][1], 2), f_(fins[ib + 1][0], 2), f_(fins[ib + 1][1], 2), ib + 1, f_(spans[ib], 2), P["ledge_y0"], P["rear_wall"][1],
            f_(G["plate_under"][0][1], 2), f_(G["z_seat"], 2), f_(min(z for y, z in G["plate_under"]), 2), zcut),
         "윗판 밑 서포트(모듈 88 g)를 없앨 수 있는지: 브리지 처짐 ≤ 0.3, 레일 립이 서는지, 패드 바가 들어가는지", settings=LIKE_FRAME)
    return dict(bay=ib + 1, span=spans[ib], x=(xa, xb), zcut=zcut, n_prisms=len(keep), tags=sorted(set(t for t, *_ in keep)))


# ============================================================================ C12 across-layer tension (fin-plate joint, test 15)
def c12():
    tg, wg, lg = P["fin_t"], 2.0, 12.0
    A = tg * wg
    s = HDR
    for k in range(3):
        X0 = k * 22.0
        cx = X0 + 8.0
        grip = lambda z0: box(X0, X0 + 16.0, 0, 8.0, z0, z0 + 10.0)
        body = grip(0.0)
        body += ("hull(){" + box(X0, X0 + 16.0, 0, 8.0, 9.99, 10.0).strip() + box(cx - wg / 2, cx + wg / 2, 4.0 - tg / 2, 4.0 + tg / 2, 16.5, 16.51).strip() + "}\n")
        body += box(cx - wg / 2, cx + wg / 2, 4.0 - tg / 2, 4.0 + tg / 2, 16.5, 16.5 + lg)
        body += ("hull(){" + box(cx - wg / 2, cx + wg / 2, 4.0 - tg / 2, 4.0 + tg / 2, 16.49 + lg, 16.5 + lg).strip() + box(X0, X0 + 16.0, 0, 8.0, 23.0 + lg - 0.01, 23.0 + lg).strip() + "}\n")
        body += grip(23.0 + lg)
        hole = lambda zc: ("translate([%.3f,-1,%.3f]) rotate([-90,0,0]) linear_extrude(height=10) %s" % (cx, zc, teardrop2d(4.3, 270.0).strip()) + "\n")
        s += diff(uni(body), hole(5.0), hole(28.0 + lg))
    part("C12a", "층간 인장 쿠폰 (핀 두께 %s × 폭 %s, 3개)" % (f_(tg, 1), f_(wg, 1)), 15, s, "바로 세워 (당김 방향 = 층을 가로지름, 프레임 핀과 같음); 끝 구멍은 눈물방울",
         "목 %s×%s×%s (단면 %s mm²), 잡이 16×8×10 + Ø4.3 구멍 (Ø4 봉 토막을 끼워 줄을 검)" % (f_(wg, 1), f_(tg, 1), f_(lg, 0), f_(A, 1)),
         "양동이에 물을 부어 끊어질 때의 무게로 층간 강도를 잰다", settings=LIKE_FRAME)
    st = MET["plate"]
    return dict(A=A, s_single=st["play"]["single"]["fin_top"], s_chord=st["play"]["chord"]["fin_top"],
                s_abuse=st["abuse_chord20"]["chord"]["fin_top"], s_cyc=P["s_cyc"], s_rare=P["s_rare"])


# ============================================================================ C13 USB-C overmould gauge (test 19)
def c13():
    ux, uy, uz = P["usb_x"], P["usb_y"], P["usb_z"]
    w, h, Lm = ux[1] - ux[0], uz[1] - uz[0], uy[1] - uy[0]
    s = HDR
    s += diff(box(0, w + 8, 0, h + 8, 0, Lm), box(4, 4 + w, 4, 4 + h, -1, Lm + 1), text_("%sx%s" % (f_(w, 1), f_(h, 1)), (w + 8) / 2, 2.0, Lm, size=2.2))
    part("C13a", "USB-C 몰드 게이지 (%s × %s × %s)" % (f_(w, 1), f_(h, 1), f_(Lm, 0)), 19, s, "창이 수직이 되게 세워 (xy 정밀도)",
         "바깥 %s×%s×%s, 창 %s×%s 관통 (케이블 몰드 한계 = 회로 인터페이스, 고정값)" % (f_(w + 8, 1), f_(h + 8, 1), f_(Lm, 0), f_(w, 1), f_(h, 1)),
         "케이블을 사기 전/후 몰드가 창을 끝까지 걸림 없이 지나가는지 본다 (출력 뒤 창을 캘리퍼로 확인)")
    return dict(w=w, h=h, L=Lm, slot=M.usb_slot(P), clear=P["usb_clear"])


# ============================================================================ C14 weight cup (DW/UW, spring, capstan torque)
def c14():
    s = HDR
    body = cyl(0, 0, 0, 18.0, 26.0) + box(-6, 6, -6, 6, 0, 1.0)
    ears = box(-15.5, -11.0, -2.0, 2.0, 0, 18.0) + box(11.0, 15.5, -2.0, 2.0, 0, 18.0)
    s += diff(uni(body, ears), cyl(0, 0, 1.2, 19, 23.6), cyl(-13.6, 0, -1, 19, 1.8), cyl(13.6, 0, -1, 19, 1.8))
    part("C14a", "추 컵 (DW·스프링·캡스턴 토크)", 7, s, "바닥을 베드에", "Ø26×18, 벽 1.2, 바닥 1.2, 줄 귀 Ø1.8 두 개; 빈 컵 무게를 0.1 g 저울로 잼",
         "물·동전을 부어 무게를 맞춘다. DW는 컵 바닥 가운데를 y13(흑 앞+10)에 놓음")
    return dict()


# ============================================================================ C15 front-felt drop tube (test 4)
def c15():
    d_ball = 19.05
    m_ball = math.pi / 6 * d_ball ** 3 * M.RHO_ST
    e_front = P["front_e"]
    KE = M.FELT["front"]
    e_model_ball = M.felt_effective_e(KE, m=m_ball, v=1.5)
    hs = {1.5: 1.5 ** 2 / (2 * 9.80665) * 1000.0, 1.0: 1.0 ** 2 / (2 * 9.80665) * 1000.0}
    base_t = 6.0
    felt_stack = P["felt_front"] + 1.0              # felt 3T on PU 1T
    s = HDR
    tube_id, tube_od = d_ball + 0.8, d_ball + 4.8
    ztop = base_t + felt_stack + max(hs.values()) + d_ball + 8.0
    body = box(-22, 22, -22, 22, 0, base_t) + cyl(0, 0, base_t - 0.01, ztop, tube_od, 96)
    cuts = cyl(0, 0, base_t - 0.01, ztop + 1, tube_id, 96)
    z_felt_top = base_t + felt_stack
    # viewing window (y+ side) over the rebound zone, ticks every 1 mm (5 mm long ones) beside it
    cuts += box(-3.0, 3.0, 0, tube_od, z_felt_top - 2.0, z_felt_top + 25.0)
    for i in range(0, 26):
        zz = z_felt_top + i
        ln = 3.0 if i % 5 else 5.0
        cuts += box(3.6, 3.6 + ln, tube_od / 2 - 1.2, tube_od / 2 + 1, zz - 0.2, zz + 0.2)
    # skewer holes (release): ball bottom at h above the felt top -> skewer centre at h + d_ball + 1.6
    for v, h in hs.items():
        zc = z_felt_top + h - 1.5              # a D3 bamboo skewer across the tube: the ball bottom rests on its top
        cuts += "translate([0,0,%.3f]) rotate([0,90,0]) cylinder(h=40, d=3.3, center=true, $fn=24);\n" % zc
    s += diff(uni(body), cuts, text_("C15", 14, -15, base_t, size=4))
    part("C15a", "앞 펠트 반발 낙하관 (Ø%s 강철 공)" % f_(d_ball, 2), 4, s, "바닥을 베드에 (관이 수직)",
         "바탕 44×44×%.0f (펠트 3T + PU 1T를 바탕 윗면 가운데에 붙임), 관 안지름 %s, 창 6 폭·1 mm 눈금 25, 놓는 꼬치 구멍 Ø3.3 (공 밑 %s / %s mm 위)"
         % (base_t, f_(tube_id, 2), f_(hs[1.5], 1), f_(hs[1.0], 1)) + " (꼬치 Ø3 중심 = 펠트 윗면 + h − 1.5)",
         "공(%s g)을 꼬치에 얹었다가 꼬치를 빼 떨어뜨리고, 240 fps로 되튄 높이를 읽는다" % f_(m_ball, 1))
    return dict(d=d_ball, m=m_ball, e=e_front, e_model_ball=e_model_ball, h=hs, z_window=(z_felt_top, z_felt_top + 25.0),
                K=KE[0])


# ============================================================================ C17 first-module dead-load support comb (test 21)
def c17():
    """r4.5 fix 3 (verifier major): test 21 in the service direction.  In service the pads push the top plate UP; the F|F#
    fin and its keel pull the balance rail's rear face up and the rail lifts between the fin lines (model keel_rail 'fins':
    rail + floor strip continuous over the module's fin lines, simply supported there, twist held).  Loading the plate from
    above with the module on its floor EVA pushes the rail + floor strip (z3-5) onto the EVA (z0-3) = the rigid-rail case,
    whatever the rail's own stiffness.  The model is linear, so standing the module on narrow strips under the fin lines and
    the rear wall only (nothing under the rail between the fin lines, the board hatch open) and loading from above gives the
    service case.  C17a is that support: a flat comb as high as the EVA, one 3-wide tooth under each fin line over the full
    depth (the module cannot tip forward) and a bar under the rear wall.  The dead-load seat deflections of the loaded chord
    are computed here for the rail-support bounds (plate_loads on that chord only)."""
    W_, D_ = P["module_w"], P["frame_depth"]
    h = P["z_eva"][1] - P["z_eva"][0]
    tw = 3.0
    KR_ = MET["keel_rail"]
    DL_ = KR_["dead"]
    rail_ = KR_["rail"]
    lines = [rail_["span"][0]] + list(rail_["inner"]) + [rail_["span"][1]]
    fc = sorted(0.5 * (f0 + f1) for f0, f1 in LAY["fins"])
    hx = P["board_hatch"]
    keel_x = [x for x in fc if hx[0] < x < hx[1]]
    assert len(keel_x) == 1 and all(min(abs(x - c) for c in fc if c not in keel_x) < 1e-6 for x in lines) and len(lines) == len(fc) - 1, (lines, fc)
    teeth = [(min(max(c - tw / 2, 0.0), W_ - tw), min(max(c - tw / 2, 0.0), W_ - tw) + tw) for c in lines]
    rw = P["rear_wall"]
    bar = (0.0, W_, rw[0], rw[1])
    # nothing under the rail between the fin lines, nothing under the board hatch (x46.25-118.25, y144.5-196.5)
    gap = (teeth[1][1], teeth[2][0])
    assert teeth[1][1] < hx[0] and teeth[2][0] > hx[1] and bar[2] > hx[3], (teeth, hx)
    s = HDR
    body = box(bar[0], bar[1], bar[2], bar[3], 0.0, h)
    for x0, x1 in teeth:
        body += box(x0, x1, 0.0, bar[2] + 0.01, 0.0, h)
    lab_x = 0.5 * (teeth[1][0] + teeth[1][1])
    s += diff(uni(body), text_("C17a", lab_x, 12.0, h, size=2.0, depth=0.4, rot=90.0))
    part("C17a", "정하중 받침 빗 (핀 선 4줄 + 뒷벽, 레일 밑은 빔)", 21, s, "납작하게 (어느 면이든 베드에)",
         "높이 %s (= 바닥 EVA z%s~%s), 이 폭 %s × 길이 %s: 핀 선 x%s 밑 (%s; 양 끝 이는 모듈 옆면과 같은 면), 뒤 막대 x0~%s × y%s~%s (뒷벽 밑); 레일 밑 x%s~%s와 기판 구멍 밑은 빔"
         % (f_(h, 1), f_(P["z_eva"][0], 0), f_(P["z_eva"][1], 0), f_(tw, 1), f_(bar[2], 0), " / ".join(f_(c, 1) for c in lines), ", ".join("x%s~%s" % (f_(a_, 2), f_(b_, 2)) for a_, b_ in teeth),
            f_(W_, 1), f_(bar[2], 0), f_(bar[3], 0), f_(gap[0], 2), f_(gap[1], 2)),
         "모듈을 핀 선과 뒷벽으로만 받친다. 위에서 누르는 정하중이 쓰임(패드가 윗판을 밑에서 밀어 레일이 들림)과 같은 레일 휨을 만든다")
    # dead load 6 x F on the chord the test loads, for the rail-support cases of model_v4.rail_keel_root
    ch6 = list(DL_["keys"])
    assert "E" in ch6 and "F" in ch6, ch6
    lv = {n: LAY["levers"][n] for n in ch6}
    cases = {}
    for lab, kr in (("fins", "fins"), ("rigid", None), ("fins_span", "fins_span"), ("hatch", "hatch")):
        q = M.plate_loads(dict(P, keel_rail=kr), G, DL_["F"], DL_["F"], LAY["fins"], lv, KEYS, chords=True)["chord"]
        st_ = q["k_eq_seats"]
        cases[lab] = dict(seats={n: st_[n] for n in ch6}, EF=max(st_["E"], st_["F"]), EF_key="E" if st_["E"] >= st_["F"] else "F")
    assert abs(cases["fins"]["EF"] - DL_["EF_max"]) < 5e-4, (cases["fins"]["EF"], DL_["EF_max"])
    # the rail simply supported between the neighbouring fin lines: its weakest chord (metrics keel_rail EF_fins_span) is not the tested one
    q = M.plate_loads(dict(P, keel_rail="fins_span"), G, DL_["F"], DL_["F"], LAY["fins"], LAY["levers"], KEYS, chords=True)["chord"]
    ss_weak = dict(keys=list(q["k_eq_keys"]), EF=max(v_ for n_, v_ in q["k_eq_seats"].items() if n_ in ("E", "F")))
    assert abs(ss_weak["EF"] - (KR_["EF_fins_span"] or 0.0)) < 5e-4, (ss_weak, KR_["EF_fins_span"])
    return dict(h=h, tw=tw, lines=lines, teeth=teeth, bar=bar, gap=gap, keys=ch6, F=DL_["F"], kg=6 * DL_["F"] / 9.81, limit=DL_["limit"], cases=cases, fins_span_weakest=ss_weak,
                k_rigid=KR_["k_chord_rigid"], k_fins_span=KR_["k_chord_fins_span"], k_model=KR_["k_chord"])


# ============================================================================ export: SCAD -> STL -> PNG, checks
def read_stl(path):
    """ASCII or binary STL -> (n, 3, 3) triangles (no trimesh in the venv)."""
    raw = open(path, "rb").read()
    if raw[:5] == b"solid" and b"facet" in raw[:400]:
        v = [list(map(float, ln.split()[1:4])) for ln in raw.decode().splitlines() if ln.strip().startswith("vertex")]
        return np.array(v).reshape(-1, 3, 3)
    n = int(np.frombuffer(raw[80:84], dtype="<u4")[0])
    rec = np.frombuffer(raw[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return rec["v"].astype(float)


class Mesh:
    def __init__(self, path):
        T = read_stl(path)
        self.T = T
        cr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(cr, axis=1)
        self.area_faces = ln / 2
        self.face_normals = cr / np.maximum(ln, 1e-12)[:, None]
        self.triangles_center = T.mean(axis=1)
        allv = T.reshape(-1, 3)
        self.bounds = np.array([allv.min(axis=0), allv.max(axis=0)])
        self.volume = float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0)
        key = np.round(allv / 1e-4).astype(np.int64)
        _, idx = np.unique(key, axis=0, return_inverse=True)
        idx = idx.reshape(-1, 3)
        e = np.sort(np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]]), axis=1)
        _, cnt = np.unique(e, axis=0, return_counts=True)
        self.is_watertight = bool((cnt == 2).all())


def render_png(view, png, title):
    """two perspective views of the STL (front-right and back-left, from above) side by side, with the part title."""
    from PIL import Image, ImageDraw, ImageFont
    ims = []
    for k, eye in enumerate(("220,-320,260", "-220,320,260")):
        tmp = png[:-4] + "_%d.png" % k
        subprocess.run([OPENSCAD, "--backend=manifold", "--render", "-o", tmp, "--imgsize=800,640", "--viewall", "--autocenter",
                        "--colorscheme=Tomorrow", "--projection=p", "--camera=%s,0,0,0" % eye, view], capture_output=True, text=True)
        ims.append(Image.open(tmp).convert("RGB"))
        os.remove(tmp)
    W = sum(i.width for i in ims)
    out = Image.new("RGB", (W, ims[0].height + 40), (248, 248, 248))
    x = 0
    for i in ims:
        out.paste(i, (x, 40))
        x += i.width
    d = ImageDraw.Draw(out)
    font = None
    for fp in ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"):
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 22)
                break
            except Exception:
                pass
    d.text((12, 8), title, fill=(30, 30, 30), font=font)
    d.line([(ims[0].width, 40), (ims[0].width, out.height)], fill=(200, 200, 200), width=2)
    out.save(png)


def export_all(only=None):
    for p in PARTS:
        if only and p["id"] not in only:
            continue
        scad = os.path.join(OUT_SCAD, p["id"] + ".scad")
        stl = os.path.join(OUT_STL, p["id"] + ".stl")
        png = os.path.join(OUT_PNG, p["id"] + ".png")
        with open(scad, "w") as fh:
            fh.write("// Toccata stage-0 %s - %s (generated by make_stage0.py; print orientation, z = build direction)\n" % (p["id"], p["name_ko"]))
            fh.write(p["scad"])
        r = subprocess.run([OPENSCAD, "--backend=manifold", "--export-format", "binstl", "-o", stl, scad], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(stl):
            raise RuntimeError("openscad failed for %s:\n%s" % (p["id"], r.stderr[-2000:]))
        mesh = Mesh(stl)
        bb = mesh.bounds
        ext_ = bb[1] - bb[0]
        # overhang check: downward faces above the bed; 'bridge' = flat (|nz| > 0.99), 'overhang' = steeper than 45 deg
        n = mesh.face_normals
        c = mesh.triangles_center
        a = mesh.area_faces
        above = c[:, 2] > bb[0][2] + 0.25
        bridge = above & (n[:, 2] < -0.99)
        over = above & (n[:, 2] < -0.74) & ~bridge
        p.update(stl=os.path.relpath(stl, HERE), png=os.path.relpath(png, HERE), bbox=[r_(v, 2) for v in ext_],
                 volume_cm3=r_(mesh.volume / 1000.0, 2), mass_g_solid=r_(mesh.volume * RHO, 1), watertight=bool(mesh.is_watertight),
                 bridge_area_mm2=r_(float(a[bridge].sum()), 1), overhang45_area_mm2=r_(float(a[over].sum()), 1),
                 fits_bed=bool(ext_[0] <= BED[0] and ext_[1] <= BED[1] and ext_[2] <= BED[2]))
        # render the STL itself
        view = os.path.join(OUT_SCAD, "_view_" + p["id"] + ".scad")
        with open(view, "w") as fh:
            fh.write('color([0.93,0.62,0.22]) import("%s");\n' % stl)
        render_png(view, png, p["id"] + "  " + p["name_ko"])
        os.remove(view)


# ============================================================================ documents: geometry JSON, Korean procedure, CSV template
def model_version():
    try:
        first = open(os.path.join(MODEL_DIR, "DESIGN.md"), encoding="utf-8").readline()
        import re
        m = re.search(r"r4\.\d+", first)
        return m.group(0) if m else "?"
    except Exception:
        return "?"


def write_docs(R):
    ver = model_version()
    S = MET["sens"]
    W, B = MET["white"], MET["black"]
    c1, c2, c3, c4, c5, c6, c7, c8 = (R[k] for k in ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"))
    c9, c10, c11, c12, c13, c15 = (R[k] for k in ("C09", "C10", "C11", "C12", "C13", "C15"))
    adj = MET["adjust"]
    t50w, t50b = MET["dyn"]["white"]["release"]["t50"], MET["dyn"]["black"]["release"]["t50"]
    t100w, t100b = MET["dyn"]["white"]["release"]["t100"], MET["dyn"]["black"]["release"]["t100"]
    rep_min = 13.3
    t50_lim = 1000.0 / (2 * rep_min)
    pmap = {p["id"]: p for p in PARTS}
    km = c3["fe"]["module"]
    ks1 = c3["fe"]["S1 (x0.2~84.3, C~F)"]
    kd_pass = km["k_dial"] * c3["ratio_single"]
    ch = c3["chord_vs_dz"]
    r_need = {dz: P["seat_k_chord_req"] / v["k_chord"] for dz, v in ch.items()}
    e_pass, e_des = P["pad_e_pass"], P["pad_e"]
    fr_rows = c1["table"]
    sg = lambda nm, col, k: S[nm][col][k]

    # ---------------------------------------------------------------- tests (number -> dict) for JSON + CSV
    T = {}

    def test(no, title, parts, pass_ko, design, outcomes, rows):
        T[str(no)] = dict(no=no, title_ko=title, parts=parts, pass_ko=pass_ko, design=design, outcomes=outcomes, csv=rows)

    test(1, "패드 반발 (계 실효 e)", ["C01a", "C01b", "C01c", "C01d"], "e ≤ %s (설계 %s)" % (f_(e_pass, 2), f_(e_des, 2)),
         dict(pad_e=e_des, pad_e_pass=e_pass, w0_rad_s=r_(c1["w0"] * 1000, 1)),
         [dict(range="e ≤ %s" % f_(e_pass, 2), verdict="통과", param="pad_e = 측정값", note="모델 'pad e 0.07': 들림 %s / %s, ABUSE %s / %s, 연타 %s / %s Hz"
               % tuple(f_(sg("pad e 0.07 (pass line)", c, k), n) for k, n in (("lift_play", 3), ("lift_abuse", 3), ("rep", 1)) for c in ("white", "black"))),
          dict(range="%s < e ≤ 0.10" % f_(e_pass, 2), verdict="조건부", param="pad_e = 측정값, 다른 합격선(E·앞 펠트)은 공칭이어야", note="모델 'pad e 0.10': 백 들림 %s, 흑 ABUSE %s, 연타 %s / %s Hz; 최악 조합이면 백 PLAY 들림 %s > 0.20"
               % (f_(sg("pad e 0.10", "white", "lift_play"), 3), f_(sg("pad e 0.10", "black", "lift_abuse"), 3), f_(sg("pad e 0.10", "white", "rep"), 1),
                  f_(sg("pad e 0.10", "black", "rep"), 1), f_(sg("worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)", "white", "lift_play"), 3))),
          dict(range="0.10 < e ≤ 0.15", verdict="대안 ①", param="대안 ①: gap_us_w −0.40 → −0.60, gap_us_b −0.45 → −0.65 (PET 심 2장 더), pad_E 1.4", note="모델 대안 ①(e 0.15): 들림 %s / %s, ABUSE %s / %s, 연타 %s / %s Hz"
               % tuple(f_(sg("fallback 1: pad e 0.15, gap -0.60/-0.65, E 1.4", c, k), n) for k, n in (("lift_play", 3), ("lift_abuse", 3), ("rep", 1)) for c in ("white", "black"))),
          dict(range="e > 0.15", verdict="불합격", param="다른 패드 후보 (② 점탄성 PU, ③ 부틸 1T 덧댐)", note="모델 e 0.25: 백 들림 %s, 백 ABUSE 키퍼 %s(닿음), 흑 ABUSE %s"
               % (f_(sg("pad e 0.25", "white", "lift_play"), 3), f_(sg("pad e 0.25", "white", "keep_abuse"), 2), f_(sg("pad e 0.25", "black", "lift_abuse"), 3)))],
         [("1", "C01", "마찰 감쇠 (반 흔들림당)", "deg", "", "", ""), ("1", "C01", "쉼 읽음 θ_h", "deg", "0", "-0.5", "0.5")]
         + [("1", "C01", "θ0 %d° → 되튐 θr" % t, "deg", "", "", "") for t in (90, 120, 150)]
         + [("1", "C01", "실효 e (θ0 150°, 마찰 보정)", "-", f_(e_des, 2), "", f_(e_pass, 2))])
    test(2, "패드 강성", ["C02a", "C02b"], "25 %% 압축(1.75 mm)에서 %s~%s N (E 0.7~1.4 MPa, 설계 %s N)" % (f_(c2["F25_band"][0], 1), f_(c2["F25_band"][1], 1), f_(c2["F25"], 1)),
         dict(pad_E=P["pad_E"], pad_epsD=P["pad_epsD"], sigma25=r_(c2["sig25"], 3)),
         [dict(range="E < 0.7", param="두꺼운/단단한 등급", note="모델 'pad E 0.7': 흑 ABUSE 들림 %s" % f_(sg("pad E 0.7 (softer foam)", "black", "lift_abuse"), 3)),
          dict(range="0.7 ≤ E ≤ 1.4", param="pad_E = 측정값", note="통과"),
          dict(range="E > 1.4", param="pad_E = 측정값, 윗판 하중 다시", note="모델 'pad E 1.4': 백 업스톱 힘 %s N (설계 %s)" % (f_(sg("pad E 1.4 (firmer foam)", "white", "up_play"), 1), f_(MET["upstop_peaks"]["play"][0], 1)))],
         [("2", "C02", "눌림 %s mm에서 힘" % f_(r["d"], 2), "N", f_(r["F10"], 1), f_(r["F07"], 1), f_(r["F14"], 1)) for r in c2["rows"]]
         + [("2", "C02", "맞춘 E", "MPa", f_(P["pad_E"], 1), "0.7", "1.4")])
    test(3, "윗판 패드 자리 처짐 (굽힘 띠 E + 프레임 조각)", ["C03a", "C03b", "C03c", "C03d", "C03e"],
         "띠 E_eff ≥ %s MPa (화음 자리 460 N/mm), 프레임 C# 자리 다이얼 점 처짐 ≤ %s mm @ 98 N" % (f_(M.E_PETG * c3["ratio_chord"], 0), f_(98.0 / kd_pass, 3)),
         dict(E_PETG=M.E_PETG, seat_k_min=MET["seat"]["k_min"], seat_k_chord=r_(MET["seat"]["k_chord"], 1), k_strip=r_(c3["k_beam"], 1)),
         [dict(range="r = E_eff/%.0f ≥ %s" % (M.E_PETG, f_(c3["ratio_chord"], 3)), param="(선택) E_PETG = 1950 r", note="통과"),
          dict(range="%s ≤ r < %s" % (f_(r_need[0.6], 3), f_(c3["ratio_chord"], 3)), param="윗판 채움 100 % 다시; 그래도면 plate_t +0.6 (z_top 73.4)", note="FE 화음 자리 %s → %s N/mm" % (f_(ch[0.0]["k_chord"], 0), f_(ch[0.6]["k_chord"], 0))),
          dict(range="%s ≤ r < %s" % (f_(r_need[1.2], 3), f_(r_need[0.6], 3)), param="plate_t +1.2 (z_top 74.0 = 높이 목표 끝)", note="FE 화음 자리 %s N/mm" % f_(ch[1.2]["k_chord"], 0)),
          dict(range="r < %s" % f_(r_need[1.2], 3), param="재료·설정 바꿈 (다른 PETG, 온도)", note="두께만으로 못 채움; 한 건반 자리 선 r %s" % f_(c3["ratio_single"], 3))],
         [("3", "C03a", "띠 두께 t (3곳 평균)", "mm", f_(c3["t"], 2), "", ""), ("3", "C03a", "띠 폭 b", "mm", f_(c3["b"], 2), "", ""),
          ("3", "C03a", "띠 강성 k (2→20 N 기울기)", "N/mm", f_(c3["k_beam"], 1), f_(c3["k_beam"] * c3["ratio_chord"], 1), ""),
          ("3", "C03a", "E_eff", "MPa", f_(M.E_PETG, 0), f_(M.E_PETG * c3["ratio_chord"], 0), ""),
          ("3", "프레임", "C# 자리 다이얼 점 처짐 @49 N", "mm", f_(49.0 / km["k_dial"], 3), "", f_(49.0 / kd_pass, 3)),
          ("3", "프레임", "C# 자리 다이얼 점 처짐 @98 N", "mm", f_(98.0 / km["k_dial"], 3), "", f_(98.0 / kd_pass, 3))])
    h15 = c15["h"][1.5]
    test(4, "앞 펠트 반발", ["C15a"], "e ≤ 0.22 (1.5 m/s 낙하 %s mm에서 되튐 ≤ %s mm)" % (f_(h15, 1), f_(0.22 ** 2 * h15, 2)),
         dict(front_e=P["front_e"], ball_g=r_(c15["m"], 1), e_model_ball=r_(c15["e_model_ball"], 3)),
         [dict(range="e ≤ 0.22", param="front_e = 측정값", note="통과"),
          dict(range="0.22 < e ≤ 0.28", param="front_e = 측정값 후 run_all", note="모델 'front felt e 0.28'만: 들림 %s / %s, ABUSE %s / %s (모두 통과)"
               % (f_(sg("front felt e 0.28", "white", "lift_play"), 3), f_(sg("front felt e 0.28", "black", "lift_play"), 3), f_(sg("front felt e 0.28", "white", "lift_abuse"), 3), f_(sg("front felt e 0.28", "black", "lift_abuse"), 3))),
          dict(range="e > 0.28", param="펠트 밑 PU 1T → 2T (앞 레일을 1.0 낮게: w_felt_line)", note="§17 불합격 조치")],
         [("4", "C15", "1.5 m/s 되튐 높이", "mm", f_(P["front_e"] ** 2 * h15, 2), "", f_(0.22 ** 2 * h15, 2)), ("4", "C15", "e (1.5 m/s)", "-", f_(P["front_e"], 2), "", "0.22"),
          ("4", "C15", "1.0 m/s 되튐 높이", "mm", f_(P["front_e"] ** 2 * c15["h"][1.0], 2), "", "")])
    test(5, "스냅 노치 반지름", ["C04a", "C04b", "C04c"], "빠짐 힘 1~2 N (백·흑 모두), 끼운 채 DW 변화 ≤ 0.5 g",
         dict(notch_R=P["notch_R"], cloth=P["cloth"], F_model=MET["snap"]["F_model"], w_white=r_(c4["w_white"], 2), w_black=r_(c4["w_black"], 2)),
         [dict(range="R%s" % (("%.3f" % r["R"]).rstrip("0")), param="notch_R = %s; lift_play = %s, lift_popout = %s, lift_abuse = %s" % (
             ("%.3f" % r["R"]).rstrip("0"), f_(r["touch"], 3), f_(r["popout"], 3), f_(r["popout"] / 2, 3)),
               note="추정 빠짐 백 %s / 흑 %s N" % (f_(r["F_est_white"], 2), f_(r["F_est_white"] * c4["w_black"] / c4["w_white"], 2))) for r in c4["rows"]],
         [("5", "C04%s" % ("a" if col == "백" else "b"), "%s R%s 빠짐 힘 (2~5회 평균)" % (col, ("%.3f" % r["R"]).rstrip("0")), "N",
           f_(r["F_est_white"] * (1.0 if col == "백" else c4["w_black"] / c4["w_white"]), 2), "1.0", "2.0") for col in ("백", "흑") for r in c4["rows"]])
    test(6, "가이드 탭 천", ["C05a", "C05b"], "10원 동전 올린 홈 쿠폰이 저절로 내려감(끌림 ≤ 0.02 N), 옆 놀음 < 0.1 (PET 심 0.1이 안 들어감)",
         dict(tab_w_b=P["tab_w_b"], tab_w=P["tab_w"], cloth=P["tab_cloth"], tab_play=P["tab_play"], guide_drag=P["guide_drag"]),
         [dict(range="헐거움 (심 들어감)", param="천 한 단계 두껍게 또는 날 +0.1 (tab_w_b / tab_w)", note="tab_play = 잰 놀음/2 로 틈 검사 다시"),
          dict(range="걸림", param="천 한 단계 얇게 또는 날 −0.1", note=""), dict(range="둘 다 통과", param="tab_w_b·tab_w·tab_cloth = 고른 값", note="")],
         [("6", "C05", "흑 날 %s + 천 %s: 내려감 / 심" % (f_(w, 1), f_(cl, 1)), "O/X", "", "", "") for w in c5["black"] for cl in (0.4, 0.5, 0.6)]
         + [("6", "C05", "백 날 %s + 천 0.5: 내려감 / 심" % f_(w, 1), "O/X", "", "", "") for w in c5["white"]])
    test(7, "DW / UW (조립 건반)", ["C14a"], "DW 47~55 g (y13 / 흑 앞+10), 립 y0 ≥ 47 g, UW ≥ 20 g",
         dict(DW_w=r_(W["DW"], 1), DW_b=r_(B["DW"], 1), UW_w=r_(W["UW"], 1), UW_b=r_(B["UW"], 1), DW_lip=r_(W["DW_lip"], 1)),
         [dict(range="DW 높음/낮음", param="퍼티 강철 앞 1 g = +%s / +%s g, 캡스턴 1/8회전 = +%s / +%s g" % (f_(adj["white_putty_steel"], 2), f_(adj["black_putty_steel"], 2), f_(adj["white_0.125"]["dDW"], 2), f_(adj["black_0.125"]["dDW"], 2)), note="")],
         [("7", "C14", "%s DW" % c_, "g", f_(v, 1), "47", "55") for c_, v in (("백", W["DW"]), ("흑", B["DW"]))]
         + [("7", "C14", "%s UW" % c_, "g", f_(v, 1), "20", "") for c_, v in (("백", W["UW"]), ("흑", B["UW"]))] + [("7", "C14", "백 립 y0 DW", "g", f_(W["DW_lip"], 1), "47", "")])
    st = c6["states"]
    test(8, "비틀림 보조 스프링", ["C06a", "C06b", "C14a"], "k_t %s ± 15 %%, 자유각 %s ± 5°, 쉼 %s / 바닥 %s N·mm ± 15 %%" % (f_(c6["kt"], 1), f_(c6["free"], 0), f_(st["rest"]["T"], 2), f_(st["bottom"]["T"], 2)),
         dict(spring_kt=c6["kt"], spring_free_deg=c6["free"], k_coil=r_(c6["k_coil"], 2), groove_arm=r_(c6["arm"], 2)),
         [dict(range="자유각 벗어남 Δ°", param="spring_free_deg = 측정값", note="쉼 토크 %s N·mm/° → DW·UW %s g/° (캡스턴 1/8회전 %s g로 맞춤)"
               % (f_(c6["kt"] * math.pi / 180, 3), f_(c6["DW_per_T"] * c6["kt"] * math.pi / 180, 2), f_(adj["white_0.125"]["dDW"], 2))),
          dict(range="덜 감김(자유각이 +쪽으로) > 5°", param="뒷벽 홈 바닥을 더 깊게는 %s mm까지만(뒷벽 살 %s 남김) = +%s°; 더 모자라면 `spring_notch_rot`(가둠 홈을 CW로 Δ° 돌림, 캐리어 다시 출력) 또는 스프링 다시 주문"
               % (f_(c6["deeper_max"], 1), f_(c6["skin_min"], 1), f_(c6["deeper_max"] / (c6["arm"] * math.pi / 180), 1)), note="홈 바닥 %s mm/°; 한쪽만 됨 — 벽은 y%s까지"
               % (f_(c6["arm"] * math.pi / 180, 3), f_(P["rear_wall"][1], 0))),
          dict(range="더 감김(자유각이 −쪽으로) > 5°", param="뒷벽 홈 바닥을 얕게(앞으로) %s mm/° 옮김 (보스 %s 안에서 자유)" % (f_(c6["arm"] * math.pi / 180, 3), f_(P["spring_groove"][4], 1)), note=""),
          dict(range="쉼 토크가 모델보다 10 % 넘게 낮고 짧은 다리가 홈 바깥 면에서 떨어져 보임", param="가둠 홈 폭 재기(0.5 날·틈새 게이지): 넓으면 `spring_notch` 놀음 = 잰 폭 − 0.5 후 run_all", note="홈 +0.3 넓으면 쉼 −%s N·mm (모델)" % f_(c6["tol_p30"], 2)),
          dict(range="k_t 벗어남", param="spring_kt = 측정값 후 run_all (연타·복귀)", note="")],
         [("8", "C06", "추 %s g → b" % f_(g_, 0), "deg", "", "", "") for g_ in (10, 15, 20, 25, 30, 35, 40)]
         + [("8", "C06", "k_t (맞춤)", "N·mm/rad", f_(c6["kt"], 2), f_(c6["kt"] * 0.85, 2), f_(c6["kt"] * 1.15, 2)),
            ("8", "C06", "자유각 (맞춤)", "deg", f_(c6["free"], 1), f_(c6["free"] - 5, 1), f_(c6["free"] + 5, 1))])
    test(9, "복귀 시간 (조립 건반)", ["-"], "t50 ≤ %s ms, 끝까지 ≤ 60 ms, 스프링 다리 10/10 다시 걸림" % f_(t50_lim, 1),
         dict(t50_w=t50w, t50_b=t50b, t100_w=t100w, t100_b=t100b),
         [dict(range="느림", param="spring_free_deg −10° (감는 각 +10°)", note="§17")], [("9", "-", "%s t50 / t100" % c_, "ms", "%s / %s" % (f_(a, 1), f_(b, 1)), "", "%s / 60" % f_(t50_lim, 1)) for c_, a, b in (("백", t50w, t100w), ("흑", t50b, t100b))])
    test(10, "노치 들림·입술 천 마모 (조립)", ["-"], "PLAY ≤ 0.20, ABUSE ≤ 0.40, 빠지지 않음", dict(), [],
         [("10", "-", "들림 PLAY / ABUSE", "mm", "%s / %s" % (f_(MET["metrics"]["key_lift_play_mm"], 3), f_(MET["metrics"]["key_lift_abuse_mm"], 3)), "", "0.20 / 0.40")])
    # r4.5 circuit 2nd (item 9): the filter window = SCH-03 note 9 (re-arm within ghost_win of the note-on, first re-press within
    # ghost_rep_max of the note-on); the firmware logs the re-press time of a suspect key so that the window can be checked
    gw_, grm_ = P["ghost_win"], P.get("ghost_rep_max", 500.0)
    test(11, "유령 (조립, 펌웨어 거름)", ["-"], "거름(0.3 m/s, 25 %%, 재무장 %s ms · 다시 눌림 %s ms, 모두 note-on부터) 켜면 재타건 없음; 기록된 유령 다시 눌림 ≤ %s ms" % (f_(gw_, 0), f_(grm_, 0), f_(grm_, 0)),
         dict(ghost_win=gw_, ghost_rep_max=grm_),
         [dict(range="유령 다시 눌림 > %s ms" % f_(grm_, 0), param="ghost_rep_max = 가장 늦은 것 + 100 ms (펌웨어 상수, SCH-03 주 9)", note="대가: 그만큼 느린 진짜 재타건이 더 버려짐")],
         [("11", "-", "거름 켠 재타건 수", "회", "0", "", "0"), ("11", "-", "유령 다시 눌림 시각 (note-on부터, 가장 늦은 것)", "ms", "-", "", "%s" % f_(grm_, 0))])
    test(12, "패드 바 놀음·잎 크리프", ["C10a", "C10b", "C10c"], "40 °C 1주 뒤 잎 힘 ≥ 처음의 50 % (0.3 눌림), 바 상하 놀음 없음",
         dict(bar_leaf=list(P["bar_leaf"]), F_leaf_g=r_(c10["grams"], 1), sigma=r_(c10["sig"], 1), sigma_tol=r_(c10["sig_tol"], 1)),
         [dict(range="남은 힘 ≥ 50 %", param="그대로", note="바 무게의 3배 이상"), dict(range="17~50 %", param="bar_leaf 두께 0.6 → 0.8 권장", note="힘 ×2.37, 응력 ×1.33"),
          dict(range="< 17 %", param="bar_leaf (0.8, 1.6, 8, 0.5) 또는 손 맞춤", note="바가 0.3 처져 딸깍 (83 % 풀림 = 모델 한계)")],
         [("12", "C10", "잎 %d 처음 힘 (0.3)" % k, "g", f_(c10["grams"], 1), "", "") for k in (1, 2, 3)]
         + [("12", "C10", "잎 %d 1주 뒤 힘 (0.3)" % k, "g", "", f_(c10["grams"] * 0.5, 1), "") for k in (1, 2, 3)])
    IN45 = MET.get("r45", {}).get("insert", {})
    ILO = MET.get("r45", {}).get("insert_lo", {})
    test(13, "스프링 넣기 (조립, r4.5 고침 2 가둠 홈)", ["C16a", "C06b"],
         "짧은 다리 끝부터 가둠 홈(폭 %s)을 따라 밀어 넣으면 코일이 주머니에 앉고 짧은 다리가 홈 끝까지 들어감 (3/3); 긴 다리가 코일 +x 끝; 레버 −31°~+18°에서 긴 다리가 창 면에 끌리지 않음" % f_(c6["notch"]["width"], 2),
         dict(short_leg_gap=r_(IN45.get("short_A", [0.0])[0], 3), groove_w=r_(c6["notch"]["width"], 2), alpha_s=r_(c6["notch"]["alpha_s"], 2), slot_deg=r_(c6["notch"]["slot_deg"], 1)),
         [dict(range="짧은 다리가 홈에 안 들어감 (홈이 좁게 나옴)", param="0.5 날로 홈을 다듬음; 3개 다 그러면 `spring_notch` 놀음 +0.1 후 run_all", note="모델 넣는 길 짧은 다리 틈 %s (홈 0.10 / 0.15 좁게 %s / %s)" % (f_(IN45.get("short_A", [0.0])[0], 3), f_(ILO.get("-0.1", ILO.get(-0.1, 0.0)), 3), f_(ILO.get("-0.15", ILO.get(-0.15, 0.0)), 3))),
          dict(range="짧은 다리가 홈에 맞지 않음(각이 틀림)", param="스프링을 뒤집어 넣음 — 긴 다리가 +x 끝이어야 함", note="오른쪽 감기"),
          dict(range="긴 다리가 창 면에 끌림", param="spring_window 면 +2.6 → +2.8", note="")],
         [("13", "C16a", "넣기 %d회 (캐리어 3개)" % k_, "O/X", "", "", "") for k_ in (1, 2, 3)])
    ws = adj["white_shim"], adj["black_shim"]
    test(14, "종이 띠 시점 (조립)", ["-"], "백 0.75 N 미끄러짐·1.04 N 물림, 흑 0.96 N·1.43 N", dict(), [dict(range="먼저 물림 / 늦게 물림", param="PET 심 빼기 / 넣기", note="한 장 = 레버 %s° / %s°" % (f_(ws[0]["db0_deg"], 2), f_(ws[1]["db0_deg"], 2)))],
         [("14", "-", "백 0.75 / 1.04 N", "O/X", "", "", ""), ("14", "-", "흑 0.96 / 1.43 N", "O/X", "", "", "")])
    test(15, "층간 강도 (핀-윗판 이음)", ["C12a"], "층간 인장 강도 ≥ %s MPa (= s_rare × 2) → 끊김 ≥ %s N" % (f_(2 * c12["s_rare"], 0), f_(2 * c12["s_rare"] * c12["A"], 0)),
         dict(A_mm2=c12["A"], s_single=r_(c12["s_single"], 2), s_chord=r_(c12["s_chord"], 2), s_abuse_chord=r_(c12["s_abuse"], 2), s_cyc=P["s_cyc"], s_rare=P["s_rare"]),
         [dict(range="≥ 30 MPa", param="그대로", note="통과"),
          dict(range="%s~30 MPa" % f_(2 * c12["s_abuse"], 1), param="s_rare = 강도/2, s_cyc = 강도/6 로 모델 한계 바꿈; 이음 모서리 살 3", note="ABUSE 화음 %s MPa가 강도의 절반 아래" % f_(c12["s_abuse"], 1)),
          dict(range="< %s MPa" % f_(2 * c12["s_abuse"], 1), param="출력 온도↑·팬↓, 이음 모서리 살 3 mm", note="불합격")],
         [("15", "C12", "시편 %d 끊김 무게" % k, "kg", "", f_(2 * c12["s_rare"] * c12["A"] / 9.80665, 2), "") for k in (1, 2, 3)] + [("15", "C12", "층간 강도 (평균)", "MPa", "", "30", "")])
    test(16, "윗판 브리지 출력", ["C11a"], "서포트 없이 핀 사이 %s 브리지 처짐 ≤ 0.3, 레일 립이 섬, 1.5T 띠가 레일에 들어감" % f_(c11["span"], 2), dict(span=r_(c11["span"], 2)),
         [dict(range="처짐 > 0.3 또는 립 늘어짐", param="트리 서포트 유지 (§15, 모듈 88 g)", note="")],
         [("16", "C11", "처짐 (%s)" % y_, "mm", "0", "", "0.3") for y_ in ("앞 홈 y150", "패드 구간 y176", "뒤 y200")] + [("16", "C11", "1.5T 띠 넣기", "O/X", "", "", "")])
    test(17, "느낌", ["-"], "받아들일 만함 (y90 %s g, 흑 1 N 바닥 %s mm)" % (f_(W["DW_y90"], 0), f_(MET["heights"]["held_pad_front_b"], 2)), dict(), [dict(range="흑 바닥이 무름", param="gap_us_b −0.45 → −0.30", note="§17")], [("17", "-", "느낌", "O/X", "", "", "")])
    test(18, "90° 세움", ["-"], "모든 건반 제자리 (앞 높이 ±0.2)", dict(), [dict(range="빠짐", param="노치 R 한 단계 작게", note="")], [("18", "-", "세웠다 눕힘", "O/X", "", "", "")])
    test(19, "USB-C 케이블 맞춤", ["C13a"], "몰드 ≤ %s × %s × %s (게이지 통과), 실제 프레임에서 홈 가장자리와 1 mm 이상" % (f_(c13["w"], 1), f_(c13["h"], 1), f_(c13["L"], 0)),
         dict(usb_x=list(P["usb_x"]), usb_z=list(P["usb_z"]), slot=list(c13["slot"]), clear=c13["clear"]),
         [dict(range="게이지 안 들어감", param="몰드 폭 ≤ 11 케이블로 (회로 인터페이스는 고정)", note="")], [("19", "C13", "케이블 몰드 폭×높이×길이", "mm", "12.5×7.6×25", "", "")])
    c16_ = R["C16"]
    Bp, Ba = c16_["B_play"], c16_["B_abuse"]
    sp_ = [v_ for v_ in c16_["spread_play"] if v_]
    Fpop = [Bp * 1.0 / v_ for v_ in sp_] if sp_ else []
    test(20, "강철 블록 유지 (캐리어 스냅 + 접착)", ["C16a", "C16b", "C03c"],
         "MS 폴리머로 접착한 캐리어: 5 ↔ 45 °C 3번 뒤 %s N(ABUSE %s N의 1.5배)을 10초씩 3번 눌러 강철이 캐리어에 대해 0.05 mm 넘게 움직이지 않음, 흰 줄·들뜸 없음; 1 m 낙하 3번 뒤 그대로" % (f_(1.5 * Ba, 0), f_(Ba, 1)),
         dict(B_play=r_(Bp, 1), B_abuse=r_(Ba, 1), bond_area=c16_["bond_area"], snap_pop_model=[r_(v_, 0) for v_ in Fpop]),
         [dict(range="스냅만(접착 없이) 빠지는 힘 ≥ %s N" % f_(1.5 * Ba, 0), verdict="모델이 비관적", param="carrier_wall_plate 받침 조건(clamped) — 접착은 그대로 두는 것을 권함(립 뿌리 응력은 여전히 한계 위)", note=""),
          dict(range="접착 캐리어가 움직임 / 흰 줄 / 온도 순환 뒤 들뜸", verdict="불합격", param="접착면 사포질·탈지 다시, PETG용 프라이머 + 같은 MS 폴리머, 다른 MS 폴리머 제품; 단단한 2액형 에폭시는 쓰지 않음(열팽창 차이, DESIGN 1e 고침 2b); 그래도 안 되면 옆벽 0.7 → 1.0(레버 폭 11.2, 배치 다시)", note="")],
         [("20", "C16", "스냅만: 강철이 아래로 빠지는 힘 (캐리어 1)", "N", " ~ ".join(f_(v_, 0) for v_ in sorted(Fpop)) if Fpop else "", "", ""),
          ("20", "C16", "스냅만: %s N에서 립 선 벌어짐 (한쪽)" % f_(Bp, 0), "mm", " / ".join(f_(v_, 2) for v_ in sorted(sp_)) if sp_ else "", "", ""),
          ("20", "C16", "접착: MS 폴리머 굳힘 시간", "h", "24", "24", ""),
          ("20", "C16", "접착: 5 °C ↔ 45 °C 순환 (각 2 h 이상)", "번", "3", "", "3"),
          ("20", "C16", "접착: %s N × 10 s × 3 뒤 강철 움직임 (캐리어 2·3)" % f_(1.5 * Ba, 0), "mm", "0", "", "0.05"),
          ("20", "C16", "접착: 1 m 낙하 3번 (나무 바닥, 세 방향)", "O/X", "", "", "")])
    # r4.5 fix 3 (verifier major): test 21 loads the module on the C17a comb (service direction, see c17)
    c17_ = R["C17"]
    cs_ = c17_["cases"]
    lim_ = c17_["limit"]
    test(21, "첫 모듈 정하중 (조립 모듈, 쓰임과 같은 레일 휨)", ["C17a"],
         "C17a 위에서 %s 여섯 자리 × %s N: E·F 자리 처짐 ≤ %s mm (= %s N ÷ %s N/mm)" % ("-".join(c17_["keys"]), f_(c17_["F"], 0), f_(lim_, 2), f_(c17_["F"], 0), f_(P["seat_k_chord_req"], 0)),
         dict(keys=c17_["keys"], F=c17_["F"], EF_model=r_(cs_["fins"]["EF"], 3), EF_rail_rigid=r_(cs_["rigid"]["EF"], 3), EF_rail_hatch_clamped=r_(cs_["hatch"]["EF"], 3),
              EF_rail_simply_supported=r_(cs_["fins_span"]["EF"], 3), limit=r_(lim_, 3), k_chord_req=P["seat_k_chord_req"]),
         [dict(range="E·F ≤ %s" % f_(lim_, 2), verdict="통과", param="", note="모델 %s (레일 단단 %s, 이웃 핀 선 사이 단순 지지 %s)" % (f_(cs_["fins"]["EF"], 3), f_(cs_["rigid"]["EF"], 3), f_(cs_["fins_span"]["EF"], 3))),
          dict(range="E·F > %s" % f_(lim_, 2), verdict="불합격", param="run_all 화음 자리 강성 k_ch = %s N ÷ 잰 처짐으로 화음 자리 동역학(들림 0.20, 키퍼, 유령) 다시" % f_(c17_["F"], 0), note=""),
          dict(range="그래도 불합격", verdict="불합격", param="회로 세션과 리본 차선 위 레일 높이를 다시 정함", note="킬 z%s과 핀 앞끝 y%s은 건반 F와 1.3 한계" % (f_(P["fin_keel"][2], 1), f_(M.keel_front(P), 1)))],
         [("21", "C17a", "%s 자리 처짐 (0 → %s kg → 0, 3회 평균)" % (n_, f_(c17_["kg"], 1)), "mm", f_(cs_["fins"]["seats"][n_], 3), "", f_(lim_, 2)) for n_ in ("E", "F")]
         + [("21", "C17a", "레일 밑·기판 구멍 밑이 책상에서 뜸 (종이 띠가 지나감)", "O/X", "", "", "")])
    test("P", "밸런스 핀 압입 (모델 밖 제안)", ["C07a", "C07b"], "돌출 %s ± 0.1 (핀 꼭대기 z%s), 누름 힘 15~80 N (제안), 흔들림 없음" % (f_(c7["prot"], 2), f_(c7["z_pin_top"], 2)),
         dict(pin_top=c7["z_pin_top"], rail_top=c7["z_rail"], prot=r_(c7["prot"], 2), yaw_pin=P["yaw_pin"]),
         [dict(range="고른 구멍 Ø", param="새 값 P['pin_hole_print'] (모델에 없음 → 추가), 레일 구멍으로 geometry에 내보냄", note="")],
         [("P", "C07", "Ø%s 누름 힘 최대" % f_(d, 2), "N", "", "15", "80") for d in c7["ds"]] + [("P", "C07", "Ø%s 돌출" % f_(d, 2), "mm", f_(c7["prot"], 2), f_(c7["prot"] - 0.1, 2), f_(c7["prot"] + 0.1, 2)) for d in c7["ds"]])
    test("C", "캡스턴 너트 트랩 (모델 밖 제안)", ["C08a", "C14a"], "너트가 뒤집어도 안 빠짐, 돌림 토크 3~40 N·mm (제안), 8×1/8회전 = 0.50 ± 0.05 mm, 20번 조정 뒤 토크 ≥ 3 N·mm",
         dict(eighth=c8["eighth"], dDW_w=adj["white_0.125"]["dDW"], dDW_b=adj["black_0.125"]["dDW"], dcap_w=adj["white_0.125"]["dcap"]),
         [dict(range="고른 변형 (홈 폭 / 구멍 Ø)", param="건반 빔 너트 홈 폭·자가 잠김 구멍 Ø를 모델 key_body 'nut trap'에 넣음 (지금 5.6 / Ø2.8)", note="")],
         [("C", "C08", "변형 %d 토크 (처음 / 20번 뒤)" % (k + 1), "N·mm", "", "3", "40") for k in range(5)])
    test("T", "펠트·천 두께 (모델 밖 기준, 조정 환산)", ["C09a", "C09b"], "공칭 ±10 % (제안); 벗어나면 아래 환산표로 조정량",
         dict((nm, v) for nm, v, *_ in c9["felts"]), [], [("T", "C09", "%s 두께 (빈 / 강철1 / 강철2)" % nm, "mm", f_(v, 2), f_(v * 0.9, 2), f_(v * 1.1, 2)) for nm, v, *_ in c9["felts"]])

    # ---------------------------------------------------------------- geometry JSON
    geo = dict(
        generator="make_stage0.py", model_dir=MODEL_DIR, model_version=ver, created=time.strftime("%Y-%m-%d %H:%M"),
        bed_mm=BED, units="mm, g, N", rounding="half away from zero at the shown precision (r_ helper)",
        parts=[{k: v for k, v in p.items() if k != "scad"} for p in PARTS],
        tests=T,
        analysis=dict(
            C01=dict(arm_mass_g=r_(c1["arm_mass"], 2), arm_rcg=r_(c1["arm_rcg"], 2), arm_I=r_(c1["arm_I"], 0), lever_model=dict((k, (r_(v, 2) if isinstance(v, float) else [r_(x, 2) for x in v])) for k, v in c1["lever_model"].items()),
                     play_omega_rad_s=r_(c1["w0"] * 1000, 2), release_table=c1["table"], free_swing_limit_deg=c1["th_free_lim"], release_clearance_min=r_(c1["rel_clear"], 2),
                     rig_rotation_deg=r_(math.degrees(c1["psi"]), 2), contact_angle_b0_deg=r_(math.degrees(c1["b0"]), 3), pad_face_centre_rig=[r_(v, 2) for v in c1["pad_face_centre"]],
                     pad_normal_rig=[r_(v, 4) for v in c1["pad_normal"]], rod_len=c1["rod_len"], x_layout=c1["x"], e_model_check=r_(c1["e_check"], 3)),
            C02=dict(area=c2["area"], h=c2["h"], sigma25=r_(c2["sig25"], 4), F25=r_(c2["F25"], 2), F25_band=[r_(v, 2) for v in c2["F25_band"]], table=c2["rows"]),
            C03=dict(fe_C_sharp={k: {kk: r_(vv, 4) for kk, vv in v.items()} for k, v in c3["fe"].items()}, x_seat=r_(c3["x_seat"], 3), x_dial=r_(c3["x_dial"], 3), y_load=r_(c3["y_load"], 3),
                     chord_k_vs_plate_dz={str(k): {kk: r_(vv, 1) for kk, vv in v.items()} for k, v in ch.items()}, r_needed_vs_dz={str(k): r_(v, 3) for k, v in r_need.items()},
                     strip=dict(t=c3["t"], b=c3["b"], span=c3["span"], k_pred=r_(c3["k_beam"], 2)), ratio_single=r_(c3["ratio_single"], 3), ratio_chord=r_(c3["ratio_chord"], 3)),
            C04=dict(rows=[{k: r_(v, 4) for k, v in r.items()} for r in c4["rows"]], w_white=r_(c4["w_white"], 3), w_black=r_(c4["w_black"], 3),
                     note="pull-off estimate = model F 1.99 N (R2.55, white) x (equator interference ratio)^1.5 (cloth law exponent), black x width ratio"),
            C06=dict(groove_arm=r_(c6["arm"], 3), arm=r_(c6["arm"], 3), tip=[r_(v, 3) for v in c6["tip"]], drum_R=c6["Rd"], rows=[{k: r_(v, 3) for k, v in r.items()} for r in c6["rows"]], DW_per_Nmm=r_(c6["DW_per_T"], 3),
                     deeper_max=r_(c6["deeper_max"], 2), skin_min=c6["skin_min"], groove_x_leg=r_(c6["x_leg"], 2), notch={k: (r_(v, 3) if isinstance(v, float) else v) for k, v in c6["notch"].items()},
                     tol_p30_dT=r_(c6["tol_p30"], 3)),
            C07={k: (r_(v, 3) if isinstance(v, float) else v) for k, v in c7.items()},
            C10={k: r_(v, 4) for k, v in c10.items()},
            C11=dict(bay=c11["bay"], span=r_(c11["span"], 3), x=c11["x"], zcut=c11["zcut"], tags=c11["tags"]),
            C12={k: r_(v, 3) for k, v in c12.items()}, C13={k: (r_(v, 3) if isinstance(v, float) else v) for k, v in c13.items()},
            C15=dict(d=c15["d"], m=r_(c15["m"], 2), e_model_ball=r_(c15["e_model_ball"], 3), h={str(k): r_(v, 2) for k, v in c15["h"].items()}),
            C17=dict(h=R["C17"]["h"], tooth_w=R["C17"]["tw"], fin_lines=[r_(v, 3) for v in R["C17"]["lines"]], teeth=[[r_(a_, 3), r_(b_, 3)] for a_, b_ in R["C17"]["teeth"]],
                     rear_bar=[r_(v, 2) for v in R["C17"]["bar"]], rail_free=[r_(v, 3) for v in R["C17"]["gap"]], keys=R["C17"]["keys"], F=R["C17"]["F"], kg=r_(R["C17"]["kg"], 2),
                     limit=r_(R["C17"]["limit"], 4), k_chord_play=dict(model=r_(R["C17"]["k_model"], 1), rigid=r_(R["C17"]["k_rigid"], 1), fins_span=r_(R["C17"]["k_fins_span"], 1)),
                     dead_seats={lab_: dict(seats={n_: r_(v_, 6) for n_, v_ in q_["seats"].items()}, EF=r_(q_["EF"], 6), EF_key=q_["EF_key"]) for lab_, q_ in R["C17"]["cases"].items()},
                     fins_span_weakest=dict(keys=R["C17"]["fins_span_weakest"]["keys"], EF=r_(R["C17"]["fins_span_weakest"]["EF"], 6)),
                     note="rail-support cases of model_v4.rail_keel_root: fins = model (continuous over the fin lines), rigid = keel_rail None, "
                          "fins_span = simply supported between the neighbouring fin lines only, hatch = clamped at the hatch edges; dead load on the tested chord only")),
        model_params_used=sorted(set(PARAMS_USED)))
    json.dump(geo, open(os.path.join(HERE, "stage0_geometry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---------------------------------------------------------------- CSV template
    import csv
    with open(os.path.join(HERE, "stage0_results_template.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["시험", "시편", "항목", "단위", "설계(모델)", "합격 하한", "합격 상한", "1회", "2회", "3회", "평균", "판정(O/X)", "메모"])
        order = [1, 2, 3, 20, 16, 15, 5, 6, "P", "C", "T", 4, 8, 12, 19, 7, 9, 10, 11, 13, 14, 17, 18, 21]
        for no in order:
            for row in T[str(no)]["csv"]:
                w.writerow(list(row) + ["", "", "", "", "", ""])
    write_md(R, T, ver)
    return T


PARAMS_USED = ["L", "K", "y_steel_front", "steel_len", "steel_h", "steel_w", "z_c", "felt_c", "pad_y", "pad_w", "pad_h", "pad_felt", "pad_foam", "pad_E",
               "pad_epsD", "pad_e", "pad_e_pass", "gap_us_w", "gap_us_b", "v_play", "seat_k_req", "seat_k_chord_req", "plate_t", "notch_R", "cloth",
               "rod_k", "block_lift", "block_y", "block_top", "block_step_z", "lift_play", "lift_abuse", "lift_popout", "snap_F", "snap_F_min", "tab_w",
               "tab_w_b", "tab_cloth", "rib_in", "b_wall_in", "tab_play", "guide_drag", "spring_kt", "spring_free_deg", "spring_groove", "spring_leg",
               "spring_d", "spring_pocket", "spring_slot", "hub_R", "rail_y", "rail_front_y", "z_floor", "pin_d", "pin_len", "pin_engage", "yaw_pin",
               "beam_w", "beam_z", "beam_z_cap", "cap_k", "cap_dk", "felt_front", "rest_felt", "keeper_felt", "bar_leaf", "bar_leaf_bump",
               "bar_leaf_gap", "pad_bar_t", "fin_t", "s_cyc", "s_rare", "usb_x", "usb_y", "usb_z", "usb_clear", "front_e", "ledge_y0", "rear_wall",
               "fin_y", "wall"]


def write_md(R, T, ver):
    c1, c2, c3, c4, c5, c6, c7, c8 = (R[k] for k in ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"))
    c9, c10, c11, c12, c13, c15 = (R[k] for k in ("C09", "C10", "C11", "C12", "C13", "C15"))
    S = MET["sens"]
    MM = MET["metrics"]
    W, B = MET["white"], MET["black"]
    adj = MET["adjust"]
    pm = {p["id"]: p for p in PARTS}
    km = c3["fe"]["module"]
    ks1 = c3["fe"]["S1 (x0.2~84.3, C~F)"]
    kd_pass = km["k_dial"] * c3["ratio_single"]
    ch = c3["chord_vs_dz"]
    r_need = {dz: P["seat_k_chord_req"] / v["k_chord"] for dz, v in ch.items()}
    L = []
    a = L.append
    t50w, t50b = MET["dyn"]["white"]["release"]["t50"], MET["dyn"]["black"]["release"]["t50"]
    t100w, t100b = MET["dyn"]["white"]["release"]["t100"], MET["dyn"]["black"]["release"]["t100"]
    ang = lambda x: f_(x, 1)

    a("# Toccata W1+ %s — 단계 0 시험 키트 (출력 시편·지그와 절차)" % ver)
    a("")
    a("%s · `make_stage0.py`가 단일 모델(`%s/model_v4.py`, `metrics.json`)에서 만들었다. 모든 합격선·설계값·민감도는 모델 값이고, 모델에 없는 값은 **제안**이라고 적었다. 단위 mm·g·N. 좌표는 DESIGN.md와 같다(z0 책상, y0 백건 립 앞끝). 숫자는 보인 자리에서 반올림(0.5는 0에서 멀어지는 쪽)."
      % (time.strftime("%Y-%m-%d"), os.path.basename(MODEL_DIR.rstrip("/"))))
    a("")
    a("여기서는 아무도 물리 시험을 할 수 없다. 이 키트는 DESIGN.md 17장의 21개 시험(+ 모델 밖 3개: 밸런스 핀 압입 P, 캡스턴 너트 트랩 C, 펠트·천 두께 T)을 **집에 있는 도구로** 할 수 있게 시편(STL), 재는 법, 합격 숫자, 그리고 결과마다 모델의 어느 값을 얼마나 바꾸는지를 모았다. 결과는 `stage0_results_template.csv`에 적는다.")
    a("")
    a("## 0. 한눈에")
    a("")
    a("| 순서 | 시험 | 시편 | 합격 | 설계(모델) | 떨어지면 바꿀 모델 값 |")
    a("|---|---|---|---|---|---|")
    rows0 = [
        ("1", 1, "C01a~d", "e ≤ %s" % f_(P["pad_e_pass"], 2), "e %s" % f_(P["pad_e"], 2), "`pad_e`; e > 0.10이면 `gap_us_w/_b` −0.2 + `pad_E` 1.4"),
        ("2", 2, "C02a·b", "25 %% 압축 %s~%s N" % (f_(c2["F25_band"][0], 1), f_(c2["F25_band"][1], 1)), "%s N (E 1.0)" % f_(c2["F25"], 1), "`pad_E`"),
        ("3", 3, "C03a~e", "띠 E ≥ %s MPa; 프레임 C# 처짐 ≤ %s mm @98 N" % (f_(M.E_PETG * c3["ratio_chord"], 0), f_(98 / kd_pass, 3)), "E %s; %s mm" % (f_(M.E_PETG, 0), f_(98 / km["k_dial"], 3)), "윗판 채움 100 %, `plate_t` +0.6~1.2"),
        ("4", 20, "C16a·b", "접착: %s N에 움직임 ≤ 0.05; 스냅만 빠짐 힘 기록" % f_(1.5 * R["C16"]["B_abuse"], 0), "스냅만 빠짐 %s N" % " ~ ".join(f_(R["C16"]["B_play"] / v_, 0) for v_ in sorted((v_ for v_ in R["C16"]["spread_play"] if v_), reverse=True)), "접착 필수 (r4.4 고침 2)"),
        ("4b", 16, "C11a", "처짐 ≤ 0.3", "-", "서포트 유지 (§15)"),
        ("5", 15, "C12a", "층간 ≥ 30 MPa", "이음 최대 %s MPa" % f_(c12["s_abuse"], 1), "`s_rare`·`s_cyc`, 이음 살 3"),
        ("6", 5, "C04a~c", "빠짐 1~2 N", "1.99 N (R2.55)", "`notch_R` + `lift_play/_abuse/_popout`"),
        ("7", 6, "C05a·b", "끌림 ≤ 0.02 N, 놀음 < 0.1", "놀음 %s" % f_(P["tab_play"], 2), "`tab_w_b`·`tab_w`·`tab_cloth`·`tab_play`"),
        ("8", "P", "C07a·b", "돌출 %s ± 0.1, 누름 15~80 N (제안)" % f_(c7["prot"], 2), "-", "새 `pin_hole_print`"),
        ("9", "C", "C08a", "토크 3~40 N·mm (제안)", "1/8회전 0.0625 mm", "너트 홈 폭·잠김 구멍 Ø"),
        ("10", "T", "C09a·b", "공칭 ±10 % (제안)", "표 T", "펀칭·심·캡스턴 환산"),
        ("11", 4, "C15a", "e ≤ 0.22", "0.20", "`front_e`, PU 2T"),
        ("12", 8, "C06a·b", "k_t %s ± 15 %%, 자유각 %s ± 5°" % (f_(c6["kt"], 1), f_(c6["free"], 0)), "쉼 %s N·mm" % f_(c6["states"]["rest"]["T"], 2), "`spring_kt`·`spring_free_deg`"),
        ("13", 12, "C10a~c", "1주 40 °C 뒤 잎 힘 ≥ 50 %", "%s g" % f_(c10["grams"], 1), "`bar_leaf` 두께 0.8"),
        ("14", 19, "C13a", "몰드 ≤ 12.5 × 7.6 × 25", "-", "(회로 고정값, 케이블만 바꿈)"),
        ("15~", "7·9·10·11·13·14·17·18·21", "조립 모듈 (21: C17a)", "17장 그대로", "-", "각 절 참조"),
    ]
    for o, no, sp, ps, ds, ch_ in rows0:
        a("| %s | %s %s | %s | %s | %s | %s |" % (o, no, T[str(no)]["title_ko"] if str(no) in T else "", sp, ps, ds, ch_))
    a("")
    a("**가장 먼저 1번(패드 반발)을 한다** — 모든 동역학 결과가 e 0.06 가정 위에 있다(DESIGN §18). 3번의 띠 시험은 화음 자리(설계 %s, 합격선 %s N/mm; 레일 휨은 조립 시험 21)에 여유가 %s %%밖에 없다는 것을 처음으로 확인한다: 출력한 윗판의 실효 E가 모델 %s MPa의 %s %% 아래이면 화음 자리가 합격선 아래로 내려간다."
      % (f_(MET["seat"]["k_chord"], 0), f_(P["seat_k_chord_req"], 0), f_(100 * (1 - c3["ratio_chord"]), 1), f_(M.E_PETG, 0), f_(100 * c3["ratio_chord"], 1)))
    a("")
    a("## 1. 준비물")
    a("")
    a("| 도구·재료 | 쓰는 곳 | 비고 |")
    a("|---|---|---|")
    for r in (("정밀 저울 0.1 g (최대 200~500 g)", "2 무게, 5 쿠폰, 8 추, 12 잎 힘, C 토크", "추 컵·쿠폰 무게"),
              ("주방 저울 1 g (최대 5 kg, 가능하면 10 kg)", "3 굽힘·프레임 처짐, 5 빠짐 힘, P 누름 힘", "손으로 누르는 힘 = 저울 읽음"),
              ("디지털 버니어 캘리퍼스 0.01 (깊이 막대 있는 것)", "2, 3, 12, 16, P, T", ""),
              ("다이얼 게이지 0.01 mm, 줄기 Ø8, 행정 10", "3, 21", "약 1.5만 원; 스탠드는 C03d·e 출력"),
              ("휴대폰 슬로 모션 240 fps", "1, 4, 8, 9, 10", "삼각대(또는 책 더미)로 눈금판에 수직"),
              ("PET 심 0.1 (OHP 필름 6×12.2), 영수증 종이 0.05", "1, 6, 12, 14", "부품 목록에 있음"),
              ("Ø4 SUS 봉 토막 24 ×1, 40 ×1, 18 ×1, 45 ×2", "C01, C04c, C06, C12", "레버 봉 4 m에서 자름 (C06 18: r4.5 고침 2 북 받침 +2)"),
              ("강철 블록 SS400 9×19×40 ×2", "1, 3, 9, 12, T", "레버용과 같은 것"),
              ("Ø19.05 (3/4\") 강철 공 1개 (%s g)" % f_(c15["m"], 1), "4", "베어링 볼"),
              ("대나무 꼬치 Ø3, 가는 실(재봉실/낚싯줄), 순간접착제, 흑연 가루", "1, 4, 5, 8, 15", ""),
              ("M3×12 나사 2개, M3 너트·M3×6 버튼헤드 5개씩", "C03d·e, C08", "캡스턴 재고"),
              ("물병·쌀 봉지(무게를 주방 저울로 잰 것), 10 L 양동이, 수건", "2, 15", ""),
              ("곧은 판재(합판 약 200 × 80, 두께 12 이상), 6×12 받침 6개, 물통·아령 %s kg" % f_(R["C17"]["kg"], 1), "21", "C17a 받침 빗 위에서"),
              ("40 °C를 1주 유지할 곳 (요구르트 제조기·식품 건조기·온열 매트 + 온도계)", "12", "여름 차 안은 60 °C를 넘어 안 됨"),
              ("후보 패드: ① 미세셀 우레탄 6T + 펠트 1T, ② 점탄성 PU 시트, ③ ①+부틸 1T", "1, 2", "6×12로 자름")):
        a("| %s | %s | %s |" % r)
    a("")
    a("## 2. 출력")
    a("")
    a("모든 부품은 256×256 베드, PETG, **서포트 없이** 출력한다(C11a는 서포트 없는 브리지 자체가 시험). STL은 이미 출력 방향(z = 쌓는 방향)으로 놓여 있다. ‘생산과 같은 설정’이라고 적은 쿠폰은 그 부품(프레임·건반·패드 바)을 뽑을 슬라이서 설정을 그대로 써야 결과가 모델로 옮겨진다.")
    a("")
    a("| ID | 이름 | 시험 | 방향 | 설정 | 크기 (mm) | 부피 (cm³) | 브리지 (mm²) |")
    a("|---|---|---|---|---|---|---|---|")
    for p in PARTS:
        a("| %s | %s | %s | %s | %s | %s | %s | %s |" % (p["id"], p["name_ko"], p["test"], p["print_ko"], p["settings"], " × ".join(f_(v, 1) for v in p.get("bbox", [])),
                                                    f_(p.get("volume_cm3", 0), 1), f_(p.get("bridge_area_mm2", 0), 0)))
    a("")
    a("브리지 칸이 0이 아닌 것은 짧은 천장뿐이다: C08a 너트 홈 천장 5.6~5.8, C09a 다리 윗판 26, C09b 강철 자리 9.5, C07b Ø2.4 구멍 천장, C15a 창 윗변 6, C06a 홈 보스. 45°보다 가파른 내민 면은 C03d·e의 가로 M3 구멍(Ø2.7/3.3)과 C15a 꼬치 구멍(Ø3.3)뿐이다. "
      + ("모든 STL은 닫힌 몸(watertight)이다." if all(p.get("watertight") for p in PARTS) else "닫힌 몸(watertight)이 아닌 STL: %s." % ", ".join(p["id"] for p in PARTS if not p.get("watertight"))))
    a("")
    a("공통: Ø3.9로 출력한 봉 구멍(C01a·b·d, C06a)은 Ø4.0 드릴로 뚫는다(모델 S11과 같음). 봉을 끼우는 구멍에는 흑연 가루를 조금 넣는다(모델 레버와 같은 마찰).")
    a("")

    # ------------------------------------------------------------------ test 1
    a("## 3. 시험 절차")
    a("")
    a("### 시험 1 — 패드 반발 (가장 먼저)")
    a("")
    a("**무엇을 재나.** 모델의 `pad_e`는 ‘레버 혼자, 단단한 자리 위의 패드를 PLAY 각속도(건반 앞 1.5 m/s → 레버 %s rad/s)로 칠 때의 실효 반발계수’다(`PadTable.calibrate`). C01은 이것을 그대로 만든다: 모델 레버와 같은 자리(봉 L 기준 y150~190, z33~52)에 강철을 잡은 시험 레버(C01b, 강철 포함 %s g, 무게중심 반지름 %s, 봉 둘레 관성 %s g·mm² — 모델 레버 %s g, %s g·mm²)를 모델의 패드 면 자리에 놓은 패드에 **중력으로** 떨어뜨린다. 받침은 모델 좌표를 %s° 돌려, 패드에 처음 닿는 각(b0 = %s°)에서 레버 무게중심이 봉 바로 아래에 오게 했다. 그래서 닿는 순간이 흔들림의 맨 아래이고, 되튄 높이(각)만 읽으면 e가 나온다."
      % (f_(c1["w0"] * 1000, 1), f_(c1["arm_mass"], 1), f_(c1["arm_rcg"], 2), f_(c1["arm_I"], 0), f_(c1["lever_model"]["m"], 1), f_(c1["lever_model"]["IL"], 0),
         f_(math.degrees(c1["psi"]) % 360, 1), f_(math.degrees(c1["b0"]), 2)))
    a("")
    a("**시편.** C01a 받침(봉 구멍·눈금 θ −20~160°, 2° 눈금·20°마다 숫자·패드 블록), C01b 시험 레버, C01c 패드 받침판(후보마다 1개), C01d 칼라, Ø4 봉 24, 강철 블록 1, 후보 패드(6×12).")
    a("")
    a("**준비.**")
    a("1. C01a·C01b·C01d 구멍을 Ø4.0으로 뚫는다. 봉(24)을 C01a 뒷면에서 밀어 넣는다(뒷면과 같은 면, 보스 앞면에서 14 나옴). 헐거우면 순간접착제.")
    a("2. 강철 블록을 C01b 칸에 옆에서 밀어 넣어 양면을 같게 하고 순간접착제 한 방울로 고정한다. **C01b를 출력할 때 베드에 닿았던 면이 브래킷 쪽**이다(뒤집으면 강철 윗면이 패드 반대쪽을 본다).")
    a("3. 봉에 흑연 가루, C01b를 끼우고(허브가 보스 Ø12에 닿음) C01d로 막는다(축 방향 놀음 1 mm 이하).")
    a("4. 패드(폼 6T + 펠트 1T, 생산과 같은 풀)를 C01c 표시 자리(6×12)에 펠트가 바깥으로 오게 붙인다. C01c를 C01a 패드 블록 홈에 위에서 끝까지 밀어 넣는다.")
    a("5. 받침을 평평한 탁자에 두고 레버가 늘어진 채 패드에 **막 닿는지** 본다: 영수증 종이(0.05)를 강철과 패드 사이에 넣고 당기면 살짝 끌려야 한다. 떨어져 있으면 C01c 뒤에 PET 심(0.1)을 넣고, 눌려 있으면(레버가 패드에 밀려 기울면) C01c 뒷면을 사포질한다. 이때 지침이 가리키는 값 θ_h를 적는다(설계 0°, 모든 읽음에서 뺀다).")
    a("6. 휴대폰을 눈금판에 수직으로 30 cm 앞에 고정한다(240 fps).")
    a("")
    a("**마찰 보정 (패드 없이).** C01c를 뺀다. 레버를 θ0 = 6°에서 놓는다(**7°를 넘기지 말 것** — 반대쪽 %s°에서 패드 블록과 1 mm 안으로 들어온다). 영상에서 연속한 꼭짓점 각 a0, a1, a2, a3, a4(양쪽 번갈아)를 읽는다. 반 흔들림마다 줄어드는 각 Δ = (a0 − a4)/4 (라디안으로 바꿈), 마찰 비 f = Δ/2. 봉 마찰 0.28 N·mm(μ 0.25)이면 Δ ≈ %s°."
      % (f_(c1["th_free_lim"], 0), f_(math.degrees(2 * 0.28 / c1["mgr"]), 1)))
    a("")
    a("**반발.** C01c(패드)를 다시 넣는다. θ0 = 90°, 120°, 150°에서 각각 3번 놓는다(강철 쪽 틀을 손가락으로 잡았다 뗌; 150°는 거의 거꾸로 선 자세). 영상에서 실제 놓은 각 θ0(움직이기 시작한 첫 프레임)과 **첫 되튐의 꼭짓점 각 θr**을 읽는다(둘 다 θ_h를 뺀 값).")
    a("")
    a("**계산.** e = √{[(1 − cos θr) + f·θr] / [(1 − cos θ0) − f·θ0]} (f 항의 각은 라디안). 레버 질량·무게중심은 식에서 지워진다. 판정 값은 θ0 150°(모델 PLAY 각속도의 %s %%)의 평균이다. 90° → 150°로 e가 커지면(속도 의존) 150° 값을 직선으로 PLAY 속도(100 %%)까지 늘려 쓴다."
      % f_(100 * c1["table"][3]["omega_ratio_play"], 0))
    a("")
    a("마찰이 없을 때 e별 되튐 각 θr (도):")
    a("")
    es = ("0.04", "0.05", "0.06", "0.07", "0.08", "0.10", "0.12", "0.15", "0.20", "0.25", "0.30")
    a("| θ0 | 충돌 각속도 (rad/s, PLAY 대비) | " + " | ".join("e " + e for e in es) + " |")
    a("|---|---|" + "---|" * len(es))
    for r in c1["table"]:
        a("| %d° | %s (%s %%) | " % (r["theta0"], f_(r["omega"], 1), f_(100 * r["omega_ratio_play"], 0)) + " | ".join(ang(r["e" + e]) for e in es) + " |")
    a("")
    a("**합격: e ≤ %s** (설계 %s). 모델 확인: 패드 표가 설계 e에서 되돌린 값 %s."
      % (f_(P["pad_e_pass"], 2), f_(P["pad_e"], 2), f_(c1["e_check"], 3)))
    a("")
    a("**결과에 따라** (모델 `metrics.json` `sens`):")
    a("")
    a("| 측정 e | 판정 | 모델에서 바꿀 것 | 모델 결과 (백 / 흑) |")
    a("|---|---|---|---|")
    for o in T["1"]["outcomes"]:
        a("| %s | %s | %s | %s |" % (o["range"], o["verdict"], o["param"], o["note"]))
    a("")
    a("민감도(한 가지만 바꿈, 백 / 흑): e 0.06 → 0.07 → 0.10 → 0.15 → 0.25에서 PLAY 들림 %s, 흑 ABUSE 들림 %s, 백 0.45 N 유령 재무장 %s (모두 펌웨어가 거름), 연타 백 %s Hz."
      % (" / ".join(f_(S[k]["white"]["lift_play"], 3) for k in ("seat stiffest key", "pad e 0.07 (pass line)", "pad e 0.10", "pad e 0.15", "pad e 0.25")),
         " / ".join(f_(S[k]["black"]["lift_abuse"], 3) for k in ("seat stiffest key", "pad e 0.07 (pass line)", "pad e 0.10", "pad e 0.15", "pad e 0.25")),
         " / ".join(f_(S[k]["white"]["ghost045"], 2) for k in ("seat stiffest key", "pad e 0.07 (pass line)", "pad e 0.10", "pad e 0.15", "pad e 0.25")),
         " / ".join(f_(S[k]["white"]["rep"], 1) for k in ("seat stiffest key", "pad e 0.07 (pass line)", "pad e 0.10", "pad e 0.15", "pad e 0.25"))))
    a("")
    a("참고: DESIGN D11의 ‘캡 모양 60 g 추를 2.5 m/s로 떨어뜨림’은 17장(레버를 PLAY 속도로 휘두름)과 다르다. 모델의 `pad_e` 정의는 17장 쪽이므로 이 키트는 C01을 기준 방법으로 한다(D11 문구는 다음 개정에서 17장에 맞출 것).")
    a("")
    a("| 기록 | θ0 90° | θ0 120° | θ0 150° |")
    a("|---|---|---|---|")
    a("| θr 1 / 2 / 3회 (°) |  |  |  |")
    a("| e (마찰 보정) |  |  |  |")
    a("")

    # ------------------------------------------------------------------ test 2
    a("### 시험 2 — 패드 강성")
    a("")
    a("**모델.** 폼 법칙 σ = E·ε / (1 − ε/ε_D), E %s MPa(펠트 면 포함), ε_D %s, 패드 %s×%s×%s. 25 %% 압축(1.75 mm)에서 σ %s MPa = %s N."
      % (f_(P["pad_E"], 1), f_(P["pad_epsD"], 1), f_(P["pad_w"], 0), f_(P["pad_y"][1] - P["pad_y"][0], 0), f_(c2["h"], 0), f_(c2["sig25"], 3), f_(c2["F25"], 1)))
    a("")
    a("**방법.** C02a 바탕 자리(6.4×12.4×1)에 패드를 펠트가 위로 가게 놓고 C02b 누름 막대를 통에 넣는다. C02b 무게 m_p를 잰다. 버니어 깊이 막대를 C02b 모서리 Ø4.2 구멍으로 넣어 C02a 바탕 윗면까지의 깊이 D0를 잰다. 추(주방 저울로 잰 쌀 봉지·물병) 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0 / 3.5 kg을 받침판 가운데에 차례로 올리고, 30초 기다린 뒤 D를 잰다. 눌림 d = D0 − D, 힘 F = (추 + m_p)·9.81/1000 N. 마지막에 추를 모두 내리고 1분 뒤 D를 다시 잰다(영구 눌림).")
    a("")
    a("| 눌림 d (mm) | ε | F (N), E 0.7 | E 1.0 (설계) | E 1.4 |")
    a("|---|---|---|---|---|")
    for r in c2["rows"]:
        a("| %s | %s | %s | %s | %s |" % (f_(r["d"], 2), f_(r["eps"], 2), f_(r["F07"], 1), f_(r["F10"], 1), f_(r["F14"], 1)))
    a("")
    a("**계산.** d = 1.75에서의 F를 이웃 두 점으로 보간 → σ25 = F/72 MPa → E = σ25 × (1 − 0.25/%s)/0.25 = %s × σ25. **합격: E 0.7~1.4 MPa (F25 %s~%s N).**"
      % (f_(P["pad_epsD"], 1), f_((1 - 0.25 / P["pad_epsD"]) / 0.25, 3), f_(c2["F25_band"][0], 1), f_(c2["F25_band"][1], 1)))
    a("")
    for o in T["2"]["outcomes"]:
        a("- %s → %s" % (o["range"], o["param"]) + (" (%s)" % o["note"] if o["note"] else ""))
    a("")

    # ------------------------------------------------------------------ test 3
    a("### 시험 3 — 윗판 패드 자리 처짐")
    a("")
    a("모델의 자리 강성은 윗판 그릴리지 FE(`plate_fe`, E_PETG %s MPa, 판 두께 = z_top %s − 밑면)에서 나온다. 모든 강성이 E에 비례하므로, 출력한 윗판의 **실효 E**를 재면 모델의 자리 강성이 얼마나 줄어드는지 곧바로 안다: 한 건반 자리 %s·r, 6건반 화음 자리 %s·r N/mm (r = E_eff / %s)."
      % (f_(M.E_PETG, 0), f_(G["z_top"], 1), f_(MET["seat"]["k_min"], 0), f_(MET["seat"]["k_chord"], 0), f_(M.E_PETG, 0)))
    a("")
    a("**3a. 굽힘 띠 (C03a~d) — 먼저.** C03a는 **윗판을 뽑을 설정 그대로**(벽·윗/아랫면 층·채움) 뽑는다. 두께 t·폭 b를 세 곳에서 잰다.")
    a("1. 주방 저울 위에 C03b(날 간격 %s)를 놓고 띠를 가운데에 걸친다. 띠 가운데에 C03c(누름 코, 날이 아래)를 얹는다. C03d 스탠드를 같은 저울판 위에 세우고 다이얼 게이지를 줄기로 물려 **끝을 C03c 가운데 Ø4 구멍으로 넣어 띠 윗면에 직접** 0.5 mm쯤 눌러 댄다(누름 코·날 접촉이 읽음에 들어가지 않음). 저울을 0으로 맞춘다." % f_(c3["span"], 0))
    a("2. 손가락으로 C03c의 두 날 쪽 판을 고르게 눌러 저울 204 g(2 N)에서 다이얼을 0으로 맞춘다. 510 / 1020 / 1530 / 2040 g(5 / 10 / 15 / 20 N)에서 다이얼을 읽는다(20 N에서 약 %s mm). 다시 2 N으로 돌아와 0 근처인지 본다. 3번 되풀이하고, k는 세 번 기울기의 평균." % f_(18.0 / c3["k_beam"], 2))
    a("3. k = (20 − 2) N / (δ20 − δ2). 모델 띠(%s×%s, 경간 %s, 굽힘 + 전단)는 k = %s N/mm. E_eff = %s × (k / %s) × (%s / t)³ × (%s / b)."
      % (f_(c3["b"], 0), f_(c3["t"], 1), f_(c3["span"], 0), f_(c3["k_beam"], 1), f_(M.E_PETG, 0), f_(c3["k_beam"], 1), f_(c3["t"], 1), f_(c3["b"], 0)))
    a("")
    a("**합격: r = E_eff / %s ≥ %s (E_eff ≥ %s MPa)** — 화음 자리 합격선 %s N/mm ÷ 모델 %s. 한 건반 자리(%s N/mm)만 보면 r ≥ %s."
      % (f_(M.E_PETG, 0), f_(c3["ratio_chord"], 3), f_(M.E_PETG * c3["ratio_chord"], 0), f_(P["seat_k_chord_req"], 0), f_(MET["seat"]["k_chord"], 1), f_(P["seat_k_req"], 0), f_(c3["ratio_single"], 3)))
    a("")
    a("| r | 모델에서 바꿀 것 | 근거 (윗판 FE, PLAY 패드 힘) |")
    a("|---|---|---|")
    for o in T["3"]["outcomes"]:
        a("| %s | %s | %s |" % (o["range"], o["param"], o["note"]))
    a("")
    a("윗판 두께 민감도(FE): z_top +0 / +0.6 / +1.2 → 화음 자리 %s / %s / %s N/mm, 한 건반 C# %s / %s / %s N/mm. +1.2는 높이 목표 z74의 끝이다. 두께를 바꾸면 z_top·가림판·건반 위 틈이 모두 바뀌므로 `plate_t`를 고치고 run_all을 다시 돌린다."
      % tuple([f_(ch[k]["k_chord"], 0) for k in (0.0, 0.6, 1.2)] + [f_(ch[k]["k_single"], 0) for k in (0.0, 0.6, 1.2)]))
    a("")
    a("**3b. 프레임 조각 (생산 프레임 파일, 프레임이 나온 뒤).** 권장 조각 S1 = 모듈 프레임 x0~85(건반 C~F, 핀 x0.2~1.8 / 40.76~42.56 / 82.42~84.22) — 17장의 ‘D·D#·E 3건반 조각’은 패드 바 두 칸에 걸치고 C# 자리가 없으므로 S1으로 바꿀 것을 권한다(FE로 S1의 C# 자리는 모듈과 %s %% 차이)."
      % f_(100 * abs(ks1["k_dial"] / km["k_dial"] - 1), 1))
    a("1. 프레임(또는 S1)을 바닥으로 주방 저울(가능하면 10 kg) 위에 놓는다. 강철 블록을 9×19 끝면으로 윗판 윗면 C# 자리 위에 세운다: 가운데 x%s, y%s (패드 하중 중심)." % (f_(c3["x_seat"], 1), f_(c3["y_load"], 1)))
    a("2. C03e 스탠드를 저울판 위에 세우고 다이얼 끝을 윗판 윗면 x%s, y%s(블록 오른쪽 가장자리에서 2.5)에 댄다." % (f_(c3["x_dial"], 1), f_(c3["y_load"], 1)))
    a("3. 블록 위를 손가락으로 눌러 5 N(510 g)에서 0, 49 N(5.0 kg)과 98 N(10 kg)에서 읽는다. 3번.")
    a("")
    a("| 하중 | 모델 다이얼 점 처짐 (모듈 / S1) | 합격 (한 건반 830 N/mm 선) | 모델 패드 자리 (6×12 발) |")
    a("|---|---|---|---|")
    for F_ in (49.0, 98.0):
        a("| %s N | %s / %s mm | ≤ %s mm | %s mm |" % (f_(F_, 0), f_(F_ / km["k_dial"], 3), f_(F_ / ks1["k_dial"], 3), f_(F_ / kd_pass, 3), f_(F_ / km["k_seat_pad"], 3)))
    a("")
    a("다이얼 0.01로는 화음 선(r %s)을 가를 수 없다 — 그것은 3a가 한다. 킬 뿌리·밸런스 레일의 휨은 이 띠 시험에 보이지 않으므로 첫 모듈에서 6자리 × 60 N 정하중(조립 시험 21, C17a 받침 빗 위에서 — 쓰임과 같은 레일 휨)으로 E·F 자리 처짐을 잰다." % f_(c3["ratio_chord"], 3))
    a("")

    # ------------------------------------------------------------------ test 16
    a("### 시험 16 — 윗판 브리지 출력 (C11a)")
    a("")
    a("C11a는 모델의 프레임 기둥(`fixed_prisms`)에서 가장 넓은 칸(칸 %d, 핀 사이 %s)을 z%s 위로 잘라낸 것이다: 윗판(밑면 z%s / %s / %s), 두 핀, 뒷벽, 스프링 홈 보스, L 레일과 립. **서포트 없이** 프레임 설정으로 뽑는다."
      % (c11["bay"], f_(c11["span"], 2), f_(c11["zcut"], 0), f_(G["plate_under"][0][1], 1), f_(G["z_seat"], 1), f_(min(z for y, z in G["plate_under"]), 1)))
    a("1. 뒤집어 윗판 윗면을 평평한 곳에 놓는다. 쇠자를 두 바닥 띠 위에 걸치고, 버니어 깊이 막대로 쇠자 윗면에서 윗판 밑면까지 잰다: 핀 옆(핀 면에서 3) 두 곳과 가운데, y150(앞 홈)·y176(패드 구간)·y200(뒤) 세 줄.")
    a("2. 처짐 = 핀 옆 평균 − 가운데. **합격: 모든 줄에서 ≤ 0.3.** 레일 립이 서 있고(늘어짐 ≤ 0.3), 1.5T 띠(패드 바 조각 또는 C01c)가 레일에 끝까지 들어가야 한다.")
    a("3. 불합격이면 트리 서포트를 유지한다(§15, 모듈당 88 g, 88건반 약 0.6 kg).")
    a("")

    # ------------------------------------------------------------------ test 15
    a("### 시험 15 — 층간 강도 (C12a)")
    a("")
    a("핀-윗판 이음은 층을 가로질러 당겨진다. 모델 응력: 한 건반 PLAY %s MPa, 6건반 화음 %s MPa, ABUSE 2.0 m/s 화음 %s MPa. 한계는 r3 기준(s_cyc %s, s_rare %s MPa = 강도의 1/6, 1/2). 17장의 10^6회 반복 인장은 기계 없이는 못 하므로, 이 키트는 **정적 층간 강도**로 한계를 확인한다."
      % (f_(c12["s_single"], 1), f_(c12["s_chord"], 1), f_(c12["s_abuse"], 1), f_(P["s_cyc"], 0), f_(P["s_rare"], 0)))
    a("1. C12a(목 %s×%s, 단면 %s mm²) 3개를 프레임 설정으로 바로 세워 뽑는다. 목의 폭·두께를 잰다." % (f_(2.0, 1), f_(P["fin_t"], 1), f_(c12["A"], 1)))
    a("2. 위 구멍에 Ø4 봉(45)을 끼워 튼튼한 막대(의자 두 개 사이 빗자루)에 건다. 아래 구멍 봉에 줄로 양동이를 단다. 밑에 수건.")
    a("3. 물을 0.5 L씩 30초마다 붓는다. 끊어지면 양동이+물+봉+줄 무게를 잰다. 강도 = 무게(kg) × 9.81 / 단면.")
    a("**합격: ≥ 30 MPa (%s N = %s kg).** 최소 허용 %s MPa (ABUSE 화음 %s MPa가 강도의 절반)."
      % (f_(2 * P["s_rare"] * c12["A"], 0), f_(2 * P["s_rare"] * c12["A"] / 9.80665, 1), f_(2 * c12["s_abuse"], 1), f_(c12["s_abuse"], 1)))
    for o in T["15"]["outcomes"]:
        a("- %s → %s" % (o["range"], o["param"]) + (" (%s)" % o["note"] if o["note"] else ""))
    a("- (선택) 크리프 파단: 한 개에 %s N(%s kg, ABUSE 화음 응력)을 1주 걸어 둔다 — 끊어지면 불합격." % (f_(c12["s_abuse"] * c12["A"], 1), f_(c12["s_abuse"] * c12["A"] / 9.80665, 2)))
    a("")

    # ------------------------------------------------------------------ test 5
    a("### 시험 5 — 스냅 노치 반지름 (C04)")
    a("")
    a("C04a(백 D 블록 폭 %s)와 C04b(흑 C# 블록 폭 %s)는 모델 `notch_block_poly`를 R만 바꿔 뽑은 블록이다(블록 밑면 봉 중심 아래 %s, 계단 z%s). **건반과 같은 방향·설정**(윗면을 베드에, 노치가 출력 맨 위의 열린 홈)으로 뽑아야 출력 오차까지 같다."
      % (f_(c4["w_white"], 2), f_(c4["w_black"], 2), f_(-P["block_lift"], 2), f_(P["block_step_z"], 1)))
    a("1. 각 노치에 부싱 천 0.5T(12 × 9, 생산과 같은 풀)를 붙이고 하루 굳힌다.")
    a("2. C04c에 Ø4 봉(40)을 끼우고 날개에 1 kg 추를 얹어 주방 저울(1 g)에 놓는다. 저울 0.")
    a("3. 쿠폰을 봉에 위에서 눌러 끼운다(딸깍). 두 줄 구멍에 실을 꿰어 가운데를 잡고 2~3초에 걸쳐 곧게 위로 당긴다. 저울 화면을 영상으로 찍어 빠지기 직전 가장 작은 읽음(음수) = 빠짐 힘을 읽는다(g × 0.00981 = N). 5번, 첫 번은 천 길들이기라 빼고 2~5번 평균.")
    a("")
    lp = MM["key_lift_play_mm"]
    a("| R | 쉼 입술 틈 | 입술 닿는 들림 | 빠지는 들림 | 모델 추정 빠짐 백 / 흑 (N) | PLAY 최대 들림(%s) 대비 | 모델 값 |" % f_(lp, 3))
    a("|---|---|---|---|---|---|---|")
    for r in c4["rows"]:
        a("| %s | %s | %s | %s | %s / %s | %s | `notch_R` %s, `lift_play` %s, `lift_popout` %s, `lift_abuse` %s |"
          % (("%.3f" % r["R"]).rstrip("0"), f_(r["clear"], 3), f_(r["touch"], 3), f_(r["popout"], 3), f_(r["F_est_white"], 2), f_(r["F_est_white"] * c4["w_black"] / c4["w_white"], 2),
             "입술이 일함" if r["touch"] < lp else "닿지 않음", ("%.3f" % r["R"]).rstrip("0"), f_(r["touch"], 3), f_(r["popout"], 3), f_(r["popout"] / 2, 3)))
    a("")
    a("추정 빠짐 힘 = 모델 입술 법칙 1.99 N(R2.55, 백) × (적도에서 입술이 넘어야 할 겹침 비)^1.5(천 접촉 법칙 지수), 흑은 블록 폭 비 %s를 곱함 — 쿠폰이 이 추정을 대신한다. **합격: 백·흑 모두 1~2 N.** 모델 추정으로는 R2.55가 백 1.99 / 흑 %s N이라 흑이 1 N 근처다."
      % (f_(c4["w_black"] / c4["w_white"], 3), f_(1.99 * c4["w_black"] / c4["w_white"], 2)))
    a("")
    a("**고르는 법.** 백·흑이 모두 1~2 N인 가장 큰 R. 없으면 흑 ≥ 1 N을 먼저(덜걱 방지), 백은 2.5 N까지 허용. 고른 R을 건반 파일에 넣고 모델에서 `notch_R`와 들림 판정(`lift_play` = 입술 닿는 들림, `lift_popout`, `lift_abuse` = 빠짐/2)을 표대로 바꿔 run_all을 다시 돌린다. **R2.525 이하는 입술 닿는 들림(%s)이 PLAY 최대 들림(%s)보다 작아 판정식(‘PLAY에서 입술이 일하지 않음’)을 다시 세워야 한다.** 천 두께가 0.5에서 Δ만큼 다르면 유효 반지름이 −Δ 바뀐다(표 T): 천 0.025 두꺼움 = R 0.025 작음." % (f_(c4["rows"][1]["touch"], 3), f_(lp, 3)))
    a("")
    a("끼운 채 DW 변화(≤ 0.5 g)는 고른 R로 뽑은 실제 건반에서 시험 7과 함께 잰다.")
    a("")

    # ------------------------------------------------------------------ test 6
    a("### 시험 6 — 가이드 탭 천 (C05)")
    a("")
    a("모델: 흑 탭 %s + 천 %s × 2 = %s가 흑 벽 사이 %s에, 백 탭 %s + 천 × 2 = %s가 갈비 사이 %s에 들어가 옆 놀음 %s(`tab_play`), 끌림 %s N(`guide_drag`)."
      % (f_(P["tab_w_b"], 1), f_(P["tab_cloth"], 1), f_(P["tab_w_b"] + 2 * P["tab_cloth"], 1), f_(P["b_wall_in"], 1), f_(P["tab_w"], 1), f_(P["tab_w"] + 2 * P["tab_cloth"], 1), f_(P["rib_in"], 1), f_(P["tab_play"], 2), f_(P["guide_drag"], 2)))
    a("1. C05a 날(흑 %s, 백 %s) 양면에 천을 붙인다: 흑은 0.4 / 0.5 / 0.6T, 백은 0.5T." % (" / ".join(f_(w, 1) for w in c5["black"]), " / ".join(f_(w, 1) for w in c5["white"])))
    a("2. C05b 홈 쿠폰 하나(100 %% 채움이면 %s g)에 10원 동전(1.22 g)·클립을 붙여 저울로 2.0 g(= 끌림 0.02 N)에 맞춘다. 날 위에 홈을 얹었을 때 **저절로 끝까지 내려가면** 끌림 ≤ 0.02 N." % f_(pm["C05b"]["mass_g_solid"] / 2, 1))
    a("3. 날을 한쪽 벽에 밀고 반대쪽 틈에 PET 심 0.1을 넣어 본다. **들어가지 않으면** 놀음 < 0.1(합격).")
    a("4. 두 조건을 모두 채우는 날 두께·천을 고른다 → `tab_w_b`·`tab_w`·`tab_cloth`, 잰 놀음의 반을 `tab_play`로 넣고 틈 검사(run_all)를 다시 돌린다.")
    a("")

    # ------------------------------------------------------------------ test P
    a("### 시험 P — 밸런스 핀 압입 (모델 밖, 제안 기준)")
    a("")
    a("모델은 핀 꼭대기 z%s ± 0.1(P32)과 핀 x 놀음 %s(`yaw_pin`)만 정하고 레일 구멍 지름은 없다(DESIGN 1c: ‘핀을 압입하는 구멍이 모델에 없을 뿐’). C07a는 레일 낮은 부분(z%s~%s)과 같은 높이에 Ø1.80~2.00 관통 구멍 5개다."
      % (f_(c7["z_pin_top"], 2), f_(P["yaw_pin"], 2), f_(P["z_floor"][1], 0), f_(c7["z_rail"], 1)))
    a("1. C07a를 주방 저울에 놓고 0. 핀을 구멍에 세우고 C07b 게이지(밑면 구멍 깊이 %s)를 씌워 게이지가 레일 윗면에 닿을 때까지 손바닥(또는 바이스)으로 누른다. 저울의 가장 큰 읽음 = 누름 힘." % f_(c7["prot"], 2))
    a("2. 캘리퍼로 돌출(핀 꼭대기 − 레일 윗면)을 잰다: %s ± 0.1." % f_(c7["prot"], 2))
    a("3. 핀 머리를 옆으로 밀어 흔들림이 느껴지는지, 구멍 둘레가 하얗게(응력 백화) 되는지 본다.")
    a("**제안 합격: 누름 힘 15~80 N**(15 N 아래는 청소 때 빠질 수 있음, 80 N 위는 레일이 갈라질 위험), 돌출 %s ± 0.1, 흔들림·백화 없음. 고른 지름을 모델에 새 값 `pin_hole_print`로 넣고 레일 구멍으로 geometry에 내보낸다(지금 geometry는 핀과 레일이 15.2 mm² 겹침)." % f_(c7["prot"], 2))
    a("")

    # ------------------------------------------------------------------ test C
    a("### 시험 C — 캡스턴 너트 트랩 (모델 밖, 제안 기준)")
    a("")
    a("모델(D02): M3 육각 너트를 옆에서 끼우고, 위 Ø2.8 자가 잠김 구멍으로 M3×6 ISO 7380 버튼헤드를 돌려 머리 꼭대기 z%s. 1/8회전 = %s mm → DW 백 +%s / 흑 +%s g, 바닥 캡 높이 +%s / +%s mm. C08a는 빔(폭 %s, z%s~%s)의 너트 홈 폭·잠김 구멍 5가지다: %s."
      % (f_(c8["z_head_top"], 1), f_(c8["eighth"], 4), f_(adj["white_0.125"]["dDW"], 2), f_(adj["black_0.125"]["dDW"], 2), f_(adj["white_0.125"]["dcap"], 2), f_(adj["black_0.125"]["dcap"], 2),
         f_(P["beam_w"], 1), f_(P["beam_z"][0], 1), f_(P["beam_z_cap"], 1), ", ".join("%d) 홈 %s / Ø%s" % (i + 1, f_(w, 1), f_(d, 1)) for i, (w, d) in enumerate(c8["variants"]))))
    a("1. 너트를 옆 홈에 손가락으로 밀어 넣는다. 쿠폰을 뒤집어 두드려도 빠지지 않아야 한다.")
    a("2. 버튼헤드를 바탕 판 쪽(Ø7 구멍)에서 2.0 육각 렌치로 돌려 넣는다. 렌치 긴 팔 끝(축에서 40 mm)에 실로 C14 추 컵을 달고 물을 부어 나사가 돌기 시작하는 무게 m을 잰다: 토크 = m × 0.00981 × 40 N·mm.")
    a("3. 1/8회전씩 8번(1회전) 돌려 머리 높이 변화를 캘리퍼로 잰다: 0.50 ± 0.05 mm. 20번 풀고 조인 뒤 2를 다시 한다.")
    a("**제안 합격: 너트 유지, 토크 3~40 N·mm(처음·20번 뒤 모두)**(3 아래면 진동에 돌 수 있음, 40 위면 2.0 렌치가 헛돌고 PETG 나사산이 뭉개짐). 고른 홈 폭·구멍 지름을 건반 파일과 모델 `key_body` ‘nut trap’에 넣는다.")
    a("")

    # ------------------------------------------------------------------ test T
    a("### 시험 T — 펠트·천 두께 (C09)")
    a("")
    a("모델은 두께를 공칭으로 쓴다. 실제 두께가 다르면 아래 환산으로 조정한다. C09b 발 20×20: 빈 누름판(무게를 잼; 100 %% 채움이면 %s g → %s kPa), 강철 1개(+53.7 g → %s kPa), 강철 2개(→ %s kPa)."
      % (f_(pm["C09b"]["mass_g_solid"], 1), f_(pm["C09b"]["mass_g_solid"] * GN / 400 * 1000, 2), f_((pm["C09b"]["mass_g_solid"] + 53.7) * GN / 400 * 1000, 2), f_((pm["C09b"]["mass_g_solid"] + 107.4) * GN / 400 * 1000, 2)))
    a("1. C09a 자리(22×22)에 시편 없이 C09b를 얹고, 다리 윗면에서 Ø4 구멍으로 깊이 막대를 내려 누름판 끝까지 깊이 D0를 잰다(세 하중 모두).")
    a("2. 시편(22×22)을 놓고 같은 방법으로 D를 잰다. 두께 = D0 − D.")
    a("")
    a("| 재료 | 공칭 (모델) | 두께가 공칭보다 Δ 두꺼우면 | 조정 |")
    a("|---|---|---|---|")
    a("| 앞 펠트 3T (+ PU 1T) | %s | 건반 앞 바닥이 Δ 높아짐 (dip −Δ) | 업스톱 시점: PET 심을 Δ/%s장 더 (한 장 = 건반 앞 %s / %s) |" % (f_(P["felt_front"], 1), f_(adj["white_shim"]["front_mm"], 3), f_(adj["white_shim"]["front_mm"], 2), f_(adj["black_shim"]["front_mm"], 2)))
    a("| 쉼 펠트 1.5T | %s | 건반 앞이 %s × Δ 낮게 쉼 | 종이 펀칭(0.1)을 Δ/0.1장 뺌 (한 장 = 건반 앞 %s) |" % (f_(P["rest_felt"], 1), f_(adj["levelling_front_per_punching"] / 0.1, 2), f_(adj["levelling_front_per_punching"], 2)))
    a("| 키퍼 펠트 2T | %s | 키퍼 틈 %s − Δ | Δ ≤ 0.3이면 그대로 (PLAY 최소 여유 0.34, 합격선 재료 조합) |" % (f_(P["keeper_felt"], 1), f_(P["keeper_gap"], 1)))
    a("| 캡스턴 펠트 2T | %s | 캡스턴을 Δ 올린 것과 같음 → DW +%s × Δ g | 캡스턴을 (Δ/%s) × 1/8회전 조여 머리를 낮춤 |" % (f_(P["felt_c"], 1), f_(adj["white_0.125"]["dDW"] / c8["eighth"], 2), f_(c8["eighth"], 4)))
    a("| 패드 펠트 1T + 폼 6T | %s | 업스톱 틈이 Δ 더 음수 | PET 심 Δ/0.1장 뺌 (한 장 = 레버 %s°) |" % (f_(P["pad_h"], 1), f_(adj["white_shim"]["db0_deg"], 2)))
    a("| 부싱 천 0.5T | %s | 노치 유효 반지름 −Δ, 탭 폭 +2Δ | 시험 5·6을 그 천으로 (R 표에서 Δ만큼 큰 R) |" % f_(P["cloth"], 2))
    a("")
    a("**제안 합격: 강철 1개 하중에서 공칭 ±10 %.** 벗어나도 위 조정으로 맞출 수 있으면 쓴다.")
    a("")

    # ------------------------------------------------------------------ test 4
    a("### 시험 4 — 앞 펠트 반발 (C15a)")
    a("")
    a("모델 앞 펠트: K %s N/mm^1.5, 실효 e %s (30 g, 접촉 법칙은 질량·속도에 무관; Ø19.05 공 %s g로 모델을 돌리면 e %s)."
      % (f_(c15["K"], 0), f_(P["front_e"], 2), f_(c15["m"], 1), f_(c15["e_model_ball"], 3)))
    a("1. PU 1T와 펠트 3T를 Ø19.5 원판으로 잘라 C15a 관 바닥에 PU·펠트 순서로 붙인다(생산 앞 레일과 같은 쌓음).")
    a("2. 꼬치(Ø3)를 위 구멍(공 밑이 펠트 위 %s mm = 1.5 m/s) 또는 아래 구멍(%s mm = 1.0 m/s)에 꿰고 공을 얹는다. 창 옆 1 mm 눈금이 보이게 240 fps로 찍으며 꼬치를 뺀다." % (f_(c15["h"][1.5], 1), f_(c15["h"][1.0], 1)))
    a("3. 공 밑이 펠트에 닿은 높이와 첫 되튐 꼭짓점의 차 h_r을 읽는다. e = √(h_r / h). 5번 평균.")
    a("")
    a("| e | 0.15 | 0.20 (설계) | 0.22 (합격선) | 0.25 | 0.28 |")
    a("|---|---|---|---|---|---|")
    a("| 1.5 m/s 되튐 (mm) | " + " | ".join(f_(e * e * c15["h"][1.5], 2) for e in (0.15, 0.20, 0.22, 0.25, 0.28)) + " |")
    a("| 1.0 m/s 되튐 (mm) | " + " | ".join(f_(e * e * c15["h"][1.0], 2) for e in (0.15, 0.20, 0.22, 0.25, 0.28)) + " |")
    a("")
    for o in T["4"]["outcomes"]:
        a("- %s → %s" % (o["range"], o["param"]) + (" (%s)" % o["note"] if o["note"] else ""))
    a("")

    # ------------------------------------------------------------------ test 8
    a("### 시험 8 — 비틀림 보조 스프링 (C06)")
    a("")
    a("모델(D05, r4.5 미스미 %s): SUS304-WPB d%s, ID %s, 몸통 %s권, 두 다리를 잘라 k_t %s N·mm/rad(코일만 %s), 자유각 %s°(b = 0에서 %s° 감김), 쉼 %s / 바닥 %s N·mm. C06a는 모델 뒷벽 홈(바닥 y%s, 폭 %s, z%s~%s)을 봉 L 기준 같은 자리에, C06b는 모델 레버의 주머니 단면(Ø%s×%s, 짧은 다리 가둠 홈·넣는 슬롯 %s°·긴 다리 창)을 그대로 복제했다 — 코일은 진짜 Ø4 봉 위에 있으므로 코일 뜸(r4.5 검증 major: 한 면 받침이면 코일이 봉으로 밀려 쉼 토크 −46 %%)도 이 시험이 잰다. 긴 다리가 홈 바닥을 미는 팔은 %s mm."
      % (P["spring_cat"]["part"], f_(P["spring_d"], 2), f_(P["spring_ID"], 1), f_(P["spring_n"], 2), f_(c6["kt"], 2), f_(c6["k_coil"], 2), f_(c6["free"], 1), f_(-c6["free"], 1), f_(c6["states"]["rest"]["T"], 2), f_(c6["states"]["bottom"]["T"], 2),
         f_(P["spring_groove"][0] + P["spring_groove"][4], 1), f_(P["spring_groove"][3], 1), f_(P["spring_groove"][1], 0), f_(P["spring_groove"][2], 0), f_(P["spring_pocket"][0], 1), f_(P["spring_pocket"][1], 1),
         f_(c6["notch"]["slot_deg"], 0), f_(c6["arm"], 2)))
    a("1. C06a·C06b 구멍을 Ø4.0으로 뚫고 봉(18)을 C06a에 박는다. 봉에 흑연. 스프링(미스미 %s, 두 다리를 긴 %s / 짧은 %s로 자른 것)의 짧은 다리 끝을 C06b의 가둠 홈(폭 %s, %s° 방향) 입구에 대고 홈을 따라 끝까지 밀어 넣는다(코일이 넣는 슬롯 %s°로 주머니에 들어감) — 긴 다리가 북 쪽(+x) 끝(r4.5 고침 2). 0.5 선이 안 들어가면 홈을 0.5 날로 다듬고 폭을 적는다. C06b를 봉에 끼우고(허브가 브래킷 쪽) C01d 칼라로 막는다. 긴 다리를 C06a 홈(폭 %s, 다리 x에 맞춤)에 밑에서 넣는다(생산 조립과 같음 — 시험 13 연습)."
      % (P["spring_cat"]["part"], f_(P["spring_leg"], 1), f_(P["spring_short_leg"], 1), f_(c6["notch"]["width"], 2), f_(c6["notch"]["band_deg"], 0), f_(c6["notch"]["slot_deg"], 0), f_(P["spring_groove"][3], 1)))
    a("2. 실을 C06b 매듭 구멍(위쪽)에 묶어 북 홈 위로 시계 방향으로 감고 **오른쪽(+y, 홈 쪽)에서** 내려 C14 추 컵을 단다(팔 = 북 홈 반지름 %s + 실 반지름)." % f_(c6["Rd"], 1))
    a("3. 추 컵 무게(물 포함)를 10 / 15 / 20 / 25 / 30 / 35 / 40 g으로 바꾸며 북 눈금(레버 각 b)을 읽는다. 각 무게에서 북을 살짝 위·아래로 건드려 멈춘 두 값의 평균(마찰 상쇄).")
    a("4. 토크 T = m × 0.00981 × %s(N·mm)를 b에 대해 직선 맞춤: 기울기 = k_t, T = 0인 b = 자유각." % f_(c6["Rd"], 1))
    a("")
    a("| b (°) | " + " | ".join(f_(r["b"], 1) for r in c6["rows"]) + " |")
    a("|---|" + "---|" * len(c6["rows"]))
    a("| 모델 T (N·mm) | " + " | ".join(f_(r["T"], 2) for r in c6["rows"]) + " |")
    a("| 추 (g) | " + " | ".join(f_(r["grams"], 1) for r in c6["rows"]) + " |")
    a("")
    a("**합격: k_t %s~%s N·mm/rad, 자유각 %s~%s°, 쉼(b 0) %s~%s, 바닥(b 12.6) %s~%s N·mm.**"
      % (f_(c6["kt"] * 0.85, 2), f_(c6["kt"] * 1.15, 2), f_(c6["free"] - 5, 0), f_(c6["free"] + 5, 0), f_(c6["states"]["rest"]["T"] * 0.85, 2), f_(c6["states"]["rest"]["T"] * 1.15, 2),
         f_(c6["states"]["bottom"]["T"] * 0.85, 2), f_(c6["states"]["bottom"]["T"] * 1.15, 2)))
    for o in T["8"]["outcomes"]:
        a("- %s → %s" % (o["range"], o["param"]) + (" (%s)" % o["note"] if o["note"] else ""))
    a("")

    # ------------------------------------------------------------------ test 12
    a("### 시험 12 — 패드 바 잎 크리프 (C10)와 바 놀음")
    a("")
    a("모델: 잎 혀 %s×%s×%s, 설치 휨 %s(돌기 %s = 틈 %s + 휨), 힘 %s N(%s g), 늘 굽힘 %s MPa(공차 끝 +0.3이면 %s MPa)로 2 MPa 크리프 선 위. 두 잎의 힘은 패드 붙은 바 무게의 6.0배라 83 %% 넘게 풀려야 바가 처진다(§18)."
      % (f_(c10["t"], 1), f_(c10["w"], 1), f_(c10["L"], 0), f_(c10["pre"], 1), f_(c10["bump_h"], 1), f_(P["bar_leaf_gap"], 1), f_(c10["F"], 3), f_(c10["grams"], 1), f_(c10["sig"], 1), f_(c10["sig_tol"], 1)))
    a("1. **처음 힘.** C10c 턱 윗면에 쿠폰 뿌리를 얹고 강철 블록으로 누른다. 혀가 0.1 g 저울판 위로 나가 돌기가 아래를 보게 한다. C10c 밑에 PET 심 3장 + 카드를 괴어 돌기가 저울판에 **막 닿게**(0.1~0.3 g) 한다. 심 3장을 빼면 돌기가 0.3 눌린다 → 읽음 = F0 (모델 %s g)." % f_(c10["grams"], 1))
    a("2. **크리프.** 쿠폰 1·2를 C10b ‘0.3’ 자리, 쿠폰 3을 ‘0.6’ 자리(공차 끝)에 돌기가 아래로 가게 놓고 뿌리 위에 강철 블록을 얹는다. 40 °C에서 7일.")
    a("3. 꺼내 1시간 식힌 뒤 1을 다시 한다 → F1. 남은 비 = F1/F0.")
    a("")
    for o in T["12"]["outcomes"]:
        a("- %s → %s" % (o["range"], o["param"]) + (" (%s)" % o["note"] if o["note"] else ""))
    a("- 조립 모듈에서는 17장 그대로: 바를 뒤 멈춤까지 넣고 위아래로 흔들어 놀음 없음, 흑 칸에서 10번 빼기(21.5 mm부터 밀어 올림).")
    a("")

    # ------------------------------------------------------------------ test 20 (r4.4 fix 2)
    c16_ = R["C16"]
    Bp, Ba = c16_["B_play"], c16_["B_abuse"]
    sp_ = sorted(v_ for v_ in c16_["spread_play"] if v_)
    a("### 시험 20 — 강철 블록 유지 (C16a·b, r4.4 고침 2 · 2b)")
    a("")
    a("모델(4-DOF 동역학): 패드가 강철 윗면을 누를 때 캐리어가 강철을 받치는 힘이 매 음(PLAY 1.5 m/s) %s N, ABUSE %s N이다. 옆벽(0.7, r4.4 고침 2b) 판 모델로는 **스냅 립만으로는 버티지 못한다**: 이 힘이 립에서 옆벽 밖으로 치우쳐 걸려, 립 선이 한쪽 %s mm 벌어지고(물림 1.0) 옆벽 립 뿌리가 층 안 19 MPa를 넘는다. 그래서 강철 두 19×40 옆면을 **MS 폴리머(탄성) 접착제로** 옆벽에 붙인다(접착 면 %s mm², 매 음 전단 %s MPa + 열 %s MPa). r4.4 고침 2b: 단단한 5분 에폭시는 PETG(선팽창 60e-6/K)와 강철(11.7e-6/K)의 차이로 ΔT 15 K만 되어도 가장자리 전단 약 %s MPa라 떨어진다 — 탄성 접착제(G 약 %s MPa)는 %s MPa. 캐리어 옆벽은 %s(주머니 %s)라 접착층이 한쪽 %s 생긴다."
      % (f_(Bp, 1), f_(Ba, 1), " ~ ".join(f_(v_, 2) for v_ in sp_), f_(c16_["bond_area"] or 0, 0), f_((c16_["bond"].get("play") or {}).get("tau_mech", (c16_["bond"].get("play") or {}).get("tau", float("nan"))), 3),
         f_((c16_["bond"].get("play") or {}).get("tau_th", float("nan")), 3), f_(M.bond_thermal(P, P["bond_dT"][0], G=P["bond_G_epoxy"], t_a=P["bond_t"])["tau"], 1), f_(P["bond_G"], 1),
         f_(M.bond_thermal(P, P["bond_dT"][0])["tau"], 3), f_(P["carrier_side_wall"], 1), f_(P["lever_w"] - 2 * P["carrier_side_wall"], 1), f_(P["bond_t"], 2)))
    a("")
    a("1. C16a 3개를 생산 캐리어 설정으로 뽑고 허브를 Ø4.0으로 뚫는다. 강철 블록 3개(생산품)의 옆면을 사포(#120)로 긁고 알코올로 닦는다. 캐리어 옆벽 안쪽도 #120.")
    a("2. **스냅만 (캐리어 1)**: 강철을 밑에서 눌러 아래 립을 넘긴다. C16b를 주방 저울(10 kg) 위에 놓고, 캐리어를 옆벽 밑면으로 C16b 위에 얹는다(강철은 가운데 홈 위, 허브는 받침 뒤로 나감). C03c(누름 코, 날을 아래로 → 판을 아래로 뒤집어)로 강철 윗면 패드 자리(레버 y%s~%s)를 천천히 누르며 저울을 본다. 강철이 립을 밀고 빠지는 힘을 적는다. 모델: %s N(판의 앞·뒷벽 받침 핀 ~ 고정)."
      % (f_(P["pad_y"][0], 0), f_(P["pad_y"][1], 0), " ~ ".join(f_(Bp / v_, 0) for v_ in sp_[::-1])))
    a("3. **접착 (캐리어 2·3)**: 강철 두 옆면에 MS 폴리머(하이브리드) 접착제를 얇게(한 면 약 0.1 mL, 주걱으로 고르게) 바르고 밑에서 스냅으로 끼운다(생산과 같은 순서, DESIGN 10장 4단계). 윗 립·아래 립·캡스턴 펠트 자리로 밀려 나온 것은 바로 닦는다. 24시간 굳힌다.")
    a("3a. **온도 순환 (r4.4 고침 2b)**: 캐리어 2·3을 냉장고/냉동실(약 5 °C 이하) 2시간 ↔ 45 °C(지퍼백에 넣어 따뜻한 물, 또는 여름 차 안) 2시간을 3번 되풀이한 뒤 실온에서 4번으로 간다. 모델: 매일 ΔT %s K에서 열 전단 %s MPa, 운반 ΔT %s K에서 %s MPa(가장 얇은 접착층 %s)."
      % (f_(P["bond_dT"][0], 0), f_(M.bond_thermal(P, P["bond_dT"][0], t_a=P["bond_t_min"])["tau"], 3), f_(P["bond_dT"][1], 0), f_(M.bond_thermal(P, P["bond_dT"][1], t_a=P["bond_t_min"])["tau"], 3), f_(P["bond_t_min"], 2)))
    a("4. 캐리어를 C16b에 얹고 강철 윗면을 %s N(%s kg; 욕실 저울 또는 바이스 + 저울)으로 10초씩 3번 누른다. 다이얼(C03e 스탠드)을 강철 윗면 앞쪽(뚜껑 뒤 y155)에 대고 캐리어 뚜껑과의 높이 차이를 누르기 전·후에 잰다. **합격: 움직임 ≤ 0.05 mm, 립·옆벽에 흰 줄 없음.**"
      % (f_(1.5 * Ba, 0), f_(1.5 * Ba / 9.80665, 1)))
    a("5. 같은 캐리어를 1 m에서 나무 바닥에 세 방향(옆벽·앞·허브 쪽)으로 떨어뜨린다. 강철이 그대로면 합격.")
    a("6. 10^5회 반복(매 음 %s N)은 모터 캠 장치가 필요해 이 키트에 없다(시험 10과 같음). 대신 완성 모듈을 1주일 연주한 뒤 캐리어 몇 개를 빼 4번을 다시 한다." % f_(Bp, 0))
    a("")
    a("평철 모서리 반지름(압연 모서리)은 접착하면 상관없다(검증자 지적 (a)는 스냅만일 때의 문제). 스냅만으로 %s N 넘게 버티면 판 모델이 비관적이라는 뜻이지만, 그래도 아래 립 뿌리 층간 응력이 매 음 한계 5 MPa를 넘으므로 접착은 그대로 둔다." % f_(1.5 * Ba, 0))
    a("")
    # ------------------------------------------------------------------ test 19
    a("### 시험 19 — USB-C 케이블 (C13a)")
    a("")
    a("회로 인터페이스(고정값): 플러그 몰드 ≤ %s × %s × %s(z%s~%s), 선반 홈 x%s~%s(가장자리 틈 %s). C13a 창(%s × %s, 길이 %s)을 출력 뒤 캘리퍼로 확인하고(작으면 줄로 다듬음), 케이블 몰드가 창을 **끝까지 걸림 없이** 지나면 합격이다. 사기 전에 상품 페이지 치수가 12.5 × 7.6을 넘는 것은 거른다. 프레임 뒤 조각이 나오면 17장대로 10번 꽂고 뺀다."
      % (f_(c13["w"], 1), f_(c13["h"], 1), f_(c13["L"], 0), f_(P["usb_z"][0], 1), f_(P["usb_z"][1], 1), f_(c13["slot"][0], 2), f_(c13["slot"][1], 2), f_(c13["clear"], 1), f_(c13["w"], 1), f_(c13["h"], 1), f_(c13["L"], 0)))
    a("")

    # ------------------------------------------------------------------ assembled-module tests
    a("### 조립 모듈 시험 (7, 9, 10, 11, 13, 14, 17, 18, 21)")
    a("")
    a("건반·레버·프레임이 나온 뒤 17장 그대로 한다. 키트에서 쓰는 것과 숫자:")
    a("")
    a("- **7 DW/UW** — C14a 추 컵 바닥 가운데를 백 y13(흑 앞 끝 + 10)에 놓고 물을 스포이트로 넣어 건반이 끝까지 내려가는 무게 = DW, 끝까지 누른 컵에서 물을 빼 건반이 올라오는 무게 = UW. 합격 DW 47~55 g(모델 %s / %s), 백 립 y0 ≥ 47 g(%s), UW ≥ 20 g(%s / %s). 조정: 강철 앞 퍼티 1 g = DW +%s / +%s g, 캡스턴 1/8회전 = +%s / +%s g."
      % (f_(W["DW"], 1), f_(B["DW"], 1), f_(W["DW_lip"], 1), f_(W["UW"], 1), f_(B["UW"], 1), f_(adj["white_putty_steel"], 2), f_(adj["black_putty_steel"], 2), f_(adj["white_0.125"]["dDW"], 2), f_(adj["black_0.125"]["dDW"], 2)))
    a("- **9 복귀 시간** — 1 N = 강철 블록 2개(107.4 g = 1.05 N)를 건반 앞에 1초 얹었다가 옆으로 밀어 떨어뜨리고 240 fps로 앞끝을 찍는다. 합격 t50 ≤ %s ms(= 1/(2 × 13.3 Hz)), 끝까지 ≤ 60 ms; 모델 t50 %s / %s, 끝까지 %s / %s ms(마찰 2배 %s / %s)."
      % (f_(1000 / (2 * 13.3), 1), f_(t50w, 1), f_(t50b, 1), f_(t100w, 1), f_(t100b, 1), f_(S["friction x2"]["white"]["t100"], 1), f_(S["friction x2"]["black"]["t100"], 1)))
    a("- **10 노치 들림** — 노치 옆 흰 점을 240 fps. 합격 PLAY ≤ 0.20, ABUSE ≤ 0.40(모델 PLAY %s, 합격선 재료 화음 %s, ABUSE %s, ABUSE 재료 조합 최대 %s). 입술 천 10^5회 마모는 모터 캠 장치가 필요해 이 키트에 없다."
      % (f_(MM["key_lift_play_mm"], 3), f_(MM["key_lift_chord_pass_mm"], 3), f_(MM["key_lift_abuse_mm"], 3), f_(MM["key_lift_abuse_sets_mm"], 3)))
    a("- **11 유령** — 17장 그대로(거름 켜고 끔). 펌웨어는 의심 상태(note-on부터 %s ms 안에 재무장)의 건반마다 첫 다시 눌림 시각(note-on부터)과 속도를 기록한다. 모델: %d 경우 중 재무장 %d건, 거르지 못한 것 %d; 재무장한 건반을 note-on 뒤 %s s까지 돌려도 스스로 다시 닿는 것 %d건(흔들림 멈춤 ≤ %s ms) — 기록에서 유령 다시 눌림이 %s ms를 넘으면 창을 (가장 늦은 것 + 100 ms)로."
      % (f_(P["ghost_win"], 0), MM["ghost_cases"], MM["ghost_armed"], MM["ghost_not_dropped"], f_(P.get("ghost_long", 1500.0) / 1000.0, 1), MM.get("ghost_reland_n", 0), f_(MM.get("ghost_settle_max_ms", 0.0), 0), f_(P.get("ghost_rep_max", 500.0), 0)))
    a("- **13 스프링 넣기 (r4.5 고침 2)** — C06에서 한 순서를 생산 캐리어 C16a 3개로: 짧은 다리 끝을 가둠 홈(폭 %s, 레버 기준 %s° 방향, 축에서 %s~%s) 입구에 대고 홈을 따라 밀면 코일이 넣는 슬롯(%s°)으로 주머니에 들어가 앉는다(모델 넣는 길 짧은 다리 틈 %s; 홈이 0.15 좁게 나와도 지나감, 더 좁으면 0.5 날로 다듬음). 긴 다리는 코일의 +x 끝(오른쪽 감기; 뒤집어 넣으면 짧은 다리가 홈에 맞지 않음). 봉을 꿰기 전 레버를 쉼 자세·−31°로 기울여 코일이 넣는 슬롯으로 미끄러져 나오는지 보고(나오면 조립 때 이쑤시개 Ø2를 허브·코일에 꽂아 둠 — DESIGN 10장), 봉을 꿰고 레버를 −31°~+18°로 돌려 긴 다리가 창 면에 끌리지 않는지 본다."
      % (f_(c6["notch"]["width"], 2), f_(c6["notch"]["band_deg"], 1), f_(c6["notch"]["nn"][0], 2), f_(c6["notch"]["nn"][1], 2), f_(c6["notch"]["slot_deg"], 0), f_(MET.get("r45", {}).get("insert", {}).get("short_A", [0.0])[0], 3)))
    a("- **14 종이 띠** — 0.05 띠: 백 0.75 N에서 미끄러지고 1.04 N에서 물림, 흑 0.96 / 1.43 N (1 N ≈ 추 컵 102 g). PET 심 한 장 = 레버 %s° / %s°." % (f_(adj["white_shim"]["db0_deg"], 2), f_(adj["black_shim"]["db0_deg"], 2)))
    a("- **17 느낌** — y90 %s g, 흑 1 N 바닥이 펠트 위 %s mm. 흑 바닥이 무르면 `gap_us_b` −0.45 → −0.30." % (f_(W["DW_y90"], 0), f_(MET["heights"]["held_pad_front_b"], 2)))
    a("- **18 90° 세움** — 모든 건반 앞 높이 ±0.2. 빠지면 노치 R 한 단계 작게(시험 5 표).")
    # r4.5 fix 3 (verifier major): test 21 in the service direction (C17a comb, see c17)
    c17 = R["C17"]
    cs17 = c17["cases"]
    ln17 = " / ".join(f_(c, 1) for c in c17["lines"])
    a("- **21 첫 모듈 정하중 (r4.5 고침 2, 하중 방향은 r4.5 고침 3)** — 시험 3은 출력한 띠의 E만 잰다. F|F# 킬 뿌리와 밸런스 레일의 휨은 이 시험으로 잰다.")
    a("  - **방향이 중요하다.** 쓰임에서는 패드가 윗판을 밑에서 밀어 올린다. 그러면 F|F# 핀과 킬이 밸런스 레일 뒷면을 위로 당기고, 레일은 핀 선 사이에서 들린다. "
      "모듈을 바닥 EVA에 둔 채 윗판을 위에서 누르면 방향이 반대다. 레일과 바닥 띠(z%s~%s)가 EVA(z%s~%s)에 얹혀, 레일 자체가 약해도 단단한 레일처럼 읽힌다. 그러면 약한 레일도 합격이 나온다. "
      "그래서 모듈을 C17a 받침 빗에 얹고 위에서 누른다. 빗은 핀 선과 뒷벽만 받치고 레일 밑은 비어 있다. 모델은 선형이므로 이것이 쓰임과 같은 레일 휨이다."
      % (f_(P["z_floor"][0], 0), f_(P["z_floor"][1], 0), f_(P["z_eva"][0], 0), f_(P["z_eva"][1], 0)))
    a("  1. 첫 모듈을 다 조립한다(패드 바 넣음). 모듈 밑에 EVA가 붙어 있으면 뗀다. C17a가 EVA 두께 %s mm를 대신한다. EVA 위에서 재면 EVA가 눌린 만큼 더 처진다." % f_(c17["h"], 0))
    a("  2. 평평한 책상에 C17a를 놓고 모듈을 얹는다. 이 4개는 핀 선 x%s 밑에, 뒤 막대는 뒷벽 밑(y%s~%s)에 온다. 양 끝 이의 바깥 면을 모듈 옆면에 맞춘다."
      % (ln17, f_(c17["bar"][2], 0), f_(c17["bar"][3], 0)))
    a("  3. 레일 밑(x%s~%s, y%s~%s)과 기판 구멍 밑이 책상에서 떠 있는지 본다. 종이 띠가 걸림 없이 지나가야 한다. 빗 말고는 모듈 밑에 닿는 것이 없어야 한다."
      % (f_(c17["gap"][0], 1), f_(c17["gap"][1], 1), f_(P["rail_front_y"], 1), f_(P["rail_y"][1], 1)))
    a("  4. %s 여섯 패드 자리 위 윗판 윗면에 6×12 받침 6개를 놓는다. 그 위에 곧은 판재를 얹고 물통·아령으로 %s kg(= 6 × %s N)을 싣는다."
      % ("-".join(c17["keys"]), f_(c17["kg"], 1), f_(c17["F"], 0)))
    a("  5. 다이얼 스탠드는 책상에 둔다. 다이얼 끝을 E·F 패드 자리 옆 윗판 윗면에 대고 0 → 하중 → 0을 3번 읽는다.")
    a("  - **합격: E·F 처짐 ≤ %s mm** (= %s N ÷ %s N/mm). 모델(레일을 핀 선 위 연속 보로 봄)은 %s mm다. 레일 받침의 두 끝: 레일이 단단하면 %s mm, 레일이 이웃 핀 선 사이에서 단순 지지만이면 %s mm(불합격). 이 시험이 그 둘을 가른다."
      % (f_(c17["limit"], 2), f_(c17["F"], 0), f_(P["seat_k_chord_req"], 0), f_(cs17["fins"]["EF"], 3), f_(cs17["rigid"]["EF"], 3), f_(cs17["fins_span"]["EF"], 3)))
    a("  - 넘으면 run_all의 화음 자리 강성 `k_ch`를 잰 값(%s N ÷ 처짐)으로 바꿔 화음 자리 동역학(들림 0.20, 키퍼, 유령)을 다시 본다. 그래도 불합격이면 회로 세션과 리본 차선 위 레일 높이를 다시 정한다. "
      "킬 윗단(z%s)과 F|F# 핀 앞끝(y%s)은 이미 건반 F와의 1.3 한계라 더 키울 수 없다(DESIGN 18장)."
      % (f_(c17["F"], 0), f_(P["fin_keel"][2], 1), f_(M.keel_front(P), 1)))
    a("")

    # ------------------------------------------------------------------ model update
    a("## 4. 결과를 모델에 넣는 법")
    a("")
    a("1. `stage0_results_template.csv`를 채운다(판정 O/X).")
    a("2. 바뀐 값만 `model_v4.py`의 `P`에 넣는다: `pad_e`, `pad_E`, `front_e`, `notch_R`(+ `lift_play`·`lift_abuse`·`lift_popout`), `tab_w_b`·`tab_w`·`tab_cloth`·`tab_play`, `spring_kt`·`spring_free_deg`, `bar_leaf`, 필요하면 `E_PETG`(= 1950 r)·`plate_t`, `gap_us_w/_b`(대안 ①), `s_rare`·`s_cyc`(층간 강도).")
    a("3. `run_all.py`를 다시 돌려 0.2장의 모든 목표가 통과인지 본다. 통과하지 않는 값이 있으면 위 표의 다음 대안으로.")
    a("4. 모델에 아직 없는 값(시험 P의 핀 구멍 Ø, 시험 C의 너트 홈 폭·잠김 구멍 Ø)은 새 매개변수로 넣고 geometry에 내보낸다.")
    a("")
    a("## 5. 파일")
    a("")
    a("- `make_stage0.py` — 이 키트를 만드는 스크립트 (`MODEL_DIR` 환경변수, 기본 `../`). OpenSCAD로 STL, STL을 다시 읽어 PNG.")
    a("- `stage0_geometry.json` — 부품 C01a~C16b의 치수·출력·질량·브리지 면적, 시험별 합격선·결과 대응, 모델 해석 값.")
    a("- `stl/`, `png/`, `scad/` — 부품별 STL(출력 방향), 두 방향 그림, 생성된 OpenSCAD 원본.")
    a("- `stage0_results_template.csv` — 결과 기록표.")
    open(os.path.join(HERE, "stage0_procedure.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    only = sys.argv[1:] or None
    R = {}
    for k, fn in (("C01", c01), ("C02", c02), ("C03", c03), ("C04", c04), ("C05", c05), ("C06", c06), ("C07", c07), ("C08", c08),
                  ("C09", c09), ("C10", c10), ("C11", c11), ("C12", c12), ("C13", c13), ("C14", c14), ("C15", c15), ("C16", c16),
                  ("C17", c17)):
        t = time.time()
        R[k] = fn()
        print("%s built (%.1f s)" % (k, time.time() - t))
    export_all(only)
    for p in PARTS:
        if "stl" in p:
            print(p["id"], p["bbox"], p["volume_cm3"], "wt" if p["watertight"] else "NOT WATERTIGHT", "bridge", p["bridge_area_mm2"], "over45", p["overhang45_area_mm2"])
    write_docs(R)
    print("docs written (%.0f s total)" % (time.time() - T0))
