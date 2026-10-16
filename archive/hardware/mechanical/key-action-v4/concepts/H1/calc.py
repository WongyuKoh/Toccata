#!/usr/bin/env python3
"""Toccata v4 concept H1 -- Casio/GHS-type rear-pivot key + weighted hammer, downsized.

Every number reported in results.txt / design.md comes from this file.
Units: mm, g, N, ms (SI inside the dynamic simulation).  z = 0 desk, y = 0 white key front lip,
+y away from the player, x across.  Rotations are CCW in the (y, z) plane; for BOTH bodies a
positive angle is the "pressed" direction (key front goes down, hammer nose goes down / weight up).

Architecture (one hammer part for all 12 keys of an octave):
  key    : printed PETG U-channel (v3 outer shape y0..163), rear tongue with an open-rear slot that
           slides onto a Ø3 SUS304 rod at (171, 40) = v3's leaf instantaneous centre (171.04, 40.96),
           so the front of the key moves exactly like v3 (sensor, stops, hook, tab unchanged).
  hammer : printed PETG lever on a second Ø3 rod; nose pad (felt 1T) under a lug that hangs from the
           key (black lug y95, white lug y_cw), long rear arm to a steel block (cut 9x25 flat bar)
           that sits BEHIND the key rod, above the (shrunk) control board.
  rest   : v3 tab+hook (up-stop felt) holds the key; the hammer pushes the key up against it, so the
           coupling is always preloaded (no play).  Down-stop: v3 front felt.  Hammer over-travel stop:
           felt on the floor under the nose.  Hammer rest stop (key removed only): felt on the board ledge.
"""
import math

GF = 9.80665e-3          # N per gram-force
G = 9.80665              # m/s^2
RHO_PETG = 1.25          # g/cm3 (Bambu PETG Basic)
RHO_STEEL = 7.85
RHO_NDFEB = 7.5

# ------------------------------------------------------------------ parameters
P = dict(
    # v3 interfaces (kept)
    z_floor=5.0, z_top_w=43.5, z_bot=23.5, z_top_b=55.5, skin_w=2.6, skin_b=2.0, wall=1.2,
    dip_w=10.0, dip_b=9.5, y_bf=52.5,
    y_mag_w=65.8, y_mag_b=64.2, z_elem_w=12.68, z_elem_b=10.15,
    sens_top_w=13.709, sens_top_b=11.176, bar_top_w=13.6, bar_top_b=11.5, bar_y=(59.0, 77.5),
    tab_y=(84.0, 91.0), crossbar_top=25.1, hook_felt_bot=25.1, hook_under=28.1,
    y_front_felt_w=6.6, y_front_felt_b=55.85,          # centre of the down-stop contact patch
    y_f_w=13.0, y_f_b=62.5,                            # where DW is measured (v3 convention)
    frame_depth=212.0, rear_wall=(209.0, 212.0),
    tail_w=13.5,                                       # representative white tail width
    # key rod (pivot)
    pk=(171.0, 40.0), rod_d=3.0, tongue_r=3.5, fin_half=5.0, fin_t=1.6, fin_cl=0.2,
    # coupling
    R_lug=3.0, t_pad=1.0, y_cb=96.0, y_cw=108.0, z_pc=20.0, alpha_deg=14.0,
    # hammer
    y_ph=None, z_ph=15.0,          # y_ph solved for equal white/black hammer rotation
    y_n0=93.5, y_pad1=113.0, h_nose=5.0, w_nose=8.0,
    boss_half=8.0, boss_h=8.0, w_boss=8.0,
    w_arm=6.0, h_arm=7.0,
    # weight block: cut piece of 9 x 25 flat bar: 9 across x, 25 along y, h = cut length (z)
    blk_w=9.0, blk_L=25.0, blk_h=None, y_w0=182.0,
    ring_side=0.8, ring_front=1.6, ring_back=0.8, ring_chamfer=9.0,
    # stops / felts
    ledge_face=15.7,               # board ledge (1.2 PETG over components <= z13.0) + felt 1T
    rest_gap=0.8,                  # weight bottom above ledge felt at key rest
    cover_top=66.0, cover_t=2.5, rail_t=5.0, stop_felt_t=3.0, stop_gap=0.5, stop_dff=1.4,
    # friction
    mu_pin=0.25, mu_pad=0.15, guide_drag_g=0.6, black_dw_extra=2.5, match_black=True,
)


def rot(p, c, a):
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def rotv(v, a):
    ca, sa = math.cos(a), math.sin(a)
    return (v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca)


def rect(y0, y1, z0, z1):
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def poly_props(poly):
    """area, centroid, polar second moment about the origin  (int (y^2+z^2) dA)."""
    A = cy = cz = J = 0.0
    n = len(poly)
    for i in range(n):
        y0, z0 = poly[i]
        y1, z1 = poly[(i + 1) % n]
        c = y0 * z1 - y1 * z0
        A += c
        cy += (y0 + y1) * c
        cz += (z0 + z1) * c
        J += c * (y0 * y0 + y0 * y1 + y1 * y1 + z0 * z0 + z0 * z1 + z1 * z1)
    A *= 0.5
    cy /= (6 * A)
    cz /= (6 * A)
    J /= 12.0
    if A < 0:
        A, J = -A, -J
    return A, (cy, cz), J


class Body:
    """rigid body = list of (name, polygon(y,z), x-thickness, density, fill)."""

    def __init__(self, name, pivot):
        self.name, self.pivot, self.parts = name, pivot, []

    def add(self, name, poly, t, rho=RHO_PETG, fill=1.0):
        self.parts.append((name, poly, t, rho, fill))

    def props(self, only=None):
        m = my = mz = I = 0.0
        py, pz = self.pivot
        for name, poly, t, rho, fill in self.parts:
            if only and not only(name):
                continue
            sh = [(y - py, z - pz) for y, z in poly]
            A, (cy, cz), J = poly_props(sh)
            mi = A * t * rho * fill / 1000.0
            m += mi
            my += mi * cy
            mz += mi * cz
            I += J * t * rho * fill / 1000.0
        return dict(m=m, com=(py + my / m, pz + mz / m), I=I)   # I about pivot, g*mm^2

    def vol_petg(self):
        return sum(poly_props(p)[0] * t * f for _, p, t, rho, f in self.parts if rho == RHO_PETG)


# ------------------------------------------------------------------ coupling pad plane
def pad_geom(P):
    a = math.radians(P["alpha_deg"])
    n0 = (math.sin(a), math.cos(a))                    # unit normal (up, tilted toward +y)
    zp = lambda y: P["z_pc"] - (y - P["y_cb"]) * math.tan(a)   # felt top surface at rest
    Q0 = (P["y_cb"], P["z_pc"])
    Cb = (P["y_cb"] + P["R_lug"] * n0[0], zp(P["y_cb"]) + P["R_lug"] * n0[1])
    Cw = (P["y_cw"] + P["R_lug"] * n0[0], zp(P["y_cw"]) + P["R_lug"] * n0[1])
    return dict(a=a, n0=n0, zp=zp, Q0=Q0, Cb=Cb, Cw=Cw)


# ------------------------------------------------------------------ bodies
def white_key(P, G_):
    pk = P["pk"]
    k = Body("white key", pk)
    ztop, zb, sk, w = P["z_top_w"], P["z_bot"], P["skin_w"], P["wall"]
    zc = ztop - sk                                     # ceiling z40.9
    tw, yend = P["tail_w"], pk[0] - 8.0                # body ends at y163
    k.add("top head", rect(0, 50, zc, ztop), 22.5)
    k.add("top tail", rect(50, yend, zc, ztop), tw)
    k.add("front wall", rect(0, w, zb, zc), 22.5 - 2 * w)
    k.add("walls head", rect(w, 50, zb, zc), 2 * w)
    k.add("step wall y50", rect(50, 50 + w, zb, zc), 22.5 - tw)
    k.add("walls tail", rect(50 + w, yend, zb, zc), 2 * w)
    k.add("rear wall", rect(yend - w, yend, pk[1] - 3.5, zc), tw - 2 * w)
    k.add("front floor plate", rect(2.7, 10.5, zb, zb + 1.2), 22.5 - 2 * w)
    k.add("guide ribs", rect(80, 95, zb, zc), 2 * w)
    k.add("crossbar", rect(P["tab_y"][0], P["tab_y"][1], zb, P["crossbar_top"]), 8.6)
    k.add("magnet boss", rect(P["y_mag_w"] - 3.8, P["y_mag_w"] + 3.8, zb, zc), 7.6 * math.pi / 4)
    C = G_["Cw"]
    k.add("lug post", rect(C[0] - 3, C[0] + 3, C[1], zc), 7.0, fill=0.8)
    k.add("lug nose", [(C[0] - 3, C[1]), (C[0] - 2.1, C[1] - 2.1), (C[0], C[1] - 3.0),
                       (C[0] + 2.1, C[1] - 2.1), (C[0] + 3, C[1])], 7.0)
    k.add("tongue", rect(yend, pk[0] + 3.5, pk[1] - 3.5, pk[1] + 3.5), 8.0, fill=0.85)
    k.add("magnet", rect(P["y_mag_w"] - 2.5, P["y_mag_w"] + 2.5, zb, zb + 2.0), 5 * math.pi / 4, RHO_NDFEB)
    return k


def black_key(P, G_):
    pk = P["pk"]
    k = Body("black key", pk)
    ztop, zb, sk, w = P["z_top_b"], P["z_bot"], P["skin_b"], P["wall"]
    zc = ztop - sk
    yf, yend = P["y_bf"], pk[0] - 8.0
    k.add("top skin", rect(yf, 142, zc, ztop), (11.0 + 9.5) / 2)
    k.add("front wall", rect(yf, yf + w, zb, zc), 11.0 - 2 * w)
    k.add("walls", rect(yf + w, 146, zb, zc), 2 * w)
    k.add("step down y142-146", rect(142, 146, 43.5, ztop), 11.0)
    k.add("rear top skin", rect(146, yend, 41.5, 43.5), 11.0)
    k.add("rear walls", rect(146, yend, zb, 41.5), 2 * w)
    k.add("rear wall", rect(yend - w, yend, pk[1] - 3.5, 41.5), 11.0 - 2 * w)
    k.add("front floor plate", rect(52.7, 59.0, zb, zb + 1.2), 11.0 - 2 * w)
    k.add("crossbar", rect(P["tab_y"][0], P["tab_y"][1], zb, P["crossbar_top"]), 8.6)
    k.add("magnet boss", rect(P["y_mag_b"] - 3.8, P["y_mag_b"] + 3.8, zb, zb + 8.0), 7.6 * math.pi / 4)
    k.add("magnet web", rect(P["y_mag_b"] - 0.6, P["y_mag_b"] + 0.6, zb + 8.0, zc), 11.0 - 2 * w)
    C = G_["Cb"]
    k.add("lug web", rect(C[0] - 0.8, C[0] + 0.8, C[1] + 6.0, zc), 11.0 - 2 * w)
    k.add("lug post", rect(C[0] - 3, C[0] + 3, C[1], C[1] + 6.0), 7.0, fill=0.8)
    k.add("lug nose", [(C[0] - 3, C[1]), (C[0] - 2.1, C[1] - 2.1), (C[0], C[1] - 3.0),
                       (C[0] + 2.1, C[1] - 2.1), (C[0] + 3, C[1])], 7.0)
    k.add("tongue", rect(yend, pk[0] + 3.5, pk[1] - 3.5, pk[1] + 3.5), 8.0, fill=0.85)
    k.add("magnet", rect(P["y_mag_b"] - 2.5, P["y_mag_b"] + 2.5, zb, zb + 2.0), 5 * math.pi / 4, RHO_NDFEB)
    return k


