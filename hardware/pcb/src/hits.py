"""Click data for the drawings on the '01 회로도' tab: what each wire, pad, pin or part on a sheet is, which product it is and
what it connects to.

usage: called by page.py after model3d.build() (the part texts come from model3d.INFO = bom.csv + cables.csv)
  in : netlist/sheethits.json  (build.py: geometry in sheet mm, nets from the connectivity check / BRD-08 routes)
  out: docs/report/toccata-v4/fin/circuit/sheethits.json  {code: {items: [...], nets: {...}}}
       item = {k: 'w' wire | 'p' pad or pin | 'r' part box, g: geometry, t: title, d: [lines], n: net or absent}
       net  = {t: title, d: [lines], c: colour}
The page script (page.py JS, 'sheet hits') picks the nearest item to a click and shows t / d plus the net block.
"""
import csv
import json
import os
import re

import boards3 as B3
import parts as P

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(HERE, "..", "netlist")


def _csv(name):
    with open(os.path.join(NETLIST, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------- MB (SCH-03 / BRD-08) names and meanings
ZERO = dict(P.RP2040_ZERO)
MUXN = dict(P.MUX_CH + P.MUX_CTRL)
J302_ROLE = {1: "GND", 2: "EXT1", 3: "EXT2", 4: "EXT3", 5: "EXT4", 6: "3V3"}
STRAND = P.BOM["RIBBONW"]


def zero_name(n):
    nm = ZERO.get(int(n), "?")
    return nm + (" (ADC0)" if nm == "GP26" else "")


def mb_pin_name(ref, num, net=None):
    """short name of one MB pad: 'GP26 (ADC0)', 'SIG', '13번 (앞줄)' ..."""
    n = int(num) if str(num).isdigit() else num
    if ref == "A301":
        return zero_name(n)
    if ref == "A302":
        return MUXN.get(n, str(n))
    if ref == "J301":
        return "%d번 (%s)" % (n, "앞줄" if n % 2 else "뒷줄")
    if ref == "J302":
        return "%d번 %s" % (n, J302_ROLE.get(n, ""))
    if ref.startswith("R30"):
        return "%s번 다리" % num
    if ref.startswith("JP"):
        return "%s번 (%s 쪽)" % (num, "GND" if net == "GND" else "신호")
    if ref.startswith("TP"):
        return "테스트 점 (%s)" % (net or "")
    return ""


TP_USE = {"+3V3": "3.3 V 전원 — TP301과 TP302(GND) 사이가 3.3 V면 정상입니다.", "GND": "접지 — 전압을 잴 때 검은 탐침을 대는 기준점입니다.",
          "MUX_SIG": "먹스가 고른 센서의 출력 전압 — 건반을 누르면 값이 변합니다."}


def tp_lines(net):
    """what a test point is (a bare hole pad, no part) and what is measured there."""
    return ["테스트 점: 부품 없이 납만 올린 구멍 패드 한 칸입니다. 멀티미터 탐침을 대고 전압을 재는 자리입니다.",
            "재는 것: " + TP_USE.get(net, "넷 %s" % net)]


def mb_end(tok, net=None):
    """wire end 'A301.7' -> 'A301 RP2040-Zero GP26 (ADC0)'."""
    ref, num = tok.split(".")
    what = {"A301": "RP2040-Zero", "A302": "4067 먹스 모듈", "J301": "리본 구멍", "J302": "EXT 패드", "C301": "콘덴서"}.get(ref)
    if ref.startswith("R30"):
        what = "100 kΩ 풀다운"
    elif ref.startswith("JP"):
        what = "ID·PED 점퍼"
    elif ref.startswith("TP"):
        return "%s 테스트 점" % ref
    return "%s %s %s" % (ref, what or "", mb_pin_name(ref, num, net))


def mb_net_text():
    """net -> (title, lines) for the control board nets."""
    mux = {r["먹스 채널"]: r for r in _csv("mux_map.csv")}
    sens = {r["넷"]: r for r in _csv("sb_sensors.csv")}
    ribbon = {}
    for r in _csv("netlist.csv"):
        if r.get("도면") == "SCH-03" and r.get("부품") in ("J301", "A302"):
            ribbon.setdefault(r["넷"], {})[r["부품"]] = r["핀"]
    out = {
        "+3V3": ("+3V3 · 3.3 V 전원", ["RP2040-Zero의 3V3 핀(USB 5 V → 내장 레귤레이터)에서 나와 먹스 VCC, 리본 1·16번(센서 기판 SB의 센서 12개),",
                                     "J302 6번(끝 부속 EL·ER), TP301로 갑니다. 측정: TP301–TP302 = 3.3 V."]),
        "GND": ("GND · 접지", ["제로 GND, 먹스 GND와 EN(EN을 GND에 묶어 먹스를 항상 켬), 리본 2·15번, J302 1번, 풀다운 R301~R304, 점퍼 GND 쪽, TP302."]),
        "MUX_SIG": ("MUX_SIG · 먹스 공통 출력", ["먹스가 고른 채널의 센서 전압 → 제로 GP26 (ADC0, 12비트). TP303에서 전압을 잴 수 있습니다."]),
        "PED_SEL": ("PED_SEL · 페달 보드 표시", ["제로 GP14 ↔ JP304. 닫으면(GND) 페달 보드 PB로 동작합니다. MB 7장은 모두 열림 — TP302에서 온 GND 선은 JP304 한쪽 패드까지만 옵니다."]),
    }
    for k in range(4):
        out["MUX_S%d" % k] = ("MUX_S%d · 먹스 채널 선택 %d번 비트" % (k, k),
                              ["제로 GP%d → 먹스 S%d. 펌웨어가 S0~S3으로 채널 0~15를 차례로 고릅니다." % (2 + k, k)])
    for k in range(3):
        out["ID%d" % k] = ("ID%d · 보드 번호 %d번 비트" % (k, k),
                           ["제로 GP%d ↔ JP30%d. 펌웨어가 풀업을 켜 두고, 점퍼를 닫으면(GND) 이 비트 = 1. O1~O7 조합은 ID 점퍼 표." % (6 + k, k + 1)])
    for net, sides in ribbon.items():
        if not net.startswith("HALL_"):
            continue
        ch = MUXN.get(int(sides.get("A302", 0)), "?")
        s = sens.get(net, {})
        keys = mux.get(ch, {})
        notes = " · ".join(keys.get("O%d" % o, "") for o in range(1, 8) if keys.get("O%d" % o, "—") != "—")
        out[net] = ("%s · %s 건반 센서 출력" % (net, s.get("건반", "?")),
                    ["센서 기판 SB의 %s(%s 건반) OUT → 리본 %s번 심 → J301 %s번 → 먹스 %s." % (s.get("센서", "?"), s.get("건반", "?"), s.get("리본 심", "?"),
                                                                                  sides.get("J301", "?"), ch),
                     "옥타브별 건반 (MIDI 번호): " + notes])
    for k in range(1, 5):
        ch = "C%d" % (11 + k)
        keys = mux.get(ch, {})
        use = " · ".join("O%d %s" % (o, keys.get("O%d" % o)) for o in range(1, 8) if keys.get("O%d" % o, "—") != "—") or "지금 쓰는 보드 없음 (△34)"
        out["EXT%d" % k] = ("EXT%d · 끝 부속 센서 입력 %d" % (k, k),
                            ["J302 %d번 패드(끝 부속 선) → 먹스 %s. R30%d 100 kΩ이 GND로 당겨 선이 없으면 0 V(펌웨어가 '없음'으로 봄)." % (k + 1, ch, k),
                             "쓰는 곳: " + use])
    return out


# ---------------------------------------------------------------------- part cards (2026-11-23)
# User 2026-11-23: 'C301같은 부품을 클릭하면 이게 뭔지 이미지랑 저항 수치 등 세부 정보를 옆에 띄워' and, for the jumpers,
# '클릭하면 연결해라, 연결하지 마라 확실하게 작성해줘'.  A card per BOM ref: value, product photo (the purchase list photo the
# page already ships, img/bom/<id>.jpg), specs and how to tell it apart (data/final_items.json), plus for the parts that differ
# between boards (ID jumpers, EXT pull-downs, the EXT lead) an explicit 'act': which boards connect / fit it and which do not.
PAGE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "docs", "report", "toccata-v4"))
MB_ALL = ["O%d" % n for n in range(1, 8)]
REF_RX = re.compile(r"\b([A-Z]{1,3}\d{3}(?:-[A-Z]+)?)\b")


