"""Parametric model of the Toccata key actions (4 methods) + shared layout.

Coordinates (mm): x = across the keyboard (left->right), y = depth measured from the
front edge of the white keys (y=0) toward the back, z = height above the keybed plate top (z=0).
"""
import math
from field import Bz

G = 9.80665e-3  # N per gram-force

# ------------------------------------------------------------------ shared layout
L = dict(
    Pw=23.5,          # white key pitch (octave 164.5)
    gap=1.0,          # gap between neighbouring keys
    Bw=11.5,          # black key width at its base (Reyburn: 11.5)
    Bt=9.5,           # black key width at its top (design choice)
    head=50.0,        # white key head length (front edge -> black key front)
    fall=150.0,       # visible white length (front edge -> name board face)
    black_end=145.0,  # rear end of the raised black body (black length 95)
    black_h=12.0,     # black top above white top
    black_chamfer=4.0,  # black top starts this far behind the black key front
    skin=2.0, wall=1.6, rib=1.2,
    y_sensor=110.0,
    dip=10.0,         # white key dip at the front edge
    black_dip=9.0,    # black key dip at its front top edge (real pianos ~9.5)
    elem_depth=0.8,   # Hall element below branded face (DRV5055 TO-92 LPG)
    g_min=3.0,        # magnet face -> sensor face at the closest point
    rho_petg=1.27, rho_steel=7.85,
    BW_rest=44.0,     # up-force at white key front at rest (g)
    BW_bottom=56.0,   # at full dip (spring methods)
    BW_grav=44.0,     # static balance weight for gravity methods (g)
    friction=6.0,     # estimated friction at the key front (g)
    E_petg=1500.0,    # MPa, Prusament PETG TDS (printed)
    base_t=18.0,      # keybed plywood
    felt=3.0, felt_comp=0.5,
    slip_gap=2.0, slip_t=18.0,
    lid_t=18.0,
    shaft_len=163.0,  # B/D pivot shafts: one per octave module (module 164, rails 0.25..164.25), cut to this length
    # guide pin / guide slot (front of every key)
    pin_d=3.0,        # guide pin diameter
    pin_depth=8.0,    # guide pin pressed this deep into the keybed plywood (Ø2.9 hole)
    slot_len=5.0,     # key guide slot length along y (3.4 across x): pin Ø3 + 2 mm arc clearance, 1.5 mm walls in the 8 mm boss
    slot_clear=1.0,   # min. slot ceiling above the pin tip at full dip (white and black)
    # key ribs / hammer (method D)
    rib_z0=4.0,       # transverse ribs stop this far above the key underside (default)
    rib_clear=1.0,    # min. rib bottom above the rising hammer at full dip
    w_clear_min=1.5,  # min. hammer-weight top below the key ceiling at full dip
    # misc hardware / rail constants shared by several drawings
    spine_bolt=45.0,  # method A spine bolt M3 x spine_bolt
    wire_ch=(116.0, 124.0),  # sensor rail wire channel (y)
    pocket_h=1.7,     # half length (y) of the sensor recess in the sensor rail (y_sensor ± pocket_h)
    pocket_d=1.7,     # depth of that recess below the sensor face (TO-92 is 1.52 thick)
    lead_slot=1.2,    # sensor rail: lead groove/slot width from the recess down into the wire channel
    # rear pivot comb (B, D): fin thickness and side clearance between the key eyelet and each fin
    fin_t=3.0,
    eye_cl=0.3,
    punch_gap=0.3,    # C: min. gap between neighbouring balance-rail felt punchings
)
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
IS_BLACK = [n.endswith("#") for n in NAMES]


def octave_layout(P=L):
    """slot (tail) x-ranges for the 12 keys of one octave, measured from the C left edge."""
    Pw, g, Bw = P["Pw"], P["gap"], P["Bw"]
    bs = Bw + g
    ce = (3 * Pw - 2 * bs) / 3
    fb = (4 * Pw - 3 * bs) / 4
    widths = [ce, bs, ce, bs, ce, fb, bs, fb, bs, fb, bs, fb]
    keys, x, wi = [], 0.0, 0
    for i, n in enumerate(NAMES):
        w = widths[i]
        k = dict(name=n, black=IS_BLACK[i], slot=(x, x + w), cx=x + w / 2,
                 body=(x + g / 2, x + w - g / 2), w=w - g)
        if not k["black"]:
            k["head"] = (wi * Pw + g / 2, (wi + 1) * Pw - g / 2)
            k["hcx"] = (wi + 0.5) * Pw
            wi += 1
        keys.append(k)
        x += w
    return keys, dict(ce=ce, fb=fb, bs=bs, ce_w=ce - g, fb_w=fb - g, black_w=Bw)


KEYS, TAILS = octave_layout()


def rot(p, c, a):
    """rotate point p=(y,z) about c by angle a (CCW, radians)."""
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def solve_theta(pivot, z_top, dip):
    lo, hi = 0.0, 0.2
    for _ in range(60):
        m = (lo + hi) / 2
        if pivot[1] - rot((0, z_top), pivot, m)[1] + (z_top - pivot[1]) < dip:
            pass
        drop = z_top - rot((0, z_top), pivot, m)[1]
        if drop < dip:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def spring_from_k(k, F_rest, s, d=0.4, D_out=6.0, Gm=79000.0):
    Dm = D_out - d
    n = Gm * d ** 4 / (8 * Dm ** 3 * k)
    C = Dm / d
    wahl = (4 * C - 1) / (4 * C - 4) + 0.615 / C
    F_max = F_rest + k * s
    tau = 8 * F_max * Dm / (math.pi * d ** 3) * wahl
    return dict(k=k, n=n, d=d, D_out=D_out, F_rest=F_rest, F_max=F_max, pre=F_rest / k, tau=tau,
                solid=(n + 2) * d)


