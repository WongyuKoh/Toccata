"""Build every Toccata CAD output.

  python build_all.py            # everything
  python build_all.py --no-anno  # skip the dimensioned STLs
  python build_all.py --no-drawings / --no-png / --no-render   # skip the 2D sheets / their PNG copies / the OpenSCAD renders
                                                               # (a drawing self-check failure -> exit code 2, other outputs still written)

Outputs (../):
  stl/print/<NN_폴더>/<부품이름>__<수량>개.stl   print-ready, lying on the bed, one file per distinct shape
                                                 (06_출력공구 = key-action tools, 08_합판지그 = plywood drilling jigs from
                                                 src/plywood_jigs.py, guide cad/jigs/README.md; 09_기판지그 = perfboard cut / drill
                                                 jigs for the BE163 control / PED boards from src/perfboard_jigs.py; optional
                                                 prints -> stl/print_extra/)
  Toccata_출력STL_전체.zip                        everything in stl/print in one file
  Toccata_한옥타브_출력STL.zip                    one octave module (+ tools, MB jig), names carrying per-octave counts
  stl/assembly/<그룹>.stl                        every part in world coordinates (open them together)
  stl/assembly/Toccata_전체조립.stl               the whole instrument in one file
  stl/annotated/<폴더>/<부품이름>_치수.stl         part + dimension lines + numbers (for looking, not printing)
  Toccata_전체조립.3mf                           named + coloured objects (one per group and colour)
  Toccata_전체조립.glb                           the same for the web viewer
  manifest.json                                  every part: id, names, kind, group, bbox, file
  drawings/D01..D06_*.svg + .png                 dimensioned 2D sheets of the L2 rear unit + touchscreen (src/drawings.py)
  renders/R01_front.png, R02_rear_left.png, R03_folded.png
"""
import collections
import hashlib
import io
import json
import os
import re
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.normpath(os.path.join(HERE, ".."))

from cadlib import mesh_arrays, write_stl  # noqa: E402


def safe(s):
    s = s.replace("/", "·").replace(":", "-").replace("\\", "·")
    s = re.sub(r"\s+", "_", s.strip())
    return s


def collect():
    parts = []
    import keyaction_parts
    parts += keyaction_parts.build_all()
    for mod in ("body", "electronics"):
        p = os.path.join(HERE, mod + ".py")
        if os.path.exists(p):
            m = __import__(mod)
            parts += m.build()
    # unique ids
    seen = collections.Counter()
    for p in parts:
        seen[p.id] += 1
        if seen[p.id] > 1:
            p.id = "%s-%d" % (p.id, seen[p.id])
    return parts


def signature(m):
    b = m.bounding_box()
    dims = tuple(round(b[i + 3] - b[i], 2) for i in range(3))
    v, f = mesh_arrays(m)
    v = v - v.min(axis=0)
    key = np.round(np.sort(np.round(v, 2).view([("a", "f8"), ("b", "f8"), ("c", "f8")]).ravel(), order=["a", "b", "c"]).view("f8"), 2)
    h = hashlib.sha1(key.tobytes()).hexdigest()[:12]
    return (round(m.volume(), 1), dims, h)


def concat(solids):
    vs, fs, off = [], [], 0
    for m in solids:
        v, f = mesh_arrays(m)
        vs.append(v)
        fs.append(f + off)
        off += len(v)
    return np.vstack(vs), np.vstack(fs)


def write_mesh_stl(v, f, path, header=""):
    import struct
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ln[ln == 0] = 1
    n = n / ln[:, None]
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n
    rec["v"] = tri
    with open(path, "wb") as fh:
        fh.write(header.encode("ascii", "replace")[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(f)))
        fh.write(rec.tobytes())


# ------------------------------------------------------------------ print files
EXTRA = "@extra/"           # print folders that start with this go to stl/print_extra/ (alternatives, options, spares)

# spare keys per the parts list (parts_list.json): every white-key file +1, black C#.D# +2, F# +1, G# +1, A#.A#0 +2
SPARE_KEYS = {"흑건_C#·D#": 2, "흑건_F#": 1, "흑건_G#": 1, "흑건_A#·A#0": 2}


