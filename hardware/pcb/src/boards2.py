"""Rev E physical sheets: BRD-03 PED board, BRD-04 centre-unit wiring (top view from the CAD), BRD-05 power/audio harnesses,
BRD-06 signal harnesses. Same engine and style as BRD-01/02 (sch.Sheet, A3, mm).

Every coordinate is either from the CAD (cad_extract.py -> netlist/cad_centre.json) or from the hole lattice of the board
(BE163 2.54 grid as the printed jig P-PED registers it). Each sheet also builds a self-check list (sheet.board_check) that
build.py prints: BRD-03 checks every wire route against the SCH-05 netlist (all pads of a net reached, no pad of another net
crossed, no wire under a support post).
"""
import html
import math

import harness as HN
import parts as P
from sch import Sheet

E = html.escape

NET_COL = {"GND": "#1d2433", "+3V3": "#c0392b", "PED_TIP": "#1f5fbf", "PED_ADC": "#2e8b57", "PED_VCC": "#b86e00",
           "PED_SEL": "#7a3fb0"}


def _pt(X, Y, p):
    return "%.2f,%.2f" % (X(p[0]), Y(p[1]))


def _path(polys, X, Y):
    d = []
    for pg in polys:
        d.append("M" + " L".join(_pt(X, Y, p) for p in pg) + " Z")
    return " ".join(d)


# ====================================================================== BRD-03 PED board
# BE163 piece 70 x 50 cut with the printed jig P-PED: board = CAD CU-E-PEDBOARD x426.5..476.5 (v) y244..314 (u), turned 90 deg.
# Jig frame: u = y - 244 (0..70, along the long side, u = 0 at the USB / front edge), v = 476.5 - x (0..50).
# Holes: u = 1.27 + 2.54 i (i = 0..27), v = 1.27 + 2.54 j (j = 0..19) - the jig puts both reference edges mid-gap.
PB_BOX = (426.5, 476.5, 244.0, 314.0)
PB_Z = (21.5, 23.1)                       # board on 5 mm posts (CAD)


def pb_x(j):
    return round(476.5 - 1.27 - 2.54 * j, 2)


def pb_y(i):
    return round(244.0 + 1.27 + 2.54 * i, 2)


# RP2040-Zero A501 snapped to the lattice: CAD box x449..467 y244..268.8 -> x -0.55, y -1.62 (nearest lattice place that keeps the
# USB-C plug in front of the board edge). Left column (pads 1..9) = j4, right column (pads 10..18) = j10, pad 1 / 10 = row i0.
ZERO_SNAP = (-0.55, -1.62)


def pb_zero_pad(n):
    if 1 <= n <= 9:
        return pb_x(4), pb_y(n - 1)
    if 10 <= n <= 18:
        return pb_x(10), pb_y(n - 10)
    return None


# pads of every part: ref -> [(pin, x, y)]. R503 = five 100 ohm resistors side by side (all pin 1 on one net, pin 2 on the other)
PB_PADS = {
    "J502": [("1", pb_x(5), pb_y(25)), ("2", pb_x(6), pb_y(25)), ("3", pb_x(7), pb_y(25)), ("4", pb_x(8), pb_y(25))],
    "R501": [("1", pb_x(5), pb_y(16)), ("2", pb_x(5), pb_y(19))],
    "R502": [("2", pb_x(5), pb_y(21)), ("1", pb_x(2), pb_y(21))],
    "C501": [("1", pb_x(4), pb_y(16)), ("2", pb_x(3), pb_y(16))],
    "JP504": [("2", pb_x(3), pb_y(8)), ("1", pb_x(3), pb_y(9))],
    "TP501": [("1", pb_x(4), pb_y(23))],
    "TP502": [("1", pb_x(11), pb_y(23))],
}
for _k, _j in enumerate(range(7, 12)):                     # R503a..e at j7..j11
    PB_PADS["R503" + "abcde"[_k]] = [("1", pb_x(_j), pb_y(19)), ("2", pb_x(_j), pb_y(22))]
PB_PADS["A501"] = [(str(n), *pb_zero_pad(n)) for n in range(1, 19)]

# wire routes on the underside. Insulated ribbon strands join ONLY at their two stripped ends (each end on a pad, on another strand's end
# or on a bare wire of the net); tinned bare wire (PB_BARE: the GND rail, the +3V3 / PED_VCC buses and short hops) is soldered at
# every pad it passes. boards3.route_check() checks exactly this (rev E review: GP26 / jack sleeve).
PB_ROUTES = {
    "GND": [[(pb_x(4), pb_y(1)), (pb_x(3), pb_y(1)), (pb_x(3), pb_y(3)), (pb_x(2), pb_y(3)), (pb_x(2), pb_y(23))],   # pad 2 -> rail (bare)
            [(pb_x(3), pb_y(9)), (pb_x(2), pb_y(9))],                                                                # JP504.1 -> rail
            [(pb_x(3), pb_y(16)), (pb_x(2), pb_y(16))],                                                              # C501.2 -> rail
            [(pb_x(8), pb_y(25)), (pb_x(8), pb_y(26)), (pb_x(3), pb_y(26)), (pb_x(3), pb_y(23)), (pb_x(2), pb_y(23))],  # J502.4 (sleeve) -> rail end (bare)
            [(pb_x(6), pb_y(25)), (pb_x(6), pb_y(26))]],                                                             # J502.2 (TN) -> that bare run (bare hop)
    "+3V3": [[(pb_x(4), pb_y(2)), (pb_x(6), pb_y(2)), (pb_x(6), pb_y(19)), (pb_x(11), pb_y(19))]],                    # pad 3 -> bus (bare)
    "PED_ADC": [[(pb_x(4), pb_y(6)), (pb_x(5), pb_y(6)), (pb_x(5), pb_y(16))],                                      # GP26 -> R501.1 (strand)
                [(pb_x(5), pb_y(16)), (pb_x(4), pb_y(16))]],                                                         # R501.1 -> C501.1 (bare hop)
    "PED_TIP": [[(pb_x(5), pb_y(19)), (pb_x(5), pb_y(25))],                       # R501.2 -> R502.2 -> J502.1 (bare, soldered at all three)
                [(pb_x(5), pb_y(23)), (pb_x(4), pb_y(23))]],                      # that bare run -> TP501 (bare hop)
    "PED_VCC": [[(pb_x(7), pb_y(25)), (pb_x(7), pb_y(22)), (pb_x(11), pb_y(22)), (pb_x(11), pb_y(23))]],             # J502.3 -> bus -> TP502 (bare)
    "PED_SEL": [[(pb_x(4), pb_y(8)), (pb_x(3), pb_y(8))]],                                                           # GP14 -> JP504.2 (strand)
}
PB_BARE = {("GND", 0), ("GND", 3), ("GND", 4), ("+3V3", 0), ("PED_VCC", 0), ("PED_TIP", 0), ("PED_TIP", 1), ("PED_ADC", 1)}
PB_PART_INFO = {
    "A501": ("RP2040-Zero", "윗면, 핀 헤더 1×9 ×2 (몰드 뺌), 밑면 부품 위 캡톤 · USB-C −y"),
    "R501": ("1 kΩ", "윗면 눕힘, 리드 7.62 (y 방향)"),
    "R502": ("100 kΩ", "윗면 눕힘, 리드 7.62 (x 방향)"),
    "R503": ("100 Ω × 5", "윗면 눕힘 5개 나란히 = 20 Ω (몸통이 닿아도 됨 — 같은 두 넷 사이 병렬)"),
    "C501": ("100 nF 1206", "아랫면, 이웃 패드 두 개에 걸쳐"),
    "JP504": ("닫음", "아랫면 납땜 브리지 (GP14 = GND → 'Toccata PED')"),
    "J502": ("W502 패드 1×4", "아랫면, 리본 가닥 4개 (1 T · 2 TN · 3 R · 4 S)"),
    "TP501": ("PED_TIP", "구멍 패드에 피복 벗긴 선 고리"),
    "TP502": ("PED_VCC", "구멍 패드에 선 고리"),
}


def _sch05_nets():
    import sheets
    s = sheets.sch05()
    s.connectivity()
    pin_net = {}
    for net, pins in s.nets.items():
        for p in pins:
            pin_net[p] = net
    return pin_net


