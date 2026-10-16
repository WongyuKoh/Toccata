"""Toccata v4 concept K1 - rear-pivot key + steel compression spring + encapsulated steel inertia mass.

One lever per key. The key pivots on a steel shaft (one Ø3 SUS304 rod per octave) at its rear,
a steel compression spring standing on the frame floor pushes the key up from inside its hollow tail,
and steel mass encapsulated in the key front (print-pause insert) gives inertia.  The spring preload
carries the key's own gravity moment + the steel's gravity moment + the balance weight, so the
downweight stays ~50 g while the inertia is chosen freely.

Units: mm, g, N, ms (SI inside the ODE: N, mm, g -> converted explicitly).
Coordinates: z = 0 desk, y = 0 white-key front lip, +y away from the player, x across.
Angle theta > 0 = key pressed (front down).  Torques: + = pushes the front down.

Run: python3 calc.py  (prints every metric of brief section 6; results.txt is its output)
"""
import math

G = 9.80665e-3            # N per gram-force
RHO_PETG = 1.25           # g/cm3 (brief)
RHO_STEEL = 7.85
RHO_NDFEB = 7.5
E_PETG = 1950.0           # MPa (Bambu PETG Basic)
G_WIRE = 78500.0          # MPa, music wire SWP-A shear modulus
E_WIRE = 206000.0

# ---------------------------------------------------------------- v3 interfaces (kept)
Z_DESK, Z_FLOOR = 0.0, 5.0          # EVA 0-3, frame floor 3-5
W_TOP, KEY_BOT = 43.5, 23.5         # white top / key underside (white and black)
B_TOP = 55.5                        # black top
SKIN_W, SKIN_B, WALL = 2.6, 2.0, 1.2
Y_BFRONT = 52.5                     # black top front edge (dip reference), black body front y51.5
DIP_W, DIP_B = 10.0, 9.5            # at y0 (white top lip) / y52.5 (black top front edge)
Y_SENS = 67.0                       # sensor element row
Z_ELEM_W, Z_ELEM_B = 12.68, 10.15   # DRV5055A2 element z (white / black pockets)
Z_BAR_TOP_W, Z_BAR_TOP_B = 13.6, 11.5
BAR_Y = (59.0, 77.5)                # sensor bar y range
Y_MAG_W, Y_MAG_B = 65.8, 64.2       # magnet centre y (v3)
MAG_D, MAG_T = 5.0, 2.0             # N35 disc
BR_N35 = 1.18                       # T remanence
GAP_BOT_W_V3, GAP_BOT_B_V3 = 4.7, 4.9   # v3 bottom gaps -> keep field range at the Hall element
FRAME_DEPTH = 212.0
BOARD = dict(x=(47.25, 117.25), y=(145.5, 195.5), z_top_parts=20.0)   # v3 control board, kept
COVER_FASCIA_Z = 44.5               # v3 rear-cover fascia lower edge
COVER_TOP_Z = 59.0

# ---------------------------------------------------------------- K1 decisions
PIV = (200.0, 33.5)                 # shaft axis (y, z); fins y196-204 clear the board (ends y195.5)
SHAFT_D, RING_OD, RING_W = 5.0, 11.0, 6.0     # S45C Ø5 ground bar (magnetic); key end = open fork (slot 5.05) + retention magnet
MAG_RET_N = 2.0                     # N, pull of the Ø5x2 N35 in the fork end on the shaft (estimate -> stage-0 test)
Y_S = 138.0                         # spring axis y (front of the control board, behind the sensor bar)
Z_SEAT_LO = Z_FLOOR                 # spring lower end on the frame floor, around a printed guide post
Z_SEAT_W = W_TOP - SKIN_W           # white: spring pushes directly on the skin underside (40.9)
Y_FINGER_W, Y_FINGER_B = 13.0, 62.5 # where DW/UW are quoted (white / black), as in v3
Y_UP_W, Y_UP_B = 43.25, 105.0       # up-stop crossbar centre (white: behind the steel bar; black: behind its steel bar)
Y_GUIDE_W, Y_GUIDE_B = 48.0, 111.5  # guide tab (felt-bushed) centre, directly behind each hook finger
FELT_T = 3.0

# friction assumptions (explicit)
MU_PIVOT = 0.25                     # steel shaft in printed PETG fork, dry (0.15 with PTFE grease)
F_GUIDE = 2.0                       # gf drag at the felt-bushed guide tab (0.05 mm/side clearance, no preload)
F_SPRING_RUB = 0.3                  # gf, coil touching its printed guide post
FRIC_SENS = (1.0, 3.0)              # sensitivity multipliers reported


def rot(p, c, a):
    """rotate point p=(y,z) about c by angle a (a>0: front (small y) goes DOWN)."""
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def solve_theta(pt, dip):
    """angle at which point pt drops by `dip` (exact rotation about PIV)."""
    lo, hi = 0.0, 0.3
    for _ in range(80):
        m = (lo + hi) / 2
        if pt[1] - rot(pt, PIV, m)[1] < dip:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


# ---------------------------------------------------------------- bodies (box model)
class Box:
    """rectangular block in (y,z) with width w along x; fill = solid fraction (holes, infill)."""
    def __init__(s, name, y0, y1, z0, z1, w, rho=RHO_PETG, fill=1.0):
        s.name, s.y0, s.y1, s.z0, s.z1, s.w, s.rho, s.fill = name, y0, y1, z0, z1, w, rho, fill

    @property
    def m(s):
        return (s.y1 - s.y0) * (s.z1 - s.z0) * s.w * s.fill * s.rho / 1000.0

    @property
    def c(s):
        return ((s.y0 + s.y1) / 2, (s.z0 + s.z1) / 2)

    @property
    def Ic(s):   # about its own centroid, axis along x
        return s.m * ((s.y1 - s.y0) ** 2 + (s.z1 - s.z0) ** 2) / 12.0


class Cyl(Box):
    """vertical cylinder (axis z) of diameter d: stored as an equivalent box (same mass, y-extent d)."""
    def __init__(s, name, yc, z0, z1, d, rho=RHO_PETG, fill=1.0):
        Box.__init__(s, name, yc - d / 2, yc + d / 2, z0, z1, d, rho, fill * math.pi / 4)


class Ball:
    def __init__(s, name, yc, zc, d, rho=RHO_STEEL):
        s.name, s.d = name, d
        s.m = math.pi / 6 * d ** 3 * rho / 1000.0
        s.c = (yc, zc)
        s.Ic = 0.1 * s.m * d ** 2      # 2/5 m r^2


def white_key(mass):
    """representative white key = D (widest tail 14.362). mass = dict(kind, ...) for the steel insert."""
    tw = 14.362
    zs = W_TOP - SKIN_W                       # 40.9 skin underside
    B = [
        Box("top skin head y0-50", 0, 50, zs, W_TOP, 22.5),
        Box("top skin tail y50-146", 50, 146, zs, W_TOP, tw),
        Box("side walls head", 1.5, 50, KEY_BOT, zs, 2 * WALL),
        Box("front wall", 1.5, 2.7, KEY_BOT, zs, 22.5 - 2 * WALL),
        Box("head->tail step walls", 48.8, 50, KEY_BOT, zs, 22.5 - tw),
        Box("side walls tail (end y144, clear of the board)", 50, 144, KEY_BOT, zs, 2 * WALL),
        Box("insert cavity floor (down-stop pad)", 2.7, 38.5, KEY_BOT, KEY_BOT + 1.0, 22.5 - 2 * WALL),
        Box("insert cavity rear wall", 38.5, 39.5, KEY_BOT, zs, 22.5 - 2 * WALL),
        Box("guide ribs x2 (slot 8.6)", 40.0, 50.5, KEY_BOT, zs, 2 * WALL),
        Box("up-stop crossbar", Y_UP_W - 1.75, Y_UP_W + 1.75, KEY_BOT, KEY_BOT + 1.6, 8.6),
        Box("transverse ribs x3 (y90,112,160)", 100 - 1.8, 100 + 1.8, KEY_BOT + 6, zs, tw - 2 * WALL),
        Cyl("magnet boss", Y_MAG_W, KEY_BOT, zs, 7.6, fill=0.85),
        Cyl("spring seat boss + centring spigot", Y_S, zs - 3.0, zs, 9.0, fill=0.75),
        Box("rear arm skin y146-196", 146, 196, W_TOP - 2.0, W_TOP, 10.0),
        Box("tail end wall y142.8-144", 142.8, 144, 29.5, zs, tw - 2 * WALL),
        Box("rear arm walls y144-196", 144, 196, 29.5, W_TOP - 2.0, 2 * WALL),
        Box("fork web y190-194", 190, 194, 29.0, W_TOP - 2.0, RING_W, fill=0.8),
        Box("pivot fork (slot 5.05 open to the rear) y194-204 z28-39", 194.0, 204.0, 28.0, 39.0, RING_W, fill=0.62),
        Box("retention magnet Ø5x2 in fork end", 194.8, 196.8, 31.0, 36.0, 5.0, rho=RHO_NDFEB, fill=math.pi / 4),
        Box("magnet N35 Ø5x2", Y_MAG_W - 2.5, Y_MAG_W + 2.5, KEY_BOT, KEY_BOT + 2, 5.0, rho=RHO_NDFEB, fill=math.pi / 4),
    ]
    B += steel_insert("W", mass)
    return B