def print_path(folder, fn):
    """stl/print/<folder>/<fn>, or stl/print_extra/<rest>/<fn> for '@extra/<rest>' folders."""
    if folder.startswith(EXTRA):
        return os.path.join(OUT, "stl", "print_extra", folder[len(EXTRA):], fn)
    return os.path.join(OUT, "stl", "print", folder, fn)


def write_print(parts):
    groups = collections.OrderedDict()
    pieces = []                   # (part, file stem, solid on bed): parts longer than the bed, printed in pieces (2026-10-16)
    for p in parts:
        if p.kind != "print" or p.print_solid is None:
            continue
        if p.print_pieces:
            pieces += [(p, nm, q) for nm, q in p.print_pieces]
            continue
        sig = signature(p.print_solid)
        groups.setdefault((p.print_folder, sig), []).append(p)
    rows = []
    for (folder, sig), ps in groups.items():
        names = []
        for p in ps:
            if p.print_name not in names:
                names.append(p.print_name)
        if len(names) > 1:
            # e.g. 흑건_C# + 흑건_D# -> 흑건_C#·D#
            pre = os.path.commonprefix(names)
            pre = pre[: pre.rfind("_") + 1] if "_" in pre else ""
            name = pre + "·".join(n[len(pre):] for n in names)
        else:
            name = names[0]
        qty = len(ps)
        fn = "%s__%d개.stl" % (safe(name), qty)
        path = print_path(folder, fn)
        b = ps[0].print_solid.bounding_box()
        write_stl(ps[0].print_solid, path, "Toccata %s x%d  %.1fx%.1fx%.1f mm" % (ps[0].id, qty, b[3] - b[0], b[4] - b[1], b[5] - b[2]))
        for p in ps:
            p._print_file = os.path.relpath(path, OUT)
        rows.append({
            "file": os.path.relpath(path, OUT), "name": name, "qty": qty, "folder": folder,
            "size_mm": [round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)],
            "volume_cm3": round(ps[0].print_solid.volume() / 1000.0, 2),
            "mass_g_solid_petg": round(ps[0].print_solid.volume() / 1000.0 * 1.27, 1),
            "material": ps[0].material, "note": ps[0].print_note, "ids": [p.id for p in ps],
            "name_ko": name.replace("_", " "), "extra": folder.startswith(EXTRA),
        })
    files = {}
    for p, nm, q in pieces:
        path = print_path(p.print_folder, "%s__1개.stl" % safe(nm))
        b = q.bounding_box()
        write_stl(q, path, "Toccata %s piece %s  %.1fx%.1fx%.1f mm" % (p.id, nm.encode("ascii", "ignore").decode() or "", b[3] - b[0], b[4] - b[1], b[5] - b[2]))
        files.setdefault(p.id, []).append(os.path.relpath(path, OUT))
        rows.append({
            "file": os.path.relpath(path, OUT), "name": nm, "qty": 1, "folder": p.print_folder,
            "size_mm": [round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)],
            "volume_cm3": round(q.volume() / 1000.0, 2), "mass_g_solid_petg": round(q.volume() / 1000.0 * 1.27, 1),
            "material": p.material, "note": p.print_note, "ids": [p.id], "piece_of": p.id,
            "name_ko": nm.replace("_", " "), "extra": p.print_folder.startswith(EXTRA),
        })
    for p in parts:
        if p.id in files:
            p._print_file = " + ".join(files[p.id])
    # print-only variants (not in the assembly), e.g. pad bars for the PORON 5T that the purchase list buys
    import keyaction_parts
    for (folder, name, solid, qty, material, note) in keyaction_parts.EXTRA_PRINTS:
        path = print_path(folder, "%s__%d개.stl" % (safe(name), qty))
        b = solid.bounding_box()
        write_stl(solid, path, "Toccata %s x%d (variant)" % (name.encode("ascii", "ignore").decode() or "variant", qty))
        rows.append({"file": os.path.relpath(path, OUT), "name": name, "qty": qty, "folder": folder,
                     "size_mm": [round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)],
                     "volume_cm3": round(solid.volume() / 1000.0, 2), "mass_g_solid_petg": round(solid.volume() / 1000.0 * 1.27, 1),
                     "material": material, "note": note, "ids": [], "name_ko": name.replace("_", " "), "variant": True,
                     "extra": folder.startswith(EXTRA)})
    # printed assembly tools of the key-action design (DESIGN 10.1 / 15): copied from key-action-v4/printables/tools
    import shutil
    tools = os.path.normpath(os.path.join(HERE, "..", "..", "key-action-v4", "printables", "tools", "stl"))
    tnames = {"tool_bench_jig.stl": ("공구_벤치지그받침_T1a", 38.4), "tool_height_block.stl": ("공구_높이블록_T1b", 10.3),
              "tool_capstan_gauge.stl": ("공구_캡스턴벤치게이지_T2", 13.3), "tool_pin_gauge.stl": ("공구_밸런스핀높이게이지_T3", 6.3)}
    for fn, (nm, g) in tnames.items():
        src = os.path.join(tools, fn)
        if not os.path.exists(src):
            continue
        dst = os.path.join(OUT, "stl", "print", "06_출력공구", "%s__1개.stl" % nm)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        import trimesh
        tb = trimesh.load(src).bounds
        rows.append({"file": os.path.relpath(dst, OUT), "name": nm, "qty": 1, "folder": "06_출력공구",
                     "size_mm": [round(float(tb[1][i] - tb[0][i]), 2) for i in range(3)],
                     "volume_cm3": 0, "mass_g_solid_petg": g, "material": "PETG",
                     "note": "건반 액션 설계의 출력 공구(DESIGN 10.1, key-action-v4/printables/tools/tools.md): 악기당 1벌, 서포트 없음; "
                             "T2·T3는 채움 100 %·층 0.1", "ids": [], "name_ko": nm.replace("_", " "), "variant": True})
    # printed plywood drilling jigs (W1 2026-10-02, src/plywood_jigs.py, how to use: cad/jigs/README.md): required -> stl/print/08_합판지그
    # (one set per instrument, all four J-b saddle gaps included), optional J-f -> stl/print_extra/선택_합판지그. Tools, not instrument parts
    # (variant True). A failure here only drops the jigs (warning), the rest of the build goes on.
    # 2026-10-16 (A안): no plywood left (all panels printed, holes / pilots / magnet seats in the prints) -> the 08 plywood drilling
    # jigs are no longer built (src/plywood_jigs.py kept for the record)
    rows += write_pcb_jigs()
    # spare keys (optional) -> stl/print_extra/예비_건반: same STL as the 01 file, count = spares only
    for r in [r for r in rows if r["folder"] == "01_건반"]:
        spare = SPARE_KEYS.get(r["name"], 1 if r["name"].startswith("백건") else 0)
        if not spare:
            continue
        dst = print_path(EXTRA + "예비_건반", "%s__%d개.stl" % (safe(r["name"]), spare))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(OUT, r["file"]), dst)
        rows.append(dict(r, file=os.path.relpath(dst, OUT), qty=spare, folder=EXTRA + "예비_건반", ids=[], variant=True, extra=True,
                         note="선택: 예비 건반 (부품표 parts_list.json의 예비 수). 01_건반의 같은 파일과 모양이 같음 - 부러진 건반 하나만 바꿀 때 씀. "
                              "본체에 보관 칸이 없으니(R29) 따로 상자에 보관. 출력 방법은 01_건반과 같음"))
    return rows


