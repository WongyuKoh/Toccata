"""Interference check of the rev-3 B1 preview model (mesh booleans, manifold3d).

  poses: 22 deg (heel on the stop, leg hanging on the pocket), 25 deg (use, leg foot in the pocket corner), 90 deg (folded,
         leg clipped on the cradle back), and a sweep 22..90 deg in 1 deg steps with the leg clipped (the way it is folded).
  pairs: every moving part x every fixed part, moving x moving, cables x everything; keep-out box over the key modules.
  result: model3d/interference.json (+ printed summary). Expected contacts (by design) are listed with the reason.
"""
import json
import math
import os
import re
import time

import numpy as np

import b1model as B
from cadlib import box

HERE = os.path.dirname(os.path.abspath(__file__))
TOL_V = 1e-3          # mm3 below this = touching, not interfering
GAP_SEARCH = 3.0

MOVING = re.compile(r"^TS-(SCREEN|CRADLE|WINCOVER|M25|LEG|M3X20-LEG)")
CABLE = re.compile(r"^TS-(FFC|PWR)")

# (regex a, regex b, poses or None, reason, zone) - order-independent.
# zone = None: the whole overlap is by design; zone = "touch": only touching allowed (overlap > TOL is an interference);
# zone = f(theta) -> world Manifold: overlap inside the zone is by design, overlap outside it is reported as an interference.
def _far_cheek_leg(theta):
    """leg axle thread zone: the far clevis cheek (xr5.3~11.3) only."""
    pu, pw = B.PIV_UW
    a, b = B.LG["clevis"]["far"]
    return B.place(box(a - 0.01, b + 0.01, pu - 2.0, pu + 2.0, pw - 2.0, pw + 2.0), theta)


def _far_cheeks_hinge(theta):
    out = []
    for side in ("left", "right"):
        a, b = B.HG[side]["far_cheek"]
        out.append(box(B.XC + a - 0.01, B.XC + b + 0.01, B.AY - 2.0, B.AY + 2.0, B.AZ - 2.0, B.AZ + 2.0))
    return B.union(out)


EXPECTED = [
    (r"TS-CRADLE$", r"TS-SCREEN$", None, "보스·채움 블록 면이 화면 뒷면(w8)에, 아래 벽 안쪽 면(u0)이 유리 아래 끝에 닿음", "touch"),
    (r"TS-CRADLE$", r"TS-SCREEN-BEZEL", None, "유리 아래 끝이 아래 벽 안쪽 면(u0)에 얹힘", "touch"),
    (r"TS-CRADLE$", r"TS-WINCOVER", None, "점검창 덮개 턱이 뒷판 뒷면(w13)에 얹힘", "touch"),
    (r"TS-CRADLE$", r"TS-M25", None, "M2.5 머리가 보스 자리(w11)에 닿음", "touch"),
    (r"TS-CRADLE$", r"TS-M3X20-LEG", None, "다리 축 M3가 먼 볼 Ø2.5에만 나사산을 냄 (물림 5.4) — 그 밖의 겹침은 간섭", _far_cheek_leg),
    (r"TS-LID$", r"TS-M3X20-HINGE", None, "경첩 축 M3가 먼 볼 Ø2.5에만 나사산을 냄 — 그 밖의 겹침은 간섭", _far_cheeks_hinge),
    (r"TS-LID$", r"TS-M3X10-LID", None, "뚜껑 나사 머리가 자리파기 바닥(z%.2f)에 닿음" % B.LS["head_seat_z"], "touch"),
    (r"TS-M3X10-LID", r"L2-INSERT", None, "뚜껑 나사가 레일 인서트에 %.0f 물림 (나사산)" % B.LS["insert_engage"], None),
    (r"TS-LID$", r"TS-RCLIP", None, "클립 핀이 Ø%.1f 구멍에 들어감" % B.CLIP["pin_hole_d"], "touch"),
    (r"TS-LID$", r"TS-LEG", ["25", "22"], "다리 발이 주머니 바닥·뒷벽(25°) 또는 경사(22°)에 닿음", "touch"),
    (r"TS-LID$", r"TS-CRADLE$", ["22", "90"], "22°: 귀 뒤꿈치가 멈춤 블록 윗면에 닿음 / 90°: 받침 패드가 접이 받침 발에 얹힘", "touch"),
    (r"TS-FFC", r"TS-SCREEN-ZIF", None, "리본 끝이 화면 ZIF에 %.1f 꽂힘" % B.RB["screen_end_insert"], None),
    (r"TS-FFC", r"PI5-DISP1", None, "리본 끝이 Pi CAM/DISP 1에 %.1f 꽂힘" % B.RB["pi_end_insert"], None),
    (r"TS-FFC", r"TS-SCREEN$", None, "리본이 화면 뒷면(w8)에 눕혀 붙음", "touch"),
    (r"TS-FFC", r"TS-CRADLE$", None, "리본이 받침 안 벽 면에 닿음", "touch"),
    (r"TS-FFC", r"TS-RCLIP", None, "리본이 클립 윗면(z%.2f)에 눌려 물림" % B.CLIP["clamp_z"][0], "touch"),
    (r"TS-FFC", r"TS-LID$", None, "리본이 클립 자리 밑면(z%.2f)에 눌려 물림" % B.CLIP["clamp_z"][1], "touch"),
    (r"TS-FFC", r"PI5-HDMI", None, "리본이 안 쓰는 micro-HDMI 모서리에 얹힘 (HDMI는 추정 자리)", "touch"),
    (r"TS-PWR-(RED|BLK)", r"TS-SCREEN-MX", None, "전원선 끝이 MX1.25에 꽂힘", None),
    (r"TS-PWR-(RED|BLK)", r"TS-SCREEN$", None, "전원선이 화면 뒷면에 눕혀 붙음", "touch"),
    (r"TS-PWR-(RED|BLK)", r"TS-PWR-HOUSING", None, "선 끝이 점퍼 하우징에 들어감", None),
    (r"TS-PWR-HOUSING", r"PI5-GPIO", None, "점퍼 하우징이 GPIO 핀 받침 위에 끼워짐", "touch"),
    (r"TS-PWR-RED", r"TS-PWR-BLK", None, "두 선이 나란히 붙어 감", None),
    (r"TS-LEG", r"TS-M3X20-LEG", None, "다리 축 (Ø3.0 / 구멍 Ø3.3)", "touch"),
    (r"PI5-", r"PI5-", None, "Pi 부품끼리 (기판 위)", None),
    (r"L2-", r"L2-", None, "L2 잠정 외형끼리", None),
    (r"L2-", r"PI5-", None, "L2 잠정 외형과 Pi", None),
    (r"TS-SCREEN", r"TS-SCREEN", None, "화면 더미 부품끼리", None),
    (r"TS-M25", r"TS-SCREEN$", None, "M2.5가 화면 모서리 구멍에 들어감", "touch"),
]
# overlaps with parts whose position is only an estimate (not a design clash; listed separately with the open item)
ESTIMATE = [
    (r"TS-FFC", r"PI5-HEATSINK", "방열판 상자는 추정 자리이고 CAD 리본 지킴 구역(x%.0f부터)을 1.0 넘어 그려져 있음 → 실제 Pi 5로 확인 (사양 G-8)" % B.N["pi5"]["cad_disp1"]["keepout"]["x"][0]),
]


