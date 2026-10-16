#!/usr/bin/env python3
"""Toccata v4 concept W1 - short seesaw key + tail-lifted weighted lever.

Units: mm, g, ms  ->  force unit g*mm/ms^2 = 1 N exactly, torque N*mm, inertia g*mm^2,
velocity mm/ms = m/s.  z = 0 desk, y = 0 white-key front lip, +y away from the player.
Key angle a  > 0 : key front goes DOWN  (CCW rotation in the (y,z) plane about the key pivot K).
Lever angle b > 0 : lever weight goes UP (CW rotation in the (y,z) plane about the lever pivot L).
Everything printed by this script is what results.txt contains.
"""
import math, sys

G = 9.80665e-3          # mm/ms^2 ; weight of 1 g = G N
RHO_PETG = 1.25e-3      # g/mm^3 (Bambu PETG Basic, brief)
RHO_ST = 7.85e-3        # g/mm^3 steel
RHO_FELT = 0.35e-3      # g/mm^3 high-density wool felt
E_PETG = 1950.0         # MPa (brief)
E_ST = 200000.0


def rot(p, c, a):
    """rotate point p=(y,z) about c by angle a (CCW, rad)."""
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def rotv(v, a):
    ca, sa = math.cos(a), math.sin(a)
    return (v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca)


# ------------------------------------------------------------------ parameters (final iteration)
P = dict(
    # fixed v3 interfaces kept
    z_desk=0.0, z_floor=5.0, z_board_max=20.0, board_y=(145.5, 195.5), board_x=(47.25, 117.25),
    key_top=43.5, key_bot=23.5, black_top=55.5, dip_w=10.0, dip_b=9.5, y_black_front=52.5 + 2.0,
    black_shift=2.0,   # W1 moves the black key front 2.0 mm back (v3 51.5/52.5 -> 53.5/54.5): see clearance E

    y_elem=67.0, z_elem_w=12.68, z_elem_b=10.15, sensor_bar_top_w=13.6, sensor_bar_top_b=11.5,
    g_min=3.0,
    # key pivot: SUS304 round bar 4 mm lying in the balance rail, key notch sits on it
    K=(141.0, 21.5), rod_k=4.0,
    beam_z=(21.5, 28.5), beam_w=8.0, tail_top=24.5,      # beam behind the capstan is thinned to z21.5-25
    y_cap_w=190.0, y_cap_b=184.0, R_cap=3.0, cap_h=2.5,  # capstan (half cylinder R3) top = beam top + 2.5
    y_rest=(196.0, 199.0), rest_felt=1.5,                # rest felt pad on the beam end, on the rear shelf
    y_beam_end=199.0,
    # lever: SUS304 3 mm rod through the hubs
    L=(203.5, 33.5), rod_L=3.0, hub_R=4.5, hub_w=13.0,
    felt_c=2.0,                                          # felt strip under the steel (capstan contact)
    steel=(149.0, 199.0), steel_w=9.0, steel_h=21.5,     # 9T x 50 flat bar cut to h (block 9 x 50 x h)
    wall=1.0, curtain=(145.0, 147.0, 44.5),              # cover front curtain y-range and bottom z
    cover_plate=2.5, upstop_felt=2.0, upstop_gap=0.0,
    # friction assumptions
    mu_kp=0.20, mu_Lp=0.25, mu_c=0.30, guide_drag=0.015,  # N (1.5 gf) felt-bushed guide tab
    y_guide_w=18.0, y_guide_b=87.5,
    # finger points
    y_f13=13.0, y_f90=90.0, y_fb=62.5 + 2.0,
)
P["z_c"] = P["beam_z"][1] + P["cap_h"]          # contact plane (capstan top) at rest
P["z_sb"] = P["z_c"] + P["felt_c"]              # steel bottom


# ------------------------------------------------------------------ rigid bodies from boxes
class Body:
    def __init__(self, name):
        self.name, self.el = name, []

    def box(self, tag, y0, y1, z0, z1, w, rho=RHO_PETG, fill=1.0):
        m = (y1 - y0) * (z1 - z0) * w * rho * fill
        self.el.append(dict(tag=tag, m=m, y=(y0 + y1) / 2, z=(z0 + z1) / 2,
                            I=m * ((y1 - y0) ** 2 + (z1 - z0) ** 2) / 12.0, rho=rho,
                            V=(y1 - y0) * (z1 - z0) * w * fill))
        return self

    def point(self, tag, y, z, m):
        self.el.append(dict(tag=tag, m=m, y=y, z=z, I=0.0, rho=0, V=0))
        return self

    @property
    def m(self):
        return sum(e["m"] for e in self.el)

    @property
    def com(self):
        M = self.m
        return (sum(e["m"] * e["y"] for e in self.el) / M, sum(e["m"] * e["z"] for e in self.el) / M)

    def I_about(self, c):
        """moment of inertia about an x-axis through c: sum(I_self + m d^2) (parallel axis)."""
        return sum(e["I"] + e["m"] * ((e["y"] - c[0]) ** 2 + (e["z"] - c[1]) ** 2) for e in self.el)

    def mass_of(self, rho):
        return sum(e["m"] for e in self.el if e["rho"] == rho)


def white_key(P, y_cap=None, tail_steel=0.0):
    y_cap = P["y_cap_w"] if y_cap is None else y_cap
    zb, zt = P["key_bot"], P["key_top"]
    sk, wl = 2.0, 1.2
    k = Body("white key")
    k.box("top skin head", 0, 50, zt - sk, zt, 22.5)
    k.box("top skin tail", 50, 146, zt - sk, zt, 13.5)
    k.box("side walls head", 0, 50, zb, zt - sk, 2 * wl)
    k.box("side walls tail", 50, 146, zb, zt - sk, 2 * wl)
    k.box("front wall", 1.5, 2.7, zb, zt - sk, 22.5 - 2 * wl)
    k.box("head step walls", 49.4, 50.6, zb, zt - sk, 9.0)
    k.box("rear wall", 144.8, 146, zb, zt - sk, 13.5 - 2 * wl)
    for y in (40, 90, 118):
        k.box("rib", y - 0.6, y + 0.6, zt - sk - 8, zt - sk, 13.5 - 2 * wl)
    k.box("guide ribs", 10.5, 27, zb, zt - sk, 2 * wl)
    k.box("down-stop floor", 2.7, 10.5, zb, zb + 1.2, 22.5 - 2 * wl)
    k.box("magnet boss", P["y_elem"] - 3.8, P["y_elem"] + 3.8, zb, zt - sk, 3.2)
    k.box("magnet N35 5x2", P["y_elem"] - 2.5, P["y_elem"] + 2.5, zb, zb + 2, 5.0, rho=5.9e-3)
    b0, b1 = P["beam_z"]
    k.box("balance block", 135, 147, b0, 30.0, P["beam_w"], fill=0.9)
    k.box("beam", 147, y_cap + 3, b0, b1, P["beam_w"])
    k.box("capstan", y_cap - 3, y_cap + 3, b1, b1 + P["cap_h"], P["beam_w"], fill=0.75)
    k.box("thin tail", y_cap + 3, P["y_beam_end"], b0, P["tail_top"], P["beam_w"])
    k.box("rest felt", P["y_rest"][0], P["y_rest"][1], b0 - P["rest_felt"], b0, P["beam_w"], rho=RHO_FELT)
    if tail_steel:
        k.point("tail steel", 190.0, 24.0, tail_steel)
    return k


