"""Assembly side elevations (section through a white key) for methods A–D."""
import math
from draw import View, fmt_mm, ord_y, ord_z
from drawings_common import (hatch, hrect, hpoly, rotate_pts, side_common, lid, white_key_outline,
                             key_section, black_phantom, pressed_outline, magnet, spring_zig, std_pids)
from model import L, METHODS, rot, hammer_parts

BT = L["base_t"]


def frame_view(M, y_max, top):
    # left margin for key slip, right margin for z ordinates, bottom for y ordinates
    return View(-48, -BT - 62, y_max + 72, top, px_width=1180)


def balloons(v, items):
    for n, (u, w), (tu, tw) in items:
        v.balloon(u, w, tu, tw, n)


def common_ords(v, M, feats_y, feats_z, y_max):
    ord_y(v, feats_y, -BT - 6)
    ord_z(v, feats_z, y_max + 8)


def travel_marks(v, M):
    """dip: rest front top corner (0, z_top) -> pressed front top corner (exact rotation about the pivot),
    dimensioned left of the key slip; extension lines run above the slip (both z > slip_top)."""
    zt = M["z_top"]
    y_dn, z_dn = rot((0.0, zt), M["pivot"], M["theta"])
    u = -(2 + L["slip_gap"] + L["slip_t"]) - v.px(28)
    v.dim_v(zt, z_dn, u, text="", ext_from=(0.0, y_dn))
    v.text(u - v.px(5), (zt + z_dn) / 2, f"딥 {fmt_mm(zt - z_dn)}", cls="dt", anchor="end", size_px=10.5, dy_px=3.5)


def guide_slot(v, M):
    """white key's guide slot (L.slot_len long, M.slot_depth up from the key underside), cut after
    key_section, with the guide pin redrawn inside it up to its tip M.pin_top."""
    gy, zb = M["guide_w_y"], M["z_bot"]
    v.rect(gy - L["slot_len"] / 2, zb, L["slot_len"], M["slot_depth"], cls="void")
    v.rect(gy - L["pin_d"] / 2, zb, L["pin_d"], M["pin_top"] - zb, cls="m-steel")


def comb(v, M, P, z_top, cb=6.0):
    """printed comb: pins (y c0..c1) standing on a base plate cb thick that overhangs cb front and back."""
    c0, c1 = M["comb"]
    v.poly([(c0, cb), (c1, cb), (c1, z_top), (c0, z_top)], cls="m-print ph")
    hrect(v, c0 - cb, 0, c1 - c0 + 2 * cb, cb, P["print"], "m-print")
    return c0, c1, cb


