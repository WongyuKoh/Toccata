#!/usr/bin/env python3
"""Toccata v4 W1+ (round 4: fix + simplify): run every calculation of model_v4 and write results.txt, metrics.json,
geometry.json and parts_list.json.   Usage: ../venv/bin/python run_all.py"""
import json, math, time, os, multiprocessing as mp
import numpy as np
import model_v4 as m

P = m.P
OUT = os.path.dirname(os.path.abspath(__file__))
T = []
R = {}


def pr(*a):
    s = " ".join(str(x) for x in a)
    T.append(s)
    print(s, flush=True)


def sec(t):
    pr("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


def D(x):
    return math.degrees(x)


t_start = time.time()
g = m.build_geo(P)
keys, lay, caps = g["keys"], g["lay"], g["caps"]
Aw, Ab = g["Aw"], g["Ab"]
# r4.3: the rear shelf is cut over the USB plug -> F / F# rest felts land on part of their width only
RLAND = m.rest_landing(P, g)
LAND_MIN = min(q["frac"] for q in RLAND.values())
LAND_LAB = "rest felt landing (USB slot)"


# ------------------------------------------------------------------ parallel helpers (fork: workers inherit g)
def _dyn_job(args):
    lab, kw = args
    pads = None
    if "pad" in kw:
        gw_, gb_ = kw.get("gap", (P["gap_us_w"], P["gap_us_b"]))
        pads = dict(white=m.PadTable(Aw, g["held_b_w"], gw_, **kw["pad"]),
                    black=m.PadTable(Ab, g["held_b_b"], gb_, **kw["pad"]))
    felt = kw.get("felt")
    full = kw.get("full", False)
    hp = kw.get("holds_play", (None, 0.45, 0.6, 1.0))
    ha = kw.get("holds_abuse", (None, 1.0))
    r = m.dyn_cases(P, g, felt=felt, fmul=kw.get("fmul", 1.0), seat_k=kw.get("seat_k"), vf=kw.get("vf"), pads=pads,
                    holds_play=hp, holds_abuse=ha, full=full, v_play=kw.get("v_play"))
    for col, A in (("white", Aw), ("black", Ab)):
        if kw.get("release", True):
            pad = None if pads is None else pads[col]
            Dm = m.dyn_for(g, A, felt=felt, fmul=kw.get("fmul", 1.0), seat_k=kw.get("seat_k"), vf=kw.get("vf"), pad=pad,
                           mu_lip=kw.get("mu_lip"))
            st = Dm.run(300.0)["state"]
            r[col]["release"] = m.ev_summary(m.release_from_bottom(Dm, st))
            if kw.get("f2"):
                D2 = m.dyn_for(g, A, felt=felt, fmul=2.0, seat_k=kw.get("seat_k"), vf=kw.get("vf"), pad=pad)
                r[col]["release_f2"] = m.ev_summary(m.release_from_bottom(D2, D2.run(300.0)["state"]))
    return lab, r


# r4.1: single-case jobs (speed grids, chord sweeps, end keys, paper-strip holds); workers inherit g / EPG by fork
Fe_ = m.FELT
MATS = dict(nom=dict(pad={}, felt=None, vf=None),
            passline=dict(pad=dict(e_eff=P["pad_e_pass"], E=0.7), felt=dict(Fe_, front=(Fe_["front"][0], m.e_input(0.22)), front_b=(Fe_["front_b"][0], m.e_input(0.22))), vf=None),
            vf01=dict(pad={}, felt=None, vf=0.1),
            pass_vf01=dict(pad=dict(e_eff=P["pad_e_pass"], E=0.7), felt=dict(Fe_, front=(Fe_["front"][0], m.e_input(0.22)), front_b=(Fe_["front_b"][0], m.e_input(0.22))), vf=0.1),
            worst=dict(pad=dict(e_eff=0.10, E=0.7), felt=dict(Fe_, front=(Fe_["front"][0], m.e_input(0.28)), front_b=(Fe_["front_b"][0], m.e_input(0.28))), vf=0.1))
EPG = {}
_PADS, _REST = {}, {}


# r4.4 (R44 issue 2): F / F# with their own key bodies and rest-felt landing (r4.4 felts, and the r4.3 felts for 'before')
# r4.4 circuit cross-check: the 'before' of issue 2 keeps the r4.3 control-board interface (plug face y195.5, r4.3 BRD-01
# positions) so that the fix-1 record stays the r4.3 state; the r4.4 model uses the circuit's grid values
C43 = dict(usb_y=(195.5, 220.5), usb_rcpt=(79.53, 88.47, 188.2, 195.5, 12.9, 16.1), zero_xy=(75.0, 93.0, 172.0, 195.5), mux_xy=(53.3, 71.1, 152.4, 193.0),
           ribbon_pads=(61.59, 79.37, 148.59, 151.13), ext_pads=(95.25, 107.95, 193.04))
P43 = dict(P, rest_felt_cut=False, rest_foot={}, **C43)
RLAND43 = m.rest_landing(P43, g)
ACTK = {}
for nm_ in ("F", "F#"):
    for tag_, PP_ in (("r44", P), ("r43", P43)):
        kd_ = keys[nm_]
        ACTK[(nm_, tag_)] = m.Action(PP_, kd_, caps["black" if kd_["black"] else "white"], lay["levers"][nm_])


def _felt_land(mat, frac):
    """rest-felt contact scaled to the landed width (the r4.3 LAND_LAB law) on top of the material set's felts."""
    base = m.felt_inputs(dict(m.FELT_EFF, rest=(m.FELT_EFF["rest"][0] * frac, m.FELT_EFF["rest"][1])))
    f_ = MATS[mat]["felt"]
    if f_ is not None:
        base = dict(base, front=f_["front"], front_b=f_["front_b"])
    return base


def _case_action(key):
    if isinstance(key, tuple):              # r4.4: (module key, 'r44' / 'r43')
        A = ACTK[key]
        return A, g["held_b_b" if A.black else "held_b_w"], P["gap_us_b"] if A.black else P["gap_us_w"]
    if key == "white":
        return g["Aw"], g["held_b_w"], P["gap_us_w"]
    if key == "black":
        return g["Ab"], g["held_b_b"], P["gap_us_b"]
    for side in EPG:                      # end keys (A0, C8, ...): own action, own settled bottom, own colour's gap
        if key in EPG[side]["acts"]:
            A = EPG[side]["acts"][key]
            return A, EPG[side]["stat"][key]["held_b"], P["gap_us_b"] if A.black else P["gap_us_w"]
    raise KeyError(key)


def _grid_job(c):
    key, k, mat = c["key"], c["k"], c.get("mat", "nom")
    A, hb, gap = _case_action(key)
    gap = c.get("gap", gap)
    M = MATS[mat]
    pk_ = (key, gap, mat)
    if pk_ not in _PADS:
        _PADS[pk_] = m.PadTable(A, hb, gap, **M["pad"])
    pt = _PADS[pk_]
    kind = c["kind"]
    if kind == "held":
        st, top, fr, w_ = m.held_bottom(A, g["z_shelf"], c["F"], pad=pt, seat_k=k)
        z_stop = m.key_point_world(A, st, A.stop_pts[0])[1]
        return c, dict(gap_free=z_stop - A.kp(A.stop_pts[0], A.a_dip)[1], b=st[1])
    felt_ = _felt_land(mat, c["land"]) if c.get("land") is not None else M["felt"]
    D = m.Dyn(A, g["z_shelf"], pad=pt, seat_k=k, felt=felt_, vf=M["vf"], fmul=c.get("fmul", 1.0), track_steel=c.get("track", False))
    rk = (key, k, gap, mat, c.get("fmul", 1.0), c.get("land"), c.get("track", False))
    if rk not in _REST:
        _REST[rk] = D.run(300.0)["state"]
    st = _REST[rk]
    if kind == "release":
        ev = m.release_from_bottom(D, st)
        return c, dict(t50=ev["t50"], t100=ev["t100"], rep=500.0 / ev["t50"], th_min_rel=ev["th_min_rel"], b_min_rel=ev["b_min_rel"],
                       keep_gap_min=ev["keep_gap_min"], lift_max=ev["lift_max"], rest_peak=ev["rest_peak"], steel=ev.get("steel"), cap_peak=ev["cap_peak"])
    if kind == "press":
        return c, m.ev_summary(m.press(D, c["F"], st))
    # r4.1: a constant 3 N finger cannot strike slower than ~0.99 (white) / 1.11 m/s (black) at the front: soft notes
    # (< 1.15 m/s) are struck with a 1 N finger so that the key front really reaches the target speed
    F_f = c.get("F_follow") or (1.0 if c["v"] < 1.15 else 3.0)
    v0 = m.v0_for_front(D, st, c["v"], F_follow=F_f)
    return c, m.ev_summary(m.strike(D, st, v0, F_follow=F_f, F_hold=c.get("hold"), t_end=320.0))


def run_grid(cases, n=16):
    ctx = mp.get_context("fork")
    with ctx.Pool(n) as pool:
        return pool.map(_grid_job, cases, chunksize=2)


def run_parallel(jobs, n=None):
    ctx = mp.get_context("fork")
    with ctx.Pool(n or min(16, len(jobs))) as pool:
        return dict(pool.map(_dyn_job, jobs))


# main dynamics (seat = the weakest key of the plate FE) + friction x2 releases, in parallel with the sensitivity sets
Fe = m.FELT
sens_sets = [
    ("main", dict(full=True, holds_play=m.HOLDS_PLAY, holds_abuse=m.HOLDS_ABUSE, f2=True)),
    ("seat stiffest key", dict(seat_k=max(g["seat_k_keys"].values()))),
    ("v_floor 0.1", dict(vf=0.1, holds_play=(None, 0.45, 0.6, 1.0, 2.0), holds_abuse=(None, 0.6, 1.0, 2.0))),
    ("pad e 0.07 (pass line)", dict(pad=dict(e_eff=P["pad_e_pass"]))),
    ("pad e 0.10", dict(pad=dict(e_eff=0.10))),
    ("pad E 0.7 (softer foam)", dict(pad=dict(E=0.7))),
    ("pad E 1.4 (firmer foam)", dict(pad=dict(E=1.4))),
    ("front felt e 0.28", dict(felt=dict(Fe, front=(Fe["front"][0], m.e_input(0.28)), front_b=(Fe["front_b"][0], m.e_input(0.28))))),
    ("pass lines together (pad e 0.07, E 0.7, front e 0.22)", dict(pad=dict(e_eff=P["pad_e_pass"], E=0.7),
                                                                   felt=dict(Fe, front=(Fe["front"][0], m.e_input(0.22)), front_b=(Fe["front_b"][0], m.e_input(0.22))))),
    ("worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)", dict(pad=dict(e_eff=0.10, E=0.7), vf=0.1,
                                                                   felt=dict(Fe, front=(Fe["front"][0], m.e_input(0.28)), front_b=(Fe["front_b"][0], m.e_input(0.28))))),
    ("lip friction 0.35", dict(mu_lip=0.35, release=True)),
    # r4.1 (verifier physics minors): the combined corner, and the pad-restitution fallback of stage-0 test 1
    ("pass lines + v_floor 0.1", dict(pad=dict(e_eff=P["pad_e_pass"], E=0.7), vf=0.1,
                                      felt=dict(Fe, front=(Fe["front"][0], m.e_input(0.22)), front_b=(Fe["front_b"][0], m.e_input(0.22))))),
    ("pad e 0.15", dict(pad=dict(e_eff=0.15), holds_play=(None, 0.45, 0.6, 1.0), holds_abuse=(None, 1.0))),
    ("pad e 0.25", dict(pad=dict(e_eff=0.25), holds_play=(None, 0.45, 0.6, 1.0), holds_abuse=(None, 1.0))),
    ("fallback 1: pad e 0.15, gap -0.60/-0.65, E 1.4", dict(pad=dict(e_eff=0.15, E=1.4), gap=(-0.60, -0.65), holds_play=(None, 0.45, 0.6, 1.0), holds_abuse=(None, 1.0))),
    ("friction x2", dict(fmul=2.0, holds_play=(None, 0.45, 1.0), holds_abuse=(None,))),
    # r4.3: rest-felt contact stiffness scaled to the smallest landing (F# beside the USB slot, same effective e) for both
    # colours (conservative for the white F); releases with basic and doubled friction
    (LAND_LAB, dict(felt=m.felt_inputs(dict(m.FELT_EFF, rest=(m.FELT_EFF["rest"][0] * LAND_MIN, m.FELT_EFF["rest"][1]))),
                    holds_play=(None, 0.45, 0.6, 1.0), holds_abuse=(None, 1.0), f2=True)),
]
t_dyn = time.time()
DYN = run_parallel(sens_sets)
dyn = DYN["main"]
g = m.finish_geo(P, g, dyn)
# the real bottom pose: truly settled 1 N hold WITH the pad (sweep 'dip' pose)
g["held_pad_w"] = m.held_bottom(Aw, g["z_shelf"], 1.0, pad=g["pad_w"], seat_k=g["seat_k"])[0]
g["held_pad_b"] = m.held_bottom(Ab, g["z_shelf"], 1.0, pad=g["pad_b"], seat_k=g["seat_k"])[0]
t_dyn = time.time() - t_dyn

# ----------------------------------------------------------------------------------------------- A layout
sec("A. PLAN LAYOUT - lever centres, fins, hub collars, pad bars (module x, 0 = C left boundary)")
rings = m.spacer_rings(lay, P)
pr("white head width %.2f, head gap %.2f; white-white tail gap %.2f; black base %.1f, top %.1f"
   % (23.5 - P["head_gap"], P["head_gap"], P["tail_gap_ww"], P["black_w"], P["black_top_w"]))
pr("%-3s %-16s %-16s %-8s %-8s %-8s %-18s %-14s" % ("key", "head x", "tail x", "tail c", "lever c", "offset", "beam/block x", "collars L/R"))
roll = {}
for nm in m.ORDER:
    kd = keys[nm]
    xl = lay["levers"][nm]
    b_ = m.block_x(P, kd)
    roll[nm] = dict(finger_fff=6.0 * abs(kd["guide_c"] - (b_[0] + b_[1]) / 2))
    pr("%-3s %-16s %-16s %-8.3f %-8.3f %+-8.2f %-18s %.2f / %.2f" % (nm, "%.2f-%.2f" % kd["head"], "%.3f-%.3f" % kd["tail"], kd["xc"], xl, xl - kd["xc"],
                                                               "%.2f-%.2f" % (xl - 4, xl + 4), g["collars"][nm][0], g["collars"][nm][1]))
fc = [(f0 + f1) / 2 for f0, f1 in lay["fins"]]
spans = [b - a for a, b in zip(fc[:-1], fc[1:])]
bays = m.bays(lay["fins"])
pr("fins: " + ", ".join("x%.2f-%.2f" % f for f in lay["fins"]) + " (end fins %.1f, interior %.1f: %s)" % (P["fin_end_t"], P["fin_t"], ", ".join(a + "|" + m.ORDER[m.ORDER.index(a) + 1] for a in P["fins_after"])))
pr("lever-rod spans between fins: " + ", ".join("%.1f" % s_ for s_ in spans) + " (max %.1f)" % max(spans))
pr("gaps along the rod: " + ", ".join("%.2f" % gg["gap"] for gg in lay["gaps"]))
pr("r3 C-rings -> hub collars: every lever-lever ring (>= %.2f + axial play share) split in half onto the two hubs; lever-fin rings = fin bosses (one-sided at the ends) %s"
   % (P["ring_min"], ", ".join("%.2f/%.2f" % q for q in m.fin_boss_len(lay, P))))
off_tail = max(abs(lay["levers"][n] - 0.5 * (keys[n]["tail"][0] + keys[n]["tail"][1])) for n in m.ORDER)
pr("largest lever offset: %.2f mm from the v3 sensor centre, %.2f mm from the actual tail centre (beam and balance block follow the lever, inside the tail)" % (lay["max_offset"], off_tail))
pr("pad bars (one per fin bay, 3 pads each): " + ", ".join("x%.2f-%.2f" % (a + P["bar_rail"][0] + P["pad_bar_clear"], b - P["bar_rail"][0] - P["pad_bar_clear"]) for a, b in bays))
R["layout"] = dict(levers=lay["levers"], fins=lay["fins"], max_offset=lay["max_offset"], max_offset_tail=off_tail, rings=[r_["length"] for r_ in rings], collars=g["collars"],
                   gaps=[gg["gap"] for gg in lay["gaps"]], spans=spans, span_max=max(spans), roll=roll, bays=bays, boss_len=m.fin_boss_len(lay, P))

# ----------------------------------------------------------------------------------------------- B statics
sec("B. CAPSTANS AND STATICS (DW target white %.1f g at y13, black %.1f g at front + 10; friction at every contact; torsion assist spring k_t %.2f N mm/rad, free angle %.2f deg)"
    % (P["dw_target_w"], P["dw_target_b"], P["spring_kt"], P["spring_free_deg"]))
pr("per-key capstan solve: " + ", ".join("%s %.2f" % (n, g["caps_all"][n]) for n in m.ORDER))
pr("common capstan y: white %.2f, black %.2f (M3x6 ISO 7380 button head, crown z%.1f)" % (caps["white"], caps["black"], P["z_c"]))
stat = {}
for nm in m.ORDER:
    kd = keys[nm]
    A = m.Action(P, kd, caps["black" if kd["black"] else "white"], lay["levers"][nm])
    s = A.statics(1e-4)
    stat[nm] = dict(key_g=m.petg_mass(A.key), DW=s["DW"], UW=s["UW"], BW=s["BW"], f=s["f"], meff=s["meff"])
    pr("%-3s key PETG %.2f g  BW %.2f DW %.2f UW %.2f fric %.2f m_eff %.1f" % (nm, m.petg_mass(A.key), s["BW"], s["DW"], s["UW"], s["f"], s["meff"]))
R["keys"] = stat
for A, nm in ((Aw, "white"), (Ab, "black")):
    s = A.statics(1e-4)
    A2 = m.Action(P, A.kd, A.y_cap, A.x_lever, fmul=2.0)
    A0 = m.Action(P, A.kd, A.y_cap, A.x_lever, spring=False)
    s2 = A2.statics(1e-4)
    s0_ = A0.statics(1e-4)
    curve, curve2 = [], []
    for fr_ in (0.0, 0.25, 0.5, 0.75, 1.0):
        aa = max(1e-4, A.solve_a(A.front, A.dip * fr_)) if fr_ > 0 else 1e-4
        q = A.statics(min(aa, A.a_dip - 1e-5))
        q2 = A2.statics(min(aa, A.a_dip - 1e-5))
        curve.append((fr_, q["BW"], q["DW"], q["UW"], q["meff"], q["f"], q["fr"]["capstan"], A.spring_T(q["b"])))
        curve2.append((fr_, q2["DW"], q2["UW"]))
    pr("%s (%s): key %.2f g (PETG %.2f), lever %.2f g (steel %.2f, carrier %.2f); I_key %.0f, I_lever %.0f g mm2"
       % (nm, "D" if nm == "white" else "C#", A.mk, m.petg_mass(A.key), A.mL, A.lev.mass_of(m.RHO_ST), A.lev.mass_of(m.RHO_PETG), A.Ik, A.IL))
    pr("   BW %.2f DW %.2f UW %.2f friction %.2f = key rod %.2f + lever rod %.2f + capstan %.2f + guide %.2f; m_eff %.1f (key %.1f + lever %.1f); capstan N %.3f"
       % (s["BW"], s["DW"], s["UW"], s["f"], s["fr"]["key_rod"], s["fr"]["lever_rod"], s["fr"]["capstan"], s["fr"]["guide"], s["meff"], s["meff_key"], s["meff_lev"], s["N"]))
    pr("   spring torque rest %.2f / bottom %.2f N mm; the spring gives %.1f g of the %.1f g DW (without it DW %.1f)"
       % (A.spring_T(s["b"]), A.spring_T(A.b_dip), s["DW"] - s0_["DW"], s["DW"], s0_["DW"]))
    pr("   friction x2: DW %.2f UW %.2f; stroke -> DW/UW (friction, capstan part, spring N mm): " % (s2["DW"], s2["UW"]) +
       "; ".join("%.2f: %.1f/%.1f (%.1f, %.1f, %.2f)" % (c[0], c[2], c[3], c[5], c[6], c[7]) for c in curve))
    pr("   friction x2 along the stroke DW/UW: " + "; ".join("%.2f: %.1f/%.1f" % c for c in curve2))
    R[nm] = dict(DW=s["DW"], UW=s["UW"], BW=s["BW"], friction=s["f"], fr=s["fr"], meff=s["meff"], meff_key=s["meff_key"],
                 meff_lev=s["meff_lev"], N=s["N"], Rk=s["Rk"], RL=s["RL"], DW_2f=s2["DW"], UW_2f=s2["UW"], curve=curve, curve2=curve2,
                 key_g=A.mk, lever_g=A.mL, steel_g=A.lev.mass_of(m.RHO_ST), carrier_g=A.lev.mass_of(m.RHO_PETG),
                 Ik=A.Ik, IL=A.IL, a_dip=A.a_dip, b_dip=A.b_dip, j0=s["j"], jdip=A.j(A.a_dip)[0], y_cap=A.y_cap,
                 UW_bottom=curve[-1][3], UW_bottom_2f=curve2[-1][2], f_bottom=curve[-1][5], DW_nospring=s0_["DW"],
                 spring_T_rest=A.spring_T(s["b"]), spring_T_bottom=A.spring_T(A.b_dip), DW_max_stroke=max(c[2] for c in curve))
s0 = Aw.statics(1e-4, (0.0, P["key_top"]))
s90 = Aw.statics(1e-4, (P["y_f90"], P["key_top"]))
R["white"]["DW_lip"], R["white"]["DW_y90"] = s0["DW"], s90["DW"]
R["front_back_ratio"] = s90["DW"] / R["white"]["DW"]
pr("white lip y0: DW %.2f (band at y13 like v3); y90: DW %.2f -> front/back ratio %.2f" % (s0["DW"], s90["DW"], R["front_back_ratio"]))
# torsion spring (A2; r4.5: MISUMI C-UA90R5-3-0.5, both arms cut)
d_, ID_, n_ = P["spring_d"], P["spring_ID"], P["spring_n"]
Dm_ = ID_ + d_
k_coil = P["spring_E"] * d_ ** 4 / (64 * Dm_ * n_)          # r4.5: coil body only, catalogue E (r4.4: E_SUS 193 GPa)
kt_chk, Ne_, l_long_ = m.spring_rate(P)
C_ = Dm_ / d_
Ki = (4 * C_ * C_ - C_ - 1) / (4 * C_ * (C_ - 1))
CAT_ = P["spring_cat"]
k_cat_legs = P["spring_E"] * d_ ** 4 / (64 * Dm_ * (n_ + sum(CAT_["arms"]) / 2 / (3 * math.pi * Dm_))) * math.pi / 180   # catalogue legs 25 / 25
T_cat = CAT_["k_deg"] * CAT_["max_deg"]
sp = {}
for lab, b in (("rest", g["Aw"].statics(1e-4)["b"]), ("bottom", Aw.b_dip), ("service", math.radians(16.0)), ("hand 25 deg", math.radians(25.0))):
    Tq = Aw.spring_T(b)
    sp[lab] = dict(T=Tq, sigma=Ki * 32 * Tq / (math.pi * d_ ** 3), wound=math.degrees(b) - P["spring_free_deg"], b=math.degrees(b))
ID_bot = ID_ * n_ / (n_ + math.degrees(Aw.b_dip - math.radians(P["spring_free_deg"])) / 360.0)
ID_hand = ID_ * n_ / (n_ + sp["hand 25 deg"]["wound"] / 360.0)
sm_ = m.spring_mass(P)
pr("torsion spring %s (SUS304-WPB d%.2f ID %.1f, %.2f body turns, E %.0f from the catalogue rates): coil body rate %.2f N mm/rad, with the cut legs %.1f / %.1f (N_e %.3f) k_t %.3f N mm/rad = %.4f /deg "
   "(catalogue %.4f /deg with legs 25 / 25, this model %.4f), C %.1f, K_i %.3f; free angle %.2f deg (same b = 0 torque %.3f N mm as D05); "
   % (CAT_["part"], d_, ID_, n_, P["spring_E"], k_coil, l_long_, P["spring_short_leg"], Ne_, P["spring_kt"], math.radians(P["spring_kt"]), CAT_["k_deg"], k_cat_legs, C_, Ki, P["spring_free_deg"], P["spring_T0"]) +
   ", ".join("%s b %.2f wound %.1f deg %.2f N mm %.0f MPa" % (k, v["b"], v["wound"], v["T"], v["sigma"]) for k, v in sp.items()) + " (Su 2150: %.0f %%); ID at the bottom %.2f / hand lift %.2f on the D%.0f rod; "
   "catalogue max-use %.0f deg = %.2f N mm (%.0f MPa): hand lift %.1f deg, %.0f %% of that torque; one cut spring %.3f g (wire %.1f mm)"
   % (100 * max(v["sigma"] for v in sp.values()) / 2150, ID_bot, ID_hand, P["rod_L"], CAT_["max_deg"], T_cat, Ki * 32 * T_cat / (math.pi * d_ ** 3),
      sp["hand 25 deg"]["wound"], 100 * sp["hand 25 deg"]["T"] / T_cat, sm_[0], sm_[1]))
R["spring"] = dict(k_coil=k_coil, C=C_, Ki=Ki, states=sp, ID_bottom=ID_bot, ID_hand=ID_hand, Su=2150.0, kt=P["spring_kt"], free_deg=P["spring_free_deg"], N_e=Ne_, l_long=l_long_,
                   E=P["spring_E"], k_cat_model_deg=k_cat_legs, cat=dict(CAT_, T_max=T_cat, sigma_max=Ki * 32 * T_cat / (math.pi * d_ ** 3)),
                   hand_over_cat=sp["hand 25 deg"]["T"] / T_cat, mass_g=sm_[0], wire_mm=sm_[1], T0=P["spring_T0"])
# r4.5 fix 2 (verifier spring major): coil float on the D4 rod.  spring_pose 'face' = the r4.5 short leg (2.5, bearing on one groove
# face): the net leg force pushes the coil onto the rod, the leg lifts off and the spring unwinds until its tip is back on the face;
# the rod reaction rubs on the fixed rod (hysteresis mu_sr N r_rod).  Candidates: as built, notch rotated to restore the rest torque,
# longer short leg (5.0) + rotation, and the r4.5 fix 2 captured short leg (8.0 in a 0.70 blind groove: two contacts = a couple).
_P45 = dict(P, spring_short_leg=2.5, spring_mode="face", spring_notch=(0.8, -0.5, 0.3))
_P45["spring_kt"] = m.spring_rate(dict(_P45))[0]
_P45["spring_free_deg"] = -math.degrees(P["spring_T0"] / _P45["spring_kt"])
_P45["spring_rm_rest"] = P["spring_rm"]
_P45["spring_face_off"] = P["spring_rm"] + P["spring_d"] / 2


def _rot_for_T0(PP):
    lo_, hi_ = -25.0, 0.0
    for _ in range(40):
        mid_ = 0.5 * (lo_ + hi_)
        if m.spring_pose(dict(PP, spring_notch_rot=mid_), 0.0, "face")["T"] > PP["spring_T0"]:
            lo_ = mid_
        else:
            hi_ = mid_
    return 0.5 * (lo_ + hi_)
_cands = {"r4.5 as built (short leg 2.5 on one face)": dict(_P45)}
_rot45 = _rot_for_T0(_P45)
_cands["notch rotated %.1f deg (short leg 2.5)" % _rot45] = dict(_P45, spring_notch_rot=_rot45)
_P5 = dict(_P45, spring_short_leg=5.0)
_P5["spring_kt"] = m.spring_rate(dict(_P5))[0]
_P5["spring_free_deg"] = -math.degrees(P["spring_T0"] / _P5["spring_kt"])
_rot5 = _rot_for_T0(_P5)
_cands["short leg 5.0 + notch rotated %.1f deg" % _rot5] = dict(_P5, spring_notch_rot=_rot5)
FLOAT = {}
for lab_, PP_ in _cands.items():
    tb_ = m.spring_T_table(PP_, "face")
    for mu_ in ((0.0, 0.1, 0.3) if "as built" not in lab_ else (0.0,)):
        PPm_ = dict(P, mu_sr=mu_)          # lever geometry of this design; only T(b), N(b) from the candidate
        row_ = {}
        for nm_, A_ in (("D", Aw), ("C#", Ab)):
            sp_ = dict(kt=PP_["spring_kt"], b_free=math.radians(PP_["spring_free_deg"]), table=tb_)
            A1_ = m.Action(PPm_, A_.kd, A_.y_cap, A_.x_lever, spring=sp_)
            A2_ = m.Action(PPm_, A_.kd, A_.y_cap, A_.x_lever, spring=sp_, fmul=2.0)
            s1_, s2_ = A1_.statics(1e-4), A2_.statics(1e-4)
            b1_ = A2_.statics(A_.a_dip - 1e-5)
            row_[nm_] = dict(DW=s1_["DW"], UW=s1_["UW"], DW_2f=s2_["DW"], UW_bottom_2f=b1_["UW"],
                             DW_lip=(A1_.statics(1e-4, (0.0, P["key_top"]))["DW"] if nm_ == "D" else None))
        r0_, rb_ = m.spring_pose(PP_, 0.0, "face"), m.spring_pose(PP_, math.degrees(Aw.b_dip), "face")
        FLOAT["%s, mu %.1f" % (lab_, mu_)] = dict(T_rest=r0_["T"], T_bottom=rb_["T"], unwind=r0_["theta"], shift=r0_["off"], dir=r0_["dir"], N_rest=r0_["N_rod"], N_bottom=rb_["N_rod"],
                                                  H_bottom=mu_ * rb_["N_rod"] * P["rod_L"] / 2, keys=row_, rot=PP_.get("spring_notch_rot", 0.0), ls=PP_["spring_short_leg"])
_pc0, _pcb = m.spring_pose(P, 0.0), m.spring_pose(P, math.degrees(Aw.b_dip))
FLOAT["r4.5 fix 2 captured short leg %.1f (groove %.2f)" % (P["spring_short_leg"], P["spring_d"] + P["spring_notch"][0])] = dict(
    T_rest=_pc0["T"], T_bottom=_pcb["T"], unwind=0.0, shift=_pc0["off"], dir=0.0, N_rest=0.0, N_bottom=0.0, H_bottom=0.0,
    keys={"D": dict(DW=R["white"]["DW"], UW=R["white"]["UW"], DW_2f=R["white"]["DW_2f"], UW_bottom_2f=R["white"]["UW_bottom_2f"], DW_lip=R["white"]["DW_lip"]),
          "C#": dict(DW=R["black"]["DW"], UW=R["black"]["UW"], DW_2f=R["black"]["DW_2f"], UW_bottom_2f=R["black"]["UW_bottom_2f"], DW_lip=None)},
    rot=0.0, ls=P["spring_short_leg"], gap_rest=_pc0["gap_left"], gap_bottom=_pcb["gap_left"], F_couple=_pc0["F_couple"])
pr("r4.5 fix 2 coil float on the D%.0f rod (ID %.1f): short leg / notch -> rest / bottom torque, unwind, coil shift (dir), rod force rest / bottom, "
   "hysteresis mu N r at the bottom -> D DW / DW lip y0 / UW, C# DW / UW; friction x2 D DW, C# UW at the bottom:" % (P["rod_L"], P["spring_ID"]))
for lab_, q_ in FLOAT.items():
    pr("   %-58s T %.2f / %.2f N mm, unwind %.1f deg, shift %.2f (%.0f deg), N %.2f / %.2f N, H %.2f N mm -> D %.1f / %.1f / %.1f, C# %.1f / %.1f; x2: D DW %.1f, C# UW bottom %.1f"
       % (lab_, q_["T_rest"], q_["T_bottom"], q_["unwind"], q_["shift"], q_["dir"], q_["N_rest"], q_["N_bottom"], q_["H_bottom"], q_["keys"]["D"]["DW"], q_["keys"]["D"]["DW_lip"],
          q_["keys"]["D"]["UW"], q_["keys"]["C#"]["DW"], q_["keys"]["C#"]["UW"], q_["keys"]["D"]["DW_2f"], q_["keys"]["C#"]["UW_bottom_2f"]))
CTOL = {dp_: m.spring_capture_tol(P, dp_) for dp_ in (-0.2, -0.15, -0.1, 0.0, 0.1, 0.2, 0.3)}
pr("r4.5 fix 2 captured short leg: groove %.2f (play %.2f), leg cocked %.2f deg in it, contacts arm %.2f -> couple %.2f N at rest; coil off the rod %.3f (rest) / %.3f (bottom) / %.3f (hand 25 deg); "
   "groove printed dp (both faces dp/2): " % (P["spring_d"] + P["spring_notch"][0], P["spring_notch"][0], m.spring_notch_geo(P)["theta_c"], m.spring_notch_geo(P)["arm"], _pc0["F_couple"],
                                             _pc0["gap_left"], _pcb["gap_left"], m.spring_pose(P, 25.0)["gap_left"])
   + ", ".join("%+.2f -> %s%.2f deg, rest %.2f N mm, rod gap %.2f" % (dp_, "" if q_["feasible"] else "NO FIT ", q_["dtheta"], q_["T0"], q_["gap_left"]) for dp_, q_ in CTOL.items()))
# r4.5 fix 2 (resume): the long leg's reaction also has a component ALONG the captured groove; friction at the two contacts holds
# it (mu needed) or the leg tip stops on the groove's blind end (spring_notch[2] further): the coil's rod gap after that slide
_NG_ = m.spring_notch_geo(P)
SLIDE = {}
for bd_ in (0.0, math.degrees(Aw.b_dip), 25.0):
    r_ = m.spring_pose(P, bd_)
    ey_ = (-math.cos(math.radians(bd_)), -math.sin(math.radians(bd_)))
    al_ = r_["Fl"] * (ey_[0] * _NG_["u_g"][0] + ey_[1] * _NG_["u_g"][1])
    SLIDE["%.2f" % bd_] = dict(b=bd_, Fl=r_["Fl"], along=al_, mu_req=abs(al_) / (2 * r_["F_couple"]), gap=r_["gap_left"], gap_slid=r_["gap_left"] - P["spring_notch"][2],
                               toward="blind end" if al_ > 0 else "pocket")
pr("r4.5 fix 2 captured leg, long-leg reaction along the groove: " + "; ".join("b %.1f: %.3f N of %.3f toward the %s -> friction needed %.3f (2 contacts x %.2f N); slid %.1f onto the blind end: rod gap %.3f -> %.3f"
                                                                              % (q_["b"], abs(q_["along"]), q_["Fl"], q_["toward"], q_["mu_req"], q_["along"] / q_["mu_req"] / 2 if q_["mu_req"] > 0 else 0.0,
                                                                                 P["spring_notch"][2], q_["gap"], q_["gap_slid"]) for q_ in SLIDE.values()))
R["spring"]["float"] = FLOAT
R["spring"]["capture_tol"] = {"%+.2f" % k_: v_ for k_, v_ in CTOL.items()}
R["spring"]["capture"] = dict(theta_c=m.spring_notch_geo(P)["theta_c"], arm=m.spring_notch_geo(P)["arm"], F_couple_rest=_pc0["F_couple"], F_couple_hand=m.spring_pose(P, 25.0)["F_couple"],
                              gap_rest=_pc0["gap_left"], gap_bottom=_pcb["gap_left"], gap_hand=m.spring_pose(P, 25.0)["gap_left"], width=P["spring_d"] + P["spring_notch"][0],
                              slide=SLIDE, mu_req_max=max(q_["mu_req"] for q_ in SLIDE.values()), gap_slid_min=min(q_["gap_slid"] for q_ in SLIDE.values()))

# ----------------------------------------------------------------------------------------------- C heights
sec("C. HEIGHTS - truly settled 1 N bottom, pad faces, pad bar seat, top plate, curtain, shelf, keeper")
pr("cap top at the bottom: rigid %.2f (white) / %.2f (black); rigid - capstan-felt set %.2f / %.2f; TRULY settled 4-DOF state held at 1 N (no pad): %.2f / %.2f, |w| at the end %.1e rad/ms"
   % (g["rigid_top_w"], g["rigid_top_b"], g["top_w_set"], g["top_b_set"], g["top_w"], g["top_b"], g["held_w_end"]))
pr("   (key front held at 1 N: white z%.2f, black z%.2f; lever angle held %.2f / %.2f deg)" % (g["held_front_w"], g["held_front_b"], D(g["held_b_w"]), D(g["held_b_b"])))
for c, nm in (("w", "white"), ("b", "black")):
    pt = g["pad_" + c]
    pr("%s pad: face parallel to the steel top at %.2f deg, %+.2f along its normal (lever first when negative); face at y%.0f z%.2f / y%.0f z%.2f; first contact at %.2f deg; damping c %.2f for e %.3f"
       % (nm, D(g["held_b_" + c]), P["gap_us_" + c], P["pad_y"][0], m.pad_face_z(pt, P["pad_y"][0]), P["pad_y"][1], m.pad_face_z(pt, P["pad_y"][1]),
          D(pt.b0), pt.c, pt.e_check))
pr("pad %.0fT foam + %.0fT felt (E %.1f MPa: %.2f MPa at 25 %%), %.0f wide, y%.0f-%.0f; wedges white %.2f-%.2f, black %.2f-%.2f; pad bar %.1f: seat (bar top) z%.2f, front part in the plate channel z%.2f-%.2f"
   % (P["pad_foam"], P["pad_felt"], P["pad_E"], float(m.foam_sigma(0.25, P["pad_E"], P["pad_epsD"])), P["pad_w"], P["pad_y"][0], P["pad_y"][1],
      g["wedge_range"]["w"][0], g["wedge_range"]["w"][1], g["wedge_range"]["b"][0], g["wedge_range"]["b"][1], P["pad_bar_t"], g["z_seat"], g["z_seat"], g["z_seat"] + P["pad_bar_t"]))
zu_rear = min(z for y, z in g["plate_under"] if y > P["pad_bar_y"][1] + 1)
pr("top plate: top z%.2f (= seat + %.1f), front channel underside z%.2f, pad zone z%.2f, behind the pads z%.2f (thickness %.1f); nothing above it (r3 cover z78.0, heads z80.7; v3 z59)"
   % (g["z_top"], P["plate_t"], g["z_seat"] + P["pad_bar_t"], g["z_seat"], zu_rear, g["z_top"] - zu_rear))
pr("lever extremes from all dynamic cases: max b %.2f / %.2f deg (sweep 'ff' +0.25), return overshoot %.2f / %.2f, settled rest %.2f / %.2f; key max %.2f / %.2f deg, max rise above rest %.2f / %.2f deg"
   % (D(g["b_ff_w"]), D(g["b_ff_b"]), D(g["b_over_w"]), D(g["b_over_b"]), D(g["b_rest_w"]), D(g["b_rest_b"]), D(g["a_ff_w"]), D(g["a_ff_b"]), D(g["a_over_w"]), D(g["a_over_b"])))
pr("real bottom (1 N, pad present): white lever %.2f deg, key front z%.2f (%+.2f above its felt); black %.2f deg, z%.2f (%+.2f)"
   % (D(g["held_pad_w"][1]), m.key_point_world(Aw, g["held_pad_w"], Aw.front)[1], m.key_point_world(Aw, g["held_pad_w"], Aw.front)[1] - g["held_front_w"],
      D(g["held_pad_b"][1]), m.key_point_world(Ab, g["held_pad_b"], Ab.front)[1], m.key_point_world(Ab, g["held_pad_b"], Ab.front)[1] - g["held_front_b"]))
pr("balance rail: lowered to z%.1f under the blocks (lowest block corner over all poses z%.2f), rod cradles between the blocks (x clearance %.2f), saddle lip z%.1f"
   % (g["z_rail_low"], g["z_block_min"], m.cradle_clear_x(P), P["rail_groove_lip"]))
pr("rear shelf top z%.3f; keeper felt underside z%.2f (crossbar + %.1f); curtain strip bottom z%.1f (white) / z%.1f (black notches)"
   % (g["z_shelf"], g["z_keep"], P["keeper_gap"], g["z_curtain_w"], g["z_curtain_b"]))
R["heights"] = {k: g[k] for k in ("top_w", "top_b", "rigid_top_w", "rigid_top_b", "top_w_set", "top_b_set", "set_w", "set_b", "z_shelf", "z_keep",
                                  "held_front_w", "held_front_b", "z_seat", "z_top", "y_bar_step", "z_rail_low", "z_block_min", "z_curtain_w", "z_curtain_b",
                                  "held_w_end", "pad_comp_ratio_w", "pad_comp_ratio_b")}
R["heights"].update(wedge=g["wedge_range"], plate_under=g["plate_under"], plate_rear=zu_rear,
                    b_ff_w=D(g["b_ff_w"]), b_ff_b=D(g["b_ff_b"]), b_over_w=D(g["b_over_w"]), b_over_b=D(g["b_over_b"]), b_rest_w=D(g["b_rest_w"]),
                    b_rest_b=D(g["b_rest_b"]), a_ff_w=D(g["a_ff_w"]), a_ff_b=D(g["a_ff_b"]), a_over_w=D(g["a_over_w"]), a_over_b=D(g["a_over_b"]),
                    held_b_w=D(g["held_b_w"]), held_b_b=D(g["held_b_b"]), held_pad_b_w=D(g["held_pad_w"][1]), held_pad_b_b=D(g["held_pad_b"][1]),
                    held_pad_front_w=m.key_point_world(Aw, g["held_pad_w"], Aw.front)[1] - g["held_front_w"],
                    held_pad_front_b=m.key_point_world(Ab, g["held_pad_b"], Ab.front)[1] - g["held_front_b"],
                    pad_face_w=(m.pad_face_z(g["pad_w"], P["pad_y"][0]), m.pad_face_z(g["pad_w"], P["pad_y"][1])),
                    pad_face_b=(m.pad_face_z(g["pad_b"], P["pad_y"][0]), m.pad_face_z(g["pad_b"], P["pad_y"][1])),
                    pad_b0_w=D(g["pad_b0_w"]), pad_b0_b=D(g["pad_b0_b"]), sigma25=float(m.foam_sigma(0.25, P["pad_E"], P["pad_epsD"])))

# ----------------------------------------------------------------------------------------------- D sensor
sec("D. SENSOR (magnet D5x2 at y67)")
sens = {}
for A, nm, ze, cc in ((Aw, "white", P["z_elem_w"], "w"), (Ab, "black", P["z_elem_b"], "b")):
    tr, dy = A.mag_travel()
    tr_ff, _ = A.mag_travel(g["a_ff_" + cc])
    sens[nm] = dict(rest=A.mag[1] - ze, bottom=A.mag[1] - tr - ze, ff=A.mag[1] - tr_ff - ze, travel=tr, y_shift=dy)
    pr("%s: rest gap %.2f, bottom %.2f, max over-travel (2.5 m/s abuse) %.2f, travel %.2f, y shift %.2f; 50%% re-arm = %.2f mm rise"
       % (nm, sens[nm]["rest"], sens[nm]["bottom"], sens[nm]["ff"], tr, dy, 0.5 * tr))
R["sensor"] = sens

# ----------------------------------------------------------------------------------------------- E dynamics
sec("E. DYNAMICS - 4-DOF (free key on the cloth-lined snap notch with lip friction + keeper + lever with torsion spring), flat foam pad on the steel top "
    "in series with its seat (%.0f N/mm = weakest key of the plate FE), Flores contact law, dt 4 us" % g["seat_k"])
pr("load envelopes (R4 brief): PLAY = key-FRONT speed %.1f m/s at the felt contact (Askenfelt & Jansson 1991: forte key speed seldom above 1 m/s; Goebl et al. 2005: loudest struck "
   "attacks 6.4-7.8 m/s hammer = about 1.3-1.6 m/s at the key with the ~5x ratio); ABUSE = %.1f m/s single, %.1f m/s 6-key chord" % (P["v_play"], P["v_abuse"], P["v_abuse_chord"]))
fel = {}
for nm_, KE in m.FELT_EFF.items():
    ki = m.FELT[nm_]
    fel[nm_] = dict(K=KE[0], e_eff=KE[1], e_in=ki[1], check=m.felt_effective_e(ki))
    pr("  contact %-8s K %.0f N/mm^1.5, design (effective) e %.2f -> Flores input %.3f -> simulated drop restitution %.3f" % (nm_, KE[0], KE[1], ki[1], fel[nm_]["check"]))
R["felt"] = fel
cases_txt = dict(pp="push 0.8 N", mf="push 1.5 N", ff_push="push 3 N", push6="push 6 N",
                 ff_rel="1.0 m/s front, let go", ff_h1="1.0 m/s, hold 1 N", chord20_rel="2.0 m/s front, let go", chord20_h1="2.0 m/s, hold 1 N",
                 cons_rel="1.5 m/s at the FINGER start, let go", cons_h0="1.5 m/s finger, hold 0.45 N", cons_h1="1.5 m/s finger, hold 1 N",
                 release="release from a settled 1 N hold")
for h in m.HOLDS_PLAY:
    cases_txt["play_" + m.hl(h)] = "PLAY 1.5 m/s front, " + ("let go" if h is None else "hold %.2f N" % h)
for h in m.HOLDS_ABUSE:
    cases_txt["abuse_" + m.hl(h)] = "ABUSE 2.5 m/s front, " + ("let go" if h is None else "hold %.2f N" % h)
cases_txt["cons_h0.45"] = cases_txt.pop("cons_h0")
cases_txt["cons_h1.00"] = cases_txt.pop("cons_h1")
R["cases_txt"] = cases_txt
dd = {}
for col in ("white", "black"):
    A = Aw if col == "white" else Ab
    dc = dyn[col]
    Dm = m.dyn_for(g, A)
    st = Dm.run(300.0)["state"]
    lip = m.key_point_world(A, st, A.front)[1]
    kg = Dm.z_keep - max(m.key_point_world(A, st, p)[1] for p in A.keeper_pts)
    pr("%s settled rest: key front z%.3f, keeper gap %.3f, lever %.3f deg (capstan felt set), rod penetration %.3f; finger-start speed for PLAY %.3f, ABUSE %.3f, 1.0 m/s %.3f, 2.0 m/s %.3f m/s"
       % (col, lip, kg, D(st[1]), m.state_pen(st, Dm), dc["v0_play"], dc["v0_abuse"], dc["v0_ff"], dc["v0_chord"]))
    d = dict(rest_front=lip, rest_keeper_gap=kg, rest_b=D(st[1]), v0_play=dc["v0_play"], v0_abuse=dc["v0_abuse"])
    for k, v in dc.items():
        if isinstance(v, dict) and "lift_max" in v:
            d[k] = v
            if k == "release_f2":
                continue
            pr("   %-38s front %s m/s | lift %.3f (lip pull %.2f N) | pad %.0f N (comp %.2f, seat %.2f) | front felt %.0f N | capstan %.1f N | keeper gap %.2f | rod %.0f N | ghost: rise %.2f, magnet %.0f %%, desc %.2f m/s"
               % (cases_txt.get(k, k), "%.2f" % v["v_front_bottom"] if v["v_front_bottom"] else " -  ", v["lift_max"], v["lip_pull"], v["up_peak"], v["pen_up_max"],
                  v["seat_max"], v["front_peak"], v["cap_peak"], v["keep_gap_min"], v["RL_peak"], v["ghost_rise"], 100 * v["ghost_frac"], v["ghost_v_desc"]))
    rel, rel2 = dc["release"], dc["release_f2"]
    d.update(t40=rel["t40"], t50=rel["t50"], t100=rel["t100"], rep=500 / rel["t50"], t50_2f=rel2["t50"], t100_2f=rel2["t100"], rep_2f=500 / rel2["t50"])
    pr("   repetition (re-arm at 50 %%, released from a 1.2 s settled 1 N hold): t50 %.1f ms (t40 %.1f), full %.1f ms -> 1/(2 t50) %.1f Hz | friction x2 t50 %.1f / full %.1f ms -> %.1f Hz"
       % (rel["t50"], rel["t40"], rel["t100"], d["rep"], rel2["t50"], rel2["t100"], d["rep_2f"]))
    dd[col] = d
R["dyn"] = dd
# sensitivity sets
sec("E1. SENSITIVITY - pad seat, contact-law floor, pad and felt materials, lip friction, doubled friction (PLAY 1.5 m/s front, ABUSE 2.5 m/s)")
sens_out = {}
for lab, _ in sens_sets:
    if lab == "main":
        continue
    rr = DYN[lab]
    row = {}
    for col in ("white", "black"):
        c = rr[col]
        pl = [v for k, v in c.items() if k.startswith("play_")]
        ab = [v for k, v in c.items() if k.startswith("abuse_")]
        rel = c.get("release")
        row[col] = dict(lift_play=max(v["lift_max"] for v in pl), keep_play=min(v["keep_gap_min"] for v in pl), up_play=max(v["up_peak"] for v in pl),
                        ghost045=c.get("play_h0.45", {}).get("ghost_frac"), ghost06=c.get("play_h0.60", {}).get("ghost_frac"),
                        vdesc=max(v["ghost_v_desc"] for v in pl), lift_abuse=max(v["lift_max"] for v in ab) if ab else None,
                        keep_abuse=min(v["keep_gap_min"] for v in ab) if ab else None, up_abuse=max(v["up_peak"] for v in ab) if ab else None,
                        t50=rel["t50"] if rel else None, rep=500 / rel["t50"] if rel and rel["t50"] else None, t100=rel["t100"] if rel else None,
                        lip_pull=max(v["lip_pull"] for v in pl + ab))
    sens_out[lab] = row
    pr("%-58s " % lab + " || ".join("%s: lift %.3f keep %.2f pad %.0f N ghost 0.45/0.6 N %s/%s %% (desc %.2f) | abuse lift %s keep %s pad %s | rep %s Hz"
                                      % (col[0].upper(), q["lift_play"], q["keep_play"], q["up_play"],
                                         "-" if q["ghost045"] is None else "%.0f" % (100 * q["ghost045"]), "-" if q["ghost06"] is None else "%.0f" % (100 * q["ghost06"]),
                                         q["vdesc"], "-" if q["lift_abuse"] is None else "%.3f" % q["lift_abuse"],
                                         "-" if q["keep_abuse"] is None else "%.2f" % q["keep_abuse"], "-" if q["up_abuse"] is None else "%.0f" % q["up_abuse"],
                                         "-" if q["rep"] is None else "%.1f" % q["rep"]) for col, q in row.items()))
R["sens"] = sens_out
ev_a = m.strike(m.dyn_for(g, Aw), dyn["white"]["rest_state"], dyn["white"]["v0_play"], F_hold=1.0, t_end=250.0)
Dd = m.dyn_for(g, Aw)
ev_b = Dd.run(250.0, dt=0.002, state=m.strike_state(Aw, dyn["white"]["rest_state"], dyn["white"]["v0_play"]),
              finger=lambda t, ev: 3.0 if (ev["t_bottom"] is None or t < ev["t_bottom"] + 2.0) else 1.0)
pr("time-step check (white PLAY, hold 1 N): dt 4 us lift %.3f pad %.1f N magnet %.1f %% | dt 2 us lift %.3f pad %.1f N magnet %.1f %%"
   % (ev_a["lift_max"], ev_a["up_peak"], 100 * ev_a["ghost_frac"], ev_b["lift_max"], ev_b["up_peak"], 100 * ev_b["ghost_frac"]))
R["dt_check"] = dict(lift4=ev_a["lift_max"], lift2=ev_b["lift_max"], up4=ev_a["up_peak"], up2=ev_b["up_peak"])

# ----------------------------------------------------------------------------------------------- H0 plate FE (needed for the chord seat)
sec("H0. TOP PLATE FE (grillage 1 mm, fins as line springs / the board fin F|F# as a deep beam, rear wall) - pad seats and chord seats")
pr("per-key pad-seat stiffness (100 N on one pad): " + ", ".join("%s %.0f" % (k, v) for k, v in g["seat_k_keys"].items()) + " N/mm -> the dynamics use the weakest, %.0f N/mm" % g["seat_k"])
up_play = (max(dyn["white"][k]["up_peak"] for k in dyn["white"] if k.startswith("play_")), max(dyn["black"][k]["up_peak"] for k in dyn["black"] if k.startswith("play_")))
up_abuse = (max(dyn["white"][k]["up_peak"] for k in dyn["white"] if k.startswith("abuse_")), max(dyn["black"][k]["up_peak"] for k in dyn["black"] if k.startswith("abuse_")))
up_ch = (max(dyn["white"][k]["up_peak"] for k in ("chord20_rel", "chord20_h1.00")), max(dyn["black"][k]["up_peak"] for k in ("chord20_rel", "chord20_h1.00")))
PL = {}
for lab, F_ in (("play", up_play), ("abuse_chord20", up_ch), ("abuse", up_abuse)):
    PL[lab] = m.plate_loads(P, g, F_[0], F_[1], lay["fins"], lay["levers"], keys, chords=(lab != "abuse"))
    for kind, q in PL[lab].items():
        pr("   %-14s %-6s pads %.0f / %.0f N (sum %.0f N): plate %.1f MPa (in layer), fin top %.1f MPa (across layers), rear wall %.1f N/mm, max seat deflection %.2f mm, chord-equivalent seat %.0f N/mm (%s)"
           % (lab, kind, F_[0], F_[1], q["total"], q["sigma"], q["fin_top"], q["wall_q"], q["seat_max"], q["k_eq"], "-".join(q.get("k_eq_keys", []))))
R["plate"] = PL
R["upstop_peaks"] = dict(play=up_play, abuse=up_abuse, chord20=up_ch)
# r4.4 fix 2b: the F|F# foot is grounded by its keel to the balance rail (the floor under the board is open)
kq_ = P["fin_keel"]
for lab in ("play", "abuse_chord20", "abuse"):
    for kind, q in PL[lab].items():
        pr("   keel (y%.1f-%.1f z%.0f-%.0f, t %.1f) %-14s %-6s: shear %.1f N -> %.2f MPa, bending %.2f MPa (in the layer plane; every note %.0f / rare %.0f)"
           % (kq_[0], m.keel_front(P), kq_[1], kq_[2], P["fin_t"] - 2 * P["fin_ext_inset"], lab, kind, q.get("keel_V", 0.0), q.get("keel_tau", 0.0), q.get("keel_sigma", 0.0), P["s_cyc_in"], P["s_rare_in"]))
# r4.5 fix 2 (verifier fixes minor): the keel root sits on the balance rail + floor strip as a beam along x (keel_rail 'fins':
# continuous over the module's fin lines, simply supported there, twist held; no EVA under it), not on a rigid clamp
_kr_ = PL["play"]["chord"].get("keel_rail") or PL["play"]["single"].get("keel_rail") or {}
PLr_ = m.plate_loads(dict(P, keel_rail=None), g, up_play[0], up_play[1], lay["fins"], lay["levers"], keys, chords=True)
PLr18_ = m.plate_loads(dict(P, fin_keel=(P["fin_keel"][0], P["fin_keel"][1], 18.0), fin_keel_front=None), g, up_play[0], up_play[1], lay["fins"], lay["levers"], keys, chords=True)
# r4.5 fix 2 (resume): the first fix-2 pass kept the fin front at y152 and raised the keel to z21 (hits key F, section G); the keel
# at its clearance limit z19.5 with the fin front still at y152; and the rail-support bounds for the new geometry
PLr21_ = m.plate_loads(dict(P, fin_keel=(P["fin_keel"][0], P["fin_keel"][1], 21.0), fin_keel_front=None), g, up_play[0], up_play[1], lay["fins"], lay["levers"], keys, chords=True)
PLr152_ = m.plate_loads(dict(P, fin_keel_front=None), g, up_play[0], up_play[1], lay["fins"], lay["levers"], keys, chords=True)
PLrss_ = m.plate_loads(dict(P, keel_rail="fins_span"), g, up_play[0], up_play[1], lay["fins"], lay["levers"], keys, chords=True)
PLrh_ = m.plate_loads(dict(P, keel_rail="hatch"), g, up_play[0], up_play[1], lay["fins"], lay["levers"], keys, chords=True)
PLdss_ = m.plate_loads(dict(P, keel_rail="fins_span"), g, 60.0, 60.0, lay["fins"], lay["levers"], keys, chords=True)
PLdead_ = m.plate_loads(P, g, 60.0, 60.0, lay["fins"], lay["levers"], keys, chords=True)
_ch_ = PLdead_["chord"]
_ef_ = {k_: v_ for k_, v_ in _ch_.get("k_eq_seats", {}).items() if k_ in ("E", "F")}
pr("r4.5 fix 2 keel root on the rail spring (%s: rail y%.1f-%.1f z%.0f-%.2f + floor strip, ribbon lane x%.0f-%.0f not composite, supports x %s, interior fin lines %s): kv %.0f N/mm, kr %.0f N mm/rad, "
   "rear face %.2f behind the twist axis -> %.0f N/mm at the face; PLAY chord seat %.1f N/mm (%s; keel z%.1f, F|F# fin front y%.1f; rigid rail %.1f; keel to z18 as r4.4 %.1f), keel root sinks %.3f mm; "
   "first-module dead load 6 pads x 60 N on %s: seats %s mm (E/F max %.3f, pass line 60 / %.0f = %.3f)"
   % (_kr_.get("supports"), P["rail_front_y"], P["rail_y"][1], P["z_floor"][0], _kr_.get("rail_top", 0.0), P["ribbon_x"][0], P["ribbon_x"][1], tuple(round(v_, 1) for v_ in _kr_.get("span", (0, 0))),
      [round(v_, 1) for v_ in _kr_.get("inner", [])], _kr_.get("kv", 0.0), _kr_.get("kr", 0.0), _kr_.get("e", 0.0), _kr_.get("k_face", 0.0), PL["play"]["chord"]["k_eq"], "-".join(PL["play"]["chord"]["k_eq_keys"]),
      P["fin_keel"][2], m.keel_front(P), PLr_["chord"]["k_eq"], PLr18_["chord"]["k_eq"], PL["play"]["chord"].get("keel_w_root", 0.0), "-".join(_ch_["k_eq_keys"]), ", ".join("%s %.3f" % kv_ for kv_ in _ch_["k_eq_seats"].items()),
      max(_ef_.values()) if _ef_ else float("nan"), P["seat_k_chord_req"], 60.0 / P["seat_k_chord_req"]))
_efss_ = {k_: v_ for k_, v_ in PLdss_["chord"].get("k_eq_seats", {}).items() if k_ in ("E", "F")}
pr("   r4.5 fix 2 keel variants (PLAY chord seat N/mm): first fix-2 pass keel z21 / fin front y152 %.1f (%s; clearance to key F: section G), keel z%.1f with the fin front still at y152 %.1f (%s), "
   "this design %.1f (%s; FE keel %.1f long to the first plate node behind y%.1f); rail support bounds for this design: clamped at the hatch edges %.1f, simply supported between the neighbouring fin lines only "
   "(no continuity, no EVA) %.1f (%s) - dead-load E/F %.3f mm; the model's case (continuous over the fin lines, no EVA) %.1f"
   % (PLr21_["chord"]["k_eq"], "-".join(PLr21_["chord"]["k_eq_keys"]), P["fin_keel"][2], PLr152_["chord"]["k_eq"], "-".join(PLr152_["chord"]["k_eq_keys"]), PL["play"]["chord"]["k_eq"], "-".join(PL["play"]["chord"]["k_eq_keys"]),
      (PL["play"]["chord"].get("keel_L") or 0.0), m.keel_front(P), PLrh_["chord"]["k_eq"], PLrss_["chord"]["k_eq"], "-".join(PLrss_["chord"]["k_eq_keys"]), max(_efss_.values()) if _efss_ else float("nan"), PL["play"]["chord"]["k_eq"]))
R["keel_rail"] = dict(rail=_kr_, k_chord=PL["play"]["chord"]["k_eq"], k_chord_rigid=PLr_["chord"]["k_eq"], k_chord_keel18=PLr18_["chord"]["k_eq"], w_root=PL["play"]["chord"].get("keel_w_root", 0.0),
                      k_chord_keel21=PLr21_["chord"]["k_eq"], k_chord_front152=PLr152_["chord"]["k_eq"], k_chord_hatch=PLrh_["chord"]["k_eq"], k_chord_fins_span=PLrss_["chord"]["k_eq"],
                      EF_fins_span=max(_efss_.values()) if _efss_ else None, fin_front=m.keel_front(P), keel_top=P["fin_keel"][2], keel_L_fe=PL["play"]["chord"].get("keel_L"),
                      keel_sigma_keel18=PLr18_["chord"].get("keel_sigma", 0.0), dead=dict(F=60.0, keys=_ch_["k_eq_keys"], seats=_ch_["k_eq_seats"], EF_max=max(_ef_.values()) if _ef_ else None,
                                                                                        limit=60.0 / P["seat_k_chord_req"], k_eq=_ch_["k_eq"]))
# chord-equivalent seat: the 6-key PLAY chord deflects each seat more -> run the light holds with that seat
k_ch = PL["play"]["chord"]["k_eq"]
k_ch_ab = PL["abuse_chord20"]["chord"]["k_eq"]
CHJ = run_parallel([("chord seat", dict(seat_k=k_ch, holds_play=(None, 0.45, 0.5, 0.6, 0.8, 1.0, 2.0), holds_abuse=(), release=False)),
                    ("chord seat 1.2", dict(seat_k=k_ch, v_play=1.2, holds_play=(None, 0.45, 0.6, 1.0), holds_abuse=(), release=False)),
                    ("chord seat 2.0 (abuse)", dict(seat_k=k_ch_ab, v_play=P["v_abuse_chord"], holds_play=(None, 0.45, 1.0), holds_abuse=(), release=False))])
CH = CHJ["chord seat"]
CH12 = CHJ["chord seat 1.2"]
CH20 = CHJ["chord seat 2.0 (abuse)"]
chord_dyn = {}
for col in ("white", "black"):
    c = CH[col]
    chord_dyn[col] = {k: v for k, v in c.items() if k.startswith(("play_", "abuse_"))}
    pr("6-key PLAY chord (every seat at %.0f N/mm) %s: " % (k_ch, col) + "; ".join("%s lift %.3f keep %.2f magnet %.0f %% desc %.2f" %
                                                                               (k.replace("play_", ""), v["lift_max"], v["keep_gap_min"], 100 * v["ghost_frac"], v["ghost_v_desc"])
                                                                               for k, v in chord_dyn[col].items() if k.startswith("play_")))
chord_ab = {c: {k: v for k, v in CH20[c].items() if k.startswith("play_")} for c in ("white", "black")}
for col in ("white", "black"):
    pr("6-key ABUSE chord 2.0 m/s (every seat at %.0f N/mm) %s: " % (k_ch_ab, col) + "; ".join("%s lift %.3f keep %.2f magnet %.0f %% desc %.2f" %
                                                                                  (k.replace("play_", ""), v["lift_max"], v["keep_gap_min"], 100 * v["ghost_frac"], v["ghost_v_desc"])
                                                                                  for k, v in chord_ab[col].items()))
# the chord seats let the levers rise further: widen the sweep's 'ff' poses to cover them
for col, c in (("white", "w"), ("black", "b")):
    bm = max(v["b_max"] for src_ in (CH, CH12, CH20) for k, v in src_[col].items() if isinstance(v, dict) and "b_max" in v)
    am = max(v["th_max"] for src_ in (CH, CH12, CH20) for k, v in src_[col].items() if isinstance(v, dict) and "th_max" in v)
    g["b_ff_" + c] = max(g["b_ff_" + c], bm + math.radians(0.25))
    g["a_ff_" + c] = max(g["a_ff_" + c], am + math.radians(0.1))
pr("sweep 'ff' poses incl. the chord seats: lever %.2f / %.2f deg, key %.2f / %.2f deg" % (D(g["b_ff_w"]), D(g["b_ff_b"]), D(g["a_ff_w"]), D(g["a_ff_b"])))
R["heights"].update(b_ff_w=D(g["b_ff_w"]), b_ff_b=D(g["b_ff_b"]), a_ff_w=D(g["a_ff_w"]), a_ff_b=D(g["a_ff_b"]))
R["chord_dyn"] = dict(k=k_ch, res=chord_dyn, k_abuse=k_ch_ab, res_abuse=chord_ab,
                      res12={c: {k: v for k, v in CH12[c].items() if k.startswith("play_")} for c in ("white", "black")})

# ------------------------------------------------------------------ r4.1 grids (verifier physics majors 1 + 2)
EPG.update(m.end_parts(P, g))
seat_end = {}
for side_ in ("left", "right"):
    e_ = EPG[side_]
    xf_ = [(f0, f1) for f0, f1 in e_["lay"]["fins"]]
    x_rng_ = (min(e_["x"][0], e_["cheek"][0]) + 0.2, max(e_["x"][1], e_["cheek"][1]) - 0.2)
    kse_, _ = m.plate_seat_k(P, g, xf_, e_["lay"]["levers"], {False: g["y_load_w"], True: g["y_load_b"]},
                             {n_: e_["keys"][n_]["black"] for n_ in e_["order"]}, x_range=x_rng_, extra_fins=[e_["cheek"]])
    seat_end.update(kse_)
V_SWEEP = [round(1.0 + 0.05 * i, 2) for i in range(11)]
V_GRID = [round(0.5 + 0.1 * i, 1) for i in range(11)]
GH = (0.45, 0.5, 0.6, 0.8, 1.0, 2.0)
gcases = []
for col in ("white", "black"):
    for mat in ("nom", "passline", "vf01", "pass_vf01", "worst"):
        for v in V_SWEEP:
            gcases.append(dict(grp="chord_sweep", key=col, k=k_ch, mat=mat, kind="strike", v=v, hold=None))
    for v in V_GRID:
        for h in GH:
            gcases.append(dict(grp="chord_ghost", key=col, k=k_ch, mat="nom", kind="strike", v=v, hold=h))
    for mat in ("nom", "worst"):
        for v in (0.5, 1.0) + ((1.5,) if mat == "worst" else ()):
            for h in (None, 0.45, 0.5, 0.6, 1.0, 2.0):
                gcases.append(dict(grp="single_grid", key=col, k=g["seat_k"], mat=mat, kind="strike", v=v, hold=h))
    for gap_ in ((-0.30, -0.40, -0.50) if col == "white" else (-0.35, -0.45, -0.55)):
        for F_ in (0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0):
            gcases.append(dict(grp="strip", key=col, k=g["seat_k"], mat="nom", kind="held", F=F_, gap=gap_))
for nm_ in ("A0", "C8"):
    for mat in ("nom", "worst"):
        for v, h in ((1.5, None), (1.5, 0.45), (1.5, 1.0), (1.5, 2.0), (1.0, None), (1.0, 0.45), (0.5, None), (P["v_abuse"], None)):
            gcases.append(dict(grp="end", key=nm_, k=seat_end[nm_], mat=mat, kind="strike", v=v, hold=h))
        gcases.append(dict(grp="end", key=nm_, k=seat_end[nm_], mat=mat, kind="release"))
        gcases.append(dict(grp="end", key=nm_, k=seat_end[nm_], mat=mat, kind="release", fmul=2.0))
# r4.4 (R44 issue 2): F / F# on their own rest-felt landing - PLAY grid 0.5/1.0/1.5 m/s x let go / 0.45 / 1 / 2 N at the 6-key chord
# seat, ABUSE 2.5 m/s single at the chord seat (brief) and at the single-key seat, ABUSE 2.0 m/s chord seat, releases (friction x1 / x2);
# materials nominal / pass line / worst; r4.4 felts (cut at the slot, F# widened to its tail edge) and the r4.3 felts ('before')
for nm_ in ("F", "F#"):
    for tag_, RL_ in (("r44", RLAND), ("r43", RLAND43)):
        fr_ = RL_[nm_]["frac"]
        for mat in ("nom", "passline", "worst"):
            base_ = dict(grp="land", key=(nm_, tag_), mat=mat, land=fr_, tag=tag_, nm=nm_)
            for v in (0.5, 1.0, 1.5):
                for h in (None, 0.45, 1.0, 2.0):
                    gcases.append(dict(base_, sub="play_chord", k=k_ch, kind="strike", v=v, hold=h))
            for h in (None, 1.0):
                gcases.append(dict(base_, sub="abuse_at_chord_seat", k=k_ch, kind="strike", v=P["v_abuse"], hold=h))
                gcases.append(dict(base_, sub="abuse_single", k=g["seat_k"], kind="strike", v=P["v_abuse"], hold=h))
                gcases.append(dict(base_, sub="abuse_chord20", k=k_ch_ab, kind="strike", v=P["v_abuse_chord"], hold=h))
            for fm_ in (1.0, 2.0):
                gcases.append(dict(base_, sub="release", k=k_ch, kind="release", fmul=fm_))
# r4.4 (R44 issue 1): carrier -> steel interface forces (snap-lip retention) over the PLAY / ABUSE / chord / release / press cases
for col in ("white", "black"):
    for mat in ("nom", "passline", "worst"):
        for v, h in ((P["v_play"], None), (P["v_play"], 1.0), (P["v_abuse"], None), (P["v_abuse"], 1.0), (1.0, None), (0.5, None)):
            gcases.append(dict(grp="steel", key=col, k=g["seat_k"], mat=mat, kind="strike", v=v, hold=h, track=True, sub="single"))
        gcases.append(dict(grp="steel", key=col, k=g["seat_k"], mat=mat, kind="release", track=True, sub="release"))
    for v, h in ((P["v_play"], None), (P["v_play"], 0.45), (1.2, None)):
        gcases.append(dict(grp="steel", key=col, k=k_ch, mat="nom", kind="strike", v=v, hold=h, track=True, sub="chord"))
    for h in (None, 1.0):
        gcases.append(dict(grp="steel", key=col, k=k_ch_ab, mat="nom", kind="strike", v=P["v_abuse_chord"], hold=h, track=True, sub="chord20"))
    for F_ in (3.0, 6.0):
        gcases.append(dict(grp="steel", key=col, k=g["seat_k"], mat="nom", kind="press", F=F_, track=True, sub="press"))
t_g = time.time()
GRID = run_grid(gcases)
t_g = time.time() - t_g
sec("E3. r4.1 GRIDS - 6-key chord seat %.0f N/mm (F|F# fin: through the stripboard slot, keel to the balance rail since r4.4 fix 2b) swept 1.0-1.5 m/s in 0.05 steps, ghost grid 0.5-1.5 m/s in 0.1 steps, "
    "single keys 0.5 / 1.0 m/s, end keys A0 / C8, paper-strip holds (%d cases, %.0f s)" % (k_ch, len(gcases), t_g))
CS = {}
for c, r in GRID:
    if c["grp"] == "chord_sweep":
        CS.setdefault((c["key"], c["mat"]), []).append((c["v"], r["lift_max"], r["keep_gap_min"], r["lip_pull"]))
for (col, mat), rows in CS.items():
    pr("chord sweep %-5s %-9s max lift %.3f, min keeper %.2f | " % (col, mat, max(q[1] for q in rows), min(q[2] for q in rows)) +
       " ".join("%.2f:%.3f" % (q[0], q[1]) for q in rows))
CG = {}
for c, r in GRID:
    if c["grp"] == "chord_ghost":
        CG.setdefault(c["key"], {})["%.1f_h%.2f" % (c["v"], c["hold"])] = dict(r, v_note=c["v"], hold=c["hold"])
SG = {}
for c, r in GRID:
    if c["grp"] == "single_grid":
        SG.setdefault((c["key"], c["mat"]), {})["%.1f_%s" % (c["v"], m.hl(c["hold"]))] = dict(r, v_note=c["v"], hold=c["hold"])
for (col, mat), rr_ in SG.items():
    pr("single grid %-5s %-5s: " % (col, mat) + " | ".join("%s lift %.3f keep %.2f magnet %.0f %%" % (k, v["lift_max"], v["keep_gap_min"], 100 * v["ghost_frac"]) for k, v in rr_.items()))
END_DYN = {}
for c, r in GRID:
    if c["grp"] == "end":
        lab_ = ("release_f2" if c.get("fmul", 1.0) > 1 else "release") if c["kind"] == "release" else "%.1f_%s" % (c["v"], m.hl(c["hold"]))
        END_DYN.setdefault(c["key"], {}).setdefault(c["mat"], {})[lab_] = dict(r, v_note=c.get("v"), hold=c.get("hold"))
for nm_, d_ in END_DYN.items():
    for mat, rr_ in d_.items():
        pr("end key %-3s %-5s (seat %.0f N/mm): " % (nm_, mat, seat_end[nm_]) + " | ".join(
            ("%s %.1f Hz (full %.1f ms)" % (k, v["rep"], v["t100"])) if k.startswith("release") else
            ("%s lift %.3f keep %.2f pad %.0f N magnet %.0f %%" % (k, v["lift_max"], v["keep_gap_min"], v["up_peak"], 100 * v["ghost_frac"])) for k, v in rr_.items()))
STRIP = {}
for c, r in GRID:
    if c["grp"] == "strip":
        STRIP.setdefault((c["key"], c["gap"]), []).append((c["F"], r["gap_free"]))
strip_band = {}
for (col, gp), rows in sorted(STRIP.items()):
    rows.sort()
    Fs_ = [q[0] for q in rows]
    gs_ = [q[1] for q in rows]
    t_strip = 0.05
    Fp = None
    for i in range(len(rows) - 1):
        if gs_[i] >= t_strip >= gs_[i + 1]:
            Fp = Fs_[i] + (Fs_[i + 1] - Fs_[i]) * (gs_[i] - t_strip) / (gs_[i] - gs_[i + 1])
    strip_band["%s_%.2f" % (col, gp)] = dict(F_pinch=Fp, curve=rows)
    pr("paper strip %s gap %+.2f: stop-floor gap to the free felt " % (col, gp) + ", ".join("%.1f N %+.3f" % q for q in rows) +
       " -> a 0.05 strip is pinched from %s N" % ("%.2f" % Fp if Fp else "-"))
for col, c in (("white", "w"), ("black", "b")):
    # r4.4 fix 2b (verifier geometry major): the worst material set (beyond the pass line) is in the PLAY sweep poses too
    bm_ = max(r["b_max"] for c_, r in GRID if c_["grp"] in ("chord_sweep", "chord_ghost", "single_grid") and c_["key"] == col and c_.get("mat", "nom") in ("nom", "passline", "worst"))
    am_ = max(r["th_max"] for c_, r in GRID if c_["grp"] in ("chord_sweep", "chord_ghost", "single_grid") and c_["key"] == col and c_.get("mat", "nom") in ("nom", "passline", "worst"))
    g["b_ff_" + c] = max(g["b_ff_" + c], bm_ + math.radians(0.25))
    g["a_ff_" + c] = max(g["a_ff_" + c], am_ + math.radians(0.1))
pr("sweep 'ff' poses incl. the r4.1 grids (nominal + pass-line + worst materials, PLAY): lever %.2f / %.2f deg, key %.2f / %.2f deg" % (D(g["b_ff_w"]), D(g["b_ff_b"]), D(g["a_ff_w"]), D(g["a_ff_b"])))
# r4.4 (R44 issue 2): the return-overshoot poses keep the r4.3 case set (main dynamics: PLAY + ABUSE single key) and add the
# PLAY chord seats (1.5 / 1.2 m/s) and the PLAY grids, nominal + pass line; lever margin 0.25 deg as before.  The ABUSE 6-key
# chord (2.0 m/s) and the brief's 2.5 m/s at the chord seat are ABUSE cases: checked for no contact (after FDM) separately
over_r43 = dict(a_w=g["a_over_w"], a_b=g["a_over_b"], b_w=g["b_over_w"], b_b=g["b_over_b"])
over_f2 = {}
for col, c in (("white", "w"), ("black", "b")):
    src_ = [v for s_ in (CH, CH12) for k, v in s_[col].items() if isinstance(v, dict) and "b_min_rel" in v]
    src_ += [r for c_, r in GRID if c_["grp"] in ("chord_sweep", "chord_ghost", "single_grid") and c_["key"] == col and c_.get("mat", "nom") in ("nom", "passline")]
    # r4.4 fix 2b: the fix-2 set (nominal + pass line) for the record, then + the worst set (PLAY grids)
    over_f2[c] = (min(g["a_over_" + c], min(min(v["th_min_rel"] for v in src_), 0.0)), min(g["b_over_" + c], min(v["b_min_rel"] for v in src_) - math.radians(0.25)))
    src_ += [r for c_, r in GRID if c_["grp"] in ("chord_sweep", "single_grid") and c_["key"] == col and c_.get("mat") == "worst"]
    g["b_over_" + c] = min(g["b_over_" + c], min(v["b_min_rel"] for v in src_) - math.radians(0.25))
    g["a_over_" + c] = min(g["a_over_" + c], min(min(v["th_min_rel"] for v in src_), 0.0))
R["heights"].update(b_over_w=D(g["b_over_w"]), b_over_b=D(g["b_over_b"]), a_over_w=D(g["a_over_w"]), a_over_b=D(g["a_over_b"]),
                   over_f2={c_: (D(v_[0]), D(v_[1])) for c_, v_ in over_f2.items()})
pr("r4.4 sweep 'over' poses incl. the PLAY chord seats and grids (nominal + pass line + worst): lever %.2f / %.2f deg (r4.3 %.2f / %.2f), key %.3f / %.3f deg (r4.3 %.3f / %.3f)"
   % (D(g["b_over_w"]), D(g["b_over_b"]), D(over_r43["b_w"]), D(over_r43["b_b"]), D(g["a_over_w"]), D(g["a_over_b"]), D(over_r43["a_w"]), D(over_r43["a_b"])))

R["heights"].update(b_ff_w=D(g["b_ff_w"]), b_ff_b=D(g["b_ff_b"]), a_ff_w=D(g["a_ff_w"]), a_ff_b=D(g["a_ff_b"]))
vf_err = max(abs((r["v_front_bottom"] or 0.0) - c["v"]) for c, r in GRID if c["kind"] == "strike")
pr("grid strikes: achieved key-front speed within %.3f m/s of the target in every case (finger 1 N below 1.15 m/s, 3 N above)" % vf_err)
R["r41_vf_err"] = vf_err
R["r41"] = dict(k_ch=k_ch, seat_end=seat_end, chord_sweep={"%s_%s" % k_: v for k_, v in CS.items()}, chord_ghost=CG,
                single_grid={"%s_%s" % k_: v for k_, v in SG.items()}, end_dyn=END_DYN, strip=strip_band, t_grid=t_g)

# ghost evaluation with the r4 firmware filter
sec("E2. GHOST RE-TRIGGER - magnet rise vs the %.0f %% re-arm line; firmware filter (U6, r4.5 circuit 2nd wording = SCH-03 note 9): a note >= %.1f m/s whose key "
    "re-arms within %.0f ms of its note-on makes the key suspect; the FIRST re-press that lands within %.0f ms of that note-on is dropped if its finger-point descent is "
    "< %.2f m/s and < %.0f %% of the note's speed. Held strikes that re-arm run on to %.0f ms after the note-on (ghost_reland)"
    % (100 * P["rearm"], P["ghost_v_note"], P["ghost_win"], P["ghost_rep_max"], P["ghost_v_desc"], 100 * P["ghost_ratio"], P["ghost_long"]))
ghost = {}


def gfilter(v, v_note):
    """r4.5 circuit 2nd (item 9): the model rule is the firmware rule of SCH-03 note 9 - suspect = re-arm (magnet back over the
    re-arm line) within ghost_win of the note-on; the first re-press is judged by the speed ratio if it lands within ghost_rep_max
    of the note-on.  A re-armed key whose ghost does not land within the long run (ghost_long after the note-on) makes no second
    note in the run: nothing to drop (counted as handled; its float / creep is reported)."""
    armed = v["ghost_frac"] >= P["rearm"]
    t_ok = (v["ghost_t_arm"] or 0.0) < P["ghost_win"]
    rel = v.get("ghost_reland")
    if not armed:
        return False, False
    if rel is None:
        return True, True
    dropped = t_ok and v_note >= P["ghost_v_note"] and rel <= P["ghost_rep_max"] and v["ghost_v_desc"] < min(P["ghost_v_desc"], P["ghost_ratio"] * v_note)
    return armed, dropped


def gdet(v):
    """r4.5 circuit 2nd: the long-run record of a ghost case."""
    return dict(reland=v.get("ghost_reland"), settle=v.get("ghost_settle"), creep=v.get("ghost_creep"), land_est=v.get("ghost_land_est"), frac_end=v.get("frac_end"),
                t_run=(v.get("t_run") or 0.0) - (v.get("t_bottom") or 0.0), long=bool(v.get("ghost_long")))


for src, lab, table in (("main", "single key, weakest seat", dyn), ("chord", "6-key chord seat, 1.5 m/s", {c: CH[c] for c in ("white", "black")}),
                        ("chord12", "6-key chord seat, 1.2 m/s", {c: CH12[c] for c in ("white", "black")}),
                        ("chord20", "6-key ABUSE chord seat, 2.0 m/s", {c: CH20[c] for c in ("white", "black")})):
    for col in ("white", "black"):
        rows = []
        for k, v in table[col].items():
            if not (isinstance(v, dict) and "ghost_frac" in v and ("_h" in k)) or k.startswith(("ff_", "cons_")):
                continue
            vn = {"chord12": 1.2, "chord20": P["v_abuse_chord"]}.get(src, P["v_play"]) if k.startswith(("play", "chord20")) else P["v_abuse"]
            if k.startswith("chord20"):
                vn = P["v_abuse_chord"]
            armed, dropped = gfilter(v, vn)
            ghost["%s_%s_%s" % (src, col, k)] = dict(frac=v["ghost_frac"], v_desc=v["ghost_v_desc"], armed=bool(armed), dropped=bool(dropped), t_arm=v["ghost_t_arm"], **gdet(v))
            rows.append("%s %.0f %%%s" % (k, 100 * v["ghost_frac"], (" (re-arms, desc %.2f -> %s)" % (v["ghost_v_desc"], "dropped" if dropped else "NOT dropped")) if armed else ""))
        pr("%s %s: " % (lab, col) + " | ".join(rows))
for col, tab_ in CG.items():
    rows = []
    for k, v in tab_.items():
        armed, dropped = gfilter(v, v["v_note"])
        ghost["gridc_%s_%s" % (col, k)] = dict(frac=v["ghost_frac"], v_desc=v["ghost_v_desc"], armed=bool(armed), dropped=bool(dropped), t_arm=v["ghost_t_arm"], v_note=v["v_note"], **gdet(v))
        if armed:
            rows.append("%s %.0f %% desc %.2f %s" % (k, 100 * v["ghost_frac"], v["ghost_v_desc"], "dropped" if dropped else "NOT dropped"))
    pr("6-key chord seat ghost grid %s (0.5-1.5 m/s x 0.45-2 N): re-arming cases: " % col + ("; ".join(rows) if rows else "none"))
for (col, mat), tab_ in SG.items():
    for k, v in tab_.items():
        if v["hold"] is None:
            continue
        armed, dropped = gfilter(v, v["v_note"])
        ghost["grids_%s_%s_%s" % (mat, col, k)] = dict(frac=v["ghost_frac"], v_desc=v["ghost_v_desc"], armed=bool(armed), dropped=bool(dropped), t_arm=v["ghost_t_arm"], v_note=v["v_note"], **gdet(v))
for nm_, d_ in END_DYN.items():
    for mat, tab_ in d_.items():
        for k, v in tab_.items():
            if k.startswith("release") or v.get("hold") is None:
                continue
            armed, dropped = gfilter(v, v["v_note"])
            ghost["end_%s_%s_%s" % (nm_, mat, k)] = dict(frac=v["ghost_frac"], v_desc=v["ghost_v_desc"], armed=bool(armed), dropped=bool(dropped), t_arm=v["ghost_t_arm"], v_note=v["v_note"], **gdet(v))
for lab in ("pad e 0.10", "worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)", "pad e 0.07 (pass line)", "pass lines + v_floor 0.1", LAND_LAB):
    for col in ("white", "black"):
        for k, v in DYN[lab][col].items():
            if isinstance(v, dict) and "ghost_frac" in v and k.startswith(("play_h", "abuse_h")):
                armed, dropped = gfilter(v, P["v_play"] if k.startswith("play") else P["v_abuse"])
                ghost["%s_%s_%s" % (lab, col, k)] = dict(frac=v["ghost_frac"], v_desc=v["ghost_v_desc"], armed=bool(armed), dropped=bool(dropped), t_arm=v["ghost_t_arm"], **gdet(v))
LANDD = {}
for c_, r_ in GRID:
    if c_["grp"] == "land":
        LANDD.setdefault((c_["tag"], c_["nm"], c_["mat"]), []).append((c_, r_))


def _land_sum(rows):
    st_ = [(c_, r_) for c_, r_ in rows if c_["kind"] == "strike"]
    play_ = [r_ for c_, r_ in st_ if c_["sub"] == "play_chord"]
    ab_ = [r_ for c_, r_ in st_ if c_["sub"] != "play_chord"]
    rel_ = {c_["fmul"]: r_ for c_, r_ in rows if c_["kind"] == "release"}
    design_ = [r_ for c_, r_ in rows if c_["sub"] in ("play_chord", "abuse_single", "release")]
    brief_ = [r_ for c_, r_ in rows if c_["sub"] in ("abuse_at_chord_seat", "abuse_chord20")]
    gh_ = []
    for c_, r_ in st_:
        if c_.get("hold") is not None and c_["sub"] == "play_chord":
            armed_, dropped_ = gfilter(r_, c_["v"])
            gh_.append((c_["v"], c_["hold"], r_["ghost_frac"], r_["ghost_v_desc"], armed_, dropped_))
    return dict(lift_play=max(r_["lift_max"] for r_ in play_), keep_play=min(r_["keep_gap_min"] for r_ in play_),
                lift_abuse=max(r_["lift_max"] for r_ in ab_), keep_abuse=min(r_["keep_gap_min"] for r_ in ab_),
                ghost_max=max(q_[2] for q_ in gh_), ghost_armed=sum(1 for q_ in gh_ if q_[4]), ghost_not_dropped=sum(1 for q_ in gh_ if q_[4] and not q_[5]),
                ghost_desc_max=max([q_[3] for q_ in gh_ if q_[4]] + [0.0]),
                rep=rel_[1.0]["rep"], rep_2f=rel_[2.0]["rep"], t100=rel_[1.0]["t100"], t100_2f=rel_[2.0]["t100"],
                rest_peak=max(r_["rest_peak"] for r_ in play_ + ab_), cap_peak=max(r_["cap_peak"] for r_ in play_ + ab_),
                over_a=min(min(r_["th_min_rel"] for r_ in design_), 0.0), over_b=min(r_["b_min_rel"] for r_ in design_),
                over_a_brief=min(min(r_["th_min_rel"] for r_ in brief_), 0.0), over_b_brief=min(r_["b_min_rel"] for r_ in brief_),
                over_a_play=min(min(r_["th_min_rel"] for r_ in play_ + [rel_[1.0], rel_[2.0]]), 0.0), over_b_play=min(r_["b_min_rel"] for r_ in play_ + [rel_[1.0], rel_[2.0]]))


LSUM = {k_: _land_sum(v_) for k_, v_ in LANDD.items()}
sec("E4. r4.4 F / F# REST-FELT LANDING (R44 issue 2) - own key, own landing, 6-key chord seat %.0f N/mm; PLAY 0.5/1.0/1.5 m/s x let go / 0.45 / 1 / 2 N, "
    "ABUSE 2.5 m/s (chord seat = brief, single seat %.0f), ABUSE chord 2.0 m/s (%.0f), releases" % (k_ch, g["seat_k"], k_ch_ab))
for tag_, RL_ in (("r43", RLAND43), ("r44", RLAND)):
    for nm_ in ("F", "F#"):
        pr("%s %-2s felt x%.2f-%.2f lands x%.2f-%.2f (%.0f %% of the 8.0 felt, reaction %+.2f off the lever line):" % (tag_, nm_, RL_[nm_]["felt"][0], RL_[nm_]["felt"][1],
           RL_[nm_]["segs"][0][0], RL_[nm_]["segs"][0][1], 100 * RL_[nm_]["frac"], RL_[nm_]["dx"]))
        for mat in ("nom", "passline", "worst"):
            q_ = LSUM[(tag_, nm_, mat)]
            pr("   %-8s PLAY lift %.3f keeper %.2f ghost max %.0f %% (re-arm %d, not dropped %d, desc %.2f) | ABUSE lift %.3f keeper %.2f | rep %.1f / %.1f Hz, full %.1f / %.1f ms | "
               "over (PLAY chord seat + ABUSE single) key %.3f lever %.2f deg; ABUSE chord 2.0 / 2.5 at the chord seat key %.3f lever %.2f; PLAY only key %.3f lever %.2f | rest felt peak %.1f N"
               % (mat, q_["lift_play"], q_["keep_play"], 100 * q_["ghost_max"], q_["ghost_armed"], q_["ghost_not_dropped"], q_["ghost_desc_max"], q_["lift_abuse"], q_["keep_abuse"],
                  q_["rep"], q_["rep_2f"], q_["t100"], q_["t100_2f"], D(q_["over_a"]), D(q_["over_b"]), D(q_["over_a_brief"]), D(q_["over_b_brief"]),
                  D(q_["over_a_play"]), D(q_["over_b_play"]), q_["rest_peak"]))


def _own_over(tag_, which="", worst=True):
    out_ = {}
    for nm_ in ("F", "F#"):
        qs_ = [LSUM[(tag_, nm_, mat)] for mat in ("nom", "passline")]
        a_, b_ = min(q_["over_a" + which] for q_ in qs_), min(q_["over_b" + which] for q_ in qs_)
        if tag_ == "r44" and which == "" and worst:
            # r4.4 fix 2b (verifier geometry major): + the worst material set's PLAY return overshoot (ABUSE stays nom + pass line)
            qw_ = LSUM[(tag_, nm_, "worst")]
            a_, b_ = min(a_, qw_["over_a_play"]), min(b_, qw_["over_b_play"])
        out_[nm_] = (a_, b_ - math.radians(0.25))
    return out_


g["over_key"] = _own_over("r44")
pr("F / F# own return-overshoot poses (r4.4 felts, nominal + pass line, PLAY chord seat + ABUSE single key): " +
   ", ".join("%s key %.3f lever %.2f deg" % (k_, D(v_[0]), D(v_[1])) for k_, v_ in g["over_key"].items()))
STEEL = {}
for c_, r_ in GRID:
    if c_["grp"] == "steel":
        STEEL.setdefault((c_["key"], c_["sub"], c_["mat"]), []).append((c_, r_))
for (tag_, nm_, mat_), rows_ in LANDD.items():
    if tag_ != "r44":
        continue
    for c_, r_ in rows_:
        if c_["kind"] == "strike" and c_.get("hold") is not None and c_["sub"] != "abuse_at_chord_seat":
            armed_, dropped_ = gfilter(r_, c_["v"])
            ghost["land_%s_%s_%s_%.1f_%s_%s" % (tag_, nm_, mat_, c_["v"], m.hl(c_["hold"]), c_["sub"])] = dict(frac=r_["ghost_frac"], v_desc=r_["ghost_v_desc"], armed=bool(armed_),
                                                                                                           dropped=bool(dropped_), t_arm=r_["ghost_t_arm"], v_note=c_["v"], **gdet(r_))
nar = [k for k, v in ghost.items() if v["armed"]]
nnd = [k for k, v in ghost.items() if v["armed"] and not v["dropped"]]
pr("ghost cases re-arming mechanically: %d of %d; not dropped by the filter: %d %s" % (len(nar), len(ghost), len(nnd), nnd))
# r4.5 circuit 2nd (item 9): when (if at all) the re-armed ghosts land again
nrl = [k for k in nar if ghost[k]["reland"] is not None]
_ga = [ghost[k] for k in nar]
_rl_max = max([ghost[k]["reland"] for k in nrl] + [0.0])
_st_max = max([q_["settle"] or 0.0 for q_ in _ga] + [0.0])
_cr = [q_["creep"] for q_ in _ga if q_["creep"] is not None]
_le = [q_["land_est"] for q_ in _ga if q_["land_est"] is not None and q_["reland"] is None]
_tr_min = min(q_["t_run"] for q_ in _ga) if _ga else 0.0
_arm_max = max([q_["t_arm"] or 0.0 for q_ in _ga] + [0.0])
pr("r4.5 circuit 2nd: re-armed cases run on to %.0f ms after the note-on (shortest run %.0f ms of simulated time): %d of %d land again (latest %.0f ms after the note-on; window %.0f ms); "
   "the key stops at its float point by %.0f ms at the latest (re-arm by %.1f ms); float at the end of the run %s; creep at the end max %.5f m/s at the magnet (model friction: linear below 0.2 mm/s slip) "
   "-> at that rate the earliest would reach the bottom %.1f s after the note-on"
   % (P["ghost_long"], _tr_min, len(nrl), len(nar), _rl_max, P["ghost_rep_max"], _st_max, _arm_max,
      "%.0f-%.0f %%" % (100 * min(q_["frac_end"] for q_ in _ga), 100 * max(q_["frac_end"] for q_ in _ga)) if _ga else "-", max(_cr + [0.0]), (min(_le) / 1000.0) if _le else float("nan")))
for k in nar:
    q_ = ghost[k]
    pr("   %-70s rise %3.0f %% re-arm %5.1f ms, settle %s ms, desc %.3f m/s, lands %s, float at %.0f ms %.0f %%, creep %.5f m/s%s"
       % (k[:70], 100 * q_["frac"], q_["t_arm"] or 0.0, ("%.0f" % q_["settle"]) if q_["settle"] is not None else "-", q_["v_desc"], ("%.0f ms" % q_["reland"]) if q_["reland"] is not None else "no",
          q_["t_run"], 100 * (q_["frac_end"] or 0.0), q_["creep"] or 0.0, (" -> bottom ~%.1f s" % (q_["land_est"] / 1000.0)) if q_["land_est"] is not None and q_["reland"] is None else ""))
R["ghost"] = ghost
R["ghost_summary"] = dict(n=len(ghost), armed=nar, not_dropped=nnd, relanded=nrl, reland_max=_rl_max, settle_max=_st_max, creep_max=max(_cr + [0.0]),
                          land_est_min=min(_le) if _le else None, t_run_min=_tr_min, t_arm_max=_arm_max, rep_max=P["ghost_rep_max"], long=P["ghost_long"],
                          frac_end=(min(q_["frac_end"] for q_ in _ga), max(q_["frac_end"] for q_ in _ga)) if _ga else None)
# force histories (roll check)
hist_rec = {}
for col, A in (("white", Aw), ("black", Ab)):
    Dh = m.dyn_for(g, A)
    ev = m.strike(Dh, dyn[col]["rest_state"], dyn[col]["v0_play"], F_hold=1.0, t_end=120.0, record=True, rec_every=25)
    hist_rec[col] = ev["hist"]

# ----------------------------------------------------------------------------------------------- F tilt
sec("F. TRANSPORT TILT - module rotated about x, keys settle 400 ms, then laid flat 400 ms (lip friction included)")
tilt = {}
for mu in (None, 0.35):
    for ang in (90, -90, -120, 180):
        for A, nm in ((Aw, "white"), (Ab, "black")):
            r_ = m.tilt_check(g, A, ang, mu_lip=mu)
            tilt["%s_%d_%s" % (nm, ang, "mu%.2f" % r_["mu_lip"])] = r_
            pr("%s %+4d deg, lip mu %.2f: notch lift %.2f (pop-out %.2f), y offset %+.2f, keeper %.2f N; laid flat: lift %.3f, front %+.3f, y %+.2f"
               % (nm, ang, r_["mu_lip"], r_["notch_lift"], P["lift_popout"], r_["notch_y_offset"], r_["keeper_force"], r_["reseat_lift"], r_["reseat_front_dz"], r_["reseat_y"]))
R["tilt"] = tilt
# snap law (RET-2): quasi-static pull-off of the model's lip law
Rn = P["notch_R"] - P["cloth"]
lip_h = math.sqrt(Rn ** 2 - P["block_lift"] ** 2)
lip_touch = math.hypot(lip_h, P["block_lift"] - (Rn - P["rod_k"] / 2)) - P["rod_k"] / 2
R["snap"] = dict(lip_clear_rest=lip_touch, popout=P["lift_popout"], F_model=1.99, F_coupon=(P["snap_F_min"], P["snap_F"]),
                 shock_g_upside=1.99 / (Aw.mk * m.G) if Aw.mk else None)
pr("snap notch (RET-2): lips clear the rod by %.2f at rest, touch after %.2f of lift, let go at %.2f; model lip law pull-off 1.99 N (mu 0.25) -> coupon band %.0f-%.0f N; "
   "upside-down shock that pops a white key %.1f g (key %.1f g)" % (lip_touch, P["lift_play"], P["lift_popout"], P["snap_F_min"], P["snap_F"], 1.99 / (Aw.mk * m.G), Aw.mk))

# r4.4 fix 2 (verifier geometry major 3): the key poses carry the notch seating / sinking on the rod (translation after the
# rotation about K): rest / dip exact planar states, ff = lowest rod point near / past the bottom, over = lowest while above
# rest, over every dynamic case (main + chord seats + grids); a colour whose block lip region then comes within 1.3 of the
# balance-rail top gets a pocket behind the pin row
_xk = {}
for col in ("white", "black"):
    rows_ = [v for s_ in (CH, CH12, CH20) for k, v in s_[col].items() if isinstance(v, dict) and "kz_ff" in v]
    rows_ += [r for c_, r in GRID if c_.get("key") == col and isinstance(r, dict) and "kz_ff" in r]
    _xk[col] = dict(ff=min([r["kz_ff"] or 1e9 for r in rows_] + [1e9]), over=min([r["kz_over"] or 1e9 for r in rows_] + [1e9]))
KSH, RPOCK = m.key_pose_shifts(P, g, dyn, _xk)
R["key_shift"] = dict(shift={c_: {k_: list(v_) for k_, v_ in q_.items()} for c_, q_ in KSH.items()}, pocket=RPOCK, extra=_xk)

# ----------------------------------------------------------------------------------------------- G clearances
sec("G. CLEARANCE SWEEP - keys rest/dip/ff/over, levers settled rest/dip/ff/overshoot (all from the dynamics), own pairs coupled; "
    "yaw play (keys +-%.2f at the pin + tab play +-%.2f, levers +-%.2f at the front) over the shared y-range; rule nominal - %.1f >= %.1f"
    % (P["yaw_pin"], P["tab_play"], P["yaw_lever"], m.TOL, m.CLEAR_MIN))
pk, pl = m.poses_for(P, g)
recs = m.clearance_sweep(P, g, pk, pl)
# r4.5 fix 2 (resume): the first fix-2 pass keel (z21, fin front y152) against keys E / F / F# in every pose
_kf21_ = [f_ for f_ in m.fixed_prisms(dict(P, fin_keel=(P["fin_keel"][0], P["fin_keel"][1], 21.0), fin_keel_front=None), g, play=True) if f_[0].startswith("fin keel")]
_bod21_ = [(("key", nm_, 0), "key", nm_, 0.0, m.yaw_inflate(P, m.key_prisms(P, keys[nm_], g["caps"]["black" if keys[nm_]["black"] else "white"], lay["levers"][nm_]), "key", keys[nm_]["black"]))
           for nm_ in ("E", "F", "F#")]
_r21_ = sorted([q_ for q_ in m.clearance_sweep(P, g, pk, pl, extra_moving=dict(fixed=_kf21_, bodies=_bod21_)) if q_["cls"].endswith("fixed")], key=lambda q_: q_["d"])
_kfn_ = [f_ for f_ in m.fixed_prisms(P, g, play=True) if f_[0].startswith("fin keel")]
_rn_ = sorted([q_ for q_ in m.clearance_sweep(P, g, pk, pl, extra_moving=dict(fixed=_kfn_, bodies=_bod21_)) if q_["cls"].endswith("fixed")], key=lambda q_: q_["d"])
R["keel_rail"]["keel21_clear"] = dict(d=_r21_[0]["d"], key=_r21_[0]["a"], part=_r21_[0]["part_a"], pose=_r21_[0]["pose_a"]) if _r21_ else None
_ffin_ = [f_ for f_ in m.fixed_prisms(P, g, play=True) if f_[0] == "fin" and P["board_x"][0] < 0.5 * (f_[1] + f_[2]) < P["board_x"][1]]
_rf_ = sorted([q_ for q_ in m.clearance_sweep(P, g, pk, pl, extra_moving=dict(fixed=_ffin_, bodies=_bod21_)) if q_["cls"].endswith("fixed")], key=lambda q_: q_["d"])
R["keel_rail"]["fin_clear"] = dict(d=_rf_[0]["d"], key=_rf_[0]["a"], part=_rf_[0]["part_a"], pose=_rf_[0]["pose_a"]) if _rf_ else None
pr("r4.5 fix 2 F|F# fin (front y%.1f) vs keys E / F / F#: min %.2f (%s %s, %s)" % (m.keel_front(P), _rf_[0]["d"], _rf_[0]["a"], _rf_[0]["part_a"], _rf_[0]["pose_a"]))
R["keel_rail"]["keel_clear"] = dict(d=_rn_[0]["d"], key=_rn_[0]["a"], part=_rn_[0]["part_a"], pose=_rn_[0]["pose_a"]) if _rn_ else None
pr("r4.5 fix 2 keel vs keys E / F / F# (all poses): first fix-2 pass keel z21 min %.2f (%s %s, %s) -> rejected; this keel z%.1f to y%.1f min %.2f (%s %s, %s)"
   % (_r21_[0]["d"], _r21_[0]["a"], _r21_[0]["part_a"], _r21_[0]["pose_a"], P["fin_keel"][2], m.keel_front(P), _rn_[0]["d"], _rn_[0]["a"], _rn_[0]["part_a"], _rn_[0]["pose_a"]))
S = m.summarize_clearances(recs)
nbad = sum(1 for r_ in S if not r_["ok"])
pr("%d part pairs checked (%d pose records); %d below 1.3 nominal" % (len(S), len(recs), nbad))
FLO, PGAP = m.lever_float(lay, P, g["collars"])
pr("r4.4 fix 2: key poses translated by the notch on the rod (dy, dz after the rotation about K): " + " | ".join(
    "%s " % c_ + ", ".join("%s (%+.3f, %+.3f)" % (k_, v_[0], v_[1]) for k_, v_ in KSH[c_].items() if k_ in ("rest", "dip", "ff", "over")) for c_ in ("w", "b"))
   + "; balance-rail pocket: " + "; ".join("%s %s" % (c_, ("top z%.2f behind y%.1f (lowest lip-region corner z%.3f at %s)" % (q_["z"], q_["y"], q_["zmin"], q_["pose"])) if q_ else "none") for c_, q_ in RPOCK.items()))
pr("r4.4 fix 2: lever axial float on the rod (left / right, from the collar / boss gap chain; bosses +%.2f, collars >= %.2f): " % (P["boss_extra"], P["collar_min"])
   + ", ".join("%s %.3f/%.3f" % (k_, v_[0], v_[1]) for k_, v_ in FLO.items()) + "; neighbour free gaps " + ", ".join("%s|%s %.3f" % (a_, b_, v_) for (a_, b_), v_ in PGAP.items())
   + "; pad bars +-%.1f sideways (pads, wedges, strips, leaves, grip) - all in the sweep" % P["pad_bar_clear"])
cls_min = {}
for r_ in S:
    c = r_["cls"]
    if c not in cls_min or r_["d"] < cls_min[c]["d"]:
        cls_min[c] = r_
for c, r_ in sorted(cls_min.items(), key=lambda kv: kv[1]["d"]):
    pr("  min %-14s %.2f mm (after tol %.2f): %s [%s, %s] vs %s [%s %s] (%s)"
       % (c, r_["d"], r_["after_tol"], r_["a"], r_["part_a"], r_["pose_a"], r_["b"], r_["part_b"], r_["pose_b"], r_["mode"]))
pr("closest 20 pairs:")
for r_ in S[:20]:
    pr("  %.2f %-4s %-22s %-5s %-26s | %-34s %-5s %s" % (r_["d"], r_["mode"], r_["a"], r_["pose_a"], r_["part_a"], r_["b"][:34], r_["pose_b"], r_["part_b"]))
pr("designed contacts / sliding fits excluded: " + "; ".join("%s~%s" % e for e in m.EXCLUDE))
named_rules = [
    ("건반 ↔ 밸런스 레일", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("balance rail")),
    ("건반 옆벽 ↔ 건반 봉", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("key rod")),
    ("건반 ↔ 센서 바", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("sensor bar")),
    ("건반 ↔ 센서 바 오른쪽 턱 (v3 P112, r4.5 회로 2차)", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("sensor-bar ledge")),
    ("건반 빔·꼬리 ↔ 제어 기판 부품", lambda q: q["cls"] == "key-fixed" and ("board" in q["b"] or "RP2040" in q["b"])),
    ("건반 꼬리·쉼 펠트 ↔ USB-C 플러그", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("USB-C plug")),
    ("건반 ↔ 가림판 띠", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("cover curtain")),
    ("건반 옆벽·리브 ↔ 키퍼 훅", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("keeper")),
    ("건반 꼬리 ↔ 도브테일", lambda q: q["cls"] == "key-fixed" and "dovetail" in q["b"]),
    ("건반 ↔ 핀", lambda q: q["cls"] == "key-fixed" and q["b"] == "fin"),
    ("흑건 ↔ 이웃 백건", lambda q: q["cls"] == "key-key" and ((q["a"].split()[1] in ("C#", "D#", "F#", "G#", "A#")) != (q["b"].split()[1][:2] in ("C#", "D#", "F#", "G#", "A#")))),
    ("백건 ↔ 백건 (x 틈)", lambda q: q["cls"] == "key-key" and q["mode"] == "x" and "skin" in q["part_a"] and "skin" in q["part_b"]),
    ("자기 건반 ↔ 자기 레버", lambda q: q["cls"] == "own key-lever"),
    ("건반 ↔ 이웃 레버", lambda q: q["cls"] == "key-lever"),
    ("레버 ↔ 레버", lambda q: q["cls"] == "lever-lever"),
    ("레버 ↔ 핀", lambda q: q["cls"] == "lever-fixed" and q["b"] == "fin"),
    ("레버 ↔ 윗판", lambda q: q["cls"] == "lever-fixed" and q["b"].startswith("top plate")),
    ("레버 ↔ 패드 바·레일", lambda q: q["cls"] == "lever-fixed" and q["b"].startswith("pad bar")),
    ("레버 ↔ 패드 쐐기", lambda q: q["cls"] == "lever-fixed" and q["b"].startswith("pad wedge")),
    ("레버 ↔ 이웃 패드", lambda q: q["cls"] == "lever-fixed" and q["b"].startswith("up-stop pad")),
    ("레버 ↔ 뒷벽", lambda q: q["cls"] == "lever-fixed" and q["b"].startswith("rear wall")),
    ("레버 ↔ 가림판 띠", lambda q: q["cls"] == "lever-fixed" and q["b"].startswith("cover curtain")),
    ("건반 블록 ↔ 밸런스 레일(낮춘 곳·받침)", lambda q: q["cls"] == "key-fixed" and q["b"].startswith("balance rail") and q["part_a"] == "balance block"),
]
named = {}
for lab, fn in named_rules:
    cand = [q for q in recs if fn(q)]
    if cand:
        q = min(cand, key=lambda q: q["d"])
        named[lab] = dict(d=q["d"], after_tol=q["d"] - m.TOL, a=q["a"], part_a=q["part_a"], pose_a=q["pose_a"], b=q["b"], part_b=q["part_b"], pose_b=q["pose_b"])
        pr("  named: %-26s %.2f (after tol %.2f)  %s [%s, %s] vs %s [%s %s]" % (lab, q["d"], q["d"] - m.TOL, q["a"], q["part_a"], q["pose_a"], q["b"], q["part_b"], q["pose_b"]))
dove = [r_ for r_ in S if "dovetail" in r_["b"]]
dmin = min(dove, key=lambda r_: r_["d"]) if dove else None
# designed stops / fits reported separately
cb_tab = []
for nm in m.ORDER:
    A = Ab if keys[nm]["black"] else Aw
    cb = P["b_crossbar_y"] if keys[nm]["black"] else P["w_crossbar_y"]
    ytab = (P["b_tab_y"] if keys[nm]["black"] else P["w_tab_y"])[0]
    for a_ in (0.0, A.a_dip, pk[nm]["ff"], pk[nm]["over"]):
        for zc_ in (P["key_bot"], P["key_bot"] + P["crossbar_t"]):
            p = A.kp((cb[1], zc_), a_)
            cb_tab.append(ytab - p[0])
pr("designed rear y-stop (crossbar rear corners -> 0.5T cloth on the guide-tab front face): %.2f nominal, min over all poses %.2f"
   % (P["w_tab_y"][0] - P["w_crossbar_y"][1], min(cb_tab)))
felt_w = [f for f in m.fixed_prisms(P, g) if f[0].startswith("white front felt")][0]
cf = 1e9
for nm in m.ORDER:
    if keys[nm]["black"]:
        continue
    for t_, x0_, x1_, poly_ in m.key_prisms(P, keys[nm], caps["white"], lay["levers"][nm]):
        if t_.startswith(("crossbar", "guide rib")):
            for a_ in (0.0, Aw.a_dip, pk[nm]["ff"], pk[nm]["over"]):
                cf = min(cf, m.poly_dist([m.rot(p, P["K"], a_) for p in poly_], felt_w[3]))
pr("white front felt (y%.1f-%.1f) vs crossbar / guide ribs over all poses: %.2f mm (after tol %.2f) [r3 0.88]" % (P["w_felt_y"][0], P["w_felt_y"][1], cf, cf - m.TOL))
# balance pin vs the snap-lip wall and the slot rear end (RET-4), over all key poses
yl0_, yl1_ = m.block_lip_y(P)
pin_wall, pin_slot = 1e9, 1e9
for nm in ("D", "C#"):
    A = Ab if keys[nm]["black"] else Aw
    for a_ in (0.0, A.a_dip, pk[nm]["ff"], pk[nm]["over"]):
        for zz in (P["K"][1] + P["block_lift"], P["block_step_z"]):
            pin_wall = min(pin_wall, A.kp((yl0_, zz), a_)[0] - (P["pin_y"] + P["pin_d"] / 2))
            pin_slot = min(pin_slot, A.kp((P["slot_y"][1], P["block_step_z"]), a_)[0] - (P["pin_y"] + P["pin_d"] / 2))
pr("balance pin rear face vs the snap-lip wall of the stepped block: %.2f (r3 0.19-0.26); vs the slot rear end %.2f (pin moved to y%.1f, rail front y%.1f -> hole front wall %.1f)"
   % (pin_wall, pin_slot, P["pin_y"], P["rail_front_y"], P["pin_y"] - P["pin_d"] / 2 - P["rail_front_y"]))
# r4.4 (R44 issue 1): the r4.3 front top lip (y150-168, not in the r4.3 sweep) against its own pad, re-derived on this model
lip43 = dict(d=1e9)
for nm, xl in lay["levers"].items():
    pad_, wedge_ = m.pad_polys(P, g, keys[nm]["black"])
    for sgn in (-1, 1):
        # the r4.3 lip: side wall 0.8 (= carrier_wall) and lip 0.8 (r4.4 fix 2b changed them to 0.7 / 0.9, same inner edge)
        xa_, xb_ = sorted((xl + sgn * (P["lever_w"] / 2 - P["carrier_wall"] - 0.8), xl + sgn * (P["lever_w"] / 2 - P["carrier_wall"])))
        for pz_ in ("rest", "dip", "dip_rigid", "ff", "over"):
            pg_ = [m.rot(p_, P["L"], -pl[nm][pz_]) for p_ in m.rect(P["y_steel_front"], P["lip_gap_y"][0], P["z_st"], P["z_st"] + P["lip"])]
            A_ = ("lip", xa_, xb_, pg_, (P["yaw_lever"] / (P["L"][0] - P["y_lever_front"]), P["L"][0], 0.0))
            d_, mode_ = m.pair_dist(A_, ("up-stop pad", xl - P["pad_w"] / 2, xl + P["pad_w"] / 2, pad_))
            if d_ < lip43["d"]:
                lip43 = dict(d=d_, mode=mode_, lever=nm, pose=pz_, b=D(pl[nm][pz_]), corner=pg_[2])
pr("r4.3 front top lip y%.0f-%.0f (lever frame) vs its own pad: min %.3f (%s) at lever %s pose %s (b %.2f deg): rear-top corner at world y%.2f z%.2f -> after FDM %.3f (rule 1.0)"
   % (P["y_steel_front"], P["lip_gap_y"][0], lip43["d"], lip43["mode"], lip43["lever"], lip43["pose"], lip43["b"], lip43["corner"][0], lip43["corner"][1], lip43["d"] - m.TOL))
# the sweep keeps only the closest part of each lever per fixed part, so the lips are measured on their own here
_FX = m.with_bar_play(P, m.fixed_prisms(P, g, play=True))       # r4.4 fix 2: pad-bar play
lip44_all = []
for nm, xl in lay["levers"].items():
    _yk = (P["yaw_lever"] / (P["L"][0] - P["y_lever_front"]), P["L"][0], FLO[nm])      # r4.4 fix 2: + axial float
    for t_, x0_, x1_, poly_ in m.lever_prisms(P, xl, g["collars"][nm]):
        if not t_.startswith("carrier top snap lip"):
            continue
        for pz_ in ("rest", "dip", "dip_rigid", "ff", "over"):
            pg_ = [m.rot(p_, P["L"], -pl[nm][pz_]) for p_ in poly_]
            for f_ in _FX:
                if f_[1] - x1_ > 6 or x0_ - f_[2] > 6 or not f_[0].startswith(("up-stop pad", "pad wedge", "pad bar", "top plate", "fin", "cover curtain")):
                    continue
                d_, mode_ = m.pair_dist((t_, x0_, x1_, pg_, _yk), f_)
                lip44_all.append(dict(d=d_, a="lever " + nm, part_a=t_, pose_a=pz_, b=f_[0], mode=mode_))
lip44_min = min(lip44_all, key=lambda q: q["d"])
lip44_pad = min([q for q in lip44_all if q["b"].startswith("up-stop pad")], key=lambda q: q["d"])
lip44_rail = min([q for q in lip44_all if q["b"].startswith("pad bar")], key=lambda q: q["d"])
pr("r4.4 top snap lips (y%s, lever frame) in the sweep: min %.3f %s [%s %s] vs %s; vs the pads %.3f (%s %s); vs the pad bars / rails %.3f (%s %s %s)"
   % (" / ".join("%.0f-%.0f" % q for q in P["lip_segs"]), lip44_min["d"], lip44_min["a"], lip44_min["part_a"], lip44_min["pose_a"], lip44_min["b"],
      lip44_pad["d"], lip44_pad["a"], lip44_pad["pose_a"], lip44_rail["d"], lip44_rail["a"], lip44_rail["pose_a"], lip44_rail["b"]))
rodq = [q for q in recs if q["b"].startswith(("lever rod", "fin boss bore"))]
rod_min = min(rodq, key=lambda q: q["d"]) if rodq else None
Frod_ = [f_ for f_ in m.fixed_prisms(P, g) if f_[0].startswith(("lever rod", "fin boss bore"))]
plug_ = [f_ for f_ in Frod_ if f_[0].startswith("lever rod end plug")][0]
rodp_ = [f_ for f_ in Frod_ if f_[0].startswith("lever rod D4")][0]
bores_ = [f_ for f_ in Frod_ if f_[0].startswith("fin boss bore")]
rodck = dict(plug=(plug_[1], plug_[2]), rod=(rodp_[1], rodp_[2]), blind_end=bores_[-1][2], play_left=rodp_[1] - plug_[2], play_right=bores_[-1][2] - rodp_[2],
             plug_face_to_fin_face=plug_[1] - lay["fins"][0][0], seam_gap=(P["module_w"] + lay["fins"][0][0]) - lay["fins"][-1][1],
             rod_len_tol=0.2, sweep_min=(rod_min["d"], rod_min["a"], rod_min["part_a"], rod_min["b"]) if rod_min else None, n_bores=len(bores_))
pr("r4.4 lever rod x%.1f-%.1f, fin-boss bores %d (D4.0, the right end fin blind to x%.1f = wall %.1f), plug x%.2f-%.2f flush with the end-fin face (seam gap %.2f unchanged); "
   "axial play %.2f + %.2f (rod %.1f +- %.1f: %.2f-%.2f); closest moving part in the sweep %s"
   % (rodck["rod"][0], rodck["rod"][1], rodck["n_bores"], rodck["blind_end"], lay["fins"][-1][1] - rodck["blind_end"], rodck["plug"][0], rodck["plug"][1], rodck["seam_gap"],
      rodck["play_left"], rodck["play_right"], rodck["rod"][1] - rodck["rod"][0], rodck["rod_len_tol"],
      rodck["play_left"] + rodck["play_right"] - rodck["rod_len_tol"], rodck["play_left"] + rodck["play_right"] + rodck["rod_len_tol"],
      "%.2f (%s [%s] vs %s)" % rodck["sweep_min"] if rodck["sweep_min"] else "-"))
# r4.4 (R44 issue 2): F / F# at the brief's conservative ABUSE 2.5 m/s on the chord seat (no-damage check: no contact after FDM)
g_ov_ = g["over_key"]
g["over_key"] = _own_over("r44", "_brief")
pk_b_, pl_b_ = m.poses_for(P, g)
recs_b_ = m.clearance_sweep(P, g, pk_b_, pl_b_)
fq_b_ = [q for q in recs_b_ if any(q[k_] in ("key F", "key F#", "lever F", "lever F#") for k_ in ("a", "b")) and "over" in (q["pose_a"], q["pose_b"])]
brief_min = min(fq_b_, key=lambda q: q["d"])
g["over_key"] = g_ov_
# r4.3 felts + r4.3 landing overshoot (the 'before' of issue 2), same pose rules
g["over_key"] = _own_over("r43")
pk_43_, pl_43_ = m.poses_for(P43, g)
recs_43_ = m.clearance_sweep(P43, g, pk_43_, pl_43_)
S43_ = m.summarize_clearances(recs_43_)
bad43_ = [q for q in S43_ if not q["ok"]]
g["over_key"] = g_ov_
pr("r4.3 felts (8.0 centred, F / F# land %.0f / %.0f %%) with their own overshoot (key %.3f / %.3f, lever %.2f / %.2f deg): %d pairs below 1.3, min %.3f: %s"
   % (100 * RLAND43["F"]["frac"], 100 * RLAND43["F#"]["frac"], D(_own_over("r43")["F"][0]), D(_own_over("r43")["F#"][0]), D(_own_over("r43")["F"][1]), D(_own_over("r43")["F#"][1]),
      len(bad43_), S43_[0]["d"], "; ".join("%.3f %s [%s %s] vs %s [%s]" % (q["d"], q["a"], q["part_a"], q["pose_a"], q["b"], q["part_b"]) for q in bad43_)))
pr("r4.4 felts, F / F# at their ABUSE overshoot (6-key chord 2.0 m/s, and the brief's 2.5 m/s on the chord seat; key %.3f / %.3f, lever %.2f / %.2f deg): min %.3f (after FDM %.3f > 0: no contact, no damage) %s [%s] vs %s [%s]"
   % (D(_own_over("r44", "_brief")["F"][0]), D(_own_over("r44", "_brief")["F#"][0]), D(_own_over("r44", "_brief")["F"][1]), D(_own_over("r44", "_brief")["F#"][1]),
      brief_min["d"], brief_min["d"] - m.TOL, brief_min["a"], brief_min["part_a"], brief_min["b"], brief_min["part_b"]))
fq_ = [q for q in recs if any(q[k_] in ("key F", "key F#", "lever F", "lever F#") for k_ in ("a", "b")) and "over" in (q["pose_a"], q["pose_b"])]
ff_over_min = min(fq_, key=lambda q: q["d"])
pr("r4.4 felts, F / F# own overshoot poses in the module sweep: closest %.3f (after FDM %.3f) %s [%s] vs %s [%s]"
   % (ff_over_min["d"], ff_over_min["d"] - m.TOL, ff_over_min["a"], ff_over_min["part_a"], ff_over_min["b"], ff_over_min["part_b"]))
# r4.4 (R44 issue 3): the key 'dip' pose is the truly settled 1 N bottom with the pad for both colours; rigid kept as 'dip_rigid'
dipck = {}
for col_, A_, hs_ in (("white", Aw, g["held_pad_w"]), ("black", Ab, g["held_pad_b"])):
    kq_ = m.key_point_world(A_, hs_, P["K"])
    fr_ = m.key_point_world(A_, hs_, A_.front)
    ang_front = D(math.atan2(fr_[1] - P["K"][1], fr_[0] - P["K"][0]) - math.atan2(A_.front[1] - P["K"][1], A_.front[0] - P["K"][0]))
    dipck[col_] = dict(held=D(hs_[0]), rigid=D(A_.a_dip), lever_held=D(hs_[1]), lever_rigid=D(A_.b_dip), notch_dy=kq_[0] - P["K"][0], notch_dz=kq_[1] - P["K"][1],
                       front_angle=ang_front, front_z_held=fr_[1], front_z_rigid=A_.kp(A_.front, A_.a_dip)[1])
pr("r4.4 dip export (settled 1 N with the pad = full planar key state; rigid = kinematic bottom): " + " | ".join(
    "%s key %.3f deg + notch shift (%+.3f, %+.3f) = front point %.3f deg about K, front z%.2f (rigid %.3f deg, z%.2f); lever %.3f (rigid %.3f)"
    % (c_, q_["held"], q_["notch_dy"], q_["notch_dz"], q_["front_angle"], q_["front_z_held"], q_["rigid"], q_["front_z_rigid"], q_["lever_held"], q_["lever_rigid"]) for c_, q_ in dipck.items())
   + "; r4.3 exported max(settled angle, rigid angle) = the rigid angle for both colours; the sweep checks both poses")
# carrier top lips beside the pad (soft foam, designed proximity)
lip_pad, lip_pad_flat = 1e9, 1e9
for nm, xl in lay["levers"].items():
    blk = keys[nm]["black"]
    pad, wedge = m.pad_polys(P, g, blk)
    for t_, x0_, x1_, poly_ in m.lever_prisms(P, xl):
        if t_.startswith("carrier side wall"):
            for b_ in (pl[nm]["dip"], pl[nm]["ff"]):
                pg = [m.rot(p, P["L"], -b_) for p in poly_]
                # r4.4 fix 2: the lever's axial float + yaw and the pad bar's +-0.3 counted
                d_, mode_ = m.pair_dist((t_, x0_, x1_, pg, (P["yaw_lever"] / (P["L"][0] - P["y_lever_front"]), P["L"][0], FLO[nm])),
                                        ("pad", xl - P["pad_w"] / 2, xl + P["pad_w"] / 2, pad, (0.0, 0.0, (P["pad_bar_clear"], P["pad_bar_clear"]))))
                lip_pad = min(lip_pad, d_)
                # the r4.4-fix-1 wall (top = steel top in the pad zone), same play: the verifier's 0.71
                P_f1 = dict(P, wall_drop_pad=0.0, carrier_side_wall=P["carrier_wall"], lip_over=0.8)      # the fix-1 carrier (0.8 walls)
                sw1_ = [q_ for q_ in m.lever_prisms(P_f1, xl) if q_[0] == t_][0]
                pg1 = [m.rot(p, P["L"], -b_) for p in sw1_[3]]
                d1_, _ = m.pair_dist((t_, sw1_[1], sw1_[2], pg1, (P["yaw_lever"] / (P["L"][0] - P["y_lever_front"]), P["L"][0], FLO[nm])),
                                     ("pad", xl - P["pad_w"] / 2, xl + P["pad_w"] / 2, pad, (0.0, 0.0, (P["pad_bar_clear"], P["pad_bar_clear"]))))
                lip_pad_flat = min(lip_pad_flat, d1_)
pr("carrier side walls beside the pad (x gap to the wall %.2f; r4.4 fix 2: lever float + yaw and pad-bar +-%.1f counted): min 3D distance over the bottom / ff poses %.2f "
   "(side-wall top %.1f below the steel top between the lips; with the fix-1 wall top = steel top %.2f)"
   % ((P["lever_w"] - P["pad_w"]) / 2 - P.get("carrier_side_wall", P["carrier_wall"]), P["pad_bar_clear"], lip_pad, P["wall_drop_pad"], lip_pad_flat))
ff = m.fixed_fixed_checks(P, g)
ff["felt_crossbar_min"] = cf
pr("fixed-fixed: seam gaps plates %.2f, end fins %.2f; USB-C plug vs shelf / fins / ribs / rear wall %.2f (%s); neighbour's dovetail groove vs the end fin %.2f"
   % (ff["seam_gap_plates"], ff["seam_gap_end_fins"], ff["usb_plug_min"][0], ff["usb_plug_min"][1], ff["dovetail_zone_vs_end_fin"][0]))
R["clear"] = dict(n_pairs=len(S), n_bad=nbad, min=S[0]["d"], min_after_tol=S[0]["after_tol"],
                  cls_min={c: dict(d=r_["d"], a=r_["a"], part_a=r_["part_a"], pose_a=r_["pose_a"], b=r_["b"], part_b=r_["part_b"], pose_b=r_["pose_b"]) for c, r_ in cls_min.items()},
                  closest=[dict(d=r_["d"], a=r_["a"], pose_a=r_["pose_a"], part_a=r_["part_a"], b=r_["b"], pose_b=r_["pose_b"], part_b=r_["part_b"], mode=r_["mode"]) for r_ in S[:30]],
                  dovetail_min=dmin["d"] if dmin else None, named=named, crossbar_tab_min=min(cb_tab), fixed_fixed=ff, pin_lip_wall=pin_wall, pin_slot=pin_slot,
                  lip_pad=lip_pad, lip_pad_fix1=lip_pad_flat, lever_float={k_: list(v_) for k_, v_ in FLO.items()}, pair_gap={"%s|%s" % k_: v_ for k_, v_ in PGAP.items()}, lip43=lip43, lip44=dict(min=lip44_min["d"], pad=lip44_pad["d"], rail=lip44_rail["d"], pair="%s [%s %s] vs %s" % (
                      lip44_min["a"], lip44_min["part_a"], lip44_min["pose_a"], lip44_min["b"])),
                  rod=rodck, over_ff=dict(d=ff_over_min["d"], a=ff_over_min["a"], part_a=ff_over_min["part_a"], b=ff_over_min["b"], part_b=ff_over_min["part_b"]),
                  over_brief=dict(d=brief_min["d"], a=brief_min["a"], part_a=brief_min["part_a"], b=brief_min["b"], part_b=brief_min["part_b"]),
                  r43_felts=dict(n_bad=len(bad43_), min=S43_[0]["d"], bad=[dict(d=q["d"], a=q["a"], part_a=q["part_a"], b=q["b"], part_b=q["part_b"]) for q in bad43_]),
                  dip=dipck)
# end parts (with the neighbouring module's keys, levers and fixed parts across the seam)
ep = m.end_parts(P, g)
epc = {}
for side in ("left", "right"):
    e = ep[side]
    rr_ = m.summarize_clearances(m.end_part_sweep(P, g, e, pk["D"], pk["C#"], pl["D"], pl["C#"], pk, pl))
    ch = [q for q in rr_ if q["b"].startswith("cheek")]
    nb_ = [q for q in rr_ if "module" in q["b"] or q["a"].startswith(("key C ", "key C# ", "key D ", "lever C ", "lever C# ", "lever D ", "key A ", "key A# ", "key B ", "lever A ", "lever A# ", "lever B "))]
    sf = m.seam_fixed_check(P, g, e)
    epc[side] = dict(min=rr_[0]["d"], min_pair="%s [%s] vs %s [%s]" % (rr_[0]["a"], rr_[0]["part_a"], rr_[0]["b"], rr_[0]["part_b"]),
                     n_bad=sum(1 for q in rr_ if not q["ok"]), cheek=min(q["d"] for q in ch) if ch else None, n=len(rr_),
                     seam_moving=min(q["d"] for q in nb_) if nb_ else None, seam_fixed=sf["min"], seam_face=sf["seam"], seam_dovetail=sf["dovetail"])
    # r4.4 (circuit cross-check 4): the end part's sensor board / support and the rear wall over the lead notch in the sweep
    epc[side]["new_parts"] = {pf_: min(q["d"] for q in rr_ if q["b"].startswith(pf_)) for pf_ in ("sensor board", "rear wall (over the lead notch") if any(q["b"].startswith(pf_) for q in rr_)}
    pr("end part %s: %d pairs, %d below 1.3, min %.2f (%s); key/lever vs cheek min %.2f; across the seam: moving %.2f, fixed-fixed %.2f (%s), seam faces %.2f (%s), dovetail pair %.2f (%s)"
       % (side, len(rr_), epc[side]["n_bad"], rr_[0]["d"], epc[side]["min_pair"], epc[side]["cheek"], epc[side]["seam_moving"] or -1,
          sf["min"][0], sf["min"][1], sf["seam"][0], sf["seam"][1], sf["dovetail"][0], sf["dovetail"][1]))
R["clear"]["end_parts"] = epc
# lever drops (key out, no service block) - needed before the removal paths of black keys (their white neighbours are out)
g["lever_drop"] = {nm: m.lever_drop(P, g, nm, actual=True) for nm in m.ORDER}      # r4.5 fix 3: the real landings (= circuit_r44.drop)
for nm in ("C", "D", "E", "F", "G", "B", "C#", "F#", "A#"):
    d_ = g["lever_drop"][nm]
    pr("lever %-2s with its key out falls %.1f deg onto %s (rests there with %.2f N at its front bottom corner)" % (nm, d_["drop_deg"], d_["onto"], d_["F_rest"]))
swing = {nm: m.service_swing(P, g, lay["levers"][nm], g["collars"][nm]) for nm in ("C", "C#", "D", "F", "F#", "B")}
# r4 (r3 minor 'narrow window'): the hand lifts the lever until it touches the top plate; the removal path is checked 0.5 deg below that stop
BH = round(min(swing.values()) - 0.5, 1)
g["b_hold_removal"] = math.radians(BH)
rem_paths = {}
for nm, tl, rem, dx in (("D", 2.0, (), 0.0), ("E", 2.0, (), 0.0), ("B", 2.0, (), 0.0), ("C", 2.0, (), 0.0), ("F", 2.0, (), 0.0),
                        ("C#", 5.0, ("C", "D"), 0.0), ("F#", 5.0, ("F", "G"), 0.0), ("A#", 5.0, ("A", "B"), 0.0)):
    r_ = m.removal_path(P, g, nm, BH, tl, rem, dx)
    rem_paths[nm] = r_
    pr("removal %-3s (lever held %.1f deg by its tab, key tilt %.0f deg%s): pull up %.2f (%s) | slide 3 mm %.2f | tilt %.2f | draw out %.2f (%s)"
       % (nm, BH, tl, (", neighbours %s out first" % "+".join(rem)) if rem else "", r_["pull_up"][0], r_["pull_up"][1], r_["slide_3mm"][0], r_["tilt"][0],
          r_["draw_out"][0], r_["draw_out"][1]))
pr("lever service swing (curtain and the bay's pad bar out, top plate stays): " + ", ".join("%s %.1f" % kv for kv in swing.items()) +
   " deg; removal needs %.1f (white) / %.1f (black), held at %.1f" % (g["removal_w"]["lever_angle_needed_deg"], g["removal_b"]["lever_angle_needed_deg"], BH))
R["removal_paths"] = {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items()} for k, v in rem_paths.items()}
R["lever_drop"] = g["lever_drop"]
R["service_swing"] = swing
# r4.1 (verifier geometry major 1): assembly order 'levers before keys' - lever insertion under the one-piece top plate
Fx = m.fixed_prisms(P, g)
ins = {}
for nm in ("C", "C#", "D", "E", "F", "F#", "G#", "B"):
    ins[nm] = dict(no_keys=m.lever_insert(P, g, nm, (), fixed=Fx),
                   keys_first=m.lever_insert(P, g, nm, m.ORDER, fixed=Fx) if nm in ("C#", "D", "E", "G#") else None)
