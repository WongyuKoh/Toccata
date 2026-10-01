"""Toccata v4 W1+ round 4 — dimensioned engineering drawings (15 sheets) from ../final/geometry.json (14 / 15 in render_v4c.py).

run:  ../../venv/bin/python render_v4.py [n ...]      (no argument = all sheets)
out:  dNN_*.svg + dNN_*.png (1800 px) + drawings.json   in this folder.
A re-run after the model changes (geometry.json / metrics.json rewritten) picks up every number: nothing is cached
and no local geometry patch is applied (the r3 drawing-side corrections are merged into the model).

Every number drawn is read from geometry.json (parts / plan / end_parts / solved / dims; dimension ids are cited
in the labels as (P13), (S15) ...).  Removal poses (sheet 12) come from ../final/metrics.json (same model run);
the rear-bar outline (sheet 11) and the magnet size from the v3 tables (context/v3_extract.txt).
Coordinates in the code that are not read from those files are only label / balloon PLACEMENT positions.
House style = v3 render_drawings.py: rest pose solid, full dip dashed orange, parts coloured by material,
balloons + legend, ordinate dimensions, scale bar.
"""
import json
import math
import os
import sys

import kit
from kit import (G, SOL, PLAN, View, fmt_mm, dn, dns, v3n, nums, body, fixed, pts, cut_x, plan_item, plan_all, bbox, yslice,
                 rot, rot_pts, rect, arc_pts, circle_pts, union_rings, fill_rings, stroke_rings, hpoly, pids, mat_fixed,
                 pivot_mark, sensor_mark, scalebar, balloon_row, legend, note_lines, label, panel_title, leader_to,
                 table, page, ordz, ordy, clip_begin, clip_end, F2, callouts)

OUT = kit.HERE
DIMS_ = kit.DIMS
def F(v, nd=2):
    return fmt_mm(v, nd)
SHEETS = []


def _labels():
    """label fragments whose numbers are read from the dimension table / solved block (no typed values)."""
    p32, s08, s11, s16 = dns("P32"), dns("S08", "item"), dns("S11", "note"), dns("S16")
    s21, d10v, d10n = dns("S21", "note"), dns("D10"), dns("D10", "note")
    d11, d06, sp = dns("D11"), dns("D06"), SOL["spring"]
    mag = (2 * plan_item("key D magnet")["circle"][2], v3n(r"자석 Ø5×", 0))
    return dict(
        rod4=f"Ø{F(dn('S03', 0, 'note'))} SUS304", pin=f"Ø{F(p32[1])}×{F(p32[2])}", rail_z=f"z{F(dns('P20')[3])}",
        cap=f"M{F(s08[0])}×{F(s08[1])}", rest_felt=f"{F(dns('P28', 'note')[0])}T", strip_felt=f"{F(dns('S14')[3] - dns('S14')[2])}T",
        rodL=f"Ø{F(s11[0])} SUS304", hub=f"R{F(s11[2])}", bore=f"Ø{F(s11[3])} 출력 → Ø{F(s11[4])} 드릴",
        foam=f"{F(d11[0])}T", pad_felt=f"{F(d11[1])}T", bar_t=f"{F(s16[1])}T",
        magnet=f"Ø{F(mag[0])}×{F(mag[1])}", cloth=f"{F(dn('P31', 0, 'note'))}T",
        front_felt=f"펠트 {F(s21[0])}T + PU {F(s21[1])}T", front_felt_lr=f"펠트 {F(s21[0])}T + 저반발 PU {F(s21[1])}T",
        punch=f"종이 펀칭 {F(d10v[3])}×{F(d10v[4])}, 한 장 = 앞 {F(d10n[0])}", low_lip=f"{F(low_lip_wh()[0])}×{F(low_lip_wh()[1])}",
        top_lip=f"{F(top_lip_wh()[0])}×{F(top_lip_wh()[1])}", keeper_felt=f"{F(dn('S20', 0, 'note'))}T", fins=len(SOL["fins"]),
        collar=f"Ø{F(d06[0])}", boss=f"Ø{F(d06[2])}", notch=f"R{F2(dn('S04', 0))}",
        spring=f"d{F(sp['d'])} · ID {F(sp['ID'])} · {F(sp['n'])}권 · k {F(sp['kt'])} N·mm/rad",
        top=f"z{F2(dn('S18'))}")


KP_W = G["key_points"]["white D"]
KP_B = G["key_points"]["black C#"]
K = tuple(KP_W["K"])
L = tuple(KP_W["L"])


def kpt(kp, name, pose="rest"):
    for p in kp["points"]:
        if p["point"].startswith(name):
            return tuple(p[pose])
    raise KeyError(name)


def part(bodyname, partname, i=0, src=None):
    return [p for p in body(bodyname, src) if p["part"].startswith(partname)][i]


def fpart(name, src=None):
    return next(p for p in fixed(src) if p["part"] == name)


def fparts(prefix, src=None):
    return [p for p in fixed(src) if p["part"].startswith(prefix)]


def bar_steps(src=None):
    """r4.2 pad-bar joggle from the bar outline: (bottom step y, top step y) = (165.5, 167.0)."""
    q = pts(fpart("pad bar") if src is None else next(p for p in src if p["part"] == "pad bar"))
    zb, zt = min(t[1] for t in q), max(t[1] for t in q)
    return min(t[0] for t in q if abs(t[1] - zb) < 1e-6), max(t[0] for t in q if abs(t[1] - zt) < 1e-6)


def usb_env():
    """r4.3: the USB-C plug envelope (P24) as a fixed prism; its name carries the z range ('USB-C plug envelope (z..)')."""
    return fparts("USB-C plug envelope")[0]


def shelf_slot():
    """r4.3: open slot in the rear shelf over the USB plug (P19), x range from the plan item."""
    q = plan_item("rear shelf slot over the USB plug (open)")["poly"]
    return min(t[0] for t in q), max(t[0] for t in q)


def shelf_plan_polys():
    """the rear shelf pieces in plan (r4.3: two pieces beside the USB slot)."""
    return [[tuple(t) for t in p["poly"]] for p in PLAN if p["part"] == "rear shelf"]


# the frame is ONE print: these fixed sub-parts are drawn as one union (pad bar rails and fin bosses included)
FRAME_KEYS = ("floor", "white front rail", "tab ", "keeper hook", "black stop rail", "black tab base", "balance rail",
              "rod end stop post", "rear shelf", "shelf rib", "fin", "top plate", "pad bar rail", "rear wall",
              "rear dovetail", "front dovetail", "cheek", "spring groove boss",
              # r4.4 (circuit session): printed with the frame — control-board stand-offs + locating pins (P35),
              # v3 sensor-board support post + ribs (P36 / A02 / A03)
              "control-board stand-off", "control-board locating pin", "sensor board support",
              # r4.4 fix 2b: the four bosses hung over the board (brackets to the balance rail / shelf ribs), frame print
              "control-board boss",
              # r4.5 circuit 2nd (request 8, P36): the sensor-bar right ledge (v3 P112) = lip + post, front / rear
              "sensor-bar ledge")


def ledge_parts(src=None):
    """r4.5 circuit 2nd (P36): the 4 sensor-bar ledge prisms (lip / post, front / rear), geometry.json parts."""
    return sorted((p for p in fixed(src) if p["part"].startswith("sensor-bar ledge")),
                  key=lambda p: (bbox(pts(p))[0], p["x"][0]))


def ledge_slide():
    """P36 note (r4.5 circuit 2nd): the bar + board are laid down this far left of their place, then slid right under
    the ledge lip (v3 procedure, with the module out / no left neighbour)."""
    import re
    return float(re.search(r"([\d.]+) mm 왼쪽에 내려놓", kit.DIMS["P36"]["note"]).group(1))


def is_boss(n):
    """fin boss prism (frame).  r4.4: 'fin boss bore D4.0 ...' is the drilled bore (a void), not a boss."""
    return n.startswith("fin boss") and not n.startswith("fin boss bore")


def boss_parts(src=None):
    return [p for p in fixed(src) if is_boss(p["part"])]


def bore_parts(src=None):
    """r4.4 (D18): the fin-boss bores Ø4.0 as exported prisms (x ranges: the right end fin is blind)."""
    return [p for p in fixed(src) if p["part"].startswith("fin boss bore")]


def rod_part(src=None):
    """r4.4 (D18 / P22): the lever rod Ø4 SUS304 as an exported prism."""
    return next(p for p in fixed(src) if p["part"].startswith("lever rod D4"))


def plug_part(src=None):
    """r4.4 (D18 / P22): the printed rod-end plug, pressed flush with the end-fin face."""
    return next(p for p in fixed(src) if p["part"].startswith("lever rod end plug"))


def void_first(parts):
    """draw order for the non-frame fixed parts: voids (bores) first, then the rest (so the rod sits on top)."""
    return sorted(parts, key=lambda p: 0 if mat_fixed(p["part"])[0] == "void" else 1)


# ---------------------------------------------------------------- carrier lips (D07) and the control board outline (P23)
def top_lip_parts(lever="lever D", src=None):
    """r4.4: the carrier top snap lips are exported parts ('carrier top snap lip L y150-163' ...) — left-side ones."""
    return sorted((p for p in body(lever, src) if p["part"].startswith("carrier top snap lip L")),
                  key=lambda p: min(t[0] for t in pts(p, "rigid0")))


def top_lip_spans(lever="lever D", src=None):
    """lever-frame y spans of the top snap lips, from the exported lip parts (r4.4: [(150, 163), (184, 190)])."""
    sp = []
    for p in top_lip_parts(lever, src):
        q = pts(p, "rigid0")
        sp.append((min(t[0] for t in q), max(t[0] for t in q)))
    return sp


def top_lip_wh(lever="lever D", src=None):
    """(width, height) of a top lip from its part (x range, z range at 0 deg)."""
    p = top_lip_parts(lever, src)[0]
    q = pts(p, "rigid0")
    return p["x"][1] - p["x"][0], max(t[1] for t in q) - min(t[1] for t in q)


def in_top_lip(y):
    return any(a - 1e-9 <= y <= b + 1e-9 for a, b in top_lip_spans())


def _d07_low():
    import re as _re
    m = _re.search(r"아래 립 ([\d.]+)×([\d.]+) \(y([\d.]+)~([\d.]+)", DIMS_["D07"]["value"])
    kit.USED["D07"] = DIMS_["D07"]["item"]
    return tuple(float(t) for t in m.groups())


def low_lip_wh():
    """D07 '아래 립 1.0×1.0 (y165~176.5, ...)' -> (width, height, y0, y1)."""
    return _d07_low()


def steel_plan_rects(xc, lt):
    """steel top seen from above between the front cap end and the steel rear: narrow (between the 0.8 top lips)
    over the lip spans, full width where the lips are cut (beside the pad, D07) and behind the last lip."""
    hw, li = lt["steel_hw"], lt["lip_in"]
    out, cur = [], lt["cap_end"]
    for a, b in top_lip_spans():
        a = max(a, cur)
        if b <= a:
            continue
        if a > cur + 1e-6:
            out.append(rect(xc - hw, xc + hw, cur, a))
        out.append(rect(xc - hw + li, xc + hw - li, a, b))
        cur = b
    if lt["s_rear"] > cur + 1e-6:
        out.append(rect(xc - hw, xc + hw, cur, lt["s_rear"]))
    return out


def board_rings(src=None):
    """plan outline of the control board (P23) with the r4.1 slot for the F|F# fin (from the board part pieces)."""
    rs = [rect(p["x"][0], p["x"][1], bbox(pts(p))[0], bbox(pts(p))[1]) for p in fixed(src) if p["part"].startswith("control board")]
    return union_rings(rs, res=0.02)


def is_frame(name):
    return any(name.startswith(k) for k in FRAME_KEYS)


def pad_face(black):
    return SOL["pad_face_b" if black else "pad_face_w"]


def pad_layers(p):
    """D11: up-stop pad = felt 1T on the face (bottom) + micro-cell urethane foam 6T above it.  The pad prism of
    geometry.json is a parallelogram p0 p1 (face) p2 p3 (back, on the wedge); the layers split it along p0->p3."""
    p0, p1, p2, p3 = pts(p)[:4]
    foam, felt = dns("D11")[:2]
    t = felt / (foam + felt)
    q0 = (p0[0] + (p3[0] - p0[0]) * t, p0[1] + (p3[1] - p0[1]) * t)
    q1 = (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)
    return [([p0, p1, q1, q0], "m-felt"), ([q0, q1, p2, p3], "m-foam")], dict(felt=felt, foam=foam, face=(p0, p1), back=(p3, p2))


def split_para(poly, t_bottom):
    """4-point parallelogram (p0,p1 bottom, p2,p3 top) -> (lower layer of thickness t_bottom, upper layer)."""
    p0, p1, p2, p3 = poly
    q0 = (p0[0], p0[1] + t_bottom)
    q1 = (p1[0], p1[1] + t_bottom)
    return [p0, p1, q1, q0], [q0, q1, p2, p3]


def pu_t():
    """S21 note: '펠트 2T + 저반발 PU 1T' -> PU thickness (under the felt)."""
    return dns("S21", "note")[1]


def mag_size():
    return 2 * plan_item("key D magnet")["circle"][2], v3n(r"자석 Ø5×", 0)


def magnet_polys(y, z_face):
    """Ø5 (plan circle) x 2 (v3 'Ø5×2') magnet, S pole down on the face z_face."""
    d, t = mag_size()
    return rect(y - d / 2, y + d / 2, z_face, z_face + t / 2), rect(y - d / 2, y + d / 2, z_face + t / 2, z_face + t)


def cloth_ring(c):
    """S04: notch R2.55 lined with 0.5T cloth (effective R2.05), wrap 223 deg centred on the top."""
    r_out, r_in = dn("S04", 0), dn("S04", 2)
    wrap = dn("S04", 0, "note")
    a0, a1 = 90 - wrap / 2, 90 + wrap / 2
    return arc_pts(c, r_out, a0, a1, 40) + arc_pts(c, r_in, a1, a0, 40)


def block_bottom_z(key):
    """z of the balance-block bottom beside the snap lips (first vertex of the block polygon)."""
    return pts(part(key, "balance block"))[0][1]


def pin_groove(key):
    """P32 note: groove under the block, printed width 3.2 (cloth 0.5 both sides -> 2.2), depth 2.5, y134.0~138.0."""
    n = dns("P32", "note")      # [3.2, 0.5, 2.2, 2.5, 134.0, 138.0, 1.39, ...]
    zb = block_bottom_z(key)
    return dict(y0=n[4], y1=n[5], z0=zb, z1=zb + n[3], w=n[0], w_cloth=n[2], cloth=n[1], lip_wall=n[6])


def cradle_y():
    """rod cradle (S05 / P20): the y of its four edges at the lip height (the cradle polygon of geometry.json)."""
    q = pts(fparts("balance rail cradle")[0])
    zl = dn("S05", 0)
    return sorted(set(round(t[0], 3) for t in q if abs(t[1] - zl) < 1e-6))


def rest_rad(black):
    """lever rest angle (rad) with the drawn sign convention (key_points b_rest)."""
    return (KP_B if black else KP_W)["b_rest"]


def top_edge_rest(lever, name, end="rear"):
    """one end of the top edge of a lever sub-part, in the settled rest pose: the top edge = the vertices at the
    highest z of the 0-deg polygon (side_rigid0); the rest-pose point with the same index is returned."""
    p = part(lever, name)
    q0, q = pts(p, "rigid0"), pts(p, "rest")
    zt = max(t[1] for t in q0)
    idx = [i for i, t in enumerate(q0) if abs(t[1] - zt) < 1e-6]
    i = (max if end == "rear" else min)(idx, key=lambda k: q0[k][0])
    return q[i]


def steel_top(lever, end="rear", pose="rest"):
    """end of the steel block top edge in a pose (index taken from the 0-deg polygon)."""
    p = part(lever, "steel block")
    q0, q = pts(p, "rigid0"), pts(p, pose)
    zt = max(t[1] for t in q0)
    idx = [i for i, t in enumerate(q0) if abs(t[1] - zt) < 1e-6]
    i = (max if end == "rear" else min)(idx, key=lambda k: q0[k][0])
    return q[i]


def steel_top_rest(lever, end="rear"):
    return steel_top(lever, end, "rest")


def front_y_at(poly, z):
    """front (smallest y) of a closed (y, z) polygon on the horizontal line z."""
    ys = []
    n = len(poly)
    for i in range(n):
        (y1, z1), (y2, z2) = poly[i], poly[(i + 1) % n]
        if (z1 <= z < z2) or (z2 <= z < z1):
            ys.append(y1 + (y2 - y1) * (z - z1) / (z2 - z1))
    return min(ys)


def capstan_shank(key):
    """S08 'M3×6': shank Ø3 x 6 below the head (the dome polygon's widest line = head underside)."""
    cp = pts(part(key, "capstan head"))
    zb = min(q[1] for q in cp)                      # neck bottom (beam seat)
    ymin = min(q[0] for q in cp)
    zh = next(q[1] for q in cp if abs(q[0] - ymin) < 1e-6)   # head underside (widest point)
    yc = (ymin + max(q[0] for q in cp)) / 2
    d, ln = dns("S08", "item")[0], dns("S08", "item")[1]
    return yc, d, zh, zh - ln, zb


def dim_aligned(v, a, b, off_px, text, size_px=9.5):
    """dimension parallel to a-b, offset off_px to the right of a->b (screen), label beside its middle."""
    du, dv = b[0] - a[0], b[1] - a[1]
    Ln = math.hypot(du, dv)
    nu, nv = dv / Ln, -du / Ln                      # right-hand normal (world, v up)
    o = v.px(off_px)
    A = (a[0] + nu * o, a[1] + nv * o)
    B = (b[0] + nu * o, b[1] + nv * o)
    for p, q in ((a, A), (b, B)):
        v.line(p[0] + nu * v.px(2), p[1] + nv * v.px(2), q[0] + nu * v.px(3), q[1] + nv * v.px(3), cls="ex")
    v.line(A[0], A[1], B[0], B[1], cls="dm")
    ang = math.atan2(dv, du)
    if Ln * v.s > 26:
        v._arrow(B[0], B[1], ang)
        v._arrow(A[0], A[1], ang + math.pi)
    else:
        v._arrow(B[0], B[1], ang + math.pi)
        v._arrow(A[0], A[1], ang)
    m = ((A[0] + B[0]) / 2 + nu * v.px(6), (A[1] + B[1]) / 2 + nv * v.px(6))
    v.text(m[0], m[1] - v.px(3.5), text, cls="dt", anchor="start" if nu >= 0 else "end", size_px=size_px)


def _on_line(a, b, y):
    """z on the line a-b at y."""
    return a[1] + (b[1] - a[1]) * (y - a[0]) / (b[0] - a[0])


def plate_z(y):
    """z intervals of the top plate (P15) at y."""
    return yslice(pts(fpart("top plate (ledge + bridge)")), y)


def plate_under_mid(z):
    """middle y of the top-plate underside edge at height z (the edge an ordinate at z measures, P15 / S17)."""
    q = pts(fpart("top plate (ledge + bridge)"))
    segs = [(a, b) for a, b in zip(q, q[1:] + q[:1]) if abs(a[1] - z) < 1e-6 and abs(b[1] - z) < 1e-6]
    a, b = max(segs, key=lambda t: abs(t[1][0] - t[0][0]))
    return (a[0] + b[0]) / 2


