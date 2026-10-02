"""Toccata rear bar / body as Part instances (world coordinates, assembled pose).

Sources (the only numeric sources):
  spec/body_speakers.json        speaker parts L/R (5 okoume panels + printed baffle each), grille + spacer ring, EVA
                                 gasket, XT30 holders, feet + 4 mm spacers, dovetail blocks, toggle latch L64
  spec/body_centre_unit.json     centre unit (11 okoume panels), CU tray (re-laid component bosses), CU lid, I/O plate,
                                 lid corner supports + L65 magnets, power-bank holder, key-storage insert, small-parts box
  spec/keyaction_features_frame.json   cheek extents + the M3 bolt seats (bracket.proposal_v4) for the v4 bracket

Decisions applied (task):
  - feet at the drawing positions y299 / y379 (x from body_speakers feet[]); the 4 mm foot spacer appears in both spec
    files and is emitted once (14 pcs)
  - the EVA 3T strip between centre unit and speaker parts is left out on purpose: the 2 dovetails + the toggle latch fix
    the joint, and a 3 mm strip would push the female grooves 3 mm away from the males so they could not drop in
    (overall width stays 1254, A05)
  - CU tray / I/O plate component layout = body_centre_unit.json re-layout (supersedes drawing 10)
  - v3 A12 flat bracket cannot mount in v4 -> new L bracket (printed, L and R), see bracket(); its bolt x = the cheek
    seats the key-action frame generator cuts (BRK_SEAT_X), left leg notched for the headphone cables
  - review fixes (2026-09-30): speaker-wire holes x140 / x1082 (WIRE_HOLE_X), CU-tray pilot pads full height from z22,
    XT30 holder R screws y235 (XT30R_*), speaker-side rear ear screw off the back-panel end grain (REAR_EAR_*), latch seats
    9.5 thick (LATCH_SEAT_Y), grille spacer ring 11 (GRILLE_FACE_Y), CU-tray rib pitch constant TRAY_RIB_PITCH
Not modelled: plywood-to-plywood glue, wood screws other than the bracket screw, rubber-foot screws + washers,
dovetail / XT30 / tray / I/O / holder / insert 13 mm screws, latch M3x10 screws, board screws (F05..F10).

Every printed part: kind='print', one body, lies on the bed via to_bed(orient(...)), print folder 05_본체출력물.
Horizontal holes in printed parts are teardrops whose apex points up in the print orientation.
"""
import json
import math
import os

from manifold3d import CrossSection, FillRule, Manifold

from cadlib import box, cone_z, cyl_x, cyl_y, cyl_z, diff, mirror_x, orient, prism_x, prism_y, prism_z, rot_x, rot_y, \
    to_bed, union
from parts import COLORS, Part

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

FOLDER = "05_본체출력물"
SRC_S = "spec/body_speakers.json"
SRC_C = "spec/body_centre_unit.json"
SRC_F = "spec/keyaction_features_frame.json"

G_SPK = {"L": "스피커 파트 L", "R": "스피커 파트 R"}
G_CU = "가운데 유닛"
G_CUP = "CU 칸 출력물"
G_JOIN = "뒷바 이음·발"
G_BR = "방진 브래킷"

PETG = "PETG 회색"
PLY = "오꾸메 합판 11.5T"
MIRROR_X = 611.0          # speaker parts L/R are mirror images about x = (-16 + 1238) / 2

R_NONE = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_FLIP = rot_x(180)       # top face (max z) on the bed
R_YMIN = rot_x(90)        # print z = world y  -> the min-y face on the bed
R_YMAX = rot_x(-90)       # print z = -world y -> the max-y face on the bed
R_XMAX = rot_y(90)        # print z = -world x -> the max-x face on the bed
R_XMIN = rot_y(-90)       # print z = world x  -> the min-x face on the bed



def tray_tabs(fe):
    """A8: the spec's left tab at y240..260 puts the 8-ho screw head (about Ø8 x 3 on the tab face x528.75) onto the PED
    board edge (x531, z38.5..40.1). Both left tabs move into the free wall stretch between the PED board (y..294) and the
    Pi 5 (y336..): y298..314 and y318..334, 16 wide. Right tabs stay as specified."""
    out = []
    for t in fe["divider_screw_tabs"]["tabs"]:
        t = json.loads(json.dumps(t))
        if t["side"] == "left":
            if t["box"]["y"][0] < 300:
                t["box"]["y"] = [298.0, 314.0]
                t["hole_center"][1] = 306.0
            else:
                t["box"]["y"] = [318.0, 334.0]
                t["hole_center"][1] = 326.0
        out.append(t)
    return out

def _load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


# ------------------------------------------------------------------ geometry helpers

def B(b, dx=0.0, dy=0.0, dz=0.0):
    """spec box {x:[..], y:[..], z:[..]} -> solid."""
    return box(b["x"][0] + dx, b["x"][1] + dx, b["y"][0] + dy, b["y"][1] + dy, b["z"][0] + dz, b["z"][1] + dz)


def _nseg(d):
    return int(max(24, min(96, math.ceil(math.pi * d / 0.35))))


