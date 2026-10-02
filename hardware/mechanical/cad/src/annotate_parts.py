"""Dimensioned STLs: every distinct printed part (and the big bought / plywood parts) with its drawing
dimensions modelled as thin solids next to it.

Layout (part in its assembled orientation, moved so its bounding box starts at the origin):
  - x dimensions: front view, in the plane just in front of the part (read from the front, -y)
  - y dimensions: side view, in the plane just right of the part (read from the right, +x)
  - z dimensions: side view as well (vertical lines behind the part)
  - title + print hint lying on the floor in front of the part
Numbers are the design values (geometry.json / DESIGN.md tables / v3 tables); where a family table gives
a coordinate, the dimension is measured from the part's own origin feature (front lip y0, desk z0 ...).

L2 rear bar (2026-10-01): the body families (pods, baffle, duct former, centre panels, lids, back plate, hub shelf, brackets)
are computed from body.py (the one ANGLE constant), so a switch to 40 deg redraws the numbers. The plywood pieces are
written too (stl/annotated/08_합판재단/), one file per piece, since they are cut by hand. A part's own Part.dims come first;
family lines that repeat one of them are dropped and the rest are moved to the next free lanes.
"""
import os
import re

from annotate import dim2d, label2d, leader, to_plane
from cadlib import union, write_stl

# family tables: (axis, a, b, label, lane)  a/b are world y or z values (x uses the part bbox)
WK = [("y", 0.0, 199.0, "전체 199 (S09)", 0), ("y", 0.0, 50.0, "헤드 50", 1), ("y", 0.0, 67.0, "자석 y67 (P29)", 2),
      ("y", 0.0, 135.3, "밸런스 핀 y135.3 (P32)", 3), ("y", 0.0, 141.0, "봉 중심 K y141 (S03)", 4),
      ("y", 0.0, 188.34, "캡스턴 y188.34 (S08)", 5),
      ("z", 23.5, 43.5, "몸체 20 = z23.5~43.5 (S02)", 0), ("z", 20.75, 23.5, "노치 입술 z20.75", 1),
      ("z", 21.5, 43.5, "K z21.5 → 윗면", 2)]
BK = [("y", 54.2, 199.0, "전체 144.8", 0), ("y", 54.2, 67.0, "자석 y67 (P29)", 1), ("y", 54.2, 141.0, "앞끝→K 86.8 (S03)", 2),
      ("y", 54.2, 180.31, "캡스턴 y180.31 (S08)", 3),
      ("z", 23.5, 55.5, "몸체 32 = z23.5~55.5 (S02)", 0), ("z", 43.5, 55.5, "흑건 높이 12", 1)]
LV = [("y", 148.2, 207.55, "전체 59.35", 0), ("y", 150.0, 190.0, "강철 칸 40 (S12)", 1), ("y", 149.2, 203.25, "앞면→L 54.05 (S11)", 2),
      ("z", 33.0, 52.0, "강철 칸 19 (S12)", 0), ("z", 29.2, 53.0, "전체 23.8", 1), ("z", 33.5, 53.0, "L z33.5 → 윗면", 2)]
FR = [("y", 0.0, 212.0, "모듈 깊이 212 (A10)", 0), ("y", 0.0, 141.0, "건반 봉 K y141 (S03)", 1),
      ("y", 0.0, 203.25, "레버 봉 L y203.25 (S11)", 2), ("y", 144.5, 196.5, "기판 구멍 52 (P35)", 3),
      ("y", 146.5, 212.0, "윗판 y146.5~212 (P15)", 4),
      ("z", 3.0, 72.85, "프레임 69.85 = z3~72.85 (S18)", 0), ("z", 3.0, 21.5, "K z21.5", 1), ("z", 3.0, 33.5, "L z33.5", 2),
      ("z", 3.0, 20.054, "뒤 선반 z20.054 (S10)", 3)]
SB = [("y", 59.0, 77.5, "18.5 (P107)", 0), ("z", 8.6, 13.6, "5.0 (백 구간), 흑 구간 z11.5", 0)]
PB = [("y", 146.5, 185.0, "38.5 (P13)", 0), ("y", 170.0, 182.0, "패드 자리 12 (P16)", 1), ("z", 65.85, 68.85, "계단 3.0 (P13)", 0)]
CU = [("z", 45.5, 72.85, "27.35 (S27, 흑 노치 z57.5)", 0), ("y", 144.3, 148.0, "걸이 3.7 (P26)", 0)]
PL = [("z", 31.5, 35.5, "Ø4.0", 0)]

