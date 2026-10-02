"""Toccata v4 W1+ drawing kit (on top of the repo kit draw.py View + dwg.css, both copied here).

Data : every coordinate comes from ../final/geometry.json (parts / plan / end_parts / solved / dims).
       Removal kinematics (drawing 12) come from ../final/metrics.json (same model run as geometry.json);
       the rear bar outline (drawing 11) and the magnet size come from the v3 tables in ../context/v3_extract.txt
       (the system v4 plugs into).  Nothing is typed by hand: dn()/v3n() parse numbers out of those tables.
Draw : sections are built by slicing the (y, z) prisms of geometry.json at a plane; the cut face of one printed
       body is drawn as the union of its sub-part prisms (raster union + contour trace, 0.02 mm), so the seams
       between sub-parts do not show.  Page = rows of View panels -> one standalone SVG (CSS resolved per panel
       scale, like v4/alts/common.py) -> PNG with resvg_py.
"""
import json
import math
import os
import re

import contourpy
import numpy as np
from PIL import Image, ImageDraw

from draw import View, fmt_mm, ord_y, ord_z  # noqa: F401  (re-exported)

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.dirname(HERE)
# read at import time: a re-run after the model changes picks up every new number (no local patches; the r3
# drawing-side corrections are merged into the model, see geometry.json "patches_merged")
_REPO_MODEL = os.path.normpath(os.path.join(HERE, "..", "..", "model"))
if not os.path.exists(os.path.join(V4, "final", "geometry.json")) and os.path.exists(os.path.join(_REPO_MODEL, "geometry.json")):
    G = json.load(open(os.path.join(_REPO_MODEL, "geometry.json")))
    M = json.load(open(os.path.join(_REPO_MODEL, "metrics.json")))
    V3TXT = open(os.path.join(_REPO_MODEL, "v3_extract.txt")).read()
else:
    G = json.load(open(os.path.join(V4, "final", "geometry.json")))
    M = json.load(open(os.path.join(V4, "final", "metrics.json")))
    V3TXT = open(os.path.join(V4, "context", "v3_extract.txt")).read()
DIMS = {d["id"]: d for d in G["dims"]}
PARTS = G["parts"]
PLAN = G["plan"]
SOL = G["solved"]
USED = {}          # dimension ids actually used (for the log)
# title-block revision (r4.5 = r4.4 fix 2b + the MISUMI C-UA90R5-3-0.5 torsion spring, geometry.json meta)
REV = "Toccata v4 W1+ r4.5" if "r4.5" in G["meta"]["project"] else "Toccata v4 W1+ r4.4"
REV = REV + " · 2026-09-28"


# ------------------------------------------------------------------ numbers out of the tables
def nums(s):
    """all numbers in a table string; a '-' right after a digit is a range dash, not a sign."""
    s = str(s).replace("−", "-").replace("–", "-")
    out = []
    for m in re.finditer(r"-?\d+(?:\.\d+)?", s):
        t = m.group(0)
        if t.startswith("-") and m.start() > 0 and s[m.start() - 1].isdigit():
            t = t[1:]
        out.append(float(t))
    return out


def dn(did, i=0, field="value"):
    """i-th number in dims[did][field] (value / ref / note / item)."""
    USED[did] = DIMS[did]["item"]
    v = DIMS[did][field]
    if isinstance(v, (int, float)) and field == "value":
        return float(v)
    return nums(v)[i]


def dns(did, field="value"):
    USED[did] = DIMS[did]["item"]
    v = DIMS[did][field]
    return [float(v)] if isinstance(v, (int, float)) else nums(v)


def v3n(pattern, i=0):
    """i-th number on the first v3_extract line matching pattern (after the match)."""
    for line in V3TXT.splitlines():
        m = re.search(pattern, line)
        if m:
            return nums(line[m.end():])[i]
    raise KeyError(pattern)


# ------------------------------------------------------------------ parts
def body(name, src=None):
    return [p for p in (PARTS if src is None else src) if p["body"] == name]


def fixed(src=None):
    return [p for p in (PARTS if src is None else src) if p["body"] == "fixed"]