def black_key(P, y_cap=None):
    y_cap = P["y_cap_b"] if y_cap is None else y_cap
    zb, zt = P["key_bot"], P["black_top"]
    sk, wl = 2.0, 1.2
    f0 = 51.5 + P["black_shift"]          # base front face
    k = Body("black key")
    k.box("top skin", f0 + 1.0, 142, zt - sk, zt, 9.5)
    k.box("side walls", f0, 142, zb, zt - sk, 2 * wl)
    k.box("front wall", f0, f0 + 1.2, zb, zt - sk, 8.6)
    k.box("rear wall", 140.8, 142, zb, zt - sk, 8.6)
    for y in (100, 125):
        k.box("rib", y - 0.6, y + 0.6, zt - sk - 8, zt - sk, 8.6)
    k.box("stop floor", f0 + 1.2, 58.7, zb, zb + 1.2, 8.6)
    k.box("magnet boss", P["y_elem"] - 3.8, P["y_elem"] + 3.8, zb, zt - sk, 3.2)
    k.box("magnet N35 5x2", P["y_elem"] - 2.5, P["y_elem"] + 2.5, zb, zb + 2, 5.0, rho=5.9e-3)
    b0, b1 = P["beam_z"]
    k.box("balance block", 135, 147, b0, 30.0, P["beam_w"], fill=0.9)
    k.box("beam", 142, y_cap + 3, b0, b1, P["beam_w"])
    k.box("capstan", y_cap - 3, y_cap + 3, b1, b1 + P["cap_h"], P["beam_w"], fill=0.75)
    k.box("thin tail", y_cap + 3, P["y_beam_end"], b0, P["tail_top"], P["beam_w"])
    k.box("rest felt", P["y_rest"][0], P["y_rest"][1], b0 - P["rest_felt"], b0, P["beam_w"], rho=RHO_FELT)
    return k


def lever(P, h=None):
    h = P["steel_h"] if h is None else h
    s0, s1 = P["steel"]
    zs = P["z_sb"]
    Ly, Lz = P["L"]
    w, wl = P["steel_w"], P["wall"]
    lv = Body("lever")
    lv.box("steel 9T flat bar", s0, s1, zs, zs + h, w, rho=RHO_ST)
    lv.box("side walls", s0, s1, zs, zs + h, 2 * wl)
    lv.box("hub", Ly - P["hub_R"], Ly + P["hub_R"], Lz - P["hub_R"], Lz + P["hub_R"], P["hub_w"], fill=0.68)
    lv.box("hub web", s1, Ly, Lz + P["hub_R"], zs + h, w + 2 * wl, fill=0.5)
    lv.box("felt strip", 177.0, 196.5, zs - P["felt_c"], zs, w, rho=RHO_FELT)
    return lv


# ------------------------------------------------------------------ kinematics
class Action:
    """one key (white or black) + its lever, with exact rotation kinematics."""

    def __init__(self, P, black=False, h=None, y_cap=None, spring=None, tail_steel=0.0):
        self.P, self.black = P, black
        self.y_cap = (P["y_cap_b"] if black else P["y_cap_w"]) if y_cap is None else y_cap
        self.key = black_key(P, self.y_cap) if black else white_key(P, self.y_cap, tail_steel)
        self.lev = lever(P, h)
        self.h = P["steel_h"] if h is None else h
        self.K, self.L = P["K"], P["L"]
        self.C0 = (self.y_cap, P["z_c"] - P["R_cap"])      # capstan centre (key frame, rest)
        self.Q0 = (self.y_cap, P["z_c"])                  # a point of the felt contact plane (lever frame, rest)
        self.R = P["R_cap"]
        self.mk, self.ck, self.Ik = self.key.m, self.key.com, self.key.I_about(self.K)
        self.mL, self.cL, self.IL = self.lev.m, self.lev.com, self.lev.I_about(self.L)
        zt = P["black_top"] if black else P["key_top"]
        self.front = (P["y_black_front"], zt) if black else (0.0, zt)
        self.dip = P["dip_b"] if black else P["dip_w"]
        self.finger = (P["y_fb"], zt) if black else (P["y_f13"], zt)
        self.guide = ((P["y_guide_b"] if black else P["y_guide_w"]), P["key_bot"])
        self.p_stop = ((P["y_black_front"] - 1.0 + 58.7) / 2, P["key_bot"]) if black else (6.0, P["key_bot"])
        self.p_rest = ((P["y_rest"][0] + P["y_rest"][1]) / 2, P["beam_z"][0] - P["rest_felt"])
        self.mag = (P["y_elem"], P["key_bot"])
        s0, s1 = P["steel"]
        zt_s = P["z_sb"] + self.h
        self.corners = [(s0, zt_s), (s1, zt_s)]   # steel carrier top corners (up-stop contacts)
        self.a_dip = self.solve_a(self.front, self.dip)
        self.b_dip = self.solve_b(self.a_dip)
        self.spring = spring
        # felt top plane of the front down-stop: touches exactly at the dip
        self.z_ff = self.kz(self.p_stop, self.a_dip)
        self.z_shelf = self.p_rest[1]
        self.z_us = max(self.lz(c, self.b_dip) for c in self.corners) + P["upstop_gap"]

    # rotations ---------------------------------------------------------
    def kp(self, p, a):
        return rot(p, self.K, a)

    def lp(self, p, b):
        return rot(p, self.L, -b)

    def kz(self, p, a):
        return self.kp(p, a)[1]

    def lz(self, p, b):
        return self.lp(p, b)[1]

    def dkz(self, p, a):
        dy, dz = p[0] - self.K[0], p[1] - self.K[1]
        return dy * math.cos(a) - dz * math.sin(a)

    def dlz(self, p, b):
        dy, dz = p[0] - self.L[0], p[1] - self.L[1]
        return -dy * math.cos(b) - dz * math.sin(b)

    def solve_a(self, p, drop):
        lo, hi = 0.0, 0.3
        z0 = p[1]
        for _ in range(80):
            m = (lo + hi) / 2
            if z0 - self.kz(p, m) < drop:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2

    # capstan / lever contact ------------------------------------------------
    def geo(self, a, b):
        C = self.kp(self.C0, a)
        Q = self.lp(self.Q0, b)
        n = (-math.sin(b), -math.cos(b))           # plane normal, lever -> key
        t = (math.cos(b), -math.sin(b))
        d = (C[0] - Q[0]) * n[0] + (C[1] - Q[1]) * n[1]
        gap = d - self.R
        dC = (-(C[1] - self.K[1]), C[0] - self.K[0])
        g_a = dC[0] * n[0] + dC[1] * n[1]
        dQ = (Q[1] - self.L[1], -(Q[0] - self.L[0]))
        dn = (-math.cos(b), math.sin(b))
        g_b = -(dQ[0] * n[0] + dQ[1] * n[1]) + (C[0] - Q[0]) * dn[0] + (C[1] - Q[1]) * dn[1]
        Pc = (C[0] - self.R * n[0], C[1] - self.R * n[1])
        return gap, g_a, g_b, n, t, Pc

    def solve_b(self, a, b0=0.0):
        b = b0
        for _ in range(60):
            gap, g_a, g_b, *_ = self.geo(a, b)
            step = -gap / g_b
            b += step
            if abs(step) < 1e-13:
                break
        return b

    def j(self, a):
        b = self.solve_b(a, 0.0 if a < 1e-9 else self.solve_b(a))
        gap, g_a, g_b, *_ = self.geo(a, b)
        return -g_a / g_b, b

    def slip_rate(self, a, b, va, vb):
        _, _, _, n, t, Pc = self.geo(a, b)
        vk = (-va * (Pc[1] - self.K[1]), va * (Pc[0] - self.K[0]))
        wl = -vb
        vl = (-wl * (Pc[1] - self.L[1]), wl * (Pc[0] - self.L[0]))
        return (vk[0] - vl[0]) * t[0] + (vk[1] - vl[1]) * t[1]

    # statics ---------------------------------------------------------------
    def statics(self, a, fpt=None):
        """quasi-static finger force at fpt (default finger point) at key angle a:
        balance (frictionless), friction force, DW, UW, contact force, m_eff, lever ratio."""
        fpt = self.finger if fpt is None else fpt
        jj, b = self.j(a)
        Qa = -self.mk * G * self.dkz(self.ck, a)
        Qb = -self.mL * G * self.dlz(self.cL, b)
        dzf = self.dkz(fpt, a)                 # < 0
        F = (Qa + jj * Qb) / dzf                # N, finger force for equilibrium (frictionless)
        gap, g_a, g_b, n, t, Pc = self.geo(a, b)
        N = -Qb / g_b                          # capstan normal force
        Rk = math.hypot(-N * n[0], self.mk * G - N * n[1] + F)
        RL = math.hypot(N * n[0], self.mL * G + N * n[1])
        slip = abs(self.slip_rate(a, b, 1.0, jj))
        dzg = abs(self.dkz(self.guide, a))
        wf = dict(kp=self.P["mu_kp"] * self.P["rod_k"] / 2 * Rk,
                  Lp=self.P["mu_Lp"] * self.P["rod_L"] / 2 * RL * abs(jj),
                  cap=self.P["mu_c"] * N * slip,
                  guide=self.P["guide_drag"] * dzg)
        fr = {k: v / abs(dzf) for k, v in wf.items()}
        f = sum(fr.values())
        r = abs(dzf)
        meff = (self.Ik + self.IL * jj ** 2) / r ** 2
        return dict(a=a, b=b, j=jj, F=F / G, f=f / G, fr={k: v / G for k, v in fr.items()},
                    DW=(F + f) / G, UW=(F - f) / G, N=N, Rk=Rk, RL=RL, meff=meff,
                    meff_key=self.Ik / r ** 2, meff_lev=self.IL * jj ** 2 / r ** 2, r=r, slip=slip)

    def mag_travel(self):
        return self.mag[1] - self.kz(self.mag, self.a_dip), self.kp(self.mag, self.a_dip)[0] - self.mag[0]


