#!/usr/bin/env python3
"""Toccata v4 key action — concept F1 "over-tail counter-lever" (오버테일 카운터레버).

Architecture (side view, y = depth from the white-key lip, z = height above the desk):
  * The key is a rigid printed body that pivots at its REAR on a shared Ø3 steel rod (KP, one per octave).
    Behind the visible part (y>146) the key continues only as a thin keel (3 mm plate) that dives under
    the weight zone to a C-hook on the rod.
  * Directly behind the visible key, a weighted counter-lever pivots on a second shared Ø3 rod (LP) that
    rests in open-top notches of a printed fin comb.  Its short front arm (nose) reaches forward INTO the
    key's hollow and pushes UP on a cloth pad under the key top skin; its rear arm carries a cut piece of
    9 mm steel flat bar that sits ABOVE the key keel, under the nameboard cover (hidden dead space).
  * Pressing the key pushes the nose down -> the steel rises (about 1:1 with the key front).  Releasing:
    the steel falls and pushes the key back up against its front up-stop (v3 hook + crossbar, felt).
  * Rest position = key up-stop (felt) with the lever pushing the key into it by gravity only.
  * Nothing plastic carries a bending stress above ~1.3 MPa at rest (see STRESS); both pivots are steel rods.
Units: mm, g, ms.  Force N (= g*mm/ms^2), torque N*mm.  1 gf = 9.80665e-3 N.
Every number printed by this script is computed here from explicit geometry and masses.
"""
import math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

gacc = 9.80665e-3          # mm/ms^2
GF = 9.80665e-3            # N per gram-force  (g*mm/ms^2 = N)
RHO_PETG = 1.25e-3         # g/mm^3  (Bambu PETG Basic)
RHO_STEEL = 7.85e-3
RHO_MAG = 7.5e-3           # sintered NdFeB
RHO_FELT = 0.40e-3         # high-density wool felt
RHO_CLOTH = 0.50e-3        # key bushing cloth

# ------------------------------------------------------------------ fixed v3 interfaces (kept)
V3 = dict(
    white_top=43.5, key_bot=23.5, black_top=55.5, white_len=146.0,
    dip_w=10.0, dip_b=9.5, black_front_top=52.5, black_front_base=51.5,
    mag_y_w=65.8, mag_y_b=64.2, mag_face_z=23.5,
    elem_z_w=12.68, elem_z_b=10.15, sensor_row_y=67.0, g_min=3.0,
    frame_depth=212.0, rear_wall=(209.0, 212.0), cover_under=56.5, cover_top=59.0,
    floor_top=5.0, fascia_low=44.5,
    upstop_w=(10.5, 14.0), upstop_b=(76.5, 80.0), crossbar_top=25.1,
    downplate_w=(2.7, 10.5), downplate_b=(52.7, 59.0), plate_t=1.2,
    guide_w_y=18.75, guide_b_y=87.5,
)
# x positions of the 12 keys in an octave module (v3 sensor/magnet x, module left edge = 0)
KEY_X = dict(C=7.431, Cs=21.215, D=35.250, Ds=49.285, E=63.070, F=77.359, Fs=90.573,
             G=104.037, Gs=117.500, A=130.964, As=144.427, B=157.641)
BLACK = {"Cs", "Ds", "Fs", "Gs", "As"}

# ------------------------------------------------------------------ design parameters (F1)
P = dict(
    KP=(205.0, 18.0),        # key rear pivot: Ø3 steel rod (shared per octave) held by the rear comb
    rod_d=3.0,
    yL=151.0,                # lever pivot rod y (shared Ø3 rod, per octave, in open-top fin notches)
    r_tip_w=10.0,            # white lever: nose centre ahead of the lever pivot
    r_tip_b=13.0,            # black lever: longer nose arm (black key rotates 28 % more)
    r_nose=2.0,
    nose_dz=1.5,             # nose centre above the lever-pivot line at mid-stroke (tunes nose slip)
    pad_t=0.6,               # bushing cloth pad under the key skin (lever nose contact)
    skin_w=2.0, skin_b=2.0, wall=1.2,   # white skin 2.6 -> 2.0: it no longer doubles as the v3 leaf
    keel_w=3.0,              # key keel (tail plate) thickness, x, from the hollow to the lever rod
    keel_w2=4.5, keel_h=7.5,  # keel section under the weights (x width, z height)
    keel_neck_end=149.0,     # tall keel neck ends in front of the lever rod (rod y149.5-152.5); low keel behind
    notch_chamfer=2.5,       # white head notch-face lower chamfer (v3 S10 was 1.5): clears the black key's arc
    keel_step=172.0, keel_w3=8.0, keel_h3=4.5,   # rear keel section: wider and flatter
    riser_len=3.0,           # keel rises to the hook in the last 3 mm in front of the rear comb
    steel_w=9.0,             # 9T flat bar (same stock as build-set C)
    steel_h=25.0,            # 9 x 25 flat bar, on edge (25 in z)
    carrier_wall=1.2, carrier_floor=1.2,
    side_plate=1.5,          # lever = one flat side plate (printed on the bed) + floor + end walls; steel face open
    lever_w_tip=3.6, lever_w_hub=4.4,
    fin_half=3.0,            # lever carrier starts 0.6 behind yL + fin_half (hub radius 3.6)
    fin_t=1.2,               # thin fin plates at the lever-column boundaries hold the lever rod
    steel_ahead=3.6,         # steel front face this far behind the lever rod (carrier front wall 1.0 ahead of it)
    over=0.5,                # lever overtravel beyond key bottom, measured at the tab (mm)
    guard=1.5,               # rest guard (lower tab felt) below the working rest, at the tab (mm); lever lands on it on return
    tab_pad=(5.0, 8.0),      # tab stop felt contact (x, y) in the rear comb pocket, 3T felt
    tab_y=(199.8, 207.8),    # lever rear stop tab y range (runs in a pocket of the rear comb), 6 wide in x
    tab_dz=3.0,              # tab centre above the steel centre line (keeps the pocket floor clear of the key rod)
    cover_under=57.5,        # rear cover top plate thinned 2.5 -> 1.5 over y150-200 (top stays z59)
    tooth=(200.0, 209.0),    # rear comb block (key-rod bores, key-hook slots, tab pockets with 2 felts)
    steel_dz=-0.5,           # steel centre below the lever line (reference pose)
    B_target_w=44.0,         # static balance weight at y13, mid-stroke (g)
    B_target_b=43.0,         # black: at y62.5
    y_finger_w=13.0, y_finger_b=62.5,
    mu_pivot=0.20,           # PETG on steel, dry (grease -> ~0.1)
    mu_tip=0.30,             # PETG nose on bushing cloth
    guide_drag_gf=2.0,       # front guide tab in 0.5T bushing felt, drag at the guide (gf)
    E_felt=0.40,             # MPa, 3T wool felt initial modulus (v3: 4.8 mJ -> ~52 % compression)
    E_cloth=3.0,             # MPa, 0.6T bushing cloth
    zeta_felt=0.35,          # felt damping ratio (restitution ~0.3)
)


def rot(p, c, a):
    """rotate point p=(y,z) about c by a (CCW; + = key front down / lever steel up)."""
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


class Body:
    """rigid body made of boxes (y0,y1,z0,z1,wx,rho,fill); in-plane (y,z) inertia with parallel-axis terms."""

    def __init__(self, name, pivot):
        self.name, self.pivot, self.boxes = name, pivot, []

    def add(self, tag, y0, y1, z0, z1, wx, rho=RHO_PETG, fill=1.0, xr=None):
        """xr = (x0, x1) relative to the key centre line (for clearance checks); None = whole key width."""
        assert y1 > y0 and z1 > z0 and wx > 0, tag
        self.boxes.append((tag, y0, y1, z0, z1, wx, rho, fill, xr))

    def props(self):
        m = sy = sz = Ic = 0.0
        mp = ms = 0.0
        rows = []
        for tag, y0, y1, z0, z1, wx, rho, fill, xr in self.boxes:
            mi = (y1 - y0) * (z1 - z0) * wx * rho * fill
            yc, zc = (y0 + y1) / 2, (z0 + z1) / 2
            m += mi
            sy += mi * yc
            sz += mi * zc
            rows.append((tag, mi, yc, zc, mi * ((y1 - y0) ** 2 + (z1 - z0) ** 2) / 12))
            if rho == RHO_PETG:
                mp += mi
            if rho == RHO_STEEL:
                ms += mi
        com = (sy / m, sz / m)
        I_com = 0.0
        for tag, mi, yc, zc, Iown in rows:
            I_com += Iown + mi * ((yc - com[0]) ** 2 + (zc - com[1]) ** 2)
        dp = (com[0] - self.pivot[0]) ** 2 + (com[1] - self.pivot[1]) ** 2
        return dict(m=m, com=com, I_com=I_com, I_piv=I_com + m * dp, m_petg=mp, m_steel=ms, rows=rows)


# ------------------------------------------------------------------ key bodies
def keel_bottom(y):
    """keel underside z at rest in the weight zone: clears the floor by 0.8 mm at full black-key dip."""
    return V3["floor_top"] + 0.8 + (P["KP"][0] - y) * math.tan(LAY_TH_B)


LAY_TH_B = 0.0626    # black dip angle (refined after layout; only sets the keel floor clearance)


