"""Build src/summary.html: the '한눈에 보기' tab of the Toccata v4 merged artifact.

Cost numbers come from the user's real purchase list (최종 재료 page, artifact 9CJ3HwhbhoodCAui94g28n):
the built page data in hardware/bom/final-bom/site/index.html + the user's saved choices (db state/main, copy
passed as argv[1]).  Design numbers are the settled values of 2026-10-02 (sources listed in the tab itself).
usage: python3 build_summary.py <state_main.json>
"""
import html
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
FB = os.path.join(REPO, "hardware", "bom", "final-bom", "site", "index.html")
FULL_LIST = 1134177          # 전체 구매 목록 xlsx (가진 부품·공구·예비 포함), 10/2
FINAL_URL = "https://claude.ai/artifact/9CJ3HwhbhoodCAui94g28n"

page = open(FB, encoding="utf-8").read()
D = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
S = json.load(open(sys.argv[1]))


def unit_at(it, q):
    u = it["unit"]
    for mq, up in it.get("tiers") or []:
        if q >= mq:
            u = up
    return u


groups, gcount, per = defaultdict(int), defaultdict(int), {}
parts = n = 0
for it in D["items"]:
    if not S["on"].get(it["id"], it["on"]):
        continue
    q = S["qty"].get(it["id"], it["qty"])
    a = unit_at(it, q) * q
    parts += a
    n += 1
    groups[it.get("g") or "기타"] += a
    gcount[it.get("g") or "기타"] += 1
    k = it.get("sk") or "_" + it["store"]
    p = per.setdefault(k, {"sub": 0, "key": it.get("sk"), "store": it["store"], "n": 0})
    p["sub"] += a
    p["n"] += 1
ship_rows = []
for k, p in per.items():
    sh = D["ships"].get(p["key"]) if p["key"] else None
    fee = 0
    if sh:
        fee = 0 if (sh.get("free_over") is not None and p["sub"] >= sh["free_over"]) else sh["fee"]
    name = p["key"] or k.lstrip("_")
    ship_rows.append((name, p["sub"], fee, p["n"]))
ship = sum(r[2] for r in ship_rows)
total = parts + ship
assert total == 731485, total   # 10/2 v7 page + db state v43

W = lambda v: f"{v:,}"
E = html.escape

# ---------------------------------------------------------------- cost bars (one series: magnitude by group)
gs = sorted(((g, v) for g, v in groups.items() if v > 0), key=lambda x: -x[1])
vmax = gs[0][1]
bars = []
for g, v in gs:
    pct = v / vmax * 100
    share = v / parts * 100
    bars.append(
        f'<div class="bar" title="{E(g)}: {W(v)}원 · 부품의 {share:.1f}% · {gcount[g]}품목">'
        f'<span class="bl">{E(g)}</span>'
        f'<span class="bt"><span class="bf" style="width:{pct:.2f}%"></span></span>'
        f'<span class="bv num">{W(v)}<small>원</small></span></div>')
paid = sorted([r for r in ship_rows if r[2] > 0], key=lambda r: -r[2])
free = sorted([r for r in ship_rows if r[2] == 0 and r[1] > 0], key=lambda r: -r[1])
ship_tr = "".join(f'<tr><td>{E(nm)}</td><td class="num">{W(sub)}</td><td class="num">{W(fee)}</td></tr>' for nm, sub, fee, _ in paid)
free_names = " · ".join(E(r[0]) for r in free)

# ---------------------------------------------------------------- page
SPEC = [
    ("건반", "88건반", "옥타브 모듈 7개 + 끝 부속 2개"),
    ("본체 크기", "1254 × 342.5 mm", "건반 뒤 뒷바 깊이 130.5 mm"),
    ("높이", "z72.85 · z144.65", "건반·가운데 윗면 · 스피커 윗면 (mm)"),
    ("누르는 힘", "51.9 / 51.0 g", "백건 / 흑건, 연타 16.3 / 18.8 Hz"),
    ("화면", "7인치 1024×600", "25° 세움, 접으면 z78~95"),
    ("전력", "평균 16~20 W", "순간 54.4 W · 보조배터리 3.2~4.0시간"),
]
spec_html = "".join(f'<div class="kv"><span class="k">{E(a)}</span><b class="v">{E(b)}</b><span class="d">{E(c)}</span></div>' for a, b, c in SPEC)

