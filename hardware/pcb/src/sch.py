"""Tiny schematic engine for the Toccata circuit sheets.

Draws KiCad-style schematic sheets as SVG (A3, mm units) and rebuilds the
connectivity from the drawn geometry (wires, pins, labels, power symbols),
so every sheet can be checked against the intended netlist (a small ERC).

Coordinates: mm, origin top-left of the A3 sheet, y down. Grid 2.5 mm.
"""
import html
import math

GRID = 2.5
SHEET_W, SHEET_H = 420.0, 297.0

FONT = "'IBM Plex Sans KR','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif"
MONO = "'IBM Plex Mono',Menlo,Consolas,monospace"

CSS = f"""
.frame{{fill:none;stroke:#7a1f1f;stroke-width:.35}}
.frame2{{fill:none;stroke:#7a1f1f;stroke-width:.2}}
.zone{{font:2.2px {MONO};fill:#7a1f1f;text-anchor:middle}}
.tb{{fill:none;stroke:#7a1f1f;stroke-width:.3}}
.tbk{{font:1.9px {FONT};fill:#7a1f1f}}
.tbv{{font:2.8px {FONT};fill:#101820}}
.tbt{{font:600 4.6px {FONT};fill:#101820}}
.tbs{{font:600 3.2px {FONT};fill:#101820}}
.wire{{fill:none;stroke:#0b7a2a;stroke-width:.3;stroke-linecap:round;stroke-linejoin:round}}
.bus{{fill:none;stroke:#1f4fa0;stroke-width:.8}}
.cable{{fill:none;stroke:#8a5a00;stroke-width:.45;stroke-dasharray:2.2 1.1}}
.jn{{fill:#0b7a2a}}
.body{{fill:#fffbe6;stroke:#8c1c13;stroke-width:.3}}
.bodyl{{fill:none;stroke:#8c1c13;stroke-width:.3}}
.bodyf{{fill:#8c1c13;stroke:#8c1c13;stroke-width:.2}}
.mod{{fill:#eef4fb;stroke:#1f4fa0;stroke-width:.35}}
.modl{{fill:none;stroke:#1f4fa0;stroke-width:.3}}
.pinl{{stroke:#8c1c13;stroke-width:.3}}
.pinnum{{font:1.9px {MONO};fill:#a3281b}}
.pinname{{font:2.3px {MONO};fill:#0e5e5e}}
.pinnameh{{font:2.3px {FONT};fill:#0e5e5e}}
.ref{{font:600 2.7px {FONT};fill:#0e4a6e}}
.val{{font:2.4px {FONT};fill:#0e4a6e}}
.part{{font:1.9px {FONT};fill:#56657a}}
.lbl{{font:600 2.4px {MONO};fill:#101820}}
.glbl{{fill:#fff;stroke:#7a1f1f;stroke-width:.3}}
.glblt{{font:600 2.2px {MONO};fill:#7a1f1f}}
.pwr{{fill:none;stroke:#7a1f1f;stroke-width:.35}}
.pwrt{{font:600 2.4px {MONO};fill:#7a1f1f}}
.nc{{stroke:#1f4fa0;stroke-width:.35}}
.note{{font:2.35px {FONT};fill:#1b2a44}}
.noteb{{font:600 2.8px {FONT};fill:#1b2a44}}
.notes{{font:2.0px {FONT};fill:#44536b}}
.box{{fill:none;stroke:#8a96ab;stroke-width:.25;stroke-dasharray:1.5 1}}
.boxt{{font:600 2.6px {FONT};fill:#44536b}}
.tblh{{font:600 2.1px {FONT};fill:#1b2a44}}
.tbl{{font:2.0px {FONT};fill:#1b2a44}}
.tblm{{font:2.0px {MONO};fill:#1b2a44}}
.tline{{stroke:#b6bfcc;stroke-width:.2}}
.chg{{fill:#fff1c2;stroke:#b86e00;stroke-width:.3}}
.chgt{{font:600 1.9px {MONO};fill:#8a4f00;text-anchor:middle}}
.cabt{{font:600 2.2px {FONT};fill:#8a5a00}}
"""

DIRV = {"R": (1, 0), "L": (-1, 0), "U": (0, -1), "D": (0, 1)}


def _k(x, y):
    return (round(x * 100), round(y * 100))


