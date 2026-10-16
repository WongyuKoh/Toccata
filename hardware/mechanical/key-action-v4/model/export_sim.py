#!/usr/bin/env python3
"""Toccata v4 W1+ r4.5 - export for the page tab '05 동작 시뮬레이션' (docs/report/toccata-v4/fin/sim/).

Read-only use of the verified model: model_v4.py is imported and never edited; geometry.json / metrics.json are read.
Nothing here changes a design value.  Writes:
  fin/sim/keyaction.json  time histories (white D, black C#) of the r4.5 4-DOF dynamics (Dyn.run, dt 4 us) for a
                          0.8 N push (the metrics 'pp' case) and struck notes at key-front speeds 0.3 / 0.7 / 1.0 / 1.5 /
                          2.5 m/s: strike -> hold 1 N -> let go; side-section outlines at the balance-pin plane (the same
                          plane as drawings d01 / d02), sensor law, thresholds, the metrics numbers the page shows
  fin/sim/system.json     88-key signal map (from hardware/pcb netlist CSVs), audio chain, power budget (sheets.budget),
                          touchscreen fold outlines (CAD solids, optional)

Usage (repo root or anywhere):  python3 hardware/mechanical/key-action-v4/model/export_sim.py [--out DIR] [--cad-check]
--cad-check also loads hardware/mechanical/cad (build_all.collect(), read-only, ~15 s) and compares the exported rest
outlines with the CAD solids of module O1 and builds the touchscreen fold outlines from the CAD solids.
"""
import argparse, csv, json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
import model_v4 as m                                                  # noqa: E402  (read-only)

P = m.P
CHECKS = []                                                           # (name, ok, detail)


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("OK   " if ok else "FAIL ") + name + ("  " + detail if detail else ""), flush=True)


def r(v, n):
    return float(round(float(v), n))


# =============================================================================== sensor law (SCH-02 table basis)
# SCH-02 note: field on the axis of the Ø5x2 N35 disc magnet (Br 1.19 T), +-10 %; DRV5055A2 at 3.3 V = 1.65 V + 30 mV/mT
# (A2 linear range +-44 mT), RP2040 ADC 12 bit ratiometric to the same 3.3 V.
SENS = dict(Br_mT=1190.0, R=2.5, L=2.0, vq=1.65, mv_per_mT=30.0, vref=3.3, codes=4096, lin_mT=44.0)


def field_mT(gap):
    R_, L_, Br = SENS["R"], SENS["L"], SENS["Br_mT"]
    return Br / 2.0 * ((gap + L_) / math.sqrt(R_ * R_ + (gap + L_) ** 2) - gap / math.sqrt(R_ * R_ + gap * gap))


def adc_of_gap(gap):
    v = SENS["vq"] + SENS["mv_per_mT"] / 1000.0 * field_mT(gap)
    return v / SENS["vref"] * SENS["codes"]


# =============================================================================== firmware-side assumptions of the page
TH = dict(rearm=P.get("rearm", 0.50),          # model / firmware: re-arm when the magnet has come back 50 %
          noteon=0.10,                          # page assumption: note-on when the magnet is 90 % down
          vel_hi=0.50, vel_lo=0.10)             # page assumption: velocity = magnet time between 50 % and 90 % down
VMAP = dict(v_lo=0.05, v_hi=2.0)                # page assumption: MIDI velocity = 1 + 126 ln(v/v_lo)/ln(v_hi/v_lo), clamp


def midi_vel(v_front):
    if v_front <= VMAP["v_lo"]:
        return 1
    return int(max(1, min(127, round(1 + 126 * math.log(v_front / VMAP["v_lo"]) / math.log(VMAP["v_hi"] / VMAP["v_lo"])))))


# =============================================================================== 2D polygon helpers (manifold3d)
def _cs(polys):
    import manifold3d as m3
    out = None
    for p in polys:
        q = [(float(a), float(b)) for a, b in p]
        if len(q) < 3:
            continue
        a2 = 0.5 * sum(q[i][0] * q[(i + 1) % len(q)][1] - q[(i + 1) % len(q)][0] * q[i][1] for i in range(len(q)))
        if a2 < 0:
            q = q[::-1]
        c = m3.CrossSection([q])
        out = c if out is None else out + c
    return out


def union_rings(polys, subs=()):
    c = _cs(polys)
    if c is None:
        return []
    if subs:
        s = _cs(subs)
        if s is not None:
            c = c - s
    return [[[r(x, 3), r(y, 3)] for x, y in ring] for ring in c.to_polygons()]


def rings(poly):
    return [[r(x, 3), r(y, 3)] for x, y in poly]


# =============================================================================== geometry for the section views
FRAME_KEYS = ("floor", "white front rail", "tab ", "keeper hook", "black stop rail", "black tab base", "balance rail",
              "rod end stop post", "rear shelf", "shelf rib", "fin", "top plate", "pad bar rail", "rear wall",
              "rear dovetail", "front dovetail", "cheek", "spring groove boss", "control-board stand-off",
              "control-board locating pin", "sensor board support", "control-board boss", "sensor-bar ledge")
# same classes as the drawing kit (drawings/src/kit.py MAT_FIXED), reduced to what the page draws
MAT = [("fin boss bore", "void"), ("lever rod end plug", "print2"), ("lever rod D4", "steel"),
       ("spring groove cut", "void"), ("spring groove entry chamfer", "void"), ("control-board screw", "env"),
       ("sensor board support", "print"), ("sensor board", "pcb"), ("up-stop pad", "pad"), ("felt", "felt"),
       ("key rod", "steel"), ("balance pin", "steel"), ("control board", "pcb"), ("board components", "env"),
       ("board part", "env"), ("RP2040", "env"), ("USB-C plug", "env"), ("pad bar rail", "print"), ("pad bar", "bar"),
       ("pad wedge", "bar"), ("cover curtain", "cover"), ("sensor bar", "sbar")]


def mat_of(name):
    for k, c in MAT:
        if k in name:
            return c
    return "print"


# Korean names (final parts) for the fixed parts the page draws, used as hover titles.  Names follow the CAD (build_all.collect()
# name_ko) and the rev E circuit BOM (hardware/pcb/netlist/bom.csv PCB-SB: SB is a 6-row strip cut from the 12 x 18 board).
# Order matters (first match wins).  The key name in the geometry name (last token, e.g. 'D', 'C#') is appended.
FIXED_KO = [("sensor board SB", "센서 기판 SB (12 × 18 기판에서 자른 6행 띠 161.6 × 15.24 × 1.6)", False),
            ("sensor bar", "센서 바 (출력)", False),
            ("key rod", "건반 봉 SUS304 Ø4", False),
            ("lever rod", "레버 봉 SUS304 Ø4", False),
            ("balance pin", "밸런스 핀 Ø2×12 SUS304", True),
            ("up-stop pad", "업스톱 패드 (산 것 PORON 5T + 펠트 1T, 계산은 설계 패드)", True),
            ("pad wedge", "패드 바 쐐기 (출력)", True),
            ("pad bar grip", "패드 바 손잡이 (출력)", False),
            ("pad bar", "패드 바 (출력)", False),
            ("cover curtain hook", "가림판 띠 고리 (출력)", False),
            ("cover curtain", "가림판 띠 (출력)", False),
            ("keeper felt", "키퍼 펠트 2T", True),
            ("white front felt", "백건 앞 펠트 3T (울 펠트 2T + 하네나이트 1T)", False),
            ("black front felt", "흑건 앞 펠트 3T (울 펠트 2T + 하네나이트 1T)", True)]
NOTE_TOKENS = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}


def ko_name(part):
    for k, ko, keyed in FIXED_KO:
        if part.startswith(k):
            last = part.split(" ")[-1]
            return ko + (f" · 건반 {last}" if keyed and last in NOTE_TOKENS else "")
    return None


def cut_x(p, x):
    return p["x"][0] - 1e-9 <= x <= p["x"][1] + 1e-9


