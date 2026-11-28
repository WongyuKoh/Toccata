"""BRD-09 ~ BRD-15: the control board MB of each octave module O1 ~ O7, top side and underside next to each other.

  BRD-09  O1  left end board   R301~R303, J302 lead W403 (5 strands) to the end part EL, ID jumper JP301
  BRD-10  O2                   ID jumper JP302
  BRD-11  O3                   JP301 + JP302
  BRD-12  O4                   JP303
  BRD-13  O5                   JP301 + JP303
  BRD-14  O6                   JP302 + JP303
  BRD-15  O7  right end board  R301, J302 lead W413 (3 strands) to the end part ER, JP301 + JP302 + JP303

The user (2026-11-12): "7개 기판을 왼쪽 끝, 오른쪽 끝, 나머지 기판 회로 이렇게 나눠서 회로 도면을 보여줄래?" -> three kinds; (2026-11-23):
"기판 1번부터 7번까지 하나하나 선택해서 볼 수 있게 하고, 사용하지 않는 회로는 애초에 그리지 마" -> one sheet per board, and a sheet
draws ONLY what that board carries: the parts it is fitted with (R30x, closed ID jumpers, the EXT lead) and the underside wires that
connect them (used_nos: every wire of BRD-08 / wiring_MB.csv, pruned of branches that end at a pad nothing on this board needs - an empty
R30x / J302 place, an open jumper, JP304). Nets, pads and routes are still SCH-03 / BRD-01 / BRD-08 (sheets.py MB geometry, mbroute.py).

Each sheet: left = top side (seen from above), right = underside (seen from below, mirrored). Regions 'front' / 'back' are the crops
the page shows. Click data (s.hits_custom -> build.py sheethits.json -> hits.py): wires, pads and part boxes of BOTH views, plus
padnote / pnote (what is special on this board) and 'extra' ready-made items (lead strands, the rail strip).
"""
import harness as HN
import mbroute as MR
import parts as P
from boards3 import ncol
from sch import Sheet, text_w

SC = 1.55                      # sheet mm per model mm (BRD-01 / BRD-08 use 2.0 for one view)
OY = 47.0
OXF, OXB = 17.0, 217.0         # left edge of the top view / of the underside view

def _kind(n):
    end = {1: dict(r=("R301", "R302", "R303"), ext={1: "GND", 2: "EXT1", 3: "EXT2", 4: "EXT3", 6: "+3V3"}, lead="W403", end="EL",
                   end_keys="A0 · A#0 · B0", name="O1 (왼쪽 끝)"),
           7: dict(r=("R301",), ext={1: "GND", 2: "EXT1", 6: "+3V3"}, lead="W413", end="ER", end_keys="C8", name="O7 (오른쪽 끝)")}
    v = dict(key="O%d" % n, code="BRD-%02d" % (8 + n), num=15 + n, fn="brd%02d" % (8 + n), boards=[n], short="O%d" % n,
             qty="MB × 1 (O%d)" % n, r=(), ext={}, lead=None, end=None, end_keys="", name="O%d (가운데)" % n)
    v.update(end.get(n, {}))
    return v


KINDS = {"O%d" % n: _kind(n) for n in range(1, 8)}         # BRD-09 = O1 ... BRD-15 = O7


def jp_closed(n):
    """board number 1..7 -> the ID jumpers that are bridged (bit k of the number = JP30(k+1), export.id_rows())."""
    return {"JP30%d" % (k + 1) for k in range(3) if (n >> k) & 1}


def required(v, ref, num):
    """a pad this board needs for itself: header pins of the Zero / mux, the ribbon, test points, the fitted R30x, the closed ID jumpers,
    the J302 pads of the EXT lead"""
    if ref in ("A301", "A302", "J301") or ref.startswith("TP"):
        return True
    if ref.startswith("R30"):
        return ref in v["r"]
    if ref.startswith("JP"):
        return ref in jp_closed(v["boards"][0])
    if ref == "J302":
        return int(num) in v["ext"]
    return True


_USED = {}


def used_nos(v):
    """numbers of the BRD-08 wires this board needs: all wires, minus (repeatedly) every wire with an end at a pad that this board does not
    need and that no other remaining wire touches (a dead branch: EXT lines to an empty J302, the R30x places, open jumpers, JP304)"""
    if v["key"] not in _USED:
        live = {w["no"]: w for w in MR.get()[1]}
        while True:
            deg = {}
            for w in live.values():
                for e in (w["a"], w["b"]):
                    deg[e] = deg.get(e, 0) + 1
            drop = [no for no, w in live.items()
                    if any(not required(v, e.split(".")[0], e.split(".")[1]) and deg[e] == 1 for e in (w["a"], w["b"]))]
            if not drop:
                break
            for no in drop:
                live.pop(no, None)
        _USED[v["key"]] = set(live)
    return _USED[v["key"]]


def wire_used(v, w):
    """True for a wire this board needs (used_nos)"""
    return w["no"] in used_nos(v)


def pad_state(v, ref, num, net, ends):
    """'sol' soldered on this board (a part pin it carries or a joint of wires it needs), 'empty' nothing (not drawn)."""
    if not MR.soldered((ref, num, net)):
        return "empty"
    if required(v, ref, num) or any(wire_used(v, w) for w in ends.get("%s.%s" % (ref, num), [])):
        return "sol"
    return "empty"


