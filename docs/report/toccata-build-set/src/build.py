"""Assemble the Toccata build report (single HTML + img/)."""
import copy, json, math, os, re, html as H
from model import L, METHODS, KEYS, TAILS, hammer_parts
from draw import fmt_mm
from field import Bz
import dw_side, dw_plan, dw_parts, dw_elec, calc
from content import METHOD_TEXT, REQ_MAP, ASSUMPTIONS, ASSEMBLY

S = "/private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/3546328f-6f85-459b-b398-b7404472305f/scratchpad"
RES = f"{S}/research"
OUT = f"{S}/report"
A, B, C, D = METHODS
MID = ["A", "B", "C", "D"]
MBY = {m["id"]: m for m in METHODS}


def esc(s):
    return H.escape(str(s), quote=True)


def won(v):
    return f"{int(round(v)):,}원"


def load(name):
    p = f"{RES}/{name}.json"
    if os.path.exists(p):
        with open(p) as fh:
            return json.load(fh)
    return {}


ELEC = load("electronics")
AUD = load("audio")
PED = load("pedals")
MECH = load("mechanical")
DIMS = load("dimensions")


def items_of(src):
    if isinstance(src, list):
        return src
    return src.get("items", [])


ITEMS = {}
for src in (ELEC, AUD, PED, MECH):
    for it in items_of(src):
        if isinstance(it, dict) and it.get("id"):
            ITEMS[it["id"]] = it
EXTRA = load("extra")          # manual additions / overrides (same schema)
for it in items_of(EXTRA):
    ITEMS[it["id"]] = {**ITEMS.get(it["id"], {}), **it}


def parse_pack(p):
    import re
    if isinstance(p, (int, float)):
        return max(1.0, float(p))
    if not p:
        return 1.0
    s = str(p)
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(개|m|kg|장|본|세트|봉|롤)?", s)
    if not m:
        return 1.0
    n, unit = float(m.group(1)), m.group(2) or ""
    if unit in ("개", "m", "장", "세트", "봉", "롤") or unit == "":
        return max(1.0, n) if unit in ("개", "m", "") else 1.0
    return 1.0


def priced_offers(it):
    return [o for o in it.get("offers", []) if isinstance(o, dict) and isinstance(o.get("price_krw"), (int, float))]


def best_offer(it, idx=0):
    offs = priced_offers(it)
    if not offs:
        return None
    return offs[min(idx, len(offs) - 1)]


def unit_price(it, idx=0):
    o = best_offer(it, idx)
    if not o:
        return None, 1
    return float(o["price_krw"]), parse_pack(o.get("pack_qty"))


# ------------------------------------------------------------------ BOM definition
# (id, category, {method: qty in "units needed"}, note)   qty is converted to purchase packs
CAT = {"elec": "전자·배선", "audio": "소리", "pedal": "페달·조작부", "print": "3D 출력 재료", "mech": "방식별 기구 부품", "case": "케이스·공통 하드웨어"}
CAT_ORDER = ["elec", "audio", "pedal", "print", "mech", "case"]


def allm(q):
    return {m: q for m in MID}


def basis_note(ref, key, word, rel=False):
    """caption note for a sheet drawn with method `ref`: '방식 B·D 기준, A는 깊이 +4, C는 깊이 +124' (from the model)."""
    same = "·".join(M["id"] for M in METHODS if M[key] == ref[key])
    val = lambda M: (("+" if M[key] > ref[key] else "") + fmt_mm(M[key] - ref[key])) if rel else fmt_mm(M[key])
    diff = ", ".join(f"{M['id']}는 {word} {val(M)}" for M in METHODS if M[key] != ref[key])
    return f"방식 {same} 기준" + (f", {diff}" if diff else "")


PIN3 = "m-pin3"          # researched guide pin offer (Ø3 x 30, price verified)


def _len_of(it):
    m = re.search(r"×\s*(\d+(?:\.\d+)?)\s*mm", str((it.get("specs") or {}).get("치수", "")))
    return float(m.group(1)) if m else None


def pin3_id(length):
    """item id for a Ø3 guide pin of `length`: the researched offer when the length matches, otherwise a
    same-series item with no price (so it shows as '가격 확인 필요' and is listed as missing, never guessed)."""
    base = ITEMS.get(PIN3)
    b = _len_of(base) if base else None
    if base is None or b is None or abs(b - length) < 1e-6:
        return PIN3
    n, bs = fmt_mm(length), fmt_mm(b)
    pid = f"{PIN3}-{n}"
    if pid not in ITEMS:
        it = copy.deepcopy(base)
        specs = {k: v for k, v in (it.get("specs") or {}).items() if "단가" not in k}
        specs["치수"] = f"Ø{fmt_mm(L['pin_d'])} × {n} mm"
        specs["가격"] = f"{n} mm 품번 가격 확인 필요 ({bs} mm 품번만 확인함)"
        offers = [dict(store=o.get("store", "구매처"), url=o["url"].split("?")[0],
                       price_note=f"{n} mm 품번 가격 확인 필요") for o in base.get("offers", []) if isinstance(o, dict) and o.get("url")]
        it.update(id=pid, name_ko=f"Ø{fmt_mm(L['pin_d'])}×{n} 평행핀 (키 가이드핀)",
                  model=re.sub(rf"-{bs}\b", f"-{n}", base.get("model", "")) + f" — 같은 계열 {n} mm 품번, 가격 확인 필요",
                  specs=specs, offers=offers, alternatives=[],
                  used_by=[M["id"] for M in METHODS if abs(M["pin_len"] - length) < 1e-6],
                  notes_ko=f"건반이 높아 가이드 핀이 {n} mm 필요합니다({bs} mm 품번은 다른 방식용). "
                           f"{n} mm 품번의 가격을 확인하지 못해 합계에 넣지 않았습니다.")
        ITEMS[pid] = it
    return pid


def pin3_lines(hq):
    """guide pin BOM lines, one per pin length (calc.hw_qty: A-C Ø3x30, D Ø3x40)."""
    out = []
    for ln in sorted({hq[m]["pin3_len"] for m in MID}):
        pid = pin3_id(ln)
        note = f"가이드 핀 Ø{fmt_mm(L['pin_d'])}×{fmt_mm(ln)}"      # an unpriced length already shows '가격 확인 필요'
        out.append((pid, "mech", {m: (hq[m]["pin3"] if hq[m]["pin3_len"] == ln else 0) for m in MID}, note, {}))
    return out


def dowel_offer(bp, pid="m-dowel4"):
    """index (into priced offers) of the balance-pin pack whose catalog code matches the model pin, e.g. '-D4-40'."""
    offs = priced_offers(ITEMS.get(pid, {}))
    code = f"-D{fmt_mm(bp['d'])}-{fmt_mm(bp['len'])}"
    idx = next((i for i, o in enumerate(offs) if str(o.get("url", "")).endswith(code)), None)
    assert idx is not None or not offs, f"no {pid} offer for balance pin {code}"
    return idx or 0