def section_geometry(G, A, colour, key, lever, xsec, extra_keys=()):
    """outlines at the plane x = xsec, seen from +x (y right, z up): key in its design frame (the page applies the
    simulated planar state), lever in its b = 0 frame (side_rigid0; the page rotates it by -b about L), fixed parts."""
    parts = G["parts"]
    kp = [p for p in parts if p["body"] == key]
    lp = [p for p in parts if p["body"] == lever]
    fx = [p for p in parts if p["body"] == "fixed" and cut_x(p, xsec)]
    out = dict(xsec=xsec)
    kcut = [p for p in kp if cut_x(p, xsec)]
    out["key_cut"] = union_rings([p["side_rest"] for p in kcut if p["part"] not in ("capstan head", "rest felt")])
    out["key_beyond"] = [rings(p["side_rest"]) for p in kp if not cut_x(p, xsec) and p["x"][1] < xsec]
    out["key_steel"] = [rings(p["side_rest"]) for p in kp if p["part"] == "capstan head"]
    out["key_felt"] = [rings(p["side_rest"]) for p in kp if p["part"] == "rest felt"]
    ym, zf = A.mag
    out["magnet_S"] = rings(m.rect(ym - 2.5, ym + 2.5, zf, zf + 1.0))      # Ø5 x 2, S pole down (DESIGN, BRD-02)
    out["magnet_N"] = rings(m.rect(ym - 2.5, ym + 2.5, zf + 1.0, zf + 2.0))
    lcut = [p for p in lp if cut_x(p, xsec)]
    out["lever_cut"] = union_rings([p["side_rigid0"] for p in lcut if not p["part"].startswith(("steel", "felt"))])
    out["lever_steel"] = [rings(p["side_rigid0"]) for p in lcut if p["part"].startswith("steel")]
    out["lever_felt"] = [rings(p["side_rigid0"]) for p in lcut if p["part"].startswith("felt")]
    out["lever_beyond"] = [rings(p["side_rigid0"]) for p in lp if not cut_x(p, xsec) and p["x"][1] < xsec]
    # torsion spring (model spring_geometry): coil + long leg fixed while loaded, short leg turns with the lever
    sg = m.spring_geometry(P, 0.0)
    xl = G["solved"]["levers"][key.split(" ")[1]]
    cl_ = (P["spring_n"] + 1) * P["spring_d"] / 2
    out["spring"] = dict(coil=rings(sg["coil"]), coil_r_mean=r(sg["coil_rm"], 3), d=P["spring_d"],
                         long_leg=rings(sg["long_leg"]), short_leg_lf=rings(sg["short_leg"]),
                         coil_cut=bool(xl - cl_ - 1e-9 <= xsec <= xl + cl_ + 1e-9))
    # fixed parts: the frame as one union minus the spring-leg groove (as the drawing kit does), the rest by material
    frame = [p["side"] for p in fx if p["part"].startswith(FRAME_KEYS) and not p.get("female")]
    voids = [p["side"] for p in fx if p.get("female")]
    out["frame"] = union_rings(frame, subs=voids)
    groups = {}
    for p in fx:
        n = p["part"]
        if n.startswith(FRAME_KEYS) or p.get("female"):
            continue
        c = mat_of(n)
        if c in ("env", "void"):
            continue
        groups.setdefault(c, []).append(dict(part=n, ko=ko_name(n), ring=rings(p["side"])))
    out["fixed"] = groups
    # neighbour white keys cut by the plane (black section): static, at rest
    ex = []
    for b in extra_keys:
        cut = [p["side_rest"] for p in parts if p["body"] == b and cut_x(p, xsec) and p["part"] not in ("capstan head", "rest felt")]
        if cut:
            ex.append(dict(body=b, rings=union_rings(cut)))
    out["neighbours"] = ex
    return out


# =============================================================================== runs
def run_case(D, st, kind, v_target=None, F_push=None, hold=200.0, after=150.0, pre=5.0):
    """record every 4 us step.  kind 'strike': co-moving start at the finger speed v0 that gives key-front speed v_target at
    the front felt (model v0_for_front, finger F_follow = 1 N below 1.15 m/s else 3 N as run_all's grid rule), finger
    F_follow until t_bottom + 2 ms (model strike), then holds 1.0 N until t_bottom + hold, then lets go.
    kind 'push': constant F_push for 150 ms then let go (model press = the metrics 'pp' case)."""
    A = D.A
    if kind == "strike":
        F_f = 1.0 if v_target < 1.15 else 3.0
        v0 = m.v0_for_front(D, st, v_target, F_follow=F_f)
        s0 = m.strike_state(A, st, v0)

        def fin(t, ev):
            if ev["t_bottom"] is None or t < ev["t_bottom"] + 2.0:
                return F_f
            if t < ev["t_bottom"] + hold:
                return 1.0
            return 0.0

        def stop(t, ev):
            return ev["t_bottom"] is not None and t >= ev["t_bottom"] + hold + after
        ev = D.run(2000.0, state=s0, finger=fin, record=True, rec_every=1, stop_when=stop)
        meta = dict(kind="strike", v_target=v_target, F_follow=F_f, v0=v0, F_hold=1.0, hold_ms=hold)
    else:
        s0 = st
        ev = D.run(150.0 + 200.0, state=st, finger=lambda t, ev_: F_push if t < 150.0 else 0.0, record=True, rec_every=1)
        meta = dict(kind="push", F_push=F_push, push_ms=150.0)
    H = np.array([h[:17] for h in ev["hist"]], dtype=float)
    dt = 0.004
    # key COM translation: Dyn.run integrates c += vc dt after updating vc; the record holds that vc -> exact replay
    cy = s0[2][0] + np.cumsum(H[:, 12]) * dt
    cz = s0[2][1] + np.cumsum(H[:, 13]) * dt
    cerr = max(abs(cy[-1] - ev["state"][2][0]), abs(cz[-1] - ev["state"][2][1]))
    data = dict(t=H[:, 0], th=H[:, 1], b=H[:, 2], frac=H[:, 3], Nc=H[:, 4], fre=H[:, 7], fup=H[:, 8], ffr=H[:, 9],
                Ff=H[:, 16], cy=cy, cz=cz)
    return ev, meta, data, cerr, s0


def kw_pts(A, th, cy, cz, p):
    rx, rz = p[0] - A.ck[0], p[1] - A.ck[1]
    return cy + rx * np.cos(th) - rz * np.sin(th), cz + rx * np.sin(th) + rz * np.cos(th)


def crossing(t, y, level, i0=0, down=True):
    """first time at or after index i0 where y crosses level (down: from above to <= level), linear interpolation."""
    y = np.asarray(y)
    if down:
        idx = np.nonzero(y[i0:] <= level)[0]
    else:
        idx = np.nonzero(y[i0:] >= level)[0]
    if len(idx) == 0:
        return None, None
    j = i0 + int(idx[0])
    if j == 0:
        return float(t[0]), 0
    y0, y1 = y[j - 1], y[j]
    f = 0.0 if y1 == y0 else (level - y0) / (y1 - y0)
    return float(t[j - 1] + f * (t[j] - t[j - 1])), j


def decimate(t, Y, tol, keep_idx=(), max_dt=1.0):
    """greedy piecewise-linear decimation: keep the fewest samples so that linear interpolation between kept samples
    reproduces every channel within tol (and no gap longer than max_dt ms).  keep_idx are always kept."""
    n = len(t)
    forced = np.zeros(n, bool)
    for k in keep_idx:
        if k is not None and 0 <= k < n:
            forced[k] = True
    nxt_forced = np.full(n, n - 1)
    last = n - 1
    for k in range(n - 1, -1, -1):
        if forced[k]:
            last = k
        nxt_forced[k] = last

    def ok(i, j):
        if j - i <= 1:
            return True
        if t[j] - t[i] > max_dt:
            return False
        a = (t[i:j + 1] - t[i]) / (t[j] - t[i])
        itp = Y[i] + a[:, None] * (Y[j] - Y[i])
        return bool(np.all(np.abs(itp - Y[i:j + 1]) <= tol))
    keep = [0]
    i = 0
    while i < n - 1:
        lim = nxt_forced[i + 1] if i + 1 < n else n - 1
        lim = min(lim, n - 1)
        step = 1
        good = i + 1
        while good + step <= lim and ok(i, good + step):
            good += step
            step *= 2
        hi = min(good + step, lim + 1)
        while hi - good > 1:
            mid = (good + hi) // 2
            if ok(i, mid):
                good = mid
            else:
                hi = mid
        keep.append(good)
        i = good
    return np.array(sorted(set(keep)))


