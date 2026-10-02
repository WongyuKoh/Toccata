"""Toccata v4 W1+ round 4 drawings 7-12 (called from render_v4.main).  Same rules as render_v4.py: every number drawn
is read from ../final/geometry.json (dims ids cited in the labels), removal poses / masses / spring states from
../final/metrics.json, the rear bar from the v3 tables (context/v3_extract.txt).  Coordinates typed below are
placement only.  r4: sheet 9 = pad bar + up-stop pads + curtain strip + torsion spring (the r3 rail / cover /
spring-seat sheet is gone); no thumb screws, disc springs, tapped strips, brass bushings, C-rings or L blocks."""
import json
import math
import os
import re

import kit
from kit import (G, SOL, M, PLAN, View, fmt_mm, dn, dns, v3n, nums, body, fixed, pts, cut_x, plan_item, plan_all, bbox, yslice,
                 rot, rot_pts, rect, arc_pts, circle_pts, union_rings, fill_rings, stroke_rings, hpoly, pids, mat_fixed,
                 pivot_mark, sensor_mark, scalebar, balloon_row, legend, note_lines, label, panel_title, leader_to,
                 table, page, ordz, ordy, clip_begin, clip_end, F2, callouts)
import render_v4 as R
from render_v4 import (in_win, K, L, KP_W, KP_B, kpt, part, fpart, fparts, is_frame, WHITE, BLACK, ORDER, ppoly, pcirc, side_scene,
                       pad_layers, dovetail_polys, lever_top_features, capstan_shank, magnet_polys, cloth_ring, pin_groove,
                       rest_rad, spring_geom, pocket_x, plate_z, sheet4_cuts, xz_scene, rod_elements, bay_play,
                       usb_env, shelf_slot, board_rings, is_boss, boss_parts, bore_parts, rod_part, plug_part,
                       top_lip_spans, top_lip_wh, top_lip_parts, low_lip_wh, void_first)

OUT = kit.HERE
PL = json.load(open(os.path.join(kit.V4, "final", "parts_list.json")))     # r4.4: spares (d11) and printed tools / plug (d13)


def pl_item(prefix):
    return next(p for p in PL["parts"] if p["name"].startswith(prefix))


def pl_spare(prefix):
    """'88 + 예비 2' / '모듈 7 + 끝 2 + 예비 1' -> number of spares of a parts_list item (0 if none)."""
    m = re.search(r"예비 (\d+)", pl_item(prefix)["note"])
    return int(m.group(1)) if m else 0


def F(v, nd=2):
    return fmt_mm(v, nd)
SHEETS = R.SHEETS


def rec(n, base, title_ko, caption_ko):
    SHEETS.append(dict(n=n, title_ko=title_ko, caption_ko=caption_ko,
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))


def vert(poly, pred):
    """first vertex of poly satisfying pred(y, z)."""
    return next(q for q in poly if pred(q[0], q[1]))


def arrow(v, u1, w1, u2, w2, cls="dm"):
    v.line(u1, w1, u2, w2, cls=cls)
    v._arrow(u2, w2, math.atan2(w2 - w1, u2 - u1))


# ================================================================ sheet 7: lever carrier + steel block + spring pocket
LEV = "lever D"


def lev_parts():
    return body(LEV)


def lev_poly(name, i=0, pose="rigid0"):
    return pts(part(LEV, name, i), pose)


def lever_geom():
    core = lev_poly("carrier core")
    wall = lev_poly("carrier side wall L")
    stl = lev_poly("steel block")
    felt = lev_poly("felt strip")
    web = lev_poly("web")
    hub = lev_poly("hub")
    tab = lev_poly("fingernail tab")
    rfl = lev_poly("carrier rear floor")
    lipA = lev_poly("bottom lip", 0)
    wl = part(LEV, "carrier side wall L")["x"]
    wr = part(LEV, "carrier side wall R")["x"]
    col = part(LEV, "hub collar")
    xc = SOL["levers"]["D"]
    lt = lever_top_features()
    zt_st = max(q[1] for q in stl)
    z_top = max(q[1] for q in wall)
    y_front = min(q[0] for q in core)
    y_rear = max(q[0] for q in core)
    s_y0, s_y1 = min(q[0] for q in stl), max(q[0] for q in stl)
    s_z0 = min(q[1] for q in stl)
    cap_r = dn("D08")
    cap_c = (min(q[0] for q in wall if abs(q[1] - z_top) < 1e-6), z_top - cap_r)
    lip_z0 = min(q[1] for q in lipA)
    felt_z0 = min(q[1] for q in felt)
    s11 = dns("S11", "note")            # [4, 304, 4.3, 3.9, 4.0]
    web_top = max(q[1] for q in web)
    web_y0 = min(q[0] for q in web)
    slope_z = vert(core, lambda y, z: abs(y - y_rear) < 1e-6 and z > s_z0 + 5)[1]
    lips = top_lip_spans()                   # r4.4: exported lip parts [(150, 163), (184, 190)]
    # r4.4 fix 2 (D07): between the top-lip spans the side wall's top is below the steel top (the wall passes under the pad)
    s_z0_ = min(q[1] for q in stl)
    wpad = [q for q in wall if lips[0][1] - 1e-6 <= q[0] <= lips[1][0] + 1e-6 and (zt_st + s_z0_) / 2 < q[1] < zt_st - 1e-6]
    zw_pad = min(q[1] for q in wpad)
    return dict(zw_pad=zw_pad, wpad=sorted(wpad), core=core, wall=wall, stl=stl, felt=felt, web=web, hub=hub, tab=tab, rfl=rfl, lipA=lipA, wl=wl, wr=wr, col=col,
                xc=xc, lt=lt, zt_st=zt_st, z_top=z_top, y_front=y_front, y_rear=y_rear, s_y0=s_y0, s_y1=s_y1, s_z0=s_z0,
                cap_r=cap_r, cap_c=cap_c, lip_z0=lip_z0, felt_z0=felt_z0, hub_r=s11[2], bore_p=s11[3], bore=s11[4],
                web_top=web_top, web_y0=web_y0, slope_z=slope_z, lip_y=lips[0], lips=lips, low_lip=low_lip_wh()[:2],
                pocket=SOL["spring"]["pocket"])


def d07_bond():
    """D07 value: '강철은 두 19×40 옆면에 MS 폴리머를 바르고 밑에서 스냅으로 끼워 접착 (접착층 한쪽 0.10, 접착 면 1411 mm²; ...)'
    (r4.4 fix 2b: MS polymer instead of the fix-2 5-min epoxy) -> the sentence up to the bonded area, parentheses closed."""
    kit.USED["D07"] = kit.DIMS["D07"]["item"]
    t = re.search(r"강철은 .*?mm²", kit.DIMS["D07"]["value"]).group(0).strip()
    return t + ")" * (t.count("(") - t.count(")"))


def low_lip_y():
    """D07 '아래 립 1.0×1.0 (y165~176.5 ...)' -> (y0, y1)."""
    return low_lip_wh()[2:4]


def web_exit(g):
    """point where the web's sloping top edge leaves the carrier rear face (the web apex is inside the wall)."""
    w = g["web"]
    i = max(range(len(w)), key=lambda k: w[k][1])
    a = w[i]
    b = max((w[i - 1], w[(i + 1) % len(w)]), key=lambda t: t[0])
    t = (g["y_rear"] - a[0]) / (b[0] - a[0])
    return (g["y_rear"], a[1] + t * (b[1] - a[1]))


def lever_xz(v, P, y, g, pose="rigid0", spring=True):
    """x-z section of the lever at y (rigid0 pose): carrier (union, hatched), steel, felt; the top snap lips are exported
    lever parts (r4.4, D07) and are sliced with the rest; hub bore + spring pocket as voids."""
    carrier, over = [], []
    for p in lev_parts():
        for z0, z1 in yslice(pts(p, pose), y):
            r_ = rect(p["x"][0], p["x"][1], z0, z1)
            if p["part"].startswith("steel"):
                over.append((r_, "m-steel"))
            elif p["part"].startswith("felt"):
                over.append((r_, "m-felt"))
            else:
                carrier.append(r_)
    if carrier:
        fill_rings(v, union_rings(carrier, res=0.01), "m-lever", P["lever"])
    for r_, c in over:
        hpoly(v, r_, c, P["steel"] if c == "m-steel" else None)
    dy = y - L[0]
    sg = R.spring_geom()
    if spring:          # r4.5: the pocket D6.6 is the exported 'spring pocket section A / B' (sliced above); coil wires only
        if abs(dy) < sg["r_m"]:
            hz = math.sqrt(sg["r_m"] ** 2 - dy * dy)
            for xw in R.coil_wires("D"):
                for s_ in (1, -1):
                    v.circle(xw, L[1] + s_ * hz, sg["d"] / 2, cls="m-steel")
    if abs(dy) < g["bore"] / 2:
        h = math.sqrt((g["bore"] / 2) ** 2 - dy * dy)
        v.poly(rect(g["col"]["x"][0], g["wr"][1], L[1] - h, L[1] + h), cls="void")
    return carrier, over


def hub_pocket_detail(g):
    """r4.5 fix detail G: the hub's spring-pocket section at the lever centre x (0 deg): pocket D6.6, the insertion slot
    along the captured leg (316.83 deg, faces +-3.25: only the -3.25 face is material, the +3.25 side opens round to the
    long-leg window), the long-leg window (35 deg, upper face +2.6), the captured short-leg groove (0.70 wide along
    136.83 deg, faces 2.511 / 3.211 from the axis, ss -0.5 .. 8.21 blind), its two contacts (leg tip on the outer face,
    leg on the inner face's pocket edge, arm 5.75) and the pieces A (web side) / B (lower ring) — all from the exported
    lever parts and solved.spring (short_leg_groove / capture)."""
    sp = SOL["spring"]
    slg = sp["short_leg_groove"]
    cap = sp.get("capture", {})
    xc = g["xc"]
    Lp = (L[0], L[1])
    u0, u1, w0, w1 = L[0] - 9.5, L[0] + 6.4, L[1] - 6.5, L[1] + 6.4
    s_ = 44.0
    NB = 162                                   # px below the window for the callout list
    v = View(u0 - 20 / s_, w0 - NB / s_, u1 + 20 / s_, w1 + 30 / s_, px_width=(u1 - u0) * s_ + 40, pad_px=4)
    P = pids(v)
    i0 = clip_begin(v)
    cut = [pts(p, "rigid0") for p in lev_parts() if cut_x(p, xc) and not p["part"].startswith(("steel", "felt"))]
    fill_rings(v, union_rings(cut, res=0.01), "m-lever", P["lever"])
    R.draw_spring(v, "D", xc, pose="rigid0")
    v.circle(L[0], L[1], g["bore"] / 2, cls="m-steel")
    at = lambda c, d, r: (c[0] + r * math.cos(math.radians(d)), c[1] + r * math.sin(math.radians(d)))
    vec = lambda d: (math.cos(math.radians(d)), math.sin(math.radians(d)))
    add = lambda *ps: (sum(p_[0] for p_ in ps), sum(p_[1] for p_ in ps))
    mul = lambda k, p_: (k * p_[0], k * p_[1])
    # insertion slot: centre line, the open +3.25 side (phantom), the -3.25 wall (piece B edge) and the 6.5 across
    a_s = sp.get("insertion_slot_deg", sp["slot_deg_lever_frame"])
    a_sd = a_s - 360.0 if a_s > 180.0 else a_s                       # signed (CW from +y is negative)
    t_s, n_s = vec(a_sd), vec(a_sd + 90.0)
    fa, fb = sp["slot_faces"]
    v.cl(L[0], L[1], *add(Lp, mul(5.9, t_s)))
    s_in = math.sqrt(max(sp["pocket"][0] ** 2 / 4 - fa * fa, 0.0))    # the +3.25 line leaves the pocket there
    v.line(*add(Lp, mul(fa, n_s), mul(s_in, t_s)), *add(Lp, mul(fa, n_s), mul(4.9, t_s)), cls="phan")
    A_ = add(Lp, mul(fa, n_s), mul(4.9, t_s))
    B_ = add(Lp, mul(fb, n_s), mul(4.9, t_s))
    on_b = [q for r_ in cut for q in r_ if abs((q[0] - L[0]) * n_s[0] + (q[1] - L[1]) * n_s[1] - fb) < 0.03]
    if on_b:                                                           # extension line along the -3.25 wall
        q_ = max(on_b, key=lambda q: (q[0] - L[0]) * t_s[0] + (q[1] - L[1]) * t_s[1])
        v.line(q_[0] + t_s[0] * v.px(2), q_[1] + t_s[1] * v.px(2), B_[0], B_[1], cls="ex")
    R.dim_aligned(v, A_, B_, 0, "", size_px=9.5)
    mid = add(mul(0.5, add(A_, B_)), mul(v.px(8), t_s))
    v.text(mid[0] + v.px(2), mid[1] - v.px(3.5), f"{F(fa - fb)} (±{F2(fa)})", cls="dt", anchor="start", size_px=9.5)
    v.poly(arc_pts(L, 5.4, 0.0, a_sd, 14), cls="dm", closed=False)
    p_lab = at(Lp, a_sd / 2, 5.4)
    v.text(p_lab[0] - v.px(4), p_lab[1] - v.px(3), f"{F(a_s)}°", cls="dt", anchor="end", size_px=9.5)
    # long-leg window: centre line 35 deg, the upper face +2.6 (piece A edge) and its offset
    a_w, f_w = sp["short_leg_groove"].get("window", sp.get("window", [35.0, 2.6]))
    t_w, n_w = vec(a_w), vec(a_w + 90.0)
    v.cl(L[0], L[1], *add(Lp, mul(5.9, t_w)))
    Wc = add(Lp, mul(5.0, t_w))
    Wf = add(Wc, mul(f_w, n_w))
    on_w = [q for r_ in cut for q in r_ if abs((q[0] - L[0]) * n_w[0] + (q[1] - L[1]) * n_w[1] - f_w) < 0.03]
    if on_w:
        q_ = max(on_w, key=lambda q: (q[0] - L[0]) * t_w[0] + (q[1] - L[1]) * t_w[1])
        v.line(q_[0] + t_w[0] * v.px(2), q_[1] + t_w[1] * v.px(2), Wf[0] + t_w[0] * v.px(3), Wf[1] + t_w[1] * v.px(3), cls="ex")
    R.dim_aligned(v, Wc, Wf, 0, "", size_px=9.5)
    Wm = add(Wc, mul(f_w / 2, n_w))
    v.text(Wm[0] + v.px(6), Wm[1] - v.px(2), f"+{F(f_w)}", cls="dt", anchor="start", size_px=9.5)
    v.poly(arc_pts(L, 4.9, 0.0, a_w, 10), cls="dm", closed=False)
    p_lab = at(Lp, a_w / 2, 4.9)
    v.text(p_lab[0] + v.px(4), p_lab[1] - v.px(3), f"{F(a_w)}°", cls="dt", anchor="start", size_px=9.5)
    # captured groove: centre line along the band, the two faces from the axis (along the band normal), 0.70 across
    bd = slg.get("band_deg", slg["leg_dir"])
    t_g, n_g = vec(bd), vec(bd + 90.0)
    nn0, nn1 = slg["nn"]
    ss0, ss1 = slg["ss"]
    c0 = add(Lp, mul((nn0 + nn1) / 2, n_g), mul(ss0, t_g))
    v.cl(*c0, *add(c0, mul(ss1 - ss0 + 0.9, t_g)))
    nr_ = (n_g[1], -n_g[0])                   # right-hand normal of axis -> face (dim_aligned's offset direction)
    for k_, r_ in enumerate((nn0, nn1)):
        R.dim_aligned(v, Lp, add(Lp, mul(r_, n_g)), -10 - 26 * k_, "", size_px=9.5)
    taken_ = []
    for k_, r_ in enumerate((nn0, nn1)):
        # r4.5 fix 3: the value goes outboard, past the groove-face arrowhead on a tail of the dimension line (beyond
        # the outer face, in piece B), with a white halo - it no longer sits on the coil ring / the other dimension line
        Bk = add(Lp, mul(r_, n_g), mul(v.px(-10 - 26 * k_), nr_))
        kit.tail_text(v, Bk, n_g, F2(r_), (nn1 - r_) + v.px(10), (nn1 - r_) + v.px(120), taken=taken_)
    # width 0.70 across the groove near its blind end, outside arrows (the groove is 31 px wide at this scale)
    sw = ss1 - 1.4
    G0, G1 = add(Lp, mul(nn0, n_g), mul(sw, t_g)), add(Lp, mul(nn1, n_g), mul(sw, t_g))
    R.dim_aligned(v, G1, G0, 0, "", size_px=9.5)
    v.text(G0[0] + v.px(5), G0[1] + v.px(3), f"{F2(slg.get('width', nn1 - nn0))}", cls="dt", anchor="start", size_px=9.5)
    # contacts: O = leg tip on the outer face, E = leg on the inner face at the pocket edge; arm along the groove
    O_, E_ = tuple(slg["O"]), tuple(slg["E"])
    arm = slg.get("arm", cap.get("arm"))
    for q_ in (O_, E_):
        v.circle(q_[0], q_[1], v.px(2.6), cls="dot")
    b_ = add(O_, mul(-arm, t_g))                                       # E's station on the outer face
    R.dim_aligned(v, O_, b_, 30, "", size_px=9.5)           # O -> b runs down-right: +offset = outward (n_g)
    v.line(E_[0], E_[1], b_[0], b_[1], cls="ex")
    mm = add(mul(0.5, add(O_, b_)), mul(v.px(40), n_g))
    v.text(mm[0], mm[1] - v.px(4), f"팔 {F2(arm)}", cls="dt", anchor="end", size_px=9.5)
    clip_end(v, i0, u0, u1, w0, w1)
    panel_title(v, u0 - 20 / s_ + v.px(4), w1 + v.px(14), f"확대 G (r4.5 고침): 허브 스프링 주머니 구간, x{F2(xc)} 단면, 0° — 짧은 다리 가둠 홈", size_px=11.5)
    v.cl(u0 + 0.3, L[1], u1 - 0.3, L[1])
    v.cl(L[0], w0 + 0.3, L[0], w1 - 0.3)
    a_pc = [p for p in lev_parts() if "pocket section A" in p["part"]][0]
    b_pc = [p for p in lev_parts() if "pocket section B" in p["part"]][0]
    qa, qb = pts(a_pc, "rigid0"), pts(b_pc, "rigid0")
    cb = min(qb, key=lambda t_: t_[1])
    Fr, Fh = cap.get("F_couple_rest"), cap.get("F_couple_hand")
    items = [("A", (L[0] - 5.2, L[1] + 5.0), (-26, 22), f"조각 A (웹 쪽: 웹 + 가둠 홈의 안 면·막힌 끝·웹 속 바깥 면 + 긴 다리 창 윗면), x{F2(a_pc['x'][0])}~{F2(a_pc['x'][1])}"),
             ("B", (cb[0], cb[1] + 0.25), (-40, -26), f"조각 B (아래 고리: 가둠 홈 바깥 면(축에서 {F2(nn1)})의 허브 부분 ~ 넣는 슬롯 아래 면 −{F2(-fb)})"),
             ("p", at(Lp, 165.0, g["pocket"][0] / 2), (-36, 14),           # r4.5 fix 3: pocket arc of piece A (the B-side corner is the 3.21 tail)
              f"주머니 Ø{F(g['pocket'][0])} × {F(g['pocket'][1])} (레버 x ±{F(g['pocket'][1] / 2)}) — 코일 OD {F(sp['ID'] + 2 * sp['d'])}, 반경 틈 {F2((g['pocket'][0] - sp['ID'] - 2 * sp['d']) / 2)}"),
             ("g", add(Lp, mul((nn0 + nn1) / 2, n_g), mul(ss1 - 3.2, t_g)), (-34, 34),
              f"가둠 홈 폭 {F2(slg.get('width', nn1 - nn0))} (다리 d{F(sp['d'])} + 놀음 {F2(slg.get('play', 0.0))}), {F2(bd)}° 방향 = 짧은 다리({F2(slg['leg_dir'])}°)를 CW {F2(slg.get('theta_c', 0.0))}° 돌림, "
              f"축에서 {F2(nn0)}(안 면)~{F2(nn1)}(바깥 면), ss {kit.FR(ss0, ss1)} (다리 끝 {F2(slg.get('ss_tip', ss1))} + 0.3 막힌 끝)"),
             ("O", O_, (-20, -40), f"닿는 점 O: 짧은 다리 {F(R.short_leg_len())} 끝이 바깥 면에 (y{F2(O_[0])} z{F2(O_[1])})"),
             ("E", E_, (22, 30), f"닿는 점 E: 다리가 안 면의 주머니 모서리에 (y{F2(E_[0])} z{F2(E_[1])}) — 팔 {F2(arm)}, 짝 힘 쉼 {F2(Fr)} N · 손 들기 25° {F2(Fh)} N (코일이 봉에서 뜸)"),
             ("w", tuple(slg["end_inner"]), (26, 22), f"홈이 웹 밑면 z{F(L[1])}에서 {F2(slg['web_cut_depth'])} 올라감 (막힌 끝 z{F2(max(q_[1] for q_ in slg['band']))}, 웹 밑면 깎음)"),
             ("s", add(Lp, mul(fb, n_s), mul(3.6, t_s)), (-30, -20),
              f"넣는 슬롯 {F(a_s)}° (+y에서 CW {F(-a_sd)}°) 면 ±{F2(fa)} (폭 {F(fa - fb)}): 스프링을 짧은 다리 끝부터 홈 방향으로 넣음 — 위 면 +{F2(fa)} 쪽은 긴 다리 창까지 열림"),
             ("l", add(Lp, mul(3.2, t_w), mul(f_w, n_w)), (-8, 40),
              f"긴 다리 창 {F(a_w)}°, 윗면 +{F(f_w)}: 긴 다리가 레버 {F(sp['leg_range_deg'][0])}°~{F(sp['leg_range_deg'][1])}° 내내 면과 {F2(sp['leg_slot_margin'])} 이상")]
    callouts(v, items, u0 - 20 / s_ + v.px(6), w0 - v.px(14), line_px=14.5, size_px=9.8)
    return v


def rear_groove_detail(g):
    """r4.5 detail H: the rear-wall spring groove of lever D seen from above (plane z = middle of the groove):
    boss 4.4 on the rear-wall face, groove 2.4 wide x 3.2 deep (2.0 into the wall, 1.0 of wall behind), the long leg
    cut by the plane (it leaves the coil's +x end and rises straight), the lever centre and the pocket / coil x."""
    sp = SOL["spring"]
    gr = next(t for t in sp["grooves"] if t["lever"] == "D")
    xc = g["xc"]
    boss = next(p for p in fixed() if p["part"] == "spring groove boss" and p["x"][0] < xc < p["x"][1])
    wall = next(p for p in fixed() if p["part"] == "rear wall" and p["x"][0] < xc < p["x"][1])
    zc = (gr["z"][0] + gr["z"][1]) / 2
    by0, by1 = bbox(pts(boss))[:2]
    wy0, wy1 = bbox(pts(wall))[:2]
    u0, u1, w0, w1 = boss["x"][0] - 1.6, boss["x"][1] + 1.6, by0 - 2.2, wy1 + 0.8
    s_ = 40.0
    v = View(u0 - 120 / s_, w0 - 150 / s_, u1 + 150 / s_, w1 + 30 / s_, px_width=(u1 - u0) * s_ + 270, pad_px=4)
    P = pids(v)
    fill_rings(v, union_rings([rect(u0, u1, wy0, wy1), rect(boss["x"][0], boss["x"][1], by0, by1)]), "m-print", P["print"])
    v.poly(rect(gr["x"][0], gr["x"][1], gr["y"][0], gr["y"][1]), cls="void")
    lg = spring_parts_b("D")[2]
    for z0_, z1_ in [(zc, zc)]:
        ys = yslice([(t_[1], t_[0]) for t_ in pts(lg, "rest")], zc)      # the leg band sliced at z = zc (swap to slice along z)
        for a_, b_ in ys:
            hpoly(v, rect(lg["x"][0], lg["x"][1], a_, b_), "m-steel", P["steel"])
    coil = spring_parts_b("D")[0]
    # r4.5 fix: the coil (OD about L: y{L-3.0}~{L+3.0}) runs out of the window at its bottom edge: drawn open there
    # (it was a closed 0.55-high box that read as a thin part)
    cy1 = L[0] + (sp["ID"] + 2 * sp["d"]) / 2
    v.poly([(coil["x"][0], w0), (coil["x"][0], cy1), (coil["x"][1], cy1), (coil["x"][1], w0)], cls="phan", closed=False)
    v.cl(xc, w0, xc, w1)
    panel_title(v, u0 - 120 / s_ + v.px(4), w1 + v.px(14), f"확대 H (r4.5 고침): 뒷벽 스프링 홈 D, 위에서 (z{F(zc)}) — 홈 가운데 = 긴 다리 x", size_px=11.5)
    v.dim_h(boss["x"][0], boss["x"][1], by0 - 1.0, text=f"보스 {F(boss['x'][1] - boss['x'][0])}", ext_from=(by0, by0), size_px=9.5)
    v.dim_h(gr["x"][0], gr["x"][1], by0 - 0.35, text=f"홈 {F(gr['x'][1] - gr['x'][0])}", ext_from=(by0, by0), size_px=9.5)
    v.dim_v(gr["y"][0], gr["y"][1], boss["x"][1] + 0.7, text=f"{F(gr['y'][1] - gr['y'][0])}", ext_from=(gr["x"][1], gr["x"][1]), size_px=9.5, left=False)
    v.dim_v(gr["y"][1], wy1, boss["x"][1] + 0.7, text=f"{F(wy1 - gr['y'][1])}", ext_from=(gr["x"][1], gr["x"][1]), size_px=9.5, left=False)
    v.dim_v(by0, by1, u0 + 0.5, text=f"{F(by1 - by0)}", ext_from=(boss["x"][0], boss["x"][0]), size_px=9.5)
    xl = (lg["x"][0] + lg["x"][1]) / 2
    # r4.5 fix: boss + groove centred on the long leg's x (lever x + groove_dx), not on the lever
    xg = (gr["x"][0] + gr["x"][1]) / 2
    v.cl(xg, by0 - 0.2, xg, w1)
    v.dim_h(xc, xg, wy1 + 0.45, text=f"+{F(sp.get('groove_dx', xg - xc))}", ext_from=(wy1, wy1), size_px=9, tpos="right")
    chm = next((p for p in fixed() if p["part"].startswith("spring groove entry chamfer") and p["x"][0] < xc < p["x"][1]), None)
    ch_txt = (f"입구 {F(gr.get('chamfer', 0.5))}×45° 모따기 x{F2(chm['x'][0])}~{F2(chm['x'][1])} (암 부품 'spring groove entry chamfer', P18)"
              if chm else f"입구 {F(gr.get('chamfer', 0.5))}×45° 모따기 (P18)")
    note_lines(v, [f"홈 y{F(gr['y'][0])}~{F(gr['y'][1])} × z{F(gr['z'][0])}~{F(gr['z'][1])} × x{F2(gr['x'][0])}~{F2(gr['x'][1])} (뒷벽 안 {F(gr['y'][1] - wy0)}, 뒤에 {F(wy1 - gr['y'][1])} 남음)",
                   f"r4.5 고침: 보스·홈 가운데 = 레버 x + {F(sp.get('groove_dx', xg - xc))} (긴 다리 x{F2(xl)}, 레버에서 +{F2(xl - xc)})",
                   f"{ch_txt} — 보스 밑면 z{F(gr['z'][0])}의 홈 입구라 이 z{F(zc)} 단면 밑에 있어 안 보임",
                   f"회색 = z{F(zc)}에서 잘린 긴 다리 (코일 +x 끝에서 곧게) · 가상선 = 코일 x{kit.FR(coil['x'][0], coil['x'][1])} (y{F2(cy1)}까지) · 쇄선 = 레버 중심 x{F2(xc)} / 홈 가운데 x{F2(xg)}"],
               u0 - 110 / s_, w0 - v.px(40), line_px=14, size_px=9.5)
    return v


def spring_parts_b(nm):
    return R.spring_parts(nm)


