"""Merge base.json (purchase list) + workflow results into data for the page, write site/index.html,
copy images and drawings into site/img and site/v.  Usage: python3 build.py [results.json]"""
import json, os, sys, shutil, re

F = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(F, "site")
B = json.load(open(os.path.join(F, "base.json")))
Z = json.load(open(os.path.join(F, "zones.json")))
RES = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
OVR = json.load(open(os.path.join(F, "overrides.json"))) if os.path.exists(os.path.join(F, "overrides.json")) else {}

GROUPS = ["제어·전원", "터치스크린", "센서·MCU·기판", "건반 액션", "오디오", "본체·결합", "3D 출력 재료", "소모품", "공구", "페달", "게임", "소프트웨어"]
BATCH_GROUP = {"power": "제어·전원", "sensor": "센서·MCU·기판", "audio": "오디오", "action1": "건반 액션", "action2": "건반 액션",
               "body": "본체·결합", "consum": "소모품", "tools": "공구"}
batches = json.load(open(os.path.join(F, "batches.json")))
batch_of = {it["id"]: b["name"] for b in batches for it in b["items"]}

enr = {it["id"]: it for it in RES.get("items", [])}
# critic fixes
crit = RES.get("critic") or {}
for zf in crit.get("zone_fixes", []):
    if zf["id"] in enr and zf.get("zones") is not None:
        enr[zf["id"]]["zones"] = zf["zones"]
for fx in crit.get("item_fixes", []):
    if fx["id"] not in enr or not fx.get("field") or "value" not in fx:
        continue
    e_, f_, v_ = enr[fx["id"]], fx["field"], fx["value"]
    m_ = re.match(r"^(\w+)\[(\d+)\]$", f_)
    if m_:
        arr = e_.setdefault(m_.group(1), [])
        i_ = int(m_.group(2))
        if i_ < len(arr): arr[i_] = v_
        else: arr.append(v_)
    elif f_.endswith("+"):
        e_.setdefault(f_[:-1], []).append(v_)
    else:
        e_[f_] = v_
# style normalisation (polite -> plain endings) done by a separate pass
if os.path.exists(os.path.join(F, "style_out.json")):
    for so in json.load(open(os.path.join(F, "style_out.json"))):
        if so["id"] in enr:
            for k in ("where", "buy_note", "identify", "owned_hint", "flags"):
                if k in so and so[k] not in (None, ""):
                    enr[so["id"]][k] = so[k]
imgs = {x["id"]: x["file"] for x in ((RES.get("images") or {}).get("images") or []) if x.get("file")}

items = []
for it in B["items"]:
    e = enr.get(it["id"], {})
    o = OVR.get(it["id"], {})
    d = dict(
        id=it["id"], no=it["no"], code=it["code"], n=it["name"], cat=it["cat"], unit=it["unit"] or 0, qty=it["qty"] or 0,
        url=it["url"], store=it["store"], seller=it["seller"], sk=it["ship_key"],
        img=imgs.get(it["id"]) or it["img"],
        on=True,
        t=e.get("title") or it["name"],
        g=e.get("group") or BATCH_GROUP.get(batch_of.get(it["id"]), "소모품"),
        where=e.get("where") or it["use"] or "",
        used=e.get("used_qty"), buy=e.get("buy_note") or "", pack=e.get("pack") or "",
        specs=[[s["k"], s["v"]] for s in e.get("specs", [])],
        ident=e.get("identify") or "", zones=[z for z in e.get("zones", []) if z in Z],
        refs=e.get("refs", []), ess=e.get("essential") or "필수", own=e.get("owned_hint") or "",
        flags=e.get("flags", []), qmin=e.get("qty_min"),
        src="extra" if it["no"] >= 200 else "list",
    )
    d.update(o)
    items.append(d)
for x in OVR.get("_extra", []):
    items.append(dict(x))