def summarize(A, colour, meta, data, ev, st_rest, mag_rest, mag_bot, z_elem, front_rest_z, pre):
    t = data["t"]
    gap = kw_pts(A, data["th"], data["cy"], data["cz"], A.mag)[1] - z_elem
    fz = kw_pts(A, data["th"], data["cy"], data["cz"], A.front)[1]
    fr = (gap + z_elem - mag_bot) / (mag_rest - mag_bot)
    # Dyn records frac with the updated COM but the rotation of the step start (kw closure): differs by < 1e-4
    assert np.max(np.abs(fr - data["frac"])) < 1e-3, "frac replay %.2e" % np.max(np.abs(fr - data["frac"]))
    Ff = data["Ff"]
    i_rel = int(np.nonzero((Ff == 0.0) & (np.arange(len(Ff)) > 0))[0][0]) if np.any(Ff[1:] == 0.0) else None
    t_rel = float(t[i_rel]) if i_rel is not None else None
    i_rel_eff = i_rel if i_rel is not None else len(t)
    i_bot = int(np.nonzero(data["ffr"] > 0)[0][0]) if np.any(data["ffr"] > 0) else None
    t_hi, i_hi = crossing(t, fr, TH["vel_hi"], 0, down=True)
    t_on, i_on = crossing(t, fr, TH["noteon"], 0, down=True)
    v_mag = None if (t_hi is None or t_on is None) else (TH["vel_hi"] - TH["vel_lo"]) * (mag_rest - mag_bot) / (t_on - t_hi)
    # SCH-03 note 9 stroke ratio: key front = magnet x 1.91 (white) / 1.18 (black) = design dip / magnet travel
    ratio = (P["dip_b"] if A.black else P["dip_w"]) / (mag_rest - mag_bot)
    v_est = None if v_mag is None else v_mag * ratio
    t_arm, i_arm = (None, None) if i_rel is None else crossing(t, fr, TH["rearm"], i_rel, down=False)
    t_full, i_full = (None, None) if i_rel is None else crossing(t, fr, 1.0, i_rel, down=False)
    pre_rel = slice(0, i_rel_eff)
    hold_frac = float(np.max(fr[i_on:i_rel_eff])) if (i_on is not None and i_on < i_rel_eff) else None
    s = dict(t_bottom=None if ev["t_bottom"] is None else r(ev["t_bottom"] + pre, 3),
             v_front_bottom=None if ev["v_front_bottom"] is None else r(ev["v_front_bottom"], 4),
             v_finger_bottom=None if ev["v_bottom"] is None else r(ev["v_bottom"], 4),
             t_vel_hi=None if t_hi is None else r(t_hi + pre, 3), t_noteon=None if t_on is None else r(t_on + pre, 3),
             v_mag_est=None if v_mag is None else r(v_mag, 4), ratio_front_mag=r(ratio, 4),
             v_front_est=None if v_est is None else r(v_est, 4), midi_vel=None if v_est is None else midi_vel(v_est),
             t_release=None if t_rel is None else r(t_rel + pre, 3),
             t_rearm=None if t_arm is None else r(t_arm + pre, 3), t50_after_release=None if t_arm is None else r(t_arm - t_rel, 3),
             t_full=None if t_full is None else r(t_full + pre, 3), t100_after_release=None if t_full is None else r(t_full - t_rel, 3),
             up_peak=r(np.max(data["fup"][pre_rel]), 3), cap_peak=r(np.max(data["Nc"][pre_rel]), 3),
             front_peak=r(np.max(data["ffr"][pre_rel]), 3), finger_peak=r(np.max(Ff), 3),
             rest_peak_after_release=None if i_rel is None else r(np.max(data["fre"][i_rel:]), 3),
             cap_peak_after_release=None if i_rel is None else r(np.max(data["Nc"][i_rel:]), 3),
             gap_min=r(np.min(gap), 4), adc_max=int(round(adc_of_gap(float(np.min(gap))))),
             travel_max=r(front_rest_z - np.min(fz), 4), b_max_deg=r(math.degrees(np.max(data["b"])), 4),
             hold_frac_max=None if hold_frac is None else r(hold_frac, 4),
             cap_sep_max=r(ev["sep_max"], 4), lift_max=r(ev["lift_max"], 4))
    idx = dict(bottom=i_bot, rel=i_rel, on=i_on, hi=i_hi, arm=i_arm, full=i_full)
    return s, gap, fz, fr, idx


# =============================================================================== system data (signal map, power, audio)
def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def fmt_val(v):
    """bom.csv short values -> text with units: '1k' -> '1 kΩ', '100n' -> '100 nF', '20Ω' -> '20 Ω'."""
    v = v.strip()
    if v.endswith("Ω"):
        return v[:-1].strip() + " Ω"
    if v[-1:] in ("k", "M") and v[:-1].replace(".", "").isdigit():
        return v[:-1] + " " + v[-1] + "Ω"
    if v[-1:] in ("n", "u", "µ", "p") and v[:-1].replace(".", "").isdigit():
        return v[:-1] + " " + {"u": "µ"}.get(v[-1], v[-1]) + "F"
    return v


def pedal_path(rows, R_, PN, PNM, N_, bom_row, bcol, cables):
    """sustain-pedal signal path built from the SCH-05 netlist rows (rev E: W502 ends at the J502 pads of the PB board) and the
    bom.csv values; the topology is asserted so a circuit change stops the export instead of showing a stale path."""
    def pins(ref):
        return {x[PN]: (x[N_], x[PNM]) for x in rows(sheet="SCH-05", ref=ref)}

    def val(ref):
        b = bom_row(ref)
        return fmt_val(b[bcol[3]]) if b else "?"
    u = pins("U551")
    p_out = [p for p, (n, nm) in u.items() if nm == "OUT"][0]
    n_out = u[p_out][0]
    r551 = pins("R551")
    assert n_out in [n for n, _ in r551.values()], "U551 OUT -> R551"
    tip = [n for n, _ in r551.values() if n != n_out][0]
    p501 = {nm: n for _, (n, nm) in pins("P501").items()}
    j501 = {nm: n for _, (n, nm) in pins("J501").items()}
    assert p501["T"] == j501["T"] == tip and p501["R"] == j501["R"] and p501["S"] == j501["S"] == "GND", "P501 = J501 T/R/S"
    vcc = p501["R"]
    letter = {tip: "T", vcc: "R", "GND": "GND"}
    j502 = pins("J502")
    grp = {}
    for p, (n, _) in sorted(j502.items()):
        grp.setdefault(n, []).append(p)
    assert set(grp) == {tip, vcc, "GND"}, "J502 nets"
    j502_txt = " · ".join("/".join(grp[n]) + " " + letter[n] for n in (tip, vcc, "GND"))
    r501, c501, r502, r503 = pins("R501"), pins("C501"), pins("R502"), pins("R503")
    adc_net = [n for n, _ in r501.values() if n != tip][0]
    assert tip in [n for n, _ in r501.values()], "R501 on the tip"
    a501 = [(p, nm) for p, (n, nm) in pins("A501").items() if n == adc_net]
    assert len(a501) == 1 and a501[0][1] == "GP26", "PED_ADC -> A501 GP26"
    assert sorted(n for n, _ in c501.values()) == sorted([adc_net, "GND"]), "C501 PED_ADC-GND"
    assert sorted(n for n, _ in r502.values()) == sorted([tip, "GND"]), "R502 tip-GND"
    assert vcc in [n for n, _ in r503.values()] and "+3V3" in [n for n, _ in r503.values()], "R503 +3V3-PED_VCC"
    w501, w502, w208 = cables.get("W501", {}), cables.get("W502", {}), cables.get("W208", {})
    usens = (bom_row("U551") or {}).get(bcol[3], "DRV5055")
    path = [f"U551 {usens} OUT(핀 {p_out}) → R551 {val('R551')} → {tip} (PS 기판, 페달 안)",
            f"W501 {w501.get('선', '')} → P501 플러그 ⇄ J501 잭 (T {tip} · R {vcc} · S GND)",
            f"W502 리본 {w502.get('심', '')} {w502.get('자르는 길이 (mm)', '')} mm: {w502.get('한쪽', '')} → J502 PB 패드 {j502_txt}",
            f"PB 기판: {tip} → R501 {val('R501')} → {adc_net} → A501 {a501[0][1]} (ADC0, 핀 {a501[0][0]}) · C501 {val('C501')} {adc_net}–GND · R502 {val('R502')} {tip}–GND",
            f"센서 전원: +3V3 → R503 {val('R503')} → {vcc} → J502.{grp[vcc][0]} → W502 → J501 R → U551 VCC",
            f"A501 RP2040-Zero → W208 ({w208.get('선', '')}) → {w208.get('한쪽', '')} → W209 → Pi 5",
            "MIDI CC64 0~127 (서스테인, 하프페달) · USB 장치 이름 'Toccata PED'"]
    return dict(sensor=f"U551 {usens}", path=path, src="hardware/pcb/netlist/netlist.csv SCH-05 · bom.csv · cables.csv")


