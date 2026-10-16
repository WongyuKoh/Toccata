#!/usr/bin/env python3
"""wf.json(final) + bom_all.json + drawings.json + img/t_*.jpg → toccata-build-v3.html"""
import base64, html, json, os, re, sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'toccata-build-v3.html')
sys.path.insert(0, HERE)
from draw import DRAW_CSS  # noqa: E402

d = json.load(open(os.path.join(HERE, 'wf.json')))
F = d['final']
B = json.load(open(os.path.join(HERE, 'bom_all.json')))
DR = json.load(open(os.path.join(HERE, 'drawings.json')))
CSS0 = open(os.path.join(HERE, '..', 'report.css')).read()

# ---------- 조달 중 바뀐 용어(설계 본문·도면에 일괄 반영) ----------
TERMS = [
    ('final: ', ''),
    ('M3 대와셔 Ø9', 'M4 와셔(외경 9)'),
    ('Ø9 와셔', 'M4 와셔(외경 9)'),
    ('철 원판', '황동 원판'),
    ('태핑', '자가 탭'),
    ('부싱 크로스', '부싱 펠트'),
]


def fix(s):
    s = str(s or '')
    for a, b in TERMS:
        s = s.replace(a, b)
    return re.sub(r'(?<!파워)마스터', '초기안', s)


# 예산·필라멘트 계산은 최종 부품표 값으로 바꾼다
for c in F['calcs']:
    if c['name'].startswith('예산'):
        c['inputs'] = f'최종 부품표 기본 구성 {len(B["base"])}줄(9/24~25 가격·배송비 확인, R24~R29 반영), Σ(수량 × 단가 + 배송비), 같은 판매처 배송비는 한 줄에만'
        _gt = {}
        for _l in B['base']:
            _gt[_l['group']] = _gt.get(_l['group'], 0) + _l['qty'] * _l['unit_price_krw'] + (_l.get('shipping_krw') or 0)
        c['result'] = ' + '.join(f'{g} {v:,}원' for g, v in sorted(_gt.items(), key=lambda x: -x[1])) + f' = {sum(_gt.values()):,}원. 남는 예산 {1_000_000 - sum(_gt.values()):,}원'
        _cs = sum(l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0) for l in B['consumable'])
        _ts = sum(l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0) for l in B['tools'])
        c['conclusion'] = f'100만원 이하(R21). 소모품 {_cs:,}원과 공구 {_ts:,}원은 한도 밖. Pianoteq(188,200원)와 Pi 5 4GB(+97,900원)는 선택 항목(R25 이후에는 넣어도 한도 안).'
    if c['name'].startswith('필라멘트'):
        c['_fil'] = True  # 결과·결론은 R26 반영 뒤 출력 목록에서 다시 계산(아래 FIL_TXT)
for r in F['requirement_check']:
    if r['id'] == 'R21':
        _tb = sum(l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0) for l in B['base'])
        r['how'] = (f'소모품 제외 {_tb:,}원 ≤ 100만원(Pianoteq 제외, R24~R29 반영). 여유 {1_000_000 - _tb:,}원. '
                    '더 줄이는 방법은 §{{#cost}}에 있다.')

# ---------- R24: 페달은 댐퍼 하나만 (2026-09-24 사용자 결정) ----------
F['pedals'] = (
    '댐퍼(서스테인) 1개만 둔다(R24). 소스테누토·소프트 페달과 6.35 mm 잭은 두지 않는다. '
    '[페달] 듀로 피아노형 스위치 페달(L43)을 연다. 마이크로스위치 배선을 떼고, 발판 밑면 발끝 쪽에 예비 자석 Ø5×2(L21, S극 아래)를 순간접착제(C18)로 붙인다. '
    '바로 아래 바닥판에 예비 DRV5055(L20)를 만능기판 자투리(L23)에 표시면이 위로 오게 세워 붙이고, 센서 VCC–GND 옆에 100 nF(L26 예비)를 단다. '
    '간격은 눌렀을 때 약 4.5 mm, 뗐을 때 12 mm 이상으로 맞춘다(자기장 약 36 → 2.4 mT, 한계 ±44 mT 안). '
    '발판이 강철이면 자석이 붙고 자기장이 휘므로 조립 뒤 최대값이 44 mT 아래인지 확인하고, 넘으면 간격을 늘린다. 복귀 스프링·고무 바닥·발판은 완제품 그대로 쓴다. '
    '[배선] 3 m 3.5 mm 스테레오 케이블(L50)의 한쪽 플러그를 잘라 페달의 기존 케이블 구멍으로 넣고 팁 = 센서 출력, 링 = 3V3, 슬리브 = GND로 납땜한 뒤 케이블 타이로 당김을 막는다. '
    '다른 쪽은 I/O 판(가운데 유닛 CU 칸 뒤)의 PJ-313 잭(L15의 두 번째)에 꽂는다. '
    "[PED 보드] RP2040-Zero(GP14 = GND → 'Toccata PED'). 링 3V3 직렬 저항은 0 Ω(DRV5055 최소 3.0 V 유지), 팁 → 1 kΩ → GP26(100 nF). "
    '팁의 100 kΩ 풀 저항 반대쪽을 GP27로 구동해, 케이블을 뽑으면 최소값 아래로 떨어져 CC64가 0으로 남는다. '
    '[펌웨어] 부팅 때 최소·최대를 학습하고 건반과 같은 자기장 곡선 역함수로 선형화해 CC64를 0~127 연속값으로, 발을 떼면 정확히 0, ±2 이상 변할 때만 보낸다(D1, 하프페달). '
    '개조가 안 되면 원래 스위치를 되살려 켜짐·꺼짐 댐퍼로 쓴다. 기본 엔진인 FluidSynth는 어차피 64 기준 켜짐·꺼짐이다. 페달 ADC는 모듈 ADC와 별개라 건반 스캔에 영향이 없다.')
for _a, _b in [('서스테인: sleeve = GND, ring = 3V3(100 Ω)', '댐퍼(R24로 페달은 이것 하나): sleeve = GND, ring = 3V3(0 Ω, 페달 안 홀센서 급전)'),
               (' 소스테누토 GP2·소프트 GP3(1 kΩ 직렬, 내부 풀업, sleeve = GND).', ' 소스테누토·소프트 입력은 두지 않는다(R24).')]:
    assert _a in F['electronics'], _a
    F['electronics'] = F['electronics'].replace(_a, _b)
assert '페달 TRS 3' in F['control_unit']
F['control_unit'] = F['control_unit'].replace('페달 TRS 3', '댐퍼 페달 3.5 mm 잭 1(PJ-313)')
assert '페달 3개(멀티미터로 단자 확인)' in F['assembly'][11]
F['assembly'][11] = F['assembly'][11].replace('페달 3개(멀티미터로 단자 확인)', '댐퍼 페달 1개(홀센서 개조, 팁·링·슬리브를 멀티미터로 확인)')
_rc = []
for r in F['requirement_check']:
    if r['id'] == 'R3':
        r = dict(r, how='개조한 듀로 스위치 페달(홀센서) → CC64 0~127 연속값(하프페달), 뽑아도 0 유지. 페달은 댐퍼 하나(R24).')
    elif r['id'] == 'R6':
        r = dict(r, how=r['how'].replace('페달 3개', '댐퍼 페달(연속형)'))
    elif r['id'] == 'R7':
        r = dict(r, how=r['how'].replace('페달 3개를 모두 전송', '댐퍼 페달을 전송'))
    elif r['id'] == 'D5':
        r = dict(r, how='R24로 소스테누토·소프트 페달을 두지 않아 CC66·CC67 입력이 없다(처리 코드는 남겨도 무해). 선택 CC88은 그대로.')
    _rc.append(r)
    if r['id'] == 'R23':
        _rc.append({'id': 'R24', 'how': '댐퍼 페달 1개(L43 듀로 스위치 페달 홀센서 개조 + L50 3 m 신호선, 14,360원). 스위치 페달 2개와 6.35 mm 잭 5개를 뺐다(DP-10 구성 대비 −71,400원).'})
F['requirement_check'] = _rc

# ---------- R25: 스피커는 좌우 2개, 스피커·앰프는 싼 것으로 (2026-09-24 사용자 결정) ----------
from patch_r25 import apply_r25  # noqa: E402
apply_r25(F)
from patch_r26 import apply_r26  # noqa: E402
apply_r26(F)  # R26~R29: 뒷바·보조배터리·건반 보관함
_B25 = json.load(open(os.path.join(HERE, 'bom_all.before_r25.json')))
_sub25 = lambda l: l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0)
_o25 = {l['line_id']: l for l in _B25['base']}
_B26P = os.path.join(HERE, 'bom_all.before_r26.json')
_B25N = json.load(open(_B26P)) if os.path.exists(_B26P) else B  # R25 반영 직후(R26 이전) 부품표
_n25 = {l['line_id']: l for l in _B25N['base']}
AUD_IDS = sorted(i for i in set(_o25) | set(_n25) if (_sub25(_o25[i]) if i in _o25 else 0) != (_sub25(_n25[i]) if i in _n25 else 0))
AUD_OLD = sum(_sub25(_o25[i]) for i in AUD_IDS if i in _o25)
AUD_NEW = sum(_sub25(_n25[i]) for i in AUD_IDS if i in _n25)
BASE_R24 = sum(map(_sub25, _B25['base']))
for r in F['requirement_check']:
    if r['id'] == 'R25':
        r['how'] = (f'스피커는 좌우 2개(CW-100B25), 앰프는 XH-A232 한 대, DAC는 USB 동글. 서브·DAC2 Pro·AAmp60·릴레이를 뺐다. '
                    f'바뀐 줄 {len(AUD_IDS)}개가 {AUD_OLD:,}원 → {AUD_NEW:,}원(−{AUD_OLD - AUD_NEW:,}원). 자세한 비교는 §{{{{#audio}}}}.')


def esc(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def inline(s, fx=True):
    out = esc(fix(s) if fx else str(s or ''))
    out = re.sub(r'`([^`]+)`', r'<code>\1</code>', out)

    def link(m):
        url = m.group(0)
        tail = ''
        while url and url[-1] in '.,;:)]':
            tail = url[-1] + tail
            url = url[:-1]
        label = re.sub(r'^https?://(www\.)?', '', url)
        if len(label) > 48:
            label = label[:45] + '…'
        return f'<a href="{url}" rel="noopener">{label}</a>{tail}'

    return re.sub(r'(?<![="])https?://[^\s<>"\']+', link, out)


CIRC = '①②③④⑤⑥⑦⑧⑨⑩'


def paras(s, target=260):
    """긴 문단을 '다.' 경계에서 2~3문장씩 끊는다."""
    s = s.strip()
    if not s:
        return ''
    sents = re.split(r'(?<=다\.)\s+', s)
    out, buf = [], ''
    for x in sents:
        buf = (buf + ' ' + x).strip()
        if len(buf) >= target:
            out.append(buf)
            buf = ''
    if buf:
        out.append(buf)
    return ''.join(f'<p>{inline(p)}</p>' for p in out)


def circ_list(s):
    """①② 표시가 둘 이상이면 앞 문장 + 번호 목록으로."""
    idx = [i for i, ch in enumerate(s) if ch in CIRC]
    if len(idx) < 2:
        return paras(s)
    head = s[:idx[0]].strip()
    items = [s[a + 1:b].strip() for a, b in zip(idx, idx[1:] + [len(s)])]
    return (paras(head) if head else '') + '<ol class="circ">' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ol>'


def rich(s):
    """[소제목] 표시 → h5, 나머지는 번호 목록·문단."""
    s = fix(s)
    parts = re.split(r'\[([^\]\d][^\]]{1,18})\]\s*', s)
    html_ = circ_list(parts[0]) if parts[0].strip() else ''
    for i in range(1, len(parts), 2):
        html_ += f'<h5>{esc(parts[i])}</h5>' + circ_list(parts[i + 1])
    return html_


def table(head, rows, cls=''):
    th = ''.join(f'<th{(" class=" + chr(34) + c + chr(34)) if c else ""}>{h}</th>' for h, c in head)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def won(n):
    return f'{int(round(n)):,}'


def sub(l):
    return l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0)


def img_uri(lid):
    p = os.path.join(HERE, 'img', f't_{lid}.jpg')
    if not os.path.exists(p):
        return ''
    return 'data:image/jpeg;base64,' + base64.b64encode(open(p, 'rb').read()).decode()


# ---------- 부품 카드 ----------
def use_line(lid):
    u = USE.get(lid)
    if not u:
        return ''
    z = ZONES[u[0]]
    return f'<p class="use-line"><a href="#use-{lid}"><span class="zb sm">{ZNUM[u[0]]}</span>{esc(z[1])}</a> · {esc(u[1])}</p>'


