"""Drawing kit for the R31 touchscreen sheets = the key-action v4 kit (kav4/drawings/src: draw.py View, kit.py page /
ordinates / hatches / union, dwg.css) used unchanged, with three local settings:
  - the revision stamp (title block top right) is the touchscreen revision,
  - dwg.css here = the key-action dwg.css + touchscreen classes (lid, cradle, leg, ribbon, power wire, keep-out ...),
  - resolved_css reads every :root block of that file.
render_v4.side_scene (key-action module section) is imported for the context module on t01.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KAV4 = os.path.join(HERE, "kav4", "drawings", "src")
sys.path.insert(0, KAV4)
sys.dont_write_bytecode = True

import kit  # noqa: E402
import tgeo as g  # noqa: E402

kit.REV = g.REV_TXT


def resolved_css(k, prefix=""):
    src = open(os.path.join(HERE, "dwg.css")).read()
    vars_ = {}
    for root in re.findall(r":root\{([^}]*)\}", src):
        vars_.update(dict(re.findall(r"(--[\w-]+):([^;]+);?", root)))
    out = []
    for l in [l for l in src.splitlines() if l.startswith(".dwg")]:
        l = re.sub(r"var\((--[\w-]+)\)", lambda m: vars_[m.group(1)].strip(), l)
        l = l.replace("vector-effect:non-scaling-stroke", "")
        l = re.sub(r"stroke-width:([\d.]+)px", lambda m: f"stroke-width:{float(m.group(1)) * k:.5f}", l)
        l = re.sub(r"stroke-dasharray:([\d. ]+)", lambda m: "stroke-dasharray:" + " ".join(
            f"{float(x) * k:.5f}" for x in m.group(1).split()), l)
        l = l.replace('"IBM Plex Sans KR","Pretendard",system-ui,sans-serif', '"Apple SD Gothic Neo",sans-serif')
        l = l.replace('"IBM Plex Mono",ui-monospace,Menlo,monospace', 'Menlo,"Apple SD Gothic Neo",monospace')
        l = l.replace('"IBM Plex Mono",ui-monospace,monospace', 'Menlo,"Apple SD Gothic Neo",monospace')
        l = l.replace('"IBM Plex Mono",monospace', 'Menlo,"Apple SD Gothic Neo",monospace')
        sel, bodyc = l.split("{", 1)
        sel = ",".join(prefix + x.replace(".dwg ", "").strip() for x in sel.split(","))
        if bodyc.strip() == "}":
            continue
        out.append(sel + "{" + bodyc)
    return "\n".join(out)


kit.resolved_css = resolved_css

from kit import (View, fmt_mm, hatch, fill_rings, stroke_rings, union_rings, hpoly, ordz, ordy, panel_title, note_lines,  # noqa
                 leader_to, table, scalebar, halo1, halo_text, callouts, clip_begin, clip_end, break_top, FX, FR, F2, legend)


def F(v, nd=2):
    return fmt_mm(v, nd)


def pid_set(v):
    return dict(lid=hatch(v, "lid", 6, 45), cr=hatch(v, "cr", 5, -45), leg=hatch(v, "leg", 5, 45), print=hatch(v, "print", 6, 45),
                wood=hatch(v, "wood", 7, 45), steel=hatch(v, "steel", 4, -45), ko=hatch(v, "ko", 9, 45))


def poly_h(v, poly, cls, pid=None):
    kit.hpoly(v, poly, cls, pid)


def rings_h(v, polys, cls, pid=None, subs=(), res=0.02):
    fill_rings(v, union_rings(polys, res=res, subs=subs), cls, pid)


def T(v, u, w, s, cls="lt", anchor="start", size_px=10, rot=0, dy_px=0, halo=False):
    if halo:
        halo1(v, u, w, s, cls=cls, anchor=anchor, size_px=size_px, rot=rot, dy_px=dy_px)
    else:
        v.text(u, w, s, cls=cls, anchor=anchor, size_px=size_px, rot=rot, dy_px=dy_px)


def lead(v, fu, fv, tu, tv, s, anchor="start", size_px=10, cls="lt"):
    """leader with a label that keeps a white halo (lines under it do not strike it through)."""
    v.circle(fu, fv, v.px(1.6), cls="dot")
    v.line(fu, fv, tu, tv, cls="ld")
    e = v.px(5) if anchor == "start" else -v.px(5)
    v.line(tu, tv, tu + e, tv, cls="ld")
    halo1(v, tu + e + (v.px(2.5) if anchor == "start" else -v.px(2.5)), tv, s, cls=cls, anchor=anchor, size_px=size_px, dy_px=3.8)


def dim_al(v, a, b, off_px, text, size_px=9.5, cls="dm", ext=True, tside=1):
    """aligned dimension between points a, b offset by off_px (screen px, + = left of a->b)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    o = v.px(off_px)
    A = (a[0] + nx * o, a[1] + ny * o)
    B = (b[0] + nx * o, b[1] + ny * o)
    if ext:
        s = 1 if off_px > 0 else -1
        g_ = v.px(2.5)
        v.line(a[0] + nx * g_ * s, a[1] + ny * g_ * s, A[0] + nx * g_ * s * 1.4, A[1] + ny * g_ * s * 1.4, cls="ex")
        v.line(b[0] + nx * g_ * s, b[1] + ny * g_ * s, B[0] + nx * g_ * s * 1.4, B[1] + ny * g_ * s * 1.4, cls="ex")
    v.line(A[0], A[1], B[0], B[1], cls=cls)
    ang = math.atan2(B[1] - A[1], B[0] - A[0])
    v._arrow(B[0], B[1], ang)
    v._arrow(A[0], A[1], ang + math.pi)
    rot = -math.degrees(ang)
    if rot > 90:
        rot -= 180
    if rot < -90:
        rot += 180
    mu, mv = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
    tu, tv = mu + nx * v.px(4) * tside, mv + ny * v.px(4) * tside
    halo1(v, tu, tv, text, cls="dt", anchor="middle", size_px=size_px, rot=rot)