def black_key(mass):
    """representative black key (C#): base 11 wide to z43.5, top 9.5 at z55.5, body y51.5-146, rear arm to the shaft."""
    zs = B_TOP - SKIN_B
    B = [
        Box("top skin y52.5-146", 52.5, 146, zs, B_TOP, 9.75),
        Box("side walls y51.5-144", 51.5, 144, KEY_BOT, zs, 2 * WALL),
        Box("front wall", 51.5, 52.7, KEY_BOT, zs, 11 - 2 * WALL),
        Box("rear wall y142.8-144", 142.8, 144, 29.5, zs, 11 - 2 * WALL),
        Box("body top y144-146 (above the arm)", 144, 146, 43.5, zs, 2 * WALL),
        Box("insert pocket floor", 52.7, 101.0, 32.0, 33.0, 11 - 2 * WALL),
        Box("up-stop crossbar", Y_UP_B - 1.75, Y_UP_B + 1.75, KEY_BOT, KEY_BOT + 1.6, 11 - 2 * WALL),
        Box("transverse rib y125", 125 - 0.6, 125 + 0.6, KEY_BOT + 6, zs, 11 - 2 * WALL),
        Cyl("magnet boss", Y_MAG_B, KEY_BOT, KEY_BOT + 8, 7.6, fill=0.85),
        Cyl("spring seat boss (lower plate)", Y_S, 38.0, 41.0, 8.6, fill=0.75),
        Box("rear arm skin y146-196", 146, 196, W_TOP - 2.0, W_TOP, 9.0),
        Box("rear arm walls y144-196", 144, 196, 29.5, W_TOP - 2.0, 2 * WALL),
        Box("fork web y190-194", 190, 194, 29.0, W_TOP - 2.0, RING_W, fill=0.8),
        Box("pivot fork (slot 5.05 open to the rear) y194-204 z28-39", 194.0, 204.0, 28.0, 39.0, RING_W, fill=0.62),
        Box("retention magnet Ø5x2 in fork end", 194.8, 196.8, 31.0, 36.0, 5.0, rho=RHO_NDFEB, fill=math.pi / 4),
        Box("magnet N35 Ø5x2", Y_MAG_B - 2.5, Y_MAG_B + 2.5, KEY_BOT, KEY_BOT + 2, 5.0, rho=RHO_NDFEB, fill=math.pi / 4),
    ]
    B += steel_insert("B", mass)
    return B


def steel_insert(which, mass):
    """steel inertia mass, encapsulated during a print pause.
    white: 'balls' = n x 5/8" (15.875) carbon-steel balls in a row, centres from y10.84, pitch 15.875, z32.44
           'bar'   = 16x16 square bar, y4..4+L, z24.5..40.5
    black: 'flat'  = 6x19 flat bar on edge, y53..53+L, z33..52 (>= 7.5 mm above the magnet top)."""
    k = mass.get(which)
    if not k or k[1] == 0:
        return []
    if k[0] == "balls":
        d = 15.875
        return [Ball("steel ball 5/8in #%d" % (i + 1), 2.7 + 0.2 + d / 2 + i * d, KEY_BOT + 1.0 + d / 2, d)
                for i in range(k[1])]
    if k[0] == "bar":
        return [Box("steel square bar 16x16xL", 4.0, 4.0 + k[1], KEY_BOT + 1.0, KEY_BOT + 17.0, 16.0, rho=RHO_STEEL)]
    if k[0] == "flat":
        return [Box("steel flat bar 6x19xL", 53.0, 53.0 + k[1], 33.0, 52.0, 6.0, rho=RHO_STEEL)]
    if k[0] == "flat2":    # white: two 6x19 flat bars laid flat and stacked (19 wide x 12 tall), y4..4+L
        return [Box("steel flat bar 19x6xL (2 layers)", 4.0, 4.0 + k[1], KEY_BOT + 1.0, KEY_BOT + 13.0, 19.0, rho=RHO_STEEL)]
    if k[0] == "balls516":  # black: n x 5/16in (7.938) balls in a row, y from 57, z37.5
        d = 7.938
        return [Ball("steel ball 5/16in #%d" % (i + 1), 57.0 + i * d, 37.5, d) for i in range(k[1])]
    raise ValueError(k)


def mass_props(B):
    m = sum(b.m for b in B)
    cy = sum(b.m * b.c[0] for b in B) / m
    cz = sum(b.m * b.c[1] for b in B) / m
    I = sum(b.Ic + b.m * ((b.c[0] - PIV[0]) ** 2 + (b.c[1] - PIV[1]) ** 2) for b in B)
    steel = sum(b.m for b in B if "steel" in b.name)
    plastic = sum(b.m for b in B if getattr(b, "rho", None) == RHO_PETG)
    return dict(m=m, c=(cy, cz), I=I, steel=steel, plastic=plastic)


def grav_torque(B, th):
    """N*mm, + = front down."""
    return sum(b.m * G * (PIV[0] - rot(b.c, PIV, th)[0]) for b in B)


# ---------------------------------------------------------------- spring (helical compression, music wire)
def uts_wire(d):
    """SWP-A / ASTM A228 music wire tensile strength, Shigley A=2211 MPa*mm^m, m=0.145."""
    return 2211.0 / d ** 0.145


class Spring:
    def __init__(s, d, OD, n, L0, ends="closed-ground"):
        s.d, s.OD, s.n, s.L0 = d, OD, n, L0
        s.D = OD - d
        s.C = s.D / d
        s.k = G_WIRE * d ** 4 / (8 * s.D ** 3 * n)                 # N/mm
        s.Nt = n + 2
        s.Ls = s.Nt * d                                            # solid length (closed & ground)
        s.Kw = (4 * s.C - 1) / (4 * s.C - 4) + 0.615 / s.C
        s.mass = math.pi * s.D * s.Nt * math.pi / 4 * d ** 2 * RHO_STEEL / 1000.0
        # surge (first longitudinal) frequency, fixed-fixed: f = d/(2 pi n D^2) * sqrt(G/(2 rho)) (SI)
        s.f_surge = (d * 1e-3) / (2 * math.pi * n * (s.D * 1e-3) ** 2) * math.sqrt(G_WIRE * 1e6 / (2 * RHO_STEEL * 1e3))

    def F(s, L):
        return s.k * (s.L0 - L)

    def tau(s, F):
        return s.Kw * 8 * F * s.D / (math.pi * s.d ** 3)


# ---------------------------------------------------------------- felt (high-density wool 3T)
# pressure law P = A * eps^2.5, A fitted to the v3 statement "8x3 hook felt: 4.8 mJ -> ~52 % compression"
FELT_P = 2.5
FELT_A = 4.8 / (24.0 * FELT_T * 0.52 ** (FELT_P + 1) / (FELT_P + 1))    # MPa
FELT_E = 0.4                                                              # coefficient of restitution (assumed)


def felt_force(delta, area):
    if delta <= 0:
        return 0.0
    return FELT_A * area * (delta / FELT_T) ** FELT_P


def felt_delta(F, area):
    return FELT_T * (F / (FELT_A * area)) ** (1 / FELT_P) if F > 0 else 0.0


