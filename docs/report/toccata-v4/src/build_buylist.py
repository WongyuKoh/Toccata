"""Build src/buylist.html: the '구매 목록' tab — the user's final purchase list (최종 재료 page data + saved choices).

usage: python3 build_buylist.py <state_main.json>
Source: hardware/bom/final-bom/site/index.html (embedded data) + the db doc state/main of
https://claude.ai/artifact/9CJ3HwhbhoodCAui94g28n (items the user turned off = owned or not bought).
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
FB = os.path.join(REPO, "hardware", "bom", "final-bom", "site", "index.html")
FINAL_URL = "https://claude.ai/artifact/9CJ3HwhbhoodCAui94g28n"
NOT_USED = {"i054", "i056", "i097", "i103", "i068", "i105", "i030"}   # dropped by the design (L2/R30) or not used in r4.5

page = open(FB, encoding="utf-8").read()
D = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
S = json.load(open(sys.argv[1]))
E = html.escape
W = lambda v: f"{v:,}"


def unit_at(it, q):
    u = it["unit"]
    for mq, up in it.get("tiers") or []:
        if q >= mq:
            u = up
    return u


stores, owned = {}, []
for it in D["items"]:
    on = S["on"].get(it["id"], it["on"])
    if not on:
        if it["id"] not in NOT_USED and "빠짐" not in (it.get("t") or ""):
            owned.append(it)
        continue
    q = S["qty"].get(it["id"], it["qty"])
    u = unit_at(it, q)
    k = it.get("sk") or it["store"]
    st = stores.setdefault(k, {"key": it.get("sk"), "name": k, "rows": [], "sub": 0})
    st["rows"].append((it, q, u, u * q))
    st["sub"] += u * q
for st in stores.values():
    sh = D["ships"].get(st["key"]) if st["key"] else None
    st["fee"] = 0 if not sh else (0 if (sh.get("free_over") is not None and st["sub"] >= sh["free_over"]) else sh["fee"])
    st["free_over"] = sh.get("free_over") if sh else None
parts = sum(s["sub"] for s in stores.values())
ship = sum(s["fee"] for s in stores.values())
assert parts + ship == 731485, parts + ship

order = sorted(stores.values(), key=lambda s: -s["sub"])
blocks = []
for st in order:
    rows = []
    for it, q, u, a in sorted(st["rows"], key=lambda r: -r[3]):
        link = f'<a href="{E(it["url"])}" target="_blank" rel="noopener">열기</a>' if it.get("url", "").startswith("http") else ""
        rows.append(f'<tr><td><span class="nm">{E(it.get("t") or it["n"])}</span><span class="g">{E(it.get("g") or "")}</span></td>'
                    f'<td class="num">{W(q)}</td><td class="num">{W(u)}</td><td class="num">{W(a)}</td><td>{link}</td></tr>')
    rule = ""
    if st["free_over"]:
        rule = f'{W(st["free_over"])}원 이상 무료'
    fee_txt = "무료" if st["fee"] == 0 else f'{W(st["fee"])}원'
    blocks.append(
        f'<section class="store"><header><h3>{E(st["name"])}</h3><span class="meta">{len(st["rows"])}품목 · 부품 {W(st["sub"])}원 · 배송비 {fee_txt}'
        f'{(" (" + rule + ")") if rule else ""}</span></header>'
        f'<div class="tw"><table><thead><tr><th>품목</th><th class="num">수량</th><th class="num">단가</th><th class="num">금액</th><th>판매 페이지</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></section>')

owned_li = "".join(f'<li>{E(it.get("t") or it["n"])}</li>' for it in owned)
CSS = r"""
#p-buy .tot{display:flex;flex-wrap:wrap;gap:8px 24px;align-items:baseline;background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 16px;margin:6px 0 16px}
#p-buy .tot b{font-family:var(--mono);font-size:26px;font-weight:500;font-variant-numeric:tabular-nums}
#p-buy .tot span{color:var(--ink-2);font-size:13.5px}
#p-buy .stores{display:flex;flex-direction:column;gap:14px}
#p-buy .store{background:var(--card);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
#p-buy .store header{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--rule)}
#p-buy .store h3{margin:0;font-size:15.5px}
#p-buy .store .meta{font-size:12.5px;color:var(--ink-2);font-variant-numeric:tabular-nums}
#p-buy .tw{overflow-x:auto}
#p-buy table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed;min-width:520px}
#p-buy th:nth-child(2),#p-buy td:nth-child(2){width:56px}#p-buy th:nth-child(3),#p-buy td:nth-child(3){width:84px}#p-buy th:nth-child(4),#p-buy td:nth-child(4){width:96px}#p-buy th:nth-child(5),#p-buy td:nth-child(5){width:84px}
#p-buy th{font-size:11.5px;color:var(--ink-3);font-weight:500;text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);white-space:nowrap}
#p-buy td{padding:6px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
#p-buy tr:last-child td{border-bottom:0}
#p-buy .num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
#p-buy .nm{display:block}
#p-buy .g{display:block;font-size:11.5px;color:var(--ink-3)}
#p-buy details{margin-top:16px;background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:8px 14px}
#p-buy details summary{cursor:pointer;font-weight:600;font-size:14px}
#p-buy details ul{columns:2;column-gap:28px;font-size:13px;color:var(--ink-2);margin:8px 0 4px;padding-left:18px}
@media (max-width:620px){#p-buy details ul{columns:1}}
"""
section = f'''<section class="page" id="p-buy" hidden>
<h2>구매 목록</h2>
<p class="lede">실제로 살 부품만 판매처별로 모았습니다. 이미 가진 부품과 예비는 뺐고, 배송비는 판매처마다 남은 주문액으로 계산했습니다. 품목을 켜고 끄거나 수량을 바꾸려면 <a href="{FINAL_URL}" target="_blank" rel="noopener">최종 재료 페이지</a>에서 고칩니다(사진·규격·쓰는 위치 도면도 그곳에 있습니다).</p>
<div class="tot"><b>{W(parts + ship)}원</b><span>부품 {W(parts)}원 ({sum(len(s["rows"]) for s in order)}품목) + 배송비 {W(ship)}원 · 판매처 {len(order)}곳</span></div>
<div class="stores">{"".join(blocks)}</div>
<details><summary>가진 것으로 쓰는 부품·공구 ({len(owned)}가지, 사지 않음)</summary><ul>{owned_li}</ul></details>
</section>'''
open(os.path.join(HERE, "buylist.html"), "w", encoding="utf-8").write(f"<style>{CSS}</style>\n{section}\n")
print("buylist.html", parts + ship, "stores", len(order), "owned", len(owned))
