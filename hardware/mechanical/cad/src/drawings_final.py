"""Toccata FINAL drawing set - the whole instrument from every direction (E01..E07) and the inside (I01..I05), SVG.

Made FROM THE BUILT SOLIDS (build_all.collect(): keyaction_parts + body + electronics - the same solids the print STLs and
stl/assembly are written from), with the engine of drawings.py (Sheet, View, sec, proj, hole_list, dimensions, title
block, layout check). Nothing is typed by hand: every outline is a projection / section of a solid and every number on a
sheet is read from a solid's bounding box, a section polygon or the generator constants (body.py / touchscreen_rev3.py /
spec/body_L2.json) - the self check at the end compares printed numbers with stl/assembly + manifest.json.

Hidden lines: the views are true hidden-surface drawings. Every triangle of every solid is rasterised into a depth
buffer (0.04-0.2 mm per pixel, numba), which decides which part is in front where; each part's visible region is the
raster region grown by 1.5 px and cut with the part's EXACT projection (Manifold.project), and the regions are drawn
far-to-near in the order the buffer gives at every shared edge. So outlines are the solids' own silhouettes; only the
line where one part disappears behind another can sit up to 1.5 px (0.06-0.3 mm) off - it is covered by the nearer
part, which is drawn after. Sections: the solids are cut (Manifold.trim_by_plane), the far side drawn the same way and
the cut faces (drawings.sec) hatched on top. (drawings.py's painter sorts whole parts by their bounding box, which hides the keys under
the frame's top plate in a plan view; that is why this file adds the buffer.)

  python3 drawings_final.py              # every sheet -> ../drawings/final/*.svg + checks.json
  python3 drawings_final.py E01 I04      # only these

Sheets: E01 정면도 · E02 배면도 · E03 좌측면도 · E04 우측면도 · E05 평면도 · E06 저면도 · E07 화면 접은 상태
        I01 내부 평면도 · I02 가운데 유닛 내부 상세 · I03 전체 길이 단면 · I04 측면 단면 (O4 D) · I05 건반 모듈 내부 평면
A2 = 594 x 420, A1 = 841 x 594 (sheet mm = SVG user units; width/height in mm, so printing at 100 % keeps the scales).
This file never writes outside ../drawings/final/ (numba's cache goes to $TMPDIR) and never calls build_all.main().
Self check: checks.json lists printed numbers next to manifest.json / stl/assembly / stl/print / spec values (0.006 mm).
"""
import collections
import json
import math
import os
import re
import sys
import time

import numpy as np
from manifold3d import CrossSection, FillRule, JoinType

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "toccata_numba"))

import drawings as D  # noqa: E402
from drawings import fnum, text_w, polys, sec, proj, signed_area, T_LAB, T_DIM, T_NOTE, T_SMALL, T_HEAD  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, ".."))
FIN = os.path.join(OUT, "drawings", "final")
DATE = "2026-10-08"
STATE = "W1+ r4.5 · L2 40° · 화면 3판 · 전원 R33 · 회로 E"
SOURCES = "build_all.collect() = keyaction_parts.py · body.py · electronics.py · touchscreen_rev3.py · spec/body_L2.json"
PAPER = {"A2": (594.0, 420.0), "A1": (841.0, 594.0)}
SHEETS = collections.OrderedDict([
    ("E01", ("E01_front", "정면도 (사용 상태, 화면 25°)", "A2")),
    ("E02", ("E02_rear", "배면도 (사용 상태)", "A2")),
    ("E03", ("E03_left", "좌측면도 (사용 상태)", "A2")),
    ("E04", ("E04_right", "우측면도 (사용 상태)", "A2")),
    ("E05", ("E05_top", "평면도 (사용 상태)", "A2")),
    ("E06", ("E06_bottom", "저면도", "A2")),
    ("E07", ("E07_folded", "화면 접은 상태 (운반)", "A2")),
    ("I01", ("I01_inside_plan", "내부 평면도 (뚜껑·화면·앞판·윗판 뗌)", "A1")),
    ("I02", ("I02_centre_detail", "가운데 유닛 내부 상세", "A1")),
    ("I03", ("I03_long_sections", "전체 길이 단면 (y67 · y260)", "A1")),
    ("I04", ("I04_side_section", "측면 단면 (O4 D 건반 x575.75)", "A2")),
    ("I05", ("I05_module_plan", "건반 모듈 내부 평면 (O4)", "A2")),
])
N_TOTAL = len(SHEETS)

# ------------------------------------------------------------------ styles (drawings.CSS + the classes this set adds)
MAT = collections.OrderedDict([
    ("keyw", "흰 건반 (PETG 흰색)"), ("keyb", "검은 건반 (PETG 검정)"), ("print", "출력물 PETG"), ("wood", "오꾸메 합판 11.5T"),
    ("metal", "구매 금속 (나사·자석·강철·스피커)"), ("felt", "펠트·패드 (건반 액션)"), ("rubber", "고무·EVA·실리콘"),
    ("elec", "전자부 (보드·모듈·배터리)"), ("screen", "화면 (Waveshare 7\")"), ("cable", "케이블·커넥터"), ("ctx", "건반 모듈 (참고, 연한 회색)")])
EXTRA_CSS = """
.P-keyw{fill:#fdfdfa;stroke:#39404d;stroke-width:.2;stroke-linejoin:round}
.P-keyb{fill:#454a53;stroke:#1d2433;stroke-width:.2;stroke-linejoin:round}
.S-keyw{fill:url(#hk);stroke:#1d2433;stroke-width:.35;stroke-linejoin:round}
.S-keyb{fill:#2a2d33;stroke:#1d2433;stroke-width:.3;stroke-linejoin:round}
.P-felt{fill:#ecc3bd;stroke:#39404d;stroke-width:.16}
.S-felt{fill:#d98c8c;stroke:#1d2433;stroke-width:.22}
.lt{font-family:%s;fill:#1d2433}
.cutl{fill:none;stroke:#1d2433;stroke-width:.7}
.tag{fill:#ffffff;stroke:#1d2433;stroke-width:.3}
""" % D.FONT
EXTRA_DEFS = '<pattern id="hk" patternUnits="userSpaceOnUse" width="1.4" height="1.4" patternTransform="rotate(45)">' \
             '<rect width="1.4" height="1.4" fill="#f7f7f3"/><line x1="0" y1="0" x2="0" y2="1.4" stroke="#9aa3b2" stroke-width=".14"/></pattern>'
ORDER = {"ctx": 0, "wood": 1, "print": 2, "keyw": 2, "keyb": 2, "felt": 3, "rubber": 3, "elec": 4, "metal": 5, "screen": 6, "cable": 7}


def cls_of(p, ctx_ka=False):
    """material class of a part (drawings.mclass, but the key action in its own materials unless ctx_ka)."""
    if not D.is_ka(p):
        return D.mclass(p)
    if ctx_ka:
        return "ctx"
    nm = p.name_ko
    if p.kind == "print":
        if nm.startswith("백건"):
            return "keyw"
        if nm.startswith("흑건"):
            return "keyb"
        return "print"
    if p.kind == "electronics":
        return "cable" if "-C-" in p.id else "elec"
    if p.kind == "consumable":
        return "rubber" if "EVA" in nm else "felt"
    return "metal"


# ------------------------------------------------------------------ sheet / view

class FSheet(D.Sheet):
    """drawings.Sheet with this set's register, paper size, title block and extra CSS."""

    def __init__(self, code, scale_txt):
        self.code = code
        self.file, self.name, self.paper = SHEETS[code]
        self.scale_txt = scale_txt
        self.w, self.h = PAPER[self.paper]
        self.L = {k: [] for k in D.LAYERS}
        self.tboxes = []
        self.used = set()
        self.views = []
        self.defs = []
        self.checks = []          # [(label, printed value, reference value, source)]

    def chk(self, label, printed, ref, src):
        self.checks.append(dict(sheet=self.code, label=label, printed=float(printed), ref=float(ref), src=src))

    def title_block(self, n_total=N_TOTAL):
        W, H = 210.0, 38.0
        x0, y0 = self.w - 10 - W, self.h - 10 - H
        self.rect(x0, y0, x0 + W, y0 + H, "grid", "over")
        self.add("over", '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#ffffff"/>' % (x0 + .2, y0 + .2, W - .4, H - .4))
        r1, r2, r3 = y0 + 13, y0 + 21, y0 + 29
        for yy in (r1, r2, r3):
            self.line([(x0, yy), (x0 + W, yy)], "grid2", "over")
        self.line([(x0 + 62, y0), (x0 + 62, r3)], "grid2", "over")
        self.line([(x0 + 162, y0), (x0 + 162, r1)], "grid2", "over")
        self.line([(x0 + 134, r1), (x0 + 134, r3)], "grid2", "over")
        self.line([(x0 + 152, r1), (x0 + 152, r2)], "grid2", "over")
        self.text(x0 + 3, y0 + 9.2, "Toccata", D.T_TITLE, bold=True, halo=False)
        self.text(x0 + 65, y0 + 4.4, "도면 이름", T_SMALL - 0.4, cls="tm", halo=False)
        self.text(x0 + 65, y0 + 10.6, self.name, 4.2 if text_w(self.name, 4.2) < 94 else 3.3, bold=True, halo=False)
        self.text(x0 + 165, y0 + 4.4, "도면 번호", T_SMALL - 0.4, cls="tm", halo=False)
        self.text(x0 + 165, y0 + 10.8, "%s / %d장" % (self.code, n_total), 5.0, bold=True, halo=False)
        self.text(x0 + 3, r1 + 5.6, "최종 설계도 (전체 6방향 · 내부)", T_SMALL, halo=False)
        self.text(x0 + 65, r1 + 3.6, "척도 (%s %g×%g 출력 기준)" % (self.paper, self.w, self.h), T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 65, r1 + 7.3, self.scale_txt, T_SMALL if text_w(self.scale_txt, T_SMALL) < 67 else T_SMALL - 0.5, halo=False)
        self.text(x0 + 137, r1 + 3.6, "단위", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 137, r1 + 7.3, "mm", T_SMALL, halo=False)
        self.text(x0 + 155, r1 + 3.6, "날짜", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 155, r1 + 7.3, DATE, T_SMALL, halo=False)
        self.text(x0 + 3, r2 + 5.6, "좌표: x 가로(0 = A0 왼쪽 끝) · y 흰 건반 앞 끝에서 뒤로 · z 책상에서 위로", T_SMALL - 0.4, halo=False)
        self.text(x0 + 137, r2 + 3.6, "설계 상태", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 137, r2 + 7.3, STATE, T_SMALL - 0.9, halo=False)
        self.text(x0 + 3, r3 + 3.7, "원본 (모든 선과 숫자는 이 생성기의 입체에서 계산 · src/drawings_final.py)", T_SMALL - 0.6, cls="tm", halo=False)
        self.text(x0 + 3, r3 + 7.5, SOURCES, T_SMALL - 0.6, halo=False)
        return (x0, y0, x0 + W, y0 + H)

    def legend2(self, x, y, mats, cols=1, colw=88.0, size=T_SMALL, extra=()):
        self.text(x, y, "범례", T_NOTE, bold=True, halo=False)
        y += 2.5
        items = [("S-" + m if m in ("wood", "print", "metal", "elec", "keyw") else "P-" + m, MAT[m]) for m in MAT if m in mats] + list(extra)
        per = int(math.ceil(len(items) / float(cols))) or 1
        for i, (cls, txt) in enumerate(items):
            cx = x + (i // per) * colw
            cy = y + (i % per) * 5.0
            if cls.startswith(("S-", "P-")) or cls in ("air", "zone", "sheetply"):
                self.rect(cx, cy, cx + 8, cy + 3.6, cls, "over")
            else:
                self.line([(cx, cy + 1.8), (cx + 8, cy + 1.8)], cls, "over")
            self.text(cx + 10, cy + 2.9, txt, size, halo=False)
        return y + per * 5.0

    def svg(self):
        W, H = self.w, self.h
        s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="0 0 %g %g">' % (W, H, W, H),
             "<title>Toccata %s %s</title>" % (self.code, D.esc(self.name)),
             "<defs><style>%s%s</style>%s%s%s</defs>" % (D.CSS, EXTRA_CSS, D.DEFS, EXTRA_DEFS, "".join(self.defs)),
             '<rect class="bg" x="0" y="0" width="%g" height="%g"/>' % (W, H),
             '<rect class="frame" x="10" y="10" width="%g" height="%g"/>' % (W - 20, H - 20)]
        for k in D.LAYERS:
            s.append('<g id="%s">' % k)
            s.extend(self.L[k])
            s.append("</g>")
        s.append("</svg>")
        return "\n".join(s)


class FView(D.View):
    """drawings.View + vflip (v grows downward on the sheet: the bottom view keeps the player side on top)."""

    def __init__(self, sh, k, win, at, flip=False, vflip=False):
        D.View.__init__(self, sh, k, win, at, flip)
        self.vflip = vflip

    def P(self, u, v):
        return (self.X + self.k * ((self.u1 - u) if self.flip else (u - self.u0)),
                self.Y + self.k * ((v - self.v0) if self.vflip else (self.v1 - v)))


# ------------------------------------------------------------------ hidden-surface raster

_RAST = None


def _rast_fn():
    global _RAST
    if _RAST is None:
        import numba

        @numba.njit(cache=True)
        def rast(P, F, ids, d, W, H, Z, I):
            for t in range(F.shape[0]):
                a, b, c = F[t, 0], F[t, 1], F[t, 2]
                x0, y0 = P[a, 0], P[a, 1]
                x1, y1 = P[b, 0], P[b, 1]
                x2, y2 = P[c, 0], P[c, 1]
                area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
                if abs(area) < 1e-12:
                    continue
                xmin = int(np.floor(min(x0, x1, x2) - 0.5))
                xmax = int(np.ceil(max(x0, x1, x2) - 0.5))
                ymin = int(np.floor(min(y0, y1, y2) - 0.5))
                ymax = int(np.ceil(max(y0, y1, y2) - 0.5))
                if xmax < 0 or ymax < 0 or xmin >= W or ymin >= H:
                    continue
                xmin = max(xmin, 0)
                ymin = max(ymin, 0)
                xmax = min(xmax, W - 1)
                ymax = min(ymax, H - 1)
                d0, d1, d2 = d[a], d[b], d[c]
                for py in range(ymin, ymax + 1):
                    yc = py + 0.5
                    for px in range(xmin, xmax + 1):
                        xc = px + 0.5
                        w0 = (x2 - x1) * (yc - y1) - (y2 - y1) * (xc - x1)
                        w1 = (x0 - x2) * (yc - y2) - (y0 - y2) * (xc - x2)
                        w2 = (x1 - x0) * (yc - y0) - (y1 - y0) * (xc - x0)
                        if area > 0:
                            if w0 < 0 or w1 < 0 or w2 < 0:
                                continue
                        else:
                            if w0 > 0 or w1 > 0 or w2 > 0:
                                continue
                        z = (w0 * d0 + w1 * d1 + w2 * d2) / area
                        if z > Z[py, px]:
                            Z[py, px] = z
                            I[py, px] = ids[t]
        _RAST = rast
    return _RAST


# view name -> (projection axis of drawings.proj, u index, v index, depth index, depth sign)
VIEWS = {"front": ("y", 0, 2, 1, -1), "rear": ("y", 0, 2, 1, 1), "left": ("x", 1, 2, 0, -1), "right": ("x", 1, 2, 0, 1),
         "top": ("z", 0, 1, 2, 1), "bottom": ("z", 0, 1, 2, -1)}
AX = {"x": 0, "y": 1, "z": 2}