def side_A(M):
    ymax = 262
    top = M["lid_bot"] + L["lid_t"] + 27
    v = frame_view(M, ymax, top)
    P = std_pids(v)
    side_common(v, M, ymax, P)
    lid(v, M, L["fall"], ymax, P)
    zb, zt = M["z_bot"], M["z_top"]
    black_phantom(v, M)
    key_section(v, M, P, [50, 80, 140, 170, 212],
                [(14, 22, zb, zt - 2), (105, 115, zb, zt - 2), (185, 195, zb, zt - 2)])
    guide_slot(v, M)
    v.rect(106.9, zb, 6.2, 3.2, cls="void")
    v.rect(186.8, zb, 6.4, M["pocket_depth"], cls="void")
    magnet(v, 110, zb)
    lt = M["leaf_t"]
    hrect(v, M["body_end"], zb, M["leaf"], lt, P["key"], "m-key")
    s0, s1 = M["spine"]
    hrect(v, s0, zb, s1 - s0, zt - zb, P["key"], "m-key")
    b0, b1 = M["blk"]
    hrect(v, b0, 0, b1 - b0, zb, P["print"], "m-print")
    # M3 spine bolt: shank L.spine_bolt long under the head (head on the spine top), centred on the spine
    bc, br = (s0 + s1) / 2, 1.7
    v.rect(bc - br, zt - L["spine_bolt"], 2 * br, L["spine_bolt"], cls="m-steel")
    v.rect(bc - 2 * br, zt, 4 * br, 2.2, cls="m-steel")
    ys, pt = M["spring_y"], M["post_top"]
    hrect(v, ys - 7, 0, 14, pt, P["print"], "m-print")
    v.rect(ys - 1.5, -10, 3, pt + 10 - 0.8, cls="m-steel ph")
    spring_zig(v, ys, pt, zb + M["pocket_depth"], 6.0, 9)
    pressed_outline(v, M, white_key_outline(M) )
    pv = M["pivot"]
    v.cl(pv[0], pv[1] - 12, pv[0], pv[1] + 28)
    v.circle(pv[0], pv[1], v.px(3), cls="pivot")
    travel_marks(v, M)
    common_ords(v, M,
                [(M["guide_w_y"], -L["pin_depth"], "가이드 핀(백)"), (L["head"], zt, "흑건 앞"),
                 (M["guide_b_y"], -L["pin_depth"], "가이드 핀(흑)"),
                 (L["y_sensor"], 0, "홀센서·자석"), (L["fall"], M["lid_bot"], "명판 앞면"), (M["upstop_y"][0], M["lid_bot"], "상한 펠트"),
                 (ys, 0, "스프링"), (M["body_end"], zb, "힌지 시작"), (pv[0], zb, "피벗"), (s0, zb, "스파인"), (s1, zb, "스파인 끝")],
                [(M["rail_w_top"], 6, "전면 레일(백)"), (M["rail_b_top"], 62, "전면 레일(흑)"), (M["sensor_top"], 126, "센서면"),
                 (pt, ys + 7, "스프링 받침"), (zb, s1, "건반 밑면"), (zt, s1, "백건 윗면"),
                 (M["z_black"], L["black_end"], "흑건 윗면"), (M["lid_bot"], ymax, "뚜껑 밑면")], ymax)
    tb = M["lid_bot"] + L["lid_t"] + 16
    lid_pt = ((L["fall"] + M["upstop_y"][0]) / 2, (M["z_black"] + M["lid_bot"] + L["lid_t"]) / 2)
    balloons(v, [(1, (60, zt - 1), (60, tb)), (2, (231, zb + 0.6), (214, tb)), (3, ((s0 + bc - br) / 2, (zb + zt) / 2), (238, tb)),
                 (4, (bc, 8), (258, tb)), (5, (30, 2.5), (-20, tb)), (6, (M["guide_w_y"], 8), (4, tb)), (7, (24, M["rail_w_top"] + 2), (22, tb)),
                 (8, (110, 7), (96, tb)), (9, (110, zb + 1.5), (124, tb)), (10, (ys, 13), (196, tb)),
                 (11, (170, M["lid_bot"] - 1.5), (170, tb)), (12, lid_pt, (146, tb)), (13, (-12, 6), (-40, tb)),
                 (14, (80, -9), (80, tb))])
    v.note(-46, -BT - 60, f"θmax {math.degrees(M['theta']):.2f}° · 피벗 (y {fmt_mm(pv[0])}, z {fmt_mm(pv[1],1)}) · "
           f"센서 위치 이동 {M['t110']:.2f} mm · 빨간 점선 = 끝까지 눌린 상태", size_px=10.5)
    return v.svg(aria="방식 A 조립 측면도")