def sheet_lever():
    g = lever_geom()
    xc = g["xc"]
    lt = g["lt"]
    lb = R._labels()
    sg = R.spring_geom()
    # ------------------------------------------------ view 1: side section at the carrier centre (b = 0)
    U0, U1, V0, V1 = 127.0, 236.0, -1.5, 60.0
    v = View(U0, V0, U1, V1, px_width=1480, pad_px=6)
    P = pids(v)
    for p in lev_parts():        # beyond the cut (x < xc): side wall L, collar, lips
        if p["x"][1] < xc and not p["part"].startswith(("hub", "web")):
            v.poly(pts(p, "rigid0"), cls="vis")
    cut = [pts(p, "rigid0") for p in lev_parts() if cut_x(p, xc) and not p["part"].startswith(("steel", "felt"))]
    fill_rings(v, union_rings(cut), "m-lever", P["lever"])
    hpoly(v, g["stl"], "m-steel", P["steel"])
    # r4.4 fix 2: the side wall L (beyond the cut) is lower than the steel top over y163~184 -> hidden behind the steel
    wp_ = g["wpad"]
    v.poly([(wp_[0][0], g["zt_st"])] + wp_ + [(wp_[-1][0], g["zt_st"])], cls="hid", closed=False)
    v.poly(g["felt"], cls="m-felt")
    # r4.5: the centre plane runs through the spring pocket (lever parts 'spring pocket section A / B' = pocket D6.6, slot,
    # short-leg groove, web cut); the MISUMI spring as exported in the 0-deg pose: coil cut, short leg beyond, long leg in front
    R.draw_spring(v, "D", xc, pose="rigid0")
    v.circle(L[0], L[1], g["bore"] / 2, cls="m-steel")
    v.cl(L[0] - g["hub_r"] - 2.5, L[1], L[0] + g["hub_r"] + 2.5, L[1])
    v.cl(L[0], L[1] - g["hub_r"] - 2.5, L[0], L[1] + g["hub_r"] + 2.5)
    v.cl(g["cap_c"][0] - 1.0, g["cap_c"][1], g["cap_c"][0] + 1.0, g["cap_c"][1])
    v.cl(g["cap_c"][0], g["cap_c"][1] - 1.0, g["cap_c"][0], g["cap_c"][1] + 1.0)
    col = L[0] + g["hub_r"] + 2.2
    tabz = (min(q[1] for q in g["tab"]), max(q[1] for q in g["tab"]))
    zf = [(g["felt_z0"], 190.0, "펠트 띠 밑 (S14)"), (g["lip_z0"], 176.0, "아래 립 밑 (D07)"), (g["s_z0"], g["s_y1"], "강철 밑 (S12)"),
          (L[1] - g["hub_r"], L[0], "허브 밑"), (L[1], L[0] + 1.5, "L 레버 봉 (S11)"), (L[1] + g["hub_r"], L[0], f"허브 위 ({lb['hub']})"),
          (L[1] - g["pocket"][0] / 2, L[0], f"스프링 주머니 Ø{F(g['pocket'][0])} 밑 (P18)"),
          (web_exit(g)[1], g["y_rear"], "웹 윗면이 뒷벽에서 나옴"), (g["slope_z"], g["y_rear"], "뒷벽 비탈 시작"),
          (g["zt_st"], g["s_y1"], "강철 윗면 (S12)"),
          (g["zw_pad"], g["wpad"][-1][0], f"옆벽 윗단 y{F(g['lips'][0][1])}~{F(g['lips'][1][0])} (숨은선, 강철 윗면 − {F(g['zt_st'] - g['zw_pad'])}, D07)"),
          (g["z_top"], g["lips"][1][1], "캐리어 윗면 = 윗 립 (S13)")]
    ordz(v, zf, col, gap_px=14, label_px=10)
    ordz(v, [(g["cap_c"][1], g["y_front"], f"R{F(g['cap_r'])} 중심"), (tabz[0], min(q[0] for q in g["tab"]), "손톱 턱 밑 (D08)"),
             (tabz[1], min(q[0] for q in g["tab"]), "손톱 턱 위")], min(q[0] for q in g["tab"]) - 1.4, side="left", gap_px=14, label_px=10)
    yf = [(min(q[0] for q in g["tab"]), g["s_z0"], "손톱 턱 앞 (D08)"), (g["y_front"], g["s_z0"], "앞면 (S13)"), (g["s_y0"], g["s_z0"], "강철 앞 (S12)"),
          (g["cap_c"][0], g["z_top"], f"R{F(g['cap_r'])} 중심"), (lt["cap_end"], g["z_top"], "강철 노출 (S12)"),
          (g["lipA"][0][0], g["lip_z0"], "아래 립 (D07)"), (g["lipA"][1][0], g["lip_z0"], "립 끝·펠트 (S14)"),
          (g["felt"][1][0], g["felt_z0"], "펠트 끝"), (g["lips"][0][1], g["z_top"], "앞 위 립 끝 (D07)"),
          (g["lips"][1][0], g["z_top"], "뒤 위 립 (D07)"),
          (g["s_y1"], g["s_z0"], "강철 뒤 (S12)"), (g["web_y0"], 33.5, "웹 앞"), (g["y_rear"], g["lip_z0"], "뒷면"),
          (max(q[0] for q in g["rfl"]), min(q[1] for q in g["rfl"]), "뒤 바닥 끝 (S13)"),
          (L[0], L[1] - g["hub_r"], "L (S11)"), (L[0] + g["hub_r"], L[1], "허브 뒤")]
    ordy(v, yf, L[1] - g["hub_r"] - 2.0, gap_px=13.5, label_px=10)
    s12n = dns("S12", "note")      # r4.4: [53.7, 3, 9, 50, 21.5, 75.8, 153, 190, 7.4, 163, 184]
    p11 = dns("P11", "note")          # '강철 9 + 접착층 0.10×2 + 옆벽 0.7×2 (r4.4 고침 2b: 주머니 9.2; 앞·뒷벽 0.8)'
    tw_ = top_lip_wh()
    slg = SOL["spring"]["short_leg_groove"]
    items = [("a", (g["y_front"] + 0.4, 42.0), (-60, 30), f"캐리어 PETG — 백·흑 공통 1종, 폭 {F(dn('P11'))} = 강철 {F(p11[0])} + 접착층 {F(p11[1])}×{F(p11[2])} + 옆벽 {F(p11[3])}×{F(p11[4])} (P11, 고침 2b)"),
             ("b", (175.0, 46.0), (0, 58), f"강철 블록 SS400 {'×'.join(F(x) for x in dns('S12', 'item')[1:4])}, {F(s12n[0])} g, 모따기 없음 (S12)"),
             ("c", ((g["tab"][0][0] + g["tab"][1][0]) / 2, (g["tab"][0][1] + g["tab"][2][1]) / 2), (-34, 30),
              f"손톱 턱 {F(dns('D08')[1])} 앞으로 × {F(dns('D08')[2])} (D08) — 빼기 때 레버를 손으로 듦"),
             ("d", (g["cap_c"][0] - g["cap_r"] * 0.7, g["cap_c"][1] + g["cap_r"] * 0.7), (-44, 44), f"앞 윗모서리 R{F(g['cap_r'])} (업스톱 접점 아님, D08)"),
             ("e", (170.0, g["zt_st"] + 0.02), (20, 50), f"드러난 강철 윗면 y{F(s12n[6])}~{F(s12n[7])} (윗 립 사이 {F(s12n[8])}, y{F(s12n[9])}~{F(s12n[10])}는 전폭) = 업스톱 접점 (S12·P16)"),
             ("f", (g["lips"][0][1] - 1.0, g["zt_st"] + 0.5), (40, 40),
              f"위 립 {F(tw_[0])}×{F(tw_[1])} 양쪽: 앞 y{F(g['lips'][0][0])}~{F(g['lips'][0][1])} · 뒤 y{F(g['lips'][1][0])}~{F(g['lips'][1][1])} (패드 옆 끊김, D07, 옆벽 쪽 = 뒤에 보임)"),
             ("g", (170.0, g["lip_z0"] + 0.5), (-30, -44), f"아래 립 {F(g['low_lip'][0])}×{F(g['low_lip'][1])}, y{F(g['lipA'][0][0])}~{F(g['lipA'][1][0])} (D07, 뒤에 보임)"),
             ("h", (186.0, g["felt_z0"] + 0.4), (30, -44), f"밑 펠트 띠 {lb['strip_felt']} × 폭 {F(dns('S14', 'ref')[0])}, 강철 밑면에 붙임, 흑연 (S14)"),
             ("i", (L[0] + g["hub_r"] * 0.7, L[1] - g["hub_r"] * 0.7), (40, -30), f"허브 {lb['hub']}, 구멍 {lb['bore']} (S11) · 칼라 {lb['collar']} (P14)"),
             ("j", (L[0] - sg["r_m"] * 0.7, L[1] + sg["r_m"] * 0.7), (-40, 40),
              f"스프링 주머니 Ø{F(g['pocket'][0])}×{F(g['pocket'][1])} + 코일(미스미 {SOL['spring']['part']}); {R.spring_txt()['slot']} + {R.spring_txt()['window']}; "
              f"r4.5 고침 {R.spring_txt()['groove']}, {R.spring_txt()['web']} (P18·D05, 확대 G)"),
             ("k", (g["web_y0"] + 0.4, 40.0), (40, 26), "웹 (뒷벽 ↔ 허브)"),
             ("l", (158.0, g["s_z0"] + 0.3), (-20, -40), f"{d07_bond()} — 립은 굳는 동안만 잡음 (D07, r4.4 고침 2b)"),
             ("m", ((g["wpad"][0][0] + g["wpad"][-1][0]) / 2 - 3.0, g["zw_pad"]), (-26, -52),
              f"패드 구간 옆벽 윗단 z{F(g['zw_pad'])} (y{F(g['lips'][0][1])}~{F(g['lips'][1][0])}, 숨은선): 옆벽이 패드 밑으로 지나감 (D07, 고침 2)")]
    callouts(v, items, U0 + 1.0, 13.0, line_px=14.5, size_px=10.5)
    scalebar(v, 208.0, 58.5, 10)
    v1 = v
    # ------------------------------------------------ view 2: top and bottom views (u = y, v = local x)
    S2 = 11.0
    y0v, y1v = 117.0, 212.0
    off = 24.0
    w2 = View(y0v - 1.0, -off - 9.0, y1v, 10.0, px_width=(y1v - y0v + 1.0) * S2, pad_px=6)
    P2 = pids(w2)
    T = lambda x: -(x - xc)          # top view: +x down
    B = lambda x: (x - xc) - off     # bottom view: +x up, shifted down
    xl0, xl1 = g["wl"][0], g["wr"][1]
    xs0, xs1 = g["wl"][1], g["wr"][0]
    li = lt["lip_in"]
    cx0, cx1 = g["col"]["x"]
    colr = dns("D06")[0] / 2
    ty0, ty1 = min(q[0] for q in g["tab"]), max(q[0] for q in g["tab"])
    tx0, tx1 = part(LEV, "fingernail tab")["x"]
    for F_ in (T, B):
        lo_, hi_ = sorted((F_(xl0), F_(xl1)))
        hpoly(w2, rect(g["y_front"], L[0] + g["hub_r"], lo_, hi_), "m-lever", P2["lever"])
        c0, c1 = sorted((F_(cx0), F_(cx1)))
        hpoly(w2, rect(L[0] - colr, L[0] + colr, c0, c1), "m-lever", P2["lever"])      # hub collar (P14)
        t0, t1 = sorted((F_(tx0), F_(tx1)))
        hpoly(w2, rect(ty0, ty1, t0, t1), "m-lever", P2["lever"])                      # fingernail tab (D08)
    for sr in R.steel_plan_rects(xc, lt):     # narrow between the top lips (D07 spans y150~168, y184~186), full width beside the pad
        (xa, ya), (xb, yb) = sr[0], sr[2]
        hpoly(w2, rect(ya, yb, T(xb), T(xa)), "m-steel", P2["steel"])
    for yy in (g["cap_c"][0], lt["cap_end"], g["s_y1"], g["y_rear"], g["web_y0"], L[0] - g["hub_r"]):
        w2.line(yy, T(xl1), yy, T(xl0), cls="vis")
    px0, px1 = R.pocket_x("D")
    w2.poly(rect(L[0] - g["pocket"][0] / 2, L[0] + g["pocket"][0] / 2, T(px1), T(px0)), cls="hid")
    y_cl1 = L[0] + g["hub_r"] + 1.0
    yd_ = sum(g["lip_y"]) / 2 + 3.0              # narrow-steel width dimension inside the first top-lip span
    for a_, b_ in ((g["y_front"] - 2.0, yd_ - 1.6), (yd_ + 0.4, y_cl1)):
        w2.cl(a_, T(xc), b_, T(xc))
    w2.cl(L[0], T(xl1) - 2.0, L[0], T(cx0) + 2.0)
    w2.poly(rect(L[0] - g["bore"] / 2, L[0] + g["bore"] / 2, T(xl1), T(cx0)), cls="hid")
    hpoly(w2, rect(g["s_y0"], g["s_y1"], B(xs0), B(xs1)), "m-steel", P2["steel"])
    for p in lev_parts():
        q = pts(p, "rigid0")
        if p["part"] == "bottom lip":
            hpoly(w2, rect(min(t[0] for t in q), max(t[0] for t in q), B(p["x"][0]), B(p["x"][1])), "m-lever", P2["lever"])
        if p["part"] == "carrier rear floor":
            hpoly(w2, rect(min(t[0] for t in q), max(t[0] for t in q), B(p["x"][0]), B(p["x"][1])), "m-lever", P2["lever"])
        if p["part"] == "felt strip":
            w2.poly(rect(min(t[0] for t in q), max(t[0] for t in q), B(p["x"][0]), B(p["x"][1])), cls="m-felt")
    for yy in (g["y_rear"], g["web_y0"], L[0] - g["hub_r"]):
        w2.line(yy, B(xl0), yy, B(xl1), cls="vis")
    for a_, b_ in ((g["y_front"] - 2.0, 184.4), (186.4, y_cl1)):
        w2.cl(a_, B(xc), b_, B(xc))
    w2.cl(L[0], B(cx0) - 2.0, L[0], B(xl1) + 2.0)
    w2.poly(rect(L[0] - g["bore"] / 2, L[0] + g["bore"] / 2, B(cx0), B(xl1)), cls="hid")
    panel_title(w2, y0v + w2.px(2), 10.0 - w2.px(12), "위에서 봄 (+x 아래) — 윗 립 사이로 강철이 보임 · 앞 손톱 턱 · 뒤 허브 칼라", size_px=11.5)
    w2.text(y0v + w2.px(2), B(xl1) + w2.px(26), "밑에서 봄 (+x 위) — 아래 립·펠트 띠·뒤 바닥", cls="ttl", anchor="start", size_px=11.5)
    fx_top = [(T(cx0), L[0], f"x{F2(cx0)} 칼라"), (T(xl0), g["y_front"], f"x{F2(xl0)}"), (T(xs0), g["y_front"], f"x{F2(xs0)} 벽"),
              (T(xs0 + li), lt["cap_end"], f"x{F2(xs0 + li)} 립"), (T(xc), g["y_front"], f"x{F2(xc)} 중심"),
              (T(xs1 - li), lt["cap_end"], f"x{F2(xs1 - li)}"), (T(xs1), g["y_front"], f"x{F2(xs1)}"), (T(xl1), g["y_front"], f"x{F2(xl1)}")]
    ordz(w2, fx_top, y0v + 5.0, side="left", gap_px=11.5, label_px=9, raw=True)
    fe = dns("S14", "ref")[0]
    lw_ = g["low_lip"][0]
    fx_bot = [(B(xl0), g["y_front"], f"x{F2(xl0)}"), (B(xs0), g["y_front"], f"x{F2(xs0)}"), (B(xs0 + lw_), 165.0, f"x{F2(xs0 + lw_)} 립"),
              (B(xc), g["y_front"], f"x{F2(xc)}"), (B(xs1 - lw_), 165.0, f"x{F2(xs1 - lw_)}"),
              (B(xs1), g["y_front"], f"x{F2(xs1)}"), (B(xl1), g["y_front"], f"x{F2(xl1)}"), (B(cx0), L[0], f"x{F2(cx0)} 칼라")]
    ordz(w2, fx_bot, y0v + 5.0, side="left", gap_px=11.5, label_px=9, raw=True)
    w2.dim_v(T(xl1), T(xl0), L[0] + g["hub_r"] + 1.8, text=f"{F2(xl1 - xl0)} (P11)", ext_from=(L[0] + g["hub_r"], L[0] + g["hub_r"]), size_px=9, left=False)
    w2.dim_v(T(xs1 - li), T(xs0 + li), yd_, text=F2(xs1 - xs0 - 2 * li), size_px=9)
    w2.dim_v(B(xs1 - lw_), B(xs0 + lw_), 186.0, text=f"{F2(fe)} 펠트", size_px=9)
    scalebar(w2, 190.0, -off - 8.0, 10)
    # ------------------------------------------------ view 3: steel block part (local: y, z)
    S3 = 6.2
    sw = View(-26.0, -38.0, 62.0, 37.0, px_width=88.0 * S3, pad_px=6)
    Ps = pids(sw)
    sy = [(q[0] - g["s_y0"], q[1] - g["s_z0"]) for q in g["stl"]]
    hpoly(sw, sy, "m-steel", Ps["steel"])
    Ls, Hs = g["s_y1"] - g["s_y0"], g["zt_st"] - g["s_z0"]
    Ws = g["wr"][0] - g["wl"][1]
    hpoly(sw, rect(0, Ls, -Ws - 9.0, -9.0), "m-steel", Ps["steel"])
    hpoly(sw, rect(-Ws - 10.0, -10.0, 0.0, Hs), "m-steel", Ps["steel"])
    sw.dim_h(0, Ls, Hs + 4.0, text=f"{F(Ls)}", ext_from=(Hs, Hs))
    sw.dim_v(0, Hs, Ls + 4.0, text=f"{F(Hs)}", ext_from=(Ls, Ls), left=False)
    sw.dim_h(-Ws - 10.0, -10.0, Hs + 4.0, text=f"{F(Ws)}", ext_from=(Hs, Hs))
    sw.dim_v(-9.0 - Ws, -9.0, Ls + 4.0, text=f"{F(Ws)}", ext_from=(Ls, Ls), left=False)
    panel_title(sw, -26.0 + sw.px(2), 37.0 - sw.px(12), "강철 블록 부품 (S12) — 옆 · 앞 · 위", size_px=11.5)
    sw.text(-10.0 - Ws / 2, -3.2, "앞에서", cls="tx-s", size_px=9.5)
    sw.text(Ls / 2, -3.2, "옆에서", cls="tx-s", size_px=9.5)
    sw.text(Ls / 2, -9.0 - Ws - 3.2, "위에서", cls="tx-s", size_px=9.5)
    note_lines(sw, [f"SS400 평철 {F(Ws)}T×{F(Hs)}를 {F(Ls)} 길이로 절단, 모서리 줄 다듬기, 모따기 없음",
                    f"질량 {F(s12n[0])} g (r3 {F(s12n[5])} g) · 모듈 {len(ORDER)}개 · 88건반 {F(dns('A09')[0])} kg (A09)"],
               -24.0, -26.0, line_px=14, size_px=10)
    # ------------------------------------------------ view 4: x-z stations
    stations = [((min(q[0] for q in g["tab"]) + max(q[0] for q in g["tab"])) / 2, "손톱 턱 (D08)"),
                ((g["s_y0"] + lt["cap_end"]) / 2, f"앞 R{F(g['cap_r'])} 캡"), (160.0, "앞 위 립만"), (170.0, "아래 립만"),
                (sum(g["lips"][1]) / 2, "뒤 위 립 + 펠트 띠"), ((g["y_rear"] + max(q[0] for q in g["rfl"])) / 2, "뒤 바닥"),
                (L[0], "허브 (L) + 스프링 주머니")]
    st = []
    for yy, lab in stations:
        sv = View(xc - 8.2, 26.0, xc + 8.2, 58.5, px_width=16.4 * 12.5, pad_px=6)
        Pq = pids(sv)
        carr, ovr = lever_xz(sv, Pq, yy, g)
        allr = carr + [o[0] for o in ovr]
        zlow = min(q[1] for r_ in allr for q in r_)

        def zend(x):
            c_ = [q[1] for r_ in allr if min(t[0] for t in r_) - 1e-3 <= x <= max(t[0] for t in r_) + 1e-3 for q in r_]
            return min(c_) if c_ else zlow
        sv.cl(xc, zlow - 0.9, xc, 58.5 - sv.px(31))
        panel_title(sv, xc - 8.2 + sv.px(2), 58.5 - sv.px(12), f"y{F2(yy)} {lab}", size_px=10)
        if not R.in_top_lip(yy) and g["lips"][0][1] < yy < g["lips"][1][0]:     # r4.4: say why the top lips are missing here
            sv.text(xc - 8.2 + sv.px(2), 58.5 - sv.px(25), f"패드 옆 y{F(g['lips'][0][1])}~{F(g['lips'][1][0])}: 위 립 없음, 옆벽 z{F(g['zw_pad'])} (D07)",
                    cls="tx-s", anchor="start", size_px=9)
        xs_ = sorted(set(round(q[0], 3) for r_ in allr for q in r_))
        sv.dim_h(xs_[0], xs_[-1], 27.2, text=F2(xs_[-1] - xs_[0]), ext_from=(zend(xs_[0]), zend(xs_[-1])), size_px=9.5)
        st.append(sv)

    # ------------------------------------------------ view 5: capture details (x-z at y170)
    def cap_detail(tag, win, dims_fn, title, y_cut):
        u0, u1, w0, w1 = win
        s_ = 64.0
        dv = View(u0, w0, u1 + 150 / s_, w1 + 16 / s_, px_width=(u1 - u0) * s_ + 150, pad_px=4)
        Pd = pids(dv)
        i0 = clip_begin(dv)
        lever_xz(dv, Pd, y_cut, g)
        clip_end(dv, i0, u0, u1, w0, w1)
        panel_title(dv, u0 + dv.px(2), w1 + dv.px(4), title, size_px=11)
        dims_fn(dv)
        return dv

    def dims_top(dv):
        z0, z1 = g["zt_st"], g["z_top"]
        dv.dim_h(xl0, xs0, z1 + dv.px(14) - 0.05, text=f"{F(xs0 - xl0)} 옆벽", ext_from=(z1, z1), size_px=9)
        dv.dim_h(xs0, xs0 + li, z1 + dv.px(34), text=f"{F(li)} 립", ext_from=(z1, z1), size_px=9, tpos="right")
        dv.dim_v(z0, z1, xs0 + li + dv.px(22), text=f"{F(z1 - z0)}", ext_from=(xs0 + li, xs0 + li), size_px=9, left=False)
        dv.text(xs0 + 2.3 + dv.px(10), (z0 + z1) / 2 - dv.px(3), "위 립 (D07)", cls="tx", anchor="start", size_px=10)
        sx0_ = part(LEV, "steel block")["x"][0]          # r4.4 fix 2b: bond line between the 0.7 wall and the steel (P11)
        dv.dim_h(xs0, sx0_, z0 - 1.1, text=f"{F(sx0_ - xs0)} 접착층 (MS 폴리머)", ext_from=(z0 - 1.5, z0 - 1.5), size_px=9, tpos="right")

    def dims_bot(dv):
        z0, z1 = g["lip_z0"], g["s_z0"]
        dv.dim_h(xs0, xs0 + lw_, z0 - dv.px(16), text=f"{F(lw_)} 립", ext_from=(z0, z0), size_px=9)
        dv.dim_v(z0, z1, xs0 + lw_ + dv.px(22), text=f"{F(z1 - z0)}", ext_from=(xs0 + lw_, xs0 + lw_), size_px=9, left=False)
        dv.text(xs0 + 2.3 + dv.px(10), (z0 + z1) / 2 - dv.px(3), "아래 립 (D07)", cls="tx", anchor="start", size_px=10)

    # r4.4: E is cut where the front top lip exists (y150~163, D07) — at y170 (beside the pad) there is no top lip
    y_E, y_F = 160.0, 170.0
    assert R.in_top_lip(y_E) and low_lip_y()[0] <= y_F <= low_lip_y()[1], (y_E, y_F)
    e1 = cap_detail("E", (xl0 - 0.4, xs0 + 2.3, g["zt_st"] - 1.6, g["z_top"] + 0.8), dims_top, f"확대 E: 위 립 (y{F(y_E)})", y_E)
    e2 = cap_detail("F", (xl0 - 0.4, xs0 + 2.3, g["lip_z0"] - 0.6, g["s_z0"] + 1.6), dims_bot, f"확대 F: 아래 립 (y{F(y_F)})", y_F)
    pp = M["mass"]["print_plan"][2][1]
    bore_print = float(re.search(r"Ø([\d.]+)로 뽑아", pp).group(1))
    gap_sup = float(re.search(r"z 틈 ([\d.]+)", pp).group(1))
    r44 = G["r44"]
    sr_ = r44["steel_retention"]["peaks"]["play"]
    lip_ch = next(c for c in G["changes_this_round"] if "top snap lip, front segment" in c["part"])
    lip43_end = float(re.search(r"over y([\d.]+)~([\d.]+)", lip_ch["old"]).group(2))   # 'lip 0.8 x 1.0 over y150~168 ...'
    nv = View(0, -300, 780, 0, px_width=780, pad_px=6)
    bd_ = r44["steel_retention"]["bond"]
    fix2_wall = next(c for c in G["changes_this_round"] if "side walls in the pad zone" in c["part"])
    note_lines(nv, [f"조립 (D07, r4.4 고침 2b): {d07_bond()}",
                    f"  립은 굳는 동안만 잡음 · 접착 전단 매 음 {F(bd_['play']['tau'], 3)} MPa (기계 {F(bd_['play']['tau_mech'], 3)} + 열 {F(bd_['play']['tau_th'], 3)}, 허용 {F(bd_['play']['limit'], 3)}), "
                    f"드문 경우 {F(bd_['abuse']['tau'], 3)} (허용 {F(bd_['abuse']['limit'], 3)}); 고침 2의 5분 에폭시는 열 전단 {F(bd_['play']['epoxy_th'])} MPa로 떨어짐.",
                    f"  패드 구간 옆벽 윗단 z{F(g['zw_pad'])} = 강철 윗면 − {F(g['zt_st'] - g['zw_pad'])}: 축 놀음·패드 바 옆 놀음에도 옆벽 ↔ 패드 {re.search(r'now ([0-9.]+)', fix2_wall['why']).group(1)}.",
                    f"출력: 옆벽을 베드에 눕혀, 강철 칸 안 지지대 1개(z 틈 {F(gap_sup)}) · 허브 칼라·스프링 주머니 함께 출력.",
                    f"허브 구멍은 Ø{F(bore_print)}로 출력 → Ø{F(g['bore'])} 드릴 (S11). 캐리어 {F(round(M['mass']['lever_carrier_g'], 1))} g.",
                    f"r4.5 고침 스프링 미스미 {SOL['spring']['part']} (두 다리 잘라 씀): 레버 봉을 넣기 전 스프링을 짧은 다리 끝부터",
                    f"  홈 방향({F2(slg.get('band_deg', slg['leg_dir']))}°)으로 {R.spring_txt()['slot']}에 밀어 넣으면 {R.spring_txt()['short']}이",
                    f"  {R.spring_txt()['groove']} 끝까지 들어가 갇힘 (닿는 점: {R.spring_txt()['contacts']}).",
                    f"  긴 다리 {F(sg['leg'])}는 코일 +x 끝에서 {R.spring_txt()['window']}을 지나 뒷벽 {F(SOL['spring']['groove'][3])} 홈 ({R.spring_txt()['dx']} 가운데, P18, 도면 8·9).",
                    f"쉼 각 백 {F2(dns('S13', 'note')[0])}° / 흑 {F2(dns('S13', 'note')[1])}° (캡스턴 펠트 눌림, S13) — 부품도는 0°.",
                    f"r4.4 위 립 (D07): 앞 립을 y{F(g['lips'][0][1])}에서 끊음 — r4.3(y{F(lip43_end)}까지)은 1 N 바닥·ff에서 패드 옆 {F2(r44['lip43']['d'])}",
                    f"  → 이제 립 ↔ 패드 {F2(r44['lip44']['pad'])} · 패드 바 레일 {F2(r44['lip44']['rail'])} (FDM ±0.3 뒤에도 1.0 이상).",
                    f"  뒤 립 y{F(g['lips'][1][0])}~{F(g['lips'][1][1])} ({F(g['lips'][1][1] - g['lips'][1][0])} 길이): 캡스턴이 강철 뒤를 립에 밀어 올리는 힘 {F(sr_['T_rear'], 1)} N (PLAY 최대)",
                    f"  → 층을 가로지르는 뿌리 굽힘 {F2(sr_['sig_rear'])} MPa ≤ {F(sr_['limit'])} (r4.3 2 mm 립이면 {F2(sr_['sig_rear_r43'])})."],
               4.0, -14.0, line_px=19, size_px=11.5)
    rows = [[v1], [w2, sw], st, [e1, e2, nv], [hub_pocket_detail(g), rear_groove_detail(g)]]
    base = os.path.join(OUT, "d07_lever_carrier_steel")
    page(rows, base, "도면 7. 레버 부품도 — 출력 캐리어 + SS400 강철 블록 (백·흑 공통 1종)",
         f"레버 각 0° (geometry side_rigid0) · 단면 x = {F2(xc)} (레버 D 중심 = 스프링 주머니 가운데) · 단위 mm · 숫자 = geometry.json (괄호 = 치수표 번호) · "
         "연두 빗금 = PETG 캐리어, 회색 빗금 = 강철, 빨강 = 펠트, 가는 실선 = 단면 뒤에 보이는 옆벽·립·칼라")
    rec(7, base, "레버 캐리어 + 강철 블록 부품도",
        f"레버(백·흑 공통 1종)를 0°로 놓은 부품도. 위: 캐리어 중심 측면 단면(모든 z·y 좌표; 손톱 턱, 앞 R{F(g['cap_r'])} 모서리, 드러난 강철 윗면 = 업스톱 접점, "
        f"립·펠트·허브 {lb['hub']}·구멍 {lb['bore']}·스프링 주머니). 가운데: 위·밑에서 본 평면(윗 립 사이 강철 폭, 허브 칼라, 아래 립·펠트 띠)과 "
        f"강철 블록 부품 {'×'.join(F(x) for x in dns('S12', 'item')[1:4])}(모따기 없음). 아래: y 위치별 가로 단면 {len(st)}개와 확대 E·F(E: 위 립 {lb['top_lip']}를 앞 립이 있는 y160에서, F: 아래 립 {lb['low_lip']}를 y170에서; y170 단면은 아래 립만). "
        f"위 립은 y{F(g['lips'][0][0])}~{F(g['lips'][0][1])}·{F(g['lips'][1][0])}~{F(g['lips'][1][1])} 두 구간(r4.4: 앞 립을 y{F(g['lips'][0][1])}에서 끊어 패드 옆 y{F(g['lips'][0][1])}~{F(g['lips'][1][0])}는 립 없이 강철 전폭·옆벽 윗단 z{F(g['zw_pad'])}(고침 2: 강철 윗면보다 {F(g['zt_st'] - g['zw_pad'])} 낮음), 뒤 립은 강철 뒤끝 y{F(g['lips'][1][1])}까지); "
        f"{d07_bond()}(립은 굳는 동안만); "
        f"립 ↔ 패드 {F2(G['r44']['lip44']['pad'])}·레일 {F2(G['r44']['lip44']['rail'])}, 뒤 립 뿌리 {F2(G['r44']['steel_retention']['peaks']['play']['sig_rear'])} MPa. "
        f"r4.4 고침 2b: 옆벽 {F(dns('P11', 'note')[3])}(주머니 {F(dns('P11', 'note')[7])}, 접착층 {F(dns('P11', 'note')[1])}), 위 립 {lb['top_lip']}, MS 폴리머 접착. "
        f"r4.5: 허브 스프링 주머니 Ø{F(SOL['spring']['pocket'][0])} — r4.5 고침: 짧은 다리 {F(R.short_leg_len())}를 가두는 {R.spring_txt()['groove']}(닿는 점 {R.spring_txt()['contacts']}, {R.spring_txt()['web']}), "
        f"{R.spring_txt()['slot']}(짧은 다리 끝부터 넣음) + {R.spring_txt()['window']} — 주머니 구간은 두 조각 A·B (확대 G, P18), 뒷벽 홈 {F(SOL['spring']['groove'][3])}×{F(SOL['spring']['groove'][4])}·보스 {F(SOL['spring']['boss'][0])}는 {R.spring_txt()['dx']} 가운데(긴 다리 x), 입구 0.5×45° 모따기 (확대 H), "
        f"미스미 {SOL['spring']['part']} 스프링.")


# ================================================================ sheet 8: frame part drawing
def prect(p):
    q = pts(p)
    return rect(p["x"][0], p["x"][1], min(t[0] for t in q), max(t[0] for t in q))


def is_fem(n):
    return n.startswith(("rear dovetail (female", "front dovetail (female"))


def frame_part(n):
    return is_frame(n) and not is_fem(n)


def boss_bore():
    """fin-boss bore: printed Ø3.9 teardrop, drilled Ø4.0 (S11 note / P22 ref)."""
    return dns("S11", "note")[4]


def rod_end_parts():
    """P22 note '왼쪽 끝 핀에 출력 마개 1.2, 오른쪽 끝 핀은 막힌 벽 1.2' -> (plug length, blind wall thickness)."""
    n = dns("P22", "note")
    return n[0], n[1]


def grooves_x():
    return [tuple(sorted((q[0][0], q[1][0]))) for q in ([tuple(t) for t in g["poly"]] for g in plan_all("torsion spring groove"))]


def screw_bore(p):
    """P35 screw-boss bore from the part name -> (x centre, y centre, d, z0, z1).  r4.4 fix 2b: the boss hangs over the
    board ('... screw bore D2.5 to z15.4)'): blind bore from the boss underside (board top) up to z15.4; the centre is
    the plan circle (the part prism is the bracket).  Earlier floor stand-off ('bore D2.5 to z4.2'): down to z4.2."""
    n = p["part"]
    nb = nums(n)
    q = bbox(pts(p))
    xc_ = (p["x"][0] + p["x"][1]) / 2
    yc_ = next((t[1] for t in R.standoffs() if abs(t[0] - xc_) < 1e-6 and q[0] - 1e-6 <= t[1] <= q[1] + 1e-6), (q[0] + q[1]) / 2)
    if "hung" in n:
        return xc_, yc_, nb[1], q[2], nb[2]
    return xc_, yc_, nb[1], nb[2], q[3]


def is_screw_boss(n):
    return n.startswith(("control-board stand-off", "control-board boss")) and "bore" in n


def frame_side(v, P, xs, src=None):
    """y-z section of the frame alone at x = xs: printed frame (union) with the fin-boss bore (drilled), balance pins
    (steel, pressed in), spring-leg groove in the rear wall when the plane runs through it."""
    fx = [p for p in fixed(src) if cut_x(p, xs)]
    fill_rings(v, union_rings([pts(p) for p in fx if frame_part(p["part"])]), "m-print", P["print"])
    for p in fx:
        if is_fem(p["part"]):
            v.poly(pts(p), cls="void")
    for p in fx:
        n = p["part"]
        if n.startswith("fin boss bore"):                  # r4.4: exported bore prism (D18)
            v.poly(pts(p), cls="void")
            v.cl(L[0] - 5, L[1], L[0] + 5, L[1])
            v.cl(L[0], L[1] - 5, L[0], L[1] + 5)
        elif n.startswith("balance pin"):
            hpoly(v, pts(p), "m-steel", P["steel"])
        elif is_screw_boss(n):                                          # P35 screw-boss hole (r4.4 fix 2b: blind, from below)
            xc_, yc, d_, z0_, z1_ = screw_bore(p)
            h_ = math.sqrt(max(0.0, (d_ / 2) ** 2 - (xs - xc_) ** 2))
            if h_ > 0:
                v.poly(rect(yc - h_, yc + h_, z0_, z1_), cls="void")
    sg = spring_geom()
    if src is None and any(a <= xs <= b for a, b in grooves_x()):
        v.poly(rect(sg["groove"][0], sg["groove"][1], sg["groove"][2], sg["groove"][3]), cls="void")
    return fx


def frame_xz(v, P, y, src=None, width=None):
    W = dn("P01") if width is None else width
    rects, fem, over = [], [], []
    for p in fixed(src):
        n = p["part"]
        for z0, z1 in yslice(pts(p), y):
            r_ = rect(p["x"][0], p["x"][1], z0, z1)
            if is_fem(n):
                fem.append(r_)
            elif frame_part(n):
                rects.append(r_)
            elif n.startswith("balance pin"):
                over.append((r_, "m-steel"))
    for (ya, yb), zt in (((dns("D09", "ref")[0], dns("D09", "ref")[1]), dns("D09")[4]),
                         ((dns("D09", "ref")[2], dns("D09", "ref")[3]), dns("D09")[6])):
        if ya <= y <= yb and width is None:
            rects.append(rect(W, W + dns("D09")[2], dns("D09")[3], zt))
    fill_rings(v, union_rings(rects, res=0.03), "m-print", P["print"])
    for r_ in fem:
        v.poly(r_, cls="void")
    sg = spring_geom()
    if src is None and sg["groove"][0] <= y <= sg["groove"][1]:
        for a, b in grooves_x():
            v.poly(rect(a, b, sg["groove"][2], sg["groove"][3]), cls="void")
    for p in bore_parts(src):                     # r4.4 (D18): drilled Ø4.0 bores (right end fin blind) and the printed plug
        for z0, z1 in yslice(pts(p), y):
            v.poly(rect(p["x"][0], p["x"][1], z0, z1), cls="void")
    pp_ = plug_part(src)
    for z0, z1 in yslice(pts(pp_), y):
        hpoly(v, rect(pp_["x"][0], pp_["x"][1], z0, z1), "m-print2")
    for p in fixed(src):                          # P35: screw-boss hole Ø2.5 (r4.4 fix 2b: blind, from the board top up to z15.4)
        n = p["part"]
        if is_screw_boss(n):
            xc_, yc_, d_, z0_, z1_ = screw_bore(p)
            h_ = math.sqrt(max(0.0, (d_ / 2) ** 2 - (y - yc_) ** 2))
            if h_ > 0:
                v.poly(rect(xc_ - h_, xc_ + h_, z0_, z1_), cls="void")
    for r_, c in over:
        hpoly(v, r_, c, P["steel"])