def jp_closed(n):
    """board number 1..7 -> bridged ID jumpers (bit k of the number = JP30(k+1)); = boards4.jp_closed / export.id_rows()"""
    return {"JP30%d" % (k + 1) for k in range(3) if (n >> k) & 1}


def part_act(ref):
    """{'yes', 'no', 'how_yes', 'how_no', 'on', 'all', 'why'} for a part that some boards carry and others not, else None"""
    J = dict(yes="연결하세요", no="연결하지 마세요", how_yes="아랫면에서 두 구멍을 납 한 방울로 이어 붙입니다 (납땜 브리지). 부품은 없습니다.",
             how_no="두 구멍을 비워 둡니다. 납이 번져 서로 붙지 않았는지 확인합니다.")
    R = dict(yes="다세요", no="달지 마세요 (자리 비움)", how_yes="100 kΩ(갈·검·노·금)을 윗면에 눕혀 꽂고 아랫면에서 납땜, 다리 끝은 1 mm 이하로 자릅니다.",
             how_no="두 구멍을 비워 둡니다. 다른 기판과 같은 판을 써도 이 자리는 그대로 둡니다.")
    m = re.fullmatch(r"JP30([1-3])", ref)
    if m:
        k = int(m.group(1)) - 1
        on = ["O%d" % n for n in range(1, 8) if ref in jp_closed(n)]
        return dict(J, on=on, all=MB_ALL, why="모듈 번호를 정하는 ID 점퍼(GP%d, 비트 %d)입니다. 이은 기판에서 이 비트가 1이 되고, JP301·JP302·JP303 조합이 O1~O7 "
                    "번호 = USB 이름 'Toccata O…'가 됩니다. 잘못 이으면 두 모듈이 같은 번호가 되어 음이 겹칩니다." % (6 + k, k))
    if ref == "JP304":
        return dict(J, on=[], all=MB_ALL, why="GP14 페달 보드 표시입니다. MB 7장은 모두 비워 둡니다 — 이으면 그 기판이 페달 보드로 동작합니다.")
    if ref == "JP504":
        return dict(J, on=["PB"], all=["PB"], why="페달 보드 PB의 GP14 표시입니다. 이어야 펌웨어가 페달 보드(CC64)로 동작합니다.")
    fit = {"R301": ["O1", "O7"], "R302": ["O1"], "R303": ["O1"], "R304": []}
    if ref in fit:
        n = int(ref[1:]) - 300
        why = ("EXT%d 풀다운입니다. 끝 부속 선이 빠졌을 때 입력을 0 V로 당겨 유령 음을 막습니다. EXT%d를 쓰는 기판에만 답니다." % (n, n)
               if fit[ref] else "EXT4 자리입니다. EXT4를 쓰는 부품이 없어 어느 기판에도 달지 않습니다.")
        return dict(R, on=fit[ref], all=MB_ALL, why=why)
    if ref == "J302":
        return dict(yes="EXT 선을 다세요", no="EXT 선을 달지 마세요", how_yes="O1: 1·2·3·4·6번 패드에 W403 5가닥, O7: 1·2·6번 패드에 W413 3가닥을 윗면에서 납땜합니다.",
                    how_no="EXT 선이 없습니다. 1번 구멍만 GND 선의 이음 자리로 납땜합니다.", on=["O1", "O7"], all=MB_ALL,
                    why="끝 부속(왼쪽 EL: A0·A#0·B0, 오른쪽 ER: C8) 센서 선이 들어오는 자리입니다. 양 끝 모듈만 씁니다.")
    return None