FAMILY = [
    (r"^백건_", WK), (r"^흑건_", BK), (r"^레버캐리어_", LV), (r"^(프레임_모듈|끝부속프레임)", FR),
    (r"^센서바", SB), (r"^패드바", PB), (r"^가림판띠", CU), (r"^레버봉끝마개", PL),
]

PLY_FOLDER = "08_합판재단"     # 07 is the touchscreen print folder (07_터치스크린)
_BODY = None


def body_families():
    """[(regex on the print name (printed parts) or the part id (plywood), dims)] of the L2 rear bar, from body.py."""
    global _BODY
    if _BODY is not None:
        return _BODY
    try:
        import body as B
    except Exception:                                               # body.py mid-edit: key-action families still work
        _BODY = []
        return _BODY
    Y0, YB, YBI, ZB, ZT, ZFB = B.Y0, B.YB, B.YBI, B.ZB, B.SPK_ZT, B.Z_FB
    dy1, dz1 = B.DUCT_Y[1], B.DUCT_Z[1]
    ang = "%.0f°" % B.ANGLE
    side = [("y", Y0, dy1, "통로 홈 %s (y%s~%s)" % (_f(dy1 - Y0), _f(Y0), _f(dy1)), 0),
            ("y", Y0, B.SL_A[0], "턱 %s" % _f(B.SL_A[0] - Y0), 1), ("y", Y0, B.SL_B[0], "사선 윗끝 %s" % _f(B.SL_B[0] - Y0), 2),
            ("y", B.SL_B[0], YB, "윗변 %s (뒤 y%s)" % (_f(YB - B.SL_B[0]), _f(YB)), 3),
            ("z", ZB, dz1, "통로 홈 %s (z%s~%s)" % (_f(dz1 - ZB), _f(ZB), _f(dz1)), 0),
            ("z", ZB, ZFB, "앞 모서리 %s" % _f(ZFB - ZB), 1),
            ("z", ZFB, ZT, "사선 %s %s (길이 %s, 윗면 z%s)" % (ang, _f(ZT - ZFB), _f(B.SL_LEN), _f(ZT)), 2)]
    fams = [(r"^SPK[LR]-PLY-SIDEOUT$", side)]
    for s_ in "LR":
        holes = [("y", Y0, y, "인서트 구멍 Ø%s×%s 막힘 y%s" % (_f(B.QS_HOLE[0]), _f(B.QS_HOLE[1]), _f(y)), 4 + k) for k, (y, z) in enumerate(B.TS_YZ[s_])]
        holes += [("z", ZB, z, "인서트 z%s" % _f(z), 3 + k) for k, (y, z) in enumerate(B.TS_YZ[s_])]
        wy, wz = B.WIRE_YZ[s_]
        holes += [("y", Y0, wy, "선 구멍 Ø6 y%s" % _f(wy), 6), ("z", ZB, wz, "선 구멍 z%s" % _f(wz), 5)]
        fams.append((r"^SPK%s-PLY-SIDEIN$" % s_, side + holes))
        feet = sorted(set(y for x, y in B.L2["feet"]["positions_xy"]["pod_" + s_]))
        fams.append((r"^SPK%s-PLY-BOTTOM$" % s_, [("y", B.RISER[0], y, "고무발 y%s" % _f(y), k) for k, y in enumerate(feet)]))
        wall = [("y", Y0, B.RISER[0], "통로 홈 27 (y214~241)", 0),
                ("y", Y0, wy, "XT30 구멍 Ø14 y%s" % _f(wy), 1)] + \
               [("y", Y0, y, "슬리브 Ø8 y%s" % _f(y), 2 + k) for k, (y, z) in enumerate(B.TS_YZ[s_])] + \
               [("y", Y0, B.MAG_END[s_][1], "자석 y%s" % _f(B.MAG_END[s_][1]), 4),
                ("z", ZB, dz1, "통로 홈 22 (z5~27)", 0), ("z", ZB, wz, "XT30 z%s" % _f(wz), 1)] + \
               [("z", ZB, z, "슬리브 z%s" % _f(z), 2 + k) for k, (y, z) in enumerate(B.TS_YZ[s_])]
        fams.append((r"^CU-PLY-END-%s$" % s_, wall))
    fams += [
        (r"^SPK[LR]-PLY-BACK$", [("y", YBI, YB, "11.5 (y%s~%s)" % (_f(YBI), _f(YB)), 0), ("z", ZB, ZT, "z%s~%s" % (_f(ZB), _f(ZT)), 0)]),
        (r"^SPK[LR]-PLY-TOP$", [("y", B.TOP_Y0, YBI, "%s (앞은 앞판 윗마개에 맞댐)" % _f(YBI - B.TOP_Y0), 0),
                                ("z", ZT - B.T, ZT, "윗면 z%s" % _f(ZT), 0)]),
        (r"^CU-PLY-BACK$", [("x", B.CU_X[0], B.BP_X[0], "창까지 %s" % _f(B.BP_X[0] - B.CU_X[0]), 0),
                            ("x", B.BP_X[0], B.BP_X[1], "뒤판 출력물 창 %s" % _f(B.BP_X[1] - B.BP_X[0]), 1),
                            ("x", B.BACK_SLOTS[0][0], B.BACK_SLOTS[-1][0] + 4, "환기 홈 8 × (4×15)", 2),
                            ("z", ZB, B.Z_BOT, "창 밑 %s" % _f(B.Z_BOT - ZB), 0), ("z", B.BACK_SLOTS[0][1], B.BACK_SLOTS[0][2], "환기 홈 z%s~%s" % (_f(B.BACK_SLOTS[0][1]), _f(B.BACK_SLOTS[0][2])), 1)]),
        (r"^CU-PLY-BOTTOM$", [("x", B.CU_IX[0], B.BOT_SLOTS_BUCK[0][0], "강압 흡기 홈까지 %s" % _f(B.BOT_SLOTS_BUCK[0][0] - B.CU_IX[0]), 0),
                              ("x", B.BOT_SLOTS_BUCK[0][0], B.BOT_SLOTS_BUCK[-1][0] + 4, "홈 6 × (4×34)", 1),
                              ("x", B.BOT_SLOTS_PI[0][0], B.BOT_SLOTS_PI[-1][0] + 4, "Pi 아래 홈 8 × (4×34)", 2),
                              ("y", B.RISER[0], B.BOT_SLOTS_BUCK[0][1], "강압 홈 y%s~%s (앞 모서리 R3)" % (_f(B.BOT_SLOTS_BUCK[0][1]), _f(B.BOT_SLOTS_BUCK[0][2])), 0),
                              ("y", B.RISER[0], B.BOT_SLOTS_PI[0][1], "Pi 홈 y%s~%s" % (_f(B.BOT_SLOTS_PI[0][1]), _f(B.BOT_SLOTS_PI[0][2])), 1)]),
        (r"^LID-L$", [("x", B.LIDS["LID-L"][0], B.LIDL_SLOTS[0][0], "배기 홈까지 %s" % _f(B.LIDL_SLOTS[0][0] - B.LIDS["LID-L"][0]), 0),
                      ("x", B.LIDL_SLOTS[0][0], B.LIDL_SLOTS[0][1], "홈 30", 1),
                      ("y", Y0, B.LIDL_SLOTS[0][2], "홈 6 × 4 y%s~" % _f(B.LIDL_SLOTS[0][2]), 0),
                      ("z", B.Z_LIDU, B.Z_LID, "11.5 (윗면 z%s = 건반 윗면)" % _f(B.Z_LID), 0)]),
        (r"^LID-R$", [("x", B.LIDS["LID-R"][0], B.LIDR_SLOTS[0][0], "배기 홈까지 %s" % _f(B.LIDR_SLOTS[0][0] - B.LIDS["LID-R"][0]), 0),
                      ("x", B.LIDR_SLOTS[0][0], B.LIDR_SLOTS[-1][0] + 4, "홈 10 × (4×40)", 1),
                      ("y", Y0, B.LIDR_SLOTS[0][1], "홈 y%s~%s" % (_f(B.LIDR_SLOTS[0][1]), _f(B.LIDR_SLOTS[0][2])), 0),
                      ("z", B.Z_LIDU, B.Z_LID, "11.5 (윗면 z%s = 건반 윗면)" % _f(B.Z_LID), 0)]),
        # printed (the parts carry their own Part.dims; these add the world positions)
        (r"^스피커앞판_경사배플_", [("y", B.SL_A[0], B.SL_B[0], "바깥면 뒤로 %s (%s, 경사 %s)" % (_f(B.SL_B[0] - B.SL_A[0]), ang, _f(B.SL_LEN)), 0),
                               ("z", ZFB, B.DRV_YZ[1], "유닛 중심 z%s" % _f(B.DRV_YZ[1]), 0)]),
        (r"^스피커통로틀", [("y", Y0, Y0 + B.FW_T + B.SILL[0], "앞판이 얹히는 면 %s" % _f(B.FW_T + B.SILL[0]), 0),
                         ("z", dz1, ZFB, "앞벽 z%s~%s" % (_f(dz1), _f(ZFB)), 0)]),
        (r"^뒤판출력물_IO", [("z", B.Z_BOT, B.BP_HOLES["pedal_jack_J501_D6"][1], "J501 z%s" % _f(B.BP_HOLES["pedal_jack_J501_D6"][1]), 0),
                          ("z", B.Z_BOT, B.BP_HOLES["rocker_KCD1_13.2x19.2"][1], "KCD1 z%s" % _f(B.BP_HOLES["rocker_KCD1_13.2x19.2"][1]), 1)]),
        (r"^허브선반", [("z", B.CC["PR-HUBSHELF"][4], B.BOARD_Z["AMP"], "앰프 밑면 z%s (선반 밑 z%s = 허브 윗면 z%s + 1)"
                        % (_f(B.BOARD_Z["AMP"]), _f(B.CC["PR-HUBSHELF"][4]), _f(B.HUB[5])), 0)]),
        # BRK2 (방진브래킷2_L/R): its own Part.dims already give leg, bolt pitch, arm, pin x/y/z (12 lines) - nothing to add
    ]
    _BODY = fams
    return _BODY