def side_B(M):
    ymax = 262
    top = M["lid_bot"] + L["lid_t"] + 27
    v = frame_view(M, ymax, top)
    P = std_pids(v)
    side_common(v, M, ymax, P)
    lid(v, M, L["fall"], ymax, P)
    zb, zt = M["z_bot"], M["z_top"]
    black_phantom(v, M)
    ysb = M["spring_y"]
    key_section(v, M, P, [50, 80, 140, 172, 212],
                [(14, 22, zb, zt - 2), (105, 115, zb, zt - 2), (ysb - 5, ysb + 5, zb, zt - 2),
                 (M["eyelet_y"], M["body_end"], zb, zt - L["skin"])])      # solid narrowed rear eyelet
    guide_slot(v, M)
    v.rect(106.9, zb, 6.2, 3.2, cls="void")
    v.rect(ysb - 3.2, zb, 6.4, M["pocket_depth"], cls="void")
    magnet(v, 110, zb)
    pv = M["pivot"]
    c0, c1, cb = comb(v, M, P, pv[1] + 5)
    v.circle(pv[0], pv[1], M["hole_d"] / 2, cls="void")
    v.circle(pv[0], pv[1], M["shaft_d"] / 2, cls="m-steel")
    ys, pt = M["spring_y"], M["post_top"]
    hrect(v, ys - 7, 0, 14, pt, P["print"], "m-print")
    v.rect(ys - 1.5, -10, 3, pt + 10 - 0.8, cls="m-steel ph")
    spring_zig(v, ys, pt, zb + M["pocket_depth"], 6.0, 8)
    pressed_outline(v, M, white_key_outline(M))
    v.cl(pv[0], pv[1] - 14, pv[0], pv[1] + 20)
    v.cl(pv[0] - 12, pv[1], pv[0] + 14, pv[1])
    travel_marks(v, M)
    common_ords(v, M,
                [(M["guide_w_y"], -L["pin_depth"], "가이드 핀(백)"), (L["head"], zt, "흑건 앞"),
                 (M["guide_b_y"], -L["pin_depth"], "가이드 핀(흑)"),
                 (L["y_sensor"], 0, "홀센서·자석"), (L["fall"], M["lid_bot"], "명판 앞면"), (M["upstop_y"][0], M["lid_bot"], "상한 펠트"),
                 (ys, 0, "스프링"), (c0, cb, "힌지 콤"), (pv[0], pv[1], "샤프트 중심"), (M["body_end"], zb, "건반 끝")],
                [(M["rail_w_top"], 6, "전면 레일(백)"), (M["rail_b_top"], 62, "전면 레일(흑)"), (M["sensor_top"], 126, "센서면"),
                 (pt, ys + 7, "스프링 받침"), (zb, M["body_end"], "건반 밑면"), (pv[1], pv[0] + 2, "샤프트 중심"),
                 (zt, M["body_end"], "백건 윗면"), (M["z_black"], L["black_end"], "흑건 윗면"), (M["lid_bot"], ymax, "뚜껑 밑면")], ymax)
    tb = M["lid_bot"] + L["lid_t"] + 16
    balloons(v, [(1, (60, zt - 1), (60, tb)), (2, (pv[0], pv[1]), (228, tb)), (3, (c1 - 2, 4), (248, tb)),
                 (5, (30, 2.5), (-20, tb)), (6, (M["guide_w_y"], 8), (4, tb)), (7, (24, M["rail_w_top"] + 2), (22, tb)),
                 (8, (110, 7), (96, tb)), (9, (110, zb + 1.5), (124, tb)), (10, (ys, 10), (192, tb)),
                 (11, (170, M["lid_bot"] - 1.5), (172, tb)),
                 (12, ((L["fall"] + M["upstop_y"][0]) / 2, (M["z_black"] + M["lid_bot"] + L["lid_t"]) / 2), (146, tb)),
                 (13, (-12, 6), (-40, tb)),
                 (14, (80, -9), (80, tb))])
    v.note(-46, -BT - 60, f"θmax {math.degrees(M['theta']):.2f}° · 피벗 (y {fmt_mm(pv[0])}, z {fmt_mm(pv[1],1)}) · "
           f"센서 위치 이동 {M['t110']:.2f} mm · 빨간 점선 = 끝까지 눌린 상태", size_px=10.5)
    return v.svg(aria="방식 B 조립 측면도")


