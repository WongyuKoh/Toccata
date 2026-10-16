#!/usr/bin/env python3
"""Toccata v4 - concept S1 "mini seesaw" (balance-pin key, steel tail weight, felt stops).

Every number reported for S1 comes out of this file.  Run:  python3 calc.py > results.txt

Coordinates (mm, same as v3): x across, y = 0 at the white key front lip (+y away from the player),
z = 0 desk.  Rotation angle phi > 0 = key front goes DOWN (counter-clockwise in the (y, z) plane).
Units in the statics: g, mm, N (1 gf = 9.80665e-3 N).  The dynamics run in SI internally.

Architecture (see design.md):
  * key = one printed PETG seesaw, steel cross pin (dowel 3x10) at y_b resting in an open notch on a
    printed fin of the balance rail (the fin also guides x).  Load on the notch is always downward.
  * rest (up) stop  = v3 front hook: key crossbar presses UP on a felt under the frame hook (white y12,
    black y78).  Tail weight + spring hold it there.
  * down stop       = the steel tail bar hits a felt under the "tail stop bar" (screwed to the rear wall).
    It sits in front of the centre of percussion so the pivot pin is never lifted by the impact.
  * second down stop = v3 front felt, 0.3 mm later (takes the static finger force).
  * return          = gravity of the steel bar + a steel compression spring in a well at the tail end
    (only the part gravity cannot give inside the 212 mm frame; see the scans at the end).
"""
import math

GF = 9.80665e-3            # N per gram-force
RHO_PETG = 1.25e-3         # g/mm^3 (Bambu PETG Basic)
RHO_STEEL = 7.85e-3
RHO_NDFEB = 7.5e-3
E_PETG = 1950.0            # MPa
G_WIRE = 79000.0           # MPa, spring steel / SUS304 ~ 69000 (we size with piano wire)
FIL_G_PER_H = 15.0         # brief: 15 g/h
WASTE = 1.10

# ------------------------------------------------------------------ v3 interfaces (kept)
V3 = dict(key_bot=23.5, white_top=43.5, black_top=55.5, dip_w=10.0, dip_b=9.5,
          y_mag_w=65.8, y_mag_b=64.2, y_elem=67.0, z_elem_w=12.68, z_elem_b=10.15, gap_min=3.0,
          frame_depth=212.0, rear_wall_y=(209.0, 212.0), cover_under=56.5, cover_top=59.0,
          floor_top=5.0, v3_total_depth=410.0, sensor_bar=(59.0, 77.5),
          hook_w=(11.5, 14.5), hook_b=(77.5, 80.5), crossbar_w=(10.5, 14.0), crossbar_b=(76.5, 80.0),
          hook_under=28.1, felt=3.0, front_plate_w=(2.7, 10.5), front_plate_b=(52.7, 59.0),
          tab_w_y=(16.8, 25.0), tab_b_y=(84.0, 91.0))

# ------------------------------------------------------------------ S1 parameters (iterated, final values)
P = dict(
    y_b=140.0,          # balance pin (key pivot) y  (chosen from the sweep in [11])
    z_p=27.0,           # pin axis z (3.5 above the key underside)
    pin_d=3.0, pin_len=10.0,
    skin=2.0, wall=1.2, rib=1.2,
    w_head=22.5, w_narrow=13.2, w_tail=12.708,      # tail on a uniform 164.5/12 grid behind y146, gap 1.0
    boss_half=6.0,      # pivot boss y_b +- 6 (solid, 75 % fill)
    y_end=206.5,        # tail end (rear wall inner face y209; the low keel corner moves back up to 2 mm when pressed)
    z_kb_w=11.0,        # white tail keel bottom at rest (USB cable lane z5..10.5 below it)
    bar_t=9.0, bar_h=32.0,          # steel flat bar 9 x 32 standing on edge
    bar_rear=198.0,                 # bar rear end (spring well behind it)
    bar_len_w=31.0, bar_len_b=31.0, # cut lengths (mm)
    well_y=202.5, well_id=6.6, well_wall=1.0,
    stop_bar_z=(51.2, 56.2), stop_felt=(186.0, 198.0), spring_seat_depth=3.0,
    # helper spring (one part number for white and black; preload set by the printed well depth)
    spring=dict(d=0.4, D_out=6.0, L0=45.0, n_act=40),
    front_felt_gap=0.50,            # front felt touches this much (at the front plate) after the tail felt
    # friction model
    mu_pin=0.30, mu_bush=0.25, bush_pre=0.05, lat_frac=0.05, fin_r=3.0,
    # felt model (linearised 3T wool felt): E_felt such that v3's own figure (8x3 piece, 4.8 mJ -> 52 %)
    # gives ~0.5 MPa; high-density felt nominal 1.0 MPa.  Damping ratio 0.30 (restitution ~0.37)
    E_felt=1.0, zeta=0.30,
    # control board moved under the key front arm (between black hooks y93 and balance rail)
    board_y=(94.0, 133.0), board_x=(47.25, 117.25), board_top_components=15.0,
    dw_target=50.0,
    front_lead=0.0,     # optional white key lead (steel balls d10 in a head pocket y28..48), see [10b]
)


# ------------------------------------------------------------------ rigid-body bookkeeping
class Part:
    def __init__(self, name, m, y, z, Iown, mat):
        self.name, self.m, self.y, self.z, self.Iown, self.mat = name, m, y, z, Iown, mat


def box(name, y0, y1, z0, z1, wx, rho=RHO_PETG, fill=1.0, mat="PETG"):
    ly, lz = abs(y1 - y0), abs(z1 - z0)
    m = ly * lz * wx * rho * fill
    return Part(name, m, (y0 + y1) / 2, (z0 + z1) / 2, m * (ly ** 2 + lz ** 2) / 12, mat)


def point(name, m, y, z, ly=0.0, lz=0.0, mat="PETG"):
    return Part(name, m, y, z, m * (ly ** 2 + lz ** 2) / 12, mat)


class Body:
    def __init__(self, parts):
        self.parts = [p for p in parts if p.m > 0]

    @property
    def m(self):
        return sum(p.m for p in self.parts)

    def com(self):
        m = self.m
        return (sum(p.m * p.y for p in self.parts) / m, sum(p.m * p.z for p in self.parts) / m)

    def I_about(self, c):
        return sum(p.Iown + p.m * ((p.y - c[0]) ** 2 + (p.z - c[1]) ** 2) for p in self.parts)

    def mass_of(self, mat):
        return sum(p.m for p in self.parts if p.mat == mat)


def rot(p, c, a):
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def solve_phi(pivot, pt, drop):
    lo, hi = 0.0, 0.4
    for _ in range(80):
        m = (lo + hi) / 2
        if pt[1] - rot(pt, pivot, m)[1] < drop:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


# ------------------------------------------------------------------ key geometry
def tail_parts(P, z_kb, bar_len, black, boss_w=None):
    """pivot boss, pin, keel/pocket, steel bar, spring well (common to white and black keys)."""
    yb, s, w, wt = P["y_b"], P["skin"], P["wall"], P["w_tail"]
    boss_w = wt if boss_w is None else boss_w
    zb, ztop = V3["key_bot"], V3["white_top"]
    b0, b1 = yb - P["boss_half"], yb + P["boss_half"]
    bar_z0 = z_kb + w                                  # bar stands on a 1.2 floor
    bar_z1 = bar_z0 + P["bar_h"]
    z_tt = bar_z1                                      # pocket walls end flush with the bar top
    has_well = P.get("well_b" if black else "well_w", P.get("well", True))
    bar_rear = P["bar_rear"] if has_well else P["y_end"] - w
    y_bar0 = bar_rear - bar_len
    inner = wt - 2 * w
    parts = [
        box("pivot boss (75 %)", b0, b1, zb, ztop, boss_w, fill=0.75),
        point("pivot pin 3x10 (steel)", math.pi * 1.5 ** 2 * P["pin_len"] * RHO_STEEL, yb, P["z_p"], 3, 3, "steel"),
        # tail box behind the boss: two side walls, floor, top skin in front of the bar, end walls
        box("tail side walls", b1, P["y_end"], z_kb, z_tt, 2 * w),
        box("tail floor", b1, P["y_end"], z_kb, z_kb + w, inner),
        box("tail top skin (front of bar)", b1, y_bar0 - w, z_tt - w, z_tt, inner),
        box("keel front wall", b1, b1 + w, z_kb, zb, inner),
        box("bar front wall", y_bar0 - w, y_bar0, z_kb, z_tt, inner),
        box("bar rear wall", bar_rear, bar_rear + w, z_kb, z_tt, inner),
        box("tail end wall", P["y_end"] - w, P["y_end"], z_kb, z_tt, inner),
    ]
    if has_well:
        ro, ri = P["well_id"] / 2 + P["well_wall"], P["well_id"] / 2
        parts.append(point("spring well tube", math.pi * (ro ** 2 - ri ** 2) * (z_tt - bar_z0) * RHO_PETG,
                           P["well_y"], (z_tt + bar_z0) / 2, 2 * ro, z_tt - bar_z0))
        sp = spring_props(P)
        parts.append(point("spring (1/3 of its mass)", sp["mass"] / 3, P["well_y"], bar_z0 + 10, 0, 0, "steel"))
    else:
        parts = [p for p in parts if p.name != "bar rear wall"]
    parts.append(box("steel bar %gx%gx%g" % (P["bar_t"], P["bar_h"], bar_len), y_bar0, bar_rear,
                     bar_z0, bar_z1, P["bar_t"], RHO_STEEL, P.get("bar_fill", 1.0), "steel"))
    feat = dict(z_tt=z_tt, bar=(y_bar0, bar_rear, bar_z0, bar_z1), well_bottom=(P["well_y"], bar_z0),
                keel=(b1, P["y_end"], z_kb), well=has_well)
    return parts, feat