def hammer_polys(P, G_, black=False):
    """named side-profile polygons of the hammer at rest (world y, z) with x widths."""
    yph, zph = P["y_ph"], P["z_ph"]
    zp, tf, hn = G_["zp"], P["t_pad"] / math.cos(G_["a"]), P["h_nose"]
    y0, y1 = P["y_n0"], P["y_pad1"]
    zt0, zt1 = zp(y0) - tf, zp(y1) - tf
    nose = [(y0, zt0 - hn), (y1, zt1 - hn), (y1, zt1), (y0, zt0)]
    yb0, yb1 = yph - P["boss_half"], yph + P["boss_half"]
    zb0, zb1 = zph - P["boss_h"] / 2, zph + P["boss_h"] / 2
    farm = [(y1, zt1 - hn), (yb0, zb0), (yb0, zb1), (y1, zt1)]
    boss = rect(yb0, yb1, zb0, zb1)
    yw0, L, zw, h = P["y_w0"], P["blk_L"], P["z_wb"], P["blk_h"]
    hs = h - P["blk_h_b"] if (black and P.get("blk_h_b")) else 0.0     # black: shorter steel on a PETG shim
    yr0 = yw0 - P["ring_front"]
    za0 = P["z_arm_r"]                                   # rear-arm bottom at the ring front
    rarm = [(yb1, zph - P["h_arm"] / 2), (yr0, za0), (yr0, za0 + P["h_arm"]), (yb1, zph + P["h_arm"] / 2)]
    ch = P["ring_chamfer"]
    ringf = [(yr0, zw), (yw0, zw), (yw0, zw + h), (yr0, zw + min(ch, h))]   # front face ch tall, then sloped
    rings = rect(yw0, yw0 + L, zw, zw + h)
    ringb = rect(yw0 + L, yw0 + L + P["ring_back"], zw, zw + h)
    blk = rect(yw0, yw0 + L, zw + hs, zw + h)
    ringw = P["blk_w"] + 2 * P["ring_side"]
    return [("nose pad", nose, P["w_nose"], RHO_PETG, 1.0),
            ("front arm", farm, P["w_nose"], RHO_PETG, 1.0),
            ("boss", boss, P["w_boss"], RHO_PETG, 0.85),
            ("rear arm", rarm, P["w_arm"], RHO_PETG, 1.0),
            ("ring front", ringf, ringw, RHO_PETG, 1.0),
            ("ring sides", rings, 2 * P["ring_side"], RHO_PETG, 1.0),
            ("ring back", ringb, ringw, RHO_PETG, 1.0),
            ("steel block", blk, P["blk_w"], RHO_STEEL, 1.0)] + (
            [("black shim", rect(yw0, yw0 + L, zw, zw + hs), P["blk_w"], RHO_PETG, 1.0)] if hs > 0 else [])


def hammer(P, G_, black=False):
    h = Body("hammer (black)" if black else "hammer (white)", (P["y_ph"], P["z_ph"]))
    for name, poly, t, rho, fill in hammer_polys(P, G_, black):
        h.add(name, poly, t, rho, fill)
    return h


# ------------------------------------------------------------------ kinematics
def lug_center(P, G_, black, th_k):
    return rot(G_["Cb"] if black else G_["Cw"], P["pk"], th_k)


def pad_signed(P, G_, C, th_h):
    """signed distance lug-centre -> felt surface minus lug radius (<0 = penetration)."""
    Oh = (P["y_ph"], P["z_ph"])
    Q = rot(G_["Q0"], Oh, th_h)
    n = rotv(G_["n0"], th_h)
    return (C[0] - Q[0]) * n[0] + (C[1] - Q[1]) * n[1] - P["R_lug"], n


def th_h_of(P, G_, black, th_k):
    C = lug_center(P, G_, black, th_k)
    lo, hi = -0.6, 0.9
    for _ in range(80):
        m = 0.5 * (lo + hi)
        s, _ = pad_signed(P, G_, C, m)
        # rotating the hammer CCW moves the pad (nose) down -> s grows
        if s > 0:
            hi = m
        else:
            lo = m
    return 0.5 * (lo + hi)


def theta_bottom(P, black):
    """key rotation at first contact with the front down-stop felt (dip measured on the top front edge)."""
    pk = P["pk"]
    p0 = (P["y_bf"], P["z_top_b"]) if black else (0.0, P["z_top_w"])
    dip = P["dip_b"] if black else P["dip_w"]
    lo, hi = 0.0, 0.3
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if p0[1] - rot(p0, pk, m)[1] < dip:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def solve_y_ph(P):
    """hammer pivot y so that white and black keys turn the (identical) hammer by the same angle."""
    tb_w, tb_b = theta_bottom(P, False), theta_bottom(P, True)
    lo, hi = P["y_cw"] + 6.0, 175.0

    def f(yph):
        Q = dict(P, y_ph=yph)
        G_ = pad_geom(Q)
        return th_h_of(Q, G_, False, tb_w) - th_h_of(Q, G_, True, tb_b)
    flo = f(lo)
    for _ in range(60):
        m = 0.5 * (lo + hi)
        fm = f(m)
        if (fm > 0) == (flo > 0):
            lo, flo = m, fm
        else:
            hi = m
    return 0.5 * (lo + hi)



def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def poly_at(poly, c, a):
    return [rot(p, c, a) for p in poly]


# ------------------------------------------------------------------ design completion
def complete(P, d_ff=None):
    """fill in y_ph (equal rotation) and the weight-block height from the vertical budget.

    The hammer over-travel stop is a felt strip (3T) under a printed stop rail that sits on the rear wall;
    the rear cover sits on the rail.  At the key's bottom (front felt first contact) the block top is
    stop_gap below the felt; d_ff = design felt compression at a hard blow (verified by strike())."""
    Q = dict(P)
    d_ff = Q["stop_dff"] if d_ff is None else d_ff
    Q["y_ph"] = solve_y_ph(Q)
    G_ = pad_geom(Q)
    tb_w, tb_b = theta_bottom(Q, False), theta_bottom(Q, True)
    th_hb = th_h_of(Q, G_, False, tb_w)
    Q["z_wb"] = Q["ledge_face"] + Q["rest_gap"]
    Oh = (Q["y_ph"], Q["z_ph"])
    Q["cover_under"] = Q["cover_top"] - Q["cover_t"]
    Q["stop_face"] = Q["cover_under"] - Q["rail_t"] - Q["stop_felt_t"]
    Q.update(th_hb=th_hb, tb_w=tb_w, tb_b=tb_b)
    Q["z_arm_r"] = Q["z_wb"] + 1.0
    h = 8.0
    while True:
        Q["blk_h"] = h + 0.5
        top = max(p[1] for _, poly, *_ in hammer_polys(Q, G_) for p in poly_at(poly, Oh, th_hb))
        if top > Q["stop_face"] - Q["stop_gap"]:
            break
        h += 0.5
    Q["blk_h"] = h
    yw0, L, zt = Q["y_w0"], Q["blk_L"], Q["z_wb"] + h
    c_top = rot((yw0 + L / 2, zt), Oh, th_hb)
    Q["r_stop"] = c_top[0] - Oh[0]
    Q["th_stop"] = th_hb + Q["stop_gap"] / Q["r_stop"]
    Q["th_hmax"] = th_hb + (Q["stop_gap"] + d_ff) / Q["r_stop"]
    Q["blk_h_b"] = None
    if Q.get("match_black", True):
        dw_w = statics(Q, G_, False, 1e-4, 1)["F_g"]
        hb = h
        while hb > 8.0:
            Q["blk_h_b"] = hb - 0.5
            if statics(Q, G_, True, 1e-4, 1)["F_g"] < dw_w + Q["black_dw_extra"]:
                break
            hb -= 0.5
        Q["blk_h_b"] = hb
    return Q, G_


# ------------------------------------------------------------------ statics
def statics(Q, G_, black, th_k, s, y_f=None, mu=True):
    """finger force (gf, vertical, on the key top at y_f) for quasi-static equilibrium at key angle th_k.
    s=+1 key moving down (DW), -1 moving up (UW), 0 frictionless (balance weight)."""
    K = black_key(Q, G_) if black else white_key(Q, G_)
    H = hammer(Q, G_, black)
    kp, hp = K.props(), H.props()
    Ok, Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
    th_h = th_h_of(Q, G_, black, th_k)
    d = 1e-5
    ratio = (th_h_of(Q, G_, black, th_k + d) - th_h_of(Q, G_, black, th_k - d)) / (2 * d)
    C = lug_center(Q, G_, black, th_k)
    _, n = pad_signed(Q, G_, C, th_h)
    t = (n[1], -n[0])
    Pc = (C[0] - Q["R_lug"] * n[0], C[1] - Q["R_lug"] * n[1])
    # slip direction (key material relative to hammer material, for w_k = s)
    rk, rh = (Pc[0] - Ok[0], Pc[1] - Ok[1]), (Pc[0] - Oh[0], Pc[1] - Oh[1])
    vk = (-rk[1], rk[0])
    vh = (-rh[1] * ratio, rh[0] * ratio)
    vt = (vk[0] - vh[0]) * t[0] + (vk[1] - vh[1]) * t[1]
    slip_per_rad = abs(vt)
    mu_c = Q["mu_pad"] if (mu and s != 0) else 0.0
    mu_p = Q["mu_pin"] if (mu and s != 0) else 0.0
    sg = s * (1 if vt > 0 else -1)
    dirk = (n[0] - mu_c * sg * t[0], n[1] - mu_c * sg * t[1])   # unit-N contact force on the key
    Wk = (0.0, -kp["m"] * GF)
    Wh = (0.0, -hp["m"] * GF)
    Gk = rot(kp["com"], Ok, th_k)
    Gh = rot(hp["com"], Oh, th_h)
    tau_gk = cross((Gk[0] - Ok[0], Gk[1] - Ok[1]), Wk)
    tau_gh = cross((Gh[0] - Oh[0], Gh[1] - Oh[1]), Wh)
    r_pin = Q["rod_d"] / 2
    N = 1.0
    for _ in range(30):                         # hammer: tau_gh + tau(-N*dirk) - s*mu*r*|R_h| = 0
        Rh = (-(Wh[0] - N * dirk[0]), -(Wh[1] - N * dirk[1]))
        fr = -s * mu_p * r_pin * math.hypot(*Rh)
        N = (tau_gh + fr) / cross(rh, dirk)
    Fc = (N * dirk[0], N * dirk[1])
    yf = y_f if y_f is not None else (Q["y_f_b"] if black else Q["y_f_w"])
    ztop = Q["z_top_b"] if black else Q["z_top_w"]
    pf = rot((yf, ztop), Ok, th_k)
    lever = Ok[0] - pf[0]
    r_guide = Ok[0] - 0.5 * (Q["tab_y"][0] + Q["tab_y"][1])
    tau_guide = -s * (Q["guide_drag_g"] * GF if (mu and s) else 0.0) * r_guide
    F = 0.0
    for _ in range(30):                         # key: tau_gk + F*lever + cross(rk,Fc) + guide - s*mu*r*|R_k| = 0
        Rk = (-(Wk[0] + Fc[0]), -(Wk[1] - F + Fc[1]))
        fr = -s * mu_p * r_pin * math.hypot(*Rk)
        F = -(tau_gk + cross(rk, Fc) + tau_guide + fr) / lever
    Rk = (-(Wk[0] + Fc[0]), -(Wk[1] - F + Fc[1]))
    Rh = (-(Wh[0] - Fc[0]), -(Wh[1] - Fc[1]))
    return dict(F_g=F / GF, N_g=N / GF, Fc=Fc, n=n, th_h=th_h, ratio=ratio, lever=lever, Rk=Rk, Rh=Rh,
                slip_per_rad=slip_per_rad, kp=kp, hp=hp, Pc=Pc, fx_key=Fc[0])


