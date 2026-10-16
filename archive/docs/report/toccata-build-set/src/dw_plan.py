"""Plan views: shared octave key layout, per-method frame plans, full keyboard and case layout."""
import math
from draw import View, fmt_mm, ord_y, ord_z
from drawings_common import hatch, hrect, hpoly, front_rail_end, black_pad_half
from model import L, KEYS, TAILS, METHODS

OCT = 7 * L["Pw"]
JOINT = 0.5                      # joint between neighbouring octave modules (module width = OCT - JOINT)


def white_outline(k, y_end):
    h0, h1 = k["head"]
    b0, b1 = k["body"]
    hd = L["head"]
    pts = [(h0, 0), (h1, 0), (h1, hd)]
    if b1 < h1 - 0.01:
        pts.append((b1, hd))
    pts.append((b1, y_end))
    pts.append((b0, y_end))
    if b0 > h0 + 0.01:
        pts.append((b0, hd))
    pts.append((h0, hd))
    return pts


def black_rect(k):
    b0, b1 = k["body"]
    return (b0, L["head"], b1 - b0, L["black_end"] - L["head"])


def black_top(k):
    """flat top face of a black key (inside the side chamfers): (x, y, w, h)."""
    x, y, w, h = black_rect(k)
    ins = (L["Bw"] - L["Bt"]) / 2
    return (x + ins, y + L["black_chamfer"], L["Bt"], h - L["black_chamfer"])


def _dim_h_side(v, u1, u2, y, text, ext_y, size_px=9.5):
    """horizontal dimension u1..u2 at y with extension lines from the feature edge ext_y and the label
    beside the right end (dimension line carried on to it), like View.dim_h's outside label."""
    g = v.px(2.5)
    s = 1 if y > ext_y else -1
    for uu in (u1, u2):
        v.line(uu, ext_y + s * g, uu, y + s * g * 1.4, cls="ex")
    v.line(u1, y, u2 + v.px(12), y, cls="dm")
    v._arrow(u1, y, math.pi)
    v._arrow(u2, y, 0)
    v.text(u2 + v.px(14), y + v.px(3.2), text, cls="dt", anchor="start", size_px=size_px)


