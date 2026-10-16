"""도면용 SVG 기본 도구. 월드 좌표(mm) → 화면(px). 치수선·지시선·폴리곤."""
import html
import math


def esc(s):
    return html.escape(str(s), quote=True)


DIM_STROKE = 0.8                 # .dim stroke-width (DRAW_CSS와 같게)
ARROW_MW = 7                     # 화살표 marker 크기(stroke 배수)
ARROW_PX = ARROW_MW * DIM_STROKE  # 화살촉 길이 5.6 px
ARROW_OUT_PX = 10                # 짧은 치수에서 바깥 화살표 꼬리 길이


def fmt(v):
    """치수 표기: 정수면 정수, 아니면 소수 1자리."""
    v = float(v)
    return f'{v:.0f}' if abs(v - round(v)) < 0.05 else f'{v:.1f}'


class SVG:
    """x→오른쪽, v→위(월드). 화면에서는 v를 뒤집는다."""

    def __init__(self, x0, v0, x1, v1, scale=3.0, pad=(70, 60, 70, 60)):
        self.x0, self.v0, self.x1, self.v1 = x0, v0, x1, v1
        self.s = scale
        self.pl, self.pt, self.pr, self.pb = pad  # left, top, right, bottom (px)
        self.w = (x1 - x0) * scale + self.pl + self.pr
        self.h = (v1 - v0) * scale + self.pt + self.pb
        self.items = []

    def P(self, x, v):
        return (self.pl + (x - self.x0) * self.s, self.pt + (self.v1 - v) * self.s)

    def add(self, s):
        self.items.append(s)

    def poly(self, pts, cls='part', closed=True, title=None):
        if not pts:
            return
        d = ' '.join(f'{a:.2f},{b:.2f}' for a, b in (self.P(x, v) for x, v in pts))
        tag = 'polygon' if closed and len(pts) > 2 else 'polyline'
        t = f'<title>{esc(title)}</title>' if title else ''
        self.add(f'<{tag} class="{cls}" points="{d}">{t}</{tag}>')

    def rect(self, x, v, w, h, cls='part', title=None):
        self.poly([(x, v), (x + w, v), (x + w, v + h), (x, v + h)], cls, True, title)

    def circle(self, x, v, r, cls='part'):
        cx, cy = self.P(x, v)
        self.add(f'<circle class="{cls}" cx="{cx:.2f}" cy="{cy:.2f}" r="{r * self.s:.2f}"/>')

    def line(self, a, b, cls='thin'):
        (x1, y1), (x2, y2) = self.P(*a), self.P(*b)
        self.add(f'<line class="{cls}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"/>')

    def text(self, x, v, s, cls='lbl', anchor='middle', dx=0, dy=0, rot=0):
        px, py = self.P(x, v)
        px += dx
        py += dy
        r = f' transform="rotate({rot} {px:.2f} {py:.2f})"' if rot else ''
        self.add(f'<text class="{cls}" x="{px:.2f}" y="{py:.2f}" text-anchor="{anchor}"{r}>{esc(s)}</text>')

    # ---- 치수선 ----
    def _dim_line(self, x1, y1, x2, y2, cls):
        """치수선. 두 끝점 사이가 화살촉 두 개(2·AH)보다 짧으면 화살표를 바깥에 두고 안쪽을 가리키게 한다."""
        span = math.hypot(x2 - x1, y2 - y1)
        if span >= 2 * ARROW_PX:
            self.add(f'<line class="{cls}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" marker-start="url(#arr)" marker-end="url(#arr)"/>')
            return False
        ux, uy = ((x2 - x1) / span, (y2 - y1) / span) if span else (1.0, 0.0)
        e = ARROW_OUT_PX
        ox1, oy1, ox2, oy2 = x1 - ux * e, y1 - uy * e, x2 + ux * e, y2 + uy * e
        self.add(f'<line class="{cls}" x1="{ox1:.2f}" y1="{oy1:.2f}" x2="{ox2:.2f}" y2="{oy2:.2f}"/>')
        self.add(f'<line class="{cls}" x1="{ox1:.2f}" y1="{oy1:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" marker-end="url(#arr)"/>')
        self.add(f'<line class="{cls}" x1="{ox2:.2f}" y1="{oy2:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" marker-end="url(#arr)"/>')
        return True

    def dim_h(self, xa, xb, v, off_px, label=None, cls='dim', va=None, vb=None, lab_side='right', tcls='dimt'):
        """수평 치수: 월드 높이 v의 두 점 사이, 화면에서 off_px만큼 위(+)/아래(-)로 띄움.
        va·vb를 주면 그 끝의 보조선은 높이 va·vb(재는 모서리)에서 시작한다(치수선 위치는 v 기준).
        lab_side='left'면 짧은 치수의 글자를 왼쪽 끝 바깥에 둔다. tcls로 글자 class를 바꾼다(어두운 면 위 등)."""
        if xb < xa:
            xa, xb, va, vb = xb, xa, vb, va
        (ax, ay), (bx, by) = self.P(xa, v), self.P(xb, v)
        y = ay - off_px
        if va is not None:
            ay = self.P(xa, va)[1]
        if vb is not None:
            by = self.P(xb, vb)[1]
        lab = label if label is not None else fmt(xb - xa)
        for ex, ey in ((ax, ay), (bx, by)):  # 보조선은 치수선을 4 px 넘는다
            self.add(f'<line class="ext" x1="{ex:.2f}" y1="{ey:.2f}" x2="{ex:.2f}" y2="{y - 4 if y < ey else y + 4:.2f}"/>')
        outside = self._dim_line(ax, y, bx, y, cls)
        small = (bx - ax) < 7 * len(str(lab)) + 6
        tx = (ax + bx) / 2 if not small else bx + (ARROW_OUT_PX + 4 if outside else 4)
        anchor = 'middle' if not small else 'start'
        if small and lab_side == 'left':
            tx, anchor = ax - (ARROW_OUT_PX - 2 if outside else 4), 'end'
        self.add(f'<text class="{tcls}" x="{tx:.2f}" y="{y - 3:.2f}" text-anchor="{anchor}">{esc(lab)}</text>')

    def dim_v(self, va, vb, x, off_px, label=None, cls='dim', x2=None, hlab=False, lab_v=None):
        """수직 치수: 월드 x에서 두 높이 사이, 화면에서 off_px만큼 오른쪽(+)/왼쪽(-).
        x2를 주면 높이 vb 쪽 보조선은 x2(그 높이의 모서리)에서 시작한다(치수선 위치는 x 기준).
        hlab=True면 글자를 눕히지 않고 위 끝 바로 아래 오른쪽에 둔다. lab_v를 주면 세운 글자의 가운데를 월드 높이 lab_v에 둔다."""
        if vb < va:
            va, vb = vb, va
        (ax, ay), (bx, by) = self.P(x, va), self.P(x if x2 is None else x2, vb)
        xx = ax + off_px
        lab = label if label is not None else fmt(vb - va)
        self.add(f'<line class="ext" x1="{ax:.2f}" y1="{ay:.2f}" x2="{xx + (4 if off_px > 0 else -4):.2f}" y2="{ay:.2f}"/>')
        self.add(f'<line class="ext" x1="{bx:.2f}" y1="{by:.2f}" x2="{xx + (4 if off_px > 0 else -4):.2f}" y2="{by:.2f}"/>')
        self._dim_line(xx, ay, xx, by, cls)
        small = (ay - by) < 12
        ty = (ay + by) / 2 if lab_v is None else self.P(x, lab_v)[1]
        if hlab:
            self.add(f'<text class="dimt" x="{xx + 4:.2f}" y="{by + 11:.2f}" text-anchor="start">{esc(lab)}</text>')
        elif small:
            self.add(f'<text class="dimt" x="{xx + 4:.2f}" y="{by - 3:.2f}" text-anchor="start">{esc(lab)}</text>')
        else:
            self.add(f'<text class="dimt" x="{xx - 3:.2f}" y="{ty:.2f}" text-anchor="middle" transform="rotate(-90 {xx - 3:.2f} {ty:.2f})">{esc(lab)}</text>')

    def leader(self, x, v, tdx, tdy, label, cls='lead'):
        px, py = self.P(x, v)
        tx, ty = px + tdx, py + tdy
        self.add(f'<circle class="dot" cx="{px:.2f}" cy="{py:.2f}" r="1.8"/>')
        self.add(f'<polyline class="{cls}" points="{px:.2f},{py:.2f} {tx:.2f},{ty:.2f} {tx + (14 if tdx >= 0 else -14):.2f},{ty:.2f}"/>')
        anchor = 'start' if tdx >= 0 else 'end'
        self.add(f'<text class="lbl" x="{tx + (16 if tdx >= 0 else -16):.2f}" y="{ty + 3.5:.2f}" text-anchor="{anchor}">{esc(label)}</text>')

    def leader_abs(self, x, v, lx, lv, label, anchor='start'):
        """점(x,v)에서 월드 좌표(lx,lv)의 글자 위치까지 지시선."""
        px, py = self.P(x, v)
        tx, ty = self.P(lx, lv)
        self.add(f'<circle class="dot" cx="{px:.2f}" cy="{py:.2f}" r="1.8"/>')
        k = 10 if anchor == 'start' else -10
        self.add(f'<polyline class="lead" points="{px:.2f},{py:.2f} {tx - k:.2f},{ty:.2f} {tx - 2 * (k > 0) + 2 * (k < 0):.2f},{ty:.2f}"/>')
        self.add(f'<text class="lbl" x="{tx + (2 if anchor == "start" else -2):.2f}" y="{ty + 3.5:.2f}" text-anchor="{anchor}">{esc(label)}</text>')

    def scalebar(self, length_mm=50):
        x, y = self.pl, self.h - 16
        L = length_mm * self.s
        self.add(f'<line class="dim" x1="{x:.1f}" y1="{y:.1f}" x2="{x + L:.1f}" y2="{y:.1f}"/>')
        for i in sorted(set(range(0, int(length_mm) + 1, 10)) | {int(length_mm)}):  # 끝 눈금은 항상
            xx = x + i * self.s
            self.add(f'<line class="dim" x1="{xx:.1f}" y1="{y - 3:.1f}" x2="{xx:.1f}" y2="{y + 3:.1f}"/>')
        self.add(f'<text class="dimt" x="{x + L + 6:.1f}" y="{y + 4:.1f}" text-anchor="start">{length_mm:.0f} mm</text>')

    def render(self, title=None, desc=None):
        head = (f'<svg viewBox="0 0 {self.w:.0f} {self.h:.0f}" width="{self.w:.0f}" role="img" '
                f'xmlns="http://www.w3.org/2000/svg">')
        t = f'<title>{esc(title)}</title>' if title else ''
        dsc = f'<desc>{esc(desc)}</desc>' if desc else ''
        # refX=10: 화살촉 끝이 치수 끝점(보조선)에 오고 몸통은 치수선 안쪽에 놓인다
        defs = (f'<defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="{ARROW_MW}" markerHeight="{ARROW_MW}" '
                'orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" class="arrh"/></marker></defs>')
        return head + t + dsc + defs + ''.join(self.items) + '</svg>'