# ---------------------------------------------------------------- one key = bodies + spring seat + stops
class Key:
    def __init__(s, black, bodies, spring=None, z_seat=None):
        s.black = black
        s.B = bodies
        s.mp = mass_props(bodies)
        s.y_front = Y_BFRONT if black else 0.0
        s.top_front = (Y_BFRONT, B_TOP) if black else (0.0, W_TOP)
        s.y_finger = Y_FINGER_B if black else Y_FINGER_W
        s.y_up = Y_UP_B if black else Y_UP_W
        s.y_guide = Y_GUIDE_B if black else Y_GUIDE_W
        s.up_area = 24.0
        s.dn_area = 82.0 if black else 9.0 * (22.5 - 2 * WALL)
        s.y_dn = 55.1 if black else 7.5
        s.theta_dip = solve_theta(s.top_front, DIP_B if black else DIP_W)
        s.spring = spring
        s.seat = (Y_S, z_seat if z_seat is not None else Z_SEAT_W)
        s.y_mag = Y_MAG_B if black else Y_MAG_W
        s.z_elem = Z_ELEM_B if black else Z_ELEM_W
        s.I_spring = 0.0

    # ---- geometry
    def seat_at(s, th):
        return rot(s.seat, PIV, th)

    def L_spring(s, th):
        return s.seat_at(th)[1] - Z_SEAT_LO

    def arm(s, y, th=0.0, z=None):
        """horizontal lever arm (mm) of a vertical force applied at key point (y, z) at angle th."""
        z = KEY_BOT if z is None else z
        return PIV[0] - rot((y, z), PIV, th)[0]

    # ---- torques (N*mm, + = front down)
    def M_spring(s, th):
        return -s.spring.F(s.L_spring(th)) * (PIV[0] - s.seat_at(th)[0]) if s.spring else 0.0

    def M_grav(s, th):
        return grav_torque(s.B, th)

    def M_net_up(s, th):
        """front-up torque with no friction and no stop contact."""
        return -(s.M_spring(th) + s.M_grav(th))

    def BW(s, th, y=None):
        """balance force (g) at key-top point y needed to hold the key at th (no friction)."""
        y = s.y_finger if y is None else y
        return s.M_net_up(th) / s.arm(y, th, W_TOP) / G

    def R_vert(s, th, F_ext_down):
        """vertical pivot reaction magnitude (N) for a quasi-static state with an extra downward force."""
        Fs = s.spring.F(s.L_spring(th)) if s.spring else 0.0
        return abs(Fs - s.mp["m"] * G - F_ext_down)

    def M_fric(s, th, F_ext_down):
        return (MU_PIVOT * (s.R_vert(th, F_ext_down) + MAG_RET_N) * SHAFT_D / 2
                + F_GUIDE * G * s.arm(s.y_guide, th)
                + F_SPRING_RUB * G * (PIV[0] - s.seat_at(th)[0]))

    def fric_g(s, th, y, F_ext_down, mult=1.0):
        return mult * s.M_fric(th, F_ext_down) / s.arm(y, th, W_TOP) / G

    def DW_UW(s, th, y=None, mult=1.0):
        """(DW, UW) in g at y: weight that just starts the key down / lets it just rise, at angle th."""
        y = s.y_finger if y is None else y
        bw = s.BW(th, y)
        dw = bw
        for _ in range(30):
            dw = bw + s.fric_g(th, y, dw * G, mult)
        uw = bw
        for _ in range(30):
            uw = bw - s.fric_g(th, y, uw * G, mult)
        return dw, uw

    # ---- rest state: up-stop force and felt pre-compression
    def rest(s):
        U_at_stop = s.M_net_up(0.0) / s.arm(s.y_up, 0.0)          # N down on the key at the crossbar
        return U_at_stop, felt_delta(U_at_stop, s.up_area)

    def mag_face_z(s, th, z_face0):
        return rot((s.y_mag, z_face0), PIV, th)[1]


# ---------------------------------------------------------------- spring design (same spring for white and black)
DW_TARGET = 50.0         # g at y13 (white) / y62.5 (black), static start-of-stroke incl. friction
SOLID_MARGIN = 0.85      # max deflection <= 85 % of (L0 - Ls)
TAU_ALLOW = 0.45         # x UTS, static allowable (set removed not needed)
OD_MAX = 6.5             # black interior 8.6 minus a 1.0 cup wall
ID_MIN = 3.6             # printed guide post Ø3.0 + 0.3 radial
L0_MAX = 80.0


def fit_L0(key, sp_proto, target=DW_TARGET):
    """free length that gives DW(start) = target for this key (seat fixed)."""
    lo, hi = key.L_spring(0.0) + 0.01, key.L_spring(0.0) + 200.0
    for _ in range(60):
        mid = (lo + hi) / 2
        key.spring = Spring(sp_proto.d, sp_proto.OD, sp_proto.n, mid)
        if key.DW_UW(0.0)[0] < target:
            lo = mid
        else:
            hi = mid
    key.spring = Spring(sp_proto.d, sp_proto.OD, sp_proto.n, (lo + hi) / 2)
    return key.spring.L0


def fit_seat(key, sp, target=DW_TARGET):
    """seat height (black key, same spring) that gives DW(start) = target."""
    lo, hi = Z_SEAT_LO + sp.Ls, 60.0
    key.spring = sp
    for _ in range(60):
        mid = (lo + hi) / 2
        key.seat = (Y_S, mid)
        if key.DW_UW(0.0)[0] > target:      # higher seat = longer spring = less force
            lo = mid
        else:
            hi = mid
    key.seat = (Y_S, (lo + hi) / 2)
    return key.seat[1]


def spring_ok(key, sp):
    Lb = key.L_spring(key.theta_dip)
    Fb = sp.F(Lb)
    ok = (sp.L0 - Lb) <= SOLID_MARGIN * (sp.L0 - sp.Ls) and sp.tau(Fb) <= TAU_ALLOW * uts_wire(sp.d)
    return ok, Lb, Fb


def choose_spring(wk, bk, verbose=False):
    best, rows = None, []
    for d in (0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8):
        for OD in (5.0, 5.5, 6.0, 6.5):
            if OD > OD_MAX or OD - 2 * d < ID_MIN:
                continue
            for n in range(6, 90):
                proto = Spring(d, OD, n, 50.0)
                L0 = fit_L0(wk, proto)
                sp = wk.spring
                if L0 > L0_MAX:
                    continue
                okw, Lbw, Fbw = spring_ok(wk, sp)
                if not okw:
                    continue
                zb = fit_seat(bk, sp)
                if not (KEY_BOT + 4.0 <= zb <= B_TOP - SKIN_B):
                    continue
                okb, Lbb, Fbb = spring_ok(bk, sp)
                if not okb:
                    continue
                rise_w = wk.BW(wk.theta_dip) - wk.BW(0.0)
                rise_b = bk.BW(bk.theta_dip) - bk.BW(0.0)
                rows.append((rise_w, d, OD, n, L0, zb, rise_b, sp.k, sp.f_surge))
    rows.sort()
    return rows


def apply_spring(wk, bk, d, OD, n):
    fit_L0(wk, Spring(d, OD, n, 50.0))
    sp = wk.spring
    fit_seat(bk, sp)
    return sp


# ---------------------------------------------------------------- separate springs (white / black): the black key
# strokes 1.29x more at the spring and has a 1.36x shorter finger arm, so one common spring makes the
# black force curve 1.75x steeper (checked: common spring -> black rise ~27 g). Two spring specs instead.
Z_SEAT_B = B_TOP - SKIN_B            # 53.5: black spring pushes on its skin underside (longest possible)
L0_MAX_ONE = 85.0
STD_WIRES = (0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7)
STD_OD = (5.0, 5.5, 6.0, 6.5)


def spring_table(key):
    saved = (key.spring, key.seat)
    rows = []
    for d in STD_WIRES:
        for OD in STD_OD:
            if OD > OD_MAX or OD - 2 * d < ID_MIN:
                continue
            for n in range(6, 120):
                L0 = fit_L0(key, Spring(d, OD, n, 50.0))
                sp = key.spring
                if L0 > L0_MAX_ONE:
                    break
                ok, Lb, Fb = spring_ok(key, sp)
                if not ok:
                    continue
                rows.append(dict(rise=key.BW(key.theta_dip) - key.BW(0.0), d=d, OD=OD, n=n, L0=L0, k=sp.k,
                                 tau=sp.tau(Fb), Ls=sp.Ls, f=sp.f_surge, Lr=key.L_spring(0.0), Lb=Lb))
    rows.sort(key=lambda r: r["rise"])
    key.spring, key.seat = saved
    return rows


def pick_spring(key, d=None, OD=None):
    """flattest feasible spring; optionally restricted to one wire/OD (common stock sizes)."""
    rows = [r for r in spring_table(key) if (d is None or r["d"] == d) and (OD is None or r["OD"] == OD)]
    r = rows[0]
    fit_L0(key, Spring(r["d"], r["OD"], r["n"], 50.0))
    return r


# ---------------------------------------------------------------- dynamics (1 DOF, RK4)
W_SMOOTH = 0.02          # rad/s, Coulomb friction smoothing
DT = 4e-6                # s