for side_, nm in (("left", "A0"), ("left", "A#0"), ("right", "C8")):
    e_ = ep[side_]
    ins[nm] = dict(no_keys=m.lever_insert(P, g, nm, (), fixed=m.end_fixed_prisms(P, g, e_), keys=e_["keys"], lay=e_["lay"], collars=e_["collars"]), keys_first=None)
for nm, q in ins.items():
    pr("lever insertion %-3s: no keys in -> %s (hub on the rod line at pitch %s deg)%s" % (
        nm, "reachable" if q["no_keys"]["ok"] else "BLOCKED", "%.0f..%.0f" % q["no_keys"]["pitches"] if q["no_keys"]["pitches"] else "-",
        "" if q["keys_first"] is None else "; all keys in first (r4.0 order) -> %s" % ("reachable" if q["keys_first"]["ok"] else "blocked")))
# pad-bar slide-out (every single-key removal and shim adjustment)
slide = {}
slide_fit = []
RP_ = P["bar_raise_pull"]
for i_, bay_ in enumerate((("C", "C#", "D"), ("D#", "E", "F"), ("F#", "G", "G#"), ("A", "A#", "B"))):
    slide["bay%d" % (i_ + 1)] = dict(straight=m.pad_bar_slide(P, g, bay_, fixed=Fx, fit_out=slide_fit), straight_3shims=m.pad_bar_slide(P, g, bay_, fixed=Fx, shims=3),
                                     pressed=m.pad_bar_slide(P, g, bay_, fixed=Fx, raise_after=(RP_, P["pad_bar_t"]), fit_out=slide_fit),
                                     pressed_3shims=m.pad_bar_slide(P, g, bay_, fixed=Fx, shims=3, raise_after=(RP_, P["pad_bar_t"])))