def pb_check():
    """route check against SCH-05 (boards3.route_check: strands join only at their ends, bare wire at every pad it passes, one group per
    net, nothing over another net's pad or under a support post): returns (list of problems, {})."""
    import boards3 as B3
    pin_net = _sch05_nets()
    pads = {}                        # (x, y) -> (ref, pin, net)
    for ref, lst in PB_PADS.items():
        base = "R503" if ref.startswith("R503") else ref
        for pin, x, y in lst:
            net = pin_net.get(f"{base}.{pin}")
            if net is None or net.startswith("~"):          # single-pin anonymous net = NC pin (x on the schematic)
                net = "NC"
            pads[(round(x, 2), round(y, 2))] = (ref, pin, net)
    # support posts on the bottom side: 6 x 6 squares around the 4 fixing holes, +0.5 (edges count as inside)
    keep = [(hx - 3.51, hx + 3.51, hy - 3.51, hy + 3.51) for (hx, hy) in PB_HOLES_XY]
    probs = B3.route_check(pads, PB_ROUTES, keep=keep, bare=PB_BARE)
    # schematic pins of the PB board that have no pad
    pb_refs = {"A501", "R501", "R502", "R503", "C501", "JP504", "J502", "TP501", "TP502"}
    padded = {f"{('R503' if r.startswith('R503') else r)}.{p}" for (r, p, n) in pads.values()}
    for p, net in pin_net.items():
        if p.split(".")[0] == "A501" and int(p.split(".")[1]) >= 19:
            continue                                       # bottom-edge pads 19..23: no header (BRD-01 rule)
        if p.split(".")[0] in pb_refs and p not in padded:
            probs.append(f"schematic pin {p} ({net}) has no pad on BRD-03")
    return probs, {}


PB_HOLES = [(430.5, 248.0, 3.2, "M3 나사"), (472.5, 310.0, 3.2, "M3 나사"), (472.5, 248.0, 3.0, "위치 핀"), (430.5, 310.0, 3.0, "위치 핀")]
PB_HOLES_XY = [(h[0], h[1]) for h in PB_HOLES]


def _wire_len(poly):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(poly, poly[1:]))