def white_key():
    K = Body("white", P["KP"])
    t, w = P["skin_w"], P["wall"]
    top, bot = V3["white_top"], V3["key_bot"]
    zs = top - t
    tail_w = 14.36
    K.add("skin head", 0.0, 50.0, zs, top, 22.5)
    K.add("skin tail", 50.0, 146.0, zs, top, tail_w)
    K.add("front wall", 1.5, 2.7, bot, zs, 22.5)
    K.add("head side walls", 2.7, 50.0, bot, zs, 2 * w)
    K.add("notch wall", 48.8, 50.0, bot, zs, 22.5 - tail_w)
    K.add("tail side walls", 50.0, 146.0, bot, zs, 2 * w)
    K.add("guide ribs", 10.5, 27.0, bot, zs, 2 * w)
    K.add("up-stop crossbar", 10.5, 14.0, bot, V3["crossbar_top"], 8.6)
    K.add("down-stop plate", 2.7, 10.5, bot, bot + V3["plate_t"], 20.1)
    K.add("magnet boss (tube)", 62.0, 69.6, bot, zs, 3.18)
    K.add("magnet N35 5x2", 63.3, 68.3, bot, bot + 2.0, 3.93, RHO_MAG)
    K.add("transverse ribs", 94.4, 95.6, bot + 4, zs, 11.96)
    K.add("transverse ribs", 119.4, 120.6, bot + 4, zs, 11.96)
    return K


def black_key():
    K = Body("black", P["KP"])
    t, w = P["skin_b"], P["wall"]
    top, bot = V3["black_top"], V3["key_bot"]
    zs = top - t
    K.add("top skin", 52.5, 146.0, zs, top, 9.9)
    K.add("side walls", 51.5, 146.0, bot, zs, 2 * w)
    K.add("front wall", 51.5, 52.7, bot, zs, 8.6)
    K.add("down-stop plate", 52.7, 59.0, bot, bot + V3["plate_t"], 8.6)
    K.add("up-stop crossbar", 76.5, 80.0, bot, V3["crossbar_top"], 8.6)
    K.add("magnet boss (tube)", 60.4, 68.0, bot, zs, 3.18)
    K.add("magnet N35 5x2", 61.7, 66.7, bot, bot + 2.0, 3.93, RHO_MAG)
    K.add("transverse rib", 109.4, 110.6, bot + 4, zs, 8.6)
    return K


def add_tail(K, black, y_c, z_pad):
    """nose contact pad + keel + rear C-hook (shared by white/black)."""
    kw = P["keel_w"]
    top = V3["black_top"] if black else V3["white_top"]
    zs = top - (P["skin_b"] if black else P["skin_w"])
    X = XR_B if black else XR_W
    if black:   # bridge block inside the black key: its underside carries the pad at z_pad
        K.add("contact bridge (40 % infill)", y_c - 5.0, 146.0, z_pad + P["pad_t"], zs, 6.0, fill=0.40, xr=X["nose"])
    K.add("contact pad cloth", y_c - 4.0, y_c + 4.0, z_pad, z_pad + P["pad_t"], 4.0, RHO_CLOTH, xr=X["nose"])
    K.add("keel web in hollow", 136.0, 146.0, V3["key_bot"], zs, kw, xr=X["keel"])
    yL = P["yL"]
    rod_bot = LEVER_ZL - P["rod_d"] / 2
    K.add("keel under lever rod", 146.0, P["keel_neck_end"], 9.5, rod_bot - 0.8, kw, xr=X["keel"])   # neck, ends ahead of the rod
    # weight zone: flat keel stepped down toward the rear (moment falls toward the hook)
    y_riser = P["tooth"][0] - P["riser_len"]
    for (y0, y1), h, w in (((P["keel_neck_end"], P["keel_step"]), P["keel_h"], P["keel_w2"]),
                           ((P["keel_step"], y_riser), P["keel_h3"], P["keel_w3"])):
        zb = keel_bottom(y0)
        K.add("keel under weights", y0, y1, zb, zb + h, w, xr=(X["keel"][0], X["keel"][0] + w))
    KPy, KPz = P["KP"]
    zb = keel_bottom(y_riser)
    K.add("keel riser to hook", y_riser, P["tooth"][0], zb, max(zb + P["keel_h3"], KPz + 4.5), kw, xr=X["keel"])
    K.add("rear C-hook (60 % solid)", P["tooth"][0], KPy + 3.5, KPz - 4.5, KPz + 4.5, kw, fill=0.60, xr=X["keel"])
    return K


# x ranges relative to the key centre line (white key interior +-5.98, black +-4.3)
XR_W = dict(keel=(-4.5, -1.5), nose=(-0.5, 3.1), hub=(-0.5, 3.9), carrier=(-5.25, 5.25), tab=(0.5, 5.5))
XR_B = dict(keel=(-5.5, -2.5), nose=(-1.5, 2.1), hub=(-1.5, 2.9), carrier=(-5.25, 5.25), tab=(0.5, 5.5))

# ------------------------------------------------------------------ lever
LEVER_ZL = None   # set by layout()


def lever_body(black, steel_len, steel_y0, steel_dz, tab_z):
    """printed carrier + 9xH steel bar.  Reference pose (phi = 0): nose radial line horizontal."""
    yL, zL = P["yL"], LEVER_ZL
    r_tip = P["r_tip_b"] if black else P["r_tip_w"]
    L = Body("lever_b" if black else "lever_w", (yL, zL))
    X = XR_B if black else XR_W
    rn = P["r_nose"]
    L.add("nose + arm", yL - r_tip - rn, yL - 3.0, zL - 2.5, zL + 2.5, P["lever_w_tip"], xr=X["nose"])
    L.add("hub ring (Ø7.2/Ø3.2)", yL - 3.6, yL + 3.6, zL - 3.6, zL + 3.6, P["lever_w_hub"], fill=0.63, xr=X["hub"])
    cw, cf = P["carrier_wall"], P["carrier_floor"]
    sw, sh = P["steel_w"], P["steel_h"]
    zs0 = zL + steel_dz - sh / 2          # steel bottom (reference pose)
    if steel_y0 - cw > yL + 3.6 + 0.1:
        L.add("neck", yL + 3.6, steel_y0 - cw, zL - 3.0, zL + 3.0, P["lever_w_hub"], xr=X["hub"])
    C = X["carrier"]
    L.add("carrier floor", steel_y0 - cw, steel_y0 + steel_len + cw, zs0 - cf, zs0, sw + P["side_plate"], xr=C)
    L.add("carrier side plate", steel_y0 - cw, steel_y0 + steel_len + cw, zs0, zs0 + sh - 3.0, P["side_plate"], xr=C)
    L.add("carrier end walls", steel_y0 - cw, steel_y0, zs0, zs0 + sh - 3.0, sw, xr=C)
    L.add("carrier end walls", steel_y0 + steel_len, steel_y0 + steel_len + cw, zs0, zs0 + sh - 3.0, sw, xr=C)
    if P["tab_y"][1] > steel_y0 + steel_len + cw + 0.1:
        L.add("rear stop tab", steel_y0 + steel_len + cw, P["tab_y"][1], tab_z - 2.0, tab_z + 2.0, 5.0, fill=0.8, xr=X["tab"])
    L.add("steel 9T flat bar", steel_y0, steel_y0 + steel_len, zs0, zs0 + sh, sw, RHO_STEEL, xr=C)
    return L


# ------------------------------------------------------------------ kinematics
def key_contact_line(black, th, y_c, z_pad):
    Pt = rot((y_c, z_pad), P["KP"], th)
    return Pt, (math.cos(th), math.sin(th)), (math.sin(th), -math.cos(th))   # point, tangent, downward normal


def nose_center(black, ph):
    r_tip = P["r_tip_b"] if black else P["r_tip_w"]
    return rot((P["yL"] - r_tip, LEVER_ZL + P["nose_dz"]), (P["yL"], LEVER_ZL), ph)


def gap(black, th, ph, y_c, z_pad):
    Pt, t, nd = key_contact_line(black, th, y_c, z_pad)
    N = nose_center(black, ph)
    return (N[0] - Pt[0]) * nd[0] + (N[1] - Pt[1]) * nd[1] - P["r_nose"]


def phi_of(black, th, y_c, z_pad):
    """lever angle that keeps the nose on the key pad (gap = 0)."""
    return brentq(lambda ph: gap(black, th, ph, y_c, z_pad), -0.8, 0.8, xtol=1e-12)


def dip_angle(black):
    """key rotation that gives the v3 dip (white lip top 10 at y0, black front top edge 9.5 at y52.5)."""
    if black:
        p0, dip = (V3["black_front_top"], V3["black_top"]), V3["dip_b"]
    else:
        p0, dip = (0.0, V3["white_top"]), V3["dip_w"]
    return brentq(lambda a: p0[1] - rot(p0, P["KP"], a)[1] - dip, 0.0, 0.3, xtol=1e-12)


# ------------------------------------------------------------------ layout (contact heights, lever pivot height)
def layout():
    """white pad z from the v3 key; lever pivot z so the white nose swings symmetrically about horizontal;
    black pad z so the black nose also swings symmetrically."""
    global LEVER_ZL
    th_w, th_b = dip_angle(False), dip_angle(True)
    yc_w, yc_b = P["yL"] - P["r_tip_w"], P["yL"] - P["r_tip_b"]
    zpad_w = V3["white_top"] - P["skin_w"] - P["pad_t"]
    # vertical travel of the pad at the nose y (exact rotation)
    s_w = zpad_w - rot((yc_w, zpad_w), P["KP"], th_w)[1]
    LEVER_ZL = zpad_w - P["r_nose"] - s_w / 2 - P["nose_dz"]
    s_b0 = 0.0
    zpad_b = LEVER_ZL + P["nose_dz"] + P["r_nose"]
    for _ in range(20):    # fixed point: pad z such that the black nose swings +-s_b/2 about its mid pose
        s_b0 = zpad_b - rot((yc_b, zpad_b), P["KP"], th_b)[1]
        zpad_b = LEVER_ZL + P["nose_dz"] + P["r_nose"] + s_b0 / 2
    return dict(th_w=th_w, th_b=th_b, yc_w=yc_w, yc_b=yc_b, zpad_w=zpad_w, zpad_b=zpad_b, s_w=s_w, s_b=s_b0)


