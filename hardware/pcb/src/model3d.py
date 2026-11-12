"""3D model of the rev E circuit for the '01 회로도' tab: hardware/pcb/page/circuit3d.json (page.py ships it as fin/circuit/circuit3d.json).

usage:  python3 model3d.py          -> ../page/circuit3d.json + a short report (page.py calls build() itself)

No new geometry is made up here. Every board outline, hole, pad, part and wire is read from what the drawings and the CAD already use:
  * pads and nets: mbroute.pads_and_nets() (MB = SCH-03 + BRD-01), boards3.sb_pads() (SB), sheets.END_BOARDS (EL / ER, as BRD-02),
    netlist/pads_PB.csv (PB, BRD-03), netlist/pads_small.csv (J702 / J501 / PS, BRD-07); pad nets cross-checked with netlist.csv
  * underside wires: netlist/wiring_MB.csv, wiring_SB.csv, wiring_PB.csv, wiring_small.csv, the bare SB buses (boards3.SB_BUS) and the
    EL / ER strands of BRD-02 (straight, as drawn)
  * part bodies and heights: CAD spec hardware/mechanical/cad/spec/electronics_modules.json (MB, Zero, mux, ribbon, USB plug, SB, EL / ER,
    hall sensors (WSH137, TO-92S) in the sensor-bar pockets) and keyaction_features_frame.json (J701 pocket)
  * module frame context (△33 = CAD A16): the separate balance rail on the MB strip, fins 2 / 4 and the F|F# fin over the board, the
    floor ribs under it - sheets.MB (same numbers as spec mb_board keepouts / cad/src/keyaction.py A16)
  * centre unit: netlist/cad_centre.json (CAD outlines, boxes, wire centre lines, fixing points) and harness.py (conductor colours)
Where a source only gives an envelope (Zero top parts, modules, jacks) the model shows the envelope. Places that depend on the received
part (PJ-313 legs, the W502 path, the RP2040 chip spot on the Zero) are drawn and marked '추정'.

Coordinates: mm, z up from the desk. Module scene = module-local x (world x = 47 + 164.5 (k - 1) + x); EL / ER = end-part local x
(ER shown beside EL); the rest in world x as the CAD.
JSON objects (short keys, the viewer src/circuit3d.js builds the meshes):
  {k:'b', b:[x0,y0,z0,x1,y1,z1]}                box          {k:'c', a:'x'|'y'|'z', p:[u,v], r, s:[s0,s1]}   cylinder
  {k:'t', p:[[x,y,z]..], r}                     tube         {k:'e', p:[[x,y]..] | [[[x,y]..]..], z:[z0,z1]}  prism (outline + holes)
                                                             {k:'e', ax:'x', p:[[y,z]..], z:[x0,x1]}       side outline extruded along x
  {k:'B', p:[[x,y]..], z:[z0,z1], h:[[x,y]..], m:[[x,y,d]..]}  perfboard: outline, lattice holes (texture), drilled holes
  {k:'p', p:[x,y], z:[z0,z1], s:'b'|'t'|'bt'}   pad + solder     {k:'l', p:[x,y,z], t}                         label
  common: c colour, i info key, g layer (board / part / pad / wire / cable / ctx), n net, o opacity, w '주석 맨선' | '피복 가닥' ...
          m scope ('O1'..'O7', 'EL', 'ER', 'PED', 'AUD': a net name is one net only inside its scope; scene 'join' ties scopes together,
          e.g. O1 EXT1 = EL EL_A0 through the XH pair), v info variant (info key 'i@v' first: what differs on one board kind),
          q one more line for this object only (which core of a ribbon, which key a sensor reads), dz (labels) shown only when the
          camera is closer than this
  top level: info {key: {t, d}} what the thing is / what it connects to, netinfo {net or 'scope|net': {t, d}} what the net does
  scene: scopes {m: {t, d}} (where the picked thing sits), join {'m|net': 'm|net'}
"""
import csv
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ROOT, "..", ".."))
NL = os.path.join(ROOT, "netlist")
OUT = os.path.join(ROOT, "page", "circuit3d.json")
SPEC = os.path.join(REPO, "hardware", "mechanical", "cad", "spec")
sys.path.insert(0, HERE)

import boards2 as B2   # noqa: E402
import boards3 as B3   # noqa: E402
import boards4 as B4   # noqa: E402
import harness as HN   # noqa: E402
import hitkeys as HK   # noqa: E402
import hits as HT      # noqa: E402
import mbroute as MR   # noqa: E402
import sheets as S     # noqa: E402

REV = "E"
X_O1, MODULE_W = 47.0, 164.5
X_RIGHT = 1198.5                      # ER local x0 (world)
ER_SHOW_DX = 60.0                     # ER drawn beside EL in the end-part scene

# physical colours (CAD palette where the CAD has one: electronics.COLORS)
C = dict(perf="#c8a45a", perf_side="#a8863f", pcb_blue="#2a5caa", pcb_green="#2f7d4f", pcb_dark="#1f3f2c", chip="#1d1d1f",
         kapton="#d08a2a", header="#222326", pin="#d8c27a", solder="#c9ccd2", copper="#c9894b", tin="#c9ccd2", res="#d8c49a",
         res_body100k="#d8c49a", cap1206="#b98b5a", capend="#c9ccd2", mlcc="#3d6fb5", ribbon="#a7adb8", ribbon_red="#c0392b",
         usb="#2b2b2b", shell="#b8bec6", cable="#3a3a3a", jack="#202124", hall="#1d1d1f", lead="#c0c6cc", ctx="#7d858f",
         bar="#6b8fb5", screw="#5a5f66", xt60="#e0b020", fuse="#d9473a", battery="#24427a", pi="#2e7d32", hub="#1f2227",
         dongle="#eceef1", amp="#2a5caa", buck="#2a5caa", heat="#9aa3ad", ffc="#b8862f", ply="#d9b98b", printed="#7d858f",
         wire_wht="#e6e8ec", shrink_red="#c0392b", shrink_blu="#1f5fbf", frame="#8f9bb0")
BANDS = {"1k": ["#7a4a1e", "#111", "#c0392b"], "100k": ["#7a4a1e", "#111", "#e8c61a"], "100": ["#7a4a1e", "#111", "#7a4a1e"]}


def r2(v):
    return round(float(v), 2)


def col(net):
    return B3.ncol(net)


def _shift(o, dx):
    """move one object dx along x (a module / end part placed in the instrument scene)."""
    k = o["k"]
    if k == "b":
        o["b"][0], o["b"][3] = r2(o["b"][0] + dx), r2(o["b"][3] + dx)
    elif k == "c":
        if o["a"] == "x":
            o["s"] = [r2(v + dx) for v in o["s"]]
        else:
            o["p"][0] = r2(o["p"][0] + dx)
    elif k == "t":
        for q in o["p"]:
            q[0] = r2(q[0] + dx)
    elif k == "e":
        if o.get("ax") == "x":
            o["z"] = [r2(v + dx) for v in o["z"]]
        elif o["p"] and isinstance(o["p"][0][0], (int, float)):
            o["p"] = [[r2(x + dx), y] for x, y in o["p"]]
        else:
            o["p"] = [[[r2(x + dx), y] for x, y in pl] for pl in o["p"]]
    elif k == "B":
        for key in ("p", "h", "md"):
            for q in o[key]:
                q[0] = r2(q[0] + dx)
        if o.get("hg"):
            o["hg"][0] = r2(o["hg"][0] + dx)
    elif k in ("p", "l"):
        o["p"][0] = r2(o["p"][0] + dx)


class Scene:
    def __init__(self, sid, title, sub, frame, short=None):
        self.d = dict(id=sid, t=title, st=short or title, s=sub, f=frame, objs=[], views={}, notes=[])
        self.dx = 0.0       # x offset of what is being added
        self.m = None       # scope of what is being added ('O3', 'EL' ...)
        self.v = None       # board kind of what is being added (info variants)
        self.bd = None      # netlist board of the pads being added ('SB', 'MB' ...), kept as '_bd' until the output
        self.dz = None      # {label level: camera distance below which the label shows}

    def add(self, **o):
        o = {k: v for k, v in o.items() if v is not None}
        if self.dx:
            _shift(o, self.dx)
        if self.m and "m" not in o:
            o["m"] = self.m
        if o["k"] == "l":
            if o.get("dz") == 0:
                del o["dz"]                                        # far label: always shown
            elif self.dz and self.dz.get(o.get("lv", 1)):
                o["dz"] = self.dz[o.get("lv", 1)]
        self.d["objs"].append(o)
        return o

    def box(self, b, c, i=None, g="part", n=None, o=None, w=None, q=None):
        x0, y0, z0, x1, y1, z1 = b
        return self.add(k="b", b=[r2(min(x0, x1)), r2(min(y0, y1)), r2(min(z0, z1)), r2(max(x0, x1)), r2(max(y0, y1)), r2(max(z0, z1))],
                        c=c, i=i, g=g, n=n, o=o, w=w, q=q)

    def cyl(self, a, p, r, s, c, i=None, g="part", n=None, o=None):
        return self.add(k="c", a=a, p=[r2(p[0]), r2(p[1])], r=r2(r) if r >= 0.05 else round(r, 3), s=[r2(min(s)), r2(max(s))], c=c, i=i, g=g,
                        n=n, o=o)

    def tube(self, pts, r, c, i=None, g="wire", n=None, w=None, o=None, q=None):
        pp = [[r2(x), r2(y), r2(z)] for x, y, z in pts]
        pp = [p for k, p in enumerate(pp) if k == 0 or p != pp[k - 1]]
        if len(pp) < 2:
            return None
        return self.add(k="t", p=pp, r=round(r, 3), c=c, i=i, g=g, n=real_net(n), w=w, o=o, q=q)

    def prism(self, poly, z, c, i=None, g="part", o=None, n=None):
        return self.add(k="e", p=poly, z=[r2(z[0]), r2(z[1])], c=c, i=i, g=g, o=o, n=n)

    def board(self, poly, z, holes, c, i, mholes=(), side=None, grid=None):
        """grid = (x0, pitch x, columns, y0, pitch y, rows): a full lattice written as six numbers instead of every hole."""
        return self.add(k="B", p=[[r2(x), r2(y)] for x, y in poly], z=[r2(z[0]), r2(z[1])], h=[[r2(x), r2(y)] for x, y in holes],
                        hg=[r2(v) for v in grid] if grid else None,
                        md=[[r2(x), r2(y), r2(d)] for x, y, d in mholes], c=c, cs=side or C["perf_side"], i=i, g="board")

    def pad(self, x, y, z, n, i, s="b", v=None):
        return self.add(k="p", p=[r2(x), r2(y)], z=[r2(z[0]), r2(z[1])], n=real_net(n), i=i, s=s, g="pad", v=v, _bd=self.bd)

    def label(self, p, t, lv=1, far=False):
        return self.add(k="l", p=[r2(v) for v in p], t=t, lv=lv, dz=0 if far else None)

    def view(self, name, box, az=-35, el=38, default=False):
        self.d["views"][name] = dict(b=[r2(v) for v in box], az=az, el=el)
        if default:
            self.d["v0"] = name

    def note(self, t):
        self.d["notes"].append(t)


