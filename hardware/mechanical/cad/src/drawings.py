"""Toccata L2 rear unit + touchscreen rev 3 - dimensioned 2D drawing sheets D01..D06 (SVG + PNG) and shaded renders R01..R03.

Made FROM THE BUILT SOLIDS (build_all.collect(): keyaction_parts + body + electronics), so every outline and every number on the
sheets comes from the same geometry as the print STLs:
  * sections   = manifold3d slices of the real solids at the cut plane (Manifold.slice after a proper rotation),
  * plan / elevation views = the solids' projections (Manifold.project) drawn far-to-near (painter), hidden ones dashed,
  * dimensions, coordinates, hole sizes, slot patterns, clearances, volumes = computed from those polygons or from the
    generator constants (body.POD / body.GEOM, touchscreen_rev3) - nothing typed by hand.
Only the loudspeaker assumptions (Qts, Vas, driver displacement, fill factor) and the centre-unit bay zones are read from
spec/body_L2.json (stated on the sheets).

  python3 drawings.py                 # every sheet + PNG copies + renders
  python3 drawings.py D02 D05         # only these sheets (PNG too)
  python3 drawings.py --no-png        # SVG only
  python3 drawings.py --no-render     # skip R01..R03
  python3 drawings.py --only-render   # just R01..R03

Outputs: ../drawings/D01_plan.svg (전체 평면), D02_speaker_section.svg (스피커 단면), D03_centre_sections.svg (가운데 유닛 단면 2개),
D04_rear_elevation.svg (뒷면 입면 - I/O 판), D05_touchscreen.svg (터치스크린: 사용 25° / 뒤꿈치 22° / 접은 상태),
D06_plywood_cuts.svg (합판 재단도, 400 x 1200 한 장) + the same names .png; ../renders/R01_front.png, R02_rear_left.png, R03_folded.png.
Sheets are A2 landscape (594 x 420 mm); the view scales on each sheet are true when printed on A2. PNG = 4 px per sheet mm.
build_all.py calls main(parts) at the end of a build (a failure - e.g. a DrawingCheckError self check - makes build_all exit 2 after the other outputs are written).
"""
import collections
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from manifold3d import CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
OUT = os.path.normpath(os.path.join(HERE, ".."))
DWG = os.path.join(OUT, "drawings")
REN = os.path.join(OUT, "renders")

DATE = "2026-10-02"
STATE = "L2 · 스피커 앞판 40° · 터치스크린 3판"
SOURCES = "src/body.py · electronics.py · touchscreen_rev3.py · keyaction_parts.py (build_all.collect) · spec/body_L2.json"
SHEETS = collections.OrderedDict([
    ("D01", ("D01_plan", "전체 평면")),
    ("D02", ("D02_speaker_section", "스피커 단면")),
    ("D03", ("D03_centre_sections", "가운데 유닛 단면 2개")),
    ("D04", ("D04_rear_elevation", "뒷면 입면 - I/O 판")),
    ("D05", ("D05_touchscreen", "터치스크린: 사용 25° / 뒤꿈치 22° / 접은 상태")),
    ("D06", ("D06_plywood_cuts", "합판 재단도 (400 × 1200 한 장)")),
])
A2 = (594.0, 420.0)
PX_PER_MM = 4.0

# text heights (sheet mm)
T_LAB = 3.5
T_DIM = 3.2
T_NOTE = 3.1
T_SMALL = 2.8
T_HEAD = 4.8
T_TITLE = 6.5

FONT = "'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic','IBM Plex Sans KR',sans-serif"

# ------------------------------------------------------------------ text width (real font metrics when PIL + the Mac font exist)
_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        _FONT = False
        try:
            from PIL import ImageFont
            for p in ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"):
                if os.path.exists(p):
                    _FONT = ImageFont.truetype(p, 100)
                    break
        except Exception:
            _FONT = False
    return _FONT


def text_w(s, size):
    f = _font()
    if f:
        return f.getlength(s) / 100.0 * size * 1.02
    return sum(0.92 if ord(c) > 0x2E80 else 0.56 for c in s) * size


def fnum(v, nd=2):
    s = ("%." + str(nd) + "f") % v
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return html.escape(s, quote=True)


# ------------------------------------------------------------------ materials / styles

ORDER = {"ctx": 0, "wood": 1, "print": 2, "rubber": 3, "elec": 4, "metal": 5, "screen": 6, "cable": 7}
MAT_NAME = collections.OrderedDict([
    ("wood", "오꾸메 합판 11.5T"), ("print", "출력물 PETG"), ("metal", "구매 금속 (스피커·나사·인서트·자석)"),
    ("rubber", "고무·EVA·실리콘"), ("elec", "전자부 (보드·모듈)"), ("screen", "화면 (Waveshare 7\")"),
    ("cable", "케이블"), ("ctx", "건반 모듈 (참고, 연한 회색)")])

CSS = """
.bg{fill:#ffffff}
.frame{fill:none;stroke:#1d2433;stroke-width:.5}
.t{font-family:%(font)s;fill:#1d2433}
.h{paint-order:stroke;stroke:#ffffff;stroke-width:.75;stroke-linejoin:round}
.tb{font-weight:700}
.td{fill:#1f5fbf}
.tm{fill:#5b6578}
.tr{fill:#c2410c}
.S-wood{fill:url(#hw);stroke:#1d2433;stroke-width:.4;stroke-linejoin:round}
.S-print{fill:url(#hp);stroke:#1d2433;stroke-width:.4;stroke-linejoin:round}
.S-metal{fill:url(#hm);stroke:#1d2433;stroke-width:.32;stroke-linejoin:round}
.S-rubber{fill:#50555e;stroke:#1d2433;stroke-width:.25}
.S-elec{fill:url(#he);stroke:#1d2433;stroke-width:.3}
.S-screen{fill:#3a4150;stroke:#1d2433;stroke-width:.3}
.S-cable{fill:#e3b23c;stroke:#6b5a1e;stroke-width:.18}
.S-ctx{fill:#eceef1;stroke:#a3aab5;stroke-width:.18}
.P-wood{fill:#f2e6d2;stroke:#39404d;stroke-width:.22;stroke-linejoin:round}
.P-print{fill:#e5ebf3;stroke:#39404d;stroke-width:.22;stroke-linejoin:round}
.P-metal{fill:#c9ced6;stroke:#39404d;stroke-width:.2}
.P-rubber{fill:#7d828b;stroke:#39404d;stroke-width:.18}
.P-elec{fill:#d3ead8;stroke:#39404d;stroke-width:.2}
.P-screen{fill:#596070;stroke:#39404d;stroke-width:.2}
.P-cable{fill:#f0cf7a;fill-opacity:.55;stroke:#8a7430;stroke-width:.14;stroke-opacity:.7}
.P-ctx{fill:#f2f3f5;stroke:#b3b9c3;stroke-width:.18}
.air{fill:#e8f1fb;stroke:none}
.hid{fill:none;stroke:#39404d;stroke-width:.24;stroke-dasharray:1.6 .9}
.hidc{fill:none;stroke:#c2410c;stroke-width:.28;stroke-dasharray:2.2 1.1}
.ph{fill:none;stroke:#5b6578;stroke-width:.3;stroke-dasharray:4 1 1 1}
.cl{fill:none;stroke:#6b7690;stroke-width:.2;stroke-dasharray:6 1.2 1 1.2}
.thin{fill:none;stroke:#39404d;stroke-width:.2}
.vis{fill:none;stroke:#1d2433;stroke-width:.3}
.sound{fill:none;stroke:#c2410c;stroke-width:.4;stroke-dasharray:3 1.2}
.ax{fill:none;stroke:#7a3fb5;stroke-width:.3;stroke-dasharray:5 1.2 1 1.2}
.keep{fill:none;stroke:#b42318;stroke-width:.3;stroke-dasharray:1.2 1}
.dm{fill:none;stroke:#1f5fbf;stroke-width:.18}
.ex{fill:none;stroke:#8a96ab;stroke-width:.15}
.ah{fill:#1f5fbf;stroke:none}
.ld{fill:none;stroke:#3d4555;stroke-width:.18}
.dot{fill:#3d4555}
.bal{fill:#ffffff;stroke:#1d2433;stroke-width:.25}
.secl{fill:none;stroke:#1d2433;stroke-width:.55}
.seca{fill:#1d2433}
.grid{fill:none;stroke:#1d2433;stroke-width:.25}
.grid2{fill:none;stroke:#8a96ab;stroke-width:.15}
.box{fill:#fbfbfc;stroke:#c3c9d3;stroke-width:.2}
.sheetply{fill:#fbf6ee;stroke:#1d2433;stroke-width:.35}
.zone{fill:#f4f6f9;stroke:#8a96ab;stroke-width:.2}
""" % {"font": FONT}

DEFS = """
<pattern id="hw" patternUnits="userSpaceOnUse" width="1.6" height="1.6" patternTransform="rotate(45)"><rect width="1.6" height="1.6" fill="#ecdcc2"/><line x1="0" y1="0" x2="0" y2="1.6" stroke="#a8875a" stroke-width=".22"/></pattern>
<pattern id="hp" patternUnits="userSpaceOnUse" width="1.1" height="1.1" patternTransform="rotate(-45)"><rect width="1.1" height="1.1" fill="#dfe6ef"/><line x1="0" y1="0" x2="0" y2="1.1" stroke="#7f93b0" stroke-width=".16"/></pattern>
<pattern id="hm" patternUnits="userSpaceOnUse" width=".9" height=".9" patternTransform="rotate(45)"><rect width=".9" height=".9" fill="#c3c8d1"/><path d="M0 0V.9M0 0H.9" stroke="#5d6778" stroke-width=".12"/></pattern>
<pattern id="he" patternUnits="userSpaceOnUse" width="1.4" height="1.4"><rect width="1.4" height="1.4" fill="#cfe6d3"/><line x1="0" y1=".7" x2="1.4" y2=".7" stroke="#5f9a6c" stroke-width=".14"/></pattern>
"""

LAYERS = ("geo", "over", "dim", "lead", "text")


def is_ka(p):
    g = p.group
    return (len(g) > 1 and g[0] == "O" and g[1].isdigit()) or g.startswith("끝 부속")


def mclass(p):
    if is_ka(p):
        return "ctx"
    if p.kind == "plywood":
        return "wood"
    if p.kind == "print":
        return "print"
    if p.id.startswith("TS-E-SCREEN"):
        return "screen"
    if p.id in ("SPK-L", "SPK-R"):
        return "metal"
    if p.kind == "electronics":
        if p.group == "케이블" or p.id.startswith("TS-C-") or p.id.startswith("C-"):
            return "cable"
        return "elec"
    if p.kind == "consumable" or any(k in (p.material or "") for k in ("고무", "실리콘", "EVA")):
        return "rubber"
    return "metal"


def short(name):
    s = re.split(r" \(| — | - ", name)[0].strip()
    if s.count("(") > s.count(")"):
        s = s[:s.index("(")].strip()
    return s


_SIDE = re.compile(r"(?<![A-Za-z0-9])([LR])(?![A-Za-z0-9])")


def pair_name(ps):
    """one name for the instances of an item: 'XT30 짝 집게 L' + '... R' -> 'XT30 짝 집게 L·R'."""
    names = [short(p.name_ko) for p in ps]
    if len(set(names)) > 1 and len(set(_SIDE.sub("#", n) for n in names)) == 1 and \
            {m.group(1) for n in names for m in _SIDE.finditer(n)} == {"L", "R"}:
        return _SIDE.sub("L·R", names[0], count=1)
    return names[0]


# ------------------------------------------------------------------ 2D geometry from the solids

TX = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]], float)     # (x, y, z) -> (y, z, x): slice / project along x -> (y, z)
TY = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]], float)    # (x, y, z) -> (x, z, -y): along y -> (x, z)


def sec(m, axis, c):
    if axis == "x":
        cs = m.transform(TX).slice(c)
    elif axis == "y":
        cs = m.transform(TY).slice(-c)
    else:
        cs = m.slice(c)
    return cs.simplify(0.002)


def proj(m, axis):
    if axis == "x":
        cs = m.transform(TX).project()
    elif axis == "y":
        cs = m.transform(TY).project()
    else:
        cs = m.project()
    return cs.simplify(0.002)


def polys(cs):
    return [np.asarray(p, float) for p in cs.to_polygons() if len(p) >= 3]


def rect_cs(u0, u1, v0, v1):
    return CrossSection.square((u1 - u0, v1 - v0)).translate((u0, v0))


def signed_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def inner_point(pl, extra_avoid=None):
    """approximate pole of inaccessibility of a polygon set (even-odd), returns (u, v, clearance)."""
    if not pl:
        return None
    allp = np.vstack(pl)
    (x0, y0), (x1, y1) = allp.min(0), allp.max(0)
    segs = np.vstack([np.hstack([p, np.roll(p, -1, axis=0)]) for p in pl])   # x0 y0 x1 y1
    best = None
    for n in (18, 36):
        xs = np.linspace(x0, x1, n + 2)[1:-1]
        ys = np.linspace(y0, y1, n + 2)[1:-1]
        G = np.array([(x, y) for x in xs for y in ys])
        px, py = G[:, 0:1], G[:, 1:2]
        ax, ay, bx, by = segs[:, 0], segs[:, 1], segs[:, 2], segs[:, 3]
        cond = ((ay > py) != (by > py))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = ax + (py - ay) * (bx - ax) / (by - ay)
        inside = (np.sum(cond & (px < xint), axis=1) % 2) == 1
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        L2[L2 == 0] = 1e-12
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
        d = np.hypot(px - (ax + t * dx), py - (ay + t * dy)).min(axis=1)
        d[~inside] = -1
        i = int(np.argmax(d))
        if d[i] > 0 and (best is None or d[i] > best[2]):
            best = (float(G[i, 0]), float(G[i, 1]), float(d[i]))
    if best is None:
        c = allp.mean(0)
        best = (float(c[0]), float(c[1]), 0.0)
    return best


def hole_list(cs):
    """inner contours of a cross section: [{'u0','u1','v0','v1','cu','cv','w','h','area','round','d'}]"""
    out = []
    for p in polys(cs):
        a = signed_area(p)
        if a >= 0:
            continue
        u0, v0 = p.min(0)
        u1, v1 = p.max(0)
        w, h = u1 - u0, v1 - v0
        rnd = len(p) >= 12 and abs(w - h) < 0.05 * max(w, h) and abs(-a - math.pi * w * h / 4) < 0.04 * (-a)
        out.append(dict(u0=u0, u1=u1, v0=v0, v1=v1, cu=(u0 + u1) / 2, cv=(v0 + v1) / 2, w=w, h=h, area=-a, round=rnd,
                        d=(w + h) / 2 if rnd else None))
    return out


def pattern_text(hs, ax="u"):
    """group holes of the same size, then by row / column; describe count, size, centres and pitch."""
    groups = collections.OrderedDict()
    for h in hs:
        key = ("Ø%s" % fnum(h["d"], 1)) if h["round"] else ("%s×%s" % (fnum(h["w"], 1), fnum(h["h"], 1)))
        groups.setdefault(key, []).append(h)
    lines = []

    def pitch_txt(c):
        d = np.diff(c)
        return ("간격 %s" % fnum(d.mean(), 2)) if np.ptp(d) < 0.05 else "간격 " + "·".join(fnum(x, 2) for x in d)

    for key, g in groups.items():
        if len(g) == 1:
            h = g[0]
            lines.append("%s : 중심 (%s, %s)" % (key, fnum(h["cu"], 2), fnum(h["cv"], 2)))
            continue
        rows = collections.OrderedDict()
        for h in sorted(g, key=lambda h: (round(h["cv"], 1), h["cu"])):
            rows.setdefault(round(h["cv"], 1), []).append(h)
        cols = collections.OrderedDict()
        for h in sorted(g, key=lambda h: (round(h["cu"], 1), h["cv"])):
            cols.setdefault(round(h["cu"], 1), []).append(h)
        if len(cols) == 1:
            cv = sorted(h["cv"] for h in g)
            lines.append("%s ×%d : 세로 중심 %s~%s %s, 가로 중심 %s" % (key, len(g), fnum(cv[0], 2), fnum(cv[-1], 2), pitch_txt(cv), fnum(g[0]["cu"], 2)))
            continue
        rk = [tuple(round(h["cu"], 1) for h in r) for r in rows.values()]
        if len(rows) > 1 and len(cols) > 1 and len(set(rk)) == 1:
            cu = [h["cu"] for h in list(rows.values())[0]]
            cv = sorted(rows.keys())
            lines.append("%s ×%d : %d열 × %d줄 — 가로 중심 %s (%s) · 세로 중심 %s~%s %s"
                         % (key, len(g), len(cu), len(cv), "·".join(fnum(c_, 2) for c_ in cu), pitch_txt(cu), fnum(cv[0], 2), fnum(cv[-1], 2), pitch_txt(cv)))
            continue
        parts_ = []
        for cv, r in rows.items():
            cu = sorted(h["cu"] for h in r)
            if len(cu) == 1:
                parts_.append("(%s, %s)" % (fnum(cu[0], 2), fnum(cv, 2)))
            else:
                parts_.append("%d개 가로 중심 %s~%s %s · 세로 중심 %s" % (len(cu), fnum(cu[0], 2), fnum(cu[-1], 2), pitch_txt(cu), fnum(cv, 2)))
        lines.append("%s ×%d : " % (key, len(g)) + " / ".join(parts_))
    return lines


def pack_1d(want, half, lo, hi, gap):
    """positions for items wanting `want` (sorted order kept), each half-size `half`, min gap, inside [lo, hi]."""
    n = len(want)
    if n == 0:
        return []
    pos = list(want)
    for _ in range(4):
        for i in range(n):
            mn = lo + half[i] if i == 0 else pos[i - 1] + half[i - 1] + gap + half[i]
            pos[i] = max(pos[i], mn)
        for i in range(n - 1, -1, -1):
            mx = hi - half[i] if i == n - 1 else pos[i + 1] - half[i + 1] - gap - half[i]
            pos[i] = min(pos[i], mx)
    return pos


# ------------------------------------------------------------------ sheet