class HLR:
    """hidden-surface drawing of solids: depth buffer -> per-part visible region (exact silhouettes) + draw order."""

    def __init__(self, M):
        self.M = M
        self._mesh = {}
        self._solid = {}
        self._proj = {}

    def solid(self, p, clips=()):
        """the part cut by clip half-spaces: clips = ((axis, '>' or '<', c), ...) keeps axis >= c / <= c."""
        key = (p.id, clips)
        if key in self._solid:
            return self._solid[key]
        m = p.solid
        b = self.M.bb(p)
        for ax, keep, c in clips:
            i = AX[ax]
            n = [0.0, 0.0, 0.0]
            if keep == ">":
                if b[i + 3] <= c:
                    m = None
                    break
                if b[i] < c:
                    n[i] = 1.0
                    m = m.trim_by_plane(tuple(n), c)
            else:
                if b[i] >= c:
                    m = None
                    break
                if b[i + 3] > c:
                    n[i] = -1.0
                    m = m.trim_by_plane(tuple(n), -c)
            if m.is_empty():
                m = None
                break
        self._solid[key] = m
        return m

    def mesh(self, p, clips=()):
        key = (p.id, clips)
        if key not in self._mesh:
            m = self.solid(p, clips)
            if m is None:
                self._mesh[key] = None
            else:
                t = m.to_mesh()
                self._mesh[key] = (np.asarray(t.vert_properties, float)[:, :3], np.asarray(t.tri_verts, np.int64))
        return self._mesh[key]

    def projection(self, p, axis, clips=()):
        key = (p.id, axis, clips)
        if key not in self._proj:
            m = self.solid(p, clips)
            self._proj[key] = None if m is None else proj(m, axis)
        return self._proj[key]

    def render(self, parts, view, win, r=0.2, clips=(), min_px=4, exact=True):
        """returns (items, info): items = [(part, visible CrossSection in (u, v))] far-to-near; info = buffers etc."""
        import cv2
        import networkx as nx
        from scipy import ndimage
        axis, iu, iv, idp, sg = VIEWS[view]
        u0, u1, v0, v1 = win
        W = int(math.ceil((u1 - u0) / r))
        H = int(math.ceil((v1 - v0) / r))
        Vs, Fs, Is = [], [], []
        off = 0
        plist = []
        for p in parts:
            b = self.M.bb(p)
            if b[iu + 3] < u0 or b[iu] > u1 or b[iv + 3] < v0 or b[iv] > v1:
                continue
            ms = self.mesh(p, clips)
            if ms is None:
                continue
            V, F = ms
            Vs.append(V)
            Fs.append(F + off)
            Is.append(np.full(len(F), len(plist), np.int32))
            plist.append(p)
            off += len(V)
        if not plist:
            return [], None
        V = np.vstack(Vs)
        F = np.vstack(Fs)
        ids = np.concatenate(Is)
        P = np.empty((len(V), 2))
        P[:, 0] = (V[:, iu] - u0) / r
        P[:, 1] = (v1 - V[:, iv]) / r
        dep = sg * V[:, idp]
        Z = np.full((H, W), -1e18)
        I = np.full((H, W), -1, np.int32)
        _rast_fn()(P, F, ids, dep, W, H, Z, I)
        n = len(plist)
        cnt = np.bincount(I[I >= 0], minlength=n)
        zsum = np.bincount(I[I >= 0], weights=Z[I >= 0], minlength=n)
        mdep = np.where(cnt > 0, zsum / np.maximum(cnt, 1), -1e18)
        # draw order from every shared edge: the nearer side of a depth step is drawn later
        votes = collections.Counter()
        for a, b_, za, zb in ((I[:, :-1], I[:, 1:], Z[:, :-1], Z[:, 1:]), (I[:-1, :], I[1:, :], Z[:-1, :], Z[1:, :])):
            m = (a != b_) & (a >= 0) & (b_ >= 0) & (np.abs(za - zb) > 0.05)
            fa = za[m] > zb[m]
            back = np.where(fa, b_[m], a[m]).astype(np.int64)
            front = np.where(fa, a[m], b_[m]).astype(np.int64)
            k, c = np.unique(back * n + front, return_counts=True)
            for kk, cc in zip(k.tolist(), c.tolist()):
                votes[kk] += cc
        G = nx.DiGraph()
        vis_ids = [i for i in range(n) if cnt[i] >= min_px]
        G.add_nodes_from(vis_ids)
        vs = set(vis_ids)
        for kk, cc in votes.items():
            bk, fr = divmod(kk, n)
            if bk in vs and fr in vs and cc > votes.get(fr * n + bk, 0):
                G.add_edge(bk, fr)
        C = nx.condensation(G)
        mem = C.graph["mapping"]
        scc_dep = collections.defaultdict(lambda: 1e18)
        for node, s in mem.items():
            scc_dep[s] = min(scc_dep[s], mdep[node])
        order = []
        for s in nx.lexicographical_topological_sort(C, key=lambda s: scc_dep[s]):
            order += sorted(C.nodes[s]["members"], key=lambda i: mdep[i])
        # visible regions
        objs = ndimage.find_objects(I + 1)
        items = []
        for i in order:
            sl = objs[i] if i < len(objs) else None
            if sl is None:
                continue
            rs, cs_ = sl
            sub = (I[rs, cs_] == i).astype(np.uint8)
            sub = np.pad(sub, 1)
            cont, hier = cv2.findContours(sub, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
            pl = []
            for c in cont:
                if len(c) < 3:
                    if len(c) >= 1:      # one- or two-pixel region: a tiny square
                        q = c[:, 0, :].astype(float)
                        cx, cy = q.mean(0)
                        q = np.array([[cx - .5, cy - .5], [cx + .5, cy - .5], [cx + .5, cy + .5], [cx - .5, cy + .5]])
                    else:
                        continue
                else:
                    q = cv2.approxPolyDP(c, 0.6, True)[:, 0, :].astype(float)
                    if len(q) < 3:
                        q = c[:, 0, :].astype(float)
                uu = u0 + (q[:, 0] - 1 + cs_.start + 0.5) * r
                vv = v1 - (q[:, 1] - 1 + rs.start + 0.5) * r
                pl.append(np.column_stack([uu, vv]))
            if not pl:
                continue
            rcs = CrossSection(pl, FillRule.EvenOdd)
            p = plist[i]
            if exact and cnt[i] >= 150:
                pj = self.projection(p, axis, clips)
                g = rcs.offset(1.5 * r, JoinType.Miter, 2.0)
                v_cs = g ^ pj if pj is not None else rcs.offset(0.5 * r, JoinType.Miter, 2.0)
                if v_cs.is_empty() or v_cs.area() < 0.25 * rcs.area():
                    v_cs = rcs.offset(0.5 * r, JoinType.Miter, 2.0)
            else:
                v_cs = rcs.offset(0.5 * r, JoinType.Miter, 2.0)
            if v_cs.is_empty():
                continue
            items.append((p, v_cs))
        info = dict(I=I, Z=Z, plist=plist, cnt=cnt, r=r, win=win, view=view)
        return items, info


def draw_items(view, items, ctx_ka=False, prefix="P-", cls_fn=None):
    for p, cs in items:
        c = cls_fn(p) if cls_fn else cls_of(p, ctx_ka)
        view.sh.used.add(c)
        view.area(polys(cs), prefix + c)


def draw_cut(view, items, ctx_ka=False):
    for p, cs in items:
        c = cls_of(p, ctx_ka)
        view.sh.used.add(c)
        view.area(polys(cs), "S-" + c)


def section_items(M, parts, axis, c, clip=None):
    out = []
    i = AX[axis]
    for p in parts:
        b = M.bb(p)
        if not (b[i] < c < b[i + 3]):
            continue
        cs = sec(p.solid, axis, c)
        if clip is not None:
            cs = cs ^ clip
        if cs.is_empty() or cs.area() < 1e-4:
            continue
        out.append((p, cs))
    out.sort(key=lambda t: ORDER[cls_of(t[0])])
    return out


# ------------------------------------------------------------------ names and groups

_KEYNAME = re.compile(r"^(백건|흑건) [A-G]#?\d$")
_TAIL = [re.compile(r"\s*\((?:[A-G]#?\d|[LR]\d?|칸\d|왼쪽|오른쪽)\)$"), re.compile(r"\s+O\d$"), re.compile(r"\s+[LR]\d?$"), re.compile(r"\s+[A-G]#?\d$"),
         re.compile(r"(?<![×x*])\s+\d$"), re.compile(r"\s+끝 부속 (?:왼쪽|오른쪽)$"), re.compile(r"\s*칸\d$"), re.compile(r"\s+(?:왼쪽|오른쪽)$")]


def gname(p):
    """group name for counting identical things (keys of every note -> 흰 건반 / 검은 건반, L/R / numbered instances merged)."""
    nm = p.name_ko
    if _KEYNAME.match(nm):
        return "흰 건반 (PETG 흰색)" if nm.startswith("백건") else "검은 건반 (PETG 검정)"
    s = D.short(nm)
    for _ in range(3):
        for rx in _TAIL:
            s = rx.sub("", s)
    s = s.replace("끝부속", "").strip()
    return s


ROOT = os.path.normpath(os.path.join(OUT, "..", "..", ".."))
ITEMS_JSON = os.path.join(ROOT, "docs", "report", "toccata-v4", "data", "final_items.json")
PARTS_DATA = os.path.join(OUT, "drawings", "parts", "data")
_CODES = None


def _code_maps():
    """part id -> codes the user can look up:
    - bought / electronics / consumable / plywood: the final item id (i### / u## / t##) through final_items.json cad_match.ids
      (the ids of the 06 parts tab; build_items.py applied its rules to the non-printed parts to make that list);
    - printed parts and plywood: the part-sheet code P-xx-yy / P-PLY-xx of the 03 tab (drawings/parts/data/*.json, via the
      print file of manifest.json for printed parts).
    Nothing is read out of part names."""
    global _CODES
    if _CODES is not None:
        return _CODES
    with open(ITEMS_JSON, encoding="utf-8") as fh:
        fi = json.load(fh)
    by_id = collections.defaultdict(list)
    for it in fi["items"]:
        for pid in (it.get("cad_match") or {}).get("ids", []):
            if it["id"] not in by_id[pid]:
                by_id[pid].append(it["id"])
    f2code, inst2code = {}, {}
    if os.path.isdir(PARTS_DATA):
        for f in sorted(os.listdir(PARTS_DATA)):
            if not f.endswith(".json"):
                continue
            with open(os.path.join(PARTS_DATA, f), encoding="utf-8") as fh:
                d = json.load(fh)
            if d.get("file"):
                f2code[d["file"]] = d["code"]
            if d.get("inst"):
                inst2code.setdefault(d["inst"], d["code"])
    with open(os.path.join(OUT, "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    pcode = {}
    for it in man["print"]:
        c = f2code.get(it["file"])
        if c:
            for pid in it.get("ids", []):
                pcode[pid] = c
    for pid, c in inst2code.items():
        if c.startswith("P-PLY-"):
            pcode.setdefault(pid, c)
    _CODES = (by_id, pcode)
    return _CODES


def part_codes(p):
    """[item ids..., part-sheet code] of one part (the folded screen parts '-FOLD' use the codes of the unfolded ones)."""
    by_id, pcode = _code_maps()
    pid = p.id[:-5] if p.id.endswith("-FOLD") else p.id
    out = list(by_id.get(pid, []))       # cad_match.ids already hold the result of its rules (applied to non-printed parts only)
    if pid in pcode:
        out.append(pcode[pid])
    return out


def codes_of(ps):
    """codes of a group of parts, item ids (i/u/t) before part-sheet codes (P-), each once."""
    items, sheets = [], []
    for p in ps:
        for c in part_codes(p):
            lst = sheets if c.startswith("P-") else items
            if c not in lst:
                lst.append(c)
    return items + sheets


def codes_txt(ps, n=2):
    cs = codes_of(ps)
    if not cs:
        return "-"
    return ", ".join(cs[:n]) + (" 외 %d" % (len(cs) - n) if len(cs) > n else "")


CODE_HEAD = "코드 = 06 탭 물건 번호 (i····u··) · 03 탭 출력·합판 부품 도면 번호 (P-··-··)"
CODE_HEAD_SHORT = "코드: i·u = 06 탭 물건 번호 · P- = 03 탭 부품 도면 번호"


def anchor(view, cs):
    pt = D.best_inner(cs)
    return view.P(pt[0], pt[1]) if pt else None


def merge_cs(css):
    out = CrossSection()
    for c in css:
        out = out + c
    return out


def vis_groups(items, min_area=1.0, key=gname):
    """visible items grouped by name: [(name, [parts], union of visible regions)] largest first."""
    g = collections.OrderedDict()
    for p, cs in items:
        g.setdefault(key(p), []).append((p, cs))
    out = []
    for nm, lst in g.items():
        u = merge_cs([c for _, c in lst])
        if u.area() >= min_area:
            out.append((nm, [p for p, _ in lst], u))
    out.sort(key=lambda t: -t[2].area())
    return out


# ------------------------------------------------------------------ common drawing helpers

def ground(view, u0, u1, step=10.0, flip=False):
    """desk line z0 with hatch ticks (front / side views)."""
    view.seg((u0, 0.0), (u1, 0.0), "vis")
    i = math.ceil(u0 / step) * step + step / 2
    while i < u1:
        view.seg((i, 0.0), (i + step * 0.4 * (-1 if flip else 1), -step * 0.3), "thin")
        i += step


def heading2(sh, x, y, s, sub=None, size=T_HEAD):
    sh.text(x, y, s, size, bold=True)
    if sub:
        sh.text(x + text_w(s, size) + 3, y, sub, T_NOTE, cls="tm")


def write(sh):
    os.makedirs(FIN, exist_ok=True)
    p = os.path.join(FIN, sh.file + ".svg")
    s = sh.svg()
    s = re.sub(r"(\d+\.\d{2})\d+", r"\1", s)   # 0.01 mm is enough everywhere
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(s)
    return p, sh.check()


# ------------------------------------------------------------------ reference data for the self check

_MAN = None


def man_bb(pid):
    """bounding box of a part as written to manifest.json by the last build_all run (independent of this run)."""
    global _MAN
    if _MAN is None:
        with open(os.path.join(OUT, "manifest.json"), encoding="utf-8") as fh:
            _MAN = {p["id"]: p["bbox"] for p in json.load(fh)["parts"]}
    return _MAN[pid]


def man_union(pids):
    bs = [man_bb(i) for i in pids]
    return [min(b[i] for b in bs) for i in range(3)] + [max(b[i] for b in bs) for i in range(3, 6)]


# ------------------------------------------------------------------ view helpers

def ext_view(sh, Hh, parts, view, win, k, at, r=0.2, ctx_ka=False, clips=(), flip=False, vflip=False):
    v = FView(sh, k, win, at, flip=flip, vflip=vflip)
    items, info = Hh.render(parts, view, win, r=r, clips=clips)
    draw_items(v, items, ctx_ka)
    return v, items, info


def item_map(items):
    out = collections.defaultdict(list)
    for p, cs in items:
        out[p.id].append(cs)
    return {k: merge_cs(v) for k, v in out.items()}


def anchor_ids(view, vis, ids):
    css = [vis[i] for i in ids if i in vis]
    if not css:
        return None
    u = merge_cs(css)
    if u.is_empty():
        return None
    pt = D.best_inner(u)
    return view.P(pt[0], pt[1]) if pt else None


def ords_v(sh, view, zs, side=-1, gap=1.0, lo=None, hi=None, cls="td"):
    x0, y0, x1, y1 = view.rect
    xb = x0 - gap if side < 0 else x1 + gap
    sh.ordinates_v([(view.Py(z), None, fnum(z), cls) for z in sorted(set(round(z, 2) for z in zs))], xb, side,
                   lo=y0 - 3 if lo is None else lo, hi=y1 + 3 if hi is None else hi)


def ords_h(sh, view, us, side=1, gap=2.0, lo=None, hi=None, cls="td", base=None):
    x0, y0, x1, y1 = view.rect
    yb = (y1 + gap if side > 0 else y0 - gap) if base is None else base
    sh.ordinates_h([(view.Px(u), None, fnum(u), cls) for u in sorted(set(round(u, 2) for u in us))], yb, side,
                   lo=x0 - 4 if lo is None else lo, hi=x1 + 4 if hi is None else hi)


def visible_table(sh, x, y, groups, M, axes, title, maxrows=18, size=T_SMALL - 0.2, rh=3.7, name_w=74.0, min_area=4.0):
    """table of the things seen in a view, grouped by name: count of instances seen, bbox along the two view axes."""
    rows = []
    for nm, ps, u in groups:
        if u.area() < min_area:
            continue
        bb = M.bbox([p.id for p in ps])
        rr = [nm if text_w(nm, size) < name_w - 2 else nm[:int(len(nm) * (name_w - 4) / text_w(nm, size))] + "…", str(len(ps))]
        for a in axes:
            i = AX[a]
            rr.append("%s ~ %s" % (fnum(bb[i], 1), fnum(bb[i + 3], 1)))
        rows.append(rr)
        if len(rows) >= maxrows:
            break
    sh.text(x, y, title, T_NOTE + 0.4, bold=True, halo=False)
    cols = [("이름 (부품 이름에서)", name_w, "start"), ("보이는 수", 15.0, "middle")] + [(a, 30.0, "start") for a in axes]
    return sh.table(x, y + 2.5, cols, rows, size=size, rh=rh)


def bbox_of(M, pred):
    ps = [p for p in M.parts if pred(p)]
    return M.bbox([p.id for p in ps]), ps


def hole_of(M, pid, axis, c, near):
    """the hole of a part's section nearest to (u, v)."""
    hs = D.hole_list(sec(M.by[pid].solid, axis, c))
    return min(hs, key=lambda h: math.hypot(h["cu"] - near[0], h["cv"] - near[1])) if hs else None


def mark_hole(view, h, r_extra=1.6):
    view.centre_mark(h["cu"], h["cv"], 0.5 * view.k * max(h["w"], h["h"]) + r_extra)


def sz_txt(h):
    return ("Ø%s" % fnum(h["d"], 2)) if h["round"] else ("%s × %s" % (fnum(h["w"], 2), fnum(h["h"], 2)))


def use_parts(M):
    return M.ka + M.rear


def black_w_model():
    """black key head width as written in the key-action generator (independent reference for the E01 check)."""
    src = os.path.normpath(os.path.join(OUT, "..", "key-action-v4", "model", "model_v4.py"))
    with open(src, encoding="utf-8") as fh:
        m = re.search(r"\bblack_w=([\d.]+)", fh.read())
    return float(m.group(1))


# ------------------------------------------------------------------ E01 front

def module_x(M):
    """module joints from the frame solids: [(name, x0, x1)] EL, O1..O7, ER."""
    out = [("EL", M.bb(M.by["EL-FRAME"])[0], M.bb(M.by["O1-FRAME"])[0])]
    for k in range(1, 8):
        b = M.bb(M.by["O%d-FRAME" % k])
        out.append(("O%d" % k, b[0], b[0] + 164.5 if k < 7 else M.bb(M.by["ER-FRAME"])[0]))
    out.append(("ER", M.bb(M.by["ER-FRAME"])[0], M.bb(M.by["ER-FRAME"])[3]))
    return out


def cheek_x(M):
    """cheek (볼) x ranges from the end frames' section at z60 (the part of the end frame that rises to the top)."""
    out = {}
    for s, pid in (("L", "EL-FRAME"), ("R", "ER-FRAME")):
        pl = [q for q in polys(sec(M.by[pid].solid, "z", 60.0)) if signed_area(q) > 0]
        big = max(pl, key=lambda q: abs(signed_area(q)) if (q[:, 1].max() - q[:, 1].min()) > 200 else 0)
        out[s] = (float(big[:, 0].min()), float(big[:, 0].max()))
    return out


def key_parts(M, white=True):
    return [p for p in M.ka if _KEYNAME.match(p.name_ko) and p.name_ko.startswith("백건" if white else "흑건")]


def sheet_E01(M, Hh):
    import body
    import touchscreen_rev3 as TS
    sh = FSheet("E01", "1:2.5 · 확대 1:1, 1:1.5")
    use = use_parts(M)
    allb = M.bbox([p.id for p in use])
    heading2(sh, 16, 21, "정면도 — 연주자 자리에서 봄 (사용 상태, 화면 25°)", "1:2.5 · 숨은 선은 그리지 않음 (깊이 버퍼로 앞뒤를 가려 그림)")
    win = (-24.0, 1246.0, -3.0, 196.0)
    k1 = 0.4
    v, items, info = ext_view(sh, Hh, use, "front", win, k1, (48.0, 52.0))
    x0, y0, x1, y1 = v.rect
    ground(v, win[0], win[1], 10)
    vis = item_map(items)
    # dims above: pods / centre widths (at the speaker tops), overall
    L, R, cu = body.SPK_X["L"], body.SPK_X["R"], body.CU_X
    chain = [L[0], L[1], cu[0], cu[1], R[0], R[1]]
    tops = {L[0]: body.SPK_ZT, L[1]: body.SPK_ZT, cu[0]: body.Z_LID, cu[1]: body.Z_LID, R[0]: body.SPK_ZT, R[1]: body.SPK_ZT}
    ya, yb_ = y0 - 4.0, y0 - 11.0
    for a, b_ in zip(chain[:-1], chain[1:]):
        sh.dim_h(v.Px(a), v.Px(b_), ya, fnum(b_ - a), ext=[(v.Px(a), v.Py(tops[a])), (v.Px(b_), v.Py(tops[b_]))],
                 out_side="left" if (b_ - a) < 10 and a < 611 else "right")
    sh.dim_h(v.Px(allb[0]), v.Px(allb[3]), yb_, "전체 폭 %s (x%s ~ %s)" % (fnum(allb[3] - allb[0]), fnum(allb[0]), fnum(allb[3])),
             ext=[(v.Px(allb[0]), ya), (v.Px(allb[3]), ya)])
    mu = man_union([p.id for p in use])
    sh.chk("전체 폭", allb[3] - allb[0], mu[3] - mu[0], "manifest.json bbox (모든 부품)")
    sh.chk("스피커 L 폭", L[1] - L[0], man_union([p.id for p in M.rear if p.group == body.G_SPK["L"]])[3] - man_union([p.id for p in M.rear if p.group == body.G_SPK["L"]])[0], "manifest 스피커 파트 L")
    sh.chk("가운데 유닛 폭", cu[1] - cu[0], man_bb("CU-PLY-BACK")[3] - man_bb("CU-PLY-BACK")[0], "manifest CU-PLY-BACK")
    # z ordinates (left) and the screen glass (right)
    wk, bk = key_parts(M, True), key_parts(M, False)
    wkb, bkb = M.bbox([p.id for p in wk]), M.bbox([p.id for p in bk])
    fr = M.bbox([p.id for p in M.ka if p.group.endswith("프레임")])
    gl = M.bbox(["SPKL-GRILLE"])
    cr = M.bb(M.by["TS-CRADLE"])
    scr = M.bb(M.by["TS-E-SCREEN"])
    zs = [0.0, M.bb(M.by["O4-EVA"])[5], wkb[5], bkb[5], fr[5], gl[2], body.DRV_YZ[1], body.SPK_ZT, cr[5]]
    ords_v(sh, v, zs, -1, gap=2.0)
    sh.text(x0 - 2, y0 - 3.5, "z", T_SMALL, "end", cls="tm")
    ords_v(sh, v, [scr[2], scr[5]], 1, gap=2.0, lo=y0 + 4, hi=y1)
    sh.text(x1 + 2, y0 + 1.0, "z 화면 유리", T_SMALL, cls="tm")
    sh.chk("화면 받침 위 끝 z", cr[5], man_bb("TS-CRADLE")[5], "manifest TS-CRADLE")
    sh.chk("스피커 윗면 z", body.SPK_ZT, man_bb("SPKL-PLY-TOP")[5], "manifest SPKL-PLY-TOP")
    sh.chk("건반 바닥 윗면(모듈 윗판) z", fr[5], man_bb("O4-FRAME")[5], "manifest O4-FRAME")
    sh.chk("흰 건반 윗면 z", wkb[5], man_bb("O4-KEY-C")[5], "manifest O4-KEY-C")
    sh.chk("검은 건반 윗면 z", bkb[5], man_bb("O4-KEY-Cs")[5], "manifest O4-KEY-Cs")
    # driver centres, grille edges, screen
    for s in "LR":
        v.centre_mark(body.DRV_X[s], body.DRV_YZ[1], 3.0)
    gr = M.bbox(["SPKR-GRILLE"])
    xs = [m[1] for m in module_x(M)] + [allb[3], gl[0], gl[3], gr[0], gr[3], body.DRV_X["L"], body.DRV_X["R"], cr[0], cr[3], TS.XC]
    ords_h(sh, v, xs, 1, gap=2.0)
    sh.text(x0 - 3, y1 + 3.6, "x", T_SMALL, "end", cls="tm")
    # callouts below
    jh = hole_of(M, "EL-FRAME", "y", 1.0, (-8.3, 20.5))
    co = []
    for pid, lab in (("SPKL-GRILLE", "스피커 L 육각 그릴 (앞판 %s°)" % fnum(body.ANGLE)), ("SPKR-BAFFLE", "스피커 R 앞판 (출력)"),
                     ("TS-E-SCREEN", "화면 Waveshare 7-DSI-TOUCH-C"), ("TS-CRADLE", "화면 받침 (출력)"),
                     ("EL-FRAME", "볼 L (끝 부속 왼쪽 프레임)"), ("ER-FRAME", "볼 R"), ("O4-EVA", "EVA 3T 바닥 (모듈마다)")):
        a = anchor_ids(v, vis, [pid])
        if a:
            co.append(a + (lab,))
    a = anchor_ids(v, vis, [p.id for p in wk])
    co.append(a + ("흰 건반 %d개" % len(wk),))
    a = anchor_ids(v, vis, [p.id for p in bk])
    co.append(a + ("검은 건반 %d개" % len(bk),))
    if jh:
        co.append(v.P(jh["cu"], jh["cv"]) + ("헤드폰 잭 J701 구멍",))
    sh.callouts_h(co, y1 + 24.0, 1, x0, x1, size=T_NOTE)

    # ---- detail A: left cheek + J701 (1:1)
    wa = (-22.0, 52.0, -3.0, 78.0)
    ya0 = y1 + 56.0
    heading2(sh, 16, ya0 - 20, "확대 A — 볼 L과 헤드폰 잭 J701", "1:1", size=T_HEAD - 0.6)
    va, ita, _ = ext_view(sh, Hh, use, "front", wa, 1.0, (40.0, ya0), r=0.08)
    ax0, ay0, ax1, ay1 = va.rect
    va.frame()
    ground(va, wa[0], wa[1], 4)
    ck = cheek_x(M)
    if jh:
        mark_hole(va, jh)
    ka = [p for p in wk + bk if M.bb(p)[3] < 52]
    xsa = [ck["L"][0], ck["L"][1]] + [M.bb(p)[i] for p in ka for i in (0, 3)] + ([jh["cu"]] if jh else [])
    ords_h(sh, va, xsa, 1, gap=2.0)
    zsa = [0.0, M.bb(M.by["EL-EVA"])[5], fr[5], wkb[5], bkb[5]] + ([jh["cv"]] if jh else [])
    ords_v(sh, va, zsa, -1, gap=2.0)
    if jh:
        sh.callouts_v([va.P(jh["cu"] - jh["w"] / 2, jh["cv"]) + ("J701 구멍 %s\n중심 x%s z%s" % (sz_txt(jh), fnum(jh["cu"]), fnum(jh["cv"])),)],
                      ax1 + 4, 1, ay0, ay1, size=T_SMALL)
    sh.chk("볼 L 폭", ck["L"][1] - ck["L"][0], 15.8, "keyaction 볼 두께 (EL-FRAME 단면 z60)")

    # ---- detail B: O4 key fronts (1:1)
    o4 = M.bb(M.by["O4-FRAME"])
    wb = (o4[0] - 4.0, o4[3] + 4.0, -3.0, 78.0)
    bx = 168.0
    heading2(sh, bx, ya0 - 20, "확대 B — O4 건반 앞모습 (C4~B4, 모듈 x%s~%s)" % (fnum(o4[0]), fnum(o4[3])), "1:1", size=T_HEAD - 0.6)
    vb, itb, _ = ext_view(sh, Hh, use, "front", wb, 1.0, (bx, ya0), r=0.08)
    bx0, by0, bx1, by1 = vb.rect
    vb.frame()
    ground(vb, wb[0], wb[1], 4)
    o4w = [p for p in wk if p.group.startswith("O4")]
    o4b = [p for p in bk if p.group.startswith("O4")]
    xsb = [M.bb(p)[i] for p in o4w for i in (0, 3)]
    ords_h(sh, vb, xsb, 1, gap=2.0)
    # black keys: head edges from a section at y100 (the bounding box also holds the tail, which is offset sideways up to ~1)
    yh = 100.0
    bkh = [(p, sec(p.solid, "y", yh).bounds()) for p in o4b]
    xbk = [hb[i] for _, hb in bkh for i in (0, 2)]
    ords_h(sh, vb, xbk, -1, gap=2.0)
    zsb = [0.0, M.bb(M.by["O4-EVA"])[5], wkb[2], wkb[5], bkb[5], fr[5]]
    ords_v(sh, vb, zsb, -1, gap=2.0)
    ws = sorted(M.bb(p)[3] - M.bb(p)[0] for p in o4w)
    pitch = M.bb(o4w[1])[0] - M.bb(o4w[0])[0]
    bws = sorted(hb[2] - hb[0] for _, hb in bkh)
    tail = max(max(hb[0] - M.bb(p)[0], M.bb(p)[3] - hb[2]) for p, hb in bkh)
    bw_txt = fnum(bws[0]) if abs(bws[-1] - bws[0]) < 0.005 else "%s~%s" % (fnum(bws[0]), fnum(bws[-1]))
    sh.textblock(bx, by1 + 20.0, ["흰 건반 폭 %s (앞면 기준), 피치 %s, 틈 %s · 검은 건반 머리 폭 %s (y%s 단면, %d개 모두)"
                                   % (fnum(ws[0]), fnum(pitch), fnum(pitch - ws[0]), bw_txt, fnum(yh), len(bkh)),
                                   "검은 건반 꼬리는 머리보다 옆으로 최대 %s 비켜 있음 (위에서만 보임) · 위: 흰 건반 x, 아래(안쪽 위): 검은 건반 머리 x"
                                   % ("%.1f" % tail)], T_SMALL, cls="tm")
    sh.chk("흰 건반 폭", ws[0], man_bb("O4-KEY-C")[3] - man_bb("O4-KEY-C")[0], "manifest O4-KEY-C")
    sh.chk("검은 건반 머리 폭 (y%s 단면)" % fnum(yh), bws[-1], black_w_model(), "key-action-v4/model/model_v4.py black_w")

    # ---- detail C: screen front (1:1.5)
    k3 = 1 / 1.5
    wcs = (518.0, 704.0, 70.0, 194.0)
    cx = 380.0
    heading2(sh, cx, ya0 - 20, "확대 C — 화면 (정면)", "1:1.5 · 25° 기울어 짧게 보임", size=T_HEAD - 0.6)
    vcs, itc, _ = ext_view(sh, Hh, use, "front", wcs, k3, (cx + 22.0, ya0 - 6.0), r=0.1)
    vcs.frame()
    ords_h(sh, vcs, [cr[0], scr[0], TS.XC, scr[3], cr[3]], 1, gap=2.0)
    ords_v(sh, vcs, [body.Z_LID, scr[2], scr[5], cr[5]], -1, gap=2.0)
    sh.chk("화면 받침 폭", cr[3] - cr[0], man_bb("TS-CRADLE")[3] - man_bb("TS-CRADLE")[0], "manifest TS-CRADLE")

    # ---- table + legend + notes
    groups = vis_groups(items, 2.0)
    visible_table(sh, 16, 312.0, groups, M, ("x", "z"), "정면에서 보이는 것 (보이는 넓이 순, 좌표는 입체의 바깥 상자)", maxrows=14, rh=3.6)
    sh.legend2(372, 300, sh.used, cols=2, colw=100)
    sh.scale_bar(200, 318, k1, 200, 50, "1:2.5")
    sh.scale_bar(200, 332, 1.0, 40, 10, "1:1")
    sh.scale_bar(290, 332, k3, 60, 20, "1:1.5")
    D.notes_box(sh, 200, 345, 170, "읽는 법", [
        "모든 x는 A0 왼쪽 끝(x0)에서, z는 책상(z0)에서 잰 값입니다. 모듈 이음은 x47 + 164.5·k.",
        "스피커 앞판은 수평에서 %s° 누운 면이라 정면에서는 그릴이 납작하게 보입니다 (실제 경사 길이 %s, D02)." % (fnum(body.ANGLE), fnum(body.SL_LEN)),
        "화면은 경첩 축(y%s z%s)에서 뒤로 %s° 기울어 있습니다 (E03 옆모습, D05)." % (fnum(TS.AX_Y), fnum(TS.AX_Z), fnum(TS.TILT_USE)),
    ], size=T_SMALL)
    sh.title_block()
    return sh


def chain_dims(sh, v, y_top, allb, tops=None, label_all=True):
    """pod / gap / centre / gap / pod chain + overall width above a view (x along the view)."""
    import body
    L, R, cu = body.SPK_X["L"], body.SPK_X["R"], body.CU_X
    chain = [L[0], L[1], cu[0], cu[1], R[0], R[1]]
    ya, yb_ = y_top - 4.0, y_top - 11.0
    for a, b_ in zip(chain[:-1], chain[1:]):
        ext = [(v.Px(a), v.Py(tops[a])), (v.Px(b_), v.Py(tops[b_]))] if tops else [(v.Px(a), y_top), (v.Px(b_), y_top)]
        small = (b_ - a) < 10
        side = "right"
        if small:
            side = ("left" if a < 611 else "right") if not v.flip else ("right" if a < 611 else "left")
        sh.dim_h(v.Px(a), v.Px(b_), ya, fnum(b_ - a), ext=ext, out_side=side)
    if label_all:
        sh.dim_h(v.Px(allb[0]), v.Px(allb[3]), yb_, "전체 폭 %s (x%s ~ %s)" % (fnum(allb[3] - allb[0]), fnum(allb[0]), fnum(allb[3])),
                 ext=[(v.Px(allb[0]), ya), (v.Px(allb[3]), ya)])


def callouts_for(v, vis, spec):
    """spec: [(ids or regex, label)] -> callout items anchored on the visible part of those parts."""
    out = []
    for key, lab in spec:
        if isinstance(key, str):
            ids = [i for i in vis if re.match(key, i)]
        else:
            ids = [i for i in key if i in vis]
        a = anchor_ids(v, vis, ids)
        if a:
            out.append(a + (lab,))
    return out


def feet(M):
    fs = [p for p in M.rear if p.id.startswith("FOOT-")]
    return fs, sorted(set((round((M.bb(p)[0] + M.bb(p)[3]) / 2, 2), round((M.bb(p)[1] + M.bb(p)[4]) / 2, 2)) for p in fs))


# ------------------------------------------------------------------ E02 rear

def sheet_E02(M, Hh):
    import body
    import touchscreen_rev3 as TS
    sh = FSheet("E02", "1:2.5 · 확대 1:1")
    use = use_parts(M)
    allb = M.bbox([p.id for p in use])
    heading2(sh, 16, 21, "배면도 — 뒤에서 봄 (오른쪽 스피커가 왼쪽에 보임)", "1:2.5 · 사용 상태 · 숨은 선 없음")
    win = (-24.0, 1246.0, -3.0, 196.0)
    k1 = 0.4
    v, items, info = ext_view(sh, Hh, use, "rear", win, k1, (48.0, 52.0), flip=True)
    x0, y0, x1, y1 = v.rect
    ground(v, win[0], win[1], 10, flip=True)
    vis = item_map(items)
    tops = {body.SPK_X["L"][0]: body.SPK_ZT, body.SPK_X["L"][1]: body.SPK_ZT, body.CU_X[0]: body.Z_LID, body.CU_X[1]: body.Z_LID,
            body.SPK_X["R"][0]: body.SPK_ZT, body.SPK_X["R"][1]: body.SPK_ZT}
    chain_dims(sh, v, y0, allb, tops)
    cr = M.bb(M.by["TS-CRADLE"])
    bp = M.bb(M.by["PR-BACKPLATE"])
    zs = [0.0, body.ZB, body.Z_BOT, body.Z_LIDU, body.Z_LID, body.SPK_ZT, cr[5]]
    ords_v(sh, v, zs, -1, gap=2.0)
    sh.text(x0 - 2, y0 - 3.5, "z", T_SMALL, "end", cls="tm")
    fs, fc = feet(M)
    vents = [h for h in D.plate_holes(M, "CU-PLY-BACK", "y", body.YB - body.T / 2) if h["w"] < 100]
    leg = M.bb(M.by["TS-LEG"])
    xs = sorted(set([f[0] for f in fc] + [bp[0], bp[3], vents[0]["cu"], vents[-1]["cu"], cr[0], cr[3], TS.XC]))
    ords_h(sh, v, xs, 1, gap=2.0)
    sh.text(x1 + 2, y1 + 3.6, "x", T_SMALL, cls="tm")
    co = callouts_for(v, vis, [
        ("SPKR-PLY-BACK", "스피커 R 뒤판 (오꾸메)"), ("SPKL-PLY-BACK", "스피커 L 뒤판"), ("CU-PLY-BACK", "가운데 유닛 뒤판 (오꾸메)"),
        ("PR-BACKPLATE", "뒤판 출력물 (I/O·루버)"), ("TS-CRADLE", "화면 받침 뒷면"), ("TS-LEG", "받침다리"), ("TS-WINCOVER", "점검창 덮개"),
        (r"FOOT-\d+$", "고무발 28×5 (%d개)" % len(fs)), ("SPKL-PLY-SIDEOUT", "스피커 L 바깥 옆판"), ("SPKR-PLY-SIDEOUT", "스피커 R 바깥 옆판")])
    if vents:
        h = vents[len(vents) // 2]
        co.append(v.P(h["cu"], h["cv"]) + ("앰프 뒤 환기 구멍 Ø%s ×%d" % (fnum(vents[0]["d"], 1), len(vents)),))
    sh.callouts_h(co, y1 + 24.0, 1, x0, x1, size=T_NOTE)
    sh.chk("뒤판 출력물 x 범위 폭", bp[3] - bp[0], man_bb("PR-BACKPLATE")[3] - man_bb("PR-BACKPLATE")[0], "manifest PR-BACKPLATE")
    sh.chk("고무발 수", len(fs), len(body.L2["feet"]["positions_xy"]["pod_L"]) * 2 + len(body.L2["feet"]["positions_xy"]["centre"]), "spec feet.positions_xy")

    # ---- detail C: the centre rear x380..860 at 1:1 (seen from behind: +x to the left)
    wc = (380.0, 862.0, -3.0, 80.0)
    yc0 = y1 + 64.0
    heading2(sh, 16, yc0 - 22, "확대 C — 가운데 유닛 뒷면 (I/O 판 · 환기 구멍)", "1:1 · 뒤에서 봄, x가 오른쪽에서 왼쪽으로 커짐", size=T_HEAD - 0.6)
    vc, itc, _ = ext_view(sh, Hh, use, "rear", wc, 1.0, (52.0, yc0), r=0.1, flip=True)
    cx0, cy0, cx1, cy1 = vc.rect
    vc.frame()
    ground(vc, wc[0], wc[1], 5, flip=True)
    holes = D.plate_holes(M, "PR-BACKPLATE", "y", body.YB - body.BP_SKIN / 2)
    louv = [h for h in holes if h["w"] > 30]
    small = [h for h in holes if h["w"] <= 30]
    spec = body.BP["holes_xz"]
    rows = []
    xo, zo = set([bp[0], bp[3]]), set([body.ZB, body.Z_BOT, body.Z_LIDU, body.Z_LID])
    # the outer skin is YB-2..YB; the switch sits in a 2 mm panel behind it (YB-4..YB-2) whose cut-out is the snap-in hole,
    # while the skin only has the bezel recess - so each opening is measured in both layers and the narrowest is the hole
    y_sk0 = body.YB - body.BP_SKIN
    inner = D.plate_holes(M, "PR-BACKPLATE", "y", y_sk0 - 1.0)
    for h in sorted(small, key=lambda h: h["cu"]):
        key = min(spec, key=lambda kk: math.hypot(spec[kk][0] - h["cu"], spec[kk][1] - h["cv"]))
        nm = next((vv for kk, vv in D.BP_NAMES.items() if key.startswith(kk)), key)
        mark_hole(vc, h, 2.0)
        xo.add(h["cu"])
        zo.add(h["cv"])
        hi = [g for g in inner if math.hypot(g["cu"] - h["cu"], g["cv"] - h["cv"]) < 0.5 and g["w"] < h["w"] - 0.05]
        if hi:
            g = hi[0]
            rows.append([nm + " 끼움 구멍", sz_txt(g) + " 관통", fnum(g["cu"]), fnum(g["cv"]),
                         "스위치 판 2 (y%s~%s)" % (fnum(y_sk0 - 2.0), fnum(y_sk0))])
            rows.append(["  └ 테두리 오목 자리", "%s × 깊이 %s" % (sz_txt(h), fnum(body.BP_SKIN)), fnum(h["cu"]), fnum(h["cv"]),
                         "바깥 판 (y%s~%s)" % (fnum(y_sk0), fnum(body.YB))])
            if "KCD1" in nm:
                sh.chk("KCD1 끼움 구멍 폭 (스위치 판 단면)", min(g["w"], g["h"]), float(re.search(r"KCD1_([\d.]+)x", key).group(1)), "spec holes_xz " + key)
        else:
            rows.append([nm, sz_txt(h) + " 관통", fnum(h["cu"]), fnum(h["cv"]), "바깥 판 %s (y%s~%s)" % (fnum(body.BP_SKIN), fnum(y_sk0), fnum(body.YB))])
    if louv:
        lz = sorted(h["cv"] for h in louv)
        h = louv[0]
        xo |= {h["u0"], h["u1"]}
        zo |= {lz[0], lz[-1]}
        rows.append(["루버 (강압 컨버터 뒤 흡기)", "%s ×%d" % (sz_txt(h), len(louv)), "%s~%s" % (fnum(h["u0"]), fnum(h["u1"])),
                     "%s~%s, 간격 %s" % (fnum(lz[0]), fnum(lz[-1]), fnum(lz[1] - lz[0]) if len(lz) > 1 else "-"), "뒤판 출력물"])
    if vents:
        for h in vents:
            mark_hole(vc, h, 1.0)
        xo |= {vents[0]["cu"], vents[-1]["cu"]}
        zo.add(vents[0]["cv"])
        pitch = vents[1]["cu"] - vents[0]["cu"]
        rows.append(["앰프 뒤 환기 구멍", "%s ×%d" % (sz_txt(vents[0]), len(vents)), "%s~%s, 간격 %s" % (fnum(vents[0]["cu"]), fnum(vents[-1]["cu"]), fnum(pitch)),
                     fnum(vents[0]["cv"]), "가운데 유닛 뒤판 (오꾸메, 드릴)"])
        sh.chk("뒤판 환기 구멍 간격", pitch, body.VENT_PITCH, "body.VENT_PITCH")
    xo |= {leg[0], leg[3]}
    ords_h(sh, vc, sorted(xo), 1, gap=2.0)
    ords_v(sh, vc, sorted(zo), -1, gap=2.0)
    co2 = callouts_for(vc, item_map(itc), [("CU-E-SWITCH", "KCD1 로커 스위치"), ("CU-E-J501", "페달 잭 J501"), ("PR-BACKPLATE", "뒤판 출력물"),
                                           ("TS-LEG", "받침다리 (발끝은 뚜껑 주머니 안)"), ("CU-PLY-BACK", "뒤판 (오꾸메)"), ("CU-SCREENLID", "화면 뚜껑")])
    sh.callouts_h(co2, cy0 - 4.0, -1, cx0, cx1, size=T_SMALL)
    sh.text(16, cy1 + 22.0, "뒷면 구멍 (단면에서 잼)", T_NOTE + 0.4, bold=True, halo=False)
    sh.table(16, cy1 + 24.5, [("구멍", 50.0, "start"), ("크기", 36.0, "start"), ("중심 x", 40.0, "start"), ("중심 z", 34.0, "start"), ("판", 52.0, "start")],
             rows, size=T_SMALL, rh=4.0)
    sh.legend2(392, cy1 + 22.0, sh.used, cols=2, colw=96)
    sh.scale_bar(240, cy1 + 26.0, k1, 200, 50, "1:2.5")
    sh.scale_bar(240, cy1 + 40.0, 1.0, 50, 10, "1:1")
    D.notes_box(sh, 16, 372.0, 350, "잘못 꽂기 막기 (전원과 스피커가 같은 XT60)", D.mismate_lines()[:2], size=T_SMALL)
    sh.title_block()
    return sh


# ------------------------------------------------------------------ E03 / E04 sides

def sheet_side(M, Hh, code, side):
    import body
    import touchscreen_rev3 as TS
    left = side == "L"
    sh = FSheet(code, "1:1 · 확대 2:1")
    use = use_parts(M)
    allb = M.bbox([p.id for p in use])
    heading2(sh, 16, 21, ("좌측면도 — 왼쪽 끝(−x)에서 봄, 연주자는 오른쪽" if left else "우측면도 — 오른쪽 끝(+x)에서 봄, 연주자는 왼쪽"),
             "1:1 · 사용 상태 (화면 25°) · 숨은 선 없음")
    win = (-6.0, 350.0, -3.0, 196.0)
    v, items, info = ext_view(sh, Hh, use, "left" if left else "right", win, 1.0, (44.0, 40.0), r=0.1, flip=left)
    x0, y0, x1, y1 = v.rect
    ground(v, win[0], win[1], 6, flip=left)
    vis = item_map(items)
    cr = M.bb(M.by["TS-CRADLE"])
    # profile corners
    F_, T_ = body.SL_A, body.SL_B
    ys = [0.0, body.MOD_REAR, body.Y0, F_[0], body.DUCT_Y[1], T_[0], body.YB, cr[1], cr[4], TS.AX_Y]
    ords_h(sh, v, ys, 1, gap=2.0)
    sh.text(x1 + 2 if not left else x0 - 2, y1 + 3.6, "y", T_SMALL, "start" if not left else "end", cls="tm")
    fr = M.bbox([p.id for p in M.ka if p.group.endswith("프레임")])
    zs = [0.0, 3.0, body.ZB, body.DUCT_Z[1], F_[1], fr[5], TS.AX_Z, body.SPK_ZT, cr[5]]
    ords_v(sh, v, zs, -1 if left else 1, gap=2.0)
    # overall depth dims above
    sh.dim_h(v.Px(0.0), v.Px(body.YB), y0 - 12.0, "전체 깊이 %s" % fnum(allb[4] - allb[1]), ext=[(v.Px(0.0), v.Py(fr[5])), (v.Px(body.YB), v.Py(body.SPK_ZT))])
    sh.dim_h(v.Px(0.0), v.Px(body.MOD_REAR), y0 - 4.0, "건반 모듈 %s" % fnum(body.MOD_REAR), ext=[(v.Px(0.0), v.Py(fr[5]))])
    sh.dim_h(v.Px(body.Y0), v.Px(body.YB), y0 - 4.0, "뒷바 %s" % fnum(body.YB - body.Y0), ext=[(v.Px(body.YB), v.Py(body.SPK_ZT))])
    sh.chk("전체 깊이", allb[4] - allb[1], man_union([p.id for p in use])[4] - man_union([p.id for p in use])[1], "manifest bbox (모든 부품)")
    sh.chk("뒷바 앞면 y", body.Y0, man_bb("SPKL-PLY-SIDEOUT")[1], "manifest SPKL-PLY-SIDEOUT")
    # angles: baffle 40 and screen 25
    v.seg(T_, (T_[0] - 44, T_[1]), "ex")
    v.angle(T_, (-math.cos(math.radians(body.ANGLE)), -math.sin(math.radians(body.ANGLE))), (-1.0, 0.0), 30.0,
            "앞판 %s°" % fnum(body.ANGLE), text_r=34.0)
    AXp = (TS.AX_Y, TS.AX_Z)
    du = TS.world_dir(0, 1, 0, TS.TILT_USE)[1:]
    v.seg(AXp, (AXp[0], AXp[1] + 80), "ex")
    v.centre_mark(AXp[0], AXp[1], 3.0)
    v.angle(AXp, (du[0], du[1]), (0.0, 1.0), 60.0, "화면 %s°" % fnum(TS.TILT_USE), tpos="top-left")
    # callouts in a lane beside the view
    sp = "L" if left else "R"
    end = "EL" if left else "ER"
    spec = [("SPK%s-PLY-SIDEOUT" % sp, "스피커 %s 바깥 옆판 (오꾸메 11.5)" % sp), ("%s-FRAME" % end, "볼 %s (끝 부속 프레임)" % sp),
            ("DUCT-CAP-%s" % sp, "케이블 통로 옆 마개 %s (출력)" % sp), ("BRK2-%s" % sp, "방진 브래킷 %s (출력)" % sp),
            ("TS-CRADLE", "화면 받침 (출력)"), ("TS-E-SCREEN", "화면 Waveshare 7\""), ("TS-LEG", "받침다리"),
            (r"FOOT-\d+$", "고무발 28×5"), ("%s-EVA" % end, "EVA 3T 바닥"), ("SPK%s-BAFFLE" % sp, "앞판 %s° (출력)" % fnum(body.ANGLE)),
            ("SPK%s-GRILLE" % sp, "육각 그릴"), (r"%s-KEY-" % end, "건반 (끝 부속)"), (r"BRK2-%s-BOLT\d" % sp, "M3×20 볼트 (브래킷)"),
            (r"BRK2-%s-GROM\d" % sp, "실리콘 그로밋")]
    co = callouts_for(v, vis, spec)
    lane = x1 + 22 if not left else x1 + 22
    sh.callouts_v(co, lane, 1, y0 - 4, y1 + 6, size=T_NOTE)
    # detail E: duct mouth / gap / bracket at 2:1
    wd = (196.0, 252.0, -2.0, 34.0)
    de0 = (44.0, y1 + 44.0)
    heading2(sh, 16, de0[1] - 22, "확대 E — 건반 뒤 틈 · 케이블 통로 입구 · 방진 브래킷", "2:1", size=T_HEAD - 0.6)
    ve, ite, _ = ext_view(sh, Hh, use, "left" if left else "right", wd, 2.0, de0, r=0.04, flip=left)
    ex0, ey0, ex1, ey1 = ve.rect
    ve.frame()
    ground(ve, wd[0], wd[1], 3, flip=left)
    bb = M.bb(M.by["BRK2-%s" % sp])
    cap = M.bb(M.by["DUCT-CAP-%s" % sp])
    ords_h(sh, ve, [body.MOD_REAR, body.Y0, body.DUCT_Y[1], bb[1], bb[4], cap[1], cap[4]], 1, gap=2.0)
    ords_v(sh, ve, [0.0, body.ZB, body.DUCT_Z[1], bb[2], bb[5], cap[2], cap[5], 3.0], -1 if left else 1, gap=2.0)
    co2 = callouts_for(ve, item_map(ite), [("DUCT-CAP-%s" % sp, "통로 옆 마개"), ("BRK2-%s" % sp, "방진 브래킷"), ("%s-FRAME" % end, "볼 (끝 부속)"),
                                           ("SPK%s-PLY-SIDEOUT" % sp, "스피커 바깥 옆판"), ("POD-SOCKET-%s" % sp, "핀 소켓 블록")])
    sh.callouts_v(co2, ex1 + 22, 1, ey0, ey1 + 4, size=T_SMALL)
    sh.textblock(16, ey1 + 22.0, ["건반 모듈 뒷벽 y%s와 뒷바 앞면 y%s 사이 %s mm는 공기 틈입니다 (딱딱하게 닿지 않음, D15)." % (fnum(body.MOD_REAR), fnum(body.Y0), fnum(body.Y0 - body.MOD_REAR)),
                                  "케이블 통로 y%s~%s × z%s~%s는 책상이 바닥이고, 옆 끝은 마개로 막습니다." % (fnum(body.DUCT_Y[0]), fnum(body.DUCT_Y[1]), fnum(body.DUCT_Z[0]), fnum(body.DUCT_Z[1]))],
                 T_SMALL, cls="tm")
    groups = vis_groups(items, 2.0)
    visible_table(sh, 196.0, y1 + 30.0, groups, M, ("y", "z"), "%s에서 보이는 것 (보이는 넓이 순)" % ("왼쪽" if left else "오른쪽"), maxrows=13, rh=3.6, name_w=70)
    sh.legend2(392, y1 + 30.0, sh.used, cols=1)
    sh.scale_bar(392, 345.0, 1.0, 50, 10, "1:1")
    sh.scale_bar(470, 345.0, 2.0, 20, 5, "2:1")
    sh.title_block()
    return sh


def sheet_E03(M, Hh):
    return sheet_side(M, Hh, "E03", "L")


def sheet_E04(M, Hh):
    return sheet_side(M, Hh, "E04", "R")


# ------------------------------------------------------------------ E05 top

def lid_slot_rows(M):
    import body
    rows = []
    for pid, nm in (("LID-L", "뚜껑 L 배기 홈"), ("CU-SCREENLID", "화면 뚜껑 배기 홈"), ("LID-R", "뚜껑 R 배기 홈")):
        hs = D.plate_holes(M, pid, "z", body.Z_LID - 1.5)
        slots = [h for h in hs if not h["round"] and min(h["w"], h["h"]) < 5.0]
        if slots:
            rows.append((pid, nm, slots))
    return rows


def sheet_E05(M, Hh):
    import body
    import touchscreen_rev3 as TS
    sh = FSheet("E05", "1:2.5 · 가운데 1:1.5")
    use = use_parts(M)
    allb = M.bbox([p.id for p in use])
    heading2(sh, 16, 21, "평면도 — 위에서 봄 (사용 상태, 연주자는 아래쪽)", "1:2.5 · 화면은 25°로 서 있음")
    win = (-24.0, 1246.0, -6.0, 346.0)
    k1 = 0.4
    v, items, info = ext_view(sh, Hh, use, "top", win, k1, (48.0, 50.0))
    x0, y0, x1, y1 = v.rect
    vis = item_map(items)
    chain_dims(sh, v, y0, allb)
    seams = (M.bb(M.by["LID-L"])[3], M.bb(M.by["CU-SCREENLID"])[0], M.bb(M.by["CU-SCREENLID"])[3], M.bb(M.by["LID-R"])[0])
    gl, gr = M.bbox(["SPKL-GRILLE"]), M.bbox(["SPKR-GRILLE"])
    cr = M.bb(M.by["TS-CRADLE"])
    xs = [m[1] for m in module_x(M)] + [allb[3], seams[0], seams[3], gl[0], gl[3], gr[0], gr[3], cr[0], cr[3]]
    ords_h(sh, v, xs, 1, gap=2.0)
    sh.text(x0 - 3, y1 + 3.6, "x", T_SMALL, "end", cls="tm")
    bkb = M.bbox([p.id for p in key_parts(M, False)])
    wkb = M.bbox([p.id for p in key_parts(M, True)])
    curt = M.bbox([p.id for p in M.ka if "CURTAIN" in p.id])
    ys = [0.0, bkb[1], curt[1], wkb[4], body.MOD_REAR, body.Y0, gl[1], body.TOP_Y0, body.YB, cr[1], cr[4]]
    ords_v(sh, v, ys, 1, gap=1.0)
    sh.text(x1 + 1, y0 - 3.5, "y", T_SMALL, cls="tm")
    co = callouts_for(v, vis, [("SPKL-PLY-TOP", "스피커 L 윗판 (z%s)" % fnum(body.SPK_ZT)), ("SPKR-GRILLE", "스피커 R 그릴 (앞판 %s°)" % fnum(body.ANGLE)),
                               ("LID-L", "뚜껑 L (출력, 자석)"), ("LID-R", "뚜껑 R (출력, 자석)"), ("CU-SCREENLID", "화면 뚜껑 (출력)"),
                               ("TS-E-SCREEN", "화면 (25°)"), (r"O\d-FRAME$", "모듈 윗판 z%s" % fnum(M.bb(M.by["O4-FRAME"])[5])),
                               ([p.id for p in key_parts(M, True)], "흰 건반"), ([p.id for p in key_parts(M, False)], "검은 건반")])
    sh.callouts_h(co, y1 + 24.0, 1, x0, x1, size=T_NOTE)
    sh.chk("화면 뚜껑 x 시작", seams[1], man_bb("CU-SCREENLID")[0], "manifest CU-SCREENLID")
    sh.chk("뚜껑 L 오른쪽 끝 x", seams[0], man_bb("LID-L")[3], "manifest LID-L")
    # ---- centre top 1:1.5
    k2 = 1 / 1.5
    w2 = (252.0, 970.0, 206.0, 348.0)
    yc0 = y1 + 50.0
    heading2(sh, 16, yc0 - 18, "가운데 유닛 윗면 (뚜껑 L · 화면 뚜껑 · 뚜껑 R)", "1:1.5 · 배기 홈과 나사 자리", size=T_HEAD - 0.6)
    v2, it2, _ = ext_view(sh, Hh, use, "top", w2, k2, (40.0, yc0), r=0.12)
    a0, b0, a1, b1 = v2.rect
    v2.frame()
    rows = []
    xo, yo = set(seams), set([body.Y0, body.YB])
    for pid, nm, slots in lid_slot_rows(M):
        for t in D.pattern_text(slots):
            rows.append(nm + ": " + t)
        xo |= {min(h["u0"] for h in slots), max(h["u1"] for h in slots)}
        yo |= {min(h["v0"] for h in slots), max(h["v1"] for h in slots)}
    scr = [h for h in D.plate_holes(M, "CU-SCREENLID", "z", body.Z_LID - 1.5) if h["round"]]
    for h in scr:
        mark_hole(v2, h, 1.0)
    if scr:
        rows.append("화면 뚜껑 나사 자리 (M3×10 → 레일 인서트): " + "; ".join(D.pattern_text(scr)))
        xo |= {h["cu"] for h in scr}
        yo |= {h["cv"] for h in scr}
    rib = [h for h in D.plate_holes(M, "CU-SCREENLID", "z", body.Z_LID - 1.5) if not h["round"] and min(h["w"], h["h"]) >= 5.0]
    for h in rib:
        rows.append("화면 뚜껑 리본·전원선 구멍 %s × %s, 중심 (%s, %s)" % (fnum(h["w"]), fnum(h["h"]), fnum(h["cu"]), fnum(h["cv"])))
    ords_h(sh, v2, sorted(xo), 1, gap=2.0)
    ords_v(sh, v2, sorted(yo), 1, gap=1.0)
    D.notes_box(sh, 16, b1 + 22.0, 335, "윗면 구멍 (판 단면 z%s에서 잼, 중심 (x, y))" % fnum(body.Z_LID - 1.5), rows, size=T_SMALL - 0.2)
    sh.legend2(300, 14.0, sh.used, cols=4, colw=71, size=T_SMALL - 0.4)
    sh.scale_bar(358, b1 + 22.0, k1, 100, 50, "1:2.5")
    sh.scale_bar(440, b1 + 22.0, k2, 60, 20, "1:1.5")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ E06 bottom

def sheet_E06(M, Hh):
    import body
    sh = FSheet("E06", "1:2.5 · 가운데 1:1.5")
    use = use_parts(M)
    allb = M.bbox([p.id for p in use])
    heading2(sh, 16, 21, "저면도 — 아래에서 봄 (연주자 쪽이 위)", "1:2.5 · 고무발 14개 + 모듈 EVA 3T")
    win = (-24.0, 1246.0, -6.0, 346.0)
    k1 = 0.4
    v, items, info = ext_view(sh, Hh, use, "bottom", win, k1, (48.0, 50.0), vflip=True)
    x0, y0, x1, y1 = v.rect
    vis = item_map(items)
    chain_dims(sh, v, y0, allb)
    fs, fc = feet(M)
    xs = sorted(set([f[0] for f in fc] + [m[1] for m in module_x(M)] + [allb[3]]))
    ords_h(sh, v, xs, 1, gap=2.0)
    sh.text(x0 - 3, y1 + 3.6, "x", T_SMALL, "end", cls="tm")
    ys = sorted(set([0.0, body.MOD_REAR, body.Y0, body.DUCT_Y[1], body.YB] + [f[1] for f in fc]))
    ords_v(sh, v, ys, 1, gap=1.0)
    sh.text(x1 + 1, y0 - 3.5, "y", T_SMALL, cls="tm")
    for f in fc:
        v.centre_mark(f[0], f[1], 2.0)
    sh.chk("고무발 가운데 x (가운데 유닛 가운데)", [f for f in fc if abs(f[0] - 611) < 1][0][0], body.L2["feet"]["positions_xy"]["centre"][1][0], "spec feet.positions_xy")
    co = callouts_for(v, vis, [(r"FOOT-\d+$", "고무발 28×5 ×%d (8호 13 나사; 배터리 홈 밑 %d개는 MS 폴리머)" % (len(fs), len(body.GLUED_FEET))), ("CU-PLY-BOTTOM", "가운데 유닛 아랫판 (흡기 Ø8)"),
                               ("SPKL-PLY-BOTTOM", "스피커 L 아랫판"), ("SPKR-PLY-BOTTOM", "스피커 R 아랫판"), (r"O\d-EVA$", "모듈 EVA 3T"),
                               (r"SPK[LR]-DUCTFORMER$", "케이블 통로 (밑이 열림, 책상이 바닥)"), (r"BRK2-[LR]$", "방진 브래킷"),
                               ("EL-EVA", "끝 부속 EVA"), (r"O\d-C-USB$", "모듈 USB-C 선 (통로 안)")])
    sh.callouts_h(co, y1 + 24.0, 1, x0, x1, size=T_NOTE)
    # ---- centre bottom 1:1.5
    k2 = 1 / 1.5
    w2 = (252.0, 970.0, 206.0, 348.0)
    yc0 = y1 + 50.0
    heading2(sh, 16, yc0 - 18, "가운데 유닛 아랫면", "1:1.5 · 흡기 구멍 Ø8과 고무발", size=T_HEAD - 0.6)
    v2, it2, _ = ext_view(sh, Hh, use, "bottom", w2, k2, (40.0, yc0), r=0.12, vflip=True)
    a0, b0, a1, b1 = v2.rect
    v2.frame()
    bb = M.bb(M.by["CU-PLY-BOTTOM"])
    hs = D.plate_holes(M, "CU-PLY-BOTTOM", "z", (bb[2] + bb[5]) / 2)
    for h in hs:
        v2.centre_mark(h["cu"], h["cv"], 0.5 * k2 * h["w"] + 0.8)
    xo = set([bb[0], bb[3]] + [f[0] for f in fc if bb[0] < f[0] < bb[3]])
    yo = set([bb[1], bb[4]] + [f[1] for f in fc])
    grp = collections.OrderedDict()
    for h in hs:
        grp.setdefault("buck" if h["cu"] < 541 else "pi", []).append(h)
    rows = []
    for key, g in grp.items():
        xo |= {min(h["cu"] for h in g), max(h["cu"] for h in g)}
        yo |= {min(h["cv"] for h in g), max(h["cv"] for h in g)}
        for t in D.pattern_text(g):
            rows.append(("강압 컨버터 밑 " if key == "buck" else "Pi 5 밑 ") + t)
    sh.chk("아랫판 흡기 구멍 수", len(hs), len(body.BOT_HOLES_BUCK) + len(body.BOT_HOLES_PI), "body.BOT_HOLES_BUCK + BOT_HOLES_PI")
    rows.append("고무발 28×5 중심 (x, y): " + " · ".join("(%s, %s)" % (fnum(f[0]), fnum(f[1])) for f in fc))
    rows.append("발 나사 8호 13 mm (머리 자리 Ø%s × 깊이 %s, 끝이 판 윗면 1.5 아래) - 배터리 홈 밑 %s는 나사 없이 MS 폴리머"
                % (fnum(body.FOOT_SEAT[0]), fnum(body.FOOT_SEAT[1]), " · ".join("(%s, %s)" % (fnum(x), fnum(y)) for (x, y) in body.GLUED_FEET)))
    ords_h(sh, v2, sorted(xo), 1, gap=2.0)
    ords_v(sh, v2, sorted(yo), 1, gap=1.0)
    D.notes_box(sh, 16, b1 + 22.0, 330, "아랫면 구멍과 발 (판 단면에서 잼, 중심 (x, y))", rows, size=T_SMALL - 0.2)
    sh.legend2(300, 14.0, sh.used, cols=4, colw=71, size=T_SMALL - 0.4)
    sh.scale_bar(358, b1 + 22.0, k1, 100, 50, "1:2.5")
    sh.scale_bar(440, b1 + 22.0, k2, 60, 20, "1:1.5")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ E07 folded

def folded_parts(M):
    moving = set(D.TS_MOVING)
    return [p for p in use_parts(M) if p.id not in moving] + [p for p in M.alt if p.id != "TS-SCREENCOVER"]


def sheet_E07(M, Hh):
    import body
    import touchscreen_rev3 as TS
    sh = FSheet("E07", "1:2.5 · 단면 1:1")
    use = folded_parts(M)
    allb = M.bbox([p.id for p in use])
    heading2(sh, 16, 21, "화면 접은 상태 (운반) — 정면 · 평면 · 가운데 단면", "1:2.5 · 받침다리는 받침 뒤 클립에, 화면 덮개(선택)는 그리지 않음")
    win = (-24.0, 1246.0, -3.0, 150.0)
    k1 = 0.4
    v, items, _ = ext_view(sh, Hh, use, "front", win, k1, (48.0, 40.0))
    x0, y0, x1, y1 = v.rect
    ground(v, win[0], win[1], 10)
    fb = M.bb(M.by["TS-CRADLE-FOLD"])
    fs = M.bb(M.by["TS-E-SCREEN-FOLD"])
    ords_v(sh, v, [0.0, body.Z_LID, fb[5], body.SPK_ZT], -1, gap=2.0)
    sh.text(x0 - 2, y0 - 3.5, "z", T_SMALL, "end", cls="tm")
    ords_h(sh, v, [allb[0], fb[0], fb[3], allb[3]], 1, gap=2.0)
    sh.chk("접은 받침 위 끝 z", fb[5], man_bb("TS-CRADLE-FOLD")[5], "manifest TS-CRADLE-FOLD")
    # plan
    w2 = (-24.0, 1246.0, 150.0, 346.0)
    yp = y1 + 24.0
    sh.text(48, yp - 4, "평면 (위에서 봄, 건반 뒤쪽 y150부터)", T_HEAD - 0.8, bold=True)
    v2, it2, _ = ext_view(sh, Hh, use, "top", w2, k1, (48.0, yp))
    a0, b0, a1, b1 = v2.rect
    ords_v(sh, v2, [fb[1], fb[4], body.YB], 1, gap=1.0)
    ords_h(sh, v2, [fb[0], fb[3], TS.XC], 1, gap=2.0)
    # section at x611
    X = TS.XC
    w3 = (196.0, 348.0, -3.0, 100.0)
    ys0 = b1 + 30.0
    heading2(sh, 16, ys0 - 16, "단면 x%s (화면 가운데, 오른쪽 끝에서 봄)" % fnum(X), "1:1", size=T_HEAD - 0.6)
    v3 = FView(sh, 1.0, w3, (40.0, ys0))
    its, _ = Hh.render(use, "right", w3, r=0.08, clips=(("x", "<", X),))
    draw_items(v3, its, prefix="P-")
    cut = section_items(M, use, "x", X - 0.001, v3.clip())
    draw_cut(v3, cut)
    v3.frame()
    c0, d0, c1, d1 = v3.rect
    ground(v3, w3[0], w3[1], 6)
    ords_h(sh, v3, [body.Y0, fb[1], TS.AX_Y, fb[4], body.YB], 1, gap=2.0)
    ords_v(sh, v3, [body.Z_LID, fs[5], fb[5], TS.AX_Z], -1, gap=2.0)
    v3.centre_mark(TS.AX_Y, TS.AX_Z, 3.0)
    co = callouts_for(v3, item_map(cut), [("TS-CRADLE-FOLD", "화면 받침 (접음)"), ("TS-E-SCREEN-FOLD", "화면 (유리가 위)"), ("TS-LEG-FOLD", "받침다리 (클립)"),
                                         ("CU-SCREENLID", "화면 뚜껑"), ("CU-PLY-BACK", "뒤판"), ("CU-PLY-BOTTOM", "아랫판")])
    sh.callouts_v(co, c1 + 14, 1, d0, d1 + 4, size=T_NOTE)
    D.notes_box(sh, 300, ys0 - 4, 200, "접은 상태 숫자 (입체에서 잼)", [
        "받침 몸 y%s~%s, 위 끝 z%s — 스피커 윗면 z%s보다 %s 낮음" % (fnum(fb[1]), fnum(fb[4]), fnum(fb[5]), fnum(body.SPK_ZT), fnum(body.SPK_ZT - fb[5])),
        "화면 유리 위 z%s · 경첩 축 y%s z%s" % (fnum(fs[5]), fnum(TS.AX_Y), fnum(TS.AX_Z)),
        "전체 높이는 스피커 윗면 z%s (화면이 그 아래)" % fnum(allb[5]),
        "화면 덮개(선택, stl/print_extra)를 얹으면 위 끝 z%s" % fnum(M.bb(M.by["TS-SCREENCOVER"])[5]),
    ], size=T_SMALL)
    sh.legend2(300, ys0 + 34, sh.used, cols=2, colw=100)
    sh.scale_bar(440, 19.0, k1, 100, 50, "1:2.5")
    sh.scale_bar(520, 19.0, 1.0, 40, 10, "1:1")
    sh.title_block()
    return sh


# ------------------------------------------------------------------ inside sheets

LIDS_OFF = re.compile(r"^(LID-[LR]$|CU-SCREENLID$|CU-M3X10-\d|CU-MAG-LID-|TS-|SPK[LR]-PLY-TOP$|SPK[LR]-BAFFLE$|SPK[LR]-GRILLE$|SPK[LR]-GASKET$|SPK[LR]-INS-)")


def inside_parts(M):
    return [p for p in M.rear if not LIDS_OFF.match(p.id)]


def number_groups(items, M, min_area=3.0, skip_ctx=True):
    """visible items -> numbered groups (by gname), numbered along x then y."""
    g = collections.OrderedDict()
    for p, cs in items:
        if skip_ctx and D.is_ka(p):
            continue
        g.setdefault(gname(p), []).append((p, cs))
    out = []
    for nm, lst in g.items():
        u = merge_cs([c for _, c in lst])
        if u.area() < min_area:
            continue
        b = M.bbox([p.id for p, _ in lst])
        out.append(dict(name=nm, vis=lst, union=u, bb=b))
    out.sort(key=lambda d: ((d["bb"][0] + d["bb"][3]) / 2, d["bb"][1]))
    return out


def balloon_lanes(sh, view, groups, nmap, top_lane, bot_lane, lo, hi, check=True):
    """balloons on a view: each group anchored on its own visible region in this view (refused if the point is off the part)."""
    x0, y0, x1, y1 = view.rect
    ym = (y0 + y1) / 2
    top, bot, bad = [], [], []
    for d in groups:
        u = d["union"] ^ view.clip()
        if u.is_empty() or u.area() < 1.0:
            continue
        pt = D.best_inner(u)
        if pt is None:
            continue
        if check and not D.point_in(u, pt[0], pt[1], r=min(0.3, max(pt[2] * 0.5, 0.05))):
            bad.append(d["name"])
        a = view.P(pt[0], pt[1])
        n = nmap[d["name"]]
        (top if a[1] < ym else bot).append((a[0], a[1], n))
    sh.balloons_h(top, top_lane, lo, hi)
    sh.balloons_h(bot, bot_lane, lo, hi)
    if bad:
        raise D.DrawingCheckError("%s: balloon not on its part: %s" % (sh.code, ", ".join(bad)))


def parts_rows(M, names, pool, nmap):
    rows = []
    for nm in names:
        ps = [p for p in pool if gname(p) == nm]
        b = M.bbox([p.id for p in ps])
        rows.append([str(nmap[nm]), nm, codes_txt(ps), str(len(ps)), "%s~%s" % (fnum(b[0], 1), fnum(b[3], 1)),
                     "%s~%s" % (fnum(b[1], 1), fnum(b[4], 1)), "%s~%s" % (fnum(b[2], 1), fnum(b[5], 1))])
    return rows


def fit(s, w, size):
    if text_w(s, size) <= w:
        return s
    while s and text_w(s + "…", size) > w:
        s = s[:-1]
    return s + "…"


PT_COLS = [("번호", 8.0, "middle"), ("이름 (모델 부품 이름)", 84.0, "start"), ("코드", 32.0, "start"), ("수량", 10.0, "middle"),
           ("x", 30.0, "start"), ("y", 27.0, "start"), ("z", 25.0, "start")]


def parts_table2(sh, x, y, rows, size=T_SMALL - 0.3, rh=3.5, cols=PT_COLS):
    rows = [[fit(c, w - 1.5, size) for c, (_, w, _) in zip(r, cols)] for r in rows]
    return sh.table(x, y, cols, rows, size=size, rh=rh)


def sheet_I01(M, Hh):
    import body
    sh = FSheet("I01", "1:1.5 · 스피커 L 1:1")
    pool = inside_parts(M)
    heading2(sh, 16, 21, "내부 평면도 — 뚜껑 L·R, 화면 뚜껑, 화면, 스피커 윗판·앞판·그릴·가스켓을 뗀 모습", "1:1.5 · 위에서 봄 · 연주자는 아래쪽 · 번호는 오른쪽 표")
    k = 1 / 1.5
    rows_v = []
    allitems = []
    wins = [((-22.0, 612.0, 196.0, 348.0), (52.0, 56.0)), ((610.0, 1244.0, 196.0, 348.0), (52.0, 202.0))]
    ka_ctx = [p for p in M.ka if M.bb(p)[4] > 190]
    for win, at in wins:
        v = FView(sh, k, win, at)
        items, _ = Hh.render(pool + ka_ctx, "top", win, r=0.15)
        draw_items(v, items, ctx_ka=True)
        v.frame()
        rows_v.append((v, items))
        allitems += items
    groups = number_groups(allitems, M)
    nmap = {d["name"]: i + 1 for i, d in enumerate(groups)}
    for v, items in rows_v:
        gs = number_groups(items, M)
        x0, y0, x1, y1 = v.rect
        balloon_lanes(sh, v, gs, nmap, y0 - 7.0, y1 + 7.0, x0, x1)
        ys = [body.MOD_REAR, body.Y0, body.DUCT_Y[1], body.YBI, body.YB]
        ords_v(sh, v, ys, -1, gap=1.0)
        xs = [x for x in (body.SPK_X["L"][1], body.CU_X[0], body.CU_X[1], body.SPK_X["R"][0], body.DRV_X["L"], body.DRV_X["R"],
                          body.LID_SEAMS[0], body.LID_SEAMS[1]) if v.u0 < x < v.u1]
        for xx in xs:
            v.seg((xx, v.v0), (xx, v.v0 + 3.0), "thin")
        sh.text(x1 + 3.0, y1 - 1.0, "x %s ~ %s" % (fnum(v.u0), fnum(v.u1)), T_SMALL, cls="tm")
    # ---- speaker L inside at 1:1 (R is its mirror about x611)
    wp = (-22.0, 262.0, 196.0, 348.0)
    pv = FView(sh, 1.0, wp, (52.0, 360.0))
    itp, _ = Hh.render(pool + ka_ctx, "top", wp, r=0.08)
    draw_items(pv, itp, ctx_ka=True)
    pv.frame()
    p0, q0, p1, q1 = pv.rect
    sh.text(16, q0 - 18.0, "스피커 L 안 (1:1) — R은 x%s 기준 거울" % fnum(body.MIRROR_X), T_HEAD - 0.6, bold=True)
    balloon_lanes(sh, pv, number_groups(itp, M), nmap, q0 - 7.0, q1 + 7.0, p0, p1)
    pods = [p for p in pool if p.group == body.G_SPK["L"]] + [M.by["SPK-L"]]
    xs_p = [body.SPK_X["L"][0], body.SPK_IX["L"][0], body.DRV_X["L"], body.SPK_IX["L"][1], body.SPK_X["L"][1]]
    for pid in ("POD-SOCKET-L", "CABLE-CLIP-L1", "CABLE-CLIP-L2", "CABLE-CLIP-L3"):
        b = M.bb(M.by[pid])
        xs_p.append((b[0] + b[3]) / 2)
    ords_h(sh, pv, xs_p, 1, gap=16.0)
    ords_v(sh, pv, [body.MOD_REAR, body.Y0, body.DUCT_Y[1], body.RISER[1], body.DRV_YZ[0], body.YBI, body.YB], -1, gap=1.0)
    pv.centre_mark(body.DRV_X["L"], body.DRV_YZ[0], 4.0)
    sh.chk("스피커 유닛 가운데 x (L)", body.DRV_X["L"], (man_bb("SPK-L")[0] + man_bb("SPK-L")[3]) / 2, "manifest SPK-L")
    # tables
    names = [d["name"] for d in groups]
    rows = parts_rows(M, names, pool, nmap)
    tx = 506.0
    half = 74
    sh.text(tx, 36.0, "보이는 부품 (번호 = 그림, 수량 = 뒷바 전체, 좌표 = 모든 개체의 바깥 상자)", T_NOTE - 0.3, bold=True, halo=False)
    sh.text(tx, 40.0, CODE_HEAD, T_SMALL - 0.4, cls="tm", halo=False)
    yb = parts_table2(sh, tx, 43.0, rows[:half], size=T_SMALL - 0.4, rh=3.3, cols=[(a, w * 0.98, al) for a, w, al in PT_COLS])
    if len(rows) > half:
        yb = parts_table2(sh, tx, yb + 4.0, rows[half:], size=T_SMALL - 0.4, rh=3.3, cols=[(a, w * 0.98, al) for a, w, al in PT_COLS])
    sh.legend2(tx, yb + 10.0, sh.used | {"ctx"}, cols=2, colw=110)
    sh.scale_bar(tx, yb + 44.0, k, 100, 20, "1:1.5")
    sh.scale_bar(tx + 110, yb + 44.0, 1.0, 50, 10, "1:1")
    D.notes_box(sh, 360, 360, 135, "읽는 법", [
        "뚜껑을 들면 보이는 그대로입니다. 건반 모듈(연한 회색)은 뒷부분만 그렸습니다.",
        "스피커 유닛은 %s° 누운 앞판에 달려 있어 위에서는 뒤쪽(자석)이 보입니다." % fnum(body.ANGLE),
        "가운데 유닛 칸별 좌표·기둥·구멍은 I02, 높이는 I03·D03에 있습니다.",
        "수량이 1보다 큰데 그림에 하나만 보이면 나머지는 다른 부품 밑에 숨어 있습니다.",
    ], size=T_SMALL)
    sh.title_block()
    sh.chk("I01 표 줄 수 = 번호 수", len(rows), len(groups), "number_groups")
    return sh


# ------------------------------------------------------------------ I02 centre detail

CENTRE_SKIP = re.compile(r"^(SPK|DUCT-CAP|POD-SOCKET|BRK2|CABLE-CLIP-[LR]|FOOT-0[1-4]$|FOOT-1[1-4]$|JOIN-)")


def centre_parts(M):
    import body
    out = []
    for p in inside_parts(M):
        b = M.bb(p)
        if CENTRE_SKIP.match(p.id):
            continue
        if b[3] < body.CU_X[0] - 1 or b[0] > body.CU_X[1] + 1:
            continue
        out.append(p)
    return out


def post_rows(M):
    posts = sorted([p for p in M.rear if p.id.startswith("CU-POST-")], key=lambda p: (M.bb(p)[0], M.bb(p)[1]))
    rows = []
    for i, p in enumerate(posts):
        b = M.bb(p)
        cx, cy = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2
        hs = D.hole_list(sec(p.solid, "z", b[5] - 0.6))
        h = min(hs, key=lambda h: math.hypot(h["cu"] - cx, h["cv"] - cy)) if hs else None
        pin = [q for q in polys(sec(p.solid, "z", b[5] - 0.2)) if signed_area(q) > 0]
        rows.append(dict(n="P%d" % (i + 1), p=p, cx=cx, cy=cy, top=b[5], h=b[5] - b[2], w=b[3] - b[0],
                         hole=sz_txt(h) if h else ("핀 Ø%s" % fnum(float(np.ptp(pin[0][:, 0])), 2) if pin else "-")))
    return rows


def sheet_I02(M, Hh):
    import body
    sh = FSheet("I02", "1:1")
    pool = centre_parts(M)
    heading2(sh, 16, 21, "가운데 유닛 내부 상세 — 뚜껑·화면을 뗀 평면과 y290 단면", "1:1 · 모든 좌표는 입체에서 · 번호·P번호는 아래 표")
    win = (256.0, 966.0, 206.0, 348.0)
    v = FView(sh, 1.0, win, (52.0, 60.0))
    items, _ = Hh.render(pool, "top", win, r=0.1)
    draw_items(v, items)
    v.frame()
    x0, y0, x1, y1 = v.rect
    groups = number_groups(items, M, min_area=1.0)
    nmap = {d["name"]: i + 1 for i, d in enumerate(groups)}
    balloon_lanes(sh, v, groups, nmap, y0 - 8.0, y1 + 30.0, x0, x1)
    # posts: P labels + ordinates
    pr = post_rows(M)
    for r in pr:
        v.centre_mark(r["cx"], r["cy"], 0.5 * r["w"] + 1.5)
        px, py = v.P(r["cx"], r["cy"])
        sh.text(px + 0.5 * r["w"] + 1.2, py - 0.8 * 0 - 1.6, r["n"], T_SMALL - 0.2, bold=True)
    ords_h(sh, v, [r["cx"] for r in pr] + [body.CU_IX[0], body.CU_IX[1], body.LID_SEAMS[0], body.LID_SEAMS[1]], 1, gap=2.0)
    ords_v(sh, v, sorted(set([round(r["cy"], 2) for r in pr] + [body.Y0, body.DUCT_Y[1], body.YBI, body.YB])), 1, gap=1.0)
    # bay zones (spec centre.bays_x)
    zb0, zb1 = y0 - 22.0, y0 - 16.0
    for key, (xa, xb) in body.CE["bays_x"].items():
        tag, nm = key.split("_", 1)
        pa, pb2 = v.Px(xa), v.Px(xb)
        sh.rect(pa, zb0, pb2, zb1, "zone", "over")
        sh.text((pa + pb2) / 2, zb1 - 1.4, "%s %s · x%s~%s" % (tag, D.BAY_KO.get(nm, nm), fnum(xa), fnum(xb)), T_SMALL, "middle", halo=False)
    sh.text(x0 - 2, zb1 - 1.4, "칸 (사양 bays_x)", T_SMALL, "end", cls="tm")
    # ---- section y290 looking +y
    yc = 290.0
    w2 = (256.0, 966.0, -3.0, 80.0)
    ys0 = y1 + 62.0
    heading2(sh, 16, ys0 - 10, "단면 y%s — 앞에서 봄 (배터리 · 강압 · Pi 5 · 허브 · 앰프)" % fnum(yc), "1:1 · 잘린 면 빗금, 그 뒤는 보이는 그대로", size=T_HEAD - 0.6)
    v2 = FView(sh, 1.0, w2, (52.0, ys0))
    its, _ = Hh.render(pool, "front", w2, r=0.1, clips=(("y", ">", yc),))
    draw_items(v2, its)
    cut = section_items(M, pool, "y", yc + 0.001, v2.clip())
    draw_cut(v2, cut)
    v2.frame()
    a0, b0, a1, b1 = v2.rect
    ground(v2, w2[0], w2[1], 6)
    zs = [0.0, body.ZB, body.Z_BOT, body.Z_LIDU]
    for pid in ("BAT-LFP", "CU-E-BUCK", "CU-E-PI5", "PB-E-HUB", "CU-E-AMP", "PR-HUBSHELF"):
        b = M.bb(M.by[pid])
        zs += [b[2], b[5]]
    ords_v(sh, v2, zs, -1, gap=2.0)
    co = callouts_for(v2, item_map(cut), [("BAT-LFP", "LiFePO4 12.8 V 6 Ah"), ("CU-BATFRAME", "배터리 틀"), ("CU-E-BUCK", "XL4016 강압"),
                                         ("CU-E-PI5", "Pi 5"), ("PB-E-HUB", "USB 허브"), ("CU-E-AMP", "TPA3110 앰프"), ("PR-HUBSHELF", "허브 위 선반"),
                                         ("CU-PLY-BOTTOM", "아랫판 오꾸메"), ("CU-PLY-END-L", "끝벽 L (출력)"), ("CU-PLY-END-R", "끝벽 R (출력)"),
                                         (r"FOOT-\d+$", "고무발"), ("CU-E-PEDBOARD", "PED 기판")])
    sh.callouts_h(co, b1 + 12.0, 1, a0, a1, size=T_SMALL)
    # ---- tables
    ty = b1 + 24.0
    rows = []
    for d in groups:
        ps = [p for p in pool if gname(p) == d["name"]]
        b = M.bbox([p.id for p in ps])
        rows.append([str(nmap[d["name"]]), d["name"], codes_txt(ps), str(len(ps)), "%s~%s" % (fnum(b[0], 1), fnum(b[3], 1)),
                     "%s~%s" % (fnum(b[1], 1), fnum(b[4], 1)), "%s~%s" % (fnum(b[2], 1), fnum(b[5], 1))])
    half = (len(rows) + 1) // 2
    sh.text(16, ty - 3.0, "가운데 유닛 안 부품 (번호 = 위 평면, 좌표 = 입체의 바깥 상자)", T_NOTE + 0.2, bold=True, halo=False)
    parts_table2(sh, 16, ty, rows[:half], size=T_SMALL - 0.4, rh=3.3)
    parts_table2(sh, 16 + 220, ty, rows[half:], size=T_SMALL - 0.4, rh=3.3)
    px0 = 460.0
    sh.text(px0, ty - 3.0, "보드 받침 기둥 (출력, 아랫판 위)", T_NOTE + 0.2, bold=True, halo=False)
    prow = [[r["n"], fit((re.search(r"\((.*)\)", r["p"].name_ko) or re.search(r"(.*)", r["p"].name_ko)).group(1), 54, T_SMALL - 0.4), fnum(r["cx"]), fnum(r["cy"]), fnum(r["top"]), fnum(r["h"]), r["hole"]] for r in pr]
    sh.table(px0, ty, [("P", 8.0, "middle"), ("보드", 56.0, "start"), ("중심 x", 18.0, "start"), ("중심 y", 18.0, "start"), ("위 z", 14.0, "start"),
                       ("높이", 12.0, "start"), ("구멍", 26.0, "start")], prow, size=T_SMALL - 0.4, rh=3.3)
    bb = M.bb(M.by["CU-PLY-BOTTOM"])
    hs = D.plate_holes(M, "CU-PLY-BOTTOM", "z", (bb[2] + bb[5]) / 2)
    notes = ["아랫판 흡기 구멍: " + t for t in D.pattern_text(hs)]
    for pid, nm in (("PR-BACKPLATE", "뒤판 출력물"),):
        b = M.bb(M.by[pid])
        notes.append("%s x%s~%s, z%s~%s (I/O 판, E02 확대 C)" % (nm, fnum(b[0]), fnum(b[3]), fnum(b[2]), fnum(b[5])))
    notes.append("뚜껑 밑면 z%s · 아랫판 윗면 z%s → 안 높이 %s" % (fnum(body.Z_LIDU), fnum(body.Z_BOT), fnum(body.Z_LIDU - body.Z_BOT)))
    notes.append("앞 공간 y%s~%s는 앞벽 없이 케이블 통로와 이어짐 (모듈 USB-C를 위에서 잡음)" % (fnum(body.Y0), fnum(body.DUCT_Y[1])))
    D.notes_box(sh, px0, ty + 3.3 * (len(prow) + 1) + 10.0, 170, "구멍·높이", notes, size=T_SMALL - 0.3)
    sh.legend2(650, ty - 3.0, sh.used, cols=1)
    sh.scale_bar(650, ty + 52.0, 1.0, 50, 10, "1:1")
    sh.title_block()
    sh.chk("기둥 수", len(pr), 14, "CU-POST-* (PI 4 · BUCK 4 · PED 4 · J702 2)")
    return sh


# ------------------------------------------------------------------ I03 long sections

def sec_view(sh, Hh, M, parts, view, win, k, at, axis, c, keep, depth=None, r=0.2, ctx_ka=False, flip=False):
    """section: solids cut at axis = c, the far side drawn (hidden-surface), the cut faces hatched on top."""
    clips = ((axis, keep, c),)
    if depth is not None:
        clips = clips + ((axis, "<" if keep == ">" else ">", c + depth if keep == ">" else c - depth),)
    v = FView(sh, k, win, at, flip=flip)
    its, info = Hh.render(parts, view, win, r=r, clips=clips)
    draw_items(v, its, ctx_ka)
    cut = section_items(M, parts, axis, c + (0.001 if keep == ">" else -0.001), v.clip())
    draw_cut(v, cut, ctx_ka)
    return v, its, cut


def sheet_I03(M, Hh):
    import body
    sh = FSheet("I03", "1:2.5 · 확대 1:1")
    use = use_parts(M)
    heading2(sh, 16, 21, "전체 길이 단면 A-A (y67 센서 줄) · B-B (y260 스피커 축)", "앞에서 봄 · 잘린 면 빗금 · 그 뒤는 보이는 그대로")
    k1 = 0.4
    yA = body.SENSOR_YZ[0]
    yB = body.DRV_YZ[0]
    # A-A main (key action only behind)
    wA = (-24.0, 1246.0, -3.0, 80.0)
    vA, itA, cutA = sec_view(sh, Hh, M, use, "front", wA, k1, (48.0, 46.0), "y", yA, ">", depth=body.MOD_REAR - yA + 1.0)
    ax0, ay0, ax1, ay1 = vA.rect
    ground(vA, wA[0], wA[1], 10)
    sh.text(ax0, ay0 - 5.0, "A-A  y%s — 홀 센서 줄 (뒤로 y%s까지)" % (fnum(yA), fnum(body.MOD_REAR)), T_HEAD - 0.6, bold=True)
    ords_h(sh, vA, [m[1] for m in module_x(M)] + [1238.0], 1, gap=2.0)
    sb = M.bb(M.by["O4-SENSORBAR"])
    zsA = [0.0, 3.0, sb[2], sb[5], M.bb(M.by["O4-KEY-C"])[2], M.bb(M.by["O4-KEY-C"])[5], M.bb(M.by["O4-FRAME"])[5]]
    ords_v(sh, vA, zsA, -1, gap=2.0)
    # B-B main
    wB = (-24.0, 1246.0, -3.0, 196.0)
    yb0 = ay1 + 40.0
    vB, itB, cutB = sec_view(sh, Hh, M, use, "front", wB, k1, (48.0, yb0), "y", yB, ">")
    bx0, by0, bx1, by1 = vB.rect
    ground(vB, wB[0], wB[1], 10)
    sh.text(bx0, by0 - 5.0, "B-B  y%s — 스피커 유닛 가운데 (뒤는 끝까지)" % fnum(yB), T_HEAD - 0.6, bold=True)
    for s in "LR":
        vB.centre_mark(body.DRV_X[s], body.DRV_YZ[1], 3.0)
    ords_h(sh, vB, [body.SPK_X["L"][0], body.SPK_X["L"][1], body.CU_X[0], body.CU_X[1], body.SPK_X["R"][0], body.SPK_X["R"][1], body.DRV_X["L"], body.DRV_X["R"]], 1, gap=2.0)
    ords_v(sh, vB, [0.0, body.ZB, body.Z_BOT, body.Z_LIDU, body.Z_LID, body.DRV_YZ[1], body.SPK_ZT - body.T, body.SPK_ZT], -1, gap=2.0)
    coB = callouts_for(vB, item_map(cutB), [("SPK-L", "스피커 유닛 L (잘림)"), ("SPKR-BAFFLE", "앞판 R (잘림)"), ("BAT-LFP", "배터리"),
                                           ("CU-E-PI5", "Pi 5"), ("TS-E-SCREEN", "화면 (잘림)"), ("CU-SCREENLID", "화면 뚜껑"), ("PB-E-HUB", "허브"),
                                           ("SPKL-PLY-BOTTOM", "스피커 아랫판"), (r"FOOT-\d+$", "고무발")])
    sh.callouts_h(coB, by1 + 22.0, 1, bx0, bx1, size=T_SMALL)
    # A-A detail 1:1 (EL + O1)
    wa = (-22.0, 216.0, -3.0, 76.0)
    da = (580.0, 52.0)
    sh.text(da[0] - 22, da[1] - 12.0, "확대 A — A-A의 왼쪽 끝 (끝 부속 + O1)", T_HEAD - 0.8, bold=True)
    sh.text(da[0] - 22, da[1] - 6.5, "1:1 · 뒤로 y%s까지" % fnum(body.MOD_REAR), T_SMALL, cls="tm")
    k3 = 1.0
    wa2 = (-22.0, 216.0, -3.0, 76.0)
    va, ita, cuta = sec_view(sh, Hh, M, use, "front", wa2, 1.0, (da[0] - 0.0, da[1]), "y", yA, ">", depth=body.MOD_REAR - yA + 1.0, r=0.08)
    # 238 mm wide at 1:1 does not fit beside A-A on A1 -> scale this detail to fit (stated)
    va_x0, va_y0, va_x1, va_y1 = va.rect
    va.frame()
    co_a = callouts_for(va, item_map(cuta), [("EL-FRAME", "끝 부속 프레임 (볼)"), ("EL-SENSORBAR", "센서 바"), ("EL-E-BOARD", "센서 기판 EL"),
                                            ("O1-SENSORBAR", "센서 바 O1"), ("O1-E-SB", "센서 기판 SB"), ("O1-FRAME", "모듈 프레임 O1"),
                                            ("O1-EVA", "EVA 3T"), (r"O1-MAGNET-", "자석 Ø5×2"), (r"O1-KEY-", "건반 (잘림)")])
    sh.callouts_h(co_a, va_y1 + 10.0, 1, va_x0, va_x1, size=T_SMALL - 0.2)
    zsa = [0.0, 3.0, sb[2], sb[5], M.bb(M.by["O1-E-SB"])[2], M.bb(M.by["O1-MAGNET-C"])[2], M.bb(M.by["O1-MAGNET-C"])[5]]
    ords_v(sh, va, zsa, -1, gap=1.5)
    # B-B centre detail 1:1
    wc = (256.0, 966.0, -3.0, 100.0)
    dc0 = by1 + 52.0
    sh.text(48, dc0 - 8.0, "확대 B — B-B의 가운데 유닛 (y%s, z100까지 — 화면 단면은 B-B)" % fnum(yB), T_HEAD - 0.6, bold=True)
    vc, itc, cutc = sec_view(sh, Hh, M, use, "front", wc, 1.0, (48.0, dc0), "y", yB, ">", r=0.1)
    cx0, cy0, cx1, cy1 = vc.rect
    vc.frame()
    ground(vc, wc[0], wc[1], 6)
    zc = [0.0, body.ZB, body.Z_BOT, body.Z_LIDU, body.Z_LID]
    for pid in ("BAT-LFP", "CU-E-PI5", "PB-E-HUB", "CU-E-AMP"):
        b = M.bb(M.by[pid])
        zc += [b[2], b[5]]
    ords_v(sh, vc, zc, -1, gap=2.0)
    xc = []
    for p, cs in cutc:
        if p.id.startswith(("CU-POST", "BAT-LFP", "CU-E-PI5", "PB-E-HUB", "CU-E-AMP", "CU-PLY-END", "CU-E-BUCK", "CU-E-PED")):
            b = cs.bounds()
            xc += [b[0], b[2]]
    ords_h(sh, vc, xc, 1, gap=2.0)
    co_c = callouts_for(vc, item_map(cutc), [("BAT-LFP", "LiFePO4 배터리"), ("CU-BATFRAME", "배터리 틀"), ("CU-E-PI5", "Pi 5"), ("PB-E-HUB", "USB 허브"),
                                            ("CU-E-AMP", "앰프"), ("PR-HUBSHELF", "허브 위 선반"), ("CU-SCREENLID", "화면 뚜껑"), ("TS-CRADLE", "화면 받침"),
                                            ("TS-E-SCREEN", "화면"), ("LID-L", "뚜껑 L"), ("LID-R", "뚜껑 R"), ("CU-PLY-BOTTOM", "아랫판"),
                                            (r"CU-POST-", "보드 받침 기둥"), ("CU-E-PEDBOARD", "PED 기판"), ("CU-E-BUCK", "강압")])
    sh.callouts_v(co_c, cx1 + 14.0, 1, cy0 - 4, cy1, size=T_SMALL)
    sh.legend2(16, cy1 + 30.0, sh.used, cols=4, colw=100)
    sh.scale_bar(440, cy1 + 30.0, k1, 200, 50, "1:2.5")
    sh.scale_bar(440, cy1 + 44.0, 1.0, 50, 10, "1:1")
    seen = collections.OrderedDict()
    for p, cs in cutc:
        b = cs.bounds()
        seen.setdefault(gname(p), []).append((p, b))
    rows = []
    for nm, lst in seen.items():
        xs_ = [b[0] for _, b in lst] + [b[2] for _, b in lst]
        zs_ = [b[1] for _, b in lst] + [b[3] for _, b in lst]
        rows.append([fit(nm, 88, T_SMALL - 0.4), str(len(lst)), "%s~%s" % (fnum(min(xs_), 1), fnum(max(xs_), 1)), "%s~%s" % (fnum(min(zs_), 1), fnum(max(zs_), 1))])
    cols = [("확대 B 단면에 잘린 것 (잘린 면의 범위)", 90.0, "start"), ("수", 8.0, "middle"), ("x", 30.0, "start"), ("z", 24.0, "start")]
    third = (len(rows) + 2) // 3
    for i in range(3):
        if rows[i * third:(i + 1) * third]:
            sh.table(16 + i * 158, cy1 + 62.0, cols, rows[i * third:(i + 1) * third], size=T_SMALL - 0.4, rh=3.3)
    sh.title_block()
    return sh


# ------------------------------------------------------------------ I04 side section through D4

def sheet_I04(M, Hh):
    import body
    import touchscreen_rev3 as TS
    sh = FSheet("I04", "1:1")
    use = use_parts(M)
    mg = M.bb(M.by["O4-MAGNET-D"])
    X = round((mg[0] + mg[3]) / 2, 2)
    depth = 12.0
    heading2(sh, 16, 21, "측면 단면 x%s — O4 D 건반 가운데 (자석·밸런스 핀 줄)" % fnum(X),
             "1:1 · 오른쪽 끝(+x)에서 봄, 연주자는 왼쪽 · 잘린 면 빗금, 그 뒤 %s mm까지 보이는 그대로" % fnum(depth))
    win = (-5.0, 350.0, -3.0, 196.0)
    v, its, cut = sec_view(sh, Hh, M, use, "right", win, 1.0, (40.0, 42.0), "x", X, "<", depth=depth, r=0.06)
    x0, y0, x1, y1 = v.rect
    ground(v, win[0], win[1], 6)
    sh.chk("단면 x (자석 D4 가운데)", X, (man_bb("O4-MAGNET-D")[0] + man_bb("O4-MAGNET-D")[3]) / 2, "manifest O4-MAGNET-D")
    vis = item_map(cut)
    key = M.bb(M.by["O4-KEY-D"])
    lev = M.bb(M.by["O4-LEVER-D"])
    rod = M.bb(M.by["O4-B-keyrodSUS304D4"])
    lrod = M.bb(M.by["O4-B-leverrodD4SUS304x151629"])
    sb = M.bb(M.by["O4-SENSORBAR"])
    ys = [0.0, mg[1] / 2 + mg[4] / 2, (rod[1] + rod[4]) / 2, (lrod[1] + lrod[4]) / 2, key[4], body.MOD_REAR, body.Y0, body.DUCT_Y[1],
          body.YBI, body.YB, TS.AX_Y]
    ords_h(sh, v, ys, 1, gap=2.0)
    zs = [0.0, 3.0, sb[2], key[5], (rod[2] + rod[5]) / 2, (lrod[2] + lrod[5]) / 2, M.bb(M.by["O4-FRAME"])[5], body.Z_BOT, body.Z_LIDU, TS.AX_Z,
          M.bb(M.by["TS-CRADLE"])[5]]
    ords_v(sh, v, zs, -1, gap=2.0)
    v.centre_mark(TS.AX_Y, TS.AX_Z, 3.0)
    co = callouts_for(v, vis, [
        ("O4-KEY-D", "흰 건반 D4 (PETG)"), ("O4-MAGNET-D", "자석 Ø5×2 (홀 센서 위)"), ("O4-SENSORBAR", "센서 바"), ("O4-E-SB", "센서 기판 SB"),
        ("O4-B-keyrodSUS304D4", "건반 봉 Ø4 (밸런스 축)"), ("O4-LEVER-D", "레버 캐리어"), ("O4-STEEL-D", "강철 블록 9×19×40"),
        ("O4-SPRING-D", "비틀림 스프링"), ("O4-B-leverrodD4SUS304x151629", "레버 봉 Ø4"), ("O4-FRAME", "모듈 프레임 (윗판 z72.85)"),
        (r"O4-PADBAR-", "패드 바"), ("O4-B-upstoppad-D", "업스톱 패드"), ("O4-CURTAIN", "가림판 띠"), ("O4-EVA", "EVA 3T"),
        ("O4-E-MB", "제어 기판 MB"), ("O4-C-USB", "USB-C 선"), ("O4-CAPSTAN-D", "캡스턴 M3×6"), (r"O4-B-balancepinD2-D", "밸런스 핀 Ø2"),
        ("CU-SCREENLID", "화면 뚜껑"), ("TS-CRADLE", "화면 받침"), ("TS-E-SCREEN", "화면"), ("CU-E-PI5", "Pi 5"), ("CU-PLY-BOTTOM", "아랫판 (오꾸메)"),
        ("CU-PLY-BACK", "뒤판 (오꾸메)"), (r"CU-POST-PI", "Pi 받침 기둥"), ("TS-C-DSI", "DSI 리본"), ("O4-RESTFELT-D", "쉼 펠트"),
        ("O4-B-whitefrontfelt3T", "앞 펠트"), ("O4-B-keeperfelt-D", "키퍼 펠트")])
    sh.callouts_v(co, x1 + 14.0, 1, y0 - 6, y1 + 8, size=T_SMALL)
    # notes + table of the cut parts
    rows = []
    seen = collections.OrderedDict()
    for p, cs in cut:
        seen.setdefault(gname(p), []).append(p)
    for nm, ps in list(seen.items())[:30]:
        b = M.bbox([p.id for p in ps])
        if any(PAD_6T.search(p.id) for p in ps):
            nm = "※ " + nm
        rows.append([fit(nm, 82, T_SMALL - 0.4), fit(codes_txt(ps), 26.5, T_SMALL - 0.4), "%s~%s" % (fnum(b[1], 1), fnum(b[4], 1)), "%s~%s" % (fnum(b[2], 1), fnum(b[5], 1))])
    half = (len(rows) + 1) // 2
    ty = y1 + 30.0
    sh.text(16, ty - 3.0, "이 단면에 잘린 부품 (좌표는 입체의 바깥 상자)", T_NOTE + 0.2, bold=True, halo=False)
    cols = [("부품", 84.0, "start"), ("코드", 28.0, "start"), ("y", 30.0, "start"), ("z", 26.0, "start")]
    yt = max(sh.table(16, ty, cols, rows[:half], size=T_SMALL - 0.4, rh=3.3),
             sh.table(16 + 172, ty, cols, rows[half:], size=T_SMALL - 0.4, rh=3.3))
    sh.text(16 + text_w("이 단면에 잘린 부품 (좌표는 입체의 바깥 상자)", T_NOTE + 0.2) + 5.0, ty - 3.0, CODE_HEAD, T_SMALL - 0.4, cls="tm", halo=False)
    D.notes_box(sh, 16, yt + 7.0, 345, "※ 패드 바 · 업스톱 패드 — 출력 파일과 그림의 차이", pad_note_lines(M, "O4"), size=T_SMALL)
    sh.legend2(372, ty - 3.0, sh.used, cols=2, colw=106)
    sh.scale_bar(372, ty + 40.0, 1.0, 50, 10, "1:1")
    sh.title_block()
    return sh


PAD_6T = re.compile(r"PADBAR|-B-upstoppad-")


def pad_note_lines(M, mod):
    """the pad bars are drawn from the assembly solids (designed for 6T urethane + 1T felt); the print STLs have the wedge 1.0
    thicker for the PORON 5T (i124) + felt 1T that was bought - the pad face stays where it is (manifest print note)."""
    bars = sorted([p for p in M.ka if p.id.startswith(mod + "-PADBAR-") and p.print_solid is not None], key=lambda p: p.id)
    d = []
    for p in bars:
        a, q = p.solid.bounding_box(), p.print_solid.bounding_box()
        d.append(((q[5] - q[2]) - (a[5] - a[2]), a[2], a[5]))
    dz = max(t[0] for t in d)
    z0, z1 = min(t[1] for t in d), max(t[2] for t in d)
    allbars = [p for p in M.ka if "-PADBAR-" in p.id]
    pc = sorted(c for c in codes_of(allbars) if c.startswith("P-"))
    return ["그림과 표는 조립 모델로 그렸습니다: 업스톱 패드 = 설계값 우레탄 6T + 펠트 1T, 패드 바 z%s~%s." % (fnum(z0), fnum(z1)),
            "실제로 뽑는 패드 바 STL(03 탭 %s)은 쐐기가 패드 면 법선으로 1.0 두껍습니다 "
            "— 구매한 PORON 5T(i124) + 펠트 1T 기준. 높이가 %s 커서 아래 끝이 z%s까지 내려옵니다." % (" · ".join(pc), fnum(dz), fnum(z0 - dz)),
            "패드 면(업스톱이 닿는 면)의 위치는 같아서 건반 높이와 멈춤 위치는 그림과 같습니다. PORON 6T를 따로 사면 stl/print_extra의 6T용 패드 바를 뽑습니다."]


# ------------------------------------------------------------------ I05 module internal plan

KEY_OFF = re.compile(r"-(KEY|CAPSTAN|NUT|MAGNET)-")
LEVER_OFF = re.compile(r"-(LEVER|STEEL|FELTSTRIP|SPRING)-|-B-upstoppad-|PADBAR|CURTAIN|-B-leverrod|-PLUG$")


def sheet_I05(M, Hh):
    import body
    sh = FSheet("I05", "1:1")
    mod = [p for p in M.ka if p.group.startswith("O4")] + [p for p in M.parts if p.id.startswith("O4-C-")]
    fb = M.bb(M.by["O4-FRAME"])
    heading2(sh, 16, 21, "건반 모듈 내부 평면 — O4 (x%s~%s), 위에서 봄" % (fnum(fb[0]), fnum(fb[3])), "1:1 · 연주자는 아래쪽 · 잘린 면 빗금")
    win = (fb[0] - 4.0, fb[3] + 4.0, -4.0, 216.0)
    za, zb_ = 54.0, 30.0
    pa = [p for p in mod if not KEY_OFF.search(p.id)]
    pb = [p for p in pa if not LEVER_OFF.search(p.id)]
    va, ita, cuta = sec_view(sh, Hh, M, pa, "top", win, 1.0, (40.0, 56.0), "z", za, "<", r=0.07)
    vb, itb, cutb = sec_view(sh, Hh, M, pb, "top", win, 1.0, (40.0 + 177.0 + 52.0, 56.0), "z", zb_, "<", r=0.07)
    for v, ttl in ((va, "① 건반을 빼고 z%s에서 자름 — 레버·스프링·강철" % fnum(za)), (vb, "② 레버도 빼고 z%s에서 자름 — 센서·기판·선" % fnum(zb_))):
        x0, y0, x1, y1 = v.rect
        v.frame()
        sh.text(x0, y0 - 24.0, ttl, T_HEAD - 1.0, bold=True)
    # ① ordinates: lever centres (x), rods / curtain (y)
    levers = sorted([p for p in pa if "-LEVER-" in p.id], key=lambda p: M.bb(p)[0])
    lx = [(M.bb(p)[0] + M.bb(p)[3]) / 2 for p in levers]
    ords_h(sh, va, lx, -1, gap=2.0)
    lrod = M.bb(M.by["O4-B-leverrodD4SUS304x151629"])
    rod = M.bb(M.by["O4-B-keyrodSUS304D4"])
    cu = M.bb(M.by["O4-CURTAIN"])
    stl = M.bb(M.by["O4-STEEL-C"])
    ords_v(sh, va, [0.0, (rod[1] + rod[4]) / 2, cu[1], stl[1], stl[4], (lrod[1] + lrod[4]) / 2, fb[4]], -1, gap=1.5)
    sh.textblock(va.rect[0], va.rect[3] + 6.0, ["위 숫자 = 레버 가운데 x (12개, 레버 캐리어 입체의 바깥 상자 가운데)"], T_SMALL, cls="tm")
    # ② boards
    bx = []
    by_ = []
    for pid in ("O4-E-SB", "O4-E-MB", "O4-E-ZERO", "O4-E-MUX", "O4-SENSORBAR"):
        b = M.bb(M.by[pid])
        bx += [b[0], b[3]]
        by_ += [b[1], b[4]]
    ords_h(sh, vb, [x for x in bx if True], -1, gap=2.0)
    ords_v(sh, vb, sorted(set(round(y, 2) for y in by_ + [0.0, fb[4]])), 1, gap=1.5)
    co_b = callouts_for(vb, item_map(itb), [("O4-E-SB", "센서 기판 SB (홀 센서 12)"), ("O4-SENSORBAR", "센서 바"), ("O4-E-MB", "제어 기판 MB"),
                                           ("O4-E-ZERO", "RP2040-Zero"), ("O4-E-MUX", "4067 먹스"), ("O4-C-RIBBON", "16심 리본 W104"),
                                           ("O4-C-USB", "USB-C W204"), ("O4-B-keyrodSUS304D4", "건반 봉 Ø4"), (r"O4-B-balancepinD2-", "밸런스 핀 Ø2 ×12"),
                                           ("O4-FRAME", "프레임"), ("O4-EVA", "EVA 3T")])
    sh.callouts_h(co_b, vb.rect[3] + 18.0, 1, vb.rect[0] - 10, vb.rect[2] + 40, size=T_SMALL)
    co_a = callouts_for(va, item_map(ita), [("O4-LEVER-E", "레버 캐리어 ×12"), ("O4-STEEL-E", "강철 블록 ×12"), ("O4-SPRING-E", "비틀림 스프링 ×12"),
                                           ("O4-B-leverrodD4SUS304x151629", "레버 봉 Ø4"), ("O4-FRAME", "프레임 (윗판 z72.85는 잘려 나감)")])
    sh.callouts_h(co_a, va.rect[3] + 18.0, 1, va.rect[0] - 10, va.rect[2] + 30, size=T_SMALL)
    # parts table of one module
    g = collections.OrderedDict()
    for p in mod:
        g.setdefault(gname(p), []).append(p)
    rows = []
    for nm, ps in g.items():
        rows.append([("※ " if any(PAD_6T.search(p.id) for p in ps) else "") + nm, codes_txt(ps), str(len(ps))])
    tx = 470.0
    sh.text(tx, 35.0, "모듈 하나 (O4)의 부품 · 수량", T_NOTE + 0.2, bold=True, halo=False)
    sh.text(tx, 40.0, CODE_HEAD_SHORT, T_SMALL - 0.4, cls="tm", halo=False)
    sh.table(tx, 43.0, [("부품 (모델 이름)", 68.0, "start"), ("코드", 28.0, "start"), ("수", 8.0, "middle")], [[fit(r[0], 66, T_SMALL - 0.45), fit(r[1], 26.5, T_SMALL - 0.45), r[2]] for r in rows],
             size=T_SMALL - 0.45, rh=3.2)
    sh.legend2(16, 330, sh.used, cols=3, colw=96)
    sh.scale_bar(16, 362, 1.0, 50, 10, "1:1")
    D.notes_box(sh, 120, 358, 240, "읽는 법", [
        "모듈 x는 47 + 164.5·(k-1)에서 시작합니다 (O4 = x%s). 모듈 안 좌표 = 이 x - %s." % (fnum(fb[0]), fnum(fb[0])),
        "건반·레버의 자세한 치수는 도면 1~10 (건반 액션), 프레임은 도면 8에 있습니다.",
        "※ 표의 패드 바·업스톱 패드는 조립 모델(설계 우레탄 6T + 펠트 1T) 기준입니다. 뽑는 패드 바 STL은 쐐기가 1.0 두껍습니다 "
        "(구매한 PORON 5T + 펠트 1T, 패드 면 위치는 같음 — I04 주).",
    ], size=T_SMALL)
    sh.title_block()
    sh.chk("O4 모듈 시작 x", fb[0], 47 + 164.5 * 3, "x = 47 + 164.5·(k−1)")
    return sh


# ------------------------------------------------------------------ self check against the written STL files + main

def stl_checks(M):
    """compare numbers printed on the sheets with the STL files the last build wrote (stl/assembly, stl/print)."""
    import trimesh
    out = []
    use = use_parts(M)
    allb = M.bbox([p.id for p in use if p.id not in ("PEDAL-DAMPER",)])
    p_all = os.path.join(OUT, "stl", "assembly", "Toccata_전체조립.stl")
    if os.path.exists(p_all):
        b = trimesh.load(p_all, force="mesh").bounds
        for lab, pr, ref in (("전체 폭 (E01·E02·E05·E06)", allb[3] - allb[0], b[1][0] - b[0][0]),
                             ("전체 깊이 (E03·E04)", allb[4] - allb[1], b[1][1] - b[0][1]),
                             ("가장 높은 곳 z = 화면 받침 위 끝 (E01·E03)", allb[5], b[1][2])):
            out.append(dict(sheet="STL", label=lab, printed=round(float(pr), 3), ref=round(float(ref), 3), src="stl/assembly/Toccata_전체조립.stl bounds"))
    with open(os.path.join(OUT, "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    by_id = {}
    for it in man["print"]:
        for i in it.get("ids", []):
            by_id[i] = it
    for pid in ("CU-SCREENLID", "LID-L", "SPKL-BAFFLE", "TS-CRADLE", "CU-PLY-END-L", "PR-BACKPLATE"):
        it = by_id.get(pid)
        p = M.by.get(pid)
        if it is None or p is None or p.print_solid is None:
            continue
        f = os.path.join(OUT, it["file"])
        bs = p.print_solid.bounding_box()
        own = sorted([bs[3] - bs[0], bs[4] - bs[1], bs[5] - bs[2]], reverse=True)
        if os.path.exists(f):
            tb = trimesh.load(f, force="mesh").bounds
            ref = sorted((tb[1] - tb[0]).tolist(), reverse=True)
            src = it["file"]
        else:
            ref = sorted(it["size_mm"], reverse=True)
            src = "manifest size_mm"
        out.append(dict(sheet="STL", label="%s 출력 크기 (가장 긴 변)" % pid, printed=round(own[0], 3), ref=round(ref[0], 3), src=src))
    return out


def main(codes=None, verbose=True):
    t0 = time.time()
    import build_all
    parts = build_all.collect()
    M = D.Model(parts)
    Hh = HLR(M)
    codes = codes or list(SHEETS)
    done, checks, layout = [], [], {}
    for code in codes:
        t = time.time()
        sh = globals()["sheet_" + code](M, Hh)
        p, bad = write(sh)
        done.append(p)
        checks += sh.checks
        layout[code] = bad
        if verbose:
            print("drawings_final: %s %s (%.1f s, %d KB)%s" % (code, os.path.relpath(p, OUT), time.time() - t, os.path.getsize(p) // 1024,
                                                             ("  layout: " + "; ".join(bad[:8])) if bad else ""))
    if len(codes) == len(SHEETS):
        checks += stl_checks(M)
    for c in checks:
        c["ok"] = abs(c["printed"] - c["ref"]) <= 0.006
    rep = dict(date=DATE, state=STATE, sheets={c: SHEETS[c][0] + ".svg" for c in codes}, layout_issues=layout, checks=checks,
               all_ok=all(c["ok"] for c in checks) and not any(layout.values()))
    with open(os.path.join(FIN, "checks.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    if verbose:
        bad = [c for c in checks if not c["ok"]]
        print("drawings_final: %d checks, %d mismatched, layout issues %d - %.0f s" % (len(checks), len(bad), sum(len(v) for v in layout.values()), time.time() - t0))
        for c in bad:
            print("   MISMATCH", c)
    return done, rep


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a in SHEETS]
    main(args or None)