# ====================================================================== sources
def read_csv(name):
    with open(os.path.join(NL, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_rows(name):
    with open(os.path.join(NL, name), encoding="utf-8-sig") as f:
        return list(csv.reader(f))


PT_RX = re.compile(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")


def parse_path(s):
    return [(float(a), float(b)) for a, b in PT_RX.findall(s)]


def load_spec():
    with open(os.path.join(SPEC, "electronics_modules.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {i["id"]: i for i in d["module_items"] + d["end_items"]}


def load_jack_spec():
    with open(os.path.join(SPEC, "keyaction_features_frame.json"), encoding="utf-8") as f:
        d = json.load(f)
    return d["cheeks"]["headphone_jack"]


def bx(b):
    return [b["x"][0], b["y"][0], b["z"][0], b["x"][1], b["y"][1], b["z"][1]]


# netlist pins: (board, ref, pin) -> net ; ref -> board(s)
NET_ROWS = read_csv("netlist.csv")
PIN_NET = {}
for _r in NET_ROWS:
    PIN_NET[(_r["보드"], _r["부품"], _r["핀"])] = _r["넷"]


def pin_net(board, ref, pin):
    return PIN_NET.get((board, ref, str(pin)))


def real_net(net):
    """None for pads that carry no net: 'NC', '연결 금지 (…)' (pads_PB.csv), unnamed '~…' nets of the drawn netlist."""
    if not net or net == "NC" or net.startswith(("연결 금지", "~")):
        return None
    return net


# ====================================================================== info (click panel)
INFO = {}        # raw texts: bom.csv / cables.csv + what the scenes add (hits.py takes its part texts from here, page.py)
OVR = {}         # texts of the 3D model that replace INFO in the output: 'key' or 'key@kind' -> {t, d}
BOMV = {}        # ref -> value column of bom.csv
PIN_NAME = {(r["보드"], r["부품"], r["핀"]): r["핀 이름"] for r in NET_ROWS}
REAL_NETS = {r["넷"] for r in NET_ROWS}
MUX_ROWS = {r["먹스 채널"]: r for r in read_csv("mux_map.csv")}
SENS = read_csv("sb_sensors.csv")
ID_ROWS = {r["보드"]: r for r in read_csv("id_jumpers.csv")}


def info(key, title, lines):
    if key and key not in INFO:
        INFO[key] = dict(t=title, d=[x for x in lines if x])


def ovr(key, title, lines):
    OVR[key] = dict(t=title, d=[x for x in lines if x])


def board_info(key, title, lines):
    """a board: what it is and does first (the scene's text), then how it is bought (bom.csv, when the board has a BOM line)."""
    bom = INFO.get(key)
    more = [x for x in (bom["d"] if bom and key in BOMV else []) if x.startswith(("구매", "실장"))]
    if bom and key in BOMV:
        more.insert(0, "기판 재료: " + bom["d"][0])
    ovr(key, title, list(lines) + more)
    info(key, title, lines)


def vinfo(key, kind, title, lines):
    """text of `key` on one MB kind: the first kind built gives the common text, a kind whose text differs gets 'key@kind'.
    True when this kind needs the variant."""
    e = dict(t=title, d=[x for x in lines if x])
    if key not in OVR:
        OVR[key] = e
        return False
    if OVR[key] == e:
        return False
    OVR["%s@%s" % (key, kind)] = e
    return True


def bom_info():
    rows = read_csv("bom.csv")
    by = {}
    for r in rows:
        by.setdefault(r["부품"], []).append(r)
    for ref, rs in by.items():
        r = rs[0]
        BOMV[ref] = r["값"]
        boards = sorted({x["보드"] for x in rs})
        pins = sorted({(p["핀"], p["넷"]) for p in NET_ROWS if p["부품"] == ref and p["보드"] in boards},
                      key=lambda t: (len(t[0]), t[0]))
        def where(pin, net):
            if not net.startswith(("~", "(이름 없음")):
                return net
            other = sorted({"%s.%s" % (q["부품"], q["핀"]) for q in NET_ROWS if q["넷"] == net and q["보드"] in boards
                            and (q["부품"], q["핀"]) != (ref, pin)})
            return ("↔ " + ", ".join(other)) if other else "연결 없음"
        def pname(pin):
            nm = next((PIN_NAME.get((b_, ref, pin)) for b_ in boards if PIN_NAME.get((b_, ref, pin))), "")
            return "%s (%s)" % (pin, nm) if nm and nm != pin else pin
        conn = [(p, where(p, n)) for p, n in pins]
        pin_txt = ", ".join("%s → %s" % (pname(p), w) for p, w in conn if w != "연결 없음")
        free = [pname(p) for p, w in conn if w == "연결 없음"]
        if free:
            pin_txt += (" · " if pin_txt else "") + "연결 없는 핀: " + ", ".join(free)
        info(ref, "%s · %s" % (ref, r["값"]), [
            r["부품 설명"],
            "보드 %s · %s장 × %s = %s개" % ("/".join(boards), r["보드 수"], r["보드당"], r["전체 수량"]),
            ("실장: " + r["실장 조건"]) if r["실장 조건"] else "",
            "핀이 이어진 넷: " + pin_txt if pin_txt else "",
            "KiCad: " + r["KiCad 풋프린트"] if r["KiCad 풋프린트"] else "",
            "구매: %s %s · %s" % (r["구매 목록 코드"], r["구매처"], r["구매 상태 (최종 목록)"]),
            "도면 " + r["도면"],
        ])
    return by


def cable_info():
    """cables.csv (one line per lead) + harness.csv (one line per conductor: net, the pin at each end)."""
    code = {}
    for r in read_csv("cables.csv"):
        cut = r["자르는 길이 (mm)"]
        info(r["W"], "%s · %s" % (r["W"], r["선"]), ["잇는 곳: %s → %s" % (r["한쪽"], r["다른 쪽"]),
                                                       "자르는 길이: " + cut + (" mm" if re.fullmatch(r"[\d. ×+/]+", cut) else ""),
                                                       ("심: " + r["심"]) if r["심"] not in ("", "—") else "", "구매 목록: " + r["구매 목록 코드"]])
        code[r["W"]] = r["구매 목록 코드"]
    by = {}
    for r in read_csv("harness.csv"):
        by.setdefault(r["W"], []).append(r)
    for w, rs in by.items():
        r0 = rs[0]
        if len(rs) > 6:
            cores = ["심마다 넷: " + " · ".join("%s %s" % (r["심 번호"], r["넷"]) for r in rs) + " (두 끝 모두 같은 번호 구멍)"]
        else:
            cores = ["%s번 심 (%s) · 넷 %s: A 끝 %s → B 끝 %s" % (r["심 번호"], r["색"], r["넷"], r["A 핀"], r["B 핀"]) for r in rs]
        ovr(w, "%s · %s" % (w, r0["이름"]), ["잇는 곳: (A) %s → (B) %s" % (r0["끝 A"], r0["끝 B"]), "선: " + r0["선"], "자르는 길이: " + r0["자르는 길이"]] + cores +
            [("수축 튜브: " + r0["수축 튜브"]) if r0["수축 튜브"] else "", ("구매 목록: " + code[w]) if code.get(w) else ""])
    OVR["W101~W107"]["d"] += ["두 끝 모두 아랫면에서 꽂습니다. 자르는 길이 70 (경로 약 30): SB·리본·MB를 작업대에서 한 묶음으로 납땜하고 남는 약 35는 "
                              "기판 앞 검은 건반 탭 받침 사이 바닥에 평평하게 접어 둡니다 (△33).",
                              "1번 심(빨간 줄) = 3V3, 2·15 = GND, 3~14 = HALL_C~B, 16 = 3V3 (△12)."]


def cond_net(wid, colour):
    """net of the conductor of that colour in a harness lead (harness.py), None unless it is a real net of the netlist."""
    h = B4._harness(wid)
    for c in (h["cond"] if h else []):
        if c[1] == colour:
            n = c[2].split(" (")[0]
            return n if n in REAL_NETS else None
    return None


def kind_of(k):
    return "O1" if k == 1 else ("O7" if k == 7 else "MID")


_KT = {}
_FIX = (("(점선)", "(3D 모델에서는 흐리게 보임)"), ("점선 선 ", "흐린 선 "), (" (그림 왼쪽)", ""), ("이 그림에서 이어진 선", "아랫면에서 이어진 선"),
        (" (그림에서 연하게 함께 표시)", ""), ("이 패드에 오는 선: ", "이 패드에 오는 아랫면 선 번호: "))


def _fix(t):
    for a, b in _FIX:
        t = t.replace(a, b)
    return t


def kind_texts(kind):
    """click texts of the control board for one board kind - the same texts as the drawings BRD-09 / 10 / 11 (boards4.py -> hits.py),
    put into OVR. Returns (keys whose text differs on this kind, the EXT lead strand items)."""
    if kind not in _KT:
        V = B4.KINDS[kind]
        sh = B4._sheet(kind)
        items, _n = HT.board_items(V["code"], sh.hits_custom, INFO, HT.mb_net_text(), keyed=True)
        var, seen = set(), set()
        for it in items:
            kk = it.get("_k")
            if not kk or kk in seen:
                continue
            seen.add(kk)
            typ, ref = kk.split(":", 1)
            if typ == "r" and not ref.startswith(("A30", "C30", "R30", "JP30")):
                continue
            key = "MBW-" + ref if typ == "w" else ref
            title = ("MB 아랫면 " + it["t"]) if typ == "w" else it["t"]
            more = ["도면 BRD-08 (아랫면 배선) · BRD-09~11 (기판 종류별 앞·뒤)"] if typ == "w" else []
            if vinfo(key, kind, title, [_fix(x) for x in it["d"]] + more):
                var.add(key)
        _KT[kind] = (var, [e for e in sh.hits_custom["extra"] if e["k"] == "w"])
    return _KT[kind]


def scope_module(k):
    """where a picked thing sits: one octave module."""
    tag = "O%d" % k
    V = B4.KINDS[kind_of(k)]
    row = ID_ROWS[tag]
    midi = 24 + 12 * (k - 1)
    jp = " · ".join("%s %s" % (ref, "닫음" if ref in B4.jp_closed(k) else "열림") for ref in ("JP301", "JP302", "JP303"))
    d = ["USB 이름 '%s' · 선 W20%d → 허브 포트 %s" % (row["USB 이름"], k, row["허브 포트"]),
         "ID 점퍼: " + jp,
         "제어 기판 종류: %s — R30x %s, J302 %s (도면 %s)" % (V["name"], " · ".join(V["r"]) if V["r"] else "없음",
                                                      ("%s %d가닥 → 끝 부속 %s" % (V["lead"], len(V["ext"]), V["end"])) if V["lead"] else "비움", V["code"])]
    if V["end"]:
        d.append("끝 부속 %s의 센서(%s 건반)도 이 기판이 읽습니다." % (V["end"], V["end_keys"]))
    return dict(t="옥타브 모듈 %s — 건반 C%d~B%d (MIDI %d~%d)" % (tag, k, k, midi, midi + 11), d=d)


def scope_end(tag):
    Bd = S.END_BOARDS[tag]
    keys = " · ".join(k[1] for k in Bd["keys"])
    if tag == "EL":
        return dict(t="끝 부속 EL (왼쪽 끝) — 건반 %s (MIDI 21~23)" % keys,
                    d=["센서 출력은 J401 → W401 → X401 ⇄ X402 → W403 → O1 제어 기판 J302로 가서 먹스 C12~C14(EXT1~3)로 읽힙니다.",
                       "전원 3.3 V와 GND도 같은 선으로 O1에서 옵니다."])
    return dict(t="끝 부속 ER (오른쪽 끝) — 건반 %s (MIDI 108)" % keys,
                d=["센서 출력은 J411 → W411 → X411 ⇄ X412 → W413 → O7 제어 기판 J302로 가서 먹스 C12(EXT1)로 읽힙니다.",
                   "전원 3.3 V와 GND도 같은 선으로 O7에서 옵니다."])


def net_texts():
    """what each net does (title, lines) for the nets outside the control board; 'scope|net' = the text inside that scope only.
    The control-board nets come from hits.mb_net_text() (same texts as the drawings)."""
    out = {
        "PED_TIP": ("PED_TIP · 페달 선 TIP (센서 신호)", [
            "페달 안 센서 조각 PS: U551 OUT → R551 1 kΩ → 페달 선 W501 TIP → J501 T → W502 → PB J502 1번 → R501 1 kΩ → PED_ADC.",
            "R502 100 kΩ이 GND로 당겨 페달이 빠지면 0 V가 됩니다. TP501에서 잴 수 있습니다."]),
        "PED_VCC": ("PED_VCC · 페달 선 RING (센서 전원)", [
            "PB의 +3V3 → R503 (100 Ω 5개 나란히 = 20 Ω) → J502 3번 → W502 → J501 R → 페달 선 W501 RING → PS의 U551 VCC · C551.",
            "TP502에서 잴 수 있습니다."]),
        "PED_ADC": ("PED_ADC · 페달 ADC 입력", ["R501 1 kΩ 뒤 → A501 GP26 (ADC0). C501 100 nF가 GND로 이어져 잡음을 줄입니다."]),
        "PED|PED_SEL": ("PED_SEL · 페달 보드 표시", ["A501 GP14 ↔ JP504. 페달 보드 PB에서는 닫아서(GND) 펌웨어가 페달 보드로 동작합니다."]),
        "PED|+3V3": ("+3V3 · 페달 보드 3.3 V", ["A501 RP2040-Zero의 3V3 핀(USB 5 V → 내장 레귤레이터)에서 나와 R503을 거쳐 페달 센서 전원(PED_VCC)이 됩니다."]),
        "PED|GND": ("GND · 접지", ["A501 GND, J502 2·4번(페달 잭 TN·S), R502, C501, JP504 GND 쪽. USB 선(W208)으로 허브·Pi와 같은 접지입니다."]),
        "CU|GND": ("GND · 접지 (가운데 유닛)", ["배터리 − → W601 검정 → ★ 별 접지(강압 A602 IN−) → 강압 OUT− → Pi 5 · 허브, 그리고 ★ → 앰프 A702 DC−.",
                                         "USB 선으로 제어 기판 7장·페달 보드의 GND와도 이어져 악기 전체가 한 접지입니다."]),
        "EL|GND": ("GND · 접지 (끝 부속 EL)", ["J401 1번 → W401 → X401 ⇄ X402 → W403 → O1 제어 기판 J302 1번. 센서 U401~U403과 콘덴서의 GND."]),
        "ER|GND": ("GND · 접지 (끝 부속 ER)", ["J411 1번 → W411 → X411 ⇄ X412 → W413 → O7 제어 기판 J302 1번. 센서 U411과 콘덴서의 GND."]),
        "+3V3_EL": ("+3V3_EL · 끝 부속 EL 전원 3.3 V", ["O1 제어 기판의 +3V3 → J302 6번 → W403 → X402 ⇄ X401 5번 → W401 → J401 5번 → 센서 U401~U403 VCC · C401~C404."]),
        "+3V3_ER": ("+3V3_ER · 끝 부속 ER 전원 3.3 V", ["O7 제어 기판의 +3V3 → J302 6번 → W413 → X412 ⇄ X411 3번 → W411 → J411 3번 → 센서 U411 VCC · C411 · C412."]),
        "VBAT": ("VBAT · 배터리 + (퓨즈 앞)", ["BT601 + → 팩 XT60 암 X605 ⇄ XT60 수 X606 → W601 → 퓨즈 F601."]),
        "VBAT_F": ("VBAT_F · 퓨즈 뒤", ["F601 5 A 뒤 → W602a → 스위치 SW601 입력 단자 1·3 (두 회로를 나란히, W602j)."]),
        "+12V8": ("+12V8 · 스위치 뒤 12.8 V", ["SW601 출력 단자 2·4 → W602b → 강압 A602 IN+, W602c → 앰프 A702 DC+. TP601에서 잽니다."]),
        "+5V1": ("+5V1 · 강압 출력 5.1 V", ["A602 OUT+ → W603 → P601 (Pi 5 USB-C 전원), W604 → P602 (허브 DC 잭). TP602에서 잽니다."]),
        "+5V_PI": ("+5V_PI · Pi 헤더 5 V (화면 전원)", ["Pi 5 40핀 헤더 2번 → W606 → W607 → W608 → 화면 A605 5V."]),
        "AGND": ("AGND · 오디오 접지", ["동글 A701 슬리브 → W701 → J701 S → W702 → J702 S → R701·R702 → W707 → 앰프 A702 입력 GND."]),
        "DAC_L": ("DAC_L · 동글 출력 왼쪽", ["동글 A701 → 플러그 P701 → W701 → 헤드폰 잭 J701 T."]),
        "DAC_R": ("DAC_R · 동글 출력 오른쪽", ["동글 A701 → 플러그 P701 → W701 → 헤드폰 잭 J701 R."]),
        "HP_TN_L": ("HP_TN_L · 헤드폰 잭 노멀 접점 왼쪽", ["헤드폰을 꽂지 않았을 때만 J701 TN이 T에 붙어 신호가 넘어옵니다 → W702 → J702 T → C701 ∥ C702.",
                                                 "헤드폰을 꽂으면 끊겨 스피커가 조용해집니다."]),
        "HP_RN_R": ("HP_RN_R · 헤드폰 잭 노멀 접점 오른쪽", ["헤드폰을 꽂지 않았을 때만 J701 RN이 R에 붙습니다 → W702 → J702 R → C703 ∥ C704."]),
        "AMP_IN_L": ("AMP_IN_L · 앰프 입력 왼쪽", ["C701 ∥ C702 (1 µF × 2) 뒤, R701 1 kΩ이 AGND로 (80 Hz 고역 통과) → W707 → 앰프 A702 INL."]),
        "AMP_IN_R": ("AMP_IN_R · 앰프 입력 오른쪽", ["C703 ∥ C704 (1 µF × 2) 뒤, R702 1 kΩ이 AGND로 (80 Hz 고역 통과) → W707 → 앰프 A702 INR."]),
    }
    for ch, side, w1, x1, w2, ls in (("L", "왼쪽", "W703", "X703 ⇄ X704", "W704", "LS701"), ("R", "오른쪽", "W705", "X705 ⇄ X706", "W706", "LS702")):
        for pol, sym in (("P", "+"), ("N", "−")):
            out["SPK_%s_%s" % (ch, pol)] = ("SPK_%s_%s · 스피커 %s %s" % (ch, pol, side, sym),
                                             ["앰프 A702 OUT%s%s → %s → %s → %s → 스피커 %s %s." % (ch, sym, w1, x1, w2, ls, sym)])
    for tag, mod in (("EL", "O1"), ("ER", "O7")):
        Bd = S.END_BOARDS[tag]
        lead, mate, lead2 = ("W401", "X401 ⇄ X402", "W403") if tag == "EL" else ("W411", "X411 ⇄ X412", "W413")
        for i_, (u, key, xk, cref, rref) in enumerate(Bd["keys"]):
            net = Bd["jnames"][1 + i_]
            midi = MUX_ROWS["C%d" % (12 + i_)][mod].split("= ")[-1]
            out[net] = ("%s · %s 건반 센서 출력 (끝 부속 %s)" % (net, key, tag),
                        ["%s OUT → %s 1 kΩ → %s %d번 → %s → %s → %s → %s 제어 기판 J302 %d번 = EXT%d → 먹스 C%d (MIDI %s)."
                         % (u, rref, Bd["jref"], i_ + 2, lead, mate, lead2, mod, i_ + 2, i_ + 1, 12 + i_, midi)])
    return out


def cu_pins(net):
    """the pins of a centre-unit net as the schematic lists them (those parts have no pads in the model)."""
    ps = ["%s.%s%s" % (r["부품"], r["핀"], (" " + r["핀 이름"]) if r["핀 이름"] and r["핀 이름"] != r["핀"] else "")
          for r in NET_ROWS if r["넷"] == net and r["보드"].startswith(("CU", "J701"))]
    if not ps or net == "GND":
        return []
    return ["회로도(SCH-06 · SCH-07)에서 이 넷의 핀: " + ", ".join(ps)]


# ---------------------------------------------------------------------- pads <-> wires by geometry
def _seg_d(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = ((x - a[0]) * dx + (y - a[1]) * dy) / L if L else 0.0
    t = max(0.0, min(1.0, t))
    return math.hypot(a[0] + t * dx - x, a[1] + t * dy - y)


def _base_ref(ref):
    return re.sub(r"(?<=\d)[a-e]$", "", ref)


def pad_name(o):
    ref, pin = o["i"].split(".", 1)
    bd = o.get("_bd")
    nm = PIN_NAME.get((bd, ref, pin)) or PIN_NAME.get((bd, _base_ref(ref), pin)) or ""
    return ref, pin, ("" if nm == pin else nm)


def pad_text(o):
    ref, pin, nm = pad_name(o)
    val = BOMV.get(ref) or BOMV.get(_base_ref(ref)) or ""
    return "%s.%s%s%s" % (ref, pin, (" " + nm) if nm else "", (" (%s)" % val) if val else "")


def link(sc):
    """pads <-> wires of one scene by where they are: where each underside wire starts and ends (a bare bus: every pad it passes),
    which board wires and cable cores meet at each pad -> OVR. Texts are per info key, so the copies in the instrument scene share
    them. Keys that already have a text (the control board: hits.py) are left alone."""
    objs = sc.d["objs"]
    pads = [o for o in objs if o["k"] == "p"]

    def z_ok(p, z):
        return p["z"][0] - 4.0 <= z <= p["z"][1] + 4.0

    def at(m, q):
        for p in pads:
            if p.get("m") == m and abs(p["p"][0] - q[0]) <= 0.2 and abs(p["p"][1] - q[1]) <= 0.2 and z_ok(p, q[2]):
                return p
        return None

    def title(key):
        return (OVR.get(key) or INFO.get(key) or dict(t=key))["t"]
    meet = {}

    def note(p, which, t):
        lst = meet.setdefault(p["i"], ([], []))[which]
        if t not in lst:
            lst.append(t)
    for o in objs:
        if o["k"] != "t" or not o.get("i"):
            continue
        key, g, m, pts = o["i"], o.get("g"), o.get("m"), o["p"]
        if g == "wire" and o.get("w"):
            bare = o.get("w") == "주석 맨선"
            if bare:
                ps = [p for p in pads if p.get("m") == m and z_ok(p, pts[0][2])
                      and any(_seg_d(p["p"][0], p["p"][1], a, b) <= 0.2 for a, b in zip(pts, pts[1:]))]
                ps.sort(key=lambda p: (p["p"][0], p["p"][1]))
            else:
                ps = [p for p in (at(m, pts[0]), at(m, pts[-1])) if p]
            for p in ps:
                note(p, 0, title(key))
            if key not in OVR and key in INFO and ps:
                if bare:
                    lines = ["지나는 패드 %d개에 모두 납땜: %s%s" % (len(ps), ", ".join(pad_text(p) for p in ps[:16]),
                                                           " … 외 %d개" % (len(ps) - 16) if len(ps) > 16 else "")]
                elif len(ps) == 2:
                    lines = ["시작: " + pad_text(ps[0]), "끝: " + pad_text(ps[1])]
                else:
                    lines = ["이어진 패드: " + pad_text(ps[0])]
                ovr(key, INFO[key]["t"], lines + INFO[key]["d"])
        elif g == "cable" and o.get("n"):
            for q in (pts[0], pts[-1]):
                p = at(m, q)
                if p:
                    note(p, 1, title(key).split(" · ")[0] + ((" " + o["q"].split(" · ")[0]) if o.get("q") else ""))
    for p in pads:
        key = p["i"]
        if key in OVR:
            continue
        ref, pin, nm = pad_name(p)
        base = INFO.get(ref) or INFO.get(_base_ref(ref))
        w, c = meet.get(key, ([], []))
        d = []
        if base:
            d.append(base["t"])
            d += [x for x in base["d"][:1] if not x.startswith(("KiCad", "도면", "보드 "))]
        if w:
            d.append("이 패드에 납땜하는 기판 선: " + " · ".join(w))
        if c:
            d.append("이 패드에 꽂는 선·리본: " + " · ".join(c))
        if not w and not c and not p.get("n"):
            d.append("연결 없음 — 납땜만 하거나 비워 둡니다.")
        ovr(key, "%s.%s%s" % (ref, pin, (" · " + nm) if nm else ""), d)


# ====================================================================== shape helpers
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def lattice(xs, ys, inside=None):
    return [(x, y) for x in xs for y in ys if inside is None or inside(x, y)]


def corner_u_outline(x0, x1, y0, y1, ux, uy0, uy1, r):
    """Board rectangle with two U-slots open to the left edge x0 (SB / EL / ER: slot centres (ux, uy0) front, (ux, uy1) rear, radius r;
    both circles reach past the front / rear edge, so each slot is a corner notch with a round inner end)."""
    pts = []
    # front-left notch: from the left edge at y = uy0 + r, around the circle (90 deg -> where it meets the front edge y0)
    a_end = math.asin(max(-1.0, min(1.0, (y0 - uy0) / r)))
    pts.append((x0, uy0 + r))
    pts.append((ux, uy0 + r))
    for k in range(1, 13):
        a = math.pi / 2 - (math.pi / 2 - a_end) * k / 12.0
        pts.append((ux + r * math.cos(a), uy0 + r * math.sin(a)))
    pts.append((x1, y0))
    pts.append((x1, y1))
    a_st = math.asin(max(-1.0, min(1.0, (y1 - uy1) / r)))
    for k in range(0, 13):
        a = a_st - (a_st + math.pi / 2) * k / 12.0
        pts.append((ux + r * math.cos(a), uy1 + r * math.sin(a)))
    pts.append((x0, uy1 - r))
    return pts


def resistor(sc, ref, p1, p2, zt, value, g="part", zb=None, n=None, lift=1.25):
    """axial resistor lying on the top face: body D2.5 x 6.3 centred between the two holes, leads bent down through the board."""
    (x1, y1), (x2, y2) = p1, p2
    zc = zt + lift
    ax = "x" if abs(x2 - x1) >= abs(y2 - y1) else "y"
    L = abs(x2 - x1) if ax == "x" else abs(y2 - y1)
    bl = min(6.3, L - 1.0)
    if ax == "x":
        xm, y = (x1 + x2) / 2.0, y1
        sc.cyl("x", (y, zc), 1.25, (xm - bl / 2, xm + bl / 2), C["res"], i=ref, g=g)
        for k, bc in enumerate(BANDS.get(value, [])):
            u = xm - bl / 2 + 0.9 + 0.75 * k
            sc.cyl("x", (y, zc), 1.29, (u, u + 0.4), bc, i=ref, g=g)
        for xe, xp in ((xm - bl / 2, min(x1, x2)), (xm + bl / 2, max(x1, x2))):
            sc.tube([(xe, y, zc), (xp + (0.6 if xp < xe else -0.6), y, zc), (xp, y, zc - 0.6), (xp, y, (zb if zb is not None else zt - 1.6) - 1.0)],
                    0.25, C["lead"], i=ref, g=g)
    else:
        ym, x = (y1 + y2) / 2.0, x1
        sc.cyl("y", (x, zc), 1.25, (ym - bl / 2, ym + bl / 2), C["res"], i=ref, g=g)
        for k, bc in enumerate(BANDS.get(value, [])):
            u = ym - bl / 2 + 0.9 + 0.75 * k
            sc.cyl("y", (x, zc), 1.29, (u, u + 0.4), bc, i=ref, g=g)
        for ye, yp in ((ym - bl / 2, min(y1, y2)), (ym + bl / 2, max(y1, y2))):
            sc.tube([(x, ye, zc), (x, yp + (0.6 if yp < ye else -0.6), zc), (x, yp, zc - 0.6), (x, yp, (zb if zb is not None else zt - 1.6) - 1.0)],
                    0.25, C["lead"], i=ref, g=g)


def chip1206(sc, ref, p1, p2, zb, under=True, g="part"):
    """1206 across two holes (3.2 x 1.6 x 0.9) on the underside (under=True: hangs below zb) or the top."""
    (x1, y1), (x2, y2) = p1, p2
    xm, ym = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    ax = "x" if abs(x2 - x1) >= abs(y2 - y1) else "y"
    z0, z1 = (zb - 0.9, zb) if under else (zb, zb + 0.9)
    if ax == "x":
        sc.box([xm - 1.0, ym - 0.8, z0, xm + 1.0, ym + 0.8, z1], C["cap1206"], i=ref, g=g)
        sc.box([xm - 1.6, ym - 0.8, z0, xm - 1.0, ym + 0.8, z1], C["capend"], i=ref, g=g)
        sc.box([xm + 1.0, ym - 0.8, z0, xm + 1.6, ym + 0.8, z1], C["capend"], i=ref, g=g)
    else:
        sc.box([xm - 0.8, ym - 1.0, z0, xm + 0.8, ym + 1.0, z1], C["cap1206"], i=ref, g=g)
        sc.box([xm - 0.8, ym - 1.6, z0, xm + 0.8, ym - 1.0, z1], C["capend"], i=ref, g=g)
        sc.box([xm - 0.8, ym + 1.0, z0, xm + 0.8, ym + 1.6, z1], C["capend"], i=ref, g=g)


def spec_1206(sc, ref, b):
    """a 1206 from a CAD spec box (the box is the part + solder envelope): body + two end terminations along the long side."""
    x0, y0, z0, x1, y1, z1 = bx(b)
    if (y1 - y0) >= (x1 - x0):
        sc.box([x0, y0 + 0.5, z0, x1, y1 - 0.5, z1], C["cap1206"], i=ref)
        sc.box([x0, y0, z0, x1, y0 + 0.5, z1], C["capend"], i=ref)
        sc.box([x0, y1 - 0.5, z0, x1, y1, z1], C["capend"], i=ref)
    else:
        sc.box([x0 + 0.5, y0, z0, x1 - 0.5, y1, z1], C["cap1206"], i=ref)
        sc.box([x0, y0, z0, x0 + 0.5, y1, z1], C["capend"], i=ref)
        sc.box([x1 - 0.5, y0, z0, x1, y1, z1], C["capend"], i=ref)


def hall(sc, ref, item, xo, dx=0.0, net_out=None, nets=("+3V3", "GND"), q=None):
    """Hall sensor (WSH137 TO-92S, same body as the DRV5055 LPG) lying marked face up in its sensor-bar pocket, leads +x, bent down at the lead column xo through the bar and the
    board (CAD spec hall_* / el_hall_* boxes: body, lead band, down band)."""
    b0 = bx(item["boxes"][0])
    body = [b0[0] + dx, b0[1], b0[2], b0[3] + dx, b0[4], b0[5]]
    sc.box(body, C["hall"], i=ref, q=q)
    zl = (item["boxes"][1]["z"][0] + item["boxes"][1]["z"][1]) / 2.0
    zt = item["boxes"][2]["z"][0]
    bx1 = body[3]
    d = (xo + dx) - bx1
    for yb, yt in ((65.73, 64.46), (67.0, 67.0), (68.27, 69.54)):
        sc.tube([(bx1, yb, zl), (bx1 + 0.45 * d, yb, zl), (xo + dx - 0.05, yt, zl), (xo + dx, yt, zl - 0.5), (xo + dx, yt, zt)], 0.2,
                C["lead"], i=ref, g="part", q=q)


def strand(sc, pts, net, i, bare=False, r=None):
    """one underside wire: tinned bare (silver, thin) or an insulated strand (net colour)."""
    if bare:
        return sc.tube(pts, r or 0.26, C["tin"], i=i, g="wire", n=net, w="주석 맨선")
    return sc.tube(pts, r or 0.34, col(net), i=i, g="wire", n=net, w="피복 가닥")


def down_ends(poly, z_under, z_board):
    """a 2D underside route -> 3D: runs at z_under, rises into the board at both ends."""
    pts = [(poly[0][0], poly[0][1], z_board)] + [(x, y, z_under) for x, y in poly] + [(poly[-1][0], poly[-1][1], z_board)]
    return pts


# ====================================================================== octave module (SB + ribbon + MB), module-local x
NEAR = {0: 900.0, 1: 420.0, 2: 200.0}      # label level -> camera distance below which a module's labels show in the instrument scene


def module_objs(sc, SP, k=1, whole=False):
    """one octave module, board number k: sensor board SB + ribbon + control board MB + the ghost frame parts around them, in
    module-local x (the caller sets sc.dx / sc.m to place it). whole = inside the instrument scene: no cable stubs (the CAD cable
    lines follow), sensors named by the key they read on THIS module."""
    tag = "O%d" % k
    # ---------------------------------------------------------------- SB (z7.0~8.6)
    sc.bd = "SB"
    sbb = SP["sb_board"]["boxes"][0]
    zb0, zb1 = sbb["z"]
    y0, y1 = sbb["y"]
    outline = corner_u_outline(sbb["x"][0], sbb["x"][1], y0, y1, 3.0, 61.9, 74.6, 1.7)
    rows = SP["sb_board"]["hole_grid"]["y"]
    cols = [0.63 + 2.54 * i for i in range(1, 70) if sbb["x"][0] + 0.6 < 0.63 + 2.54 * i < sbb["x"][1] - 0.6]
    sc.board(outline, (zb0, zb1), lattice(cols, rows, lambda x, y: math.hypot(x - 3.0, y - 61.9) > 2.2 and math.hypot(x - 3.0, y - 74.6) > 2.2),
             C["perf"], "PCB-SB")
    board_info("PCB-SB", "센서 기판 SB (6행 양면 도트 띠 161.6 × 15.24 × 1.6)", [
        "모듈마다 1장 (×7). 건반 12개의 홀 센서 U201~U212 출력을 리본(J201)으로 제어 기판 MB에 보냅니다.",
        "줄: y61.92 예비 · 64.46 3V3 버스 · 67.00 GND 버스 · 69.54 OUT · 72.08 / 74.62 리본 J201.",
        "센서 바(출력물)가 기판 윗면을 덮어서 기판 부품은 모두 아랫면에 있습니다(1206). 센서는 바의 홈 안에 눕혀 리드를 아래로 꽂습니다.",
        "고정: 왼쪽 U홈 M3×10 ×2 (3.0, 61.9)·(3.0, 74.6), 앞·뒤 받침 리브 위 (W1 P36).", "도면 BRD-02, SCH-02"])
    sc.label(((sbb["x"][0] + sbb["x"][1]) / 2, y0 - 2.5, zb1), "SB 센서 기판", 0)
    # sensors
    keys = list(zip(S.KEYS, S.SENSOR_X))
    hall_ids = ["hall_C", "hall_Cs", "hall_D", "hall_Ds", "hall_E", "hall_F", "hall_Fs", "hall_G", "hall_Gs", "hall_A", "hall_As", "hall_B"]
    pads = B3.sb_pads()
    xo_of = {}
    for (xp, yp), (ref, pin, net) in pads.items():
        if ref.startswith("U2") and pin == "3":
            xo_of[ref] = xp
    for n_, ((key, xk), hid) in enumerate(zip(keys, hall_ids)):
        ref = "U%d" % (201 + n_)
        ch = SENS[n_]["먹스 채널"]
        nm, midi = [t.strip() for t in MUX_ROWS[ch][tag].split("=")]
        q = "%s의 %s 건반 = %s (MIDI %s) · 리본 %s번 심 → 먹스 %s" % (tag, key, nm, midi, SENS[n_]["리본 심"], ch) if whole else \
            "%s 건반 · 리본 %s번 심 → 먹스 %s" % (key, SENS[n_]["리본 심"], ch)
        hall(sc, ref, SP[hid], xo_of[ref], q=q)
        sc.label((xk, 67.0, SP[hid]["boxes"][0]["z"][1] + 1.0), "%s %s" % (ref, nm if whole else key), 2)
    # underside 1206s: C201..C212 under the sensor lead columns, C213 / C214 at the bus ends
    und = SP["sb_underside"]["boxes"]
    for n_ in range(12):
        spec_1206(sc, "C%d" % (201 + n_), und[n_])
    spec_1206(sc, "C213", und[12])
    spec_1206(sc, "C214", und[13])
    # pads (solder on the underside; J201 = ribbon strands soldered from below)
    for (xp, yp), (ref, pin, net) in pads.items():
        sc.pad(xp, yp, (zb0, zb1), net, "%s.%s" % (ref, pin), "b")
    # bare buses + 16 strands (wiring_SB.csv)
    zu = zb0 - 0.32
    for net, poly in B3.SB_BUS.items():
        strand(sc, [(x, y, zu + 0.05) for x, y in poly], net, "BUS-SB-" + net, bare=True)
    info("BUS-SB-+3V3", "SB 3V3 버스 (주석 맨선)", ["아랫면 y64.46을 따라 x8.25 → 160.65, 지나는 센서 VCC 패드마다 납땜.", "도면 BRD-02"])
    info("BUS-SB-GND", "SB GND 버스 (주석 맨선)", ["아랫면 y67.00을 따라 x8.25 → 160.65, 지나는 센서 GND 패드마다 납땜.", "도면 BRD-02"])
    for n_, r in enumerate(read_csv("wiring_SB.csv")):
        poly = parse_path(r["경로 (모듈 좌표 x, y)"])
        lane = [(x, y + ((n_ - 5.5) * 0.12 if abs(y - 70.81) < 0.01 else 0.0)) for x, y in poly]
        wid = "SBW-%d" % (n_ + 1)
        strand(sc, down_ends(lane, zu - 0.05 - 0.04 * (n_ % 3), zb0), r["넷"], wid)
        info(wid, "SB 아랫면 선: %s%s → %s" % (r["선 (센서 OUT / 버스)"], " OUT" if r["선 (센서 OUT / 버스)"].startswith("U") else "", r["J201 핀"]),
             ["넷 %s · 길이 %s mm · %s" % (r["넷"], r["길이 (mm)"], r["줄"]),
              "선: EUNSUNG 2651-16P 리본에서 가른 1가닥 (구매 %s · %s)" % (HT.STRAND[0], HT.STRAND[2]),
              "꺾인 점 (모듈 좌표): " + r["경로 (모듈 좌표 x, y)"], "wiring_SB.csv · 도면 BRD-02"])
    # support ribs + sensor bar (context)
    for (a0, a1, b0, b1) in B3.SB_RIBS:
        sc.box([a0, b0, 5.0, a1, b1, zb0], C["ctx"], i="CTX-RIB", g="ctx", o=0.35)
    info("CTX-RIB", "SB 받침 리브 (프레임, W1 P36)", ["윗면 z7.0 = 기판 밑면. 뒤 리브는 x59~82(리본 틈)만 열려 있어 아랫면 선은 그 안에서만 뒤 띠를 지납니다."])
    sc.box([0.5, 59.0, zb1, 162.9, 77.5, 13.6], C["bar"], i="CTX-BAR", g="ctx", o=0.12)
    info("CTX-BAR", "센서 바 (출력물, 윤곽만)", ["기판 윗면을 덮는 출력물. 센서는 바의 홈(백건 z12.19 · 흑건 z9.66)에 눕혀 넣고 리드를 바 구멍 Ø0.9와 기판에 꽂습니다.",
                                           "여기서는 바깥 윤곽 상자만 흐리게 보입니다 (홈·턱 모양은 04 3D 모델)."])
    # ---------------------------------------------------------------- ribbon W101 (flat on the floor) + strands into J201 / J301
    rb = SP["ribbon"]["boxes"]
    xr0, xr1 = rb[1]["x"]
    x0_, y0_, z0_, x1_, y1_, z1_ = bx(rb[1])                     # flat on the floor, through the front-rib gap to the board edge
    sc.box([x0_, y0_, z0_, x1_, y1_, z1_], C["ribbon"], i="W101~W107", g="cable")
    sc.box([x0_, y0_, z1_, x0_ + 0.9, y1_, z1_ + 0.02], C["ribbon_red"], i="W101~W107", g="cable")
    zf = rb[1]["z"][1] - 0.45
    yf = rb[1]["y"][1]                                           # y96.0: the last ~6 mm are split into strands
    zb_mb = SP["mb_board"]["boxes"][0]["z"][0]
    zt_mb = SP["mb_board"]["boxes"][0]["z"][1]
    for n in range(1, 17):
        cx = xr0 + 0.635 + 1.27 * (n - 1)
        net = S.RIBBON[n - 1]
        colr = C["ribbon"] if n > 1 else C["ribbon_red"]
        q = "%d번 심 · SB J201 %d번 → MB J301 %d번" % (n, n, n)
        # SB end: J201 pad (from below) -> folds down through the rib gap to the flat ribbon at y77.5
        px, py = 61.59 + 2.54 * ((n - 1) // 2), (72.08 if n % 2 else 74.62)
        sc.tube([(px, py, zb0), (px, py, zb0 - 0.7), (cx, 76.0, zf + 0.6), (cx, 77.5, zf)], 0.22, colr, i="W101~W107", g="cable", n=net, q=q)
        # MB end: split strands shifted -0.93 (J301 centre x69.55), into the J301 holes from below, soldered on the top (<= z10.0);
        # back-row strands pass between the front-row pads (half-pitch lanes x + 1.27)
        qx, qy = S.mb_pad_xy("J301", n)
        if n % 2:
            pts = [(cx, yf, zf), (cx - 0.93, yf + 1.0, zf), (qx, qy - 1.0, 5.6), (qx, qy, zb_mb), (qx, qy, zt_mb + 0.9)]
        else:
            pts = [(cx, yf, zf), (cx - 0.93, yf + 1.0, zf), (qx + 1.27, qy - 3.2, 5.6), (qx + 1.27, qy - 1.3, 5.75), (qx, qy, zb_mb),
                   (qx, qy, zt_mb + 0.9)]
        sc.tube(pts, 0.22, colr, i="W101~W107", g="cable", n=net, q=q)
    sc.label((70.48, 86.0, 6.5), "리본 W10%d (16심)" % k, 1 if whole else 0)
    # ---------------------------------------------------------------- MB (whole 80 x 120 board on the floor ribs, z7.0~8.6)
    mb_scene_parts(sc, SP, k, whole)
    # ---------------------------------------------------------------- frame context (CAD A16): rail on the strip, fins, floor ribs
    rx0, rx1, ry0, ry1, rz0, rz1 = S.MB["rail"]
    sc.box([rx0, ry0, rz0, rx1, ry1, rz1], C["frame"], i="CTX-RAIL", g="ctx", o=0.30)
    sc.label(((rx0 + rx1) / 2, (ry0 + ry1) / 2, rz1 + 0.5), "밸런스 레일 (따로 출력)", 1)
    info("CTX-RAIL", "밸런스 레일 (따로 출력한 출력물, 윤곽만) — MB 맨 띠 위", [
        "x%.2f~%.2f × y%.1f~%.1f × z%.1f~%.1f: 밑면 z%.1f = 기판 윗면. 기판의 맨 띠(y132.0~144.8, 줄 j 14~19 — 부품·패드·윗면 선 없음)에 얹혀 기판을 눌러 잡습니다."
        % (rx0, rx1, ry0, ry1, rz0, rz1, rz0),
        "M3×6 2개는 레일 양 끝(x11.2 / 154.2, 기판 밖)에서 위로부터 조입니다 — 기판에는 나사·구멍이 없습니다.",
        "레일 윗면·밸런스 핀 자리는 그대로이고 건반 동작은 바뀌지 않습니다 (CAD keyaction.py A16).",
        "출처: CAD A16 · spec/electronics_modules.json mb_board"])
    fy0, fy1 = S.MB["fin_y"]
    for (a0, a1) in S.MB["fins"]:
        sc.box([a0, fy0, S.MB["fin_z"], a1, fy1, 30.0], C["frame"], i="CTX-FIN", g="ctx", o=0.35)
    info("CTX-FIN", "프레임 핀 2 · 4 (레버틀 세로판, 아랫부분만)", [
        "x40.76~42.56 · x123.03~124.83: 기판 뒤 구역 위(y%.1f~%.1f)에서 밑변 z%.1f — 그 밑 기판 윗면 열 i 4·5 · 36·37에는 부품이 없습니다 (아랫면 선은 됨)."
        % (fy0, fy1, S.MB["fin_z"]),
        "y%.1f 뒤로는 다시 바닥에 섭니다. 위쪽(레버틀)은 생략." % fy1, "출처: CAD keyaction.py A16 (a16_cage_cuts)"])
    fa, fb, fc, fd, fz = S.MB["ffs"]
    sc.box([fa, fc, fz, fb, fd, 30.0], C["frame"], i="CTX-FFS", g="ctx", o=0.35)
    sc.label(((fa + fb) / 2, 186.0, 30.5), "F|F# 핀 (밑변 z%.1f)" % fz, 1)
    info("CTX-FFS", "F|F# 핀 (프레임 세로판, 아랫부분만) — 제로·USB 플러그 위", [
        "x%.2f~%.2f × y%.1f~%.1f: 밑변 z%.1f로 제로(윗면 부품 ≤ z%.1f)와 USB 플러그 몰드(≤ z%.1f) 위를 지나 뒷벽까지 갑니다."
        % (fa, fb, fc, fd, fz, SP["zero"]["boxes"][2]["z"][1], SP["usb_plug"]["boxes"][0]["z"][1]),
        "이전(W1 r4.5)에는 기판 앞 홈으로 바닥까지 내려와 킬로 레일에 붙었습니다 — A16에서 레일을 따로 출력하고 기판을 바닥에 놓으면서 들어 올림.",
        "출처: CAD keyaction.py A16 (ffs)"])
    for (a0, a1, b0, b1) in S.MB["ribs"]:
        sc.box([a0, b0, 5.0, a1, b1, zb_mb], C["ctx"], i="CTX-MBRIB", g="ctx", o=0.45)
    info("CTX-MBRIB", "MB 받침 리브 (모듈 바닥틀, z%.1f~%.1f)" % (S.MB["floor"], zb_mb), [
        "기판 밑면(z%.1f)을 받침. 앞 리브(리본 틈 x59.5~81.5), 뒤 리브, 옆 리브 2, 레일 밑 띠 리브(틈 x92.0~114.0 하나)." % zb_mb,
        "리브 위에는 납땜·아랫면 선이 없습니다. 앞 구역 ↔ 뒤 구역 선 %d가닥은 띠 리브 틈으로만 지납니다 (BRD-08)." % MR.stats()["gap"],
        "기판 밑은 바닥(z%.1f)까지 %.1f — 다리·핀 끝 ≤ 1.0, 선은 리본 가닥(약 0.9, 두 가닥이 직각으로 겹쳐도 1.8)." % (S.MB["floor"], zb_mb - S.MB["floor"]),
        "출처: CAD keyaction.py A16 (a16_bed)"])
    sc.bd = None


def scene_module(SP, BOM):
    sc = Scene("module", "옥타브 모듈 (O1 기준): 센서 기판 SB → 리본 → 제어 기판 MB",
               "모듈 로컬 좌표 (세계 x = 47 + 164.5 × (k − 1) + x). 7개 모듈이 같은 기판이고 ID 점퍼·EXT만 다릅니다 — 모듈마다 다른 점은 '악기 전체 배선' 장면에 그대로 있습니다.", "module",
               "옥타브 모듈 SB·MB")
    module_objs(sc, SP, 1)
    sc.view("모듈 전체", [0, 58, 4, 165, 212, 30], az=-28, el=42, default=True)
    sc.view("SB 확대", [0, 58, 4, 165, 80, 15], az=-20, el=48)
    sc.view("SB 아랫면", [0, 58, 4, 165, 80, 15], az=-20, el=-52)
    sc.view("MB 확대", [20, 90, 4, 145, 178, 20], az=-30, el=45)
    sc.view("MB 아랫면", [20, 90, 4, 145, 178, 20], az=-30, el=-55)
    sc.view("MB 위", [20, 90, 4, 145, 178, 20], az=0, el=89)
    sc.view("레일 · 핀 (주변)", [20, 88, 2, 145, 212, 32], az=-22, el=26)
    sc.note("ID 점퍼는 O1 = JP301 닫음, R301~R303 100 kΩ와 J302 EXT는 O1·O7에만 (O7은 R301만). 다른 모듈은 같은 자리를 비웁니다.")
    sc.note("센서 바·받침 리브·밸런스 레일·프레임 핀은 위치만 흐리게(주변 출력물). 센서가 기판보다 떠 있는 것은 바의 홈 안에 눕혀 있기 때문입니다.")
    sc.note("MB는 80 × 120 한 장을 통째로 모듈 바닥 자리에 놓고, 따로 출력한 밸런스 레일이 맨 띠를 눌러 잡습니다(△33) — 레일·핀을 누르면 이유가 나옵니다. "
            "'주변 출력물'을 끄면 숨겨집니다.")
    return sc


def mb_scene_parts(sc, SP, k=1, whole=False):
    """the control board MB of module k as that board is built (boards4.KINDS: O1 = R301~R303 + EXT lead W403 5 strands, O7 = R301 +
    W413 3 strands, O2~O6 = neither; ID jumpers by the board number): board, Zero, mux, headers, J301 / J302 pads, R30x, JP, TP, C301,
    USB plug, EXT lead, underside wiring (△33: the whole 80 x 120 board on the module floor). Wires and pads a kind does not use are
    drawn faint / without solder. Click texts = the drawings' (kind_texts)."""
    kind = kind_of(k)
    V = B4.KINDS[kind]
    var, leads = kind_texts(kind)
    start = len(sc.d["objs"])
    sc.bd = "MB"
    rt, wires, _probs = MR.get()
    ends = {}
    for w in wires:
        for e in (w["a"], w["b"]):
            ends.setdefault(e, []).append(w)
    mbb = SP["mb_board"]["boxes"]
    z0, z1 = mbb[0]["z"]
    outline = rect(S.MB["x0"], S.MB["y0"], S.MB["x1"], S.MB["y1"])
    sc.board(outline, (z0, z1), [], C["perf"], "PCB-MB",
             grid=(S.lat(0), S.lat(1) - S.lat(0), S.LAT_N[0], S.latj(0), S.latj(1) - S.latj(0), S.LAT_N[1]))
    board_info("PCB-MB", "제어 기판 MB (양면 만능기판 80 × 120 × 1.6 통째로)", [
        "모듈마다 1장 (×7). RP2040-Zero가 먹스로 센서 12개(끝 기판은 끝 부속 센서까지)를 차례로 읽어 USB로 Pi에 보냅니다.",
        "자르지 않고 구멍도 뚫지 않습니다 — 모듈 바닥 자리(받침 리브 z%g~%g, 가장자리 턱)에 놓고 따로 출력한 밸런스 레일이 맨 띠(y132.0~144.8)를 눌러 잡습니다 (△33)."
        % (S.MB["floor"], z0),
        "외곽 x%.2f~%.2f × y%.1f~%.1f. 격자 x = 30.18 + 2.54 i, y = 96.47 + 2.54 j (BE163 30 × 42 구멍, 가운데 가정) — 부품은 i 1~40 · j 1~28만이라 28 × 40 구멍 판도 같은 배치."
        % (S.MB["x0"], S.MB["x1"], S.MB["y0"], S.MB["y1"]),
        "앞 구역(J301·먹스) 부품 ≤ z17.27, 뒤 구역(제로·J302·R30x·JP·TP) ≤ z20.9. 아랫면은 바닥까지 %.1f — 다리 끝 ≤ 1.0, 선은 리본 가닥(겹쳐도 1.8)."
        % (z0 - S.MB["floor"]),
        "도면 BRD-01 (윗면), BRD-08 (아랫면 배선), BRD-09~11 (기판 종류별), SCH-03"])
    sc.label((82.25, 91.0, z1), "MB 제어 기판", 0)
    pads, _nets = MR.pads_and_nets()
    # ---- Zero A301 on standard headers with the 2.5 mold (PCB z11.1~12.1)
    zb = SP["zero"]["boxes"]
    sc.box(bx(zb[0]), C["pcb_blue"], i="A301")
    sc.box(bx(zb[1]), C["chip"], i="A301", o=0.8)
    sc.box(bx(zb[2]), C["pcb_blue"], i="A301", o=0.18)
    sc.box(bx(zb[3]), C["shell"], i="A301")
    zt = zb[0]["z"][1]
    cx, cy = (zb[2]["x"][0] + zb[2]["x"][1]) / 2.0, (zb[2]["y"][0] + zb[2]["y"][1]) / 2.0 - 1.5
    sc.box([cx - 3.5, cy - 3.5, zt, cx + 3.5, cy + 3.5, zt + 0.9], C["chip"], i="A301-CHIP")
    info("A301-CHIP", "RP2040 칩 (자리 어림)", ["제로 윗면 부품(RP2040·플래시·BOOT/RESET·LED)은 높이 한계 z%.1f 상자(흐린 파랑) 안에 있습니다. 칩 자리는 어림입니다."
                                             % zb[2]["z"][1]])
    for xc in (S.zero_hole(1)[0], S.zero_hole(10)[0]):             # 1x9 header molds (2.5) under the Zero
        sc.box([xc - 1.27, S.zero_hole(9)[1] - 1.27, z1, xc + 1.27, S.zero_hole(1)[1] + 1.27, zb[0]["z"][0]], C["header"], i="A301-HDR")
    info("A301-HDR", "제로 핀 헤더 1×9 ×2 (몰드 2.5 그대로)", ["몰드 z%.1f~%.1f이 제로를 받칩니다(밑면 칩과 기판 사이 %.1f). 꼬리는 기판 밑 1.0 이하로 자릅니다."
                                                        % (z1, zb[0]["z"][0], zb[1]["z"][0] - z1),
                                                        "구매 목록 SE7 (bom.csv A301-HDR)"])
    sc.label((83.5, 158.0, 15.6), "A301 RP2040-Zero", 1)
    # ---- mux A302 (header spacers, module PCB, chip)
    mx = SP["mux"]["boxes"]
    sc.box(bx(mx[0]), C["header"], i="A302")
    sc.box(bx(mx[1]), C["header"], i="A302")
    sc.box(bx(mx[2]), C["pcb_green"], i="A302")
    sc.box(bx(mx[3]), C["chip"], i="A302")
    sc.label((102.6, 109.2, 14.8), "A302 4067 먹스", 1)
    # ---- pins of the two modules, pads, other parts
    zpin = (z0 - S.MB["tails"], SP["zero_headers"]["boxes"][0]["z"][1])
    for (i_, j_), (ref, num, net) in sorted(pads.items()):
        x, y = MR.X(i_), MR.Y(j_)
        nn = None if net == "NC" else net
        pid = "%s.%s" % (ref, num)
        sol = B4.pad_state(V, ref, num, net, ends) == "sol"
        if ref == "A301":
            if int(num) <= 18:
                sc.box([x - 0.32, y - 0.32, zpin[0], x + 0.32, y + 0.32, zpin[1]], C["pin"], i=pid, n=nn)
            sc.pad(x, y, (z0, z1), nn, pid, "b" if int(num) <= 18 else "")
        elif ref == "A302":
            sc.box([x - 0.32, y - 0.32, zpin[0], x + 0.32, y + 0.32, zpin[1]], C["pin"], i=pid, n=nn)
            sc.pad(x, y, (z0, z1), nn, pid, "b")
        elif ref == "J301":
            sc.pad(x, y, (z0, z1), nn, pid, "bt")                 # strands soldered on the top, board wires below
        elif ref == "J302":                                       # the EXT lead is soldered on the top of the pads this kind uses
            sc.pad(x, y, (z0, z1), nn, pid, ("bt" if int(num) in V["ext"] else "b") if sol else "")
        elif ref.startswith("TP"):
            sc.pad(x, y, (z0, z1), nn, pid, "bt")
            sc.add(k="c", a="x", p=[r2(y), r2(z1 + 1.6)], r=1.1, s=[r2(x - 0.25), r2(x + 0.25)], c=C["tin"], i=pid, g="part", n=nn, ring=1)
        else:                                                     # R30x, JP30x: soldered where this kind has a part or a wire joint
            sc.pad(x, y, (z0, z1), nn, pid, "b" if sol else "")
    # EXT pull-downs this kind carries (O1: R301~R303, O7: R301; R304 on no board)
    for ref, (x, y) in S.R_EXT.items():
        if ref in V["r"]:
            resistor(sc, ref, (x, y), (x + 7.62, y), z1, "100k", zb=z0)
    # ID jumpers: bit n of the board number = JP30(n+1) closed (solder bridge on the underside)
    for ref, (sig, gnd) in S.JP_PADS.items():
        if ref in B4.jp_closed(k):
            xa, xb_ = sorted((sig[0], gnd[0]))
            sc.box([xa - 0.4, sig[1] - 0.55, z0 - 0.55, xb_ + 0.4, sig[1] + 0.55, z0], C["solder"], i=ref)
    # C301 1206 across the mux GND / VCC header tails (underside, flat against the board)
    g_, v_ = S.mux_hole("GND"), S.mux_hole("VCC")
    chip1206(sc, "C301", (g_[0], g_[1]), (v_[0], v_[1]), z0)
    # USB plug (+ a cable stub straight +y out of the rear-wall opening when the CAD cable line is not drawn)
    up = SP["usb_plug"]["boxes"][0]
    ucx, ucz = (up["x"][0] + up["x"][1]) / 2.0, (up["z"][0] + up["z"][1]) / 2.0
    usb = "W20%d" % k
    sc.box(bx(SP["usb_plug_shell"]["boxes"][0]), C["shell"], i=usb)
    sc.box(bx(up), C["usb"], i=usb, g="cable")
    if not whole:
        sc.cyl("y", (ucx, ucz), 1.75, (up["y"][1], 214.0), C["cable"], i=usb, g="cable")
    sc.label((ucx, 203.0, 19.0), "%s USB → 허브" % usb, 1)
    # EXT lead (O1 five strands, O7 three): soldered into J302 from the top, flat to the rear edge, over the rear lip (z8.5) to the
    # floor, -x behind the board, then +y under the USB plug (z9.9) out of the rear-wall opening (spec ext_lead)
    if V["lead"]:
        for n_, n in enumerate(sorted(V["ext"])):
            lid = "%s-%d" % (V["lead"], n_ + 1)
            ovr(lid, leads[n_]["t"], [_fix(x) for x in leads[n_]["d"]])
            sc.tube(ext_lead_route(n) + [(84.6 + 0.55 * (n - 1), 214.0, 5.4)], 0.27, "#7e889a", i=lid, g="cable",
                    n=pin_net("MB", "J302", n) or "")
    # underside wiring (BRD-08 / wiring_MB.csv): single 2651 ribbon strands (OD ~0.9), joins only at pads
    zu = z0 - 0.47
    for n_, w in enumerate(wires):
        o = strand(sc, down_ends(list(w["pts"]), zu - 0.04 * (n_ % 3), z0), w["net"], "MBW-%d" % w["no"], r=0.42)
        if o is not None and not B4.wire_used(V, w):
            o["o"], o["w"] = 0.3, "피복 가닥 — 이 기판에서는 쓰지 않아 흐리게 그림"
    for o in sc.d["objs"][start:]:
        if o.get("i") in var:
            o["v"] = kind
    sc.bd = None


def ext_lead_route(n):
    """module part of EXT lead conductor n (J302 pin n, module-local): top joint -> flat over the board -> over the rear edge and the rear
    lip (y173.6~174.6, top z8.5) -> down behind it to the floor -> -x behind the board -> +y under the USB plug to the rear-wall opening
    y212 (spec ext_lead boxes)."""
    z1, zl, yb1 = S.MB["zt"], S.MB["lips"][0], S.MB["y1"]
    x = S.EXT_X0 + 2.54 * (n - 1)
    xe = 84.6 + 0.55 * (n - 1)
    ye = 176.4 + 0.45 * (n - 1)
    return [(x, S.EXT_Y, z1 + 0.3), (x, S.EXT_Y + 0.6, z1 + 0.65), (x, yb1 - 0.4, z1 + 0.65), (x, 174.9, zl + 0.6), (x, 175.3, 6.2),
            (x, ye - 0.6, 5.5), (x - 0.6, ye, 5.4), (xe + 0.6, ye, 5.4), (xe, ye + 0.6, 5.4), (xe, 212.0, 5.4)]


def ext_lead_lengths():
    """(min, max) path of the six EXT conductors for O1 / O7: ext_lead_route + the duct-floor run of cad/src/electronics.py ext_floor_path
    (read-only copy of its numbers: bundle at module x86.5, y212 z6.5 -> y213.5 -> y217 z1.5 -> +-8 x, y226 -> XH plug end face at
    x69.4 + 1.5 (O1) / 1160 - 1.5 (O7), y231)."""
    def plen(p):
        return sum(math.dist(a, b) for a, b in zip(p, p[1:]))
    out = {}
    for tag, k, sgn, xh in (("O1", 1, -1, 69.4 + 1.5), ("O7", 7, 1, 1160.0 - 1.5)):
        X0 = X_O1 + MODULE_W * (k - 1)
        x = X0 + 86.5
        duct = [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, 1.5), (x + sgn * 8.0, 226.0, 1.5), (xh, 231.0, 1.5)]
        ls = []
        for n in range(1, 7):
            m = ext_lead_route(n)
            ls.append(plen(m) + math.dist(m[-1], (86.5, 212.0, 6.5)) + plen(duct))
        out[tag] = (round(min(ls), 1), round(max(ls), 1))
    return out


def shift(b, dx):
    return [b[0] + dx, b[1], b[2], b[3] + dx, b[4], b[5]]


# ====================================================================== end parts EL / ER
def end_objs(sc, SP, tag, whole=False):
    """one end-part sensor board (EL / ER) in end-part local x (the caller sets sc.dx / sc.m). whole = inside the instrument scene:
    the lead goes on along the CAD lane instead of being cut at y96."""
    Bd = S.END_BOARDS[tag]
    mod = "O1" if tag == "EL" else "O7"
    sc.bd = tag
    it = SP["el_board" if tag == "EL" else "er_board"]["boxes"][0]
    zb0, zb1 = it["z"]
    y0, y1 = it["y"]
    outline = corner_u_outline(it["x"][0], it["x"][1], y0, y1, 3.0, 61.9, 74.6, 1.7)
    cols = [0.63 + 2.54 * i for i in range(1, 20) if 1.0 + 0.6 < 0.63 + 2.54 * i < Bd["x1"] - 0.6]
    rows = [61.92, 64.46, 67.00, 69.54, 72.08, 74.62]
    sc.board(outline, (zb0, zb1),
             lattice(cols, rows, lambda x, y: math.hypot(x - 3.0, y - 61.9) > 2.2 and math.hypot(x - 3.0, y - 74.6) > 2.2), C["perf"], "PCB-" + tag)
    board_info("PCB-" + tag, "%s 센서 기판 (6행 띠 %s × 15.24)" % (tag, "45.5" if tag == "EL" else "22.0"), [
        "끝 건반(%s) 센서 기판: 옥타브 모듈에 들지 않는 %s 끝 건반의 홀 센서를 달고, 리드선으로 %s 제어 기판에 보냅니다."
        % (" · ".join(k_[1] for k_ in Bd["keys"]), "왼쪽" if tag == "EL" else "오른쪽", mod),
        "끝 부속 센서 바 안 (EL x1.0~46.5, ER 로컬 x1.0~23.0). 줄은 SB와 같음.",
        "센서 바가 윗면을 덮어 100 nF · 1 kΩ · 10 µF 모두 1206 아랫면 (△13).", "리드 %s → 뒤 통로 XH (SCH-04 주 6)" % ("W401 5심" if tag == "EL" else "W411 3심"),
        "도면 BRD-02 (끝 부속 칸), SCH-04"])
    sc.label((it["x"][0] + 4, y0 - 2.5, zb1), "%s 기판" % tag, 0)
    sc.box([Bd["bar"][0], 59.0, zb1, Bd["bar"][1], 77.5, 13.6], C["bar"], i="CTX-BAR-END", g="ctx", o=0.12)
    jx = Bd["jx"]
    hall_items = ["el_hall_A0", "el_hall_As0", "el_hall_B0"] if tag == "EL" else ["er_hall_C8"]
    last = max(S.end_col(k_[2]) for k_ in Bd["keys"])
    for n_, ((u, key, xk, cref, rref), hid) in enumerate(zip(Bd["keys"], hall_items)):
        colx = S.end_col(xk)
        midi = MUX_ROWS["C%d" % (12 + n_)][mod].split("= ")[-1]
        hall(sc, u, SP[hid], colx, q="%s 건반 (MIDI %s) → %s 1 kΩ → %s 제어 기판 EXT%d · 먹스 C%d" % (key, midi, rref, mod, n_ + 1, 12 + n_))
        sc.label((xk, 67.0, SP[hid]["boxes"][0]["z"][1] + 1.0), "%s %s" % (u, key), 2)
        for y, pin in ((64.46, "1"), (67.00, "2"), (69.54, "3")):
            sc.pad(colx, y, (zb0, zb1), pin_net(tag, u, pin), "%s.%s" % (u, pin), "b")
        sc.pad(colx, 72.08, (zb0, zb1), pin_net(tag, rref, "1"), "%s.1" % rref, "b")
        chip1206(sc, cref, (colx, 64.46), (colx, 67.00), zb0)
        chip1206(sc, rref, (colx, 69.54), (colx, 72.08), zb0)
    chip1206(sc, Bd["bulk"], (8.25, 64.46), (8.25, 67.00), zb0)
    for y, pin in ((64.46, "1"), (67.00, "2")):
        sc.pad(8.25, y, (zb0, zb1), pin_net(tag, Bd["bulk"], pin), "%s.%s" % (Bd["bulk"], pin), "b")
    zu = zb0 - 0.32
    rail = "+3V3_EL" if tag == "EL" else "+3V3_ER"
    strand(sc, [(8.25, 64.46, zu), (last, 64.46, zu)], rail, "BUS-%s-3V3" % tag, bare=True)
    strand(sc, [(8.25, 67.00, zu), (last, 67.00, zu)], "GND", "BUS-%s-GND" % tag, bare=True)
    info("BUS-%s-3V3" % tag, "%s 3V3 버스 (주석 맨선)" % tag, ["아랫면 y64.46, x8.25 → %.2f" % last, "도면 BRD-02 (끝 부속 칸)"])
    info("BUS-%s-GND" % tag, "%s GND 버스 (주석 맨선)" % tag, ["아랫면 y67.00, x8.25 → %.2f" % last, "도면 BRD-02 (끝 부속 칸)"])
    for n, x in enumerate(jx, 1):
        sc.pad(x, 74.62, (zb0, zb1), pin_net(tag, Bd["jref"], n), "%s.%d" % (Bd["jref"], n), "b")
    wires = [((jx[0], 67.00), (jx[0], 74.62), "GND", "GND 버스 → %s.1" % Bd["jref"]),
             ((jx[-1], 64.46), (jx[-1], 74.62), rail, "3V3 버스 → %s.%d" % (Bd["jref"], len(jx)))]
    for n_, (u, key, xk, cref, rref) in enumerate(Bd["keys"]):
        wires.append(((S.end_col(xk), 72.08), (jx[1 + n_], 74.62), pin_net(tag, rref, "1"), "%s (%s 건반) → %s.%d" % (rref, key, Bd["jref"], n_ + 2)))
    for n_, (a, b_, net, nm) in enumerate(wires):
        wid = "%sW-%d" % (tag, n_ + 1)
        strand(sc, down_ends([(a[0], a[1]), (b_[0], b_[1])], zu - 0.1, zb0), net, wid)
        info(wid, "%s 아랫면 선: %s" % (tag, nm),
             ["넷 %s · 피복 단선, 점 대 점" % net, "선: EUNSUNG 2651-16P 리본에서 가른 1가닥 (구매 %s · %s)" % (HT.STRAND[0], HT.STRAND[2]), "도면 BRD-02 (끝 부속 칸)"])
    # lead strands: down from the J pads inside the rear-rib gap, gathered, flat on the floor toward the rear wall
    gx0 = 14.825 if tag == "EL" else 8.885
    wid = "W401" if tag == "EL" else "W411"
    xh = "X401" if tag == "EL" else "X411"
    for n, x in enumerate(jx, 1):
        g = gx0 + 0.635 + 1.27 * (n - 1)
        net = pin_net(tag, Bd["jref"], n)
        pts = [(x, 74.62, zb0), (x, 74.62, zb0 - 1.0), (x, 75.6, 6.0), (g, 77.39, 5.45)] + ([] if whole else [(g, 96.0, 5.45)])
        sc.tube(pts, 0.24, C["ribbon"] if n > 1 else C["ribbon_red"], i=wid, g="cable", n=net,
                q="%d번 가닥 · %s %d번 → %s %d번" % (n, Bd["jref"], n, xh, n))
    if whole:                                                      # the rest of the lead: CAD lane under the balance rail to the rear wall
        sc.box(bx(SP["el_lead" if tag == "EL" else "er_lead"]["boxes"][2]), C["ribbon"], i=wid, g="cable")
    sc.label((gx0 + 3.0, 92.0, 6.5), "%s → 뒤 통로 XH" % wid, 1)
    for (a0, a1, b0, b1) in ([(6.0, Bd["gap"][0], 73.2, 75.5), (Bd["gap"][1], Bd["x1"], 73.2, 75.5), (6.0, Bd["x1"] - 0.5, 61.0, 62.8)]):
        if a1 > a0:
            sc.box([a0, b0, 5.0, a1, b1, zb0], C["ctx"], i="CTX-RIB", g="ctx", o=0.35)
    info("CTX-BAR-END", "끝 부속 센서 바 (출력물, 윤곽만)", ["EL 바 x0.5~46.5 (A#0 낮은 구간 x19.93~33.93), ER 바 로컬 x0.5~23.0. 센서는 바의 홈에 눕혀 있습니다."])
    sc.bd = None


def scene_end(SP):
    sc = Scene("end", "끝 부속 센서 기판 EL (A0 · A#0 · B0) · ER (C8)",
               "끝 부속 로컬 좌표. ER은 보기 위해 EL 오른쪽에 옮겨 둠 (실제로는 악기 오른쪽 끝, 세계 x = 1198.5 + x).", "end", "끝 부속 EL·ER")
    sc.d["scopes"] = {}
    for tag, dx in (("EL", 0.0), ("ER", ER_SHOW_DX)):
        sc.dx, sc.m = dx, tag
        end_objs(sc, SP, tag)
        sc.d["scopes"][tag] = scope_end(tag)
    sc.dx, sc.m = 0.0, None
    sc.view("EL · ER", [0, 58, 4, 85, 98, 15], az=-25, el=45, default=True)
    sc.view("아랫면", [0, 58, 4, 85, 80, 15], az=-25, el=-55)
    sc.view("EL 확대", [0, 58, 4, 48, 80, 15], az=-25, el=45)
    sc.view("ER 확대", [ER_SHOW_DX, 58, 4, ER_SHOW_DX + 24, 80, 15], az=-25, el=45)
    sc.note("10 µF C404 · C412 자리(x8.25)는 C412가 CAD 사양에서 '어림'입니다. 리드는 y96에서 자름 (실제로는 레일 밑 차선 → 뒷벽 홈 → 뒤 통로 XH — '악기 전체 배선' 장면에 이어져 있습니다).")
    return sc


# ====================================================================== pedal: PB + J501 scrap + PS
def scene_pedal():
    sc = Scene("pedal", "페달: PED 보드 PB + J501 잭 조각 + 페달 안 센서 PS",
               "가운데 유닛 세계 좌표 (PB x426.5~476.5 · y244~314). PS는 페달 안에 있어 보기 위해 PB 옆에 둠.", "world", "페달 PB·J501·PS")
    sc.m, sc.bd = "PED", "PB"
    z0, z1 = B2.PB_Z
    bx0, bx1, by0, by1 = B2.PB_BOX
    holes = lattice([B2.pb_x(j) for j in range(20)], [B2.pb_y(i) for i in range(28)],
                    lambda x, y: min(math.hypot(x - a, y - b) for a, b, _, _ in B2.PB_HOLES) > 2.2)
    sc.board(rect(bx0, by0, bx1, by1), (z0, z1), holes, C["perf"], "PCB-PB", mholes=[(a, b, d) for a, b, d, _ in B2.PB_HOLES])
    board_info("PCB-PB", "PED 페달 보드 PB (8 × 12 양면 기판에서 자른 70 × 50)", [
        "페달(서스테인, MIDI CC64) 보드: 페달 안 홀 센서 PS의 전압을 A501 RP2040-Zero가 ADC로 읽어 USB 선 W208로 Pi에 보냅니다.",
        "가운데 유닛 바닥 5 mm 기둥 위 (z21.5~23.1). 격자 x = 475.23 − 2.54 j, y = 245.27 + 2.54 i (지그 P-PED).",
        "A501 RP2040-Zero (180° 돌림, USB-C −y) · R501 1 kΩ · R502 100 kΩ · R503 100 Ω × 5 = 20 Ω · C501 100 nF · JP504 닫음.",
        "도면 BRD-03, SCH-05"])
    sc.label((bx0 + 4, by0 - 3.0, z1), "PB 페달 보드", 0)
    pads = read_csv("pads_PB.csv")
    pp = {}
    for r in pads:
        pp.setdefault(r["부품"], {})[r["핀"]] = (float(r["x"]), float(r["y"]), r["넷"])
    # A501 Zero: CAD box snapped to the lattice (BRD-03 △22), 180 deg (USB-C toward -y), pin headers 1.3 gap
    zx0 = 449.0 + B2.ZERO_SNAP[0]
    zy_r = 244.0 + B2.ZERO_SNAP[1]                     # receptacle face
    zp0 = z1 + 1.3
    sc.box([zx0, zy_r + 1.3, zp0, zx0 + 18.0, zy_r + 1.3 + 23.5, zp0 + 1.0], C["pcb_blue"], i="A501")
    sc.box([zx0 + 0.5, zy_r + 7.3, zp0 + 1.0, zx0 + 17.5, zy_r + 24.3, zp0 + 4.4], C["pcb_blue"], i="A501", o=0.18)
    sc.box([zx0 + 2.06, zy_r + 1.3 + 5.5, z1, zx0 + 15.96, zy_r + 1.3 + 23.0, zp0], C["kapton"], i="A501", o=0.85)
    sc.box([zx0 + 4.67, zy_r, zp0 + 1.0, zx0 + 13.61, zy_r + 7.3, zp0 + 4.2], C["shell"], i="A501")
    sc.box([zx0 + 5.5, zy_r + 12.0, zp0 + 1.0, zx0 + 12.5, zy_r + 19.0, zp0 + 1.9], C["chip"], i="A301-CHIP")
    sc.label((zx0 + 9, zy_r + 14, zp0 + 5.0), "A501 RP2040-Zero", 1)
    for pin, (x, y, net) in pp["A501"].items():
        sc.box([x - 0.32, y - 0.32, z0 - 2.0, x + 0.32, y + 0.32, zp0 + 3.4], C["pin"], i="A501.%s" % pin, n=real_net(net))
    # W208 USB-C plug stub toward -y
    sc.box([zx0 + 4.92, zy_r - 25.0, zp0 + 0.8, zx0 + 13.36, zy_r - 0.05, zp0 + 4.4], C["usb"], i="W208", g="cable")
    sc.label((zx0 + 9, zy_r - 14, zp0 + 6.0), "W208 USB → 허브 포트 2", 1)
    for ref, d in pp.items():
        for pin, (x, y, net) in d.items():
            s = "bt" if ref.startswith("TP") else "b"
            sc.pad(x, y, (z0, z1), net, "%s.%s" % (ref, pin), s)
    # parts
    resistor(sc, "R501", pp["R501"]["1"][:2], pp["R501"]["2"][:2], z1, "1k", zb=z0)
    resistor(sc, "R502", pp["R502"]["1"][:2], pp["R502"]["2"][:2], z1, "100k", zb=z0)
    for s_ in "abcde":
        resistor(sc, "R503", pp["R503" + s_]["1"][:2], pp["R503" + s_]["2"][:2], z1, "100", zb=z0)
    chip1206(sc, "C501", pp["C501"]["1"][:2], pp["C501"]["2"][:2], z0 - 0.25)
    a, b = pp["JP504"]["1"][:2], pp["JP504"]["2"][:2]
    sc.box([a[0] - 0.55, min(a[1], b[1]) - 0.4, z0 - 0.55, a[0] + 0.55, max(a[1], b[1]) + 0.4, z0], C["solder"], i="JP504")
    for tp in ("TP501", "TP502"):
        x, y, net = pp[tp]["1"]
        sc.add(k="c", a="x", p=[r2(y), r2(z1 + 1.6)], r=1.1, s=[r2(x - 0.25), r2(x + 0.25)], c=C["tin"], i=tp, g="part", n=net, ring=1)
    # underside wires (wiring_PB.csv)
    zu = z0 - 0.4
    for k, r in enumerate(read_csv("wiring_PB.csv")):
        poly = parse_path(r["경로 (모델 좌표 x, y)"])
        bare = "맨선" in r["선"]
        wid = "PBW-%s-%s" % (r["넷"], r["선 번호"])
        strand(sc, down_ends(poly, zu - (0.0 if bare else 0.12), z0), r["넷"], wid, bare=bare)
        info(wid, "PB 아랫면 %s %s (%s)" % (r["넷"], r["선 번호"], r["선"]),
             ["%s · %s mm" % (r["선"], r["직각 길이 (mm)"]), "경로: " + r["경로 (모델 좌표 x, y)"],
              "주석 맨선은 지나는 패드마다 납땜, 리본 가닥은 두 끝만." , "wiring_PB.csv · BRD-03"])
    # posts + screws (context)
    for hx, hy, d, t in B2.PB_HOLES:
        if "나사" in t:
            sc.cyl("z", (hx, hy), 3.0, (16.5, z0), C["printed"], i="CTX-POST", g="ctx", o=0.45)
            sc.cyl("z", (hx, hy), 2.75, (z1, z1 + 1.65), C["screw"], i="CTX-POST", g="ctx")
        else:
            sc.cyl("z", (hx, hy), 3.0, (16.5, z0), C["printed"], i="CTX-POST", g="ctx", o=0.45)
            sc.cyl("z", (hx, hy), 1.4, (z0, z1 + 2.0), C["printed"], i="CTX-POST", g="ctx", o=0.6)
    info("CTX-POST", "기둥 (가운데 유닛 아랫판 출력물)", ["PB · J702 기판은 5 mm 기둥 위. M3 나사 2개 + 위치 핀 2개."])
    # ---- J501 scrap (z36.4~38.0) + jack + W502 strands (estimated path) + W501 stub
    jb = B3.J5_BOX
    jz0, jz1 = HN.PTS.get("j501_board", [450.0, 475.0, 316.5, 340.5, 36.4, 38.0])[4:6]
    sc.board(rect(jb[0], jb[2], jb[1], jb[3]), (jz0, jz1), lattice([B3.j5x(i) for i in range(9)], [B3.j5y(j) for j in range(9)]), C["perf"], "PCB-J501")
    board_info("PCB-J501", "J501 페달 잭 조각 (25 × 24, 9 × 9 구멍)", ["페달 선 W501의 3.5 mm 플러그를 꽂는 잭 자리입니다. 잭 → W502 4가닥 → PB J502.",
                                                         "뒤판 출력물 위 (z36.4~38.0). 잭 다리 → 앞 패드 1 T · 2 TN · 3 R · 4 S (피복 가닥, 받은 잭 다리에서 가장 짧게).",
                                                         "도면 BRD-07, SCH-05"])
    jk = B3.J5_JACK
    sc.box([jk[0], jk[2], jz1, jk[1], jk[3] - 2.5, jz1 + 5.0], C["jack"], i="J501")
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, jz1 + 2.5), 2.5, (jk[3] - 2.5, jk[3]), C["jack"], i="J501")
    sc.box([B3.J5_FIELD[0], B3.J5_FIELD[2], jz1, B3.J5_FIELD[1], B3.J5_FIELD[3], jz1 + 0.05], "#f0a830", i="J5-FIELD", g="ctx", o=0.35)
    info("J5-FIELD", "잭 다리 자리 (추정)", ["PJ-313 다리 간격은 2.54가 아니어서 이 칸 안에서 가장 가까운 구멍으로 구부려 꽂습니다. 다리 글자는 통전 검사로 찾음."])
    sc.label(((jk[0] + jk[1]) / 2, jk[3] + 2.0, jz1 + 7.0), "J501 페달 잭", 1)
    smalls = read_csv("pads_small.csv")
    j5p = [(float(r["x"]), float(r["y"]), r["넷"], r["핀"]) for r in smalls if r["기판"].startswith("J501")]
    sc.bd = "J501 조각"
    for x, y, net, pin in j5p:
        sc.pad(x, y, (jz0, jz1), net, "W502.%s" % pin, "b")
    pbj = sorted(pp["J502"].items())
    for (pin, (x, y, net)), (xa, ya, _n, _p) in zip(pbj, sorted(j5p, key=lambda t: t[3])):
        sc.tube([(x, y, z0), (x, y, z0 - 1.2), (x, by1 + 2.0, z0 - 1.2), (x, by1 + 2.0, jz0 - 1.0), (xa, ya - 1.0, jz0 - 1.0), (xa, ya, jz0)], 0.24,
                C["ribbon"] if pin != "1" else C["ribbon_red"], i="W502", g="cable", n=net, q="%s번 가닥 · PB J502 %s번 → J501 조각 %s번 패드" % (pin, pin, pin))
    sc.label((452.0, 315.0, 30.0), "W502 (경로 추정)", 1)
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, jz1 + 2.5), 1.9, (jk[3] + 8.0, jk[3] + 26.0), C["cable"], i="W501", g="cable")
    sc.label(((jk[0] + jk[1]) / 2, jk[3] + 22.0, jz1 + 6.0), "W501 → 페달 (3 m)", 1)
    # ---- PS pedal sensor scrap (local frame), shown beside the PB
    ox, oy, oz = 392.0, 300.0, 21.5
    ps = [(float(r["x"]), float(r["y"]), r["넷"], r["부품"], r["핀"]) for r in smalls if r["기판"].startswith("PS")]
    pz0, pz1 = oz, oz + 1.6
    sc.board(rect(ox - 1.27, oy - 1.27, ox + 6 * 2.54 + 1.27, oy + 4 * 2.54 + 1.27), (pz0, pz1),
             lattice([ox + 2.54 * c for c in range(7)], [oy + 2.54 * r for r in range(5)]), C["perf"], "PCB-PS")
    board_info("PCB-PS", "PS 페달 안 센서 조각 (7 × 5 구멍)", ["페달을 밟은 깊이를 재는 홀 센서 U551 조각입니다. 페달 선 W501(TIP 신호 · RING 3.3 V · SLEEVE GND)로 J501에 이어집니다.",
                                                      "페달 안 자석 아래 (실제 위치는 페달 몸통 안 — 여기서는 PB 옆에 둠). U551은 표시면을 위로 눕혀 리드를 +x로.",
                                                      "로컬 좌표 (왼쪽 아래 구멍 = 0, 0). 도면 BRD-07, SCH-05"])
    sc.label((ox + 7.0, oy - 4.0, pz1), "PS (페달 안, 보기 위해 옆에)", 0)
    sc.bd = "PS"
    for x, y, net, ref, pin in ps:
        sc.pad(ox + x, oy + y, (pz0, pz1), None if net.startswith("U551 OUT") else net, "%s.%s" % (ref, pin), "b")
    sc.box([ox + 5.08 - 1.75 - 3.15, oy + 5.08 - 2.0, pz1, ox + 5.08 - 1.75, oy + 5.08 + 2.0, pz1 + 1.52], C["hall"], i="U551")
    for yb, yt in ((-1.27, 2.54), (0.0, 5.08), (1.27, 7.62)):
        sc.tube([(ox + 5.08 - 1.75, oy + 5.08 + yb, pz1 + 0.76), (ox + 5.08 - 0.6, oy + yt, pz1 + 0.76), (ox + 5.08, oy + yt, pz1 + 0.3),
                 (ox + 5.08, oy + yt, pz0 - 1.0)], 0.2, C["lead"], i="U551")
    chip1206(sc, "C551", (ox + 7.62, oy + 2.54), (ox + 7.62, oy + 5.08), pz0 - 0.25)
    resistor(sc, "R551", (ox + 7.62, oy + 7.62), (ox + 15.24, oy + 7.62), pz1, "1k", zb=pz0)
    for k, r in enumerate([q for q in read_csv("wiring_small.csv") if q["기판"] == "PS"]):
        poly = [(ox + x, oy + y) for x, y in parse_path(r["경로 (x, y)"])]
        net = r["넷"] if not r["넷"].startswith("U551 OUT") else None
        wid = "PSW-%d" % (k + 1)
        strand(sc, down_ends(poly, pz0 - 0.4, pz0), net, wid, bare=True)
        info(wid, "PS 아랫면 %s (주석 맨선)" % r["넷"], ["%s mm · 경로 %s (로컬)" % (r["길이 (mm)"], r["경로 (x, y)"]), "wiring_small.csv · BRD-07"])
    for k, (pin, cc) in enumerate((("T", C["wire_wht"]), ("R", C["shrink_red"]), ("S", "#6b7690"))):
        x, y = [(ox + q[0], oy + q[1]) for q in ps if q[3] == "W501" and q[4] == pin][0]
        sc.tube([(x, y, pz0), (x, y, pz0 - 1.0), (x + 4.0, y, pz0 - 1.5), (ox + 26.0, oy + 5.08, pz0 - 1.5)], 0.35, cc, i="W501", g="cable",
                n=[q[2] for q in ps if q[3] == "W501" and q[4] == pin][0])
    sc.view("PB · J501 · PS", [388, 238, 14, 480, 345, 45], az=-30, el=45, default=True)
    sc.view("PB 아랫면", [424, 240, 14, 480, 318, 30], az=-30, el=-55)
    sc.view("PB 위", [424, 240, 14, 480, 318, 30], az=0, el=89)
    sc.view("J501 · W502", [440, 300, 15, 480, 345, 45], az=35, el=30)
    sc.view("PS 확대", [388, 296, 15, 422, 314, 26], az=-25, el=45)
    sc.note("W502(J502 → J501)의 실제 경로는 판 모서리를 돌아 약 40 mm로 '추정'입니다. 잭 다리 위치는 받은 잭에 따릅니다 (주황 칸).")
    return sc


# ====================================================================== J702 amp-input board (+ J701 note)
def scene_j702():
    sc = Scene("j702", "앰프 입력 기판 J702 (30 × 25, 80 Hz RC)", "가운데 유닛 세계 좌표 (x505~535 · y255~280 · z21.5~23.1).", "world", "앰프 입력 J702")
    sc.m, sc.bd = "AUD", "J702 기판"
    jb = B3.J7_BOX
    z0, z1 = HN.PTS.get("j702_board", {}).get("box", [505.0, 535.0, 255.0, 280.0, 21.5, 23.1])[4:6]
    sc.board(rect(jb[0], jb[2], jb[1], jb[3]), (z0, z1), lattice([B3.j7x(i) for i in range(B3.J7_NI)], [B3.j7y(j) for j in range(B3.J7_NJ)],
                                                                lambda x, y: min(math.hypot(x - a, y - b) for a, b in B3.J7_HOLES) > 2.2),
             C["perf"], "PCB-J702", mholes=[(a, b, 3.2) for a, b in B3.J7_HOLES])
    board_info("PCB-J702", "J702 앰프 입력 기판 (만능기판 조각 30 × 25, 12 × 10 구멍)", [
        "헤드폰 잭 노멀(W702) → J702 → C701·C702 / C703·C704 1 µF 나란히 + R701 · R702 1 kΩ (80 Hz 고역 통과) → W707 → 앰프 입력.",
        "잭 TN · RN 다리는 고정용으로만 납땜. 도면 BRD-07, SCH-07"])
    sc.label((jb[0] + 3, jb[2] - 3.0, z1), "J702 기판", 0)
    jk = B3.J7_JACK
    sc.box([jk[0], jk[2] + 2.5, z1, jk[1], jk[3], z1 + 5.0], C["jack"], i="J702")
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, z1 + 2.5), 2.5, (jk[2], jk[2] + 2.5), C["jack"], i="J702")
    sc.cyl("y", ((jk[0] + jk[1]) / 2.0, z1 + 2.5), 1.8, (jk[2] - 0.01, jk[2] + 0.2), "#000000", i="J702")
    fz = B3.J7_FIELD
    sc.box([fz[0], fz[2], z1, fz[1], fz[3], z1 + 0.05], "#f0a830", i="J7-FIELD", g="ctx", o=0.35)
    info("J7-FIELD", "잭 다리 자리 (추정)", ["PJ-313 다리(1.8 · 3.2 · 3.5 간격)는 격자에 맞지 않아 이 칸 안의 가장 가까운 구멍에 꽂고, T · R · S 다리만 모음 패드까지 짧은 피복 가닥으로 잇습니다."])
    sc.label(((jk[0] + jk[1]) / 2, jk[2] - 1.5, z1 + 7.0), "J702 PJ-313 ← W702", 1)
    smalls = [r for r in read_csv("pads_small.csv") if r["기판"].startswith("J702")]
    pp = {}
    for r in smalls:
        pp.setdefault(r["부품"], {})[r["핀"]] = (float(r["x"]), float(r["y"]), r["넷"])
        sc.pad(float(r["x"]), float(r["y"]), (z0, z1), r["넷"], "%s.%s" % (r["부품"], r["핀"]), "b")
    # 1 uF radial MLCC (blue dipped, 5.0 x 2.5 body standing), leads 5.08 along y
    for ref in ("C701", "C702", "C703", "C704"):
        (xa, ya, _), (xb, yb, _) = pp[ref]["1"], pp[ref]["2"]
        xm, ym = (xa + xb) / 2.0, (ya + yb) / 2.0
        sc.box([xm - 1.2, ym - 2.5, z1 + 2.2, xm + 1.2, ym + 2.5, z1 + 6.6], C["mlcc"], i=ref)
        for yy in (ya, yb):
            sc.tube([(xm, yy, z1 + 2.4), (xm, yy, z0 - 1.0)], 0.25, C["lead"], i=ref, g="part")
    resistor(sc, "R701", pp["R701"]["1"][:2], pp["R701"]["2"][:2], z1, "1k", zb=z0)
    resistor(sc, "R702", pp["R702"]["1"][:2], pp["R702"]["2"][:2], z1, "1k", zb=z0)
    # jack legs -> collector pads (depend on the jack): short dashed-style strands from the field edge
    for pin, (x, y, net) in pp["J702"].items():
        fx = min(max(x, fz[0] + 0.6), fz[1] - 0.6)
        fy = min(y, fz[3] - 0.6)
        sc.tube([(fx, fy, z0), (fx, fy, z0 - 0.9), (x, y, z0 - 0.9), (x, y, z0)], 0.3, col(net), i="J7-LEG-" + pin, g="wire", n=net, w="피복 가닥 (추정)")
        info("J7-LEG-" + pin, "잭 %s 다리 → %s 모음 패드 (추정)" % (pin, pin), ["받은 잭의 다리 자리에서 가장 짧게 피복 가닥 1가닥. 넷 " + net])
    zu = z0 - 0.4
    for k, r in enumerate([q for q in read_csv("wiring_small.csv") if q["기판"] == "J702"]):
        poly = parse_path(r["경로 (x, y)"])
        bare = "맨선" in r["선"]
        wid = "J7W-%d" % (k + 1)
        strand(sc, down_ends(poly, zu - (0.0 if bare else 0.12), z0), r["넷"], wid, bare=bare)
        info(wid, "J702 아랫면 %s (%s)" % (r["넷"], r["선"]), ["%s mm · 경로 %s" % (r["길이 (mm)"], r["경로 (x, y)"]), "wiring_small.csv · BRD-07"])
    # W707 to the amp input (L / G / R), stub toward +y; W702 plug in front
    for pin, cc in (("L", C["wire_wht"]), ("G", "#6b7690"), ("R", C["shrink_red"])):
        x, y, net = pp["W707"][pin]
        sc.tube([(x, y, z0), (x, y, z0 - 1.0), (x, jb[3] + 2.0, z0 - 1.0), (x + (519.0 - x) * 0.6, jb[3] + 14.0, z0 + 1.0)], 0.35, cc, i="W707",
                g="cable", n=net)
    sc.label((519.0, jb[3] + 12.0, z1 + 3.0), "W707 → 앰프 입력", 1)
    pl = HN.PTS.get("hp_route", {}).get("j702_plug", [520.0, 222.0, 25.6])
    sc.cyl("y", (pl[0], z1 + 2.5), 1.75, (jk[2] - 14.0, jk[2] - 0.5), C["shell"], i="W702", g="cable")
    sc.cyl("y", (pl[0], z1 + 2.5), 3.0, (jk[2] - 30.0, jk[2] - 14.0), C["usb"], i="W702", g="cable")
    for hx, hy in B3.J7_HOLES:
        sc.cyl("z", (hx, hy), 3.0, (16.5, z0), C["printed"], i="CTX-POST", g="ctx", o=0.45)
        sc.cyl("z", (hx, hy), 2.75, (z1, z1 + 1.65), C["screw"], i="CTX-POST", g="ctx")
    sc.view("J702", [503, 246, 14, 537, 296, 32], az=-30, el=45, default=True)
    sc.view("W702 플러그까지", [500, 222, 14, 540, 296, 32], az=-30, el=45)
    sc.view("아랫면", [503, 253, 14, 537, 282, 26], az=-30, el=-55)
    sc.view("위", [503, 253, 14, 537, 282, 26], az=0, el=89)
    sc.note("C701~C704는 리드형 적층 세라믹 1 µF (몸통 5 × 2.5 어림). 잭 다리 → 모음 패드 3가닥은 받은 잭에 따라 '추정'입니다.")
    return sc