def m_eff(Q, G_, black, th_k, y_f):
    K = black_key(Q, G_) if black else white_key(Q, G_)
    H = hammer(Q, G_, black)
    st = statics(Q, G_, black, th_k, 0, y_f=y_f, mu=False)
    Ieff = K.props()["I"] + H.props()["I"] * st["ratio"] ** 2
    return Ieff / st["lever"] ** 2, st["ratio"], Ieff



# ------------------------------------------------------------------ geometry checks
def seg_dist(a, b, c, d):
    def pd(p, q, r):
        qy, qz = r[0] - q[0], r[1] - q[1]
        L2 = qy * qy + qz * qz
        u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - q[0]) * qy + (p[1] - q[1]) * qz) / L2))
        return math.hypot(p[0] - q[0] - u * qy, p[1] - q[1] - u * qz)
    return min(pd(a, c, d), pd(b, c, d), pd(c, a, b), pd(d, a, b))


def inside(p, poly):
    c, n = False, len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]):
            y = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if p[0] < y:
                c = not c
    return c


def poly_dist(A, B):
    """min distance between polygon outlines; negative (-0.01) if they overlap."""
    if any(inside(p, B) for p in A) or any(inside(p, A) for p in B):
        return -0.01
    return min(seg_dist(A[i], A[(i + 1) % len(A)], B[j], B[(j + 1) % len(B)])
               for i in range(len(A)) for j in range(len(B)))


def key_fin(Q):
    """key-comb fin side profile (one fin each side of every key tongue): holds the Ø3 rod with 2.5 mm
    of material around the hole; the top-rear corner is cut away for the rising weight ring."""
    y, z = Q["pk"]
    y0, y1 = y - Q["fin_half"] - 1.0, y + Q["fin_half"] - 1.0
    return [(y0, Q["z_floor"]), (y1, Q["z_floor"]), (y1, z + 1.0), (y1 - 2.5, z + 4.0), (y0, z + 4.0)]


def key_outline(Q, black):
    """side outline used for clearance: underside line + tongue (world, rest)."""
    pk = Q["pk"]
    yend = pk[0] - 8.0
    y0 = Q["y_bf"] if black else 0.0
    under = [(y0, Q["z_bot"]), (yend, Q["z_bot"])]
    tongue = rect(yend - 1.2, pk[0] + 3.5, pk[1] - 3.5, pk[1] + 3.5)   # incl. the body rear wall above the arm
    return under, tongue


def clearances(Q, G_, black, ff_over=0.6):
    """sweep the stroke (rest -> bottom + ff) and report minimum gaps between moving/fixed parts."""
    Ok, Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
    tb = Q["tb_b"] if black else Q["tb_w"]
    rf = Ok[0] - (Q["y_front_felt_b"] if black else Q["y_front_felt_w"])
    hp = hammer_polys(Q, G_, black)
    wide = {"ring front", "ring sides", "ring back", "steel block", "black shim"}
    interior = 8.6 if black else (12.72 - 2 * Q["wall"])
    ceil = (Q["z_top_b"] - Q["skin_b"]) if black else (Q["z_top_w"] - Q["skin_w"])
    under, tongue = key_outline(Q, black)
    fins = key_fin(Q)
    out = dict(floor=1e9, key_under=1e9, key_ceiling=1e9, tongue=1e9, fins=1e9, stop_rail=1e9, rear_wall=1e9,
               tab=1e9)
    states = []
    n = 24
    for i in range(n + 1):
        thk = -0.002 + (tb + ff_over / rf + 0.002) * i / n
        thk_c = min(thk, tb + ff_over / rf)
        thh = th_h_of(Q, G_, black, thk_c)
        states.append((thk_c, thh))
    states.append((tb, Q["th_hmax"]))              # key on its felt, hammer at full over-travel
    for thk, thh in states:
        uk = [rot(p, Ok, thk) for p in under]
        tg = [rot(p, Ok, thk) for p in tongue]
        for name, poly, wdt, rho, fill in hp:
            pp = poly_at(poly, Oh, thh)
            out["floor"] = min(out["floor"], min(p[1] for p in pp) - Q["z_floor"])
            out["stop_rail"] = min(out["stop_rail"], Q["stop_face"] + Q["stop_felt_t"] - max(p[1] for p in pp))
            out["rear_wall"] = min(out["rear_wall"], Q["rear_wall"][0] - max(p[0] for p in pp))
            if name in ("nose pad",):
                out["tab"] = min(out["tab"], min(p[0] for p in pp) - Q["tab_y"][1])
            # key underside / ceiling (only where the key body exists); nose pad is the contact face -> skip
            if name != "nose pad":
                for p in pp:
                    if uk[0][0] <= p[0] <= uk[1][0]:
                        zu = uk[0][1] + (uk[1][1] - uk[0][1]) * (p[0] - uk[0][0]) / (uk[1][0] - uk[0][0])
                        if wdt <= interior - 0.6:
                            out["key_ceiling"] = min(out["key_ceiling"], zu + (ceil - Q["z_bot"]) - p[1])
                        else:
                            out["key_under"] = min(out["key_under"], zu - p[1])
            out["tongue"] = min(out["tongue"], poly_dist(pp, tg))
            if name in wide or name == "rear arm":
                if name in wide:
                    out["fins"] = min(out["fins"], poly_dist(pp, fins))
    return out


def sensor(Q, black):
    Ok = Q["pk"]
    tb = Q["tb_b"] if black else Q["tb_w"]
    ym = Q["y_mag_b"] if black else Q["y_mag_w"]
    ze = Q["z_elem_b"] if black else Q["z_elem_w"]
    st = Q["sens_top_b"] if black else Q["sens_top_w"]
    bt = Q["bar_top_b"] if black else Q["bar_top_w"]
    m0, m1 = (ym, Q["z_bot"]), rot((ym, Q["z_bot"]), Ok, tb)
    # key underside over the sensor bar (y59..77.5) at the bottom
    y0 = Q["y_bf"] if black else 0.0
    ug = min(rot((y, Q["z_bot"]), Ok, tb)[1] - bt for y in [Q["bar_y"][0] + 0.5 * i for i in range(38)] if y >= y0)
    boss_r = 3.8
    # magnet boss outer edge (front/back of the Ø7.6 boss) vs sensor top
    bg = min(rot((ym + dy, Q["z_bot"]), Ok, tb)[1] - st for dy in (-boss_r, 0.0, boss_r))
    return dict(rest_face_elem=m0[1] - ze, bottom_face_elem=m1[1] - ze, travel=m0[1] - m1[1],
                y_shift=m1[0] - m0[0], bottom_boss_sensor=bg, bottom_under_bar=ug)



# ------------------------------------------------------------------ dynamics
E_FELT = 0.5      # MPa, initial compressive modulus of 3T wool felt (back-computed from v3 S17: 52 % at 4.8 mJ on 8x3)
ZETA = 0.35       # felt damping ratio (restitution ~0.3)


def felt_F(d, dd, k1, t, c):
    """nonlinear felt: stiffens x5 at 50 % strain, bottoms (x20) beyond 90 %; linear dashpot; never pulls."""
    if d <= 0:
        return 0.0
    e = d / t
    F = k1 * d * (1 + 4 * e * e)
    if e > 0.9:
        F += 20 * k1 * (d - 0.9 * t)
    F += c * dd
    return max(F, 0.0)