LAY = layout()


def relayout(**kw):
    """change design parameters and recompute the layout (used by the parameter study)."""
    global LAY
    P.update(kw)
    LAY = layout()
    return LAY


def finger_pt(black):
    return (P["y_finger_b"], V3["black_top"]) if black else (P["y_finger_w"], V3["white_top"])


def perp_vel(p, c, w):
    return (-w * (p[1] - c[1]), w * (p[0] - c[0]))


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


class Action:
    """one key + its lever (white or black) with statics / kinematics helpers."""

    def __init__(self, black, steel_len, steel_dz=0.0, tab_z=None):
        self.black = black
        self.yc = LAY["yc_b"] if black else LAY["yc_w"]
        self.zpad = LAY["zpad_b"] if black else LAY["zpad_w"]
        self.th_max = LAY["th_b"] if black else LAY["th_w"]
        K = black_key() if black else white_key()
        add_tail(K, black, self.yc, self.zpad)
        self.K = K
        self.kp = K.props()
        self.steel_len, self.steel_dz = steel_len, steel_dz
        self.steel_y0 = P["yL"] + P["steel_ahead"]
        self.tab_z = LEVER_ZL + steel_dz + P["tab_dz"] if tab_z is None else tab_z
        self.L = lever_body(black, steel_len, self.steel_y0, steel_dz, self.tab_z)
        self.lp = self.L.props()
        self.LP = (P["yL"], LEVER_ZL)
        self.ph_rest = phi_of(black, 0.0, self.yc, self.zpad)
        self.ph_bot = phi_of(black, self.th_max, self.yc, self.zpad)
        self.fp = finger_pt(black)
        s = self.L
        zs0 = LEVER_ZL + steel_dz - P["steel_h"] / 2
        self.steel_com_ref = (self.steel_y0 + steel_len / 2, zs0 + P["steel_h"] / 2)
        self.r_tab = P["tab_y"][1] - P["yL"]

    # --- positions
    def phi(self, th):
        return phi_of(self.black, th, self.yc, self.zpad)

    def V(self, th, ph=None):
        ph = self.phi(th) if ph is None else ph
        zk = rot(self.kp["com"], P["KP"], th)[1]
        zl = rot(self.lp["com"], self.LP, ph)[1]
        return self.kp["m"] * gacc * zk + self.lp["m"] * gacc * zl

    def zf(self, th, pt=None):
        return rot(pt or self.fp, P["KP"], th)[1]

    def contact(self, th, ph):
        Pt, t, nd = key_contact_line(self.black, th, self.yc, self.zpad)
        N = nose_center(self.black, ph)
        C = (N[0] - P["r_nose"] * nd[0], N[1] - P["r_nose"] * nd[1])
        return C, t, nd

    # --- statics at key angle th
    def statics(self, th, h=1e-6, pt=None):
        ph = self.phi(th)
        dph = (self.phi(th + h) - self.phi(th - h)) / (2 * h)
        dV = (self.V(th + h) - self.V(th - h)) / (2 * h)
        dzf = (self.zf(th + h, pt) - self.zf(th - h, pt)) / (2 * h)
        B = dV / (-dzf) / GF                                   # gf, balance weight at the finger
        # contact force from the lever moment balance (quasi-static)
        C, t, nd = self.contact(th, ph)
        comL = rot(self.lp["com"], self.LP, ph)
        tau_gL = -self.lp["m"] * gacc * (comL[0] - self.LP[0])
        arm = cross((C[0] - self.LP[0], C[1] - self.LP[1]), nd)
        fn = -tau_gL / arm                                      # N, >0 = pushing the nose down
        RL = (-fn * nd[0], self.lp["m"] * gacc - fn * nd[1])
        Ff = B * GF
        RK = (fn * nd[0], self.kp["m"] * gacc + fn * nd[1] + Ff)
        # slip at the contact per unit key rotation
        vk = perp_vel(C, P["KP"], 1.0)
        vl = perp_vel(C, self.LP, dph)
        slip = (vl[0] - vk[0]) * t[0] + (vl[1] - vk[1]) * t[1]
        gy = V3["guide_b_y"] if self.black else V3["guide_w_y"]
        dzg = (rot((gy, V3["key_bot"]), P["KP"], th + h)[1] - rot((gy, V3["key_bot"]), P["KP"], th - h)[1]) / (2 * h)
        r = P["rod_d"] / 2
        fr = dict(
            key_pivot=P["mu_pivot"] * math.hypot(*RK) * r / abs(dzf) / GF,
            lever_pivot=P["mu_pivot"] * math.hypot(*RL) * r * abs(dph) / abs(dzf) / GF,
            nose_slide=P["mu_tip"] * abs(fn) * abs(slip) / abs(dzf) / GF,
            guide_bushing=P["guide_drag_gf"] * abs(dzg) / abs(dzf),
        )
        I = self.kp["I_piv"] + self.lp["I_piv"] * dph ** 2
        m_eff = I / dzf ** 2
        m_eff_key = self.kp["I_piv"] / dzf ** 2
        steel = rot(self.steel_com_ref, self.LP, ph)
        steel_h = rot(self.steel_com_ref, self.LP, ph + dph * h)[1] - rot(self.steel_com_ref, self.LP, ph - dph * h)[1]
        R = (steel_h / (2 * h)) / (-dzf)
        return dict(th=th, ph=ph, dph=dph, B=B, fn=fn, RK=RK, RL=RL, fric=fr, F_fric=sum(fr.values()),
                    m_eff=m_eff, m_eff_key=m_eff_key, m_eff_lever=m_eff - m_eff_key, R=R, dzf=dzf,
                    slip=slip, steel=steel)

    def balance_profile(self, n=11):
        return [self.statics(self.th_max * i / (n - 1)) for i in range(n)]


def solve_steel(black, target, steel_dz=0.0):
    """steel length (0.5 mm steps, rounded to nearest) that gives the target balance weight at mid-stroke."""
    def f(Ls):
        A = Action(black, Ls, steel_dz)
        return A.statics(A.th_max / 2)["B"] - target
    Ls = brentq(f, 2.0, 80.0, xtol=1e-4)
    return round(Ls * 2) / 2, Ls


# ------------------------------------------------------------------ geometry checks
def box_corners(b):
    tag, y0, y1, z0, z1 = b[:5]
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def body_pts(body, pivot, ang, tags=None, n=6):
    """corner + edge sample points of a body's boxes rotated by ang about pivot."""
    pts = []
    for b in body.boxes:
        if tags and not any(t in b[0] for t in tags):
            continue
        c = box_corners(b)
        for i in range(4):
            a, bb = c[i], c[(i + 1) % 4]
            for k in range(n):
                s = k / n
                pts.append((b[0], rot((a[0] + (bb[0] - a[0]) * s, a[1] + (bb[1] - a[1]) * s), pivot, ang), b[8]))
    return pts


def x_overlap(a, b):
    return a is None or b is None or (a[0] < b[1] and b[0] < a[1])


def keel_clear(K, pt, th=0.0, xr=None):
    """vertical clearance of a point above the keel boxes whose y-range (and x-range) contains it."""
    best = None
    for b in K.boxes:
        if not b[0].startswith("keel") or not x_overlap(xr, b[8]):
            continue
        a, c = rot((b[1], b[4]), P["KP"], th), rot((b[2], b[4]), P["KP"], th)
        if min(a[0], c[0]) <= pt[0] <= max(a[0], c[0]):
            z = a[1] + (c[1] - a[1]) * (pt[0] - a[0]) / (c[0] - a[0])
            d = pt[1] - z
            best = d if best is None else min(best, d)
    return best


def angles_of(A):
    over = P["over"] / A.r_tab
    guard = P["guard"] / A.r_tab
    return dict(rest=A.ph_rest, bot=A.ph_bot, over=A.ph_bot + over, guard=A.ph_rest - guard)