e_ = ep["left"]
slide["left end"] = dict(pressed=m.pad_bar_slide(P, g, tuple(e_["order"]), fixed=m.end_fixed_prisms(P, g, e_), keys=e_["keys"], lay=e_["lay"],
                                                 raise_after=(RP_, P["pad_bar_t"]), caps=e_["caps"], collars=e_["collars"], fit_out=slide_fit))
pr("pad bar slide fit against the plate / rails / lips over the whole pull (contact -0.01 = designed sliding fit): min %.3f (%s at %.1f mm)"
   % (min(q[0] for q in slide_fit), min(slide_fit)[2], min(slide_fit)[1]))
for k_, q in slide.items():
    pr("pad bar slide %-8s: " % k_ + " | ".join("%s min %.2f at %.1f mm (%s)" % (kk, v[0], v[1], v[2]) for kk, v in q.items()))
# torsion-spring leg of a keyless lever (it lies past the free angle): where is the unloaded leg tip?
sg_ = P["spring_groove"]
yb_ = sg_[0] + sg_[4]
# r4.2: long leg tangent to the coil (rear side), tip centre on the groove bottom (m.spring_geometry)
sg_rest = m.spring_geometry(P, 0.0)
phi_g = math.degrees(math.atan2(sg_rest["tip_world"][1] - P["L"][1], sg_rest["tip_world"][0] - P["L"][0]))
leg = {}
_lf_ = max(max(v_) for v_ in FLO.values())
KLEG = {}
for nm in ("C", "C#", "E"):
    bd = g["lever_drop"][nm]["angle_deg"]
    kl_ = m.spring_keyless_leg(P, bd, _lf_)
    KLEG[nm] = kl_
    for tol in (0.0, 5.0, -5.0):
        bf = P["spring_free_deg"] + tol
        sgk = m.spring_geometry(P, math.radians(bd), bf=math.radians(bf))
        ytip = sgk["long_leg"][1][0]
        cq_ = kl_["cases"]["%+.0f" % tol]
        leg["%s_%+.0f" % (nm, tol)] = dict(b=bd, free=bf, tip_y=ytip, in_groove=ytip - sg_[0], loaded=bd >= bf, in_groove_float=cq_["in_mouth"])