def sheet_frame():
    W = dn("P01")
    D = dns("A05")[0]
    FX = fixed()
    sg = spring_geom()
    lb = R._labels()
    plate = fpart("top plate (ledge + bridge)")
    plq = pts(plate)
    # ------------------------------------------------ plan (top plate removed)
    U0, U1, V0, V1 = -52.0, 236.0, -53.5, 262.0          # r4.5 circuit 2nd: one more note line (ledge, P36)
    v = View(U0, V0, U1, V1, px_width=1480)
    P = pids(v)
    v.rect(0, 0, W, D, cls="faintfill")
    v.poly(R.hatch_plan(), cls="void")                 # r4.4 fix 2b (P35): no floor under the control board
    groups = [("white front rail", "m-print"), ("black stop rail", "m-print"), ("black tab base", "m-print"),
              ("balance rail (lowered", "m-print"), ("balance rail cradle", "m-print2"), ("rod end stop post", "m-print2"),
              ("rear shelf", "m-print"), ("rear wall", "m-print"), ("tab ", "m-print2"), ("keeper hook", "m-print2"),
              ("fin", "m-print"), ("rear dovetail male", "m-print"), ("front dovetail male", "m-print"),
              ("spring groove boss", "m-print")]       # r4.5: 4.4-wide bosses on the rear-wall face (P18)
    for key, cls in groups:
        for p in FX:
            if p["part"].startswith(key) and not is_boss(p["part"]):
                hpoly(v, prect(p), cls, P["print"] if cls == "m-print" else None)
    for p in FX:
        if is_boss(p["part"]):
            hpoly(v, prect(p), "m-print2")
    for p in FX:                                 # r4.4 (P36): v3 sensor-board support post + ribs, printed with the floor
        if p["part"].startswith("sensor board support"):
            hpoly(v, prect(p), "m-print", P["print"])
    for p in R.ledge_parts():                    # r4.5 circuit 2nd (P36): sensor-bar right ledge, lip + post (v3 P112)
        hpoly(v, prect(p), "m-print", P["print"])
    for p in R.board_boss_plan():                # r4.4 fix 2b (P35): bosses hung over the board, brackets to the rail / shelf ribs
        hpoly(v, [tuple(t) for t in p["poly"]], "m-print2")
        v.circle(p["circle"][0], p["circle"][1], p["circle"][2], cls="m-print2")
    for p in PLAN:
        if p["part"].startswith("control-board locating pin"):
            v.circle(p["circle"][0], p["circle"][1], p["circle"][2], cls="m-print")
    for p in FX:
        if is_screw_boss(p["part"]):
            xc_, yc_, d_, _, _ = screw_bore(p)
            v.circle(xc_, yc_, d_ / 2, cls="void")
    for a, b in grooves_x():                     # spring-leg grooves in the rear wall inner face (P18)
        v.poly(rect(a, b, sg["groove"][0], sg["groove"][1]), cls="void")
    ss0, ss1 = shelf_slot()                   # r4.3: open slot in the rear shelf over the USB plug (P19)
    sq = [tuple(t) for t in plan_item("rear shelf slot over the USB plug (open)")["poly"]]
    v.dim_h(ss0, ss1, sq[0][1] + 1.6, text="", ext_from=(sq[0][1] + 1.6, sq[0][1] + 1.6), size_px=8.5)   # r4.4: label by leader (items)
    for p in FX:
        if p["part"] == "shelf rib":
            v.poly(prect(p), cls="hid")
    for fem, male in dovetail_polys():
        v.poly(fem, cls="void")
        hpoly(v, male, "m-print", P["print"])
    for p in FX:
        if p["part"].startswith("balance pin"):
            q = prect(p)
            c = ((q[0][0] + q[1][0]) / 2, (q[0][1] + q[2][1]) / 2)
            v.circle(c[0], c[1], (q[1][0] - q[0][0]) / 2, cls="m-steel")
    # above the plan: top plate (phantom) and the pad-bar rails under it (phantom, z above the plate underside)
    v.poly(ppoly("top plate"), cls="phan")
    for p in plan_all("pad bar rail"):
        v.poly([tuple(q) for q in p["poly"]], cls="phan")
    s28 = dns("S28", "note")
    v.poly(rect(s28[0], s28[1], dns("S28")[0], dns("S28")[1]), cls="hid")
    for ring in board_rings():                # control board with the r4.1 slot for the F|F# fin foot (P23)
        v.poly(ring, cls="env")
    v.poly(ppoly("USB plug"), cls="env")
    # r4.3 circuit interface (BRD-01, P27): board parts, keep-out around the fin foot, ribbon lane under the rail (P20)
    for nm_ in ("RP2040-Zero (on pin headers)", "USB-C receptacle", "CD74HC4067 module", "J301 ribbon 2x8 pads", "J302 EXT 1x6 pads"):
        v.poly([tuple(t) for t in plan_item(nm_)["poly"]], cls="env")
    v.poly([tuple(t) for t in plan_item("board keep-out (no parts / wires)")["poly"]], cls="zone")
    v.poly([tuple(t) for t in plan_item("ribbon lane under the balance rail (z5-10)")["poly"]], cls="hid")
    for nm_ in ("sensor board SB", "16-core ribbon SB J201", "16-core ribbon under the board", "SB J201 ribbon 2x8 pads"):
        v.poly([tuple(t) for t in next(p for p in PLAN if p["part"].startswith(nm_))["poly"]], cls="env")
    for p in PLAN:                               # M3 screw heads on the board (envelope)
        if p["part"].startswith("control-board screw"):
            v.circle(p["circle"][0], p["circle"][1], p["circle"][2], cls="env")
    fins = SOL["fins"]
    top = [(sum(f) / 2, 209.0, f"핀 {F2(f[1] - f[0])}") for f in fins] + \
          [((p["x"][0] + p["x"][1]) / 2, 209.0, "리브") for p in FX if p["part"] == "shelf rib"]
    ordy(v, top, 222.0, side="above", gap_px=12.5, label_px=9)
    v.text(-3.0, 226.0, "핀·리브 중심 x (P12·P19)", cls="tx-s", anchor="end", size_px=9.5)
    tabs = [((p["x"][0] + p["x"][1]) / 2, 14.8 if "#" not in p["part"] else 80.8, p["part"][4:]) for p in FX if p["part"].startswith("tab ")]
    ordy(v, tabs, -6.0, gap_px=12.5, label_px=9)
    v.text(-3.0, -12.0, "가이드 탭 중심 x (P31)", cls="tx-s", anchor="end", size_px=9.5)
    fr = fpart("white front rail")
    tabw = fpart("tab C")
    hk = fpart("keeper hook C")
    bsr = fpart("black stop rail C#")
    btb = fpart("black tab base C#")
    tbb = fpart("tab C#")
    hkb = fpart("keeper hook C#")
    rail = ppoly("balance rail")
    pin = pts(fpart("balance pin D2 C"))
    fin_f = next(p for p in FX if p["part"] == "fin" and p["x"][0] > 40 and bbox(pts(p))[0] < 160)
    boss = boss_parts()[1]
    shelf = fparts("rear shelf")[0]
    rib = next(p for p in FX if p["part"] == "shelf rib")
    prail = fparts("pad bar rail")[0]
    sbp_ = fparts("sensor board support post")[0]
    sbf_ = fparts("sensor board support rib front")[0]
    sbr_ = fparts("sensor board support rib rear")[0]
    yl = [(0.0, 0.0, "앞끝"), (bbox(pts(fr))[0], 0.5, "앞 레일 (S21 펠트 자리)"), (bbox(pts(hk))[0], 9.15, "키퍼 훅"),
          (bbox(pts(tabw))[0], 8.0, "백 탭 앞면 (P31)"), (bbox(pts(tabw))[1], 8.0, "백 탭 뒤"), (bbox(pts(fr))[1], 0.5, "앞 레일 끝"),
          (bbox(pts(bsr))[0], 15.5, "흑 멈춤 레일 (D12)"), (bbox(pts(bsr))[1], 15.5, "흑 레일 끝"), (bbox(pts(hkb))[0], 18.6, "흑 키퍼 훅"),
          (bbox(pts(btb))[0], 17.2, "흑 탭 받침"), (bbox(pts(tbb))[0], 17.5, "흑 탭 앞면 (P31)"), (bbox(pts(tbb))[1], 17.5, "흑 탭 뒤"),
          (bbox(pts(btb))[1], 17.2, "받침 끝"), (rail[0][1], 0.3, "밸런스 레일 (P20)"), ((pin[0][0] + pin[1][0]) / 2, 6.6, "밸런스 핀 (P32)"),
          (K[0], 0.3, "봉 K (S03)"), (rail[2][1], 0.3, "레일 뒤"), (bbox(plq)[0], 0.2, "윗판 앞 (P15)"), (bbox(pts(fin_f))[0], 40.8, "핀 앞 (S29)"),
          (dns("P12", "ref")[2], 40.8, f"핀 두께 {F(dns('P12', 'ref')[1])}부터"), (bbox(pts(prail))[0], 1.8, "패드 바 레일 (P13)"),
          (bbox(pts(prail))[1], 1.8, "레일 끝"),
          (bbox(pts(shelf))[0], 0.0, "뒤 선반 (P19)"), (bbox(pts(rib))[0], 7.4, "리브"), (dns("D09", "ref")[2], 0.0, "뒤 도브테일 (D09)"),
          (bbox(pts(boss))[0], 0.2, f"핀 보스 {lb['boss']}"), (L[0], 0.2, "L (S11)"), (bbox(pts(boss))[1], 0.2, ""), (dns("D09", "ref")[3], 0.0, ""),
          (dns("S28")[0], 0.0, "뒷벽·스프링 홈 (S28·P18)"), (D, 0.0, "뒤끝 (A05)"), (dns("D09", "ref")[0], 0.0, "앞 도브테일"), (dns("D09", "ref")[1], 0.0, ""),
          (bbox(pts(sbp_))[0], 0.5, "센서 기판 받침 기둥 (P36)"), (bbox(pts(sbf_))[0], 6.0, "앞 리브"), (bbox(pts(sbf_))[1], 6.0, ""),
          (bbox(pts(sbr_))[0], 6.0, "뒤 리브"), (bbox(pts(sbr_))[1], 6.0, ""), (bbox(pts(sbp_))[1], 0.5, "기둥 끝"),
          (R.standoffs()[0][1], 47.0, "기판 보스 앞 (P35)"), (R.standoffs()[-1][1], 47.0, "기판 보스 뒤"),
          (bbox(R.hatch_plan())[2], 46.25, "바닥 구멍 (P35)"), (bbox(R.hatch_plan())[3], 78.53, "구멍 끝 (USB 뒤)")]
    ordz(v, yl, -8.0, side="left", gap_px=11.5, label_px=9, prefix="y")
    Rr = W + 30.0
    boss_r = boss_parts()[-1]
    lg_ = R.ledge_parts()                          # r4.5 circuit 2nd (P36): [lip front, post front, lip rear, post rear]
    lg_ = sorted(lg_, key=lambda p: (bbox(pts(p))[0], p["x"][0]))
    CL_ = G["circuit_r45"]["ledge"]
    ko_ = [tuple(t) for t in plan_item("board keep-out (no parts / wires)")["poly"]]
    rl_ = [tuple(t) for t in plan_item("ribbon lane under the balance rail (z5-10)")["poly"]]
    items = [(W + 2.0, 203.5, 226.0, "도브테일 수 (D09) → 오른쪽 모듈 홈"),
             ((boss_r["x"][0] + boss_r["x"][1]) / 2, L[0] + 2.0, 238.0, f"핀 보스 {lb['boss']} (프레임), 구멍 {lb['bore']} (D06·S11)"),
             (ss1 - 1.2, sq[0][1] + 1.6, 205.0, f"선반 홈 x{F2(ss0)}~{F2(ss1)} = {F2(ss1 - ss0)}, USB 플러그 위 뚫림 (P19)"),
             (grooves_x()[-1][1], sg["groove"][1], 214.0, f"스프링 다리 홈 {F(sg['gw'])}×{F(sg['groove'][1] - sg['groove'][0])}, z{F(sg['groove'][2])}~{F(sg['groove'][3])} × {len(grooves_x())}, 보스 {F(SOL['spring']['boss'][0])} (P18, r4.5)"),
             (163.5, 190.0, 197.0, f"핀 {len(fins)}장 (P12), 앞 연장 y{F(dns('P12', 'ref')[4])}~{F(dns('P12', 'ref')[5])} {F(dns('P12', 'ref')[6])} 얇게 (F|F# y{F(bbox(R.keel_plan())[3])}~)"),
             (fparts("pad bar rail")[-1]["x"][0] + 0.5, 178.0, 180.0, f"패드 바 L 레일 {sum(1 for p_ in FX if p_['part'] == 'pad bar rail')}개 = 웹 + 립 (윗판 밑, 가상선, P13)"),
             (150.0, 176.0, 166.0, f"윗판 (가상선, P15): 맨 위 {lb['top']}"),
             (93.0, 186.0, 188.5, "RP2040-Zero + USB-C 리셉터클 (P27)"),
             (117.0, 165.0, 162.0, f"제어 기판 z{F(dns('P23')[4])}~{F(dns('P23')[5])} + 핀 발 홈 (P23)"),
             (ko_[1][0], 150.0, 150.5, f"주황 칸 = 부품·배선 금지 x{F2(ko_[0][0])}~{F2(ko_[1][0])}, y~{F2(ko_[2][1])} (P23)"),
             (rl_[1][0] - 1.0, 138.0, 138.0, f"리본 차선 x{F(rl_[0][0])}~{F(rl_[1][0])}, 레일 밑 z5~10 (P20, 숨은선)"),
             (163.7, 141.0, 144.0, "봉 끝 멈춤 기둥 (P21)"),
             (R.standoffs()[1][0] + R.standoffs()[1][2], R.standoffs()[1][1], 156.0,
              f"기판 보스 Ø{F(2 * R.standoffs()[0][2])} × {len(R.standoffs())}, 매달림 (P35)"),
             (bbox(R.hatch_plan())[1], 170.0, 172.5, "바닥 구멍: 기판을 밑에서 (P35)"),
             (sum(bbox(R.keel_plan())[:2]) / 2, bbox(R.keel_plan())[2] + 1.0, 146.5, "F|F# 핀 킬 (P12)"),
             (sbr_["x"][1] + 0.3 if sbr_["x"][1] < 150 else fparts("sensor board support rib rear")[-1]["x"][1] - 0.3, bbox(pts(sbr_))[1], 74.0,
              f"센서 기판 받침 z{F(bbox(pts(sbp_))[3])} (P36), 뒤 리브 틈 x{F(sbr_['x'][1])}~{F(fparts('sensor board support rib rear')[-1]['x'][0])} = 리본 길"),
             (next(p for p in PLAN if p["part"].startswith("16-core ribbon SB J201"))["poly"][1][0] - 0.5, 104.0, 104.0,
              "16심 리본 (바닥 → 레일 밑 차선 → 기판 밑 z5~9, P20·P27)"),
             (160.0, 139.5, 132.0, f"밸런스 레일 z{F(dns('P20')[3])} + 봉 받침 z{F(dn('S05', 0))} (P20·S05)"),
             (150.0, 86.0, 86.0, "흑 탭 받침 + 탭 + 키퍼 훅 (P31·P34)"),
             (149.0, 55.0, 58.0, "흑 멈춤 레일 (D12)"),
             (sum(lg_[1]["x"]) / 2, bbox(pts(lg_[1]))[1] - 0.6, 66.0,
              "센서 바 오른쪽 턱 × 2 = 립 + 기둥 (P36, r4.5 회로 2차)"),
             (152.0, 20.0, 22.0, "백 가이드 탭 + 키퍼 훅 (P31·P34)"),
             (163.0, 5.0, 6.0, "앞 레일 + 앞 도브테일 (D09)")]
    for fu, fv, tv, txt in items:
        leader_to(v, fu, fv, Rr, tv, txt, size_px=9.5)
    # r4.5 circuit 2nd (P36): second line of the ledge label (x / y of the two inverted-L pieces)
    v.text(Rr + v.px(7.5), 66.0 - v.px(14.0),
           f"립 x{F(CL_['lip'][0])}~{F(CL_['lip'][1])} z{F(CL_['z'][0])}~{F(CL_['z'][1])} · 기둥 x{F(CL_['post'][0])}~{F(CL_['post'][1])} z{F(CL_['floor_z'])}~{F(CL_['z'][1])}",
           cls="lt", anchor="start", size_px=9.5)
    z_pl = min(q[1] for q in plq)
    note_lines(v, [f"실선 = 윗판 밑(z{F(z_pl)} 아래)을 위에서 봄 · 보라 가상선 = 윗판·패드 바 레일(그 위) · 파란 점선 = 가려진 리브·뒷벽 USB 개구·리본 차선 · 초록 점선 = 제어 기판(핀 발 홈)·BRD-01 부품·USB 플러그 · 주황 칸 = 기판 부품·배선 금지",
                   f"연녹 = 탭·키퍼 훅·봉 받침·멈춤 기둥·핀 보스 · 회색 원 = 밸런스 핀 Ø{F(dns('P32')[1])} (압입) · 흰 칸 = 뒷벽 스프링 홈 · 흰 사다리꼴 = 도브테일 암 홈 (왼쪽 모듈의 수가 들어옴)",
                   f"r4.4 고침 2b: 흰 칸 x{F2(bbox(R.hatch_plan())[0])}~{F2(bbox(R.hatch_plan())[1])} y{F2(bbox(R.hatch_plan())[2])}~{F2(bbox(R.hatch_plan())[3])} = 바닥 구멍 (기판을 밑에서 넣음) · "
                   f"연녹 원 = 기판 위에 매달린 보스 Ø{F(2 * R.standoffs()[0][2])} (나사 막힌 구멍 Ø{F(nums(next(p['part'] for p in FX if is_screw_boss(p['part'])))[1])}, 위치 핀 Ø{F(2 * next(p['circle'][2] for p in PLAN if p['part'].startswith('control-board locating pin')))}) · "
                   f"F|F# 핀 킬 y{F(bbox(R.keel_plan())[2])}~{F(bbox(R.keel_plan())[3])} z{F(bbox(pts(fparts('fin keel')[0]))[2])}~{F(bbox(pts(fparts('fin keel')[0]))[3])}",
                   f"r4.5 고침: F|F# 핀 앞끝 y{F(bbox(R.keel_plan())[3])} (킬 짧아짐) · 스프링 홈 보스 {F(SOL['spring']['boss'][0])}·홈 {F(SOL['spring']['groove'][3])} = {R.spring_txt()['dx']} 가운데 (긴 다리 x), 입구 0.5×45° 모따기",
                   f"r4.5 회로 2차 (P36): 센서 바·기판의 왼쪽 끝 = M3×10 2개로 받침 기둥 x{F(sbp_['x'][0])}~{F(sbp_['x'][1])}, 오른쪽 끝 = 오른쪽 턱 (v3 P112) — 립 밑 z{F(CL_['z'][0])} = 바 윗면, 바 끝 x{F(CL_['bar_end'])} 위를 {F(CL_['over_bar'])} 덮음, "
                   f"기둥 ↔ 바·기판 끝 {F(CL_['post_to_bar'])}, 이음 면에서 {F(CL_['seam_inset'])} 안 · 넣기: 모듈을 빼 놓고 바·기판을 {F(R.ledge_slide())} 왼쪽에 놓고 오른쪽으로 밀어 턱 밑에 → 왼쪽 나사"],
               U0 + 2.0, -39.0, line_px=14, size_px=10)
    scalebar(v, 196.0, -44.0, 20)
    # ------------------------------------------------ side sections (y-z)
    z_top = dn("S18")
    sides = []
    cbx_ = bbox(ppoly("control board"))
    fin3 = next(f for f in fins if cbx_[0] < sum(f) / 2 < cbx_[1])      # the F|F# fin (foot through the stripboard slot)
    for xs, ttl in ((sum(fins[1]) / 2, "핀 2 (D|D#)"), (SOL["levers"]["C#"], "C# 중심 (흑 레일·탭·밸런스 핀·윗판·스프링 홈)"),
                    (sum(fparts("pad bar rail")[0]["x"]) / 2, "패드 바 레일 (P13)"),
                    (sum(fin3) / 2, "핀 3 (F|F#): 기판 홈 속 발 + 기판 부품·USB 플러그 위 매달림 (기판·부품·플러그는 초록)"),
                    (R.standoffs()[0][0], "기판 보스 (기판 위에 매달림, 나사 앞 · 위치 핀 뒤, P35) + 바닥 구멍 + 센서 기판 받침 리브 (P36); 기판·센서 기판·나사 머리는 초록")):
        sv = View(-6.0, -30.0, 262.0, z_top + 12.0, px_width=1480)
        Ps = pids(sv)
        fx = [p for p in FX if cut_x(p, xs)]
        has_fin = any(p["part"] == "fin" for p in fx)
        panel_title(sv, -5.0, z_top + 12.0 - sv.px(14), f"측면 단면 x = {F2(xs)} — {ttl} (프레임만)", size_px=12)
        zf = [(dns("S01")[2], 212.0, "바닥판 밑 (S01)"), (dns("S01")[3], 212.0, "바닥판 위")]
        for p in fx:
            n = p["part"]
            q = pts(p)
            b_ = bbox(q)
            if n == "white front rail":
                zf += [(q[4][1], q[4][0], "앞 레일 앞 (펠트 자리)"), (b_[3], 27.0, "앞 레일 위")]
            elif n.startswith("black stop rail"):
                zf += [(q[4][1], 54.5, "흑 레일 (펠트 자리 앞)"), (b_[3], 59.0, "흑 레일 뒤")]
            elif n.startswith("black tab base"):
                zf += [(b_[3], b_[1], "흑 탭 받침 위")]
            elif n.startswith("tab "):
                zf += [(b_[3], b_[1], "탭 꼭대기")]
            elif n.startswith("keeper hook"):
                zf += [(b_[2], b_[0], "훅 밑 (S20 펠트 자리)")]
            elif n.startswith("balance rail (lowered"):
                zf += [(b_[3], 144.5, "밸런스 레일 위 (P20)")]
                m_ = re.search(r"pocket z([\d.]+) behind y([\d.]+)", n)        # r4.4 fix 2: rail pocket under the key block (P20)
                if m_:
                    zf += [(float(m_.group(1)), float(m_.group(2)) + 1.0, "레일 포켓 (블록 밑, P20)")]
            elif n.startswith("balance pin"):
                zf += [(b_[2], b_[1], "핀 구멍 바닥 (P32)"), (b_[3], b_[1], "핀 꼭대기 (P32)")]
            elif n == "rear shelf" and not has_fin:
                zf += [(b_[2], 209.0, "선반 밑"), (b_[3], 209.0, "선반 위 (S10)")]
            elif n.startswith("top plate"):
                zf += [(b_[3], 212.0, "윗판 위 = 맨 위 (S18)")]
                if not has_fin:
                    zf += [(b_[2], 209.0, "윗판 밑 뒤 (P15)"), (dn("S17"), 175.0, "패드 바 자리 (S17)"),
                           (yslice(q, b_[0] + 1e-3)[0][0], b_[0], "앞 홈 밑 (P15)")]
            elif n.startswith("pad bar rail") and n != "pad bar rail lip":
                zf += [(b_[2], b_[1], "레일 밑 (P13)")]
                ch_ = [t for t in q if abs(t[0] - b_[0]) < 1e-6 and t[1] > b_[2] + 1e-6]
                if ch_ and abs(min(t[1] for t in ch_) - b_[2]) > 1e-6:          # r4.4: web front-bottom chamfer (P13)
                    zc_ = min(t[1] for t in ch_)
                    zf += [(zc_, b_[0], f"웹 모따기 {F(zc_ - b_[2])}×45° (P13)")]
            elif n == "fin":
                zf += [(b_[3], 209.0, "핀 위 = 윗판 밑 (S29)")]
            elif n.startswith("control-board boss"):
                zf += [(b_[2], b_[1], "보스 밑 = 기판 윗면 (P35)"), (b_[3], b_[1], "받침 위")]
                if "bore" in n:
                    zf += [(screw_bore(p)[4], screw_bore(p)[1], f"막힌 구멍 Ø{F(screw_bore(p)[2])} 끝")]
            elif n.startswith("control-board locating pin"):
                zf += [(b_[2], b_[1], "위치 핀 끝 (P35)")]
            elif n.startswith("sensor board support"):
                zf += [(b_[3], b_[1], "센서 기판 받침 위 (P36)")]
        if any(is_boss(p["part"]) for p in fx):
            zf += [(L[1], L[0] + 3.5, "L (S11)")]
        if any(a <= xs <= b for a, b in grooves_x()):
            zf += [(sg["groove"][2], sg["groove"][0], "스프링 홈 (P18)"), (sg["groove"][3], sg["groove"][0], "")]
        brd = [p for p in FX if cut_x(p, xs) and p["part"].startswith(("control board", "board ", "USB-C plug", "control-board screw", "sensor board SB"))]
        if abs(xs - sum(fin3) / 2) < 1e-6:          # r4.3: board / parts / plug under the hung F|F# fin
            fin_parts = [p for p in fx if p["part"] == "fin"]
            cb_ = [p for p in brd if p["part"].startswith("control board")]
            ue_ = bbox(pts(usb_env()))
            zer = bbox(pts(fparts("board part: RP2040-Zero")[0]))
            z_hang = min(z0 for p in fin_parts for z0, z1 in yslice(pts(p), 200.0))
            zf = [t for t in zf if not t[2].startswith(("앞 레일 앞", "흑 밑"))]
            zf += [(bbox(pts(cb_[0]))[2], 186.0, "기판 밑 (P23)"), (bbox(pts(cb_[0]))[3], 186.0, "기판 위"),
                   (zer[3], 190.0, "Zero 윗면 부품 (P27)"), (ue_[2], 212.0, "USB 플러그 밑 (P24)"), (ue_[3], 212.0, "USB 플러그 위"),
                   (z_hang, 209.0, "F|F# 핀 밑 = 매달림 (S29)")]
            kl_ = [p for p in fx if p["part"].startswith("fin keel")]
            if kl_:                                   # r4.5 fix: keel y144.5-148.6 z3-19.3 (P12 / S29)
                kb_ = bbox(pts(kl_[0]))
                zf += [(kb_[3], kb_[1], f"F|F# 킬 위 (y{F(kb_[0])}~{F(kb_[1])}, P12)")]
        ordz(sv, zf, 216.0, gap_px=12, label_px=9.5)
        yf = [(0.0, 5.0, "")]
        fin_y0 = min((bbox(pts(p))[0] for p in fx if p["part"] == "fin"), default=None)
        for p in fx:
            n = p["part"]
            b_ = bbox(pts(p))
            if has_fin and fin_y0 is not None and fin_y0 + 1e-6 < b_[0] < dns("A05")[0] - 1e-6 and \
                    n.startswith(("top plate", "fin", "rear shelf", "rear wall", "pad bar rail")):
                if n.startswith("rear wall"):
                    yf += [(b_[1], 5.0, "")]
                continue
            if n == "white front rail":
                yf += [(b_[0], 5.0, "앞 레일"), (b_[1], 5.0, "")]
            elif n.startswith(("black stop rail", "black tab base")):
                yf += [(b_[0], 5.0, "흑 레일" if "stop" in n else "탭 받침"), (b_[1], 5.0, "")]
            elif n.startswith("tab "):
                yf += [(b_[0], b_[2], "탭"), (b_[1], b_[2], "")]
            elif n.startswith("balance rail (lowered"):
                yf += [(b_[0], 5.0, "레일"), (b_[1], 5.0, "")]
                m_ = re.search(r"pocket z([\d.]+) behind y([\d.]+)", n)
                if m_:
                    yf += [(float(m_.group(2)), float(m_.group(1)), "포켓")]
            elif n.startswith("balance pin"):
                yf += [((b_[0] + b_[1]) / 2, b_[2], "핀")]
            elif n.startswith("top plate"):
                yf += [(b_[0], 65.0, "윗판")]
            elif n.startswith("pad bar rail") and n != "pad bar rail lip":
                yf += [(b_[0], b_[2] + 0.5, "레일"), (b_[1], b_[2], "")]
                bot_ = [t[0] for t in pts(p) if abs(t[1] - b_[2]) < 1e-6]
                if min(bot_) > b_[0] + 1e-6:                                        # r4.4: chamfer on the web's front-bottom corner
                    yf += [(min(bot_), b_[2], "모따기 끝")]
            elif n == "fin":
                yf += [(b_[0], 5.0, "핀")]
            elif n.startswith("control-board boss"):
                yf += [(b_[0], b_[2], "보스 받침"), (b_[1], b_[2], "")]
            elif n.startswith("sensor board support rib"):
                yf += [(b_[0], 5.0, "리브"), (b_[1], 5.0, "")]
            elif n == "rear shelf":
                yf += [(b_[0], b_[2], "선반")]
            elif n.startswith("rear wall"):
                yf += [(b_[0], 5.0, "뒷벽"), (b_[1], 5.0, "")]
        if any(is_boss(p["part"]) for p in fx):
            yf += [(L[0], L[1] - 3.5, "L")]
        if abs(xs - sum(fin3) / 2) < 1e-6:
            foot = min(fin_parts, key=lambda p: bbox(pts(p))[0])
            fq = pts(foot)
            y_foot = max(q[0] for q in fq if abs(q[1] - bbox(fq)[2]) < 1e-6)             # rear end of the foot on the floor
            yf += [(y_foot, 5.0, "핀 발 끝 (S29)"), (min(bbox(pts(p))[0] for p in cb_), 9.0, "기판 홈 끝 = Zero 앞 (P23)"),
                   (ko_[2][1], 10.6, "금지 끝"), (ue_[0], ue_[2], "USB")]
        ordy(sv, yf, 1.5, gap_px=12.5, label_px=9.5)
        frame_side(sv, Ps, xs)
        for p in brd:
            q_ = pts(p)
            if p["part"].startswith(("control board", "sensor board SB")):
                hpoly(sv, q_, "m-pcb")
            elif p["part"].startswith("USB-C plug"):    # r4.4: clip at the frame end y212 (the plug runs on into the cable duct, sheet 11)
                b_ = bbox(q_)
                y_cut = dns("A05")[0]
                sv.poly([(y_cut, b_[2]), (b_[0], b_[2]), (b_[0], b_[3]), (y_cut, b_[3])], cls="env", closed=False)
            else:
                sv.poly(q_, cls="env")
        sides.append(sv)
    # cradle detail (y-z at a cradle, enlarged)
    cr = next(p for p in FX if p["part"] == "balance rail cradle")
    xcr = sum(cr["x"]) / 2
    u0, u1, w0, w1 = 135.8, 146.2, 17.8, 24.2
    s_ = 32.0
    dv = View(u0 - 150 / s_, w0 - 120 / s_, u1 + 20 / s_, w1 + 28 / s_, px_width=(u1 - u0) * s_ + 170, pad_px=4)
    Pd = pids(dv)
    i0 = clip_begin(dv)
    frame_side(dv, Pd, xcr)
    dv.circle(K[0], K[1], dn("S03", 0, "note") / 2, cls="ph2")
    dv.cl(K[0] - 3, K[1], K[0] + 3, K[1])
    dv.cl(K[0], K[1] - 3, K[0], K[1] + 3)
    clip_end(dv, i0, u0, u1, w0, w1)
    panel_title(dv, u0 - 150 / s_ + dv.px(4), w1 + dv.px(14), f"확대: 봉 받침 x{F(cr['x'][0], 3)}~{F(cr['x'][1], 3)} (P20·S05; 표는 둘째 자리)", size_px=11.5)
    cy = R.cradle_y()
    ordz(dv, [(dns("S05")[1], K[0], "받침 바닥 (S05)"), (dns("S05")[0], 139.0, "받침 입술"), (dns("P20")[3], 136.0, "레일 (P20)"),
              (K[1], K[0] - 2.2, "K")], u0 - 0.2, side="left", gap_px=13, label_px=9.5, lo=w0, hi=w1)
    ordy(dv, [(cy[0], 20.5, "받침"), (cy[1], 20.5, ""), (K[0], 19.5, "K"), (cy[2], 20.5, ""), (cy[3], 20.5, "받침")],
         w0 - 0.1, gap_px=13, label_px=9.5, lo=u0)
    dv.text(K[0] + dv.px(58), 23.6, f"홈 R{F2(dns('S05', 'ref')[2])} · 깊이 {F(dn('S05', 0) - dn('S05', 1))}", cls="dt", anchor="start", size_px=9.5)
    # ------------------------------------------------ x-z sections
    xzs = []
    y_pad = R.sheet4_y_pad()
    y_gr = (sg["groove"][0] + sg["groove"][1]) / 2
    for yy, ttl, zlo, zhi in ((K[0], "봉 줄 (밸런스 레일·봉 받침·멈춤 기둥, 봉은 가상선)", 1.0, 26.0),
                              (y_pad, "패드 줄 (윗판·패드 바 레일·핀; 패드 바는 가상선)", 1.0, z_top + 6.0),
                              (L[0], "레버 봉 줄 (선반·리브·핀 보스·도브테일·윗판, 봉은 가상선)", 1.0, z_top + 6.0),
                              (y_gr, "뒷벽 스프링 홈 줄 (홈 12·USB 개구)", 1.0, z_top + 6.0),
                              (R.standoff_y_front(), "기판 앞 보스 줄 (바닥 구멍·매달린 보스·위치 핀·F|F# 핀 앞 연장, P35; 기판·나사 머리는 가상선)", 1.0, 26.0),
                              (sum(bbox(pts(sbr_))[:2]) / 2, "센서 기판 뒤 리브 줄 (받침 기둥·리브, 리본 틈, 오른쪽 끝 센서 바 턱 = 립 + 기둥, P36; 센서 기판·센서 바는 가상선)", 1.0, 20.0)):
        xv = View(-16.0, zlo - 22.0, 214.0, zhi, px_width=1480)
        Px = pids(xv)
        ph = []
        if abs(yy - K[0]) < 1e-6:
            rodp = plan_item("key rod")["poly"]
            ph.append((rect(rodp[0][0], rodp[1][0], K[1] - dn("S03", 0, "note") / 2, K[1] + dn("S03", 0, "note") / 2), "ph2"))
        if abs(yy - L[0]) < 1e-6:
            ue = bbox(pts(usb_env()))
            ph.append((rect(ppoly("USB plug")[0][0], ppoly("USB plug")[1][0], ue[2], ue[3]), "env"))
            rp_ = R.rod_part()
            for z0_, z1_ in yslice(pts(rp_), yy):
                ph.append((rect(rp_["x"][0], rp_["x"][1], z0_, z1_), "ph2"))
        if abs(yy - R.standoff_y_front()) < 1e-6 or abs(yy - sum(bbox(pts(sbr_))[:2]) / 2) < 1e-6:
            for p in FX:                              # boards above the stand-offs / ribs (not frame): phantom
                if p["part"].startswith(("control board", "sensor board SB", "control-board screw", "board part: J301 16-core")):
                    for z0_, z1_ in yslice(pts(p), yy):
                        ph.append((rect(p["x"][0], p["x"][1], z0_, z1_), "env"))
        if abs(yy - sum(bbox(pts(sbr_))[:2]) / 2) < 1e-6:
            # r4.5 circuit 2nd (P36): the sensor bar on the board (phantom) - the right ledge lip lies on its end
            sbar_ = union_rings([rect(p["x"][0], p["x"][1], z0_, z1_) for p in FX if p["part"] == "sensor bar"
                                 for z0_, z1_ in yslice(pts(p), yy)])
            ph += [(r_, "ph2") for r_ in sbar_]
        if abs(yy - y_pad) < 1e-6:
            for p in plan_all("pad bar"):
                if p["part"] == "pad bar":
                    q = [tuple(t) for t in p["poly"]]
                    bq = pts(fpart("pad bar"))
                    zz = yslice(bq, yy)
                    ph.append((rect(q[0][0], q[1][0], zz[0][0], zz[-1][1]), "ph2"))
        panel_title(xv, -15.0, zhi - xv.px(14), f"가로 단면 y = {F2(yy)} — {ttl}", size_px=12)
        zf, xf = ([] if abs(yy - L[0]) < 1e-6 else [(dns("S01")[3], W, "바닥판 위")]), []
        zpl = yslice(plq, yy)
        if zpl:
            zf += [(zpl[0][0], W, "윗판 밑 (P15)"), (zpl[0][1], W, "윗판 위 (S18)")]
        if abs(yy - K[0]) < 1e-6:
            zf += [(dns("P20")[3], W, "레일 (P20)"), (dns("S05")[1], W, "받침 홈 바닥 (S05)"),
                   (bbox(pts(fparts("rod end stop post")[0]))[3], W, "멈춤 기둥 위"),
                   (min(bbox(pts(p))[2] for p in FX if p["part"].startswith("balance rail (lowered") and bbox(pts(p))[2] > 6), 80.0, "레일 밑 = 리본 차선 (P20)")]
            for p in FX:
                if p["part"] == "balance rail cradle":
                    zc_ = max(z1 for z0, z1 in yslice(pts(p), yy))
                    xf += [(p["x"][0], zc_, "받침"), (p["x"][1], zc_, "")]
            for p in FX:
                if p["part"].startswith("balance rail (lowered") and bbox(pts(p))[2] > 6:
                    xf += [(p["x"][0], 10.0, "밑 z10"), (p["x"][1], 10.0, "")]
            xf += [(fparts("rod end stop post")[-1]["x"][1], 21.0, "멈춤")]
        elif abs(yy - y_pad) < 1e-6:
            rl = fparts("pad bar rail")
            zf += [(bbox(pts(rl[0]))[2], W, "레일 밑 (P13)"), (dn("S17"), W, "패드 바 자리 (S17)")]
            for p in rl:
                xf += [(p["x"][0], bbox(pts(p))[2], "레일"), (p["x"][1], bbox(pts(p))[2], "")]
            zf += [(yslice(pts(p), yy)[0][0], p["x"][1], "핀 밑 (기판 위, S29)") for p in FX
                   if p["part"] == "fin" and yslice(pts(p), yy) and yslice(pts(p), yy)[0][0] > 6]
        elif abs(yy - L[0]) < 1e-6:
            b_ = bbox(pts(boss_parts()[0]))
            zf += [(bbox(pts(fparts("rear shelf")[0]))[2], W, "선반 밑"), (SOL["z_shelf"], W, "선반 위 (S10)"),
                   (bbox(pts(usb_env()))[3], 84.0, "USB 플러그 위 (P24)"),
                   (min(z0 for p in FX if p["part"] == "fin" and p["x"][0] < 84.0 < p["x"][1] for z0, z1 in yslice(pts(p), yy)), 82.0, "F|F# 핀 밑 (S29)"),
                   (b_[2], W, f"보스 밑 {lb['boss']}"), (L[1], W, "L (S11)"), (b_[3], W, "보스 위"),
                   (dns("D09")[6], W + 4.0, "도브테일 수 위 (D09)"), (bbox(pts(fpart("rear dovetail (female groove, neighbour male inside)")))[3], 0.0, "암 홈 위")]
            for p in FX:
                if is_boss(p["part"]):
                    xf += [(p["x"][0], 30.0, "보스"), (p["x"][1], 30.0, "")]
            pp_, rp_ = R.plug_part(), R.rod_part()          # r4.4 (D18): exported plug / rod / bores
            bR = max((p for p in FX if is_boss(p["part"])), key=lambda p: p["x"][1])
            xb_ = max(p["x"][1] for p in R.bore_parts())
            xf += [(pp_["x"][0], L[1], f"마개 {F(pp_['x'][1] - pp_['x'][0])} (D18)"), (rp_["x"][0], L[1], "봉 끝"),
                   (rp_["x"][1], L[1], "봉 끝"), (xb_, L[1], f"막힌 구멍 끝, 벽 {F2(bR['x'][1] - xb_)} (D18)")]
            xf += [(bbox(ppoly("USB plug"))[0], bbox(pts(usb_env()))[2], "USB (P24)"), (bbox(ppoly("USB plug"))[1], bbox(pts(usb_env()))[2], "")]
            xf += [(ss0, SOL["z_shelf"], "선반 홈 (P19)"), (ss1, SOL["z_shelf"], "")]
            xf += [(W + dns("D09")[2], 3.0, "수 끝")]
        elif abs(yy - R.standoff_y_front()) < 1e-6:
            so_ = sorted((p for p in FX if p["part"].startswith("control-board boss") and bbox(pts(p))[0] <= yy <= bbox(pts(p))[1]),
                         key=lambda p: p["x"][0])
            pin_ = next(p for p in FX if p["part"].startswith("control-board locating pin") and bbox(pts(p))[0] <= yy <= bbox(pts(p))[1])
            sb_ = screw_bore(next(p for p in so_ if "bore" in p["part"]))
            kl_ = fparts("fin keel")[0]
            hx_ = bbox(R.hatch_plan())
            # r4.5 fix: ordinates from the feature edges (right boss, pin, bore, board, screw head, keel), not from W
            xbR = max(p["x"][1] for p in so_)
            scr_ = next((p for p in FX if p["part"].startswith("control-board screw") and bbox(pts(p))[0] <= yy <= bbox(pts(p))[1]), None)
            zf += [(bbox(pts(so_[0]))[2], xbR, "보스 밑 = 기판 윗면 (P35)"), (bbox(pts(so_[0]))[3], xbR, "보스·받침 위"),
                   (bbox(pts(pin_))[2], pin_["x"][1], "위치 핀 끝 (P35)"), (sb_[4], sb_[0] + sb_[2] / 2, f"막힌 구멍 Ø{F(sb_[2])} 끝"),
                   (bbox(pts(fpart("control board")))[2], max(p["x"][1] for p in FX if p["part"] == "control board"), "기판 밑 (가상선, P23)"),
                   (G["circuit_r44"]["screw"]["head_z"][0], scr_["x"][1] if scr_ else sb_[0], "M3 머리 밑 (밑에서, 가상선)")]
            # r4.5 fix 3: y149 cuts the full-height F|F# fin (front y148.6); the keel y144.5~148.6 is in front of the plane
            fin_ = next(p for p in FX if p["part"] == "fin" and bbox(pts(p))[0] - 1e-6 <= yy <= bbox(pts(p))[1] + 1e-6
                        and p["x"][0] < sum(kl_["x"]) / 2 < p["x"][1])
            fb_ = bbox(pts(fin_))
            for p in so_:
                xf += [(p["x"][0], bbox(pts(p))[3], "보스 Ø6"), (p["x"][1], bbox(pts(p))[3], ""),
                       ((p["x"][0] + p["x"][1]) / 2, bbox(pts(p))[2], "나사" if "bore" in p["part"] else "위치 핀")]
            xf += [(hx_[0], 3.0, "바닥 구멍"), (hx_[1], 3.0, ""),
                   (fin_["x"][0], fb_[2], f"F|F# 핀 앞 연장 {F2(fin_['x'][1] - fin_['x'][0])}"), (fin_["x"][1], fb_[2], "")]
        elif abs(yy - sum(bbox(pts(sbr_))[:2]) / 2) < 1e-6:
            ribs_ = sorted((p for p in FX if p["part"].startswith("sensor board support rib rear")), key=lambda p: p["x"][0])
            zf += [(bbox(pts(sbp_))[3], W, "받침 위 = 센서 기판 밑 (P36)")]
            zf += [(bbox(pts(p))[3], W, "센서 기판 위 (v3 1.6)") for p in FX if p["part"].startswith("sensor board SB")]
            # r4.5 audit (R50): the post (x0.5~6) and the rear rib are both z5~7 here = one outline, so the post end x6 has
            # no edge in this section -> no ordinate there (x6 is dimensioned in the plan above, '기둥 끝')
            xf += [(sbp_["x"][0], 5.0, "기둥 (리브와 한 몸)")] + [(ribs_[0]["x"][1], 5.0, "리브 틈 = 리본 차선"), (ribs_[-1]["x"][0], 5.0, ""), (ribs_[-1]["x"][1], 5.0, "리브 끝")]
            # r4.5 circuit 2nd (P36): right ledge lip / post (v3 P112), cut by this row (rear piece y70.6~77.5)
            lgc_ = [p for p in R.ledge_parts() if yslice(pts(p), yy)]
            CL_ = G["circuit_r45"]["ledge"]
            if lgc_:
                zf += [(CL_["z"][0], W, "립 밑 = 센서 바 위 (P36)"), (CL_["z"][1], W, "턱 위")]
                xf += [(CL_["lip"][0], CL_["z"][0], "립"), (CL_["bar_end"], 8.6, "바·기판 끝"), (CL_["post"][0], 5.0, "턱 기둥"),
                       (CL_["post"][1], 5.0, "")]
        else:
            zf += [(sg["groove"][2], W, "스프링 홈 밑 (P18)"), (sg["groove"][3], W, "홈 위"),
                   (dns("S28", "note")[3], W, "USB 개구 위 (S28)")]
            # r4.5 fix 3: both groove faces (the old labels were the groove centres = lever x + 0.8, read as a face); the
            # extension lines are drawn over the wall (after frame_xz) up to the groove bottoms
            for i_, (a, b) in enumerate(grooves_x()):
                xf += [(a, sg["groove"][2], "홈"), (b, sg["groove"][2], "")]
            xf += [(dns("S28", "note")[0], 5.0, "USB 개구"), (dns("S28", "note")[1], 5.0, "")]
        zf = [t for t in zf if zlo - 1.0 <= t[0] <= zhi]          # r4.5 fix: no ordinate outside the panel (was z68.85/72.85 at y149)
        ordz(xv, zf, W + 10.0, gap_px=12, label_px=9.5)
        on_wall = abs(yy - y_gr) < 1e-6                            # r4.5 fix 3: groove ordinates visible over the wall
        if not on_wall:
            ordy(xv, xf, zlo + 1.0, gap_px=12.5, label_px=9, nd=3 if abs(yy - K[0]) < 1e-6 else 2)   # cradle x exact (P20 rounds)
        frame_xz(xv, Px, yy)
        if on_wall:
            ordy(xv, xf, zlo + 1.0, gap_px=12.5, label_px=9)
            ga_ = grooves_x()[0]
            xv.dim_h(ga_[0], ga_[1], sg["groove"][3] + 3.0, text=f"{F(ga_[1] - ga_[0])}", ext_from=(sg["groove"][3], sg["groove"][3]), size_px=9)
            xv.text(-15.0, zlo - 19.0, f"뒷벽 스프링 다리 홈 {len(grooves_x())}개 (P18): 폭 {F(SOL['spring']['groove'][3])} × 깊이 {F(SOL['spring']['groove'][4])}, z{F(sg['groove'][2])}~{F(sg['groove'][3])}; "
                    f"가운데 = 그 레버 x + {F2(sum(grooves_x()[0]) / 2 - SOL['levers']['C'])} (긴 다리 x) — 아래 x 치수는 홈 두 면",
                    cls="tx-s", anchor="start", size_px=9.5)
        for r_, c in ph:
            xv.poly(r_, cls=c)
        if abs(yy - sum(bbox(pts(sbr_))[:2]) / 2) < 1e-6 and any(yslice(pts(p), yy) for p in R.ledge_parts()):
            CL_ = G["circuit_r45"]["ledge"]
            # below the rotated x labels (the 'x59 리브 틈' label reaches z-17.6): one more text row, panel grown
            xv.v0 = min(xv.v0, zlo - 24.5)
            xv.text(-15.0, zlo - 22.0, f"오른쪽 턱 (r4.5 회로 2차, v3 P112): 모듈을 빼 놓고 센서 바·기판을 {F(R.ledge_slide())} 왼쪽에 놓고 오른쪽으로 밀어 립 밑에 넣은 뒤 왼쪽 끝 M3×10 2개를 기둥에 조임; "
                    f"립이 바 끝 위 {F(CL_['over_bar'])} 덮음 ({F2(CL_['held_area'])} mm²), 기둥 ↔ 바·기판 끝 {F(CL_['post_to_bar'])}, 이음 면에서 {F(CL_['seam_inset'])} 안 (이웃 모듈 {F2(CL_['neighbour_module'][0])} · ER {F2(CL_['end_part_ER'][0])})",
                    cls="tx-s", anchor="start", size_px=9.5)
        # r4.5 fix 3: a frame member that runs out of the panel top (the F|F# fin at y149 goes up to the top plate) is
        # cut with a break line a little under the panel edge and its top named
        for p in FX:
            if frame_part(p["part"]) and not is_fem(p["part"]):
                for z0_, z1_ in yslice(pts(p), yy):
                    if z1_ > zhi + 1e-6 and z0_ < zhi - 4.0 and p["x"][1] - p["x"][0] < 10.0:
                        zb_ = zhi - 2.5
                        kit.break_top(xv, p["x"][0], p["x"][1], zb_)
                        xv.text(p["x"][1] + xv.px(8), zb_ - xv.px(3.5), f"{'F|F# ' if p['part'] == 'fin' and p['x'][0] < sum(SOL['levers'][n] for n in ('F', 'F#')) / 2 < p['x'][1] else ''}"
                                f"{'핀' if p['part'] == 'fin' else p['part']} → z{F2(z1_)} 윗판 밑까지 (끊어 그림, S29)", cls="tx-s", anchor="start", size_px=9.5)
        scalebar(xv, 175.0, zlo - 19.0, 10)
        xzs.append(xv)
    # ------------------------------------------------ table (y / z ranges; x = ordinates above)
    rows = []

    def row(name, parts_, cid):
        if not parts_:
            return
        ys = [bbox(pts(p)) for p in parts_]
        y0, y1 = min(b[0] for b in ys), max(b[1] for b in ys)
        z0, z1 = min(b[2] for b in ys), max(b[3] for b in ys)
        xw = sorted(set(round(p["x"][1] - p["x"][0], 3) for p in parts_))
        # r4.5 fix 3 (issue 5): one fixed precision in every column (kit.FX / FR, same half-up rule)
        xs_ = " / ".join(kit.FX(w) for w in xw) if len(xw) <= 4 else f"{kit.FR(xw[0], xw[-1])} ({len(xw)}가지)"
        rows.append([name, str(len(parts_)), xs_, kit.FR(y0, y1), kit.FR(z0, z1), cid])

    sel = lambda k: [p for p in FX if p["part"].startswith(k)]
    row("바닥판", sel("floor"), "S01")
    row("백 앞 레일", sel("white front rail"), "S21")
    row("백 가이드 탭", [p for p in sel("tab ") if "#" not in p["part"]], "P31")
    row("백 키퍼 훅", [p for p in sel("keeper hook") if "#" not in p["part"]], "P34·S20")
    row("흑 멈춤 레일", sel("black stop rail"), "D12")
    row("흑 탭 받침", sel("black tab base"), "P31")
    row("흑 가이드 탭", [p for p in sel("tab ") if "#" in p["part"]], "P31")
    row("흑 키퍼 훅", [p for p in sel("keeper hook") if "#" in p["part"]], "P34·S20")
    row("밸런스 레일 (낮춘 곳)", sel("balance rail (lowered"), "P20")
    row("봉 받침", sel("balance rail cradle"), "P20·S05")
    row("봉 끝 멈춤 기둥", sel("rod end stop post"), "P21")
    row("뒤 선반", sel("rear shelf"), "P19·S10")
    rows.append(["뒤 선반 USB 홈 (뚫림, r4.3)", "1", kit.FX(ss1 - ss0), kit.FR(sq[0][1], sq[2][1]), "—", "P19"])
    row("선반 리브", sel("shelf rib"), "P19")
    row("핀 (앞 연장 포함)", [p for p in FX if p["part"] == "fin"], "P12·S29")
    row(f"핀 보스 {lb['boss']} (구멍 {lb['bore']})", boss_parts(), "D06")
    row("윗판 (앞 걸이 턱 + 옛 브리지)", sel("top plate"), "P15·S18")
    row("패드 바 L 레일 (웹 + 립, r4.2; r4.4 웹 앞 아래 1×45° 모따기)", sel("pad bar rail"), "P13")
    row("뒷벽", sel("rear wall"), "S28")
    gx = grooves_x()
    rows.append([f"뒷벽 스프링 다리 홈", str(len(gx)), kit.FX(gx[0][1] - gx[0][0]), kit.FR(sg['groove'][0], sg['groove'][1]),
                 kit.FR(sg['groove'][2], sg['groove'][3]), "P18"])
    row("도브테일 (암 홈 / 수 뿌리)", sel("rear dovetail") + sel("front dovetail"), "D09")
    row("핀 보스 구멍 Ø4.0 (출력 Ø3.9 → 드릴, 뚫림 / 막힘)", R.bore_parts(), "D18")
    hx_ = bbox(R.hatch_plan())
    rows.append(["바닥 구멍 (기판 밑, 기판을 밑에서 넣음, 고침 2b)", "1", kit.FX(hx_[1] - hx_[0]), f"{kit.FR(hx_[2], hx_[3])} (USB 뒤 홈까지)", "뚫림", "P35"])
    row("기판 보스 Ø6 + 받침 (나사, 막힌 구멍 Ø2.5, 매달림, 고침 2b)", [p for p in sel("control-board boss") if "bore" in p["part"]], "P35")
    row("기판 보스 Ø6 + 받침 (위치 핀, 매달림, 고침 2b)", [p for p in sel("control-board boss") if "locating pin" in p["part"]], "P35")
    row("기판 위치 핀 Ø2.8 (아래로 기판 구멍을 지남)", sel("control-board locating pin"), "P35")
    row("F|F# 핀 킬 (기판 홈 속, 레일 뒷면에 붙음, 고침 2b)", sel("fin keel"), "P12·D18")
    row(f"스프링 홈 보스 (뒷벽 면, r4.5 폭 {F(SOL['spring']['boss'][0])}, 고침: {R.spring_txt()['dx']} 가운데)", sel("spring groove boss"), "P18")
    row("스프링 홈 입구 모따기 0.5×45° (암, r4.5 고침)", sel("spring groove entry chamfer"), "P18")
    row("센서 기판 받침 기둥 (v3 P111, r4.4)", sel("sensor board support post"), "P36")
    row("센서 기판 받침 앞 리브 (v3 P113)", sel("sensor board support rib front"), "P36")
    row("센서 기판 받침 뒤 리브 (틈 = 리본 차선)", sel("sensor board support rib rear"), "P36")
    # r4.5 circuit 2nd (P36): the two ledge pieces sit at different y (front / rear of the B lead rows) - one y range each
    for nm_, key_ in (("센서 바 오른쪽 턱 립 (v3 P112, r4.5 회로 2차; 밑면 = 바 윗면)", "sensor-bar ledge lip"),
                      (f"센서 바 오른쪽 턱 기둥 (바닥부터, 이음 면에서 {F(G['circuit_r45']['ledge']['seam_inset'])} 안)", "sensor-bar ledge post")):
        lp_ = sorted(sel(key_), key=lambda p: bbox(pts(p))[0])
        if lp_:
            xw_ = sorted(set(round(p["x"][1] - p["x"][0], 3) for p in lp_))
            rows.append([nm_, str(len(lp_)), " / ".join(kit.FX(w) for w in xw_), " / ".join(kit.FR(*bbox(pts(p))[:2]) for p in lp_),
                         kit.FR(min(bbox(pts(p))[2] for p in lp_), max(bbox(pts(p))[3] for p in lp_)), "P36"])
    tvh = (len(rows) + 1) * 17 + 44
    tv = View(0, -tvh, 1480, 0, px_width=1480, pad_px=6)
    tv.text(8, -16, "프레임 형상 표 (geometry.json parts, 같은 이름의 형상을 묶음) — x 위치는 평면도·단면의 좌표, 여기는 x 폭·y·z 범위", cls="ttl", anchor="start", size_px=12)
    table(tv, 8, -26, ["형상", "개수", "x 폭", "y 범위", "z 범위", "번호"], rows, [300, 60, 180, 200, 200, 120], row_px=17, size_px=10)
    pp = M["mass"]["print_plan"][3][1].replace("패드 바 레일(도브테일)", "패드 바 L 레일(웹 + 립)")   # r4.4: metrics text still says dovetail
    n_ = [f"출력: {pp}",
          f"압입: 밸런스 핀 Ø{F(dns('P32')[1])}×{F(dns('P32')[2])} 꼭대기 z{F2(dns('P32')[4])} (높이 게이지). r4: 황동 부싱·탭 강철 띠·위치 핀·손나사 구멍 없음.",
          f"프레임 출력 {F(round(M['mass']['frame_g']))} g + 윗판 서포트 {F(round(M['mass']['support_plate_g']))} g (metrics) · 윗판 {F(round(M['mass']['frame_parts']['top_plate']))} g."]
    note_lines(tv, n_, 8.0, -26 - (len(rows) + 1) * 17 - 16, line_px=15, size_px=10.5)
    tv.v0 = -tvh - 3 * 15 - 10
    rows_ = [[v], [sides[0]], [sides[1]], [sides[2]], [sides[3]], [sides[4]], [dv], [xzs[0]], [xzs[1]], [xzs[2]], [xzs[3]], [xzs[4]], [xzs[5]], [tv]]
    base = os.path.join(OUT, "d08_frame")
    page(rows_, base, "도면 8. 프레임 부품도 (모듈 하나, PETG 한 덩어리 — 윗판 포함)",
         "x = 0 C 왼쪽 명목 경계, y = 0 백건 앞끝, z = 0 책상 · 단위 mm · 숫자 = geometry.json (괄호 = 치수표 번호) · 건반·레버·패드 바·가림판·기판은 뺀 프레임만 (봉·패드 바는 가상선)")
    rec(8, base, "프레임 부품도",
        "모듈 프레임 한 덩어리(r4: 옛 브리지를 앞으로 늘린 윗판 z" + F2(z_top) + "과 한 몸). 평면(윗판 밑을 위에서 봄: 앞 레일·탭·키퍼 훅·흑 멈춤 레일·밸런스 레일과 봉 받침·핀·보스·선반·리브·"
        "뒷벽 스프링 다리 홈·도브테일, 윗판·패드 바 레일은 가상선; 기판 부품·금지 칸·리본 차선·선반 USB 홈), 측면 단면 다섯(핀 2, C# 중심, 패드 바 레일, F|F# 핀과 기판·USB, "
        f"x{F2(R.standoffs()[0][0])} 기판 보스·바닥 구멍·센서 기판 받침), 봉 받침 확대, "
        f"가로 단면 여섯(봉 줄 y{F(K[0])}, 패드 줄 y{F2(y_pad)}, 레버 봉 줄 y{F(L[0])} — 왼쪽 끝 핀 보스에 출력 마개, 오른쪽 끝 핀은 막힌 구멍 (D18), 스프링 홈 줄 y{F2(y_gr)}, "
        f"기판 앞 보스 줄 y{F2(R.standoff_y_front())}, 센서 기판 뒤 리브 줄)과 형상 표. "
        f"r4.4: v3 센서 기판 받침 기둥·리브 (뒤 리브 틈 = 리본 차선, P36), 밸런스 레일 블록 밑 포켓 (P20), "
        "패드 바 레일 웹 앞 아래 1×45° 모따기 (P13), 레버 봉·핀 보스 구멍·끝 마개를 geometry 부품으로 그림 (D18). "
        f"r4.4 고침 2b: 기판 밑 바닥 구멍(기판을 밑에서 넣음), 기판 위에 매달린 보스 Ø6 × {len(R.standoffs())} (앞 2 = 밸런스 레일 뒷면 받침, 뒤 2 = 선반 리브·선반 밑 받침; M3 막힌 구멍 · 아래로 내려온 위치 핀, P35), F|F# 핀 킬 (P12). "
        f"r4.5: 뒷벽 스프링 홈 {F(sg['gw'])}×{F(sg['groove'][1] - sg['groove'][0])} + 보스 {F(SOL['spring']['boss'][0])} (P18). "
        f"r4.5 고침: 스프링 홈·보스를 {R.spring_txt()['dx']}(긴 다리 x) 가운데로 옮기고 홈 + 입구 0.5×45° 모따기를 암 부품으로 그림 (P18); "
        f"F|F# 핀 킬 y{F(bbox(R.keel_plan())[2])}~{F(bbox(R.keel_plan())[3])} z{F(bbox(pts(fparts('fin keel')[0]))[2])}~{F(bbox(pts(fparts('fin keel')[0]))[3])}, F|F# 핀 앞끝 y{F(bbox(R.keel_plan())[3])} (P12·S29) — 가로 단면 y{F2(R.standoff_y_front())}은 킬 뒤의 F|F# 핀 앞 연장을 자르고 윗부분은 끊어 그림; "
        f"뒷벽 홈 줄 단면은 홈 12개의 두 면 x와 폭 {F(SOL['spring']['groove'][3])} (r4.5 고침 3). "
        f"r4.5 회로 2차 (P36): 센서 바 오른쪽 턱 2곳 (v3 P112, y{F(CL_['y'][0][0])}~{F(CL_['y'][0][1])}·{F(CL_['y'][1][0])}~{F(CL_['y'][1][1])}) — 립 x{F(CL_['lip'][0])}~{F(CL_['lip'][1])} z{F(CL_['z'][0])}~{F(CL_['z'][1])} (밑면 = 바 윗면, 바 끝 x{F(CL_['bar_end'])} 위를 {F(CL_['over_bar'])} 덮음) + "
        f"기둥 x{F(CL_['post'][0])}~{F(CL_['post'][1])} z{F(CL_['floor_z'])}~{F(CL_['z'][1])} (바·기판 끝과 {F(CL_['post_to_bar'])}, 이음 면에서 {F(CL_['seam_inset'])} 안)를 평면·센서 기판 뒤 리브 줄 단면(센서 바 가상선)·형상 표에 그림; "
        f"바·기판의 왼쪽 끝은 M3×10 2개로 받침 기둥에, 오른쪽 끝은 턱이 잡음 (넣기: 모듈을 빼 놓고 {F(R.ledge_slide())} 왼쪽에 놓고 오른쪽으로 밀어 넣은 뒤 왼쪽 나사). "
        "황동 부싱·탭 띠·손나사 구멍은 없다.")


