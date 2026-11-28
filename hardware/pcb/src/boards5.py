"""BRD-02: the sensor board SB and the end-part boards EL / ER, each drawn twice the way BRD-09~15 draw the control boards:

  top side   (부품 쪽, seen from above)  the sensors lying under their bar, the bent leads in their lead holes, the ribbon / lead pad block
  underside  (배선 쪽, seen from below = mirror image, left and right swapped)  the bare 3V3 / GND buses, EVERY 1206 part (100 nF per
             sensor, the 10 uF bulk caps, the EL / ER 1 kOhm), every insulated strand with its number, the solder joints, the support pads
             and floor bridges of the bed under the board, the ribbon / lead leaving the board

User 2026-11-28 on the BRD-02 crop: "얘도 7개 기판처럼 클릭하고 확대할 수 있게 해놔. 그리고 지금 보면 콘덴서가 다 표시가 안된 거 같은데
회로를 다 그려봐. 전체적으로 점검하고 고쳐." The old sheet had ONE top view in which the underside parts were faint dashed outlines drawn over
the sensor lead holes (the 100 nF looked missing) and the underside wires were dashed lines on the top view.

Review fixes made with it:
  * EL / ER underside strands were straight diagonal point-to-point lines (EL B0 passed 0.36 mm from the J401.5 3V3 pad). They are routed
    on the lattice now (half-pitch lanes, the 3V3 strand crosses the GND bus between holes like the SB power links) and checked with
    boards3.route_check like the SB (end_check); the paths are written to wiring_small.csv (기판 EL / ER) and the 3D model draws them.
  * build order: sensors first (the A20 bar slides on from behind after the sensors are soldered - octave-assembly guide), then the buses,
    then the 1206 parts on the joints, then the strands - the page used to say 1206 first, which fills the lead holes with solder.
"""
import boards3 as B3
import hitkeys as HK
import sheets as S
from sch import Sheet, text_w

H = 1.27                                   # half pitch
ROWS = (61.92, 64.46, 67.00, 69.54, 72.08, 74.62)
BY0, BY1 = 60.65, 75.89                    # board edges (y), the same 15.24 stripe for SB / EL / ER
BAR_Y = (59.0, 77.5)                       # sensor bar (y) over the board
NOTCH = ((3.0, 61.9, 60.65), (3.0, 74.6, 75.89))   # U-notches D3.4 for the M3x10 self-tappers (x, y, edge)
POST = (0.5, 6.0)                          # left post of the bed under every sensor board (cad a20_fix.sb_bed post_x1)
BRIDGES = (32.4, 88.3, 141.6)              # SB only: floor bridges 4.0 wide, 2.0 under the board (cad a20_fix A20 bridges.module)
BRIDGE_W = 4.0
LANE_OUT, LANE_J = 70.81, 73.35            # half-pitch lanes: SB OUT bundle / EL-ER signal lane and the SB even-pin lane

COL_CAP, COL_CAP_EDGE, COL_END, COL_RES = "#cfa86a", "#7a5a2a", "#d7dce3", "#2a2a2a"
COL_HOLE = "#b9cdb6"


def cols(x0, x1):
    return [round(0.63 + 2.54 * i, 2) for i in range(1, 80) if x0 < 0.63 + 2.54 * i < x1]


# ====================================================================== EL / ER underside strands (lattice routes) + check
def end_rows(tag):
    """the insulated underside strands of EL / ER in the order of the 3D model's ELW-n / ERW-n:
    1 GND bus -> pad 1 (straight back over empty holes), 2 3V3 bus -> last pad (half-pitch column beside the pad: crosses the bare GND
    bus between two holes, then the half lane y65.73 onto an empty 3V3 bus hole), 3.. 1 kOhm end (col, 72.08) -> half-pitch lane y73.35 ->
    J pad. A 1 kOhm end whose lane start would lie on an A20 support pad keep-out first runs one hole left along its row (EL B0)."""
    B = S.END_BOARDS[tag]
    jx, jref, rail = B["jx"], B["jref"], B["jnames"][-1]
    keep = end_keep(tag)

    def inside(x, y):
        return any(a0 <= x <= a1 and b0 <= y <= b1 for (a0, a1, b0, b1) in keep)
    rows = [dict(key="%sW-1" % tag, net="GND", a="GND 버스", b="%s.1" % jref, poly=[(jx[0], 67.00), (jx[0], 74.62)])]
    x = jx[-1]
    rows.append(dict(key="%sW-2" % tag, net=rail, a="3V3 버스", b="%s.%d" % (jref, len(jx)),
                     poly=[(x, 64.46), (x, 65.73), (round(x + H, 2), 65.73), (round(x + H, 2), 74.62), (x, 74.62)]))
    for i, (u, k, xk, c, r) in enumerate(B["keys"]):
        col, xp = S.end_col(xk), jx[1 + i]
        poly = [(col, 72.08)]
        if inside(col, LANE_J):
            col2 = round(col - 2.54, 2)
            poly.append((col2, 72.08))
            col = col2
        poly += [(col, LANE_J), (xp, LANE_J), (xp, 74.62)]
        rows.append(dict(key="%sW-%d" % (tag, 3 + i), net=B["jnames"][1 + i], a="%s (%s 건반) 1 kΩ 끝" % (r, k), b="%s.%d" % (jref, 2 + i),
                         poly=[(round(a, 2), round(b, 2)) for a, b in poly]))
    for r in rows:
        r["length"] = B3.wlen(r["poly"])
    return rows


def end_bus(tag):
    B = S.END_BOARDS[tag]
    last = max(S.end_col(k[2]) for k in B["keys"])
    return {B["jnames"][-1]: [(8.25, 64.46), (last, 64.46)], "GND": [(8.25, 67.00), (last, 67.00)]}


def end_keep(tag):
    """no underside wire within 0.5 of an A20 support pad, of the left post (x0.5~6.0) or of a U-notch"""
    k = [(a0 - 0.5, a1 + 0.5, b0 - 0.5, b1 + 0.5) for (a0, a1, b0, b1) in S.end_pads(tag)]
    k += [(POST[0], POST[1] + 0.5, BY0 - 1.0, BY1 + 1.0)]
    k += [(x - 2.2, x + 2.2, y - 2.2, y + 2.2) for (x, y, _e) in NOTCH]
    return k