def brd03():
    from sheets import TOTAL, REV_E
    s = Sheet("BRD-03", 10, TOTAL, "페달 보드 배치 (PB · 위에서 봄)",
              "BE163에서 자른 70 × 50 조각(지그 P-PED), 가운데 유닛 C칸 5 mm 기둥 위. 모든 구멍 = 지그가 맞추는 2.54 격자. 배선은 아랫면. 아래: J501 잭 조각, 페달 안 센서 조각.",
              "PB", qty="PB · J501 · PS", basis="CU-E-PEDBOARD · SCH-05", **REV_E)
    S = 2.0
    ox, oy = 46.0, 36.0
    x0b, x1b, y0b, y1b = PB_BOX

    def X(x):
        return ox + (x - x0b) * S

    def Y(y):
        return oy + (y1b - y) * S
    o = s.out["body"]
    # board + posts (dashed squares) + lattice
    o.append(f'<rect x="{X(x0b):.2f}" y="{Y(y1b):.2f}" width="{(x1b-x0b)*S:.2f}" height="{(y1b-y0b)*S:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".5"/>')
    for (hx, hy, d, t) in PB_HOLES:
        o.append(f'<rect x="{X(hx-3.0):.2f}" y="{Y(hy+3.0):.2f}" width="{6*S:.2f}" height="{6*S:.2f}" fill="#c9d0da" fill-opacity=".35" '
                 f'stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.2 .7"/>')
    for i in range(28):
        for j in range(20):
            x, y = pb_x(j), pb_y(i)
            edge = y + 0.5 > y1b
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r=".45" fill="{"#d7e3d4" if edge else "#b9cdb6"}"/>')
    for (hx, hy, d, t) in PB_HOLES:
        o.append(f'<circle cx="{X(hx):.2f}" cy="{Y(hy):.2f}" r="{d/2*S:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".4"/>')
    # Zero outline, receptacle, header rows
    zx0, zx1 = 449.0 + ZERO_SNAP[0], 467.0 + ZERO_SNAP[0]
    zy0, zy1 = 245.3 + ZERO_SNAP[1], 268.8 + ZERO_SNAP[1]
    o.append(f'<rect x="{X(zx0):.2f}" y="{Y(zy1):.2f}" width="{(zx1-zx0)*S:.2f}" height="{(zy1-zy0)*S:.2f}" rx="3" fill="#1f2a44" fill-opacity=".08" stroke="#1f2a44" stroke-width=".45"/>')
    rx0, rx1 = zx1 - 4.39 - 8.94, zx1 - 4.39
    ry0, ry1 = zy0 - 1.3, zy0 - 1.3 + 7.3
    o.append(f'<rect x="{X(rx0):.2f}" y="{Y(ry1):.2f}" width="{(rx1-rx0)*S:.2f}" height="{(ry1-ry0)*S:.2f}" fill="#c9d0da" stroke="#1f2a44" stroke-width=".3"/>')
    s.text(X((zx0 + zx1) / 2), Y(257.0), "A501", "ref", "middle", size=2.7)
    s.text(X((zx0 + zx1) / 2), Y(257.0) + 3.0, "RP2040-Zero", "notes", "middle", size=1.9)
    pin_net = _sch05_nets()
    names = dict(P.RP2040_ZERO)
    for n in range(1, 19):
        x, y = pb_zero_pad(n)
        net = pin_net.get(f"A501.{n}")
        used = net not in (None,)
        col = NET_COL.get(net, "#fff")
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{0.6*S:.2f}" fill="{col if used else "#fff"}" stroke="#1f2a44" stroke-width=".3"/>')
        nm = names[n]
        if n <= 9:
            s.text(X(x) - 1.9, Y(y) + 0.7, nm, "pinname", "end", size=1.6, check=False)
        else:
            s.text(X(x) + 1.9, Y(y) + 0.7, nm, "pinname", "start", size=1.6, check=False)
    # routes (underside): dashed, net colour; bare buses solid and thicker
    for net, routes in PB_ROUTES.items():
        for k, poly in enumerate(routes):
            bare = (net, k) in PB_BARE
            pts = " ".join(_pt(X, Y, p) for p in poly)
            dash = "" if bare else ' stroke-dasharray="1.4 .7"'
            o.append(f'<polyline points="{pts}" fill="none" stroke="{NET_COL.get(net, "#444")}" stroke-width="{0.9 if bare else 0.5}" '
                     f'stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".85"{dash}/>')
    # parts
    def pad(x, y, net, sq=False):
        c = NET_COL.get(net, "#fff")
        if sq:
            o.append(f'<rect x="{X(x)-1.3:.2f}" y="{Y(y)-1.3:.2f}" width="2.6" height="2.6" fill="#fff" stroke="{c}" stroke-width=".5"/>')
        else:
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.05" fill="{c}" stroke="#1f2a44" stroke-width=".25"/>')
    for ref, lst in PB_PADS.items():
        if ref == "A501":
            continue
        base = "R503" if ref.startswith("R503") else ref
        for pin, x, y in lst:
            pad(x, y, pin_net.get(f"{base}.{pin}"), sq=ref == "J502")
        if ref.startswith("R50"):
            (p1, xa, ya), (p2, xb, yb) = lst
            if abs(xa - xb) < 0.01:
                o.append(f'<rect x="{X(xa)-1.25:.2f}" y="{Y(max(ya, yb))+1.6:.2f}" width="2.5" height="{abs(ya-yb)*S-3.2:.2f}" rx=".8" '
                         f'fill="#f3e3c3" fill-opacity=".85" stroke="#8a5a00" stroke-width=".3"/>')
            else:
                o.append(f'<rect x="{X(min(xa, xb))+1.6:.2f}" y="{Y(ya)-1.25:.2f}" width="{abs(xa-xb)*S-3.2:.2f}" height="2.5" rx=".8" '
                         f'fill="#f3e3c3" fill-opacity=".85" stroke="#8a5a00" stroke-width=".3"/>')
        if ref == "C501":
            (p1, xa, ya), (p2, xb, yb) = lst
            o.append(f'<rect x="{X(min(xa, xb))-0.4:.2f}" y="{Y(ya)-1.6:.2f}" width="{abs(xa-xb)*S+0.8:.2f}" height="3.2" fill="none" '
                     f'stroke="#b86e00" stroke-width=".4" stroke-dasharray=".9 .5"/>')
        if ref == "JP504":
            (p1, xa, ya), (p2, xb, yb) = lst
            o.append(f'<rect x="{X(xa)-0.9:.2f}" y="{Y(max(ya, yb)):.2f}" width="1.8" height="{abs(ya-yb)*S:.2f}" fill="#7a3fb0" fill-opacity=".45"/>')
        if ref.startswith("TP"):
            x, y = lst[0][1], lst[0][2]
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.9" fill="none" stroke="#1f5fbf" stroke-width=".45"/>')
    # part labels (placed beside the parts)
    # part labels in sheet mm, offsets chosen so no label sits on a pad or a wire
    lab = [("J502", X(pb_x(6.5)), Y(pb_y(25)) - 3.2, "middle"), ("R501", X(pb_x(5)) + 2.0, Y(pb_y(17.5)) + 0.8, "start"),
           ("R502", X(pb_x(3.5)), Y(pb_y(21)) + 4.4, "middle"), ("R503 ×5", X(pb_x(9)), Y(pb_y(19)) + 4.6, "middle"),
           ("C501", X(pb_x(3.5)), Y(pb_y(16)) + 4.4, "middle"), ("JP504", X(pb_x(2)) + 1.8, Y(pb_y(8.5)) + 0.8, "start"),
           ("TP501", X(pb_x(4)), Y(pb_y(23)) + 5.0, "middle"), ("TP502", X(pb_x(11)) - 2.6, Y(pb_y(23)) + 0.8, "end")]
    for t, x, y, a in lab:
        s.text(x, y, t, "ref", a, size=2.1, check=False)
    s.text(X(pb_x(2)) + 1.8, Y(pb_y(13)), "GND 레일", "pinname", "start", size=1.8, check=False)
    s.text(X(pb_x(11)) - 2.2, Y(pb_y(22)) + 2.6, "PED_VCC 버스", "pinname", "end", size=1.7, check=False)
    s.text(X(pb_x(11)) - 2.2, Y(pb_y(19)) + 0.7, "+3V3 버스", "pinname", "end", size=1.7, check=False)
    # rulers: world x / v (bottom), world y / u (left) + lattice indices
    for j in range(0, 20, 5):
        x = pb_x(j)
        s.line(X(x), Y(y0b) + 2, X(x), Y(y0b) + 5, "bodyl", "text")
        s.text(X(x), Y(y0b) + 7.6, f"j{j}", "tblm", "middle", size=1.7, check=False)
        s.text(X(x), Y(y0b) + 10.0, f"x{x:.2f}", "tblm", "middle", size=1.6, check=False)
    for i in range(0, 28, 5):
        y = pb_y(i)
        s.line(X(x0b) - 5, Y(y), X(x0b) - 2, Y(y), "bodyl", "text")
        s.text(X(x0b) - 5.6, Y(y) + 0.7, f"i{i} y{y:.2f}", "tblm", "end", size=1.6, check=False)
    for x in (x0b, x1b):
        s.text(X(x), Y(y1b) - 2.0, f"x{x:g}", "tblm", "middle", size=1.7, check=False)
    s.text(X(x1b) + 1.5, Y(y1b) + 1.0, f"y{y1b:g}", "tblm", "start", size=1.7, check=False)
    s.text(X(x1b) + 1.5, Y(y0b) + 1.0, f"y{y0b:g}", "tblm", "start", size=1.7, check=False)
    s.text(X(x0b), Y(y0b) + 13.6, "앞 (연주자 쪽, −y) · USB-C → W208 → 허브 포트 2 · USB 끝 = 지그 '◀USB 끝' (u = 0)", "notes", size=2.0)
    s.text(X(x0b), Y(y1b) - 5.0, "뒤 (+y) → 뒤판 J501 · 척도 2 : 1 · 위에서 봄 (모델 좌표 mm)", "notes", size=2.0)
    for (hx, hy, d, t) in PB_HOLES:
        s.text(X(hx), Y(hy) + (5.4 if hy < 270 else -4.2), f"{t} Ø{d:g}", "notes", "middle", size=1.7, check=False)
    # placement table
    rows = []
    for ref in ("A501", "R501", "R502", "R503", "C501", "JP504", "J502", "TP501", "TP502"):
        val, how = PB_PART_INFO[ref]
        if ref == "R503":
            xs = [PB_PADS["R503" + c][0][1] for c in "abcde"]
            pos = f"x{min(xs):.2f}~{max(xs):.2f} · y{pb_y(19):.2f}/{pb_y(22):.2f}"
        elif ref == "A501":
            pos = f"패드 1~9 x{pb_x(4):.2f}, 10~18 x{pb_x(10):.2f} · y{pb_y(0):.2f}~{pb_y(8):.2f}"
        else:
            pos = " · ".join(f"{p}({x:.2f},{y:.2f})" for p, x, y in PB_PADS[ref])
        rows.append([ref, val, pos, how])
    s.table(160, 30, ["부품", "값", "구멍 (모델 좌표, 핀(x,y))", "실장"], rows, [14, 26, 82, 128],
            title="배치표 — 구멍 x = 475.23 − 2.54·j, y = 245.27 + 2.54·i (지그 P-PED 격자)", mono_cols=(0, 2))
    # wiring list (underside)
    wr = []
    for net, routes in PB_ROUTES.items():
        for k, poly in enumerate(routes):
            a, b = poly[0], poly[-1]
            wr.append([net, f"({a[0]:.2f},{a[1]:.2f})", f"({b[0]:.2f},{b[1]:.2f})", f"{len(poly)-1}", f"{_wire_len(poly):.1f}",
                       "주석 입힌 맨선" if (net, k) in PB_BARE else "리본 가닥 (피복)"])
    yt = s.table(160, 72, ["넷", "시작", "끝", "꺾임 수", "직각 길이", "선"], wr, [20, 34, 34, 18, 22, 40],
                 title="아랫면 배선 (꺾인 점은 모두 격자 구멍 위) — netlist/wiring_PB.csv", mono_cols=(0, 1, 2, 3, 4))
    # self check
    probs, reached = pb_check()
    s.board_check = probs
    s.text(160, yt + 4.0, ("배선 검사: SCH-05 넷 %d개가 넷마다 한 덩어리(피복 가닥은 두 끝에서만 이음), 다른 넷 패드·기둥 밑을 안 지남 (문제 0)" % len(PB_ROUTES))
           if not probs else "배선 검사 문제 %d건 — build.py 출력 확인" % len(probs), "noteb", size=2.2)
    # notes
    s.para(160, yt + 9.0, [
        "주",
        "1. 기판: 사용자 Coms BE163(80 × 120, 구멍 30 × 42)에서 지그 P-PED로 70 × 50을 긋고 꺾는다. 나사 Ø3.2 ×2, 위치 핀 Ø3.0 ×2를 지그 안내 구멍으로 먼저 뚫는다.",
        "    지그는 USB 끝(u = 0)·왼쪽 모서리를 구멍 사이 가운데(구멍에서 1.27)에 둔다 → 구멍 (i, j) = (u, v) = (1.27 + 2.54·i, 1.27 + 2.54·j).",
        f"2. A501은 CAD 상자(x449~467 y244~268.8)보다 x {ZERO_SNAP[0]:+.2f}, y {ZERO_SNAP[1]:+.2f} — 핀이 격자 구멍에 들어가는 가장 가까운 자리. USB-C 리셉터클 면 y{ry0:.2f}는",
        "    기판 앞 모서리 y244보다 1.62 앞이라 플러그 몰드가 기판에 걸리지 않는다. 플러그 축 x457.59 (CAD 458.14).",
        "3. 순서: 패드·저항·JP504 → 아랫면 배선 → 핀 헤더(몰드 뺌) → 캡톤 → A501 → W502(J501 조각과 함께). △28 맨선(굵은 실선: GND 레일·버스·PED_TIP 줄·짧은 다리)은",
        "    지나는 패드마다 납땜, 리본 가닥(점선)은 두 끝만 벗겨 끝의 패드·맨선에 납땜 — 가닥 중간은 아무것도 잇지 않는다.",
        "    점선 네모 = 받침 기둥 6 × 6 (아랫면이 닿는 자리) — 배선·납땜 혹 금지. 아랫면 혹·핀 끝 ≤ 2 mm (기둥 5 mm 위).",
        "4. 확인 (멀티미터): A501을 꽂기 전 3V3–GND 단락 없음, GP26 패드–R501.1 = 0 Ω, J502.1–GP26 = 1 kΩ, J502.1–TP501 = 0 Ω,",
        "    J502.2–GND = 0 Ω, J502.4–GND = 0 Ω, J502.3–3V3 = 20 Ω (100 Ω ×5), J502.1–GND = 100 kΩ.",
        "    USB를 꽂은 뒤: 3V3 = 3.3 V, 페달을 꽂은 상태에서 J502.3 = 3.05 V 이상, 페달을 뺀 상태에서 GP26 ≈ 0 V.",
    ], size=2.0, lh=2.8)
    # ---------------- insets: J501 scrap (2 : 1) and the pedal sensor scrap PS (3 : 1)
    jb = HN.PTS.get("j501_board", [450.0, 475.0, 316.5, 340.5, 36.4, 38.0])
    jj = HN.PTS.get("j501", [459.5, 465.5, 328.5, 342.5, 38.0, 43.0])
    ix, iy, S2 = 18.0, 203.0, 2.0

    def XJ(x):
        return ix + (x - jb[0]) * S2

    def YJ(y):
        return iy + (jb[3] - y) * S2
    s.text(ix, iy - 7.5, "J501 잭 조각 (12 × 18 기판 자투리, 25 × 24) — 뒤판 출력물 잭 선반 위, 2 : 1", "noteb", size=2.3)
    o.append(f'<rect x="{XJ(jb[0]):.2f}" y="{YJ(jb[3]):.2f}" width="{(jb[1]-jb[0])*S2:.2f}" height="{(jb[3]-jb[2])*S2:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".45"/>')
    o.append(f'<rect x="{XJ(jj[0]):.2f}" y="{YJ(jj[3]):.2f}" width="{(jj[1]-jj[0])*S2:.2f}" height="{(jj[3]-jj[2])*S2:.2f}" fill="#222" fill-opacity=".75"/>')
    s.text(XJ(jj[1]) + 1.5, YJ(jj[3]) + 3.0, "← 잭 코 → 뒤판 Ø6 (y342.5)", "notes", "start", size=1.8, check=False)
    import boards3 as B3
    for (ref_, nm), (ii, jj_) in B3.J5_PADS.items():
        px, py_ = B3.j5x(ii), B3.j5y(jj_)
        o.append(f'<rect x="{XJ(px)-1.2:.2f}" y="{YJ(py_)-1.2:.2f}" width="2.4" height="2.4" fill="#fff" stroke="#8a5a00" stroke-width=".4"/>')
        s.text(XJ(px), YJ(py_) + 4.0, nm.split()[1], "pinname", "middle", size=1.7, check=False)
    s.para(XJ(jb[1]) + 4.0, iy + 4.0, [
        f"조각 x{jb[0]:g}~{jb[1]:g} × y{jb[2]:g}~{jb[3]:g} (CAD CU-E-J501BOARD), 잭 x{jj[0]:g}~{jj[1]:g}.",
        "구멍 좌표·잭 다리 연결 = BRD-07 (잭 다리는 2.54 격자 밖).",
        "앞 패드 4개(T·TN·R·S, y317.77)에 W502 4가닥 → PB J502 1·2·3·4.",
        "TN·S는 둘 다 GND — 통전으로 T/TN/R/RN/S를 먼저 찾는다.",
        "조각은 잭 선반에 MS 폴리머(구멍 없음). 붙이기 전에 W502 납땜.",
    ], "notes", size=1.9, lh=2.6)
    # PS scrap (same data as BRD-07): 7 x 5 holes, local frame (0, 0) = lower-left hole
    px0, py0, S3 = 172.0, 240.0, 3.0
    s.text(px0 - 4.0, py0 - 40.0, "PS 페달 안 센서 조각 (12 × 18 자투리 7 × 5 구멍) — 3 : 1, 위에서 봄 (구멍·배선 = BRD-07)", "noteb", size=2.3)

    def XP(x):
        return px0 + x * S3

    def YP(y):
        return py0 - y * S3
    o.append(f'<rect x="{XP(-1.27):.2f}" y="{YP(11.43):.2f}" width="{17.78*S3:.2f}" height="{12.7*S3:.2f}" fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".45"/>')
    for c in range(7):
        for r in range(5):
            o.append(f'<circle cx="{XP(2.54*c):.2f}" cy="{YP(2.54*r):.2f}" r=".5" fill="#b9cdb6"/>')
    o.append(f'<rect x="{XP(-1.0):.2f}" y="{YP(7.0):.2f}" width="{4.0*S3:.2f}" height="{4.0*S3:.2f}" fill="#222" fill-opacity=".8"/>')
    s.text(XP(1.0), YP(9.4), "U551 표시면 위", "notes", "middle", size=1.7, check=False)
    for net, polys in B3.PS_ROUTES.items():
        for poly in polys:
            d = " ".join("%.2f,%.2f" % (XP(x), YP(y)) for x, y in poly)
            o.append(f'<polyline points="{d}" fill="none" stroke="{B3.ncol(net)}" stroke-width=".8" stroke-opacity=".85"/>')
    o.append(f'<rect x="{XP(7.62)+1.6:.2f}" y="{YP(7.62)-1.2:.2f}" width="{7.62*S3-3.2:.2f}" height="2.4" rx=".8" fill="#f3e3c3" stroke="#8a5a00" stroke-width=".3"/>')
    for (ref_, pin_), (c, r) in B3.PS_PADS.items():
        o.append(f'<circle cx="{XP(2.54*c):.2f}" cy="{YP(2.54*r):.2f}" r="1.0" fill="{B3.ncol(B3.PS_NET[(ref_, pin_)])}"/>')
    s.text(XP(11.43), YP(7.62) - 2.2, "R551 1 kΩ", "ref", "middle", size=1.9, check=False)
    s.para(XP(17.78) + 2.0, py0 - 34.0, [
        "U551 리드 1·2·3 = 셋째 열(c2) r1·r2·r3(표시면 위, 리드 +x), C551 100 nF 1206은 아랫면 c3의 VCC–GND 사이.",
        "R551 1 kΩ(리드형)을 OUT 옆(c3 r3) → c6 r3: 3 m 선의 용량이 OUT에 바로 걸리지 않게(△7).",
        "W501 끝: 팁 → c6 r4, 링 → c6 r1, 슬리브 → c6 r2. 케이블 타이로 당김 방지.",
        "자석 Ø5×2 S극 아래, 눌렀을 때 약 4.5 mm · 뗐을 때 12 mm 이상(SCH-05 주 1).",
        "크기·구멍은 BRD-07대로 — 페달 바닥판에 붙일 자리만 현장에서 정한다(MS 폴리머).",
    ], "notes", size=1.9, lh=2.6)
    s.frame()
    s.expected = {}
    return s


