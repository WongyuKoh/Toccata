"""Toccata - where every final part goes, drawn from the CAD solids (page tab '06 부품·사용처').

    python3 hardware/mechanical/cad/src/locate.py              # everything (about 1-2 min)
    python3 hardware/mechanical/cad/src/locate.py --no-detail  # base frames + overlays only
    python3 hardware/mechanical/cad/src/locate.py i014 p-KEY-C # only these detail figures (+ frames / overlays)

Reads (never writes) the CAD: build_all.collect() (in memory - build_all.main() is NOT called, it would wipe stl/print),
drawings.py (sections / projections / sheet primitives), body.py (screw rows of wood_screws(), the pod cavity, the grille and
driver screw frames), manifest.json (print files) and docs/report/toccata-v4/data/final_items.json (the final item list).

Writes docs/report/toccata-v4/fin/loc/:
  base_plan.svg   top view in use state with the lids L / R, the screen lid and the touchscreen removed (internals show);
                  hidden surfaces removed with a z-buffer of the solids' upward faces (0.4 mm cells), outlines vectorised
  base_side.svg   section x = XS (centre of the white key E4) through the key action and the rear unit, over a light
                  silhouette of the whole instrument seen from the left
  base_front.svg  section y = YF through the centre unit and both speaker boxes, over a light silhouette seen from the front
  overlays.json   frames (viewBox <-> world mapping) + one entry per final item / print file / plywood piece: highlighted shapes
                  in each frame (projection of the matched solids, all instances merged into one path), instance centres,
                  counts, bbox, CAD ids (for the 3D tab), representative instance, x rule for module parts, detail figure
  detail/<key>.svg  enlarged figure around one representative instance: a top view with everything above the part lifted off
                  (cut at the part's top) and a section through the part's centre, neighbours for context, the part in red,
                  leader + label, world coordinates of the instance and its size from the solid

Frames (mm; world: x across from the A0 left end, y from the white-key front lip toward the back, z up from the desk):
  plan : X = x, Y = -y        side : X = y, Y = -z        front : X = x, Y = -z
Nothing is typed by hand: shapes and numbers come from the solids or from the generator constants they were built with.
Parts the CAD does not model (wood / board / grille / driver screws, washers, hall sensors, the polyester fill space) are drawn
from those constants (body.wood_screws(), AMP_HOLES, board posts, GR_HOLES, DRV_PIL, SENSOR_YZ, POD.cavity()) and are marked
derived=true ('자리 계산') in the JSON.
"""
import collections
import html
import json
import math
import os
import re
import sys
import time

import cv2
import numpy as np
from manifold3d import CrossSection, FillRule, JoinType, OpType

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
CAD = os.path.normpath(os.path.join(HERE, ".."))
PAGE = os.path.join(ROOT, "docs", "report", "toccata-v4")
OUT = os.path.join(PAGE, "fin", "loc")
DET = os.path.join(OUT, "detail")
ITEMS = os.path.join(PAGE, "data", "final_items.json")
PIDX = os.path.join(PAGE, "fin", "parts", "index.json")
REL = "fin/loc/"

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))

import build_all          # noqa: E402  (collect() only)
import body as B          # noqa: E402
import cadlib as CL       # noqa: E402
import drawings as D      # noqa: E402

LID_IDS = ("LID-L", "LID-R", "CU-SCREENLID")
MOD0, MODP = 47.0, 164.5   # module Ok starts at x = 47 + 164.5 (k - 1)


def fnum(v, nd=2):
    return D.fnum(v, nd)


def esc(s):
    return html.escape(str(s), quote=True)


def num(v):
    s = "%.1f" % v
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


# ------------------------------------------------------------------ derived (not modelled) instances


class XPart:
    """an instance the CAD does not model, drawn from the generator constants (same interface as a build_all Part)."""

    def __init__(self, id, name_ko, solid, how, group="자리 계산 (모델에 없음)", kind="derived", material=""):
        self.id, self.name_ko, self.solid, self.how = id, name_ko, solid, how
        self.group, self.kind, self.material = group, kind, material
        self.note, self.name_en, self.color, self.dims, self.source = "", "", "", None, "locate.py"
        self.print_solid = self.print_folder = self.print_name = self.print_note = self.print_key = None


def is_derived(p):
    return isinstance(p, XPart)


def _centre(M, pid):
    b = M.bb(M.by[pid])
    return ((b[0] + b[3]) / 2.0, (b[1] + b[4]) / 2.0, (b[2] + b[5]) / 2.0), b


def derived_sets(M):
    """{name: [XPart]} for the screws / washers / sensors / fill space the CAD leaves out."""
    S = collections.OrderedDict()
    rows = B.wood_screws()

    def screw(row, i, name, how):
        ax, (a, b_) = row["axis"], row["at"]
        h0, h1 = sorted((row["head"], row["tip"]))
        m = {"z": CL.cyl_z, "y": CL.cyl_y, "x": CL.cyl_x}[ax](a, b_, h0, h1, row["d"])
        return XPart("X-%s-%02d" % (name, i + 1), row["label"], m, how)

    feet = [r for r in rows if r["kind"] == "foot"]
    S["foot_screw"] = [screw(r, i, "FOOTSCREW", "body.wood_screws(): 고무발 자리 (x%s, y%s), 머리 z%s → 끝 z%s, Ø%s"
                             % (fnum(r["at"][0]), fnum(r["at"][1]), fnum(r["head"]), fnum(r["tip"]), fnum(r["d"], 1)))
                       for i, r in enumerate(feet)]
    csk = [r for r in rows if r["kind"] == "csk"]
    S["csk"] = [screw(r, i, "CSK", "body.wood_screws(): %s (x%s, y%s), 머리 z%s → 끝 z%s"
                      % (r["label"], fnum(r["at"][0]), fnum(r["at"][1]), fnum(r["head"]), fnum(r["tip"])))
                for i, r in enumerate(csk)]
    pan = [r for r in rows if r["kind"] == "pan"]
    S["shelf_screw"] = [screw(r, i, "SHELFSCREW", "body.wood_screws(): %s (x%s, 축 z%s), 머리 y%s → 끝 y%s"
                              % (r["label"], fnum(r["at"][0]), fnum(r["at"][1]), fnum(r["head"]), fnum(r["tip"])))
                        for i, r in enumerate(pan)]
    wf = []
    for i, r in enumerate(feet):
        x, y = r["at"]
        wf.append(XPart("X-WASHER-FOOT-%02d" % (i + 1), "M4 평와셔 Ø9 × 0.5 (고무발 %d 나사 머리 밑)" % (i + 1),
                        CL.cyl_z(x, y, r["head"] - 0.5, r["head"], 9.0),
                        "고무발 자리 (x%s, y%s) 머리 면 z%s 밑 0.5 (자리 표시)" % (fnum(x), fnum(y), fnum(r["head"]))))
    for side in "LR":
        for k in (1, 2):
            bolt, grom = M.by["BRK2-%s-BOLT%d" % (side, k)], M.by["BRK2-%s-GROM%d" % (side, k)]
            bb, gb = M.bb(bolt), M.bb(grom)
            cx, cz = (bb[0] + bb[3]) / 2.0, (bb[2] + bb[5]) / 2.0
            wf.append(XPart("X-WASHER-BRK-%s%d" % (side, k), "M4 평와셔 Ø9 × 0.5 (방진 브래킷 %s M3×20 %d 머리 밑)" % (side, k),
                            CL.cyl_y(cx, cz, gb[4], gb[4] + 0.5, 9.0),
                            "볼트 %s 축 (x%s, z%s), 그로밋 뒤 면 y%s 위 0.5 (자리 표시)" % (bolt.id, fnum(cx), fnum(cz), fnum(gb[4]))))
    S["washer"] = wf
    gs = []
    for side in "LR":
        for j, (px, ps) in enumerate(B.GR_HOLES):
            m = B.sl(CL.cyl_y(px, ps, -B.GR_W[1], 19.0 - B.GR_W[1], 4.2), B.DRV_X[side])
            gs.append(XPart("X-GRILLESCREW-%s%d" % (side, j + 1), "직결피스 8호 19 (그릴 %s %d)" % (side, j + 1), m,
                            "body.GR_HOLES: 유닛 중심 x%s %+.0f, 경사 s %+.0f · 머리 = 그릴 판 바깥 w%s, 앞판 안 %s"
                            % (fnum(B.DRV_X[side]), px, ps, fnum(B.GR_W[1]), fnum(19.0 - B.GR_W[1]))))
    S["grille_screw"] = gs
    ds = []
    for j, (px, ps) in enumerate(B.DRV_PIL):
        mL = B.sl(CL.cyl_y(px, ps, -(B.DRV_SCREW[1] + B.DRV_SCREW[2]), B.DRV_SCREW_IN, 4.0), B.DRV_X["L"])
        for side, m in (("L", mL), ("R", B.mx(mL))):
            ds.append(XPart("X-DRVSCREW-%s%d" % (side, j + 1), "M4×12 (스피커 유닛 %s 플랜지 %d)" % (side, j + 1), m,
                            "body.DRV_PIL: PCD %s · 머리 = 플랜지 %s + 가스켓 %s 앞, 앞판 안 %s (인서트 L69)"
                            % (fnum(B.DRV_PCD), fnum(B.DRV_SCREW[1]), fnum(B.DRV_SCREW[2]), fnum(B.DRV_SCREW_IN))))
    S["driver_screw"] = sorted(ds, key=lambda p: p.id)

    def post_screw(pid, d, board_t, name, label):
        (cx, cy, _), b = _centre(M, pid)
        head = b[5] + board_t
        return XPart("X-%s-%s" % (name, pid), "%s (%s 위 %s)" % ("M2.5×6" if d < 2.8 else "M3×6", pid, label), CL.cyl_z(cx, cy, head - 6.0, head, d),
                     "받침 기둥 %s (x%s, y%s) 윗면 z%s + 기판 %s → 머리 z%s, 끝 z%s" % (pid, fnum(cx), fnum(cy), fnum(b[5]), fnum(board_t, 1), fnum(head), fnum(head - 6.0)))

    S["pi_screw"] = [post_screw("CU-POST-PI-%d" % k, 2.5, 1.6, "PISCREW", "Pi 5") for k in range(1, 5)]
    bs = [post_screw("CU-POST-BUCK-%d" % k, 3.0, 1.6, "M3X6", "강압 모듈") for k in range(1, 5)]
    bs += [post_screw("CU-POST-J702-%d" % k, 3.0, 1.6, "M3X6", "J702 기판") for k in (1, 2)]
    bs += [post_screw("CU-POST-PED-%d" % k, 3.0, 1.6, "M3X6", "페달 보드") for k in (1, 2)]
    amp = M.bb(M.by["CU-E-AMP"])
    for k, (x, y) in enumerate(B.AMP_HOLES):
        head = amp[2] + 1.6
        bs.append(XPart("X-M3X6-AMP-%d" % (k + 1), "M3×6 (앰프 구멍 %d)" % (k + 1), CL.cyl_z(x, y, head - 6.0, head, 3.0),
                        "body.AMP_HOLES (x%s, y%s) · 앰프 기판 z%s~%s → 머리 z%s, 끝 z%s" % (fnum(x), fnum(y), fnum(amp[2]), fnum(head), fnum(head), fnum(head - 6.0))))
    S["board_screw"] = bs
    hs = []
    sy, sz = B.SENSOR_YZ
    for p in M.parts:
        if "-MAGNET-" in p.id and p.note not in ("altview", "offdesk"):
            b = M.bb(p)
            cx = (b[0] + b[3]) / 2.0
            hs.append(XPart("X-HALL-" + p.id.replace("-MAGNET-", "-"), "홀센서 (%s 밑)" % p.id,
                            CL.box(cx - 2.0, cx + 2.0, sy - 1.5, sy + 1.5, sz - 0.75, sz + 0.75),
                            "자석 %s 중심 x%s 바로 밑 · body.SENSOR_YZ = (y%s, z%s) · 몸통 4 × 3 × 1.5 = TO-92(LPG) 표준 크기"
                            % (p.id, fnum(cx), fnum(sy), fnum(sz))))
    S["hall"] = hs
    cav = []
    for side in "LR":
        x0, x1 = M.bb(M.by["SPK%s-PLY-SIDEOUT" % side]), M.bb(M.by["SPK%s-PLY-SIDEIN" % side])
        xa, xb = (x0[3], x1[0]) if side == "L" else (x1[3], x0[0])
        cav.append(XPart("X-FILL-%s" % side, "스피커 상자 %s 안 공간 (흡음솜 자리)" % side, CL.prism_x(B.POD.cavity(), xa, xb),
                         "body.POD.cavity() (y-z 다각형) × x%s~%s (옆판 안쪽 면 사이)" % (fnum(xa), fnum(xb))))
    S["fill"] = cav
    return S