def _hull2d(pts):
    """convex hull, counter-clockwise (monotone chain)."""
    pts = sorted(set((round(a, 9), round(b, 9)) for a, b in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def tear_pts(c1, c2, d, apex=None):
    """circle (+ 45 deg roof point toward `apex`, a 2D direction in the same plane) as a CCW polygon."""
    n = _nseg(d)
    r = d / 2.0
    pts = [(c1 + r * math.cos(2 * math.pi * i / n), c2 + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    if apex is not None:
        ax, ay = apex
        L = math.hypot(ax, ay)
        pts.append((c1 + ax / L * r * math.sqrt(2.0), c2 + ay / L * r * math.sqrt(2.0)))
    return _hull2d(pts)


def _prism(axis, poly, a0, a1):
    return {"x": prism_x, "y": prism_y, "z": prism_z}[axis](poly, a0, a1)


def hole(axis, c1, c2, a0, a1, d, apex=None):
    """round hole along axis ('x': c=(y,z), 'y': c=(x,z), 'z': c=(x,y)); apex = teardrop roof direction or None."""
    return _prism(axis, tear_pts(c1, c2, d, apex), a0, a1)


def slot_hole(axis, p, q, a0, a1, d, apex=None):
    """hull of two (teardrop) circles at p and q (2D points in the axis plane)."""
    return _prism(axis, _hull2d(tear_pts(p[0], p[1], d, apex) + tear_pts(q[0], q[1], d, apex)), a0, a1)


def stadium_y(cx, cz, w, h, y0, y1):
    """stadium opening w (x) x h (z) through y0..y1."""
    r = (w - h) / 2.0
    return slot_hole("y", (cx - r, cz), (cx + r, cz), y0, y1, h)


def bed(m, R):
    return to_bed(orient(m, R))


def mx(m):
    """mirror a left-side solid to the right side (speaker parts, joints)."""
    return mirror_x(m, MIRROR_X)


def mxv(x):
    return 2 * MIRROR_X - x


class Out(list):
    def add(self, id, name_ko, name_en, kind, group, solid, color, material="", source="", note="",
            print_name=None, R=None, print_note="", dims=()):
        ps = bed(solid, R if R is not None else R_NONE) if kind == "print" else None
        self.append(Part(id=id, name_ko=name_ko, name_en=name_en, kind=kind, group=group, solid=solid, color=color,
                         material=material, print_name=print_name if kind == "print" else None,
                         print_folder=FOLDER if kind == "print" else None, print_solid=ps, print_note=print_note,
                         dims=list(dims), source=source, note=note))


# ------------------------------------------------------------------ speaker parts L / R

PANEL_KEYS = [("side_outer", "SIDEOUT", "side panel (outer)"), ("side_inner", "SIDEIN", "side panel (centre-unit side)"),
              ("back", "BACK", "back panel"), ("top", "TOP", "top panel"), ("bottom", "BOTTOM", "bottom panel")]

# speaker-wire hole Ø6 in the baffle (spec x6 / x1216, z38). At the spec x the wire, running down the 3 mm gap in front
# of the baffle, lands on the anti-vibration bracket's horizontal leg (x..9 / x1213..). Moved next to the centre-unit
# side edge (12.5 from it, mirror pair about MIRROR_X) so it drops in front of the XT30 holder (y218..).
WIRE_HOLE_X = {"L": 140.0, "R": 2 * 611.0 - 140.0}           # 140 / 1082
# XT30 holder R: block extended back from y238 to y243 and the 2 screws moved from y228 to y235 (see speaker_parts)
XT30R_Y_END, XT30R_SCREW_Y = 243.0, 235.0


def speaker_parts(S, out):
    panels = {p["id"]: p for p in S["panels"]}
    pr = {p["id"]: p for p in S["printed"]}
    for side in "LR":
        g = G_SPK[side]
        # ---- 5 okoume panels
        for key, tag, en in PANEL_KEYS:
            p = panels["spk%s_%s" % (side, key)]
            out.add("SPK%s-PLY-%s" % (side, tag), p["name_ko"], "speaker part %s %s" % (side, en), "plywood", g,
                    box(p["x"][0], p["x"][1], p["y"][0], p["y"][1], p["z"][0], p["z"][1]), COLORS["plywood"], PLY,
                    source=SRC_S + " panels " + p["id"] + " (%s)" % p["source"].split(";")[0])

        # ---- printed baffle
        b = pr["spk%s_baffle" % side]
        w = b["world"]
        y0, y1 = w["y"]
        solid = box(w["x"][0], w["x"][1], y0, y1, w["z"][0], w["z"][1])
        hs = {h["name_ko"]: h for h in b["holes"]}
        cut = hs["유닛 컷아웃"]
        cx, cz = cut["center"]["x"], cut["center"]["z"]
        cuts = [cyl_y(cx, cz, y0 - 0.01, y1 + 0.01, cut["dia"])]
        dp = hs["유닛 고정 파일럿 ×4 (유닛 장공 Ø4.8×6.8 자리)"]
        cuts += [cyl_y(c["x"], c["z"], y0 - 0.01, y0 + dp["depth"], dp["dia"]) for c in dp["centers"]]
        gp = hs["그릴 고정 파일럿 ×4"]
        cuts += [cyl_y(c["x"], c["z"], y0 - 0.01, y0 + gp["depth"], gp["dia"]) for c in gp["centers"]]
        wh = hs["스피커선 구멍"]
        whx, whz = WIRE_HOLE_X[side], wh["center"]["z"]      # moved off the spec x6 / x1216 (see WIRE_HOLE_X)
        cuts.append(cyl_y(whx, whz, y0 - 0.01, y1 + 0.01, wh["dia"]))
        baffle = diff(solid, cuts)
        xa, xb = w["x"]
        x_in = xb if side == "L" else xa                     # baffle edge on the centre-unit side
        pil = sorted(c["x"] for c in dp["centers"])
        gpl = sorted(c["x"] for c in gp["centers"])
        out.add("SPK%s-BAFFLE" % side, b["name_ko"], "speaker baffle (printed front panel) " + side, "print", g, baffle,
                COLORS["printed_body"], "PETG (검정 또는 회색)",
                source=SRC_S + " printed %s (157×11.5×210; 컷아웃 Ø94 중심 x%.0f z%.0f, 유닛 파일럿 4-Ø3.4 깊이 10 PCD115 45°, "
                               "그릴 파일럿 4-Ø3.4 깊이 9 (±57), 선 구멍 Ø6 spec x%.0f z38 → x%.0f로 옮김)"
                % (b["id"], cx, cz, wh["center"]["x"], whx),
                note="추정: 유닛 파일럿 깊이 10 (막힌 구멍, 밀폐), 그릴 파일럿 Ø3.4 깊이 9 (spec assumed_fields); "
                     "추정: 스피커선 구멍 Ø6을 spec x%.0f에서 x%.0f z%.0f로 옮김 - spec 자리는 선이 앞면 틈(y212~215)으로 내려가다 방진 브래킷 "
                     "눕힘 다리(z18~22) 위에 걸림. 새 자리는 가운데 유닛 쪽 모서리에서 %.1f, 밑 모서리에서 %.0f (구멍 벽 %.1f / %.0f), "
                     "유닛 파일럿(PCD115)·그릴 파일럿(±57)·컷아웃 Ø94와 45 mm 이상 떨어짐. 선은 틈을 따라 XT30 받침(y218~) 앞으로 "
                     "내려가 받침 밑 선 슬롯으로 들어감"
                     % (wh["center"]["x"], whx, whz,
                        abs(x_in - whx), whz - w["z"][0], abs(x_in - whx) - wh["dia"] / 2, whz - w["z"][0] - wh["dia"] / 2),
                print_name="스피커앞판_배플_" + side, R=R_YMIN,
                print_note="앞면(y215, 유닛·그릴 면)을 베드에 눕혀 출력(두께 11.5가 높이). 서포트 없음. 파일럿은 베드 면에서 막힌 구멍. "
                           "통판이 크고 속이 꽉 차 있으므로 벽(둘레) 4줄 + 채움(infill) 30~40 % (그리드/자이로이드) - 무게와 울림 사이 절충. "
                           "옆판 사이에 끼워 둘레를 목공본드(오공 205)로 밀봉, 선 구멍은 선을 넣은 뒤 본드로 막음",
                dims=[("x", xa, xb, "앞판 폭 157", 0), ("x", cx - 47, cx + 47, "컷아웃 Ø94", 1),
                      ("x", pil[0], pil[-1], "유닛 파일럿 PCD115 45° (Ø3.4 깊이 10)", 2),
                      ("x", gpl[0], gpl[-1], "그릴 파일럿 114 (Ø3.4 깊이 9)", 3),
                      ("x", min(xa, cx), max(xa, cx), "유닛 중심 x%.0f" % cx, 4),
                      ("x", min(whx, x_in), max(whx, x_in), "선 구멍 Ø6 중심 x%.0f (모서리에서 %.1f)" % (whx, abs(x_in - whx)), 5),
                      ("y", y0, y1, "두께 11.5", 0), ("y", y0, y0 + dp["depth"], "파일럿 깊이 10", 1),
                      ("z", w["z"][0], w["z"][1], "높이 210", 0), ("z", w["z"][0], cz, "유닛 중심 z142", 1),
                      ("z", w["z"][0], whz, "선 구멍 Ø6 중심 z%.0f" % whz, 2), ("z", cz - 57, cz + 57, "그릴 파일럿 114", 3)])

        # ---- grille + spacer ring (identical L / R: built at the origin and moved)
        gr = pr["spk_grille"]
        gw = gr["world"][side]
        gcx = (gw["x"][0] + gw["x"][1]) / 2.0
        gcz = (gw["z"][0] + gw["z"][1]) / 2.0
        gsolid = GRILLE.translate((gcx, 0, gcz))
        fy0, fy1 = GRILLE_FACE_Y
        ring = GRILLE_BACK_Y - fy1
        out.add("SPK%s-GRILLE" % side, gr["name_ko"], "hex grille + spacer ring " + side, "print", g, gsolid,
                COLORS["printed_body"], "PETG 회색 또는 검정",
                source=SRC_S + " printed spk_grille (130×130, 그릴 면 2.0 y203~205, 링 10 y205~215, 링 벽 12, 4-Ø4.5 ±57) "
                               "→ 링 %.0f로 늘려 그릴 면 y%.0f~%.0f" % (ring, fy0, fy1),
                note="추정: 육각 칸 맞은편 10 · 살 1.8 · 피치 11.8 (개구율 71.8 %%, spec lattice assumed), 칸 격자 중심 = 유닛 축, "
                     "링 안쪽 106×106을 벗어난 칸은 잘림(3 mm² 미만 조각은 막음); "
                     "추정: 스페이서 링 10 → %.0f - spec 링 10이면 유닛 플랜지 앞면(y208)과 그릴 면 뒤(y205) 사이가 3.0뿐이라 "
                     "유닛 고정 직결피스 8호 둥근머리(머리 높이 약 3)가 그릴 면에 닿음; 링 %.0f이면 %.1f 틈. "
                     "그릴 피스 8호 19 mm의 앞판 물림은 19 − (2 + %.0f) = %.0f (파일럿 깊이 9 안)"
                     % (ring, ring, 208.0 - fy1, ring, 19.0 - (fy1 - fy0) - ring),
                print_name="스피커그릴_링", R=R_YMIN,
                print_note="그릴 면(y%.0f)을 베드에 두고 링(%.0f)을 위로 세워 출력. 서포트 없음. 직결피스 8호 19 mm ×4로 앞판 파일럿에"
                           % (fy0, ring),
                dims=[("x", gw["x"][0], gw["x"][1], "그릴 130", 0), ("x", gcx - 53, gcx + 53, "링 안쪽 106", 1),
                      ("x", gcx - 57, gcx + 57, "고정 구멍 114 (Ø4.5)", 2),
                      ("y", fy0, fy1, "그릴 면 %.0f" % (fy1 - fy0), 0), ("y", fy1, GRILLE_BACK_Y, "링 %.0f" % ring, 1),
                      ("y", fy1, 208.0, "유닛 플랜지까지 %.1f (8호 머리 자리)" % (208.0 - fy1), 2),
                      ("z", gw["z"][0], gw["z"][1], "그릴 130", 0), ("z", gw["z"][0], gw["z"][0] + 12.0, "링 벽 12", 1)])

        # ---- EVA gasket (cut by knife)
        gk = pr["spk_gasket"]
        kw = gk["world"][side]
        kcx = (kw["x"][0] + kw["x"][1]) / 2.0
        kcz = (kw["z"][0] + kw["z"][1]) / 2.0
        r45 = 115.0 / 2.0 / math.sqrt(2.0)
        gasket = diff(B(kw), [cyl_y(kcx, kcz, 211.99, 215.01, gk["dims"]["inner_dia"])] +
                      [cyl_y(kcx + sx * r45, kcz + sz * r45, 211.99, 215.01, 4.8) for sx in (-1, 1) for sz in (-1, 1)])
        out.add("SPK%s-GASKET" % side, gk["name_ko"] + " " + side, "driver EVA gasket 3T " + side, "consumable", g, gasket,
                COLORS["rubber"], gk["material"],
                source=SRC_S + " printed spk_gasket (105×105×3, 안 Ø94, 4-Ø4.8 PCD115, y212~215)",
                note="추정: 안쪽 Ø94·바깥 105×105 (spec assumed) - EVA 3T 자투리를 칼로 재단")

        # ---- XT30 holder
        h = pr["xt30_holder_" + side]
        hw = h["world"]
        pk = h["pocket"]["world"]
        hh = h["holes"][0]
        zb, zt = hw["z"]
        cb_d, cb_h = hh["counterbore"]["dia"], hh["counterbore"]["depth"]
        if side == "L":
            # O1 USB-C plug overmould (module spec usb_plug, assumed:false: world x124.75..137.25 y196.8..221.8 z10.7..18.3)
            # and its R25 bend toward +x (geometry.json passage bend 25, centre (156, 221.8), z14.5 +-1.75) run through the
            # spec block x128..164 y218..238 -> pocket housing kept at the spec pocket (x146..164), screws moved to a block
            # behind the cable sweep (y250..262) joined by a bridge over the cable (z17..22).
            hold = union([box(146.0, hw["x"][1], hw["y"][0], hw["y"][1], zb, zt),        # pocket housing
                          box(146.0, 154.0, hw["y"][1] - 0.1, 250.1, 17.0, zt),         # bridge over the O1 cable (tube top z16.25)
                          box(132.0, 154.0, 250.0, 262.0, zb, zt)])                     # screw block
            pocket = box(pk["x"][0], pk["x"][1] + 0.5, pk["y"][0], pk["y"][1], pk["z"][0], pk["z"][1])
            slot = box(147.9, pk["x"][0] + 0.2, 225.0, 231.0, zb - 0.01, pk["z"][1])
            screws = [(138.0, 256.0), (148.0, 256.0)]
        else:
            # spec screws (x1079/1089, y228) sit 1.5 behind the bottom panel's front edge y226.5 (Ø4.5 hole edge in front of
            # it). A mirrored holder-L screw block (y250..262) would cut the O7 USB-C cable (bend R25 at z14.5 from x1118,
            # then down to the floor along y246.8..254.8), so the block is extended back to y243 only (cable >= 2 away)
            # and the screws move to y235 (8.5 inside the plywood face, 9.5 from the side panel x1069.5).
            hold = union([B(hw), box(hw["x"][0], hw["x"][1], hw["y"][1] - 0.01, XT30R_Y_END, zb, zt)])
            pocket = box(pk["x"][0] - 0.5, pk["x"][1], pk["y"][0], pk["y"][1], pk["z"][0], pk["z"][1])
            slot = box(pk["x"][1] - 0.2, mxv(148.3), 225.0, 231.0, zb - 0.01, pk["z"][1])
            screws = [(c["x"], XT30R_SCREW_Y) for c in hh["centers"]]
        hcuts = [pocket, slot]
        for (sx_, sy_) in screws:
            hcuts.append(cyl_z(sx_, sy_, zb - 0.01, zt + 0.01, hh["dia"]))
            hcuts.append(cyl_z(sx_, sy_, zb - 0.01, zb + cb_h, cb_d))
        holder = diff(hold, hcuts)
        hb = holder.bounding_box()
        hx = sorted(s[0] for s in screws)
        if side == "L":
            note = ("추정: spec 받침(x128~164 y218~238)은 O1 USB-C 플러그 몰드(x124.75~137.25 y≤221.8 z10.7~18.3, 모듈 spec assumed:false)와 "
                    "케이블 R25 굽힘 자리를 막음 → 홈 몸통은 spec 홈 자리(x146~164 y218~238) 그대로, 나사 2개는 케이블 뒤 블록(x132~154 y250~262, "
                    "나사 x138/x148 y256 - 아랫판 x≤152.5 안)으로 옮기고 케이블 위 다리(z17~22, 케이블 윗면 z16.25와 0.75 틈)로 이음; "
                    "선 슬롯 6(y)×3.7(x) 홈 뒤끝에서 밑면까지")
            src = SRC_S + " printed xt30_holder_L (홈 12.6×10.8×5.6 x151.4~164 y222.6~233.4 z12.2~17.8 입구 +x; 2-Ø4.5 + 자리 Ø9 깊이 11); " \
                  "spec/electronics_modules.json usb_plug + usb_cable (R25 sweep)"
            dims = [("x", hb[0], hb[3], "전체 %.0f" % (hb[3] - hb[0]), 0), ("x", pk["x"][0], pk["x"][1], "홈 12.6 (XT30U-F 12.4)", 1),
                    ("x", hx[0], hx[1], "나사 간격 10 (Ø4.5, 자리 Ø9)", 2), ("x", 146.0, hw["x"][1], "홈 몸통 18", 3),
                    ("y", hb[1], hb[4], "전체 %.0f" % (hb[4] - hb[1]), 0), ("y", pk["y"][0], pk["y"][1], "홈 10.8", 1),
                    ("y", hw["y"][1], 250.0, "케이블 위 다리 12", 2), ("y", 250.0, 262.0, "나사 블록 12", 3),
                    ("z", zb, zt, "14", 0), ("z", pk["z"][0], pk["z"][1], "홈 5.6", 1), ("z", 17.0, zt, "다리 5", 2),
                    ("z", zb, zb + cb_h, "나사 자리 깊이 11", 3)]
        else:
            note = ("추정: 선 슬롯 6(y)×3.3(x) - 홈 뒤끝에서 밑면까지 (spec '6×4'; 나사 자리 Ø9와 0.8 벽을 남기려고 x를 3.3으로); "
                    "추정: spec 나사 y228은 아랫판 앞 모서리(y226.5)에서 1.5뿐(구멍 Ø4.5 가장자리가 모서리 앞) → 받침을 뒤로 y%.0f까지 "
                    "늘리고 나사 2개를 y%.0f로 옮김(합판 앞 모서리에서 %.1f, 옆판 x1069.5에서 9.5). 받침 L처럼 y250~262에 나사 블록을 "
                    "두면 O7 USB-C 케이블(x1118에서 R25로 굽어 z14.5 → y246.8~254.8 통로 바닥)을 자르므로 y%.0f에서 멈춤(케이블과 2 이상). "
                    "홈 자리는 spec 그대로" % (XT30R_Y_END, XT30R_SCREW_Y, XT30R_SCREW_Y - 226.5, XT30R_Y_END))
            src = SRC_S + " printed %s (36×20×14 x%.0f~%.0f y218~238 z8~22; 홈 12.6×10.8×5.6 입구 %s; 2-Ø4.5 + 자리 Ø9 깊이 11); " \
                          "electronics.py cable_plan O7 (USB-C 케이블 경로)" \
                % (h["id"], hw["x"][0], hw["x"][1], h["pocket"]["mouth"].split(" ")[0])
            dims = [("x", hw["x"][0], hw["x"][1], "36", 0), ("x", pk["x"][0], pk["x"][1], "홈 12.6 (XT30U-F 12.4)", 1),
                    ("x", hx[0], hx[1], "나사 간격 10 (Ø4.5, 자리 Ø9)", 2),
                    ("y", hw["y"][0], XT30R_Y_END, "%.0f" % (XT30R_Y_END - hw["y"][0]), 0), ("y", pk["y"][0], pk["y"][1], "홈 10.8", 1),
                    ("y", 226.5, XT30R_SCREW_Y, "나사 y%.0f (아랫판 앞 모서리에서 %.1f)" % (XT30R_SCREW_Y, XT30R_SCREW_Y - 226.5), 2),
                    ("z", zb, zt, "14", 0), ("z", pk["z"][0], pk["z"][1], "홈 5.6", 1), ("z", zb, zb + cb_h, "나사 자리 깊이 11", 2)]
        out.add("SPK%s-XT30HOLDER" % side, h["name_ko"], "XT30 holder " + side, "print", g, holder, COLORS["printed_body"],
                h["material"], source=src, note=note, print_name="XT30받침_" + side, R=R_FLIP,
                print_note="윗면(z22, 합판에 닿는 면)을 베드에. 홈 천장은 브리지 10.8. 서포트 없음. "
                           "직결피스 8호 13 mm ×2로 스피커 아랫판 밑면에 (옆판 끝면 x152.5~164 / x1058~1069.5에는 박지 않음)",
                dims=dims)


# grille face y202..204 + spacer ring 11 (y204..215); spec: face y203..205 + ring 10. With ring 10 only 3.0 was left
# between the driver flange front (y208) and the grille face for the #8 pan-head driver screws.
GRILLE_FACE_Y = (202.0, 204.0)
GRILLE_BACK_Y = 215.0


def build_grille(S):
    gr = next(p for p in S["printed"] if p["id"] == "spk_grille")
    dm = gr["dims"]
    H = dm["outer"][0] / 2.0                       # 65
    Ri = dm["ring_inner"][0] / 2.0                 # 53
    lat = gr["lattice"]
    af, pitch = lat["across_flats"], lat["pitch"]
    fy0, fy1 = GRILLE_FACE_Y
    solid = box(-H, H, fy0, GRILLE_BACK_Y, -H, H)
    cuts = [box(-Ri, Ri, fy1, GRILLE_BACK_Y + 0.01, -Ri, Ri)]
    # honeycomb: flats vertical (pointy top), neighbours pitch apart along x, rows pitch*sqrt(3)/2 apart
    rc = af / math.sqrt(3.0)
    sq = CrossSection([[(-Ri, -Ri), (Ri, -Ri), (Ri, Ri), (-Ri, Ri)]], FillRule.NonZero)
    dv = pitch * math.sqrt(3.0) / 2.0
    nrow = int(Ri / dv) + 2
    cells = []
    for j in range(-nrow, nrow + 1):
        off = (pitch / 2.0) if (j % 2) else 0.0
        for i in range(-nrow - 1, nrow + 2):
            u, v = i * pitch + off, j * dv
            pts = [(u + rc * math.cos(math.radians(30 + 60 * k)), v + rc * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
            c = CrossSection([pts], FillRule.NonZero) ^ sq
            if c.area() < 3.0:
                continue
            for poly in c.to_polygons():
                if len(poly) >= 3:
                    cells.append(prism_y([tuple(q) for q in poly], fy0 - 0.01, fy1 + 0.01))
    cuts += cells
    for sx in (-1, 1):
        for sz in (-1, 1):
            cuts.append(cyl_y(sx * 57.0, sz * 57.0, fy0 - 0.01, GRILLE_BACK_Y + 0.01, 4.5))
    return diff(solid, cuts)


GRILLE = None


# ------------------------------------------------------------------ feet + spacers

def feet(S, out):
    f = S["feet"]
    ft = f["foot"]
    sp = ft["spacer"]
    foot0 = diff(Manifold.cylinder(ft["height"], ft["bottom_dia"] / 2.0, ft["top_dia"] / 2.0, 96),
                 [cyl_z(0, 0, -0.01, ft["height"] + 0.01, ft["hole_dia"])])
    spc0 = diff(cyl_z(0, 0, sp["z"][0], sp["z"][1], sp["dia"]), [cyl_z(0, 0, sp["z"][0] - 0.01, sp["z"][1] + 0.01, 4.5)])
    for i, p in enumerate(f["positions"]):
        x, y = p["x"], p["y"]
        out.add("FOOT-%02d" % (i + 1), "고무발 L14 화성고무 RUB-E2 (Ø28→Ø20 × 18, %s)" % p["group"], "rubber foot RUB-E2",
                "bought", G_JOIN, foot0.translate((x, y, 0.0)), COLORS["rubber"], "고무",
                source=SRC_S + " feet (x%.0f y%.0f; 밑 Ø28 윗면 Ø20 높이 18, 구멍 Ø5)" % (x, y),
                note="추정: 윗면 Ø20은 도면 실측(판매처는 외경 28만 표기), 원뿔대로 표시")
        out.add("FOOTSP-%02d" % (i + 1), "뒷바 고무발 받침 4 mm", "rear-bar rubber-foot spacer 4 mm", "print", G_JOIN,
                spc0.translate((x, y, 0.0)), COLORS["printed_body"], PETG,
                source=SRC_S + " printed foot_spacer (Ø20×4, 구멍 Ø4.5, z18~22) = " + SRC_C + " PR-FOOT-SPACER (한 번만 14개)",
                note="추정: 지름 20은 도면 실측 (spec assumed) - 두 spec에 모두 있는 부품이라 14개를 한 번만 넣음",
                print_name="뒷바_고무발받침_4mm", R=R_NONE,
                print_note="평평하게(두께 4가 높이). 직결피스 8호 25 mm + M4 와셔(L36)로 고무발과 함께 아래에서 위로",
                dims=[("x", x - 10.0, x + 10.0, "Ø20", 0), ("x", x - 2.25, x + 2.25, "구멍 Ø4.5", 1),
                      ("z", 18.0, 22.0, "4", 0)])


# ------------------------------------------------------------------ dovetail blocks + toggle latches

def dovetail_poly(root_hw, tip_hw, yc, x_root, x_tip, x_ext):
    """plan trapezoid (x, y): half-width root_hw at x_root, tip_hw at x_tip, continued with the same flank to x_ext."""
    k = (tip_hw - root_hw) / (x_tip - x_root)
    he = root_hw + k * (x_ext - x_root)
    return [(x_tip, yc - tip_hw), (x_ext, yc - he), (x_ext, yc + he), (x_tip, yc + tip_hw)]


# latch seat plates y410..419.5 (spec 8 thick, y410..418): M3x10 latch screws through the 1.2 latch sheet reach 8.8 deep,
# so an 8 seat lets the tip bite 0.8 into the plywood face y410; 9.5 leaves 0.7.
LATCH_SEAT_Y = (410.0, 419.5)


def latch_left():
    """L64 toggle latch at the left joint (closed), world coords: catch x137..148.8 on the speaker seat face y419.5,
    body x150..191 on the centre seat; z centre 35 (spec latch placement). Drawn on a y418 face, moved to the seat face."""
    zc = 35.0
    body = union([
        diff(box(165.0, 191.0, 418.0, 419.2, zc - 12.6, zc + 12.6),                         # base 26 x 25.2 x 1.2
             [cyl_y(186.0, zc + s * 5.25, 417.99, 419.21, 4.0) for s in (-1, 1)]),       # 2-Ø4, 10.5 apart
        box(172.0, 181.0, 419.2, 420.2, zc - 4.0, zc + 4.0),                               # lever pivot bracket
        box(150.0, 181.0, 420.2, 428.0, zc - 4.0, zc + 4.0),                               # lever (height 10 over the seat)
        box(149.0, 151.0, 421.0, 422.0, zc - 7.5, zc + 7.5),                               # wire loop: cross link
        box(141.0, 151.0, 421.0, 422.0, zc - 7.5, zc - 6.5),                               # wire loop arms
        box(141.0, 151.0, 421.0, 422.0, zc + 6.5, zc + 7.5),
        box(141.0, 142.3, 421.0, 422.0, zc - 7.5, zc + 7.5),                               # loop bar behind the hook
    ])
    catch = union([
        diff(box(137.0, 148.8, 418.0, 419.2, zc - 11.65, zc + 11.65),                       # 11.8 x 23.3 x 1.2
             [cyl_y(140.2, zc + s * 6.25, 417.99, 419.21, 4.0) for s in (-1, 1)]),       # 2-Ø4, 12.5 apart
        box(145.3, 146.8, 419.2, 426.8, zc - 6.0, zc + 6.0),                               # hook upright (8.8 high)
        box(143.3, 146.8, 425.6, 426.8, zc - 6.0, zc + 6.0),                               # hook lip
    ])
    dy = LATCH_SEAT_Y[1] - 418.0
    return body.translate((0.0, dy, 0.0)), catch.translate((0.0, dy, 0.0))


# speaker-side rear ear: spec ear x136..157.5 y396..410 with its screw at (142, 403) goes into the bottom end face of the
# speaker back panel (y398.5..410, plywood end grain). The screw moves onto the bottom panel (hole y389, 9.5 in front of
# the back panel). The rubber foot at (144, 379) (spacer Ø20 z18..22, cone r10.2..10.4 at z16..18) fills x134..154 up
# to y389.4, so the ear runs behind the foot (y390.5..410) and the screw pad sits left of it (x117..131), with a 45 deg
# underside toward the foot so the pad needs no support when the block stands on its joint face.
REAR_EAR_HOLE = (124.0, 389.0)
REAR_EAR_STRIP = (117.0, 157.5, 390.5, 410.0)                # x0, x1, y0, y1 (z16..22)
REAR_EAR_PAD = [(117.0, 382.0), (130.0, 382.0), (138.5, 390.51), (117.0, 390.51)]   # (x, y), 45 deg edge 1.5 off the foot

LATCH_BODY_HOLES = [(186.0, 35.0 - 5.25), (186.0, 35.0 + 5.25)]     # (x, z) left joint, centre seat
LATCH_CATCH_HOLES = [(140.2, 35.0 - 6.25), (140.2, 35.0 + 6.25)]    # (x, z) left joint, speaker seat


def joints(S, out):
    pr = {p["id"]: p for p in S["printed"]}
    # ---------------- speaker side (female, open below) + catch seat: build left, mirror right
    d = pr["dovetail_L_speaker"]
    w = d["world"]
    dv = d["dovetail"]
    pp = dv["profile_plan"]
    cl = pp["clearance_per_side"]
    ls = w["latch_seat"]
    seat = box(ls["x"][0], ls["x"][1], LATCH_SEAT_Y[0], LATCH_SEAT_Y[1], ls["z"][0], ls["z"][1])
    ears = [e for e in w["ears"] if e["y"][0] < 390.0]                  # front + middle ear as in the spec
    ex0, ex1, ey0, ey1 = REAR_EAR_STRIP
    ez0, ez1 = w["ears"][-1]["z"]
    rear_ear = union([box(ex0, ex1, ey0, ey1, ez0, ez1), prism_z(REAR_EAR_PAD, ez0, ez1)])
    blk = union([B(w["bar"])] + [B(e) for e in ears] + [rear_ear, seat])
    cuts = []
    for (ya, yb) in dv["y_ranges"]:
        yc = (ya + yb) / 2.0
        poly = dovetail_poly(pp["root"] / 2.0 + cl, pp["tip"] / 2.0 + cl, yc, 164.0, 164.0 - pp["depth"], 164.6)
        cuts.append(prism_z(poly, w["bar"]["z"][0] - 0.01, w["bar"]["z"][1] + 0.01))
    eh = d["holes"][0]
    ear_holes = [(c["x"], c["y"]) for c in eh["centers"] if c["y"] < 390.0] + [REAR_EAR_HOLE]
    for (cx_, cy_) in ear_holes:         # ears z16..22: counterbore Ø9 3 deep from below, Ø4.5 through (apex -x = print up)
        cuts.append(hole("z", cx_, cy_, 15.99, 22.01, eh["dia"], apex=(-1, 0)))
        cuts.append(hole("z", cx_, cy_, 15.99, 19.0, eh["counterbore"]["dia"], apex=(-1, 0)))
    for (hx, hz) in LATCH_CATCH_HOLES:   # M3x10 self-tapping pilots through the 9.5 mm seat
        cuts.append(hole("y", hx, hz, LATCH_SEAT_Y[0] - 0.01, LATCH_SEAT_Y[1] + 0.01, 2.75, apex=(-1, 0)))
    spk_blk = diff(blk, cuts)
    st = LATCH_SEAT_Y[1] - LATCH_SEAT_Y[0]
    note_sp = ("추정: 블록 모양은 spec 제안(v3에 모양 없음) - 암 홈 뿌리 14.2·끝 18.2(틈 0.1씩) 깊이 4, 귀 나사 자리 Ø9 깊이 3(PETG 3 + 합판 10), "
               "래치 걸이 파일럿 Ø2.75 ×2 (x140.2, z28.75/41.25 = 걸이 구멍 간격 12.5). "
               "추정: 뒤 귀 나사를 spec (142, 403)에서 (%.0f, %.0f)로 옮김 - spec 자리는 스피커 뒷판(y398.5~410) 밑 끝면(합판 마구리)에 박힘; "
               "새 자리는 아랫판 밑면(뒷판 앞면 y398.5에서 %.1f). 뒤 귀를 y382~396 x136~157.5로 옮기면 고무발(x144 y379: 받침 Ø20 z18~22, "
               "원뿔 윗부분)과 겹치므로 귀를 발 뒤(x%.0f~%.1f y%.1f~410)로 두르고 나사 자리 판(x%.0f~%.0f y%.0f~, 발 쪽 45° 모서리)을 발 왼쪽에 둠 "
               "(발과 1 mm 이상). 추정: 래치 받침 두께 8 → %.1f (y%.0f~%.1f) - M3×10이 래치 판 1.2를 지나 받침에 8.8 들어가므로 받침 8이면 "
               "끝이 합판 면 y410에 0.8 박힘, %.1f이면 %.1f 남음. 이음면 EVA 3T 띠는 넣지 않음(모델에도 없음): 도브테일 2개 + 토글 래치가 "
               "이음을 고정하고, 띠를 끼우면 스피커 파트가 3 mm 밖으로 밀려 암 홈이 수 도브테일에서 3 mm 벗어나 수를 위에서 내려 끼울 수 없음 "
               "(전체 폭 1254 유지, A05)"
               % (REAR_EAR_HOLE[0], REAR_EAR_HOLE[1], 398.5 - REAR_EAR_HOLE[1], REAR_EAR_STRIP[0], REAR_EAR_STRIP[1], REAR_EAR_STRIP[2],
                  REAR_EAR_PAD[0][0], REAR_EAR_PAD[1][0], REAR_EAR_PAD[0][1], st, LATCH_SEAT_Y[0], LATCH_SEAT_Y[1], st, st + 1.2 - 10.0))
    src_sp = SRC_S + " printed dovetail_%s_speaker (막대 x157.5~164 y268~410 z6~22, 귀 3곳 z16~22 (뒤 귀 나사 y403 → y389로 옮김), " \
                     "래치 받침 y410~418 z6~50 (→ 두께 9.5); 도브테일 y275~293·y360~378)"
    dims_l = [("x", REAR_EAR_STRIP[0], 164.0, "뒤 귀 끝→이음면 %.0f" % (164.0 - REAR_EAR_STRIP[0]), 0), ("x", 160.0, 164.0, "홈 깊이 4", 1),
              ("x", 157.5, 164.0, "막대 6.5", 2), ("x", 136.0, 164.0, "앞·가운데 귀 28", 3),
              ("x", REAR_EAR_STRIP[0], REAR_EAR_HOLE[0], "뒤 귀 나사 x%.0f" % REAR_EAR_HOLE[0], 4),
              ("y", 268.0, 410.0, "막대 142", 0), ("y", 275.0, 293.0, "도브테일 끝 18 (뿌리 14)", 1), ("y", 360.0, 378.0, "도브테일 18", 2),
              ("y", LATCH_SEAT_Y[0], LATCH_SEAT_Y[1], "래치 받침 %.1f" % st, 3),
              ("y", REAR_EAR_HOLE[1], 398.5, "뒤 귀 나사 y%.0f ↔ 뒷판 앞면 %.1f" % (REAR_EAR_HOLE[1], 398.5 - REAR_EAR_HOLE[1]), 4),
              ("z", 6.0, 22.0, "막대 16", 0), ("z", 16.0, 22.0, "귀 6", 1), ("z", 6.0, 50.0, "래치 받침 44", 2)]
    for side in "LR":
        s = spk_blk if side == "L" else mx(spk_blk)
        dims = dims_l if side == "L" else [(a, (mxv(q) if a == "x" else p), (mxv(p) if a == "x" else q), lab, ln)
                                           for (a, p, q, lab, ln) in dims_l]
        dims = [(a, min(p, q), max(p, q), lab, ln) for (a, p, q, lab, ln) in dims]
        out.add("JOIN-DT-%sS" % side, pr["dovetail_%s_speaker" % side]["name_ko"], "rear-bar dovetail block %s, speaker side (female)" % side,
                "print", G_JOIN, s, COLORS["printed_body"], PETG, source=src_sp % side, note=note_sp,
                print_name="도브테일블록_%s_스피커쪽" % side, R=(R_XMAX if side == "L" else R_XMIN),
                print_note="이음면(x%s)을 베드에 세워 출력: 귀·래치 받침이 막대 위로 서고, 도브테일 홈 옆면은 26.6° 기울기, 뒤 귀 나사 판 밑은 "
                           "45°라 서포트 없음. 속이 꽉 찬 작은 블록이라 벽 4줄 + 채움 25 %%. "
                           "귀 3곳의 직결피스 8호 13 mm ×4로 스피커 아랫판 밑면에, 래치 걸이는 M3×10 자가 탭 ×2. "
                           "이음면에 EVA 3T 띠를 붙이지 않음(띠 두께만큼 암 홈이 밀려 수 도브테일이 안 들어감)" % ("164" if side == "L" else "1058"),
                dims=dims)

    # ---------------- centre side (male) + latch-body seat
    d = pr["dovetail_L_centre"]
    w = d["world"]
    dv = d["dovetail"]
    pp = dv["profile_plan"]
    ls = w["latch_seat"]
    parts = [B(w["bar"]), box(ls["x"][0], ls["x"][1], LATCH_SEAT_Y[0], LATCH_SEAT_Y[1], ls["z"][0], ls["z"][1])]
    for (ya, yb) in w["male"]["y_ranges"]:
        yc = (ya + yb) / 2.0
        poly = dovetail_poly(pp["root"] / 2.0, pp["tip"] / 2.0, yc, 164.0, 164.0 - pp["depth"], 164.5)
        parts.append(prism_z(poly, w["male"]["z"][0], w["male"]["z"][1]))
    blk = union(parts)
    eh = d["holes"][0]
    cuts = []
    for c in eh["centers"]:              # bar z6..22: counterbore Ø9 from below to z19 (PETG 3 under the head), Ø4.5 through
        cuts.append(cyl_z(c["x"], c["y"], 5.99, 22.01, eh["dia"]))
        cuts.append(cyl_z(c["x"], c["y"], 5.99, 19.0, eh["counterbore"]["dia"]))
    for (hx, hz) in LATCH_BODY_HOLES:
        cuts.append(hole("y", hx, hz, LATCH_SEAT_Y[0] - 0.01, LATCH_SEAT_Y[1] + 0.01, 2.75, apex=(0, 1)))
    cen_blk = diff(blk, cuts)
    note_c = ("추정: 블록 모양은 spec 제안 - 수 도브테일 뿌리 14·끝 18·깊이 4 (z6~21.7, 합판 밑면과 0.3 틈), 나사 자리 Ø9 z6~19 (PETG 3 + 합판 10), "
              "래치 본체 파일럿 Ø2.75 ×2 (x186, z29.75/40.25 = 본체 구멍 간격 10.5). 추정: 래치 받침 두께 8 → %.1f (y%.0f~%.1f) - M3×10이 래치 판 "
              "1.2를 지나 받침에 8.8 들어가므로 받침 8이면 끝이 합판 면 y410에 0.8 박힘, %.1f이면 %.1f 남음. 이음면 EVA 3T 띠는 넣지 않음(모델에도 없음): "
              "도브테일 2개 + 토글 래치가 이음을 고정하고, 띠를 끼우면 스피커 파트가 3 mm 밖으로 밀려 암 홈이 수 도브테일에서 3 mm 벗어나 "
              "수를 위에서 내려 끼울 수 없음 (전체 폭 1254 유지, A05)"
              % (st, LATCH_SEAT_Y[0], LATCH_SEAT_Y[1], st, st + 1.2 - 10.0))
    src_c = SRC_S + " printed dovetail_%s_centre (막대 x164~184 y268~410 z6~22, 수 x160~164 z6~21.7, 래치 받침 x164~210 y410~418 z6~50 (→ 두께 9.5))"
    dims_c = [("x", 160.0, 184.0, "수 4 + 막대 20", 0), ("x", 160.0, 164.0, "도브테일 4", 1), ("x", 164.0, 210.0, "래치 받침 46", 2),
              ("y", 268.0, 410.0, "막대 142", 0), ("y", 275.0, 293.0, "도브테일 끝 18 (뿌리 14)", 1), ("y", 360.0, 378.0, "도브테일 18", 2),
              ("y", LATCH_SEAT_Y[0], LATCH_SEAT_Y[1], "래치 받침 %.1f" % st, 3),
              ("z", 6.0, 22.0, "막대 16", 0), ("z", 6.0, 21.7, "수 15.7", 1), ("z", 6.0, 19.0, "나사 자리 13", 2), ("z", 6.0, 50.0, "래치 받침 44", 3)]
    for side in "LR":
        s = cen_blk if side == "L" else mx(cen_blk)
        dims = dims_c if side == "L" else [(a, (mxv(q) if a == "x" else p), (mxv(p) if a == "x" else q), lab, ln)
                                           for (a, p, q, lab, ln) in dims_c]
        out.add("JOIN-DT-%sC" % side, pr["dovetail_%s_centre" % side]["name_ko"], "rear-bar dovetail block %s, centre side (male)" % side,
                "print", G_JOIN, s, COLORS["printed_body"], PETG, source=src_c % side, note=note_c,
                print_name="도브테일블록_%s_가운데쪽" % side, R=R_NONE,
                print_note="막대 밑면(z6)을 베드에. 수 도브테일·래치 받침은 곧게 서서 서포트 없음. 속이 꽉 찬 작은 블록이라 벽 4줄 + 채움 25 %%. "
                           "직결피스 8호 13 mm ×4로 가운데 유닛 바닥(x%s) 밑면에, 래치 본체는 M3×10 자가 탭 ×2. "
                           "이음면에 EVA 3T 띠를 붙이지 않음(띠 두께만큼 암 홈이 밀려 수 도브테일이 안 들어감)" % ("178" if side == "L" else "1044"),
                dims=dims)

    # ---------------- toggle latches (bought)
    lt = S["latch"]
    body, catch = latch_left()
    for side in "LR":
        m = union([body, catch])
        if side == "R":
            m = mx(m)
        out.add("JOIN-LATCH-%s" % side, "토글 래치 L64 (매미고리 1-20, SUS304) — 본체 + 걸이 %s" % side,
                "toggle latch L64 (body + catch) " + side, "bought", G_JOIN, m, COLORS["stainless"], "SUS304",
                source=SRC_S + " latch (잠근 길이 54 x%s, 본체 43.3×25.2×10 2-Ø4 간격 10.5, 걸이 23.3×11.8×8.8 2-Ø4 간격 12.5, z중심 35)"
                % ("137~191" if side == "L" else "1031~1085"),
                note="추정: 상자 여러 개로 단순화(레버·철사 고리·걸이 갈고리); 본체 x165~191·걸이 x137~148.8 (좌), 받침 면 y%.1f에 붙음 "
                     "(받침 두께 9.5로 늘려 spec y418에서 옮김). 잠근 래치가 뒤로 y%.1f까지 나옴" % (LATCH_SEAT_Y[1], LATCH_SEAT_Y[1] + 10.0))


# ------------------------------------------------------------------ v4 anti-vibration bracket

# cheek bolt seats as the key-action frame generator cuts them (keyaction_parts.cheek_features: bolt holes Ø3.4 teardrop
# y203..212.5 at z12, M3 nut pockets 5.6 x 2.6 at y204.95..207.55 from below, roof z15.2). Pitch 6.92, centred on the
# cheek centres x-8.34 / x1230.34 (spec proposal_v4 said 7.8 apart around x-8.34 / x1230.84).
BRK_SEAT_X = {"L": (-11.80, -4.88), "R": (1226.88, 1233.80)}
# left cheek wire channel for the two headphone cables W701/W702 (Ø3.5 each): x-12.6..-4.1 z3..7.5, open at the cheek
# rear face y212 (keyaction_parts.cheek_features). The left bracket leg gets a notch around it.
BRK_CABLE_NOTCH_L = (-13.0, -3.7, 2.9, 8.0)                  # x0, x1, z0, z1 through the whole leg depth y212.5..218


def bracket(F, out):
    """L bracket (printed) from the end-part cheek rear face to the speaker-part bottom panel.

    vertical leg: 0.5 inside both cheek edges, y212.5..218 (front face 0.5 clear of the cheek rear face y212 so only the
    grommets touch the key action), z3..20; per bolt a 1.6 web at y215.5..217.1 (the grommet waist) with a Ø4.2 hole,
    Ø6.5 flange pockets on both sides of the web (opened to the side where the leg is too narrow, and joined to the next
    pocket when the wall between them would be under 0.8). Left leg: cable notch for the headphone cables below z8.
    horizontal leg: z18..22 under the speaker part, y212.5..245, one countersunk Ø4.5 hole at y232 for an 8-ho 13 mm screw.
    """
    cheeks = F["cheeks"]
    Z = 12.0
    YF, YW0, YW1, YB = 212.5, 215.5, 217.1, 218.0          # leg front, web front, web back, leg back
    G_FL, G_WAIST, G_BORE, G_LEN = 6.0, 4.0, 3.2, 8.6       # grommet flange Ø, waist Ø, bore, length (3.5 + 1.6 + 3.5)
    POCKET, WEB_HOLE = 6.5, 4.2
    for side in "LR":
        holes = sorted(BRK_SEAT_X[side])
        if side == "L":
            cx0, cx1 = cheeks["left"]["x"]
            screw_x = 2.0
        else:
            cx0, cx1 = cheeks["right"]["x_world"]
            screw_x = mxv(2.0)
        lx0, lx1 = cx0 + 0.5, cx1 - 0.5                     # vertical leg x (0.5 inside each cheek edge)
        hx0, hx1 = (lx0, 9.0) if side == "L" else (mxv(9.0), lx1)   # horizontal leg reaches under the plywood bottom
        solid = union([box(lx0, lx1, YF, YB, 3.0, 20.0), box(hx0, hx1, YF, 245.0, 18.0, 22.0),
                       prism_x([(YB - 0.01, 15.5), (YB + 2.5, 18.0 + 0.01), (YB - 0.01, 18.0 + 0.01)], lx0, lx1)])  # 2.5 fillet
        cuts = []
        opened = []
        r = POCKET / 2.0
        for i, hxc in enumerate(holes):
            wl, wr = (hxc - r) - lx0, lx1 - (hxc + r)
            ext = []
            if wl < 0.8:
                ext.append(lx0 - 2.0)
                opened.append("x%.2f -x" % hxc)
            if wr < 0.8:
                ext.append(lx1 + 2.0)
                opened.append("x%.2f +x" % hxc)
            if i + 1 < len(holes) and (holes[i + 1] - r) - (hxc + r) < 0.8:     # 0.42 sliver between the pockets -> join
                ext.append(holes[i + 1])
                opened.append("x%.2f↔x%.2f 이어짐" % (hxc, holes[i + 1]))
            for (ya, yb) in ((YF - 0.01, YW0), (YW1, YB + 0.01)):          # flange pockets both sides of the web
                if ext:
                    for e in ext:
                        cuts.append(slot_hole("y", (hxc, Z), (e, Z), ya, yb, POCKET, apex=(0, -1)))
                else:
                    cuts.append(hole("y", hxc, Z, ya, yb, POCKET, apex=(0, -1)))
            cuts.append(hole("y", hxc, Z, YW0 - 0.01, YW1 + 0.01, WEB_HOLE, apex=(0, -1)))
        if side == "L":                                     # headphone-cable notch (open below, leg tip in print)
            nx0, nx1, nz0, nz1 = BRK_CABLE_NOTCH_L
            cuts.append(box(nx0, nx1, YF - 0.01, YB + 0.01, nz0, nz1))
        cuts.append(cyl_z(screw_x, 232.0, 17.99, 22.01, 4.5))
        cuts.append(cone_z(screw_x, 232.0, 17.99, 18.0 + (8.62 - 4.5) / 2.0, 8.62, 4.5))
        brk = diff(solid, cuts)
        pitch = holes[-1] - holes[0]
        dims = [("x", lx0, lx1, "세움 다리 %.2f (볼 안쪽 0.5씩)" % (lx1 - lx0), 0),
                ("x", holes[0], holes[-1], "볼트 간격 %.2f (볼 너트 자리 x%.2f/x%.2f)" % (pitch, holes[0], holes[-1]), 1),
                ("x", hx0, hx1, "눕힘 다리 %.1f" % (hx1 - hx0), 2),
                ("x", min(screw_x, lx0 if side == "R" else hx0), max(screw_x, lx0 if side == "R" else hx0), "나사 x%.1f" % screw_x, 3),
                ("y", YF, YB, "세움 다리 5.5 (볼과 0.5 띄움)", 0), ("y", YW0, YW1, "그로밋 웹 1.6", 1), ("y", YF, 245.0, "눕힘 다리 32.5", 2),
                ("y", YF, 232.0, "나사 y232", 3),
                ("z", 3.0, 22.0, "전체 19", 0), ("z", 3.0, Z, "그로밋 z12", 1), ("z", 18.0, 22.0, "눕힘 다리 4", 2)]
        notch_txt = ""
        if side == "L":
            nx0, nx1, nz0, nz1 = BRK_CABLE_NOTCH_L
            dims += [("x", nx0, nx1, "헤드폰 선 홈 %.1f (Ø3.5 ×2)" % (nx1 - nx0), 4), ("z", 3.0, nz1, "선 홈 z3~8 (밑 열림)", 3)]
            notch_txt = ("세움 다리 밑에 헤드폰 선 홈 x%.1f~%.1f z3~%.1f (y212.5~218 관통, 밑 열림) - 볼 선 통로 x-12.6~-4.1 z3~7.5 "
                         "(볼 뒷면 y212에서 열림)로 나온 Ø3.5 선 2가닥(W701/W702)이 지나감; 그로밋 자리(z8.75~)는 그대로. "
                         % (nx0, nx1, nz1))
        out.add("BRK-%s" % side, "방진 브래킷 %s (끝 부속 볼 ↔ 스피커 파트, v4 제안)" % side,
                "anti-vibration bracket %s (v4 proposal)" % side, "print", G_BR, brk, COLORS["printed_body"], "PETG 회색",
                source=SRC_F + " bracket.proposal_v4 (볼 뒷면 y212 M3 볼트 자리 z12, 너트 홈 y205~207.5); 볼트 x%s = keyaction_parts.py "
                "cheek_features 볼 자리(구멍 Ø3.4 y203~212.5, 너트 홈 5.6×2.6 y205~207.5 밑에서, 천장 z15.2); cheeks %s; "
                % ("/".join("%.2f" % h for h in holes), "left x-16~-0.68" if side == "L" else "right x1222.68~1238")
                + SRC_S + " spk_bracket (그로밋 구멍 Ø6.5 / 1.6 웹, v3 A12는 v4에 못 붙음 - conflicts)",
                note="추정: v4용으로 새로 제안한 형상 - v3 A12 평판(y205~222 z9~15)은 v4 끝 부속 뒷벽(z5~72.85)을 지나고 스피커 쪽 z22 아래에 "
                     "재료가 없어 못 붙음. ㄱ자: 세움 다리 x%.2f~%.2f y212.5~218 z3~20 (볼 뒷면에서 0.5 띄워 그로밋만 닿게), "
                     "눕힘 다리 x%.1f~%.1f y212.5~245 z18~22, 스피커 아랫판(x%s)에 접시 자리 Ø4.5/Ø8.6 + 직결피스 8호 13 mm 1개 (y232). "
                     "볼트 자리 x%.2f/x%.2f (간격 %.2f, 볼 중심 x%.2f) = 키 액션 생성기가 볼에 판 자리 (spec 제안 간격 7.8에서 바뀜). "
                     "그로밋 자리: 웹 1.6 (y215.5~217.1)에 허리 구멍 Ø4.2, 양쪽 플랜지 자리 Ø6.5 - 다리 폭이 좁아 자리가 옆으로 열리고 "
                     "두 자리 사이 벽이 0.42뿐이라 하나로 이음 (%s). %s"
                     "그로밋은 허리 Ø4 × 길이 8.6 (플랜지 Ø6 × 3.5 ×2)로 가정"
                % (lx0, lx1, hx0, hx1, "−4.5~152.5" if side == "L" else "1069.5~1226.5", holes[0], holes[-1], pitch,
                   (holes[0] + holes[-1]) / 2.0, ", ".join(opened), notch_txt),
                print_name="방진브래킷_" + side, R=R_FLIP,
                print_note="눕힘 다리 윗면(z22)을 베드에, 세움 다리가 위로. 그로밋 구멍은 위쪽 눈물방울(서포트 없음)%s. "
                           "그로밋을 웹에 끼우고 M3×16 볼트 ×2를 볼의 눌러 넣은 M3 너트에; 눕힘 다리는 접시머리 8호 13 mm로 스피커 아랫판에"
                           % (", 헤드폰 선 홈은 세움 다리 끝(출력 때 맨 위)에서 열림 - 브리지 없음" if side == "L" else ""),
                dims=dims)
        # ---- bought: grommets, bolts, nuts, screw
        for i, hxc in enumerate(sorted(holes)):
            gm = union([cyl_y(hxc, Z, 212.0, YW0, G_FL), cyl_y(hxc, Z, YW0, YW1, G_WAIST), cyl_y(hxc, Z, YW1, 212.0 + G_LEN, G_FL)])
            gm = diff(gm, [cyl_y(hxc, Z, 211.99, 212.0 + G_LEN + 0.01, G_BORE)])
            out.add("BRK-%s-GROM%d" % (side, i + 1), "실리콘 방진 그로밋 M3 (L42, 1.6 판용 홈)", "M3 silicone anti-vibration grommet (L42)",
                    "bought", G_BR, gm, COLORS["rubber"], "실리콘",
                    source="hardware/bom L42 (FPV M3 실리콘 방진 그로밋, 홈 1.6); " + SRC_S + " spk_bracket holes",
                    note="추정: 플랜지 Ø6 × 3.5 + 허리 Ø4 × 1.6 + 플랜지 Ø6 × 3.5 = 길이 8.6, 구멍 Ø3.2 (받은 그로밋을 재서 웹 구멍·자리 조정); "
                         "앞 플랜지가 볼 뒷면 y212에 닿음")
            yb0 = 212.0 + G_LEN
            bolt = union([cyl_y(hxc, Z, yb0 - 16.0, yb0, 3.0), cyl_y(hxc, Z, yb0, yb0 + 1.65, 5.7)])
            out.add("BRK-%s-BOLT%d" % (side, i + 1), "M3×16 둥근머리 볼트 ISO 7380 (방진 브래킷)", "M3x16 button head bolt (bracket)",
                    "bought", G_BR, bolt, COLORS["stainless"], "SUS",
                    source=SRC_F + " bracket.proposal_v4 hardware (M3 볼트 → 볼 너트); 길이 16 = 그로밋 8.6 + 볼 속 7.4 (끝 y204.6, 너트 y205~207.5 관통)",
                    note="추정: 머리 Ø5.7 × 1.65 (ISO 7380); 와셔(L36)를 넣으면 끝이 y205.1로 너트 물림 2.35")
            rc = 5.5 / math.sqrt(3.0)                 # M3 nut AF 5.5 -> corner radius 3.175
            zc = Z                                    # pocket roof raised to z15.2 (> 12 + 3.175) -> nut on the bolt axis
            nut = diff(prism_y(hex_pts(hxc, zc, rc), 205.05, 207.45), [cyl_y(hxc, zc, 205.0, 207.5, 2.5)])
            out.add("BRK-%s-NUT%d" % (side, i + 1), "M3 육각 너트 (볼의 너트 홈에 압입, 방진 브래킷)", "M3 hex nut in the cheek pocket",
                    "bought", G_BR, nut, COLORS["stainless"], "SUS",
                    source=SRC_F + " bracket.proposal_v4 nut_pocket (맞변 5.5 압입, y205~207.5, 밑에서 홈; 천장 z15.2로 올림)",
                    note="추정: 볼 너트 홈 천장을 z15.2로 올려(볼트 축 z12 + 꼭짓점 3.175) 너트가 볼트 축에 맞음")
        scr = union([cone_z(screw_x, 232.0, 18.0, 20.1, 8.4, 4.2), cyl_z(screw_x, 232.0, 20.1, 31.0, 4.2)])
        out.add("BRK-%s-SCREW" % side, "직결피스 8호 13 mm 접시머리 (방진 브래킷 → 스피커 아랫판)", "8-ho 13 mm countersunk self-drilling screw",
                "bought", G_BR, scr, COLORS["stainless"], "SUS",
                source="task: 접시 자리 + 8호 13 mm (L49 계열); 물림 13 − 4 = 9 < 아랫판 11.5 (밀폐 유지)",
                note="추정: 접시머리 Ø8.4; L49 둥근머리 예비분을 쓰면 머리가 약 2.7 mm 밑으로 나옴")


def hex_pts(c1, c2, rc):
    """hexagon (corner radius rc) with flats facing +-c1 and corners at +-c2, CCW."""
    return [(c1 + rc * math.cos(math.radians(30 + 60 * k)), c2 + rc * math.sin(math.radians(30 + 60 * k))) for k in range(6)]


# ------------------------------------------------------------------ centre unit plywood

def cu_panels(C, out):
    for p in C["panels"]:
        out.add("CU-PLY-%s" % p["id"].split("-")[1], "가운데 유닛 " + p["name_ko"], "centre unit " + p["name"], "plywood", G_CU,
                B(p["box"]), COLORS["plywood"], PLY,
                source=SRC_C + " panels %s (%s, 재단 %g×%g)" % (p["id"], p["name"], p["cut"][0], p["cut"][1]))


# ------------------------------------------------------------------ CU tray

# CU tray underside rib pitch (spec PR-CU-TRAY structure.underside_ribs.pitch = 40). The top skin bridges the rib cells,
# so this is the one number to lower (e.g. 25) if the first skin layer sags; ribs are laid out by tray_rib_positions().
TRAY_RIB_PITCH = 40.0


def tray_rib_positions(x0, x1, y0, y1, wall, rt, pitch=None):
    """rib centre lines: along-y ribs symmetric about the bay centre x620 (pitch 40 -> 560/600/640/680), along-x ribs at
    y0 + k * pitch (pitch 40 -> 255/295/335/375); only ribs clear of the 4.0 perimeter wall are kept."""
    p = TRAY_RIB_PITCH if pitch is None else pitch
    xc = (x0 + x1) / 2.0
    xs = []
    k = 0
    while True:
        d = (k + 0.5) * p
        if xc + d + rt / 2 >= x1 - wall:
            break
        xs += [xc - d, xc + d]
        k += 1
    ys = []
    y = y0 + p
    while y + rt / 2 < y1 - wall:
        ys.append(y)
        y += p
    return sorted(round(v, 3) for v in xs), ys

def cu_tray(C, out):
    T = next(p for p in C["printed"] if p["id"] == "PR-CU-TRAY")
    st = T["structure"]
    fe = {f["name"]: f for f in T["features"]}
    x0, x1 = 520.0 + T["fit"]["clearance_each_side_x"], 720.0 - T["fit"]["clearance_each_side_x"]
    y0, y1 = T["box"]["y"]
    z0, z1 = T["box"]["z"]
    zs0, zs1 = st["top_skin_z"]
    wall = st["perimeter_wall"]
    rt = st["underside_ribs"]["t"]
    add = [box(x0, x1, y0, y1, zs0, zs1),
           diff(box(x0, x1, y0, y1, z0, zs0 + 0.01), [box(x0 + wall, x1 - wall, y0 + wall, y1 - wall, z0 - 0.01, zs0 + 0.02)])]
    rxs, rys = tray_rib_positions(x0, x1, y0, y1, wall, rt)
    for rx in rxs:                                              # ribs along y, TRAY_RIB_PITCH apart, centred on x620
        add.append(box(rx - rt / 2, rx + rt / 2, y0 + wall - 0.01, y1 - wall + 0.01, z0, zs0 + 0.01))
    for ry in rys:                                              # ribs along x, y0 + k * TRAY_RIB_PITCH
        add.append(box(x0 + wall - 0.01, x1 - wall + 0.01, ry - rt / 2, ry + rt / 2, z0, zs0 + 0.01))
    inl = fe["cable_inlet"]["box"]
    add.append(box(inl["x"][0] - 2.0, inl["x"][1] + 2.0, y0, inl["y"][1] + 2.0, z0, zs0 + 0.01))   # inlet rim (cut below)
    # foot screw bosses + solid pads under them
    fb = fe["foot_screw_bosses"]
    for (px, py) in fb["at"]:
        add.append(cyl_z(px, py, z0, zs0 + 0.01, 22.0))
        add.append(cyl_z(px, py, zs1 - 0.01, fb["z"][1], fb["d"]))
    # component bosses
    pi = fe["pi5_bosses"]
    add += [cyl_z(px, py, zs1 - 0.01, pi["z"][1], pi["od"]) for (px, py) in pi["at"]]
    for nm in ("amp_bosses", "buck_bosses", "amp_input_jack_board_bosses"):
        f = fe[nm]
        for (px, py) in f["at"]:
            add.append(cyl_z(px, py, zs1 - 0.01, f["z"][1], f["od"]))
            add.append(cyl_z(px, py, z0, zs0 + 0.01, 9.0))              # full-height post under the 10-deep pilot (from z22)
    ped = fe["ped_board_standoffs"]
    pedpts = [tuple(p) for p in ped["screw_at"]] + [tuple(p) for p in ped["pin_at"]]
    add += [cyl_z(px, py, zs1 - 0.01, ped["z"][1], ped["od"]) for (px, py) in pedpts]
    add += [cyl_z(px, py, ped["z"][1] - 0.01, ped["z"][1] + 2.5, 2.8) for (px, py) in ped["pin_at"]]
    # divider screw tabs
    tabs = tray_tabs(fe)
    add += [B(t["box"]) for t in tabs]
    # fuse holder cradle
    fc = fe["fuse_holder_cradle"]
    cb = fc["box"]
    fy = 311.0                                                  # holder axis y311 z40.5 (component box y306..316 z35.5..45.5)
    fz = 40.5
    add.append(diff(B(cb), [cyl_x(fy, fz, cb["x"][0] - 0.01, cb["x"][1] + 0.01, fc["inner_d"])]))
    tray = union(add)

    cuts = []
    # cable inlet: through slot + 1.0 chamfers on the x ends and the rear edge (top and bottom)
    ix0, ix1, iy0, iy1 = inl["x"][0], inl["x"][1], inl["y"][0], inl["y"][1]
    ch = fe["cable_inlet"]["chamfer"]
    cuts.append(box(ix0, ix1, iy0, iy1, z0 - 0.01, z1 + 0.01))
    cuts.append(Manifold.batch_hull([box(ix0, ix1, iy0, iy1, z1 - ch, z1 - ch + 0.001),
                                     box(ix0 - ch, ix1 + ch, iy0, iy1 + ch, z1, z1 + 0.5)]))
    cuts.append(Manifold.batch_hull([box(ix0 - ch, ix1 + ch, iy0, iy1 + ch, z0 - 0.5, z0),
                                     box(ix0, ix1, iy0, iy1, z0 + ch - 0.001, z0 + ch)]))
    # foot boss pilots Ø3.4 from below, 1.0 cap on top
    cuts += [cyl_z(px, py, z0 - 0.01, fb["z"][1] - 1.0, fb["pilot"]) for (px, py) in fb["at"]]
    # Pi taps Ø2.2 x 8
    cuts += [cyl_z(px, py, pi["z"][1] - pi["tap_depth"], pi["z"][1] + 0.01, pi["tap"]) for (px, py) in pi["at"]]
    # amp / buck / J702 pilots Ø2.7 x 10
    for nm in ("amp_bosses", "buck_bosses", "amp_input_jack_board_bosses"):
        f = fe[nm]
        dep = f.get("pilot_depth", 10.0)
        cuts += [cyl_z(px, py, f["z"][1] - dep, f["z"][1] + 0.01, f["pilot"]) for (px, py) in f["at"]]
    # PED standoff screw holes Ø2.5 x 5
    cuts += [cyl_z(px, py, ped["z"][1] - 5.0, ped["z"][1] + 0.01, 2.5) for (px, py) in ped["screw_at"]]
    # tab holes Ø4.5 along x (teardrop, apex +z)
    for t in tabs:
        hx, hy, hz = t["hole_center"]
        cuts.append(hole("x", hy, hz, t["box"]["x"][0] - 0.01, t["box"]["x"][1] + 0.01, 4.5, apex=(0, 1)))
    # cable-tie anchors: 2 slots 1.6 (x) x 2.8 (y) through the skin, bridge 3.6 between them
    an = fe["cable_tie_anchors"]
    sw, sl = an["slot"][1], an["slot"][0]
    for (ax, ay) in an["at"]:
        for s in (-1, 1):
            cuts.append(box(ax + s * 2.6 - sw / 2, ax + s * 2.6 + sw / 2, ay - sl / 2, ay + sl / 2, zs0 - 0.01, z1 + 0.01))
    # fuse cradle tie slots: through the skin in front of / behind the cradle at x642 / x668
    for tx in (642.0, 668.0):
        for (ya, yb) in ((301.5, 303.1), (318.9, 320.5)):
            cuts.append(box(tx - 1.4, tx + 1.4, ya, yb, zs0 - 0.01, z1 + 0.01))
    tray = diff(tray, cuts)

    out.add("CU-TRAY", "CU 트레이", "CU tray (printed bay floor)", "print", G_CUP, tray, COLORS["printed_body"], "PETG 회색/검정",
            source=SRC_C + " PR-CU-TRAY (x520~720 틈 0.2씩, y215~410, z22~33.5; 윗판 3.0, 테 4.0, 밑 리브 2.0 피치 40; 케이블 입구 x540~700 "
                           "y217~237 모따기 1.0; 부품 보스 = 재배치 좌표)",
            note="추정: 리브 위치 x%s·y%s (피치 %.0f = body.py TRAY_RIB_PITCH), 입구 둘레 벽 2.0 (밑에서 선이 리브 칸으로 새지 않게), "
                 "앰프·강압·J702 보스 밑 Ø9 기둥 10개 z22~30.5 (파일럿 10 깊이; 트레이 밑면 z22부터 서는 기둥 - 고무발 보스 받침처럼, "
                 "밑면을 베드에 두고 출력할 때 공중에서 시작하는 곳이 없음), 고무발 보스 파일럿 윗면 1.0 막음, "
                 "케이블 타이 고리 = 윗판 슬롯 1.6×2.8 두 개(다리 3.6), 퓨즈 받침 타이 슬롯 x642/x668 (받침 앞·뒤)"
                 % ("/".join("%.0f" % v for v in rxs), "/".join("%.0f" % v for v in rys), TRAY_RIB_PITCH),
            print_name="CU트레이", R=R_NONE,
            print_note="밑(리브 쪽)을 베드에, 보스가 위. 윗판(z30.5~33.5)은 리브 칸 %.0f×%.0f (빈 폭 약 %.0f)을 브리지로 덮음 - "
                       "슬라이서 브리지 설정: 두꺼운 브리지(thick bridges) 켬, 브리지 유량 0.9~0.95, 브리지 속도 20~30 mm/s, "
                       "브리지 팬 100 %%, 브리지 방향 자동(리브에 수직). 첫 윗판 층이 처지면 리브 피치를 줄여 다시 생성: "
                       "body.py 상수 TRAY_RIB_PITCH (지금 %.0f; 예 25). 199.6×195 (220 베드 OK). "
                       "칸막이 탭 구멍은 눈물방울(서포트 없음). 13 mm 피스 ×4로 칸막이·낮은 칸막이 옆면에"
                       % (TRAY_RIB_PITCH, TRAY_RIB_PITCH, TRAY_RIB_PITCH - rt, TRAY_RIB_PITCH),
            dims=[("x", x0, x1, "199.6 (합판 틈 0.2씩)", 0), ("x", ix0, ix1, "케이블 입구 160", 1),
                  ("x", 534.5, 592.5, "Pi 보스 58", 2), ("x", 667.5, 706.5, "앰프 보스 39", 3), ("x", 611.2, 665.6, "강압 보스 54.4", 4),
                  ("x", x0, 620.0, "고무발 보스 x620", 5),
                  ("y", y0, y1, "195", 0), ("y", iy0, iy1, "입구 20 (방 안쪽 10.5)", 1), ("y", 339.5, 388.5, "Pi 보스 49", 2),
                  ("y", 337.5, 384.5, "앰프 보스 47", 3), ("y", 299.0, 379.0, "고무발 보스 80", 4),
                  ("z", z0, z1, "11.5", 0), ("z", zs0, zs1, "윗판 3.0", 1), ("z", z1, pi["z"][1], "Pi 보스 6", 2),
                  ("z", z0, fb["z"][1], "고무발 보스 16", 3), ("z", z1, 48.5, "칸막이 탭 15", 4),
                  ("z", z0, zs0, "보스 밑 Ø9 기둥 8.5 (밑면부터)", 5)])


# ------------------------------------------------------------------ CU lid

def cu_lid(C, out):
    L = next(p for p in C["printed"] if p["id"] == "PR-CU-LID")
    st = L["structure"]
    x0, x1 = L["box"]["x"]
    y0, y1 = L["box"]["y"]
    z0, z1 = L["box"]["z"]
    zs0, zs1 = st["top_skin_z"]
    wall = st["perimeter_wall"]
    rt = st["underside_ribs"]["t"]
    add = [box(x0, x1, y0, y1, zs0, zs1),
           diff(box(x0, x1, y0, y1, z0, zs0 + 0.01), [box(x0 + wall, x1 - wall, y0 + wall, y1 - wall, z0 - 0.01, zs0 + 0.02)])]
    for rx in (564.0, 604.0, 644.0, 684.0):                     # between the vent slots
        add.append(box(rx - rt / 2, rx + rt / 2, y0 + wall - 0.01, y1 - wall + 0.01, z0, zs0 + 0.01))
    for ry in (255.0, 295.0, 335.0, 375.0):
        add.append(box(x0 + wall - 0.01, x1 - wall + 0.01, ry - rt / 2, ry + rt / 2, z0, zs0 + 0.01))
    sup = next(p for p in C["printed"] if p["id"] == "PR-LID-SUP")
    for ins in sup["instances"]:
        if ins["bay"] == "cu_bay":                              # solid bearing pads over the 4 CU corner supports
            bb = ins["box"]
            add.append(box(bb["x"][0], bb["x"][1], bb["y"][0], bb["y"][1], z0, zs0 + 0.01))
    lid = union(add)
    vs = next(f for f in L["features"] if f["name"] == "vent_slots")
    sw = vs["slot"][0]
    cuts = [box(vs["x_first"] + i * vs["pitch_x"] - sw / 2, vs["x_first"] + i * vs["pitch_x"] + sw / 2, vs["y"][0], vs["y"][1],
                z0 - 0.01, z1 + 0.01) for i in range(vs["count"])]
    lid = diff(lid, cuts)
    xl = vs["x_first"] + (vs["count"] - 1) * vs["pitch_x"]
    out.add("CU-LID", "CU 뚜껑(출력)", "CU lid (printed)", "print", G_CUP, lid, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-CU-LID (x520.5~719.5 y215~410 z110.5~122; 윗판 2.5, 테 3.0, 리브 2.0 피치 40; 통풍 슬롯 15개 4×100 피치 8)",
            note="추정: 리브 x564/604/644/684 (슬롯 사이)·y255/295/335/375, 모서리 받침 4곳 위 18×18 받침 면 (자석 Ø8×3을 이 면 z110.5에 붙임)",
            print_name="CU뚜껑", R=R_FLIP,
            print_note="윗면(z122)을 베드에, 리브가 위. 서포트 없음. 뚜껑 쪽 자석은 받침 자석에 붙여 놓고 순간접착제로 자리 맞춤(대각 2곳)",
            dims=[("x", x0, x1, "199 (틈 0.5씩)", 0), ("x", vs["x_first"] - sw / 2, xl + sw / 2, "통풍 슬롯 15 × 4, 피치 8", 1),
                  ("y", y0, y1, "195", 0), ("y", vs["y"][0], vs["y"][1], "슬롯 100", 1),
                  ("z", z0, z1, "11.5", 0), ("z", zs0, zs1, "윗판 2.5", 1)])


# ------------------------------------------------------------------ I/O plate

def io_plate(C, out):
    P = next(p for p in C["printed"] if p["id"] == "PR-IO-PLATE")
    st = P["structure"]
    fe = {f["name"]: f for f in P["features"]}
    x0, x1 = P["box"]["x"]
    y0, y1 = P["box"]["y"]
    z0, z1 = P["box"]["z"]
    ys0 = st["outer_skin_y"][0]                                 # 408
    fw = st["perimeter_frame"]["w"]
    rt = st["ribs"]["t"]
    tabs = fe["divider_screw_tabs"]["tabs"]          # the I/O plate's own tabs (A8 applies to the tray only)
    txl = max(t["box"]["x"][1] for t in tabs if t["side"] == "left")      # 528.75
    txr = min(t["box"]["x"][0] for t in tabs if t["side"] == "right")     # 711.25
    add = [box(x0, x1, ys0, y1, z0, z1),                                   # outer skin 2.0
           box(x0, x1, y0, y1, z0, z0 + fw), box(x0, x1, y0, y1, z1 - fw, z1),    # top / bottom frame
           box(x0, txl, y0, y1, z0, z1), box(txr, x1, y0, y1, z0, z1)]            # side frame, widened to carry the tabs
    for rx in (540.0, 585.0, 635.0, 680.0):                                # ribs clear of the openings
        add.append(box(rx - rt / 2, rx + rt / 2, y0, ys0 + 0.01, z0, z1))
    for rz in (57.0, 76.5):
        add.append(box(x0, x1, y0, ys0 + 0.01, rz - rt / 2, rz + rt / 2))
    # pedal-jack ledge + 2 gussets under it
    pj = fe["pedal_jack_hole"]
    led = pj["mount"]["box"]
    add.append(B(led))
    for gx in (led["x"][0] + 1.5, led["x"][1] - 1.5):
        add.append(prism_x([(ys0 + 0.01, led["z"][0] - 15.5), (ys0 + 0.01, led["z"][0] + 0.01), (ys0 - 20.0, led["z"][0] + 0.01)],
                           gx - 0.8, gx + 0.8))
    # USB-C / PD-trigger pocket block
    uc = fe["usb_c_input"]
    add.append(B(uc["pocket"]["block"]))
    # tabs
    add += [B(t["box"]) for t in tabs]
    plate = union(add)

    cuts = []
    cxj, czj = pj["center_xz"]
    cuts.append(cyl_y(cxj, czj, ys0 - 0.01, y1 + 0.01, pj["d"]))
    for (hx, hy) in ((551.0, 392.0), (569.0, 402.0)):                      # Ø2.7 blind 7 deep from the ledge top
        cuts.append(hole("z", hx, hy, led["z"][1] - 7.0, led["z"][1] + 0.01, 2.7, apex=(0, -1)))
    sw = fe["power_switch_hole"]
    sx, sz = sw["center_xz"]
    w, h = sw["size_xz"]
    cuts.append(box(sx - w / 2, sx + w / 2, ys0 - 0.01, y1 + 0.01, sz - h / 2, sz + h / 2))
    ux, uz = uc["center_xz"]
    cuts.append(stadium_y(ux, uz, uc["size_xz"][0], uc["size_xz"][1], ys0 - 0.01, y1 + 0.01))
    cav = uc["pocket"]["cavity"]
    cuts.append(box(cav["x"][0], cav["x"][1], uc["pocket"]["block"]["y"][0] - 0.01, ys0 + 0.01, cav["z"][0], cav["z"][1]))  # open -y
    cp = fe["cable_pass_hole"]
    px, pz = cp["center_xz"]
    cuts.append(stadium_y(px, pz, cp["size_xz"][0], cp["size_xz"][1], y0 - 0.01, y1 + 0.01))
    for t in tabs:
        hx, hy, hz = t["hole_center"]
        cuts.append(hole("x", hy, hz, t["box"]["x"][0] - 0.01, t["box"]["x"][1] + 0.01, 4.5, apex=(-1, 0)))
    plate = diff(plate, cuts)
    out.add("CU-IOPLATE", "I/O 판", "I/O plate (printed CU-bay back wall)", "print", G_CUP, plate, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-IO-PLATE (x520.2~719.8 y398.5~410 z33.5~110.3; 바깥 판 2.0; 페달 잭 Ø6.5 x560, 스위치 13.2×19.2 x610, "
                           "USB-C 13.5×8 x660 + PD 트리거 포켓, 선 통과 18×11 x700 - 모두 z92; 칸막이 탭 4)",
            note="추정: 속 빈 판 - 좌우 테를 탭 끝(x528.75 / x711.25)까지 넓힘, 리브 x540/585/635/680·z57/76.5 (구멍 피함), "
                 "페달 잭 선반 밑 삼각 보강 2개(1.6), PD 트리거 포켓은 안쪽(-y)으로 열림(블록 앞 벽까지 관통)",
            print_name="IO판", R=R_YMAX,
            print_note="바깥면(y410)을 베드에. 스위치·잭·USB-C 구멍은 수직, 탭 구멍·선반 파일럿은 눈물방울 - 서포트 없음. "
                       "13 mm 피스 ×4로 칸막이·낮은 칸막이 뒤끝 옆면에",
            dims=[("x", x0, x1, "199.6", 0), ("x", x0, cxj, "페달 잭 x560 (Ø6.5)", 1), ("x", x0, sx, "스위치 x610 (13.2×19.2)", 2),
                  ("x", x0, ux, "USB-C x660 (13.5×8)", 3), ("x", x0, px, "선 통과 x700 (18×11)", 4),
                  ("y", y0, y1, "11.5", 0), ("y", ys0, y1, "바깥 판 2.0", 1), ("y", led["y"][0], ys0, "잭 선반 24", 2),
                  ("z", z0, z1, "76.8", 0), ("z", z0, 92.0, "구멍 중심 z92", 1), ("z", led["z"][0], led["z"][1], "선반 8", 2)])


# ------------------------------------------------------------------ lid corner supports + magnets

def lid_supports(C, out):
    S = next(p for p in C["printed"] if p["id"] == "PR-LID-SUP")
    pk = S["part"]["magnet_pocket"]
    sx, sy, sz = S["part"]["size"]
    top = S["part"]["top_z"]
    base = diff(box(-sx / 2, sx / 2, -sy / 2, sy / 2, top - sz, top), [cyl_z(0, 0, top - pk["depth"], top + 0.01, pk["d"])])
    mag = cyl_z(0, 0, 0, 3.0, 8.0)
    z_sup = top - pk["depth"]                                   # 104.3
    for ins in S["instances"]:
        bb = ins["box"]
        cx, cy = (bb["x"][0] + bb["x"][1]) / 2.0, (bb["y"][0] + bb["y"][1]) / 2.0
        pc = ins["pocket_center"]
        m = base.translate((cx, cy, 0.0))
        out.add("CU-LIDSUP-%s" % ins["tag"], "뚜껑 모서리 받침(자석 자리) %s" % ins["tag"], "lid corner support " + ins["tag"], "print",
                G_CUP, m, COLORS["printed_body"], "PETG",
                source=SRC_C + " PR-LID-SUP %s (18×18×12, 윗면 z110.5, 포켓 Ø8.2 깊이 6.2 중심 (%.2f, %.2f))" % (ins["tag"], pc[0], pc[1]),
                note="추정: 받침 크기 18×18×12·포켓 깊이 6.2 (spec assumed); 모서리 두 합판 면에 목공본드",
                print_name="뚜껑모서리받침", R=R_NONE,
                print_note="밑면을 베드에, 자석 포켓이 위. 12개 모두 포켓, 6개(대각)에 자석",
                dims=[("x", bb["x"][0], bb["x"][1], "18", 0), ("x", pc[0] - pk["d"] / 2, pc[0] + pk["d"] / 2, "포켓 Ø8.2", 1),
                      ("y", bb["y"][0], bb["y"][1], "18", 0), ("z", bb["z"][0], bb["z"][1], "12", 0),
                      ("z", top - pk["depth"], top, "포켓 깊이 6.2", 1)])
        if ins["magnet"]:
            out.add("CU-MAG-SUP-%s" % ins["tag"], "네오디뮴 자석 Ø8×3 N35 (L65) — 받침 포켓 바닥 %s" % ins["tag"],
                    "magnet 8x3 N35 in support " + ins["tag"], "bought", G_CUP, mag.translate((pc[0], pc[1], z_sup)),
                    COLORS["magnet"], "N35", source=SRC_C + " PR-LID-SUP magnet_method (z104.3~107.3); F12")
            out.add("CU-MAG-LID-%s" % ins["tag"], "네오디뮴 자석 Ø8×3 N35 (L65) — 뚜껑 밑면 %s" % ins["tag"],
                    "magnet 8x3 N35 on the lid underside " + ins["tag"], "bought", G_CUP, mag.translate((pc[0], pc[1], top - 3.0)),
                    COLORS["magnet"], "N35", source=SRC_C + " PR-LID-SUP magnet_method (뚜껑 밑면 z110.5에 붙여 포켓 위 z107.5~110.5로 내려옴, 틈 0.2); F12")


# ------------------------------------------------------------------ power-bank holder

def pb_holder(C, out):
    H = next(p for p in C["printed"] if p["id"] == "PR-PB-HOLDER")
    g = H["geometry"]
    sp = g["screw_pads"]
    st = g["strap"]
    hk = st["right_hook"]["box"]
    add = [B(g["base"]["box"]), B(g["left_stop_wall"]), B(g["front_stop_wall"])]
    add += [cyl_z(px, py, sp["z"][0], sp["z"][1], sp["d"]) for (px, py) in sp["at"]]
    hy0, hy1 = hk["y"][0] - 2.0, hk["y"][1] + 2.0                  # hook widened 2 each side so the 22 strap slot is closed
    add.append(box(hk["x"][0], hk["x"][1], hy0, hy1, hk["z"][0] - 0.01, hk["z"][1]))
    hold = union(add)
    cuts = [cyl_z(px, py, sp["z"][0] - 0.01, sp["z"][1] + 0.01, sp["hole"]) for (px, py) in sp["at"]]
    ls = st["left_slot"]
    lx, ly, lz = ls["center"]
    wy, wz = ls["size_yz"]
    lw = g["left_stop_wall"]["x"]
    cuts.append(box(lw[0] - 0.01, lw[1] + 0.01, ly - wy / 2, ly + wy / 2, lz - wz / 2, lz + wz / 2))
    rs = st["right_hook"]
    cuts.append(box(hk["x"][0] - 0.01, hk["x"][1] + 0.01, hk["y"][0], hk["y"][1], rs["slot_z"][0], rs["slot_z"][1]))
    hold = diff(hold, cuts)
    bx_ = H["box"]
    out.add("CU-PBHOLDER", "보조배터리 받침 + 끈 고리", "power-bank holder + strap hook", "print", G_CUP, hold, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-PB-HOLDER (바닥 190×100×2 x731~921 y227.5~327.5; 멈춤벽 왼쪽 x737~741·앞 y227.5~231.5 z35.5~50.5; "
                           "나사 받침 Ø10×3 ×4 구멍 Ø4.5; 끈 슬롯 22×3 / 고리 슬롯 22×4)",
            note="추정: 오른쪽 끈 고리를 y261~287 (spec 263~285보다 2씩 넓힘) - 22 슬롯이 고리 폭과 같아 고리가 떨어지므로 양옆 2 mm 기둥을 남김. "
                 "끈(20 mm 벨크로)은 BOM에 없음",
            print_name="보조배터리받침", R=R_NONE,
            print_note="바닥을 베드에. 끈 슬롯은 브리지 22. 서포트 없음. 13 mm 피스 ×4로 바닥 오른쪽 합판에 (물림 10)",
            dims=[("x", bx_["x"][0], bx_["x"][1], "190", 0), ("x", 741.0, 911.0, "배터리 칸 170", 1),
                  ("y", bx_["y"][0], bx_["y"][1], "100", 0), ("y", 231.5, 316.5, "배터리 칸 85", 1), ("y", hk["y"][0], hk["y"][1], "끈 슬롯 22", 2),
                  ("z", 33.5, 35.5, "바닥 2", 0), ("z", 33.5, 50.5, "멈춤벽 17", 1), ("z", 33.5, hk["z"][1], "끈 고리 22", 2)])


# ------------------------------------------------------------------ spare-key storage insert + small-parts box

def ks_insert(C, out):
    K = next(p for p in C["printed"] if p["id"] == "PR-KS-INSERT")
    g = K["geometry"]
    gu = g["gussets"]
    wl = g["wall"]["x"][1]
    fz = g["flange"]["z"][1]
    add = [B(g["wall"]), B(g["flange"])]
    for gy in gu["y"]:
        add.append(prism_y([(wl - 0.01, fz - 0.01), (wl + gu["size_xz"][0], fz - 0.01), (wl - 0.01, fz + gu["size_xz"][1])],
                           gy - gu["t"] / 2, gy + gu["t"] / 2))
    ins = union(add)
    sh = g["screw_holes"]
    ins = diff(ins, [cyl_z(px, py, 33.49, fz + 0.01, sh["d"]) for (px, py) in sh["at"]])
    out.add("CU-KSINSERT", "예비 건반 보관함 칸막이(출력)", "spare-key storage insert wall", "print", G_CUP, ins, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-KS-INSERT (벽 1.2 x376.8~378 y226.7~398.3 z33.5~107.5, 플랜지 x378~398 z33.5~36.5, 삼각 보강 1.2 ×3, 4-Ø4.5 x394)",
            note="추정: v4 DESIGN §13은 벽 1.2 위치만 정함 - 플랜지·보강·나사 자리는 spec 제안",
            print_name="보관함칸막이", R=R_NONE,
            print_note="플랜지를 베드에, 벽이 서도록(172×21.2 바닥, 높이 74). 서포트 없음. 13 mm 피스 ×4로 바닥 왼쪽 합판에",
            dims=[("x", 376.8, 398.0, "21.2", 0), ("x", 376.8, 378.0, "벽 1.2", 1), ("y", 226.7, 398.3, "171.6 (앞뒤 0.2씩)", 0),
                  ("z", 33.5, 107.5, "74 (뚜껑 밑 3)", 0), ("z", 33.5, 36.5, "플랜지 3", 1)])


def small_box(C, out):
    Sb = next(p for p in C["printed"] if p["id"] == "PR-SMALL-BOX")
    g = Sb["geometry"]
    bx_ = Sb["box"]
    x0, x1 = bx_["x"]
    y0, y1 = bx_["y"]
    Z0 = 33.5                                            # stands on bottom_L (spec z36.5 = flange level; nothing under it there)
    H = g["outer"][2]
    wall, floor_t, lid_t = g["wall"], g["floor"], 1.6
    zr = Z0 + H - lid_t                                  # rim 61.9
    body = diff(box(x0, x1, y0, y1, Z0, zr), [box(x0 + wall, x1 - wall, y0 + wall, y1 - wall, Z0 + floor_t, zr + 0.01)])
    div_t, div_top = 1.2, zr - 3.5
    iw = (x1 - x0 - 2 * wall)
    divs = [box(x0 + wall + iw * k / 3.0 - div_t / 2, x0 + wall + iw * k / 3.0 + div_t / 2, y0 + wall - 0.01, y1 - wall + 0.01,
                Z0 + floor_t - 0.01, div_top) for k in (1, 2)]
    divs.append(box(x0 + wall - 0.01, x1 - wall + 0.01, (y0 + y1) / 2 - div_t / 2, (y0 + y1) / 2 + div_t / 2, Z0 + floor_t - 0.01, div_top))
    body = union([body] + divs)
    out.add("CU-SMALLBOX", "작은 부품 통", "small-parts box", "print", G_CUP, body, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-SMALL-BOX (80×60×30, 벽 1.6, 바닥 1.2, 칸 3×2, 끼움 뚜껑 1.6 + 치마 3; x410~490 y333~393)",
            note="추정: spec z36.5~66.5 대신 바닥 왼쪽 합판 위 z33.5~63.5에 놓음(플랜지는 x378~398뿐이라 그 높이에 받칠 곳이 없음); "
                 "통 몸 28.4 + 뚜껑 1.6 = 30, 칸막이 1.2는 뚜껑 치마를 피해 테두리보다 3.5 낮음",
            print_name="작은부품통", R=R_NONE, print_note="바닥을 베드에. 서포트 없음. 밸런스 핀·캡스턴 나사·센서 자석·PET 심 보관",
            dims=[("x", x0, x1, "80", 0), ("y", y0, y1, "60", 0), ("z", Z0, zr, "몸 28.4", 0), ("z", Z0, Z0 + floor_t, "바닥 1.2", 1)])
    cl, sk_t, sk_h = 0.2, 1.2, 3.0
    lid = union([box(x0, x1, y0, y1, zr, zr + lid_t),
                 diff(box(x0 + wall + cl, x1 - wall - cl, y0 + wall + cl, y1 - wall - cl, zr - sk_h, zr + 0.01),
                      [box(x0 + wall + cl + sk_t, x1 - wall - cl - sk_t, y0 + wall + cl + sk_t, y1 - wall - cl - sk_t, zr - sk_h - 0.01, zr + 0.02)])])
    out.add("CU-SMALLBOX-LID", "작은 부품 통 뚜껑", "small-parts box lid", "print", G_CUP, lid, COLORS["printed_body"], "PETG",
            source=SRC_C + " PR-SMALL-BOX lid (끼움 1.6 + 치마 3)",
            note="추정: 치마는 통 안쪽에 끼움(틈 0.2, 두께 1.2) - 바깥 80×60 유지",
            print_name="작은부품통_뚜껑", R=R_FLIP, print_note="윗면을 베드에, 치마가 위. 서포트 없음",
            dims=[("x", x0, x1, "80", 0), ("y", y0, y1, "60", 0), ("z", zr - sk_h, zr + lid_t, "4.6 (치마 3)", 0)])


# ------------------------------------------------------------------ entry point

def build():
    global GRILLE
    S = _load("body_speakers.json")
    C = _load("body_centre_unit.json")
    F = _load("keyaction_features_frame.json")
    GRILLE = build_grille(S)
    out = Out()
    speaker_parts(S, out)
    feet(S, out)
    joints(S, out)
    bracket(F, out)
    cu_panels(C, out)
    cu_tray(C, out)
    cu_lid(C, out)
    io_plate(C, out)
    lid_supports(C, out)
    pb_holder(C, out)
    ks_insert(C, out)
    small_box(C, out)
    return list(out)


if __name__ == "__main__":
    ps = build()
    for p in ps:
        b = p.solid.bounding_box()
        print("%-22s %-11s %-12s %3d  %s" % (p.id, p.kind, p.group, len(p.solid.decompose()), " ".join("%.2f" % v for v in b)))
    print(len(ps), "parts")