def system_data():
    pcb = os.path.join(ROOT, "hardware", "pcb")
    sys.path.insert(0, os.path.join(pcb, "src"))
    import sheets as S                                     # read-only: constants + budget()
    import parts as PP
    # hardware/pcb/src/parts.py shares its module name with hardware/mechanical/cad/src/parts.py: unload after use
    sys.path.remove(os.path.join(pcb, "src"))
    for mod_ in ("sheets", "parts", "sch"):
        sys.modules.pop(mod_, None)
    NL = read_csv(os.path.join(pcb, "netlist", "netlist.csv"))
    with open(os.path.join(pcb, "netlist", "wiring_MB.csv"), encoding="utf-8-sig") as f_:     # two x / y columns: plain reader
        WM_all = list(csv.reader(f_))
    # columns found by header name (rev E: 번호, 넷, 시작, x, y, 끝, x, y, 경로 (꺾인 점, 모듈 좌표), 길이 (mm), 꺾임 수); the two
    # x / y pairs follow 시작 and 끝.  A column change stops the export instead of silently dropping the board-wiring row.
    WH = [h.strip() for h in WM_all[0]]

    def _col(pred, what):
        hit = [i for i, h in enumerate(WH) if pred(h)]
        assert len(hit) == 1, "wiring_MB.csv: column %s not found once in %s" % (what, WH)
        return hit[0]
    WC = dict(net=_col(lambda h: h == "넷", "넷"), a=_col(lambda h: h == "시작", "시작"), b=_col(lambda h: h == "끝", "끝"),
              len=_col(lambda h: h.startswith("길이"), "길이 (mm)"), path=_col(lambda h: h.startswith("경로"), "경로"),
              bends=_col(lambda h: h.startswith("꺾임"), "꺾임 수"))
    for k_ in ("a", "b"):
        assert WH[WC[k_] + 1] == "x" and WH[WC[k_] + 2] == "y", "wiring_MB.csv: x, y must follow %s (%s)" % (WH[WC[k_]], WH)
    WM = WM_all[1:]
    MX = read_csv(os.path.join(pcb, "netlist", "mux_module_pins.csv"))
    CB = read_csv(os.path.join(pcb, "netlist", "cables.csv"))
    col = list(NL[0].keys())                               # 도면, 보드, 넷, 부품, 핀, 핀 이름
    D_, B_, N_, R_, PN, PNM = col

    def rows(**kw):
        return [x for x in NL if all(x[{"sheet": D_, "board": B_, "net": N_, "ref": R_, "pin": PN}[k]] == v for k, v in kw.items())]
    mux_hdr = {x["이름"]: (x["심볼 핀"], x["모듈 헤더"], x["헤더 핀"]) for x in MX}

    def mb_route(net):
        # every wiring_MB.csv segment of this net (MB coordinates, mm); the page shows the ones that touch the mux A302
        a_, b_ = WC["a"], WC["b"]
        segs = [w for w in WM if w[WC["net"]] == net]
        return [dict(a=w[a_], ax=float(w[a_ + 1]), ay=float(w[a_ + 2]), b=w[b_], bx=float(w[b_ + 1]), by=float(w[b_ + 2]),
                     len_mm=float(w[WC["len"]]), path=w[WC["path"]], bends=int(w[WC["bends"]]))
                for w in segs]
    # MB side: net -> mux channel
    ch_of_net = {}
    for x in rows(sheet="SCH-03", board="MB"):
        if x[R_] == "A302" and x[PNM].startswith("C"):
            ch_of_net[x[N_]] = x[PNM]
    j301_of_net = {x[N_]: int(x[PN]) for x in rows(sheet="SCH-03", board="MB", ref="J301")}
    j302_net = {int(x[PN]): x[N_] for x in rows(sheet="SCH-03", board="MB", ref="J302")}
    sig = rows(sheet="SCH-03", board="MB", net="MUX_SIG")
    adc_pin = [x for x in sig if x[R_] == "A301"][0]
    sel = {x[N_]: x[PNM] for x in rows(sheet="SCH-03", board="MB", ref="A301") if x[N_].startswith("MUX_S")}
    sb = {}
    for x in rows(sheet="SCH-02", board="SB"):
        if x[R_].startswith("U2") and x[PNM] == "OUT":
            sb[x[N_]] = x[R_]
    j201_of_net = {x[N_]: int(x[PN]) for x in rows(sheet="SCH-02", board="SB", ref="J201")}
    keys = []
    for midi in range(21, 109):
        nm = NOTE_NAMES[midi % 12]
        octv = midi // 12 - 1
        e = dict(midi=midi, name=f"{nm}{octv}", black="#" in nm, freq=r(440.0 * 2 ** ((midi - 69) / 12.0), 2))
        if midi <= 23 or midi == 108:
            side = "EL" if midi <= 23 else "ER"
            eb = S.END_BOARDS[side]
            kk = [k for k in eb["keys"] if k[1] == e["name"]][0]
            net = [x[N_] for x in rows(sheet="SCH-04", board=side, ref=eb["jref"]) if x[PNM] == e["name"]][0]
            xpin = int([x[PN] for x in rows(sheet="SCH-04", board=side, net=net) if x[R_] == ("X402" if side == "EL" else "X412")][0])
            ext = j302_net[xpin]
            ch = [x[PNM] for x in rows(sheet="SCH-03", board="MB", net=ext) if x[R_] == "A302"][0]
            mod = 1 if side == "EL" else 7
            res = [x[R_] for x in rows(sheet="SCH-04", board=side, net=net) if x[R_].startswith("R4")][0]
            pd = [x[R_] for x in rows(sheet="SCH-03", board="MB", net=ext) if x[R_].startswith("R3")][0]
            x0 = 0.0 if side == "EL" else 47.0 + 164.5 * 7
            e.update(part=side, mb=f"O{mod}", sensor=kk[0], board=side, x_sensor=r(x0 + kk[2], 3), net=net,
                     path=[f"{kk[0]} OUT → {res} 1 kΩ (센서 옆, △8)", f"{eb['jref']}.{xpin} → 리드 {'W401' if side == 'EL' else 'W411'}",
                           f"{'X401 ⇄ X402' if side == 'EL' else 'X411 ⇄ X412'} (JST-XH 6P) → 연장 {'W403' if side == 'EL' else 'W413'}",
                           f"O{mod} MB J302.{xpin} = {ext} (풀다운 {pd} 100 kΩ)"],
                     j_pin=xpin, ext=ext, mux_ch=ch, mb_route=mb_route(ext), ribbon=None)
        else:
            mod = (midi - 24) // 12 + 1
            i = (midi - 24) % 12
            net = S.NET[NOTE_NAMES[i]]
            u = sb[net]
            jp = j201_of_net[net]
            assert jp == j301_of_net[net]
            ch = ch_of_net[net]
            e.update(part=f"O{mod}", mb=f"O{mod}", sensor=u, board="SB", x_sensor=r(47.0 + 164.5 * (mod - 1) + S.SENSOR_X[i], 3), net=net,
                     path=[f"{u} OUT (SB 기판 O{mod}) → J201.{jp}", f"리본 W10{mod} {jp}번 선 (16심, 약 180 mm)", f"O{mod} MB J301.{jp}"],
                     j_pin=jp, ext=None, mux_ch=ch, mb_route=mb_route(net), ribbon=f"W10{mod}")
        chn = int(e["mux_ch"][1:])
        sp, hdr, hp = mux_hdr[e["mux_ch"]]
        e.update(mux_sym_pin=int(sp), mux_hdr=f"{hdr}.{hp}", sel_bits=format(chn, "04b"),
                 adc=f"{adc_pin[PNM]} (ADC0)", adc_pad=f"A301 패드 {adc_pin[PN]} / WS P1 {PP.WS_P1['GP26']}",
                 usb=f"W20{e['mb'][1:]}", usb_name=f"Toccata {e['mb']}")
        keys.append(e)
    # scan rate: an ESTIMATE (no scan period is given in hardware/pcb).  Per channel = the settle wait of SCH-03 note 7 (4 us after
    # S0..S3 change) + one RP2040 ADC conversion (96 clocks at 48 MHz = 2 us).  Channels per board from the mux map (O1 15, O7 13).
    scan_assume = dict(settle_us=4.0, conv_us=2.0, per_ch_us=6.0, estimate=True,
                       src="추정: SCH-03 주 7 (S0~S3 바꾼 뒤 4 µs 대기) + RP2040 ADC 변환 1번 2 µs (96클록 ÷ 48 MHz). hardware/pcb에 스캔 주기는 없음")
    n_ch = {1: 15, 7: 13}
    pc = scan_assume["per_ch_us"]
    scan = {f"O{k}": dict(channels=n_ch.get(k, 12), period_us=r(pc * n_ch.get(k, 12), 1), khz=r(1000.0 / (pc * n_ch.get(k, 12)), 1), estimate=True)
            for k in range(1, 8)}
    for k in keys:
        nmb = sum(1 for q in keys if q["mb"] == k["mb"])
        assert nmb == scan[k["mb"]]["channels"], (k["mb"], nmb)
    sel_pins = {k: v for k, v in sorted(sel.items())}
    B = S.budget()
    T = S.BATT
    I = S.BUDGET_IN
    # fuse as installed (rev E bom.csv F601: ATO blade in the user's ATC/ATO inline holder)
    BOM = read_csv(os.path.join(pcb, "netlist", "bom.csv"))
    bcol = list(BOM[0].keys())                             # 도면, 보드, 부품, 값, 부품 설명, ...

    def bom_row(ref):
        q = [x for x in BOM if x[bcol[2]] == ref]
        return q[0] if q else None
    fr_ = bom_row("F601")
    fuse = dict(ref="F601", value=fr_[bcol[3]], desc=fr_[bcol[4]], holder=(bom_row("F601-HLD") or {}).get(bcol[4], ""),
                src="hardware/pcb/netlist/bom.csv F601")
    power = dict(batt=dict(model=T["model"], v_nom=T["v_nom"], v_min=T["v_min"], v_max=T["v_max"], wh=T["wh"], usable=T["usable"],
                           fuse_a=T["fuse_a"], amp_w_ch=T["amp_w_ch"], amp_eff=T["amp_eff"], buck_min_v=T["buck_min_v"]),
                 loads=dict(pi_w=I["pi_w"], hub_w=I["hub_w"], dongle_w=I["dongle_w"], disp_w=S.DISP["power_w"], eff=I["eff"],
                            amp_avg_w=list(I["amp_avg_w"]), v5=I["pi_v"]),
                 budget=dict(avg=[r(x, 2) for x in B["avg"]], avg_a=[r(x, 3) for x in B["avg_a"]], peak=r(B["peak"], 2), peak_a=r(B["peak_a"], 3),
                             peak_a_min_v=r(B["peak_a_min_v"], 3), run=[r(x, 2) for x in B["run"]], base_new=r(B["base_new"], 3),
                             amp_hi=r(B["amp_hi"], 2), loss_new=r(B["loss_new"], 3), five_new=r(B["five_new"], 3)),
                 fuse=fuse,
                 src="hardware/pcb/src/sheets.py BATT · BUDGET_IN · DISP · budget() = SCH-06 전원 예산 (research/power.md 0.4 · 0.7); 퓨즈 F601 = netlist/bom.csv")
    # cable list: every column as written by hardware/pcb (column names change between circuit revisions: keep them all)
    cables = {x[list(x.keys())[0]]: {k: v for k, v in x.items()} for x in CB}
    # USB cable of each module (rev E: one cables.csv row per cable W201..W207, each with its own length and hub port)
    for e in keys:
        c_ = cables.get(e["usb"])
        assert c_ is not None, "cables.csv has no row %s (module %s)" % (e["usb"], e["mb"])
        e.update(usb_cable=c_["선"], usb_port=c_["한쪽"])
    # harness (optional, hardware/pcb/netlist/harness.csv): conductor colour and cut length of each key's own wire
    hpath = os.path.join(pcb, "netlist", "harness.csv")
    if os.path.exists(hpath):
        HN = read_csv(hpath)
        hk = list(HN[0].keys()) if HN else []

        def hrow(wid, core=None, net=None):
            for x in HN:
                if x.get(hk[0]) != wid:
                    continue
                if core is not None and str(x.get("심 번호", "")).strip() != str(core):
                    continue
                if net is not None and not str(x.get("넷", "")).startswith(net):
                    continue
                return {k: x[k] for k in hk if k in ("W", "이름", "선", "심 번호", "색", "넷", "끝 A", "A 핀", "끝 B", "B 핀", "자르는 길이")}
            return None
        for e in keys:
            w = []
            if e["ribbon"]:
                w.append(hrow("W101~W107", core=e["j_pin"]))
            elif e["part"] == "EL":
                w += [hrow("W401", net=e["net"]), hrow("W403", net=e["net"])]
            else:
                w += [hrow("W411", net=e["net"]), hrow("W413", net=e["net"])]
            e["wires"] = [x for x in w if x]
    pedal = pedal_path(rows, R_, PN, PNM, N_, bom_row, bcol, cables)
    # circuit revision of every sheet (hardware/pcb/netlist/sheets.json, written by build.py)
    SJ = json.load(open(os.path.join(pcb, "netlist", "sheets.json"), encoding="utf-8"))
    revs = sorted({(v.get("rev"), v.get("date")) for v in SJ.values()}, key=lambda q: (q[1] or "", q[0] or ""))
    circuit = dict(rev=revs[-1][0], date=revs[-1][1], src="hardware/pcb/netlist/sheets.json")
    return dict(keys=keys, scan=scan, scan_assume=scan_assume, sel_pins=sel_pins, power=power, cables=cables, pedal=pedal, circuit=circuit,
                mod_x0={f"O{k}": r(47.0 + 164.5 * (k - 1), 3) for k in range(1, 8)}, key_bed=dict(x0=0.0, x1=47.0 + 164.5 * 7 + 23.5, el=[0.0, 47.0], er=[1198.5, 1222.0]))