# ------------------------------------------------------------------ entries


def white_material(m):
    return "흰색" in (m or "")


def module_k(pid):
    m = re.match(r"(?:X-HALL-)?O(\d)-", pid)
    return int(m.group(1)) if m else None


def slug(s):
    return re.sub(r"[^A-Za-z0-9._~-]", "", s).strip("-") or "x"


class Entry:
    def __init__(self, key, group, name):
        self.key, self.group, self.name = key, group, name
        self.inst = []        # highlighted instances (CAD parts and / or XPart)
        self.host = []        # parts the item is applied to / mounted on (lighter highlight)
        self.kind = "none"    # cad / derived / cad+derived / host / none
        self.where_note = ""
        self.extra = {}
        self.item = None
        self.sec = None       # detail panel B: (axis, c, why) to cut somewhere else than the representative's centre
        self.det_lines = []   # extra note lines for the detail figure (numbers measured on the solids)
        self.sec_mark = None  # panel B call-out: dict(pts=[(u, v), ...] in the cut plane, at=(u, v) label centre, label=str)


BOARDS_ALL = r"(O\d-E-SB|O\d-E-MB|E[LR]-E-BOARD|CU-E-PEDBOARD|CU-E-J702BOARD|CU-E-J501BOARD)$"
PLYS = r"(SPK[LR]-PLY-(SIDEOUT|BACK|TOP|BOTTOM)|CU-PLY-(BACK|BOTTOM))$"
HOST = {
    "i063": (r"((O\d|EL|ER)-STEEL-.*)$", "레버 강철 블록 앞 윗면(또는 건반 앞) — 누르는 힘이 47~55 g을 벗어난 건반에만 붙입니다"),
    "i069": (r".*-B-upstoppad-.*$", "업스톱 패드 밑, 패드 바 쐐기 사이에 끼웁니다"),
    "i006": (r"(O\d-E-SB|O\d-E-MB|E[LR]-E-BOARD|CU-E-PEDBOARD)$", "센서 기판 SB·EL·ER(센서마다 1), 제어 기판 MB·페달 보드(전원 1)에 납땜합니다. 페달 센서 1개는 페달 안"),
    "i007": (r"(O\d-E-SB|E[LR]-E-BOARD)$", "센서 기판 SB 3V3 버스 양 끝 2개씩, EL·ER 기판 1개씩"),
    "i008": (r"(E[LR]-E-BOARD)$", "끝 부속 기판 EL(R401~R403)·ER(R411) 아랫면"),
    "i024": (r"(O\d-E-MB|O\d-E-SB|CU-E-PEDBOARD|CU-E-J501BOARD)$", "가닥으로 갈라 제어 기판·센서 기판 배선과 페달 잭 → 페달 보드 선(W502)에 씁니다"),
    "i005": (r"(O\d-E-MUX|O\d-E-ZERO|CU-E-PEDZERO)$", "먹스 모듈·RP2040-Zero 밑 — 핀 헤더로 제어 기판에 세웁니다"),
    "i029": (r"(CU-E-J702BOARD|CU-E-PEDBOARD)$", "J702 기판 R701·R702, 페달 보드 R501 (+ 페달 안 센서 R551)"),
    "i031": (r"(O1-E-MB|O7-E-MB|CU-E-PEDBOARD)$", "제어 기판 O1(R301~R303)·O7(R301), 페달 보드 R502"),
    "i032": (r"(CU-E-PEDBOARD)$", "페달 보드 R503 자리 (5개 병렬)"),
    "i010": (r"(CU-E-J702BOARD)$", "J702 기판 C701~C704"),
    "i080": (r"(CU-E-PI5)$", "Pi 5 칩 4곳 윗면"),
    "i092": (r"(CU-E-PI5)$", "Pi 5 뒷면 microSD 슬롯"),
    "u02": (r"(C-XT60)$", "충전할 때만 배터리 윗면의 XT60 짝을 뽑고 충전기 XT60 수를 배터리 암에 꽂습니다 (충전기는 악기 밖)"),
    "i038": (r"(EL-E-J701|CU-E-DONGLE|CU-E-J702)$", "헤드폰 잭 J701(왼쪽 볼) ↔ 동글, 잭 노멀 접점 ↔ J702 — 선 경로는 조립 때 정합니다"),
    "i013": (r"(CU-E-J501)$", "뒤판 출력물의 페달 잭 J501 ↔ 바닥의 페달"),
    "i204": (r"(TS-C-DSI)$", "B형 리본(TS-C-DSI) 자리 — B형이 맞지 않을 때만 대신 씁니다"),
    "i070": (r".*-FELTSTRIP-.*$", "레버 캐리어 밑 펠트 띠의 캡스턴이 닿는 면"),
    "i071": (r"((O\d|EL|ER)-STEEL-.*|SPK[LR]-BAFFLE|CU-PLY-END-[LR]|CU-POST-.*|SEAM-POSTRAIL-\d|XT60-CLIP-[LR]|CU-E-J501BOARD)$",
             "강철 블록 88개 접착, 스피커 앞판 둘레 밀봉, 끝벽·받침 기둥·이음 레일·XT60 집게·J501 기판 붙이기, 고무발 나사 구멍"),
    "i057": (PLYS, "합판 10조각의 이음 (스피커 상자 바깥 옆판·아랫판·뒤판·윗판, 가운데 아랫판·뒤판)"),
    "i012": (r"(.*-MAGNET-.*|CU-MAG-.*)$", "건반 자석 Ø5 88개, 뚜껑 자석 Ø8 12개 포켓"),
    "i025": (r"(C-XT60.*|C-XH-[LR]|C-PWR-IN|C-PWR-FUSE)$", "XT60 표시(전원 빨강·스피커 파랑 + SPK), 끝 부속 리드 ↔ JST-XH 이음, 퓨즈 홀더 선 이음"),
    "i026": (r"(O\d-E-ZERO|CU-E-PEDZERO|TS-CRADLE)$", "RP2040-Zero 8개 밑, 화면 받침 안 리본 누름 패드 자리"),
    "i027": (r"(O\d-C-USB|O\d-C-EXT|C-USB-PED)$", "모듈 USB 선·EXT 리드를 모듈 뒷벽에 묶음 (+ 페달 안 선)"),
    "i028": (BOARDS_ALL, "센서 기판·제어 기판·끝 부속 기판·페달 보드·잭 기판 납땜 전체"),
    "i040": (r"((O\d|EL|ER)-EVA|PB-E-HUB)$", "모듈·끝 부속 밑 EVA 바닥, F칸 뒤판의 USB 허브"),
    "t06": (r"((O\d|EL|ER)-(STEEL|LEVER)-.*)$", "강철 블록과 레버 캐리어 접착면"),
    "t07": (PLYS, "목공본드가 굳는 동안 합판 이음을 누릅니다"),
    "t08": (r".*-SPRING-.*$", "토션 스프링을 레버 허브에 밀어 넣을 때"),
    "t09": (r".*-RESTFELT-.*$", "쉼 펠트 밑 (건반마다 2장)"),
    "i109": (r"(CU-E-J501)$", "페달은 바닥에 둡니다. 악기와는 뒤판 페달 잭 J501로만 이어집니다"),
    "i221": (r"(CU-BATFRAME|BAT-LFP)$", "배터리 틀 앞·뒤 벽 아래의 끈 구멍으로 배터리를 밑과 위로 감아 묶습니다"),   # note rewritten from the solid
}
# host-only items that are a real part (not a shapeless material): their own count note instead of '모양이 없는 재료'
HOST_PART_NOTE = {"i221": "CAD에 끈 모양이 없어 감는 자리(배터리 틀 CU-BATFRAME + 배터리 BAT-LFP)를 주황으로 표시합니다 — 끈 1개"}