def part_card(l, kind):
    lid = l['line_id']
    uri = img_uri(lid)
    store = esc(l.get('store') or '')
    url = esc(l.get('url') or '')
    ship = l.get('shipping_krw') or 0
    price_line = (f'<span class="mono">{l["qty"]} × {won(l["unit_price_krw"])}'
                  + (f' + 배송 {won(ship)}' if ship else '') + f' = <b>{won(sub(l))}원</b></span>')
    unit = f'<span class="mut"> · 구매 단위 {esc(l.get("purchase_unit") or "")}</span>' if l.get('purchase_unit') else ''
    specs = l.get('specs') or []
    kv = ''.join(f'<tr><th>{esc(s.get("k"))}</th><td>{inline(s.get("v"), False)}</td></tr>' for s in specs)
    extra = ''
    if l.get('design_ref'):
        extra += f'<p class="dref"><b>설계 위치</b> {inline(l["design_ref"], False)}</p>'
    if l.get('why'):
        extra += f'<p class="dref"><b>고른 이유</b> {inline(l["why"], False)}</p>'
    if l.get('check'):
        extra += f'<p class="dref"><b>검증 메모</b> {inline(l["check"], False)}</p>'
    flags = ''
    if not l.get('page_ok', True) or not l.get('image_ok', True):
        flags = '<span class="chip c-warn">링크 재확인</span> '
    img = (f'<a class="ph" href="{url}" rel="noopener" tabindex="-1"><img src="{uri}" alt="{esc(l["name"])} 제품 사진" loading="lazy"></a>'
           if uri else '<div class="ph noimg">사진 없음</div>')
    return f'''<article class="pc-card" id="{lid}">
{img}
<div class="pb">
<div class="pt"><span class="lid">{lid}</span> {flags}<b>{esc(l["name"])}</b></div>
<p class="role">{inline(l.get("role"), False)}</p>
{use_line(lid)}
<div class="buy">{price_line}{unit}<br><a href="{url}" rel="noopener">{store} ↗</a></div>
<details><summary>세부 스펙 {len(specs)}개 · 선정 근거</summary>
<table class="kv">{kv}</table>{extra}</details>
</div></article>'''


GROUP_ORDER = ['센서·MCU', '배선·납땜', '구조·체결', '페달', '제어·전원', '오디오', '소프트웨어']
GROUP_DESC = {
    '센서·MCU': '건반 위치를 재는 홀센서·자석과 모듈마다 USB-MIDI를 내는 RP2040-Zero, 아날로그 멀티플렉서, 칩 부품.',
    '배선·납땜': 'PCB 없이 손으로 납땜하는 만능기판과 헤더(R19).',
    '구조·체결': '출력물을 묶는 나사·인서트·원판, 펠트·EVA 시트, 뒷바(가운데 유닛) 합판·래치·자석, 스피커 상자 부자재.',
    '페달': '댐퍼(서스테인) 페달 하나(R24). 싼 스위치 페달에 예비 홀센서를 달아 연속형(하프 페달)으로 개조하고, 3 m 신호선으로 CU에 꽂는다.',
    '제어·전원': 'Pi 5와 부속, USB-C PD 전원 입력(벽 충전기·보조배터리)·5.1 V 강압·스위치·퓨즈, 전원형 USB 허브(R28).',
    '오디오': 'USB 동글(DAC·헤드폰 앰프) → 헤드폰 잭 노멀 접점 → 80 Hz RC → TPA3110 앰프 → 좌우 스피커 2개(R25), 상자 재료.',
    '소프트웨어': '무료 음원 엔진과 피아노 샘플.',
}


def group_block(lines, g, idx):
    rows = [l for l in lines if l['group'] == g]
    tot = sum(sub(l) for l in rows)
    cards = '\n'.join(part_card(l, 'base') for l in rows)
    return (f'<h3 id="g-{idx}">{esc(g)} <span class="gsum mono">{len(rows)}줄 · {won(tot)}원</span></h3>'
            f'<p class="mut">{esc(GROUP_DESC.get(g, ""))}</p><div class="cards">{cards}</div>')


def cost_table(lines, anchor_prefix=''):
    rows = []
    for l in lines:
        ship = l.get('shipping_krw') or 0
        rows.append([
            f'<a class="cn" href="#{l["line_id"]}">{l["line_id"]}</a>',
            esc(l['name']),
            f'<span class="mono">{l["qty"]}</span>',
            f'<span class="mono">{won(l["unit_price_krw"])}</span>',
            f'<span class="mono">{won(ship) if ship else "–"}</span>',
            f'<span class="mono"><b>{won(sub(l))}</b></span>',
            f'<a href="{esc(l.get("url"))}" rel="noopener">{esc(re.sub(r" [(].*", "", l.get("store") or ""))}</a>',
        ])
    return table([('ID', ''), ('품목', ''), ('수량', 'n'), ('단가', 'n'), ('배송', 'n'), ('소계', 'n'), ('판매처', '')], rows, 'cost')


def drawing(key, cap, num):
    svg = fix(DR[key]).replace('id="arr"', f'id="arr-{key}"').replace('url(#arr)', f'url(#arr-{key})')
    return f'<figure class="drw" id="dwg-{key}">{svg}<figcaption><b>도면 {num}.</b> {cap}</figcaption></figure>'


# ---------- 본문 조각 ----------
base = B['base']
cons = B['consumable']
tools = B['tools']
opt = B['optional']
T_BASE = sum(map(sub, base))
T_CONS = sum(map(sub, cons))
T_TOOL = sum(map(sub, tools))
assert T_CONS == 232000 and T_TOOL == 165273, (T_CONS, T_TOOL)
MARGIN = 1_000_000 - T_BASE

g_tot = OrderedDict((g, sum(sub(l) for l in base if l['group'] == g)) for g in GROUP_ORDER)

fil = F['filament']
fil_g = sum(x['qty'] * x['grams_each'] for x in fil)
fil_h = sum(x['qty'] * x['hours_each'] for x in fil)
_col = {}
for _x in fil:
    _col[_x['material']] = _col.get(_x['material'], 0) + _x['qty'] * _x['grams_each']
_mix = _col.get('PETG 흰·검정·회색', 0) + _col.get('PETG 흰·회색', 0)  # 끝 부속·쿠폰: 회색 약 절반, 흰 3할, 검정 2할
FIL_W = (_col.get('PETG 흰색', 0) + 0.3 * _mix) / 1000
FIL_K = (_col.get('PETG 검정', 0) + 0.2 * _mix) / 1000
FIL_G = (_col.get('PETG 회색', 0) + _col.get('PETG 회색 또는 검정', 0) + 0.5 * _mix) / 1000
_SP = {l['line_id']: l['qty'] for l in B['consumable'] if l['line_id'] in ('C01', 'C02', 'C03')}
FIL_KG = sum(_SP.values())
FIL_SP = f'흰 {_SP["C01"]} · 검정 {_SP["C02"]} · 회색 {_SP["C03"]}'
for c in F['calcs']:
    if c.pop('_fil', False):
        c['inputs'] = ('모듈 502 g ×7, 끝 부속 160+82 g, 쿠폰 200 g, 스피커 그릴 64 g(R25), 스피커 앞판 310 g·뒷바 출력물 388 g(CU 트레이·I/O 판·도브테일·받침, R26), '
                       '예비 콤 1세트 266 g(R29), 브래킷 12 g')
        c['result'] = re.sub(r'^합계 약 [\d.]+ kg\(\+낭비 10% → [\d.]+ kg\), 약 \d+ h',
                             f'합계 약 {fil_g / 1000:.2f} kg(+낭비 10% → {fil_g * 1.1 / 1000:.1f} kg), 약 {fil_h:.0f} h', c['result'])
        assert c['result'].startswith(f'합계 약 {fil_g / 1000:.2f}'), c['result']
        c['conclusion'] = (f'{FIL_SP} = {FIL_KG} kg. 순수 필요량은 흰 약 {FIL_W:.2f}, 검정 약 {FIL_K:.2f}, 회색 약 {FIL_G:.2f} kg이다(낭비 10%를 더해도 스풀 안). '
                           f'검정은 여유가 약 {_SP["C02"] - FIL_K * 1.1:.1f} kg이다. 24 h 가동이면 약 {fil_h / 24:.0f}일, 실패 15% 포함 약 {fil_h * 1.15 / 24:.0f}일.')

VIEW_KO = OrderedDict([('plan', '평면(P)'), ('side', '측면(S)'), ('detail', '상세(D)'), ('assembly', '배치(A)')])


def dims_block():
    out = []
    for v, lab in VIEW_KO.items():
        rows = [x for x in F['dims'] if x['view'] == v]
        trs = [[f'<span class="mono">{esc(x["id"])}</span>', esc(fix(x['name'])),
                f'<span class="mono">{esc(x["value"])}</span>', esc(x.get('unit') or ''),
                inline(x.get('ref')), inline(x.get('note') or '')] for x in rows]
        out.append(f'<details class="dims"><summary><b>{lab}</b> 치수 {len(rows)}개</summary>'
                   + table([('ID', ''), ('항목', ''), ('값', 'n'), ('단위', ''), ('기준·위치', ''), ('비고', '')], trs, 'dimt')
                   + '</details>')
    return ''.join(out)


def calcs_block():
    out = []
    for i, c in enumerate(F['calcs'], 1):
        out.append(f'''<details class="calc"><summary><span class="lid">C{i:02d}</span> <b>{esc(fix(c["name"]))}</b><span class="cres">{inline(c["result"])}</span></summary>
<div class="cbody"><table class="kv"><tr><th>식</th><td class="mono small">{inline(c["formula"])}</td></tr>
<tr><th>입력</th><td>{inline(c["inputs"])}</td></tr><tr><th>결과</th><td>{inline(c["result"])}</td></tr>
<tr><th>결론</th><td>{inline(c["conclusion"])}</td></tr></table></div></details>''')
    return ''.join(out)


def fil_table():
    rows = [[esc(fix(x['part'])), esc(x['material']), f'<span class="mono">{x["qty"]}</span>',
             f'<span class="mono">{x["grams_each"]}</span>', f'<span class="mono">{x["hours_each"]}</span>',
             f'<span class="mono">{won(x["qty"] * x["grams_each"])}</span>',
             f'<span class="mono">{x["qty"] * x["hours_each"]:.1f}</span>'] for x in fil]
    rows.append(['<b>합계</b>', '', '', '', '', f'<span class="mono"><b>{won(fil_g)} g</b></span>',
                 f'<span class="mono"><b>{fil_h:.0f} h</b></span>'])
    return table([('출력물', ''), ('재료', ''), ('개수', 'n'), ('g/개', 'n'), ('h/개', 'n'), ('g 합', 'n'), ('h 합', 'n')], rows)


def budget_table():
    rows = [[esc(g), f'<span class="mono">{sum(1 for l in base if l["group"] == g)}</span>',
             f'<span class="mono">{won(v)}</span>',
             f'<div class="bar"><i style="width:{v / T_BASE * 100:.1f}%"></i></div>'] for g, v in g_tot.items()]
    rows.append(['<b>기본 구성 합계</b>', f'<span class="mono">{len(base)}</span>', f'<span class="mono"><b>{won(T_BASE)}</b></span>', f'<span class="mut">한도 1,000,000 · 여유 {won(MARGIN)}</span>'])
    rows.append(['소모품(한도 밖, R21 허용)', f'<span class="mono">{len(cons)}</span>', f'<span class="mono">{won(T_CONS)}</span>', f'<span class="mut">필라멘트 {FIL_KG} kg·케이블·납·본드 등</span>'])
    rows.append(['공구(보유 시 0원)', f'<span class="mono">{len(tools)}</span>', f'<span class="mono">{won(T_TOOL)}</span>', '<span class="mut">인두·멀티미터·캘리퍼스 등</span>'])
    rows.append(['<b>처음부터 다 산다면</b>', '', f'<span class="mono"><b>{won(T_BASE + T_CONS + T_TOOL)}</b></span>', '<span class="mut">기본 + 소모품 + 공구</span>'])
    return table([('구분', ''), ('줄', 'n'), ('금액(원)', 'n'), ('', '')], rows, 'budget')


def opt_rows():
    rows = []
    for l in opt:
        rows.append([f'<a class="cn" href="#{l["line_id"]}">{l["line_id"]}</a>', esc(l['name']),
                     f'<span class="mono">{won(sub(l))}</span>', inline((l.get('why') or '')[:220] + ('…' if len(l.get('why') or '') > 220 else ''), False)])
    return table([('ID', ''), ('항목', ''), ('금액', 'n'), ('언제 쓰나', '')], rows)


# 요구사항 원문 요지(sound-requirements.md §1)
REQ = {}
md = open('/Users/kwg/Desktop/mydrive/project/Toccata/hardware/mechanical/sound-requirements.md').read()
for m in re.finditer(r'^\|\s*\*{0,2}(R\d+|D\d+)\*{0,2}\s*\|\s*([^|]+)\|', md, re.M):
    REQ.setdefault(m.group(1), re.sub(r'~~.*?~~\s*(→\s*)?', '', m.group(2)).strip().replace('**', ''))


def req_table():
    rows = [[f'<span class="mono">{esc(r["id"])}</span>', esc(REQ.get(r['id'], '')), inline(r['how'])] for r in F['requirement_check']]
    return table([('ID', ''), ('요구', ''), ('이 설계에서', '')], rows, 'req')


def risk_table():
    rows = [[f'<span class="mono">{i}</span>', inline(r['risk']), inline(r['mitigation'])] for i, r in enumerate(F['risks'], 1)]
    return table([('#', ''), ('위험', ''), ('대책', '')], rows)


def changelog():
    out = []
    for c in F['changelog']:
        m = re.match(r'\[([^\]]+)\]\s*(.*)', fix(c))
        if m:
            tag, body = m.groups()
            sev = 'c-crit' if '치명' in tag else ('c-warn' if '주요' in tag else 'c-mut')
            out.append(f'<li><span class="chip {sev}">{esc(tag)}</span> {inline(body)}</li>')
        else:
            out.append(f'<li>{inline(c)}</li>')
    return '<ul class="chg">' + ''.join(out) + '</ul>'


