#!/usr/bin/env python3
"""기존 아티팩트 'Toccata 제작 도면집'(A–D) + 제작 설계서 v3(절감안 포함) → 한 아티팩트 페이지"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
ART = sys.argv[1]  # 저장된 아티팩트 HTML
OUT = os.path.join(HERE, 'toccata-drawings.html')

art = open(ART, encoding='utf-8').read()
v3 = open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(V3, 'toccata-build-v3.html'), encoding='utf-8').read()
FR = json.load(open(os.path.join(V3, 'cost', 'fragment.json')))

# ---------- 1. 아티팩트: 게시 골격 제거 ----------
art = art[art.index('<title>'):]
art = art[:art.rindex('</body>')]

# ---------- 2. v3: CSS·본문·스크립트 분리 ----------
v3_css = ''.join(re.findall(r'<style>(.*?)</style>', v3, re.S))
v3_body = v3[v3.index('<div class="wrap">') + len('<div class="wrap">'):v3.rindex('</div><script>')]
v3_js = re.search(r'<script>(.*?)</script>', v3[v3.rindex('</div><script>'):], re.S).group(1)


def scope_css(css):
    """v3 CSS를 .v3 아래로 한정. :root 토큰과 다크 토큰 블록은 버린다(아티팩트 토큰에 연결)."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out = []
    i = 0
    n = len(css)
    while i < n:
        j = css.find('{', i)
        if j < 0:
            break
        sel = css[i:j].strip()
        if sel.startswith('@'):
            # 중괄호 짝 맞춰 블록 전체
            depth, k = 1, j + 1
            while depth and k < n:
                depth += {'{': 1, '}': -1}.get(css[k], 0)
                k += 1
            inner = scope_css(css[j + 1:k - 1])
            if inner.strip():
                out.append(sel + '{' + inner + '}')
            i = k
            continue
        k = css.find('}', j)
        body = css[j + 1:k]
        i = k + 1
        sels = []
        for s in sel.split(','):
            s = s.strip()
            if not s or s.startswith(':root') or s == 'html':
                continue
            if s == 'body':
                sels.append('.v3')
            elif s == '*':
                sels.append('.v3 *')
            elif s.startswith('.js '):
                sels.append('.js .v3 ' + s[4:])
            elif s.startswith('.v3'):
                sels.append(s)
            else:
                sels.append('.v3 ' + s)
        if sels:
            out.append(','.join(sels) + '{' + body + '}')
    return ''.join(out)


V3_TOKENS = '''
.v3{--bg:var(--paper);--sur:var(--card);--ink2:var(--ink-2);--mut:var(--ink-3);--acc:var(--blue);--acc-bg:var(--tint-blue);
--crit:var(--felt);--steel:var(--ink-3);--bed:color-mix(in srgb,var(--ink) 13%,var(--card));
font-family:var(--sans);background:var(--paper);color:var(--ink)}
.v3 [id]{scroll-margin-top:72px}
.v3>h2:first-child,.v3>header+*{margin-top:0}
.v3>h2:first-child{border-top:0;padding-top:0}
.v3 .mast h2.v3t{font-size:clamp(24px,3.2vw,34px);line-height:1.15;margin:0;padding:0;border:0;font-weight:700;letter-spacing:-.01em}
.v3 .chip{color:var(--card)}
.v3 .cd .tabs{position:static}
.v3 .drw{border-radius:10px}
.v3 .pc-card{border-radius:10px}
.v3 details{border-radius:8px}
.v3 .callout{border-radius:0 8px 8px 0}
'''
css = scope_css(v3_css) + V3_TOKENS

# ---------- 3. v3 본문: id 접두어, 외부 상대 링크 정리 ----------
body = v3_body
body = re.sub(r'\sid="([^"]+)"', lambda m: f' id="v3-{m.group(1)}"', body)
body = re.sub(r'href="#([^"]+)"', lambda m: f'href="#v3-{m.group(1)}"', body)
body = body.replace('url(#', 'url(#v3-')
body = re.sub(r'<a href="(\.\./\.\./[^"]+|toccata-[\w-]+\.html)"[^>]*>(.*?)</a>', r'<span class="mono">\2</span>', body)
body = body[:body.rindex('<footer')] if '<footer' in body else body
body = body.replace('<h1>', '<h2 class="v3t">', 1).replace('</h1>', '</h2>', 1)
js = (v3_js.replace("'tier-'+k", "'v3-tier-'+k").replace("'#tier-'+b.dataset.k", "'#v3-tier-'+b.dataset.k")
      .replace(".replace('#tier-','')", ".replace('#v3-tier-','')"))
assert "'v3-tier-'+k" in js and "#v3-tier-" in js

# 장 단위로 자르기
head = body[:body.index('<h2 id="v3-sum">')]
secs = {}
for m in re.finditer(r'<h2 id="v3-([\w-]+)">', body):
    secs[m.group(1)] = m.start()