def write_jigs():
    """plywood_jigs.build() -> STL files + print rows (tools: variant True; J-f optional -> print_extra). [] + a warning on failure."""
    try:
        import plywood_jigs
        jigs = plywood_jigs.build()
    except Exception as ex:  # noqa: BLE001
        print("WARNING: plywood_jigs failed (%s: %s) - no 08_합판지그 jigs in this build; run src/check_plywood_jigs.py" % (type(ex).__name__, ex))
        return []
    req_folder = getattr(plywood_jigs, "PRINT_SUB", "08_합판지그")
    opt_folder = EXTRA + getattr(plywood_jigs, "EXTRA_SUB", "선택_합판지그")
    est = getattr(plywood_jigs, "est_print", None)
    rows = []
    for j in jigs:
        solid, qty = j["solid"], int(j.get("qty", 1))
        folder = req_folder if j.get("required", True) else opt_folder
        path = print_path(folder, "%s__%d개.stl" % (safe(j["name"]), qty))
        b = solid.bounding_box()
        write_stl(solid, path, "Toccata %s x%d plywood jig  %.1fx%.1fx%.1f mm" % (j.get("key", "jig"), qty, b[3] - b[0], b[4] - b[1], b[5] - b[2]))
        row = {"file": os.path.relpath(path, OUT), "name": j["name"], "qty": qty, "folder": folder,
               "size_mm": [round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)],
               "volume_cm3": round(solid.volume() / 1000.0, 2), "mass_g_solid_petg": round(solid.volume() / 1000.0 * 1.27, 1),
               "material": "PETG", "note": j.get("note", ""), "ids": [], "name_ko": j["name"].replace("_", " "),
               "variant": True, "extra": folder.startswith(EXTRA), "jig": j.get("key")}
        if est:
            g, minutes = est(solid)                       # 3 walls + 15 % infill estimate (plywood_jigs.est_print, P2S)
            row["mass_g_print_est"], row["print_min_est"] = round(g, 1), round(minutes, 0)
        rows.append(row)
    return rows


