#!/usr/bin/env python3
"""Preparation checklist data for the Toccata page, tab "07 준비 체크" (#prep).

Writes
  docs/report/toccata-v4/fin/prep/lines.json          (canonical line list, stable ids)
  docs/report/toccata-v4/src/tabs/prep/section.html   (tab fragment; the same data inline as JSON)

Line groups
  parts   A 부품      kept items of data/final_items.json (school / personal / owned / gap)
  prints  B 출력물    hardware/mechanical/cad/manifest.json - one line per STL file
                      (stl/print = needed, stl/print_extra = optional)
  make    C 가공·조립 what the maker cuts, glues, solders and assembles - every count is taken
                      from the CAD solids (build_all.collect(), in memory only) or the circuit
                      bom/cables CSV, never typed in
  tools   D 공구      items with source 'tool' (need 1 each; out of the main % unless switched on)

Stable line ids (the saved counts in the artifact db are keyed by them)
  a-<item id>   d-<item id>   c-<name>
  b-<folder no>-<sha1(folder/name)[:8]>   bx-<sha1(extra folder/name)[:8]>   (name = file name
  without the "__N개.stl" quantity, so a changed quantity keeps the id)

Run from anywhere:  python3 docs/report/toccata-v4/src/build_prep.py [--verify-stl]
  --verify-stl  also loads every STL with trimesh and checks its extents against manifest size_mm
Exits non-zero when a check fails.  Never calls build_all.main().
"""
import contextlib
import csv
import datetime
import hashlib
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.dirname(HERE)                                   # docs/report/toccata-v4
ROOT = os.path.abspath(os.path.join(PAGE, "..", "..", ".."))   # repo root
CAD = os.path.join(ROOT, "hardware", "mechanical", "cad")
CAD_SRC = os.path.join(CAD, "src")
NET = os.path.join(ROOT, "hardware", "pcb", "netlist")
ITEMS = os.path.join(PAGE, "data", "final_items.json")
OUT_DIR = os.path.join(PAGE, "fin", "prep")
OUT_JSON = os.path.join(OUT_DIR, "lines.json")
TAB_DIR = os.path.join(PAGE, "src", "tabs", "prep")
OUT_SECTION = os.path.join(TAB_DIR, "section.html")

ERRORS = []
CHECKS = []


def err(msg):
    ERRORS.append(msg)
    print("ERROR", msg)


def ok(msg):
    CHECKS.append(msg)
    print("ok   ", msg)