pr("spring leg of a keyless lever (groove mouth y%.1f on the printed boss, bottom y%.1f, lead-in %.1f): " % (sg_[0], yb_, P["spring_lead_in"]) +
   ", ".join("%s: lever %.1f deg, free %.1f -> %s, tip %.2f inside the mouth (%.2f with the coil float)" % (k, v["b"], v["free"], "loaded" if v["loaded"] else "unloaded", v["in_groove"], v["in_groove_float"]) for k, v in leg.items()))
pr("r4.5 fix 2 keyless leg in x: groove and boss centred on the long leg (lever x %+.1f); coil slides %.3f each way in the %.1f pocket, lever floats up to %.3f -> leg off the groove centre <= %.3f, "
   "the groove catches %.2f (half width %.1f + lead-in %.1f - wire %.2f): margin %.2f (groove on the lever centre as first built: %.2f)"
   % (P["spring_groove_dx"], KLEG["C"]["coil_axial"], P["spring_pocket"][1], _lf_, KLEG["C"]["x_off"], KLEG["C"]["catch"], P["spring_groove"][3] / 2, P["spring_lead_in"], P["spring_d"] / 2,
      KLEG["C"]["x_margin"], KLEG["C"]["x_margin_centred_on_lever"]))
R["assembly"] = dict(insert=ins, slide=slide, spring_leg=leg, slide_fit=min(slide_fit), keyless_x=dict(margin=KLEG["C"]["x_margin"], margin_r45=KLEG["C"]["x_margin_centred_on_lever"],
                                                                                                   x_off=KLEG["C"]["x_off"], catch=KLEG["C"]["catch"], coil_axial=KLEG["C"]["coil_axial"], lever_float=_lf_))
# ------------------------------------------------------------------ r4.2: drafter's geometry findings, re-checked on the model
fit_mod = m.fixed_fit_check(Fx)
gaps_mod = m.pad_bar_fit_gaps(P, g, Fx)
fit_end, gaps_end = {}, {}
for side_ in ("left", "right"):
    Fe_ = m.end_fixed_prisms(P, g, ep[side_])
    fit_end[side_] = m.fixed_fit_check(Fe_)
    gaps_end[side_] = m.pad_bar_fit_gaps(P, g, Fe_)
b_lo = min(min(q["angle_deg"] for q in g["lever_drop"].values()), P["spring_free_deg"])
b_hi = max(swing.values()) + 0.25
slot = m.spring_slot_check(P, (b_lo, b_hi))
tab_core = min(m.poly_dist(m.nail_tab_poly(P), q[3]) for q in m.lever_prisms(P, 0.0) if q[0].startswith(("carrier core", "carrier side wall")))
pr("r4.2 fixed-part fit (raster 0.02, different prints, x overlap > 0.05): module %d overlaps%s; left end %d, right end %d"
   % (len(fit_mod), (" (largest %.2f mm2 %s vs %s)" % (fit_mod[0]["area"], fit_mod[0]["a"], fit_mod[0]["b"])) if fit_mod else "", len(fit_end["left"]), len(fit_end["right"])))
pr("r4.2 pad bar: joggle 1.5 x 1.5 at y%.1f-%.1f, %.1f in front of the plate's channel end y%.1f; rear end on the step y%.1f; wedges / pads to the plate step and rails %.2f / %.2f (end parts %.2f / %.2f)"
   % (g["y_bar_joggle"] - P["pad_bar_t"], g["y_bar_joggle"], gaps_mod["joggle_to_channel_end"], g["y_bar_step"], P["plate_step_y"], gaps_mod["pad wedge"][0], gaps_mod["up-stop pad"][0],
      min(gaps_end[s_]["pad wedge"][0] for s_ in gaps_end), min(gaps_end[s_]["up-stop pad"][0] for s_ in gaps_end)))
pr("r4.2 L-rails: web %.1f down to z%.2f, lip %.1f wide (%.1f under the bar edge) z%.2f-%.2f from y%.1f; leaf tongue %.1f x %.1f x %.0f per bar edge, bump on the lip, preload %.1f: %.3f N/mm, %.2f N per leaf (%.2f N per bar), constant bending stress %.1f MPa (%.1f at +0.3 FDM)"
   % (P["bar_rail"][0], g["z_seat"] - P["bar_rail"][1], P["rail_lip"], gaps_mod["lip_under_bar"], g["z_seat"] - P["bar_rail"][1], g["z_seat"] - P["pad_bar_t"] - P["bar_leaf_gap"], P["rail_lip_y0"],
      P["bar_leaf"][0], P["bar_leaf"][1], P["bar_leaf"][2], P["bar_leaf"][3], gaps_mod["leaf_k"], gaps_mod["leaf_F"], 2 * gaps_mod["leaf_F"], gaps_mod["leaf_sigma"], gaps_mod["leaf_sigma_max_tol"]))
pr("r4.2 torsion spring: hub slot %.0f deg, faces +%.2f / -%.2f; long leg (tangent, rear side) inside the slot over %.1f..%.1f deg with >= %.2f to the faces (worst at %.2f deg, r %.2f); "
   "leg reaches the boss face at z%.2f (boss from z%.1f), groove open from z%.1f -> %s"
   % (P["spring_slot"][0], P["spring_slot"][1], P["spring_slot"][2], b_lo, b_hi, slot["margin"], slot["at"]["b"], slot["at"]["r"],
      slot["leg_z_at_boss_face"], P["spring_boss"][1], P["spring_groove"][1], "in the groove" if slot["leg_in_groove"] else "HITS THE BOSS"))
# r4.5: short leg in its own groove through the hub wall; insertion path along the slot axis
NT_ = slot["notch"]
ins45 = m.spring_insert_check(P)
ins45_lo = {dp_: m.spring_insert_check(P, dp=dp_, dt=0.02)["short_A"][0] for dp_ in (-0.1, -0.15)}
pr("r4.5 fix 2 short leg (captured): tangent point %.2f deg (lever frame) y%.2f z%.2f, straight %.1f along %.2f deg to the tip y%.2f z%.2f (r %.2f); groove %.2f wide (play %.2f) along %.2f deg "
   "(the loaded leg turned %.2f deg CW), faces at %.3f / %.3f from the axis, from ss %.1f in the pocket to the blind end ss %.2f (%.1f past the tip) in the web; contacts: leg tip on the outer face "
   "y%.2f z%.2f, leg on the inner face's pocket edge y%.2f z%.2f, arm %.2f; web underside cut %.2f over x +-%.1f; insertion slot along the leg (%.2f deg, faces +-%.2f), long-leg window face %.1f deg +%.1f"
   % (NT_["alpha_s"], NT_["Q"][0], NT_["Q"][1], P["spring_short_leg"], NT_["leg_dir"], NT_["T"][0], NT_["T"][1], NT_["tip_r"], NT_["width"], NT_["play"], NT_["band_deg"], NT_["theta_c"],
      NT_["nn"][0], NT_["nn"][1], NT_["ss"][0], NT_["ss"][1], P["spring_notch"][2], NT_["O"][0], NT_["O"][1], NT_["E"][0], NT_["E"][1], NT_["arm"],
      NT_["web_cut_depth"], P["spring_pocket"][1] / 2, NT_["slot_deg"], P["spring_slot"][2], P["spring_window"][0], P["spring_window"][1]))
pr("r4.5 fix 2 insertion (free spring slid tip-first along its short leg's groove, no rod): %s; short leg to the groove faces %.3f (groove printed 0.10 / 0.15 narrower: %.3f / %.3f), coil to piece A %.3f / B %.3f, "
   "free long leg (%.1f deg) to A %.2f / B %.2f"
   % ("CLEAR" if ins45["clear"] else "BLOCKED", ins45["short_A"][0], ins45_lo[-0.1], ins45_lo[-0.15], ins45["per"]["coil|A"][0], ins45["per"]["coil|B"][0], ins45["long_free_dir"],
      ins45["per"]["long leg|A"][0], ins45["per"]["long leg|B"][0]))
R["r45"] = dict(notch=NT_, insert=ins45, insert_lo=ins45_lo)
pr("r4.2 fingernail tab: fills the R3 corner above z%.1f, distance to the carrier %.3f (<= 0 = one piece; r4.1 +0.37)" % (P["z_st"] - P["nail_tab_below"] - P["nail_tab"][1], tab_core))
for side_ in ("left", "right"):
    for nm_ in ep[side_]["order"]:
        q_ = ep[side_]["stat"][nm_]
        pr("r4.2 end key %-3s own pad face (tilt %.3f deg, gap %+.2f): wedge %.3f~%.3f (module %.3f~%.3f, delta %+.3f / %+.3f)"
           % (nm_, q_["face_tilt_deg"], q_["gap_design"], q_["wedge"][0], q_["wedge"][1], q_["wedge_module"][0], q_["wedge_module"][1], q_["wedge_delta"][0], q_["wedge_delta"][1]))
R["r42"] = dict(fit_module=fit_mod, fit_end=fit_end, gaps_module=gaps_mod, gaps_end=gaps_end, spring_slot=slot, spring_b_range=(b_lo, b_hi), tab_core=tab_core,
                slide_fit=min(slide_fit), y_bar_joggle=g["y_bar_joggle"],
                spring_rest=dict(long_leg=sg_rest["long_leg"], short_leg=sg_rest["short_leg"], tip=sg_rest["tip_world"], short_bend_deg=sg_rest["short_bend_deg"]))
R["leg_free_dir"] = phi_g + P["spring_free_deg"]
R["leg_in_groove_drop"] = leg["C_+0"]["in_groove"]
# axial play per fin bay (gaps along the rod minus the printed collars and fin bosses)
# r4.4 fix 2: from the float chain (fin bosses + boss_extra, collars >= collar_min)
_flo_, _ = m.lever_float(lay, P, g["collars"])
play_ = []
for f0_, f1_ in zip(lay["fins"][:-1], lay["fins"][1:]):
    q_ = [v_ for k_, v_ in _flo_.items() if f0_[1] < lay["levers"][k_] < f1_[0]]
    if q_:
        play_.append(q_[0][0] + q_[0][1])
R["axial_play"] = play_
R["axial_play_bay"] = min(play_)
pr("axial play per fin bay (collars %.2f short each, never below %.2f; fin bosses +%.2f): " % (P["collar_short"], P["collar_min"], P["boss_extra"]) + ", ".join("%.2f" % q for q in play_))

# ----------------------------------------------------------------------------------------------- H stresses / loads
sec("H. STRESSES AND LOADS (PETG across layers: every note < %.0f MPa, rare (6-key chords, abuse, <= 1e4 events) < %.0f MPa; in the layer plane < %.0f / %.0f MPa; constant < 2 MPa)"
    % (P["s_cyc"], P["s_rare"], P["s_cyc_in"], P["s_rare_in"]))
rs = m.rest_stresses(P, g)
for nm in ("white", "black"):
    q = rs[nm]
    pr("%s at rest: capstan %.3f N, shelf %.3f N, key rod %.3f N, lever rod %.3f N | thin tail %.2f MPa, beam %.2f, beam at capstan %.2f, notch section %.2f | cloth %.3f, hub %.3f MPa"
       % (nm, q["capstan_N"], q["shelf_R"], q["rod_R"], q["lever_rod_R"], q["tail"], q["beam"], q["beam_at_capstan"], q["notch_section"], q["cloth_p"], q["hub_p"]))
pr("torsion-spring long leg on the rear-wall groove: %.2f N mm -> %.3f N on the groove flank (%.2f MPa)" % (rs["spring_leg"]["T_rest"], rs["spring_leg"]["F_leg"], rs["spring_leg"]["groove_p"]))
pr("-> max constant stress in any plastic part %.2f MPa (target < 2); no preloaded joint left" % rs["max"])
pr("up-stop peaks (white / black, real pad normal force): PLAY %.0f / %.0f N, 2.0 m/s (chord) %.0f / %.0f N, ABUSE 2.5 m/s %.0f / %.0f N (r3: 138 / 159 N at 1.5 m/s finger start)"
   % (up_play + up_ch + up_abuse))
pr("pad: bearing on the wedge / pad bar %.2f MPa at the ABUSE peak (%.0f x %.0f footprint); foam compression max %.0f %% / %.0f %% of %.0f (densification at %.0f %%)"
   % (max(up_abuse) / (P["pad_w"] * (P["pad_y"][1] - P["pad_y"][0])), P["pad_w"], P["pad_y"][1] - P["pad_y"][0], 100 * g["pad_comp_ratio_w"], 100 * g["pad_comp_ratio_b"], P["pad_h"], 100 * P["pad_epsD"]))
for lab in ("play", "abuse_chord20", "abuse"):
    for kind, q in PL[lab].items():
        pr("   plate %-14s %-6s %.0f N: plate %.1f MPa (in layer), fin top junction %.1f MPa (across layers), rear wall %.2f MPa, seat deflection max %.2f mm"
           % (lab, kind, q["total"], q["sigma"], q["fin_top"], q["wall_q"] / 3.0, q["seat_max"]))
RLp = (max(dyn["white"][k]["RL_peak"] for k in dyn["white"] if k.startswith("play_")), max(dyn["black"][k]["RL_peak"] for k in dyn["black"] if k.startswith("play_")))
RLc = (max(dyn["white"][k]["RL_peak"] for k in ("chord20_rel", "chord20_h1.00")), max(dyn["black"][k]["RL_peak"] for k in ("chord20_rel", "chord20_h1.00")))
RLa = (max(dyn["white"][k]["RL_peak"] for k in dyn["white"] if k.startswith("abuse_")), max(dyn["black"][k]["RL_peak"] for k in dyn["black"] if k.startswith("abuse_")))
LR = dict(play=m.lever_rod_loads(P, g, RLp[0], RLp[1], lay["fins"], lay["levers"], keys),
          chord20=m.lever_rod_loads(P, g, RLc[0], RLc[1], lay["fins"], lay["levers"], keys),
          abuse=m.lever_rod_loads(P, g, RLa[0], RLa[1], lay["fins"], lay["levers"], keys))
for lab, q in LR.items():
    pr("   lever rod SUS304 D%.0f (%s, rod peaks %.0f / %.0f N): 6-key chord %.0f MPa (defl %.3f, fin %.0f N -> printed boss %.1f MPa); single worst %.0f MPa; hub %.1f MPa  [yield cold-drawn %.0f, annealed %.0f]"
       % (P["rod_L"], lab, q["RL"][0], q["RL"][1], q["chord"]["sigma"], q["chord"]["defl"], q["chord"]["fin_R"], q["chord"]["boss_bearing"], q["single"]["sigma"],
          q["single"]["hub_bearing"], P["rod_L_yield"], P["rod_L_yield_annealed"]))
# r4.5: hub / web strength where the short-leg groove cuts the pocket section (ABUSE rod reaction + the hand-lift spring torque; PLAY + bottom torque)
HN = dict(abuse=m.hub_notch_stress(P, max(RLa), R["spring"]["states"]["hand 25 deg"]["T"]), play=m.hub_notch_stress(P, max(RLp), R["spring"]["states"]["bottom"]["T"]),
          chord20=m.hub_notch_stress(P, max(RLc), R["spring"]["states"]["bottom"]["T"]))
for lab_, q_ in HN.items():
    pr("   r4.5 fix 2 hub/web at the captured short-leg groove (%s, rod %.1f N): section y%.2f M %.0f N mm -> %.2f MPa in layer (x Kt %.1f = %.2f; without the groove %.2f), shear %.2f; "
       "the two leg contacts %.2f N each (couple, both on piece A, %.1f MPa on d x d); piece B carries no leg force; rod on the two full hub segments %.2f MPa (full width %.2f)"
       % (lab_, max(RLa) if lab_ == "abuse" else (max(RLp) if lab_ == "play" else max(RLc)), q_["section"]["y"], q_["section"]["M"], q_["section"]["sigma"], q_["Kt"], q_["section"]["sigma_kt"], q_["section"]["sigma_full"],
          q_["section"]["tau"], q_["F_couple"], q_["contact_p"], q_["hub_bearing"], q_["hub_bearing_fullwidth"]))
R["r45"]["hub"] = HN
cap_pk = max(dyn[c][k]["cap_peak"] for c in ("white", "black") for k in dyn[c] if isinstance(dyn[c][k], dict) and "cap_peak" in dyn[c][k] and k.startswith(("play_", "push6", "ff_", "release")))
cap_pk_ab = max(dyn[c][k]["cap_peak"] for c in ("white", "black") for k in dyn[c] if isinstance(dyn[c][k], dict) and k.startswith("abuse_"))
hb = P["beam_z"][1] - P["beam_z"][0]
s_beam_pk = cap_pk * (caps["white"] - P["y_body_end"]) / (P["beam_w"] * hb ** 2 / 6)
s_beam_ab = cap_pk_ab * (caps["white"] - P["y_body_end"]) / (P["beam_w"] * hb ** 2 / 6)
t_tail = P["tail_top"] - P["beam_z"][0]
tail_c = {}
for c in ("white", "black"):
    arm_c = sum(P["rest_pad_y"]) / 2 - (caps[c] + 4.0)
    Z_c = m.tail_w(P, c == "black") * t_tail ** 2 / 6
    pk_c = max(dyn[c][k]["rest_peak"] for k in ("release", "play_rel", "ff_rel", "abuse_rel"))
    pk_play = max(dyn[c][k]["rest_peak"] for k in ("release", "play_rel", "ff_rel"))
    tail_c[c] = dict(arm=arm_c, w=m.tail_w(P, c == "black"), peak_N=pk_c, play_N=pk_play, s_peak=pk_c * arm_c / Z_c, s_play=pk_play * arm_c / Z_c)
