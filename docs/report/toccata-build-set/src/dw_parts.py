"""Part drawings (keys, hammers, rails) and details, per method."""
import math
from draw import View, fmt_mm, ord_y, ord_z, f as f_
from drawings_common import hatch, hrect, hpoly, magnet
from model import L, KEYS, TAILS, METHODS, rot, hammer_parts
from field import Bz

SLOT_W = L.get("slot_w", 3.4)      # guide slot width across the key (x); length L.slot_len, depth M.slot_depth
EYE_CL = L["eye_cl"]               # side clearance between an eyelet and each comb fin (B, D) — model value
MAG_POCKET = (6.2, 3.2)            # key magnet pocket Ø x depth (white; black adds M.mag_recess_b)
LAP_HOLE_D = 3.4                   # C lap joint: M3 clearance hole


def dim_v_lab(v, v1, v2, u, text, ext_from=None, where="side", size_px=10.5):
    """vertical dimension whose label is placed explicitly (draw.View.dim_v puts a short dimension's label
    above/below its span, where it can collide with outlines):
    side  = rotated, left of the dimension line (as for a long dimension)
    left  = horizontal, right-aligned left of the dimension line, at mid-span
    above = horizontal, centred above the upper arrow"""
    v.dim_v(v1, v2, u, text="", ext_from=ext_from, size_px=size_px)
    if v.el[-1].startswith("<text") and v.el[-1].endswith("></text>"):
        v.el.pop()                                  # drop dim_v's empty auto label
    a, b = sorted((v1, v2))
    if where == "side":
        v.text(u - v.px(4), (a + b) / 2, text, cls="dt", size_px=size_px, rot=-90)
    elif where == "right":                          # rotated, right of the line, clear of the extension lines
        v.text(u + v.px(16), (a + b) / 2, text, cls="dt", size_px=size_px, rot=-90)
    elif where == "left":
        v.text(u - v.px(6), (a + b) / 2, text, cls="dt", anchor="end", size_px=size_px, dy_px=4)
    else:
        v.text(u, b + v.px(16), text, cls="dt", size_px=size_px)


def key_features(M, black=False):
    """feature list in key-local coords: y along key, z from key underside (0..H)."""
    H, zb = M["H"], M["z_bot"]
    f = dict(H=H, end=M["body_end"], ribs=[], bosses=[], pockets=[], slots=[], notes=[])
    mid = M["id"]
    gy = M["guide_b_y"] if black else M["guide_w_y"]
    f["bosses"].append(("rect", gy - 4, gy + 4, 8.0, "가이드 보스"))
    sl, sd = L["slot_len"], M["slot_depth"]
    f["slots"].append((gy - sl / 2, gy + sl / 2, SLOT_W, sd,
                       f"가이드 슬롯 {fmt_mm(SLOT_W)}×{fmt_mm(sl)} (깊이 {fmt_mm(sd)})"))
    if mid in ("A", "B", "C"):
        ys = L["y_sensor"]
        pd, dep = MAG_POCKET[0], MAG_POCKET[1] + (M.get("mag_recess_b", 0.0) if black else 0.0)
        f["bosses"].append(("circ", ys, 10.0, None, "자석 보스 Ø10"))
        f["pockets"].append((ys, pd, dep, f"자석 포켓 Ø{fmt_mm(pd)} 깊이 {fmt_mm(dep)}"))
    if mid == "A":
        f["ribs"] = [80, 140, 170, 212]
        f["bosses"].append(("circ", 190, 10.0, None, "스프링 보스 Ø10"))
        f["pockets"].append((190, 6.4, 5.0, "스프링 포켓 Ø6.4 깊이 5"))
        f["leaf"] = (M["body_end"], M["body_end"] + M["leaf"], M["leaf_t"])
        f["spine"] = M["spine"]
    if mid == "B":
        f["ribs"] = [80, 140, 172, 212]
        f["bosses"].append(("circ", M["spring_y"], 10.0, None, "스프링 보스 Ø10"))
        f["pockets"].append((M["spring_y"], 6.4, 5.0, "스프링 포켓 Ø6.4 깊이 5"))
        f["eyelet"] = (M["eyelet_y"], M["body_end"], M["pivot"][1] - zb, M["hole_d"])
    if mid == "C":
        f["ribs"] = [80, 140, 180]
        mw, ml = M["bal_mortise"][:2]
        f["balance"] = (M["pivot"][0], M["bal_hole_d"], mw, ml)
        f["bal_boss"] = M["bal_boss"]            # solid block, wall to wall, around the hole and mortise
        a0, a1 = M["rear_part"][0], M["front_part"][1]
        f["lap"] = (a0, a1, 10.0)
        f["lap_screws"] = ((a0 + a1) / 2 - (a1 - a0) / 4, (a0 + a1) / 2 + (a1 - a0) / 4)   # as dw_side.side_C
        f["lap_block"] = (a0, a1 - L["wall"])        # front part: solid wall-to-wall over the lap (z lap..H-skin) so the screws have material
        f["end"] = a1
    if mid == "D":
        f["ribs"] = [80, 112, 205] if not black else [112, 205]
        f["actuator"] = (M["h_push"], M["act_len"], M["h_act"])
        f["act_boss"] = M["act_boss"]            # wall-to-wall boss above the pad (the pad hangs from it)
        f["window"] = M["h_window_b"] if black else M["h_window"]    # over this key's own hammer cradle
        f["eyelet"] = (M["eyelet_y"], M["body_end"], M["pivot"][1] - zb, 4.3)
    if not black and L["head"] not in f["ribs"]:
        f["ribs"] = [L["head"]] + f["ribs"]      # head-to-tail junction rib (as in the assembly sections)
    return f


def rib_span(M, y):
    """(z0, z1) of a transverse rib at key-local y: z0 from the model (None = rib left out), z1 = under the skin."""
    z0 = M["rib_z0"][y]
    return None if z0 is None else (z0, M["H"] - L["skin"])