# ---------------------------------------------------------------- torsion assist spring (P18 / D05 / solved.spring)
def spring_geom():
    """coil on the lever rod at L in the hub pocket; long leg to the rear-wall groove (P18: y209, z50~58, 1.2 x 0.8).
    The leg tip sits in the groove at the leg length from the coil axis (solved.spring.leg); the leg is tangent to
    the coil (mean radius (ID + d) / 2)."""
    sp = SOL["spring"]
    gy, gz0, gz1, gw, gd = sp["groove"]
    r_m = sp.get("coil_rm", (sp["ID"] + sp["d"]) / 2)
    if "long_leg_world" in sp:          # r4.2: the model exports the tangent long leg (rest pose) and the short leg
        tp, tip = tuple(sp["long_leg_world"][0]), tuple(sp["long_leg_world"][1])
    else:
        ty = gy + gd / 2
        dy = ty - L[0]
        tz = L[1] + math.sqrt(sp["leg"] ** 2 - dy * dy)
        D = math.hypot(ty - L[0], tz - L[1])
        a = math.atan2(tz - L[1], ty - L[0]) - math.acos(r_m / D)
        tp, tip = (L[0] + r_m * math.cos(a), L[1] + r_m * math.sin(a)), (ty, tz)
    short = [tuple(t) for t in sp.get("short_leg_lever_frame", [])]
    return dict(r_m=r_m, d=sp["d"], tip=tip, tp=tp, groove=(gy, gy + gd, gz0, gz1), pocket=sp["pocket"],
                ID=sp["ID"], n=sp["n"], leg=sp["leg"], kt=sp["kt"], free=sp["free_deg"], gw=gw, short=short,
                slot_deg=sp.get("slot_deg_lever_frame"), slot_faces=sp.get("slot_faces"), bend=sp.get("short_leg_bend_deg"),
                leg_range=sp.get("leg_range_deg"), leg_margin=sp.get("leg_slot_margin"))


def pocket_x(nm):
    """x range of the spring pocket = hub centre +- pocket length / 2 (P18 '허브 가운데 주머니 Ø6.1×3.0')."""
    xc = SOL["levers"][nm]
    return xc - SOL["spring"]["pocket"][1] / 2, xc + SOL["spring"]["pocket"][1] / 2


def short_leg_len():
    """D05 '... 짧은 다리 2.5 (접선, 굽힘 없음)' -> 2.5 (r4.5 catalogue spring, arm cut)."""
    import re as _re
    kit.USED["D05"] = DIMS_["D05"]["item"]
    return float(_re.search(r"짧은 다리 ([\d.]+)", DIMS_["D05"]["value"]).group(1))


def spring_txt():
    """r4.5 fix: shared wording (numbers from solved.spring) for the captured short-leg groove, the insertion slot along
    the leg and the long-leg window of the hub's spring-pocket section (P18 / D05)."""
    sp = SOL["spring"]
    slg = sp["short_leg_groove"]
    bd = slg.get("band_deg", slg["leg_dir"])
    win = slg.get("window", sp.get("window", [35.0, 2.6]))
    return dict(
        slot=f"넣는 슬롯 {F(sp.get('insertion_slot_deg', sp['slot_deg_lever_frame']))}° 면 ±{F2(sp['slot_faces'][0])}",
        window=f"긴 다리 창 {F(win[0])}° 윗면 +{F(win[1])}",
        groove=f"가둠 홈 폭 {F2(slg.get('width', slg['nn'][1] - slg['nn'][0]))} ({F2(bd)}° 방향, 축에서 {F2(slg['nn'][0])}~{F2(slg['nn'][1])}, 막힌 끝)",
        short=f"짧은 다리 {F(short_leg_len())}",
        contacts=f"다리 끝(바깥 면) + 주머니 모서리(안 면) 두 점, 팔 {F2(slg.get('arm', 0.0))}",
        web=f"웹 밑면에서 {F2(slg['web_cut_depth'])} 올라감",
        dx=f"레버 x +{F(sp.get('groove_dx', 0.0))}")


def spring_parts(nm, src=None):
    """r4.5: the exported spring prisms of one position -> (coil, short leg, long leg).  MISUMI C-UA90R5-3-0.5 with
    both arms cut: coil OD 6.0 x 2.13 in the D6.6 x 3.0 hub pocket, short leg straight in the hub's short-leg groove
    (-x coil end), long leg straight up into the 2.4-wide rear-wall groove (+x coil end)."""
    ps = body(f"spring {nm}", src)
    return (next(p for p in ps if "coil" in p["part"]), next(p for p in ps if "short leg" in p["part"]),
            next(p for p in ps if "long leg" in p["part"]))


def spring_groove_cut(xsec):
    """r4.5 rear-wall spring-leg grooves (solved.spring.grooves, exported only as data, not as a frame cut) that the
    plane x = xsec runs through -> [(y, z) rect] to subtract from the frame section."""
    return [rect(g["y"][0], g["y"][1], g["z"][0], g["z"][1]) for g in SOL["spring"].get("grooves", [])
            if g["x"][0] <= xsec <= g["x"][1]]


def _pip(pt, poly):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def split_outline(v, q, solids, voids=(), vis_cls="spring", hid_cls="hid", n=120):
    """outline of a part seen BEYOND the section plane: the edge runs that lie behind cut material (inside one of
    `solids` and not in one of `voids`, all (y, z) polygons of the section) are drawn hidden (dashed), the rest
    visible (drafting rule: an edge behind the cut face is hidden)."""
    hidden = lambda p: any(_pip(p, s_) for s_ in solids) and not any(_pip(p, h_) for h_ in voids)
    for a, b in zip(q, q[1:] + q[:1]):
        L_ = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(2, int(n * L_ / 20.0))
        pts_ = [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k + 1)]
        runs, cur, st = [], [pts_[0]], None
        for p0, p1 in zip(pts_, pts_[1:]):
            h = hidden(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2))
            if st is None or h == st:
                cur.append(p1)
            else:
                runs.append((st, cur))
                cur = [p0, p1]
            st = h
        runs.append((st, cur))
        for h, r_ in runs:
            v.poly(r_, cls=hid_cls if h else vis_cls, closed=False)


def draw_spring(v, nm, xsec, cut_hub=True, pose="rest", tf=None, leg_tf=None, hide=None):
    """spring as exported (P18 / D05): the hub pocket, slot and short-leg groove are the lever's own 'spring pocket
    section A / B' prisms (drawn with the lever), so no pocket is painted here.  Cut by the plane -> steel section
    (coil = annulus ID..OD, legs = bands); beyond the plane -> visible outline, hidden (dashed) where it runs behind
    the cut frame (hide = (solids, voids) of the section, e.g. the long leg inside the rear-wall groove).
    tf: lever transform (coil + short leg ride on the hub); the long leg is held in the rear-wall groove, so it does
    NOT follow the lever: leg_tf (default: the exported pose) - r4.5 fix: a keyless lever below the free angle turns
    it only by the angle past the free angle (metrics leg_in_groove_drop)."""
    sg = spring_geom()
    tf = tf or (lambda t: t)
    ltf = leg_tf or (lambda t: t)
    coil, short, long_ = spring_parts(nm)
    cq = [tf(t) for t in pts(coil, pose)]
    c = (sum(t[0] for t in cq) / len(cq), sum(t[1] for t in cq) / len(cq))
    ro, ri = sg["r_m"] + sg["d"] / 2, sg["r_m"] - sg["d"] / 2
    # looking from +x toward -x: x > xsec is the removed half (phantom), x < xsec is seen beyond the cut
    if cut_x(coil, xsec):
        v.circle(c[0], c[1], ro, cls="m-steel")
        v.circle(c[0], c[1], ri, cls="void")
    else:
        for r_ in (ro, ri):
            v.circle(c[0], c[1], r_, cls="spring" if coil["x"][1] < xsec else "phan")
    for leg, f_ in ((short, tf), (long_, ltf)):
        q = [f_(t) for t in pts(leg, pose)]
        if cut_x(leg, xsec):
            hpoly(v, q, "m-steel")
        elif leg["x"][1] < xsec and hide:
            split_outline(v, q, hide[0], hide[1])
        else:
            v.poly(q, cls="spring" if leg["x"][1] < xsec else "phan")
    return sg


# ================================================================ side section scene (sheets 1, 2, 12)
def side_scene(v, P, key, lever, xsec, black, press=True, beyond=True, extra_cut_keys=(), key_tf=None,
               lever_pose="rest", lever_tf=None, skip_fixed=(), marks=True, sensor=True, spring=True, spring_leg_tf=None):
    """section plane x = xsec, looking from +x (treble side) toward -x: y to the right, z up.
    key_tf / lever_tf: optional point transforms (removal poses); spring_leg_tf: the long spring leg's own transform
    (it stays in the rear-wall groove, see draw_spring)."""
    nm = key[4:]
    kp = KP_B if black else KP_W
    ktf = key_tf or (lambda t: t)
    ltf = lever_tf or (lambda t: t)
    fl = fpart("floor")
    fy0, fy1, _, _ = bbox(pts(fl))
    eva = dns("S01")                                   # [0, 3, 3, 5]
    v.rect(fy0 + 0.5, eva[0], fy1 - fy0 - 1.0, eva[1] - eva[0], cls="faintfill")
    skip = tuple(skip_fixed) if skip_fixed else ("\0",)
    fx = [p for p in fixed() if cut_x(p, xsec) and not p["part"].startswith(skip)]
    # ---- beyond (x < xsec, seen behind the cut): nearest cradle, own key / lever walls
    if beyond:
        cr = [p for p in fixed() if p["part"] == "balance rail cradle" and p["x"][1] < xsec]
        if cr:
            v.poly(pts(max(cr, key=lambda p: p["x"][1])), cls="vis")
        for p in body(key):
            if not cut_x(p, xsec) and p["x"][1] < xsec:
                v.poly([ktf(t) for t in pts(p)], cls="vis")
        for p in body(lever):
            if not cut_x(p, xsec) and p["x"][1] < xsec:
                v.poly([ltf(t) for t in pts(p, lever_pose)], cls="vis")
    # ---- fixed, cut: the frame as one union (top plate, fins, pad bar rails, bosses ...); r4.5 fix: minus the
    # rear-wall spring-leg groove when the plane runs through it (solved.spring.grooves, as drawing 8 does)
    gcut = spring_groove_cut(xsec)
    fsol = [pts(p) for p in fx if is_frame(p["part"])]
    fill_rings(v, union_rings(fsol, subs=gcut), "m-print", P["print"])
    for p in void_first(fx):
        n = p["part"]
        if is_frame(n):
            continue
        q = pts(p)
        if n.startswith("up-stop pad"):
            for poly, cls in pad_layers(p)[0]:
                v.poly(poly, cls=cls)
            continue
        if "front felt" in n:
            lo, hi = split_para(q, pu_t())
            v.poly(lo, cls="m-pu")
            v.poly(hi, cls="m-felt")
            continue
        cls, h = mat_fixed(n)
        if cls == "env":
            v.poly(q, cls="env")
            continue
        hpoly(v, q, cls, P[h] if h else None)
    # the pad bar is ONE print (bar + grip + wedges): its outline over the sub-part fills
    bar = [pts(p) for p in fx if p["part"].startswith(("pad bar", "pad wedge")) and not p["part"].startswith("pad bar rail")]
    stroke_rings(v, union_rings(bar), "out")
    # guide-tab cloth (P31): 0.5T on the tab front face, from the tab foot to the hook
    for p in fx:
        if p["part"].startswith("tab "):
            y0, y1, z0, z1 = bbox(pts(p))
            t = dn("P31", 0, "note")
            hook = [h for h in fx if h["part"] == "keeper hook " + p["part"][4:]]
            ztop = min(q[1] for q in pts(hook[0])) if hook else z1
            v.poly(rect(y0, y0 + t, z0, ztop), cls="m-cloth")
    # ---- other keys cut by the plane (the white neighbour head in the black section)
    for nm_ in extra_cut_keys:
        fill_rings(v, union_rings([pts(p) for p in body(nm_) if cut_x(p, xsec)]), "m-key", P["key"])
    # ---- the key
    kparts = [p for p in body(key) if cut_x(p, xsec)]
    kb = [[ktf(t) for t in pts(p)] for p in kparts if p["part"] not in ("capstan head", "rest felt")]
    fill_rings(v, union_rings(kb), "m-black" if black else "m-key", None if black else P["key"])
    pin_x = plan_item(f"{key} balance pin")["circle"][0]
    g = pin_groove(key)
    if abs(xsec - pin_x) < g["w"] / 2:
        # P32: the groove is lined with 0.5T cloth on both SIDE faces; the far face is seen through the cut
        v.poly([ktf(t) for t in rect(g["y0"], g["y1"], g["z0"], g["z1"])], cls="void")
        v.poly([ktf(t) for t in rect(g["y0"], g["y1"], g["z0"], g["z1"])], cls="m-clothfar")
        for p in fx:
            if p["part"].startswith("balance pin"):
                hpoly(v, pts(p), "m-steel", P["steel"])
    for p in kparts:
        q = [ktf(t) for t in pts(p)]
        if p["part"] == "capstan head":
            hpoly(v, q, "m-steel", P["steel"])
            yc, d, zh, zlo, zb = capstan_shank(key)
            v.poly([ktf(t) for t in rect(yc - d / 2, yc + d / 2, zlo, zb)], cls="hid")
        elif p["part"] == "rest felt":
            v.poly(q, cls="m-felt")
    mf = kpt(kp, "magnet face")
    s_, n_ = magnet_polys(*mf)
    v.poly([ktf(t) for t in s_], cls="m-magS")
    v.poly([ktf(t) for t in n_], cls="m-magN")
    v.poly([ktf(t) for t in cloth_ring(K)], cls="m-cloth")
    # ---- the lever
    lparts = [p for p in body(lever) if cut_x(p, xsec)]
    lb = [[ltf(t) for t in pts(p, lever_pose)] for p in lparts if not p["part"].startswith(("steel", "felt"))]
    fill_rings(v, union_rings(lb), "m-lever", P["lever"])
    for p in lparts:
        q = [ltf(t) for t in pts(p, lever_pose)]
        if p["part"].startswith("steel"):
            hpoly(v, q, "m-steel", P["steel"])
        elif p["part"].startswith("felt"):
            v.poly(q, cls="m-felt")
    # torsion spring in the hub pocket (P18 / D05) + rods (S03 at K, S11 at L; both Ø4)
    if spring:
        draw_spring(v, lever[6:], xsec, pose=lever_pose if lever_pose in ("rest", "dip", "ff", "over", "service", "rigid0", "dip_rigid") else "rest",
                    tf=lever_tf, leg_tf=spring_leg_tf, hide=(fsol, gcut))
    pivot_mark(v, K, dn("S03", 0, "note") / 2)
    pivot_mark(v, L, dn("S11", 0, "note") / 2)
    # ---- full dip (settled, 1 N): dashed orange silhouettes
    if press:
        stroke_rings(v, union_rings([pts(p, "dip") for p in body(key)]), "pressed")
        # r4.4: the lever is drawn as cut by the plane (steel, core, hub section) — the side walls / top lips (z53 zone)
        # stand beside the pad, not under it, so they are a thin line behind the cut (else the lever seems to crush the pad)
        stroke_rings(v, union_rings([pts(p, "dip") for p in body(lever) if not cut_x(p, xsec)]), "pressed3")
        stroke_rings(v, union_rings([pts(p, "dip") for p in body(lever) if cut_x(p, xsec)]), "pressed")
    if sensor:
        zs = dns("S30")
        sensor_mark(v, dn("P29"), zs[1] if black else zs[0])
    if marks:      # pivot letters in the open space above the key / below the lever hub, leader to the rod
        for c, r_, bods, du in ((K, dn("S03", 0, "note") / 2, [key], -4.0), (L, dn("S11", 0, "note") / 2, [lever], 2.5)):
            yl = c[0] + du
            if c is K:
                ztop = max(z1 for b in bods for p in body(b) for z0, z1 in yslice(pts(p, "rest") if "side" not in p else pts(p), yl))
                zl = ztop + v.px(16)
            else:          # L: below the hub, above the rear shelf
                zl = SOL["z_shelf"] + v.px(26)
            a = math.atan2(zl - c[1], yl - c[0])
            v.line(c[0] + r_ * math.cos(a), c[1] + r_ * math.sin(a), yl, zl + (-v.px(2) if c is K else v.px(9)), cls="ld")
            v.text(yl, zl, "K" if c is K else "L", cls="ttl", anchor="middle", size_px=11)