def strap_holes(M):
    """the strap slots of the battery frame, measured on the solid: wall slab at z25 minus slab just above the floor gives the
    slot footprints (x, y); a y-section through each slot (floor .. z25) gives its height. Returns [(x0, x1, y0, y1, z0, z1), ...] front first."""
    p = M.by.get("CU-BATFRAME")
    if p is None:
        return []
    s = p.solid
    b = s.bounding_box()
    out = []
    try:
        foot = D.sec(s, "z", 25.0) - D.sec(s, "z", b[2] + 0.5)
        for c in foot.decompose():
            if c.area() < 1.0:
                continue
            x0, y0, x1, y1 = c.bounds()
            g = D.rect_cs(x0, x1, b[2], 25.0) - D.sec(s, "y", (y0 + y1) / 2.0)    # the wall is solid at z25 over the slot
            zz = [cc.bounds() for cc in g.decompose() if cc.area() > 0.5]
            if not zz:
                continue
            z0, z1 = min(q[1] for q in zz), max(q[3] for q in zz)
            out.append(tuple(round(v, 2) for v in (x0, x1, y0, y1, z0, z1)))
    except Exception:
        return []
    return sorted(out, key=lambda t: t[2])


def dropped_map(items):
    """dropped item id -> the kept item that replaces it (final_items.json 'dropped' with replaced_by in the kept list)."""
    kept = {it["id"] for it in items.get("items", [])}
    return {d["id"]: d["replaced_by"] for d in items.get("dropped", []) if d.get("replaced_by") in kept}


def map_ids(text, repl):
    """CAD print notes still name a few item ids the final list merged into another item (i068 bushing cloth = i062)."""
    if not text or not repl:
        return text
    return re.sub(r"\b(" + "|".join(map(re.escape, repl)) + r")\b", lambda m: repl[m.group(1)], text)


DERIVED_FOR = {"i004": "hall", "i053": "foot_screw", "i055": "grille_screw", "i212": "driver_screw", "i219": "csk",
               "i220": "shelf_screw", "i060": "washer", "i052": "fill", "i050": "pi_screw", "i059": "board_screw"}
HOST_FOR_DERIVED = {
    "i004": (r"((O\d|EL|ER)-SENSORBAR|O\d-E-SB|E[LR]-E-BOARD)$", "센서 바 포켓(y67), 건반 자석 바로 밑 — 다리는 센서 기판에 납땜"),
    "i053": (r"FOOT-\d+$", "고무발 14개 가운데 (아래에서 조임)"),
    "i060": (r"(FOOT-\d+|BRK2-[LR]-GROM\d)$", "고무발 나사 머리 밑 14, 방진 브래킷 M3×20 머리 밑 4"),
    "i055": (r"SPK[LR]-GRILLE$", "그릴 옆벽 4곳 → 스피커 앞판 파일럿"),
    "i212": (r"(SPK-[LR]|SPK[LR]-INS-\d)$", "스피커 유닛 플랜지 → 앞판 M4 인서트"),
    "i219": (r"(CU-BATFRAME|PR-BACKPLATE)$", "배터리 틀 4곳 + 뒤판 출력물 바닥 탭 2곳 → 가운데 아랫판"),
    "i220": (r"PR-HUBSHELF$", "허브 선반 받침 2곳 → 가운데 뒤판 안쪽 면"),
    "i052": (r"SPK-[LR]$", "스피커 상자 안 전체 (유닛 뒤 10 mm와 폴 벤트 축은 비움)"),
    "i050": (r"(CU-POST-PI-\d|TS-M25-\d)$", "Pi 5 받침 기둥 4 + 화면 네 귀 4"),
    "i059": (r"(O\d-B-controlboardscrew.*|CU-POST-(BUCK|J702|PED)-\d|PR-HUBSHELF)$", "제어 기판 14 + 강압 4·J702 2·페달 보드 2·앰프 4"),
}


def build_entries(M, items, manifest, X):
    parts = M.parts
    E = collections.OrderedDict()

    def match(rx, keep_alt=False):
        r = re.compile(rx)
        return [p for p in parts if r.match(p.id) and (keep_alt or p.note != "altview")]

    for it in items["items"]:
        iid = it["id"]
        e = Entry(iid, "item", it["name"])
        e.item = it
        cm = it.get("cad_match") or {}
        inst = [M.by[i] for i in (cm.get("ids") or []) if i in M.by and M.by[i].note != "altview"]
        e.inst = list(inst)
        e.kind = "cad" if inst else "none"
        if iid in DERIVED_FOR:
            e.inst += X[DERIVED_FOR[iid]]
            e.kind = "cad+derived" if inst else "derived"
            rx, note = HOST_FOR_DERIVED.get(iid, (None, ""))
            if rx:
                ii = set(q.id for q in e.inst)
                e.host = [p for p in match(rx) if p.id not in ii and p.note != "offdesk"]
            e.where_note = note
        elif not inst and iid in HOST:
            rx, note = HOST[iid]
            e.host = match(rx)
            e.kind = "host" if e.host else "none"
            e.where_note = note
        elif inst and iid in HOST:          # e.g. the pedal: its solid is off the desk, show where it plugs in
            rx, note = HOST[iid]
            e.host = match(rx)
            e.where_note = note
        if iid in ("i087", "i088", "i089"):
            white = iid in ("i087", "i088")
            e.host = [p for p in parts if p.kind == "print" and p.note != "altview" and white_material(p.material) == white
                      and not (p.print_folder or "").startswith("@")]
            e.kind = "host"
            e.where_note = ("흰색 출력물 (흰 건반 52개)" if white else
                            "흰색이 아닌 출력물 (흑건·프레임·레버 캐리어·센서 바·패드 바·가림판·뒷바·터치스크린 출력물)")
        if iid == "i221" and e.host:
            sl = strap_holes(M)
            if sl:
                x0, x1, _, _, z0, z1 = sl[0]
                walls = " · ".join("y%s~%s" % (fnum(q[2]), fnum(q[3])) for q in sl)
                e.where_note = ("배터리 틀 앞·뒤 벽 아래 끈 구멍 %d곳 (%s × %s, x%s~%s, z%s~%s, 벽 %s)으로 끈을 넣어 배터리 밑과 위를 감습니다"
                                % (len(sl), fnum(x1 - x0), fnum(z1 - z0), fnum(x0), fnum(x1), fnum(z0), fnum(z1), walls))
                e.sec = ("x", round((x0 + x1) / 2.0, 2), "끈 구멍 가운데")
                bp = M.bb(M.by["CU-BATFRAME"])
                e.sec_mark = dict(pts=[((q[2] + q[3]) / 2.0, (q[4] + q[5]) / 2.0) for q in sl],
                                  at=((sl[0][2] + sl[-1][3]) / 2.0, bp[2] - 6.0),
                                  label="끈 구멍 %s × %s · z%s~%s" % (fnum(x1 - x0), fnum(z1 - z0), fnum(z0), fnum(z1)))
                e.det_lines = ["끈 구멍 %s × %s (가로 x × 높이 z): x%s~%s, z%s~%s — 앞 벽과 뒤 벽(%s)에 하나씩, 배터리 틀 입체에서 잼"
                               % (fnum(x1 - x0), fnum(z1 - z0), fnum(x0), fnum(x1), fnum(z0), fnum(z1), walls),
                               "끈(폭 20 이하)은 앞 구멍 → 배터리 밑 → 뒤 구멍 → 배터리 위로 한 바퀴 감아 찍찍이로 붙입니다 (CAD에 끈 모양은 없음)"]
        if it["source"] == "tool" or iid in ("u07", "i090"):
            e.inst, e.host, e.kind = [], [], "none"
        E[iid] = e
    repl = dropped_map(items)
    # printed parts: instrument print files of the manifest (folders 01..05, 07)
    for pe in manifest["print"]:
        ids = [i for i in (pe.get("ids") or []) if i in M.by and M.by[i].note != "altview"]
        if pe["folder"].startswith("@") or not ids:
            continue
        sk = slug(re.sub(r"^O\d-", "", ids[0]).replace("칸", "k").replace("왼쪽", "L").replace("오른쪽", "R"))
        key, n = "p-" + sk, 2
        while key in E:
            key, n = "p-%s-%d" % (sk, n), n + 1
        e = Entry(key, "print", pe.get("name_ko") or pe["name"].replace("_", " "))
        e.inst = [M.by[i] for i in ids]
        e.kind = "cad"
        e.extra = dict(file=pe["file"], name=pe["name"], qty=pe["qty"], folder=pe["folder"], size_mm=pe["size_mm"],
                       volume_cm3=pe.get("volume_cm3"), mass_g=pe.get("mass_g_solid_petg"), material=pe.get("material"),
                       note=map_ids(pe.get("note", ""), repl))
        E[key] = e
    # plywood pieces (the D06 slots: one entry per L / R pair or single piece)
    for slot, rx in D.PLY_SLOTS:
        r = re.compile(rx)
        ps = [p for p in parts if p.kind == "plywood" and r.search(p.id)]
        if not ps:
            continue
        key = "ply-" + slot.lower().replace("ply-", "")
        e = Entry(key, "plywood", D.pair_name(ps))
        e.inst = ps
        e.kind = "cad"
        b = [M.bb(p) for p in ps]
        ext = sorted([b[0][3] - b[0][0], b[0][4] - b[0][1], b[0][5] - b[0][2]])
        e.extra = dict(qty=len(ps), size_mm=[round(ext[2], 2), round(ext[1], 2), round(ext[0], 2)], ids=[p.id for p in ps])
        E[key] = e
    return E