def key_part(M, keyname="C", black=False):
    k = next(kk for kk in KEYS if kk["name"] == keyname)
    f = key_features(M, black)
    H, end = f["H"], f["end"]
    rear = end
    if "spine" in f:
        rear = f["spine"][1]
    if black:
        y0 = L["head"]
    else:
        y0 = 0.0
    hx0 = k["head"][0] if not black else k["body"][0]
    tb0, tb1 = k["body"][0] - hx0, k["body"][1] - hx0
    hw = (k["head"][1] - k["head"][0]) if not black else L["Bw"]
    gap_v = 26
    # a boss dimension above the side view next to its title lifts the title (16 px): make room for it
    s_px = 1180 / (rear + 100)
    top_dims = [f[kk][0] for kk in ("bal_boss", "act_boss") if kk in f]
    lift = any(b0 < y0 + (3 * 11 + 8) / s_px for b0 in top_dims)
    gap_v += 16 / s_px if lift else 0.0
    top_off = H + gap_v + hw     # top view sits above the side view
    v = View(-30, -40, rear + 70, top_off + 12, px_width=1180)
    kp = hatch(v, "key", 4, -45)
    # ---------------- top view (v = top_off - x')
    T = lambda x: top_off - x
    oend = f["eyelet"][0] if "eyelet" in f else end
    if black:
        outline = [(y0, T(tb0)), (oend, T(tb0)), (oend, T(tb1)), (y0, T(tb1))]
    else:
        outline = [(0, T(0)), (0, T(hw)), (L["head"], T(hw))]
        if tb1 < hw - 0.01:
            outline += [(L["head"], T(tb1))]
        outline += [(oend, T(tb1)), (oend, T(tb0))]
        if tb0 > 0.01:
            outline += [(L["head"], T(tb0)), (L["head"], T(0))]
    # method A: the 12 key bodies are one white-PETG comb print; only the black key's raised cap is printed
    # black and glued on (A-5 print plan). B-D black keys are printed black whole.
    cap_only = black and M["id"] == "A"
    v.poly(outline, cls="kw" if (not black or cap_only) else "kb2")
    if black:
        # raised cap: 9.5 top face (lighter) from the chamfer top edge to the cap end; sides slope down to 11.5
        bi, c = (L["Bw"] - L["Bt"]) / 2, L["black_chamfer"]
        if cap_only:
            v.rect(y0, T(tb1), L["black_end"] - y0, tb1 - tb0, cls="kb2")
        v.poly([(y0 + c, T(tb0 + bi)), (L["black_end"], T(tb0 + bi)), (L["black_end"], T(tb1 - bi)),
                (y0 + c, T(tb1 - bi))], cls="kbt")
    w = L["wall"]
    cav_end = (f["eyelet"][0] if "eyelet" in f else end) - w      # inner end wall (the eyelet is solid)
    # inner cavity hidden lines (tail)
    v.line(y0 + 2.4 if black else L["head"], T(tb0 + w), cav_end, T(tb0 + w), cls="hid")
    v.line(y0 + 2.4 if black else L["head"], T(tb1 - w), cav_end, T(tb1 - w), cls="hid")
    if not black:
        # head cavity, open toward the tail cavity (the junction at y=head is the rib below); a wall at
        # head - w only where the head is wider than the tail
        Lh = L["head"]
        hc = ([(Lh, T(tb1 - w)), (Lh - w, T(tb1 - w)), (Lh - w, T(hw - w))] if tb1 < hw - 0.01 else [(Lh, T(hw - w))])
        hc += [(2.4, T(hw - w)), (2.4, T(w))]
        hc += ([(Lh - w, T(w)), (Lh - w, T(tb0 + w)), (Lh, T(tb0 + w))] if tb0 > 0.01 else [(Lh, T(w))])
        v.poly(hc, cls="hid", closed=False)
    for yr in f["ribs"]:
        if rib_span(M, yr):
            v.line(yr, T(tb0 + w), yr, T(tb1 - w), cls="hid")
    cx = (tb0 + tb1) / 2
    gx = (hw / 2) if not black else cx
    for b in f["bosses"]:
        if b[0] == "rect":
            v.rect(b[1], T(gx + b[3] / 2), b[2] - b[1], b[3], cls="hid")
        else:
            v.circle(b[1], T(cx), b[2] / 2, cls="hid")
    for (py, d, dep, lab) in f["pockets"]:
        v.circle(py, T(cx), d / 2, cls="hid2")
    for (s0, s1, sw, dep, lab) in f["slots"]:
        v.rect(s0, T(gx + sw / 2), s1 - s0, sw, cls="hid2")
    if "leaf" in f:
        l0, l1, lt = f["leaf"]
        v.rect(l0, T(tb1), l1 - l0, tb1 - tb0, cls="leaf")
        s0, s1 = f["spine"]
        v.rect(s0, T(tb1 + 0.5), s1 - s0, tb1 - tb0 + 1.0, cls="kph")
        v.text((s0 + s1) / 2, T(tb1 + 3), "스파인(콤 공통)", cls="tx-s", size_px=9)
    if "eyelet" in f:
        e0, e1, ez, hd = f["eyelet"]
        ew = (tb1 - tb0) + L["gap"] - (M["fin_t"] + 2 * L["eye_cl"])   # slot - fin - 2 x clearance
        ec = cx
        v.rect(e0, T(ec + ew / 2), e1 - e0, ew, cls="kw" if not black else "kb2")
        v.line(M["pivot"][0], T(ec + ew / 2), M["pivot"][0], T(ec - ew / 2), cls="cl")
        dim_v_lab(v, T(ec + ew / 2), T(ec - ew / 2), e1 + 8, f"아이렛 {fmt_mm(ew, 2)}", ext_from=(e1, e1), where="right")
    if "bal_boss" in f:
        b0, b1 = f["bal_boss"]
        v.rect(b0, T(tb1 - w), b1 - b0, (tb1 - tb0) - 2 * w, cls="hid")
    if "balance" in f:
        by, dh, mw, ml = f["balance"]
        v.rect(by - ml / 2, T(cx + mw / 2), ml, mw, cls="hid2")
        v.circle(by, T(cx), dh / 2, cls="hid")
    if "lap" in f:
        a0, a1, lz = f["lap"]
        v.line(a0, T(tb0), a0, T(tb1), cls="hid")
        b0, b1 = f["lap_block"]
        v.rect(b0, T(tb1 - w), b1 - b0, (tb1 - tb0) - 2 * w, cls="hid")
        for yy in f["lap_screws"]:
            v.circle(yy, T(cx), LAP_HOLE_D / 2, cls="hid2")
    if "act_boss" in f:
        b0, b1 = f["act_boss"]
        v.rect(b0, T(tb1 - w), b1 - b0, (tb1 - tb0) - 2 * w, cls="hid")
    if "actuator" in f:
        ay, al, ah = f["actuator"]
        v.rect(ay - al / 2, T(cx + 3), al, 6, cls="hid2")
    if "window" in f:
        w0, w1 = f["window"]
        v.rect(w0, T(tb1 - w), w1 - w0, (tb1 - tb0) - 2 * w, cls="zone")
    # top-view dims
    if not black:
        v.dim_v(T(0), T(hw), -8, text=fmt_mm(hw), ext_from=(0, 0))
        v.dim_v(T(tb0), T(tb1), L["head"] + 45, text=f"{fmt_mm(tb1 - tb0, 2)}")
        if tb0 > 0.01:
            v.dim_v(T(0), T(tb0), L["head"] + 8, text=f"{fmt_mm(tb0, 2)}")
    else:
        v.dim_v(T(tb0), T(tb1), y0 - 16, text=fmt_mm(tb1 - tb0, 2), ext_from=(y0, y0))
        dim_v_lab(v, T(tb0 + bi), T(tb1 - bi), y0 - 8, fmt_mm(L["Bt"], 2), ext_from=(y0 + c, y0 + c))
    v.text(y0, top_off + v.px(14), f"평면도 (위에서, 점선 = 속 형상) — {keyname}{' (흑건)' if black else ' 건반 기준, 다른 백건은 표 참조'}",
           cls="tx", anchor="start", size_px=11)
    # ---------------- side view (z from key underside)
    # underside outline; method C's front part ends in the upper half of the lap joint (the lower half is the rear part)
    lz_end = f["lap"][2] if "lap" in f else 0.0
    base = [(y0, 0)] + ([(f["lap"][0], 0), (f["lap"][0], lz_end), (end, lz_end)] if "lap" in f else [(end, 0)])
    if black:
        c = L["black_chamfer"]
        cap = [(y0, H), (L["black_end"], H), (L["black_end"], H + L["black_h"]), (y0 + c, H + L["black_h"])]
        if cap_only:                                  # white comb body + black cap glued on at z = H
            v.poly(base + [(end, H), (y0, H)], cls="kw")
            v.poly(cap, cls="kb2")
            v.text((y0 + c + L["black_end"]) / 2, H + L["black_h"] / 2, "검정 캡 (따로 출력해 접착)",
                   cls="tx-w", size_px=9.5, dy_px=3.5)
        else:
            v.poly(base + [(end, H)] + cap[1:] + [(y0, H)], cls="kb2")
        v.line(y0, H, L["black_end"], H, cls="ln")
    else:
        v.poly(base + [(end, H), (0, H)], cls="kw")
    top_at = lambda y: H + (L["black_h"] if black and y < L["black_end"] else 0.0)   # key top at y (side view)
    v.line(y0 + 2.4, H - L["skin"], cav_end, H - L["skin"], cls="hid")
    v.line(y0 + 2.4, 0, y0 + 2.4, H - L["skin"], cls="hid")
    v.line(cav_end, lz_end, cav_end, H - L["skin"], cls="hid")
    rh = L["rib"] / 2
    for yr in f["ribs"]:
        rs = rib_span(M, yr)
        if rs:
            v.poly([(yr - rh, rs[0]), (yr - rh, rs[1]), (yr + rh, rs[1]), (yr + rh, rs[0])], cls="hid", closed=False)
    for b in f["bosses"]:
        if b[0] == "rect":
            v.rect(b[1], 0, b[2] - b[1], H - L["skin"], cls="hid")
        else:
            v.rect(b[1] - b[2] / 2, 0, b[2], H - L["skin"], cls="hid")
    for (py, d, dep, lab) in f["pockets"]:
        v.rect(py - d / 2, 0, d, dep, cls="hid2")
    for (s0, s1, sw, dep, lab) in f["slots"]:
        v.rect(s0, 0, s1 - s0, dep, cls="hid2")
    if "leaf" in f:
        l0, l1, lt = f["leaf"]
        v.rect(l0, 0, l1 - l0, lt, cls="leaf")
        s0, s1 = f["spine"]
        v.rect(s0, 0, s1 - s0, H, cls="kph")
        v.dim_v(0, lt, (l0 + l1) / 2, text=f"t {fmt_mm(lt)}")      # on the leaf itself (its middle = virtual pivot)
    if "eyelet" in f:
        e0, e1, ez, hd = f["eyelet"]
        v.line(e0, 0, e0, H, cls="ln")                 # shoulder: width steps down to the eyelet
        v.circle(M["pivot"][0], ez, hd / 2, cls="void")   # through hole, visible from the side
        v.cl(M["pivot"][0], ez - 5, M["pivot"][0], ez + 5)
        v.cl(M["pivot"][0] - 5, ez, M["pivot"][0] + 5, ez)
    if "bal_boss" in f:
        b0, b1 = f["bal_boss"]
        v.rect(b0, 0, b1 - b0, H - L["skin"], cls="hid")
        v.dim_h(b0, b1, top_at(b0) + v.px(12), text=f"밸런스 블록 {fmt_mm(b1 - b0)}", ext_from=(H - L["skin"],) * 2)
    if "balance" in f:
        by, dh, mw, ml = f["balance"]
        mz0, mz1 = M["bal_mortise"][2:]
        v.poly([(by - dh / 2 - 1, 0), (by - dh / 2, 1), (by - dh / 2, mz0), (by - ml / 2, mz0), (by - ml / 2, mz1),
                (by + ml / 2, mz1), (by + ml / 2, mz0), (by + dh / 2, mz0), (by + dh / 2, 1), (by + dh / 2 + 1, 0)],
               cls="hid2", closed=False)
    if "lap_block" in f:
        b0, b1 = f["lap_block"]
        v.rect(b0, f["lap"][2], b1 - b0, H - L["skin"] - f["lap"][2], cls="hid")
    if "lap_screws" in f:
        lz = f["lap"][2]
        for yy in f["lap_screws"]:
            v.rect(yy - LAP_HOLE_D / 2, lz, LAP_HOLE_D, H - L["skin"] - lz, cls="hid2")
    if "act_boss" in f:
        b0, b1 = f["act_boss"]
        v.rect(b0, 0, b1 - b0, H - L["skin"], cls="hid")
        v.dim_h(b0, b1, top_at(b0) + v.px(12), text=f"액추에이터 보스 {fmt_mm(b1 - b0)}", ext_from=(H - L["skin"],) * 2)
    if "actuator" in f:
        ay, al, ah = f["actuator"]
        v.poly([(ay - al / 2, 0), (ay + al / 2, 0), (ay + al / 2 - 2, -ah), (ay - al / 2 + 2, -ah)],
               cls="kw" if not black else "kb2")
    if "window" in f:
        w0, w1 = f["window"]
        v.rect(w0, 0, w1 - w0, H - L["skin"], cls="zone")
        v.text((w0 + w1) / 2, H / 2, "리브 금지(추가 올라옴)", cls="tx-s" if not black else "tx-w", size_px=9)
    # side-view dims
    zdims = [(H, end, "윗면"), (H - L["skin"], cav_end, "윗판 안쪽")]
    if black:
        zdims.append((H + L["black_h"], L["black_end"], "흑건 윗면"))
    if "lap" in f:
        zdims.append((f["lap"][2], end, "이음 턱 (앞 부품 밑면)"))
    ord_z(v, zdims, rear + 6, prefix="h ")
    feats = []
    for b in f["bosses"]:
        feats.append((b[1] if b[0] == "circ" else (b[1] + b[2]) / 2, 0, b[4]))
    for yr in f["ribs"]:
        rs = rib_span(M, yr)
        if rs and not (not black and yr == L["head"]):
            feats.append((yr, rs[0], "리브"))
    if not black:
        feats.append((L["head"], H, "머리 끝 · 리브" if rib_span(M, L["head"]) else "머리 끝"))
    feats.append((end, lz_end, "앞 부품 끝" if "lap" in f else "몸체 끝"))
    for yy in f.get("lap_screws", ()):
        feats.append((yy, f["lap"][2], f"이음 나사 Ø{fmt_mm(LAP_HOLE_D)}"))
    if "leaf" in f:
        feats.append((f["leaf"][1], 0, "힌지 끝"))
        feats.append((f["spine"][1], 0, "스파인 끝"))
    if "eyelet" in f:
        feats.append((f["eyelet"][0], 0, "아이렛 시작"))
        feats.append((M["pivot"][0], f["eyelet"][2], "축 구멍"))
    if "balance" in f:
        feats.append((f["balance"][0], 0, "밸런스 구멍"))
        feats.append((f["lap"][0], 0, "이음 턱"))
    if "actuator" in f:
        feats.append((f["actuator"][0], -f["actuator"][2], "액추에이터"))
    if "window" in f:
        feats.append((f["window"][0], 0, "창 시작"))
        feats.append((f["window"][1], 0, "창 끝"))
    if black:
        feats.append((y0, 0, "흑건 앞"))
        feats.append((L["black_end"], H + L["black_h"], "윗면 끝"))
    row = -6 - (f["actuator"][2] if "actuator" in f else 0.0)     # ordinate row below the lowest feature
    ord_y(v, feats, row, gap_px=12.5, label_px=9.5)
    lab_w = max(v.text_w(f"{fmt_mm(y, 1)}  {lab}", 9.5) for y, _, lab in feats)
    v.v0 = min(v.v0, row - v.px(9 + 2) - lab_w)                    # keep the longest rotated label in view
    tz = top_at(y0) + v.px(14) + (v.px(16) if lift else 0.0)
    v.text(y0, tz, "측면도", cls="tx", anchor="start", size_px=11)
    return v.svg(aria=f"방식 {M['id']} {'흑건' if black else '백건'} 부품도")