def angle_arc(v, c, r, a0, a1, text, size_px=10, cls="dm", tpos=None):
    pts = g.arc(c, r, a0, a1, 24)
    v.poly(pts, cls=cls, closed=False)
    am = math.radians((a0 + a1) / 2)
    tp = tpos or (c[0] + (r + v.px(10)) * math.cos(am), c[1] + (r + v.px(10)) * math.sin(am))
    halo1(v, tp[0], tp[1], text, cls="dt", anchor="middle", size_px=size_px, dy_px=3.5)


def box_note(v, u0, z_top, lines, size_px=10, line_px=14.5, cls="tx-s", title=None):
    z = z_top
    if title:
        v.text(u0, z, title, cls="ttl", anchor="start", size_px=size_px + 1)
        z -= v.px(line_px + 2)
    for s in lines:
        v.text(u0, z, s, cls=cls, anchor="start", size_px=size_px)
        z -= v.px(line_px)
    return z


def group_open(v, attrs):
    v.el.append(f"<g {attrs}>")
    return len(v.el)


def group_close(v):
    v.el.append("</g>")


def page(rows, out_base, title, subtitle="", width_px=1500, foot=()):
    svg = kit.page(rows, out_base, title, subtitle=subtitle, width_px=width_px, foot=foot)
    AUDIT[os.path.basename(out_base)] = text_audit(svg)
    return svg


AUDIT = {}


MONO_CLS = ("dt", "ot", "nt", "bt")


def _tw(s, fs, mono=False):
    """advance width measured with resvg (100 px test strings): sans (Apple SD Gothic Neo) Hangul 0.86 em / Latin 0.48 em,
    mono (Menlo) Latin 0.60 em / Hangul 0.99 em; +5 % margin."""
    cj, ot = (0.99, 0.60) if mono else (0.86, 0.48)
    return 1.05 * sum(fs * (cj if ord(c) > 0x2E80 else ot) for c in s)