# r4.3: no thin shelf over the plug any more (slot); the 2.0 shelf beside the slot carries the F / F# rest-felt peak on
# its landing strip: worst of (a) the whole peak at the strip's inner edge in the span between the neighbouring rib
# faces, (b) the whole peak at the slot edge on the cantilever past the last rib face
rest_pk = max(tail_c["white"]["peak_N"], tail_c["black"]["peak_N"])
sup_ = sorted([(x_ - P["rib_t"] / 2, x_ + P["rib_t"] / 2) for x_ in g["ribs"]] + [tuple(f_) for f_ in lay["fins"]])
Zsh = (P["shelf_y"][1] - P["shelf_y"][0]) * 2.0 ** 2 / 6
shelf_slot = {}
for nm_, q_ in RLAND.items():
    if q_["frac"] > 1 - 1e-9:
        continue
    u_, v_ = q_["segs"][0]
    s0_, s1_ = m.usb_slot(P)
    Pk_ = tail_c["black" if keys[nm_]["black"] else "white"]["peak_N"]
    if abs(v_ - s0_) < 1e-6:          # landing left of the slot: cantilever from the last rib face left of the slot edge
        rf_ = max(b_ for a_, b_ in sup_ if b_ <= s0_ + 1e-9)
        lf_ = max(b_ for a_, b_ in sup_ if b_ <= rf_ - P["rib_t"] - 1e-9)
        ra_ = max(a_ for a_, b_ in sup_ if b_ <= s0_ + 1e-9)
        x_in = u_
        Lsp_ = ra_ - lf_
        M_span = Pk_ * (x_in - lf_) * (ra_ - x_in) / Lsp_ if lf_ < x_in < ra_ else 0.0
        M_cant = Pk_ * (s0_ - rf_)
    else:                               # landing right of the slot
        lf_ = min(a_ for a_, b_ in sup_ if a_ >= s1_ - 1e-9)
        rb2_ = min(a_ for a_, b_ in sup_ if a_ >= lf_ + P["rib_t"] + 1e-9)
        la_ = min(b_ for a_, b_ in sup_ if a_ >= s1_ - 1e-9)
        x_in = v_
        Lsp_ = rb2_ - la_
        M_span = Pk_ * (x_in - la_) * (rb2_ - x_in) / Lsp_ if la_ < x_in < rb2_ else 0.0
        M_cant = Pk_ * (lf_ - s1_)
    shelf_slot[nm_] = dict(peak_N=Pk_, landing=(u_, v_), frac=q_["frac"], M_span=M_span, M_cant=M_cant, sigma=max(M_span, M_cant) / Zsh)
s_shelf = max([q_["sigma"] for q_ in shelf_slot.values()] + [0.0])
pr("peak stresses: hidden beam at the block %.1f MPa (capstan %.1f N, PLAY) / %.1f MPa (ABUSE %.1f N); thin tail white %.1f / black %.1f MPa at PLAY (rest-felt %.1f / %.1f N), "
   "%.1f / %.1f MPa ABUSE; shelf beside the USB slot (F / F# landing) %.1f MPa"
   % (s_beam_pk, cap_pk, s_beam_ab, cap_pk_ab, tail_c["white"]["s_play"], tail_c["black"]["s_play"], tail_c["white"]["play_N"], tail_c["black"]["play_N"],
      tail_c["white"]["s_peak"], tail_c["black"]["s_peak"], s_shelf))
roll = m.roll_check(P, g, hist_rec.get("white"), hist_rec.get("black"))
pr("key roll (restoring / overturning): " + ", ".join("%s %.1f/%.1f" % (k, v["ratio_rest"], v["ratio_stroke"]) for k, v in roll.items())
   + " (rest / held PLAY stroke); guide tab takes at most %.2f N (white tab %.1f in %.1f ribs, black tab %.1f in %.1f walls, 0.5T cloth each side: +-%.2f)"
   % (max(v["tab_N"] for v in roll.values()), P["tab_w"], P["rib_in"], P["tab_w_b"], P["b_wall_in"], P["tab_play"]))
# r4.4 (R44 issue 1): steel block retention in the carrier.  Zone forces from the 4-DOF runs (m.steel_zones / steel_zone_split):
# top-front = solid cap y150-153 + front top lips, top-rear = rear top lips, bottom = bottom snap lips.  Lip root bending across the
# layers (carrier printed on its side): sigma = 3 F a / (L t^2), a = half the overhang (uniform contact; upper bound)
ZS = m.steel_zones(P)
ZS43 = m.steel_zones(P, segs=((150.0, P["lip_gap_y"][0]), (P["lip_gap_y"][1], P["lip_end_y"])))
def _sig(F_, L_, over_, t_=1.0):
    return 3.0 * F_ * (over_ / 2) / (L_ * t_ ** 2) if L_ > 0 else float("inf")
ret = {}
for (col_, sub_, mat_), rows_ in STEEL.items():
    for c_, r_ in rows_:
        s_ = r_["steel"]
        lab_ = "play" if (sub_ in ("single", "release", "press") and (c_.get("v") is None or c_["v"] <= P["v_play"] + 1e-9)) else ("chord" if sub_ == "chord" else "abuse")
        q_ = ret.setdefault(lab_, dict(T_front=0.0, T_rear=0.0, B=0.0, T_front_r43=0.0, T_rear_r43=0.0, B_r43=0.0, case={}))
        for k_ in ("T_front", "T_rear", "B", "T_front_r43", "T_rear_r43", "B_r43"):
            if s_[k_] > q_[k_]:
                q_[k_] = s_[k_]
                q_["case"][k_] = "%s %s %s %s" % (col_, sub_, mat_, "v%.1f %s" % (c_["v"], m.hl(c_.get("hold"))) if c_.get("v") else c_.get("F", ""))
lim_ = dict(play=P["s_cyc"], chord=P["s_rare"], abuse=P["s_rare"])
lo_, lb_ = P["lip_over"] - P.get("bond_t", 0.0), 1.0          # r4.4 fix 2b: the lip's overlap over the steel (lip 0.9 - bond line 0.1 = 0.8)
for lab_, q_ in ret.items():
    q_["sig_front"] = _sig(q_["T_front"], ZS["L_front"], lo_)
    q_["sig_rear"] = _sig(q_["T_rear"], ZS["L_rear"], lo_)
    q_["sig_bottom"] = _sig(q_["B"], ZS["L_bottom"], lb_)
    q_["sig_bottom_root"] = _sig(q_["B"], ZS["L_bottom"], 0.7 * lb_)      # contact biased to the root (a = 0.35)
    q_["sig_front_r43"] = _sig(q_["T_front_r43"], ZS43["L_front"], lo_)
    q_["sig_rear_r43"] = _sig(q_["T_rear_r43"], ZS43["L_rear"], lo_)
    q_["limit"] = lim_[lab_]
    pr("steel retention %-5s (limit %.0f MPa across layers): top-front (cap + lips %.0f) %.1f N -> lips alone %.1f MPa | top-rear lips (%.0f long) %.1f N -> %.1f MPa | "
       "bottom lips (%.1f long) %.1f N -> %.1f MPa (root-biased %.1f) || r4.3 lips: front %.1f N %.1f MPa, rear (%.0f long) %.1f N %.1f MPa"
       % (lab_, q_["limit"], ZS["L_front"], q_["T_front"], q_["sig_front"], ZS["L_rear"], q_["T_rear"], q_["sig_rear"], ZS["L_bottom"], q_["B"], q_["sig_bottom"],
          q_["sig_bottom_root"], q_["T_front_r43"], q_["sig_front_r43"], ZS43["L_rear"], q_["T_rear_r43"], q_["sig_rear_r43"]))
# handling / transport: a uniform shock n x g on the steel alone (module upside down or dropped), zones share by lever arm
ms_ = ZS["m"] * m.G
share_f = (ZS["yr"] - ZS["com"][0]) / (ZS["yr"] - ZS["yf"])
n_rear = P["s_rare"] * ZS["L_rear"] / (3 * lo_ / 2) / (ms_ * (1 - share_f))
n_front = P["s_rare"] * ZS["L_front"] / (3 * lo_ / 2) / (ms_ * share_f)
n_bot = P["s_rare"] * ZS["L_bottom"] / (3 * lb_ / 2) / ms_
ret["transport"] = dict(weight_N=ms_, n_up_rear=n_rear, n_up_front=n_front, n_down=n_bot, n_min=min(n_rear, n_front, n_bot))
pr("steel retention, handling: the steel weighs %.2f N; the %.0f MPa rare limit is reached at a shock of %.0f g upward on the rear lips, %.0f g on the front lips (cap not counted), "
   "%.0f g downward on the bottom lips; upside down (1 g) %.3f N on the rear lips.  Geometric capture: the steel can leave only downward past the bottom snap lips "
   "(front / rear walls, side walls, the solid front cap and the rear lips close the other five sides)"
   % (ms_, P["s_rare"], n_rear, n_front, n_bot, ms_ * (1 - share_f)))
# r4.4 fix 2 (verifier physics majors 1-2): the snap alone, measured on a plate model of the side wall (m.carrier_wall_plate):
# the bottom-lip load is eccentric to the 0.8 wall, so the wall itself bends at the lip root and the lip line opens
WP = {}
for lab_, F_ in (("play", ret["play"]["B"]), ("abuse", ret["abuse"]["B"]), ("abuse_x1.5", 1.5 * ret["abuse"]["B"])):
    for a_c in (0.5, 0.75):
        for cl_ in (False, True):
            q_ = m.carrier_wall_plate(P, F_ / 2, a_c, clamp_ends=cl_)
            WP["%s_a%.2f_%s" % (lab_, a_c, "clamped" if cl_ else "pinned")] = dict((k_, v_) for k_, v_ in q_.items())
for k_, q_ in WP.items():
    pr("snap alone (no bond), side-wall plate %-26s: lip line opens %.2f (mean %.2f) of the %.1f overhang, flank %.1f deg, wall at the lip root %.1f MPa (plate max %.1f; in the layer plane, limit %.0f / %.0f)"
       % (k_, q_["spread_max"], q_["spread_mean"], 1.0, q_["flank_deg"], q_["s_root"], q_["s_plate"], P["s_cyc_in"], P["s_rare_in"]))
# the bond: every carrier -> steel resultant (V, M about the steel COM) through the two bonded side faces (shear)
SB = m.steel_bond(P)
bond = {}
for (col_, sub_, mat_), rows_ in STEEL.items():
    for c_, r_ in rows_:
        s_ = r_["steel"]
        lab_ = "play" if (sub_ in ("single", "release", "press") and (c_.get("v") is None or c_["v"] <= P["v_play"] + 1e-9)) else ("chord" if sub_ == "chord" else "abuse")
        dM_ = abs(ZS["com"][0] - SB["c"][0]) + abs(ZS["com"][1] - SB["c"][1])     # moment arm COM -> bond centroid (bound)
        V_ = max(abs(s_["V_min"]), abs(s_["V_max"]))
        M_ = max(abs(s_["M_min"]), abs(s_["M_max"])) + V_ * dM_
        tau_ = V_ / SB["area"] + M_ * SB["rmax"] / SB["J"]
        q_ = bond.setdefault(lab_, dict(tau=0.0, V=0.0, M=0.0))
        q_["tau"] = max(q_["tau"], tau_); q_["V"] = max(q_["V"], V_); q_["M"] = max(q_["M"], M_)
# r4.4 fix 2b (verifier physics major 1): + the edge shear from the PETG / steel thermal mismatch (every day dT, rare = transport),
# at the thinnest bond line (steel pushed to one wall); flexible MS polymer (G bond_G) - the rigid 5-min epoxy for the record
TH = {}
for k_, dT_ in (("day", P["bond_dT"][0]), ("rare", P["bond_dT"][1])):
    for ta_ in (P["bond_t"], 0.05, P["bond_t_min"]):
        TH["%s_%.2f" % (k_, ta_)] = dict(dT=dT_, t_a=ta_, ms=m.bond_thermal(P, dT_, t_a=ta_)["tau"], epoxy=m.bond_thermal(P, dT_, G=P["bond_G_epoxy"], t_a=ta_)["tau"])
thq_ = m.bond_thermal(P, P["bond_dT"][0])
for lab_, q_ in bond.items():
    q_["limit"] = P["bond_tau"] / (P["bond_sf_play"] if lab_ == "play" else P["bond_sf_rare"])
    q_["tau_mech"] = q_["tau"]
    q_["tau_th"] = m.bond_thermal(P, P["bond_dT"][0] if lab_ == "play" else P["bond_dT"][1], t_a=P["bond_t_min"])["tau"]
    q_["tau"] = q_["tau_mech"] + q_["tau_th"]
    q_["slip"] = q_["V"] / thq_["slip_k"]
    q_["epoxy_th"] = m.bond_thermal(P, P["bond_dT"][0] if lab_ == "play" else P["bond_dT"][1], G=P["bond_G_epoxy"], t_a=P["bond_t"])["tau"]
    pr("steel bond %-5s: |V| %.1f N, |M| %.0f N mm -> shear %.3f MPa over %.0f mm2 (2 faces, J %.0f mm4, r %.1f) + thermal (dT %.0f K, bond line %.2f) %.3f = %.3f | allowed %.2f (%s %.1f MPa / %.0f); "
       "slip under the peak %.4f mm; rigid 5-min epoxy (G %.0f, line %.2f) thermal alone %.2f MPa"
       % (lab_, q_["V"], q_["M"], q_["tau_mech"], SB["area"], SB["J"], SB["rmax"], P["bond_dT"][0] if lab_ == "play" else P["bond_dT"][1], P["bond_t_min"], q_["tau_th"], q_["tau"],
          q_["limit"], P["bond_adhesive"], P["bond_tau"], P["bond_sf_play"] if lab_ == "play" else P["bond_sf_rare"], q_["slip"], P["bond_G_epoxy"], P["bond_t"], q_["epoxy_th"]))
pr("steel bond thermal edge shear (MS polymer G %.1f / rigid epoxy G %.0f MPa; wall %.1f, E %.0f, dalpha %.1f e-6/K, shear-lag length %.1f mm << 40): " % (
    P["bond_G"], P["bond_G_epoxy"], P.get("carrier_side_wall", P["carrier_wall"]), m.E_PETG, 1e6 * (P["cte_petg"] - P["cte_steel"]), thq_["lag"])
   + ", ".join("%s line %.2f: %.3f / %.2f" % (k_.split("_")[0], v_["t_a"], v_["ms"], v_["epoxy"]) for k_, v_ in TH.items()))
n_bond = P["bond_tau"] / P["bond_sf_rare"] * SB["area"] / ms_
pr("steel bond, handling: a shock of %.0f g (any direction) reaches the rare-load bond stress; the snap lips alone (glue not yet cured) hold the steel's own weight "
   "(upside down 0.53 N: lip root %.2f MPa)" % (n_bond, 3.0 * ms_ * (1 - share_f) * (lo_ / 2) / (ZS["L_rear"] * 1.0)))
R["steel_retention"] = dict(zones=ZS, zones_r43=ZS43, peaks=ret, wall_plate=WP, bond=bond, bond_geo=dict(area=SB["area"], J=SB["J"], rmax=SB["rmax"], c=SB["c"]),
                            bond_shock_g=n_bond, thermal=TH, lag=thq_["lag"], slip_k=thq_["slip_k"],
                            pocket=P["lever_w"] - 2 * P["carrier_side_wall"], bond_line=(P["lever_w"] - 2 * P["carrier_side_wall"] - P["steel_w"]) / 2)
R["stress"] = dict(rest=rs, rest_max=rs["max"], plate=PL, lever_rod=LR, beam_peak=s_beam_pk, beam_abuse=s_beam_ab, cap_peak=cap_pk, cap_peak_abuse=cap_pk_ab,
                   tail=tail_c, shelf_usb=s_shelf, shelf_slot=shelf_slot, roll=roll, pad_bearing=max(up_abuse) / (P["pad_w"] * (P["pad_y"][1] - P["pad_y"][0])))

# ------------------------------------------------------------------ r4.3: control-board interface (circuit session BRD-01)
sec("Q. r4.3 CONTROL-BOARD INTERFACE (circuit BRD-01 against r4.1): RP2040-Zero on pin headers (+1.3), USB-C plug z%.1f-%.1f, 4067 on headers, 16-core ribbon, EXT pads"
    % tuple(P["usb_z"]))
R2_ = json.load(open(os.path.join(OUT, "work_r4r3", "metrics.r4_2.json")))
s0_, s1_ = m.usb_slot(P)
ffe = ff["usb_plug_each"]
pr("USB-C plug envelope x%.2f-%.2f y%.1f-%.1f z%.2f-%.2f (r4.2 z9.45-16.95): to the rear shelf %.2f (slot x%.2f-%.2f, r4.2 thin shelf underside z18.55 would leave %.2f), "
   "shelf ribs %.2f, F|F# fin %.2f (hung from z%.1f), rear wall opening %.2f (x%.0f-%.0f z%.0f-%.0f unchanged), cable passage behind the modules z0-22 (v3): %.1f above the plug"
   % (P["usb_x"] + P["usb_y"] + tuple(P["usb_z"]) + (ffe["rear shelf"], s0_, s1_, g["z_shelf"] - 1.5 - P["usb_z"][1], ffe["shelf rib"], ffe["fin"],
      max(P["comp_zmax"] + 1.5, P["usb_z"][1] + P["usb_clear"]), ffe["rear wall"]) + tuple(P["usb_wall_open"]) + (22.0 - P["usb_z"][1],)))
roll43 = {nm_: roll[nm_] for nm_ in RLAND if RLAND[nm_]["frac"] < 1 - 1e-9}
land_tab = {}
rib_h_ = P["key_top"] - P["skin_w"] - P["key_bot"]
for nm_, q_ in roll43.items():
    col_ = "black" if keys[nm_]["black"] else "white"
    dR_ = abs(lay["levers"][nm_] - sum(m.block_x(P, keys[nm_])) / 2 + RLAND[nm_]["dx"])
    # landing couple with no restoring rod moment at all (upper bound): rest-felt peak x its offset from the block centre, over the rib height
    land_tab[nm_] = dict(dR=dR_, peak_N=tail_c[col_]["peak_N"], tab_N=tail_c[col_]["peak_N"] * dR_ / rib_h_)
pr("rest felts beside the slot: " + "; ".join("%s lands on x%.2f-%.2f (%.0f %% of 8.0), reaction %.2f off the lever line -> roll restoring / overturning at rest %.2f (r4.2 %.1f), "
                                            "landing couple bound %.2f N on the guide tab (rest-felt peak %.1f N x %.2f / rib %.0f)"
                                            % (nm_, RLAND[nm_]["segs"][0][0], RLAND[nm_]["segs"][0][1], 100 * RLAND[nm_]["frac"], RLAND[nm_]["dx"], roll43[nm_]["ratio_rest"],
                                               R2_["stress"]["roll"][nm_]["ratio_rest"], land_tab[nm_]["tab_N"], land_tab[nm_]["peak_N"], land_tab[nm_]["dR"], rib_h_)
                                            for nm_ in roll43))
SL_ = R["sens"][LAND_LAB]
pr("rest-felt contact K x %.2f (F# landing, applied to both colours): " % LAND_MIN + " || ".join(
    "%s rep %.1f Hz (main %.1f), full return %.1f ms (main %.1f), friction x2 %.1f Hz / %.1f ms, PLAY lift %.3f keep %.2f, ABUSE lift %.3f"
    % (c_[0].upper(), SL_[c_]["rep"], dd[c_]["rep"], SL_[c_]["t100"], dd[c_]["t100"], 500.0 / DYN[LAND_LAB][c_]["release_f2"]["t50"], DYN[LAND_LAB][c_]["release_f2"]["t100"],
       SL_[c_]["lift_play"], SL_[c_]["keep_play"], SL_[c_]["lift_abuse"]) for c_ in ("white", "black")))
pr("shelf beside the slot (2.0 thick, 13.2 deep): " + "; ".join("%s rest-felt peak %.1f N: span %.1f / cantilever %.1f N mm -> %.2f MPa" % (k_, q_["peak_N"], q_["M_span"], q_["M_cant"], q_["sigma"]) for k_, q_ in shelf_slot.items()))
kk2 = R2_["seat"]["k_keys"]
pr("plate FE with the F|F# fin hung over the USB tunnel behind y%.1f (r4.2 grounded it there through the thin shelf): pad seat " % P["rib_y0"] +
   ", ".join("%s %.0f (%.0f)" % (k_, g["seat_k_keys"][k_], kk2[k_]) for k_ in ("E", "F", "F#", "G")) + " N/mm (r4.2 in brackets); weakest %s %.0f -> dynamics seat %.0f (r4.2 %.0f); 6-key PLAY chord seat %.0f (r4.2 %.0f)"
   % (min(g["seat_k_keys"], key=g["seat_k_keys"].get), min(g["seat_k_keys"].values()), g["seat_k"], R2_["seat"]["k_min"], k_ch, R2_["seat"]["k_chord"]))
fin_R_ = max(LR[k_]["chord"]["fin_R"] for k_ in LR)
h_fw = min(z for y, z in g["plate_under"] if y >= P["rear_wall"][0] - 1.0) - max(P["comp_zmax"] + 1.5, P["usb_z"][1] + P["usb_clear"])
t_fw = lay["fins"][2][1] - lay["fins"][2][0]
arm_fw = P["rear_wall"][0] - P["L"][0]
tau_fw = fin_R_ / (t_fw * h_fw)
sig_fw = fin_R_ * arm_fw / (t_fw * h_fw ** 2 / 6)
pr("F|F# fin behind the board: grounded foot y%.1f-%.1f (stripboard slot to y%.1f), hung from z%.1f behind it up to the rear wall; rear face of the foot -> RP2040-Zero front edge y%.1f: %.2f; "
   "largest lever-rod reaction on a fin boss %.0f N (ABUSE chord) into the fin-rear wall junction (%.1f x %.1f): shear %.2f MPa, bending %.2f MPa (in the layer plane)"
   % (m.keel_front(P), P["fin_slot_y"][1], P["board_slot_y1"], P["comp_zmax"] + 1.5, P["zero_xy"][2], P["zero_xy"][2] - P["fin_slot_y"][1], fin_R_, t_fw, h_fw, tau_fw, sig_fw))   # r4.5 fix 3: fin front = keel_front (y148.6), not fin_slot_y[0]
bvf = ff["board_vs_frame"]
pr("BRD-01 parts / component envelope vs the printed frame (fins, shelf, ribs, rail, rear wall): " + "; ".join("%s %.2f (%s)" % (k_.replace("board part: ", ""), v_[0], v_[1]) for k_, v_ in bvf.items()))
rl_ = ff["ribbon_lane"]
pr("ribbon: %d cores x %.2f = %.2f wide centred on J301 (x%.2f) in the lane x%.1f-%.1f under the balance rail (r4.2 x60-82): margins %.2f / %.2f, height %.1f (z5-10)"
   % (P["ribbon_cores"], P["ribbon_pitch"], rl_["width"], 0.5 * (P["ribbon_pads"][0] + P["ribbon_pads"][1]), rl_["lane"][0], rl_["lane"][1], rl_["left"], rl_["right"], rl_["height"]))
ribs_ = sorted(g["ribs"])
tun_ = (max(r_ for r_ in ribs_ if r_ < P["usb_x"][0]) + P["rib_t"] / 2, min(r_ for r_ in ribs_ if r_ > P["usb_x"][1]) - P["rib_t"] / 2)
pr("J302 EXT lead (O1 / O7 only): pads x%.2f-%.2f y%.2f are behind a closed pocket under the shelf (x%.1f-%.1f, rear wall without opening) -> solder from the underside, "
   "route under the stripboard (z%.1f-%.1f, %.1f high) into the USB tunnel x%.1f-%.1f and under the plug (z%.1f-%.1f, %.1f high) out through the rear-wall opening"
   % (P["ext_pads"][0], P["ext_pads"][1], P["ext_pads"][2], tun_[1] + P["rib_t"], min(r_ for r_ in ribs_ if r_ > tun_[1] + P["rib_t"]) - P["rib_t"] / 2,
      P["z_floor"][1], P["board_z"][0], P["board_z"][0] - P["z_floor"][1], tun_[0], tun_[1], P["z_floor"][1], P["usb_z"][0], P["usb_z"][0] - P["z_floor"][1]))
