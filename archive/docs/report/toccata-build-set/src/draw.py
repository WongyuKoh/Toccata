"""Tiny engineering-drawing kit that emits inline SVG in mm units.

World coords are mm. A View maps world (u, v) -> SVG (x, y) with v pointing up.
All strokes/text are sized in *screen px* and converted to mm via the view scale,
so every drawing reads the same regardless of its physical size.
"""
import math

def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")

def fmt_mm(v, nd=1):
    s = f"{v:.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


class View:
    def __init__(self, u0, v0, u1, v1, px_width=960, title=None, flip_v=True, pad_px=18):
        self.u0, self.v0, self.u1, self.v1 = u0, v0, u1, v1
        self.s = px_width / (u1 - u0)          # px per mm
        self.flip = flip_v
        self.el = []
        self.defs = []
        self.title = title
        self.pad = pad_px / self.s
        self.segs = []          # straight strokes drawn so far (world coords), for label placement
        self._late = []         # (index in el, fn) resolved in svg(), after everything else is drawn

    # ---- unit helpers
    def px(self, p):
        return p / self.s

    def X(self, u):
        return u

    def Y(self, v):
        return -v if self.flip else v

    def P(self, u, v):
        return f"{f(self.X(u))},{f(self.Y(v))}"

    # ---- primitives
    def line(self, u1, v1, u2, v2, cls="ln"):
        self.segs.append((u1, v1, u2, v2))
        self.el.append(f'<line class="{cls}" x1="{f(u1)}" y1="{f(self.Y(v1))}" x2="{f(u2)}" y2="{f(self.Y(v2))}"/>')

    def poly(self, pts, cls="ln", closed=True):
        tag = "polygon" if closed else "polyline"
        pts = list(pts)
        ring = pts + pts[:1] if closed else pts
        self.segs += [(a[0], a[1], b[0], b[1]) for a, b in zip(ring, ring[1:])]
        self.el.append(f'<{tag} class="{cls}" points="{" ".join(self.P(u, v) for u, v in pts)}"/>')

    def rect(self, u, v, w, h, cls="ln", rx=0):
        # (u, v) = lower-left in world
        y = self.Y(v + h) if self.flip else v
        self.segs += [(u, v, u + w, v), (u + w, v, u + w, v + h), (u + w, v + h, u, v + h), (u, v + h, u, v)]
        r = f' rx="{f(rx)}"' if rx else ""
        self.el.append(f'<rect class="{cls}" x="{f(u)}" y="{f(y)}" width="{f(w)}" height="{f(h)}"{r}/>')

    def circle(self, u, v, r, cls="ln"):
        self.el.append(f'<circle class="{cls}" cx="{f(u)}" cy="{f(self.Y(v))}" r="{f(r)}"/>')

    def path(self, d, cls="ln"):
        self.el.append(f'<path class="{cls}" d="{d}"/>')

    def _text_el(self, u, v, s, cls="tx", anchor="middle", size_px=11, rot=0, dy_px=0):
        fs = self.px(size_px)
        x, y = u, self.Y(v) + self.px(dy_px)
        tr = f' transform="rotate({f(rot)} {f(x)} {f(y)})"' if rot else ""
        s = str(s).replace("&", "&amp;").replace("<", "&lt;")
        return f'<text class="{cls}" x="{f(x)}" y="{f(y)}" font-size="{f(fs)}" text-anchor="{anchor}"{tr}>{s}</text>'

    def text(self, u, v, s, cls="tx", anchor="middle", size_px=11, rot=0, dy_px=0):
        self.el.append(self._text_el(u, v, s, cls, anchor, size_px, rot, dy_px))

    # ---- labels placed after the whole view is drawn
    def late(self, fn):
        """reserve a slot at the current drawing order; fn(view) -> svg string is called in svg(),
        when every later stroke (leaders, dimensions ...) is known."""
        self._late.append((len(self.el), fn))
        self.el.append("")

    def _hits(self, box):
        """number of recorded strokes crossing the box (u_lo, u_hi, v_lo, v_hi) — Liang–Barsky clip."""
        u_lo, u_hi, v_lo, v_hi = box
        n = 0
        for u1, v1, u2, v2 in self.segs:
            t0, t1, du, dv = 0.0, 1.0, u2 - u1, v2 - v1
            ok = True
            for p, q in ((-du, u1 - u_lo), (du, u_hi - u1), (-dv, v1 - v_lo), (dv, v_hi - v1)):
                if abs(p) < 1e-12:
                    if q < 0:
                        ok = False
                        break
                else:
                    r = q / p
                    if p < 0:
                        t0 = max(t0, r)
                    else:
                        t1 = min(t1, r)
                    if t0 > t1:
                        ok = False
                        break
            n += ok
        return n

    def text_free(self, u_lo, u_hi, v, s, size_px=11, prefer=None, pad_px=3):
        """centre u in [u_lo, u_hi] for a horizontal, middle-anchored label with baseline v whose box
        crosses the fewest strokes (then the one closest to `prefer`, default the middle of the range)."""
        w, fs, pad = self.text_w(s, size_px), self.px(size_px), self.px(pad_px)
        prefer = (u_lo + u_hi) / 2 if prefer is None else prefer
        a, b = u_lo + w / 2, u_hi - w / 2
        if b <= a:
            return prefer
        n = max(1, int((b - a) / self.px(1)))
        best = None
        for i in range(n + 1):
            u = a + (b - a) * i / n
            key = (self._hits((u - w / 2 - pad, u + w / 2 + pad, v - 0.25 * fs, v + 0.85 * fs)), abs(u - prefer))
            if best is None or key < best[0]:
                best = (key, u)
        return best[1]

    # ---- text extent helpers (world mm; CJK glyph ~1 em, others ~0.6 em)
    def text_w(self, s, size_px):
        return self.px(sum(size_px * (1.0 if ord(c) > 0x2E80 else 0.6) for c in str(s)))

    def _box(self):
        """viewBox extent in world coords (u_lo, u_hi, v_lo, v_hi)."""
        p = self.pad
        return self.u0 - p, self.u1 + p, self.v0 - p, self.v1 + p

    # ---- drafting helpers
    def _arrow(self, u, v, ang):
        """filled arrowhead with tip at (u, v) pointing along ang (radians, world)."""
        L, W = self.px(7), self.px(2.4)
        ca, sa = math.cos(ang), math.sin(ang)
        bu, bv = u - L * ca, v - L * sa
        p1 = (bu + W * -sa, bv + W * ca)
        p2 = (bu - W * -sa, bv - W * ca)
        self.poly([(u, v), p1, p2], cls="ah")

    def dim_h(self, u1, u2, v, text=None, ext_from=None, cls="dm", above=True, size_px=10.5, nd=1):
        """horizontal dimension between u1,u2 drawn at height v.
        ext_from: (v_a, v_b) feature heights for extension lines (defaults to v)."""
        if text is None:
            text = fmt_mm(abs(u2 - u1), nd)
        g = self.px(2.5)
        if ext_from:
            for uu, vv in ((u1, ext_from[0]), (u2, ext_from[1])):
                if abs(v - vv) < g:          # dimension line already on the feature: no extension line
                    continue
                s = 1 if v > vv else -1
                self.line(uu, vv + s * g, uu, v + s * g * 1.4, cls="ex")
        self.line(u1, v, u2, v, cls=cls)
        a, b = (u1, u2) if u1 < u2 else (u2, u1)
        span_px = (b - a) * self.s
        if span_px > 26:
            self._arrow(a, v, math.pi)
            self._arrow(b, v, 0)
        else:  # outside arrows
            self._arrow(a, v, 0)
            self._arrow(b, v, math.pi)
            self.line(a - self.px(12), v, a, v, cls=cls)
            self.line(b, v, b + self.px(12), v, cls=cls)
        tv = v + (self.px(3.2) if above else -self.px(11))
        tu = (a + b) / 2
        if span_px < 34 and len(str(text)) > 3:
            # outside label: right of the dimension, or left when it would leave the viewBox
            tw = self.text_w(text, size_px)
            if b + self.px(14) + tw <= self._box()[1]:
                self.text(b + self.px(14), tv, text, cls="dt", anchor="start", size_px=size_px)
            else:
                self.text(a - self.px(14), tv, text, cls="dt", anchor="end", size_px=size_px)
        else:
            self.text(tu, tv, text, cls="dt", size_px=size_px)

    def dim_v(self, v1, v2, u, text=None, ext_from=None, cls="dm", left=True, size_px=10.5, nd=1):
        if text is None:
            text = fmt_mm(abs(v2 - v1), nd)
        g = self.px(2.5)
        if ext_from:
            for vv, uu in ((v1, ext_from[0]), (v2, ext_from[1])):
                if abs(u - uu) < g:          # dimension line already on the feature: no extension line
                    continue
                s = 1 if u > uu else -1
                self.line(uu + s * g, vv, u + s * g * 1.4, vv, cls="ex")
        self.line(u, v1, u, v2, cls=cls)
        a, b = (v1, v2) if v1 < v2 else (v2, v1)
        span_px = (b - a) * self.s
        if span_px > 26:
            self._arrow(u, a, -math.pi / 2)
            self._arrow(u, b, math.pi / 2)
        else:
            self._arrow(u, a, math.pi / 2)
            self._arrow(u, b, -math.pi / 2)
            self.line(u, a - self.px(12), u, a, cls=cls)
            self.line(u, b, u, b + self.px(12), cls=cls)
        tv = (a + b) / 2
        if span_px < 34:
            # outside label above the dimension, or below it when it would leave the viewBox;
            # shifted sideways just enough to stay inside the viewBox
            fs = self.px(size_px)
            u_lo, u_hi, v_lo, v_hi = self._box()
            tv = b + self.px(16)
            if tv + 0.8 * fs > v_hi:
                tv = a - self.px(14) - 0.8 * fs
            hw = self.text_w(text, size_px) / 2
            tu = min(max(u, u_lo + hw), u_hi - hw)
            self.text(tu, tv, text, cls="dt", anchor="middle", size_px=size_px)
        else:
            du = -self.px(4) if left else self.px(4)
            self.text(u + du, tv, text, cls="dt", anchor="middle", size_px=size_px, rot=-90 if self.flip else 90)

    def leader(self, u, v, tu, tv, label, anchor="start", size_px=11, cls="ld"):
        self.circle(u, v, self.px(1.8), cls="dot")
        self.line(u, v, tu, tv, cls=cls)
        ext = self.px(6) if anchor == "start" else -self.px(6)
        self.line(tu, tv, tu + ext, tv, cls=cls)
        self.text(tu + ext + (self.px(3) if anchor == "start" else -self.px(3)), tv, label,
                  cls="lt", anchor=anchor, size_px=size_px, dy_px=4)

    def balloon(self, u, v, tu, tv, n):
        r = self.px(8.5)
        self.line(u, v, tu, tv, cls="ld")
        self.circle(u, v, self.px(1.8), cls="dot")
        self.circle(tu, tv, r, cls="bl")
        self.text(tu, tv, n, cls="bt", size_px=10.5, dy_px=3.8)

    def cl(self, u1, v1, u2, v2):
        self.line(u1, v1, u2, v2, cls="cl")

    def note(self, u, v, s, size_px=11, anchor="start", cls="nt"):
        self.text(u, v, s, cls=cls, anchor=anchor, size_px=size_px)

    def svg(self, cls="dwg", aria=""):
        for i, fn in self._late:
            self.el[i] = fn(self)
        p = self.pad
        x0 = self.u0 - p
        w = (self.u1 - self.u0) + 2 * p
        if self.flip:
            y0 = -self.v1 - p
        else:
            y0 = self.v0 - p
        h = (self.v1 - self.v0) + 2 * p
        wpx = w * self.s
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg class="{cls}" viewBox="{f(x0)} {f(y0)} {f(w)} {f(h)}" '
                f'style="--k:{f(1/self.s)};max-width:{int(wpx)}px" role="img" aria-label="{aria}" '
                f'xmlns="http://www.w3.org/2000/svg">{defs}{"".join(self.el)}</svg>')