# ================================================================ sheet 9: pad bar + up-stop pads + curtain strip + torsion spring
def helix_side(v, u0, u1, zc, r, d, n, cls="spring"):
    """axial (side) view of a close-wound coil: n turns of wire d between u0 and u1 around the axis z = zc."""
    m = max(2, int(math.ceil(n)))
    for i in range(m + 1):
        u = u0 + d / 2 + i * (u1 - u0 - d) / m
        v.circle(u, zc + r, d / 2, cls="m-steel")
        v.circle(u, zc - r, d / 2, cls="m-steel")
    for i in range(m):
        ua = u0 + d / 2 + i * (u1 - u0 - d) / m
        ub = u0 + d / 2 + (i + 1) * (u1 - u0 - d) / m
        v.line(ua, zc + r, ub, zc - r, cls=cls)


def sheet_pad_bar_cover_spring():
    lb = R._labels()
    sg = spring_geom()
    bar = fpart("pad bar")
    barq = pts(bar)
    grip = pts(fpart("pad bar grip"))
    plate = pts(fpart("top plate (ledge + bridge)"))
    rails = fparts("pad bar rail")
    bars = [p for p in plan_all("pad bar") if p["part"] == "pad bar"]
    b0 = [tuple(t) for t in bars[0]["poly"]]
    bx0, bx1 = b0[0][0], b0[1][0]
    by0, by1 = b0[0][1], b0[2][1]
    z_seat = dn("S17")
    zb0 = min(q[1] for q in barq)
    y_step = SOL["y_bar_step"]                               # plate channel end (P15) = where the rails' upper part starts
    y_j0, y_j1 = R.bar_steps()                                # r4.2 joggle: bottom step 165.5, top step 167.0 (P13)
    y_step2 = y_j1
    in_bay = lambda q_: bx0 - 0.5 <= min(t[0] for t in q_) and max(t[0] for t in q_) <= bx1 + 0.5
    wins = [[tuple(t) for t in p_["poly"]] for p_ in plan_all("pad bar leaf window") if in_bay(p_["poly"])]
    tongs = [[tuple(t) for t in p_["poly"]] for p_ in plan_all("pad bar leaf tongue") if in_bay(p_["poly"])]
    lips = [p_ for p_ in fparts("pad bar rail lip") if bx0 - 2.0 <= p_["x"][0] <= bx1 + 2.0]
    dg = G["drafter_r42"]["gaps_module"]
    wedges = [p for p in fparts("pad wedge") if bx0 <= p["x"][0] and p["x"][1] <= bx1]
    pads = [p for p in fparts("up-stop pad") if bx0 <= p["x"][0] and p["x"][1] <= bx1]
    # ------------------------------------------------ 1. pad bar plan (bay 1, seen from below = wedge side)
    S1 = 11.0
    U0, U1, V0, V1 = bx0 - 16.0, bx1 + 60.0, by0 - 14.0, by1 + 18.0
    v = View(U0, V0, U1, V1, px_width=(U1 - U0) * S1, pad_px=6)
    P = pids(v)
    hpoly(v, rect(bx0, bx1, by0, by1), "m-bar", P["bar"])
    hpoly(v, rect(bx0, bx1, by0, bbox(grip)[1]), "m-bar")
    for wq_ in wins:                                          # r4.2 leaf windows (through) with the printed tongues
        v.poly(wq_, cls="void")
    for tq_ in tongs:
        hpoly(v, tq_, "m-bar", P["bar"])
    v.line(bx0, y_j0, bx1, y_j0, cls="vis")                  # bottom step (seen from below)
    v.line(bx0, y_j1, bx1, y_j1, cls="hid")                  # top step (on the top face)
    for lp_ in lips:
        y0_, y1_, _, _ = bbox(pts(lp_))
        v.poly(rect(lp_["x"][0], lp_["x"][1], y0_, y1_), cls="phan")
    for w in wedges:
        q = pts(w)
        hpoly(v, rect(w["x"][0], w["x"][1], bbox(q)[0], bbox(q)[1]), "m-bar")
    for p in pads:
        q = pts(p)
        y0, y1 = min(t[0] for t in q[:2]), max(t[0] for t in q[:2])
        v.poly(rect(p["x"][0], p["x"][1], y0, y1), cls="m-foam")
    for r_ in rails:
        if bx0 - 2 <= r_["x"][0] <= bx1 + 2:
            y0, y1, _, _ = bbox(pts(r_))
            v.poly(rect(r_["x"][0], r_["x"][1], y0, y1), cls="phan")
    for nm in ORDER:
        if bx0 < SOL["levers"][nm] < bx1:
            v.cl(SOL["levers"][nm], by0 - 3.0, SOL["levers"][nm], by1 + 3.0)
            v.text(SOL["levers"][nm], by1 + 4.5, nm, cls="ttl", size_px=11)
    ordy(v, [(bx0, by0, "패드 바 (P13)"), (bx1, by0, "")] +
         [(max(t[0] for t in tq_) if min(t[0] for t in tq_) <= bx0 + 1e-6 else min(t[0] for t in tq_), 175.0, "혀") for tq_ in tongs] +
         [(r_["x"][0], bbox(pts(r_))[0], "레일") for r_ in rails if bx0 - 2 <= r_["x"][0] <= bx1 + 2] +
         [(r_["x"][1], bbox(pts(r_))[0], "") for r_ in rails if bx0 - 2 <= r_["x"][0] <= bx1 + 2] +
         [(w["x"][0], bbox(pts(w))[0], f"쐐기 {w['part'][10:]}") for w in wedges] + [(w["x"][1], bbox(pts(w))[0], "") for w in wedges],
         by0 - 2.0, gap_px=12.5, label_px=9)
    wq = pts(wedges[0])
    ordz(v, [(by0, bx1, "앞 = 손잡이 (P13)"), (bbox(grip)[1], bx1, "손잡이 끝"), (bbox(pts(lips[0]))[0], bx1, "레일 립 시작"),
             (y_j0, bx1, "밑 계단 (P13)"), (y_j1, bx1, "윗 계단 (숨은선)"), (y_step, bx1, "윗판 홈 끝 (P15)"),
             (min(t[1] for t in wins[0]), bx1, "잎 창"), (min(t[1] for t in tongs[0]), bx1, "잎 혀 앞끝"),
             (dn("P16", 0), bx1, "패드 (P16)"), (bbox(wq)[0], bx1, "쐐기 앞"), (dn("P16", 1), bx1, "패드 뒤"), (bbox(wq)[1], bx1, "쐐기 뒤"),
             (max(t[1] for t in tongs[0]), bx1, "잎 혀 뿌리"), (by1, bx1, "패드 바 끝 = 윗판 계단")],
         bx1 + 5.0, gap_px=12.5, label_px=9.5, prefix="y")
    v.dim_h(bx0, bx1, by1 + 10.0, text=f"{F2(bx1 - bx0)}", ext_from=(by1, by1), size_px=9.5)
    panel_title(v, U0 + v.px(4), V1 - v.px(14), "1. 패드 바 (핀 칸 1, C·C#·D) — 밑에서 봄 (쐐기·패드 쪽), 레일·립은 가상선, 양 가장자리 잎 혀", size_px=12)
    v1 = v
    # ------------------------------------------------ 2. side sections of the pad bar at a white and a black wedge (y-z)
    sides = []
    for nm in ("D", "C#"):
        xs = SOL["levers"][nm]
        w = fpart(f"pad wedge {nm}")
        p = fpart(f"up-stop pad {nm}")
        u0, u1, w0, w1 = by0 - 4.0, bbox(plate)[1] - 20.0, 53.5, dn("S18") + 1.0
        s_ = 12.0                                  # r4.4: page ~1536 wide (2a beside 4), text stays >= 9 px at 1600
        sv = View(u0 - 150 / s_, w0 - 60 / s_, u1 + 170 / s_, w1 + 30 / s_, px_width=(u1 - u0) * s_ + 320, pad_px=4)
        Ps = pids(sv)
        i0 = clip_begin(sv)
        fill_rings(sv, union_rings([plate]), "m-print", Ps["print"])
        for r_ in rails:
            if cut_x(r_, xs):
                hpoly(sv, pts(r_), "m-print", Ps["print"])
        hpoly(sv, barq, "m-bar", Ps["bar"])
        hpoly(sv, grip, "m-bar", Ps["bar"])
        hpoly(sv, pts(w), "m-bar", Ps["bar"])
        stroke_rings(sv, union_rings([barq, grip, pts(w)]), "out")
        lay, info = R.pad_layers(p)
        for poly, cls in lay:
            sv.poly(poly, cls=cls)
        # interference check drawn from the geometry: the bar's thick front part vs the plate step (only if it exists)
        z_gr = yslice(plate, by0 + 1e-3)[0][0]
        y_pl_step = min(q[0] for q in plate if abs(q[1] - z_seat) < 1e-6)          # plate underside drops to the seat here
        if y_step2 > y_pl_step + 0.05:
            y_pl0 = max(q[0] for q in plate if abs(q[1] - z_gr) < 1e-6 and q[0] < y_pl_step + 1e-6)
            sv.poly(rect(y_pl0, y_step2, z_seat, z_gr), cls="zone")
            sv.text((y_pl0 + y_step2) / 2, z_gr + sv.px(4), f"윗판과 겹침 y{F(y_pl0)}~{F(y_step2)}", cls="tx", size_px=9.5)
        else:                                                   # r4.2: the top step stops in front of the channel end
            sv.dim_h(y_step2, y_pl_step, z_gr + 0.6, text=f"{F2(y_pl_step - y_step2)} 틈", ext_from=(z_seat + 0.2, z_gr), size_px=9, tpos="right")
        clip_end(sv, i0, u0, u1, w0, w1)
        wq = pts(w)
        kp = KP_B if "#" in nm else KP_W
        ordz(sv, [(dn("S18"), bbox(plate)[0], "윗판 위 (S18)"), (yslice(plate, by0 + 1e-3)[0][0], by0, "앞 홈 밑"), (z_seat, y_step, "패드 바 자리 (S17)"),
                  (zb0, by0, "패드 바 밑·손잡이 밑"), (wq[0][1], wq[0][0], "쐐기 앞 밑"), (wq[1][1], wq[1][0], "쐐기 뒤 밑"),
                  (pts(p)[0][1], pts(p)[0][0], "패드 면 앞 (S15)"), (pts(p)[1][1], pts(p)[1][0], "패드 면 뒤")],
             u0 - 0.3, side="left", gap_px=13, label_px=9.5, lo=w0 - 1.0, hi=w1 + 1.0)
        ordy(sv, in_win([(by0, zb0, "앞 (P13)"), (bbox(grip)[1], zb0, "손잡이"), (y_j0, zb0, "밑 계단"), (y_j1, z_seat, "윗 계단"),
                         (y_step, z_gr, "홈 끝"),
                         (dn("P16", 0), pts(p)[0][1], "패드"), (wq[0][0], wq[0][1], "쐐기"), (by1, zb0, "끝"), (wq[1][0], wq[1][1], ""),
                         (dn("P16", 1), pts(p)[1][1], "")], w0, w1), w0 - 0.2, gap_px=13, label_px=9.5, lo=u0)
        tf, tr = zb0 - wq[0][1], zb0 - wq[1][1]
        uc = u1 + sv.px(12)
        sv.dim_v(wq[1][1], zb0, uc, text="", ext_from=(wq[1][0], wq[1][0]), size_px=9)
        sv.text(uc + sv.px(6), (wq[1][1] + zb0) / 2 - sv.px(3.5), f"{F2(tr)} 쐐기 뒤", cls="dt", anchor="start", size_px=9.5)
        sv.dim_v(zb0, z_seat, uc, text="", ext_from=(by1, by1), size_px=9)
        sv.text(uc + sv.px(6), (zb0 + z_seat) / 2 - sv.px(3.5), f"{F2(z_seat - zb0)} 바", cls="dt", anchor="start", size_px=9.5)
        panel_title(sv, u0 - 150 / s_ + sv.px(4), w1 + sv.px(12),
                    f"2{'a' if nm == 'D' else 'b'}. 측면 단면 x = {F2(xs)} ({'백' if nm == 'D' else '흑'} {nm} 쐐기): 쐐기 {kit.FR(tf, tr)} (P17), 면 기울기 {F2(kp['pad_face']['tilt_deg'])}°", size_px=11.5)
        sides.append(sv)
    # ------------------------------------------------ 3. x-z section of bay 1 at the pad middle
    y_mid = R.sheet4_y_pad()
    u0, u1, w0, w1 = -1.0, SOL["fins"][1][1] + 1.0, 52.0, dn("S18") + 0.8
    s_ = 20.0
    xv = View(u0 - 20 / s_, w0 - 120 / s_, u1 + 190 / s_, w1 + 30 / s_, px_width=(u1 - u0) * s_ + 210, pad_px=4)
    Px = pids(xv)
    i0 = clip_begin(xv)
    xz_scene(xv, Px, y_mid, keys=True)
    clip_end(xv, i0, u0, u1, w0, w1)
    panel_title(xv, u0 + xv.px(2), w1 + xv.px(12), f"3. 가로 단면 y = {F2(y_mid)} (핀 칸 1): 레일 사이 패드 바, 쐐기, 패드, 쉼 자세 레버", size_px=11.5)
    r1 = next(r_ for r_ in rails if r_["x"][1] <= bx0 + 1e-6 and r_["x"][1] > bx0 - 2)
    r2 = next(r_ for r_ in rails if r_["x"][0] >= bx1 - 1e-6 and r_["x"][0] < bx1 + 2)
    zr0 = bbox(pts(r1))[2]
    xv.dim_h(r1["x"][0], r1["x"][1], w0 + 2.5, text=f"{F2(r1['x'][1] - r1['x'][0])} 레일", ext_from=(zr0, zr0), size_px=9, tpos="right")
    xv.dim_h(r1["x"][1], bx0, w0 + 5.0, text=f"{F2(bx0 - r1['x'][1])} 틈", ext_from=(zr0, zb0), size_px=9, tpos="right")
    xv.dim_h(bx1, r2["x"][0], w0 + 5.0, text=f"{F2(r2['x'][0] - bx1)} 틈", ext_from=(zb0, zr0), size_px=9, tpos="left")
    ordz(xv, [(dn("S18"), u1, "윗판 위"), (z_seat, u1, "패드 바 자리 = 레일 위 (S17)"), (zb0, u1, "패드 바 밑"), (zr0, u1, "레일 밑 (P13)")],
         u1 + 0.3, gap_px=13, label_px=9.5, lo=w0, hi=w1 + 1.0)
    lb_ = bbox(pts(lips[0]))
    lw_ = lips[0]["x"][1] - lips[0]["x"][0]
    ov_ = min(lips[0]["x"][1], bx1) - max(lips[0]["x"][0], bx0) if lips[0]["x"][1] > bx0 else lips[0]["x"][1] - bx0
    xv.text(u0 + xv.px(4), w0 - xv.px(36), f"L 레일 = 웹 {F2(r1['x'][1] - r1['x'][0])} (윗판 밑 z{F2(zr0)}까지) + 립 {F2(lw_)}×{F2(lb_[3] - lb_[2])} (z{F2(lb_[2])}~{F2(lb_[3])}, y{F(lb_[0])}~{F(lb_[1])}):",
            cls="tx", anchor="start", size_px=10)
    xv.text(u0 + xv.px(4), w0 - xv.px(52), f"립이 바 가장자리 밑 {F2(dg['lip_under_bar'])} 겹침, 바 밑면과 {F2(dg['lip_top_to_bar'])} 띄움 · 잎 혀가 립에 얹혀 바를 자리로 밀어 올림 (확대 2c, P13)",
            cls="tx", anchor="start", size_px=10)
    # ------------------------------------------------ 2c. leaf tongue on the rail lip (y-z at the tongue centre, bay 1 left edge)
    tq0 = tongs[0]
    x_t = (min(t[0] for t in tq0) + max(t[0] for t in tq0)) / 2
    u0c, u1c, w0c, w1c = 158.0, 187.0, 63.6, 70.0
    s_c = 34.0
    lv = View(u0c - 170 / s_c, w0c - 172 / s_c, u1c + 190 / s_c, w1c + 26 / s_c, px_width=(u1c - u0c) * s_c + 360, pad_px=4)
    Pl = pids(lv)
    i0 = clip_begin(lv)
    fill_rings(lv, union_rings([plate]), "m-print", Pl["print"])
    for p_ in fixed():
        n_ = p_["part"]
        if cut_x(p_, x_t) and n_.startswith("pad bar rail"):
            hpoly(lv, pts(p_), "m-print", Pl["print"])
    ebar = [pts(p_) for p_ in fixed() if cut_x(p_, x_t) and p_["part"].startswith(("pad bar (edge strip", "pad bar grip", "pad bar leaf"))]
    for q_ in ebar:
        hpoly(lv, q_, "m-bar", Pl["bar"])
    stroke_rings(lv, union_rings(ebar), "out")
    leaf = next(p_ for p_ in fixed() if cut_x(p_, x_t) and p_["part"].startswith("pad bar leaf"))
    lq = pts(leaf)
    # r4.4 (P13): the rail WEB stands beyond the cut (x < x_t) — its outline shows the 1.0 x 45 deg front-bottom chamfer
    web_ = max((p_ for p_ in fparts("pad bar rail") if p_["part"] == "pad bar rail" and p_["x"][1] <= x_t), key=lambda p_: p_["x"][1])
    wq_ = pts(web_)
    lv.poly(wq_, cls="vis")
    wb_ = bbox(wq_)
    ch_z = min(t[1] for t in wq_ if abs(t[0] - wb_[0]) < 1e-6)            # chamfer top on the front face
    ch_y = min(t[0] for t in wq_ if abs(t[1] - wb_[2]) < 1e-6)            # chamfer end on the bottom face
    clip_end(lv, i0, u0c, u1c, w0c, w1c)
    wy0 = min(t[1] for t in wins[0])
    z_gr = yslice(plate, by0 + 1e-3)[0][0]
    ordz(lv, [(yslice(plate, u0c + 0.01)[0][0], u0c, "윗판 앞 홈 밑"), (z_seat, 186.0, "패드 바 자리 (S17)"),
              (zb0, 184.0, "바 밑"), (lb_[3], 164.0, "립 위"), (lb_[2], 164.0, "립 밑 = 레일 밑 (P13)"), (min(t[1] for t in lq), 175.4, "혀 돌기 밑"),
              (ch_z, wb_[0], f"웹 모따기 {F(ch_z - wb_[2])}×45° 위 (r4.4)")],
         u0c - 0.3, side="left", gap_px=13, label_px=9.5, lo=w0c - 0.5, hi=w1c + 0.5)
    ordy(lv, in_win([(wb_[0], ch_z, "웹 앞"), (ch_y, wb_[2], "모따기 끝"), (lb_[0], lb_[2], "립 (P13)"), (y_j0, zb0, "밑 계단"), (y_j1, z_seat, "윗 계단"), (y_step, z_gr, "홈 끝"),
                     (wy0, zb0, "창"), (min(t[0] for t in lq), min(t[1] for t in lq), "혀 앞"), (max(t[0] for t in lq), zb0, "혀 뿌리"),
                     (by1, zb0, "바 끝")], w0c, w1c), w0c - 0.2, gap_px=13, label_px=9.5, lo=u0c)
    zr_ = yslice(lq, max(t[0] for t in lq) - 0.05)
    t_leaf = zr_[-1][1] - zr_[0][0]
    note_lines(lv, [f"잎 혀 {F2(t_leaf)}T × {F2(max(t[0] for t in tq0) - min(t[0] for t in tq0))} × {F(max(t[1] for t in tq0) - min(t[1] for t in tq0))} (패드 바와 한 몸 출력, 뿌리 y{F(max(t[1] for t in tq0))}), 앞 끝 돌기가 립 위에 얹힘",
                    f"설치하면 끝이 {F2(dg['lip_top_to_bar'])} 들림 → 잎마다 {F2(dg['leaf_F'])} N (k {F2(dg['leaf_k'])} N/mm), 상시 굽힘 {F2(dg['leaf_sigma'])} MPa (공차 끝 {F2(dg['leaf_sigma_max_tol'])})",
                    "빼기: 손잡이로 앞으로 당김 — 혀가 립 위를 미끄러짐; 넣기: 뒤끝이 윗판 계단 y" + F(by1) + "에 닿을 때까지 밂 (P13·P15)"],
               u0c - 150 / s_c, w0c - 120 / s_c, line_px=15, size_px=10)
    panel_title(lv, u0c - 170 / s_c + lv.px(4), w1c + lv.px(12),
                f"2c. 확대 측면 단면 x = {F2(x_t)} (패드 바 가장자리, 잎 혀 가운데): 레일 립 위의 잎 혀 (r4.2) · 가는 선 = 뒤의 레일 웹 (r4.4 앞 아래 모따기)", size_px=11.5)
    # ------------------------------------------------ 4. pad stack detail + PET shim
    pd = fpart("up-stop pad D")
    lay, info = R.pad_layers(pd)
    q = pts(pd)
    u0, u1, w0, w1 = q[0][0] - 1.5, q[2][0] + 1.5, q[1][1] - 1.5, q[3][1] + 1.2
    s_ = 24.0
    dv = View(u0 - 20 / s_, w0 - 150 / s_, u1 + 200 / s_, w1 + 30 / s_, px_width=(u1 - u0) * s_ + 220, pad_px=4)
    Pd = pids(dv)
    for poly, cls in lay:
        dv.poly(poly, cls=cls)
    face, back = info["face"], info["back"]
    L12 = math.hypot(face[1][0] - face[0][0], face[1][1] - face[0][1])
    R.dim_aligned(dv, face[0], face[1], 16, f"{F2(L12)} (면 길이; P16 y{F(dn('P16', 0))}~{F(dn('P16', 1))})")
    nu = ((back[1][0] - face[1][0]) / (info["felt"] + info["foam"]), (back[1][1] - face[1][1]) / (info["felt"] + info["foam"]))
    qf = (face[1][0] + nu[0] * info["felt"], face[1][1] + nu[1] * info["felt"])
    R.dim_aligned(dv, face[1], qf, 18, f"{F(info['felt'])} 펠트")
    R.dim_aligned(dv, qf, back[1], 18, f"{F(info['foam'])} 미세셀 우레탄 폼")
    sh = dns("D16")                       # [0.1, 6, 12]
    so = (back[0][0] + nu[0] * sh[0] * 6, back[0][1] + nu[1] * sh[0] * 6)
    dv.poly([back[0], back[1], (back[1][0] + nu[0] * sh[0] * 6, back[1][1] + nu[1] * sh[0] * 6), so], cls="phan")
    panel_title(dv, u0 + dv.px(2), w1 + dv.px(12), "4. 업스톱 패드 (백 D, 면에 수직 두께)", size_px=11.5)
    d11n = dns("D11", "note")
    note_lines(dv, [f"펠트 {F(info['felt'])}T(면) + 미세셀 우레탄 폼 {F(info['foam'])}T, {F(dns('P16')[2])} × {F(L12)}, 쐐기에 접착 (P16·D11)",
                    f"실효 e ≤ {F2(d11n[0])} · {F(d11n[4])} % 압축 {F2(d11n[5])} MPa · 자리 강성 ≥ {F(d11n[6])} N/mm (D11)",
                    f"보라 쇄선 = PET 심 {F(sh[0])}×{F(sh[1])}×{F(sh[2])} 자리 (패드와 쐐기 사이, 두께 6배로 그림, D16)",
                    f"심 한 장 = 레버 {F2(dns('D16', 'note')[0])}° 일찍 = 건반 앞 {F2(dns('D16', 'note')[1])} (D16)"],
               u0, w0 - dv.px(28), line_px=15, size_px=10)
    # ------------------------------------------------ 5. curtain strip: front elevation (x-z) + side section (y-z)
    cur = [p for p in fixed() if p["part"] == "cover curtain"]
    hook = fpart("cover curtain hook")
    z_lo_w = min(bbox(pts(p))[2] for p in cur)
    z_lo_b = max(bbox(pts(p))[2] for p in cur)
    W = dn("P01")
    cv = View(-6.0, z_lo_w - 16.0, W + 60.0, dn("S18") + 14.0, px_width=1060, pad_px=4)
    Pc = pids(cv)
    ring = []
    for p in cur:
        b_ = bbox(pts(p))
        ring.append(rect(p["x"][0], p["x"][1], b_[2], b_[3]))
    fill_rings(cv, union_rings(ring, res=0.03), "m-cover", Pc["cover"])
    hb = bbox(pts(hook))
    cv.poly(rect(hook["x"][0], hook["x"][1], hb[2], hb[3]), cls="hid")
    notch = [p for p in cur if bbox(pts(p))[2] > z_lo_w + 1e-6]
    for p in notch:
        nmk = min(BLACK, key=lambda n: abs(sum(q[0] for q in ppoly(f"key {n} body")[:2]) / 2 - (p["x"][0] + p["x"][1]) / 2))
        cv.text((p["x"][0] + p["x"][1]) / 2, z_lo_b - cv.px(14), nmk, cls="ttl", size_px=10)
    ordy(cv, [(cur[0]["x"][0], z_lo_w, "띠 (P26)")] + [(p["x"][0], z_lo_b, "노치") for p in notch] + [(p["x"][1], z_lo_b, "") for p in notch] +
         [(cur[-1]["x"][1], z_lo_w, "")], z_lo_w - 1.0, gap_px=12.5, label_px=9)
    ordz(cv, [(z_lo_w, W, "띠 밑 (S27 백)"), (z_lo_b, W, f"흑 노치 밑 (S27, ±{F(dns('P26', 'ref')[0])})"), (hb[2], W, "걸이 밑 = 윗판 턱"), (hb[3], W, "위 = 윗판 위 (S18)")],
         W + 4.0, gap_px=13, label_px=9.5)
    panel_title(cv, -5.0, dn("S18") + 14.0 - cv.px(14), "5a. 가림판 띠 — 앞에서 봄 (모듈 하나, 흑건 자리 노치; 숨은선 = 윗 걸이)", size_px=11.5)
    u0, u1, w0, w1 = dn("P26", 0) - 3.0, bbox(plate)[0] + 6.0, z_lo_w - 1.0, dn("S18") + 1.0
    s_ = 9.0
    cs = View(u0 - 150 / s_, w0 - 50 / s_, u1 + 170 / s_, w1 + 26 / s_, px_width=(u1 - u0) * s_ + 320, pad_px=4)
    Pcs = pids(cs)
    i0 = clip_begin(cs)
    fill_rings(cs, union_rings([plate]), "m-print", Pcs["print"])
    hpoly(cs, pts(cur[0]), "m-cover", Pcs["cover"])
    hpoly(cs, pts(hook), "m-cover", Pcs["cover"])
    stroke_rings(cs, union_rings([pts(cur[0]), pts(hook)]), "out")
    clip_end(cs, i0, u0, u1, w0, w1)
    ordz(cs, [(z_lo_w, dn("P26", 0), "띠 밑 (S27)"), (hb[2], hb[1], "걸이 밑 = 턱 (P15)"), (hb[3], hb[1], "맨 위 (S18)")],
         u0 - 0.3, side="left", gap_px=13, label_px=9.5, lo=w0, hi=w1 + 1.0)
    ordy(cs, in_win([(dn("P26", 0), z_lo_w, "띠 (P26)"), (dn("P26", 1), z_lo_w, ""), (bbox(plate)[0], 68.8, "윗판 앞"), (hb[1], hb[2], "걸이 끝")], w0, w1),
         w0 - 0.2, gap_px=13, label_px=9.5, lo=u0)
    panel_title(cs, u0 - 150 / s_ + cs.px(4), w1 + cs.px(12), f"5b. 측면 단면: 걸이가 윗판 앞 턱에 얹힘 (P26 걸이 립 y{F(dns('P26')[2])}~{F(dns('P26')[3])})", size_px=11)
    # ------------------------------------------------ 6. torsion spring: end view, axial view, installed at rest / bottom
    # r4.5: MISUMI C-UA90R5-3-0.5 (bought, both arms cut), drawn from the exported spring parts of lever D (relative to L)
    r_m, d = sg["r_m"], sg["d"]
    spc = SOL["spring"]
    slg = spc["short_leg_groove"]
    coil_, short_, long_ = R.spring_parts("D")
    sv6 = View(-14.0, -15.0, 58.0, 30.0, px_width=72.0 * 13.0, pad_px=6)
    P6 = pids(sv6)
    rel = lambda q: [(a - L[0], b - L[1]) for a, b in q]
    sv6.circle(0, 0, dn("S11", 0, "note") / 2, cls="ph2")
    # the hub around the spring (b = 0, phantom): pocket D6.6, coil / long-leg slot faces, short-leg groove band (P18)
    sv6.circle(0, 0, sg["pocket"][0] / 2, cls="phan")
    ca0, sa0 = math.cos(math.radians(sg["slot_deg"])), math.sin(math.radians(sg["slot_deg"]))
    for off_ in sg["slot_faces"]:
        p0_ = (-sa0 * off_ + ca0 * 1.5, ca0 * off_ + sa0 * 1.5)
        p1_ = (-sa0 * off_ + ca0 * 6.5, ca0 * off_ + sa0 * 6.5)
        sv6.line(p0_[0], p0_[1], p1_[0], p1_[1], cls="phan")
    sv6.poly(rel([tuple(t) for t in slg["band"]]), cls="phan")
    # r4.5 fix: the long-leg window's upper face (35 deg, +2.6; the insertion slot's +3.25 side opens round to it)
    win_ = slg.get("window", spc.get("window", [35.0, 2.6]))
    caw, saw = math.cos(math.radians(win_[0])), math.sin(math.radians(win_[0]))
    s_w0 = math.sqrt(max((sg["pocket"][0] / 2) ** 2 - win_[1] ** 2, 0.0))
    sv6.line(-saw * win_[1] + caw * s_w0, caw * win_[1] + saw * s_w0, -saw * win_[1] + caw * 6.5, caw * win_[1] + saw * 6.5, cls="phan")
    leader_to(sv6, -saw * win_[1] + caw * 4.6, caw * win_[1] + saw * 4.6, 7.2, 1.4, f"{R.spring_txt()['window']} (가상선)", size_px=9)
    sv6.circle(0, 0, r_m + d / 2, cls="m-steel")
    sv6.circle(0, 0, r_m - d / 2, cls="void")
    sv6.circle(0, 0, dn("S11", 0, "note") / 2, cls="ph2")
    # r4.5 fix: the rear-wall groove is drawn FIRST (it used to be painted over the leg and its 22.3 dimension); the
    # long leg is cut at the groove mouth: below it hatched steel, inside the groove (behind the groove side walls
    # in this end view) a hidden outline up to the tip
    grv = rect(sg["groove"][0] - L[0], sg["groove"][1] - L[0], sg["groove"][2] - L[1], sg["groove"][3] - L[1])
    sv6.poly(grv, cls="void")
    sv6.line(sg["groove"][0] - L[0], sg["groove"][2] - L[1] - 3.0, sg["groove"][0] - L[0], sg["groove"][3] - L[1] + 3.0, cls="vis")
    hpoly(sv6, rel(pts(short_, "rigid0")), "m-steel", P6["steel"])
    lq_ = rel(pts(long_, "rigid0"))
    hpoly(sv6, clip_below(lq_, sg["groove"][2] - L[1]), "m-steel", P6["steel"])
    R.split_outline(sv6, lq_, [grv], (), vis_cls="spring", hid_cls="hid")
    # the long leg at rest in the frame (world) and its free direction (catalogue part unloaded, lever frame at b = 0)
    tipv = (sg["tip"][0] - L[0], sg["tip"][1] - L[1])
    tpv = (sg["tp"][0] - L[0], sg["tp"][1] - L[1])
    fdir = math.radians(spc["insert"]["long_free_dir"])
    ftp = (r_m * math.cos(fdir - math.pi / 2), r_m * math.sin(fdir - math.pi / 2))
    ltp = M["spring"]["l_long"]
    ftip = (ftp[0] + ltp * math.cos(fdir), ftp[1] + ltp * math.sin(fdir))
    sv6.line(ftp[0], ftp[1], ftip[0], ftip[1], cls="phan")
    sv6.text(ftip[0] + 0.4, ftip[1] - 0.6, f"자유 (풀린) 긴 다리 {F2(spc['insert']['long_free_dir'])}°", cls="tx-s", anchor="start", size_px=9)
    ang_i = math.degrees(math.atan2(tipv[1] - tpv[1], tipv[0] - tpv[0]))
    sv6.poly(arc_pts((0.0, 0.0), 14.0, spc["insert"]["long_free_dir"], ang_i, 16), cls="dm", closed=False)
    sv6.text(14.0 * math.cos(math.radians((ang_i + spc["insert"]["long_free_dir"]) / 2)) + 0.6,
             14.0 * math.sin(math.radians((ang_i + spc["insert"]["long_free_dir"]) / 2)), f"b = 0에서 {F2(abs(sg['free']))}° 감김",
             cls="dt", anchor="start", size_px=9)
    R.dim_aligned(sv6, tipv, (0.0, 0.0), 22, f"긴 다리 {F(sg['leg'])} (축에서 끝; 접점에서 {F2(ltp)})")
    sv6.text(sg["groove"][1] - L[0] + 1.0, sg["groove"][3] - L[1] - sv6.px(4),
             f"뒷벽 홈 {F(sg['gw'])} 폭 × 깊이 {F(sg['groove'][1] - sg['groove'][0])} (보스 면 y{F(sg['groove'][0])}, P18)", cls="tx-s", anchor="start", size_px=9)
    sh_ = rel(pts(short_, "rigid0"))
    leader_to(sv6, sum(t[0] for t in sh_) / 4, sum(t[1] for t in sh_) / 4, -13.8, 8.6,
              f"짧은 다리 {F(R.short_leg_len())} → 가둠 홈 폭 {F2(slg.get('width', slg['nn'][1] - slg['nn'][0]))} (막힌 끝)", size_px=9)
    ca_, sa_ = math.cos(math.radians(sg["slot_deg"])), math.sin(math.radians(sg["slot_deg"]))
    sv6.text(-sa_ * sg["slot_faces"][1] + ca_ * 6.8, ca_ * sg["slot_faces"][1] + sa_ * 6.8,
             f"{R.spring_txt()['slot']} (가상선, 짧은 다리 끝부터 넣음)", cls="tx-s", anchor="start", size_px=9)
    sv6.dim_h(-(r_m + d / 2), r_m + d / 2, -r_m - 3.0, text=f"OD {F2(sg['ID'] + 2 * d)}", ext_from=(0, 0), size_px=9)
    sv6.dim_h(-(r_m - d / 2), r_m - d / 2, -r_m - 6.5, text=f"ID {F2(sg['ID'])}", ext_from=(0, 0), size_px=9)
    sv6.cl(-4, 0, 4, 0)
    sv6.cl(0, -4, 0, 4)
    # axial view: coil (3.25 body turns of d = its exported length) in the 3.0 pocket, short leg at -x, long leg at +x
    ax0 = 32.0                                          # r4.5 fix: clear of the free-leg / slot labels of the end view
    xc_ = SOL["levers"]["D"]
    X = lambda x: ax0 + (x - xc_)                      # lever centre at u = ax0
    cl_ = coil_["x"][1] - coil_["x"][0]
    nwire = max(2, int(round(cl_ / d)))
    helix_side(sv6, X(coil_["x"][0]), X(coil_["x"][1]), 0.0, r_m, d, nwire - 1)
    px0, px1 = R.pocket_x("D")
    sv6.poly(rect(X(px0), X(px1), -sg["pocket"][0] / 2, sg["pocket"][0] / 2), cls="phan")
    for leg in (short_, long_):
        zz = [t[1] - L[1] for t in pts(leg, "rigid0")]
        hpoly(sv6, rect(X(leg["x"][0]), X(leg["x"][1]), min(zz), max(zz)), "m-steel", P6["steel"])
    sv6.cl(ax0, -sg["pocket"][0] / 2 - 1.0, ax0, sg["pocket"][0] / 2 + 1.0)
    sv6.dim_h(X(px0), X(px1), sg["pocket"][0] / 2 + 2.0, text=f"주머니 {F(sg['pocket'][1])}", ext_from=(sg["pocket"][0] / 2, sg["pocket"][0] / 2), size_px=9, tpos="right")
    sv6.dim_h(X(coil_["x"][0]), X(coil_["x"][1]), -sg["pocket"][0] / 2 - 2.0, text=f"코일 {F2(cl_)} (몸통 {F(sg['n'])}권)", ext_from=(-r_m, -r_m), size_px=9, tpos="right")
    xl_ = (long_["x"][0] + long_["x"][1]) / 2
    sv6.dim_h(ax0, X(xl_), sg["pocket"][0] / 2 + 5.0, text=f"긴 다리 +{F2(xl_ - xc_)} (+x 끝)", ext_from=(sg["pocket"][0] / 2, sg["pocket"][0] / 2), size_px=9, tpos="right")
    panel_title(sv6, -13.0, 30.0 - sv6.px(12), f"6. 비틀림 보조 스프링 (D05): 미스미 {spc['part']} — {lb['spring']}", size_px=11.5)
    sv6.text(0, -r_m - 10.5, "끝에서 봄 (레버 0°, 긴 다리 → 뒷벽 홈)", cls="tx-s", size_px=9.5)
    sv6.text(ax0 - 1.0, -r_m - 10.5, "옆에서 봄 (허브 주머니 안, 레버 중심 쇄선)", cls="tx-s", anchor="start", size_px=9.5)
    st = M["spring"]["states"]
    # r4.5 fix: the table rows are the NOMINAL (rigid) lever angles of metrics.spring.states; the settled poses drawn on
    # sheets 1 / 2 (rest with the spring, 1 N bottom with the pad) are quoted under the table so the two do not clash
    st_ko = {"rest": "쉼 (명목, 강체)", "bottom": "바닥 (강체 기구)", "service": "서비스 들기", "hand 25 deg": "손 들기 25°"}
    rows = [[st_ko.get(k_, k_), kit.FX(st[k_]["b"]), kit.FX(st[k_]["wound"]), kit.FX(st[k_]["T"]), F(round(st[k_]["sigma"]))] for k_ in st]   # r4.5 fix 3: fixed 2 decimals per column
    tv6 = View(0, -150, 560, 0, px_width=560, pad_px=6)
    tv6.text(6, -14, f"스프링 상태 — 명목 b (강체 자세, metrics.spring; Su {F(M['spring']['Su'])} MPa)", cls="ttl", anchor="start", size_px=11)
    ty = table(tv6, 6, -22, ["상태", "레버 b °", "감김 °", "토크 N·mm", "응력 MPa"], rows, [140, 90, 90, 105, 105], row_px=17, size_px=10)
    dp_, ht_ = M["clear"]["dip"], M["heights"]
    note_lines(tv6, ["명목 b = 강체 자세 값. 도면 1·2에 그린 정착 자세 (패드·스프링 포함, metrics):",
                     f"  쉼 레버 백 {F2(ht_['b_rest_w'])}° / 흑 {F2(ht_['b_rest_b'])}° · 1 N 정착 바닥 백 {F2(dp_['white']['lever_held'])}° / 흑 {F2(dp_['black']['lever_held'])}°",
                     f"  (강체 바닥 백 {F2(dp_['white']['lever_rigid'])}° / 흑 {F2(dp_['black']['lever_rigid'])}°; 토크 = k_t × (b − 자유각))"],
               6, ty - 14, line_px=15, size_px=10, cls="tx")
    ty -= 3 * 15 + 4
    cat = spc["catalogue"]
    note_lines(tv6, [f"사는 부품: 한국미스미 {cat['part']} — SUS304-WPB d{F(sg['d'])} · ID {F(sg['ID'])} · 3권(몸통 {F(sg['n'])}권), 암 각 90°, {'오른쪽' if cat['hand'] == 'R' else '왼쪽'} 감기,",
                     f"  암 {F(cat['arms'][0])}/{F(cat['arms'][1])} → 긴 다리를 축에서 {F(sg['leg'])}(접점에서 {F2(ltp)}), 짧은 다리를 {F(R.short_leg_len())}로 잘라 씀; 100개 × {F(cat['krw_100'])}원 + VAT",
                     f"k_t {F2(sg['kt'])} N·mm/rad (E {F(spc['E'])}, N_e {F2(M['spring']['N_e'])}), 자유각 {F2(sg['free'])}° (b = 0에서 {F2(abs(sg['free']))}° 감아 설치)",
                     f"카탈로그 최대 {F(cat['max_deg'])}° · {F2(cat['T_max'])} N·mm 대비 손 들기 25° 토크 {F(round(100 * spc['hand_over_catalogue']))} % (잘린 다리가 짧아 강성이 큼)",
                     f"{R.spring_txt()['slot']}: 스프링을 짧은 다리 끝부터 넣는 길",
                     f"{R.spring_txt()['window']}: 긴 다리는 레버 {F(sg['leg_range'][0], 1)}°~{F(sg['leg_range'][1], 1)}° 내내 면과 {F2(sg['leg_margin'])} 이상",
                     f"r4.5 고침 {R.spring_txt()['groove']}: 짧은 다리가 갇힘 —",
                     f"  {R.spring_txt()['contacts']} (쉼 {F2(spc['capture']['F_couple_rest'])} N), 코일이 봉에서 {F2(spc['capture']['gap_rest'])} 뜸",
                     f"긴 다리: 코일 뒤쪽 접선 y{F2(sg['tp'][0])} z{F2(sg['tp'][1])} → 뒷벽 홈 y{F2(sg['tip'][0])} z{F2(sg['tip'][1])} (쉼, 보스 밑에서 들어감)"],
               6, ty - 16, line_px=15, size_px=10)
    tv6.v0 = ty - 16 - 9 * 15 - 8
    # ------------------------------------------------ 7. wedge table (all 12)
    trows = []
    for nm in ORDER:
        w = fpart(f"pad wedge {nm}")
        p = fpart(f"up-stop pad {nm}")
        wq = pts(w)
        # r4.5 fix 3 (issue 5): one fixed precision per column (kit.FX / FR, same half-up rule)
        trows.append([nm, kit.FR(w['x'][0], w['x'][1]), kit.FR(wq[0][0], wq[1][0]), kit.FX(zb0 - wq[0][1]), kit.FX(zb0 - wq[1][1]),
                      f"{kit.FX(pts(p)[0][1])} / {kit.FX(pts(p)[1][1])}", F(round(SOL["seat_k"][nm]))])
    th = (len(trows) + 1) * 17 + 44
    tv = View(0, -th, 1480, 0, px_width=1480, pad_px=6)
    tv.text(8, -16, "쐐기·패드 표 (geometry.json pad wedge / up-stop pad, solved.seat_k) — 쐐기는 패드 바와 한 몸으로 출력", cls="ttl", anchor="start", size_px=12)
    table(tv, 8, -26, ["레버", "x (패드·쐐기)", "쐐기 y", "쐐기 앞 두께", "쐐기 뒤 두께", "패드 면 z 앞 / 뒤 (S15)", "자리 강성 N/mm"], trows,
          [80, 190, 170, 140, 140, 230, 160], row_px=17, size_px=10)
    # r4.4: one panel column ~1536 wide (was 2208 -> text 6.5~8 px at 1600): 1 / 2a + 4 / 2b / 2c / 3 / 6 + table / 5a + 5b / table
    rows_ = [[v1], [sides[0], dv], [sides[1]], [lv], [xv], [sv6, tv6], [cv, cs], [tv]]
    base = os.path.join(OUT, "d09_pad_bar_curtain_spring")
    page(rows_, base, "도면 9. 패드 바 + 업스톱 패드 + 가림판 띠 + 비틀림 스프링 (r3 레일·손나사·커버·스프링 자리를 대신함)",
         "단위 mm · 숫자 = geometry.json (괄호 = 치수표 번호), 스프링 상태 = metrics.json · 연한 갈색 = 패드 바(PETG, 쐐기 포함 한 몸), 보라 = 폼, 빨강 = 펠트, "
         "연보라 = 가림판 띠, 파랑 빗금 = 프레임(윗판·레일)")
    rec(9, base, "패드 바 + 업스톱 패드 + 가림판 띠 + 비틀림 스프링",
        f"r4에서 새로 생긴 작은 부품: 1 패드 바(핀 칸마다 1개, 계단형 {lb['bar_t']}, 앞 손잡이, 쐐기 3개, 양 가장자리 잎 혀)를 밑에서 본 평면, 2a·2b 백·흑 쐐기 자리의 측면 단면(윗판·패드와 함께), 2c 레일 립 위의 잎 혀 확대, "
        f"3 레일 사이 가로 단면, 4 패드(펠트 {lb['pad_felt']} + 폼 {lb['foam']})와 PET 심 자리, 5a·5b 가림판 띠(흑건 노치, 윗판 앞 턱에 거는 걸이), "
        f"6 레버 허브의 비틀림 스프링(r4.5: 미스미 {SOL['spring']['part']}를 사서 두 다리를 자름 — {lb['spring']}; 짧은 다리 {F(R.short_leg_len())}·긴 다리 {F(SOL['spring']['leg'])}, "
        f"자유각 {F2(SOL['spring']['free_deg'])}°, r4.5 고침: 허브 가둠 홈 폭 {F2(SOL['spring']['short_leg_groove']['width'])}·넣는 슬롯·긴 다리 창, 뒷벽 {F(SOL['spring']['groove'][3])} 홈은 {R.spring_txt()['dx']} 가운데)과 상태 표, 7 쐐기·패드·자리 강성 표. 업스톱 힘은 패드 → 쐐기 → 패드 바 → 윗판으로 누르는 힘으로만 전해진다. "
        f"r4.2: 패드 바 계단 y{F(R.bar_steps()[0])}/{F(R.bar_steps()[1])}(윗판 홈 끝 y{F(SOL['y_bar_step'])}보다 앞), 뒤끝 = 윗판 계단 y{F(SOL['plate_step_y'])}, L 레일 립 + 잎 혀(2c). "
        f"r4.4: 레일 웹 앞 아래 모서리를 1×45° 모따기(P13, 2c에 뒤의 웹으로 보임; 칸 가장자리 캐리어 옆벽이 ff에서 지나감 → 레버 ↔ 레일 {F2(web_clear())}).")