def pts(p, pose="rest"):
    if "side" in p:
        return [tuple(q) for q in p["side"]]
    return [tuple(q) for q in p["side_" + pose]]


def cut_x(p, x):
    return p["x"][0] - 1e-9 <= x <= p["x"][1] + 1e-9


def plan_item(name):
    for p in PLAN:
        if p["part"] == name:
            return p
    raise KeyError(name)


def plan_all(prefix):
    return [p for p in PLAN if p["part"].startswith(prefix)]


def bbox(poly):
    us = [q[0] for q in poly]
    vs = [q[1] for q in poly]
    return min(us), max(us), min(vs), max(vs)


def yslice(poly, y):
    """z intervals of a closed (y, z) polygon on the vertical line y."""
    zs = []
    n = len(poly)
    for i in range(n):
        (y1, z1), (y2, z2) = poly[i], poly[(i + 1) % n]
        if (y1 <= y < y2) or (y2 <= y < y1):
            zs.append(z1 + (z2 - z1) * (y - y1) / (y2 - y1))
    zs.sort()
    return [(zs[i], zs[i + 1]) for i in range(0, len(zs) - 1, 2)]


def rot(p, c, a):
    dy, dz = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + dy * ca - dz * sa, c[1] + dy * sa + dz * ca)


def rot_pts(poly, c, a):
    return [rot(p, c, a) for p in poly]


def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def arc_pts(c, r, a0, a1, n=16):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def circle_pts(c, r, n=40):
    return arc_pts(c, r, 0, 360, n)[:-1]


# ------------------------------------------------------------------ union outline (raster + contour trace)
def _rdp(P, eps):
    if len(P) < 3:
        return P
    P = np.asarray(P)
    keep = np.zeros(len(P), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        d = b - a
        L = math.hypot(*d)
        seg = P[i + 1:j]
        if L < 1e-12:
            dist = np.hypot(*(seg - a).T)
        else:
            dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(dist))
        if dist[k] > eps:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return [tuple(q) for q in P[keep]]


def union_rings(polys, res=0.02, eps=0.012, subs=()):
    """raster union of polys (contour-traced); subs: polygons cut out of the union afterwards (voids)."""
    polys = [p for p in polys if len(p) >= 3]
    subs = [p for p in subs if len(p) >= 3]
    if not polys:
        return []
    allp = np.concatenate([np.asarray(p, float) for p in polys])
    u0, v0 = allp.min(0) - 5 * res
    u1, v1 = allp.max(0) + 5 * res
    W = int((u1 - u0) / res) + 3
    H = int((v1 - v0) / res) + 3
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon([((u - u0) / res - 0.5, (v1 - v) / res - 0.5) for u, v in p], fill=255)
    for p in subs:
        d.polygon([((u - u0) / res - 0.5, (v1 - v) / res - 0.5) for u, v in p], fill=0)
    a = np.asarray(im, dtype=float)
    gen = contourpy.contour_generator(z=a, line_type="Separate")
    rings = []
    for L in gen.lines(127.5):
        w = [(u0 + (c + 1) * res, v1 - (r + 1) * res) for c, r in L]
        if len(w) >= 4:
            rings.append(_rdp(w, eps))
    return rings


def ring_d(v, rings):
    out = []
    for r in rings:
        out.append("M" + " L".join(v.P(a, b) for a, b in r) + " Z")
    return " ".join(out)


# ------------------------------------------------------------------ hatches / materials
_uid = [0]


def uid(p):
    _uid[0] += 1
    return f"{p}{_uid[0]}"


def hatch(v, kind="print", spacing_px=6, ang=45):
    pid = uid("h")
    sp = v.px(spacing_px)
    v.defs.append(
        f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="{sp:.4f}" height="{sp:.4f}" '
        f'patternTransform="rotate({ang})"><line x1="0" y1="0" x2="0" y2="{sp:.4f}" class="hl-{kind}"/></pattern>')
    return pid