def family(name):
    for rx, t in FAMILY:
        if re.search(rx, name):
            return t
    for rx, t in body_families():
        if re.search(rx, name):
            return t
    return []


def family_of(p):
    """family dims of a Part (printed: by print name, anything else: by id)."""
    return family(p.print_name or "") if p.kind == "print" else family(p.id)


def merged_dims(fam, own):
    """own (Part.dims) first; family lines that repeat an own line are dropped, the rest go to the lanes after the own ones."""
    own = list(own or [])
    seen = set((ax, round(a, 1), round(b, 1)) for (ax, a, b, lab, ln) in own)
    top = {}
    for (ax, a, b, lab, ln) in own:
        top[ax] = max(top.get(ax, -1), ln)
    out = list(own)
    for (ax, a, b, lab, ln) in fam:
        if (ax, round(a, 1), round(b, 1)) in seen:
            continue
        out.append((ax, a, b, lab, ln + top.get(ax, -1) + 1))
    return out


def annotated(solid, name, dims_extra=(), title=None, extra_lines=()):
    x0, y0, z0, x1, y1, z1 = solid.bounding_box()
    W, D, H = x1 - x0, y1 - y0, z1 - z0
    size = max(2.5, min(7.0, max(W, D, H) / 38.0))
    lane = size * 2.6
    m = solid.translate((-x0, -y0, -z0))
    items = [m]
    # overall sizes
    # x : front view (plane y = -1), line above the part
    fx = dim2d((0, H), (W, H), size * 2.2, text="%s" % _f(W), size=size)
    items.append(to_plane(fx, "xz", (0, -1.0, 0)))
    # y and z : side view (plane x = W + 1)
    fy = dim2d((0, 0), (D, 0), -size * 2.2, text="%s" % _f(D), size=size)
    items.append(to_plane(fy, "yz", (W + 1.0, 0, 0)))
    fz = dim2d((D, 0), (D, H), -size * 2.2, text="%s" % _f(H), size=size)
    items.append(to_plane(fz, "yz", (W + 1.0, 0, 0)))
    # family dims (world y / z values -> local)
    ly = 0
    lz = 0
    fam = merged_dims(family(name), dims_extra) if dims_extra else list(family(name))
    nz = max([ln for (ax, a, b, lab, ln) in fam if ax == "z"] + [0])
    xlab = D + size * 2.2 + lane * (nz + 2)
    zlabels = []
    for (ax, a, b, lab, ln) in fam:
        if ax == "x":
            if a < x0 - 1e-6 or b > x1 + 1e-6:
                continue
            off = size * 2.2 + lane * (1 + ln)
            d = dim2d((a - x0, H), (b - x0, H), off, text="%s  %s" % (_f(b - a), lab), size=size * 0.8)
            items.append(to_plane(d, "xz", (0, -1.0, 0)))
            continue
        if ax == "y":
            if a < y0 - 1e-6 or b > y1 + 1e-6:
                continue
            off = -(size * 2.2 + lane * (1 + ln))
            d = dim2d((a - y0, 0), (b - y0, 0), off, text="%s  %s" % (_f(b - a), lab), size=size * 0.8)
            items.append(to_plane(d, "yz", (W + 1.0, 0, 0)))
            ly += 1
        elif ax == "z":
            if a < z0 - 1e-6 or b > z1 + 1e-6:
                continue
            off = -(size * 2.2 + lane * (1 + ln)) * 1.0
            d = dim2d((D, a - z0), (D, b - z0), off, text="", size=size * 0.8)
            xl = D - off
            zm = (a + b) / 2 - z0
            zlabels.append((zm, xl, "%s  %s" % (_f(b - a), lab)))
            items.append(to_plane(d, "yz", (W + 1.0, 0, 0)))
            lz += 1
    # z labels: horizontal, stacked so they never overlap, each with a leader to its dimension line
    zlabels.sort()
    last = -1e9
    for (zm, xl, s) in zlabels:
        zt = max(zm, last + size * 1.25)
        last = zt
        g = [leader((xl, zm), (xlab - 0.8, zt)), label2d(s, xlab, zt, size=size * 0.8)]
        items.append(to_plane(union([q for q in g if q is not None]), "yz", (W + 1.0, 0, 0)))
    # title on the floor in front
    t = title or name
    items.append(label2d(t, 0, -size * 4.0, size=size * 1.1))
    yy = -size * 6.0
    for s in extra_lines:
        items.append(label2d(s, 0, yy, size=size * 0.75))
        yy -= size * 1.6
    return union(items)