def num(x):
    """22.0 -> '22', 22.04 -> '22.04', 139.65 -> '139.65' (no rounding beyond 2 decimals)."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s


def dims(vals):
    return " × ".join(num(v) for v in vals)


# ---------------------------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------------------------
def cad_parts():
    sys.path.insert(0, CAD_SRC)
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))
    import build_all  # noqa: E402  (collect() only - never main())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        parts = build_all.collect()
    return parts


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------------------------
# A + D: items
# ---------------------------------------------------------------------------------------------
SRC_CHIP = {"school": "학교 지원", "personal": "사비",
            "owned": "가진 것", "gap": "준비처 없음", "tool": "가진 공구"}


def first_sentence(t, limit=70):
    t = (t or "").strip()
    m = re.match(r"(.+?(?:니다|요)\.)\s", t + " ")
    s = m.group(1) if m else t
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def item_lines(items_doc):
    items = items_doc["items"]
    issues = {}
    for iss in items_doc.get("issues", []):
        issues.setdefault(iss["id"], []).append(iss)
    aircon_note = None
    if "aircon" in issues:
        aircon_note = None

    cats = [c for c in items_doc["cat_order"] if c != "공구"]
    subs_a = [{"id": f"parts-{i + 1}", "name": c} for i, c in enumerate(cats)]
    sub_of = {c: f"parts-{i + 1}" for i, c in enumerate(cats)}
    lines_a, lines_d = [], []
    for it in items:
        src = it["source"]
        o = it.get("ordered")
        unit = it["unit"]
        meta = []
        if o:
            units = o.get("units") or o.get("qty")
            meta.append(f"주문 {units}{' ' if unit == 'm' else ''}{unit}")
            if o.get("store"):
                meta.append(o["store"])
        details = []
        if it.get("where"):
            details.append(["쓰는 곳", it["where"]])
        if it.get("need_note"):
            details.append(["필요 수", it["need_note"]])
        if it.get("pack_note"):
            details.append(["남는 것", it["pack_note"]])
        if it.get("check_on_arrival"):
            details.append(["받으면 확인", it["check_on_arrival"]])
        warn = [i["text"] for i in issues.get(it["id"], [])]
        if src == "aircon" and aircon_note:
            warn.append(aircon_note)
        line = {
            "id": ("d-" if src == "tool" else "a-") + it["id"],
            "code": it["id"],
            "n": it["name"],
            "need": int(it["qty_need"]),
            "u": unit,
            "src": src,
            "m": " · ".join(meta),
            "d": details,
        }
        if it.get("optional"):
            line["opt"] = True
        if warn:
            line["w"] = warn
        if it.get("img"):
            line["img"] = it["img"]
        if src == "tool":
            line["g"], line["s"] = "tools", "tools-1"
            line["m"] = first_sentence(it.get("where"))
            lines_d.append(line)
        else:
            line["g"], line["s"] = "parts", sub_of[it["cat"]]
            lines_a.append(line)
    # order A by category order, keep item order inside
    order = {s["id"]: i for i, s in enumerate(subs_a)}
    lines_a.sort(key=lambda l: order[l["s"]])
    return subs_a, lines_a, lines_d, issues


# ---------------------------------------------------------------------------------------------
# B: print files
# ---------------------------------------------------------------------------------------------
B_SUBS = [
    ("01", "01 건반"), ("02", "02 레버 캐리어"), ("03", "03 프레임"),
    ("04", "04 센서 바·패드 바·가림판·마개"), ("05", "05 본체 출력물"), ("07", "07 터치스크린"),
    ("jig", "공구·지그 (06 출력 공구 · 09 기판 지그)"),
    ("extra", "선택·대안·예비 (stl/print_extra, 켜야 계산)"),
]


def print_lines(manifest, verify_stl):
    lines = []
    subs = [{"id": f"prints-{k}", "name": n} for k, n in B_SUBS]
    seen_ids = set()
    total_files = total_qty = 0
    for p in manifest["print"]:
        f = p["file"]
        top = f.split("/")[1]
        folder_dir = f.split("/")[2]
        name = p["name"]
        if top == "print":
            fno = folder_dir[:2]
            sub = "jig" if fno in ("06", "08", "09") else fno
            lid = "b-" + fno + "-" + hashlib.sha1(f"{folder_dir}/{name}".encode()).hexdigest()[:8]
            opt = False
            total_files += 1
            total_qty += p["qty"]
        elif top == "print_extra":
            sub = "extra"
            lid = "bx-" + hashlib.sha1(f"{folder_dir}/{name}".encode()).hexdigest()[:8]
            opt = True
        else:
            err(f"unknown print folder {f}")
            continue
        if lid in seen_ids:
            err(f"duplicate print id {lid} {f}")
        seen_ids.add(lid)
        # qty in the file name must equal manifest qty
        m = re.search(r"__(\d+)개\.stl$", f)
        if not m or int(m.group(1)) != p["qty"]:
            err(f"qty in file name differs from manifest: {f} vs {p['qty']}")
        base = os.path.basename(f)
        meta = [dims(p["size_mm"]) + " mm", p.get("material") or "PETG"]
        details = []
        if p.get("note"):
            details.append(["출력 메모", p["note"]])
        mass = p.get("mass_g_solid_petg")
        extra = f"속을 꽉 채운 질량 {num(mass)} g (실제 채움으로 뽑으면 더 적음)" if mass is not None else ""
        if p.get("mass_g_print_est") is not None or p.get("print_min_est") is not None:
            est = []
            if p.get("mass_g_print_est") is not None:
                est.append(f"출력 약 {num(p['mass_g_print_est'])} g")
            if p.get("print_min_est") is not None:
                est.append(f"약 {int(round(p['print_min_est']))}분")
            extra = (extra + " · " if extra else "") + ", ".join(est) + " (슬라이서 추정)"
        if extra:
            details.append(["무게", extra])
        details.append(["파일", f"hardware/mechanical/cad/{f}"])
        details = [[k, v.replace("**", "")] for k, v in details]
        line = {"id": lid, "g": "prints", "s": f"prints-{sub}", "n": p.get("name_ko") or name.replace("_", " "),
                "need": int(p["qty"]), "u": "개", "file": base,
                "fold": folder_dir.split("_")[0] if top == "print" else "선택",
                "m": " · ".join(meta), "d": details}
        if opt:
            line["opt"] = True
        lines.append(line)
    ok(f"B: stl/print {total_files} files = {total_qty} parts; print_extra {sum(1 for l in lines if l.get('opt'))} files")
    if verify_stl:
        verify_stl_files(manifest)
    return subs, lines, total_files, total_qty


def verify_stl_files(manifest):
    import trimesh  # noqa: E402
    bad = 0
    for p in manifest["print"]:
        path = os.path.join(CAD, p["file"])
        mesh = trimesh.load(path, force="mesh")
        ext = [round(float(v), 2) for v in mesh.extents]
        want = [round(float(v), 2) for v in p["size_mm"]]
        if any(abs(a - b) > 0.011 for a, b in zip(ext, want)):
            bad += 1
            err(f"STL extents {p['file']}: {ext} vs manifest {want}")
    if not bad:
        ok(f"STL extents equal manifest size_mm for all {len(manifest['print'])} files (trimesh, ±0.01)")


# ---------------------------------------------------------------------------------------------
# C: making and assembly - counts from CAD / circuit CSV
# ---------------------------------------------------------------------------------------------
def bb(p):
    b = p.solid.bounding_box()
    return [b[i + 3] - b[i] for i in range(3)]


def make_lines(parts, bom, cables, harness):
    ids = [p.id for p in parts]
    by_id = {p.id: p for p in parts}

    def cnt(rx):
        r = re.compile(rx)
        return sum(1 for i in ids if r.fullmatch(i))

    def sel(rx):
        r = re.compile(rx)
        return [p for p in parts if r.fullmatch(p.id)]

    def need(rx, expect=None, what=""):
        n = cnt(rx)
        if n <= 0:
            err(f"C: no CAD part matches {rx} ({what})")
        if expect is not None and n != expect:
            err(f"C: {what} CAD count {n} != expected {expect}")
        return n

    lines = []
    subs = [{"id": "make-metal", "name": "금속·자석"},
            {"id": "make-felt", "name": "펠트·패드 자르기"},
            {"id": "make-ply", "name": "판 잇기 (출력 판 — 10/16부터 합판 없음)"},
            {"id": "make-board", "name": "기판 만들기"},
            {"id": "make-cable", "name": "선·하네스 만들기"},
            {"id": "make-asm", "name": "조립"}]

    def add(sub, lid, name, n, unit, meta, detail=None, cad=None):
        line = {"id": "c-" + lid, "g": "make", "s": "make-" + sub, "n": name, "need": int(n), "u": unit,
                "m": meta, "d": []}
        if detail:
            line["d"].append(["하는 일", detail])
        if cad:
            line["d"].append(["셈 근거", cad])
        lines.append(line)

    # ---- 금속·자석 --------------------------------------------------------------------------
    n_steel = need(r".*-STEEL-.*", 88, "steel blocks")
    add("metal", "steel", "강철 블록 자르기 9 × 19 × 40", n_steel, "개",
        "강철 띠 9T × 19 × 1 m (i119) 4장 → 40 mm씩",
        "블록은 캐리어 칸 길이 40.0에 딱 맞으므로 40 −0.1/−0.3으로 자르고 두께 8.9~9.1만 씁니다. "
        "캐리어 칸 속 지지대를 떼고 밑에서 끼운 뒤 MS 폴리머(i071)로 붙입니다.",
        f"CAD 강철 블록 {n_steel}개 (…-STEEL-…)")

    def rod_meta(rx, what):
        ps = sel(rx)
        mods = sorted(round(max(bb(p)), 2) for p in ps if re.match(r"O\d-", p.id))
        el = [round(max(bb(p)), 2) for p in ps if p.id.startswith("EL-")]
        er = [round(max(bb(p)), 2) for p in ps if p.id.startswith("ER-")]
        if len(set(mods)) != 1 or len(el) != 1 or len(er) != 1:
            err(f"{what}: unexpected rod lengths {mods} {el} {er}")
            return "", len(ps), 0
        total = sum(mods) + el[0] + er[0]
        return (f"{num(mods[0])} × {len(mods)} · {num(el[0])} (EL) · {num(er[0])} (ER)", len(ps), total)

    km, kn, kt = rod_meta(r".*-B-keyrod.*", "key rods")
    add("metal", "keyrod", "건반 봉 자르기 Ø4", kn, "토막", km + " · 환봉 i066",
        "1 m 환봉 2개에서 자르고 끝을 줄로 다듬습니다. 밸런스 레일의 봉 받침에 놓고 건반 노치가 위에서 물립니다.",
        f"CAD 건반 봉 {kn}토막, 합 {num(kt)} mm")
    lm, ln_, lt = rod_meta(r".*-B-leverrod.*", "lever rods")
    add("metal", "leverrod", "레버 봉 자르기 Ø4", ln_, "토막", lm + " · 환봉 i067",
        "1 m 환봉 2개에서 자릅니다. 핀 보스·레버 허브·스프링 코일을 꿰고 이음 쪽 끝을 출력 마개로 막습니다.",
        f"CAD 레버 봉 {ln_}토막, 합 {num(lt)} mm")
    n_spring = need(r".*-SPRING-.*", 88, "springs")
    add("metal", "spring", "스프링 다리 자르기 22.3 / 8.0", n_spring, "개",
        "미스미 C-UA90R5-3-0.5 (i123) · 긴 다리 22.3 · 짧은 다리 8.0",
        "짧은 다리 끝부터 레버 허브 가둠 홈에 밀어 넣고, 긴 다리는 뒷벽 보스 홈(2.4 × 3.2)으로 밑에서 넣습니다. "
        "레버 봉을 넣기 전에 끼웁니다.",
        f"CAD 스프링 {n_spring}개 (…-SPRING-…)")
    n_pin = need(r".*-B-balancepin.*", 88, "balance pins")
    add("metal", "pin", "밸런스 핀 꽂기 Ø2 × 12", n_pin, "개",
        "밸런스 레일 · 핀 높이 게이지 T3로 꼭대기 z23.30 (i121)",
        "핀 높이 게이지(06 출력 공구 T3)를 대고 눌러 넣어 꼭대기 높이를 맞춥니다.",
        f"CAD 밸런스 핀 {n_pin}개")
    n_mag = need(r".*-MAGNET-.*", 88, "key magnets")
    add("metal", "magkey", "건반 자석 붙이기 Ø5 × 2", n_mag, "개",
        "건반 밑 포켓 y67 · S극이 아래 · 순간접착제 (i098, i012)",
        "포켓(Ø5.2 × 2.1)에 S극이 아래로 가게 눌러 넣고 순간접착제로 고정합니다. 페달 자석 1개는 페달 개조 줄에서 셉니다.",
        f"CAD 건반 자석 {n_mag}개 (…-MAGNET-…)")
    n_mag8 = need(r"CU-MAG-.*", 12, "lid magnets")
    add("metal", "mag8", "뚜껑 자석 붙이기 Ø8 × 3", n_mag8, "개",
        "뚜껑 L·R 밑면 6 + 뒤판·끝벽 윗모서리 6 (i099)",
        "짝끼리 극이 서로 당기게 맞춰 순간접착제로 붙입니다. 뒤판 자리(Ø8 × 3.2)는 지그 J-b로 뚫습니다.",
        f"CAD 자석 {n_mag8}개 (CU-MAG-…)")
    n_ins4a = cnt(r"SPK[LR]-INS-\d")
    n_ins4b = cnt(r"JOIN-INS-.*")
    n_ins3 = cnt(r"SEAM-INS-\d")
    if (n_ins4a, n_ins4b, n_ins3) != (8, 4, 4):
        err(f"inserts {n_ins4a} {n_ins4b} {n_ins3}")
    add("metal", "insert", "열 인서트 넣기 (인두)", n_ins4a + n_ins4b + n_ins3, "개",
        f"M4 스피커 앞판 {n_ins4a} + M4 안쪽 옆판 {n_ins4b} + M3 이음 레일 {n_ins3} (i211, i213)",
        "인두로 곧게 눌러 면까지만 넣습니다. 구멍 바닥까지 밀지 않습니다. 이음 레일은 붙이기 전에 넣습니다.",
        "CAD SPK…-INS + JOIN-INS + SEAM-INS")

    # ---- 펠트·패드 --------------------------------------------------------------------------
    def one_bb(rx):
        p = sel(rx)[0]
        return bb(p)

    n = need(r".*-RESTFELT-.*", 88, "rest felt")
    b_ = one_bb(r".*-RESTFELT-.*")
    add("felt", "restfelt", "쉼 펠트 만들기 1.5T", n, "개",
        f"펠트 1T (i107) + 0.5T 천 (i062) · {num(b_[0])} × {num(b_[1])}",
        "1T 펠트 위에 0.5T 접착 천을 한 겹 붙여 1.5T로 만들고 잘라 건반 꼬리 밑에 붙입니다. 높이는 종이 펀칭으로 맞춥니다.",
        f"CAD 쉼 펠트 {n}개")
    n = need(r".*-FELTSTRIP-.*", 88, "carrier felt strip")
    add("felt", "feltstrip", "캐리어 밑 펠트 띠 2T", n, "개",
        "메리노 2T (i106) · 폭 7 × 15.5 (y176.5~192.0)",
        "레버 캐리어 밑, 캡스턴 나사가 미는 자리에 붙입니다.",
        f"CAD 펠트 띠 {n}개")
    n = need(r".*-B-keeperfelt-.*", 88, "keeper felt")
    b_ = one_bb(r".*-B-keeperfelt-.*")
    add("felt", "keeper", "키퍼 펠트 2T", n, "개",
        f"메리노 2T (i106) · {num(b_[0])} × {num(b_[1])}",
        "키퍼 훅 밑에 붙입니다.",
        f"CAD 키퍼 펠트 {n}개")
    n = need(r".*-B-upstoppad-.*", 88, "upstop pads")
    add("felt", "upstop", "업스톱 패드 만들기", n, "개",
        "PORON 5T (i124) 6 × 12.2 + 펠트 1T (i107) → 패드 바 쐐기",
        "PORON을 6 × 12.2로 자르고 강철이 닿는 면에 펠트 1T를 겹쳐 패드 바 쐐기에 붙입니다. 높이 맞춤은 OHP 심(i069)으로 합니다.",
        f"CAD 업스톱 패드 {n}개")
    ws = sel(r".*-B-whitefrontfelt.*")
    wl = sorted({num(max(bb(p))) for p in ws}, key=float, reverse=True)
    add("felt", "frontw", "백건 앞 펠트 띠", len(ws), "개",
        f"메리노 2T + 하네나이트 1T (i125) · 폭 7.5 · 길이 {' / '.join(wl)}",
        "앞 레일에 하네나이트 1T를 먼저 깔고 그 위에 펠트 2T 띠를 붙입니다. 모듈·끝 부속마다 한 줄입니다.",
        f"CAD 백건 앞 펠트 {len(ws)}줄")
    n = need(r".*-B-blackfrontfelt-.*", 36, "black front felt")
    add("felt", "frontb", "흑건 앞 펠트 조각", n, "개",
        "메리노 2T + 하네나이트 1T · 흑건마다 한 조각 (y54.5~59.0)",
        "흑건 36개 자리마다 하네나이트 1T 위에 펠트 2T 조각을 붙입니다.",
        f"CAD 흑건 앞 펠트 {n}개")
    n_keys = cnt(r"(O\d|EL|ER)-KEY-.*")
    if n_keys != 88:
        err(f"CAD keys {n_keys}")
    add("felt", "bushing", "건반 부싱 천 0.5T 붙이기", n_keys, "건반",
        "0.5T 접착 천 (i062) · 노치 안쪽 · 핀 홈 양쪽 벽",
        "건반 스냅 노치 안쪽과 밸런스 핀 홈 양쪽 벽에 0.5T 천을 붙입니다. CAD 모델에는 천이 따로 없어 건반 수로 셉니다.",
        f"CAD 건반 {n_keys}개 (…-KEY-…)")
    evas = sel(r"(O\d|EL|ER)-EVA")
    esz = []
    for tag, rx in (("모듈", r"O\d-EVA"), ("EL", r"EL-EVA"), ("ER", r"ER-EVA")):
        szs = sorted({dims(bb(p)[:2]) for p in evas if re.fullmatch(rx, p.id)})
        esz += [f"{s_} ({tag})" for s_ in szs]
    add("felt", "evafloor", "모듈 바닥 EVA 3T 자르기", len(evas), "장",
        f"EVA 3T (i061) · {' / '.join(esz)} · 기판 자리 오려 냄",
        "모듈 7개와 끝 부속 2개 밑면에 붙입니다. 제어 기판 자리와 도브테일 홈 밑 두 곳을 오려 냅니다.",
        f"CAD EVA 바닥 {len(evas)}장")
    n = need(r"SPK[LR]-GASKET", 2, "gaskets")
    add("felt", "gasket", "스피커 가스켓 EVA 3T", n, "개",
        "바깥 105 × 105 · 안 Ø94 · 나사 자리 4-Ø4.8 (i061)",
        "EVA 3T 자투리를 칼로 잘라 스피커 출력 앞판 바깥면 유닛 자리에 둡니다.",
        f"CAD 가스켓 {n}개")
    js = sel(r"JOIN-EVA-.*")
    jsz = sorted({dims(sorted(bb(p))[1:][::-1]) for p in js}, reverse=True)
    add("felt", "evastrip", "이음 EVA 띠 3T", len(js), "개",
        f"EVA 3T (i061) · {' / '.join(jsz)} · 스피커 안쪽 옆판에 2줄씩",
        "스피커를 놓기 전에 안쪽 옆판에 붙여 끝벽과 닿는 면을 막습니다.",
        f"CAD 이음 띠 {len(js)}개")

    # ---- 판 잇기 (2026-10-16 A안: no plywood - the former panels are prints in group B; the two long centre panels come in
    # 3 half-lap pieces each that are glued into one panel here) ----------------------------------------------------------
    ply = [p for p in parts if p.kind == "plywood"]
    if ply:
        err(f"plywood pieces {len(ply)} != 0 (A안)")
    for pid, nm in (("CU-PLY-BOTTOM", "가운데 아랫판 3토막 잇기"), ("CU-PLY-BACK", "가운데 뒤판 3토막 잇기")):
        p = by_id.get(pid)
        if p is None or p.kind != "print" or len(p.print_pieces) != 3:
            err(f"{pid}: printed in 3 pieces expected")
            continue
        e = bb(p)
        add("ply", "join-" + pid.lower(), nm, 1, "장",
            f"출력 3토막 → {dims(sorted(e)[1:][::-1])} · 반턱 이음 2곳 (겹침 16) · MS 폴리머 (i071)",
            "반턱끼리 겹쳐 붙이고 모서리를 곧은 자에 맞춰 마스킹테이프로 눌러 굳힌 뒤 길이를 잽니다.",
            f"CAD {pid} (출력 3토막)")

    # ---- 기판 (bom.csv 'PCB-…' rows = one line per board kind) -----------------------------
    for bl in board_lines(bom, cnt):
        lines.append(bl)

    # ---- 선·하네스 (harness.csv / cables.csv rows that are cut or soldered) -----------------
    for cl in cable_lines(cables, harness, cnt):
        lines.append(cl)

    # ---- 조립 ------------------------------------------------------------------------------
    mods = sorted({int(m.group(1)) for i in ids for m in [re.match(r"O(\d)-", i)] if m})
    if mods != list(range(1, 8)):
        err(f"modules {mods}")
    add("asm", "mod", "옥타브 모듈 조립 O1~O7", len(mods), "개",
        "프레임 + 건반 12 + 레버 캐리어 12 + 봉 2 + 스프링 12 + 센서 바 + 패드 바 4 + 가림판 띠 + SB + MB",
        "모듈을 뒤집어 제어 기판을 바닥 구멍으로 넣고 M3 × 6 2개로 조입니다. 바닥 EVA를 붙입니다.",
        f"CAD 모듈 O1~O{len(mods)}")
    ends = [g for g in ("EL", "ER") if any(i.startswith(g + "-") for i in ids)]
    add("asm", "end", "끝 부속 조립 EL · ER", len(ends), "개",
        "왼쪽 A0 · A#0 · B0 (헤드폰 잭 J701) · 오른쪽 C8",
        "끝 부속 프레임에 건반·레버·봉·스프링·센서 기판을 넣고 리드를 뒤 통로로 뺍니다.",
        "CAD EL-… · ER-…")
    n_cap = need(r"(O\d|EL|ER)-CAPSTAN-.*", 88, "capstans")
    add("asm", "tune", "캡스턴 맞추기 (누르는 힘 47~55 g)", n_cap, "건반",
        "벤치 지그 T1 + 캡스턴 게이지 T2 · 1/8바퀴씩",
        "캡스턴 나사를 1/8바퀴씩 돌려 누르는 힘을 맞추고, 벗어나는 건반만 텅스텐 퍼티(i063)로 고칩니다.",
        f"CAD 캡스턴 {n_cap}개")
    add("asm", "pedal", "페달 개조 (홀센서 연속형)", need(r"PEDAL-DAMPER", 1, "pedal"), "개",
        "듀로 페달 (i109) · 발판 밑 자석 Ø5 × 2 1개 + 바닥판 PS",
        "마이크로스위치 배선을 떼고 자석과 센서 조각을 붙여 연속형으로 바꿉니다.",
        "CAD PEDAL-DAMPER")
    n_feet = need(r"FOOT-\d+", 14, "feet")
    add("asm", "feet", "고무발 달기 28 × 5", n_feet, "개",
        f"스피커 4 × 2 + 가운데 {n_feet - 8} · 직결피스 8호 13 mm (i039, i053)",
        "스피커 아랫판은 밀폐 상자 바닥이라 나사 구멍마다 MS 폴리머를 한 방울 넣습니다.",
        f"CAD 고무발 {n_feet}개 (FOOT-…)")
    n_box = len({p.id[:4] for p in parts if re.match(r"^SPK[LR]-PLY-BACK$", p.id)})
    add("asm", "spkbox", "스피커 상자 조립 L · R", n_box, "개",
        "출력 판 4 (바깥 옆판·뒤판·윗판·아랫판) + 앞판 · 안쪽 옆판 · 통로 틀 · 흡음솜 · 밀봉 확인",
        "이음은 모두 MS 폴리머로 붙이고(PETG에는 목공본드가 붙지 않음) 새는 곳이 없는지 확인합니다.",
        "CAD SPKL-… · SPKR-…")
    n_unit = need(r"SPK-[LR]", 2, "speaker units")
    add("asm", "spkunit", "스피커 유닛 · 그릴 달기", n_unit, "개",
        "가스켓 + M4 × 12 4개 (i212) · 그릴 8호 19 mm 4개 (i055)",
        "가스켓을 끼우고 유닛을 인서트에 조인 뒤 그릴을 나사 4개로 고정합니다.",
        "CAD SPK-L · SPK-R")
    add("asm", "cu", "가운데 유닛 조립", 1, "개",
        "아랫판 + 뒤판 + 끝벽 L·R · 배터리 틀 · 보드 (Pi, 강압, 앰프, 허브, PED)",
        "오꾸메는 목공본드, 출력 끝벽은 MS 폴리머로 붙이고 보드를 받침 기둥에 나사로 단 뒤 기둥째 붙입니다.",
        "CAD CU-…")
    n_ts = cnt(r"TS-E-SCREEN")
    if n_ts != 1:
        err(f"touchscreen {n_ts}")
    add("asm", "screen", "터치스크린 받침 조립", n_ts, "개",
        "화면 → 받침 (M2.5 × 6 4개) → 화면 뚜껑 (M3 × 20 경첩 2 + 다리 1)",
        "FFC B형을 꽂고 접어 받침에 넣은 뒤 화면 뚜껑에 경첩으로 답니다.",
        "CAD TS-…")
    add("asm", "final", "전체 결합", 1, "번",
        "모듈 잇기 → 방진 브래킷 → 가운데 유닛 → 스피커 → 선 정리 → 뚜껑",
        "모듈을 도브테일로 잇고 가운데 유닛과 스피커를 놓은 뒤 USB 선을 허브에 꽂고 뚜껑을 덮습니다.",
        "CAD 조립 순서 1~11")
    return subs, lines



# ---- boards and cables: read from the circuit lists so the page follows the circuit tab -----
BOARD_NAME = {"SB": "센서 기판 SB", "MB": "제어 기판 MB", "EL": "끝 부속 센서 기판 EL",
              "ER": "끝 부속 센서 기판 ER", "PB": "페달 보드 PB", "PS": "페달 센서 조각 PS",
              "J501 조각": "페달 잭 조각 J501", "J702 기판": "앰프 입력 잭 기판 J702"}
BOARD_CAD = {"SB": r"O\d-E-SB", "MB": r"O\d-E-MB", "EL": r"EL-E-BOARD", "ER": r"ER-E-BOARD",
             "PB": r"CU-E-PEDBOARD", "J702 기판": r"CU-E-J702BOARD", "J501 조각": r"CU-E-J501BOARD"}
BOARD_DO = {
    "SB": "띠를 잘라 홀센서를 표시면이 위로 눕혀 2.54 간격으로 납땜하고, 버스와 리본 블록 J201을 만듭니다.",
    "MB": "지그로 조각을 긋고 꺾고 구멍을 뚫은 뒤 RP2040-Zero와 먹스를 핀 헤더로 세워 납땜합니다. 모듈마다 ID 점퍼만 다르게 닫습니다.",
    "EL": "센서 3개와 리드 패드 J401을 납땜합니다.",
    "ER": "센서 1개와 리드 패드 J411을 납땜합니다.",
    "PB": "지그로 조각을 자르고 RP2040-Zero를 핀 헤더로 세워 페달 입력 부품을 납땜합니다.",
    "PS": "자투리에 센서와 부품을 납땜해 페달 바닥판에 붙입니다.",
    "J501 조각": "잭을 납땜하고 뒤판 출력물 잭 선반에 MS 폴리머로 붙입니다.",
    "J702 기판": "잭과 저음 차단 필터를 납땜합니다. 채널마다 1 µF 2개를 나란히 붙여(2 µF) 신호에 직렬로 넣고, "
                 "1 kΩ는 앰프 입력과 GND 사이에 답니다.",
}


def _int(x):
    try:
        return int(str(x).strip())
    except (TypeError, ValueError):
        return None


def part_label(r):
    v, ref = r.get("값", ""), r.get("부품", "")
    status = r.get("구매 상태 (최종 목록)", "") or ""
    if ref.startswith(("PCB-", "TP", "JP")) or "HDR" in ref or "부품 없음" in status or "선과 함께" in status:
        return None
    if v.startswith("DRV5055"):
        return "홀센서"
    if "RP2040" in v:
        return "RP2040-Zero"
    if "4067" in v:
        return "먹스 4067"
    if "PJ-313" in v:
        return "PJ-313 잭"
    if "JST-XH" in v:
        return "JST-XH"
    if re.fullmatch(r"[\d.]+\s*[nuµp]", v):
        return "콘덴서"
    if re.fullmatch(r"[\d.]+\s*[kM]?Ω?", v):
        return "저항"
    return None


def board_lines(bom, cnt):
    pcb_rows = [r for r in bom if r.get("부품", "").startswith("PCB-")]
    if not pcb_rows:
        err("bom.csv has no PCB-… rows (board list)")
        return []
    out = []
    for r in pcb_rows:
        board = r["보드"]
        n = _int(r.get("전체 수량")) or _int(r.get("보드 수"))
        nb = _int(r.get("보드 수")) or 1
        if not n:
            err(f"board {board}: no count")
            continue
        size = re.sub(r"^PCB-\S+\s*", "", r.get("값", "")).strip()
        rows = [x for x in bom if x["보드"] == board]
        labels = {}
        uniform = {}
        for x in rows:
            lab = part_label(x)
            per = _int(x.get("보드당"))
            tot = _int(x.get("전체 수량"))
            if not lab or per is None:
                continue
            labels[lab] = labels.get(lab, 0) + per
            uniform[lab] = uniform.get(lab, True) and (tot == per * nb)
        parts_txt = " · ".join(f"{k} {v}" for k, v in labels.items() if uniform.get(k))
        desc = r.get("부품 설명", "")
        if "BE163" in desc:
            stock = "BE163 (u06)에서" + (" · 지그 09_기판지그" if "기판지그" in desc else "")
        elif "12 × 18" in desc:
            stock = "만능기판 12 × 18 cm (i081)에서"
        else:
            stock = ""
        sheet = r.get("도면", "")
        meta = " · ".join(x for x in [size, stock, parts_txt, sheet] if x)
        lid = "c-" + (re.sub(r"[^a-z0-9]", "", board.lower()) or hashlib.sha1(board.encode()).hexdigest()[:6])
        cad = BOARD_CAD.get(board)
        basis = f"bom.csv {r.get('부품')} (보드 {nb}장)"
        if cad:
            c = cnt(cad)
            if c != n:
                err(f"board {board}: bom {n} != CAD {c}")
            basis += f" = CAD {c}장"
        else:
            basis += " · CAD 모델에는 기판이 따로 없음"
        line = {"id": lid, "g": "make", "s": "make-board", "n": BOARD_NAME.get(board, f"기판 {board}"),
                "need": n, "u": "장", "m": meta, "d": []}
        line["d"].append(["하는 일", BOARD_DO.get(board, "회로도대로 부품을 납땜합니다.")])
        if "아직 준비처 없음" in (r.get("구매 상태 (최종 목록)") or ""):
            line["w"] = ["이 기판을 자를 만능기판(12 × 18 cm, i081)이 아직 준비처가 없습니다."]
        line["d"].append(["셈 근거", basis])
        out.append(line)
    ok(f"C boards from bom.csv: {', '.join(f'{l['n']} {l['need']}' for l in out)}")
    return out


CABLE_CAD = {"W101~W107": r"O\d-C-RIBBON", "W401": r"EL-C-LEAD", "W411": r"ER-C-LEAD",
             "W403": r"O1-C-EXT", "W413": r"O7-C-EXT", "W601": r"C-PWR-IN", "W602a": r"C-PWR-FUSE",
             "W602b": r"C-PWR-BUS", "W602c": r"C-PWR-BUS", "W603": r"C-PWR-5V", "W604": r"C-PWR-5V",
             "W703": r"C-SPK-L", "W705": r"C-SPK-R", "W704": r"C-SPKPIG-L", "W706": r"C-SPKPIG-R"}


def with_mm(v):
    """'180 × 7' -> '180 mm × 7', '350 + 50' -> '350 + 50 mm', '1.5 m' stays."""
    v = (v or "").strip()
    if not v or re.search(r"\d\s*(m|cm|mm)\b", v) or not re.search(r"\d", v):
        return v
    mult = ""
    m = re.search(r"\s*×\s*\d+\s*$", v)
    if m:
        mult, v = m.group(0), v[: m.start()]
    v = re.sub(r"(\d(?:\.\d+)?)(?!.*\d)", r"\1 mm", v, count=1)
    return v + mult


def cable_lines(cables, harness, cnt):
    if not cables:
        err("cables.csv empty")
        return []
    keyname = "선" if "선" in cables[0] else "종류"
    keylen = "자르는 길이 (mm)" if "자르는 길이 (mm)" in cables[0] else "길이"
    hz = {}
    for h in harness or []:
        hz.setdefault(h["W"], []).append(h)
    out, skipped = [], []
    for r in cables:
        w = r["W"].strip()
        if not w.startswith("W"):
            skipped.append(w)
            continue
        hrows = hz.get(w, [])
        length = (r.get(keylen) or "").strip()
        if harness:
            if not hrows or all((h.get("자르는 길이") or "").strip() == "자르지 않음" for h in hrows):
                skipped.append(w)
                continue
        elif length in ("산 그대로", "동봉"):
            skipped.append(w)
            continue
        m = re.fullmatch(r"W(\d+)~W(\d+)", w)
        if m:
            n = int(m.group(2)) - int(m.group(1)) + 1
        else:
            mm = re.search(r"×\s*(\d+)\s*$", length)
            n = int(mm.group(1)) if mm else 1
        ends = " → ".join(x for x in [r.get("한쪽", "").strip(), r.get("다른 쪽", "").strip()] if x)
        core = (r.get("심") or r.get("심선") or "").strip()
        meta = " · ".join(x for x in [w, "자르는 길이 " + with_mm(length) if length else "", ends,
                                      core if core and core != "—" else ""] if x)
        det = []
        if hrows:
            h0 = hrows[0]
            if h0.get("선"):
                det.append(["선", h0["선"]])
            if h0.get("자르는 길이"):
                det.append(["자르는 길이", h0["자르는 길이"]])
            if h0.get("수축 튜브"):
                det.append(["수축 튜브", h0["수축 튜브"]])
            if len(hrows) <= 6:
                cores = []
                for h in hrows:
                    cores.append(f"{h.get('심 번호', '')} {h.get('색', '')} {h.get('넷', '')}: "
                                 f"{h.get('끝 A', '')} {h.get('A 핀', '')} → {h.get('끝 B', '')} {h.get('B 핀', '')}".strip())
                det.append(["심", " / ".join(cores)])
            else:
                det.append(["심", f"{len(hrows)}심 (1번 ↔ 1번 그대로, 회로도 탭의 선 목록)"])
        basis = f"cables.csv {w}"
        rx = CABLE_CAD.get(w)
        if rx:
            c = cnt(rx)
            if c <= 0:
                err(f"cable {w}: CAD {rx} not found")
            basis += f" · CAD {rx.replace(chr(92) + 'd', 'n')}"
            if w == "W101~W107" and c != n:
                err(f"ribbons: cables.csv {n} != CAD {c}")
        det.append(["셈 근거", basis])
        lid = "c-" + w.lower().replace("~", "-")
        out.append({"id": lid, "g": "make", "s": "make-cable", "n": r.get(keyname, w).strip(),
                    "need": n, "u": "가닥", "m": meta, "d": det})
    ok(f"C cables from {'harness.csv + ' if harness else ''}cables.csv: {len(out)} lines; "
       f"not made by hand (bought / plugged as is): {', '.join(skipped)}")
    return out

WARNINGS = []


def cable_text_check(item_lines_, cables, harness):
    """Item texts come from final_items.json (items step).  When one quotes a cut length next to a
    wire id ('W703 530'), that number must appear in the circuit lists for that wire.  A mismatch is a
    warning for the items step (the page shows final_items as it is), not a build error here."""
    nums = {}
    for r in list(cables) + list(harness or []):
        w = (r.get("W") or "").strip()
        txt = " ".join(str(r.get(k) or "") for k in ("자르는 길이 (mm)", "자르는 길이", "길이"))
        nums.setdefault(w, set()).update(re.findall(r"\d+(?:\.\d+)?", txt))
    bad = []
    for l in item_lines_:
        for _, v in l.get("d", []):
            for w, n in re.findall(r"\b(W\d{3}[a-z]?)\s+(\d+(?:\.\d+)?)\b", v):
                if w in nums and n not in nums[w]:
                    bad.append(f"{l['id']}: '{w} {n}' (cables.csv {w}: {', '.join(sorted(nums[w], key=float))})")
    if bad:
        for b in bad:
            WARNINGS.append("final_items text disagrees with cables.csv - " + b)
            print("WARN ", WARNINGS[-1])
    else:
        ok("cut lengths quoted in item texts match cables.csv")


# ---------------------------------------------------------------------------------------------
# section.html
# ---------------------------------------------------------------------------------------------
CHECK_SVG = ""


DEC_UNITS = ("m",)  # units counted to one decimal on the page


def inline_doc(doc):
    """What the page needs at start: everything except the long 'd' details and the build checks
    (those are fetched from fin/prep/lines.json when a row's '자세히' is opened)."""
    lite = {k: v for k, v in doc.items() if k not in ("lines", "checks", "warnings")}
    lite["lines"] = [{k: v for k, v in l.items() if k != "d"} for l in doc["lines"]]
    return lite


def section_html(doc):
    data = json.dumps(inline_doc(doc), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    g = {x["id"]: x for x in doc["groups"]}
    t = doc["totals"]
    opts = "".join(f'<option value="{x["id"]}">{x["tag"]} {html.escape(x["name"])}</option>' for x in doc["groups"])
    return f"""<section class="page" id="p-prep" hidden aria-labelledby="prep-h">
<h2 id="prep-h">07 준비 체크</h2>
<p class="lede">부품, 출력물, 가공·조립, 공구를 줄마다 몇 개 필요하고 몇 개 준비됐는지 적습니다. 필요한 만큼 준비되면 그 줄에 체크 표시가 뜨고, 위 막대가 전체 준비율을 보여 줍니다. 숫자는 이 페이지를 여는 모두가 함께 봅니다.</p>
<div class="prep-banner" id="prep-banner" role="status" aria-live="polite" hidden></div>
<div class="prep-sticky" id="prep-sticky">
  <div class="prep-st-main">
    <span class="prep-st-pct num" id="prep-pct">0%</span>
    <span class="prep-st-txt"><b>전체 준비</b><span id="prep-done">다 된 줄 0 / {t['main_lines']}</span></span>
  </div>
  <div class="prep-st-bar" aria-hidden="true"><i id="prep-bar"></i></div>
  <div class="prep-st-mini" id="prep-mini" aria-hidden="true"></div>
  <span class="prep-st-save small" id="prep-save">불러오는 중</span>
</div>
<div class="prep-gcards" id="prep-gcards" role="group" aria-label="묶음별 준비율"></div>
<label class="prep-tooltoggle small" for="prep-tools-in"><input type="checkbox" id="prep-tools-in"> 공구(D)도 전체 준비율에 넣기</label>
<div class="prep-filters" role="search" aria-label="줄 거르기">
  <div class="seg prep-seg" role="group" aria-label="상태로 거르기">
    <button type="button" data-f="all" aria-pressed="true">전체</button><button type="button" data-f="todo" aria-pressed="false">남은 것</button><button type="button" data-f="done" aria-pressed="false">다 된 것</button>
  </div>
  <label class="prep-gsel small" for="prep-group-sel">묶음
    <select id="prep-group-sel"><option value="">모두</option>{opts}</select></label>
  <input type="search" id="prep-q" class="prep-q" placeholder="이름·번호로 찾기 (예: M3, i014, 백건)" aria-label="이름이나 번호로 찾기" autocomplete="off">
  <button type="button" class="prep-csv" id="prep-csv">목록 받기 (csv)</button>
</div>
<p class="prep-csvnote small muted" id="prep-csv-note" aria-live="polite" hidden></p>
<p class="prep-shown small muted" id="prep-shown" aria-live="polite"></p>
<div class="prep-list" id="prep-list"><p class="muted small">목록을 불러오는 중입니다.</p></div>
<details class="spec prep-how" id="prep-how"><summary>계산 방법과 출처</summary>
<div class="small">
<p><b>전체 준비율</b> = 셈에 들어가는 줄마다 (준비 수 ÷ 필요 수, 1이 넘으면 1)를 더해 줄 수로 나눈 값입니다. 88개짜리 줄과 1개짜리 줄이 같은 무게입니다. 퍼센트는 버림이라 모든 줄이 끝나야 100 %가 됩니다.</p>
<p><b>소수</b> = 길이 줄(단위 m)은 0.1 m까지 적습니다. 나머지 줄은 개수라 소수를 적으면 버립니다(필요 2개에 1.5를 적으면 1개). 반올림하지 않으므로 모자란 줄이 다 됨으로 바뀌지 않습니다.</p>
<p><b>기본으로 셈에 넣는 줄</b> = A 부품 {g['parts']['counted']}줄 + B 출력물 {g['prints']['counted']}줄 + C 가공·조립 {g['make']['counted']}줄 = {t['main_lines']}줄. D 공구 {g['tools']['counted']}줄은 위 칸을 켜야 들어갑니다. 선택 줄(A의 보험·시험용 {g['parts']['optional']}줄, B의 stl/print_extra {g['prints']['optional']}줄)은 그 줄의 '준비율에 넣기'를 켜야 들어갑니다.</p>
<p><b>출처</b> = A·D: 최종 재료 목록 data/final_items.json (주문 수와 설계가 쓰는 수). B: hardware/mechanical/cad/manifest.json의 출력 파일 (파일 이름 끝 개수만큼 뽑음). C: CAD 모델(build_all.collect)의 부품 수와 회로 선 목록(cables.csv)·부품표(bom.csv). 줄 목록은 src/build_prep.py가 {html.escape(doc['generated'])}에 만들었습니다.</p>
<p><b>저장</b> = 준비 수는 이 페이지의 공유 저장소(prep/state)에 줄 번호별로 저장됩니다. 공유 저장소에 연결되지 않은 화면(미리보기 등)에서는 이 기기에만 저장됩니다.</p>
</div></details>
<script type="application/json" id="prep-data">{data}</script>
</section>
"""


# ---------------------------------------------------------------------------------------------
def main():
    verify = "--verify-stl" in sys.argv
    items_doc = json.load(open(ITEMS, encoding="utf-8"))
    manifest = json.load(open(os.path.join(CAD, "manifest.json"), encoding="utf-8"))
    bom = read_csv(os.path.join(NET, "bom.csv"))
    cables = read_csv(os.path.join(NET, "cables.csv"))
    hpath = os.path.join(NET, "harness.csv")
    harness = read_csv(hpath) if os.path.exists(hpath) else []
    parts = cad_parts()
    ok(f"CAD collect(): {len(parts)} parts (in memory)")

    subs_a, lines_a, lines_d, issues = item_lines(items_doc)
    cable_text_check(lines_a + lines_d, cables, harness)
    subs_b, lines_b, nfiles, nqty = print_lines(manifest, verify)
    subs_c, lines_c = make_lines(parts, bom, cables, harness)

    # D: tool issue note (no saw for plywood) goes into the group note
    tool_note = ""
    if "tools" in issues:
        tool_note = " " + issues["tools"][0]["text"]

    groups = [
        {"id": "parts", "tag": "A", "name": "부품",
         "note": "산 것과 가진 것을 손에 든 개수로 적습니다. "
                 "'필요'는 설계가 쓰는 개수입니다(주문 개수가 더 많으면 남는 것은 세지 않습니다).",
         "subs": subs_a},
        {"id": "prints", "tag": "B", "name": "출력물",
         "note": f"stl/print의 파일 {nfiles}개, 부품 {nqty}개입니다. 파일 이름 끝 개수만큼 뽑고 뽑은 개수를 적습니다. "
                 "stl/print_extra(선택·대안·예비)는 켜야 계산에 들어갑니다.",
         "subs": subs_b},
        {"id": "make", "tag": "C", "name": "가공·조립",
         "note": "자르고, 붙이고, 납땜하고, 조립하는 일입니다. 개수는 CAD 모델과 회로 선 목록에서 셌습니다.",
         "subs": subs_c},
        {"id": "tools", "tag": "D", "name": "공구",
         "note": "가진 공구입니다. 찾아서 손 닿는 곳에 두면 1로 둡니다. 기본은 전체 준비율에서 뺍니다." + tool_note,
         "subs": [{"id": "tools-1", "name": "공구"}]},
    ]
    lines = lines_a + lines_b + lines_c + lines_d

    # Length lines (unit m) take ready counts to 0.1 m ("dec": 1 = one decimal); every other line is whole
    # units and the page floors a typed fraction (1.5 of 2 stays 1, never rounds up to done).
    for l in lines:
        if l["u"] in DEC_UNITS:
            l["dec"] = 1

    # CAD print notes (B lines only) still name a few item ids that the final list merged into another item
    # (e.g. i068 bushing cloth = i062).  Show the kept id so nobody looks for a dropped item.
    kept = {it["id"] for it in items_doc["items"]}
    repl = {d["id"]: d["replaced_by"] for d in items_doc.get("dropped", [])
            if d.get("replaced_by") in kept}
    if repl:
        rx = re.compile(r"\b(" + "|".join(map(re.escape, repl)) + r")\b")
        n_sub = 0
        for l in lines_b:
            def sub(t):
                nonlocal n_sub
                t2 = rx.sub(lambda m: repl[m.group(1)], t)
                n_sub += t2 != t
                return t2
            l["m"] = sub(l.get("m", ""))
            l["d"] = [[k, sub(v)] for k, v in l.get("d", [])]
        ok(f"dropped item ids in texts replaced by the kept item ({', '.join(f'{a}→{b}' for a, b in repl.items())}): {n_sub} texts")

    # ---- checks -----------------------------------------------------------------------------
    ids = [l["id"] for l in lines]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        err(f"duplicate line ids {dup}")
    else:
        ok(f"{len(ids)} line ids unique")
    bad_ids = [i for i in ids if not re.fullmatch(r"[A-Za-z0-9_-]+", i)]
    if bad_ids:
        err(f"line ids with characters outside [A-Za-z0-9_-]: {bad_ids[:5]}")
    for l in lines:
        if not (isinstance(l["need"], int) and l["need"] > 0):
            err(f"need not a positive int: {l['id']} {l['need']}")
    n_dec = [l["id"] for l in lines if l.get("dec")]
    if any(l.get("dec") and l["u"] not in DEC_UNITS for l in lines):
        err("dec flag on a whole-unit line")
    ok(f"{len(n_dec)} length lines take 0.1 m steps ({', '.join(n_dec)}); the rest are whole units")
    sub_ids = {s["id"] for g in groups for s in g["subs"]}
    for l in lines:
        if l["s"] not in sub_ids:
            err(f"line {l['id']} sub {l['s']} unknown")
    n_items = len([i for i in items_doc["items"]])
    if len(lines_a) + len(lines_d) != n_items:
        err(f"A+D {len(lines_a) + len(lines_d)} != items {n_items}")
    # ordered >= need for purchased lines (A)
    for it in items_doc["items"]:
        o = it.get("ordered")
        if o and (o.get("units") or o.get("qty")) < it["qty_need"]:
            err(f"{it['id']} ordered units < need")
    # A counts equal checklist count of final_items
    chk = items_doc.get("counts", {}).get("checklist")
    non_opt_items = sum(1 for l in lines_a + lines_d if not l.get("opt"))
    if chk is not None and chk != non_opt_items:
        err(f"final_items checklist {chk} != non-optional A+D lines {non_opt_items}")
    else:
        ok(f"A+D non-optional lines {non_opt_items} = final_items counts.checklist")

    totals = {}
    for g in groups:
        gl = [l for l in lines if l["g"] == g["id"]]
        counted = [l for l in gl if not l.get("opt")]
        g["counted"] = len(counted)
        g["optional"] = len(gl) - len(counted)
        g["need_sum"] = sum(l["need"] for l in counted)
        g["need_sum_optional"] = sum(l["need"] for l in gl if l.get("opt"))
        units = {}
        for l in counted:
            units[l["u"]] = units.get(l["u"], 0) + l["need"]
        g["need_by_unit"] = units
        totals[g["id"]] = {"lines": len(gl), "counted": len(counted), "optional": g["optional"],
                           "need_sum": g["need_sum"], "need_by_unit": units}
    totals["main_lines"] = sum(g["counted"] for g in groups if g["id"] != "tools")
    totals["all_lines"] = len(lines)

    doc = {
        "version": 1,
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "about": "Toccata 준비 체크 줄 목록 (build_prep.py). id는 저장된 준비 수의 열쇠라 바꾸지 않습니다.",
        "db": {"doc": "prep/state", "shape": "{counts:{lineId:n}, include:{lineId:true}, opts:{tools:bool}, updatedAt}"},
        "src_chip": SRC_CHIP,
        "groups": groups,
        "totals": totals,
        "lines": lines,
        "checks": CHECKS,
        "warnings": WARNINGS,
    }
    for g in groups:
        ok(f"group {g['tag']} {g['name']}: {g['counted']} counted lines (+{g['optional']} optional), "
           f"need total {g['need_sum']} ({', '.join(f'{v} {k}' for k, v in g['need_by_unit'].items())})")
    ok(f"main % lines (A+B+C) = {totals['main_lines']}; all lines = {len(lines)}")

    if ERRORS:
        print(f"\n{len(ERRORS)} error(s); nothing written")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TAB_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    with open(OUT_SECTION, "w", encoding="utf-8") as f:
        f.write(section_html(doc))
    print(f"wrote {os.path.relpath(OUT_JSON, ROOT)} ({os.path.getsize(OUT_JSON) // 1024} KB), "
          f"{os.path.relpath(OUT_SECTION, ROOT)} ({os.path.getsize(OUT_SECTION) // 1024} KB)")
    write_meta(doc)


OUT_META = os.path.join(TAB_DIR, "meta.json")


def write_meta(doc):
    """meta.json for the integration step; every number is taken from the doc just written."""
    t, g = doc["totals"], {x["id"]: x for x in doc["groups"]}

    def units(gid):
        return ", ".join(f"{v} {k}" for k, v in g[gid]["need_by_unit"].items())

    opt_a = [l["id"].split("-", 1)[1] for l in doc["lines"] if l["g"] == "parts" and l.get("opt")]
    dec = [l["id"] for l in doc["lines"] if l.get("dec")]
    n_files = t["prints"]["counted"]
    n_parts = t["prints"]["need_sum"]
    extra = [l for l in doc["lines"] if l["g"] == "prints" and l.get("opt")]
    notes = (
        "Preparation tracker. Lines are generated by src/build_prep.py (re-run it after final_items.json, the CAD "
        "build or hardware/pcb/netlist changes; the C board/cable lines are read from bom.csv, cables.csv and "
        "harness.csv at build time, so they follow the 01 circuit tab). It writes fin/prep/lines.json (canonical, "
        f"{os.path.getsize(OUT_JSON) // 1024} KB, fetched on first open for the '자세히' texts), "
        f"src/tabs/prep/section.html (light copy of the same data inline as <script type=application/json "
        f"id=prep-data>, ~{os.path.getsize(OUT_SECTION) // 1024} KB, so the summary card and deep links work "
        f"without a fetch) and this meta.json. Generated {doc['generated']}. "
        f"Lines: {t['all_lines']} total; main % uses A+B+C = {t['main_lines']} lines. "
        f"A 부품 {t['parts']['counted']} lines (+{t['parts']['optional']} optional {', '.join(opt_a)}), "
        f"need total {t['parts']['need_sum']} ({units('parts')}). "
        f"B 출력물 {n_files} files = {n_parts} parts in stl/print (+{len(extra)} optional stl/print_extra files, "
        f"{sum(l['need'] for l in extra)} parts). "
        f"C 가공·조립 {t['make']['counted']} lines, need total {t['make']['need_sum']} ({units('make')}). "
        f"D 공구 {t['tools']['counted']} lines, need {t['tools']['need_sum']} ({units('tools')}), out of the main % "
        "unless the '공구(D)도 전체 준비율에 넣기' box is on. Counts: whole-unit lines floor a typed fraction "
        f"(1.5 of 2 stays 1, never rounds up to done); the {len(dec)} length lines (unit m: {', '.join(dec)}) "
        "carry \"dec\":1 in lines.json and take one decimal (input step 0.1, inputmode decimal, also floored: "
        "1.95 m -> 1.9 m), compared with need without rounding; +/- buttons move 1 unit. Percent = "
        "floor(100 * mean over counted lines of min(ready, need)/need). Persistence: requires capabilities "
        "{db:{}, user:{}, downloads:true}; db document 'prep/state' = {counts:{lineId:n}, include:{lineId:true}, "
        "opts:{tools:bool}, updatedAt}; first write is set() (document absent), later writes update() with only "
        "the changed keys, 600 ms debounce, one write in flight, re-read + back-off on unavailable; "
        "user.can('data.write') false or a rejected write -> read-only banner; no db -> localStorage "
        "'toccata.prep.v1' + banner. Saved counts of a line id that no longer exists are ignored (not counted). "
        "API: window.toccata.prep = {onChange(cb)->unsubscribe, summary(), line(id), lines()} (+ _test for node "
        "tests). Renders a compact card into #sum-prep (summary tab) using global classes .card .eyebrow .num "
        ".small .muted and inline token styles only. Element ids: prep-r-<lineId> (row, deep-linkable), "
        "prep-in-<lineId> (count input), prep-inc-<lineId> (optional include), prep-g-<group>, prep-sg-<sub>. "
        "Line ids: a-<item id> / d-<item id> (final_items), b-<folder>-<sha1(folder/name)[:8]> and bx-<…> (print "
        "files), c-<name> (making; boards c-sb, c-mb …, cables c-w101-w107, c-w601 …). CSV export via "
        "downloads.save (Toccata_준비체크_YYYY-MM-DD.csv, UTF-8 BOM); without the capability the button is "
        "replaced by a note with the file name and size. Row images use img/bom/<id>.jpg from the items step "
        "(loading=lazy).")
    meta = {"tab": "prep", "notes": notes, "generated": doc["generated"],
            "warnings_for_other_steps": doc.get("warnings", []),
            "totals": {k: v for k, v in t.items()},
            "capabilities": {"db": {}, "user": {}, "downloads": True},
            "builder": "python3 docs/report/toccata-v4/src/build_prep.py [--verify-stl]"}
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT_META, ROOT)}")


if __name__ == "__main__":
    main()