def assembly_steps():
    return '<ol class="steps">' + ''.join(f'<li>{circ_list(fix(s))}</li>' for s in F['assembly']) + '</ol>'


UNRES = B['unresolved']

# ---------- 부품 쓰임새(어디에·어떻게) ----------
_UJ = json.load(open(os.path.join(HERE, 'usage.json')))
ZONES, USE = _UJ['zones'], _UJ['use']

# ---------- R26 문구를 도면·모델 값에 맞춘다(bom_all.json·usage.json은 읽기만 하고 여기서 바꾼다) ----------
import patch_r26 as _P  # noqa: E402
from draw import fmt as _dfmt  # noqa: E402
_N_MOD = sum(1 for p in F['assembly_plan'] if p['name'].startswith('모듈 O'))  # 통로를 지나는 모듈 USB-C 가닥 수(PED 1가닥은 CU 칸 안)
_R26_TXT = [
    ('CU 칸(안폭 189)', f'CU 칸(안폭 {_dfmt(_P.CU_W)})'),
    ('→ 허브 USB 8가닥. 허브에 꽂힌 채 뒷바 아래 케이블 통로에 두고,',
     f'→ 허브 USB 8가닥. 모듈 {_N_MOD}가닥은 허브에 꽂힌 채 뒷바 아래 케이블 통로에 두고(PED 1가닥은 CU 칸 안 짧은 선),'),
    ('케이블 통로 안 USB 8가닥 묶음', f'케이블 통로 안 모듈 USB-C {_N_MOD}가닥 묶음'),
    ('모듈 USB-C 8가닥, 스피커 XT30', f'모듈 USB-C {_N_MOD}가닥(PED 1가닥은 CU 칸 안 짧은 선), 스피커 XT30'),
    ('CU 허브까지. 허브에 꽂힌 채 케이블 통로에 두고,', f'CU 허브까지. 모듈 {_N_MOD}가닥은 허브에 꽂힌 채 케이블 통로에 두고(PED 1가닥은 CU 칸 안 짧은 선),'),
    ('USB 8가닥 + 끝 부속 선 묶음(통로 안)', f'모듈 USB-C {_N_MOD}가닥 + 끝 부속 선 묶음(통로 안)'),
]


_R26_CUT = ('폭 195 띠 ×2: 바닥 356·338, 뚜껑 356·338 / 폭 77 띠: 앞판 894 + 끝판 172 / 폭 77 띠: 뒤판 356·338 + 끝판 172 + 칸막이 172(77) + 칸막이 172(57, CU↔보조배터리)', '폭 195 띠 ①: 바닥 356·338 + 뚜껑 356 / 폭 195 띠 ②: 뚜껑 338 + 칸막이 172×77 / 폭 77 띠: 앞판 894 + 끝판 172 / 폭 77 띠: 뒤판 356·338 + 끝판 172 + 칸막이 172×57(CU↔보조배터리) / 남는 띠 약 44')  # BOM L63 재단 계획 = 도면 11의 배치


def _r26_txt(x):
    for a, b in _R26_TXT:
        x = x.replace(a, b)
    return x


for _k in ('base', 'consumable', 'tools'):
    for _l in B[_k]:
        if _l.get('role'):
            _l['role'] = _r26_txt(_l['role'])
        for _s in _l.get('specs') or []:
            if isinstance(_s, dict) and _s.get('k') == '재단 계획' and _s.get('v') == _R26_CUT[0]:
                _s['v'] = _R26_CUT[1]
for _d in (USE, ZONES):
    for _k in _d:
        _d[_k] = [_r26_txt(x) if isinstance(x, str) else x for x in _d[_k]]
ZONE_ORDER = ['mod', 'end', 'cab', 'cu', 'spk', 'ped', 'com', 'tool']
ZNUM = {z: str(i + 1) for i, z in enumerate(ZONE_ORDER)}
ZCLS = {'mod': 'zf1', 'end': 'zf2', 'cab': 'zf3', 'cu': 'zf4', 'spk': 'zf5', 'ped': 'zf6'}
ALL_LINES = {l['line_id']: l for k in ('base', 'consumable', 'tools') for l in B[k]}


def zone_map():
    from draw import SVG
    from patch_r26 import Y0, CH_D, T
    s = SVG(-40, -440, 1260, 500, scale=0.62, pad=(30, 26, 30, 30))
    cab_polys = []
    for p in F['assembly_plan']:
        n = p['name']
        pts = [tuple(q) for q in p['points']]
        if '페달 3개' in n:  # R24: 댐퍼 하나
            pts = [(640, -400), (716, -400), (716, -160), (640, -160)]
            n = '댐퍼 페달'
        if 'USB 케이블' in n or 'EXT 선' in n or '센서 열' in n or re.match(r'^[A-G]#?\d 건반', n):
            continue
        # 브래킷은 L·R 모두 쓰임새 표 L42 구역(spk) — '끝 부속' 이름보다 먼저 본다
        z = ('spk' if '브래킷' in n else 'end' if '끝 부속' in n and '선' not in n else 'mod' if '모듈 O' in n else 'cab' if ('케이블 공간' in n or '케이블 통로' in n)
             else 'cu' if ('CU' in n or '가운데 유닛' in n or '보관함' in n or '보조배터리' in n or n.startswith('I/O')) else 'spk' if ('스피커' in n or '서브' in n) else 'ped' if '페달' in n else None)
        if z == 'cab':
            cab_polys.append((pts, n))  # 뒷바 아래 통로: 다른 구역 위에 윤곽만
        elif z:
            s.poly(pts, ZCLS[z], True, n)
    for pts, n in cab_polys:
        s.poly(pts, 'zf3o', True, n)
    for k in range(7):
        s.text(47 + 164.5 * k + 82.25, 150, f'O{k + 1}', 'zl')
    for x, lab in ((345, '건반 보관함'), (620, 'CU 칸'), (886, '보조배터리 칸')):
        s.text(x, 280, lab, 'zl')
    badges = [('mod', 622, 90, '건반 모듈 ×7'), ('end', 15, 90, ''), ('end', 1218, 90, ''), ('cab', 150, Y0 + CH_D / 2, '케이블 통로(아래)'),
              ('cu', 620, 345, '가운데 유닛'), ('spk', 74, 330, '스피커'), ('spk', 1148, 330, '스피커'),
              ('ped', 678, -280, '댐퍼 페달')]
    BR = 26
    for z, x, v, lab in badges:
        r = min(BR, CH_D / 2 - 1.5) if z == 'cab' else BR  # 통로 배지는 띠(깊이 CH_D) 안에 들어가게
        s.circle(x, v, r, 'zb-c')
        s.text(x, v, str(ZONE_ORDER.index(z) + 1), 'zb-t', 'middle', 0, 5)
        if lab and z == 'cab':  # 통로 띠 중 칸 앞 안벽(Y0+T)과 띠 뒤 끝 사이 가운데, 가운데 유닛 끝판 안쪽
            s.text(x + BR + 4, (Y0 + T + Y0 + CH_D) / 2, lab, 'zl', 'start', 0, 4)
        elif lab:
            s.text(x, v - 44, lab, 'zl')
    s.text(-20, -30, '끝 부속 ②', 'zl', 'start')
    s.text(1240, -30, '② 끝 부속', 'zl', 'end')
    s.text(610, -420, '연주자 쪽 ↓', 'zl')
    s.scalebar(200)
    return s.render('부품 위치 지도', '평면, 연주자 쪽이 아래, 단위 mm')


def usage_section():
    out = []
    legend = ''.join(f'<li><a href="#use-z-{z}"><span class="zb">{ZNUM[z]}</span>{esc(ZONES[z][1])}</a></li>' for z in ZONE_ORDER)
    n = {k: len(B[k]) for k in ('base', 'consumable', 'tools')}
    out.append(f'<p>부품표의 모든 줄(기본 {n["base"]} · 소모품 {n["consumable"]} · 공구 {n["tools"]})이 어느 구역에 몇 개 들어가고 어떻게 쓰이는지 정리했다. '
               '번호는 아래 지도의 구역 번호다. ID를 누르면 그 부품의 사진·스펙 카드로 간다. 모듈 안의 정확한 위치는 도면 1·2·3·5에 있다.</p>')
    out.append(f'<figure class="drw" id="use-map">{zone_map()}<figcaption><b>부품 위치 지도.</b> 위에서 본 배치(연주자 쪽이 아래). '
               '번호는 아래 표의 구역이다. 뒷바는 스피커 파트 2개와 가운데 유닛으로 나뉜다(R26·R27).</figcaption></figure>')
    out.append(f'<ul class="zlegend">{legend}</ul>')
    for z in ZONE_ORDER:
        rows = []
        for lid, (zz, where, how, ref) in USE.items():
            if zz != z:
                continue
            l = ALL_LINES[lid]
            nm = re.sub(r'^\[[^\]]*\]\s*', '', l['name'])
            rows.append(f'<tr id="use-{lid}"><td><a class="cn" href="#{lid}"><span class="lid">{lid}</span></a></td><td>{esc(nm[:48])}</td>'
                        f'<td>{esc(where)}</td><td>{esc(how)}</td><td class="mut">{esc(ref)}</td></tr>')
        out.append(f'<h3 id="use-z-{z}"><span class="zb">{ZNUM[z]}</span>{esc(ZONES[z][1])} <span class="gsum mono">{len(rows)}줄</span></h3>'
                   f'<p class="mut">{esc(ZONES[z][2])}</p>'
                   '<div class="tw"><table class="use"><thead><tr><th>ID</th><th>부품</th><th>어디에 · 몇 개</th><th>어떻게 쓰나</th><th>조립·도면</th></tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div>')
    return '<h2 id="use"><span class="eyebrow">00</span>부품 쓰임새 — 어디에, 어떻게</h2>' + ''.join(out)


# ---------- R25 오디오 재설계 장 ----------
SPK = json.load(open(os.path.join(HERE, 'work', 'audio2', 'spk_result.json')))
AMP = json.load(open(os.path.join(HERE, 'work', 'audio2', 'amp_result.json')))
VERD = {'추천': 'c-good', '가능': 'c-acc', '비추천': 'c-mut'}


def _short(t, n=150):
    t = re.sub(r'\s+', ' ', str(t or '')).strip()
    return t if len(t) <= n else t[:n].rsplit(' ', 1)[0] + '…'