# ------------------------------------------------------------------ 2D helpers

FRAMES = collections.OrderedDict([
    ("plan", dict(win=(-22.0, 1242.0, -6.0, 348.0), axis="z", map="X = x, Y = -y", look="위에서 봄 (연주자 쪽 = 아래)")),
    ("side", dict(win=(-8.0, 350.0, -4.0, 196.0), axis="x", map="X = y, Y = -z", look="왼쪽에서 봄 (연주자 쪽 = 왼쪽)")),
    ("front", dict(win=(-22.0, 1242.0, -4.0, 196.0), axis="y", map="X = x, Y = -z", look="앞에서 봄")),
])


def vb_of(win):
    u0, u1, v0, v1 = win
    return [u0, -v1, u1 - u0, v1 - v0]


class GeoCache:
    def __init__(self, M):
        self.M = M
        self.pc = {}
        self.tc = {}

    def proj(self, p, axis):
        k = (p.id, axis)
        cs = self.pc.get(k)
        if cs is None:
            cs = self.pc[k] = D.proj(p.solid, axis)
        return cs

    def up_tris(self, p, m=None):
        """upward-facing triangles (n, 3, 3) of the solid (or of m, uncached)."""
        if m is None:
            t = self.tc.get(p.id)
            if t is not None:
                return t
        mg = (m if m is not None else p.solid).to_mesh()
        V = np.asarray(mg.vert_properties, dtype=np.float64)[:, :3]
        T = np.asarray(mg.tri_verts, dtype=np.int64)
        if len(T) == 0:
            t = np.zeros((0, 3, 3))
        else:
            a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
            nz = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
            k = nz > 1e-7
            t = np.stack([a[k], b[k], c[k]], 1)
        if m is None:
            self.tc[p.id] = t
        return t


def qnum(v, q):
    return num(round(v / q) * q) if q else num(v)


def cs_path(cs, tol=0.0, mapf=None, q=0.0):
    """CrossSection -> SVG path. Default frame mapping X = u, Y = -v (world units, rounded to q mm when q > 0);
    mapf(u, v) -> (X, Y) for sheets."""
    if tol:
        cs = cs.simplify(tol)
    out = []
    for p in cs.to_polygons():
        if len(p) < 3:
            continue
        q_, last = [], None
        for u, v in p:
            if mapf:
                X, Y = mapf(u, v)
                t = ("%.2f" % X, "%.2f" % Y)
            else:
                t = (qnum(u, q), qnum(-v, q))
            if t != last:
                q_.append(t)
                last = t
        if len(q_) >= 3 and q_[0] == q_[-1]:
            q_.pop()
        if len(q_) >= 3:
            out.append("M" + " ".join("%s %s" % t for t in q_) + "Z")
    return "".join(out)


def union_cs(css):
    css = [c for c in css if c is not None and not c.is_empty()]
    if not css:
        return CrossSection()
    if len(css) == 1:
        return css[0]
    return CrossSection.batch_boolean(css, OpType.Add)


def bb_frame(b, frame):
    if frame == "plan":
        return (b[0], b[1], b[3], b[4])
    if frame == "side":
        return (b[1], b[2], b[4], b[5])
    return (b[0], b[2], b[3], b[5])


def zbuffer(G, parts, win, res, cut=None):
    """top-view z-buffer of the parts' upward faces (each triangle at its highest z, drawn low -> high).
    cut: everything above z = cut is lifted off (solids trimmed). Returns (id buffer, parts list used)."""
    u0, u1, v0, v1 = win
    W, H = int(math.ceil((u1 - u0) / res)), int(math.ceil((v1 - v0) / res))
    P, Z, O, used = [], [], [], []
    for p in parts:
        b = G.M.bb(p)
        if b[3] < u0 or b[0] > u1 or b[4] < v0 or b[1] > v1:
            continue
        if cut is not None and b[2] >= cut - 0.25:      # parts starting at (or within 0.25 under) the cut are 'above'
            continue
        if cut is not None and b[5] > cut:
            t = G.up_tris(p, p.solid.trim_by_plane((0.0, 0.0, -1.0), -cut))
        else:
            t = G.up_tris(p)
        if len(t) == 0:
            continue
        idx = len(used)
        used.append(p)
        P.append(t)
        Z.append(t[:, :, 2].max(1))
        O.append(np.full(len(t), idx, np.int32))
    buf = np.full((H, W), -1, np.int32)
    if not P:
        return buf, used
    P, Z, O = np.concatenate(P), np.concatenate(Z), np.concatenate(O)
    SH = 4
    px = np.empty((len(P), 3, 2), np.int32)
    px[:, :, 0] = np.round((P[:, :, 0] - u0) / res * (1 << SH)).astype(np.int32)
    px[:, :, 1] = np.round((v1 - P[:, :, 1]) / res * (1 << SH)).astype(np.int32)
    lim = 1 << 28
    np.clip(px, -lim, lim, out=px)
    for i in np.argsort(Z, kind="stable"):
        cv2.fillConvexPoly(buf, px[i], int(O[i]), lineType=cv2.LINE_8, shift=SH)
    return buf, used


def regions(buf, win, res, b=None):
    """id buffer -> {index: CrossSection of the visible region (world coords)}."""
    u0, u1, v0, v1 = win
    out = {}
    ids = np.unique(buf)
    for idx in ids:
        if idx < 0:
            continue
        mask = (buf == idx).astype(np.uint8)
        cnts, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        polys = []
        for c in cnts:
            c = c.reshape(-1, 2)
            if len(c) < 3:
                if len(c) >= 1:
                    cc, rr = c[:, 0].mean(), c[:, 1].mean()
                    c = np.array([[cc - 0.5, rr - 0.5], [cc + 0.5, rr - 0.5], [cc + 0.5, rr + 0.5], [cc - 0.5, rr + 0.5]])
                else:
                    continue
            polys.append([(u0 + (x + 0.5) * res, v1 - (y + 0.5) * res) for x, y in c])
        if not polys:
            continue
        cs = CrossSection(polys, FillRule.EvenOdd).offset(0.5 * res, JoinType.Miter).simplify(0.35 * res)
        if not cs.is_empty():
            out[int(idx)] = cs
    return out


# ------------------------------------------------------------------ base frames

BASE_CSS = """
.kw{fill:#fdfdfb;stroke:#8f98a6}.kb{fill:#b7bcc4;stroke:#7d8592}.pr{fill:#eceef2;stroke:#97a0ad}.wd{fill:#f2eadb;stroke:#a6957a}
.el{fill:#e2ece4;stroke:#8fa595}.mt{fill:#d8dce2;stroke:#8c95a2}.rb{fill:#cfd2d7;stroke:#8c95a2}.cb{fill:#efe2bd;stroke:#b39b5a}
.sil{fill:#f3f4f6;stroke:#c3c9d3}
.sec .kw,.sec .kb,.sec .pr,.sec .wd,.sec .el,.sec .mt,.sec .rb,.sec .cb{stroke:#5b6578}
.sec .kw{fill:#f6f6f2}.sec .kb{fill:#9aa0a9}.sec .pr{fill:#dde3eb}.sec .wd{fill:#ead9bd}.sec .el{fill:#cfe3d4}.sec .mt{fill:#c3c8d1}
.sec .rb{fill:#8d929a}.sec .cb{fill:#e3c66f}
path{stroke-width:.6px;vector-effect:non-scaling-stroke;stroke-linejoin:round}
"""


def bcls(p):
    if p.kind == "plywood":
        return "wd"
    if p.kind == "print":
        if "-KEY-" in p.id:
            return "kb" if "흑건" in p.group else "kw"
        return "pr"
    if p.kind == "electronics":
        if re.search(r"(^C-|-C-|^TS-C-)", p.id):
            return "cb"
        return "el"
    if p.kind == "consumable" or any(k in (p.material or "") for k in ("고무", "실리콘", "EVA")):
        return "rb"
    return "mt"


ORDER = {"wd": 0, "pr": 1, "kw": 2, "kb": 3, "rb": 4, "el": 5, "mt": 6, "cb": 7}


def use_state(M):
    return [p for p in M.parts if p.note not in ("altview", "offdesk") and not is_derived(p)]


def plan_base_parts(M):
    out = []
    for p in use_state(M):
        if p.id in LID_IDS or p.id.startswith("CU-MAG-LID"):
            continue
        if p.group == "터치스크린" and p.id != "TS-RCLIP":
            continue
        if bcls(p) == "cb":
            continue
        out.append(p)
    return out


def svg_open(vb, title, extra=""):
    x, y, w, h = vb
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s" width="%d" height="%d"%s>'
            % (num(x), num(y), num(w), num(h), round(w * 2), round(h * 2), extra) + "<title>%s</title>" % esc(title))


PLAN_RES = 0.4