def side_C(M):
    ymax = 392
    top = M["lid_bot"] + L["lid_t"] + 27
    v = View(-48, -BT - 62, ymax + 72, top, px_width=1180)
    P = std_pids(v)
    side_common(v, M, ymax, P)
    # transport-guard lid at lid_bot up to lid_end, then the raised rear cover (underside rear_cover_z)
    # over the rising key rear end and counterweight (model: pressed key top >= 1 mm below both)
    le, rcz = M["lid_end"], M["rear_cover_z"]
    lid(v, M, L["fall"], le, P)
    hrect(v, le, rcz, ymax - le, L["lid_t"], P["wood"], "m-wood")
    zb, zt = M["z_bot"], M["z_top"]
    black_phantom(v, M)
    bb0, bb1 = M["bal_boss"]                 # wall-to-wall balance block (key underside .. top skin)
    key_section(v, M, P, [50, 80, 140, 180, 262, 296],
                [(14, 22, zb, zt - 2), (105, 115, zb, zt - 2), (bb0, bb1, zb, zt - L["skin"])])
    guide_slot(v, M)
    # balance hole (Ø bal_hole_d, key-local 0..mz0) and pin mortise (ml long, mz0..mz1) cut in the block
    py = M["pivot"][0]
    _mw, ml, mz0, mz1 = M["bal_mortise"]
    hd = M["bal_hole_d"]
    v.rect(py - hd / 2, zb, hd, mz0, cls="void")
    v.rect(py - ml / 2, zb + mz0, ml, mz1 - mz0, cls="void")
    v.rect(106.9, zb, 6.2, 3.2, cls="void")
    magnet(v, 110, zb)
    # lap joint: rear part starts at j0, front part ends at j1; the step is lap_h above the key underside
    j0, j1, lap_h = M["rear_part"][0], M["front_part"][1], 10.0
    v.poly([(j0, zb), (j0, zb + lap_h), (j1, zb + lap_h), (j1, zt - L["skin"])], cls="edge", closed=False)
    screws = ((j0 + j1) / 2 - (j1 - j0) / 4, (j0 + j1) / 2 + (j1 - j0) / 4)
    for yy in screws:
        v.rect(yy - 1.5, zb + 2, 3, zt - zb - 4, cls="m-steel ph")
    c0, c1 = M["cw_c"] - M["cw_len"] / 2, M["cw_c"] + M["cw_len"] / 2
    z0, z1 = M["cw_z"]
    hrect(v, c0, z0, c1 - c0, z1 - z0, P["steel"], "m-steel")
    hrect(v, py - 12, 0, 24, M["balrail_top"], P["print"], "m-print")
    pd = M["punch_d"]                        # balance-rail felt punching
    v.rect(py - pd / 2, M["balrail_top"], pd, zb - M["balrail_top"], cls="m-felt")
    bp = M["bal_pin"]
    v.rect(py - bp["d"] / 2, -bp["embed"], bp["d"], bp["len"], cls="m-steel")
    br0, br1 = M["cw_c"] - 10, M["cw_c"] + 10
    hrect(v, br0, 0, br1 - br0, M["backrail_top"], P["print"], "m-print")
    v.rect(br0, M["backrail_top"], br1 - br0, z0 - M["backrail_top"], cls="m-felt")
    pressed_outline(v, M, white_key_outline(M))
    pressed_outline(v, M, [(c0, z0), (c1, z0), (c1, z1), (c0, z1)])
    v.cl(py, -14, py, zt + 16)
    travel_marks(v, M)
    common_ords(v, M,
                [(M["guide_w_y"], -L["pin_depth"], "가이드 핀(백)"), (L["head"], zt, "흑건 앞"),
                 (M["guide_b_y"], -L["pin_depth"], "가이드 핀(흑)"),
                 (L["y_sensor"], 0, "홀센서·자석"), (L["fall"], M["lid_bot"], "명판 앞면"), (py, 0, "밸런스 핀"),
                 (j0, zb, "이음 시작"), (j1, zb + lap_h, "앞 부품 끝"), (le, M["lid_bot"], "높인 덮개"),
                 (c0, z0, "추 앞"), (M["cw_c"], 0, "추 중심·백레일"), (c1, z0, "추 끝"),
                 (M["body_end"], zb, "건반 끝")],
                [(M["rail_w_top"], 6, "전면 레일(백)"), (M["rail_b_top"], 62, "전면 레일(흑)"), (M["backrail_top"], br1, "백레일"),
                 (M["sensor_top"], 126, "센서면"), (z0, c1, "추 밑면"), (M["balrail_top"], py + 12, "밸런스 레일"),
                 (zb, M["body_end"], "건반 밑면"), (z1, c1, "추 윗면"), (zt, M["body_end"], "백건 윗면"),
                 (M["lid_bot"], le, "뚜껑 밑면"), (rcz, ymax, "덮개 밑면")], ymax)
    tb = M["lid_bot"] + L["lid_t"] + 16
    balloons(v, [(1, (60, zt - 1), (60, tb)), (2, (300, zt - 1), (300, tb)), (3, (screws[1], zb + 12), (250, tb)),
                 (4, (py, zb + 6), (212, tb)), (5, (py + (bp["d"] + pd) / 4, M["balrail_top"] + 1), (190, tb)),
                 (6, (M["cw_c"], z1 - 4), (340, tb)), (7, (br1 - 3, M["backrail_top"] + 1), (362, tb)),
                 (8, (30, 2.5), (-20, tb)), (9, (M["guide_w_y"], 8), (4, tb)), (10, (24, M["rail_w_top"] + 2), (22, tb)),
                 (11, (110, 7), (96, tb)), (12, (110, zb + 1.5), (124, tb)), (13, (le - 6, M["lid_bot"] + L["lid_t"] / 2), (276, tb)),
                 (14, (-12, 6), (-40, tb)), (15, (80, -9), (80, tb))])
    v.note(-46, -BT - 60, f"θmax {math.degrees(M['theta']):.2f}° · 밸런스 (y {fmt_mm(py)}) · 센서 위치 이동 {M['t110']:.2f} mm · "
           f"뒤끝 상승 {M['rear_rise']:.1f} mm · 복귀 = 중력(스프링 없음) · 흑건 윗면 z {fmt_mm(M['z_black'])}", size_px=10.5)
    return v.svg(aria="방식 C 조립 측면도")