# ---------------------------------------------------------------- sheet 1 / 2
def sheet_side(black):
    n_sheet = 2 if black else 1
    key, lever = ("key C#", "lever C#") if black else ("key D", "lever D")
    nm = "C#" if black else "D"
    kp = KP_B if black else KP_W
    xsec = plan_item(f"{key} balance pin")["circle"][0]
    z_top = dn("S18")
    z_bal = z_top + 20.0                       # balloon row (placement)
    n_leg = 18 + (1 if black else 0)                  # legend entries (below)
    U0, U1, V1 = -34.0, 300.0, z_bal + 8.0
    V0 = -44.0 - (math.ceil(n_leg / 3) * 15.5 + 6) * (U1 - U0) / 1480
    v = View(U0, V0, U1, V1, px_width=1480)
    P = pids(v)
    extra = ()
    if black:  # white neighbour heads cut by the plane (C head spans x0.73~22.77)
        extra = tuple(b for b in ("key C", "key D") if any(cut_x(p, xsec) for p in body(b)))
    side_scene(v, P, key, lever, xsec, black, extra_cut_keys=extra)
    zt = dns("S02")[2] if black else dns("S02")[0]
    ft = kpt(kp, "key front top")
    # r4.4 (R44-3): the dashed pose is the truly settled 1 N bottom WITH the pad (geometry side_dip, both colours) ->
    # the dip dimension ends on that drawn front point (bottom_held_1N); S23 is the design (kinematic) dip
    fd = kpt(kp, "key front top", "bottom_held_1N")
    dip = dns("S23")[1 if black else 0]
    v.dim_v(fd[1], ft[1], ft[0] - 10, text=f"딥 {F2(ft[1] - fd[1])} (1 N)", ext_from=(fd[0], ft[0]), tpos="left", size_px=10)
    v.text(ft[0] - 10 - v.px(6), (fd[1] + ft[1]) / 2 - v.px(3.5) - v.px(13), f"설계 {F(dip)} (S23)", cls="dt", anchor="end", size_px=9)
    pf = pad_face(black)
    plate = pts(fpart("top plate (ledge + bridge)"))
    bar = pts(fpart("pad bar"))
    y_plate0 = bbox(plate)[0]
    # ---- ordinate z (right)
    col = 218.0
    capy = kpt(kp, "capstan crown")[0]
    zf = [(dns("S01")[1], 212, "바닥판 밑 (S01)"), (dns("S01")[3], 212, "바닥판 윗면"),
          (SOL["z_shelf"], 209, "뒤 선반 (S10)"), (K[1], 143, "K (S03)"), (L[1], 207.6, "L (S11)"),
          (dns("S02")[1], 146, "건반 밑면 (S02)"), (zt, 146, ("흑건" if black else "백건") + " 윗면 (S02)"),
          (steel_top_rest(lever)[1], steel_top_rest(lever)[0], "강철 윗면 뒤, 쉼 (S12)"),
          (top_edge_rest(lever, "carrier side wall L")[1], top_edge_rest(lever, "carrier side wall L")[0], "캐리어 윗면 뒤, 쉼 (S13)"),
          (pf["z"][0], pf["y"][0], "패드 면 앞 (S15)"), (pf["z"][1], pf["y"][1], "패드 면 뒤"),
          (min(q[1] for q in bar), bbox(bar)[1], "패드 바 밑 (S16)"), (dn("S17"), plate_under_mid(dn("S17")), "패드 바 자리 (S17)"),
          (min(q[1] for q in plate if q[0] > dn("S17") + 100), plate_under_mid(min(q[1] for q in plate if q[0] > dn("S17") + 100)), "윗판 밑, 뒤 (P15)"),
          (z_top, 212, "윗판 윗면 = 맨 위 (S18)"),
          (dn("S07", 0), 192.76, "빔 밑면 (S07)"), (dn("S08", 2), capy, "캡스턴 꼭대기 (S08)")]
    ordz(v, zf, col, gap_px=12.5, label_px=9.5)
    # ---- ordinate y (bottom)
    # feature z of the extension lines = the drawn edge at that y (geometry), not a typed height
    front_keys = extra if black else (key,)
    z_front = min(z0 for k in front_keys for p in body(k) if cut_x(p, xsec) for z0, z1 in yslice(pts(p), 0.02))
    yf = [(0.0, z_front, "백건 앞끝"), (dn("P29"), 23.5, "자석·센서 (P29)"),
          (dn("P20", 0), 5, "밸런스 레일 앞 (P20)"), (dn("P32", 3), 11.3, "밸런스 핀 (P32)"), (K[0], 19.5, "K (S03)"),
          (dn("P26", 0), dns("S27")[1 if black else 0], "가림판 (P26)"), (y_plate0, plate_z(y_plate0 + 1e-3)[0][0], "윗판 앞 (P15)"),
          (dn("S13", 0), 33, "레버 앞면 0° (S13)"),
          (dn("P16", 0), pf["z"][0], "패드 (P16)"), (dn("P16", 1), pf["z"][1], ""), (bbox(bar)[1], min(q[1] for q in bar), "패드 바 끝 (P13)"),
          (capy, 31, "캡스턴 (S08)"), (dns("P19")[0], 18, "뒤 선반 (P19)"),
          (dns("S09")[2], 21.8, "꼬리 끝 (S09)"), (L[0], 29.2, "L (S11)"), (dns("S28")[0], 5, "뒷벽 (S28)"),
          (dns("A05")[0], 3, "프레임 뒤끝 (A05)")]
    if black:
        yf += [(dns("P30")[0], 23.5, "흑건 앞면 (P30)"), (dns("P31")[1], 12, "탭 앞면 (P31)")]
    else:
        yh = bbox(pts(part(key, "skin head")))[1]
        yf += [(dn("P31", 0), 11.2, "탭 앞면 (P31)"), (yh, 23.5, "헤드 끝 (P03)")]
    ordy(v, yf, -2.0, gap_px=12.5, label_px=9.5)
    # ---- balloons: rear cluster on the top row, front cluster on a middle row over the key
    mag = kpt(kp, "magnet face")
    pad = fpart(f"up-stop pad {nm}")
    pq = pts(pad)
    sg = spring_geom()
    wall = pts(fpart("rear wall"))
    hi = [("2", (K[0] + 1.3, K[1] + 1.4), K[0]), ("3", (dn("P32", 3), dn("P32", 4) - 3.0), dn("P32", 3) - 3),
          ("4", (bbox(pts(fparts("balance rail (lowered under the blocks)")[0]))[0] + 1.0, 12.0), 131.0),
          ("5", (capy + 1.6, dn("S08", 2) - 1.2), capy),
          ("6", (dns("P28")[0] + 1.2, SOL["z_shelf"] + 0.8), dns("P28")[0] + 4),
          ("7", (dn("S13", 0) + 1.0, 44.0), dn("S13", 0) + 4), ("8", (170.0, 40.0), 168.0),
          ("9", (L[0] - 2.6, L[1] - 2.6), L[0] - 6),
          ("18", ((sg["tp"][0] + sg["tip"][0]) / 2, (sg["tp"][1] + sg["tip"][1]) / 2), L[0] + 2),
          ("10", ((pq[0][0] + pq[2][0]) / 2, (pq[0][1] + pq[2][1]) / 2), 176.0),
          ("11", (160.0, (dn("S17") + plate_z(160.0)[0][0]) / 2), 156.0),
          ("12", (196.0, (z_top + plate_z(196.0)[0][0]) / 2), 196.0), ("13", (sum(dns("P26")[:2]) / 2, 58.0), 144.0)]
    balloon_row(v, hi, z_bal, 118.0, 226.0, gap_px=23)
    mid_z = zt + 17.0
    tab = fpart(f"tab {nm}")
    ff = fpart(f"black front felt {nm}") if black else fpart("white front felt 3T")
    mid = [("1", (100.0, zt - 1.0), 100.0), ("14", (mag[0] - 1.0, mag[1] + 1.0), mag[0] - 3),
           ("15", (mag[0] + 6.0, 12.5 if not black else 10.5), mag[0] + 6),
           ("16", (bbox(pts(tab))[0] + 3.0, 20.0), bbox(pts(tab))[0] + 3.0),
           ("17", (bbox(pts(ff))[0] + 1.5, bbox(pts(ff))[3] - 1.0), bbox(pts(ff))[0] - 6)]
    for i, k_ in enumerate(extra):          # white neighbour head(s) cut by the plane (hatched as a cut key)
        sk_ = next(p for p in body(k_) if p["part"] == "skin head")
        y0_, y1_, z0_, z1_ = bbox(pts(sk_))
        mid.append((str(19 + i), ((y0_ + y1_) / 2, (z0_ + z1_) / 2), (y0_ + y1_) / 2 - 10.0))
    balloon_row(v, mid, mid_z, -24.0, 120.0, gap_px=23)
    lb = _labels()
    leg = [("1", f"{'흑건 C#' if black else '백건 D'} (PETG 한 덩어리, 단면)"), ("2", f"건반 봉 {lb['rod4']} (S03, P21) + 노치 천"),
           ("3", f"밸런스 핀 {lb['pin']} + 블록 밑 홈 (P32)"), ("4", f"밸런스 레일 {lb['rail_z']} + 봉 받침 (뒤에 보임, P20·S05)"),
           ("5", f"캡스턴 {lb['cap']} 버튼헤드 (S08, D02)"), ("6", f"쉼 펠트 {lb['rest_felt']} + 뒤 선반 (P28, S10)"),
           ("7", "레버 캐리어 PETG + 손톱 턱 (S13, D08)"), ("8", f"강철 블록 SS400 (S12) + 밑 펠트 {lb['strip_felt']} (S14)"),
           ("9", f"레버 봉 {lb['rodL']} + 허브 {lb['hub']} (S11)"), ("10", f"업스톱 패드: 폼 {lb['foam']} + 펠트 {lb['pad_felt']} + 쐐기 (P16·P17)"),
           ("11", f"패드 바 {lb['bar_t']} 계단형 (P13·S16·S17)"), ("12", f"윗판·핀·뒷벽 (프레임 한 몸, P15·S18·S28)"),
           ("13", "가림판 띠 + 걸이 (P26, S27)"), ("14", f"자석 {lb['magnet']} + 센서 소자 (P29, S30)"),
           ("15", "센서 바 (v3) · 바닥판 · EVA (S01)"), ("16", f"가이드 탭 + 천 {lb['cloth']} + 키퍼 훅·펠트 (P31, S20)"),
           ("17", ("흑 " if black else "") + f"앞 {lb['front_felt']} (" + ("S22" if black else "S21") + ")"),
           ("18", f"비틀림 보조 스프링 미스미 {SOL['spring']['part']} d{F(sg['d'])}·ID {F(sg['ID'])} (두 다리 잘라 씀) → 뒷벽 홈 (P18, D05)")]
    leg += [(str(19 + i), f"이웃 백건 {k_[4:]} 헤드 (x{F2(xsec)} 평면에 잘림, 단면)") for i, k_ in enumerate(extra)]
    legend(v, leg, -30.0, -44.0, cols=3, col_w=112.0, line_px=15.5, size_px=10.5)
    scalebar(v, 262.0, V0 + 3.0, 20)
    det = detail_specs(black)
    for tag, sp in det.items():
        u0, u1, w0, w1 = sp["win"]
        v.rect(u0, w0, u1 - u0, w1 - w0, cls="phan")
        v.text(u0 + 0.6, w1 + v.px(3), tag, cls="ttl", anchor="start", size_px=11)
    dets = [make_detail(black, key, lever, xsec, extra, tag, sp) for tag, sp in det.items()]
    rows = [[v], dets[:2], dets[2:]]

    # angles of the DRAWN dashed pose (settled 1 N bottom polygons), from rest; S24 / S25 are the rigid kinematic bottom
    def _ang(p, a_, b_):
        q, r = pts(p, a_), pts(p, b_)
        return math.degrees(math.atan2(q[1][1] - q[0][1], q[1][0] - q[0][0]) - math.atan2(r[1][1] - r[0][1], r[1][0] - r[0][0]))
    # lever from the settled dip polygon; rigid kinematic bottoms quoted FROM REST (S24 is from rest; S25 is from 0 deg)
    # r4.5 fix: the key angle is the model's own number (metrics clear.dip front_angle, 4.046 -> 4.05 / 6.08) through the
    # one rounding helper, not recomputed from 2-decimal key_points (that gave 4.04 = the old r4.3 rigid value)
    ka = kit.M["clear"]["dip"]["black" if black else "white"]["front_angle"]
    la = -_ang(part(lever, "steel block"), "dip", "rest")
    la_rr = -_ang(part(lever, "steel block"), "dip_rigid", "rest")
    ka_r, la_r = dns("S24")[1 if black else 0], dns("S25")[1 if black else 0]
    title = f"도면 {n_sheet}. {'흑건 C#' if black else '백건 D'} 측면 단면 — 정지(실선) / 끝까지 누름(주황 점선)"
    sub = (f"단면 x = {F2(xsec)} ({nm} 밸런스 핀·자석 중심, +x 쪽에서 봄) · 단위 mm · z = 0 책상, y = 0 백건 앞끝 · 숫자 = geometry.json (괄호 = 치수표 번호)\n"
           f"점선 = 1 N으로 끝까지 누른 정착 바닥(패드 눌림 포함, geometry side_dip — 백·흑 같은 방식, S24·S25): 쉼에서 건반 {F2(ka)}°(앞끝, 노치가 봉에 앉는 것 포함)·레버 {F2(la)}° "
           f"· K ({F2(K[0])}, {F2(K[1])}), L ({F2(L[0])}, {F2(L[1])})\n"
           f"누른 레버 = 이 단면(강철·캐리어 속) 굵은 점선, 옆벽·위 립(z53 구역, 패드 옆)은 가는 점선 · 가는 실선 = 단면 뒤에 보이는 모서리(자기 옆벽·레버 옆벽·봉 받침) · "
           f"숨은선 = 캡스턴 나사 · 레버 z = 그린 쉼 자세 값 (0° 값은 도면 7) · 맨 위 {lb['top']}")
    base = os.path.join(OUT, f"d{n_sheet:02d}_{'black_Csharp' if black else 'white_D'}_side")
    page(rows, base, title, sub)
    SHEETS.append(dict(n=n_sheet, title_ko=f"{'흑건' if black else '백건'} 측면 단면 ({nm})",
                       caption_ko=(f"{'흑건 C#' if black else '백건 D'}를 x{F2(xsec)}(밸런스 핀·자석 중심)에서 자른 측면. 실선 = 정지(레버 정착 쉼 각), "
                                   f"주황 점선 = 1 N으로 끝까지 누른 정착 바닥(패드 눌림 포함; 쉼에서 건반 {F2(ka)}°, 레버 {F2(la)}°; 딥 치수도 이 자세의 앞끝까지, S23 설계 {F(dip)}), "
                                   f"누른 레버는 단면(강철·캐리어 속)만 굵게, 옆벽·위 립은 가는 점선. "
                                   f"r4: 업스톱은 윗판 밑 패드 바의 쐐기에 붙인 폼 {lb['foam']} + 펠트 {lb['pad_felt']} 패드가 드러난 강철 윗면을 받음(레일·손나사·커버 없음, 맨 위 {lb['top']}); "
                                   f"허브의 비틀림 스프링(r4.5: 미스미 {SOL['spring']['part']}, 두 다리를 잘라 씀 — r4.5 고침: {spring_txt()['short']}은 허브의 {spring_txt()['groove']}에 갇히고, 긴 다리는 뒷벽 {F(SOL['spring']['groove'][3])} 홈({spring_txt()['dx']} 가운데))이 뒷벽 홈을 민다. "
                                   f"오른쪽 z·아래 y 좌표는 모두 geometry.json 값이고 괄호는 치수표 번호. "
                                   f"확대 A 봉·스냅 노치·핀, B 캡스턴·쉼·허브 주머니 Ø{F(SOL['spring']['pocket'][0])}·가둠 홈·스프링, C 업스톱(패드·쐐기·패드 바 계단 y{F(bar_steps()[0])}/{F(bar_steps()[1])}·윗판·가림판), D 앞 멈춤·키퍼."
                                   + (" 19 = 단면에 잘린 이웃 백건 C 헤드." if black else "")),
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))


def detail_specs(black):
    """details: world window, px/mm, margins (left, right, bottom, top) in px, number of callouts."""
    z_top = dn("S18")
    return {"A": dict(win=(130.8, 150.0, 16.0, 31.0), s=27.0, m=(165, 24, 152, 34), n=6),
            "B": dict(win=(176.0 if black else 180.0, 212.5, 16.5, 44.0), s=16.0 if black else 17.0, m=(24, 190, 142, 34), n=9),
            "C": dict(win=(142.5, 187.0, 43.0, z_top + 1.5), s=12.0, m=(165, 170, 160, 34), n=8),
            "D": dict(win=(49.5, 95.5, 9.0, 57.5) if black else (-2.5, 29.5, 9.0, 45.5), s=10.0 if black else 12.6,
                      m=(165, 24, 132, 34), n=6)}


def make_detail(black, key, lever, xsec, extra, tag, sp):
    u0, u1, w0, w1 = sp["win"]
    s = sp["s"]
    ml, mr, mb, mt = sp["m"]
    mb = mb + 14.5 * sp["n"] + 12
    v = View(u0 - ml / s, w0 - mb / s, u1 + mr / s, w1 + mt / s, px_width=(u1 - u0) * s + ml + mr, pad_px=4)
    P = pids(v)
    i0 = clip_begin(v)
    side_scene(v, P, key, lever, xsec, black, extra_cut_keys=extra, marks=False)
    clip_end(v, i0, u0, u1, w0, w1)
    panel_title(v, u0 - ml / s + v.px(4), w1 + v.px(12), f"확대 {tag}", size_px=13)
    scalebar(v, u0 + v.px(80), w1 + v.px(14), 5 if (u1 - u0) < 40 else 10)
    items = globals()[f"detail_{tag}"](v, black, KP_B if black else KP_W, sp, key, lever)
    callouts(v, items, u0 - ml / s + v.px(8), w0 - v.px(sp["m"][2] - 6))
    return v


def in_win(feats, w0, w1):
    """ordinate features of a clipped detail: a feature height outside the window is moved to the window edge
    (the part is cut by the frame there), so the extension line never runs outside the detail."""
    return [(a, min(max(b, w0), w1), lab) for a, b, lab in feats]


def detail_A(v, black, kp, sp, key, lever):
    """rod / snap notch / balance pin / cradle."""
    u0, u1, w0, w1 = sp["win"]
    r_out, r_in = dn("S04", 0), dn("S04", 2)
    blk = pts(part(key, "balance block"))
    zb = block_bottom_z(key)
    lipz = dn("S04", 3)
    ylips = sorted(q[0] for q in blk if abs(q[1] - lipz) < 1e-6)
    g = pin_groove(key)
    cr = dns("S05", "ref")      # [139.24, 142.76, 2.05]
    cy = cradle_y()             # [138.44, 139.24, 142.76, 143.56]
    rail = pts(fparts("balance rail (lowered under the blocks)")[0])
    # r4.4 fix 2 (P20): the rail piece under this key's block has a pocket behind the pin row (exported polygon)
    xp_ = pcirc(f"{key} balance pin")[0]
    rpk = next(p for p in fixed() if p["part"].startswith("balance rail (lowered") and "pocket" in p["part"] and cut_x(p, xp_))
    rpq = pts(rpk)
    pk_z = yslice(rpq, bbox(rpq)[1] - 0.05)[-1][1]
    pk_y = min(q[0] for q in rpq if abs(q[1] - pk_z) < 1e-6)
    ordz(v, [(dns("P20")[3], dns("P20")[0], "레일 (P20)"), (pk_z, bbox(rpq)[1], "레일 포켓 (P20)"), (dn("S05", 1), K[0], "받침 바닥 (S05)"),
             (dn("S05", 0), cy[0], "받침 입술 (S05)"), (lipz, ylips[0], "노치 입술 밑 (S04)"), (K[1], K[0] - 2.0, "K"),
             (zb, g["y0"], "블록 밑"), (dn("P32", 4), g["y0"] + 0.5, "핀 꼭대기 (P32)"),
             (K[1] + dn("S03", 0, "note") / 2, K[0], "봉 꼭대기"), (K[1] + r_out, K[0], "노치 천장"),
             (g["z1"], g["y0"], "핀 홈 천장 (P32)")], u0 - 0.3, side="left", gap_px=13, label_px=9.5, lo=w0 - 1.0, hi=w1)
    ordy(v, in_win([(g["y0"], zb, "블록 앞·홈 (P32)"), (dn("P32", 3), dn("P32", 4) - 12.0, "핀"), (g["y1"], zb, "홈 끝"),
             (ylips[0], lipz, "입술"), (cy[0], dns("P20")[3], "받침"), (cr[0], dn("S05", 0), ""), (K[0], dn("S05", 1), "K"),
             (cr[1], dn("S05", 0), ""), (cy[-1], dns("P20")[3], "받침"), (ylips[-1], lipz, "입술"), (bbox(rail)[1], dns("P20")[3], "레일 뒤"),
             (pk_y, pk_z, "포켓")], w0, w1),
         w0 - 0.2, gap_px=13, label_px=9.5, lo=u0 - 1.5)
    n4 = dns("S04", "note")     # [223, 3.82, 0.07, 0.20, 0.80, 1, 2, 0]
    p32 = dns("P32")            # [2338, 2.0, 12, 135.3, 23.3, 0.1]
    engage = dn("P32", 4) - zb
    return [("a", (K[0] - r_out * 0.62, K[1] + r_out * 0.78), (-40, 40),
             f"노치 R{F2(r_out)} + 부싱 천 {F(dn('S04', 1))}T → 유효 R{F2(r_in)}, 감쌈 {F(n4[0])}°, 입구 {F2(n4[1])} (S04·D01)"),
            ("b", (K[0] + 0.9, K[1] - 1.1), (38, -26), f"건반 봉 Ø{F(dn('S03', 0, 'note'))} SUS304, 받침 위 CA 고정 (S03·P21)"),
            ("c", (p32[3], (dns("P20")[3] + zb) / 2 - 1.0), (-34, -10), f"밸런스 핀 ISO {F(p32[0])} Ø{F(p32[1])}×{F(p32[2])}, 꼭대기 z{F2(p32[4])} ±{F(p32[5])}, 블록 밑 위로 물림 {F2(engage)} (P32)"),
            ("d", (g["y0"] + 0.4, g["z1"] - 0.6), (-36, 18),
             f"핀 홈: 출력 폭 {F(g['w'])} (천 {F(g['cloth'])}T 양 옆면 → {F(g['w_cloth'])}; 연한 주황 = 뒤 옆면 천) × 깊이 {F(g['z1'] - g['z0'])}, 앞이 열림, 핀 ↔ 입술 벽 {F2(g['lip_wall'])} (P32)"),
            ("e", (cy[-1] - 0.2, dn("S05", 0) - 0.3), (30, -34), f"봉 받침 (블록 사이, 뒤에 보임) R{F2(cr[2])}, 입술 z{F(dn('S05', 0))} (S05·P20)"),
            ("f", (ylips[-1] - 0.1, lipz + 0.05), (34, 16), f"쉼에서 입술–봉 틈 {F2(n4[2])} · 들림 {F2(n4[3])}에서 닿고 {F2(n4[4])}에서 빠짐 · 빠짐 힘 {F(n4[5])}~{F(n4[6])} N (S04·D15)")]