def base_plan(M, G, X, log):
    win = FRAMES["plan"]["win"]
    pp = plan_base_parts(M)
    buf, used = zbuffer(G, pp, win, PLAN_RES)
    reg = regions(buf, win, PLAN_RES)
    cnt = collections.Counter(buf.ravel().tolist())
    vis = {}
    for i, p in enumerate(used):
        a = G.proj(p, "z").area()
        vis[p.id] = min(1.0, cnt.get(i, 0) * PLAN_RES * PLAN_RES / a) if a > 0 else 0.0
    rows = sorted(((G.M.bb(used[i])[5], ORDER[bcls(used[i])], used[i], cs) for i, cs in reg.items()), key=lambda t: (t[0], t[1]))
    body = ['<g class="base">'] + ['<path class="%s" d="%s"/>' % (bcls(p), cs_path(cs)) for _, _, p, cs in rows] + ["</g>"]
    meta = ' data-frame="plan" data-map="%s" data-world="%s"' % (FRAMES["plan"]["map"], " ".join(num(v) for v in win))
    s = svg_open(vb_of(win), "Toccata 위에서 본 배치 — 뚜껑 L·R, 화면 뚜껑, 터치스크린을 뗀 모습", meta) + \
        "<defs><style>%s</style></defs>" % BASE_CSS + '<rect x="%s" y="%s" width="%s" height="%s" fill="#fff"/>' % tuple(num(v) for v in vb_of(win)) + \
        "".join(body) + "</svg>"
    # visibility of everything else (cables, lids, screen, derived) against the same base: second buffer with them included
    ppi = set(p.id for p in pp)
    extra = [p for p in use_state(M) if p.id not in ppi] + [p for v in X.values() for p in v]
    buf2, used2 = zbuffer(G, pp + extra, win, PLAN_RES)
    cnt2 = collections.Counter(buf2.ravel().tolist())
    for i, p in enumerate(used2):
        if p.id in vis:
            continue
        a = G.proj(p, "z").area()
        vis[p.id] = min(1.0, cnt2.get(i, 0) * PLAN_RES * PLAN_RES / a) if a > 0 else 0.0
    log("base_plan: %d of %d parts visible from above, %d bytes" % (len(reg), len(pp), len(s)))
    return s, vis


def section_items(M, parts, axis, c, win=None):
    i = "xyz".index(axis)
    ui, vi = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    out = []
    for p in parts:
        b = M.bb(p)
        if not (b[i] < c < b[i + 3]):
            continue
        if win is not None and (b[ui + 3] < win[0] or b[ui] > win[1] or b[vi + 3] < win[2] or b[vi] > win[3]):
            continue
        cs = D.sec(p.solid, axis, c)
        if cs.is_empty() or cs.area() < 1e-4:
            continue
        out.append((p, cs))
    out.sort(key=lambda t: ORDER[bcls(t[0])])
    return out


def base_section(M, G, frame, c, title, log):
    F = FRAMES[frame]
    win, axis = F["win"], F["axis"]
    clip = D.rect_cs(*win)
    us = use_state(M)
    sil = union_cs([G.proj(p, axis) for p in us]) ^ clip
    secs = section_items(M, us, axis, c)
    body = ['<path class="sil" d="%s"/>' % cs_path(sil, 0.2), '<g class="sec">']
    for p, cs in secs:
        d = cs_path(cs ^ clip, 0.05)
        if d:
            body.append('<path class="%s" d="%s"/>' % (bcls(p), d))
    body.append("</g>")
    meta = ' data-frame="%s" data-map="%s" data-cut="%s=%s" data-world="%s"' % (frame, F["map"], axis, num(c), " ".join(num(v) for v in win))
    s = svg_open(vb_of(win), title, meta) + "<defs><style>%s</style></defs>" % BASE_CSS + \
        '<rect x="%s" y="%s" width="%s" height="%s" fill="#fff"/>' % tuple(num(v) for v in vb_of(win)) + "".join(body) + "</svg>"
    log("base_%s: %d sections at %s=%s, %d bytes" % (frame, len(secs), axis, fnum(c), len(s)))
    return s


# ------------------------------------------------------------------ overlays


def frame_overlay(G, parts, frame):
    if not parts:
        return None
    F = FRAMES[frame]
    win = F["win"]
    clip = D.rect_cs(*win)
    inwin = [p for p in parts if not (lambda b: b[2] < win[0] or b[0] > win[1] or b[3] < win[2] or b[1] > win[3])(bb_frame(G.M.bb(p), frame))]
    if not inwin:
        return None
    cs = union_cs([G.proj(p, F["axis"]) for p in inwin]) ^ clip
    if cs.is_empty():
        return None
    pts, seen, sizes, allb = [], set(), [], []
    for p in inwin:
        b = bb_frame(G.M.bb(p), frame)
        allb.append(b)
        cu, cv = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        sizes.append(max(b[2] - b[0], b[3] - b[1]))
        k = (round(cu), round(cv))
        if k not in seen:
            seen.add(k)
            pts.append([round(cu, 1), round(-cv, 1)])
    bb = [min(b[0] for b in allb), -max(b[3] for b in allb), max(b[2] for b in allb), -min(b[1] for b in allb)]
    q = 0.5 if frame == "side" else 1.0
    small = bool(np.median(sizes) < 14.0)
    return dict(d=cs_path(cs, 0.3 if frame == "side" else 0.6, q=q), pts=pts if (small or len(pts) <= 24) else [], np=len(pts),
                bb=[float(num(v)) for v in bb], small=small)


# ------------------------------------------------------------------ representative instance, x rule, kinds


def pick_rep(e, XS):
    ps = e.inst or e.host
    if not ps:
        return None
    o4 = [p for p in ps if module_k(p.id) == 4]
    if o4:
        es = [p for p in o4 if re.search(r"-E$", p.id)]
        return es[0] if es else min(o4, key=lambda p: abs(_cx(p) - XS))
    real = [p for p in ps if not is_derived(p) and p.note != "offdesk"]
    if not real:                      # only computed instances: keep their list order (e.g. foot washers before bracket washers)
        return ps[0]
    return sorted(real, key=lambda p: (_cx(p), p.id))[0]


_BB = {}


def _cx(p):
    b = _BB.get(p.id) or tuple(p.solid.bounding_box())
    _BB[p.id] = b
    return (b[0] + b[3]) / 2.0


def x_rule(M, ps, rep):
    """module parts: x of the representative as 47 + 164.5 (k - 1) + dx, and whether every module repeats the same offsets."""
    k = module_k(rep.id)
    if k is None:
        return None
    by = collections.defaultdict(list)
    for p in ps:
        kk = module_k(p.id)
        if kk is not None:
            b = M.bb(p)
            by[kk].append(round((b[0] + b[3]) / 2.0 - (MOD0 + MODP * (kk - 1)), 2))
    for v in by.values():
        v.sort()
    ref = by[k]
    same = all(len(v) == len(ref) and all(abs(a - b) < 0.02 for a, b in zip(v, ref)) for v in by.values())
    b = M.bb(rep)
    dx = (b[0] + b[3]) / 2.0 - (MOD0 + MODP * (k - 1))
    mods = sorted(by)
    return dict(k=k, dx=round(dx, 2), per_module=len(ref), modules=mods, same=bool(same),
                text="x = 47 + 164.5(k-1) + %s" % fnum(dx), offsets=ref if len(ref) <= 16 else None)


def kinds_of(ps):
    c = collections.OrderedDict()
    for p in ps:
        n = D.short(p.name_ko)
        n = re.sub(r"\s*\((?:[A-G]s?|[A-G]#?)\d\)$", "", n)
        c[n] = c.get(n, 0) + 1
    return [[k, v] for k, v in c.items()]


# ------------------------------------------------------------------ detail figures

DCSS = D.CSS + """
.Zkw{fill:#fbfbf8;stroke:#7d8592;stroke-width:.16}.Zkb{fill:#aab0b9;stroke:#5d6672;stroke-width:.16}.Zpr{fill:#e6eaf0;stroke:#7d8592;stroke-width:.16}
.Zwd{fill:#efe4d0;stroke:#8a7a5e;stroke-width:.16}.Zel{fill:#dbe9df;stroke:#6f8a77;stroke-width:.16}.Zmt{fill:#d2d7de;stroke:#6f7887;stroke-width:.14}
.Zrb{fill:#c4c8ce;stroke:#6f7887;stroke-width:.14}.Zcb{fill:#efdca4;stroke:#9a8240;stroke-width:.12}
.Skw{fill:#f4f4ee;stroke:#1d2433;stroke-width:.3}.Skb{fill:#8e95a0;stroke:#1d2433;stroke-width:.3}.Spr{fill:url(#hp);stroke:#1d2433;stroke-width:.3}
.Swd{fill:url(#hw);stroke:#1d2433;stroke-width:.3}.Sel{fill:url(#he);stroke:#1d2433;stroke-width:.26}.Smt{fill:url(#hm);stroke:#1d2433;stroke-width:.24}
.Srb{fill:#7d828b;stroke:#1d2433;stroke-width:.22}.Scb{fill:#e3b23c;stroke:#6b5a1e;stroke-width:.16}
.HL{fill:#B3342D;fill-opacity:.88;stroke:#6e1c17;stroke-width:.3;stroke-linejoin:round}
.HLs{fill:#B3342D;stroke:#5a1511;stroke-width:.32;stroke-linejoin:round}
.HL2{fill:#B3342D;fill-opacity:.32;stroke:#B3342D;stroke-width:.2}
.HLp{fill:#B3342D;fill-opacity:.14;stroke:#B3342D;stroke-width:.3;stroke-dasharray:1.2 .7}
.HH{fill:#d9822b;fill-opacity:.35;stroke:#a35a12;stroke-width:.22}
.vf{fill:none;stroke:#8a96ab;stroke-width:.25}
.lead{fill:none;stroke:#6e1c17;stroke-width:.3}
.tl{fill:#6e1c17}
.nb{fill:#5b6578}
"""
SW = 120.0          # detail sheet width (sheet units; the page scales it)
T1, T2, T3 = 4.2, 3.3, 2.9


