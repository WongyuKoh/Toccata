"""09 CAD 모델 tab for the merged v4 artifact.

Writes, next to this file:
  cad.html   the tab section (static tables: print list, adjustments, assumed values, file map)
  parts.json compact part table for the 3D viewer (id, name, kind, group, bbox, print file, notes, dims)
The GLB comes from ../Toccata_전체조립.glb (build_all.py). docs/report/toccata-v4/merge.py copies parts.json and the
GLB into docs/report/toccata-v4/cad/ and splices cad.html / cad.css / cad.js into index.html.
Run after `python3 ../src/build_all.py`.
"""
import collections
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(CAD, "src"))

import body  # noqa: E402  (L2 numbers from the one ANGLE constant)
import touchscreen_rev3 as TS  # noqa: E402  (R31 rev 3 numbers / poses)
import make_readme  # noqa: E402  (ADJUSTMENTS, L2 figures, note parsing)
from annotate_parts import family_of, merged_dims  # noqa: E402

KIND = {"print": "출력", "bought": "구매", "plywood": "합판", "electronics": "전자", "consumable": "소모품"}
LID_IDS = ["LID-L", "CU-SCREENLID", "LID-R"]          # L2 lids (+ their magnets / screws, see lid_ids())
X_O4 = 47 + 164.5 * 3


def lid_ids(man):
    """everything that comes off with the three L2 lids: the lids, the lid-side magnets, the screen-lid screws and the R31 touchscreen
    (it comes off with the screen lid, spec B / O4 service)."""
    ids = [p["id"] for p in man["parts"] if p.get("note") not in ("offdesk", "altview")]
    out = [i for i in LID_IDS if i in ids]
    out += [i for i in ids if i.startswith("CU-MAG-LID-") or i.startswith("CU-M3X10-") or i.startswith("TS-")]
    return out


def l2_dims():
    """dimension overlay (model coordinates) for the L2 body."""
    fg = make_readme.FG
    yb, zt, y0 = body.YB, body.SPK_ZT, body.Y0
    dy0, dy1 = body.DUCT_Y
    F, T = body.SL_A, body.SL_B
    f = make_readme.f
    return [
        {"t": "1254 전체 폭 (A05)", "a": [-16, -45, 0], "b": [1238, -45, 0], "ea": [-16, 0, 0], "eb": [1238, 0, 0]},
        {"t": "%s 전체 깊이 (L2)" % f(yb), "a": [-70, 0, 0], "b": [-70, yb, 0], "ea": [-16, 0, 0], "eb": [-16, yb, 0]},
        {"t": "212 건반 모듈", "a": [1290, 0, 0], "b": [1290, 212, 0], "ea": [1238, 0, 0], "eb": [1238, 212, 0]},
        {"t": "통로 %s (y%s~%s, 닫힘)" % (f(dy1 - dy0), f(dy0, 0), f(dy1, 0)), "a": [1290, dy0, 0], "b": [1290, dy1, 0],
         "ea": [1238, dy0, 0], "eb": [1238, dy1, 0]},
        {"t": "%s 뒷바 (y%s~%s)" % (f(yb - y0), f(y0, 0), f(yb)), "a": [1340, y0, 0], "b": [1340, yb, 0], "ea": [1238, y0, 0], "eb": [1238, yb, 0]},
        {"t": "164.5 모듈 O4 (P01)", "a": [X_O4, -20, 72.85], "b": [X_O4 + 164.5, -20, 72.85], "ea": [X_O4, 0, 72.85], "eb": [X_O4 + 164.5, 0, 72.85]},
        {"t": "z%s 건반 윗면 = 가운데 뚜껑 (L2)" % f(body.Z_LID), "a": [611, yb + 12, 0], "b": [611, yb + 12, body.Z_LID]},
        {"t": "z%s 스피커 윗면 (%s°)" % (f(zt), f(body.ANGLE, 1)), "a": [1260, yb, 0], "b": [1260, yb, zt]},
        {"t": "%s° 앞판 (경사 %s)" % (f(body.ANGLE, 1), f(body.SL_LEN)), "a": [-32, F[0], F[1]], "b": [-32, T[0], T[1]],
         "ea": [-16, F[0], F[1]], "eb": [-16, T[0], T[1]]},
        {"t": "통로 z%s~%s" % (f(body.DUCT_Z[0], 0), f(body.DUCT_Z[1], 0)), "a": [611, dy0 - 1, 0], "b": [611, dy0 - 1, body.DUCT_Z[1]]},
        {"t": "z43.5 백건 윗면 (S02)", "a": [-40, 20, 0], "b": [-40, 20, 43.5]},
    ] + touch_dims()