def white_key(P):
    s, w, r = P["skin"], P["wall"], P["rib"]
    zb, zt = V3["key_bot"], V3["white_top"]
    yb = P["y_b"]
    wh, wn, wt = P["w_head"], P["w_narrow"], P["w_tail"]
    b0 = yb - P["boss_half"]
    parts = [
        box("head top skin", 0.0, 50.0, zt - s, zt, wh),
        box("narrow top skin", 50.0, min(146.0, b0), zt - s, zt, wn),
        box("tail top skin (y146..boss)", 146.0, max(146.0, b0), zt - s, zt, wt),
        box("front wall", 1.5, 2.7, zb, zt - s, wh),
        box("head side walls", 1.5, 50.0, zb, zt - s, 2 * w),
        box("notch step wall", 48.8, 50.0, zb, zt - s, wh - wn),
        box("narrow side walls", 50.0, min(146.0, b0), zb, zt - s, 2 * w),
        box("tail side walls (y146..boss)", 146.0, max(146.0, b0), zb, zt - s, 2 * w),
        box("front plate (front felt contact)", 2.7, 10.5, zb, zb + w, wh - 2 * w),
        box("guide ribs x2 (hook tab slot)", 10.5, 27.0, zb, zt - s, 2 * w),
        box("crossbar (hook contact)", 10.5, 14.0, zb, zb + 1.6, 8.6),
        point("magnet boss tube", math.pi * (3.8 ** 2 - 2.6 ** 2) * (zt - s - zb) * RHO_PETG, V3["y_mag_w"],
              (zt - s + zb) / 2, 7.6, zt - s - zb),
        point("magnet 5x2 N35", math.pi * 2.5 ** 2 * 2 * RHO_NDFEB, V3["y_mag_w"], zb + 1.0, 5, 2, "magnet"),
    ]
    for yr in (26.4, 100.0, 128.0):
        parts.append(box("rib y%g" % yr, yr - r / 2, yr + r / 2, zb + 4.0, zt - s, wn - 2 * w))
    if P.get("front_lead", 0.0) > 0:
        parts.append(box("key-lead pocket walls/floor", 27.0, 48.8, zb, zb + 11.0, 2.4 + 20.0 * 1.2 / 11.0))
        # key lead: steel balls d10 (4.11 g each) in the head behind the hook tab, y32..42, 2 x 2 in x/y, one layer
        parts.append(point("front lead: %d steel balls d10" % round(P["front_lead"] / 4.11), P["front_lead"], 38.0, 29.7,
                           20, 10, "steel"))
    tp, feat = tail_parts(P, P["z_kb_w"], P["bar_len_w"], False, wn if b0 + 2 * P["boss_half"] <= 146.5 else wt)
    parts += tp
    feat.update(front_top=(0.0, zt), finger=(13.0, zt), finger0=(0.0, zt), finger90=(90.0, zt),
                mag=(V3["y_mag_w"], zb), elem=(V3["y_elem"], V3["z_elem_w"]),
                hook=((V3["crossbar_w"][0] + V3["crossbar_w"][1]) / 2, zb + 1.6),
                hook_area=(V3["crossbar_w"][1] - V3["hook_w"][0]) * 8.3,
                front=((V3["front_plate_w"][0] + V3["front_plate_w"][1]) / 2, zb),
                front_area=(V3["front_plate_w"][1] - V3["front_plate_w"][0]) * (wh - 2 * w),
                tab_y=sum(V3["tab_w_y"]) / 2, dip=V3["dip_w"], black=False)
    return Body(parts), feat


def black_key(P):
    s, w, r = P["skin"], P["wall"], P["rib"]
    zb, zt, ztb = V3["key_bot"], V3["white_top"], V3["black_top"]
    yb = P["y_b"]
    b0 = yb - P["boss_half"]
    yf = 51.5
    parts = [
        box("black top skin (raised part ends y144)", 52.5, 144.0, ztb - s, ztb, 9.5),
        box("black upper side walls", yf, 144.0, zt, ztb - s, 2 * w),
        box("black lower side walls", yf, min(146.0, b0), zb, zt, 2 * w),
        box("black front wall", yf, yf + w, zb, ztb - s, 11.0 - 2 * w),
        box("black front plate", 52.7, 59.0, zb, zb + w, 11.0 - 2 * w),
        box("black crossbar", 76.5, 80.0, zb, zb + 1.6, 8.6),
        point("magnet boss tube", math.pi * (3.8 ** 2 - 2.6 ** 2) * (ztb - s - zb) * RHO_PETG, V3["y_mag_b"],
              (ztb - s + zb) / 2, 7.6, ztb - s - zb),
        point("magnet 5x2 N35", math.pi * 2.5 ** 2 * 2 * RHO_NDFEB, V3["y_mag_b"], zb + 1.0, 5, 2, "magnet"),
        box("black tail top skin (y146..boss)", 146.0, max(146.0, b0), zt - s, zt, P["w_tail"]),
        box("black tail side walls (y146..boss)", 146.0, max(146.0, b0), zb, zt - s, 2 * w),
    ]
    for yr in (100.0, 128.0):
        parts.append(box("rib y%g" % yr, yr - r / 2, yr + r / 2, zb + 4.0, ztb - s, 11.0 - 2 * w))
    # black tail keel lower so the bigger black tail rise meets the same stop felt (set in design())
    tp, feat = tail_parts(P, P["z_kb_b"], P["bar_len_b"], True, 11.0 if b0 + 2 * P["boss_half"] <= 146.5 else P["w_tail"])
    parts += tp
    feat.update(front_top=(52.5, ztb), finger=(62.5, ztb), finger0=(52.5, ztb), finger90=(90.0, ztb),
                mag=(V3["y_mag_b"], zb), elem=(V3["y_elem"], V3["z_elem_b"]),
                hook=((V3["crossbar_b"][0] + V3["crossbar_b"][1]) / 2, zb + 1.6),
                hook_area=(V3["crossbar_b"][1] - V3["hook_b"][0]) * 8.3,
                front=((V3["front_plate_b"][0] + V3["front_plate_b"][1]) / 2, zb),
                front_area=(V3["front_plate_b"][1] - V3["front_plate_b"][0]) * (11.0 - 2 * w),
                tab_y=sum(V3["tab_b_y"]) / 2, dip=V3["dip_b"], black=True)
    return Body(parts), feat


# ------------------------------------------------------------------ spring
def spring_props(P):
    sp = P["spring"]
    d, Do, n = sp["d"], sp["D_out"], sp["n_act"]
    D = Do - d
    k = G_WIRE * d ** 4 / (8 * D ** 3 * n)                  # N/mm
    C = D / d
    wahl = (4 * C - 1) / (4 * C - 4) + 0.615 / C
    solid = (n + 2) * d
    mass = math.pi * D * (n + 2) * math.pi * d ** 2 / 4 * RHO_STEEL
    return dict(k=k, D=D, C=C, wahl=wahl, solid=solid, mass=mass, L0=sp["L0"], d=d, D_out=Do, n=n)


# ------------------------------------------------------------------ one key: statics
class Key:
    def __init__(self, P, black):
        self.P, self.black = P, black
        self.body, self.f = (black_key if black else white_key)(P)
        self.piv = (P["y_b"], P["z_p"])
        self.m = self.body.m
        self.G = self.body.com()
        self.Ip = self.body.I_about(self.piv)
        self.IG = self.body.I_about(self.G)
        f = self.f
        self.phi_bot = solve_phi(self.piv, f["front_top"], f["dip"])
        self.sp = spring_props(P)
        self.z_seat = P["stop_bar_z"][0] + P["spring_seat_depth"]
        # stop felts
        self.k_hook = P["E_felt"] * f["hook_area"] / V3["felt"]
        self.k_front = P["E_felt"] * f["front_area"] / V3["felt"]
        a_c = (P["stop_felt"][1] - P["stop_felt"][0]) * P["bar_t"]
        self.k_catch = P["E_felt"] * a_c / V3["felt"]
        self.catch_pts = [(P["stop_felt"][0] + 2.0, f["z_tt"]), (P["stop_felt"][1] - 2.0, f["z_tt"])]

    # geometry helpers --------------------------------------------------
    def zpt(self, pt, phi, h=0.0):
        return rot(pt, self.piv, phi)[1] + h

    def spring_len(self, phi, h=0.0):
        return self.z_seat - self.zpt(self.f["well_bottom"], phi, h)

    def spring_force(self, phi, h=0.0):
        if not self.f["well"]:
            return 0.0
        L = self.spring_len(phi, h)
        return max(0.0, self.sp["k"] * (self.sp["L0"] - L))

    def lever(self, pt, phi=0.0):
        """d z_pt / d phi (mm per rad); negative for points in front of the pivot."""
        dy, dz = pt[0] - self.piv[0], pt[1] - self.piv[1]
        return dy * math.cos(phi) - dz * math.sin(phi)

    def Q_grav(self, phi):
        """generalized force of gravity in the front-DOWN direction, N*mm."""
        return -sum(p.m * GF * self.lever((p.y, p.z), phi) for p in self.body.parts)

    def Q_spring(self, phi):
        return -self.spring_force(phi) * self.lever(self.f["well_bottom"], phi)

    def T_return(self, phi):
        """torque lifting the front (N*mm) = -(Q_grav + Q_spring)."""
        return -(self.Q_grav(phi) + self.Q_spring(phi))

    def T_fric(self, F_finger, phi=0.0):
        P = self.P
        Rp = self.m * GF + self.spring_force(phi) + F_finger          # pin reaction (all downward)
        t_pin = P["mu_pin"] * Rp * P["pin_d"] / 2
        n_bush = 2 * P["bush_pre"] + P["lat_frac"] * F_finger
        t_tab = P["mu_bush"] * n_bush * (self.piv[0] - self.f["tab_y"])
        t_fin = P["mu_pin"] * P["lat_frac"] * F_finger * P["fin_r"]
        return t_pin + t_tab + t_fin, dict(pin=t_pin, tab=t_tab, fin=t_fin, Rp=Rp)

    def force_at(self, pt, phi, sense):
        """finger force (g) at pt: sense=+1 start moving down (DW), -1 just held while rising (UW)."""
        lev = -self.lever(pt, phi)
        F = self.T_return(phi) / lev
        for _ in range(30):
            tf, _ = self.T_fric(F * 1.0, phi)
            F = (self.T_return(phi) + sense * tf) / lev
        return F / GF

    def statics(self):
        f = self.f
        out = {}
        out["DW"] = self.force_at(f["finger"], 0.0, +1)
        out["UW"] = self.force_at(f["finger"], self.phi_bot, -1)
        out["DW_bot"] = self.force_at(f["finger"], self.phi_bot, +1)
        out["UW_rest"] = self.force_at(f["finger"], 0.0, -1)
        out["DW0"] = self.force_at(f["finger0"], 0.0, +1)
        out["UW0"] = self.force_at(f["finger0"], 0.0, -1)
        out["DW90"] = self.force_at(f["finger90"], 0.0, +1)
        out["ratio_90"] = out["DW90"] / out["DW"]
        # balance and friction from DW and UW taken at the SAME position (rest); with a rising spring the UW
        # measured from the bottom (out["UW"]) is higher than the UW near rest.
        out["BW"] = (out["DW"] + out["UW_rest"]) / 2
        out["fric"] = (out["DW"] - out["UW_rest"]) / 2
        out["UW_min"] = min(out["UW"], out["UW_rest"])
        tf, parts = self.T_fric(out["DW"] * GF, 0.0)
        lev = -self.lever(f["finger"])
        out["fric_parts_g"] = {k: v / lev / GF for k, v in parts.items() if k != "Rp"}
        # contributions to the return torque at rest (as grams at the finger)
        tg = -self.Q_grav(0.0)
        ts = -self.Q_spring(0.0)
        out["grav_g"], out["spring_g"] = tg / lev / GF, ts / lev / GF
        out["grav_share"] = tg / (tg + ts)
        steel = [p for p in self.body.parts if p.mat == "steel" and "bar" in p.name]
        out["bar_torque_g"] = steel[0].m * (steel[0].y - self.piv[0]) / lev if steel else 0.0
        out["m_eff"] = self.Ip / lev ** 2
        out["m_eff0"] = self.Ip / self.lever(f["finger0"]) ** 2
        return out

    def sensor(self):
        f = self.f
        m0 = f["mag"]
        m1 = rot(m0, self.piv, self.phi_bot)
        e = f["elem"]
        gap0 = m0[1] - e[1]
        gap1 = m1[1] - e[1]
        return dict(gap_rest=gap0, gap_bot=gap1, travel=gap0 - gap1, dy_bot=m1[0] - m0[0],
                    y_bot=m1[0], elem_dy_bot=m1[0] - e[0])

    def cop(self):
        dG = self.G[0] - self.piv[0]
        return self.Ip / (self.m * dG) if dG > 0 else float("inf")