def part_cards():
    """ref -> card {t, v, desc, img, cap, spec, ident, act} from bom.csv + data/final_items.json"""
    rows = _csv("bom.csv")
    try:
        with open(os.path.join(PAGE, "data", "final_items.json"), encoding="utf-8") as f:
            fi = json.load(f)
        items = fi if isinstance(fi, list) else fi.get("items", [])
    except OSError:
        items = []
    by_ref, by_code, ncode = {}, {}, {}
    for it in items:
        by_code.setdefault(it.get("code"), it)
        ncode[it.get("code")] = ncode.get(it.get("code"), 0) + 1
        for sr in it.get("sch_refs") or []:
            for rf in REF_RX.findall(sr):
                by_ref.setdefault(rf, it)
    # a ref the purchase list does not name (e.g. R304, fitted nowhere): the item of another ref with the same part description
    by_desc = {}
    for r in rows:
        it = by_ref.get(r["부품"]) or by_ref.get(r["부품"].split("-")[0])
        if it:
            by_desc.setdefault(r["부품 설명"], it)
    cards = {}
    for r in rows:
        ref = r["부품"]
        if ref in cards:
            continue
        code = r["구매 목록 코드"]
        it = (by_ref.get(ref) or by_ref.get(ref.split("-")[0]) or by_desc.get(r["부품 설명"])
              or (by_code.get(code) if code and ncode.get(code) == 1 else None))
        img = None
        if it and it.get("img") and os.path.exists(os.path.join(PAGE, it["img"])):
            img = it["img"]
        same = bool(it) and ref not in by_ref and ref.split("-")[0] not in by_ref and by_desc.get(r["부품 설명"]) is not it
        desc = r["부품 설명"]
        if desc.startswith("SolderJumper"):
            desc = "납땜 브리지 자리 — 이웃한 두 구멍을 납으로 잇거나 비워 두는 곳 (KiCad %s)" % desc
        c = dict(t="%s · %s" % (ref, r["값"]) if r["값"] else ref, v=r["값"], desc=desc,
                 board="%s · %s장 × %s = %s개" % (r["보드"], r["보드 수"], r["보드당"], r["전체 수량"]))
        if r["실장 조건"]:
            c["fit"] = r["실장 조건"]
        if it:
            c.update(item=it["id"], cap=it.get("name") or it.get("full_name"), spec=it.get("specs") or [], ident=it.get("ident") or "")
            if same:
                c["same"] = "사진은 구매 목록 %s(%s)의 같은 종류 부품입니다. 값은 위 '값'을 따릅니다." % (it["id"], it.get("name"))
        elif "브리지" in (r["구매 상태 (최종 목록)"] or "") or r["KiCad 심볼"].startswith("Jumper:"):
            c["spec"] = [["종류", "납땜 브리지 — 산 부품 없음"], ["모양", "만능기판의 이웃한 두 구멍 (2.54 mm)"]]
        if img:
            c["img"] = img
        a = part_act(ref)
        if a:
            c["act"] = a
        cards[ref] = c
    return cards


