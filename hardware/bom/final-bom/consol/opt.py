"""MILP: pick one option per item, minimise item cost + shipping (fee unless store subtotal >= free_over).
Input: opts.json {items:{id:[{store,total,label}]}, ships:{store:{fee,free_over}}}"""
import json, sys, numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
D = json.load(open(sys.argv[1]))
items = D['items']; ships = D['ships']
stores = sorted({o['store'] for l in items.values() for o in l})
var = []  # (kind, key)
for iid, l in items.items():
    for k, o in enumerate(l): var.append(('x', iid, k))
for s in stores: var.append(('y', s)); var.append(('z', s))
idx = {v: n for n, v in enumerate(var)}
N = len(var); c = np.zeros(N)
for iid, l in items.items():
    for k, o in enumerate(l): c[idx[('x', iid, k)]] = o['total']
for s in stores:
    f = ships.get(s, {'fee': 0, 'free_over': None})
    c[idx[('y', s)]] = f['fee']; c[idx[('z', s)]] = -f['fee']
A = []; lo = []; hi = []
def row(): return np.zeros(N)
for iid, l in items.items():
    r = row()
    for k in range(len(l)): r[idx[('x', iid, k)]] = 1
    A.append(r); lo.append(1); hi.append(1)
    for k, o in enumerate(l):
        r = row(); r[idx[('x', iid, k)]] = 1; r[idx[('y', o['store'])]] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
BIG = 1e7
for s in stores:
    f = ships.get(s, {'fee': 0, 'free_over': None})
    r = row(); r[idx[('z', s)]] = 1; r[idx[('y', s)]] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
    r = row()
    if f.get('free_over') is None:
        r[idx[('z', s)]] = 1; A.append(r); lo.append(0); hi.append(0)
    else:  # subtotal >= free_over * z
        for iid, l in items.items():
            for k, o in enumerate(l):
                if o['store'] == s: r[idx[('x', iid, k)]] = o['total']
        r[idx[('z', s)]] = -f['free_over']; A.append(r); lo.append(0); hi.append(np.inf)
res = milp(c, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.ones(N), bounds=Bounds(0, 1))
x = np.round(res.x).astype(int)
out = {'total': round(res.fun), 'pick': {}, 'stores': {}}
for iid, l in items.items():
    for k, o in enumerate(l):
        if x[idx[('x', iid, k)]]: out['pick'][iid] = dict(o, k=k)
for s in stores:
    if x[idx[('y', s)]]:
        sub = sum(o['total'] for o in out['pick'].values() if o['store'] == s)
        f = ships.get(s, {'fee': 0}); out['stores'][s] = {'sub': sub, 'ship': 0 if x[idx[('z', s)]] else f['fee']}
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
print('total', out['total'], 'ship', sum(v['ship'] for v in out['stores'].values()), 'stores', len(out['stores']))