def checks(A):
    """clearances (mm) of the moving parts; every value is a minimum over the stated poses."""
    out = {}
    ang = angles_of(A)
    LP = A.LP
    heavy = ("steel", "carrier")
    # 1 cover underside vs lever top (at overtravel)
    top = max(p[1][1] for p in body_pts(A.L, LP, ang["over"]))
    out["lever_top_z_over"] = top
    out["cover_clear"] = P["cover_under"] - top
    # 2 lever (all parts) vs own key keel/web, key at rest & lever at rest (the closest pose)
    c = 1e9
    for tag, pt, xr in body_pts(A.L, LP, ang["rest"], None, n=20):
        d = keel_clear(A.K, pt, 0.0, xr)
        if d is not None and not tag.startswith("nose"):
            c = min(c, d)
    out["keel_clear_rest"] = c
    # 2b carrier/steel front face vs the rear face of the tall keel neck (horizontal gap), key at rest
    neck = [b for b in A.K.boxes if b[0] == "keel under lever rod"][0]
    gy = 1e9
    for a in ("rest", "guard", "over"):
        for tag, (y, z), xr in body_pts(A.L, LP, ang[a], heavy, n=20):
            if x_overlap(xr, neck[8]) and neck[3] - 0.5 <= z <= neck[4] + 0.5:
                gy = min(gy, y - neck[2])
    out["neck_to_carrier_y"] = gy
    # 3 lever lowest point at the rest guard (key removed) vs floor / keel-less column
    out["lever_low_z_guard"] = min(p[1][1] for p in body_pts(A.L, LP, ang["guard"], heavy))
    # 4 rear: carrier must stay in front of the rear comb teeth, tab inside the tooth pocket
    ymax = max(p[1][0] for a in ("rest", "over", "guard") for p in body_pts(A.L, LP, ang[a], heavy))
    out["rear_clear"] = P["tooth"][0] - ymax
    # 5 nose arm top edge vs the key's skin/bridge underside between the pad and the key end (y146)
    worst = 1e9
    under = (A.zpad + P["pad_t"])        # underside of skin (white) / bridge (black) above the arm
    for th, ph in ((0.0, A.ph_rest), (A.th_max, A.ph_bot)):
        for tag, (y, z), xr in body_pts(A.L, LP, ph, ("nose",), n=30):
            if A.yc + 4.0 <= y <= 146.0:
                ks = rot((y, under), P["KP"], th)[1]
                worst = min(worst, ks - z)
    out["arm_under_skin"] = worst
    # 6 key rear end (y146 face) vs lever rod
    yr = min(rot((146.0, z), P["KP"], th)[0] for z in (V3["key_bot"], V3["white_top"]) for th in (0.0, A.th_max))
    out["key_end_to_rod"] = (P["yL"] - P["rod_d"] / 2) - max(rot((146.0, z), P["KP"], th)[0]
                                                           for z in (V3["key_bot"], V3["white_top"]) for th in (0.0, A.th_max))
    # 7 keel (all boxes) vs lever rod surface (the rod crosses every column), key at rest and at the bottom
    best = 1e9
    for th in (0.0, A.th_max):
        for b in A.K.boxes:
            if not b[0].startswith("keel"):
                continue
            for i in range(4):
                a, c2 = box_corners(b)[i], box_corners(b)[(i + 1) % 4]
                for s in np.linspace(0, 1, 41):
                    q = rot((a[0] + (c2[0] - a[0]) * s, a[1] + (c2[1] - a[1]) * s), P["KP"], th)
                    best = min(best, math.hypot(q[0] - P["yL"], q[1] - LEVER_ZL) - P["rod_d"] / 2)
    out["keel_to_rod"] = best
    # 8 keel underside vs floor at full dip
    lo = 1e9
    for b in A.K.boxes:
        if b[0].startswith("keel"):
            for p in box_corners(b):
                lo = min(lo, rot(p, P["KP"], A.th_max)[1])
    out["keel_floor_clear_dip"] = lo - V3["floor_top"]
    # 9 key underside over the relocated control board (y82..132, parts <= z14.5)
    zmin = min(rot((y, V3["key_bot"]), P["KP"], A.th_max)[1] for y in np.linspace(82, 132, 51))
    out["board_clear_dip"] = zmin - 14.5
    # 10 lever vs nameboard fascia (v3 cover front plate, lower edge z44.5; inner face assumed y148.5)
    fy = 1e9
    for a in ("rest", "over", "guard"):
        for tag, (y, z), xr in body_pts(A.L, LP, ang[a], None, n=20):
            if z >= V3["fascia_low"] - 0.5:
                fy = min(fy, y - 148.5)
    out["fascia_clear_y"] = fy
    return out


def x_layout():
    """lever columns between fin plates at the midpoints of neighbouring key centres (module 164.5)."""
    names = list(KEY_X)
    xs = [KEY_X[n] for n in names]
    left = [xs[-1] - 164.5] + xs[:-1]
    right = xs[1:] + [xs[0] + 164.5]
    rows = []
    for n, x, l, r in zip(names, xs, left, right):
        sh = dict(B=-0.35)           # the A#|B fin is shifted left: the B column is closed by the module-edge fin
        f0 = (l + x) / 2 + sh.get(n, 0.0) if n != "C" else 0.3   # module edge fins stay inside the module
        f1 = (x + r) / 2 + sh.get(names[(names.index(n) + 1) % 12], 0.0) if n != "B" else 164.2
        col = (f1 - P["fin_t"] / 2) - (f0 + P["fin_t"] / 2) if n not in ("C", "B") else None
        if n == "C":
            col = (f1 - P["fin_t"] / 2) - (f0 + P["fin_t"])
        if n == "B":
            col = (f1 - P["fin_t"]) - (f0 + P["fin_t"] / 2)
        carrier = P["steel_w"] + P["side_plate"]
        rows.append(dict(key=n, x=x, fin_l=f0, fin_r=f1, column=col, side_clear=(col - carrier) / 2))
    return rows


def magnet(A):
    y = V3["mag_y_b"] if A.black else V3["mag_y_w"]
    ez = V3["elem_z_b"] if A.black else V3["elem_z_w"]
    r0 = (y, V3["mag_face_z"])
    r1 = rot(r0, P["KP"], A.th_max)
    r40 = None
    return dict(rest_gap=r0[1] - ez, bottom_gap=r1[1] - ez, travel=r0[1] - r1[1], y_shift=r1[0] - r0[0],
                y_bottom=r1[0])


def stresses(A):
    """constant (rest) stresses in printed parts, MPa.  Loads from the rest statics (finger off)."""
    s0 = A.statics(0.0)
    RKz = abs(s0["RK"][1])
    out = {}
    # keel: shear = hook reaction, bending moment grows toward the key body
    for b in A.K.boxes:
        if b[0] in ("keel under lever rod", "keel under weights"):
            y = b[1]
            M = RKz * (P["KP"][0] - y)
            h, w = b[4] - b[3], b[5]
            out.setdefault("keel", []).append((y, 6 * M / (w * h * h)))
    out["keel_max"] = max(v for _, v in out["keel"])
    # lever neck at the hub rear (steel moment) and nose arm root
    comL = rot(A.lp["com"], A.LP, A.ph_rest)
    M_hub = A.lp["m"] * gacc * (comL[0] - A.LP[0])
    out["lever_hub"] = 6 * M_hub / (P["lever_w_hub"] * 6.0 ** 2)
    r_tip = P["r_tip_b"] if A.black else P["r_tip_w"]
    out["lever_nose_arm"] = 6 * s0["fn"] * (r_tip - 3.6) / (P["lever_w_tip"] * 5.0 ** 2)
    # key up-stop: frame hook lip (v3: 8.3 wide, 1.4 thick, ~3 mm overhang), key crossbar (3.5 x 1.6, span 8.6)
    y_up = sum(V3["upstop_b"] if A.black else V3["upstop_w"]) / 2
    F_up = s0["B"] * GF * (P["KP"][0] - A.fp[0]) / (P["KP"][0] - y_up)
    out["upstop_force_N"] = F_up
    out["upstop_hook_lip"] = 6 * F_up * 3.0 / (8.3 * 1.4 ** 2)
    out["key_crossbar"] = (F_up * 8.6 / 4) * 6 / (3.5 * 1.6 ** 2)
    # key skin over the pad (simply supported between the side walls)
    span = 8.6 if A.black else 11.96
    t = 6.0 if A.black else P["skin_w"]          # black: bridge block (>= 6 deep) carries the pad
    out["key_skin_at_pad"] = (s0["fn"] * span / 4) * 6 / (8.0 * t * t)
    # bearing pressures on the steel rods (projected area)
    out["key_hook_bearing"] = math.hypot(*s0["RK"]) / (P["rod_d"] * P["keel_w"])
    out["lever_hub_bearing"] = math.hypot(*s0["RL"]) / (P["rod_d"] * P["lever_w_hub"])
    out["fin_notch_bearing"] = 12 * math.hypot(*s0["RL"]) / (P["rod_d"] * 1.5 * 13)   # 13 fin blocks, 1.5 seat
    # rear C-hook lower jaw (3 wide, 2.5 thick, rod load at 2 mm from the root)
    out["hook_jaw"] = 6 * math.hypot(*s0["RK"]) * 2.0 / (P["keel_w"] * 2.5 ** 2)
    out["RK_rest"] = s0["RK"]
    out["fn_rest"] = s0["fn"]
    return out


# ------------------------------------------------------------------ dynamics (2 DOF: key angle th, lever angle ph)
def felt(delta, rate, k, c, t):
    """wool felt / cloth pad: hardening spring + linear damper, compression only."""
    if delta <= 0.0:
        return 0.0
    f = k * delta * (1.0 + (delta / (0.4 * t)) ** 2) + c * rate
    return max(f, 0.0)