def clip_below(poly, zmax):
    """Sutherland-Hodgman clip of a (u, z) polygon to z <= zmax."""
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ina, inb = a[1] <= zmax, b[1] <= zmax
        if ina:
            out.append(a)
        if ina != inb:
            t = (zmax - a[1]) / (b[1] - a[1])
            out.append((a[0] + t * (b[0] - a[0]), zmax))
    return out


def web_clear():
    """r4.4 changes_this_round (pad-bar rail webs): 'now lever-rail 1.52' -> 1.52."""
    c = next(c for c in G["changes_this_round"] if c["part"].startswith("frame (module, end parts): pad-bar rail webs"))
    return float(re.search(r"now lever-rail (\d+(?:\.\d+)?)", c["why"]).group(1))


# ================================================================ sheet 10: end parts (left A0 A#0 B0, right C8)
def ep_bodies(parts):
    keys, levers = [], []
    for p in parts:
        b = p["body"]
        if b.startswith("key ") and b not in keys:
            keys.append(b)
        if b.startswith("lever ") and b not in levers:
            levers.append(b)
    return keys, levers


def ep_is_frame(n):
    return (is_frame(n) or (n.startswith("cheek") or is_boss(n))) and not is_fem(n)


def bb_pose(p, pose="rest"):
    return bbox(pts(p, pose) if "side" not in p else pts(p))