def pids(v):
    return dict(steel=hatch(v, "steel", 4, -45), print=hatch(v, "print", 6, 45), key=hatch(v, "key", 5, -45),
                lever=hatch(v, "print", 5, -45), cover=hatch(v, "print", 7, 45), bar=hatch(v, "bar", 4, 0))


def fill_rings(v, rings, cls, pid=None, outline=True):
    """filled region with holes (evenodd); cls = material class; optional hatch; outline stroke."""
    if not rings:
        return
    d = ring_d(v, rings)
    v.el.append(f'<path class="{cls} fillonly" fill-rule="evenodd" d="{d}"/>')
    if pid:
        v.el.append(f'<path fill="url(#{pid})" fill-rule="evenodd" class="nostroke" d="{d}"/>')
    if outline:
        v.el.append(f'<path class="out" d="{d}"/>')
    for r in rings:
        v.segs += [(a[0], a[1], b[0], b[1]) for a, b in zip(r, r[1:] + r[:1])]


def stroke_rings(v, rings, cls):
    if rings:
        v.el.append(f'<path class="{cls}" d="{ring_d(v, rings)}"/>')
        for r in rings:
            v.segs += [(a[0], a[1], b[0], b[1]) for a, b in zip(r, r[1:] + r[:1])]


def hpoly(v, poly, cls, pid=None):
    v.poly(poly, cls=cls)
    if pid:
        v.el.append(f'<polygon points="{" ".join(v.P(a, b) for a, b in poly)}" fill="url(#{pid})" class="nostroke"/>')


MAT_FIXED = [  # (substring in part name, css class, hatch key)
    # r4.4 exported prisms: fin-boss bores (drilled void), lever rod (steel), printed rod-end plug, control-board screw
    # head envelope, sensor board SB / EL / ER (stripboard)
    ("fin boss bore", "void", None), ("lever rod end plug", "m-print2", None), ("lever rod D4", "m-steel", "steel"),
    # r4.5 fix: the rear-wall spring-leg groove and its 0.5 x 45 deg entry chamfer are exported as FEMALE cut parts
    # (boss + rear wall): drawn as voids, never as printed material
    ("spring groove cut", "void", None), ("spring groove entry chamfer", "void", None),
    ("control-board screw", "env", None), ("sensor board support", "m-print", "print"), ("sensor board", "m-pcb", None),
    ("felt", "m-felt", None), ("key rod", "m-steel", "steel"), ("balance pin", "m-steel", "steel"),
    ("control board", "m-pcb", None), ("board components", "env", None), ("board part", "env", None), ("RP2040", "env", None),
    ("USB-C plug", "env", None), ("pad bar rail", "m-print", "print"), ("pad bar", "m-bar", "bar"),
    ("pad wedge", "m-bar", "bar"), ("cover curtain", "m-cover", "cover"), ("sensor bar", "m-sbar", "print"),
]


def mat_fixed(name):
    for k, c, h in MAT_FIXED:
        if k in name:
            return c, h
    return "m-print", "print"


# ------------------------------------------------------------------ small symbols
def pivot_mark(v, c, r, cross=3.0, cls="m-steel"):
    v.circle(c[0], c[1], r, cls=cls)
    v.circle(c[0], c[1], v.px(1.6), cls="pivot")
    v.cl(c[0] - r - cross, c[1], c[0] + r + cross, c[1])
    v.cl(c[0], c[1] - r - cross, c[0], c[1] + r + cross)


def sensor_mark(v, y, z, size_px=4):
    s = v.px(size_px)
    v.poly([(y - s, z), (y, z + s), (y + s, z), (y, z - s)], cls="m-sensor")


def scalebar(v, u, z, L=20, size_px=10):
    v.line(u, z, u + L, z, cls="dm")
    step = 5 if L <= 20 else 10
    for i in range(0, int(L) + 1, step):
        v.line(u + i, z - v.px(3), u + i, z + v.px(3), cls="dm")
    v.text(u + L + v.px(6), z - v.px(3.5), f"{L:g} mm", cls="dt", anchor="start", size_px=size_px)