PARTS = [
    ("action", "건반 액션 · W1+ r4.5", "dwg/d01_white_D_side.svg", "흰건반 D 옆 단면",
     ["짧은 시소 건반이 Ø4 강철 봉 위에서 돌고, 꼬리가 무게 레버(SS400 9×19×40, MS 폴리머 접착)를 들어 올립니다.",
      "되돌림은 레버 무게 + 미스미 비틀림 스프링 C-UA90R5-3-0.5(다리 22.3 / 8.0, 짧은 다리 가둠 홈).",
      "누르는 힘 백 51.9 g · 흑 51.0 g, 올라오는 힘 42.8 / 40.8 g, 연타 16.3 / 18.8 Hz. 검증 45개 통과."],
     [("#design", "01 건반 액션 구조"), ("#drawings", "02 건반 도면"), ("#check", "03 남은 위험")]),
    ("body", "본체 · L2 한 몸 뒷바", "rear/R02_rear_left.png", "뒤 왼쪽 3/4 렌더",
     ["뒷바가 건반 모듈 바로 뒤(틈 2 mm)에 붙어 전체 깊이가 447 → 342.5 mm로 줄었습니다.",
      "가운데 유닛 윗면이 건반과 같은 z72.85로 평평하고, 선은 모두 닫힌 통로(y212~241)와 앞 공간 안으로 지납니다.",
      "합판은 오꾸메 400×1200 한 장, 뒤 래치 없음. 예비 건반은 따로 출력한 상자에 보관합니다(R29, 10/2)."],
     [("#rear", "08 뒷부분 도면"), ("#cad", "07 CAD 모델")]),
    ("speaker", "스피커 · 앞판 40°", "rear/D02_speaker_section.png", "D02 스피커 단면",
     ["4인치 CW-100B25 2개, 밀폐 상자 안 부피 2.16 L, 앞판을 수평에서 40° 눕혀 연주자 귀 쪽(17° 차이)을 봅니다.",
      "Qtc 1.13(흡음솜 넣으면 1.08), 콘 아래 끝 27° 소리 길이 건반 모서리 위 3.50 mm로 지나갑니다.",
      "자석에서 가장 가까운 홀센서까지 228.5 mm(기준 100 mm). TPA3110 앰프, 저음 차단 약 93 Hz."],
     [("#rear", "08 뒷부분 도면 D02")]),
    ("touch", "터치스크린 · 3판", "rear/D05_touchscreen.png", "D05 터치스크린",
     ["Waveshare 7-DSI-TOUCH-C(7인치 가로 1024×600, DSI). 가운데 뚜껑에 25° 기울여 세우고 받침다리 1개로 받칩니다.",
      "경첩 축 y226.55 · z81.35라 어느 각도에서도 건반 모듈 위로 넘어가지 않습니다(가장 앞 y216.0). 접으면 z78~95.",
      "리본 22핀 300 mm(쓰는 길이 254 mm), 전원은 Pi 헤더 2·6번에서 약 2.15 W."],
     [("#rear", "08 뒷부분 도면 D05")]),
    ("elec", "전자부 · 회로 개정 C", "sch/SCH-01_system.svg", "SCH-01 시스템 연결도",
     ["건반마다 홀센서 DRV5055(모두 89개) → 모듈마다 RP2040-Zero + 16채널 먹스 → USB 허브 → Raspberry Pi 5(FluidSynth).",
      "USB-C PD 20 V → 퓨즈 → 스위치 → 5.1 V 강압. 벽 충전기 또는 보조배터리(65 W PD)로 씁니다.",
      "회로도 9장, 연결 검사 오류 0. 개정 C(10/1)에서 화면 연결 △16을 더했습니다."],
     [("#circuit", "06 회로도")]),
]
cards = []
for pid, title, img, alt, lines, links in PARTS:
    lk = " ".join(f'<a class="go" href="{h}">{E(t)} →</a>' for h, t in links)
    li = "".join(f"<li>{E(x)}</li>" for x in lines)
    cards.append(f'<article class="part" id="sum-{pid}"><figure><img src="{img}" alt="{E(alt)}" loading="lazy"></figure>'
                 f'<div class="pt"><h3>{E(title)}</h3><ul>{li}</ul><p class="links">{lk}</p></div></article>')