# ----------------------------------------------------------------- 1. octave layout (shared)
def octave_layout_plan():
    yv = 172
    v = View(-26, -44, OCT + 58, yv + 30, px_width=1080)
    for k in KEYS:
        if not k["black"]:
            v.poly(white_outline(k, yv), cls="kw")
    for k in KEYS:
        if k["black"]:
            x, y, w, h = black_rect(k)
            v.rect(x, y, w, h, cls="kb")
            v.rect(*black_top(k), cls="kbt")
            # low tail behind the raised body (runs on under the name board): same width as the body
            v.rect(x, L["black_end"], w, yv - L["black_end"], cls="kph")
    # break line at the back
    v.line(-4, yv, OCT + 4, yv, cls="cl")
    v.text(OCT / 2, yv + v.px(8), "↑ 이 뒤 건반 길이·피벗은 방식별 도면", cls="tx-s", size_px=10)
    xr = OCT + 12                     # right-hand y dimension columns: xr, xr + 14, xr + 28
    # sensor row (carried on to its y dimension at xr + 14)
    v.line(-8, L["y_sensor"], xr + 14 + 3, L["y_sensor"], cls="cl")
    for k in KEYS:
        cx = k["cx"]
        v.rect(cx - 2.0, L["y_sensor"] - 1.5, 4.0, 3.0, cls="sens")
    v.text(-9, L["y_sensor"] + v.px(4), "홀센서 열", cls="tx", anchor="end", size_px=10.5)
    # fall line (carried on to its y dimension at xr + 28)
    v.line(-8, L["fall"], xr + 28 + 3, L["fall"], cls="ph2")
    v.text(-9, L["fall"] + v.px(4), "명판 앞면", cls="tx-s", anchor="end", size_px=10)
    # key names
    for k in KEYS:
        if k["black"]:
            v.text(k["cx"], 128, k["name"], cls="tx-w", size_px=11)
        else:
            v.text(sum(k["head"]) / 2, 22, k["name"], cls="tx", size_px=13)
    # front: white pitch chain + overall
    for i in range(7):
        v.dim_h(i * L["Pw"], (i + 1) * L["Pw"], -9, text=f"{L['Pw']:.1f}", ext_from=(0, 0))
    v.dim_h(0, OCT, -23, text=f"옥타브 {fmt_mm(OCT)}", ext_from=(0, 0))
    # head width + gap on C
    c = KEYS[0]
    g0, g1 = c["head"][1], KEYS[2]["head"][0]          # C | D head gap
    v.dim_h(c["head"][0], c["head"][1], 34, text=fmt_mm(c["head"][1] - c["head"][0]), ext_from=(30, 30))
    v.dim_h(g0, g1, 42, text=f"틈 {g1 - g0:.1f}")
    # tail / slot chain at y=160
    for k in KEYS:
        s0, s1 = k["slot"]
        v.dim_h(s0, s1, 160, text=fmt_mm(s1 - s0, 2), size_px=9.5)
    v.text(OCT + 3, 160 + v.px(12), "슬롯 폭(틈 포함)", cls="tx-s", anchor="start", size_px=9.5)
    # black key top face + width, dimensioned on D# in the light white-head area in front of it
    # (narrower top face nearest the key; labels beside the dimension, clear of the D|E head gap lines)
    bk = KEYS[3]
    tx, ty, tw, _ = black_top(bk)
    _dim_h_side(v, tx, tx + tw, L["head"] - v.px(22), f"윗면 {fmt_mm(tw)}", ty)
    bx, by, bw, bh = black_rect(bk)
    _dim_h_side(v, bx, bx + bw, L["head"] - v.px(40), fmt_mm(bw), by)
    # y dims on the right, with extension lines from the rightmost white front (B) and black edges (A#);
    # the sensor-row and fall lines above run on to their dims (an end on its own column gets no ext line)
    xw = KEYS[-1]["head"][1]
    xb = KEYS[-2]["body"][1]
    v.dim_v(0, L["head"], xr, text=fmt_mm(L["head"]), ext_from=(xw, xb))
    v.dim_v(L["head"], L["black_end"], xr, text=fmt_mm(L["black_end"] - L["head"]), ext_from=(xb, xb))
    v.dim_v(0, L["y_sensor"], xr + 14, text=fmt_mm(L["y_sensor"]), ext_from=(xw, xr + 14))
    v.dim_v(0, L["fall"], xr + 28, text=fmt_mm(L["fall"]), ext_from=(xw, xr + 28))
    v.dim_v(L["black_end"], L["fall"], xr, text=fmt_mm(L["fall"] - L["black_end"]), ext_from=(xb, xr))
    return v.svg(aria="1옥타브 건반 배열 평면도")