class Sim:
    """unilateral nose contact (separation allowed), 4 felt stops, Coulomb friction (tanh-smoothed)."""

    def __init__(self, A, spring_gf=0.0):
        self.A = A
        self.KP, self.LP = P["KP"], A.LP
        self.Ik, self.IL = A.kp["I_piv"], A.lp["I_piv"]
        self.mk, self.mL = A.kp["m"], A.lp["m"]
        blk = A.black
        yu = sum(V3["upstop_b"] if blk else V3["upstop_w"]) / 2
        yd = sum(V3["downplate_b"] if blk else V3["downplate_w"]) / 2
        self.up_pt, self.up_z0 = (yu, V3["crossbar_top"]), V3["crossbar_top"]
        self.dn_pt = (yd, V3["key_bot"])
        self.dn_z0 = rot(self.dn_pt, self.KP, A.th_max)[1]
        ty = sum(P["tab_y"]) / 2
        self.tab_top, self.tab_bot = (ty, A.tab_z + 2.0), (ty, A.tab_z - 2.0)
        self.ut_z0 = rot(self.tab_top, self.LP, A.ph_bot)[1] + P["over"]
        self.gd_z0 = rot(self.tab_bot, self.LP, A.ph_rest)[1] - P["guard"]
        E = P["E_felt"]
        a_dn = (20.1 * 7.8) if not blk else (8.6 * 6.3)
        a_tab = P["tab_pad"][0] * P["tab_pad"][1]
        self.k_up, self.k_dn, self.k_tab = E * 8.3 * 3.0 / 3.0, E * a_dn / 3.0, E * a_tab / 3.0
        self.k_c = P["E_cloth"] * 7.2 / P["pad_t"]
        z = P["zeta_felt"]
        s0 = A.statics(0.0)
        r_up = self.KP[0] - yu
        m_up = (self.Ik + self.IL * s0["dph"] ** 2) / r_up ** 2
        m_dn = self.Ik / (self.KP[0] - yd) ** 2
        m_tab = self.IL / (ty - self.LP[0]) ** 2
        C, t, nd = A.contact(0.0, A.ph_rest)
        m_c = 1.0 / (1.0 / (self.Ik / (self.KP[0] - C[0]) ** 2) + 1.0 / (self.IL / (self.LP[0] - C[0]) ** 2))
        self.c_up = 2 * z * math.sqrt(self.k_up * m_up)
        self.c_dn = 2 * z * math.sqrt(self.k_dn * m_dn)
        self.c_tab = 2 * z * math.sqrt(self.k_tab * m_tab)
        self.c_c = 2 * 0.3 * math.sqrt(self.k_c * m_c)
        self.gy = V3["guide_b_y"] if blk else V3["guide_w_y"]
        self.w0k = 2e-3 / (self.KP[0] - A.fp[0])        # 2 mm/s at the finger
        self.w0l = self.w0k * 6.0
        self.finger = lambda t: 0.0
        self.spring_gf = spring_gf                         # optional assist spring, gf at the finger (constant)
        self.rec = None

    def forces(self, t, x):
        A = self.A
        th, w, ph, W = x
        KP, LP = self.KP, self.LP
        tk = -self.mk * gacc * (rot(A.kp["com"], KP, th)[0] - KP[0])
        tl = -self.mL * gacc * (rot(A.lp["com"], LP, ph)[0] - LP[0])
        Fk = [0.0, -self.mk * gacc]
        Fl = [0.0, -self.mL * gacc]
        # nose contact
        g0 = gap(A.black, th, ph, A.yc, A.zpad)
        fn = 0.0
        if g0 < 0.0:
            h = 1e-7
            dg = ((gap(A.black, th + h, ph, A.yc, A.zpad) - g0) / h * w
                  + (gap(A.black, th, ph + h, A.yc, A.zpad) - g0) / h * W)
            fn = max(self.k_c * (-g0) + self.c_c * (-dg), 0.0)
            C, tt, nd = A.contact(th, ph)
            vl, vk = perp_vel(C, LP, W), perp_vel(C, KP, w)
            vs = (vl[0] - vk[0]) * tt[0] + (vl[1] - vk[1]) * tt[1]
            ft = -P["mu_tip"] * fn * math.tanh(vs / 2e-3)
            F = (fn * nd[0] + ft * tt[0], fn * nd[1] + ft * tt[1])
            tl += cross((C[0] - LP[0], C[1] - LP[1]), F)
            tk -= cross((C[0] - KP[0], C[1] - KP[1]), F)
            Fl[0] += F[0]; Fl[1] += F[1]
            Fk[0] -= F[0]; Fk[1] -= F[1]
        # key up-stop (front hook felt, pushes down) and down-stop (front felt, pushes up)
        U = rot(self.up_pt, KP, th)
        f_up = felt(U[1] - self.up_z0, perp_vel(U, KP, w)[1], self.k_up, self.c_up, 3.0)
        tk += cross((U[0] - KP[0], U[1] - KP[1]), (0.0, -f_up)); Fk[1] -= f_up
        D = rot(self.dn_pt, KP, th)
        f_dn = felt(self.dn_z0 - D[1], -perp_vel(D, KP, w)[1], self.k_dn, self.c_dn, 3.0)
        tk += cross((D[0] - KP[0], D[1] - KP[1]), (0.0, f_dn)); Fk[1] += f_dn
        # lever tab: upper felt (overtravel) and lower felt (rest guard)
        T = rot(self.tab_top, LP, ph)
        f_ut = felt(T[1] - self.ut_z0, perp_vel(T, LP, W)[1], self.k_tab, self.c_tab, 3.0)
        tl += cross((T[0] - LP[0], T[1] - LP[1]), (0.0, -f_ut)); Fl[1] -= f_ut
        Tb = rot(self.tab_bot, LP, ph)
        f_gd = felt(self.gd_z0 - Tb[1], -perp_vel(Tb, LP, W)[1], self.k_tab, self.c_tab, 3.0)
        tl += cross((Tb[0] - LP[0], Tb[1] - LP[1]), (0.0, f_gd)); Fl[1] += f_gd
        # finger (+ optional constant assist spring, expressed at the finger, pushing the key up)
        Ff = self.finger(t) - self.spring_gf * GF
        Fp = rot(A.fp, KP, th)
        tk += cross((Fp[0] - KP[0], Fp[1] - KP[1]), (0.0, -Ff)); Fk[1] -= Ff
        # pivot reactions WITH inertia (R = m*a_com - sum F_ext), from a friction-free first pass
        def reaction(m, com0, piv, ang, om, al, Fext):
            c = rot(com0, piv, ang)
            dy, dz = c[0] - piv[0], c[1] - piv[1]
            a = (-al * dz - om * om * dy, al * dy - om * om * dz)
            return (m * a[0] - Fext[0], m * a[1] - Fext[1])
        Rk = reaction(self.mk, A.kp["com"], KP, th, w, tk / self.Ik, Fk)
        Rl = reaction(self.mL, A.lp["com"], LP, ph, W, tl / self.IL, Fl)
        # pivot friction and guide bushing drag
        r = P["rod_d"] / 2
        tk -= P["mu_pivot"] * math.hypot(*Rk) * r * math.tanh(w / self.w0k)
        tl -= P["mu_pivot"] * math.hypot(*Rl) * r * math.tanh(W / self.w0l)
        tk -= P["guide_drag_gf"] * GF * (KP[0] - self.gy) * math.tanh(w / self.w0k)
        return tk, tl, dict(fn=fn, gap=g0, f_up=f_up, f_dn=f_dn, f_ut=f_ut, f_gd=f_gd, RKz=Rk[1], RLz=Rl[1], Ff=Ff)

    def rhs(self, t, x):
        tk, tl, _ = self.forces(t, x)
        return [x[1], tk / self.Ik, x[3], tl / self.IL]

    def run(self, x0, t_end, max_step=0.01):
        sol = solve_ivp(self.rhs, (0.0, t_end), x0, method="LSODA", max_step=max_step, rtol=1e-8, atol=1e-10,
                        dense_output=True)
        ts = np.arange(0.0, t_end, 0.01)
        X = sol.sol(ts)
        return ts, X


def magnet_z(A, th):
    y = V3["mag_y_b"] if A.black else V3["mag_y_w"]
    return rot((y, V3["mag_face_z"]), P["KP"], th)[1]


def return_test(A, spring_gf=0.0, t_end=160.0):
    """release from the bottom (finger lifted at t=0): re-trigger (40 % of magnet travel back) and full return."""
    S = Sim(A, spring_gf)
    x0 = [A.th_max, 0.0, A.ph_bot, 0.0]
    ts, X = S.run(x0, t_end)
    zb, zr = magnet_z(A, A.th_max), magnet_z(A, 0.0)
    rise = np.array([(magnet_z(A, th) - zb) / (zr - zb) for th in X[0]])
    t40 = next((t for t, r in zip(ts, rise) if r >= 0.40), None)
    t90 = next((t for t, r in zip(ts, rise) if r >= 0.90), None)
    tfull = next((t for t, th in zip(ts, X[0]) if th <= 0.0), None)
    fn = []
    rkz = []
    for t, x in zip(ts, X.T):
        _, _, d = S.forces(t, x)
        fn.append(d["fn"])
        rkz.append(d["RKz"])
    fn = np.array(fn)
    i_full = int(tfull / 0.01) if tfull else len(ts) - 1
    # bounce after the first up-stop contact: largest re-descent of the finger point (mm)
    zf = np.array([rot(A.fp, P["KP"], th)[1] for th in X[0]])
    z_rest = rot(A.fp, P["KP"], 0.0)[1]
    bounce = float(max(0.0, z_rest - zf[i_full:].min())) if tfull else None
    # settle: last time the finger point is more than 0.2 mm below rest
    below = np.where(zf < z_rest - 0.2)[0]
    t_settle = float(ts[below[-1]]) if len(below) else 0.0
    return dict(t40=t40, t90=t90, tfull=tfull, rate40=1000.0 / t40 if t40 else None,
                fn_min_during_return=float(fn[50:i_full].min()), sep_during_return=bool((fn[50:i_full] <= 0).any()),
                bounce=bounce, t_settle=t_settle, RKz_max=float(max(rkz)), RKz_min=float(min(rkz)), ts=ts, X=X, fn=fn)