def wiring_pb_rows():
    rows = []
    for net, routes in PB_ROUTES.items():
        for k, poly in enumerate(routes):
            rows.append([net, k + 1, " → ".join(f"({x:.2f},{y:.2f})" for x, y in poly), f"{_wire_len(poly):.1f}",
                         "주석 맨선" if (net, k) in PB_BARE else "리본 가닥"])
    return rows


def pb_pad_rows():
    pin_net = _sch05_nets()
    rows = []
    for ref, lst in PB_PADS.items():
        base = "R503" if ref.startswith("R503") else ref
        for pin, x, y in lst:
            j = round((476.5 - 1.27 - x) / 2.54)
            i = round((y - 244.0 - 1.27) / 2.54)
            net = pin_net.get(f"{base}.{pin}", "NC")
            if net.startswith("~"):                       # single-pin anonymous net = not connected
                net = "연결 금지 (USB VBUS)" if (ref == "A501" and pin == "1") else "NC"
            rows.append([ref, pin, net, f"{x:.2f}", f"{y:.2f}", i, j, f"{y-244.0:.2f}", f"{476.5-x:.2f}"])
    return rows


# ====================================================================== BRD-04 centre-unit wiring (top view, lids and screen off)
C_BOARD = ("CU-E-PEDBOARD", "CU-E-J702BOARD", "CU-E-J501BOARD")
C_MOD = ("CU-E-PI5", "PB-E-HUB", "CU-E-BUCK", "CU-E-AMP", "CU-E-PEDZERO")
C_RED = ("C-PWR-IN", "C-PWR-FUSE", "C-PWR-BUS", "C-PWR-5V", "C-BAT-LEAD")
C_SPK = ("C-SPK-L", "C-SPK-R", "C-SPKPIG-L", "C-SPKPIG-R")
LABELS04 = {   # refdes shown on the parts (id -> text)
    "BAT-LFP": "BT601 LiFePO4", "C-XT60": "X605⇄X606", "CU-E-FUSE": "F601", "CU-E-SWITCH": "SW601", "CU-E-BUCK": "A602 XL4016",
    "CU-E-PI5": "A603 Pi 5", "PB-E-HUB": "A604 허브", "CU-E-AMP": "A702 XH-A232", "CU-E-PEDBOARD": "PB", "CU-E-J702BOARD": "J702",
    "CU-E-J501BOARD": "J501", "CU-E-DONGLE": "A701", "CU-E-GENDER": "X701", "C-XT60F-L": "X704", "C-XT60M-L": "X703",
    "C-XT60F-R": "X706", "C-XT60M-R": "X705", "C-DC": "DC 충전",
}


