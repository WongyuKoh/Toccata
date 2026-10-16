#!/usr/bin/env python3
"""Tab '06 부품·사용처' (#p-parts): writes section.html + assets.txt next to this file.

    python3 hardware/mechanical/cad/src/locate.py                       # first: fin/loc/ (base frames, overlays, details)
    python3 docs/report/toccata-v4/src/tabs/parts/build_section.py      # then: this tab's static HTML

Inputs (read only): data/final_items.json (the final item list), fin/loc/overlays.json (CAD locations, written by locate.py),
fin/circuit/bom.csv (schematic sheet of each reference), fin/prep/lines.json (prep line ids, optional).
Writes fin/loc/cards.json (card text: item list fields + CAD location notes + schematic sheets + prep line ids). section.html holds
one empty anchor per card (id parts-<key>) so deep links (#parts-i014, #parts-p-KEY-C, #parts-ply-pod-side) work with the page
router; script.js fills the cards from cards.json and draws the location figures (overlays.json) when a card scrolls into view.
"""
import collections
import csv
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ITEMS = os.path.join(PAGE, "data", "final_items.json")
OV = os.path.join(PAGE, "fin", "loc", "overlays.json")
BOM = os.path.join(PAGE, "fin", "circuit", "bom.csv")
PREP = os.path.join(PAGE, "fin", "prep", "lines.json")

SRC_KO = collections.OrderedDict([("school", "학교"), ("personal", "사비"), ("owned", "가진 것"),
                                  ("tool", "공구"), ("gap", "준비처 없음")])
SRC_LONG = {"school": "학교 지원 구매", "personal": "사비 구매", "owned": "가진 것",
            "tool": "가진 공구", "gap": "아직 준비처 없음"}
FOLD_KO = {"01_건반": "01 건반", "02_레버캐리어": "02 레버 캐리어", "03_프레임": "03 프레임", "04_센서바·패드바·가림판·마개": "04 센서 바·패드 바·가림판·마개",
           "05_본체출력물": "05 본체 출력물", "07_터치스크린": "07 터치스크린", "06_출력공구": "06 출력 공구", "08_합판지그": "08 합판 지그",
           "09_기판지그": "09 기판 지그"}


def e(s):
    return html.escape("" if s is None else str(s), quote=True)


def won(v):
    return "{:,}".format(int(round(v)))


def fnum(v, nd=2):
    s = ("%." + str(nd) + "f") % v
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def qty_txt(v):
    return fnum(v, 2) if isinstance(v, float) and not float(v).is_integer() else str(int(v))