def detail_B(v, black, kp, sp, key, lever):
    u0, u1, w0, w1 = sp["win"]
    capy = kpt(kp, "capstan crown")[0]
    yc, d, zh, zlo, zb = capstan_shank(key)
    beam = pts(part(key, "beam"))
    tail = pts(part(key, "thin tail"))
    shelf = fparts("rear shelf")[0]
    s11 = dns("S11", "note")    # [4, 304, 4.3, 3.9, 4.0]
    hub_r = s11[2]
    cph = pts(part(key, "capstan head"))
    ztail = max(q[1] for q in tail)
    sg = spring_geom()
    ordz(v, [f for f in [(bbox(pts(shelf))[2], 209, "선반 밑"), (SOL["z_shelf"], 209, "선반 윗면 (S10)"),
             (dn("S07", 0), yc, "빔 밑 (S07)"), (ztail, max(q[0] for q in tail if abs(q[1] - ztail) < 1e-6), "꼬리 윗면 (S09)"),
             (zb, yc, "캡스턴 자리"), (dn("S07", 1), max(q[0] for q in beam if abs(q[1] - dn("S07", 1)) < 1e-6), "빔 윗면 (S07)"),
             (zh, max(q[0] for q in cph), "머리 밑"), (dn("S08", 2), capy, "캡스턴 꼭대기 (S08)"), (L[1], L[0], "L (S11)"),
             (L[1] + hub_r, L[0], "허브 위"), (sg["groove"][2], sg["groove"][1], "스프링 홈 밑 (P18)")] if u0 <= f[1] <= u1 + 1.0 and w0 <= f[0] <= w1],
         u1 + 0.3, gap_px=13, label_px=9.5, lo=w0 - 0.5, hi=w1 + 1.0)
    rf = pts(part(key, "rest felt"))
    ordy(v, [(capy, dn("S08", 2), "캡스턴 (S08)"), (bbox(beam)[1], dn("S07", 0), "빔 끝"),
             (bbox(pts(shelf))[0], SOL["z_shelf"], "선반 앞 (S10)"), (bbox(rf)[0], bbox(rf)[2], "쉼 펠트 (P28)"),
             (bbox(rf)[1], bbox(rf)[2], "꼬리 끝 (S09)"), (L[0], L[1] - hub_r, "L"), (dns("S28")[0], 30.0, "뒷벽 (S28)")],
         w0 - 0.2, gap_px=13, label_px=9.5, lo=u0)
    fs = dns("S14")             # [176.5, 192.0, 31.0, 33.0]
    d02 = dns("D02", "value")
    s09 = dns("S09", "note")
    lip = pts(part(lever, "carrier rear floor"), "rest")
    return [("a", (capy + 1.2, dn("S08", 2) - 0.3), (26, 30), f"캡스턴 M{F(d)}×{F(zh - zlo)} ISO 7380 버튼헤드, 꼭대기 z{F(dn('S08', 2))} (S08)"),
            ("b", (yc, (zlo + zb) / 2), (-30, -20), f"나사 M{F(d)} 숨은선 · 너트 트랩: 옆에서 끼움 + 위 Ø{F(d02[1])} 자가 잠김 구멍 (D02)"),
            ("c", ((fs[0] + fs[1]) / 2 - 3.0, fs[2] + 0.4), (-26, 26), f"캐리어 밑 펠트 띠 {F(fs[3] - fs[2])}T, y{F(fs[0])}~{F(fs[1])}, 폭 {F(dns('S14', 'ref')[0])}, 흑연 (S14)"),
            ("d", (bbox(rf)[0] + 0.9, bbox(rf)[2] + 0.8), (-22, -26), f"쉼 펠트 {F(dns('P28', 'note')[0])}T + {_labels()['punch']} (P28·D10)"),
            ("e", (bbox(pts(shelf))[0] + 6.0, SOL["z_shelf"] - 1.0), (18, -24), f"뒤 선반 윗면 z{F2(SOL['z_shelf'])} (S10) + 리브 (P19)"),
            ("f", (L[0] + hub_r * 0.72, L[1] - hub_r * 0.72), (22, -22), f"허브 R{F(hub_r)}, 구멍 Ø{F(s11[3])} 출력 → Ø{F(s11[4])} 드릴 · 레버 봉 Ø{F(s11[0])} SUS304 (S11·P22)"),
            ("g", (L[0] + 0.3, L[1] + sg["r_m"] + 0.3), (-40, 36),
             f"비틀림 스프링 미스미 {SOL['spring']['part']}: d{F(sg['d'])} ID {F(sg['ID'])} 몸통 {F(sg['n'])}권, 허브 주머니 Ø{F(sg['pocket'][0])}×{F(sg['pocket'][1])}, "
             f"{spring_txt()['slot']} + {spring_txt()['window']}; 긴 다리 {F(sg['leg'])} → 뒷벽 홈 (P18·D05)"),
            ("h", tuple(SOL["spring"]["short_leg_groove"]["exit_bearing"]), (-34, 20),
             f"r4.5 고침 {spring_txt()['groove']}: {spring_txt()['short']}이 갇혀 {spring_txt()['contacts']}로 토크를 받음 (P18)"),
            ("i", (bbox(tail)[1] - 3.0, max(q[1] for q in tail) - 0.5), (-12, 30), f"얇은 꼬리 {F(s09[0])}T, 끝 모따기 {F(dns('S09')[3])} (S09)")]


def detail_C(v, black, kp, sp, key, lever):
    """up-stop: exposed steel top -> felt + foam pad -> wedge -> pad bar -> top plate (compression only)."""
    u0, u1, w0, w1 = sp["win"]
    nm = key[4:]
    pf = pad_face(black)
    pad = fpart(f"up-stop pad {nm}")
    lay, info = pad_layers(pad)
    wedge = pts(fpart(f"pad wedge {nm}"))
    bar = pts(fpart("pad bar"))
    grip = pts(fpart("pad bar grip"))
    plate = pts(fpart("top plate (ledge + bridge)"))
    hook = pts(fpart("cover curtain hook"))
    st_r = steel_top(lever, "front", "rest")
    st_d = steel_top(lever, "front", "dip")
    st_f = steel_top(lever, "front", "ff")
    tab_r = pts(part(lever, "fingernail tab"), "rest")
    z_seat = dn("S17")
    z_bar0 = min(q[1] for q in bar)
    z_groove = plate_z(bbox(plate)[0] + 1e-3)[0][0]
    z_ledge = min(q[1] for q in hook)
    # pad thickness: aligned dimensions along the rear edge (normal to the face); then the vertical stack above
    # the pad back at its rear corner: wedge / bar / plate above the seat
    back_r = info["back"][1]
    face_r = info["face"][1]
    nu = ((back_r[0] - face_r[0]) / (info["felt"] + info["foam"]), (back_r[1] - face_r[1]) / (info["felt"] + info["foam"]))
    q = (face_r[0] + nu[0] * info["felt"], face_r[1] + nu[1] * info["felt"])
    dim_aligned(v, face_r, q, 30, f"{F(info['felt'])} 펠트")
    dim_aligned(v, q, back_r, 30, f"{F(info['foam'])} 폼 (면에 수직)")
    uc = u1 + v.px(14)
    z = back_r[1]
    for t, lab in ((z_bar0 - back_r[1], "쐐기 뒤"), (z_seat - z_bar0, "패드 바"), (dn("S18") - z_seat, "윗판")):
        v.dim_v(z, z + t, uc, text="", ext_from=(back_r[0] + 0.3, bbox(plate)[1]), size_px=9)
        v.text(uc + v.px(8), z + t / 2 - v.px(3.5), f"{F2(t)} {lab}", cls="dt", anchor="start", size_px=9.5)
        z += t
    ordz(v, [(st_r[1], st_r[0], "강철 윗면 앞, 쉼"), (st_d[1], st_d[0], "강철 윗면 앞, 1 N 바닥"),
             (pf["z"][0], pf["y"][0], "패드 면 앞 (S15)"), (st_f[1], st_f[0], "ff 최대"),
             (z_bar0, bbox(bar)[0] + 1.0, "패드 바 밑·손잡이 밑"), (z_seat, pf["y"][0], "패드 바 자리 (S17)"),
             (z_groove, bbox(plate)[0], "윗판 앞 홈 밑 (P15)"), (z_ledge, bbox(hook)[0], "걸이 턱"), (dn("S18"), bbox(plate)[0] + 2.0, "맨 위 (S18)"),
             (dns("S27")[1 if black else 0], dn("P26", 0), "가림판 밑 (S27)")],
         u0 - 0.3, side="left", gap_px=13, label_px=9.5, lo=w0 - 1.0, hi=w1 + 1.0)
    yc_front = front_y_at(pts(part(lever, "carrier core"), "rest"), w0 + 1.0)
    ys_front = front_y_at(pts(part(lever, "steel block"), "rest"), w0 + 1.0)
    ordy(v, in_win([(dn("P26", 0), 60.0, "가림판 (P26)"), (dn("P26", 1), 60.0, ""), (bbox(plate)[0], z_groove, "윗판 앞 (P15)"),
             (bbox(grip)[1], z_bar0, "손잡이"), (yc_front, w0, "캐리어 앞"),
             (ys_front, w0, "강철 앞"), (bar_steps()[0], z_bar0, "패드 바 밑 계단"), (bar_steps()[1], z_seat, "윗 계단"),
             (SOL["y_bar_step"], z_groove, "윗판 홈 끝"), (dn("P16", 0), pf["z"][0], "패드 (P16)"),
             (dn("P16", 1), pf["z"][1], ""), (bbox(bar)[1], z_bar0, "패드 바 끝")], w0, w1),
         w0 - 0.2, gap_px=13, label_px=9.5, lo=u0)
    # the ff pose is not drawn: mark its steel-top point (small orange ring) so the 'ff 최대' ordinate lands on it
    v.circle(st_f[0], st_f[1], v.px(2.6), cls="pressed2")
    gap = kp["pad_face"]["gap"]
    first = "레버가 패드에 먼저" if gap < 0 else "건반이 앞 펠트에 먼저"
    wd = SOL["wedge"]["b" if black else "w"]
    d11n = dns("D11", "note")
    return [("a", ((tab_r[0][0] + tab_r[2][0]) / 2, (tab_r[0][1] + tab_r[2][1]) / 2), (-28, 20),
             f"손톱 턱 (캐리어 앞 위, D08) — 빼기 때 레버를 손으로 듦 · 캐리어 앞 R{F(dn('D08'))}은 접점 아님"),
            ("b", (dn("P16", 0) - 4.0, _on_line(st_r, steel_top(lever, "rear", "rest"), dn("P16", 0) - 4.0) - 0.1), (-6, -40),
             f"드러난 강철 윗면 (윗 립 사이 {F(dns('P16')[3])}) = 업스톱 접점, 모따기 없음 (S12)"),
            ("c", ((info["face"][0][0] + info["back"][1][0]) / 2, (info["face"][0][1] + info["back"][1][1]) / 2), (30, 26),
             f"패드: 미세셀 우레탄 폼 {F(info['foam'])}T + 펠트 {F(info['felt'])}T, 폭 {F(dns('P16')[2])}, e ≤ {F2(d11n[0])} (P16·D11)"),
            ("d", (st_d[0] + 3.0, st_d[1] - 0.5), (-8, -46), f"1 N 바닥: 강철 ↔ 패드 면 {F2(gap)} → {first} (S15)"),
            ("e", ((wedge[0][0] + wedge[1][0]) / 2, (wedge[1][1] + wedge[2][1]) / 2), (36, 10),
             f"쐐기 (패드 바와 한 몸) {kit.FR(wd[0], wd[1])}, 면 기울기 {F2((KP_B if black else KP_W)['pad_face']['tilt_deg'])}° (P17)"),
            ("f", (158.0, (z_seat + z_groove) / 2), (10, 26), f"패드 바 {_labels()['bar_t']} 계단형, 앞 손잡이; 윗판 밑 L 레일 립 위로 앞에서 밀어 넣음, 잎 혀가 자리로 밀어 올림 (P13·S16)"),
            ("g", (bbox(plate)[0] + 12.0, dn("S18") - 1.0), (-4, 22), f"윗판 z{F2(dn('S18'))} = 맨 위, 패드 힘은 누르는 힘으로만 (P15·S18)"),
            ("h", (sum(dns("P26")[:2]) / 2, 55.0), (-26, -18), f"가림판 띠 {F2(dn('P26', 1) - dn('P26', 0))}T + 걸이, 밑 z{F(dns('S27')[1 if black else 0])} (P26·S27)")]


def detail_D(v, black, kp, sp, key, lever):
    u0, u1, w0, w1 = sp["win"]
    nm = "C#" if black else "D"
    tab = fpart(f"tab {nm}")
    hook = fpart(f"keeper hook {nm}")
    kf = fpart(f"keeper felt {nm}")
    cb = pts(part(key, "crossbar"))
    ff = fpart(f"black front felt {nm}") if black else fpart("white front felt 3T")
    fq = pts(ff)
    fr = fpart(f"black stop rail {nm}") if black else fpart("white front rail")
    floor_k = pts(part(key, "stop floor" if black else "down-stop floor"))
    kpnt = kpt(kp, "keeper point")
    zt = dns("S02")[2] if black else dns("S02")[0]
    feats = [(fq[0][1], fq[0][0], "레일 윗면 앞"), (fq[1][1], fq[1][0], "레일 윗면 뒤"), (fq[3][1], fq[3][0], "펠트 윗면 앞"),
             (fq[2][1], fq[2][0], "펠트 윗면 뒤 (" + ("S22" if black else "S21") + ")"), (dns("S02")[1], floor_k[0][0], "건반 밑 (S02)"),
             (bbox(floor_k)[3], floor_k[0][0], "바닥판 위"), (bbox(cb)[3], bbox(cb)[0], "크로스바 위"),
             (dn("S20"), bbox(pts(kf))[0], "키퍼 펠트 밑 (S20)"), (bbox(pts(hook))[3], bbox(pts(hook))[0], "훅 위"),
             (zt, dns("P30")[1] if black else 0.0, "윗면 (S02)")]
    ordz(v, feats, u0 - 0.3, side="left", gap_px=13, label_px=9.5, lo=w0 - 1.0, hi=w1 + 0.5)
    yfe = [(fq[0][0], fq[0][1], "펠트 앞"), (floor_k[0][0], 23.5, "바닥판"), (bbox(floor_k)[1], 23.5, ""),
           (fq[1][0], fq[1][1], "펠트 뒤"), (bbox(cb)[0], 23.5, "크로스바"), (bbox(pts(kf))[0], dn("S20"), "훅"),
           (bbox(cb)[1], 23.5, ""), (bbox(pts(tab))[0], 12.0, "탭 면 (P31)"), (bbox(pts(tab))[1], 12.0, "탭 뒤")]
    if black:
        yfe += [(dns("P30")[0], 23.5, "흑건 앞 (P30)"), (bbox(pts(fr))[0], 5.0, "흑 레일")]
    else:
        yfe += [(0.0, 41.5, "앞끝")]
    ordy(v, in_win(yfe, w0, w1), w0 - 0.2, gap_px=13, label_px=9.5, lo=u0 - 2.0)
    kg = dn("S20", 0, "ref")
    v.dim_v(kpnt[1], dn("S20"), bbox(cb)[0] - v.px(10), text=f"{F(kg)}", ext_from=(bbox(cb)[0], bbox(pts(kf))[0]), size_px=9)
    tg = dn("P31", 0, "ref")
    v.dim_h(bbox(cb)[1], bbox(pts(tab))[0], dns("S02")[1] - v.px(30), text=f"{F(tg)}", ext_from=(dns("S02")[1], dns("S02")[1] - 2.0),
            size_px=9, tpos="right")
    fl = "S22" if black else "S21"
    p34 = dns("P34")
    return [("a", ((fq[0][0] + fq[1][0]) / 2, (fq[0][1] + fq[2][1]) / 2 + 0.6), (30, 26),
             f"{'흑 ' if black else ''}앞 {_labels()['front_felt_lr']}, y{F(fq[0][0])}~{F(fq[1][0])}, 딥에서 바닥판과 평행 ({fl})"),
            ("b", ((floor_k[0][0] + bbox(floor_k)[1]) / 2, bbox(floor_k)[3] - 0.3), (22, 26),
             f"건반 바닥판 (멈춤면) y{F(floor_k[0][0])}~{F(bbox(floor_k)[1])}, {F(bbox(floor_k)[3] - bbox(floor_k)[2])}T"),
            ("c", ((bbox(cb)[0] + bbox(cb)[1]) / 2, bbox(cb)[3] - 0.5), (-4, -30), f"크로스바 y{F(bbox(cb)[0])}~{F(bbox(cb)[1])}, 윗면 z{F(bbox(cb)[3])}"),
            ("d", (bbox(pts(kf))[0] + 1.0, dn("S20") + 1.0), (-26, 24), f"키퍼 훅 + 펠트 {_labels()['keeper_felt']}, 쉼 틈 {F(kg)} (연주 중 무접촉) · 폭 {F(p34[0])} (S20·P34)"),
            ("e", (bbox(pts(tab))[0] + 0.25, 17.5), (26, -8), f"가이드 탭 앞면 천 {F(dn('P31', 0, 'note'))}T = 뒤쪽 y 스톱, 크로스바 뒤 +{F(tg)} (P31)"),
            ("f", (bbox(pts(fr))[0] + (6.0 if black else 12.0), bbox(pts(fr))[2] + 5.3), (22, 14), "앞 레일 (프레임 한 몸)" if not black else "흑 멈춤 레일 (프레임 한 몸)")]


# ================================================================ sheet 3: octave module plan
WHITE = ["C", "D", "E", "F", "G", "A", "B"]
BLACK = ["C#", "D#", "F#", "G#", "A#"]
ORDER = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def ppoly(name):
    return [tuple(q) for q in plan_item(name)["poly"]]


def pcirc(name):
    return plan_item(name)["circle"]


def lever_top_features(xc=0, black=False, src=None):
    """plan features of a lever seen from above (rigid0 side polygons): steel visible between the top lips
    (lips 0.8 inward, exported lip parts D07) from the front cap end; full steel width where the lips are cut."""
    lw = dn("P11") / 2
    cw = dns("P11", "note")[1]                     # side wall 0.8 ('강철 9 + 옆벽 0.8×2')
    core = pts(part("lever D", "carrier core"), "rigid0")
    zt = dn("S12", 3)                              # steel top z52 (0 deg)
    cap_end = max(q[0] for q in core if abs(q[1] - max(t[1] for t in core)) < 1e-6)   # front cap over the steel ends
    lip_end = top_lip_spans()[0][1]                # r4.4: from the exported lip parts
    lip_in = top_lip_wh()[0]
    stl = pts(part("lever D", "steel block"), "rigid0")
    s_rear = max(q[0] for q in stl)
    s_front = min(q[0] for q in stl)
    return dict(lw=lw, cw=cw, cap_end=cap_end, lip_end=lip_end, lip_in=lip_in, s_rear=s_rear, s_front=s_front,
                steel_hw=lw - cw, zt=zt)


def dovetail_polys():
    """D09: root 6 / tip 9 / depth 4; female groove in the left edge (opening = root), male tail on the right edge."""
    r, t, dpt = dns("D09")[:3]
    out = []
    for yr in ((dns("D09", "ref")[0], dns("D09", "ref")[1]), (dns("D09", "ref")[2], dns("D09", "ref")[3])):
        yc = sum(yr) / 2
        fem = [(0.0, yc - r / 2), (dpt, yc - t / 2), (dpt, yc + t / 2), (0.0, yc + r / 2)]
        W = dn("P01")
        male = [(W, yc - r / 2), (W + dpt, yc - t / 2), (W + dpt, yc + t / 2), (W, yc + r / 2)]
        out.append((fem, male))
    return out


def plan_cut_z():
    """plan section height: half-way between the highest lever top at rest and the lowest up-stop pad face,
    rounded to 0.5 (so the levers are seen from above and the pads / pad bars / top plate are above the cut)."""
    lev_top = max(q[1] for n in ORDER for p in body(f"lever {n}") for q in pts(p, "rest"))
    pad_lo = min(SOL["pad_face_w"]["z"] + SOL["pad_face_b"]["z"])
    return round((lev_top + pad_lo) / 2 * 2) / 2, lev_top, pad_lo


def z_range(p):
    q = pts(p)
    return min(t[1] for t in q), max(t[1] for t in q)


