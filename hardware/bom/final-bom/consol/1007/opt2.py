"""MILP: pick one option per item (or the fixed one), minimise item cost + shipping.
Shipping per store: fee unless (toccata subtotal + carry) >= free_over.  carry = what the user's other
project (aircon) already puts in the SAME cart.  shared=True: the other project already pays that store's
fee in its own list, so Toccata's marginal fee is 0 (but crossing free_over still saves `fee` overall ->
reported as 'other_saved').
Input JSON: {items:{id:[{store,total,label,...}]}, ships:{store:{fee,free_over,carry,shared}}}"""
import json, sys, numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
D = json.load(open(sys.argv[1])); items = D['items']; ships = D['ships']
stores = sorted({o['store'] for l in items.values() for o in l})
var = [('x', i, k) for i, l in items.items() for k in range(len(l))] + [v for s in stores for v in (('y', s), ('z', s))]
idx = {v: n for n, v in enumerate(var)}; N = len(var); c = np.zeros(N)
def sh(s): return ships.get(s, {'fee': 0, 'free_over': None})
for i, l in items.items():
    for k, o in enumerate(l): c[idx[('x', i, k)]] = o['total']
for s in stores:
    f = sh(s); fee = f['fee']
    if f.get('shared'):            # other project pays the fee anyway; we gain `fee` if the combined cart becomes free
        c[idx[('z', s)]] = -fee
    else:
        c[idx[('y', s)]] = fee; c[idx[('z', s)]] = -fee
A, lo, hi = [], [], []
def row(): return np.zeros(N)
for i, l in items.items():
    r = row()
    for k in range(len(l)): r[idx[('x', i, k)]] = 1
    A.append(r); lo.append(1); hi.append(1)
    for k, o in enumerate(l):
        r = row(); r[idx[('x', i, k)]] = 1; r[idx[('y', o['store'])]] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
for s in stores:
    f = sh(s); carry = f.get('carry', 0)
    if not f.get('shared'):
        r = row(); r[idx[('z', s)]] = 1; r[idx[('y', s)]] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
    r = row()
    if f.get('free_over') is None:
        r[idx[('z', s)]] = 1; A.append(r); lo.append(0); hi.append(0)
    else:   # sub + carry >= free_over * z   <=>   sub - free_over*z >= -carry
        for i, l in items.items():
            for k, o in enumerate(l):
                if o['store'] == s: r[idx[('x', i, k)]] = o['total']
        r[idx[('z', s)]] = -f['free_over']; A.append(r); lo.append(-carry); hi.append(np.inf)
res = milp(c, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.ones(N), bounds=Bounds(0, 1))
assert res.success, res.message
x = np.round(res.x).astype(int)
out = {'total': None, 'pick': {}, 'stores': {}}
for i, l in items.items():
    for k, o in enumerate(l):
        if x[idx[('x', i, k)]]: out['pick'][i] = dict(o, k=k)
tot_items = sum(o['total'] for o in out['pick'].values()); ship = 0; other_saved = 0
for s in stores:
    sub = sum(o['total'] for o in out['pick'].values() if o['store'] == s)
    used = any(o['store'] == s for o in out['pick'].values())
    if not used: continue
    f = sh(s); carry = f.get('carry', 0)
    free = f.get('free_over') is not None and sub + carry >= f['free_over']
    if f.get('shared'):
        fee = 0; other_saved += f['fee'] if free else 0
    else:
        fee = 0 if free else f['fee']
    ship += fee
    out['stores'][s] = {'sub': sub, 'ship': fee, 'carry': carry, 'free': free}
out['items_total'] = tot_items; out['ship'] = ship; out['total'] = tot_items + ship; out['other_saved'] = other_saved
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
print('items', tot_items, 'ship', ship, 'total', tot_items + ship, 'stores', len(out['stores']), 'other_saved', other_saved)