def audio_section():
    ALL = _n25  # R25 시점 부품표(R26에서 빠진 줄도 보여 준다)
    CUR = {l['line_id'] for l in B['base']}
    OLD = _o25
    lk = lambda i: (f'<a class="cn" href="#{i}"><span class="lid">{i}</span></a>' if i in CUR
                    else f'<span class="lid">{i}</span><span class="mut small">(R26에서 뺌)</span>')
    # 역할별 이전 → 지금 (부품표 줄로 계산)
    groups = [
        ('DAC·헤드폰 앰프', ['L04'], ['L51', 'L52']),
        ('스피커 앰프', ['L05', 'L09'], ['L53']),
        ('헤드폰을 꽂으면 스피커 끄기', ['L16', 'L28'], []),
        ('저음 보호(D18)', [], ['L56']),
        ('전원', ['L06'], ['L06', 'L54', 'L55']),
        ('스피커 유닛', ['L07', 'L08'], ['L07']),
        ('상자·그릴·단자', ['L10', 'L13', 'L11'], ['L10', 'L11']),
        ('유닛·그릴 나사', ['L48', 'L49'], ['L49']),
    ]
    rows = []
    for role, o_ids, n_ids in groups:
        o_s = sum(_sub25(OLD[i]) for i in o_ids)
        n_s = sum(_sub25(ALL[i]) for i in n_ids)
        o_t = ' + '.join(f'{re.sub(r"^\[[^\]]*\]\s*", "", OLD[i]["name"])[:34]} <span class="mono mut">{won(_sub25(OLD[i]))}</span>' for i in o_ids) or '—'
        n_t = ' + '.join(f'{lk(i)} {esc(re.sub(r"^\[[^\]]*\]\s*", "", ALL[i]["name"])[:34])} <span class="mono mut">{won(_sub25(ALL[i]))}</span>' for i in n_ids) or '노멀 접점(PJ-313, L15 그대로) <span class="mono mut">0</span>'
        rows.append([esc(role), o_t, n_t, f'<span class="mono">{won(o_s)}</span>', f'<span class="mono"><b>{won(n_s)}</b></span>'])
    rows.append(['<b>합계(바뀐 줄)</b>', '', '', f'<span class="mono">{won(AUD_OLD)}</span>', f'<span class="mono"><b>{won(AUD_NEW)}</b></span>'])
    cmp_tbl = table([('역할', ''), ('이전(R24까지)', ''), ('지금(R25)', ''), ('이전 원', 'n'), ('지금 원', 'n')], rows, 'aud cmp')
    loud = table([('구성', ''), ('채널당 출력', 'n'), ('1 m 음압(한 개)', 'n'), ('P-145 대비', 'n')], [
        ['Yamaha P-145(기준, §1.5)', '7 W', '약 93.5~96.5 dB(추정)', '—'],
        ['이전 설계: AAmp60 + DMA105-4(4 Ω, 89.8 dB/2.83 V) + 서브', '약 30 W', '약 101.5 dB', '+5~+8 dB'],
        ['R25: XH-A232 19 V 어댑터 + CW-100B25(8 Ω, 86 dB/2.83 V)', '약 19 W', '약 98.8 dB', '+2~+5 dB'],
        ['<b>지금(R28): 같은 앰프를 PD 20 V로</b>', '<b>약 21 W</b>', '<b>약 99.2 dB</b>', '<b>+3~+6 dB</b>'],
        ['지금, 제조사 성적서 감도(89 dB)가 맞다면', '약 21 W', '약 102.2 dB', '+6~+9 dB'],
    ], 'budget')
    srows = []
    for d in SPK['drivers']:
        pair = d['price_each_krw'] * d['qty'] + (d.get('shipping_krw') or 0)
        srows.append([f'<span class="mono">{esc(d["id"])}</span>', f'<a href="{esc(d["url"])}" rel="noopener">{esc(_short(d["name"], 60))}</a>',
                      f'<span class="mono">{won(pair)}</span>', f'<span class="mono">{won(d.get("pair_total_krw") or 0)}</span>',
                      esc(_short(d['impedance'], 24)), esc(_short(d['sensitivity'], 60)),
                      f'<span class="chip {VERD.get(d["verdict"], "c-mut")}">{esc(d["verdict"])}</span>', esc(_short(d['why'], 160))])
    spk_tbl = table([('ID', ''), ('유닛', ''), ('한 쌍(배송 포함)', 'n'), ('상자 재료 포함', 'n'), ('임피던스', ''), ('감도', ''), ('판정', ''), ('이유', '')], srows, 'aud cand')
    arows = []
    for c in AMP['configs']:
        arows.append([f'<span class="mono">{esc(c["id"])}</span>', esc(_short(c['title'], 80)), f'<span class="mono">{won(c["total_krw"])}</span>',
                      esc(_short(c['power_w'], 70)), esc(_short(c['loudness_vs_p145'], 40)), esc(_short(c['latency'], 60)),
                      f'<span class="chip {VERD.get(c["verdict"], "c-mut")}">{esc(c["verdict"])}</span>', esc(_short(c['why'], 150))])
    amp_tbl = table([('ID', ''), ('구성', ''), ('합계(따로 살 때)', 'n'), ('출력', ''), ('P-145 대비', ''), ('지연', ''), ('판정', ''), ('이유', '')], arows, 'aud amp')
    return f"""<h2 id="audio"><span class="eyebrow">00</span>오디오 재설계 — 스피커 2개, 싼 앰프(R25)</h2>
<p>사용자 결정(R25, 2026-09-24): 스피커는 좌우 2개면 되고, 스피커와 앰프는 비싸지 않은 것으로 고른다. 그래서 스피커 13종과 앰프·DAC 구성 10종을 다시 조사해 판매 페이지에서 가격·재고·사진을 확인했다. 기준은 §1.5(P-145 이상의 음량)와 R12~R16(호환, 부착형, 음량, 헤드폰 차단, 88키 찌그러짐 없음)이다.</p>
<div class="callout good"><p><b>결론</b></p><p>Apple USB-C 동글(DAC·헤드폰 앰프) → 헤드폰 잭 노멀 접점 → 80 Hz RC → XH-A232(TPA3110, R28 이후 PD 20 V) → 삼미 CW-100B25 ×2(오꾸메 밀폐, R26 이후 5.05 L). 바뀐 줄 {len(AUD_IDS)}개가 {won(AUD_OLD)}원에서 {won(AUD_NEW)}원으로 {won(AUD_OLD - AUD_NEW)}원 줄었고, 기본 구성은 {won(BASE_R24)}원에서 {won(BASE_R26)}원이 됐다(R26~R29 이후 {won(T_BASE)}원). 아래 표의 '지금'은 R25 시점 값이고, 전원 줄은 R28로 다시 바뀌었다(§{{{{#body}}}}).</p></div>
<h3>왜 3개였고, 왜 비쌌나</h3>
<ul class="sub"><li><b>3개였던 이유</b>: §1.5에 '최저음 30~100 Hz를 채운다'는 기준이 있어 위성 2개에 서브우퍼 1개를 더했다. R25로 이 기준을 뺐다(sound-requirements.md §1.5 표에 반영).</li>
<li><b>비쌌던 이유</b>: HiFiBerry DAC2 Pro + AAmp60(해외 배송 포함 141,300원), Dayton 유닛 3개(222,070원), 서브 전용 앰프, 90 W 어댑터와 부속 케이블, 600×1200 합판, 알루미늄 그릴, 헤드폰 감지 릴레이였다. 음질 여유를 크게 잡은 구성이었다.</li>
<li><b>줄여도 되는 이유</b>: 피아노 소리를 P-145보다 크게 내는 데 필요한 출력은 채널당 약 10 W급(8 Ω에 약 9 Vrms)이다. 저가 D급 앰프 칩(TPA3110)으로 충분하고, DAC는 USB 동글도 DAC2 Pro와 같은 급(SNR 약 113 dB)이다.</li></ul>
<h3>이전 → 지금</h3>{cmp_tbl}
<h3>소리는 충분한가 — 음량</h3>{loud}
<p class="sub">감도 + 20·log(출력 전압 / 2.83 V)로 계산했다. R28로 앰프 전원이 19 V 어댑터에서 PD 20 V가 돼 약 +0.4 dB 커졌다. 이전 설계보다 약 2.5 dB 작지만 P-145보다는 크다. 두 개가 함께 울리면 저음역에서 +3~6 dB가 더해진다.</p>
<h3>소리는 충분한가 — 음역과 찌그러짐</h3>
<ul class="sub"><li><b>88건반 모두 음높이가 맞게 들린다.</b> 가장 낮은 두 옥타브(A0~D#2, 27.5~78 Hz)는 기본음이 상자의 저음 한계(F3 약 95~128 Hz) 아래라 약하다. 대신 귀가 2·3·4배음으로 음높이를 알아듣는다. P-145 같은 작은 디지털 피아노도 같은 방식이다.</li>
<li><b>고음</b>: 유닛이 13~15 kHz까지 내서 C8(4,186 Hz)의 기본음과 주요 배음이 들어간다. 알루미늄 콘보다 반짝임은 조금 덜할 수 있다.</li>
<li><b>찌그러짐(R16·D18)</b>: 작은 유닛은 최저음을 세게 낼 때 콘이 한계(Xmax 약 3 mm)까지 움직여 먼저 찌그러진다. 앰프 입력의 80 Hz RC, FluidSynth 리미터, 소리 게이트에서 정한 볼륨 상한으로 막는다. D7(hw: 직결)을 지키려고 필터는 소프트웨어 대신 콘덴서 2개(L56)와 저항으로 만든다.</li>
<li><b>지연(D8)</b>: USB 동글이라 계산 8~10 ms로 여유가 작다. 설치 후 재서 넘으면 버퍼를 줄이고, 그래도 넘으면 I2S DAC(O03)로 바꾼다.</li></ul>
<h3>스피커 후보 13종</h3><p class="sub">'상자 재료 포함'은 오꾸메 합판·본드·피스·흡음솜까지 더한 한 쌍 값이다. 가격은 9/24 판매 페이지 기준이다.</p>{spk_tbl}
<h3>앰프·DAC 구성 10종</h3><p class="sub">'합계'는 그 구성 부품만 따로 살 때의 값(배송비 포함)이다. 부품표에서는 다른 부품과 합배송이라 배송비가 빠진다. 추천 A4를 8 Ω 스피커에 맞춰 19 V로 골랐고, R28 이후에는 PD 트리거의 20 V를 그대로 쓴다.</p>{amp_tbl}
<p class="sub">나중에 바꾸는 길: 소리를 더 다듬고 싶으면 스피커를 PC105-4(O02)로, 지연이 넘치면 DAC를 Raspberry Pi DAC+(O03)로 바꾼다. 상자와 배선은 그대로 쓴다.</p>
"""


# ---------- R26~R29 본체 구조 장 ----------
_B26 = _B25N
_o26 = {l['line_id']: l for k in ('base', 'consumable', 'tools') for l in _B26[k]}
_n26 = {l['line_id']: l for k in ('base', 'consumable', 'tools') for l in B[k]}
BASE_R26 = sum(map(_sub25, _B26['base']))
R26_IDS = sorted(i for i in set(_o26) | set(_n26) if (_sub25(_o26[i]) if i in _o26 else 0) != (_sub25(_n26[i]) if i in _n26 else 0))


def _lk(i):
    l = _n26.get(i) or next((x for x in B['optional'] if x['line_id'] == i), None)
    if not l:
        return '—'
    nm = re.sub(r'^\[[^\]]*\]\s*', '', l['name'])
    return f'<a class="cn" href="#{i}"><span class="lid">{i}</span></a> {esc(nm[:40])}'