# ------------------------------------------------------------------- sections (shared, 6 px/mm)
def key_sections(M):
    H = M["H"]
    v = View(-8, -14, 150, H + L["black_h"] + 16, px_width=820)
    kp = hatch(v, "key", 3, -45)
    s, w = L["skin"], L["wall"]
    def ushape(x0, W, Hh, lab):
        outer = [(x0, 0), (x0, Hh), (x0 + W, Hh), (x0 + W, 0), (x0 + W - w, 0), (x0 + W - w, Hh - s),
                 (x0 + w, Hh - s), (x0 + w, 0)]
        hpoly(v, outer, kp, "m-key")
        v.dim_h(x0, x0 + W, -5, text=fmt_mm(W, 2), ext_from=(0, 0))
        v.dim_v(0, Hh, x0 - 3, text=fmt_mm(Hh), ext_from=(x0, x0))
        v.text(x0 + W / 2, Hh + v.px(22), lab, cls="tx", size_px=10.5)
    ushape(0, L["Pw"] - L["gap"], H, "A-A 백건 머리 (y=30)")
    ushape(34, TAILS["ce_w"], H, "B-B 꼬리 C·D·E")
    ushape(62, TAILS["fb_w"], H, "C-C 꼬리 F·G·A·B")
    # black key section
    x0 = 92
    Bw, Bt, bh = L["Bw"], L["Bt"], L["black_h"]
    outer = [(x0, 0), (x0, H), (x0 + (Bw - Bt) / 2, H + bh), (x0 + (Bw + Bt) / 2, H + bh), (x0 + Bw, H), (x0 + Bw, 0),
             (x0 + Bw - w, 0), (x0 + Bw - w, H - s), (x0 + w, H - s), (x0 + w, 0)]
    hpoly(v, outer, kp, "m-blk")
    v.dim_h(x0, x0 + Bw, -5, text=fmt_mm(Bw, 2), ext_from=(0, 0))
    v.dim_h(x0 + (Bw - Bt) / 2, x0 + (Bw + Bt) / 2, H + bh + 4, text=fmt_mm(Bt, 2), ext_from=(H + bh, H + bh))
    v.dim_v(H, H + bh, x0 + Bw + 4, text=fmt_mm(bh), ext_from=(x0 + Bw, x0 + (Bw + Bt) / 2))
    v.text(x0 + Bw / 2, H + bh + v.px(44), "D-D 흑건 (y=100)", cls="tx", size_px=10.5)
    # note block
    v.text(116, H + 6, f"벽 {w} (0.4 노즐 4줄)", cls="tx-s", anchor="start", size_px=10)
    v.text(116, H + 1, f"윗판 {s} (0.2 층 10장)", cls="tx-s", anchor="start", size_px=10)
    v.text(116, H - 4, f"리브 {fmt_mm(L['rib'])}, 밑에서 {fmt_mm(L['rib_z0'])} 띄움", cls="tx-s", anchor="start", size_px=10)
    v.text(116, H - 9, "모서리 R0.6 (윗면)", cls="tx-s", anchor="start", size_px=10)
    return v.svg(aria="건반 단면도")