def sheet_plan():
    W = dn("P01")
    zc, lev_top, pad_lo = plan_cut_z()
    U0, U1, V0, V1 = -40.0, 242.0, -47.0, 268.0
    v = View(U0, V0, U1, V1, px_width=1480)
    P = pids(v)
    sg = spring_geom()
    # ---- frame parts cut by the plane z = zc (fins, rear wall with the spring grooves, curtain strip) or seen
    #      below it (rear shelf, dovetails, lever rod); hidden / above-the-cut items are drawn after the keys
    v.rect(0, 0, W, dns("A05")[0], cls="vis")
    br = ppoly("balance rail")
    for fem, male in dovetail_polys():
        hpoly(v, fem, "void")
        hpoly(v, male, "m-print", P["print"])
    for sp in shelf_plan_polys():            # r4.3: two pieces beside the open slot over the USB plug (P19)
        hpoly(v, sp, "m-print")
    rx = dns("P22")
    rr = dn("S11", 0, "note") / 2
    hpoly(v, rect(rx[0], rx[1], L[0] - rr, L[0] + rr), "m-steel", P["steel"])
    for p in fixed():                       # fin bosses (printed, frame) around the rod
        if is_boss(p["part"]):
            y0, y1, _, _ = bbox(pts(p))
            hpoly(v, rect(p["x"][0], p["x"][1], y0, y1), "m-print")
    hpoly(v, ppoly("rear wall"), "m-print", P["print"])
    for p in fixed():                       # r4.2: printed bosses on the rear-wall face that carry the spring grooves (P18)
        if p["part"].startswith("spring groove boss"):
            z0, z1 = z_range(p)
            if z0 <= zc <= z1:
                y0, y1, _, _ = bbox(pts(p))
                hpoly(v, rect(p["x"][0], p["x"][1], y0, y1), "m-print", P["print"])
    for f in plan_all("fin"):
        hpoly(v, [tuple(q) for q in f["poly"]], "m-print", P["print"])
    g0, g1 = sg["groove"][2], sg["groove"][3]
    if g0 <= zc <= g1:                      # the spring grooves in the rear wall are cut by the plane
        for g in plan_all("torsion spring groove"):
            hpoly(v, [tuple(q) for q in g["poly"]], "void")
    # ---- keys (black keys reach above the cut: section; white keys below it: seen)
    for nm in WHITE:
        hpoly(v, ppoly(f"key {nm} body"), "m-key")
    for nm in BLACK:
        hpoly(v, ppoly(f"key {nm} body"), "m-black")
        sk = part(f"key {nm}", "skin")
        y0, y1, _, _ = bbox(pts(sk))
        v.poly(rect(sk["x"][0], sk["x"][1], y0, y1), cls="faint")
    for p in fixed():                       # curtain strip (cut; above the white keys) segments reaching below the cut (white-key x only)
        if p["part"] == "cover curtain":
            z0, z1 = z_range(p)
            if z0 <= zc <= z1:
                y0, y1, _, _ = bbox(pts(p))
                hpoly(v, rect(p["x"][0], p["x"][1], y0, y1), "m-cover", P["cover"])
    # ---- levers (seen from above): carrier, steel between the top lips, hub + collars
    lt = lever_top_features()
    for nm in ORDER:
        lp = ppoly(f"lever {nm}")
        hc = ppoly(f"lever {nm} hub + collars")
        x0, x1 = lp[0][0], lp[1][0]
        xc = SOL["levers"][nm]
        hpoly(v, lp, "m-lever", P["lever"])
        hpoly(v, hc, "m-lever", P["lever"])
        for sr in steel_plan_rects(xc, lt):     # narrow between the top lips (D07 spans), full width where they are cut
            hpoly(v, sr, "m-steel")
        # long spring leg from the hub to the rear-wall groove, seen from above at its own x (r4.5: the leg leaves the
        # coil's +x end and rises straight into the 2.4-wide groove, P18)
        lg = spring_parts(nm)[2]
        xl = (lg["x"][0] + lg["x"][1]) / 2
        lq = pts(lg, "rest")
        v.line(xl, min(t[0] for t in lq), xl, max(t[0] for t in lq), cls="spring")
        v.cl(xc, lp[0][1] - 3.0, xc, lp[2][1] + 3.0)
    # ---- hidden (below the keys / levers) and envelope items, dashed over the fills
    sb = [p for p in fixed() if p["part"] == "sensor bar"]
    v.rect(min(p["x"][0] for p in sb), bbox(pts(sb[0]))[0], max(p["x"][1] for p in sb) - min(p["x"][0] for p in sb),
           bbox(pts(sb[0]))[1] - bbox(pts(sb[0]))[0], cls="hid")
    for p in ledge_parts():                  # r4.5 circuit 2nd (P36): the right ledge (lip + post) holding the bar's right end
        y0_, y1_ = bbox(pts(p))[:2]
        v.poly(rect(p["x"][0], p["x"][1], y0_, y1_), cls="hid")
    v.poly(br, cls="hid")
    for c in plan_all("rod cradle"):
        v.poly([tuple(q) for q in c["poly"]], cls="hid")
    for ring in board_rings():               # control board with the r4.1 slot for the F|F# fin foot (P23)
        v.poly(ring, cls="env")
    v.poly(ppoly("USB plug"), cls="env")
    for r in plan_all("shelf rib"):
        v.poly([tuple(q) for q in r["poly"]], cls="hid")
    for nm in ORDER:                         # r4.4: rest felts (P28) under the tails; F / F# cut at the USB-slot edges
        v.poly(ppoly(f"key {nm} rest felt"), cls="hid")
    # r4.4 fix 2b (P35): the floor hatch under the board, the F|F# keel and the four bosses hung over the board
    v.poly(hatch_plan(), cls="hid")
    v.poly(keel_plan(), cls="hid")
    for p in board_boss_plan():
        c = p["circle"]
        v.poly([tuple(q) for q in p["poly"]], cls="hid")
        v.circle(c[0], c[1], c[2], cls="hid")
    for nm in ORDER:
        bt = ppoly(f"key {nm} beam + tail")
        tt = part(f"key {nm}", "thin tail")
        ty0 = bbox(pts(tt))[0]
        v.poly(rect(bt[0][0], bt[1][0], bt[0][1], ty0), cls="hid")
        v.poly(rect(tt["x"][0], tt["x"][1], ty0, bbox(pts(tt))[1]), cls="hid")
        v.poly(ppoly(f"key {nm} balance block"), cls="hid")
        for what in ("balance pin", "magnet", "capstan"):
            c = pcirc(f"key {nm} {what}")
            v.circle(c[0], c[1], c[2], cls="hid")
    # ---- above the cut plane (phantom): top plate, pad bars + their rails, up-stop pads
    v.poly(ppoly("top plate"), cls="phan")
    for p in plan_all("pad bar"):
        v.poly([tuple(q) for q in p["poly"]], cls="phan")
    for p in plan_all("up-stop pad"):
        v.poly([tuple(q) for q in p["poly"]], cls="phan")
    for nm in WHITE:
        b = ppoly(f"key {nm} body")
        v.text((b[0][0] + b[1][0]) / 2, 20.0, nm, cls="ttl", size_px=13)
    for nm in BLACK:
        b = ppoly(f"key {nm} body")
        v.text((b[0][0] + b[1][0]) / 2, 110.0, nm, cls="inv", size_px=11)
    # section markers for sheet 4 (right side)
    for yy, tg in sheet4_cuts():
        v.line(W + 7, yy, W + 15, yy, cls="edge")
        v.text(W + 17, yy - v.px(4), tg, cls="ttl", anchor="start", size_px=12)
    # ---- dimensions: front (pitch / head width / gap / module width)
    xs = [i * dn("P02") for i in range(8)]
    for a_, b_ in zip(xs, xs[1:]):
        v.dim_h(a_, b_, -9.0, text=F2(b_ - a_), ext_from=(0.0, 0.0), size_px=9.5)
    c = ppoly("key C body")
    d = ppoly("key D body")
    v.dim_h(c[0][0], c[1][0], -19.0, text=f"{F2(dn('P03'))} 헤드 (P03)", ext_from=(0.0, 0.0), size_px=9.5)
    v.dim_h(c[1][0], d[0][0], -19.0, text=f"{F2(dns('P04')[0])} (P04)", ext_from=(0.0, 0.0), size_px=9.5)
    v.dim_h(0.0, W, -30.0, text=f"{F2(W)} 옥타브 모듈 폭 (P01)", ext_from=(0.0, 0.0), size_px=10)
    cs = ppoly("key C# body")
    v.dim_h(cs[0][0], cs[1][0], cs[0][1] - 8.0, text=f"{F2(dns('P05')[0])} (P05)", ext_from=(cs[0][1], cs[0][1]), size_px=9.5, tpos="right")
    # ---- top: x ordinates of lever centres; fins and pad bars
    lab1 = ordy(v, [(SOL["levers"][nm], ppoly(f"lever {nm}")[2][1], nm) for nm in ORDER], 223.0, side="above", gap_px=13, label_px=9.5)
    f2 = [(sum(f) / 2, 209.0, "핀") for f in SOL["fins"]]
    for p in plan_all("pad bar"):
        if p["part"] != "pad bar":
            continue
        q = [tuple(t) for t in p["poly"]]
        f2 += [(q[0][0], q[2][1], "패드 바"), (q[1][0], q[2][1], "")]
    # r4.5 fix (issue 5): fin / pad bar x through the one rounding helper at 2 decimals, as P12 / P13 and sheets 4 / 8
    ordy(v, f2, 243.0, side="above", gap_px=13, label_px=9.5, breaks=lab1)   # lines broken at the lever-centre labels
    v.text(-3, 226.0, "레버 중심 x", cls="tx-s", anchor="end", size_px=10)
    v.text(-3, 246.0, "핀 · 패드 바 x (P12·P13)", cls="tx-s", anchor="end", size_px=10)
    # ---- left: y ordinates
    pb = ppoly("pad bar")
    pad = ppoly("up-stop pad C")
    fin = ppoly("fin")
    yl = [(0.0, 0.0, "백건 앞끝"), (c[2][1], 0.73, "헤드 끝"),
          (cs[0][1], cs[0][0], "흑건 앞 (P30)"), (pcirc("key C magnet")[1], 0.5, "자석·센서 (P29)"),
          (br[0][1], br[0][0], "밸런스 레일 (P20)"), (pcirc("key C balance pin")[1], 0.3, "밸런스 핀 (P32)"),
          (K[0], 1.55, "건반 봉 K (S03)"), (ppoly("curtain strip")[0][1], 0.2, "가림판 (P26)"),
          (pb[0][1], pb[0][0], "윗판·패드 바 앞 (P15·P13)"),
          (ppoly("lever C")[0][1], ppoly("lever C")[0][0], "레버 앞 (손톱 턱)"), (fin[0][1], fin[0][0], f"핀 앞 (P12; F|F# y{F(bbox(keel_plan())[3])})"),
          (pad[0][1], pad[0][0], "패드 (P16)"), (pad[2][1], pad[0][0], "패드 뒤"), (pb[2][1], pb[0][0], "패드 바 끝"),
          (SOL["caps"]["black"], 16.0, "캡스턴 흑 (S08)"),
          (SOL["caps"]["white"], 3.0, "캡스턴 백 (S08)"), (ppoly("rear shelf")[0][1], 0.0, "뒤 선반 (P19)"),
          (L[0], rx[0], "레버 봉 L (S11)"), (ppoly("rear wall")[0][1], 0.0, "뒷벽 (S28)"), (dns("A05")[0], 0.0, "프레임 뒤끝")]
    ordz(v, yl, -8.0, side="left", gap_px=12.5, label_px=9.5, prefix="y")
    # ---- right: leaders
    R = W + 28.0
    lb = _labels()
    usb = ppoly("USB plug")
    rfF, rfFs = ppoly("key F rest felt"), ppoly("key F# rest felt")
    items = [(rfFs[1][0] - 0.3, rfFs[2][1] - 0.4, 229.0,
              "쉼 펠트 F·F# (P28, 숨은선) — USB 홈 가장자리에서 자름"),
             (usb[1][0], 218.0, 218.0, "USB-C 플러그 (P24)"),
             (W - 0.5, 210.5, 212.0, f"뒷벽 + 스프링 다리 홈 {len(plan_all('torsion spring groove'))} (S28·P18)"),
             (W + 2.0, 202.0, 206.0, "도브테일 수 (D09) → 이웃"),
             (rx[1] - 0.5, L[0], 199.5, f"레버 봉 {lb['rodL']} (P22)"),
             (164.0, 190.0, 192.0, f"핀 {lb['fins']}장 + 보스 {lb['boss']} (P12·D06)"),
             (ppoly("pad bar")[1][0] + 0.2, 184.0, 184.5, f"윗판 {lb['top']} (P15, 가상선)"),
             (plan_all("pad bar")[-1]["poly"][1][0] - 0.3, 178.0, 177.0, "패드 바 + 레일 (P13, 가상선)"),
             (SOL["levers"]["B"] + 2.0, 160.0, 160.0, "레버 = 캐리어 + 강철 (P11)"),
             (ppoly("up-stop pad B")[1][0] - 0.3, 172.0, 169.0, "업스톱 패드 (P16, 가상선)"),
             (164.0, ppoly("curtain strip")[0][1] + 0.6, 151.0, "가림판 띠 (P26, 단면)"),
             (164.2, 136.0, 139.0, "밸런스 레일·봉 받침 (P20)"),
             (bbox(hatch_plan())[1], (bbox(hatch_plan())[2] + bbox(hatch_plan())[3]) / 2, 122.0,
              f"기판 밑 바닥 구멍 + 매달린 보스 {len(standoffs())} (P35, 숨은선)"),
             (162.9, 70.0, 70.0, "센서 바 + 오른쪽 턱 2곳 (P36, 숨은선)"),
             (W + 2.0, 11.0, 11.0, "앞 도브테일 수 (D09)")]
    for fu, fv, tv, txt in items:
        leader_to(v, fu, fv, R, tv, txt, size_px=9.5)
    # r4.4 (P28): the cut F / F# rest felts, second line under their leader label (the one-line label left the page)
    v.text(R + v.px(7.5), 229.0 - v.px(17.0), f"F x{F2(rfF[0][0])}~{F2(rfF[1][0])} · F# x{F2(rfFs[0][0])}~{F2(rfFs[1][0])}",
           cls="lt", anchor="start", size_px=9.5)
    note_lines(v, [f"실선 채움 = z{F(zc)} 평면 단면을 위에서 봄 (레버 윗면 쉼 최고 z{F2(lev_top)}와 패드 면 최저 z{F2(pad_lo)} 사이) · 보라 가상선 = 그 위(윗판·패드 바·패드) · 파란 점선 = 가려진 것",
                   "초록 점선 = 제어 기판 x{0}~{1} y{2}~{3} (P23, F|F# 핀 발 홈)와 USB-C 플러그 (P24) · 뒤 선반은 USB 위 홈 x{4}~{5}로 두 토막 (P19)".format(*([F2(q) for q in dns("P23")[:4]] + [F2(q) for q in shelf_slot()])),
                   "파란 점선 (r4.4 고침 2b, P35) = 기판 밑 바닥 구멍(기판을 밑에서 넣음) · F|F# 핀 킬 · 기판 위에 매달린 보스 Ø{0} 4곳(나사 {1}·위치 핀 {2})과 받침".format(
                       F(2 * standoffs()[0][2]), " · ".join(f"({F(t[0])}, {F(t[1])})" for t in standoffs() if t[3] == "screw"),
                       " · ".join(f"({F(t[0])}, {F(t[1])})" for t in standoffs() if t[3] == "pin")),
                   "레버: 연두 = 캐리어, 회색 = 강철 (윗 립 y{0}~{1}·y{2}~{3}에서는 립 사이로 좁게, 패드 옆은 립 없이 전폭, D07), 회색 선 = 스프링 긴 다리".format(*[F(q) for sp_ in top_lip_spans() for q in sp_]),
                   f"흑건 안 연한 선 = 윗면 폭 {F2(dns('P05')[1])} (P05) · A / B / C / D = 도면 4 가로 단면 자리 (" + ", ".join(f"y{F2(yy)}" for yy, tg in sheet4_cuts()) + ")"],
               U0 + 2.0, -37.0, line_px=14, size_px=10)
    scalebar(v, 200.0, -40.5, 20)
    base = os.path.join(OUT, "d03_octave_plan")
    page([[v]], base, f"도면 3. 옥타브 모듈 평면도 (C~B, z{F(zc)} 평면 단면)",
         "x = 0 C 왼쪽 명목 경계, y = 0 백건 앞끝 · 단위 mm · 숫자 = geometry.json plan·dims (괄호 = 치수표 번호) · 레버·핀·패드 바 x는 위, y 좌표는 왼쪽")
    SHEETS.append(dict(n=3, title_ko="옥타브 모듈 평면도",
                       caption_ko=f"C~B 모듈을 z{F(zc)}(레버 윗면과 업스톱 패드 면 사이)에서 잘라 위에서 본 평면. 건반·레버(캐리어 + 윗 립 사이 강철)·핀·보스·뒷벽(스프링 다리 홈)·가림판 띠는 실선, "
                                  "윗판·패드 바 4개·업스톱 패드 12개는 보라 가상선(r4: 레일·손나사·위치 핀 없음), 밸런스 레일·봉 받침·센서 바·캡스턴·자석·핀·리브는 파란 숨은선, "
                                  "제어 기판(F|F# 핀 발 홈)·USB 플러그는 초록 점선. 앞은 피치·헤드 폭·틈, 위는 레버 중심·핀·패드 바 x, 왼쪽은 y 좌표. A·B·C·D는 도면 4의 가로 단면 자리. "
                                  f"r4.2~4.3: 강철은 윗 립 두 구간에서만 좁게 보임, 뒷벽 스프링 홈 보스 12, 뒤 선반은 USB 위 홈 x{F2(shelf_slot()[0])}~{F2(shelf_slot()[1])}로 두 토막. "
                                  f"r4.4: 윗 립 y{F(top_lip_spans()[0][0])}~{F(top_lip_spans()[0][1])}·{F(top_lip_spans()[1][0])}~{F(top_lip_spans()[1][1])}, "
                                  f"쉼 펠트(숨은선) F x{F2(ppoly('key F rest felt')[0][0])}~{F2(ppoly('key F rest felt')[1][0])}·F# x{F2(ppoly('key F# rest felt')[0][0])}~{F2(ppoly('key F# rest felt')[1][0])}는 USB 홈에서 자름(P28), "
                                  f"USB 플러그 y{F2(ppoly('USB plug')[0][1])}~{F2(ppoly('USB plug')[2][1])}(P24). "
                                  f"r4.4 고침 2b: 기판 밑 바닥 구멍 x{F2(bbox(hatch_plan())[0])}~{F2(bbox(hatch_plan())[1])} y{F2(bbox(hatch_plan())[2])}~{F2(hatch_main_y1())}"
                                  f" (x{F2(hatch_notch()[0])}~{F2(hatch_notch()[1])}은 y{F2(bbox(hatch_plan())[3])}까지, USB 리셉터클 뒤; 기판은 밑에서 넣음), "
                                  f"F|F# 핀 킬 y{F2(bbox(keel_plan())[2])}~{F2(bbox(keel_plan())[3])}, 기판 위에 매달린 보스 Ø{F(2 * standoffs()[0][2])} 4곳과 받침(P35, 숨은선). "
                                  f"r4.5: 뒷벽 스프링 홈 {F(SOL['spring']['groove'][3])} 폭(보스 {F(SOL['spring']['boss'][0])}), 긴 다리는 코일 +x 끝에서 곧게 홈으로(회색 선); r4.5 고침: 홈·보스 = {spring_txt()['dx']} 가운데(긴 다리 x). "
                                  f"r4.5 회로 2차: 센서 바 오른쪽 끝을 잡는 턱 2곳 (숨은선, v3 P112, P36) — 립 x{F(G['circuit_r45']['ledge']['lip'][0])}~{F(G['circuit_r45']['ledge']['lip'][1])} + 기둥 x{F(G['circuit_r45']['ledge']['post'][0])}~{F(G['circuit_r45']['ledge']['post'][1])}, "
                                  f"y{F(G['circuit_r45']['ledge']['y'][0][0])}~{F(G['circuit_r45']['ledge']['y'][0][1])}·{F(G['circuit_r45']['ledge']['y'][1][0])}~{F(G['circuit_r45']['ledge']['y'][1][1])}.",
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))


def sheet4_y_pad():
    """y of section B-B: middle of the up-stop pads (P16)."""
    return (dn("P16", 0) + dn("P16", 1)) / 2


def sheet4_cuts():
    """sheet-4 section planes: A-A lever rod L, B-B middle of the pads, C-C middle of the pad bar's front part
    (in the top-plate groove, between the plate front and the bar step)."""
    return [(L[0], "A"), (sheet4_y_pad(), "B"), ((bbox(pts(fpart("pad bar")))[0] + SOL["y_bar_step"]) / 2, "C"),
            (standoff_y_front(), "D")]


def standoffs():
    """P35: the four control-board bosses from the plan circles -> [(x, y, r, kind)] (kind 'screw' / 'pin').
    r4.4 fix 2b: they hang over the board (brackets to the balance rail / shelf ribs); the kind is taken from the
    screw-head / locating-pin circles at the same centre (the boss plan names no longer say it)."""
    scr = [p["circle"] for p in PLAN if p["part"].startswith("control-board screw")]
    out = []
    for p in PLAN:
        if p["part"].startswith(("control-board stand-off", "control-board boss")):
            c = p["circle"]
            kind = "screw" if any(abs(s[0] - c[0]) < 1e-6 and abs(s[1] - c[1]) < 1e-6 for s in scr) else "pin"
            out.append((c[0], c[1], c[2], kind))
    return sorted(out, key=lambda t: (t[1], t[0]))