def write_pcb_jigs():
    """perfboard_jigs.build() (2026-10-07: BE163 control / PED board cut + drill jigs) -> stl/print/09_기판지그. [] + a warning on failure."""
    try:
        import perfboard_jigs
        jigs = perfboard_jigs.build()
    except Exception as ex:  # noqa: BLE001
        print("WARNING: perfboard_jigs failed (%s: %s) - no 09_기판지그 jigs in this build; run src/check_perfboard_jigs.py" % (type(ex).__name__, ex))
        return []
    rows = []
    for j in jigs:
        solid, qty = j["solid"], int(j.get("qty", 1))
        folder = perfboard_jigs.PRINT_SUB
        path = print_path(folder, "%s__%d개.stl" % (safe(j["name"]), qty))
        b = solid.bounding_box()
        write_stl(solid, path, "Toccata %s x%d perfboard jig  %.1fx%.1fx%.1f mm" % (j.get("key", "jig"), qty, b[3] - b[0], b[4] - b[1], b[5] - b[2]))
        g, minutes = perfboard_jigs.est_print(solid)
        rows.append({"file": os.path.relpath(path, OUT), "name": j["name"], "qty": qty, "folder": folder,
                     "size_mm": [round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)],
                     "volume_cm3": round(solid.volume() / 1000.0, 2), "mass_g_solid_petg": round(solid.volume() / 1000.0 * 1.27, 1),
                     "material": "PETG", "note": j.get("note", ""), "ids": [], "name_ko": j["name"].replace("_", " "),
                     "variant": True, "extra": False, "pcbjig": j.get("key"),
                     "mass_g_print_est": round(g, 1), "print_min_est": round(minutes, 0)})
    return rows


def write_print_zip():
    """one-file download of stl/print (everything to print for one instrument)."""
    zp = os.path.join(OUT, "Toccata_출력STL_전체.zip")
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        base = os.path.join(OUT, "stl")
        for root, _dirs, fns in os.walk(os.path.join(base, "print")):
            for fn in sorted(fns):
                if fn.endswith(".stl"):
                    full = os.path.join(root, fn)
                    z.write(full, os.path.relpath(full, base))
    return zp


