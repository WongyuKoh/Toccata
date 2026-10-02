"""v4 건반 액션 부품 조사(costopt/result.json) → 선택기 카드(data_v4.json, imgs_v4.json) + 묶음 선택(presets.json)."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util, io, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('bd', os.path.join(HERE, 'build_data.py'))
with contextlib.redirect_stdout(io.StringIO()):
    bd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bd)
bd.IMGS.clear()

R3 = json.load(open(os.path.join(V4, 'costopt', 'result.json')))
R4 = json.load(open(os.path.join(V4, 'costopt_r4', 'parts.json')))
CHECK = {}
for c in R3['check']['results']:
    CHECK.setdefault(c['url'], []).append(c)
R = dict(parts=[p for p in R3['parts'] if p['part_id'] in R4['unchanged_ids']] + R4['parts'])
REMOVED = [p for p in R3['parts'] if p['part_id'] in R4['removed_ids']]

KNOWN = ['아이씨뱅큐', '엘레파츠', '굿나잇몰', '스튜디오분트', '대건상사', 'Bambu Lab']


def ship_group(store):
    s = store or ''
    for k in KNOWN:
        if k in s:
            return k
    n = re.sub(r'\s*\(.*$', '', s).strip()
    if not n or '픽업' in s or '동네' in s or '구매 없음' in s or '재사용' in s:
        return None
    return 'O:' + n


ORDER = ['weight', 'keyrod', 'levershaft', 'capstan', 'pins', 'tspring', 'felt2', 'pu', 'cloth', 'shim', 'graphite', 'cuttools', 'drill4']
R4_PARTS = set()
parts = {p['part_id']: p for p in R['parts']}
ORDER = [x for x in ORDER if x in parts] + [x for x in parts if x not in ORDER]
ship_extra = {}


def conv_option(p, o, oid):
    items = []
    fits = o['fits_design']
    notes = []
    for i, it in enumerate(o['items']):
        nm = it['name']
        if p['part_id'] == 'capstan' and ('너트' in nm or 'nut' in nm.lower()) and 'XHHD' in nm:
            continue  # counted once in the L31 nut card (2026-09-28: the old test missed the English name "hexagon nut")
        ver = bool(it.get('verified'))
        for c in CHECK.get(it.get('url') or '', []):
            if c['status'] != 'ok':
                ver = False if c['status'] in ('unverifiable', 'broken') else ver
                if c['status'] == 'mismatch_spec':
                    fits = False
                    notes.append('링크 재검증: ' + (c.get('note') or '')[:240])
                if c['status'] == 'price_changed' and c.get('found_price_krw'):
                    notes.append(f'링크 재검증: 가격이 {c["found_price_krw"]:,}원으로 바뀜')
        g = ship_group(it.get('store'))
        fee = it.get('shipping_krw') or 0
        if g and g.startswith('O:'):
            ship_extra[g] = max(ship_extra.get(g, 0), fee)
        key = bd.img_file(f'V-{p["part_id"]}-{oid}-{i}', it.get('image_file'))
        items.append(dict(name=nm, qty=it['qty'], unit=it['unit_krw'], b=o['bucket'], store=it.get('store', ''), ship=g, ship_fee=fee,
                          url=it.get('url', ''), note=it.get('note_ko', ''), spec=it.get('spec', ''), img=key, code=p['part_id'], verified=ver))
    return dict(id=oid, title=o['title_ko'], items=items, pros=[o.get('pros_ko', '')], cons=[o.get('cons_ko', '')],
                note=' '.join(filter(None, [o.get('risk_ko') and ('위험: ' + o['risk_ko']), *notes])), labor=o.get('extra_labor_ko', ''),
                verified=all(i['verified'] for i in items), fits=fits, src='v4 조사')


cards = []
for pid in ORDER:
    p = parts[pid]
    cur = conv_option(p, p['current'], 'cur')
    cur['title'] = '현재: ' + p['current']['title_ko']
    alts = [conv_option(p, a, f'a{i + 1}') for i, a in enumerate(p['alternatives'])]
    cards.append(dict(id='v4' + pid, cat='key', title=p['name_ko'], role=p['role_ko'] + ' · 필요량: ' + p['qty_needed'],
                      options=[cur] + alts, unused=p['if_unused_ko'], r4=pid in R4_PARTS, r4note=p.get('r4_note_ko', ''),
                      default='none' if pid == 'spring' else 'cur'))

# ---------------------------------------------------------------- r4.4 patch (2026-09-28)
# 스프링: 사용자가 한국미스미 C-UA90R5-3-0.5로 정함(spring 세션 W1_REQUEST.md). 에폭시: r4.4 고침 2(블록 두 옆면 접착).
# 경선용 니퍼: 스프링 다리 200번 자르기. 캡스턴 너트: L31과 이중 계산이던 것을 뺌. 가격은 9/28 판매 페이지에서 확인.
SPR = os.path.join(HERE, 'spring')
IMGD = os.path.join(V4, 'costopt', 'img')
byid = {c['id']: c for c in cards}


def item(name, qty, unit, b, store, ship, url, note, img, code, spec='', fee=0, ver=True):
    return dict(name=name, qty=qty, unit=unit, b=b, store=store, ship=ship, ship_fee=fee, url=url, note=note, spec=spec, img=img,
                code=code, verified=ver)


# 캡스턴: 너트 줄이 빠졌으니 제목·필요량 글도 맞춘다
cap = byid['v4capstan']
cap['title'] = '캡스턴 나사 M3×6 버튼헤드 (너트는 L31 M3 육각너트 카드)'
cap['role'] = cap['role'].replace('· 필요량: 나사 96개(건반 88 + 예비 8), 너트 96개',
                                  '· 필요량: 나사 92개(88 + 예비 4) → 100개. 너트 92개는 L31 M3 육각너트(100개)에 들어 있다')
for o in cap['options']:
    o['title'] = o['title'].replace(' + XHHD M3 너트 96개', '').replace(' + XHHD 너트', '')

# 비틀림 스프링: 현재안 = 미스미 100개, 직접 감기·주문 제작·V형은 대안
MISUMI_URL = 'https://kr.misumi-ec.com/vona2/detail/110310556289/?HissuCode=C-UA90R5-3-0.5'
ts = byid['v4tspring']
wind, custom, vtype = ts['options']
wind['id'] = 'wind'
wind['title'] = 'SUS304 스프링 강선 d0.5를 사서 직접 감기 (미스미와 같은 ID 5 · 3.25권으로)'
wind['pros'] = ['선값이 가장 싸다(18,000원 + 배송 5,000원). 다리 길이를 처음부터 22.3 / 8.0으로 만든다.']
wind['cons'] = ['100개를 손으로 감아야 한다(3~5시간). 권수·다리 각이 흩어지면 k_t도 흩어진다.',
                '9/28 사용자가 미스미 기성품으로 정해 대안으로 내렸다.']
wind['note'] = ('위험: 되튐 때문에 안지름이 심봉보다 커진다 — 처음 몇 개로 안지름 5.0이 나오는 심봉 굵기를 찾는다. '
                '선 표기가 SUS304H(FH)라 인장 강도 등급은 받은 뒤 확인한다.')
wind['labor'] = '심봉에 3.25권 감기 → 다리 22.3 · 8.0으로 자르기 → 다리 각 맞추기. 1개 2~3분, 100개 약 3~5시간. 처음 5개로 단계 0 시험 8(쉼 4.19, 바닥 6.03 N·mm ± 15 %)을 먼저 본다.'
custom['title'] = '스프링 제작소에 주문 제작 100개 — 다리까지 잘라 받음 (설계서 추정)'
custom['items'][0]['name'] = 'SUS304-WPB 비틀림 스프링 주문 제작 d0.5 × ID5 × 3.25권, 다리 22.3 / 8.0'
custom['items'][0]['spec'] = '미스미 형상과 같게 도면으로 견적'
custom['items'][0]['note'] = '확인 안 됨: 온라인 단가표가 있는 국내 토션 스프링 제작소를 찾지 못했다(케이원텍·레이원텍 등은 문의형). 값은 설계서 16장 추정 1개 200원이다.'
custom['pros'] = ['다리를 잘라 받으면 경선용 니퍼와 다리 자르기 200번이 필요 없다.']
vtype['note'] = (vtype.get('note') or '') + ' 9/28: 같은 선경·권수의 규격품(미스미 C-UA90R5-3-0.5)이 있어 이 안을 고를 이유가 적다.'
misumi = dict(
    id='cur', title='현재: 한국미스미 경제형 토션스프링 C-UA90R5-3-0.5 100개 (두 다리를 잘라 씀)', src='9/28 결정', verified=True, fits=True,
    items=[item('한국미스미 경제형 토션스프링 C-UA90R5-3-0.5 (SUS304-WPB, 내경 5 · 선경 0.5 · 3권 · 암 각 90° 오른쪽 감기, 암 50/50)', 100, 310, 'base',
                '한국미스미 (kr.misumi-ec.com)', 'O:한국미스미', MISUMI_URL,
                '9/28 페이지 확인: 1~99개 332원(VAT 포함 365원), 100~236개 282원(VAT 포함 310원). 88개만 사면 32,120원이라 100개가 더 싸다. '
                '재고품, 당일 출하 가능(18시 이후 주문은 다음 날 접수). VAT는 주문 합계에 붙어 실제 결제는 약 31,020원. '
                '배송비는 무료로 알려져 있으나 결제 화면에서 확인하지 못했다.',
                bd.img_file('V-tspring-misumi', os.path.join(SPR, 'img_misumi_spring.jpg')), 'tspring',
                spec='긴 다리 22.3 · 짧은 다리 8.0 mm로 자름. k_t 8.44 N·mm/rad, 설치 자유각 −28.4°')],
    pros=['규격품이라 스프링마다 k_t가 고르다(카탈로그 k표와 0.1 % 안에서 맞음).', '감는 일(100개, 3~5시간)이 없다. 재고품이라 바로 온다.',
          'DW 51.89 / 50.99 g, 연타 16.30 / 18.87 Hz로 원안과 같다(spring 세션 계산).'],
    cons=['두 다리를 모두 잘라야 한다: 100개 × 2 = 200번. 스프링강이라 경선용 니퍼가 필요하다(공구 카드).',
          '손으로 25° 들 때 토크 8.06 N·mm가 카탈로그 55° 값 7.52보다 7 % 크다(암이 짧아서) — 단계 0에서 확인.'],
    note='두 다리를 22.3 / 8.0 mm로 자른다. 200번 자른다. 미스미 암 길이 지정 가공(C형)은 3~49 mm · 1 mm 단위라 짧은 다리 8은 되지만 긴 다리 22.3은 만들 수 없어 기성품(50/50)을 잘라 쓴다.',
    labor='다리 자르기 200번(출력 지그에 끼워 길이를 맞춘다).')
ts['options'] = [misumi, wind, custom, vtype]
ts['title'] = '비틀림 보조 스프링 — 미스미 C-UA90R5-3-0.5 (SUS304-WPB d0.5 · ID5 · 3권 · 90°)'
ts['role'] = ('레버 봉 위 허브 주머니(Ø6.6×3.0)에 코일을 넣고, 짧은 다리(8.0으로 자름)는 허브의 가둠 홈(폭 0.7), 긴 다리(22.3으로 자름)는 뒷벽 홈(깊이 3.2)에 28.4° 감아 끼운다. '
              '쉼 4.19 / 바닥 6.03 N·mm. DW 51.9 g과 연타 16.3 / 18.8 Hz는 원안과 같다. · 필요량: 100개 (88 + 예비 12)')
ts['r4note'] = '9/28 결정: 주문 제작·직접 감기 대신 미스미 기성품. 주머니 Ø6.6, 홈 폭 2.4 · 깊이 3.2, 짧은 다리 홈은 r4.4 다음 판 도면에 들어간다.'

# 강철 블록 접착제 (r4.4 고침 2b, 9/29): 5분 에폭시 → MS 폴리머 탄성 접착제.
# 딱딱한 에폭시는 PETG·강철 열팽창 차이로 ΔT 15 K에서 모서리 전단 2.24 MPa → 떨어짐. 에폭시 안은 대안으로 남기고 "설계와 맞지 않음"으로 표시.
ELE_EPOXY = 'https://www.eleparts.co.kr/goods/view?no=16596617'
epoxy_img = bd.img_file('V-epoxy2-loctite14', os.path.join(IMGD, 'soft_epoxy_loctite14_ele.jpg'))
TDS = '제조사 자료(TDS 1365868): 샌드블라스트 강판 인장 전단 17.2 MPa(2,500 psi, 24 h). 굳기 시작 5~7분, 쓸 수 있는 강도 20분, 완전 경화 24 h, 사용 온도 49 °C까지.'
EPOXY = [
        dict(id='cur', title='현재: 엘레파츠 LOCTITE 5분 에폭시 14 mL × 2 (28 mL)', src='9/28 조사', verified=True, fits=True,
             items=[item('[LOCTITE] 에폭시접착제 / 5분 에폭시 14ml (1365868)', 2, 4260, 'consumable', '엘레파츠 (eleparts.co.kr)', '엘레파츠', ELE_EPOXY,
                         '9/28 페이지: 3,872.73원(VAT 별도, 16 % 할인) → 4,260원, 평균 발송 1.5일. 9/27 조사 때는 1인 1개 제한이 보였다 — 2개가 안 되면 대안 a1.',
                         epoxy_img, 'epoxy2', spec='2액형 5분 경화, 14 mL 자동 혼합 주사기')],
             pros=[TDS, '엘레파츠 합배송이라 배송비가 붙지 않는다.'],
             cons=['PETG에 대한 강도 자료는 없다(단계 0 시험 20으로 확인).'], note='', labor=''),
        dict(id='a1', title='나비엠알오 같은 제품 14 mL × 2 (엘레파츠 수량 제한일 때)', src='9/28 조사', verified=True, fits=True,
             items=[item('[록타이트] 5분 인스턴트 믹스 에폭시 14 mL', 2, 4389, 'consumable', '나비엠알오 (navimro.com, g/310655)', 'O:나비엠알오',
                         'https://www.navimro.com/g/310655/', '9/28 페이지: 3,990원(VAT 별도) → 4,389원, 오늘 출하.',
                         bd.img_file('V-epoxy2-navi14', os.path.join(SPR, 'img_K15347441.jpg')), 'epoxy2', fee=3300)],
             pros=[TDS, '나비엠알오 주문(PU 폼·드릴)과 합배송.'], cons=['엘레파츠보다 258원 비싸다.'], note='', labor=''),
        dict(id='a2', title='록타이트 EA 9017 25 mL 1개 (양이 빠듯함)', src='9/28 조사', verified=True, fits=True,
             items=[item('[록타이트] 2액형 에폭시계 접착제 EA 9017 (Fixmaster Fast Cure Poxy Pak) 25 mL', 1, 10989, 'consumable',
                         '나비엠알오 (navimro.com, g/1699673)', 'O:나비엠알오', 'https://www.navimro.com/g/1699673/', '9/28 페이지: 9,990원(VAT 별도) → 10,989원, 오늘 출하.',
                         bd.img_file('V-epoxy2-ea9017', os.path.join(SPR, 'img_K48659403.jpg')), 'epoxy2', fee=3300)],
             pros=['제조사 자료: 전단 강도 15.9 MPa(2,300 psi, ASTM D1002, 금속). 4~6분에 손으로 만질 강도, 45~60분 경화, 149 °C까지.'],
             cons=['25 mL라 필요량(약 20~28 mL)을 겨우 채운다.', 'TDS가 열가소성 플라스틱은 응력 균열을 먼저 확인하라고 한다.'], note='', labor=''),
        dict(id='a3', title='록타이트 투명 고강도 에폭시 25 mL 1개 (가장 쌈, 강도 자료 없음)', src='9/28 조사', verified=True, fits=True,
             items=[item('[록타이트] 에폭시접착제 투명 고강도 25 mL (IDH 3034799)', 1, 4279, 'consumable', '나비엠알오 (navimro.com, g/3263753)', 'O:나비엠알오',
                         'https://www.navimro.com/g/3263753/', '9/28 페이지: 3,890원(VAT 별도) → 4,279원, 오늘 출하. 경화 시간·강도 자료를 찾지 못했다.',
                         bd.img_file('V-epoxy2-3034799', os.path.join(SPR, 'img_K92925824.jpg')), 'epoxy2', fee=3300)],
             pros=['가장 싸다.'], cons=['공개된 전단 강도가 없다.', '25 mL라 필요량(약 20~28 mL)을 겨우 채운다.'], note='', labor=''),
]
EPOXY_BAD = '설계와 맞지 않음 — 온도 변화에 떨어짐'
for i, o in enumerate(EPOXY):
    o['id'] = f'e{i + 1}'
    o['title'] = '에폭시: ' + o['title'].replace('현재: ', '')
    o['fits'] = False
    o['fitlabel'] = EPOXY_BAD
    o['cons'] = ['굳으면 딱딱해 PETG·강철 열팽창 차이를 받지 못한다: ΔT 15 K에서 모서리 전단 2.24 MPa → 떨어진다(r4.4 고침 2b).'] + o['cons']
    o['note'] = EPOXY_BAD + '. 9/29 설계가 MS 폴리머 탄성 접착제로 바뀌었다.'
    for it in o['items']:
        it['note'] = it['note'].replace('대안 a1', '에폭시 e2(나비엠알오)')

MSD = os.path.join(HERE, 'msbond')
SX_TDS = ('제조사 기술 자료(슈퍼X No.8008, 접착층 0.1 mm, 23 °C 4주): 인장 전단 PET 2.8 MPa(대부분 접착제 안쪽이 끊어짐), '
          '연강 4.8 MPa, ABS 2.8 MPa. 설계값 1.5 MPa보다 크다.')
SX_PROP = '굳은 뒤 쇼어 A 43~50(G 약 0.6~0.8 MPa로 추정), 늘어남 200 %, −40~120 °C. 1액형이라 섞지 않는다.'
MS_OPTS = [
    dict(id='cur', title='현재: 세메다인 슈퍼X 백색 20 mL × 2 (40 mL) — 11번가 주영종합상사', src='9/29 조사', verified=True, fits=True,
         items=[item('세메다인 슈퍼X 8008 탄성접착제 백색 20 mL (AX-022)', 2, 8000, 'consumable', '11번가 주영종합상사 (11st.co.kr/products/7459325704)',
                     'O:11번가 주영종합상사', 'https://www.11st.co.kr/products/7459325704',
                     '9/29 페이지: 8,000원(VAT 포함), 배송비 3,000원(주문 1번), 판매 중, 9/30 도착 예정. 재고 수량은 나오지 않는다.',
                     bd.img_file('V-msbond-sx-white', os.path.join(MSD, 'sx_white_11st.jpg')), 'msbond', fee=3000,
                     spec='1액형 습기 경화 MS 폴리머(변성 실리콘) 탄성 접착제, 20 mL 튜브, 백색')],
         pros=[SX_TDS, SX_PROP, '같은 제품을 여러 곳에서 판다(흑색은 대안 a1).'],
         cons=['PETG 자료는 없다 — PET 값으로 보고 단계 0 시험 20으로 확인한다.', '투명형(クリア)은 PET 0.9 MPa로 약하다 — 백색·흑색만 산다.',
               '11번가 배송비 3,000원이 따로 붙는다.'],
         note='', labor='블록 두 면에 얇게 펴 바르고 10분 안에 끼운다(겉이 굳기 시작하는 시간 약 11~13분). 한 번에 8~10개씩.'),
    dict(id='a1', title='세메다인 슈퍼X 흑색 20 mL × 2 — 11번가 MRO마트 (백색 품절일 때)', src='9/29 조사', verified=True, fits=True,
         items=[item('세메다인 슈퍼X 탄성접착제 흑색 20 mL (AX-035)', 2, 8630, 'consumable', '11번가 MRO마트_3M대리점 (11st.co.kr/products/2826567875)',
                     'O:11번가 MRO마트_3M대리점', 'https://www.11st.co.kr/products/2826567875',
                     '9/29 페이지: 9,700원에서 11 % 할인 → 8,630원(VAT 포함), 배송비 3,000원, 9/30 도착 예정. 흑색 판매 중, 백색은 품절. 투명은 고르지 않는다.',
                     bd.img_file('V-msbond-sx-black', os.path.join(MSD, 'sx_black_11st.jpg')), 'msbond', fee=3000,
                     spec='슈퍼X 흑색 20 mL 튜브')],
         pros=['같은 슈퍼X다. 제조사 일반 물성의 인장 전단 강도가 백색과 같다(4.0 MPa).'],
         cons=['백색보다 2개에 1,260원 비싸다.'], note='', labor=''),
    dict(id='a2', title='나비엠알오 세메다인 SUPER-X 백색 170 g 1개 (합배송, 많이 남음)', src='9/29 조사', verified=True, fits=True,
         items=[item('[세메다인] 강력 접착제 SUPER-X 백색 170 g (약 130 mL, K01646488)', 1, 31889, 'consumable', '나비엠알오 (navimro.com, g/41866)',
                     'O:나비엠알오', 'https://www.navimro.com/g/41866/',
                     '9/29 페이지: 28,990원(VAT 별도) → 31,889원, 오늘 출하. "산업용·전문가용 — 가정·일반 사무실 구매 불가" 표기가 있다.',
                     bd.img_file('V-msbond-sx-navi170', os.path.join(MSD, 'sx_white170_navi.jpg')), 'msbond', fee=3300,
                     spec='슈퍼X 백색 170 g 튜브')],
         pros=['나비엠알오 주문(PU 폼·드릴·니퍼)과 합배송이라 배송비가 더 붙지 않는다.', '같은 슈퍼X 백색이다(강도 자료 같음).'],
         cons=['약 90 mL가 남는다. 배송비를 넣어도 11번가 안보다 약 12,900원 비싸다.', '산업용 표기라 개인 구매가 막힐 수 있다.'], note='', labor=''),
    dict(id='a3', title='코니시 본드 울트라 다용도 SU 프리미엄 소프트 25 mL × 3 (해외 구매대행, 강도 숫자 없음)', src='9/29 조사', verified=True, fits=True,
         items=[item('[코니시] 본드 울트라 다용도 SU 프리미엄 소프트 투명 25 mL 3개 묶음', 1, 48300, 'consumable', '11번가 tany3 (해외 구매대행)',
                     'O:11번가 tany3', 'https://www.11st.co.kr/products/8839602242',
                     '9/29 페이지: 48,300원(VAT 포함), 무료배송, 해외 항공 배송(구매대행)이라 오래 걸린다.',
                     bd.img_file('V-msbond-konishi', os.path.join(MSD, 'konishi_11st.jpg')), 'msbond', spec='SU 폴리머(실릴 변성 우레탄) 탄성 접착제')],
         pros=['열팽창이 다른 재료·충격·냉열 반복용 탄성 접착제(제조사). 75 mL로 넉넉하다.'],
         cons=['제조사 자료에 PET·강철 인장 전단 숫자가 없다(콘크리트 상대 막대그래프뿐).', '가장 비싸고 해외 배송이라 느리다.'], note='', labor=''),
]
cards.append(dict(
    id='v4msbond', cat='key', title='MS 폴리머 탄성 접착제 — 강철 블록을 레버 캐리어에 붙임', r4=False, default='cur',
    role=('r4.4 고침 2b: 강철 블록(SS400 9×19×40)의 두 19×40 옆면을 캐리어 옆벽에 붙인다(틈 한쪽 0.1 mm). 굳어도 고무처럼 늘어나 '
          'PETG·강철 열팽창 차이를 받는다(설계 G 약 1 MPa, 접착 강도 1.5 MPa). '
          '· 필요량: 레버 92개 × 1,520 mm² × 0.1 mm = 14 mL + 삐져나옴·튜브 잔량·단계 0 시험편 → 약 25~40 mL (20 mL 2개)'),
    r4note=('PETG 면은 #120 사포로 갈고 알코올로 닦아 말린다. 강철 면도 알코올로 닦는다. 1~2시간이면 안 움직이고 24~48시간이면 쓸 수 있는 강도다. '
            '습기로 굳어 닫힌 틈 가운데는 더 늦으니 조립 뒤 하루 넘게 둔다. '
            '단계 0 시험 20: 같은 0.1 mm 틈 시험편을 5 ↔ 45 °C 3번 돌린 뒤 1.5 MPa를 넘는지 본다.'),
    unused='빼면 안 된다(r4.4 고침 2b). 블록 옆면 접착이 설계의 전제다. 강도 자료가 있는 MS 폴리머(백색·흑색)가 30 mL쯤 있을 때만 사용 안함.',
    options=MS_OPTS + EPOXY))

# 경선용(피아노선) 니퍼 (r4.4 신규 공구)
cards.append(dict(
    id='v4wirecut', cat='tool', title='경선용(피아노선) 니퍼 — 스프링 다리 자르기', r4=False, default='cur',
    role=('미스미 스프링의 두 다리를 22.3 / 8.0 mm로 자른다(100개 × 2 = 200번). SUS304-WPB 0.5 mm 스프링 선은 HRC 45~50 정도로 단단하다. '
          '지금 공구의 니퍼(CT13 JAKEMY JM-CT2-2)는 플라스틱·구리선용이라 200번 자르면 날이 상한다. 쇠톱은 0.5 mm 선에 맞지 않는다. · 필요량: 1개 (피아노선 0.5 mm 이상 정격)'),
    r4note='짧은 다리 2.5 mm는 코일 가까이 자르므로 머리가 작은 옆 자르기 니퍼가 편하다. 날 끝이 아니라 날 뿌리 쪽으로 자른다.',
    unused='피아노선 0.5 mm 이상 정격 니퍼가 이미 있을 때만. 스프링을 다리까지 잘라 받는 주문 제작(스프링 카드)을 고르면 필요 없다.',
    options=[
        dict(id='cur', title='현재: 후지야 편심강력 니퍼 FKN-150G (피아노선 1.0 mm)', src='9/28 조사', verified=True, fits=True,
             items=[item('[후지야] 편심강력 니퍼 FKN-150G (150 mm, 피아노선 1.0 · 철선 2.0 · 동선 3.0)', 1, 21989, 'tool', '나비엠알오 (navimro.com, g/3523817)',
                         'O:나비엠알오', 'https://www.navimro.com/g/3523817/', '9/28 페이지: 19,990원(VAT 별도) → 21,989원. 해외 직수입, 10/06 출하 예정, 반품 불가.',
                         bd.img_file('V-wirecut-fkn150', os.path.join(SPR, 'img_K94434966.jpg')), 'wirecut', fee=3300, spec='피아노선 1.0 mm 정격 — SUS304-WPB 0.5 mm 스프링 다리 200번')],
             pros=['피아노선 정격 1.0 mm로 0.5 mm 선에 두 배 여유가 있다.', '나비엠알오 주문(PU 폼·드릴)과 합배송.'],
             cons=['해외 직수입이라 10/06 출하, 반품 불가.'], note='', labor=''),
        dict(id='a1', title='쓰리픽스 강선용 니퍼 NP-190G (피아노선 2.0 mm, 오늘 출하)', src='9/28 조사', verified=True, fits=True,
             items=[item('[쓰리픽스] 강선용 니퍼 NP-190G (190 mm, 피아노선 2.0 · 철선 2.6 · 동선 3.2, 일본)', 1, 32989, 'tool', '나비엠알오 (navimro.com, g/68245)',
                         'O:나비엠알오', 'https://www.navimro.com/g/68245/', '9/28 페이지: 29,990원(VAT 별도) → 32,989원, 오늘 출하.',
                         bd.img_file('V-wirecut-np190g', os.path.join(SPR, 'img_K01088539.jpg')), 'wirecut', fee=3300, spec='피아노선 2.0 mm 정격 — SUS304-WPB 0.5 mm 스프링 다리 200번')],
             pros=['여유가 가장 크다(피아노선 2.0 mm). 일본산, 바로 온다.'], cons=['190 mm로 크고 가장 비싸다.'], note='', labor=''),
        dict(id='a2', title="엘레파츠 Pro'sKit 8PK-905 (피아노선 0.5 mm 정격, 싼 안)", src='9/28 조사', verified=True, fits=True,
             items=[item("[Prokit] 8PK-905 컷팅 플라이어 — 가는선 및 피아노선 절단용 (125 mm)", 1, 11000, 'tool', '엘레파츠 (eleparts.co.kr, no=3345626)', '엘레파츠',
                         'https://www.eleparts.co.kr/goods/view?no=3345626',
                         "9/28 페이지: 10,000원(VAT 별도) → 11,000원, 평균 발송 3일. 제조사 표기: 피아노선 Ø0.5 mm, 날 HRC 62 ± 3. 같은 공구가 나비엠알오에서 컴스 T8194(14,289원).",
                         bd.img_file('V-wirecut-8pk905', os.path.join(SPR, 'img_K51825184.jpg')), 'wirecut', spec='피아노선 0.5 mm 정격 — SUS304-WPB 0.5 mm 스프링 다리 200번')],
             pros=['엘레파츠 합배송이라 배송비가 없고 10,989원 싸다. 머리가 작아 짧은 다리 자르기에 좋다.'],
             cons=['정격이 0.5 mm로 딱 맞아 여유가 없다. 날 뿌리 쪽으로 자르고, 날이 상하면 바꾼다.'], note='', labor=''),
    ]))

ship = {k: dict(fee=v, b='base', label=k[2:]) for k, v in ship_extra.items()}


# ---------------------------------------------------------------- presets (r4): cheapest verified option that fits the design
def best(c):
    cur = c['options'][0]
    cands = [o for o in c['options'][1:] if o.get('fits') and o.get('verified') and not any(w in o['title'] for w in ('가진', '생략', '외주', '가지고')) and sum(i['qty'] * i['unit'] for i in o['items']) < sum(i['qty'] * i['unit'] for i in cur['items'])]
    return min(cands, key=lambda o: sum(i['qty'] * i['unit'] for i in o['items']))['id'] if cands else None
# ---------------------------------------------------------------- 9/30 판매처 변경: OHP 필름 (사용자 결정; 가격은 9/30 페이지 확인)
shim = byid['v4shim']
_prev = json.loads(json.dumps(shim['options'][0]))
_prev.update(id='prev', title='이전: 11번가 핑블샵 A4 OHP 필름 100㎛ 20매 (5,980원)', src='9/29 목록')
_pi = _prev['items'][0]
_cur = dict(id='cur', title='현재: 나비엠알오 카피어랜드 OHP 필름 A4 흑백 레이저용 1PK (9/30 변경)',
            items=[item('[카피어랜드] OHP 필름 (A4) 흑백 레이저용 1PK (나비엠알오 K02664266)', 1, 2739, _pi['b'], '나비엠알오 (navimro.com, g/37021)',
                        'O:나비엠알오', 'https://www.navimro.com/g/37021/',
                        '9/30 판매처 변경(이전 11번가 핑블샵 5,980원). 페이지에 두께·매수 표기가 없다 → 받으면 캘리퍼로 0.1 mm인지 확인(PET 심 한 장 = 0.1 mm가 설계값)',
                        bd.img_file('V-shim-navimro', '/private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/2f19e142-4ac2-4c90-bd1e-b3b469f97487/scratchpad/v4/costsel/vendor930/ohp_navimro.jpg'), _pi['code'], spec='A4 OHP 필름(흑백 레이저용) — 페이지에 두께·매수 표기 없음, 받으면 0.1 mm인지 확인', fee=3300)],
            pros=['나비엠알오는 PORON·하네나이트 주문과 같이 와서 배송비가 더 들지 않는다', '가장 싸다'],
            cons=['두께·매수 표기가 없어 받은 뒤 확인해야 한다'], note='', labor='', verified=True, fits=True, src='9/30 판매처 변경')
shim['options'] = [_cur, _prev] + shim['options'][1:]

# ---------------------------------------------------------------- R31 터치스크린 (9/30 사용자 요청, 10/1 사용자 선택 B1 = Waveshare 7-DSI-TOUCH-C; 값은 9/30 밤~10/1 새벽 판매 페이지)
_gn = bd.ship_key('굿나잇몰', '11번가')
_EL = '엘레파츠'
_IMG = '/private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/2f19e142-4ac2-4c90-bd1e-b3b469f97487/scratchpad'
def _jump():
    return [item('[엘레파츠] 실리콘 점퍼 케이블 26AWG-RED (20cm, F/F)', 1, 451, 'consumable', '엘레파츠 (eleparts.co.kr, no=9461190)', _EL, 'https://www.eleparts.co.kr/goods/view?no=9461190',
                 '화면 5 V 연장 1단(Pi GPIO 2번)', None, 'v4touch'),
            item('[엘레파츠] 실리콘 점퍼 케이블 26AWG-BLACK (20cm, F/F)', 1, 451, 'consumable', '엘레파츠 (eleparts.co.kr, no=9461199)', _EL, 'https://www.eleparts.co.kr/goods/view?no=9461199',
                 '화면 GND 연장 1단(Pi GPIO 6번)', None, 'v4touch'),
            item('[엘레파츠] 실리콘 점퍼 케이블 26AWG-RED (20cm, M/M)', 1, 451, 'consumable', '엘레파츠 (eleparts.co.kr, no=9756990)', _EL, 'https://www.eleparts.co.kr/goods/view?no=9756990',
                 '5 V 연장 2단(화면 동봉 전원선의 2.54 하우징에 꽂음)', None, 'v4touch'),
            item('[엘레파츠] 실리콘 점퍼 케이블 26AWG-BLACK (20cm, M/M)', 1, 451, 'consumable', '엘레파츠 (eleparts.co.kr, no=9756998)', _EL, 'https://www.eleparts.co.kr/goods/view?no=9756998',
                 'GND 연장 2단', None, 'v4touch')]
def _m3x20():
    return item('스텐 유두 렌치볼트 M3 × 20 mm (굿나잇몰, 기존 볼트 주문에 옵션 추가)', 4, 100, 'base', '11번가 굿나잇몰', _gn, 'https://www.11st.co.kr/products/4236198413',
                '경첩 축 2 + 받침다리 축 1 + 예비 1, PETG 구멍에 직접 탭. 옵션 가격은 M3×6·×10 가격에서 추정', None, 'v4touch', ver=False)
def _sc1132():
    return item('Raspberry Pi 5 공식 디스플레이 리본 Standard–Mini 300 mm (SC1132)', 1, 3080, 'base', '아이씨뱅큐 (icbanq.com, P015646405)', '아이씨뱅큐', 'https://www.icbanq.com/P015646405',
                '22핀(Pi) → 15핀(화면) 디스플레이용(카메라용 SC1129와 섞지 않는다). 해외 재고 2주 이내, 기존 아이씨뱅큐 주문에 합침', None, 'v4touch')
_ws7c = [item('Waveshare 7-DSI-TOUCH-C 7인치 DSI 정전식 터치 1024×600 IPS', 1, 79900, 'base', 'G마켓 해외직구 (판매자 이룸종합상사4)', 'O:G마켓', 'https://item.gmarket.co.kr/Item?goodscode=4783965807',
              '10/1 사용자 선택(B1). 가로 1024×600, 5점 터치, 400 cd/m², 약 2.15 W(Pi GPIO 5 V). config.txt 한 줄(dtoverlay=vc4-kms-dsi-waveshare-panel-v2,7_0_inch_c), 밝기 sysfs 0~255. '
              '해외 구매대행: 중국 국경절 뒤 발송, 10/15~10/22 도착 추정. 개인통관고유부호 필요, 150달러 이하라 관부가세 없음. 쿠폰가 73,510원. 알리 공식 스토어 목록가 60,635원(미확인). 동봉: 22핀 200 mm 리본 2(책상 시험용), 2핀→2.54 3핀 전원선, 스탠드오프',
              bd.img_file('V-touch-ws7c', _IMG + '/touch2/img/dsi_ws_7-dsi-touch-c.jpg'), 'v4touch', spec='1024×600 가로, 166.10 × 101.00 × 8.0 mm, 뒷면 M2.5 구멍 154 × 88'),
         item('GUOCONN 0.5*22P*300*B FFC 22핀 0.5 mm 300 mm 반대면(B형) — 5개 묶음', 5, 391, 'base', '엘레파츠 (eleparts.co.kr, no=18622271)', _EL, 'https://www.eleparts.co.kr/goods/view?no=18622271',
              'Pi 5 CAM/DISP 1 ↔ 화면 22핀. 경로 약 271 mm(여유 29 mm). 해외재고, 평균 발송 10/21. 최소 주문 5개(나머지 예비)', None, 'v4touch'),
         item('GUOCONN 0.5*22P*300*A FFC 22핀 0.5 mm 300 mm 같은 면(A형) — 5개 묶음 (보험)', 5, 395, 'base', '엘레파츠 (eleparts.co.kr, no=18581287)', _EL, 'https://www.eleparts.co.kr/goods/view?no=18581287',
              '보험: 받침 안에서 45° 두 번 접혀 필요한 접점 면이 반대일 수 있다. 틀리면 재주문에 2주가 걸려 함께 산다. 빼면 1,975원 준다', None, 'v4touch')] + _jump() + [
         _m3x20(),
         item('스텐 유두 렌치볼트 M2.5 × 6 mm (굿나잇몰, 기존 볼트 주문에 옵션 추가)', 4, 100, 'base', '11번가 굿나잇몰', _gn, 'https://www.11st.co.kr/products/4236198413',
              '화면 뒷면 네 귀 M2.5 구멍(154 × 88)을 받침 뒤판에 고정. 동봉 스탠드오프 세트의 나사 수·길이가 공개되지 않아 산다. 받은 뒤 구멍 깊이를 재서 길이 확인(길면 화면 뒤를 누름). 값 추정', None, 'v4touch', ver=False)]
_td7 = [item('Raspberry Pi Touch Display 2 7인치 (SC1635)', 1, 95700, 'base', '엘레파츠 (eleparts.co.kr, no=16630499)', _EL, 'https://www.eleparts.co.kr/goods/view?no=16630499',
             '공식 제품, Pi 5 자동 인식. 세로 720×1280(앱이 회전). 약 2.5 W. 24시간 발송',
             bd.img_file('V-touch-td2-7', _IMG + '/touch/screens/img/rpi_td2_7.jpg'), 'v4touch', spec='720×1280(가로 회전), 정전식 5점, 189.3 × 120.2 × 14.9 mm'),
        _sc1132()] + _jump() + [_m3x20()]
_td5 = [item('Raspberry Pi Touch Display 2 5인치 (SC1975)', 1, 68200, 'base', '디바이스마트', 'O:디바이스마트', 'https://www.devicemart.co.kr/goods/view?no=15907263',
             '9/30 오후 값(밤에는 사이트 접속 안 됨). 화면 폭 110 mm라 2옥타브 흰 레인 6.9 mm. 66,000원 이상 무료배송',
             bd.img_file('V-touch-td2-5', _IMG + '/touch/screens/img/rpi_td2_5.jpg'), 'v4touch', ver=False, spec='720×1280, 143.4 × 91.5 mm'),
        _sc1132()] + _jump() + [_m3x20()]
_c1 = [item('7인치 1024×600 IPS 정전식 HDMI 터치 호환품 (쿠팡 8836448367, [01] IPS Touch LCD)', 1, 38310, 'base', '쿠팡 (판매자 제스117, 해외직구)', 'O:쿠팡', 'https://www.coupang.com/vp/products/8836448367?itemId=25750932443',
            'Waveshare 7inch HDMI LCD (C) 복제형. 10/20 도착 표시(해외), 상품평 0, 반품 왕복 32,200원. 밝기는 스위치로 켜고 끄기만. 불량이면 엘레파츠 (C) 정품 87,076원으로 바꿈(같은 받침)',
            bd.img_file('V-touch-c1', _IMG + '/touch2/img/hdmi_generic7c_coupang8836448367.jpg'), 'v4touch', spec='1024×600 가로, 164.9 × 124.3 mm(귀 포함)'),
       item('Wild Wire FFC HDMI 헤드 D-3 (micro HDMI, Pi 쪽) + A-1 (HDMI-A, 화면 쪽)', 2, 3300, 'base', '엘레파츠 (eleparts.co.kr, no=12558075)', _EL, 'https://www.eleparts.co.kr/goods/view?no=12558075', '옵션 D-3, A-1 각 1', None, 'v4touch'),
       item('Wild Wire FFC HDMI-50Cm', 1, 2145, 'base', '엘레파츠 (eleparts.co.kr, no=11845384)', _EL, 'https://www.eleparts.co.kr/goods/view?no=11845384', 'HDMI 경로 약 404 mm', None, 'v4touch'),
       item('Wild Wire FFC USB 헤드 USB A-1 (Pi 쪽) + Micro-1 (화면 쪽)', 2, 3300, 'base', '엘레파츠 (eleparts.co.kr, no=11833566)', _EL, 'https://www.eleparts.co.kr/goods/view?no=11833566', '옵션 USB A-1, Micro-1 각 1 (터치 + 전원)', None, 'v4touch'),
       item('Wild Wire FFC USB 리본 50 cm', 1, 2145, 'base', '엘레파츠 (eleparts.co.kr, no=11851039)', _EL, 'https://www.eleparts.co.kr/goods/view?no=11851039', 'USB 경로 약 472 mm', None, 'v4touch'),
       _m3x20()]
cards.append(dict(id='v4touch', cat='cpu', title='터치스크린 7인치 (R31)',
                  role='본체 터치스크린: 가운데 유닛 CU 뚜껑 위에 25° 기울여 세우고, 운반할 때 뒤로 접는다. 음색·볼륨·메트로놈·게임 메뉴와 리듬게임 기본 화면. 외부 TV(HDMI)는 선택 · 10/1 사용자 선택: Waveshare 7-DSI-TOUCH-C (비교 13조합: hardware/mechanical/touchscreen/compare/) · 필요량: 화면 1 + 22핀 리본 1(+보험 1) + 점퍼 4가닥 + M3×20 4 + M2.5×6 4',
                  options=[dict(id='cur', title='현재: Waveshare 7-DSI-TOUCH-C 7인치 가로 DSI (10/1 선택, B1)', items=_ws7c,
                                pros=['가로 1024×600이라 앱 회전 없음, 그릴 픽셀 33% 적어 60 fps 여유', '밝기 sysfs 조절(D14·D19 시험 가능), 약 2.15 W', '접은 받침 길이 106 mm라 L2 뚜껑에 유리', '공식 도면이 있어 받기 전에 받침을 그림'],
                                cons=['해외 구매대행, 10/15~10/22 도착 추정', 'config.txt 한 줄 필요', '받침을 새로 그림(L2 사양 뒤)'], note='', labor='', verified=True, fits=True, src='10/1 사용자 선택'),
                           dict(id='a1', title='공식 Touch Display 2 7인치 (9/30 rev 2 안, 국내 24시간)', items=_td7, pros=['설정 없음, 국내 재고', 'CAD v13(rev 2) 받침 그대로'],
                                cons=['세로 화면이라 앱이 매 프레임 회전', '접은 길이 125 mm라 L2에 경계', '비쌈'], note='', labor='', verified=True, fits=True, src='10/1 비교 A1'),
                           dict(id='a2', title='7인치 HDMI 호환품 (쿠팡 최저가, C1)', items=_c1, pros=['가장 쌈', '가로 화면, 드라이버 없음'],
                                cons=['10/20 도착(해외), 복제품·상품평 없음', '밝기 소프트웨어 조절 안 됨', '접은 길이 129 mm라 L2에 불리', '받침 새로'], note='', labor='', verified=True, fits=False, src='10/1 비교 C1'),
                           dict(id='a3', title='공식 Touch Display 2 5인치 (국내, A2)', items=_td5, pros=['국내 공식품, 설정 없음', '접은 길이 97 mm'],
                                cons=['화면이 작아 흰 레인 6.9 mm', '세로 화면', '받침 새로'], note='', labor='', verified=False, fits=False, src='10/1 비교 A2')],
                  unused='빼면 본체 화면 없이 외부 모니터·휴대폰(웹 UI)으로 조작한다. CU 뚜껑은 원래 모양(CAD L1)으로 출력한다.',
                  r4=False, r4note='', default='cur'))
byid['v4touch'] = cards[-1]

# ---------------------------------------------------------------- 10/1 L2 + 터치스크린 3판 (CAD_SPEC_rev3.md, cad/README.md '구매 목록에 없는 것')
# 리본 경로 271 → 256(모델 254) mm, 화면 뚜껑은 L2 레일 M3 열압입 인서트에 M3×10 4개(L34·L71), 굿나잇몰 옵션 값 10/1 확인.
_tc = byid['v4touch']
_tc['role'] = ('본체 터치스크린: 가운데 유닛 L2 화면 뚜껑(CU-SCREENLID, x501.5~720.5, 레일 인서트에 M3×10 4개) 위에 25° 기울여 세우고, '
               '운반할 때 뒤로 접는다(접은 윗면 z95.35). 음색·볼륨·메트로놈·게임 메뉴와 리듬게임 기본 화면. 외부 TV(HDMI)는 선택 · '
               '10/1 사용자 선택: Waveshare 7-DSI-TOUCH-C, 3판 CAD 반영(hardware/mechanical/touchscreen/rev3) · '
               '필요량: 화면 1 + 22핀 리본 1(+보험 1) + 점퍼 4가닥 + M3×20 4 + M2.5×6 4 (뚜껑 M3×10 4는 L34, 레일 인서트 4는 L71)')
_cur = _tc['options'][0]
_cur['pros'] = [p.replace('접은 받침 길이 106 mm라 L2 뚜껑에 유리', '접은 받침 y233.05~339.05라 L2 뚜껑 뒤 y342.5 안(여유 3.45)') for p in _cur['pros']]
_cur['cons'] = [c_.replace('받침을 새로 그림(L2 사양 뒤)', '받침 3판 CAD 완료(10/1) — 출력 전 종이띠로 리본 길 확인') for c_ in _cur['cons']]
_tc['unused'] = '빼면 본체 화면 없이 외부 모니터·휴대폰(웹 UI)으로 조작한다. 화면 뚜껑은 경첩·리본 구멍 없이 평판으로 출력한다(L2 자리만 잡은 판).'
for o in _tc['options']:
    for it in o['items']:
        if it['name'].startswith('GUOCONN 0.5*22P*300*B'):
            it['note'] = ('Pi 5 CAM/DISP 1 ↔ 화면 22핀. 10/1 3판·L2: 경로 약 256 mm(CAD 모델 254, 사양 256.32 → 여유 약 44~46). '
                          '해외재고, 평균 발송 10/21. 최소 주문 5개(나머지 예비)')
        if it['name'].startswith('스텐 유두 렌치볼트 M3 × 20'):
            it.update(unit=70, verified=True,
                      note=('경첩 축 2 + 받침다리 축 1 + 예비 1, PETG 구멍에 직접 탭(ISO 7380, 렌치 2 mm). '
                            '10/1 옵션 값 확인: 유두 M3 20mm 70원(이전 추정 100원)'))
        if it['name'].startswith('스텐 유두 렌치볼트 M2.5 × 6'):
            it.update(unit=200, verified=True,
                      note=('화면 뒷면 네 귀 M2.5 구멍(154 × 88)을 받침 뒤판에 고정(보스 Ø8, 물림 3). 받은 뒤 구멍 깊이를 재서 길이 확인(사양 G-2). '
                            '10/1 옵션 값 확인: 유두 M2.5 6mm 200원(이전 추정 100원) — Pi용 L47과 같은 옵션'))
    o['verified'] = all(i['verified'] for i in o['items'])

# ---- 10/1 L2 고침: 합판 가공 공구 (선택 공구, 기본 X — 가진 것 확인). 목록 공구는 Ø4.0 HSS(v4drill4)·쇠톱·줄뿐이었다.
cards.append(dict(
    id='v4wood', cat='tool', title='목공 드릴 비트 3~10 mm — L2 합판 구멍 (가진 것 확인)', r4=False, r4note='', default='none',
    role=('L2 판 가공(CAD README "합판 재단"): 뚜껑·뒤판·아랫판의 폭 4 mm 홈 38개(Ø4 구멍을 한 줄로 뚫어 잇고 줄로 다듬음), '
          '스피커 선 구멍 Ø6 ×2, 고무 슬리브 Ø8 ×4, 목재 인서트(L73) 막힌 구멍 ×4(약 Ø5.5~6 — L73 확인), XT30 선 구멍 Ø14 ×2(세트에 없음: Ø10으로 뚫고 줄로 넓힘), '
          '자석 자리 Ø8 × 3.2 12곳(README는 포스트너 비트 — 목공 비트도 가운데 뿔 자국만 남음). 사선 40°·통로 홈 27 × 22·뒤판 창은 쇠톱(v4cuttools)으로 자를 수 있으나 '
          '목공 톱·실톱이 있으면 그것이 빠르다. 가정: 전동 드릴은 가지고 있다 · 필요량: 세트 1 (가진 비트가 있으면 사지 않음)'),
    unused='기본은 사용 안함: 전동 드릴과 4·6·8 mm 목공(또는 철공) 비트를 가지고 있다고 본다. 없으면 이 세트를 고른다.',
    options=[
        dict(id='cur', title='나비엠알오 HARDEN 목공 드릴세트 8pcs (3·4·5·6·7·8·9·10 mm)', src='10/1 L2 고침', verified=True, fits=True,
             items=[item('[나비엠알오] 목공 드릴세트 8pcs (HARDEN 610287, 3·4·5·6·7·8·9·10 mm)', 1, 4389, 'tool', '나비엠알오 (navimro.com, g/1068385)',
                         'O:나비엠알오', 'https://www.navimro.com/g/1068385/',
                         '10/1 페이지: 3,990원(VAT 별도) → 4,389원, K44323944, 10/02 출하. 크기는 상세 사진의 케이스 표기(3~10)로 확인',
                         None, 'wood', fee=3300, spec='목공용 뿔 비트 8개 — Ø4 홈 줄 구멍·Ø6·Ø8·인서트 구멍; Ø14는 Ø10 + 줄')],
             pros=['나비엠알오 주문에 묶여 배송비가 더 들지 않는다(공급가 5만 원 넘음)', 'L2 구멍 크기 대부분(4·6·8)을 한 번에'],
             cons=['Ø14와 포스트너 Ø8은 없다(Ø14는 줄로 넓힘)'], note='', labor=''),
        dict(id='a1', title='가진 드릴 비트·톱 사용', src='10/1 L2 고침', verified=True, fits=True,
             items=[item('목공·철공 드릴 비트 4·6·8 mm + 톱 (보유품)', 1, 0, 'tool', '구매 없음', None, '', '구매 없음', None, 'wood')],
             pros=['돈이 들지 않는다'], cons=['Ø14·Ø8 × 3.2 자리는 가진 비트에 따라 줄로 다듬어야 할 수 있다'], note='', labor=''),
    ]))

REC = {c['id']: best(c) for c in cards if best(c)}
# 9/28: 스프링은 사용자가 미스미로 정했고(직접 감기는 추천하지 않음). 9/29: 블록 접착제는 강도 자료가 있는 슈퍼X 현재안을 둔다(더 싼 안은 에폭시뿐이고 설계와 맞지 않음).
REC.pop('v4tspring', None)
REC.pop('v4msbond', None)
TOOLS = {c['id']: 'none' for c in cards if all(i['b'] == 'tool' for i in c['options'][0]['items'])}
old = json.load(open(os.path.join(HERE, 'data_old.json')))
TOOLS.update({c['id']: 'none' for c in old['cards'] if c['cat'] == 'tool'})
presets = {
    'cur': dict(label='현재 목록 (4차 설계)', desc='지금 구매 목록 + v4 4차 설계 부품을 그대로 산다', sel={}),
    'rec': dict(label='v4 부품 추천 절감', desc='설계를 바꾸지 않는 확인된 더 싼 판매처·대체품으로(v4 부품만)', sel=REC),
    'tools': dict(label='공구는 가진 것', desc='공구 카드를 모두 사용 안함으로', sel=TOOLS),
}
REMOVED = [p for p in REMOVED if p['part_id'] != 'epoxy']  # r4.4에서 블록 접착제가 다시 들어옴(v4msbond 카드, 9/29 MS 폴리머)
removed = [dict(code='v4' + p['part_id'], name=p['name_ko'], reason='4차 단순화에서 빠짐', price=sum(i['qty'] * i['unit_krw'] for i in p['current']['items'])) for p in REMOVED]
json.dump(removed, open(os.path.join(HERE, 'removed_r4.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(dict(cards=cards, ship={}), open(os.path.join(HERE, 'data_v4.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(bd.IMGS, open(os.path.join(HERE, 'imgs_v4.json'), 'w'))
json.dump(presets, open(os.path.join(HERE, 'presets.json'), 'w'), ensure_ascii=False, indent=1)
tot = sum(i['qty'] * i['unit'] for c in cards if c['default'] == 'cur' for i in c['options'][0]['items'])
print('v4 cards', len(cards), 'imgs', len(bd.IMGS), 'current v4 total', tot, 'ship groups', ship)
