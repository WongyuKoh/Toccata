"""Build all Toccata schematic sheets: SVG + connectivity check (+ PNG preview if resvg_py is available).

usage: python3 build.py [--png DIR]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sheets  # noqa: E402

OUT = os.path.join(HERE, "..", "schematic")
OUT_BRD = os.path.join(HERE, "..", "board")
NAMES = {"sch01": "SCH-01_system", "sch02": "SCH-02_sensor_board", "sch03": "SCH-03_control_board",
         "sch04": "SCH-04_end_parts", "sch05": "SCH-05_pedal", "sch06": "SCH-06_power", "sch07": "SCH-07_audio",
         "brd01": "BRD-01_control_board_placement", "brd02": "BRD-02_sensor_board_placement"}


def main():
    png_dir = None
    if "--png" in sys.argv:
        png_dir = sys.argv[sys.argv.index("--png") + 1]
        os.makedirs(png_dir, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    built = []
    bad = 0
    for fn in sheets.SHEETS:
        s = fn()
        errs = s.check(s.expected)
        name = NAMES[fn.__name__] + ".svg"
        path = os.path.join(OUT_BRD if fn.__name__.startswith("brd") else OUT, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf8") as f:
            f.write(s.svg())
        built.append((s, path))
        print(f"{s.code}: {len(s.pins)} pins, {len(s.nets)} nets, errors {len(errs)}, overlaps {len(s.overlaps)}, warnings {len(s.warnings)}")
        for e in errs:
            print("   ERR", e)
        for o in s.overlaps[:40]:
            print("   OVL", o)
        for w in s.warnings[:20]:
            print("   WRN", w)
        bad += len(errs)
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
    return built, bad


if __name__ == "__main__":
    b, bad = main()
    import export
    nets, bom = export.export(b)
    print(f"netlist rows {len(nets)}, bom rows {len(bom)}")
    sys.exit(1 if bad else 0)