# ------------------------------------------------------------------ key mass model
def key_mass(length, tail_w, head=True, H=20.0, extra=0.0, y0=None, holes=()):
    """hollow PETG key: top skin + side/front/rear walls + transverse ribs (+ extra mm^3)."""
    s, w, r = L["skin"], L["wall"], L["rib"]
    hl = L["head"]
    parts = []   # (volume, y_centroid)
    if head:
        hw = 22.5
        parts.append((hl * hw * s + (2 * hl + hw) * (H - s) * w, hl / 2))
        y0 = hl
        parts.append((((hw - tail_w)) * (H - s) * w, hl))
    else:
        y0 = y0 if y0 is not None else hl
        parts.append((tail_w * (H - s) * w, y0))
    tl = length - y0
    parts.append((tl * tail_w * s + 2 * tl * (H - s) * w + tail_w * (H - s) * w, y0 + tl / 2))
    nrib = int(tl / 30)
    parts.append((nrib * (tail_w - 2 * w) * (H - s) * r, y0 + tl / 2))
    for v, yc in extra if isinstance(extra, (list, tuple)) else [(extra, length / 2)]:
        parts.append((v, yc))
    V = sum(p[0] for p in parts)
    com = sum(p[0] * p[1] for p in parts) / V
    m = V * L["rho_petg"] / 1000
    # radius of gyration about own COM ~ uniform bar of length `length`
    I_com = m * (length ** 2) / 12
    return dict(m=m, com=com, V=V, I_com=I_com)


def black_raised(H0=None):
    """mass/volume of the raised black body (hollow, ~50 % infill incl. walls)."""
    y0, y1 = L["head"], L["black_end"]
    Lr = y1 - y0
    v = Lr * (L["Bw"] + L["Bt"]) / 2 * L["black_h"] * 0.5
    return v, (y0 + y1) / 2


def white_black_mass(length, H=20.0, extra=(), extra_b=None):
    """extra: [(mm^3, y)] added to both keys; extra_b (if given) replaces it for the black key."""
    wk = key_mass(length, TAILS["fb_w"], True, H, list(extra))
    rv, ry = black_raised()
    eb = list(extra if extra_b is None else extra_b)
    bk = key_mass(length, TAILS["black_w"], False, H, eb + [(rv, ry)], y0=L["head"])
    return wk, bk


def key_interior(black):
    """clear width between the key side walls (x) on the mass-model basis (white = F–B tail)."""
    return (TAILS["black_w"] if black else TAILS["fb_w"]) - 2 * L["wall"]


def min_key_pitch():
    """smallest centre-to-centre spacing of neighbouring key tails (x), octave wrap included."""
    xs = [k["cx"] for k in KEYS] + [KEYS[0]["cx"] + 7 * L["Pw"]]
    return min(b - a for a, b in zip(xs, xs[1:]))


def common_levels(M, H, z_bot):
    M["H"] = H
    M["z_bot"] = z_bot
    M["z_top"] = z_bot + H
    M["z_black"] = M["z_top"] + L["black_h"]
    M["slip_top"] = M["z_top"] - 14.5
    M["lid_bot"] = M["z_top"] + L["felt"] - 0.3   # felt lightly pre-compressed at rest
    return M


def front_rail(M):
    """down-stop heights: white front dips L.dip, black front top edge dips L.black_dip."""
    piv, th = M["pivot"], M["theta"]
    bp = (L["head"] + L["black_chamfer"], M["z_top"] + L["black_h"])
    lo, hi = 0.0, 0.2
    for _ in range(60):
        mm = (lo + hi) / 2
        if bp[1] - rot(bp, piv, mm)[1] < L["black_dip"]:
            lo = mm
        else:
            hi = mm
    M["theta_b"] = thb = (lo + hi) / 2
    fw = rot((M["guide_w_y"], M["z_bot"]), piv, th)[1]
    fb = rot((M["stop_b_y"], M["z_bot"]), piv, thb)[1]
    felt_c = L["felt"] - L["felt_comp"]
    M["rail_w_top"] = fw - felt_c
    M["rail_b_top"] = fb - felt_c
    M["black_dip"] = L["black_dip"]
    M["t110"] = M["z_bot"] - rot((L["y_sensor"], M["z_bot"]), piv, th)[1]
    M["t110_b"] = M["z_bot"] - rot((L["y_sensor"], M["z_bot"]), piv, thb)[1]
    return M


def _line_z(a, b, y):
    """z of the straight line through a=(y,z), b=(y,z) at y."""
    return a[1] + (b[1] - a[1]) * (y - a[0]) / (b[0] - a[0])


def guide(M, pin_len):
    """guide pin (pressed L.pin_depth into the keybed) + the key's guide slot.

    The slot depth (from the key underside) is the smallest whole mm that keeps the slot
    ceiling >= L.slot_clear above the pin tip at full dip, for the white key (guide_w_y, theta)
    and the black key (guide_b_y, theta_b). The ceiling is rotated exactly about the key pivot."""
    M["pin_len"] = pin_len
    M["pin_top"] = pin_len - L["pin_depth"]
    zb, piv, h, r = M["z_bot"], M["pivot"], L["slot_len"] / 2, L["pin_d"] / 2
    states = ((M["guide_w_y"], M["theta"]), (M["guide_b_y"], M["theta_b"]))

    def clear(depth, gy, th):
        a = rot((gy - h, zb + depth), piv, th)
        b = rot((gy + h, zb + depth), piv, th)
        return min(_line_z(a, b, y) - M["pin_top"] for y in (gy - r, gy + r))

    need = 0.0
    for gy, th in states:
        lo, hi = 0.0, M["H"]
        for _ in range(60):
            mid = (lo + hi) / 2
            if clear(mid, gy, th) >= L["slot_clear"]:
                hi = mid
            else:
                lo = mid
        need = max(need, hi)
    M["slot_depth"] = float(math.ceil(need - 1e-6))
    M["slot_margin"] = min(clear(M["slot_depth"], gy, th) for gy, th in states)
    assert M["pin_top"] > zb, "guide pin must reach into the key at rest"
    assert M["slot_depth"] <= M["H"] - L["skin"], "guide slot deeper than the guide boss"
    return M


