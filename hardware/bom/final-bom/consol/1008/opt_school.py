"""School-budget MILP (2026-10-08).
Every needed line picks one option.  An option at one of the 4 school-eligible sites (디바이스마트·엘레파츠·
아이씨뱅큐·쿠팡) can be paid by the school or by the user; the two are separate orders, so each has its own
shipping group ("<group>|학교" / "<group>|개인").  School orders (items + shipping) <= BUDGET.
Minimise what the user pays (personal items + personal shipping); tie-break: fill the school budget.
Input JSON: {items:{id:[{group,total,school_ok,label}]}, groups:{group:{fee,free_over}}, budget}
"""
import json, sys, numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
D = json.load(open(sys.argv[1])); B = D.get("budget", 200000); EPS = 1e-4
SHIP_OWN = D.get("ship_paid_by_user", False)   # 10/8 v19: 학교 한도 = 물건값만, 배송비는 모두 사비
SHIP_FREE = D.get("school_ship_free", False)   # 10/8 v21: 학교 한도 = 물건값만, 학교 주문 배송비는 학교가 (한도·사비 둘 다 아님)
items, G = D["items"], D["groups"]
opts = []                                   # (item, label, group key, total, pay)
for iid, lst in items.items():
    for o in lst:
        opts.append((iid, o, o["group"] + "|개인", o["total"], "개인"))
        if o.get("school_ok"):
            opts.append((iid, o, o["group"] + "|학교", o["total"], "학교"))
gkeys = sorted({k for *_, k, _, _ in [(a, b, c, d, e) for a, b, c, d, e in opts]})
nx, ng = len(opts), len(gkeys); gi = {g: n for n, g in enumerate(gkeys)}
# vars: x[opt], y[group used], z[group free]
N = nx + 2 * ng; Y = lambda g: nx + gi[g]; Z = lambda g: nx + ng + gi[g]
def rule(g): return G.get(g.split("|")[0], {"fee": 0, "free_over": None})
c = np.zeros(N)
for n, (iid, o, g, t, pay) in enumerate(opts):
    c[n] = t if pay == "개인" else -EPS * t
for g in gkeys:
    f = rule(g)["fee"]
    if g.endswith("|개인") or SHIP_OWN: c[Y(g)] += f; c[Z(g)] -= f
    elif SHIP_FREE: c[Y(g)] += EPS * f; c[Z(g)] -= EPS * f          # school pays; tiny penalty avoids needless extra orders
    else: c[Y(g)] -= EPS * f; c[Z(g)] += EPS * f
A, lo, hi = [], [], []
def row(): return np.zeros(N)
for iid in items:                                            # one option per line
    r = row()
    for n, (j, *_ ) in enumerate(opts):
        if j == iid: r[n] = 1
    A.append(r); lo.append(1); hi.append(1)
for n, (iid, o, g, t, pay) in enumerate(opts):               # option -> group used
    r = row(); r[n] = 1; r[Y(g)] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
for g in gkeys:
    fr = rule(g)
    r = row(); r[Z(g)] = 1; r[Y(g)] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
    r = row()
    if fr.get("free_over") is None:
        r[Z(g)] = 1; A.append(r); lo.append(0); hi.append(0 if fr["fee"] else 1)
    else:                                                    # free only if subtotal >= free_over
        for n, (iid, o, gg, t, pay) in enumerate(opts):
            if gg == g: r[n] = t
        r[Z(g)] = -fr["free_over"]; A.append(r); lo.append(0); hi.append(np.inf)
r = row()                                                    # school budget incl. shipping
for n, (iid, o, g, t, pay) in enumerate(opts):
    if pay == "학교": r[n] = t
if not SHIP_OWN and not SHIP_FREE:
    for g in gkeys:
        if g.endswith("|학교"): r[Y(g)] += rule(g)["fee"]; r[Z(g)] -= rule(g)["fee"]
A.append(r); lo.append(-np.inf); hi.append(B)
res = milp(c, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.ones(N), bounds=Bounds(0, 1))
assert res.success, res.message
x = np.round(res.x).astype(int)
pick = {}; grp = {}
for n, (iid, o, g, t, pay) in enumerate(opts):
    if x[n]:
        pick[iid] = dict(o, pay=pay, gkey=g)
        grp.setdefault(g, {"sub": 0, "items": []}); grp[g]["sub"] += t; grp[g]["items"].append(iid)
tot = {"학교": 0, "개인": 0}; ship_all = 0
for g, v in grp.items():
    fr = rule(g); free = fr.get("free_over") is not None and v["sub"] >= fr["free_over"]
    v["ship"] = 0 if (free or not fr["fee"]) else fr["fee"]; ship_all += v["ship"]
    if SHIP_OWN: tot[g.split("|")[1]] += v["sub"]; tot["개인"] += v["ship"]
    elif SHIP_FREE: tot[g.split("|")[1]] += v["sub"] + (v["ship"] if g.endswith("|개인") else 0)
    else: tot[g.split("|")[1]] += v["sub"] + v["ship"]
sch_ship = sum(v["ship"] for g, v in grp.items() if g.endswith("|학교"))
out = {"school": tot["학교"], "personal": tot["개인"], "total": tot["학교"] + tot["개인"] + (sch_ship if SHIP_FREE else 0), "ship": ship_all, "school_ship": sch_ship, "pick": pick, "groups": grp}
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print("school items" + ("" if (SHIP_OWN or SHIP_FREE) else "+ship"), tot["학교"], "| school shipping (paid by school)" if SHIP_FREE else "", sch_ship if SHIP_FREE else "", "| personal", tot["개인"], "| total", out["total"], "| ship", ship_all)
for g, v in sorted(grp.items(), key=lambda kv: (kv[0].split("|")[1], -kv[1]["sub"])):
    print(f"  {g:28s} {v['sub']:>8,} +{v['ship']:>5,}  {v['items']}")