def bom_lines():
    """(id, category, {method: qty}, note, opts) — qty in the offer's selling unit (개, m, kg ...)."""
    pp = {m: calc.print_plan(MBY[m]) for m in MID}
    hq = {m: calc.hw_qty(MBY[m]) for m in MID}
    ply = {m: calc.plywood_cost(MBY[m])[1] for m in MID}
    shaft_m = lambda n: 2 if n else 0                      # 8 x L['shaft_len'] (163) mm + kerf -> 2 m of 1 m bar
    n_sh = lambda key: max(hq[m][key] for m in MID)        # shafts per method that uses them (calc.hw_qty)
    shaft_note = lambda key: f"m, {fmt_mm(L['shaft_len'])} mm × {n_sh(key)} 절단"
    bp = C["bal_pin"]                                      # catalog balance pin (model.method_C)
    L_ = [
        ("e-hall", "elec", allm(100), "88 + 여분 12", {}),
        ("e-magnet", "elec", allm(100), "88 + 여분 12", {}),
        ("e-mux", "elec", allm(8), "건반 모듈 7 + 여분 1", {}),
        ("e-pico", "elec", allm(9), "건반 7 + 페달 1 + 여분 1", {}),
        ("e-perf", "elec", allm(9), "모듈마다 1장 + 여분", {}),
        ("e-header", "elec", allm(20), "피코·MUX 소켓", {}),
        ("e-cap", "elec", allm(110), "센서당 100 nF + 여분", {}),
        ("e-cap10u", "elec", allm(20), "모듈 전원 안정", {}),
        ("e-res", "elec", allm(1), "페달 풀업·LED", {}),
        ("e-wire-sil", "elec", allm(1), "신호선", {}),
        ("e-wire-bus", "elec", allm(1), "센서 레일 버스", {}),
        ("e-jst", "elec", allm(1), "레일↔모듈 커넥터", {}),
        ("e-dupont", "elec", allm(3), "시험·디버깅", {}),
        ("e-usbcable", "elec", allm(9), "피코 → 허브", {}),
        ("e-hub", "elec", allm(1), "10포트", {}),
        ("t-solder", "elec", allm(1), "", {}),
        ("t-flux", "elec", allm(1), "", {}),
        ("t-wick", "elec", allm(1), "", {}),
        ("t-heatshrink", "elec", allm(1), "", {}),
        ("t-ties", "elec", allm(2), "", {}),
        ("t-standoff", "elec", allm(4), "보드 고정", {}),
        ("m-petg-white", "print", {m: math.ceil(pp[m]["white"] / 1000) for m in MID}, "kg", {}),
        ("m-petg-black", "print", {m: math.ceil(pp[m]["black"] / 1000) for m in MID}, "kg", {}),
        ("m-pla", "print", {m: math.ceil(pp[m]["other"] / 1000) for m in MID}, "kg, 프레임·레일", {}),
        *pin3_lines(hq),
        ("m-spring-spec", "mech", {m: hq[m]["springs"] for m in MID}, "C-UR6-25", {}),
        ("m-setscrew", "mech", {m: hq[m]["setscrew"] for m in MID}, "스프링 예압 조절", {}),
        ("m-shaft4", "mech", {m: shaft_m(hq[m]["shaft4"]) for m in MID}, shaft_note("shaft4"), {"fee": {m: 4000 if hq[m]["shaft4"] else 0 for m in MID}}),
        ("m-shaft3", "mech", {m: shaft_m(hq[m]["shaft3"]) for m in MID}, shaft_note("shaft3"), {"fee": {m: 4000 if hq[m]["shaft3"] else 0 for m in MID}}),
        ("m-dowel4", "mech", {m: hq[m]["dowel4"] for m in MID}, f"Ø{fmt_mm(bp['d'])}×{fmt_mm(bp['len'])} 밸런스 핀",
         {"offer": dowel_offer(bp)}),
        ("m-flat925", "mech", {m: round(hq[m]["flat925_m"], 2) for m in MID}, "m, 직접 절단", {}),
        ("m-flat616", "mech", {m: round(hq[m]["flat616_m"], 2) for m in MID}, "m, 직접 절단 (19×6)", {}),
        ("m-screws", "mech", {"A": 0, "B": 0, "C": 1, "D": 1}, "M3 볼트 1000개", {}),
        ("m-felt3", "case", {"A": 1, "B": 1, "C": 2, "D": 1}, "하한·상한·패드", {}),
        ("m-plywood", "case", allm(1), "재단표 전체", {"cost": ply}),
        ("m-woodscrew", "case", allm(1), "레일·케이스 고정", {}),
        ("m-glue", "case", allm(1), "", {"offer": 1}),
        ("m-insert", "case", {m: hq[m]["inserts"] for m in MID}, "M3 인서트", {}),
        ("m-lube", "case", allm(1), "PTFE 건식 윤활", {}),
    ]
    topo = next((t for t in AUD.get("topologies", []) if t.get("recommended")), None)
    skip_audio = {"a-buck", "a-mount"}
    if topo:
        for pid in topo.get("parts", []):
            pid = pid if isinstance(pid, str) else pid.get("id")
            if pid not in ITEMS or pid in skip_audio:
                continue
            L_.append((pid, "audio", allm(qty_num(ITEMS[pid].get("qty_suggest"), pid)), "", {}))
    L_.append(("s-pianoteq", "audio", allm(1), "하프 페달 지원 음원", {}))
    cfg = next((c for c in PED.get("configs", []) if c.get("recommended")), None)
    if cfg:
        for p in cfg.get("parts", []):
            pid, qn = (p.get("id"), p.get("qty", 1)) if isinstance(p, dict) else (p, 1)
            if pid in ITEMS and priced_offers(ITEMS[pid]):
                L_.append((pid, "pedal", allm(qn), "", {}))
    for pid in ("c-encoder", "c-knob", "c-powerbtn"):
        if pid in ITEMS:
            L_.append((pid, "pedal", allm(1), "", {}))
    return L_


def qty_num(q, pid=""):
    if isinstance(q, (int, float)):
        return q
    if isinstance(q, dict):
        return q.get("qty") or q.get("n") or 1
    if isinstance(q, str):
        import re
        m = re.match(r"\s*(\d+(?:\.\d+)?)", q)
        if m:
            return float(m.group(1))
    return 1


def cost_line(pid, qty, opts=None, m=None):
    opts = opts or {}
    it = ITEMS.get(pid)
    if not it or not qty:
        return None
    idx = opts.get("offer", 0)
    up, pack = unit_price(it, idx)
    o = best_offer(it, idx)
    if "cost" in opts:
        c = opts["cost"][m]
        return dict(id=pid, qty=qty, packs=1, pack=1, unit=c, cost=c, it=it, offer=o)
    if up is None:
        return dict(id=pid, qty=qty, packs=None, cost=None, it=it, offer=o)
    packs = math.ceil(qty / pack - 1e-9)
    fee = (opts.get("fee") or {}).get(m, 0)
    return dict(id=pid, qty=qty, packs=packs, pack=pack, unit=up, cost=packs * up + fee, fee=fee, it=it, offer=o)


def method_costs():
    lines = bom_lines()
    res = {m: {c: 0.0 for c in CAT_ORDER} for m in MID}
    table = {m: [] for m in MID}
    missing = set()
    for pid, cat, qd, note, opts in lines:
        for m in MID:
            q = qd.get(m, 0)
            if not q:
                continue
            cl = cost_line(pid, q, opts, m)
            if cl is None:
                missing.add(pid)
                continue
            if cl.get("cost") is None:
                missing.add(pid)
            cl["cat"], cl["note"] = cat, note
            table[m].append(cl)
            if cl.get("cost"):
                res[m][cat] += cl["cost"]
    return res, table, lines, missing


def topo_cost(t):
    tot, miss = 0.0, []
    for pid in t.get("parts", []):
        pid = pid if isinstance(pid, str) else pid.get("id")
        it = ITEMS.get(pid)
        if not it or pid in ("a-buck", "a-mount"):
            continue
        cl = cost_line(pid, qty_num(it.get("qty_suggest"), pid))
        if cl and cl.get("cost"):
            tot += cl["cost"]
        else:
            miss.append(it.get("name_ko", pid))
    return tot, miss


# ------------------------------------------------------------------ html helpers
def sheet(svg, title, meta="", cls="", after=""):
    return (f'<figure class="sheet"><figcaption class="cap"><b>{esc(title)}</b><span class="mono">{esc(meta)}</span></figcaption>'
            f'<div class="dw {cls}">{svg}</div>{after}</figure>')


MAT_LEGEND = ('<div class="legend-mat">'
              '<span><i style="background:#fbfbf8"></i>건반 PETG (단면 빗금)</span>'
              '<span><i style="background:#dfe6ef"></i>출력 프레임</span>'
              '<span><i style="background:#cfe3d6"></i>해머/콤 핀</span>'
              '<span><i style="background:#ecdcc2"></i>합판</span>'
              '<span><i style="background:#b9c0cc"></i>강철</span>'
              '<span><i style="background:#c74a4a"></i>펠트</span>'
              '<span><i style="background:linear-gradient(90deg,#2f6fd6 50%,#c0392b 50%)"></i>자석 S/N</span>'
              '<span><i style="background:transparent;border:1.5px dashed #c2410c"></i>끝까지 눌린 위치</span>'
              '</div>')