def text_audit(svg, shrink_px=1.2, min_px=1.5):
    """text boxes of a page (page px): pairs of texts that overlap, and texts that leave their panel (clipped).
    Box of a text: advance width (CJK 0.95 em, others 0.58 em) x (baseline - 0.78 em .. baseline + 0.18 em), rotated by its
    transform, mapped through the panel viewBox.  Boxes are shrunk by shrink_px before the overlap test."""
    import html
    items, outside = [], []
    head_end = svg.find('<svg id="p')
    panels = [(None, svg[:head_end if head_end > 0 else len(svg)])]
    for m in re.finditer(r'<svg id="(p\d+)" x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)" viewBox="([-\d. ]+)">(.*?)</svg>', svg, re.S):
        panels.append((m, m.group(7)))
    for m, body in panels:
        if m is None:
            ox, oy, k, vx, vy, pw, ph = 0.0, 0.0, 1.0, 0.0, 0.0, None, None
        else:
            vb = [float(q) for q in m.group(6).split()]
            k = float(m.group(4)) / vb[2]
            ox, oy, vx, vy, pw, ph = float(m.group(2)), float(m.group(3)), vb[0], vb[1], float(m.group(4)), float(m.group(5))
        for t in re.finditer(r"<text ([^>]*)>([^<]*)</text>", body):
            a, s = t.group(1), html.unescape(t.group(2))
            if not s.strip() or "fill:#ffffff" in a and "paint-order" not in a:
                continue
            g_ = lambda n, d=None: (re.search(rf'{n}="([^"]*)"', a) or [None, d])[1]
            x, y = float(g_("x", 0)), float(g_("y", 0))
            fs = float(g_("font-size", 11))
            anc = g_("text-anchor", "start")
            cls_ = g_("class", "")
            w = _tw(s, fs, mono=cls_ in MONO_CLS)
            x0 = x - (w / 2 if anc == "middle" else (w if anc == "end" else 0.0))
            pts = [(x0, y - 0.78 * fs), (x0 + w, y - 0.78 * fs), (x0 + w, y + 0.18 * fs), (x0, y + 0.18 * fs)]
            tr = re.search(r"rotate\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)", a)
            if tr:
                r_, cx, cy = math.radians(float(tr.group(1))), float(tr.group(2)), float(tr.group(3))
                pts = [(cx + (px - cx) * math.cos(r_) - (py - cy) * math.sin(r_), cy + (px - cx) * math.sin(r_) + (py - cy) * math.cos(r_)) for px, py in pts]
            xs = [ox + (px - vx) * k for px, py in pts]
            ys = [oy + (py - vy) * k for px, py in pts]
            box = (min(xs), max(xs), min(ys), max(ys))
            items.append((box, s, m.group(1) if m else "head"))
            if pw is not None and (box[0] < ox - 2 or box[1] > ox + pw + 2 or box[2] < oy - 2 or box[3] > oy + ph + 2):
                outside.append((s[:40], m.group(1)))
    over = []
    for i in range(len(items)):
        (a0, a1, b0, b1), s1, p1 = items[i]
        for j in range(i + 1, len(items)):
            (c0, c1, d0, d1), s2, p2 = items[j]
            ix = min(a1, c1) - max(a0, c0) - 2 * shrink_px
            iy = min(b1, d1) - max(b0, d0) - 2 * shrink_px
            if ix > min_px and iy > min_px and s1 != s2:
                over.append((s1[:36], s2[:36], p1, round(ix, 1), round(iy, 1)))
    return dict(n_text=len(items), overlaps=over, outside=outside)


def callouts2(v, items, u_cols, z_top, line_px=14.5, size_px=9.5, r_px=7.0, per_col=None):
    """lettered balloons at features + the note list in several columns (u_cols = left u of each column).
    items: [(tag, (fu, fv), (dx_px, dy_px), text)]."""
    r = v.px(r_px)
    for tag, (fu, fv), (dx, dy), text in items:
        tu, tv = fu + v.px(dx), fv + v.px(dy)
        L = math.hypot(tu - fu, tv - fv)
        if L > r:
            v.line(fu, fv, tu - (tu - fu) * r / L, tv - (tv - fv) * r / L, cls="ld")
        v.circle(fu, fv, v.px(1.6), cls="dot")
        v.circle(tu, tv, r, cls="bl")
        v.text(tu, tv, tag, cls="bt", size_px=9, dy_px=3.2)
    per = per_col or math.ceil(len(items) / len(u_cols))
    for i, (tag, f, d, text) in enumerate(items):
        c, k = divmod(i, per)
        u0 = u_cols[min(c, len(u_cols) - 1)]
        z = z_top - k * v.px(line_px)
        v.circle(u0 + r, z + v.px(3.4), r, cls="bl")
        v.text(u0 + r, z, tag, cls="bt", size_px=9, dy_px=0.2)
        v.text(u0 + 2 * r + v.px(5), z, text, cls="lt", anchor="start", size_px=size_px)
    return z_top - per * v.px(line_px)