class Sim:
    def __init__(s, key, fric_mult=1.0, finger_g=0.0, const_force=None):
        s.k = key
        s.fm = fric_mult
        s.Ff = finger_g * G
        s.const = const_force          # if set: replace spring+gravity by this constant front-up torque (N*mm)
        sp = key.spring
        s.I = key.mp["I"] + (sp.mass / 3.0 * (PIV[0] - key.seat[0]) ** 2 if sp else 0.0)
        U, s.dst = key.rest()
        s.z_uf = KEY_BOT + 1.6 - s.dst           # up-stop felt free surface: at rest the crossbar is dst into the felt
        s.z_df = rot((key.y_dn, KEY_BOT), PIV, key.theta_dip)[1]   # down-stop felt free surface = dip contact
        s.vin_u = s.vin_d = None
        s.alpha_prev = 0.0

    def forces(s, th, w):
        k = s.k
        Pu = rot((k.y_up, KEY_BOT + 1.6), PIV, th)
        pen_u = Pu[1] - s.z_uf
        Pd = rot((k.y_dn, KEY_BOT), PIV, th)
        pen_d = s.z_df - Pd[1]
        Fu = Fd = 0.0
        if pen_u > 0:
            rate = (Pu[0] - PIV[0]) * w             # d(pen_u)/dt = dz/dt of the crossbar top
            if s.vin_u is None:
                s.vin_u = max(abs(rate), 1.0)
            lam = 8 * (1 - FELT_E) / (5 * FELT_E * s.vin_u)   # Flores et al. (valid for low e)
            Fu = max(0.0, felt_force(pen_u, k.up_area) * (1 + lam * rate))
        else:
            s.vin_u = None
        if pen_d > 0:
            rate = -(Pd[0] - PIV[0]) * w
            if s.vin_d is None:
                s.vin_d = max(abs(rate), 1.0)
            lam = 8 * (1 - FELT_E) / (5 * FELT_E * s.vin_d)
            Fd = max(0.0, felt_force(pen_d, k.dn_area) * (1 + lam * rate))
        else:
            s.vin_d = None
        return Pu, Fu, Pd, Fd

    def torque(s, th, w):
        k = s.k
        Pu, Fu, Pd, Fd = s.forces(th, w)
        if s.const is None:
            M = k.M_spring(th) + k.M_grav(th)
            Fs = k.spring.F(k.L_spring(th)) if k.spring else 0.0
        else:
            M = -s.const
            Fs = s.const / (PIV[0] - k.mp["c"][0]) + k.mp["m"] * G     # equivalent support force (for R only)
        M += Fu * (PIV[0] - Pu[0]) - Fd * (PIV[0] - Pd[0])
        Pf = rot((k.y_finger, W_TOP if not k.black else B_TOP), PIV, th)
        M += s.Ff * (PIV[0] - Pf[0])
        # pivot reaction (vertical) incl. the COM acceleration from the previous step
        c = rot(k.mp["c"], PIV, th)
        az = (s.alpha_prev * (c[0] - PIV[0]) - w * w * (c[1] - PIV[1])) * 1e-3   # mm/s^2 -> m/s^2
        R = abs(Fs - k.mp["m"] * G - Fu + Fd - s.Ff - k.mp["m"] * 1e-3 * az)
        Mf = s.fm * (MU_PIVOT * (R + MAG_RET_N) * SHAFT_D / 2 + F_GUIDE * G * k.arm(k.y_guide, th)
                     + F_SPRING_RUB * G * (PIV[0] - k.seat_at(th)[0]))
        M -= Mf * math.tanh(w / W_SMOOTH)
        return M, R, Fu, Fd

    def deriv(s, th, w):
        M = s.torque(th, w)[0]
        a = M * 1e6 / s.I
        return w, a

    def step(s, th, w):
        k1 = s.deriv(th, w)
        k2 = s.deriv(th + DT / 2 * k1[0], w + DT / 2 * k1[1])
        k3 = s.deriv(th + DT / 2 * k2[0], w + DT / 2 * k2[1])
        k4 = s.deriv(th + DT * k3[0], w + DT * k3[1])
        s.alpha_prev = k1[1]
        return (th + DT / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]),
                w + DT / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]))


def mag_rise_frac(key, th):
    z0 = rot((key.y_mag, KEY_BOT), PIV, 0.0)[1]
    zb = rot((key.y_mag, KEY_BOT), PIV, key.theta_dip)[1]
    return (rot((key.y_mag, KEY_BOT), PIV, th)[1] - zb) / (z0 - zb)


RETRIG = 0.40            # firmware re-arms when the magnet has risen 40 % of its travel from the bottom


def sim_release(key, fric_mult=1.0, const_force=None, t_end=0.30):
    s = Sim(key, fric_mult, 0.0, const_force)
    th, w, t = key.theta_dip, 0.0, 0.0
    arm0 = key.arm(key.y_front, 0.0, W_TOP)
    out = dict(t_rt=None, t_full=None, v_imp=None, E_imp=None, pen_max=0.0, rebound=0.0, t_settle=None,
               R_min=1e9, R_max=0.0)
    last_out = 0.0
    while t < t_end:
        th, w = s.step(th, w)
        t += DT
        M, R, Fu, Fd = s.torque(th, w)
        out["R_min"], out["R_max"] = min(out["R_min"], R), max(out["R_max"], R)
        if out["t_rt"] is None and mag_rise_frac(key, th) >= RETRIG:
            out["t_rt"] = t * 1e3
        if out["t_full"] is None and Fu > 0:
            out["t_full"] = t * 1e3
            out["v_imp"] = -w * arm0                                       # mm/s at the front
            out["E_imp"] = 0.5 * s.I * 1e-9 * w * w * 1e3                  # mJ
        if out["t_full"] is not None:
            pen = rot((key.y_up, KEY_BOT + 1.6), PIV, th)[1] - s.z_uf
            out["pen_max"] = max(out["pen_max"], pen)
            front_drop = th * arm0                                         # + = below rest
            out["rebound"] = max(out["rebound"], front_drop)
            if abs(front_drop) > 0.1:
                last_out = t
    out["t_settle"] = last_out * 1e3 if out["t_full"] else None
    return out


def sim_press(key, finger_g, th0, fric_mult=1.0, t_end=0.2):
    s = Sim(key, fric_mult, finger_g)
    th, w, t = th0, 0.0, 0.0
    while t < t_end:
        th, w = s.step(th, w)
        t += DT
        if th >= key.theta_dip:
            return t * 1e3, w * key.arm(key.y_front, 0.0, W_TOP)
    return None, None


def theta_at_rise(key, frac):
    lo, hi = 0.0, key.theta_dip
    for _ in range(60):
        m = (lo + hi) / 2
        if mag_rise_frac(key, m) < frac:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


# ---------------------------------------------------------------- sensor: magnet recess, gaps, field
def B_axial(z_gap):
    """on-axis field (mT) of the Ø5x2 N35 disc at distance z_gap (mm) from its face."""
    R, T = MAG_D / 2, MAG_T
    return BR_N35 / 2 * ((T + z_gap) / math.hypot(R, T + z_gap) - z_gap / math.hypot(R, z_gap)) * 1000


def magnet_setup(key):
    """choose the magnet face height at rest so the bottom gap equals v3's (keeps the Hall range)."""
    gap_b = GAP_BOT_B_V3 if key.black else GAP_BOT_W_V3
    zf = KEY_BOT
    for _ in range(40):
        zb = rot((key.y_mag, zf), PIV, key.theta_dip)[1]
        zf += (key.z_elem + gap_b) - zb
    pr = rot((key.y_mag, zf), PIV, key.theta_dip)
    return dict(z_face=zf, recess=zf - KEY_BOT, gap_rest=zf - key.z_elem, gap_bot=pr[1] - key.z_elem,
                travel=zf - pr[1], y_rest=key.y_mag, y_bot=pr[0],
                B_rest=B_axial(zf - key.z_elem), B_bot=B_axial(pr[1] - key.z_elem))


# ---------------------------------------------------------------- frame levels derived from the key
HOOK_T = 2.0             # frame hook finger thickness (z)
HOOK_L = 3.0             # finger overhang over the crossbar (y)
HOOK_W = 8.3


def frame_levels(key, sim):
    """up-stop felt / finger, down-stop felt and rail tops (rest geometry)."""
    felt_free_bot = sim.z_uf
    finger_under = felt_free_bot + FELT_T
    d_top = sim.z_df                                     # down-stop felt top (dip contact)
    return dict(upfelt_free_bottom=felt_free_bot, finger_under=finger_under, finger_top=finger_under + HOOK_T,
                downfelt_top=d_top, downrail_top=d_top - FELT_T)


# ---------------------------------------------------------------- constant stress in plastic at rest
def u_channel_Z(w_top, t_top, h, t_wall):
    """section modulus (min) of a downward-open U channel: top plate w x t + 2 walls t_wall x (h - t)."""
    parts = [(w_top * t_top, h - t_top / 2, w_top * t_top ** 3 / 12),
             (2 * t_wall * (h - t_top), (h - t_top) / 2, 2 * t_wall * (h - t_top) ** 3 / 12)]
    A = sum(p[0] for p in parts)
    zc = sum(p[0] * p[1] for p in parts) / A
    I = sum(p[2] + p[0] * (p[1] - zc) ** 2 for p in parts)
    return I / max(zc, h - zc)


def bending_at_rest(key):
    """internal bending moment (N*mm) along the key at rest from: gravity of every body, spring (up at y_s),
    up-stop reaction (down at y_up); cut at section y, sum of moments of the loads in FRONT of the cut."""
    U, _ = key.rest()
    Fs = key.spring.F(key.L_spring(0.0))
    out = []
    for yc in (30, 50, 70, 100, 120, 138, 144, 160, 180, 192):
        M = 0.0
        for b in key.B:
            y0, y1 = (b.y0, b.y1) if hasattr(b, "y0") else (b.c[0] - b.d / 2, b.c[0] + b.d / 2)
            if y1 <= yc:
                M += b.m * G * (yc - b.c[0])
            elif y0 < yc:
                f = (yc - y0) / (y1 - y0)
                M += b.m * f * G * (yc - (y0 + yc) / 2)
        if key.y_up < yc:
            M += U * (yc - key.y_up)
        if Y_S < yc:
            M -= Fs * (yc - Y_S)
        out.append((yc, M))
    return out