def kfs(items):
    return '<div class="kfs">' + "".join(f'<div class="kf"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in items) + "</div>"


def table(head, rows, cls="", right=()):
    th = "".join(f'<th class="{"r" if i in right else ""}">{esc(h)}</th>' for i, h in enumerate(head))
    trs = []
    for r in rows:
        rc = ""
        if isinstance(r, dict):
            rc, r = r.get("cls", ""), r["cells"]
        tds = "".join(f'<td class="{"r num" if i in right else ""}">{c}</td>' for i, c in enumerate(r))
        trs.append(f'<tr class="{rc}">{tds}</tr>')
    return f'<div class="tbl {cls}"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'


def img_path(it):
    cands = []
    f = it.get("image_file")
    if f:
        cands.append("img/" + os.path.splitext(os.path.basename(f))[0] + ".jpg")
    cands.append(f"img/{it.get('id')}.jpg")
    for c in cands:
        if os.path.exists(f"{OUT}/{c}"):
            return c
    return None


def img_tag(it):
    f = img_path(it)
    if f:
        return f'<img src="{esc(f)}" alt="{esc(it.get("name_ko", ""))}" loading="lazy">'
    return '<span class="noimg">이미지 없음</span>'


def part_card(it, qty=None, packs=None, cost=None, note="", optional=None, idx=0, offer=None, fee=0):
    optional = it.get("optional") if optional is None else optional
    if offer is not None:
        up, pack = float(offer["price_krw"]), parse_pack(offer.get("pack_qty"))
    else:
        up, pack = unit_price(it, idx)
    offers = [o for o in it.get("offers", []) if isinstance(o, dict) and o.get("url")]
    links = "".join(
        f'<a href="{esc(o["url"])}" target="_blank" rel="noopener">{esc(o.get("store", "구매처"))}'
        f'{("<span class=pr>" + won(o["price_krw"]) + "</span>") if o.get("price_krw") else ""}</a>' for o in offers[:3])
    specs = it.get("specs") or {}
    spec_rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in specs.items())
    alts = it.get("alternatives") or []
    alt_html = ""
    if alts:
        lis = []
        for a in alts[:3]:
            if not isinstance(a, dict):
                continue
            nm = esc(a.get("name", ""))
            if a.get("url"):
                nm = f'<a href="{esc(a["url"])}" target="_blank" rel="noopener">{nm}</a>'
            pr = f' · {won(a["price_krw"])}' if isinstance(a.get("price_krw"), (int, float)) else ""
            lis.append(f"<li>{nm}{pr} — {esc(a.get('why', ''))}</li>")
        alt_html = f'<div class="alt"><b>대안</b><ul class="proslist">{"".join(lis)}</ul></div>'
    notes = f'<p class="alt">{esc(it.get("notes_ko"))}</p>' if it.get("notes_ko") else ""
    o = offer if offer is not None else best_offer(it, idx)
    pnote = esc(o.get("price_note", "")) if o else ""
    if fee:
        pnote = (pnote + " · " if pnote else "") + f"절단비 {won(fee)} 포함"
    if up is not None:
        unit_txt = f"{won(up)} / {fmtq(pack)}" if pack > 1 else won(up)
    else:
        unit_txt = "가격 확인 필요"
    qty_badge = f'<span class="qty">× {esc(fmtq(qty))}</span>' if qty else ""
    opt = '<span class="opt">선택</span>' if optional else ""
    src = str(it.get("image_source", ""))
    stand_in = any(k in src for k in ("유사", "동일 규격", "아님", "같은 ", "계열")) or it.get("id") in ("e-perf", "e-perf-strip", "e-dupont")
    if stand_in:
        lab = "도면 발췌 (제품 사진 아님)" if "아님" in src else "사진: 같은 규격의 다른 제품"
        opt += f'<span class="sim">{lab}</span>'
    total = f"<b>{won(cost)}</b>" if cost else (f"<b>{won(up)}</b>" if up else "<b>—</b>")
    buy = f"{packs}묶음" if packs and pack > 1 else (f"{packs}개" if packs else "")
    return f"""<article class="part">
<div class="ph">{img_tag(it)}{qty_badge}{opt}</div>
<div class="pb"><div class="cat">{esc(it.get("category", ""))}</div>
<h4>{esc(it.get("name_ko", it.get("id")))}</h4>
<div class="model">{esc(it.get("model", ""))}</div>
<p class="role">{esc(it.get("role_ko", ""))}</p>
<details class="spec"><summary>세부 스펙</summary><table>{spec_rows}</table>{alt_html}{notes}
{f'<p class="alt">사진 출처: {esc(src)}</p>' if stand_in else ''}
{f'<p class="alt">가격 메모: {pnote}</p>' if pnote else ''}</details>
<div class="links">{links}</div>
<div class="price"><span>{esc(unit_txt)}{(' · ' + buy) if buy else ''}{(' · ' + esc(note)) if note else ''}</span>{total}</div>
</div></article>"""


def fmtq(q):
    if isinstance(q, float) and not q.is_integer():
        return f"{q:.2f}".rstrip("0")
    return f"{int(q)}"


# ------------------------------------------------------------------ pages
def page_overview(costs):
    cards = []
    for M in METHODS:
        t = METHOD_TEXT[M["id"]]
        pp = calc.print_plan(M)
        tot = sum(costs[M["id"]].values())
        dw = f'{M.get("DW", L["BW_rest"] + 2):.0f}'
        cards.append(f"""<a class="mcard" href="#{M['id'].lower()}">
<div style="display:flex;justify-content:space-between;align-items:center"><span class="id">{M['id']}</span>{'<span class="pill rec">권장</span>' if M['id'] == REC else ''}</div>
<div class="nm">{esc(t['title'].split('·')[1].strip())}</div>
<div class="muted small">{esc(M['short'])}</div>
<dl><dt>피벗 (앞끝→축)</dt><dd>{M['pivot'][0]:.0f} mm</dd>
<dt>복귀</dt><dd>{'스프링' if M['id'] in 'AB' else '중력(추)'}</dd>
<dt>센서 위치 이동</dt><dd>{M['t110']:.2f} mm</dd>
<dt>유효 질량(관성)</dt><dd>{M['m_eff']:.0f} g</dd>
<dt>필라멘트 / 출력</dt><dd>{pp['total']/1000:.1f} kg · {pp['hours']:.0f} h</dd>
<dt>케이스 깊이</dt><dd>{M['depth'] + 14 + 150 + 22:.0f} mm</dd></dl>
<div class="cost"><small>예상 총비용</small>{won(tot)}</div></a>""")
    # cost bars
    mx = max(sum(costs[m].values()) for m in MID)
    rows = []
    for m in MID:
        segs = "".join(
            f'<span class="c{i+1}" style="width:{costs[m][c]/mx*100:.2f}%" data-tip="{CAT[c]} {won(costs[m][c])}"></span>'
            for i, c in enumerate(CAT_ORDER) if costs[m][c] > 0)
        rows.append(f'<div class="cb-row"><div class="lab">방식 {m}</div><div class="bar">{segs}</div><div class="tot">{won(sum(costs[m].values()))}</div></div>')
    leg = "".join(f'<span><i class="c{i+1}"></i>{CAT[c]}</span>' for i, c in enumerate(CAT_ORDER))
    trows = []
    for c in CAT_ORDER:
        trows.append([esc(CAT[c])] + [won(costs[m][c]) for m in MID])
    trows.append({"cls": "total", "cells": ["합계"] + [won(sum(costs[m].values())) for m in MID]})
    req = table(["요구", "내용", "이 설계에서의 답"], [[f'<span class="mono">{esc(a)}</span>', esc(b), esc(c)] for a, b, c in REQ_MAP])
    return f"""<section class="page" id="p-overview" data-page="overview">
<h2>개요 · 4가지 건반 방식과 총비용</h2>
<p class="lede">기준 문서는 <span class="mono">hardware/mechanical/sound-requirements.md</span> 하나입니다(R1–R16, D1–D17). 이전 설계 자료는 참고하지 않고,
건반 액션을 4가지 방식으로 새로 설계했습니다. 각 방식은 실제 치수가 적힌 측면도·평면도·부품도를 갖고 있어 그대로 CAD로 옮길 수 있습니다.
전자부·소리·페달·케이스는 네 방식이 같이 씁니다.</p>
<div class="grid g4">{''.join(cards)}</div>
<h3>방식별 예상 비용</h3>
<div class="card"><div class="costbars" id="costbars">{''.join(rows)}</div><div class="cb-leg">{leg}</div></div>
{table(["분류", "A", "B", "C", "D"], trows, right=(1, 2, 3, 4))}
<p class="muted small">공구(인두·스트리퍼·멀티미터)와 3D 프린터는 이미 있다고 보고 합계에서 뺐습니다. 필요하면 <a href="#bom">부품표·비용</a>의 선택 항목을 더하세요.</p>
<h3>고르는 기준</h3>
<div class="grid g2">
<div class="card"><h4>빨리, 싸게, 확실하게 동작시키려면 → B</h4><p class="muted small">건반을 하나씩 교체할 수 있고, 강철 축이라 수명 걱정이 적습니다. 터치는 가벼운 신스 느낌입니다.</p></div>
<div class="card"><h4>“실제 피아노처럼”(R6)이 우선이면 → D</h4><p class="muted small">해머 추가 만드는 관성(약 {D['m_eff']:.0f} g)이 입문형 디지털 피아노 액션과 같은 원리입니다. 부품과 조립 시간이 가장 많습니다.</p></div>
<div class="card"><h4>부품 수를 최소로 → A</h4><p class="muted small">옥타브당 출력 1회. 대신 힌지 크리프를 시제품으로 먼저 검증해야 합니다.</p></div>
<div class="card"><h4>어쿠스틱 구조 그대로 → C</h4><p class="muted small">밸런스 핀·펀칭·중력 복귀. 건반이 {C['body_end']:.0f} mm로 길고 강철이 약 {(52*C['m_cw']+36*C['m_cw_b'])/1000:.1f} kg 들어갑니다.</p></div>
</div>
<div class="note felt"><b>권장 순서.</b> B와 D를 각각 1옥타브(12키)만 먼저 만들어 비교하세요. 전자부·센서 레일·프레임은 두 방식이 같은 치수라서 그대로 재사용됩니다.</div>
<h3>요구사항 대응</h3>{req}
<h3>전제</h3><ul class="proslist muted small">{''.join(f'<li>{esc(a)}</li>' for a in ASSUMPTIONS)}</ul>
</section>"""