# ------------------------------------------------------------------ dynamics (2 DOF: pin lift h, rotation phi)
class Sim:
    """planar rigid key; pin y fixed by the notch walls, pin may lift (unilateral notch contact).
    Contacts: hook felt (up-stop), tail stop felt (2 pts), front felt, notch.  Coulomb friction at the pin
    (normal force = notch force) + tab bushing.  Helper spring force at the well bottom."""

    def __init__(self, K, front_gap=None, E_felt=None):
        self.K = K
        P = K.P
        s = 1e-3                     # mm -> m
        self.m = K.m * 1e-3          # kg
        self.Ip = K.Ip * 1e-9        # kg m^2
        self.dG = ((K.G[0] - K.piv[0]) * s, (K.G[1] - K.piv[1]) * s)
        ef = P["E_felt"] if E_felt is None else E_felt
        kf = lambda area: ef * area / V3["felt"] * 1e3      # N/m
        f = K.f
        rel = lambda pt: ((pt[0] - K.piv[0]) * s, (pt[1] - K.piv[1]) * s)
        self.g = 9.80665
        # stop planes (world z, m, relative to pin at rest)
        # hook: felt underside at rest height (zero compression at phi = 0)
        self.hook = (rel(f["hook"]), 0.0 + (f["hook"][1] - K.piv[1]) * s, kf(f["hook_area"]), -1)
        # tail stop felt: two points, plane = bar top at full dip (zero compression)
        if "felt_line" in P:          # common fixed felt line (defined by the white bar at full dip)
            y0_, z0_, y1_, z1_ = P["felt_line"]
            fl = lambda y: z0_ + (y - y0_) * (z1_ - z0_) / (y1_ - y0_)
            cz = [(fl(rot(p, K.piv, K.phi_bot)[0]) - K.piv[1]) * s for p in K.catch_pts]
        else:
            cz = [(K.zpt(p, K.phi_bot) - K.piv[1]) * s for p in K.catch_pts]
        a_c = (P["stop_felt"][1] - P["stop_felt"][0]) * P["bar_t"]
        self.catch = [(rel(p), cz[i], kf(a_c) / 2, -1) for i, p in enumerate(K.catch_pts)]
        # front felt: touches front_gap later (at the front plate centre)
        fg = P["front_felt_gap"] if front_gap is None else front_gap
        zf = (K.zpt(f["front"], K.phi_bot) - fg - K.piv[1]) * s
        self.front = (rel(f["front"]), zf, kf(f["front_area"]), +1)
        self.k_notch = 2.0e6          # N/m, PETG notch local stiffness (2000 N/mm)
        self.zeta = P["zeta"]
        self.mu_pin, self.r_pin = P["mu_pin"], P["pin_d"] / 2 * s
        self.t_tab = P["mu_bush"] * 2 * P["bush_pre"] * (K.piv[0] - f["tab_y"]) * s   # N m (no finger)
        self.well = rel(f["well_bottom"])
        self.k_sp, self.L0 = (K.sp["k"] * 1e3 if f["well"] else 0.0), K.sp["L0"] * s
        self.z_seat = (K.z_seat - K.piv[1]) * s
        self.finger = rel(f["finger"])
        self.mag = rel(f["mag"])

    @staticmethod
    def zrel(pt, phi, h):
        return h + pt[0] * math.sin(phi) + pt[1] * math.cos(phi)

    @staticmethod
    def vrel(pt, phi, hd, phd):
        return hd + (pt[0] * math.cos(phi) - pt[1] * math.sin(phi)) * phd

    @staticmethod
    def lev(pt, phi):
        return pt[0] * math.cos(phi) - pt[1] * math.sin(phi)

    def meff(self, pt):
        r = abs(pt[0])
        return self.Ip / r ** 2 if r > 1e-6 else self.m

    def contact(self, c, phi, h, hd, phd):
        pt, zs, k, sense = c
        z = self.zrel(pt, phi, h)
        v = self.vrel(pt, phi, hd, phd)
        if sense < 0:                 # ceiling above the point: penetration when z > zs
            d, dv = z - zs, v
        else:                         # floor below the point
            d, dv = zs - z, -v
        if d <= 0:
            return 0.0, 0.0
        c_d = 2 * self.zeta * math.sqrt(k * self.meff(pt))
        Fm = max(0.0, k * d + c_d * dv)
        return (-Fm if sense < 0 else Fm), d

    def forces(self, s, F_f):
        h, phi, hd, phd = s
        Qh = -self.m * self.g
        c = self.lev(self.dG, phi)
        Qp = -self.m * self.g * c
        out = {}
        for name, cs in (("hook", [self.hook]), ("catch", self.catch), ("front", [self.front])):
            tot = 0.0
            for cc in cs:
                F, _ = self.contact(cc, phi, h, hd, phd)
                Qh += F
                Qp += F * self.lev(cc[0], phi)
                tot += F
            out[name] = tot
        # notch (pin at relative (0,0)): penetration when h < 0
        Fn = 0.0
        if h < 0:
            cn = 2 * 0.3 * math.sqrt(self.k_notch * self.m)
            Fn = max(0.0, -self.k_notch * h - cn * hd)
        Qh += Fn
        out["notch"] = Fn
        # spring (pushes the well bottom down)
        L = self.z_seat - self.zrel(self.well, phi, h)
        Fs = max(0.0, self.k_sp * (self.L0 - L))
        Qh -= Fs
        Qp -= Fs * self.lev(self.well, phi)
        out["spring"] = Fs
        # finger (down at the finger point)
        if F_f:
            Qh -= F_f
            Qp -= F_f * self.lev(self.finger, phi)
        # friction torque (regularised Coulomb)
        Tf = self.mu_pin * self.r_pin * Fn + self.t_tab
        Qp -= Tf * math.tanh(phd / 0.05)
        return Qh, Qp, c, out

    def deriv(self, s, F_f):
        h, phi, hd, phd = s
        Qh, Qp, c, _ = self.forces(s, F_f)
        m, I = self.m, self.Ip
        cp = -(self.dG[0] * math.sin(phi) + self.dG[1] * math.cos(phi))
        # [m, m c; m c, I] [hdd; phdd] = [Qh - m c' phd^2 ; Qp]
        a11, a12, a22 = m, m * c, I
        b1, b2 = Qh - m * cp * phd ** 2, Qp
        det = a11 * a22 - a12 * a12
        hdd = (b1 * a22 - a12 * b2) / det
        phdd = (a11 * b2 - a12 * b1) / det
        return (hd, phd, hdd, phdd)

    def step(self, s, dt, F_f):
        k1 = self.deriv(s, F_f)
        s2 = tuple(a + dt / 2 * b for a, b in zip(s, k1))
        k2 = self.deriv(s2, F_f)
        s3 = tuple(a + dt / 2 * b for a, b in zip(s, k2))
        k3 = self.deriv(s3, F_f)
        s4 = tuple(a + dt * b for a, b in zip(s, k3))
        k4 = self.deriv(s4, F_f)
        return tuple(a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(s, k1, k2, k3, k4))

    def settle(self, s, T=0.06, dt=4e-6, F_f=0.0):
        t = 0.0
        while t < T:
            s = self.step(s, dt, F_f)
            t += dt
        return s

    def mag_drop(self, s):
        """magnet drop from the design rest position (m)."""
        h, phi = s[0], s[1]
        return -(self.zrel(self.mag, phi, h) - self.mag[1])

    def run_return(self, dt=4e-6, T=0.20):
        """released at the bottom (tail felt contact, zero compression) with zero velocity."""
        K = self.K
        s = (0.0, K.phi_bot, 0.0, 0.0)
        # start from the static bottom equilibrium under a light 1 N hold, then release
        s = self.settle(s, 0.03, dt, F_f=1.0)
        d_bot = self.mag_drop(s)
        s = (s[0], s[1], 0.0, 0.0)
        # rest reference: settled rest position
        s_rest = self.settle((0.0, 0.0, 0.0, 0.0), 0.08, dt)
        d_rest = self.mag_drop(s_rest)
        travel = d_bot - d_rest
        t, t_rt, t_full, t_settle = 0.0, None, None, None
        hmax, bounce, last_out = 0.0, 0.0, 0.0
        first_hook = None
        while t < T:
            s = self.step(s, dt, 0.0)
            t += dt
            d = self.mag_drop(s) - d_rest
            if t_rt is None and d <= 0.6 * travel:
                t_rt = t
            _, _, _, out = self.forces(s, 0.0)
            if t_full is None and out["hook"] < 0:
                t_full = t
                first_hook = t
            if first_hook is not None:
                bounce = max(bounce, d)
            hmax = max(hmax, s[0])
            if abs(d) > 0.2e-3:
                last_out = t
        return dict(t_rt=t_rt, t_full=t_full, h_max=hmax, bounce=bounce, t_settle=last_out,
                    travel=travel, d_bot=d_bot, d_rest=d_rest)

    def run_impact(self, v, F_hold=2.0, dt=4e-6, T=0.04):
        """key arrives at the first down-stop with finger speed v (m/s) and the finger keeps pushing F_hold (N)."""
        K = self.K
        r = -self.lev(self.finger, K.phi_bot)
        phi0 = K.phi_bot - 0.3e-3 / r
        s = (0.0, phi0, 0.0, v / r)
        t, hmax, Fc, Ff, lift_t = 0.0, 0.0, 0.0, 0.0, 0.0
        phi_max = phi0
        while t < T:
            s = self.step(s, dt, F_hold)
            t += dt
            _, _, _, out = self.forces(s, F_hold)
            hmax = max(hmax, s[0])
            if s[0] > 1e-6:
                lift_t += dt
            Fc = max(Fc, -out["catch"])
            Ff = max(Ff, out["front"])
            phi_max = max(phi_max, s[1])
        over = (phi_max - K.phi_bot) * K.piv[0]
        return dict(h_max=hmax, lift_ms=lift_t * 1e3, F_catch=Fc, F_front=Ff, overtravel=over)

    def run_press(self, F, dt=4e-6, T=0.08):
        """from rest, constant finger force F (N) at the finger point."""
        s = self.settle((0.0, 0.0, 0.0, 0.0), 0.08, dt)
        phi_c = self.K.phi_bot
        t, v_imp, t_imp = 0.0, None, None
        hmax, Fc, Ff, Fn_min = 0.0, 0.0, 0.0, 1e9
        phi_max = 0.0
        while t < T:
            sp = s
            s = self.step(s, dt, F)
            t += dt
            _, _, _, out = self.forces(s, F)
            if v_imp is None and (out["catch"] < 0 or out["front"] > 0):
                v_imp = -self.vrel(self.finger, s[1], s[2], s[3])
                v_front = -self.vrel((-self.K.piv[0] * 1e-3, 0.0), s[1], s[2], s[3])
                t_imp = t
                who = "tail felt" if out["catch"] < 0 else "front felt"
            hmax = max(hmax, s[0])
            Fc = max(Fc, -out["catch"])
            Ff = max(Ff, out["front"])
            if t_imp is not None:
                Fn_min = min(Fn_min, out["notch"])
            phi_max = max(phi_max, s[1])
        over = (phi_max - phi_c) * self.K.piv[0]          # extra front travel past the nominal dip (mm, approx)
        return dict(v_imp=v_imp, v_front=v_front if v_imp else None, t_imp=t_imp, first=who if v_imp else None,
                    h_max=hmax, F_catch=Fc, F_front=Ff, overtravel=over, Fn_min=Fn_min)