# ------------------------------------------------------------------ dynamics
FELT = dict(front=(30.0, 0.35), front_b=(20.0, 0.35), rest=(40.0, 0.35), cap=(30.0, 0.30), up=(40.0, 0.35))
# (K [N/mm^1.5], e) : F = K d^1.5 (1 + alpha d_dot), alpha = 3(1-e^2)/(4 v0) set at each impact onset
# (Lankarani-Nikravesh), so every felt impact has restitution ~e at any speed. K and e are assumptions
# (wool felt, high density); the stage-0 drop test measures them.


class Felt:
    def __init__(self, KA):
        self.K, self.e = KA
        self.al = 0.0
        self.on = False

    def force(self, pen, pen_dot):
        if pen <= 0:
            self.on = False
            return 0.0
        if not self.on:
            self.on = True
            v0 = max(abs(pen_dot), 1e-3)
            self.al = 3 * (1 - self.e ** 2) / (4 * v0)
        return max(0.0, self.K * pen ** 1.5 * (1.0 + self.al * pen_dot))


def sat(x):
    return max(-1.0, min(1.0, x))


def simulate(A, t_end=300.0, dt=0.004, a0=None, finger=None, record=False, b0=None):
    """integrate key angle a and lever angle b.
    finger(t) -> force in N at the finger point (downward), or None.
    Returns time histories (sparse) and event summary."""
    P = A.P
    a = A.a_dip if a0 is None else a0
    b = A.solve_b(a) if b0 is None else b0
    va = vb = 0.0
    fe_front = Felt(FELT["front_b"] if A.black else FELT["front"])
    fe_rest, fe_cap = Felt(FELT["rest"]), Felt(FELT["cap"])
    fe_up = [Felt(FELT["up"]) for _ in A.corners]
    mag_rest = A.mag[1]
    mag_bot = A.kz(A.mag, A.a_dip)
    ev = dict(t40=None, t100=None, sep_max=0.0, sep_time=0.0, t_bottom=None, v_bottom=None,
              up_peak=0.0, up_hits=0, land_v=0.0, cap_peak=0.0, front_peak=0.0, rest_peak=0.0,
              min_frac_after_rest=None, b_max=b, last_sep_end=None)
    hist = []
    t = 0.0
    in_contact = True
    was_up = False
    released = finger is None
    t_rel = None
    frac_prev = 0.0
    n = int(t_end / dt)
    for i in range(n):
        Ff = finger(t) if finger else 0.0
        if not released and Ff == 0.0 and t > 0:
            released, t_rel = True, t
        # gravity
        Qa = -A.mk * G * A.dkz(A.ck, a)
        Qb = -A.mL * G * A.dlz(A.cL, b)
        # finger
        if Ff:
            Qa += -Ff * A.dkz(A.finger, a)
        # capstan contact
        gap, g_a, g_b, nrm, tng, Pc = A.geo(a, b)
        pen = -gap
        pen_dot = -(g_a * va + g_b * vb)
        N = fe_cap.force(pen, pen_dot)
        Qa += N * g_a
        Qb += N * g_b
        fk = (0.0, 0.0)
        if N > 0:
            vt = A.slip_rate(a, b, va, vb)
            fm = -P["mu_c"] * N * sat(vt / 1e-3)
            fk = (fm * tng[0], fm * tng[1])
            Qa += (Pc[0] - A.K[0]) * fk[1] - (Pc[1] - A.K[1]) * fk[0]
            Qb -= (Pc[0] - A.L[0]) * (-fk[1]) - (Pc[1] - A.L[1]) * (-fk[0])
        # front down-stop felt
        zs = A.kz(A.p_stop, a)
        dzs = A.dkz(A.p_stop, a)
        Ffr = fe_front.force(A.z_ff - zs, -dzs * va)
        Qa += Ffr * dzs
        # rest felt on the rear shelf
        zr = A.kz(A.p_rest, a)
        dzr = A.dkz(A.p_rest, a)
        Fre = fe_rest.force(A.z_shelf - zr, -dzr * va)
        Qa += Fre * dzr
        # lever up-stop (cover felt) on the carrier top corners
        Fup = 0.0
        for c, fe in zip(A.corners, fe_up):
            zc_ = A.lz(c, b)
            dzc = A.dlz(c, b)
            f_ = fe.force(zc_ - A.z_us, dzc * vb)
            Qb -= f_ * dzc
            Fup += f_
        # optional assist spring (steel compression spring hanging from the cover onto the carrier top)
        Fsp = 0.0
        if A.spring:
            ps = A.spring["pt"]
            zp = A.lz(ps, b)
            comp = zp - A.spring["z_tip"]
            if comp > 0:
                Fsp = A.spring["k"] * comp
                Qb -= Fsp * A.dlz(ps, b)
        # guide drag (felt-bushed tab)
        dzg = A.dkz(A.guide, a)
        Qa += -P["guide_drag"] * sat(dzg * va / 1e-3) * dzg
        # pivot friction (quasi-static reactions)
        Rk = math.hypot(-N * nrm[0] - fk[0], A.mk * G - N * nrm[1] - fk[1] + Ff - Ffr - Fre)
        RL = math.hypot(N * nrm[0] + fk[0], A.mL * G + N * nrm[1] + fk[1] + Fup + Fsp)
        Qa += -P["mu_kp"] * P["rod_k"] / 2 * Rk * sat(va / 2e-5)
        Qb += -P["mu_Lp"] * P["rod_L"] / 2 * RL * sat(vb / 1e-4)
        # integrate (semi-implicit Euler)
        va += Qa / A.Ik * dt
        vb += Qb / A.IL * dt
        a += va * dt
        b += vb * dt
        t += dt
        # events
        ev["cap_peak"] = max(ev["cap_peak"], N)
        ev["front_peak"] = max(ev["front_peak"], Ffr)
        ev["rest_peak"] = max(ev["rest_peak"], Fre)
        ev["b_max"] = max(ev["b_max"], b)
        if Fup > 0:
            ev["up_peak"] = max(ev["up_peak"], Fup)
            if not was_up:
                ev["up_hits"] += 1
            was_up = True
        else:
            was_up = False
        if gap > 1e-3:
            ev["sep_max"] = max(ev["sep_max"], gap)
            ev["sep_time"] += dt
            if in_contact:
                in_contact = False
        elif not in_contact and gap <= 0:
            in_contact = True
            ev["land_v"] = max(ev["land_v"], abs(pen_dot))
            ev["last_sep_end"] = t
        if finger and ev["t_bottom"] is None and Ffr > 0:
            ev["t_bottom"] = t
            ev["v_bottom"] = abs(A.dkz(A.finger, a) * va)
        frac = (A.kz(A.mag, a) - mag_bot) / (mag_rest - mag_bot)   # 0 bottom -> 1 rest (magnet)
        if released:
            tr = t - (t_rel or 0.0)
            if ev["t40"] is None and frac >= 0.40 and (finger is None or t_rel is not None):
                ev["t40"] = tr
            if ev["t100"] is None and a <= 0.0:
                ev["t100"] = tr
            if ev["t100"] is not None:
                ev["min_frac_after_rest"] = frac if ev["min_frac_after_rest"] is None else min(ev["min_frac_after_rest"], frac)
        if record and i % 25 == 0:
            hist.append((t, a, b, frac, N, gap, Ffr, Fre, Fup))
    ev["a_end"], ev["b_end"] = a, b
    return ev, hist