def board_boss_plan():
    """r4.4 fix 2b (P35): plan items of the hung bosses (bracket poly + boss circle)."""
    return [p for p in PLAN if p["part"].startswith("control-board boss")]


def hatch_plan():
    """r4.4 fix 2b (P35): the floor hatch under the control board (the board goes in from below) + the notch
    behind the USB-C receptacle, as one plan polygon."""
    return [tuple(q) for q in plan_all("floor hatch under the control board")[0]["poly"]]


def hatch_main_y1():
    """rear edge of the main floor hatch (the rectangle), below the receptacle notch: second-largest y of the polygon."""
    return sorted(set(q[1] for q in hatch_plan()))[-2]


def hatch_notch():
    """x range of the hatch notch behind the USB-C receptacle (the vertices at the largest y)."""
    y1 = max(q[1] for q in hatch_plan())
    xs = [q[0] for q in hatch_plan() if abs(q[1] - y1) < 1e-6]
    return min(xs), max(xs)


def keel_plan():
    """r4.4 fix 2b (P12 / D18): the F|F# fin keel inside the board slot (plan rectangle)."""
    return [tuple(q) for q in plan_all("F|F# fin keel")[0]["poly"]]


def standoff_y_front():
    """y of the front stand-off row (P35) = section D-D of sheet 4 (through the ribbon under the board, J301)."""
    return min(t[1] for t in standoffs())


# ================================================================ sheet 4: module cross sections (x-z)
def zspans(poly, y):
    return yslice(poly, y)


def sub_intervals(a0, a1, holes):
    """[a0, a1] minus the hole intervals."""
    out = [(a0, a1)]
    for h0, h1 in holes:
        nxt = []
        for b0, b1 in out:
            if h1 <= b0 or h0 >= b1:
                nxt.append((b0, b1))
            else:
                if h0 > b0:
                    nxt.append((b0, h0))
                if h1 < b1:
                    nxt.append((h1, b1))
        out = nxt
    return out


def rod_elements(src_levers=None, fins=None, bosses=None):
    """elements along the lever rod, sorted: fin bosses (fin + one-sided / two-sided extensions, frame) and the
    lever hubs with their collars (P14, one print with the carrier).  -> [(x0, x1, kind, name)]"""
    out = []
    for p in (bosses if bosses is not None else [p for p in fixed() if is_boss(p["part"])]):
        out.append((p["x"][0], p["x"][1], "boss", ""))
    for nm in (src_levers or ORDER):
        q = ppoly(f"lever {nm} hub + collars")
        out.append((q[0][0], q[1][0], "hub", nm))
    return sorted(out)


def bay_play():
    """axial play of each fin bay = sum of the gaps between the elements on the rod between two fin bosses."""
    el = rod_elements()
    res = []
    bos = [e for e in el if e[2] == "boss"]
    for a, b in zip(bos, bos[1:]):
        inside = [e for e in el if a[1] - 1e-6 <= e[0] and e[1] <= b[0] + 1e-6 and e[2] == "hub"]
        seq = [a] + inside + [b]
        gaps = [q[0] - p[1] for p, q in zip(seq, seq[1:])]
        res.append((a, b, inside, gaps))
    return res


def coil_wires(nm):
    """x positions of the coil wire sections seen in a plane through the rod axis: close-wound wires of d over the
    exported coil length (r4.5 MISUMI coil 2.13 long = 3.25 body turns + 1 wire -> 4 wire sections)."""
    sp = SOL["spring"]
    coil = spring_parts(nm)[0]
    x0, x1 = coil["x"]
    nw = max(1, int(round((x1 - x0) / sp["d"])))
    step = (x1 - x0 - sp["d"]) / (nw - 1) if nw > 1 else 0.0
    return [x0 + sp["d"] / 2 + i * step for i in range(nw)]


def xz_scene(v, P, y, press=False, keys=True, spring=True):
    """x-z section of the module at y (looking from the front toward +y, x to the right)."""
    eva = dns("S01")
    v.rect(0.5, eva[0], dn("P01") - 1.0, eva[1] - eva[0], cls="faintfill")
    frame, other, bar = [], [], []
    for p in void_first(fixed()):
        n = p["part"]
        x0, x1 = p["x"]
        if n.startswith(("lever rod D4", "lever rod end plug")):     # drawn last, on top of the hubs (below)
            continue
        if n.startswith("up-stop pad"):
            for poly, cls in pad_layers(p)[0]:
                for z0, z1 in yslice(poly, y):
                    other.append((rect(x0, x1, z0, z1), cls, None))
            continue
        if p.get("female") and "front" in p:        # r4.5 fix: groove entry chamfer = its exported x-z (front) outline
            if zspans(pts(p), y):
                other.append(([tuple(t) for t in p["front"]], "void", None))
            continue
        for z0, z1 in zspans(pts(p), y):
            if is_frame(n):
                frame.append(rect(x0, x1, z0, z1))
                continue
            cls, h = mat_fixed(n)
            other.append((rect(x0, x1, z0, z1), cls, h))
            if n.startswith(("pad bar", "pad wedge")) and not n.startswith("pad bar rail"):
                bar.append(rect(x0, x1, z0, z1))
    # male dovetail tail (D09) beyond the right edge
    r_, t_, dpt = dns("D09")[:3]
    for (ya, yb), zt in (((dns("D09", "ref")[0], dns("D09", "ref")[1]), dns("D09")[4]),
                         ((dns("D09", "ref")[2], dns("D09", "ref")[3]), dns("D09")[6])):
        if ya <= y <= yb:
            frame.append(rect(dn("P01"), dn("P01") + dpt, dns("D09")[3], zt))
    fill_rings(v, union_rings(frame, res=0.03), "m-print", P["print"])
    sg = spring_geom()
    if sg["groove"][0] <= y <= sg["groove"][1]:       # spring-leg grooves in the rear wall (P18)
        for g in plan_all("torsion spring groove"):
            q = [tuple(t) for t in g["poly"]]
            v.poly(rect(q[0][0], q[1][0], sg["groove"][2], sg["groove"][3]), cls="void")
    for poly, cls, h in other:
        if cls == "env":
            v.poly(poly, cls="env")
        else:
            hpoly(v, poly, cls, P[h] if h else None)
    stroke_rings(v, union_rings(bar, res=0.03), "out")          # pad bar = one print (bar + grip + wedges)
    dy = y - L[0]
    rr = dn("S11", 0, "note") / 2
    rx = dns("P22")
    if not keys:
        return
    # keys and levers (r4.4: the carrier top snap lips are exported lever parts, sliced like the others)
    for nm in ORDER:
        black = "#" in nm
        kb, ov = [], []
        for p in body(f"key {nm}"):
            for z0, z1 in zspans(pts(p), y):
                r_ = rect(p["x"][0], p["x"][1], z0, z1)
                if p["part"] == "capstan head":
                    ov.append((r_, "m-steel"))
                elif p["part"] == "rest felt":
                    ov.append((r_, "m-felt"))
                else:
                    kb.append(r_)
        fill_rings(v, union_rings(kb, res=0.03), "m-black" if black else "m-key", None if black else P["key"])
        for r_, c in ov:
            hpoly(v, r_, c, P["steel"] if c == "m-steel" else None)
        lb, lo = [], []
        bore = []                                  # the plane cuts the rod: hub slice minus its bore (S11)
        if abs(dy) < dns("S11", "note")[4] / 2:
            hb = math.sqrt((dns("S11", "note")[4] / 2) ** 2 - dy ** 2)
            bore = [(L[1] - hb, L[1] + hb)]
        for p in body(f"lever {nm}"):
            for z0_, z1_ in zspans(pts(p, "rest"), y):
                for z0, z1 in (sub_intervals(z0_, z1_, bore) if not p["part"].startswith(("steel", "felt")) else [(z0_, z1_)]):
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
        # spring coil wires where the plane cuts the coil (r4.5: the pocket D6.6 is the lever's own 'spring pocket section
        # A / B' prisms, sliced above; the coil is the exported MISUMI coil OD 6.0 x 2.13 at its own x)
        if spring and abs(dy) < sg["r_m"]:
            hz = math.sqrt(sg["r_m"] ** 2 - dy * dy)
            for xw in coil_wires(nm):
                for s_ in (1, -1):
                    v.circle(xw, L[1] + s_ * hz, sg["d"] / 2, cls="m-steel")
        if press:
            dd = []
            for p in body(f"lever {nm}"):
                for z0, z1 in zspans(pts(p, "dip"), y):
                    dd.append(rect(p["x"][0], p["x"][1], z0, z1))
            if dd:
                stroke_rings(v, union_rings(dd, res=0.03), "pressed")
    # the cut lever rod (P22 / D18) as one continuous steel strip through the hub bores, on top; the printed end plug
    # in the left end-fin bore — both exported prisms (r4.4)
    rp_, pp_ = rod_part(), plug_part()
    for z0, z1 in yslice(pts(rp_), y):
        hpoly(v, rect(rp_["x"][0], rp_["x"][1], z0, z1), "m-steel", P["steel"])
    for z0, z1 in yslice(pts(pp_), y):
        hpoly(v, rect(pp_["x"][0], pp_["x"][1], z0, z1), "m-print2")