# ------------------------------------------------------------------- sensor detail (shared)
def sensor_detail():
    v = View(-10, -8, 62, 24, px_width=round(760 / 64 * 72))     # 11.875 px/mm as before, 8 mm more on the left
    pp = hatch(v, "print", 3, 45)
    kp = hatch(v, "key", 2.5, -45)
    A = METHODS[0]
    st = A["sensor_top"]
    # rail section (y horizontal, local u = y - rail front); same rail / recess / channel as side_common
    ry0, ry1 = A.get("srail", (98.0, 126.0))
    rail_w = ry1 - ry0
    mag_u = L["y_sensor"] - ry0                               # sensor, element and magnet centre
    rec0, rec1, rec_d = mag_u - L["pocket_h"], mag_u + L["pocket_h"], L["pocket_d"]
    c0, c1 = L["wire_ch"][0] - ry0, L["wire_ch"][1] - ry0
    ls = L["lead_slot"]
    # same profile as drawings_common.side_common: the recess floor runs on as a lead groove to the wire
    # channel, where an ls-wide slot drops into it (section at the key centre: rail cut in two; the recess
    # end at rec1 is seen beyond)
    hpoly(v, [(0, 0), (0, st), (rec0, st), (rec0, st - rec_d), (c0, st - rec_d), (c0, 0)], pp, "m-print")
    hpoly(v, [(c0 + ls, 5), (c0 + ls, st), (rail_w, st), (rail_w, 0), (c1, 0), (c1, 5)], pp, "m-print")
    v.line(rec1, st - rec_d, rec1, st, cls="ln")
    v.rect(mag_u - 1.5, st - 1.52, 3.0, 1.52, cls="m-sensor")
    v.line(mag_u + 1.5, st - 0.76, c0 + ls / 2, st - 0.76, cls="lead")     # along the groove
    v.line(c0 + ls / 2, st - 0.76, c0 + ls / 2, 4.0, cls="lead")          # down the slot
    v.line(c0 + ls / 2, 4.0, c0 + 2, 3.0, cls="lead")                     # to the first wire
    v.dim_h(c0, c0 + ls, st + v.px(14), text=f"리드 홈 {fmt_mm(ls)}", ext_from=(st - rec_d, st))
    for xx in (c0 + 2, c0 + 4.4, c0 + 6.8):
        v.circle(xx, 2.5, 1.1, cls="m-wire")
    # element
    ed = L["elem_depth"]
    v.circle(mag_u, st - ed, 0.35, cls="pivot")
    # key underside + magnet at rest (A) and pressed (ghost)
    gup, gdn = A["g_up"], A["g_dn"]
    ky = st + gup
    key_u0, key_w, key_t = mag_u - 10.0, 20.0, 5.0            # key underside strip around the magnet
    pk_d, pk_h = MAG_POCKET                                   # magnet pocket Ø x depth
    mag_d = 6.0                                               # magnet Ø6 x 3
    hrect(v, key_u0, ky, key_w, key_t, kp, "m-key")
    v.rect(mag_u - pk_d / 2, ky, pk_d, pk_h, cls="void")
    magnet(v, mag_u, ky)
    v.rect(mag_u - mag_d / 2, st + gdn, mag_d, 3, cls="pressed")
    # gaps (left of the rail): extension lines from the rail top front corner, the pressed magnet face and the key underside
    dim_v_lab(v, st, st + gdn, -v.px(40), f"끝 {gdn:.2f}", ext_from=(0, mag_u - mag_d / 2), where="above")
    v.dim_v(st, ky, -v.px(80), text=f"휴지 {gup:.2f}", ext_from=(0, key_u0))
    v.dim_h(rec0, rec1, st - rec_d - v.px(14), text=fmt_mm(rec1 - rec0), ext_from=(st - rec_d, st - rec_d))
    v.dim_h(mag_u - pk_d / 2, mag_u + pk_d / 2, ky + key_t + v.px(14), text=f"Ø{fmt_mm(pk_d)}",
            ext_from=(ky + pk_h, ky + pk_h))
    v.dim_v(st - rec_d, st, rec0 - v.px(14), text=fmt_mm(rec_d), ext_from=(rec0, rec0))
    v.dim_v(ky, ky + pk_h, mag_u - pk_d / 2 - v.px(14), text=fmt_mm(pk_h),
            ext_from=(mag_u - pk_d / 2, mag_u - pk_d / 2))
    v.leader(mag_u, st - ed, 46, 2, f"홀 소자: 각인면 아래 약 {fmt_mm(ed)} mm")
    v.leader(c0 + 4.4, 2.5, 46, -3, "배선: VCC·GND 버스 + 신호선 (AWG28)")
    v.leader(mag_u, ky + 1.5, 46, 16, "자석 Ø6×3 N35 (축 방향 자화)")
    v.leader(mag_u, st + gdn + 1.5, 46, 11, "눌림 끝 위치 (방식 A)", cls="ld")
    v.text(0, -6, f"센서 레일 단면 (y {fmt_mm(ry0)}~{fmt_mm(ry1)}, 확대 약 {v.s * 25.4 / 96:.0f}:1, 최대 폭 기준)",
           cls="tx", anchor="start", size_px=10.5)
    return v.svg(aria="홀센서·자석 상세도")