class Sim:
    def __init__(self, Q, G_, black, spring=None):
        self.Q, self.G_, self.black = Q, G_, black
        K = black_key(Q, G_) if black else white_key(Q, G_)
        H = hammer(Q, G_, black)
        self.kp, self.hp = K.props(), H.props()
        self.Ok, self.Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
        self.Ik = self.kp["I"] * 1e-9          # g mm^2 -> kg m^2
        self.Ih = self.hp["I"] * 1e-9
        self.tb = Q["tb_b"] if black else Q["tb_w"]
        self.yf = Q["y_f_b"] if black else Q["y_f_w"]
        self.ztop = Q["z_top_b"] if black else Q["z_top_w"]
        self.r_front = self.Ok[0] - (Q["y_front_felt_b"] if black else Q["y_front_felt_w"])
        self.r_hook = self.Ok[0] - 0.5 * (Q["tab_y"][0] + Q["tab_y"][1])
        self.r_nose = Q["r_stop"]            # (name kept) lever of the weight-top stop
        self.th_nose = Q["th_stop"]
        blk = H.props(only=lambda n: n == "steel block")
        self.r_ledge = blk["com"][0] - self.Oh[0]
        self.th_ledge = -Q["rest_gap"] / self.r_ledge
        # felt stiffness (N/mm) and damping (N s/mm) per contact
        mk_front = self.Ik / (self.r_front * 1e-3) ** 2
        mh_nose = self.Ih / (self.r_nose * 1e-3) ** 2
        mh_ledge = self.Ih / (self.r_ledge * 1e-3) ** 2
        st = statics(Q, G_, black, 0.0, 0, mu=False)
        m_sys_hook = (self.Ik + self.Ih * st["ratio"] ** 2) / (self.r_hook * 1e-3) ** 2
        rk_lug = math.hypot(*(a - b for a, b in zip(st["Pc"], self.Ok))) * 1e-3
        rh_lug = math.hypot(*(a - b for a, b in zip(st["Pc"], self.Oh))) * 1e-3
        mk_l, mh_l = self.Ik / rk_lug ** 2, self.Ih / rh_lug ** 2
        m_pad = mk_l * mh_l / (mk_l + mh_l)

        def c_of(k1, m):                      # k1 N/mm, m kg -> c in N/(mm/s)
            return 2 * ZETA * math.sqrt(k1 * 1e3 * m) * 1e-3
        A_front = 200.0 if not black else 82.0
        self.felt = dict(
            front=(E_FELT * A_front / 3.0, 3.0), hook=(E_FELT * 24 / 3.0, 3.0),
            pad=(E_FELT * 21 / Q["t_pad"], Q["t_pad"]), nose=(E_FELT * Q["blk_w"] * Q["blk_L"] / Q["stop_felt_t"], Q["stop_felt_t"]),
            ledge=(E_FELT * Q["blk_w"] * Q["blk_L"] / 1.0, 1.0))
        self.c = dict(front=c_of(self.felt["front"][0], mk_front), hook=c_of(self.felt["hook"][0], m_sys_hook),
                      pad=c_of(self.felt["pad"][0], m_pad), nose=c_of(self.felt["nose"][0], mh_nose),
                      ledge=c_of(self.felt["ledge"][0], mh_ledge))
        self.spring = spring                  # dict(k N/mm, y (contact y on the nose), engage (th_h))
        self.log_max = {}

    # ---- helpers
    def z_mag(self, thk):
        Q = self.Q
        ym = Q["y_mag_b"] if self.black else Q["y_mag_w"]
        return rot((ym, Q["z_bot"]), self.Ok, thk)[1]

    def forces(self, thk, wk, thh, wh, Ff, prev):
        Q, G_, Ok, Oh = self.Q, self.G_, self.Ok, self.Oh
        # gravity
        Gk = rot(self.kp["com"], Ok, thk)
        Gh = rot(self.hp["com"], Oh, thh)
        tk = -self.kp["m"] * GF * (Gk[0] - Ok[0])          # N mm
        th = -self.hp["m"] * GF * (Gh[0] - Oh[0])
        Fk_sum = [0.0, -self.kp["m"] * GF]
        Fh_sum = [0.0, -self.hp["m"] * GF]
        info = {}
        # lug / pad contact
        C = lug_center(Q, G_, self.black, thk)
        s, n = pad_signed(Q, G_, C, thh)
        d = -s
        dd = (d - prev.get("pad", d)) / prev["dt"] if "dt" in prev else 0.0
        prev["pad"] = d
        info["gap_pad"] = s
        N = felt_F(d, dd, *self.felt["pad"], self.c["pad"]) if d > 0 else 0.0
        if N > 0:
            Pc = (C[0] - Q["R_lug"] * n[0], C[1] - Q["R_lug"] * n[1])
            t = (n[1], -n[0])
            rk, rh = (Pc[0] - Ok[0], Pc[1] - Ok[1]), (Pc[0] - Oh[0], Pc[1] - Oh[1])
            vk = (-rk[1] * wk, rk[0] * wk)
            vh = (-rh[1] * wh, rh[0] * wh)
            vt = (vk[0] - vh[0]) * t[0] + (vk[1] - vh[1]) * t[1]       # mm/s
            fr = -Q["mu_pad"] * N * math.tanh(vt / 2.0)
            F = (N * n[0] + fr * t[0], N * n[1] + fr * t[1])
            tk += cross(rk, F)
            th += cross(rh, (-F[0], -F[1]))
            Fk_sum[0] += F[0]; Fk_sum[1] += F[1]
            Fh_sum[0] -= F[0]; Fh_sum[1] -= F[1]
        info["N_pad"] = N
        # key front felt (down-stop)
        d = (thk - self.tb) * self.r_front
        dd = wk * self.r_front
        Ff_ = felt_F(d, dd, *self.felt["front"], self.c["front"])
        tk -= Ff_ * self.r_front
        Fk_sum[1] += Ff_
        info["F_front"], info["d_front"] = Ff_, d
        # hook (up-stop): felt pushes the key crossbar down
        d = -thk * self.r_hook
        dd = -wk * self.r_hook
        Fh_ = felt_F(d, dd, *self.felt["hook"], self.c["hook"])
        tk += Fh_ * self.r_hook
        Fk_sum[1] -= Fh_
        info["F_hook"], info["d_hook"] = Fh_, d
        # hammer over-travel stop: block top into the stop-rail felt
        d = (thh - self.th_nose) * self.r_nose
        dd = wh * self.r_nose
        Fn = felt_F(d, dd, *self.felt["nose"], self.c["nose"])
        th -= Fn * self.r_nose
        Fh_sum[1] -= Fn
        info["F_nose"], info["d_nose"] = Fn, d
        # ledge (weight rest; only without key)
        d = (self.th_ledge - thh) * self.r_ledge
        dd = -wh * self.r_ledge
        Fl = felt_F(d, dd, *self.felt["ledge"], self.c["ledge"])
        th += Fl * self.r_ledge
        Fh_sum[1] += Fl
        info["F_ledge"] = Fl
        # optional assist spring under the nose (compression, engages near the bottom)
        if self.spring:
            rs = self.spring["r"]
            d = (thh - self.spring["engage"]) * rs
            Fs = self.spring["k"] * d if d > 0 else 0.0
            th -= Fs * rs
            Fh_sum[1] += Fs
            info["F_spring"] = Fs
        # finger (vertical, down) at y_f on the key top
        pf = rot((self.yf, self.ztop), Ok, thk)
        tk += Ff * (Ok[0] - pf[0])
        Fk_sum[1] -= Ff
        # pivot friction (Coulomb, smoothed) using the static pivot reaction magnitude
        r_pin = Q["rod_d"] / 2
        tk -= Q["mu_pin"] * r_pin * math.hypot(*Fk_sum) * math.tanh(wk / 0.05)
        th -= Q["mu_pin"] * r_pin * math.hypot(*Fh_sum) * math.tanh(wh / 0.05)
        tk -= Q["guide_drag_g"] * GF * self.r_hook * math.tanh(wk / 0.05)
        return tk * 1e-3, th * 1e-3, info                 # N m

    def run(self, thk, thh, wk=0.0, wh=0.0, T=0.25, dt=2e-6, finger=lambda t, s: 0.0, events=None):
        prev = {}
        t = 0.0
        hist = []
        st = dict(thk=thk, wk=wk, thh=thh, wh=wh, t=0.0)
        step = 0
        while t < T:
            Ff = finger(t, st)
            tk, th, info = self.forces(thk, wk, thh, wh, Ff, prev)
            prev["dt"] = dt
            wk += tk / self.Ik * dt
            wh += th / self.Ih * dt
            thk += wk * dt
            thh += wh * dt
            t += dt
            st.update(thk=thk, wk=wk, thh=thh, wh=wh, t=t, info=info)
            for k in ("F_front", "F_hook", "F_nose", "N_pad", "d_nose", "d_front", "F_ledge"):
                self.log_max[k] = max(self.log_max.get(k, 0.0), info.get(k, 0.0))
            self.log_max["gap_pad"] = max(self.log_max.get("gap_pad", -9), info["gap_pad"])
            if events and events(t, st):
                break
            if step % 50 == 0:
                hist.append((t, thk, wk, thh, wh, info["gap_pad"], Ff))
            step += 1
        return st, hist


def rest_state(sim):
    """settle at rest (no finger) and return the equilibrium angles."""
    th0 = th_h_of(sim.Q, sim.G_, sim.black, 0.0)
    st, _ = sim.run(0.0, th0, T=0.25)
    return st["thk"], st["thh"]


def release_from_bottom(sim, frac=0.4):
    """key held at the down-stop (hammer in contact), finger removed at t=0."""
    Q = sim.Q
    thk0 = sim.tb
    thh0 = th_h_of(Q, sim.G_, sim.black, thk0)
    z_b, z_r = sim.z_mag(thk0), sim.z_mag(0.0)
    z_trig = z_b + frac * (z_r - z_b)
    res = {}

    def ev(t, s):
        zm = sim.z_mag(s["thk"])
        if "t_trig" not in res and zm >= z_trig:
            res["t_trig"] = t
        if "t_full" not in res and s["thk"] <= 0.0:
            res["t_full"] = t
            res["v_top"] = s["wk"] * (sim.Ok[0] - sim.yf)
            st0 = statics(Q, sim.G_, sim.black, 0.0, 0, mu=False)
            res["E_hook_mJ"] = 0.5 * (sim.Ik + sim.Ih * st0["ratio"] ** 2) * s["wk"] ** 2 * 1e3
        if "t_full" in res:
            res["bounce_mm"] = max(res.get("bounce_mm", 0.0), s["thk"] * (sim.Ok[0] - sim.yf))
        return False
    sim.log_max = {}
    st, hist = sim.run(thk0, thh0, T=0.20, events=ev)
    res["sep_max"] = sim.log_max.get("gap_pad", 0.0)
    res["hist"] = hist
    return res


def repetition(sim, F_rep, frac=0.4, cycles=6):
    """release at the bottom, re-press with constant finger force F_rep (N) as soon as the key has risen
    frac of the travel at the sensor, release again at the down-stop.  Returns the mean period of the
    last cycles (s)."""
    thk0 = sim.tb
    thh0 = th_h_of(sim.Q, sim.G_, sim.black, thk0)
    z_b, z_r = sim.z_mag(thk0), sim.z_mag(0.0)
    z_trig = z_b + frac * (z_r - z_b)
    state = dict(push=False, bottoms=[], trig=[])

    def finger(t, s):
        return F_rep if state["push"] else 0.0

    def ev(t, s):
        zm = sim.z_mag(s["thk"])
        if not state["push"] and zm >= z_trig and s["wk"] < 0:
            state["push"] = True
            state["trig"].append(t)
        if state["push"] and s["thk"] >= sim.tb:
            state["push"] = False
            state["bottoms"].append(t)
        return len(state["bottoms"]) >= cycles
    sim.log_max = {}
    sim.run(thk0, thh0, T=1.5, finger=finger, events=ev)
    b = state["bottoms"]
    per = [(b[i + 1] - b[i]) for i in range(len(b) - 1)]
    tail = per[-3:] if len(per) >= 3 else per
    return (sum(tail) / len(tail)) if tail else float("nan"), state


def strike(sim, F_peak, t_push=0.030, T=0.12):
    """finger force F_peak (N) from rest until 8 ms after the key reaches the felt, then a light 2 N hold."""
    thk0, thh0 = rest_state(sim)
    rec = dict(t_bottom=None)

    def finger(t, s):
        if rec["t_bottom"] is None:
            return F_peak
        return F_peak if t < rec["t_bottom"] + 0.008 else 2.0

    def ev(t, s):
        if rec["t_bottom"] is None and s["thk"] >= sim.tb:
            rec["t_bottom"] = t
            rec["v_key"] = s["wk"] * (sim.Ok[0] - sim.yf)
            rec["v_ham_nose"] = s["wh"] * sim.r_nose
        return False
    sim.log_max = {}
    st, hist = sim.run(thk0, thh0, T=T, finger=finger, events=ev)
    rec.update({k: v for k, v in sim.log_max.items()})
    # top of the weight at the peak hammer angle
    thh_max = max(h[3] for h in hist)
    Oh = sim.Oh
    rec["thh_peak"] = thh_max
    rec["weight_top_peak"] = max(rot(p, Oh, thh_max)[1] for _, poly, *_ in hammer_polys(sim.Q, sim.G_, sim.black) for p in poly)
    rec["hist"] = hist
    return rec




# ------------------------------------------------------------------ section stresses (rest)
def u_section(b_top, t_top, h, t_wall):
    """open-bottom U channel: returns (I, y_max) about its neutral axis (mm^4, mm)."""
    parts = [(b_top * t_top, h - t_top / 2, b_top * t_top ** 3 / 12),
             (2 * t_wall * (h - t_top), (h - t_top) / 2, 2 * t_wall * (h - t_top) ** 3 / 12)]
    A = sum(p[0] for p in parts)
    zc = sum(p[0] * p[1] for p in parts) / A
    I = sum(p[2] + p[0] * (p[1] - zc) ** 2 for p in parts)
    return I, max(zc, h - zc)


def key_bending(Q, G_, black):
    """bending moment along the key at rest (no finger): parts' weights, hook, pad contact; M at sections."""
    K = black_key(Q, G_) if black else white_key(Q, G_)
    st = statics(Q, G_, black, 0.0, 0, mu=False)
    kp = st["kp"]
    Ok = Q["pk"]
    # hook force from key moment balance with F = 0
    r_hook = Ok[0] - 0.5 * (Q["tab_y"][0] + Q["tab_y"][1])
    tau_g = -kp["m"] * GF * (kp["com"][0] - Ok[0])
    tau_c = cross((st["Pc"][0] - Ok[0], st["Pc"][1] - Ok[1]), st["Fc"])
    H = -(tau_g + tau_c) / r_hook          # N, downward on the key at the hook (>0 means the key presses up)
    loads = [(0.5 * (Q["tab_y"][0] + Q["tab_y"][1]), -H), (st["Pc"][0], st["Fc"][1])]
    for name, poly, t, rho, fill in K.parts:
        A, (cy, cz), _ = poly_props(poly)
        loads.append((cy, -A * t * rho * fill / 1000 * GF))
    res = {}
    for ys in (60.0, 100.0, 120.0, 150.0, 160.0):
        res[ys] = sum(F * (ys - y) for y, F in loads if y < ys)
    return H, res