def page_common():
    krows = []
    for k in KEYS:
        head = f"{k['head'][0]:.2f} – {k['head'][1]:.2f}" if not k["black"] else "—"
        krows.append([f"<b>{k['name']}</b>", "흑건" if k["black"] else "백건", f"{k['slot'][0]:.2f}", f"{k['slot'][1]:.2f}",
                      f"{k['slot'][1]-k['slot'][0]:.2f}", f"{k['w']:.2f}", f"<b>{k['cx']:.2f}</b>", head,
                      f"{k['hcx']:.2f}" if not k["black"] else f"{k['cx']:.2f}"])
    mods = [("O1", "A0–B1", 15, "A0·A#0·B0 레일(3) + C1 옥타브"), ("O2", "C2–B2", 12, ""), ("O3", "C3–B3", 12, ""), ("O4", "C4–B4", 12, "가운데 C = C4"),
            ("O5", "C5–B5", 12, ""), ("O6", "C6–B6", 12, ""), ("O7", "C7–C8", 13, "C7 옥타브 + C8 레일(1)"), ("PED", "페달 3개", 3, "GP26·27·28 직접 ADC")]
    mrows = [[f"<b>{a}</b>", b, str(c), f"C0–C{c-1}" if a != "PED" else "—", f"Toccata {a}", d] for a, b, c, d in mods]
    grow = []
    for M in METHODS:
        if M["id"] == "D":
            grow.append([f"<b>D</b> (해머)", f"{M['g_up']:.2f}", f"{M['g_dn']:.2f}", f"{3.0 + M['t110_hb']:.2f}", f"{M['t110']:.2f}",
                         f"{Bz(M['g_up']+0.8):.0f} → {Bz(M['g_dn']+0.8):.0f}", "0"])
        else:
            grow.append([f"<b>{M['id']}</b>", f"{M['g_up']:.2f}", f"{M['g_dn']:.2f}", f"{M['g_dn_b']:.2f}", f"{M['t110']:.2f} / {M['t110_b']:.2f}",
                         f"{Bz(M['g_up']+0.8):.0f} → {Bz(M['g_dn']+0.8):.0f}", f"{M['mag_recess_b']:.1f}"])
    return f"""<section class="page" id="p-common" data-page="common" hidden>
<h2>공통 규격 · 네 방식이 같이 쓰는 치수</h2>
<p class="lede">좌표는 모든 도면에서 같습니다. <b>x</b> = 건반 폭 방향(옥타브 도면은 C 왼쪽 끝이 0), <b>y</b> = 백건 앞끝이 0인 깊이 방향, <b>z</b> = 키베드 합판 윗면이 0인 높이. 단위는 모두 mm입니다.</p>
{kfs([("백건 간격", "23.5 mm"), ("옥타브", "164.5 mm"), ("88건반 폭", "1222 mm"), ("백건 딥", "10.0 mm"), ("흑건 딥", "9.0 mm"), ("흑건 높이", "+12.0 mm"), ("홀센서 열", "y = 110")])}
<h3><span class="no">01</span>1옥타브 건반 배열 평면도</h3>
{sheet(dw_plan.octave_layout_plan(), "건반 배열 — 위에서 본 모습 (연주자 쪽이 아래)", "축척 약 1:1 화면 기준 · 단위 mm")}
<p class="muted small">흑건 위치는 그룹 분할 방식입니다: C–E 구간(70.5 mm)에 흑건 2개(폭 11.5 + 틈 1.0)를 넣고 남은 폭을 꼬리 3개로 나누고, F–B 구간(94 mm)은 흑건 3개와 꼬리 4개로 나눕니다. 흑건 폭 11.5 mm·길이 95 mm·높이 12 mm, 백건 머리 50 mm는 조사한 실측값 범위입니다.</p>
{table(["건반", "종류", "슬롯 시작 x", "슬롯 끝 x", "슬롯 폭", "몸체 폭", "센서·자석 x", "머리 x 범위", "가이드 핀 x"], krows, right=(2, 3, 4, 5, 6, 8))}
<h3><span class="no">02</span>88건반 전체와 모듈 분할</h3>
{sheet(dw_plan.full_keyboard(), "88건반 (A0–C8) · 모듈 O1–O7", "전체 폭 1222 mm")}
{table(["모듈", "건반", "센서 수", "MUX 채널", "USB 이름 (D3)", "비고"], mrows)}
<p class="muted small">양 끝 건반 A0와 C8은 옆에 흑건이 없습니다. A0는 꼬리를 왼쪽으로 넓혀 {fmt_mm(dw_plan.end_tail_w()['A0'], 2)} mm, C8은 오른쪽으로 넓혀 머리 폭과 같은 {fmt_mm(dw_plan.end_tail_w()['C8'], 2)} mm로 출력하고, 센서·자석은 표의 x 값(A 슬롯 중심, C 슬롯 중심) 그대로 둡니다. 옥타브 모듈은 C–B 단위로 만들고, A0–B0(3키)와 C8(1키)은 짧은 전용 레일을 씁니다.</p>
<h3><span class="no">03</span>건반 단면</h3>
{sheet(dw_parts.key_sections(A), f"건반 단면 A-A ~ D-D ({basis_note(A, 'H', '높이')})", "벽 1.6 · 윗판 2.0", "narrow")}
<h3><span class="no">04</span>홀센서와 자석</h3>
<p>센서는 TI <b>DRV5055A3</b>(TO-92)를 각인면이 위를 보게 눕혀 레일 홈에 넣습니다. 3.3 V에서 감도 15 mV/mT, 선형 범위 ±88 mT입니다. 자석은 Ø6×3 N35 원판, 건반(또는 해머) 밑 홈에 순간접착제로 붙입니다.
가장 가까울 때 간격을 3.0 mm로 잡아 자기장이 선형 범위 안(약 {Bz(3.8):.0f} mT)에 들게 했습니다.</p>
{sheet(dw_parts.sensor_detail(), "센서 레일 단면과 자석 간격", "레일 y 98–126 · 센서면 z 8.0", "narrow")}
<div class="grid g2">
<div class="card"><div class="eyebrow">자석 거리별 자기장 (Ø6×3 N35, 계산)</div>{dw_parts.field_chart()}</div>
<div>{table(["방식", "휴지 간격", "백건 끝 간격", "흑건 끝 간격", "이동량 백/흑", "자기장 mT", "흑건 자석 추가 깊이"], grow, right=(1, 2, 3, 4, 6))}
<p class="muted small">흑건은 딥 9 mm로 백건보다 각도가 커서 센서 위치에서 더 많이 내려옵니다. 그래서 흑건 자석 홈만 표의 값만큼 더 깊게 파서 가장 가까운 간격을 3.0 mm로 맞춥니다. 이웃 건반 자석(약 13 mm 옆)이 주는 간섭은 계산상 최대 약 2 mT(신호의 약 3 %)로, 펌웨어 보정(D4)으로 지웁니다.</p></div>
</div>
<h3><span class="no">05</span>케이스와 스피커 배치</h3>
{sheet(dw_plan.case_layout(B), f"케이스 평면 배치 ({basis_note(B, 'depth', '깊이', rel=True)})", f"D14: 위성 {fmt_mm(dw_plan.SAT_R)} mm · 서브 {fmt_mm(dw_plan.SUB_R)} mm 이상")}
<ul class="proslist muted small">
<li>위성 스피커 2개는 뒤쪽 스피커 바 양 끝의 밀폐 상자(내부 4.7 L, D12)에 넣고, 유닛은 연주자 쪽으로 약 15° 들어 올립니다 (D17). 그릴은 구멍이 넉넉한 타공판.</li>
<li>서브우퍼는 키베드 뒤쪽·스피커 바 아래 가운데에 매달고 아래쪽으로 방사합니다. 상자는 고무 방진 마운트로 키베드와 떼어 놓습니다 (D15).</li>
<li>센서 열(y 110)에서 위성 유닛까지 y거리 {dw_plan.case_geom(B)['spk_y'] - L['y_sensor']:.0f} mm, 서브 유닛 중심까지 {dw_plan.case_geom(B)['sub_c'][1] - L['y_sensor']:.0f} mm로 D14 이격을 넘깁니다. 설치 후 게이트 ④ 재시험은 그대로 필요합니다.</li>
</ul>
</section>"""