def _style04(pid, kind):
    if kind in ("print", "plywood"):
        return 'fill="#f1f3f6" stroke="#b6bfcc" stroke-width=".2"'
    if pid == "BAT-LFP":
        return 'fill="#dbe6f3" stroke="#2f5d8a" stroke-width=".3"'
    if pid in C_BOARD:
        return 'fill="#eaf4e8" stroke="#2d6a3e" stroke-width=".3"'
    if pid in C_MOD:
        return 'fill="#e7eef9" stroke="#1f5fbf" stroke-width=".3"'
    if pid in C_RED:
        return 'fill="#c0392b" fill-opacity=".8" stroke="none"'
    if pid in C_SPK:
        return 'fill="#1f3f8f" fill-opacity=".75" stroke="none"'
    if pid == "TS-C-DSI":
        return 'fill="#d4a017" fill-opacity=".7" stroke="none"'
    if pid == "TS-C-PWR-RED":
        return 'fill="#e67e22" fill-opacity=".9" stroke="none"'
    if pid == "TS-C-PWR-BLK":
        return 'fill="#5d6778" fill-opacity=".9" stroke="none"'
    if pid.startswith("C-USB") or pid.endswith("-C-USB") or pid == "C-BAT-DC":
        return 'fill="#9aa3b2" fill-opacity=".7" stroke="none"'
    return 'fill="#d0d5dd" stroke="#4a5568" stroke-width=".25"'


def _order04(pid, kind):
    if kind in ("print", "plywood"):
        return 0
    if pid == "BAT-LFP":
        return 1
    if pid in C_BOARD or pid in C_MOD:
        return 2
    if pid.startswith("C-") or pid.startswith("TS-C") or pid.endswith("-C-USB"):
        return 4
    return 3


def _clip(polys, box):
    """clip world polygons to an axis box (x0, x1, y0, y1) with manifold3d CrossSection (no shapely here)."""
    import numpy as np
    from manifold3d import CrossSection, FillRule
    if not polys:
        return []
    try:
        cs = CrossSection([np.array(p, dtype=float) for p in polys], FillRule.NonZero)
        x0, x1, y0, y1 = box
        sq = CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
        return [[(round(float(a), 2), round(float(b), 2)) for a, b in q] for q in (cs ^ sq).to_polygons()]
    except Exception:
        return polys


def _mid(poly):
    """point at half the length of a 3D polyline (x, y)."""
    seg = [math.dist(a[:2], b[:2]) for a, b in zip(poly, poly[1:])]
    tot = sum(seg)
    acc = 0.0
    for (a, b), d in zip(zip(poly, poly[1:]), seg):
        if acc + d >= tot / 2 and d > 0:
            t = (tot / 2 - acc) / d
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        acc += d
    return poly[0][0], poly[0][1]