def text_w(s, size):
    """Rough text width estimate in mm (for overlap checks)."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x1100:
            w += 1.0
        elif ch in "il.,:;|!'`":
            w += 0.32
        elif ch == " ":
            w += 0.33
        else:
            w += 0.6
    return w * size


class Sym:
    """Symbol definition in local coordinates (rot 0)."""

    def __init__(self, name, kind="box"):
        self.name = name
        self.kind = kind  # 'two' for 2-terminal passives, 'box' otherwise
        self.g = []
        self.pins = []

    def line(self, x1, y1, x2, y2, cls="bodyl"):
        self.g.append(("line", x1, y1, x2, y2, cls))

    def rect(self, x, y, w, h, cls="body"):
        self.g.append(("rect", x, y, w, h, cls))

    def circle(self, cx, cy, r, cls="bodyl"):
        self.g.append(("circle", cx, cy, r, cls))

    def poly(self, pts, cls="bodyl", closed=False):
        self.g.append(("poly", pts, cls, closed))

    def arc(self, x1, y1, r, x2, y2, sweep=1, cls="bodyl"):
        self.g.append(("arc", x1, y1, r, x2, y2, sweep, cls))

    def text(self, x, y, s, cls="pinnameh", anchor="start"):
        self.g.append(("text", x, y, s, cls, anchor))

    def pin(self, num, name, x, y, d, length=5.0, show_name=True, show_num=True,
            nameh=False, etype="pas"):
        self.pins.append(dict(num=str(num), name=name, x=x, y=y, d=d, len=length,
                              sn=show_name, snum=show_num, nameh=nameh, etype=etype))


def xf(rot, mirror, ox, oy):
    def f(x, y):
        if mirror:
            x = -x
        for _ in range((rot // 90) % 4):
            x, y = -y, x
        return ox + x, oy + y
    return f


def xd(rot, mirror, d):
    x, y = DIRV[d]
    if mirror:
        x = -x
    for _ in range((rot // 90) % 4):
        x, y = -y, x
    for k, v in DIRV.items():
        if v == (x, y):
            return k
    raise ValueError


class Sheet:
    def __init__(self, code, num, total, title, subtitle, board, rev="B",
                 date="2026-09-29", qty="", basis=""):
        self.code, self.num, self.total = code, num, total
        self.title, self.subtitle, self.board = title, subtitle, board
        self.rev, self.date, self.qty, self.basis = rev, date, qty, basis
        self.out = {"frame": [], "box": [], "wire": [], "body": [], "pin": [], "text": [], "top": []}
        self.pins = {}      # (ref, num) -> dict(x,y,name)
        self.segs = []      # (x1,y1,x2,y2)
        self.labels = []    # (x,y,name,kind)
        self.ncs = []
        self.parts = {}     # ref -> meta
        self.texts = []     # (x0,y0,x1,y1,s) for overlap check
        self.bodies = []    # (x0,y0,x1,y1,ref)
        self.warnings = []
        self.mates = []     # (refA, refB, pin-map dict or None)
        self.gboxes = []    # graphic boxes (power symbols etc.) for text collision checks

    # ---------- low level svg ----------
    def _t(self, layer, x, y, s, cls, anchor="start", rot=0, size=None, check=True):
        tr = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot else ""
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        self.out[layer].append(
            f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}"{a}{tr}>{html.escape(str(s))}</text>')
        if check and size:
            w = text_w(str(s), size)
            if rot:
                # rotated -90: text runs upward from (x,y) for anchor start
                if anchor == "start":
                    bx = (x - size * 0.8, y - w, x + size * 0.2, y)
                elif anchor == "end":
                    bx = (x - size * 0.8, y, x + size * 0.2, y + w)
                else:
                    bx = (x - size * 0.8, y - w / 2, x + size * 0.2, y + w / 2)
            else:
                x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
                bx = (x0, y - size * 0.78, x0 + w, y + size * 0.2)
            self.texts.append((*bx, str(s)))

    def line(self, x1, y1, x2, y2, cls="bodyl", layer="body"):
        self.out[layer].append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="{cls}"/>')

    def rect(self, x, y, w, h, cls="box", layer="box", rx=0):
        r = f' rx="{rx}"' if rx else ""
        self.out[layer].append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"{r} class="{cls}"/>')

    def text(self, x, y, s, cls="note", anchor="start", size=2.35, rot=0, layer="text", check=True):
        self._t(layer, x, y, s, cls, anchor, rot, size, check)

    def para(self, x, y, lines, cls="note", size=2.35, lh=None, layer="text"):
        lh = lh or size * 1.45
        for i, s in enumerate(lines):
            if s:
                self.text(x, y + i * lh, s, cls, size=size, layer=layer)
        return y + len(lines) * lh

    def box(self, x, y, w, h, title=None):
        self.rect(x, y, w, h, "box", "box", rx=1.2)
        if title:
            self.text(x + 1.5, y + 3.4, title, "boxt", size=2.6)

    # ---------- symbols ----------
    def place(self, sym, ref, value, x, y, rot=0, mirror=False, part="", ref_at=None,
              val_at=None, part_at=None, meta=None, hide_ref=False, hide_val=False):
        f = xf(rot, mirror, x, y)
        for g in sym.g:
            t = g[0]
            if t == "line":
                (a, b), (c, d) = f(g[1], g[2]), f(g[3], g[4])
                self.line(a, b, c, d, g[5])
            elif t == "rect":
                (a, b), (c, d) = f(g[1], g[2]), f(g[1] + g[3], g[2] + g[4])
                x0, y0, x1, y1 = min(a, c), min(b, d), max(a, c), max(b, d)
                self.out["body"].append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1-x0:.2f}" height="{y1-y0:.2f}" class="{g[5]}"/>')
                if g[5] in ("body", "mod"):
                    self.bodies.append((x0, y0, x1, y1, ref))
            elif t == "circle":
                a, b = f(g[1], g[2])
                self.out["body"].append(f'<circle cx="{a:.2f}" cy="{b:.2f}" r="{g[3]}" class="{g[4]}"/>')
            elif t == "poly":
                pts = " ".join("%.2f,%.2f" % f(px, py) for px, py in g[1])
                tag = "polygon" if g[3] else "polyline"
                self.out["body"].append(f'<{tag} points="{pts}" class="{g[2]}"/>')
            elif t == "arc":
                (a, b), (c, d) = f(g[1], g[2]), f(g[4], g[5])
                sw = g[6] if not mirror else 1 - g[6]
                self.out["body"].append(
                    f'<path d="M{a:.2f},{b:.2f} A{g[3]},{g[3]} 0 0 {sw} {c:.2f},{d:.2f}" class="{g[7]}"/>')
            elif t == "text":
                a, b = f(g[1], g[2])
                self._t("text", a, b, g[3], g[4], g[5], 0, 2.3)
        for p in sym.pins:
            px, py = f(p["x"], p["y"])
            d = xd(rot, mirror, p["d"])
            vx, vy = DIRV[d]
            ex, ey = px + vx * p["len"], py + vy * p["len"]
            if p["len"] > 0:
                self.out["pin"].append(
                    f'<line x1="{px:.2f}" y1="{py:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" class="pinl"/>')
            key = (ref, p["num"])
            if key in self.pins:
                raise ValueError(f"duplicate pin {key}")
            self.pins[key] = dict(x=px, y=py, name=p["name"], etype=p["etype"])
            if p["snum"] and p["len"] > 0:
                mx, my = (px + ex) / 2, (py + ey) / 2
                if d in ("L", "R"):
                    self._t("pin", mx, my - 0.55, p["num"], "pinnum", "middle", 0, 1.9)
                else:
                    self._t("pin", mx - 0.55, my, p["num"], "pinnum", "middle", -90, 1.9)
            if p["sn"] and p["name"]:
                if d == "R":
                    self._t("pin", ex + 0.9, ey + 0.8, p["name"], "pinname", "start", 0, 2.3)
                elif d == "L":
                    self._t("pin", ex - 0.9, ey + 0.8, p["name"], "pinname", "end", 0, 2.3)
                elif p["nameh"]:
                    if d == "D":
                        self._t("pin", ex, ey + 2.6, p["name"], "pinnameh", "middle", 0, 2.3)
                    else:
                        self._t("pin", ex, ey - 0.9, p["name"], "pinnameh", "middle", 0, 2.3)
                elif d == "D":
                    self._t("pin", ex + 0.8, ey + 0.9, p["name"], "pinname", "end", -90, 2.3)
                else:
                    self._t("pin", ex + 0.8, ey - 0.9, p["name"], "pinname", "start", -90, 2.3)
        # reference / value text
        if sym.kind == "two":
            p1 = self.pins[(ref, sym.pins[0]["num"])]
            p2 = self.pins[(ref, sym.pins[1]["num"])]
            vertical = abs(p1["x"] - p2["x"]) < 0.01
            if vertical:
                ra, va, pa = (x + 3.2, y - 0.6, "start"), (x + 3.2, y + 2.4, "start"), (x + 3.2, y + 4.8, "start")
            else:
                ra, va, pa = (x, y - 3.0, "middle"), (x, y + 4.9, "middle"), (x, y + 7.1, "middle")
        else:
            xs = [b[0] for b in self.bodies if b[4] == ref] or [x]
            ys = [b[1] for b in self.bodies if b[4] == ref] or [y]
            ys2 = [b[3] for b in self.bodies if b[4] == ref] or [y]
            bx0, by0, by1 = min(xs), min(ys), max(ys2)
            ra, va, pa = (bx0, by0 - 1.2, "start"), (bx0, by1 + 3.0, "start"), (bx0, by1 + 5.3, "start")
        if ref_at:
            ra = (x + ref_at[0], y + ref_at[1], ref_at[2] if len(ref_at) > 2 else "start")
        if val_at:
            va = (x + val_at[0], y + val_at[1], val_at[2] if len(val_at) > 2 else "start")
        if part_at:
            pa = (x + part_at[0], y + part_at[1], part_at[2] if len(part_at) > 2 else "start")
        if not hide_ref:
            self._t("text", ra[0], ra[1], ref, "ref", ra[2], 0, 2.7)
        if value and not hide_val:
            self._t("text", va[0], va[1], value, "val", va[2], 0, 2.4)
        if part:
            self._t("text", pa[0], pa[1], part, "part", pa[2], 0, 1.9)
        m = dict(meta or {})
        m.setdefault("value", value)
        m.setdefault("symbol", sym.name)
        self.parts[ref] = m
        return self

    def pin(self, ref, num):
        p = self.pins[(ref, str(num))]
        return p["x"], p["y"]

    def pin_by_name(self, ref, name):
        for (r, n), p in self.pins.items():
            if r == ref and p["name"] == name:
                return n
        raise KeyError((ref, name))

    # ---------- connections ----------
    def wire(self, *pts):
        pts = [p for p in pts]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if abs(x1 - x2) > 1e-6 and abs(y1 - y2) > 1e-6:
                raise ValueError(f"non-orthogonal wire {pts}")
            if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
                continue
            self.segs.append((x1, y1, x2, y2))
        d = "M" + " L".join("%.2f,%.2f" % p for p in pts)
        self.out["wire"].append(f'<path d="{d}" class="wire"/>')

    def cable(self, *pts, text=None, at=None, anchor="middle"):
        """Physical cable (drawing only, not an electrical net inside a board sheet)."""
        d = "M" + " L".join("%.2f,%.2f" % p for p in pts)
        self.out["wire"].append(f'<path d="{d}" class="cable"/>')
        if text:
            tx, ty = at or pts[0]
            self.text(tx, ty, text, "cabt", anchor, 2.2)

    def label(self, x, y, name, side="R", up=True):
        """Local net label; text sits above the wire, starting at (x,y)."""
        self.labels.append((x, y, name, "local"))
        dy = -0.7 if up else 2.7
        if side == "R":
            self._t("text", x + 0.6, y + dy, name, "lbl", "start", 0, 2.4)
        elif side == "L":
            self._t("text", x - 0.6, y + dy, name, "lbl", "end", 0, 2.4)
        elif side == "U":
            self._t("text", x - 0.7, y - 0.6, name, "lbl", "start", -90, 2.4)
        else:
            self._t("text", x - 0.7, y + 0.6, name, "lbl", "end", -90, 2.4)
        self.out["top"].append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r=".35" fill="#101820"/>')

    def glabel(self, x, y, name, side="R", text=None):
        """Off-board / hierarchical label (pentagon flag). Connects by name inside the sheet."""
        self.labels.append((x, y, name, "global"))
        s = text or name
        w = text_w(s, 2.2) + 3.2
        h = 3.4
        if side == "R":
            pts = [(x, y), (x + 1.7, y - h / 2), (x + w, y - h / 2), (x + w, y + h / 2), (x + 1.7, y + h / 2)]
            tx, anc = x + 2.2, "start"
        else:
            pts = [(x, y), (x - 1.7, y - h / 2), (x - w, y - h / 2), (x - w, y + h / 2), (x - 1.7, y + h / 2)]
            tx, anc = x - 2.2, "end"
        self.out["top"].append('<polygon points="%s" class="glbl"/>' % " ".join("%.2f,%.2f" % p for p in pts))
        self._t("top", tx, y + 0.8, s, "glblt", anc, 0, 2.2)

    def pwr(self, x, y, name, kind=None):
        """Power symbol; connection point at (x,y). kind 'up' (rail) or 'gnd'."""
        kind = kind or ("gnd" if name.upper().startswith("GND") else "up")
        self.labels.append((x, y, name, "power"))
        o = self.out["top"]
        if kind == "gnd":
            self.gboxes.append((x - 2.1, y + 0.4, x + 2.1, y + 3.6, name))
            o.append(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x:.2f}" y2="{y+2:.2f}" class="pwr"/>')
            for i, hw in enumerate((2.0, 1.3, .6)):
                yy = y + 2 + i * 0.7
                o.append(f'<line x1="{x-hw:.2f}" y1="{yy:.2f}" x2="{x+hw:.2f}" y2="{yy:.2f}" class="pwr"/>')
            if name != "GND":
                self._t("top", x, y + 6.2, name, "pwrt", "middle", 0, 2.4)
        else:
            self.gboxes.append((x - 1.4, y - 2.7, x + 1.4, y - 0.4, name))
            o.append(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x:.2f}" y2="{y-2.2:.2f}" class="pwr"/>')
            o.append(f'<polyline points="{x-1.3:.2f},{y-1.2:.2f} {x:.2f},{y-2.6:.2f} {x+1.3:.2f},{y-1.2:.2f}" class="pwr"/>')
            self._t("top", x, y - 3.4, name, "pwrt", "middle", 0, 2.4)

    def mate(self, ra, rb, pinmap=None, at=None):
        """Mated connector pair: pin n of ra is connected to pin n (or pinmap[n]) of rb."""
        self.mates.append((ra, rb, pinmap))
        if at:
            x, y = at
            self.out["top"].append(f'<path d="M{x-1.6:.2f},{y-1.4:.2f} L{x:.2f},{y:.2f} L{x-1.6:.2f},{y+1.4:.2f} M{x+0.4:.2f},{y-1.4:.2f} L{x+2:.2f},{y:.2f} L{x+0.4:.2f},{y+1.4:.2f}" fill="none" stroke="#8c1c13" stroke-width=".35"/>')

    def nc(self, x, y):
        self.ncs.append((x, y))
        s = 0.9
        self.out["top"].append(f'<line x1="{x-s:.2f}" y1="{y-s:.2f}" x2="{x+s:.2f}" y2="{y+s:.2f}" class="nc"/>')
        self.out["top"].append(f'<line x1="{x-s:.2f}" y1="{y+s:.2f}" x2="{x+s:.2f}" y2="{y-s:.2f}" class="nc"/>')

    def chg(self, x, y, n):
        """Revision marker (triangle with number): change against the electronics text spec W1 inherited."""
        self.out["top"].append(
            f'<polygon points="{x:.2f},{y-2.2:.2f} {x+2.2:.2f},{y+1.6:.2f} {x-2.2:.2f},{y+1.6:.2f}" class="chg"/>')
        self._t("top", x, y + 1.05, str(n), "chgt", "middle", 0, 1.9, check=False)

    # ---------- tables ----------
    def table(self, x, y, cols, rows, widths, title=None, rh=3.3, mono_cols=()):
        yy = y
        if title:
            self.text(x, yy + 2.6, title, "noteb", size=2.8)
            yy += 4.2
        tw = sum(widths)
        self.line(x, yy, x + tw, yy, "tline", "text")
        cx = x
        for c, w in zip(cols, widths):
            self.text(cx + 0.8, yy + 2.4, c, "tblh", size=2.1)
            cx += w
        yy += rh
        self.line(x, yy, x + tw, yy, "tline", "text")
        for r in rows:
            cx = x
            for i, (c, w) in enumerate(zip(r, widths)):
                self.text(cx + 0.8, yy + 2.35, c, "tblm" if i in mono_cols else "tbl", size=2.0)
                cx += w
            yy += rh
            self.line(x, yy, x + tw, yy, "tline", "text")
        return yy

    # ---------- frame ----------
    def frame(self, notes=None, revs=None):
        o = self.out["frame"]
        m = 5.0
        o.append(f'<rect x="{m}" y="{m}" width="{SHEET_W-2*m}" height="{SHEET_H-2*m}" class="frame"/>')
        i = 9.0
        o.append(f'<rect x="{i}" y="{i}" width="{SHEET_W-2*i}" height="{SHEET_H-2*i}" class="frame2"/>')
        ncol, nrow = 8, 6
        cw, rhh = (SHEET_W - 2 * i) / ncol, (SHEET_H - 2 * i) / nrow
        for c in range(ncol + 1):
            xx = i + c * cw
            for y0, y1 in ((m, i), (SHEET_H - i, SHEET_H - m)):
                o.append(f'<line x1="{xx:.2f}" y1="{y0}" x2="{xx:.2f}" y2="{y1}" class="frame2"/>')
        for c in range(ncol):
            xx = i + (c + .5) * cw
            o.append(f'<text x="{xx:.2f}" y="{m+2.9:.2f}" class="zone">{c+1}</text>')
            o.append(f'<text x="{xx:.2f}" y="{SHEET_H-m-1.2:.2f}" class="zone">{c+1}</text>')
        for r in range(nrow + 1):
            yy = i + r * rhh
            for x0, x1 in ((m, i), (SHEET_W - i, SHEET_W - m)):
                o.append(f'<line x1="{x0}" y1="{yy:.2f}" x2="{x1}" y2="{yy:.2f}" class="frame2"/>')
        for r in range(nrow):
            yy = i + (r + .5) * rhh + 0.8
            L = "ABCDEF"[r]
            o.append(f'<text x="{m+2:.2f}" y="{yy:.2f}" class="zone">{L}</text>')
            o.append(f'<text x="{SHEET_W-m-2:.2f}" y="{yy:.2f}" class="zone">{L}</text>')
        # title block (bottom right)
        W, H = 176.0, 34.0
        x0, y0 = SHEET_W - i - W, SHEET_H - i - H
        self.tb_box = (x0, y0, x0 + W, y0 + H)
        t = self.out["frame"]
        t.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{W}" height="{H}" class="tb" fill="#fff"/>')
        rows = [0, 7.5, 18.5, 26, 34]
        for yy in rows[1:-1]:
            t.append(f'<line x1="{x0:.2f}" y1="{y0+yy:.2f}" x2="{x0+W:.2f}" y2="{y0+yy:.2f}" class="tb"/>')

        def cell(cx, cy, w, k, v, cls="tbv"):
            t.append(f'<text x="{cx+1.2:.2f}" y="{cy+2.3:.2f}" class="tbk">{html.escape(k)}</text>')
            t.append(f'<text x="{cx+1.2:.2f}" y="{cy+6.0:.2f}" class="{cls}">{html.escape(v)}</text>')
            if cx > x0:
                t.append(f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" y2="{cy+7.5:.2f}" class="tb"/>')
        cell(x0, y0, 100, "프로젝트", "Toccata v4 W1+ — 전자부 회로도")
        cell(x0 + 100, y0, 40, "기준 설계", self.basis or "v4 W1+ r4.5")
        cell(x0 + 140, y0, 36, "보드 / 수량", self.qty or self.board)
        t.append(f'<text x="{x0+1.2:.2f}" y="{y0+10.2:.2f}" class="tbk">도면명</text>')
        t.append(f'<text x="{x0+1.2:.2f}" y="{y0+16.4:.2f}" class="tbt">{html.escape(self.title)}</text>')
        cell(x0, y0 + 18.5, 34, "도면 번호", self.code, "tbs")
        cell(x0 + 34, y0 + 18.5, 24, "시트", f"{self.num} / {self.total}", "tbs")
        cell(x0 + 58, y0 + 18.5, 16, "개정", self.rev, "tbs")
        cell(x0 + 74, y0 + 18.5, 30, "날짜", self.date)
        cell(x0 + 104, y0 + 18.5, 38, "크기 · 단위", "A3 · mm")
        cell(x0 + 142, y0 + 18.5, 34, "작성", "Claude (검토 필요)")
        t.append(f'<text x="{x0+1.2:.2f}" y="{y0+28.4:.2f}" class="tbk">설명</text>')
        t.append(f'<text x="{x0+1.2:.2f}" y="{y0+32.2:.2f}" class="tbv" style="font-size:2.3px">{html.escape(self.subtitle)}</text>')
        # sheet heading (top left)
        self.text(i + 3, i + 7.5, f"{self.code}  {self.title}", "tbt", size=4.6)
        self.text(i + 3, i + 12.2, self.subtitle, "notes", size=2.0)

    # ---------- connectivity ----------
    def connectivity(self):
        parent = {}

        def find(a):
            parent.setdefault(a, a)
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        pts = []  # all interesting points
        for (ref, num), p in self.pins.items():
            pts.append(_k(p["x"], p["y"]))
        for x, y, n, kind in self.labels:
            pts.append(_k(x, y))
        for x1, y1, x2, y2 in self.segs:
            pts.append(_k(x1, y1))
            pts.append(_k(x2, y2))
        pts = set(pts)
        deg = {}
        for x1, y1, x2, y2 in self.segs:
            a, b = _k(x1, y1), _k(x2, y2)
            union(a, b)
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
            xa, xb = sorted((a[0], b[0]))
            ya, yb = sorted((a[1], b[1]))
            for p in pts:
                if p in (a, b):
                    continue
                if xa <= p[0] <= xb and ya <= p[1] <= yb and (xa == xb or ya == yb):
                    union(p, a)
                    deg[p] = deg.get(p, 0) + 2
        for (ref, num), p in self.pins.items():
            k = _k(p["x"], p["y"])
            find(k)
            deg[k] = deg.get(k, 0) + 1
        for ra, rb, pm in self.mates:
            pa = {n: p for (r, n), p in self.pins.items() if r == ra}
            pb = {n: p for (r, n), p in self.pins.items() if r == rb}
            for n, p in pa.items():
                m = (pm or {}).get(n, n)
                if m in pb:
                    q = pb[m]
                    union(_k(p["x"], p["y"]), _k(q["x"], q["y"]))
                    deg[_k(p["x"], p["y"])] = deg.get(_k(p["x"], p["y"]), 0) + 1
        for x, y, n, kind in self.labels:
            if kind == "power":
                k = _k(x, y)
                if deg.get(k, 0) >= 2:
                    deg[k] = deg.get(k, 0) + 1
        byname = {}
        for x, y, n, kind in self.labels:
            k = _k(x, y)
            find(k)
            if n in byname:
                union(k, byname[n])
            else:
                byname[n] = k
        # junction dots
        self.junctions = [k for k, v in deg.items() if v >= 3]
        for k in self.junctions:
            self.out["top"].append(f'<circle cx="{k[0]/100:.2f}" cy="{k[1]/100:.2f}" r=".6" class="jn"/>')
        groups = {}
        for (ref, num), p in self.pins.items():
            groups.setdefault(find(_k(p["x"], p["y"])), {"pins": set(), "names": set()})["pins"].add(f"{ref}.{num}")
        for x, y, n, kind in self.labels:
            groups.setdefault(find(_k(x, y)), {"pins": set(), "names": set()})["names"].add(n)
        # dangling wire ends
        pinpts = {_k(p["x"], p["y"]) for p in self.pins.values()}
        lblpts = {_k(x, y) for x, y, n, k in self.labels}
        ncpts = {_k(x, y) for x, y in self.ncs}
        for x1, y1, x2, y2 in self.segs:
            for k in (_k(x1, y1), _k(x2, y2)):
                if deg.get(k, 0) == 1 and k not in pinpts and k not in lblpts:
                    self.warnings.append(f"dangling wire end at ({k[0]/100},{k[1]/100})")
        nets = {}
        errors = []
        auto = 0
        for g in groups.values():
            names = sorted(g["names"])
            if len(names) > 1:
                errors.append(f"short: {names} pins {sorted(g['pins'])}")
            if names:
                nm = names[0]
            else:
                auto += 1
                nm = f"~N{auto}"
            if nm in nets:
                nets[nm] |= g["pins"]
            else:
                nets[nm] = set(g["pins"])
        for (ref, num), p in self.pins.items():
            k = _k(p["x"], p["y"])
            g = groups[find(k)]
            if len(g["pins"]) == 1 and not g["names"]:
                if k in ncpts:
                    continue
                errors.append(f"unconnected pin {ref}.{num} ({p['name']})")
        self.nets = nets
        return nets, errors

    def check(self, expected):
        """expected: dict netname -> list of 'REF.PIN'. Names starting with '~' are unlabeled nets."""
        nets, errors = self.connectivity()
        got_named = {k: v for k, v in nets.items() if not k.startswith("~")}
        got_anon = [frozenset(v) for k, v in nets.items() if k.startswith("~") and len(v) > 1]
        exp_named = {k: set(v) for k, v in expected.items() if not k.startswith("~")}
        exp_anon = [frozenset(v) for k, v in expected.items() if k.startswith("~")]
        for k, v in exp_named.items():
            g = got_named.get(k, set())
            if g != v:
                errors.append(f"net {k}: missing {sorted(v-g)} extra {sorted(g-v)}")
        for k, v in got_named.items():
            if k not in exp_named and v:
                errors.append(f"unexpected net {k}: {sorted(v)}")
        for s in exp_anon:
            if s not in got_anon:
                errors.append(f"anon net not found: {sorted(s)}")
        for s in got_anon:
            if s not in exp_anon:
                errors.append(f"unexpected anon net: {sorted(s)}")
        # overlap check between texts
        ov = []
        T = self.texts
        for a in range(len(T)):
            for b in range(a + 1, len(T)):
                A, B = T[a], T[b]
                if A[0] < B[2] - 0.15 and B[0] < A[2] - 0.15 and A[1] < B[3] - 0.15 and B[1] < A[3] - 0.15:
                    ov.append(f"text overlap: '{A[4]}' / '{B[4]}' at ({A[0]:.1f},{A[1]:.1f})")
        for G in self.gboxes:
            for A in T:
                if A[4] == G[4]:
                    continue
                if A[0] < G[2] and G[0] < A[2] and A[1] < G[3] and G[1] < A[3]:
                    ov.append(f"text on power symbol {G[4]}: '{A[4]}' at ({G[0]:.1f},{G[1]:.1f})")
        tb = getattr(self, "tb_box", None)
        for A in T:
            if tb and A[0] < tb[2] and tb[0] < A[2] and A[1] < tb[3] and tb[1] < A[3]:
                ov.append(f"text on title block: '{A[4]}'")
            if A[0] < 9.5 or A[2] > SHEET_W - 9.5 or A[1] < 9.5 or A[3] > SHEET_H - 9.5:
                ov.append(f"text outside frame: '{A[4]}'")
        self.overlaps = ov
        return errors

    def svg(self):
        body = "".join("".join(self.out[k]) for k in ("frame", "box", "wire", "body", "pin", "text", "top"))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SHEET_W} {SHEET_H}" '
                f'width="{SHEET_W}mm" height="{SHEET_H}mm" font-family="{FONT}">'
                f'<title>{html.escape(self.code + " " + self.title)}</title>'
                f'<style>{CSS}</style><rect width="{SHEET_W}" height="{SHEET_H}" fill="#fff"/>{body}</svg>')


# ======================= symbol library =======================

def sym_R(name="R"):
    s = Sym(name, "two")
    s.rect(-1.25, -3.75, 2.5, 7.5)
    s.pin(1, "", 0, -7.5, "D", 3.75, show_name=False, show_num=False)
    s.pin(2, "", 0, 7.5, "U", 3.75, show_name=False, show_num=False)
    return s


def sym_C(name="C", polar=False):
    s = Sym(name, "two")
    s.line(-2.5, -0.75, 2.5, -0.75, "bodyl")
    if polar:
        s.arc(-2.5, 1.2, 4.5, 2.5, 1.2, 0)
        s.text(-3.4, -1.6, "+", "pinnameh", "middle")
        s.line(0, 5, 0, 0.9, "pinl")
    else:
        s.line(-2.5, 0.75, 2.5, 0.75, "bodyl")
    s.pin(1, "", 0, -5, "D", 4.25, show_name=False, show_num=False)
    s.pin(2, "", 0, 5, "U", 4.25 if not polar else 0, show_name=False, show_num=False)
    return s


def sym_hall():
    """DRV5055 (TO-92 LPG): 1 VCC top, 2 GND bottom, 3 OUT right."""
    s = Sym("DRV5055", "box")
    s.rect(-5, -5, 10, 10)
    s.rect(-2.2, -1.6, 3.2, 3.2, "bodyl")
    s.line(-2.2, -1.6, 1.0, 1.6, "bodyl")
    s.pin(1, "VCC", 0, -7.5, "D", 2.5, nameh=True, etype="pwr")
    s.pin(2, "GND", 0, 7.5, "U", 2.5, nameh=True, etype="pwr")
    s.pin(3, "OUT", 7.5, 0, "L", 2.5, show_name=False, etype="out")
    return s


def sym_box(name, left=(), right=(), width=20.0, pitch=5.0, top_pad=5.0, cls="body",
            pinlen=5.0, title=None, rows=None):
    """Generic box. left/right = lists of (num, name[, etype]) or None for a gap.
    Origin = top-left of the body."""
    s = Sym(name, "box")
    n = rows or max(len(left), len(right))
    h = top_pad + pitch * (n - 1) + top_pad
    s.rect(0, 0, width, h, cls)
    for i, p in enumerate(left):
        if p is None:
            continue
        s.pin(p[0], p[1], -pinlen, top_pad + i * pitch, "R", pinlen, etype=p[2] if len(p) > 2 else "pas")
    for i, p in enumerate(right):
        if p is None:
            continue
        s.pin(p[0], p[1], width + pinlen, top_pad + i * pitch, "L", pinlen, etype=p[2] if len(p) > 2 else "pas")
    if title:
        for j, tl in enumerate(title if isinstance(title, (list, tuple)) else [title]):
            s.text(width / 2, -1.2 - (len(title) - 1 - j) * 2.8 if isinstance(title, (list, tuple)) else -1.2,
                   tl, "pinnameh", "middle")
    s.h = h
    s.w = width
    return s


def sym_conn(name, n, side="R", names=None, pitch=5.0, width=5.0, rev=False):
    """1xN connector. side = side the pins stick out. Origin = top-left of body. rev: pin 1 at the bottom."""
    s = Sym(name, "box")
    h = pitch * n
    s.rect(0, 0, width, h)
    for i in range(n):
        y = pitch * ((n - 1 - i) + 0.5) if rev else pitch * (i + 0.5)
        nm = names[i] if names else ""
        if side == "R":
            s.pin(i + 1, nm, width + 5, y, "L", 5, show_name=False)
            s.line(width - 1.6, y, width, y, "bodyl")
            s.circle(width - 2.2, y, 0.55, "bodyl")
        else:
            s.pin(i + 1, nm, -5, y, "R", 5, show_name=False)
            s.circle(2.2, y, 0.55, "bodyl")
            s.line(0, y, 1.6, y, "bodyl")
    s.h, s.w = h, width
    return s


def sym_jumper(name="SolderJumper", bridged=False):
    s = Sym(name + ("_2_Bridged" if bridged else "_2_Open"), "two")
    if bridged:
        s.rect(-0.8, -0.5, 1.6, 1.0, "bodyf")
    s.arc(-0.6, -1.6, 1.6, -0.6, 1.6, 0, "bodyf")
    s.line(-0.6, -1.6, -0.6, 1.6, "bodyl")
    s.arc(0.6, -1.6, 1.6, 0.6, 1.6, 1, "bodyf")
    s.line(0.6, -1.6, 0.6, 1.6, "bodyl")
    s.pin(1, "", -5, 0, "R", 2.8, show_name=False, show_num=False)
    s.pin(2, "", 5, 0, "L", 2.8, show_name=False, show_num=False)
    return s


def sym_fuse():
    s = Sym("Fuse", "two")
    s.rect(-4, -1.3, 8, 2.6)
    s.line(-4, 0, 4, 0, "bodyl")
    s.pin(1, "", -7.5, 0, "R", 3.5, show_name=False, show_num=False)
    s.pin(2, "", 7.5, 0, "L", 3.5, show_name=False, show_num=False)
    return s


def sym_switch():
    s = Sym("SW_SPST", "two")
    s.circle(-2.5, 0, 0.6, "bodyl")
    s.circle(2.5, 0, 0.6, "bodyl")
    s.line(-1.9, -0.3, 2.4, -2.6, "bodyl")
    s.pin(1, "", -7.5, 0, "R", 4.4, show_name=False, show_num=True)
    s.pin(2, "", 7.5, 0, "L", 4.4, show_name=False, show_num=True)
    return s


def sym_speaker():
    s = Sym("Speaker", "box")
    s.rect(0, -3.2, 3.2, 6.4)
    s.poly([(3.2, -3.2), (7.2, -7.0), (7.2, 7.0), (3.2, 3.2)], "bodyl", True)
    s.pin(1, "+", -5, -2.5, "R", 5, show_name=False)
    s.pin(2, "−", -5, 2.5, "R", 5, show_name=False)
    s.text(-1.2, -3.4, "+", "pinnameh", "middle")
    s.text(-1.2, 5.9, "−", "pinnameh", "middle")
    return s


def sym_jack(name="PJ-313"):
    """3.5 mm TRS jack with tip/ring normal contacts (KiCad AudioJack3_SwitchTR style).
    Pins on the right: T, TN, R, RN, S. Pin numbers = functional names; PJ-313 pad no. in text."""
    s = Sym(name, "box")
    s.rect(0, 0, 16, 27.5)
    # plug body graphic
    s.rect(1.5, 11.5, 3.0, 5.0, "bodyl")
    s.poly([(4.5, 12.4), (8.5, 12.4)], "bodyl")
    s.poly([(4.5, 15.6), (8.5, 15.6)], "bodyl")
    # contacts: T y=5, TN y=10, R y=15, RN y=20, S y=25 (relative to top pad 0)
    ys = {"T": 2.5, "TN": 7.5, "R": 12.5, "RN": 17.5, "S": 22.5}
    for nm, y in ys.items():
        s.pin(nm, nm, 21, y + 2.5, "L", 5, show_name=False, show_num=True)
    # switch arrows (normals touching T / R when no plug)
    s.poly([(16, 5), (11.5, 5), (10.5, 7.2)], "bodyl")
    s.poly([(16, 10), (11.5, 10), (11.5, 8.2)], "bodyl")
    s.poly([(10.8, 8.0), (11.5, 7.2), (12.2, 8.0)], "bodyf", True)
    s.poly([(16, 15), (11.5, 15), (10.5, 17.2)], "bodyl")
    s.poly([(16, 20), (11.5, 20), (11.5, 18.2)], "bodyl")
    s.poly([(10.8, 18.0), (11.5, 17.2), (12.2, 18.0)], "bodyf", True)
    s.poly([(16, 25), (3, 25), (3, 16.5)], "bodyl")
    s.h, s.w = 27.5, 16
    return s


def sym_xt30(gender="M"):
    s = Sym("XT30U-" + gender, "box")
    s.rect(0, 0, 6, 10)
    s.text(3, 4.0, "+", "pinnameh", "middle")
    s.text(3, 8.8, "−", "pinnameh", "middle")
    s.pin(1, "+", -5, 2.5, "R", 5, show_name=False)
    s.pin(2, "−", -5, 7.5, "R", 5, show_name=False)
    s.pin("1b", "+", 11, 2.5, "L", 5, show_name=False, show_num=False)
    s.pin("2b", "−", 11, 7.5, "L", 5, show_name=False, show_num=False)
    return s


def sym_plug(name="Plug_TRS"):
    """3.5 mm TRS plug (cable end). Pins on the left: T, R, S."""
    s = Sym(name, "box")
    s.rect(0, 0, 9, 15)
    s.poly([(9, 3.0), (13.5, 3.0), (15, 4.2), (13.5, 5.4), (9, 5.4)], "bodyl", True)
    s.line(11.2, 3.0, 11.2, 5.4, "bodyl")
    s.line(12.6, 3.0, 12.6, 5.4, "bodyl")
    for i, nm in enumerate(("T", "R", "S")):
        s.pin(nm, nm, -5, 2.5 + 5 * i, "R", 5, show_name=True, show_num=False)
    s.h, s.w = 15, 9
    return s


def sym_conn2(name, rows, pitch=5.0, width=12.0):
    """2xN connector, KiCad Conn_02xNN_Odd_Even: odd pins left, even pins right. Origin = top-left."""
    s = Sym(name, "box")
    h = pitch * rows
    s.rect(0, 0, width, h)
    for i in range(rows):
        y = pitch * (i + 0.5)
        s.pin(2 * i + 1, "", -5, y, "R", 5, show_name=False)
        s.pin(2 * i + 2, "", width + 5, y, "L", 5, show_name=False)
        s.circle(2.4, y, 0.55, "bodyl")
        s.circle(width - 2.4, y, 0.55, "bodyl")
    s.h, s.w = h, width
    return s


def sym_tp(name="TestPoint"):
    """Test point: one pin at the bottom, ring on top."""
    s = Sym(name, "box")
    s.circle(0, -3.2, 1.1, "bodyl")
    s.pin(1, "", 0, 0, "U", 2.1, show_name=False, show_num=False)
    return s


def sym_conn_pos(name, rows, pins, side="R", pitch=5.0, width=6.0):
    """1xN connector drawn with `rows` positions (R31 display harness). pins = [(num, row)];
    a row without a pin is drawn as an empty gap (separate single housings, e.g. two jumper ends)."""
    s = Sym(name, "box")
    h = pitch * rows
    s.rect(0, 0, width, h)
    for num, row in pins:
        y = pitch * (row + 0.5)
        if side == "R":
            s.pin(num, "", width + 5, y, "L", 5, show_name=False)
            s.line(width - 1.6, y, width, y, "bodyl")
            s.circle(width - 2.2, y, 0.55, "bodyl")
        else:
            s.pin(num, "", -5, y, "R", 5, show_name=False)
            s.circle(2.2, y, 0.55, "bodyl")
            s.line(0, y, 1.6, y, "bodyl")
    s.h, s.w = h, width
    return s