# ----------------------------------------------------------------- 2. frame plan per method
def frame_plan(M):
    """top view, y horizontal (front at left), x downward (C at top)."""
    ymax = M["depth"] + 14
    v = View(-26, -OCT - 12, ymax + 84, 16, px_width=1180)
    X = lambda x: -x
    P = dict(print=hatch(v, "print", 5, 45), wood=hatch(v, "wood", 7, 45))
    # keybed
    v.rect(-2, X(OCT + 4), ymax + 2, OCT + 8, cls="m-wood")
    def rr(y0, y1, x0, x1, cls="m-print"):
        v.rect(y0, X(x1), y1 - y0, x1 - x0, cls=cls)
    m0, m1 = JOINT / 2, OCT - JOINT / 2   # printed module edges (half a joint in from the octave pitch)
    sh0 = (OCT - L["shaft_len"]) / 2      # B/D pivot shaft (cut length L.shaft_len) centred in the module
    assert sh0 > m0, "pivot shaft longer than the printed module"
    # front rail
    rail_y0 = 6
    rail_end = front_rail_end(M)
    rr(rail_y0, rail_end, m0, m1)
    rr(8, 28, m0, m1, "m-felt")
    hl = black_pad_half(M)              # black down-stop pad stays on the front rail
    for k in KEYS:
        if k["black"]:
            rr(M["stop_b_y"] - hl, M["stop_b_y"] + hl, k["cx"] - 5, k["cx"] + 5, "m-felt")
            v.circle(M["guide_b_y"], X(k["cx"]), 1.5, cls="m-steel")
        else:
            v.circle(M["guide_w_y"], X(k["hcx"]), 1.5, cls="m-steel")
    # sensor rail
    sy0, sy1 = M.get("srail", (98, 126))
    rr(sy0, sy1, m0, m1)
    rr(*L["wire_ch"], m0, m1, "zone")                       # wire channel under the sensor rail
    for k in KEYS:
        v.rect(L["y_sensor"] - L["pocket_h"], X(k["cx"] + 2.2), 2 * L["pocket_h"], 4.4, cls="sens")
    # screws (M4 wood) for rails: on slot boundaries C#|D, F|F#, A|A# (clear of springs and sensors)
    XS = [KEYS[i]["slot"][1] for i in (1, 5, 9)]
    def screws(yc):
        for xs in XS:
            v.circle(yc, X(xs), 2.2, cls="void")
    screws(46 if M["id"] != "D" else 36)
    # sensor rail: in the flat strip between the rail front and the sensor recess (not in the wire channel)
    screws((sy0 + L["y_sensor"] - L["pocket_h"]) / 2)
    mid = M["id"]
    if mid in ("A", "B"):
        ys = M["spring_y"]
        rr(ys - 7, ys + 7, m0, m1)
        for k in KEYS:
            v.circle(ys, X(k["cx"]), 3.0, cls="spk")
            v.circle(ys, X(k["cx"]), 1.5, cls="void")
        screws(ys)
    if mid == "A":
        s0, s1 = M["spine"]
        rr(*M["blk"], m0, m1)                   # printed spine support block: starts at the spine (leaf stays free)
        rr(s0, s1, m0, m1, "kph")
        for k in KEYS:                          # flexing leaves (full tail width) from the key body to the spine
            b0, b1 = k["body"]
            v.rect(M["body_end"], X(b1), M["leaf"], b1 - b0, cls="kph")
        for xs in XS:
            v.circle((s0 + s1) / 2, X(xs), 1.7, cls="m-steel")
    if mid in ("B", "D"):
        c0, c1 = M["comb"]
        rr(c0 - 6, c1 + 6, m0, m1)
        for k in KEYS + [None]:
            xb = k["slot"][0] if k else OCT
            t = 1.5 if (k is None or k is KEYS[0]) else 3.0
            xa = xb - (0 if k is KEYS[0] else (t if k is None else t / 2))
            rr(c0, c1, max(xa, m0), min(xa + t, m1), "m-print2")
        v.line(M["pivot"][0], X(sh0), M["pivot"][0], X(OCT - sh0), cls="shaft")
        screws(c1 + 3)
    if mid == "C":
        py = M["pivot"][0]
        rr(py - 12, py + 12, m0, m1)
        for k in KEYS:
            v.circle(py, X(k["cx"]), M["punch_d"] / 2, cls="m-felt")       # balance-rail felt punching
            v.circle(py, X(k["cx"]), M["bal_pin"]["d"] / 2, cls="m-steel")
        c = M["cw_c"]
        rr(c - 10, c + 10, m0, m1)
        rr(c - 10, c + 10, m0, m1, "m-felt")
        screws(py - 8)
    if mid == "D":
        h0, h1 = M["h_comb"]
        rr(h0, h1, m0, m1)
        for k in KEYS + [None]:
            xb = k["slot"][0] if k else OCT
            rr(h0, h1, max(xb - 1.5, m0), min(xb + 1.5, m1), "m-print2")
        v.line(M["h_pivot"][0], X(sh0), M["h_pivot"][0], X(OCT - sh0), cls="shaft")
        rr(66, 76, m0, m1, "m-felt")
        r0, r1 = M["h_rest"]
        if M["h_rest_pad"] > 0:
            rr(r0, r1, m0, m1)
        rr(r0, r1, m0, m1, "m-felt")
        hb = M["h_comb"][1]                     # beam narrows behind the hammer comb (enters the key when pressed)
        for k in KEYS:
            # beam slot - 3.4 wide up to the hammer comb's rear end, then M.h_rear_w up to the cradle;
            # the cradle that rises into the key is M.h_cradle_w wide
            hw0, hw1 = k["slot"][0] + 1.7, k["slot"][1] - 1.7
            c0, c1 = M["h_cradle_b"] if k["black"] else M["h_cradle"]
            assert M["h_front"] < hb < c0, "hammer comb not between the beam front and the cradle"
            v.rect(M["h_front"], X(hw1), hb - M["h_front"], hw1 - hw0, cls="kph")
            rw = M["h_rear_w"]
            v.rect(hb, X(k["cx"] + rw / 2), c0 - hb, rw, cls="kph")
            cw = M["h_cradle_w"]
            v.rect(c0, X(k["cx"] + cw / 2), c1 - c0, cw, cls="kph")
    # keys phantom; B/D: behind M.eyelet_y the key narrows to the eyelet between the comb fins
    # (slot - fin_t - 2 x eye_cl, centred on the slot) - same width as the key part drawing
    e0 = M.get("eyelet_y")
    y_end = e0 if e0 is not None else M["body_end"]
    for k in KEYS:
        if k["black"]:
            b0, b1 = k["body"]
            v.rect(L["head"], X(b1), y_end - L["head"], b1 - b0, cls="kph")
        else:
            pts = [(y, X(x)) for (x, y) in white_outline(k, y_end)]
            v.poly(pts, cls="kph")
        if e0 is not None:
            ew = (k["slot"][1] - k["slot"][0]) - (M.get("fin_t", L["fin_t"]) + 2 * L["eye_cl"])
            v.rect(e0, X(k["cx"] + ew / 2), M["body_end"] - e0, ew, cls="kph")
    # x ordinates (slot centres) on the right
    feats = [(-k["cx"], ymax, f'{k["name"]}  x {fmt_mm(k["cx"], 2)}'
              + ('' if k["black"] or abs(k["hcx"] - k["cx"]) < 0.01 else f' · 가이드 핀 x {fmt_mm(k["hcx"], 2)}'))
             for k in KEYS]
    feats += [(-m0, ymax, f"모듈 끝  x {fmt_mm(m0, 2)} (x 0 = 옥타브 경계)"), (-m1, ymax, f"모듈 끝  x {fmt_mm(m1, 2)}")]
    ord_z(v, feats, ymax + 6, gap_px=12, label_px=9.5, prefix=None)
    # printed module width (from the rail ends); the octave pitch is stated in the sheet caption
    v.dim_v(X(m0), X(m1), -14, text=f"모듈 폭 {fmt_mm(m1 - m0)}", ext_from=(rail_y0, rail_y0))
    return v.svg(aria=f"방식 {M['id']} 프레임 평면도")