# ------------------------------------------------------------------- field curve chart
def field_chart():
    """B at the Hall element vs magnet gap, with each method's working window."""
    W = 640
    x0, y0, x1 = 58, 20, W - 20
    plot_h = 240
    y1 = y0 + plot_h
    band = y1 + 56                     # working-window bars sit below the axis (their x is the gap in mm)
    H = band + 16 * (len(METHODS) - 1) + 14
    gmin, gmax, bmax = 2.0, 11.0, 140.0
    ed = L["elem_depth"]
    X = lambda g: x0 + (g - gmin) / (gmax - gmin) * (x1 - x0)
    Y = lambda b: y1 - b / bmax * (y1 - y0)
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="자석 거리별 자기장" xmlns="http://www.w3.org/2000/svg">']
    for b in range(0, 141, 20):
        out.append(f'<line class="grid" x1="{x0}" y1="{Y(b):.1f}" x2="{x1}" y2="{Y(b):.1f}"/>')
        out.append(f'<text class="ax" x="{x0-8}" y="{Y(b)+4:.1f}" text-anchor="end">{b}</text>')
    for g in range(2, 12):
        out.append(f'<text class="ax" x="{X(g):.1f}" y="{y1+18}" text-anchor="middle">{g}</text>')
    out.append(f'<text class="ax" x="{(x0+x1)/2}" y="{y1+36}" text-anchor="middle">자석 면 ↔ 센서 면 거리 (mm)</text>')
    out.append(f'<text class="ax" x="14" y="{(y0+y1)/2}" text-anchor="middle" transform="rotate(-90 14 {(y0+y1)/2})">자기장 (mT)</text>')
    # linear range of A3
    out.append(f'<rect class="lim" x="{x0}" y="{Y(88):.1f}" width="{x1-x0}" height="{Y(0)-Y(88):.1f}"/>')
    out.append(f'<text class="ax" x="{x1-4}" y="{Y(88)-5:.1f}" text-anchor="end">DRV5055A3 선형 한계 ±88 mT (3.3 V)</text>')
    pts = []
    g = gmin
    while g <= gmax + 1e-9:
        pts.append(f"{X(g):.1f},{Y(Bz(g + ed)):.1f}")
        g += 0.1
    out.append(f'<polyline class="curve" points="{" ".join(pts)}"/>')
    for i, M in enumerate(METHODS):
        a, b = sorted((M["g_up"], M["g_dn"]))
        yy = band + i * 16
        out.append(f'<line class="win w{i}" x1="{X(a):.1f}" y1="{yy}" x2="{X(b):.1f}" y2="{yy}"/>')
        out.append(f'<text class="ax" x="{X(b)+6:.1f}" y="{yy+4}">{M["id"]}  {a:.1f}–{b:.1f} mm · {Bz(b+ed):.0f}–{Bz(a+ed):.0f} mT</text>')
        # the same window's end points on the curve (mm on x, mT on y)
        for gg in (a, b):
            r = 4 + 1.5 * (len(METHODS) - 1 - i)          # nested rings: coincident end points stay visible
            out.append(f'<circle class="w{i}" cx="{X(gg):.1f}" cy="{Y(Bz(gg + ed)):.1f}" r="{r:g}" style="fill:var(--card,#fff);stroke-width:2.5"/>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------- pivot details
def detail_A(M):
    # local u = y - body_end (leaf starts at u 0), z from the key underside; the keybed is at -z_bot
    zt, lt, ll = M["H"], M["leaf_t"], M["leaf"]
    zbk = M["z_bot"]
    yb = M["body_end"]
    s0 = M["spine"][0] - yb                     # spine front face (= leaf end)
    sp = M["spine"][1] - M["spine"][0]          # spine length
    b0, b1 = M["blk"][0] - yb, M["blk"][1] - yb  # printed support block under the spine (shared with side_A)
    body_len = 6.0                              # visible stub of the key body
    s_px = 600 / 66                             # drawing scale (px/mm)
    u0 = -(body_len + 6)
    bolt = L["spine_bolt"]                      # M3 x bolt under its head on the spine top (as side_A)
    zbt = zt - bolt                             # bolt tip (key-local z)
    emb = -zbk - zbt                            # bolt length in the keybed plywood
    ply = emb + 3.5                             # plywood stub shown down to a break line
    lab_b = f"받침 블록 + M3×{fmt_mm(bolt)} 볼트 (합판 {fmt_mm(emb)} 박힘)"
    tu_r = 44                                   # right leader text anchor
    u1 = max(60.0, tu_r + (6 + 3 + 6) / s_px + View(0, 0, 1, 1, px_width=s_px).text_w(lab_b, 11))
    v = View(u0, min(-(zbk + 4), -(zbk + ply) - 2.5), u1, 30, px_width=round(s_px * (u1 - u0)))
    kp = hatch(v, "key", 3, -45)
    pp = hatch(v, "print", 4, 45)
    wd = hatch(v, "wood", 5, 45)
    hrect(v, -body_len, 0, body_len, zt, kp, "m-key")
    hrect(v, 0, 0, ll, lt, kp, "m-key")
    hrect(v, s0, 0, sp, zt, kp, "m-key")
    hrect(v, b0, -zbk, b1 - b0, zbk, pp, "m-print")
    # keybed plywood under the block (stub, Z break line at the bottom)
    pa, pb, zp = b0 - 6, b1, -zbk - ply
    pm = (pa + pb) / 2
    hpoly(v, [(pa, -zbk), (pb, -zbk), (pb, zp), (pm + 1.0, zp), (pm + 0.4, zp + 1.2), (pm - 0.4, zp - 1.2),
              (pm - 1.0, zp), (pa, zp)], wd, "m-wood")
    bc, br = s0 + sp / 2, 1.7                   # M3 spine bolt on the spine centre (hidden shank, tip in the plywood)
    v.rect(bc - br, zbt, 2 * br, zt - zbt, cls="m-steel ph")
    v.rect(bc - 2 * br, zt, 4 * br, 2.2, cls="m-steel")
    # inner corner fillets (leaf top to body end face, leaf top to spine front face)
    r = 1.0
    v.path(f"M {f_(0)},{f_(-lt)} L {f_(0)},{f_(-(lt + r))} A {f_(r)} {f_(r)} 0 0 0 {f_(r)},{f_(-lt)} Z", cls="m-key")
    v.path(f"M {f_(s0)},{f_(-lt)} L {f_(s0)},{f_(-(lt + r))} A {f_(r)} {f_(r)} 0 0 1 {f_(s0 - r)},{f_(-lt)} Z", cls="m-key")
    v.dim_h(0, ll, lt + (zt - lt) / 2, text=fmt_mm(ll))          # between the body end face and the spine face
    v.dim_v(0, lt, ll / 2 + 3, text=fmt_mm(lt))
    v.dim_v(0, zt, -body_len - v.px(24), text=fmt_mm(zt), ext_from=(-body_len, -body_len))
    v.dim_h(s0, s0 + sp, zt + 3, text=fmt_mm(sp), ext_from=(zt, zt))
    v.dim_v(-zbk, 0, b1 + v.px(40), text=fmt_mm(zbk), ext_from=(b1, b1))
    v.dim_v(zbt, -zbk, b1 + v.px(40), text=fmt_mm(emb), ext_from=(bc + br, b1))     # bolt tip in the plywood
    v.circle(ll / 2, lt / 2, v.px(3), cls="pivot")
    v.leader(ll / 2, lt / 2, s0 + sp + v.px(14), 14, f"가상 피벗 (힌지 중앙) · 변형률 {M['flex']['strain']*100:.2f} %")
    v.leader(-body_len / 2, zt - 3, 14, 26, f"건반 몸체 끝 (y {fmt_mm(yb)})")
    v.leader((bc + br + s0 + sp) / 2, zt - 3, 44, 26, f"스파인 (y {fmt_mm(M['spine'][0])}~{fmt_mm(M['spine'][1])})")
    v.leader((bc + br + b1) / 2, -zbk / 2, tu_r, -12, lab_b)
    k = r * (1 - math.sqrt(0.5))                # fillet arc midpoint
    v.leader(s0 - k, lt + k, 8, -12, f"안쪽 모서리 R{r:.1f}", anchor="end")
    return v.svg(aria="A 탄성 힌지 상세")


def detail_B(M):
    """top view of eyelets between comb fins + side of the eyelet."""
    # v = y - comb front: fins v 0..(comb length); the key eyelet runs from the shoulder (eyelet_y) to the key end
    c0, c1 = M["comb"]
    e0, e1 = key_features(M)["eyelet"][:2]
    ve0, ve1, vf, vs = e0 - c0, e1 - c0, c1 - c0, M["pivot"][0] - c0
    rf = min(-5.0, ve0 - 2.5)                   # fin-thickness dimension row, below the eyelet fronts
    v = View(-4, -22, 64, max(26.0, ve1 + 7), px_width=620)
    ks = KEYS[4:8]     # E, F, F#, G
    base = ks[0]["slot"][0]
    ft, cl = M["fin_t"], L["eye_cl"]            # comb fin thickness, eyelet-to-fin clearance
    for k in ks:
        s0, s1 = k["slot"][0] - base, k["slot"][1] - base
        cx = (s0 + s1) / 2
        ew = (s1 - s0) - (ft + 2 * cl)
        v.rect(cx - ew / 2, ve0, ew, ve1 - ve0, cls="kw" if not k["black"] else "kb2")
        v.dim_h(cx - ew / 2, cx + ew / 2, ve1 + 2, text=fmt_mm(ew, 2), size_px=9.5, ext_from=(ve1, ve1))
        v.line(cx, ve0 - 1, cx, ve1 + 1, cls="cl")
        v.text(cx, vs - v.px(15), k["name"], cls="tx" if not k["black"] else "tx-w", size_px=10)   # below the Ø shaft line
    for k in ks + [None]:
        xb = (k["slot"][0] if k else ks[-1]["slot"][1]) - base
        v.rect(xb - ft / 2, 0, ft, vf, cls="m-print2")
    xe = ks[-1]["slot"][1] - base + ft / 2      # rear face of the last fin
    v.line(-3, vs, xe + v.px(60), vs, cls="shaft")
    xb = ks[1]["slot"][0] - base
    v.dim_h(xb - ft / 2, xb + ft / 2, rf, text=f"핀 {ft:.1f}", ext_from=(0, 0))
    v.dim_h(xb + ft / 2, xb + ft / 2 + cl, rf - 7, text=f"틈 {fmt_mm(cl)}", ext_from=(0, ve0))
    v.text(xe + v.px(4), vs + v.px(4), f"Ø{fmt_mm(M['shaft_d'])} 샤프트", cls="tx-s", anchor="start", size_px=10)
    v.text(0, -20, "힌지 콤 평면 (E·F·F#·G 구간)", cls="tx", anchor="start", size_px=10.5)
    return v.svg(aria="B 힌지 콤 상세")


def detail_C(M):
    # section along the key through the balance hole; z from the key underside (keybed top at -z_bot)
    H, zb = M["H"], M["z_bot"]
    bp = M["bal_pin"]
    pd, pl, emb = bp["d"], bp["len"], bp["embed"]
    kf = key_features(M)
    by, dh, mw, ml = kf["balance"]
    b0, b1 = (yy - by for yy in kf["bal_boss"])   # solid balance block (wall to wall), u = y - pivot
    la, lz = kf["lap"][0] - by, kf["lap"][2]    # lap joint: rear part below lz from la on
    sk = L["skin"]
    ch = 1.0                                   # lower hole chamfer
    mt0, mt1 = M["bal_mortise"][2:]            # mortise bottom / top (same as key_part)
    fb = M["balrail_top"] - zb                 # felt underside = balance rail top
    pch = M["punch_d"]                         # balance-rail felt punching Ø (fits the minimum key pitch)
    lab_l = f"아래 구멍 Ø{fmt_mm(dh)} + 모따기 {fmt_mm(ch)}: 흔들 여유 {fmt_mm(M['bal_hole_clear'], 1)} 이상"
    lab_b = f"밸런스 블록 {fmt_mm(b1 - b0)} (양쪽 벽까지 속채움)"
    s_px = 560 / 66                            # drawing scale (px/mm)
    tu_l = -20                                 # left leader text anchor (text runs leftwards from here)
    tw = View(0, 0, 1, 1, px_width=s_px).text_w
    u0 = min(-26.0, tu_l - (9 + 12) / s_px - max(tw(lab_l, 11), tw(lab_b, 11)))
    bt = L["base_t"]                           # keybed plywood thickness
    v = View(u0, -(zb + bt + 4), 40, 30, px_width=round(s_px * (40 - u0)))
    kp = hatch(v, "key", 3, -45)
    pp = hatch(v, "print", 4, 45)
    wd = hatch(v, "wood", 5, 45)
    # the key is a hollow shell (cut at its centre plane): far wall beyond, top skin and the balance block cut
    v.rect(-24, 0, 48, H - sk, cls="m-keyfar")
    hrect(v, -24, H - sk, 48, sk, kp, "m-key")
    hrect(v, b0, 0, b1 - b0, H - sk, kp, "m-key")
    v.rect(-24, 0, 48, H, cls="ln")
    v.poly([(la, 0), (la, lz), (24, lz)], cls="edge", closed=False)       # lap seam on the far wall
    v.text((la + 24) / 2, lz / 2, "뒤 부품", cls="tx-s", size_px=9.5, dy_px=3.5)
    v.rect(-dh / 2, 0, dh, mt0, cls="void")
    v.rect(-ml / 2, mt0, ml, mt1 - mt0, cls="void")
    v.poly([(-dh / 2 - ch, 0), (-dh / 2, ch), (dh / 2, ch), (dh / 2 + ch, 0)], cls="void")
    hrect(v, -24, -zb - bt, 48, bt, wd, "m-wood")                       # keybed plywood
    hrect(v, -12, -zb, 24, M["balrail_top"], pp, "m-print")            # balance rail
    v.rect(-pch / 2, fb, pch, -fb, cls="m-felt")
    v.rect(-pd / 2, -zb - emb, pd, pl, cls="m-steel")                  # pin: embed in the plywood, tip in the mortise
    v.dim_h(-dh / 2, dh / 2, 6, text=f"Ø{fmt_mm(dh, 1)}")
    v.dim_h(-ml / 2, ml / 2, H + v.px(14), text=f"{fmt_mm(ml, 1)} (길이 방향)", ext_from=(mt1, mt1))
    v.dim_h(-pch / 2, pch / 2, fb - v.px(14), text=f"펀칭 Ø{fmt_mm(pch)}×{fmt_mm(L['felt'])} (눌려 {fmt_mm(-fb)})", ext_from=(fb, fb))
    # mortise depth on the left wall, label beside it (an auto label above would sit on the key top)
    dim_v_lab(v, mt0, mt1, -ml / 2 - v.px(16), fmt_mm(mt1 - mt0), ext_from=(-ml / 2, -ml / 2), where="left")
    tip = -zb - emb + pl                       # pin tip (key-local z)
    v.leader((pd / 2 + ml / 2) / 2, (mt0 + min(tip, mt1)) / 2, 20, 25, f"윗 모티스 {fmt_mm(mw)} 폭: 좌우 흔들림 잡음")
    v.leader(-(dh / 2 + ch / 2), ch / 2, tu_l, 25, lab_l, anchor="end")
    v.leader(b0 + 0.6, 1.2, tu_l, -6, lab_b, anchor="end")          # low corner: below the hole leader
    v.leader(0, -10, 20, -12, f"밸런스 핀 Ø{fmt_mm(pd)}×{fmt_mm(pl)} (합판 {fmt_mm(emb)} 박힘)")
    return v.svg(aria="C 밸런스 핀 상세")


def hammer_beam(M):
    """PETG hammer beam outline (world y, z at rest) — shared with side_D via model.hammer_parts."""
    return hammer_parts(M)["beam"]


def detail_D(M):
    """hammer part drawing (side): beam + printed cradle + steel bar + 2 screws from below."""
    hpv = M["h_pivot"]
    hu, ht = M["h_under"], M["h_top"]
    w0, w1 = M["h_weight"]
    wz0, wz1 = M["h_w_z"]
    c0, c1 = M["h_cradle"]
    cz0, cz1 = M["h_cradle_z"]
    y0 = M["h_front"]
    HP = hammer_parts(M)
    v = View(y0 - 6, -24 - (hu - cz0), c1 + 60, 30, px_width=1000)
    pp = hatch(v, "print", 4, 45)
    sp = hatch(v, "steel", 3, -45)
    z = lambda zz: zz - hu
    beam = [(y, z(zz)) for y, zz in HP["beam"]]
    hpoly(v, beam, pp, "m-print2")
    hpoly(v, [(y, z(zz)) for y, zz in HP["cradle"]], pp, "m-print2")
    hpoly(v, [(y, z(zz)) for y, zz in HP["bar"]], sp, "m-steel")
    for (sy, sz, sw, sh) in HP["screws"]:
        v.rect(sy, z(sz), sw, sh, cls="m-steel ph")
    for ck in HP["csk"]:                        # countersunk heads flush in the cradle floor
        v.poly([(y, z(zz)) for y, zz in ck], cls="m-steel")
    hd = M["h_hole_d"]
    v.circle(hpv[0], z(hpv[1]), hd / 2, cls="void")
    pk_d, pk_h = MAG_POCKET
    v.rect(L["y_sensor"] - pk_d / 2, 0, pk_d, pk_h, cls="void")
    v.rect(M["h_push"] - 4, z(ht), 8, 2, cls="m-felt")
    # beam width steps down at the hammer comb's rear end (slot - 3.4 in front, h_rear_w behind): edge line
    hc1 = M["h_comb"][1]
    zc = [a[1] + (b[1] - a[1]) * (hc1 - a[0]) / (b[0] - a[0]) for a, b in zip(beam, beam[1:] + beam[:1])
          if a[0] != b[0] and min(a[0], b[0]) <= hc1 <= max(a[0], b[0])]
    v.line(hc1, min(zc), hc1, max(zc), cls="ln")
    sy = M["h_screw_y"]
    ord_y(v, [(beam[0][0], beam[0][1], "앞끝"), (M["h_push"], z(ht), "누름 패드"), (hpv[0], z(hpv[1]), f"축 Ø{fmt_mm(hd)}"),
              (hc1, min(zc), f"폭 {fmt_mm(M['h_rear_w'])}"),
              (L["y_sensor"], 0, "자석 포켓"), (c0, z(cz0), "받침 앞"), (w0, z(wz0), "추 앞"), (sy[0], z(cz0), "나사"),
              (sy[1], z(cz0), "나사"), (w1, z(wz0), "추 끝"), (c1, z(cz0), "뒤끝")], z(cz0) - 4, gap_px=15)
    ord_z(v, [(z(cz0), c1, "받침 바닥"), (z(wz0), w1, "추 밑"), (0, c0, "해머 밑"), (z(hpv[1]), hpv[0] + hd / 2, "축 중심"),
              (z(ht), c0, "해머 위"), (z(wz1), c1, "추·받침 위")], c1 + 6, prefix="h ")
    v.text(y0, z(wz1) + v.px(32), f"해머 부품도 (PETG) · 폭: 앞끝~{fmt_mm(hc1)} 슬롯 − 3.4, {fmt_mm(hc1)}~받침 "
           f"{fmt_mm(M['h_rear_w'])} mm, 받침 {fmt_mm(M['h_cradle_w'])} mm",
           cls="tx", anchor="start", size_px=10.5)
    v.text(y0, z(wz1) + v.px(16), f"추 {M['w_bar']} × 백 {M['w_len']} / 흑 {M['w_len_b']} mm · "
           f"받침 바닥·끝벽 {fmt_mm(M['h_ct'])} mm · 밑에서 {M['h_screw']} {len(sy)}개로 고정",
           cls="tx", anchor="start", size_px=10.5)
    cb0, cb1 = M["h_cradle_b"]
    wb0, wb1 = M["h_weight_b"]
    syb = M["h_screw_y_b"]
    v.text(y0, z(wz1) + v.px(48), f"흑건 해머(그림은 백건): 빔 {fmt_mm(hc1)}~{fmt_mm(cb0)} 폭 {fmt_mm(M['h_rear_w'])}, "
           f"받침 {fmt_mm(cb0)}~{fmt_mm(cb1)}, 추 {fmt_mm(wb0)}~{fmt_mm(wb1)}, 나사 y {fmt_mm(syb[0])}·{fmt_mm(syb[1])} — 나머지는 같음",
           cls="tx", anchor="start", size_px=10.5)
    return v.svg(aria="D 해머 부품도")


DETAIL = dict(A=detail_A, B=detail_B, C=detail_C, D=detail_D)

if __name__ == "__main__":
    import sys
    css = open("dwg.css").read() + """
.dwg .hid{fill:none;stroke:#6b7690;stroke-width:.8px;stroke-dasharray:4 2.5}
.dwg .hid2{fill:none;stroke:#1f5fbf;stroke-width:.9px;stroke-dasharray:3 2}
.dwg .kb2{fill:#3a3e46;stroke:#1d2433;stroke-width:1.2px}
.dwg .m-blk{fill:#3a3e46;stroke:#1d2433;stroke-width:1px}
.dwg .leaf{fill:#f6c89a;stroke:#1d2433;stroke-width:1px}
.dwg .tx-w{fill:#fff}
.dwg .shaft{stroke:#5d6778;stroke-width:2.5px}
.chart .grid{stroke:#e3e7ee}.chart .ax{fill:#5a6378;font:11px system-ui}.chart .curve{fill:none;stroke:#1f5fbf;stroke-width:2}
.chart .lim{fill:#1f5fbf;fill-opacity:.05}.chart .win{stroke-width:6;stroke-linecap:round}.chart .w0{stroke:#c2410c}.chart .w1{stroke:#0f766e}.chart .w2{stroke:#7c3aed}.chart .w3{stroke:#b45309}
"""
    html = f"<html><head><meta charset='utf-8'><style>{css} body{{background:#fff}}</style></head><body>"
    ids = sys.argv[1] if len(sys.argv) > 1 else "A"
    for M in [m for m in METHODS if m["id"] in ids]:
        html += f"<h3>{M['id']}</h3><div class='dw'>{key_part(M)}</div><div class='dw'>{key_part(M, 'C#', True)}</div>"
        html += f"<div class='dw' style='max-width:800px'>{DETAIL[M['id']](M)}</div>"
    html += f"<div class='dw'>{key_sections(METHODS[0])}</div><div class='dw'>{sensor_detail()}</div><div style='max-width:640px'>{field_chart()}</div>"
    open("test.html", "w").write(html + "</body></html>")