def strike_test(A, v_key, hold_ms=60.0, t_end=320.0, k_f=5.0, zeta_f=0.7, press_in=1.5):
    """velocity-driven keystroke: the finger target moves down at v_key (mm/ms = m/s) until it is press_in mm
    below the bottom, holds, and is lifted hold_ms after the key first reaches the bottom.  The finger pad is
    a push-only spring-damper (k_f N/mm, damping ratio zeta_f on the key's effective mass)."""
    S = Sim(A)
    z0 = rot(A.fp, P["KP"], 0.0)[1]
    zb = rot(A.fp, P["KP"], A.th_max)[1]
    m_eff = A.statics(0.0)["m_eff"]
    c_f = 2 * zeta_f * math.sqrt(k_f * m_eff)
    state = dict(t_rel=1e9)

    def target(t):
        return max(z0 - v_key * t, zb - press_in), (-v_key if z0 - v_key * t > zb - press_in else 0.0)

    def finger(t, x):
        if t >= state["t_rel"]:
            return 0.0
        zt, vt = target(t)
        Fp = rot(A.fp, P["KP"], x[0])
        vz = perp_vel(Fp, P["KP"], x[1])[1]
        return max(0.0, k_f * (Fp[1] - zt) + c_f * (vz - vt))

    x0 = [0.0, 0.0, A.ph_rest, 0.0]
    S.finger = lambda t: 0.0
    base = S.forces

    def forces(t, x, _b=base):
        S.finger = lambda tt, xx=x: finger(tt, xx)
        return _b(t, x)
    S.forces = forces
    ts, X = S.run(x0, 200.0)
    i_b = next((i for i, th in enumerate(X[0]) if th >= A.th_max), None)
    if i_b is None:
        return dict(reached=False)
    state["t_rel"] = ts[i_b] + hold_ms
    ts, X = S.run(x0, t_end)
    t_rel = state["t_rel"]
    vf = [(-perp_vel(rot(A.fp, P["KP"], th), P["KP"], w)[1]) for th, w in zip(X[0], X[1])]
    i_b = next(i for i, th in enumerate(X[0]) if th >= A.th_max)
    gaps, fut, fgd, RKz, fdn = [], [], [], [], []
    for t, x in zip(ts, X.T):
        _, _, d = S.forces(t, x)
        gaps.append(d["gap"]); fut.append(d["f_ut"]); fgd.append(d["f_gd"]); RKz.append(d["RKz"]); fdn.append(d["f_dn"])
    gaps = np.array(gaps)
    i_rel = int(round(t_rel / 0.01))
    i_sep = int(np.argmax(gaps[:i_rel]))
    land_v = 0.0
    for i in range(i_sep, i_rel):
        if gaps[i] <= 0.0:
            th, w, ph, W = X[:, i]
            h = 1e-7
            g0 = gap(A.black, th, ph, A.yc, A.zpad)
            dg = ((gap(A.black, th + h, ph, A.yc, A.zpad) - g0) / h * w + (gap(A.black, th, ph + h, A.yc, A.zpad) - g0) / h * W)
            land_v = -dg
            break
    # last time the lever is off the key before release (settling of the bottom bounce)
    off = np.where(gaps[:i_rel] > 0.02)[0]
    t_lever_settled = float(ts[off[-1]] - ts[i_b]) if len(off) else 0.0
    ph_max = X[2][:i_rel].max()
    zb_m, zr_m = magnet_z(A, A.th_max), magnet_z(A, 0.0)
    t40 = next((t - t_rel for t, th in zip(ts, X[0]) if t > t_rel and (magnet_z(A, th) - zb_m) / (zr_m - zb_m) >= 0.4), None)
    tfull = next((t - t_rel for t, th in zip(ts, X[0]) if t > t_rel and th <= 0.0), None)
    top_max = max(p[1][1] for p in body_pts(A.L, A.LP, ph_max))
    return dict(reached=True, v_key=v_key, t_down=float(ts[i_b]), v_bottom=float(vf[i_b]), max_sep=float(gaps[:i_rel].max()),
                lever_top_z_max=float(top_max),
                land_v=float(land_v), t_lever_settled=t_lever_settled,
                lever_over_mm=float((ph_max - A.ph_bot) * A.r_tab), tab_felt_peak_N=float(max(fut)),
                front_felt_peak_N=float(max(fdn)), guard_peak_N=float(max(fgd)),
                t40_after_release=t40, tfull_after_release=tfull, RKz_min=float(min(RKz)), RKz_max=float(max(RKz)))


def repetition_test(A, v_key=0.5, n=12, k_f=5.0, zeta_f=0.7):
    """fastest repeated notes with firmware re-trigger at 40 % rise: press (velocity-driven) to the bottom,
    lift the finger at once, press again as soon as the magnet has risen 40 % of its travel."""
    S = Sim(A)
    m_eff = A.statics(0.0)["m_eff"]
    c_f = 2 * zeta_f * math.sqrt(k_f * m_eff)
    zb_m, zr_m = magnet_z(A, A.th_max), magnet_z(A, 0.0)
    zb = rot(A.fp, P["KP"], A.th_max)[1]
    x = [A.th_max, 0.0, A.ph_bot, 0.0]
    t = 0.0
    notes = []
    for k in range(n):
        # release until 40 % rise
        S.finger = lambda tt: 0.0
        ev = lambda tt, xx: (magnet_z(A, xx[0]) - zb_m) / (zr_m - zb_m) - 0.40
        ev.terminal, ev.direction = True, 1
        sol = solve_ivp(S.rhs, (t, t + 200.0), x, method="LSODA", max_step=0.01, rtol=1e-8, atol=1e-10, events=ev)
        t, x = sol.t[-1], list(sol.y[:, -1])
        # press from here at v_key
        z_start, t_start = rot(A.fp, P["KP"], x[0])[1], t

        def fin(tt, xx):
            zt = max(z_start - v_key * (tt - t_start), zb - 1.5)
            vt = -v_key if zt > zb - 1.5 else 0.0
            Fp = rot(A.fp, P["KP"], xx[0])
            return max(0.0, k_f * (Fp[1] - zt) + c_f * (perp_vel(Fp, P["KP"], xx[1])[1] - vt))

        def rhs(tt, xx):
            S.finger = lambda _t: fin(tt, xx)
            return S.rhs(tt, xx)
        ev2 = lambda tt, xx: xx[0] - A.th_max
        ev2.terminal, ev2.direction = True, 1
        sol = solve_ivp(rhs, (t, t + 200.0), x, method="LSODA", max_step=0.01, rtol=1e-8, atol=1e-10, events=ev2)
        t, x = sol.t[-1], list(sol.y[:, -1])
        notes.append(t)
    iv = np.diff(notes)
    return dict(v_key=v_key, intervals=[float(v) for v in iv], rate_hz=float(1000.0 / iv[2:].mean()))


def coords(A):
    """world (y, z) of the key-action reference points at rest and at the bottom."""
    KP, LP = P["KP"], A.LP
    rows = []

    def add(name, p_key=None, p_lev=None, fixed=None):
        if fixed is not None:
            rows.append((name, fixed, fixed))
        elif p_key is not None:
            rows.append((name, rot(p_key, KP, 0.0), rot(p_key, KP, A.th_max)))
        else:
            rows.append((name, rot(p_lev, LP, A.ph_rest), rot(p_lev, LP, A.ph_bot)))
    top = V3["black_top"] if A.black else V3["white_top"]
    front = (V3["black_front_top"], top) if A.black else (0.0, top)
    add("key pivot rod centre (KP, Ø3)", fixed=KP)
    add("lever pivot rod centre (LP, Ø3)", fixed=LP)
    add("key front top edge (dip point)", p_key=front)
    add("finger point (top)", p_key=A.fp)
    yu = sum(V3["upstop_b"] if A.black else V3["upstop_w"]) / 2
    yd = sum(V3["downplate_b"] if A.black else V3["downplate_w"]) / 2
    add("up-stop contact (crossbar top / hook felt)", p_key=(yu, V3["crossbar_top"]))
    add("down-stop contact (plate underside / front felt)", p_key=(yd, V3["key_bot"]))
    add("magnet face centre", p_key=((V3["mag_y_b"] if A.black else V3["mag_y_w"]), V3["mag_face_z"]))
    add("key pad surface at nose (coupling)", p_key=(A.yc, A.zpad))
    r_tip = P["r_tip_b"] if A.black else P["r_tip_w"]
    add("lever nose centre (R2)", p_lev=(P["yL"] - r_tip, LEVER_ZL + P["nose_dz"]))
    add("key centre of mass", p_key=A.kp["com"])
    add("lever centre of mass", p_lev=A.lp["com"])
    add("steel centroid", p_lev=A.steel_com_ref)
    ty = sum(P["tab_y"]) / 2
    add("lever tab top (upper felt side)", p_lev=(ty, A.tab_z + 2.0))
    add("lever tab bottom (guard felt side)", p_lev=(ty, A.tab_z - 2.0))
    return rows


