"""Build all Toccata schematic / board sheets: SVG + connectivity check (+ PNG preview if resvg_py is available).

usage: python3 build.py [--png DIR] [--no-cad]
  1. cad_extract.refresh(): reads the built CAD (hardware/mechanical/cad, build_all.collect() only) -> netlist/cad_centre.json
     (--no-cad: use the saved JSON)
  2. every sheet in sheets.SHEETS: draw, re-derive the nets from the drawn geometry, compare with the intended netlist,
     text-overlap check, board self-checks (BRD-03 wire routes vs SCH-05)
  3. export.export(): netlist / BOM / cables / harness / pin tables (CSV) + regions.json for the page
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "..", "schematic")
OUT_BRD = os.path.join(HERE, "..", "board")
NAMES = {"sch01": "SCH-01_system", "sch02": "SCH-02_sensor_board", "sch03": "SCH-03_control_board",
         "sch04": "SCH-04_end_parts", "sch05": "SCH-05_pedal", "sch06": "SCH-06_power", "sch07": "SCH-07_audio",
         "brd01": "BRD-01_control_board_placement", "brd02": "BRD-02_sensor_board_placement",
         "brd03": "BRD-03_pedal_board_placement", "brd04": "BRD-04_centre_unit_wiring",
         "brd05": "BRD-05_power_audio_harness", "brd06": "BRD-06_signal_harness",
         "brd07": "BRD-07_small_boards", "brd08": "BRD-08_control_board_underside",
         "brd09": "BRD-09_control_board_O1", "brd10": "BRD-10_control_board_O7", "brd11": "BRD-11_control_board_O2-O6"}


def main():
    png_dir = None
    if "--png" in sys.argv:
        png_dir = sys.argv[sys.argv.index("--png") + 1]
        os.makedirs(png_dir, exist_ok=True)
    if "--no-cad" not in sys.argv:
        # separate process: the CAD tree has its own parts.py / body.py that would shadow ours in sys.modules
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(HERE, "cad_extract.py")], capture_output=True, text=True)
        print((r.stdout or "").strip() or ("cad_extract failed, using the saved netlist/cad_centre.json: " + (r.stderr or "")[-300:]))
    import sheets  # after the CAD refresh: harness.py reads netlist/cad_centre.json at import
    os.makedirs(OUT, exist_ok=True)
    built = []
    bad = 0
    regions = {}
    for fn in sheets.SHEETS:
        s = fn()
        errs = s.check(s.expected)
        name = NAMES[fn.__name__] + ".svg"
        sub = "board" if fn.__name__.startswith("brd") else "schematic"
        path = os.path.join(OUT_BRD if sub == "board" else OUT, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf8") as f:
            f.write(s.svg())
        built.append((s, path))
        bc = getattr(s, "board_check", [])
        regions[s.code] = {"file": name, "rev": s.rev, "date": s.date, "title": s.title, "regions": s.regions,
                           "checks": {"errors": len(errs), "overlaps": len(s.overlaps), "board": len(getattr(s, "board_check", []))}}
        print(f"{s.code} rev {s.rev}: {len(s.pins)} pins, {len(s.nets) if hasattr(s, 'nets') else 0} nets, errors {len(errs)}, "
              f"overlaps {len(s.overlaps)}, warnings {len(s.warnings)}, board checks {len(bc)}")
        for e in errs:
            print("   ERR", e)
        for o in s.overlaps[:40]:
            print("   OVL", o)
        for w in s.warnings[:20]:
            print("   WRN", w)
        for b in bc:
            print("   BRD", b)
        bad += len(errs) + len(s.overlaps) + len(bc)
        if png_dir:
            try:
                import resvg_py
                svgp = s.svg().replace('width="420.0mm" height="297.0mm"', 'width="420" height="297"')
                data = resvg_py.svg_to_bytes(svg_string=svgp, width=3200,
                                             font_dirs=["/System/Library/Fonts", "/Library/Fonts",
                                                        "/System/Library/Fonts/Supplemental"])
                with open(os.path.join(png_dir, name.replace(".svg", ".png")), "wb") as f:
                    f.write(bytes(data))
            except ImportError:
                pass
    with open(os.path.join(HERE, "..", "netlist", "sheets.json"), "w", encoding="utf-8") as f:
        json.dump(regions, f, ensure_ascii=False, indent=1)
    write_hits(built)
    return built, bad


def write_hits(built):
    """netlist/sheethits.json: what can be clicked on each sheet in the page (page.py adds the texts).
    Schematics: every wire segment and pin with the net the connectivity check found, part body boxes.
    Boards with their own data (s.hits_custom, BRD-08): numbered wires, pads, part boxes. All in sheet mm (420 x 297).
    Boards / wiring sheets BRD-01~07: s.hits_keys = click targets named by the 3D model's info keys (hitkeys.py)."""
    r2 = lambda v: round(v, 2)  # noqa: E731
    out = {}
    for s, path in built:
        h = {}
        segs = [[r2(a), r2(b), r2(c), r2(d), n] for a, b, c, d, n in getattr(s, "hit_segs", []) if n]
        pins = [[ref, num, name, r2(x), r2(y), n] for ref, num, name, x, y, n in getattr(s, "hit_pins", [])]
        bodies = {}
        for x0, y0, x1, y1, ref in s.bodies:
            b = bodies.get(ref)
            bodies[ref] = [min(x0, b[0]), min(y0, b[1]), max(x1, b[2]), max(y1, b[3])] if b else [x0, y0, x1, y1]
        if segs or pins:
            h.update(segs=segs, pins=pins, parts=[[ref] + [r2(v) for v in b] for ref, b in bodies.items()])
        if getattr(s, "hits_custom", None):
            h["board"] = s.hits_custom
        if getattr(s, "hits_keys", None):           # BRD-01~07: where things are + which thing (hitkeys.py); texts come later
            h["keys"] = s.hits_keys
        if h:
            out[s.code] = h
    with open(os.path.join(HERE, "..", "netlist", "sheethits.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    b, bad = main()
    import export
    nets, bom = export.export(b)
    miss = export.check_refs(b, bom)
    for k, v in miss.items():
        print(f"   REF {k}: refdes on the sheet without a BOM row: {v}")
        bad += len(v)
    print(f"netlist rows {len(nets)}, bom rows {len(bom)}, problems {bad}")
    sys.exit(1 if bad else 0)
