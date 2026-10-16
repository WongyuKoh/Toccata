"""Purchase status of every circuit part, read from the FINAL purchase data (plan C, 2026-10-08).

Sources (read only):
  hardware/bom/final-bom/data.json         130 items i001..i225 (code, name, store key 'sk' with '(학교)' for school orders)
  hardware/bom/final-bom/state_main.json   the user's on/off + qty (identical to the live db)
  hardware/bom/final-bom/overrides.json    'own' notes (items the user already has)
  hardware/bom/final-bom/consol/1007/off_extra.json   items switched off because the smart-aircon order carries them
  docs/report/toccata-v4/data/final_items.json        canonical classification, if the items step has written it (optional)

status(key) -> dict(code, ids, state, text, store, url) for a parts.BOM key.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FB = os.path.join(ROOT, "hardware", "bom", "final-bom")
FINAL_ITEMS = os.path.join(ROOT, "docs", "report", "toccata-v4", "data", "final_items.json")

# parts.BOM key -> final-bom item ids (several ids = several purchase lines for one circuit part)
KEY_IDS = {
    "DRV5055": ["i004"], "C100n": ["i006"], "C10u": ["i007"], "C1u": ["i010"], "R1k": ["i029"], "R1k1206": ["i008"],
    "R100k": ["i031"], "R100": ["i032"], "ZERO": ["i084"], "MUX": ["i085"], "HDR": ["i005"], "HDRZ": ["i005"],
    "PERF": ["u06"], "PERF1218": ["i081"], "RIBBON": ["i023"], "RIBBONW": ["i024"], "JSTXH": ["i101"], "PJ313": ["i033"],
    "TRS3M": ["i013"], "TRS15": ["i038"], "PEDAL": ["i109"], "MAG5": ["i098"], "XT60M": ["i224"], "XT60M_SPK": ["i224"],
    "XT60F_SPK": ["i225"], "XT60F_BENCH": ["i225"], "FUSEH": ["u04"], "FUSE": ["u05"], "SW": ["u03"], "BUCK": ["i003"], "BATT": ["u01"],
    "C24": ["i021"], "PI5": ["i001"], "HUB": ["i093"], "USBAC": ["i022"], "DONGLE": ["i111"], "GENDER": ["i034"],
    "AMP": ["i009"], "SPK": ["i051"], "SPKW": ["i037"], "C25": ["i222"], "DISP7C": ["i202"], "JMPFF": ["i205", "i206"],
    "JMPMM": ["i207", "i208"], "FFC22B": ["i203"], "FFC22A": ["i204"], "SHRINK": ["i025"], "KAPTON": ["i026"],
}
# keys with no purchase line of their own (other end of a cable, part of a module, the battery bought separately)
NO_LINE = {
    "XT60F": "BT601 팩 리드에 달려 옴 (따로 사지 않음)",
    "PADS6": "패드만 (부품 없음)", "PADS": "패드만 (부품 없음)", "JP": "납땜 브리지 (부품 없음)", "TP": "구멍 패드 (부품 없음)",
    "JMPFF2": "W606 다른 끝 (같은 점퍼)", "JMPMM2": "W607 다른 끝 (같은 점퍼)", "DPWR": "A605 화면에 동봉된 전원선",
    "DPWR2": "W608 다른 끝 (동봉선)", "PLUG": "케이블 끝 플러그 (선과 함께)", "HUBDC": "허브에 딸린 5 V 어댑터 선의 플러그 쪽",
}

_cache = {}


def _load():
    if _cache:
        return _cache
    d = json.load(open(os.path.join(FB, "data.json"), encoding="utf-8"))
    st = json.load(open(os.path.join(FB, "state_main.json"), encoding="utf-8"))
    ov = json.load(open(os.path.join(FB, "overrides.json"), encoding="utf-8"))
    try:
        air = set(json.load(open(os.path.join(FB, "consol", "1007", "off_extra.json"), encoding="utf-8")))
    except Exception:
        air = set()
    items = {}
    for it in d["items"]:
        i = it["id"]
        on = st.get("on", {}).get(i, it.get("on", False))
        qty = st.get("qty", {}).get(i, it.get("qty"))
        items[i] = dict(id=i, code=it.get("code", ""), name=it.get("n", ""), sk=it.get("sk") or it.get("store") or "",
                        store=it.get("store", ""), url=it.get("url", ""), unit=it.get("unit"), qty=qty, on=bool(on),
                        own=(ov.get(i) or {}).get("own", ""), air=i in air, used=it.get("used"))
    final = {}
    if os.path.exists(FINAL_ITEMS):
        try:
            fi = json.load(open(FINAL_ITEMS, encoding="utf-8"))
            rows = fi.get("items", fi) if isinstance(fi, dict) else fi
            if isinstance(rows, dict):
                rows = [dict(v, id=k) if isinstance(v, dict) else {"id": k, "status": v} for k, v in rows.items()]
            for r in rows or []:
                if isinstance(r, dict) and r.get("id"):
                    final[r["id"]] = r
        except Exception:
            final = {}
    _cache.update(items=items, final=final)
    return _cache


def _final_text(r):
    for k in ("status_ko", "class_ko", "status", "class", "kind", "source", "state"):
        v = r.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


SRC_KO = {"school": "학교 지원 구매", "personal": "사비 구매", "owned": "가진 것",
          "tool": "가진 공구", "gap": "아직 준비처 없음"}


def item_status(i):
    c = _load()
    f = c["final"].get(i)
    if f and f.get("source"):                       # canonical classification (docs/report/toccata-v4/data/final_items.json)
        src = f["source"]
        od = f.get("ordered") or {}
        txt = f.get("source_ko") or SRC_KO.get(src, src)
        if src in ("school", "personal") and od.get("store"):
            txt += " · " + od["store"]
        return dict(state=src, text=txt, store=od.get("store", ""), url=od.get("url", ""), code=f.get("code") or "",
                    name=f.get("name", ""), qty=f.get("qty_need"))
    it = c["items"].get(i)
    if not it:
        return dict(state="?", text="최종 목록에 없음")
    ft = _final_text(f) if f else ""
    if it["on"]:
        school = "(학교)" in it["sk"]
        st = "school" if school else "personal"
        txt = ("학교 구매" if school else "사비 구매") + " · " + it["store"]
    elif it["air"] or it["own"] or (ft and ("보유" in ft or "own" in ft.lower())):
        st, txt = "owned", "사용자 보유"
    else:
        st, txt = "off", "이번 주문 밖 (보유·공용)"
    if ft and ft not in txt:
        txt = txt + " (" + ft + ")"
    return dict(state=st, text=txt, store=it["store"], url=it["url"], code=it["code"], name=it["name"], qty=it["qty"])


def status(key):
    """purchase line(s) for a parts.BOM key."""
    if key in NO_LINE:
        return dict(code="", ids=[], state="none", text=NO_LINE[key], store="", url="")
    ids = KEY_IDS.get(key)
    if not ids:
        return dict(code="", ids=[], state="?", text="", store="", url="")
    sts = [item_status(i) for i in ids]
    states = {s["state"] for s in sts}
    text = sts[0]["text"] if len(states) == 1 else " / ".join(s["text"] for s in sts)
    return dict(code=sts[0].get("code", ""), ids=ids, state=sts[0]["state"], text=text, store=sts[0].get("store", ""),
                url=sts[0].get("url", ""), name=sts[0].get("name", ""), qty=sts[0].get("qty"))


def final_items_present():
    return bool(_load()["final"])


if __name__ == "__main__":
    for k in sorted(KEY_IDS):
        s = status(k)
        print(k, s["ids"], s["state"], s["text"])
    print("final_items.json:", final_items_present())