def black_front_clear(Ab):
    """black key front face at full dip vs the (resting) white head notch face with its v3 lower chamfer."""
    face_b = [(51.5, 23.5), (51.5, 33.5), (51.5, 43.5), (52.0, 49.5), (52.5, 55.5)]
    ch = P["notch_chamfer"]                                    # white notch face: y50 above z40.9, chamfered below

    def notch_y(z):
        if z > 43.5:
            return None
        if z >= 40.9:
            return 50.0
        return 50.0 - ch + (z - 23.5) / (40.9 - 23.5) * ch
    c = 1e9
    for i in range(len(face_b) - 1):
        for s in np.linspace(0, 1, 21):
            p = (face_b[i][0] + (face_b[i + 1][0] - face_b[i][0]) * s, face_b[i][1] + (face_b[i + 1][1] - face_b[i][1]) * s)
            q = rot(p, P["KP"], Ab.th_max)
            ny = notch_y(q[1])
            if ny is not None:
                c = min(c, q[0] - ny)
    return c


FRAME_DELTA = [  # per octave module, mm^3 and print fill (walls + infill), + added / - removed vs v3 frame
    ("fin plates (13 x 1.2 x 13 x 33, y147-160, lever-rod J-slots)", +13 * 1.2 * 13.0 * 33.0, 1.0),
    ("rear comb block y200-209 x 163.5 x z5-48 minus 12 hook slots + 12 tab pockets",
     +(9.0 * 163.5 * 43.0 - 12 * 3.8 * 8.5 * 11.0 - 12 * 3.8 * 3.7 * 29.0), 0.45),
    ("v3 spine rail y196-209 (removed)", -(13.0 * 163.5 * 15.7), 0.50),
    ("v3 rear second-floor stop rail y138-144 (removed)", -(6.0 * 163.5 * 15.0), 0.50),
]
V3_MODULE = dict(white_comb=175.0, black_comb=92.0, frame=175.0, cover=44.0, sensor_bar=16.0)   # g (v3 C20 / §11)
V3_TOTAL_KG, V3_TOTAL_H = 5.00, 332.0