# =============================================================================== touchscreen fold (optional, from CAD solids)
def touch_fold(parts):
    """touchscreen fold (D05 poses: use 25 deg, heel contact 22 deg, folded 90 deg) from the CAD solids: the cradle, the
    screen and the window cover cut at x = XC + 40 (clear of the leg x606-616) in the use pose and taken back to the cradle
    frame (u, w) with touchscreen_rev3.inv; the page turns them about the hinge axis with touchscreen_rev3.pt.  The screen
    lid of the CU (CU-SCREENLID) at the same x is static; the leg (TS-LEG, cut at its own x611) is drawn in the use pose."""
    sys.path.insert(0, os.path.join(ROOT, "hardware", "mechanical", "cad", "src"))
    import touchscreen_rev3 as TS
    out = dict(axis=[TS.AX_Y, TS.AX_Z], axis_uw=[TS.AX_U, TS.AX_W], tilt_use=TS.TILT_USE, tilt_heel=TS.TILT_HEEL, tilt_fold=TS.TILT_FOLD,
               xc=TS.XC, glass=list(TS.GLASS), body_t=TS.BODY_T, parts=[], static=[], leg=None,
               src="hardware/mechanical/cad (build_all.collect, touchscreen_rev3.py)")
    xs = TS.XC + 40.0

    def section(sol, x):
        b = sol.bounding_box()
        if not (b[0] <= x <= b[3]):
            return []
        R = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x]], float)       # (x, y, z) -> (y, z, x - x0): slice at 0
        cs = sol.transform(R).slice(0.0)
        return [[(float(a), float(c)) for a, c in ring] for ring in cs.to_polygons()]
    byid = {p.id: p for p in parts}
    for pid in ("TS-CRADLE", "TS-E-SCREEN", "TS-WINCOVER"):
        p = byid[pid]
        rg = section(p.solid, xs)
        uw = [[[r(v, 3) for v in TS.inv(y, z, TS.TILT_USE)] for y, z in ring] for ring in rg]
        out["parts"].append(dict(id=p.id, name=p.name_ko, kind=p.kind, rings=uw))
    lid = byid.get("CU-SCREENLID")
    if lid is not None:
        out["static"].append(dict(id=lid.id, name=lid.name_ko, kind=lid.kind, rings=[[[r(y, 3), r(z, 3)] for y, z in ring] for ring in section(lid.solid, xs)]))
    leg = byid.get("TS-LEG")
    if leg is not None:
        out["leg"] = dict(id=leg.id, name=leg.name_ko, x=TS.XC, rings=[[[r(y, 3), r(z, 3)] for y, z in ring] for ring in section(leg.solid, TS.XC)])
    # pose check: the CAD's folded cradle (altview) = the use-pose cradle turned to 90 deg (z extents of the cut)
    f = byid.get("TS-CRADLE-FOLD")
    if f is not None:
        rg = section(f.solid, xs)
        zc = [z for ring in rg for _, z in ring]
        zm = [TS.pt(u, w, TS.TILT_FOLD)[1] for ring in out["parts"][0]["rings"] for u, w in ring]
        out["fold_check"] = dict(cad_z=[r(min(zc), 3), r(max(zc), 3)], turned_z=[r(min(zm), 3), r(max(zm), 3)])
    out["x_section"] = xs
    return out


def cad_check(parts, G, secs):
    """the exported rest outlines vs the CAD solids of module O1 (key D / C#, lever, magnet): y and z extents."""
    byid = {p.id: p for p in parts}

    def bb(rr_):
        ys = [q[0] for ring in rr_ for q in ring]
        zs = [q[1] for ring in rr_ for q in ring]
        return min(ys), max(ys), min(zs), max(zs)
    for colour, key, pid in (("white", "key D", "O1-KEY-D"), ("black", "key C#", "O1-KEY-Cs")):
        if pid not in byid:
            check(f"CAD part {pid} present", False)
            continue
        b = byid[pid].solid.bounding_box()
        allk = [p["side_rest"] for p in G["parts"] if p["body"] == key and p["part"] not in ("capstan head", "rest felt")]
        y0, y1, z0, z1 = bb(allk)
        d = max(abs(y0 - b[1]), abs(y1 - b[4]), abs(z0 - b[2]), abs(z1 - b[5]))
        check(f"CAD {pid} y/z extents = geometry.json {key} (rest)", d < 0.02, "max diff %.3f mm (CAD y%.2f~%.2f z%.2f~%.2f)" % (d, b[1], b[4], b[2], b[5]))
        mid = "O1-MAGNET-" + ("D" if colour == "white" else "Cs")
        if mid in byid:
            mb = byid[mid].solid.bounding_box()
            ms = secs[colour]["magnet_S"] + secs[colour]["magnet_N"]
            yy0, yy1, zz0, zz1 = bb([ms])
            dm = max(abs(yy0 - mb[1]), abs(yy1 - mb[4]), abs(zz0 - mb[2]), abs(zz1 - mb[5]))
            check(f"CAD {mid} = page magnet outline", dm < 0.02, "max diff %.3f mm" % dm)