# ------------------------------------------------------------------ configure one design point
STOP_BAR_TOP = 56.2          # 0.3 under the v3 cover underside z56.5
Z_FLOOR_MIN = 7.0            # lowest keel bottom (frame floor z5 + 2)


def bar_mass(K):
    b = [p.m for p in K.body.parts if "steel bar" in p.name]
    return b[0] if b else 0.0


def spring_seat_for(K, target):
    """well-bottom height z that gives the DW target at the finger; returns (z_well_bottom, preload N)."""
    P = K.P
    lo, hi = -40.0, 60.0
    for _ in range(70):
        mid = (lo + hi) / 2
        K.f["well_bottom"] = (P["well_y"], mid)
        dw = K.force_at(K.f["finger"], 0.0, +1)
        if dw > target:          # too much return torque -> lower the well bottom (less preload)
            hi = mid
        else:
            lo = mid
    K.f["well_bottom"] = (P["well_y"], (lo + hi) / 2)
    return (lo + hi) / 2, K.spring_force(0.0)


SPRING_L0 = (30.0, 35.0, 40.0, 45.0, 50.0)     # stock free lengths considered (same wire/OD)


def configure(P0, y_b, spring=True, black_spring_g=5.0):
    """S1 design point at pin position y_b: longest bar that fits, black keel/bar set, springs seated.
    spring=False: pure gravity, no well, bar runs to the tail end wall and is trimmed (from the front) to DW."""
    P = dict(P0)
    P["y_b"] = y_b
    if not spring:
        P["well"] = False
        P["bar_rear"] = P["y_end"] - P["wall"]
        P["stop_felt"] = (P["y_end"] - 16.0, P["y_end"] - 2.0)
        P["spring"] = dict(P["spring"], L0=-100.0)
    P["bar_len_w"] = float(math.floor(P["bar_rear"] - (y_b + P["boss_half"] + P["wall"]) - 0.5))
    P["bar_len_b"] = P["bar_len_w"]
    P["z_kb_b"] = P["z_kb_w"]
    notes = []
    for H in (32.0, 25.0):                       # stock flat bar 9x32, else 9x25
        P["bar_h"] = H
        W = Key(P, False)
        top_bot = max(W.zpt((y, W.f["z_tt"]), W.phi_bot) for y in (W.f["bar"][0], W.f["bar"][1]))
        if top_bot + V3["felt"] + 4.0 <= STOP_BAR_TOP:      # stop bar at least 4 thick
            break
    felt_plane = top_bot
    P["stop_bar_z"] = (felt_plane + V3["felt"], STOP_BAR_TOP)
    # the fixed stop-felt underside = the white bar top at full dip under the pad (a line in y, z)
    fw = [rot(p, W.piv, W.phi_bot) for p in W.catch_pts]
    felt_line = lambda y: fw[0][1] + (y - fw[0][0]) * (fw[1][1] - fw[0][1]) / (fw[1][0] - fw[0][0])
    P["felt_line"] = (fw[0][0], fw[0][1], fw[1][0], fw[1][1])

    def black_level():
        # black: bigger tail rise -> set its keel so its bar top touches the same felt line (under the pad)
        for _ in range(8):
            B = Key(P, True)
            pts = [rot(p, B.piv, B.phi_bot) for p in B.catch_pts]
            P["z_kb_b"] -= max(q[1] - felt_line(q[0]) for q in pts)
    black_level()
    if P["z_kb_b"] < Z_FLOOR_MIN:
        notes.append("black keel z%.1f below floor limit" % P["z_kb_b"])
    # black bar: shorten (from the front) so gravity alone gives target - black_spring_g (spring tops up)
    target = P["dw_target"]
    P_no = dict(P, spring=dict(P["spring"], L0=-100.0))
    Bg = Key(P_no, True)
    # black keys: no spring at all if the longest bar (running to the tail end, no well) reaches the target
    P_nb = dict(P_no, well_b=False)
    P_nb["bar_len_b"] = float(math.floor(P["y_end"] - P["wall"] - (y_b + P["boss_half"] + P["wall"]) - 0.5))
    black_spring = spring and Key(P_nb, True).force_at(Bg.f["finger"], 0.0, +1) < target
    if spring and not black_spring:
        P["well_b"] = False
        P_no = P_nb
        P["bar_len_b"] = P_nb["bar_len_b"]
        Bg = Key(P_no, True)
    bs = black_spring_g if black_spring else 0.0
    if Bg.force_at(Bg.f["finger"], 0.0, +1) > target - bs:
        lo, hi = 1.0, P["bar_len_b"]
        for _ in range(40):
            mid = (lo + hi) / 2
            P_no["bar_len_b"] = mid
            Bg = Key(P_no, True)
            if Bg.force_at(Bg.f["finger"], 0.0, +1) > target - bs:
                hi = mid
            else:
                lo = mid
        P["bar_len_b"] = float(math.floor(lo))
    if not spring:
        # trim both bars from the front so gravity alone gives the DW target
        Wt = trim_to(Key(P, False), target, False)
        P["bar_len_w"] = float(math.ceil(Wt.P["bar_len_w"]))
        Bt = trim_to(Key(P, True), target, True)
        P["bar_len_b"] = float(math.ceil(Bt.P["bar_len_b"]))
        W0 = Key(P, False)
        if W0.force_at(W0.f["finger"], 0.0, +1) < target - 3.0:
            notes.append("gravity alone gives only DW %.1f g" % W0.force_at(W0.f["finger"], 0.0, +1))
    else:
        # choose the stock free length that puts the white well bottom ~6 mm above the pocket floor
        best = None
        for L0 in SPRING_L0:
            P["spring"] = dict(P["spring"], L0=L0)
            Wt = Key(P, False)
            zw, pre = spring_seat_for(Wt, target)
            err = abs(zw - (Wt.f["bar"][2] + 6.0))
            if best is None or err < best[0]:
                best = (err, L0)
        P["spring"] = dict(P["spring"], L0=best[1])
    if spring and not black_spring:
        black_level()           # re-level the black keel for the (possibly longer) springless bar
    W, B = Key(P, False), Key(P, True)
    seats = {}
    if spring:
        seats["white"] = spring_seat_for(W, target)
        seats["black"] = spring_seat_for(B, target) if black_spring else (None, 0.0)
        for nm, K in (("white", W), ("black", B)):
            if not K.f["well"]:
                continue
            zfl = K.f["bar"][2]                  # floor top (bar bottom)
            if seats[nm][0] < zfl - 1e-6:
                notes.append("%s spring well bottom z%.1f below the pocket floor z%.1f" % (nm, seats[nm][0], zfl))
            if K.spring_len(K.phi_bot) - K.sp["solid"] < 1.0:
                notes.append("%s spring near solid" % nm)
            if seats[nm][1] <= 0:
                notes.append("%s spring has no preload" % nm)
    return P, W, B, seats, notes