def rest_stresses(key):
    U, dst = key.rest()
    Fs = key.spring.F(key.L_spring(0.0))
    R = Fs - key.mp["m"] * G - U                         # N, key pushes UP on the shaft (+) at rest
    res = {}
    if key.black:
        Z_body = u_channel_Z(9.75, SKIN_B, B_TOP - KEY_BOT, WALL)
    else:
        Z_body = u_channel_Z(14.362, SKIN_W, W_TOP - KEY_BOT, WALL)
    Z_arm = u_channel_Z(10.0 if not key.black else 9.0, 2.0, W_TOP - 29.5, WALL)
    bm = bending_at_rest(key)
    res["body bending max (U-channel)"] = max(abs(M) / (Z_arm if y > 144 else Z_body) for y, M in bm)
    res["_bm"] = bm
    # pivot fork: lower prong (t3, w6) carries R as a 1.5 mm cantilever from the slot end; bearing pressure
    res["fork lower prong bending"] = 6 * abs(R) * 1.5 / (RING_W * 3.0 ** 2)
    res["fork bearing pressure"] = (abs(R) + MAG_RET_N) / (SHAFT_D * RING_W)
    # spring seat: spring force on the top skin, boss spanning the walls (fixed-fixed strip, width = boss)
    span = (14.362 - 2 * WALL) if not key.black else 7.3
    t = SKIN_B if key.black else SKIN_W
    b = 9.0 if not key.black else 7.0
    res["top skin under spring seat"] = 6 * (Fs * span / 8) / (b * t ** 2)
    # frame hook finger (cantilever HOOK_L, t HOOK_T, w HOOK_W) under the up-stop force U
    res["frame hook finger (up-stop)"] = 6 * U * HOOK_L / (HOOK_W * HOOK_T ** 2)
    # steel insert resting on its 1.0 mm floor (white) / 1.0 floor (black): strip spanning the interior
    steel = key.mp["steel"] * G
    if steel > 0:
        if key.black:
            q, sp_, L = steel / 47.0, 8.6, 1.0
        else:
            q, sp_, L = steel / 34.0, 20.1, 1.0
        res["insert floor (steel weight)"] = 6 * (q * sp_ / 8) / (1.0 * L ** 2)
    # fins carrying the shaft: tension, fin 2 x 10 per key side (two fins share a key)
    res["shaft fin tension"] = abs(R) / (2 * 2.0 * 10.0)
    res["_R_rest"] = R
    res["_U"] = U
    res["_Fs"] = Fs
    res["_felt_static_mm"] = dst
    return res


# ---------------------------------------------------------------- design point
DESIGN = dict(W=("bar", 34), B=("flat", 47))      # 16x16x34 square bar (white), 6x19x47 flat bar (black)
POST_TOP_W, POST_TOP_B = 20.0, 30.0               # printed spring guide posts (z)
SLIDE = 3.5                                       # install/remove slide (y): crossbar/finger overlap 2.5 + 1.0
F_PRESS = (150.0, 300.0)                          # gf at the finger for the re-press after re-trigger


SPRING_W = (0.45, 5.5, 40)    # d, OD, active turns: near-flattest feasible with a common wire (see section 1)
SPRING_B = (0.45, 5.0, 75)    # same wire, smaller OD -> the two springs cannot be mixed up


def build(cfg=DESIGN, spring_w=SPRING_W, spring_b=SPRING_B):
    wk = Key(False, white_key(cfg))
    bk = Key(True, black_key(cfg), z_seat=Z_SEAT_B)
    rw = pick_spring(wk) if spring_w is None else None
    if spring_w is not None:
        fit_L0(wk, Spring(*spring_w, 50.0))
    rb = pick_spring(bk) if spring_b is None else None
    if spring_b is not None:
        fit_L0(bk, Spring(*spring_b, 50.0))
    return wk, bk


def dyn_summary(key, fric_mult=1.0):
    r = sim_release(key, fric_mult)
    th_rt = theta_at_rise(key, RETRIG)
    presses = [sim_press(key, f, th_rt, fric_mult)[0] for f in F_PRESS]
    r["t_down"] = presses
    r["hz"] = [1000.0 / (r["t_rt"] + p) for p in presses]
    return r


def fmt(v, n=2):
    return ("%." + str(n) + "f") % v if isinstance(v, (int, float)) and v is not None else str(v)