def expected(a, b, pose):
    for ra, rb, poses, why, zone in EXPECTED:
        if (re.search(ra, a) and re.search(rb, b)) or (re.search(ra, b) and re.search(rb, a)):
            if poses is None or pose in poses:
                return why, zone
    return None, None


def estimate_pair(a, b):
    for ra, rb, why in ESTIMATE:
        if (re.search(ra, a) and re.search(rb, b)) or (re.search(ra, b) and re.search(rb, a)):
            return why
    return None


def film_depth(x, v):
    """overlap thickness estimate = volume / (the two largest bbox sides)."""
    bb = x.bounding_box()
    d = sorted([bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]])
    return v / max(d[1] * d[2], 1e-9)


def bb_overlap(a, b, pad=0.0):
    A, Bb = a.bounding_box(), b.bounding_box()
    return all(A[i] - pad <= Bb[i + 3] and Bb[i] - pad <= A[i + 3] for i in range(3))


def ivol(a, b):
    if not bb_overlap(a, b):
        return 0.0
    return (a ^ b).volume()


def gap(a, b):
    if not bb_overlap(a, b, GAP_SEARCH):
        return None
    return a.min_gap(b, GAP_SEARCH)


def keepout_box():
    k = B.KEEP
    x0, x1 = B.BL2["overall"]["x"]
    return box(x0, x1, -50.0, k["y_max"], k["z_min"], 600.0)


def min_y_above(m, z):
    t = m.trim_by_plane((0, 0, 1), z)
    if t.is_empty():
        return None
    return t.bounding_box()[1]


