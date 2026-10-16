"""Shop file for the plywood: all 10 pieces nested on one okoume 400 x 1200 x 11.5 sheet, 1:1, mm.

python3 hardware/mechanical/cad/src/ply_cnc.py
  -> hardware/mechanical/cad/drawings/plywood_cnc/Toccata_합판가공_400x1200.dxf   (CNC / laser shop)
     hardware/mechanical/cad/drawings/plywood_cnc/Toccata_합판가공_400x1200.svg   (preview, same geometry)
     hardware/mechanical/cad/drawings/plywood_cnc/pieces.json                    (what each piece needs)

Same solids, same nesting as sheet D06 (drawings.flat_piece / layout_xywh / relax_layout), so the numbers match the STL
build and the D06 / P-PLY sheets. Layers:
  CUT_OUTSIDE   outer contour of each piece (cut through, tool outside the line); square inside corners carry a dog-bone
                arc R3.2 (2026-10-15, bit up to D6.4) - the only place the DXF differs from the model outline
  CUT_INSIDE    through holes and inner cut-outs (cut through, tool inside the line); round holes are CIRCLEs
  POCKET_TOP / POCKET_BOTTOM   blind pockets on the face that is up / down on the sheet (depth in the label)
  SHEET         the 400 x 1200 board outline (do not cut)
  LABEL         piece names (do not cut)
Not on the sheet (done by hand, listed in pieces.json): pockets in the board EDGES and edge round-overs / chamfers.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.normpath(os.path.join(HERE, "..", "drawings", "plywood_cnc"))
SW, SH = 1200.0, 400.0


DOG_R = 3.2               # dog-bone relief radius: a router bit up to D6.4 (D6, 1/4" 6.35) reaches the corner point
DOG_ANGLE = (80.0, 100.0)  # only square inside corners get one (the 140 deg baffle step keeps ~0.2 of wood - harmless)


def dogbones(pts, r=DOG_R):
    """outer contour -> LWPOLYLINE points (x, y, bulge) with a dog-bone at every square inside corner.
    2026-10-15: a round bit leaves an R(bit) fillet in a concave corner; the printed back plate (P01 window) and the duct cap
    (P03 / P04 notch) have square corners there. The relief circle (radius r) has its centre r from the corner on the bisector,
    inside the cut-away side, so it passes through the corner point; the contour leaves each edge r*sqrt2 from the corner and runs a
    half circle through the corner (bulge +-1)."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2.0
    out, made = [], []
    for i in range(n):
        a, v, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        d1 = (a[0] - v[0], a[1] - v[1])
        d2 = (c[0] - v[0], c[1] - v[1])
        l1, l2 = math.hypot(*d1), math.hypot(*d2)
        cross = (v[0] - a[0]) * (c[1] - v[1]) - (v[1] - a[1]) * (c[0] - v[0])
        ang = math.degrees(math.acos(max(-1.0, min(1.0, (d1[0] * d2[0] + d1[1] * d2[1]) / (l1 * l2)))))
        if cross * area >= 0 or not (DOG_ANGLE[0] <= ang <= DOG_ANGLE[1]) or min(l1, l2) < 2.0 * r * math.sqrt(2.0):
            out.append((v[0], v[1], 0.0))
            continue
        u1, u2 = (d1[0] / l1, d1[1] / l1), (d2[0] / l2, d2[1] / l2)
        k = r * math.sqrt(2.0)
        p1 = (v[0] + u1[0] * k, v[1] + u1[1] * k)
        p2 = (v[0] + u2[0] * k, v[1] + u2[1] * k)
        cen = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)           # chord p1-p2 is a diameter (square corner)
        bulge = 1.0 if (p1[0] - cen[0]) * (v[1] - cen[1]) - (p1[1] - cen[1]) * (v[0] - cen[0]) > 0 else -1.0
        out += [(p1[0], p1[1], bulge), (p2[0], p2[1], 0.0)]
        made.append(dict(x=round(v[0], 2), y=round(v[1], 2), angle=round(ang, 1), r=r))
    return out, made


def bulge_to_svg(pl):
    """(x, y, bulge) closed polyline -> SVG path d (sheet coords; the group flips y)."""
    d = ["M %.3f %.3f" % pl[0][:2]]
    for i in range(len(pl)):
        x0, y0, b = pl[i]
        x1, y1, _ = pl[(i + 1) % len(pl)]
        if abs(b) < 1e-9:
            d.append("L %.3f %.3f" % (x1, y1))
        else:
            rr = math.hypot(x1 - x0, y1 - y0) / 2.0 * (1 + b * b) / (2 * abs(b))
            d.append("A %.3f %.3f 0 0 %d %.3f %.3f" % (rr, rr, 1 if b > 0 else 0, x1, y1))
    return " ".join(d) + " Z"