def report():
    global LAY_TH_B
    LAY_TH_B = LAY["th_b"]
    out = []
    pr = out.append
    pr("Toccata v4 — concept F1: over-tail counter-lever (오버테일 카운터레버).  All values computed by calc.py.")
    pr("Units: mm, g (gf for forces), ms.  z = 0 desk, y = 0 white-key lip.")
    pr("")
    pr("== layout")
    pr(f"  key pivot rod KP = {P['KP']}  (Ø{P['rod_d']} steel, one per octave, rear comb)   lever rod LP = ({P['yL']}, {LEVER_ZL:.2f})")
    pr(f"  dip angle white {math.degrees(LAY['th_w']):.3f}°  black {math.degrees(LAY['th_b']):.3f}°")
    pr(f"  nose contact y: white {LAY['yc_w']:.1f} (pad z {LAY['zpad_w']:.2f}), black {LAY['yc_b']:.1f} (pad z {LAY['zpad_b']:.2f})")
    pr(f"  pad vertical travel at the nose: white {LAY['s_w']:.2f}, black {LAY['s_b']:.2f}")
    acts = {}
    for blk in (False, True):
        tgt = P["B_target_b"] if blk else P["B_target_w"]
        Ls, Lraw = solve_steel(blk, tgt, P["steel_dz"])
        acts[blk] = Action(blk, Ls, P["steel_dz"])
    W, Bk = acts[False], acts[True]
    res = dict()
    for A in (W, Bk):
        nm = "BLACK" if A.black else "WHITE"
        pr("")
        pr(f"== {nm} key + lever")
        pr(f"  key mass {A.kp['m']:.2f} g (PETG {A.kp['m_petg']:.2f}), COM {tuple(round(v, 2) for v in A.kp['com'])}, "
           f"I_KP {A.kp['I_piv']:.0f} g·mm²  (I_com {A.kp['I_com']:.0f} + m·d² parallel-axis)")
        pr(f"  lever mass {A.lp['m']:.2f} g = steel 9x25x{A.steel_len:.1f} {A.lp['m_steel']:.2f} g + PETG {A.lp['m_petg']:.2f} g, "
           f"COM {tuple(round(v, 2) for v in A.lp['com'])} (ref pose), I_LP {A.lp['I_piv']:.0f} g·mm²")
        pr(f"  lever angle rest {math.degrees(A.ph_rest):.2f}°, bottom {math.degrees(A.ph_bot):.2f}° (sweep {math.degrees(A.ph_bot - A.ph_rest):.2f}°)")
        pr("  box table (key):")
        for tag, mi, yc, zc, Iown in A.kp["rows"]:
            pr(f"     {tag:34s} {mi:7.3f} g  at ({yc:7.2f},{zc:6.2f})")
        pr("  box table (lever, reference pose):")
        for tag, mi, yc, zc, Iown in A.lp["rows"]:
            pr(f"     {tag:34s} {mi:7.3f} g  at ({yc:7.2f},{zc:6.2f})")
        pr("  statics over the stroke (finger at y%.1f):" % A.fp[0])
        pr("     key°    lever°   B(g)  fric(g)  DW(g)  UW(g)  m_eff(g) [key/lever]  R(steel/finger)  nose F(N)  keyrod Rz(N)")
        prof = A.balance_profile(11)
        for s in prof:
            pr(f"   {math.degrees(s['th']):6.3f} {math.degrees(s['ph']):8.3f} {s['B']:6.2f} {s['F_fric']:7.2f} {s['B'] + s['F_fric']:6.2f} "
               f"{s['B'] - s['F_fric']:6.2f} {s['m_eff']:8.1f} [{s['m_eff_key']:.1f}/{s['m_eff_lever']:.1f}] {s['R']:8.3f} "
               f"{s['fn']:9.3f} {s['RK'][1]:9.3f}")
        s0, sm, sb = prof[0], prof[5], prof[-1]
        pr("  friction breakdown at rest / mid / bottom (g at the finger): " + " | ".join(
            ", ".join(f"{k} {v:.2f}" for k, v in s["fric"].items()) for s in (s0, sm, sb)))
        lip = (V3["black_front_top"], V3["black_top"]) if A.black else (0.0, V3["white_top"])
        sl = A.statics(0.0, pt=lip)
        pr(f"  at the {'black front edge y52.5' if A.black else 'lip y0'}: B {sl['B']:.2f} g (m_eff {sl['m_eff']:.1f} g)")
        y90 = A.statics(0.0, pt=(90.0, V3["black_top"] if A.black else V3["white_top"]))
        ratio = y90["B"] / s0["B"]
        pr(f"  front/back ratio: force at y90 / force at y{A.fp[0]:.1f} = {ratio:.3f}  (B at y90 {y90['B']:.2f} g)")
        mg = magnet(A)
        pr(f"  magnet: rest gap {mg['rest_gap']:.2f}, bottom gap {mg['bottom_gap']:.2f}, travel {mg['travel']:.2f}, "
           f"y shift {mg['y_shift']:.2f} (face centre at bottom y {mg['y_bottom']:.2f}, element row y67)")
        ch = checks(A)
        pr("  clearances (mm): " + ", ".join(f"{k} {float(v):.2f}" for k, v in ch.items()))
        st = stresses(A)
        pr("  constant stresses at rest (MPa): keel " + ", ".join(f"y{y:.0f} {v:.2f}" for y, v in st["keel"]) +
           f"; lever hub {st['lever_hub']:.2f}; nose arm {st['lever_nose_arm']:.2f}; up-stop hook lip {st['upstop_hook_lip']:.2f} "
           f"(F_up {st['upstop_force_N']:.3f} N); rear hook jaw {st['hook_jaw']:.2f}; key crossbar {st['key_crossbar']:.2f}; skin/bridge at pad {st['key_skin_at_pad']:.2f}; "
           f"bearing: key hook {st['key_hook_bearing']:.3f}, lever hub {st['lever_hub_bearing']:.3f}, fin notch {st['fin_notch_bearing']:.3f}")
        rt = return_test(A)
        rs = return_test(A, spring_gf=6.0)
        pr(f"  RETURN from the bottom (finger lifted, lever at rest on the key): re-trigger point = magnet back 40 % of its travel")
        pr(f"     no spring : t40 {rt['t40']:.1f} ms -> {rt['rate40']:.1f} Hz, t90 {rt['t90']:.1f}, full (first up-stop contact) {rt['tfull']:.1f} ms, "
           f"bounce {rt['bounce']:.2f} mm at the finger, settled (<0.2 mm) at {rt['t_settle']:.0f} ms, "
           f"nose force min {rt['fn_min_during_return']:.3f} N (separation {rt['sep_during_return']}), key-rod Rz range {rt['RKz_min']:.2f}..{rt['RKz_max']:.3f} N")
        pr(f"     +6 gf assist spring (option, not in the BOM): t40 {rs['t40']:.1f} ms ({rs['rate40']:.1f} Hz), full {rs['tfull']:.1f} ms")
        a_est = (sm["B"] - sm["F_fric"]) * GF / sm["m_eff"]
        pr(f"     check of the v2.0 claim: constant-acceleration estimate t = sqrt(2*dip*m_eff/((B-fric)*g)) = "
           f"{math.sqrt(2 * 10.0 / a_est):.1f} ms full / {math.sqrt(2 * 4.0 / a_est):.1f} ms to 40 % — it depends on m_eff/(B-fric), "
           f"not a fixed 40 ms; the 40 % re-trigger point, not full return, sets the repetition limit")
        pr("  KEYSTROKES (finger target moving down at v, press-in 1.5 mm, hold 60 ms after bottom, then lift):")
        strikes = {}
        for v in (0.1, 0.3, 0.6, 1.0):
            r = strike_test(A, v)
            strikes[v] = r
            pr(f"     v {v:.1f} m/s: bottom at {r['t_down']:.1f} ms, key speed at bottom {r['v_bottom']:.2f} m/s, lever lift-off {r['max_sep']:.3f} mm, "
               f"nose lands at {r['land_v']:.3f} m/s, lever settled {r['t_lever_settled']:.1f} ms after bottom, tab overtravel {r['lever_over_mm']:.2f} mm "
               f"(upper felt peak {r['tab_felt_peak_N']:.1f} N, lever top z {r['lever_top_z_max']:.2f}), front felt peak {r['front_felt_peak_N']:.1f} N, rest-guard peak {r['guard_peak_N']:.2f} N, "
               f"after release t40 {r['t40_after_release']:.1f} / full {r['tfull_after_release']:.1f} ms, key-rod Rz {r['RKz_min']:.1f}..{r['RKz_max']:.2f} N")
        rp = repetition_test(A, 0.5, n=10)
        pr(f"  REPETITION (press 0.5 m/s, lift at bottom, re-press at the 40 % point): steady interval {1000.0 / rp['rate_hz']:.1f} ms = {rp['rate_hz']:.1f} Hz")
        pr("  coordinates (y, z) rest -> bottom:")
        for n, a, b in coords(A):
            pr(f"     {n:48s} ({a[0]:7.2f},{a[1]:6.2f}) -> ({b[0]:7.2f},{b[1]:6.2f})")
        res[A.black] = dict(A=A, prof=prof, lip=sl, ratio=ratio, mg=mg, ch=ch, st=st, rt=rt, rs=rs, strikes=strikes, rp=rp)
    # ---- whole-instrument numbers
    pr("")
    pr("== envelope")
    top_moving = max(res[b]["ch"]["lever_top_z_over"] for b in (False, True))
    top_ff = max(res[b]["strikes"][1.0]["lever_top_z_max"] for b in (False, True))
    pr(f"  white key top z {V3['white_top']}, black top z {V3['black_top']}; highest moving point: lever at nominal overtravel z {top_moving:.2f}, "
       f"at the 1.0 m/s keystroke z {top_ff:.2f}; cover underside z {P['cover_under']} (top plate thinned to 1.5 over y150-200, cover top z59 unchanged)")
    res["top_ff"] = top_ff
    low = min(min(rot(p, P['KP'], res[b]['A'].th_max)[1] for bx in res[b]['A'].K.boxes if bx[0].startswith('keel') for p in box_corners(bx)) for b in (False, True))
    pr(f"  lowest moving point (keel at full dip) z {low:.2f} (floor z {V3['floor_top']})")
    pr(f"  depth used: key y0 -> rear hook y{P['KP'][0] + 3.5:.1f}; rear comb y{P['tooth'][0]}-{P['tooth'][1]}; frame y0-{V3['frame_depth']:.0f} (v3, unchanged); "
       f"total instrument depth {V3['frame_depth'] + 3 + 195:.0f}")
    pr(f"  black-key front face at full dip vs resting white notch face (lower chamfer {P['notch_chamfer']} mm, v3 had 1.5): "
       f"min clearance {black_front_clear(Bk):.2f} mm")
    pr("  x layout (lever columns between 1.2 mm fin plates; carrier = 9 steel + 1.5 side plate = 10.5):")
    for r in x_layout():
        pr(f"     {r['key']:3s} x {r['x']:7.3f}  fins {r['fin_l']:7.2f} | {r['fin_r']:7.2f}  column {r['column']:5.2f}  side clearance {r['side_clear']:.2f}")
    # ---- masses, filament, prints
    wg, bg = W.lp["m_steel"], Bk.lp["m_steel"]
    steel_oct = 7 * wg + 5 * bg
    n_w, n_b = 52, 36
    steel_88 = n_w * wg + n_b * bg
    key_p = dict(w=W.kp["m_petg"], b=Bk.kp["m_petg"])
    lev_p = dict(w=W.lp["m_petg"], b=Bk.lp["m_petg"])
    support = dict(w=1.5, b=2.0)      # designed breakaway rib under the keel when printed upside-down (g, estimate from 0.8x3x~50 wall)
    frame_d = sum(v * f * RHO_PETG for _, v, f in FRAME_DELTA)
    oct_act = 7 * (key_p["w"] + lev_p["w"] + support["w"]) + 5 * (key_p["b"] + lev_p["b"] + support["b"])
    act_88 = n_w * (key_p["w"] + lev_p["w"] + support["w"]) + n_b * (key_p["b"] + lev_p["b"] + support["b"])
    v3_keys_oct = V3_MODULE["white_comb"] + V3_MODULE["black_comb"]
    total_88 = V3_TOTAL_KG * 1000 - v3_keys_oct * 88 / 12 + act_88 + frame_d * 7.33
    pr("")
    pr("== masses / filament / printing")
    pr(f"  steel per key: white {wg:.1f} g (9x25x{W.steel_len:.1f}), black {bg:.1f} g (9x25x{Bk.steel_len:.1f}); per octave {steel_oct:.0f} g; 88 keys {steel_88 / 1000:.2f} kg "
       f"(bar length {(n_w * W.steel_len + n_b * Bk.steel_len) / 1000:.2f} m + kerf)")
    pr(f"  PETG per key: white key {key_p['w']:.1f} + lever {lev_p['w']:.1f} + breakaway rib {support['w']:.1f} g; black key {key_p['b']:.1f} + lever {lev_p['b']:.1f} + rib {support['b']:.1f} g")
    for nm, v, f in FRAME_DELTA:
        pr(f"  frame change: {nm}: {v * f * RHO_PETG:+.1f} g")
    pr(f"  per octave: action parts {oct_act:.0f} g (v3 key combs {v3_keys_oct:.0f} g), frame delta {frame_d:+.1f} g; "
       f"module total {oct_act + V3_MODULE['frame'] + frame_d + V3_MODULE['cover'] + V3_MODULE['sensor_bar']:.0f} g "
       f"(v3 {sum(V3_MODULE.values()):.0f} g)")
    pr(f"  88 keys: action parts {act_88 / 1000:.2f} kg = {act_88 / 15:.0f} h at 15 g/h; whole instrument filament {total_88 / 1000:.2f} kg "
       f"(v3 {V3_TOTAL_KG:.2f}) = {total_88 / 15:.0f} h at 15 g/h (v3 figure {V3_TOTAL_H:.0f} h incl. its own overheads)")
    Lw = P['KP'][0] + 3.5
    pr(f"  bed 220x220: 7 white keys side by side {7 * 22.5 + 6 * 2:.1f} x {Lw:.1f} (upside down, height 43.5-{low:.0f}); "
       f"5 black keys {5 * 11 + 4 * 3:.0f} x {Lw - 51.5:.1f}; 12 levers flat on their side plate, each {P['tab_y'][1] - (P['yL'] - P['r_tip_b'] - 2):.1f} x ~31; all fit.")
    bar_m = (n_w * (W.steel_len + 1.5) + n_b * (Bk.steel_len + 1.5)) / 1000
    rod_m = 7 * 2 * 0.1635 + 2 * (0.047 + 0.0395)
    cost = [  # (item, spec, qty_88, unit KRW, total KRW, source)
        ("steel flat bar 평철 SS400 9T x 25", f"cut pieces: {n_w} x {W.steel_len:.1f} mm (white) + {n_b} x {Bk.steel_len:.1f} mm (black) = {bar_m:.2f} m incl. 1.5 mm kerf",
         math.ceil(bar_m), 4500, math.ceil(bar_m) * 4500, "online 평철 cut-to-length shop (1 m lots) — estimate"),
        ("cutting service for the steel pieces", "88 cuts (or DIY hacksaw ~3 h -> 0 KRW)", 88, 300, 88 * 300, "estimate"),
        ("SUS304 polished round bar Ø3 x 1 m", f"key rods + lever rods: {rod_m:.2f} m -> 3 bars", 3, 9600, 3 * 9600,
         "baegwan.net 스텐연마봉 SUS304 1M Φ3 (9,600 KRW, checked 2026-09-27)"),
        ("USB-C extension 15 cm (M-F, low-profile)", "relocated control board -> rear wall, one per module", 7, 3500, 7 * 3500, "estimate"),
        ("removed: v3 leaf-spine clamp hardware", "per module 4x M3x40, 4x M3x10 set screw, 4x brass disc Ø8x1, 4x M4 washer, 8x M3 nut", 7, -2500, -7 * 2500, "estimate"),
    ]
    consumable = [("wool felt 3T + bushing cloth 0.6T extra", "24 tab pads 5x8 + 12 nose pads 8x4 per octave", 1, 5000, 5000, "estimate")]
    pr("")
    pr("== purchased items (delta vs v3 base BOM)")
    tot = 0
    for it in cost:
        pr(f"  {it[0]:42s} {it[1]:92s} qty {it[2]:3d}  unit {it[3]:6d}  total {it[4]:7d} KRW  [{it[5]}]")
        tot += it[4]
    pr(f"  base BOM delta: {tot:+d} KRW  (v3.2 base 583,219 -> {583219 + tot:,d}, cap 1,000,000)")
    for it in consumable:
        pr(f"  consumable: {it[0]} ({it[1]}): {it[4]} KRW [{it[5]}]")
    res["cost"], res["cost_delta"], res["consumable"] = cost, tot, consumable
    res["steel_oct"], res["steel_88"], res["act_88"], res["total_88"], res["frame_d"] = steel_oct, steel_88, act_88, total_88, frame_d
    res["top_moving"], res["low"] = top_moving, low
    res["black_front"] = black_front_clear(Bk)
    return out, res


if __name__ == "__main__":
    lines, R = report()
    print("\n".join(lines))