def brd04():
    from sheets import TOTAL, REV_E
    s = Sheet("BRD-04", 11, TOTAL, "가운데 유닛 배선도 (위에서 봄, 뚜껑·화면 뗌)",
              "CAD(build_all.collect, 2026-10-07 빌드)의 부품·선을 위에서 투영. 위: 전체 1 : 2, 아래: 전원 구석 1 : 1. 선 번호 W = SCH-01·BRD-05/06, 길이 = CAD 중심선.",
              "CU", qty="CU × 1", basis="CAD L2 · cad_centre.json", **REV_E)
    cad = HN.CAD
    s.board_check = []
    if not cad:
        s.text(30, 60, "CAD 자료(netlist/cad_centre.json)가 없습니다 — python3 src/cad_extract.py", "noteb", size=3.0)
        s.frame()
        s.expected = {}
        s.board_check = ["cad_centre.json missing"]
        return s
    parts = cad["parts"]
    items = [(c["id"], c["kind"], c["poly"], c.get("name", "")) for c in cad["context"]]
    items += [(pid, d["kind"], d["poly"], d.get("name", "")) for pid, d in parts.items()]
    items.sort(key=lambda t: _order04(t[0], t[1]))
    o = s.out["body"]

    def draw(X, Y, box):
        g = ["<g>"]
        for pid, kind, polys, nm in items:
            cp = _clip(polys, box)
            if not cp:
                continue
            g.append(f'<path d="{_path(cp, X, Y)}" {_style04(pid, kind)} fill-rule="nonzero"/>')
        g.append("</g>")
        o.append("".join(g))

    # ---------------- overview 1 : 2
    S1 = 0.5
    ox1, oy1 = 30.0, 30.0
    rx0, rx1, ry0, ry1 = 255.0, 967.0, 208.0, 346.0

    def X1(x):
        return ox1 + (x - rx0) * S1

    def Y1(y):
        return oy1 + (ry1 - y) * S1
    o.append(f'<rect x="{X1(rx0):.2f}" y="{Y1(ry1):.2f}" width="{(rx1-rx0)*S1:.2f}" height="{(ry1-ry0)*S1:.2f}" fill="#fff" stroke="#8a96ab" stroke-width=".25"/>')
    draw(X1, Y1, (rx0, rx1, ry0, ry1))
    s.text(X1(rx0), Y1(ry1) - 2.2, "전체 1 : 2 — x255~967 × y208~346 (뒤 +y 위, 연주자 쪽 아래)", "noteb", size=2.4)
    for x in range(300, 967, 100):
        s.line(X1(x), Y1(ry0), X1(x), Y1(ry0) + 1.6, "bodyl", "text")
        s.text(X1(x), Y1(ry0) + 4.0, f"x{x}", "tblm", "middle", size=1.6, check=False)
    # labels on the overview (refdes + W numbers along the CAD centre lines)
    PW = cad["paths"]
    w_over = [("W602c", _mid(PW["PWR"]["BUS"][1])), ("W703", (520.0, 328.5)), ("W705", _mid(PW["SPK"]["R"])),
              ("W704", (262.0, 252.0)), ("W706", (957.0, 298.0)), ("W604", (610.0, 285.0)),
              ("W201~W207 묶음", (380.0, 237.5)), ("W208", (600.0, 227.0)), ("W209", (680.0, 312.0)), ("W701 자리", (650.0, 232.0)),
              ("W702 자리", (520.0, 232.0))]
    for t, (x, y) in w_over:
        s.text(X1(x), Y1(y) - 0.9, t, "cabt", "middle", size=1.8, check=False)
    for pid, at in (("BAT-LFP", None), ("CU-E-PI5", (585.0, 292.0)), ("PB-E-HUB", (865.0, 316.0)), ("CU-E-AMP", (769.0, 306.0)),
                    ("CU-E-BUCK", None), ("C-XT60F-L", (283.0, 262.0)), ("C-XT60F-R", (939.0, 309.0))):
        if pid in parts:
            b = parts[pid]["bbox"]
            x, y = at if at else ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2)
            t = LABELS04[pid] + (" (선반 밑)" if pid == "PB-E-HUB" else " (선반 위)" if pid == "CU-E-AMP" else "")
            s.text(X1(x), Y1(y) + 0.8, t, "ref", "middle", size=1.9, check=False)
    s.text(X1(611), Y1(ry0) + 7.2, "점선 = CAD에 모델이 없는 선 (W707 경로 추정)", "notes", "middle", size=1.8, check=False)
    jb = parts.get("CU-E-J702BOARD", {}).get("bbox")
    ab = parts.get("CU-E-AMP", {}).get("bbox")
    if jb and ab:
        p0, p1 = (jb[3], (jb[1] + jb[4]) / 2), (ab[0], (ab[1] + ab[4]) / 2)
        o.append(f'<path d="M{X1(p0[0]):.2f},{Y1(p0[1]):.2f} L{X1(p0[0]+20):.2f},{Y1(p0[1]):.2f} L{X1(p1[0]-20):.2f},{Y1(p1[1]):.2f} L{X1(p1[0]):.2f},{Y1(p1[1]):.2f}" '
                 'fill="none" stroke="#2e8b57" stroke-width=".5" stroke-dasharray="1.6 .9"/>')
        s.text(X1((p0[0] + p1[0]) / 2), Y1((p0[1] + p1[1]) / 2) - 1.2, "W707", "cabt", "middle", size=1.8, check=False)
    # ---------------- detail 1 : 1 (power corner)
    dx0, dx1, dy0, dy1 = 378.0, 562.0, 212.0, 344.0
    ox2, oy2 = 14.0, 112.0

    def X2(x):
        return ox2 + (x - dx0)

    def Y2(y):
        return oy2 + (dy1 - y)
    o.append(f'<rect x="{X2(dx0):.2f}" y="{Y2(dy1):.2f}" width="{dx1-dx0:.2f}" height="{dy1-dy0:.2f}" fill="#fff" stroke="#8a96ab" stroke-width=".25"/>')
    draw(X2, Y2, (dx0, dx1, dy0, dy1))
    s.text(X2(dx0), Y2(dy1) - 2.2, f"전원 구석 1 : 1 — x{dx0:g}~{dx1:g} × y{dy0:g}~{dy1:g} (위 그림의 파란 테, 눈금 = 모델 좌표 mm)", "noteb", size=2.4)
    o.append(f'<rect x="{X1(dx0):.2f}" y="{Y1(dy1):.2f}" width="{(dx1-dx0)*S1:.2f}" height="{(dy1-dy0)*S1:.2f}" fill="none" stroke="#1f5fbf" stroke-width=".4"/>')
    for x in range(380, 562, 10):
        big = x % 20 == 0
        s.line(X2(x), Y2(dy0), X2(x), Y2(dy0) + (2.0 if big else 1.0), "bodyl", "text")
        if big:
            s.text(X2(x), Y2(dy0) + 4.2, f"{x}", "tblm", "middle", size=1.6, check=False)
    for y in range(220, 344, 10):
        big = y % 20 == 0
        s.line(X2(dx0) - (2.0 if big else 1.0), Y2(y), X2(dx0), Y2(y), "bodyl", "text")
        if big:
            s.text(X2(dx0) - 2.4, Y2(y) + 0.6, f"{y}", "tblm", "end", size=1.6, check=False)
    # refdes in the detail
    det = [("BAT-LFP", None), ("C-XT60", (407.5, 263.0)), ("CU-E-FUSE", (417.0, 232.5)), ("CU-E-SWITCH", (438.5, 336.0)),
           ("CU-E-BUCK", (508.0, 318.0)), ("CU-E-PEDBOARD", (437.0, 290.0)), ("CU-E-J702BOARD", (520.0, 285.0)),
           ("CU-E-J501BOARD", (462.5, 337.0)), ("C-DC", (407.0, 316.0)), ("CU-E-PI5", (553.0, 300.0))]
    for pid, at in det:
        if pid not in parts:
            continue
        b = parts[pid]["bbox"]
        x, y = at if at else ((max(b[0], dx0) + b[3]) / 2, (b[1] + b[4]) / 2)
        s.text(X2(x), Y2(y) + 0.8, LABELS04[pid], "ref", "middle", size=2.2, check=False)
    # star point, switch lugs, splices, wire numbers
    sw = HN.PTS.get("sw_lugs", {})
    bk = parts["CU-E-BUCK"]["bbox"]
    star = (bk[0], 306.0)
    o.append(f'<text x="{X2(star[0]):.2f}" y="{Y2(star[1])+1.4:.2f}" font-size="4.2" text-anchor="middle" fill="#b86e00">★</text>')
    s.text(X2(star[0]) + 3.0, Y2(star[1]) + 4.6, "★ 별 접지점 = A602 IN− 단자 (전지 − · 앰프 GND)", "notes", size=1.9, check=False)
    for xx, t in ((sw.get("x", 443.25), "1·2"), (sw.get("x2", 433.75), "3·4")):
        o.append(f'<rect x="{X2(xx)-0.5:.2f}" y="{Y2(sw.get("y_tip", 318.3))-0.2:.2f}" width="1.0" height="6.0" fill="#b86e00"/>')
        s.text(X2(xx), Y2(sw.get("y_tip", 318.3)) + 8.2, t, "pinnum", "middle", size=1.8, check=False)
    pin_ = PW["PWR"]["IN"][1]
    fus = PW["PWR"]["FUSE"][1]
    s1 = ((pin_[0][0] + pin_[1][0]) / 2, (pin_[0][1] + pin_[1][1]) / 2)
    s3 = ((fus[0][0] + fus[1][0]) / 2, (fus[0][1] + fus[1][1]) / 2)
    for (x, y), t, dxl in ((s1, "S1·S2", 3.0), (s3, "S3", 3.0)):
        o.append(f'<circle cx="{X2(x):.2f}" cy="{Y2(y):.2f}" r="2.2" fill="none" stroke="#b86e00" stroke-width=".4"/>')
        s.text(X2(x) + dxl, Y2(y) + 0.7, t, "pinnum", "end" if dxl < 0 else "start", size=1.9, check=False)
    w_det = [("W601", _mid(PW["PWR"]["IN"][2]), (3.5, -2.5)), ("W602a", _mid(PW["PWR"]["FUSE"][2]), (3.0, 0.0)),
             ("W602b", _mid(PW["PWR"]["BUS"][0]), (0.0, -2.0)), ("W602c →", (500.0, 325.0), (0.0, -1.0)),
             ("W603 → Pi", _mid(PW["PWR"]["5V"][0]), (0.0, -1.6)), ("W604 → 허브", (548.0, 285.0), (0.0, -1.6)),
             ("W703 →", (470.0, 328.5), (0.0, 3.4)), ("W502", (458.0, 315.0), (5.0, 0.0)), ("W208 →", (470.0, 222.0), (0.0, -1.0)),
             ("배터리 리드", _mid(PW["PWR"]["BAT"][0]), (3.5, 0.0))]
    for t, (x, y), (ddx, ddy) in w_det:
        s.text(X2(x) + ddx, Y2(y) + ddy, t, "cabt", "end" if ddx < 0 else ("start" if ddx > 0 else "middle"), size=2.0, check=False)
    s.text(X2(dx0) + 1.5, Y2(dy0) - 2.0, "앞 공간 y214~241 (위로 열림) · 아래쪽 = 연주자 쪽", "notes", size=1.8, check=False)
    # ---------------- wire table
    by = {h["id"]: h for h in HN.HARNESS}
    rows = []
    for wid in ("W601", "W602a", "W602j", "W602b", "W602c", "W603", "W604", "W502", "W701", "W702", "W707", "W703", "W704", "W705", "W706",
                "W606", "W608"):
        h = by[wid]
        cols = "·".join(dict.fromkeys(HN.COL[c[1]][1] for c in h["cond"]))
        rows.append([wid, h["cable"].split(" (")[0][:34], f"{h['a'][0]} → {h['b'][0]}", HN.path_cell(h).replace("제품 길이 ", "제품 "),
                     h["cut_short"], h["shrink"] or cols])
    for b in HN.BOUGHT:
        if b["id"] in ("W208", "W209", "W605", "X701"):
            rows.append([b["id"], b["cable"].split(" (")[0][:34], f"{b['a'].split(' (')[0]} → {b['b'].split(' (')[0]}", b["path"].split(" ")[0], "산 그대로", ""])
    yt = s.table(206, 108, ["W", "선", "끝 → 끝", "CAD 경로", "자름 (mm)", "수축·색"], rows, [15, 50, 54, 16, 30, 40],
                 title="선 목록 (가운데 유닛 안) — 경로 = CAD 중심선 mm", mono_cols=(0, 3), rh=3.1)
    s.para(206, yt + 4.0, [
        "주",
        "1. 그림은 CAD 부품을 위에서 투영한 실제 외곽(뚜껑 z61.35 위는 뗌). 선은 CAD가 그린 굵기(빨강 전원, 남색 스피커, 회색 USB, 노랑 DSI, 주황 화면 전원).",
        f"2. 전원 검정 선은 CAD에서 빨강과 한 줄로 그렸다. 실제로는 빨강 옆을 따라 ★까지(전지 − 경로 합 약 {HN.BLACK_RETURN} mm).",
        "3. 스위치 SW601 단자 4개는 x433.75 / 443.25 두 열(위에서 보면 겹침). 1·2 = 회로 A(x443.25), 3·4 = 회로 B — 통전으로 짝을 확인한 뒤 W602j로 나란히.",
        "4. 전원 XT60(X605⇄X606)은 빨강 수축, 스피커 XT60(X703~X706)은 파랑 수축 + ‘SPK’. W601은 홀더 −x 끝에서 XT60 뒤끝까지",
        f"    {HN.W601_MAX} mm 이하(꼬리 {HN.STUB12} + 리드 {HN.LEAD_W601} − 겹침 10) → 왼쪽 스피커 XT60(직선 {HN.W601_NEED_L:.1f} mm)에 닿지 않는다.",
        "5. 앰프 A702 단자: CAD는 스피커 L 단자를 −x 끝, R 단자를 +x 끝에 두었지만 실물은 L+·L−·R+·R−가 한 가장자리에 한 줄,",
        "    VCC·GND는 반대 가장자리(research/audio.md 1.1). 그래서 W602c·W703·W705는 50 mm 더 자른다 — 단자 자리는 받은 보드로 확인.",
        "6. PB(페달 보드) 자리는 BRD-03, J702·J501·J701·PS 작은 기판은 BRD-07, 선 만드는 법·핀은 BRD-05·06.",
    ], size=1.95, lh=2.75)
    s.frame()
    s.expected = {}
    return s