def check_pose(tag, theta, leg="auto"):
    parts, info = B.touch_parts(theta, leg=leg)
    ctx = B.context_parts()
    allp = parts + ctx
    rows, inter, contacts, est = [], [], [], []
    names = {p.id: p.name for p in allp}
    for i in range(len(allp)):
        for j in range(i + 1, len(allp)):
            a, b = allp[i], allp[j]
            ma, mb = MOVING.search(a.id) or CABLE.search(a.id), MOVING.search(b.id) or CABLE.search(b.id)
            if not (ma or mb):
                continue                                   # fixed vs fixed: not part of this check
            v = ivol(a.solid, b.solid)
            g = None
            if v <= TOL_V:
                g = gap(a.solid, b.solid)
            why, zone = expected(a.id, b.id, tag)
            ew = estimate_pair(a.id, b.id)
            row = {"a": a.id, "b": b.id, "vol_mm3": round(v, 3), "a_ko": names[a.id], "b_ko": names[b.id]}
            if v > TOL_V:
                if ew:
                    est.append(dict(row, why=ew))
                elif why and zone is None:
                    contacts.append(dict(row, why=why))
                elif why and zone == "touch":
                    depth = film_depth(a.solid ^ b.solid, v)
                    if depth < 0.005:                      # coplanar faces: float rounding, not a real overlap
                        contacts.append(dict(row, why=why, touch=True, film_depth_um=round(depth * 1000, 2)))
                    else:
                        inter.append(dict(row, why=None, depth_est=round(depth, 3), note="닿기만 해야 하는데 겹침: " + why))
                elif why:
                    z = zone(theta)
                    vin = ivol(a.solid ^ b.solid, z)
                    vout = v - vin
                    if vout > TOL_V:
                        inter.append(dict(row, vol_mm3=round(vout, 3), vol_in_zone=round(vin, 3), why=None, note="허용 구역 밖 겹침: " + why))
                    else:
                        contacts.append(dict(row, why=why, zone_ok=True))
                else:
                    inter.append(dict(row, why=None))
            elif g is not None and g < 1e-3:
                if why:
                    contacts.append(dict(row, vol_mm3=0.0, touch=True, why=why))
                else:
                    inter.append(dict(row, vol_mm3=0.0, touch=True, why=None, note="맞닿음 (설계에 없는 닿음)"))
            elif g is not None and g < GAP_SEARCH:
                rows.append({"a": a.id, "b": b.id, "gap": round(g, 3), "a_ko": names[a.id], "b_ko": names[b.id]})
    ko = keepout_box()
    ko_hits = []
    fwd = {}
    for p in parts:
        if MOVING.search(p.id) or CABLE.search(p.id):
            v = ivol(p.solid, ko)
            if v > TOL_V:
                ko_hits.append({"part": p.id, "vol_mm3": round(v, 3)})
            my = min_y_above(p.solid, B.KEEP["z_min"])
            if my is not None:
                fwd[p.id] = round(my, 2)
    rows.sort(key=lambda r: r["gap"])
    moving_min = min(fwd[k] for k in fwd if MOVING.search(k))
    cable_min = min(fwd[k] for k in fwd if CABLE.search(k))
    return {"theta": theta, "leg": info.get("leg_mode"), "info": {k: (np.round(v, 2).tolist() if not isinstance(v, str) else v) for k, v in info.items()},
            "interferences": inter, "expected_contacts": contacts, "estimate_overlaps": est, "closest_gaps": rows[:25], "keepout_hits": ko_hits,
            "min_y_above_module_top": {"moving": moving_min, "cables": cable_min, "per_part": fwd}}


def sweep(step=1.0):
    """fold motion: leg clipped on the cradle back, 22 -> 90 deg; cradle group + cables vs the fixed body and the keep-out."""
    loc = {"cradle": B.cradle_local(), "cover": B.cover_local(), "leg": B.leg_local_stowed(), "axle": B.leg_axle_local()}
    S = B.screen_local()
    loc.update({"screen": B.union([S["body"], S["bezel"], S["active"], S["zif"], S["mx"], S["tab"]])})
    loc["m25"] = B.union(B.m25_local())
    lid = B.lid_world()
    fixed = {"TS-LID": lid}
    for side, s in B.hinge_axles_world():
        fixed["TS-M3X20-HINGE-" + side[0].upper()] = s
    for p in B.context_parts():
        if p.id.startswith("L2-") and p.id not in ("L2-FEET",):
            fixed[p.id] = p.solid
    fixed["TS-RCLIP"] = B.ribbon_clip_world()
    ko = keepout_box()
    out = []
    worst = {"min_gap_to_lid": (9e9, None, None), "min_y_moving": (9e9, None), "min_y_cable": (9e9, None)}
    th = B.TH_HEEL
    while th <= B.TH_FOLD + 1e-9:
        mv = {k: B.place(v, th) for k, v in loc.items()}
        rb = B.ribbon_parts(th)["solid"]
        wr = B.wire_parts(th)
        cab = {"TS-FFC": rb, "TS-PWR": B.union([wr["red"], wr["black"]])}
        hits = []
        gaps = {}
        for mk, m in mv.items():
            for fk, f in fixed.items():
                v = ivol(m, f)
                if v > TOL_V:
                    why = expected("TS-" + mk.upper(), fk, "%d" % round(th))[0] if mk == "cradle" else None
                    if mk == "cradle" and fk == "TS-LID" and abs(th - 90) > 1e-6 and abs(th - 22) > 1e-6:
                        why = None
                    hits.append({"moving": mk, "fixed": fk, "vol_mm3": round(v, 3), "why": why})
            g = gap(m, lid)
            if g is not None:
                gaps[mk] = round(g, 3)
        for ck, c in cab.items():
            v = ivol(c, lid)
            if v > TOL_V:
                hits.append({"moving": ck, "fixed": "TS-LID", "vol_mm3": round(v, 3), "why": None})
        allm = B.union(list(mv.values()))
        kv = ivol(allm, ko) + sum(ivol(c, ko) for c in cab.values())
        my = min_y_above(allm, B.KEEP["z_min"])
        cy = min(v for v in (min_y_above(c, B.KEEP["z_min"]) for c in cab.values()) if v is not None)
        gl = min(gaps.values()) if gaps else None
        if gl is not None and gl < worst["min_gap_to_lid"][0] and abs(th - 22) > 1e-6 and abs(th - 90) > 1e-6:
            worst["min_gap_to_lid"] = (gl, th, min(gaps, key=gaps.get))
        if my is not None and my < worst["min_y_moving"][0]:
            worst["min_y_moving"] = (my, th)
        if cy < worst["min_y_cable"][0]:
            worst["min_y_cable"] = (cy, th)
        out.append({"theta": round(th, 2), "hits": hits, "gap_to_lid": gaps, "keepout_vol": round(kv, 4),
                    "min_y_moving_above_top": round(my, 2) if my is not None else None, "min_y_cables_above_top": round(cy, 2)})
        th += step
    return out, worst