def touch_dims():
    """R31 rev 3: screen top and front-most point (25 deg use pose), hinge axis, folded height (numbers.json / touchscreen_rev3.py)."""
    f = make_readme.f
    P = TS.POINTS
    xs = TS.XC + TS.CR_XR[1] + 14.0                                   # just right of the cradle
    yf, zf = P["use"]["cr_bot_front"]
    yt, zt = P["use"]["cr_top_front"]
    h22 = TS.pt(TS.CR_U[0], TS.CR_W[0], TS.TILT_HEEL)
    return [
        {"t": "z%s 화면 받침 윗끝 (25°, 화면 위 끝 z%s)" % (f(zt), f(P["use"]["glass_top"][1])), "a": [xs, yt, TS.LID_TOP], "b": [xs, yt, zt],
         "ea": [TS.XC + TS.CR_XR[1], yt, zt], "eb": [xs, yt, zt]},
        {"t": "y%s 화면 가장 앞 (25°; 22°에서 y%s, 모듈 위 금지 y≤%s)" % (f(yf), f(h22[0]), f(TS.KEEP_Y, 0)), "a": [xs, 212.0, zf], "b": [xs, yf, zf],
         "ea": [TS.XC + TS.CR_XR[1], yf, zf], "eb": [xs, yf, zf]},
        {"t": "경첩 축 y%s z%s" % (f(TS.AX_Y), f(TS.AX_Z)), "a": [TS.XC - 140, TS.AX_Y, TS.LID_TOP], "b": [TS.XC - 140, TS.AX_Y, TS.AX_Z]},
    ]


def l2_views():
    """camera presets read by cad.js (eye / target in model coordinates, optional section x and lids off)."""
    xl = body.DRV_X["L"]
    return {
        "all": {"eye": [-260, -900, 760], "tgt": [611, 200, 40]},
        "front": {"eye": [611, -1500, 300], "tgt": [611, 190, 70]},
        "back": {"eye": [-520, 980, 640], "tgt": [611, 230, 40]},
        "module": {"eye": [500, -170, 260], "tgt": [622, 110, 30]},
        "section": {"eye": [X_O4 + 35.25 + 380, 170, 90], "tgt": [X_O4 + 35.25, 170, 36], "section": round(X_O4 + 35.25, 2)},
        "pod": {"eye": [xl + 640, 190, 120], "tgt": [xl, 200, 72], "section": xl},
        "rear": {"eye": [611, 40, 840], "tgt": [611, 278, 30], "lids": False},
        "touch": {"eye": [TS.XC + 430, 80, 260], "tgt": [TS.XC, 250, 120]},
    }


def esc(s):
    return html.escape(str(s), quote=True)