class Mini(D.Sheet):
    def __init__(self, w, h):
        self.code, self.file, self.name, self.scale_txt = "LOC", "", "", ""
        self.w, self.h = w, h
        self.L = {k: [] for k in D.LAYERS}
        self.tboxes, self.used, self.views, self.defs = [], set(), [], []

    def svg_doc(self, title):
        W, H = self.w, self.h
        s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%d" height="%d">' % (num(W), num(H), round(W * 5), round(H * 5)),
             "<title>%s</title>" % esc(title), "<defs><style>%s</style>%s%s</defs>" % (DCSS, D.DEFS, "".join(self.defs)),
             '<rect class="bg" x="0" y="0" width="%s" height="%s"/>' % (num(W), num(H))]
        for k in D.LAYERS:
            s.append('<g class="L-%s">' % k)
            s.extend(self.L[k])
            s.append("</g>")
        s.append("</svg>")
        return "\n".join(s)


def nice_step(span):
    for s in (1, 2, 5, 10, 20, 25, 50, 100, 200):
        if span / s <= 4.5:
            return s
    return 500


def fit_window(b, margin_min, aspect=(0.42, 1.05), lim=None):
    """world window (u0, u1, v0, v1) around a 2D bbox b = (u0, v0, u1, v1) with margins, clamped aspect h/w."""
    u0, v0, u1, v1 = b
    wu, wv = max(u1 - u0, 1.0), max(v1 - v0, 1.0)
    m = max(margin_min, 0.25 * max(wu, wv))
    U0, U1, V0, V1 = u0 - m, u1 + m, v0 - m, v1 + m
    W_, H_ = U1 - U0, V1 - V0
    if H_ / W_ < aspect[0]:
        d = aspect[0] * W_ - H_
        V0, V1 = V0 - d / 2, V1 + d / 2
    elif H_ / W_ > aspect[1]:
        d = H_ / aspect[1] - W_
        U0, U1 = U0 - d / 2, U1 + d / 2
    return (U0, U1, V0, V1)


class Panel:
    def __init__(self, sh, win, X0, Y0, wv):
        self.sh, self.win = sh, win
        self.k = wv / (win[1] - win[0])
        self.X0, self.Y0 = X0, Y0
        self.w = wv
        self.h = self.k * (win[3] - win[2])
        self.cid = "c%d" % len(sh.defs)
        sh.defs.append('<clipPath id="%s"><rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"/></clipPath>' % (self.cid, X0, Y0, self.w, self.h))

    def P(self, u, v):
        return (self.X0 + self.k * (u - self.win[0]), self.Y0 + self.k * (self.win[3] - v))

    def area(self, cs, cls, layer="geo", tol=0.0):
        d = cs_path(cs, tol, self.P)
        if d:
            self.sh.add(layer, '<path class="%s" fill-rule="evenodd" d="%s" clip-path="url(#%s)"/>' % (cls, d, self.cid))

    def frame(self):
        self.sh.rect(self.X0, self.Y0, self.X0 + self.w, self.Y0 + self.h, "vf", "over")


def _inner(cs):
    pt = D.best_inner(cs)
    return pt


def detail_figure(e, M, G, XS, xr, label_name):
    """two panels: top view cut at the part's top / section through the part's centre."""
    rep = e.rep
    ps_hi = e.inst if e.inst else e.host
    hi_mode = "item" if e.inst else "host"
    others = [p for p in ps_hi if p.id != rep.id]
    b = M.bb(rep)
    cx, cy, cz = (b[0] + b[3]) / 2.0, (b[1] + b[4]) / 2.0, (b[2] + b[5]) / 2.0
    us = use_state(M)
    offdesk = rep.note == "offdesk"
    ctx = [] if offdesk else us
    sh = Mini(SW, 400.0)
    ML, MR = 17.0, 3.0
    VW = SW - ML - MR
    y = 7.0
    sh.text(3.0, y, label_name, T1, bold=True, halo=False, check=False)
    y += 5.2
    sub = "대표 자리 %s" % rep.id + (" · 전체 %d곳" % len(ps_hi) if len(ps_hi) > 1 else "")
    if hi_mode == "host":
        sub = "쓰는 자리 · " + sub
    sh.text(3.0, y, sub, T3, cls="tm", halo=False, check=False)
    y += 4.5
    # ---------------- panel A: top view, everything above the part's top lifted off
    cut = b[5] + 0.01
    win = fit_window((b[0], b[1], b[3], b[4]), 18.0)
    sh.text(3.0, y + 3.0, "① 위에서 본 자리 — z%s 위 부품은 걷어 냄" % fnum(b[5]), T2, bold=True, halo=False, check=False)
    y += 6.0
    A = Panel(sh, win, ML, y, VW)
    res = max((win[1] - win[0]) / 700.0, 0.05)
    hi_ids = set(p.id for p in ps_hi)
    near = [p for p in ctx if p.id not in hi_ids]
    buf, used = zbuffer(G, near + list(ps_hi), win, res, cut=cut)
    reg = regions(buf, win, res)
    rows = sorted(((M.bb(used[i])[5], ORDER[bcls(used[i])], used[i], cs) for i, cs in reg.items()), key=lambda t: (t[0], t[1]))
    nb_items = []
    for _, _, p, cs in rows:
        if p.id in hi_ids:
            continue
        A.area(cs, "Z" + bcls(p))
        nb_items.append((cs.area(), p, cs))
    for p in others:
        pb = M.bb(p)
        if pb[3] < win[0] or pb[0] > win[1] or pb[4] < win[2] or pb[1] > win[3]:
            continue
        A.area(G.proj(p, "z") ^ D.rect_cs(*win), "HL2", "over")
    if hi_mode == "item":
        for p in e.host:
            pb = M.bb(p)
            if pb[3] < win[0] or pb[0] > win[1] or pb[4] < win[2] or pb[1] > win[3]:
                continue
            A.area(G.proj(p, "z") ^ D.rect_cs(*win), "HH", "over")
    rp = G.proj(rep, "z")
    A.area(rp, "HL" if hi_mode == "item" else "HH", "over")
    A.frame()
    xa_, ya_ = A.P(b[0], b[4])
    xb_, yb_ = A.P(b[3], b[1])
    item_box = (xa_ - 1.0, ya_ - 1.0, xb_ + 1.0, yb_ + 1.0)
    _marks(sh, A, rep, b, "plan", label_name if len(label_name) <= 22 else label_name[:21] + "…")
    # neighbour names (largest visible pieces, no overlaps)
    for _, p, cs in sorted(nb_items, key=lambda t: -t[0])[:5]:
        pt = _inner(cs)
        if not pt or pt[2] * A.k < 2.2:
            continue
        X_, Y_ = A.P(pt[0], pt[1])
        nm = D.short(p.name_ko)
        nm = re.sub(r"\s*\([^)]*\)$", "", nm)
        if len(nm) > 18:
            nm = nm[:17] + "…"
        box = (X_ - D.text_w(nm, T3) / 2 - 0.4, Y_ + 1.0 - 0.78 * T3 - 0.3, X_ + D.text_w(nm, T3) / 2 + 0.4, Y_ + 1.0 + 0.22 * T3 + 0.3)
        if box[0] < A.X0 + 1 or box[2] > A.X0 + A.w - 1 or box[1] < A.Y0 + 1 or box[3] > A.Y0 + A.h - 1:
            continue
        if any(box[0] < q[2] and q[0] < box[2] and box[1] < q[3] and q[1] < box[3] for q, _ in sh.tboxes + [(item_box, "")]):
            continue
        sh.text(X_, Y_ + 1.0, nm, T3, "middle", cls="nb")
    y = A.Y0 + A.h + 12.5
    # ---------------- panel B: section through the part's centre
    ka = D.is_ka(rep) or rep.id.startswith("X-HALL-")
    if e.sec:                                   # cut where the item is used (e.g. through the battery strap slot)
        axis = e.sec[0]
    elif ka or rep.id.startswith("TS-"):         # key action and the tilted screen read best from the side
        axis = "x"
    else:
        ax_ = D.sec(rep.solid, "x", cx).area() if b[0] < cx < b[3] else 0.0
        ay_ = D.sec(rep.solid, "y", cy).area() if b[1] < cy < b[4] else 0.0
        axis = "x" if ax_ * 1.5 >= ay_ else "y"
    c = cx if axis == "x" else cy
    if e.sec:
        c = e.sec[1]
    if axis == "x":
        bu = (b[1], b[2], b[4], b[5])
        title = "② 옆 단면 x = %s (%s왼쪽에서 봄, 연주자 쪽 = 왼쪽)" % (fnum(c), (e.sec[2] + ", ") if e.sec else "")
        uname, vname = "y", "z"
    else:
        bu = (b[0], b[2], b[3], b[5])
        title = "② 앞 단면 y = %s (앞에서 봄)" % fnum(c)
        uname, vname = "x", "z"
    win2 = fit_window(bu, 18.0, aspect=(0.42, 0.95))
    sh.text(3.0, y + 3.0, title, T2, bold=True, halo=False, check=False)
    y += 6.0
    Bp = Panel(sh, win2, ML, y, VW)
    secs = section_items(M, [p for p in ctx if p.id not in hi_ids], axis, c, win2)
    clip2 = D.rect_cs(*win2)
    for p, cs in secs:
        Bp.area(cs ^ clip2, "S" + bcls(p))
    pax = "x" if axis == "x" else "y"
    for p in others:
        pb = M.bb(p)
        i = "xyz".index(axis)
        if pb[i] < c < pb[i + 3]:
            cs = D.sec(p.solid, axis, c) ^ clip2
            if not cs.is_empty():
                Bp.area(cs, "HL2", "over")
    if hi_mode == "item":
        for p in e.host:
            pb = M.bb(p)
            i = "xyz".index(axis)
            if pb[i] < c < pb[i + 3]:
                cs = D.sec(p.solid, axis, c) ^ clip2
                if not cs.is_empty():
                    Bp.area(cs, "HH", "over")
    Bp.area(G.proj(rep, pax) ^ clip2, "HLp", "over")
    rs = D.sec(rep.solid, axis, c) ^ clip2
    if not rs.is_empty():
        Bp.area(rs, "HLs" if hi_mode == "item" else "HH", "over")
    Bp.frame()
    if axis == "x":
        xa_, ya_ = Bp.P(b[1], b[5])
        xb_, yb_ = Bp.P(b[4], b[2])
    else:
        xa_, ya_ = Bp.P(b[0], b[5])
        xb_, yb_ = Bp.P(b[3], b[2])
    item_box = (xa_ - 1.0, ya_ - 1.0, xb_ + 1.0, yb_ + 1.0)
    _marks(sh, Bp, rep, b, "side" if axis == "x" else "front", None)
    if e.sec_mark:                              # e.g. the battery strap slots in the cut
        sm = e.sec_mark
        TX_, TY_ = Bp.P(*sm["at"])
        tw = D.text_w(sm["label"], T3)
        for u_, v_ in sm["pts"]:
            X_, Y_ = Bp.P(u_, v_)
            ex = TX_ - tw / 2 - 0.6 if X_ < TX_ else TX_ + tw / 2 + 0.6
            sh.add("lead", '<path class="lead" d="M%.2f %.2f L%.2f %.2f"/>' % (X_, Y_, ex, TY_ - 0.9))
            sh.circle(X_, Y_, 0.6, "tl", "lead")
        sh.text(TX_, TY_, sm["label"], T3, "middle", cls="tl", bold=True)
    for p, cs in sorted(secs, key=lambda t: -t[1].area())[:4]:
        pt = _inner(cs ^ clip2)
        if not pt or pt[2] * Bp.k < 2.0:
            continue
        X_, Y_ = Bp.P(pt[0], pt[1])
        nm = re.sub(r"\s*\([^)]*\)$", "", D.short(p.name_ko))
        if len(nm) > 18:
            nm = nm[:17] + "…"
        box = (X_ - D.text_w(nm, T3) / 2 - 0.4, Y_ + 1.0 - 0.78 * T3 - 0.3, X_ + D.text_w(nm, T3) / 2 + 0.4, Y_ + 1.0 + 0.22 * T3 + 0.3)
        if box[0] < Bp.X0 + 1 or box[2] > Bp.X0 + Bp.w - 1 or box[1] < Bp.Y0 + 1 or box[3] > Bp.Y0 + Bp.h - 1:
            continue
        if any(box[0] < q[2] and q[0] < box[2] and box[1] < q[3] and q[1] < box[3] for q, _ in sh.tboxes + [(item_box, "")]):
            continue
        sh.text(X_, Y_ + 1.0, nm, T3, "middle", cls="nb")
    y = Bp.Y0 + Bp.h + 12.5
    # ---------------- notes
    lines = []
    lines.append("대표 자리 중심 (x %s, y %s, z %s) · 바깥 크기 %s × %s × %s (x·y·z, 입체 상자)"
                 % (fnum(cx), fnum(cy), fnum(cz), fnum(b[3] - b[0]), fnum(b[4] - b[1]), fnum(b[5] - b[2])))
    if xr:
        lines.append("모듈 O%d: %s (k = %s%s)" % (xr["k"], xr["text"], "·".join(str(k) for k in xr["modules"]),
                                                ", 모듈마다 같은 자리 %d곳" % xr["per_module"] if xr["same"] else ""))
    if is_derived(rep):
        lines.append("모델에 없는 부품: " + rep.how)
    if offdesk:
        lines.append("악기 밖(바닥)에 두는 부품이라 주변 부품 없이 그렸습니다.")
    lines.extend(e.det_lines)
    lines.append(("빨간 면 = 이 물건 (진한 = 대표, 연한 = 같은 물건의 다른 자리)" if hi_mode == "item" else "주황 = 쓰는 자리") + " · 빨간 점선 = 단면 밖 부분" + (" · 주황 = 붙는 자리" if (e.host and hi_mode == "item") else "") + " · 숫자는 mm, CAD 입체에서 계산")
    for ln in lines:
        for wl in sh.wrap(ln, SW - 6.0, T3):
            sh.text(3.0, y, wl, T3, halo=False, check=False)
            y += T3 * 1.42
    sh.h = y + 2.0
    issues = [b_ for b_ in sh.check() if not b_.startswith("outside")]
    return sh.svg_doc("%s — 자리 상세" % label_name), axis, c, issues