def _bisect(f, lo, hi, n=14):
    """largest x in [lo, hi] with f(x) True (f monotone: True .. False)."""
    for _ in range(n):
        mid = (lo + hi) / 2
        if f(mid):
            lo = mid
        else:
            hi = mid
    return lo


def ear_checks(lid):
    """3a ear outline (numbers cradle.ear.profile_uw) vs the heel stop block + ear-slot floor, 22..90 deg; and the first rev-3 lobe."""
    sides = ("left", "right")
    slot = B.union([box(B.HG["ear_slot_x"][sd][0] + 0.1, B.HG["ear_slot_x"][sd][1] - 0.1, B.AY - 20, B.AY + 20, B.LID_BED, B.AZ + 20) for sd in sides])
    lid_slot = lid ^ slot

    def ears(pts):
        return B.union([B.prism_x(pts, *B.HG[sd]["ear"]) for sd in sides])
    e3a = ears(B.ear_profile()[0])
    res = {}
    at22 = B.place(e3a, B.TH_HEEL)
    res["overlap_22_mm3"] = round(ivol(at22, lid_slot), 4)
    res["gap_22"] = round(at22.min_gap(lid_slot, 3.0), 3)
    best, th = (9e9, None), 22.0
    fine = []
    while th <= 90.0 + 1e-9:
        m = B.place(e3a, th)
        v = ivol(m, lid_slot)
        g = m.min_gap(lid_slot, 3.0) if v <= TOL_V else -1.0
        if th >= B.TH_USE - 1e-9 and g < best[0]:
            best = (round(g, 3), round(th, 2))
        if th <= 25.0 + 1e-9:
            fine.append((round(th, 2), round(g, 3), round(v, 4)))
        th += 0.25 if th < 25.0 - 1e-9 else 0.5
    res["min_gap_25_90"] = best
    res["gap_22_to_25"] = fine
    res["design"] = {"gap_at_22": B.EAR["check"]["gap_at_22"], "min_gap_25_90": B.EAR["check"]["min_gap_25_90"], "rule": B.EAR["check"]["rule"]}
    res["ok"] = res["overlap_22_mm3"] <= TOL_V and best[0] >= 0.3
    # the first rev-3 outline (extra lobe point): the same mesh check must catch it
    e1 = ears(B.ear_profile_rev3_first())
    old = {}
    for t in (22.0, 25.0, 30.0):
        m = B.place(e1, t)
        v = ivol(m, lid_slot)
        dz = _bisect(lambda z: ivol(m.translate((0, 0, z)), lid_slot) > TOL_V, 0.0, 5.0) if v > TOL_V else 0.0
        old["%g" % t] = {"overlap_mm3": round(v, 3), "depth_z": round(dz, 2)}
    t = 25.0
    while t < 70.0 and ivol(B.place(e1, t), lid_slot) > TOL_V:
        t += 0.1
    old["clears_from_deg"] = round(t, 1)
    old["design_says"] = {k: B.EAR["check"]["rev3_first_lobe"][k] for k in ("gap_at_22", "gap_at_25", "clears_from_deg")}
    res["rev3_first_lobe"] = old
    return res


def axle_checks():
    """leg axle M3x20 ISO 7380 from -x: seated overlap only in the far cheek (thread); the way in (head dia over the whole
    length outside the near cheek) is free; gap to the nearest rib. Also the first rev-3 cradle (u30 rib) for comparison."""
    near0 = B.LG["clevis"]["near"][0]
    pu, pw = B.PIV_UW
    a, b = B.LG["clevis"]["far"]
    far = box(a - 0.01, b + 0.01, pu - 2, pu + 2, pw - 2, pw + 2)
    ax = B.leg_axle_local()
    path = B.leg_axle_path_local()

    def one(crl):
        tot = ivol(crl, ax)
        v_far = ivol(crl ^ ax, far) if tot > TOL_V else 0.0
        rest = crl.trim_by_plane((-1.0, 0.0, 0.0), -(near0 - 0.02))
        vp = ivol(path, crl)
        pth = path.trim_by_plane((-1.0, 0.0, 0.0), -(near0 - 0.02))
        g_all = pth.min_gap(rest, 6.0)
        ribs = rest.trim_by_plane((0.0, 0.0, 1.0), B.PLO + 0.05)          # back ribs / pads / bosses only (w > 13.05)
        g = pth.min_gap(ribs, 6.0)
        return {"seated_thread_far_cheek_mm3": round(v_far, 3), "seated_elsewhere_mm3": round(tot - v_far, 3),
                "path_overlap_mm3": round(vp, 3), "path_gap_to_ribs": round(g, 3), "path_gap_to_back_plate_w13": round(g_all, 3)}
    res = {"3a": one(B.cradle_local())}
    keep = list(B.CR["cross_ribs_u"])
    B.CR["cross_ribs_u"] = [30.0, keep[1]]
    try:
        res["rev3_u30_rib"] = one(B.cradle_local())
    finally:
        B.CR["cross_ribs_u"] = keep
    res["design"] = {"head_gap": B.CR["axle_check"]["min_head_gap"], "path_gap": B.CR["axle_check"]["min_path_gap"],
                     "nearest": B.CR["axle_check"]["nearest"], "rev3_u30": B.CR["axle_check"]["rev3_u30_rib"]}
    r = res["3a"]
    res["ok"] = r["seated_elsewhere_mm3"] <= TOL_V and r["path_overlap_mm3"] <= TOL_V and r["path_gap_to_ribs"] >= 0.5
    return res


