"""Toccata R31 touchscreen rev 3a (B1 = Waveshare 7-DSI-TOUCH-C on the L2 low rear bar) -- dimensioned drawing sheets t01..t06.
Drawing fix round 1 (2026-10-01): 3a ear outline, u24 rib + axle check, notch detail H, t03 back-view +x/-x, clip groove,
ribbon on the HDMI (no U-bend), one sound-path value, frames/titles from the placement block, O4 service, text-overlap audit.

run : ../../../venv/bin/python render_t.py [t01 ...]      (no argument = all sheets)
out : ../tNN_*.svg + ../tNN_*.png (1800 px) + ../drawings.json
Data: tgeo.py (numbers.json of the rev-3 design + final L2 files + circuit netlist copies).  House style = key-action v4
drawings (kav4 kit: View panels, ordinates, hatches, balloons, revision stamp).  Coordinates typed in this file are only
label / panel placement positions; every drawn geometry and every number written comes from tgeo.
"""
import csv
import json
import math
import os
import sys

import tkit as K
import tgeo as g
from tkit import View, F, FX, FR, T, lead, ordz, ordy, panel_title, note_lines, scalebar, halo1, dim_al, angle_arc

OUT = os.path.normpath(os.path.join(K.HERE, ".."))
SHEETS = []
sys.path.insert(0, K.KAV4)
import render_v4 as R  # noqa: E402  (key-action module section for the context)


def add_sheet(n, base, title_ko, caption_ko):
    SHEETS.append(dict(id=f"t{n:02d}", title_ko=title_ko, caption_ko=caption_ko, svg_file=base + ".svg", png_file=base + ".png"))


def sub_head(n, title):
    return f"도면 T{n}. {title}"


SRC_LINE = ("좌표 mm: x = A0 왼쪽 경계, y = 흰건반 앞끝에서 뒤로, z = 책상에서 위로 · 받침 좌표 xr = x − {xc}, u = 유리 아래 끝에서 위로, "
            "w = 유리 앞면에서 뒤로 · 숫자 = numbers.json(수정 {rev}판, 확정 L2)").format(xc=F(g.XC), rev=g.REV)


def foot_lines():
    src = " · ".join(f"{k} md5 {v[:8]}" for k, v in g.SOURCES.items())
    return [f"일반 공차 {g.TOL['general']} (FDM PETG, P2S) · 표시 없는 모서리 C0.5 · 출처: {src}"]


# ------------------------------------------------------------------ shared drawing pieces
def draw_cradle_section(v, P_, th, xr0, pid, cls="m-cr"):
    """cradle cut by xr = xr0, posed at th (world y, z)."""
    adds, subs = g.cradle_section(xr0)
    K.rings_h(v, [g.tf(p, th) for p in adds], cls, pid, subs=[g.tf(p, th) for p in subs])


def draw_screen(v, th, xr0, act=True):
    for p in g.screen_section(xr0):
        v.poly(g.tf(p, th), cls="m-scr")
    a, b = g.P(0, 0, th), g.P(g.GH, 0, th)
    v.line(a[0], a[1], b[0], b[1], cls="glass")
    if act:
        a, b = g.P(g.ACT_U[0], 0, th), g.P(g.ACT_U[1], 0, th)
        v.line(a[0], a[1], b[0], b[1], cls="act")


def cradle_outline(th):
    """side silhouette of the whole cradle (walls + ears + lugs + clips), world, for phantom poses."""
    polys = [g.wall_poly(g.U1), g.EAR_PROFILE, g.LUG_PROFILE,
             g.rect(g.CLIPD["u"][0], g.CLIPD["u"][1], g.RIB0, g.CLIPD["back_w"])]
    return K.union_rings([g.tf(p, th) for p in polys], res=0.05)


def draw_leg_use(v, pid, cls="m-leg"):
    piv, tip = g.LG["pivot_yz"], g.LG["tip_yz"]
    K.rings_h(v, [g.leg_outline(piv, tip)], cls, pid, subs=[g.circle(piv, g.LEG_HOLE / 2, 32)])
    v.circle(piv[0], piv[1], 1.5, cls="m-steel")


def lid_section_at(x0):
    """(add, sub) (y, z) polygons of the lid (+ rev-3 additions) cut by the plane x = x0."""
    L = g.LID
    adds = [g.rect(L["y"][0], L["y"][1], L["top_z"] - L["plate_t"], L["top_z"])]
    subs = []
    pk = g.PK
    if pk["x"][0] <= x0 <= pk["x"][1]:
        c_ = g.LG["pocket_edge_C"]                    # back-wall top edge C0.5
        subs.append([(pk["ramp_front_y"], L["top_z"] + 0.05), (pk["ramp_front_y"], L["top_z"]), (pk["ramp_end_y"], pk["bottom_z"]),
                     (pk["back_wall_y"], pk["bottom_z"]), (pk["back_wall_y"], L["top_z"] - c_), (pk["back_wall_y"] + c_, L["top_z"]),
                     (pk["back_wall_y"] + c_, L["top_z"] + 0.05)])
    b = pk["block"]
    if b["x"][0] <= x0 <= b["x"][1]:
        adds.append(g.rect(b["y"][0], b["y"][1], b["z"][0], L["top_z"] - L["plate_t"] + 0.01))
    for kn in (g.KNL, g.KNR):
        if kn["all"][0] <= x0 <= kn["all"][1]:
            adds.append(g.rect(g.KN_FILL["y"][0], g.KN_FILL["y"][1], g.KN_FILL["z"][0], g.KN_FILL["z"][1] + 0.01))
            if kn["near"][0] <= x0 <= kn["near"][1] or kn["far"][0] <= x0 <= kn["far"][1]:
                adds.append(g.knuckle_profile())
                d = g.KN_NEAR_HOLE if kn["near"][0] <= x0 <= kn["near"][1] else g.KN_FAR_HOLE
                subs.append(g.circle(g.H, d / 2, 40))
            else:
                adds.append(g.rect(g.HEEL_STOP["y"][0], g.HEEL_STOP["y"][1], g.HEEL_STOP["z"][0] - 0.01, g.HEEL_STOP["z"][1]))
    hw = g.HOLE_WALL
    if hw[0] <= x0 <= hw[1]:
        adds.append(g.rect(hw[2], hw[3], L["bed_z"], L["top_z"]))
        if g.HO["x"][0] <= x0 <= g.HO["x"][1]:
            subs.append(g.rect(g.HO["y"][0], g.HO["y"][1], L["bed_z"] - 0.05, L["top_z"] + 0.05))
    cp = g.CL["pad"]
    if cp["x"][0] <= x0 <= cp["x"][1]:
        adds.append(g.rect(cp["y"][0], cp["y"][1], cp["z"][0], cp["z"][1] + 0.01))
    for f in g.FEET:
        if f["x"][0] <= x0 <= f["x"][1]:
            adds.append(g.rect(f["y"][0], f["y"][1], f["z"][0] - 0.01, f["z"][1]))
            if f["rear"]:
                adds.append(g.rect(f["lip"]["y"][0], f["lip"]["y"][1], f["z"][0] - 0.01, f["lip"]["z"][1]))
    for s in g.V["slots"]:
        if s[0] <= x0 <= s[1]:
            subs.append(g.rect(s[2], s[3], L["top_z"] - L["plate_t"] - 0.05, L["top_z"] + 0.05))
    return adds, subs


def draw_rear_bar(v, pid):
    """L2 centre unit section at x = XC (walls from body_L2.json), plywood."""
    W = g.WALLS
    fz = g.FLOOR_ZONE
    K.poly_h(v, g.rect(fz["y"][0], W["back_y"][0], W["bottom_z"][0], W["bottom_z"][1]), "m-wood", pid["wood"])
    K.poly_h(v, g.rect(W["back_y"][0], W["back_y"][1], W["bottom_z"][0], W["lid_z"][0]), "m-wood", pid["wood"])


def draw_pi(v):
    """Pi 5 at x = XC plane (board cut) + parts behind (x < XC) as thin outlines."""
    pi = g.PI
    top = pi["board_top_z"]
    v.rect(pi["board_y"][0], top - 1.6, pi["board_y"][1] - pi["board_y"][0], 1.6, cls="m-pi")
    for key, cls in (("heatsink", "vis"), ("hdmi", "vis")):
        q = pi[key]
        v.rect(q["y"][0], top, q["y"][1] - q["y"][0], q["top_z"] - top, cls=cls)
    d1 = pi["disp1"]
    v.rect(d1["y"][0], top, d1["y"][1] - d1["y"][0], pi["cad_disp1"]["z"][1] - top, cls="m-lead")
    gp = pi["gpio_pin2"]
    pp = g.PIN_PITCH
    v.rect(gp[1] - 1.5 * pp, top, 2 * pp, pi["gpio_top_z"] - top, cls="m-black")


def ribbon_side(th):
    """ribbon centre line in side projection (world y, z): FPC -> gap -> groove exit -> hinge loop -> hole -> under the lid."""
    gap_w = (g.CR["w_screen_back"] + g.PL_IN) / 2
    pts = [g.P(g.S["fpc"]["pin_u_centre"], gap_w, th), g.P(g.U0, gap_w, th)]
    ex = pts[-1]
    hole_c = ((g.HO["y"][0] + g.HO["y"][1]) / 2, g.LID["top_z"])
    loop = hinge_loop(ex, hole_c, g.RB["loop"]["single_arc_R"]["use" if th == g.TH_USE else ("heel" if th == g.TH_HEEL else "fold")])
    wp = g.RB["waypoints"]
    return pts + loop[1:] + [(p[1], p[2]) for p in wp[1:]]


def power_side(rib):
    """power wire side projection: along the ribbon (offset 1.2) down to the lid-hole top, then its own waypoints."""
    n_c = len(rib) - (len(g.RB["waypoints"]) - 1)
    return [(p[0] + 1.2, p[1]) for p in rib[:n_c]] + [(q[1], q[2]) for q in g.PW["waypoints"]]


def frame_check(name, view_box, subject):
    """a zoom / panel window must contain its subject (world boxes (u0, u1, v0, v1))."""
    ok = view_box[0] <= subject[0] and subject[1] <= view_box[1] and view_box[2] <= subject[2] and subject[3] <= view_box[3]
    g.check(f"frame {name} contains its subject", ok, f"view {[round(q, 2) for q in view_box]} subject {[round(q, 2) for q in subject]}")