# ---------------------------------------------------------------- ordinate dimensioning
def ord_y(v, feats, row, gap_px=13, label_px=10):
    """feats: [(y, z_feature, label)], vertical extension lines down to `row` (world z),
    labels rotated, de-overlapped to the right."""
    feats = sorted(feats, key=lambda t: t[0])
    gap = v.px(gap_px)
    pos, last = [], -1e9
    for y, zf, lab in feats:
        u = max(y, last + gap)
        pos.append(u)
        last = u
    # pull the whole run back if it drifted right of the last feature too far
    for (y, zf, lab), u in zip(feats, pos):
        v.line(y, zf - v.px(2), y, row, cls="ex")
        v.circle(y, row, v.px(1.6), cls="dot")
        jog = row - v.px(9)
        v.line(y, row, u, jog, cls="ex")
        v.text(u + v.px(3.5), jog - v.px(2), f"{fmt_mm(y, 1)}  {lab}", cls="ot", anchor="end", size_px=label_px, rot=-90)


def _pav(t):
    """least-squares non-decreasing fit of the sequence t (pool adjacent violators)."""
    blocks = []                      # [sum, count]
    for x in t:
        blocks.append([x, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s_, c_ = blocks.pop()
            blocks[-1][0] += s_
            blocks[-1][1] += c_
    out = []
    for s_, c_ in blocks:
        out += [s_ / c_] * c_
    return out


def ord_z(v, feats, col, gap_px=13, label_px=10, prefix="z "):
    """feats: [(z, y_feature, label)], horizontal extension lines to `col` (world y), labels to the right.

    Labels keep >= gap_px between them and sit as close to their own z as possible
    (centred least-squares placement, not pushed up only); the jog widens with the displacement.
    Features at the same z (within 0.05 mm) share one extension line (from the feature farthest from
    `col`) and one label ("a · b")."""
    feats = sorted(feats, key=lambda t: t[0])
    if not feats:
        return
    merged = []
    for z, yf, lab in feats:
        if merged and abs(z - merged[-1][0]) < 0.05:
            z0, y0, labs = merged[-1]
            merged[-1] = (z0, max((y0, yf), key=lambda y: abs(col - y)), labs + [lab] * (lab not in labs))
        else:
            merged.append((z, yf, [lab]))
    feats = [(z, yf, " · ".join(labs)) for z, yf, labs in merged]
    gap = v.px(gap_px)
    u = _pav([z - i * gap for i, (z, yf, lab) in enumerate(feats)])
    pos = [ui + i * gap for i, ui in enumerate(u)]
    run = max(v.px(9), 0.6 * max(abs(w - z) for w, (z, yf, lab) in zip(pos, feats)))
    for (z, yf, lab), w in zip(feats, pos):
        v.line(yf + v.px(2), z, col, z, cls="ex")
        v.circle(col, z, v.px(1.6), cls="dot")
        v.line(col, z, col + run, w, cls="ex")
        txt = f"{prefix}{fmt_mm(z, 1)}  {lab}" if prefix is not None else lab
        v.text(col + run + v.px(3), w, txt, cls="ot", anchor="start", size_px=label_px, dy_px=3.5)
