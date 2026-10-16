"""Build optimizer input: current option per on-item + candidate options from agent JSONs.
usage: python3 mk_opts.py <scenario> > opts_<scenario>.json    scenario: alone | combined"""
import json, sys, os
FB = '/Users/kwg/Desktop/mydrive/project/Toccata/hardware/bom/final-bom'
SP = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(FB + '/data.json')); st = json.load(open(SP + '/state_v90.json'))
scen = sys.argv[1] if len(sys.argv) > 1 else 'alone'
OFF_EXTRA = set(json.load(open(SP + '/off_extra.json'))) if os.path.exists(SP + '/off_extra.json') else set()
def unit_at(i, q):
    u = i['unit']
    for mq, up in (i.get('tiers') or []):
        if q >= mq: u = up
    return u
items, meta = {}, {}
for i in D['items']:
    on = st['on'].get(i['id'], i['on'])
    if not on or i['id'] in OFF_EXTRA: continue
    q = st['qty'].get(i['id'], i['qty']); k = i['sk'] or '_' + i['store']
    if unit_at(i, q) * q == 0: continue
    items[i['id']] = [{'store': k, 'total': unit_at(i, q) * q, 'label': 'current: ' + i['t'], 'cur': True, 'qty': q}]
    meta[i['id']] = i['t']
# packs shared by two lines: optimise them as one line
for a, b in (('i050', 'i210'), ('i066', 'i067')):
    if a in items and b in items:
        items[a][0]['total'] += items[b][0]['total']; items[a][0]['label'] += ' + ' + b; del items[b]
ships = {k: {'fee': v['fee'], 'free_over': v['free_over']} for k, v in D['ships'].items()}
ships['미건케미칼'] = {'fee': 3000, 'free_over': None}
ships['엘레파츠']['free_over'] = 66000          # 공급가 6만 원 = VAT 포함 66,000 (sellers agent quote 10/7)
# candidate options from agents
CANON = {'디바이스마트': '디바이스마트', '엘레파츠': '엘레파츠', '아이씨뱅큐': '아이씨뱅큐', '나비엠알오': '나비엠알오', '한국미스미': '_한국미스미'}
for fn in ('extra_opts.json', 'devicemart_cur.json'):
    p = os.path.join(SP, fn)
    if not os.path.exists(p): continue
    for e in json.load(open(p)):
        if not isinstance(e, dict) or e.get('id', '').startswith('_') or e['id'] not in items: continue
        for c in e.get('candidates', []):
            if not c.get('total') or c.get('use') is False: continue
            if str(c.get('spec_match', '')).startswith('다름'): continue
            s = CANON.get(c['store'], c['store'])
            items[e['id']].append({'store': s, 'total': int(round(c['total'])), 'label': c.get('product', ''), 'url': c.get('url'), 'src': fn, 'verified': c.get('verified')})
    for e in json.load(open(p)):
        if isinstance(e, dict) and e.get('id') == '_ships':
            for s in e.get('ships', []):
                k = CANON.get(s['store'], s['store'])
                if k not in ships and s.get('fee') is not None:
                    ships[k] = {'fee': s['fee'], 'free_over': s.get('free_over_vat_incl')}
ships.setdefault('디바이스마트', {'fee': 2700, 'free_over': 66000})
ships.setdefault('쿠팡 로켓배송', {'fee': 3000, 'free_over': 19800})
if scen == 'combined':     # the user's aircon order in the same carts (aircon artifact 7CsQ8… 10/7)
    ships['디바이스마트'].update(carry=444191)
    ships['쿠팡 로켓배송'].update(carry=109670)
    ships['엘레파츠'].update(carry=7770, shared=True)
json.dump({'items': items, 'ships': ships, 'meta': meta}, sys.stdout, ensure_ascii=False, indent=1)