# ------------------------------------------------------------------ design solve helpers
def solve_cap(P, black, target):
    """capstan y so that DW at the finger point (white y13 / black y62.5) = target g."""
    key = "y_cap_b" if black else "y_cap_w"
    lo, hi = 178.0, 194.0
    for _ in range(50):
        m = (lo + hi) / 2
        P[key] = m
        if Action(P, black).statics(1e-4)["DW"] < target:
            lo = m
        else:
            hi = m
    P[key] = round((lo + hi) / 2, 2)
    return P[key]


def fmt(p):
    return "(%.2f, %.2f)" % p


def seg_pts(a, b, n=12):
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


def key_outline_pts(A):
    """points on the top edge of the key beam/capstan/thin tail (key frame, rest)."""
    P = A.P
    b0, b1 = P["beam_z"]
    yc = A.y_cap
    pts = seg_pts((147.0, b1), (yc - A.R, b1), 30)
    pts += [(yc + A.R * math.cos(t), (P["z_c"] - A.R) + A.R * math.sin(t))
            for t in [math.pi * i / 16 for i in range(17)]]
    pts += [(yc + A.R, P["tail_top"])]
    pts += seg_pts((yc + A.R, P["tail_top"]), (P["y_beam_end"], P["tail_top"]), 8)
    pts += seg_pts((P["y_beam_end"], P["tail_top"]), (P["y_beam_end"], b0), 4)
    return pts


def lever_under_segments(A):
    """lever underside (lever frame, rest): felt strip, steel bottom in front, front wall, hub circle."""
    P = A.P
    s0, s1 = P["steel"]
    zc, zs = P["z_c"], P["z_sb"]
    segs = [((177.0, zc), (196.5, zc)), ((196.5, zc), (196.5, zs)), ((196.5, zs), (s1, zs)),
            ((s0, zs), (177.0, zs)), ((177.0, zs), (177.0, zc)), ((s0, zs), (s0, zs + A.h))]
    return segs