def evaluate(P, W, B, dyn=True, press=(3.0, 8.0)):
    out = {}
    for nm, K in (("white", W), ("black", B)):
        st = K.statics()
        se = K.sensor()
        d = dict(st=st, se=se, bar=bar_mass(K), cop=K.cop(), m=K.m)
        if dyn:
            d["ret"] = Sim(K).run_return()
            d["press"] = {F: Sim(K).run_press(F) for F in press}
        out[nm] = d
    return out


# ------------------------------------------------------------------ section properties for plastic stress
def u_section(width, height, skin, wall, floor=0.0):
    """U channel (top skin + 2 walls [+ floor]); returns (A, I, c_max) about the centroid (z)."""
    rects = [(width, skin, height - skin / 2), (2 * wall, height - skin - floor, (height - skin + floor) / 2)]
    if floor:
        rects.append((width - 2 * wall, floor, floor / 2))
    A = sum(b * h for b, h, _ in rects)
    zc = sum(b * h * z for b, h, z in rects) / A
    I = sum(b * h ** 3 / 12 + b * h * (z - zc) ** 2 for b, h, z in rects)
    return A, I, max(zc, height - zc)


def coord_table(K, nm):
    """rest / bottom coordinates of the key features (for design.md)."""
    ph = K.phi_bot
    f = K.f
    rows = [("pivot pin axis", K.piv), ("finger point", f["finger"]), ("front top edge", f["front_top"]),
            ("hook contact (crossbar top)", f["hook"]), ("front felt contact (plate centre)", f["front"]),
            ("magnet face centre", f["mag"]), ("key COM (incl. bar)", K.G),
            ("steel bar centroid", ((f["bar"][0] + f["bar"][1]) / 2, (f["bar"][2] + f["bar"][3]) / 2)),
            ("bar top front corner", (f["bar"][0], f["bar"][3])), ("bar top rear corner", (f["bar"][1], f["bar"][3])),
            ("tail stop felt contact pts", K.catch_pts[0]), ("", K.catch_pts[1]),
            ("spring well bottom (spring lower seat)" if f["well"] else "(no spring well)", f["well_bottom"] if f["well"] else (K.P["y_end"], f["z_tt"])),
            ("keel bottom front / rear", (f["keel"][0], f["keel"][2])), ("", (f["keel"][1], f["keel"][2])),
            ("tail end top", (K.P["y_end"], f["z_tt"]))]
    print("  %s key: feature                               rest (y, z)          bottom (y, z)" % nm)
    for label, p in rows:
        q = rot(p, K.piv, ph)
        print("    %-40s (%7.2f, %6.2f)   (%7.2f, %6.2f)" % (label, p[0], p[1], q[0], q[1]))