def balloon_row(v, items, z_row, u_min, u_max, gap_px=22):
    """items: [(n, (fu, fv), u_pref)] -> balloons on one row at z_row (no crossing leaders: sorted by u)."""
    items = sorted(items, key=lambda t: t[2])
    gap = v.px(gap_px)
    pos = []
    for n, f, up in items:
        u = max(up, (pos[-1] + gap) if pos else u_min)
        pos.append(u)
    over = pos[-1] - u_max if pos else 0
    if over > 0:
        for i in range(len(pos) - 1, -1, -1):
            lim = u_max if i == len(pos) - 1 else pos[i + 1] - gap
            pos[i] = min(pos[i], lim)
    for (n, f, up), u in zip(items, pos):
        v.balloon(f[0], f[1], u, z_row, n)


def legend(v, items, u0, v_top, cols=3, col_w=110.0, line_px=16, size_px=10.5):
    rows = math.ceil(len(items) / cols)
    r = v.px(7)
    for i, (n, lab) in enumerate(items):
        c, rr = divmod(i, rows)
        u = u0 + c * col_w
        z = v_top - rr * v.px(line_px)
        v.circle(u + r, z + v.px(3.5), r, cls="bl")
        v.text(u + r, z, n, cls="bt", size_px=9, dy_px=0.5)
        v.text(u + 2 * r + v.px(5), z, lab, cls="lt", anchor="start", size_px=size_px)


def note_lines(v, lines, u0, z_top, line_px=15, size_px=10.5, cls="tx-s"):
    for i, s in enumerate(lines):
        v.text(u0, z_top - i * v.px(line_px), s, cls=cls, anchor="start", size_px=size_px)


def halo_text(v, u, w, s, cls="tx", anchor="middle", size_px=11, rot=0, dy_px=0, halo_px=2.6):
    """text with a white halo (drawn twice: white stroke under, then the text) so a line running under it does
    not strike it through."""
    e = v._text_el(u, w, s, cls, anchor, size_px, rot, dy_px)
    v.el.append(e.replace("<text ", f'<text style="stroke:#ffffff;stroke-width:{v.px(halo_px):.4f};stroke-linejoin:round;fill:#ffffff" ', 1))
    v.el.append(e)


def halo1(v, u, w, s, cls="tx", anchor="middle", size_px=11, rot=0, dy_px=0, halo_px=2.6):
    """r4.5 fix 3: the white halo of halo_text as ONE text element (white stroke painted under the fill,
    paint-order: stroke) - same look, and a text-overlap check does not see a duplicate."""
    e = v._text_el(u, w, s, cls, anchor, size_px, rot, dy_px)
    v.el.append(e.replace("<text ", f'<text style="stroke:#ffffff;stroke-width:{v.px(halo_px):.4f};stroke-linejoin:round;paint-order:stroke" ', 1))


def tail_text(v, B, d, s, t_min, t_max, size_px=9.5, taken=None, cls="dt", pad_px=2.5):
    """r4.5 fix 3: value of an aligned dimension placed OUTBOARD: a tail of the dimension line from its arrowhead B
    along the unit direction d (world), length searched in [t_min, t_max] (world) for the first spot where the
    horizontal label at the tail end (anchor on the side the tail points to) crosses no recorded stroke and no box in
    `taken`; then the tail (dimension-line class) and the label with a white halo are drawn.  Returns the label box."""
    w, fs, pad = v.text_w(s, size_px), v.px(size_px), v.px(pad_px)
    left = d[0] < 0
    best = None
    n = max(1, int((t_max - t_min) / v.px(1)))
    for i in range(n + 1):
        t = t_min + (t_max - t_min) * i / n
        T = (B[0] + t * d[0], B[1] + t * d[1])
        u0 = T[0] - v.px(2) - w if left else T[0] + v.px(2)
        base = T[1] - v.px(3.5)
        box = (u0 - pad, u0 + w + pad, base - 0.25 * fs - pad, base + 0.8 * fs + pad)
        hit = v._hits(box) + sum(1 for q in (taken or ()) if box[0] < q[1] and q[0] < box[1] and box[2] < q[3] and q[2] < box[3])
        if best is None or hit < best[0]:
            best = (hit, T, box)
        if hit == 0:
            break
    hit, T, box = best
    v.line(B[0], B[1], T[0], T[1], cls="dm")
    halo1(v, T[0] - v.px(2) if left else T[0] + v.px(2), T[1], s, cls=cls, anchor="end" if left else "start", size_px=size_px, dy_px=3.5)
    if taken is not None:
        taken.append(box)
    return box