def end_pad_map(tag):
    """soldered holes of EL / ER {(x, y): (ref, pin, net)} (the 1 kOhm's OUT end shares the sensor OUT hole: anonymous net '~U4xx.3')."""
    B = S.END_BOARDS[tag]
    rail = B["jnames"][-1]
    pads = {}
    for i, (u, k, xk, c, r) in enumerate(B["keys"]):
        col = S.end_col(xk)
        pads[(col, 64.46)] = (u, "1", rail)
        pads[(col, 67.00)] = (u, "2", "GND")
        pads[(col, 69.54)] = (u, "3", "~%s.3" % u)
        pads[(col, 72.08)] = (r, "1", B["jnames"][1 + i])
    pads[(8.25, 64.46)] = (B["bulk"], "1", rail)
    pads[(8.25, 67.00)] = (B["bulk"], "2", "GND")
    for n, x in enumerate(B["jx"], 1):
        pads[(x, 74.62)] = (B["jref"], str(n), B["jnames"][n - 1])
    return pads


def end_check():
    """EL / ER: boards3.route_check (every net one group, strands joined only at their ends, no wire over another net's pad or in a
    keep-out) + no solder joint within 1.0 of an A20 support pad (the joints stand ~1 mm proud)."""
    probs = []
    for tag in ("EL", "ER"):
        routes, bare = {}, set()
        for net, poly in end_bus(tag).items():
            routes.setdefault(net, []).append(poly)
            bare.add((net, len(routes[net]) - 1))
        for r in end_rows(tag):
            routes.setdefault(r["net"], []).append(r["poly"])
        pads = end_pad_map(tag)
        probs += ["%s: %s" % (tag, p) for p in B3.route_check(pads, routes, keep=end_keep(tag), bare=bare)]
        for (x, y), (ref, pin, net) in pads.items():
            for (a0, a1, b0, b1) in S.end_pads(tag):
                if a0 - 1.0 <= x <= a1 + 1.0 and b0 - 1.0 <= y <= b1 + 1.0:
                    probs.append("%s: joint %s.%s (%.2f, %.2f) on an A20 support pad" % (tag, ref, pin, x, y))
    return probs


def wiring_end_rows():
    """wiring_small.csv rows of EL / ER (board, net, path, length, kind)"""
    out = []
    for tag in ("EL", "ER"):
        for net, poly in end_bus(tag).items():
            out.append([tag, net, " → ".join("(%.2f,%.2f)" % p for p in poly), "%.1f" % B3.wlen(poly), "주석 맨선 (버스)"])
        for r in end_rows(tag):
            out.append([tag, r["net"], " → ".join("(%.2f,%.2f)" % p for p in r["poly"]), "%.1f" % r["length"],
                        "피복 가닥 %d: %s → %s" % (int(r["key"].split("-")[1]), r["a"], r["b"])])
    return out