def black_magnet(M):
    """black keys travel further at y=110: recess their magnet so the closest gap equals g_min."""
    gdn_b = M["g_up"] - M["t110_b"]
    M["mag_recess_b"] = max(0.0, round(L["g_min"] - gdn_b + 0.049, 1))
    M["g_dn_b"] = gdn_b + M["mag_recess_b"]
    M["g_up_b"] = M["g_up"] + M["mag_recess_b"]
    return M


STOCK_SPRING = dict(model="MISUMI C-UR6-25", k=0.29, L0=25.0, d=0.5, D_out=6.0)


def stock_spring(M, wk, bk, ys, Mf=0.0):
    """size the install length of the stock spring so the white front reads BW_rest at rest."""
    SP = STOCK_SPRING
    py = M["pivot"][0]
    a = py - ys
    th = M["theta"]
    Mg = wk["m"] * G * (py - wk["com"])
    F0 = (L["BW_rest"] * G * py + Mg) / a
    k = SP["k"]
    M["spring_y"] = ys
    M["spring"] = spring_from_k(k, F0, a * th, d=SP["d"], D_out=SP["D_out"])
    M["spring"]["model"] = SP["model"]
    M["spring"]["L0"] = SP["L0"]
    M["spring_Lrest"] = SP["L0"] - M["spring"]["pre"]
    M["spring_Lbot"] = M["spring_Lrest"] - a * th
    M["BW_bottom_calc"] = L["BW_rest"] + (k * a * a * th + Mf) / (G * py)
    M["Mg"] = Mg
    M["pocket_depth"] = 5.0
    M["post_top"] = M["z_bot"] + M["pocket_depth"] - M["spring_Lrest"]
    black_spring(M, bk, a, k)
    return a, Mg


def black_spring(M, bk, a, k):
    """same spring on black keys: preload reduced with the M3 adjuster so the black front reads BW_rest."""
    py = M["pivot"][0]
    lever = py - L["head"]
    Mg_b = bk["m"] * G * (py - bk["com"])
    F_b = (L["BW_rest"] * G * lever + Mg_b) / a
    M["black_pre"] = F_b / k
    M["black_adj"] = M["spring"]["pre"] - M["black_pre"]
    M["BW_black_same"] = (M["spring"]["F_rest"] * a - Mg_b) / lever / G


# ------------------------------------------------------------------ methods
def method_A():
    M = dict(id="A", name="콤 플렉서", short="옥타브 일체 콤 + 탄성 힌지 + 스프링")
    M["body_end"], M["leaf"], M["leaf_t"], M["spine"] = 222.0, 18.0, 1.2, (240.0, 252.0)
    common_levels(M, 20.0, 16.5)
    M["pivot"] = (M["body_end"] + M["leaf"] / 2, M["z_bot"] + M["leaf_t"] / 2)
    M["theta"] = solve_theta(M["pivot"], M["z_top"], L["dip"])
    M["guide_w_y"], M["guide_b_y"], M["stop_b_y"] = 18.0, 62.0, 62.0
    M["sensor_top"] = 8.0
    front_rail(M)
    guide(M, 30.0)
    M["g_up"] = M["z_bot"] - M["sensor_top"]
    M["g_dn"] = M["g_up"] - M["t110"]
    black_magnet(M)
    M["blk"] = (M["spine"][0], M["spine"][1] + 4.0)   # spine support block (y), printed, z 0..z_bot; starts at the spine so the leaf stays free
    # masses
    ext = [(1300, 110), (900, 18), (1200, 190)]
    wk, bk = white_black_mass(M["body_end"], 20.0, ext)
    M["wk"], M["bk"] = wk, bk
    # spring + flexure
    th = M["theta"]
    I = TAILS["fb_w"] * M["leaf_t"] ** 3 / 12
    kf = L["E_petg"] * I / M["leaf"]
    Mf = kf * th
    a, Mg = stock_spring(M, wk, bk, 190.0, Mf)
    M["BW_bottom_A"] = M["BW_bottom_calc"]
    M["flex"] = dict(I=I, kf=kf, Mf=Mf, Mf_front_g=Mf / M["pivot"][0] / G,
                     strain=th * M["leaf_t"] / (2 * M["leaf"]))
    M["flex"]["stress_bend"] = L["E_petg"] * M["flex"]["strain"]
    M["upstop_y"] = (158.0, 178.0)
    M["m_eff"] = (wk["I_com"] + wk["m"] * (M["pivot"][0] - wk["com"]) ** 2) / M["pivot"][0] ** 2
    # standing load on the leaf at rest (key held against the up-stop at y=168)
    ystop = sum(M["upstop_y"]) / 2
    R = (M["spring"]["F_rest"] * a - Mg) / (M["pivot"][0] - ystop)
    V = M["spring"]["F_rest"] - wk["m"] * G - R
    Mleaf = abs(V) * M["leaf"] / 2
    M["flex"]["V_rest"] = V
    M["flex"]["sigma_rest"] = 6 * Mleaf / (TAILS["fb_w"] * M["leaf_t"] ** 2)
    M["depth"] = 252.0
    return M