def _harness(wid):
    for h in HN.HARNESS:
        if h.get("id") == wid:
            return h
    return None


def _ranges(nums):
    nums = sorted(nums)
    out, a, b = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == b + 1:
            b = n
            continue
        out.append((a, b))
        a = b = n
    out.append((a, b))
    return ", ".join(str(a) if a == b else "%d~%d" % (a, b) for a, b in out)


def _sheet(key):
    import sheets as S
    v = KINDS[key]
    r, rows, probs = MR.get()
    x0, x1, y0, y1 = MR.BOARD
    kname = v["short"]
    closed = jp_closed(v["boards"][0])
    sub = ("SCH-03 · BRD-01 · BRD-08과 같은 기판에서 %s에 다는 부품과 쓰는 선만 그림: 왼쪽 = 윗면(부품), 오른쪽 = 아랫면(배선, 좌우 거울상). "
           "이 기판에 없는 자리·선은 그리지 않음." % kname)
    s = Sheet(v["code"], v["num"], S.TOTAL, "제어 기판 %s — 윗면 · 아랫면" % v["name"], sub, "MB", qty=v["qty"],
              basis="SCH-03 · BRD-01 · BRD-08", **S.REV_E)      # same circuit revision as every sheet (drawn 2026-11-12)
    s.board_check = list(probs)
    o = s.out["body"]
    ends = {}
    for w in rows:
        for e in (w["a"], w["b"]):
            ends.setdefault(e, []).append(w)
    state = {(ref, num): pad_state(v, ref, num, net, ends) for (ref, num, net) in r.pads.values()}

    def Y(y):
        return OY + (y1 - y) * SC

    def XF(x):
        return OXF + (x - x0) * SC

    def XB(x):                      # underside: world +x to the LEFT
        return OXB + (x1 - x) * SC

    def tx(x, y, txt, cls="pinname", anchor="start", fs=1.3):
        S._tx(s, x, y, txt, cls, anchor, fs=fs)

    def pad(X, x, y, st, net, square=False, rad=0.82):
        c = "#fff" if net == "NC" else ncol(net)
        if st != "sol":                     # not on this board: not drawn at all (2026-11-23)
            return
        if square:
            o.append(f'<rect x="{X(x)-rad:.2f}" y="{Y(y)-rad:.2f}" width="{2*rad:.2f}" height="{2*rad:.2f}" fill="{c}" stroke="#1f2a44" stroke-width=".3"/>')
        else:
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{rad:.2f}" fill="{c}" stroke="#1f2a44" stroke-width=".3"/>')

    zx0, zy0 = S.ZERO_ORIGIN
    mx0, my0 = S.MUX_ORIGIN
    YT = y1 + 8.0
    names = dict(P.RP2040_ZERO)
    mux_names = ["C%d" % i for i in range(16)] + ["GND", "VCC", "EN", "S0", "S1", "S2", "S3", "SIG"]
    jp_state = {ref: ("closed" if ref in closed else "open") for ref in S.JP_PADS}

    # ================================================================== top side (parts), seen from above
    S.mb_frame_draw(s, XF, Y)
    S.size_mark(s, XF(x0), Y(y1), XF(x1), Y(y0), 120, 80, wy=Y(y0) + 9.5, hx=XF(x0) - 4.2,
                badge=(XF(x0) + 40.0, Y(YT) - 3.4, "실제 크기 120 × 80 mm (8 × 12 cm 통째로, 구멍 42 × 30)"))
    tx(XF(x0), Y(YT) - 3.4, "윗면 (부품 쪽) — 위에서 봄", "noteb", fs=3.0)
    tx(XF(x0), Y(y0) + 5.6, "앞 (연주자 쪽) ↓", "notes", fs=1.8)
    tx(XF(x1), Y(YT) - 3.4, "뒤 (USB 쪽) ↑", "notes", "end", fs=1.8)
    tx(XF(x0) + 2.0, Y(138.4) + 0.6, "밸런스 레일이 얹히는 띠 — 부품·납땜 없음", "notes", fs=1.6)
    # RP2040-Zero, USB receptacle, cable plug
    o.append(f'<rect x="{XF(zx0):.2f}" y="{Y(zy0):.2f}" width="{18*SC:.2f}" height="{23.5*SC:.2f}" rx="1.6" fill="#1f2a44" fill-opacity=".08" '
             f'stroke="#1f2a44" stroke-width=".45"/>')
    px0, px1, py0 = S.PLUG[0], S.PLUG[1], S.PLUG[2]
    o.append(f'<rect x="{XF(px0):.2f}" y="{Y(YT):.2f}" width="{(px1-px0)*SC:.2f}" height="{(YT-py0)*SC:.2f}" fill="#2b2b2b" fill-opacity=".14" '
             f'stroke="#2b2b2b" stroke-width=".35" stroke-dasharray="2 .8"/>')
    o.append(f'<rect x="{XF(S.USB_RX[0]):.2f}" y="{Y(S.USB_RY[1]):.2f}" width="{(S.USB_RX[1]-S.USB_RX[0])*SC:.2f}" '
             f'height="{(S.USB_RY[1]-S.USB_RY[0])*SC:.2f}" fill="#c9d0da" stroke="#1f2a44" stroke-width=".3"/>')
    tx(XF(83.38), Y(166.4), "USB-C", "notes", "middle", fs=1.4)
    tx(XF(zx0 + 9), Y(zy0 - 11.6), "A301", "ref", "middle", fs=2.2)
    tx(XF(zx0 + 9), Y(zy0 - 13.6), "RP2040-Zero", "notes", "middle", fs=1.5)
    tx(XF(px0) - 1.2, Y(YT) + 2.4, "USB 선 → 허브", "cabt", "end", fs=1.5)
    # 4067 module
    o.append(f'<rect x="{XF(mx0):.2f}" y="{Y(my0+S.MUX_D):.2f}" width="{S.MUX_W*SC:.2f}" height="{S.MUX_D*SC:.2f}" rx=".8" fill="#1f5fbf" '
             f'fill-opacity=".08" stroke="#1f5fbf" stroke-width=".45"/>')
    tx(XF(mx0 + 20.3), Y(my0 + 9.6), "A302 4067 먹스 모듈", "ref", "middle", fs=2.2)
    gx_, gy_ = S.mux_hole("GND")
    vx_, _ = S.mux_hole("VCC")
    cxa, cxb = sorted((XF(gx_), XF(vx_)))
    o.append(f'<rect x="{cxa-1.2:.2f}" y="{Y(gy_)-1.5:.2f}" width="{cxb-cxa+2.4:.2f}" height="3.0" fill="none" stroke="#b86e00" '
             f'stroke-width=".35" stroke-dasharray=".9 .5"/>')
    if XF(gx_) >= XF(vx_):                  # label on the GND side, outside the control row
        tx(cxb + 1.6, Y(gy_) + 0.5, "C301 (아랫면)", "notes", "start", fs=1.3)
    else:
        tx(cxa - 1.6, Y(gy_) + 0.5, "C301 (아랫면)", "notes", "end", fs=1.3)
    # ribbon from the sensor board
    rb0, rb1 = 70.48 - 10.16, 70.48 + 10.16
    o.append(f'<rect x="{XF(rb0):.2f}" y="{Y(S.MB["ribbon"][2]):.2f}" width="{(rb1-rb0)*SC:.2f}" height="{(S.MB["ribbon"][2]-y0)*SC:.2f}" fill="#c9d0da" '
             f'fill-opacity=".35" stroke="#6b7690" stroke-width=".3" stroke-dasharray="1.4 .8"/>')
    o.append(f'<rect x="{XF(rb0):.2f}" y="{Y(y0):.2f}" width="{(rb1-rb0)*SC:.2f}" height="6.40" fill="#c9d0da" fill-opacity=".7" stroke="#6b7690" stroke-width=".3"/>')
    o.append(f'<line x1="{XF(rb0):.2f}" y1="{Y(y0)+0.3:.2f}" x2="{XF(rb0):.2f}" y2="{Y(y0)+6.4:.2f}" stroke="#c0392b" stroke-width=".7"/>')
    tx(XF(70.48), Y(y0) + 4.0, "리본 16심 ← 센서 기판 SB", "cabt", "middle", fs=1.5)
    tx(XF(S.RIB_X0) - 1.8, Y(S.RIB_Y[0]) - 0.6, "J301", "ref", "end", fs=1.9)
    # EXT pull-downs: fitted = body with the 100k colour bands, not fitted = dashed place
    for ref, (x, y) in S.R_EXT.items():
        bx, bw_ = XF(x) + 1.25, 7.62 * SC - 2.5
        if ref in v["r"]:                   # fitted only; an empty place is not drawn
            o.append(f'<line x1="{XF(x):.2f}" y1="{Y(y):.2f}" x2="{XF(x+7.62):.2f}" y2="{Y(y):.2f}" stroke="#8a96ab" stroke-width=".35"/>')
            o.append(f'<rect x="{bx:.2f}" y="{Y(y)-1.1:.2f}" width="{bw_:.2f}" height="2.2" rx=".8" fill="#f3e3c3" stroke="#8a5a00" stroke-width=".3"/>')
            for f, c in ((.18, "#7b4a12"), (.34, "#111"), (.50, "#e2b100"), (.78, "#b8962e")):
                o.append(f'<rect x="{bx+bw_*f:.2f}" y="{Y(y)-1.1:.2f}" width=".75" height="2.2" fill="{c}"/>')
            tx(XF(x + 7.62) + 1.5, Y(y) + 0.5, "%s 100 kΩ" % ref, "pinname", fs=1.35)
    # ID / PED jumpers: the bridge is on the underside (dashed here)
    for ref, (sig, gnd) in S.JP_PADS.items():
        if jp_state[ref] != "closed":       # open jumpers (and JP304 on every MB) are not drawn
            continue
        xa, xb = sorted((XF(sig[0]), XF(gnd[0])))
        o.append(f'<rect x="{xa-1.25:.2f}" y="{Y(sig[1])-1.25:.2f}" width="{xb-xa+2.5:.2f}" height="2.5" rx="1.25" fill="#aab3bd" '
                 f'fill-opacity=".55" stroke="#1d2433" stroke-width=".3" stroke-dasharray=".7 .45"/>')
        tx(XF(gnd[0]) + 1.4, Y(gnd[1]) + 0.5, ref + " 연결", "pinname", fs=1.25)
    jl = {"closed": "연결", "open": "연결 안 함"}
    tx(XF(S.JP_PADS["JP303"][1][0]) + 1.4, Y(S.JP_PADS["JP303"][1][1]) + 3.2,
       "ID 점퍼 연결: " + " · ".join(sorted(closed)) + " (아랫면 납땜 브리지)", "notes", fs=1.25)
    # pads
    for (k, m), (ref, num, net) in r.pads.items():
        pad(XF, MR.X(k), MR.Y(m), state[(ref, num)], net, square=ref in ("J301", "J302"))
    for ref, (x, y) in S.TP_POS.items():
        o.append(f'<circle cx="{XF(x):.2f}" cy="{Y(y):.2f}" r="1.2" fill="none" stroke="#1f5fbf" stroke-width=".4"/>')
    tx(XF(S.TP_POS["TP302"][0]), Y(S.TP_POS["TP302"][1]) - 1.9, "TP301 · 302 · 303", "pinname", "middle", fs=1.25)
    # pin names
    for n in range(1, 19):
        x, y = S.zero_hole(n)
        if n <= 9:
            tx(XF(x) - 1.75, Y(y) + 0.5, names[n], "pinname", "end", fs=1.3)
        else:
            tx(XF(x) + 1.75, Y(y) + 0.5, names[n], "pinname", fs=1.3)
    for nm in mux_names:
        x, y = S.mux_hole(nm)
        tx(XF(x), Y(y) + (-1.5 if nm.startswith("C") else 2.5), nm, "pinname", "middle", fs=1.25)
    for n in range(1, 17):
        x, y = S.mb_pad_xy("J301", n)
        tx(XF(x), Y(y) + (2.5 if n % 2 else -1.4), str(n), "pinnum", "middle", fs=1.2)
    # J302 and the EXT lead (soldered from the top, over the rear edge, under the USB plug to the rear-wall opening)
    j302_on = [n for n in range(1, 7) if state.get(("J302", str(n))) == "sol"]
    for n in j302_on:
        tx(XF(S.EXT_X0 + 2.54 * (n - 1)), Y(S.EXT_Y) + 2.6, str(n), "pinnum", "middle", fs=1.2)
    lead_items = []
    h = _harness(v["lead"]) if v["lead"] else None
    if h:
        order = sorted(v["ext"])
        cond = {int(c[3]): c for c in h["cond"]}                # J302 pad -> (core no, colour, net text, J302 pad, housing pin)
        for i, n in enumerate(order):
            x = S.EXT_X0 + 2.54 * (n - 1)
            hy, cx = y1 + 1.3 + 0.75 * i, 85.4 + 0.75 * i
            pts = [(XF(x), Y(S.EXT_Y)), (XF(x), Y(hy)), (XF(cx), Y(hy)), (XF(cx), Y(YT))]
            net = v["ext"][n]
            d = " ".join("%.2f,%.2f" % p for p in pts)
            o.append(f'<polyline points="{d}" fill="none" stroke="#fff" stroke-width=".85" stroke-linejoin="round"/>')
            o.append(f'<polyline points="{d}" fill="none" stroke="{ncol(net)}" stroke-width=".45" stroke-linejoin="round"/>')
            c = cond[n]
            lead_items.append(dict(k="w", g=[[[round(a, 2), round(b, 2)] for a, b in pts]], n=net,
                                   t="%s %d번 가닥 · %s" % (v["lead"], c[0], c[2]),
                                   d=["%s: %s" % (v["lead"], h["title"]),
                                      "J302 %d번 패드(윗면에서 납땜) → %s %s번" % (n, h["b"][0], c[4]),
                                      "선: " + h["cable"],
                                      "자르는 길이: " + h["cut_txt"],
                                      "길: J302 윗면 → 기판 뒤 모서리·뒤 턱 위 → 바닥 → USB 플러그 밑 → 뒷벽 개구 → 통로"]))
        tx(XF(S.EXT_X0 + 5 * 2.54) + 1.8, Y(S.EXT_Y) + 0.5, "J302", "ref", fs=1.6)
        tx(XF(px1) + 1.4, Y(YT) + 2.4, "%s %d가닥 → 끝 부속 %s (%s 건반)" % (v["lead"], len(order), v["end"], v["end_keys"]), "cabt", fs=1.5)
    elif j302_on:
        tx(XF(S.EXT_X0 + 2.54 * (max(j302_on) - 1)) + 1.8, Y(S.EXT_Y) + 0.5, "J302 %s번 = GND 이음 자리 (EXT 선 없음)" % "·".join(map(str, j302_on)),
           "notes", fs=1.3)

    # ================================================================== underside (wiring), seen from below - mirrored
    S.mb_frame_draw(s, XB, Y, top=False)
    S.size_mark(s, XB(x1), Y(y1), XB(x0), Y(y0), 120, 80, wy=Y(y0) + 9.5, hx=XB(x1) - 4.2)
    tx(XB(x1), Y(YT) - 3.4, "아랫면 (납땜·배선 쪽) — 아래에서 봄, 좌우가 반대", "noteb", fs=3.0)
    tx(XB(x1), Y(y0) + 5.6, "앞 (연주자 쪽) ↓", "notes", fs=1.8)
    tx(XB(x0), Y(YT) - 3.4, "뒤 (USB 쪽) ↑", "notes", "end", fs=1.8)
    rx0, rx1, ry1 = S.MB["ribbon"]
    o.append(f'<rect x="{XB(rx1):.2f}" y="{Y(ry1):.2f}" width="{(rx1-rx0)*SC:.2f}" height="{(ry1-y0)*SC:.2f}" fill="#c9d0da" fill-opacity=".75" '
             f'stroke="#6b7690" stroke-width=".3"/>')
    for (k, m) in sorted(MR.strand_lanes()):
        xl, yl = MR.X(k), MR.Y(m)
        o.append(f'<line x1="{XB(xl):.2f}" y1="{Y(yl)+1.3:.2f}" x2="{XB(xl):.2f}" y2="{Y(yl)-1.3:.2f}" stroke="#6b7690" stroke-width=".75" '
                 f'stroke-opacity=".55" stroke-linecap="round"/>')
    tx(XB((rx0 + rx1) / 2), Y(y0) - 2.0, "리본·가닥 자리 (선 없음)", "notes", "middle", fs=1.4)
    o.append(f'<rect x="{XB(zx0+18):.2f}" y="{Y(zy0):.2f}" width="{18*SC:.2f}" height="{23.5*SC:.2f}" rx="1.6" fill="none" stroke="#1f2a44" '
             f'stroke-width=".35" stroke-dasharray="2 1" stroke-opacity=".5"/>')
    o.append(f'<rect x="{XB(mx0+S.MUX_W):.2f}" y="{Y(my0+S.MUX_D):.2f}" width="{S.MUX_W*SC:.2f}" height="{S.MUX_D*SC:.2f}" rx=".8" fill="none" '
             f'stroke="#1f5fbf" stroke-width=".35" stroke-dasharray="2 1" stroke-opacity=".5"/>')
    tx(XB(zx0 + 9), Y(zy0 - 6.0), "A301 (윗면)", "notes", "middle", fs=1.4)
    tx(XB(mx0 + 30.5), Y(my0 + 10.8), "A302 (윗면)", "notes", "middle", fs=1.4)
    # resistor places on the other side
    for ref, (x, y) in S.R_EXT.items():
        if ref in v["r"]:
            o.append(f'<rect x="{XB(x+7.62)+1.25:.2f}" y="{Y(y)-1.0:.2f}" width="{7.62*SC-2.5:.2f}" height="2.0" rx=".8" fill="#f3e3c3" '
                     f'fill-opacity=".5" stroke="#8a5a00" stroke-width=".25" stroke-dasharray=".8 .5"/>')
    # wires: only the ones this board needs (used_nos); the others are not drawn
    urows = [w for w in rows if wire_used(v, w)]
    for w in urows:
        d = " ".join("%.2f,%.2f" % (XB(x), Y(y)) for x, y in w["pts"])
        o.append(f'<polyline points="{d}" fill="none" stroke="{ncol(w["net"])}" stroke-width=".45" stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".9"/>')
    # jumper bridges of this board (solder blob under the two pads), then the pads
    for ref, (sig, gnd) in S.JP_PADS.items():
        if jp_state[ref] == "closed":
            xa, xb = sorted((XB(sig[0]), XB(gnd[0])))
            o.append(f'<rect x="{xa-1.3:.2f}" y="{Y(sig[1])-1.3:.2f}" width="{xb-xa+2.6:.2f}" height="2.6" rx="1.3" fill="#aab3bd" stroke="#1d2433" stroke-width=".35"/>')
    for (k, m), (ref, num, net) in r.pads.items():
        pad(XB, MR.X(k), MR.Y(m), state[(ref, num)], net, rad=0.78)
    g_, v_ = S.mux_hole("GND"), S.mux_hole("VCC")
    cxa, cxb = sorted((XB(g_[0]), XB(v_[0])))
    o.append(f'<rect x="{cxa-0.3:.2f}" y="{Y(g_[1])-0.75:.2f}" width="{cxb-cxa+0.6:.2f}" height="1.5" rx=".3" fill="#b98b5a" '
             f'fill-opacity=".85" stroke="#8a5a00" stroke-width=".25"/>')
    # labels (their boxes are kept clear by the wire numbers)
    placed = [(XB(MR.X(k)) - 0.95, Y(MR.Y(m)) - 0.95, XB(MR.X(k)) + 0.95, Y(MR.Y(m)) + 0.95) for (k, m), (ref, num, net) in r.pads.items()
              if state[(ref, num)] == "sol"]

    def T(x, y, txt, cls, anchor="start", fs=1.2):
        tx(x, y, txt, cls, anchor, fs=fs)
        w = text_w(str(txt), fs)
        xa = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        placed.append((xa, y - fs * 0.78, xa + w, y + fs * 0.2))
    if XB(g_[0]) >= XB(v_[0]):              # label on the GND side, outside the control row
        T(cxb + 1.4, Y(g_[1]) + 0.45, "C301", "pinname", "start", fs=1.2)
    else:
        T(cxa - 1.4, Y(g_[1]) + 0.45, "C301", "pinname", "end", fs=1.2)
    for n in range(1, 19):
        x, y = S.zero_hole(n)
        side = 1.3 if n <= 9 else -1.3                       # mirror: the left column (1~9) is on the RIGHT here
        T(XB(x) + side, Y(y) - 0.8, names[n], "pinname", "start" if side > 0 else "end", fs=1.15)
    for nm in mux_names:
        x, y = S.mux_hole(nm)
        T(XB(x), Y(y) + (-1.3 if nm.startswith("C") else 2.3), nm, "pinname", "middle", fs=1.15)
    for n in range(1, 17):
        x, y = S.mb_pad_xy("J301", n)
        T(XB(x) + 1.0, Y(y) + (1.6 if n % 2 else -0.8), str(n), "pinnum", "start", fs=1.1)
    T(XB(S.RIB_X0) + 1.8, Y(S.RIB_Y[0]) + 0.5, "J301 (1 = 이 그림의 오른쪽 끝)", "cabt", "start", fs=1.35)
    for n in j302_on:
        T(XB(S.EXT_X0 + 2.54 * (n - 1)), Y(S.EXT_Y) - 1.2, str(n), "pinnum", "middle", fs=1.1)
    if j302_on:
        T(XB(S.EXT_X0 + 2.54 * (sum(j302_on) / len(j302_on) - 1)), Y(S.EXT_Y) - 2.9, "J302 (선은 윗면에서)" if h else "J302 (GND 이음)",
          "cabt", "middle", fs=1.35)
    for ref, (sig, gnd) in S.JP_PADS.items():
        if jp_state[ref] == "closed":
            T(XB(gnd[0]) - 1.5, Y(gnd[1]) + 0.45, "%s 연결" % ref, "pinname", "end", fs=1.15)
    for ref, (x, y) in S.R_EXT.items():
        if ref in v["r"]:
            T(XB(x + 3.81), Y(y) - 1.2, ref, "pinname", "middle", fs=1.15)
    T(XB(S.TP_POS["TP302"][0]), Y(S.TP_POS["TP302"][1]) - 1.4, "TP303·302·301", "pinname", "middle", fs=1.1)
    # wire numbers on a free spot of the wire (longest segment first)
    bw, bh = 2.9, 1.8
    for w in urows:
        col = ncol(w["net"])
        segs = sorted(zip(w["pts"], w["pts"][1:]), key=lambda t: -(abs(t[0][0] - t[1][0]) + abs(t[0][1] - t[1][1])))
        box = lead = None
        for a, b in segs:
            for f in (0.5, 0.3, 0.7, 0.4, 0.6, 0.15, 0.85, 0.22, 0.78):
                mx_, my_ = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
                q = (XB(mx_) - bw / 2, Y(my_) - bh / 2, XB(mx_) + bw / 2, Y(my_) + bh / 2)
                if not any(q[0] < p[2] and p[0] < q[2] and q[1] < p[3] and p[1] < q[3] for p in placed):
                    box = q
                    break
            if box:
                break
        if box is None:                           # short wire: the number beside it with a short leader
            a, b = segs[0]
            mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            vert = abs(a[0] - b[0]) < 0.01
            offs = [(d * (bw / 2 + 1.0), 0.0) for d in (1, -1)] if vert else [(0.0, d * (bh / 2 + 1.0)) for d in (1, -1)]
            offs += [(d * (bw / 2 + 1.0), e * (bh / 2 + 0.8)) for d in (1, -1) for e in (1, -1)]
            offs += [(d * (bw + 2.2), 0.0) for d in (1, -1)] + [(0.0, d * (bh + 1.8)) for d in (1, -1)]
            for dx, dy in offs:
                cx_, cy_ = XB(mx_) + dx, Y(my_) + dy
                q = (cx_ - bw / 2, cy_ - bh / 2, cx_ + bw / 2, cy_ + bh / 2)
                if not any(q[0] < p[2] and p[0] < q[2] and q[1] < p[3] and p[1] < q[3] for p in placed):
                    box, lead = q, (XB(mx_), Y(my_))
                    break
            if box is None:
                box = (XB(mx_) - bw / 2, Y(my_) - bh / 2, XB(mx_) + bw / 2, Y(my_) + bh / 2)
        placed.append(box)
        cxn, cyn = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if lead:
            o.append(f'<line x1="{lead[0]:.2f}" y1="{lead[1]:.2f}" x2="{cxn:.2f}" y2="{cyn:.2f}" stroke="{col}" stroke-width=".2"/>')
        o.append(f'<rect x="{box[0]:.2f}" y="{box[1]:.2f}" width="{bw}" height="{bh}" rx=".45" fill="#fff" fill-opacity=".92" stroke="{col}" stroke-width=".25"/>')
        tx(cxn, cyn + 0.47, str(w["no"]), "pinnum", "middle", fs=1.25)

    # ================================================================== tables and notes
    unused = [w for w in rows if not wire_used(v, w)]
    trows = [["A301 RP2040-Zero", "답니다", "헤더 1×9 ×2 위, USB-C가 뒤"],
             ["A302 4067 먹스", "답니다", "헤더 1×16 + 1×8, 채널 줄이 앞"],
             ["J301 리본 2×8", "답니다", "SB에서 온 16심, 아랫면에서 꽂음"],
             ["C301 100 nF", "답니다 (아랫면)", "먹스 GND–VCC 꼬리 사이 1206"]]
    for ref in v["r"]:
        trows.append(["%s 100 kΩ" % ref, "답니다", "EXT%d 풀다운, 붙여 눕힘" % (int(ref[1:]) - 300)])
    if v["lead"]:
        trows.append(["J302 EXT 1×6", "%s번: %s" % ("·".join(str(n) for n in sorted(v["ext"])), v["lead"]),
                      "%d가닥 윗면 납땜 → 끝 부속 %s" % (len(v["ext"]), v["end"])])
    elif j302_on:
        trows.append(["J302 %s번" % "·".join(map(str, j302_on)), "GND 이음 자리", "EXT 선 없음, GND 선만 납땜"])
    for ref in sorted(closed):
        trows.append(["%s (ID %d)" % (ref, int(ref[-1]) - 1), "연결하세요", "아랫면 두 구멍 납땜 브리지"])
    trows.append(["TP301~303", "구멍 패드", "3V3 · GND · MUX_SIG 측정 자리"])
    yt = s.table(14, 184, ["자리", "이 기판 (%s)" % kname, "메모"], trows, [32, 34, 48], title="이 기판에 다는 것", rh=3.1)
    groups = []
    urows = [w for w in rows if wire_used(v, w)]
    for label, pred in (("+3V3", lambda n: n == "+3V3"), ("GND", lambda n: n == "GND"), ("HALL_* (센서 12)", lambda n: n.startswith("HALL_")),
                        ("EXT1", lambda n: n == "EXT1"), ("EXT2", lambda n: n == "EXT2"), ("EXT3", lambda n: n == "EXT3"),
                        ("EXT4", lambda n: n == "EXT4"), ("MUX_S0~S3", lambda n: n.startswith("MUX_S") and n != "MUX_SIG"),
                        ("MUX_SIG", lambda n: n == "MUX_SIG"), ("ID0~ID2", lambda n: n.startswith("ID")), ("PED_SEL", lambda n: n == "PED_SEL")):
        ws = [w for w in urows if pred(w["net"])]
        if ws:
            groups.append([label, _ranges([w["no"] for w in ws]), str(len(ws))])
    s.table(136, 184, ["넷", "선 번호", "가닥"], groups, [30, 34, 14],
            title="아랫면 선 %d가닥 (번호 = BRD-08 · wiring_MB.csv)" % len(urows), rh=3.1, mono_cols=(1, 2))
    gone = [ref for ref in S.R_EXT if ref not in v["r"]] + [ref for ref in S.JP_PADS if ref not in closed] + ([] if v["lead"] else ["EXT 선"])
    notes = ["주",
             "1. 왼쪽 = 윗면(부품 쪽), 오른쪽 = 아랫면(납땜·배선 쪽). 아랫면 그림은 기판을 좌우로 뒤집어 본",
             "    거울상이라 왼쪽·오른쪽이 윗면 그림과 반대다. 패드 이름을 보고 맞춘다.",
             "2. 색 = 넷: 빨강 +3V3 · 검정 GND · 파랑 센서(HALL) · 초록 EXT · 보라 먹스 선택 · 갈색 ID ·",
             "    주황 MUX_SIG. 흰 패드 = 연결 없는 헤더 핀.",
             "3. 이 기판(%s)에 없는 것은 그리지 않았다: %s." % (kname, " · ".join(gone)),
             ("    아랫면 선은 BRD-08의 %d가닥 가운데 %d가닥만 넣는다 (빠진 번호 %s)." % (len(rows), len(urows), _ranges([w["no"] for w in unused])))
             if unused else "    아랫면 선은 BRD-08의 %d가닥을 모두 넣는다." % len(rows),
             "4. GND 선(검정)이 지나는 J302·R30x 구멍은 부품이 없어도 선의 이음 자리로 납땜한다.",
             "5. 빗금 띠 = 밸런스 레일이 얹혀 기판을 눌러 잡는 자리(부품·납땜 없음).",
             "6. 자리 좌표·높이 한계 = BRD-01, 선 꺾인 점·길이 = BRD-08 · wiring_MB.csv, 7장 비교 = 01 회로도 탭."]
    s.para(238, 187, notes, size=1.95, lh=2.7)
    s.regions["front"] = (11.0, 25.0, 210.0, 180.5)
    s.regions["back"] = (211.0, 25.0, 409.0, 180.5)

    # ================================================================== click data
    def R2(a):
        return round(a, 2)

    def box(X, pts, padv=1.3, up=0.0, down=0.0, right=0.0):
        xs, ys = [X(p[0]) for p in pts], [Y(p[1]) for p in pts]
        return [R2(min(xs) - padv), R2(min(ys) - padv - up), R2(max(xs) + padv + right), R2(max(ys) + padv + down)]

    def rect(X, a0, a1, b0, b1):
        xs, ys = sorted((X(a0), X(a1))), sorted((Y(b0), Y(b1)))
        return [R2(xs[0]), R2(ys[0]), R2(xs[1]), R2(ys[1])]
    hparts, pnote = [], {}
    for X, front in ((XF, True), (XB, False)):
        hparts.append(["A301"] + rect(X, zx0, zx0 + 18, zy0 - 23.5, zy0))
        hparts.append(["A302"] + rect(X, mx0, mx0 + S.MUX_W, my0, my0 + S.MUX_D))
        hparts.append(["J301"] + box(X, [S.mb_pad_xy("J301", n) for n in range(1, 17)]))
        if j302_on:
            hparts.append(["J302"] + box(X, [S.mb_pad_xy("J302", n) for n in j302_on], up=0.0 if front else 2.0))
        hparts.append(["C301"] + box(X, [g_, v_], padv=0.9))
        hparts.append(["W101~W107"] + (rect(X, rb0, rb1, y0 - 4.1, S.MB["ribbon"][2]) if front else rect(X, rx0, rx1, y0, ry1)))
        for ref, (x, y) in S.R_EXT.items():
            if ref in v["r"]:
                hparts.append([ref] + box(X, [(x, y), (x + 7.62, y)], padv=1.25))
        for ref, (sig, gnd) in S.JP_PADS.items():
            if ref in closed:
                hparts.append([ref] + box(X, [sig, gnd], padv=1.25))
        for ref, (x, y) in S.TP_POS.items():
            hparts.append([ref] + box(X, [(x, y)], padv=1.25))
    for ref in v["r"]:
        pnote[ref] = ["이 기판(%s)에 답니다: 윗면에 붙여 눕히고 리드를 짧게, 아랫면에서 납땜한 뒤 다리 끝을 1 mm 이하로 자릅니다." % kname,
                      "하는 일: 끝 부속 선이 빠졌을 때 EXT%d 입력을 0 V로 당겨 유령 음을 막습니다." % (int(ref[1:]) - 300)]
    for ref in sorted(closed):
        pnote[ref] = ["이 기판(%s): 연결하세요 — 아랫면에서 두 구멍을 납으로 이어 붙입니다(납땜 브리지)." % kname]
    if h:
        pnote["J302"] = ["이 기판(%s): %s번 패드에 %s %d가닥을 윗면에서 납땜합니다 → 끝 부속 %s (%s 건반)." % (
            kname, "·".join(str(n) for n in sorted(v["ext"])), v["lead"], len(v["ext"]), v["end"], v["end_keys"])]
    elif j302_on:
        pnote["J302"] = ["이 기판(%s)에는 끝 부속이 없어 EXT 선을 달지 않습니다. %s번 구멍만 GND 선의 이음 자리로 납땜합니다." % (
            kname, "·".join(map(str, j302_on)))]
    padnote = {}
    hpads = []
    for (k, m), (ref, num, net) in r.pads.items():
        st = state[(ref, num)]
        key_ = "%s.%s" % (ref, num)
        ws = ends.get(key_, [])
        if st != "sol":
            continue                        # not on this board: no pad, no click target
        if ref.startswith("R30") and ref not in v["r"]:
            padnote[key_] = ["이 기판(%s)에는 저항이 없습니다. GND 선 %s번이 만나는 이음 자리로만 납땜합니다." % (
                kname, ", ".join(str(w["no"]) for w in ws if wire_used(v, w)))]
        elif ref == "J302" and int(num) not in v["ext"]:
            padnote[key_] = ["이 기판(%s)에는 EXT 선이 없습니다. GND 선 %s번이 만나는 이음 자리로만 납땜합니다." % (
                kname, ", ".join(str(w["no"]) for w in ws if wire_used(v, w)))]
        elif ref == "J302":
            padnote[key_] = ["윗면에서 %s 가닥을 납땜합니다 (그림 왼쪽)." % v["lead"]]
        for X in (XF, XB):
            hpads.append([ref, str(num), net, R2(X(MR.X(k))), R2(Y(MR.Y(m))), 1])
    wnote = {}
    sy0, sy1 = S.MB["strip"]
    rail = dict(t="밸런스 레일이 얹히는 띠 (빗금)", d=[
        "부품이 아니라 '여기에는 부품·납땜을 두지 않는다'는 표시입니다 (y%.1f~%.1f)." % (sy0, sy1),
        "제어 기판은 구멍도 나사도 없이 모듈 바닥에 놓이고, 따로 출력한 밸런스 레일이 이 띠를 위에서 눌러 잡습니다.",
        "이 띠에 부품이나 납땜 돌기가 있으면 레일이 뜨거나 기판이 눌려 휩니다.",
        "아랫면에서는 이 띠 밑에 받침 리브가 있어, 앞↔뒤 선은 리브 틈 x%.1f~%.1f으로만 지납니다." % S.MB["gap"]])
    extra = list(lead_items)
    extra.append(dict(k="r", g=rect(XF, x0, x1, sy0, sy1), **rail))
    for (a0, a1, b0, b1) in S.MB["ribs"][5:]:
        extra.append(dict(k="r", g=rect(XB, a0, a1, b0, b1), **rail))
    s.hits_custom = {
        "wires": [dict(no=w["no"], net=w["net"], a=w["a"], b=w["b"], len=round(w["length"], 1), bends=w["bends"],
                       pts=[[R2(XB(x)), R2(Y(y))] for x, y in w["pts"]]) for w in urows],
        "pads": hpads, "parts": hparts, "wnote": wnote, "padnote": padnote, "pnote": pnote, "extra": extra,
    }
    s.frame()
    s.expected = {}
    return s


def brd09():
    return _sheet("O1")


def brd10():
    return _sheet("O2")


def brd11():
    return _sheet("O3")


def brd12():
    return _sheet("O4")


def brd13():
    return _sheet("O5")


def brd14():
    return _sheet("O6")


def brd15():
    return _sheet("O7")