def leg_swing(lid):
    """leg let down about its pivot (screen held at 22 deg / at 25 deg): overlap with the lid pocket vs angle below horizontal."""
    L, R = B.LG["length"], B.LEG_R
    x0, x1 = B.LEG_X
    zone = lid ^ box(B.POCKET["x"][0] - 3, B.POCKET["x"][1] + 3, B.POCKET["ramp_front_y"] - 25, B.POCKET["back_wall_y"] + 15, B.LID_BED, B.LID_TOP + 20)

    def leg(piv, phi, r=R):
        tip = (piv[0] + L * math.cos(math.radians(phi)), piv[1] - L * math.sin(math.radians(phi)))
        return B.capsule_x(piv, tip, x0, x1, r=r)
    out = {}
    for tag, th in (("22", B.TH_HEEL), ("25", B.TH_USE)):
        piv = tuple(B.to_world((0, B.PIV_UW[0], B.PIV_UW[1]), th)[1:])
        phi, first, worst, rows = 25.0, None, (0.0, None), []
        end = B.LG["angle_deg"] if tag == "25" else 45.0
        while phi <= end + 1e-9:
            m = leg(piv, phi)
            v = ivol(m, zone)
            g = m.min_gap(zone, 2.0) if v <= TOL_V else 0.0
            if first is None and (v > TOL_V or g < 1e-3):
                first = round(phi, 2)
                if tag == "22":
                    break                                  # foot rests on the ramp: the screen then goes back to 25 deg
            if v > worst[0]:
                worst = (v, round(phi, 2))
            rows.append((round(phi, 2), round(v, 4)))
            phi += 0.1
        r = {"pivot": [round(v, 2) for v in piv], "first_contact_deg": first, "max_overlap_mm3": round(worst[0], 4), "at_deg": worst[1]}
        if worst[1] is not None:
            m_ok = _bisect(lambda rr: ivol(leg(piv, worst[1], rr), zone) <= TOL_V, R - 2.0, R)
            r["depth"] = round(R - m_ok, 2)
            over = [p for p, v in rows if v > TOL_V]
            r["overlap_deg"] = [over[0], over[-1]]
        out[tag] = r
    sw = B.LG["swing"]
    out["design"] = {"at_22_first_contact_deg": sw["at_22"]["first_contact_deg"], "at_25_first_contact_deg": sw["at_25"]["first_contact_deg"],
                     "at_25_worst_overlap": sw["at_25"]["worst_overlap"], "at_25_worst_at_deg": sw["at_25"]["worst_at_deg"], "procedure": sw["procedure"]}
    return out


def walls_checks(crl):
    S = B.screen_local()
    scr = B.union([S["body"], S["bezel"]])
    bot = crl ^ box(-40, 40, B.U0 - 0.01, 1.0, B.W0 - 0.01, 7.9)
    top = crl ^ box(-40, 40, 99.0, B.U1 + 0.01, B.W0 - 0.01, 7.9)
    side = crl ^ box(80.0, B.X1 + 0.01, 20.0, 80.0, B.W0 - 0.01, 7.9)
    nt = B.NOTCH
    inside = crl ^ box(nt["xr"][0] + 0.05, nt["xr"][1] - 0.05, nt["u"][0] + 0.05, nt["u"][1] - 0.05, nt["w"][0] + 0.05, nt["w"][1] - 0.05)
    beside = [crl ^ box(nt["xr"][0] - 3.0, nt["xr"][0] - 0.05, nt["u"][0] + 0.05, nt["u"][1] - 0.05, nt["w"][0] + 0.05, nt["w"][1] - 0.05),
              crl ^ box(nt["xr"][1] + 0.05, nt["xr"][1] + 3.0, nt["u"][0] + 0.05, nt["u"][1] - 0.05, nt["w"][0] + 0.05, nt["w"][1] - 0.05)]
    full = 2.95 * 2.4 * 8.9
    fills = []
    fw = B.BO["fill_to_side_wall"]
    for xr in B.BO["xr"]:
        fx = next(r for r in fw["xr"] if r[0] <= xr <= r[1])
        a, b = (fx[0] + 0.05, xr - B.BO["d"] / 2 - 0.3) if xr < 0 else (xr + B.BO["d"] / 2 + 0.3, fx[1] - 0.05)
        for u in B.BO["u"]:
            bx = box(a, b, u - 3.9, u + 3.9, B.BO["w"][0] + 0.05, B.BO["w"][1] - 0.05)
            fills.append(round((crl ^ bx).volume() / bx.volume(), 3))
    tab = S["tab"]
    ch = crl.bounding_box()
    return {"glass_bottom_gap": round(scr.min_gap(bot, 2.0), 3), "glass_top_gap": round(scr.min_gap(top, 2.0), 3),
            "glass_side_gap": round(scr.min_gap(side, 2.0), 3), "design": {"bottom": B.WL["bottom_gap"], "top": B.WL["top_gap"], "side": B.WL["side_gap"]},
            "notch_material_mm3": round(inside.volume(), 4), "wall_beside_notch_fill": [round(bb.volume() / full, 3) for bb in beside],
            "tab_to_cradle_gap": round(tab.min_gap(crl, 10.0), 3), "tab_margin_x_design": B.N["checks"]["notch_margin"],
            "boss_fill_fraction": fills, "print_height": round(ch[4] - ch[1], 2), "print_height_design": B.CR["print_height"],
            "ear_lowest_u": round(ch[1], 2)}