# views
views = {}
CROPS = json.load(open(os.path.join(F, "raster", "crops.json")))
RANK = {"d01_white_D_side.svg": 1, "d03_octave_plan.svg": 3, "d11_overall_layout.svg": 2, "BRD-01_control_board_placement.svg": 2,
        "BRD-02_sensor_board_placement.svg": 2, "d07_lever_carrier_steel.svg": 2, "d09_pad_bar_curtain_spring.svg": 2}
for v in RES.get("views", []):
    f = v["file"].split("/")[-1]
    zz = {}
    for zb in v.get("zones", []):
        if zb["zone"] not in Z:
            continue
        b = [round(float(x), 1) for x in zb["box"]]
        if b[2] <= 0 or b[3] <= 0:
            continue
        zz.setdefault(zb["zone"], {"l": zb.get("label") or Z[zb["zone"]], "b": []})["b"].append(b)
    if not zz:
        continue
    crop = CROPS.get(f)
    if not crop:
        continue
    views[f] = {"t": v.get("title") or f, "vb": crop[:4], "img": crop[6], "z": zz, "rank": RANK.get(f, 5)}

ships = {}
for s in B["ships"]:
    ships[s["key"]] = {"fee": s["fee"], "free_over": None, "basis": "구매 목록", "verified": False}
for s in ((RES.get("shipping") or {}).get("sellers") or []):
    k = s["key"]
    if k in ships or any(i["ship_key"] == k for i in B["items"]):
        ships[k] = {"fee": s["fee"], "free_over": s.get("free_over"), "basis": s.get("basis", ""), "verified": s.get("verified", False)}
ships.update(OVR.get("_ships", {}))

used_groups = [g for g in GROUPS if any(i["g"] == g for i in items)]
data = dict(items=items, views=views, zones=Z, ships=ships, groups=used_groups, prep=OVR.get("_prep", []), design=OVR.get("_design", []),
            foot=OVR.get("_foot", "처음 목록 = docs/report/toccata-purchase-list-v4.xlsx (2026-09-29) + 게임용 HDMI 케이블. 가격은 판매처 페이지 확인값(VAT 포함)이며 주문 전에 다시 확인하세요. 배송비는 판매처 안내 기준으로 계산합니다."))

os.makedirs(os.path.join(SITE, "img"), exist_ok=True)
os.makedirs(os.path.join(SITE, "v"), exist_ok=True)
for it in items:
    if it["img"]:
        src = os.path.join(F, "img", it["img"])
        if os.path.exists(src):
            shutil.copy(src, os.path.join(SITE, "img", it["img"]))
        else:
            print("missing image file", it["id"], it["img"])
            it["img"] = None
for f, v in views.items():
    shutil.copy(os.path.join(F, "raster", v["img"]), os.path.join(SITE, "v", v["img"]))
tpl = open(os.path.join(F, "template.html"), encoding="utf-8").read()
js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(tpl.replace("__DATA__", js))
open(os.path.join(SITE, "preview.html"), "w", encoding="utf-8").write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + tpl.replace("__DATA__", js) + "</body></html>")
json.dump(data, open(os.path.join(F, "data.json"), "w"), ensure_ascii=False, indent=1)

# totals check
def comp(on_fn, q_fn):
    per = {}
    tot = 0
    for i in items:
        if not on_fn(i):
            continue
        q = q_fn(i)
        u = i["unit"]
        for mq, up in (i.get("tiers") or []):
            if q >= mq: u = up
        a = u * q
        tot += a
        k = i["sk"] or "_" + i["store"]
        per[k] = per.get(k, 0) + a
    ship = 0
    for k, sub in per.items():
        s = ships.get(k)
        if s:
            ship += 0 if (s["free_over"] is not None and sub >= s["free_over"]) else s["fee"]
    return tot, ship
t, s = comp(lambda i: i["on"], lambda i: i["qty"])
print("items", len(items), "views", len(views), "images", sum(1 for i in items if i["img"]), "default total", t + s, "(items", t, "ship", s, ")")
print("site size", sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(SITE) for f in fs))