# ====================================================================== BRD-05 / BRD-06 harness strips
SHRINK_COL = {"빨강": "#c0392b", "파랑": "#1f5fbf"}


def strip(s, x, y0, w, h):
    """one cable drawn as a strip: connector A | conductors | connector B. Returns the y below it."""
    o = s.out["body"]
    cond = h["cond"]
    n = len(cond)
    band = n > 6
    pitch = 1.25 if band else 3.2
    hh = (n * pitch + 2.0) if not band else 22.0
    bw = 27.0
    top = y0 + 4.2
    s.text(x, y0 + 2.6, f"{h['id']} · {h['title']}", "noteb", size=2.2)
    meta = ("CAD 경로 %.1f · " % h["path"] if h.get("path") is not None else (h["path_label"] + " · " if h.get("path_label") else "")) + "자름 " + h["cut_short"]
    s.text(x + w, y0 + 2.6, meta, "tblm", "end", size=1.8, check=False)
    for bx, (ref, desc), side in ((x, h["a"], "A"), (x + w - bw, h["b"], "B")):
        o.append(f'<rect x="{bx:.2f}" y="{top:.2f}" width="{bw}" height="{hh:.2f}" rx=".8" fill="#fffbe6" stroke="#8c1c13" stroke-width=".3"/>')
        s.text(bx + 1.2, top + 2.6, ref, "ref", size=2.0, check=False)
    x_a, x_b = x + bw, x + w - bw
    if band:
        o.append(f'<rect x="{x_a:.2f}" y="{top+4:.2f}" width="{x_b-x_a:.2f}" height="{hh-6:.2f}" fill="#c9d0da" stroke="#6b7690" stroke-width=".3"/>')
        o.append(f'<line x1="{x_a:.2f}" y1="{top+4.4:.2f}" x2="{x_b:.2f}" y2="{top+4.4:.2f}" stroke="#c0392b" stroke-width=".6"/>')
        s.text((x_a + x_b) / 2, top + 9.6, f"{n}심 리본 (1번 = 빨간 줄)", "notes", "middle", size=1.9, check=False)
        pins = " · ".join(f"{c[0]} {c[2].replace('HALL_', '').replace('S', '#') if c[2].startswith('HALL_') else c[2]}" for c in cond)
        s.text((x_a + x_b) / 2, top + 13.2, pins[:110], "tblm", "middle", size=1.55, check=False)
        if len(pins) > 110:
            s.text((x_a + x_b) / 2, top + 15.6, pins[110:], "tblm", "middle", size=1.55, check=False)
    else:
        for k, (num, col, net, pa, pb) in enumerate(cond):
            yy = top + 1.0 + pitch * (k + 0.5)
            c = HN.COL[col][0]
            o.append(f'<line x1="{x_a:.2f}" y1="{yy:.2f}" x2="{x_b:.2f}" y2="{yy:.2f}" stroke="{c}" stroke-width=".7" stroke-linecap="round"/>')
            s.text(x_a - 0.8, yy + 0.6, pa, "pinnum", "end", size=1.6, check=False)
            s.text(x_b + 0.8, yy + 0.6, pb, "pinnum", "start", size=1.6, check=False)
            s.text(x_a + 2.0 + (x_b - x_a) * 0.08, yy - 0.5, f"{net} ({HN.COL[col][1]})", "pinname", "start", size=1.5, check=False)
    # splices (amber sleeves) and heat-shrink bands
    for k, (sid, sdesc) in enumerate(h.get("splices", [])):
        sx = x_a + (x_b - x_a) * (0.62 + 0.14 * k)
        o.append(f'<rect x="{sx-3:.2f}" y="{top+0.4:.2f}" width="6" height="{hh-0.8:.2f}" rx="1" fill="#f2b45a" fill-opacity=".45" stroke="#b86e00" stroke-width=".3"/>')
        s.text(sx, top - 0.5, sid, "pinnum", "middle", size=1.6, check=False)
    if h.get("shrink"):
        col = next((v for k_, v in SHRINK_COL.items() if h["shrink"].startswith(k_)), "#888")
        for bx in (x_a + 0.6, x_b - 4.6) if "SPK" in h["shrink"] else (x_a + 0.6,):
            o.append(f'<rect x="{bx:.2f}" y="{top+0.2:.2f}" width="4" height="{hh-0.4:.2f}" fill="{col}" fill-opacity=".35"/>')
    s.text(x, top + hh + 2.6, h["a"][1][:70], "notes", size=1.65, check=False)
    s.text(x + w, top + hh + 2.6, h["b"][1][:70], "notes", "end", size=1.65, check=False)
    return top + hh + 5.2


def _cut_table(s, x, y, ids, widths, title, splice_col=True):
    by = {h["id"]: h for h in HN.HARNESS}
    rows = []
    for i in ids:
        h = by[i]
        if splice_col:
            sp = "; ".join(f"{a} {b}" for a, b in h.get("splices", []))
            rows.append([i, h["cut_txt"], h["path_src"], sp or "—"])
        else:
            sp = " · ".join(a for a, b in h.get("splices", []))
            rows.append([i, h["cut_txt"], h["path_src"], sp or "—"])
    return s.table(x, y, ["W", "자르는 길이", "경로 근거", "이음"], rows, widths, title=title, mono_cols=(0,), rh=3.0)