def named():
    """clearances the design names (numbers.json), measured on the model."""
    lid = B.lid_world()
    kp = B.knuckle_profile()
    cheeks = []
    for side in ("left", "right"):
        h = B.HG[side]
        for ck in ("far_cheek", "near_cheek"):
            cheeks.append(B.prism_x(kp, B.XC + h[ck][0], B.XC + h[ck][1]))
    cheeks = B.union(cheeks)
    crl = B.cradle_local()
    res = {}
    res["ear"] = ear_checks(lid)
    res["heel_gap_25"] = res["ear"]["min_gap_25_90"][0] if res["ear"]["min_gap_25_90"][1] == B.TH_USE else None
    res["heel_gap_25_design"] = B.HG["heel_gap_at_25"]
    res["axle"] = axle_checks()
    res["walls"] = walls_checks(crl)
    g_cheek = (9e9, None)
    body = crl.trim_by_plane((0, 1, 0), B.U0 - 1e-3)          # cradle without the ears (the ears run 0.2 beside the cheeks by design)
    res["ear_to_cheek_side_gap"] = round(B.HG["left"]["ear"][0] - B.HG["left"]["near_cheek"][1], 3)
    th = B.TH_HEEL
    while th <= B.TH_FOLD + 1e-9:
        g = B.place(body, th).min_gap(cheeks, 3.0)
        if g < g_cheek[0]:
            g_cheek = (round(g, 3), th)
        th += 0.5
    res["cheek_gap_min_22_90"] = g_cheek
    res["cheek_gap_design"] = B.CR["rib_relief_at_cheeks"]["gap_after"]
    lg, piv, tip = B.leg_world_use()
    ramp_zone = lid ^ box(B.POCKET["x"][0] - 1, B.POCKET["x"][1] + 1, B.POCKET["ramp_front_y"] - 20, B.POCKET["ramp_end_y"], B.LID_BED, B.LID_TOP + 1)
    res["leg_ramp_gap_25"] = round(lg.min_gap(ramp_zone, 3.0), 3)
    res["leg_ramp_gap_design"] = B.POCKET["ramp_min_clear"]
    res["leg_swing"] = leg_swing(lid)
    c90 = B.place(crl, B.TH_FOLD)
    l90 = B.place(B.leg_local_stowed(), B.TH_FOLD)
    res["fold_leg_gap_to_lid"] = round(l90.min_gap(lid, 5.0), 3)
    res["fold_leg_gap_design"] = B.LG["fold_leg_z"][0] - B.LID_TOP
    cl = B.LG["clip"]
    yc0, yc1 = B.to_world((0, cl["u"][0], 0), B.TH_FOLD)[1], B.to_world((0, cl["u"][1], 0), B.TH_FOLD)[1]
    clipzone = c90 ^ box(B.XC - 10, B.XC + 10, min(yc0, yc1) - 0.5, max(yc0, yc1) + 0.5, B.LID_TOP - 1, B.LID_TOP + 6)
    res["fold_clip_gap_to_lid"] = round(clipzone.min_gap(lid, 5.0), 3) if not clipzone.is_empty() else None
    res["fold_clip_gap_design"] = B.N["checks"]["fold_clip_clear_lid"]
    cb = c90.bounding_box()
    res["fold_rear_margin"] = round(B.LID_Y[1] - cb[4], 3)
    res["fold_top_z"] = round(cb[5], 3)
    res["fold_speaker_margin"] = round(B.PL["speaker_top_z"] - cb[5], 3)
    gmin = (9e9, None)
    rc = B.ribbon_clip_world()
    th = B.TH_HEEL
    while th <= B.TH_FOLD + 1e-9:
        rb = B.ribbon_parts(th)["solid"]
        wr = B.wire_parts(th)
        for nm, sld in (("ribbon", rb), ("power", B.union([wr["red"], wr["black"]]))):
            g = (sld - rc).min_gap(lid, 5.0) if nm == "ribbon" else sld.min_gap(lid, 5.0)
            gg = sld.min_gap(lid ^ box(B.LID_X[0], B.LID_X[1], B.LID_Y[0], B.LID_Y[1], B.LID_TOP - B.LID_T - 0.01, B.LID_TOP + 30), 5.0)
            if gg < gmin[0]:
                gmin = (round(gg, 3), th, nm)
        th += 2.0
    res["cables_gap_to_lid_plate_hole_knuckles_min"] = gmin      # lid from the plate underside up (hole walls, knuckles, stop blocks)
    res["clip"] = clip_checks(lid, rc)
    res["lid_screw"] = lid_screw_checks(lid)
    res["cables"] = cable_checks()
    return res