DRAW_CSS = """
.drw svg{max-width:100%;height:auto;display:block;color:var(--ink)}
.drw .part{fill:var(--sur);stroke:currentColor;stroke-width:1.2}
.drw .white{fill:#F4F2EC;stroke:currentColor;stroke-width:1.1}
.drw .black{fill:#2A2B2E;stroke:currentColor;stroke-width:1.1}
.drw .flex{fill:var(--acc-bg);stroke:var(--acc);stroke-width:1.3}
.drw .fixed{fill:var(--bed);stroke:currentColor;stroke-width:1}
.drw .pcb{fill:#2E7D4F33;stroke:var(--good);stroke-width:1.2}
.drw .mag{fill:var(--crit);stroke:none}
.drw .sensor{fill:var(--warn);stroke:currentColor;stroke-width:.8}
.drw .pad{fill:var(--felt);stroke:none}
.drw .hole{fill:var(--bg);stroke:currentColor;stroke-width:1}
.drw .ghost{fill:none;stroke:var(--acc);stroke-width:1;stroke-dasharray:4 3}
.drw .spk{fill:#6B7A9022;stroke:var(--mut);stroke-width:1.2}
.drw .zone{fill:none;stroke:var(--crit);stroke-width:1;stroke-dasharray:6 4}
.drw .thin{stroke:var(--mut);stroke-width:.7;fill:none}
.drw .center{stroke:var(--mut);stroke-width:.7;stroke-dasharray:10 3 2 3;fill:none}
.drw .ext{stroke:var(--mut);stroke-width:.6}
.drw .dim{stroke:var(--acc);stroke-width:""" + f'{DIM_STROKE:g}' + """;fill:none}
.drw .arrh{fill:var(--acc)}
.drw .dimt{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:10.5px;fill:var(--acc)}
.drw .dimt.dimt-inv{fill:#86B4FF}
.drw .dimt.dimt-onw{fill:#1F5FBF}
.drw .lbl{font-family:"IBM Plex Sans KR","Noto Sans KR",sans-serif;font-size:11px;fill:var(--ink)}
.drw .lbl.lblk{fill:#1A2030}
.drw .lead{stroke:var(--ink2);stroke-width:.7;fill:none}
.drw .dot{fill:var(--ink2)}
.drw .ttl{font-family:"IBM Plex Sans KR",sans-serif;font-size:13px;font-weight:600;fill:var(--ink)}
.drw .ttlw{font-family:"IBM Plex Sans KR",sans-serif;font-size:11px;font-weight:600;fill:#F4F2EC}
.drw .ttlk{font-family:"IBM Plex Sans KR",sans-serif;font-size:13px;font-weight:600;fill:#1A2030}
.drw .flexb{fill:none;stroke:var(--acc);stroke-width:1.1;stroke-dasharray:5 3}
.drw .flexb2{fill:var(--acc-bg);stroke:var(--acc);stroke-width:1.2;stroke-dasharray:5 3}
.drw .inner{fill:none;stroke:currentColor;stroke-width:.7}
.drw .rubber{fill:#8A909955;stroke:none}
.drw .faint{fill:none;stroke:var(--rule);stroke-width:.8}
.drw .ghostfill{fill:none;stroke:var(--mut);stroke-width:.6;stroke-dasharray:2 2}
"""