def calc_table(M):
    mid = M["id"]
    rows = [["θmax 백건 / 흑건", f"{math.degrees(M['theta']):.2f}° / {math.degrees(M['theta_b']):.2f}°", "딥 10.0 / 9.0 mm가 되도록 하한 펠트 높이 결정"],
            ["하한 레일 윗면 (백 / 흑)", f"z {M['rail_w_top']:.2f} / {M['rail_b_top']:.2f}", "펠트 3 t, 0.5 mm 눌림 포함"],
            ["센서 위치 이동량 (백 / 흑)", f"{M['t110']:.2f} / {M.get('t110_b', M.get('t110_hb', 0)):.2f} mm", "y 110"],
            ["건반 질량 (백 / 흑)", f"{M['wk']['m']:.1f} / {M['bk']['m']:.1f} g", "PETG 1.27 g/cm³, 속 빈 구조"],
            ["유효 질량 (건반 앞끝 환산 관성)", f"{M['m_eff']:.0f} g", "누를 때 손가락이 느끼는 묵직함"]]
    if mid in ("A", "B"):
        s = M["spring"]
        rows += [["스프링", f"선경 {s['d']} · 외경 {s['D_out']:.0f} · 유효 {s['n']:.1f}회", f"자유 길이 약 {M['spring_Lrest'] + s['pre']:.1f} mm, 설치 12.0 mm"],
                 ["스프링 상수 / 예압", f"{s['k']:.3f} N/mm / {s['pre']:.1f} mm", f"휴지 {s['F_rest']:.2f} N → 끝 {s['F_max']:.2f} N"],
                 ["스프링 전단 응력", f"{s['tau']:.0f} MPa", "피아노선 허용 약 800 MPa 이하"],
                 ["누르는 힘 (백건 앞끝)", f"{L['BW_rest']:.0f} → {M.get('BW_bottom_A', L['BW_bottom']):.0f} g", "시작 → 바닥 (마찰 약 2–4 g 별도)"],
                 ["흑건 예압 조정", f"{M['black_adj']:.1f} mm 내림", f"조정 안 하면 흑건이 {M['BW_black_same']:.0f} g로 무거워짐"]]
    if mid == "A":
        f = M["flex"]
        rows += [["힌지 굽힘 변형률", f"{f['strain']*100:.2f} %", "PETG 권장 0.5 % 이하"],
                 ["힌지 굽힘 강성 기여", f"{f['Mf_front_g']:.1f} g", "바닥에서 추가되는 힘"],
                 ["힌지 상시 하중 / 응력", f"{f['V_rest']:.2f} N / {f['sigma_rest']:.1f} MPa", "크리프 검토 대상 (PETG 항복 약 47 MPa)"]]
    if mid == "B":
        rows += [["샤프트 휨 (핀 사이)", f"{M['shaft_defl']*1000:.1f} µm", "콤 핀이 13–15 mm마다 받침"]]
    if mid == "C":
        rows += [["추 (백건 / 흑건)", f"{M['cw_len']} / {M['cw_len_b']} mm · {M['m_cw']:.0f} / {M['m_cw_b']:.0f} g", f"{M['cw_bar']}, 중심 y {fmt_mm(M['cw_c'])}"],
                 ["DW / UW", f"{M['DW']:.0f} / {M['UW']:.0f} g", f"균형 {L['BW_grav']:.0f} g ± 마찰 {L['friction']:.0f} g"],
                 ["뒤끝 상승", f"{M['rear_rise']:.1f} mm", "뚜껑까지 여유 확인"]]
    if mid == "D":
        wc, wcb = fmt_mm(sum(M["h_weight"]) / 2), fmt_mm(sum(M["h_weight_b"]) / 2)
        rows += [["해머 추 (백건 / 흑건)", f"{M['w_len']} / {M['w_len_b']} mm · {M['m_w']:.0f} / {M['m_w_b']:.0f} g",
                  f"{M['w_bar']}, 중심 y {wc}" + (f" / {wcb}" if wcb != wc else "")],
                 ["해머 각도 (백 / 흑)", f"{math.degrees(M['h_theta']):.1f}° / {math.degrees(M['h_theta_b']):.1f}°", f"각속도비 {M['ratio']:.2f}"],
                 ["추 상승 (백 / 흑)", f"{M['w_rise']:.1f} / {M['w_rise_b']:.1f} mm", "건반 속으로 올라감"],
                 ["추 위 여유 (백 / 흑)", f"{M['w_clear']:.1f} / {M['w_clear_b']:.1f} mm", "과회전 스톱이 넘침 제한"],
                 ["DW / UW", f"{M['DW']:.0f} / {M['UW']:.0f} g", f"균형 {L['BW_grav']:.0f} g ± 마찰 {L['friction']:.0f} g"]]
    return table(["항목", "값", "설명"], [[esc(a), f'<span class="num">{esc(b)}</span>', esc(c)] for a, b, c in rows])