# ----------------------------------------------------------------- 3. full keyboard & modules
N_WHITE = 52
FULL_W = N_WHITE * L["Pw"]
X_C0 = -5 * L["Pw"]             # C0 starts 5 whites left of A0 (A0 = 6th white of octave 0)


def full_keys():
    """all 88 keys A0..C8 as (key, x_base, name). The end keys A0 and C8 have no black neighbour
    on their outer side (G#0 / C#8 do not exist), so their tail is widened to the head edge there."""
    keys = []
    for i in range(88):
        midi = 21 + i
        octv = midi // 12 - 1
        k = KEYS[midi % 12]
        keys.append((k, X_C0 + octv * OCT, f"{k['name']}{octv}"))
    (ka, ba, na), (kc, bc, nc) = keys[0], keys[-1]
    keys[0] = (dict(ka, body=(ka["head"][0], ka["body"][1])), ba, na)       # A0: widen to the left
    keys[-1] = (dict(kc, body=(kc["body"][0], kc["head"][1])), bc, nc)      # C8: widen to the right
    return keys


def end_tail_w():
    """printed tail width of the end keys: {'A0': w, 'C8': w}."""
    ks = full_keys()
    return {ks[0][2]: ks[0][0]["body"][1] - ks[0][0]["body"][0],
            ks[-1][2]: ks[-1][0]["body"][1] - ks[-1][0]["body"][0]}