NEXT = [
    ("주문", "지금", "최종 재료 목록대로 주문합니다. 해외에서 오는 화면(10/15~22 도착 예상)과 10/26에 출하되는 스피커 결합 인서트(반품 불가)를 먼저 넣습니다."),
    ("단계 0 시험", "10월", "시편 34개와 공구 4개를 먼저 출력합니다. 시험 순서는 1(패드 반발) → 3a(윗판 굽힘) → 20(접착)·21(첫 모듈 정하중)·8(스프링 토크)입니다."),
    ("출력·조립", "10~11월", "건반 액션 7 모듈과 뒷바·스피커·화면 출력물을 뽑고 모듈부터 조립합니다. 출력용 STL은 hardware/mechanical/cad/stl/print에 있습니다."),
    ("통합·시연", "11/16~12/14", "본체·전자부·소리·터치 메뉴를 합치고 리듬게임 MVP를 Pi 5로 옮깁니다. 시연은 12/14 주입니다."),
]
next_html = "".join(f'<li><span class="when">{E(w)}</span><b>{E(t)}</b><span class="what">{E(d)}</span></li>' for t, w, d in NEXT)
CHECK = ["화면 뒤 DSI 커넥터 방향(반대면 받침을 좌우로 뒤집고 A형 리본을 씀)과 M2.5 구멍 깊이",
         "보조배터리 USB-C 포트 중심이 바닥에서 15.5 mm 이상인지(NC888 꺾인 머리)",
         "허브 DC 플러그가 잭 면에서 32 mm 안인지(넘으면 ㄱ자 플러그를 따로 삼)",
         "업스톱 패드 PORON 두께: 목록대로 5T면 stl/print 그대로(패드 바가 5T용), 6T를 사면 stl/print_extra의 6T용 패드 바로 바꿔 뽑음",
         "스피커 결합 인서트 구멍은 자투리 판에 Ø5.8부터 시험(헐거우면 Ø5.5)"]
check_html = "".join(f"<li>{E(x)}</li>" for x in CHECK)