def page_method(M, costs, table_rows):
    mid = M["id"]
    t = METHOD_TEXT[mid]
    pp = calc.print_plan(M)
    k = [("피벗 (앞끝→축)", f"{M['pivot'][0]:.0f} mm"), ("건반 길이", f"{M['body_end']:.0f} mm"), ("백건 윗면 높이", f"z {M['z_top']:.1f}"),
         ("센서 이동량", f"{M['t110']:.2f} mm"), ("유효 질량", f"{M['m_eff']:.0f} g"),
         ("필라멘트", f"{pp['total']/1000:.1f} kg"), ("출력 시간", f"약 {pp['hours']:.0f} h"), ("예상 총비용", won(sum(costs[mid].values())))]
    legend = "".join(f'<tr><td><span class="bal">{n}</span></td><td>{esc(nm)}</td></tr>' for n, nm in t["parts"])
    prow = [[esc(r["name"]), esc(r["mat"]), str(r["n"]), f"{r['g']:.1f}", f"{r['tot']:.0f}"] for r in pp["rows"]]
    prow.append({"cls": "total", "cells": ["합계 (여유 15 % 포함)", f"흰 {pp['white']/1000:.2f} · 검 {pp['black']/1000:.2f} · 기타 {pp['other']/1000:.2f} kg", "", "", f"{pp['total']:.0f}"]})
    # method-specific parts (mech category)
    mech = [cl for cl in table_rows[mid] if cl["cat"] == "mech"]
    mcards = "".join(card_from_line(cl) for cl in mech)
    side = dw_side.SIDE[mid](M)
    det = dw_parts.DETAIL[mid](M)
    det_title = {"A": "탄성 힌지 상세 (옆에서)", "B": "힌지 콤과 아이렛 (위에서)", "C": "밸런스 핀과 모티스 (단면)", "D": "해머 레버 부품도 (옆에서)"}[mid]
    wtab = ""
    if True:
        rows = []
        for kk in KEYS:
            if kk["black"]:
                continue
            h0 = kk["head"][0]
            rows.append([kk["name"], f"{kk['head'][1]-kk['head'][0]:.2f}", f"{kk['w']:.2f}", f"{kk['body'][0]-h0:.2f}", f"{kk['head'][1]-kk['body'][1]:.2f}"])
        wtab = table(["백건", "머리 폭", "꼬리 폭", "꼬리 왼쪽 오프셋", "꼬리 오른쪽 오프셋"], rows, right=(1, 2, 3, 4))
    win = dw_parts.key_features(M).get("window")      # rib-free window drawn on the D key part (None for A-C)
    winb = dw_parts.key_features(M, black=True).get("window")
    tap = fmt_mm(hammer_parts(M)["screws"][0][3] - M["h_ct"]) if win else ""   # screw length minus the cradle floor = thread depth in the bar
    extra_note = {
        "A": "콤은 흰 PETG 한 색으로 뽑고, 흑건 윗부분(길이 95 · 높이 12)은 검정 캡으로 따로 뽑아 붙입니다. AMS가 있으면 두 색 한 번에 출력해도 됩니다. 힌지 판(t1.2)은 첫 레이어 0.2 + 이후 0.2 × 5층으로, 인필 없이 100 % 벽으로 채웁니다.",
        "B": "건반은 윗면을 베드에 대고 뒤집어 출력합니다(서포트 없음, 윗면이 매끈). 흑건은 바로 세워 출력합니다. 아이렛 구멍 Ø" + fmt_mm(B['hole_d']) + "은 출력 후 Ø4.1 드릴로 한 번 정리합니다.",
        "C": "앞 부품은 윗면을 베드에 대고, 뒤 부품은 밑면을 베드에 대고 출력합니다. 겹침 이음에는 M3 인서트를 뒤 부품에 박고 앞 부품 쪽에서 볼트를 넣습니다.",
        "D": (f"건반 높이가 {fmt_mm(M['H'])} mm이고, 추가 올라오는 구간(백건 y {win[0]:.0f}–{win[1]:.0f}, 흑건 y {winb[0]:.0f}–{winb[1]:.0f})에는 리브가 없습니다. 해머는 옆으로 눕혀 출력하고, 추는 해머 뒤쪽 받침(크래들)에 넣어 밑에서 {M['h_screw']} 나사 2개로 고정합니다(추에 M3 탭 {tap} mm)." if win else ""),
    }[mid]
    return f"""<section class="page" id="p-{mid.lower()}" data-page="{mid.lower()}" hidden>
<div class="eyebrow">건반 액션 방식 {mid} / 4</div>
<h2>{esc(t['title'])}</h2>
<p class="lede">{esc(t['one'])}</p>
{kfs(k)}
<div class="cols"><div><h4>동작 원리</h4><ul class="proslist">{''.join(f'<li>{esc(x)}</li>' for x in t['how'])}</ul></div>
<div class="grid g2" style="gap:10px"><div class="card"><h4>장점</h4><ul class="proslist small">{''.join(f'<li>{esc(x)}</li>' for x in t['pros'])}</ul></div>
<div class="card"><h4>단점·위험</h4><ul class="proslist small">{''.join(f'<li>{esc(x)}</li>' for x in t['cons'])}</ul></div></div></div>
<h3><span class="no">{mid}-1</span>조립 측면도 (백건 중심 단면)</h3>
{sheet(side, "측면도 — 오른쪽 방향이 연주자에게서 멀어지는 쪽", "좌표 y·z · 단위 mm · 세로 좌표는 키베드 윗면 기준", after=MAT_LEGEND)}
<div class="grid g2" style="margin-top:12px"><div>{table(["번호", "부품"], [[f'<span class="bal">{n}</span>', esc(nm)] for n, nm in t['parts']])}</div>
<div>{calc_table(M)}</div></div>
<h3><span class="no">{mid}-2</span>프레임 평면도 (1옥타브 모듈)</h3>
{sheet(dw_plan.frame_plan(M), "위에서 본 프레임 — 건반은 점선 투시", f"모듈 폭 {fmt_mm(dw_plan.OCT - dw_plan.JOINT)} (피치 {fmt_mm(dw_plan.OCT)}) · 오른쪽 라벨 = 각 건반 중심 x")}
<h3><span class="no">{mid}-3</span>건반 부품도</h3>
{sheet(dw_parts.key_part(M), "백건 (C 기준)", "위: 평면도 · 아래: 측면도 · 점선 = 속 형상")}
{wtab}
{sheet(dw_parts.key_part(M, 'C#', True), "흑건 (모든 흑건 공통)", "흑건 윗면 폭 9.5 · 밑 폭 11.5")}
<h3><span class="no">{mid}-4</span>{esc(det_title)}</h3>
{sheet(det, det_title, "확대", "narrow")}
<h3><span class="no">{mid}-5</span>출력 계획</h3>
<p class="muted small">{esc(extra_note)}</p>
{table(["출력물", "재료", "개수", "개당 g", "합계 g"], prow, right=(2, 3, 4))}
<h3><span class="no">{mid}-6</span>조립 순서</h3>
<ol class="proslist">{''.join(f'<li>{esc(s)}</li>' for s in ASSEMBLY[mid])}</ol>
<h3><span class="no">{mid}-7</span>이 방식에만 필요한 부품</h3>
{('<div class="parts">' + mcards + '</div>') if mcards else '<p class="muted">추가 기구 부품 없음 (공통 부품만 사용).</p>'}
<div class="note warn"><b>시제품 검증.</b> {esc(t['test'])}</div>
</section>"""


def card_from_line(cl):
    return part_card(cl["it"], cl["qty"], cl.get("packs"), cl.get("cost"), cl.get("note", ""), offer=cl.get("offer"), fee=cl.get("fee", 0))


LINES = {}


def cards_for(ids, method="B"):
    out = []
    for pid in ids:
        it = ITEMS.get(pid)
        if not it:
            continue
        cl = LINES.get(method, {}).get(pid)
        if cl is None:
            for m in MID:
                if pid in LINES.get(m, {}):
                    cl = LINES[m][pid]
                    break
        out.append(card_from_line(cl) if cl else part_card(it))
    return '<div class="parts">' + "".join(out) + "</div>"


def ids_with_prefix(prefix, src):
    return [it["id"] for it in items_of(src) if isinstance(it, dict) and str(it.get("id", "")).startswith(prefix)]


def page_elec(table_rows):
    bq = {cl["id"]: cl["qty"] for cl in table_rows["B"] if cl["cat"] == "elec"}
    ids = [it["id"] for it in items_of(ELEC) if isinstance(it, dict)]
    core = [i for i in ids if not ITEMS[i].get("optional")]
    opt = [i for i in ids if ITEMS[i].get("optional")]
    pn = lambda p: f"{p[0]} ({p[1]}번)"          # (name, pin no.) shared with dw_elec.module_schematic
    pinrows = [["GP26 (ADC0)", "MUX SIG", "센서 신호 (모듈당 1개 ADC)"], ["GP2–GP5", "MUX S0–S3", "채널 선택 (0–15)"], [pn(dw_elec.PIN_GND), "MUX EN", "항상 켬 (LOW)"],
               [pn(dw_elec.PIN_3V3), "센서 VCC 버스 · MUX VCC", "센서 12–15개 × 약 6 mA ≈ 100 mA"], [pn(dw_elec.PIN_AGND), "센서 GND 버스 · MUX GND", "아날로그 잡음 분리"],
               ["ADC_VREF", "—", "기본(3.3 V) 사용, 센서 출력이 전원 비례형"], ["USB", "허브", "USB-MIDI + 전원"]]
    return f"""<section class="page" id="p-elec" data-page="elec" hidden>
<h2>전자·배선 · PCB 없이 납땜으로</h2>
<p class="lede">건반 모듈 7개와 페달 모듈 1개가 각각 표준 USB-MIDI 장치로 Pi 5에 연결됩니다(R8·R9·D3). 모듈 하나는 피코 1개 + 16채널 MUX 1개 + 만능기판 1장이고, 센서는 센서 레일 위에서 전선으로 이어 붙입니다.</p>
<h3><span class="no">E-1</span>전체 신호 흐름</h3>
<div class="sheet"><div class="dw">{dw_elec.system_diagram()}</div></div>
<h3><span class="no">E-2</span>건반 모듈 배선도 (O2 예)</h3>
<div class="sheet"><div class="dw">{dw_elec.module_schematic()}</div></div>
{table(["피코 핀", "연결", "메모"], pinrows)}
<ul class="proslist muted small">
<li>스캔: MUX 채널 전환 후 약 5 µs 기다렸다 읽으면 16채널 한 바퀴가 약 0.2 ms → 건반당 약 5 kHz로 읽습니다. 속도 계산(R2)에 충분합니다.</li>
<li>센서 레일 배선: VCC·GND는 0.5 mm 주석 도금 단선을 레일 뒤 홈을 따라 버스로 깔고, 센서 다리를 그대로 납땜합니다. 신호선은 AWG28 실리콘선으로 모듈까지(15–25 cm).</li>
<li>레일과 모듈 사이는 JST-XH 커넥터로 떼어낼 수 있게 합니다. 고장 모듈을 통째로 바꿀 수 있습니다.</li>
</ul>
<h3><span class="no">E-3</span>부품</h3>
{cards_for(core)}
<h4 style="margin-top:18px">선택 · 공구</h4>
{cards_for(opt)}
</section>"""