def method_B():
    M = dict(id="B", name="샤프트 힌지", short="개별 키 + Ø4 강철 샤프트 + 스프링")
    M["body_end"] = 248.0
    common_levels(M, 20.0, 16.5)
    M["pivot"] = (238.0, M["z_bot"] + 10.0)
    M["shaft_d"], M["hole_d"] = 4.0, 4.3
    M["theta"] = solve_theta(M["pivot"], M["z_top"], L["dip"])
    M["guide_w_y"], M["guide_b_y"], M["stop_b_y"] = 18.0, 62.0, 62.0
    M["sensor_top"] = 8.0
    front_rail(M)
    guide(M, 30.0)
    M["g_up"] = M["z_bot"] - M["sensor_top"]
    M["g_dn"] = M["g_up"] - M["t110"]
    black_magnet(M)
    ext = [(1300, 110), (900, 18), (1200, 190), (1500, 238)]
    wk, bk = white_black_mass(M["body_end"], 20.0, ext)
    M["wk"], M["bk"] = wk, bk
    a, Mg = stock_spring(M, wk, bk, 190.0)
    M["BW_bottom_A"] = M["BW_bottom_calc"]
    M["comb"] = (229.0, 247.0)
    M["fin_t"] = L["fin_t"]
    M["eyelet_y"] = 226.0                 # the key narrows to the eyelet (slot - fin_t - 2 eye_cl) behind here
    assert M["eyelet_y"] < M["comb"][0] < M["pivot"][0] < M["comb"][1] < M["body_end"]
    M["upstop_y"] = (158.0, 178.0)
    M["m_eff"] = (wk["I_com"] + wk["m"] * (M["pivot"][0] - wk["com"]) ** 2) / M["pivot"][0] ** 2
    # shaft deflection between fins (worst span = C–E slot)
    E, d = 200000.0, M["shaft_d"]
    I = math.pi * d ** 4 / 64
    Fk = M["spring"]["F_max"] - L["BW_rest"] * G       # reaction at shaft ~ spring force
    span = TAILS["ce"]
    M["shaft_defl"] = Fk * span ** 3 / (48 * E * I)
    M["depth"] = 248.0
    return M