# ====================================================================== whole instrument wiring (world)
PAIR = {"red": C["shrink_red"], "blk": "#1d2433"}


def pair_tube(sc, pts, r, cols, i, nets=None, gap=None):
    """two conductors side by side along a centre line (offset in the horizontal normal; vertical runs offset in x); nets = the net
    of each conductor (harness.py), so a click lights the whole net."""
    nets = list(nets or []) + [None, None]
    if len(cols) == 1:
        sc.tube(pts, r, cols[0], i=i, g="cable", n=nets[0])
        return
    gap = gap or r * 1.05
    out = [[], []]
    for k, p in enumerate(pts):
        a = pts[max(0, k - 1)]
        b = pts[min(len(pts) - 1, k + 1)]
        tx, ty, tz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        h = math.hypot(tx, ty)
        if h < 1e-6 * (abs(tz) + 1):
            nx, ny = 1.0, 0.0
        else:
            nx, ny = -ty / h, tx / h
        for s, o in ((1, out[0]), (-1, out[1])):
            o.append((p[0] + s * gap * nx, p[1] + s * gap * ny, p[2]))
    sc.tube(out[0], r, cols[0], i=i, g="cable", n=nets[0])
    sc.tube(out[1], r, cols[1], i=i, g="cable", n=nets[1])