def body_section():
    parts = [
        ['건반 모듈 O1~O7 (7개)', '164.5 × 212 × 59', '약 0.59 kg', '건반 12, 센서 12, RP2040 기판', '모듈끼리 도브테일(위에서 끼움)'],
        ['끝 부속 L·R (2개)', '63 × 212 / 39.5 × 212', '약 0.1 kg', 'A0·A#0·B0 / C8, 센서', 'O1·O7에 도브테일 + 6핀 커넥터, 스피커 파트에 방진 브래킷'],
        ['스피커 파트 L·R (2개)', '180 × 195 × 232', '약 1.95 kg', 'CW-100B25, 흡음솜, 그릴(출력 앞판)', '가운데 유닛에 도브테일 2 + 래치 1, XT30'],
        ['가운데 유닛 (1개)', '894 × 195 × 122', '약 3.3 kg (+ 보조배터리 약 0.4)', '건반 보관함 · CU 칸 · 보조배터리 칸', '양 끝 도브테일·래치, 커넥터는 아래 표'],
        ['댐퍼 페달 (1개)', '76 × 240', '약 0.5 kg', '듀로 스위치 페달 개조', '3.5 mm 3 m 선(L50) → I/O 판'],
    ]
    ptab = table([('파트', ''), ('크기(mm)', ''), ('무게', ''), ('들어가는 것', ''), ('결합', '')], [[esc(c) for c in r] for r in parts], 'aud')
    conns = [
        ['건반 모듈 O1~O7·PED → 허브', f'USB-C(모듈 쪽) / USB-A(허브 쪽), {_N_MOD + 1}가닥', _lk('C04'),
         f'모듈 {_N_MOD}가닥은 허브에 꽂힌 채 케이블 통로에 둔다(PED 1가닥은 CU 칸 안 짧은 선). 모듈 쪽만 뺀다'],
        ['끝 부속 ↔ O1·O7', '6핀 잠금 커넥터(미리 배선된 것)', _lk('L66'), '듀폰보다 잘 안 빠진다'],
        ['헤드폰 잭 ↔ CU', '3.5 mm 플러그 2개(선 ①·②)', _lk('C14'), '① 동글, ② CU 트레이의 앰프 입력 잭(PJ-313 추가분)'],
        ['CU ↔ 스피커 L·R', 'XT30 2쌍(2핀, 극성)', _lk('L61'), 'XT90은 90 A용(전기자전거·드론 배터리)이라 여기엔 너무 크다. 같은 계열 XT30을 쓴다'],
        ['페달 ↔ CU', '3.5 mm (I/O 판)', _lk('L15'), '기존 PJ-313'],
        ['전원 ↔ CU', 'USB-C PD (I/O 판)', _lk('L57'), '벽 충전기 또는 보조배터리 선을 꽂는다'],
    ]
    ctab = table([('연결', ''), ('커넥터', ''), ('부품', ''), ('메모', '')], [[esc(a), esc(b), c, esc(d)] for a, b, c, d in conns], 'aud')
    pw = [
        ['Pi 5 (FluidSynth)', '약 5 W', '5.1 V'], ['건반 모듈 7 + PED', '약 2.8 W', '5 V(허브)'], ['허브·동글', '약 0.7 W', '5 V'],
        ['5 V 강압 손실(효율 약 0.85~0.9)', '약 1~1.5 W', '20 V → 5.1 V'], ['앰프 대기 + 음악 평균', '약 1.5~4.5 W', '20 V'],
        ['<b>평균 합계</b>', '<b>약 12 W</b>', ''], ['최대 볼륨 저음 화음(순간)', '약 52 W', 'PD 20 V 3 A면 버틴다'],
    ]
    ptab2 = table([('부하', ''), ('전력', 'n'), ('전압', '')], pw, 'budget')
    opt_pb = [l for l in B['optional'] if l['line_id'] == 'O07']
    pb = (f'<p class="sub">권장 보조배터리 예: {_lk("O07")} ({won(_sub25(opt_pb[0]))}원, 선택 항목). 이미 가진 보조배터리가 PD 20 V 3 A 이상이면 그대로 쓴다.</p>' if opt_pb else '')
    added = [i for i in R26_IDS if i not in _o26]
    removed = [i for i in R26_IDS if i not in _n26]
    changed = [i for i in R26_IDS if i in _o26 and i in _n26]
    o_sum = sum(_sub25(_o26[i]) for i in R26_IDS if i in _o26 and _o26[i].get('line_id', '')[0] == 'L')
    n_sum = sum(_sub25(_n26[i]) for i in R26_IDS if i in _n26 and _n26[i].get('line_id', '')[0] == 'L')
    fmt = lambda ids: ', '.join(ids) if ids else '없음'
    return f"""<h2 id="body"><span class="eyebrow">00</span>본체 구조 — 파트별 분리·무선·보관(R26~R29)</h2>
<p>사용자 결정(R26~R29, 2026-09-25)을 반영했다. 요약하면 네 가지다. 모든 파트를 따로 떼어 보관한다. 뒷공간을 채워 직사각형으로 만든다. 보조배터리로 전원 없이 친다. 건반 보관함을 둔다.</p>
<div class="callout good"><p><b>결론</b></p><p>본체 뒤를 깊이 195 mm의 <b>뒷바</b>로 채워 전체가 <b>1254 × 410 mm 직사각형</b>이 됐다(이전 깊이 440, −30 mm). 뒷바는 왼쪽 스피커 파트 · 가운데 유닛 · 오른쪽 스피커 파트로 나뉜다. 뒷바를 22 mm 띄워 생긴 아래 앞쪽이 케이블 통로라 따로 비우던 케이블 공간이 없어졌다. 가운데 유닛에는 <b>건반 보관함 · CU 칸 · 보조배터리 칸</b>이 있다. 전원은 <b>USB-C 입력 하나</b>에 벽 충전기나 보조배터리를 꽂는다(평균 약 12 W, 20,000 mAh로 약 5시간). 합판은 직선으로만 자르고 구멍이 필요한 곳(스피커 앞판, CU 트레이, I/O 판)은 출력하므로 드릴이 필요 없다.</p></div>
<h3>파트 5종(모두 따로 들고 보관)</h3>{ptab}
<h3>파트 사이 연결 — 모두 꽂았다 빼는 커넥터</h3>{ctab}
<p class="sub">파트끼리 납땜으로 묶인 전선이 없다. 스피커선(XT30)과 헤드폰 선은 케이블 통로 안에서 만난다.</p>
<h3>보조배터리로 치기(R28)</h3>
<p>USB-C PD 입력 → PD 트리거(20 V) → 퓨즈 → 전원 스위치 → 20 V 단자 → ① 앰프(20 V 그대로) ② 5.1 V 강압 모듈 → Pi 5·허브. 벽에서는 65 W PD 충전기(L62)를 2 m C-C 선(C23)으로 같은 입력에 꽂는다. Pi에는 강압 모듈의 5 V만 USB-C 전원선(C24)으로 들어간다(동시 급전 금지, D16). Pi는 PD가 아닌 5 V를 3 A 전원으로 가정하므로 공식 문서대로 EEPROM <code>PSU_MAX_CURRENT=5000</code>(또는 config.txt <code>usb_max_current_enable=1</code>)을 넣어 USB 한도를 1.6 A로 연다.</p>
<p>보조배터리는 오른쪽 칸 앞쪽 받침에 끈으로 고정하고, 0.6 m C-C 선(C22)을 낮은 칸막이(172 × 57) 위로 넘겨 I/O 판의 선 통과 구멍으로 빼 입력에 꽂는다. 같은 칸 뒤 벽에는 USB 허브(228 × 48)가 있다. 20 V가 없는 작은 보조배터리면 트리거가 15·12 V로 내려가 소리만 작아진다.</p>
{ptab2}
<p class="sub">20,000 mAh(74~76 Wh) × 변환 효율 약 0.85 ÷ 12 W ≈ 5시간(조용히 치면 약 6시간, 크게 치면 약 4시간). 보조배터리는 USB-C PD 20 V 3 A(60 W) 이상이어야 최대 음량에서 끊기지 않는다(D19). 45 W 제품이면 볼륨 상한을 1 dB 낮춘다.</p>{pb}
<h3>건반 보관함(R29)</h3>
<p>가운데 유닛 왼쪽 칸(안치수 {_dfmt(_P.KS_W)} × {_dfmt(_P.IN_D)} × {_dfmt(_P.IN_H)}). 예비 백건 콤({_dfmt(_P.COMB_W)} × {_dfmt(_P.COMB_D)} × 22)을 눕히고 그 위에 흑건 콤({_dfmt(_P.BCOMB_W)} × {_dfmt(_P.COMB_D)} × 32)을 겹쳐 한 옥타브 1세트가 들어간다(높이 54). 오른쪽 {_P.DIV1 - _P.T / 2 - (_P.COMB_X0 + _P.COMB_W):.0f} mm에는 작은 부품 칸 3개(자석·펠트·나사·육각렌치)가 있다. 리프가 부러진 콤을 바로 바꿀 수 있다(위험 표 12). 건반 모듈 전체를 넣으려면 뒷바 깊이가 다시 440 mm로 늘어나므로 넣지 않았다. 모듈은 지금처럼 폼 상자로 옮긴다.</p>
<h3>설치와 분리 순서</h3>
<ol class="sub"><li>가운데 유닛을 놓는다 → 양쪽 스피커 파트를 도브테일에 위에서 끼우고 뒷면 래치를 잠근다 → XT30 2쌍을 꽂는다.</li>
<li>왼쪽 끝 부속 → O1 → … → O7 → 오른쪽 끝 부속을 뒷바 앞에 3 mm 띄워 끼운다. 끝 부속 브래킷을 스피커 파트에 건다.</li>
<li>통로에 있던 모듈 USB-C {_N_MOD}가닥을 각 모듈에 꽂는다. 6핀 커넥터로 끝 부속과 O1·O7을 잇고, 헤드폰 선 ①·②와 페달을 CU에 꽂는다.</li>
<li>보조배터리(또는 벽 충전기)를 USB-C 입력에 꽂고 스위치를 켠다.</li>
<li>분리는 거꾸로 한다. 끄기 전에 소프트웨어를 먼저 끈다(팝 방지).</li></ol>
<h3>부품표 변화</h3>
<p class="sub">바뀐 줄 {len(R26_IDS)}개. 새로 넣은 줄: {fmt(added)}. 뺀 줄: {fmt(removed)}. 수량·값이 바뀐 줄: {fmt(changed)}. 기본 구성은 {won(BASE_R26)}원에서 {won(T_BASE)}원이 됐다(바뀐 기본 줄 {won(o_sum)}원 → {won(n_sum)}원).</p>
"""

FRAG_P = os.path.join(HERE, 'cost', 'fragment.json')
FR = json.load(open(FRAG_P)) if os.path.exists(FRAG_P) else None


def cost_callout():
    if not FR:
        return ''
    rows = [[f'<a class="cn" href="#tier-{t["key"]}"><b>{t["key"]}</b></a> {esc(t["title"])}', f'<span class="mono"><b>{won(t["base"])}</b></span>',
             f'<span class="mono">{won(t["cons"])}</span>', f'<span class="mono">{won(t["tool"])}</span>',
             f'<span class="mono">−{(T_BASE - t["base"]) / T_BASE * 100:.0f}%</span>'] for t in FR['tiers']]
    t2 = next(t for t in FR['tiers'] if t['key'] == FR['recommended'])
    return (f'<div class="callout good"><p><b>더 줄일 수 있다 — 추천 {esc(FR["recommended"])}</b></p>'
            f'<p>요구사항을 모두 지키면서 부품과 설계를 바꾸면 기본 구성이 {won(t2["base"])}원까지 준다. 요구를 일부 완화하거나 PC에 소리를 맡기면 더 내려간다. 단계별 구성과 절감안 {FR["n_ok"]}개는 <a href="#cost">§{{{{#cost}}}}</a>에 있다.</p></div>'
            + table([('단계', ''), ('기본 구성', 'n'), ('소모품', 'n'), ('공구', 'n'), ('기본 절감', 'n')], rows, 'budget'))

# ---------- HTML ----------
EXTRA_CSS = r'''
:root{--bed:#DCD6CB}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bed:#34373D}}
:root[data-theme="dark"]{--bed:#34373D}
.wrap{max-width:1180px}
.drw{background:var(--sur);border:1px solid var(--rule);padding:12px}
.drw svg{margin:0 auto}
figure.drw figcaption{padding:0 4px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:12px;margin:14px 0 8px}
.pc-card{display:grid;grid-template-columns:132px 1fr;gap:14px;border:1px solid var(--rule);background:var(--sur);padding:12px;scroll-margin-top:16px}
.pc-card:target{outline:2px solid var(--acc)}
.pc-card .ph{display:block;width:132px;height:132px;background:#fff;border:1px solid var(--rule);overflow:hidden}
.pc-card .ph img{width:100%;height:100%;object-fit:contain;display:block}
.pc-card .noimg{display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--mut)}
.pc-card .pt{font-size:14px;line-height:1.45}
.pc-card .role{font-size:13px;color:var(--ink2);margin:6px 0;max-width:none}
.pc-card .buy{font-size:13px;line-height:1.6}
.pc-card .buy b{color:var(--ink)}
.pc-card details{margin:8px 0 0}
.pc-card details>summary{padding:6px 10px;font-size:12.5px}
.pc-card table.kv{margin:0;font-size:12.5px}
.pc-card table.kv th{width:108px}
.pc-card .dref{font-size:12.5px;color:var(--ink2);margin:8px 10px;max-width:none}
.pc-card .dref b{color:var(--ink);font-weight:600;margin-right:4px}
.zb{display:inline-grid;place-items:center;min-width:22px;height:22px;padding:0 5px;border-radius:11px;background:var(--acc);color:var(--sur);font:600 12px "IBM Plex Mono",monospace;margin-right:7px;vertical-align:1px}
.zb.sm{min-width:18px;height:18px;font-size:11px;border-radius:9px;margin-right:5px}
.use-line{font-size:12.5px;margin:2px 0 6px;max-width:none;color:var(--ink2)}
.use-line a{color:var(--ink2);text-decoration:none;border-bottom:1px dotted var(--mut)}
.use-line a:hover,.use-line a:focus{color:var(--acc)}
.zlegend{columns:2;column-gap:28px;font-size:13.5px;list-style:none;padding:0;margin:12px 0 4px;max-width:none}
.zlegend li{padding:3px 0;break-inside:avoid}
.zlegend a{color:var(--ink);text-decoration:none}
table.use td{font-size:12.5px;padding:6px 8px}
table.use td:nth-child(3){min-width:170px}
table.use td:nth-child(4){min-width:260px}
table.use td:nth-child(5){white-space:nowrap}
table.use tr:target td{background:var(--acc-bg)}
[id^="use-"]{scroll-margin-top:16px}
.drw .zf1{fill:color-mix(in srgb,var(--acc) 20%,var(--sur));stroke:currentColor;stroke-width:1}
.drw .zf2{fill:color-mix(in srgb,var(--warn) 30%,var(--sur));stroke:currentColor;stroke-width:1}
.drw .zf3{fill:color-mix(in srgb,var(--mut) 22%,var(--sur));stroke:currentColor;stroke-width:.8;stroke-dasharray:5 3}
.drw .zf3o{fill:none;stroke:currentColor;stroke-width:.8;stroke-dasharray:5 3}
.drw .zf4{fill:color-mix(in srgb,var(--good) 24%,var(--sur));stroke:currentColor;stroke-width:1}
.drw .zf5{fill:color-mix(in srgb,var(--steel) 30%,var(--sur));stroke:currentColor;stroke-width:1}
.drw .zf6{fill:color-mix(in srgb,var(--crit) 22%,var(--sur));stroke:currentColor;stroke-width:1}
.drw .zb-c{fill:var(--acc);stroke:var(--sur);stroke-width:2}
.drw .zb-t{font:600 16px "IBM Plex Mono",monospace;fill:var(--sur)}
.drw .zl{font:600 12px "IBM Plex Sans KR","Noto Sans KR",sans-serif;fill:var(--ink)}
@media (max-width:640px){.zlegend{columns:1}}
.lid{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--acc);font-weight:600;margin-right:4px}
.gsum{font-size:13px;color:var(--mut);font-weight:400;margin-left:8px}
table.cost td,table.dimt td{font-size:12.5px;padding:6px 8px}
table.aud td{font-size:12.5px;padding:6px 8px;vertical-align:top}
table.aud td:first-child{white-space:nowrap}
table.aud.cmp td:first-child{white-space:normal;min-width:96px}
table.aud.cmp td:nth-child(2),table.aud.cmp td:nth-child(3){min-width:210px}
table.aud.cmp td:nth-child(4),table.aud.cmp td:nth-child(5),table.aud.cand td:nth-child(3),table.aud.cand td:nth-child(4),table.aud.amp td:nth-child(3){text-align:right;white-space:nowrap}
table.aud.cand td:last-child,table.aud.amp td:last-child{min-width:260px}
table.aud.cand td:nth-child(2){min-width:180px}
table.cost td:nth-child(3),table.cost td:nth-child(4),table.cost td:nth-child(5),table.cost td:nth-child(6){text-align:right;white-space:nowrap}
table.dimt td:nth-child(3){text-align:right;white-space:nowrap}
table.budget td:nth-child(2),table.budget td:nth-child(3){text-align:right;white-space:nowrap}
.bar{height:8px;background:var(--rule);min-width:120px;border-radius:1px}
.bar i{display:block;height:100%;background:var(--acc)}
details.dims>summary,details.calc>summary{font-size:14px}
details.calc .cres{display:block;font-size:12.5px;color:var(--ink2);margin:2px 0 0 20px}
details.calc .cbody table.kv th{width:64px}
.small{font-size:12px}
ol.circ{padding-left:20px}
ol.circ li{margin:5px 0}
ol.steps>li{margin:10px 0}
ol.steps>li p{margin:4px 0}
ul.chg li{margin:6px 0;font-size:13.5px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));border:1px solid var(--rule);margin:22px 0 0}
.kpi div{padding:12px 14px;border-right:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.kpi b{display:block;font-family:"IBM Plex Mono",monospace;font-size:20px;font-weight:600;line-height:1.2}
.kpi b.ok{color:var(--good)}
.kpi span{font-size:11.5px;color:var(--mut)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.vid{border:1px solid var(--rule);background:var(--sur);padding:14px 16px}
.vid p{margin:6px 0;max-width:none}
table.req td:first-child{white-space:nowrap}
.sub{font-size:13.5px}
@media (max-width:640px){
.cards{grid-template-columns:1fr}
.pc-card{grid-template-columns:88px 1fr;gap:10px;padding:10px}
.pc-card .ph{width:88px;height:88px}
.pc-card table.kv th{width:76px}
.drw{padding:6px}
figure.drw svg{max-width:none;width:760px}
.drw figcaption::before{content:"도면을 옆으로 밀어 보세요. ";color:var(--acc)}
}
'''