def card_ref(key, cards):
    """'A301.7' / 'r:A301' / 'C301' -> the card ref, else None"""
    if not key:
        return None
    k = key.split(":", 1)[-1].split(".")[0]
    return k if k in cards else (k.split("-")[0] if k.split("-")[0] in cards else None)


# ---------------------------------------------------------------------- generic
def part_lines(info, ref, extra=()):
    """title + lines of a part (model3d.INFO), without the KiCad / sheet lines (the popup is about the part and its links)."""
    I = info.get(ref) or info.get(ref.split("-")[0])
    if not I:
        return ref, list(extra)
    d = []
    for x in I["d"]:
        if x.startswith(("KiCad:", "도면 ")):
            continue
        x = re.sub(r"^구매:\s+·\s*", "구매: ", x)
        x = re.sub(r"\(이름 없음 N\d+\)", "NC", x) if ref.startswith(("A301", "A501")) else x
        d.append(x)
    return I["t"].rstrip(" ·"), d + list(extra)


def net_block(net, known, pins=None):
    col = B3.ncol(net) if net else "#555"
    if net and net in known:
        t, d = known[net]
    elif not net or net.startswith("~"):
        t, d = "이름 없는 넷 (두 부품 사이 짧은 연결)", []
    else:
        t, d = "넷 " + net, []
    d = list(d)
    if pins:
        d.append("이 도면에서 이어진 핀: " + ", ".join(pins))
    return dict(t=t, d=d, c=col)