def full_keyboard():
    v = View(-10, -70, FULL_W + 10, 190, px_width=1180)
    keys = full_keys()
    x_c = X_C0
    yv = 150
    for k, base, nm in keys:
        if not k["black"]:
            v.poly([(x + base, y) for (x, y) in white_outline(k, yv)], cls="kw")
    for k, base, nm in keys:
        if k["black"]:
            x, y, w, h = black_rect(k)
            v.rect(x + base, y, w, h, cls="kb")
    # modules
    mods = [("O1", "A0–B1", 21, 35), ("O2", "C2–B2", 36, 47), ("O3", "C3–B3", 48, 59), ("O4", "C4–B4", 60, 71),
            ("O5", "C5–B5", 72, 83), ("O6", "C6–B6", 84, 95), ("O7", "C7–C8", 96, 108)]
    def x_of(midi, edge="l"):
        k, base, nm = keys[midi - 21]
        if k["black"]:
            s = k["slot"]
        else:
            s = k["slot"] if False else k["head"]
        return base + (k["head"][0] - 0.5 if not k["black"] else k["slot"][0]) if edge == "l" else \
            base + (k["head"][1] + 0.5 if not k["black"] else k["slot"][1])
    for i, (mid, rng, lo, hi) in enumerate(mods):
        x0 = max(0, x_of(lo, "l"))
        x1 = min(FULL_W, x_of(hi, "r"))
        yb = 162 if i % 2 == 0 else 176
        fs = 10.5
        hh = max(5.0, v.px(fs * 0.65))      # bar half height from the label font: text sits inside the bar
        v.rect(x0, yb - hh, x1 - x0, 2 * hh, cls="mod")
        v.text((x0 + x1) / 2, yb, f"{mid} · {rng} · {hi - lo + 1}키", cls="tx", size_px=fs, dy_px=fs * 0.36)
    # octave marks
    for o in range(1, 9):
        xo = x_c + o * OCT
        if 0 < xo < FULL_W:
            v.line(xo, -4, xo, yv + 4, cls="cl")
            v.text(xo + v.px(2), -14, f"C{o}", cls="tx-s", anchor="start", size_px=10)
    v.text(4, 20, "A0", cls="tx", anchor="start", size_px=11)
    v.text(FULL_W - 4, 20, "C8", cls="tx", anchor="end", size_px=11)
    v.dim_h(0, FULL_W, -34, text=f"88건반 전체 폭 {fmt_mm(FULL_W)}  (백건 {N_WHITE}개 × {L['Pw']:.1f})", ext_from=(0, 0))
    v.dim_h(0, 2 * L["Pw"], -52, text=f"{2 * L['Pw']:.1f}", ext_from=(0, 0))
    v.dim_h(FULL_W - L["Pw"], FULL_W, -52, text=f"{L['Pw']:.1f}", ext_from=(0, 0))
    v.line(-6, L["y_sensor"], FULL_W + 6, L["y_sensor"], cls="cl")
    return v.svg(aria="88건반 전체 배열과 모듈 분할")


# ----------------------------------------------------------------- 4. case & speaker layout
SAT_R, SUB_R = 100.0, 150.0      # D14 keep-out radius from the sensor row: satellite / sub (mm)