def side_D(M):
    ymax = 262
    top = M["lid_bot"] + L["lid_t"] + 27
    v = frame_view(M, ymax, top)
    P = std_pids(v)
    side_common(v, M, ymax, P)
    lid(v, M, L["fall"], ymax, P)
    zb, zt = M["z_bot"], M["z_top"]
    black_phantom(v, M)
    # ribs: plain y -> key_section takes the lower edge from model.rib_z0 (y 112 is shortened over the rising hammer)
    ab0, ab1 = M["act_boss"]                 # wall-to-wall boss above the actuator pad
    key_section(v, M, P, [50, 80, 112, 205],
                [(14, 22, zb, zt - 2), (ab0, ab1, zb, zt - L["skin"]),
                 (M["eyelet_y"], M["body_end"], zb, zt - L["skin"])])      # solid narrowed rear eyelet
    guide_slot(v, M)
    hp = M["h_push"]
    ha_ = M["h_act"]                         # actuator pad (act_len long at the key, 6 at the tip) down to the felt
    v.poly([(ab0, zb), (ab1, zb), (hp + 3, zb - ha_), (hp - 3, zb - ha_)], cls="m-key")
    pv = M["pivot"]
    c0, c1, cb = comb(v, M, P, pv[1] + 5)
    v.circle(pv[0], pv[1], 2.15, cls="void")
    v.circle(pv[0], pv[1], 2.0, cls="m-steel")
    hpv = M["h_pivot"]
    hu, ht = M["h_under"], M["h_top"]
    w0, w1 = M["h_weight"]
    wz0, wz1 = M["h_w_z"]
    HP = hammer_parts(M)
    beam, cradle, bar = HP["beam"], HP["cradle"], HP["bar"]
    c0h, c1h = M["h_cradle"]
    cz0, cz1 = M["h_cradle_z"]
    hpoly(v, beam, P["print"], "m-print2")
    hpoly(v, cradle, P["print"], "m-print2")
    hpoly(v, bar, P["steel"], "m-steel")
    for (sy, sz, sw, sh) in HP["screws"]:
        v.rect(sy, sz, sw, sh, cls="m-steel ph")
    for p in HP["csk"]:                      # M3 countersunk heads, flush with the cradle floor
        v.poly(p, cls="m-steel")
    v.rect(hp - 4, ht, 8, 2.0, cls="m-felt")
    v.rect(106.9, hu, 6.2, 3.2, cls="void")
    magnet(v, 110, hu)
    h0, h1 = M["h_comb"]
    v.poly([(h0, 0), (h1, 0), (h1, hpv[1] + 5), (h0, hpv[1] + 5)], cls="m-print ph")
    v.circle(hpv[0], hpv[1], M["h_hole_d"] / 2, cls="void")
    v.circle(hpv[0], hpv[1], M["h_shaft_d"] / 2, cls="m-steel")
    v.rect(66, 0.0, 10, L["felt"], cls="m-felt")
    # rest felt under the cradle floor (1 mm below it at rest); printed pad only if the felt alone is too low
    r0, r1 = M["h_rest"]
    pad = M["h_rest_pad"]
    if pad > 0:
        hrect(v, r0, 0, r1 - r0, pad, P["print"], "m-print")
    v.rect(r0, pad, r1 - r0, L["felt"], cls="m-felt")
    wr0 = pad
    pressed_outline(v, M, white_key_outline(M))
    ha = M["h_theta"]
    v.poly(rotate_pts(beam, hpv, ha), cls="pressed")
    v.poly(rotate_pts(cradle, hpv, ha), cls="pressed")
    v.cl(pv[0], pv[1] - 14, pv[0], pv[1] + 18)
    v.cl(hpv[0], -6, hpv[0], hpv[1] + 16)
    travel_marks(v, M)
    common_ords(v, M,
                [(M["guide_w_y"], -L["pin_depth"], "가이드 핀(백)"), (M["guide_b_y"], -L["pin_depth"], "가이드 핀(흑)"),
                 (beam[0][0], beam[0][1], "해머 앞끝"),
                 (hp, zb, "누름점"), (hpv[0], 0, "해머 축"), (L["y_sensor"], 0, "홀센서·자석"), (c0h, cz0, "받침 앞"),
                 (L["fall"], M["lid_bot"], "명판 앞면"), (c1h, cz0, "해머 뒤끝"), (M["upstop_y"][0], M["lid_bot"], "상한 펠트"),
                 (c0, cb, "건반 콤"), (pv[0], pv[1], "건반 축"), (M["body_end"], zb, "건반 끝")],
                [(L["felt"], 76, "과회전 스톱"), (M["h_rest_top"], r1, "추 받침 펠트"), (M["sensor_top"], 126, "센서면"),
                 (cz0, c1h, "받침 바닥"), (wz0, w1, "추 밑면"), (hu, beam[2][0], "해머 밑면"), (hpv[1], h1, "해머 축"), (M["rail_w_top"], 6, "전면 레일(백)"),
                 (M["rail_b_top"], 58, "전면 레일(흑)"), (ht, beam[3][0], "해머 윗면"), (zb, M["body_end"], "건반 밑면"), (wz1, w1, "추 윗면"),
                 (pv[1], pv[0] + 2, "건반 축"), (zt, M["body_end"], "백건 윗면"), (M["z_black"], L["black_end"], "흑건 윗면"),
                 (M["lid_bot"], ymax, "뚜껑 밑면")], ymax)
    tb = M["lid_bot"] + L["lid_t"] + 16
    balloons(v, [(1, (40, zt - 1), (40, tb)), (2, (hp, zb - 1), (66, tb)), (3, (pv[0], pv[1]), (232, tb)),
                 (4, (82, ht - 2), (86, tb)), (5, (hpv[0], hpv[1]), (106, tb)), (6, ((w0 + w1) / 2, wz1 - 3), (160, tb)),
                 (7, (hp, ht + 1), (-2, tb)), (8, (71, 1.5), (-20, tb)), (9, ((r0 + r1) / 2, wr0 + 1.5), (180, tb)),
                 (10, (110, 7), (140, tb)), (11, (110, hu + 1.5), (126, tb)), (12, (M["guide_w_y"], 8), (16, tb)),
                 (13, (205, M["lid_bot"] - 1.5), (205, tb)), (14, (-12, 6), (-40, tb)), (15, (30, 7), (30, tb + 0.01))][:14])
    v.note(-46, -BT - 60, f"건반 θmax {math.degrees(M['theta']):.2f}° · 해머 θ {math.degrees(M['h_theta']):.1f}° · "
           f"각속도비 {M['ratio']:.2f} · 해머 자석 이동 {M['t110']:.2f} mm(눌리면 멀어짐) · 추 상승 {M['w_rise']:.1f} mm, 건반 안 여유 {M['w_clear']:.1f} mm (흑건 {M['w_rise_b']:.1f} / {M['w_clear_b']:.1f} mm)",
           size_px=10.5)
    return v.svg(aria="방식 D 조립 측면도")


SIDE = dict(A=side_A, B=side_B, C=side_C, D=side_D)

if __name__ == "__main__":
    css = open("dwg.css").read()
    html = f"<html><head><meta charset='utf-8'><style>{css} body{{background:#fff;font-family:sans-serif}}</style></head><body>"
    import sys
    ids = sys.argv[1] if len(sys.argv) > 1 else "ABCD"
    for M in [m for m in METHODS if m["id"] in ids]:
        html += f"<h3>{M['id']}</h3><div class='dw'>{SIDE[M['id']](M)}</div>"
    open("test.html", "w").write(html + "</body></html>")