# One octave module for a first-module print (the seven modules O1..O7 are the same shapes): (file stem in stl/print,
# prints per octave, stem in the zip when the full-set name would mislead). Plus the key-action tools and the MB jig.
OCTAVE_PRINTS = (
    [("백건_" + n, 1, None) for n in ("C", "D", "E", "F", "G", "A", "B")]
    + [("흑건_C#·D#", 2, None), ("흑건_F#", 1, None), ("흑건_G#", 1, None), ("흑건_A#·A#0", 1, "흑건_A#")]
    + [("레버캐리어_" + n, 1, None) for n in ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")]
    + [("프레임_모듈", 1, None), ("센서바", 1, None), ("가림판띠", 1, None), ("레버봉끝마개", 1, None)]
    + [("패드바_칸%d" % i, 1, None) for i in (1, 2, 3, 4)]
    + [("공구_벤치지그받침_T1a", 1, None), ("공구_높이블록_T1b", 1, None), ("공구_캡스턴벤치게이지_T2", 1, None),
       ("공구_밸런스핀높이게이지_T3", 1, None), ("P-MB_제어기판지그_MB7장", 1, "P-MB_제어기판지그")]
)


def write_octave_zip(rows):
    """one octave module from stl/print, file names carrying the per-octave counts, plus a short list."""
    by_stem = collections.defaultdict(list)
    for r in rows:
        m = re.match(r"stl/print/([^/]+)/(.+)__\d+개\.stl$", r["file"].replace(os.sep, "/"))
        if m:
            by_stem[m.group(2)].append((m.group(1), r))
    top = "Toccata_한옥타브_출력STL"
    lines, parts, tools, grams = [], 0, 0, [0.0, 0.0]
    entries = []
    for stem, qty, new in OCTAVE_PRINTS:
        hits = by_stem.get(stem, [])
        if len(hits) != 1:
            raise SystemExit("octave zip: '%s' matches %d files in stl/print" % (stem, len(hits)))
        folder, r = hits[0]
        name = "%s__%d개.stl" % (new or stem, qty)
        is_tool = folder.startswith(("06_", "09_"))
        tools += qty if is_tool else 0
        parts += 0 if is_tool else qty
        grams[is_tool] += qty * r["mass_g_solid_petg"]
        entries.append((os.path.join(OUT, r["file"]), "%s/%s/%s" % (top, folder, name)))
        lines.append("  %d개  %5.1f g  %-9s  %s/%s" % (qty, r["mass_g_solid_petg"], r.get("material", ""), folder, name))
    readme = "\n".join([
        "Toccata 한 옥타브 출력 STL — 옥타브 모듈 1개(건반 12개)",
        "",
        "옥타브 모듈 7개(O1~O7)는 모양이 같아 이 묶음을 어느 옥타브로 써도 됩니다.",
        "파일 이름 끝 __N개가 한 옥타브에 뽑을 개수입니다.",
        "- 흑건_C#·D#: C#과 D#이 같은 모양이라 2개.",
        "- 흑건_A#: 전체 목록의 '흑건_A#·A#0'과 같은 파일(한 옥타브에는 A#만).",
        "- P-MB_제어기판지그: 전체 목록의 'P-MB_제어기판지그_MB7장'과 같은 파일(지그 하나로 MB를 모두 자름).",
        "",
        "악기 부품 %d개, 출력 공구·기판 지그 %d개." % (parts, tools),
        "속 꽉 채움 질량: 부품 %.0f g + 공구·지그 %.0f g. 실제 출력은 채움 %%만큼 적고, 프레임 서포트 약 88 g이 따로 듭니다." % tuple(grams),
        "뽑는 방향·서포트·재료: 최종본/05_조립·제작/01_CAD_출력·조립_안내.md '출력 목록' (원본 hardware/mechanical/cad/README.md).",
        "",
        "들어 있지 않은 것: 끝 부속(A0·A#0·B0·C8), 본체·스피커·터치스크린 출력물, 예비 건반, 대안 패드바(PORON 6T용),",
        "단계 0 시편(첫 모듈의 조립 시험 21에 쓰는 받침 빗은 00_단계0_시험출력/C17a.stl).",
        "",
        "파일 (한 옥타브 개수, 개당 속 꽉 채움 질량, 재료, 폴더/이름):",
    ] + lines) + "\n"
    zp = os.path.join(OUT, "Toccata_한옥타브_출력STL.zip")
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(top + "/읽어보기.txt", readme)
        for full, arc in entries:
            z.write(full, arc)
    return zp


# ------------------------------------------------------------------ assembly files
def write_assembly(parts):
    by = collections.OrderedDict()
    for p in parts:
        by.setdefault(p.group, []).append(p)
    files = []
    for g, ps in by.items():
        v, f = concat([p.solid for p in ps])
        path = os.path.join(OUT, "stl", "assembly", safe(g) + ".stl")
        write_mesh_stl(v, f, path, "Toccata assembly group")
        files.append(os.path.relpath(path, OUT))
    v, f = concat([p.solid for p in parts if p.note not in ("offdesk", "altview")])
    write_mesh_stl(v, f, os.path.join(OUT, "stl", "assembly", "Toccata_전체조립.stl"), "Toccata full assembly, mm, world coords")
    return files


def write_3mf(parts, path):
    """objects = (group, colour) merges; names and display colours survive in most viewers/slicers."""
    objs = collections.OrderedDict()
    for p in parts:
        objs.setdefault((p.group, p.color, p.kind), []).append(p)
    mats = []
    buf = io.StringIO()
    w = buf.write
    w('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="ko-KR" '
      'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n<metadata name="Title">Toccata 전체 조립</metadata>\n<resources>\n')
    colors = []
    for (g, c, k) in objs:
        if c not in colors:
            colors.append(c)
    w('<basematerials id="1">\n')
    for c in colors:
        w('<base name="%s" displaycolor="%sFF"/>\n' % (c, c.upper()))
    w('</basematerials>\n')
    oid = 2
    ids = []
    for (g, c, k), ps in objs.items():
        v, f = concat([p.solid for p in ps])
        nm = "%s · %s" % (g, {"print": "출력", "bought": "구매", "consumable": "소모품", "electronics": "전자", "plywood": "합판"}.get(k, k))
        w('<object id="%d" type="model" name="%s" pid="1" pindex="%d"><mesh><vertices>\n' % (oid, nm.replace('"', "'").replace("&", "+"), colors.index(c)))
        w("".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(q) for q in v))
        w("</vertices><triangles>\n")
        w("".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(t) for t in f))
        w("</triangles></mesh></object>\n")
        ids.append(oid)
        oid += 1
    w("</resources>\n<build>\n")
    for i in ids:
        w('<item objectid="%d"/>\n' % i)
    w("</build>\n</model>\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", buf.getvalue())