TOC = [
    ('sum', '한눈에 보기'), ('video', '참고 영상 분석'), ('concept', '설계 개념'),
    ('dwg', '도면 11장'), ('dims', f'치수표 {len(F["dims"])}개'), ('mech', '기구 상세'),
    ('elec', '센서·전자·제어부·페달'), ('audio', '오디오 재설계(R25)'), ('body', '본체 구조(R26~R29)'), ('calc', f'계산 근거 {len(F["calcs"])}개'), ('print', '출력 계획·필라멘트'),
    ('use', '부품 쓰임새 — 어디에, 어떻게'), ('bom', '부품표 — 기본 구성'), ('cons', '소모품'), ('tools', '공구'), ('opt', '선택 항목'),
    ('budget', '비용 합계와 예산')] + ([('cost', '비용 절감안')] if FR else []) + [('order', '주문 방법'), ('check', '주문 전 확인할 것'),
    ('subst', '조달하며 바뀐 설계'), ('asm', '조립 순서'), ('risk', '위험과 대책'),
    ('req', '요구사항 대응표'), ('chg', '설계 검토 기록'), ('meth', '방법과 한계'),
]
toc_html = '<ol class="toc">' + ''.join(f'<li><a href="#{a}">{b}</a></li>' for a, b in TOC) + '</ol>'

VIDEO = 'https://www.youtube.com/watch?v=BAQskCuPaeY'

video_rows = [
    ('규모', '5옥타브 60건반 시제품. 약 7개월, 약 1,000시간, 50회 이상 반복'),
    ('핵심 아이디어', '<b>컴플라이언트 메커니즘</b>: 플라스틱이 휘어서 움직여 관절·체결구가 없다(플라스틱 상자 경첩과 같은 원리)'),
    ('건반 회전', '건반 뒤쪽의 얇은 4절 링크(플렉셔). 깊이를 짧게 두면서 긴 레버의 움직임을 흉내 낸다'),
    ('무게감', '컴플라이언트 힌지로 이어진 해머(무게 레버) 끝에 볼트·너트를 달아 무게와 관성을 흉내 낸다'),
    ('이스케이프먼트', '출력된 스프링 형상이 누르는 도중 촉각 턱을 만든다'),
    ('출력', '옥타브를 한 번에 뽑으면 서포트가 모델의 약 66%. 건반을 나눠 뽑고 도브테일로 조립해 필라멘트를 절반으로 줄였다'),
    ('부품 수', '옥타브당 53개(건반 12, 무게 레버 12, 연결 12, 덮개 12, 스페이서 5), 441 g'),
    ('센서 <a href="' + VIDEO + '&t=193s" rel="noopener">3:13</a>', '적외선 반사 센서가 흰 해머 위치를 연속으로 재고, 필터링한 위치로 속도를 구한다. 환경·제조 편차 때문에 보정이 필요하다'),
    ('전자부', '직접 설계한 PCB(보드당 센서 16), 데이지 체인, 2단 멀티플렉서, Pico 2W 1개, FluidSynth'),
    ('제작자가 밝힌 문제', '센서·건반 신뢰성 부족 → 다음 버전은 <b>PETG + 홀 센서</b>로 바꿀 계획'),
    ('시청자 반응', '기계 소음과 지연 지적. 시연에서는 무게감이 좋다는 반응도 있었다'),
]
take_rows = [
    ('가져옴', '플라스틱이 휘어 회전·복귀(핀·금속 스프링 없음)', '4절 링크 대신 <b>리프 한 장</b>(테이퍼 판)이 회전축과 스프링을 겸한다. 구조가 더 단순하다', 'R22, R23'),
    ('가져옴', '나눠 뽑고 끼워 맞춰 서포트를 없앰', '건반을 하나씩이 아니라 <b>백건 7개·흑건 5개를 각각 한 덩어리(콤)</b>로 뒤집어 뽑는다. 리프가 첫 10~13층이 된다', 'R20'),
    ('가져옴', '연속 위치로 속도 계산', '홀센서 위치를 건반당 5,952 Hz로 읽어 40%→90% 통과 시간으로 벨로시티', 'R2'),
    ('가져옴', '옥타브 모듈 + 멀티플렉서', 'C~B 모듈 7개가 출력물·기판·펌웨어까지 같다. 모듈마다 USB 1가닥', 'R17, R18'),
    ('가져옴', '제작자 교훈: PETG + 홀 센서', '전부 PETG, TI DRV5055A2 + Ø5×2 자석', '신뢰성'),
    ('줄여서', '볼트·너트 추', '무게 레버는 없다. 건반별 미세 조정만 텅스텐 퍼티(백 ≤6 g)로', 'R22'),
    ('안 가져옴', '무게 레버·스프링 턱·건반 덮개', '단순성 우선. 무게감은 리프 프리로드 42 g → 바닥 64 g', 'R22'),
    ('안 가져옴', '적외선 센서', '주변광·색·편차 보정 부담', '신뢰성'),
    ('안 가져옴', '전용 PCB·데이지 체인', '손 납땜 만능기판, 모듈 사이 전선 0', 'R19, R18'),
    ('주의', '기계 소음·지연', '업스톱·다운스톱 모두 펠트 3T, 스캔 지연 약 2.5 ms 창', 'R6, D8'),
]

KPI = [
    ('88', '건반(A0~C8) = 모듈 7 + 끝 부속 2'),
    ('164.5 mm', '옥타브 모듈 폭 · 깊이 212 · 높이 56.5'),
    ('10 mm', '딥(백건 앞끝) · 흑건 9.5'),
    ('42→64 g', '다운웨이트(시작→바닥)'),
    ('0.59 kg', '모듈 1개 · 모듈 사이 전선 0'),
    ('1254 × 410', '본체(mm) · 뒷바까지 직사각형(R27)'),
    ('5,952 Hz', '건반당 위치 스캔'),
    (won(T_BASE) + '원', f'기본 구성(소모품 제외) · 여유 {won(MARGIN)}원'),
    (won(T_CONS) + '원', '소모품(한도 밖 허용)'),
]
kpi_html = '<div class="kpi">' + ''.join(
    f'<div><b{" class=ok" if "여유" in s else ""}>{esc(v)}</b><span>{esc(s)}</span></div>' for v, s in KPI) + '</div>'

subst_rows = [
    ('척추 세트스크루 받침', '철 원판 Ø8×1', '황동 원판 Ø8×1(품절이면 Ø10×1, L38)', 'Ø10이면 원판 자리를 Ø8.1 → Ø10.1로(레일 벽 1.45, 면압 2.6 MPa). 황동은 비자성이라 센서에 영향 없음'),
    ('클램프 와셔', 'M3 대와셔 Ø9', 'M4 평와셔(외경 9, L36)', '외경이 같아 카운터보어 Ø9.5 그대로'),
    ('센서 바·기판 고정', 'M3 태핑 나사', 'M3 머신 나사로 자가 탭(구멍 Ø2.7~2.8)', 'PETG에 바로 나사산을 낸다'),
    ('열압입 인서트', 'M3×5.7', 'M3×5.0, 외경 4.6(L31)', '구멍 Ø4×6.5 그대로. 윗면에 맞춰 압입, 나사 물림 5.0 mm'),
    ('가이드 부싱·뒤 스톱', '부싱 크로스 0.5T, 펠트 1T', '0.5 mm 접착 펠트 1겹(부싱)·2겹(뒤 스톱, L40)', '부싱 틈 약 0.05 유지'),
    ('헤드폰 잭', 'PJ-313 패널형', 'PJ-313 PCB형(L15)', '왼쪽 끝 부속 볼에 작은 기판으로 고정'),
    ('CU 뒷면 스피커 단자', '단자 3조', '생략', '스피커선을 CU 안에서 바로 연결'),
    ('스피커 상자 밀폐', '실리콘 실란트', 'EVA 남는 조각 가스켓 + 목공본드(C21)', '추가 구매 없음'),
    ('필라멘트', '흰 2 / 검정 1 / 회색 2 = 5 kg', f'{FIL_SP.replace(" · ", " / ")} = {FIL_KG} kg', f'회색 순수 필요량 약 {FIL_G:.2f} kg(R26 스피커 앞판·뒷바 출력물 포함)'),
    ('틈 확인 도구', '0.15 mm 필러 게이지', '부품표에서 제외', '조립 검사에서 리브-탭 틈은 눈·손으로 확인'),
    ('페달(R24)', 'Roland DP-10 + 스위치 페달 2개 + 6.35 mm 잭 5개(85,760원)', '댐퍼 1개: 듀로 스위치 페달 홀센서 개조(L43) + 3 m 신호선(L50), 14,360원',
     '사용자 결정(댐퍼만 필요). 하프페달 신호 유지, 소스테누토·소프트 없음, 기본 구성 −71,400원'),
    ('오디오(R25)', f'DAC2 Pro + AAmp60 + 서브 앰프 + 릴레이, 스피커 3개(DMA105-4 ×2 + DCS165-4), 자작 합판·타공 그릴({AUD_OLD:,}원)',
     f'USB 동글 + TPA3110 보드(19 V) + 헤드폰 잭 노멀 접점 + 80 Hz RC, 스피커 2개(CW-100B25), 오꾸메·PETG 그릴({AUD_NEW:,}원)',
     f'사용자 결정(스피커 2개, 싼 앰프). P-145보다 약 +2~5 dB, 헤드폰 기계식 차단, 최저 옥타브는 배음. 기본 구성 −{AUD_OLD - AUD_NEW:,}원'),
    ('본체 뒤(R26~R29)', '케이블 공간 38 mm + PETG CU 상자 200×160×100 + 스피커 상자 2개, 전체 깊이 440',
     '뒷바 195 = 스피커 파트 2 + 가운데 유닛(건반 보관함·CU 칸·보조배터리 칸, 오꾸메 894×195×100), 1254 × 410 직사각형',
     '사용자 결정. 뒷바를 22 mm 띄운 아래 앞쪽이 케이블 통로라 깊이 −30 mm. 파트 5종을 따로 보관하고, 합판은 직선 재단 + 본드, 구멍은 출력 부품이 맡아 드릴이 필요 없다'),
    ('전원(R28)', '앰프용 19 V 어댑터 + DC 잭 + Pi용 5.1 V PD 어댑터(어댑터 2개)', 'USB-C PD 입력 하나 → 트리거 20 V → 퓨즈 → 스위치 → 앰프 + 5.1 V 강압(Pi·허브)',
     '벽 65 W 충전기(공구 목록에서 옮김) 또는 보조배터리(D19). 평균 약 12 W, 20,000 mAh로 약 5시간'),
    ('파트 사이 연결(R26)', '스피커 단자판(L11), 핀 헤더 6핀(끝 부속), 황동 스탠드오프(L37)', 'XT30 2쌍, JST-XH 6핀 2쌍, 토글 래치 2, CU 트레이 출력 보스',
     '모두 꽂았다 빼고, 합판에 구멍을 내지 않는다'),
    ('USB 허브 자리(R26)', 'CU 상자 안', f'보조배터리 칸 뒤 벽(228 mm라 CU 칸 안폭 {_dfmt(_P.CU_W)}에 안 들어감)', '모듈 USB 선이 낮은 칸막이(172×57) 위로 넘어간다'),
]