def rest_stresses(Q, G_):
    out = {}
    for black in (False, True):
        tag = "black" if black else "white"
        H, M = key_bending(Q, G_, black)
        if black:
            I, c = u_section(11.0, Q["skin_b"], Q["z_top_b"] - Q["z_bot"], Q["wall"])
        else:
            I, c = u_section(12.72, Q["skin_w"], Q["z_top_w"] - Q["z_bot"], Q["wall"])
        Mmax = max(abs(v) for v in M.values())
        out[tag + " key body (U channel), max |M| %.1f N mm" % Mmax] = Mmax * c / I
        out[tag + " hook force on tab (N)"] = H
        st = statics(Q, G_, black, 0.0, 0, mu=False)
        # lug post: horizontal pad force x post length (C.z .. ceiling) on a 7 x 6 section
        C = G_["Cb"] if black else G_["Cw"]
        ceil = (Q["z_top_b"] - Q["skin_b"]) if black else (Q["z_top_w"] - Q["skin_w"])
        Lp = ceil - C[1]
        out[tag + " lug post (horizontal pad force x %.1f mm)" % Lp] = abs(st["Fc"][0]) * Lp / (7.0 * 6.0 ** 2 / 6)
        # key tongue: rod reaction x 8 mm lever on 8 x 7 minus slot (take 8 x 4 net)
        out[tag + " key tongue (rod reaction %.2f N)" % math.hypot(*st["Rk"])] = math.hypot(*st["Rk"]) * 8.0 / (8.0 * 4.0 ** 2 / 6)
        # frame tab: hook force x 17.5 mm on 7.5 (x) x 7 (y)
        out[tag + " frame guide tab/hook"] = H * 17.5 / (7.5 * 7.0 ** 2 / 6)
        # hammer rear arm root (y_ph+8): weight of everything behind it
        Hm = hammer(Q, G_, black)
        Oh = (Q["y_ph"], Q["z_ph"])
        yroot = Oh[0] + Q["boss_half"]
        Mr = 0.0
        for name, poly, t, rho, fill in Hm.parts:
            A, (cy, cz), _ = poly_props(poly)
            if cy > yroot:
                Mr += A * t * rho * fill / 1000 * GF * (cy - yroot)
        out[tag + " hammer rear-arm root (6 x 7)"] = Mr / (Q["w_arm"] * Q["h_arm"] ** 2 / 6)
        # hammer front arm at the boss: pad force x lever on 8 x 8
        Mf = st["N_g"] * GF * (Oh[0] - Q["boss_half"] - st["Pc"][0])
        out[tag + " hammer front-arm root (8 x 8)"] = Mf / (Q["w_nose"] * Q["boss_h"] ** 2 / 6)
        # block glue shear (steel block held by epoxy in the ring side walls)
        blk = Hm.props(only=lambda n: n == "steel block")["m"] * GF
        out[tag + " block epoxy shear (MPa)"] = blk / (2 * Q["blk_L"] * (Q["blk_h_b"] if (black and Q.get("blk_h_b")) else Q["blk_h"]))
    return out


# ------------------------------------------------------------------ SVG side view
def write_svg(Q, G_, path):
    sc, ox, oy = 4.0, 20.0, 20.0
    W, Hh = 240 * sc, 75 * sc

    def P2(p):
        return (ox + p[0] * sc, oy + (70 - p[1]) * sc)

    def poly(pts, cls, dash=False):
        s = " ".join("%.1f,%.1f" % P2(p) for p in pts)
        return '<polygon points="%s" class="%s"%s/>' % (s, cls, ' stroke-dasharray="4 3"' if dash else "")
    el = []
    zf = Q["z_floor"]
    el.append(poly(rect(0, 212, 0, zf), "fix"))
    el.append(poly(rect(Q["bar_y"][0], Q["bar_y"][1], 8.6, Q["bar_top_w"]), "fix"))
    el.append(poly(rect(Q["tab_y"][0], Q["tab_y"][1], zf, Q["hook_under"] + 1.4), "fix"))
    el.append(poly(rect(1.5, 10.5, 10.5, 14.0), "felt"))
    el.append(poly(key_fin(Q), "fix"))
    el.append(poly(rect(Q["y_w0"] - 1.6, 209, 13.5, 14.7), "fix"))                       # board ledge
    el.append(poly(rect(181, 209, 7.0, 8.6), "pcb"))                                     # control board
    el.append(poly(rect(Q["y_w0"] - 4, 209, Q["stop_face"] + Q["stop_felt_t"], Q["cover_under"]), "fix"))  # stop rail
    el.append(poly(rect(Q["y_w0"] - 4, 209, Q["stop_face"], Q["stop_face"] + Q["stop_felt_t"]), "felt"))
    el.append(poly(rect(146, 212, Q["cover_under"], Q["cover_top"]), "fix"))
    el.append(poly(rect(209, 212, zf, Q["cover_under"]), "fix"))
    Ok, Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
    for black, cls in ((False, "key"),):
        K = white_key(Q, G_)
        for th_k, dash in ((0.0, False), (Q["tb_w"], True)):
            thh = th_h_of(Q, G_, False, th_k)
            for name, pg, *_ in K.parts:
                el.append(poly([rot(p, Ok, th_k) for p in pg], cls, dash))
            for name, pg, *_ in hammer_polys(Q, G_, False):
                el.append(poly([rot(p, Oh, thh) for p in pg], "steel" if name == "steel block" else "ham", dash))
    for c in (Ok, Oh):
        x, y = P2(c)
        el.append('<circle cx="%.1f" cy="%.1f" r="%.1f" class="rod"/>' % (x, y, 1.5 * sc))
    css = ("<style>.fix{fill:#d8d8d8;stroke:#666;stroke-width:.6}.felt{fill:#e8a44a;stroke:#a86a1a;stroke-width:.5}"
           ".key{fill:none;stroke:#222;stroke-width:.8}.ham{fill:none;stroke:#1f5fbf;stroke-width:.9}"
           ".steel{fill:#9aa4b0;fill-opacity:.35;stroke:#3a4450;stroke-width:.9}.pcb{fill:#2e8b57;stroke:#1d5e3a}"
           ".rod{fill:#333}text{font:11px sans-serif}</style>")
    lab = ('<text x="20" y="14">H1 white key (D section), rest = solid, full dip = dashed. 1 mm = %d px. '
           'Key rod (171,40), hammer rod (%.1f,%.1f)</text>' % (sc, Oh[0], Oh[1]))
    open(path, "w").write('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s%s%s</svg>'
                          % (W + 40, Hh + 40, W + 40, Hh + 40, css, lab, "".join(el)))