def sheet_sections():
    W = dn("P01")
    panels = []
    cuts = dict((t, y) for y, t in sheet4_cuts())
    z_top = dn("S18")
    specs = [("A", cuts["A"], "레버 봉 L 줄: 허브·칼라·핀 보스·비틀림 스프링 코일·핀·뒤 선반·리브·USB 플러그·도브테일·윗판"),
             ("B", cuts["B"], "업스톱 패드 가운데: 레버(캐리어 + 강철)·패드(폼 + 펠트)·쐐기·패드 바·L 레일(웹 + 립)·윗판·숨은 빔·제어 기판"),
             ("C", cuts["C"], "패드 바 앞부분: 윗판 홈 속 패드 바·핀 앞 연장(얇음)·레버 앞쪽·숨은 빔·제어 기판"),
             ("D", cuts["D"], "제어 기판 앞 보스 줄 (r4.4 고침 2b): 바닥 구멍·매달린 보스·밑에서 넣는 M3·위치 핀 (P35)·F|F# 핀 앞 연장·기판·기판 밑 16심 리본 (P27)")]
    lb = _labels()
    for tag, yy, desc in specs:
        U0, U1, V0, V1 = -16.0, 214.0, -22.0, z_top + 16.0
        if tag == "D":          # r4.5 fix 3: the D-D notes go above the top plate (the full-height F|F# fin crossed them)
            V1 += 14.0 * (U1 - U0) / 1480
        v = View(U0, V0, U1, V1, px_width=1480)
        P = pids(v)
        xz_scene(v, P, yy, press=(tag == "B"))
        panel_title(v, U0 + 1.0, V1 - v.px(16), f"단면 {tag}-{tag}  (y = {F2(yy)})  — {desc}", size_px=12.5)
        plate = pts(fpart("top plate (ledge + bridge)"))
        zpl = yslice(plate, yy)
        zf = [(z_top, W, f"윗판 윗면 = 맨 위 (S18)")] + ([(zpl[0][0], W, "윗판 밑 (P15)")] if zpl else [])
        if tag == "A":
            fins = SOL["fins"]
            hub = pts(part("lever D", "hub"), "rigid0")
            col = pts(part("lever D", "hub collar"), "rigid0")
            bos = pts(boss_parts()[0])
            zf += [(bbox(pts(fparts("rear shelf")[0]))[2], W, "선반 밑"), (SOL["z_shelf"], W, "선반 윗면 (S10)"),
                   (bbox(pts(usb_env()))[3], bbox(ppoly("USB plug"))[1], "USB 플러그 위 (P24)"),
                   (min(z0 for p in fixed() if p["part"] == "fin" and p["x"][0] < sum(shelf_slot()) / 2 < p["x"][1] for z0, z1 in yslice(pts(p), yy)),
                    sum(shelf_slot()) / 2, "F|F# 핀 밑 (S29)"),
                   (L[1], W, "L (S11)"), (bbox(col)[3], W, f"칼라 위 {lb['collar']} (P14)"),
                   (bbox(bos)[3], W, f"보스 위 {lb['boss']} (D06)"), (bbox(hub)[3], W, f"허브 위 {lb['hub']}"),
                   (L[1] + SOL["spring"]["pocket"][0] / 2, W, f"스프링 주머니 Ø{F(SOL['spring']['pocket'][0])} (P18)")]
            # collar lengths (P14) above each collar, boss extensions above each boss
            ztxt = bbox(hub)[3] + v.px(4)
            cols = sorted((p["x"][0], p["x"][1]) for nm in ORDER for p in body(f"lever {nm}") if p["part"] == "hub collar")
            i = 0
            while i < len(cols):                  # neighbouring collars (play gap between): one label 'a+b' at the joint
                x0, x1 = cols[i]
                if i + 1 < len(cols) and cols[i + 1][0] - x1 < 0.5:
                    t = f"{F(x1 - x0, 3)}+{F(cols[i + 1][1] - cols[i + 1][0], 3)}"
                    u = (x1 + cols[i + 1][0]) / 2
                    i += 2
                else:
                    t, u = F(x1 - x0, 3), (x0 + x1) / 2
                    i += 1
                v.text(u + v.px(3.3), ztxt, t, cls="dt", anchor="start", size_px=8.5, rot=-90)
            for p in boss_parts():
                fin = next(f for f in fins if p["x"][0] - 1e-6 <= f[0] and f[1] <= p["x"][1] + 1e-6)
                for k_, (a_, b_) in enumerate(((p["x"][0], fin[0]), (fin[1], p["x"][1]))):
                    if b_ - a_ > 1e-6:          # r4.4: glyph column kept off the fin edge (left of fin: shift left, right: shift right)
                        v.text((a_ + b_) / 2 + v.px(1.2 if k_ == 0 else 5.0), ztxt, F2(b_ - a_), cls="dt", anchor="start", size_px=8.5, rot=-90)
            v.text(SOL["fins"][0][1] + 1.0, ztxt + v.px(60), "칼라 a+b (P14, 셋째 자리) · 보스 (D06)", cls="tx-s", anchor="start", size_px=9.5)

            def fin_bottom(f):
                zz = [z0 for p in fixed() if p["part"] == "fin" and p["x"][0] <= sum(f) / 2 <= p["x"][1] for z0, z1 in yslice(pts(p), yy)]
                zb = min(zz) if zz else dns("S01")[3]
                return dns("S01")[2] if zb <= dns("S01")[3] + 1e-6 else zb     # fin standing on the floor: floor underside
            ordy(v, [(sum(f) / 2, fin_bottom(f), f"핀 {F2(f[1] - f[0])}") for f in fins] +
                    [(rod_part()["x"][0], L[1], "봉 끝 (P22)"), (rod_part()["x"][1], L[1], "봉 끝"),
                     (plug_part()["x"][0], L[1], "마개 (D18)"),
                     (max(p["x"][1] for p in bore_parts()), L[1], "막힌 구멍 끝 (D18)")] +
                    [(bbox(ppoly("USB plug"))[0], bbox(pts(usb_env()))[2], "USB (P24)"), (bbox(ppoly("USB plug"))[1], bbox(pts(usb_env()))[2], "")] +
                    [(shelf_slot()[0], SOL["z_shelf"], "선반 홈 (P19)"), (shelf_slot()[1], SOL["z_shelf"], "")],
                 -1.0, gap_px=12.5, label_px=9)
        elif tag == "B":
            cb = fpart("control board")
            comp = fpart("board components (<= z20)")
            bar = pts(fpart("pad bar"))
            rail = pts(fparts("pad bar rail")[0])
            pfw, pfb = SOL["pad_face_w"], SOL["pad_face_b"]

            def face_at(pf):
                return pf["z"][0] + (pf["z"][1] - pf["z"][0]) * (yy - pf["y"][0]) / (pf["y"][1] - pf["y"][0])
            zf += [(dns("S01")[3], W, "바닥판"), (bbox(pts(cb))[2], 117.25, "기판 밑 (v3)"),
                   (bbox(pts(cb))[3], 117.25, "기판 윗면"), (bbox(pts(comp))[3], 117.25, f"부품 ≤ z{F(bbox(pts(comp))[3])} (P27)"),
                   (bbox(pts(fparts("board part: RP2040-Zero")[0]))[3], fparts("board part: RP2040-Zero")[0]["x"][1], "RP2040-Zero 윗면 부품 (P27)"),
                   (dn("S07", 0), W, "빔 밑 (S07)"), (dn("S07", 1), W, "빔 위"), (face_at(pfb), W, "흑 패드 면 (S15)"),
                   (face_at(pfw), W, "백 패드 면 (S15)"), (min(q[1] for q in bar), W, "패드 바 밑"), (min(q[1] for q in rail), W, "레일 밑 (P13)"),
                   (dn("S17"), W, "패드 바 자리 (S17)")]
            lv = ppoly("lever C")
            zlb = min(z0 for p in body("lever C") for z0, z1 in yslice(pts(p, "rest"), yy))
            zdim = (dn("S07", 1) + zlb) / 2
            v.dim_h(lv[0][0], lv[1][0], zdim, text=f"{F2(dn('P11'))} (P11)", ext_from=(zlb, zlb), size_px=9, tpos="right")
            pd = ppoly("up-stop pad C")
            v.dim_h(pd[0][0], pd[1][0], z_top + 6.0, text=f"{F2(pd[1][0] - pd[0][0])} (P16)", ext_from=(z_top, z_top), size_px=9)
            wd = SOL["wedge"]
            v.text(60.0, z_top + 5.5, f"쐐기 (P17): 백 {kit.FR(*wd['w'][:2])}, 흑 {kit.FR(*wd['b'][:2])} → 흑 패드 면이 백보다 낮음 (S15)",
                   cls="tx", anchor="start", size_px=9.5)

            def lever_bottom(n):
                return min(z0 for p in body(f"lever {n}") if p["x"][0] <= SOL["levers"][n] <= p["x"][1]
                           for z0, z1 in yslice(pts(p, "rest"), yy))
            ordy(v, [(SOL["levers"][n], lever_bottom(n), n) for n in ORDER], -1.0, gap_px=12.5, label_px=9)
        elif tag == "D":
            # r4.4 fix 2b (P35): no floor under the board (hatch), the board rises into place from below; the bosses hang
            # over it (front two on brackets from the balance rail's rear face), M3x6 from BELOW into a blind D2.5 bore,
            # the locating pins hang down through the board; the F|F# fin keel stands in the board slot
            def _at(p):
                y0_, y1_ = bbox(pts(p))[:2]
                return y0_ - 1e-6 <= yy <= y1_ + 1e-6
            cb = fpart("control board")
            rib_ = fparts("board part: J301 16-core ribbon under the board")[0]
            jp_ = fparts("board part: J301 ribbon 2x8 pads")[0]
            scr = next(p for p in fparts("control-board screw") if _at(p))
            pin_ = next(p for p in fparts("control-board locating pin") if _at(p))
            bo_ = sorted((p for p in fparts("control-board boss") if _at(p)), key=lambda p: p["x"][0])
            kl_ = fparts("fin keel")[0]
            cz = G["circuit_r44"]["screw"]
            sbo = next(p for p in bo_ if "screw bore" in p["part"])
            nb = nums(sbo["part"])            # '... boss D6 hung ... screw bore D2.5 to z15.4)' -> [6, 2.5, 15.4]
            m3 = nums(scr["part"])[0]         # 'screw M3x6 head D5.7 x 3.0 ...' -> 3
            sx = next(t[0] for t in standoffs() if t[3] == "screw" and abs(t[1] - yy) < 1e-6)
            px_ = next(t[0] for t in standoffs() if t[3] == "pin" and abs(t[1] - yy) < 1e-6)
            zb0, zb1 = bbox(pts(cb))[2:]
            v.poly(rect(sx - nb[1] / 2, sx + nb[1] / 2, zb1, nb[2]), cls="void")                  # blind bore in the boss
            v.poly(rect(sx - m3 / 2, sx + m3 / 2, cz["head_z"][1], cz["tip_z"]), cls="hid")        # M3 shank, head under the board
            hpoly(v, rect(pin_["x"][0], pin_["x"][1], bbox(pts(pin_))[2], bbox(pts(pin_))[3]), "m-print", P["print"])
            hx = bbox(hatch_plan())
            # r4.5 fix: each z ordinate starts at its own feature (right boss / bore / screw / pin / pad / keel edge), not at
            # the module edge W
            xbR = bo_[-1]["x"][1]
            xcb = max(p["x"][1] for p in fparts("control board"))
            zf += [(dns("S01")[3], W, "바닥판 윗면 (구멍 밖)"), (zb0, xcb, "기판 밑 (P23)"), (zb1, xbR, "기판 윗면 = 보스 밑 (P35)"),
                   (bbox(pts(bo_[0]))[3], xbR, "보스·받침 위 (P35)"), (nb[2], sx + nb[1] / 2, f"막힌 구멍 Ø{F(nb[1])} 끝 (P35)"),
                   (cz["tip_z"], sx + m3 / 2, f"M{F(m3)} 나사 끝"), (cz["head_z"][0], scr["x"][1], "나사 머리 밑 (밑에서 넣음)"),
                   (bbox(pts(pin_))[2], pin_["x"][1], "위치 핀 끝 (P35)"), (bbox(pts(jp_))[3], jp_["x"][1], "J301 납땜 자국 ≤ (P27)")]
            # r4.5 fix 3: at y149 the cut runs through the full-height F|F# fin (front y148.6), the keel (y144.5~148.6) is in
            # front of the plane -> no keel-top ordinate here; the fin is named by its own width (P12 front extension)
            fin_ = next(p for p in fixed() if p["part"] == "fin" and bbox(pts(p))[0] - 1e-6 <= yy <= bbox(pts(p))[1] + 1e-6
                        and p["x"][0] < sum(kl_["x"]) / 2 < p["x"][1])
            fb_ = bbox(pts(fin_))
            ordy(v, [(hx[0], dns("S01")[2], "바닥 구멍 (P35)"), (hx[1], dns("S01")[2], ""),
                     (bo_[0]["x"][0], bbox(pts(bo_[0]))[3], "보스 Ø6"), (bo_[0]["x"][1], bbox(pts(bo_[0]))[3], ""),
                     (bo_[1]["x"][0], bbox(pts(bo_[1]))[3], "보스 Ø6"), (bo_[1]["x"][1], bbox(pts(bo_[1]))[3], ""),
                     (sx, cz["head_z"][0], "나사 (P35)"), (px_, bbox(pts(pin_))[2], "위치 핀"),
                     (fin_["x"][0], fb_[2], f"F|F# 핀 앞 연장 {F2(fin_['x'][1] - fin_['x'][0])}"), (fin_["x"][1], fb_[2], ""),
                     (rib_["x"][0], bbox(pts(rib_))[2], "리본 (기판 밑)"), (rib_["x"][1], bbox(pts(rib_))[2], ""),
                     (cb["x"][0], zb0, "기판 (P23)"),
                     (max(p["x"][1] for p in fparts("control board")), zb0, "")],
                 -1.0, gap_px=12.5, label_px=9)
            rb_ = G["circuit_r44"]["ribbon"]
            # r4.5 fix 3: notes above the top plate (free band made in the D view), clear of the full-height F|F# fin
            z_t = V1 - v.px(16 + 24 + 14)          # first baseline 24 px under the panel title
            kb_ = bbox(pts(kl_))
            note_lines(v, [f"r4.4 고침 2b: 기판 밑 바닥이 x{F2(hx[0])}~{F2(hx[1])}로 뚫림 — 모듈을 뒤집어 기판을 밑에서 넣고, 보스 {len(standoffs())}곳이 기판 위에 매달림 "
                           f"(앞 두 곳은 밸런스 레일 뒷면 받침, 위 z{F(bbox(pts(bo_[0]))[3])}); F|F# 핀 (앞끝 y{F(fb_[0])}, 바닥 z{F(fb_[2])}~윗판 밑 z{F(fb_[3])}, r4.5)이 기판 홈 속을 지남 — "
                           f"킬 y{F(kb_[0])}~{F(kb_[1])} z{F(kb_[2])}~{F(kb_[3])}은 이 단면 앞 (P12)",
                           f"M{F(m3)}×{F(cz['length'])} 밑에서: 머리 z{F2(cz['head_z'][0])}~{F(cz['head_z'][1])} (기판 밑), 기판 {F(cz['stack'][0])} + 보스 {F(cz['stack'][1])}, "
                           f"Ø{F(nb[1])} 막힌 구멍 z{F(nb[2])}까지 (나사 끝 z{F(cz['tip_z'])}); 위치 핀 Ø{F(G['circuit_r44']['pins']['d'])} → 기판 구멍 Ø{F(G['circuit_r44']['pins']['hole'])}, 끝 z{F(G['circuit_r44']['pins']['tip_z'])} (P35)",
                           f"기판 밑 초록 점선 = 16심 리본 {F2(rb_['width'])} 폭, z{F(rb_['under_z'][0])}~{F(rb_['under_z'][1])}, y{kit.FR(*rb_['under_y'][:2])} "
                           f"(J301은 아랫면 납땜) — 보스까지 {F2(rb_['to_standoff'])}, F|F# 핀 발까지 {F2(rb_['to_fin'])} (P27)"],
                       2.0, z_t + v.px(14), line_px=14, size_px=9.5)
        else:
            cb = fpart("control board")
            bar = pts(fpart("pad bar"))
            fins_front = [p for p in fixed() if p["part"] == "fin" and any(y0 <= yy <= y1 for y0, y1 in [bbox(pts(p))[:2]])
                          and min(q[0] for q in pts(p)) <= yy]
            zf += [(dns("S01")[3], W, "바닥판"), (bbox(pts(cb))[3], 117.25, "기판 윗면"),
                   (dn("S07", 0), W, "빔 밑 (S07)"), (dn("S07", 1), W, "빔 위"),
                   (dn("S17"), W, "패드 바 밑 = 홈 속 (S17)"), (max(q[1] for q in bar), W, "패드 바 위")]
            ordy(v, [((p["x"][0] + p["x"][1]) / 2, min(z0 for z0, z1 in yslice(pts(p), yy)), f"핀 앞 연장 {F2(p['x'][1] - p['x'][0])}")
                     for p in fins_front], -1.0, gap_px=12.5, label_px=9)
        ordz(v, zf, W + 8.0, gap_px=12.5, label_px=9.5)
        scalebar(v, 176.0, v.v0 + v.px(6), 10)
        panels.append(v)
    # detail: bay boundary at fin 2 (x38~46) at A-A: boss extensions, collars, gaps
    f = SOL["fins"][1]
    u0, u1, w0, w1 = f[0] - 3.0, f[1] + 3.0, L[1] - 5.2, L[1] + 5.2
    s_ = 30.0
    dv = View(u0 - 40 / s_, w0 - 40 / s_, u1 + 900 / s_, w1 + 30 / s_, px_width=(u1 - u0) * s_ + 940, pad_px=4)
    P = pids(dv)
    i0 = clip_begin(dv)
    xz_scene(dv, P, L[0])
    clip_end(dv, i0, u0, u1, w0, w1)
    panel_title(dv, u0 - 40 / s_ + dv.px(4), w1 + dv.px(12), "확대 A-A: 핀 2 (D|D#) 둘레의 축 놀음", size_px=12.5)
    el = rod_elements()
    boss = next(e for e in el if e[2] == "boss" and e[0] < f[0] < e[1])
    hl = next(e for e in el if e[3] == "D")
    hr = next(e for e in el if e[3] == "D#")
    g1, g2 = boss[0] - hl[1], hr[0] - boss[1]
    hub = pts(part("lever D", "hub"), "rigid0")
    dv.dim_h(hl[1], boss[0], w1 - 0.8, text=f"{F(g1, 3)}", ext_from=(bbox(hub)[3], bbox(hub)[3] - 0.8), size_px=9)
    dv.dim_h(boss[1], hr[0], w1 - 0.8, text=f"{F(g2, 3)}", ext_from=(bbox(hub)[3] - 0.8, bbox(hub)[3]), size_px=9)
    dv.dim_h(boss[0], f[0], w0 + 0.9, text=f"{F2(f[0] - boss[0])}", ext_from=(L[1] - 3.5, L[1] - 3.5), size_px=9)
    dv.dim_h(f[1], boss[1], w0 + 0.9, text=f"{F2(boss[1] - f[1])}", ext_from=(L[1] - 3.5, L[1] - 3.5), size_px=9)
    bp = bay_play()
    # r4.4: the D#|E joint — D#'s only collar is on its RIGHT (its left is the fin boss, P14 0.00), E's left collar meets it
    col_dr = next(p for p in body("lever D#") if p["part"] == "hub collar")
    col_el = min((p for p in body("lever E") if p["part"] == "hub collar"), key=lambda p: p["x"][0])
    assert col_dr["x"][0] > SOL["levers"]["D#"] and col_el["x"][1] < SOL["levers"]["E"], (col_dr["x"], col_el["x"])
    note_lines(dv, [f"핀 {F2(f[1] - f[0])} + 보스 연장 {F2(f[0] - boss[0])}씩 (프레임과 한 몸, 보스 {lb['boss']}, 황동 없음, D06) · 핀 옆 틈 {F(g1, 3)} + {F(g2, 3)}",
                    "핀 칸마다 축 놀음 = 칸 안 틈의 합: " + " / ".join(F2(sum(g)) for a, b, i, g in bp) + " (P14)",
                    f"허브 칼라 {lb['collar']} (P14, 캐리어와 한 몸 — r3 C-링 대신): 이웃 레버의 칼라끼리 맞닿음, 예: D# 오른쪽 {F(col_dr['x'][1] - col_dr['x'][0], 3)} · E 왼쪽 {F(col_el['x'][1] - col_el['x'][0], 3)}",
                    f"레버 봉 {lb['rodL']}, 허브 구멍 {lb['bore']} (S11) · 허브 가운데 스프링 주머니 Ø{F(SOL['spring']['pocket'][0])}×{F(SOL['spring']['pocket'][1])} + 코일 (P18)",
                    "A-A의 칼라 길이는 모델 값 그대로 셋째 자리까지 (0.955 등; P14 표는 둘째 자리로 반올림한 값)"],
               u1 + 1.0, w1 - 1.0, line_px=17, size_px=10.5)
    rows = [[panels[0]], [dv], [panels[1]], [panels[2]], [panels[3]]]
    base = os.path.join(OUT, "d04_module_cross_sections")
    page(rows, base, "도면 4. 옥타브 모듈 가로 단면 (x–z) — 레버 구역 A-A · B-B · C-C · D-D",
         "앞에서 본 단면 (x 오른쪽, z 위) · 정지 자세 실선, B-B의 주황 점선 = 1 N 끝까지 누른 레버 · 단위 mm · 숫자 = geometry.json (괄호 = 치수표 번호) · 단면 자리는 도면 3의 A·B·C·D")
    SHEETS.append(dict(n=4, title_ko="모듈 가로 단면 (레버 구역)",
                       caption_ko=f"레버 구역 x–z 단면 넷. A-A(y{F2(cuts['A'])} 레버 봉): 허브·허브 칼라(P14)·핀 보스(프레임, 황동 없음)·스프링 주머니와 코일·핀·뒤 선반·리브·USB 플러그·윗판, "
                                  f"확대로 핀 둘레 축 놀음; r4.3 선반 USB 홈 x{F2(shelf_slot()[0])}~{F2(shelf_slot()[1])}, 플러그 z{F2(bbox(pts(usb_env()))[2])}~{F2(bbox(pts(usb_env()))[3])}, F|F# 핀은 그 위에 매달림. "
                                  f"B-B(y{F2(cuts['B'])} 패드 가운데): 레버 캐리어·강철·패드(폼 + 펠트)·쐐기·패드 바·L 레일(웹 + 립)·윗판과 누른 레버(점선), 기판 위 RP2040-Zero·4067(초록 점선, P27). "
                                  f"C-C(y{F2(cuts['C'])}): 윗판 앞 홈 속의 패드 바 앞부분, 핀 앞 연장, 기판 홈을 지나 바닥 구멍의 z3까지 내려간 F|F# 핀 발(r4.4 고침 2b: 킬로 밸런스 레일 뒷면에 붙음). "
                                  f"r4.4: A-A의 레버 봉·핀 보스 구멍 Ø4.0·끝 마개는 geometry 부품(D18: 봉 x{F2(rod_part()['x'][0])}~{F2(rod_part()['x'][1])}, 마개 x{F2(plug_part()['x'][0])}~{F2(plug_part()['x'][1])}, 오른쪽 막힌 구멍 x{F2(max(p['x'][1] for p in bore_parts()))}까지), "
                                  f"B-B의 기판 부품은 BRD-01 2.54 격자 자리(P27), D-D(y{F2(cuts['D'])}, r4.4 고침 2b): 기판 밑 바닥 구멍, 기판 위에 매달린 보스 Ø6 두 곳(밸런스 레일 뒷면 받침; 밑에서 넣는 M3×6·막힌 구멍, 아래로 내려온 위치 핀, P35), "
                                  f"기판 홈 속 F|F# 핀 앞 연장(r4.5: 앞끝 y{F(bbox(keel_plan())[3])}, 바닥부터 윗판까지; 킬은 단면 앞, P12), 기판 밑 16심 리본 z5~9(P27). "
                                  f"r4.5: A-A의 스프링 주머니 Ø{F(SOL['spring']['pocket'][0])}와 미스미 {SOL['spring']['part']} 코일(몸통 {F(SOL['spring']['n'])}권, 길이 {F2(spring_parts('D')[0]['x'][1] - spring_parts('D')[0]['x'][0])}).",
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))


# ================================================================ sheets 5 / 6: key part drawings
def key_only_side(v, P, key, xsec, black, pose="rest"):
    """the key alone, section at xsec + beyond (x < xsec) walls as thin lines."""
    for p in body(key):
        if not cut_x(p, xsec):
            v.poly(pts(p, pose), cls="vis")
    kparts = [p for p in body(key) if cut_x(p, xsec)]
    kb = [pts(p, pose) for p in kparts if p["part"] not in ("capstan head", "rest felt")]
    fill_rings(v, union_rings(kb), "m-black" if black else "m-key", None if black else P["key"])
    g = pin_groove(key)
    v.poly(rect(g["y0"], g["y1"], g["z0"], g["z1"]), cls="void")
    v.poly(rect(g["y0"], g["y1"], g["z0"], g["z1"]), cls="m-clothfar")     # P32 cloth on both side faces (far one seen)
    for p in kparts:
        q = pts(p, pose)
        if p["part"] == "capstan head":
            hpoly(v, q, "m-steel", P["steel"])
            yc, d, zh, zlo, zb = capstan_shank(key)
            v.poly(rect(yc - d / 2, yc + d / 2, zlo, zb), cls="hid")
        elif p["part"] == "rest felt":
            v.poly(q, cls="m-felt")
    kp = KP_B if black else KP_W
    s_, n_ = magnet_polys(*kpt(kp, "magnet face"))
    v.poly(s_, cls="m-magS")
    v.poly(n_, cls="m-magN")
    v.poly(cloth_ring(K), cls="m-cloth")
    # r4.4: the side-wall relief over the rod (S06) lies behind the cut balance block -> hidden edge (the ordinates end on it)
    s06 = dns("S06")
    for p in body(key):
        if (p["part"].startswith("tail wall") or p["part"].startswith("wall L low")) and not cut_x(p, xsec):
            ch = [t for t in pts(p, pose) if s06[0] - 1e-6 <= t[0] <= s06[1] + 1e-6 and t[1] <= s06[2] + 1e-6]
            if len(ch) >= 3:
                v.poly(ch, cls="hid", closed=False)
                break
    v.circle(K[0], K[1], dn("S03", 0, "note") / 2, cls="ph2")
    v.cl(K[0] - 4, K[1], K[0] + 4, K[1])
    v.cl(K[0], K[1] - 4, K[0], K[1] + 4)


def key_xz(v, P, key, y, black):
    kb, ov = [], []
    for p in body(key):
        for z0, z1 in yslice(pts(p), y):
            r_ = rect(p["x"][0], p["x"][1], z0, z1)
            if p["part"] == "capstan head":
                ov.append((r_, "m-steel"))
            elif p["part"] == "rest felt":
                ov.append((r_, "m-felt"))
            else:
                kb.append(r_)
    fill_rings(v, union_rings(kb, res=0.02), "m-black" if black else "m-key", None if black else P["key"])
    for r_, c in ov:
        hpoly(v, r_, c, P["print"] if c == "m-print" else None)
    # magnet Ø5×2 in its pocket from below (P29, plan circle + v3 size): chord of the circle at this y
    mc = pcirc(f"{key} magnet")
    if abs(y - mc[1]) < mc[2]:
        hc = math.sqrt(mc[2] ** 2 - (y - mc[1]) ** 2)
        mf = kpt(KP_B if black else KP_W, "magnet face")
        t = mag_size()[1]
        v.poly(rect(mc[0] - hc, mc[0] + hc, mf[1], mf[1] + t / 2), cls="m-magS")
        v.poly(rect(mc[0] - hc, mc[0] + hc, mf[1] + t / 2, mf[1] + t), cls="m-magN")
    return kb