def method_C():
    M = dict(id="C", name="밸런스 핀 시소", short="2피스 롱키 + 밸런스 핀 + 강철 카운터웨이트")
    M["front_part"], M["rear_part"] = (0.0, 240.0), (220.0, 372.0)
    M["body_end"] = 372.0
    common_levels(M, 20.0, 16.0)
    M["lid_bot"] = M["z_top"] + L["felt"] + 1.0      # transport guard only: 1 mm clear at rest
    M["upstop_y"] = (158.0, 178.0)
    M["pivot"] = (212.0, M["z_bot"])
    M["theta"] = solve_theta(M["pivot"], M["z_top"], L["dip"])
    M["guide_w_y"], M["guide_b_y"], M["stop_b_y"] = 18.0, 62.0, 62.0
    M["sensor_top"] = 8.0
    front_rail(M)
    guide(M, 30.0)
    M["g_up"] = M["z_bot"] - M["sensor_top"]
    M["g_dn"] = M["g_up"] - M["t110"]
    black_magnet(M)
    # balance pin (catalog Ø4×40): pressed `embed` into the keybed like the guide pins; tip ends in the key mortise
    M["bal_pin"] = dict(d=4.0, len=40.0, embed=L["pin_depth"])
    H, piv = M["H"], M["pivot"]
    # upper mortise (width across x, length along y, key-local z from..to): holds the pin tip sideways
    M["bal_mortise"] = (4.2, 9.0, H - 6.0, H - L["skin"])
    mw, ml, mz0, mz1 = M["bal_mortise"]
    _tip = M["bal_pin"]["len"] - M["bal_pin"]["embed"] - M["z_bot"]
    assert mz0 < _tip < mz1, "balance pin tip must end inside the mortise"
    # lower round hole (key-local z 0..mz0): the key rocks about the pin axis at its underside, so the hole
    # wall at height h moves by ~h*sin(theta) toward the pin; size the hole (0.5 mm steps) so it keeps
    # bal_margin radial clearance at the hole top at full dip, white and black (exact rotation checked below)
    bal_margin = 0.2
    rp = M["bal_pin"]["d"] / 2
    ths = (M["theta"], M["theta_b"])
    r_need = max((rp + bal_margin + mz0 * math.sin(t)) / math.cos(t) for t in ths)
    M["bal_hole_d"] = math.ceil(2 * r_need * 2 - 1e-9) / 2

    def pin_gap(r, h, th):
        """clearance between the rear hole/mortise wall (radius or half length r) at height h and the pin."""
        return rot((piv[0] + r, piv[1] + h), piv, th)[0] - (piv[0] + rp)
    M["bal_hole_clear"] = min(pin_gap(M["bal_hole_d"] / 2, h, t) for t in ths for h in (0.0, mz0))
    assert M["bal_hole_clear"] >= bal_margin - 1e-9, "balance hole binds on the pin at full dip"
    assert min(pin_gap(ml / 2, h, t) for t in ths for h in (mz0, min(_tip, mz1))) > 0, "mortise binds on the pin"
    # solid balance block, wall to wall, around the hole and mortise (2 mm end walls); ends before the lap joint
    M["bal_boss"] = (piv[0] - (ml / 2 + 2.0), piv[0] + (ml / 2 + 2.0))
    assert M["bal_boss"][1] < M["rear_part"][0], "balance block runs into the lap joint"
    assert M["bal_hole_d"] / 2 < ml / 2 + 2.0

    def bal_block_v(black):
        b0, b1 = M["bal_boss"]
        return ((b1 - b0) * key_interior(black) * (H - L["skin"]) - math.pi * (M["bal_hole_d"] / 2) ** 2 * mz0
                - mw * ml * (mz1 - mz0))
    # balance-rail felt punchings, one per key on the y=212 line: largest 0.5 mm step that leaves punch_gap
    M["punch_d"] = math.floor((min_key_pitch() - L["punch_gap"]) * 2 + 1e-9) / 2
    assert M["punch_d"] >= M["bal_hole_d"] + 2.0, "punching leaves no felt ring around the key's balance hole"
    ext0 = [(1300, 110), (900, 18), (1200, 230)]
    ext = ext0 + [(bal_block_v(False), piv[0])]
    ext_b = ext0 + [(bal_block_v(True), piv[0])]
    wk, bk = white_black_mass(M["body_end"], 20.0, ext, ext_b)
    M["wk"], M["bk"] = wk, bk
    py = M["pivot"][0]
    # moments about pivot (g*mm): +ve lifts the front
    # split key mass into front / rear of pivot using a uniform-per-length approx around COM
    M_key = wk["m"] * (wk["com"] - py)          # negative (front heavy)
    cw_c = 343.0                                # counterweight centre
    arm = cw_c - py
    m_cw = (L["BW_grav"] * py - M_key) / arm
    M["cw_c"], M["cw_arm"], M["m_cw"] = cw_c, arm, m_cw
    bar_g_per_mm = 9 * 25 * L["rho_steel"] / 1000
    lever_b = py - L["head"]
    M_key_b = bk["m"] * (bk["com"] - py)
    M["m_cw_b"] = (L["BW_grav"] * lever_b - M_key_b) / arm
    M["cw_len_b"] = round(M["m_cw_b"] / bar_g_per_mm)
    M["cw_len"] = round(m_cw / bar_g_per_mm)
    M["m_cw_actual"] = M["cw_len"] * bar_g_per_mm
    M["cw_bar"] = "9 × 25 평철"
    M["cw_z"] = (M["z_bot"] - 7.0, M["z_bot"] - 7.0 + 25.0)
    M["backrail_top"] = M["cw_z"][0] - (L["felt"] - 0.3)
    M["balrail_top"] = M["z_bot"] - (L["felt"] - L["felt_comp"])
    I_piv = wk["I_com"] + wk["m"] * (py - wk["com"]) ** 2 + m_cw * arm ** 2
    M["m_eff"] = I_piv / py ** 2
    M["DW"] = L["BW_grav"] + L["friction"]
    M["UW"] = L["BW_grav"] - L["friction"]
    M["rear_rise"] = M["theta"] * (M["body_end"] - py)
    # transport-guard lid at lid_bot only as far back as the pressed key top (white theta, black theta_b)
    # stays lid_clear below it; behind lid_end a raised rear cover (underside rear_cover_z) clears the
    # rising key rear end and counterweight corner (exact rotation about the balance pin)
    lid_clear, zt, piv = 1.0, M["z_top"], M["pivot"]
    states = ((M["theta"], M["cw_len"]), (M["theta_b"], M["cw_len_b"]))
    M["rear_top"] = max(rot((M["body_end"], zt), piv, th)[1] for th, _ in states)
    M["cw_top_dn"] = max(rot((M["cw_c"] + n / 2, M["cw_z"][1]), piv, th)[1] for th, n in states)
    ends = []
    for th, _ in states:
        a, b = rot((0.0, zt), piv, th), rot((M["body_end"], zt), piv, th)
        ends.append(a[0] + (M["lid_bot"] - lid_clear - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
    M["lid_end"] = float(math.floor(min(ends)))                       # whole mm, toward the front
    M["rear_cover_z"] = math.ceil((max(M["rear_top"], M["cw_top_dn"]) + lid_clear) * 2 - 1e-6) / 2   # 0.5 mm steps
    for th, _ in states:
        a, b = rot((0.0, zt), piv, th), rot((M["body_end"], zt), piv, th)
        assert _line_z(a, b, M["lid_end"]) <= M["lid_bot"] - lid_clear + 1e-9, "pressed key top hits the lid"
    assert M["upstop_y"][1] < M["lid_end"] < M["body_end"], "lid must still carry the up-stop felt"
    assert M["rear_cover_z"] >= M["rear_top"] + lid_clear and M["rear_cover_z"] >= M["cw_top_dn"] + lid_clear
    M["depth"] = 372.0
    return M


def hammer_top(M, h_theta=0.0, black=False):
    """top profile of the hammer (beam top, then weight top) rotated by h_theta about h_pivot."""
    c0, c1 = M["h_cradle_b"] if black else M["h_cradle"]
    pts = [(M["h_front"], M["h_top"]), (c0, M["h_top"]), (c0, M["h_w_z"][1]), (c1, M["h_w_z"][1])]
    return [rot(p, M["h_pivot"], h_theta) for p in pts]


def hammer_parts(M, black=False):
    """shared D hammer geometry (world y, z at rest): PETG beam, PETG cradle around the steel bar, the bar,
    the two M3 countersunk screws (rects y0, z0, w, h) that go up from the cradle floor into the bar,
    and their 90° countersinks in the cradle floor (csk: polygons, head Ø at the floor underside)."""
    y0, ch = M["h_front"], M["h_chamfer"]
    hu, ht = M["h_under"], M["h_top"]
    c0, c1 = M["h_cradle_b"] if black else M["h_cradle"]
    w0, w1 = M["h_weight_b"] if black else M["h_weight"]
    cz0, cz1 = M["h_cradle_z"]
    wz0, wz1 = M["h_w_z"]
    beam = [(y0, hu + ch), (y0 + 2 * ch, hu), (c0, hu), (c0, ht), (y0, ht)]
    cradle = [(c0, cz0), (c1, cz0), (c1, cz1), (c0, cz1)]
    bar = [(w0, wz0), (w1, wz0), (w1, wz1), (w0, wz1)]
    sy = M["h_screw_y_b"] if black else M["h_screw_y"]
    screws = [(y - 1.5, cz0, 3.0, M["h_ct"] + 6.0) for y in sy]
    hd, cd = M["h_csk"]
    ri = hd / 2 - cd                                   # 90° cone: hole radius at the top of the countersink
    csk = [[(y - hd / 2, cz0), (y + hd / 2, cz0), (y + ri, cz0 + cd), (y - ri, cz0 + cd)] for y in sy]
    return dict(beam=beam, cradle=cradle, bar=bar, screws=screws, csk=csk)


def _poly_z(poly, y):
    """highest z of a polyline at y (None when y is outside it)."""
    zs = []
    for a, b in zip(poly, poly[1:]):
        lo, hi = min(a[0], b[0]), max(a[0], b[0])
        if lo - 1e-9 <= y <= hi + 1e-9:
            zs.append(max(a[1], b[1]) if hi - lo < 1e-9 else _line_z(a, b, y))
    return max(zs) if zs else None


def key_ceiling(M, y, th):
    """z of the key's inner ceiling (underside of the top skin) at world y, key rotated by th."""
    zs = M["z_top"] - L["skin"]
    return _line_z(rot((0.0, zs), M["pivot"], th), rot((M["body_end"], zs), M["pivot"], th), y)


def rib_z0(M, y):
    """height of a transverse rib's lower edge above the key underside at key-local y.

    Default L.rib_z0; in method D a rib over the hammer is shortened so that at full dip
    (white and black) its lower edge stays >= L.rib_clear above the rising hammer (exact rotation).
    Returns None when not even a stub rib fits (the rib must be left out)."""
    z_def = L["rib_z0"]
    if M["id"] != "D":
        return z_def
    states = ((M["theta"], M["h_theta"], False), (M["theta_b"], M["h_theta_b"], True))

    def clear(z0):
        c = math.inf
        for th, hth, blk in states:
            top = hammer_top(M, hth, blk)
            a = rot((y - L["rib"] / 2, M["z_bot"] + z0), M["pivot"], th)
            b = rot((y + L["rib"] / 2, M["z_bot"] + z0), M["pivot"], th)
            ys = [a[0], b[0]] + [p[0] for p in top if a[0] < p[0] < b[0]]
            for yy in ys:
                zt = _poly_z(top, yy)
                if zt is not None:
                    c = min(c, _line_z(a, b, yy) - zt)
        return c

    if clear(z_def) >= L["rib_clear"]:
        return z_def
    lo, hi = z_def, M["H"] - L["skin"] - 1.0
    if clear(hi) < L["rib_clear"]:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if clear(mid) >= L["rib_clear"]:
            hi = mid
        else:
            lo = mid
    return math.ceil(hi * 2 - 1e-6) / 2          # round up to 0.5 mm


class RibZ0(dict):
    """M['rib_z0'][y] -> rib lower edge above the key underside (computed on demand)."""
    def __init__(self, M):
        super().__init__()
        self.M = M

    def __missing__(self, y):
        z = rib_z0(self.M, y)
        self[y] = z
        return z

    def get(self, y, default=None):
        return self[y]


def _method_D(H, zb=24.5):
    M = dict(id="D", name="해머 액션", short="키 + 가중 해머 레버(GHS 방식)")
    M["body_end"] = 248.0
    common_levels(M, H, zb)
    M["pivot"] = (238.0, M["z_bot"] + 13.0)
    M["theta"] = solve_theta(M["pivot"], M["z_top"], L["dip"])
    M["guide_w_y"], M["guide_b_y"], M["stop_b_y"] = 18.0, 54.0, 54.0
    M["sensor_top"] = 8.0
    M["srail"] = (102.0, 126.0)
    front_rail(M)
    # guide pin: tip >= 6 mm into the key at rest, length rounded up to a 5 mm catalog step
    guide(M, 5.0 * math.ceil((zb + 6.0 + L["pin_depth"]) / 5.0))
    # hammer
    hp = (95.0, 16.0)           # hammer pivot (y, z)
    M["h_pivot"] = hp
    M["h_shaft_d"] = 3.0
    M["h_hole_d"] = M["h_shaft_d"] + 0.3
    M["h_push"] = 66.0
    M["h_front"] = 60.0
    M["h_chamfer"] = 4.0         # front lower chamfer of the beam
    M["h_under"] = 11.0          # hammer underside at rest (flat beam)
    M["h_top"] = 21.0
    # actuator: pad under the key (top act_len long, 6 long at the bottom, 6 wide) reaching down to the
    # 2 mm felt on the hammer top at h_push, hung from a wall-to-wall boss inside the key (underside..skin)
    M["act_len"] = 10.0
    M["act_boss"] = (M["h_push"] - M["act_len"] / 2, M["h_push"] + M["act_len"] / 2)
    M["h_act"] = M["z_bot"] - (M["h_top"] + 2.0)
    w1 = 186.0                   # rear end of the hammer = rear end of the weight (white and black)
    M["h_w_z"] = (6.0, 25.0)     # steel 6 x 19 flat bar on edge
    M["w_bar"] = "6 × 19 평철"
    bar_t = 6.0                                   # bar thickness (across x)
    gpm = bar_t * 19 * L["rho_steel"] / 1000      # g per mm of bar
    ct = M["h_ct"] = 2.0                          # printed cradle: floor and end-wall thickness
    # the cradle rises into the key: its width fits the narrowest key interior (black) with 0.3 mm per side
    M["h_cradle_w"] = round(TAILS["black_w"] - 2 * L["wall"] - 2 * 0.3, 2)
    cs = (M["h_cradle_w"] - bar_t) / 2            # cradle side-wall thickness
    assert cs >= 0.8, "cradle side walls around the steel bar too thin"
    wz0_, wz1_ = M["h_w_z"]
    piv, zb, py = M["pivot"], M["z_bot"], M["pivot"][0]

    def h_angle(th):
        drop = zb - rot((M["h_push"], zb), piv, th)[1]
        return drop, math.asin(drop / (hp[0] - M["h_push"]))

    M["push_drop"], M["h_theta"] = h_angle(M["theta"])
    _, M["h_theta_b"] = h_angle(M["theta_b"])
    # magnet face centre (y_sensor, h_under) rotated exactly about the hammer pivot
    M["t110"] = rot((L["y_sensor"], M["h_under"]), hp, M["h_theta"])[1] - M["h_under"]
    M["t110_hb"] = rot((L["y_sensor"], M["h_under"]), hp, M["h_theta_b"])[1] - M["h_under"]
    M["g_up"] = M["h_under"] - M["sensor_top"]       # closest at REST
    M["g_dn"] = M["g_up"] + M["t110"]                 # farther when pressed
    def act_v(black):
        """actuator pad (trapezoid act_len/6 long, 6 wide, h_act tall) + its wall-to-wall boss in the key."""
        pad = (M["act_len"] + 6.0) / 2 * M["h_act"] * 6.0
        return pad + M["act_len"] * key_interior(black) * (H - L["skin"])
    ext0 = [(900, 18), (1500, 238)]
    wk, bk = white_black_mass(M["body_end"], H, ext0 + [(act_v(False), M["h_push"])],
                              ext0 + [(act_v(True), M["h_push"])])
    M["wk"], M["bk"] = wk, bk
    # required force at the push point (g) so the key front rests with BW_grav up-force
    F_push = (L["BW_grav"] * py + wk["m"] * (py - wk["com"])) / (py - M["h_push"])
    F_push_b = (L["BW_grav"] * (py - L["head"]) + bk["m"] * (py - bk["com"])) / (py - M["h_push"])

    def weight(F):
        """hammer = PETG beam (8 x 10, 55 % solid) from h_front to the weight + steel bar ending at w1.
        Fixed point: bar length -> arm -> required mass -> rounded bar length."""
        wl = 40
        for _ in range(40):
            w0 = w1 - wl
            beam_len = (w0 - ct) - M["h_front"]
            beam_m = 8 * 10 * beam_len * 0.55 * L["rho_petg"] / 1000
            beam_c = (M["h_front"] + w0 - ct) / 2
            arm = (w0 + w1) / 2 - hp[0]
            # PETG cradle around the bar: floor + 2 side walls (cs) + 2 end walls, ~90 % solid
            cl, cw, ch = wl + 2 * ct, M["h_cradle_w"], (wz1_ - wz0_) + ct
            cradle_m = (cl * cw * ct + 2 * cl * cs * (wz1_ - wz0_) + 2 * ct * cw * ch) * 0.9 * L["rho_petg"] / 1000
            m = (F * (hp[0] - M["h_push"]) - beam_m * (beam_c - hp[0]) - cradle_m * arm) / arm
            wl_new = round(m / gpm)
            if wl_new == wl:
                break
            wl = wl_new
        return dict(w_len=wl, m=m, arm=arm, beam_len=beam_len, beam_m=beam_m, beam_c=beam_c, cradle_m=cradle_m)

    Wt, Wb = weight(F_push), weight(F_push_b)
    M["F_push"], M["F_push_b"] = F_push, F_push_b
    M["w_len"], M["w_len_b"] = Wt["w_len"], Wb["w_len"]
    M["h_weight"] = (w1 - Wt["w_len"], w1)
    M["h_weight_b"] = (w1 - Wb["w_len"], w1)
    M["h_cradle"] = (M["h_weight"][0] - ct, w1 + ct)          # printed cradle (hammer rear part), white key
    M["h_cradle_b"] = (M["h_weight_b"][0] - ct, w1 + ct)
    M["h_cradle_z"] = (wz0_ - ct, wz1_)
    M["h_screw_y"] = (M["h_weight"][0] + 8.0, w1 - 8.0)       # 2 x M3 from the cradle floor into the bar (tapped 6 deep)
    M["h_screw_y_b"] = (M["h_weight_b"][0] + 8.0, w1 - 8.0)
    M["h_screw"] = "M3×8 접시머리"
    # 90° countersink in the cradle floor: head Ø6.3 (ISO 10642 M3) -> Ø3.4 clearance hole, so the head
    # sits flush with the floor underside and stays clear of the rest felt 1 mm below
    M["h_csk"] = (6.3, round((6.3 - 3.4) / 2, 2))
    assert M["h_csk"][1] < ct, "countersink deeper than the cradle floor"
    # rest felt under the cradle floor, 1 mm below it at rest (printed pad only if needed)
    M["h_rest"] = (M["h_weight"][0] + 4.0, w1 - 4.0)
    M["h_rest_top"] = M["h_cradle_z"][0] - 1.0
    M["h_rest_pad"] = max(0.0, M["h_rest_top"] - L["felt"])
    M["cradle_m"] = Wt["cradle_m"]
    # rib-free window in the key over the rising cradle, in key-local y: the cradle corners at rest and at
    # full dip (hammer rotated about h_pivot, then taken into the pressed key's frame), 4 mm margin each side
    def window(cr, th, hth):
        ys = [cr[0], cr[1]]
        for p in [(y, z) for y in cr for z in M["h_cradle_z"]]:
            ys.append(rot(rot(p, hp, hth), piv, -th)[0])
        return (float(math.floor(min(ys) - 4.0)), float(math.ceil(max(ys) + 4.0)))
    M["h_window"] = window(M["h_cradle"], M["theta"], M["h_theta"])
    M["h_window_b"] = window(M["h_cradle_b"], M["theta_b"], M["h_theta_b"])
    M["m_w"], M["m_w_b"] = Wt["m"], Wb["m"]                  # required steel mass at the final arm
    M["m_w_actual"], M["m_w_b_actual"] = Wt["w_len"] * gpm, Wb["w_len"] * gpm
    M["w_arm"], M["w_arm_b"] = Wt["arm"], Wb["arm"]
    M["beam_m"] = Wt["beam_m"]
    ratio = (py - M["h_push"]) / (hp[0] - M["h_push"])      # hammer ang. vel / key ang. vel
    I_h = Wt["m"] * Wt["arm"] ** 2 + Wt["beam_m"] * (Wt["beam_len"] ** 2 / 12 + (Wt["beam_c"] - hp[0]) ** 2)
    I_k = wk["I_com"] + wk["m"] * (py - wk["com"]) ** 2
    M["m_eff"] = (I_k + I_h * ratio ** 2) / py ** 2
    M["ratio"] = ratio
    M["DW"] = L["BW_grav"] + L["friction"]
    M["UW"] = L["BW_grav"] - L["friction"]
    # weight rise (centre of the top face) and exact clearance at full dip:
    # both top corners of the weight (rotated about the hammer pivot) vs the rotated key ceiling
    wz1 = M["h_w_z"][1]

    def rise_clear(wr, th, hth):
        """rise of the bar top centre; clearance of the highest cradle/bar corners vs the key ceiling."""
        rise = rot(((wr[0] + wr[1]) / 2, wz1), hp, hth)[1] - wz1
        clear = min(key_ceiling(M, p[0], th) - p[1] for p in (rot((wr[0], wz1), hp, hth), rot((wr[1], wz1), hp, hth)))
        return rise, clear

    M["w_rise"], M["w_clear"] = rise_clear(M["h_cradle"], M["theta"], M["h_theta"])
    M["w_rise_b"], M["w_clear_b"] = rise_clear(M["h_cradle_b"], M["theta_b"], M["h_theta_b"])
    M["comb"] = (229.0, 247.0)
    M["fin_t"] = L["fin_t"]
    M["eyelet_y"] = 226.0                 # the key narrows to the eyelet (slot - fin_t - 2 eye_cl) behind here
    assert M["eyelet_y"] < M["comb"][0] < M["pivot"][0] < M["comb"][1] < M["body_end"]
    M["h_comb"] = (89.0, 101.0)
    M["h_comb_top"] = hp[1] + 5.0
    # beam width: slot - 3.4 from h_front to the hammer comb's rear end h_comb[1]; behind it the beam enters
    # the key cavity when pressed -> h_rear_w (= cradle width, fits the narrowest key interior)
    M["h_rear_w"] = M["h_cradle_w"]
    assert M["h_rear_w"] <= key_interior(True) - 2 * 0.3 + 1e-9, "rear beam wider than the black key interior"
    assert (M["h_rear_w"] - 6.2) / 2 >= 0.7, "hammer magnet pocket (Ø6.2) walls too thin in the rear beam"
    # the key walls must clear everything under them that is wider than the key interior:
    # the comb fins (top h_comb_top) and the wide beam/eyelet from the front to the comb's rear end
    def under_clear(th, hth):
        worst = 1e9
        y = M["h_front"]
        while y <= M["h_comb"][1] + 1e-9:
            key_u = rot((y, M["z_bot"]), piv, th)[1]
            if y <= M["act_boss"][1]:               # actuator zone: the pad sits between key and hammer
                y += 0.5
                continue
            beam_t = rot((y, M["h_top"]), hp, hth)[1] + (2.0 if abs(y - M["h_push"]) <= 4 else 0.0)
            top = max(beam_t, M["h_comb_top"] if M["h_comb"][0] <= y <= M["h_comb"][1] else -1e9)
            worst = min(worst, key_u - top)
            y += 0.5
        return worst
    M["under_clear"] = under_clear(M["theta"], M["h_theta"])
    M["under_clear_b"] = under_clear(M["theta_b"], M["h_theta_b"])
    M["upstop_y"] = (196.0, 214.0)
    M["depth"] = 248.0
    M["rib_z0"] = RibZ0(M)
    return M


def method_D():
    """key base z_bot and key height H for the hammer action, chosen to give the LOWEST key top (z_bot + H)
    such that, at full dip for white AND black keys,
      - the rising hammer weight/cradle stays >= L.w_clear_min below the key ceiling, and
      - the key walls stay >= 1.0 mm above the hammer comb fins and the wide front beam."""
    best = None
    zb = 24.5
    while zb <= 40.0:
        H = 22.0
        while H <= 40.0:
            try:
                M = _method_D(H, zb)
            except AssertionError:           # e.g. guide slot deeper than the boss at this H
                H += 0.5
                continue
            if (min(M["w_clear"], M["w_clear_b"]) >= L["w_clear_min"]
                    and min(M["under_clear"], M["under_clear_b"]) >= 1.0):
                if best is None or M["z_top"] < best["z_top"] - 1e-9:
                    best = M
                break                       # larger H only raises the key top
            H += 0.5
        zb += 0.5
    assert best is not None, "no key height/base gives the hammer enough clearance"
    return best


METHODS = [method_A(), method_B(), method_C(), method_D()]
for _M in METHODS:
    _M.setdefault("rib_z0", RibZ0(_M))      # rib lower edge per key-local y (L.rib_z0 except over the D hammer)

if __name__ == "__main__":
    print(TAILS)
    for M in METHODS:
        out = {}
        for k, v in M.items():
            if isinstance(v, float):
                out[k] = round(v, 3)
            elif isinstance(v, dict):
                out[k] = {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()}
            elif isinstance(v, tuple):
                out[k] = tuple(round(x, 2) for x in v)
            else:
                out[k] = v
        print("\n==", M["id"])
        for k, v in out.items():
            print(f"  {k}: {v}")
