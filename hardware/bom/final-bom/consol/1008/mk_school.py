"""Build opt_school.py input from the live page data (data.json) + db state + Coupang/4-site candidates (10/8)."""
import json, os, sys
FB = "/Users/kwg/Desktop/mydrive/project/Toccata/hardware/bom/final-bom"
H = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.environ.get("DATA", FB + "/data.json"))); S = json.load(open(FB + "/state_main.json"))
SCHOOL = ("아이씨뱅큐", "엘레파츠", "디바이스마트", "쿠팡")   # any group whose name starts with one of the 4 school sites
def unit_at(i, q):
    u = i["unit"]
    for mq, up in (i.get("tiers") or []):
        if q >= mq: u = up
    return u
items, meta = {}, {}
for i in D["items"]:
    if not S["on"].get(i["id"], i["on"]): continue
    q = S["qty"].get(i["id"], i["qty"]); t = unit_at(i, q) * q
    if t == 0: continue
    g = i["sk"] or "_" + i["store"]
    items[i["id"]] = [{"group": g, "total": t, "school_ok": g.startswith(SCHOOL), "label": "지금: " + i["t"], "cur": True}]
    meta[i["id"]] = i["t"]
# lines bought as one pack / one order
def merge(a, b):
    if a in items and b in items:
        items[a][0]["total"] += items[b][0]["total"]; items[a][0]["label"] += " + " + b; del items[b]
merge("i066", "i067")
groups = {k: {"fee": v["fee"], "free_over": v["free_over"]} for k, v in D["ships"].items()}   # no aircon carry/shared here
groups.update({
    "쿠팡 로켓": {"fee": 0, "free_over": None},                  # 와우회원: 로켓·판매자로켓 무조건 무료배송 (10/8 상품 페이지)
    "쿠팡·삼미 CW-100B25": {"fee": 4000, "free_over": None},
    "쿠팡·파츠파츠": {"fee": 3000, "free_over": None},
    "쿠팡·CD74HC4067": {"fee": 3000, "free_over": None},
    "쿠팡·세메다인 흑색": {"fee": 3000, "free_over": None},
    "쿠팡·EVA": {"fee": 3000, "free_over": None},
    "쿠팡·onezaze": {"fee": 3500, "free_over": None},
    "쿠팡·흑연": {"fee": 3000, "free_over": None},
    "쿠팡·무료배송": {"fee": 0, "free_over": None},
    "굿나잇몰": {"fee": 3500, "free_over": None},
    "디바이스마트·입점 댐퍼": {"fee": 3500, "free_over": 350000},
    "쿠팡·화성고무": {"fee": 3000, "free_over": None},
    "쿠팡·스튜디오분트": {"fee": 3000, "free_over": None},
})
C = json.load(open(os.path.join(H, "cands.json")))
for c in C:
    if c["id"] not in items: continue
    items[c["id"]].append({k: c[k] for k in ("group", "total", "label") if k in c} | {"school_ok": c["group"].startswith(SCHOOL), "note": c.get("note", ""), "url": c.get("url", ""), "risk": c.get("risk", "")})
excl = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else set()
for iid in items:
    items[iid] = [o for o in items[iid] if o.get("cur") or o.get("risk", "") not in excl]
json.dump({"items": items, "groups": groups, "budget": 200000, "ship_paid_by_user": os.environ.get("SHIP_OWN") == "1", "school_ship_free": os.environ.get("SHIP_FREE") == "1", "meta": meta}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(len(items), "lines", sum(len(v) for v in items.values()), "options")