def _marks(sh, Pn, rep, b, frame, label):
    """coordinates of the representative (ticks on the panel edges), its size dims, a leader + label and a scale bar."""
    if frame == "plan":
        u0, v0, u1, v1, un, vn = b[0], b[1], b[3], b[4], "x", "y"
    elif frame == "side":
        u0, v0, u1, v1, un, vn = b[1], b[2], b[4], b[5], "y", "z"
    else:
        u0, v0, u1, v1, un, vn = b[0], b[2], b[3], b[5], "x", "z"
    cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    w = Pn.win
    X, Y = Pn.P(cu, cv)
    xb = Pn.Y0 + Pn.h
    # centre ticks + labels on the bottom / left edges
    X = min(max(X, Pn.X0), Pn.X0 + Pn.w)
    Y = min(max(Y, Pn.Y0), Pn.Y0 + Pn.h)
    sh.line([(X, xb), (X, xb + 1.8)], "dm", "dim")
    sh.text(X, xb + 5.2, "%s %s" % (un, fnum(cu)), T3, "middle", cls="td")
    sh.line([(Pn.X0 - 1.8, Y), (Pn.X0, Y)], "dm", "dim")
    sh.text(Pn.X0 - 2.4, Y + 1.0, "%s %s" % (vn, fnum(cv)), T3, "end", cls="td")
    # window edge coordinates (scale reference)
    sh.text(Pn.X0, xb + 9.4, "%s %s" % (un, fnum(w[0], 1)), T3 - 0.4, "start", cls="tm", halo=False, check=False)
    sh.text(Pn.X0 + Pn.w, xb + 9.4, "%s %s" % (un, fnum(w[1], 1)), T3 - 0.4, "end", cls="tm", halo=False, check=False)
    # size dims of the representative (only when they fit)
    Xa, Ya = Pn.P(u0, v1)
    Xb, Yb = Pn.P(u1, v0)
    span_u, span_v = Xb - Xa, Yb - Ya
    if span_u >= 6.0:
        yd = Ya - 2.4
        if yd < Pn.Y0 + 3.0:
            yd = Yb + 3.4
        if yd < Pn.Y0 + Pn.h - 1.0:
            sh.dim_h(Xa, Xb, yd, fnum(u1 - u0), ext=[(Xa, Ya if yd < Ya else Yb), (Xb, Ya if yd < Ya else Yb)], size=T3)
    if span_v >= 6.0:
        xd = Xb + 2.6
        if xd > Pn.X0 + Pn.w - 3.0:
            xd = Xa - 2.6
        if xd > Pn.X0 + 1.0:
            sh.dim_v(Ya, Yb, xd, fnum(v1 - v0), ext=[(Xb if xd > Xb else Xa, Ya), (Xb if xd > Xb else Xa, Yb)], size=T3)
    # leader + label to the top-left / top-right corner (away from the part)
    if label:
        left = X > Pn.X0 + Pn.w / 2
        tx = Pn.X0 + 2.0 if left else Pn.X0 + Pn.w - 2.0
        ty = Pn.Y0 + 5.0
        tw = D.text_w(label, T2)
        x_end = tx + tw if left else tx - tw
        sh.add("lead", '<path class="lead" d="M%.2f %.2f L%.2f %.2f L%.2f %.2f"/>' % (X, Y, x_end + (1.0 if left else -1.0), ty + 1.2, x_end, ty + 1.2))
        sh.circle(X, Y, 0.6, "tl", "lead")
        sh.text(tx, ty, label, T2, "start" if left else "end", cls="tl", bold=True)
    # scale bar (bottom-right inside)
    step = nice_step((w[1] - w[0]) / 3.0)
    L_ = step * Pn.k
    bx, by = Pn.X0 + Pn.w - 2.0 - L_, Pn.Y0 + Pn.h - 2.6
    sh.rect(bx, by, bx + L_, by + 0.9, "seca", "over")
    sh.text(bx + L_ / 2, by - 0.8, "%s mm" % fnum(step), T3 - 0.4, "middle", cls="tm", check=False)


# ------------------------------------------------------------------ main