def scene_all(SP, CAD, JK):
    sc = Scene("all", "악기 전체 배선 — 모듈 7개 · 끝 부속 · 가운데 유닛",
               "세계 좌표 (x 0 = A0 왼쪽 끝, y = 흰 건반 앞 끝부터 뒤로). 모듈 7개(O1~O7)와 끝 부속 EL · ER, 가운데 유닛 기판 셋(PB · J702 · J501) 모두 "
               "센서·패드·아랫면 배선까지 그렸습니다. 보기의 O1~O7을 누르거나 두 번 눌러 다가가세요.", "world", "악기 전체 배선")
    parts = CAD["parts"]
    sc.d["scopes"] = {}
    sc.d["g0"] = "CU"
    # ---- modules O1..O7, each as it is built (the same objects as the module scene, placed at the module's x; O1 / O7 / O2~O6 differ
    # in R30x, the EXT lead and the ID jumpers - mb_scene_parts)
    for k in range(1, 8):
        X0 = X_O1 + MODULE_W * (k - 1)
        tag = "O%d" % k
        sc.dx, sc.m, sc.dz = X0, tag, NEAR
        module_objs(sc, SP, k, whole=True)
        sc.dx, sc.dz = 0.0, None
        sc.label((X0 + 82.0, 122.0, 24.0), tag, 0, far=True)
        sc.d["scopes"][tag] = scope_module(k)
        if tag in ("O1", "O7"):
            x = X0 + 86.5
            path = ([(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, 1.5), (x - 8.0, 226.0, 1.5), (69.4 + 1.5, 231.0, 1.5)] if tag == "O1" else
                    [(x, 212.0, 6.5), (x, 213.5, 6.5), (x, 217.0, 1.5), (x + 8.0, 226.0, 1.5), (1160.0 - 1.5, 231.0, 1.5)])
            sc.tube(path, 1.5, "#7e889a", i="W403" if tag == "O1" else "W413", g="cable")
        sc.m = None
    # ---- end parts: the boards with their sensors and wiring, leads to the XH pairs on the passage floor
    for tag, X0 in (("EL", 0.0), ("ER", X_RIGHT)):
        sc.dx, sc.m, sc.dz = X0, tag, NEAR
        end_objs(sc, SP, tag, whole=True)
        sc.dx, sc.dz = 0.0, None
        sc.label((X0 + 12.0, 60.0, 16.0), tag, 0, far=True)
        sc.d["scopes"][tag] = scope_end(tag)
        sc.m = None
    for k_, it in (("EL", "xh_left"), ("ER", "xh_right")):
        b = SP[it]["boxes"]
        sc.m = k_
        sc.box(bx(b[0]), "#f4f1ea", i="XH-" + k_, g="part")
        x0_, x1_ = b[1]["x"]
        xm = (x0_ + x1_) / 2.0
        sc.tube([(xm, 212.0, 3.0), (xm, 216.0, 1.0), (b[0]["x"][0] - 1.0 if k_ == "EL" else b[0]["x"][1] + 1.0, 231.0, 1.0)], 1.0, C["ribbon"],
                i="W401" if k_ == "EL" else "W411", g="cable")
        sc.m = None
    info("XH-EL", "X401 ⇄ X402 XH2.54 5P (뒤 통로 바닥)", ["EL 리드 W401 끝 헤더(수) ⇄ O1 EXT W403 하우징(암, 압착). 1 GND · 2 A0 · 3 A#0 · 4 B0 · 5 3V3 (△34; J302 패드 1·2·3·4·6)."])
    info("XH-ER", "X411 ⇄ X412 XH2.54 3P (뒤 통로 바닥)", ["ER 리드 W411 끝 헤더(수) ⇄ O7 EXT W413 하우징(암, 압착). 1 GND · 2 C8 · 3 3V3 (△34; J302 패드 1·2·6)."])
    # ---- headphone jack J701 (left cheek pocket) + AUX halves W701 / W702
    pk = JK["pocket"]
    cav = pk["body_cavity"]
    sc.box([cav["x"][0], cav["y"][0], cav["z"][0], cav["x"][1], cav["y"][1], cav["z"][1]], C["jack"], i="J701")
    sc.cyl("y", (pk["centre_x"], pk["axis_z"]), JK["jack_dims"]["nose_d"] / 2.0, (0.0, cav["y"][0]), C["jack"], i="J701")
    sc.label((pk["centre_x"], 0.0, pk["axis_z"] + 5.0), "J701 헤드폰 잭", 1)
    for w, cc in (("W701", C["wire_wht"]), ("W702", "#c8ccd4")):
        pts = CAD["paths"]["HP"][w]
        sc.tube([tuple(p) for p in pts], 1.75, cc, i=w, g="cable")
    # ---- USB cables (CAD centre lines). △33 (A16) moved the module plug into the module (tail y195.48, axis z13.2); a centre line saved
    # before that starts at the old tail (y~221) -> joined to the new tail with the straight +y run the spec describes
    up = SP["usb_plug"]["boxes"][0]
    for k in range(1, 8):
        X0 = X_O1 + MODULE_W * (k - 1)
        pts = [tuple(p) for p in CAD["paths"]["USB"]["O%d" % k]]
        tail = (X0 + (up["x"][0] + up["x"][1]) / 2.0, up["y"][1], (up["z"][0] + up["z"][1]) / 2.0)
        if pts and pts[0][1] > tail[1] + 1.0:
            pts = [tail, (tail[0], tail[1] + 4.0, tail[2])] + pts
        sc.m = "O%d" % k
        sc.tube(pts, 1.75, C["cable"], i="W20%d" % k, g="cable")
        sc.m = None
    # ---- centre-unit parts (CAD outlines); the three small boards come from the detail scenes
    # the three small boards come from the detail scenes; the screen leads (DSI FFC, 5 V / GND) rise to the screen on the lid - the CAD
    # gives them only as top-view outlines, so they are left out here (04 3D 모델 has them); W208 / C25 are drawn from their CAD route below
    skip = {"CU-E-PEDBOARD", "CU-E-PEDZERO", "CU-E-J702BOARD", "CU-E-J702", "CU-E-J501BOARD", "CU-E-J501", "TS-C-DSI", "TS-C-PWR-RED",
            "TS-C-PWR-BLK", "C-USB-PED", "C-USB-UPSTREAM"}
    paint = {"BAT-LFP": C["battery"], "C-XT60": C["xt60"], "C-DC": C["jack"], "CU-E-FUSE": C["fuse"], "CU-E-SWITCH": "#1d1d1f",
             "CU-E-BUCK": C["buck"], "CU-E-PI5": C["pi"], "CU-E-PI5-RJ45": C["shell"], "CU-E-PI5-USBA1": C["shell"], "CU-E-PI5-USBA2": C["shell"],
             "CU-E-PI5-DISP1": "#e8e2d0", "CU-E-GENDER": C["shell"], "CU-E-DONGLE": C["dongle"], "PB-E-HUB": C["hub"], "CU-E-AMP": C["amp"],
             "C-XT60F-L": C["xt60"], "C-XT60M-L": C["xt60"], "C-XT60F-R": C["xt60"], "C-XT60M-R": C["xt60"], "C-USB-PED": C["cable"],
             "C-USB-UPSTREAM": C["cable"], "TS-C-DSI": C["ffc"], "TS-C-PWR-RED": C["shrink_red"], "TS-C-PWR-BLK": "#1d2433"}
    tube_ids = {"C-BAT-LEAD": ("BAT", ["red", "blk"]), "C-BAT-DC": ("DC", ["red", "blk"]), "C-PWR-IN": ("IN", ["red", "blk"]),
                "C-PWR-FUSE": ("FUSE", ["red"]), "C-PWR-BUS": ("BUS", None), "C-PWR-5V": ("5V", ["red", "blk"]),
                "C-SPK-L": ("SPK.L", ["red", "blk"]), "C-SPK-R": ("SPK.R", ["red", "blk"]), "C-SPKPIG-L": ("PIG.L", ["red", "blk"]),
                "C-SPKPIG-R": ("PIG.R", ["red", "blk"])}
    wid_of, cad_ref = HK.WID_OF, HK.CAD_REF                  # CAD id -> W number / refdes (shared with BRD-04, hitkeys.py)
    for pid, p in parts.items():
        if pid in skip or pid.startswith("O") and pid.endswith("-C-USB"):
            continue
        name = p["name"]
        key = wid_of.get(pid, pid)
        ref = cad_ref.get(pid)
        if ref and ref in INFO:                                   # a circuit part: what it is and where its pins go (bom.csv + netlist.csv)
            key = ref
            more = {"X605": "X606 (W601 전지 하네스의 XT60 수)와 맞물립니다.", "X703": "X704 (왼쪽 스피커 꼬리선)와 맞물립니다.",
                    "X704": "X703 (앰프 쪽 스피커선 W703)과 맞물립니다.", "X705": "X706 (오른쪽 스피커 꼬리선)과 맞물립니다.",
                    "X706": "X705 (앰프 쪽 스피커선 W705)와 맞물립니다.",
                    "A604": "포트: " + " · ".join("%s번 %s" % (pt, t) for t, pt in sorted(HN.HUB_PORTS.items(), key=lambda q: q[1])) +
                            " (W201~W208). 업스트림 B ← W209 ← Pi 5, 전원 DC ← W604 ← 강압 5.1 V.",
                    "A603": "USB-C 전원 ← P601 (W603, 강압 5.1 V) · USB-A ← 허브 업스트림 W209, 동글 젠더 X701 · CAM/DISP 1 ← 화면 FFC W605 · 헤더 2·6번 → 화면 전원 W606.",
                    "A701": "젠더 X701로 Pi 5 USB-A에 꽂고, 3.5 mm 출력은 W701로 헤드폰 잭 J701에 갑니다."}.get(ref)
            ovr(ref, INFO[ref]["t"], ([more] if more else []) + INFO[ref]["d"] + ["3D 자리: " + name])
        elif key not in INFO:
            info(key, name, [p.get("note", "")[:400], "CAD %s · 상자 x%.1f~%.1f y%.1f~%.1f z%.1f~%.1f" % tuple([pid] + [p["bbox"][j] for j in (0, 3, 1, 4, 2, 5)])])
        if pid == "CU-E-AMP" and CAD["points"].get("amp"):
            amp_detail(sc, CAD["points"]["amp"], key)
            continue
        if pid in tube_ids:
            grp, cols = tube_ids[pid]
            g1, g2 = (grp.split(".") + [None])[:2]
            polys = CAD["paths"]["PWR"][g1] if g2 is None else [CAD["paths"][g1][g2]]
            def cn(w, cs):
                return [cond_net(w, c) for c in cs]
            if grp == "BUS":
                pair_tube(sc, [tuple(q) for q in polys[0]], 0.75, [PAIR["red"]], "W602b", cn("W602b", ["red"]))
                for q in polys[1:]:                     # back lane + (△32) the flat leg under the HW-720 to its DC jack pins
                    pair_tube(sc, [tuple(r) for r in q], 0.75, [PAIR["red"], PAIR["blk"]], "W602c", cn("W602c", ["red", "blk"]))
            elif grp == "5V":
                pair_tube(sc, [tuple(q) for q in polys[0]], 0.75, [PAIR[c] for c in cols], "W603", cn("W603", cols))
                pair_tube(sc, [tuple(q) for q in polys[1]], 0.75, [PAIR[c] for c in cols], "W604", cn("W604", cols))
            elif grp in ("IN", "FUSE"):
                # 12 AWG holder tail (D4.2) -> soldered + heat-shrunk splice (D6.5) -> 16 AWG lead (W601: the XT60 M pair)
                sc.tube([tuple(q) for q in polys[0]], 2.1, PAIR["red"], i=key, g="cable", n=cond_net(key, "red"))
                sc.tube([tuple(q) for q in polys[1]], 3.25, "#2b2b2b", i=key, g="cable")
                pair_tube(sc, [tuple(q) for q in polys[2]], 0.75, [PAIR[c] for c in cols], key, cn(key, cols))
            else:
                for pl in polys:
                    pair_tube(sc, [tuple(q) for q in pl], 0.75, [PAIR[c] for c in cols], key, cn(key, cols))
            continue
        sc.prism(p["poly"], (p["bbox"][2], p["bbox"][5]), paint.get(pid, "#6b7690"), i=key, g="cable" if pid.startswith(("C-", "TS-C")) else "part")
    # W208 PED -> hub port 2 and C25 Pi -> hub upstream: centre lines rebuilt from electronics.ped_cable() / c25_geom() points
    hub = CAD["points"]["hub"]
    for pid in ("C-USB-PED", "C-USB-UPSTREAM"):
        p = parts[pid]
        info(wid_of[pid], p["name"], [p.get("note", "")[:400], "선 중심선은 CAD 경로 점(electronics.ped_cable / c25_geom)에서 다시 그림 (보기용)"])
    cx = 449.0 + B2.ZERO_SNAP[0] + 9.14                           # PED Zero USB-C axis (PB scene, snapped)
    px = hub["ports_x"][hub["port_map"]["PED"]]
    sc.m = "PED"
    sc.tube([(cx, 217.9, 27.0), (cx, 215.6, 27.0), (cx + 13.0, 215.6, 32.0), (cx + 27.0, 227.0, 37.0), (731.0, 227.0, 37.0),
             (px, 236.0, hub["port_z"]), (px, 248.0, hub["port_z"])], 1.75, C["cable"], i="W208", g="cable")
    for t, port in sorted(hub["port_map"].items(), key=lambda q: q[1]):
        x = hub["ports_x"][port]
        sc.m = t
        sc.box([x - 6.0, 248.0, hub["port_z"] - 3.5, x + 6.0, hub["bbox"][2], hub["port_z"] + 3.5], C["usb"], i="W208" if t == "PED" else
               "W20%s" % t[1:], g="cable", q="허브 포트 %s번에 꽂는 쪽" % port)
    sc.m = None
    # C25: up-angled A head in the Pi's lower GPIO-side port -> CAD centre line (cad_centre.json paths.C25) -> straight B into the hub
    c5 = CAD["points"]["c25"]
    face, ys, za = c5["face"], c5["ys"], c5["za"]
    hx, hw, ht = c5["a_head"]
    sc.box([face, ys - hw / 2, za - ht / 2, face + hx, ys + hw / 2, za + ht / 2], C["usb"], i="W209", g="cable")
    sc.cyl("z", (c5["xr"], ys), c5["a_boss"][0] / 2, (za + ht / 2, c5["z_top"]), C["usb"], i="W209", g="cable")
    sc.tube([tuple(q) for q in CAD["paths"]["C25"]], c5["d"] / 2, C["cable"], i="W209", g="cable")
    (by, bz), bb = c5["b_port"], c5["b_body"]
    sc.cyl("x", (by, bz), c5["b_boot"][1] / 2, (c5["x_b0"], c5["x_b1"]), C["usb"], i="W209", g="cable")
    sc.box([c5["x_b1"], by - bb[1] / 2, bz - bb[2] / 2, hub["bbox"][0], by + bb[1] / 2, bz + bb[2] / 2], C["usb"], i="W209", g="cable")
    # W604 hub DC: straight plug on the jack axis (2026-10-26), CAD box = jack face -> end of the boot
    dc, (dy, dz) = hub["dc"], hub["dc_yz"]
    sc.cyl("x", (dy, dz), (dc[3] - dc[2]) / 2, (dc[0], dc[1]), C["usb"], i="W604", g="cable")
    for pid, lab in (("BAT-LFP", "BT601 LiFePO4 12.8 V"), ("CU-E-FUSE", "F601 5 A"), ("CU-E-SWITCH", "SW601"), ("CU-E-BUCK", "A602 XL4016 5.1 V"),
                     ("CU-E-PI5", "Pi 5"), ("PB-E-HUB", "허브 710U3"), ("CU-E-AMP", "A702 HW-720"), ("CU-E-DONGLE", "동글")):
        b = parts[pid]["bbox"]
        sc.label(((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[5] + 4.0), lab, 0)
    # ---- detailed small boards in place
    for sub in (scene_pedal(), scene_j702()):
        for o in sub.d["objs"]:
            if o.get("k") == "l" and o.get("lv", 1) > 0:
                continue
            if sub.d["id"] == "pedal" and o.get("i", "").startswith(("PCB-PS", "U551", "C551", "R551", "PSW-")) or \
                    (sub.d["id"] == "pedal" and o.get("i") in ("U551", "C551", "R551")):
                continue
            if sub.d["id"] == "pedal" and o.get("i") == "W501" and o.get("k") == "t":
                continue
            if sub.d["id"] == "pedal" and o.get("k") in ("p",) and str(o.get("i", "")).split(".")[0] in ("U551", "C551", "R551", "W501"):
                continue
            sc.d["objs"].append(o)
    # ---- context: centre-unit printed / plywood walls (ghost)
    for c in CAD["context"]:
        sc.prism(c["poly"], (c["bbox"][2], c["bbox"][5]), C["ply"] if c.get("kind") == "plywood" else C["printed"], i="CTX-" + c["id"], g="ctx", o=0.10)
        info("CTX-" + c["id"], c["name"], ["주변 출력물 (흐리게) · CAD " + c["id"]])
    b = parts
    # one net under two names across a connector pair: the end-part nets are the EXT nets of the end boards
    J = sc.d["join"] = {}
    for tag, mod in (("EL", "O1"), ("ER", "O7")):
        Bd = S.END_BOARDS[tag]
        for n_ in range(len(Bd["keys"])):
            J["%s|%s" % (tag, Bd["jnames"][1 + n_])] = "%s|EXT%d" % (mod, n_ + 1)
        J["%s|%s" % (tag, Bd["jnames"][-1])] = "%s|+3V3" % mod
    sc.view("전체", [-14, 0, 0, 1232, 346, 60], az=-20, el=50, default=True)
    sc.view("EL · O1", [-6, 54, 0, 216, 242, 30], az=-28, el=42)
    for k in range(1, 8):
        X0 = X_O1 + MODULE_W * (k - 1)
        sc.view("O%d" % k, [X0 - 3, 56, 2, X0 + 167.5, 216, 30], az=-28, el=42)
    sc.view("O7 · ER", [1030, 54, 0, 1228, 242, 30], az=-28, el=42)
    sc.view("가운데 유닛", [255, 208, 0, 967, 346, 60], az=-25, el=55)
    sc.view("전원 구석", [372, 214, 14, 482, 345, 62], az=-35, el=45)
    sc.view("오디오 · Pi · 허브", [500, 214, 14, 920, 335, 62], az=-25, el=50)
    sc.view("위에서", [-14, 0, 0, 1232, 346, 60], az=0, el=89)
    sc.note("모듈마다 실제로 다른 것까지 그렸습니다: O1은 R301~R303 + EXT 선 W403 5가닥, O7은 R301 + W413 3가닥, O2~O6은 둘 다 없음, ID 점퍼는 모듈 번호대로. "
            "그 기판에서 쓰지 않는 아랫면 선은 흐리게 보입니다.")
    sc.note("끝 부속의 센서 넷(EL_A0 등)은 XH 커넥터를 지나 O1·O7의 EXT 넷과 같은 선이라, 누르면 양쪽이 함께 밝아집니다. GND는 악기 전체가 한 덩어리입니다.")
    sc.note("가운데 유닛 뚜껑 · 화면 · 스피커 통은 빼고, 아랫판 · 끝벽 · 뒤판 · 배터리 틀 · 기둥만 흐리게 보입니다. 선은 CAD의 선 중심선 (빨강 + 검정 두 가닥은 옆으로 나란히).")
    sc.note("화면 DSI · 화면 전원선(W606~W608)은 뚜껑 위 화면으로 올라가므로 여기서는 뺐습니다(04 3D 모델에 있음). USB 선은 지름 3.5 어림, 허브 쪽 플러그는 상자.")
    return sc


AMP_COL = {"OUTL": "#2f6fd6", "OUTR": "#2f6fd6", "DC": "#202124", "IC": "#1d1d1f", "CD": "#2b2b2b", "J35": "#2e8b57", "XH": "#f2f2f2",
           "POT": "#b8bec6"}


def amp_detail(sc, a, key):
    """△32 HW-720 from the CAD part boxes (cad_centre.json points.amp): board, terminals, DC jack, coils, chip, caps, XH input, pot shaft."""
    x0, y1, z0 = a["x0"], a["y1"], a["z0"]
    w, d, t = a["pcb"]
    zt = z0 + t
    sc.box([x0, y1 - d, z0, x0 + w, y1, zt], C["amp"], i=key)
    for k, (u0, u1, v0, v1, h) in a["boxes"].items():
        sc.box([x0 + u0, y1 - v1, zt, x0 + u1, y1 - v0, zt + h], AMP_COL.get(k, "#5b5f66"), i=key)
    for u, v in a["caps"]:
        sc.cyl("z", (x0 + u, y1 - v), a["cap"][0] / 2, (zt, zt + a["cap"][1]), "#3a3a3a", i=key)
    u0, u1, va, ha, dd = a["shaft"]
    sc.cyl("x", (y1 - va, zt + ha), dd / 2, (x0 + u0, x0 + u1), "#c0c6cc", i=key)


# ====================================================================== build
def build(write=True):
    t0 = time.time()
    INFO.clear()
    OVR.clear()
    _KT.clear()
    SP = load_spec()
    JK = load_jack_spec()
    with open(os.path.join(NL, "cad_centre.json"), encoding="utf-8") as f:
        CAD = json.load(f)
    bom = bom_info()
    cable_info()
    info("BAT-LEAD", "BT601 팩 XT60 선 (배터리에 딸림)", ["팩 +x 끝면 → 선 꺾는 자리 → 팩 윗면 XT60 암 X605 (빨강 수축).", "잇는 곳: BT601 → X605 ⇄ X606 (W601)"])
    info("BAT-DC", "BT601 충전 선 (배터리에 딸림)", ["팩 +x 끝면 → 팩 윗면 DC 5.5 × 2.1 충전 입력 (14.4 V).", "잇는 곳: BT601 ← 충전기 (악기 회로에는 이어지지 않음)"])
    scenes = [scene_all(SP, CAD, JK), scene_module(SP, bom), scene_end(SP), scene_pedal(), scene_j702()]
    for s in scenes[1:]:                    # pads <-> wires; the instrument scene holds the same keys
        link(s)
    nets = {}
    for s in scenes:
        join = s.d.setdefault("join", {})
        for o in s.d["objs"]:
            n = o.get("n")
            if n:
                nets[n] = col(n)
                if n == "GND" and o.get("m"):            # one ground: the boards share it through the USB cables and the EXT leads
                    join["%s|GND" % o["m"]] = "|GND"
            i = o.get("i")
            if i and i not in INFO and i not in OVR:
                base = i.split(".")[0]
                if base not in INFO and base not in OVR and not i.startswith(("CTX", "J7-", "J5-")):
                    INFO.setdefault(base, dict(t=base, d=[]))
            o.pop("_bd", None)
        if not join:
            del s.d["join"]
    out = {}
    for src in (INFO, OVR):                 # OVR last: the 3D texts win
        for key, e in src.items():
            out[key] = dict(t=e["t"].rstrip(" ·"), d=[x for x in e["d"] if x and not x.startswith("KiCad:")])
    known = dict(HT.mb_net_text())
    known.update(net_texts())
    netinfo = {}
    for n in nets:
        t, d = known.get(n, ("넷 " + n, []))
        netinfo[n] = dict(t=t, d=list(d) + cu_pins(n))
    for key, (t, d) in known.items():
        if "|" in key:
            netinfo[key] = dict(t=t, d=list(d))
    data = dict(rev=REV, built=time.strftime("%Y-%m-%d %H:%M"), nets=nets, netinfo=netinfo, info=out, scenes=[s.d for s in scenes],
                src=["hardware/pcb/src/model3d.py", "netlist/*.csv · cad_centre.json", "cad/spec/electronics_modules.json"])
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if write:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(txt)
    rep = dict(bytes=len(txt.encode("utf-8")), seconds=round(time.time() - t0, 2),
               scenes={s.d["id"]: len(s.d["objs"]) for s in scenes}, nets=len(nets), info=len(out))
    return data, rep


def spec_check():
    """the MB placement of the drawings (sheets.py) against the CAD spec electronics_modules.json (A16): outline, Zero, receptacle, mux pin
    rows, J301 / J302 pads, R30x rows - the two sources must agree (the CAD places its boxes from the same numbers)."""
    SP = load_spec()
    probs = []

    def near(a, b, tol=0.02):
        return abs(a - b) <= tol
    mb = SP["mb_board"]["boxes"][0]
    if not (near(mb["x"][0], S.MB["x0"]) and near(mb["x"][1], S.MB["x1"]) and near(mb["y"][0], S.MB["y0"]) and near(mb["y"][1], S.MB["y1"])
            and near(mb["z"][0], S.MB["zb"]) and near(mb["z"][1], S.MB["zt"])):
        probs.append("MB outline: spec %s / sheets %s" % (mb, S.MBX["board"]))
    z = SP["zero"]["boxes"][0]
    if not (near(z["x"][0], S.ZX) and near(z["y"][1], S.ZY)):
        probs.append("Zero PCB: spec x%.2f y%.2f / sheets x%.2f y%.2f" % (z["x"][0], z["y"][1], S.ZX, S.ZY))
    rc = SP["zero"]["boxes"][3]
    if not (near(rc["x"][0], S.USB_RX[0]) and near(rc["x"][1], S.USB_RX[1]) and near(rc["y"][1], S.USB_RY[1])):
        probs.append("USB-C receptacle: spec %s / sheets %s" % (rc, S.MBX["usb"]))
    for hb, n in ((SP["zero_headers"]["boxes"][0], 1), (SP["zero_headers"]["boxes"][1], 10)):
        if not near((hb["x"][0] + hb["x"][1]) / 2.0, S.zero_hole(n)[0]):
            probs.append("Zero header column x: spec %.2f / sheets %.2f" % ((hb["x"][0] + hb["x"][1]) / 2.0, S.zero_hole(n)[0]))
    pins = SP["mux"].get("pins", {})
    for row, names in (("channel_row", ["C%d" % i for i in range(16)]), ("control_row", ["GND", "VCC", "EN", "S0", "S1", "S2", "S3", "SIG"])):
        r = pins.get(row)
        if not r:
            probs.append("spec mux pins.%s missing" % row)
            continue
        for x, nm in zip(r["x"], names):
            px, py = S.mux_hole(nm)
            if not (near(x, px) and near(r["y"], py)):
                probs.append("mux %s: spec (%.2f, %.2f) / sheets (%.2f, %.2f)" % (nm, x, r["y"], px, py))
    jb = SP["j301_pads"]["boxes"][0]
    x1_, y1_ = S.mb_pad_xy("J301", 1)
    x16, y16 = S.mb_pad_xy("J301", 16)
    if not (near(jb["x"][0] + 0.9, x1_) and near(jb["x"][1] - 0.9, x16) and near(jb["y"][0] + 0.9, y1_) and near(jb["y"][1] - 0.9, y16)):
        probs.append("J301 pads: spec %s / sheets (%.2f, %.2f)~(%.2f, %.2f)" % (jb, x1_, y1_, x16, y16))
    eb = SP["j302_pads"]["boxes"][0]
    if not (near(eb["x"][0] + 0.9, S.EXT_X0) and near(eb["x"][1] - 0.9, S.EXT_X0 + 5 * 2.54) and near((eb["y"][0] + eb["y"][1]) / 2.0, S.EXT_Y)):
        probs.append("J302 pads: spec %s / sheets x%.2f y%.2f" % (eb, S.EXT_X0, S.EXT_Y))
    for b, ref in zip(SP["r30x"]["boxes"], ("R301", "R302", "R303")):
        x, y = S.R_EXT[ref]
        if not near((b["y"][0] + b["y"][1]) / 2.0, y) or not (x < b["x"][0] and b["x"][1] < x + 7.62):
            probs.append("%s: spec %s / sheets (%.2f, %.2f)" % (ref, b, x, y))
    # EXT lead path lengths quoted by harness.py (W403 / W413 cut lengths) = the drawn route
    el = ext_lead_lengths()
    for tag in ("O1", "O7"):
        if any(abs(a - b) > 0.5 for a, b in zip(el[tag], HN.EXT_PATH[tag])):
            probs.append("EXT lead %s path %s, harness.EXT_PATH says %s" % (tag, el[tag], HN.EXT_PATH[tag]))
        if HN.EXT_CUT[tag] < el[tag][1] + 10.0:
            probs.append("EXT lead %s cut %d < longest path %.1f + strip 5 + spare 5" % (tag, HN.EXT_CUT[tag], el[tag][1]))
    return probs


def check(data):
    """every pad / wire net is a real net of the netlist (or None), every info key the viewer will ask for exists (with its variant),
    join keys name real nets, the seven modules of the instrument scene carry what their board kind carries, and the MB placement
    agrees with the CAD spec (spec_check)."""
    probs = spec_check()
    real = {r["넷"] for r in NET_ROWS}
    inf = data["info"]
    for s in data["scenes"]:
        for o in s["objs"]:
            n = o.get("n")
            if n and n not in real:
                probs.append("%s: net %s (%s) not in netlist.csv" % (s["id"], n, o.get("i")))
            if n and n not in data["netinfo"]:
                probs.append("%s: no net text for %s" % (s["id"], n))
            i = o.get("i")
            if i and i.split(".")[0] not in inf and i not in inf:
                probs.append("%s: no info for %s" % (s["id"], i))
            if o.get("v") and "%s@%s" % (i, o["v"]) not in inf:
                probs.append("%s: no variant text %s@%s" % (s["id"], i, o["v"]))
            if o.get("m") and o["k"] != "l" and s.get("scopes") is not None and o["m"] not in s["scopes"] and o["m"] not in ("PED", "AUD"):
                probs.append("%s: scope %s has no text (%s)" % (s["id"], o["m"], i))
        for a_, b_ in s.get("join", {}).items():
            for key in (a_, b_):
                if key.split("|")[1] not in real:
                    probs.append("%s: join %s names no net" % (s["id"], key))
    allsc = data["scenes"][0]["objs"]
    for k in range(1, 8):
        tag, V = "O%d" % k, B4.KINDS[kind_of(k)]
        mine = [o for o in allsc if o.get("m") == tag]
        ids = {o.get("i") for o in mine}
        want_r = set(V["r"])
        have_r = {r for r in ("R301", "R302", "R303", "R304") if r in ids}
        if want_r != have_r:
            probs.append("all: %s carries %s, its kind wants %s" % (tag, sorted(have_r), sorted(want_r)))
        jp = {r for r in ("JP301", "JP302", "JP303", "JP304") if r in ids}
        if jp != B4.jp_closed(k):
            probs.append("all: %s closed jumpers %s, the ID table wants %s" % (tag, sorted(jp), sorted(B4.jp_closed(k))))
        lead = sum(1 for o in mine if str(o.get("i", "")).startswith(("W403-", "W413-")))
        if lead != len(V["ext"]):
            probs.append("all: %s EXT lead strands %d, its kind wants %d" % (tag, lead, len(V["ext"])))
        if sum(1 for o in mine if o["k"] == "p") < 140 or sum(1 for o in mine if str(o.get("i", "")).startswith("MBW-")) != MR.stats()["wires"]:
            probs.append("all: %s is not drawn in detail (pads / underside wires missing)" % tag)
    return probs


if __name__ == "__main__":
    d, rep = build()
    pr = check(d)
    print("model3d:", rep)
    for p in pr[:40]:
        print("  !", p)
    print("problems:", len(pr))
    sys.exit(1 if pr else 0)