def label(v, u, z, s, size_px=10.5, anchor="middle", cls="tx"):
    v.text(u, z, s, cls=cls, anchor=anchor, size_px=size_px)


def panel_title(v, u, z, s, size_px=12.5):
    v.text(u, z, s, cls="ttl", anchor="start", size_px=size_px)


def leader_to(v, fu, fv, tu, tv, s, anchor="start", size_px=10.5):
    """leader from feature (fu, fv) to a label at (tu, tv) (world); short horizontal tail."""
    v.circle(fu, fv, v.px(1.6), cls="dot")
    v.line(fu, fv, tu, tv, cls="ld")
    e = v.px(5) if anchor == "start" else -v.px(5)
    v.line(tu, tv, tu + e, tv, cls="ld")
    v.text(tu + e + (v.px(2.5) if anchor == "start" else -v.px(2.5)), tv, s, cls="lt", anchor=anchor,
           size_px=size_px, dy_px=3.8)


def table(v, u0, v0, cols, rows, col_w, row_px=17, size_px=10, head_cls="tbh"):
    """simple grid table; cols = header strings; rows = list of lists; col_w = widths in world units.
    (u0, v0) = top-left corner (world, v up)."""
    rh = v.px(row_px)
    W = sum(col_w)
    n = len(rows) + 1
    v.rect(u0, v0 - rh, W, rh, cls=head_cls)
    for i in range(n + 1):
        v.line(u0, v0 - i * rh, u0 + W, v0 - i * rh, cls="tbl")
    u = u0
    for w in col_w + [0]:
        v.line(u, v0, u, v0 - n * rh, cls="tbl")
        u += w
    u = u0
    for j, (h, w) in enumerate(zip(cols, col_w)):
        v.text(u + w / 2, v0 - rh + v.px(5), h, cls="lt", size_px=size_px)
        u += w
    for i, r in enumerate(rows):
        u = u0
        for j, (c, w) in enumerate(zip(r, col_w)):
            cls = "nt" if j else "lt"
            v.text(u + w / 2, v0 - (i + 2) * rh + v.px(5), c, cls=cls, size_px=size_px)
            u += w
    return v0 - n * rh


# ------------------------------------------------------------------ page assembly and export
def resolved_css(k, prefix=""):
    src = open(os.path.join(HERE, "dwg.css")).read()
    root = re.search(r":root\{([^}]*)\}", src).group(1)
    vars_ = dict(re.findall(r"(--[\w-]+):([^;]+);?", root))
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


def panel_svg(v):
    s = v.svg()
    m = re.search(r'viewBox="([-\d. ]+)"', s)
    x0, y0, w, h = map(float, m.group(1).split())
    return s, w * v.s, h * v.s