def section(t):
    print("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


def report():
    section("K1 - rear-pivot key + steel compression spring + encapsulated steel inertia mass  (calc.py)")
    print("assumptions: mu_pivot=%.2f (steel/PETG dry), guide drag %.1f gf at the tab, spring rub %.1f gf, "
          "retention magnet %.1f N, felt 3T P=%.2f*eps^%.1f MPa, e=%.1f; re-trigger at %d%% magnet rise; "
          "re-press with %s gf at the finger" % (MU_PIVOT, F_GUIDE, F_SPRING_RUB, MAG_RET_N, FELT_A, FELT_P,
                                                  FELT_E, RETRIG * 100, "/".join("%d" % f for f in F_PRESS)))

    # ---- 1. why two springs: common-spring check
    section("1. spring choice: one common spring vs white/black springs")
    wk, bk = build()
    spw = wk.spring
    bk_c = Key(True, black_key(DESIGN))
    fit_seat(bk_c, spw)
    print("common spring (white spec) on the black key: seat would have to be at z%.1f (search limit; black skin underside "
          "is z%.1f -> infeasible, black DW there %.1f g) and the black BW rise rest->bottom would be %.1f g (white %.1f g)"
          "  -> rejected, black spring gets its own spec"
          % (bk_c.seat[1], Z_SEAT_B, bk_c.DW_UW(0.0)[0], bk_c.BW(bk_c.theta_dip) - bk_c.BW(0),
             wk.BW(wk.theta_dip) - wk.BW(0)))
    for nm, key in (("white", wk), ("black", bk)):
        tab = spring_table(key)
        print("%s: %d feasible (d, OD, n) combos; flattest 5:" % (nm, len(tab)))
        for r in tab[:5]:
            print("   d %.2f OD %.1f n %3d L0 %.1f k %.3f N/mm rise %.1f g tau %.0f MPa surge %.0f Hz"
                  % (r["d"], r["OD"], r["n"], r["L0"], r["k"], r["rise"], r["tau"], r["f"]))
    # torsion alternative (coaxial on the shaft), for the record
    print("torsion alternative (coaxial on the shaft, coil <= 8 mm long between key ears):")
    for d, Dm, n in ((1.3, 6.0, 5), (1.2, 6.0, 5)):
        kt = E_WIRE * d ** 4 / (64 * Dm * n)                       # N*mm/rad
        C = Dm / d
        Ki = (4 * C * C - C - 1) / (4 * C * (C - 1))
        for nm, key in (("white", wk), ("black", bk)):
            M0 = -key.M_spring(0.0)                                  # same rest torque the coil spring gives
            phi0 = M0 / kt
            rise = kt * key.theta_dip / key.arm(key.y_finger, 0, W_TOP) / G
            sig = Ki * 32 * (M0 + kt * key.theta_dip) / (math.pi * d ** 3)
            print("   d %.1f Dm %.1f n %d: %s preload %.0f deg, rise %.1f g, bending %.0f MPa (%.2f UTS)"
                  % (d, Dm, n, nm, math.degrees(phi0), rise, sig, sig / uts_wire(d)))

    # ---- 2. inertia sweep
    section("2. inertia sweep (white insert; black 6x19x47) - m_eff vs return time; spring re-picked each time")
    print("%-26s %6s %7s %7s %6s %6s %6s %7s %7s %7s %7s" % ("white insert", "steel", "meff0", "meff13",
          "DW", "UW", "DWbot", "rise", "t_rt", "t_full", "Hz150"))
    sweep = [("none", ("balls", 0)), ("2 x 5/8in balls", ("balls", 2)), ("bar 16x16x20", ("bar", 20)),
             ("2x flat 19x6x34", ("flat2", 34)), ("bar 16x16x34 (design)", ("bar", 34)),
             ("bar 16x16x46 (hypoth.)", ("bar", 46)), ("bar 16x16x60 (hypoth.)", ("bar", 60))]
    for nm, w in sweep:
        k = Key(False, white_key(dict(W=w)))
        pick_spring(k)
        d = dyn_summary(k)
        dw, uw = k.DW_UW(0.0)
        print("%-26s %6.1f %7.1f %7.1f %6.1f %6.1f %6.1f %7.1f %7.1f %7.1f %7.1f" % (
            nm, k.mp["steel"], k.mp["I"] / k.arm(0, 0, W_TOP) ** 2, k.mp["I"] / k.arm(13, 0, W_TOP) ** 2,
            dw, uw, k.DW_UW(k.theta_dip)[0], k.BW(k.theta_dip) - k.BW(0), d["t_rt"], d["t_full"], d["hz"][0]))
    print("black inserts:")
    for nm, b in (("none", ("flat", 0)), ("5 x 5/16in balls", ("balls516", 5)), ("flat 6x19x22", ("flat", 22)),
                  ("flat 6x19x47 (design)", ("flat", 47))):
        k = Key(True, black_key(dict(B=b)), z_seat=Z_SEAT_B)
        pick_spring(k)
        d = dyn_summary(k)
        dw, uw = k.DW_UW(0.0)
        print("%-26s %6.1f %7.1f %7s %6.1f %6.1f %6.1f %7.1f %7.1f %7.1f %7.1f" % (
            nm, k.mp["steel"], k.mp["I"] / k.arm(Y_BFRONT, 0, B_TOP) ** 2, "-", dw, uw,
            k.DW_UW(k.theta_dip)[0], k.BW(k.theta_dip) - k.BW(0), d["t_rt"], d["t_full"], d["hz"][0]))
    return wk, bk


def pt(key, p, th):
    q = rot(p, PIV, th)
    return "(%.1f, %.1f)" % q


def report2(wk, bk):
    section("3. design point: coordinates (y, z) at rest -> fully pressed (dip contact)")
    for nm, k in (("WHITE (D key, representative)", wk), ("BLACK (C#, representative)", bk)):
        ms = magnet_setup(k)
        sim = Sim(k)
        fl = frame_levels(k, sim)
        th = k.theta_dip
        print("%s: rotation to the bottom %.3f deg" % (nm, math.degrees(th)))
        rows = [("pivot shaft axis (fixed)", PIV),
                ("key top front edge (dip ref.)", k.top_front),
                ("finger point for DW/UW", (k.y_finger, B_TOP if k.black else W_TOP)),
                ("centre of mass (key+steel)", k.mp["c"]),
                ("spring upper seat", k.seat),
                ("spring lower seat (fixed)", (Y_S, Z_SEAT_LO)),
                ("up-stop crossbar top (centre)", (k.y_up, KEY_BOT + 1.6)),
                ("down-stop pad (centre, underside)", (k.y_dn, KEY_BOT)),
                ("sensor magnet face centre", (k.y_mag, ms["z_face"])),
                ("rear arm top at y146", (146.0, W_TOP)),
                ("fork tip (key end)", (204.0, PIV[1]))]
        for lab, p in rows:
            moving = "fixed" not in lab
            print("   %-36s rest %-16s bottom %s" % (lab, "(%.1f, %.1f)" % p, pt(k, p, th) if moving else "(fixed)"))
        print("   frame: up-stop felt free bottom z%.2f, hook finger z%.2f-%.2f (y%.2f-%.2f); down-stop felt top z%.2f"
              " (rail top z%.2f) at y%.1f; spring post top z%.0f"
              % (fl["upfelt_free_bottom"], fl["finger_under"], fl["finger_top"], k.y_up - 0.75, k.y_up + 2.25,
                 fl["downfelt_top"], fl["downrail_top"], k.y_dn, POST_TOP_B if k.black else POST_TOP_W))

    section("4. masses and inertia")
    for nm, k in (("white", wk), ("black", bk)):
        yf = k.y_front
        print("%s: total %.1f g (PETG %.1f, steel %.1f, magnets %.2f), COM (%.1f, %.1f), I_pivot %.0f g*mm^2"
              % (nm, k.mp["m"], k.mp["plastic"], k.mp["steel"], k.mp["m"] - k.mp["plastic"] - k.mp["steel"],
                 k.mp["c"][0], k.mp["c"][1], k.mp["I"]))
        Isp = k.spring.mass / 3 * (PIV[0] - Y_S) ** 2
        for lab, y, z in (("front edge", yf, B_TOP if k.black else W_TOP), ("finger", k.y_finger, B_TOP if k.black else W_TOP)):
            a = k.arm(y, 0, z)
            print("   m_eff at %-10s (arm %.1f): key+steel %.1f g, +spring %.2f g -> %.1f g"
                  % (lab, a, k.mp["I"] / a ** 2, Isp / a ** 2, (k.mp["I"] + Isp) / a ** 2))
        top = sorted(k.B, key=lambda b: -(b.Ic + b.m * ((b.c[0] - PIV[0]) ** 2 + (b.c[1] - PIV[1]) ** 2)))[:4]
        print("   largest inertia contributors: " + "; ".join("%s %.0f%%" % (b.name, 100 * (b.Ic + b.m * (
            (b.c[0] - PIV[0]) ** 2 + (b.c[1] - PIV[1]) ** 2)) / k.mp["I"]) for b in top))

    section("5. springs (music wire SWP-A, closed & ground ends)")
    for nm, k in (("white", wk), ("black", bk)):
        sp = k.spring
        Lr, Lb = k.L_spring(0), k.L_spring(k.theta_dip)
        print("%s: d %.2f OD %.2f (ID %.2f) n %d active (%d total), L0 %.1f, k %.4f N/mm, solid %.1f, mass %.2f g"
              % (nm, sp.d, sp.OD, sp.OD - 2 * sp.d, sp.n, sp.Nt, sp.L0, sp.k, sp.Ls, sp.mass))
        print("   installed %.2f (rest) -> %.2f (bottom): F %.3f -> %.3f N (+%.1f%%); preload defl %.1f, stroke %.2f; "
              "tau %.0f/%.0f MPa = %.2f UTS; defl/available %.2f; surge %.0f Hz; lateral seat shift %.2f mm"
              % (Lr, Lb, sp.F(Lr), sp.F(Lb), 100 * (sp.F(Lb) / sp.F(Lr) - 1), sp.L0 - Lr, Lr - Lb, sp.tau(sp.F(Lr)),
                 sp.tau(sp.F(Lb)), sp.tau(sp.F(Lb)) / uts_wire(sp.d), (sp.L0 - Lb) / (sp.L0 - sp.Ls), sp.f_surge,
                 k.seat_at(k.theta_dip)[0] - k.seat[0]))
        print("   per-key trim: 0.5 mm printed shim under the spring = %.2f g at the finger"
              % (sp.k * 0.5 * (PIV[0] - Y_S) / k.arm(k.y_finger, 0, W_TOP) / G))
        tol = 0.10 * sp.F(Lr) * (PIV[0] - Y_S) / k.arm(k.y_finger, 0, W_TOP) / G
        print("   spring load tolerance +-10%% at L_rest -> +-%.1f g at the finger (order load-tolerance springs or bin them)" % tol)


def report3(wk, bk):
    M = {}
    section("6. static forces (g) - BW = frictionless balance force; DW/UW include friction")
    for nm, k in (("white", wk), ("black", bk)):
        yf = k.y_finger
        ztop = B_TOP if k.black else W_TOP
        print("%s at finger y%.1f:" % (nm, yf))
        for f in (0.0, 0.25, 0.5, 0.75, 1.0):
            th = f * k.theta_dip
            dw, uw = k.DW_UW(th)
            print("   %3d%% dip: BW %.1f  DW %.1f  UW %.1f  (at front edge y%.1f: BW %.1f DW %.1f UW %.1f)"
                  % (f * 100, k.BW(th), dw, uw, k.y_front, k.BW(th, k.y_front), *k.DW_UW(th, k.y_front)))
        dw0, uw0 = k.DW_UW(0.0)
        # friction breakdown at rest (for the DW case)
        R = k.R_vert(0.0, dw0 * G)
        a = k.arm(yf, 0, ztop)
        parts = dict(pivot_R=MU_PIVOT * R * SHAFT_D / 2, pivot_magnet=MU_PIVOT * MAG_RET_N * SHAFT_D / 2,
                     guide=F_GUIDE * G * k.arm(k.y_guide, 0), spring_rub=F_SPRING_RUB * G * (PIV[0] - Y_S))
        print("   friction at the finger: " + ", ".join("%s %.2f g" % (n_, v / a / G) for n_, v in parts.items())
              + " -> total %.2f g; DW-UW = %.2f g (= 2 x friction: spring is conservative)" % (
                  sum(parts.values()) / a / G, dw0 - uw0))
        print("   balance weight (DW+UW)/2 = %.1f g; start DW %.1f / UW %.1f; bottom DW %.1f / UW %.1f"
              % ((dw0 + uw0) / 2, dw0, uw0, *k.DW_UW(k.theta_dip)))
        for m_ in FRIC_SENS[1:]:
            print("   friction x%.0f: DW %.1f  UW %.1f (start), UW at bottom %.1f"
                  % (m_, *k.DW_UW(0.0, None, m_), k.DW_UW(k.theta_dip, None, m_)[1]))
        M[nm] = dict(dw=dw0, uw=uw0, dwb=k.DW_UW(k.theta_dip)[0], uwb=k.DW_UW(k.theta_dip)[1],
                     fric=(dw0 - uw0) / 2)
    f13 = wk.DW_UW(0.0, 13.0)[0]
    f90 = wk.DW_UW(0.0, 90.0)[0]
    print("front/back: white DW at y90 %.1f g / at y13 %.1f g = %.2f  (pure lever (200-13)/(200-90) = %.2f)"
          % (f90, f13, f90 / f13, (PIV[0] - 13) / (PIV[0] - 90)))
    M["fb"] = f90 / f13

    section("7. dynamics - release from the bottom (felt contact, v=0), re-press, full return")
    for nm, k in (("white", wk), ("black", bk)):
        for fm in FRIC_SENS:
            d = dyn_summary(k, fm)
            print("%s friction x%.0f: t(bottom->%d%% rise) %.1f ms, full return (up-stop contact) %.1f ms, "
                  "impact %.0f mm/s at the front, %.2f mJ, felt max %.2f mm, rebound %.2f mm, settled (<0.1 mm) %.0f ms"
                  % (nm, fm, RETRIG * 100, d["t_rt"], d["t_full"], d["v_imp"], d["E_imp"], d["pen_max"], d["rebound"],
                     d["t_settle"]))
            print("      re-press %s gf: %s ms -> re-trigger rate %s Hz; pivot vertical reaction |R| %.2f..%.2f N"
                  % ("/".join("%d" % f for f in F_PRESS), "/".join("%.1f" % t for t in d["t_down"]),
                     "/".join("%.1f" % h for h in d["hz"]), d["R_min"], d["R_max"]))
            if fm == 1.0:
                M[nm + "_dyn"] = d
        g = sim_release(k, 1.0, const_force=k.M_net_up(0.0))
        print("   same inertia with a constant (gravity-like) return torque = rest BW: t_rt %.1f ms, full %.1f ms"
              % (g["t_rt"], g["t_full"]))
        print("   without the spring the key does not return (front-heavy: gravity torque %+.0f N*mm pushes the front down)"
              % k.M_grav(0.0))
        sp = k.spring
        print("   spring never unloads: F at rest %.2f N, min over stroke %.2f N (no separation; steel is encapsulated)"
              % (sp.F(k.L_spring(0)), min(sp.F(k.L_spring(t)) for t in (0.0, k.theta_dip))))
    # v2.0 claim check: gravity return time "fixed ~40 ms regardless of mass"
    print("v2.0 claim check (constant force F=BW-friction on m_eff, 10 mm): ", end="")
    for me, bw, fr in ((47, 44, 6), (65, 47, 2.5), (128, 44, 6)):
        t = math.sqrt(2 * 10e-3 * me * 1e-3 / ((bw - fr) * G))
        print("m_eff %d g, BW %d, fric %.1f -> %.0f ms; " % (me, bw, fr, t * 1e3), end="")
    print("=> time scales with sqrt(m_eff/(BW-friction)); not fixed.")

    section("8. constant stress in plastic at rest (MPa)")
    smax = 0.0
    for nm, k in (("white", wk), ("black", bk)):
        r = rest_stresses(k)
        vals = {a: v for a, v in r.items() if not a.startswith("_")}
        smax = max(smax, max(vals.values()))
        print("%s: spring %.2f N up, up-stop %.2f N down (felt pre-compression %.2f mm), pivot reaction %.2f N (key pushes "
              "the shaft up)" % (nm, r["_Fs"], r["_U"], r["_felt_static_mm"], r["_R_rest"]))
        for a, v in vals.items():
            print("   %-36s %.2f" % (a, v))
        print("   bending moment along the key at rest (y, N*mm): " + ", ".join("%d:%.0f" % bm for bm in r["_bm"]))
    print("max constant plastic stress = %.2f MPa (target < 2); the only permanently loaded parts are felt (stops) and "
          "steel (spring, shaft)" % smax)
    M["smax"] = smax
    return M


def clearances(wk, bk):
    C = {}
    for nm, k in (("white", wk), ("black", bk)):
        th = k.theta_dip
        sim = Sim(k)
        fl = frame_levels(k, sim)
        zbar = Z_BAR_TOP_B if k.black else Z_BAR_TOP_W
        ys = [BAR_Y[0] + i * (BAR_Y[1] - BAR_Y[0]) / 20 for i in range(21)]
        C[nm + ": key underside - sensor bar top @dip"] = min(rot((y, KEY_BOT), PIV, th)[1] for y in ys) - zbar
        tip = k.y_up - 0.75                                   # hook finger front tip (y)
        if k.black:
            ceil_z = B_TOP - SKIN_B
            C[nm + ": key ceiling - hook finger top @dip"] = min(
                rot((y, ceil_z), PIV, th)[1] for y in (tip, tip + 3.0)) - fl["finger_top"]
            C[nm + ": insert floor end (y101) - finger tip, y @dip"] = tip - rot((101.0, 32.0), PIV, th)[0]
            C[nm + ": black top @dip - white top"] = rot(k.top_front, PIV, th)[1] - W_TOP
        else:
            C[nm + ": key ceiling - hook finger top @dip"] = min(
                rot((y, W_TOP - SKIN_W), PIV, th)[1] for y in (tip, tip + 3.0)) - fl["finger_top"]
            C[nm + ": cavity wall (y39.5) - finger tip, y @dip"] = tip - max(
                rot((39.5, z), PIV, th)[0] for z in (KEY_BOT, W_TOP - SKIN_W))
        C[nm + ": tail end (y144) - board footprint y145.5, y @dip (info: key edge is at z>19.8, board top z10.6)"] = \
            145.5 - max(rot((144.0, z), PIV, th)[0] for z in (KEY_BOT, 29.5))
        C[nm + ": rear arm underside - board parts (z20) @dip"] = rot((145.5, 29.5), PIV, th)[1] - BOARD["z_top_parts"]
        C[nm + ": rear arm top - cover fascia (rest)"] = COVER_FASCIA_Z - W_TOP
        post = POST_TOP_B if k.black else POST_TOP_W
        C[nm + ": spring spigot - guide post top @dip"] = k.seat_at(th)[1] - 3.0 - post
        interior = 8.6 if k.black else 14.362 - 2 * WALL
        C[nm + ": spring coil - key wall (radial)"] = (interior - k.spring.OD) / 2
        C[nm + ": fork - fin (x, per side, design)"] = 0.3
        ms = magnet_setup(k)
        C[nm + ": magnet face - Hall element @dip"] = ms["gap_bot"]
    return C


def frame_mass_delta():
    """per module, g: v3 frame 175 g minus spine rail and rear stop rail, plus fin comb and spring posts."""
    rem_spine = 164.5 * 13 * (20.7 - 5.0) * 0.45 * RHO_PETG / 1000
    rem_rstop = 164.5 * 6 * (19.7 - 5.0) * 0.5 * RHO_PETG / 1000
    add_fins = (13 * 2.0 * 10.0 * (39.5 - 5.0) + 164.5 * 10 * 3.0) * 0.9 * RHO_PETG / 1000
    add_posts = (7 * math.pi * 1.6 ** 2 * (POST_TOP_W - 5) + 5 * math.pi * 1.6 ** 2 * (POST_TOP_B - 5)) * 0.9 * RHO_PETG / 1000
    return 175.0 - rem_spine - rem_rstop + add_fins + add_posts, dict(spine=-rem_spine, rear_stop=-rem_rstop,
                                                                       fins=add_fins, posts=add_posts)


PURCHASE = [   # item, spec, qty_88, unit KRW, source (price status)
    ("압축 스프링 (백건)", "SWP-A 피아노선, 양끝 닫힘·연마, 사양은 5절", 60, None, "국내 스프링 소량 주문제작 — estimate"),
    ("압축 스프링 (흑건)", "SWP-A 피아노선, 양끝 닫힘·연마, 사양은 5절", 40, None, "국내 스프링 소량 주문제작 — estimate"),
    ("S45C 연마봉 Ø5 × 1 m", "회전축, 164 mm × 8개로 절단(끝 부속 2개 포함)", 2, 4790, "배관몰 baegwan.net goods 4320 (확인 4,790원/1 m, 배송 6,000원 별도)"),
    ("배송비(연마봉)", "1 m 기준 기본 배송", 1, 6000, "배관몰 상품 안내 (확인)"),
    ("SS400 사각봉 16×16, 34 mm 절단", "백건 관성 추 (68.3 g)", 56, 800, "국내 철강 온라인몰 절단 주문 — estimate (자재 약 7,000원/m + 절단 개당 약 500원)"),
    ("SS400 평철 6×19, 47 mm 절단", "흑건 관성 추 (42.1 g)", 40, 700, "국내 철강 온라인몰 절단 주문 — estimate"),
    ("네오디뮴 원형자석 Ø5×2 N35", "포크 끝 고정 자석 (센서 자석과 같은 품목)", 100, 80, "dgmagnet (v3 구매목록 L21 단가 80원)"),
]
REMOVED_V3 = [  # v3.2 purchase-list rows no longer needed (KRW)
    ("스텐 유두 렌치볼트 M3×40 (척추 클램프) 34개", 4420),
    ("스텐 무두 렌치볼트 M3×10 (세트스크루) 40개", 2400),
    ("황동 원판 Ø8×1 4봉", 10676),
    ("M3 육각너트 63개 (클램프·세트스크루용, 75→12개)", 693),
]
SPRING_LOT_EST = 60000   # KRW for 60 + 40 custom springs incl. setup (estimate, not verified)


def report4(wk, bk, M):
    section("9. sensing at the v3 Hall row (y67)")
    for nm, k in (("white", wk), ("black", bk)):
        ms = magnet_setup(k)
        print("%s: magnet face recessed %.2f mm into the key underside; face->element rest %.2f, bottom %.2f, travel %.2f mm; "
              "magnet y %.1f -> %.1f (element y67); on-axis B %.1f -> %.1f mT (DRV5055A2 @3.3 V linear to ~42 mT)"
              % (nm, ms["recess"], ms["gap_rest"], ms["gap_bot"], ms["travel"], ms["y_rest"], ms["y_bot"],
                 ms["B_rest"], ms["B_bot"]))
        M[nm + "_mag"] = ms
    print("nearest steel to a sensor magnet: white insert ends y38 (27.8 mm in front of its magnet); black insert bottom "
          "z33 = %.1f mm above its magnet top (moves with it: calibrated offset)" % (33.0 - (KEY_BOT + MAG_T)))

    section("10. clearances (mm) and envelope")
    C = clearances(wk, bk)
    for a, v in C.items():
        print("   %-58s %.2f" % (a, v))
    moving = {a: v for a, v in C.items() if "Hall" not in a and "design" not in a and "info" not in a}
    M["min_clear"] = min(moving.values())
    M["min_clear_item"] = min(moving, key=moving.get)
    M["min_gap_sensor"] = min(v for a, v in C.items() if "Hall" in a)
    low_w = min(rot((y, KEY_BOT), PIV, wk.theta_dip)[1] for y in (2.7, 10.0))
    low_b = min(rot((y, KEY_BOT), PIV, bk.theta_dip)[1] for y in (51.5, 58.7))
    print("   y range: keys y0 (lip) .. y204 (fork tip); frame y0..212 (v3); rear bar from y215 -> total depth 410 (unchanged)")
    print("   z: white top %.1f, black top %.1f, highest moving part z%.1f (black top at rest; parts behind the pivot rise "
          "<= %.2f mm); lowest moving part z%.2f (white front underside at the bottom), black z%.2f; frame floor z5; "
          "cover top z59" % (W_TOP, B_TOP, B_TOP, 4.0 * bk.theta_dip, low_w, low_b))
    M["low"] = min(low_w, low_b)

    section("11. parts, print plan, steel, filament")
    fm, fd = frame_mass_delta()
    kw, kb = wk.mp["plastic"], bk.mp["plastic"]
    per_oct = dict(white_keys=7 * kw, black_keys=5 * kb, frame=fm, sensor_bar=17.0, rear_cover=44.0)
    print("printed parts per octave: 7 white keys (%.1f g each), 5 black keys (%.1f g each), 1 frame (%.0f g: v3 175 %s), "
          "1 sensor bar (17 g, v3), 1 rear cover (44 g, v3) = 15 parts, %.0f g"
          % (kw, kb, fm, " ".join("%s %+.1f" % (a, v) for a, v in fd.items()), sum(per_oct.values())))
    oct_eq = 7 + (47.0 + 39.5) / 164.5
    total = (52 * kw + 36 * kb + oct_eq * (fm + 17.0 + 44.0)) * 1.10
    print("88 keys: 52 white x %.1f + 36 black x %.1f + %.2f module-equivalents x %.0f g, +10%% waste = %.2f kg, %.0f h at 15 g/h"
          " (v3: 4.13 kg / 275 h)" % (kw, kb, oct_eq, fm + 61, total / 1000, total / 15))
    print("bed 220x220: white key plate 7 x (22.5+1.5) = 168 x 204 (h20), black plate 5 x 13 = 65 x 152.5 (h32), frame "
          "168.5 x 212 (h36.5), sensor bar + cover as v3 -> all fit; keys print top-down with a PAUSE at z%.1f (white) / "
          "z%.1f (black) from the bed to drop the steel in, then the floor bridges over it" % (W_TOP - KEY_BOT - 1.0,
                                                                                         B_TOP - 33.0))
    steel_oct = 7 * wk.mp["steel"] + 5 * bk.mp["steel"]
    shaft_g = math.pi / 4 * SHAFT_D ** 2 * 164.0 * RHO_STEEL / 1000
    print("steel per octave: inserts %.0f g + shaft %.0f g + springs %.1f g = %.0f g; 88 keys: inserts %.2f kg, total %.2f kg"
          % (steel_oct, shaft_g, 7 * wk.spring.mass + 5 * bk.spring.mass, steel_oct + shaft_g,
             (52 * wk.mp["steel"] + 36 * bk.mp["steel"]) / 1000,
             (52 * wk.mp["steel"] + 36 * bk.mp["steel"] + 8 * shaft_g) / 1000))
    print("module mass: v3 0.59 kg -> K1 %.2f kg (keys+frame printed %.0f g replaces 502 g, + steel)"
          % (0.59 - 0.502 + sum(per_oct.values()) / 1000 + (steel_oct + shaft_g) / 1000, sum(per_oct.values())))
    M.update(filament=total, hours=total / 15, steel_oct=steel_oct + shaft_g, printed_oct=15,
             bought_oct=7 + 5 + 7 + 5 + 1 + 12)

    section("12. purchased items and cost delta vs v3.2 base 583,219 KRW")
    add = 0
    for it, spec, q, u, src in PURCHASE:
        if u is None:
            continue
        add += q * u
        print("   + %-34s %-44s x%3d  %6d  = %7d  [%s]" % (it, spec, q, u, q * u, src))
    add += SPRING_LOT_EST
    print("   + springs 60 white + 40 black (custom lot incl. setup)                            = %7d  [estimate]" % SPRING_LOT_EST)
    rem = sum(v for _, v in REMOVED_V3)
    for it, v in REMOVED_V3:
        print("   - %-70s = %7d" % (it, -v))
    print("   delta = +%d - %d = %+d KRW -> base %d KRW (cap 1,000,000)" % (add, rem, add - rem, 583219 + add - rem))
    M["cost_delta"] = add - rem

    section("13. noise: every impact")
    for nm, k in (("white", wk), ("black", bk)):
        a = k.arm(k.y_front, 0, W_TOP)
        me = k.mp["I"] / a ** 2
        eps = [(0.5 * me * v * v / (k.dn_area * FELT_T * FELT_A / (FELT_P + 1))) ** (1 / (FELT_P + 1)) for v in (0.3, 0.6, 1.0)]
        print("%s down-stop (felt 3T, %.0f mm^2): key-front speed 0.3/0.6/1.0 m/s -> %.1f/%.1f/%.1f mJ into the felt, "
              "felt compression %s%%  (spring actions A/B in the brief: m_eff 12 g -> x%.1f the energy)"
              % (nm, k.dn_area, *(0.5 * me * v * v for v in (0.3, 0.6, 1.0)), "/".join("%.0f" % (100 * e) for e in eps),
                 me / 12.0))
        d = M[nm + "_dyn"]
        print("%s up-stop on release: %.2f mJ into the 24 mm^2 hook felt (%.0f%% compression), rebound %.2f mm, settled %.0f ms"
              % (nm, d["E_imp"], 100 * d["pen_max"] / FELT_T, d["rebound"], d["t_settle"]))
        print("%s spring: surge %.0f Hz (can ring on stop impacts; guide-post contact + a smear of silicone grease damp it)"
              % (nm, k.spring.f_surge))
    print("pivot: fork seated on the shaft by the magnet, 0.05 slot clearance taken up -> no rattle; no coupling "
          "(single lever) -> the Casio release rattle has no source here")
    return M


def main():
    wk, bk = report()
    report2(wk, bk)
    M = report3(wk, bk)
    M = report4(wk, bk, M)
    section("14. metrics (brief section 6)")
    dw, db = M["white_dyn"], M["black_dyn"]
    out = dict(
        dw_white_g=M["white"]["dw"], uw_white_g=M["white"]["uw"], dw_black_g=M["black"]["dw"], uw_black_g=M["black"]["uw"],
        dw_white_bottom_g=M["white"]["dwb"], uw_white_bottom_g=M["white"]["uwb"],
        friction_white_g=M["white"]["fric"],
        m_eff_white_g=wk.mp["I"] / wk.arm(0, 0, W_TOP) ** 2, m_eff_white_y13_g=wk.mp["I"] / wk.arm(13, 0, W_TOP) ** 2,
        m_eff_black_g=bk.mp["I"] / bk.arm(Y_BFRONT, 0, B_TOP) ** 2,
        t_rt_white_ms=dw["t_rt"], t_rt_black_ms=db["t_rt"],
        full_return_ms_white=dw["t_full"], full_return_ms_black=db["t_full"],
        retrigger_hz_white=dw["hz"][0], retrigger_hz_black=db["hz"][0],
        front_back_ratio=M["fb"], max_plastic_rest_stress_mpa=M["smax"],
        magnet_travel_white_mm=M["white_mag"]["travel"], magnet_travel_black_mm=M["black_mag"]["travel"],
        min_gap_sensor_mm=M["min_gap_sensor"], min_clearance_moving_mm=M["min_clear"],
        white_top_z_mm=W_TOP, max_z_mm=B_TOP, frame_depth_mm=FRAME_DEPTH, total_instrument_depth_mm=410.0,
        printed_parts_per_octave=M["printed_oct"], bought_parts_per_octave=M["bought_oct"],
        steel_g_per_octave=M["steel_oct"], filament_g_88=M["filament"], print_h_88=M["hours"],
        cost_delta_krw=M["cost_delta"])
    for a, v in out.items():
        print("   %-30s %.2f" % (a, v))
    print("   min clearance item: %s" % M["min_clear_item"])


if __name__ == "__main__":
    main()