def sch_items(code, h, info, known):
    """schematic: one wire item per net (all its segments), one item per pin, one box per part."""
    items, nets = [], {}
    pins_by = {}
    for ref, num, name, x, y, n in h["pins"]:
        pins_by.setdefault(n, []).append("%s.%s%s" % (ref, num, (" " + name) if name and name not in ("~", "") else ""))
    segs = {}
    for x1, y1, x2, y2, n in h["segs"]:
        segs.setdefault(n, []).append([[x1, y1], [x2, y2]])
    for n, pl in segs.items():
        nets[n] = net_block(n, known, pins_by.get(n))
        items.append(dict(k="w", g=pl, n=n, t="회로도 선 · " + ("이름 없는 넷" if n.startswith("~") else n),
                          d=["회로도의 선은 같은 넷(전기적으로 한 덩어리)을 뜻합니다. 실제 선·가닥과 길이는 기판·배선 도면(BRD)에 있습니다."]))
    for ref, num, name, x, y, n in h["pins"]:
        if n not in nets:
            nets[n] = net_block(n, known, pins_by.get(n))
        pt, pd = part_lines(info, ref)
        solo = len(pins_by.get(n, [])) <= 1 and (n or "").startswith("~")
        items.append(dict(k="p", g=[x, y], r=0.8, n=None if solo else n, ref=ref,
                          t="%s.%s%s" % (ref, num, (" · " + name) if name else ""),
                          d=[pt] + pd[:1] + (["연결 없음 (NC)"] if solo else [])))
    for ref, x0, y0, x1, y1 in h["parts"]:
        t, d = part_lines(info, ref)
        items.append(dict(k="r", g=[x0, y0, x1, y1], t=t, d=d, ref=ref))
    return items, nets