def plot_side(Q, G_, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Circle
    fig, axs = plt.subplots(2, 1, figsize=(15, 10.5))
    Ok, Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
    zf = Q["z_floor"]
    for ax, black in zip(axs, (False, True)):
        def add(pts, fc="none", ec="k", lw=0.8, ls="-", alpha=1.0, z=1):
            ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, ls=ls, alpha=alpha, zorder=z))
        # fixed parts
        add(rect(0, 212, 0, 3), "#bbbbbb", "#777")
        add(rect(0, 212, 3, zf), "#d9d9d9", "#777")
        add(rect(1.5, 10.5, 10.55, 10.55 + 3.0), "#e8a44a", "#a86a1a")                   # white front felt
        add(rect(51.5, 58.7, 10.8, 10.8 + 3.0), "#e8a44a", "#a86a1a")                    # black stop felt
        add(rect(Q["bar_y"][0], Q["bar_y"][1], 8.6, Q["bar_top_b"] if black else Q["bar_top_w"]), "#d9d9d9", "#777")
        add(rect(59.0, 77.5, 7.0, 8.6), "#2e8b57", "#1d5e3a")
        add(rect(Q["tab_y"][0], Q["tab_y"][1], zf, Q["hook_under"] + 1.4), "#d9d9d9", "#777")
        add(rect(Q["tab_y"][0], Q["tab_y"][1], Q["hook_felt_bot"], Q["hook_under"]), "#e8a44a", "#a86a1a", z=3)
        add(key_fin(Q), "#d9d9d9", "#777")
        yh0, yh1 = Oh[0] - Q["boss_half"] - 1.0, Oh[0] + Q["boss_half"] + 1.0
        add([(yh0, zf), (yh1, zf), (yh1, Oh[1] + 1.0), (Oh[0] + 2.5, Oh[1] + 3.5), (Oh[0] - 2.5, Oh[1] + 3.5), (yh0, Oh[1] + 1.0)],
            "#d9d9d9", "#777")                                                             # hammer comb fin
        add(rect(Q["y_w0"] - 1.6, 209, 13.5, 14.7), "#d9d9d9", "#777")                   # board ledge
        add(rect(Q["y_w0"] - 1.6, 209, 14.7, 15.7), "#e8a44a", "#a86a1a")                # ledge felt 1T
        add(rect(181, 209, 7.0, 8.6), "#2e8b57", "#1d5e3a")                              # control board
        add(rect(186, 209, 8.6, 13.0), "#2e8b57", "#1d5e3a", alpha=0.4)                  # board parts <= z13
        add(rect(Q["y_w0"] - 4, 209, Q["stop_face"] + Q["stop_felt_t"], Q["cover_under"]), "#d9d9d9", "#777")
        add(rect(Q["y_w0"] - 4, 209, Q["stop_face"], Q["stop_face"] + Q["stop_felt_t"]), "#e8a44a", "#a86a1a")
        add(rect(146, 212, Q["cover_under"], Q["cover_top"]), "#d9d9d9", "#777")
        add(rect(209, 212, zf, Q["cover_under"]), "#d9d9d9", "#777")
        K = black_key(Q, G_) if black else white_key(Q, G_)
        tb = Q["tb_b"] if black else Q["tb_w"]
        for th_k, ls, al in ((0.0, "-", 1.0), (tb, "--", 0.8)):
            thh = th_h_of(Q, G_, black, th_k)
            for name, pg, *_ in K.parts:
                add([rot(p, Ok, th_k) for p in pg], "#fafafa" if (ls == "-" and not black) else ("#303030" if (ls == "-" and black) else "none"),
                    "#111" if not black else "#555", 0.7, ls, 0.35 if black and ls == "-" else al, z=4)
            for name, pg, *_ in hammer_polys(Q, G_, black):
                fc = "#8a96a3" if name == "steel block" else ("#9ec3ff" if ls == "-" else "none")
                add([rot(p, Oh, thh) for p in pg], fc, "#1f5fbf", 0.9, ls, 0.55 if ls == "-" else 0.9, z=5)
        for c in (Ok, Oh):
            ax.add_patch(Circle(c, 1.5, fc="#222", zorder=7))
        ax.set_xlim(-3, 215)
        ax.set_ylim(-2, 70)
        ax.set_aspect("equal")
        ax.set_xticks(range(0, 215, 10))
        ax.set_yticks(range(0, 71, 10))
        ax.grid(alpha=0.25)
        ax.set_xlabel("y (mm, from white key front lip)")
        ax.set_ylabel("z (mm, desk = 0)")
        ax.set_title(("black key (C#) section" if black else "white key (D) section") +
                     " - solid = rest, dashed = full dip.  key rod (%.0f, %.0f)  hammer rod (%.1f, %.1f)"
                     % (Ok[0], Ok[1], Oh[0], Oh[1]), fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


# ------------------------------------------------------------------ report
def spring_option(Q, frac=0.6):
    """optional assist spring: a soft SUS compression spring in a Ø5 pocket through the stop rail, its lower end
    (with a 0.5T felt disc) protruding below the stop felt; it touches the weight block top only in the last
    (1 - frac) of the hammer stroke, so it carries zero load at rest.  k = G d^4 / (8 D^3 n), G = 69 GPa."""
    d, Dout, n = 0.25, 4.0, 18
    k = 69000.0 * d ** 4 / (8 * (Dout - d) ** 3 * n)
    r = Q["r_stop"]
    engage = frac * Q["th_hb"]
    protrude = (Q["th_stop"] - engage) * r                 # below the stop felt face
    comp_max = (Q["th_hmax"] - engage) * r
    L0 = 12.5
    return dict(k=k, r=r, engage=engage, d=d, D_out=Dout, n=n, L0=L0, solid=(n + 2) * d, protrude=protrude,
                comp_max=comp_max, frac=frac)


def main(out=print):
    Q, G_ = complete(P)
    Ok, Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
    W, B = False, True
    R = {}                                           # collected metrics
    hr = lambda s: out("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)
    hr("0. DESIGN PARAMETERS (input) AND SOLVED GEOMETRY")
    for k in ("pk", "rod_d", "y_cb", "y_cw", "z_pc", "alpha_deg", "R_lug", "t_pad", "z_ph", "blk_w", "blk_L", "y_w0",
              "ledge_face", "rest_gap", "cover_top", "cover_t", "rail_t", "stop_felt_t", "stop_gap", "stop_dff",
              "mu_pin", "mu_pad", "guide_drag_g"):
        out("  %-14s = %s" % (k, Q[k]))
    out("  solved: hammer rod y_ph = %.2f (white & black turn the hammer by the same angle), z_ph = %.1f" % Oh)
    out("  solved: key bottom angle white %.5f rad (%.3f deg), black %.5f rad (%.3f deg)" % (
        Q["tb_w"], math.degrees(Q["tb_w"]), Q["tb_b"], math.degrees(Q["tb_b"])))
    out("  solved: hammer angle at key bottom %.4f rad (%.2f deg) for BOTH colours" % (Q["th_hb"], math.degrees(Q["th_hb"])))
    out("  solved: weight block height (cut length of 9x25 flat bar) white %.1f mm, black %.1f mm on a %.1f mm PETG shim"
        % (Q["blk_h"], Q["blk_h_b"], Q["blk_h"] - Q["blk_h_b"]))
    out("  stop-rail felt face z %.2f (cover top %.1f - cover %.1f - rail %.1f - felt %.1f); lever of the stop r = %.1f mm"
        % (Q["stop_face"], Q["cover_top"], Q["cover_t"], Q["rail_t"], Q["stop_felt_t"], Q["r_stop"]))

    hr("1. MASSES AND INERTIAS (explicit polygons x thickness; I about own pivot incl. parallel-axis terms)")
    for black in (W, B):
        K = black_key(Q, G_) if black else white_key(Q, G_)
        H = hammer(Q, G_, black)
        kp, hp = K.props(), H.props()
        tag = "black" if black else "white"
        out("  %s key : m = %.2f g, COM (y %.1f, z %.1f), I_pivot = %.0f g mm^2 (radius of gyration %.1f mm)" % (
            tag, kp["m"], kp["com"][0], kp["com"][1], kp["I"], math.sqrt(kp["I"] / kp["m"])))
        for name, poly, t, rho, fill in K.parts:
            A, c, _ = poly_props(poly)
            out("      %-22s %6.2f g  at y %6.1f" % (name, A * t * rho * fill / 1000, c[0]))
        out("  %s hammer: m = %.2f g (steel %.2f g), COM (y %.1f, z %.1f), I_pivot = %.0f g mm^2" % (
            tag, hp["m"], H.props(only=lambda n: n == "steel block")["m"], hp["com"][0], hp["com"][1], hp["I"]))
        for name, poly, t, rho, fill in H.parts:
            A, c, _ = poly_props(poly)
            out("      %-22s %6.2f g  at y %6.1f  (x width %.1f)" % (name, A * t * rho * fill / 1000, c[0], t))
        R["key_g_" + tag] = kp["m"]
        R["ham_g_" + tag] = hp["m"]
        R["steel_g_" + tag] = H.props(only=lambda n: n == "steel block")["m"]

    hr("2. KINEMATICS")
    for black in (W, B):
        tag = "black" if black else "white"
        tb = Q["tb_b"] if black else Q["tb_w"]
        H = hammer(Q, G_, black)
        blk = H.props(only=lambda n: n == "steel block")["com"]
        yf = Q["y_f_b"] if black else Q["y_f_w"]
        ztop = Q["z_top_b"] if black else Q["z_top_w"]
        s_f = ztop - rot((yf, ztop), Ok, tb)[1]
        rise = rot(blk, Oh, Q["th_hb"])[1] - blk[1]
        r0 = statics(Q, G_, black, 0.0, 0)["ratio"]
        r1 = statics(Q, G_, black, tb, 0)["ratio"]
        out("  %s: finger point y%.1f travel %.2f mm; steel COM rises %.2f mm -> displacement ratio R = %.2f;"
            " hammer/key angular ratio %.2f (rest) .. %.2f (bottom)" % (tag, yf, s_f, rise, rise / s_f, r0, r1))
        R["R_" + tag] = rise / s_f
        pcs = [statics(Q, G_, black, f * tb, 0)["Pc"] for f in (0.0, 1.0)]
        slip = statics(Q, G_, black, 0.5 * tb, 0)["slip_per_rad"] * tb
        out("      lug contact point rest (%.2f, %.2f) -> bottom (%.2f, %.2f); pad sliding per stroke %.2f mm" % (
            pcs[0][0], pcs[0][1], pcs[1][0], pcs[1][1], slip))
        out("      lug/pad normal force (hammer preload on the key) rest %.2f N, bottom %.2f N" % (
            statics(Q, G_, black, 0.0, 0)["N_g"] * GF, statics(Q, G_, black, tb, 0)["N_g"] * GF))
        fx = [statics(Q, G_, black, f * tb, 0)["fx_key"] for f in (0.0, 0.5, 1.0)]
        out("      horizontal pad force on the key (+ = pushes key onto its rod slot) rest/mid/bottom: %s N" %
            ", ".join("%.3f" % v for v in fx))

    hr("3. STATIC FORCES AT THE KEY (gf).  BW = frictionless balance, DW = start moving down, UW = rising slowly")
    for black in (W, B):
        tag = "black" if black else "white"
        tb = Q["tb_b"] if black else Q["tb_w"]
        pts = (52.5, 62.5) if black else (0.0, 13.0, 90.0)
        for yf in pts:
            bw = statics(Q, G_, black, 1e-4, 0, y_f=yf)["F_g"]
            dw = statics(Q, G_, black, 1e-4, 1, y_f=yf)["F_g"]
            uw = statics(Q, G_, black, 0.003, -1, y_f=yf)["F_g"]
            out("  %s at y%-5.1f: BW %.1f  DW %.1f  UW %.1f  friction (DW-UW)/2 = %.1f" % (tag, yf, bw, dw, uw, (dw - uw) / 2))
            R["DW_%s_%g" % (tag, yf)], R["UW_%s_%g" % (tag, yf)], R["BW_%s_%g" % (tag, yf)] = dw, uw, bw
        prof = [statics(Q, G_, black, f * tb, 0)["F_g"] for f in (0, 0.25, 0.5, 0.75, 1.0)]
        out("  %s balance force over the stroke (0/25/50/75/100 %%): %s" % (tag, " ".join("%.1f" % v for v in prof)))
        # friction breakdown at the finger point
        base = statics(Q, G_, black, 1e-4, 0)["F_g"]
        for lab, qq in (("key+hammer pins (mu %.2f)" % Q["mu_pin"], dict(Q, mu_pad=0, guide_drag_g=0)),
                        ("lug/pad sliding (mu %.2f)" % Q["mu_pad"], dict(Q, mu_pin=0, guide_drag_g=0)),
                        ("guide bushing (%.1f g drag)" % Q["guide_drag_g"], dict(Q, mu_pin=0, mu_pad=0))):
            out("      friction share %-30s %.2f g" % (lab, statics(qq, G_, black, 1e-4, 1)["F_g"] - base))
        for mu in (0.10, 0.25, 0.35):
            q2 = dict(Q, mu_pad=mu)
            out("      sensitivity mu_pad %.2f: DW %.1f UW %.1f" % (mu, statics(q2, G_, black, 1e-4, 1)["F_g"],
                                                                   statics(q2, G_, black, 0.003, -1)["F_g"]))
    R["fb_ratio"] = R["DW_white_90"] / R["DW_white_13"]
    out("  front/back ratio F(y90)/F(y13) (DW) = %.2f   (lever ratio (171-13)/(171-90) = %.2f)" % (
        R["fb_ratio"], (Ok[0] - 13) / (Ok[0] - 90)))

    hr("4. EFFECTIVE (INERTIAL) MASS AT THE KEY  m_eff = (I_key + I_hammer * (dth_h/dth_k)^2) / lever^2")
    for black in (W, B):
        tag = "black" if black else "white"
        tb = Q["tb_b"] if black else Q["tb_w"]
        pts = (52.5, 62.5) if black else (0.0, 13.0)
        for yf in pts:
            vals = [m_eff(Q, G_, black, f * tb, yf)[0] for f in (0.0, 0.5, 1.0)]
            out("  %s at y%-5.1f: rest %.1f g, mid %.1f g, bottom %.1f g" % (tag, yf, *vals))
            R["meff_%s_%g" % (tag, yf)] = vals[1]
        K = black_key(Q, G_) if black else white_key(Q, G_)
        yf = Q["y_f_b"] if black else Q["y_f_w"]
        out("      key alone contributes %.1f g at y%.1f" % (K.props()["I"] / (Ok[0] - yf) ** 2, yf))

    hr("5. DYNAMICS (2 bodies, unilateral felt contacts, Coulomb friction, dt = 2 us)")
    out("  felt: E0 = %.2f MPa (v3 S17 back-calculation), x5 stiffer at 50 %% strain, damping ratio %.2f" % (E_FELT, ZETA))
    sp = spring_option(Q)
    for black in (W, B):
        tag = "black" if black else "white"
        s = Sim(Q, G_, black)
        out("  %s contact stiffness k1 (N/mm): %s" % (tag, ", ".join("%s %.1f" % (k, v[0]) for k, v in s.felt.items())))
        th0 = rest_state(Sim(Q, G_, black))
        out("  %s static rest: key %.5f rad (hook felt %.2f mm), hammer %.5f rad" % (
            tag, th0[0], -th0[0] * s.r_hook, th0[1]))
        for lab, spring in (("no spring", None), ("assist spring", sp)):
            r = release_from_bottom(Sim(Q, G_, black, spring=spring))
            out("  %s release from bottom, %-13s: 40 %% re-trigger %.1f ms, full return %.1f ms, top speed %.0f mm/s,"
                " hook impact %.2f mJ, rebound %.2f mm, max lug/pad gap %.3f mm" % (
                    tag, lab, r["t_trig"] * 1e3, r["t_full"] * 1e3, -r["v_top"], r["E_hook_mJ"], r["bounce_mm"], max(0.0, r["sep_max"])))
            key = "" if spring is None else "_spring"
            R["t40_%s%s" % (tag, key)], R["tfull_%s%s" % (tag, key)] = r["t_trig"] * 1e3, r["t_full"] * 1e3
            if spring is None:
                R["E_hook_" + tag] = r["E_hook_mJ"]
        for lab, spring in (("no spring", None), ("assist spring", sp)):
            rates = []
            for F in (1.0, 1.5, 2.0, 3.0):
                per, _ = repetition(Sim(Q, G_, black, spring=spring), F)
                rates.append(1 / per)
            out("  %s repetition (release at felt, re-press at 40 %% rise with constant finger force 1.0/1.5/2.0/3.0 N), %-13s:"
                " %s Hz" % (tag, lab, " / ".join("%.1f" % v for v in rates)))
            if spring is None:
                R["hz_%s_1.5" % tag], R["hz_%s_2.0" % tag] = rates[1], rates[2]
        for F in (1.0, 3.0, 6.0, 10.0):
            k = strike(Sim(Q, G_, black), F)
            out("  %s strike, finger %4.1f N: key speed at felt %.2f m/s | front felt %.2f mm / %.0f N | weight stop felt %.2f mm / %.0f N"
                " | lug-pad separation %.2f mm | weight top peak z %.2f (rail PETG at %.2f)" % (
                    tag, F, k["v_key"] / 1000, k["d_front"], k["F_front"], k["d_nose"], k["F_nose"], max(0, k["gap_pad"]),
                    k["weight_top_peak"], Q["stop_face"] + Q["stop_felt_t"]))
            R["strike_%s_%g" % (tag, F)] = k
    base_top = Q["stop_face"] - sp["protrude"] + sp["L0"]
    out("  assist spring (option): SUS d %.2f / OD %.1f / %d coils / L0 %.1f / solid %.1f -> k %.4f N/mm, in a Ø5 pocket through"
        " the stop rail (spring top z%.1f <= rail top z%.1f); tip %.1f mm below the stop felt, touches the block only after"
        " %.0f %% of the hammer stroke (zero load at rest); max compression %.2f mm at ff (< L0 - solid %.2f)" % (
            sp["d"], sp["D_out"], sp["n"], sp["L0"], sp["solid"], sp["k"], base_top, Q["cover_under"], sp["protrude"],
            100 * sp["frac"], sp["comp_max"], sp["L0"] - sp["solid"]))
    R["spring"] = sp
    for black in (W, B):
        tag = "black" if black else "white"
        tb = Q["tb_b"] if black else Q["tb_w"]
        dF = statics(Q, G_, black, tb, 0)["F_g"]
        # spring torque at full dip reflected to the finger point via the hammer/key ratio
        st = statics(Q, G_, black, tb, 0, mu=False)
        extra = sp["k"] * (Q["th_hb"] - sp["engage"]) * sp["r"] * sp["r"] * st["ratio"] / st["lever"] / GF
        out("      %s: balance force at full dip %.1f g without, %.1f g with the spring" % (tag, dF, dF + extra))
        R["spring_dF_" + tag] = extra
    # v2.0 claim check
    t_ideal = math.sqrt(2 * 0.010 / G) * 1e3
    out("  v2.0 claim check: an ideal massless-key seesaw with R = 1 accelerates at g/R -> 10 mm full return %.1f ms,"
        " 40 %% rise %.1f ms.  True: the full-return time is set by R (and friction), not by the mass; but the"
        " re-trigger needs only the 40 %% rise, and here the simulated 40 %% rise is %.1f ms (white)." % (
            t_ideal, math.sqrt(2 * 0.004 / G) * 1e3, R["t40_white"]))
    return report2(Q, G_, R, out)


PURCHASE = [  # item, spec, qty_88, unit_krw, source, note
    ("SUS304 연마봉 Ø3 × 1 m", "건반 축·해머 축 (모듈 2 × 164 mm ×7 + 끝 부속 4개)", 3, 9600,
     "배관몰 baegwan.net/goods/view?no=4356 (Φ3×1M 9,600원, 착불 배송비 별도 — 배송 4,000원 추정)", "verified 2026-09-27"),
    ("착불 배송비 (환봉)", "택배", 1, 4000, "estimate", "estimate"),
    ("평철 SS400 9 × 25, 1 m", "무게추 블록: 백건 24 mm × 52 + 흑건 22 mm × 36 + 톱날 1.5 mm", 3, 6000,
     "원자재닷컴/철물점 소량 절단 판매 (가격 확인 못 함)", "estimate"),
    ("평철 배송비", "택배", 1, 4000, "estimate", "estimate"),
    ("5분 에폭시 (2액형, 소형)", "무게추 블록을 링에 고정", 1, 3500, "다이소/철물점", "estimate"),
    ("흑연 가루 (건식 윤활제, 소형)", "러그-패드 펠트 마찰 μ 0.25 → 0.15", 1, 3000, "철물점/자물쇠 윤활용", "estimate"),
    ("스텐 유두 렌치볼트 M3 × 10 (추가)", "스톱 레일 3 + 선반 판 2 / 모듈, 끝 부속 포함 40개", 40, 60,
     "굿나잇몰 11st.co.kr/products/4236198413 (v3 L 같은 줄 단가 60원)", "v3 BOM unit price"),
]
REMOVED = [  # v3 lines no longer needed (from docs/report/toccata-purchase-list.xlsx)
    ("스텐 유두 렌치볼트 M3 × 40 (클램프)", 34, 130, "척추 클램프 없음"),
    ("스텐 무두 렌치볼트 M3 × 10 (세트스크루)", 40, 60, "척추 세트스크루 없음"),
    ("황동 라운드 디스크 Ø8×1 (10개 팩)", 4, 2669, "세트스크루 받침 없음"),
    ("스텐 와셔 M4×9×0.5 (클램프용 32개분)", 32, 10, "고무발용 14개만 남김"),
    ("M3 육각너트 (레일 클램프 + 세트스크루 63개분)", 63, 11, "스톱 레일·선반 판 나사는 PETG에 직결 탭, 스피커 브래킷 4개분만 남김"),
]


def report2(Q, G_, R, out):
    Ok, Oh = Q["pk"], (Q["y_ph"], Q["z_ph"])
    hr = lambda s: out("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)
    hr("6. SENSOR (v3 sensor bar, element row y67, key magnet Ø5x2 on the key underside)")
    for black in (False, True):
        tag = "black" if black else "white"
        s = sensor(Q, black)
        out("  %s: magnet face -> element rest %.2f, bottom %.2f mm; magnet travel %.2f mm (shifts +%.2f in y);"
            " bottom gap boss/sensor top %.2f mm, key underside/bar %.2f mm" % (
                tag, s["rest_face_elem"], s["bottom_face_elem"], s["travel"], s["y_shift"], s["bottom_boss_sensor"], s["bottom_under_bar"]))
        R["sensor_" + tag] = s
        out("      v3 for comparison: rest %.2f, bottom %.2f (S45/S46) -> unchanged because the key rod sits on v3's"
            " instantaneous centre" % ((10.82, 4.70) if not black else (13.35, 4.90)))

    hr("7. CLEARANCES OVER THE STROKE (rest -> full dip + %.1f mm ff felt compression at the stop)" % Q["stop_dff"])
    allc = []
    for black in (False, True):
        c = clearances(Q, G_, black)
        tag = "black" if black else "white"
        for k, v in c.items():
            if v < 1e8:
                out("  %s %-12s %.2f mm" % (tag, k, v))
                if k != "stop_rail":
                    allc.append(v)
    R["min_clear"] = min(allc)
    # lateral: hammer yaw in its comb (0.2 per side over 16 mm boss) at the block centre vs neighbour
    yaw = 2 * Q["fin_cl"] / (2 * Q["boss_half"])
    b_blk = Q["y_w0"] + Q["blk_L"] / 2 - Oh[0]
    lat = 0.5 * yaw * b_blk
    pitch_min = 13.214
    ringw = Q["blk_w"] + 2 * Q["ring_side"]
    out("  lateral: hammer yaw play +/-%.4f rad -> +/-%.2f mm at the block; worst gap between neighbouring rings"
        " %.2f - %.2f - 2 x %.2f = %.2f mm" % (0.5 * yaw, lat, pitch_min, ringw, lat, pitch_min - ringw - 2 * lat))
    R["lat_gap"] = pitch_min - ringw - 2 * lat

    hr("8. COORDINATE TABLE (y, z) mm - design rest (felts just touching) and full dip (front felt first contact)")
    for black in (False, True):
        tag = "BLACK (C#)" if black else "WHITE (D)"
        tb = Q["tb_b"] if black else Q["tb_w"]
        thh_b = th_h_of(Q, G_, black, tb)
        K = black_key(Q, G_) if black else white_key(Q, G_)
        H = hammer(Q, G_, black)
        blk = [p for n, pg, *_ in hammer_polys(Q, G_, black) if n == "steel block" for p in pg]
        C = G_["Cb"] if black else G_["Cw"]
        st0 = statics(Q, G_, black, 0.0, 0)
        st1 = statics(Q, G_, black, tb, 0)
        rows = [
            ("key rod centre (fixed)", Ok, None, "Ø3 SUS304 through 24 fins"),
            ("hammer rod centre (fixed)", Oh, None, "Ø3 SUS304 through 24 fins"),
            ("key top front edge", (52.5, 55.5) if black else (0.0, 43.5), "k", "dip %.1f" % (9.5 if black else 10.0)),
            ("finger point (DW)", (62.5, 55.5) if black else (13.0, 43.5), "k", ""),
            ("front down-stop contact", ((55.85, 23.5) if black else (6.6, 23.5)), "k", "felt 3T on v3 rail"),
            ("crossbar top = hook contact", (87.5, 25.1), "k", "felt 3T under hook z25.1-28.1"),
            ("magnet face centre", ((64.2 if black else 65.8), 23.5), "k", "sensor element y67"),
            ("lug centre (R3)", C, "k", "lug hangs from the key"),
            ("key COM", K.props()["com"], "k", "%.1f g" % K.props()["m"]),
            ("hammer COM", H.props()["com"], "h", "%.1f g" % H.props()["m"]),
            ("steel block centroid", H.props(only=lambda n: n == "steel block")["com"], "h",
             "%.1f g" % H.props(only=lambda n: n == "steel block")["m"]),
            ("steel block bottom-front", blk[0], "h", ""),
            ("steel block top-front", blk[3], "h", ""),
            ("steel block top-rear", blk[2], "h", "highest point"),
            ("steel block bottom-rear", blk[1], "h", ""),
        ]
        out("  %s   (key angle bottom %.5f rad, hammer %.5f rad)" % (tag, tb, thh_b))
        out("  %-30s %-18s %-18s %s" % ("point", "rest (y, z)", "full dip (y, z)", "note"))
        for name, p, body, note in rows:
            if body is None:
                q = p
            elif body == "k":
                q = rot(p, Ok, tb)
            else:
                q = rot(p, Oh, thh_b)
            out("  %-30s (%7.2f, %6.2f)  (%7.2f, %6.2f)  %s" % (name, p[0], p[1], q[0], q[1], note))
        out("  %-30s (%7.2f, %6.2f)  (%7.2f, %6.2f)  %s" % ("lug/pad contact point", st0["Pc"][0], st0["Pc"][1],
                                                           st1["Pc"][0], st1["Pc"][1], "pad = felt 1T on the hammer nose"))
    out("  fixed: stop-rail felt face z%.2f (y%.1f-209), ledge felt face z%.2f (y%.1f-209), hook underside z%.1f (y%.0f-%.0f),"
        " floor z%.1f, cover z%.1f-%.1f" % (Q["stop_face"], Q["y_w0"] - 4, Q["ledge_face"], Q["y_w0"] - 1.6, Q["hook_under"],
                                           Q["tab_y"][0], Q["tab_y"][1], Q["z_floor"], Q["cover_under"], Q["cover_top"]))
    out("  hammer outline at rest (world y, z):")
    for n, pg, t, rho, f in hammer_polys(Q, G_, False):
        out("    %-12s w%4.1f: %s" % (n, t, " ".join("(%.1f,%.1f)" % p for p in pg)))

    hr("9. STRESS IN PLASTIC AT REST (MPa) - target < 2")
    rs = rest_stresses(Q, G_)
    mx = 0.0
    for k, v in rs.items():
        out("  %-62s %.4f" % (k, v))
        if "force" not in k:
            mx = max(mx, v)
    R["max_rest_stress"] = mx
    out("  -> max %.2f MPa.  No part is preloaded: pivots are steel rods, the rest position is the hook felt, held by gravity." % mx)
    for F in (6.0, 10.0):
        k = R["strike_white_%g" % F]
        a = Q["rear_wall"][0] - (Oh[0] + Q["r_stop"])
        sig = 6 * k["F_nose"] * a / (40.0 * Q["rail_t"] ** 2)
        out("  transient: stop rail (t %.1f, effective width 40 mm, lever %.1f mm) at finger %.0f N -> %.0f N -> %.1f MPa" % (
            Q["rail_t"], a, F, k["F_nose"], sig))
        R["rail_sigma_%g" % F] = sig

    hr("10. ENVELOPE")
    zs_min, zs_max = 1e9, -1e9
    for black in (False, True):
        for th in (-0.01, Q["th_hmax"]):
            for n, pg, *_ in hammer_polys(Q, G_, black):
                for p in pg:
                    z = rot(p, Oh, th)[1]
                    zs_min, zs_max = min(zs_min, z), max(zs_max, z)
    R["max_z_moving"], R["min_z_moving"] = zs_max, zs_min
    out("  depth used y0 - y%.1f (hammer ring rear), rear wall y209-212 -> frame 212 (unchanged), instrument 212 + 3 + 195 = 410" % (
        Q["y_w0"] + Q["blk_L"] + Q["ring_back"]))
    out("  white key top z43.5, black z55.5 (unchanged); highest moving point z%.2f (weight at ff), lowest z%.2f (hammer nose)" % (zs_max, zs_min))
    out("  rear cover top z%.1f (v3 z59.0, +%.1f mm) - needed for the weight stroke + stop rail, see section 13" % (
        Q["cover_top"], Q["cover_top"] - 59.0))

    hr("11. MASS, FILAMENT, PRINT TIME (15 g/h), BED 220 x 220")
    wk = white_key(Q, G_).vol_petg() * RHO_PETG / 1000
    bk = black_key(Q, G_).vol_petg() * RHO_PETG / 1000
    hm = hammer(Q, G_, False).vol_petg() * RHO_PETG / 1000
    shim = Q["blk_w"] * Q["blk_L"] * (Q["blk_h"] - Q["blk_h_b"]) * RHO_PETG / 1000
    fin_area = poly_props(key_fin(Q))[0]
    hfin_area = (2 * Q["boss_half"] + 2) * (Oh[1] + 1.0 - Q["z_floor"]) + 5 * 2.5
    frame_v3, removed_v3 = 175.0, 27.0            # v3 C19 frame; spine rail + back-stop rail (estimate)
    added = (24 * fin_area * Q["fin_t"] + 24 * hfin_area * Q["fin_t"] + 164.5 * 3.0 * 2.0 * 1.0) * RHO_PETG / 1000
    frame = frame_v3 - removed_v3 + added
    ledge = 164.5 * (209 - Q["y_w0"] + 1.6) * 1.2 * RHO_PETG / 1000 + 2.0
    rail = (164.5 * (209 - Q["y_w0"] + 4) * Q["rail_t"] * 0.6 + 164.5 * 3.0 * 3.5) * RHO_PETG / 1000
    cover = 44.0 + 164.5 * (Q["cover_top"] - 59.0) * 2.5 * RHO_PETG / 1000
    sbar = 17.0
    module = frame + ledge + rail + cover + sbar + 7 * wk + 5 * bk + 12 * hm + 5 * shim
    total = module * (7 + (160 + 82) / 502.0) * 1.10
    out("  per key: white key %.1f g, black key %.1f g, hammer (PETG) %.1f g, black shim %.2f g" % (wk, bk, hm, shim))
    out("  per module: frame %.0f (v3 175 - %.0f + combs/ledge %.0f), ledge plate %.0f, stop rail %.0f, cover %.0f, sensor bar %.0f,"
        " keys %.0f, hammers %.0f -> %.0f g, %.1f h" % (frame, removed_v3, added, ledge, rail, cover, sbar, 7 * wk + 5 * bk,
                                                     12 * hm + 5 * shim, module, module / 15))
    out("  88 keys (7 modules + end parts scaled as in v3, +10 %% waste): %.2f kg, %.0f h   (v3 C20: 5.0 kg / 332 h incl. rear bar;"
        " keyboard only 4.13 kg / 275 h; method D 7.6 kg / 304 h)" % (total / 1000, total / 15))
    R["fil_g_88"], R["print_h_88"] = total, total / 15
    R["module_g"] = module
    st_w = hammer(Q, G_, False).props(only=lambda n: n == "steel block")["m"]
    st_b = hammer(Q, G_, True).props(only=lambda n: n == "steel block")["m"]
    rod_g = 2 * 164.0 * math.pi * 1.5 ** 2 * RHO_STEEL / 1000
    steel_oct = 7 * st_w + 5 * st_b + rod_g
    steel_88 = 52 * st_w + 36 * st_b + (14 * 164.0 + 2 * 45 + 2 * 38) * math.pi * 1.5 ** 2 * RHO_STEEL / 1000
    out("  steel per octave: blocks 7 x %.1f + 5 x %.1f + rods %.1f = %.0f g; 88 keys %.2f kg" % (st_w, st_b, rod_g, steel_oct, steel_88 / 1000))
    R["steel_oct"], R["steel_88"] = steel_oct, steel_88
    out("  bed fit: frame 168.5 x 212 (v3 layout); 7 white keys side by side 164.5 x 174.5; 5 black keys 55 x 122;"
        " hammers printed on their side, 114 x 34 each -> 6 per plate (204 x 114); stop rail 164.5 x %.0f; all <= 220 x 220" % (
            209 - Q["y_w0"] + 4))

    hr("12. PARTS AND COST")
    out("  printed per octave: frame 1, ledge plate 1, stop rail 1, cover 1, sensor bar 1, white keys 7, black keys 5, hammers 12,"
        " black shims 5 = 34")
    out("  bought per octave (action): Ø3 rods 2, steel blocks 12, M3x10 5 = 19; felt cut from v3 stock: pad 1T x 12,"
        " stop strip 3T 25 x 164, ledge strip 1T; v3 carry-over: magnets 12, hook felts 12, front felts")
    add = 0
    for it, spec, q, u, src_, note in PURCHASE:
        out("  + %-34s %-60s %3d x %6d = %7d  [%s]" % (it, spec, q, u, q * u, note))
        add += q * u
    rem = 0
    for it, q, u, why in REMOVED:
        out("  - %-44s %3d x %6d = %7d  (%s)" % (it, q, u, q * u, why))
        rem += q * u
    out("  delta vs v3 base BOM: +%d - %d = %+d KRW  -> base %d KRW (cap 1,000,000)" % (add, rem, add - rem, 583219 + add - rem))
    R["cost_delta"] = add - rem
    out("  tools: hacksaw + file for 88 cuts of 9x25 bar (or order cut pieces) ; 1.5 mm hex key no longer needed")

    hr("13. WHY THE REAR COVER GOES UP; TRADE-OFF; ALTERNATIVE CLOSER TO z59")
    for cov in (59.0, 62.0, 66.0):
        q2, g2 = complete(dict(P, cover_top=cov))
        out("  this geometry, cover z%.0f: block %.1f mm, DW white %.1f g (target >= 47), m_eff %.1f g" % (
            cov, q2["blk_h"], statics(q2, g2, False, 1e-4, 1)["F_g"], m_eff(q2, g2, False, 0.5 * q2["tb_w"], 13.0)[0]))
    out("  energy view: finger work BW x travel + key PE must equal the weight's PE gain m*g*dz; with a rectangular block of"
        " 9 x 25 the best height split gives PE_max ~ rho w L (B/2)^2, so the vertical room B from the ledge (z%.1f) to the stop"
        " felt sets the achievable BW; the control board under the weights costs %.1f mm of B." % (Q["z_wb"], Q["z_wb"] - 9.0))
    out("  trade-off (key rod y171): lowest cover (0.5 steps) giving white DW >= 47.5 g, then m_eff / full return / rate @1.5 N:")
    for ycw in (106, 108, 110, 112):
        cov = 60.0
        while cov < 80:
            q4, g4 = complete(dict(P, cover_top=cov, y_cw=ycw))
            if statics(q4, g4, False, 1e-4, 1)["F_g"] >= 47.5:
                break
            cov += 0.5
        me = m_eff(q4, g4, False, 0.5 * q4["tb_w"], 13.0)[0]
        rr = release_from_bottom(Sim(q4, g4, False))
        hz = 1 / repetition(Sim(q4, g4, False), 1.5)[0]
        out("    lug y%d: cover z%.1f, block %.1f mm (%.1f g), m_eff %.1f g, 40 %% rise %.1f ms, full %.1f ms, %.1f Hz" % (
            ycw, cov, q4["blk_h"], hammer(q4, g4).props(only=lambda n: n == "steel block")["m"], me, rr["t_trig"] * 1e3,
            rr["t_full"] * 1e3, hz))
    for ycw, cov in ((107, 60.0), (107, 61.0), (108, 61.0)):
        q3 = dict(P, pk=(164.0, 40.0), blk_L=32.0, y_w0=175.0, cover_top=cov, y_cw=ycw)
        q3, g3 = complete(q3)
        dw = statics(q3, g3, False, 1e-4, 1)["F_g"]
        me = m_eff(q3, g3, False, 0.5 * q3["tb_w"], 13.0)[0]
        rr = release_from_bottom(Sim(q3, g3, False))
        c = min(min(v for k, v in clearances(q3, g3, b).items() if k != "stop_rail") for b in (False, True))
        fb = statics(q3, g3, False, 1e-4, 1, y_f=90.0)["F_g"] / dw
        out("  ALT key rod y164 + 9x32 bar (L32), lug y%d, cover z%.0f: block %.1f, DW %.1f, m_eff %.1f, full return %.1f ms,"
            " F90/F13 %.2f, magnet travel %.2f, min clearance %.2f" % (ycw, cov, q3["blk_h"], dw, me, rr["t_full"] * 1e3, fb,
                                                                     sensor(q3, False)["travel"], c))
    return Q, G_, R


if __name__ == "__main__":
    import io
    import sys
    buf = io.StringIO()

    def out(s=""):
        print(s)
        buf.write(s + "\n")
    Q, G_, R = main(out)
    plot_side(Q, G_, "h1_side.png")
    import json
    keep = {k: v for k, v in R.items() if isinstance(v, (int, float))}
    json.dump(keep, open("metrics.json", "w"), indent=1)