# =============================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "report", "toccata-v4", "fin", "sim"))
    ap.add_argument("--cad-check", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    G = json.load(open(os.path.join(HERE, "geometry.json")))
    MT = json.load(open(os.path.join(HERE, "metrics.json")))
    g = m.build_geo(P)
    print("build_geo %.1f s, seat_k %s, z_shelf %.3f" % (time.time() - t0, g["seat_k"], g["z_shelf"]), flush=True)
    # the dynamics use the pad-seat stiffness of the VERIFIED run (metrics.json seat.k_min = geometry.json solved.seat_k min,
    # 1490 N/mm).  build_geo's plate FE can give another value on another numpy / scipy (here 1410): with the verified seat
    # every history below equals metrics.json to 6 digits (checked).
    seat_v = MT["seat"]["k_min"]
    check("seat_k of the verified run = floor(min(geometry.json solved.seat_k), 10)", seat_v == math.floor(min(G["solved"]["seat_k"].values()) / 10) * 10, "%s N/mm" % seat_v)
    if g["seat_k"] != seat_v:
        print("NOTE build_geo plate FE gives seat_k %s here (verified run %s): the export uses %s" % (g["seat_k"], seat_v, seat_v), flush=True)
    seat_fe_here = g["seat_k"]
    g["seat_k"] = seat_v
    check("z_shelf = geometry.json solved.z_shelf", abs(g["z_shelf"] - G["solved"]["z_shelf"]) < 1e-6, "%.3f" % g["z_shelf"])
    sens_m = MT["sensor"]
    out = dict(meta=dict(title="Toccata 건반 액션 시뮬레이션 데이터", model="hardware/mechanical/key-action-v4/model/model_v4.py (W1+ r4.5, Dyn 4-DOF, dt 0.004 ms)",
                         geometry="geometry.json (r4.5) side outlines at the balance-pin plane (= drawings d01 / d02)",
                         generated=time.strftime("%Y-%m-%d %H:%M"), units="mm, ms, N, deg; y from the white-key front lip, z from the desk",
                         seat_k=seat_v, seat_k_note="pad-seat stiffness of the verified run (metrics.json seat.k_min); build_geo here gave %s" % seat_fe_here, pad="design pad (micro-cell urethane 6T + felt 1T: P pad_E, pad_h, e_eff %.2f)" % P["pad_e"],
                         script="hardware/mechanical/key-action-v4/model/export_sim.py"),
               sensor=dict(SENS, formula="B = Br/2 [(g+L)/sqrt(R²+(g+L)²) − g/sqrt(R²+g²)], OUT = 1.65 V + 30 mV/mT · B, ADC = OUT/3.3 V · 4096"),
               thresholds=TH, vmap=dict(VMAP, formula="vel = 1 + 126 ln(v/0.05)/ln(2.0/0.05), 1~127"), colours={})
    secs = {}
    for colour, A, key, lever, ze, cc in (("white", g["Aw"], "key D", "lever D", P["z_elem_w"], "w"), ("black", g["Ab"], "key C#", "lever C#", P["z_elem_b"], "b")):
        nm = key.split(" ")[1]
        # ---- design points of the model = geometry.json key_points (same design)
        kpj = G["key_points"]["white D" if colour == "white" else "black C#"]
        pts = {q["point"]: q for q in kpj["points"]}
        dd = max(abs(pts["key front top"]["rest"][0] - A.front[0]), abs(pts["key front top"]["rest"][1] - A.front[1]),
                 abs(pts["magnet face"]["rest"][0] - A.mag[0]), abs(pts["magnet face"]["rest"][1] - A.mag[1]),
                 abs(pts["key COM"]["rest"][0] - A.ck[0]), abs(pts["key COM"]["rest"][1] - A.ck[1]))
        check(f"{colour}: model key points = geometry.json key_points", dd < 0.006, "max %.4f" % dd)
        # ---- sensor gaps (model = README / SCH-02)
        tr, _ = A.mag_travel()
        g_rest, g_bot = A.mag[1] - ze, A.mag[1] - tr - ze
        check(f"{colour}: rest gap {g_rest:.2f} = metrics sensor.rest", abs(g_rest - sens_m[colour]["rest"]) < 1e-6)
        check(f"{colour}: rigid bottom gap {g_bot:.4f} = metrics sensor.bottom", abs(g_bot - sens_m[colour]["bottom"]) < 1e-5)
        # ---- dynamics
        D = m.dyn_for(g, A)
        st = D.run(300.0)["state"]
        rest = dict(th=st[0], b=st[1], cy=st[2][0], cz=st[2][1])
        mag_rest, mag_bot = A.mag[1], A.kp(A.mag, A.a_dip)[1]
        frz = m.key_point_world(A, st, A.front)[1]
        md = MT["dyn"][colour]
        check(f"{colour}: settled rest b = metrics dyn.rest_b", abs(math.degrees(st[1]) - md["rest_b"]) < 1e-4, "%.4f deg" % math.degrees(st[1]))
        check(f"{colour}: settled rest front z = metrics dyn.rest_front", abs(frz - md["rest_front"]) < 1e-4, "%.4f" % frz)
        v0p = m.v0_for_front(D, st, P["v_play"])
        check(f"{colour}: v0 for 1.5 m/s = metrics dyn.v0_play", abs(v0p - md["v0_play"]) < 1e-5, "%.6f" % v0p)
        evr = m.release_from_bottom(D, st)
        # metrics.json was written by run_all on the W1 machine: a crossing may land one 4 us step apart here
        check(f"{colour}: release t50 (1.2 s hold) = metrics within 0.01 ms", abs(evr["t50"] - md["t50"]) < 0.01, "%.3f / %.3f ms" % (evr["t50"], md["t50"]))
        check(f"{colour}: release t100 (1.2 s hold) = metrics within 0.01 ms", abs(evr["t100"] - md["t100"]) < 0.01, "%.3f / %.3f ms" % (evr["t100"], md["t100"]))
        gap_rest_settled = m.key_point_world(A, st, A.mag)[1] - ze
        cols = dict(name=("백건 D" if colour == "white" else "흑건 C#"), key=nm, K=list(P["K"]), L=list(P["L"]),
                    ck0=[r(A.ck[0], 6), r(A.ck[1], 6)], front=[r(v, 4) for v in A.front], finger=[r(v, 4) for v in A.finger],
                    mag=[r(v, 4) for v in A.mag], capstan=[r(A.y_cap, 3), r(P["z_c"], 3)], y_elem=P["y_elem"], z_elem=ze,
                    mag_rest_z=r(mag_rest, 6), mag_bot_z=r(mag_bot, 6), travel_mag=r(mag_rest - mag_bot, 4),
                    gap_rest_design=r(g_rest, 4), gap_bottom_rigid=r(g_bot, 4), gap_rest_settled=r(gap_rest_settled, 4),
                    gap_over_max=r(sens_m[colour]["ff"], 4), dip=(P["dip_b"] if A.black else P["dip_w"]),
                    gap_rearm=r(g_bot + TH["rearm"] * (g_rest - g_bot), 4), gap_noteon=r(g_bot + TH["noteon"] * (g_rest - g_bot), 4),
                    front_rest_z=r(frz, 4), rest=dict(th=r(rest["th"], 8), b=r(rest["b"], 8), cy=r(rest["cy"], 6), cz=r(rest["cz"], 6)),
                    a_dip=r(A.a_dip, 6), b_dip=r(A.b_dip, 6),
                    adc=dict(rest_design=int(round(adc_of_gap(g_rest))), bottom_rigid=int(round(adc_of_gap(g_bot))),
                             over_max=int(round(adc_of_gap(sens_m[colour]["ff"]))), rearm=int(round(adc_of_gap(g_bot + TH["rearm"] * (g_rest - g_bot)))),
                             noteon=int(round(adc_of_gap(g_bot + TH["noteon"] * (g_rest - g_bot)))), rest_settled=int(round(adc_of_gap(gap_rest_settled)))),
                    field=dict(rest=r(field_mT(g_rest), 2), bottom=r(field_mT(g_bot), 2), over=r(field_mT(sens_m[colour]["ff"]), 2)))
        # the 1 N settled bottom with the pad (geometry.json key side_dip): magnet gap and ADC (README: 5.52 / 5.47, 2890 / 2907)
        hp = g["held_pad_w" if colour == "white" else "held_pad_b"] if ("held_pad_" + cc) in g else None
        if hp is None:
            hp = m.held_bottom(A, g["z_shelf"], 1.0, pad=g["pad_" + cc], seat_k=g["seat_k"])[0]
        gap_held = m.key_point_world(A, hp, A.mag)[1] - ze
        cols["gap_held_1N"] = r(gap_held, 4)
        cols["adc"]["held_1N"] = int(round(adc_of_gap(gap_held)))
        # ---- metrics numbers shown on the page (copied, not retyped)
        mt = MT["metrics"]
        cols["metrics"] = dict(DW=r(MT[colour]["DW"], 2), UW=r(MT[colour]["UW"], 2), BW=r(MT[colour]["BW"], 2), friction=r(MT[colour]["friction"], 2),
                               t50=md["t50"], t100=md["t100"], rep_hz=r(md["rep"], 2), t50_2f=md["t50_2f"], rep_2f=r(md["rep_2f"], 2),
                               v0_play=r(md["v0_play"], 5), up_play=r(md["play_h1.00"]["up_peak"], 3), up_abuse=r(md["abuse_h1.00"]["up_peak"], 3),
                               spring_T_rest=r(MT[colour]["spring_T_rest"], 3), spring_T_bottom=r(MT[colour]["spring_T_bottom"], 3),
                               meff=r(MT[colour]["meff"], 2), key_g=r(MT[colour]["key_g"], 2), lever_g=r(MT[colour]["lever_g"], 2), steel_g=r(MT[colour]["steel_g"], 2),
                               carrier_g=r(MT[colour]["carrier_g"], 2), lever_rest_g=r(MT[colour]["lever_g"] - MT[colour]["steel_g"] - MT[colour]["carrier_g"], 2),
                               mag_travel=r(sens_m[colour]["travel"], 4), sensor_rest=sens_m[colour]["rest"], sensor_bottom=r(sens_m[colour]["bottom"], 4),
                               sensor_ff=r(sens_m[colour]["ff"], 4))
        # lever mass breakdown (lever_g already contains the steel block): steel + printed carrier + felt strip + spring + the
        # MS-polymer bond film (every lever body element whose density is none of PETG / steel / felt / SUS304)
        felt_g, spr_g = A.lev.mass_of(m.RHO_FELT), A.lev.mass_of(m.RHO_SUS)
        bond_g = sum(e["m"] for e in A.lev.el if e.get("rho") not in (m.RHO_PETG, m.RHO_ST, m.RHO_FELT, m.RHO_SUS))
        lsum = MT[colour]["steel_g"] + MT[colour]["carrier_g"] + felt_g + spr_g + bond_g
        check(f"{colour}: lever {MT[colour]['lever_g']:.2f} g = steel + carrier + felt strip + spring + bond film", abs(lsum - MT[colour]["lever_g"]) < 0.01,
              "%.2f + %.2f + %.2f + %.2f + %.2f = %.2f g" % (MT[colour]["steel_g"], MT[colour]["carrier_g"], felt_g, spr_g, bond_g, lsum))
        cols["metrics"].update(felt_strip_g=r(felt_g, 2), spring_g=r(spr_g, 3), bond_g=r(bond_g, 2))
        cols["metrics_global"] = dict(min_sensor_gap=r(mt["min_sensor_gap_mm"], 3), ghost_settle_max_ms=r(mt["ghost_settle_max_ms"], 1),
                                      ghost_armed=mt["ghost_armed"], ghost_cases=mt["ghost_cases"], ghost_not_dropped=mt["ghost_not_dropped"])
        # ---- geometry of the section
        xsec = [q for q in G["plan"] if q["part"] == f"{key} balance pin"][0]["circle"][0]
        extra = ("key C", "key D") if A.black else ()
        sec = section_geometry(G, A, colour, key, lever, xsec, extra_keys=extra)
        secs[colour] = sec
        cols["section"] = sec
        # ---- runs
        # settled rest forces (capstan carries the lever, rest felt carries the key): last step of a short rest run
        ev_rest = D.run(0.2, state=st, record=True, rec_every=1)
        h0 = ev_rest["hist"][-1]
        rest_row = [st[0], st[1], st[2][0], st[2][1], gap_rest_settled, frz, h0[4], h0[8], h0[9], h0[7], 0.0]
        cols["rest_forces"] = dict(Nc=r(h0[4], 4), fre=r(h0[7], 4), fup=r(h0[8], 4), ffr=r(h0[9], 4))
        runs = []
        cases = [("push", None, 0.8)] + [("strike", v, None) for v in (0.5, 0.7, 1.0, 1.5, 2.5)]
        PRE = 5.0
        for kind, v, F in cases:
            t1 = time.time()
            ev, meta, data, cerr, s0 = run_case(D, st, kind, v_target=v, F_push=F)
            check(f"{colour} {kind} {v or F}: key COM replay = model state", cerr < 1e-9, "%.1e mm" % cerr)
            s, gap, fz, fr, idx = summarize(A, colour, meta, data, ev, st, mag_rest, mag_bot, ze, frz, PRE)
            if kind == "strike":
                check(f"{colour} {v} m/s: front speed at the felt = target", abs(ev["v_front_bottom"] - v) < 0.01 * v, "%.4f" % ev["v_front_bottom"])
            # metrics cross-checks (same finger profile until the release)
            if kind == "push":
                q = md["pp"]
                vb_ok = (ev["v_front_bottom"] is None and q["v_front_bottom"] is None) or (
                    ev["v_front_bottom"] is not None and q["v_front_bottom"] is not None and abs(ev["v_front_bottom"] - q["v_front_bottom"]) < 1e-6)
                check(f"{colour} pp push 0.8 N = metrics dyn.pp (v_front_bottom, up_peak)", vb_ok and abs(s["up_peak"] - q["up_peak"]) < 1e-3,
                      "%s / %.3f (metrics %s / %.3f)" % (ev["v_front_bottom"], s["up_peak"], q["v_front_bottom"], q["up_peak"]))
            if kind == "strike" and v in (1.5, 2.5):
                q = md["play_h1.00" if v == 1.5 else "abuse_h1.00"]
                ok = (abs(ev["v_front_bottom"] - q["v_front_bottom"]) < 1e-6 and abs(s["up_peak"] - q["up_peak"]) < 1e-3
                      and abs(s["cap_peak"] - q["cap_peak"]) < 1e-3 and abs(s["front_peak"] - q["front_peak"]) < 1e-3)
                check(f"{colour} {v} m/s hold 1 N = metrics dyn.{'play' if v == 1.5 else 'abuse'}_h1.00 (until the release)", ok,
                      "up %.3f/%.3f cap %.3f/%.3f front %.3f/%.3f" % (s["up_peak"], q["up_peak"], s["cap_peak"], q["cap_peak"], s["front_peak"], q["front_peak"]))
            # ---- decimate for the page
            th, b = data["th"], data["b"]
            Y = np.column_stack([th, b, data["cy"], data["cz"], gap, fz, data["Nc"], data["fup"], data["ffr"], data["fre"], data["Ff"]])
            tol = np.array([1.2e-5, 2.0e-5, 0.002, 0.002, 0.002, 0.003, 0.05, 0.25, 0.1, 0.05, 0.01])
            keep = decimate(data["t"], Y, tol, keep_idx=list(idx.values()), max_dt=1.0)
            # page arrays: two identical prefix rows = the settled rest state at t = 0 and at t = PRE (the run itself starts at
            # t = PRE with the finger force as a step, model run_case): linear interpolation then holds the rest values over 0..PRE
            arr = {}
            names = ["th", "b", "cy", "cz", "gap", "fz", "Nc", "fup", "ffr", "fre", "Ff"]
            nd = [7, 7, 5, 5, 4, 4, 3, 3, 3, 3, 3]
            for j, (nm_, n_) in enumerate(zip(names, nd)):
                arr[nm_] = [round(float(rest_row[j]), n_)] * 2 + [round(float(x), n_) for x in Y[keep, j]]
            arr["t"] = [0.0, PRE] + [round(float(x), 3) for x in data["t"][keep] + PRE]
            assert arr["t"][2] > PRE, "first run sample after PRE"
            runs.append(dict(id=(f"push{F:g}" if kind == "push" else f"v{v:g}"), label=(f"{F:g} N로 누름 (pp)" if kind == "push" else f"{v:g} m/s"),
                             meta={k: (r(vv, 6) if isinstance(vv, float) else vv) for k, vv in meta.items()}, events=s,
                             idx={k: (None if vv is None else 2 + int(np.searchsorted(keep, vv))) for k, vv in idx.items()},
                             n_raw=int(len(data["t"])), n=len(keep) + 2, data=arr))
            print("   %s %-8s %5d -> %4d samples, t_end %.1f ms, %.1f s" % (colour, runs[-1]["id"], len(data["t"]), len(keep), data["t"][-1], time.time() - t1), flush=True)
        cols["runs"] = runs
        # the settled rest forces (for the t = 0 prefix the page holds the first sample before the run starts)
        out["colours"][colour] = cols
    # ---- sensor law vs README / SCH-02 table
    W, Bk = out["colours"]["white"], out["colours"]["black"]
    check("ADC rest 2207 / 2138 (README)", W["adc"]["rest_design"] == 2207 and Bk["adc"]["rest_design"] == 2138, "%d / %d" % (W["adc"]["rest_design"], Bk["adc"]["rest_design"]))
    check("ADC re-arm 2373 / 2282 (README)", W["adc"]["rearm"] == 2373 and Bk["adc"]["rearm"] == 2282, "%d / %d" % (W["adc"]["rearm"], Bk["adc"]["rearm"]))
    check("ADC 1 N bottom 2890 / 2907 (README)", W["adc"]["held_1N"] == 2890 and Bk["adc"]["held_1N"] == 2907, "%d / %d" % (W["adc"]["held_1N"], Bk["adc"]["held_1N"]))
    check("gap 1 N bottom 5.52 / 5.47 (README)", round(W["gap_held_1N"], 2) == 5.52 and round(Bk["gap_held_1N"], 2) == 5.47, "%.3f / %.3f" % (W["gap_held_1N"], Bk["gap_held_1N"]))
    # README 9.34 = 5.32 + 8.03 / 2 from the rounded table values; exact 9.334 (white 8.208): within 0.01
    check("re-arm gap 8.21 / 9.34 (README, rounded inputs) within 0.01", abs(W["gap_rearm"] - 8.21) < 0.01 and abs(Bk["gap_rearm"] - 9.34) < 0.01,
          "%.3f / %.3f" % (W["gap_rearm"], Bk["gap_rearm"]))
    dw, db = W["adc"]["bottom_rigid"] - 2862, Bk["adc"]["bottom_rigid"] - 2962
    check("ADC rigid bottom about 2862 / 2962 (README, within 5 codes)", abs(dw) <= 5 and abs(db) <= 5, "%d / %d (diff %+d / %+d)" % (W["adc"]["bottom_rigid"], Bk["adc"]["bottom_rigid"], dw, db))
    check("field rest / bottom 4.3 / 21.9, 2.4 / 24.6 mT (SCH-02)", round(W["field"]["rest"], 1) == 4.3 and round(W["field"]["bottom"], 1) == 21.9
          and round(Bk["field"]["rest"], 1) == 2.4 and round(Bk["field"]["bottom"], 1) == 24.6,
          "%.2f / %.2f, %.2f / %.2f" % (W["field"]["rest"], W["field"]["bottom"], Bk["field"]["rest"], Bk["field"]["bottom"]))
    # ---- system data
    SYS = system_data()
    check("88 keys mapped", len(SYS["keys"]) == 88 and len({k["midi"] for k in SYS["keys"]}) == 88)
    k60 = [k for k in SYS["keys"] if k["midi"] == 60][0]
    check("C4 = O4 U201 C0", k60["mb"] == "O4" and k60["sensor"] == "U201" and k60["mux_ch"] == "C0", json.dumps({x: k60[x] for x in ("mb", "sensor", "mux_ch")}))
    a0 = [k for k in SYS["keys"] if k["midi"] == 21][0]
    c8 = [k for k in SYS["keys"] if k["midi"] == 108][0]
    check("A0 = EL U401 -> O1 EXT1 C12, C8 = ER U411 -> O7 EXT1 C12", a0["mb"] == "O1" and a0["mux_ch"] == "C12" and c8["mb"] == "O7" and c8["mux_ch"] == "C12",
          "%s %s %s / %s %s %s" % (a0["sensor"], a0["ext"], a0["mux_ch"], c8["sensor"], c8["ext"], c8["mux_ch"]))
    unnamed = sorted({it["part"] for c_ in secs.values() for g_ in c_["fixed"].values() for it in g_ if not it.get("ko")})
    check("every drawn fixed part has a Korean final-part name (hover title)", not unnamed, ", ".join(unnamed))
    check("circuit revision from hardware/pcb/netlist/sheets.json", bool(SYS["circuit"]["rev"]), "개정 %s (%s)" % (SYS["circuit"]["rev"], SYS["circuit"]["date"]))
    check("pedal path from the SCH-05 netlist (W502 -> J502 -> R501 -> GP26)", any("J502" in q for q in SYS["pedal"]["path"]) and any("GP26" in q for q in SYS["pedal"]["path"]),
          " | ".join(SYS["pedal"]["path"][1:4]))
    no_rt = [k["name"] for k in SYS["keys"] if not any("A302" in w["a"] or "A302" in w["b"] for w in k["mb_route"])]
    check("every key has a wiring_MB.csv segment touching the mux A302 (page row '제어 기판 배선')", not no_rt, ", ".join(no_rt) or "88 / 88")
    CBL = SYS["cables"]
    miss = [w for w in ("W201", "W202", "W203", "W204", "W205", "W206", "W207", "W208", "W209") if w not in CBL]
    check("cables.csv has one row per USB cable W201~W209", not miss, ", ".join(miss) or
          " · ".join("%s %s (%s)" % (w, CBL[w]["선"].split()[-2] + " " + CBL[w]["선"].split()[-1], CBL[w]["한쪽"]) for w in ("W201", "W202", "W203", "W204", "W205", "W206", "W207", "W208")))
    bad_usb = [k["name"] for k in SYS["keys"] if k.get("usb_cable") != CBL.get(k["usb"], {}).get("선") or k.get("usb_port") != CBL.get(k["usb"], {}).get("한쪽")]
    check("each key's USB cable / hub port (page row 'USB') = cables.csv row of its module", not bad_usb, ", ".join(bad_usb) or
          ", ".join(sorted({"%s %s %s" % (k["mb"], k["usb"], k["usb_cable"]) for k in SYS["keys"]})))
    w208 = CBL.get("W208", {})
    check("pedal path names W208 with its cables.csv cable and hub port", any(("W208 (%s) → %s" % (w208.get("선"), w208.get("한쪽"))) in q for q in SYS["pedal"]["path"]),
          [q for q in SYS["pedal"]["path"] if "W208" in q][0] if any("W208" in q for q in SYS["pedal"]["path"]) else "no W208 line")
    # the page must take the USB lengths from system.json, not from its own text
    js_p = os.path.join(ROOT, "docs", "report", "toccata-v4", "src", "tabs", "sim", "script.js")
    if os.path.exists(js_p):
        import re as _re
        js = open(js_p, encoding="utf-8").read()
        hard = _re.findall(r"USB-A → C \d", js)
        check("page script has no hard-coded USB cable length (reads k.usb_cable / k.usb_port)", not hard and "k.usb_cable" in js and "k.usb_port" in js,
              ", ".join(hard) or "ok")
    fz_ = SYS["power"]["fuse"]
    check("fuse F601 = bom.csv value (ATO blade)", "ATO" in fz_["value"], fz_["value"])
    b = SYS["power"]["budget"]
    check("power avg 15.72~19.72 W, peak 33.72 W, run 4.40~3.50 h (SCH-06)", abs(b["avg"][0] - 15.72) < 0.01 and abs(b["avg"][1] - 19.72) < 0.01
          and abs(b["peak"] - 33.72) < 0.01 and abs(b["run"][0] - 4.40) < 0.01 and abs(b["run"][1] - 3.50) < 0.01, json.dumps(b))
    parts = None
    if a.cad_check:
        sys.path.insert(0, os.path.join(ROOT, "hardware", "mechanical", "cad", "src"))
        os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))
        import build_all                                       # collect() only: never main() (it rewrites stl/print)
        t1 = time.time()
        parts = build_all.collect()
        print("collect(): %d parts, %.1f s" % (len(parts), time.time() - t1), flush=True)
        cad_check(parts, G, secs)
        try:
            SYS["touch"] = touch_fold(parts)
            fc = SYS["touch"].get("fold_check", {})
            okf = bool(fc) and abs(fc["cad_z"][0] - fc["turned_z"][0]) < 0.05 and abs(fc["cad_z"][1] - fc["turned_z"][1]) < 0.05
            check("touchscreen fold: use-pose cradle turned to 90 deg = CAD folded cradle (z of the cut)", okf, json.dumps(fc))
        except Exception as e:                                 # optional
            check("touchscreen fold outlines from CAD", False, repr(e))
    os.makedirs(a.out, exist_ok=True)
    out["checks"] = [dict(name=n, ok=o, detail=d) for n, o, d in CHECKS]
    p1 = os.path.join(a.out, "keyaction.json")
    with open(p1, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    p2 = os.path.join(a.out, "system.json")
    with open(p2, "w", encoding="utf-8") as f:
        json.dump(SYS, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote %s (%.0f kB), %s (%.0f kB); %d checks, %d failed; %.0f s" % (p1, os.path.getsize(p1) / 1024, p2, os.path.getsize(p2) / 1024,
                                                                          len(CHECKS), sum(1 for c in CHECKS if not c[1]), time.time() - t0))
    return 0 if all(c[1] for c in CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