_ele = lambda k: [l for l in B[k] if '엘레파츠' in (l.get('store') or '')]
ELE_B, ELE_C = len(_ele('base')), len(_ele('consumable'))
ELE_SUP = sum(l['qty'] * l['unit_price_krw'] for k in ('base', 'consumable', 'tools') for l in _ele(k)) / 1.1
order_html = f'''
<div class="two sub">
<div><h4>판매처별 묶음</h4><ul>
<li><b>엘레파츠</b>: 부품 {ELE_B}줄 + 소모품 {ELE_C}줄 + 스트리퍼(T13). 공급가 약 {ELE_SUP / 10000:.1f}만원이라 무료배송(부품만 따로 사면 +3,000원).</li>
<li><b>아이씨뱅큐</b>: Pi 5는 단독 주문을 권한다(납기 '8주 이상' 표기, 단독 10.9만원이라 무료배송). 나머지 부품(앰프 보드·1 µF·PD 트리거·강압 모듈 포함)·공구는 한 주문(VAT 제외 5만원 이상 무료).</li>
<li><b>굿나잇몰(11번가)</b>: 볼트·와셔·M2.5·직결피스·육각렌치. 옵션으로 한 번에 담아 배송비 3,500원 1회.</li>
<li><b>11번가 세운상가새한음향</b>: 스피커 CW-100B25 2개(배송비 4,000원).</li>
<li><b>Apple Store 온라인</b>: USB-C–3.5 mm 헤드폰 잭 어댑터(무료배송).</li>
<li><b>메카솔루션</b>: Pi 방열판·12×18 기판(배송비 3,000원은 추정).</li>
</ul></div>
<div><h4>&nbsp;</h4><ul>
<li><b>11번가 개별 판매자</b>: 구름솜·펠트·EVA·인서트·텅스텐 퍼티. 판매자마다 배송비가 따로 붙는다(부품표에 반영).</li>
<li><b>3D프린터 스토어</b>: PETG {FIL_KG}스풀(배송비 4,000원 1회).</li>
<li><b>AliExpress</b>: 황동 원판·그로밋(Choice 무료배송). 가격을 캡차 때문에 다시 확인하지 못했다.</li>
<li><b>Pine64</b>: 인두 관련 공구 4종(관세는 결제 때 별도).</li>
<li><b>동진나무공장</b>: 오꾸메 합판 400×1200(스피커 파트)·600×1200(가운데 유닛, 무료 재단·배송) + 목공본드. 재단도(도면 8·11)를 함께 보낸다. 합배송 여부는 주문 화면에서 확인한다.</li>
<li><b>철물박사(metaldiy.com)</b>: 토글 래치 매미고리 1-20 2개(배송비 3,000원). <b>알씨뱅크</b>: JST-XH 6핀 연장선 2개(배송비 3,500원). <b>대건상사</b>: 건반 자석과 뚜껑 자석을 한 주문(배송비 2,500원 1회).</li>
<li><b>다나와 최저가</b>: 65 W PD 충전기(무료배송). 보조배터리(선택 O07)는 모루이 공식몰(무료배송).</li>
<li><b>피아노모아</b>: 댐퍼용 듀로 스위치 페달 1개(8,500원 + 배송비 3,000원). 받아서 홀센서로 개조한다.</li>
</ul></div></div>
<h4>예산 여유</h4>
<p class="sub">R26~R29 이후 기본 구성이 {won(T_BASE)}원으로 한도보다 {won(MARGIN)}원 적다. 그래서 예전의 '한도를 넘을 때 줄이는 순서'는 필요 없다. 더 줄이는 방법은 §{{{{#cost}}}}에 있다.</p>
'''

html_out = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toccata 제작 설계서 v3</title>
<meta name="description" content="3D 프린팅 88건반 디지털 피아노 Toccata의 새 설계: 옥타브 모듈형 컴플라이언트 건반 도면·치수, 부품표(사진·스펙·구매 링크), 비용 합계와 단계별 절감안.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>{CSS0}{EXTRA_CSS}{DRAW_CSS}{FR['css'] if FR else ''}</style></head>
<body><div class="wrap">

<header class="mast"><div><span class="eyebrow">Toccata · 제작 설계서 v3 · 2026-09-24 · R26~R29 2026-09-25</span>
<h1>리프 한 장으로 움직이는<br>옥타브 모듈 88건반</h1>
<p class="lede">기준 문서 <a href="../../hardware/mechanical/sound-requirements.md">sound-requirements.md</a>만 보고 새로 설계했다. 건반 구조와 실제 치수, 전체 부품(사진·세부 스펙·구매 링크·가격), 비용 합계를 한 문서에 모았다.</p></div>
<div class="ver"><b>{won(T_BASE)}원</b>기본 구성(소모품 제외)<br>한도 1,000,000원 · 여유 {won(MARGIN)}원<br>가격 확인 2026-09-24~25 · VAT 포함{('<br>절감안 ' + FR['recommended'] + ' ' + won(next(t for t in FR['tiers'] if t['key'] == FR['recommended'])['base']) + '원') if FR else ''}</div></header>
{kpi_html}
{toc_html}