def page(rows, out_base, title, subtitle="", width_px=1500, gap_px=8, margin_px=10, foot=()):
    """rows: list of rows; a row = list of View.  Writes out_base.svg and out_base.png (1800 px)."""
    head = []
    y = 8.0
    head.append((y + 22, title, 20, 700, "#1d2433"))
    y += 30
    if subtitle:
        for line in subtitle.split("\n"):
            head.append((y + 14, line, 12.5, 400, "#4a5568"))
            y += 18
    y += 8
    parts, styles = [], []
    i = 0
    maxw = width_px
    for row in rows:
        x = margin_px
        hmax = 0.0
        for v in row:
            s, wpx, hpx = panel_svg(v)
            pid = f"p{i}"
            i += 1
            styles.append(resolved_css(1.0 / v.s, f"#{pid} "))
            s = re.sub(r'^<svg class="dwg" viewBox="([-\d. ]+)" style="[^"]*" role="img" aria-label="[^"]*" '
                       r'xmlns="http://www.w3.org/2000/svg">',
                       lambda m: f'<svg id="{pid}" x="{x:.1f}" y="{y:.1f}" width="{wpx:.1f}" height="{hpx:.1f}" '
                                 f'viewBox="{m.group(1)}">', s)
            parts.append(s)
            x += wpx + gap_px
            hmax = max(hmax, hpx)
        maxw = max(maxw, x - gap_px + margin_px)
        y += hmax + gap_px
    for line in foot:
        head.append((y + 13, line, 11.5, 400, "#4a5568"))
        y += 17
    total_h = y + 6
    txt = []
    for yy, t, size, weight, fill in head:
        t = t.replace("&", "&amp;").replace("<", "&lt;")
        txt.append(f'<text x="{margin_px + 4}" y="{yy:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                   f'font-family=\'"Apple SD Gothic Neo",sans-serif\'>{t}</text>')
    # r4.5 title block: revision stamp at the top right of every sheet (the model revision drawn)
    txt.append(f'<text x="{maxw - margin_px - 4:.1f}" y="30.0" font-size="13" font-weight="700" fill="#1d2433" text-anchor="end" '
               f'font-family=\'"Apple SD Gothic Neo",sans-serif\'>{REV}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{maxw:.0f}" height="{total_h:.0f}" '
           f'viewBox="0 0 {maxw:.1f} {total_h:.1f}">'
           f'<style>{"".join(styles)}</style>'
           f'<rect x="0" y="0" width="{maxw:.1f}" height="{total_h:.1f}" fill="#ffffff"/>'
           + "".join(txt) + "".join(parts) + "</svg>")
    open(out_base + ".svg", "w").write(svg)
    import resvg_py
    open(out_base + ".png", "wb").write(bytes(resvg_py.svg_to_bytes(svg_string=svg, background="#ffffff", width=1800)))
    return svg


# ------------------------------------------------------------------ ordinates with 2-decimal labels, both sides
def F2(x):
    return fmt_mm(x, 2)


def FX(x, nd=2):
    """r4.5 fix 3 (issue 5): the same half-up rule as fmt_mm at a FIXED precision (trailing zeros kept: 1.501 -> '1.50',
    2.699 -> '2.70') - for table columns and value ranges, so one column / one range shows one number of decimals."""
    from decimal import Decimal, ROUND_HALF_UP
    s = str(Decimal(repr(round(float(x), 9))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))
    return "0" + s[2:] if s.startswith("-0") and set(s[2:]) <= set(".0") else s


def FR(a, b, nd=2):
    """value range 'a~b' at one fixed precision (FX)."""
    return f"{FX(a, nd)}~{FX(b, nd)}"


def break_top(v, u0, u1, z, over_px=4.0, amp_px=3.0, cls="vis"):
    """r4.5 fix 3: conventional break line across a member that runs out of the panel (u0..u1 at height z): the part
    above z is masked white and a thin zigzag is drawn across it (slightly wider than the member)."""
    e = v.px(over_px)
    top = v.v1 + v.pad + 1.0
    v.el.append(f'<polygon style="fill:#ffffff;stroke:none" points="{v.P(u0 - e, z)} {v.P(u1 + e, z)} {v.P(u1 + e, top)} {v.P(u0 - e, top)}"/>')
    w = u1 - u0 + 2 * e
    a = v.px(amp_px)
    zz = [(u0 - e, z), (u0 - e + 0.35 * w, z), (u0 - e + 0.45 * w, z + a), (u0 - e + 0.55 * w, z - a), (u0 - e + 0.65 * w, z), (u1 + e, z)]
    v.poly(zz, cls=cls, closed=False)


def _pav(t):
    blocks = []
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