def clip_checks(lid, rc):
    rb = B.ribbon_parts(B.TH_USE)
    wr = B.wire_parts(B.TH_USE)
    ffc, wires = rb["solid"], B.union([wr["red"], wr["black"]])
    cp = B.CLIP["pad"]
    zone = box(cp["x"][0] - 1, cp["x"][1] + 1, cp["y"][0] - 1, cp["y"][1] + 1, 55.0, 70.0)
    f_in = ffc ^ zone
    fb = f_in.bounding_box()
    px, py = B.CLIP["pins"][0]
    col = lid ^ B.cyl_z(px, py, B.LID_BED - 1, B.LID_TOP + 1, 1.0)
    rcb = rc.bounding_box()
    return {"ribbon_z_in_clip": [round(fb[2], 3), round(fb[5], 3)], "clamp_z_design": B.CLIP["clamp_z"],
            "ribbon_to_clip_gap": round(ffc.min_gap(rc, 2.0), 3), "ribbon_to_pad_gap": round(f_in.min_gap(lid, 2.0), 3),
            "ribbon_clip_overlap_mm3": round(ivol(ffc, rc), 4), "ribbon_pad_overlap_mm3": round(ivol(ffc, lid), 4),
            "wires_to_clip_gap": round(wires.min_gap(rc, 3.0), 3), "wires_to_lid_gap": round(wires.min_gap(lid, 3.0), 3),
            "wires_to_ribbon_gap": round(wires.min_gap(ffc, 3.0), 3),
            "pin_top_z": round(rcb[5], 3), "pin_hole_bottom_z": round(col.bounding_box()[2], 3),
            "pin_tip_to_hole_bottom": round(col.bounding_box()[2] - rcb[5], 3), "pin_len": B.CLIP["pin_len"]}


def lid_screw_checks(lid):
    scr = B.lid_screws_world()
    ctx = {p.id: p.solid for p in B.context_parts()}
    rails = B.union([v for k, v in ctx.items() if k.startswith("L2-PR-SEAMRAIL")])
    posts = [v for k, v in ctx.items() if k.startswith("L2-PR-SEAMPOST")]
    ins = B.union([v for k, v in ctx.items() if k.startswith("L2-INSERT")])
    s0 = scr[0]
    b = s0.bounding_box()
    x, y = B.lid_screw_xy()[0]
    col = rails ^ B.cyl_z(x, y, 40.0, 70.0, 1.0)
    return {"head_seat_z": B.LS["head_seat_z"], "screw_z": [round(b[2], 3), round(b[5], 3)], "tip_z_design": B.LS["tip_z"],
            "screw_to_lid_gap": round(min(s.min_gap(lid, 2.0) for s in scr), 3), "screw_lid_overlap_mm3": round(sum(ivol(s, lid) for s in scr), 4),
            "screw_to_rail_gap": round(min(s.min_gap(rails, 3.0) for s in scr), 3), "tip_to_insert_hole_bottom": round(b[2] - col.bounding_box()[5], 3),
            "rail_floor_under_hole": round(col.bounding_box()[5] - B.LS["rail_z"][0], 3), "rail_floor_design": B.LS["rail_floor_under_hole"],
            "tip_to_post_top": round(min((s.min_gap(p, 5.0) for s in scr for p in posts), default=None), 3),
            "screw_insert_overlap_mm3": round(sum(ivol(s, ins) for s in scr), 3), "cbore_d": B.LS["cbore_d"], "cbore_depth": B.LS["cbore_depth"]}


def cable_checks():
    rb = B.ribbon_parts(B.TH_USE)
    wr = B.wire_parts(B.TH_USE)
    pi = {p.id: p.solid for p in B.context_parts() if p.id.startswith("PI5-")}
    ffc = rb["solid"]
    fb = ffc.bounding_box()
    d1 = B.N["pi5"]["cad_disp1"]
    hs = ffc ^ pi["PI5-HEATSINK"]
    hsb = hs.bounding_box() if not hs.is_empty() else None
    corner = rb["pi_corner"]
    roll = B.RB["parts"]["fold_roll_allowance"]          # the under-lid 45 deg fold is modelled as a crease
    wire_model = [round(v, 2) for v in wr["lengths"]]
    to_pin = B.N["pi5"]["gpio_top_z"] - B.EST["gpio_pin_above_base"] + B.EST["dupont"][2] - B.N["pi5"]["gpio_top_z"]
    return {"ribbon_end_x": round(float(rb["pi_end"][0]), 3), "disp1_back_x": d1["x"][1], "ribbon_end_short_of_back": round(d1["x"][1] - float(rb["pi_end"][0]), 3),
            "pi_insert": B.RB["pi_end_insert"], "pi_corner_xz": [round(float(corner[0]), 2), round(float(corner[2]), 2)],
            "ribbon_to_hdmi_gap": round(ffc.min_gap(pi["PI5-HDMI"], 2.0), 3), "ribbon_hdmi_overlap_mm3": round(ivol(ffc, pi["PI5-HDMI"]), 4),
            "ribbon_heatsink_overlap_mm3": round(ivol(ffc, pi["PI5-HEATSINK"]), 4),
            "ribbon_heatsink_overlap_box": [round(v, 2) for v in hsb] if hsb else None,
            "design_pi_clearance": B.RB["pi_clearance"],
            "ribbon_len_model": round(rb["length"], 2), "ribbon_len_model_plus_lid_fold_roll": round(rb["length"] + roll, 2),
            "ribbon_len_design": B.RB["total"], "cable": B.RB["cable"],
            "wire_len_model_to_housing_top": wire_model, "housing_top_to_pin_tip": round(to_pin, 2),
            "wire_len_model_plus_pin_and_dupont": [round(v + to_pin + B.PW["parts"]["dupont_and_slack"], 2) for v in wr["lengths"]],
            "wire_len_design": B.PW["total"], "wire_available": B.PW["available"], "ffc_bbox": [round(v, 2) for v in fb],
            "l2_zones": zone_checks(ffc, B.union([wr["red"], wr["black"]]))}