# ====================================================================== board descriptions (one per strip board)
def sb_board():
    rows, pw = B3.sb_rows(), B3.sb_pwr_rows()
    sens = []
    for i, (k, xk) in enumerate(zip(S.KEYS, S.SENSOR_X)):
        sens.append(dict(u="U%d" % (201 + i), key=k, xk=xk, col=rows[i]["xo"], nets=("+3V3", "GND", S.NET[k]),
                         q="%s 건반 · 리본 %d번 심 → 먹스 C%d" % (k, 3 + i, i), cap="C%d" % (201 + i), res=None))
    jp = [(n, round(61.59 + 2.54 * ((n - 1) // 2), 2), 72.08 if n % 2 else 74.62, S.RIBBON[n - 1]) for n in range(1, 17)]
    strands = []
    for k, r in enumerate(rows):
        strands.append(dict(key="SBW-%d" % (k + 1), no=k + 1, net=r["net"], poly=r["poly"], dy=(k - 5.5) * 0.10,
                            tag=(r["xo"] + 1.65, 69.54)))
    for k, r in enumerate(pw):
        strands.append(dict(key="SBW-%d" % (len(rows) + k + 1), no=len(rows) + k + 1, net=r["net"], poly=r["poly"], dy=0.0, tag=None,
                            bus_end=True))
    caps = [(s_["cap"], s_["col"], "100n") for s_ in sens] + [("C213", 8.25, "10µ"), ("C214", 158.11, "10µ")]
    return dict(tag="SB", m=None, x0=S.CUT_X0, x1=S.SB_X1, bar=(0.5, 162.9), low=None, rail="+3V3", sens=sens, caps=caps, res=[],
                bus=dict(B3.SB_BUS), jref="J201", jpads=jp, strands=strands, keep=list(B3.SB_RIBS), bridges=BRIDGES, ledge=True,
                rowname={61.92: "예비", 64.46: "3V3 버스", 67.00: "GND 버스", 69.54: "OUT", 72.08: "리본 홀수", 74.62: "리본 짝수"})


def end_board(tag):
    B = S.END_BOARDS[tag]
    rail = B["jnames"][-1]
    sens = []
    for i, (u, k, xk, c, r) in enumerate(B["keys"]):
        sens.append(dict(u=u, key=k, xk=xk, col=S.end_col(xk), nets=(rail, "GND", None), q="%s 건반" % k, cap=c, res=r,
                         rnet=B["jnames"][1 + i]))
    jp = [(n, x, 74.62, B["jnames"][n - 1]) for n, x in enumerate(B["jx"], 1)]
    strands = []
    for r in end_rows(tag):
        no = int(r["key"].split("-")[1])
        strands.append(dict(key=r["key"], no=no, net=r["net"], poly=r["poly"], dy=0.0, tag=None, bus_end=no <= 2))
    caps = [(s_["cap"], s_["col"], "100n") for s_ in sens] + [(B["bulk"], 8.25, "10µ")]
    res = [(s_["res"], s_["col"], "1k") for s_ in sens]
    return dict(tag=tag, m=tag, x0=S.CUT_X0, x1=B["cut1"], bar=B["bar"], low=B["low"], rail=rail, sens=sens, caps=caps, res=res,
                bus=end_bus(tag), jref=B["jref"], jpads=jp, strands=strands, keep=S.end_pads(tag), bridges=(), ledge=False,
                rowname={61.92: "예비", 64.46: "3V3", 67.00: "GND", 69.54: "OUT", 72.08: "1k 끝", 74.62: "패드"})


# ====================================================================== drawing
class View:
    """model (x, y) -> sheet mm. Top view: +x to the right; underside: mirrored (+x to the LEFT). Both: back (+y) up."""

    def __init__(self, sc, ox, oy, x0, x1, mirror):
        self.sc, self.ox, self.oy, self.x0, self.x1, self.mirror = sc, ox, oy, x0, x1, mirror

    def X(self, x):
        return self.ox + ((self.x1 - x) if self.mirror else (x - self.x0)) * self.sc

    def Y(self, y):
        return self.oy + (BAR_Y[1] - y) * self.sc

    def xr(self, a, b):
        return sorted((self.X(a), self.X(b)))


def T(s, x, y, txt, cls="notes", anchor="start", fs=2.0, check=True, color=None):
    """text with its own font size, in the sheet's overlap check"""
    S._tx(s, x, y, txt, cls, anchor, fs=fs)
    if color:
        s.out["text"][-1] = s.out["text"][-1].replace('style="', 'style="fill:%s;' % color, 1)
    if check:
        w = text_w(str(txt), fs)
        x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        s.texts.append((x0, y - fs * 0.78, x0 + w, y + fs * 0.2, str(txt)))


def para(s, x, y, lines, fs=2.0, lh=None, cls="note"):
    lh = lh or fs * 1.42
    for i, t in enumerate(lines):
        if t:
            T(s, x, y + i * lh, t, "noteb" if i == 0 else cls, fs=fs + (0.3 if i == 0 else 0.0))
    return y + len(lines) * lh


def _board(s, V, B, top):
    o = s.out["body"]
    x0, x1 = V.xr(B["x0"], B["x1"])
    o.append(f'<rect x="{x0:.2f}" y="{V.Y(BY1):.2f}" width="{x1 - x0:.2f}" height="{15.24 * V.sc:.2f}" fill="{"#eaf4e8" if top else "#e3eee0"}" '
             f'stroke="#2d6a3e" stroke-width=".5"/>')
    for y in ROWS:
        for x in cols(B["x0"], B["x1"]):
            o.append(f'<circle cx="{V.X(x):.2f}" cy="{V.Y(y):.2f}" r=".42" fill="{COL_HOLE}"/>')
    for (x, y, edge) in NOTCH:
        a, b = min(y, edge), max(y, edge)
        nx0, nx1 = V.xr(x - 1.7, x + 1.7)
        o.append(f'<rect x="{nx0:.2f}" y="{V.Y(b):.2f}" width="{nx1 - nx0:.2f}" height="{(b - a) * V.sc:.2f}" fill="#fff" stroke="none"/>')
        o.append(f'<circle cx="{V.X(x):.2f}" cy="{V.Y(y):.2f}" r="{1.7 * V.sc:.2f}" fill="#fff" stroke="#1d2433" stroke-width=".35"/>')


def _row_labels(s, V, B, x_end, fs=1.8):
    for y in ROWS:
        T(s, x_end, V.Y(y) + 0.6, ("y%.2f %s" % (y, B["rowname"][y])) if fs >= 1.7 else B["rowname"][y], "tblm", "end", fs=fs)


def _part1206(s, V, ref, x, ya, yb, kind):
    """a 1206 on the underside across the holes (x, ya) - (x, yb): body + two silver end terminations; returns its sheet box."""
    o = s.out["body"]
    ym = (ya + yb) / 2.0
    cx, w, L = V.X(x), 1.6 * V.sc, 3.2 * V.sc
    yt = V.Y(ym) - L / 2
    body = COL_RES if kind == "1k" else COL_CAP
    o.append(f'<rect x="{cx - w / 2:.2f}" y="{yt:.2f}" width="{w:.2f}" height="{L:.2f}" rx=".25" fill="{body}" fill-opacity=".95" '
             f'stroke="{COL_CAP_EDGE}" stroke-width=".3"/>')
    e = 0.5 * V.sc
    for yy in (yt, yt + L - e):
        o.append(f'<rect x="{cx - w / 2:.2f}" y="{yy:.2f}" width="{w:.2f}" height="{e:.2f}" fill="{COL_END}" stroke="#8a96ab" stroke-width=".2"/>')
    if kind == "1k":
        S._tx(s, cx, V.Y(ym) + 0.45, "102", "pinnum", "middle", fs=1.0)
        s.out["text"][-1] = s.out["text"][-1].replace('style="', 'style="fill:#fff;', 1)
    return (cx - w / 2, yt, cx + w / 2, yt + L)


def draw_top(s, V, B, title, K):
    """top side: bar outline, board, sensors + leads into their lead holes, the pad block (from below), U-notches, ledge."""
    o = s.out["body"]
    sc = V.sc
    bx0, bx1 = V.xr(*B["bar"])
    o.append(f'<rect x="{bx0:.2f}" y="{V.Y(BAR_Y[1]):.2f}" width="{bx1 - bx0:.2f}" height="{(BAR_Y[1] - BAR_Y[0]) * sc:.2f}" fill="#6b7690" '
             f'fill-opacity=".05" stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.2 .8"/>')
    if B["low"]:
        lx0, lx1 = V.xr(*B["low"])
        o.append(f'<rect x="{lx0:.2f}" y="{V.Y(BAR_Y[1]):.2f}" width="{lx1 - lx0:.2f}" height="{(BAR_Y[1] - BAR_Y[0]) * sc:.2f}" fill="#6b7690" '
                 f'fill-opacity=".08" stroke="none"/>')
    _board(s, V, B, True)
    for se in B["sens"]:
        xk, col = se["xk"], se["col"]
        x0_, x1_ = V.xr(xk - 1.54, xk + 1.61)
        o.append(f'<rect x="{x0_:.2f}" y="{V.Y(69.0):.2f}" width="{x1_ - x0_:.2f}" height="{4.0 * sc:.2f}" rx=".4" fill="#222" fill-opacity=".85"/>')
        S._tx(s, (x0_ + x1_) / 2, V.Y(67.0) + 0.4, "W137", "pinnum", "middle", fs=max(0.9, 0.55 * sc))
        s.out["text"][-1] = s.out["text"][-1].replace('style="', 'style="fill:#e8e8e8;', 1)
        for (ly, lt), net, pin in zip(((65.73, 64.46), (67.0, 67.0), (68.27, 69.54)), (B["rail"], "GND", "OUT"), "123"):
            o.append(f'<polyline points="{V.X(xk + 1.61):.2f},{V.Y(ly):.2f} {V.X(xk + 3.0):.2f},{V.Y(ly):.2f} {V.X(col):.2f},{V.Y(lt):.2f}" '
                     f'fill="none" stroke="#8b8f96" stroke-width=".45" stroke-linecap="round"/>')
            c = B3.ncol(net) if net != "OUT" else "#1f5fbf"
            o.append(f'<circle cx="{V.X(col):.2f}" cy="{V.Y(lt):.2f}" r="{0.45 * sc:.2f}" fill="#fff" stroke="{c}" stroke-width=".45"/>')
            o.append(f'<circle cx="{V.X(col):.2f}" cy="{V.Y(lt):.2f}" r=".35" fill="#8b8f96"/>')
            S._tx(s, V.X(col + 0.95), V.Y(lt) + 0.42, pin, "pinnum", "start", fs=max(0.95, 0.5 * sc))
    for (n, x, y, net) in B["jpads"]:
        o.append(f'<rect x="{V.X(x) - 0.55 * sc:.2f}" y="{V.Y(y) - 0.55 * sc:.2f}" width="{1.1 * sc:.2f}" height="{1.1 * sc:.2f}" fill="#fff" '
                 f'stroke="#8a5a00" stroke-width=".35" stroke-dasharray=".6 .4"/>')
        S._tx(s, V.X(x), V.Y(y) + 0.42, n, "pinnum", "middle", fs=max(0.95, 0.5 * sc))
    if B["ledge"]:
        for (ya, yb) in ((59.0, 63.4), (70.6, 77.5)):
            a0, a1 = V.xr(161.5, 163.0)
            o.append(f'<rect x="{a0:.2f}" y="{V.Y(yb):.2f}" width="{a1 - a0:.2f}" height="{(yb - ya) * sc:.2f}" fill="#c9d0da" fill-opacity=".6" '
                     f'stroke="#6b7690" stroke-width=".3"/>')
            a0, a1 = V.xr(163.0, 164.3)
            o.append(f'<rect x="{a0:.2f}" y="{V.Y(yb):.2f}" width="{a1 - a0:.2f}" height="{(yb - ya) * sc:.2f}" fill="#9aa6b8" stroke="#6b7690" stroke-width=".3"/>')
    # click targets
    for se in B["sens"]:
        it = K.box(se["xk"] - 1.54, 65.0, se["xk"] + 1.61, 69.0, key=se["u"], q=se["q"])
        for y, pin, net in ((64.46, "1", se["nets"][0]), (67.00, "2", "GND"), (69.54, "3", se["nets"][2])):
            K.pad(se["col"], y, "%s.%s" % (se["u"], pin), net, r=0.5 * sc,
                  q="윗면: 센서 다리가 이 구멍으로 들어갑니다 (납땜은 아랫면)." if B["tag"] == "SB" else None)
    for (n, x, y, net) in B["jpads"]:
        K.pad(x, y, "%s.%d" % (B["jref"], n), net, r=0.6 * sc, q="윗면에서는 구멍만 보입니다 — %s 선은 아랫면에서 납땜." % ("리본" if B["tag"] == "SB" else "리드"))
    _common_keys(B, K)
    if B["ledge"]:
        for (ya, yb) in ((59.0, 63.4), (70.6, 77.5)):
            K.box(161.5, ya, 164.3, yb, t="오른쪽 턱 (프레임, W1 r4.5 P36)",
                  d=["립 x161.5~163.0 (z13.6~15.1, 센서 바 끝 위 1.4) + 바닥에서 올라온 기둥 x163.0~164.3.",
                     "센서 바를 1.5 mm 왼쪽에 놓고 오른쪽으로 밀어 넣은 뒤 왼쪽 나사 2개로 고정합니다."])
    it = K.box(B["bar"][0], BAR_Y[0], B["bar"][1], BAR_Y[1], key="CTX-BAR" if B["tag"] == "SB" else "CTX-BAR-END")
    it["lo"] = 1


def _common_keys(B, K):
    for (x, y, _e) in NOTCH:
        K.box(x - 1.7, y - 1.7, x + 1.7, y + 1.7, t="고정 U홈 (M3×10 자가 탭 나사 자리)",
              d=["기판 왼쪽 끝의 앞·뒤에 Ø3.4 U홈이 하나씩 있습니다: (3.0, 61.9) · (3.0, 74.6).",
                 "센서 바와 기판을 함께 M3×10 자가 탭 나사 2개로 왼쪽 받침 기둥에 고정합니다.",
                 "오른쪽 끝은 나사 없이 " + ("프레임의 턱 밑으로 밀어 넣습니다." if B["tag"] == "SB" else "받침 패드 위에 놓입니다.")])
    it = K.box(B["x0"], BY0, B["x1"], BY1, key="PCB-" + B["tag"])
    it["lo"] = 1


def draw_under(s, V, B, K, label_ref=True):
    """underside (mirror image): bed (post, bridges, support pads), bare buses, joints, strands, 1206 parts, labels."""
    o = s.out["body"]
    sc = V.sc
    _board(s, V, B, False)
    # the bed under the board: left post (M3), floor bridges (2.0 under the board), support pads (no wire / joint on them)
    a0, a1 = V.xr(max(POST[0], B["x0"]), POST[1])
    o.append(f'<rect x="{a0:.2f}" y="{V.Y(BY1):.2f}" width="{a1 - a0:.2f}" height="{15.24 * sc:.2f}" fill="#6b7690" fill-opacity=".16" '
             f'stroke="#4b5568" stroke-width=".3" stroke-dasharray="1.0 .6"/>')
    for xc in B["bridges"]:
        a0, a1 = V.xr(xc - BRIDGE_W / 2, xc + BRIDGE_W / 2)
        o.append(f'<rect x="{a0:.2f}" y="{V.Y(BY1):.2f}" width="{a1 - a0:.2f}" height="{15.24 * sc:.2f}" fill="#6b7690" fill-opacity=".08" stroke="none"/>')
    for (p0, p1, q0, q1) in B["keep"]:
        p0_, p1_ = V.xr(max(p0, B["x0"]), min(p1, B["x1"]))
        o.append(f'<rect x="{p0_:.2f}" y="{V.Y(q1):.2f}" width="{p1_ - p0_:.2f}" height="{(q1 - q0) * sc:.2f}" fill="#6b7690" fill-opacity=".24" '
                 f'stroke="#4b5568" stroke-width=".3" stroke-dasharray="1.0 .6"/>')
    # bare tinned buses
    for net, (pa, pb) in B["bus"].items():
        c = B3.ncol(net if not net.startswith("+3V3") else "+3V3")
        o.append(f'<line x1="{V.X(pa[0]):.2f}" y1="{V.Y(pa[1]):.2f}" x2="{V.X(pb[0]):.2f}" y2="{V.Y(pb[1]):.2f}" stroke="{c}" stroke-width="1.0" '
                 f'stroke-opacity=".55" stroke-linecap="round"/>')
        o.append(f'<line x1="{V.X(pa[0]):.2f}" y1="{V.Y(pa[1]):.2f}" x2="{V.X(pb[0]):.2f}" y2="{V.Y(pb[1]):.2f}" stroke="#fff" stroke-width=".22" '
                 f'stroke-opacity=".8"/>')
    # strands: casings first, then the colours (a bundled lane reads as one band of separate wires)
    paths = []
    for st in B["strands"]:
        pts = [(x, y + (st["dy"] if abs(y - LANE_OUT) < 0.01 else 0.0)) for x, y in st["poly"]]
        st["_pts"] = pts
        paths.append((st, " ".join("%.2f,%.2f" % (V.X(x), V.Y(y)) for x, y in pts)))
    for st, d in paths:
        o.append(f'<polyline points="{d}" fill="none" stroke="#fff" stroke-width=".9" stroke-linejoin="round" stroke-linecap="round"/>')
    for st, d in paths:
        c = B3.ncol(st["net"] if not st["net"].startswith("+3V3") else "+3V3") if not st["net"].startswith(("EL_", "ER_")) else "#1f5fbf"
        o.append(f'<polyline points="{d}" fill="none" stroke="{c}" stroke-width=".42" stroke-linejoin="round" stroke-linecap="round"/>')
    # joints: sensor leads (3), 1 kOhm ends, bulk caps, pad block, strand ends soldered onto a bus
    def joint(x, y, net, r=0.42):
        c = "#1f5fbf" if (net is None or net.startswith(("HALL_", "EL_", "ER_"))) else B3.ncol(net if not net.startswith("+3V3") else "+3V3")
        o.append(f'<circle cx="{V.X(x):.2f}" cy="{V.Y(y):.2f}" r="{r * sc:.2f}" fill="{c}" stroke="#1f2a44" stroke-width=".25"/>')
    for se in B["sens"]:
        for y, net in zip((64.46, 67.00, 69.54), se["nets"]):
            joint(se["col"], y, net)
        if se["res"]:
            joint(se["col"], 72.08, se["rnet"])
    for (ref, x, val) in B["caps"]:
        if not any(abs(x - se["col"]) < 0.01 for se in B["sens"]):
            joint(x, 64.46, B["rail"])
            joint(x, 67.00, "GND")
    for (n, x, y, net) in B["jpads"]:
        c = B3.ncol(net if not net.startswith("+3V3") else "+3V3") if not net.startswith(("EL_", "ER_")) else "#1f5fbf"
        o.append(f'<rect x="{V.X(x) - 0.55 * sc:.2f}" y="{V.Y(y) - 0.55 * sc:.2f}" width="{1.1 * sc:.2f}" height="{1.1 * sc:.2f}" rx=".3" '
                 f'fill="#fff" stroke="{c}" stroke-width=".55"/>')
        S._tx(s, V.X(x), V.Y(y) + 0.42, n, "pinnum", "middle", fs=max(0.95, 0.5 * sc))
    for st in B["strands"]:
        if st.get("bus_end"):
            x, y = st["poly"][0]
            c = B3.ncol(st["net"] if not st["net"].startswith("+3V3") else "+3V3")
            o.append(f'<circle cx="{V.X(x):.2f}" cy="{V.Y(y):.2f}" r="{0.38 * sc:.2f}" fill="{c}" stroke="#fff" stroke-width=".25"/>')
    # the 1206 parts on top of their joints
    boxes = {}
    for (ref, x, val) in B["caps"]:
        boxes[ref] = _part1206(s, V, ref, x, 64.46, 67.00, val)
    for (ref, x, val) in B["res"]:
        boxes[ref] = _part1206(s, V, ref, x, 69.54, 72.08, "1k")
    # ---- labels: strand numbers first, then the 1206 names, each on the first free spot (no wire, joint, part or label under it)
    placed = []

    def seg_box(a, b, pad=0.35):
        xs, ys = sorted((V.X(a[0]), V.X(b[0]))), sorted((V.Y(a[1]), V.Y(b[1])))
        return (xs[0] - pad, ys[0] - pad, xs[1] + pad, ys[1] + pad)
    for st in B["strands"]:
        placed += [seg_box(a, b) for a, b in zip(st["_pts"], st["_pts"][1:])]
    for net, (pa, pb) in B["bus"].items():
        placed.append(seg_box(pa, pb, 0.5))
    for bx in boxes.values():
        placed.append(bx)
    rj = 0.42 * sc + 0.15
    for se in B["sens"]:
        for y in (64.46, 67.00, 69.54) + ((72.08,) if se["res"] else ()):
            placed.append((V.X(se["col"]) - rj, V.Y(y) - rj, V.X(se["col"]) + rj, V.Y(y) + rj))
    for (n, x, y, net) in B["jpads"]:
        placed.append((V.X(x) - 0.6 * sc, V.Y(y) - 0.6 * sc, V.X(x) + 0.6 * sc, V.Y(y) + 0.6 * sc))
    bxs = V.xr(B["x0"], B["x1"])
    inner = (bxs[0] + 0.3, V.Y(BY1) + 0.3, bxs[1] - 0.3, V.Y(BY0) - 0.3)

    def free(q, own=()):
        if q[0] < inner[0] or q[2] > inner[2] or q[1] < inner[1] or q[3] > inner[3]:
            return False
        return not any(q[0] < p[2] and p[0] < q[2] and q[1] < p[3] and p[1] < q[3] for p in placed if p not in own)

    bw, bh = 2.5, 1.6
    for st in B["strands"]:
        c = B3.ncol(st["net"] if not st["net"].startswith("+3V3") else "+3V3") if not st["net"].startswith(("EL_", "ER_")) else "#1f5fbf"
        own = [seg_box(a, b) for a, b in zip(st["_pts"], st["_pts"][1:])]
        cands = []
        if st.get("tag"):
            tx_, ty_ = st["tag"]
            cands += [(V.X(tx_), V.Y(ty_)), (V.X(2 * st["poly"][0][0] - tx_), V.Y(ty_))]
        segs = [(a, b) for a, b in zip(st["_pts"], st["_pts"][1:]) if not abs(a[1] - LANE_OUT) < 0.2 or abs(a[0] - b[0]) < 0.01]
        segs.sort(key=lambda ab: -(abs(ab[0][0] - ab[1][0]) + abs(ab[0][1] - ab[1][1])))
        for a, b in segs:
            for f in (0.5, 0.3, 0.7, 0.2, 0.8):
                cands.append((V.X(a[0] + (b[0] - a[0]) * f), V.Y(a[1] + (b[1] - a[1]) * f)))
        box = None
        for cx, cy in cands:
            q = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
            if free(q, own):
                box = q
                break
        if box is None:
            cx, cy = cands[0]
            box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
        placed.append(box)
        o.append(f'<rect x="{box[0]:.2f}" y="{box[1]:.2f}" width="{bw}" height="{bh}" rx=".4" fill="#fff" fill-opacity=".95" '
                 f'stroke="{c}" stroke-width=".25"/>')
        S._tx(s, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 0.42, st["no"], "pinnum", "middle", fs=1.15)
    lab_fs = 1.25 if sc < 2.1 else 1.35
    labs = [(ref, x, "%s %s" % (ref, val), (64.46, 67.00), "#7a4a00") for (ref, x, val) in B["caps"]]
    labs += [(ref, x, "%s 1k" % ref, (69.54, 72.08), "#3a3a3a") for (ref, x, val) in B["res"]]
    for ref, x, txt, (ya, yb), colr in labs:
        bx = boxes[ref]
        w, h = text_w(txt, lab_fs), lab_fs
        ym = V.Y((ya + yb) / 2)
        cands = []
        for dy in (0.0, -1.27 * sc, 1.27 * sc, -2.0 * sc, 2.0 * sc):
            cands += [(bx[2] + 0.5, ym + dy, "start"), (bx[0] - 0.5, ym + dy, "end")]
        cands += [(V.X(x), bx[1] - 0.9, "middle"), (V.X(x), bx[3] + h + 0.4, "middle")]
        pick = None
        for cx, cy, anc in cands:
            x0_ = cx if anc == "start" else (cx - w if anc == "end" else cx - w / 2)
            q = (x0_ - 0.2, cy - h * 0.55, x0_ + w + 0.2, cy + h * 0.55)
            if free(q, (bx,)):
                pick = (cx, cy, anc, q)
                break
        if pick is None:
            cx, cy, anc = cands[0]
            x0_ = cx
            pick = (cx, cy, anc, (x0_, cy - h * 0.55, x0_ + w, cy + h * 0.55))
        placed.append(pick[3])
        T(s, pick[0], pick[1] + h * 0.35, txt, "pinname", pick[2], fs=lab_fs, check=False, color=colr)
    # click targets
    m = B["m"]
    for se in B["sens"]:
        for y, pin, net in ((64.46, "1", se["nets"][0]), (67.00, "2", "GND"), (69.54, "3", se["nets"][2])):
            K.pad(se["col"], y, "%s.%s" % (se["u"], pin), net, r=0.5 * sc)
        if se["res"]:
            K.pad(se["col"], 72.08, "%s.1" % se["res"], se["rnet"], r=0.5 * sc)
    for (ref, x, val) in B["caps"]:
        bx = boxes[ref]
        K.sbox(bx[0] - 0.2, bx[1] - 0.2, bx[2] + 0.2, bx[3] + 0.2, key=ref)
    for (ref, x, val) in B["res"]:
        bx = boxes[ref]
        K.sbox(bx[0] - 0.2, bx[1] - 0.2, bx[2] + 0.2, bx[3] + 0.2, key=ref)
    for (n, x, y, net) in B["jpads"]:
        K.pad(x, y, "%s.%d" % (B["jref"], n), net, r=0.6 * sc)
    for net, poly in B["bus"].items():
        K.wire(poly, "BUS-%s-%s" % (B["tag"], net if B["tag"] == "SB" else ("GND" if net == "GND" else "3V3")), net)
    for st in B["strands"]:
        K.wire(st["_pts"], st["key"], st["net"])
    for (p0, p1, q0, q1) in B["keep"]:
        it = K.box(max(p0, B["x0"]), q0, min(p1, B["x1"]), q1, key="CTX-RIB" if B["tag"] == "SB" else "CTX-PAD-END")
        it["lo"] = 1
    it = K.box(max(POST[0], B["x0"]), BY0, POST[1], BY1, t="왼쪽 받침 기둥 (바닥틀)",
               d=["기판 왼쪽 끝 밑의 기둥(x0.5~6.0): 기판과 센서 바를 M3×10 자가 탭 나사 2개(U홈)로 여기에 고정합니다.",
                  "기둥 위에는 아랫면 선·납땜이 없습니다 (버스는 x8.25부터)."])
    it["lo"] = 1
    for xc in B["bridges"]:
        it = K.box(xc - BRIDGE_W / 2, BY0, xc + BRIDGE_W / 2, BY1, t="바닥 다리 (기판 밑 2.0)",
                   d=["바닥틀의 창을 가로지르는 다리(폭 4.0, x%.1f~%.1f): 여기만 기판 밑이 2.0이고 나머지는 4.0입니다 (A20)." % (xc - 2, xc + 2),
                      "이 위를 지나는 선은 겹쳐 쌓지 말고 나란히 눕힙니다 (선 한 가닥 약 0.9). 아랫면 부품·납땜 ≤ 1.8."])
        it["lo"] = 1
    _common_keys(B, K)


def sb_ribbon(s, V, K):
    """underside view: the 16-core ribbon leaves the J201 block from below and runs back (+y) to the floor and the MB"""
    o = s.out["body"]
    x0, x1 = V.xr(60.32, 80.64)
    y0, y1 = V.Y(79.2), V.Y(BY1)
    o.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" fill="#c9d0da" fill-opacity=".75" stroke="#6b7690" '
             f'stroke-width=".3"/>')
    for n in range(1, 17):                            # each conductor from its pad (it comes up from below) to the ribbon
        x, y = 61.59 + 2.54 * ((n - 1) // 2), (72.08 if n % 2 else 74.62)
        c = "#c0392b" if n == 1 else "#8a96ab"
        o.append(f'<line x1="{V.X(x):.2f}" y1="{V.Y(y) - 0.6 * V.sc:.2f}" x2="{V.X(x):.2f}" y2="{y1:.2f}" stroke="{c}" stroke-width=".4" '
                 f'stroke-dasharray=".9 .5"/>')
    xr = V.X(61.59)                                   # conductor 1 = red stripe = pin 1 side
    o.append(f'<line x1="{xr:.2f}" y1="{y0:.2f}" x2="{xr:.2f}" y2="{y1:.2f}" stroke="#c0392b" stroke-width=".7"/>')
    K.box(60.32, 75.89, 80.64, 79.2, key="W101~W107", q="J201 2×8에 아랫면에서 납땜(선 n = 핀 n, 1번 = 빨간 줄). 기판 밑(바닥 창) → 바닥 → MB J301.")


def end_leads(s, V, B, K):
    """underside view: the lead strands leave the pads from below toward the rear (+y)"""
    o = s.out["body"]
    tag = B["tag"]
    wid = "W401" if tag == "EL" else "W411"
    for (n, x, y, net) in B["jpads"]:
        c = "#c0392b" if n == 1 else "#8a96ab"
        o.append(f'<line x1="{V.X(x):.2f}" y1="{V.Y(y) - 0.55 * V.sc:.2f}" x2="{V.X(x):.2f}" y2="{V.Y(79.0):.2f}" stroke="{c}" stroke-width=".55" '
                 f'stroke-dasharray="1.0 .5"/>')
    xs = [p[1] for p in B["jpads"]]
    K.box(min(xs) - 0.6, 75.89, max(xs) + 0.6, 79.0, key=wid)


# ====================================================================== the sheet
def brd02():
    s = Sheet("BRD-02", 9, S.TOTAL, "센서 기판 배치 (SB · EL · ER, 윗면 · 아랫면)",
              "SB 160.02 × 15.24 · EL 43.18 · ER 20.32 (구멍 6행) 양면 도트 기판. 기판마다 윗면(센서, 위에서 봄)과 아랫면(버스·1206 부품·선, 아래에서 본 거울상). 모듈 좌표 mm.",
              "SB · EL · ER", qty="SB × 7 · EL × 1 · ER × 1", basis="v4 W1+ r4.5", **S.REV_E)
    o = s.out["body"]
    sb = sb_board()
    # ------------------------------------------------------------ SB top
    sc = 2.2
    VT = View(sc, 44.18, 34.0, S.CUT_X0, S.SB_X1, False)
    VB = View(sc, 44.18, 98.5, S.CUT_X0, S.SB_X1, True)
    K = HK.Keys(s, VT.X, VT.Y)
    T(s, 14.0, 27.6, "SB 윗면 (부품 쪽) — 위에서 봄: 센서 12개만 (센서 바가 덮음, 나머지 부품·선은 모두 아랫면)", "noteb", fs=2.9)
    S.size_badge(s, 263.0, 27.6, "SB 자르는 크기 %.2f × 15.24 mm — 구멍 63 × 6 (×7장)" % (S.SB_X1 - S.CUT_X0), fs=2.2)
    draw_top(s, VT, sb, "", K)
    _row_labels(s, VT, sb, 39.6)
    for se in sb["sens"]:
        T(s, VT.X(se["xk"]), VT.Y(BAR_Y[1]) - 1.1, se["key"], "noteb", "middle", fs=2.6)
        T(s, VT.X(se["xk"]), VT.Y(BAR_Y[0]) + 3.0, se["u"], "ref", "middle", fs=2.2)
        T(s, VT.X(se["xk"]), VT.Y(BAR_Y[0]) + 5.5, "%.2f" % se["xk"], "tblm", "middle", fs=1.7)
    T(s, VT.X(80.9), VT.Y(73.35) + 0.6, "J201 리본 2×8 — 구멍만 (리본은 아랫면에서 납땜)", "cabt", fs=1.6)
    S.size_mark(s, VT.X(S.CUT_X0), VT.Y(BY1), VT.X(S.SB_X1), VT.Y(BY0), S.SB_X1 - S.CUT_X0, 15.24, wy=VT.Y(BAR_Y[0]) + 9.6, hx=17.0)
    T(s, 14.0, VT.Y(BAR_Y[0]) + 3.0, "점선 = 센서 바(출력물)", "notes", fs=1.6)
    T(s, 14.0, VT.Y(BAR_Y[0]) + 5.3, "회색 = 오른쪽 턱(프레임)", "notes", fs=1.6)
    # ------------------------------------------------------------ SB underside
    K = HK.Keys(s, VB.X, VB.Y)
    T(s, 14.0, 92.6, "SB 아랫면 (납땜·배선 쪽) — 아래에서 봄, 좌우가 윗면과 반대: 버스 2줄 · 100 nF ×12 · 10 µF ×2 · 피복 단선 16가닥 · 리본", "noteb", fs=2.9)
    draw_under(s, VB, sb, K)
    sb_ribbon(s, VB, K)
    _row_labels(s, VB, sb, 39.6)
    for se in sb["sens"]:
        T(s, VB.X(se["col"]), VB.Y(BY0) + 2.9, se["u"], "ref", "middle", fs=1.9)
    T(s, VB.X(70.48) + 0.0, VB.Y(79.2) - 0.9, "리본 W101 16심 → 기판 밑 → 바닥 → MB J301 (1번 = 빨간 줄)", "cabt", "middle", fs=1.6)
    for xc in BRIDGES:
        T(s, VB.X(xc), VB.Y(BY0) + 5.4, "바닥 다리 (밑 2.0)", "notes", "middle", fs=1.4)
    T(s, VB.X(3.25), VB.Y(BY0) + 5.4, "왼쪽 기둥·U홈", "notes", "middle", fs=1.4)
    T(s, VB.X(160.65), VB.Y(BY0) + 5.4, "받침 패드(점선)", "notes", "middle", fs=1.4)
    # ------------------------------------------------------------ SB table + notes
    rows = []
    for i, se in enumerate(sb["sens"]):
        st = sb["strands"][i]
        pin = B3.sb_rows()[i]["pin"]
        rows.append([se["u"], se["key"], "%.3f" % se["xk"], "%.2f" % se["col"], se["cap"], "%d → J201.%d" % (st["no"], pin)])
    s.table(14, 146.0, ["센서", "건반", "소자 x", "리드 구멍 x", "100 nF", "OUT 선 → 핀"], rows, [14, 11, 16, 20, 15, 26],
            title="SB 센서·콘덴서·선 (리드 구멍 x = 소자 x + 3.0 이상 첫 격자)", rh=3.0, mono_cols=(0, 2, 3, 4, 5))
    para(s, 122.0, 148.0, [
        "SB 주",
        "1. 기판 x1.90~161.92 × y60.65~75.89 = 160.02 × 15.24, 63열 × 6행(두 짧은 변은 구멍 사이 가운데). 바 끝 x162.9보다 1.0 짧고 오른쪽 턱 기둥 x163.0과 1.08.",
        "2. 윗면 = 센서만: WSH137 표시면('W137')을 위로 눕혀 리드를 +x로 빼고 1.40~3.44 mm에서 2.54 간격으로 벌려 꺾는다. 핀 1 VCC = 앞(y64.46), 2 GND, 3 OUT = 뒤.",
        "3. 아랫면: 3V3(y64.46)·GND(y67.00) 버스 = 주석 맨선 x8.25~160.65, 지나는 센서 핀마다 납땜. 100 nF C201~C212 = 1206, 각 센서 리드 열의 3V3·GND 납땜 위에 걸쳐",
        "    붙임(센서 바로 옆 = 가장 짧은 고리). 10 µF C213 x8.25 · C214 x158.11은 버스 양 끝의 빈 구멍 위. 그림의 1206 상자 = 실제 크기 3.2 × 1.6.",
        "4. 선 1~12 = OUT → J201: 반 칸 줄 y70.81에 나란히 눕혀 모으고(겹쳐 쌓지 않음 — 바닥 다리 위는 기판 밑 2.0), 홀수 핀은 앞줄 y72.08로, 짝수 핀은 핀 옆 반 칸",
        "    기둥에서 앞줄을 건너 y73.35 → 뒷줄 y74.62. 선 13~16 = 전원: J201.1·16 → 3V3 버스, J201.2·15 → GND 버스(끝은 버스가 지나는 빈 구멍 ●에 버스와 함께 납땜).",
        "5. 순서: 센서를 꽂아 납땜하고 다리를 1 mm 아래로 자름 → 버스 → 1206 14개 → 선 16가닥(번호 = wiring_SB.csv) → 리본 → 센서 바를 뒤에서 밀어 끼움.",
        "    1206을 먼저 달면 리드 구멍이 납으로 막혀 센서를 꽂을 수 없다.",
        "6. 회색 점선 상자 = 받침 패드(A20: 쓰지 않는 1·6행, 오른쪽 끝과 바닥 다리 3곳): 그 위에는 선·납땜이 없다(자동 검사). 그 밖의 기판 밑은 바닥판이 뚫려 4.0,",
        "    흐린 띠 = 바닥 다리(폭 4.0, 기판 밑 2.0): 아랫면 부품·납땜 ≤ 1.8. 오른쪽 끝(그림 왼쪽)은 나사 없이 프레임 턱 밑으로 밀어 넣는다.",
        "7. 리본 16심(W101~W107)을 J201 2×8에 아랫면에서 납땜: 선 n = 핀 n, 1 = 빨간 줄 = 앞줄 왼쪽(아랫면 그림에서는 오른쪽), 15 = GND, 16 = 3V3 → 기판 밑 → 바닥 → MB J301(△33).",
        "8. 확인: 3V3–GND 단락 없음, J201.1·16 ↔ U201 핀 1 = 0 Ω, J201.2·15 ↔ U201 핀 2 = 0 Ω, J201 핀 n ↔ 센서 OUT = 0 Ω(표) → 3.3 V를 넣고 자석 없이 OUT 1.59~1.71 V,",
        "    S극을 표시면에 가까이 하면 오른다. 건반을 얹은 쉼: 백 ≈1.78 · 흑 ≈1.72 V.",
    ], fs=1.85, lh=2.72)
    # ------------------------------------------------------------ EL / ER (top + underside each)
    sce = 2.0
    oy = 201.5
    end_tab = []
    for tag, ox_t, ox_b in (("EL", 27.0, 121.0), ("ER", 224.0, 268.0)):
        B = end_board(tag)
        Bd = S.END_BOARDS[tag]
        VTe = View(sce, ox_t, oy, S.CUT_X0, Bd["cut1"], False)
        VBe = View(sce, ox_b, oy, S.CUT_X0, Bd["cut1"], True)
        ncol_ = len(cols(S.CUT_X0, Bd["cut1"]))
        side = "왼쪽" if tag == "EL" else "오른쪽"
        T(s, ox_t - (4.0 if tag == "EL" else 0.0), 194.8, "%s — %s 끝 (%s) · %.2f × 15.24, 구멍 %d × 6%s" % (
            tag, side, " · ".join(k[1] for k in Bd["keys"]), Bd["cut1"] - S.CUT_X0, ncol_, "" if tag == "EL" else " (로컬 x)"), "noteb", fs=2.3)
        T(s, ox_t, 198.4, "윗면 (센서)", "notes", fs=1.7)
        T(s, ox_b, 198.4, "아랫면 (거울상)", "notes", fs=1.7)
        K = HK.Keys(s, VTe.X, VTe.Y, m=tag)
        draw_top(s, VTe, B, "", K)
        K = HK.Keys(s, VBe.X, VBe.Y, m=tag)
        draw_under(s, VBe, B, K)
        end_leads(s, VBe, B, K)
        for se in B["sens"]:
            T(s, VTe.X(se["xk"]), VTe.Y(BAR_Y[0]) + 2.8, "%s %s" % (se["u"], se["key"]), "ref", "middle", fs=1.7)
        T(s, VBe.X(sum(p[1] for p in B["jpads"]) / len(B["jpads"])), VBe.Y(79.0) - 0.8,
          "%s %d심 → 뒤 통로 XH" % ("W401" if tag == "EL" else "W411", len(B["jpads"])), "cabt", "middle", fs=1.45)
        S.size_dim(s, VTe.X(S.CUT_X0), VTe.X(Bd["cut1"]), VTe.Y(BAR_Y[0]) + 7.8, "%.2f mm" % (Bd["cut1"] - S.CUT_X0), fs=1.7)
        for i, se in enumerate(B["sens"]):
            end_tab.append([tag, se["u"], se["key"], "%.2f" % se["col"], "%s · %s" % (se["cap"], se["res"]), "%s.%d" % (Bd["jref"], 2 + i)])
        end_tab_bulk = None  # noqa: F841
    _row_labels(s, View(sce, 27.0, oy, S.CUT_X0, 45.08, False), end_board("EL"), 21.8, fs=1.45)
    s.table(318, 194.0, ["보드", "센서", "건반", "리드 x", "100n · 1k", "→ 패드"], end_tab, [9, 11, 10, 13, 22, 16],
            title="EL·ER 센서 (SB와 같은 규칙)", rh=3.0, mono_cols=(1, 3, 4, 5))
    T(s, 318.0, 222.0, "10 µF: C404 (EL) · C412 (ER), x8.25", "notes", fs=1.7)
    para(s, 14.0, 254.5, [
        "EL·ER 주",
        "1. SB와 같은 6행 띠: y61.92 예비 · 64.46 3V3 · 67.00 GND · 69.54 OUT · 72.08 1 kΩ 끝 · 74.62 리드 패드. 점선 = 끝 부속 센서 바(흐린 칸 = A#0 낮은 구간 x19.93~33.93).",
        "2. 윗면 = 센서만. 아랫면 = 버스 2줄 + 1206 모두: 100 nF(3V3–GND), 1 kΩ(OUT → y72.08, △13), 10 µF(x8.25) + 피복 단선(번호 = wiring_small.csv EL·ER).",
        "3. 선 1 = GND 버스 → 패드 1, 선 2 = 3V3 버스 → 끝 패드(반 칸 기둥에서 GND 버스를 구멍 사이로 건넘), 선 3~ = 1 kΩ 끝 → 반 칸 줄 y73.35 → 패드 2~ (자동 검사).",
        "4. 고정: 왼쪽 U홈 M3×10 ×2 + 오른쪽 끝 받침 패드(점선, A20: EL x42.8~46.3 · ER x19.3~22.8) — 패드 둘레에는 선·납땜 없음. 기판 밑은 바닥이 뚫려 4.0.",
        "5. 리드(W401 5심 · W411 3심): 패드에 아랫면에서 납땜 → 뒤(+y) → y77.39 안에서 EL x14.83~21.18 · ER x8.89~12.70으로 모음 → 레일 밑 차선 → 뒷벽 홈 → XH.",
        "6. 순서: 센서 → 버스 → 1206 → 선 → 리드. 확인: 패드 1 ↔ 센서 핀 2 = 0 Ω, 끝 패드 ↔ 핀 1 = 0 Ω, 패드 2~ ↔ 그 센서 OUT = 1 kΩ.",
    ], fs=1.75, lh=2.55)
    # ------------------------------------------------------------ regions (page crops) + checks
    s.regions["sb-front"] = (11.0, 24.0, 409.0, 87.5)
    s.regions["sb-back"] = (11.0, 88.5, 409.0, 142.0)
    s.regions["el"] = (11.0, 191.0, 215.0, 250.0)
    s.regions["er"] = (215.0, 191.0, 314.0, 250.0)
    s.regions["sb"] = (9.0, 20.0, 411.0, 142.0)          # whole SB (both views)
    s.regions["end"] = (9.0, 191.0, 411.0, 252.0)         # whole EL / ER band
    s.board_check = ["SB: " + p for p in B3.sb_check()] + end_check()
    s.frame()
    s.expected = {}
    return s