def ordz(v, feats, col, side="right", gap_px=12.5, label_px=9.5, prefix="z", lo=None, hi=None, raw=False, nd=2):
    """feats [(z, u_feature, label)] -> horizontal extension lines to column u=col, labels spread in z
    (least squares, >= gap) to the right (or left) of col.  lo/hi: keep labels inside [lo, hi] (world z)."""
    feats = sorted(feats, key=lambda t: t[0])
    merged = []
    for z, uf, lab in feats:
        if merged and abs(z - merged[-1][0]) < 0.005:
            z0, u0, labs = merged[-1]
            merged[-1] = (z0, max((u0, uf), key=lambda u: abs(col - u)), labs + [lab] * (lab not in labs))
        else:
            merged.append((z, uf, [lab]))
    feats = [(z, uf, " · ".join(l for l in labs if l)) for z, uf, labs in merged]
    if not feats:
        return
    gap = v.px(gap_px)
    u = _pav([z - i * gap for i, (z, uf, lab) in enumerate(feats)])
    pos = [ui + i * gap for i, ui in enumerate(u)]
    if lo is not None and pos[0] < lo:
        pos = [p + (lo - pos[0]) for p in pos]
    if hi is not None and pos[-1] > hi:
        d = pos[-1] - hi
        pos = [p - d for p in pos]
    run = max(v.px(9), 0.6 * max(abs(w - z) for w, (z, uf, lab) in zip(pos, feats)))
    run = min(run, v.px(40))
    s = 1 if side == "right" else -1
    for (z, uf, lab), w in zip(feats, pos):
        v.line(uf + s * v.px(2), z, col, z, cls="ex")
        v.circle(col, z, v.px(1.5), cls="dot")
        v.line(col, z, col + s * run, w, cls="ex")
        txt = lab if raw else f"{prefix}{fmt_mm(z, nd)}" + (f"  {lab}" if lab else "")
        v.text(col + s * (run + v.px(3)), w, txt, cls="ot", anchor="start" if s > 0 else "end", size_px=label_px, dy_px=3.3)


def _vline_broken(v, u, a, b, breaks, gap_px=2.0):
    """vertical extension line u, from v=a to v=b, interrupted where it crosses a label box of `breaks`
    [(u_lo, u_hi, v_lo, v_hi)] (drafting rule: extension lines are broken at text)."""
    lo, hi = min(a, b), max(a, b)
    cuts = sorted((max(lo, b0 - v.px(gap_px)), min(hi, b1 + v.px(gap_px)))
                  for u0, u1, b0, b1 in breaks if u0 - v.px(1) <= u <= u1 + v.px(1) and b1 > lo and b0 < hi)
    cur = lo
    for c0, c1 in cuts:
        if c0 > cur:
            v.line(u, cur, u, c0, cls="ex")
        cur = max(cur, c1)
    if cur < hi:
        v.line(u, cur, u, hi, cls="ex")