def main():
    man = json.load(open(os.path.join(CAD, "manifest.json")))
    # Part.dims + family dims per part (label, value text)
    import build_all
    parts = build_all.collect()
    pdims = {}
    for p in parts:
        d = []
        for (ax, a, b, lab, ln) in merged_dims(family_of(p), p.dims):
            d.append([lab, ("%.2f" % (b - a)).rstrip("0").rstrip(".")])
        pdims[p.id] = d[:14]
    shown = [p for p in man["parts"] if p.get("note") not in ("offdesk", "altview")]     # = the GLB (folded touchscreen: stl/assembly only)
    groups = []
    for p in shown:
        if p["group"] not in groups:
            groups.append(p["group"])
    rows = []
    for p in shown:
        pn = ""
        pr = None
        if p.get("print_file"):
            pr = next((r for r in man["print"] if r["file"] == p["print_file"]), None)
        rows.append({
            "id": p["id"], "n": p["name_ko"], "k": p["kind"], "g": groups.index(p["group"]),
            "b": [round(v, 1) for v in p["bbox"]],
            "f": os.path.basename(p["print_file"]) if p.get("print_file") else "",
            "m": p.get("material", ""), "pn": (pr or {}).get("note", "")[:260],
            "nt": (p.get("note") or "")[:260], "d": pdims.get(p["id"], []),
        })
    dims = l2_dims()
    lids = lid_ids(man)
    data = {"groups": groups, "parts": rows, "dims": dims, "lids": lids, "section_x": round(X_O4 + 35.25, 2), "views": l2_views()}
    json.dump(data, open(os.path.join(HERE, "parts.json"), "w"), ensure_ascii=False, separators=(",", ":"))

    # ---------------- static section
    pr = man["print"]
    n_print = sum(r["qty"] for r in pr)
    kinds = collections.Counter(p["kind"] for p in man["parts"] if p.get("note") not in ("offdesk", "altview"))
    H = []
    a = H.append
    a('<section class="page" id="p-cad" hidden>')
    a('<h2>CAD 모델: 출력용 STL과 전체 조립</h2>')
    fg = make_readme.FG
    f = make_readme.f
    a('<p class="lede">건반 액션 r4.5(geometry.json)와 L2 한 몸 뒷바(spec/body_L2.json, 2026-10-01 사용자 요청, W1 음향 확인 통과)를 수치 그대로 입체로 만든 결과입니다. '
      '출력 부품은 베드에 놓인 STL로, 나머지는 조립 위치에 둔 구매품·합판·전자 부품 외곽으로 들어 있습니다. '
      '만능기판은 사각형만, 그 위에는 RP2040-Zero·먹스 모듈처럼 부피 있는 부품만 두었습니다. '
      '뒷바는 건반 뒤 2 mm에서 시작해 전체 깊이 %s (L1 447, 건반 뒤 면적 %s %%)입니다: 가운데 뚜껑 윗면이 건반 윗면과 같은 z%s, 스피커는 수평에서 %s° 눕힌 앞판에 윗면 z%s, '
      '모듈 USB 선은 뒷바 밑 닫힌 통로(y%s~%s, z0~%s) 안이라 밖에서 거의 보이지 않습니다(배기 홈 아래와 건반 뒤 2 mm 틈으로만 조금). 터치스크린은 R31 3판(Waveshare 7-DSI-TOUCH-C, W1 3a)으로 가운데 화면 뚜껑의 경첩에 25°로 서 있고, 접은 상태는 <code>stl/assembly/</code>의 별도 그룹입니다. '
      '저장소 <code>hardware/mechanical/cad/</code>에서 <code>python3 src/build_all.py</code> 한 번으로 모두 다시 만들어집니다(약 10~20초).</p>'
      % (f(fg["depth"]), f(fg["area_pct"], 1).replace("-", "−"), f(fg["centre_top"]), f(fg["angle"], 1), f(fg["top"]),
         f(fg["duct_y"][0], 0), f(fg["duct_y"][1], 0), f(fg["duct_z"][1], 0)))
    a('<div class="kfs">')
    for b, s in [("%d" % sum(kinds.values()), "조립 부품 (페달·접은 화면 제외)"), ("%d종" % len(pr), "출력 STL 파일"),
                 ("%d개" % n_print, "출력할 부품 수"), ("1254 × %s" % f(fg["depth"]), "전체 mm (L2 뒷바)"),
                 ("z%s · %s°" % (f(fg["top"]), f(fg["angle"], 1)), "스피커 윗면 · 앞판 각도"),
                 ("%d" % kinds.get("electronics", 0), "전자 부품 외곽"), ("%d" % kinds.get("plywood", 0), "오꾸메 합판 조각")]:
        a('<div class="kf"><b>%s</b><span>%s</span></div>' % (esc(b), esc(s)))
    a('</div>')
    a('<div class="cadv"><div class="cad-main">')
    a('<div class="cad-bar"><span class="lbl">보기</span><div class="seg" role="group" aria-label="보기">'
      '<button type="button" data-preset="all" aria-pressed="true">전체</button>'
      '<button type="button" data-preset="front" aria-pressed="false">정면</button>'
      '<button type="button" data-preset="back" aria-pressed="false">뒤 왼쪽</button>'
      '<button type="button" data-preset="module" aria-pressed="false">모듈 O4</button>'
      '<button type="button" data-preset="section" aria-pressed="false">백건 D 단면</button>'
      '<button type="button" data-preset="pod" aria-pressed="false">스피커 단면</button>'
      '<button type="button" data-preset="rear" aria-pressed="false">뒷바 속 (뚜껑 뗌)</button>'
      '<button type="button" data-preset="touch" aria-pressed="false">터치스크린</button></div>'
      '<button type="button" class="cadchip" id="cadDims" aria-pressed="false">치수 표시</button></div>')
    a('<div class="cad-bar"><span class="lbl">종류</span><div class="chips">')
    for k, c in [("print", "#9aa3ad"), ("bought", "#c0c6cc"), ("plywood", "#d9b98b"), ("electronics", "#2f7d4f"), ("consumable", "#b0413e")]:
        a('<button type="button" class="cadchip" data-kind="%s" aria-pressed="true"><i style="background:%s"></i>%s <span class="mono">%d</span></button>'
          % (k, c, KIND[k], kinds.get(k, 0)))
    a('</div></div>')
    a('<div class="stage"><canvas aria-label="Toccata 전체 조립 3D"></canvas><svg class="dims" aria-hidden="true"></svg>'
      '<div class="load">CAD 탭을 열면 3D 모델(약 5 MB)을 불러옵니다.</div>'
      '<div class="hint">끌기 = 돌리기 · 오른쪽 끌기/두 손가락 = 옮기기 · 휠 = 확대 · 누르기 = 부품 정보</div>'
      '<div class="axes">x 가로 · y 깊이 · z 높이 (mm)</div></div>')
    a('<div class="secbar"><label><input type="checkbox" id="cadSecOn"> 단면 (x보다 오른쪽을 잘라냄)</label>'
      '<input type="range" id="cadSec" min="-16" max="1238" step="0.25" value="%s" aria-label="단면 x 위치"><output id="cadSecOut">끔</output></div>'
      % data["section_x"])
    a('</div><div class="side"><div class="info"><p class="empty">부품을 누르면 이름·크기·출력 파일이 여기에 나옵니다.</p></div>')
    a('<details class="grp" open><summary>그룹 (%d)</summary><div class="gtools"><button type="button" data-gall>모두 보기</button>'
      '<button type="button" data-gnone>모두 숨기기</button><button type="button" data-gshow>숨긴 부품 다시</button></div>'
      '<div class="glist"></div></details></div></div>' % len(groups))

    # print list
    a('<h3>출력 목록 (%d종 · %d개)</h3>' % (len(pr), n_print))
    a('<p class="small muted">파일은 <code>hardware/mechanical/cad/stl/print/</code>에 있습니다. 파일 이름 끝이 출력 개수이고, 부품은 이미 베드 위 방향으로 놓여 있습니다. '
      '같은 이름으로 <code>stl/annotated/</code>에 치수선과 숫자를 붙인 보기용 STL이 있습니다(출력 금지). 질량은 속을 꽉 채운 PETG 기준입니다.</p>')
    by = collections.OrderedDict()
    for r in pr:
        by.setdefault(r["folder"], []).append(r)
    for folder, rs in by.items():
        a('<h4 class="sub4">%s</h4><div class="tbl ptbl"><table><thead><tr><th>파일</th><th class="r">개수</th><th>크기 (베드 위)</th>'
          '<th class="r">g</th><th>재료</th></tr></thead><tbody>' % esc(folder))
        notes = collections.OrderedDict()
        for r in rs:
            a('<tr><td>%s</td><td class="num">%d</td><td class="num">%s</td><td class="num">%.1f</td><td>%s</td></tr>'
              % (esc(os.path.basename(r["file"])), r["qty"], " × ".join("%.1f" % v for v in r["size_mm"]),
                 r["mass_g_solid_petg"], esc(r["material"])))
            if r["note"]:
                notes.setdefault(r["note"], []).append(os.path.basename(r["file"]).split("__")[0])
        a('</tbody></table></div>')
        if notes:
            a('<details class="spec"><summary>출력 방향·후가공</summary><ul class="small">')
            for n, fs in notes.items():
                a('<li><b>%s</b>: %s</li>' % (esc(", ".join(fs[:6]) + (" 외 %d" % (len(fs) - 6) if len(fs) > 6 else "")), esc(n)))
            a('</ul></details>')
    # adjustments
    a('<h3>설계 모델에서 CAD로 옮기며 고친 점</h3>')
    a('<div class="tbl adj"><table><thead><tr><th>번호</th><th>어디</th><th>무엇을 왜</th></tr></thead><tbody>')
    for (i, w, t) in make_readme.ADJUSTMENTS:
        a('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (esc(i), esc(w), esc(t)))
    a('</tbody></table></div>')
    dev = make_readme.deviations(man) + make_readme.extra_deviations(man)
    a('<h3>L2 사양(body_L2.json)과 다르게 만든 곳 (%d)</h3>' % len(dev))
    a('<p class="small muted">사양 수치가 실제 모양에서 맞지 않는 곳만 가장 작게 고쳤습니다. 부품 메모에도 같은 내용이 있습니다.</p><ul class="small">')
    for (names, txt) in dev:
        a('<li><b>%s</b> — %s</li>' % (esc(names), esc(txt)))
    a('</ul>')
    est = make_readme.grouped_notes(man, "추정")
    a('<h3>문서에 치수가 없어 정한 값 (%d)</h3>' % len(est))
    a('<p class="small muted">받은 부품을 재 보고 맞지 않으면 <code>spec/*.json</code>이나 생성기의 값을 바꾼 뒤 다시 만듭니다.</p><ul class="small">')
    for (name, txt, cnt, nvar) in est:
        a('<li><b>%s</b> — %s%s</li>' % (esc(name), esc(txt), esc(" (같은 부품 %d개, 자리만 다름)" % cnt) if nvar > 1 else ""))
    a('</ul>')
    a('<h3>파일</h3><div class="tbl files"><table><tbody>')
    for k, v in [("stl/print/", "출력용 STL (폴더 01~07; 04b는 PORON 5T를 쓸 때 04 대신, 07은 터치스크린 3판)"), ("stl/annotated/", "치수를 붙인 보기용 STL (08_합판재단은 합판 조각)"),
                 ("stl/assembly/", "그룹별 조립 STL과 Toccata_전체조립.stl"), ("Toccata_전체조립.3mf / .glb", "색·이름이 붙은 전체 조립"),
                 ("manifest.json", "부품마다 id·이름·종류·그룹·외곽·출력 파일"), ("spec/", "문서에서 뽑은 세부 사양(출처 포함)"),
                 ("viewer/", "이 탭의 원본 (gen_viewer.py가 만듦)"),
                 ("src/", "생성기 (build_all.py 한 번으로 STL·manifest·README·이 탭 데이터까지; keyaction*.py, body.py (L2), electronics.py; "
                          "L1은 body_L1.py·electronics_L1.py로 보관)")]:
        a('<tr><td><code>hardware/mechanical/cad/%s</code></td><td>%s</td></tr>' % (esc(k), esc(v)))
    a('</tbody></table></div>')
    a('</section>')
    open(os.path.join(HERE, "cad.html"), "w").write("\n".join(H) + "\n")
    print("parts", len(rows), "groups", len(groups), "print", len(pr), "json bytes", os.path.getsize(os.path.join(HERE, "parts.json")))



if __name__ == "__main__":
    main()