CSS = r"""
#p-summary{--sum-bar:var(--blue);--sum-track:var(--tint-blue)}
#p-summary .lead{max-width:68ch;color:var(--ink-2);margin:4px 0 14px}
#p-summary .hero{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);gap:16px;align-items:start;margin-bottom:22px}
@media (max-width:860px){#p-summary .hero{grid-template-columns:minmax(0,1fr)}}
#p-summary .hero figure{margin:0;background:var(--card);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
#p-summary .hero figure img{display:block;width:100%;height:auto;background:#f6f7f9}
#p-summary .hero figcaption{font-size:12.5px;color:var(--ink-3);padding:8px 12px}
#p-summary .side{display:flex;flex-direction:column;gap:12px;min-width:0}
#p-summary .money{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:14px 16px}
#p-summary .money .lab{font-size:12px;letter-spacing:.04em;color:var(--ink-3)}
#p-summary .money .big{font-family:var(--mono);font-size:34px;line-height:1.15;font-weight:500;color:var(--ink);font-variant-numeric:tabular-nums}
#p-summary .money .big small{font-size:16px;margin-left:2px;color:var(--ink-2)}
#p-summary .money .brk{font-size:13px;color:var(--ink-2)}
#p-summary .money .note{font-size:12.5px;color:var(--ink-3);margin-top:6px}
#p-summary .specs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
#p-summary .kv{background:var(--card);padding:10px 12px;display:flex;flex-direction:column;gap:1px;min-width:0}
#p-summary .kv .k{font-size:11.5px;color:var(--ink-3);letter-spacing:.03em}
#p-summary .kv .v{font-size:16px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
#p-summary .kv .d{font-size:12px;color:var(--ink-2)}
#p-summary h3.sec{font-size:16px;margin:26px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--ink);text-wrap:balance}
#p-summary .parts{display:flex;flex-direction:column;gap:12px}
#p-summary .part{display:grid;grid-template-columns:280px minmax(0,1fr);gap:16px;background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px}
@media (max-width:760px){#p-summary .part{grid-template-columns:minmax(0,1fr)}}
#p-summary .part figure{margin:0;background:#fff;border:1px solid var(--rule);border-radius:8px;overflow:hidden;align-self:start}
#p-summary .part figure img{display:block;width:100%;height:auto;max-height:220px;object-fit:contain;background:#fff}
#p-summary .part h3{font-size:15px;margin:2px 0 6px}
#p-summary .part ul{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:3px;font-size:13.5px;color:var(--ink-2);max-width:72ch}
#p-summary .part .links{margin:8px 0 0;display:flex;flex-wrap:wrap;gap:8px}
#p-summary a.go{font-size:12.5px;text-decoration:none;border:1px solid var(--rule-2);border-radius:999px;padding:2px 10px;color:var(--blue-ink)}
#p-summary a.go:hover{border-color:var(--blue)}
#p-summary .cost{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px;align-items:start}
@media (max-width:860px){#p-summary .cost{grid-template-columns:minmax(0,1fr)}}
#p-summary .bars{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
#p-summary .bars .cap{font-size:12.5px;color:var(--ink-3)}
#p-summary .bar{display:grid;grid-template-columns:92px minmax(0,1fr) 96px;gap:10px;align-items:center;font-size:13px}
#p-summary .bar .bl{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#p-summary .bar .bt{height:12px;background:var(--sum-track);border-radius:0 4px 4px 0;overflow:hidden}
#p-summary .bar .bf{display:block;height:100%;background:var(--sum-bar);border-radius:0 4px 4px 0}
#p-summary .bar:hover .bf{filter:brightness(1.12)}
#p-summary .bar .bv{text-align:right;color:var(--ink);font-variant-numeric:tabular-nums}
#p-summary .bar .bv small{font-size:11px;color:var(--ink-3);margin-left:1px}
#p-summary .shipbox{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 14px;min-width:0}
#p-summary .shipbox .tw{overflow-x:auto}
#p-summary .shipbox table{width:100%;border-collapse:collapse;font-size:13px}
#p-summary .shipbox th{text-align:left;font-weight:500;color:var(--ink-3);font-size:12px;border-bottom:1px solid var(--rule);padding:4px 6px}
#p-summary .shipbox td{border-bottom:1px solid var(--rule);padding:4px 6px}
#p-summary .shipbox .num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
#p-summary .shipbox tfoot td{font-weight:600;border-bottom:0}
#p-summary .shipbox .free{font-size:12.5px;color:var(--ink-2);margin-top:8px}
#p-summary .next{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0;background:var(--card);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
#p-summary .next li{display:grid;grid-template-columns:110px 120px minmax(0,1fr);gap:12px;padding:10px 14px;border-top:1px solid var(--rule);font-size:13.5px}
#p-summary .next li:first-child{border-top:0}
@media (max-width:640px){#p-summary .next li{grid-template-columns:minmax(0,1fr)}}
#p-summary .next .when{font-family:var(--mono);font-size:12.5px;color:var(--blue-ink)}
#p-summary .next .what{color:var(--ink-2)}
#p-summary .checks{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:4px;font-size:13.5px;color:var(--ink-2);max-width:80ch}
#p-summary .src{font-size:12.5px;color:var(--ink-3);margin-top:18px;max-width:90ch}
#p-summary .num{font-family:var(--mono);font-variant-numeric:tabular-nums}
"""