def case_geom(M):
    """plan geometry of the case (shared by the drawing and the report text)."""
    g = dict(cheek=25.0, sat_r=SAT_R, sub_r=SUB_R)
    g["W"] = FULL_W + 2 * g["cheek"] + 2
    g["x0"] = -g["cheek"] - 1
    g["rb0"] = M["depth"] + 14                  # front of the rear speaker bar
    g["bar_d"] = 150.0
    g["depth"] = g["rb0"] + g["bar_d"]          # rear outer edge (y); front outer edge at -22
    g["box_w"], g["spk_y"] = 300.0, g["rb0"] + 70
    # sub box: 18 mm walls around the inner volume, hung under the rear keybed / speaker bar, back at the rear edge
    wall = 18.0
    g["sub_in"] = (400.0, 250.0, 165.0)
    g["sub_w"], g["sub_d"] = g["sub_in"][0] + 2 * wall, g["sub_in"][1] + 2 * wall
    g["sub_y1"] = g["depth"]
    g["sub_y0"] = g["sub_y1"] - g["sub_d"]
    g["sub_c"] = (FULL_W / 2, (g["sub_y0"] + g["sub_y1"]) / 2)
    g["sub_unit_r"] = 106.0                     # RSS210HF-4 frame radius
    return g


def case_layout(M):
    """top view of the whole instrument: key area, sensor row, speaker keep-out circles (D14)."""
    g = case_geom(M)
    cheek, W, depth, x0, rb0 = g["cheek"], g["W"], g["depth"], g["x0"], g["rb0"]
    v = View(x0 - 20, -40, x0 + W + 170, depth + 30, px_width=1180)
    # outline
    v.rect(x0, -22, W, depth + 22, cls="m-wood")
    v.rect(0, 0, FULL_W, M["body_end"], cls="kph")
    v.rect(0, 0, FULL_W, L["fall"], cls="kw")
    v.line(0, L["y_sensor"], FULL_W, L["y_sensor"], cls="sensrow")
    # label below the row: the sub box front edge and its keep-out arc lie just behind it
    v.text(FULL_W / 2, L["y_sensor"] - v.px(14), f"홀센서 열 y = {fmt_mm(L['y_sensor'])}", cls="tx", size_px=11)
    # rear speaker bar
    v.rect(x0, rb0, W, g["bar_d"], cls="m-print")
    box_w, spk_y = g["box_w"], g["spk_y"]

    def centre_mark(cu, cv, r=8.0):
        v.line(cu - r, cv, cu + r, cv, cls="cl")
        v.line(cu, cv - r, cu, cv + r, cls="cl")
    for side in (0, 1):
        bx = x0 + 20 if side == 0 else x0 + W - 20 - box_w
        v.rect(bx, rb0 + 10, box_w, 130, cls="spkbox")
        cx = bx + box_w / 2
        v.circle(cx, spk_y, 52, cls="spk")
        v.circle(cx, spk_y, 49.2, cls="kph")
        v.circle(cx, spk_y, g["sat_r"], cls="zone")
        centre_mark(cx, spk_y)
        # label above the bar and above the keep-out circle
        v.text(cx, max(rb0 + g["bar_d"], spk_y + g["sat_r"]) + v.px(8), "위성 스피커 DMA105-4 · 밀폐 4.7 L",
               cls="tx", size_px=10.5)
        # sensor row -> unit centre, beside the keep-out circle (lower end on the sensor row line)
        xs = cx + g["sat_r"] + 10
        v.dim_v(L["y_sensor"], spk_y, xs, text=f"y거리 {fmt_mm(spk_y - L['y_sensor'])}", ext_from=(xs, cx))
    # sub (under the rear keybed and the speaker bar, drawn dashed)
    sub_c, sub_w, sub_d, sub_y0 = g["sub_c"], g["sub_w"], g["sub_d"], g["sub_y0"]
    v.rect(sub_c[0] - sub_w / 2, sub_y0, sub_w, sub_d, cls="kph")
    v.circle(sub_c[0], sub_c[1], g["sub_unit_r"], cls="kph")
    v.circle(sub_c[0], sub_c[1], g["sub_r"], cls="zone")
    centre_mark(*sub_c)
    si = g["sub_in"]
    vol = si[0] * si[1] * si[2] / 1e6
    # label in the empty white-key area in front of the sensor row, leader to the box's front strip
    # (clear of both sub circles)
    lx, ly = sub_c[0] - sub_w / 2 + 12, L["y_sensor"] - v.px(32)
    v.leader(lx, sub_y0 + 4, lx + 18, ly,
             f"서브우퍼 상자 RSS210HF-4 · 내부 {fmt_mm(si[0])}×{fmt_mm(si[1])}×{fmt_mm(si[2])} ≈ {fmt_mm(vol)} L", size_px=10.5)
    v.text(lx + 18 + v.px(9), ly - v.px(16), "(키베드 뒤쪽·스피커 바 아래, 아래쪽 방사)", cls="lt", anchor="start",
           size_px=10.5, dy_px=4)
    xd = sub_c[0] + sub_w / 2 - v.px(14)
    v.dim_v(L["y_sensor"], sub_c[1], xd, text=f"y거리 {fmt_mm(sub_c[1] - L['y_sensor'])}", ext_from=(xd, sub_c[0]))
    # electronics bay
    v.rect(FULL_W / 2 - 230, rb0 + 20, 150, 110, cls="elec")
    v.text(FULL_W / 2 - 155, rb0 + 75, "Pi 5 + 앰프 HAT", cls="tx", size_px=10)
    v.rect(FULL_W / 2 + 80, rb0 + 20, 150, 110, cls="elec")
    v.text(FULL_W / 2 + 155, rb0 + 75, "USB 허브 · 전원", cls="tx", size_px=10)
    v.dim_h(x0, x0 + W, -34, text=f"외곽 폭 {fmt_mm(W)}", ext_from=(-22, -22), above=False)
    v.dim_v(-22, depth, x0 + W + 30, text=f"외곽 깊이 {fmt_mm(depth + 22)}", ext_from=(x0 + W, x0 + W))
    v.text(x0 + W + 40, 60, "점선 원 = D14 이격 범위", cls="tx-s", anchor="start", size_px=10)
    v.text(x0 + W + 40, 60 - v.px(16), f"위성 {fmt_mm(g['sat_r'])} mm", cls="tx-s", anchor="start", size_px=10)
    v.text(x0 + W + 40, 60 - v.px(32), f"서브 {fmt_mm(g['sub_r'])} mm", cls="tx-s", anchor="start", size_px=10)
    return v.svg(aria="케이스·스피커 배치 평면도")