def pt_seg(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(p[0] - qx, p[1] - qy), (qx, qy)


def clearances(A, a):
    """min clearances at key angle a (lever in contact): key beam top vs lever underside (excluding the
    capstan crown inside +-3 mm of the contact), key tail vs hub, key underside vs sensor bar, etc."""
    P = A.P
    b = A.solve_b(a)
    out = {}
    _, _, _, n, t, Pc = A.geo(a, b)
    segs = [(A.lp(s[0], b), A.lp(s[1], b)) for s in lever_under_segments(A)]
    best = 1e9
    for p0 in key_outline_pts(A):
        p = A.kp(p0, a)
        if math.hypot(p[0] - Pc[0], p[1] - Pc[1]) < A.R * 1.2:
            continue   # the capstan crown is the contact itself
        for s in segs:
            d, q = pt_seg(p, *s)
            # only count points below the lever underside (sign by the normal)
            below = (q[0] - p[0]) * n[0] + (q[1] - p[1]) * n[1] <= 0
            best = min(best, d if below else -d)
    out["beam_vs_lever_underside"] = best
    Lc = P["L"]
    hub = min(math.hypot(A.kp(p0, a)[0] - Lc[0], A.kp(p0, a)[1] - Lc[1]) for p0 in key_outline_pts(A)) - P["hub_R"]
    out["key_tail_vs_hub"] = hub
    ztop = P["sensor_bar_top_b"] if A.black else P["sensor_bar_top_w"]
    out["key_underside_vs_sensor_bar"] = min(A.kz((y, P["key_bot"]), a) for y in (59.0, 67.0, 77.5)) - ztop
    out["magnet_face_vs_element"] = A.kz(A.mag, a) - (P["z_elem_b"] if A.black else P["z_elem_w"])
    out["balance_block_vs_rail"] = min(A.kz((y, P["beam_z"][0]), a) for y in (135.0, 147.0)) - (P["K"][1] - P["rod_k"] / 2)
    out["beam_vs_board_ceiling"] = min(A.kz((y, P["beam_z"][0]), a) for y in (147.0, 160.0, 195.5)) - P["z_board_max"]
    s0 = P["steel"][0]
    out["lever_front_vs_curtain"] = min(A.lp((s0, z), b)[0] for z in (P["z_sb"], P["z_sb"] + A.h)) - P["curtain"][1]
    if A.black:
        # black front face (base y f0 up to z43.5, raised front edge to the top) vs the static white head
        # notch face (v3: y50 above z40.9, 1.5 chamfer to y48.5 at z23.5); horizontal gap inside z23.5..43.5
        f0 = 51.5 + P["black_shift"]
        face = seg_pts((f0, P["key_bot"]), (f0, P["key_top"]), 20) + seg_pts((f0, P["key_top"]), (f0 + 1.0, P["black_top"]), 24)
        best = 1e9
        for p0 in face:
            p = A.kp(p0, a)
            if 23.5 <= p[1] <= 43.5:
                ny = 48.5 + 1.5 * (p[1] - 23.5) / 17.4 if p[1] <= 40.9 else 50.0
                best = min(best, p[0] - ny)
            elif p[1] > 43.5:
                best = min(best, math.hypot(p[0] - 50.0, p[1] - 43.5) if p[0] < 50.0 else p[0] - 50.0)
        out["black_front_vs_white_notch"] = best
    out["steel_top_max_z"] = max(A.lz(c, b) for c in A.corners)
    return out, b


# ------------------------------------------------------------------ report
def pr(*a):
    print(*a)


def section(t):
    pr("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def main():
    P0 = dict(P)
    TARGET_DW = 50.5
    section("A0. DESIGN EXPLORATION - white capstan y vs steel height h for DW(y13) = %.1f g (no spring)" % TARGET_DW)
    pr("  ycap   h    steel g  m_eff  UW    t40   t_full  1/(2t40)  highest steel z at dip")
    for yc in (186.0, 187.0, 188.0, 189.0, 190.0):
        Pq = dict(P0); Pq["y_cap_w"] = yc
        lo, hi = 6.0, 40.0
        for _ in range(40):
            m = (lo + hi) / 2; Pq["steel_h"] = m
            if Action(Pq, False).statics(1e-4)["DW"] < TARGET_DW:
                lo = m
            else:
                hi = m
        Pq["steel_h"] = (lo + hi) / 2
        Aq = Action(Pq, False); sq = Aq.statics(1e-4); evq, _ = simulate(Aq, t_end=160.0)
        pr("  %5.1f %5.1f %7.1f %6.1f %5.1f %6.1f %6.1f %7.1f Hz %8.1f" % (yc, Pq["steel_h"], Aq.lev.mass_of(RHO_ST),
           sq["meff"], sq["UW"], evq["t40"], evq["t100"], 500 / evq["t40"], max(Aq.lz(c, Aq.b_dip) for c in Aq.corners)))
    pr("  -> chosen: capstan ~189 with h = %.1f mm (cut length of 9T x 50 flat bar): meets 13.3 Hz and < 60 ms with"
       " the least steel height; capstans are then re-solved for exactly DW = %.1f g." % (P0["steel_h"], TARGET_DW))
    section("A. SOLVE - capstan positions for DW = %.1f g (white at y13, black at y62.5); steel 9 x 50 x %.1f fixed"
            % (TARGET_DW, P0["steel_h"]))
    yw = solve_cap(P0, False, TARGET_DW)
    yb = solve_cap(P0, True, TARGET_DW)
    pr("white capstan y = %.2f  (lever arm a_L = %.2f, key arm a_K = %.2f)" % (yw, P0["L"][0] - yw, yw - P0["K"][0]))
    pr("black capstan y = %.2f  (a_L = %.2f, a_K = %.2f)" % (yb, P0["L"][0] - yb, yb - P0["K"][0]))
    for bl, key in ((False, "y_cap_w"), (True, "y_cap_b")):
        Pq = dict(P0); Pq[key] += 0.3
        d = Action(Pq, bl).statics(1e-4)["DW"] - TARGET_DW
        pr("  DW sensitivity %s: +0.3 mm capstan -> %+.2f g" % ("black" if bl else "white", d))
    W, B = Action(P0, False), Action(P0, True)
    R = {}
    for A in (W, B):
        nm = "black" if A.black else "white"
        section("B. GEOMETRY (%s key, D / C# representative)  coordinates (y, z) mm" % nm)
        a1, b1 = A.a_dip, A.b_dip
        pts = [("key pivot K (SUS 4 rod centre)", A.K, True), ("lever pivot L (SUS 3 rod centre)", A.L, None),
               ("key top front (lip / black front edge)", A.front, True), ("finger point", A.finger, True),
               ("front down-stop contact (key underside)", A.p_stop, True),
               ("rest felt bottom (on rear shelf)", A.p_rest, True),
               ("magnet face centre", A.mag, True), ("key COM", A.ck, True),
               ("capstan crown (contact at rest)", (A.y_cap, P0["z_c"]), True),
               ("lever COM", A.cL, False), ("steel front-top corner", A.corners[0], False),
               ("steel rear-top corner", A.corners[1], False)]
        pr("%-42s %-18s %-18s" % ("point", "rest", "bottom (dip)"))
        for name, p, onkey in pts:
            if onkey is None:
                q = p
            elif onkey:
                q = A.kp(p, a1)
            else:
                q = A.lp(p, b1)
            pr("%-42s %-18s %-18s" % (name, fmt(p), fmt(q)))
        _, _, _, n, t, Pc = A.geo(a1, b1)
        pr("%-42s %-18s %-18s" % ("capstan contact point", fmt((A.y_cap, P0["z_c"])), fmt(Pc)))
        pr("key rotation at dip a = %.4f rad (%.2f deg); lever rotation b = %.4f rad (%.2f deg)"
           % (a1, math.degrees(a1), b1, math.degrees(b1)))
        pr("front down-stop felt top plane z = %.2f ; rear shelf top z = %.2f ; up-stop felt face z = %.2f"
           % (A.z_ff, A.z_shelf, A.z_us))

        section("C. STATICS (%s)" % nm)
        pr("masses: key %.2f g (COM y%.1f), lever %.2f g (steel %.2f g, PETG %.2f g, felt %.2f g)"
           % (A.mk, A.ck[0], A.mL, A.lev.mass_of(RHO_ST), A.lev.mass_of(RHO_PETG), A.lev.mass_of(RHO_FELT)))
        pr("inertia about own pivot: key I_k = %.0f g mm^2, lever I_L = %.0f g mm^2" % (A.Ik, A.IL))
        s = A.statics(1e-4)
        pr("at rest (start of motion), finger %s:" % fmt(A.finger))
        pr("  balance weight BW = %.2f g, friction = %.2f g  ->  DW = %.2f g, UW = %.2f g" % (s["F"], s["f"], s["DW"], s["UW"]))
        pr("  friction split (g at finger): key pivot %.2f, lever pivot %.2f, capstan slip %.2f, guide bushing %.2f"
           % (s["fr"]["kp"], s["fr"]["Lp"], s["fr"]["cap"], s["fr"]["guide"]))
        pr("  capstan normal force %.3f N ; key pivot reaction %.3f N ; lever pivot reaction %.3f N"
           % (s["N"], s["Rk"], s["RL"]))
        pr("  lever ratio j = db/da = %.3f (rest), %.3f (dip); capstan slip %.2f mm per rad of key"
           % (s["j"], A.j(A.a_dip)[0], s["slip"]))
        pr("  m_eff at finger = %.1f g (key %.1f + lever %.1f)" % (s["meff"], s["meff_key"], s["meff_lev"]))
        if not A.black:
            s0 = A.statics(1e-4, (0.0, P0["key_top"]))
            s90 = A.statics(1e-4, (P0["y_f90"], P0["key_top"]))
            pr("  at lip y0: BW %.2f, DW %.2f, UW %.2f g, m_eff %.1f g" % (s0["F"], s0["DW"], s0["UW"], s0["meff"]))
            pr("  at y90: DW %.2f g  -> front/back ratio DW(y90)/DW(y13) = %.2f" % (s90["DW"], s90["DW"] / s["DW"]))
            R["lip"], R["y90"] = s0, s90
        pr("  force along the stroke (finger point), fraction of dip -> BW / DW / UW g, j, m_eff:")
        for fr_ in (0.0, 0.25, 0.5, 0.75, 1.0):
            aa = max(1e-4, A.solve_a(A.front, A.dip * fr_)) if fr_ > 0 else 1e-4
            q = A.statics(aa)
            pr("   %4.2f : %6.2f / %6.2f / %6.2f   j %.3f  m_eff %.1f" % (fr_, q["F"], q["DW"], q["UW"], q["j"], q["meff"]))
        # weight travel and velocity ratio
        cg0, cg1 = A.cL, A.lp(A.cL, b1)
        sc = A.lev.el[0]
        st0 = (sc["y"], sc["z"]); st1 = A.lp(st0, b1)
        f0, f1 = A.finger, A.kp(A.finger, a1)
        pr("  steel centroid rise %.2f mm, lever COM rise %.2f mm, finger drop %.2f mm -> velocity ratio %.2f"
           % (st1[1] - st0[1], cg1[1] - cg0[1], f0[1] - f1[1], (st1[1] - st0[1]) / (f0[1] - f1[1])))
        pr("  highest steel corner rise %.2f mm (front-top corner)" % (A.lz(A.corners[0], b1) - A.corners[0][1]))
        R[nm] = dict(A=A, s=s)

        section("D. SENSOR (%s)" % nm)
        tr, dy = A.mag_travel()
        ze = P0["z_elem_b"] if A.black else P0["z_elem_w"]
        pr("magnet y%.1f: rest face-element %.2f mm, bottom %.2f mm, travel %.2f mm, y shift at dip %.2f mm"
           % (A.mag[0], A.mag[1] - ze, A.mag[1] - tr - ze, tr, dy))
        pr("40%% re-trigger point = %.2f mm of magnet rise above the bottom" % (0.4 * tr))
        R[nm]["mag"] = (A.mag[1] - ze, A.mag[1] - tr - ze, tr)

        section("E. CLEARANCES along the stroke (%s), mm (negative = interference)" % nm)
        worst = {}
        extra = A.solve_a(A.front, A.dip + 0.6)   # ff over-travel: front felt compressed 0.6 mm
        for aa in [A.a_dip * i / 10 for i in range(11)] + [extra]:
            c, _ = clearances(A, max(aa, 1e-6))
            for k, v in c.items():
                if k == "steel_top_max_z":
                    worst[k] = max(worst.get(k, -1e9), v)
                else:
                    worst[k] = min(worst.get(k, 1e9), v)
        for k, v in worst.items():
            pr("  %-34s %8.2f" % (k, v))
        R[nm]["clear"] = worst
    return P0, W, B, R


def spring_for(A, add_g, y_s=172.0, engage=0.5, Gm=69000.0, d=0.30, D_out=6.0):
    """optional assist spring: steel compression spring hanging from the cover onto the carrier top at y_s,
    touching at `engage` x lever travel; rate chosen to add `add_g` grams at the finger at the bottom."""
    pt = (y_s, A.P["z_sb"] + A.h)
    z_tip = A.lz(pt, engage * A.b_dip)
    comp = A.lz(pt, A.b_dip) - z_tip
    jd = A.j(A.a_dip)[0]
    k = add_g * G * abs(A.dkz(A.finger, A.a_dip)) / (comp * abs(A.dlz(pt, A.b_dip)) * jd)
    Dm = D_out - d
    n = Gm * d ** 4 / (8 * Dm ** 3 * k)
    Fmax = k * comp
    C = Dm / d
    wahl = (4 * C - 1) / (4 * C - 4) + 0.615 / C
    tau = 8 * Fmax * Dm / (math.pi * d ** 3) * wahl
    z_ci = A.z_us + A.P["upstop_felt"]
    return dict(pt=pt, z_tip=z_tip, k=k, comp=comp, n=n, Fmax=Fmax, tau=tau, solid=(n + 2) * d, d=d, D_out=D_out,
                L0=z_ci - z_tip, fits=(n + 2) * d + comp + 1.0 <= z_ci - z_tip)


def run_release(A, label):
    ev, _ = simulate(A, t_end=200.0)
    t40, t100 = ev["t40"], ev["t100"]
    pr("  %-34s t(40%%) %6.1f ms  t(full) %6.1f ms  rate 1/(2 t40) %5.1f Hz  1/(t40+10) %5.1f Hz  "
       "sep max %.3f mm  rebound below rest %.1f %% dip  rest-felt peak %.2f N"
       % (label, t40, t100, 500.0 / t40, 1000.0 / (t40 + 10.0), ev["sep_max"],
          100 * (1 - ev["min_frac_after_rest"]), ev["rest_peak"]))
    return ev


def rest_state(A):
    """settle the action at rest (felts loaded by gravity) - initial state of every press."""
    ev, _ = simulate(A, t_end=120.0, a0=0.0, b0=0.0)
    return ev["a_end"], ev["b_end"]


def run_press(A, F, label, hold=120.0):
    a0, b0 = rest_state(A)
    ev, _ = simulate(A, t_end=hold + 200.0, finger=lambda t: F if t < hold else 0.0, a0=a0, b0=b0)
    pr("  %-12s finger %.2f N: key speed at felt %.2f m/s, lever flight gap max %.2f mm (%.1f ms), "
       "up-stop hits %d peak %.2f N, re-landing %.3f m/s, front felt peak %.1f N, capstan peak %.1f N; "
       "after release t40 %.1f ms, full %.1f ms"
       % (label, F, ev["v_bottom"] or 0, ev["sep_max"], ev["sep_time"], ev["up_hits"], ev["up_peak"],
          ev["land_v"], ev["front_peak"], ev["cap_peak"], ev["t40"] or -1, ev["t100"] or -1))
    return ev


def main2(P0, W, B, R):
    section("F. DYNAMICS - release from the bottom (finger lifted instantly), 4 us steps")
    pr("felt model: Hunt-Crossley, K / e =", {k: v for k, v in FELT.items()})
    pr("re-trigger assumption: firmware re-arms when the MAGNET has risen 40 % of its travel from the bottom;")
    pr("rate = 1/(2 t40) assumes the finger re-presses as slowly as the key rose (conservative); 1/(t40+10ms) "
       "assumes a 10 ms re-press.")
    R["rel"] = {}
    for A in (W, B):
        nm = "black" if A.black else "white"
        R["rel"][nm] = run_release(A, nm + " (no spring)")
    for A in (W, B):
        nm = "black" if A.black else "white"
        sp = spring_for(A, 12.0)
        A2 = Action(P0, A.black, spring=sp)
        pr("  option: assist spring for %s: k %.3f N/mm, touches at 50%% lever travel, compression %.2f mm, "
           "F max %.3f N, SUS wire d%.2f OD%.1f n %.1f active, tau %.0f MPa, solid %.1f mm, free length %.1f "
           "(cover to tip) -> fits %s" % (nm, sp["k"], sp["comp"], sp["Fmax"], sp["d"], sp["D_out"], sp["n"], sp["tau"],
                                          sp["solid"], sp["L0"], sp["fits"]))
        s_b = A2.statics(A2.a_dip - 1e-4)
        R["rel"][nm + "_spring"] = run_release(A2, nm + " (+12 g assist spring)")
        R[nm + "_spring"] = sp
    section("F2. OPTION W1-S - heavier inertia + assist spring (white): capstan y191.5, steel h solved for DW 50.5")
    Pq = dict(P0); Pq["y_cap_w"] = 191.5
    lo, hi = 6.0, 40.0
    for _ in range(40):
        m = (lo + hi) / 2; Pq["steel_h"] = m
        if Action(Pq, False).statics(1e-4)["DW"] < 50.5:
            lo = m
        else:
            hi = m
    Pq["steel_h"] = round((lo + hi) / 2, 1)
    A = Action(Pq, False); s = A.statics(1e-4)
    pr("  h %.1f mm, steel %.1f g, DW %.1f, UW %.1f, m_eff %.1f g, highest steel z at dip %.2f (cover top %.2f)"
       % (Pq["steel_h"], A.lev.mass_of(RHO_ST), s["DW"], s["UW"], s["meff"], max(A.lz(c, A.b_dip) for c in A.corners),
          max(A.lz(c, A.b_dip) for c in A.corners) + Pq["upstop_felt"] + Pq["cover_plate"]))
    run_release(A, "W1-S no spring")
    for add in (12.0, 20.0):
        sp = spring_for(A, add)
        pr("  spring +%.0f g: k %.3f N/mm, F max %.3f N, d%.2f OD%.1f n %.1f, solid %.1f, free %.1f mm, fits %s"
           % (add, sp["k"], sp["Fmax"], sp["d"], sp["D_out"], sp["n"], sp["solid"], sp["L0"], sp["fits"]))
        R["rel"]["W1S_%d" % add] = run_release(Action(Pq, False, spring=sp), "W1-S + %.0f g spring" % add)
    R["W1S"] = dict(h=Pq["steel_h"], st=A.lev.mass_of(RHO_ST), meff=s["meff"])
    section("G. DYNAMICS - press (constant finger force at the finger point, held 120 ms, then released)")
    R["press"] = {}
    for A in (W, B):
        nm = "black" if A.black else "white"
        for F, lab in ((0.8, "pp"), (1.5, "mf"), (3.0, "ff"), (6.0, "fff")):
            R["press"][nm + lab] = run_press(A, F, nm + " " + lab)
    pr("  up-stop height tolerance (lever up-stop felt face vs its nominal 'touch at dip' position), ff 3 N:")
    for A0 in (W, B):
        for dg in (-0.3, 0.3):
            Pq = dict(P0); Pq["upstop_gap"] = dg
            run_press(Action(Pq, A0.black), 3.0, ("black" if A0.black else "white") + " gap%+.1f" % dg)
    section("H. CHECK of the v2.0 claim 'gravity return ~40 ms regardless of mass' (white, same capstan)")
    for h in (10.0, 14.0, 19.0, 24.0):
        A = Action(P0, False, h=h)
        s = A.statics(1e-4)
        ev, _ = simulate(A, t_end=250.0)
        pr("  steel h %4.1f: DW %5.1f UW %5.1f m_eff %5.1f  m_eff/UW %.2f -> t40 %5.1f ms, full %5.1f ms"
           % (h, s["DW"], s["UW"], s["meff"], s["meff"] / s["UW"], ev["t40"], ev["t100"]))
    pr("  -> return time scales with sqrt(m_eff/UW); re-trigger needs only the 40 % rise (~62 % of full-return time).")
    section("H2. SENSITIVITY of the white release to the assumed felt / friction values")
    base = dict(FELT)
    cases = [("baseline", {}, 1.0), ("rest felt e 0.2", {"rest": (40.0, 0.2)}, 1.0),
             ("rest felt e 0.5", {"rest": (40.0, 0.5)}, 1.0), ("rest felt K 15 (soft)", {"rest": (15.0, 0.35)}, 1.0),
             ("capstan felt K 12 (soft)", {"cap": (12.0, 0.3)}, 1.0), ("all friction x2", {}, 2.0)]
    for lab, ch, fm in cases:
        FELT.update(base); FELT.update(ch)
        Pq = dict(P0)
        for k in ("mu_kp", "mu_Lp", "mu_c", "guide_drag"):
            Pq[k] = P0[k] * fm
        A = Action(Pq, False)
        s = A.statics(1e-4)
        ev, _ = simulate(A, t_end=200.0)
        pr("  %-26s DW %5.1f UW %5.1f  t40 %5.1f ms  full %5.1f ms  rebound below rest %4.1f %% dip"
           % (lab, s["DW"], s["UW"], ev["t40"], ev["t100"], 100 * (1 - ev["min_frac_after_rest"])))
    FELT.update(base)


def main3(P0, W, B, R):
    section("I. CONSTANT STRESS IN PLASTIC AT REST (gravity only) and rod deflections")
    worst = 0.0
    for A in (W, B):
        nm = "black" if A.black else "white"
        s = A.statics(1e-4)
        N0 = s["N"]
        aK = A.y_cap - A.K[0]
        Mg = A.mk * G * (A.K[0] - A.ck[0])                    # key front-heavy moment (N mm)
        y_r = A.p_rest[0]
        Rs = (N0 * aK - Mg) / (y_r - A.K[0])                   # rear shelf reaction
        Rk = A.mk * G + N0 - Rs
        t_tail = A.P["tail_top"] - A.P["beam_z"][0]
        s_tail = Rs * (y_r - (A.y_cap + A.R)) / (A.P["beam_w"] * t_tail ** 2 / 6)
        s_beam = Rs * (y_r - A.y_cap) / (A.P["beam_w"] * (A.P["beam_z"][1] - A.P["beam_z"][0]) ** 2 / 6)
        s_piv = Mg / (A.P["beam_w"] * (8.5 - 2.05) ** 2 / 6)
        s_shelf = Rs * 13.708 / 4 / (8.0 * 2.0 ** 2 / 6)
        p_notch = Rk / (A.P["rod_k"] * A.P["beam_w"])
        p_hub = s["RL"] / (A.P["rod_L"] * 11.4)
        pr("  %s: capstan force %.3f N, rear-shelf reaction %.3f N, key-rod reaction %.3f N, lever-rod reaction %.3f N"
           % (nm, N0, Rs, Rk, s["RL"]))
        pr("    thin tail (8 x %.1f) bending %.2f MPa | beam at capstan %.2f MPa | beam at pivot (notch) %.2f MPa"
           % (t_tail, s_tail, s_beam, s_piv))
        pr("    rear shelf plate (t2, span 13.7 between ribs) %.2f MPa | key notch on rod %.3f MPa | lever hub on rod %.3f MPa"
           % (s_shelf, p_notch, p_hub))
        R[nm]["stress"] = dict(tail=s_tail, beam=s_beam, piv=s_piv, shelf=s_shelf, Rs=Rs, N0=N0)
        worst = max(worst, s_tail, s_beam, s_piv, s_shelf)
    pr("  lever carrier: steel carries the lever load; PETG only clamps it (web moment < 0.1 MPa)")
    # lever rod Ø3: supports at x 0.7, 41.1, 123.4, 163.8 -> worst span 82.3 mm with 6 levers (4 white + 2 black typical)
    I3 = math.pi * 3 ** 4 / 64
    w = (4 * R["white"]["A"].statics(1e-4)["RL"] + 2 * R["black"]["A"].statics(1e-4)["RL"]) / 82.3
    d3 = 5 * w * 82.3 ** 4 / (384 * E_ST * I3)
    pr("  lever rod SUS 3 mm, span 82.3 mm between fins (x41.1 / x123.4), 6 levers at rest: sag %.3f mm" % d3)
    pr("  key rod SUS 4 mm lies in a continuous groove of the balance rail: no span")
    # up-stop rail: SS400 flat bar 3T x 19 (y149-168) lying flat in slots of the 4 fins (x0.5, 41.1, 123.4, 164.0)
    ff_peak = max(R["press"]["whiteff"]["up_peak"], R["press"]["blackff"]["up_peak"])
    fff_peak = max(R["press"]["whitefff"]["up_peak"], R["press"]["blackfff"]["up_peak"])
    Ir = 19 * 3.0 ** 3 / 12
    wch = 6 * ff_peak / 82.3
    d_r = 5 * wch * 82.3 ** 4 / (384 * E_ST * Ir)
    s_r = wch * 82.3 ** 2 / 8 / (19 * 3.0 ** 2 / 6)
    d_1 = fff_peak * 82.3 ** 3 / (48 * E_ST * Ir)
    pr("  up-stop rail 3T x 19 steel, span 82.3: 6-key ff chord (6 x %.1f N peak) sag %.3f mm, stress %.0f MPa;"
       " single fff hit %.1f N at mid-span sag %.3f mm" % (ff_peak, d_r, s_r, fff_peak, d_1))
    pr("  -> the up-stop must be a steel rail anchored in the fins (a PETG cover plate would lift/deflect)")
    R["rail"] = dict(d_r=d_r, s_r=s_r, ff_peak=ff_peak, fff_peak=fff_peak)
    pr("  -> max constant plastic stress %.2f MPa (target < 2)" % worst)
    R["stress_max"] = worst

    section("J. ENVELOPE")
    zmax = max(R["white"]["clear"]["steel_top_max_z"], R["black"]["clear"]["steel_top_max_z"])
    z_us = max(W.z_us, B.z_us)
    z_ci = z_us + P0["upstop_felt"] + 3.0          # felt + 3T steel up-stop rail; dust cover sits on the rail
    z_cov = z_ci + P0["cover_plate"]
    zlow = min(W.kz(W.front, W.a_dip) - 20.0, W.kz(W.p_stop, W.a_dip))
    pr("  depth used y0..212 (key lip moves to y%.2f at dip); total instrument depth 212 + 3 + 195 = 410 mm"
       % W.kp(W.front, W.a_dip)[0])
    pr("  key top z%.1f (white) / z%.1f (black); highest moving part = steel corner z%.2f (incl. ff over-travel)"
       % (P0["key_top"], P0["black_top"], zmax))
    pr("  lever up-stop felt face z%.2f -> felt 2T -> steel rail top z%.2f -> dust cover top z%.2f (v3: z59.0, +%.1f mm)"
       % (z_us, z_ci, z_cov, z_cov - 59.0))
    pr("  lowest moving point: white key underside at the front at dip z%.2f; frame floor z5" % zlow)
    R["env"] = dict(zmax=zmax, z_cov=z_cov, z_ci=z_ci, zlow=zlow)
    section("J2. WHY v3 COVER z59 CANNOT BE KEPT")
    lim = 59.0 - P0["cover_plate"] - 3.0 - P0["upstop_felt"]
    pr("  under a z59 cover the steel may reach z%.1f at dip (cover 2.5 + rail 3 + felt 2 above it)" % lim)
    best = None
    for yc in [184.0 + 0.5 * i for i in range(17)]:
        Pq = dict(P0); Pq["y_cap_w"] = yc
        lo, hi = 1.0, 40.0
        for _ in range(40):
            m = (lo + hi) / 2; Pq["steel_h"] = m
            Aq = Action(Pq, False)
            if max(Aq.lz(c, Aq.b_dip) for c in Aq.corners) < lim:
                lo = m
            else:
                hi = m
        Pq["steel_h"] = lo
        Aq = Action(Pq, False); sq = Aq.statics(1e-4)
        if best is None or sq["DW"] > best[1]:
            best = (yc, sq["DW"], lo, sq["meff"])
    pr("  best case: capstan y%.1f, steel h %.1f mm -> DW only %.1f g (target 47-55), m_eff %.1f g" % (best[0], best[2], best[1], best[3]))
    pr("  if the control board were moved off the tail zone the key beam could drop 9 mm (beam bottom z12.5 on a"
       " low balance rail): cover top would still be z%.1f > z59" % (z_cov - 9.0))
    R["z59"] = best

    section("K. MASS, FILAMENT, PRINT TIME (PETG 1.25 g/cm3, 15 g/h)")
    kw = W.key.mass_of(RHO_PETG); kb = B.key.mass_of(RHO_PETG); lv = W.lev.mass_of(RHO_PETG)
    st = W.lev.mass_of(RHO_ST)
    g = lambda V, fill=1.0: V * fill * RHO_PETG
    frame_v3 = 175.0
    spine_rail = g(13 * 163.5 * 15.7, 0.35)
    back_stop = g(6 * 163.5 * 14.7, 0.35)
    bal_rail = g(8 * 163.5 * 14.5, 0.35)
    shelf = g(13 * 163.5 * 2 + 10 * 13 * 1.2 * 13)
    posts = g(2 * 61 * 1.6 * (z_ci - 5) + 2 * 61 * 0.8 * (z_ci - 5), 0.8)   # 4 fins y148-209
    wall_up = g((z_ci - 56.5) * 3 * 164.5)
    frame = frame_v3 - spine_rail - back_stop + bal_rail + shelf + posts + wall_up
    cover = g(164.5 * (212 - 145) * 2.5 + 164.5 * 2 * (z_ci - 44.5) + 11 * 1.2 * 30 * 8 + 164.5 * 1.2 * 20, 0.9)
    sensor_bar = 17.0
    mod = 7 * kw + 5 * kb + 12 * lv + frame + cover + sensor_bar
    pr("  per key: white %.1f g, black %.1f g, lever carrier %.1f g (+ steel %.1f g)" % (kw, kb, lv, st))
    pr("  frame: v3 %.0f - spine rail %.1f - leaf back-stop rail %.1f + balance rail %.1f + rear shelf/ribs %.1f"
       " + 4 fins %.1f + taller rear wall %.1f = %.1f g" % (frame_v3, spine_rail, back_stop, bal_rail, shelf, posts, wall_up, frame))
    pr("  cover (taller, with up-stop ribs) %.1f g ; sensor bar %.0f g" % (cover, sensor_bar))
    pr("  module (C-B) printed: %.0f g = %.1f h" % (mod, mod / 15))
    ends = (242.0 * 1.1) + 3 * kw + 1 * kb + 4 * lv          # end parts A0-B0 (2 white + 1 black) and C8 (1 white)
    other = 200 + 64 + 310 + 388 + 12                        # coupons, grille, speaker fronts, rear-bar prints, bracket (v3)
    spare = 7 * kw + 5 * kb                                   # spare key set (R29), no spare levers
    tot = 7 * mod + ends + other + spare
    pr("  88 keys: 7 modules + end parts %.0f g + other v3 prints %.0f g + spare keys %.0f g = %.2f kg, %.0f h"
       % (ends, other, spare, tot / 1000, tot / 15))
    steel_oct = 12 * st
    steel_88 = 88 * st
    pr("  steel: %.1f g per lever, %.0f g per octave, %.2f kg for 88 keys; module mass incl. steel ~%.2f kg"
       % (st, steel_oct, steel_88 / 1000, (mod + steel_oct + 60 + 26) / 1000))
    pr("  bed: longest part = frame 164.5 x 212 (fits 220 x 220); key 199 x 22.5; lever 64 x 13; cover 164.5 x 67")
    rod4 = math.pi * 2.0 ** 2 * 163.5 * 7.93e-3
    rod3 = math.pi * 1.5 ** 2 * 163.5 * 7.93e-3
    rail = 3 * 19 * 163 * RHO_ST
    pr("  per module hardware: SUS 4 rod %.1f g, SUS 3 rod %.1f g, up-stop rail 3x19x163 %.1f g" % (rod4, rod3, rail))
    # key service: lever swung up (weight up) until its rear-top corner meets the rear wall inner face y209
    bb = 0.0
    while W.lp(W.corners[1], bb)[0] < 209.0 and bb < 1.5:
        bb += 0.001
    pr("  key removal: lever can be swung up %.1f deg before its rear-top corner touches the rear wall; capstan"
       " then clears by %.1f mm (enough to lift the key notch 2.05 mm off its rod)"
       % (math.degrees(bb), W.lz((W.y_cap, P0["z_c"]), bb) - P0["z_c"]))
    R["mass"] = dict(kw=kw, kb=kb, lv=lv, st=st, mod=mod, tot=tot, steel_oct=steel_oct, steel_88=steel_88, frame=frame, cover=cover)

    section("L. PURCHASED PARTS AND COST DELTA vs v3 (KRW)")
    rod_len = 7 * 163.5 + 45 + 37                               # modules + end parts
    items = [
        ("SS400 flat bar 9T x 50, 6 m (88 blocks x %.1f mm + 2 mm kerf = %.2f m)" % (W.h, 88 * (W.h + 2) / 1000), 1, 14000, "estimate (9T x 32 6 m listed 8,542-9,085; scaled by width)"),
        ("SUS304 round bar 4 mm x 4 m (key rods, %.2f m used)" % (rod_len / 1000), 1, 7000, "estimate (onezaze/changhojajae 3-14 mm 4 m listings)"),
        ("SUS304 round bar 3 mm x 4 m (lever rods, %.2f m used)" % (rod_len / 1000), 1, 6000, "estimate"),
        ("SS400 flat bar 3T x 19, 2 m (up-stop rails, 9 pieces)", 1, 3000, "estimate"),
        ("extra wool felt 1.5T/2T (capstan strips, rest pads, up-stop strips)", 1, 5000, "estimate (consumable)"),
    ]
    removed = [
        ("M3 x 35 clamp screws (v3 spine), 4/module + 2/end part", 32, 100),
        ("M3 x 10 flat-point set screws + nuts", 32, 150),
        ("brass disc 8 x 1 (set-screw seats)", 32, 250),
        ("M3 nuts (clamp + set screw)", 64, 30),
    ]
    add = sum(q * u for _, q, u, _ in items[:4])
    rem = sum(q * u for _, q, u in removed)
    for n_, q, u, src in items:
        pr("  + %-70s %3d x %6d = %7d  [%s]" % (n_, q, u, q * u, src))
    for n_, q, u in removed:
        pr("  - %-70s %3d x %6d = %7d  [estimate]" % (n_, q, u, q * u))
    pr("  optional: cutting service 88 cuts x 500 = 44,000 (estimate) - or cut by hand (bandsaw/hacksaw), 0")
    pr("  optional: 88 assist springs (SUS 0.30 wire, OD6, ~6 coils) x 150 = 13,200 (estimate) - not in the baseline")
    delta = add - rem
    pr("  base (non-consumable) delta = +%d - %d = %+d KRW  (felt +5,000 is consumable)" % (add, rem, delta))
    R["cost"] = dict(add=add, rem=rem, delta=delta, items=items)
    return R


def summary(P0, W, B, R):
    section("M. SUMMARY (metrics used in the structured result)")
    sw, sb = R["white"]["s"], R["black"]["s"]
    out = dict(
        dw_white_g=sw["DW"], uw_white_g=sw["UW"], dw_black_g=sb["DW"], uw_black_g=sb["UW"],
        dw_white_lip_g=R["lip"]["DW"], friction_white_g=sw["f"],
        m_eff_white_g=sw["meff"], m_eff_white_lip_g=R["lip"]["meff"], m_eff_black_g=sb["meff"],
        front_back_ratio=R["y90"]["DW"] / sw["DW"],
        t40_white_ms=R["rel"]["white"]["t40"], full_return_ms_white=R["rel"]["white"]["t100"],
        t40_black_ms=R["rel"]["black"]["t40"], full_return_ms_black=R["rel"]["black"]["t100"],
        retrigger_hz_white=500.0 / R["rel"]["white"]["t40"], retrigger_hz_black=500.0 / R["rel"]["black"]["t40"],
        spring_t40_white=R["rel"]["white_spring"]["t40"], spring_full_white=R["rel"]["white_spring"]["t100"],
        magnet_travel_white_mm=R["white"]["mag"][2], magnet_travel_black_mm=R["black"]["mag"][2],
        gap_bottom_white=R["white"]["mag"][1], gap_bottom_black=R["black"]["mag"][1],
        max_plastic_rest_stress_mpa=R["stress_max"], max_z_mm=R["env"]["zmax"], cover_top=R["env"]["z_cov"],
        steel_g_per_octave=R["mass"]["steel_oct"], steel_kg_88=R["mass"]["steel_88"] / 1000,
        filament_g_88=R["mass"]["tot"], print_h_88=R["mass"]["tot"] / 15, cost_delta_krw=R["cost"]["delta"],
        min_clear_moving=min(min(v for k, v in R[n]["clear"].items() if k not in ("steel_top_max_z", "magnet_face_vs_element"))
                             for n in ("white", "black")),
        min_gap_sensor=min(R["white"]["mag"][1], R["black"]["mag"][1]),
        steel_rise_front_white=W.lz(W.corners[0], W.b_dip) - W.corners[0][1],
    )
    for k, v in out.items():
        pr("  %-28s %10.2f" % (k, v))
    return out


if __name__ == "__main__":
    P0, W, B, R = main()
    main2(P0, W, B, R)
    main3(P0, W, B, R)
    summary(P0, W, B, R)