class Sheet:
    def __init__(self, code, scale_txt, w=A2[0], h=A2[1]):
        self.code = code
        self.file, self.name = SHEETS[code]
        self.scale_txt = scale_txt
        self.w, self.h = w, h
        self.L = {k: [] for k in LAYERS}
        self.tboxes = []
        self.used = set()
        self.views = []
        self.defs = []

    def add(self, layer, s):
        self.L[layer].append(s)

    # ---- text
    def text(self, x, y, s, size=T_LAB, anchor="start", rot=0, cls="", layer="text", bold=False, halo=True, check=True):
        w = text_w(s, size)
        if rot == 0:
            x0 = x if anchor == "start" else (x - w / 2 if anchor == "middle" else x - w)
            box = (x0, y - 0.78 * size, x0 + w, y + 0.22 * size)
        elif rot == -90:
            # text runs upward from the anchor ('start') / ends at the anchor ('end')
            if anchor == "start":
                y0, y1 = y - w, y
            elif anchor == "end":
                y0, y1 = y, y + w
            else:
                y0, y1 = y - w / 2, y + w / 2
            box = (x - 0.78 * size, y0, x + 0.22 * size, y1)
        else:
            box = None
        c = "t" + (" h" if halo else "") + (" tb" if bold else "") + ((" " + cls) if cls else "")
        tr = (' transform="rotate(%g %.3f %.3f)"' % (rot, x, y)) if rot else ""
        self.add(layer, '<text class="%s" x="%.3f" y="%.3f" font-size="%.2f" text-anchor="%s"%s>%s</text>'
                 % (c, x, y, size, anchor, tr, esc(s)))
        if box and check:
            self.tboxes.append((box, s))
        return box

    def textblock(self, x, y, lines, size=T_NOTE, lh=1.42, **kw):
        for i, ln in enumerate(lines):
            self.text(x, y + i * size * lh, ln, size=size, **kw)
        return y + len(lines) * size * lh

    def wrap(self, s, width, size):
        out = []
        for para in s.split("\n"):
            words = para.split(" ")
            cur = ""
            for wd in words:
                t = (cur + " " + wd) if cur else wd
                if text_w(t, size) <= width or not cur:
                    cur = t
                else:
                    out.append(cur)
                    cur = wd
            out.append(cur)
        return out

    # ---- primitives (sheet coords)
    def line(self, pts, cls="thin", layer="over", attr=""):
        d = "M" + " L".join("%.3f %.3f" % (x, y) for x, y in pts)
        self.add(layer, '<path class="%s" d="%s"%s/>' % (cls, d, attr))

    def rect(self, x0, y0, x1, y1, cls="thin", layer="over", rx=0):
        self.add(layer, '<rect class="%s" x="%.3f" y="%.3f" width="%.3f" height="%.3f"%s/>'
                 % (cls, min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0), (' rx="%g"' % rx) if rx else ""))

    def circle(self, x, y, r, cls="thin", layer="over"):
        self.add(layer, '<circle class="%s" cx="%.3f" cy="%.3f" r="%.3f"/>' % (cls, x, y, r))

    def arrow(self, tip, frm, size=2.2, layer="dim", cls="ah"):
        dx, dy = tip[0] - frm[0], tip[1] - frm[1]
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        bx, by = tip[0] - ux * size, tip[1] - uy * size
        w = size * 0.3
        self.add(layer, '<path class="%s" d="M%.3f %.3f L%.3f %.3f L%.3f %.3f Z"/>'
                 % (cls, tip[0], tip[1], bx - uy * w, by + ux * w, bx + uy * w, by - ux * w))

    # ---- dimensions (sheet coords)
    def dim_h(self, x0, x1, y, text, ext=(), size=T_DIM, out_side="right"):
        """horizontal dimension x0..x1 on line y; ext = [(x, y_from)] extension lines."""
        x0, x1 = sorted((x0, x1))
        for (xe, ye) in ext:
            sg = 1 if y > ye else -1
            self.line([(xe, ye + sg * 0.8), (xe, y + sg * 1.2)], "ex", "dim")
        tw = text_w(text, size)
        span = x1 - x0
        if span >= tw + 5.0:
            self.line([(x0, y), (x1, y)], "dm", "dim")
            self.arrow((x0, y), (x1, y))
            self.arrow((x1, y), (x0, y))
            self.text((x0 + x1) / 2, y - 0.9, text, size, "middle", cls="td")
        else:
            # arrows outside, text beside
            self.line([(x0 - 4, y), (x1 + 4, y)], "dm", "dim")
            self.arrow((x0, y), (x0 - 3.5, y))
            self.arrow((x1, y), (x1 + 3.5, y))
            if out_side == "right":
                self.line([(x1 + 4, y), (x1 + 5.5 + tw, y)], "dm", "dim")
                self.text(x1 + 5, y - 0.9, text, size, "start", cls="td")
            else:
                self.line([(x0 - 5.5 - tw, y), (x0 - 4, y)], "dm", "dim")
                self.text(x0 - 5, y - 0.9, text, size, "end", cls="td")

    def dim_v(self, y0, y1, x, text, ext=(), size=T_DIM, out_side="up"):
        y0, y1 = sorted((y0, y1))
        for (xe, ye) in ext:   # (x_from, y)
            sg = 1 if x > xe else -1
            self.line([(xe + sg * 0.8, ye), (x + sg * 1.2, ye)], "ex", "dim")
        tw = text_w(text, size)
        span = y1 - y0
        if span >= tw + 5.0:
            self.line([(x, y0), (x, y1)], "dm", "dim")
            self.arrow((x, y0), (x, y1))
            self.arrow((x, y1), (x, y0))
            self.text(x - 0.9, (y0 + y1) / 2, text, size, "middle", rot=-90, cls="td")
        else:
            self.line([(x, y0 - 4), (x, y1 + 4)], "dm", "dim")
            self.arrow((x, y0), (x, y0 - 3.5))
            self.arrow((x, y1), (x, y1 + 3.5))
            if out_side == "up":
                self.line([(x, y0 - 5.5 - tw), (x, y0 - 4)], "dm", "dim")
                self.text(x - 0.9, y0 - 5, text, size, "start", rot=-90, cls="td")
            else:
                self.line([(x, y1 + 4), (x, y1 + 5.5 + tw)], "dm", "dim")
                self.text(x - 0.9, y1 + 5, text, size, "end", rot=-90, cls="td")

    def dim_al(self, p, q, off, text, size=T_DIM):
        """aligned dimension between sheet points p, q, offset `off` along the left normal of p->q."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        nx, ny = uy, -ux
        a = (p[0] + nx * off, p[1] + ny * off)
        b = (q[0] + nx * off, q[1] + ny * off)
        sg = 1 if off > 0 else -1
        for P_, A_ in ((p, a), (q, b)):
            self.line([(P_[0] + nx * sg * 0.8, P_[1] + ny * sg * 0.8), (A_[0] + nx * sg * 1.2, A_[1] + ny * sg * 1.2)], "ex", "dim")
        self.line([a, b], "dm", "dim")
        self.arrow(a, b)
        self.arrow(b, a)
        ang = math.degrees(math.atan2(uy, ux))
        if ang > 90:
            ang -= 180
        elif ang <= -90:
            ang += 180
        m = ((a[0] + b[0]) / 2 + nx * sg * 1.0, (a[1] + b[1]) / 2 + ny * sg * 1.0)
        self.add("text", '<text class="t h td" x="%.3f" y="%.3f" font-size="%.2f" text-anchor="middle" transform="rotate(%.3f %.3f %.3f)">%s</text>'
                 % (m[0], m[1], size, ang, m[0], m[1], esc(text)))

    def ordinates_h(self, items, y_base, side=1, size=T_DIM, lo=0.0, hi=None, title=None, title_x=None, minsep=None):
        """items: [(x, y_feature, label)]; ticks from the feature to the base line y_base, labels rotated past it."""
        hi = self.w if hi is None else hi
        items = sorted(items, key=lambda t: t[0])
        half = [size * 0.55] * len(items)
        slots = pack_1d([t[0] for t in items], half, lo, hi, minsep if minsep is not None else size * 0.12)
        for (x, yf, lab), sx in zip(items, slots):
            if yf is not None:
                sg = 1 if y_base > yf else -1
                self.line([(x, yf + sg * 0.8), (x, y_base)], "ex", "dim")
            y1 = y_base + side * 1.5
            y2 = y_base + side * 4.5
            self.line([(x, y_base), (x, y1), (sx, y2), (sx, y2 + side * 1.0)], "dm", "dim")
            self.circle(x, y_base, 0.35, "ah", "dim")
            self.text(sx + 0.28 * size, y2 + side * 1.6, lab, size, "end" if side > 0 else "start", rot=-90, cls="td")
        if title:
            tx = title_x if title_x is not None else lo
            self.text(tx, y_base - side * 1.2 + (size if side < 0 else 0) * 0, title, T_SMALL, "start", cls="tm")

    def ordinates_v(self, items, x_base, side=1, size=T_DIM, lo=0.0, hi=None, minsep=None):
        """items: [(y, x_feature, label)]; horizontal labels beside the base line x_base (side +1 = right)."""
        hi = self.h if hi is None else hi
        items = sorted(items, key=lambda t: t[0])
        half = [size * 0.58] * len(items)
        slots = pack_1d([t[0] for t in items], half, lo, hi, minsep if minsep is not None else size * 0.15)
        for (y, xf, lab), sy in zip(items, slots):
            if xf is not None:
                sg = 1 if x_base > xf else -1
                self.line([(xf + sg * 0.8, y), (x_base, y)], "ex", "dim")
            x1 = x_base + side * 1.5
            x2 = x_base + side * 4.5
            self.line([(x_base, y), (x1, y), (x2, sy), (x2 + side * 1.0, sy)], "dm", "dim")
            self.circle(x_base, y, 0.35, "ah", "dim")
            self.text(x2 + side * 1.6, sy + 0.33 * size, lab, size, "start" if side > 0 else "end", cls="td")

    def callouts_v(self, items, x_lane, side, lo, hi, size=T_LAB, lh=1.3, gap=1.0):
        """items: [(ax, ay, text)] -> labels stacked in a vertical lane at x_lane (side +1: labels to the right of the lane)."""
        items = sorted(items, key=lambda t: t[1])
        hs = [len(t[2].split("\n")) * size * lh / 2.0 for t in items]
        slots = pack_1d([t[1] for t in items], hs, lo, hi, gap)
        for (ax, ay, txt), sy, hh in zip(items, slots, hs):
            lines = txt.split("\n")
            ytop = sy - hh
            yl = ytop + size * lh * 0.5           # leader joins the first line
            self.circle(ax, ay, 0.55, "dot", "lead")
            self.line([(ax, ay), (x_lane - side * 3.0, yl), (x_lane - side * 0.8, yl)], "ld", "lead")
            for i, ln in enumerate(lines):
                self.text(x_lane, ytop + size * lh * (i + 0.5) + 0.35 * size, ln, size if i == 0 else size * 0.86,
                          "start" if side > 0 else "end", cls="" if i == 0 else "tm")

    def callouts_h(self, items, y_lane, side, lo, hi, size=T_LAB, gap=2.5):
        """items: [(ax, ay, text)] -> one row of labels at y_lane (side -1: labels above the lane line, leaders from below)."""
        items = sorted(items, key=lambda t: t[0])
        half = [text_w(t[2], size) / 2 for t in items]
        slots = pack_1d([t[0] for t in items], half, lo, hi, gap)
        for (ax, ay, txt), sx, hw in zip(items, slots, half):
            self.circle(ax, ay, 0.55, "dot", "lead")
            yb = y_lane + (0.6 if side < 0 else -size - 0.2)
            self.line([(ax, ay), (sx, yb + (0 if side < 0 else 0))], "ld", "lead")
            self.line([(sx - hw, yb), (sx + hw, yb)], "ld", "lead")
            self.text(sx, y_lane if side < 0 else y_lane, txt, size, "middle")

    def balloons_h(self, items, y_lane, lo, hi, r=2.5, size=T_DIM):
        """items: [(ax, ay, number)] -> numbered circles in a row at y_lane."""
        items = sorted(items, key=lambda t: t[0])
        slots = pack_1d([t[0] for t in items], [r] * len(items), lo, hi, 0.9)
        for (ax, ay, n), sx in zip(items, slots):
            dx, dy = sx - ax, y_lane - ay
            L = math.hypot(dx, dy) or 1
            self.circle(ax, ay, 0.5, "dot", "lead")
            self.line([(ax, ay), (sx - dx / L * r, y_lane - dy / L * r)], "ld", "lead")
            self.circle(sx, y_lane, r, "bal", "lead")
            self.text(sx, y_lane + 0.36 * size, str(n), size, "middle", bold=True, halo=False)

    def table(self, x, y, cols, rows, size=T_SMALL, rh=4.2, head=True):
        """cols: [(title, width, align)]; returns bottom y."""
        W = sum(c[1] for c in cols)
        n = len(rows) + (1 if head else 0)
        self.rect(x, y, x + W, y + n * rh, "grid", "over")
        yy = y
        allrows = ([[c[0] for c in cols]] if head else []) + rows
        for ri, r in enumerate(allrows):
            if ri:
                self.line([(x, yy), (x + W, yy)], "grid2" if not (head and ri == 1) else "grid", "over")
            xx = x
            for ci, (c, val) in enumerate(zip(cols, r)):
                if ci:
                    self.line([(xx, yy), (xx, yy + rh)], "grid2", "over")
                tx = xx + 1.0 if c[2] == "start" else (xx + c[1] / 2 if c[2] == "middle" else xx + c[1] - 1.0)
                self.text(tx, yy + rh * 0.5 + 0.34 * size, val, size, c[2], bold=(head and ri == 0), halo=False)
                xx += c[1]
            yy += rh
        return yy

    def legend(self, x, y, mats, cols=1, colw=88.0, size=T_SMALL, extra=()):
        """material swatches (only the classes used on the sheet) + extra line samples [(cls, text)]."""
        self.text(x, y, "범례", T_NOTE, bold=True, halo=False)
        y += 2.5
        items = [("S-" + m, MAT_NAME[m]) for m in MAT_NAME if m in mats] + list(extra)
        per = int(math.ceil(len(items) / float(cols)))
        for i, (cls, txt) in enumerate(items):
            cx = x + (i // per) * colw
            cy = y + (i % per) * 5.0
            if cls.startswith("S-") or cls in ("air", "zone", "sheetply"):
                self.rect(cx, cy, cx + 8, cy + 3.6, cls, "over")
            else:
                self.line([(cx, cy + 1.8), (cx + 8, cy + 1.8)], cls, "over")
            self.text(cx + 10, cy + 2.9, txt, size, halo=False)
        return y + per * 5.0

    def scale_bar(self, x, y, k, length_mm, step, label):
        """scale bar for a view of scale k (sheet mm per world mm): alternating blocks of `step` mm."""
        n = int(round(length_mm / step))
        for i in range(n):
            self.rect(x + i * step * k, y, x + (i + 1) * step * k, y + 1.4, "seca" if i % 2 == 0 else "bal", "over")
        for i in range(n + 1):
            if i in (0, n) or n <= 6:
                self.text(x + i * step * k, y + 4.6, fnum(i * step), T_SMALL, "middle", halo=False, check=False)
        self.text(x + n * step * k + 3, y + 1.6, "mm  " + label, T_SMALL, "start", halo=False)

    def title_block(self, n_total=6):
        W, H = 196.0, 38.0
        x0, y0 = self.w - 10 - W, self.h - 10 - H
        self.rect(x0, y0, x0 + W, y0 + H, "grid", "over")
        self.add("over", '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#ffffff"/>' % (x0 + .2, y0 + .2, W - .4, H - .4))
        r1, r2, r3 = y0 + 13, y0 + 21, y0 + 29
        for yy in (r1, r2, r3):
            self.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
        self.line([(x0 + 62, y0), (x0 + 62, r3)], "grid2", "over")
        self.line([(x0 + 150, y0), (x0 + 150, r1)], "grid2", "over")
        self.line([(x0 + 130, r1), (x0 + 130, r3)], "grid2", "over")
        self.text(x0 + 3, y0 + 9.2, "Toccata", T_TITLE, bold=True, halo=False)
        self.text(x0 + 65, y0 + 4.4, "도면 이름", T_SMALL - 0.4, cls="tm", halo=False)
        self.text(x0 + 65, y0 + 10.6, self.name, 4.4 if text_w(self.name, 4.4) < 83 else 3.4, bold=True, halo=False)
        self.text(x0 + 153, y0 + 4.4, "도면 번호", T_SMALL - 0.4, cls="tm", halo=False)
        self.text(x0 + 153, y0 + 10.8, "%s / D%02d" % (self.code, n_total), 5.2, bold=True, halo=False)
        self.text(x0 + 3, r1 + 5.6, "뒷부분(L2) + 터치스크린 3판 도면 모음", T_SMALL, halo=False)
        self.text(x0 + 65, r1 + 3.6, "척도 (A2 594×420 출력 기준)", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 65, r1 + 7.3, self.scale_txt, T_SMALL, halo=False)
        self.text(x0 + 133, r1 + 3.6, "단위", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 133, r1 + 7.3, "mm", T_SMALL, halo=False)
        self.text(x0 + 150, r1 + 3.6, "날짜", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 150, r1 + 7.3, DATE, T_SMALL, halo=False)
        self.line([(x0 + 147, r1), (x0 + 147, r2)], "grid2", "over")
        self.text(x0 + 3, r2 + 5.6, "좌표: x 가로(0 = A0 왼쪽 끝) · y 흰 건반 앞 끝에서 뒤로 · z 책상에서 위로", T_SMALL - 0.3, halo=False)
        self.text(x0 + 133, r2 + 3.6, "설계 상태", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 133, r2 + 7.3, STATE, T_SMALL - 0.4, halo=False)
        self.text(x0 + 3, r3 + 3.7, "원본 (모든 선과 숫자는 이 생성기의 입체에서 계산)", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 3, r3 + 7.5, SOURCES, T_SMALL - 0.5, halo=False)
        return (x0, y0, x0 + W, y0 + H)

    def heading(self, x, y, s, sub=None):
        self.text(x, y, s, T_HEAD, bold=True)
        if sub:
            self.text(x + text_w(s, T_HEAD) + 3, y, sub, T_NOTE, cls="tm")

    def check(self):
        """report overlapping text boxes and text outside the sheet (layout aid)."""
        bad = []
        B = self.tboxes
        for i in range(len(B)):
            (a, sa) = B[i]
            if a[0] < 10 or a[1] < 10 or a[2] > self.w - 10 or a[3] > self.h - 10:
                bad.append("outside: %s" % sa)
            for j in range(i + 1, len(B)):
                (b, sb) = B[j]
                if a[0] < b[2] - 0.15 and b[0] < a[2] - 0.15 and a[1] < b[3] - 0.15 and b[1] < a[3] - 0.15:
                    bad.append("overlap: %r / %r" % (sa, sb))
        return bad

    def svg(self):
        W, H = self.w, self.h
        # width / height in mm: printing at 100 % gives true A2, so the 1:x scales on the sheets hold (PNG: svg_to_png)
        s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="0 0 %g %g">' % (W, H, W, H),
             "<title>Toccata %s %s</title>" % (self.code, esc(self.name)),
             "<defs><style>%s</style>%s%s</defs>" % (CSS, DEFS, "".join(self.defs)),
             '<rect class="bg" x="0" y="0" width="%g" height="%g"/>' % (W, H),
             '<rect class="frame" x="10" y="10" width="%g" height="%g"/>' % (W - 20, H - 20)]
        for k in LAYERS:
            s.append('<g id="%s">' % k)
            s.extend(self.L[k])
            s.append("</g>")
        s.append("</svg>")
        return "\n".join(s)


class View:
    """world window (u0, u1, v0, v1) at scale k (sheet mm per world mm), top-left of the window at sheet (X, Y).
    flip: u grows to the left (seen from behind)."""

    def __init__(self, sh, k, win, at, flip=False):
        self.sh, self.k = sh, k
        self.u0, self.u1, self.v0, self.v1 = win
        self.X, self.Y = at
        self.flip = flip
        self.w = k * (self.u1 - self.u0)
        self.h = k * (self.v1 - self.v0)
        sh.views.append(self)
        self.cid = "cv%d" % len(sh.views)
        sh.defs.append('<clipPath id="%s"><rect x="%.3f" y="%.3f" width="%.3f" height="%.3f"/></clipPath>'
                       % (self.cid, self.X, self.Y, self.w, self.h))
        self.ca = ' clip-path="url(#%s)"' % self.cid

    @property
    def rect(self):
        return (self.X, self.Y, self.X + self.w, self.Y + self.h)

    def P(self, u, v):
        return (self.X + self.k * ((self.u1 - u) if self.flip else (u - self.u0)), self.Y + self.k * (self.v1 - v))

    def Px(self, u):
        return self.P(u, self.v0)[0]

    def Py(self, v):
        return self.P(self.u0, v)[1]

    def clip(self):
        return rect_cs(self.u0, self.u1, self.v0, self.v1)

    def path(self, pl):
        out = []
        for p in pl:
            pts = [self.P(u, v) for u, v in p]
            out.append("M" + " L".join("%.2f %.2f" % q for q in pts) + "Z")
        return " ".join(out)

    def area(self, pl, cls, layer="geo"):
        if not pl:
            return
        self.sh.add(layer, '<path class="%s" fill-rule="evenodd" d="%s"%s/>' % (cls, self.path(pl), self.ca))

    def outline(self, pl, cls, layer="over"):
        if not pl:
            return
        self.sh.add(layer, '<path class="%s" d="%s"%s/>' % (cls, self.path(pl), self.ca))

    def seg(self, a, b, cls="thin", layer="over"):
        self.sh.line([self.P(*a), self.P(*b)], cls, layer, self.ca)

    def pline(self, pts, cls="thin", layer="over"):
        self.sh.line([self.P(*q) for q in pts], cls, layer, self.ca)

    def frame(self, cls="thin"):
        self.sh.rect(self.X, self.Y, self.X + self.w, self.Y + self.h, cls, "over")

    def centre_mark(self, u, v, r=2.5, cls="cl"):
        x, y = self.P(u, v)
        self.sh.line([(x - r, y), (x + r, y)], cls, "over")
        self.sh.line([(x, y - r), (x, y + r)], cls, "over")

    def angle(self, c, d0, d1, r, text, size=T_DIM, text_r=None, tpos=None):
        """angle arc at world point c between world directions d0 -> d1 (counter-clockwise in the world), radius r (sheet mm)."""
        x, y = self.P(*c)
        sgn = -1 if self.flip else 1
        a0 = math.atan2(d0[1], d0[0] * sgn)
        a1 = math.atan2(d1[1], d1[0] * sgn)
        if a1 < a0:
            a1 += 2 * math.pi
        if a1 - a0 > math.pi:
            a0, a1 = a1, a0 + 2 * math.pi
        n = 24
        pts = [(x + r * math.cos(a0 + (a1 - a0) * i / n), y - r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        self.sh.line(pts, "dm", "dim")
        self.sh.arrow(pts[0], pts[2], size=1.8)
        self.sh.arrow(pts[-1], pts[-3], size=1.8)
        if tpos is not None:            # 'top-left': just left of the arc end that is highest on the sheet
            e = min((pts[0], pts[-1]), key=lambda q_: q_[1])
            self.sh.text(e[0] - 1.6, e[1] + 1.2, text, size, "end", cls="td")
            return
        am = (a0 + a1) / 2
        tr = text_r if text_r is not None else r + 3.2
        tx, ty = x + tr * math.cos(am), y - tr * math.sin(am)
        anchor = "start" if math.cos(am) > 0.3 else ("end" if math.cos(am) < -0.3 else "middle")
        self.sh.text(tx, ty + 0.35 * size, text, size, anchor, cls="td")


# ------------------------------------------------------------------ model access


class Model:
    def __init__(self, parts):
        self.parts = parts
        self.by = {p.id: p for p in parts}
        self.ka = [p for p in parts if is_ka(p)]
        self.rear = [p for p in parts if not is_ka(p) and p.note not in ("offdesk", "altview")]
        self.alt = [p for p in parts if p.note == "altview"]
        self._bb = {}

    def bb(self, p):
        b = self._bb.get(p.id)
        if b is None:
            b = self._bb[p.id] = tuple(p.solid.bounding_box())
        return b

    def bbox(self, ids):
        bs = [self.bb(self.by[i]) for i in ids]
        return tuple(min(b[i] for b in bs) for i in range(3)) + tuple(max(b[i] for b in bs) for i in range(3, 6))

    def section(self, parts, axis, c, clip=None):
        i = "xyz".index(axis)
        out = []
        for p in parts:
            b = self.bb(p)
            if not (b[i] < c < b[i + 3]):
                continue
            cs = sec(p.solid, axis, c)
            if clip is not None:
                cs = cs ^ clip
            if cs.is_empty() or cs.area() < 1e-4:
                continue
            out.append((p, cs))
        out.sort(key=lambda t: ORDER[mclass(t[0])])
        return out


def draw_section(view, items, labels=None):
    sh = view.sh
    for p, cs in items:
        m = mclass(p)
        sh.used.add(m)
        view.area(polys(cs), "S-" + m)


def painter(view, M, parts, axis, clip=None, key=None, draw=True, cls_prefix="P-"):
    """projections far-to-near; returns {id: (projection, visible part)} (visible = not covered by nearer parts)."""
    i = {"z": 5, "y": 4, "x": 3}[axis]
    key = key or (lambda p: M.bb(p)[i])
    items = []
    for p in parts:
        cs = proj(p.solid, axis)
        if clip is not None:
            cs = cs ^ clip
        if cs.is_empty() or cs.area() < 1e-3:
            continue
        items.append((key(p), ORDER[mclass(p)], p, cs))
    items.sort(key=lambda t: (t[0], t[1]))
    vis = {}
    cover = CrossSection()
    for _, _, p, cs in reversed(items):
        vis[p.id] = (cs, cs - cover)
        cover = cover + cs
    if draw:
        for _, _, p, cs in items:
            m = mclass(p)
            view.sh.used.add(m)
            view.area(polys(cs), cls_prefix + m)
    return vis


def best_inner(cs):
    """inner point of a (possibly multi-piece) cross section: the pole of each connected piece on its own grid, the piece
    with the largest clearance wins. A piece too thin for the grid falls back to a vertex of its inward offset (always
    inside). Returns (u, v, clearance) or None. (A grid over the union of far-apart pieces - e.g. the L and R instances of
    one item - finds no inside point and used to fall back to the vertex mean, between the pieces.)"""
    best = None
    try:
        comps = cs.decompose()
    except Exception:
        comps = [cs]
    for c in comps:
        pl = polys(c)
        if not pl or c.area() < 1e-6:
            continue
        pt = inner_point(pl)
        if pt[2] <= 0:
            pt = None
            for d in (1.0, 0.5, 0.25, 0.1, 0.04, 0.015):
                o = polys(c.offset(-d))
                if o:
                    q = max(o, key=lambda t: abs(signed_area(t)))
                    pt = (float(q[0][0]), float(q[0][1]), d)
                    break
            if pt is None:
                continue
        if best is None or pt[2] > best[2]:
            best = pt
    return best


def point_in(cs, u, v, r=0.3):
    """True when a small disc at (u, v) lies (mostly) inside the cross section."""
    probe = CrossSection.circle(r, 16).translate((u, v))
    return (probe ^ cs).area() > 0.5 * math.pi * r * r


def anchor_of(view, cs):
    pt = best_inner(cs)
    return view.P(pt[0], pt[1]) if pt else None


# ------------------------------------------------------------------ helpers shared by the sheets


def callout_items(view, items, names=None, skip=()):
    """[(p, cs)] -> [(ax, ay, label)] one per distinct short name, anchored in the largest polygon."""
    seen = collections.OrderedDict()
    for p, cs in items:
        if p.id in skip:
            continue
        nm = (names or {}).get(p.id) or short(p.name_ko)
        if nm is None:
            continue
        a = cs.area()
        if nm not in seen or a > seen[nm][0]:
            seen[nm] = (a, cs)
    out = []
    for nm, (a, cs) in seen.items():
        pt = anchor_of(view, cs)
        if pt:
            out.append((pt[0], pt[1], nm))
    return out


class DrawingCheckError(RuntimeError):
    """a drawing failed a self check (e.g. a balloon / leader that does not land on its part)."""


def line_clear(poly_list, q, slope_deg, y_max):
    """vertical clearance of the line through q rising toward -y at slope_deg over the polygon vertices with y <= y_max:
    (min positive = nearest thing below, max negative = nearest thing above)."""
    t = math.tan(math.radians(slope_deg))
    below, above = None, None
    for pl in poly_list:
        for (y, z) in pl:
            if y > y_max + 1e-6:
                continue
            v = q[1] + (q[0] - y) * t - z
            if v > 1e-6:
                if below is None or v < below[0]:
                    below = (v, y, z)
            elif v < -1e-6:
                if above is None or v > above[0]:
                    above = (v, y, z)
    return below, above


def notes_box(sh, x, y, w, title, lines, size=T_NOTE):
    sh.text(x, y, title, T_NOTE + 0.4, bold=True, halo=False)
    yy = y + 2.0
    for ln in lines:
        bullet = not ln.startswith("  ")
        wrapped = sh.wrap(ln.strip(), w - 4, size)
        for i, wl in enumerate(wrapped):
            yy += size * 1.42
            sh.text(x + (0 if (i == 0 and bullet) else 3), yy, ("· " if (i == 0 and bullet) else "") + wl, size, halo=False)
    return yy


# ------------------------------------------------------------------ D02 speaker pod section


def f2(v):
    return "%.2f" % v


def sheet_D02(M):
    import body
    sh = Sheet("D02", "1:1 · 확대 A 5:1")
    xd = body.DRV_X["L"]
    POD = body.POD
    C = body.DRV_YZ
    n = (body.DRIVER_AXIS[1], body.DRIVER_AXIS[2])
    q = body.D(-47.0, 0.0)
    t27 = math.tan(math.radians(27.0))
    c27 = math.cos(math.radians(27.0))
    sh.heading(16, 21, "단면 A-A  (x%s = 왼쪽 스피커 유닛 가운데)" % fnum(xd),
               "1:1 · 오른쪽 끝(+x)에서 본 방향, 연주자는 왼쪽 · 오른쪽 스피커는 x%s 기준 거울 (유닛 x%s)" % (fnum(body.MIRROR_X), fnum(body.DRV_X["R"])))
    # ---- main section A-A
    win = (150.0, 352.0, -3.0, 153.0)
    v = View(sh, 1.0, win, (34.0, 56.0))
    vx0, vy0, vx1, vy1 = v.rect
    v.area([np.array(body.CAVITY)], "air")
    items = M.section(M.rear + M.ka, "x", xd, clip=v.clip())
    draw_section(v, items)
    by = {p.id: cs for p, cs in items}
    v.outline([np.array(body.OUTER)], "vis")
    v.seg((win[0], 0.0), (win[1], 0.0), "vis")
    for i in range(int(win[0]) // 6 * 6 + 6, int(win[1]), 6):
        v.seg((i, 0.0), (i - 3.0, -3.0), "thin")
    v.seg((C[0] - 62 * n[0], C[1] - 62 * n[1]), (C[0] + 46 * n[0], C[1] + 46 * n[1]), "ax")
    v.centre_mark(C[0], C[1], 3.0)
    v.seg(q, (win[0], q[1] + (q[0] - win[0]) * t27), "sound")
    mod_c = POD.sightline_clear((body.MOD_REAR, body.MOD_TOP))
    fl_b, _ = line_clear(polys(by["SPK-L"]), q, 27.0, q[0])
    gk_b, _ = line_clear(polys(by["SPKL-GASKET"]), q, 27.0, q[0])
    _, gr_a = line_clear(polys(by["SPKL-GRILLE"]), q, 27.0, q[0])
    # ordinates
    yo = [body.MOD_REAR, body.Y0, body.SL_A[0], body.DUCT_Y[1], body.RISER[1], C[0], body.SL_B[0], body.TOP_Y0, body.YBI, body.YB]
    sh.ordinates_h([(v.Px(y), vy1, fnum(y)) for y in yo], vy1 + 3, 1, lo=vx0, hi=vx1 + 10)
    sh.text(vx0, vy1 + 3.6, "y (흰 건반 앞 끝 = 0)", T_SMALL, cls="tm")
    zo = [0.0, body.ZB, body.Z_BOT, body.DUCT_Z[1], body.DUCT_Z[1] + body.ROOF_T, body.Z_FB, body.MOD_TOP, C[1], body.SPK_ZT - body.T, body.SPK_ZT]
    sh.ordinates_v([(v.Py(z), None, fnum(z)) for z in zo], vx0 - 1, -1, lo=vy0, hi=vy1 + 2)
    sh.text(vx0 - 1, vy0 - 1.5, "z", T_SMALL, "end", cls="tm")
    yd = vy0 - 6.0
    sh.dim_h(v.Px(body.Y0), v.Px(body.YB), yd, "뒷부분 깊이 %s" % fnum(body.YB - body.Y0),
             ext=[(v.Px(body.Y0), v.Py(body.Z_FB)), (v.Px(body.YB), v.Py(body.SPK_ZT))])
    sh.dim_h(v.Px(body.MOD_REAR), v.Px(body.Y0), yd, fnum(body.Y0 - body.MOD_REAR), ext=[(v.Px(body.MOD_REAR), v.Py(body.MOD_TOP))],
             out_side="left")
    sh.dim_al(v.P(*body.SL_A), v.P(*body.SL_B), 27.0, "앞판 바깥면 %s" % fnum(body.SL_LEN))
    Tp = body.SL_B
    v.seg(Tp, (Tp[0] - 44, Tp[1]), "ex")
    v.angle(Tp, (-math.cos(math.radians(body.ANGLE)), -math.sin(math.radians(body.ANGLE))), (-1.0, 0.0), 30.0,
            "%s°" % fnum(body.ANGLE), text_r=33.5)
    # callouts: pod parts on the right, context / lines on top
    names = {"SPKL-PLY-BACK": "뒤판 (오꾸메 11.5)", "SPKL-PLY-TOP": "윗판 (오꾸메 11.5)", "SPKL-PLY-BOTTOM": "아랫판 (오꾸메 11.5)",
             "SPKL-BAFFLE": "앞판 배플 %s° (출력)" % fnum(body.ANGLE), "SPKL-GRILLE": "육각 그릴 (판 2, 아래 링 벽 없음)",
             "SPKL-DUCTFORMER": "통로 틀: 앞벽·턱·지붕·세움벽 (출력)", "SPKL-GASKET": "EVA 가스켓 3T",
             "SPK-L": "스피커 유닛 CW-100B25 (Ø94 구멍)"}
    rear_items = [(p, cs) for p, cs in items if not is_ka(p)]
    co = callout_items(v, rear_items, names)
    ia = inner_point([np.array(body.CAVITY)])
    vg = body.poly_area(body.CAVITY) * (body.SX1 - body.SX0) / 1e6
    co.append(v.P(ia[0] + 18, ia[1] - 22) + ("안 공간 %s L (폴리에스터 솜)" % fnum(vg, 3),))
    sh.callouts_v(co, vx1 + 12, 1, vy0 - 2, vy1 + 4)
    km = [(p, cs) for p, cs in items if is_ka(p)]
    top_items = []
    if km:
        big = max(km, key=lambda t: t[1].area())
        ax, ay = anchor_of(v, big[1])
        top_items.append((ax, ay, "건반 모듈 O1 (참고)"))
    ys = 168.0
    top_items.append(v.P(ys, q[1] + (q[0] - ys) * t27) + ("27° 소리 길",))
    top_items.append(v.P(C[0] + 40 * n[0], C[1] + 40 * n[1]) + ("유닛 축 (앞판에 수직, 수평에서 %s°)" % fnum(body.TH_V),))
    sh.callouts_h(top_items, vy0 - 17.0, -1, vx0, vx1)
    dA = (205.5, 231.5, 61.0, 85.0)
    p0, p1 = v.P(dA[0], dA[3]), v.P(dA[1], dA[2])
    sh.add("over", '<rect class="ph" x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="2"/>' % (p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1]))
    sh.text(p0[0] - 1.0, p0[1] + 3.2, "A", T_HEAD, "end", bold=True)

    # ---- detail A (5:1)
    va = View(sh, 5.0, dA, (372.0, 40.0))
    ax0, ay0, ax1, ay1 = va.rect
    sh.heading(372, 33, "확대 A", "5:1 · 모듈 뒤 윗모서리와 27° 소리 길")
    itA = M.section(M.rear + M.ka, "x", xd, clip=va.clip())
    draw_section(va, itA)
    va.outline([np.array(body.OUTER)], "vis")
    va.seg(q, (dA[0], q[1] + (q[0] - dA[0]) * t27), "sound")
    va.frame()
    zl = q[1] + (q[0] - body.MOD_REAR) * t27
    xm = va.Px(body.MOD_REAR)
    sh.dim_v(va.Py(body.MOD_TOP), va.Py(zl), xm - 7.0, f2(mod_c), ext=[(xm, va.Py(body.MOD_TOP)), (xm, va.Py(zl))], out_side="down")
    sh.dim_h(va.Px(body.MOD_REAR), va.Px(body.Y0), ay1 - 7, "공기 %s" % fnum(body.Y0 - body.MOD_REAR),
             ext=[(va.Px(body.MOD_REAR), va.Py(body.MOD_TOP)), (va.Px(body.Y0), va.Py(body.Z_FB))], out_side="right")
    marks = [(fl_b, "유닛 플랜지 모서리\n선 아래 %s (수직)" % f2(fl_b[0])),
             (gk_b, "가스켓 모서리\n선 아래 %s (수직)" % f2(gk_b[0])),
             (gr_a, "그릴 판 아래 모서리\n선 위 %s (직각) · %s (수직)" % (f2(-gr_a[0] * c27), f2(-gr_a[0])))]
    co = []
    for (val, yy, zz), lab in marks:
        x, y = va.P(yy, zz)
        sh.line([(x, y), va.P(yy, q[1] + (q[0] - yy) * t27)], "dm", "dim")
        sh.circle(x, y, 0.6, "ah", "dim")
        co.append((x, y, lab))
    co.append((xm, va.Py(body.MOD_TOP), "모듈 뒤 윗모서리 (y%s, z%s)\n선 아래 %s (수직, W1 ≥ 3.0)" % (fnum(body.MOD_REAR), fnum(body.MOD_TOP), f2(mod_c))))
    sh.callouts_v(co, ax1 + 6, 1, ay0, ay1, size=T_NOTE)
    sh.textblock(ax0, ay1 + 5.0, ["주황 점선 = 27° 소리 길: 콘 아래 가장자리 D(−47, 0) = (y%s, z%s)에서 연주자 쪽 위로." % (fnum(q[0]), fnum(q[1])),
                                  "모든 거리는 이 단면 다각형의 꼭짓점에서 잰 값."], T_SMALL, cls="tm")

    # ---- notes
    secA = body.poly_area(body.CAVITY)
    wi = body.SX1 - body.SX0
    IV = body.L2["speakers"]["inner_volume"]
    QA = body.L2["speakers"]["qtc"]
    disp = round(IV["gross_L"] - IV["net_L"], 3)
    m = re.search(r"Qts ([0-9.]+), Vas ([0-9.]+) L", QA["assumption"])
    qts, vas = float(m.group(1)), float(m.group(2))
    vn = vg - disp
    qtc = qts * math.sqrt(1 + vas / vn)
    qf = qts * math.sqrt(1 + vas / (vn * 1.175))
    mc = body.D(0.0, -45.5)
    d14 = math.hypot(mc[0] - body.SENSOR_YZ[0], mc[1] - body.SENSOR_YZ[1])
    meas = body.L2["angle_decision"]["measured_on_solids"]["d14_hall_elements_3d"]
    yN = 262.0
    notes_box(sh, 16, yN, 182, "상자와 앞판 (이 단면의 숫자)", [
        "안 단면 넓이 %s mm² (판 안면 다각형) × 안폭 %s (x%s~%s) = %s L" % ("{:,.0f}".format(secA), fnum(wi), fnum(body.SX0), fnum(body.SX1), fnum(vg, 3)),
        "유닛이 차지하는 %s L를 빼면 %s L (사양 inner_volume.how)" % (fnum(disp, 3), fnum(vn, 3)),
        "Qtc = %s × √(1 + %.1f / %s) = %s · 솜을 채우면 (부피 × 1.175) %s" % (fnum(qts), vas, fnum(vn, 3), f2(qtc), f2(qf)),
        "  Qts %s · Vas %.1f L는 재지 않은 가정 (사양 speakers.qtc)" % (fnum(qts), vas),
        "앞판 바깥면 F(%s, %s) → T(%s, %s), 길이 %s, 수평에서 %s° (수직에서 %s°)" % (fnum(body.SL_A[0]), fnum(body.SL_A[1]), fnum(body.SL_B[0]),
                                                                    fnum(body.SL_B[1]), fnum(body.SL_LEN), fnum(body.ANGLE), fnum(body.TH_V)),
        "유닛 가운데 (x%s / %s, y%s, z%s), 축은 앞판에 수직 (수평에서 %s° 위)" % (fnum(body.DRV_X["L"]), fnum(body.DRV_X["R"]), fnum(C[0]), fnum(C[1]), fnum(body.TH_V)),
        "판: 오꾸메 %s (뒤판·윗판·아랫판·옆판), 앞판·통로 틀·그릴은 출력 PETG" % fnum(body.T),
        "케이블 통로 y%s~%s × z%s~%s (스피커 밑, 책상이 바닥)" % (fnum(body.DUCT_Y[0]), fnum(body.DUCT_Y[1]), fnum(body.DUCT_Z[0]), fnum(body.DUCT_Z[1])),
    ])
    notes_box(sh, 206, yN, 176, "소리 길 27° · D14 (자석 ↔ 홀 센서)", [
        "27° 선: 콘 아래 가장자리 (y%s, z%s)에서 연주자 쪽으로 27° 위" % (fnum(q[0]), fnum(q[1])),
        "모듈 뒤 윗모서리 (y%s, z%s) 위 %s (수직; W1 기준 3.0 + 조립 0.5)" % (fnum(body.MOD_REAR), fnum(body.MOD_TOP), f2(mod_c)),
        "유닛 플랜지 아래 모서리 %s, 가스켓 %s 아래 (40°에서 W1이 2.61 받아들임)" % (f2(fl_b[0]), f2(gk_b[0])),
        "그릴 판 아래 모서리는 선 위 %s (직각) — 그래서 그릴 아래 링 벽 없음" % f2(-gr_a[0] * c27),
        "D14: 자석 중심 D(0, −45.5) = (y%s, z%s) → 홀 소자 줄 (y%s, z%s) %s (같은 x)" % (fnum(mc[0]), fnum(mc[1]), fnum(body.SENSOR_YZ[0]), fnum(body.SENSOR_YZ[1]), fnum(d14, 1)),
        "  3D로 가장 가까운 홀 소자 L %s (%s) / R %s (%s), 기준 100 이상 (check_body 측정)" % (fnum(meas["magnet_centre_L"][0], 1), meas["magnet_centre_L"][1], fnum(meas["magnet_centre_R"][0], 1), meas["magnet_centre_R"][1]),
    ])
    pod = [p for p in M.rear if p.group == body.G_SPK["L"]] + [M.by["SPK-L"]]
    parts_table(sh, 16, 334, pod, M, "스피커 L 한 통의 부품 (R은 x%s 기준 거울)" % fnum(body.MIRROR_X), size=T_SMALL - 0.3, rh=3.55, name_w=96.0)
    sh.legend(392, 214, sh.used, extra=[("air", "안 공기 (솜)"), ("sound", "27° 소리 길"), ("ax", "유닛 축"), ("vis", "옆판 윤곽 (단면 뒤)")])
    sh.scale_bar(392, 330, 1.0, 50, 10, "1:1")
    sh.scale_bar(480, 330, 5.0, 10, 2, "5:1 (확대 A)")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ D05 touchscreen


def own_size(p):
    """a part's own outer size (largest first), not the world bbox of its tilted pose: the print STL (lying on the bed)
    when the part is printed, otherwise the smallest box over rotations about x (every tilted part on D02 / D05 is
    tilted about x: baffle, gasket, grille, inserts, unit, cradle, leg, screws)."""
    if getattr(p, "print_solid", None) is not None:
        b = p.print_solid.bounding_box()
        return sorted([b[3] - b[0], b[4] - b[1], b[5] - b[2]], reverse=True)
    V = np.asarray(p.solid.to_mesh().vert_properties, float)[:, :3]
    ex = float(np.ptp(V[:, 0]))
    Y, Z = V[:, 1], V[:, 2]

    def box(a):
        c, s = math.cos(a), math.sin(a)
        u, w = c * Y + s * Z, -s * Y + c * Z
        return float(np.ptp(u)), float(np.ptp(w))

    angs = np.radians(np.arange(0.0, 90.0, 0.5))
    a0 = min(angs, key=lambda a: box(a)[0] * box(a)[1])
    a1 = min(np.linspace(a0 - math.radians(0.5), a0 + math.radians(0.5), 41), key=lambda a: box(a)[0] * box(a)[1])
    return sorted([ex] + list(box(a1)), reverse=True)


def parts_table(sh, x, y, parts, M, title, size=T_SMALL, rh=4.0, name_w=86.0, extra_note=None):
    """table of (short name, material, the part's own outer size, qty) grouped by name + material."""
    rows = collections.OrderedDict()
    for p in parts:
        dims = own_size(p)
        key = (short(p.name_ko), p.material or "")
        if key in rows:
            rows[key][1] += 1
        else:
            rows[key] = [dims, 1]
    sh.text(x, y, title, T_NOTE + 0.4, bold=True, halo=False)
    body_rows = [[nm, (mat[:22] + "…") if len(mat) > 23 else mat, " × ".join(fnum(d, 1) for d in dims), str(q)] for (nm, mat), (dims, q) in rows.items()]
    return sh.table(x, y + 2.5, [("부품", name_w, "start"), ("재료", 50.0, "start"), ("자기 크기 (기울기 풀어 잼)", 44.0, "start"), ("수량", 12.0, "middle")],
                    body_rows, size=size, rh=rh)


def pose_parts(theta):
    """touchscreen parts at an arbitrary tilt (the heel pose has no part list of its own): the same local builders, TS.place."""
    import body
    import electronics as E
    import touchscreen_rev3 as TS
    from parts import Part
    out = [Part(id="TS-CRADLE@%g" % theta, name_ko="화면 받침(크래들)", name_en="", kind="print", group="터치스크린",
                solid=TS.place(body.cradle_local(), theta), material="PETG"),
           Part(id="TS-E-SCREEN@%g" % theta, name_ko="Waveshare 7-DSI-TOUCH-C", name_en="", kind="electronics", group="터치스크린",
                solid=TS.place(E.screen_local(), theta))]
    return out


def sheet_D05(M):
    import body
    import touchscreen_rev3 as TS
    sh = Sheet("D05", "1:1")
    X = TS.XC
    xe = sum(TS.hinge_x("left", "ear")) / 2.0
    moving = {"TS-CRADLE", "TS-E-SCREEN", "TS-LEG", "TS-WINCOVER", "TS-M3X20-LEG", "TS-C-DSI", "TS-C-PWR-RED", "TS-C-PWR-BLK"} | \
        {"TS-M25-%d" % k for k in range(1, 5)}
    fixed = [p for p in M.rear if p.id not in moving]
    use = [M.by[i] for i in sorted(moving) if i in M.by]
    heel = pose_parts(TS.TILT_HEEL)
    fold = [p for p in M.alt if p.group.startswith("터치스크린")]
    AX = (TS.AX_Y, TS.AX_Z)
    keep = (TS.KEEP_Y, TS.KEEP_Z)
    sh.heading(16, 21, "터치스크린 옆 단면 (x%s = 화면 가운데)" % fnum(X),
               "1:1 · 오른쪽 끝(+x)에서 본 방향, 연주자는 왼쪽 · 점선 = x%s 단면 (왼쪽 경첩 귀·뒤꿈치 멈춤)" % fnum(xe))

    def pose_view(at, win, title, pose, theta, lane_side=1):
        v = View(sh, 1.0, win, at)
        x0, y0, x1, y1 = v.rect
        sh.text(x0, y0 - 3.0, title, T_HEAD - 0.4, bold=True)
        its = M.section(fixed + pose + M.ka, "x", X, clip=v.clip())
        draw_section(v, its)
        # x546.8: lid (hinge cheeks / heel stop), cradle ear, axle - dashed outlines
        for p, cs in M.section(fixed + pose, "x", xe, clip=v.clip()):
            if p.id.startswith("TS-") or p.id == "CU-SCREENLID":
                v.outline(polys(cs), "hidc" if p.id.startswith("TS-") else "hid")
        # keep-out: nothing at y <= 215 while z >= 72.85
        v.pline([(keep[0], 200.0), (keep[0], keep[1]), (win[0], keep[1])], "keep")
        v.centre_mark(AX[0], AX[1], 3.2)
        return v, its

    def pt_label(v, yz, txt):
        x, y = v.P(*yz)
        sh.circle(x, y, 0.7, "ah", "dim")
        return (x, y, txt)

    # ---------------- use 25
    W1 = (200.0, 345.0, 55.0, 197.0)
    vu, its_u = pose_view((34.0, 34.0), W1, "① 사용 %s° (뒤로 기울임, 수직에서)" % fnum(TS.TILT_USE), use, TS.TILT_USE)
    cb = M.bb(M.by["TS-CRADLE"])
    s_, c_ = TS.rot(TS.TILT_USE)
    up = (0.0, 1.0)
    du = TS.world_dir(0, 1, 0, TS.TILT_USE)[1:]
    vu.seg(AX, (AX[0], AX[1] + 70), "ex")
    vu.angle(AX, (du[0], du[1]), up, 52.0, "%s°" % fnum(TS.TILT_USE), tpos="top-left")
    act_u = sum(TS.SC["active_u"]) / 2.0
    ac = TS.pt(act_u, 0.0, TS.TILT_USE)
    gc = TS.pt(TS.GLASS[1] / 2.0, 0.0, TS.TILT_USE)
    leg_a, leg_t = TS.LEG_AX_YZ, TS.LEG_TIP_YZ
    x0, y0, x1, y1 = vu.rect
    sh.ordinates_h([(vu.Px(y), y1, fnum(y)) for y in (212.0, keep[0], cb[1], AX[0], leg_a[0], cb[4], leg_t[0], body.YB)], y1 + 3, 1, lo=x0, hi=x1 + 8)
    sh.ordinates_v([(vu.Py(z), None, fnum(z)) for z in (body.Z_LIDU, body.Z_LID, AX[1], ac[1], cb[5])], x0 - 1, -1, lo=y0, hi=y1)
    co = []
    fr = min((pp for pl in polys(dict((p.id, cs) for p, cs in its_u)["TS-CRADLE"]) for pp in pl), key=lambda t: t[0])
    co.append(pt_label(vu, AX, "경첩 축 M3×20 (y%s, z%s)" % (fnum(AX[0]), fnum(AX[1]))))
    co.append(pt_label(vu, ac, "화면 보이는 영역 가운데 z%s" % fnum(ac[1], 1)))
    co.append(pt_label(vu, leg_a, "받침다리 축 (y%s, z%s)" % (fnum(leg_a[0]), fnum(leg_a[1]))))
    co.append(pt_label(vu, leg_t, "다리 발끝 (y%s, z%s), 수평 아래 %s°" % (fnum(leg_t[0]), fnum(leg_t[1]), fnum(TS.LEG_ANGLE))))
    topp = max((pp for pl in polys(dict((p.id, cs) for p, cs in its_u)["TS-CRADLE"]) for pp in pl), key=lambda t: t[1])
    co.append(pt_label(vu, (topp[0], cb[5]), "가장 높은 곳 z%s (받침 위 끝)" % fnum(cb[5])))
    co.append(pt_label(vu, (cb[1], fr[1]), "가장 앞 y%s (모듈 쪽 지킴선 y%s까지 %s)" % (fnum(cb[1]), fnum(keep[0]), fnum(cb[1] - keep[0]))))
    names = {"TS-CRADLE": "화면 받침 (출력)", "TS-E-SCREEN": "화면 Waveshare 7-DSI-TOUCH-C", "TS-LEG": "받침다리 (출력)",
             "CU-SCREENLID": "화면 뚜껑 (출력, 윗면 z72.85)"}
    for p, cs in its_u:
        if p.id in names:
            ax_, ay_ = anchor_of(vu, cs)
            co.append((ax_, ay_, names[p.id]))
    sh.callouts_v(co, x1 + 10, 1, y0, y1 + 2, size=T_NOTE)

    # ---------------- heel 22
    hb = tuple(heel[0].solid.bounding_box())
    vh, its_h = pose_view((346.0, 34.0), W1, "② 뒤꿈치 %s° (받침다리를 넣고 뺄 때)" % fnum(TS.TILT_HEEL), heel, TS.TILT_HEEL)
    du = TS.world_dir(0, 1, 0, TS.TILT_HEEL)[1:]
    vh.seg(AX, (AX[0], AX[1] + 70), "ex")
    vh.angle(AX, (du[0], du[1]), up, 52.0, "%s°" % fnum(TS.TILT_HEEL), tpos="top-left")
    hx0, hy0, hx1, hy1 = vh.rect
    # note beside the title (outside the view, so the red keep-out line never crosses it)
    t2 = "② 뒤꿈치 %s° (받침다리를 넣고 뺄 때)" % fnum(TS.TILT_HEEL)
    sh.text(hx0 + text_w(t2, T_HEAD - 0.4) + 3.0, hy0 - 3.0, "받침다리는 빼고 그림", T_SMALL, cls="tm")
    hc = tuple(TS.HG["heel_contact_yz"])
    sh.ordinates_h([(vh.Px(y), hy1, fnum(y)) for y in (212.0, keep[0], hb[1], hc[0], AX[0], hb[4])], hy1 + 3, 1, lo=hx0, hi=hx1 + 8)
    sh.ordinates_v([(vh.Py(z), None, fnum(z)) for z in (body.Z_LID, hc[1], AX[1], hb[5])], hx0 - 1, -1, lo=hy0, hi=hy1)
    frh = min((pp for pl in polys(dict((p.id, cs) for p, cs in its_h)[heel[0].id]) for pp in pl), key=lambda t: t[0])
    toph = max((pp for pl in polys(dict((p.id, cs) for p, cs in its_h)[heel[0].id]) for pp in pl), key=lambda t: t[1])
    bkh = max((pp for pl in polys(dict((p.id, cs) for p, cs in its_h)[heel[0].id]) for pp in pl), key=lambda t: t[0])
    co = [pt_label(vh, AX, "경첩 축"),
          pt_label(vh, hc, "뒤꿈치가 멈춤 블록에 닿음 (y%s, z%s)" % (fnum(hc[0]), fnum(hc[1]))),
          pt_label(vh, (toph[0], hb[5]), "가장 높은 곳 z%s" % fnum(hb[5])),
          pt_label(vh, (hb[1], frh[1]), "가장 앞 y%s (지킴선까지 %s)" % (fnum(hb[1]), fnum(hb[1] - keep[0]))),
          pt_label(vh, (hb[4], bkh[1]), "가장 뒤 y%s" % fnum(hb[4]))]
    sh.callouts_v(co, hx1 + 10, 1, hy0, hy1 + 2, size=T_NOTE)

    # ---------------- folded 90
    W3 = (200.0, 345.0, 55.0, 125.0)
    vf, its_f = pose_view((34.0, 226.0), W3, "③ 접은 상태 (운반, 90°)", fold, TS.TILT_FOLD)
    fbb = M.bbox(["TS-CRADLE-FOLD"])
    fpl = np.vstack(polys(dict((p.id, cs) for p, cs in its_f)["TS-CRADLE-FOLD"]))
    fb = (fbb[0], float(fpl[:, 0].min()), float(fpl[:, 1].min()), fbb[3], float(fpl[:, 0].max()), float(fpl[:, 1].max()))
    fs = M.bbox(["TS-E-SCREEN-FOLD"])
    fx0, fy0, fx1, fy1 = vf.rect
    sh.ordinates_h([(vf.Px(y), fy1, fnum(y)) for y in (body.Y0, fb[1], AX[0], fb[4], body.YB)], fy1 + 3, 1, lo=fx0, hi=fx1 + 8)
    sh.ordinates_v([(vf.Py(z), None, fnum(z)) for z in (body.Z_LID, fb[2], AX[1], fs[5], fb[5])], fx0 - 1, -1, lo=fy0 - 6, hi=fy1 + 4)
    co = [pt_label(vf, AX, "경첩 축"),
          pt_label(vf, (fb[4], (fb[2] + fb[5]) / 2), "받침 뒤 끝 y%s → 뒷면 y%s까지 %s" % (fnum(fb[4]), fnum(body.YB), fnum(body.YB - fb[4]))),
          pt_label(vf, ((fb[1] + fb[4]) / 2, fb[5]), "접은 높이 z%s~%s (스피커 윗면 z%s보다 %s 낮음)" % (fnum(fb[2]), fnum(fb[5]), fnum(body.SPK_ZT), fnum(body.SPK_ZT - fb[5]))),
          pt_label(vf, ((fs[1] + fs[4]) / 2, fs[5]), "화면 유리 위로 z%s" % fnum(fs[5]))]
    for p, cs in its_f:
        if p.id == "TS-LEG-FOLD":
            ax_, ay_ = anchor_of(vf, cs)
            co.append((ax_, ay_, "받침다리 (받침 뒤 클립에)"))
    sh.callouts_v(co, fx1 + 10, 1, fy0 - 8, fy1 + 4, size=T_NOTE)

    # ---------------- notes
    notes_box(sh, 346, 222, 236, "터치스크린 3판 핵심 숫자 (입체에서 잼)", [
        "경첩 축 y%s z%s (뚜껑 윗면 z%s + %s), x%s~%s · %s~%s 두 곳" % (fnum(AX[0]), fnum(AX[1]), fnum(body.Z_LID), fnum(AX[1] - body.Z_LID),
                                                         fnum(TS.hinge_x("left", "xr")[0] if False else TS.HG["left_x"][0]), fnum(TS.HG["left_x"][1]),
                                                         fnum(TS.HG["right_x"][0]), fnum(TS.HG["right_x"][1])),
        "사용 %s°: 가장 앞 y%s, 가장 뒤 y%s, 가장 높은 z%s, 보이는 영역 가운데 z%s" % (fnum(TS.TILT_USE), fnum(cb[1]), fnum(cb[4]), fnum(cb[5]), fnum(ac[1], 1)),
        "뒤꿈치 %s°: 가장 앞 y%s, 가장 뒤 y%s, 가장 높은 z%s — 뒤꿈치가 멈춤 블록 (y%s~%s, z%s~%s)에 닿음"
        % (fnum(TS.TILT_HEEL), fnum(hb[1]), fnum(hb[4]), fnum(hb[5]), fnum(TS.HG["heel_block"]["y"][0]), fnum(TS.HG["heel_block"]["y"][1]),
           fnum(TS.HG["heel_block"]["z"][0]), fnum(TS.HG["heel_block"]["z"][1])),
        "접은 상태: 받침 몸 y%s~%s, z%s~%s (x%s 단면; 경첩 귀만 뚜껑 홈 안 z%s까지), 화면 유리 z%s" % (fnum(fb[1]), fnum(fb[4]), fnum(fb[2]), fnum(fb[5]), fnum(X), fnum(fbb[2]), fnum(fs[5])),
        "지킴선 (빨간 점선): 모듈을 위로 빼려면 z%s 위에서는 y%s 앞으로 아무것도 없어야 함 — 모든 자세 통과" % (fnum(keep[1]), fnum(keep[0])),
        "받침다리 %s × %s, 축~발끝 %s, 발은 뚜껑 주머니 바닥 z%s · 뒷벽 y%s에 닿음" % (fnum(TS.LG["section"][0]), fnum(TS.LG["section"][1]), fnum(TS.LEG_LEN_MODEL),
                                                                     fnum(TS.POCKET["bottom_z"]), fnum(TS.POCKET["back_wall_y"])),
        "화면: 유리 %s × %s, 두께 %s, 받침 폭 %s (x%s~%s)" % (fnum(TS.GLASS[0]), fnum(TS.GLASS[1]), fnum(TS.BODY_T), fnum(cb[3] - cb[0]), fnum(cb[0]), fnum(cb[3])),
        "자석 없음 (D14) · 뚜껑은 가운데 유닛 벽·레일에만 얹힘 (M3×10 4개)",
    ])
    ts_parts = [p for p in M.rear if p.group == "터치스크린" and p.kind != "electronics"] + [M.by["CU-SCREENLID"]]
    parts_table(sh, 346, 304, ts_parts, M, "터치스크린 부품 (사용 상태)", name_w=66.0)
    sh.legend(16, 330, sh.used, cols=2, colw=84, extra=[("hidc", "x%s 단면 (경첩 귀)" % fnum(xe)), ("hid", "x%s 단면 (뚜껑)" % fnum(xe)), ("keep", "지킴선 (y215 / z72.85)")])
    sh.scale_bar(200, 398, 1.0, 50, 10, "1:1")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ D03 centre sections


def plate_holes(M, pid, axis, c):
    return hole_list(sec(M.by[pid].solid, axis, c))


def section_planes(M):
    """B: through the bottom-ply intake slot nearest the screen centre (Pi / screen); C: where a back-ply amp vent and a lid-R
    exhaust slot overlap, nearest the amplifier centre."""
    import touchscreen_rev3 as TS
    bb = M.bb(M.by["CU-PLY-BOTTOM"])
    hb = plate_holes(M, "CU-PLY-BOTTOM", "z", (bb[2] + bb[5]) / 2)
    xB = min(hb, key=lambda h: abs(h["cu"] - TS.XC))["cu"]
    bk = M.bb(M.by["CU-PLY-BACK"])
    hk = plate_holes(M, "CU-PLY-BACK", "y", (bk[1] + bk[4]) / 2)
    lr = M.bb(M.by["LID-R"])
    hl = plate_holes(M, "LID-R", "z", (lr[2] + lr[5]) / 2)
    amp = M.bb(M.by["CU-E-AMP"])
    xa = (amp[0] + amp[3]) / 2
    best = None
    for a in hk:
        for b_ in hl:
            lo, hi = max(a["u0"], b_["u0"]), min(a["u1"], b_["u1"])
            if hi - lo > 0.5:
                xm = (lo + hi) / 2
                if best is None or abs(xm - xa) < abs(best - xa):
                    best = xm
    xC = best if best is not None else xa
    return xB, xC


def group_callouts(view, items, names=None):
    """callouts with cables merged into one label and repeated names merged."""
    cab = [(p, cs) for p, cs in items if mclass(p) == "cable"]
    rest = [(p, cs) for p, cs in items if mclass(p) != "cable" and not is_ka(p)]
    co = callout_items(view, rest, names)
    if cab:
        p, cs = max(cab, key=lambda t: t[1].area())
        a = anchor_of(view, cs)
        co.append((a[0], a[1], "케이블 %d가닥 (단면에 잘린 것)" % len(cab)))
    return co


def sheet_D03(M):
    import body
    sh = Sheet("D03", "1:1")
    xB, xC = section_planes(M)
    sh.heading(16, 21, "가운데 유닛 단면 B-B · C-C", "1:1 · 오른쪽 끝(+x)에서 본 방향, 연주자는 왼쪽 · 자르는 자리는 D01 평면에 표시")
    names = {"CU-SCREENLID": "화면 뚜껑 (출력, 판 3 + 갈비)", "LID-R": "뚜껑 R (오꾸메, 배기 홈)", "CU-PLY-BOTTOM": "아랫판 (오꾸메, 흡기 홈)",
             "CU-PLY-BACK": "뒤판 (오꾸메)", "TS-CRADLE": "화면 받침", "TS-LEG": "받침다리", "TS-E-SCREEN": "화면 Waveshare 7\"",
             "FOOT-06": "고무발 28×5", "FOOT-09": "고무발 28×5"}
    out = {}
    for tag, xs, win, at in (("B", xB, (160.0, 350.0, -3.0, 193.0), (32.0, 40.0)), ("C", xC, (160.0, 350.0, -3.0, 80.0), (32.0, 282.0))):
        v = View(sh, 1.0, win, at)
        x0, y0, x1, y1 = v.rect
        what = "Pi 5 · 화면 (아랫판 흡기 홈 가운데)" if tag == "B" else "허브 · 앰프 (뒤판 환기 홈과 뚜껑 R 배기 홈이 겹치는 곳)"
        sh.text(x0, y0 - 3.5, "단면 %s-%s  x%s — %s" % (tag, tag, fnum(xs), what), T_HEAD - 0.6, bold=True)
        its = M.section(M.rear + M.ka, "x", xs, clip=v.clip())
        draw_section(v, its)
        v.seg((win[0], 0.0), (win[1], 0.0), "vis")
        for i in range(int(win[0]) // 6 * 6 + 6, int(win[1]), 6):
            v.seg((i, 0.0), (i - 3.0, -3.0), "thin")
        by = dict((p.id, cs) for p, cs in its)
        # ordinates from what is cut
        ys = {body.MOD_REAR, body.Y0, body.DUCT_Y[1], body.YBI, body.YB}
        zs = {0.0, body.ZB, body.Z_BOT, body.Z_LIDU, body.Z_LID}
        if tag == "B":
            cb = M.bb(M.by["TS-CRADLE"])
            pi = M.bb(M.by["CU-E-PI5"])
            ys |= {cb[1], pi[1], pi[4]}
            zs |= {pi[2], pi[5], cb[5]}
        else:
            hub, amp, shf = M.bb(M.by["PB-E-HUB"]), M.bb(M.by["CU-E-AMP"]), M.bb(M.by["PR-HUBSHELF"])
            ys |= {hub[1], amp[1]}
            zs |= {hub[5], amp[2], amp[5]}
            for h in plate_holes(M, "CU-PLY-BACK", "y", body.YB - body.T / 2):
                if h["u0"] < xs < h["u1"]:
                    zs |= {h["v0"], h["v1"]}
            for h in plate_holes(M, "LID-R", "z", body.Z_LID - body.T / 2):
                if h["u0"] < xs < h["u1"]:
                    ys |= {h["v0"], h["v1"]}
        sh.ordinates_h([(v.Px(y), y1, fnum(y)) for y in sorted(ys)], y1 + 3, 1, lo=x0, hi=x1 + 8)
        sh.ordinates_v([(v.Py(z), None, fnum(z)) for z in sorted(zs)], x0 - 1, -1, lo=y0 - 4, hi=y1 + 3)
        co = group_callouts(v, its, names)
        sh.callouts_v(co, x1 + 10, 1, y0 - 4, y1 + 4, size=T_NOTE)
        out[tag] = (xs, v, by)
    # ---- notes (vents and gaps from the solids)
    def area_sum(pid, axis, c):
        return sum(h["area"] for h in plate_holes(M, pid, axis, c))
    bb = M.bb(M.by["CU-PLY-BOTTOM"])
    intake = area_sum("CU-PLY-BOTTOM", "z", (bb[2] + bb[5]) / 2)
    ex_l = area_sum("LID-L", "z", body.Z_LID - body.T / 2)
    ex_r = area_sum("LID-R", "z", body.Z_LID - body.T / 2)
    sl_holes = [h for h in plate_holes(M, "CU-SCREENLID", "z", body.Z_LID - 1.5) if h["w"] > 20 or h["h"] > 20]
    sl_slots = [h for h in sl_holes if min(h["w"], h["h"]) < 5.0]            # 4-wide exhaust slots
    sl_other = [h for h in sl_holes if min(h["w"], h["h"]) >= 5.0]           # 22 x 6 ribbon / power-wire hole
    ex_s = sum(h["area"] for h in sl_slots)
    ex_rib = sum(h["area"] for h in sl_other)
    ex_b = area_sum("CU-PLY-BACK", "y", body.YB - body.T / 2)
    bp = M.bb(M.by["PR-BACKPLATE"])
    louv = sum(h["area"] for h in plate_holes(M, "PR-BACKPLATE", "y", body.YB - 1.0) if h["w"] > 30)
    amp = M.bb(M.by["CU-E-AMP"])
    hub = M.bb(M.by["PB-E-HUB"])
    pi = M.bb(M.by["CU-E-PI5"])
    lines = [
        "뚜껑 윗면 z%s = 건반 윗면과 같은 높이, 뚜껑 밑면 z%s (안 높이 z%s~%s = %s)" % (fnum(body.Z_LID), fnum(body.Z_LIDU), fnum(body.Z_BOT), fnum(body.Z_LIDU), fnum(body.Z_LIDU - body.Z_BOT)),
        "앞 공간 y%s~%s는 앞벽 없이 케이블 통로 (z%s~%s)와 이어짐 — 뚜껑을 열면 모듈 USB-C를 위에서 잡음" % (fnum(body.Y0), fnum(body.DUCT_Y[1]), fnum(body.DUCT_Z[0]), fnum(body.DUCT_Z[1])),
        "Pi 5 x%s~%s, z%s~%s → 뚜껑 밑면까지 %s" % (fnum(pi[0]), fnum(pi[3]), fnum(pi[2]), fnum(pi[5]), fnum(body.Z_LIDU - pi[5])),
        "허브 z%s~%s, 선반 위 앰프 z%s~%s → 뚜껑 밑면까지 %s" % (fnum(hub[2]), fnum(hub[5]), fnum(amp[2]), fnum(amp[5]), fnum(body.Z_LIDU - amp[5])),
        "흡기: 아랫판 홈 합 %s mm² (고무발 %s mm 틈으로) + 뒤판 출력물 루버 %s mm²" % ("{:,.0f}".format(intake), fnum(body.ZB), "{:,.0f}".format(louv)),
        "배기 (홈만): 뚜껑 L %s + 화면 뚜껑 홈 %s + 뚜껑 R %s + 뒤판 앰프 뒤 %s = %s mm²" % ("{:,.0f}".format(ex_l), "{:,.0f}".format(ex_s), "{:,.0f}".format(ex_r), "{:,.0f}".format(ex_b), "{:,.0f}".format(ex_l + ex_s + ex_r + ex_b)),
    ]
    if sl_other:
        lines.append("  화면 뚜껑의 리본·전원선 구멍 %s (%s mm²)은 선이 지나는 구멍이라 배기 합에 넣지 않음"
                     % (" · ".join("%s×%s" % (fnum(h["w"], 1), fnum(h["h"], 1)) for h in sl_other), "{:,.0f}".format(ex_rib)))
    for pid, axis, c, nm in (("CU-PLY-BOTTOM", "z", (bb[2] + bb[5]) / 2, "아랫판 흡기 홈 (x, y)"), ("LID-L", "z", body.Z_LID - body.T / 2, "뚜껑 L 배기 홈 (x, y)"),
                             ("LID-R", "z", body.Z_LID - body.T / 2, "뚜껑 R 배기 홈 (x, y)"), ("CU-PLY-BACK", "y", body.YB - body.T / 2, "뒤판 환기 홈 (x, z)")):
        hs = plate_holes(M, pid, axis, c)
        hs = [h for h in hs if not (pid == "CU-PLY-BACK" and h["w"] > 100)]
        for t in pattern_text(hs):
            lines.append(nm + ": " + t)
        if pid == "LID-L" and sl_slots:
            for t in pattern_text(sl_slots):
                lines.append("화면 뚜껑 배기 홈 (x, y): " + t)
    yk = notes_box(sh, 352, 40, 228, "가운데 유닛 (입체에서 잰 숫자)", lines)
    # key plan: where B-B and C-C cut (plan, lids off)
    kp = View(sh, 0.25, (250.0, 972.0, 205.0, 346.0), (370.0, yk + 22.0))
    sh.text(352, yk + 12.0, "자르는 자리 (평면, 뚜껑 뗌)", T_NOTE + 0.4, bold=True, halo=False)
    sh.text(352 + text_w("자르는 자리 (평면, 뚜껑 뗌)", T_NOTE + 0.4) + 3, yk + 12.0, "1:4 · 연주자는 아래쪽", T_SMALL, cls="tm", halo=False)
    painter(kp, M, plan_parts(M, cables=False), "z", clip=kp.clip())
    kx0, ky0, kx1, ky1 = kp.rect
    for tag, xs in (("B", xB), ("C", xC)):
        a_, b2 = kp.P(xs, body.Y0 - 6), kp.P(xs, body.YB + 6)
        sh.line([a_, b2], "secl", "over")
        for (px, py) in (a_, b2):
            sh.line([(px, py), (px - 3.5, py)], "secl", "over")
            sh.arrow((px - 4.0, py), (px - 0.8, py), size=1.6, layer="over", cls="seca")
        sh.text(a_[0] + 1.2, a_[1] + 3.6, "%s  x%s" % (tag, fnum(xs)), T_SMALL + 0.2, bold=True)
    sh.legend(352, max(250, ky1 + 16), sh.used, cols=1)
    sh.scale_bar(352, 352, 1.0, 50, 10, "1:1")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ D04 rear elevation


BP_NAMES = {"cable_pass": "케이블 통과 (보조배터리 선)", "usb_c_pd_input": "USB-C PD 입력 (HUSB238)",
            "rocker": "로커 스위치 KCD1", "pedal_jack": "페달 잭 J501"}


def sheet_D04(M):
    import body
    sh = Sheet("D04", "1:2.5 · 확대 2:1")
    sh.heading(16, 21, "뒷면 입면 (뒤에서 봄, 오른쪽 스피커가 왼쪽에 보임)", "1:2.5")
    k = 1 / 2.5
    win = (-22.0, 1244.0, -3.0, 196.0)
    v = View(sh, k, win, (52.0, 52.0), flip=True)
    x0, y0, x1, y1 = v.rect
    parts = [p for p in M.rear]
    vis = painter(v, M, parts, "y")
    v.seg((win[0], 0.0), (win[1], 0.0), "vis")
    for i in range(int(win[0]) // 10 * 10 + 10, int(win[1]), 10):
        v.seg((i, 0.0), (i + 4.0, -3.0), "thin")
    # dims above: chain + overall
    L, R = body.SPK_X["L"], body.SPK_X["R"]
    cu = body.CU_X
    zt = body.SPK_ZT
    yA, yB_ = y0 - 6, y0 - 13
    chain = [L[0], L[1], cu[0], cu[1], R[0], R[1]]
    tops = {L[0]: zt, L[1]: zt, cu[0]: body.Z_LIDU, cu[1]: body.Z_LIDU, R[0]: zt, R[1]: zt}
    for a, b_ in zip(chain[:-1], chain[1:]):
        sh.dim_h(v.Px(a), v.Px(b_), yA, fnum(b_ - a), ext=[(v.Px(a), v.Py(tops[a])), (v.Px(b_), v.Py(tops[b_]))],
                 out_side="left" if (b_ - a) < 10 and a < 611 else "right")
    sh.dim_h(v.Px(L[0]), v.Px(R[1]), yB_, "전체 폭 %s" % fnum(R[1] - L[0]), ext=[(v.Px(L[0]), yA), (v.Px(R[1]), yA)])
    # z ordinates (left side = +x end)
    cb = M.bb(M.by["TS-CRADLE"])
    zs = [0.0, body.ZB, body.Z_LIDU, body.Z_LID, zt, cb[5]]
    sh.ordinates_v([(v.Py(z), None, fnum(z)) for z in zs], x0 - 2, -1, lo=y0 - 2, hi=y1 + 2)
    sh.text(x0 - 3, y0 - 3, "z", T_SMALL, "end", cls="tm")
    # callouts below
    names = {"SPKL-PLY-BACK": "스피커 L 뒤판", "SPKR-PLY-BACK": "스피커 R 뒤판", "CU-PLY-BACK": "가운데 유닛 뒤판 (오꾸메)",
             "PR-BACKPLATE": "뒤판 출력물 (I/O·루버)", "TS-CRADLE": "화면 받침 (뒷면)", "TS-LEG": "받침다리",
             "SPKL-PLY-SIDEOUT": "스피커 L 바깥 옆판", "SPKR-PLY-SIDEOUT": "스피커 R 바깥 옆판"}
    co = []
    for pid, nm in names.items():
        if pid in vis:
            cs = vis[pid][1]
            if cs.is_empty():
                continue
            a = anchor_of(v, cs)
            co.append((a[0], a[1], nm))
    # back-ply vents
    hk = [h for h in plate_holes(M, "CU-PLY-BACK", "y", body.YB - body.T / 2) if h["w"] < 100]
    if hk:
        h = hk[len(hk) // 2]
        co.append(v.P(h["cu"], h["v1"]) + ("앰프 뒤 환기 홈 %s×%s ×%d" % (fnum(hk[0]["w"]), fnum(hk[0]["h"]), len(hk)),))
    foots = [p for p in M.rear if p.id.startswith("FOOT-")]
    if foots:
        f = min(foots, key=lambda p: -M.bb(p)[0])
        b = M.bb(f)
        co.append(v.P((b[0] + b[3]) / 2, b[5] / 2) + ("고무발 28×5 (%d개)" % len(foots),))
    sh.callouts_h(co, y1 + 14, 1, x0, x1, size=T_NOTE)
    # back plate frame on the elevation
    bp = M.bb(M.by["PR-BACKPLATE"])
    p0, p1 = v.P(bp[3] + 3, bp[5] + 3), v.P(bp[0] - 3, bp[2] - 3)
    sh.add("over", '<rect class="ph" x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1.5"/>' % (p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1]))
    sh.text(p0[0] - 1, p0[1] - 1.2, "B", T_HEAD - 0.6, "end", bold=True)

    # ---- enlarged back plate (2:1) - seen from behind
    k2 = 2.0
    w2 = (bp[0] - 6, bp[3] + 6, bp[2] - 6, bp[5] + 6)
    v2 = View(sh, k2, w2, (60.0, 192.0), flip=True)
    a0, b0, a1, b1 = v2.rect
    sh.text(a0, b0 - 16.0, "확대 B — 뒤판 출력물 I/O 판 (뒤에서 봄)", T_HEAD - 0.6, bold=True)
    ycut = body.YB - 1.0
    sh.text(a0 + text_w("확대 B — 뒤판 출력물 I/O 판 (뒤에서 봄)", T_HEAD - 0.6) + 3, b0 - 16.0,
            "2:1 · 뒷면 y%s에서 %s mm 안을 자른 단면 + 구멍 뒤로 보이는 부품" % (fnum(body.YB), fnum(body.YB - ycut)), T_NOTE, cls="tm")
    near = [p for p in M.rear if M.bb(p)[4] > 300 and p.id not in ("PR-BACKPLATE", "CU-PLY-BACK")]
    painter(v2, M, [p for p in near if M.bb(p)[4] <= ycut], "y", clip=v2.clip())
    its = M.section([M.by["PR-BACKPLATE"], M.by["CU-PLY-BACK"]], "y", ycut, clip=v2.clip())
    draw_section(v2, its)
    painter(v2, M, [p for p in near if M.bb(p)[4] > ycut], "y", clip=v2.clip())
    v2.frame()
    skin = body.BP_SKIN
    holes = plate_holes(M, "PR-BACKPLATE", "y", body.YB - skin / 2)
    behind = plate_holes(M, "PR-BACKPLATE", "y", body.YB - skin - 0.6)
    spec = body.BP["holes_xz"]
    co2, xo, zo, rows = [], set(), set(), []
    louv = [h for h in holes if h["w"] > 30]

    def sz(h):
        return ("Ø%s" % fnum(h["d"], 1)) if h["round"] else ("%s × %s" % (fnum(h["w"], 1), fnum(h["h"], 1)))

    for h in sorted([h for h in holes if h not in louv], key=lambda h: h["cu"]):
        key = min(spec, key=lambda kk: math.hypot(spec[kk][0] - h["cu"], spec[kk][1] - h["cv"]))
        nm = next((vv for kk, vv in BP_NAMES.items() if key.startswith(kk)), key)
        bh = next((g for g in behind if math.hypot(g["cu"] - h["cu"], g["cv"] - h["cv"]) < 1.0), None)
        x, y = v2.P(h["cu"], h["v1"])
        co2.append((x, y, "%s %s" % (nm.split(" (")[0], sz(h))))
        xo.add(round(h["cu"], 2))
        zo.add(round(h["cv"], 2))
        v2.centre_mark(h["cu"], h["cv"], 0.5 * k2 * max(h["w"], h["h"]) + 2.0)
        if bh is not None and (abs(bh["w"] - h["w"]) > 0.05 or abs(bh["h"] - h["h"]) > 0.05):
            inner = "%s (바깥 %s 깊이 오목 자리 뒤)" % (sz(bh), fnum(skin))
        else:
            inner = "관통 (판 두께 그대로)"
        what = [p.id for p in near if p.kind == "electronics" and M.bb(p)[0] < h["cu"] < M.bb(p)[3] and M.bb(p)[2] < h["cv"] < M.bb(p)[5]]
        rows.append([nm, sz(h), inner, fnum(h["cu"], 2), fnum(h["cv"], 2), ", ".join(short(M.by[i].name_ko) for i in what[:2]) or "-"])
    if louv:
        lz = sorted(h["cv"] for h in louv)
        h = louv[0]
        x, y = v2.P((h["u0"] + h["u1"]) / 2, max(hh["v1"] for hh in louv))
        co2.append((x, y, "루버 %s ×%d" % (sz(h), len(louv))))
        xo |= {round(h["u0"], 2), round(h["u1"], 2)}
        rows.append(["루버 (강압 컨버터 뒤 흡기)", "%s ×%d" % (sz(h), len(louv)), "관통", "%s~%s" % (fnum(h["u0"]), fnum(h["u1"])),
                     "%s~%s, 간격 %s" % (fnum(lz[0], 2), fnum(lz[-1], 2), fnum(lz[1] - lz[0], 2) if len(lz) > 1 else "-"), "강압 컨버터"])
    sh.callouts_h(co2, b0 - 5.0, -1, a0, a1, size=T_NOTE)
    xo |= {round(bp[0], 2), round(bp[3], 2)}
    zo |= {round(bp[2], 2), round(bp[5], 2)}
    sh.ordinates_h([(v2.Px(x), b1, fnum(x)) for x in sorted(xo)], b1 + 3, 1, lo=a0, hi=a1)
    sh.text(a1 + 2, b1 + 3.6, "x", T_SMALL, cls="tm")
    sh.ordinates_v([(v2.Py(z), None, fnum(z)) for z in sorted(zo)], a0 - 2, -1, lo=b0, hi=b1)
    sh.text(16, 333, "I/O 판 구멍 (판 단면에서 잼, 뒤판 바깥면 y%s 기준)" % fnum(body.YB), T_NOTE + 0.4, bold=True, halo=False)
    sh.table(16, 335.5, [("구멍", 62.0, "start"), ("바깥면 크기", 28.0, "start"), ("안쪽", 62.0, "start"), ("중심 x", 22.0, "start"),
                         ("중심 z", 34.0, "start"), ("뒤에 있는 부품", 150.0, "start")], rows, size=T_SMALL, rh=4.3)
    sh.legend(392, 200, sh.used, cols=1)
    sh.scale_bar(392, 300, k, 200, 50, "1:2.5")
    sh.scale_bar(392, 314, k2, 40, 10, "2:1")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ D01 plan

D01_ITEMS = [
    (r"CU-PLY-END-[LR]$", "가운데 유닛 끝벽 L·R (ㄴ자, 오꾸메)"), (r"CU-PLY-BOTTOM$", "가운데 유닛 아랫판 (흡기 홈)"),
    (r"CU-PLY-BACK$", "가운데 유닛 뒤판 (I/O 창, 환기 홈)"), (r"SEAM-POSTRAIL-\d$", None), (r"SEAM-INS-\d$|CU-M3X10-\d$", "화면 뚜껑 나사 자리 (M3 인서트 + M3×10)"),
    (r"CU-MAG-PLY-", "뚜껑 자석 Ø8×3 (합판 쪽)"), (r"PB-E-BANK$", None), (r"CU-PBHOLDER$", None), (r"PR-BACKPLATE$", None),
    (r"CU-E-FUSE$", None), (r"CU-FUSECRADLE$", None), (r"CU-E-SWITCH$", None), (r"CU-E-PDTRIG$", None),
    (r"CU-E-J501BOARD$|CU-E-J501$", None), (r"CU-E-PEDBOARD$", None), (r"CU-E-PEDZERO$", None), (r"CU-E-BUCK$", None),
    (r"CU-E-J702BOARD$|CU-E-J702$", None), (r"CU-E-PI5$", None), (r"CU-E-PI5-.+", "Pi 5 포트 (RJ45·USB-A·DISP1)"),
    (r"CU-E-GENDER$", None), (r"CU-E-DONGLE$", None), (r"PB-E-HUB$", None), (r"PR-HUBSHELF$", None), (r"CU-E-AMP$", None),
    (r"CU-POST-", "보드 받침 기둥 (출력)"), (r"XT30-CLIP-[LR]$", None), (r"C-XT30", "XT30 커넥터 짝 L·R (스피커 선)"),
    (r"JOIN-TS-", None), (r"JOIN-SLV-", None), (r"JOIN-EVA-", "EVA 3T 띠 (스피커 ↔ 가운데 틈)"), (r"CABLE-CLIP-E", None),
    (r"^C-USB-|^O\d-C-USB|^C-PWR|^C-SPK", "케이블 (USB·전원·스피커)"),
]
BAY_KO = {"power_bank": "보조배터리", "io_ped_fuse": "I/O·페달·퓨즈", "buck_j702": "강압·J702", "pi_dongle": "Pi 5·동글",
          "hub_amp_shelf": "허브·앰프·선반"}
LID_IDS = ("LID-L", "LID-R", "CU-SCREENLID")


def plan_parts(M, cables=True):
    out = []
    for p in M.rear:
        if p.id in LID_IDS or p.id.startswith("CU-MAG-LID") or p.group == "터치스크린":
            continue
        if not cables and mclass(p) == "cable":
            continue
        out.append(p)
    return out


def sheet_D01(M):
    import body
    import touchscreen_rev3 as TS
    sh = Sheet("D01", "1:2.5 · 가운데 확대 1:1.5")
    xB, xC = section_planes(M)
    # ---------------- overall plan
    k1 = 1 / 2.5
    win = (-24.0, 1246.0, 150.0, 346.0)
    v = View(sh, k1, win, (40.0, 54.0))
    x0, y0, x1, y1 = v.rect
    sh.heading(16, 21, "전체 평면 (위에서 봄) — 뚜껑과 화면을 뗀 모습", "1:2.5 · 연주자는 아래쪽 · 숨은 선(점선) = 스피커·바닥 밑")
    frames = [p for p in M.ka if p.group.endswith("프레임")]
    painter(v, M, frames, "z", clip=rect_cs(win[0], win[1], win[2], body.MOD_REAR + 0.01))
    pp = plan_parts(M, cables=False)
    vis1 = painter(v, M, pp, "z", clip=v.clip())
    # hidden: duct, feet, brackets, sockets
    v.outline([np.array([(win[0] + 6, body.DUCT_Y[0]), (win[1] - 6, body.DUCT_Y[0]), (win[1] - 6, body.DUCT_Y[1]), (win[0] + 6, body.DUCT_Y[1])])], "hid")
    hidden_ids = [p.id for p in M.rear if p.id.startswith(("FOOT-", "BRK2-L", "BRK2-R", "POD-SOCKET", "DUCT-CAP"))]
    for i in hidden_ids:
        p = M.by[i]
        if p.kind == "bought" and not i.startswith("FOOT"):
            continue
        v.outline(polys(proj(p.solid, "z")), "hid")
    # screen footprint (use pose)
    scr = proj(M.by["TS-CRADLE"].solid, "z") + proj(M.by["TS-E-SCREEN"].solid, "z")
    v.outline(polys(scr), "ph")
    # lid seams + centre line
    seams = (M.bb(M.by["LID-L"])[3], M.bb(M.by["LID-R"])[0])
    for xs in seams:
        v.seg((xs, body.Y0), (xs, body.YB), "cl")
    v.seg((body.MIRROR_X, body.MOD_REAR - 20), (body.MIRROR_X, body.YB + 3), "cl")
    # section markers
    xd = body.DRV_X["L"]
    for xs, lab in ((xd, "A"), (xB, "B"), (xC, "C")):
        a, b_ = v.P(xs, body.Y0 - 4), v.P(xs, body.YB + 3)
        sh.line([a, b_], "cl", "over")
        for (px, py), dy in ((a, 1), (b_, -1)):
            sh.line([(px, py), (px - 4.0, py)], "secl", "over")
            sh.arrow((px - 4.6, py), (px - 1.0, py), size=1.8, layer="over", cls="seca")
        sh.text(a[0] + 1.2, a[1] + 3.6, lab, T_LAB, bold=True)
    sh.text(v.Px(TS.XC) + 1.2, v.Py(body.Y0 - 4) + 7.6, "D (x%s)" % fnum(TS.XC), T_SMALL, cls="tm")
    # pins (from the bracket solids: the D6 pin section)
    pins = []
    for side in "LR":
        pb = M.bb(M.by["BRK2-" + side])
        cs = sec(M.by["BRK2-" + side].solid, "z", pb[5] - 1.0)
        pl = [q for q in polys(cs) if signed_area(q) > 0]
        if pl:
            q = min(pl, key=lambda t: abs(signed_area(t) - math.pi * 9))
            pins.append(((q[:, 0].min() + q[:, 0].max()) / 2, (q[:, 1].min() + q[:, 1].max()) / 2))
    feet = [p for p in M.rear if p.id.startswith("FOOT-")]
    fc = sorted(set((round((M.bb(p)[0] + M.bb(p)[3]) / 2, 2), round((M.bb(p)[1] + M.bb(p)[4]) / 2, 2)) for p in feet))
    # dims top: chain + overall
    L, R, cu = body.SPK_X["L"], body.SPK_X["R"], body.CU_X
    chain = [L[0], L[1], cu[0], cu[1], R[0], R[1]]
    ya, yb_ = y0 - 5.0, y0 - 11.0
    for a, b_ in zip(chain[:-1], chain[1:]):
        sh.dim_h(v.Px(a), v.Px(b_), ya, fnum(b_ - a), ext=[(v.Px(a), y0), (v.Px(b_), y0)], out_side="left" if (b_ - a) < 10 and a < 611 else "right")
    sh.dim_h(v.Px(L[0]), v.Px(R[1]), yb_, "전체 폭 %s" % fnum(R[1] - L[0]), ext=[(v.Px(L[0]), ya), (v.Px(R[1]), ya)])
    # bottom x ordinates
    xs_ = sorted(set([round(pq[0], 2) for pq in pins] + [f[0] for f in fc] + [body.DRV_X["L"], body.DRV_X["R"], body.MIRROR_X] + list(seams)))
    sh.ordinates_h([(v.Px(x), None, fnum(x)) for x in xs_], y1 + 2.0, 1, lo=x0, hi=x1)
    sh.text(x0 - 2, y1 + 3.5, "x", T_SMALL, "end", cls="tm")
    # right y ruler
    ys_ = sorted(set([body.MOD_REAR, body.Y0, body.DUCT_Y[1], body.YB] + [f[1] for f in fc] + [round(pq[1], 2) for pq in pins]))
    sh.ordinates_v([(v.Py(y), None, fnum(y)) for y in ys_], x1 + 1.0, 1, lo=y0 - 3, hi=y1 + 3)
    sh.text(x1 + 1.0, y0 - 3.5, "y", T_SMALL, cls="tm")
    # callouts above
    co = []
    def vis_anchor(pid):
        cs = vis1[pid][1]
        a = anchor_of(v, cs if not cs.is_empty() else vis1[pid][0])
        return a
    co.append(vis_anchor("SPKL-PLY-TOP") + ("스피커 L (윗면 z%s)" % fnum(body.SPK_ZT),))
    co.append(vis_anchor("SPKR-GRILLE") + ("스피커 R (앞판 %s°, 그릴)" % fnum(body.ANGLE),))
    co.append(vis_anchor("PB-E-BANK") + ("가운데 유닛 (뚜껑 뗌) → 아래 확대",))
    co.append(v.P(seams[0], body.Y0 + 70) + ("뚜껑 이음 x%s · x%s" % (fnum(seams[0]), fnum(seams[1])),))
    sp = inner_point(polys(scr))
    co.append(v.P(sp[0] + 40, body.Y0 + 6) + ("화면 사용 25° 투영 (가는 1점 쇄선)",))
    co.append(v.P(60.0, body.DUCT_Y[0] + 1) + ("케이블 통로 y%s~%s (숨은 선)" % (fnum(body.DUCT_Y[0]), fnum(body.DUCT_Y[1])),))
    fl = max(feet, key=lambda p: M.bb(p)[0])
    fb_ = M.bb(fl)
    co.append(v.P(fb_[3] - 2, (fb_[1] + fb_[4]) / 2) + ("고무발 28×5 ×%d (숨은 선)" % len(feet),))
    if pins:
        co.append(v.P(pins[0][0], pins[0][1]) + ("볼 브래킷 핀 L 둥근 / R 긴 구멍 (숨은 선)",))
    sh.callouts_h(co, y0 - 19.0, -1, x0, x1, size=T_NOTE)
    sh.text(v.Px(300), v.Py(181), "건반 모듈 O1~O7 + 끝 부속 (참고, 뒷벽 y%s까지)" % fnum(body.MOD_REAR), T_NOTE, "start", cls="tm")

    # ---------------- centre enlarged
    k2 = 1 / 1.5
    w2 = (252.0, 970.0, 206.0, 346.0)
    v2 = View(sh, k2, w2, (40.0, 196.0))
    a0, b0, a1, b1 = v2.rect
    bay_tags = [k.split("_", 1)[0] for k in body.CE["bays_x"]]
    gone = [chr(c) for c in range(ord(min(bay_tags)), ord(max(bay_tags)) + 1) if chr(c) not in bay_tags]
    sh.heading(16, 172, "가운데 유닛 확대 (뚜껑·화면을 뗀 모습)", "1:1.5 · 번호는 아래 표"
               + (" · 칸 %s(예비 건반 보관 칸, R29)는 2026-10-02에 뺌 — 칸 이름은 사양 그대로" % "·".join(gone) if gone == ["C"] else ""))
    pp2 = plan_parts(M, cables=True)
    vis2 = painter(v2, M, pp2, "z", clip=v2.clip())
    for xs in seams:
        v2.seg((xs, body.Y0 - 2), (xs, body.YB + 2), "cl")
    for xs, lab in ((xB, "B"), (xC, "C")):
        v2.seg((xs, body.Y0 - 3), (xs, body.YB + 3), "cl")
        px, py = v2.P(xs, w2[2] + 1.5)
        sh.text(px + 1.0, py, lab, T_LAB, bold=True)
    # bay zone bar (spec centre.bays_x)
    zb0, zb1 = b0 - 9.0, b0 - 3.0
    for key, (xa, xb) in body.CE["bays_x"].items():
        tag, nm = key.split("_", 1)
        pa, pb2 = v2.Px(xa), v2.Px(xb)
        sh.rect(pa, zb0, pb2, zb1, "zone", "over")
        sh.text((pa + pb2) / 2, zb1 - 1.4, "%s %s · %s" % (tag, BAY_KO.get(nm, nm), fnum(xb - xa)), T_SMALL, "middle", halo=False)
    sh.text(a0 - 2, zb1 - 1.4, "칸 (사양 bays_x)", T_SMALL, "end", cls="tm")
    # numbered items: each balloon is anchored inside one real instance of its item (the piece with the most room), and
    # the sheet is refused (DrawingCheckError) if any anchor does not land on the item's own projection
    items = []
    used = set()
    off_part = []
    for rx, lab in D01_ITEMS:
        ids = [p.id for p in pp2 if re.match(rx, p.id) and p.id not in used and p.id in vis2]
        if not ids:
            continue
        used |= set(ids)
        nm = lab or pair_name([M.by[i] for i in ids])
        n_inst = len(ids)
        if re.match(r"CU-PLY-END|CU-E-FUSE|CU-E-J501|CU-E-J702|SEAM-INS|CU-E-PI5-|C-XT30|^C-USB|CU-POST", ids[0]):
            n_inst = 0
        visu = CrossSection()
        full = CrossSection()
        for i in ids:
            visu = visu + vis2[i][1]
            full = full + vis2[i][0]
        src = visu if visu.area() > 1.0 else full
        pt = best_inner(src)
        if pt is None or not point_in(src, pt[0], pt[1]) or not point_in(full, pt[0], pt[1]):
            off_part.append("%s %s" % (nm, "(none)" if pt is None else "(%.1f, %.1f)" % (pt[0], pt[1])))
        a = v2.P(pt[0], pt[1]) if pt else None
        bb = M.bbox(ids)
        items.append(dict(ids=ids, name=nm + ((" ×%d" % n_inst) if n_inst > 1 else ""), anchor=a, bb=bb, hidden=visu.area() <= 1.0))
    if off_part:
        raise DrawingCheckError("D01: balloon anchor not on its part: " + "; ".join(off_part))
    items.sort(key=lambda d: ((d["bb"][0] + d["bb"][3]) / 2, d["bb"][1]))
    for i, d in enumerate(items):
        d["n"] = i + 1
        if d["hidden"]:
            for pid in d["ids"]:
                v2.outline(polys(vis2[pid][0]), "hid")
    ym = (b0 + b1) / 2
    top = [(d["anchor"][0], d["anchor"][1], d["n"]) for d in items if d["anchor"][1] < ym]
    bot = [(d["anchor"][0], d["anchor"][1], d["n"]) for d in items if d["anchor"][1] >= ym]
    sh.balloons_h(top, zb0 - 5.0, a0, a1)
    sh.balloons_h(bot, b1 + 6.0, a0, a1)
    ys2 = [body.MOD_REAR, body.Y0, body.DUCT_Y[1], body.YBI, body.YB]
    sh.ordinates_v([(v2.Py(y), None, fnum(y)) for y in ys2], a1 + 1.0, 1, lo=b0, hi=b1)
    sh.text(a1 + 1.0, b0 - 1.5, "y", T_SMALL, cls="tm")
    # table
    rows = [[str(d["n"]), d["name"], "%s~%s" % (fnum(d["bb"][0], 1), fnum(d["bb"][3], 1)), "%s~%s" % (fnum(d["bb"][1], 1), fnum(d["bb"][4], 1)),
             "%s~%s" % (fnum(d["bb"][2], 1), fnum(d["bb"][5], 1))] for d in items]
    half = (len(rows) + 1) // 2
    cols = [("번호", 8.0, "middle"), ("이름 (모델 부품 이름)", 82.0, "start"), ("x", 26.0, "start"), ("y", 26.0, "start"), ("z", 22.0, "start")]
    ty = 304.0
    sh.text(16, ty - 3.0, "가운데 유닛 안 물건 (번호 = 위 그림, 좌표는 입체의 바깥 상자)", T_NOTE + 0.4, bold=True, halo=False)
    sh.table(16, ty, cols, rows[:half], size=T_SMALL - 0.2, rh=3.75)
    sh.table(16 + 170, ty, cols, rows[half:], size=T_SMALL - 0.2, rh=3.75)
    sh.legend(392, 302, sh.used | {"ctx"}, cols=2, colw=96, extra=[("hid", "숨은 선 (스피커·바닥 밑)"), ("ph", "화면 투영 (사용 25°)"), ("cl", "뚜껑 이음·자르는 자리")])
    sh.scale_bar(392, 360, k1, 200, 50, "1:2.5")
    sh.scale_bar(500, 360, k2, 60, 20, "1:1.5")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ D06 plywood cut sheet

PLY_SLOTS = [("PLY-POD-SIDE", r"SPKL-PLY-SIDEOUT$|SPKL-PLY-SIDEIN$|SPKR-PLY-SIDEIN$|SPKR-PLY-SIDEOUT$"), ("PLY-POD-BACK", r"SPK[LR]-PLY-BACK$"),
             ("PLY-POD-TOP", r"SPK[LR]-PLY-TOP$"), ("PLY-POD-BOTTOM", r"SPK[LR]-PLY-BOTTOM$"), ("PLY-CU-END", r"CU-PLY-END-[LR]$"),
             ("PLY-CU-BACK", r"CU-PLY-BACK$"), ("PLY-CU-BOTTOM", r"CU-PLY-BOTTOM$"), ("PLY-CU-LID-L", r"LID-L$"), ("PLY-CU-LID-R", r"LID-R$")]


def flat_piece(M, p):
    """plywood part -> 2D outline in its own plane (origin at the min corner): projection along the thickness + face slices."""
    b = M.bb(p)
    ext = [b[3] - b[0], b[4] - b[1], b[5] - b[2]]
    i = int(np.argmin(ext))
    ax = "xyz"[i]
    org = {"x": (b[1], b[2]), "y": (b[0], b[2]), "z": (b[0], b[1])}[ax]
    pr = proj(p.solid, ax).translate((-org[0], -org[1]))
    f0 = sec(p.solid, ax, b[i] + 0.3).translate((-org[0], -org[1]))
    f1 = sec(p.solid, ax, b[i + 3] - 0.3).translate((-org[0], -org[1]))
    W, H = [e for j, e in enumerate(ext) if j != i]
    return dict(p=p, ax=ax, W=W, H=H, T=ext[i], proj=pr, f0=f0, f1=f1, org=org)


def rot90(cs, W):
    """(u, v) -> (v, W - u): a W x H piece becomes H x W."""
    return cs.transform(np.array([[0, 1, 0], [-1, 0, W]], float))


def _piece_slice(M, fp, c):
    """slice of a plywood piece at plane c along its thickness axis, in piece coordinates."""
    return sec(fp["p"].solid, fp["ax"], c).translate((-fp["org"][0], -fp["org"][1]))


def _face_plane(M, fp, fi, d):
    """plane d inside face fi (0 = the smaller coordinate face, 1 = the larger)."""
    b = M.bb(fp["p"])
    i = "xyz".index(fp["ax"])
    return b[i] + d if fi == 0 else b[i + 3] - d


def face_name(M, fp, fi):
    import body
    b = M.bb(fp["p"])
    i = "xyz".index(fp["ax"])
    if fp["ax"] == "x":
        near, far = (b[i], b[i + 3]) if fi == 0 else (b[i + 3], b[i])
        return "가운데(x%s) 쪽 면" % fnum(body.MIRROR_X) if abs(near - body.MIRROR_X) < abs(far - body.MIRROR_X) else "바깥쪽 면"
    return {"y": ("앞면", "뒷면"), "z": ("밑면", "윗면")}[fp["ax"]][fi]


def blind_depth(M, fp, h, fi):
    """depth of a blind hole from its face: bisection on slices of the solid (± 0.001)."""
    def has(d):
        for g in hole_list(_piece_slice(M, fp, _face_plane(M, fp, fi, d))):
            if abs(g["cu"] - h["cu"]) < 0.3 and abs(g["cv"] - h["cv"]) < 0.3 and abs(g["w"] - h["w"]) < 0.4:
                return True
        return False
    lo, hi = 0.3, fp["T"] - 0.02
    if has(hi):
        return fp["T"]
    for _ in range(16):
        m = (lo + hi) / 2
        if has(m):
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def _edge_of(q, W, H):
    """(edge index 0 u0 / 1 u1 / 2 v0 / 3 v1, length along the edge, width into the piece, (a0, a1) along the edge)."""
    (u0, v0), (u1, v1) = q.min(0), q.max(0)
    horiz = (u1 - u0) > (v1 - v0)
    if horiz:
        return min([(v0, 2), (H - v1, 3)])[1], u1 - u0, v1 - v0, (u0, u1)
    return min([(u0, 0), (W - u1, 1)])[1], v1 - v0, u1 - u0, (v0, v1)


def edge_profile(M, fp, fi, e, outer):
    """profile of the material missing along edge e on face fi: widths at several depths fitted to a 45° chamfer
    (w = C - d) or a round (w = R - sqrt(R² - (R - d)²)). Returns ('C' | 'R', size)."""
    full = CrossSection([[(float(a_), float(b_)) for a_, b_ in outer]])

    def width(d):
        f = _piece_slice(M, fp, _face_plane(M, fp, fi, d))
        fo = [q for q in polys(f) if signed_area(q) > 0]
        if not fo:
            return 0.0
        miss = full - CrossSection([[(float(a_), float(b_)) for a_, b_ in max(fo, key=signed_area)]])
        best = (0.0, 0.0)
        for q in polys(miss):
            if signed_area(q) < 0.5:
                continue
            ee, ln, w_, _ = _edge_of(q, fp["W"], fp["H"])
            if ee == e and ln >= 20 and ln > best[0]:
                best = (ln, w_)
        return best[1]

    pts = []
    for d in (0.05, 0.15, 0.3, 0.5, 0.8, 1.2, 1.7, 2.3, 2.9, 3.6, 4.5):
        w = width(d)
        if w <= 0.02:
            break
        pts.append((d, w))
    if not pts:
        return None
    D = np.array([p_[0] for p_ in pts])
    Wd = np.array([p_[1] for p_ in pts])
    C = float(np.mean(Wd + D))
    rc = float(np.sqrt(np.mean((C - D - Wd) ** 2)))
    best_r = None
    for R in np.arange(max(0.2, D.max()), 12.0, 0.01):
        wr = R - np.sqrt(np.maximum(R * R - (R - D) ** 2, 0.0))
        r = float(np.sqrt(np.mean((wr - Wd) ** 2)))
        if best_r is None or r < best_r[1]:
            best_r = (float(R), r)
    if best_r is not None and best_r[1] < rc:
        return ("R", best_r[0])
    return ("C", C)


def edge_pockets(M, fp, blind):
    """holes drilled into an EDGE (e.g. magnet pockets Ø8 in the top edge, centred in the thickness): the projection
    and the face slices cannot see them, the mid-thickness slice can."""
    b = M.bb(fp["p"])
    i = "xyz".index(fp["ax"])
    mid = _piece_slice(M, fp, (b[i] + b[i + 3]) / 2)
    out = []
    for q in polys(fp["proj"] - mid):
        if abs(signed_area(q)) < 1.0:
            continue
        (u0, v0), (u1, v1) = q.min(0), q.max(0)
        if any(u0 - 0.3 <= h["cu"] <= u1 + 0.3 and v0 - 0.3 <= h["cv"] <= v1 + 0.3 for h in blind):
            continue                                                  # a blind hole deeper than half the board
        gaps = [(u0, 0), (fp["W"] - u1, 1), (v0, 2), (fp["H"] - v1, 3)]
        g, e = min(gaps)
        if g > 0.05:
            continue
        along, depth, c = ((u1 - u0), (v1 - v0), (u0 + u1) / 2) if e in (2, 3) else ((v1 - v0), (u1 - u0), (v0 + v1) / 2)
        out.append(dict(edge=e, c=c, w=along, depth=depth, u0=u0, u1=u1, v0=v0, v1=v1))
    return sorted(out, key=lambda t: (t["edge"], t["c"]))


EDGE_KO = {"x": ("앞", "뒤", "아래", "위"), "y": ("왼쪽", "오른쪽", "아래", "위"), "z": ("왼쪽", "오른쪽", "앞", "뒤")}


def piece_memo(fp, M):
    """features of the outline (slants, notches, edge profiles), holes (through / blind with face + depth) and edge
    pockets, all from the geometry. Returns a dict."""
    pl = polys(fp["proj"])
    outer = max([q for q in pl if signed_area(q) > 0], key=signed_area)
    slants = []
    n = len(outer)
    conc = 0
    for j in range(n):
        a, b_, c = outer[j - 1], outer[j], outer[(j + 1) % n]
        d = b_ - a
        if abs(d[0]) > 0.05 and abs(d[1]) > 0.05:
            ang = math.degrees(math.atan2(abs(d[1]), abs(d[0])))
            slants.append((ang, float(np.hypot(*d))))
        cr = (b_[0] - a[0]) * (c[1] - b_[1]) - (b_[1] - a[1]) * (c[0] - b_[0])
        if cr < -1e-6:
            conc += 1
    thru = hole_list(fp["proj"])
    blind = []
    for fi, f in enumerate((fp["f0"], fp["f1"])):
        for h in hole_list(f):
            if not any(abs(h["cu"] - t["cu"]) < 0.3 and abs(h["cv"] - t["cv"]) < 0.3 for t in thru + blind):
                h = dict(h, face=fi)
                h["depth"] = blind_depth(M, fp, h, fi)
                blind.append(h)
    pockets = edge_pockets(M, fp, blind)
    bevel = False
    memo, notes = [], []
    edge_ko = EDGE_KO[fp["ax"]]
    full = CrossSection([[(float(a_), float(b_)) for a_, b_ in outer]])
    # material missing on one face only, along an edge = chamfer / round on that face (found 0.3 inside the face,
    # measured at several depths: edge_profile)
    for fi, f in enumerate((fp["f0"], fp["f1"])):
        fo = [q for q in polys(f) if signed_area(q) > 0]
        if not fo:
            continue
        miss = full - CrossSection([[(float(a_), float(b_)) for a_, b_ in max(fo, key=signed_area)]])
        found = collections.OrderedDict()
        for q in polys(miss):
            if signed_area(q) < 2.0:
                continue
            e, l_, w_, span = _edge_of(q, fp["W"], fp["H"])
            if l_ < 20:
                continue
            found.setdefault(e, []).append(span)
        for e, spans in found.items():
            bevel = True
            prof = edge_profile(M, fp, fi, e, outer)
            ptxt = ("R%s" % fnum(prof[1], 1)) if prof and prof[0] == "R" else ("C%s (45° 모따기)" % fnum(prof[1], 1) if prof else "깎음")
            L = fp["W"] if e in (2, 3) else fp["H"]
            spans = sorted(spans)
            skip = [(spans[k][1], spans[k + 1][0]) for k in range(len(spans) - 1) if spans[k + 1][0] - spans[k][1] > 0.5]
            if spans[0][0] > 0.5:
                skip.insert(0, (0.0, spans[0][0]))
            if spans[-1][1] < L - 0.5:
                skip.append((spans[-1][1], L))
            ax_l = "u" if e in (2, 3) else "v"
            where = (", 빼는 곳 " + " · ".join("%s%s~%s" % (ax_l, fnum(s0, 1), fnum(s1, 1)) for s0, s1 in skip)) if skip else ""
            memo.append("%s %s 모서리 %s%s" % (face_name(M, fp, fi), edge_ko[e], ptxt, where))
    for ang, ln in slants:
        memo.append("경사 자르기 %s° (길이 %s)" % (fnum(ang, 1), fnum(ln, 2)))
    if conc:
        memo.append("따냄 %d곳 (오목 모서리 %d)" % (max(1, conc // 2), conc))
    if pockets:
        b = M.bb(fp["p"])
        i = "xyz".index(fp["ax"])
        mags = [M.bb(q) for q in M.rear if q.id.startswith("CU-MAG-") or q.id.startswith("MAG-")]

        def holds_magnet(pk):
            # pocket centre back in world coordinates (thickness axis = mid-board)
            u, v_ = (pk["u0"] + pk["u1"]) / 2 + fp["org"][0], (pk["v0"] + pk["v1"]) / 2 + fp["org"][1]
            w = (b[i] + b[i + 3]) / 2
            P = {"x": (w, u, v_), "y": (u, w, v_), "z": (u, v_, w)}[fp["ax"]]
            return any(all(mb[k] - 4.5 <= P[k] <= mb[k + 3] + 4.5 for k in range(3)) for mb in mags)
        by_e = collections.OrderedDict()
        for pk in pockets:
            by_e.setdefault((pk["edge"], round(pk["w"], 1), round(pk["depth"], 1), holds_magnet(pk)), []).append(pk)
        for (e, w_, dp, mg), g in by_e.items():
            ax_l = "u" if e in (2, 3) else "v"
            what = "자석 자리" if mg else "구멍"
            memo.append("%s 모서리 %s Ø%s × %s ×%d" % (edge_ko[e], what, fnum(w_, 1), fnum(dp, 1), len(g)))
            notes.append("%s 모서리 %s: 모서리 안으로 Ø%s × 깊이 %s ×%d (판 두께 가운데, 양쪽 벽 %s; 중심 %s%s) — 판을 붙이기 전에 포스트너 비트로"
                         % (edge_ko[e], what, fnum(w_, 1), fnum(dp, 1), len(g), fnum((fp["T"] - w_) / 2, 2), ax_l,
                            "·".join(fnum(pk["c"], 2) for pk in g)))
    return dict(outer=outer, thru=thru, blind=blind, memo=memo, bevel=bevel, pockets=pockets, notes=notes)


def hole_sig(fp, info, mirror=False):
    """comparable list of every hole / pocket position of a piece; mirror = the piece seen as the other side's mirror
    (about x = MIRROR_X: u -> W - u for pieces lying in x·y or x·z; x-thick pieces keep (y, z))."""
    flip = mirror and fp["ax"] in ("y", "z")

    def U(u):
        return round(fp["W"] - u, 1) if flip else round(u, 1)
    s = [("t", round(h["w"], 1), round(h["h"], 1), U(h["cu"]), round(h["cv"], 1)) for h in info["thru"]]
    s += [("b", round(h["w"], 1), round(h["h"], 1), round(h["depth"], 1), U(h["cu"]), round(h["cv"], 1)) for h in info["blind"]]
    s += [("p", pk["edge"] if not flip or pk["edge"] in (2, 3) else 1 - pk["edge"], round(pk["w"], 1), round(pk["depth"], 1),
           U(pk["c"]) if pk["edge"] in (2, 3) else round(pk["c"], 1)) for pk in info["pockets"]]
    return sorted(s)


def relax_layout(placed, kerf):
    """push pieces right / down until every neighbour gap is >= kerf (the spec layout uses rounded sizes)."""
    moved = {}
    for _ in range(20):
        changed = False
        for b_ in placed:
            for a in placed:
                if a is b_:
                    continue
                xov = min(a["x"] + a["W"], b_["x"] + b_["W"]) - max(a["x"], b_["x"])
                yov = min(a["y"] + a["H"], b_["y"] + b_["H"]) - max(a["y"], b_["y"])
                if xov > -kerf + 1e-6 and a["y"] < b_["y"] and xov > 0 and b_["y"] < a["y"] + a["H"] + kerf - 1e-6:
                    d = a["y"] + a["H"] + kerf - b_["y"]
                    b_["y"] += d
                    moved[b_["fp"]["p"].id] = moved.get(b_["fp"]["p"].id, 0.0) + d
                    changed = True
                elif yov > 0 and a["x"] < b_["x"] and b_["x"] < a["x"] + a["W"] + kerf - 1e-6:
                    d = a["x"] + a["W"] + kerf - b_["x"]
                    b_["x"] += d
                    moved[b_["fp"]["p"].id] = moved.get(b_["fp"]["p"].id, 0.0) + d
                    changed = True
        if not changed:
            break
    return moved


def sheet_D06(M):
    import body
    sh = Sheet("D06", "재단 1:3 · 부품 1:4 / 1:5")
    PC = body.L2["plywood_cut_list"]
    NEST = PC["nesting_400x1200"]
    SW, SH_ = 1200.0, 400.0
    kerf = NEST["kerf"]
    plys = [p for p in M.rear if p.kind == "plywood"]
    pool = {}
    for sid, rx in PLY_SLOTS:
        order = rx.split("|")
        pool[sid] = sorted([flat_piece(M, p) for p in plys if re.match(rx, p.id)],
                           key=lambda fp: next(k for k, r_ in enumerate(order) if re.match(r_, fp["p"].id)))
    placed = []
    for sid, x, y, w, h in NEST["layout_xywh"]:
        fp = pool[sid].pop(0)
        W, H = fp["W"], fp["H"]
        if abs(W - w) < 1.5 and abs(H - h) < 1.5:
            cs, rot = fp["proj"], False
        elif abs(W - h) < 1.5 and abs(H - w) < 1.5:
            cs, rot, (W, H) = rot90(fp["proj"], W), True, (H, W)
        else:
            raise ValueError("plywood piece %s %.1f x %.1f does not fit slot %s %.1f x %.1f" % (fp["p"].id, W, H, sid, w, h))
        placed.append(dict(fp=fp, sid=sid, x=x, y=y, W=W, H=H, cs=cs, rot=rot))
    left = [fp["p"].id for v_ in pool.values() for fp in v_]
    moved = relax_layout(placed, kerf)
    issues = []
    for a in placed:
        if a["x"] < -1e-6 or a["y"] < -1e-6 or a["x"] + a["W"] > SW + 1e-6 or a["y"] + a["H"] > SH_ + 1e-6:
            issues.append("%s 판 밖" % a["fp"]["p"].id)
    gaps = []
    for i_, a in enumerate(placed):
        for b_ in placed[i_ + 1:]:
            g = max(b_["x"] - (a["x"] + a["W"]), a["x"] - (b_["x"] + b_["W"]), b_["y"] - (a["y"] + a["H"]), a["y"] - (b_["y"] + b_["H"]))
            gaps.append(g)
            if g < kerf - 1e-3:
                issues.append("%s / %s 틈 %.2f" % (a["fp"]["p"].id, b_["fp"]["p"].id, g))
    used_w = max(a["x"] + a["W"] for a in placed)
    used_h = max(a["y"] + a["H"] for a in placed)
    info = {id(a): piece_memo(a["fp"], M) for a in placed}
    types = collections.OrderedDict()
    for a in placed:
        key = re.sub(r"-END-[LR]$", "-END", re.sub(r"^SPK[LR]-", "SPK-", a["fp"]["p"].id))
        types.setdefault(key, []).append(a)

    def side_of(a):
        pid = a["fp"]["p"].id
        return "R" if re.search(r"^SPKR-|-R$", pid) else ("L" if re.search(r"^SPKL-|-L$", pid) else "")

    # one drawing per type; an L·R type is split into its own L and R drawings when the hole / pocket positions are
    # not mirror-equal (e.g. the R inner side panel and the R end wall have their holes elsewhere: XT30-CLIP-R, JOIN-*-R2)
    groups = collections.OrderedDict()
    lab_of = {}
    split = []
    for n_, (key, lst) in enumerate(types.items(), 1):
        Ls = [a for a in lst if side_of(a) == "L"]
        Rs = [a for a in lst if side_of(a) == "R"]
        same = True
        if Ls and Rs:
            sL = hole_sig(Ls[0]["fp"], info[id(Ls[0])])
            same = all(hole_sig(a["fp"], info[id(a)]) == sL for a in Ls) and \
                all(hole_sig(a["fp"], info[id(a)], mirror=True) == sL for a in Rs)
        if Ls and Rs and not same:
            split.append(n_)
            for sd, sub in (("L", Ls), ("R", Rs)):
                lab = "P%d%s" % (n_, sd)
                groups[lab] = dict(n=n_, lst=sub, side=sd, pair=False)
                for a in sub:
                    lab_of[id(a)] = lab
        else:
            lab = "P%d" % n_
            groups[lab] = dict(n=n_, lst=lst, side="", pair=bool(Ls and Rs))
            for a in lst:
                lab_of[id(a)] = lab
    # ---- nesting view (1:3)
    k = 1 / 3.0
    v = View(sh, k, (0.0, SW, 0.0, SH_), (48.0, 44.0))
    x0, y0, x1, y1 = v.rect
    sh.heading(16, 24, "합판 재단도 — 오꾸메 11.5T, 400 × 1200 한 장", "1:3 · 톱날 %s · P 번호 = 아래 조각도 · 연한 색 = 남는 조각" % fnum(kerf))
    v.area([np.array([(0, 0), (SW, 0), (SW, SH_), (0, SH_)])], "sheetply")
    sh.used.add("wood")
    for a in placed:
        cs = a["cs"].translate((a["x"], SH_ - a["y"] - a["H"]))
        v.area(polys(cs), "S-wood")
        pt = inner_point(polys(cs))
        px, py = v.P(pt[0], pt[1])
        sz = T_LAB if pt[2] * k > 2.3 else T_SMALL
        sh.text(px, py + 0.35 * sz, lab_of[id(a)] + (" (90°)" if a["rot"] else ""), sz, "middle", bold=True)
    sh.dim_h(x0, x1, y0 - 6, "1200", ext=[(x0, y0), (x1, y0)])
    sh.dim_v(y0, y1, x0 - 6, "400", ext=[(x0, y0), (x0, y1)])
    sh.dim_h(x0, v.Px(used_w), y1 + 6, "쓴 길이 %s" % fnum(used_w, 2), ext=[(x0, y1), (v.Px(used_w), y1)])
    sh.dim_v(y0, v.Py(SH_ - used_h), x1 + 6, "쓴 폭 %s" % fnum(used_h, 2), ext=[(x1, y0), (x1, v.Py(SH_ - used_h))])
    plyA = sum(a["fp"]["proj"].area() for a in placed) / 1e6
    mv = max(moved.values()) if moved else 0.0
    if split:
        lr = "%s = 구멍 자리가 L과 R에서 달라 L·R을 따로 그림 (R은 L의 거울이 아님). 나머지 L·R 짝은 구멍까지 거울로 같음" \
             % ", ".join("P%dL·P%dR" % (s_, s_) for s_ in split)
    else:
        lr = "L·R 짝은 구멍까지 거울로 같음"
    info_l = ["조각 %d개, 넓이 %s m² (구멍 뺌) / 판 %s m² = %s %%" % (len(placed), fnum(plyA, 3), fnum(SW * SH_ / 1e6, 2), fnum(100 * plyA / (SW * SH_ / 1e6), 0)),
              "조각 사이 가장 좁은 틈 %s (톱날 %s)" % (fnum(min(gaps), 2), fnum(kerf)),
              "배치 = 사양 nesting_400x1200 순서; 실제 조각 크기로 %d개를 최대 %s 옮김" % (len(moved), fnum(mv, 2)) if moved else "배치 = 사양 nesting_400x1200 그대로",
              "(90°) = 돌려 놓은 조각 · " + lr,
              "가게: 직사각형으로만 자름. 경사·턱·홈·창·구멍·모서리 자석 자리는 아래 조각도와 오른쪽 글대로 집에서 (톱·드릴·포스트너 비트)"]
    yy = sh.textblock(x1 + 14, y0 + 2, sum([sh.wrap(t, 582 - x1 - 16, T_SMALL) for t in info_l], []), T_SMALL)
    if issues or left:
        sh.text(x0, y1 + 14, "확인 필요: " + "; ".join(issues + left), T_SMALL, cls="tr")
    sh.legend(x1 + 14, yy + 6, {"wood"}, extra=[("sheetply", "남는 조각"), ("hid", "막힘 구멍 · 모서리 자석 자리 (점선)")])
    # ---- piece drawings (one per group), flow layout in the lower-left area
    pk = {"CU-PLY-BACK": 0.2, "CU-PLY-BOTTOM": 0.2}
    X0, X1, Y0 = 16.0, 386.0, y1 + 20.0
    xcur, ycur, rowh = X0, Y0, 0.0
    rows_tbl = []
    notes = ["보는 방향: x 두께 조각(옆판·끝벽)은 +x 쪽(오른쪽 끝)에서, y 두께(뒤판)는 앞에서, z 두께(아랫판·윗판·뚜껑)는 위에서 본 그림. "
             "u = 왼쪽 끝(옆판·끝벽은 앞 모서리)에서, v = 아래 모서리(z 두께는 앞 모서리)에서 잰 거리 — 어느 면에 금을 그어도 같음"]
    for lab, g in groups.items():
        a0 = g["lst"][0]
        fp = a0["fp"]
        inf = info[id(a0)]
        outer, thru, blind = inf["outer"], inf["thru"], inf["blind"]
        kk = pk.get(fp["p"].id, 0.25)
        bw, bh = fp["W"] * kk, fp["H"] * kk
        us = sorted(set(round(float(q[0]), 2) for q in outer) - {0.0, round(fp["W"], 2)})
        vs = sorted(set(round(float(q[1]), 2) for q in outer) - {0.0, round(fp["H"], 2)})
        top = 21.0 if us else 7.0
        bwid = 11.0 + bw + (17.0 if vs else 4.0)
        bhei = top + bh + 11.0
        if xcur + bwid > X1 and xcur > X0:
            xcur, ycur, rowh = X0, ycur + rowh + 3.0, 0.0
        vp = View(sh, kk, (0.0, fp["W"], 0.0, fp["H"]), (xcur + 11.0, ycur + top))
        px0, py0, px1, py1 = vp.rect
        vp.area(polys(fp["proj"]), "S-wood")
        for h in blind:
            if h["round"]:
                q = np.array([(h["cu"] + h["d"] / 2 * math.cos(t), h["cv"] + h["d"] / 2 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 25)[:-1]])
            else:
                q = np.array([(h["u0"], h["v0"]), (h["u1"], h["v0"]), (h["u1"], h["v1"]), (h["u0"], h["v1"])])
            vp.outline([q], "hid")
        for pk_ in inf["pockets"]:
            vp.outline([np.array([(pk_["u0"], pk_["v0"]), (pk_["u1"], pk_["v0"]), (pk_["u1"], pk_["v1"]), (pk_["u0"], pk_["v1"])])], "hid")
        base = short(fp["p"].name_ko).replace("스피커 파트 L ", "스피커 ").replace("스피커 파트 R ", "스피커 ")
        if g["side"]:
            nm = _SIDE.sub("", base).strip() + " " + g["side"]
        elif g["pair"]:
            nm = _SIDE.sub("", base).strip() + " L·R"
        else:
            nm = base
        nm = re.sub(r"\s+", " ", nm)
        qty = len(g["lst"])
        sh.text(xcur, ycur + 3.6, "%s %s ×%d  (1:%s)" % (lab, nm, qty, fnum(1 / kk)), T_SMALL + 0.2, bold=True)
        sh.dim_h(px0, px1, py1 + 5.0, fnum(fp["W"], 2), ext=[(px0, py1), (px1, py1)])
        sh.dim_v(py0, py1, px0 - 5.0, fnum(fp["H"], 2), ext=[(px0, py0), (px0, py1)], out_side="down")
        if us:
            sh.ordinates_h([(vp.Px(u), None, fnum(u)) for u in us], py0 - 0.5, -1, lo=px0 - 4, hi=px1 + 6, size=T_SMALL - 0.2)
        if vs:
            sh.ordinates_v([(vp.Py(vv), None, fnum(vv)) for vv in vs], px1 + 0.5, 1, lo=py0 - 2, hi=py1 + 2, size=T_SMALL - 0.2)
        ax_ko = {"x": "y·z", "y": "x·z", "z": "x·y"}[fp["ax"]]
        parts_ = ["관통 " + t for t in pattern_text(thru)]
        bl = collections.OrderedDict()
        for h in blind:
            bl.setdefault((h["face"], round(h["depth"], 1)), []).append(h)
        for (fi, dp), hs in bl.items():
            seal = " — 밀폐 상자 판: 깊이 멈춤으로 (드릴 끝까지 1.5 이상 남김)" if fp["p"].id.startswith("SPK") else ""
            for t in pattern_text(hs):
                parts_.append("막힘(점선) %s에서 깊이 %s, 남는 판 %s%s: %s" % (face_name(M, fp, fi), fnum(dp, 1), fnum(fp["T"] - dp, 1), seal, t))
        parts_ += inf["notes"]
        notes.append("%s %s — 원점 = 왼쪽 아래 = 입체 (%s, %s) %s 면" % (lab, nm, fnum(fp["org"][0], 2), fnum(fp["org"][1], 2), ax_ko)
                     + "".join("; " + t for t in parts_))
        mir = "R은 L의 거울 (구멍 포함)" if g["pair"] else ""
        rows_tbl.append([lab, nm, "%s × %s" % (fnum(fp["W"], 2), fnum(fp["H"], 2)), str(qty), " · ".join(inf["memo"] + ([mir] if mir else [])) or "직사각형"])
        xcur += bwid + 5.0
        rowh = max(rowh, bhei)
    if ycur + rowh > 408:
        raise DrawingCheckError("D06: piece drawings overflow the sheet (%.1f > 408)" % (ycur + rowh))
    # table + notes (right column)
    tx, ty = 392.0, y1 + 22.0
    sh.text(tx, ty - 3.0, "조각 목록 (입체에서 잰 크기, 두께 %s)" % fnum(body.T), T_NOTE + 0.2, bold=True, halo=False)
    yb = sh.table(tx, ty, [("번호", 9.0, "middle"), ("조각", 48.0, "start"), ("크기", 27.0, "start"), ("수량", 8.0, "middle"),
                           ("자르기·모서리 (윤곽에서)", 98.0, "start")], rows_tbl + [["", "합계", "", str(len(placed)), ""]], size=T_SMALL - 0.45, rh=3.6)
    notes_box(sh, tx, yb + 6.0, 190, "구멍·홈 (조각 좌표, 단위 mm)", notes, size=T_SMALL - 0.45)
    sh.title_block()
    return sh


# ------------------------------------------------------------------ PNG export

CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
          shutil.which("google-chrome") or "", shutil.which("chromium") or ""]


def _chrome():
    for c in CHROME:
        if c and os.path.exists(c):
            return c
    return None


_SVG_SIZE = re.compile(r'width="[0-9.]+(?:mm)?" height="[0-9.]+(?:mm)?" viewBox="0 0 ([0-9.]+) ([0-9.]+)"')


def svg_to_png(svg_path, png_path, w_px, h_px):
    """headless Chrome at w_px x h_px; fallback = QuickLook (square thumbnail, cropped with PIL).
    The sheet SVG says width/height in mm (true A2 print), so a temporary copy with pixel width/height is rendered."""
    c = _chrome()
    if c:
        prof = tempfile.mkdtemp(prefix="tocdwg_")
        tmp_png = os.path.join(prof, "shot.png")
        px_svg = os.path.join(prof, "sheet.svg")
        s = open(svg_path, encoding="utf-8").read()
        s = _SVG_SIZE.sub(lambda m_: 'width="%d" height="%d" viewBox="0 0 %s %s"' % (w_px, h_px, m_.group(1), m_.group(2)), s, count=1)
        open(px_svg, "w", encoding="utf-8").write(s)
        proc = None
        try:
            # Chrome writes the screenshot and then may keep running with a fresh profile: poll for the file, then stop it
            proc = subprocess.Popen([c, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                                     "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
                                     "--disable-background-networking", "--user-data-dir=" + prof, "--window-size=%d,%d" % (w_px, h_px),
                                     "--default-background-color=ffffffff", "--screenshot=" + tmp_png, "file://" + os.path.abspath(px_svg)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            t_end = time.time() + 120
            last = -1
            while time.time() < t_end:
                if proc.poll() is not None and not os.path.exists(tmp_png):
                    break
                if os.path.exists(tmp_png):
                    sz = os.path.getsize(tmp_png)
                    if sz > 1000 and sz == last:
                        break
                    last = sz
                time.sleep(0.5)
            if os.path.exists(tmp_png) and os.path.getsize(tmp_png) > 1000:
                shutil.copyfile(tmp_png, png_path)
                return "chrome"
        except Exception:
            pass
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(5)
                except Exception:
                    proc.kill()
            shutil.rmtree(prof, ignore_errors=True)
    if shutil.which("qlmanage"):
        tmp = tempfile.mkdtemp(prefix="tocql_")
        try:
            s = open(svg_path, encoding="utf-8").read()
            n = max(w_px, h_px)
            s = _SVG_SIZE.sub(lambda m_: 'width="%d" height="%d" viewBox="0 0 %s %s"' % (n, n, max(float(m_.group(1)), float(m_.group(2))),
                                                                                       max(float(m_.group(1)), float(m_.group(2)))), s, count=1)
            sq = os.path.join(tmp, "sq.svg")
            open(sq, "w", encoding="utf-8").write(s)
            subprocess.run(["qlmanage", "-t", "-s", str(n), "-o", tmp, sq], capture_output=True, timeout=120)
            out = sq + ".png"
            from PIL import Image
            im = Image.open(out).convert("RGB")
            sc = im.size[0] / float(n)
            im.crop((0, 0, int(w_px * sc), int(h_px * sc))).save(png_path)
            return "qlmanage"
        except Exception as ex:
            print("  png fallback failed:", ex)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return None


# ------------------------------------------------------------------ main

BUILDERS = {}


def write_sheet(sh, png=True):
    os.makedirs(DWG, exist_ok=True)
    p = os.path.join(DWG, sh.file + ".svg")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(sh.svg())
    bad = sh.check()
    return p, bad


def main(parts=None, codes=None, png=True, render=True, verbose=True):
    t0 = time.time()
    if parts is None:
        import build_all
        parts = build_all.collect()
    M = Model(parts)
    codes = codes or list(SHEETS)
    done = []
    for code in codes:
        fn = BUILDERS.get(code)
        if fn is None:
            continue
        t = time.time()
        sh = fn(M)
        p, bad = write_sheet(sh)
        done.append((sh, p))
        if verbose:
            print("drawings: %s %s (%.1f s)%s" % (code, os.path.relpath(p, OUT), time.time() - t,
                                                 ("  layout: " + "; ".join(bad[:12]) + (" ..." if len(bad) > 12 else "")) if bad else ""))
    if png and done:
        import concurrent.futures as cf
        with cf.ThreadPoolExecutor(max_workers=3) as ex:
            futs = {ex.submit(svg_to_png, p, p[:-4] + ".png", int(sh.w * PX_PER_MM), int(sh.h * PX_PER_MM)): p for sh, p in done}
            for f in cf.as_completed(futs):
                if verbose:
                    print("drawings: png %s via %s" % (os.path.basename(futs[f])[:-4] + ".png", f.result()))
    if render:
        renders(M, verbose=verbose)
    if verbose:
        print("drawings: done in %.0f s" % (time.time() - t0))
    return [p for _, p in done]


TS_MOVING = ("TS-CRADLE", "TS-E-SCREEN", "TS-LEG", "TS-WINCOVER", "TS-M3X20-LEG", "TS-C-DSI", "TS-C-PWR-RED", "TS-C-PWR-BLK",
             "TS-M25-1", "TS-M25-2", "TS-M25-3", "TS-M25-4")
# cameras: eye (x, y, z) -> look-at (x, y, z), world mm
RENDERS = [
    ("R01_front", "앞 3/4 (사용 상태)", (-700.0, -1300.0, 1020.0), (611.0, 175.0, 40.0), "use"),
    ("R02_rear_left", "뒤 왼쪽 3/4", (-720.0, 1720.0, 860.0), (590.0, 200.0, 30.0), "use"),
    ("R03_folded", "앞 3/4 (화면 접음, 운반)", (-700.0, -1300.0, 1020.0), (611.0, 175.0, 40.0), "fold"),
]


def render_parts(M, state):
    ondesk = [p for p in M.parts if p.note not in ("offdesk", "altview")]
    if state == "fold":
        # the optional screen cover (TS-SCREENCOVER) would hide the folded screen: left out of the picture
        return [p for p in ondesk if p.id not in TS_MOVING] + [p for p in M.alt if p.id != "TS-SCREENCOVER"]
    return ondesk


def renders(M, verbose=True, size=(1800, 1100)):
    """shaded OpenSCAD renders of the whole instrument (assembly colours); one STL per colour in a temp folder."""
    exe = shutil.which("openscad") or ("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD" if os.path.exists("/Applications/OpenSCAD.app") else None)
    if not exe:
        print("drawings: renders skipped (openscad not found)")
        return []
    import build_all
    os.makedirs(REN, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tocren_")
    jobs = []
    try:
        cache = {}
        for name, title, eye, ctr, state in RENDERS:
            if state not in cache:
                by = collections.OrderedDict()
                for p in render_parts(M, state):
                    by.setdefault(p.color, []).append(p)
                lines = []
                for i, (c, ps) in enumerate(by.items()):
                    v, f = build_all.concat([p.solid for p in ps])
                    path = os.path.join(tmp, "%s_%02d.stl" % (state, i))
                    build_all.write_mesh_stl(v, f, path, "Toccata render")
                    lines.append('color("%s") import("%s");' % (c, path))
                cache[state] = "\n".join(lines)
            scad = os.path.join(tmp, name + ".scad")
            with open(scad, "w") as fh:
                fh.write(cache[state])
            out = os.path.join(REN, name + ".png")
            cam = ",".join("%.1f" % c for c in eye + ctr)
            cmd = [exe, "--backend=manifold", "-o", out, "--imgsize=%d,%d" % size, "--camera=" + cam, "--colorscheme=Tomorrow",
                   "--projection=p", scad]
            jobs.append((name, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True), out))
        done = []
        for name, pr, out in jobs:
            o, e = pr.communicate(timeout=900)
            ok = pr.returncode == 0 and os.path.exists(out)
            if verbose:
                print("drawings: render %s %s" % (os.path.relpath(out, OUT), "ok" if ok else "FAILED " + e[-400:]))
            if ok:
                done.append(out)
        return done
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


BUILDERS.update({"D01": sheet_D01, "D02": sheet_D02, "D03": sheet_D03, "D04": sheet_D04, "D05": sheet_D05, "D06": sheet_D06})

if __name__ == "__main__":
    args = sys.argv[1:]
    codes = [a for a in args if a in SHEETS]
    only_r = "--only-render" in args
    if only_r:
        import build_all
        renders(Model(build_all.collect()))
    else:
        main(codes=codes or None, png="--no-png" not in args, render="--no-render" not in args)