def rot_pts(p, W, rot):
    """piece coords -> layout coords (D06 rot90: (u, v) -> (v, W - u))."""
    if not rot:
        return [(float(u), float(v)) for u, v in p]
    return [(float(v), float(W - u)) for u, v in p]


def main():
    import numpy as np
    import build_all
    import body
    import drawings as D
    parts = build_all.collect()
    M = D.Model(parts)
    NEST = body.L2["plywood_cut_list"]["nesting_400x1200"]
    kerf = NEST["kerf"]
    plys = [p for p in M.rear if p.kind == "plywood"]
    if not plys:
        # 2026-10-16 (A안): every former plywood panel is printed - no shop file to make (the last one stays in drawings/plywood_cnc)
        print("no plywood parts (2026-10-16 A안: all panels printed) - nothing to cut, %s left as it was" % OUT)
        return
    import re
    pool = {}
    for sid, rx in D.PLY_SLOTS:
        order = rx.split("|")
        pool[sid] = sorted([D.flat_piece(M, p) for p in plys if re.match(rx, p.id)],
                           key=lambda fp: next(k for k, r_ in enumerate(order) if re.match(r_, fp["p"].id)))
    placed = []
    for sid, x, y, w, h in NEST["layout_xywh"]:
        fp = pool[sid].pop(0)
        W, H = fp["W"], fp["H"]
        if abs(W - w) < 1.5 and abs(H - h) < 1.5:
            rot = False
        elif abs(W - h) < 1.5 and abs(H - w) < 1.5:
            rot, (W, H) = True, (H, W)
        else:
            raise ValueError("piece %s does not fit slot %s" % (fp["p"].id, sid))
        placed.append(dict(fp=fp, sid=sid, x=x, y=y, W=W, H=H, rot=rot, cs=None))
    D.relax_layout(placed, kerf)
    left = [fp["p"].id for v in pool.values() for fp in v]
    assert not left, left

    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    for name, col in (("SHEET", 8), ("CUT_OUTSIDE", 1), ("CUT_INSIDE", 5), ("POCKET_TOP", 3), ("POCKET_BOTTOM", 6), ("LABEL", 7)):
        doc.layers.add(name, color=col)
    doc.styles.add("KOREAN", font="malgun.ttf")   # Korean labels: the default txt.shx shows them as ??? in AutoCAD
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (SW, 0), (SW, SH), (0, SH)], close=True, dxfattribs={"layer": "SHEET"})
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -60 %g %g" width="%gmm" height="%gmm">' % (SW + 40, SH + 120, SW + 40, SH + 120),
           '<rect x="-20" y="-60" width="%g" height="%g" fill="#fff"/>' % (SW + 40, SH + 120),
           '<g transform="translate(0,%g) scale(1,-1)">' % SH,
           '<rect x="0" y="0" width="%g" height="%g" fill="#f3e6cf" stroke="#999" stroke-width="0.6"/>' % (SW, SH)]
    labels = []
    report = []
    bad = []
    for a in placed:
        fp = a["fp"]
        info = D.piece_memo(fp, M)
        Wp = fp["W"]
        ox, oy = a["x"], a["y"]
        name = fp["p"].name_ko

        def to_sheet(p):
            return [(ox + u, oy + v) for u, v in rot_pts(p, Wp, a["rot"])]
        # which piece face lies UP on the sheet: piece coordinates are seen from +axis (face 1) for every axis in flat_piece
        # (proj along the axis); a 90 deg in-plane rotation keeps the face. So face 1 = up, face 0 = down.
        outer = to_sheet(info["outer"])
        dog_pl, dogs = dogbones(outer)
        msp.add_lwpolyline(dog_pl, format="xyb", close=True, dxfattribs={"layer": "CUT_OUTSIDE"})
        svg.append('<path d="%s" fill="#e4cfa8" stroke="#c0392b" stroke-width="0.8"/>' % bulge_to_svg(dog_pl))
        thru_out = []
        for h in info["thru"]:
            cu, cv = rot_pts([(h["cu"], h["cv"])], Wp, a["rot"])[0]
            cx, cy = ox + cu, oy + cv
            if h["round"]:
                msp.add_circle((cx, cy), h["d"] / 2.0, dxfattribs={"layer": "CUT_INSIDE"})
                svg.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#fff" stroke="#1f5fbf" stroke-width="0.6"/>' % (cx, cy, h["d"] / 2.0))
                thru_out.append(dict(kind="원 구멍", d=round(h["d"], 2), x=round(cx, 2), y=round(cy, 2)))
        # non-round inner cut-outs: take the actual hole polygons from the projection
        for q in D.polys(fp["proj"]):
            if D.signed_area(q) >= 0:
                continue
            u0, v0 = q.min(0)
            u1, v1 = q.max(0)
            hh = next((h for h in info["thru"] if abs(h["cu"] - (u0 + u1) / 2) < 0.05 and abs(h["cv"] - (v0 + v1) / 2) < 0.05), None)
            if hh is not None and hh["round"]:
                continue
            pts = to_sheet(q)
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT_INSIDE"})
            svg.append('<polygon points="%s" fill="#fff" stroke="#1f5fbf" stroke-width="0.6"/>' % " ".join("%.2f,%.2f" % p for p in pts))
            thru_out.append(dict(kind="따냄", w=round(u1 - u0, 2), h=round(v1 - v0, 2)))
        pockets_out = []
        for h in info["blind"]:
            cu, cv = rot_pts([(h["cu"], h["cv"])], Wp, a["rot"])[0]
            cx, cy = ox + cu, oy + cv
            lay = "POCKET_TOP" if h["face"] == 1 else "POCKET_BOTTOM"
            r = (h["d"] or (h["w"] + h["h"]) / 2) / 2.0
            msp.add_circle((cx, cy), r, dxfattribs={"layer": lay})
            msp.add_text("%s %.1f" % ("깊이" if h["face"] == 1 else "뒷면 깊이", h["depth"]), height=3,
                         dxfattribs={"layer": "LABEL", "style": "KOREAN"}).set_placement((cx + r + 1, cy))
            svg.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="#1e7a46" stroke-dasharray="1.5 1" stroke-width="0.6"/>' % (cx, cy, r))
            pockets_out.append(dict(face="윗면" if h["face"] == 1 else "밑면", d=round(2 * r, 2), depth=round(h["depth"], 2), x=round(cx, 2), y=round(cy, 2)))
        cx, cy = ox + a["W"] / 2.0, oy + a["H"] / 2.0
        txt = "P%02d %s  %.1f x %.1f" % (len(report) + 1, name, fp["W"] if not a["rot"] else fp["H"], fp["H"] if not a["rot"] else fp["W"])
        th = 6 if min(a["W"], a["H"]) > 40 else 3.2
        msp.add_text(txt, height=th, dxfattribs={"layer": "LABEL", "style": "KOREAN"}).set_placement((cx, cy), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        labels.append('<text x="%.2f" y="%.2f" font-size="%g" text-anchor="middle" dominant-baseline="middle" font-family="Apple SD Gothic Neo, Noto Sans KR, sans-serif">%s</text>'
                      % (cx, SH - cy, th, txt))
        for q in outer:
            if q[0] < -1e-6 or q[1] < -1e-6 or q[0] > SW + 1e-6 or q[1] > SH + 1e-6:
                bad.append("%s outside the sheet" % fp["p"].id)
                break
        report.append(dict(no="P%02d" % (len(report) + 1), id=fp["p"].id, name=name, size=[round(fp["W"], 2), round(fp["H"], 2), round(fp["T"], 2)],
                           at=[round(ox, 2), round(oy, 2)], rotated=a["rot"], through=thru_out, dogbones=dogs, pockets_face=pockets_out,
                           edge_pockets=info["notes"], edge_profiles=[m for m in info["memo"] if "모서리 R" in m or "모따기" in m],
                           memo=info["memo"]))
    svg.append("</g>")
    svg += labels
    svg.append('<text x="0" y="-30" font-size="14" font-family="Apple SD Gothic Neo, Noto Sans KR, sans-serif">Toccata 합판 가공 — 오꾸메 11.5 또는 자작 12T, '
               '400 × 1200, 1:1 mm · 빨강 = 바깥 자르기 (안쪽 직각 모서리 도그본 R%s, 공구 Ø%s 이하) · 파랑 = 안쪽 구멍·따냄 (관통) · 초록 점선 = 막힌 자리</text>'
               % (DOG_R, 2 * DOG_R))
    svg.append("</svg>")
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, "Toccata_합판가공_400x1200")
    doc.saveas(base + ".dxf")
    open(base + ".svg", "w", encoding="utf-8").write("\n".join(svg))
    json.dump(dict(sheet=[SW, SH, 11.5], kerf=kerf, pieces=report, problems=bad), open(os.path.join(OUT, "pieces.json"), "w"),
              ensure_ascii=False, indent=1)
    n_c = sum(len(r["through"]) for r in report)
    print("pieces %d, through features %d, dog-bones %d, face pockets %d, edge pocket notes %d, problems %s -> %s.dxf"
          % (len(report), n_c, sum(len(r["dogbones"]) for r in report), sum(len(r["pockets_face"]) for r in report),
             sum(len(r["edge_pockets"]) for r in report), bad or 0, base))


if __name__ == "__main__":
    main()
