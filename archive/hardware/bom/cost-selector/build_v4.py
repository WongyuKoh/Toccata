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

R = json.load(open(os.path.join(V4, 'costopt', 'result.json')))
CHECK = {}
for c in R['check']['results']:
    CHECK.setdefault(c['url'], []).append(c)

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


ORDER = ['weight', 'rail', 'keyrod', 'levershaft', 'capstan', 'pins', 'thumb', 'strip', 'disc', 'felt2', 'pu', 'cloth',
         'lead', 'magnet', 'brass', 'epoxy', 'graphite', 'spring', 'cuttools', 'reamer', 'tap']
R4_PARTS = {'thumb', 'strip', 'disc', 'lead', 'magnet', 'brass', 'spring', 'tap', 'levershaft', 'pins', 'rail', 'pu', 'felt2'}
parts = {p['part_id']: p for p in R['parts']}
ship_extra = {}


def conv_option(p, o, oid):
    items = []
    fits = o['fits_design']
    notes = []
    for i, it in enumerate(o['items']):
        nm = it['name']
        if p['part_id'] == 'capstan' and ('너트' in nm and 'XHHD' in nm):
            continue  # counted once in the L31 nut card
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

ship = {k: dict(fee=v, b='base', label=k[2:]) for k, v in ship_extra.items()}


# ---------------------------------------------------------------- presets
def pick(cid, title_sub):
    c = next(x for x in cards if x['id'] == cid)
    for o in c['options']:
        if title_sub in o['title']:
            return o['id']
    raise SystemExit(f'no option {cid} {title_sub}')


REC = {
    'v4levershaft': pick('v4levershaft', '에브로se'),
    'v4thumb': pick('v4thumb', '출력 널링 손잡이(B06 방식)'),
    'v4pins': pick('v4pins', '밸런스 핀만 구매'),
    'v4reamer': pick('v4reamer', '핸들 없이'),
    'v4tap': pick('v4tap', '스마토'),
    'v4lead': pick('v4lead', '오뚜기싱커'),
    'v4graphite': pick('v4graphite', '다이소'),
    'v4epoxy': pick('v4epoxy', 'C18'),
    'v4cuttools': pick('v4cuttools', '나비엠알오'),
}
R4 = dict(REC)
R4.update({'v4disc': 'none', 'v4strip': 'none', 'v4tap': 'none', 'v4lead': 'none', 'v4magnet': 'none', 'v4brass': 'none',
           'v4levershaft': pick('v4levershaft', '에이제트툴'), 'v4spring': 'none'})
TOOLS = {c['id']: 'none' for c in cards if all(i['b'] == 'tool' for i in c['options'][0]['items'])}
old = json.load(open(os.path.join(HERE, 'data_old.json')))
TOOLS.update({c['id']: 'none' for c in old['cards'] if c['cat'] == 'tool'})
presets = {
    'cur': dict(label='현재 목록', desc='지금 구매 목록 + v4 3차 설계 부품을 그대로 산다', sel={}),
    'rec': dict(label='v4 부품 추천 절감', desc='설계를 바꾸지 않고 확인된 더 싼 판매처·대체품으로 바꾼다(v4 부품만)', sel=REC),
    'r4': dict(label='4차 단순화 가정', desc='4차 설계 목표대로 빠질 부품을 뺀 가정치(확정 아님): 접시 스프링·탭 띠·납 추·커버 자석·황동 부싱·보조 스프링 없음, 레버 봉 SUS304', sel=R4),
    'tools': dict(label='공구는 가진 것', desc='공구 카드를 모두 사용 안함으로(인두·멀티미터·쇠톱·리머 등)', sel=TOOLS),
}
json.dump(dict(cards=cards, ship={}), open(os.path.join(HERE, 'data_v4.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(bd.IMGS, open(os.path.join(HERE, 'imgs_v4.json'), 'w'))
json.dump(presets, open(os.path.join(HERE, 'presets.json'), 'w'), ensure_ascii=False, indent=1)
tot = sum(i['qty'] * i['unit'] for c in cards if c['default'] == 'cur' for i in c['options'][0]['items'])
print('v4 cards', len(cards), 'imgs', len(bd.IMGS), 'current v4 total', tot, 'ship groups', ship)