order = sorted(secs, key=secs.get)
chunk = {}
for a, b in zip(order, order[1:] + [None]):
    chunk[a] = body[secs[a]:secs[b] if b else len(body)]

PAGES = [
    ('v3', 'v3 개요', head, ['sum', 'video', 'concept']),
    ('v3dwg', 'v3 도면·치수', '', ['dwg', 'dims']),
    ('v3spec', 'v3 설계 상세', '', ['mech', 'elec', 'calc', 'print']),
    ('v3audio', 'v3 오디오(R25)', '', ['audio']),
    ('v3body', 'v3 본체 구조(R26)', '', ['body']),
    ('v3bom', 'v3 부품표·비용', '', ['use', 'bom', 'cons', 'tools', 'opt', 'budget', 'order', 'check', 'subst']),
    ('v3cost', 'v3 절감안', '', ['cost']),
    ('v3asm', 'v3 조립·검토', '', ['asm', 'risk', 'req', 'chg', 'meth']),
]
used = [s for _, _, _, ss in PAGES for s in ss]
assert sorted(used) == sorted(order), (set(order) ^ set(used))
pages_html = ''.join(
    f'<section class="page" id="p-{pid}" data-page="{pid}" hidden><div class="v3">{pre}{"".join(chunk[s] for s in ss)}</div></section>\n'
    for pid, _, pre, ss in PAGES)

# ---------- 4. 아티팩트 쪽 수정 ----------
def rep(a, b, cnt=1):
    global art
    assert art.count(a) == cnt, (a[:80], art.count(a))
    art = art.replace(a, b)


rep('<meta name="description" content="88건반 3D 프린팅 피아노의 건반 액션 4가지 설계 도면과 부품·비용 조사">',
    '<meta name="description" content="88건반 3D 프린팅 피아노 Toccata의 v3 리프 모듈 설계·부품표·절감안과, 건반 액션 4가지(A–D) 도면·부품·비용">')
rep('<p class="sub">건반 액션 4가지(A–D)의 실제 치수 도면, 필요한 부품 전부의 사양·가격·구매처, 방식별 총비용.</p>',
    '<p class="sub">최신 v3 설계(리프 한 장으로 움직이는 옥타브 모듈, 100만원 이내)의 도면·부품표·절감안과, 앞서 비교한 건반 액션 4가지(A–D)의 도면·부품·비용.</p>')
nav_v3 = ''.join(f'<a href="#{pid}" data-to="{pid}"><span class=tag>v3</span>{lab[3:]}</a>' for pid, lab, _, _ in PAGES)
rep('<a href="#overview" data-to="overview">개요</a><a href="#common"',
    f'<a href="#overview" data-to="overview">개요</a><span class="sep"></span>{nav_v3}<span class="sep"></span><a href="#common"')

T = {t['key']: t for t in FR['tiers']}
_B = json.load(open(os.path.join(V3, 'bom_all.json')))
_TB = sum(l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0) for l in _B['base'])
_ver = re.search(r'<div class="ver"><b>([\d,]+)원</b>기본 구성\(소모품 제외\)<br>.*?<br>(v3\.\d+) — ([^(<]+)', v3)
_TAG = 'R24~R29 반영'
if _ver:  # v3.2 이후: 부품표 JSON이 아니라 설계서 머리의 합계를 쓴다
    _TB = int(_ver.group(1).replace(',', ''))
    _TAG = 'R24~R29 · ' + _ver.group(3).strip()
kf = [(f'{_TB:,}원', f'v3 기본 구성(소모품 제외, {_TAG})'), (f'{T["T2"]["base"]:,}원', '절감안 T2 · 요구사항 유지'),
      (f'{T["T4"]["base"]:,}원', '최저선 T4 · PC + 헤드폰'), ('1254 × 410', '본체(mm) · 뒷바까지 직사각형(R27)'),
      ('약 5시간', '보조배터리 20,000 mAh로 무선 연주(R28)'), ('스피커 2개', '오디오(R25): USB 동글 + TPA3110 + CW-100B25'),
      ('파트 5종', '모듈·끝 부속·스피커·가운데 유닛·페달 따로 보관(R26)'), ('댐퍼 1개', '페달(R24): 스위치 페달 홀센서 개조')]