def hinge_loop(a, b, R, n=24):
    """arc from a to b of radius R, bulging toward -y (the player side, as the design's loop estimate)."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    c = math.hypot(dx, dy)
    R = max(R, c / 2 + 1e-6)
    d = math.sqrt(R * R - (c / 2) ** 2)
    nx, ny = -dy / c, dx / c
    if nx > 0:                     # normal pointing to +y: centre on the +y side, arc bulges to -y
        cx, cy = mx + nx * d, my + ny * d
    else:
        cx, cy = mx - nx * d, my - ny * d
    a0 = math.atan2(a[1] - cy, a[0] - cx)
    a1 = math.atan2(b[1] - cy, b[0] - cx)
    # go the long way round through the -y side
    mid = math.atan2(0, -1)
    cands = []
    for k in (-1, 1):
        a1k = a1 + k * 2 * math.pi if (a1 - a0) * k < 0 else a1
        cands.append(a1k)
    best = None
    for a1k in cands:
        pts = [(cx + R * math.cos(a0 + (a1k - a0) * i / n), cy + R * math.sin(a0 + (a1k - a0) * i / n)) for i in range(n + 1)]
        ymin = min(p[0] for p in pts)
        if best is None or ymin < best[0]:
            best = (ymin, pts)
    return best[1]


# ================================================================ t01 assembly side section
def sheet_t01():
    n = 1
    L, KO, HG, LG, FO = g.LID, g.KO, g.HG, g.LG, g.FO
    th = g.TH_USE
    # frame from the placement block: 62 mm of key module in front of the rear bar, labels column right of the lid rear
    y_break = KO["module_rear_y"] - 62.0
    Y0, Y1 = y_break - 32.0, L["y"][1] + 60.5
    Z0, Z1 = -44.0, max(g.PTS["use"]["cr_top_front"][1], g.PTS["heel"]["cr_top_front"][1]) + 23.1
    v = View(Y0, Z0, Y1, Z1, px_width=1480, pad_px=6)
    frame_check("t01 side", (Y0, Y1, Z0, Z1), (KO["module_rear_y"], L["y"][1], 0.0, g.PTS["heel"]["cr_top_front"][1]))
    Pk = R.pids(v)
    pid = K.pid_set(v)
    # ---- desk
    v.line(Y0 + 4, 0.0, L["y"][1] + 8, 0.0, cls="vis")
    # ---- module context (key-action model, key D section), faded, cut at y_break
    i0 = len(v.el)
    xsec = R.pcirc("key D balance pin")[0]
    R.side_scene(v, Pk, "key D", "lever D", xsec, False, press=False, beyond=False, marks=False, sensor=True)
    cid = K.kit.uid("c")
    v.defs.append(f'<clipPath id="{cid}"><rect x="{y_break:.4f}" y="{-Z1:.4f}" width="{KO["module_rear_y"] + 1 - y_break:.4f}" height="{Z1 - Z0:.4f}"/></clipPath>')
    v.el.insert(i0, f'<g clip-path="url(#{cid})" opacity="0.5">')
    v.el.append("</g>")
    v._late = [((i + 1) if i >= i0 else i, fn) for i, fn in v._late]
    zb = K.kit.bbox(R.pts(R.fpart("top plate (ledge + bridge)")))
    v.poly([(y_break, 3.0), (y_break + 2.5, 20.0), (y_break - 2.5, 40.0), (y_break, g.KO["z_min"])], cls="vis", closed=False)
    # ---- keep-out zone above the modules
    ko = g.rect(y_break, KO["y_max"], KO["z_min"], Z1 - 6)
    v.el.append(f'<polygon points="{" ".join(v.P(a, b) for a, b in ko)}" fill="url(#{pid["ko"]})" class="nostroke"/>')
    v.poly(ko, cls="ko")
    v.line(KO["y_max"], KO["z_min"], KO["y_max"], Z1 - 6, cls="ko-line")
    T(v, y_break + 3, Z1 - 16, "모듈 위 금지 (모듈을 위로 뺌)", cls="kot", size_px=11, halo=True)
    T(v, y_break + 3, Z1 - 20.5, f"y ≤ {F(KO['y_max'])} 이면서 z ≥ {F(KO['z_min'])}: 화면 부품·선 없음", cls="kot", size_px=10, halo=True)
    # ---- speaker pod outline (ends only, hidden behind the centre end wall) + 27 deg sound path line
    v.poly([tuple(p) for p in g.SPK["outer_yz_polygon"]], cls="phan")
    cl = g.CONE_LOW
    ys = y_break
    v.line(cl[0], cl[1], ys, g.sound_line_z(ys), cls="snd")
    v.circle(cl[0], cl[1], v.px(2.2), cls="dot")
    dr = g.DRV["centre_yz"]
    v.circle(dr[0], dr[1], v.px(2.2), cls="dot")
    # ---- rear bar (L2 centre unit) + lid
    draw_rear_bar(v, pid)
    fz = g.FRONT_ZONE
    v.poly(g.rect(g.KO["rear_bar_front_y"], g.DUCT["y"][1], g.DUCT["z"][0], g.DUCT["z"][1]), cls="zone")    # cable duct (body_L2 cable_duct)
    for fx_, fy_ in g.FEET_RB["positions_xy"]["centre"]:
        if abs(fx_ - g.XC) < 1e-6:
            r_ = g.FOOT_D / 2
            v.poly(g.rect(fy_ - r_, fy_ + r_, 0.0, g.FEET_RB["h"]), cls="m-print2")
    adds, subs = lid_section_at(g.XC)
    K.rings_h(v, adds, "m-lid", pid["lid"], subs=subs)
    # lid parts behind the plane (x < XC): left knuckle + heel stop, left fold feet (+lip)
    kp = g.knuckle_profile()
    v.poly(kp, cls="vis")
    v.poly(g.rect(g.HEEL_STOP["y"][0], g.HEEL_STOP["y"][1], g.HEEL_STOP["z"][0], g.HEEL_STOP["z"][1]), cls="vis")
    v.poly(g.rect(g.KN_FILL["y"][0], g.KN_FILL["y"][1], g.KN_FILL["z"][0], g.KN_FILL["z"][1]), cls="hid")
    for f in g.FEET:
        if f["x"][1] < g.XC:
            v.poly(g.rect(f["y"][0], f["y"][1], f["z"][0], f["z"][1]), cls="m-lid")
            if f["rear"]:
                v.poly(g.rect(f["lip"]["y"][0], f["lip"]["y"][1], f["z"][1], f["lip"]["z"][1]), cls="m-lid")
    draw_pi(v)
    # ---- folded pose (90): outline + stowed leg
    for r_ in cradle_outline(g.TH_FOLD):
        v.poly(r_, cls="fold-ph")
    a, b = g.P(0, 0, g.TH_FOLD), g.P(g.GH, 0, g.TH_FOLD)
    v.line(a[0], a[1], b[0], b[1], cls="fold-ph")
    lz = LG["fold_leg_z"]
    v.poly(g.rect(LG["fold_leg_y"][0], LG["fold_leg_y"][1], lz[0], lz[1]), cls="leg-ph")
    # ---- heel pose (22): outline dashed
    for r_ in cradle_outline(g.TH_HEEL):
        v.poly(r_, cls="cr-ph")
    # ---- use pose (25): section at xr = 0 + parts beyond + screen + leg
    beh = K.union_rings([g.tf(p, th) for p in g.cradle_behind(0.0)], res=0.04)
    K.stroke_rings(v, beh, "vis")
    draw_cradle_section(v, None, th, 0.0, pid["cr"])
    draw_screen(v, th, 0.0)
    draw_leg_use(v, pid["leg"])
    v.circle(g.H[0], g.H[1], 1.5, cls="m-steel")
    K.kit.pivot_mark(v, g.H, 1.5, cross=2.0)
    # ---- ribbon + power wire (x635~657, in front of the plane: overlaid)
    rib = ribbon_side(th)
    v.poly(rib, cls="rib", closed=False)
    v.poly(power_side(rib), cls="pw", closed=False)
    # ---- eye sight line (estimate)
    ac = g.PTS["use"]["act_centre"]
    e = g.EYE["eye"]
    k_ = (Z1 - 8 - ac[1]) / (e[1] - ac[1])
    ye = ac[0] + (e[0] - ac[0]) * k_
    v.line(ye, Z1 - 8, ac[0], ac[1], cls="eye")
    v._arrow(ac[0], ac[1], math.atan2(ac[1] - (Z1 - 8), ac[0] - ye))
    ab = g.PTS["use"]["act_bottom"]
    k2 = (KO["module_rear_y"] - ab[0]) / (e[0] - ab[0])
    v.line(ab[0], ab[1], KO["module_rear_y"] - 40, ab[1] + (e[1] - ab[1]) * (KO["module_rear_y"] - 40 - ab[0]) / (e[0] - ab[0]), cls="eye")
    zs = g.EYE["sightline_z_at_module"]
    v.circle(KO["module_rear_y"], zs, v.px(2.4), cls="dot")
    zc_ = g.EYE["sightline_centre_z_at_module"]
    v.circle(KO["module_rear_y"], zc_, v.px(2.4), cls="dot")
    # ---- 25 deg / 22 deg angle marks at the glass bottom
    gb = g.PTS["use"]["glass_bottom"]
    v.line(gb[0], gb[1], gb[0], gb[1] + 44, cls="cl")
    angle_arc(v, gb, 38.0, 90.0 - g.TH_USE, 90.0, f"{F(g.TH_USE)}°", size_px=11)
    # ---- ordinates: z (right column), y (bottom row)
    col = L["y"][1] + 10.0
    zf = [(0.0, L["y"][1], "책상"), (g.FEET_RB["h"], L["y"][1], "뒷바 밑 (고무발)"), (g.WALLS["bottom_z"][1], L["y"][1], "바닥판 위"),
          (g.PI["board_top_z"], g.PI["board_y"][1], "Pi 5 판 위"), (L["bed_z"], L["y"][1], "뚜껑 리브 밑 = 출력 바닥"),
          (L["top_z"], L["y"][1], "뚜껑 윗면 = 모듈 맨 위"), (FO["rib_plane_z"], g.FEET[1]["y"][1], "접이 받침 발 위"),
          (FO["top_z"], FO["y"][1], "접은 화면 위"), (g.PL["speaker_top_z"], g.SPK["outer_yz_polygon"][4][0], "스피커 윗면")]
    ordz(v, zf, col, gap_px=13, label_px=9.5)
    zf2 = [(g.PTS["use"]["cr_top_front"][1], g.PTS["use"]["cr_top_front"][0], f"받침 윗끝 ({F(g.TH_USE)}°)"),
           (g.PTS["heel"]["cr_top_front"][1], g.PTS["heel"]["cr_top_front"][0], f"받침 윗끝 ({F(g.TH_HEEL)}°)"),
           (ac[1], ac[0], "보이는 영역 가운데")]
    ordz(v, zf2, L["y"][1] - 41.5, gap_px=13, label_px=9.5, lo=FO["top_z"] + 4.65)
    row = -8.0
    yf = [(KO["module_rear_y"], KO["z_min"], "모듈 뒤끝"), (g.KO["rear_bar_front_y"], 5.0, "뒷바 앞"), (KO["y_max"], KO["z_min"], "금지선"),
          (g.N["all_min_y"], g.PTS["heel"]["cr_bot_front"][1], "가장 앞 (22°)"), (g.H[0], g.H[1] - 1.5, "경첩 축"),
          (FO["y"][0], FO["top_z"], "접음 앞"), (ac[0], ac[1], "보이는 가운데"), (LG["pivot_yz"][0], LG["pivot_yz"][1], "다리 축"),
          (g.PK["ramp_front_y"], L["top_z"], "주머니 경사"), (LG["tip_yz"][0], LG["tip_yz"][1], "다리 발끝"),
          (g.PK["back_wall_y"], L["top_z"], "주머니 뒷벽"), (FO["y"][1], FO["rib_plane_z"], "접음 뒤끝"), (L["y"][1], 5.0, "뒷면")]
    ordy(v, yf, row, gap_px=12.5, label_px=9.2, prefix="y")
    # ---- dimensions
    dim_al(v, tuple(LG["pivot_yz"]), tuple(LG["tip_yz"]), 32, f"받침다리 {F(LG['length'])} (축–발끝) · {F(LG['angle_deg'])}°", size_px=9.5)
    yd = (FO["y"][1] + L["y"][1]) / 2 + 3.0                       # fold -> speaker top: between the fold rear and the label column
    v.dim_v(FO["top_z"], g.PL["speaker_top_z"], yd, text=f"{F(FO['speaker_margin'])}", ext_from=(FO["y"][1], g.SPK["outer_yz_polygon"][3][0]), size_px=9.5)
    # ---- labels (left column inside the keep-out hatch, white halo); rows relative to the lid top / the frame top
    LX = y_break + 4.0
    zt, yr = L["top_z"], L["y"][1] + 8.5                               # right-hand labels end at yr (anchor end)
    lead(v, y_break + 20.0, zb[3] - 20, Y0 + 10.0, zt - 12.85, "건반 모듈 (백건 D 단면, 참고 — 건반 도면 1·11)", size_px=9.5)
    ys_ = y_break + 26.0
    lead(v, ys_, g.sound_line_z(ys_), LX, Z1 - 42.0, f"소리 길: 콘(Ø{F(g.CONE_D)}) 아래 끝에서 {F(g.SP_DEG)}° 선 → y{F(KO['module_rear_y'])}에서 z{F(KO['z_min'])} 위 {F(g.SP_CLEAR)} (≥ {F(g.SP_MIN)})", size_px=9.5, cls="sndt")
    T(v, LX + v.px(10), Z1 - 42.0 - v.px(14), f"스피커는 양 끝(x{F(g.SPK_X['L'][0])}~{F(g.SPK_X['L'][1])} · {F(g.SPK_X['R'][0])}~{F(g.SPK_X['R'][1])})에만 → 화면(x{F(g.CR['x'][0])}~{F(g.CR['x'][1])})과 x로 {F(g.SR['screen_to_cone_x_gap'])} 떨어짐", cls="sndt", size_px=9, halo=True)
    lead(v, g.SPK["outer_yz_polygon"][3][0] - 12, g.PL["speaker_top_z"], yr + 2.0, Z1 - 16.0, "스피커 상자 윤곽 (양 끝, 가운데 끝벽 뒤 — 가림)", size_px=9.5, anchor="end")
    el_ = math.hypot(ac[0] - ye, ac[1] - (Z1 - 8))
    fe = (ye + 22 * (ac[0] - ye) / el_, Z1 - 8 + 22 * (ac[1] - (Z1 - 8)) / el_)
    lead(v, fe[0], fe[1], LX, Z1 - 28.0, f"연주자 눈(추정 y{F(e[0])} z{F(e[1])}) → 보이는 가운데: 아래로 {F(g.EYE['angle_to_centre'])}° (기울기와 {F(g.EYE['tilt_diff'])}° 차이), y{F(KO['module_rear_y'])}에서 z{F(zc_)}", size_px=9.5, cls="eyet")
    lead(v, ac[0], ac[1], LX, Z1 - 62.0, f"보이는 영역 z{F(g.PTS['use']['act_bottom'][1])}~{F(g.PTS['use']['act_top'][1])} ({F(g.S['active'][0])}×{F(g.S['active'][1])}) · 가운데 z{F(ac[1])}, 흑건 뒤끝에서 {F(g.N['reach']['from_black_key_rear'])} 뒤", size_px=9.5)
    lead(v, KO["module_rear_y"], zs, LX, Z1 - 76.0, f"보이는 영역 아래 끝을 보는 선: y{F(KO['module_rear_y'])}에서 z{F(zs)} (모듈 위 {F(zs - KO['z_min'])}, 가리는 것 없음)", size_px=9.5, cls="eyet")
    hc = g.PTS["heel"]["cr_bot_front"]
    lead(v, hc[0], hc[1], LX, Z1 - 90.0, f"22° (뒤꿈치 닿음, 파랑 점선): 가장 앞 y{F(g.N['all_min_y'])} → 금지선과 {F(g.CK['keepout_margin'])}", size_px=9.5, cls="kot")
    lead(v, g.HEEL_STOP["y"][0] + 1.0, g.HEEL_STOP["z"][1], LX, Z1 - 104.0, f"뒤꿈치 멈춤 블록 z{F(HG['heel_stop_z'])} (귀 홈 바닥 +{F(HG['heel_stop_h'])}) — 확대 A", size_px=9.5)
    lead(v, g.H[0], g.H[1], LX, Z1 - 118.0, f"경첩 축 y{F(g.H[0])} z{F(g.H[1])} {g.TOL['axis_pos']} (M3×20, 볼 x{FR(g.KNL['all'][0], g.KNL['all'][1], 1)} · x{FR(g.KNR['all'][0], g.KNR['all'][1], 1)})", size_px=9.5)
    pc = g.P(60, g.CR["w"][1], th)
    lead(v, pc[0], pc[1], yr - 45.0, Z1 - 52.0, f"받침 {F(g.CR['size'][0])}×{F(g.CR['size'][1])}×{F(g.CR['size'][2])} (단면 xr0 = 다리 길, 가는 선 = −x 쪽 옆벽·귀·패드)", size_px=9.5)
    sc = g.P(70, g.GB / 2, th)
    lead(v, sc[0], sc[1], yr - 45.0, Z1 - 62.0, f"화면 {F(g.S['glass'][0])}×{F(g.S['glass'][1])}×{F(g.S['body'])} (파랑 굵은 선 = 보이는 영역)", size_px=9.5)
    lead(v, g.PK["back_wall_y"] - 2, g.PK["bottom_z"], yr, zt - 10.85, f"다리 주머니 (경사 30°, 바닥 z{F(g.PK['bottom_z'])}) · 밑 덩어리 z{F(L['bed_z'])}까지 채움", size_px=9.5, anchor="end")
    lead(v, FO["y"][1] - 20, FO["top_z"], yr - 12.0, FO["top_z"] + 36.65, f"접은 상태 (점쇄선): z{F(FO['rib_plane_z'])}~{F(FO['top_z'])}, y{F(FO['y'][0])}~{F(FO['y'][1])} · 접은 다리 (보라 점선)", size_px=9.5, anchor="end")
    lead(v, g.PI["disp1"]["y"][1], g.PI["cad_disp1"]["z"][1], yr, g.PI["board_top_z"] + 15.9, f"Pi 5 (단면) · CAM/DISP 1 x{F(g.PI['disp1']['x'][0])}~{F(g.PI['disp1']['x'][1])} (뒤쪽), 입구 {g.MOUTH_TXT}", size_px=9.5, anchor="end")
    lead(v, g.RR["corner"][1] - 8.5, g.RB["z_run"], yr, g.PI["board_top_z"] + 25.9, f"DSI 리본 (주황) · 전원선 (분홍 점선) — x{F(g.HO['x'][0])}~{F(g.HO['x'][1])}, 단면 앞쪽을 겹쳐 그림", size_px=9.5, anchor="end", cls="rbt")
    lead(v, KO["rear_bar_front_y"] + 12.0, g.WALLS["bottom_z"][1] - 3.0, Y0 + 58.0, g.WALLS["bottom_z"][1] + 5.5, "케이블 통로 (모듈 USB, 열린 앞 공간)", size_px=9.5, anchor="end")
    scalebar(v, Y1 - 46.0, Z0 + 6.0, 20)
    note_lines(v, [f"단면 = x{F(g.XC)} (화면 가운데, 받침다리 가운데), +x 쪽에서 −x를 봄: 오른쪽이 뒤(+y). 실선 = {F(g.TH_USE)}° 사용, 파랑 점선 = {F(g.TH_HEEL)}° 뒤꿈치, 점쇄선 = 90° 접음.",
                   f"{F(g.TH_HEEL)}~90° 전체에서 가장 앞 y{F(g.SWEEP_MIN[0])} ({F(g.TH_HEEL)}°, 받침 앞 아래 모서리 u{F(g.U0)} w{F(g.W0)}) > 금지선 y{F(KO['y_max'])}. 선이 가장 앞으로 나오는 곳 약 y{F(g.CK['cables_fwd_min_y'])}."],
               Y0 + 2, Z1 - 1.5, line_px=14, size_px=9.8)
    rows = [[v]]
    # ------------------------------------------------ B. hinge detail (section through the right ear)
    rows.append([panel_hinge(), panel_fold()])
    base = os.path.join(OUT, "t01_assembly_side")
    K.page(rows, base, sub_head(n, f"조립 옆 단면 — {F(g.TH_USE)}° 사용 · {F(g.TH_HEEL)}° 뒤꿈치 · 90° 접음 (x{F(g.XC)})"),
           subtitle=SRC_LINE + "\n모듈·뒷바·스피커는 확정 L2(body_L2.json)와 건반 모델(geometry.json)에서 그린 참고 윤곽. 화면 쪽 모든 값은 numbers.json.",
           foot=foot_lines())
    add_sheet(n, os.path.basename(base), f"조립 옆 단면 (x{F(g.XC)})",
              f"화면 가운데 x{F(g.XC)} 단면. {F(g.TH_USE)}° 사용(실선), {F(g.TH_HEEL)}° 뒤꿈치(파랑 점선), 90° 접음(점쇄선), 경첩 축 y{F(g.H[0])} z{F(g.H[1])}, "
              f"받침다리 {F(LG['length'])} mm {F(LG['angle_deg'])}°, 모듈 위 금지(y≤{F(KO['y_max'])}, 가장 앞 y{F(g.SWEEP_MIN[0])}), 스피커 {F(g.SP_DEG)}° 소리 길 {F(g.SP_CLEAR)} 위, "
              f"스피커 윗면 z{F(g.PL['speaker_top_z'])} (접은 화면과 {F(FO['speaker_margin'])}), 시선(가운데 y{F(KO['module_rear_y'])}에서 z{F(g.EYE['sightline_centre_z_at_module'])}, "
              f"보이는 영역 아래 끝 z{F(g.EYE['sightline_z_at_module'])}), 건반 모듈·L2 뒷바 윤곽. 확대 A 경첩(오른쪽 귀 단면, 귀 윤곽 = numbers 3a: "
              f"{F(g.TH_HEEL)}°에서 멈춤 블록에 닿고 {F(g.TH_USE)}~90°에서 {F(g.EAR_GAP_25_90)} 이상 뜸), B 접은 상태, 자세별 값·점검 표.")


def clip_scene(v, i0, u0, u1, w0, w1):
    """wrap the elements drawn since i0 in a clip rectangle (world u0..u1, w0..w1), no frame."""
    cid = K.kit.uid("c")
    v.defs.append(f'<clipPath id="{cid}"><rect x="{u0:.4f}" y="{-w1:.4f}" width="{u1 - u0:.4f}" height="{w1 - w0:.4f}"/></clipPath>')
    v.el.insert(i0, f'<g clip-path="url(#{cid})">')
    v.el.append("</g>")
    v._late = [((i + 1) if i >= i0 else i, fn) for i, fn in v._late]


def panel_hinge():
    th = g.TH_USE
    L, KO, HG = g.LID, g.KO, g.HG
    xr_ear = (g.EAR_R[0] + g.EAR_R[1]) / 2
    hy, hz = g.H
    Y0, Y1, Z0, ZC, Z1 = hy - 22.55, hy + 23.45, L["top_z"] - 15.85, hz + 15.65, hz + 20.15
    v = View(Y0, Z0, Y1, Z1, px_width=640, pad_px=6)
    frame_check("t01 zoom A (hinge)", (Y0, Y1, Z0, ZC), (min(p_[0] for p_ in g.knuckle_profile()), max(p_[0] for p_ in g.knuckle_profile()), L["top_z"], hz + g.KP["R"]))
    pid = K.pid_set(v)
    panel_title(v, Y0 + 0.5, Z1 - 1.8, f"확대 A — 경첩, 오른쪽 귀 가운데 x{F(g.XC + xr_ear)} 단면 ({F(g.TH_USE)}° 실선 · {F(g.TH_HEEL)}° 점선)", size_px=12)
    i0 = len(v.el)
    ko = g.rect(Y0, KO["y_max"], KO["z_min"], ZC)
    v.el.append(f'<polygon points="{" ".join(v.P(a, b) for a, b in ko)}" fill="url(#{pid["ko"]})" class="nostroke"/>')
    v.line(KO["y_max"], KO["z_min"], KO["y_max"], ZC, cls="ko-line")
    v.line(Y0, KO["z_min"], KO["y_max"], KO["z_min"], cls="ko")
    adds, subs = lid_section_at(g.XC + xr_ear)
    K.rings_h(v, adds, "m-lid", pid["lid"], subs=subs)
    v.poly(g.knuckle_profile(), cls="vis")
    for (u, w) in ((g.U0, g.W0), (g.U0, g.W1 - g.CH), (g.U0 + g.CH, g.W1)):
        v.poly([g.P(u, w, t) for t in g.SWEEP_TH], cls="pressed3", closed=False)
    for r_ in cradle_outline(g.TH_HEEL):
        v.poly(r_, cls="cr-ph")
    draw_cradle_section(v, None, th, xr_ear, pid["cr"])
    draw_screen(v, th, xr_ear, act=False)
    v.circle(g.H[0], g.H[1], 1.5, cls="m-steel")
    clip_scene(v, i0, Y0, Y1, Z0, ZC)
    hc = HG["heel_contact_yz"]
    v.circle(hc[0], hc[1], v.px(2.6), cls="pivot")
    h25 = g.heel_world(g.TH_USE)
    v.dim_h(KO["y_max"], g.N["all_min_y"], hz + 12.15, text=f"{F(g.CK['keepout_margin'])}", ext_from=(ZC, g.PTS["heel"]["cr_bot_front"][1]), size_px=9.5, tpos="left")
    v.dim_v(L["top_z"], g.H[1], hy + 20.45, text=f"{F(g.H[1] - L['top_z'])} {g.TOL['axis_pos']}", ext_from=(g.KP["base_y"][1], g.H[0]), size_px=9.5)
    v.dim_v(L["top_z"], HG["heel_stop_z"], g.HEEL_STOP["y"][0] - 4.55, text=f"{F(HG['heel_stop_h'])}", ext_from=(g.HEEL_STOP["y"][0], g.HEEL_STOP["y"][0]), size_px=9.5, tpos="left")
    ordy(v, [(KO["y_max"], KO["z_min"], "금지선"), (g.KP["base_y"][0], L["top_z"], "볼 밑 앞 = 멈춤 블록 앞"), (hc[0], hc[1], "뒤꿈치 닿는 곳"),
             (g.HEEL_STOP["y"][1], g.HEEL_STOP["z"][1], "멈춤 블록 뒤"), (g.H[0], g.H[1], f"축 {g.TOL['axis_pos']} (금지선 +{F(g.H[0] - KO['y_max'])})"), (g.KP["base_y"][1], L["top_z"], "볼 밑 뒤")],
         L["top_z"] - 13.85, gap_px=12.5, label_px=9, prefix="y", grow=True)
    v.v0 -= 1.5                                           # a little more room under the rotated ordinate labels
    lead(v, g.H[0] + g.KP["R"] * math.cos(math.radians(55)), g.H[1] + g.KP["R"] * math.sin(math.radians(55)), Y1 - 1.0, hz + 14.15,
         f"뚜껑 볼 R{F(g.KP['R'])} (가는 선, 귀 양옆)", size_px=9, anchor="end")
    T(v, Y1 - 1.0 - v.px(10), hz + 14.15 - v.px(13), f"가까운 볼 Ø{F(g.KN_NEAR_HOLE)} {g.TOL['hole_axle']}", size_px=9, anchor="end", halo=True)
    T(v, Y1 - 1.0 - v.px(10), hz + 14.15 - v.px(26), f"먼 볼 Ø{F(g.KN_FAR_HOLE)} {g.TOL['hole_tap']}", size_px=9, anchor="end", halo=True)
    lead(v, g.H[0] - 3.0, g.H[1] + 3.2, hy + 2.45, hz + 8.65, f"귀 (받침과 한 몸) 축살 R{F(HG['ear_hub_R'])}, M3×20 축", size_px=9)
    lead(v, hc[0], hc[1], Y0 + 1.0, hz + 0.65, f"{F(g.TH_HEEL)}°: 뒤꿈치 R{F(HG['heel_R'])}가 멈춤 블록 z{F(HG['heel_stop_z'])}에 닿음", size_px=9)
    lead(v, h25[0], h25[1], Y0 + 1.0, hz + 4.65, f"{F(g.TH_USE)}°: {F(HG['heel_gap_at_25'])} 뜸 (멈춤 블록 {g.TOL['heel_stop']})", size_px=9)
    ch = g.P(g.U0 + g.CH / 2, g.W1 - g.CH / 2, th)
    lead(v, ch[0], ch[1], Y1 - 1.0, hz - 6.35, f"아래 뒤 모서리 C{F(g.CH)}: 볼과 {F(g.CR['rib_relief_at_cheeks']['gap_after'])} (없으면 {F(g.CR['rib_relief_at_cheeks']['gaps_without']['u-2.5_w16.0'])})", size_px=9, anchor="end")
    q = g.P(g.U0, g.W0, g.TH_HEEL)
    lead(v, q[0], q[1], Y0 + 1.0, hz + 8.65, f"주황 점선 = {F(g.TH_HEEL)}~90° 모서리 자취, 가장 앞 y{F(g.SWEEP_MIN[0])}", size_px=9, cls="kot")
    scalebar(v, hy + 11.45, L["top_z"] - 8.85, 5)
    return v


def panel_fold():
    L, FO, LG = g.LID, g.FO, g.LG
    zt = L["top_z"]
    Y0, Y1, Z0, Z1 = FO["y"][0] - 9.05, L["y"][1] + 62.5, zt - 72.85, FO["top_z"] + 7.65
    v = View(Y0, Z0, Y1, Z1, px_width=840, pad_px=6)
    frame_check("t01 zoom B (fold)", (Y0, Y1, Z0, Z1), (FO["y"][0], L["y"][1], L["bed_z"], FO["top_z"]))
    pid = K.pid_set(v)
    panel_title(v, Y0 + 0.5, Z1 - 1.5, f"확대 B — 접은 상태 (90°, 운반) · 단면 x{F(g.XC)}", size_px=12)
    adds, subs = lid_section_at(g.XC)
    K.rings_h(v, adds, "m-lid", pid["lid"], subs=subs)
    for f in g.FEET:
        if f["x"][1] < g.XC:
            v.poly(g.rect(f["y"][0], f["y"][1], f["z"][0], f["z"][1]), cls="m-lid")
            if f["rear"]:
                v.poly(g.rect(f["lip"]["y"][0], f["lip"]["y"][1], f["z"][1], f["lip"]["z"][1]), cls="m-lid")
    v.poly(g.knuckle_profile(), cls="vis")
    th = g.TH_FOLD
    beh = K.union_rings([g.tf(p, th) for p in g.cradle_behind(0.0)], res=0.04)
    K.stroke_rings(v, beh, "vis")
    draw_cradle_section(v, None, th, 0.0, pid["cr"])
    draw_screen(v, th, 0.0)
    lp = g.LEGP
    stow = [g.P(u, w, th) for (u, w) in g.leg_outline((lp[0], lp[1]), (LG["stow_tip_u"] - g.LEG_R, lp[1]))]
    K.rings_h(v, [stow], "m-leg", pid["leg"], subs=[g.circle(g.P(lp[0], lp[1], th), g.LEG_HOLE / 2, 32)])
    v.line(L["y"][1], L["top_z"] - 12, L["y"][1], Z1 - 4, cls="cl")
    v.dim_h(FO["y"][1], L["y"][1], FO["top_z"] + 3.5, text=f"{F(FO['rear_margin'])}", ext_from=(FO["top_z"], Z1 - 4), size_px=9.5, tpos="left")
    v.dim_h(FO["y"][0], FO["y"][1], FO["top_z"] + 3.5, text=f"{F(FO['y'][1] - FO['y'][0])} 접은 길이", ext_from=(FO["top_z"], FO["top_z"]), size_px=9.5)
    f3 = g.FEET[3]
    f0 = g.FEET[0]
    v.dim_v(L["top_z"], FO["rib_plane_z"], f0["y"][0] - 2.5, text=f"{F(FO['feet_h'])} {g.TOL['fold_feet']}", ext_from=(f0["y"][0], f0["y"][0]), size_px=9.5, tpos="left")
    ordz(v, [(L["top_z"], L["y"][1], "뚜껑 윗면"), (LG["fold_clip_zmin"], g.P(g.CLIPD["u"][1], g.CLIPD["back_w"], th)[0], f"다리 클립 턱 (뚜껑과 {F(g.CK['fold_clip_clear_lid'])})"),
             (LG["fold_clevis_zmin"], g.P(g.LEGP[0] + g.CLV["R"], g.LEGP[1] + g.CLV["R"], th)[0], f"다리 걸이 (뚜껑과 {F(g.CK['fold_leg_clear_lid'])})"),
             (LG["fold_leg_z"][0], LG["fold_leg_y"][1], "접은 다리 밑"), (FO["rib_plane_z"], FO["y"][1], "리브 면 = 받침 발 위"),
             (FO["back_plane_z"], FO["y"][1], "뒷판 뒷면 = 축 높이"), (FO["top_z"], FO["y"][1], "맨 위 (옆벽 앞끝)")],
         L["y"][1] + 5.0, gap_px=12.5, label_px=9, lo=62.0)
    T(v, Y0 + 1.0, zt - 18.85, f"스피커 윗면 z{F(g.PL['speaker_top_z'])}까지 {F(FO['speaker_margin'])} 남음 · 유리가 위를 봄 → 화면 덮개(선택)나 천을 얹음", cls="tx-s", size_px=9.5)
    lead(v, f3["lip"]["y"][1], f3["lip"]["z"][1], FO["y"][0] + 66.95, zt - 14.35, f"뒤 받침 발 턱 y{FR(f3['lip']['y'][0], f3['lip']['y'][1])} z{FR(f3['lip']['z'][0], f3['lip']['z'][1])} (x < {F(g.XC)}, 뒤)", size_px=9)
    scalebar(v, Y0 + 1.0, zt - 14.35, 10)
    checks_block(v, Y0 + 0.5, zt - 26.85)
    return v


def checks_block(v, u0, z_top):
    panel_title(v, u0, z_top, "자세별 값과 점검 (numbers.json · 이 도면 스크립트의 검사)", size_px=12)
    U, Hh, Fo = g.PTS["use"], g.PTS["heel"], g.PTS["fold"]
    cols = ["자세", "유리 아래 (y, z)", "받침 가장 앞 (y, z)", "받침 가장 위 z", "보이는 가운데 (y, z)", "비고"]
    rows = [[f"{F(g.TH_USE)}° 사용", f"{F(U['glass_bottom'][0])}, {F(U['glass_bottom'][1])}", f"{F(U['cr_bot_front'][0])}, {F(U['cr_bot_front'][1])}",
             F(U["cr_top_front"][1]), f"{F(U['act_centre'][0])}, {F(U['act_centre'][1])}", f"다리 {F(g.LG['angle_deg'])}°, 뒤꿈치 {F(g.HG['heel_gap_at_25'])} 뜸"],
            [f"{F(g.TH_HEEL)}° 뒤꿈치", f"{F(Hh['glass_bottom'][0])}, {F(Hh['glass_bottom'][1])}", f"{F(Hh['cr_bot_front'][0])}, {F(Hh['cr_bot_front'][1])}",
             F(Hh["cr_top_front"][1]), f"{F(Hh['act_centre'][0])}, {F(Hh['act_centre'][1])}", f"멈춤 블록 z{F(g.HG['heel_stop_z'])}에 닿음"],
            [f"90° 접음", f"{F(Fo['glass_bottom'][0])}, {F(Fo['glass_bottom'][1])}", f"{F(Fo['cr_bot_front'][0])}, {F(Fo['cr_bot_front'][1])}",
             F(g.FO["top_z"]), "—", f"뒤끝 y{F(g.FO['y'][1])} (뚜껑 뒤끝 {F(g.FO['rear_margin'])} 안)"]]
    zt = K.table(v, u0, z_top - v.px(8), cols, rows, [v.px(q) for q in (62, 118, 128, 84, 128, 300)], row_px=16, size_px=9)
    ck = [c for c in g.CHECKS]
    ok = sum(1 for c in ck if c["ok"])
    KN = dict(keepout_ok="모듈 위 금지", cables_ok="선 금지선", fold_rear_ok="접은 뒤끝", fold_height_ok="접은 높이", leg_stow_ok="다리 접힘",
              ribbon_ok="리본 길이", sightline_ok="시선", ear_block_ok="귀·멈춤 블록", axle_ok="다리 축 나사", leg_swing_22_ok="다리 넣기(22°)",
              notch_ok="아래 벽 홈", clip_groove_ok="클립 홈", lid_screw_ok="뚜껑 나사", sound_rule_ok="소리 27°", pi_orientation_ok="Pi 방향",
              power_wire_ok="전원선 길이", studs_fallback_ok="스터드 대비")
    nchk = [(KN.get(k, k), vv) for k, vv in g.CK.items() if k.endswith("_ok")]
    half = (len(nchk) + 1) // 2
    lines = [f"numbers.json 점검 {sum(1 for k, vv in nchk if vv)}/{len(nchk)} 통과: " + ", ".join(k for k, vv in nchk[:half] if vv) + ",",
             "\u00a0\u00a0" + ", ".join(k for k, vv in nchk[half:] if vv) + f" · C{F(g.CH)} 모따기 필요 → 넣음"
             + (" · 실패: " + ", ".join(k for k, vv in nchk if not vv) if any(not vv for k, vv in nchk) else ""),
             f"도면 스크립트 점검 {ok}/{len(ck)} 통과 (자세 행렬 = 공식, 귀·멈춤 블록 {F(g.EAR_GAP_25_90)}, 다리 축 나사 {F(g.AXLE_GAP['head'][0])}, 소리 길 {F(g.SP_CLEAR)} ≥ {F(g.SP_MIN)}, "
             f"{F(g.TH_HEEL)}~90° 가장 앞 y{F(g.SWEEP_MIN[0])}).",
             f"귀 윤곽 = 축살 R{F(g.HG['ear_hub_R'])} + 받침 아래 + 뒤꿈치 한 점 (3a): 멈춤 블록과 {F(g.TH_HEEL)}°에서 {F(abs(g.EAR_GAP22) if abs(g.EAR_GAP22) < 0.005 else g.EAR_GAP22)} (닿음), "
             f"{F(g.TH_USE)}~90° {F(g.EAR_GAP_25_90)} 이상 (3판 처음 귀는 같은 검사로 {F(g.EAR_OLD_GAP[0])} → 고침).",
             f"평면 소리 길(유닛 가운데 x{F(g.DRV_PLAN[0][0])}·{F(g.DRV_PLAN[1][0])}, y{F(g.DRV_PLAN[0][1])} → 두 귀)은 화면에서 {F(g.SOUND_MIN)} mm 떨어짐 (numbers.json과 도면 계산이 같음).",
             f"10 N으로 화면 위쪽을 누름: 다리 {F(g.ST['leg_force'])} N (좌굴 {g.ST['leg_Pcr']} N) · 앞으로 당김: 뒤꿈치 {g.ST['heel_force']} N, 뚜껑 앞 나사 합계 {g.ST['lid_screws_total']} N."]
    note_lines(v, lines, u0, zt - v.px(14), line_px=14.5, size_px=9.2, cls="lt")


# ================================================================ t02 plan on the CU lid
def draw_lid_plan(v, pid, show_under=True, show_routes=True, labels=True):
    L = g.LID
    # side lids and module strip (context)
    v.rect(L["x"][0] - 40, L["y"][0], 40, L["y"][1] - L["y"][0], cls="faintfill")
    v.rect(L["x"][1], L["y"][0], 40, L["y"][1] - L["y"][0], cls="faintfill")
    v.rect(L["x"][0] - 40, g.KO["module_rear_y"] - 22, L["x"][1] - L["x"][0] + 80, 22, cls="faintfill")
    K.poly_h(v, g.rect(L["x"][0], L["x"][1], L["y"][0], L["y"][1]), "m-lid", None)
    if show_under:
        for cid in ("PR-SEAMRAIL-1", "PR-SEAMRAIL-2", "PR-SEAMPOST-1", "PR-SEAMPOST-2"):
            x0, x1, y0, y1 = g.bbox_xy(cid)
            v.rect(x0, y0, x1 - x0, y1 - y0, cls="hid")
        pi = g.PI
        v.rect(pi["board_x"][0], pi["board_y"][0], pi["board_x"][1] - pi["board_x"][0], pi["board_y"][1] - pi["board_y"][0], cls="env")
        for key in ("heatsink", "hdmi"):
            q = pi[key]
            v.rect(q["x"][0], q["y"][0], q["x"][1] - q["x"][0], q["y"][1] - q["y"][0], cls="hid")
        for cid in ("CU-E-PI5-USBA1", "CU-E-PI5-USBA2"):
            x0, x1, y0, y1 = g.bbox_xy(cid)
            v.rect(x0, y0, x1 - x0, y1 - y0, cls="hid")
        d1, d0 = pi["disp1"], pi["disp0"]
        v.rect(d1["x"][0], d1["y"][0], d1["x"][1] - d1["x"][0], d1["y"][1] - d1["y"][0], cls="m-lead")
        v.rect(d0["x"][0], d0["y"][0], d0["x"][1] - d0["x"][0], d0["y"][1] - d0["y"][0], cls="hid")
        kz = g.PL["keepout_zones"]
        v.rect(kz["dsi"]["x"][0], kz["dsi"]["y"][0], kz["dsi"]["x"][1] - kz["dsi"]["x"][0], kz["dsi"]["y"][1] - kz["dsi"]["y"][0], cls="zone")
        v.rect(kz["gpio"]["x"][0], kz["gpio"]["y"][0], kz["gpio"]["x"][1] - kz["gpio"]["x"][0], kz["gpio"]["y"][1] - kz["gpio"]["y"][0], cls="zone")
        pp = g.PIN_PITCH
        v.rect(g.GP2[0] - pp / 2, g.GP2[1] - 1.5 * pp, 20 * pp, 2 * pp, cls="m-black")
        v.circle(g.GP2[0], g.GP2[1], 0.9, cls="wire5")
        v.circle(g.GP6[0], g.GP6[1], 0.9, cls="wireg")
        # filled blocks under the plate (hidden): knuckle fills, hole wall, clip pad, pocket block
        for kn in (g.KNL, g.KNR):
            v.rect(kn["all"][0], g.KN_FILL["y"][0], kn["all"][1] - kn["all"][0], g.KN_FILL["y"][1] - g.KN_FILL["y"][0], cls="hid")
        hw = g.HOLE_WALL
        v.rect(hw[0], hw[2], hw[1] - hw[0], hw[3] - hw[2], cls="hid")
        cp = g.CL["pad"]
        v.rect(cp["x"][0], cp["y"][0], cp["x"][1] - cp["x"][0], cp["y"][1] - cp["y"][0], cls="hid")
        for pn in g.CL["pins"]:
            v.circle(pn[0], pn[1], g.PIN_HOLE[0] / 2, cls="hid")
        b = g.PK["block"]
        v.rect(b["x"][0], b["y"][0], b["x"][1] - b["x"][0], b["y"][1] - b["y"][0], cls="hid")
    # vents
    for sl in g.V["slots"]:
        v.rect(sl[0], sl[2], sl[1] - sl[0], sl[3] - sl[2], cls="void")
    # fold feet (+ lips)
    for f in g.FEET:
        v.rect(f["x"][0], f["y"][0], f["x"][1] - f["x"][0], f["y"][1] - f["y"][0], cls="m-print2")
        if f["rear"]:
            v.rect(f["x"][0], f["lip"]["y"][0], f["x"][1] - f["x"][0], f["lip"]["y"][1] - f["lip"]["y"][0], cls="m-print")
    # knuckles: near / far cheeks, ear slot with the heel stop
    for kn, side in ((g.KNL, "left"), (g.KNR, "right")):
        for part in ("near", "far"):
            v.rect(kn[part][0], g.KP["base_y"][0], kn[part][1] - kn[part][0], g.KP["base_y"][1] - g.KP["base_y"][0], cls="m-print2")
        sl = g.SLOT[side]
        v.rect(sl[0], g.HEEL_STOP["y"][0], sl[1] - sl[0], g.HEEL_STOP["y"][1] - g.HEEL_STOP["y"][0], cls="m-print")
        v.line(kn["all"][0] - 3, g.H[0], kn["all"][1] + 3, g.H[0], cls="cl")
    # pocket
    pk = g.PK
    v.rect(pk["x"][0], pk["ramp_front_y"], pk["x"][1] - pk["x"][0], pk["back_wall_y"] - pk["ramp_front_y"], cls="void")
    v.line(pk["x"][0], pk["ramp_end_y"], pk["x"][1], pk["ramp_end_y"], cls="vis")
    # lid hole (22 x 6, R1)
    ho = g.HO
    v.rect(ho["x"][0], ho["y"][0], ho["x"][1] - ho["x"][0], ho["y"][1] - ho["y"][0], cls="void", rx=ho["edge_R"])
    # lid screws M3x10 + counterbore
    for (x, y) in g.SCREWS:
        v.circle(x, y, g.LID_SCREW["d_cbore"] / 2, cls="void")
        v.circle(x, y, 1.6, cls="ln")
    if show_routes:
        rp = g.ribbon_plan_rects()
        for k in ("run_y", "run_x"):
            v.poly(rp[k], cls="ffc")
        v.poly(rp["into"], cls="ffc")
        fx, fy = rp["fold"]
        h = g.RB_W / 2
        v.line(fx - h, fy - h, fx + h, fy + h, cls="rib-t")
        v.circle(rp["drop"][0], rp["drop"][1], v.px(2.4), cls="dot")
        pw = [(q[0], q[1]) for q in g.PW["waypoints"]]
        v.poly(pw, cls="pw", closed=False)


def sheet_t02():
    n = 2
    L = g.LID
    X0, X1, Y0, Y1 = L["x"][0] - 61.0, L["x"][1] + 87.0, g.KO["module_rear_y"] - 94.0, L["y"][1] + 14.5
    v = View(X0, Y0, X1, Y1, px_width=1480, pad_px=6)
    frame_check("t02 plan", (X0, X1, Y0, Y1), (L["x"][0], L["x"][1], L["y"][0], L["y"][1]))
    pid = K.pid_set(v)
    draw_lid_plan(v, pid)
    fp = g.FP
    v.rect(g.CR["x"][0], fp["front_25"], g.CR["x"][1] - g.CR["x"][0], fp["rear_25"] - fp["front_25"], cls="cr-ph")
    v.line(g.CR["x"][0], fp["front_22"], g.CR["x"][1], fp["front_22"], cls="cr-ph")
    v.rect(g.CR["x"][0], g.FO["y"][0], g.CR["x"][1] - g.CR["x"][0], g.FO["y"][1] - g.FO["y"][0], cls="fold-ph")
    lg = g.LG
    v.rect(lg["x"][0], lg["pivot_yz"][0] - g.LEG_R, lg["x"][1] - lg["x"][0], lg["tip_yz"][0] - lg["pivot_yz"][0] + 2 * g.LEG_R, cls="leg-ph")
    v.line(L["x"][0] - 38, g.KO["y_max"], L["x"][1] + 38, g.KO["y_max"], cls="ko-line")
    T(v, L["x"][0] - 37, g.KO["y_max"] - 4.5, f"모듈 위 금지선 y{F(g.KO['y_max'])} (모듈 뒤끝 y{F(g.KO['module_rear_y'])}, 뒷바 앞 y{F(g.KO['rear_bar_front_y'])})", cls="kot", size_px=10, halo=True)
    T(v, L["x"][0] - 37, g.KO["module_rear_y"] - 13, "건반 모듈 뒤쪽 (O4 둘레, 위로 뺌)", cls="tx-s", size_px=10)
    T(v, L["x"][0] - 20, (L["y"][0] + L["y"][1]) / 2, "LID-L (오꾸메, 자석)", cls="tx-s", size_px=9.5, anchor="middle", rot=-90)
    T(v, L["x"][1] + 20, (L["y"][0] + L["y"][1]) / 2, "LID-R (오꾸메, 자석)", cls="tx-s", size_px=9.5, anchor="middle", rot=-90)
    xf = [(L["x"][0], L["y"][0], "뚜껑"), (g.CR["x"][0], g.FO["y"][0], "받침"), (g.KNL["all"][0], g.KP["base_y"][0], "왼 경첩"),
          (g.KNL["all"][1], g.KP["base_y"][0], ""), (g.PK["x"][0], g.PK["ramp_front_y"], "주머니"), (g.XC, g.N["all_min_y"], "화면 가운데"),
          (g.PK["x"][1], g.PK["ramp_front_y"], ""), (g.HO["x"][0], g.HO["y"][0], "구멍"), (g.HO["x"][1], g.HO["y"][0], ""),
          (g.KNR["all"][0], g.KP["base_y"][0], "오른 경첩"), (g.KNR["all"][1], g.KP["base_y"][0], ""), (g.CR["x"][1], g.FO["y"][0], "받침"),
          (L["x"][1], L["y"][0], "뚜껑"), (g.FEET[0]["x"][0], g.FEET[0]["y"][0], "발"), (g.FEET[0]["x"][1], g.FEET[0]["y"][0], ""),
          (g.FEET[2]["x"][0], g.FEET[2]["y"][0], "발"), (g.FEET[2]["x"][1], g.FEET[2]["y"][0], ""),
          (g.V["slots"][0][0], g.V["slots"][0][2], "통풍"), (g.V["slots"][0][1], g.V["slots"][0][2], ""), (g.V["slots"][1][0], g.V["slots"][1][2], "통풍"),
          (g.V["slots"][1][1], g.V["slots"][1][2], ""), (g.SCREWS[0][0], g.SCREWS[0][1], "나사"), (g.SCREWS[1][0], g.SCREWS[1][1], "나사")]
    xb = ordy(v, xf, g.KO["module_rear_y"] - 25.0, gap_px=12.5, label_px=9, prefix="x")
    yfeat = [(L["y"][0], L["x"][1], "뚜껑 앞"), (g.KP["base_y"][0], g.KNR["all"][1], "볼 밑 앞"), (g.HO["y"][0], g.HO["x"][1], "구멍"),
             (g.HO["y"][1], g.HO["x"][1], ""), (g.H[0], g.KNR["all"][1], f"경첩 축 {g.TOL['axis_pos']}"), (g.KP["base_y"][1], g.KNR["all"][1], "볼 밑 뒤"),
             (g.PL["lid_screw"]["y"][0], g.SCREWS[1][0], "앞 나사"), (g.FEET[2]["y"][0], g.FEET[2]["x"][1], "앞 발"), (g.FEET[2]["y"][1], g.FEET[2]["x"][1], ""),
             (g.PK["ramp_front_y"], g.PK["x"][1], "주머니 경사"), (g.PK["back_wall_y"], g.PK["x"][1], "주머니 뒷벽"), (g.V["band_y"][0], g.V["slots"][1][1], "통풍"),
             (g.V["band_y"][1], g.V["slots"][1][1], ""), (g.FEET[3]["y"][0], g.FEET[3]["x"][1], "뒤 발"), (g.FEET[3]["y"][1], g.FEET[3]["x"][1], ""),
             (g.PL["lid_screw"]["y"][1], g.SCREWS[3][0], "뒤 나사"), (g.FEET[3]["lip"]["y"][1], g.FEET[3]["x"][1], "턱"),
             (g.FO["y"][1], g.CR["x"][1], "접음 뒤끝"), (L["y"][1], L["x"][1], "뚜껑 뒤")]
    ordz(v, yfeat, L["x"][1] + 44.0, side="right", gap_px=12.5, label_px=9, prefix="y")
    v.dim_h(L["x"][0], L["x"][1], L["y"][1] + 7.0, text=f"{F(L['x'][1] - L['x'][0])} 화면 뚜껑 (CU-SCREENLID)", ext_from=(L["y"][1], L["y"][1]), size_px=10)
    v.dim_h(g.CR["x"][0], g.CR["x"][1], L["y"][1] + 2.8, text=f"{F(g.CR['x'][1] - g.CR['x'][0])} 받침", ext_from=(g.FO["y"][1], g.FO["y"][1]), size_px=9.5)
    v.dim_v(L["y"][0], L["y"][1], L["x"][0] - 44.0, text=f"{F(L['y'][1] - L['y'][0])}", ext_from=(L["x"][0], L["x"][0]), size_px=10)
    rp = g.ribbon_plan_rects()
    items = [
        ("A", (g.KNL["near"][0], g.KP["base_y"][1]), (-26, 14), f"왼 경첩: 가까운 볼 x{FR(*g.KNL['near'])} · 귀 홈 x{FR(*g.SLOT['left'])} (귀 x{FR(*g.KNL['ear'])}) · 먼 볼 x{FR(*g.KNL['far'])}, M3×20을 −x에서 (먼 볼 Ø{F(g.KN_FAR_HOLE)} 탭, 물림 {F(g.KN_ENGAGE)})"),
        ("B", (g.KNR["near"][1], g.KP["base_y"][1]), (26, 14), f"오른 경첩: 먼 볼 x{FR(*g.KNR['far'])} · 귀 홈 x{FR(*g.SLOT['right'])} (귀 x{FR(*g.KNR['ear'])}) · 가까운 볼 x{FR(*g.KNR['near'])}, M3×20을 +x에서"),
        ("C", ((g.SLOT["right"][0] + g.SLOT["right"][1]) / 2, g.HEEL_STOP["y"][0] + 2), (18, -20), f"뒤꿈치 멈춤 블록 (귀 홈 바닥) y{FR(*g.HEEL_STOP['y'])} z{FR(*g.HEEL_STOP['z'])}"),
        ("D", (g.HO["x"][0], (g.HO["y"][0] + g.HO["y"][1]) / 2), (-22, -22), f"리본·전원선 구멍 {F(g.HO['x'][1] - g.HO['x'][0])}×{F(g.HO['y'][1] - g.HO['y'][0])} R{F(g.HO['edge_R'])} 관통, 둘레 벽 {F(g.HO['wall'])} (z{F(L['bed_z'])}까지)"),
        ("E", tuple(g.CL["pins"][0]), (-26, 10), f"리본 클립 덩어리 (뚜껑 밑) x{FR(*g.CL['pad']['x'])} y{FR(*g.CL['pad']['y'])}, 핀 구멍 Ø{F(g.PIN_HOLE[0])}×{F(g.PIN_HOLE[1])} 2개 · 클립 전원선 홈 x{FR(*g.WG['x'])}"),
        ("F", (g.PK["x"][0], g.PK["ramp_front_y"] + 3), (-24, 0), f"다리 주머니 x{FR(*g.PK['x'])}: 경사 30° y{FR(g.PK['ramp_front_y'], g.PK['ramp_end_y'])}, 바닥 z{F(g.PK['bottom_z'])} {g.TOL['pocket']}, 뒷벽 y{F(g.PK['back_wall_y'])}"),
        ("G", (g.V["slots"][6][0], g.V["slots"][6][3]), (-20, 18), f"통풍 슬롯 {len(g.V['slots'])}개 {F(g.V['slot'][0])}×{F(g.V['slot'][1])}, x{FR(g.V['slots'][0][0], g.V['slots'][0][1])} · {FR(g.V['slots'][1][0], g.V['slots'][1][1])}, 간격 {F(g.V['pitch'])} — 접으면 덮임"),
        ("H", (g.FEET[3]["x"][1], g.FEET[3]["lip"]["y"][1]), (22, 16), f"접이 받침 발 {len(g.FEET)}개 {g.FEET_SZ}×{F(g.FO['feet_h'])} {g.TOL['fold_feet']}, 뒤 발 턱 y{FR(*g.FEET[3]['lip']['y'])} 높이 {F(g.FEET[3]['lip']['z'][1] - g.FEET[3]['lip']['z'][0])}"),
        ("I", g.SCREWS[3], (22, 12), f"뚜껑 나사 M3×10 ×4 (레일 인서트) x{F(g.SCREWS[0][0])}·{F(g.SCREWS[1][0])} (추정) y{F(g.SCREWS[0][1])}·{F(g.SCREWS[2][1])}, 자리파기 Ø{F(g.LID_SCREW['d_cbore'])}"),
        ("J", (g.CR["x"][0], g.FP["front_25"] + 20), (-24, 0), f"세운 화면 발자국 (파랑 점선): {F(g.TH_USE)}° y{FR(g.FP['front_25'], g.FP['rear_25'])} · {F(g.TH_HEEL)}° 앞끝 y{F(g.FP['front_22'])} (선), 받침 x{FR(*g.CR['x'])}"),
        ("K", (g.CR["x"][0], g.FO["y"][1] - 10), (-24, 0), f"접은 화면 (점쇄선) y{FR(*g.FO['y'])} · 받침다리 (보라 점선) x{FR(*g.LG['x'])}"),
        ("L", ((rp["fold"][0] + rp["drop"][0]) / 2 + 12, rp["fold"][1] + g.RB_W / 2), (6, 22), f"DSI 리본 폭 {F(g.RB_W)}: 구멍 → +y {F(rp['run_y_len'])} → 45° 접기 → −x {F(rp['run_x_len'])} → 기둥 x{F(g.RR['drop'][0])}에서 아래로 {F(g.RB['parts']['drop'])} → HDMI 위 → 입구"),
        ("M", (g.PW["waypoints"][2][0], g.PW["waypoints"][2][1] - 15.77), (22, 0), f"전원선 (분홍): 구멍 → 클립 홈 → +y → −x → GPIO 2·6, 뚜껑 밑 z{F(g.PW['waypoints'][1][2])}"),
        ("N", (g.PI["disp1"]["x"][0], g.PI["disp1"]["y"][0] + 2), (-34, -26), f"Pi 5 CAM/DISP 1 x{FR(*g.PI['disp1']['x'], 0)} y{FR(*g.PI['disp1']['y'], 0)} (입구 {g.MOUTH_TXT}, L2 글에서 읽은 방향), 주황 점선 = DSI 지킴 구역 x{FR(*g.PL['keepout_zones']['dsi']['x'], 0)}"),
        ("O", tuple(g.GP2), (-22, 14), f"GPIO 핀 2 (5 V) x{F(g.GP2[0])} · 핀 6 (GND) x{F(g.GP6[0])}, y{F(g.GP2[1])}, 핀 끝 z{F(g.PI['gpio_top_z'])}"),
        ("P", (g.PI["board_x"][1], g.PI["board_y"][0] + 4), (22, -14), f"Pi 5 판 x{FR(*g.PI['board_x'], 0)} y{FR(*g.PI['board_y'], 0)} 윗면 z{F(g.PI['board_top_z'])} (뚜껑 밑, 초록 점선) · USB-A 2단"),
        ("Q", (g.bbox_xy("PR-SEAMRAIL-1")[1], g.bbox_xy("PR-SEAMRAIL-1")[3]), (-18, 14), "뚜껑 이음 레일 20×6 · 앞 기둥 10×10 (CAD L2, 점선) — 나사 인서트 자리"),
    ]
    half = (len(items) + 1) // 2
    top2 = Y0 + 36.0
    K.callouts(v, items[:half], X0 + 2.0, top2, line_px=14.5, size_px=9.6)
    for i, (tag, fpt, d, text) in enumerate(items[half:]):
        z = top2 - i * v.px(14.5)
        r = v.px(7.0)
        uu = X0 + 186.0
        v.circle(uu + r, z + v.px(3.4), r, cls="bl")
        v.text(uu + r, z, tag, cls="bt", size_px=9, dy_px=0.2)
        v.text(uu + 2 * r + v.px(5), z, text, cls="lt", anchor="start", size_px=9.6)
        tu, tv = fpt[0] + v.px(d[0]), fpt[1] + v.px(d[1])
        Lr = math.hypot(tu - fpt[0], tv - fpt[1])
        if Lr > r:
            v.line(fpt[0], fpt[1], tu - (tu - fpt[0]) * r / Lr, tv - (tv - fpt[1]) * r / Lr, cls="ld")
        v.circle(fpt[0], fpt[1], v.px(1.6), cls="dot")
        v.circle(tu, tv, r, cls="bl")
        v.text(tu, tv, tag, cls="bt", size_px=9, dy_px=3.2)
    scalebar(v, X1 - 68.0, Y0 + 62.0, 20)
    note_lines(v, ["위에서 본 평면: 아래쪽이 연주자(−y). 굵은 선 = 뚜껑 윗면에 보이는 것, 점선 = 뚜껑 밑 (리브 밑 z" + F(L["bed_z"]) + "까지 채운 덩어리 · Pi 5 · 레일).",
                   "갈비(리브) 배치와 앞 윗모서리 1×45° 모따기는 CAD L2 설계를 따름. 화면 뚜껑에는 자석 없음 (D14)."], X0 + 2, Y1 - 3, line_px=14, size_px=9.8)
    rows = [[v], [panel_zoom_left(), panel_zoom_right(), panel_overview()]]
    base = os.path.join(OUT, "t02_lid_plan")
    K.page(rows, base, sub_head(n, "가운데 뚜껑 평면 — 경첩 · 주머니 · 구멍 · 통풍 · 받침 발 · 나사 · Pi 5 · 선 길"),
           subtitle=SRC_LINE, foot=foot_lines())
    add_sheet(n, os.path.basename(base), "가운데 뚜껑 평면",
              f"L2 가운데 화면 뚜껑 x{FR(*L['x'], 1)}, y{FR(*L['y'], 1)} 평면. 받침 발자국({F(g.TH_USE)}° y{FR(g.FP['front_25'], g.FP['rear_25'])}, {F(g.TH_HEEL)}° 앞끝 y{F(g.FP['front_22'])}, "
              f"접음 y{FR(*g.FO['y'])}), 경첩 2 (귀 홈 {F(g.SLOT['left'][1] - g.SLOT['left'][0])}), 멈춤 블록, 다리 주머니, 리본 구멍 {F(g.HO['x'][1] - g.HO['x'][0])}×{F(g.HO['y'][1] - g.HO['y'][0])}, "
              f"클립(전원선 홈), 통풍 {len(g.V['slots'])}, 받침 발 {len(g.FEET)}, 뚜껑 나사 {len(g.SCREWS)}, Pi 5·CAM/DISP 1(입구 {g.MOUTH_TXT})·GPIO 2·6, "
              f"DSI 리본(폭 {F(g.RB_W)}, 기둥 x{F(g.RR['drop'][0])} → HDMI 위 → 입구)과 전원선 길. 확대: 왼 경첩, 구멍·클립·오른 경첩. 전체 평면: 소리 길 4개 (화면까지 {F(g.SOUND_MIN)}).")


def zoom_band(v, X0, X1, Y0, Y1):
    pid = K.pid_set(v)
    i0 = len(v.el)
    draw_lid_plan(v, pid, show_under=True, show_routes=False)
    for side, kn in (("left", g.KNL), ("right", g.KNR)):
        e = [g.XC + q for q in g.HG[side]["ear"]]
        v.rect(e[0], g.H[0] - g.HG["ear_hub_R"], e[1] - e[0], 2 * g.HG["ear_hub_R"], cls="cr-ph")
        v.line(kn["all"][0], g.H[0], kn["all"][1], g.H[0], cls="lead")
    clip_scene(v, i0, X0, X1, Y0, Y1)
    v.line(X0, g.KO["y_max"], X1, g.KO["y_max"], cls="ko-line")


def panel_zoom_left():
    X0 = g.KNL["all"][0] - 6.6
    X1, Y0 = X0 + 34.0, g.H[0] - 14.55
    Y1 = Y0 + 34.0
    v = View(X0, Y0 - 6, X1, Y1 + 8, px_width=330, pad_px=6)
    frame_check("t02 zoom C (left hinge)", (X0, X1, Y0, Y1), (g.KNL["all"][0], g.KNL["all"][1], g.KP["base_y"][0], g.KP["base_y"][1]))
    panel_title(v, X0, Y1 + 5.5, "확대 C — 왼 경첩 (위에서)", size_px=11.5)
    zoom_band(v, X0, X1, Y0, Y1)
    kn = g.KNL
    ordy(v, [(kn["near"][0], g.KP["base_y"][0], ""), (kn["near"][1], g.KP["base_y"][0], ""), (kn["ear"][0], g.H[0], "귀"), (kn["ear"][1], g.H[0], ""),
             (kn["far"][0], g.KP["base_y"][0], ""), (kn["far"][1], g.KP["base_y"][0], "")], Y0 - 1.0, gap_px=12.5, label_px=9, prefix="x")
    T(v, X0 + 0.5, Y1 + 1.5, f"볼 {F(kn['near'][1] - kn['near'][0])} + 틈 {F(g.KN_GAP)} + 귀 {F(kn['ear'][1] - kn['ear'][0])} + 틈 {F(g.KN_GAP)} + 볼 {F(kn['far'][1] - kn['far'][0])} = {F(kn['all'][1] - kn['all'][0])}", size_px=9, halo=True)
    T(v, X0 + 0.5, Y1 - 2.0, f"틈 {g.TOL['slot_gap']} · 파랑 점선 = 받침 귀", size_px=9, halo=True)
    return v


def panel_zoom_right():
    X0, X1 = g.HOLE_WALL[0] - 7.35, g.KNR["all"][1] + 6.6
    Y0, Y1 = g.H[0] - 14.55, g.CL["pad"]["y"][1] + 3.45
    v = View(X0, Y0 - 6, X1 + 19.0, Y1 + 8, px_width=560, pad_px=6)
    frame_check("t02 zoom D (hole, clip, right hinge)", (X0, X1, Y0, Y1), (g.HOLE_WALL[0], g.KNR["all"][1], g.HO["y"][0], g.CL["pad"]["y"][1]))
    panel_title(v, X0, Y1 + 5.5, "확대 D — 구멍 · 클립 · 오른 경첩 (위에서, 점선 = 뚜껑 밑)", size_px=11.5)
    zoom_band(v, X0, X1, Y0, Y1)
    kn = g.KNR
    hw = g.HOLE_WALL
    ordy(v, [(hw[0], hw[2], "벽"), (g.HO["x"][0], g.HO["y"][0], "구멍"), (g.CL["pins"][0][0], g.CL["pins"][0][1], "핀"), (g.CL["pad"]["x"][0], g.CL["pad"]["y"][1], "클립"),
             (g.HO["x"][1], g.HO["y"][0], "구멍"), (g.CL["pins"][1][0], g.CL["pins"][1][1], "핀"), (hw[1], hw[2], "벽"), (g.CL["pad"]["x"][1], g.CL["pad"]["y"][1], "클립"),
             (kn["far"][0], g.KP["base_y"][0], ""), (kn["far"][1], g.KP["base_y"][0], ""), (kn["ear"][0], g.H[0], "귀"), (kn["ear"][1], g.H[0], ""),
             (kn["near"][0], g.KP["base_y"][0], ""), (kn["near"][1], g.KP["base_y"][0], "")], Y0 - 1.0, gap_px=12.5, label_px=9, prefix="x")
    ordz(v, [(g.HO["y"][0], g.HO["x"][1], "구멍"), (g.HO["y"][1], g.HO["x"][1], ""), (hw[3], hw[1], "벽 = 클립 앞"), (g.CL["pins"][0][1], g.CL["pins"][1][0], "핀"),
             (g.CL["pad"]["y"][1], g.CL["pad"]["x"][1], "클립 뒤"), (g.H[0], kn["all"][1], "축"), (g.KP["base_y"][1], kn["all"][1], "볼 밑 뒤")],
         X1 + 1.0, side="right", gap_px=12.5, label_px=9, prefix="y")
    return v


def panel_overview():
    bx = g.PL["body_x"]
    X0, X1 = bx[0] - 24.0, bx[1] + 42.0
    Y0, Y1 = g.CTX["eye"][0] - 30.0, g.PL["rear_face_y"] + 18.5
    v = View(X0, Y0, X1, Y1, px_width=570, pad_px=6)
    frame_check("t02 overview", (X0, X1, Y0, Y1), (bx[0], bx[1], g.CTX["eye"][0], g.PL["rear_face_y"]))
    panel_title(v, X0, Y1 - 6, "전체 평면 — 소리 길 4개 (실제 유닛 → 두 귀)", size_px=11)
    kx = g.CTX["key_x"]
    v.rect(kx[0], 0.0, kx[1] - kx[0], g.KO["module_rear_y"], cls="faintfill")
    bx = g.PL["body_x"]
    v.rect(bx[0], g.KO["rear_bar_front_y"], bx[1] - bx[0], g.PL["rear_face_y"] - g.KO["rear_bar_front_y"], cls="m-wood")
    for sx in (g.SPK_X["L"], g.SPK_X["R"]):
        v.rect(sx[0], g.KO["rear_bar_front_y"], sx[1] - sx[0], g.PL["rear_face_y"] - g.KO["rear_bar_front_y"], cls="spk")
    v.rect(g.LID["x"][0], g.LID["y"][0], g.LID["x"][1] - g.LID["x"][0], g.LID["y"][1] - g.LID["y"][0], cls="m-lid")
    r = g.SCR_RECT
    v.rect(r[0], r[1], r[2] - r[0], r[3] - r[1], cls="m-cr")
    for p in g.SOUND_PATHS:
        v.line(p["src"][0], p["src"][1], p["ear"][0], p["ear"][1], cls="snd")
        v.circle(p["src"][0], p["src"][1], g.CONE_D / 2, cls="ln")
    for e in g.EARS:
        v.circle(e[0], e[1], v.px(3), cls="dot")
    v.circle(g.CTX["player_x"], g.CTX["eye"][0], 70.0, cls="ph2")
    T(v, g.CTX["player_x"] + 150.0, g.CTX["eye"][0] - 10.0, f"연주자 (x{F(g.CTX['player_x'])}, 귀 ±{F(g.CTX['ear_dx'])}, 추정)", anchor="start", size_px=9.5)
    T(v, X0 + 10, Y0 + 230.0, f"소리 길 → 화면: 가장 가까운 곳 {F(g.SOUND_MIN)} mm", cls="sndt", size_px=9.5)
    T(v, X0 + 10, Y0 + 190.0, f"(유닛 가운데 x{F(g.DRV_PLAN[0][0])}·{F(g.DRV_PLAN[1][0])}, y{F(g.DRV_PLAN[0][1])}: body_L2)", cls="tx-s", size_px=9)
    T(v, kx[1] / 2, g.KO["module_rear_y"] / 2 - 10, "건반 88", anchor="middle", cls="tx-s", size_px=9.5)
    return v


# ================================================================ t03 cradle part drawing
def sw(poly):
    return [(w, u) for (u, w) in poly]


def cr_front(v, mirror=False, back=False):
    """cradle seen along w: front (from the glass side) or back (from behind, drawn mirrored so +xr is on the left).
    View u = xr (front) or -xr (back), v = u."""
    X = (lambda x: -x) if mirror else (lambda x: x)

    def R(x0, x1, u0, u1, cls):
        a, b = sorted([X(x0), X(x1)])
        v.rect(a, u0, b - a, u1 - u0, cls=cls)

    def C(x, u, r, cls):
        v.circle(X(x), u, r, cls=cls)
    xo, xi = g.XR1, g.XIN
    # ears (below the bottom)
    for side in ("left", "right"):
        e = g.HG[side]["ear"]
        R(e[0], e[1], g.EAR_U[0], g.U0, "m-cr")
        v.line(X(e[0]) - 2, g.UA, X(e[1]) + 2, g.UA, cls="cl")
    if not back:
        R(-xo, xo, g.U0, g.U1, "m-cr")
        R(-xi, xi, g.BOT_IN, g.TOP_IN, "m-sbar")                         # plate front face seen in the opening (w10.5)
        R(g.INSP["xr"][0], g.INSP["xr"][1], g.INSP["u"][0], g.INSP["u"][1], "void")
        R(g.HP["xr"][0], g.HP["xr"][1], g.HP["u"][0], g.HP["u"][1], "m-cr")
        for xb in g.BO["xr"]:
            for ub in g.BO["u"]:
                a, b = sorted([xb, math.copysign(xi, xb)])
                R(a, b, ub - g.BO["d"] / 2, ub + g.BO["d"] / 2, "m-cr")
                C(xb, ub, g.BO["d"] / 2, "m-cr")
                C(xb, ub, g.BO["hole_d"] / 2, "void")
        gr = g.GR
        R(gr["xr"][0], gr["xr"][1], g.U0, gr["u"][1], "hid")
        nt = g.NOTCH                                                    # 3a bottom-wall notch: see-through to w8 (face behind)
        R(nt["xr"][0], nt["xr"][1], nt["u"][0], nt["u"][1], "m-sbar")
        # screen (phantom)
        R(-g.GX, g.GX, 0.0, g.GH, "ph2")
        R(g.ACT_XR[0], g.ACT_XR[1], g.ACT_U[0], g.ACT_U[1], "cr-ph2")
    else:
        R(-xo, xo, g.U0, g.U1, "m-cr")
        R(-xi, xi, g.BOT_IN, g.TOP_IN, "m-sbar")                         # plate back face w13
        v.line(X(-xo), g.U0 + g.CH, X(xo), g.U0 + g.CH, cls="vis")        # C2 chamfer edge
        wi, wo = g.WRIB_IN, g.WRIB_OUT
        R(wo[0], wo[1], wo[2], wo[3], "m-cr")
        R(g.INSP["xr"][0], g.INSP["xr"][1], g.INSP["u"][0], g.INSP["u"][1], "void")
        R(wi[0], g.INSP["xr"][0], g.INSP["u"][0], wi[3], "m-sbar")
        R(g.INSP["xr"][1], wi[1], g.INSP["u"][0], wi[3], "m-sbar")
        R(wi[0], wi[1], wi[2], g.INSP["u"][0], "m-sbar")
        R(wi[0], wi[1], g.INSP["u"][1], wi[3], "m-sbar")
        # screen parts seen through the window (estimates)
        R(g.S["window"]["xr"][0], g.S["window"]["xr"][1], g.S["window"]["u"][0], g.S["window"]["u"][1], "ph2")
        R(g.S["fpc"]["xr"][0], g.S["fpc"]["xr"][1], g.S["fpc"]["u"][0], g.S["fpc"]["u"][1], "conn")
        R(g.S["pwr"]["xr"][0], g.S["pwr"]["xr"][1], g.S["pwr"]["u"][0], g.S["pwr"]["u"][1], "conn")
        R(g.FSQ["xr"][0], g.FSQ["xr"][1], g.FSQ["u"][0], g.FSQ["u"][1], "rib-t")
        R(g.CR["rib_band_xr"][0], g.CR["rib_band_xr"][1], g.U0, g.FSQ["u"][0], "rib-t")
        R(g.S["fpc"]["mouth_xr"], g.FSQ["xr"][0], g.S["fpc"]["pin_u_centre"] - g.RB_W / 2, g.S["fpc"]["pin_u_centre"] + g.RB_W / 2, "rib-t")
        wx = sum(g.CR["wire_xr"]) / 2
        pu = sum(g.S["pwr"]["u"]) / 2
        v.poly([(X(g.S["pwr"]["mouth_xr"]), pu), (X(wx), pu), (X(wx), g.U0)], cls="pw", closed=False)
        for uu in g.XRIB:
            for a, b in ((-xi, g.CHW["xr_walls"][0][0]), (g.CHW["xr_walls"][1][1], xi)):
                R(a, b, uu - g.RIB_T / 2, uu + g.RIB_T / 2, "m-cr")
        for w_ in g.CHW["xr_walls"]:
            R(w_[0], w_[1], g.CHW["u"][0], g.CHW["u"][1], "m-cr")
        for pd in g.PADS:
            R(pd["xr"][0], pd["xr"][1], pd["u"][0], pd["u"][1], "m-print2")
        for xb in g.BO["xr"]:
            for ub in g.BO["u"]:
                a, b = sorted([xb, math.copysign(xi, xb)])
                R(a, b, ub - g.BO["d"] / 2, ub + g.BO["d"] / 2, "m-cr")
                C(xb, ub, g.BO["d"] / 2, "m-cr")
                C(xb, ub, g.BO["cbore_d"] / 2, "void")
                C(xb, ub, g.BO["hole_d"] / 2, "ln")
        for lug in (g.CLV["near"], g.CLV["far"]):
            R(lug[0], lug[1], g.LUG_U[0], g.LUG_U[1], "m-cr")
        v.line(X(g.CLV["near"][0]) , g.LEGP[0], X(g.CLV["far"][1]), g.LEGP[0], cls="cl")
        for b_ in g.CLIPD["xr_bodies"]:
            R(b_[0], b_[1], g.CLIPD["u"][0], g.CLIPD["u"][1], "m-cr")
            hk = [b_[0] - g.CLIPD["catch"], b_[0]] if b_[0] > 0 else [b_[1], b_[1] + g.CLIPD["catch"]]
            R(hk[0], hk[1], g.CLIPD["u"][0], g.CLIPD["u"][1], "m-cr")
        gr = g.GR
        R(gr["xr"][0], gr["xr"][1], g.U0, gr["u"][1], "void")
        nt = g.NOTCH
        R(nt["xr"][0], nt["xr"][1], nt["u"][0], nt["u"][1], "hid")        # notch only w-1..8: hidden from the back
        R(g.LG["xr"][0], g.LG["xr"][1], g.LEGP[0] - g.LEG_R, g.LG["stow_tip_u"], "leg-ph")


def sheet_t03():
    n = 3
    rows = []
    # ---------------- front view
    v = View(-100.0, -78.0, 128.0, 116.0, px_width=1000, pad_px=6)
    panel_title(v, -99.5, 113.5, "앞에서 본 모습 (유리 쪽, 화면 없이) — xr 오른쪽, u 위", size_px=12)
    cr_front(v)
    v.line(0.0, g.EAR_U[0] - 3, 0.0, g.U1 + 3, cls="cl")
    v.line(-g.XR1 - 3, g.GH / 2, g.XR1 + 3, g.GH / 2, cls="cl")
    xf = [(-g.XR1, g.U0, "바깥"), (-g.XIN, g.BOT_IN, "안"), (g.BO["xr"][0], g.BO["u"][0], "보스"), (g.HG["left"]["ear"][0], g.EAR_U[0], "귀"),
          (g.HG["left"]["ear"][1], g.EAR_U[0], ""), (0.0, g.U0, "가운데"), (g.INSP["xr"][0], g.INSP["u"][0], "창"), (g.HP["xr"][0], g.HP["u"][0], "누름 패드"),
          (g.HP["xr"][1], g.HP["u"][0], ""), (g.INSP["xr"][1], g.INSP["u"][0], "창"), (g.NOTCH["xr"][0], g.U0, "아래 벽 홈"), (g.NOTCH["xr"][1], g.U0, ""),
          (g.HG["right"]["ear"][0], g.EAR_U[0], "귀"),
          (g.HG["right"]["ear"][1], g.EAR_U[0], ""), (g.BO["xr"][1], g.BO["u"][0], "보스"), (g.XIN, g.BOT_IN, "안"), (g.XR1, g.U0, "바깥")]
    ordy(v, xf, g.EAR_U[0] - 4.0, gap_px=12.5, label_px=9, prefix="xr")
    uf = [(g.EAR_U[0], g.HG["right"]["ear"][1], "귀 아래 끝"), (g.UA, g.HG["right"]["ear"][1], f"경첩 축 {g.TOL['axis_pos']}"), (g.U0, g.XR1, "바깥 아래"),
          (g.BOT_IN, g.XIN, f"유리 받침 {g.TOL['glass_seat']}"), (g.BO["u"][0], g.BO["xr"][1], "보스"), (g.HP["u"][0], g.HP["xr"][1], "누름 패드"),
          (g.HP["u"][1], g.HP["xr"][1], ""), (g.INSP["u"][0], g.INSP["xr"][1], "창"), (g.GH / 2, g.XR1, "유리 가운데"), (g.INSP["u"][1], g.INSP["xr"][1], "창"),
          (g.BO["u"][1], g.BO["xr"][1], "보스"), (g.GH, g.GX, "유리 위"), (g.TOP_IN, g.XIN, "안 위"), (g.U1, g.XR1, "바깥 위")]
    ordz(v, uf, g.XR1 + 6.0, gap_px=12.5, label_px=9, prefix="u")
    v.dim_h(-g.XR1, g.XR1, g.U1 + 6.0, text=f"{F(g.CR['size'][0])} (x{FR(*g.CR['x'])})", ext_from=(g.U1, g.U1), size_px=10)
    v.dim_h(-g.XIN, g.XIN, g.U1 + 1.8, text=f"{F(2 * g.XIN)} = 유리 {F(g.S['glass'][0])} + 틈 {F(g.CLR)}×2", ext_from=(g.TOP_IN, g.TOP_IN), size_px=9.5)
    v.dim_h(g.BO["xr"][0], g.BO["xr"][1], g.BO["u"][1] - 8.0, text=f"{F(g.BO['xr'][1] - g.BO['xr'][0])} {g.TOL['boss_pitch']} (화면 구멍)", ext_from=(g.BO["u"][1], g.BO["u"][1]), size_px=9.5)
    v.dim_v(g.BO["u"][0], g.BO["u"][1], g.BO["xr"][0] + 9.0, text=f"{F(g.BO['u'][1] - g.BO['u'][0])} {g.TOL['boss_pitch']}", ext_from=(g.BO["xr"][0], g.BO["xr"][0]), size_px=9.5)
    v.dim_v(g.U0, g.U1, -g.XR1 - 6.0, text=f"{F(g.CR['size'][1])}", ext_from=(-g.XR1, -g.XR1), size_px=10)
    fitems = [
        ("a", (g.BO["xr"][0] - g.BO["d"] / 2 * 0.7, g.BO["u"][0] + g.BO["d"] / 2 * 0.7), (16, 16), f"보스 Ø{F(g.BO['d'])} ×4 (옆벽까지 채움), 구멍 Ø{F(g.BO['hole_d'])}, 화면 뒷면 w{F(g.BO['face_w'])}에 닿음 {g.TOL['boss_face']}"),
        ("b", (g.HP["xr"][0], g.HP["u"][1]), (-14, 14), f"리본 누름 패드 w{FR(*g.HP['w'])} (뒷판 안면, 리본 + 틈 {F(g.HP['w'][0] - g.GB - g.RB['ffc_t'])})"),
        ("c", (g.INSP["xr"][0], g.INSP["u"][1]), (-16, 10), f"점검창 {F(g.INSP['xr'][1] - g.INSP['xr'][0])}×{F(g.INSP['u'][1] - g.INSP['u'][0])} (뒷판 관통, 덮개 T5)"),
        ("d", (-40.0, 70.0), (0, 18), f"뒷판 안면 w{F(g.PL_IN)}: 화면 뒷면과 {F(g.PL_IN - g.GB)} 틈 = 리본·전원선 길"),
        ("e", (g.ACT_XR[0], g.ACT_U[1] - 10), (18, -14), f"점선 = 유리 {F(g.S['glass'][0])}×{F(g.S['glass'][1])} · 보이는 영역 {F(g.S['active'][0])}×{F(g.S['active'][1])}"),
        ("f", ((g.GR["xr"][0] + g.GR["xr"][1]) / 2, 1.5), (0, 16), f"아래 홈 xr{FR(*g.GR['xr'])} (뒤쪽 w{FR(*g.GR['w'])}, 숨은 선)"),
        ("g", (g.EAR_R[1], (g.U0 + g.EAR_U[0]) / 2), (16, 0), f"경첩 귀 (받침 아래) xr{FR(*g.EAR_L)} · {FR(*g.EAR_R)}"),
        ("h", (-g.XR1, 50.0), (-12, 16), f"테 (옆벽 {F(g.RIM)}·아래 {F(g.BOT_T)}·위 {F(g.RIM)}), 유리보다 {F(-g.W0)} 앞"),
        ("i", ((g.NOTCH["xr"][0] + g.NOTCH["xr"][1]) / 2, (g.NOTCH["u"][0] + g.NOTCH["u"][1]) / 2), (-10, 26),
         f"【3a】 아래 벽 홈 xr{FR(*g.NOTCH['xr'])} (x{FR(g.XC + g.NOTCH['xr'][0], g.XC + g.NOTCH['xr'][1])}) 관통, w{FR(*g.NOTCH['w'])} — 화면 아래 끝 돌기 자리 (상세 H)"),
    ]
    K.callouts2(v, fitems, [-98.0, 12.0], -46.0, line_px=14.5, size_px=9.4)
    v.v0 = -78.0
    scalebar(v, 90.0, 110.0, 20)
    info = panel_t03_info()
    rows.append([v, info])
    # ---------------- back view (mirrored)
    b = View(-100.0, -102.0, 128.0, 116.0, px_width=1000, pad_px=6)
    Xb = lambda x: -x                                     # the mirror of cr_front(mirror=True)
    left_is = "+x" if Xb(1.0) < 0 else "−x"
    panel_title(b, -99.5, 113.5, f"뒤에서 본 모습 (리브 쪽, 좌우 반전: 왼쪽이 {left_is}) — 점선 = 창으로 보이는 화면 부품·선 (추정)", size_px=12)
    cr_front(b, mirror=True, back=True)
    b.line(0.0, g.EAR_U[0] - 3, 0.0, g.U1 + 3, cls="cl")
    xb_ = [(-g.XR1, g.U0, ""), (-g.CHW["xr_walls"][1][1], g.CHW["u"][0], "길 벽"), (-g.CHW["xr_walls"][1][0], g.CHW["u"][0], ""),
           (-g.CLV["far"][1], g.LUG_U[0], "먼 볼"), (-g.CLIPD["xr_bodies"][1][1], g.CLIPD["u"][0], "클립"),
           (-g.WRIB_OUT[0], g.WRIB_OUT[2], "창 리브"), (-g.WRIB_OUT[1], g.WRIB_OUT[2], ""), (-g.GR["xr"][0], g.U0, "홈"), (-g.GR["xr"][1], g.U0, ""),
           (-g.PADS[2]["xr"][0], g.PADS[2]["u"][0], "패드"), (-g.PADS[2]["xr"][1], g.PADS[2]["u"][0], ""),
           (-g.CLV["near"][0], g.LUG_U[0], "가까운 볼"), (-g.PADS[0]["xr"][0], g.PADS[0]["u"][0], "패드"), (-g.PADS[0]["xr"][1], g.PADS[0]["u"][0], ""),
           (g.XR1, g.U0, "")]
    ordy(b, xb_, g.EAR_U[0] - 4.0, gap_px=12.5, label_px=9, prefix="−xr ")
    ub_ = [(g.U0 + g.CH, g.XR1, f"C{F(g.CH)} 모따기 끝"), (g.PADS[0]["u"][0], g.PADS[0]["xr"][0], "패드"), (g.CHW["u"][0], 7.3, "다리 길·걸이"),
           (g.XRIB[0] - g.RIB_T / 2, g.XR1, "가로 리브"), (g.XRIB[0] + g.RIB_T / 2, g.XR1, ""), (g.LEGP[0], 0.0, "다리 축"), (g.PADS[0]["u"][1], g.PADS[0]["xr"][0], ""),
           (g.LUG_U[1], 0.0, "걸이 끝"), (g.WRIB_OUT[3], g.WRIB_OUT[0], "창 리브"), (g.PADS[1]["u"][0], g.PADS[1]["xr"][0], "패드"),
           (g.XRIB[1] - g.RIB_T / 2, g.XR1, "가로 리브"), (g.XRIB[1] + g.RIB_T / 2, g.XR1, ""), (g.PADS[1]["u"][1], g.PADS[1]["xr"][0], ""),
           (g.CLIPD["u"][0], g.CLIPD["xr_bodies"][0][0], "클립"), (g.CLIPD["u"][1], g.CLIPD["xr_bodies"][0][0], ""), (g.LG["stow_tip_u"], 0.0, "접은 다리 끝")]
    ordz(b, ub_, g.XR1 + 6.0, gap_px=12.5, label_px=9, prefix="u")
    for xr_, lab_ in ((60.0, "+x"), (-60.0, "−x")):
        T(b, Xb(xr_), g.U1 + 3.0, lab_, size_px=11, anchor="middle")
    # the ordinates of this view print −xr (value at drawing u = Xb(xr)); the window (+xr side) must come out on the '+x' side
    g.check("t03 back view (mirrored): '+x' marker on the side the title names, window (+xr) on that side, ordinate −xr = drawing u",
            (Xb(60.0) < 0) == (left_is == "+x") and Xb(sum(g.INSP["xr"]) / 2) < 0 and abs(Xb(g.INSP["xr"][0]) - (-g.INSP["xr"][0])) < 1e-9,
            f"+x at u{Xb(60.0):g}, window at u{Xb(sum(g.INSP['xr']) / 2):g}")
    bitems = [
        ("A", (-g.S["fpc"]["xr"][1], g.S["fpc"]["u"][1]), (-10, 16), f"DSI ZIF 22핀 0.5 xr{FR(*g.S['fpc']['xr'])} u{FR(*g.S['fpc']['u'])}, 입구 +x (추정 ±0.5)"),
        ("B", (-g.S["pwr"]["xr"][1], g.S["pwr"]["u"][1]), (-10, 16), f"MX1.25 2핀 xr{FR(*g.S['pwr']['xr'])} u{FR(*g.S['pwr']['u'])}, 입구 +x (추정)"),
        ("C", (-g.FSQ["xr"][1], g.FSQ["u"][0]), (-16, -12), f"리본 45° 접기 R{F(g.RB['fold_roll_R'])} xr{FR(*g.FSQ['xr'])} u{FR(*g.FSQ['u'])} → −u로 내려감 (주황 점선)"),
        ("D", (-sum(g.CR["wire_xr"]) / 2, 20.0), (-18, 0), f"전원선 길 xr{FR(*g.CR['wire_xr'])} (분홍)"),
        ("E", (-g.BO["xr"][1] - g.BO["cbore_d"] / 2, g.BO["u"][1]), (-6, -18), f"자리파기 Ø{F(g.BO['cbore_d'])} → 머리 자리 w{F(g.BO['seat_w'])} (M2.5×6 물림 {F(g.BO['engage'])})"),
        ("F", (0.0, 64.0), (14, 8), f"접은 다리 (보라 점선) u{FR(g.LEGP[0] - g.LEG_R, g.LG['stow_tip_u'])}, w{FR(g.LEGP[1] - g.LEG_T / 2, g.LEGP[1] + g.LEG_T / 2)}"),
        ("G", (-(g.PADS[0]["xr"][0] + g.PADS[0]["xr"][1]) / 2, g.PADS[0]["u"][1]), (12, 12), f"뒤 패드 {F(g.PADS[0]['xr'][1] - g.PADS[0]['xr'][0])}×{F(g.PADS[0]['u'][1] - g.PADS[0]['u'][0])} ×{len(g.PADS)} (w{FR(g.RIB0, g.RIB1)}) — 접으면 받침 발 위"),
        ("H", (-g.EAR_L[1], g.EAR_U[0] + 2), (16, 0), f"경첩 귀 두께 {F(g.EAR_L[1] - g.EAR_L[0])}, 축 구멍 Ø{F(g.KN_NEAR_HOLE)} (u{F(g.UA)} w{F(g.WA)})"),
        ("I", (-g.CLV["near"][0], g.LUG_U[0]), (14, -12), f"다리 걸이: 가까운 볼 xr{FR(*g.CLV['near'])} Ø{F(g.LEG_HOLE)} · 먼 볼 xr{FR(*g.CLV['far'])} Ø{F(g.FAR_HOLE)}"),
        ("J", (-g.CLIPD["xr_bodies"][1][1], g.CLIPD["u"][1]), (-10, 14), f"다리 클립 u{FR(*g.CLIPD['u'])}, 몸 xr ±{FR(*g.CLIPD['xr_bodies'][1])}, 턱 {F(g.CLIPD['catch'])}"),
        ("K", (-g.CHW["xr_walls"][1][1], 96.0), (-14, 6), f"다리 길 벽 xr ±{FR(*g.CHW['xr_walls'][1])}, u{FR(*g.CHW['u'])}"),
        ("L", (-g.WRIB_OUT[0], g.WRIB_OUT[3]), (12, 12), f"창 둘레 리브 (창보다 {F(g.WIN_RIB_OFF)} 밖, 두께 {F(g.RIB_T)}) — 덮개 턱 자리"),
        ("M", (-60.0, g.XRIB[1]), (0, 14), f"가로 리브 u{F(g.XRIB[0])}·u{F(g.XRIB[1])} (두께 {F(g.RIB_T)}, 다리 길에서 끊김) — 【3a】 아래 리브는 다리 축 줄 u{F(g.LEGP[0])}에서 비킴"),
        ("N", (-(g.GR["xr"][0] + g.GR["xr"][1]) / 2, g.U0), (0, 14), f"아래 홈 (아래·뒤 트임): 선을 뒤에서 넣고 뺌"),
        ("O", (60.0, g.U0 + g.CH), (0, -14), f"C{F(g.CH)} 모따기 (아래 뒤 모서리 전체)"),
    ]
    K.callouts2(b, bitems, [-98.0, 12.0], -46.0, line_px=14.5, size_px=9.4)
    b.v0 = -102.0
    scalebar(b, 90.0, 110.0, 20)
    rows.append([b, panel_t03_uplanes()])
    # ---------------- sections along w
    rows.append([sec_panel("B–B", g.CLV["near"][0] + 3.0, "다리 걸이 · 다리 길 · 클립"), sec_panel("C–C", (g.EAR_L[0] + g.EAR_L[1]) / 2, "경첩 귀 (3a 윤곽) · 패드 · 가로 리브"),
                 sec_panel("D–D", (g.GR["xr"][0] + g.GR["xr"][1]) / 2, "아래 홈 · 누름 패드 · 점검창"), sec_panel("E–E", g.BO["xr"][1], "보스 · M2.5×6")])
    base = os.path.join(OUT, "t03_cradle_part")
    K.page(rows, base, sub_head(n, "화면 받침 (크래들) 부품도 — PETG 출력 1개"),
           subtitle=SRC_LINE + f"\n받침 {F(g.CR['size'][0])}×{F(g.CR['size'][1])}×{F(g.CR['size'][2])}, 화면 Waveshare 7-DSI-TOUCH-C를 뒤에서 M2.5×6 ×4로 고정. 단면 위치는 앞·뒤 그림의 xr 값.",
           foot=foot_lines())
    uc_ = (g.CLIPD["u"][0] + g.CLIPD["u"][1]) / 2
    add_sheet(n, os.path.basename(base), "화면 받침 부품도",
              f"받침 {F(g.CR['size'][0])}×{F(g.CR['size'][1])}×{F(g.CR['size'][2])} 앞·뒤 모습(테·벽 안쪽 면 u{F(g.BOT_IN)}/u{F(g.TOP_IN)}, 보스·자리파기, 점검창, 가로 리브 u{F(g.XRIB[0])}·u{F(g.XRIB[1])}, "
              f"패드, 경첩 귀·축 구멍, 다리 걸이·클립, 아래 홈, 아래 벽 홈 xr{FR(*g.NOTCH['xr'])}), 뒤 모습 ±x 표시 고침, "
              f"가로 단면 F–F u{F(g.LEGP[0])}(다리 걸이 + M3×20 ISO 7380, 머리·넣는 길 둘레 {F(g.AXLE_GAP['head'][0])}) · G–G u{F(uc_)}(클립), "
              f"세로 단면 B–B(걸이·길·클립) C–C(귀 3a 윤곽·패드) D–D(홈·누름 패드·창) E–E(보스·나사), 상세 H(아래 벽 홈), 출력 높이 {F(g.PRINT_H_CRADLE)}.")


def panel_t03_info():
    v = View(0.0, 0.0, 50.0, 93.0, px_width=470, pad_px=6)
    panel_title(v, 0.5, 91.3, "요점 · 공차 · 출력", size_px=12)
    st = g.STUD
    lines = [
        f"• 바깥 {F(g.CR['size'][0])}×{F(g.CR['size'][1])}×{F(g.CR['size'][2])}: xr{FR(g.XR0, g.XR1)}, u{FR(g.U0, g.U1)}, w{FR(g.W0, g.W1)}",
        f"• 옆벽 {F(g.RIM)}, 유리와 틈 {F(g.CLR)} · 아래 벽 {F(g.BOT_T)}: 안쪽 면 u{F(g.BOT_IN)}에 유리가 얹힘",
        f"• 위 벽 {F(g.RIM)} (안쪽 u{F(g.TOP_IN)}, 유리 위와 {F(g.TOP_GAP)}) · 앞 테: 유리보다 {F(-g.W0)} 앞 (w{F(g.W0)})",
        f"• 뒷판 w{FR(g.PL_IN, g.PL_OUT)} ({F(g.PL_OUT - g.PL_IN)}), 리브 w{FR(g.RIB0, g.RIB1)} 두께 {F(g.RIB_T)}",
        f"• 볼록판(화면 뒤, 높이 약 {F(g.S['emboss']['h'])})과 뒷판 틈 {F(g.CR['emboss_clearance'])}",
        f"• 보스 Ø{F(g.BO['d'])} ×4 xr ±{F(g.BO['xr'][1])} u{F(g.BO['u'][0])}·{F(g.BO['u'][1])} ({F(g.BO['xr'][1] - g.BO['xr'][0])}×{F(g.BO['u'][1] - g.BO['u'][0])} {g.TOL['boss_pitch']}), 옆벽까지 채움",
        f"\u00a0\u00a0\u00a0구멍 Ø{F(g.BO['hole_d'])} w{FR(g.BO['face_w'], g.BO['seat_w'])}, 자리파기 Ø{F(g.BO['cbore_d'])} w{FR(g.BO['seat_w'], g.RIB1)}",
        f"\u00a0\u00a0\u00a0M2.5×6: 물림 {F(g.BO['engage'])} = min(구멍 깊이 − 0.5, 4), 최소 2 (깊이 모름)",
        f"• 경첩 귀 xr{FR(*g.EAR_L)} · {FR(*g.EAR_R)} (두께 {F(g.EAR_L[1] - g.EAR_L[0])})",
        f"\u00a0\u00a0\u00a0축 u{F(g.UA)} w{F(g.WA)} {g.TOL['axis_pos']}, 구멍 Ø{F(g.KN_NEAR_HOLE)} {g.TOL['hole_axle']}, 축살 R{F(g.HG['ear_hub_R'])}",
        f"\u00a0\u00a0\u00a0윤곽(3a) = 축살 + 받침 아래 + 뒤꿈치 (u{F(g.HEEL_TIP_LOCAL[0])}, w{F(g.HEEL_TIP_LOCAL[1])}) 하나, C–C",
        f"\u00a0\u00a0\u00a0뒤꿈치 R{F(g.HG['heel_R'])}: {F(g.TH_HEEL)}°에서 world (y{F(g.HG['heel_contact_yz'][0])}, z{F(g.HG['heel_contact_yz'][1])}), 모서리 R0.3 이하",
        f"• 다리 걸이 축 u{F(g.LEGP[0])} w{F(g.LEGP[1])}: 가까운 볼 xr{FR(*g.CLV['near'])} Ø{F(g.LEG_HOLE)} 관통",
        f"\u00a0\u00a0\u00a0먼 볼 xr{FR(*g.CLV['far'])} Ø{F(g.FAR_HOLE)} × {F(g.FAR_HOLE_DEPTH)} (M3×20 물림 {F(g.FAR_ENGAGE)})",
        f"\u00a0\u00a0\u00a0볼 R{F(g.CLV['R'])}, +u 쪽 45° 모따기 · 축 나사 ISO 7380 −x에서 (F–F)",
        f"• 다리 클립 u{FR(*g.CLIPD['u'])}: 몸 xr ±{FR(g.CLIPD['xr_bodies'][1][0], g.CLIPD['xr_bodies'][1][1])}",
        f"\u00a0\u00a0\u00a0턱 {F(g.CLIPD['catch'])} (다리 위 {F(g.CLIPD['over_leg'])}), w{FR(g.CLIPD['catch_from_w'], g.CLIPD['back_w'])}",
        f"• C{F(g.CH)} 모따기 (아래 뒤 모서리): 뚜껑 볼과 {F(g.CR['rib_relief_at_cheeks']['gap_after'])}",
        f"• 점검창 xr{FR(*g.INSP['xr'])} u{FR(*g.INSP['u'])}, 둘레 리브 {F(g.WIN_RIB_OFF)} 밖",
        f"• 아래 홈 xr{FR(*g.GR['xr'])} u{FR(*g.GR['u'])} w{FR(*g.GR['w'])} (아래·뒤 트임)",
        f"• 누름 패드 xr{FR(*g.HP['xr'])} u{FR(*g.HP['u'])} w{FR(*g.HP['w'])} + 캡톤",
        f"• 스터드가 박혀 있으면(G-2): 보스를 Ø{F(st['bore_d'])}로 w{FR(*st['bore_w'])} 파고 보스 Ø{F(st['boss_d'])},",
        f"\u00a0\u00a0\u00a0뒤에서 M2.5×6 (물림 {F(st['engage'])}, 머리 {F(st['head_out'])} 나옴) — 뒷판·축 그대로",
        f"출력: 윗변(u{F(g.U1)} 면)을 베드에 세움, 높이 {F(g.PRINT_H_CRADLE)} (= u{F(g.U1)} − 뒤꿈치 u{F(g.EAR_U[0])})",
        f"약 {F(g.N['mass_est']['cradle_g'], 0)} g · 약 {F(g.N['mass_est']['cradle_h'], 1)}시간 (추정) · PETG · 구멍은 물방울 모양으로 뽑고 드릴",
        f"일반 공차 {g.TOL['general']} · 추정값: 커넥터 ±0.5, 볼록판 높이, 아래 끝 돌기 위치",
    ]
    note_lines(v, lines, 0.5, 88.0, line_px=14.2, size_px=9.2, cls="lt")
    detail_notch(v, 0.0, 0.5)
    return v


def detail_notch(v, ox, oy, k=2.0):
    """detail H in the info panel at scale k:1 (the numbers written are true mm): top = front view of the bottom edge around the
    notch, bottom = section H-H through the notch centre (w to the right, u up)."""
    nt = g.NOTCH
    xa, xb = nt["xr"][0] - 2.0, nt["xr"][1] + 2.0
    ua, ub = -4.0, 3.0
    fx = lambda xr: ox + 3.0 + k * (xr - xa)
    fu = lambda u: oy + 26.0 + k * (u - ua)
    panel_title(v, ox + 0.5, fu(ub) + 6.0, f"상세 H — 아래 벽 홈 【3a】 배율 {F(k)}:1 (위: 앞에서 · 아래: H–H 단면 xr{F(sum(nt['xr']) / 2)})", size_px=10.5)
    i0 = len(v.el)
    R = lambda x0, x1, u0, u1, cls: v.rect(fx(x0), fu(u0), k * (x1 - x0), k * (u1 - u0), cls=cls)
    R(xa - 2, xb + 2, g.U0, g.BOT_IN, "m-cr")                  # bottom wall
    R(nt["xr"][0], nt["xr"][1], nt["u"][0], nt["u"][1], "m-sbar")   # notch: the w8..16 part of the wall seen behind
    R(nt["xr"][0], nt["xr"][1], nt["u"][0], nt["u"][1], "vis")
    e = g.EAR_R
    R(e[0], e[1], ua - 2, g.U0, "m-cr")                        # right ear (below the wall)
    R(xa - 2, xb + 2, 0.0, ub + 2, "ph2")                      # glass (phantom)
    R(nt["feature_xr"][0], nt["feature_xr"][1], -nt["feature_proud"], 0.0, "conn")    # bottom-edge feature (estimate)
    clip_scene(v, i0, fx(xa), fx(xb), fu(ua), fu(ub))
    v.dim_h(fx(nt["xr"][0]), fx(nt["xr"][1]), fu(ub) + 2.0, text=f"{F(nt['xr'][1] - nt['xr'][0])} (xr{FR(*nt['xr'])}, x{FR(g.XC + nt['xr'][0], g.XC + nt['xr'][1])})",
            ext_from=(fu(g.BOT_IN), fu(g.BOT_IN)), size_px=9)
    v.dim_h(fx(nt["xr"][0]), fx(nt["feature_xr"][0]), fu(ua) - 1.5, text=F(g.N["checks"]["notch_margin"][0]), ext_from=(fu(g.U0), fu(-nt["feature_proud"])), size_px=8.8)
    v.dim_h(fx(nt["feature_xr"][1]), fx(nt["xr"][1]), fu(ua) - 1.5, text=F(g.N["checks"]["notch_margin"][1]), ext_from=(fu(-nt["feature_proud"]), fu(g.U0)), size_px=8.8)
    v.dim_v(fu(nt["u"][0]), fu(nt["u"][1]), fx(xa) - 0.6, text=F(nt["u"][1] - nt["u"][0]), ext_from=(fx(xa), fx(xa)), size_px=8.8, tpos="left")
    T(v, fx(sum(nt["feature_xr"]) / 2), fu(-nt["feature_proud"]) - 3.0, f"돌기 xr{FR(*nt['feature_xr'])}, {F(nt['feature_proud'])} 나옴 (추정)", size_px=8.6, anchor="middle", halo=True)
    T(v, fx(e[0]) + 1.0, fu(ua) + 1.0, "귀", size_px=8.6, anchor="start", halo=True)
    T(v, fx(xa) + 1.0, fu(ub) - 2.4, "유리 (점선)", size_px=8.6, anchor="start", cls="tx-s", halo=True)
    # section H-H at the notch centre (w -> right, u -> up)
    xs = sum(nt["xr"]) / 2
    sx = lambda w: ox + 8.0 + k * (w - g.W0)
    su = lambda u: oy + 3.5 + k * (u - ua)
    j0 = len(v.el)
    adds, subs = g.cradle_section(xs)
    tr = lambda poly: [(sx(w), su(u)) for (u, w) in poly]
    pid = K.pid_set(v)
    K.rings_h(v, [tr(q) for q in adds], "m-cr", pid["cr"], subs=[tr(q) for q in subs])
    for q in g.screen_section(xs):
        v.poly(tr(q), cls="ph2")
    v.poly(tr(g.rect(-nt["feature_proud"], 0.0, 0.0, g.GB)), cls="conn")
    clip_scene(v, j0, sx(g.W0 - 1.0), sx(g.W1 + 1.0), su(ua), su(ub))
    v.dim_h(sx(nt["w"][0]), sx(nt["w"][1]), su(ub) + 2.0, text=f"홈 w{FR(*nt['w'])}", ext_from=(su(g.BOT_IN), su(g.BOT_IN)), size_px=8.8)
    v.dim_h(sx(nt["w"][1]), sx(g.W1), su(ub) + 2.0, text=f"남는 벽 w{FR(nt['w'][1], g.W1)}", ext_from=(su(g.BOT_IN), su(g.BOT_IN)), size_px=8.8)
    T(v, sx(g.W1 + 1.0) + 1.0, su(ua) + 3.0, "H–H", size_px=10, anchor="start", cls="ttl")
    T(v, ox + 0.5, su(ua) - 2.6, "유리는 홈 양옆 아래 벽에 얹힘 · 받으면 돌기 자리·높이 확인 (G-7), 밖이면 홈을 옮김", size_px=8.6, anchor="start", cls="tx-s")
    frame_check("t03 detail H", (fx(xa), fx(xb), fu(ua), fu(ub)), (fx(nt["xr"][0]), fx(nt["xr"][1]), fu(nt["u"][0]), fu(nt["u"][1])))


def panel_t03_uplanes():
    """two cross-sections in the (xr, w) plane (w up = backward): F-F at the leg pivot u30 (clevis + axle), G-G at u90 (leg clip)."""
    v = View(-17.0, -61.0, 30.0, 34.0, px_width=470, pad_px=6)
    pid = K.pid_set(v)

    def draw(u0, dz, title):
        panel_title(v, -16.5, dz + 31.5, title, size_px=11)
        adds, subs = g.cradle_section_u(u0)
        adds = [q for q in adds if min(p_[0] for p_ in q) < 16 and max(p_[0] for p_ in q) > -16]
        sh = lambda poly: [(max(-16.0, min(16.0, x)), w + dz) for (x, w) in poly]
        K.rings_h(v, [sh(q) for q in adds], "m-cr", pid["cr"], subs=[sh(q) for q in subs])
        v.rect(-16.0, dz, 32.0, g.GB, cls="ph2")
        lw = (g.LEGP[1] - g.LEG_T / 2, g.LEGP[1] + g.LEG_T / 2)
        hole = [sh(g.rect(g.LG["xr"][0] - 0.1, g.LG["xr"][1] + 0.1, g.LEGP[1] - g.LEG_HOLE / 2, g.LEGP[1] + g.LEG_HOLE / 2))] if abs(u0 - g.LEGP[0]) < 1e-6 else []
        K.rings_h(v, [sh(g.rect(g.LG["xr"][0], g.LG["xr"][1], lw[0], lw[1]))], "m-leg", pid["leg"], subs=hole)
        for xe in (-16.0, 16.0):
            v.poly([(xe, dz + g.PL_IN - 0.6), (xe + 0.6, dz + (g.PL_IN + g.RIB1) / 2), (xe - 0.6, dz + (g.PL_IN + g.RIB1) / 2 + 0.8), (xe, dz + g.RIB1 + 0.6)], cls="vis", closed=False)
        return dz

    dz = draw(g.LEGP[0], 0.0, f"F–F (u{F(g.LEGP[0])}): 다리 걸이 + M3×20 축 (ISO 7380)")
    wp = g.LEGP[1] + dz
    x0, x1 = g.CLV["near"][0], g.CLV["near"][0] + g.AXLE_L
    v.rect(x0, wp - 1.5, x1 - x0, 3.0, cls="m-steel")
    v.rect(x0 - g.AX_HEAD["h"], wp - g.AX_HEAD["d"] / 2, g.AX_HEAD["h"], g.AX_HEAD["d"], cls="m-steel")
    # the screw on its way in from -x (head swept), clipped at the panel edge
    v.rect(-16.0, wp - g.AX_HEAD["d"] / 2, x0 - g.AX_HEAD["h"] - (-16.0), g.AX_HEAD["d"], cls="cr-ph")
    top = g.LUG_W[1] + dz
    v.dim_h(g.CLV["near"][0], g.CLV["near"][1], top + 2.5, text=f"{F(g.CLV['near'][1] - g.CLV['near'][0])}", ext_from=(top, top), size_px=9)
    v.dim_h(g.CLV["far"][0], g.CLV["far"][1], top + 2.5, text=f"{F(g.CLV['far'][1] - g.CLV['far'][0])}", ext_from=(top, top), size_px=9)
    v.dim_h(g.LG["xr"][0], g.LG["xr"][1], top + 6.5, text=f"다리 {F(g.LG['xr'][1] - g.LG['xr'][0])} (양쪽 틈 {F(g.CLV['far'][0] - g.LG['xr'][1])})", ext_from=(wp + 3, wp + 3), size_px=9)
    T(v, -16.5, dz - 3.5, f"축 {F(g.AXLE_L)}: 머리 Ø{F(g.AX_HEAD['d'])}×{F(g.AX_HEAD['h'])} xr{F(x0)} → 끝 xr{F(x1)}, 먼 볼 물림 {F(g.FAR_ENGAGE)}", size_px=9)
    T(v, -16.5, dz - 7.0, f"−x에서 넣음 (파랑 점선 = 넣는 길 xr{F(x0 - g.AXLE_L - g.AX_HEAD['h'])}~{F(x0)}), L렌치 2.0", size_px=9, cls="tx-s")
    T(v, -16.5, dz - 10.5, f"머리·넣는 길과 리브·패드·보스 {F(g.AXLE_GAP['head'][0])} 이상 ({g.AXLE_GAP['head'][1]}), 뒷판 위 {F(g.AXLE_GAP_PLATE[0])}", size_px=9, cls="tx-s")
    T(v, -16.5, dz - 14.0, f"위 = 뒤(+w) · 아래 점선 = 화면 (w0~{F(g.GB)})", size_px=9, cls="tx-s")
    uc = (g.CLIPD["u"][0] + g.CLIPD["u"][1]) / 2
    dz = draw(uc, -50.0, f"G–G (u{F(uc)}): 다리 클립 (접은 다리)")
    bw = g.CLIPD["back_w"] + dz
    xb = g.CLIPD["xr_bodies"][1]
    v.dim_h(-xb[0], xb[0], bw + 2.5, text=f"{F(2 * xb[0])}", ext_from=(bw, bw), size_px=9)
    v.dim_h(-(xb[0] - g.CLIPD["catch"]), xb[0] - g.CLIPD["catch"], bw + 6.5, text=f"{F(2 * (xb[0] - g.CLIPD['catch']))} (턱 {F(g.CLIPD['catch'])})", ext_from=(bw, bw), size_px=9)
    lwb = g.LEGP[1] + g.LEG_T / 2
    T(v, 9.5, g.CLIPD["catch_from_w"] + dz - 4.0, f"턱 w{F(g.CLIPD['catch_from_w'])} ↔ 다리 뒤 w{F(lwb)}: {F(g.CLIPD['catch_from_w'] - lwb)}", size_px=9)
    T(v, 9.5, g.CLIPD["catch_from_w"] + dz - 7.5, f"턱 두께 {F(g.CLIPD['hook_t'])} (w{F(g.CLIPD['back_w'])}까지)", size_px=9)
    T(v, -16.5, dz - 3.5, "다리를 눌러 끼움 (턱 끝 모따기는 CAD 재량)", size_px=9, cls="tx-s")
    scalebar(v, 18.0, -59.0, 5)
    return v


def sec_panel(tag, xr0, what):
    """section of the cradle at xr = xr0 in its own frame: w to the right (backward), u up."""
    v = View(-4.0, -24.0, 40.0, 110.0, px_width=368, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, -3.8, 108.0, f"{tag} (xr{F(xr0)})", size_px=11.5)
    T(v, -3.8, 104.0, what, size_px=9, cls="tx-s")
    # screen phantom (+ emboss)
    for p in g.screen_section(xr0):
        v.poly(sw(p), cls="ph2")
    v.line(0.0, 0.0, 0.0, g.GH, cls="glass")
    adds, subs = g.cradle_section(xr0)
    K.rings_h(v, [sw(p) for p in adds], "m-cr", pid["cr"], subs=[sw(p) for p in subs])
    feats_u, feats_w = [], []
    if tag.startswith("B"):
        lp = g.LEGP
        stow = [(w, u) for (u, w) in g.leg_outline((lp[0], lp[1]), (g.LG["stow_tip_u"] - g.LEG_R, lp[1]))]
        v.poly(stow, cls="leg-ph")
        v.circle(lp[1], lp[0], 1.5, cls="m-steel")
        feats_u = [(g.CHW["u"][0], g.RIB1, "길 벽 · 걸이"), (lp[0], lp[1] + g.CLV["R"], "다리 축"), (g.LUG_U[1], g.RIB0, "걸이 끝 (45°)"),
                   (g.CLIPD["u"][0], g.CLIPD["back_w"], "클립"), (g.CLIPD["u"][1], g.CLIPD["back_w"], "")]
        feats_w = [(g.RIB0, 0, "뒷판 뒤"), (g.RIB1, 0, "리브"), (lp[1], 0, "축"), (g.CLIPD["back_w"], 0, "클립 뒤")]
    elif tag.startswith("C"):
        v.circle(g.WA, g.UA, 1.5, cls="m-steel")
        h = g.HEEL_TIP_LOCAL
        tl, tb = g.EAR_TAN["lower"], g.EAR_TAN["back"]
        feats_u = [(h[0], h[1], "뒤꿈치"), (tl[0], tl[1], "접점"), (g.UA, g.WA, f"축 {g.TOL['axis_pos']}"), (tb[0], tb[1], "접점"),
                   (g.U0, g.W1, "받침 아래"),
                   (g.PADS[0]["u"][0], g.RIB1, "패드"), (g.PADS[0]["u"][1], g.RIB1, ""), (g.XRIB[0], g.RIB1, "가로 리브"), (g.PADS[1]["u"][0], g.RIB1, "패드"),
                   (g.XRIB[1], g.RIB1, "가로 리브"), (g.PADS[1]["u"][1], g.RIB1, "")]
        feats_w = [(g.W0, 0, "앞 테"), (g.GB, 0, "화면 뒤 = 귀 앞"), (h[1], 0, "뒤꿈치"), (g.WA, 0, "축"), (tl[1], 0, "접점"), (g.RIB1, 0, "리브"), (g.EAR_W[1], 0, "축살")]
        dim_al(v, (g.WA, g.UA), (h[1], h[0]), -12, f"R{F(g.HG['heel_R'])}", size_px=9)
    elif tag.startswith("D"):
        gw = (g.CR["w_screen_back"] + g.PL_IN) / 2
        v.poly([(gw, g.S["fpc"]["pin_u_centre"]), (gw, g.U0 - 2)], cls="rib", closed=False)
        v.circle(g.GB + g.RB["fold_roll_R"], g.S["fpc"]["pin_u_centre"], g.RB["fold_roll_R"], cls="rib-t")
        feats_u = [(g.U0, g.W0, "받침 아래"), (g.GR["u"][1], g.PL_OUT, "홈 위"), (g.HP["u"][0], g.HP["w"][0], "누름 패드"), (g.HP["u"][1], g.HP["w"][0], ""),
                   (g.WRIB_OUT[2], g.RIB1, "창 리브"), (g.INSP["u"][0], g.PL_OUT, "창"), (g.S["fpc"]["pin_u_centre"], gw, "리본 접기"), (g.INSP["u"][1], g.PL_OUT, "창"),
                   (g.WRIB_OUT[3], g.RIB1, "")]
        feats_w = [(g.GB, 0, "화면 뒤"), (g.HP["w"][0], 0, "패드"), (g.PL_IN, 0, "뒷판"), (g.RIB1, 0, "리브"), (g.COVER["dome"]["inner_to_w"], 0, "덮개 볼록")]
        T(v, -3.8, -20.5, f"주황 = 리본 (틈 w{FR(g.GB, g.PL_IN)}, 접기 R{F(g.RB['fold_roll_R'])})", size_px=9, cls="rbt")
    else:
        for ub in g.BO["u"]:
            hs = g.M25_HEAD
            v.rect(g.BO["seat_w"], ub - hs["d"] / 2, hs["h"], hs["d"], cls="m-steel")
            v.rect(g.BO["seat_w"] - g.M25_L, ub - 1.25, g.M25_L, 2.5, cls="m-steel")
        feats_u = [(g.U0, g.W1, "아래"), (g.BO["u"][0], g.RIB1, "보스"), (g.XRIB[0], g.RIB1, "가로 리브"), (g.XRIB[1], g.RIB1, "가로 리브"), (g.BO["u"][1], g.RIB1, "보스")]
        feats_w = [(g.W0, 0, "앞 테"), (g.BO["face_w"], 0, "보스 면"), (g.BO["seat_w"], 0, "머리 자리"), (g.BO["seat_w"] - g.M25_L, 0, "나사 끝"), (g.RIB1, 0, "리브")]
        T(v, -3.8, -20.5, f"M2.5×6 (점선 화면 안 물림 {F(g.BO['engage'])})", size_px=9)
    feats_u = sorted(set(feats_u + [(g.U1, g.W1, "위")]))
    ordz(v, [(u, w, lab) for (u, w, lab) in feats_u], 25.0, gap_px=12.0, label_px=8.8, prefix="u", lo=v.v0 + 2.0)
    ordy(v, [(w, g.U0 if tag[0] != "C" else g.EAR_U[0], lab) for (w, _, lab) in feats_w], (g.U0 if tag[0] != "C" else g.EAR_U[0]) - 3.0, gap_px=12.0, label_px=8.8, prefix="w")
    return v


# ================================================================ t04 CU lid (rev-3 additions)
def lid_sec(tag, x0, what, y0, y1, z0=None, z1=None, px=300, extra=None, geo_y1=None):
    z0 = g.LID["top_z"] - 23.85 if z0 is None else z0
    z1 = g.LID["top_z"] + 13.15 if z1 is None else z1
    v = View(y0, z0, y1, z1, px_width=px, pad_px=6)
    v.geo_y1 = y1 if geo_y1 is None else geo_y1          # geometry is cut here (room for ordinates on the right)
    pid = K.pid_set(v)
    panel_title(v, y0 + 0.3, z1 - 1.2, f"{tag} (x{F(x0)})", size_px=11)
    T(v, y0 + 0.3, z1 - 4.4, what, size_px=9, cls="tx-s", halo=True)
    adds, subs = lid_section_at(x0)
    adds = [q for q in adds if max(p_[0] for p_ in q) > y0 and min(p_[0] for p_ in q) < y1]
    clamp = lambda poly: [(max(y0 + 0.5, min(v.geo_y1 - 0.5, y)), z) for (y, z) in poly]
    K.rings_h(v, [clamp(q) for q in adds], "m-lid", pid["lid"], subs=[clamp(q) for q in subs])
    if extra:
        extra(v, pid)
    return v


def sheet_t04():
    n = 4
    L = g.LID
    rows = []
    # ---------------- plan (top) with callouts
    X0, X1, Y0, Y1 = L["x"][0] - 23.0, L["x"][1] + 51.0, L["y"][0] - 64.0, L["y"][1] + 8.5
    v = View(X0, Y0, X1, Y1, px_width=1480, pad_px=6)
    frame_check("t04 plan", (X0, X1, Y0, Y1), (L["x"][0], L["x"][1], L["y"][0], L["y"][1]))
    pid = K.pid_set(v)
    panel_title(v, X0 + 0.5, Y1 - 2.5, "위에서 본 모습 (윗면 z" + F(L["top_z"]) + f") — 수정 {g.REV}판에서 L2 뚜껑에 더하는 것", size_px=12)
    draw_lid_plan(v, pid, show_under=False, show_routes=False)
    for kn in (g.KNL, g.KNR):
        v.line(kn["all"][0] - 4, g.H[0], kn["all"][1] + 4, g.H[0], cls="cl")
    v.line(g.XC, L["y"][0] - 4, g.XC, L["y"][1] + 4, cls="cl")
    xf = [(L["x"][0], L["y"][0], "뚜껑"), (g.SCREWS[0][0], g.SCREWS[0][1], "나사"), (g.FEET[0]["x"][0], g.FEET[0]["y"][0], "발"), (g.KNL["near"][0], g.KP["base_y"][0], "경첩"),
          (g.FEET[0]["x"][1], g.FEET[0]["y"][0], ""), (g.KNL["far"][1], g.KP["base_y"][0], ""), (g.V["slots"][0][0], g.V["slots"][0][2], "통풍"), (g.V["slots"][0][1], g.V["slots"][0][2], ""),
          (g.PK["x"][0], g.PK["ramp_front_y"], "주머니"), (g.XC, L["y"][0], "가운데"), (g.PK["x"][1], g.PK["ramp_front_y"], ""), (g.V["slots"][1][0], g.V["slots"][1][2], "통풍"),
          (g.HO["x"][0], g.HO["y"][0], "구멍"), (g.HO["x"][1], g.HO["y"][0], ""), (g.V["slots"][1][1], g.V["slots"][1][2], ""), (g.KNR["far"][0], g.KP["base_y"][0], "경첩"),
          (g.FEET[2]["x"][0], g.FEET[2]["y"][0], "발"), (g.KNR["near"][1], g.KP["base_y"][0], ""), (g.FEET[2]["x"][1], g.FEET[2]["y"][0], ""),
          (g.SCREWS[1][0], g.SCREWS[1][1], "나사"), (L["x"][1], L["y"][0], "뚜껑")]
    ordy(v, xf, L["y"][0] - 8.0, gap_px=12.5, label_px=9, prefix="x")
    yfeat = [(L["y"][0], L["x"][1], "앞"), (g.KP["base_y"][0], g.KNR["all"][1], "볼 밑 앞"), (g.HEEL_STOP["y"][1], g.KNR["all"][1], "멈춤 블록 뒤"),
             (g.HO["y"][0], g.HO["x"][1], "구멍"), (g.H[0], g.KNR["all"][1], f"축 {g.TOL['axis_pos']}"), (g.HO["y"][1], g.HO["x"][1], ""),
             (g.KP["base_y"][1], g.KNR["all"][1], "볼 밑 뒤"), (g.PL["lid_screw"]["y"][0], g.SCREWS[1][0], "앞 나사"), (g.FEET[2]["y"][0], g.FEET[2]["x"][1], "앞 발"),
             (g.FEET[2]["y"][1], g.FEET[2]["x"][1], ""), (g.PK["ramp_front_y"], g.PK["x"][1], "경사 앞"), (g.PK["ramp_end_y"], g.PK["x"][1], "주머니 바닥"),
             (g.V["band_y"][0], g.V["slots"][1][1], "통풍"), (g.PK["back_wall_y"], g.PK["x"][1], "뒷벽"), (g.FEET[3]["y"][0], g.FEET[3]["x"][1], "뒤 발"),
             (g.FEET[3]["y"][1], g.FEET[3]["x"][1], ""), (g.PL["lid_screw"]["y"][1], g.SCREWS[3][0], "뒤 나사"), (g.FEET[3]["lip"]["y"][0], g.FEET[3]["x"][1], "턱"),
             (g.FEET[3]["lip"]["y"][1], g.FEET[3]["x"][1], ""), (g.V["band_y"][1], g.V["slots"][1][1], ""), (L["y"][1], L["x"][1], "뒤")]
    ordz(v, yfeat, L["x"][1] + 8.0, side="right", gap_px=12.3, label_px=9, prefix="y")
    v.dim_h(L["x"][0], L["x"][1], L["y"][1] + 4.0, text=f"{F(L['x'][1] - L['x'][0])}", ext_from=(L["y"][1], L["y"][1]), size_px=10)
    v.dim_v(L["y"][0], L["y"][1], L["x"][0] - 8.0, text=f"{F(L['y'][1] - L['y'][0])}", ext_from=(L["x"][0], L["x"][0]), size_px=10)
    v.dim_h(g.V["slots"][0][0], g.V["slots"][0][1], g.V["band_y"][1] + 3.0, text=f"{F(g.V['slot'][0])}", ext_from=(g.V["slots"][6][3], g.V["slots"][6][3]), size_px=9)
    tg = lambda k: g.spec_tag("A", k)
    items = [
        ("1", (g.KNL["near"][0], g.KP["base_y"][1]), (-18, 18), f"{tg(1)} 경첩 받침 2개 (한 몸): 볼 {F(g.KNL['near'][1] - g.KNL['near'][0])} + 귀 홈 {F(g.SLOT['left'][1] - g.SLOT['left'][0])} (귀 {F(g.KNL['ear'][1] - g.KNL['ear'][0])} + 틈 {F(g.KN_GAP)}×2) + 볼 {F(g.KNL['far'][1] - g.KNL['far'][0])} = {F(g.KNL['all'][1] - g.KNL['all'][0])}; 옆모양 R{F(g.KP['R'])} + 사다리꼴 (A–A)"),
        ("1a", ((g.SLOT["left"][0] + g.SLOT["left"][1]) / 2, g.HEEL_STOP["y"][0] + 1), (6, -22), f"【새로】 뒤꿈치 멈춤 블록: 귀 홈 바닥 +{F(g.HG['heel_stop_h'])} (z{F(g.HG['heel_stop_z'])}), y{FR(*g.HEEL_STOP['y'])} {g.TOL['heel_stop']} (A'–A')"),
        ("2", (g.HO["x"][1], g.HO["y"][1]), (16, 14), f"{tg(2)} 리본·전원선 구멍 {F(g.HO['x'][1] - g.HO['x'][0])}×{F(g.HO['y'][1] - g.HO['y'][0])} 관통, 위아래 모서리 R{F(g.HO['edge_R'])}, 둘레 벽 {F(g.HO['wall'])} (B–B)"),
        ("3", (g.PK["x"][1], g.PK["back_wall_y"]), (18, 12), f"{tg(3)} 받침다리 주머니: 30° 경사 + 바닥 z{F(g.PK['bottom_z'])} + 뒷벽 (위 모서리 C{F(g.LG['pocket_edge_C'])}) (C–C, 경사 틈 {F(g.PK['ramp_min_clear'])}) · 다리는 {F(g.TH_HEEL)}°에서 넣고 뺌"),
        ("4", (g.FEET[1]["x"][0], g.FEET[1]["lip"]["y"][1]), (-18, 12), f"{tg(4)} 접이 받침 발 {len(g.FEET)}개 {g.FEET_SZ}×{F(g.FO['feet_h'])} {g.TOL['fold_feet']}, 뒤 발 2개에 턱 (E–E)"),
        ("5", tuple(g.CL["pins"][1]), (18, -6), f"{tg(5)} 리본 클립 자리 (밑): 덩어리 z{FR(*g.CL['pad']['z'])}, 핀 구멍 Ø{F(g.PIN_HOLE[0])}×{F(g.PIN_HOLE[1])} 밑에서 (밑면 그림, B–B)"),
        ("6", (g.V["slots"][1][1], g.V["slots"][3][3]), (18, 0), f"{tg(6)} 통풍 슬롯 {len(g.V['slots'])}개 {F(g.V['slot'][0])}×{F(g.V['slot'][1])}, 판 관통, 간격 {F(g.V['pitch'])}"),
        ("7", g.SCREWS[0], (-16, -14), f"{tg(7)} 뚜껑 고정 M3×10 ×4 (L2 레일 인서트): x 추정 (뚜껑 끝 ±{F(g.PL['lid_screw']['inset_x'])}), 자리파기 Ø{F(g.LID_SCREW['d_cbore'])}×{F(g.LID_SCREW['cbore_depth'])} (F–F)"),
        ("8", (g.XC, L["y"][1] - 4), (14, -14), "자석 없음 (D14). 갈비 배치·앞 윗모서리 1×45° 모따기 = CAD L2"),
    ]
    K.callouts2(v, items, [X0 + 1.0], Y0 + 35.0, line_px=14.5, size_px=9.4)
    scalebar(v, X1 - 72.0, Y0 + 10.0, 20)
    rows.append([v])
    # ---------------- bottom view (mirrored in x) + knuckle axis section
    rows.append([panel_lid_bottom(), panel_knuckle_axis()])
    # ---------------- y-z sections
    xkf = (g.KNR["far"][0] + g.KNR["far"][1]) / 2
    xks = (g.SLOT["right"][0] + g.SLOT["right"][1]) / 2
    xh = (g.HO["x"][0] + g.HO["x"][1]) / 2

    zt = L["top_z"]

    def ex_kn(v, pid):
        v.circle(g.H[0], g.H[1], g.KN_FAR_HOLE / 2, cls="void")
        v.dim_v(L["top_z"], g.H[1], g.KP["base_y"][1] + 3.0, text=f"{F(g.H[1] - L['top_z'])}", ext_from=(g.KP["base_y"][1], g.H[0]), size_px=9, tpos="right")
        v.dim_h(g.KP["base_y"][0], g.KP["base_y"][1], zt - 13.85, text=f"{F(g.KP['base_y'][1] - g.KP['base_y'][0])}", ext_from=(L["bed_z"], L["bed_z"]), size_px=9)
        v.dim_h(g.KP["at_axis_y"][0], g.KP["at_axis_y"][1], g.H[1] + g.KP["R"] + 3.0, text=f"R{F(g.KP['R'])}", ext_from=(g.H[1], g.H[1]), size_px=9)
        T(v, v.u0 + 1.0, zt - 18.35, f"먼 볼 Ø{F(g.KN_FAR_HOLE)} (M3 탭), 가까운 볼 Ø{F(g.KN_NEAR_HOLE)}", size_px=9)
        T(v, v.u0 + 1.0, zt - 21.85, f"축 위로 R 밖 금지 · 밑 z{F(L['bed_z'])}까지 채움", size_px=9, cls="tx-s")

    def ex_slot(v, pid):
        hc = g.HG["heel_contact_yz"]
        v.circle(hc[0], hc[1], v.px(2.4), cls="pivot")
        v.poly(g.knuckle_profile(), cls="vis")
        v.circle(g.H[0], g.H[1], g.HG["ear_hub_R"], cls="cr-ph")
        v.poly(g.tf(g.EAR_PROFILE, g.TH_HEEL), cls="cr-ph")               # the 3a ear outline at 22 deg: the heel sits on the block
        v.dim_v(L["top_z"], g.HG["heel_stop_z"], g.HEEL_STOP["y"][0] - 1.5, text=f"{F(g.HG['heel_stop_h'])}", ext_from=(g.HEEL_STOP["y"][0], g.HEEL_STOP["y"][0]), size_px=9, tpos="left")
        v.dim_h(g.HEEL_STOP["y"][0], g.HEEL_STOP["y"][1], g.HG["heel_stop_z"] + 7.0, text=f"{F(g.HEEL_STOP['y'][1] - g.HEEL_STOP['y'][0])}", ext_from=(g.HEEL_STOP["z"][1], g.HEEL_STOP["z"][1]), size_px=9)
        T(v, v.u0 + 1.0, zt - 18.35, f"점 = {F(g.TH_HEEL)}° 뒤꿈치 닿는 곳 y{F(hc[0])}", size_px=9)
        T(v, v.u0 + 1.0, zt - 21.85, f"파랑 점선 = 귀 윤곽 ({F(g.TH_HEEL)}°), 축살 R{F(g.HG['ear_hub_R'])}", size_px=9, cls="tx-s")

    def ex_pocket(v, pid):
        piv, tip = g.LG["pivot_yz"], g.LG["tip_yz"]
        v.poly(g.leg_outline(piv, tip), cls="leg-ph")
        pk = g.PK
        # foot-end reach (R = L + t/2) around the leg pivot while the leg swings: at 25 deg it cuts the back-wall edge, at 22 deg it clears
        for key, cls in (("at_25", "ko"), ("at_22", "cr-ph")):
            pv = g.SWING[key]["pivot"]
            a_c = math.degrees(math.atan2(L["top_z"] - pv[1], pk["back_wall_y"] - pv[0]))
            v.poly(g.arc(tuple(pv), g.FOOT_REACH, a_c - 4.0, a_c + 3.0, 24), cls=cls, closed=False)
        v.dim_h(pk["ramp_front_y"], pk["back_wall_y"], L["top_z"] + 3.0, text=f"{F(pk['back_wall_y'] - pk['ramp_front_y'])}", ext_from=(L["top_z"], L["top_z"]), size_px=9)
        v.dim_v(pk["bottom_z"], L["top_z"], pk["back_wall_y"] + 3.0, text=f"{F(L['top_z'] - pk['bottom_z'])} {g.TOL['pocket']}", ext_from=(pk["back_wall_y"], pk["back_wall_y"]), size_px=9, tpos="right")
        angle_arc(v, (pk["ramp_front_y"], L["top_z"]), 5.0, -30.0, 0.0, "30°", size_px=9, tpos=(pk["ramp_front_y"] + 6.5, L["top_z"] - 1.2))
        T(v, v.u0 + 1.0, zt - 14.85, f"경사 앞 y{F(pk['ramp_front_y'])} (2판 규칙 y{F(pk['ramp_front_y_rev2_rule'])}이면 {F(pk['ramp_clear_rev2_rule'])} 파고듦)", size_px=9)
        T(v, v.u0 + 1.0, zt - 18.35, f"다리를 넣고 뺄 때 화면은 {F(g.TH_HEEL)}°: 발끝 반경 {F(g.FOOT_REACH)} < 모서리 {F(g.SW_D['at_22'])} (파랑)", size_px=9, cls="kot")
        T(v, v.u0 + 1.0, zt - 21.85, f"{F(g.TH_USE)}°면 모서리 {F(g.SW_D['at_25'])} → {F(-g.SWING['at_25']['worst_overlap'])} 긁음 (빨강) · 덩어리 z{F(L['bed_z'])}까지", size_px=9, cls="tx-s")

    def ex_hole(v, pid):
        cp = g.CL["pad"]
        for pn in g.CL["pins"]:
            v.rect(pn[1] - g.PIN_HOLE[0] / 2, cp["z"][0], g.PIN_HOLE[0], g.PIN_HOLE[1], cls="hid")
        yc_ = (cp["y"][0] + cp["y"][1]) / 2
        v.rect(yc_ - g.CLIP_SIZE[1] / 2, g.CLIP_Z[0], g.CLIP_SIZE[1], g.CLIP_Z[1] - g.CLIP_Z[0], cls="leg-ph")
        v.line(yc_ - g.CLIP_SIZE[1] / 2, g.CLAMP_Z[0], yc_ + g.CLIP_SIZE[1] / 2, g.CLAMP_Z[0], cls="rib")
        v.dim_h(g.HO["y"][0], g.HO["y"][1], L["top_z"] + 3.0, text=f"{F(g.HO['y'][1] - g.HO['y'][0])}", ext_from=(L["top_z"], L["top_z"]), size_px=9)
        v.dim_h(g.HOLE_WALL[2], g.HOLE_WALL[3], L["top_z"] + 7.0, text=f"{F(g.HOLE_WALL[3] - g.HOLE_WALL[2])} 벽 포함", ext_from=(L["top_z"], L["top_z"]), size_px=9)
        v.dim_v(cp["z"][0], cp["z"][1], cp["y"][1] + 2.5, text=f"{F(cp['z'][1] - cp['z'][0])}", ext_from=(cp["y"][1], cp["y"][1]), size_px=9, tpos="right")
        T(v, v.u0 + 1.0, zt - 18.85, f"점선 = 핀 구멍 Ø{F(g.PIN_HOLE[0])}×{F(g.PIN_HOLE[1])} (x{F(g.CL['pins'][0][0])}·{F(g.CL['pins'][1][0])}) · 보라 = 클립 z{FR(*g.CLIP_Z)}", size_px=9)
        T(v, v.u0 + 1.0, zt - 22.35, f"주황 = 리본을 덩어리 밑면 z{F(g.LID['bed_z'])}에 눌러 잡음 (z{FR(*g.CLAMP_Z)})", size_px=9, cls="rbt")

    def ex_foot(v, pid):
        f = g.FEET[1]
        v.dim_v(f["z"][0], f["z"][1], f["y"][0] - 2.0, text=f"{F(f['z'][1] - f['z'][0])} {g.TOL['fold_feet']}", ext_from=(f["y"][0], f["y"][0]), size_px=9, tpos="left")
        v.dim_h(f["y"][0], f["y"][1], f["z"][1] + 4.5, text=f"{F(f['y'][1] - f['y'][0])}", ext_from=(f["z"][1], f["z"][1]), size_px=9)
        v.dim_h(f["lip"]["y"][0], f["lip"]["y"][1], f["lip"]["z"][1] + 2.5, text=f"{F(f['lip']['y'][1] - f['lip']['y'][0])}", ext_from=(f["lip"]["z"][1], f["lip"]["z"][1]), size_px=9, tpos="right")
        v.dim_v(f["lip"]["z"][0], f["lip"]["z"][1], f["lip"]["y"][1] + 2.0, text=f"{F(f['lip']['z'][1] - f['lip']['z'][0])}", ext_from=(f["lip"]["y"][1], f["lip"]["y"][1]), size_px=9, tpos="right")
        fz = g.FO["rib_plane_z"]
        v.line(f["y"][0] - 4, fz, f["lip"]["y"][0], fz, cls="fold-ph")
        T(v, f["y"][0] - 3.5, zt - 18.35, f"턱과 발 사이 {F(f['lip']['y'][0] - f['y'][1])} · 점쇄선 = 접은 받침 패드 면", size_px=9)

    def ex_screw(v, pid):
        yb = g.SCREWS[0][1]
        cb = g.LID_SCREW
        bw = cb["boss_d"]
        v.rect(yb - bw / 2, L["bed_z"], bw, L["top_z"] - L["plate_t"] - L["bed_z"], cls="m-lid")
        v.rect(yb - bw / 2, L["bed_z"], bw, L["top_z"] - L["plate_t"] - L["bed_z"], cls="lid-ph")
        v.rect(yb - cb["d_cbore"] / 2, cb["seat_z"], cb["d_cbore"], L["top_z"] - cb["seat_z"], cls="void")
        v.rect(yb - cb["hole_d"] / 2, L["bed_z"], cb["hole_d"], cb["seat_z"] - L["bed_z"], cls="void")
        x0, x1, y0_, y1_ = g.bbox_xy("PR-SEAMRAIL-1")
        z0_, z1_ = g.bbox_z("PR-SEAMRAIL-1")
        v.rect(max(y0_, v.u0 + 0.5), z0_, min(y1_, v.geo_y1 - 0.5) - max(y0_, v.u0 + 0.5), z1_ - z0_, cls="m-print")
        v.rect(yb - cb["hole_d"] / 2, cb["hole_bottom"], cb["hole_d"], z1_ - cb["hole_bottom"], cls="void")      # insert hole (est.)
        z0p, z1p = g.bbox_z("PR-SEAMPOST-1")
        py0, py1 = g.bbox_xy("PR-SEAMPOST-1")[2:]
        v.rect(py0, max(z0p, v.v0 + 0.5), py1 - py0, z1p - max(z0p, v.v0 + 0.5), cls="m-print")
        v.rect(yb - 1.5, cb["tip_z"], 3.0, cb["screw_L"], cls="m-steel")
        v.rect(yb - cb["head_d"] / 2, cb["seat_z"], cb["head_d"], cb["head_h"], cls="m-steel")
        v.dim_v(cb["seat_z"], L["top_z"], yb - cb["d_cbore"] / 2 - 2.0, text=f"{F(cb['cbore_depth'])} (추정)", ext_from=(yb - cb["d_cbore"] / 2, yb - cb["d_cbore"] / 2), size_px=9, tpos="left")
        v.dim_v(cb["tip_z"], cb["hole_bottom"], yb + cb["d_cbore"] / 2 + 2.0, text=f"{F(cb['tip_z'] - cb['hole_bottom'])}", ext_from=(yb + 1.5, yb + cb["hole_d"] / 2), size_px=9, tpos="right")
        v.dim_v(z0_, cb["hole_bottom"], yb - cb["d_cbore"] / 2 - 2.0, text=f"{F(cb['rail_floor'])}", ext_from=(yb - cb["hole_d"] / 2, yb - cb["hole_d"] / 2), size_px=9, tpos="left")
        ordz(v, [(cb["seat_z"], yb + cb["d_cbore"] / 2, "머리 자리"), (cb["tip_z"], yb + 1.5, "나사 끝"), (L["bed_z"], v.geo_y1 - 0.5, "뚜껑 밑 = 레일 위")],
             v.geo_y1 + 1.0, gap_px=12.0, label_px=8.6, lo=v.v0 + 2.0)
        T(v, v.u0 + 1.0, zt + 5.15, f"M3×10 ISO 7380 (머리 Ø{F(cb['head_d'])}×{F(cb['head_h'])}) → 레일 인서트 물림 {F(cb['engage_est'])} (추정)", size_px=9)
        T(v, v.u0 + 1.0, zt + 2.15, f"나사 기둥 Ø{F(cb['boss_d'])} (점선) · 레일 · 기둥 = CAD L2", size_px=9, cls="tx-s")

    hy = g.H[0]
    rows.append([lid_sec("A–A", xkf, f"경첩 먼 볼 (탭 Ø{F(g.KN_FAR_HOLE)})", hy - 16.55, hy + 19.45, z1=zt + 18.5, px=300, extra=ex_kn),
                 lid_sec("A'–A'", xks, "귀 홈 · 뒤꿈치 멈춤 블록", hy - 16.55, hy + 19.45, z1=zt + 18.5, px=300, extra=ex_slot),
                 lid_sec("C–C", g.XC, "받침다리 주머니", g.PK["ramp_front_y"] - 10.43, g.PK["ramp_front_y"] + 25.57, px=300, extra=ex_pocket),
                 lid_sec("B–B", xh, "리본 구멍 · 클립 덩어리", g.HO["y"][0] - 6.55, g.HO["y"][0] + 29.45, z0=zt - 26.85, px=290, extra=ex_hole),
                 lid_sec("E–E", (g.FEET[1]["x"][0] + g.FEET[1]["x"][1]) / 2, "뒤 받침 발 + 턱", g.FEET[1]["y"][0] - 7.55, g.FEET[1]["y"][0] + 28.45, px=290, extra=ex_foot)])
    rows.append([lid_sec("F–F", g.SCREWS[0][0], "뚜껑 앞 나사 (추정)", g.SCREWS[0][1] - 14.0, g.SCREWS[0][1] + 30.0, z0=g.LID_SCREW["tip_z"] - 5.35, px=440, extra=ex_screw, geo_y1=g.SCREWS[0][1] + 16.0),
                 panel_t04_notes()])
    base = os.path.join(OUT, "t04_lid_changes")
    K.page(rows, base, sub_head(n, "가운데 뚜껑 (CU-SCREENLID) — 수정 3판에서 더하는 것"),
           subtitle=SRC_LINE + "\n뚜껑 자체(판 3 + 갈비, 레일 인서트 나사)는 CAD L2 설계. 이 도면은 화면 때문에 더하는 경첩·멈춤 블록·주머니·구멍·클립·통풍·받침 발. 표시: 【새로】/【변경】/【그대로】 = CAD_SPEC_rev3 A장.",
           foot=foot_lines())
    add_sheet(n, os.path.basename(base), f"가운데 뚜껑 변경 (수정 {g.REV}판)",
              f"CU-SCREENLID에 더하는 것: 경첩 받침 2(볼·귀 홈 {F(g.SLOT['left'][1] - g.SLOT['left'][0])}·멈춤 블록 {F(g.HG['heel_stop_h'])}, M3×20 축 물림 {F(g.KN_ENGAGE)}), "
              f"받침다리 주머니(30° 경사, 뒷벽 C{F(g.LG['pocket_edge_C'])}, {F(g.TH_HEEL)}°에서 다리 넣기), 리본·전원선 구멍 {F(g.HO['x'][1] - g.HO['x'][0])}×{F(g.HO['y'][1] - g.HO['y'][0])}, "
              f"클립 덩어리·핀 구멍, 통풍 {len(g.V['slots'])}, 접이 받침 발 {len(g.FEET)}(뒤 턱), 뚜껑 나사 {tg(7)} 자리파기 Ø{F(g.LID_SCREW['d_cbore'])}×{F(g.LID_SCREW['cbore_depth'])} "
              f"(나사 끝 z{F(g.LID_SCREW['tip_z'])}, 추정). 위·밑 모습, 경첩 축 단면, y–z 단면 A·A'·B·C·E·F.")


def panel_lid_bottom():
    """underside, drawn as seen from below and mirrored in x (+x on the left); filled blocks down to the bed plane."""
    L = g.LID
    X = lambda x: 2 * g.XC - x
    v = View(X(L["x"][1]) - 8, 196.0, X(L["x"][0]) + 50, 352.0, px_width=900, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, X(L["x"][1]) - 7.5, 349.0, f"밑에서 본 모습 (좌우 반전: 왼쪽이 +x) — 출력 바닥 z{F(L['bed_z'])}까지 채우는 덩어리", size_px=11.5)

    def R(x0, x1, y0, y1, cls):
        a, b = sorted([X(x0), X(x1)])
        v.rect(a, y0, b - a, y1 - y0, cls=cls)
    R(L["x"][0], L["x"][1], L["y"][0], L["y"][1], "m-lid")
    for cid in ("PR-SEAMRAIL-1", "PR-SEAMRAIL-2"):
        x0, x1, y0, y1 = g.bbox_xy(cid)
        R(max(x0, L["x"][0]), min(x1, L["x"][1]), y0, y1, "hid")
    for kn in (g.KNL, g.KNR):
        R(kn["all"][0], kn["all"][1], g.KN_FILL["y"][0], g.KN_FILL["y"][1], "m-print2")
    hw = g.HOLE_WALL
    R(hw[0], hw[1], hw[2], hw[3], "m-print2")
    cp = g.CL["pad"]
    R(cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], "m-print2")
    R(g.HO["x"][0], g.HO["x"][1], g.HO["y"][0], g.HO["y"][1], "void")
    for pn in g.CL["pins"]:
        v.circle(X(pn[0]), pn[1], g.PIN_HOLE[0] / 2, cls="void")
    b = g.PK["block"]
    R(b["x"][0], b["x"][1], b["y"][0], b["y"][1], "m-print2")
    for sl in g.V["slots"]:
        R(sl[0], sl[1], sl[2], sl[3], "void")
    for (x, y) in g.SCREWS:
        v.circle(X(x), y, 1.7, cls="void")
    ordz(v, [(g.KN_FILL["y"][0], X(g.KNL["all"][0]), "경첩 덩어리"), (hw[2], X(hw[0]), "구멍 벽"), (g.KN_FILL["y"][1], X(g.KNL["all"][0]), ""),
             (cp["y"][0], X(cp["x"][0]), "클립 덩어리"), (g.CL["pins"][0][1], X(g.CL["pins"][0][0]), "핀 구멍"), (cp["y"][1], X(cp["x"][0]), ""),
             (b["y"][0], X(b["x"][0]), "주머니 덩어리"), (b["y"][1], X(b["x"][0]), "")], X(L["x"][0]) + 6.0, gap_px=12.5, label_px=9, prefix="y")
    T(v, X(L["x"][1]) - 7.0, 200.0, f"덩어리: 경첩 x{FR(*g.KNL['all'])}·{FR(*g.KNR['all'])} · 구멍 벽 x{FR(hw[0], hw[1])} · 클립 x{FR(*cp['x'])} z{FR(*cp['z'])} · 주머니 x{FR(*b['x'])}",
      size_px=9)
    return v


def panel_knuckle_axis():
    """x-z section on the knuckle axis y = H (left set), looking from the front (-y): cheeks, ear slot, heel stop behind, M3x20."""
    L = g.LID
    kn = g.KNL
    X0, X1 = kn["all"][0] - 9.0, kn["all"][1] + 12.0
    v = View(X0, 55.0, X1, 99.0, px_width=572, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, X0 + 0.3, 97.3, f"G–G (y{F(g.H[0])}, 경첩 축): 왼 경첩, 앞(−y)에서", size_px=11.5)
    v.rect(X0 + 0.5, L["top_z"] - L["plate_t"], X1 - X0 - 1.0, L["plate_t"], cls="m-lid")
    K.poly_h(v, g.rect(kn["all"][0], kn["all"][1], L["bed_z"], L["top_z"] - L["plate_t"] + 0.01), "m-lid", pid["lid"])
    top = g.H[1] + g.KP["R"]
    for part in ("near", "far"):
        K.poly_h(v, g.rect(kn[part][0], kn[part][1], L["top_z"] - 0.01, top), "m-lid", pid["lid"])
    v.rect(g.SLOT["left"][0], L["top_z"], g.SLOT["left"][1] - g.SLOT["left"][0], g.HG["heel_stop_z"] - L["top_z"], cls="vis")
    e = kn["ear"]
    v.rect(e[0], g.H[1] - g.HG["ear_hub_R"], e[1] - e[0], 2 * g.HG["ear_hub_R"], cls="cr-ph")
    x0, x1 = kn["near"][0], kn["near"][0] + g.AXLE_L
    v.rect(x0, g.H[1] - 1.5, x1 - x0, 3.0, cls="m-steel")
    v.rect(x0 - g.M3_HEAD["h"], g.H[1] - g.M3_HEAD["d"] / 2, g.M3_HEAD["h"], g.M3_HEAD["d"], cls="m-steel")
    for part, d in (("near", g.KN_NEAR_HOLE), ("far", g.KN_FAR_HOLE)):
        v.line(kn[part][0], g.H[1] + d / 2, kn[part][1], g.H[1] + d / 2, cls="hid")
        v.line(kn[part][0], g.H[1] - d / 2, kn[part][1], g.H[1] - d / 2, cls="hid")
    zd = top + 2.5
    v.dim_h(kn["near"][0], kn["near"][1], zd, text=F(kn["near"][1] - kn["near"][0]), ext_from=(top, top), size_px=9)
    v.dim_h(kn["ear"][0], kn["ear"][1], zd, text=F(kn["ear"][1] - kn["ear"][0]), ext_from=(g.H[1] + g.HG["ear_hub_R"], g.H[1] + g.HG["ear_hub_R"]), size_px=9)
    v.dim_h(kn["far"][0], kn["far"][1], zd, text=F(kn["far"][1] - kn["far"][0]), ext_from=(top, top), size_px=9)
    v.dim_h(kn["all"][0], kn["all"][1], zd + 4.0, text=f"{F(kn['all'][1] - kn['all'][0])} (틈 {F(g.KN_GAP)} {g.TOL['slot_gap']} ×2)", ext_from=(zd, zd), size_px=9)
    v.dim_h(kn["far"][0], x1, g.H[1] - 5.0, text=f"물림 {F(g.KN_ENGAGE)}", ext_from=(g.H[1], g.H[1]), size_px=9)
    T(v, X0 + 0.5, 60.5, f"M3×20: 가까운 볼 Ø{F(g.KN_NEAR_HOLE)} 관통 → 귀 Ø{F(g.KN_NEAR_HOLE)} → 먼 볼 Ø{F(g.KN_FAR_HOLE)} 탭 (끝 x{F(x1)})", size_px=9)
    T(v, X0 + 0.5, 57.0, f"오른 경첩은 x{F(g.XC)} 대칭 (나사는 +x 쪽에서) · 가는 선 = 멈춤 블록 (귀 자리, 앞쪽)", size_px=9, cls="tx-s")
    return v


def panel_t04_notes():
    v = View(0.0, 0.0, 250.0, 62.0, px_width=1032, pad_px=6)
    panel_title(v, 0.5, 60.0, "출력 · 확인", size_px=12)
    L = g.LID
    lid_pp = [q for q in g.BODY["printed_parts"]["list"] if q["part"] == "CU-SCREENLID"][0]
    cb = g.LID_SCREW
    lines = [
        f"• 출력: 리브 면을 베드에 (윗면 z{F(L['top_z'])}이 위). 경첩 덩어리·구멍 벽·클립 덩어리·주머니 덩어리·나사 기둥은 모두 z{F(L['bed_z'])}까지 채워 서포트 없이 뽑음 (A-9).",
        f"• x 방향 구멍 Ø{F(g.KN_NEAR_HOLE)}·Ø{F(g.KN_FAR_HOLE)}는 물방울 모양으로 뽑고 드릴로 다듬음. 먼 볼 Ø{F(g.KN_FAR_HOLE)}는 M3×20이 직접 탭 (물림 {F(g.KN_ENGAGE)}).",
        f"• 경첩 볼은 축 위로 R{F(g.KP['R'])} 밖으로 나오면 안 됨 (모듈 위 금지 y{F(g.KO['y_max'])}, 볼 밑 앞 y{F(g.KP['base_y'][0])}).",
        f"• 뒤꿈치 틈 {F(g.HG['heel_gap_at_25'])} ({F(g.TH_USE)}°)은 출력 공차 수준 → 다리 발이 주머니에 잘 안 들어가면 받침 뒤꿈치를 0.3 깎음 (G-6).",
        f"• 다리는 화면을 {F(g.TH_HEEL)}°(뒤꿈치)에 댄 채 넣고 뺌. 뒷벽 위 모서리는 C{F(g.LG['pocket_edge_C'])}만 (더 깎으면 발 자리가 없어짐, C–C).",
        f"• 뚜껑 나사 x{F(g.SCREWS[0][0])}·{F(g.SCREWS[1][0])}는 추정 (레일 x{FR(*g.bbox_xy('PR-SEAMRAIL-1')[:2], 0)}·{FR(*g.bbox_xy('PR-SEAMRAIL-2')[:2], 0)}, 앞 기둥 모서리 위). "
        f"자리파기 깊이 = 뚜껑 두께 {F(L['top_z'] - L['bed_z'])} − (10 − 인서트 물림 {F(cb['engage_est'])}) = {F(cb['cbore_depth'])}; 인서트가 바뀌면 이 식으로.",
        f"• 무게: 뚜껑은 CAD L2 값 (약 {F(lid_pp['g_each_est'], 0)} g, body_L2 printed_parts). 화면 쪽 덩어리 추가분은 CAD에서 계산.",
    ]
    note_lines(v, lines, 0.5, 52.0, line_px=15.5, size_px=9.8, cls="lt")
    return v


# ================================================================ t05 easel leg + small parts
def sheet_t05():
    n = 5
    rows = []
    Lg, R_, B_, T_ = g.LEG_L, g.LEG_R, g.LEG_B, g.LEG_T
    # ---------------- leg: side (s, thickness) + top (s, width)
    v = View(-10.0, -34.0, 104.0, 30.0, px_width=1000, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, -9.5, 27.5, f"받침다리 — PETG 1개, 약 {F(g.N['mass_est']['leg_g'], 0)} g (넓은 면을 베드에)", size_px=12)
    side = g.leg_outline((0.0, 12.0), (Lg, 12.0))
    K.rings_h(v, [side], "m-leg", pid["leg"], subs=[g.circle((0.0, 12.0), g.LEG_HOLE / 2, 40)])
    v.line(-R_ - 3, 12.0, Lg + R_ + 3, 12.0, cls="cl")
    for sx in (0.0, Lg):
        v.line(sx, 12.0 - R_ - 3, sx, 12.0 + R_ + 3, cls="cl")
    top = g.rect(-R_, Lg + R_, -12.0 - B_ / 2, -12.0 + B_ / 2)
    K.rings_h(v, [top], "m-leg", pid["leg"])
    v.line(0.0, -12.0 - B_ / 2, 0.0, -12.0 + B_ / 2, cls="hid")
    for d_ in (-g.LEG_HOLE / 2, g.LEG_HOLE / 2):
        v.line(d_, -12.0 - B_ / 2, d_, -12.0 + B_ / 2, cls="hid")
    v.line(-R_ - 3, -12.0, Lg + R_ + 3, -12.0, cls="cl")
    v.dim_h(0.0, Lg, 12.0 + R_ + 5.0, text=f"{F(Lg)} {g.TOL['axis_pos']} (축–발끝)", ext_from=(12.0 + R_, 12.0 + R_), size_px=10)
    v.dim_h(-R_, Lg + R_, 12.0 + R_ + 10.0, text=f"{F(Lg + 2 * R_)} 전체", ext_from=(12.0, 12.0), size_px=10)
    v.dim_v(12.0 - R_, 12.0 + R_, Lg + R_ + 6.0, text=f"{F(T_)}", ext_from=(Lg + R_, Lg + R_), size_px=10)
    v.dim_v(-12.0 - B_ / 2, -12.0 + B_ / 2, Lg + R_ + 6.0, text=f"{F(B_)}", ext_from=(Lg + R_, Lg + R_), size_px=10)
    lead(v, g.LEG_HOLE / 2 * 0.7, 12.0 + g.LEG_HOLE / 2 * 0.7, 10.0, 22.0, f"Ø{F(g.LEG_HOLE)} {g.TOL['hole_axle']} 관통 (M3×20 축, 물방울로 뽑고 드릴)", size_px=9.5)
    lead(v, Lg + R_ * 0.7, 12.0 - R_ * 0.7, 76.0, 2.0, f"양 끝 R{F(R_)} (발끝은 주머니 바닥·뒷벽에 닿음)", size_px=9.5, anchor="end")
    T(v, -9.5, -24.5, "위: 옆에서 (두께 방향), 아래: 위에서 (폭 방향). 축 구멍은 폭 방향(x).", size_px=9.5, cls="tx-s")
    T(v, -9.5, -29.0, f"사용: 축 (y{F(g.LG['pivot_yz'][0])}, z{F(g.LG['pivot_yz'][1])}) → 발끝 (y{F(g.LG['tip_yz'][0])}, z{F(g.LG['tip_yz'][1])}), 수평에서 {F(g.LG['angle_deg'])}° · "
      f"접음: 받침 뒤 u{FR(g.LEGP[0] - R_, g.LG['stow_tip_u'])}, 클립 u{FR(*g.CLIPD['u'])}", size_px=9.5)
    scalebar(v, 84.0, -33.0, 10)
    rows.append([v, panel_t05_leg_info()])
    # ---------------- inspection-window cover
    rows.append([panel_cover_plan(), panel_cover_secs()])
    # ---------------- ribbon clip + screen cover + hardware
    rows.append([panel_clip(), panel_hardware()])
    base = os.path.join(OUT, "t05_leg_small_parts")
    K.page(rows, base, sub_head(n, "받침다리 · 점검창 덮개 · 리본 클립 · 나사"),
           subtitle=SRC_LINE + "\n작은 부품은 각자의 좌표로 그림 (덮개 = 받침 좌표 xr·u·w 그대로, 클립 = 뚜껑 밑 x·y).",
           foot=foot_lines())
    cp_ = g.CLIP_PART
    add_sheet(n, os.path.basename(base), "받침다리 · 작은 부품",
              f"받침다리 {F(g.LEG_L + 2 * g.LEG_R)}×{F(g.LEG_B)}×{F(g.LEG_T)} (축–발끝 {F(g.LEG_L)}, R{F(g.LEG_R)} 끝, Ø{F(g.LEG_HOLE)}; 넣고 빼기는 화면 {F(g.TH_HEEL)}°에서), "
              f"점검창 덮개 (끼움부·턱·볼록 자리, 두 단면), 리본 클립 {F(cp_['L'])}×{F(cp_['W'])}×{F(cp_['T'])} (핀 Ø{F(cp_['pin_d'])}×{F(cp_['pin_len'])} 두 개, "
              f"윗면 전원선 홈 x{FR(*g.WG['x'])} 깊이 {F(g.WG['depth'])}), 화면 덮개(선택), 나사·축 목록 (M3 ISO 7380).")


def panel_t05_leg_info():
    v = View(0.0, 0.0, 100.0, 64.0, px_width=470, pad_px=6)
    panel_title(v, 1.0, 61.5, "다리 · 힘 · 넣는 순서 (numbers.json)", size_px=12)
    st = g.ST
    lines = [
        f"• 길이·축 자리: 접은 다리가 받침 윗끝 안 (u{F(g.LG['stow_tip_u'])} ≤ {F(g.U1 - 3.5)}),",
        f"   발은 뚜껑 뒤끝에서 {F(g.CK['pocket_back_material'])} 안, 각도 25~40°에서 팔 길이 최대 {F(st['leg_arm_mm'])}",
        f"• 화면 위쪽 10 N: 다리 압축 {F(st['leg_force'])} N, 좌굴 한계 {st['leg_Pcr']} N ({F(st['leg_SF'])}배)",
        f"• {F(g.TH_HEEL)}°에서 다리 축이 {F(g.LG['pivot_shift_at_22'])} 움직임 (주머니 뒷벽이 멈춤)",
        f"• 【3a】 넣고 빼기: 화면을 {F(g.TH_HEEL)}°(뒤꿈치)에 댄 채 다리를 내리거나 올림",
        f"\u00a0\u00a0\u00a0{F(g.TH_HEEL)}°: 뒷벽 위 모서리까지 {F(g.SW_D['at_22'])} > 발 끝 반경 {F(g.FOOT_REACH)}",
        f"\u00a0\u00a0\u00a0→ 발이 경사에 먼저 닿고, 손을 놓으면 {F(g.TH_USE)}°로 돌며 뒷벽까지 미끄러짐",
        f"\u00a0\u00a0\u00a0{F(g.TH_USE)}°에서 넣으면 {F(g.SW_D['at_25'])} < {F(g.FOOT_REACH)} → 모서리를 {F(-g.SWING['at_25']['worst_overlap'])} 긁음",
        f"• 다리 걸이 틈 (양쪽) {F(g.CLV['far'][0] - g.LG['xr'][1])} · 클립 턱 다리 위 {F(g.CLIPD['over_leg'])}",
        f"• 접었을 때 다리 z{FR(*g.LG['fold_leg_z'])} (뚜껑 위 {F(g.CK['fold_leg_clear_lid'])} 이상)",
        "• 자석 없음 (D14)",
    ]
    note_lines(v, lines, 1.0, 55.0, line_px=13.2, size_px=9.2, cls="lt")
    return v


def cov_rings_plan():
    c = g.COV
    return c


def panel_cover_plan():
    """cover seen from the back (as in the back view of T3: mirrored, +x on the left)."""
    c = g.COV
    X = lambda x: -x
    v = View(X(c["flange"][1]) - 5, c["flange"][2] - 16, X(c["flange"][0]) + 26, c["flange"][3] + 9, px_width=520, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, X(c["flange"][1]) - 4.5, c["flange"][3] + 6.5, "점검창 덮개 — 뒤에서 (좌우 반전, T3 뒤 모습과 같음)", size_px=11)

    def R(x0, x1, u0, u1, cls):
        a, b = sorted([X(x0), X(x1)])
        v.rect(a, u0, b - a, u1 - u0, cls=cls)
    R(c["flange"][0], c["flange"][1], c["flange"][2], c["flange"][3], "m-cr")
    R(c["plug"][0], c["plug"][1], c["plug"][2], c["plug"][3], "hid")
    R(c["dome"][0], c["dome"][1], c["dome"][2], c["dome"][3], "m-cr")
    R(c["cav"][0], c["cav"][1], c["cav"][2], c["cav"][3], "hid")
    R(g.INSP["xr"][0], g.INSP["xr"][1], g.INSP["u"][0], g.INSP["u"][1], "ph2")
    ordz(v, [(c["flange"][2], X(c["flange"][0]), "턱"), (c["plug"][2], X(c["plug"][0]), "끼움부"), (c["dome"][2], X(c["dome"][0]), "볼록"),
             (c["cav"][2], X(c["cav"][0]), "속"), (c["cav"][3], X(c["cav"][0]), ""), (c["dome"][3], X(c["dome"][0]), ""),
             (c["plug"][3], X(c["plug"][0]), ""), (c["flange"][3], X(c["flange"][0]), "")], X(c["flange"][0]) + 3.0, gap_px=12.0, label_px=8.8, prefix="u")
    ordy(v, [(X(c["flange"][1]), c["flange"][2], "턱"), (X(c["plug"][1]), c["plug"][2], "끼움부"), (X(c["dome"][1]), c["dome"][2], "볼록"), (X(c["cav"][1]), c["cav"][2], ""),
             (X(c["cav"][0]), c["cav"][2], ""), (X(c["dome"][0]), c["dome"][2], ""), (X(c["plug"][0]), c["plug"][2], ""), (X(c["flange"][0]), c["flange"][2], "")],
         c["flange"][2] - 2.0, gap_px=12.0, label_px=8.8, prefix="−xr ")
    T(v, X(c["flange"][1]) - 4.5, c["flange"][3] + 2.5, f"끼움부 = 창 − {F(g.COVER['plug_under'])} (각 변, 해석) · 턱 = 창 + {F(g.COVER['flange'])}", size_px=9)
    return v


def panel_cover_secs():
    """two sections of the cover in one panel (w up = backward): left = through the dome centre xr (u to the right),
    right = through the ribbon fold u (xr to the right, drawn shifted)."""
    c = g.COV
    xr0 = (c["cav"][0] + c["cav"][1]) / 2
    u0 = g.S["fpc"]["pin_u_centre"]
    DX = c["flange"][3] - c["flange"][0] + 12.0          # shift of the second section
    v = View(c["flange"][2] - 22, -2.0, c["flange"][1] + DX + 4, 27.0, px_width=950, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, c["flange"][2] - 21.5, 25.2, f"덮개 단면 — 왼쪽: xr{F(xr0)} (u 오른쪽) · 오른쪽: u{F(u0)} (xr 오른쪽) · w 위 = 뒤", size_px=11)
    # section 1: (u, w)
    adds = [g.rect(c["plug"][2], c["plug"][3], c["plug_w"][0], c["plug_w"][1]), g.rect(c["flange"][2], c["flange"][3], c["flange_w"][0], c["flange_w"][1]),
            g.rect(c["dome"][2], c["dome"][3], c["dome_w"][0], c["dome_w"][1])]
    subs = [g.rect(c["cav"][2], c["cav"][3], c["cav_w"][0] - 0.05, c["cav_w"][1])]
    K.rings_h(v, adds, "m-cr", pid["cr"], subs=subs)
    for (a0, a1) in ((c["flange"][2] - 3, g.INSP["u"][0]), (g.INSP["u"][1], c["flange"][3] + 3)):
        v.rect(a0, g.PL_IN, a1 - a0, g.PL_OUT - g.PL_IN, cls="ph2")
    v.line(c["flange"][2] - 3, g.GB, c["flange"][3] + 3, g.GB, cls="glass")
    v.circle(u0, g.GB + g.RB["fold_roll_R"], g.RB["fold_roll_R"], cls="rib")
    v.dim_h(c["plug"][2], c["plug"][3], 6.0, text=f"{F(c['plug'][3] - c['plug'][2])} (창 {F(g.INSP['u'][1] - g.INSP['u'][0])})", ext_from=(c["plug_w"][0], c["plug_w"][0]), size_px=9)
    v.dim_h(c["flange"][2], c["flange"][3], 21.5, text=f"{F(c['flange'][3] - c['flange'][2])} 턱", ext_from=(c["flange_w"][1], c["flange_w"][1]), size_px=9)
    v.dim_h(c["dome"][2], c["dome"][3], 18.5, text=f"{F(c['dome'][3] - c['dome'][2])} 볼록", ext_from=(c["dome_w"][1], c["dome_w"][1]), size_px=9)
    ordz(v, [(g.GB, c["flange"][2] - 3, "화면 뒤"), (c["plug_w"][0], c["flange"][2], "끼움부 안 = 뒷판 안"), (c["flange_w"][0], c["flange"][2], "턱"),
             (c["flange_w"][1], c["flange"][2], "턱 뒤"), (c["cav_w"][1], c["dome"][2], "볼록 속"), (c["dome_w"][1], c["dome"][2], "볼록 밖")],
         c["flange"][2] - 3.5, side="left", gap_px=11.5, label_px=8.6, prefix="w")
    T(v, u0 + 4.0, 3.2, f"리본 접힘 R{F(g.RB['fold_roll_R'])}", size_px=9, cls="rbt")
    # section 2: (xr + DX, w)
    sh = lambda poly: [(x + DX, w) for (x, w) in poly]
    adds2 = [g.rect(c["plug"][0], c["plug"][1], c["plug_w"][0], c["plug_w"][1]), g.rect(c["flange"][0], c["flange"][1], c["flange_w"][0], c["flange_w"][1]),
             g.rect(c["dome"][0], c["dome"][1], c["dome_w"][0], c["dome_w"][1])]
    subs2 = [g.rect(c["cav"][0], c["cav"][1], c["cav_w"][0] - 0.05, c["cav_w"][1])]
    K.rings_h(v, [sh(p) for p in adds2], "m-cr", pid["cr"], subs=[sh(p) for p in subs2])
    for (a0, a1) in ((c["flange"][0] - 3, g.INSP["xr"][0]), (g.INSP["xr"][1], c["flange"][1] + 3)):
        v.rect(a0 + DX, g.PL_IN, a1 - a0, g.PL_OUT - g.PL_IN, cls="ph2")
    v.line(c["flange"][0] - 3 + DX, g.GB, c["flange"][1] + 3 + DX, g.GB, cls="glass")
    v.rect(g.S["fpc"]["xr"][0] + DX, g.GB - 1.2, g.S["fpc"]["xr"][1] - g.S["fpc"]["xr"][0], 1.2, cls="conn")
    v.dim_h(c["plug"][0] + DX, c["plug"][1] + DX, 6.0, text=f"{F(c['plug'][1] - c['plug'][0])} (창 {F(g.INSP['xr'][1] - g.INSP['xr'][0])})", ext_from=(c["plug_w"][0], c["plug_w"][0]), size_px=9)
    v.dim_h(c["flange"][0] + DX, c["flange"][1] + DX, 21.5, text=f"{F(c['flange'][1] - c['flange'][0])} 턱", ext_from=(c["flange_w"][1], c["flange_w"][1]), size_px=9)
    v.dim_h(c["dome"][0] + DX, c["dome"][1] + DX, 18.5, text=f"{F(c['dome'][1] - c['dome'][0])} 볼록", ext_from=(c["dome_w"][1], c["dome_w"][1]), size_px=9)
    T(v, g.S["fpc"]["xr"][0] + DX, 3.2, "DSI ZIF (추정)", size_px=9)
    T(v, c["flange"][2] - 21.5, -1.0, f"볼록 속 w{F(c['cav_w'][1])} = 화면 뒤 {F(g.GB)} + 2R{F(g.RB['fold_roll_R'])} + 리본 3겹 {F(3 * g.RB['ffc_t'])} + 0.3 · 살 {F(c['skin'])} · "
      "걸쇠 2개 (끼움부 u 양끝, 모양은 CAD 재량)", size_px=9)
    return v


def panel_clip():
    cp = g.CLIP_PART
    xc = g.HOLE_XC
    yc = (g.CL["pad"]["y"][0] + g.CL["pad"]["y"][1]) / 2
    wg = g.WG
    v = View(xc - cp["L"] / 2 - 6, -16.0, xc + cp["L"] / 2 + 40, 28.0, px_width=760, pad_px=6)
    pid = K.pid_set(v)
    panel_title(v, xc - cp["L"] / 2 - 5.5, 26.0, f"리본 클립 — {F(cp['L'])}×{F(cp['W'])}×{F(cp['T'])} PETG, 뚜껑 밑 (위: 위에서, 아래: 옆에서 −y 방향으로)", size_px=11)
    # plan (top face) centred at v = 12
    oy = 12.0 - yc
    K.rings_h(v, [g.rect(xc - cp["L"] / 2, xc + cp["L"] / 2, yc - cp["W"] / 2 + oy, yc + cp["W"] / 2 + oy)], "m-leg", pid["leg"])
    v.rect(wg["x"][0], yc - cp["W"] / 2 + oy, wg["x"][1] - wg["x"][0], cp["W"], cls="m-sbar")        # groove floor (1.8 lower)
    for pn in g.CL["pins"]:
        v.circle(pn[0], pn[1] + oy, cp["pin_d"] / 2, cls="m-cr")
    h = g.RB_W / 2
    v.rect(xc - h, yc - cp["W"] / 2 - 3 + oy, 2 * h, cp["W"] + 6, cls="rib-t")
    v.line(g.PW_X, yc - cp["W"] / 2 - 3 + oy, g.PW_X, yc + cp["W"] / 2 + 3 + oy, cls="pw")
    v.dim_h(g.CL["pins"][0][0], g.CL["pins"][1][0], 12.0 + cp["W"] / 2 + 3.0, text=f"{F(2 * cp['pin_dx'])} ±0.1", ext_from=(12.0, 12.0), size_px=9)
    v.dim_v(12.0 - cp["W"] / 2, 12.0 + cp["W"] / 2, xc + cp["L"] / 2 + 2.5, text=f"{F(cp['W'])}", ext_from=(xc + cp["L"] / 2, xc + cp["L"] / 2), size_px=9)
    # side view (x-z, looking along -y): v = oz + (z - lid bed)
    oz = -6.0
    zv = lambda z: oz + (z - g.LID["bed_z"])
    K.rings_h(v, [g.rect(xc - cp["L"] / 2, xc + cp["L"] / 2, zv(g.CLIP_Z[0]), zv(g.CLIP_Z[1]))], "m-leg", pid["leg"],
              subs=[g.rect(wg["x"][0], wg["x"][1], zv(g.CLIP_Z[1] - wg["depth"]), zv(g.CLIP_Z[1]) + 0.05)])
    for pn in g.CL["pins"]:
        v.rect(pn[0] - cp["pin_d"] / 2, zv(g.CLIP_Z[1]), cp["pin_d"], cp["pin_len"], cls="m-leg")
        v.rect(pn[0] - cp["hole"][0] / 2, zv(g.LID["bed_z"]), cp["hole"][0], cp["hole"][1], cls="hid")
    v.line(xc - cp["L"] / 2 - 3, zv(g.LID["bed_z"]), xc + cp["L"] / 2 + 3, zv(g.LID["bed_z"]), cls="lid-ph")
    v.rect(xc - h, zv(g.CLAMP_Z[0]), 2 * h, g.CLAMP_Z[1] - g.CLAMP_Z[0], cls="ffc")
    v.circle(g.PW_X, zv(g.PW["waypoints"][1][2]), 0.6, cls="wire5")
    v.dim_h(xc - cp["L"] / 2, xc + cp["L"] / 2, zv(g.CLIP_Z[0]) - 3.0, text=f"{F(cp['L'])}", ext_from=(zv(g.CLIP_Z[0]), zv(g.CLIP_Z[0])), size_px=9)
    v.dim_h(wg["x"][0], wg["x"][1], zv(g.CLIP_Z[0]) - 1.2, text=f"홈 {F(wg['x'][1] - wg['x'][0])}", ext_from=(zv(g.CLIP_Z[1] - wg["depth"]), zv(g.CLIP_Z[1] - wg["depth"])), size_px=8.8, tpos="right")
    v.dim_v(zv(g.CLIP_Z[1]), zv(g.CLIP_Z[1]) + cp["pin_len"], g.CL["pins"][1][0] + 3.0, text=f"{F(cp['pin_len'])} (구멍 {F(cp['hole'][1])} − 0.5)", ext_from=(g.CL["pins"][1][0], g.CL["pins"][1][0]), size_px=9, tpos="right")
    v.dim_v(zv(g.CLIP_Z[1] - wg["depth"]), zv(g.CLIP_Z[1]), xc + cp["L"] / 2 + 2.0, text=f"홈 깊이 {F(wg['depth'])}", ext_from=(wg["x"][1], wg["x"][1]), size_px=8.8, tpos="right")
    tx = xc + cp["L"] / 2 + 6.0
    T(v, tx, 20.0, f"핀 Ø{F(cp['pin_d'])} ×2, 길이 {F(cp['pin_len'])} (클립과 한 몸) → 뚜껑 밑 구멍 Ø{F(cp['hole'][0])}×{F(cp['hole'][1])}", size_px=9)
    T(v, tx, 16.5, f"핀 x{F(g.CL['pins'][0][0])}·{F(g.CL['pins'][1][0])}, y{F(g.CL['pins'][0][1])} (뚜껑 좌표)", size_px=9)
    T(v, tx, 13.0, f"주황 = 리본 {F(g.RB_W)} 폭 (x{FR(xc - h, xc + h)}), 평평한 면이 리본만 누름", size_px=9, cls="rbt")
    T(v, tx, 9.5, f"【3a】 윗면 전원선 홈 x{FR(*wg['x'])} 깊이 {F(wg['depth'])} (y로 끝까지)", size_px=9, cls="pwt")
    T(v, tx, 6.0, f"홈 ↔ 리본 끝 {F(wg['x'][0] - g.CLIP_RIB_EDGE)} · 홈 ↔ 핀 {F(g.CLIP_PIN_EDGE - wg['x'][1])}, 전원선 x{F(g.PW_X)} z{F(g.PW['waypoints'][1][2])}", size_px=9, cls="pwt")
    T(v, tx, 0.5, f"옆: 뚜껑 밑면 z{F(g.LID['bed_z'])} (보라 점선), 클립 z{FR(*g.CLIP_Z)}", size_px=9)
    T(v, tx, -3.0, f"리본 z{FR(*g.CLAMP_Z)} (두께 {F(g.RB['ffc_t'])})를 덩어리 밑면에 눌러 잡음", size_px=9)
    T(v, tx, -6.5, "(끼움 세기·핀 끝 모따기는 CAD 재량)", size_px=9, cls="tx-s")
    return v


def panel_hardware():
    v = View(0.0, 0.0, 150.0, 90.0, px_width=712, pad_px=6)
    panel_title(v, 1.0, 87.5, "나사 · 축 · 출력 부품 (design.json)", size_px=12)
    hw = g.HW
    rows = [["M3×20", str(hw.get("M3×20", "")), f"ISO 7380 (머리 Ø{F(g.AX_HEAD['d'])}×{F(g.AX_HEAD['h'])}, L렌치 2.0): 경첩 축 2 (x{F(g.KNL['near'][0])}·{F(g.KNR['near'][1])}에서) + 다리 축 1 (−x에서) + 여분 1"],
            ["M2.5×6", str(hw.get("M2.5×6", "")), f"화면 → 보스 (물림 {F(g.BO['engage'])}, 구멍 깊이는 받고 확인)"],
            ["M3×10", str(hw.get("M3×10", "")), f"ISO 7380: 뚜껑 → 레일 인서트 (y{F(g.SCREWS[0][1])}·{F(g.SCREWS[2][1])}), 자리파기 Ø{F(g.LID_SCREW['d_cbore'])}×{F(g.LID_SCREW['cbore_depth'])}"]]
    zt = K.table(v, 1.0, 81.0, ["부품", "개수", "쓰는 곳"], rows, [v.px(80), v.px(50), v.px(560)], row_px=17, size_px=9.5)
    lines = [f"• {p}" for p in g.PRINTED]
    lines.append(f"\u00a0\u00a0\u00a0화면 덮개는 접은 화면 위, 받침 테두리({F(g.CR['size'][0])}×{F(g.CR['size'][1])})에 얹힘 (CAD_SPEC E-3)")
    note_lines(v, lines, 1.0, zt - v.px(18), line_px=15.0, size_px=9.4, cls="lt")
    return v


# ================================================================ t06 wiring: DSI FFC + power
BEND_RUNS = ("parts.run_y", "parts.run_x", "parts.drop")      # the three 90 deg bends: hole -> +y, -x -> drop, drop -> landing


def panel_ffc_strip():
    segs = g.RIBSEG
    corr = [x for x in segs if x["kind"] == "corr"][0]["L"]
    nb = len(BEND_RUNS)
    g.check("ribbon corner correction = 3 bends x (pi/2 - 2) R", abs(corr - nb * (math.pi / 2 - 2) * g.RB["bend_R"]) < 0.01, corr)
    v = View(-8.0, -40.0, 330.0, 50.0, px_width=1480, pad_px=6)
    panel_title(v, -7.5, 47.5, f"A. DSI FFC 펼친 길이 — 화면 ZIF → Pi 5 CAM/DISP 1 (W605 {g.CABLES['W605']['길이']}, 필요 {F(g.RB['total'])}, 여유 {F(g.RB['margin'])})", size_px=12)
    h = g.RB_W
    pos = 0.0
    ticks = [(0.0, "0")]
    labs = []
    for sg in segs:
        if sg["kind"] == "corr":
            continue
        L = sg["L"]
        if sg["src"] in BEND_RUNS:
            L = L + corr / nb                                   # each rounded 90 deg bend shortens the run next to it
        a, b = pos, pos + L
        cls = {"ins": "m-lead", "fold": "m-cloth", "loop": "m-brass"}.get(sg["kind"], "ffc")
        v.rect(a, 0.0, b - a, h, cls=cls)
        labs.append(((a + b) / 2, sg))
        pos = b
        ticks.append((pos, F(pos, 1)))
    cable = g.RB["cable"]
    v.rect(pos, 0.0, cable - pos, h, cls="faintfill")
    T(v, (pos + cable) / 2, h / 2 - 1.2, f"여유 {F(g.RB['margin'])}", size_px=9.5, anchor="middle")
    T(v, (pos + cable) / 2, -3.0, "여유 고리: 클립과 45° 접기 사이", size_px=8.8, anchor="middle", cls="tx-s")
    T(v, (pos + cable) / 2, -6.2, f"(뚜껑 밑, O4 정비 때 풀림 — F)", size_px=8.8, anchor="middle", cls="tx-s")
    # contacts: screen end on the top face, Pi end on the bottom face (B = reverse)
    for k in range(0, 22, 3):
        yk = 0.6 + k * (h - 1.2) / 21
        v.line(0.0, yk, g.RB["screen_end_insert"], yk, cls="wire5")
    v.rect(cable - g.RB["pi_end_insert"], 0.0, g.RB["pi_end_insert"], h, cls="ph2")
    T(v, -7.5, h / 2 - 1.0, "접점", size_px=9, anchor="start", cls="lt")
    T(v, -7.5, h / 2 - 4.5, "(앞면)", size_px=8.6, anchor="start", cls="tx-s")
    T(v, cable + 1.0, h / 2 + 1.0, "접점 (뒷면)", size_px=9, anchor="start")
    T(v, cable + 1.0, h / 2 - 2.5, "= B형", size_px=9, anchor="start", cls="ttl")
    ordy(v, [(t, 0.0, "") for t, _ in ticks] + [(cable, 0.0, "리본 끝")], -9.0, gap_px=11.5, label_px=8.6, prefix="")
    gap = v.px(13.0)
    xs = [mx for mx, _ in labs]
    pos_ = K.kit._pav([x - i * gap for i, x in enumerate(xs)])
    pos_ = [p_ + i * gap for i, p_ in enumerate(pos_)]
    row = h + 5.0
    for (mx, sg), px_ in zip(labs, pos_):
        v.line(mx, h + 0.4, mx, row, cls="ex")
        v.line(mx, row, px_, row + 4.0, cls="ex")
        v.text(px_ + v.px(3.3), row + 4.0 + v.px(3), f"{sg['lab']} {F(sg['L'])}", cls="ot", anchor="start", size_px=8.8, rot=-90)
    T(v, -7.5, -34.5, f"굽힘 모서리 보정 {F(corr)} = 90° 굽힘 {nb}곳 × (π/2 − 2)·R{F(g.RB['bend_R'])} → 뚜껑 밑 +y·−x·내려감 길에서 뺌 · 접기 말림 = π·R{F(g.RB['fold_roll_R'])} · "
      f"ZIF 안 {F(g.RB['screen_end_insert'])}·{F(g.RB['pi_end_insert'])} (Pi 쪽 = 커넥터 깊이 {F(g.PI['disp1']['depth'])} − 0.3) · U자 없음 (90° 굽힘 두 번)", size_px=9.2, cls="tx-s")
    T(v, 200.0, -30.0, f"폭 {F(g.RB_W)} · 두께 {F(g.RB['ffc_t'])} · 22핀 0.5 mm", size_px=9.5)
    return v


def panel_route_side():
    th = g.TH_USE
    L = g.LID
    Y0 = g.H[0] - 20.55
    Y1, Z0 = Y0 + 94.0, g.PI["board_top_z"] - 8.1
    Z1 = Z0 + 134.0
    v = View(Y0, Z0, Y1, Z1, px_width=560, pad_px=6)
    frame_check("t06 B side route", (Y0, Y1, Z0, Z1), (min(p_[1] for p_ in g.RB["waypoints"]), max(p_[1] for p_ in g.RB["waypoints"]), min(p_[2] for p_ in g.RB["waypoints"]), g.P(g.S["fpc"]["pin_u_centre"], 0, th)[1]))
    pid = K.pid_set(v)
    panel_title(v, Y0 + 0.5, Z1 - 2.0, f"B. 리본 길 옆에서 (x{FR(*g.HO['x'], 0)} 쪽, {F(th)}°)", size_px=11.5)
    i0 = len(v.el)
    adds, subs = lid_section_at(g.HOLE_XC)
    K.rings_h(v, adds, "m-lid", pid["lid"], subs=subs)
    v.poly(g.knuckle_profile(), cls="vis")
    for r_ in cradle_outline(th):
        v.poly(r_, cls="cr-ph")
    a, b = g.P(0, 0, th), g.P(g.GH, 0, th)
    v.line(a[0], a[1], b[0], b[1], cls="glass")
    draw_pi(v)
    kz = g.PL["keepout_zones"]
    v.rect(kz["dsi"]["y"][0], kz["dsi_z"][0], kz["dsi"]["y"][1] - kz["dsi"]["y"][0], kz["dsi_z"][1] - kz["dsi_z"][0], cls="zone")
    rib = ribbon_side(th)
    v.poly(rib, cls="rib", closed=False)
    v.poly(power_side(rib), cls="pw", closed=False)
    cp_ = g.CL["pad"]
    v.rect((cp_["y"][0] + cp_["y"][1]) / 2 - g.CLIP_SIZE[1] / 2, g.CLIP_Z[0], g.CLIP_SIZE[1], g.CLIP_Z[1] - g.CLIP_Z[0], cls="leg-ph")
    clip_scene(v, i0, Y0, Y1, Z0, Z1 - 5)
    gw = (g.CR["w_screen_back"] + g.PL_IN) / 2
    zif = g.P(g.S["fpc"]["pin_u_centre"], gw, th)
    ex = g.P(g.U0, gw, th)
    wp = g.RB["waypoints"]
    rr, ri = g.RR, g.RI
    ly = Y0 + 56.0
    lead(v, zif[0], zif[1], ly, Z0 + 124.0, f"화면 ZIF → +x {F(g.RB['stiffener_out'])} → 45° 말아 접기 R{F(g.RB['fold_roll_R'])}", size_px=9, cls="rbt")
    lead(v, g.P(20, gw, th)[0], g.P(20, gw, th)[1], ly, Z0 + 114.0, f"받침 안 틈 w{FR(g.GB, g.PL_IN)}로 {F(g.RB['in_cradle_parts']['descend_to_cradle_bottom'])} 내려감", size_px=9, cls="rbt")
    lo = g.RB["loop"]
    lead(v, ex[0] - 2.0, ex[1] - 4.0, ly - 14.0, Z0 + 102.0, f"경첩 고리 {F(lo['length'])} (줄 {F(lo['chord']['use'])} 세움 · {F(lo['chord']['fold'])} 접음, R{F(min(lo['single_arc_R'].values()))} 이상)", size_px=9, cls="rbt")
    lead(v, rr["run0"][1], rr["run0"][2], ly, Z0 + 90.0, f"뚜껑 구멍 → R{F(g.RB['bend_R'])} → +y {F(g.RB['parts']['run_y'])} (z{F(g.RB['z_run'])}, 클립에 물림)", size_px=9, cls="rbt")
    lead(v, rr["drop"][1], (rr["drop"][2] + rr["drop_b"][2]) / 2, ly, Z0 + 78.0, f"45° 접기 → −x {F(g.RB['parts']['run_x'])} → 기둥 x{F(rr['drop'][0])} 안 {F(g.RB['parts']['drop'])} 내려감", size_px=9, cls="rbt")
    lead(v, rr["mouth"][1], rr["mouth"][2], ly - 14.0, Z0 + 66.0, f"R{F(g.RB['bend_R'])} → HDMI 위 z{F(ri['z_land'])} → {F(ri['approach_deg'])}°로 입구 ({F(g.RB['pi_end_insert'])} 꽂음)", size_px=9, cls="rbt")
    T(v, Y0 + 0.5, Z0 + 3.0, f"분홍 점선 = 전원선 (클립 홈 z{F(g.PW['waypoints'][1][2])}) · 주황 점선 네모 = DSI 지킴 구역 z{FR(*g.PL['keepout_zones']['dsi_z'])} · 보라 점선 = 클립", size_px=9, cls="tx-s")
    T(v, Y0 + 0.5, Z0 + 7.0, f"선이 가장 앞으로 나오는 곳 약 y{F(g.CK['cables_fwd_min_y'])} (금지선 y{F(g.KO['y_max'])})", size_px=9, cls="kot")
    return v


def panel_route_plan():
    X0 = min(g.GP2[0], g.PI["board_x"][0]) - 4.0
    X1 = max(g.HO["x"][1], g.KNR["all"][1]) + 28.6
    Y0 = g.HO["y"][0] - 6.55
    Y1 = max(g.GP2[1], g.V["band_y"][1]) + 1.0
    v = View(X0, Y0, X1, Y1, px_width=912, pad_px=6)
    frame_check("t06 C plan route", (X0, X1, Y0, Y1), (min(q[0] for q in g.RB["waypoints"] + g.PW["waypoints"]), max(q[0] for q in g.RB["waypoints"] + g.PW["waypoints"]),
                                                     min(q[1] for q in g.RB["waypoints"] + g.PW["waypoints"]), max(q[1] for q in g.RB["waypoints"] + g.PW["waypoints"])))
    pid = K.pid_set(v)
    panel_title(v, X0 + 0.5, Y1 - 2.5, "C. 뚜껑 밑 길 위에서 (리본 = 주황 띠, 전원선 = 분홍)", size_px=11.5)
    i0 = len(v.el)
    draw_lid_plan(v, pid, show_under=True, show_routes=True)
    clip_scene(v, i0, X0, X1, Y0, Y1 - 6)
    rp = g.ribbon_plan_rects()
    fx, fy = rp["fold"]
    wp = g.RB["waypoints"]
    xr_ = X1 - 40.0
    lead(v, rp["hole"][0], rp["hole"][1], xr_, Y0 + 14.0, f"구멍 {F(g.HO['x'][1] - g.HO['x'][0])}×{F(g.HO['y'][1] - g.HO['y'][0])} (3핀 이음 통과)", size_px=9)
    lead(v, fx + g.RB_W / 2, fy, xr_, Y0 + 40.0, f"45° 접기 R{F(g.RB['fold_roll_R'])} — 면이 뒤집힘", size_px=9, cls="rbt")
    lead(v, rp["drop"][0], rp["drop"][1], X0 + 62.0, Y1 - 14.0, f"x{F(g.RR['drop'][0])}에서 기둥 안으로 {F(g.RB['parts']['drop'])} 내려감 → HDMI 위 → 입구 x{F(g.RR['mouth'][0])} ({g.MOUTH_TXT} 방향 입구)", size_px=9, cls="rbt")
    lead(v, g.CL["pins"][1][0], g.CL["pins"][1][1], xr_, Y0 + 26.0, f"클립 핀 Ø{F(g.PIN_D)} · 전원선 홈 x{FR(*g.WG['x'])}", size_px=9)
    lead(v, g.GP2[0], g.GP2[1], X0 + 4.0, Y1 - 26.0, f"GPIO 핀 2 (5 V) · 6 (GND)", size_px=9, cls="pwt")
    lead(v, g.PW["waypoints"][1][0], Y1 - 36.0, xr_, Y1 - 36.0, f"전원선 x{F(g.PW_X)} → y{F(g.PW['waypoints'][2][1])}", size_px=9, cls="pwt")
    T(v, X0 + 0.5, Y0 + 2.0, f"리본 폭 {F(g.RB_W)}, 굽힘 R{F(g.RB['bend_R'])} 이상 (고정 부분) · 날카롭게 꺾지 않음", size_px=9, cls="tx-s")
    return v


def panel_power_harness():
    v = View(0.0, -44.0, 350.0, 60.0, px_width=1480, pad_px=6)
    panel_title(v, 0.5, 57.5, f"D. 화면 전원선 — Pi 헤더 핀 2·6 → 점퍼 → 동봉선 → MX1.25 (회로도 SCH-06 번호, 필요 {F(g.PW['total'])} / 있는 길이 {FR(*g.PW['available'], 0)})", size_px=12)
    Yr, Yb = 30.0, 22.0                     # red / black wire rows
    boxes = [("A603", 4.0, 34.0), ("P603", 44.0, 54.0), ("X601", 110.0, 120.0), ("X602", 122.0, 132.0), ("X603", 186.0, 196.0), ("X604", 198.0, 210.0),
             ("P604", 268.0, 278.0), ("A605", 290.0, 344.0)]
    for nm, a, b in boxes:
        hi = 44.0 if nm in ("A603", "A605") else 36.0
        lo = 12.0 if nm in ("A603", "A605") else 16.0
        v.rect(a, lo, b - a, hi - lo, cls="conn")
        T(v, (a + b) / 2, hi + 1.5, nm, size_px=10, anchor="middle", cls="ttl")
        T(v, (a + b) / 2, lo - 4.0, g.BOM[nm]["값"][:24], size_px=8.6, anchor="middle", cls="tx-s")
    # header pin grid on A603 (pins 1..6: odd row near the board edge)
    pp = 4.0
    for k in range(1, 7):
        col, row = (k - 1) // 2, (k - 1) % 2
        cx, cy = 12.0 + col * pp * 1.6, 26.0 + row * pp * 1.6
        cls = "wire5" if k == 2 else ("wireg" if k == 6 else "ln")
        v.circle(cx, cy, 1.2, cls=cls)
        T(v, cx, cy + 2.0, str(k), size_px=8, anchor="middle")
    T(v, 5.0, 16.0, f"핀 2 = 5 V · 6 = GND (4 안 씀)", size_px=8.6)
    # wires
    def wire(a, b, row, cls):
        v.line(a, row, b, row, cls=cls)
    for (a, b) in ((34.0, 44.0), (54.0, 110.0), (132.0, 186.0), (210.0, 268.0), (278.0, 290.0)):
        wire(a, b, Yr, "wire5")
        wire(a, b, Yb, "wireg")
    for nm, (a, b) in (("W606", (54.0, 110.0)), ("W607", (132.0, 186.0)), ("W608", (210.0, 268.0))):
        c = g.CABLES[nm]
        T(v, (a + b) / 2, Yr + 3.5, f"{nm} {c['길이']}", size_px=9.5, anchor="middle", cls="ttl")
        T(v, (a + b) / 2, Yb - 5.5, c["종류"][:22], size_px=8.6, anchor="middle", cls="tx-s")
    # pin numbers at each connector (netlist)
    for nm, a, b in boxes[1:-1]:
        for net, row in (("+5V_PI", Yr), ("GND", Yb)):
            pn = g.pin_of(nm, net)
            T(v, (a + b) / 2, row - 1.0, pn, size_px=8.6, anchor="middle")
    T(v, (boxes[5][1] + boxes[5][2]) / 2, (Yr + Yb) / 2 - 1.0, "2 빈칸", size_px=8, anchor="middle", cls="tx-s")
    for net, row in (("+5V_PI", Yr), ("GND", Yb)):
        T(v, 292.0, row - 1.0, f"{g.pin_of('A605', net)} {'5V' if net != 'GND' else 'GND'}", size_px=8.6)
    T(v, 300.0, 36.0, "Waveshare 7-DSI-TOUCH-C", size_px=9)
    T(v, 300.0, 16.0, f"약 {F(g.N['power']['S_W'])} W ({F(g.N['power']['screen_A_5V'])} A)", size_px=8.8)
    T(v, 136.0, 44.0, f"빨강 = 5 V (+5V_PI) · 검정 = GND · ⇄ = 꽂는 곳", size_px=9, anchor="start")
    # length bar under: the path the wire follows vs the cable pieces
    base = -14.0
    scale = 0.6
    path = g.PW["parts"]
    x = 4.0
    v.text(0.5, base + 6.5, f"선이 지나는 길 (화면 MX1.25 → GPIO) = {F(g.PW['total'])}", cls="lt", anchor="start", size_px=9.5)
    marks = [(x, "0")]
    for i_, (key, lab) in enumerate(g.PWSEG):
        L = path[key] * scale
        v.rect(x, base, L, 3.0, cls="m-print2")
        T(v, x + L / 2, base - (3.5 if i_ % 2 == 0 else 7.0), f"{lab} {F(path[key])}", size_px=8.4, anchor="middle")
        x += L
        marks.append((x, F(x - 4.0)))
    ws = g.WS_EST
    y2 = base - 21.0
    halo1(v, 0.5, y2 + 6.5, f"선 조각: W608 동봉 {FR(*ws, 0)} (추정) + W607 {F(g.JUMPER_MM[1])} + W606 {F(g.JUMPER_MM[0])} = {FR(*g.PW['available'], 0)} → 남는 {FR(g.PW['available'][0] - g.PW['total'], g.PW['available'][1] - g.PW['total'])}은 뚜껑 밑에 감음",
           cls="lt", anchor="start", size_px=9.5)
    k_ = scale
    v.rect(4.0, y2, ws[0] * k_, 3.0, cls="m-cr")
    v.rect(4.0 + ws[0] * k_, y2, (ws[1] - ws[0]) * k_, 3.0, cls="cr-ph")
    v.rect(4.0 + ws[1] * k_, y2, g.JUMPER_MM[1] * k_, 3.0, cls="m-print")
    v.rect(4.0 + (ws[1] + g.JUMPER_MM[1]) * k_, y2, g.JUMPER_MM[0] * k_, 3.0, cls="m-print2")
    for xv, lab in ((ws[0], "W608 짧으면"), (ws[1], "W608 길면"), (ws[1] + g.JUMPER_MM[1], "+ W607"), (ws[1] + sum(g.JUMPER_MM), "+ W606")):
        T(v, 4.0 + xv * k_, y2 - 3.5, f"{F(xv)} {lab}", size_px=8.4, anchor="middle")
    v.line(4.0 + g.PW["total"] * k_, base + 3.0, 4.0 + g.PW["total"] * k_, y2 - 1.0, cls="cl")
    v.line(4.0 + g.PW["ws_cable_joint_needs"] * k_, base + 3.0, 4.0 + g.PW["ws_cable_joint_needs"] * k_, y2 - 7.0, cls="ko")
    T(v, 4.0 + g.PW["ws_cable_joint_needs"] * k_ + 1.0, y2 - 9.0, f"동봉선 ≥ {F(g.PW['ws_cable_joint_needs'])}이면 X603⇄X604 이음이 뚜껑 밑, 짧으면 경첩 고리 안 → 열수축튜브 ({F(g.HO['x'][1] - g.HO['x'][0])}×{F(g.HO['y'][1] - g.HO['y'][0])} 구멍 통과)", size_px=9, cls="kot")
    return v


def panel_cable_table():
    v = View(0.0, 0.0, 350.0, 66.0, px_width=1480, pad_px=6)
    panel_title(v, 0.5, 63.5, "E. 선 목록 (회로 cables.csv) · 리본 종류 · 설정", size_px=12)
    cols = ["번호", "종류", "길이", "한쪽", "다른 쪽", "심선", "필요 / 여유"]
    need = {"W605": f"{F(g.RB['total'])} / {F(g.RB['margin'])}", "W606": f"합계 {F(g.PW['total'])}", "W607": "(전원 3조각)", "W608": f"≥ {F(g.PW['ws_cable_joint_needs'])}이면 이음이 뚜껑 밑"}
    rows = [[w, g.CABLES[w]["종류"], g.CABLES[w]["길이"], g.CABLES[w]["한쪽"], g.CABLES[w]["다른 쪽"], g.CABLES[w]["심선"], need[w]] for w in ("W605", "W606", "W607", "W608")]
    zt = K.table(v, 0.5, 58.0, cols, rows, [v.px(q) for q in (50, 330, 80, 190, 200, 150, 220)], row_px=17, size_px=9)
    sw_ = g.DJ["software"].split("\n")
    lines = [f"• 리본 종류: 이 길(받침 안 45° 접기 1 + 뚜껑 밑 45° 접기 1, 90° 굽힘은 면을 안 뒤집음)을 면 추적으로 계산 → {g.RB['ffc_type']} (접기 {g.RB['folds_total']}번). "
             f"커넥터가 왼쪽으로 확인되면 약 {F(g.N['variants']['connector_mirrored']['ribbon']['total'])} mm, {g.N['variants']['connector_mirrored']['ribbon']['ffc_type']} (예비로 산 A형).",
             f"• Waveshare 표준 연결(화면 뒤 Pi, U자)도 같은 추적으로 {g.N['ffc_tracker_check_waveshare_std']} → Waveshare가 Pi 5에 반대면 리본을 쓰는 것과 맞음.",
             "• " + sw_[0].replace("`", ""), ("• " + sw_[3].replace("`", "")) if len(sw_) > 3 else "",
             f"• 전원: Pi에서 나가는 방향으로만 받음 (D16). 화면 쪽에 다른 5 V를 넣지 않음. 3핀 하우징 1 빨강 · 2 빈칸 · 3 검정은 통전 검사로 확인 후 꽂음."]
    note_lines(v, [l for l in lines if l], 0.5, zt - v.px(18), line_px=15.0, size_px=9.3, cls="lt")
    return v


def panel_service():
    """F. O4 service (CAD request: the ribbon must be easy to unplug): steps and lift from numbers service_O4."""
    sv = g.SVC
    v = View(0.0, 0.0, 350.0, 40.0, px_width=1480, pad_px=6)
    panel_title(v, 0.5, 37.5, f"F. O4 정비 — 화면 뚜껑 열기 (O4 USB 플러그가 이 뚜껑 밑에 있음, CAD 요청 \"리본을 쉽게 뽑게\")", size_px=12)
    steps = [f"{i + 1}. {t}" for i, t in enumerate(sv["steps_ko"])]
    half = (len(steps) + 1) // 2
    note_lines(v, steps[:half], 0.5, 31.0, line_px=15.5, size_px=9.6, cls="lt")
    note_lines(v, steps[half:], 175.0, 31.0, line_px=15.5, size_px=9.6, cls="lt")
    note_lines(v, [f"• 리본 여유 {F(g.RB['margin'])}는 {sv['spare_loop_where']} → 클립에서 Pi까지 풀린 리본 약 {F(sv['free_ribbon_after_clip'])} (여유 포함 {F(sv['with_spare'])}), "
                   f"꽂은 채 약 {F(sv['lift_with_ribbon_plugged'], 0)} mm 들 수 있음 (곧은 선 − 굽힘 10, 추정).",
                   "• 뽑는 곳은 Pi 쪽 CAM/DISP 1. 화면 쪽 ZIF는 받침 안(점검창 덮개 밑)이라 정비 때 건드리지 않음. 되돌릴 때 B형 방향(접점 면)을 확인."],
               0.5, 31.0 - half * v.px(15.5) - v.px(8), line_px=15.5, size_px=9.6, cls="tx-s")
    return v


def sheet_t06():
    n = 6
    rows = [[panel_ffc_strip()], [panel_route_side(), panel_route_plan()], [panel_power_harness()], [panel_cable_table()], [panel_service()]]
    base = os.path.join(OUT, "t06_wiring")
    K.page(rows, base, sub_head(n, "배선 — DSI 리본 길(접기·길이·굽힘·A/B형) · 화면 전원선(GPIO 2·6 → 점퍼 → 3핀 → MX1.25) · 선 목록"),
           subtitle=SRC_LINE + "\n부품 번호(A603·P603·X601~X604·P604·A605·W605~W608)는 회로도 SCH-06 (touch3/pcb/netlist)과 같음. 커넥터 쪽·동봉선 길이는 추정 (T3 참고).",
           foot=foot_lines())
    add_sheet(n, os.path.basename(base), "배선 (DSI 리본 · 화면 전원 · O4 정비)",
              f"DSI FFC 22핀 0.5 mm {F(g.RB['cable'], 0)} mm {g.RB['ffc_type'][0]}형: 펼친 길이 {F(g.RB['total'])} (구간별, 접기 {g.RB['folds_total']}, 90° 굽힘 R{F(g.RB['bend_R'])} 3곳, U자 없음, 여유 {F(g.RB['margin'])}), "
              f"옆·위에서 본 길 (뚜껑 밑 z{F(g.RB['z_run'])} 클립에 물림 → 기둥 x{F(g.RR['drop'][0])} → HDMI 위 z{F(g.RI['z_land'])} → {F(g.RI['approach_deg'])}°로 입구, {F(g.RB['pi_end_insert'])} 꽂음), 접점 면. "
              f"전원선: Pi 헤더 핀 2·6 → W606 F/F {g.CABLES['W606']['길이']} → W607 M/M {g.CABLES['W607']['길이']} → X604 3핀(1 빨강·2 빈칸·3 검정) → W608 동봉선 → P604 MX1.25 → A605, "
              f"필요 {F(g.PW['total'])} / {FR(*g.PW['available'], 0)} (클립 홈 z{F(g.PW['waypoints'][1][2])}). 선 목록, 설정 한 줄, O4 정비 순서 (꽂은 채 약 {F(g.SVC['lift_with_ribbon_plugged'], 0)} mm 들기).")


# ================================================================ main
SHEET_FN = dict(t01=sheet_t01, t02=sheet_t02, t03=sheet_t03, t04=sheet_t04, t05=sheet_t05, t06=sheet_t06)


def main(argv):
    names = argv or list(SHEET_FN)
    for nm in names:
        SHEET_FN[nm]()
    for base, au in sorted(K.AUDIT.items()):
        g.check(f"{base[:3]}: no two texts overlap (page text boxes, {au['n_text']} texts)", not au["overlaps"], au["overlaps"][:8])
        g.check(f"{base[:3]}: no text runs out of its panel", not au["outside"], au["outside"][:8])
        for o in au["overlaps"]:
            print("  OVERLAP", base[:3], o)
        for o in au["outside"]:
            print("  OUTSIDE", base[:3], o)
    # drawings.json (merge with an existing one so a partial run keeps the other sheets)
    fj = os.path.join(OUT, "drawings.json")
    old = json.load(open(fj)) if os.path.exists(fj) else {"sheets": []}
    by = {s["id"]: s for s in old.get("sheets", [])}
    for s in SHEETS:
        by[s["id"]] = s
    meta = dict(project=f"Toccata R31 터치스크린 수정 {g.REV}판 (B1 · L2) · 도면 고침 1", date=g.DATE, rev=g.REV, sources=g.SOURCES,
                checks=g.CHECKS, sheets=[by[k] for k in sorted(by)])
    json.dump(meta, open(fj, "w"), ensure_ascii=False, indent=1)
    bad = [c for c in g.CHECKS if not c["ok"]]
    print("sheets", [s["id"] for s in SHEETS], "checks", len(g.CHECKS), "failed", bad)


if __name__ == "__main__":
    main(sys.argv[1:])