def board_items(code, b, info, known, keyed=False):
    """BRD-08 and BRD-09~15: numbered strands, pads and part boxes. Optional per-sheet texts (boards4.py, what differs on one board
    kind): wnote {wire no: lines}, padnote {'ref.num': lines}, pnote {ref: lines}, extra [ready-made items].
    keyed=True keeps '_k' on every item ('w:12', 'p:A301.7', 'r:A301') - model3d.py uses the same texts for the 3D model."""
    items, nets = [], {}
    wnote, padnote, pnote = b.get("wnote", {}), b.get("padnote", {}), b.get("pnote", {})
    by_end = {}
    for w in b["wires"]:
        for e in (w["a"], w["b"]):
            by_end.setdefault(e, []).append(w["no"])
    by_ref = {}
    for w in b["wires"]:
        for e in (w["a"], w["b"]):
            by_ref.setdefault(e.split(".")[0], {}).setdefault(w["net"], set()).add(w["no"])
    pins_by = {}
    for ref, num, net, x, y, sol in b["pads"]:
        if sol and net != "NC" and "%s.%s" % (ref, num) not in pins_by.setdefault(net, []):     # BRD-09~15 list every pad twice (two views)
            pins_by[net].append("%s.%s" % (ref, num))
    hidden = b.get("wires_hidden")                  # a top view: the underside wires are on another sheet, only their numbers are used
    for w in b["wires"]:
        n = w["net"]
        if n not in nets:
            nets[n] = net_block(n, known, pins_by.get(n))
            same = sorted(x["no"] for x in b["wires"] if x["net"] == n)
            nets[n]["d"].append("이 넷의 선 번호: " + ", ".join(map(str, same)) + (" (%s 아랫면 배선)" % hidden if hidden else " (그림에서 연하게 함께 표시)"))
        if hidden:
            continue
        items.append(dict(k="w", g=[w["pts"]], n=n, _k="w:%d" % w["no"], t="선 %d · %s" % (w["no"], n), d=wnote.get(str(w["no"]), []) + [
            "시작: " + mb_end(w["a"], n),
            "끝: " + mb_end(w["b"], n),
            "길이 %.1f mm · 꺾임 %d번 (꺾인 점 좌표 = wiring_MB.csv %d번 줄)" % (w["len"], w["bends"], w["no"]),
            "선: EUNSUNG 2651-16P 16심 리본에서 가른 1가닥 (구매 %s · %s, 1 m 더 사서 가름)" % (STRAND[0], STRAND[2]),
            "28 AWG, 바깥 지름 약 0.9. 기판 밑 2.0 공간이라 두 가닥이 겹쳐도 1.8.",
        ]))
    for ref, num, net, x, y, sol in b["pads"]:
        nm = mb_pin_name(ref, num, net)
        pt, pd = part_lines(info, ref)
        pn = padnote.get("%s.%s" % (ref, num), [])
        if not sol:
            d = [pt] + (pn or ["빈 구멍 — 헤더가 없는 아래 줄(GP9~GP13)이라 납땜하지 않습니다." if ref == "A301" else "빈 구멍 — 납땜하지 않습니다."])
            items.append(dict(k="p", g=[x, y], r=0.7, _k="p:%s.%s" % (ref, num), t="%s.%s · %s" % (ref, num, nm), d=d, ref=ref))
            continue
        ws = by_end.get("%s.%s" % (ref, num), [])
        d = [pt] + pn + (tp_lines(net) if ref.startswith("TP") else pd[:1])
        if net == "NC":
            d.append("연결 없음 (NC) — 헤더 핀만 납땜")
        elif ws:
            d.append("이 패드에 오는 선: " + ", ".join(map(str, ws)) + (" (%s의 선 번호 — 아랫면)" % hidden if hidden else ""))
        else:
            d.append("이 아랫면에는 선이 없습니다 (윗면에서 이어짐)")
        items.append(dict(k="p", g=[x, y], r=0.95, n=None if net == "NC" else net, _k="p:%s.%s" % (ref, num), t="%s.%s · %s" % (ref, num, nm), d=d, ref=ref))
    for ref, x0, y0, x1, y1 in b["parts"]:
        extra = list(pnote.get(ref, []))
        if ref in by_ref:
            extra.append(("아랫면에서 이어진 선 (%s 번호): " % hidden if hidden else "이 그림에서 이어진 선: ") + " · ".join("%s %s" % (n, ", ".join(map(str, sorted(v)))) for n, v in sorted(by_ref[ref].items())))
        if ref == "C301":
            extra.append("먹스 GND–VCC 꼬리 사이에 아랫면으로 붙입니다(패드 없음).")
        if ref.startswith("TP"):
            extra = tp_lines({r_: n_ for r_, _num, n_, _x, _y, _s in b["pads"]}.get(ref, "")) + extra
        t, d = part_lines(info, ref)
        items.append(dict(k="r", g=[x0, y0, x1, y1], _k="r:" + ref, t=t, d=extra + d, ref=ref))
    for it in b.get("extra", []):
        if it.get("n") and it["n"] not in nets:
            nets[it["n"]] = net_block(it["n"], known, pins_by.get(it["n"]))
        items.append(it)
    if not keyed:
        for it in items:
            it.pop("_k", None)
    return items, nets