def page_audio(table_rows):
    topo = AUD.get("topologies", [])
    tcards = []
    for t in topo:
        rec = '<span class="pill rec">권장</span>' if t.get("recommended") else ""
        tc, tmiss = topo_cost(t)
        tc += 188160
        costline = f'<p class="num"><b>{won(tc)}</b> <span class="muted small">(부품 + Pianoteq Stage{", 가격 미확인: " + ", ".join(tmiss) if tmiss else ""})</span></p>'
        tcards.append(f"""<div class="card"><div style="display:flex;justify-content:space-between;gap:8px"><h4>{esc(t.get('name_ko', t.get('id')))}</h4>{rec}</div>
<p class="small muted">{esc(t.get('summary_ko', ''))}</p>
<div class="cols"><div><div class="eyebrow">장점</div><ul class="proslist small">{''.join(f'<li>{esc(x)}</li>' for x in t.get('pros_ko', []))}</ul></div>
<div><div class="eyebrow">단점</div><ul class="proslist small">{''.join(f'<li>{esc(x)}</li>' for x in t.get('cons_ko', []))}</ul></div></div>
<p class="small"><b>요구사항:</b> {esc(t.get('meets_requirements_ko', ''))}</p>{costline}</div>""")
    rec = next((t for t in topo if t.get("recommended")), None)
    rec_ids = [p if isinstance(p, str) else p.get("id") for p in (rec or {}).get("parts", [])]
    all_ids = [it["id"] for it in items_of(AUD) if isinstance(it, dict)]
    q = {cl["id"]: cl["qty"] for cl in table_rows["B"] if cl["cat"] == "audio"}
    others = [i for i in all_ids if i not in rec_ids or i in ("a-buck", "a-mount")]
    sw = AUD.get("software", [])
    swrows = [[f'<a href="{esc(s.get("url", "#"))}" target="_blank" rel="noopener">{esc(s.get("name", ""))}</a>', esc(s.get("price", "")), esc(s.get("license", "")),
               esc(s.get("linux_arm", "")), esc(s.get("features", ""))] for s in sw if isinstance(s, dict)]
    return f"""<section class="page" id="p-audio" data-page="audio" hidden>
<h2>소리 · 프로그램 + 앰프 + 스피커</h2>
<p class="lede">R12–R16과 D6–D17을 기준으로 세 가지 구성을 비교했습니다. 권장안(T-B)은 Pi DAC+의 라인 출력을 DSP 2.1 앰프 보드에 넣어 100 Hz에서 위성과 서브를 나눕니다. 위성 DMA105-4는 4.7 L 밀폐함에서 100 Hz 아래 약 2.6 W만 넘어도 최대 진폭에 닿기 때문에, 직렬 콘덴서 없이(D13) 저음을 잘라 주려면 DSP가 필요합니다.</p>
<div class="note warn"><b>D16이 바뀝니다.</b> 권장안의 HAT(DAC+)은 Pi에 전원을 넣지 않습니다. Pi는 공식 27 W USB-C 어댑터 한 곳으로만 급전하고, 앰프는 24 V 어댑터를 따로 씁니다. “앰프 HAT이 Pi를 급전”하는 원래 구성을 지키려면 T-A(HiFiBerry Amp4 Pro)를 고르세요.</div>
<h3><span class="no">S-1</span>구성 후보</h3>
<div class="grid g2">{''.join(tcards)}</div>
<h3><span class="no">S-2</span>스피커 상자 계산</h3>
{kfs([("위성 Qtc", "0.71"), ("위성 F3 (4.7 L)", "≈101 Hz"), ("위성 Xmax 한계 (<100 Hz)", "≈2.6 W"), ("서브 Qtc (15 L)", "0.92"), ("서브 F3", "≈39 Hz"), ("서브 Xmax 한계", "≈77 W")])}
<div class="grid g2"><details class="card"><summary><b>위성 DMA105-4 · 밀폐 4.7 L 계산 과정</b></summary><p class="small" style="white-space:pre-line">{esc(AUD.get('dma105_box_calc_ko', ''))}</p></details>
<details class="card"><summary><b>서브우퍼 RSS210HF-4 계산 과정과 다른 후보</b></summary><p class="small" style="white-space:pre-line">{esc(AUD.get('sub_box_calc_ko', ''))}</p></details></div>
<p class="muted small">서브 상자는 권장 순부피 15–18 L + 흡음재. 드라이버 깊이가 124 mm라 상자 높이는 약 165 mm입니다. 케이스 아래에 공간이 모자라면 LS10-44(깊이 84 mm, F3 ≈57 Hz)로 바꿉니다.</p>
<h3><span class="no">S-3</span>권장 구성 부품</h3>
{cards_for([i for i in rec_ids if i not in ("a-buck", "a-mount")] + ["s-pianoteq"])}
<h3><span class="no">S-4</span>음원 소프트웨어</h3>
{table(["이름", "가격", "라이선스", "Pi 5 (ARM)", "기능"], swrows)}
{('<h3><span class="no">S-5</span>다른 구성의 부품·대안</h3>' + cards_for(others)) if others else ''}
</section>"""


def page_pedal(table_rows):
    cfgs = PED.get("configs", [])
    cc = []
    for c in cfgs:
        rec = '<span class="pill rec">권장</span>' if c.get("recommended") else ""
        parts = ", ".join((p if isinstance(p, str) else (f"{p.get('id')} ×{p.get('qty', 1)}" if isinstance(p, dict) else f"{p[0]} ×{p[1]}")) for p in c.get("parts", []))
        tot = c.get("total_krw")
        cc.append(f"""<div class="card"><div style="display:flex;justify-content:space-between;gap:8px"><h4>{esc(c.get('name_ko', c.get('id')))}</h4>{rec}</div>
<p class="mono small">{esc(parts)}</p>
<div class="cols"><div><div class="eyebrow">장점</div><ul class="proslist small">{''.join(f'<li>{esc(x)}</li>' for x in c.get('pros_ko', []))}</ul></div>
<div><div class="eyebrow">단점</div><ul class="proslist small">{''.join(f'<li>{esc(x)}</li>' for x in c.get('cons_ko', []))}</ul></div></div>
{f'<p class="num"><b>{won(tot)}</b></p>' if isinstance(tot, (int, float)) else ''}</div>""")
    ids = [it["id"] for it in items_of(PED) if isinstance(it, dict)]
    q = {cl["id"]: cl["qty"] for cl in table_rows["B"] if cl["cat"] == "pedal"}
    return f"""<section class="page" id="p-pedal" data-page="pedal" hidden>
<h2>페달·조작부</h2>
<p class="lede">페달 모듈(피코 1개)이 댐퍼(CC64 연속값, D1), 소스테누토(CC66), 소프트(CC67)를 읽습니다(D5). 하프 페달(R3)을 위해 댐퍼는 연속형이어야 합니다.</p>
<h3><span class="no">P-1</span>페달 구성</h3>
<div class="grid g2">{''.join(cc)}</div>
<div class="note"><b>배선.</b> <span style="white-space:pre-line">{esc(PED.get('wiring_notes_ko', ''))}</span></div>
<h3><span class="no">P-2</span>부품</h3>
{cards_for(ids)}
</section>"""


def page_mat(table_rows):
    ids = [it["id"] for it in items_of(MECH) if isinstance(it, dict)]
    q = {}
    for m in MID:
        for cl in table_rows[m]:
            if cl["cat"] in ("print", "case", "mech"):
                q.setdefault(cl["id"], cl["qty"])
    md = MECH.get("material_data", {})
    mrows = []
    for nm, d in md.items():
        if isinstance(d, dict):
            mrows.append([f"<b>{esc(nm)}</b>", esc("; ".join(f"{k}: {v}" for k, v in d.items() if k not in ("source", "sources")))])
    ply, ptot = calc.plywood_cost(B)
    prow = [[esc(a), str(n), f"{w:.0f} × {h:.0f}", mat, won(p) + (" *" if est else ""), won(p * n)] for a, n, w, h, t, mat, p, est in ply]
    prow.append({"cls": "total", "cells": ["합계 (A·B·D)", "", "", "", "", won(ptot)]})
    pr = MECH.get("printers", [])
    prrows = [[f'<a href="{esc(p.get("url", "#"))}" target="_blank" rel="noopener">{esc(p.get("name", ""))}</a>', esc(p.get("bed_mm", "")),
               won(p["price_krw"]) if isinstance(p.get("price_krw"), (int, float)) else esc(p.get("price_krw", ""))] for p in pr if isinstance(p, dict)]
    return f"""<section class="page" id="p-mat" data-page="mat" hidden>
<h2>재료·출력 · 필라멘트부터 나사까지</h2>
<p class="lede">건반은 PETG(흰색·검정), 프레임과 레일은 PETG 또는 PLA+ 회색으로 출력합니다. 방식마다 필요한 양은 각 방식 페이지의 출력 계획 표에 있습니다.</p>
<h3><span class="no">M-1</span>재료 물성 (계산에 쓴 값)</h3>
{table(["재료", "물성"], mrows)}
<h3><span class="no">M-2</span>목재 재단표 (방식 A·B·D, C는 깊이 +124)</h3>
{table(["부재", "수량", "크기 (mm)", "재료", "단가", "금액"], prow, right=(1, 4, 5))}
<p class="muted small">재단 가격은 11번가 ‘웰빙천사’의 가로+세로 합 구간 가격입니다(MDF 18T: 1,600 mm 이하 22,400원, 1,800 mm 이하 28,100원 · 자작 18T는 70,000–88,400원). * 표시는 더 작은 구간 가격을 확인하지 못해 1,600 mm 구간 가격으로 잡은 상한값입니다. 스피커 상자는 소리 면에서도 MDF가 낫고, 보이는 뚜껑만 자작으로 바꾸면 약 +47,600원입니다.</p>
<h3><span class="no">M-3</span>재료·하드웨어</h3>
{cards_for(ids)}
{('<h3><span class="no">M-4</span>3D 프린터 참고 (없을 때만)</h3>' + table(["모델", "베드 (mm)", "가격"], prrows)) if prrows else ''}
</section>"""