if __name__ == "__main__":
    css = open("dwg.css").read() + """
.dwg .tx-w{fill:#fff;font-family:system-ui}
.dwg .mod{fill:#dfe6ef;stroke:#1d2433;stroke-width:1px}
.dwg .shaft{stroke:#5d6778;stroke-width:2.5px}
.dwg .sensrow{stroke:#c2410c;stroke-width:1.4px;stroke-dasharray:8 4}
.dwg .spkbox{fill:#e6ecf4;stroke:#1d2433;stroke-width:1px}
.dwg .elec{fill:#e3f0e6;stroke:#1d2433;stroke-width:1px}
"""
    html = f"<html><head><meta charset='utf-8'><style>{css} body{{background:#fff}}</style></head><body>"
    import sys
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w in ("all", "oct"): html += f"<div class='dw'>{octave_layout_plan()}</div>"
    if w in ("all", "full"): html += f"<div class='dw'>{full_keyboard()}</div>"
    if w in ("all", "frame"):
        for M in METHODS:
            html += f"<h3>{M['id']}</h3><div class='dw'>{frame_plan(M)}</div>"
    if w in ("all", "case", "full"): html += f"<div class='dw'>{case_layout(METHODS[1])}</div>"
    open("test.html", "w").write(html + "</body></html>")