def ordy(v, feats, row, side="below", gap_px=12.5, label_px=9.5, prefix="", lo=None, hi=None, breaks=(), grow=True, nd=2):
    """feats [(y, v_feature, label)] -> vertical extension lines to row v=row, rotated labels spread in u
    (nd = decimals of the value, 2 by default; 3 where the model value has 3 and the table rounds it),
    below (or above) the row.  breaks: label boxes of another ordinate row that the extension lines must not
    run through (they are broken there).  grow: extend the view (v0 / v1) so no label leaves the panel.
    Returns the label boxes [(u_lo, u_hi, v_lo, v_hi)] (world)."""
    feats = sorted(feats, key=lambda t: t[0])
    merged = []
    for y, vf, lab in feats:
        if merged and abs(y - merged[-1][0]) < 0.005:
            y0, v0, labs = merged[-1]
            merged[-1] = (y0, max((v0, vf), key=lambda q: abs(row - q)), labs + [lab] * (lab not in labs))
        else:
            merged.append((y, vf, [lab]))
    feats = [(y, vf, " · ".join(l for l in labs if l)) for y, vf, labs in merged]
    if not feats:
        return
    gap = v.px(gap_px)
    u = _pav([y - i * gap for i, (y, vf, lab) in enumerate(feats)])
    pos = [ui + i * gap for i, ui in enumerate(u)]
    if lo is not None and pos[0] < lo:
        pos = [p + (lo - pos[0]) for p in pos]
    if hi is not None and pos[-1] > hi:
        d = pos[-1] - hi
        pos = [p - d for p in pos]
    run = max(v.px(9), 0.6 * max(abs(w - y) for w, (y, vf, lab) in zip(pos, feats)))
    run = min(run, v.px(40))
    s = -1 if side == "below" else 1
    boxes = []
    for (y, vf, lab), w in zip(feats, pos):
        if breaks:
            _vline_broken(v, y, vf + s * v.px(2), row, breaks)
        else:
            v.line(y, vf + s * v.px(2), y, row, cls="ex")
        v.circle(y, row, v.px(1.5), cls="dot")
        v.line(y, row, w, row + s * run, cls="ex")
        txt = f"{prefix}{fmt_mm(y, nd)}" + (f"  {lab}" if lab else "")
        v0_ = row + s * (run + v.px(3))
        v.text(w + v.px(3.3), v0_, txt, cls="ot", anchor="end" if s < 0 else "start",
               size_px=label_px, rot=-90)
        tw = v.text_w(txt, label_px)
        v1_ = v0_ + s * tw
        # glyph box of the -90 deg text: from (baseline u - 0.8 em) to (baseline u + 0.2 em)
        boxes.append((w + v.px(3.3) - v.px(0.8 * label_px), w + v.px(3.3) + v.px(0.25 * label_px), min(v0_, v1_), max(v0_, v1_)))
    if grow and boxes:
        lo_v = min(b[2] for b in boxes) - v.px(3)
        hi_v = max(b[3] for b in boxes) + v.px(3)
        if lo_v < v.v0 - v.pad:
            v.v0 = lo_v + v.pad
        if hi_v > v.v1 + v.pad:
            v.v1 = hi_v - v.pad
    return boxes


# ------------------------------------------------------------------ clipping of a scene to a window
def clip_begin(v):
    return len(v.el)


def clip_end(v, i0, u0, u1, w0, w1, frame=True):
    cid = uid("c")
    v.defs.append(f'<clipPath id="{cid}"><rect x="{u0:.4f}" y="{-w1:.4f}" width="{u1 - u0:.4f}" height="{w1 - w0:.4f}"/></clipPath>')
    v.el.insert(i0, f'<g clip-path="url(#{cid})">')
    v.el.append("</g>")
    # late-label slots were recorded by index; shift the ones after i0
    v._late = [((i + 1) if i >= i0 else i, fn) for i, fn in v._late]
    if frame:
        v.el.append(f'<rect class="vis" x="{u0:.4f}" y="{-w1:.4f}" width="{u1 - u0:.4f}" height="{w1 - w0:.4f}"/>')


# ------------------------------------------------------------------ lettered callouts + note list
def callouts(v, items, notes_u, notes_top, line_px=14.5, size_px=9.8, r_px=7.0):
    """items: [(tag, (fu, fv), (dx_px, dy_px), text)] -> dot at the feature, leader to a small lettered circle
    offset by (dx, dy) screen px (dy up), and a note list 'tag  text' from (notes_u, notes_top) downward."""
    r = v.px(r_px)
    for tag, (fu, fv), (dx, dy), text in items:
        tu, tv = fu + v.px(dx), fv + v.px(dy)
        L = math.hypot(tu - fu, tv - fv)
        if L > r:
            eu, ev = tu - (tu - fu) * r / L, tv - (tv - fv) * r / L
            v.line(fu, fv, eu, ev, cls="ld")
        v.circle(fu, fv, v.px(1.6), cls="dot")
        v.circle(tu, tv, r, cls="bl")
        v.text(tu, tv, tag, cls="bt", size_px=9, dy_px=3.2)
    for i, (tag, f, d, text) in enumerate(items):
        z = notes_top - i * v.px(line_px)
        v.circle(notes_u + r, z + v.px(3.4), r, cls="bl")
        v.text(notes_u + r, z, tag, cls="bt", size_px=9, dy_px=0.2)
        v.text(notes_u + 2 * r + v.px(5), z, text, cls="lt", anchor="start", size_px=size_px)