def page_bom(costs, table_rows, missing):
    tabs = "".join(f'<button type="button" data-m="{m}" aria-pressed="{"true" if m == REC else "false"}">방식 {m}</button>' for m in MID)
    blocks = []
    for m in MID:
        rows = []
        for c in CAT_ORDER:
            cl_list = [cl for cl in table_rows[m] if cl["cat"] == c]
            if not cl_list:
                continue
            rows.append({"cls": "sub", "cells": [f"<b>{esc(CAT[c])}</b>", "", "", "", "", won(costs[m][c])]})
            for cl in cl_list:
                it = cl["it"]
                o = cl.get("offer")
                link = f'<a href="{esc(o["url"])}" target="_blank" rel="noopener">{esc(o.get("store", "링크"))}</a>' if o and o.get("url") else "—"
                unit = (won(cl["unit"]) + (f" / {fmtq(cl['pack'])}" if cl.get("pack", 1) > 1 else "")) if cl.get("unit") else "확인 필요"
                rows.append([esc(it.get("name_ko", cl["id"])), f'<span class="mono small">{esc(it.get("model", ""))}</span>', fmtq(cl["qty"]), unit, link,
                             won(cl["cost"]) if cl.get("cost") else "—"])
        rows.append({"cls": "total", "cells": ["합계", "", "", "", "", won(sum(costs[m].values()))]})
        blocks.append(f'<div class="bomblock" data-m="{m}" {"hidden" if m != REC else ""}>{table(["품목", "모델", "필요 수량", "단가", "구매처", "금액"], rows, right=(2, 3, 5))}</div>')
    opt_ids = [i for i, it in ITEMS.items() if it.get("optional")]
    miss = f'<p class="muted small">가격을 확인하지 못한 품목: {esc(", ".join(sorted(missing)))}</p>' if missing else ""
    return f"""<section class="page" id="p-bom" data-page="bom" hidden>
<h2>부품표·비용</h2>
<p class="lede">방식을 고르면 그 방식에 필요한 품목과 수량, 구매 단위로 올림한 금액이 나옵니다. 링크는 가격을 확인한 판매 페이지입니다.</p>
<div class="toolbar"><div class="seg" role="group" aria-label="방식 선택">{tabs}</div></div>
{''.join(blocks)}
{miss}
<h3>선택 항목 (합계 제외)</h3>
{cards_for(opt_ids)}
</section>"""


def page_refs():
    urls = []
    for k in ("layout", "tails", "touch", "heights", "flexure"):
        pass
    import re
    s = json.dumps(DIMS, ensure_ascii=False)
    urls = sorted(set(re.findall(r'https?://[^"\s\\]+', s)))
    lis = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></li>' for u in urls)
    return f'<details class="card" style="margin-top:28px"><summary><b>치수·물성 출처 ({len(urls)}건)</b></summary><ul class="src">{lis}</ul></details>'


REC = "B"


def build():
    costs, table_rows, lines, missing = method_costs()
    for m in MID:
        LINES[m] = {cl["id"]: cl for cl in table_rows[m]}
    pages = [page_overview(costs), page_common()] + [page_method(M, costs, table_rows) for M in METHODS] + \
            [page_elec(table_rows), page_audio(table_rows), page_pedal(table_rows), page_mat(table_rows), page_bom(costs, table_rows, missing)]
    nav = [("overview", "", "개요"), ("common", "", "공통 규격"), None, ("a", "A", "콤 플렉서"), ("b", "B", "샤프트 힌지"), ("c", "C", "밸런스 핀"),
           ("d", "D", "해머 액션"), None, ("elec", "", "전자·배선"), ("audio", "", "소리"), ("pedal", "", "페달"), ("mat", "", "재료·출력"), None, ("bom", "", "부품표·비용")]
    navh = "".join('<span class="sep"></span>' if n is None else
                   f'<a href="#{n[0]}" data-to="{n[0]}">{("<span class=tag>" + n[1] + "</span>") if n[1] else ""}{esc(n[2])}</a>' for n in nav)
    css = open("page.css").read() + open("dwg.css").read().split(".dw{")[0].split(":root{")[0] + DWG_EXTRA + dw_elec.SCH_CSS
    dwg_rules = "\n".join(l for l in open("dwg.css").read().splitlines() if l.startswith(".dwg"))
    html = f"""<title>Toccata 제작 도면집</title>
<meta name="description" content="88건반 3D 프린팅 피아노의 건반 액션 4가지 설계 도면과 부품·비용 조사">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>{css}
{dwg_rules}</style>
<header class="tb"><div class="wrap"><div><div class="kicker">Toccata · 88-key build set</div><h1>Toccata 제작 도면집</h1>
<p class="sub">건반 액션 4가지(A–D)의 실제 치수 도면, 필요한 부품 전부의 사양·가격·구매처, 방식별 총비용.</p></div>
<div class="tbgrid"><div><b>기준 문서</b>sound-requirements.md</div><div><b>작성일</b>2026-09-24</div><div><b>단위</b>mm · g · 원</div><div><b>원점</b>y0 = 백건 앞끝</div></div></div></header>
<nav class="tabs" aria-label="페이지"><div class="wrap">{navh}</div></nav>
<main class="wrap">{''.join(pages)}{page_refs()}</main>
<footer><div class="wrap">가격은 판매처 사정에 따라 바뀝니다. 도면 수치는 model.py 계산에서 나온 값이며, 1옥타브 시제품으로 확인한 뒤 88건반으로 늘리는 것을 전제로 합니다.</div></footer>
<div class="tip" id="tip" hidden></div>
<script>{JS}</script>"""
    with open(f"{OUT}/index.html", "w") as fh:
        fh.write(html)
    return costs, missing


DWG_EXTRA = """
.dwg .hid{fill:none;stroke:#6b7690;stroke-width:.8px;stroke-dasharray:4 2.5}
.dwg .hid2{fill:none;stroke:#1f5fbf;stroke-width:.9px;stroke-dasharray:3 2}
.dwg .kb2{fill:#3a3e46;stroke:#1d2433;stroke-width:1.2px}
.dwg .m-blk{fill:#3a3e46;stroke:#1d2433;stroke-width:1px}
.dwg .leaf{fill:#f6c89a;stroke:#1d2433;stroke-width:1px}
.dwg .tx-w{fill:#fff;font-family:system-ui,sans-serif}
.dwg .shaft{stroke:#5d6778;stroke-width:2.5px}
.dwg .mod{fill:#dfe6ef;stroke:#1d2433;stroke-width:1px}
.dwg .sensrow{stroke:#c2410c;stroke-width:1.4px;stroke-dasharray:8 4}
.dwg .spkbox{fill:#e6ecf4;stroke:#1d2433;stroke-width:1px}
.dwg .elec{fill:#e3f0e6;stroke:#1d2433;stroke-width:1px}
"""

JS = r"""
(function(){
  const pages=[...document.querySelectorAll('.page')];
  const links=[...document.querySelectorAll('nav.tabs a')];
  function show(){
    let id=(location.hash||'#overview').slice(1).toLowerCase();
    if(!document.getElementById('p-'+id)) id='overview';
    pages.forEach(p=>{p.hidden=(p.id!=='p-'+id)});
    links.forEach(a=>{ if(a.dataset.to===id) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current'); });
    const cur=links.find(a=>a.dataset.to===id); if(cur&&cur.scrollIntoView) cur.scrollIntoView({block:'nearest',inline:'nearest'});
  }
  window.addEventListener('hashchange',()=>{show();window.scrollTo(0,0)});
  show();
  document.querySelectorAll('.seg button').forEach(b=>b.addEventListener('click',()=>{
    const m=b.dataset.m;
    document.querySelectorAll('.seg button').forEach(x=>x.setAttribute('aria-pressed',x===b?'true':'false'));
    document.querySelectorAll('.bomblock').forEach(x=>{x.hidden=(x.dataset.m!==m)});
  }));
  const tip=document.getElementById('tip');
  document.querySelectorAll('[data-tip]').forEach(el=>{
    el.addEventListener('mousemove',e=>{tip.textContent=el.dataset.tip;tip.hidden=false;tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px'});
    el.addEventListener('mouseleave',()=>{tip.hidden=true});
  });
})();
"""

if __name__ == "__main__":
    costs, missing = build()
    for m in MID:
        print(m, {k: round(v) for k, v in costs[m].items()}, round(sum(costs[m].values())))
    print("missing:", missing)