def ep_plan(v, P, E):
    parts = E["parts"]
    fx = [p for p in parts if p["body"] == "fixed"]
    keys, levers = ep_bodies(parts)
    fl = next(p for p in fx if p["part"] == "floor")
    v.poly(prect(fl), cls="faintfill")
    for key, cls in (("cheek", "m-print"), ("white front rail", "m-print"), ("black stop rail", "m-print"), ("black tab base", "m-print"),
                     ("balance rail (lowered", "m-print"), ("balance rail cradle", "m-print2"), ("rod end stop post", "m-print2"),
                     ("rear shelf", "m-print"), ("rear wall", "m-print"), ("tab ", "m-print2"), ("keeper hook", "m-print2"), ("fin", "m-print")):
        for p in fx:
            if p["part"].startswith(key) and not is_boss(p["part"]):
                hpoly(v, prect(p), cls, P["print"] if cls == "m-print" else None)
    for p in fx:
        if is_boss(p["part"]):
            hpoly(v, prect(p), "m-print2")
        if p["part"].startswith("spring groove boss"):      # r4.2: rear-wall bosses with the spring-leg grooves (P18)
            hpoly(v, prect(p), "m-print", P["print"])
        if p["part"].startswith("balance pin"):
            q = prect(p)
            v.circle((q[0][0] + q[1][0]) / 2, (q[0][1] + q[2][1]) / 2, (q[1][0] - q[0][0]) / 2, cls="m-steel")
    for k in keys:
        kp = [p for p in parts if p["body"] == k]
        black = "#" in k
        top = [rect(p["x"][0], p["x"][1], bb_pose(p)[0], bb_pose(p)[1]) for p in kp
               if p["part"] in (("skin", "wall L low", "wall R low", "front wall low") if black else ("skin head", "skin tail"))]
        fill_rings(v, union_rings(top, res=0.05), "m-black" if black else "m-key")
        for p in kp:
            if p["part"] in ("balance block", "beam", "thin tail"):
                b_ = bb_pose(p)
                v.poly(rect(p["x"][0], p["x"][1], b_[0], b_[1]), cls="hid")
            if p["part"] == "capstan head":
                b_ = bb_pose(p)
                v.circle((p["x"][0] + p["x"][1]) / 2, (b_[0] + b_[1]) / 2, (p["x"][1] - p["x"][0]) / 2, cls="hid")
            if p["part"] == "magnet boss":
                v.circle((p["x"][0] + p["x"][1]) / 2, dn("P29"), mag_d() / 2, cls="hid")
        kx = [p for p in kp if p["part"] in (("skin",) if black else ("skin head",))][0]
        v.text((kx["x"][0] + kx["x"][1]) / 2, 110.0 if black else 20.0, k[4:], cls="inv" if black else "ttl", size_px=12)
    # the curtain strip (cut at the plan height, above the white keys)
    for p in fx:
        if p["part"] == "cover curtain":
            y0, y1, z0, z1 = bbox(pts(p))
            if z0 < R.plan_cut_z()[0]:
                hpoly(v, rect(p["x"][0], p["x"][1], y0, y1), "m-cover", P["cover"])
    # levers (carrier + visible steel between the top lips + hub collars)
    lt = lever_top_features()
    for lv in levers:
        lp = [p for p in parts if p["body"] == lv]
        x0 = next(p for p in lp if p["part"] == "carrier side wall L")["x"][0]
        x1 = next(p for p in lp if p["part"] == "carrier side wall R")["x"][1]
        y0, y1 = ppoly("lever C")[0][1], ppoly("lever C")[2][1]      # same carrier as the module (plan at 0 deg)
        xc = (x0 + x1) / 2
        hpoly(v, rect(x0, x1, y0, y1), "m-lever", P["lever"])
        for p in lp:
            if p["part"] == "hub collar":
                hq = ppoly("lever C hub + collars")
                hpoly(v, rect(p["x"][0], p["x"][1], hq[0][1], hq[2][1]), "m-lever", P["lever"])
        for sr in R.steel_plan_rects(xc, lt):
            hpoly(v, sr, "m-steel")
        v.cl(xc, y0 - 3.0, xc, y1 + 3.0)
    sg = spring_geom()
    lgD = R.spring_parts("D")[2]                              # r4.5: the long leg rises at +0.81 from the groove / lever centre
    grD = next(t for t in SOL["spring"]["grooves"] if t["lever"] == "D")
    off_ = (lgD["x"][0] + lgD["x"][1]) / 2 - sum(grD["x"]) / 2
    for gr in E.get("spring_grooves", []):                    # r4.2: grooves exported for the end parts (left 3, right 1)
        v.poly(rect(gr["x"][0], gr["x"][1], gr["y"][0], gr["y"][1]), cls="void")
        gxc = sum(gr["x"]) / 2 + off_
        v.line(gxc, sg["tp"][0], gxc, sg["tip"][0], cls="spring")
    for p in fx:                                              # sensor bars under the keys (hidden, r4.2 end parts)
        if p["part"] == "sensor bar":
            b_ = bbox(pts(p))
            v.poly(rect(p["x"][0], p["x"][1], b_[0], b_[1]), cls="hid")
    # r4.4 (circuit session, A02 / A03): sensor board EL / ER + its printed support (post, ribs with the lead gap),
    # lead pads and underside wires, the lead W401 / W411 on the floor, its lane under the balance rail and the rear-wall notch
    for p in E["plan"]:
        n = p["part"]
        q = [tuple(t) for t in p.get("poly", [])]
        if n.startswith("sensor board support") or n.startswith(("lead lane", "rear-wall lead notch")):
            v.poly(q, cls="hid")
        elif n.startswith("sensor board E"):
            v.poly(q, cls="env")
        elif n.startswith("underside wire"):
            v.poly(q, cls="env")
        elif n.startswith("lead W"):
            v.poly(q, cls="lead")
        elif " lead pad " in n:
            c = p["circle"]
            v.circle(c[0], c[1], c[2], cls="env")
    fins = E["fins"]
    v.cl(fins[0][1], L[0], fins[-1][0], L[0])
    # above the cut: top plate, pad bar, rails, pads (phantom)
    for p in fx:
        n = p["part"]
        if n.startswith(("top plate", "pad bar", "up-stop pad")) and not n.startswith(("pad bar grip", "pad bar leaf", "pad bar (edge")):
            v.poly(prect(p), cls="phan")
    return fx, keys, levers