def count_note(e):
    n_real = sum(1 for p in e.inst if not is_derived(p))
    n_der = sum(1 for p in e.inst if is_derived(p))
    it = e.item
    if e.group == "plywood":
        q = e.extra.get("qty")
        return "CAD에 %d조각 = 재단 개수 %s" % (len(e.inst), q) if q == len(e.inst) else "CAD에 %d조각, 재단 개수 %s" % (len(e.inst), q)
    if e.group != "item":
        q = e.extra.get("qty")
        return "CAD에 %d곳 = 출력 개수 %s" % (len(e.inst), q) if q == len(e.inst) else "CAD에 %d곳, 출력 개수 %s" % (len(e.inst), q)
    need, unit = it["qty_need"], it.get("unit") or ""
    if e.kind == "cad":
        if n_real == need:
            return "CAD에 %d곳 — 필요 개수와 같습니다" % n_real
        return "CAD 조각 %d곳 — 필요 %s %s: %s" % (n_real, fnum(need, 2), unit, it.get("need_note") or "")
    if e.kind in ("derived", "cad+derived"):
        s = ("CAD %d곳 + 계산한 자리 %d곳 = %d" % (n_real, n_der, n_real + n_der)) if n_real else ("계산한 자리 %d곳" % n_der)
        tot = n_real + n_der
        if tot == need:
            return s + " — 필요 개수와 같습니다"
        return s + " — 필요 %s %s: %s" % (fnum(need, 2), unit, it.get("need_note") or "")
    if e.kind == "host":
        if e.key in HOST_PART_NOTE:
            return HOST_PART_NOTE[e.key]
        return "모양이 없는 재료라 쓰는 자리(%d곳)를 표시합니다" % len(e.host)
    return ""


def load_pidx():
    """part drawing codes written by the part-drawings step (fin/parts/index.json, optional):
    ({print file 'stl/print/..': code}, {CAD id: code})."""
    if not os.path.exists(PIDX):
        return {}, {}
    try:
        d = json.load(open(PIDX, encoding="utf-8"))
    except Exception:
        return {}, {}
    by_file, by_id = {}, {}

    def norm(f):
        return re.sub(r"^hardware/mechanical/cad/", "", f or "")

    for f, c in (d.get("by_file") or {}).items():
        if isinstance(c, str):
            by_file[norm(f)] = c
    for r in d.get("parts") or []:
        c = r.get("code")
        if not c:
            continue
        if r.get("file"):
            by_file.setdefault(norm(r["file"]), c)
        for i in r.get("ids") or []:
            by_id.setdefault(i, c)
    return by_file, by_id


def main(argv):
    t0 = time.time()
    do_detail = "--no-detail" not in argv
    only = [a for a in argv if not a.startswith("--")]
    lines = []

    def log(s):
        lines.append(s)
        print(s, flush=True)

    os.makedirs(DET, exist_ok=True)
    parts = build_all.collect()
    M = D.Model(parts)
    G = GeoCache(M)
    log("collect: %d parts in %.1f s" % (len(parts), time.time() - t0))
    items = json.load(open(ITEMS, encoding="utf-8"))
    manifest = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
    X = derived_sets(M)
    for v in X.values():
        for p in v:
            M.by[p.id] = p
    log("derived: " + ", ".join("%s %d" % (k, len(v)) for k, v in X.items()))
    E = build_entries(M, items, manifest, X)
    log("entries: %d (%s)" % (len(E), ", ".join("%s %d" % (g, sum(1 for e in E.values() if e.group == g)) for g in ("item", "print", "plywood"))))

    b = M.bb(M.by["O4-KEY-E"])
    XS = round((b[0] + b[3]) / 2.0, 2)
    YF = 300.0
    plan_svg, vis = base_plan(M, G, X, log)
    side_svg = base_section(M, G, "side", XS, "Toccata 옆 단면 x %s (흰 건반 E4 가운데)" % fnum(XS), log)
    front_svg = base_section(M, G, "front", YF, "Toccata 앞 단면 y %s (가운데 유닛·스피커 상자)" % fnum(YF), log)
    for nm, s in (("base_plan.svg", plan_svg), ("base_side.svg", side_svg), ("base_front.svg", front_svg)):
        with open(os.path.join(OUT, nm), "w", encoding="utf-8") as f:
            f.write(s)

    pfile, pid = load_pidx()
    out_entries = collections.OrderedDict()
    det_n = 0
    overl = []
    t1 = time.time()
    for key, e in E.items():
        e.rep = pick_rep(e, XS)
        rec = dict(group=e.group, kind=e.kind, name=e.name)
        real = [p for p in e.inst if not is_derived(p)]
        der = [p for p in e.inst if is_derived(p)]
        rec["count"] = len(e.inst)
        rec["count_cad"] = len(real)
        rec["count_derived"] = len(der)
        rec["ids"] = [p.id for p in real] or [p.id for p in e.host if not is_derived(p)]
        if der:
            rec["derived_how"] = [p.how for p in der[:3]]
        if e.host:
            rec["host_ids"] = [p.id for p in e.host]
            rec["host_kinds"] = kinds_of(e.host)
        rec["kinds"] = kinds_of(e.inst) if (e.inst and e.group == "item") else []
        rec["where_note"] = e.where_note
        rec["count_note"] = count_note(e)
        fr, hfr = {}, {}
        for f in FRAMES:
            o = frame_overlay(G, [p for p in e.inst if p.note != "offdesk"], f)
            if o:
                fr[f] = o
            if e.host:
                h = frame_overlay(G, [p for p in e.host if p.note != "offdesk"], f)
                if h:
                    hfr[f] = h
        rec["frames"] = fr
        if hfr:
            rec["host_frames"] = hfr
        vv = [vis.get(p.id) for p in e.inst if vis.get(p.id) is not None]
        if vv:
            aa = [G.proj(p, "z").area() for p in e.inst if vis.get(p.id) is not None]
            rec["vis"] = round(float(sum(v * a for v, a in zip(vv, aa)) / max(sum(aa), 1e-9)), 3)
        if any(p.group == "터치스크린" or p.id in LID_IDS or p.id.startswith("CU-MAG-LID") for p in e.inst):
            rec["removed_in_plan"] = True
        if any(p.note == "offdesk" for p in e.inst):
            rec["offdesk"] = True
        if e.rep is not None:
            rb = M.bb(e.rep)
            xr = x_rule(M, e.inst or e.host, e.rep)
            rec["rep"] = dict(id=e.rep.id, name=e.rep.name_ko, c=[round((rb[i] + rb[i + 3]) / 2.0, 2) for i in range(3)],
                              bb=[round(v, 2) for v in rb], derived=is_derived(e.rep))
            if xr:
                rec["xrule"] = xr
            if do_detail and (not only or key in only):
                label = e.name if e.group != "item" else e.item["name"]
                svg, axis, c, iss = detail_figure(e, M, G, XS, xr, label)
                if iss:
                    overl.append((key, iss))
                fn = re.sub(r"[^A-Za-z0-9._~-]", "_", key) + ".svg"
                with open(os.path.join(DET, fn), "w", encoding="utf-8") as f:
                    f.write(svg)
                det_n += 1
            fn = re.sub(r"[^A-Za-z0-9._~-]", "_", key) + ".svg"
            if os.path.exists(os.path.join(DET, fn)):
                rec["detail"] = REL + "detail/" + fn
        if e.group != "item":
            rec.update({k: v for k, v in e.extra.items() if k not in ("ids",)})
            codes = []
            for c in [pfile.get(e.extra.get("file", ""))] + [pid.get(i) for i in rec["ids"]]:
                if c and c not in codes:
                    codes.append(c)
            if codes:
                rec["partdwg"] = codes
        out_entries[key] = rec
    log("entries done in %.1f s, %d detail figures, %d with text overlaps" % (time.time() - t1, det_n, len(overl)))
    for k_, iss in overl[:40]:
        log("   overlap %s: %s" % (k_, "; ".join(iss[:3])))

    frames = collections.OrderedDict()
    for f, F in FRAMES.items():
        frames[f] = dict(src=REL + "base_%s.svg" % f, vb=[float(num(v)) for v in vb_of(F["win"])], map=F["map"], look=F["look"],
                         world=list(F["win"]))
    frames["side"]["cut"] = "x = %s (흰 건반 E4 가운데)" % fnum(XS)
    frames["front"]["cut"] = "y = %s (가운데 유닛·스피커 상자)" % fnum(YF)
    frames["plan"]["cut"] = "뚜껑 L·R, 화면 뚜껑, 터치스크린을 뗌"
    checks = run_checks(E, out_entries, items, manifest, log)
    doc = dict(version=1, generated=time.strftime("%Y-%m-%d"), source="hardware/mechanical/cad/src/locate.py (build_all.collect, %d parts)" % len(parts),
               units="mm", frames=frames, order=list(out_entries.keys()), entries=out_entries,
               tools=[dict(file=pe["file"], name=pe.get("name_ko") or pe["name"].replace("_", " "), folder=pe["folder"], qty=pe["qty"], size_mm=pe["size_mm"],
                           note=map_ids(pe.get("note", ""), dropped_map(items)), mass_g=pe.get("mass_g_solid_petg"), partdwg=pfile.get(pe["file"]))
                      for pe in manifest["print"] if not pe["folder"].startswith("@") and not pe.get("ids")],
               checks=checks)
    s = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "overlays.json"), "w", encoding="utf-8") as f:
        f.write(s)
    log("overlays.json: %d bytes; total %.1f s" % (len(s), time.time() - t0))
    return doc


def run_checks(E, recs, items, manifest, log):
    out = []
    for key, e in E.items():
        r = recs[key]
        if e.group == "item":
            it = e.item
            if e.kind in ("cad", "derived", "cad+derived"):
                ok = r["count"] == it["qty_need"]
                out.append(dict(key=key, need=it["qty_need"], unit=it.get("unit"), count=r["count"], ok=ok,
                                note="" if ok else (it.get("need_note") or "")))
        else:
            q = e.extra.get("qty")
            out.append(dict(key=key, need=q, unit="개", count=r["count"], ok=(q == r["count"])))
    bad = [c for c in out if not c["ok"]]
    log("checks: %d count rows, %d equal, %d differ (explained by need_note / units)" % (len(out), len(out) - len(bad), len(bad)))
    for c in bad:
        log("   differ %s: need %s %s, CAD %s — %s" % (c["key"], c["need"], c.get("unit") or "", c["count"], (c.get("note") or "")[:110]))
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