def brd05():
    from sheets import TOTAL, REV_E
    s = Sheet("BRD-05", 12, TOTAL, "전원 · 오디오 하네스 (선 만들기)",
              "선마다 양 끝 커넥터·핀·선 색·이음·수축 튜브와 자르는 길이. 길이 = CAD 중심선 + 20 (벗김 5 × 2 + 여유 10), 5 mm 올림. 경로는 BRD-04.",
              "CU", qty="CU × 1", basis="harness.py · CAD", **REV_E)
    by = {h["id"]: h for h in HN.HARNESS}
    yl = 24.0
    for wid in ("W601", "W602a", "W602j", "W602b", "W602c", "W603", "W604"):
        yl = strip(s, 14.0, yl, 192.0, by[wid])
    yr = 24.0
    for wid in ("W701", "W702", "W707", "W703", "W705", "W704", "W706"):
        yr = strip(s, 214.0, yr, 194.0, by[wid])
    s.regions["power"] = (9.0, 20.0, 210.0, yl + 1.0)
    s.regions["audio"] = (209.0, 20.0, 411.0, yr + 1.0)
    yt = _cut_table(s, 14.0, max(yl, yr) + 1.0, ("W601", "W602a", "W602b", "W602c", "W603", "W604", "W703", "W705", "W704", "W706", "W707"),
                    [14, 70, 108, 24], "자르는 길이와 근거 (CAD = hardware/mechanical/cad 빌드, cad_centre.json)", splice_col=False)
    # KCD1-104 lugs (seen from inside the unit, looking at the back plate)
    sw = HN.PTS.get("sw_lugs", {"x": 443.25, "x2": 433.75, "z_in": 33.9, "z_out": 43.1})
    kx, ky = 238.0, max(yl, yr) + 8.0
    S = 2.2
    o = s.out["body"]
    s.text(kx - 6.0, ky - 3.0, "SW601 KCD1-104 단자 (안에서 뒤판을 봄, 2.2 : 1)", "noteb", size=2.2)
    o.append(f'<rect x="{kx:.2f}" y="{ky:.2f}" width="{13.2*S:.2f}" height="{19.2*S:.2f}" rx="1" fill="#e7e9ee" stroke="#4a5568" stroke-width=".35"/>')
    cx = 438.5
    for (lx, lz, pin, lab) in ((sw["x"], sw["z_in"], "1", "입력 A"), (sw["x"], sw["z_out"], "2", "출력 A"),
                               (sw["x2"], sw["z_in"], "3", "입력 B"), (sw["x2"], sw["z_out"], "4", "출력 B")):
        # looking at the back plate from inside (+y view): world +x is to the LEFT
        px_ = kx + (13.2 / 2 - (lx - cx)) * S
        pz_ = ky + (19.2 / 2 - (lz - 38.5)) * S
        o.append(f'<rect x="{px_-0.4*S:.2f}" y="{pz_-2.4*S:.2f}" width="{0.8*S:.2f}" height="{4.8*S:.2f}" fill="#b86e00"/>')
        s.text(px_ + (2.6 if lx < cx else -2.6), pz_ + 0.7, f"{pin} {lab}", "pinnum", "start" if lx < cx else "end", size=1.8, check=False)
    s.para(kx + 13.2 * S + 13.0, ky + 1.0, [
        f"단자 열 x{sw['x2']:.2f} / {sw['x']:.2f}, 높이 z{sw['z_in']:.1f} / {sw['z_out']:.1f} (CAD).",
        "1 ← W602a (퓨즈), 2 → W602b + W602c.",
        "W602j: 1–3, 2–4를 짧은 선으로 (두 회로 나란히).",
        "짝(한 회로)은 켬에서 0 Ω인 두 단자 — 통전으로 먼저 확인.",
        "끈 상태에서 1–2 사이 열림을 마지막에 확인.",
    ], "notes", size=1.8, lh=2.5)
    # J702 board: connections only (holes, routes and the check are on BRD-07)
    jx0, jy0 = 346.0, ky - 3.0
    jrows = [["J702 T (HP_TN_L)", "C701.2 · C702.2"], ["C701.1 · C702.1 (AMP_IN_L)", "R701.1 · 패드 L"],
             ["J702 R (HP_RN_R)", "C703.2 · C704.2"], ["C703.1 · C704.1 (AMP_IN_R)", "R702.1 · 패드 R"],
             ["J702 S (AGND)", "R701.2 · R702.2 · 패드 G"], ["J702 TN · RN", "비움 (어디에도 잇지 않음)"]]
    yj = s.table(jx0 - 4.0, jy0, ["J702 기판", "→ 이어지는 곳"], jrows, [34, 32], title="J702 기판 연결 (구멍·배선 = BRD-07)", rh=2.9)
    s.para(jx0 - 4.0, yj + 3.5, [
        "1 µF 두 개(나란히)는 잭 T·R 다리 쪽과 출력 패드 사이에 직렬.",
        "1 kΩ은 출력 → AGND. W707 = 패드 L · G · R → 앰프 IN.",
    ], "notes", size=1.8, lh=2.5)
    h_, S2 = 0.0, 1.0
    s.para(14.0, yt + 4.0, [
        "주",
        f"1. 이음(S…): 두 선을 10 mm 꼬아 납땜 → 수축 튜브 20 mm. 12 AWG ↔ 16 AWG(S1·S3)는 같은 방법으로, R15 굽힘 뒤(홀더 끝에서 {HN.STUB12 - HN.SPLICE_OVL}~{HN.STUB12} mm).",
        "2. 수축 튜브 색: 전원 XT60(팩 리드 X605, W601 X606, 벤치 어댑터 L81) = 빨강, 스피커 XT60(X703~X706) = 파랑 + 'SPK' 글씨.",
        "3. 앰프·강압 나사 단자에는 선 끝 5 mm를 벗겨 납을 얇게 먹이고 조인다. KCD1 탭은 납땜 뒤 수축 튜브.",
        "4. 순서: W601 → W602a·S3 → 스위치(W602j) → W602b·W602c → 강압 5.10 V 맞춤(무부하) → W603·W604 → 스피커 선. 매 단계 극성·단락을 멀티미터로.",
        "이음 목록",
    ] + ["    %s (%s) %s" % (a, h["id"], b) for h in HN.HARNESS if h["part"] in ("pwr", "aud") for a, b in h.get("splices", [])],
        size=1.95, lh=2.7)
    s.regions["switch"] = (232.0, ky - 8.0, 340.0, ky + 19.2 * 2.2 + 3.0)
    s.regions["j702"] = (338.0, jy0 - 2.0, 411.0, yj + 10.0)
    s.frame()
    s.expected = {}
    s.board_check = []
    return s


def brd06():
    from sheets import TOTAL, REV_E
    s = Sheet("BRD-06", 13, TOTAL, "신호 하네스 (리본 · EXT · 페달 · 화면 전원)",
              "센서 리본, 끝 부속 EXT 선(Adafruit 4876 짝), 페달 선, 화면 전원 점퍼. 핀 = 하우징 번호. 산 그대로 꽂는 선은 아래 표.",
              "모듈 · 끝 부속 · PB · 화면", qty="전체", basis="harness.py", **REV_E)
    by = {h["id"]: h for h in HN.HARNESS}
    yl = 24.0
    for wid in ("W101~W107", "W401", "W403", "W411", "W413"):
        yl = strip(s, 14.0, yl, 192.0, by[wid])
    yr = 24.0
    ys = {}
    for wid in ("W501", "W502", "W606", "W607", "W608"):
        ys[wid] = yr
        yr = strip(s, 214.0, yr, 194.0, by[wid])
    s.regions["left"] = (9.0, 20.0, 210.0, yl + 1.0)
    s.regions["right"] = (209.0, 20.0, 411.0, yr + 1.0)
    s.regions["ped"] = (209.0, 20.0, 411.0, ys["W606"] + 0.5)
    s.regions["ts"] = (209.0, ys["W606"] - 0.5, 411.0, yr + 1.0)
    y = max(yl, yr) + 1.0
    yt = _cut_table(s, 14.0, y, ("W101~W107", "W401", "W403", "W411", "W413", "W501", "W502"), [16, 60, 110, 30],
                    "자르는 길이와 근거")
    rows = [[b["id"], b["cable"].split(" (")[0], f"{b['a'].split(' (')[0]} → {b['b'].split(' (')[0]}", b["path"].split(" (")[0],
             b["note"].split(". C 쪽")[0]] for b in HN.BOUGHT]
    yt2 = s.table(14.0, yt + 3.0, ["W", "산 선", "꽂는 곳", "CAD 길이 (mm)", "메모"], rows, [14, 58, 72, 22, 96],
                  title="산 그대로 꽂는 선 (자르지 않음) — USB 선 길이는 선마다 다름 (CAD 경로 + 플러그 ≤ 선 길이 − 40)", mono_cols=(0, 3), rh=2.7)
    # XH position table (EL / ER) on the free right side
    xr = []
    for tag, mod, keys in (("EL", "O1", [("A0", "EL_A0", 21), ("A#0", "EL_AS0", 22), ("B0", "EL_B0", 23)]), ("ER", "O7", [("C8", "ER_C8", 108)])):
        pos = {1: ("GND", "—", "—"), 6: ("+3V3_" + tag, "—", "—")}
        for k, (key, net, midi) in enumerate(keys):
            pos[2 + k] = (net, f"C{12+k}", f"{key} = {midi}")
        for n in range(1, 7):
            net, ch, md = pos.get(n, ("(비움)", f"C{10+n}", "—"))
            xr.append([tag if n == 1 else "", n, net, f"{mod} J302-{n}", ch, md])
    s.table(214.0, yr + 2.0, ["끝", "XH", "넷", "제어 기판 패드", "먹스", "건반 = MIDI"], xr, [12, 10, 34, 34, 16, 36],
            title="EXT 커넥터 위치 (X401⇄X402 · X411⇄X412)", mono_cols=(1, 2, 3, 4), rh=2.9)
    hp = HN.HUB_PORTS
    s.text(14.0, yt2 + 4.0, "허브 포트 (−x 끝부터 0~9): " + " · ".join("%d = %s" % (v, k) for k, v in sorted(hp.items(), key=lambda kv: kv[1]))
           + " · 0·1 비움 (CAD cable_duct.hub.port_map)", "notes", size=2.0)
    s.para(14.0, yt2 + 8.5, [
        "주  1. Adafruit 4876 한 쌍 = 플러그 선 + 소켓 선(각 약 20 cm, 26 AWG). 플러그 선 → 모듈 J302(150 mm로 자름), 소켓 선 → 끝 부속 리본(50 mm로 자름).",
        "    선 색은 판매처가 밝히지 않아 하우징 번호(1 = GND … 6 = 3V3)로만 잇는다. 자르기 전에 양쪽에 번호 테이프.",
        "2. 리본 가닥: 끝 1.5 mm 벗겨 납을 먹이고 아랫면에서 납땜, 다리 끝은 1 mm 아래로(기판 밑 2.0). 가닥끼리 이음은 각각 수축 튜브.",
        "3. 허브 710U3: 10포트 중 1개는 충전 전용, 포트마다 ON/OFF 스위치. 충전 전용 포트(표시, 또는 Zero를 꽂아 장치로 안 보이는 포트)가",
        "    0·1번인지 확인 — 2~9번이면 그 보드를 1번(또는 0번)으로 옮기고 회로도 탭 '허브 포트 옮김' 표로 선 길이를 다시 본다. 쓰는 8개 포트 스위치를 켠다.",
    ], size=1.95, lh=2.7)
    s.frame()
    s.expected = {}
    s.board_check = []
    return s