def _segd(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _inside(p, poly):
    x, y = p
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _polyd(P_, Q):
    if any(_inside(p, Q) for p in P_) or any(_inside(q, P_) for q in Q):
        return 0.0
    return min(min(_segd(P_[i], Q[j - 1], Q[j]), _segd(Q[j], P_[i - 1], P_[i])) for i in range(len(P_)) for j in range(len(Q)))


def box_clearance(xr, yz, parts, poses=("rest", "dip", "ff", "over")):
    """smallest 3-D distance between the prism x in xr, (y, z) polygon yz and the moving parts (x-range prisms
    of geometry.json, every pose).  Returns (distance, body, part, pose)."""
    best = None
    for p in parts:
        for pose in poses:
            q = p.get("side") or p.get("side_" + pose)
            if not q:
                continue
            dx = max(0.0, p["x"][0] - xr[1], xr[0] - p["x"][1])
            d = math.hypot(dx, _polyd(yz, [tuple(t) for t in q]))
            if best is None or d < best[0]:
                best = (d, p["body"], p["part"], pose)
    return best


def PARTS_ALL():
    return kit.PARTS


def mag_d():
    return R.mag_size()[0]


def ep_xz(v, P, y, parts):
    fx = [p for p in parts if p["body"] == "fixed"]
    keys, levers = ep_bodies(parts)
    frame, over, bar = [], [], []
    for p in fx:
        n = p["part"]
        if n.startswith("up-stop pad"):
            for poly, cls in R.pad_layers(p)[0]:
                for z0, z1 in yslice(poly, y):
                    over.append((cls, rect(p["x"][0], p["x"][1], z0, z1)))
            continue
        if p.get("female") and "front" in p:        # r4.5 fix: groove entry chamfer = its exported x-z (front) outline
            if yslice(pts(p), y):
                over.append(("void", [tuple(t) for t in p["front"]]))
            continue
        for z0, z1 in yslice(pts(p), y):
            r_ = rect(p["x"][0], p["x"][1], z0, z1)
            if ep_is_frame(n):
                frame.append(r_)
            else:
                cls, h = mat_fixed(n)
                if cls != "env":
                    over.append((cls, r_))
                if n.startswith(("pad bar", "pad wedge")) and not n.startswith("pad bar rail"):
                    bar.append(r_)
    fill_rings(v, union_rings(frame, res=0.03), "m-print", P["print"])
    for cls, r_ in over:
        hpoly(v, r_, cls, P["bar"] if cls == "m-bar" else (P["cover"] if cls == "m-cover" else None))
    stroke_rings(v, union_rings(bar, res=0.03), "out")
    for k in keys:
        kb, ov = [], []
        for p in parts:
            if p["body"] != k:
                continue
            for z0, z1 in yslice(pts(p, "rest"), y):
                r_ = rect(p["x"][0], p["x"][1], z0, z1)
                (ov if p["part"] in ("capstan head", "rest felt") else kb).append((r_, p["part"]))
        if kb:
            fill_rings(v, union_rings([r_ for r_, _ in kb], res=0.03), "m-black" if "#" in k else "m-key", None if "#" in k else P["key"])
        for r_, n in ov:
            hpoly(v, r_, "m-steel" if n == "capstan head" else "m-felt", P["steel"] if n == "capstan head" else None)
    for lv in levers:                 # r4.4: the top snap lips are exported lever parts (sliced with the rest)
        lb, lo = [], []
        wl = None
        for p in parts:
            if p["body"] != lv:
                continue
            if p["part"] == "carrier side wall L":
                wl = p
            for z0, z1 in yslice(pts(p, "rest"), y):
                r_ = rect(p["x"][0], p["x"][1], z0, z1)
                if p["part"].startswith("steel"):
                    lo.append((r_, "m-steel"))
                elif p["part"].startswith("felt"):
                    lo.append((r_, "m-felt"))
                else:
                    lb.append(r_)
        if lb:
            fill_rings(v, union_rings(lb, res=0.03), "m-lever", P["lever"])
        for r_, c in lo:
            hpoly(v, r_, c, P["steel"] if c == "m-steel" else None)


def ep_bar_outer(fx):
    """end-part pad bar: OUTER x range (grip + edge strips), the core x range (= the leaf-window edges) and the core
    y range.  (geometry end_parts 'pad bar' is the core between the leaf windows, the module plan 'pad bar' the outer.)"""
    bp = [p for p in fx if p["part"].startswith("pad bar") and not p["part"].startswith("pad bar rail")]
    core = next(p for p in fx if p["part"] == "pad bar")
    b_ = bbox(pts(core))
    return (min(p["x"][0] for p in bp), max(p["x"][1] for p in bp)), tuple(core["x"]), (b_[0], b_[1])


def ep_bar_bottom(E, title, S=7.0):
    """r4.4: small bottom view of an end-part pad bar (like sheet 9 panel 1): outer outline, grip, leaf windows + tongues,
    wedges, pads, rails and rail lips (phantom), lever centre lines, full width, x ordinates below, y ordinates right."""
    fx = [p for p in E["parts"] if p["body"] == "fixed"]
    (xo0, xo1), (xc0, xc1), (by0, by1) = ep_bar_outer(fx)
    grip = next(p for p in fx if p["part"] == "pad bar grip")
    fr = [p for p in fx if p["part"].startswith("pad bar (edge strip, front")]
    bk = [p for p in fx if p["part"].startswith("pad bar (edge strip, behind")]
    tongs = [p for p in fx if p["part"].startswith("pad bar leaf")]
    rails = [p for p in fx if p["part"] == "pad bar rail"]
    lips = [p for p in fx if p["part"] == "pad bar rail lip"]
    wedges = [p for p in fx if p["part"].startswith("pad wedge")]
    pads = [p for p in fx if p["part"].startswith("up-stop pad")]
    y_j0, y_j1 = R.bar_steps(fx)
    U0, U1, V0, V1 = min(xo0, min(r["x"][0] for r in rails)) - 8.0, xo1 + 58.0, by0 - 16.0, by1 + 17.0
    v = View(U0, V0, U1, V1, px_width=(U1 - U0) * S, pad_px=6)
    P = pids(v)
    hpoly(v, rect(xo0, xo1, by0, by1), "m-bar", P["bar"])
    hpoly(v, rect(xo0, xo1, by0, bbox(pts(grip))[1]), "m-bar")
    wins = []
    for f_ in fr:
        b_ = next(q for q in bk if abs(q["x"][0] - f_["x"][0]) < 1e-6)
        wins.append((f_["x"][0], f_["x"][1], bbox(pts(f_))[1], bbox(pts(b_))[0]))
        v.poly(rect(f_["x"][0], f_["x"][1], bbox(pts(f_))[1], bbox(pts(b_))[0]), cls="void")
    for t_ in tongs:
        b_ = bbox(pts(t_))
        hpoly(v, rect(t_["x"][0], t_["x"][1], b_[0], b_[1]), "m-bar", P["bar"])
    v.line(xo0, y_j0, xo1, y_j0, cls="vis")
    v.line(xo0, y_j1, xo1, y_j1, cls="hid")
    for w in wedges:
        b_ = bbox(pts(w))
        hpoly(v, rect(w["x"][0], w["x"][1], b_[0], b_[1]), "m-bar")
    for p_ in pads:
        q = pts(p_)
        v.poly(rect(p_["x"][0], p_["x"][1], min(t[0] for t in q[:2]), max(t[0] for t in q[:2])), cls="m-foam")
    for r_ in rails + lips:
        b_ = bbox(pts(r_))
        v.poly(rect(r_["x"][0], r_["x"][1], b_[0], b_[1]), cls="phan")
    for nm, x in E["levers"].items():
        v.cl(x, by0 - 3.0, x, by1 + 3.0)
        v.text(x, by1 + 4.5, nm, cls="ttl", size_px=10.5)
    xf = [(xo0, by0, "패드 바 (P13)"), (xo1, by0, "")] + [(a, 175.0, "잎 창") for a in (xc0, xc1)] + \
         [(r_["x"][0], bbox(pts(r_))[0], "레일") for r_ in rails] + [(r_["x"][1], bbox(pts(r_))[0], "") for r_ in rails] + \
         [(w["x"][0], bbox(pts(w))[0], f"쐐기 {w['part'][10:]}") for w in wedges] + [(w["x"][1], bbox(pts(w))[0], "") for w in wedges]
    ordy(v, xf, by0 - 2.0, gap_px=12.5, label_px=9)
    yl = [(by0, xo1, "앞 = 손잡이 (P13)"), (bbox(pts(grip))[1], xo1, "손잡이 끝"), (bbox(pts(lips[0]))[0], xo1, "레일 립 시작"),
          (y_j0, xo1, "밑 계단"), (y_j1, xo1, "윗 계단 (숨은선)"), (wins[0][2], xo1, "잎 창"),
          (max(bbox(pts(t_))[1] for t_ in tongs), xo1, "잎 혀 뿌리"), (by1, xo1, "끝 = 윗판 계단")]
    ordz(v, yl, xo1 + 4.0, gap_px=12.5, label_px=9, prefix="y")
    v.dim_h(xo0, xo1, by1 + 11.0, text=f"{F2(xo1 - xo0)} 전체 폭", ext_from=(by1, by1), size_px=9.5)
    panel_title(v, U0 + v.px(3), V1 - v.px(13), title, size_px=11)
    return v, xo1 - xo0


def sheet_end_parts():
    EP = G["end_parts"]
    lb = R._labels()
    panels = []
    S = 6.6
    a04 = dns("A04")
    x_right = a04[0] + a04[1] * 7
    specs = {"left": dict(U0=-70.0, U1=56.0, W=dn("A02"), title="왼쪽 끝 부속 A0·A#0·B0", cid="A02"),
             "right": dict(U0=-8.0, U1=88.0, W=dns("A03", "ref")[1], title=f"오른쪽 끝 부속 C8 (로컬 x, 전체 x = {F2(x_right)} + x, A04)", cid="A03")}
    for side in ("left", "right"):
        E = EP[side]
        sp = specs[side]
        v = View(sp["U0"], -34.0, sp["U1"], 262.0, px_width=(sp["U1"] - sp["U0"]) * S, pad_px=6)
        P = pids(v)
        fx, keys, levers = ep_plan(v, P, E)
        ch = E["cheek"]
        Wm = dn("P01")
        if side == "left":
            xo = sp["W"]
            for fem, male in dovetail_polys():
                hpoly(v, [(q[0] - Wm + xo, q[1]) for q in male], "m-print", P["print"])
                yc_ = (male[0][1] + male[3][1]) / 2
                v.text(xo + dns("D09")[2] + v.px(3), yc_ - v.px(3.5), "D09", cls="tx-s", anchor="start", size_px=9)
            nb = [p for p in fixed() if (p["part"] == "fin" or is_boss(p["part"])) and p["x"][0] < 1.0]
            shift = xo
        else:
            xo = 0.0
            for fem, male in dovetail_polys():
                hpoly(v, fem, "void")
                v.poly([(q[0] - Wm, q[1]) for q in male], cls="phan")
                yc_ = (fem[0][1] + fem[3][1]) / 2
                v.text(-dns("D09")[2] - v.px(3), yc_ - v.px(3.5), "D09", cls="tx-s", anchor="end", size_px=9)
            nb = [p for p in fixed() if (p["part"] == "fin" or is_boss(p["part"])) and p["x"][1] > Wm - 1.0]
            nb += R.ledge_parts()                  # r4.5 circuit 2nd (P36): the neighbour module's sensor-bar right ledge
            shift = -Wm
        for p in nb:
            v.poly(rect(p["x"][0] + shift, p["x"][1] + shift, bbox(pts(p))[0], bbox(pts(p))[1]), cls="phan")
        v.line(xo, -3.0, xo, dns("A05")[0] + 3.0, cls="phan")
        r1 = [(x, 207.55, nm) for nm, x in E["levers"].items()] + [(sum(f) / 2, 209.0, "핀") for f in E["fins"]]
        lab1 = ordy(v, r1, 222.0, side="above", gap_px=12.5, label_px=9)
        (bo0, bo1), (bc0, bc1), _ = ep_bar_outer(fx)          # r4.4: outer edges = the bar; core edges = leaf windows
        r2 = [(bo0, 183.0, "패드 바"), (bo1, 183.0, "패드 바")] + [(bc0, 183.0, "잎 창"), (bc1, 183.0, "잎 창")] + \
             [(p["x"][0], 183.0, "레일") for p in fx if p["part"] == "pad bar rail"] + [(p["x"][1], 183.0, "") for p in fx if p["part"] == "pad bar rail"]
        ordy(v, r2, 244.0, side="above", gap_px=12.5, label_px=9, breaks=lab1)
        v.dim_h(0.0, sp["W"], -8.0, text=f"{F2(sp['W'])} 건반 구역", ext_from=(0.0, 0.0), size_px=9.5)
        v.dim_h(ch[0], ch[1], -8.0, text=f"볼 {F2(ch[1] - ch[0])}", ext_from=(0.0, 0.0), size_px=9.5)
        tot = (min(ch[0], 0.0), max(ch[1], sp["W"]))
        ttxt = (f"{F2(tot[1] - tot[0])} = 볼 쪽 {F2(-tot[0])} + {F2(sp['W'])} ({sp['cid']})" if side == "left"
                else f"{F2(tot[1] - tot[0])} = {F2(sp['W'])} + 볼 쪽 {F2(tot[1] - sp['W'])} ({sp['cid']})")
        v.dim_h(tot[0], tot[1], -20.0, text=ttxt, ext_from=(0.0, 0.0), size_px=10)
        panel_title(v, sp["U0"] + 1.0, 262.0 - v.px(4), sp["title"], size_px=12.5)
        if side == "left":
            fr = next(p for p in fx if p["part"] == "white front rail")
            cur = next(p for p in fx if p["part"] == "cover curtain")
            pl = next(p for p in fx if p["part"].startswith("top plate"))
            pad = next(p for p in fx if p["part"].startswith("up-stop pad"))
            yl = [(0.0, 0.0, "백건 앞끝"), (bbox(pts(fr))[1], 0.5, "앞 레일 끝"), (dns("P30")[0], 21.7, "흑건 앞 (P30)"),
                  (dn("P29"), min((p["x"][0] + p["x"][1]) / 2 for p in E["parts"] if p["part"] == "magnet boss") - mag_d() / 2, "자석 (P29)"),
                  (dns("P20")[0], 0.3, "밸런스 레일"), (K[0], 1.55, "봉 K"), (bbox(pts(cur))[0], 0.2, "가림판 (P26)"),
                  (bbox(pts(pl))[0], 0.0, "윗판·패드 바 (P15)"), (dn("S13", 0), 5.0, "레버 앞"), (dn("P16", 0), pad["x"][0], "패드 (P16)"),
                  (dn("P16", 1), pad["x"][0], ""), (L[0], -1.8, "L"), (dns("S28")[0], 0.2, "뒷벽"), (dns("A05")[0], 0.0, "뒤끝")]
            ordz(v, yl, ch[0] - 3.0, side="left", gap_px=12, label_px=9, prefix="y")
        panels.append(v)
    # x-z sections at the pad row
    xzs = []
    y_pad = R.sheet4_y_pad()
    for side in ("left", "right"):
        E = EP[side]
        sp = specs[side]
        xv = View(sp["U0"], -13.0, sp["U1"], dn("S18") + 14.0, px_width=(sp["U1"] - sp["U0"]) * S, pad_px=6)
        Px = pids(xv)
        ep_xz(xv, Px, y_pad, E["parts"])
        ch = E["cheek"]
        chk = next(p for p in E["parts"] if p["part"] == "cheek")
        cx_ = chk["x"][0] if side == "left" else chk["x"][1]
        rl = [p for p in E["parts"] if p["part"] == "pad bar rail"]
        zf = [(dns("S01")[3], sp["W"], "바닥"), (dn("S17"), cx_, "패드 바 자리 (S17)"), (min(bbox(pts(p))[2] for p in rl), cx_, "레일 밑 (P13)"),
              (bbox(pts(chk))[3], cx_, "볼 윗면 = 윗판 위 (S18)")]
        if side == "left":
            ordz(xv, zf, ch[0] - 4.0, side="left", gap_px=12, label_px=9)
        else:
            ordz(xv, zf, ch[1] + 3.0, gap_px=12, label_px=9)
        ordy(xv, [(p["x"][0], bbox(pts(p))[2], "레일") for p in rl] + [(p["x"][1], bbox(pts(p))[2], "") for p in rl] +
             [(ch[0], 3.0, "볼"), (ch[1], 3.0, "")], -1.0, gap_px=12.5, label_px=9)
        panel_title(xv, sp["U0"] + 1.0, dn("S18") + 14.0 - xv.px(12), f"가로 단면 y = {F2(y_pad)} (패드 줄) — 볼·윗판·패드 바 레일·패드·레버", size_px=11)
        xzs.append(xv)
    # r4.4 (A02 / A03): sensor-board support, lead lane, rear-wall notch
    CE = G["circuit_r44"]["ends"]
    rib_xz, lead_yz = [], []
    for side in ("left", "right"):
        E = EP[side]
        ce = CE[side]
        fx = [p for p in E["parts"] if p["body"] == "fixed"]
        pads = sorted((p["circle"] for p in E["plan"] if " lead pad " in p["part"]), key=lambda c: c[0])
        y_r = pads[0][1]                                         # the pad row (inside the rear rib)
        # r4.5 audit (R50): the right panel starts at x-3.6 so the neighbour module's ledge lip (x-3.0~-1.5) is drawn whole;
        # the top is raised 16.0 -> V1 (both panels, same z levels side by side) so the title / note clear the lip top z15.1
        U0, Uc = (-3.6 if side == "right" else -2.0), ce["board"][1] + 1.5   # clip window: the board zone (the cheek beyond is not drawn)
        S_ = 15.0
        V1 = 17.4
        U1 = Uc + (190.0 - (-2.0 - U0) * S_) / S_             # room for the z labels (the right panel's wider start is
        # taken from this room, so the row stays inside the 1500-px sheet)
        xv = View(U0, -2.0, U1, V1, px_width=(U1 - U0) * S_, pad_px=6)
        Px = pids(xv)
        i0x = clip_begin(xv)
        frame_r, over_ = [], []
        for p in fx:
            for z0, z1 in yslice(pts(p), y_r):
                r_ = rect(p["x"][0], p["x"][1], z0, z1)
                if ep_is_frame(p["part"]):
                    frame_r.append(r_)
                elif p["part"].startswith("sensor board E"):
                    over_.append((r_, "m-pcb"))
                elif p["part"] == "sensor bar":
                    over_.append((r_, "m-sbar"))
        fill_rings(xv, union_rings(frame_r, res=0.02), "m-print", Px["print"])
        for r_, c in over_:
            hpoly(xv, r_, c, Px["print"] if c == "m-sbar" else None)
        sbz = bbox(pts(next(p for p in fx if p["part"].startswith("sensor board E"))))
        for c in pads:                                           # lead pads on the underside of the board (circuit A02 / A03)
            xv.poly(rect(c[0] - c[2], c[0] + c[2], sbz[2] - 0.35, sbz[2]), cls="m-wire")
        clip_end(xv, i0x, U0, Uc, 2.0, 15.0, frame=False)
        post = next(p for p in fx if p["part"].startswith("sensor board support post"))
        ribs = sorted((p for p in fx if p["part"].startswith("sensor board support rib rear")), key=lambda p: p["x"][0])
        rz = bbox(pts(ribs[0]))[3]
        # r4.5 audit (R50): where a rear rib starts at the post end (EL: post x0.5~6 + rib x6~15, both z5~7) the two are
        # one outline in this section and x6 has no edge -> no ordinate there (x6 is in the plan above)
        abut_ = [p for p in ribs if abs(p["x"][0] - post["x"][1]) < 1e-6]
        xf = [(post["x"][0], 5.0, "기둥")] + ([] if abut_ else [(post["x"][1], 5.0, "")])
        gap = tuple(ce["gap"])
        for p in ribs:
            xf += ([] if p in abut_ else [(p["x"][0], 5.0, "뒤 리브" if p["x"][0] > post["x"][1] + 0.1 else "")]) + [(p["x"][1], 5.0, "")]
        xf += [(c[0], sbz[2] - 0.35, "패드" if i in (0, len(pads) - 1) else "") for i, c in enumerate(pads)]
        xf += [(ce["board"][0], sbz[3], "기판"), (ce["board"][1], sbz[3], "")]
        ordy(xv, xf, -0.5, gap_px=12.5, label_px=9)
        ordz(xv, [(dns("S01")[3], Uc, "바닥 위"), (rz, Uc, f"받침 위 = 기판 밑"), (sbz[3], Uc, "기판 위 (v3 1.6)"),
                  (min(15.0, max(bbox(pts(p))[3] for p in fx if p["part"] == "sensor bar")), Uc, "센서 바 (v3)")],
             Uc + 0.4, gap_px=12.5, label_px=9, hi=16.0)
        xv.dim_h(gap[0], gap[1], dns("S01")[2] - 1.0, text=f"리브 틈 {F2(gap[1] - gap[0])}", ext_from=(dns("S01")[2], dns("S01")[2]), size_px=9)
        panel_title(xv, U0 + xv.px(3), V1 - xv.px(12),
                    f"{'왼쪽 EL' if side == 'left' else '오른쪽 ER'}: 가로 단면 y = {F2(y_r)} (리드 패드 줄) — 센서 기판 받침·뒤 리브 틈 ({'A02' if side == 'left' else 'A03'})", size_px=10.5)
        nl_ = [f"패드 ↔ 리브 {F2(ce['pad_margins'][0])} / {F2(ce['pad_margins'][1])}, 아랫면 선 ↔ 리브 {F2(ce['wire_margins'][0])} / {F2(ce['wire_margins'][1])} (P36)"]
        CL_ = G["circuit_r45"]["ledge"]
        nu_ = U0 + 0.3
        if side == "right":
            # r4.5 circuit 2nd (P36): the neighbour module's right ledge (lip + post) just left of the seam, phantom;
            # r4.5 audit (R50): the panel now starts at U0 = -3.6, so the whole lip x161.5~163 (local -3.0~-1.5) is drawn
            Wm_ = dn("P01")
            lgy_ = [p for p in R.ledge_parts() if yslice(pts(p), y_r)]
            if lgy_:
                lx0, lx1 = CL_["lip"][0] - Wm_, CL_["lip"][1] - Wm_
                assert lx0 >= U0 + 0.2, "ledge lip outside the ER rib panel"
                px1 = CL_["post"][1] - Wm_
                xv.poly([(lx0, CL_["z"][0]), (lx1, CL_["z"][0]), (lx1, CL_["floor_z"]), (px1, CL_["floor_z"]), (px1, CL_["z"][1]),
                         (lx0, CL_["z"][1])], cls="phan")
                nu_ = px1 + xv.px(8)                   # the note starts right of the phantom post (named in the notes)
        note_lines(xv, nl_, nu_, V1 - xv.px(26), line_px=13, size_px=9)
        rib_xz.append(xv)
        # ---- y-z at the lead centre x: lane under the balance rail (rail bottom raised) and the rear-wall notch
        xs = ce["lead_xc"]
        sv = View(-6.0, -8.0, 242.0, 34.0, px_width=1480, pad_px=6)
        Ps = pids(sv)
        i0 = clip_begin(sv)
        cut = [p for p in fx if cut_x(p, xs)]
        fill_rings(sv, union_rings([pts(p) for p in cut if ep_is_frame(p["part"])]), "m-print", Ps["print"])
        for p in cut:
            n = p["part"]
            if n.startswith("sensor board E"):
                hpoly(sv, pts(p), "m-pcb")
            elif n == "sensor bar":
                hpoly(sv, pts(p), "m-sbar", Ps["print"])
            elif n.startswith("balance pin"):
                hpoly(sv, pts(p), "m-steel", Ps["steel"])
        clip_end(sv, i0, -2.0, 214.0, 2.0, 28.0)
        lane = [tuple(t) for t in next(p for p in E["plan"] if p["part"].startswith("lead lane"))["poly"]]
        notch = [tuple(t) for t in next(p for p in E["plan"] if p["part"].startswith("rear-wall lead notch"))["poly"]]
        lz, nz = ce["lane_z"], ce["notch_z"]
        lead = [tuple(t) for t in next(p for p in E["plan"] if p["part"].startswith("lead W"))["poly"]]
        yl0 = min(t[1] for t in lead)
        sv.poly(rect(yl0, dns("A05")[0], lz[0], lz[0] + 0.6), cls="lead")          # the lead on the floor (flat, drawn 0.6)
        ordz(sv, [(lz[0], 216.0, "바닥 위 = 리드 길"), (lz[1], 216.0, f"레일 밑 (차선 z{F(lz[0])}~{F(lz[1])})"), (nz[1], 216.0, "뒷벽 홈 위"),
                  (dns("P20")[3], 216.0, "레일 위 (P20)"), (SOL["z_shelf"], 216.0, "선반 위 (S10)")], 216.0, gap_px=12, label_px=9, hi=28.0)
        yf_ = [(pads[0][1], 7.0, "패드 줄"), (ce["fan_y"], 5.0, "모음 끝"), (lane[0][1], lz[1], "차선"), (lane[2][1], lz[1], ""),
               (notch[0][1], nz[1], "뒷벽 홈"), (notch[2][1], nz[1], "")]
        ordy(sv, yf_, 1.0, gap_px=12.5, label_px=9, lo=-2.0)
        panel_title(sv, -5.0, 34.0 - sv.px(12),
                    f"{'왼쪽 EL' if side == 'left' else '오른쪽 ER'}: 측면 단면 x = {F2(xs)} (리드 {'W401 5심' if side == 'left' else 'W411 3심'} 가운데, 프레임만, z{F(2.0)}~{F(28.0)}) — "
                    f"레일 밑 차선 x{F2(lane[0][0])}~{F2(lane[1][0])} · 뒷벽 홈 z{F(nz[0])}~{F(nz[1])} (같은 x)", size_px=10.5)
        pins_ = "; ".join(f"{t[0]} 밸런스 핀 밑 레일 {F2(t[2])}" for t in ce["pins_over_lane"])
        note_lines(sv, [f"리드 (굵은 회색, 바닥) {F2(ce['lead_w'])} 폭 x{kit.FR(ce['lead'][0], ce['lead'][1])} + 양옆 1.3 = 차선 {F2(ce['lane_w'])}; 리드 길 ↔ 바닥 부품 최소 {F2(ce['path_min'][0])} ({ce['path_min'][1]})"
                        + (f", 흑 탭 받침 {F2(ce['tab_gap'])}" if ce.get("tab_gap") else "") + (f"; {pins_}" if pins_ else "")],
                   -5.0, 34.0 - sv.px(27), line_px=13, size_px=9.5)
        lead_yz.append(sv)
    rows = []
    for side in ("left", "right"):
        E = EP[side]
        st = M["end_parts"][side]["stat"]
        for nm, x in E["levers"].items():
            s_ = st[nm]
            blk = M["end_parts"][side]["blocks"][nm]
            wq = pts(next(p for p in E["parts"] if p["part"] == f"pad wedge {nm}"))
            zb0 = min(q[1] for q in pts(next(p for p in E["parts"] if p["part"] == "pad bar")))
            # r4.5 fix 3 (issue 5): one fixed precision per column (kit.FX = the same half-up rule, trailing zeros kept)
            rows.append([nm, "왼쪽" if side == "left" else "오른쪽", kit.FX(x), kit.FR(blk[0], blk[1]), kit.FX(E["caps"][nm]), kit.FX(s_["DW"], 1), kit.FX(s_["UW"], 1),
                         kit.FX(s_["meff"], 1), kit.FX(s_["key_g"], 1), kit.FX(s_["gap_to_face"]), kit.FX(s_["gap_design"]), kit.FR(zb0 - wq[0][1], zb0 - wq[1][1])])
    tv = View(0, -190, 1480, 0, px_width=1480, pad_px=6)
    tv.text(8, -16, "끝 부속 건반 (geometry.json end_parts + metrics.json end_parts, 같은 모델 실행) — 레버·캐리어·강철·스프링·패드는 모듈과 같은 부품", cls="ttl", anchor="start", size_px=12)
    table(tv, 8, -26, ["건반", "쪽", "레버·캡스턴 x", "밸런스 블록 x", "캡스턴 y", "DW g", "UW g", "m_eff g", "건반 g", "모듈 쐐기라면 강철–면", "자기 면 = 설계", "자기 쐐기 (P17)"], rows,
          [60, 60, 110, 150, 90, 70, 70, 80, 70, 150, 70, 150], row_px=18, size_px=10)
    chz = bbox(pts(next(p for p in EP["left"]["parts"] if p["part"] == "cheek")))[3]
    c8b = M["end_parts"]["right"]["blocks"]["C8"]
    Wm = dn("P01")
    dvp = {n: next(p for p in fixed() if p["part"].startswith(n)) for n in
           ("rear dovetail (female", "rear dovetail male root", "front dovetail (female", "front dovetail male root")}
    mvL = [p for p in EP["left"]["parts"] if p["body"] != "fixed"]
    mvR = [p for p in EP["right"]["parts"] if p["body"] != "fixed"]

    def _male_x(p):
        return (dn("A02") - (Wm - p["x"][0]), dn("A02") - (Wm - p["x"][1]))
    cl = [box_clearance(_male_x(dvp["rear dovetail male root"]), pts(dvp["rear dovetail male root"]), mvL),
          box_clearance(_male_x(dvp["front dovetail male root"]), pts(dvp["front dovetail male root"]), mvL),
          box_clearance(dvp["rear dovetail (female"]["x"], pts(dvp["rear dovetail (female"]), mvR),
          box_clearance(dvp["front dovetail (female"]["x"], pts(dvp["front dovetail (female"]), mvR)]
    fz = bbox(pts(dvp["rear dovetail (female"]))

    def _seam(side):
        E_ = EP[side]
        own = [p for p in E_["parts"] if p["part"] == "fin" or is_boss(p["part"])]
        if side == "left":
            own = [p for p in own if p["x"][1] > dn("A02") - 4.0]
            nbp = [p for p in fixed() if (p["part"] == "fin" or is_boss(p["part"])) and p["x"][0] < 4.0]
            return min((q["x"][0] + dn("A02")) - p["x"][1] for p in own for q in nbp), own
        own = [p for p in own if p["x"][0] < 4.0]
        nbp = [p for p in fixed() if (p["part"] == "fin" or is_boss(p["part"])) and p["x"][1] > Wm - 4.0]
        return min(p["x"][0] - (q["x"][1] - Wm) for p in own for q in nbp), own
    CR_ = G["circuit_r45"]                          # r4.5 circuit 2nd: EL floor (A02) + sensor-bar ledge / end bars (P36)
    EF_ = CR_["el_floor"]["now"]["left"]
    rg_ = lambda a, b: f"{F(a)}~{F(b)}"             # text range (same rounding helper, no trailing zeros)
    sg_l, own_l = _seam("left")
    sg_r, own_r = _seam("right")
    bl = next(p for p in own_l if is_boss(p["part"]))
    br_ = next(p for p in own_r if is_boss(p["part"]))
    note_lines(tv, [f"볼(x{kit.FR(*EP['left']['cheek'][:2])} / x{kit.FR(*EP['right']['cheek'][:2])})은 끝 부속 프레임과 한 몸 출력, 볼 윗면 z{F2(chz)} = 윗판 윗면 (S18). "
                    f"윗판은 볼 위까지 이어짐. 레일·손나사·탭 강철 판 없음 (r4).",
                    f"C8 밸런스 블록은 좁혀(x{kit.FR(c8b[0], c8b[1])}) 봉 양 끝에 받침 둘. r4.2: 끝 부속 쐐기는 건반마다 자기 1 N 정착 바닥에 평행한 자기 면(설계 틈, 동역학과 같은 면)으로 출력 (마지막 칸, P17); "
                    "‘모듈 쐐기라면’ 칸은 모듈 쐐기를 그대로 쓸 때의 1 N 강철–패드 면 차 (metrics gap_to_face).",
                    f"도브테일 (D09, 모듈과 같은 뿌리 {F(dns('D09')[0])}·끝 {F(dns('D09')[1])}·깊이 {F(dns('D09')[2])}): 왼쪽 부속 오른쪽 끝에 수(x{F(dn('A02'))}~{F(dn('A02') + dns('D09')[2])}, 모듈 O1의 암 홈으로), 오른쪽 부속 왼쪽 끝에 암 홈(x0~{F(dns('D09')[2])}, 모듈 O7의 수 = 가상선).",
                    f"  움직이는 부품과 최소 틈 (쉼·딥·ff·over, 모델 도브테일 구역 y{F(fz[0])}~{F(fz[1])} × z{F(fz[2])}~{F(fz[3])}): 왼쪽 뒤 {F2(cl[0][0])} ({cl[0][1][4:]} {cl[0][2]}) · 앞 {F2(cl[1][0])} / 오른쪽 뒤 {F2(cl[2][0])} ({cl[2][1][4:]} {cl[2][2]}) · 앞 {F2(cl[3][0])} — 모듈 이음: metrics clear.dovetail_min {F2(M['clear']['dovetail_min'])} (D09).",
                    f"  이음 쪽 핀 보스는 한쪽만 (왼쪽 x{kit.FR(*bl['x'][:2])}, 오른쪽 x{kit.FR(*br_['x'][:2])}): 이웃 모듈 끝 핀·보스(가상선)와 x 틈 {F2(sg_l)} / {F2(sg_r)} = 모듈 사이 이음 {F2(M['clear']['fixed_fixed']['seam_gap_end_fins'])} (metrics seam_gap_end_fins).",
                    f"실선 채움 = z{F(R.plan_cut_z()[0])} 평면(도면 3과 같음), 보라 가상선 = 윗판·패드 바·레일·립·패드, 파란 점선 = 가려진 블록·빔·캡스턴·자석·센서 바. "
                    f"뒷벽 스프링 다리 홈 (흰 칸, P18): 왼쪽 {len(EP['left'].get('spring_grooves', []))}, 오른쪽 {len(EP['right'].get('spring_grooves', []))} — 모듈과 같은 보스 {F(SOL['spring']['boss'][0])}·홈 {F(SOL['spring']['groove'][3])}×{F(SOL['spring']['groove'][4])} (r4.5), "
                    f"레버 허브의 스프링 주머니 Ø{F(SOL['spring']['pocket'][0])}·가둠 홈·넣는 슬롯·긴 다리 창도 모듈과 같음 (미스미 {SOL['spring']['part']}, 짧은 다리 {F(R.short_leg_len())});",
                    f"  홈·보스는 {R.spring_txt()['dx']} 가운데, 입구 모따기 (r4.5 고침).",
                    f"r4.5 회로 2차: 왼쪽 부속 바닥판은 한 조각 x{rg_(*EF_['pieces'][0][:2])} × y{rg_(*EF_['pieces'][0][2:])} (A02) — 모듈 기판 밑 바닥 구멍이 끝 부속으로 새어 생긴 틈 "
                    f"x{rg_(*CR_['el_floor']['r45c_gap'][0][:2])} × y{rg_(*CR_['el_floor']['r45c_gap'][0][2:])}을 없앰 (구멍은 모듈에만).",
                    f"  끝 부속 센서 바 (왼쪽 x{rg_(*CR_['ledge']['ends']['left']['bar'])}, 오른쪽 x{rg_(*CR_['ledge']['ends']['right']['bar'])})는 오른쪽 턱 없이 왼쪽 끝 M3×10 2개(받침 기둥) + 리브로 잡음 (P36); "
                    f"오른쪽 부속 이음 쪽 가상선 = 이웃 모듈 O7의 센서 바 오른쪽 턱 (립 + 기둥), 기둥 ↔ ER 받침 기둥 {F2(CR_['ledge']['end_part_ER'][0])}."],
               8.0, -26 - (len(rows) + 1) * 18 - 16, line_px=16, size_px=10.5)
    tv.v0 = min(tv.v0, -26 - (len(rows) + 1) * 18 - 16 - 10 * 16 - 6)
    bl_, wl_ = ep_bar_bottom(EP["left"], "왼쪽 패드 바 (A0·A#0·B0) — 밑에서 봄, 레일·립 가상선")
    br_, wr_ = ep_bar_bottom(EP["right"], "오른쪽 패드 바 (C8) — 밑에서 봄")
    rows_ = [panels, xzs, rib_xz, [lead_yz[0]], [lead_yz[1]], [bl_, br_], [tv]]
    base = os.path.join(OUT, "d10_end_parts")
    ch_l, ch_r = EP["left"]["cheek"], EP["right"]["cheek"]
    page(rows_, base, f"도면 10. 끝 부속 평면 — 왼쪽 A0·A#0·B0 ({F(dn('A02'))} + 볼 쪽 {F(-ch_l[0])}), 오른쪽 C8 ({F(dns('A03', 'ref')[1])} + 볼 쪽 {F(ch_r[1] - dns('A03', 'ref')[1])})",
         "왼쪽: x = 0 A0 왼쪽 경계 (전체 좌표와 같음) · 오른쪽: 로컬 x = 0 C8 왼쪽 경계 · y = 0 백건 앞끝 · 단위 mm · 숫자 = geometry.json end_parts (괄호 = 치수표 번호)")
    rec(10, base, "끝 부속 (왼쪽 A0·A#0·B0, 오른쪽 C8) 평면",
        f"끝 부속 두 개의 평면(모듈과 같은 높이에서 잘라 위에서 봄): 건반·레버(모듈과 같은 캐리어+강철+스프링)·핀·보스·밸런스 레일·가림판 띠·볼(x{F(ch_l[0])}~{F(ch_l[1])} / {F(ch_r[0])}~{F(ch_r[1])}), "
        "윗판·패드 바·레일·패드는 가상선. 위는 레버·핀·패드 바·레일 x, 아래는 폭. 이음 쪽에 도브테일(D09: 왼쪽 수, 오른쪽 암 홈)과 이웃 모듈 끝 핀·보스(가상선). "
        f"가운데 줄은 패드 줄 가로 단면(볼·윗판·레일·패드 바·패드), 그 아래 끝 패드 바 두 개를 밑에서 본 그림(전체 폭 {F2(wl_)} / {F2(wr_)}, 잎 창·잎 혀·쐐기·레일 립), "
        "아래 표는 건반별 레버 x·캡스턴 y·DW/UW·자기 쐐기. r4: 볼 위 손나사·탭 강철 판·레일 없음. "
        "r4.2: 건반마다 자기 쐐기 면, 뒷벽 스프링 다리 홈(왼쪽 3·오른쪽 1)·센서 바(숨은선)를 그림. "
        f"r4.4 (A02·A03): 센서 기판 EL x{F(G['circuit_r44']['ends']['left']['board'][0])}~{F(G['circuit_r44']['ends']['left']['board'][1])} / ER x{F(G['circuit_r44']['ends']['right']['board'][0])}~{F(G['circuit_r44']['ends']['right']['board'][1])}과 받침 기둥·리브(뒤 리브 틈 왼쪽 x{F(G['circuit_r44']['ends']['left']['gap'][0])}~{F(G['circuit_r44']['ends']['left']['gap'][1])}, 오른쪽 x{F(G['circuit_r44']['ends']['right']['gap'][0])}~{F(G['circuit_r44']['ends']['right']['gap'][1])}), "
        "리드 패드·아랫면 선·바닥 리드 길(굵은 회색), 레일 밑 차선 z5~10과 뒷벽 홈 z5~12(숨은선) — 평면 아래 가로 단면(패드 줄)과 리드 가운데 측면 단면에 치수. 레버 봉·구멍·마개는 geometry 부품(D18). "
        f"r4.4 고침 2b: 캐리어 옆벽 0.7·위 립 0.9·MS 폴리머 접착, 밸런스 레일 블록 밑 포켓 (모듈과 같음). "
        f"r4.5: 스프링 홈 {F(SOL['spring']['groove'][3])}×{F(SOL['spring']['groove'][4])}·보스 {F(SOL['spring']['boss'][0])}, 긴 다리는 레버 x +{F2(sum(R.spring_parts('D')[2]['x']) / 2 - SOL['levers']['D'])}에서 곧게 (미스미 {SOL['spring']['part']}); "
        f"r4.5 고침: 홈·보스 = {R.spring_txt()['dx']} 가운데(긴 다리 x), 입구 0.5×45° 모따기, 허브 가둠 홈 (짧은 다리 {F(R.short_leg_len())}). "
        f"r4.5 회로 2차: 왼쪽 부속 바닥판 한 조각 x{rg_(*EF_['pieces'][0][:2])} × y{rg_(*EF_['pieces'][0][2:])} (모듈 기판 구멍이 새어 생긴 틈 x{rg_(*CR_['el_floor']['r45c_gap'][0][:2])} × y{rg_(*CR_['el_floor']['r45c_gap'][0][2:])} 없앰, A02); "
        f"끝 부속 센서 바는 턱 없이 왼쪽 M3×10 2개 + 리브 (P36), 오른쪽 부속 이음 쪽에 이웃 모듈의 센서 바 오른쪽 턱 (가상선, 받침 기둥과 {F2(CR_['ledge']['end_part_ER'][0])}).")


# ================================================================ sheet 11: overall layout (side + plan + spare-key bay)
def v3a(tag, i):
    """i-th number of the v3 layout table row 'tag' (context/v3_extract.txt)."""
    pats = {"A06": r"A06 스피커 상자 외형\(폭\)", "A16": r"A16 가운데 유닛 외형\(길이\)", "A07": r"A07 CU 칸\(가운데 유닛 안\)",
            "A13": r"A13 케이블 통로\(뒷바 아래 앞쪽\)", "A15": r"A15 뒷바 띄움 높이", "A10": r"A10 전체 깊이", "A14": r"A14 뒷바 깊이",
            "A17": r"A17 건반 보관함 안치수\(길이\)", "A04": r"A04 오른쪽 끝 부속", "A12": r"A12 방진 브래킷"}
    return v3n(pats[tag], i)


def sheet_layout():
    D = dns("A05")[0]
    Dtot = dns("A05")[1]
    gap = v3a("A10", 4)
    yb0, yb1 = v3a("A14", 1), v3a("A14", 2)
    zb0 = v3a("A15", 0)
    cu_top = dns("A06")[2]
    sp_top = dns("A06")[4]
    ch0, ch1 = v3a("A13", 1), v3a("A13", 2)
    ch_z = v3a("A13", 4)
    feet, shim = v3a("A15", 1), v3a("A15", 2)
    # ------------------------------------------------ A. side section (x = D balance pin) + rear bar
    xsec = pcirc("key D balance pin")[0]
    U0s = -80.0
    v = View(U0s, -48.0, 500.0, 246.0, px_width=1480, pad_px=6)
    P = pids(v)
    # heights first (extension lines pass under the parts drawn next): rear-bar heights on the right of the bar,
    # module heights on a column in front of the module (their lines never cross the rear bar)
    v.line(0.0, 0.0, yb1, 0.0, cls="vis")           # desk surface z0 (reference of every z)
    zf = [(0.0, yb1, "책상"), (feet, yb1 - 4.0, f"고무발 {F(feet)}"), (zb0, yb1, f"뒷바 밑 = 고무발 + 받침 {F(shim)} (A15)"),
          (cu_top, yb1, "가운데 유닛 위 (A06)"), (sp_top, yb1, "스피커 파트 위 (A06)")]
    ordz(v, zf, yb1 + 6.0, gap_px=13, label_px=10)
    plate = fpart("top plate (ledge + bridge)")
    zfm = [(dns("S02")[0], 0.0, "백건 윗면 (S02)"), (dn("S18"), bbox(pts(plate))[0], "윗판 윗면 = 모듈 맨 위 (S18)")]
    ordz(v, zfm, -6.0, side="left", gap_px=13, label_px=10)
    side_scene(v, P, "key D", "lever D", xsec, False, press=False, beyond=False, marks=False, sensor=True)
    # rear bar (v3, R26-R29): speaker part outline (ends only) and centre unit, raised on feet; cable channel under the front
    v.poly(rect(yb0, yb1, zb0, sp_top), cls="phan")
    hpoly(v, rect(yb0, yb1, zb0, cu_top), "m-wood", None)
    v.poly(rect(ch0, ch1, 0.0, ch_z), cls="zone")
    # rubber feet (v3 A15: foot 18 + printed shim 4).  v3 gives only the height; the footprint is drawn square with
    # the same 18.  Rows: just behind the cable passage (A13 y215~258) and at the rear edge, so the passage stays clear;
    # x = both ends of each box (speaker L / centre unit / speaker R, plan below, hidden lines).
    fw = feet
    foot_y = [(ch1, ch1 + fw), (yb1 - fw, yb1)]
    for a_, b_ in foot_y:
        v.poly(rect(a_, b_, 0.0, feet), cls="m-print2")
        v.poly(rect(a_, b_, feet, feet + shim), cls="m-print")
    ue = bbox(pts(usb_env()))
    v.poly(rect(ue[0], ue[1], ue[2], ue[3]), cls="env")
    # r4.4 / fix 2b (P23 / P27 / P35): the control board zone beside the D section (x47.25~117.25, outside the cut) and the
    # 16-core ribbon under the board, as envelopes; the board sits in the floor hatch, the plug face at y196.8 (P24)
    cbb = bbox(pts(fpart("control board")))
    ccb = bbox(pts(fparts("board components (<= z20)")[1]))
    rbb = bbox(pts(fparts("board part: J301 16-core ribbon under the board")[0]))
    v.poly(rect(cbb[0], cbb[1], cbb[2], cbb[3]), cls="env")
    v.poly(rect(ccb[0], ccb[1], ccb[2], ccb[3]), cls="env")
    v.poly(rect(rbb[0], rbb[1], rbb[2], rbb[3]), cls="env")
    v.text((yb0 + yb1) / 2, (zb0 + cu_top) / 2 + 6.0, "가운데 유닛 (건반 보관함 · CU 칸 · 보조배터리 칸)", cls="tx", size_px=11)
    v.text((yb0 + yb1) / 2, (zb0 + cu_top) / 2 - 8.0, f"v3 A16 · z{F(zb0)}~{F(cu_top)}", cls="tx-s", size_px=10)
    v.text((yb0 + yb1) / 2, sp_top - 14.0, f"스피커 파트 윤곽 (양 끝만, z{F(zb0)}~{F(sp_top)}, v3 A06)", cls="tx", size_px=10.5)
    leader_to(v, (foot_y[1][0] + foot_y[1][1]) / 2, feet / 2, yb1 + 8.0, -10.0, f"고무발 {F(fw)} + 받침 {F(shim)} (A15)", size_px=9.5)
    v.text(yb1 + 8.0 + v.px(7.5), -10.0 - v.px(13), f"y{F(foot_y[0][0])}~{F(foot_y[0][1])} · {F(foot_y[1][0])}~{F(foot_y[1][1])} (통로 뒤)",
           cls="lt", anchor="start", size_px=9.5)
    v.dim_h(0.0, D, -16.0, text=f"{F(D)} 건반 모듈 (A05)", ext_from=(3.0, 3.0), size_px=10.5)
    v.dim_h(D, yb0, -16.0, text=f"{F(gap)}", ext_from=(3.0, zb0), size_px=10.5)
    v.dim_h(yb0, yb1, -16.0, text=f"{F(yb1 - yb0)} 뒷바 (v3 A14)", ext_from=(zb0, zb0), size_px=10.5)
    v.dim_h(0.0, Dtot, -32.0, text=f"{F(Dtot)} 전체 깊이 (A05)", ext_from=(-16.0, -16.0), size_px=11)
    v.dim_h(ch0, ch1, -4.5, text=f"케이블 통로 {F(ch1 - ch0)}×{F(ch_z)} (A13)", size_px=9.5, tpos="right")
    rw = bbox(pts(fparts("rear wall")[0]))
    leader_to(v, ue[1] - 1.0, (ue[2] + ue[3]) / 2, 196.0, -7.0, f"USB-C 플러그 면 y{F2(ue[0])} (x{F2(ppoly('USB plug')[0][0])}~{F2(ppoly('USB plug')[1][0])}, 단면 밖) → 통로에서 굽음", anchor="end", size_px=9.5)
    leader_to(v, cbb[0] + 12.0, cbb[3], 0.0, 132.0,
              f"제어 기판 y{F2(cbb[0])}~{F2(cbb[1])} z{F2(cbb[2])}~{F2(cbb[3])} + 부품 ≤ z{F(ccb[3])} (x{F2(fpart('control board')['x'][0])}~, 단면 밖; 바닥 구멍으로 밑에서 넣음, P23·P35)",
              size_px=9.5)
    leader_to(v, (rbb[0] + rbb[1]) / 2, rbb[2], 0.0, 124.0, f"기판 밑 16심 리본 z{F(rbb[2])}~{F(rbb[3])} (P27)", size_px=9.5)
    leader_to(v, rw[1], 62.0, 176.0, 116.0, f"뒷벽 뒤 y{F2(rw[1])} ↔ 뒷바 틈 {F2(yb0 - rw[1])}", anchor="end", size_px=10)
    leader_to(v, 100.0, dns("S02")[0], 60.0, 110.0, f"건반 모듈 (단면 x = {F2(xsec)}, 백건 D; 도면 1)", size_px=10)
    a06 = dns("A06")
    s18n = dns("S18", "note")        # [3, 59, 3, 78.0, 80.7]
    note_lines(v, [f"모듈 맨 위 = 윗판 윗면 z{F2(a06[0])} (그 위에 아무것도 없음) < 가운데 유닛 z{F(a06[2])} < 스피커 z{F(a06[4])} → 모듈이 뒷바보다 낮다 (A06).",
                   f"v3 z{F(s18n[1])}보다 높고 r3 커버 z{F(s18n[3])}·손나사 머리 z{F(s18n[4])}보다 낮다: 윗판이 업스톱 레일과 먼지 커버를 겸한다 (S18)."],
               U0s + 2.0, 238.0, line_px=15, size_px=10.5)
    scalebar(v, 380.0, -44.0, 50)
    # ------------------------------------------------ B. plan overview 1254 x 410
    A01 = dns("A01")
    a04 = dns("A04")
    ep = G["end_parts"]
    xL0, xR1 = ep["left"]["cheek"][0], v3a("A04", 2)
    pv = View(-60.0, -84.0, 1290.0, 440.0, px_width=1480, pad_px=6)
    Pp = pids(pv)
    for k in range(1, 8):
        x0 = a04[0] + a04[1] * (k - 1)
        pv.rect(x0, 0.0, dn("P01"), D, cls="faintfill")
        for nm in WHITE:
            pv.poly([(x0 + q[0], q[1]) for q in ppoly(f"key {nm} body")], cls="m-key")
        for nm in BLACK:
            pv.poly([(x0 + q[0], q[1]) for q in ppoly(f"key {nm} body")], cls="m-black")
        # r4.4: the module's control board (P23) and its USB-C plug (P24, face y196.8) running on into the cable passage
        for q_ in (ppoly("control board"), ppoly("USB plug")):
            pv.poly([(x0 + t[0], t[1]) for t in q_], cls="env")
        # r4.5 fix: module name drawn after the board / plug outlines, with a white halo (the dashes struck it through)
        kit.halo_text(pv, x0 + dn("P01") / 2, D - 20.0, f"O{k}", cls="ttl", size_px=12)
    for side, xo in (("left", 0.0), ("right", a04[0] + a04[1] * 7)):
        E = ep[side]
        c0, c1 = E["cheek"]
        pv.rect(xo + c0, 0.0, c1 - c0, D, cls="m-print")
        wid = dn("A02") if side == "left" else dns("A03", "ref")[1]
        pv.rect(xo, 0.0, wid, D, cls="faintfill")
        keys, _ = ep_bodies(E["parts"])
        for kk in keys:
            kp = [p for p in E["parts"] if p["body"] == kk]
            black = "#" in kk
            top = [rect(xo + p["x"][0], xo + p["x"][1], bb_pose(p)[0], bb_pose(p)[1]) for p in kp
                   if p["part"] in (("skin", "wall L low", "wall R low") if black else ("skin head", "skin tail"))]
            fill_rings(pv, union_rings(top, res=0.25), "m-black" if black else "m-key")
    pv.text(ep["left"]["cheek"][0] / 2 + dn("A02") / 2, D - 20.0, "L", cls="ttl", size_px=12)
    pv.text(a04[0] + a04[1] * 7 + dns("A03", "ref")[1] / 2, D - 20.0, "R", cls="ttl", size_px=12)
    x_spl, x_sp1 = v3a("A06", 1), v3a("A06", 2)
    x_spr0, x_spr1 = v3a("A06", 3), v3a("A06", 4)
    x_cu0, x_cu1 = v3a("A07", 1), v3a("A07", 2)
    pv.rect(x_spl, yb0, x_sp1 - x_spl, yb1 - yb0, cls="spk")
    pv.rect(x_spr0, yb0, x_spr1 - x_spr0, yb1 - yb0, cls="spk")
    hpoly(pv, rect(x_sp1, x_spr0, yb0, yb1), "m-wood")
    pv.rect(x_cu0, yb0, x_cu1 - x_cu0, yb1 - yb0, cls="m-pcb")
    pv.poly(rect(x_spl, x_spr1, ch0, ch1), cls="zone")
    pv.text((x_spl + x_sp1) / 2, (yb0 + yb1) / 2, "스피커 L", cls="tx", size_px=11)
    pv.text((x_spr0 + x_spr1) / 2, (yb0 + yb1) / 2, "스피커 R", cls="tx", size_px=11)
    pv.text((x_cu0 + x_cu1) / 2, (yb0 + yb1) / 2, "② CU 칸 (v3 A07)", cls="tx", size_px=11)
    for bx0, bx1 in ((x_spl, x_sp1), (x_sp1, x_spr0), (x_spr0, x_spr1)):     # rubber feet (hidden, under the boxes)
        for fx0 in (bx0, bx1 - fw):
            for a_, b_ in foot_y:
                pv.poly(rect(fx0, fx0 + fw, a_, b_), cls="hid")
    pv.text(x_spl, yb1 + 12.0, f"파란 점선 네모 = 고무발 (상자마다 x 양 끝, y{F(foot_y[0][0])}~{F(foot_y[0][1])} · {F(foot_y[1][0])}~{F(foot_y[1][1])}) — 케이블 통로 y{F(ch0)}~{F(ch1)} 밖",
            cls="tx-s", anchor="start", size_px=10)
    pv.text((x_sp1 + x_cu0) / 2, (yb0 + yb1) / 2 + 12.0, "① 건반 보관함 (R29)", cls="tx", size_px=11)
    pv.text((x_sp1 + x_cu0) / 2, (yb0 + yb1) / 2 - 14.0, f"안치수 {' × '.join(F(q) for q in dns('A08'))} (A08)", cls="tx-s", size_px=10)
    pv.text((x_cu1 + x_spr0) / 2, (yb0 + yb1) / 2, "③ 보조배터리 칸", cls="tx", size_px=11)
    pv.text((x_spl + x_spr1) / 2, (ch0 + ch1) / 2 - 4.0, f"케이블 통로 y{F(ch0)}~{F(ch1)} (뒷바 아래 앞쪽, v3 A13)", cls="tx-s", size_px=10)
    pv.dim_h(xL0, xR1, -22.0, text=f"{F(A01[1])} 전체 폭, 볼 포함 (A01)", ext_from=(0.0, 0.0), size_px=10.5)
    pv.dim_h(0.0, A01[0], -46.0, text=f"{F(A01[0])} 88건반 (A01)", ext_from=(0.0, 0.0), size_px=10.5)
    pv.dim_h(a04[0], a04[0] + a04[1], -68.0, text=f"{F(dn('P01'))} 모듈 (P01)", ext_from=(0.0, 0.0), size_px=10)
    pv.dim_h(xL0, a04[0], -68.0, text=f"{F(a04[0] - xL0)}", ext_from=(0.0, 0.0), size_px=10)
    pv.dim_h(a04[0] + a04[1] * 7, xR1, -68.0, text=f"{F(xR1 - a04[0] - a04[1] * 7)}", ext_from=(0.0, 0.0), size_px=10)
    pv.dim_v(0.0, D, -40.0, text=f"{F(D)}", ext_from=(xL0, xL0), size_px=10.5)
    pv.dim_v(D, yb0, -40.0, text=f"{F(gap)}", ext_from=(xL0, xL0), size_px=10.5, tpos="left")
    pv.dim_v(yb0, yb1, -40.0, text=f"{F(yb1 - yb0)}", ext_from=(xL0, xL0), size_px=10.5)
    pv.dim_v(0.0, Dtot, 1262.0, text=f"{F(Dtot)} (A05)", ext_from=(xR1, xR1), left=False, size_px=10.5)
    scalebar(pv, 880.0, -80.0, 100)
    # ------------------------------------------------ C. spare-key bay (R29): plan + section
    sb = M["spare_bay"]
    bx, by, bz = dns("A08")
    l1, l2 = sb["layer1"], sb["layer2"]
    SB = 1.92                                    # px/mm of the bay views: plan + section side by side, page <= 1536 px
    bv = View(-18.0, -46.0, 360.0, 200.0, px_width=378 * SB, pad_px=6)
    hpoly(bv, rect(0.0, bx, 0.0, by), "m-wood")
    bv.rect(0.0, 0.0, bx, by, cls="faintfill")
    kz, dv_, sz = dns("A08", "ref")
    m1 = (kz - l1[0]) / 2
    bv.rect(m1, 0.0, l1[0], l1[1], cls="phan")
    hpoly(bv, rect(kz, kz + dv_, 0.0, by), "m-wood")
    bv.rect(kz + dv_, 0.0, sz, by, cls="phan")
    # layer 1: the seven white keys of a module, upside down, heads alternating, packed across the bay depth
    heads = [(nm, ppoly(f"key {nm} body"), ppoly(f"key {nm} beam + tail")) for nm in WHITE]
    hw = dn("P03")
    g1 = (l1[1] - len(heads) * hw) / (len(heads) - 1)
    for i, (nm, q, qt) in enumerate(heads):
        hx0 = min(t[0] for t in q)
        off = i * (hw + g1)
        fill_rings(bv, union_rings([[(m1 + t[1], off + (t[0] - hx0)) for t in q], [(m1 + t[1], off + (t[0] - hx0)) for t in qt]], res=0.1), "m-key")
        bv.text(-4.0, off + hw / 2 - 1.5, nm, cls="tx", anchor="end", size_px=9)
    bv.text(kz / 2, by + 6.0, f"1층: 백건 C~B {len(WHITE)}개, 윗면이 아래 ({' × '.join(F(q) for q in l1)}, metrics)", cls="tx", size_px=10)
    sz0 = kz + dv_
    bv.text(sz0 + sz / 2, by / 2 + 16.0, "옆 칸", cls="ttl", size_px=11)
    a8r = dns("A08", "ref")          # [201.3, 1.2, 136.3] = 건반 칸 + 칸막이 + 옆 칸
    bv.text(bx / 2, -40.0, f"건반 칸 {F(a8r[0])} (여유 {F((a8r[0] - l1[0]) / 2)} + 백건 {F(l1[0])} + 여유 {F((a8r[0] - l1[0]) / 2)}) + 칸막이 {F(a8r[1])} + 옆 칸 {F(a8r[2])} = {F(bx)} (A08)",
            cls="tx-s", size_px=9.5)
    # r4.4: side-compartment contents = the spares of parts_list.json (r4.1: no spare carriers / pad bars — printed per position)
    items = [f"강철 블록 {pl_spare('강철 블록')} (SS400 9×19×40)",
             f"Ø4 봉 {pl_spare('건반 봉 SUS304') + pl_spare('레버 봉 SUS304')} (건반 봉 {pl_spare('건반 봉 SUS304')} + 레버 봉 {pl_spare('레버 봉 SUS304')}, 같은 봉)",
             f"비틀림 스프링 {pl_spare('비틀림')} · 업스톱 패드 {pl_spare('업스톱 패드')}",
             f"밸런스 핀 {pl_spare('밸런스 핀')} · 캡스턴 + 너트 {pl_spare('캡스턴')} · PET 심 (D16)",
             "작은 부품 통 (펠트·천)"]
    for j, t in enumerate(items):
        bv.text(sz0 + 4.0, by / 2 + 2.0 - j * 11.0, t, cls="tx", anchor="start", size_px=9.5)
    note_lines(bv, ["캐리어·패드 바는 예비 없음:", "위치별 파일로 필요할 때 출력 (parts_list)"], sz0 + 4.0, by / 2 + 2.0 - len(items) * 11.0 - 4.0,
               line_px=13, size_px=9, cls="tx-s")
    bv.dim_h(0.0, bx, -12.0, text=f"{F(bx)} (A08)", ext_from=(0.0, 0.0), size_px=10)
    bv.dim_h(0.0, kz, -26.0, text=f"{F(kz)} 건반 칸", ext_from=(0.0, 0.0), size_px=10)
    bv.dim_h(sz0, bx, -26.0, text=f"{F(sz)} 옆 칸", ext_from=(0.0, 0.0), size_px=10)
    bv.dim_v(0.0, by, bx + 8.0, text=f"{F(by)}", ext_from=(bx, bx), left=False, size_px=10)
    panel_title(bv, -17.0, 200.0 - bv.px(12), "건반 보관함 (R29) 평면 — 가운데 유닛 ① 칸", size_px=11.5)
    # section
    sv = View(-18.0, -30.0, 360.0, 100.0, px_width=378 * SB, pad_px=6)
    hpoly(sv, rect(0.0, bx, 0.0, bz), "m-wood")
    sv.rect(0.0, 0.0, bx, bz, cls="faintfill")
    sv.rect(m1, 0.0, l1[0], l1[2], cls="m-key")
    sv.rect(m1, l1[2], l2[0], l2[2], cls="kbt")
    hpoly(sv, rect(kz, kz + dv_, 0.0, bz), "m-wood")
    sv.rect(sz0, 0.0, sz, bz, cls="phan")
    sv.text(m1 + l1[0] / 2, l1[2] / 2 - 2.0, f"1층 백건 {len(WHITE)}", cls="tx", size_px=10)
    sv.text(m1 + l2[0] / 2, l1[2] + l2[2] / 2 - 2.0, f"2층 흑건 {len(BLACK)} + A#0 · 백건 A0·B0·C8", cls="inv", size_px=10)
    sv.text(sz0 + sz / 2, bz / 2, "옆 칸", cls="tx", size_px=10)
    sv.dim_v(0.0, l1[2], -6.0, text=F(l1[2]), ext_from=(0.0, 0.0), size_px=9.5)
    sv.dim_v(l1[2], sb["stack"], -6.0, text=F(l2[2]), ext_from=(0.0, 0.0), size_px=9.5)
    sv.dim_v(0.0, bz, bx + 8.0, text=f"{F(bz)}", ext_from=(bx, bx), left=False, size_px=10)
    sv.dim_h(m1, m1 + l2[0], sb["stack"] + 6.0, text=f"2층 {' × '.join(F(q) for q in l2)}", ext_from=(sb["stack"], sb["stack"]), size_px=9.5)
    panel_title(sv, -17.0, 100.0 - sv.px(12), f"보관함 단면 — 두 층 {F(sb['stack'])} / 안 높이 {F(bz)} · 합계 약 {F(sb['mass_kg'], 2)} kg", size_px=11.5)
    rows = [[v], [pv], [bv, sv]]
    base = os.path.join(OUT, "d11_overall_layout")
    page(rows, base, f"도면 11. 전체 배치 — 모듈 + 뒷바 측면, {F(A01[1])} × {F(Dtot)} 평면, 예비 건반 보관함",
         "측면: 모듈 단면(백건 D)과 뒷바 윤곽(v3 R26~R29 표: context/v3_extract.txt) · 평면: A0 왼쪽 경계 x = 0 · 단위 mm · 숫자 = geometry.json·metrics.json·v3 표 (괄호 = 치수표 번호)")
    rec(11, base, "전체 배치 측면",
        f"모듈 단면(프레임 {F(D)})과 틈 {F(gap)}, 뒷바 {F(yb1 - yb0)}(가운데 유닛 z{F(zb0)}~{F(cu_top)}, 양 끝 스피커 파트 z{F(zb0)}~{F(sp_top)} 윤곽, 아래 케이블 통로)로 전체 깊이 {F(Dtot)}. "
        f"모듈 맨 위(윗판 윗면) z{F2(dn('S18'))}가 뒷바보다 낮음(r3 커버·손나사 머리 없음). 가운데는 {F(A01[1])} × {F(Dtot)} 전체 평면(끝 부속 + 모듈 7 + 뒷바 칸), 아래는 예비 건반 보관함의 층 배치. "
        f"r4.3: USB-C 플러그 z{F2(ue[2])}~{F2(ue[3])}(RP2040-Zero 핀 헤더 위), 케이블 통로 안; r4.4: 플러그 면 y{F2(ue[0])}, 측면에 제어 기판 구역(기판·부품 ≤ z20, 단면 밖)과 기판 밑 16심 리본, 평면의 모듈마다 기판·플러그(초록 점선); "
        f"r4.4 고침 2b: 기판은 모듈 바닥 구멍으로 밑에서 넣음. 보관함 옆 칸 = parts_list 예비(강철 블록·Ø4 봉·스프링·패드·핀·캡스턴), 캐리어·패드 바는 예비 없이 위치별 출력.")


# ================================================================ sheet 12: taking one key out (white D; black notes)
SKIP_TOP = ("up-stop pad", "pad wedge", "pad bar grip", "cover curtain")


def skip_bar(n):
    return n == "pad bar"


def removal_tfs():
    """key / lever transforms of the removal path, exactly as model_v4.removal_path (numbers from metrics.json)."""
    rw = M["removal"]["white"]
    rp = M["removal_paths"]["D"]
    pad, kp1 = tuple(rw["pad"]), tuple(rw["kp1"])
    ph1, ph2 = rw["ph1"], rw["ph2"]
    at = math.radians(rp["tilt_deg"])
    Lout = rp["L_out"]
    lifted = lambda p: rot(rot(p, pad, -ph1), kp1, ph2)
    slid = lambda p: (lifted(p)[0] - rw["slide_forward"], lifted(p)[1])
    pad_now = slid(pad)
    tilted = lambda p: rot(slid(p), pad_now, -at)
    out = lambda p: (tilted(p)[0] - Lout * math.cos(at), tilted(p)[1] + Lout * math.sin(at))
    return dict(lifted=lifted, slid=slid, tilted=tilted, out=out, rw=rw, rp=rp, pad=pad, kp1=kp1, pad_now=pad_now,
                b_up=math.radians(rw["lever_angle_needed_deg"]), b_hold=math.radians(rp["b_hold_deg"]),
                b_drop=math.radians(M["lever_drop"]["D"]["angle_deg"]))


def key_outline(v, tf, cls):
    stroke_rings(v, union_rings([[tf(t) for t in pts(p)] for p in body("key D") if p["part"] not in ("capstan head", "rest felt")], res=0.05), cls)


def onto_ko(n):
    """Korean name of the part a keyless lever lands on (circuit_r44.drop 'onto')."""
    if n.startswith("control-board boss"):
        return "기판 위에 매달린 보스" + (" (위치 핀)" if "locating pin" in n else " (나사)")
    if n.startswith("board part: CD74HC4067"):
        return "4067 모듈"
    if n == "control board":
        return "기판 윗면"
    if n.startswith("board components"):
        return "기판 부품 구역 z20"
    return "바닥판" if n == "floor" else n


def drop_groups(sep=", "):
    """r4.5 circuit 2nd (request 10): where each lever over the control board lands with its key out, grouped by the
    part it lands on (circuit_r45.drop, the same numbers as circuit_r44.drop 'actual'):
    'D#·G# → 매달린 보스 16.75°, E·F → 4067 모듈 13.25°, F#·G → 기판 윗면 24.00° / 23.50°'."""
    D = G["circuit_r45"]["drop"]
    grp = {}
    for nm in G["circuit_r44"]["drop"]:                  # D#, E, F, F#, G, G# (the levers over the board)
        k = onto_ko(D[nm]["onto"]).split(" (")[0]
        grp.setdefault(k, []).append(nm)
    out = []
    for k, names in sorted(grp.items(), key=lambda t: ORDER.index(t[1][0])):
        degs = [D[n]["deg"] for n in names]
        dt_ = F2(degs[0]) if len(set(degs)) == 1 else " / ".join(F2(d) for d in degs)
        out.append(f"{'·'.join(names)} → {k} {dt_}°")
    return sep.join(out)


def drop_panel(nm):
    """r4.4 fix 2b: a lever whose key is out falls about L until it lands (circuit_r44.drop 'actual', from the rest angle
    of metrics.lever_drop): side section at the lever centre x with the frame, the control board and its parts / bosses."""
    dr = G["circuit_r44"]["drop"][nm]
    ld = M["lever_drop"][nm]
    rest = ld["angle_deg"] + ld["drop_deg"]
    b = math.radians(rest - dr["actual"])
    xc = SOL["levers"][nm]
    u0, u1, w0, w1 = 140.0, 214.0, 0.0, 58.0
    v = View(u0, w0 - 9.0, u1, w1, px_width=486, pad_px=4)
    P = pids(v)
    fx = [p for p in fixed() if cut_x(p, xc) and not p["part"].startswith(SKIP_TOP + ("pad bar", "top plate"))]
    fill_rings(v, union_rings([pts(p) for p in fx if is_frame(p["part"])]), "m-print", P["print"])
    for p in void_first(fx):
        n = p["part"]
        if is_frame(n):
            continue
        cls, h = mat_fixed(n)
        if cls == "env":
            v.poly(pts(p), cls="env")
        else:
            hpoly(v, pts(p), cls, P[h] if h else None)
    tf = lambda t: rot(t, L, -b)
    lp = [p for p in body(f"lever {nm}") if cut_x(p, xc)]
    fill_rings(v, union_rings([[tf(t) for t in pts(p, "rigid0")] for p in lp if not p["part"].startswith(("steel", "felt"))]), "m-lever", P["lever"])
    for p in lp:
        if p["part"].startswith("steel"):
            hpoly(v, [tf(t) for t in pts(p, "rigid0")], "m-steel", P["steel"])
        elif p["part"].startswith("felt"):
            v.poly([tf(t) for t in pts(p, "rigid0")], cls="m-felt")
    stroke_rings(v, union_rings([pts(p, "rest") for p in body(f"lever {nm}") if cut_x(p, xc)]), "phan")
    R.pivot_mark(v, L, dn("S11", 0, "note") / 2)
    panel_title(v, u0 + 0.5, w1 - v.px(12), f"{nm} (x{F2(xc)}): 쉼에서 {F2(dr['actual'])}° → {onto_ko(dr['onto'])}", size_px=11)
    # r4.5 fix: the notes go to the free band under the desk line (z < 0), clear of the phantom rest lever that struck
    # them through at the top of the panel; white halo kept as a guard
    kit.halo_text(v, u0 + 0.5, w0 - 9.0 + v.px(20), f"얹히는 힘 {F2(dr['F_rest'])} N · 일반 기준(부품 구역 z20)이면 {F2(dr['generic'])}°", cls="tx-s", anchor="start", size_px=9.5)
    if dr.get("o17"):
        kit.halo_text(v, u0 + 0.5, w0 - 9.0 + v.px(7), f"O1·O7 모듈만: 누운 R301 100k에 {F2(dr['o17'])}°", cls="tx-s", anchor="start", size_px=9.5)
    return v


def sheet_removal():
    T = removal_tfs()
    rw, rp = T["rw"], T["rp"]
    xsec = pcirc("key D balance pin")[0]
    lev_tf = lambda b: (lambda t: rot(t, L, -b))
    ident = lambda t: t
    # r4.5 fix: the long spring leg stays in the rear-wall groove (geometry pose) while the spring is loaded (lever
    # above the free angle); only a lever dropped below the free angle turns it, by the angle past free (results:
    # keyless lever -31.3 deg, free -28.45 (r4.5 fix) -> leg tip still inside the groove mouth)
    b_free = math.radians(SOL["spring"]["free_deg"])
    leg_tf = lambda b: ident if b >= b_free else (lambda t: rot(t, L, -(b - b_free)))
    bar = pts(fpart("pad bar"))
    grip = pts(fpart("pad bar grip"))
    cur = [p for p in fixed() if p["part"] == "cover curtain" and cut_x(p, xsec)][0]
    hook = fpart("cover curtain hook")
    bar_len = bbox(bar)[1] - bbox(bar)[0]
    ld = M["lever_drop"]["D"]
    tab = rw["tab_world"]
    steps = [
        dict(tag="⓪", ktf=ident, prev=None, b=T["b_hold"], pose="rigid0",
             title=f"가림판 띠를 위로 들어내고, 그 핀 칸의 패드 바를 앞 손잡이로 앞으로 뽑는다 → 손톱 턱으로 레버를 윗판까지 들어 {F(rp['b_hold_deg'])}°로 잡는다",
             lines=[f"패드 바를 빼면 그 칸 레버 3개가 자유 (핀 칸마다 1개, P13)",
                    f"레버는 윗판에 닿을 때까지 {F(M['service_swing']['D'], 2)}°까지 올라감",
                    f"손톱 턱을 드는 힘 {F2(rw['F_tab'])} N (D08)",
                    f"빼기에 필요한 각: 백 {F2(rw['lever_angle_needed_deg'])}° · 흑 {F2(M['removal']['black']['lever_angle_needed_deg'])}°"]),
        dict(tag="①", ktf=T["lifted"], prev=ident, b=T["b_hold"], pose="rigid0",
             title="다른 손 손톱을 건반 뒤 윗판 턱 밑에 걸어 위로 당긴다 → 쉼 패드 둘레로 돌다 크로스바가 키퍼에 닿고, 키퍼 둘레로 돌아 노치가 봉 위로",
             lines=[f"당기는 힘 {F(rw['pull_N'], 1)} N (스냅 {F(dns('D15')[1])} N 기준; 반지름 작은 쿠폰이면 {F(rw['pull_N_snap_hi'], 1)} N, D15)",
                    f"앞이 {F(rw['front_rise_to_keeper'], 1)} 올라 키퍼에 닿고, 노치 뒤 입술이 봉 꼭대기 + {F(M['params']['removal_lip_clear'])}",
                    f"캡스턴이 {F2(rw['capstan_rise'])} 올라감 (레버는 이미 들려 있음) · 블록 밑이 핀 위로 {F2(rw['pin_clear'])}",
                    f"최소 틈 {F2(rp['pull_up'][0])} ({rp['pull_up'][1]})"]),
        dict(tag="②", ktf=T["slid"], prev=T["lifted"], b=T["b_hold"], pose="rigid0",
             title=f"당긴 채 앞으로 {F(rw['slide_forward'])} 민다 → 크로스바가 키퍼 훅 앞으로, 노치가 봉 앞으로 빠짐",
             lines=[f"최소 틈 {F2(rp['slide_3mm'][0])} ({rp['slide_3mm'][1]})"]),
        dict(tag="③", ktf=T["tilted"], prev=T["slid"], b=T["b_hold"], pose="rigid0",
             title=f"건반 앞을 쉼 패드 둘레로 {F(rp['tilt_deg'])}° 들어 가이드 탭에서 뺀다 (레버는 {F(rp['b_hold_deg'])}°로 잡은 채)",
             lines=[f"최소 틈 {F2(rp['tilt'][0])} ({rp['tilt'][1]})"]),
        dict(tag="④", ktf=T["out"], prev=T["tilted"], b=T["b_drop"], pose="rigid0",
             title=f"기울인 방향으로 {F(rp['L_out'])} 뽑는다 → 레버를 놓으면 {'바닥판' if ld['onto'] == 'floor' else '기판 부품'} 위에 {F2(ld['F_rest'])} N으로 얹힘 (L 블록 없음)",
             lines=[f"뽑는 동안 최소 틈 {F2(rp['draw_out'][0])} ({rp['draw_out'][1]})",
                    f"레버 D는 쉼에서 {F(ld['drop_deg'], 1)}° 내려가 {'바닥판' if ld['onto'] == 'floor' else '기판 부품'}에 닿음 (metrics lever_drop)",
                    f"스프링 긴 다리는 뒷벽 홈에 남음: 자유각 {F2(SOL['spring']['free_deg'])}°보다 {F2(SOL['spring']['free_deg'] - ld['angle_deg'])}° 더 내려간",
                    f"  만큼만 돌아 끝이 홈 입구 안 {F2(M['leg_in_groove_drop'])} (짧은 다리는 가둠 홈에 갇힌 채)",
                    "기판 위 레버가 얹히는 곳, 쉼에서 내려간 각 (아래 ⑤, circuit_r45.drop):",
                    f"  {', '.join(drop_groups(', ').split(', ')[:2])},",
                    f"  {', '.join(drop_groups(', ').split(', ')[2:])}",
                    "다시 넣을 때는 ⓪처럼 레버를 들고 반대 순서로"]),
    ]
    panels = []
    for st in steps:
        v = View(-64.0, -2.0, 330.0, dn("S18") + 6.0, px_width=1480, pad_px=6)
        P = pids(v)
        side_scene(v, P, "key D", "lever D", xsec, False, press=False, beyond=False, key_tf=st["ktf"], lever_pose=st["pose"],
                   lever_tf=lev_tf(st["b"]), skip_fixed=SKIP_TOP + ("pad bar",), marks=False, sensor=False,
                   spring_leg_tf=leg_tf(st["b"]))
        if st["prev"] is not None:
            key_outline(v, st["prev"], "phan")
        if st["tag"] == "⓪":
            # the pad bar drawn pulled forward by its own length (phantom) and the lifted curtain strip (phantom)
            dy_ = -bar_len
            wq = pts(fpart("pad wedge D"))
            for q_ in (bar, grip, wq):                    # the pad bar in its seat (removed) and pulled out by its length
                v.poly(q_, cls="phan")
            v.poly([(q[0] + dy_, q[1]) for q in bar], cls="phan")
            arrow(v, bbox(bar)[0] - 1.0, bbox(grip)[2] - 2.5, bbox(bar)[0] + dy_ + 6.0, bbox(grip)[2] - 2.5)
            v.text(bbox(bar)[0] + dy_ / 2, max(q[1] for q in bar) + v.px(5), "패드 바를 앞으로 뽑음", cls="tx", size_px=10)
            cq = pts(cur)
            v.poly(cq, cls="phan")
            v.poly(pts(hook), cls="phan")
            arrow(v, bbox(cq)[0] - 2.0, bbox(cq)[2] + 1.0, bbox(cq)[0] - 2.0, bbox(cq)[2] + 9.0)
            v.text(bbox(cq)[0] - 3.0 - v.px(4), bbox(cq)[2] + 2.0, "가림판 띠를 들어냄", cls="tx", anchor="end", size_px=10)
            stroke_rings(v, union_rings([pts(p, "rest") for p in body("lever D")]), "phan")       # rest pose of the lever
            tp = rot(tuple(pts(part("lever D", "fingernail tab"), "rigid0")[0]), L, -T["b_hold"])
            arrow(v, tp[0] - 9.0, tp[1] - 9.0, tp[0] - 0.8, tp[1] - 1.0)
            v.text(tp[0] - 9.5, tp[1] - 9.0 - v.px(4), f"손톱 턱을 듦 ({F2(rw['F_tab'])} N)", cls="tx", anchor="end", size_px=10)
        elif st["tag"] == "①":
            lip = (bbox(pts(part("key D", "skin tail")))[1] - 0.5, dns("S02")[0])
            hp = T["lifted"](lip)
            arrow(v, hp[0], hp[1] + 1.0, hp[0], hp[1] + 9.0)
            v.text(hp[0] - v.px(5), hp[1] + 5.0, "손톱으로 윗판 뒤 턱을 당김", cls="tx", anchor="end", size_px=10)
            f0 = (0.0, dns("S02")[0])
            arrow(v, f0[0] - 6.0, f0[1], f0[0] - 6.0, T["lifted"](f0)[1] + 3.0)
        elif st["tag"] == "②":
            a0 = T["lifted"]((-2.0, 36.0))
            arrow(v, a0[0], a0[1], a0[0] - rw["slide_forward"] - 6.0, a0[1])
        elif st["tag"] == "③":
            c0 = T["slid"]((0.0, dns("S02")[0]))
            c1 = T["tilted"]((0.0, dns("S02")[0]))
            arrow(v, c0[0] - 4.0, c0[1], c1[0] - 4.0, c1[1] + 4.0)
        else:
            c0 = T["tilted"]((150.0, 30.0))
            c1 = T["out"]((150.0, 30.0))
            arrow(v, c0[0], c0[1] + 16.0, c1[0], c1[1] + 16.0)
            stroke_rings(v, union_rings([[rot(t, L, -T["b_hold"]) for t in pts(p, "rigid0")] for p in body("lever D")]), "phan")
        panel_title(v, -63.0, dn("S18") + 6.0 - v.px(14), f"{st['tag']} {st['title']}", size_px=12)
        note_lines(v, st["lines"], 222.0, dn("S18") - 4.0 - v.px(14), line_px=15, size_px=10.5)
        panels.append(v)
    rb = M["removal_paths"]["C#"]
    rbk = M["removal"]["black"]
    nv = View(0, -170, 1480, 0, px_width=1480, pad_px=6)
    note_lines(nv, [f"흑건 빼기: 양옆 백건을 먼저 ①~④로 뺀다 (조립은 흑건 먼저). 그 다음 같은 순서로 하되 앞을 {F(rb['tilt_deg'])}° 든다. 당기는 힘 {F(rbk['pull_N'], 1)} N, 필요한 레버 각 {F2(rbk['lever_angle_needed_deg'])}°.",
                    f"  최소 틈: 당김 {F2(rb['pull_up'][0])} · 밀기 {F2(rb['slide_3mm'][0])} · 기울임 {F2(rb['tilt'][0])} · 뽑기 {F2(rb['draw_out'][0])} ({rb['draw_out'][1]}; C#·F#·A# 모두 검사, metrics removal_paths).",
                    f"넣기: 거꾸로 — 레버를 손톱 턱으로 들고, 꼬리를 레버 밑으로 넣고, 탭에 끼우고, 뒤로 {F(rw['slide_forward'])} 밀어 크로스바를 훅 밑에 둔 뒤 블록 위 윗판을 눌러 스냅 노치를 봉에 끼운다",
                    f"  (빠짐 힘 {F(dns('D15')[0])}~{F(dns('D15')[1])} N, D15) → 레버를 캡스턴 위로 내려놓고, 패드 바를 레일에 밀어 넣고, 가림판 띠를 건다. 도구·나사·다시 조이기 없음.",
                    "레버를 바꿀 때는 모듈을 빼서 레버 봉을 왼쪽 마개 쪽으로 뽑는다 (허브 칼라는 캐리어와 한 몸, 스프링은 레버와 함께 나옴).",
                    "모든 단계는 model_v4.removal_path가 건반·레버·이웃·프레임과 충돌 검사한 경로 그대로 (보라 가상선 = 앞 단계 자세; ⓪ = 쉼 레버, ④ = 잡았던 레버)."],
               6.0, -14.0, line_px=19, size_px=11)
    dn_ = list(G["circuit_r44"]["drop"].keys())               # D#, E, F, F#, G, G# (the levers over the control board)
    drops = [drop_panel(n_) for n_ in dn_]
    dt = View(0, -40, 1480, 0, px_width=1480, pad_px=6)
    panel_title(dt, 6.0, -16.0, f"⑤ 건반을 뺀 레버가 떨어지는 곳 — 기판 위 {len(dn_)}개, 쉼에서: {drop_groups(' · ')} "
                                f"(기판 윗면 z{F2(bbox(pts(fpart('control board')))[3])}; 가상선 = 쉼 레버; circuit_r45.drop)", size_px=12.5)
    rows = [[panels[0]], [panels[1]], [panels[2]], [panels[3]], [panels[4]], [dt], drops[:3], drops[3:], [nv]]
    base = os.path.join(OUT, "d12_key_removal")
    page(rows, base, "도면 12. 건반 하나 빼기 — 백건 D (도구 없이, 레버는 두고 건반만)",
         f"단면 x = {F2(xsec)} · ①~④는 가림판 띠·패드 바(패드·쐐기 포함)를 뺀 상태, 윗판은 그대로 · 보라 가상선 = 앞 단계의 건반·레버 · "
         "숫자 = metrics.json removal / removal_paths / lever_drop (geometry.json과 같은 모델 실행)")
    rec(12, base, "건반 하나 빼기 순서",
        f"백건 D 하나를 도구 없이 빼는 다섯 단계: ⓪ 가림판 띠를 들어내고 그 칸 패드 바를 앞으로 뽑은 뒤 손톱 턱으로 레버를 {F(rp['b_hold_deg'])}°로 듦, "
        f"① 건반 뒤 윗판 턱을 손톱으로 당겨 노치를 봉 위로, ② 앞으로 {F(rw['slide_forward'])} 밀어 크로스바·노치를 뺌, ③ 건반 앞을 {F(rp['tilt_deg'])}° 들어 탭에서 뺌, "
        f"④ {F(rp['L_out'])} 뽑고 레버를 내려놓음(바닥판 위 {F2(ld['F_rest'])} N, L 서비스 블록 없음). "
        f"⑤ 기판 위 레버 {', '.join(G['circuit_r44']['drop'].keys())}는 건반이 빠지면 내려가 얹힘 — {drop_groups(', ')} (쉼에서 내려간 각, 각 레버 중심 단면, circuit_r45.drop; r4.5 회로 2차 10번: D#·G#는 기판 윗면이 아니라 매달린 보스). 각 단계의 최소 틈과 흑건·넣기 순서는 아래 글.")


# ================================================================ sheet 13 (r4.4): lever-rod end plug + printed tools
TGEO = json.load(open(os.path.join(kit.V4, "final", "tools", "tools_geometry.json")))    # r4.4: tools -> drawing 14
TDIM = {d["id"]: d for d in TGEO["dims"]}


def tn(tid, i=0):
    """i-th number of tools_geometry.json dims[tid]['value'] (T01..T29)."""
    v = TDIM[tid]["value"]
    return float(v) if isinstance(v, (int, float)) else nums(v)[i]


def sheet_tools():
    """drawing 13 (r4.4): the lever-rod end plug and the rod ends, drawn from the exported D18 prisms ('lever rod D4',
    'fin boss bore D4.0', 'lever rod end plug'); the printed tools are no longer sketched here — they are drawn with
    real dimensions on drawing 14 (tools_geometry.json), this sheet only lists what each one sets and points there."""
    W = dn("P01")
    rp = dns("P22")                                   # [1.5, 162.9, 161.4, 0.2]
    dn("D18")                                         # cite D18 (rod end geometry)
    rodp, plg = rod_part(), plug_part()
    bores = sorted(bore_parts(), key=lambda p: p["x"][0])
    rod_d = dn("S11", 0, "note")                      # Ø4 rod
    bore = boss_bore()                                # Ø4.0 drilled (printed 3.9)
    bosses = sorted((p for p in fixed() if is_boss(p["part"])), key=lambda p: p["x"][0])
    bL, bR = bosses[0], bosses[-1]
    plug_l = plg["x"][1] - plg["x"][0]
    blind = bores[-1]["x"][1]                         # right end fin: bore blind to here
    wall_t = bR["x"][1] - blind
    play_l = rodp["x"][0] - plg["x"][1]
    play_r = blind - rodp["x"][1]
    RR = G["r44"]["rod"]
    plug = pl_item("레버 봉 끝 마개")
    tools = pl_item("출력 공구")
    # ------------------------------------------------ A. the whole rod through the 5 fin bosses (x-z at y = L)
    So = 8.6
    u0, u1 = -3.0, W + 3.0
    w0, w1 = L[1] - 5.0, L[1] + 5.0
    ov = View(u0, w0 - 118 / So, u1, w1 + 44 / So, px_width=(u1 - u0) * So, pad_px=4)
    Po = pids(ov)
    i0 = clip_begin(ov)
    frame_xz(ov, Po, L[0])
    hpoly(ov, rect(rodp["x"][0], rodp["x"][1], L[1] - rod_d / 2, L[1] + rod_d / 2), "m-steel", Po["steel"])
    ov.cl(u0, L[1], u1, L[1])
    clip_end(ov, i0, u0, u1, w0, w1)
    ov.dim_h(rodp["x"][0], rodp["x"][1], w1 + 1.2, text=f"봉 {F2(rodp['x'][1] - rodp['x'][0])} ± {F(RR['rod_len_tol'])} (P22 · D18)",
             ext_from=(L[1] + rod_d / 2, L[1] + rod_d / 2), size_px=10)
    xf = [(plg["x"][0], L[1] - bore / 2, "마개 면 = 끝 핀 면"), (rodp["x"][0], L[1] - rod_d / 2, "봉 끝")]
    for k, b_ in enumerate(bores[1:-1]):
        xf += [(b_["x"][0], L[1] - bore / 2, f"보스 구멍 {k + 2}"), (b_["x"][1], L[1] - bore / 2, "")]
    xf += [(rodp["x"][1], L[1] - rod_d / 2, "봉 끝"), (blind, L[1] - bore / 2, "막힌 구멍 끝"), (bR["x"][1], w0, "끝 핀 바깥")]
    ordy(ov, xf, w0 - 0.2, gap_px=12.5, label_px=9.5, lo=u0)
    panel_title(ov, u0 + ov.px(3), w1 + 44 / So - ov.px(13),
                f"레버 봉 Ø{F(rod_d)} SUS304 — 핀 {RR['n_bores']}장의 보스 구멍 Ø{F(bore)}을 지남 (y{F2(L[0])} x–z 단면; 레버 허브·칼라는 생략, 도면 4 A-A)", size_px=11.5)
    # ------------------------------------------------ B. rod ends (x-z at y = L): left plug, right blind wall
    S = 46.0
    ends = []
    for side, (a0, a1) in (("left", (-2.4, 5.6)), ("right", (W - 5.6, W + 1.2))):
        v0_, v1_ = L[1] - 4.6, L[1] + 7.2
        v = View(a0, v0_ - 70 / S, a1, v1_ + 34 / S, px_width=(a1 - a0) * S, pad_px=4)
        P = pids(v)
        i0 = clip_begin(v)
        frame_xz(v, P, L[0])
        hpoly(v, rect(max(rodp["x"][0], a0 - 1.0), min(rodp["x"][1], a1 + 1.0), L[1] - rod_d / 2, L[1] + rod_d / 2), "m-steel", P["steel"])
        v.cl(bL["x"][0] - 0.4 if side == "left" else a0, L[1], a1, L[1])
        clip_end(v, i0, a0, a1, v0_, v1_)
        b_ = bL if side == "left" else bR
        z_d = bbox(pts(b_))[3] + 1.2                   # above the boss, extension lines from the bore top
        if side == "left":
            xf = [(b_["x"][0], v0_, "보스·핀 바깥 = 마개 면"), (plg["x"][1], L[1] - bore / 2, "마개 끝"),
                  (rodp["x"][0], L[1] - bore / 2, "봉 끝 (P22)"), (b_["x"][1], v0_, "보스 끝")]
            v.dim_h(plg["x"][0], plg["x"][1], z_d, text=f"{F(plug_l)} 마개", ext_from=(L[1] + bore / 2, L[1] + bore / 2), size_px=9, tpos="right")
            v.dim_h(plg["x"][1], rodp["x"][0], z_d + 1.6, text="", ext_from=(L[1] + bore / 2, L[1] + rod_d / 2), size_px=9)
            v.text(rodp["x"][0] + v.px(16), z_d + 1.6 + v.px(3.2), f"{F2(play_l)} 축 틈", cls="dt", anchor="start", size_px=9)
            v.dim_v(L[1] - bore / 2, L[1] + bore / 2, b_["x"][0] - 0.9, text=f"Ø{F(bore)} (S11)", ext_from=(b_["x"][0], b_["x"][0]), size_px=9)
            ttl = f"왼쪽 끝 핀: 출력 마개 {F(plug_l)}, 끝 핀 면과 같게 (D18)"
        else:
            xf = [(b_["x"][0], v0_, "보스"), (rodp["x"][1], L[1] - bore / 2, "봉 끝 (P22)"), (blind, L[1] - bore / 2, "구멍 끝"),
                  (b_["x"][1], v0_, "보스·핀 바깥")]
            fin_x0 = min(p["x"][0] for p in fixed() if p["part"] == "fin" and p["x"][1] > W - 1.0)   # labels left of the fin
            v.dim_h(blind, b_["x"][1], z_d, text="", ext_from=(L[1] + bore / 2, L[1] + bore / 2), size_px=9)
            v.text(fin_x0 - v.px(6), z_d + v.px(3.2), f"{F(wall_t)} 막힌 벽", cls="dt", anchor="end", size_px=9)
            v.dim_h(rodp["x"][1], blind, z_d + 1.6, text="", ext_from=(L[1] + rod_d / 2, L[1] + bore / 2), size_px=9)
            v.text(fin_x0 - v.px(22), z_d + 1.6 + v.px(3.2), f"{F2(play_r)} 축 틈", cls="dt", anchor="end", size_px=9)
            ttl = f"오른쪽 끝 핀: 막힌 구멍 x{F2(blind)}까지, 벽 {F(wall_t)} (D18)"
        ordy(v, in_win(xf, v0_, v1_), v0_ - 0.2, gap_px=12.5, label_px=9, lo=a0)
        panel_title(v, a0 + v.px(3), v1_ + v.px(12), ttl, size_px=11)
        ends.append(v)
    # plug part: side + end view
    Sp = 40.0
    pv = View(-2.5, -4.5, 9.5, 4.8, px_width=12.0 * Sp, pad_px=4)
    hpoly(pv, rect(0.0, plug_l, -bore / 2, bore / 2), "m-print2")
    pv.circle(5.4, 0.0, bore / 2, cls="m-print2")
    pv.cl(-0.6, 0.0, plug_l + 0.6, 0.0)
    pv.cl(5.4 - bore / 2 - 0.6, 0.0, 5.4 + bore / 2 + 0.6, 0.0)
    pv.cl(5.4, -bore / 2 - 0.6, 5.4, bore / 2 + 0.6)
    pv.dim_h(0.0, plug_l, bore / 2 + 0.8, text=F(plug_l), ext_from=(bore / 2, bore / 2), size_px=9.5)
    pv.dim_v(-bore / 2, bore / 2, -0.9, text=f"Ø{F(bore)}", ext_from=(0.0, 0.0), size_px=9.5)
    pv.text(plug_l / 2, -bore / 2 - pv.px(16), "옆에서", cls="tx-s", size_px=9)
    pv.text(5.4, -bore / 2 - pv.px(16), "끝에서", cls="tx-s", size_px=9)
    panel_title(pv, -2.4, 4.8 - pv.px(12), f"마개 부품 — {plug['kind']} PETG, {plug['total']}개", size_px=11)
    # ------------------------------------------------ C. notes + the printed tools -> drawing 14
    MV = TGEO["model_values"]
    pr = TGEO["print"]
    amp = TGEO["dummy_lever"]["per_colour"]
    rows = [["T1 벤치 지그", f"밑면 z{F(tn('T01'))} = 프레임 밑면 (T01)",
             f"K 봉 중심 z{F(tn('T05', 1))} (T05) · 쉼 선반 z{F(tn('T06', 3), 3)} (T06) · L 봉 중심 z{F(tn('T07', 1))} (T07)"],
            ["T1 높이 블록", f"받침판 윗면 z{F(tn('T02', 5))} (T02)",
             f"건반 앞 윗면: 백 {F(tn('T12'))}~{F(tn('T11'))} · 흑 {F(tn('T14'))}~{F(tn('T13'))} (T11~T14, 창 ±{F(tn('T15'))})"],
            ["T2 캡스턴 게이지", f"L 봉 토막 (y{F2(tn('T16', 2))}, z{F(tn('T16', 3))}) (T16)",
             f"캡스턴 꼭대기 z{F(tn('T17'))} (T17) · 1/8회전 = 바늘 백 {F(amp['white']['per8'])} / 흑 {F(amp['black']['per8'])} (T22)"],
            ["T3 핀 높이 게이지", f"레일 윗면 z{F(tn('T24'))} (T24)",
             f"밸런스 핀 꼭대기 z{F2(tn('T26', 1))} (T26), 합격 z{F2(tn('T29', 2))}~{F2(tn('T28', 2))} (T28 · T29)"]]
    keys_ = ["bench_jig", "height_block", "capstan_gauge", "pin_gauge"]
    for r_, k in zip(rows, keys_):
        r_ += [" × ".join(kit.FX(b, 1) for b in pr[k]["bbox"]), f"{kit.FX(pr[k]['mass_g'], 1)} g"]   # r4.5 fix 3: fixed 1 decimal
    nv = View(0, -215, 1480, 0, px_width=1480, pad_px=6)
    label(nv, 6, -14, f"출력 공구 4개 → 도면 14 (실제 모양·치수, tools_geometry.json T01~T29 · tools/make_tools.py STL과 같은 값)", size_px=12, anchor="start", cls="tx")
    yb = table(nv, 6, -24, ["공구", "기준 (닿는 면)", "맞추는 높이·자리", "출력 크기", "질량"], rows, [150, 300, 620, 150, 80], row_px=19, size_px=10)
    note_lines(nv, [f"합계 {F(TGEO['total_mass_g'], 1)} g · {F(TGEO['total_time_min'], 0)}분 (parts_list: {tools['name']} {tools['total']}개). 쓰는 순서와 합격 기준은 도면 14 글과 DESIGN 10.1장.",
                    f"parts_list: {plug['name']} — {plug['spec']} · {plug['total']}개 · {F(plug['unit_g'])} g",
                    f"  구멍 Ø{F(bore)} = 보스 드릴 구멍 (S11). 마개 면 = 끝 핀 면 (D18). 축 놀음 왼쪽 {F2(play_l)} + 오른쪽 {F2(play_r)} = {F2(play_l + play_r)} (봉 길이 ± {F(RR['rod_len_tol'])}이면 {F2(play_l + play_r - RR['rod_len_tol'])}~{F2(play_l + play_r + RR['rod_len_tol'])}).",
                    "  눌러 끼우는 억지 양은 모델에 없음 → 단계 0 쿠폰에서 정함 (손으로 들어가고 저절로 빠지지 않을 것). 레버 봉을 뽑을 때는 마개를 먼저 뺀다 (도면 12 글)."],
               6.0, yb - 16, line_px=17, size_px=10.5)
    rows_ = [[ov], ends + [pv], [nv]]
    base = os.path.join(OUT, "d13_rod_plug_tools")
    page(rows_, base, "도면 13. 레버 봉 끝 마개 (출력 공구 3종은 도면 14)",
         "단위 mm · 숫자 = geometry.json (괄호 = 치수표 번호; 봉·구멍·마개 = D18 부품) · 부품 수·무게 = parts_list.json · 공구 표 = tools_geometry.json · "
         "연녹 = 출력 마개, 회색 빗금 = 강철 봉, 흰 칸 = 드릴 구멍 Ø4.0")
    rec(13, base, "레버 봉 끝 마개 (출력 공구는 도면 14)",
        f"레버 봉 Ø{F(rod_d)} x{F2(rodp['x'][0])}~{F2(rodp['x'][1])}(길이 {F2(rodp['x'][1] - rodp['x'][0])} ± {F(RR['rod_len_tol'])})가 핀 {RR['n_bores']}장의 보스 구멍 Ø{F(bore)}을 지나는 전체 단면과 두 끝 확대: "
        f"왼쪽 끝 핀은 출력 마개 x{F2(plg['x'][0])}~{F2(plg['x'][1])}(길이 {F(plug_l)}, 끝 핀 면과 같게 눌러 끼움, 봉과 {F2(play_l)}), 오른쪽 끝 핀은 x{F2(blind)}까지 막힌 구멍(벽 {F(wall_t)}, 봉과 {F2(play_r)}) — 모두 geometry의 D18 부품. "
        f"마개 부품 {plug['total']}개. r4.4: 개략이던 출력 공구 그림을 지우고 도면 14(실제 치수)를 가리키는 표만 남김 — 공구마다 기준 면과 맞추는 높이(K z{F(tn('T05', 1))}·쉼 선반 z{F(tn('T06', 3), 3)}, "
        f"캡스턴 z{F(tn('T17'))}, 핀 꼭대기 z{F2(tn('T26', 1))}).")