nk_ = named
pr("key beams / tails over the board parts (sweep, all poses): %.2f (after tol %.2f) %s [%s %s]; key tail / rest felt over the plug %.2f (after tol %.2f) %s [%s %s]"
   % (nk_["건반 빔·꼬리 ↔ 제어 기판 부품"]["d"], nk_["건반 빔·꼬리 ↔ 제어 기판 부품"]["after_tol"], nk_["건반 빔·꼬리 ↔ 제어 기판 부품"]["a"], nk_["건반 빔·꼬리 ↔ 제어 기판 부품"]["part_a"],
      nk_["건반 빔·꼬리 ↔ 제어 기판 부품"]["pose_a"], nk_["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["d"], nk_["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["after_tol"],
      nk_["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["a"], nk_["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["part_a"], nk_["건반 꼬리·쉼 펠트 ↔ USB-C 플러그"]["pose_a"]))
pr("end parts: no control board, no USB (read by O1 / O7 through EXT): their rear shelf and rear wall are the module's clipped outside x74-94; r4.4: sensor-board support, lead lane and rear-wall notch (Q2)")
pr("EXT / JST-XH order (circuit): 1 GND, 2-5 EXT1-4, 6 3V3 (red edge wire); ribbon uses all 16 cores - the model and DESIGN.md state no pin order (nothing to update)")
R["r43"] = dict(usb=dict(z=tuple(P["usb_z"]), each=ffe, min=ff["usb_plug_min"], slot=(s0_, s1_), thin_shelf_gap_r42=g["z_shelf"] - 1.5 - P["usb_z"][1],
                         wall_open_gap=P["usb_wall_open"][3] - P["usb_z"][1], passage_gap=22.0 - P["usb_z"][1]),
                land=RLAND, land_min=LAND_MIN, land_lab=LAND_LAB, roll=roll43, roll_r42={k_: R2_["stress"]["roll"][k_] for k_ in roll43}, land_tab=land_tab,
                shelf_slot=shelf_slot, seat_r42=R2_["seat"], fin=dict(foot=tuple(P["fin_slot_y"]), slot_end=P["board_slot_y1"], zero_gap=P["zero_xy"][2] - P["fin_slot_y"][1],
                                                                       fin_R=fin_R_, tau=tau_fw, sigma=sig_fw, h=h_fw, t=t_fw),
                board_vs_frame=bvf, board_parts_min=ff["board_parts_min"], ribbon=rl_, tunnel=tun_,
                ext_path=dict(under_board=P["board_z"][0] - P["z_floor"][1], under_plug=P["usb_z"][0] - P["z_floor"][1]),
                named={k_: nk_[k_] for k_ in ("건반 빔·꼬리 ↔ 제어 기판 부품", "건반 꼬리·쉼 펠트 ↔ USB-C 플러그")})

# ------------------------------------------------------------------ r4.4: circuit session cross-check requests (hardware/pcb README)
sec("Q2. r4.4 CIRCUIT CROSS-CHECK REQUESTS (hardware/pcb README 'W1 기구 쪽에 요청한 것', 7 items) - measured on this model")
C44 = m.circuit_c44_checks(P, g, ep)
zq_, uq_, rq_, sq_ = C44["zero"], C44["usb"], C44["ribbon"], C44["screw"]
pr("1. BRD-01 on the Zero lattice (x = %.2f + 2.54 i): Zero x%.2f-%.2f y%.1f-%.1f (receptacle centre x%.2f = shelf-slot centre x%.2f), 4067 x%.2f-%.2f y%.1f-%.2f (to the keep-out %.2f), "
   "J301 x%.2f-%.2f y%.2f / %.2f soldered from the underside (top joints <= z%.1f), J302 x%.2f-%.2f y%.2f (to the rib face %.2f); named parts vs the printed frame min %.2f (%s)"
   % ((zq_["lattice_x"][0],) + zq_["x"] + zq_["y"] + (zq_["rcpt_centre"], zq_["slot_centre"]) + tuple(P["mux_xy"]) + (zq_["mux_to_keepout"],) + tuple(P["ribbon_pads"]) + (P["ribbon_z"],)
      + tuple(P["ext_pads"]) + (zq_["j302_to_rib"], ff["board_parts_min"][0], ff["board_parts_min_name"].replace("board part: ", "") + " vs " + ff["board_parts_min"][1])))
pr("   ribbon (16 x 1.27 = %.2f) centred on SB J201 x%.2f in the lane x%.1f-%.1f: margins %.2f / %.2f; J301 centre x%.2f -> last %.0f mm shifted %+.2f, under the board z%.0f-%.0f (%.1f high) x%.2f-%.2f y%.1f-%.2f: "
   "to the F|F# fin foot %.2f, to the stand-off (50,149) %.2f, %.2f outside the keep-out x%.2f"
   % (rq_["width"], rq_["xc"], rq_["lane"][0], rq_["lane"][1], rq_["lane_margins"][0], rq_["lane_margins"][1], rq_["j301_c"], P["ribbon_j301"][1], rq_["shift"], rq_["under_z"][0], rq_["under_z"][1],
      rq_["height_under"], rq_["under"][0], rq_["under"][1], rq_["under_y"][0], rq_["under_y"][1], rq_["to_fin"], rq_["to_standoff"], rq_["to_keepout"], zq_["keepout"][0]))
pr("2. USB-C plug face y%.1f (r4.3 y%.1f), overmould y%.1f-%.1f, receptacle y%.1f-%.1f (%.1f past the board edge): shelf slot x%.2f-%.2f -> %.2f / %.2f over the whole shelf y%.1f-%.1f; ribs x%.1f / x%.1f -> %.2f / %.2f; "
   "rear-wall opening x%.0f-%.0f z%.0f-%.0f (y%.0f-%.0f) -> x %.2f / %.2f, top %.2f; cable passage y%.0f-%.0f z0-%.0f (v3 A13): plug end + %.0f bend = y%.1f (%.1f spare), %.1f over the plug; "
   "receptacle to the slot edges %.2f, to the ribs %.2f, top z%.1f vs the rear-strip limit z%.1f"
   % (uq_["y"][0], uq_["y_r43"][0], uq_["y"][0], uq_["y"][1], uq_["rcpt"][2], uq_["rcpt"][3], uq_["rcpt_past_board"], uq_["slot"][0], uq_["slot"][1], uq_["slot_margins"][0], uq_["slot_margins"][1],
      uq_["plug_under_shelf_y"][0], uq_["plug_under_shelf_y"][1], P["ribs"][5], P["ribs"][6], uq_["rib_margins"][0], uq_["rib_margins"][1], uq_["wall_open"][0], uq_["wall_open"][1], uq_["wall_open"][2],
      uq_["wall_open"][3], uq_["wall_y"][0], uq_["wall_y"][1], uq_["wall_x_margins"][0], uq_["wall_x_margins"][1], uq_["wall_z_margin"], uq_["passage"][0], uq_["passage"][1], uq_["passage"][2],
      uq_["bend"], uq_["y"][1] + uq_["bend"], uq_["passage_spare"], uq_["passage_top"], uq_["rcpt_slot_margins"][0], uq_["rcpt_rib_margins"][0], uq_["rcpt"][5], P["comp_rear"][1]))
for q_ in C44["standoffs"]:
    if q_.get("hung"):
        # r4.4 fix 2b: boss hung over the board, head / pin under it
        pr("3. boss (%.1f, %.1f) %-5s D%.0f hung over the board z%.1f-%.2f on a bracket to the %s (x%.2f-%.2f y%.2f-%.2f) + %s: to the rail's rear face %.2f, to the shelf ribs %.2f (on the rib axis %s), "
           "inside the board by %.2f%s, to the floor hatch edge %.2f, closest BRD-01 part %.2f (%s), closest fin / keel %.2f"
           % (q_["x"], q_["y"], q_["kind"], P["standoff_d"], q_["boss"][4], q_["boss"][5], q_["attach"], q_["boss"][0], q_["boss"][1], q_["boss"][2], q_["boss"][3],
              ("M3x6 from below, head D%.1f z%.1f-%.1f under the board (L35 ISO 7380 D%.1f x %.2f)" % (2 * q_["top_r"], q_["top_z"][0], q_["top_z"][1], P["board_screw_real"][0], P["board_screw_real"][1])) if q_["kind"] == "screw"
              else ("pin D%.1f hanging through the board to z%.1f" % (2 * q_["top_r"], q_["top_z"][0])), q_["rail_top"], q_["rib_top"], ("%.2f" % q_["rib_top_axis"]) if q_["rib_top_axis"] is not None else "-",
              q_["in_board"], (" (board ring around the D3.2 hole %.2f)" % q_["edge_ring"]) if q_["edge_ring"] is not None else "", q_["hatch"], q_["part_min"][0], q_["part_min"][1], q_["fin"]))
        continue
    pr("3. stand-off (%.1f, %.1f) %-5s D%.0f z%.0f-%.0f + %s: to the rail's rear face %.2f (stand-off %.2f), to the shelf ribs %.2f (on the rib axis %s; stand-off %.2f), inside the board by %.2f%s, "
       "closest BRD-01 part %.2f (%s), closest fin %.2f"
       % (q_["x"], q_["y"], q_["kind"], P["standoff_d"], P["z_floor"][1], P["board_z"][0], ("M3x6 head D%.1f z%.1f-%.1f (v3.2 L35 ISO 7380 D%.1f x %.2f; envelope)" % (2 * q_["top_r"], q_["top_z"][0], q_["top_z"][1], P["board_screw_real"][0], P["board_screw_real"][1])) if q_["kind"] == "screw"
          else ("pin D%.1f to z%.1f" % (2 * q_["top_r"], q_["top_z"][1])), q_["rail_top"], q_["rail_standoff"], q_["rib_top"], ("%.2f" % q_["rib_top_axis"]) if q_["rib_top_axis"] is not None else "-",
          q_["rib_standoff"], q_["in_board"], (" (board ring around the D3.2 hole %.2f)" % q_["edge_ring"]) if q_["edge_ring"] is not None else "", q_["part_min"][0], q_["part_min"][1], q_["fin"]))
if sq_.get("mount") == "hung":
    pr("   M3x6 from below: head under the board z%.2f-%.1f (envelope z%.1f-%.1f, %.1f above the floor's underside), board %.1f + %.1f into the boss; tip z%.1f, bore D%.1f to z%.1f (%.1f above the tip), "
       "boss cap over the bore %.1f; locating pins D%.1f in D%.1f holes (radial play %.2f), tips z%.1f"
       % (sq_["head_z"][0], sq_["head_z"][1], sq_["head_env_z"][0], sq_["head_env_z"][1], sq_["below_hatch"], sq_["stack"][0], sq_["stack"][1], sq_["tip_z"], P["standoff_bore"][0], sq_["bore_top"],
          sq_["bore_above_tip"], sq_["cap_over_bore"], C44["pins"]["d"], C44["pins"]["hole"], C44["pins"]["play"], C44["pins"]["tip_z"]))
else:
    pr("   M3x6: board %.1f + stand-off %.1f + %.1f into the floor = %.1f; tip z%.1f, bore D%.1f to z%.1f (%.1f below the tip), floor under the bore %.1f, thread engagement %.1f"
       % (sq_["stack"][0], sq_["stack"][1], sq_["stack"][2] - 0.4, sq_["length"], sq_["tip_z"], P["standoff_bore"][0], P["standoff_bore"][1], sq_["bore_below_tip"], sq_["floor_under_bore"], sq_["engage"]))
for side_, q_ in C44["ends"].items():
    pr("4. %s end part: board x%.1f-%.1f in the sensor bar x%.1f-%.1f (%.1f / %.1f), support post x%.1f-%.1f + ribs x%.1f-%.1f (front y%.1f-%.1f, rear y%.1f-%.1f open x%.1f-%.1f, top z%.1f); "
       "lead pads x%.2f-%.2f -> gap margins %.2f / %.2f, underside wires enter the rib band at x%s -> %.2f / %.2f; lead %d x 1.27 = %.2f centred x%.2f (x%s-%s, fanned in from the pad row by y%.2f), "
       "lane under the rail x%s-%s (%.2f) z%.0f-%.0f, rear-wall notch same x z%.0f-%.0f; lead path (fan-in included) to the floor parts %.2f (%s), to the A#0 black tab base %s, "
       "balance pins over the lane %s, lane / notch to the fins %.2f, rod end posts %.2f, rear dovetail %s"
       % (side_, q_["board"][0], q_["board"][1], q_["bar"][0], q_["bar"][1], q_["board_in_bar"][0], q_["board_in_bar"][1], P["sb_post"][0], P["sb_post"][1], q_["rib_x"][0], q_["rib_x"][1],
          P["sb_rib_front"][0], P["sb_rib_front"][1], P["sb_rib_rear"][0], P["sb_rib_rear"][1], q_["gap"][0], q_["gap"][1], P["sb_board"][4], q_["pads"][0], q_["pads"][1], q_["pad_margins"][0], q_["pad_margins"][1],
          "/".join("%.2f" % v_ for v_ in q_["wire_cross"]), q_["wire_margins"][0], q_["wire_margins"][1], q_["cores"], q_["lead_w"], q_["lead_xc"], m.fh(q_["lead"][0]), m.fh(q_["lead"][1]), q_["fan_y"],
          m.fh(q_["lane"][0]), m.fh(q_["lane"][1]), q_["lane_w"], q_["lane_z"][0], q_["lane_z"][1], q_["notch_z"][0], q_["notch_z"][1], q_["path_min"][0], q_["path_min"][1],
          ("%.2f" % q_["fan_tab"]) if q_["fan_tab"] is not None else "(none)",
          ", ".join("%s x%.2f (%.1f of rail under the pin)" % tuple(t_) for t_ in q_["pins_over_lane"]) or "none", q_["fin_gap"], q_["post_gap"],
          ("%.2f" % q_["dovetail_gap"]) if q_["dovetail_gap"] is not None else "-"))
pr("5. SB rear support rib (v3 P113 y%.1f-%.1f) gap x%.0f-%.0f -> x%.0f-%.0f: ribbon x%.2f-%.2f margins %.2f / %.2f (r4.3 / v3 gap: %.2f / %.2f); J201 pads %.2f / %.2f"
   % (P["sb_rib_rear"][0], P["sb_rib_rear"][1], rq_["sb_gap_r43"][0], rq_["sb_gap_r43"][1], rq_["sb_gap"][0], rq_["sb_gap"][1], rq_["xc"] - rq_["width"] / 2, rq_["xc"] + rq_["width"] / 2,
      rq_["sb_gap_margins"][0], rq_["sb_gap_margins"][1], rq_["sb_gap_margins_r43"][0], rq_["sb_gap_margins_r43"][1], rq_["j201_margins"][0], rq_["j201_margins"][1]))
pr("6. keep-out x%.2f-%.2f y%.1f-%.1f: the RP2040-Zero PCB (z%.1f-%.1f, on headers) overhangs x%.2f-%.2f y%.1f-%.1f - no pins / pads / traces there (header columns x%.2f / x%.2f); "
   "Zero front edge to the fin foot's rear face %.2f, top parts to the hung fin (z%.1f) %.2f -> kept to y%.1f on the stripboard, the overhang recorded in P23"
   % (zq_["keepout"][0], zq_["keepout"][1], zq_["keepout"][2], zq_["keepout"][3], zq_["pcb_z"][0], zq_["pcb_z"][1], zq_["overhang"][0], zq_["overhang"][1], zq_["overhang"][2], zq_["overhang"][3],
      zq_["lattice_x"][0], zq_["lattice_x"][-1], zq_["foot_gap"], zq_["hung_fin_z"], zq_["to_hung_fin"], zq_["keepout"][3]))
# 7. levers whose key is out: generic z20 envelope vs the actual BRD-01 parts (+ stand-off heads / pins); O1 / O7 carry R301 (lying, D2.5 assumed)
R301_ = ("O1 / O7 only: R301 100k lying (body D2.5 assumed)", 102.58, 108.88, m.rect(153.27 - 1.25, 153.27 + 1.25, P["board_z"][1], P["board_z"][1] + 2.5))
drop_act = {}
for nm_ in ("D#", "E", "F", "F#", "G", "G#"):
    a_ = m.lever_drop(P, g, nm_)                     # generic z20 envelope (r4.4 wording)
    b_ = g["lever_drop"][nm_]
    c_ = m.lever_drop(P, g, nm_, actual=True, extra=[R301_]) if nm_ == "G" else None
    drop_act[nm_] = dict(generic=a_["drop_deg"], generic_onto=a_["onto"], actual=b_["drop_deg"], onto=b_["onto"], F_rest=b_["F_rest"],
                         o17=c_["drop_deg"] if c_ else None, o17_onto=c_["onto"] if c_ else None)
pr("7. key out, lever let go: " + "; ".join("%s %.1f deg onto %s (z20 envelope: %.1f)%s" % (k_, v_["actual"], v_["onto"].replace("board part: ", ""), v_["generic"],
                                                                                          (", O1 / O7 %.1f onto R301" % v_["o17"]) if v_["o17"] else "") for k_, v_ in drop_act.items())
   + "; C301 of the control board is a 1206 chip on the underside (text fix in 1d)")
C44["drop"] = drop_act
# the new fixed parts in the module sweep (every key / lever pose): closest moving part
sw_new = {}
for pref_ in ("control-board", "sensor board", "board part: J301 16-core ribbon under", "board part: USB-C receptacle", "USB-C plug", "board part: CD74HC4067", "board components (<= z20)"):
    q_ = [r_ for r_ in S if r_["b"].startswith(pref_)]
    if q_:
        sw_new[pref_] = dict(d=q_[0]["d"], a=q_[0]["a"], part_a=q_[0]["part_a"], pose_a=q_[0]["pose_a"], b=q_[0]["b"])
C44["sweep_new"] = sw_new
C44["sweep_head"] = sw_new.get("control-board", {}).get("d")
pr("   module sweep, closest moving part to the new / moved fixed parts: " + "; ".join("%s %.2f (%s [%s %s])" % (k_, v_["d"], v_["a"], v_["part_a"], v_["pose_a"]) for k_, v_ in sw_new.items()))
R["c44"] = C44
# r4.4 fix 2b (verifier geometry critical): the control board's way into the one-piece frame
BI = m.board_insert_check(P, g)
pr("r4.4 fix 2b: control board goes in from below through the floor hatch x%.2f-%.2f y%.1f-%.1f (notch x%.2f-%.2f to y%.1f behind the receptacle), straight up along z, its slot sliding along the "
   "F|F# foot + keel: closest frame part along the path %.2f (%s | %s); per frame part: %s; stops (above the board, contact 0 = seat): %s; locating pins radial play %.2f"
   % (BI["hatch"] + BI["notch"] + (BI["min"], BI["pair"][0], BI["pair"][1], "; ".join("%s %.2f (%s)" % (b_[:44], d_, a_[:30]) for d_, b_, a_ in BI["by_fixed"][:8]),
      "; ".join("%s %.2f" % (b_[:40], z_) for z_, a_, b_ in BI["stops"][:6]), BI["pin_play"])))
R["board_insert"] = BI
# r4.4 fix 2b (verifier printables major): capstan crown at the settled rest in the frame (the T2 bench gauge target)
crown_ = {}
for col_, A_ in (("white", Aw), ("black", Ab)):
    q_ = m.key_point_world(A_, dyn[col_]["rest_state"], (caps[col_], P["z_c"]))
    crown_[col_] = q_[1]
pr("r4.4 fix 2b: capstan crown top at the settled rest (key sinks on its notch cloth / rest felt, lever on the capstan): white %.3f, black %.3f (key frame z%.1f) -> T2 dummy-lever floor / zero pads at z%.2f"
   % (crown_["white"], crown_["black"], P["z_c"], round((crown_["white"] + crown_["black"]) / 2, 2)))
R["fix2b"] = dict(crown_rest=crown_, crown_T2=round((crown_["white"] + crown_["black"]) / 2, 2), hatch=P["board_hatch"], notch=P["board_hatch_notch"], keel=P["fin_keel"],
                  bosses=m.board_boss_rects(P, g["z_shelf"] - 2.0), relief=P["tail_relief"], side_wall=P["carrier_side_wall"], lip_over=P["lip_over"])

# ----------------------------------------------------------------------------------------------- Q3 r4.5 circuit 2nd cross-check
sec("Q3. r4.5 CIRCUIT 2ND CROSS-CHECK (hardware/pcb README '2차 요청' items 8-11; 12-13 handled elsewhere) - measured on this model")
C45 = {}
# item 8: the v3 P112 right ledge over the sensor bar's right end
LED = m.sb_ledge_prisms(P)
lx0_, lx1_, px1_, zl0_, zl1_ = P["sb_ledge"]
bar_end_ = max(f[2] for f in m.fixed_prisms(P, g) if f[0] == "sensor bar")
brd_end_ = P["sb_board"][1]
xB_ = keys["B"]["xc"]
colB_ = min(0.63 + 2.54 * i_ for i_ in range(80) if 0.63 + 2.54 * i_ >= xB_ + 3.0)
lead_y_ = (63.9, 70.1)                                   # v3 P112 note: B sensor leads / pads y63.9-70.1 (rows 64.46 / 67.00 / 69.54 +- pad)
led_sweep = [r_ for r_ in S if r_["b"].startswith("sensor-bar ledge")]
led_min = led_sweep[0] if led_sweep else None
# the neighbouring module (x + 164.5) and the right end part ER (O7 + ER local x) across the seam: every fixed prism except the
# abutting floors (fixed-to-fixed; the seam rule for faces is the 0.2 inset each side = 0.4)
def _fx_min(A_, B_, skip_=("floor",)):
    best_ = (1e9, None, None)
    for a_ in A_:
        for b_ in B_:
            if b_[0].startswith(skip_) or b_[2] < a_[1] - 8 or b_[1] > a_[2] + 8:
                continue
            d_, _ = m.prism_dist((a_[1], a_[2]), a_[3], (b_[1], b_[2]), b_[3])
            if d_ < best_[0]:
                best_ = (d_, a_[0], b_[0])
    return best_
nb_mod_ = [(f[0], f[1] + P["module_w"], f[2] + P["module_w"], f[3]) for f in m.fixed_prisms(P, g)]
er_ = [(f[0], f[1] + P["module_w"], f[2] + P["module_w"], f[3]) for f in m.end_fixed_prisms(P, g, ep["right"])]
own_ = [f for f in m.fixed_prisms(P, g) if not f[0].startswith(("sensor-bar ledge", "floor", "sensor bar", "sensor board"))]
C45["ledge"] = dict(prisms=[(f[0], f[1], f[2], f[3]) for f in LED], lip=(lx0_, lx1_), post=(lx1_, px1_), z=(zl0_, zl1_), y=P["sb_ledge_y"], floor_z=P["z_floor"][1],
                    bar_end=bar_end_, board_end=brd_end_, over_bar=bar_end_ - lx0_, post_to_bar=lx1_ - bar_end_, post_to_board=lx1_ - brd_end_, bar_top_w=P["bar_top_w"],
                    held_area=(bar_end_ - lx0_) * sum(b_ - a_ for a_, b_ in P["sb_ledge_y"]), seam_inset=P["module_w"] - px1_,
                    B_sensor_x=xB_, B_lead_col=colB_, lip_to_B_col=lx0_ - colB_, lead_y=lead_y_, lead_y_gaps=(lead_y_[0] - P["sb_ledge_y"][0][1], P["sb_ledge_y"][1][0] - lead_y_[1]),
                    sweep=dict(d=led_min["d"], a=led_min["a"], part_a=led_min["part_a"], pose_a=led_min["pose_a"], b=led_min["b"]) if led_min else None,
                    sweep_after_tol=(led_min["d"] - m.TOL) if led_min else None,
                    neighbour_module=_fx_min(LED, nb_mod_), end_part_ER=_fx_min(LED, er_), own_other=_fx_min(LED, own_),
                    c214=(158.11 - 1.2, 158.11 + 1.2), mass_note="v3 frame 175 g (frame_mass v3_frame) already holds the v3 P112 ledge",
                    ends=dict(left=dict(bar=(0.5, m.END_DEF["left"]["x"][1] - 0.5), screws="2 x M3x10 at x3.0 (v3 P111) into the post x0.5-6.0"),
                              right=dict(bar=(0.5, m.END_DEF["right"]["x"][1] - 0.5), screws="2 x M3x10 at x3.0 (v3 P111) into the post x0.5-6.0")))
q8_ = C45["ledge"]
pr("8. sensor-bar right ledge (v3 P112) back in the frame: two pieces y%.1f-%.1f / y%.1f-%.1f (off the B sensor leads y%.1f-%.1f by %.1f / %.1f), each an inverted L - lip x%.1f-%.1f z%.1f-%.1f "
   "(underside = white bar top z%.1f, over the bar end x%.1f by %.1f -> %.1f mm2 held), post x%.1f-%.1f from the floor z%.1f (%.1f from the bar end, %.1f from the board end x%.1f; %.1f seam inset); "
   "B lead holes at x%.2f (sensor x%.3f + 3.0 -> first 2.54 grid), lip %.2f beyond; C214 (underside x%.2f-%.2f) and the J201 pads are far; closest moving part %.2f (after tol %.2f): %s [%s %s]; "
   "across the seam: next module %.2f (%s vs %s), right end part ER %.2f (%s vs %s); other own frame parts %.2f (%s)"
   % (P["sb_ledge_y"][0][0], P["sb_ledge_y"][0][1], P["sb_ledge_y"][1][0], P["sb_ledge_y"][1][1], lead_y_[0], lead_y_[1], q8_["lead_y_gaps"][0], q8_["lead_y_gaps"][1], lx0_, lx1_, zl0_, zl1_,
      P["bar_top_w"], bar_end_, q8_["over_bar"], q8_["held_area"], lx1_, px1_, P["z_floor"][1], q8_["post_to_bar"], q8_["post_to_board"], brd_end_, q8_["seam_inset"],
      colB_, xB_, q8_["lip_to_B_col"], q8_["c214"][0], q8_["c214"][1],
      led_min["d"] if led_min else float("nan"), (led_min["d"] - m.TOL) if led_min else float("nan"), led_min["a"] if led_min else "-", led_min["part_a"] if led_min else "-", led_min["pose_a"] if led_min else "-",
      q8_["neighbour_module"][0], q8_["neighbour_module"][1], q8_["neighbour_module"][2], q8_["end_part_ER"][0], q8_["end_part_ER"][1], q8_["end_part_ER"][2], q8_["own_other"][0], q8_["own_other"][2]))
# item 11: the left end part's floor (the module's control-board hatch cut no longer leaks into it)
_efl = {}
for side_ in ("left", "right"):
    fl_ = sorted([(f[1], f[2], min(q[0] for q in f[3]), max(q[0] for q in f[3])) for f in m.end_fixed_prisms(P, g, ep[side_]) if f[0].startswith("floor")])
    xs_ = sorted(set([a_ for a_, b_, c_, d_ in fl_] + [b_ for a_, b_, c_, d_ in fl_]))
    gaps_ = []
    for x0_, x1_ in zip(xs_[:-1], xs_[1:]):
        xm_ = 0.5 * (x0_ + x1_)
        ys_ = sorted((c_, d_) for a_, b_, c_, d_ in fl_ if a_ <= xm_ <= b_)
        y_ = 0.0
        for c_, d_ in ys_:
            if c_ > y_ + 1e-6:
                gaps_.append((x0_, x1_, y_, c_))
            y_ = max(y_, d_)
        if y_ < P["frame_depth"] - 1e-6:
            gaps_.append((x0_, x1_, y_, P["frame_depth"]))
    _efl[side_] = dict(pieces=fl_, gaps=gaps_)
    pr("11. %s end part floor: %d piece(s) %s, holes in it: %s" % (side_, len(fl_), "; ".join("x%.2f-%.2f y%.1f-%.1f" % q_ for q_ in fl_), "; ".join("x%.2f-%.2f y%.1f-%.1f" % q_ for q_ in gaps_) or "none"))
_old_el = [(46.25, 46.8, 144.5, 196.5)]
C45["el_floor"] = dict(now=_efl, r45c_gap=_old_el, hatch=P["board_hatch"])
# item 10: landings of the levers whose key is out (same numbers as metrics lever_drop / circuit_r44.drop)
C45["drop"] = {k_: dict(deg=v_["drop_deg"], onto=v_["onto"]) for k_, v_ in g["lever_drop"].items()}
pr("10. key out, lever let go (DESIGN 11 step 6 now uses these): " + "; ".join("%s %.2f deg onto %s" % (k_, v_["deg"], v_["onto"][:48]) for k_, v_ in C45["drop"].items()))
# interface: the ribbon lane and the circuit numbers are untouched
C45["interface"] = dict(ribbon_x=tuple(P["ribbon_x"]), lane_z=(5.0, 10.0), sb_board=tuple(P["sb_board"]), sb_post=tuple(P["sb_post"]), board_hatch=tuple(P["board_hatch"]), usb_z=tuple(P["usb_z"]), changed=False)
pr("interface: ribbon lane x%.0f-%.0f z5-10, SB x%.1f-%.1f y%.2f-%.2f z%.1f-%.1f, control-board hatch, USB-C plug z%.1f-%.1f - unchanged" % (P["ribbon_x"] + tuple(P["sb_board"]) + tuple(P["usb_z"])))
R["c45"] = C45

# ----------------------------------------------------------------------------------------------- I masses / print plan
sec("I. MASS, PRINT PLAN (PETG 1.25 g/cm3, 15 g/h, 220x220 bed)")
kw = {n: m.petg_mass(m.key_body(P, keys[n], caps["black" if keys[n]["black"] else "white"], lay["levers"][n])) for n in m.ORDER}
lv_p = m.lever_carrier_mass(P)
frame_g, frame_parts = m.frame_mass(P, g)
sup_plate = m.plate_support_mass(P, g)
curtain_g = m.curtain_mass(P, g)
bar_g = [m.pad_bar_mass(P, g, b - a) for a, b in bays]
sensor_bar_g = 17.0
sup_w, sup_b = m.support_mass(P, False), m.support_mass(P, True)
keys_g = sum(kw.values())
supports_g = 7 * sup_w + 5 * sup_b + sup_plate
module_print = keys_g + 12 * lv_p + frame_g + curtain_g + sensor_bar_g + sum(bar_g)
pr("per key PETG: " + ", ".join("%s %.1f" % (n, kw[n]) for n in m.ORDER) + " g; lever carrier %.2f g" % lv_p)
pr("frame %.1f g = " % frame_g + " + ".join("%s %.1f" % kv for kv in frame_parts.items()))
pr("supports: keys %.1f g (white %.1f, black %.1f each) + under the top plate %.1f g = %.1f g per module" % (7 * sup_w + 5 * sup_b, sup_w, sup_b, sup_plate, supports_g))
pr("curtain strip %.1f g, sensor bar %.0f g, 4 pad bars %s g" % (curtain_g, sensor_bar_g, " / ".join("%.1f" % b for b in bar_g)))
pr("module print: %.0f g parts + %.0f g supports = %.0f g, %.1f h" % (module_print, supports_g, module_print + supports_g, (module_print + supports_g) / 15))
steel_block = Aw.lev.mass_of(m.RHO_ST)
rod4_g = math.pi * 4 * (P["rod_k_x"][1] - P["rod_k_x"][0]) * m.RHO_SUS
rodL_g = math.pi * (P["rod_L"] / 2) ** 2 * (P["rod_L_x"][1] - P["rod_L_x"][0]) * m.RHO_SUS
magnets_g = 12 * math.pi / 4 * 25 * 2 * m.RHO_MAG
pad_g = m.pad_mass(P)
felt_g = 12 * (7 * (P["felt_c_y"][1] - P["felt_c_y"][0]) * 2 + 8 * 2.7 * 1.5) * m.RHO_FELT
pins_g = 12 * math.pi / 4 * P["pin_d"] ** 2 * P["pin_len"] * m.RHO_SUS
caps_g = 12 * 0.95
spring_g = 12 * m.spring_mass(P)[0]          # r4.5: cut MISUMI spring (r4.4: 0.15 g each)
eva_elec = 26 + 60
module_mass = module_print + 12 * steel_block + rod4_g + rodL_g + magnets_g + 12 * pad_g + felt_g + pins_g + caps_g + spring_g + eva_elec
pr("module mass: prints %.0f + steel blocks 12 x %.1f = %.0f + rods %.0f + pads 12 x %.2f + magnets/felt/pins/capstans/springs %.0f + EVA/electronics %d = %.3f kg (v3 0.59, r3 2.03)"
   % (module_print, steel_block, 12 * steel_block, rod4_g + rodL_g, pad_g, magnets_g + felt_g + pins_g + caps_g + spring_g, eva_elec, module_mass / 1000))
print_plan = [
    ("백건 (7종)", "윗면을 매끈한 PEI에 대고 뒤집어(v3 방향). 트리 서포트는 숨은 빔·꼬리(y146~199) 밑에만. 노치 R2.55는 출력 맨 위의 열린 홈, 밸런스 핀 홈(폭 %.1f+천)은 블록 밑면에서 열림" % P["slot_w"],
     "%.1f + 서포트 %.1f" % (kw["D"], sup_w)),
    ("흑건 (4종: C#·D#은 같음)", "같은 방향(윗면이 베드). 서포트는 빔·꼬리 밑. 납·추 칸 없음", "%.1f + 서포트 %.1f" % (kw["C#"], sup_b)),
    ("레버 캐리어 (칼라가 위치마다 달라 모듈 12종 + 끝 부속 3종 = 15종, 옆벽에 음 이름 새김)", "옆으로 눕혀(옆벽이 베드, 허브 구멍이 세로). 강철 칸 안에 지지대 1개(z 틈 0.2): 먼 쪽 옆벽·립이 칸 위를 40 mm 건넘. 허브 구멍 Ø3.9로 뽑아 Ø4.0 드릴, 허브 칼라·스프링 주머니 함께 출력", "%.2f" % lv_p),
    ("프레임", "바로 세워(v3). 윗판 밑(y146.5~209)은 바닥·선반에서 올라오는 트리 서포트. 패드 바 레일(도브테일)은 윗판에 붙어 있음. 핀 보스 구멍 Ø3.9 눈물방울, Ø4.0 드릴", "%.0f + 서포트 %.0f" % (frame_g, sup_plate)),
    ("패드 바 (4개, 칸마다 다름: 모듈 4종 + 끝 부속 2종, 손잡이에 칸 이름 새김)", "윗면을 베드에(쐐기가 위). 앞 손잡이 3 mm, 뒤 계단 양쪽에 예하중 잎 0.6×4×8", "%.1f" % (sum(bar_g) / 4)),
    ("가림판 띠", "넓은 면을 베드에, 걸이 립은 위로", "%.0f" % curtain_g),
    ("센서 바", "v3 (포켓이 위)", "%.0f" % sensor_bar_g),
]
for p_ in print_plan:
    pr("  %-26s %-16s g | %s" % (p_[0], p_[2], p_[1]))
R["mass"] = dict(support_white_g=sup_w, support_black_g=sup_b, support_plate_g=sup_plate, key_g=kw, lever_carrier_g=lv_p, frame_g=frame_g,
                 frame_parts=frame_parts, curtain_g=curtain_g, sensor_bar_g=sensor_bar_g, pad_bars_g=bar_g, supports_module_g=supports_g,
                 module_print_g=module_print, steel_block_g=steel_block, rod4_g=rod4_g, rodL_g=rodL_g, pad_g=pad_g, module_mass_g=module_mass,
                 print_plan=print_plan, felt_g=felt_g, pins_g=pins_g, magnets_g=magnets_g)

# ----------------------------------------------------------------------------------------------- J end parts
sec("J. END PARTS - same section and mechanism; left A0/A#0/B0 (keys x0-47, cheek x%.2f..%.2f), right C8 (local x, cheek x%.2f..%.2f)"
    % (m.END_DEF["left"]["cheek"] + m.END_DEF["right"]["cheek"]))
end_print, end_mass, ep_loads = 0.0, 0.0, {}
for side in ("left", "right"):
    e = ep[side]
    pr("%s: levers %s, fins %s, fin bosses (L/R) %s, collars %s" % (side, e["lay"]["levers"], e["lay"]["fins"], m.fin_boss_len(e["lay"], P), e["collars"]))
    for nm in e["order"]:
        q = e["stat"][nm]
        pr("   %-3s capstan y%.2f DW %.2f UW %.2f m_eff %.1f key %.1f g; its steel top vs its colour's pad face at its own settled bottom %+.2f (design %+.2f; PET shims trim it)"
           % (nm, q["y_cap"], q["DW"], q["UW"], q["meff"], q["key_g"], q["gap_to_face"], q["gap_design"]))
    ck = e["cheek"]
    cheek_w = ck[1] - ck[0]
    xf = [(f0, f1) for f0, f1 in e["lay"]["fins"]]
    extra = [(ck[0], ck[1])]
    x_rng = (min(e["x"][0], ck[0]) + 0.2, max(e["x"][1], ck[1]) - 0.2)
    yl_ = {False: g["y_load_w"], True: g["y_load_b"]}
    kse, _ = m.plate_seat_k(P, g, xf, e["lay"]["levers"], yl_, {n: e["keys"][n]["black"] for n in e["order"]}, x_range=x_rng, extra_fins=extra)
    pls = m.plate_loads(P, g, up_abuse[0], up_abuse[1], xf, e["lay"]["levers"], e["keys"], x_range=x_rng, extra_fins=extra, chords=True)
    ep_loads[side] = dict(seat_k=kse, abuse=pls)
    pr("   seats %s N/mm; all keys at the 2.5 m/s peak at once: plate %.1f MPa, fin top %.1f MPa, seat %.2f mm"
       % (", ".join("%s %.0f" % kv for kv in kse.items()), pls["chord"]["sigma"], pls["chord"]["fin_top"], pls["chord"]["seat_max"]))
    n = len(e["order"])
    nb = sum(1 for k in e["order"] if e["keys"][k]["black"])
    width = 47.0 if side == "left" else 39.5
    prt = sum(e["stat"][k]["key_g"] for k in e["order"]) + n * lv_p + frame_g * width / 164.5 * 1.15 + curtain_g * width / 164.5 + m.pad_bar_mass(P, g, xf[1][0] - xf[0][1]) \
        + (n - nb) * sup_w + nb * sup_b + sup_plate * width / 164.5
    end_print += prt
    end_mass += prt + n * (steel_block + pad_g + 0.95 + 0.15 + 0.29) + (width / 164.5) * (rod4_g + rodL_g)
R["end_parts"] = {s: dict(levers=ep[s]["lay"]["levers"], fins=ep[s]["lay"]["fins"], stat=ep[s]["stat"], cheek=ep[s]["cheek"], collars=ep[s]["collars"],
                          boss_len=m.fin_boss_len(ep[s]["lay"], P), blocks={nm: m.block_x(P, ep[s]["keys"][nm]) for nm in ep[s]["order"]},
                          loads=dict(seat_k=ep_loads[s]["seat_k"], sigma=ep_loads[s]["abuse"]["chord"]["sigma"], fin_top=ep_loads[s]["abuse"]["chord"]["fin_top"]))
                  for s in ep}
spare_keys_g = sum(kw.values()) + ep["left"]["stat"]["A0"]["key_g"] + ep["left"]["stat"]["B0"]["key_g"] + ep["right"]["stat"]["C8"]["key_g"] + \
    ep["left"]["stat"]["A#0"]["key_g"] + 3.0          # r4.1: no complete spare levers / spare pad bar (position-specific; printed from the file when needed)
other_v3 = 200 + 64 + 310 + 388 + 12
total_g = 7 * (module_print + supports_g) + end_print + other_v3 + spare_keys_g
steel_88 = 90 * steel_block / 1000
rods_kg = (7 * (rod4_g + rodL_g) + (rod4_g + rodL_g) / 161.4 * (48.0 + 25.0) + 2 * rod4_g) / 1000
pr("\n88 keys: 7 modules %.2f kg + end parts %.2f kg + other v3 prints %.2f kg + spare set %.2f kg = %.2f kg filament, %.0f h at 15 g/h"
   % (7 * (module_print + supports_g) / 1000, end_print / 1000, other_v3 / 1000, spare_keys_g / 1000, total_g / 1000, total_g / 15))
pr("metal: blocks 90 x %.1f g = %.2f kg (88 + 2 spare); rods %.2f kg (7 x 2 + end parts + 2 spare) -> %.2f kg (r3 9.52 kg)" % (steel_block, steel_88, rods_kg, steel_88 + rods_kg))
body_88 = (7 * module_mass + end_mass + 400) / 1000
pr("88-key body about %.1f kg (v3 4.5 kg, r3 15.3 kg); heaviest single part to carry = one module %.2f kg" % (body_88, module_mass / 1000))
R["totals"] = dict(filament_kg=total_g / 1000, print_h=total_g / 15, steel_kg_88=steel_88, rods_kg=rods_kg, metal_kg=steel_88 + rods_kg, body_kg=body_88,
                   spare_set_g=spare_keys_g, end_print_g=end_print, end_mass_g=end_mass)

# ----------------------------------------------------------------------------------------------- K removal / adjustment
sec("K. SINGLE-KEY REMOVAL AND ADJUSTMENT (tool-free)")
rw, rb = g["removal_w"], g["removal_b"]
pr("lift the curtain strip; slide that bay's pad bar out by its grip; lift the own lever by its fingernail tab (%.2f N white / %.2f N black) to %.1f deg; with the other hand's fingernail under "
   "the 1.0 mm rear lip (y146-147) pull up %.1f N (white) / %.1f N (black) with the snap at %.0f N (%.1f / %.1f N with the tightest R2.50 coupon; %.1f / %.1f N if the lever rests on the capstan): "
   "the key pivots on its tail pad (front rises %.1f to the keeper), then on the keeper until the rear notch lip is %.1f above the rod top; the block is then %.2f / %.2f above its balance pin; "
   "slide 3 mm forward, tilt, draw out. Black keys: both white neighbours first. A lever whose key is out lies on the floor / board parts (above)"
   % (rw["F_tab"], rb["F_tab"], BH, rw["pull_N"], rb["pull_N"], P["snap_F"], rw["pull_N_snap_hi"], rb["pull_N_snap_hi"], rw["pull_N_lever"], rb["pull_N_lever"],
      rw["front_rise_to_keeper"], P["removal_lip_clear"], rw["pin_clear"], rb["pin_clear"]))
adj = {}
for A, nm, c in ((Aw, "white", "w"), (Ab, "black", "b")):
    base = A.statics(1e-4)["DW"]
    st0, top0, _, _ = m.held_bottom(A, g["z_shelf"], 1.0)
    for turns in (0.125, 0.5):
        dz = 0.5 * turns
        A2 = m.Action(P, A.kd, A.y_cap, A.x_lever, cap_dz=dz)
        adj["%s_%s" % (nm, turns)] = dict(dDW=A2.statics(1e-4)["DW"] - base, dcap=m.held_bottom(A2, g["z_shelf"], 1.0)[1] - top0)
    As_ = m.Action(P, A.kd, A.y_cap, A.x_lever, extra=[("lever", "putty on the steel front", P["y_steel_front"] + 6.0, P["z_st"] + 1.0, 1.0)])
    Af = m.Action(P, A.kd, A.y_cap, A.x_lever, extra=[("key", "putty front", A.stop_pts[0][0] + 3.0, P["key_bot"] + 2.0, 1.0)])
    adj[nm + "_putty_steel"] = As_.statics(1e-4)["DW"] - base
    adj[nm + "_putty_front"] = Af.statics(1e-4)["DW"] - base
    # PET shim 0.1 under a pad: the face moves 0.1 down along its normal -> the lever meets it earlier
    pt = g["pad_" + c]
    pt2 = m.PadTable(A, g["held_b_" + c], P["gap_us_" + c] - 0.1)
    adj[nm + "_shim"] = dict(db0_deg=D(pt.b0 - pt2.b0), front_mm=D(pt.b0 - pt2.b0) / D(A.b_dip) * A.dip)
    pr("%s: capstan 1/8 turn out (bench gauge, before the key goes in): DW %+.2f g, held cap %+.2f mm | half turn: DW %+.2f g | putty 1 g on the steel front top %+.2f g, at the key front %+.2f g | "
       "0.1 PET shim under the pad: the lever meets it %.2f deg earlier = %.2f mm earlier at the key front"
       % (nm, adj[nm + "_0.125"]["dDW"], adj[nm + "_0.125"]["dcap"], adj[nm + "_0.5"]["dDW"], adj[nm + "_putty_steel"], adj[nm + "_putty_front"],
          adj[nm + "_shim"]["db0_deg"], adj[nm + "_shim"]["front_mm"]))
yr = sum(P["rest_pad_y"]) / 2
adj["levelling_front_per_punching"] = 0.1 * (P["K"][0] - 0.0) / (yr - P["K"][0])
pr("key levelling: each 0.1 mm punching under a rest pad lowers the key front %.2f mm (bench jig: D4 rod stub + rest shelf z%.3f + 43.5 height block)" % (adj["levelling_front_per_punching"], g["z_shelf"]))
R["adjust"] = adj
R["removal"] = dict(white=rw, black=rb)

# ----------------------------------------------------------------------------------------------- L cost
sec("L. PURCHASED PARTS AND COST DELTA vs v3.2 (KRW; '추정' = estimate)")
n_blocks = 90
cost_items = [
    ("SS400 평철 9T×19, 1 m 4개 (블록 %d × (40 + 톱날 2) = %.2f m)" % (n_blocks, n_blocks * 42 / 1000), 4, 3500, "추정 (9T×50의 단면 38 %)"),
    ("강철 약 5 kg 택배", 1, 5000, "추정"),
    ("SUS304 환봉 Ø4 h9 × 4 m (건반 봉 + 레버 봉 %.2f m)" % ((7 * 2 + 2) * 161.4 / 1000 + 0.15), 1, 7000, "추정 (W1)"),
    ("M3×6 ISO 7380 버튼헤드 SUS (캡스턴) 100개 + M3 너트 100개", 1, 7000, "추정"),
    # r4.5: MISUMI Korea economy torsion spring, 282 KRW + VAT each at 100+ (2026-09-28), VAT incl. 310
    ("비틀림 스프링 미스미 %s (SUS304-WPB d0.5 ID5 3권 암 90°, 두 다리를 %.1f / %.1f로 잘라 씀) 100개 (88 + 단계 0 시험 4 + 예비 8)" % (P["spring_cat"]["part"], P["spring_leg"], P["spring_short_leg"]), 100, 310,
     "한국미스미 9/28 확인: 100개 이상 282원 + VAT"),
    ("경선(피아노선) 니퍼 — 스프링 다리 200곳 자름 (d0.5 SUS 경강선)", 1, 15000, "추정 (공구, 악기당 1)"),
    ("밸런스 핀 SUS Ø2×12 (ISO 2338) 100개", 1, 6000, "추정"),
    ("Ø4.0 드릴", 1, 2000, "추정"),
]
removed = [("v3.2 척추 클램프 M3×40 + 와셔", 32, 120), ("세트스크루 M3×10 평끝", 32, 120), ("황동 원판 8×1", 32, 250), ("M3 너트 (클램프 + 세트스크루)", 64, 30)]
consum = [("MS 폴리머(하이브리드) 탄성 접착제 튜브 약 80 mL (r4.4 고침 2b: 강철 블록 90개 × 두 옆면 약 0.2 mL; 고침 2의 5분 에폭시 대신)", 8000), ("부싱 천 0.5T (노치·밸런스 핀 홈·탭) A4 한 장", 5000), ("펠트 1T·1.5T·2T 띠 추가", 6000),
          ("미세셀 우레탄 폼 6T (PORON 계열, 업스톱 패드 100개) + 앞 펠트 밑 PU 1T, 약 200×300", 15000), ("OHP 필름 (PET 심 0.1)", 1000), ("흑연 가루", 3000)]
optional = [("평철 90조각 절단을 철공소에 맡김 (모따기 없음)", 31500, "추정 1개 350원"),
            ("직접 자를 때 쇠톱·바이스 (90번 약 4시간)", 0, "가진 공구")]
add = sum(q * u for _, q, u, _ in cost_items)
rem = sum(q * u for _, q, u in removed)
for n_, q, u, src in cost_items:
    pr("  + %-72s %3d x %6d = %7d  [%s]" % (n_, q, u, q * u, src))
for n_, q, u in removed:
    pr("  - %-72s %3d x %6d = %7d  [추정]" % (n_, q, u, q * u))
for n_, c in consum:
    pr("  consumable: %-60s %7d  [추정]" % (n_, c))
for n_, c, src in optional:
    pr("  optional:   %-60s %7d  [%s]" % (n_, c, src))
delta = add - rem
pr("base (non-consumable) delta = +%d - %d = %+d KRW -> base BOM 583,219 + %d = %d (cap 1,000,000; r3 +130,400)" % (add, rem, delta, delta, 583219 + delta))
R["cost"] = dict(add=add, removed=rem, delta=delta, items=cost_items, removed_items=removed, consumables=consum, optional=optional, base_bom=583219 + delta)

# ----------------------------------------------------------------------------------------------- M spare bay
sec("M. SPARE-KEY BAY (R29, inner 338.8 x 172 x 77) - r4 (A9): key zone 1.0 + 199.3 + 1.0, divider 1.2, side zone 136.3")
h_w = P["key_top"] - (P["beam_z"][0] - P["rest_felt"] - P["rest_shim"])
lw = P["y_tail_end"] + 0.3
row1 = 7 * (23.5 - P["head_gap"] + 0.86)
row2 = 6 * (P["black_w"] + 1.4) + 3 * 23.0
side = 338.8 - (1.0 + lw + 1.0) - 1.2
stack = h_w + P["black_top"] - (P["beam_z"][0] - P["rest_felt"] - P["rest_shim"])
pr("key zone %.1f (1.0 + key %.1f (199.0 + FDM 0.3) + 1.0); layer 1: 7 white keys C..B top-down %.1f x %.1f; layer 2: 5 black + A#0 + A0, B0, C8 %.1f x %.1f; stack %.1f of 77; width margin %.2f / side"
   % (lw + 2.0, lw, row1, h_w, row2, stack - h_w, stack, (172 - max(row1, row2)) / 2))
pr("side zone %.1f x 172 x 77: 2 spare steel blocks, D4 rods %.1f (x2, along the 172 depth: %.1f each end), 12 spare pads, (r4.1: no complete spare levers / pad bar - position-specific, printed from the file) "
   "12 torsion springs, PET shims, small-parts box" % (side, P["rod_k_x"][1] - P["rod_k_x"][0], (172 - 161.4) / 2))
bay_mass = spare_keys_g + 2 * steel_block + 2 * rod4_g + 40      # r4.4 fix 2: 2 spare blocks (parts list), r4.3 counted 4
R["spare_bay"] = dict(key_zone=lw + 2.0, divider=1.2, side_zone=side, layer1=(lw, row1, h_w), layer2=(lw, row2, stack - h_w), stack=stack, mass_kg=bay_mass / 1000,
                      width_margin=(172 - max(row1, row2)) / 2)

# ----------------------------------------------------------------------------------------------- N metrics + targets
sec("N. ENVELOPE AND TARGET CHECK (R4 brief load envelopes)")
dw, db = dd["white"], dd["black"]
mt = {}
mt["dw_white_g"], mt["uw_white_g"] = R["white"]["DW"], R["white"]["UW"]
mt["dw_black_g"], mt["uw_black_g"] = R["black"]["DW"], R["black"]["UW"]
mt["m_eff_white_g"], mt["m_eff_black_g"] = R["white"]["meff"], R["black"]["meff"]
mt["t50_white_ms"], mt["t50_black_ms"] = dw["t50"], db["t50"]
mt["full_return_white_ms"], mt["full_return_black_ms"] = dw["t100"], db["t100"]
mt["full_return_2f_ms"] = max(dw["t100_2f"], db["t100_2f"])
mt["rep_hz_white"], mt["rep_hz_black"] = dw["rep"], db["rep"]
mt["rep_hz_white_2x_friction"], mt["rep_hz_black_2x_friction"] = dw["rep_2f"], db["rep_2f"]
mt["front_back_ratio"] = R["front_back_ratio"]
mt["max_rest_stress_mpa"] = rs["max"]
play_keys = [k for k in dd["white"] if k.startswith("play_")] + ["pp", "mf", "ff_push", "push6", "ff_rel", "ff_h1.00", "release"]
abuse_keys = [k for k in dd["white"] if k.startswith("abuse_")] + ["chord20_rel", "chord20_h1.00"]
mt["key_lift_play_mm"] = max(dd[c][k]["lift_max"] for c in dd for k in play_keys)
mt["key_lift_abuse_mm"] = max(dd[c][k]["lift_max"] for c in dd for k in abuse_keys)
# r4.1: materials at the nominal contact-law floor are judged; the v_floor 0.1 model corner is reported separately
pass_sets = (LAND_LAB, "seat stiffest key", "pad e 0.07 (pass line)", "pad E 0.7 (softer foam)", "pad E 1.4 (firmer foam)", "front felt e 0.28",
             "pass lines together (pad e 0.07, E 0.7, front e 0.22)", "lip friction 0.35", "friction x2")
floor_sets = ("v_floor 0.1", "pass lines + v_floor 0.1")
mt["key_lift_play_sets_mm"] = max(max(q["lift_play"] for q in R["sens"][s].values()) for s in pass_sets)
mt["key_lift_play_worst_mm"] = max(q["lift_play"] for q in R["sens"]["worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)"].values())
mt["key_lift_abuse_sets_mm"] = max(max(q["lift_abuse"] for q in R["sens"][s].values() if q["lift_abuse"] is not None) for s in pass_sets + ("pad e 0.10", "worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)"))
mt["key_lift_chord_mm"] = max([v["lift_max"] for c in chord_dyn for k, v in chord_dyn[c].items() if k.startswith("play_")] +
                              [q[1] for (c_, mat_), rows in CS.items() if mat_ in ("nom", "passline") for q in rows] +
                              [v["lift_max"] for c_ in CG for v in CG[c_].values()])
mt["key_lift_chord_nom_mm"] = max(q[1] for (c_, mat_), rows in CS.items() if mat_ == "nom" for q in rows)
mt["key_lift_chord_pass_mm"] = max(q[1] for (c_, mat_), rows in CS.items() if mat_ == "passline" for q in rows)
mt["key_lift_chord_vf01_mm"] = max(q[1] for (c_, mat_), rows in CS.items() if mat_ in ("vf01", "pass_vf01") for q in rows)
mt["key_lift_chord_worst_mm"] = max(q[1] for (c_, mat_), rows in CS.items() if mat_ == "worst" for q in rows)
mt["keeper_chord_min_mm"] = min(q[2] for (c_, mat_), rows in CS.items() if mat_ in ("nom", "passline") for q in rows)
mt["keeper_chord_vf01_mm"] = min(q[2] for (c_, mat_), rows in CS.items() if mat_ in ("vf01", "pass_vf01") for q in rows)
mt["keeper_chord_worst_mm"] = min(q[2] for (c_, mat_), rows in CS.items() if mat_ == "worst" for q in rows)
mt["key_lift_vf01_single_mm"] = max(max(q["lift_play"] for q in R["sens"][s_].values()) for s_ in floor_sets)
mt["key_lift_grid_mm"] = max(v["lift_max"] for (c_, mat_), tab_ in SG.items() if mat_ == "nom" for v in tab_.values())
mt["key_lift_end_mm"] = max(v["lift_max"] for d_ in END_DYN.values() for tab_ in [d_["nom"]] for k_, v in tab_.items() if not k_.startswith("release") and v["v_note"] <= P["v_play"] + 1e-9)
mt["key_lift_end_abuse_mm"] = max(v["lift_max"] for d_ in END_DYN.values() for tab_ in d_.values() for k_, v in tab_.items() if not k_.startswith("release") and v["v_note"] > P["v_play"] + 1e-9)
mt["rep_hz_end_2f_min"] = min(tab_["release_f2"]["rep"] for d_ in END_DYN.values() for tab_ in d_.values())
mt["full_return_end_max_ms"] = max(tab_[k_]["t100"] for d_ in END_DYN.values() for tab_ in d_.values() for k_ in ("release", "release_f2"))
mt["key_lift_chord_abuse_mm"] = max(v["lift_max"] for c in chord_ab for v in chord_ab[c].values())
mt["keeper_gap_min_mm"] = min([dd[c][k]["keep_gap_min"] for c in dd for k in play_keys] + [v["keep_gap_min"] for (c_, mat_), tab_ in SG.items() if mat_ == "nom" for v in tab_.values()] +
                              [v["keep_gap_min"] for d_ in END_DYN.values() for k_, v in d_["nom"].items() if not k_.startswith("release") and v["v_note"] <= P["v_play"] + 1e-9])
mt["keeper_gap_sets_mm"] = min(min(q["keep_play"] for q in R["sens"][s].values()) for s in pass_sets)
mt["keeper_gap_worst_mm"] = min(q["keep_play"] for q in R["sens"]["worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)"].values())
mt["keeper_gap_abuse_mm"] = min(dd[c][k]["keep_gap_min"] for c in dd for k in abuse_keys)
mt["ghost_play_single_max"] = max(dd[c][k]["ghost_frac"] for c in dd for k in dd[c] if k.startswith("play_h"))
mt["ghost_not_dropped"] = len(R["ghost_summary"]["not_dropped"])
mt["ghost_armed"] = len(R["ghost_summary"]["armed"])
mt["ghost_cases"] = R["ghost_summary"]["n"]
mt["ghost_reland_n"] = len(R["ghost_summary"]["relanded"])            # r4.5 circuit 2nd (item 9)
mt["ghost_reland_max_ms"] = R["ghost_summary"]["reland_max"]
mt["ghost_settle_max_ms"] = R["ghost_summary"]["settle_max"]
mt["ghost_creep_max"] = R["ghost_summary"]["creep_max"]
mt["ghost_rep_max_ms"] = P["ghost_rep_max"]
mt["magnet_travel_white_mm"], mt["magnet_travel_black_mm"] = sens["white"]["travel"], sens["black"]["travel"]
mt["min_sensor_gap_mm"] = min(sens["white"]["ff"], sens["black"]["ff"])
mt["min_clearance_mm"] = R["clear"]["min"]
mt["min_clearance_after_tol_mm"] = R["clear"]["min_after_tol"]
mt["cover_top_z_mm"] = g["z_top"]
mt["module_mass_kg"] = module_mass / 1000
mt["steel_kg_88"] = steel_88
mt["metal_kg_88"] = steel_88 + rods_kg
mt["filament_kg"] = total_g / 1000
mt["print_h"] = total_g / 15
mt["base_cost_delta_krw"] = delta
mt["upstop_force_play_n"] = max(up_play)
mt["upstop_force_abuse_n"] = max(up_abuse)
mt["seat_k_min"] = g["seat_k"]
mt["seat_k_chord"] = k_ch
mt["fin_top_play_single_mpa"] = PL["play"]["single"]["fin_top"]
mt["fin_top_play_chord_mpa"] = PL["play"]["chord"]["fin_top"]
mt["fin_top_abuse_chord_mpa"] = PL["abuse_chord20"]["chord"]["fin_top"]
mt["plate_play_single_mpa"] = PL["play"]["single"]["sigma"]
mt["plate_abuse_chord_mpa"] = PL["abuse_chord20"]["chord"]["sigma"]
mt["rod_play_chord_mpa"] = LR["play"]["chord"]["sigma"]
mt["rod_abuse_mpa"] = max(LR["chord20"]["chord"]["sigma"], LR["abuse"]["single"]["sigma"])
mt["beam_play_mpa"], mt["beam_abuse_mpa"] = s_beam_pk, s_beam_ab
mt["tail_play_mpa"] = max(tail_c["white"]["s_play"], tail_c["black"]["s_play"])
mt["tail_abuse_mpa"] = max(tail_c["white"]["s_peak"], tail_c["black"]["s_peak"])
mt["dw_2f_max_g"] = max(R["white"]["DW_2f"], R["black"]["DW_2f"])
mt["uw_bottom_2f_min_g"] = min(R["white"]["UW_bottom_2f"], R["black"]["UW_bottom_2f"])
mt["end_min_after_tol"] = min(v["min"] for v in epc.values()) - m.TOL
R["metrics"] = mt
end_ok = all(v["n_bad"] == 0 for v in epc.values()) and all(v["seam_fixed"][0] >= m.TOL + m.CLEAR_MIN - 1e-9 for v in epc.values()) and \
    all(v["seam_face"][0] >= 0.4 - 1e-6 for v in epc.values())
checks = [
    ("PLAY", "DW 47~55 g (y13, 흑 앞+10), 기본 마찰 (백 / 흑)", 47 <= mt["dw_white_g"] <= 55 and 47 <= mt["dw_black_g"] <= 55,
     "%.1f / %.1f (마찰 2배 %.1f / %.1f, 참고)" % (mt["dw_white_g"], mt["dw_black_g"], R["white"]["DW_2f"], R["black"]["DW_2f"])),
    ("PLAY", "UW 20 g 이상 (쉼·바닥, 마찰 2배 바닥 포함)", min(mt["uw_white_g"], mt["uw_black_g"], mt["uw_bottom_2f_min_g"]) >= 20,
     "%.1f / %.1f (바닥 마찰 2배 최소 %.1f)" % (mt["uw_white_g"], mt["uw_black_g"], mt["uw_bottom_2f_min_g"])),
    ("PLAY", "DW 립 y0 47 g 이상 (백)", R["white"]["DW_lip"] >= 47.0 - 0.05, "%.1f" % R["white"]["DW_lip"]),
    ("PLAY", "연타 13.3 Hz 이상 (1/(2·t50), 50 % 재무장, 1.2 s 정착 뒤 뗌)", min(mt["rep_hz_white"], mt["rep_hz_black"]) >= 13.3,
     "%.1f / %.1f" % (mt["rep_hz_white"], mt["rep_hz_black"])),
    ("PLAY", "연타, 마찰 2배 (비틀림 보조 스프링 기본; 끝 건반 A0·C8 포함)", min(mt["rep_hz_white_2x_friction"], mt["rep_hz_black_2x_friction"], mt["rep_hz_end_2f_min"]) >= 13.3,
     "%.1f / %.1f (끝 건반 최소 %.1f)" % (mt["rep_hz_white_2x_friction"], mt["rep_hz_black_2x_friction"], mt["rep_hz_end_2f_min"])),
    ("PLAY", "끝까지 복귀 60 ms 미만 (마찰 2배, 끝 건반 포함)", max(mt["full_return_white_ms"], mt["full_return_black_ms"], mt["full_return_2f_ms"], mt["full_return_end_max_ms"]) < 60,
     "%.1f / %.1f (마찰 2배 %.1f, 끝 건반 최대 %.1f)" % (mt["full_return_white_ms"], mt["full_return_black_ms"], mt["full_return_2f_ms"], mt["full_return_end_max_ms"])),
    ("PLAY", "노치 들림 0.20 이하 (들림으로만 판정; 0.5~1.5 m/s, 뗌·0.45~2 N, 한 건반·6건반 화음 자리 1.0~1.5 m/s 0.05 간격, 끝 건반, 합격선 재료; 접촉 하한 0.02)",
     max(mt["key_lift_play_mm"], mt["key_lift_play_sets_mm"], mt["key_lift_chord_mm"], mt["key_lift_grid_mm"], mt["key_lift_end_mm"]) <= P["lift_play"],
     "%.3f (재료 조합 %.3f, 화음 자리 %.3f / 합격선 %.3f, 끝 건반 %.3f); 모델 하한 v_floor 0.1 모서리: 한 건반 %.3f, 화음 %.3f (18장); 합격선 밖 최악 %.3f / 화음 %.3f"
     % (max(mt["key_lift_play_mm"], mt["key_lift_grid_mm"]), mt["key_lift_play_sets_mm"], mt["key_lift_chord_nom_mm"], mt["key_lift_chord_pass_mm"], mt["key_lift_end_mm"],
        mt["key_lift_vf01_single_mm"], mt["key_lift_chord_vf01_mm"], mt["key_lift_play_worst_mm"], mt["key_lift_chord_worst_mm"])),
    ("PLAY", "키퍼 무접촉 (합격선 재료, 화음 자리 포함)", min(mt["keeper_gap_min_mm"], mt["keeper_gap_sets_mm"], mt["keeper_chord_min_mm"]) > 0,
     "최소 틈 %.2f (조합 %.2f, 화음 %.2f; v_floor 0.1 화음 %.2f; 합격선 밖 최악 %.2f / 화음 %.2f)" % (mt["keeper_gap_min_mm"], mt["keeper_gap_sets_mm"], mt["keeper_chord_min_mm"],
                                                                          mt["keeper_chord_vf01_mm"], mt["keeper_gap_worst_mm"], mt["keeper_chord_worst_mm"])),
    ("PLAY", "유령: 재무장선 50 %%를 넘는 경우는 모두 펌웨어 거름이 버림 (한 건반·6건반 화음 자리 0.5~1.5 m/s 0.1 간격, 0.45~2 N, 끝 건반, 거름 문턱 0.3 m/s; r4.5 회로 2차: 창 = note-on부터 재무장 %.0f ms, 첫 다시 눌림은 note-on부터 %.0f ms 안, 재무장한 경우는 note-on 뒤 %.0f ms까지 돌림)" % (P["ghost_win"], P["ghost_rep_max"], P["ghost_long"]),
     mt["ghost_not_dropped"] == 0, "한 건반 1.5 m/s 최대 %.0f %%; %d건 중 재무장 %d건 모두 거름 (못 거른 것 %d); 재무장 %d건 중 %.0f ms 안에 다시 닿는 것 %d건%s, 모두 %.0f ms까지 멈춤(뜬 자리 %.0f~%.0f %%, 기어내림 ≤ %.4f m/s)"
     % (100 * mt["ghost_play_single_max"], mt["ghost_cases"], mt["ghost_armed"], mt["ghost_not_dropped"], mt["ghost_armed"], P["ghost_long"], mt["ghost_reland_n"],
        (" (가장 늦게 %.0f ms)" % mt["ghost_reland_max_ms"]) if mt["ghost_reland_n"] else "", mt["ghost_settle_max_ms"], 100 * R["ghost_summary"]["frac_end"][0], 100 * R["ghost_summary"]["frac_end"][1], mt["ghost_creep_max"])),
    ("PLAY", "업스톱 이음 닫힘", True, "이음 없음: 패드 → 패드 바 → 윗판 압축 (나사·예하중 없음)"),
    ("PLAY", "센서 최소 간격 3.0 이상 (2.5 m/s 과다 누름)", mt["min_sensor_gap_mm"] >= 3.0, "%.2f" % mt["min_sensor_gap_mm"]),
    ("PLAY", "모든 틈 ±0.3 공차 뒤 1.0 이상 (모듈, 끝 부속, 이음매)", mt["min_clearance_after_tol_mm"] >= 1.0 - 1e-9 and end_ok,
     "%.2f (끝 부속 %.2f / %.2f, 이음매 너머 고정 부품 %.2f / %.2f; 이음 면 %.2f / %.2f = 모듈 이음과 같은 0.4)" % (mt["min_clearance_after_tol_mm"], epc["left"]["min"] - m.TOL, epc["right"]["min"] - m.TOL,
                                                          epc["left"]["seam_fixed"][0] - m.TOL, epc["right"]["seam_fixed"][0] - m.TOL, epc["left"]["seam_face"][0], epc["right"]["seam_face"][0])),
    ("PLAY", "쉼 상시 응력 2 MPa 미만", mt["max_rest_stress_mpa"] < 2.0, "%.2f MPa" % mt["max_rest_stress_mpa"]),
    ("PLAY", "매 음 층간 응력 5 MPa 미만 (핀-윗판 이음, 한 건반 1.5 m/s)", mt["fin_top_play_single_mpa"] < P["s_cyc"], "%.1f MPa" % mt["fin_top_play_single_mpa"]),
    ("PLAY", "6건반 화음 층간 응력 15 MPa 미만 (드문 하중, r3 기준)", mt["fin_top_play_chord_mpa"] < P["s_rare"], "%.1f MPa (윗판 층 안 %.1f)" % (mt["fin_top_play_chord_mpa"], PL["play"]["chord"]["sigma"])),
    ("PLAY", "숨은 빔·얇은 꼬리 매 음 12 MPa 미만 (층 안: 건반은 윗면이 베드)", max(mt["beam_play_mpa"], mt["tail_play_mpa"]) < P["s_cyc_in"],
     "빔 %.1f, 꼬리 %.1f MPa" % (mt["beam_play_mpa"], mt["tail_play_mpa"])),
    ("PLAY", "레버 봉 SUS304 Ø4: 6건반 화음 응력 < 항복/1.5", mt["rod_play_chord_mpa"] < P["rod_L_yield"] / 1.5, "%.0f MPa (항복 %.0f, 풀림재 최소값)" % (mt["rod_play_chord_mpa"], P["rod_L_yield"])),
    ("ABUSE", "노치 들림 0.40 이하 (빠짐 0.80 / 안전율 2), 모든 재료 조합, 2.0 m/s 6건반 화음 자리 포함",
     max(mt["key_lift_abuse_mm"], mt["key_lift_abuse_sets_mm"], mt["key_lift_chord_abuse_mm"]) <= P["lift_abuse"],
     "%.3f (조합 최대 %.3f, 화음 자리 %.3f)" % (mt["key_lift_abuse_mm"], mt["key_lift_abuse_sets_mm"], mt["key_lift_chord_abuse_mm"])),
    ("ABUSE", "항복 없음: 레버 봉 (2.0 m/s 6건반, 2.5 m/s 한 건반)", mt["rod_abuse_mpa"] < P["rod_L_yield"], "%.0f MPa < %.0f" % (mt["rod_abuse_mpa"], P["rod_L_yield"])),
    ("ABUSE", "피로 10^4회: 층간 15 MPa, 층 안 25 MPa 미만 (2.0 m/s 6건반)", mt["fin_top_abuse_chord_mpa"] < P["s_rare"] and mt["plate_abuse_chord_mpa"] < P["s_rare_in"],
     "핀 이음 %.1f, 윗판 %.1f MPa" % (mt["fin_top_abuse_chord_mpa"], mt["plate_abuse_chord_mpa"])),
    ("ABUSE", "숨은 빔·얇은 꼬리 25 MPa 미만 (층 안, 2.5 m/s)", max(mt["beam_abuse_mpa"], mt["tail_abuse_mpa"]) < P["s_rare_in"],
     "빔 %.1f, 꼬리 %.1f MPa" % (mt["beam_abuse_mpa"], mt["tail_abuse_mpa"])),
    ("ABUSE", "제자리 이탈·조정 풀림 없음", True, "패드 바는 압축, 조정은 인쇄 쐐기·PET 심·캡스턴(벤치)"),
    ("BUILD", "레버를 건반보다 먼저: 모든 레버가 윗판 밑 제자리(레버 봉 선)에 들어감 (2D C-공간, 끝 부속 포함)", all(q["no_keys"]["ok"] for q in ins.values()),
     "%d / %d 도달 (건반을 먼저 넣으면 흑 레버 %s)" % (sum(1 for q in ins.values() if q["no_keys"]["ok"]), len(ins),
                                             "막힘" if not all(ins[n_]["keys_first"]["ok"] for n_ in ("C#", "G#")) else "도달")),
    ("BUILD", "고정 부품끼리 겹침 없음 (따로 출력하는 부품, 모듈·끝 부속; r4.1: 패드 바 ↔ 윗판 2.5 mm²)",
     not R["r42"]["fit_module"] and not any(R["r42"]["fit_end"].values()) and R["r42"]["slide_fit"][0] >= -0.011,
     "모듈 %d, 끝 부속 %d / %d; 패드 바를 넣고 빼는 내내 윗판·레일과 최소 %.2f (접촉 −0.01)" % (len(R["r42"]["fit_module"]), len(R["r42"]["fit_end"]["left"]), len(R["r42"]["fit_end"]["right"]), R["r42"]["slide_fit"][0])),
    ("BUILD", "패드 쐐기·패드 ↔ 윗판 계단·레일 1.3 이상 (패드 바 뒤끝만 계단에 닿음)", min(R["r42"]["gaps_module"]["pad wedge"][0], R["r42"]["gaps_module"]["up-stop pad"][0],
                                                                       *[R["r42"]["gaps_end"][s_]["pad wedge"][0] for s_ in ("left", "right")]) >= 1.3 - 1e-6,
     "쐐기 %.2f, 패드 %.2f (끝 부속 %.2f)" % (R["r42"]["gaps_module"]["pad wedge"][0], R["r42"]["gaps_module"]["up-stop pad"][0], min(R["r42"]["gaps_end"][s_]["pad wedge"][0] for s_ in ("left", "right")))),
    ("BUILD", "비틀림 스프링 조립: 코일이 허브 홈으로 들어가고, 긴 다리가 레버 전 범위에서 홈 안(면까지 0.2 이상), 뒷벽 홈에 아래로 들어감",
     R["r42"]["spring_slot"]["margin"] >= 0.0 and R["r42"]["spring_slot"]["leg_in_groove"],
     "레버 %.1f°~%.1f°에서 여유 %.2f; 다리는 보스 면에 z%.2f(보스 밑 z%.1f 아래)에서 닿고 홈(z%.0f부터)으로 들어감" % (R["r42"]["spring_b_range"][0], R["r42"]["spring_b_range"][1], R["r42"]["spring_slot"]["margin"],
                                                                                   R["r42"]["spring_slot"]["leg_z_at_boss_face"], P["spring_boss"][1], P["spring_groove"][1])),
    # r4.5: the short leg's own groove, the insertion path and the catalogue limits of the MISUMI spring
    ("BUILD", "r4.5 고침 2 짧은 다리 가둠 홈에 넣기: 스프링을 짧은 다리 끝부터 홈을 따라 밀어 넣음 (홈이 0.15 좁게 나와도 틈 ≥ 0; 더 좁으면 0.5 날로 다듬음)",
     R["r45"]["insert"]["clear"] and R["r45"]["insert_lo"][-0.15] >= 0.0,
     "짧은 다리 ↔ 홈 면 %.3f (0.10 / 0.15 좁게: %.3f / %.3f), 코일 ↔ 조각 A %.2f · B %.2f, 긴 다리 ↔ A %.2f · B %.2f" % (R["r45"]["insert"]["short_A"][0], R["r45"]["insert_lo"][-0.1], R["r45"]["insert_lo"][-0.15],
                                                                                   R["r45"]["insert"]["per"]["coil|A"][0], R["r45"]["insert"]["per"]["coil|B"][0], R["r45"]["insert"]["per"]["long leg|A"][0], R["r45"]["insert"]["per"]["long leg|B"][0])),
    ("PLAY", "r4.5 고침 2 코일 뜸(검증 major): 짧은 다리를 가둬 코일이 봉에 닿지 않음 — 쉼 토크 설계값, 봉 마찰 이력 0, 홈이 +0.3 넓게 나와도 봉과 틈 > 0",
     abs(R["spring"]["float"][[k_ for k_ in R["spring"]["float"] if k_.startswith("r4.5 fix 2")][0]]["T_rest"] - P["spring_T0"]) < 0.01 and R["spring"]["capture"]["gap_hand"] > 0 and R["spring"]["capture_tol"]["+0.30"]["gap_left"] > 0,
     "쉼 %.2f N·mm (r4.5 한 면 받침이면 코일이 봉으로 %.2f 밀려 %.2f), 봉과 틈 쉼 %.2f · 바닥 %.2f · 손 25° %.2f, 홈 +0.3이면 쉼 %.2f N·mm·틈 %.2f; 짝 힘 %.2f N" % (
         P["spring_T0"], R["spring"]["float"]["r4.5 as built (short leg 2.5 on one face), mu 0.0"]["shift"], R["spring"]["float"]["r4.5 as built (short leg 2.5 on one face), mu 0.0"]["T_rest"],
         R["spring"]["capture"]["gap_rest"], R["spring"]["capture"]["gap_bottom"], R["spring"]["capture"]["gap_hand"], R["spring"]["capture_tol"]["+0.30"]["T0"], R["spring"]["capture_tol"]["+0.30"]["gap_left"], R["spring"]["capture"]["F_couple_rest"])),
    ("BUILD", "r4.5 고침 2 건반 뺀 레버의 긴 다리: 뒷벽 홈·보스를 다리 x(+%.1f)에 맞춤 — 코일 축 놀음 + 레버 놀음을 더해도 홈 입구(모따기 포함)가 다리를 받음" % P["spring_groove_dx"],
     R["assembly"]["keyless_x"]["margin"] >= 0.0,
     "다리 x 어긋남 최대 %.2f (코일 %.2f + 레버 %.2f) ≤ 받는 폭 %.2f: 여유 %.2f (레버 중심 홈이면 %.2f)" % (R["assembly"]["keyless_x"]["x_off"], R["assembly"]["keyless_x"]["coil_axial"], R["assembly"]["keyless_x"]["lever_float"],
                                                                              R["assembly"]["keyless_x"]["catch"], R["assembly"]["keyless_x"]["margin"], R["assembly"]["keyless_x"]["margin_r45"])),
    ("BUILD", "r4.5 스프링 카탈로그 한계: 손 들기(레버 25°) 감김각 ≤ 최대 사용각 %.0f°" % P["spring_cat"]["max_deg"],
     R["spring"]["states"]["hand 25 deg"]["wound"] <= P["spring_cat"]["max_deg"],
     "감김 %.1f°, 토크 %.2f N·mm = 카탈로그 55° 토크 %.2f의 %.0f %% (18장 위험), 응력 %.0f MPa (Su %.0f %%)" % (R["spring"]["states"]["hand 25 deg"]["wound"], R["spring"]["states"]["hand 25 deg"]["T"], R["spring"]["cat"]["T_max"],
                                                                                   100 * R["spring"]["hand_over_cat"], R["spring"]["states"]["hand 25 deg"]["sigma"], 100 * R["spring"]["states"]["hand 25 deg"]["sigma"] / 2150)),
    ("ABUSE", "r4.5 고침 2 허브·웹 (가둠 홈 자리): 층 안 < %.0f MPa (홈 모서리 Kt %.0f 포함), 매 음 PLAY < %.0f MPa" % (P["s_rare_in"], R["r45"]["hub"]["abuse"]["Kt"], P["s_cyc_in"]),
     R["r45"]["hub"]["abuse"]["section"]["sigma_kt"] < P["s_rare_in"] and R["r45"]["hub"]["play"]["section"]["sigma_kt"] < P["s_cyc_in"],
     "ABUSE %.2f MPa (홈 없던 단면 %.2f), PLAY %.2f MPa; 다리 두 닿는 점 %.2f N (손 25°), 봉 지압 %.2f MPa" % (R["r45"]["hub"]["abuse"]["section"]["sigma_kt"], R["r45"]["hub"]["abuse"]["section"]["sigma_full"], R["r45"]["hub"]["play"]["section"]["sigma_kt"],
                                                                     R["r45"]["hub"]["abuse"]["F_couple"], R["r45"]["hub"]["abuse"]["hub_bearing"])),
    ("BUILD", "패드 바 빼기 (앞부분이 나온 %.1f mm부터 윗판에 밀어 올림): 공칭 1.3 이상, PET 심 3장 1.0 이상" % P["bar_raise_pull"],
     min(q["pressed"][0] for q in slide.values()) >= 1.3 - 1e-6 and min(q["pressed_3shims"][0] for k_, q in slide.items() if "pressed_3shims" in q) >= 1.0,
     "공칭 %.2f, 심 3장 %.2f (곧게만 당기면 끝 0.5 mm에서 %.2f)" % (min(q["pressed"][0] for q in slide.values()), min(q["pressed_3shims"][0] for k_, q in slide.items() if "pressed_3shims" in q),
                                                     min(q["straight"][0] for k_, q in slide.items() if "straight" in q))),
]
R43 = R["r43"]
SLq = R["sens"][LAND_LAB]
land_rep2 = min(500.0 / DYN[LAND_LAB][c_]["release_f2"]["t50"] for c_ in ("white", "black"))
land_t2 = max(DYN[LAND_LAB][c_]["release_f2"]["t100"] for c_ in ("white", "black"))
checks += [
    ("PLAY", "r4.3 쉼 펠트가 USB 홈 옆에 %.0f %%만 앉을 때 (F#, 두 색에 적용): 연타 13.3 Hz 이상(마찰 2배 포함), 복귀 60 ms 미만, 들림 0.20 이하, 키퍼 무접촉" % (100 * LAND_MIN),
     min(SLq["white"]["rep"], SLq["black"]["rep"], land_rep2) >= 13.3 and max(SLq["white"]["t100"], SLq["black"]["t100"], land_t2) < 60 and
     max(SLq["white"]["lift_play"], SLq["black"]["lift_play"]) <= P["lift_play"] and min(SLq["white"]["keep_play"], SLq["black"]["keep_play"]) > 0,
     "연타 %.1f / %.1f Hz (마찰 2배 최소 %.1f), 복귀 %.1f / %.1f ms (마찰 2배 최대 %.1f), 들림 %.3f / %.3f, 키퍼 %.2f / %.2f"
     % (SLq["white"]["rep"], SLq["black"]["rep"], land_rep2, SLq["white"]["t100"], SLq["black"]["t100"], land_t2, SLq["white"]["lift_play"], SLq["black"]["lift_play"],
        SLq["white"]["keep_play"], SLq["black"]["keep_play"])),
    ("BUILD", "r4.3 USB-C 플러그(RP2040-Zero 핀 헤더 위, z%.1f~%.1f) ↔ 뒤 선반·리브·핀·뒷벽 1.3 이상" % tuple(P["usb_z"]), R43["usb"]["min"][0] >= 1.3 - 1e-6,
     "최소 %.2f (%s); 선반 홈 x%.2f~%.2f, 리브 %.2f, 핀 %.2f, 뒷벽 개구 %.2f" % (R43["usb"]["min"][0], R43["usb"]["min"][1], R43["usb"]["slot"][0], R43["usb"]["slot"][1],
                                                               R43["usb"]["each"]["shelf rib"], R43["usb"]["each"]["fin"], R43["usb"]["each"]["rear wall"])),
    ("BUILD", "r4.3 제어 기판 부품(BRD-01)·부품 한계 ↔ 출력 프레임 1.3 이상, 리본(16심) 차선 양옆 1.3 이상",
     min(v_[0] for v_ in R43["board_vs_frame"].values()) >= 1.3 - 1e-6 and min(R43["ribbon"]["left"], R43["ribbon"]["right"]) >= 1.3 - 1e-6,
     "최소 %.2f (%s ↔ %s); 핀 발 ↔ 제로 앞 모서리 %.2f; 리본 %.2f / %.2f" % (min(v_[0] for v_ in R43["board_vs_frame"].values()),
                                                         min(R43["board_vs_frame"], key=lambda k_: R43["board_vs_frame"][k_][0]).replace("board part: ", ""),
                                                         min(R43["board_vs_frame"].values(), key=lambda v_: v_[0])[1], R43["fin"]["zero_gap"], R43["ribbon"]["left"], R43["ribbon"]["right"])),
]
RT_ = R["steel_retention"]["peaks"]
LS_ = {k_: v_ for k_, v_ in LSUM.items() if k_[0] == "r44"}
land_play_ok = all(v_["lift_play"] <= P["lift_play"] and v_["keep_play"] > 0 and v_["ghost_not_dropped"] == 0 and v_["rep_2f"] >= 13.3 and v_["t100_2f"] < 60
                   for k_, v_ in LS_.items() if k_[2] in ("nom", "passline"))
land_ab_ok = all(v_["lift_abuse"] <= P["lift_abuse"] for v_ in LS_.values())
CLr = R["clear"]
checks += [
    ("PLAY", "r4.4 윗 스냅 립 ↔ 패드·패드 바·레일 1.3 이상 (립을 geometry·스윕에 넣음; r4.3 립 y150~168은 %.2f)" % CLr["lip43"]["d"], CLr["lip44"]["min"] >= 1.3 - 1e-6,
     "최소 %.2f (패드 %.2f, 패드 바·레일 %.2f); r4.3 립은 1 N 바닥에서 패드 옆 %.2f (공차 뒤 %.2f)" % (CLr["lip44"]["min"], CLr["lip44"]["pad"], CLr["lip44"]["rail"], CLr["lip43"]["d"], CLr["lip43"]["d"] - m.TOL)),
    ("PLAY", "r4.4 강철 블록 유지 (고침 2b: MS 폴리머 탄성 접착, 접착층 한쪽 %.2f): 캐리어 → 강철 힘·모멘트의 전단 + 열팽창 차이 전단(매 음 ΔT %.0f K, 드문 %.0f K, 가장 얇은 접착층 %.2f) — 매 음 %.3f, 드문 %.3f MPa 이하 (설계 %.1f MPa / %.0f·%.0f); 스냅 립만으로는 안 됨(18장)" % (
        P["bond_t"], P["bond_dT"][0], P["bond_dT"][1], P["bond_t_min"], P["bond_tau"] / P["bond_sf_play"], P["bond_tau"] / P["bond_sf_rare"], P["bond_tau"], P["bond_sf_play"], P["bond_sf_rare"]),
     R["steel_retention"]["bond"]["play"]["tau"] <= R["steel_retention"]["bond"]["play"]["limit"] and all(R["steel_retention"]["bond"][k_]["tau"] <= R["steel_retention"]["bond"][k_]["limit"] for k_ in ("chord", "abuse")),
     "전단(하중 + 열) 매 음 %.3f + %.3f, 화음 %.3f + %.3f, ABUSE %.3f + %.3f MPa (면적 %.0f mm²; 5분 에폭시면 열만 %.2f MPa), 충격 %.0f g까지; 접착 없이 스냅만: 아래 립 뿌리 층간 %.1f MPa(한계 5), 옆벽 립 뿌리 층 안 %.1f MPa(한계 12), 립 선이 %.2f 벌어짐(물림 1.0)" % (
         R["steel_retention"]["bond"]["play"]["tau_mech"], R["steel_retention"]["bond"]["play"]["tau_th"], R["steel_retention"]["bond"]["chord"]["tau_mech"], R["steel_retention"]["bond"]["chord"]["tau_th"],
         R["steel_retention"]["bond"]["abuse"]["tau_mech"], R["steel_retention"]["bond"]["abuse"]["tau_th"], R["steel_retention"]["bond_geo"]["area"], R["steel_retention"]["bond"]["play"]["epoxy_th"],
         R["steel_retention"]["bond_shock_g"], RT_["play"]["sig_bottom"], R["steel_retention"]["wall_plate"]["play_a0.50_pinned"]["s_root"],
         R["steel_retention"]["wall_plate"]["play_a0.50_clamped"]["spread_max"])),
    ("PLAY", "r4.4 F·F# 쉼 펠트 착지(r4.4 펠트) 6건반 화음 자리: 들림 0.20 이하, 키퍼 무접촉, 유령 모두 거름, 연타 13.3 Hz 이상·복귀 60 ms 미만(마찰 2배)",
     land_play_ok, "; ".join("%s %.0f %%: 들림 %.3f 키퍼 %.2f 연타 %.1f Hz 복귀 %.1f ms" % (nm_, 100 * RLAND[nm_]["frac"], max(LS_[("r44", nm_, mt_)]["lift_play"] for mt_ in ("nom", "passline")),
                                                                         min(LS_[("r44", nm_, mt_)]["keep_play"] for mt_ in ("nom", "passline")), min(LS_[("r44", nm_, mt_)]["rep_2f"] for mt_ in ("nom", "passline")),
                                                                         max(LS_[("r44", nm_, mt_)]["t100_2f"] for mt_ in ("nom", "passline"))) for nm_ in ("F", "F#"))),
    ("ABUSE", "r4.4 F·F# 착지 ABUSE (2.5 m/s 한 건반·화음 자리, 2.0 m/s 화음): 들림 0.40 이하, ABUSE 복귀 넘침 자세에서 닿지 않음", land_ab_ok and CLr["over_brief"]["d"] - m.TOL > 0,
     "들림 최대 %.3f; ABUSE 복귀 넘침 최소 틈 %.2f (공차 뒤 %.2f)" % (max(v_["lift_abuse"] for v_ in LS_.values()), CLr["over_brief"]["d"], CLr["over_brief"]["d"] - m.TOL)),
    ("BUILD", "r4.4 레버 봉·핀 보스 구멍·봉 마개를 geometry·스윕에 넣음 (마개는 끝 핀 면과 같은 면, 축 놀음 > 0)",
     rodck["plug_face_to_fin_face"] >= -1e-9 and rodck["play_left"] + rodck["play_right"] - rodck["rod_len_tol"] > 0,
     "마개 x%.1f~%.1f, 막힌 끝 x%.1f; 축 놀음 %.2f~%.2f; 가장 가까운 움직이는 부품 %.2f" % (rodck["plug"][0], rodck["plug"][1], rodck["blind_end"],
                                                                rodck["play_left"] + rodck["play_right"] - rodck["rod_len_tol"], rodck["play_left"] + rodck["play_right"] + rodck["rod_len_tol"],
                                                                rodck["sweep_min"][0] if rodck["sweep_min"] else -1)),
]
C4_ = R["c44"]
# r4.4 fix 2b rows (verifier critical / majors)
BI_ = R["board_insert"]
KE_ = {lab_: R["plate"][lab_]["chord" if lab_ != "abuse" else "single"] for lab_ in ("play", "abuse_chord20", "abuse")}
KE1_ = R["plate"]["play"]["single"]
checks += [
    ("BUILD", "r4.4 고침 2b 제어 기판 넣기: 한 덩어리 프레임에 기판이 들어갈 길 — 바닥 구멍으로 밑에서 곧게 올림(기판 홈이 F|F# 핀 발·킬을 따라감), 길 위 고정 부품과 평면 틈 > 0, 걸리는 것은 매단 보스(자리)뿐",
     BI_["min"] > 0 and all(abs(z_) < 1e-6 or z_ > 0 for z_, a_, b_ in BI_["stops"]),
     "길 위 최소 %.2f (%s ↔ %s); 바닥 구멍 x%.2f~%.2f y%.1f~%.1f(리셉터클 뒤 x%.2f~%.2f는 y%.1f까지); 멈춤 = 기판 위 매단 보스 4개(z%.1f에 닿음), 위치 핀 반경 놀음 %.2f; r4.4 고침 2까지는 길이 없었음(핀 발이 바닥~윗판, 기판 뒤 여유 1.3)"
     % ((BI_["min"], BI_["pair"][0].replace("control board", "기판").replace("board part: ", "")[:30], BI_["pair"][1][:30]) + BI_["hatch"] + BI_["notch"] + (P["board_z"][1], BI_["pin_play"]))),
    ("PLAY", "r4.4 고침 2b F|F# 핀 발 킬(밸런스 레일 뒷면까지, 바닥 대신): 화음 자리 강성 %.0f N/mm 이상(단계 0 합격선), 킬 굽힘 층 안 매 음 %.0f / 드문 %.0f MPa, 전단 층간 기준 매 음 %.0f / 드문 %.0f MPa" % (P["seat_k_chord_req"], P["s_cyc_in"], P["s_rare_in"], P["s_cyc"], P["s_rare"]),
     k_ch >= P["seat_k_chord_req"] and KE1_.get("keel_sigma", 0) < P["s_cyc_in"] and KE1_.get("keel_tau", 0) < P["s_cyc"] and max(q_.get("keel_sigma", 0) for q_ in KE_.values()) < P["s_rare_in"] and max(q_.get("keel_tau", 0) for q_ in KE_.values()) < P["s_rare"],
     "화음 자리 %.0f N/mm (r4.5 고침 2: 레일 + 바닥 띠를 핀 선 사이 보로; 킬 z%.1f + F|F# 핀 앞끝 y%.1f; 레일 고정이면 %.0f, r4.4 킬 z18·앞끝 y152면 %.0f, 첫 시도 킬 z21은 건반 F에 %.2f); 킬 한 건반 PLAY %.2f MPa (전단 %.2f), 6건반 화음 PLAY %.2f (%.2f), ABUSE 화음 2.0 m/s %.2f (%.2f) MPa" % (
         k_ch, P["fin_keel"][2], m.keel_front(P), R["keel_rail"]["k_chord_rigid"], R["keel_rail"]["k_chord_keel18"], (R["keel_rail"].get("keel21_clear") or {}).get("d", -1.0), KE1_.get("keel_sigma", 0), KE1_.get("keel_tau", 0), KE_["play"].get("keel_sigma", 0), KE_["play"].get("keel_tau", 0), KE_["abuse_chord20"].get("keel_sigma", 0), KE_["abuse_chord20"].get("keel_tau", 0))),
    ("BUILD", "r4.5 고침 2 첫 모듈 정하중 확인(단계 0): 6패드 × 60 N에서 E·F 패드 자리 처짐 ≤ 60 / %.0f = %.2f mm (모델)" % (P["seat_k_chord_req"], 60.0 / P["seat_k_chord_req"]),
     R["keel_rail"]["dead"]["EF_max"] is not None and R["keel_rail"]["dead"]["EF_max"] <= 60.0 / P["seat_k_chord_req"],
     "모델 E·F 최대 %.3f mm (%s 화음), 가장 무른 자리 %.0f N/mm" % (R["keel_rail"]["dead"]["EF_max"] or -1, "-".join(R["keel_rail"]["dead"]["keys"]), R["keel_rail"]["dead"]["k_eq"])),
]
# r4.4 resume: the bought screw is the v3.2 L35 button head D5.7 (circuit delta 14 assumed D5.5): its head may pass the
# board edge by 0.1 - the check is the board ring around the D3.2 hole (>= 1.0) plus the head clearances; pins stay inside
so_ok = all(q_["rail_top"] >= 1.3 - 1e-6 and q_["rib_top"] >= 1.3 - 1e-6 and q_["part_min"][0] >= 1.3 - 1e-6 and
            (q_["edge_ring"] >= 1.0 - 1e-6 if q_["kind"] == "screw" else q_["in_board"] >= -1e-6) for q_ in C4_["standoffs"])
end_ok = all(min(q_["pad_margins"] + q_["wire_margins"]) >= 1.3 - 1e-6 and min(q_["board_in_bar"]) >= -1e-6 and (q_["tab_gap"] is None or q_["tab_gap"] >= 1.3 - 1e-6)
             and q_["path_min"][0] >= 1.3 - 1e-6 for q_ in C4_["ends"].values())
checks += [
    ("BUILD", "r4.4 회로 대조: 스탠드오프 M3 머리(L35 Ø%.1f)·핀 ↔ 레일·리브 1.3, 핀은 기판 안·나사 구멍 둘레 기판 1.0 이상; 리본(차선·기판 밑·SB 리브 틈) 양옆 1.3; 플러그 y%.1f~%.1f ↔ 선반 홈·뒷벽 개구 1.3; "
     "끝 부속 리드 패드·선 ↔ 리브 틈 1.3, 리드 길(모음 포함) ↔ 바닥 부품 1.3, 기판이 센서 바 안" % ((P["board_screw"][0],) + tuple(C4_["usb"]["y"])),
     so_ok and end_ok and min(C4_["ribbon"]["lane_margins"] + C4_["ribbon"]["sb_gap_margins"]) >= 1.3 - 1e-6 and C4_["ribbon"]["to_fin"] >= 1.3 and
     min(C4_["usb"]["slot_margins"]) >= 1.3 - 1e-6 and C4_["usb"]["wall_z_margin"] >= 1.3 and min(C4_["usb"]["wall_x_margins"]) >= 1.3 and ff["board_parts_min"][0] >= 1.3 - 1e-6,
     "머리 ↔ 레일 %.2f, ↔ 리브 %.2f (축 위 %.2f), 구멍 둘레 기판 %.2f (머리는 모서리 밖 %.2f); 리본 %.2f / %.2f (SB 리브 틈 %.2f / %.2f, 기판 밑 ↔ 핀 발 %.2f); 플러그 홈 %.2f, 뒷벽 개구 %.2f; "
     "리드 틈 최소 %.2f, 리드 길 ↔ 바닥 부품 %.2f (A#0 탭 받침 %.2f); 기판 부품 ↔ 프레임 %.2f"
     % (min(q_["rail_top"] for q_ in C4_["standoffs"] if q_["kind"] == "screw"), min(q_["rib_top"] for q_ in C4_["standoffs"] if q_["kind"] == "screw"),
        min(q_["rib_top_axis"] for q_ in C4_["standoffs"] if q_["kind"] == "screw" and q_["rib_top_axis"] is not None),
        min(q_["edge_ring"] for q_ in C4_["standoffs"] if q_["kind"] == "screw"), max(0.0, -min(q_["in_board"] for q_ in C4_["standoffs"] if q_["kind"] == "screw")),
        C4_["ribbon"]["lane_margins"][0], C4_["ribbon"]["lane_margins"][1], C4_["ribbon"]["sb_gap_margins"][0], C4_["ribbon"]["sb_gap_margins"][1], C4_["ribbon"]["to_fin"],
        min(C4_["usb"]["slot_margins"]), C4_["usb"]["wall_z_margin"], min(min(q_["pad_margins"] + q_["wire_margins"]) for q_ in C4_["ends"].values()),
        min(q_["path_min"][0] for q_ in C4_["ends"].values()), min(q_["fan_tab"] for q_ in C4_["ends"].values() if q_["fan_tab"] is not None), ff["board_parts_min"][0])),
]
CLf2 = R["clear"]
_ffx = [q_ for q_ in S if q_["cls"] == "lever-fixed" and q_["b"] == "fin"]
_ll = [q_ for q_ in S if q_["cls"] == "lever-lever"]
_bp = [q_ for q_ in S if q_["cls"] == "lever-fixed" and q_["b"].startswith(("up-stop pad", "pad bar", "pad wedge"))]
_br = [q_ for q_ in S if q_["cls"] == "key-fixed" and q_["b"].startswith("balance rail") and q_["part_a"] == "balance block"]
checks += [
    ("PLAY", "r4.4 고침 2: 스윕에 레버 축 놀음(칼라·보스 사슬, 한쪽)·패드 바 옆 놀음 ±%.1f·건반 노치가 봉에 앉음/파고듦(쉼·1 N 바닥 평면 상태, ff·복귀 넘침 동역학 최저) — 모든 쌍 1.3 이상" % P["pad_bar_clear"],
     nbad == 0 and min(q_["d"] for q_ in _ffx + _ll + _bp + _br) >= 1.3 - 1e-6 and lip_pad >= 1.3 - 1e-6,
     "레버 ↔ 레버 %.2f, 레버 ↔ 핀 %.2f, 레버 ↔ 패드 바·패드·쐐기 %.2f, 옆벽 ↔ 자기 패드 %.2f (고침 1 옆벽이면 %.2f), 흑 블록 ↔ 밸런스 레일 %.2f (포켓 %s)" % (
         min(q_["d"] for q_ in _ll), min(q_["d"] for q_ in _ffx), min(q_["d"] for q_ in _bp), lip_pad, lip_pad_flat, min(q_["d"] for q_ in _br),
         "; ".join("%s z%.2f y%.1f~" % (("흑" if c_ == "black" else "백"), q_["z"], q_["y"]) for c_, q_ in RPOCK.items() if q_) or "없음")),
]
R["r44"] = dict(land=RLAND, land43=RLAND43, land_sum={"%s_%s_%s" % k_: v_ for k_, v_ in LSUM.items()}, over_r43=over_r43,
                over_key={k_: (D(v_[0]), D(v_[1])) for k_, v_ in g["over_key"].items()}, over_key_r43={k_: (D(v_[0]), D(v_[1])) for k_, v_ in _own_over("r43").items()},
                over_key_brief={k_: (D(v_[0]), D(v_[1])) for k_, v_ in _own_over("r44", "_brief").items()}, k_ch=k_ch, k_ch_ab=k_ch_ab,
                over_key_f2={k_: (D(v_[0]), D(v_[1])) for k_, v_ in _own_over("r44", worst=False).items()})
for grp, c, ok, v in checks:
    pr("  [%s] %-6s %-70s %s" % ("OK " if ok else "NO ", grp, c, v))
R["checks"] = [dict(group=grp, check=c, ok=bool(ok), value=v) for grp, c, ok, v in checks]

# ----------------------------------------------------------------------------------------------- O simplification r3 -> r4
sec("O. SIMPLIFICATION r3 -> r4 (per module unless noted)")
r3m = json.load(open(os.path.join(OUT, "..", "final_r3", "metrics.json")))
r3 = dict(module_kg=r3m["metrics"]["module_mass_kg"], cover=r3m["metrics"]["cover_top_z_mm"], heads=r3m["metrics"]["heads_top_z_mm"],
          cost=r3m["metrics"]["cost_delta_krw"], filament=r3m["metrics"]["filament_kg"], print_h=r3m["metrics"]["print_h"], metal=r3m["metrics"]["metal_kg_88"],
          meff_w=r3m["metrics"]["m_eff_white_g"], meff_b=r3m["metrics"]["m_eff_black_g"], steel_block=r3m["mass"]["steel_block_g"])
r3_printed = dict(keys=12, carriers=12, frame=1, cover=1, sensor_bar=1, c_rings=8, pad_holders=12, black_spacers=5, spring_seats=12, service_blocks=12)
r3_bought = dict(steel_blocks=12, rail=1, tapped_strips=4, key_rod=1, lever_rod=1, brass_bushings=5, balance_pins=12, locating_pins=2, cover_magnets=2,
                 capstans=12, capstan_nuts=12, thumb_screws=8, disc_springs=72, sensor_magnets=12, lead=5, pads=12)
r4_printed = dict(keys=12, carriers=12, frame=1, pad_bars=4, curtain_strip=1, sensor_bar=1, rod_plug=1)
r4_bought = dict(steel_blocks=12, key_rod=1, lever_rod=1, balance_pins=12, capstans=12, capstan_nuts=12, torsion_springs=12, sensor_magnets=12, pads=12,
                 board_screws=2)       # r4.4 (circuit cross-check 3): the 2 control-board M3x6 screws (v3.2 L35, not listed before)
n3p, n3b, n4p, n4b = sum(r3_printed.values()), sum(r3_bought.values()), sum(r4_printed.values()), sum(r4_bought.values())
pr("pieces per module: printed %d -> %d, bought %d -> %d, total %d -> %d (tools per instrument: r3 D30 driver + removal hook + M3 tap + D3 H7 reamer -> r4 D4.0 drill + 2.0 hex key + printed bench jig / capstan gauge / pin gauge)"
   % (n3p, n4p, n3b, n4b, n3p + n3b, n4p + n4b))
pr("module mass %.2f -> %.2f kg; top of the module z%.1f (heads z%.1f) -> z%.2f, nothing above; base cost delta %+d -> %+d KRW; filament %.2f -> %.2f kg, %.0f -> %.0f h; metal %.2f -> %.2f kg"
   % (r3["module_kg"], module_mass / 1000, r3["cover"], r3["heads"], g["z_top"], r3["cost"], delta, r3["filament"], total_g / 1000, r3["print_h"], total_g / 15, r3["metal"], steel_88 + rods_kg))
R["simplify"] = dict(r3=r3, r3_printed=r3_printed, r3_bought=r3_bought, r4_printed=r4_printed, r4_bought=r4_bought, n=(n3p, n3b, n4p, n4b))
mt["parts_per_module_printed"], mt["parts_per_module_bought"] = n4p, n4b

# ----------------------------------------------------------------------------------------------- P parts list
n_w_88, n_b_88 = 7 * 7 + 3, 7 * 5 + 1
# r4.1 (verifier geometry minor): every hub-collar pair is position-specific -> list the carrier variants; lever-rod lengths of the end parts
carrier_variants = {}
for nm_ in m.ORDER:
    carrier_variants[nm_] = g["collars"][nm_]
for side_ in ("left", "right"):
    for nm_ in ep[side_]["order"]:
        carrier_variants[nm_] = ep[side_]["collars"][nm_]
rodL_end = {s_: (ep[s_]["lay"]["fins"][-1][0] + 0.2) - (ep[s_]["lay"]["fins"][0][1] - 0.3) for s_ in ("left", "right")}
pr("carrier variants (left / right collar): " + ", ".join("%s %.2f/%.2f" % (k_, v_[0], v_[1]) for k_, v_ in carrier_variants.items()) +
   " -> %d kinds; pad bars: 4 module bays + 2 end parts = 6 kinds; lever rods: module %.1f, left end %.1f, right end %.1f"
   % (len(set(carrier_variants.values())), P["rod_L_x"][1] - P["rod_L_x"][0], rodL_end["left"], rodL_end["right"]))
R["variants"] = dict(carriers=carrier_variants, n_carriers=len(set(carrier_variants.values())), n_pad_bars=6, rodL_end=rodL_end)
spare_w, spare_b = 7 + 3, 5 + 1
# r4.2 (drafter): the pad lies along its face (11.33 / 9.61 deg), so its cut length is the face length, not the y span
R["pad_cut_len"] = math.floor(max((P["pad_y"][1] - P["pad_y"][0]) / math.cos(math.radians(R["heights"]["held_b_w"])),
                                  (P["pad_y"][1] - P["pad_y"][0]) / math.cos(math.radians(R["heights"]["held_b_b"]))) * 10 + 0.5) / 10
kw_mean_w = sum(kw[n] for n in m.ORDER if not keys[n]["black"]) / 7
_TLP = json.load(open(os.path.join(OUT, "tools", "tools_geometry.json")))["print"]
from export_geo import pf as _pf          # r4.4 fix 2: the one rounding rule for the parts-list text (collar lengths)
parts = [
    dict(name="백건 C·D·E·F·G·A·B (+ 끝 A0·B0·C8)", kind="출력", spec="PETG, 7종 + 끝 3종, 윗면을 베드에, 스냅 노치 R2.55 + 천 0.5T, 밸런스 핀 홈 y%.1f~%.1f" % P["slot_y"],   # r4.4 parts (no F foot)
         per_module=7, total=n_w_88 + spare_w, note="88건반 %d + 예비 %d" % (n_w_88, spare_w), unit_g=round(kw_mean_w, 2)),
    dict(name="흑건 (4종: C#·D#은 같음, + 끝 A#0)", kind="출력", spec="PETG, 납·추 칸 없음, 가이드 탭 %.1f" % P["tab_w_b"],
         per_module=5, total=n_b_88 + spare_b, note="88건반 %d + 예비 %d" % (n_b_88, spare_b), unit_g=round(kw["C#"], 2)),
    dict(name="레버 캐리어 (위치 %d곳, 칼라 %d종)" % (len(carrier_variants), len(set(carrier_variants.values()))), kind="출력", spec="PETG, 폭 %.1f, 허브 Ø3.9→Ø4.0 드릴, 허브 칼라 일체(왼/오 길이가 위치마다 다름: %s), 스프링 주머니 Ø%.1f×%.1f + 긴 다리 창(%.0f° 방향, 축에서 +%.1f까지 열림) + 짧은 다리 가둠 홈(r4.5 고침 2: 폭 %.2f, 주머니에서 허브 벽을 지나 웹 안 막힌 끝까지, 웹 밑면을 %.1f 깎음; 넣는 슬롯은 다리를 따라 %.0f°), 손톱 턱(R3 모서리를 채움), 윗 스냅 립 %.1f×%.1f는 y%s에만(옆벽 윗단 z%.1f도 그 구간만), 옆벽에 음 이름 새김"
         % ((P["lever_w"], "; ".join(_pf("%s %.2f/%.2f", (k_, v_[0], v_[1])) for k_, v_ in carrier_variants.items())) + P["spring_pocket"] + (P["spring_window"][0], P["spring_window"][1], P["spring_d"] + P["spring_notch"][0], R["r45"]["notch"]["web_cut_depth"], P["spring_slot"][0])
            + (P["lip_over"], P["lip"], "·".join("%.0f~%.0f" % q_ for q_ in P["lip_segs"]), P["z_st"] + P["lip"])),
         per_module=12, total=88, note="예비 없음: 위치별 파일로 필요할 때 출력 (20분)", unit_g=round(lv_p, 2)),
    dict(name="프레임 (모듈)", kind="출력", spec="PETG, 윗판 z%.2f(패드 바 L 레일 8: 웹 %.1f + 립 %.1f×%.1f), 핀 5·보스(F|F# 핀 발 y%.1f~%.1f는 기판 홈을 지나 킬로 밸런스 레일 뒷면에 붙음, 그 뒤 z%.1f부터 매달림), 기판 밑 바닥 구멍 x%.2f~%.2f y%.1f~%.1f(제어 기판을 밑에서 넣음), 제어 기판 보스 4 기판 위에 매달림(앞 2 레일, 뒤 2 리브), 밸런스 레일(리본 차선 x%.0f~%.0f), 뒤 선반·리브(USB 플러그 위 홈 x%.2f~%.2f), 뒷벽(USB 개구 x%.0f~%.0f z%.0f~%.0f, 스프링 홈 보스 12(폭 %.1f, 레버 x +%.1f 중심 = 긴 다리 자리), 홈 %.1f×%.1f z%.0f~%.0f 밑이 열림, 입구 모따기 %.1f)"
         % ((g["z_top"], P["bar_rail"][0], P["rail_lip"], P["rail_lip_t"], m.keel_front(P), P["fin_slot_y"][1], P["comp_zmax"] + 1.5) + tuple(P["board_hatch"]) + (P["ribbon_x"][0], P["ribbon_x"][1],
             m.usb_slot(P)[0], m.usb_slot(P)[1]) + tuple(P["usb_wall_open"]) + (P["spring_boss"][0], P["spring_groove_dx"], P["spring_groove"][3], P["spring_groove"][4], P["spring_groove"][1], P["spring_groove"][2], P["spring_lead_in"]))
         + (", 센서 기판 받침(기둥 x%.1f~%.1f·앞뒤 리브 윗면 z%.1f)과 센서 바 오른쪽 턱 2(v3 P112, r4.5 회로 2차: 립 x%.1f~%.1f z%.1f~%.1f, 기둥 x%.1f~%.1f)"
            % (P["sb_post"][0], P["sb_post"][1], P["sb_board"][4], P["sb_ledge"][0], P["sb_ledge"][1], P["sb_ledge"][3], P["sb_ledge"][4], P["sb_ledge"][1], P["sb_ledge"][2])),
         per_module=1, total=7, note="서포트 %.0f g 별도" % sup_plate, unit_g=round(frame_g, 1)),
    dict(name="끝 부속 프레임 (왼쪽 A0~B0, 오른쪽 C8)", kind="출력", spec="같은 단면 + 볼(cheek), 이음 핀 보스 한쪽, 도브테일 (왼쪽 수, 오른쪽 암), 스프링 홈 보스 (왼쪽 3, 오른쪽 1), 패드 바 L 레일 2",
         per_module=0, total=2, note="왼쪽 1 + 오른쪽 1", unit_g=round(frame_g * 47.0 / 164.5 * 1.15, 1)),
    dict(name="패드 바 (6종: 모듈 칸 1~4 + 끝 부속 왼·오)", kind="출력", spec="PETG 1.5T 계단형(윗 계단 y%.1f, 아래 계단 y%.1f), 길이 %.1f(뒤 멈춤까지), 쐐기 3개(백 %.2f~%.2f, 흑 %.2f~%.2f; 끝 부속은 건반마다 자기 면), 앞 손잡이(칸 이름 새김), 양쪽 가장자리 예하중 잎 혀 %.1f×%.1f×%.0f (%.1f 눌림, 레일 립 위)"
         % ((g["y_bar_joggle"], g["y_bar_joggle"] - P["pad_bar_t"], P["pad_bar_y"][1] - P["pad_bar_y"][0]) + g["wedge_range"]["w"] + g["wedge_range"]["b"] + P["bar_leaf"]),
         per_module=4, total=28 + 2, note="모듈 28 + 끝 부속 2; 예비는 파일", unit_g=round(sum(bar_g) / 4, 2)),
    dict(name="레버 봉 끝 마개", kind="출력", spec="PETG Ø4.0, 길이 %.1f, 이음 쪽 끝 핀 보스 구멍(모듈은 왼쪽 x%.1f~%.1f)에 핀 면과 같게 눌러 끼움; 반대쪽 끝 핀은 막힌 벽 %.1f" % (P["rod_L_plug"], R["clear"]["rod"]["plug"][0], R["clear"]["rod"]["plug"][1], P["rod_L_blind"]), per_module=1, total=9, note="모듈 7 + 끝 부속 2", unit_g=0.05),
    dict(name="출력 공구 (악기당 1벌, 10.1장)", kind="출력", spec="벤치 지그 받침(T1a), 높이 블록(T1b), 캡스턴 벤치 게이지 = 가짜 레버(T2), 밸런스 핀 높이 게이지(T3) — 치수 T01~T29는 tools/tools_geometry.json, 쓰는 법은 10.1장",
         per_module=0, total=len(_TLP), note="악기당; 합계 %.1f g, 약 %.0f시간" % (sum(v_["mass_g"] for v_ in _TLP.values()), sum(v_["time_min"] for v_ in _TLP.values()) / 60),
         unit_g=round(sum(v_["mass_g"] for v_ in _TLP.values()) / len(_TLP), 1)),
    dict(name="육각 렌치 2.0", kind="공구", spec="M3 ISO 7380 캡스턴 돌림 (벤치에서만)", per_module=0, total=1, note="악기당", unit_g=10.0),
    dict(name="가림판 띠", kind="출력", spec="PETG %.1fT, z%.1f(흑 노치 z%.1f)~z%.2f, 윗판 앞 턱에 걸침" % (P["curtain_t"], g["z_curtain_w"], g["z_curtain_b"], g["z_top"]),
         per_module=1, total=9, note="모듈 7 + 끝 부속 2", unit_g=round(curtain_g, 1)),
    dict(name="센서 바", kind="출력", spec="v3 (흑 낮은 구간 ±7.0); 끝 부속: 왼쪽 x0.5~46.5 (A#0 낮은 구간), 오른쪽 x0.5~23.0", per_module=1, total=9, note="모듈 7 + 끝 부속 2 (v3 단면)", unit_g=sensor_bar_g),
    dict(name="강철 블록 SS400 9T×19×40", kind="구매", spec="평철 9T×19를 40으로 절단(모따기 없음, 버 제거), 두께 %.1f~%.1f만 씀(캘리퍼스; 캐리어 주머니 %.1f, 접착층 한쪽 %.2f); 두 19×40 옆면에 MS 폴리머를 얇게 바르고 밑에서 스냅으로 끼워 접착(r4.4 고침 2b, 10장 4단계)"
         % (P["steel_w"] - 0.1, P["steel_w"] + 0.1, P["lever_w"] - 2 * P["carrier_side_wall"], P["bond_t"]), per_module=12, total=90, note="88 + 예비 2", unit_g=round(steel_block, 2)),
    dict(name="건반 봉 SUS304 Ø4", kind="구매", spec="h9, 길이 161.4 ± 0.2 (끝 부속: 왼쪽 약 45, 오른쪽 약 21)", per_module=1, total=7 + 2 + 1, note="모듈 7 + 끝 2 + 예비 1", unit_g=round(rod4_g, 2)),
    dict(name="레버 봉 SUS304 Ø4", kind="구매", spec="h9 (풀림재 항복 %.0f MPa로 충분), 길이 %.1f ± 0.2 (끝 부속: 왼쪽 %.1f, 오른쪽 %.1f) — 건반 봉과 같은 4 m 봉"
         % (P["rod_L_yield"], P["rod_L_x"][1] - P["rod_L_x"][0], rodL_end["left"], rodL_end["right"]), per_module=1, total=7 + 2 + 1,
         note="모듈 7 + 끝 2 + 예비 1", unit_g=round(rodL_g, 2)),
    dict(name="밸런스 핀 ISO 2338 Ø2×12", kind="구매", spec="SUS, y%.1f, 출력 높이 게이지로 꼭대기 z%.2f" % (P["pin_y"], P["block_step_z"] + P["pin_engage"]), per_module=12, total=88 + 4,
         note="예비 4", unit_g=round(pins_g / 12, 2)),
    dict(name="캡스턴 M3×6 ISO 7380 + M3 너트", kind="구매", spec="SUS 버튼헤드, 너트 트랩, 벤치 게이지(T2)로 꼭대기 z%.2f(정착 쉼; 건반 좌표 z%.1f)" % (R["fix2b"]["crown_T2"], P["z_c"]), per_module=12, total=88 + 4, note="예비 4 (각 2개 부품)", unit_g=0.95),
    # r4.5: the catalogue MISUMI spring, both arms cut (long / short), short leg straight in the hub's short-leg groove
    dict(name="비틀림 보조 스프링 — 미스미 %s" % P["spring_cat"]["part"], kind="구매",
         spec="한국미스미 경제형 토션스프링 %s: SUS304-WPB d%.1f, 안지름 %.0f, 3권, 암 각 90° 오른쪽 감기, 암 50/50 — 두 암을 잘라 씀: 긴 다리 %.1f (코일 중심에서 끝까지, 코일을 떠나는 점에서 %.2f), 짧은 다리 %.1f (코일을 떠나는 점에서, 굽히지 않음 — r4.5 고침 2: 레버의 가둠 홈에 끝까지 들어가 두 점으로 짝 힘을 냄, 코일은 봉에 닿지 않음). "
              "잘린 뒤 k_t %.2f N·mm/rad, b = 0에서 %.1f° 감아 설치(쉼 %.2f N·mm); 긴 다리가 코일의 +x(오른쪽) 끝에 오게, 짧은 다리 끝부터 홈을 따라 밀어 넣음 — 반대로 넣으면 짧은 다리가 홈에 맞지 않음"
              % (P["spring_cat"]["part"], P["spring_d"], P["spring_ID"], P["spring_leg"], R["spring"]["l_long"], P["spring_short_leg"], P["spring_kt"], -P["spring_free_deg"], R["spring"]["states"]["rest"]["T"]),
         per_module=12, total=100, note="88 + 단계 0 시험 4(시험 8에 1, 시험 13에 3) = 92 + 예비 8, 100개 × 310원(282원 + VAT) = 31,000원; 다리 200곳을 경선 니퍼로 자름", unit_g=round(R["spring"]["mass_g"], 3)),
    dict(name="경선(피아노선) 니퍼", kind="공구", spec="SUS304-WPB d0.5 경강선을 자르는 니퍼(일반 니퍼는 날이 이 빠짐); 스프링 100개 × 다리 2 = 200곳, 자른 끝의 거스러미는 줄로", per_module=0, total=1, note="악기당 (r4.5, 미스미 스프링)", unit_g=80.0),
    dict(name="센서 자석 Ø5×2 N35", kind="구매", spec="v3, y67", per_module=12, total=88 + 4, note="v3 그대로", unit_g=round(magnets_g / 12, 2)),
    # r4.4 (circuit cross-check 3): the control board is held by 2 screws + 2 printed locating pins (v3.2); the screws were not listed
    dict(name="제어 기판 나사 M3×6 스텐 유두 렌치볼트 (ISO 7380 버튼헤드)", kind="구매",
         spec="SUS, 머리 Ø%.1f × %.2f (모델은 Ø%.1f × %.1f 외곽 — DIN 912 Ø5.5 × 3.0로 사도 들어감); r4.4 고침 2b: 밑에서 기판을 지나(머리는 기판 밑) 기판 위에 매단 보스 %s의 Ø%.1f 막힌 구멍(z%.1f까지)에 직접 탭 = 기판 %.1f + 보스 %.1f; 나머지 2곳은 매단 보스의 위치 핀 Ø%.1f(기판 구멍으로 아래로)"
         % (P["board_screw_real"][0], P["board_screw_real"][1], P["board_screw"][0], P["board_screw"][1], "·".join("(%.1f,%.1f)" % (x_, y_) for x_, y_, k_ in P["board_standoffs"] if k_ == "screw"), P["standoff_bore"][0], P["board_boss"][1],
            P["board_z"][1] - P["board_z"][0], P["board_screw"][2] - (P["board_z"][1] - P["board_z"][0]), P["board_pin"][0]),
         per_module=2, total=14, note="v3.2 구매 목록 L35 (20개 800원, 이미 기본 구성에 있음 → 비용 변화 0); 끝 부속에는 없음", unit_g=0.6),
    dict(name="업스톱 패드", kind="구매(재단)", spec="미세셀 우레탄 폼 %.0fT (25 %% 압축 %.2f MPa) + 펠트 %.0fT, %.0f×%.1f (면 길이 = y %.0f / cos %.2f°), 쐐기에 접착"
         % (P["pad_foam"], R["heights"]["sigma25"], P["pad_felt"], P["pad_w"], R["pad_cut_len"], P["pad_y"][1] - P["pad_y"][0], R["heights"]["held_b_w"]),
         per_module=12, total=88 + 12, note="예비 12", unit_g=round(pad_g, 3)),
    dict(name="펠트·천 (캡스턴 2T, 쉼 1.5T, 앞 펠트 2T + PU 1T, 키퍼 2T, 노치·핀 홈·탭 천 0.5T)", kind="소모",
         spec="양모 펠트, 부싱 천; 쉼 펠트 8.0×2.7, F·F#만 USB 홈 옆 %s (홈 위로 나오지 않게)" % ", ".join("%s %.2f×%.1f (x%.2f~%.2f)" % (
             k_, R["r44"]["land"][k_]["felt"][1] - R["r44"]["land"][k_]["felt"][0], P["rest_pad_y"][1] - P["rest_pad_y"][0], R["r44"]["land"][k_]["felt"][0], R["r44"]["land"][k_]["felt"][1]) for k_ in ("F", "F#")), per_module=1, total=1, note="묶음", unit_g=round(felt_g, 1)),
    dict(name="PET 심 0.1 (OHP 필름 6×%.1f)" % R["pad_cut_len"], kind="소모", spec="패드 밑 업스톱 시점 조정 (패드와 같은 크기)", per_module=0, total=50, note="필요한 만큼", unit_g=0.01),
    # r4.4 fix 2: the steel blocks are bonded into their carriers
    dict(name="MS 폴리머(하이브리드) 탄성 접착제", kind="소모", spec="강철 블록의 두 19×40 옆면 ↔ 캐리어 옆벽(0.7) 접착, 접착층 한쪽 %.2f (주머니 %.1f − 강철 %.1f); 전단 탄성 G 약 %.0f MPa, 설계 겹침 전단 %.1f MPa(단계 0 시험 20); 면 #120 사포 + 알코올, 블록당 약 0.2 mL, 24 h 굳힘. 5분 에폭시(단단함)는 쓰지 않음 — 열팽창 차이로 떨어짐(1e장 고침 2b)"
         % (P["bond_t"], P["lever_w"] - 2 * P["carrier_side_wall"], P["steel_w"], P["bond_G"], P["bond_tau"]), per_module=0, total=1,
         note="튜브 약 80 mL 1개 (추정 8,000원)", unit_g=80.0),
]
json.dump(dict(meta=dict(project="Toccata v4 W1+ round 4", note="per_module = one octave module (C..B); total = 88 keys (7 modules + end parts) incl. spares; unit_g = mass of one piece"),
               parts=parts, per_module_counts=dict(printed=r4_printed, bought=r4_bought), r3_counts=dict(printed=r3_printed, bought=r3_bought)),
          open(os.path.join(OUT, "parts_list.json"), "w"), ensure_ascii=False, indent=1)
R["parts_list"] = parts
R["params"] = {k: P[k] for k in ("ghost_long", "ghost_rep_max", "sb_ledge", "sb_ledge_y", "bar_top_w", "bar_y", "tab_play", "yaw_pin", "yaw_lever", "rearm", "pad_e", "pad_e_pass", "snap_F", "snap_F_min", "lift_play", "lift_abuse", "lift_popout",
                                 "block_lift", "block_step_z", "block_lip_wall", "dw_target_w", "dw_target_b", "gap_us_w", "gap_us_b", "ghost_win", "ghost_v_note",
                                 "ghost_v_desc", "ghost_ratio", "fin_y", "fin_main_y0", "fin_ext_inset", "removal_lip_clear", "head_gap", "tail_gap_ww", "black_w",
                                 "rod_k_x", "rod_L_x", "rod_L_plug", "rod_L_blind", "pin_len", "slot_w_print", "slot_depth", "rail_front_y", "pin_y", "slot_y", "block_y",
                                 "front_e", "w_felt_y", "w_floor_y", "tab_cloth", "cradle_clear", "ring_min_lf", "rail_x", "tab_w", "tab_w_b", "rib_in", "keeper_gap",
                                 "pad_y", "pad_w", "pad_felt", "pad_foam", "pad_E", "pad_epsD", "seat_k_req", "pad_bar_t", "pad_bar_y", "plate_t", "ledge_y0",
                                 "spring_kt", "spring_free_deg", "spring_d", "spring_ID", "spring_n", "spring_leg", "spring_pocket", "spring_groove", "steel_len",
                                 "steel_h", "rod_L", "rod_L_yield", "nail_tab", "curtain_gap_w", "curtain_gap_b", "v_play", "v_abuse", "v_abuse_chord",
                                 "s_cyc", "s_rare", "s_cyc_in", "s_rare_in", "boss_R", "seat_k_chord_req", "fin_slot_y", "black_skin_step", "rail_y0", "rail_lip",
                                 "bar_leaf", "lip_gap_y", "collar_short", "spring_boss", "spring_lead_in", "plate_step_y", "board_slot_clear", "board_slot_keepout",
                                 "bar_joggle_clear", "bar_leaf_y", "bar_leaf_slot", "bar_leaf_bump", "bar_leaf_gap", "rail_lip_t", "rail_lip_y0", "bar_raise_pull",
                                 "spring_slot", "spring_rm", "spring_leg_clear", "spring_short_leg", "bar_rail", "spring_groove", "nail_tab", "nail_tab_below", "cap_R_out",
                                 "board_x", "board_y", "black_top", "y_skin_end", "ledge_y0", "curtain_y", "curtain_hook", "rod_L_x",
                                 "usb_x", "usb_y", "usb_z", "usb_clear", "usb_wall_open", "zero_xy", "zero_z", "usb_rcpt", "mux_xy", "ribbon_pads", "ribbon_cores",
                                 "ribbon_pitch", "ribbon_x", "ext_pads", "comp_rear", "comp_front_y", "board_slot_y1", "comp_zmax", "shelf_y", "rib_y0", "ribs",
                                 "rest_pad_y", "beam_w", "board_z",
                                 # r4.4
                                 "lip", "lip_over", "lip_segs", "lip_end_y", "z_st", "z_sb", "y_steel_front", "rail_front_chamfer", "rest_foot", "y_tail_end", "lip_front_y", "felt_c_y",
                                 # r4.4 circuit cross-check
                                 "ribbon_xc", "ribbon_j301", "ribbon_under_z", "ribbon_z", "ext_z", "board_pad_r", "board_standoffs", "standoff_d", "standoff_bore", "board_screw",
                                 "board_pin", "board_hole", "sb_board", "sb_post", "sb_rib_front", "sb_rib_rear", "sb_rib_x", "sb_rib_gap", "sb_j201", "lead_lane_z",
                                 "lead_notch_z", "lead_margin", "z_floor", "rail_y", "board_screw_real", "lead_fan",
                                 # r4.5
                                 "spring_E", "spring_arm_deg", "spring_swept_free", "spring_T0", "spring_cat", "spring_notch", "spring_rm", "hub_R", "L")}
R["params"]["BH"] = BH
R["seat"] = dict(k_min=g["seat_k"], k_keys=g["seat_k_keys"], k_chord=k_ch)
R["timing"] = dict(total_s=time.time() - t_start, dyn_s=t_dyn)
pr("\nrun time %.0f s (dynamics %.0f s)" % (time.time() - t_start, t_dyn))

with open(os.path.join(OUT, "results.txt"), "w") as f:
    f.write("\n".join(T) + "\n")
# r4.4 fix 2b: checkpoint for a re-export without re-running (PadTables rebuilt from g), and keep going if the export fails
try:
    import pickle
    _gs = {k_: v_ for k_, v_ in g.items() if k_ not in ("pad_w", "pad_b")}
    _ck = os.path.join(OUT, "work_r45d", "ckpt_r45d.pkl")          # r4.5 circuit 2nd (r4.5 fix: work_r45c/ckpt_r45b.pkl)
    try:
        with open(_ck, "wb") as f_:
            pickle.dump(dict(R=R, g=_gs, ep=ep, pk=pk, pl=pl, T=T), f_)
    except Exception as e_:
        with open(_ck, "wb") as f_:
            pickle.dump(dict(R=R, g=_gs, pk=pk, pl=pl, T=T), f_)
        print("checkpoint without ep:", e_)
except Exception as e_:
    print("checkpoint not written:", e_)
import export_geo
try:
    export_geo.export(P, g, R, ep, OUT, pk, pl)
except Exception as e_:
    import traceback
    traceback.print_exc()
    print("EXPORT FAILED - metrics.json is still written; re-export from work_r45d/ckpt_r45d.pkl")

with open(os.path.join(OUT, "results.txt"), "w") as f:
    f.write("\n".join(T) + "\n")


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, float):
        return round(o, 6)          # r4.4 fix 2: 6 places (4 places could flip the last shown digit, DESIGN 5)
    if hasattr(o, "item"):
        return clean(o.item())
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


R.pop("dyn_raw", None)
with open(os.path.join(OUT, "metrics.json"), "w") as f:
    json.dump(clean({k: v for k, v in R.items() if k != "plate" or True}), f, ensure_ascii=False, indent=1)
print("wrote results.txt, metrics.json, geometry.json, parts_list.json")