shares = ", ".join(f"{E(g)} {v / parts * 100:.0f}%" for g, v in gs[:3])
section = f'''<section class="page" id="p-summary" hidden>
<h2>Toccata 한눈에 보기 (2026-10-02 확정 설계)</h2>
<p class="lead">3D 프린터로 만드는 88건반 디지털 피아노입니다. 건반 밑 홀센서가 누르는 속도를 재고, Raspberry Pi 5가 소리를 내며, 본체에 내장 스피커 2개와 7인치 터치스크린이 있습니다. 이 탭은 지금 설계와 실제 구매 비용을 한 번에 보여 주고, 자세한 내용은 각 탭으로 이어집니다.</p>
<div class="hero">
  <figure><img src="rear/R01_front.png" alt="Toccata 앞 3/4 렌더: 88건반, 양 끝 스피커, 가운데 7인치 화면"><figcaption>앞 3/4 (쓰는 상태). 건반 모듈 7개 + 끝 부속, 양 끝 스피커(앞판 40°), 가운데 터치스크린 25°. CAD 렌더 R01</figcaption></figure>
  <div class="side">
    <div class="money">
      <div class="lab">실제 구매 금액 (가진 부품·예비 뺌, 배송비 포함)</div>
      <div class="big">{W(total)}<small>원</small></div>
      <div class="brk">부품 {W(parts)}원 ({n}품목) + 배송비 {W(ship)}원</div>
      <div class="note">최종 재료 목록 기준입니다. 품목별로 켜고 끄려면 <a href="{FINAL_URL}" target="_blank" rel="noopener">최종 재료 페이지</a>에서 고칩니다. 판매처별 목록은 05 구매 목록 탭에 있습니다. 가진 부품·공구·예비까지 모두 넣은 전체 목록은 {W(FULL_LIST)}원(저장소 엑셀)입니다.</div>
    </div>
    <div class="specs">{spec_html}</div>
  </div>
</div>

<h3 class="sec">설계 구성</h3>
<div class="parts">{"".join(cards)}</div>

<h3 class="sec">비용 — 무엇에 쓰나 (실제 구매 목록)</h3>
<div class="cost">
  <div class="bars"><div class="cap">묶음별 부품값 (배송비 뺌). 많이 드는 곳: {shares}</div>{"".join(bars)}</div>
  <div class="shipbox"><div class="cap" style="font-size:12.5px;color:var(--ink-3);margin-bottom:6px">배송비가 붙는 판매처</div>
    <div class="tw"><table><thead><tr><th>판매처</th><th class="num">주문액</th><th class="num">배송비</th></tr></thead>
    <tbody>{ship_tr}</tbody><tfoot><tr><td>합계</td><td></td><td class="num">{W(ship)}</td></tr></tfoot></table></div>
    <p class="free">무료 배송: {free_names}. 엘레파츠는 예비 부품 1,386원을 더해 무료 배송 기준(66,000원)을 넘겼습니다.</p>
  </div>
</div>

<h3 class="sec">다음 할 일</h3>
<ol class="next">{next_html}</ol>

<h3 class="sec">부품을 받으면 먼저 확인할 것</h3>
<ul class="checks">{check_html}</ul>

<p class="src">원본: 설계서 docs/01-hardware-design.md (v4 확정본) · 설계 기준 hardware/mechanical/sound-requirements.md (R1~R32, D1~D24) · 건반 액션 hardware/mechanical/key-action-v4 (r4.5) · 본체·스피커 hardware/mechanical/cad/spec/body_L2.json · 터치스크린 hardware/mechanical/touchscreen/rev3 · 회로 hardware/pcb (개정 C) · 재료 hardware/bom (최종 재료 페이지 = 실제 구매). 좌표는 mm, x 가로(0 = A0 왼쪽 끝), y 흰건반 앞 끝에서 뒤로, z 책상에서 위로.</p>
</section>'''

out = f"<style>{CSS}</style>\n{section}\n"
open(os.path.join(HERE, "summary.html"), "w", encoding="utf-8").write(out)
print("summary.html", len(out), "bytes; total", total, "parts", parts, "ship", ship, "items", n)