def _f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def _safe(s):
    s = s.replace("/", "·").replace(":", "-").replace("\\", "·")
    return re.sub(r"\s+", "_", s.strip())


def write_all(parts, rows, out):
    write_plywood(parts, out)
    byfile = {}
    for p in parts:
        f = getattr(p, "_print_file", None)
        if f and f not in byfile:
            byfile[f] = p
    for r in rows:
        if r.get("variant") or r["file"] not in byfile:
            continue            # print-only variants / copied tools have no assembled part to dimension
        p = byfile[r["file"]]
        stem = os.path.splitext(os.path.basename(r["file"]))[0].split("__")[0]
        lines = ["%s · %d개 · %s" % (p.name_ko, r["qty"], p.material),
                 "출력 크기 %.1f × %.1f × %.1f mm (베드 위 방향)" % tuple(r["size_mm"]),
                 "단위 mm · 조립 방향으로 표시 · 이 파일은 보기용 (출력 금지)"]
        a = annotated(p.solid, r["name"], dims_extra=p.dims, title=stem, extra_lines=lines)
        path = os.path.join(out, "stl", "annotated", r["folder"].replace("@extra/", "선택·대안·예비_"), stem + "_치수.stl")
        write_stl(a, path, "Toccata %s dimensioned (view only)" % p.id)


def write_plywood(parts, out):
    """one dimensioned view per plywood piece (cut by hand from the rectangles of the README cut list)."""
    for p in parts:
        if p.kind != "plywood":
            continue
        b = p.solid.bounding_box()
        d = sorted([b[3] - b[0], b[4] - b[1], b[5] - b[2]], reverse=True)
        stem = _safe(p.name_ko.split(" (")[0])
        lines = ["%s · 합판 재단 · %s" % (p.name_ko, p.material or "오꾸메 11.5T"),
                 "사각 재단 %s × %s, 두께 %s (직접 가공은 README '합판 재단' 표)" % (_f(d[0]), _f(d[1]), _f(d[2])),
                 "단위 mm · 조립 방향으로 표시 · 보기용 (출력 금지) · id %s" % p.id]
        name = p.id                     # family() looks plywood up by id
        a = annotated(p.solid, name, dims_extra=p.dims, title=stem, extra_lines=lines)
        path = os.path.join(out, "stl", "annotated", PLY_FOLDER, stem + "_치수.stl")
        write_stl(a, path, "Toccata %s dimensioned (view only)" % p.id)