<h2 id="sum"><span class="eyebrow">01</span>한눈에 보기</h2>
<div class="rec3">
<div class="prin"><b>건반: 출력물 5개 = 한 옥타브</b><p>백건 7개와 흑건 5개를 각각 한 덩어리(콤)로 뽑는다. 건반 뒤로 이어진 얇은 판(리프) 한 장이 회전축이자 복귀 스프링이다. 건반에 따로 붙는 부품은 자석 1개뿐이다.</p></div>
<div class="prin"><b>탈부착: 파트 5종을 모두 따로 든다</b><p>도~시 모듈 7개는 모두 같고, 도브테일로 위에서 끼우고 들어서 뺀다. 모듈 사이에는 전선이 없다. 뒷바도 스피커 파트 2개와 가운데 유닛으로 나뉘고 커넥터로만 잇는다(R26). 가장 무거운 가운데 유닛이 약 3.3 kg이다.</p></div>
<div class="prin"><b>비용: {won(T_BASE)}원</b><p>좌우 스피커 2개와 앰프까지 넣은 기본 구성이 100만원 안에 들어간다(여유 {won(MARGIN)}원). R25로 오디오를 다시 골라 {won(BASE_R24 - BASE_R26)}원 줄었고, R26~R29(뒷바·무선 전원·건반 보관함)로 {won(abs(T_BASE - BASE_R26))}원 {'늘었다' if T_BASE > BASE_R26 else '줄었다'}. 소모품 {won(T_CONS)}원과 공구 {won(T_TOOL)}원(가진 공구는 빼도 된다)은 별도다.</p></div>
</div>
{budget_table()}
<div class="callout"><p><b>오디오를 다시 골랐다(R25)</b></p><p>스피커는 좌우 2개(삼미 CW-100B25), 앰프는 TPA3110 보드 한 대, DAC는 Apple USB-C 동글이다. 오디오 관련 줄이 {won(AUD_OLD)}원에서 {won(AUD_NEW)}원이 됐다. 음량은 P-145보다 크고, 최저 옥타브는 작은 디지털 피아노처럼 배음으로 들린다. 비교와 근거는 <a href="#audio">§{{#audio}}</a>에 있다.</p></div>
<div class="callout"><p><b>파트별 분리 · 직사각형 본체 · 보조배터리(R26~R29)</b></p><p>본체 뒤를 깊이 195 mm 뒷바(스피커 파트 2 + 가운데 유닛)로 채워 1254 × 410 mm 직사각형이 됐다(이전 깊이 440). 뒷바 아래 앞쪽이 케이블 통로다. 가운데 유닛에 건반 보관함 · CU 칸 · 보조배터리 칸이 있고, 전원은 USB-C PD 입력 하나(벽 65 W 충전기 또는 보조배터리, 평균 약 12 W로 20,000 mAh면 약 5시간)다. 파트 사이는 도브테일·래치와 USB-C·3.5 mm·XT30·6핀 커넥터로만 잇는다. 자세한 내용은 <a href="#body">§{{#body}}</a>에 있다.</p></div>
{cost_callout()}
<div class="callout crit"><p><b>주문 전에 먼저 확인할 것 3가지</b></p>
<ol class="sub"><li>Raspberry Pi 5 2GB: 판매처 표기상 납기가 '8주 이상'이다. 주문 전에 납기를 문의하고, 엘레파츠 재입고 알림도 걸어 둔다.</li>
<li>전원은 USB-C PD 20 V가 나와야 한다(D19). 벽 충전기(L62)는 20 V를 낸다. 가진 보조배터리를 쓸 거면 출력 표기에 20V⎓3A(60 W) 이상이 있는지 먼저 확인하고, 없으면 선택 항목 O07을 산다. 20 V가 안 나오면 PD 트리거가 앰프를 켜지 못한다.</li>
<li>4067 모듈 660원(L19)은 비정상적으로 싸다. 주문 화면에서 가격·재고를 다시 확인한다.</li></ol>
<p>나머지 확인 사항은 <a href="#check">§{{#check}}</a>에 있다.</p></div>

<h2 id="video"><span class="eyebrow">02</span>참고 영상 분석</h2>
<p>dovetail studio, <a href="{VIDEO}" rel="noopener">“I 3D Printed a Working Piano”</a>(2026-08-03, 7분 57초). 자막과 5초 간격 장면 미리보기로 분석했다. 센서 구간은 <a href="{VIDEO}&t=193s" rel="noopener">3:13</a>부터다.</p>
<h3>영상에서 만든 것</h3>
{table([('항목', ''), ('영상의 방식', '')], [[a, b] for a, b in video_rows])}
<h3>Toccata에 옮긴 것과 뺀 것</h3>
<p>영상의 핵심인 “플라스틱이 휘어서 움직이고 스스로 돌아온다”를 유지하되, 영상보다 부품 수를 크게 줄였다. 영상은 옥타브당 53개, 이 설계는 출력물 5개다.</p>
{table([('구분', ''), ('영상', ''), ('Toccata', ''), ('관련', '')], [[f'<b>{a}</b>', b, c, f'<span class="mono">{e}</span>'] for a, b, c, e in take_rows])}

<h2 id="concept"><span class="eyebrow">03</span>설계 개념</h2>
<p>건반이 해야 하는 일은 네 가지뿐이다. 이 설계는 네 가지에 각각 부품 하나씩만 쓴다.</p>
<ol class="circ">
<li><b>회전·복귀 — 리프.</b> 건반 윗판이 뒤로 그대로 이어진 테이퍼 판이다(백건 두께 2.6·폭 11→15, 흑건 두께 2.0·폭 11→18, 길이 50). 누르면 리프가 휘며 건반이 백 3.35°·흑 4.62° 돌고, 손을 떼면 리프 탄성으로 돌아온다. 핀·축·금속 스프링이 없다.</li>
<li><b>정지 높이 — 수평 훅.</b> 척추를 백 8.61°·흑 10.76° 기울여 조이면 리프가 미리 휜다. 그래서 건반 앞의 크로스바가 프레임 훅(펠트 3T)을 위로 누른 채 쉰다. 높이는 훅이 정하므로 플라스틱이 시간이 지나 조금 느슨해져도 높이는 그대로다.</li>
<li><b>딥 — 앞 펠트 + 뒤 두 번째 바닥.</b> 백건 앞끝 10 mm, 흑건 9.5 mm에서 펠트 3T에 닿는다. 뒤쪽을 세게 눌러도 리프가 S자로 휘지 않게 뒤 스톱이 거의 동시에(틈 0.10) 받친다.</li>
<li><b>위치 측정 — 자석 + 홀센서.</b> 건반 밑면에 Ø5×2 자석 1개, 그 아래 센서 바에 TI DRV5055A2 1개. 건반당 5,952 Hz로 위치를 읽어 40%→90% 통과 시간으로 벨로시티를 낸다.</li>
</ol>
<p>무게감은 리프의 프리로드로 만든다. 누르기 시작할 때 42 g, 바닥에서 64 g인 선형 스프링 느낌이다. 콤 단위 무게는 척추의 세트스크루(1/8회전 = 백 2.4 g)로, 건반별 차이는 앞 바닥판 위 텅스텐 퍼티로 맞춘다. 영상의 볼트·너트 추를 조정용으로만 줄여 가져온 것이다.</p>
<h3>좌표계</h3>
{paras(fix(F['coordinate_system']))}

<h2 id="dwg"><span class="eyebrow">04</span>도면 11장</h2>
<p>모든 도면은 설계 좌표(mm)에서 직접 그렸다. 축척은 도면마다 다르며 아래 눈금 막대가 기준이다. 치수선(파란색)의 값을 CAD에 그대로 옮기면 된다. 도면에 없는 값은 <a href="#dims">§{{#dims}} 치수표</a>에 있다. 색: 흰·검은 판 = 건반, 파랑 = 리프(휘는 부분), 회색 = 고정 프레임, 주황 = 펠트, 빨강 점 = 자석, 노랑 = 홀센서, 초록 = 만능기판.</p>
{drawing('white_side', '백건(D) 측면 단면. 실선은 쉬는 상태, 점선은 끝까지 누른 상태(순간 회전 중심 (171.04, 40.96)으로 3.35° 회전). 리프·척추·훅·펠트·센서 바의 높이(z)와 앞뒤 위치(y).', 1)}
{drawing('black_side', '흑건(C#) 측면 단면. 흑건 리프는 백건 리프보다 12 mm 높은 z55.5 평면에 있어 평면에서 겹쳐도 닿지 않는다. 누른 상태는 중심 (170.24, 53.04)으로 4.62° 회전.', 2)}
{drawing('octave_plan', '옥타브 모듈 건반 평면. 백건 피치 23.5, 흑건 폭과 위치, 리프 테이퍼, 센서 열(y67), 척추(y196~209). 흑건 리프는 점선.', 3)}
{drawing('leaf', '리프 상세(평면). 모멘트에 맞춘 직선 테이퍼라 길이 전체의 응력이 고르다(백 5.7~6.0 MPa 정지, 8.0~8.3 MPa 바닥).', 4)}
{drawing('module_plan', '옥타브 모듈 프레임(키베드) 평면. 레일·가이드 탭·훅·스톱·센서 받침·척추 레일·뒷벽·도브테일이 한 번에 출력된다. 제어 기판과 리본 경로 포함.', 5)}
{drawing('dovetail', '모듈 결합 도브테일 상세. 뿌리 6, 끝 9, 깊이 4. 앞(높이 5.5)과 뒤(높이 14) 두 곳. 아래가 열린 암이라 위에서 내려 끼우고 들어서 뺀다.', 6)}
{drawing('assembly', '전체 배치 평면(R27). 88건반 본체(모듈 7 + 끝 부속 2) 뒤를 깊이 195 mm 뒷바(왼쪽 스피커 파트 · 가운데 유닛 · 오른쪽 스피커 파트)로 채워 1254 × 410 mm 직사각형이 됐다. 케이블 통로는 뒷바 아래 앞쪽(y215~258)에 있다.', 7)}
{drawing('spk_box', '스피커 파트(R25·R26). 위는 정면(배플)과 중앙 단면이다. 앞판은 PETG 출력(구멍·나사 자리 포함), 나머지는 오꾸메 11.5T 맞대기 + 목공본드, 외형 180×195×210, 내부 5.05 L. 22 mm 띄워 앞쪽 아래를 케이블 통로로 쓴다. 아래는 오꾸메 400×1200 재단도(10장)다.', 8)}
{drawing('audio_wiring', '오디오·전원 배선(R25·R28). USB-C PD 입력 하나(벽 충전기 또는 보조배터리) → PD 트리거 20 V → 퓨즈 → 스위치 → 앰프·5.1 V 강압(Pi·허브). 소리는 동글 → 왼쪽 볼 헤드폰 잭 → 노멀 접점 → 앰프 입력 잭 → 80 Hz RC → 앰프 → XT30 → 스피커.', 9)}
{drawing('rear_bar', '뒷바 구성(R26~R29). 위: 위에서 본 속 배치(건반 보관함·CU 칸·보조배터리 칸, XT30·도브테일·래치 자리). 아래: CU 칸을 지나는 옆 단면(건반 + 틈 3 + 뒷바 195, 22 mm 띄운 아래가 케이블 통로).', 10)}
{drawing('cn_cut', '가운데 유닛 재단도(R26). 오꾸메 600×1200 한 장에서 11장(바닥 2, 뚜껑 2, 앞판, 뒤판 2, 끝판 2, 칸막이 2)을 직선으로만 자른다. CU 칸 바닥·뚜껑과 I/O 판은 PETG 출력이다.', 11)}

<h2 id="dims"><span class="eyebrow">05</span>치수표 {len(F['dims'])}개</h2>
<p>CAD 모델링용 전체 치수다. 단위 mm, 좌표는 §{{#concept}}의 좌표계를 따른다. 누르면 펼쳐진다.</p>
{dims_block()}

<h2 id="mech"><span class="eyebrow">06</span>기구 상세</h2>
<h3>건반·리프·척추·스톱</h3>{rich(F['mechanism'])}
<h3>리프(플렉서)</h3>{rich(F['flexure'])}
<h3>끝까지 누른 상태</h3>{rich(F['pressed_state'])}
<h3>모듈 프레임</h3>{rich(F['module_frame'])}
<h3>모듈 결합(탈부착)</h3>{rich(F['inter_module'])}
<h3>끝 부속(A0~B0, C8)</h3>{rich(F['end_parts'])}

<h2 id="elec"><span class="eyebrow">07</span>센서·전자·제어부·페달</h2>
<h3>센싱</h3>{rich(F['sensing'])}
<h3>전자 배선(손 납땜)</h3>{rich(F['electronics'])}
<h3>제어부(CU)와 스피커</h3>{rich(F['control_unit'])}
<h3>페달</h3>{rich(F['pedals'])}

{audio_section()}

{body_section()}

<h2 id="calc"><span class="eyebrow">08</span>계산 근거 {len(F['calcs'])}개</h2>
<p>치수를 정한 계산이다. 제목 아래 줄이 결과이고, 누르면 식·입력·결론이 나온다.</p>
{calcs_block()}

<h2 id="print"><span class="eyebrow">09</span>출력 계획·필라멘트</h2>
{rich(F['printing'])}
{fil_table()}
<p class="mut">g 합 {won(fil_g)} g에 실패·낭비 10%를 더하면 약 {fil_g * 1.1 / 1000:.1f} kg이다. 색별 순수 필요량은 흰 약 {FIL_W:.2f} · 검정 약 {FIL_K:.2f} · 회색 약 {FIL_G:.2f} kg이라 {FIL_SP} = {FIL_KG} kg({FIL_KG}스풀)을 산다. R26~R29로 CU 상자(150 g)가 빠지고 스피커 앞판(310 g)·뒷바 출력물(388 g)·예비 콤 1세트(266 g)가 더해져 회색이 1스풀 늘었다.</p>

{usage_section()}

<h2 id="bom"><span class="eyebrow">10</span>부품표 — 기본 구성 {len(base)}줄 · {won(T_BASE)}원</h2>
<p>사진을 누르면 판매 페이지로 간다. 각 카드의 “세부 스펙”을 펼치면 규격, 설계에서 쓰이는 위치, 고른 이유가 나온다. 가격은 2026-09-24 판매 페이지 기준(R26~R29로 새로 넣은 부품은 9/25) VAT 포함이며, 같은 판매처 배송비는 한 줄에만 넣었다.</p>
{''.join(group_block(base, g, i) for i, g in enumerate(GROUP_ORDER))}
<details><summary><b>기본 구성 전체 비용표</b>({len(base)}줄)</summary>{cost_table(base)}</details>

<h2 id="cons"><span class="eyebrow">11</span>소모품 {len(cons)}줄 · {won(T_CONS)}원</h2>
<p>R21에 따라 100만원 한도에서 뺀 항목이다. 필라멘트, 케이블, 납·플럭스, 접착제처럼 쓰면 줄어드는 것들이다.</p>
<div class="cards">{''.join(part_card(l, 'cons') for l in cons)}</div>
<details><summary><b>소모품 비용표</b></summary>{cost_table(cons)}</details>

<h2 id="tools"><span class="eyebrow">12</span>공구 {len(tools)}줄 · {won(T_TOOL)}원</h2>
<p>이미 가진 것은 사지 않아도 된다. 예산과 별도다.</p>
<div class="cards">{''.join(part_card(l, 'tool') for l in tools)}</div>

<h2 id="opt"><span class="eyebrow">13</span>선택 항목(예산 밖)</h2>
{opt_rows()}
<div class="cards">{''.join(part_card(l, 'opt') for l in opt)}</div>

<h2 id="budget"><span class="eyebrow">14</span>비용 합계와 예산</h2>
{budget_table()}
<p>계산식은 Σ(수량 × 단가 + 배송비)다. 기본 구성은 한도보다 {won(MARGIN)}원 적다. 가격을 다시 확인하지 못한 항목(AliExpress 황동 원판 10,676원, 그로밋 3,040원, 메카솔루션 배송비 추정 3,000원)이 틀려도 여유 안에서 흡수될 것으로 본다.</p>
{f'<p>기본 구성을 더 줄이는 방법과 단계별 합계는 <a href="#cost">§{{{{#cost}}}}</a>에 정리했다.</p>' if FR else ''}

{f'<h2 id="cost"><span class="eyebrow">00</span>비용 절감안 — 어디까지 줄일 수 있나</h2><p>위 부품표를 8개 분야로 나눠 더 싼 방법을 찾고, 분야마다 별도 검증자가 링크·가격·호환성·요구사항 영향을 다시 확인했다. 검증을 통과한 안 {FR["n_ok"]}개를 서로 맞는 것끼리 묶어 네 단계(T1~T4)로 정리했다. 빠지는 부품 번호(L·C·T)를 누르면 위 부품표의 해당 카드로 간다.</p>' + FR['body'] if FR else ''}

<h2 id="order"><span class="eyebrow">15</span>주문 방법</h2>
{order_html}

<h2 id="check"><span class="eyebrow">16</span>주문 전 확인할 것</h2>
<ul class="sub">{''.join(f'<li>{inline(u, False)}</li>' for u in UNRES)}</ul>

<h2 id="subst"><span class="eyebrow">17</span>조달하며 바뀐 설계</h2>
<p>살 수 있는 부품에 맞춰 설계를 바꾼 곳이다. 본문과 도면에는 이미 반영했다(예: 철 원판 → 황동 원판).</p>
{table([('위치', ''), ('처음 설계', ''), ('바뀐 것', ''), ('영향', '')], [[esc(a), esc(b), esc(c), esc(e)] for a, b, c, e in subst_rows])}

<h2 id="asm"><span class="eyebrow">18</span>조립 순서</h2>
<p>단계 0의 쿠폰 시험으로 재료 강성과 수축률을 먼저 확인한 뒤 모듈 1개를 끝까지 만들어 본다. 나머지 모듈은 그다음에 만든다.</p>
{assembly_steps()}

<h2 id="risk"><span class="eyebrow">19</span>위험과 대책</h2>
{risk_table()}

<h2 id="req"><span class="eyebrow">20</span>요구사항 대응표</h2>
<p>R·D 번호는 <a href="../../hardware/mechanical/sound-requirements.md">sound-requirements.md</a>의 번호다.</p>
{req_table()}

<h2 id="chg"><span class="eyebrow">21</span>설계 검토 기록</h2>
<p>독립 검토 3건(기구·센싱·제작)이 초기안에서 찾은 문제와 최종 설계에서 고친 방법이다. 빨강은 치명, 노랑은 주요, 회색은 경미.</p>
{changelog()}

<h2 id="meth"><span class="eyebrow">22</span>방법과 한계</h2>
<ul class="sub">
<li>설계 기준은 sound-requirements.md(R1~R23, D1~D17)와 참고 영상뿐이다. 저장소의 이전 설계 자료는 보지 않았다. 이후 사용자 결정 R24~R29와 D18·D19를 더했다.</li>
<li>설계는 독립 초안 3개를 비교해 하나로 합친 뒤, 기구·센싱·제작 관점의 검토 3건을 반영했다. 부품은 7개 분야를 조사하고 판매 페이지·이미지·가격을 다시 확인했다.</li>
<li>치수·힘·응력은 PETG 탄성계수 1.5 GPa를 가정한 계산값이다. 실제 필라멘트와 프린터에 따라 달라지므로 단계 0 쿠폰으로 리프 힘과 수축률을 먼저 잰다.</li>
<li>피로 수명(약 10⁷회)은 외삽값이다. 쿠폰 10⁶회 반복 시험으로 확인한다.</li>
<li>프린터는 220×220 베드를 가정했다. 가장 큰 출력물은 프레임 168.5×212다.</li>
<li>가격은 2026-09-24 기준이며 바뀔 수 있다. AliExpress 가격 2건은 캡차 때문에 다시 확인하지 못했다.</li>
<li>제품 사진은 판매 페이지 이미지를 줄여 넣었다. 실제 상품 구성은 판매 페이지를 따른다.</li>
<li>R24(2026-09-24 사용자 결정)로 페달을 댐퍼 하나로 줄였다. DP-10 + 스위치 페달 2개 + 6.35 mm 잭 5개(85,760원)를 듀로 스위치 페달 홀센서 개조 + 3 m 신호선(14,360원)으로 바꿔 기본 구성이 981,023원에서 909,623원이 됐다.</li>
<li>R25(2026-09-24 사용자 결정)로 스피커를 좌우 2개로 줄이고 스피커·앰프를 싼 것으로 다시 골랐다. 스피커 13종과 앰프·DAC 구성 10종을 조사해 삼미 CW-100B25 + XH-A232(TPA3110) + Apple USB-C 동글로 정했고, 기본 구성이 {won(BASE_R24)}원에서 {won(T_BASE)}원이 됐다. 새 부품의 가격·링크·사진은 9/24 판매 페이지에서 확인했다. 음량·저음 값은 판매처 사양과 계산값이라 받은 뒤 측정으로 확인한다.</li>
<li>R26~R29(2026-09-25 사용자 결정)로 뒷공간을 뒷바로 채워 1254 × 410 mm 직사각형으로 만들고, 파트를 모두 따로 떼게 하고, USB-C PD 입력 하나로 벽 충전기·보조배터리를 받게 하고, 건반 보관함을 넣었다. 새 부품의 가격·링크·사진은 9/25 판매 페이지에서 확인했다. 전원 예산(평균 약 12 W, 순간 약 52 W)과 사용 시간(20,000 mAh로 약 5시간)은 계산값이라 설치 후 확인한다. 기본 구성은 {won(BASE_R26)}원에서 {won(T_BASE)}원이 됐다.</li>
{'<li>§{{#cost}}의 비용 절감안은 분야 8개 조사 → 분야별 반박 검증 → 단계 종합 → 비판 검토 순서로 만들었다. 단계 합계는 각 안의 부품 가격과 소모품·공구 증감으로 다시 계산했고, 비판 검토에서 찾은 보정(C07 제외, 양면테이프 1롤 안 제외, T4 콘덴서, 배송비 기준)을 반영했다. 해외 가격은 1 USD = 1,380원으로 환산했다.</li>' if FR else ''}
</ul>

<footer class="foot">Toccata 제작 설계서 v3 · 2026-09-24(R26~R29 2026-09-25) · 기준 문서 hardware/mechanical/sound-requirements.md · 오디오 R25 재조사는 §{{#audio}}, 이전 조사는 <a href="toccata-audio-chain.html">오디오 체인 조합 조사 보고서</a></footer>
</div>{FR['js'] if FR else ''}</body></html>'''

nums = {}
def _renum(m):
    nums[m.group(1)] = len(nums) + 1
    return f'<h2 id="{m.group(1)}"><span class="eyebrow">{len(nums):02d}</span>'
html_out = re.sub(r'<h2 id="([\w-]+)"><span class="eyebrow">\d+</span>', _renum, html_out)
html_out = re.sub(r'\{\{?#([\w-]+)\}\}?', lambda m: f'{nums[m.group(1)]:02d}', html_out)
if 'cost' in nums:
    html_out = html_out.replace('{{CH}}', f'{nums["cost"]:02d}')
assert '{{' not in html_out.replace('{{CH}}', ''), '자리표시가 남았다'
open(OUT, 'w').write(html_out)
print(OUT, f'{len(html_out.encode()) / 1e6:.2f} MB')