def key_items(keys, m3):
    """BRD-01~07: click targets named by a key (hitkeys.py) -> items with the 3D model's texts (m3 = model3d.build() data: info,
    netinfo). The same wire / pad / part reads the same on a drawing and in the 3D model. Returns (items, nets, keys without a text)."""
    info, netinfo = m3["info"], m3.get("netinfo", {})
    items, nets, miss, pads = [], {}, [], {}
    for it in keys:
        key = it.get("key")
        if key:
            I = info.get(key) or info.get(key.split(".")[0])
            if not I:
                miss.append(key)
                I = dict(t=key, d=[])
            t, d = I["t"], [x for x in I["d"] if not x.startswith(("KiCad:", "3D 자리:"))]
        else:
            t, d = "", []
        t = it.get("t") or t
        d = ([it["q"]] if it.get("q") else []) + list(it.get("d", [])) + d
        out = dict(k=it["k"], g=it["g"], t=t, d=d)
        if key and it["k"] in ("p", "r"):
            out["ref"] = key.split(".")[0]
        if it.get("m"):
            out["m"] = it["m"]
        if "r" in it:
            out["r"] = it["r"]
        if it.get("lo"):
            out["lo"] = 1                               # background: picked only when nothing else is under the pointer
        n = it.get("n")
        if n:
            nk = "%s|%s" % (it["m"], n) if it.get("m") else n
            out["n"] = nk
            if nk not in nets:
                N = netinfo.get(nk) or netinfo.get(n) or dict(t="넷 " + n, d=[])
                nets[nk] = dict(t=N["t"], d=list(N["d"]), c=B3.ncol(n))
            if it["k"] == "p" and key and key not in pads.setdefault(nk, []):
                pads[nk].append(key)
        items.append(out)
    for nk, ps in pads.items():
        nets[nk]["d"].append("이 도면에서 이 넷의 패드 %d개: %s%s" % (len(ps), ", ".join(ps[:26]), " …" if len(ps) > 26 else ""))
    return items, nets, miss


def build(info, out_path, m3=None):
    with open(os.path.join(NETLIST, "sheethits.json"), encoding="utf-8") as f:
        raw = json.load(f)
    known = mb_net_text()
    res, missing = {}, {}
    for code, h in raw.items():
        items, nets = [], {}
        if "board" in h:
            items, nets = board_items(code, h["board"], info, known)
        elif "segs" in h or "pins" in h:
            items, nets = sch_items(code, h, info, known)
        if h.get("keys") and m3:
            ki, kn, miss = key_items(h["keys"], m3)
            items += ki
            for k, v in kn.items():
                nets.setdefault(k, v)
            if miss:
                missing[code] = sorted(set(miss))
        # which board this sheet shows (the act line of a jumper / pull-down names only it): BRD-09 = O1 ... BRD-15 = O7
        bctx = {"BRD-%02d" % (8 + n): ["O%d" % n] for n in range(1, 8)}.get(code)
        res[code] = dict(items=items, nets=nets, **({"boards": bctx} if bctx else {}))
    cards = part_cards()
    used = {it.get("ref") for v in res.values() for it in v["items"]}
    for v in res.values():
        for it in v["items"]:
            if it.get("ref") and it["ref"] not in cards:
                rr = card_ref(it["ref"], cards)
                if rr:
                    it["ref"] = rr
                else:
                    it.pop("ref")
    res["_cards"] = {k: c for k, c in cards.items() if k in used or any(k == card_ref(u, cards) for u in used if u)}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    if missing:
        print("hits: keys without a text:", missing)
    return {k: len(v["items"]) for k, v in res.items() if k != "_cards"}