def key_part_sheet(black):
    n_sheet = 6 if black else 5
    nm = "C#" if black else "D"
    key = f"key {nm}"
    xsec = pcirc(f"{key} balance pin")[0]
    kp = KP_B if black else KP_W
    kparts = body(key)
    y_front = min(bbox(pts(p))[0] for p in kparts)
    y_end = max(bbox(pts(p))[1] for p in kparts)
    ysplit = 100.0 if not black else 118.0
    zt = dns("S02")[2] if black else dns("S02")[0]
    beam = pts(part(key, "beam"))
    tail = pts(part(key, "thin tail"))
    blk = pts(part(key, "balance block"))
    rf = pts(part(key, "rest felt"))
    yc, d, zh, zlo, zb = capstan_shank(key)
    S = 10.4
    halves = [(y_front - 3.0 - 36.0, ysplit + 3.0), (ysplit - 3.0, y_end + 40.0)] if not black else \
             [(y_front - 3.0 - 36.0, ysplit + 3.0), (ysplit - 3.0, y_end + 40.0)]
    # ---- z features per half
    kcut = [pts(p) for p in kparts if cut_x(p, xsec) and p["part"] not in ("capstan head", "rest felt")]
    z_front = min(z0 for q in kcut for z0, z1 in yslice(q, y_front + 0.02))            # lowest drawn edge at the front end
    y_bot = min(t[0] for q in kcut for t in q if abs(t[1] - dns("S02")[1]) < 1e-6)       # where the body bottom edge starts
    cph_ = pts(part(key, "capstan head"))
    zf_front = [(dns("S02")[1], y_bot, "몸체 밑 (S02)"), (zt - 2.0, y_front + 3.0, "윗판 밑"), (zt, dns("P30")[1] if black else y_front, "윗면 (S02)")]
    zf_rear = [(bbox(rf)[2], y_end, "쉼 펠트 밑 (P28)"), (dn("S04", 3), K[0] + 3.2, "노치 입술 (S04)"), (dn("S07", 0), y_end, "빔·꼬리 밑 (S07)"),
               (block_bottom_z(key), bbox(blk)[1], "블록 밑"), (dns("S02")[1], 146.0, "몸체 밑"),
               (max(q[1] for q in tail), y_end - 1.5, "꼬리 위 (S09)"), (zb, yc, "캡스턴 자리"), (dn("S07", 1), 150.0, "빔 위 (S07)"),
               (zh, max(t[0] for t in cph_), "머리 밑"), (dn("S08", 2), yc, "캡스턴 꼭대기 (S08)"), (bbox(blk)[3], bbox(blk)[1], "블록 위·웹 밑"),
               (K[1] + dn("S04", 0), K[0], f"노치 천장 {_labels()['notch']}"), (K[1], K[0] + 2.6, "K"), (zt - 2.0, 147.0, "윗판 밑"), (zt, 147.0, "윗면")]
    if black:
        zf_front += [(bbox(pts(part(key, "wall L low")))[3], y_front + 1.0, "아래·위 옆벽 경계"), (bbox(pts(part(key, "stop floor")))[3], 58.0, "바닥판 위"),
                     (bbox(pts(part(key, "crossbar")))[3], 78.0, "크로스바 위"), (bbox(pts(part(key, "rib")))[2], bbox(pts(part(key, "rib")))[0], "리브 밑")]
        zf_rear += [(bbox(pts(part(key, "rib", 1)))[2], 125.6, "리브 밑")]
    else:
        zf_front += [(bbox(pts(part(key, "rib")))[2], 40.6, "리브 밑"), (bbox(pts(part(key, "down-stop floor")))[3], 9.5, "바닥판 위"),
                     (bbox(pts(part(key, "crossbar")))[3], 14.0, "크로스바 위")]
    yf = [(y_front, z_front, "앞끝"), (K[0], K[1] - 2.0, "K (S03)"), (bbox(blk)[0], 22.3, "블록"), (bbox(pts(part(key, "rear wall")))[1], 23.5, "몸체 끝"),
          (bbox(pts(part(key, "skin" if black else "skin tail")))[1], zt, "윗판 끝 (빼기 턱)"), (yc, zb, "캡스턴 (S08)"),
          (bbox(beam)[1], dn("S07", 0), "빔 끝"), (bbox(rf)[0], bbox(rf)[2], "쉼 펠트"), (y_end, 21.8, "꼬리 끝 (S09)"),
          (kpt(kp, "magnet face")[0], 23.5, "자석 (P29)"), (pin_groove(key)["y1"], 22.3, "핀 홈 끝 (P32)"),
          (max(q[0] for q in tail if q[1] > 24.0), 24.9, "모따기 시작"), (bbox(pts(part(key, "block web")))[0], 30.0, "")]
    for p in kparts:
        if p["part"] in ("rib", "magnet boss", "crossbar"):
            b_ = bbox(pts(p))
            lab = {"rib": "리브", "magnet boss": "자석 보스", "crossbar": "크로스바"}[p["part"]]
            yf += [(b_[0], b_[2], lab), (b_[1], b_[2], "")]
    s06 = dns("S06")                                   # [137, 145, 25.2]: relief over the rod, bottom corners + underside
    for p in kparts:
        if p["part"].startswith("tail wall") or p["part"].startswith("wall L low"):
            qq = pts(p)
            top = [q[0] for q in qq if abs(q[1] - s06[2]) < 1e-6]
            yf += [(s06[0], dns("S02")[1], "옆벽 도려냄 (S06)"), (s06[1], dns("S02")[1], "")]
            yf += [(min(top), s06[2], "경사 끝"), (max(top), s06[2], "")] if top else []
            zf_rear.append((s06[2], max(top) if top else s06[1], "옆벽 도려냄 밑면 (S06)"))
            break
    if black:
        yf += [(bbox(pts(part(key, "stop floor")))[1], 23.5, "바닥판 끝"), (dns("P30")[1], zt, "윗면 앞 (P30)")]
    else:
        yf += [(bbox(pts(part(key, "front wall")))[0], 23.5, "앞벽"), (bbox(pts(part(key, "front wall")))[1], 23.5, ""),
               (bbox(pts(part(key, "down-stop floor")))[1], 23.5, "바닥판 끝"),
               (bbox(pts(part(key, "guide rib L")))[1], 23.5, "가이드 리브 끝"), (bbox(pts(part(key, "skin head")))[1], 41.5, "헤드 끝")]
    side_views = []
    for i, (u0, u1) in enumerate(halves):
        v = View(u0, 3.0, u1, zt + 9.0, px_width=(u1 - u0) * S, pad_px=4)
        P = pids(v)
        i0 = clip_begin(v)
        key_only_side(v, P, key, xsec, black)
        lo_, hi_ = (y_front - 1.0, ysplit) if i == 0 else (ysplit, y_end + 1.0)
        clip_end(v, i0, lo_, hi_, 14.0, zt + 3.0, frame=False)
        v.line(ysplit, 15.0, ysplit, zt + 2.0, cls="phan")
        if i == 0:
            ordz(v, zf_front, y_front - 4.0, side="left", gap_px=12, label_px=9.5)
            panel_title(v, u0 + v.px(4), zt + 9.0 - v.px(14), f"측면 단면 (x = {F2(xsec)}, 핀 홈·자석 중심) — 앞쪽 · 가는 선 = 뒤에 보이는 옆벽·리브", size_px=12)
        else:
            ordz(v, zf_rear, y_end + 4.0, gap_px=12, label_px=9.5)
            panel_title(v, u0 + v.px(4), zt + 9.0 - v.px(14), "측면 단면 — 뒤쪽 (보라 쇄선 = 앞쪽 그림과 이어지는 곳, 숨은선 = 블록 뒤 옆벽 도려냄 S06)", size_px=12)
        ordy(v, [f for f in yf if lo_ - 0.01 <= f[0] <= hi_ + 0.01], 13.0, gap_px=12.5, label_px=9.5)
        side_views.append(v)
    # ---- plan projection (skin transparent), u = y, v = -x, two halves
    xs = [p["x"][0] for p in kparts] + [p["x"][1] for p in kparts]
    x0, x1 = min(xs), max(xs)
    xm = (x0 + x1) / 2
    T = lambda x: -(x - xm)
    order = ["skin head", "skin tail", "skin"]
    plan_views = []
    for i, (u0, u1) in enumerate(halves):
        w2 = View(u0, -(x1 - xm) - 4.0, u1, (xm - x0) + 9.0, px_width=(u1 - u0) * S, pad_px=4)
        lo_, hi_ = (y_front - 1.0, ysplit) if i == 0 else (ysplit, y_end + 1.0)
        i0 = clip_begin(w2)
        for p in kparts:
            if p["part"] in order or p["part"] in ("capstan head", "rest felt"):
                continue
            y0, y1, _, _ = bbox(pts(p))
            w2.poly(rect(y0, y1, T(p["x"][1]), T(p["x"][0])), cls="m-lead" if p["part"].startswith("mass") else "faintfill")
        sk = [rect(bbox(pts(p))[0], bbox(pts(p))[1], T(p["x"][1]), T(p["x"][0])) for p in kparts if p["part"] in order]
        stroke_rings(w2, union_rings(sk, res=0.03), "out")
        c = pcirc(f"{key} capstan")
        w2.circle(c[1], T(c[0]), c[2], cls="m-steel")
        c = pcirc(f"{key} magnet")
        w2.circle(c[1], T(c[0]), c[2], cls="m-magS")
        g = pin_groove(key)
        pc = pcirc(f"{key} balance pin")
        w2.poly(rect(g["y0"], g["y1"], T(pc[0] + g["w"] / 2), T(pc[0] - g["w"] / 2)), cls="void")
        w2.cl(lo_, T(SOL["levers"][nm]), hi_, T(SOL["levers"][nm]))
        clip_end(w2, i0, lo_, hi_, -(x1 - xm) - 1.0, (xm - x0) + 1.0, frame=False)
        w2.line(ysplit, -(x1 - xm) - 1.0, ysplit, (xm - x0) + 1.0, cls="phan")
        # x ordinates (text = x value)
        xf = []
        for p in kparts:
            if p["part"] in ("skin head", "skin", "wall L low", "wall R low", "wall L up", "wall R up", "beam", "balance block", "thin tail",
                             "head wall L", "head wall R", "tail wall L", "tail wall R", "guide rib L", "guide rib R", "skin tail", "magnet boss"):
                b_ = bbox(pts(p))
                if not (lo_ <= (b_[0] + b_[1]) / 2 <= hi_ or lo_ <= b_[0] <= hi_):
                    continue
                yy = min(max(b_[0] + 0.5, lo_ + 0.5), hi_ - 0.5)
                for xx in p["x"]:
                    xf.append((T(xx), yy, f"x{F2(xx)}"))
        xf.append((T(SOL["levers"][nm]), lo_ + 0.5, f"레버·캡스턴 중심 x{F2(SOL['levers'][nm])}"))
        if i == 0:
            ordz(w2, xf, y_front - 4.0, side="left", gap_px=11.5, label_px=9, raw=True)
            panel_title(w2, u0 + w2.px(4), (xm - x0) + 9.0 - w2.px(14), "평면 투영 — 위에서 봄, 윗판 투명 (굵은 선 = 윗판 외곽, 연한 칸 = 벽·리브·블록·빔), 아래로 +x", size_px=12)
        else:
            ordz(w2, xf, y_end + 4.0, gap_px=11.5, label_px=9, raw=True)
        plan_views.append(w2)
    # ---- x-z stations
    if black:
        stations = [(bbox(pts(part(key, "stop floor")))[0] + 2.0, "앞 멈춤 바닥판"), (dn("P29"), "자석 보스·자석 (P29)"),
                    (sum(bbox(pts(part(key, "rib")))[:2]) / 2, "리브 (추 칸 없음)"), (K[0], "노치 (K)"), (170.0, "빔"),
                    (sum(bbox(pts(part(key, "rest felt")))[:2]) / 2, "꼬리·쉼 펠트")]
    else:
        stations = [(20.0, "헤드·가이드 리브"), (dn("P29"), "자석 보스·자석 (P29)"), (100.0, "꼬리"), (K[0], "노치 (K)"),
                    (170.0, "빔"), (sum(bbox(pts(part(key, "rest felt")))[:2]) / 2, "꼬리·쉼 펠트")]
    st_views = []
    sp = 236.0 / 28.0                               # px/mm of the stations (r4.3 value)
    for yy, lab in stations:
        kst = abs(yy - K[0]) < 1e-6                 # r4.4: the K station is wider: it carries the S06 relief ordinate
        wl_, wr_ = (11.0, 29.5) if kst else (13.0, 13.0)
        sv = View(xm - wl_, 11.0, xm + wr_, zt + 8.0, px_width=(wl_ + wr_) * sp, pad_px=6)
        Ps = pids(sv)
        kb = key_xz(sv, Ps, key, yy, black)
        if kst:
            sv.poly(rect(x0 - 1.0, x1 + 1.0, K[1] - dn("S03", 0, "note") / 2, K[1] + dn("S03", 0, "note") / 2), cls="ph2")
            s06 = dns("S06")
            ordz(sv, [(s06[2], x1, "옆벽 도려냄 밑 (S06)"), (K[1] + dn("S04", 0), xm + 1.0, f"노치 천장 {_labels()['notch']}")], x1 + 1.2, gap_px=12, label_px=9)
            sv.text(xm - wl_ + sv.px(2), zt + 8.0 - sv.px(25), f"옆벽은 y{F(s06[0])}~{F(s06[1])}에서 봉 위로 도려냄 (S06)", cls="tx-s", anchor="start", size_px=9)
        panel_title(sv, xm - wl_ + sv.px(2), zt + 8.0 - sv.px(12), f"y{F2(yy)} {lab}", size_px=10.5)
        xs_ = sorted(set([round(q[0], 3) for r_ in kb for q in r_]))
        if xs_:
            def zend(x):     # section bottom at that side edge
                return min(q[1] for r_ in kb if min(t[0] for t in r_) - 1e-3 <= x <= max(t[0] for t in r_) + 1e-3 for q in r_)
            sv.dim_h(xs_[0], xs_[-1], 13.2, text=F2(xs_[-1] - xs_[0]), ext_from=(zend(xs_[0]), zend(xs_[-1])), size_px=8.5)
        st_views.append(sv)
    # ---- variants table
    names = BLACK if black else WHITE

    def raise_txt(b):
        """r4.4 fix 2 / 2b (KE / KF / KF# / KG): beam + thin-tail underside raised in front of the rest felt (the
        return overshoot of the worst material set clears the control board's z20 component zone by 1.3)."""
        q = pts(part(b, "beam")) + pts(part(b, "thin tail"))
        zb = min(t[1] for t in q)
        zs = sorted(set(round(t[1], 4) for t in q if t[1] < zb + 0.5))
        if len(zs) < 2:
            return "—"
        ys = [t[0] for t in q if abs(t[1] - zs[1]) < 1e-6]
        return f"z{kit.FX(zs[1])} y{kit.FR(min(ys), max(ys))}"
    if black:
        cols = ["건반", "밑면 x (P05)", "윗면 x", "블록 x", "핀 홈 x", "빔 x", "꼬리 x (S09)", "레버·캡스턴 x", "자석·탭 x", "캡스턴 y", "빔·꼬리 밑 올림"]
        rows = []
        for n in names:
            b = f"key {n}"
            rows.append([n, kit.FR(part(b, 'wall L low')['x'][0], part(b, 'wall R low')['x'][1]), kit.FR(part(b, 'skin')['x'][0], part(b, 'skin')['x'][1]),
                         kit.FR(part(b, 'balance block')['x'][0], part(b, 'balance block')['x'][1]), kit.FX(pcirc(f'{b} balance pin')[0]),
                         kit.FR(part(b, 'beam')['x'][0], part(b, 'beam')['x'][1]), kit.FR(part(b, 'thin tail')['x'][0], part(b, 'thin tail')['x'][1]),
                         kit.FX(SOL["levers"][n]), kit.FX(pcirc(f'{b} magnet')[0]), kit.FX(pcirc(f'{b} capstan')[1]), raise_txt(b)])
        cw = [60, 140, 140, 140, 90, 140, 140, 110, 100, 90, 170]
    else:
        cols = ["건반", "헤드 x (y0~50)", "꼬리 x (y50~146)", "헤드 턱", "블록 x", "핀 홈 x", "빔·꼬리 x", "레버·캡스턴 x", "자석 x", "탭 x (P31)", "빔·꼬리 밑 올림"]
        rows = []
        for n in names:
            b = f"key {n}"
            steps = " ".join(t for t, k in (("L", "head step L"), ("R", "head step R")) if any(p["part"] == k for p in body(b)))
            tab = fpart(f"tab {n}")
            rows.append([n, kit.FR(part(b, 'skin head')['x'][0], part(b, 'skin head')['x'][1]), kit.FR(part(b, 'skin tail')['x'][0], part(b, 'skin tail')['x'][1]),
                         steps, kit.FR(part(b, 'balance block')['x'][0], part(b, 'balance block')['x'][1]), kit.FX(pcirc(f'{b} balance pin')[0]),
                         kit.FR(part(b, 'beam')['x'][0], part(b, 'beam')['x'][1]), kit.FX(SOL["levers"][n]), kit.FX(pcirc(f'{b} magnet')[0]),
                         kit.FX((tab["x"][0] + tab["x"][1]) / 2), raise_txt(b)])
        cw = [55, 140, 150, 70, 140, 90, 140, 110, 90, 100, 170]
    th = (len(rows) + 1) * 18 + 50
    tv = View(0, -th, 1480, 0, px_width=1480, pad_px=6)
    tv.text(8, -16, f"{'흑건' if black else '백건'} {len(names)}종 x 범위 (geometry.json parts·plan, 모듈 x = 0 C 왼쪽 경계) — y·z 치수는 모두 위 {nm}와 같음 "
            f"(단 빔·꼬리 밑면 z{F2(dn('S07', 0))}를 쉼 펠트 앞에서 올린 건반은 끝 열, r4.4 고침 2·2b: 최악 재료의 복귀 넘침에서 기판 부품 구역과 1.3)"
            + (" · F#·G#·A#은 빔이 밑면 가운데에서 비켜남 (P10)" if black else " · 헤드 턱 = 헤드가 꼬리보다 넓은 쪽"), cls="ttl", anchor="start", size_px=12)
    table(tv, 8, -26, cols, rows, cw, row_px=18, size_px=10)
    # r4.4: overview of the whole key at a smaller scale: the overall length across both halves (the halves break at ysplit)
    So = 5.2
    ov = View(y_front - 42.0, 9.0, y_end + 40.0, zt + 16.0, px_width=(y_end - y_front + 82.0) * So, pad_px=4)
    Po = pids(ov)
    key_only_side(ov, Po, key, xsec, black)
    ov.line(ysplit, 15.0, ysplit, zt + 2.0, cls="phan")
    ov.text(ysplit + ov.px(4), 16.0, f"y{F(ysplit)} = 앞쪽·뒤쪽 그림 경계", cls="tx-s", anchor="start", size_px=9)
    ov.dim_h(y_front, y_end, zt + 6.5, text=f"전체 길이 {F2(y_end - y_front)} (y{F2(y_front)}~{F2(y_end)})",
             ext_from=(z_front if y_front > 0 else zt, 21.8), size_px=10)
    ov.dim_h(y_front, K[0], zt + 2.8, text=f"{F2(K[0] - y_front)} 앞끝 → K (S03)", ext_from=(zt, K[1]), size_px=9.5)
    panel_title(ov, y_front - 41.0, zt + 16.0 - ov.px(13), f"전체 측면 (축소, x = {F2(xsec)}) — 아래 두 그림은 y{F(ysplit)}에서 나눔", size_px=12)
    rows_ = [[ov], [side_views[0]], [plan_views[0]], [side_views[1]], [plan_views[1]], st_views, [tv]]
    lb = _labels()
    title = f"도면 {n_sheet}. {'흑건' if black else '백건'} 부품도 — {nm} 기준 ({len(names)}종)"
    sub = (f"PETG 한 덩어리, 윗면을 베드에 대고 뒤집어 출력 (서포트 = 숨은 빔·꼬리 밑만, DESIGN 14장) · 단위 mm · 숫자 = geometry.json · "
           f"캡스턴 {lb['cap']} + 너트 트랩 (D02), 자석 {lb['magnet']} 압입 + CA (P29), 노치·핀 홈 부싱 천 {F(dn('D01'))}T (D01, P32)" + (" · 추 칸·납 없음 (r4, D13 삭제)" if black else ""))
    base = os.path.join(OUT, f"d{n_sheet:02d}_{'black' if black else 'white'}_key_part")
    page(rows_, base, title, sub)
    SHEETS.append(dict(n=n_sheet, title_ko=f"{'흑건' if black else '백건'} 부품도",
                       caption_ko=(f"{'흑건 C#' if black else '백건 D'}를 기준으로 한 부품도: 맨 위 전체 측면(축소, 전체 길이 {F2(y_end - y_front)}), 측면 단면(앞·뒤 두 토막, 모든 z·y 좌표; 블록 뒤 옆벽 도려냄 S06은 숨은선), 윗판을 투명하게 본 평면 투영(벽·리브·블록·빔 x), "
                                   f"y 위치별 가로 단면 {len(stations)}개, 아래 표에 {'흑건' if black else '백건'} {len(names)}종의 x 범위. y·z 치수는 모든 {'흑건' if black else '백건'}에서 같다 "
                                   f"(r4.4 고침 2·2b: 빔·얇은 꼬리 밑면을 쉼 펠트 앞에서 올린 건반은 표 끝 열 — {', '.join(f'{n_} {raise_txt(f"key {n_}")}' for n_ in names if raise_txt(f"key {n_}") != "—")}; 최악 재료 복귀 넘침에서 기판 부품 구역과 1.3)."
                                   + (f" r4: 추 칸·납·출력 뚜껑을 없앴다(노치 들림은 패드·펠트로 지킴, DESIGN 2.2), 가이드 탭 폭 {F(dns('P31')[3])} (P31)." if black else "")),
                       svg_file=os.path.basename(base) + ".svg", png_file=os.path.basename(base) + ".png"))


# ================================================================ main
def main(which):
    import render_v4b as B
    import render_v4c as C                       # r4.4: drawing 14 (printed tools) and 15 (stage-0 coupons / fixtures)
    todo = {1: lambda: sheet_side(False), 2: lambda: sheet_side(True), 3: sheet_plan, 4: sheet_sections, 5: lambda: key_part_sheet(False),
            6: lambda: key_part_sheet(True), 7: B.sheet_lever, 8: B.sheet_frame, 9: B.sheet_pad_bar_cover_spring, 10: B.sheet_end_parts,
            11: B.sheet_layout, 12: B.sheet_removal, 13: B.sheet_tools, 14: C.sheet_tools14, 15: C.sheet_stage0}
    for n in sorted(todo):
        if not which or n in which:
            todo[n]()
    js = os.path.join(OUT, "drawings.json")
    keep = {}
    if which and os.path.exists(js):              # partial run: keep the other sheets' entries
        keep = {d["n"]: d for d in json.load(open(js))}
    for d in SHEETS + B.SHEETS + C.SHEETS:       # run as __main__, render_v4b records into the imported module's list
        keep[d["n"]] = d
    json.dump([keep[k] for k in sorted(keep)], open(js, "w"), ensure_ascii=False, indent=1)
    print("dims used:", ", ".join(sorted(kit.USED)))


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]])