# ================================================================== main
def main():
    global P
    Y_B = P["y_b"]
    P, W, B, seats, notes = configure(P, Y_B)
    sp = spring_props(P)
    print("=" * 96)
    print("Toccata v4 - S1 mini seesaw - calc.py results  (final design point y_b = %.0f)" % Y_B)
    print("=" * 96)
    print("\n[1] parameters (after configure)")
    for k in ("y_b", "z_p", "pin_d", "z_kb_w", "z_kb_b", "bar_t", "bar_h", "bar_len_w", "bar_len_b",
              "bar_rear", "well_y", "stop_bar_z", "stop_felt", "front_felt_gap", "E_felt", "mu_pin", "mu_bush"):
        v = P[k]
        print("  %-16s %s" % (k, tuple(round(x, 2) for x in v) if isinstance(v, tuple) else round(v, 3)))
    print("  spring: d %.2f  OD %.1f  L0 %.1f  n_act %d  ->  k %.4f N/mm  index C %.1f  solid %.1f mm  mass %.2f g"
          % (sp["d"], sp["D_out"], sp["L0"], sp["n"], sp["k"], sp["C"], sp["solid"], sp["mass"]))
    print("  notes: %s" % (notes or "none"))

    E = evaluate(P, W, B)
    for nm, K in (("white", W), ("black", B)):
        st, se = E[nm]["st"], E[nm]["se"]
        print("\n[2-%s] %s key (%s)" % (nm[0], nm, "D" if nm == "white" else "C#"))
        print("  mass total %.1f g = PETG %.1f + steel %.1f (bar %.1f, pin, 1/3 spring) + magnet %.2f"
              % (K.m, K.body.mass_of("PETG"), K.body.mass_of("steel"), bar_mass(K), K.body.mass_of("magnet")))
        print("  COM (y %.1f, z %.1f): d_G = %+.1f mm behind the pin;  I_pivot %.0f g*mm^2 (I_G %.0f + m d^2 %.0f)"
              % (K.G[0], K.G[1], K.G[0] - K.piv[0], K.Ip, K.IG, K.Ip - K.IG))
        top = sorted(K.body.parts, key=lambda p: -(p.Iown + p.m * ((p.y - K.piv[0]) ** 2 + (p.z - K.piv[1]) ** 2)))[:5]
        print("  largest inertia terms: " + "; ".join("%s %.0f" % (p.name, p.Iown + p.m * ((p.y - K.piv[0]) ** 2 +
                                                                               (p.z - K.piv[1]) ** 2)) for p in top))
        print("  full-dip angle %.3f deg (%.5f rad)" % (math.degrees(K.phi_bot), K.phi_bot))
        zw, pre = seats[nm]
        if K.f["well"]:
            print("  spring well bottom z%.2f (seat z%.2f): installed %.2f mm at rest, %.2f at bottom; force %.3f -> %.3f N;"
                  " solid margin %.1f mm; max shear %.0f MPa"
                  % (zw, K.z_seat, K.spring_len(0), K.spring_len(K.phi_bot), K.spring_force(0), K.spring_force(K.phi_bot),
                     K.spring_len(K.phi_bot) - sp["solid"],
                     8 * K.spring_force(K.phi_bot) * sp["D"] / (math.pi * sp["d"] ** 3) * sp["wahl"]))
        else:
            print("  no spring: pure gravity (bar runs to the tail end wall)")
        fp = K.f["finger"]
        print("  finger y%.1f: DW %.1f g (at rest), UW %.1f g (near rest) / %.1f g (leaving the bottom); balance %.1f g,"
              " friction %.2f g; DW at the bottom %.1f g"
              % (fp[0], st["DW"], st["UW_rest"], st["UW"], st["BW"], st["fric"], st["DW_bot"]))
        print("     friction split at DW (g at finger): " + ", ".join("%s %.2f" % kv for kv in st["fric_parts_g"].items()))
        print("  front edge y%.1f: DW %.1f g, UW %.1f g" % (K.f["finger0"][0], st["DW0"], st["UW0"]))
        print("  y90: DW %.1f g -> front/back ratio F(y90)/F(y%.1f) = %.2f" % (st["DW90"], fp[0], st["ratio_90"]))
        print("  return torque at rest (as g at finger): gravity %.1f + spring %.1f  -> gravity share %.0f %%;"
              " steel bar alone %.1f g" % (st["grav_g"], st["spring_g"], 100 * st["grav_share"], st["bar_torque_g"]))
        print("  m_eff at finger %.1f g, at front edge %.1f g" % (st["m_eff"], st["m_eff0"]))
        print("  sensor y67: rest gap %.2f, bottom gap %.2f, magnet travel %.2f mm; magnet at bottom y%.2f (element y67)"
              % (se["gap_rest"], se["gap_bot"], se["travel"], se["y_bot"]))
        print("  centre of percussion %.0f mm behind pin; tail-felt contact points %.1f / %.1f mm -> %s"
              % (K.cop(), K.catch_pts[0][0] - K.piv[0], K.catch_pts[1][0] - K.piv[0],
                 "in front of CoP (impact pushes pin INTO notch)" if K.catch_pts[1][0] - K.piv[0] <= K.cop()
                 else "behind CoP"))
        pts = ["%d%%:%.1f" % (i * 20, K.force_at(fp, K.phi_bot * i / 5, +1)) for i in range(6)]
        print("  DW along the stroke (g): " + "  ".join(pts))

    print("\n[3] impact impulse on the pin (analytic, per unit angular velocity, g*mm; + = pin pushed into its notch)")
    for nm, K in (("white", W), ("black", B)):
        dG = K.G[0] - K.piv[0]
        Jp = lambda s_: K.Ip / s_ - K.m * dG
        s_tail = sum(p[0] for p in K.catch_pts) / 2 - K.piv[0]
        s_front = K.f["front"][0] - K.piv[0]
        s_hook = K.f["hook"][0] - K.piv[0]
        s_back = P["y_end"] - 4 - K.piv[0]
        print("  %s: key hits tail felt (s=%+.1f) %+.0f | front felt (s=%+.1f) %+.0f  || returns onto hook (s=%+.1f)"
              " %+.0f | onto a back rail under the tail end (s=%+.1f) %+.0f"
              % (nm, s_tail, Jp(s_tail), s_front, Jp(s_front), s_hook, -Jp(s_hook), s_back, -Jp(s_back)))

    print("\n[4] return simulation: released at the bottom (after a 1 N hold), 2 DOF with pin lift;"
          " felt E %.1f MPa, zeta %.2f" % (P["E_felt"], P["zeta"]))
    for nm, K in (("white", W), ("black", B)):
        r = E[nm]["ret"]
        d40 = 0.4 * r["travel"] * 1e3 * (-K.lever(K.f["finger"])) / (-K.lever(K.f["mag"]))
        t_push = d40 / 1e3 / 0.3
        E[nm]["rt_hz"] = 1 / (2 * r["t_rt"])
        E[nm]["rt_hz_finger"] = 1 / (r["t_rt"] + t_push)
        print("  %s: sensor travel %.2f mm | re-trigger point (risen 40 %% of travel) %.1f ms | full return (hook) %.1f ms"
              " | pin lift %.4f mm | bounce after hook %.2f mm | settled +-0.2 mm at %.1f ms"
              % (nm, r["travel"] * 1e3, r["t_rt"] * 1e3, r["t_full"] * 1e3, r["h_max"] * 1e3, r["bounce"] * 1e3,
                 r["t_settle"] * 1e3))
        print("        re-trigger rate: 1/(2 t_rt) = %.1f Hz (finger as slow as gravity); finger pushes back at 0.3 m/s:"
              " %.1f Hz; full-return based 1/(2 t_full) = %.1f Hz"
              % (E[nm]["rt_hz"], E[nm]["rt_hz_finger"], 1 / (2 * r["t_full"])))
    for ef in (0.5, 2.0):
        r = Sim(W, E_felt=ef).run_return()
        print("  white with felt E %.1f MPa: t_rt %.1f ms, t_full %.1f ms, bounce %.2f mm, pin lift %.4f mm"
              % (ef, r["t_rt"] * 1e3, r["t_full"] * 1e3, r["bounce"] * 1e3, r["h_max"] * 1e3))
    # no spring at all (what gravity alone would do with this geometry)
    Pn = dict(P, spring=dict(P["spring"], L0=-100.0))
    Wn = Key(Pn, False)
    stn = Wn.statics()
    rn = Sim(Wn).run_return()
    print("  (same white key with a broken/missing spring: DW %.1f g, UW %.1f g -> still returns by gravity,"
          " t_full %.1f ms)" % (stn["DW"], stn["UW_rest"], (rn["t_full"] or float("nan")) * 1e3))

    print("\n[5] press simulation from rest with a constant finger force (2 DOF with pin lift)")
    for nm in ("white", "black"):
        for F, r in E[nm]["press"].items():
            if r["v_imp"] is None:
                print("  %s F=%.0f N: does not reach the bottom" % (nm, F))
                continue
            print("  %s F=%.0f N: hits %s first at %.2f m/s (finger) after %.1f ms; pin lift %.3f mm;"
                  " peak tail felt %.1f N, front felt %.1f N; overtravel %.2f mm"
                  % (nm, F, r["first"], r["v_imp"], r["t_imp"] * 1e3, r["h_max"] * 1e3, r["F_catch"], r["F_front"],
                     r["overtravel"]))
    print("  impact experiment: key arrives at the first down-stop with finger speed v, finger keeps pushing 2 N")
    IMP = {}
    for nm, K in (("white", W), ("black", B)):
        for v in (0.5, 1.0, 1.5):
            r = Sim(K).run_impact(v)
            IMP[(nm, v)] = r
            print("  %s v=%.1f m/s: pin lift %.3f mm (off the notch %.1f ms), overtravel %.2f mm, tail felt %.1f N,"
                  " front felt %.1f N" % (nm, v, r["h_max"] * 1e3, r["lift_ms"], r["overtravel"], r["F_catch"],
                                          r["F_front"]))
    for fg in (0.3, 1.0, 5.0):
        r = Sim(W, front_gap=fg).run_impact(1.0)
        print("  white v=1.0, front felt gap %.1f mm: pin lift %.3f mm, overtravel %.2f mm" % (fg, r["h_max"] * 1e3,
                                                                                         r["overtravel"]))
    r = Sim(W, E_felt=2.5).run_impact(1.0)
    print("  white v=1.0, harder felt E 2.5 MPa: pin lift %.3f mm, overtravel %.2f mm" % (r["h_max"] * 1e3, r["overtravel"]))
    for fg in (0.0, 1.0):
        r = Sim(W, front_gap=fg).run_press(8.0)
        print("  white F=8 N, front felt gap %.1f mm: pin lift %.3f mm, overtravel %.2f mm, tail felt %.1f N"
              % (fg, r["h_max"] * 1e3, r["overtravel"], r["F_catch"]))

    print("\n[6] coordinates (rest / full dip), mm")
    coord_table(W, "white")
    coord_table(B, "black")

    print("\n[6b] frame features derived from the key geometry (mm)")
    for nm, K in (("white", W), ("black", B)):
        ph = K.phi_bot
        pc = rot(K.f["front"], K.piv, ph)
        top = pc[1] - P["front_felt_gap"]
        half = 3.9 if nm == "white" else 3.15
        a, b = pc[0] - half, pc[0] + half
        za = top + (a - pc[0]) * math.tan(ph)
        zb_ = top + (b - pc[0]) * math.tan(ph)
        print("  %s front felt (secondary down-stop): felt top z%.2f at y%.2f .. z%.2f at y%.2f (slope %.2f deg = key angle),"
              " rail top = felt top - 3.0" % (nm, za, a, zb_, b, math.degrees(ph)))
    fw = [rot(p, W.piv, W.phi_bot) for p in W.catch_pts]
    slope = math.degrees(math.atan2(fw[1][1] - fw[0][1], fw[1][0] - fw[0][0]))
    print("  tail stop felt underside: z%.2f at y%.2f .. z%.2f at y%.2f (inclined %.2f deg, = white bar top at full dip);"
          " black bars meet it at their own full dip (keel z%.2f)" % (fw[0][1], fw[0][0], fw[1][1], fw[1][0], slope,
                                                                    P["z_kb_b"]))
    print("  balance rail y%.0f..%.0f top z21.5; fins 2.0 thick, notch for the pin axis z%.1f: PETG R2.0 bottom z%.1f +"
          " 0.5 cloth -> seat R1.5; flat lead-in top z%.1f for %.1f mm in front of the notch"
          % (P["y_b"] - 5, P["y_b"] + 5, P["z_p"], P["z_p"] - 2.0, P["z_p"], 3.9))
    print("  spring (white only): pocket in the stop bar at y%.1f, seat z%.2f; key well bottom z%.2f (well Ø%.1f)"
          % (P["well_y"], W.z_seat, W.f["well_bottom"][1], P["well_id"]))
    print("  control board y%.0f..%.0f x%.2f..%.2f (cut 5x7 stripboard to %.0f x 70), components <= z%.1f;"
          " USB cable lane under the F tail x71..80 z5..10.5 (white keel z%.1f)"
          % (P["board_y"][0], P["board_y"][1], P["board_x"][0], P["board_x"][1], P["board_y"][1] - P["board_y"][0],
             P["board_top_components"], P["z_kb_w"]))

    print("\n[7] clearances and envelope")
    env = {}
    for nm, K in (("white", W), ("black", B)):
        ph = K.phi_bot
        f = K.f
        top_rest = f["z_tt"]
        top_bot = max(K.zpt((y, top_rest), ph) for y in (f["bar"][0], f["bar"][1], P["y_end"]))
        under = min(K.zpt((y, V3["key_bot"]), ph) for y in (P["board_y"][0], P["board_y"][1]))
        corners = [(P["y_end"], f["keel"][2]), (P["y_end"], top_rest)]
        rear = max(max(rot(c, K.piv, a)[0] for c in corners) for a in (0.0, ph))
        env[nm] = dict(top_rest=top_rest, top_bot=top_bot, keel=f["keel"][2], board=under - P["board_top_components"],
                       rear_clear=V3["rear_wall_y"][0] - rear)
        print("  %s: rearmost point of the tail (low keel corner) y%.2f at full dip -> clearance to the rear wall y209 %.2f mm"
              % (nm, rear, V3["rear_wall_y"][0] - rear))
        print("  %s: tail top z%.2f rest -> z%.2f bottom (rise %.2f); keel bottom z%.2f; key underside over the"
              " control board at full dip z%.2f (components <= z%.1f -> %.2f mm)"
              % (nm, top_rest, top_bot, top_bot - top_rest, f["keel"][2], under, P["board_top_components"],
                 under - P["board_top_components"]))
    COVER_PLATE_BOT = 46.5
    wt = max(W.zpt((y, W.f["z_tt"]), W.phi_bot) for y in (146.0, 148.5))
    bt = B.zpt((144.0, V3["black_top"]), B.phi_bot)
    env["cover_plate"] = COVER_PLATE_BOT - wt
    env["black_raised"] = V3["cover_under"] - bt
    print("  rear-cover front plate (y146..148.5) bottom raised z44.5 -> z%.1f: white tail top there at full dip z%.2f"
          " (clear %.2f); black raised top end y144 at full dip z%.2f vs cover underside z%.1f (clear %.2f)"
          % (COVER_PLATE_BOT, wt, COVER_PLATE_BOT - wt, bt, V3["cover_under"], V3["cover_under"] - bt))
    print("  stop felt z%.2f..%.2f (glued under the tail stop bar z%.2f..%.1f, %.1f thick); cover underside z%.1f"
          % (P["stop_bar_z"][0] - 3, P["stop_bar_z"][0], P["stop_bar_z"][0], P["stop_bar_z"][1],
             P["stop_bar_z"][1] - P["stop_bar_z"][0], V3["cover_under"]))
    print("  highest moving part z%.1f (black key top at rest, moves down); lowest moving part z%.2f (black keel at rest,"
          " moves up); depth used y0..%.1f; frame 212, total depth %.0f mm (unchanged)"
          % (V3["black_top"], min(env["white"]["keel"], env["black"]["keel"]), P["y_end"], V3["v3_total_depth"]))

    print("\n[8] constant stress in plastic parts at rest (MPa)")
    K = W
    F_hook = K.T_return(0.0) / (-K.lever(K.f["hook"]))
    yb0 = P["y_b"] - P["boss_half"]
    front_parts = [p for p in K.body.parts if p.y < yb0]
    M_front = F_hook * (yb0 - K.f["hook"][0]) + sum(p.m * GF * (yb0 - p.y) for p in front_parts)
    A, I, c = u_section(P["w_tail"], 20.0, P["skin"], P["wall"])
    s_front = M_front * c / I
    yb1 = P["y_b"] + P["boss_half"]
    tail_p = [p for p in K.body.parts if p.y > yb1]
    M_tail = sum(p.m * GF * (p.y - yb1) for p in tail_p) + K.spring_force(0) * (P["well_y"] - yb1)
    A2, I2, c2 = u_section(P["w_tail"], W.f["z_tt"] - P["z_kb_w"], P["wall"], P["wall"], P["wall"])
    s_tail = M_tail * c2 / I2
    Rp = K.m * GF + K.spring_force(0) + F_hook
    s_notch = Rp / (P["pin_d"] * 2.0)
    s_boss = Rp / ((P["w_tail"] - 2.3) * P["pin_d"])
    bw = bar_mass(K) * GF
    s_floor = 6 * (bw * (P["w_tail"] - 2 * P["wall"]) / (8 * P["bar_len_w"])) / P["wall"] ** 2
    s_well = 1.24 * 3 * K.spring_force(0) / (2 * math.pi * P["wall"] ** 2)
    s_hook = F_hook * 4.0 / (8.3 * 1.4 ** 2 / 6)
    Fs_all = 7 * W.spring_force(0) + 5 * B.spring_force(0)
    t_sb = P["stop_bar_z"][1] - P["stop_bar_z"][0]
    s_stopbar = 6 * (Fs_all / 164.5) * (209.0 - P["well_y"]) / t_sb ** 2      # cantilever from the rear-wall groove
    rows = [("key front arm at the pivot boss (hook load + own weight)", s_front),
            ("key tail box behind the boss (bar + spring)", s_tail),
            ("pin on the fin notch, projected bearing (R = %.2f N)" % Rp, s_notch),
            ("pin in the key boss, bearing", s_boss),
            ("pocket floor under the steel bar (plate)", s_floor),
            ("spring well floor (plate)", s_well),
            ("frame hook cantilever (F = %.3f N, v3 hook)" % F_hook, s_hook),
            ("tail stop bar, cantilever from rear-wall groove (springs %.1f N)" % Fs_all, s_stopbar)]
    for nm_, v in rows:
        print("  %-60s %.3f" % (nm_, v))
    s_max = max(v for _, v in rows)
    print("  max constant stress %.3f MPa (target < 2)" % s_max)
    print("  transient only: 8 N finger held at the bottom, front arm at the boss if the tail felt carried it: %.1f MPa"
          % (8.0 * (yb0 - 13) * c / I))
    Fpk = IMP[("white", 1.5)]["F_catch"]
    Mst = 5 * Fpk * (209.0 - sum(P["stop_felt"]) / 2)
    bw_ = 5 * 164.5 / 12
    s_sb = 6 * Mst / (bw_ * t_sb ** 2)
    EIpm = E_PETG * t_sb ** 3 / 12
    d_sb = (5 * Fpk / bw_) * (209.0 - sum(P["stop_felt"]) / 2) ** 3 / (3 * EIpm)
    print("  transient only: 5-key ff chord (1.5 m/s, %.1f N per key) on the tail stop bar (cantilever from the rear-wall"
          " groove): %.1f MPa, deflection %.2f mm" % (Fpk, s_sb, d_sb))

    print("\n[9] parts, steel, filament, print")
    wpet, bpet = W.body.mass_of("PETG"), B.body.mass_of("PETG")
    pin_m = math.pi * 1.5 ** 2 * P["pin_len"] * RHO_STEEL
    steel_oct = 7 * bar_mass(W) + 5 * bar_mass(B) + 12 * (pin_m + sp["mass"])
    steel_88 = 52 * bar_mass(W) + 36 * bar_mass(B) + 88 * (pin_m + sp["mass"])
    v3_frame = 175.0
    spine = 164.0 * 13.0 * (20.7 - 5.0) * 0.6 * RHO_PETG
    bal = (164.0 * 10.0 * (21.5 - 5.0) - 20 * 10 * 12) * 0.6 * RHO_PETG + 12 * 2.0 * 7.0 * 5.0 * RHO_PETG
    frame = v3_frame - spine + bal
    t_sb = P["stop_bar_z"][1] - P["stop_bar_z"][0]
    stopbar = 164.0 * 24.0 * t_sb * 0.5 * RHO_PETG
    cover, sensor_bar = 44.0, 16.0
    oct_g = 7 * wpet + 5 * bpet + frame + stopbar + cover + sensor_bar
    tot_g = 52 * wpet + 36 * bpet + (frame + stopbar + cover + sensor_bar) * (7 + 0.55)
    print("  PETG: white key %.1f g, black key %.1f g, frame %.0f g (v3 175 - spine rail %.0f + balance rail/fins %.0f),"
          " tail stop bar %.0f g, cover %.0f g, sensor bar %.0f g" % (wpet, bpet, frame, spine, bal, stopbar, cover,
                                                                     sensor_bar))
    print("  per octave module %.0f g -> %.1f h; 88 keys %.2f kg (+10 %% waste %.2f kg) -> %.0f h at %.0f g/h"
          % (oct_g, oct_g / FIL_G_PER_H, tot_g / 1000, tot_g * WASTE / 1000, tot_g * WASTE / FIL_G_PER_H, FIL_G_PER_H))
    print("  steel per octave %.0f g (bars %.0f g = 7 x %.0f + 5 x %.0f); 88 keys %.2f kg"
          % (steel_oct, 7 * bar_mass(W) + 5 * bar_mass(B), bar_mass(W), bar_mass(B), steel_88 / 1000))
    mod_mass = 590 - (175 + 92) + (7 * wpet + 5 * bpet) - spine + bal + stopbar + steel_oct
    print("  octave module mass ~%.2f kg (v3 0.59 kg)" % (mod_mass / 1000))
    bar_m = (52 * P["bar_len_w"] + 36 * P["bar_len_b"] + 88 * 1.5) / 1000
    print("  flat bar 9x%.0f to cut: %.2f m incl. 1.5 mm kerf -> %d x 1 m pieces" % (P["bar_h"], bar_m, math.ceil(bar_m)))
    print("  largest print: frame 164.5 x 212 (fits 220x220), key %.1f long lying on its top face (fits straight: %s);"
          " keys per 220 plate with 2 mm gaps: white %d, black %d"
          % (P["y_end"], "yes" if P["y_end"] <= 220 else "no", int(220 // (P["w_head"] + 2)), int(220 // (P["w_tail"] + 2))))
    # regulation sensitivities
    lev_w = -W.lever(W.f["finger"])
    lev_b = -B.lever(B.f["finger"])
    d_spacer = sp["k"] * W.lever(W.f["well_bottom"]) / lev_w / GF          # 1 mm more spring preload
    put_tail = 1.0 * (sum(P["stop_felt"]) / 2 - P["y_b"]) / lev_b
    put_front = 1.0 * (P["y_b"] - 57.0) / lev_b
    print("  regulation: white well spacer +1 mm -> DW %+.2f g; black: +1 g tungsten putty on the tail (y192) -> DW %+.2f g,"
          " +1 g under the front (y57) -> DW %-.2f g" % (d_spacer, put_tail, -put_front))

    print("\n[10] purchased items vs v3 (KRW)")
    n_bar = math.ceil(bar_m)
    items = [("flat bar SS400 9x%.0f, 1 m pieces (cut at home)" % P["bar_h"], n_bar, 7000, "estimate"),
             ("dowel pin 3x10 SUS, 100 pcs", 1, 10000, "estimate (NFAS lists ~100 won/ea)"),
             ("compression spring d0.4 OD6 L50 (white keys only, 52 + spares), 100 pcs", 1, 60000,
              "NaviMRO Hyundai-Spring 100EA packs 47,990-69,990 won; this size = estimate"),
             ("hacksaw blade bi-metal x2 (88 cuts)", 2, 3000, "estimate"),
             ("(option) steel balls d10 1 kg for white key leads, 208 pcs", 0, 6500,
              "danawa/bearingstore listings 5,900-6,900 won/kg"),
             ("M3 knurled thumb screw + nut, tail stop bar, 2 per module (18 sets)", 18, 300, "estimate"),
             ("bushing cloth 0.5T for notches (felt already in BOM)", 0, 0, "BOM")]
    removed = [("v3 clamp M3x35/40 x4 + setscrew M3x10 x4 + brass disc x4 per module (9 modules)",
                -(36 * 120 + 36 * 100 + 36 * 250), "v3 BOM lines, approx")]
    add = sum(n * u for _, n, u, _ in items)
    rem = sum(v for _, v, _ in removed)
    for nm_, n, u, src in items:
        print("  + %-66s %3d x %6d = %7d  [%s]" % (nm_, n, u, n * u, src))
    for nm_, v, src in removed:
        print("  - %-66s              %7d  [%s]" % (nm_, v, src))
    print("  cost delta vs v3 base BOM: %+d KRW" % (add + rem))

    print("\n[10b] options on the final geometry (white key)")
    opts = {}
    for label, upd in (("key lead: 4 steel balls d10 (16.4 g) in the head at y38", dict(front_lead=16.44)),
                       ("key lead: 8 steel balls d10 (32.9 g, 2 layers) at y38", dict(front_lead=32.88)),
                       ("steel balls d10 instead of the flat bar (no cutting; 3 layers, fill 0.545)", dict(bar_fill=0.545)),
                       ("no white bar at all (spring only)", dict(bar_fill=0.0))):
        Po = dict(P, **upd)
        Wo = Key(Po, False)
        zw_o, pre_o = spring_seat_for(Wo, P["dw_target"])
        so = Wo.statics()
        ro = Sim(Wo).run_return()
        opts[label] = dict(m_eff=so["m_eff"], pre=pre_o, DWb=so["DW_bot"], t_rt=ro["t_rt"], t_full=ro["t_full"],
                           zw=zw_o, grav=so["grav_share"], m=Wo.m)
        ok = zw_o >= Wo.f["bar"][2] and Wo.spring_len(Wo.phi_bot) - sp["solid"] > 1.0
        print("  %-72s m_eff %.1f g, gravity share %.0f %%, spring preload %.2f N (well bottom z%.1f %s), DW rest->bottom"
              " 50.0->%.1f g, t_rt %.1f ms, t_full %.1f ms, key mass %.0f g"
              % (label, so["m_eff"], 100 * so["grav_share"], pre_o, zw_o, "ok" if ok else "NOT FEASIBLE with this spring",
                 so["DW_bot"], ro["t_rt"] * 1e3, ro["t_full"] * 1e3, Wo.m))

    print("\n[11] y_b sweep of the S1 family (longest bar that fits + helper spring to DW %.0f g at y13)"
          % P["dw_target"])
    print("   y_b  bar_w  grav%  spr_N  DW   UWbot  ratio  trav_w  m_eff  t_rt  t_full  Hz(sym)  lift8N  "
          "bar_b  keel_b  trav_b  DW_b UWbot_b notes")
    sweep = {}
    for yb in (130.0, 135.0, 140.0, 145.0, 150.0, 155.0, 160.0):
        P_, W_, B_, seats_, notes_ = configure(P0_GLOBAL, yb)
        E_ = evaluate(P_, W_, B_, dyn=True, press=(8.0,))
        sw, sb = E_["white"]["st"], E_["black"]["st"]
        rw = E_["white"]["ret"]
        sweep[yb] = dict(P=P_, E=E_)
        print("  %4.0f %5.0fg %5.0f %6.2f %5.1f %5.1f %6.2f %6.2f %6.1f %5.1f %6.1f %7.1f %7.3f %5.0fg %6.1f %6.2f %5.1f %5.1f  %s"
              % (yb, bar_mass(W_), 100 * sw["grav_share"], seats_["white"][1], sw["DW"], sw["UW"], sw["ratio_90"],
                 E_["white"]["se"]["travel"], sw["m_eff"], rw["t_rt"] * 1e3, rw["t_full"] * 1e3, 1 / (2 * rw["t_rt"]),
                 E_["white"]["press"][8.0]["h_max"] * 1e3, bar_mass(B_), P_["z_kb_b"], E_["black"]["se"]["travel"],
                 sb["DW"], sb["UW"], "; ".join(notes_) or "-"))

    print("\n[12] pure gravity (no spring)")
    alt = pure_gravity_scan()
    return dict(P=P, W=W, B=B, E=E, IMP=IMP, env=env, s_max=s_max, opts=opts, steel_oct=steel_oct, steel_88=steel_88, tot_g=tot_g,
                oct_g=oct_g, cost=add + rem, alt=alt, sweep=sweep, seats=seats, mod_mass=mod_mass)


def max_bar_key(Pb, black, y_end, y_b):
    """pure gravity: pin at y_b, tail to y_end, bar fills y_b+7.2 .. y_end-1.2 (no spring, no well), tallest
    bar (0.5 steps) whose top at full dip + 3 felt + 4 stop bar stays under z56.2.  Keel bottom z11 (white)
    or lower for black only down to Z_FLOOR_MIN."""
    P2 = dict(Pb)
    P2.update(y_b=y_b, y_end=y_end, bar_rear=y_end - 1.2, well_y=y_end - 0.6)
    P2["spring"] = dict(P2["spring"], L0=-100.0)
    P2["bar_len_w"] = P2["bar_len_b"] = P2["bar_rear"] - (y_b + P2["boss_half"] + 1.2)
    P2["z_kb_b"] = Z_FLOOR_MIN if black else P2["z_kb_w"]
    for H in (38.0, 32.0, 25.0, 19.0):           # stock 9 mm flat bar widths
        P2["bar_h"] = H
        K = Key(P2, black)
        top_bot = max(K.zpt((y, K.f["z_tt"]), K.phi_bot) for y in (K.f["bar"][0], K.f["bar"][1]))
        if top_bot + 3.0 + 4.0 <= STOP_BAR_TOP:
            return K, H
    return None, None


def trim_to(K, target, black):
    """shorten the bar from the front until DW(finger) = target (bar only gets shorter)."""
    P3 = dict(K.P)
    key = "bar_len_b" if black else "bar_len_w"
    if K.force_at(K.f["finger"], 0.0, +1) < target:
        return K
    lo, hi = 0.5, P3[key]
    for _ in range(40):
        mid = (lo + hi) / 2
        P3[key] = mid
        if Key(P3, black).force_at(K.f["finger"], 0.0, +1) > target:
            hi = mid
        else:
            lo = mid
    P3[key] = hi
    return Key(P3, black)


def pure_gravity_scan():
    Pb = dict(P0_GLOBAL)
    out = {"in_frame": [], "extended": []}
    print("  (a) inside the 212 frame (tail end y206.5); bar 9 thick fills the whole tail; DW target 50 g")
    print("      y_b  white bar max(LxH, g)  DW_max  -> bar for DW50 (g)  UW   ratio  travel  m_eff | black: bar(g) "
          "DW  travel  tail rise  keel")
    for yb in (110.0, 115.0, 118.0, 120.0, 122.0, 125.0, 130.0, 135.0, 140.0, 150.0, 160.0):
        K, H = max_bar_key(Pb, False, P0_GLOBAL["y_end"], yb)
        st_max = K.statics()
        Kt = trim_to(K, 50.0, False)
        st = Kt.statics()
        Kb, Hb = max_bar_key(Pb, True, P0_GLOBAL["y_end"], yb)
        Kbt = trim_to(Kb, 50.0, True)
        stb = Kbt.statics()
        rb = max(Kbt.zpt((y, Kbt.f["z_tt"]), Kbt.phi_bot) for y in (Kbt.f["bar"][0], Kbt.f["bar"][1])) - Kbt.f["z_tt"]
        row = dict(y_b=yb, DW_max=st_max["DW"], DW=st["DW"], UW=st["UW"], ratio=st["ratio_90"],
                   travel=Kt.sensor()["travel"], m_eff=st["m_eff"], bar=bar_mass(Kt), bar_b=bar_mass(Kbt),
                   DW_b=stb["DW"], travel_b=Kbt.sensor()["travel"], rise_b=rb)
        out["in_frame"].append(row)
        print("      %4.0f   %4.0fx%4.1f %5.0f g  %6.1f   %6.0f g          %5.1f %6.2f %6.2f %6.1f | %5.0f g %5.1f %6.2f"
              " %7.1f  z%.1f"
              % (yb, K.P["bar_len_w"], H, bar_mass(K), st_max["DW"], bar_mass(Kt), st["UW"], st["ratio_90"],
                 row["travel"], st["m_eff"], bar_mass(Kbt), stb["DW"], row["travel_b"], rb, Z_FLOOR_MIN))
    ok = [r for r in out["in_frame"] if r["DW_max"] >= 50.0]
    best = max(ok, key=lambda r: r["y_b"]) if ok else None
    out["best_in_frame"] = best
    if best:
        print("      -> furthest-back pin that still reaches DW 50 g on gravity alone: y_b %.0f (ratio %.2f, travel %.2f mm,"
              " m_eff %.1f g, white bar %.0f g, black bar %.0f g)" % (best["y_b"], best["ratio"], best["travel"],
                                                                     best["m_eff"], best["bar"], best["bar_b"]))
    print("  (b) pin kept at y_b 150 / 160, tail lengthened (deeper frame) until gravity alone gives DW 50 g")
    print("      y_b  tail end  frame  total depth  white bar(g)  UW    ratio  m_eff  black bar(g)  steel 88 keys")
    for yb in (150.0, 160.0):
        for ye in [P0_GLOBAL["y_end"] + 5 * i for i in range(0, 60)]:
            K, H = max_bar_key(Pb, False, ye, yb)
            if K.statics()["DW"] < 50.0:
                continue
            Kt = trim_to(K, 50.0, False)
            Kb, Hb = max_bar_key(Pb, True, ye, yb)
            Kbt = trim_to(Kb, 50.0, True)
            st = Kt.statics()
            fd = ye + 1.5 + 3.0
            row = dict(y_b=yb, y_end=ye, frame=fd, total=V3["v3_total_depth"] + fd - 212, bar=bar_mass(Kt),
                       bar_b=bar_mass(Kbt), m_eff=st["m_eff"], ratio=st["ratio_90"], UW=st["UW"],
                       steel88=(52 * bar_mass(Kt) + 36 * bar_mass(Kbt)) / 1000)
            out["extended"].append(row)
            print("      %4.0f  y%6.1f  %5.0f  %8.0f   %8.0f     %5.1f %6.2f %6.1f  %8.0f       %5.1f kg"
                  % (yb, ye, fd, row["total"], row["bar"], row["UW"], row["ratio"], row["m_eff"], row["bar_b"],
                     row["steel88"]))
            break
        # longer keys: steel falls, inertia rises
        for ye in (256.5, 306.5):
            if out["extended"] and abs(out["extended"][-1]["y_end"] - ye) < 1e-6 and out["extended"][-1]["y_b"] == yb:
                continue
            K, H = max_bar_key(Pb, False, ye, yb)
            Kt = trim_to(K, 50.0, False)
            Kb, Hb = max_bar_key(Pb, True, ye, yb)
            Kbt = trim_to(Kb, 50.0, True)
            st = Kt.statics()
            fd = ye + 4.5
            print("      %4.0f  y%6.1f  %5.0f  %8.0f   %8.0f     %5.1f %6.2f %6.1f  %8.0f       %5.1f kg"
                  % (yb, ye, fd, V3["v3_total_depth"] + fd - 212, bar_mass(Kt), st["UW"], st["ratio_90"], st["m_eff"],
                     bar_mass(Kbt), (52 * bar_mass(Kt) + 36 * bar_mass(Kbt)) / 1000))
    # full evaluation of the best in-frame pure-gravity variant
    yb = out["best_in_frame"]["y_b"]
    Pg, Wg, Bg, _, notes = configure(P0_GLOBAL, yb, spring=False)
    Eg = evaluate(Pg, Wg, Bg, dyn=True, press=())
    print("  (c) in-frame pure gravity at y_b %.0f, full evaluation (bars 9x%.0f: white %.0f mm, black %.0f mm) %s"
          % (yb, Pg["bar_h"], Pg["bar_len_w"], Pg["bar_len_b"], notes or ""))
    for nm, K in (("white", Wg), ("black", Bg)):
        st, se, r = Eg[nm]["st"], Eg[nm]["se"], Eg[nm]["ret"]
        imp = Sim(K).run_impact(1.0)
        print("      %s: bar %.0f g, DW %.1f, UW %.1f/%.1f, ratio %.2f, travel %.2f, m_eff %.1f, t_rt %.1f ms, t_full %.1f ms,"
              " re-trigger %.1f Hz, pin lift @1 m/s %.3f mm, tail rise %.1f"
              % (nm, bar_mass(K), st["DW"], st["UW_rest"], st["UW"], st["ratio_90"], se["travel"], st["m_eff"],
                 r["t_rt"] * 1e3, r["t_full"] * 1e3, 1 / (2 * r["t_rt"]), imp["h_max"] * 1e3,
                 max(K.zpt((y, K.f["z_tt"]), K.phi_bot) for y in (K.f["bar"][0], K.f["bar"][1])) - K.f["z_tt"]))
        out["pg_" + nm] = dict(bar=bar_mass(K), DW=st["DW"], UW=st["UW_rest"], ratio=st["ratio_90"],
                               travel=se["travel"], m_eff=st["m_eff"], t_rt=r["t_rt"], t_full=r["t_full"])
    out["pg_steel88"] = (52 * bar_mass(Wg) + 36 * bar_mass(Bg)) / 1000
    print("      steel for 88 keys %.1f kg; control board would have to fit y94..%.0f (%.0f mm deep)"
          % (out["pg_steel88"], yb - 7, yb - 7 - 94))
    return out


P0_GLOBAL = dict(P)

if __name__ == "__main__":
    R = main()