v3_block = f'''<div class="card v3intro">
<div class="eyebrow">최신 설계 · v3 · R1–R29 기준</div>
<h3 style="margin:6px 0 6px">리프 한 장으로 움직이는 옥타브 모듈</h3>
<p class="muted" style="margin:0 0 12px">백건 7개와 흑건 5개를 각각 한 덩어리로 출력하고, 건반 뒤의 얇은 판(리프)이 회전축과 복귀 스프링을 겸합니다. 도~시 모듈 7개가 모두 같고 도브테일로 끼워 탈부착합니다. 본체 뒤는 뒷바(스피커 파트 2개 + 건반 보관함·CU·보조배터리 칸이 든 가운데 유닛)로 채워 1254 × 410 mm 직사각형이 됐고, 파트마다 떼어 따로 보관하며, USB-C 입력 하나로 벽 충전기나 보조배터리를 씁니다(R26~R29). 좌우 스피커 2개와 앰프까지 넣은 기본 구성이 {_TB:,}원으로 100만원 안에 들어가며, 요구사항을 모두 지키면서 더 줄이는 절감안도 함께 정리했습니다.</p>
<div class="kfs">{''.join(f'<div class="kf"><b>{v}</b><span>{s}</span></div>' for v, s in kf)}</div>
<div class="v3links">{''.join(f'<a href="#{pid}">{lab} →</a>' for pid, lab, _, _ in PAGES)}</div>
</div>
<div class="note warn"><b>A–D와 v3는 서로 다른 설계입니다.</b> A–D는 R1–R16 기준(탈부착·100만원·단순 구조·컴플라이언트 조건이 생기기 전)이고, v3는 R1–R29 기준(R24: 페달은 댐퍼 하나, R25: 스피커 2개·싼 앰프, R26~R29: 파트별 분리·직사각형 본체·보조배터리·건반 보관함)입니다. 센서 열 위치(A–D y110, v3 y67)·센서 품번(DRV5055A3 / A2)·케이스 치수가 다르니 도면 값을 섞어 쓰지 마세요. A–D의 총비용(223만~235만원)도 예산 조건 전의 계산입니다.</div>
<h3>앞서 비교한 건반 방식 4가지(A–D)</h3>
'''
rep('<h2>개요 · 4가지 건반 방식과 총비용</h2>\n<p class="lede">', '<h2>개요 · v3 설계와 건반 방식 4가지</h2>\n' + v3_block + '<p class="lede">')

V3INTRO_CSS = '''
.v3intro{margin:4px 0 14px;border-color:var(--blue)}
.v3intro .kfs{margin:0 0 12px}
.v3links{display:flex;flex-wrap:wrap;gap:6px}
.v3links a{font-size:13px;text-decoration:none;border:1px solid var(--rule-2);border-radius:7px;padding:5px 10px;color:var(--ink)}
.v3links a:hover{border-color:var(--blue);color:var(--blue)}
'''
art = art.replace('</style>\n<header class="tb">', V3INTRO_CSS + css + '</style>\n<header class="tb">', 1)
assert V3INTRO_CSS in art

# v3 페이지를 개요 뒤에 넣는다
rep('</section><section class="page" id="p-common"', '</section>\n' + pages_html + '<section class="page" id="p-common"')

# 라우터 교체: 페이지 id가 아니면 그 id를 가진 요소의 페이지를 연다
old_router = art[art.index('  function show(){'):art.index("  show();\n")]
new_router = '''  function show(){
    const raw=decodeURIComponent((location.hash||'#overview').slice(1));
    let page=document.getElementById('p-'+raw.toLowerCase()), target=null;
    if(!page){ target=document.getElementById(raw); page=target&&target.closest('.page'); }
    if(!page) page=document.getElementById('p-overview');
    const id=page.dataset.page;
    pages.forEach(p=>{p.hidden=(p!==page)});
    links.forEach(a=>{ if(a.dataset.to===id) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current'); });
    const cur=links.find(a=>a.dataset.to===id); if(cur&&cur.scrollIntoView) cur.scrollIntoView({block:'nearest',inline:'nearest'});
    return target;
  }
  function reveal(t){
    if(!t) return false;
    if(t.classList.contains('tier')){ const b=document.querySelector('.v3 .tabs button[data-k="'+t.id.replace('v3-tier-','')+'"]'); if(b) b.click(); }
    for(let d=t.closest('details'); d; d=d.parentElement&&d.parentElement.closest('details')) d.open=true;
    requestAnimationFrame(()=>t.scrollIntoView({block:'start'}));
    return true;
  }
  window.addEventListener('hashchange',()=>{ if(!reveal(show())) window.scrollTo(0,0); });
  reveal(show());
'''
art = art.replace(old_router, new_router, 1)
art = art.replace("  window.addEventListener('hashchange',()=>{show();window.scrollTo(0,0)});\n  show();\n", '', 1)
assert "reveal(show());" in art and "{show();window.scrollTo(0,0)}" not in art

# v3 절감안 탭 스크립트
art = art.rstrip() + '\n<script>' + js + '</script>\n'
open(OUT, 'w', encoding='utf-8').write(art)
print(OUT, f'{len(art.encode()) / 1e6:.2f} MB', 'pages', len(re.findall(r'<section class="page"', art)))
ids = re.findall(r'\sid="([^"]+)"', art)
from collections import Counter
dup = [k for k, v in Counter(ids).items() if v > 1]
print('dup ids', dup[:10])