def zone_checks(ffc, wires):
    """cables vs the L2 reserved zones (Z-*): only Z-DSI (ribbon) and Z-GPIO-LEAD (power leads) are theirs."""
    own = {"Z-DSI": "ribbon", "Z-GPIO-LEAD": "wires"}
    out = []
    for c in B.L2["centre_contents"]:
        if c.get("kind") != "zone":
            continue
        z = box(*c["bbox_x0x1y0y1z0z1"])
        vf, vw = ivol(ffc, z), ivol(wires, z)
        if vf > TOL_V or vw > TOL_V:
            out.append({"zone": c["id"], "ribbon_mm3": round(vf, 3), "wires_mm3": round(vw, 3), "own": own.get(c["id"])})
    return out


def main():
    t0 = time.time()
    res = {"src": B.SRC, "est": {k: v for k, v in B.EST.items()}, "tol_mm3": TOL_V,
           "keepout": "y <= %.1f and z >= %.2f over x %s (modules are lifted out upward)" % (B.KEEP["y_max"], B.KEEP["z_min"], B.BL2["overall"]["x"])}
    res["named"] = named()
    res["poses"] = {"22": check_pose("22", B.TH_HEEL), "25": check_pose("25", B.TH_USE), "90": check_pose("90", B.TH_FOLD)}
    sw, worst = sweep(1.0)
    res["sweep"] = {"step_deg": 1.0, "leg": "clipped (stowed)", "rows": sw,
                    "unexpected_hits": [dict(r, theta=s["theta"]) for s in sw for r in s["hits"] if not r["why"]],
                    "keepout_violations": [s["theta"] for s in sw if s["keepout_vol"] > TOL_V],
                    "worst": {"min_gap_to_lid_between_22_90": worst["min_gap_to_lid"], "min_y_moving_above_top": worst["min_y_moving"],
                              "min_y_cables_above_top": worst["min_y_cable"]}}
    res["summary"] = {k: {"interferences": len(r["interferences"]), "estimate_overlaps": len(r["estimate_overlaps"]),
                          "keepout_hits": len(r["keepout_hits"])} for k, r in res["poses"].items()}
    res["summary"]["sweep_unexpected"] = len(res["sweep"]["unexpected_hits"])
    res["summary"]["sweep_keepout"] = len(res["sweep"]["keepout_violations"])
    res["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(HERE, "interference.json"), "w"), ensure_ascii=False, indent=1, default=float)
    for k, r in res["poses"].items():
        print("== %s deg, leg %s  interferences %d, expected contacts %d, estimate overlaps %d, keep-out hits %d, min y above z%.2f: moving %.2f cables %.2f" % (
            k, r["leg"], len(r["interferences"]), len(r["expected_contacts"]), len(r["estimate_overlaps"]), len(r["keepout_hits"]), B.KEEP["z_min"],
            r["min_y_above_module_top"]["moving"], r["min_y_above_module_top"]["cables"]))
        for x in r["interferences"]:
            print("   !", x)
        for x in r["estimate_overlaps"]:
            print("   ~", x["a"], x["b"], x["vol_mm3"])
        for x in r["closest_gaps"][:6]:
            print("   gap", x["gap"], x["a"], x["b"])
    print("sweep unexpected", len(res["sweep"]["unexpected_hits"]), res["sweep"]["unexpected_hits"][:10])
    print("sweep keepout", res["sweep"]["keepout_violations"], "worst", res["sweep"]["worst"])
    nm = dict(res["named"])
    for k in ("ear", "axle", "walls", "leg_swing", "clip", "lid_screw", "cables"):
        v = nm.pop(k)
        if k == "ear":
            v = {kk: vv for kk, vv in v.items() if kk != "gap_22_to_25"}
        print("named", k, json.dumps(v, ensure_ascii=False, default=float))
    print("named rest", nm)
    print("elapsed", res["elapsed_s"])


if __name__ == "__main__":
    main()