def sch_map():
    m = {}
    if not os.path.exists(BOM):
        return m
    with open(BOM, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m.setdefault(r["부품"].strip(), r["도면"].strip())
    return m


W_SHEET = {"1": "SCH-02", "2": "SCH-01", "4": "SCH-04", "5": "SCH-05", "6": "SCH-06", "7": "SCH-07"}


def sheets_of(refs, SM):
    out = []
    for r in refs or []:
        parts = r.replace("×", " ").split()
        ref = parts[1] if len(parts) > 1 and not parts[0].startswith("W") else parts[0]
        sh = SM.get(ref)
        if not sh and ref.startswith("W"):
            sh = W_SHEET.get(ref[1:2])
        if not sh:
            m = re.match(r"[A-Z]+(\d)", ref)
            if m and ref[0] in "CRUJAX":
                sh = {"2": "SCH-02", "3": "SCH-03", "4": "SCH-04", "5": "SCH-05", "6": "SCH-06", "7": "SCH-07"}.get(m.group(1))
        if sh and sh not in out:
            out.append(sh)
    return out


def dropped_map(d):
    """dropped item id -> kept item (final_items.json 'dropped' whose replaced_by is in the kept list), e.g. i068 -> i062."""
    kept = {it["id"] for it in d.get("items", [])}
    return {x["id"]: x["replaced_by"] for x in d.get("dropped", []) if x.get("replaced_by") in kept}


def map_ids(text, repl):
    """CAD print notes (manifest.json) still name a few item ids the final list merged into another item."""
    if not text or not repl:
        return text
    return re.sub(r"\b(" + "|".join(map(re.escape, repl)) + r")\b", lambda m: repl[m.group(1)], text)


def prep_lines():
    if not os.path.exists(PREP):
        return set(), {}
    d = json.load(open(PREP, encoding="utf-8"))
    ids = set(l["id"] for l in d.get("lines", []))
    by_file = {}
    for l in d.get("lines", []):
        if l["id"].startswith("b-") and l.get("file"):
            by_file[(l.get("fold") or "", l["file"])] = l["id"]
    return ids, by_file


# ------------------------------------------------------------------ records for cards.json


def where_print(rec):
    xr = rec.get("xrule")
    r = rec.get("rep") or {}
    b = r.get("bb") or [0] * 6
    ids = rec.get("ids") or []
    mods = sorted(set(m.group(1) for m in (re.match(r"(O\d|EL|ER)-", i) for i in ids) if m))
    s = []
    if xr and xr.get("per_module") and len(xr["modules"]) == 7:
        s.append("모듈 O1~O7에 %d개씩" % xr["per_module"])
        if "EL" in mods or "ER" in mods:
            s.append("+ 끝 부속 %s" % "·".join(m for m in mods if m in ("EL", "ER")))
    elif len(ids) <= 6:
        s.append(", ".join(ids))
    else:
        s.append("%d곳" % len(ids))
    s.append("대표 %s: x %s~%s · y %s~%s · z %s~%s" % (r.get("id", ""), fnum(b[0]), fnum(b[3]), fnum(b[1]), fnum(b[4]), fnum(b[2]), fnum(b[5])))
    if xr:
        s.append(xr["text"])
    return " · ".join(s)


def frames_of(rec):
    if not rec:
        return []
    return [f for f in ("plan", "side", "front") if f in (rec.get("frames") or {}) or f in (rec.get("host_frames") or {})]


def item_rec(it, rec, SM, prep_ids, issues):
    iid = it["id"]
    src = it["source"]
    o = it.get("ordered")
    ordered = ""
    if o:
        ordered = "주문 수량 %s%s · %s원 · %s" % (qty_txt(o["qty"]), "" if not o.get("units") or o["units"] == o["qty"] else " (%s개 들이)" % o["units"],
                                             won(o["amount"]), o["store"])
    c = dict(key=iid, g="item", src=src, cat=it["cat"], role=it["role"], opt=bool(it.get("optional")), name=it["name"],
             full=it.get("full_name") or "", code=it.get("code") or "", qty=qty_txt(it["qty_need"]), unit=it.get("unit") or "",
             pack=it.get("pack_note") or "", ord=ordered, where=it.get("where") or "", img=it.get("img") or "")
    if rec and rec.get("where_note") and rec["where_note"] not in c["where"]:
        c["wnote"] = rec["where_note"]
    if issues.get(iid):
        c["issues"] = issues[iid]
    has_fig = bool(frames_of(rec))
    if has_fig:
        c["fr"] = frames_of(rec)
        cn = [rec.get("count_note") or ""]
        if rec.get("xrule"):
            cn.append("모듈 자리: %s (k = 모듈 번호)" % rec["xrule"]["text"])
        if rec.get("count_derived"):
            cn.append("모델에 없는 부품이라 CAD를 만든 같은 수치로 자리를 계산했습니다")
        c["cnt"] = " · ".join(x for x in cn if x)
        if rec.get("detail"):
            c["det"] = rec["detail"]
            c["rep"] = (rec.get("rep") or {}).get("name") or ""
    else:
        why = {"tool": "만들 때만 쓰는 공구라 악기 안에 자리가 없습니다.", "시험용": "책상 시험 때만 쓰고 악기에 넣지 않습니다."}
        t = why.get(src) or why.get(it["role"]) or "자리 그림이 없는 재료입니다."
        if iid == "i090":
            t = "단계 0 시편·출력 공구·재출력에 쓰는 여유 필라멘트라 악기 안에 정해진 자리가 없습니다."
        c["nofig"] = t
    sheets = sheets_of(it.get("sch_refs"), SM)
    if sheets:
        c["sch"] = sheets
    p = next((p for p in ("a-" + iid, "d-" + iid) if p in prep_ids), None)
    if p:
        c["prep"] = p
    st = it.get("store_url") or (o or {}).get("url")
    if st:
        c["store"] = st
    rows = [["필요 수", it.get("need_note") or ""]] + [[a, b] for a, b in it.get("specs") or []]
    for k_, lab in (("ident", "알아보는 법"), ("check_on_arrival", "받으면 확인"), ("replaces", "대신하는 것"), ("img_note", "사진")):
        if it.get(k_):
            rows.append([lab, it[k_]])
    if it.get("sch_refs"):
        rows.append(["회로 기호", ", ".join(it["sch_refs"])])
    if rec and rec.get("rep"):
        r = rec["rep"]
        rows.append(["대표 자리 (CAD)", "%s · 중심 x %s, y %s, z %s" % (r["id"], fnum(r["c"][0]), fnum(r["c"][1]), fnum(r["c"][2]))])
    if rec and rec.get("derived_how"):
        rows.append(["자리 계산", " / ".join(rec["derived_how"][:2])])
    c["specs"] = rows
    return c


def print_rec(key, rec, prep_by_file, repl):
    fold = rec.get("folder") or ""
    fname = os.path.basename(rec.get("file") or "")
    c = dict(key=key, g="print", fold=fold, name=rec["name"], file=rec.get("file") or "", qty=str(rec.get("qty")),
             mat=rec.get("material") or "PETG", size=" × ".join(fnum(v) for v in rec.get("size_mm") or []),
             mass=fnum(rec["mass_g"], 1) if rec.get("mass_g") else "", where=where_print(rec), cnt=rec.get("count_note") or "",
             det=rec.get("detail") or "", rep=(rec.get("rep") or {}).get("name") or "", pd=rec.get("partdwg") or [], fr=frames_of(rec))
    p = prep_by_file.get((fold[:2], fname))
    if p:
        c["prep"] = p
    rows = [["파일", rec.get("file") or ""], ["출력 메모", map_ids(rec.get("note") or "", repl)]]
    if rec.get("volume_cm3") is not None:
        rows.append(["부피", "%s cm³ (속 꽉 채움 질량 %s g)" % (fnum(rec["volume_cm3"], 1), fnum(rec.get("mass_g") or 0, 1))])
    ids = rec.get("ids") or []
    if ids:
        rows.append(["CAD 부품", ", ".join(ids) if len(ids) <= 12 else ", ".join(ids[:12]) + " 외 %d" % (len(ids) - 12)])
    c["specs"] = rows
    return c


def ply_rec(key, rec, prep_ids):
    r = rec.get("rep") or {}
    b = r.get("bb") or [0] * 6
    c = dict(key=key, g="plywood", name=rec["name"], qty=str(rec.get("qty")), size=" × ".join(fnum(v) for v in rec.get("size_mm") or []),
             ids=", ".join(rec.get("ids") or []), cnt=rec.get("count_note") or "", det=rec.get("detail") or "", rep=r.get("name") or "",
             pd=rec.get("partdwg") or [], fr=frames_of(rec),
             where="%s · 대표 %s: x %s~%s · y %s~%s · z %s~%s" % (", ".join(rec.get("ids") or []), r.get("id", ""), fnum(b[0]), fnum(b[3]),
                                                             fnum(b[1]), fnum(b[4]), fnum(b[2]), fnum(b[5])))
    # 07 준비 체크 has one line per plywood piece: c-ply-<CAD id in lower case> (L and R pieces = two lines)
    pl = [p for p in ("c-ply-" + i.lower() for i in rec.get("ids") or []) if p in prep_ids]
    if pl:
        c["prep"] = pl if len(pl) > 1 else pl[0]
    c["specs"] = [["CAD 부품", c["ids"]], ["판", "오꾸메 합판 11.5T 400 × 1200 한 장 (i096)에서 자릅니다. 재단도는 02 설계도의 합판 재단도, 조각 도면은 03 부품 도면에 있습니다."]]
    return c


def orders_html(d, items):
    T = d["totals"]
    by = collections.OrderedDict([("학교 구매", []), ("사비 구매", [])])
    for it in items:
        o = it.get("ordered")
        if o:
            by.setdefault(o["sheet"], []).append((it, o))
    out = []
    sums = {}
    for sheet, rows in by.items():
        rows.sort(key=lambda t: (t[1]["store"], t[0]["id"]))
        tr = []
        stores = collections.OrderedDict()
        for it, o in rows:
            stores.setdefault(o["store"], []).append((it, o))
        tot = 0
        for st, rr in stores.items():
            sub = 0
            for it, o in rr:
                tr.append('<tr><td><a href="#parts-%s">%s</a> <span class="mono small muted">%s</span></td><td>%s</td><td class="r num">%s</td>'
                          '<td class="r num">%s</td><td class="r num">%s</td><td>%s</td></tr>'
                          % (e(it["id"]), e(it["name"]), e(it["id"]), e(st), qty_txt(o["qty"]), won(o["unit_price"]), won(o["amount"]),
                             ('<a href="%s" target="_blank" rel="noopener noreferrer">링크 ↗</a>' % e(o["url"])) if o.get("url") else ""))
                sub += o["amount"]
            tot += sub
            tr.append('<tr class="sub"><td colspan="4">%s 소계</td><td class="r num">%s</td><td></td></tr>' % (e(st), won(sub)))
        sums[sheet] = tot
        out.append((sheet, rows, "".join(tr), tot))
    ship_s = d["shipping"]["school"]
    ship_p = d["shipping"]["personal"]
    s_fee = sum(x["fee"] for x in ship_s)
    p_fee = sum(x["fee"] for x in ship_p)
    assert sums.get("학교 구매", 0) == T["school_items"], (sums, T)
    assert sums.get("사비 구매", 0) == T["personal_items"], (sums, T)
    assert s_fee == T["school_ship"] and p_fee == T["personal_ship"], (s_fee, p_fee, T)
    assert T["school_items"] + T["school_ship"] + T["personal"] == T["total"]
    head = '<thead><tr><th>품목</th><th>판매처</th><th class="r">수량</th><th class="r">단가</th><th class="r">금액</th><th>상품</th></tr></thead>'
    h = []
    h.append('<div class="kfs parts-ordkf">'
             '<div class="kf"><b>%s원</b><span>학교 물건값 %d줄 (한도 %s원, %s)</span></div>'
             '<div class="kf"><b>%s원</b><span>학교 주문 배송비 (학교가 냄, 한도 밖)</span></div>'
             '<div class="kf"><b>%s원</b><span>사비 %d줄 = 물건 %s + 배송비 %s</span></div>'
             '<div class="kf"><b>%s원</b><span>전체 결제 (학교 + 사비)</span></div></div>'
             % (won(T["school_items"]), T["school_lines"], won(T["budget_school"]), ("남은 " + won(T["school_left"])) if T["school_left"] >= 0 else (won(-T["school_left"]) + " 초과"), won(T["school_ship"]),
                won(T["personal"]), T["personal_lines"], won(T["personal_items"]), won(T["personal_ship"]), won(T["total"])))
    for sheet, rows, tr, tot in out:
        extra = ""
        if sheet == "사비 구매":
            extra = "".join('<tr class="sub"><td colspan="4">배송비 · %s%s</td><td class="r num">%s</td><td></td></tr>'
                            % (e(x["store"]), (" (%s)" % e(x["note"])) if x.get("note") else "", won(x["fee"])) for x in ship_p)
            extra += '<tr class="total"><td colspan="4">사비 합계 (물건 %s + 배송비 %s)</td><td class="r num">%s</td><td></td></tr>' % (
                won(T["personal_items"]), won(T["personal_ship"]), won(T["personal"]))
        else:
            extra = '<tr class="total"><td colspan="4">학교 물건값 합계 (%d줄)</td><td class="r num">%s</td><td></td></tr>' % (len(rows), won(tot))
        h.append('<h4 class="parts-h4">%s · %d줄</h4><div class="tbl"><table>%s<tbody>%s%s</tbody></table></div>' % (e(sheet), len(rows), head, tr, extra))
    sh_rows = "".join('<tr><td>%s</td><td class="r num">%s</td><td class="r num">%s</td><td class="small">%s</td></tr>'
                      % (e(x["store"]), won(x["items"]), won(x["fee"]), e(x.get("rule") or "")) for x in ship_s)
    h.append('<h4 class="parts-h4">학교 주문 배송비 (판매자별)</h4><p class="small muted">%s</p><div class="tbl"><table><thead><tr><th>판매자</th>'
             '<th class="r">물건값</th><th class="r">배송비</th><th>규칙</th></tr></thead><tbody>%s<tr class="total"><td>합계</td><td class="r num">%s</td>'
             '<td class="r num">%s</td><td></td></tr></tbody></table></div>' % (e(d["shipping"].get("note") or ""), sh_rows, won(sum(x["items"] for x in ship_s)), won(s_fee)))
    h.append('<p class="small"><b>전체 결제</b> 학교 %s + 학교 배송비 %s + 사비 %s = <b class="num">%s원</b> (구매 목록 xlsx 요약과 같음)</p>'
             % (won(T["school_items"]), won(T["school_ship"]), won(T["personal"]), won(T["total"])))
    return "".join(h)


def main():
    d = json.load(open(ITEMS, encoding="utf-8"))
    ov = json.load(open(OV, encoding="utf-8"))
    SM = sch_map()
    prep_ids, prep_by_file = prep_lines()
    frames = ov["frames"]
    E = ov["entries"]
    items = d["items"]
    repl = dropped_map(d)
    issues = collections.defaultdict(list)
    top_issues = []
    for i in d.get("issues", []):
        if i["id"] in E:
            issues[i["id"]].append((i["level"], i["text"]))
        else:
            top_issues.append(i)
    cnt = collections.Counter(it["source"] for it in items)
    cats = d["cat_order"]
    prints = [(k, r) for k, r in E.items() if r["group"] == "print"]
    plys = [(k, r) for k, r in E.items() if r["group"] == "plywood"]
    n_print_parts = sum(r.get("qty") or 0 for _, r in prints)
    n_ply = sum(r.get("qty") or 0 for _, r in plys)
    T = d["totals"]
    # ---------------- header
    H = []
    H.append('<section class="page" id="p-parts" hidden aria-labelledby="parts-h">')
    H.append('<h2 id="parts-h">06 부품·사용처</h2>')
    H.append('<p class="lede">최종 설계에 들어가는 물건마다 몇 개가 필요하고 악기의 어디에 들어가는지 보여 줍니다. 위치 그림은 CAD 입체(1,467개 부품)를 '
             '위·옆·앞에서 그린 바탕에 그 물건의 모든 자리를 빨갛게 겹친 것이고, 확대 그림은 대표 한 곳을 위에서(그 부품 위는 걷어 냄) 본 그림과 '
             '단면으로 보여 줍니다. 좌표와 크기는 mm이고 모두 CAD 입체에서 계산했습니다.</p>')
    kf = [("%d줄" % cnt["school"], "학교 지원 구매 · 물건값 %s원" % won(T["school_items"])),
          ("%d줄" % cnt["personal"], "사비 구매 · 배송비 포함 %s원" % won(T["personal"])),
          ("%d줄" % cnt["owned"], "가진 것 (부품·소모품)"),
          ("%d줄" % cnt["tool"], "가진 공구"),
          ("%d파일 · %d개" % (len(prints), n_print_parts), "출력물 (01~05, 07)"),
          ("%d조각" % n_ply, "합판 (오꾸메 한 장)")]
    if cnt.get("gap"):
        kf.insert(5, ("%d줄" % cnt["gap"], "아직 준비처 없음"))
    H.append('<div class="kfs" id="parts-kfs">%s</div>' % "".join('<div class="kf"><b>%s</b><span>%s</span></div>' % (e(a), e(b)) for a, b in kf))
    for i in top_issues:
        if i["level"] == "높음":
            H.append('<div class="note warn"><b>먼저 확인</b> %s</div>' % e(i["text"]))
    gap_items = [it for it in items if it["source"] == "gap"]
    for it in gap_items:
        H.append('<div class="note warn"><b>준비처가 없는 물건</b> <a href="#parts-%s">%s</a> — %s</div>'
                 % (e(it["id"]), e(it["name"]), e((issues.get(it["id"]) or [("", it.get("check_on_arrival") or "")])[0][1])))
    H.append('<details class="parts-how"><summary>그림 읽는 법</summary><ul class="flow small">'
             '<li><b>위치 그림</b>: 위(뚜껑 L·R·화면 뚜껑·터치스크린을 뗀 평면), 옆(흰 건반 E4 가운데 x %s 단면 + 악기 윤곽), 앞(y %s 단면 + 윤곽) 중 고릅니다. '
             '빨강은 이 물건이 들어가는 모든 자리를 그 방향으로 투영한 모양이고, 작은 부품은 빨간 고리로 자리를 표시합니다. 주황은 그 물건이 붙는 부품입니다.</li>'
             '<li><b>확대 그림</b>: ①은 대표 한 곳을 위에서 본 그림으로, 그 부품 윗면보다 높은 부품은 걷어 냈습니다. ②는 대표 자리 가운데를 지나는 단면입니다. '
             '파란 숫자는 대표 자리의 중심 좌표와 바깥 크기입니다.</li>'
             '<li><b>좌표</b>: x 가로 (0 = A0 건반 왼쪽 끝), y 흰 건반 앞 끝에서 뒤로, z 책상에서 위로. 모듈 Ok는 x = 47 + 164.5(k-1)에서 시작합니다.</li>'
             '<li><b>자리 계산</b>: 모델에 없는 나사·와셔·홀센서·흡음솜 자리는 CAD를 만든 같은 수치(body.py의 나사 표, 앰프 구멍, 받침 기둥, 그릴·유닛 나사 자리, 센서 줄 y67)로 그렸습니다.</li>'
             '<li><b>모양이 없는 재료</b>(접착제·납·펠트 원단·필라멘트 등)는 쓰는 부품을 주황으로 표시합니다.</li></ul></details>'
             % (e(frames["side"]["cut"].split(" ")[2]), e(frames["front"]["cut"].split(" ")[2])))
    # ---------------- filter bar
    src_btn = '<button type="button" data-src="" aria-pressed="true">전체 <span class="num">%d</span></button>' % len(items) + "".join(
        '<button type="button" data-src="%s" aria-pressed="false">%s <span class="num">%d</span></button>' % (s, e(SRC_KO[s]), cnt[s])
        for s in SRC_KO if cnt.get(s))
    cat_opt = '<option value="">전체 묶음</option>' + "".join('<option value="%s">%s</option>' % (e(c), e(c)) for c in cats)
    folds = sorted(set(r.get("folder") for _, r in prints))
    fold_opt = '<option value="">전체 폴더</option>' + "".join('<option value="%s">%s</option>' % (e(f), e(FOLD_KO.get(f, f))) for f in folds)
    H.append('<div class="parts-bar" role="search" aria-label="부품 거르기">'
             '<div class="seg parts-mode" role="group" aria-label="목록"><button type="button" data-m="item" aria-pressed="true">물건 <span class="num">%d</span></button>'
             '<button type="button" data-m="print" aria-pressed="false">출력물 <span class="num">%d</span></button>'
             '<button type="button" data-m="plywood" aria-pressed="false">합판 <span class="num">%d</span></button></div>'
             '<div class="parts-srcs" role="group" aria-label="준비처">%s</div>'
             '<label class="parts-sel"><span class="small muted">묶음</span><select id="parts-cat">%s</select></label>'
             '<label class="parts-sel" hidden><span class="small muted">폴더</span><select id="parts-fold">%s</select></label>'
             '<label class="parts-q"><span class="sr-only">찾기</span><input type="search" id="parts-q" placeholder="이름·코드·쓰는 곳 찾기" autocomplete="off"></label>'
             '<output id="parts-count" class="small muted" aria-live="polite"></output></div>'
             % (len(items), len(prints), len(plys), src_btn, cat_opt, fold_opt))
    H.append('<p class="parts-status small muted" id="parts-status" role="status" aria-live="polite"></p>')
    # ---------------- cards: anchors only (script.js renders them from fin/loc/cards.json)
    order = {c: i for i, c in enumerate(cats)}
    cards = []
    for it in sorted(items, key=lambda it: (order.get(it["cat"], 99), list(SRC_KO).index(it["source"]), it["id"])):
        cards.append(item_rec(it, E.get(it["id"]), SM, prep_ids, issues))
    for k, r in prints:
        cards.append(print_rec(k, r, prep_by_file, repl))
    for k, r in plys:
        cards.append(ply_rec(k, r, prep_ids))
    H.append('<div class="parts-list" id="parts-list">')
    for c in cards:
        H.append('<div class="pc pc-wait" id="parts-%s" data-g="%s" data-k="%s"%s%s%s><p class="small muted">%s</p></div>'
                 % (e(c["key"]), c["g"], e(c["key"]), (' data-src="%s"' % c["src"]) if c.get("src") else "",
                    (' data-cat="%s"' % e(c["cat"])) if c.get("cat") else "", (' data-fold="%s"' % e(c["fold"])) if c.get("fold") else "",
                    e(c["name"])))
    H.append('</div>')
    H.append('<p class="parts-empty small muted" id="parts-empty" hidden>조건에 맞는 줄이 없습니다.</p>')
    with open(os.path.join(PAGE, "fin", "loc", "cards.json"), "w", encoding="utf-8") as f:
        json.dump(dict(version=1, generated=d.get("generated"), frames=frames, src_ko=SRC_KO, src_long=SRC_LONG, fold_ko=FOLD_KO,
                       totals=T, cards=cards), f, ensure_ascii=False, separators=(",", ":"))
    # ---------------- tools / jigs (print)
    tools = ov.get("tools") or []
    if tools:
        rows = "".join('<tr><td>%s</td><td>%s</td><td class="r num">%s</td><td class="num">%s</td><td>%s</td></tr>'
                       % (e(t["name"]), e(FOLD_KO.get(t["folder"], t["folder"])), e(t["qty"]), " × ".join(fnum(v) for v in t["size_mm"]),
                          ('<a href="#partdwg-%s">%s</a>' % (e(t["partdwg"]), e(t["partdwg"]))) if t.get("partdwg") else "")
                       for t in tools)
        H.append('<details class="parts-more" id="parts-tools"><summary>출력 공구·지그 %d파일 (악기에 남지 않음)</summary>'
                 '<p class="small muted">벤치 지그·게이지(06), 합판 드릴 지그(08), 만능기판 지그(09)입니다. 악기 안에 자리가 없어 위치 그림이 없습니다.</p>'
                 '<div class="tbl"><table><thead><tr><th>이름</th><th>폴더</th><th class="r">개수</th><th>크기 (mm)</th><th>부품 도면</th></tr></thead>'
                 '<tbody>%s</tbody></table></div></details>' % (len(tools), rows))
    # ---------------- dropped
    rows = "".join('<tr><td><span class="mono small">%s</span> %s</td><td>%s</td><td>%s</td></tr>'
                   % (e(x["id"]), e(x["name"]), e(x["reason"]),
                      ('<a href="#parts-%s">%s</a>' % (e(x["replaced_by"]), e(x["replaced_by"]))) if x.get("replaced_by") else "")
                   for x in d.get("dropped", []))
    H.append('<details class="parts-more" id="parts-dropped"><summary>빠진 물건 %d줄 (사지 않음)</summary>'
             '<p class="small muted">예전 목록에 있었지만 최종 설계에서 쓰지 않는 물건입니다. 잘못 사지 않도록 이유와 대신 쓰는 것을 적었습니다.</p>'
             '<div class="tbl"><table><thead><tr><th>물건</th><th>빠진 이유</th><th>대신</th></tr></thead><tbody>%s</tbody></table></div>'
             % (len(d.get("dropped", [])), rows))
    sw = d.get("software") or []
    if sw:
        H.append('<p class="small"><b>소프트웨어</b> (물건이 아님, 무료 내려받기): %s</p>' % ", ".join(e(x["name"]) for x in sw))
    H.append('</details>')
    # ---------------- purchase record
    H.append('<details class="parts-more" id="parts-orders"><summary>구매 기록 — 학교 %d줄 · 사비 %d줄 · 전체 %s원</summary>%s</details>'
             % (T["school_lines"], T["personal_lines"], won(T["total"]), orders_html(d, items)))
    H.append('<p class="small muted parts-src">원본: data/final_items.json (최종 재료 목록, %s) · fin/loc/overlays.json (hardware/mechanical/cad/src/locate.py, CAD %s) · '
             '구매 기록은 최종본/01_구매목록/Toccata_학교_사비_구매목록_2026-10-08.xlsx와 같습니다.</p>' % (e(d.get("generated")), e(ov.get("generated"))))
    H.append('</section>')
    html_ = "\n".join(H)
    with open(os.path.join(HERE, "section.html"), "w", encoding="utf-8") as f:
        f.write(html_ + "\n")
    # ---------------- assets
    A = ["fin/loc/cards.json", "fin/loc/overlays.json", "fin/loc/base_plan.svg", "fin/loc/base_side.svg", "fin/loc/base_front.svg"]
    for k, r in E.items():
        if r.get("detail"):
            A.append(r["detail"])
    for it in items:
        if it.get("img"):
            A.append(it["img"])
    seen, AA = set(), []
    for a in A:
        if a not in seen and os.path.exists(os.path.join(PAGE, a)):
            seen.add(a)
            AA.append(a)
        elif a not in seen:
            print("missing asset:", a, file=sys.stderr)
    with open(os.path.join(HERE, "assets.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(AA) + "\n")
    print("section.html %d bytes, cards.json %d bytes, %d cards (%d items, %d prints, %d plywood), %d assets"
          % (len(html_.encode()), os.path.getsize(os.path.join(PAGE, "fin", "loc", "cards.json")), len(cards), len(items), len(prints), len(plys), len(AA)))


if __name__ == "__main__":
    main()
