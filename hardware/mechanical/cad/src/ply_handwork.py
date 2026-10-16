"""What the user does by hand on the plywood after the CNC shop (ply_cnc.py) has cut the 10 pieces and the through holes.

python3 hardware/mechanical/cad/src/ply_handwork.py
  -> hardware/mechanical/cad/drawings/plywood_cnc/Toccata_합판_직접가공.svg
     hardware/mechanical/cad/drawings/plywood_cnc/handwork.json

Everything comes from the CAD model (drawings.piece_memo for edge pockets / edge rounds, body.wood_screws for the screw spots),
in the same piece coordinates as the CNC sheet: u from the LEFT end seen from the front of the instrument, v from the FRONT edge
(bottom panels, seen from above) or from the BOTTOM edge (back panel, seen from inside / the front).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.normpath(os.path.join(HERE, "..", "drawings", "plywood_cnc"))
S = 1.4                     # drawing scale (svg units per mm)
FONT = "Apple SD Gothic Neo, Noto Sans KR, sans-serif"

PIECES = [("CU-PLY-BACK", "가운데 유닛 뒤판", "안쪽 면(악기 앞에서 보는 면)을 본 그림 · 위 = 윗모서리"),
          ("CU-PLY-BOTTOM", "가운데 유닛 아랫판", "위에서 본 그림 · 아래 = 앞 모서리(연주자 쪽)"),
          ("SPKL-PLY-BOTTOM", "스피커 L 아랫판", "위에서 본 그림 · 아래 = 앞 모서리"),
          ("SPKR-PLY-BOTTOM", "스피커 R 아랫판", "위에서 본 그림 · 아래 = 앞 모서리")]

KIND = {
    "pocket": ("#c0392b", "자석 자리 Ø8 × 깊이 3.2 (모서리 안으로, 판 두께 가운데)", "지금: J-b 새들 + Ø8 날 + J-e '자8' 척 멈춤. 판을 붙이기 전에"),
    "round": ("#1e8449", "모서리 R3 둥글리기 (윗면 앞 모서리)", "지금: 사포·줄로 R3. 회색 칸(빼는 곳)은 깎지 않음"),
    "foot": ("#1f5fbf", "고무발 나사 자리 (밑면에서) 8호 13 mm 직결피스", "조립 때: 고무발을 대고 송곳으로 자리 → 피스 (깊이 10)"),
    "csk": ("#d35400", "접시 피스 자리 (윗면에서) 8호 13 mm", "조립 때: 출력물(배터리 틀·뒤판 탭)을 놓고 구멍으로 송곳 → 피스 (깊이 9)"),
    "pan": ("#7d3c98", "허브 선반 받침 나사 자리 Ø3 × 12~13 (안쪽 면에서)", "조립 때: 받침을 대고 송곳 → 나사 (깊이 8)"),
}


def fnum(x, nd=1):
    s = ("%." + str(nd) + "f") % x
    return s.rstrip("0").rstrip(".") if "." in s else s


def main():
    import io
    import contextlib
    import build_all
    import body
    import drawings as D
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        parts = build_all.collect()
    M = D.Model(parts)
    plys = {p.id: p for p in M.rear if p.kind == "plywood"}
    screws = body.wood_screws()

    report = []
    svg_body = []
    y_cur = 70.0
    x0 = 30.0
    width = 0.0
    for pid, title, view in PIECES:
        fp = D.flat_piece(M, plys[pid])
        info = D.piece_memo(fp, M)
        W, H, T = fp["W"], fp["H"], fp["T"]
        marks = []
        # edge pockets (magnets)
        for pk in info["pockets"]:
            marks.append(dict(kind="pocket", edge=pk["edge"], c=pk["c"], d=pk["w"], depth=pk["depth"]))
        # edge rounds: parse the memo the CNC sheet / P-PLY sheet use
        rounds = []
        for m in info["memo"]:
            mm = re.match(r"(\S+) (\S+) 모서리 R([\d.]+)(?:, 빼는 곳 (.*))?$", m)
            if mm:
                skips = [tuple(float(a) for a in s.strip()[1:].split("~")) for s in (mm.group(4) or "").split("·") if s.strip()]
                edge = D.EDGE_KO[fp["ax"]].index(mm.group(2))
                rounds.append(dict(kind="round", face=mm.group(1), edge=edge, r=float(mm.group(3)), skip=skips))
        # screw spots
        for s in screws:
            if s["ply"] != pid:
                continue
            a = s["at"]
            P = {"x": (s["face"], a[0], a[1]), "y": (a[0], s["face"], a[1]), "z": (a[0], a[1], s["face"])}[s["axis"]]
            u, v = D.piece_uv(fp, P)
            depth = abs(s["tip"] - s["face"])
            marks.append(dict(kind=s["kind"], u=u, v=v, d=s["d"], depth=depth, label=s["label"]))
        marks.sort(key=lambda m_: (["pocket", "foot", "csk", "pan"].index(m_["kind"]), round(m_.get("v", 0)), m_.get("u", m_.get("c", 0))))

        # ---- draw ------------------------------------------------------------------------------------------------
        strip = any(m_["kind"] == "pocket" for m_ in marks)
        top_pad = 40.0 + (T * S + 44 if strip else 0)
        oy = y_cur + top_pad                      # svg y of the piece top edge (v = H)

        def X(u):
            return x0 + u * S

        def Y(v):
            return oy + (H - v) * S
        g = ['<g>']
        g.append('<text x="%.1f" y="%.1f" font-size="17" font-weight="700">%s <tspan font-weight="400" font-size="13" fill="#555">%s × %s × %s · %s</tspan></text>'
                 % (x0, y_cur + 18, title, fnum(W), fnum(H), fnum(T), view))
        if strip:                                  # top edge seen from above, above the face view
            sy = oy - 14 - T * S
            ol = list(info["outer"])           # the top edge = outline segments lying on v = H (a notch breaks it)
            for k in range(len(ol)):
                (ua, va), (ub, vb) = ol[k], ol[(k + 1) % len(ol)]
                if abs(va - H) < 0.05 and abs(vb - H) < 0.05:
                    a_, b_ = sorted((ua, ub))
                    g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#f3e6cf" stroke="#555" stroke-width="0.8"/>'
                             % (X(a_), sy, (b_ - a_) * S, T * S))
            g.append('<text x="%.1f" y="%.1f" font-size="11" fill="#555">윗모서리 (위에서 봄, 두께 %s)</text>' % (X(0), sy - 22, fnum(T)))
        pts = " ".join("%.1f,%.1f" % (X(u), Y(v)) for u, v in info["outer"])
        g.append('<polygon points="%s" fill="#f3e6cf" stroke="#555" stroke-width="0.9"/>' % pts)
        for h in info["thru"]:                     # done by the shop: faint
            if h["round"]:
                g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#fff" stroke="#bbb" stroke-width="0.6"/>' % (X(h["cu"]), Y(h["cv"]), h["d"] / 2 * S))
        for q in D.polys(fp["proj"]):
            if D.signed_area(q) < 0:
                u0, v0 = q.min(0)
                u1, v1 = q.max(0)
                if (u1 - u0) > 12 and (v1 - v0) > 12:
                    g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fff" stroke="#bbb" stroke-width="0.6"/>'
                             % (X(u0), Y(v1), (u1 - u0) * S, (v1 - v0) * S))
                    g.append('<text x="%.1f" y="%.1f" font-size="10" fill="#999" text-anchor="middle">창 (업체가 따냄)</text>'
                             % (X((u0 + u1) / 2), Y((v0 + v1) / 2) + 3))
        rows = []
        for r in rounds:
            col = KIND["round"][0]
            L = W if r["edge"] in (2, 3) else H
            cuts = [0.0] + [c for s_ in r["skip"] for c in s_] + [L]
            segs = [(cuts[k], cuts[k + 1]) for k in range(0, len(cuts) - 1, 2)]
            vv = 0.0 if r["edge"] == 2 else H
            for a_, b_ in segs:
                g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="5" stroke-linecap="butt" opacity="0.85"/>'
                         % (X(a_), Y(vv), X(b_), Y(vv), col))
            for a_, b_ in r["skip"]:
                g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="9" fill="#888"/>' % (X(a_), Y(vv) - 4.5, (b_ - a_) * S))
                g.append('<text x="%.1f" y="%.1f" font-size="10" fill="#444" text-anchor="middle">빼는 곳 %s~%s</text>'
                         % (X((a_ + b_) / 2), Y(vv) + 18, fnum(a_), fnum(b_)))
            g.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" font-weight="700">R%s ← 초록 선 = 둥글릴 모서리</text>' % (X(4), Y(vv) + 18, col, fnum(r["r"])))
            rows.append(dict(kind="round", text="윗면 %s 모서리 R%s, 깎지 않는 곳 %s" % (D.EDGE_KO[fp["ax"]][r["edge"]], fnum(r["r"]),
                                                                                  ", ".join("%s~%s" % (fnum(a_), fnum(b_)) for a_, b_ in r["skip"]))))
        n = {}
        boxes = [(X(m_["u"]) - 6, Y(m_["v"]) - 6, X(m_["u"]) + 6, Y(m_["v"]) + 6) for m_ in marks if "u" in m_]

        def place(xm, ym, w=16, h=10):
            # first label spot (right-up, right-down, left-up, left-down) that hits no mark and no earlier label
            for dx, dy, anc in ((6, -6, "start"), (6, 14, "start"), (-6, -6, "end"), (-6, 14, "end")):
                bx0 = xm + dx if anc == "start" else xm + dx - w
                b = (bx0, ym + dy - h, bx0 + w, ym + dy)
                if not any(b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3] for o in boxes):
                    boxes.append(b)
                    return xm + dx, ym + dy, anc
            return xm + 6, ym - 6, "start"
        for m_ in marks:
            col = KIND[m_["kind"]][0]
            n[m_["kind"]] = n.get(m_["kind"], 0) + 1
            k = n[m_["kind"]]
            if m_["kind"] == "pocket":
                c = m_["c"]
                sy = oy - 14 - T * S
                g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#fff" stroke="%s" stroke-width="1.6"/>' % (X(c), sy + T * S / 2, m_["d"] / 2 * S, col))
                # hidden pocket in the face view (goes down from the top edge)
                g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="%s" stroke-width="1.2" stroke-dasharray="3 2"/>'
                         % (X(c - m_["d"] / 2), Y(H), m_["d"] * S, m_["depth"] * S, col))
                g.append('<text x="%.1f" y="%.1f" font-size="12" fill="%s" text-anchor="middle" font-weight="700">%s</text>' % (X(c), sy - 6, col, fnum(c)))
                rows.append(dict(kind="pocket", u=round(c, 2), text="자석 자리 %d: 왼쪽 끝에서 %s (오른쪽 끝에서 %s)" % (k, fnum(c), fnum(W - c))))
            else:
                u, v = m_["u"], m_["v"]
                r_ = 4.2
                g.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" fill-opacity="0.18" stroke="%s" stroke-width="1.5"/>' % (X(u), Y(v), r_, col, col))
                g.append('<path d="M%.1f %.1fh%.1fM%.1f %.1fv%.1f" stroke="%s" stroke-width="1"/>' % (X(u) - r_ - 2, Y(v), 2 * r_ + 4, X(u), Y(v) - r_ - 2, 2 * r_ + 4, col))
                tag = {"foot": "F", "csk": "C", "pan": "P"}[m_["kind"]] + str(k)
                tx, ty, anc = place(X(u), Y(v))
                g.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" font-weight="700" text-anchor="%s">%s</text>' % (tx, ty, col, anc, tag))
                vref = "앞 모서리" if fp["ax"] == "z" else "아래 모서리"
                rows.append(dict(kind=m_["kind"], tag=tag, u=round(u, 2), v=round(v, 2),
                                 text="%s: 왼쪽 끝에서 %s, %s에서 %s" % (tag, fnum(u), vref, fnum(v))))
        # simple overall dimensions
        g.append('<text x="%.1f" y="%.1f" font-size="11" fill="#555" text-anchor="middle">← %s →</text>' % (X(W / 2), Y(0) + 32, fnum(W)))
        g.append('<text x="%.1f" y="%.1f" font-size="11" fill="#555">왼쪽 끝 ▶</text>' % (X(0), Y(0) + 32))
        # list beside / below
        ly = Y(0) + 52
        for r in rows:
            col = KIND[r["kind"]][0]
            g.append('<text x="%.1f" y="%.1f" font-size="12"><tspan fill="%s">■</tspan> %s</text>' % (x0, ly, col, r["text"]))
            ly += 16
        g.append("</g>")
        svg_body += g
        width = max(width, x0 + W * S + 30)
        report.append(dict(id=pid, name=title, size=[round(W, 2), round(H, 2), round(T, 2)], view=view, marks=rows))
        y_cur = ly + 22

    # legend + steps
    width = max(width, 1040.0)
    leg = ['<g>']
    ly = y_cur + 6
    leg.append('<text x="%.1f" y="%.1f" font-size="15" font-weight="700">표시 뜻 · 언제 하나</text>' % (x0, ly))
    ly += 22
    for k in ("pocket", "round", "foot", "csk", "pan"):
        col, what, when = KIND[k]
        leg.append('<rect x="%.1f" y="%.1f" width="14" height="14" fill="%s"/>' % (x0, ly - 11, col))
        leg.append('<text x="%.1f" y="%.1f" font-size="12.5"><tspan font-weight="700">%s</tspan> — %s</text>' % (x0 + 22, ly, what, when))
        ly += 20
    ly += 8
    notes = ["회색 원·창은 업체가 이미 뚫어 오는 것입니다 (Ø8 관통 50개, 뒤판 창).",
             "'왼쪽 끝' = 악기를 앞(연주자 쪽)에서 본 왼쪽. 뒤판은 창이 가까운 쪽이 왼쪽 끝입니다.",
             "받으면 먼저 조각마다 연필로 이름 · 앞뒤 · 위아래 · 왼오른쪽을 적습니다.",
             "지금 할 것은 빨강(자석 자리 4곳)과 초록(R3) 두 가지뿐입니다. 파랑·주황·보라는 조립할 때 부품을 대고 송곳으로 자리를 냅니다 (드릴 없음).",
             "자석 자리는 자투리에 먼저 하나 파서 Ø8 × 3 자석이 면보다 튀어나오지 않는지 봅니다 (cad/jigs/README.md J-b · J-e)."]
    for t in notes:
        leg.append('<text x="%.1f" y="%.1f" font-size="12.5">· %s</text>' % (x0, ly, t))
        ly += 19
    leg.append("</g>")
    H_ = ly + 20
    head = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f" font-family="%s">' % (width, H_, width, H_, FONT),
            '<rect x="0" y="0" width="%.0f" height="%.0f" fill="#fff"/>' % (width, H_),
            '<text x="%.1f" y="32" font-size="21" font-weight="700">Toccata 합판 — 내가 직접 할 가공</text>' % x0,
            '<text x="%.1f" y="52" font-size="12.5" fill="#555">업체 CNC(Toccata_합판가공_400x1200.dxf) 다음에 할 일 · 치수 mm · CAD 모델에서 읽은 값 · 그림 배율 같음(1 mm = %s)</text>' % (x0, fnum(S))]
    svg = head + svg_body + leg + ["</svg>"]
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "Toccata_합판_직접가공.svg")
    open(p, "w", encoding="utf-8").write("\n".join(svg))
    json.dump(report, open(os.path.join(OUT, "handwork.json"), "w"), ensure_ascii=False, indent=1)
    for r in report:
        print(r["id"], [m["text"] for m in r["marks"]])
    print("->", p)


if __name__ == "__main__":
    main()