def write_glb(parts, path):
    """one mesh per part (node name = part id), one flat material per colour, shared vertices (small file)."""
    import trimesh
    from trimesh.visual.material import PBRMaterial
    scene = trimesh.Scene()
    mats = {}
    for p in parts:
        v, f = mesh_arrays(p.solid)
        c = p.color.lstrip("#")
        if p.color not in mats:
            rgba = [int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0, 1.0]
            mats[p.color] = PBRMaterial(name="c" + c, baseColorFactor=rgba, metallicFactor=0.0, roughnessFactor=0.75)
        m = trimesh.Trimesh(vertices=v.astype(np.float32), faces=f, process=False)
        m.visual = trimesh.visual.TextureVisuals(material=mats[p.color])
        scene.add_geometry(m, node_name=p.id, geom_name=p.id)
    scene.export(path)


def main():
    import shutil
    anno = "--no-anno" not in sys.argv
    parts = collect()
    for d in ("print", "print_extra", "assembly", "annotated"):
        shutil.rmtree(os.path.join(OUT, "stl", d), ignore_errors=True)
    rows = write_print(parts)
    write_print_zip()
    write_octave_zip(rows)
    files = write_assembly(parts)
    ondesk = [p for p in parts if p.note not in ("offdesk", "altview")]      # pedal on the floor / folded-screen view
    write_3mf(ondesk, os.path.join(OUT, "Toccata_전체조립.3mf"))
    if "--no-glb" not in sys.argv:
        write_glb(ondesk, os.path.join(OUT, "Toccata_전체조립.glb"))
    man = {
        "units": "mm",
        "coords": "world: x across (0 = A0 left boundary), y from the white-key front lip (+ away from the player), z from the desk",
        "print": rows,
        "assembly_files": files,
        "parts": [{"id": p.id, "name_ko": p.name_ko, "name_en": p.name_en, "kind": p.kind, "group": p.group,
                   "bbox": [round(x, 3) for x in p.solid.bounding_box()], "color": p.color, "material": p.material,
                   "print_file": getattr(p, "_print_file", None), "source": p.source, "note": p.note} for p in parts],
    }
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False, indent=1)
    if anno:
        import annotate_parts
        annotate_parts.write_all(parts, rows, OUT)
    import make_readme
    make_readme.main()
    sys.path.insert(0, os.path.join(OUT, "viewer"))
    import gen_viewer
    gen_viewer.main()
    # 2D drawing sheets D01..D06 (+ PNG) and renders R01..R03 from the same solids (src/drawings.py). A failure here does
    # not stop the other outputs (STL / 3MF / GLB / README / viewer are already written), but the build exits with 2.
    drawings_failed = False
    if "--no-drawings" not in sys.argv:
        try:
            import drawings
            drawings.main(parts=parts, png="--no-png" not in sys.argv, render="--no-render" not in sys.argv)
        except Exception as ex:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            drawings_failed = True
            print("ERROR: drawings.py failed (%s: %s) - STL / 3MF / GLB / README / viewer are still written" % (type(ex).__name__, ex))
    print("parts", len(parts), "print files", len(rows), "assembly groups", len(files))
    if drawings_failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
