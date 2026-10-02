"""bomFinal(기본·선택·공구) + 소모품(C01~C21, 검증 교체 반영) → bom_all.json"""
import json, copy
d = json.load(open('wf.json'))
bf = d['bomFinal']
cons = {l['line_id']: copy.deepcopy(l) for l in d['bom']['lines'] if l['consumable']}

# 검증 결과로 바뀐 소모품 3줄 (bomFinal notes ⑤, 9/24 브라우저·curl 확인)
cons['C13'].update(
    name='[케이블스토어] 프리즘 국산 스피커케이블 50C 16AWG, 7M [블랙/PRS-50B07]',
    role='AAmp60 → 위성 스피커 2개(각 약 0.8 m), ZK-TB21 → 서브(약 2 m) 배선. 설계 스펙 16AWG',
    specs=[{'k': '규격', 'v': '16AWG(1.31 mm²), 50가닥, 2선'},
           {'k': '길이', 'v': '7 m(주문 후 재단, 취소 불가)'},
           {'k': '가격', 'v': '13,000원 + VAT = 14,300원'},
           {'k': '배송', 'v': '평균발송 2.5일, M.O.Q 1'},
           {'k': '벗기기', 'v': '16AWG라 T07(AWG 20~30) 대신 T13 스트리퍼 사용'}],
    qty=1, purchase_unit='1개(7 m)', unit_price_krw=14300, shipping_krw=0,
    store='엘레파츠 (no=18388615)', url='https://www.eleparts.co.kr/goods/view?no=18388615',
    image_url='https://image3.compuzone.co.kr/img/product_img/2026/0206/1319682/1319682_600.jpg',
    why='검증에서 기존 Coms 10 m 선은 AWG 표기가 없고 약 20AWG로 추정돼 설계 16AWG와 달랐다. 설계 스펙대로 16AWG 7 m로 바꿨다.')
cons['C17'].update(
    name='[티테크놀로지] 국산 ㅡ자형 전원 파워케이블 AC 220V/10A, 0.75 mm²×3C, 1.5 m (C13)',
    role='19 V 어댑터(L06)의 AC 입력(C14 인렛)에 꽂는 전원 코드',
    specs=[{'k': '커넥터', 'v': '벽 플러그 ↔ IEC C13(PC 전원 코드형)'},
           {'k': '정격', 'v': 'AC 220 V / 10 A, 0.75 mm² × 3C'},
           {'k': '길이', 'v': '1.5 m'},
           {'k': '가격', 'v': '2,445원 + VAT = 2,690원, 평균발송 2.5일'}],
    qty=1, purchase_unit='1개', unit_price_krw=2690, shipping_krw=0,
    store='엘레파츠 (no=9073504)', url='https://www.eleparts.co.kr/goods/view?no=9073504',
    image_url='https://image3.compuzone.co.kr/img/product_img/2019/1108/616422/616422_600.jpg',
    why="L06 어댑터 상세 이미지에 AC 입력이 C14(3핀 각형)이고 '3구 각 파워코드 별매'로 적혀 있다. 처음 고른 크로바(C5) 코드는 꽂히지 않아 C13 코드로 바꿨다.")
cons['C21'] = dict(copy.deepcopy(cons['C18']), line_id='C21',
    name='오공205 목공용 접착제 800 g (목공본드)',
    role='스피커 밀폐 상자 3개(위성 4.8 L ×2, 서브 8 L) 합판 접합과 틈 밀봉',
    specs=[{'k': '용량', 'v': '800 g(옵션)'},
           {'k': '종류', 'v': '초산비닐 수지 에멀전(백색 목공본드)'},
           {'k': '가격', 'v': '5,000원 + 배송 3,500원(합판과 합배송 여부는 주문 시 확인)'}],
    qty=1, purchase_unit='1개', unit_price_krw=5000, shipping_krw=3500,
    store='동진나무공장 (product_no=798)', url='https://namugongjang.com/product/detail.html?product_no=798',
    image_url='https://namugongjang.com/web/product/big/202207/84482f69e4da853fd5429e665a0ddde8.jpg',
    design_ref='D12 밀폐 상자, D15', group='소모품',
    why='밀폐 상자에서 공기가 새면 저음이 줄어든다. 엘레파츠 오공 목공본드K 220 g은 M.O.Q 6이라 제외했다.')

# 검증 메모를 소모품 줄에 붙인다
notes = {}
for ch in d['checks']:
    for c in ch['checked']:
        if c['line_id'].startswith('C') and c['line_id'] not in ('C13', 'C17'):
            notes[c['line_id']] = c['issue']
for k, v in notes.items():
    if k in cons:
        cons[k]['check'] = v

out = {
    'base': bf['lines'],
    'consumable': [cons[k] for k in sorted(cons)],
    'tools': bf['tools'],
    'optional': bf['optional'],
    'budget_strategy': bf['budget_strategy'],
    'unresolved': bf['unresolved'],
    'notes': bf['notes'],
}
sub = lambda l: l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0)
for k in ('base', 'consumable', 'tools', 'optional'):
    print(k, len(out[k]), f"{sum(sub(l) for l in out[k]):,}")
json.dump(out, open('bom_all.json', 'w'), ensure_ascii=False, indent=1)
