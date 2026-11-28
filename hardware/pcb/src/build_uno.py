"""Build the Arduino-version sheets (U-01..U-04) into hardware/pcb/uno/: SVG + connectivity / overlap checks + CSVs.

usage: python3 build_uno.py      (exit code 0 = no problems)
The Raspberry Pi version (build.py) is not touched.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.normpath(os.path.join(HERE, "..", "uno"))
NAMES = {"u01": "U-01_system", "u02": "U-02_control_board_MB-U", "u03": "U-03_bus_board_UB_uno", "u04": "U-04_power_audio"}


def main():
    import uno_sheets as U
    os.makedirs(os.path.join(OUT, "schematic"), exist_ok=True)
    bad, meta, netrows = 0, {}, []
    for fn in U.SHEETS:
        s = fn()
        errs = s.check(s.expected)
        name = NAMES[fn.__name__] + ".svg"
        with open(os.path.join(OUT, "schematic", name), "w", encoding="utf8") as f:
            f.write(s.svg())
        print(f"{s.code} rev {s.rev}: {len(s.pins)} pins, errors {len(errs)}, overlaps {len(s.overlaps)}, warnings {len(s.warnings)}")
        for x in errs + s.overlaps + s.warnings[:20]:
            print("   ", x)
        bad += len(errs) + len(s.overlaps)
        meta[s.code] = {"file": name, "title": s.title, "subtitle": s.subtitle, "rev": s.rev, "date": s.date,
                        "errors": len(errs), "overlaps": len(s.overlaps)}
        for net, pins in sorted(s.expected.items()):
            netrows.append([s.code, net, " ".join(sorted(pins))])
    with open(os.path.join(OUT, "sheets.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "netlist_uno.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["도면", "넷", "핀"])
        w.writerows(netrows)
    with open(os.path.join(OUT, "pins_uno.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["우노 핀", "넷", "UB 부품", "가는 곳"])
        for k in range(4):
            w.writerow([U.UNO_S[k], f"MUX_S{k}", f"R80{k+1} 1k", "J801~J807 핀 %d (7 포트 공통)" % (4 + k)])
        for m in range(1, 8):
            w.writerow([U.UNO_EN[m], f"EN_O{m}", f"R81{m} 1k", f"J80{m} 핀 8 → O{m} 먹스 EN"])
        w.writerow(["A0", "SIG_BUS", "R808 2.2k ← R841~R847 1k", "J801~J807 핀 2"])
        w.writerow(["A1", "PED_ADC", "R805 1k · R806 100k · C801 100n", "J808 T (페달 잭)"])
        w.writerow(["A2", "V_MON", "R831 · R832 10k/10k", "+5V_B ÷ 2"])
        w.writerow(["D13", "LED", "—", "보드 LED"])
        w.writerow(["5V", "—", "—", "연결 금지"])
        w.writerow(["GND", "GND", "—", "UB GND"])
    with open(os.path.join(OUT, "ribbon_uno.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["W", "모듈", "자르는 길이 (mm)", "모듈 쪽", "UB 쪽", "우노 EN"])
        for m in range(1, 8):
            w.writerow([f"W80{m}", f"O{m}", U.CUTS[m], "MB-U J303 납땜", f"J80{m} IDC 2×5", U.UNO_EN[m]])
        w.writerow([])
        w.writerow(["핀", "넷", "뜻"])
        for i, (n, t) in enumerate(zip(U.BUS, U.BUS_TXT)):
            w.writerow([i + 1, n, t])
    with open(os.path.join(OUT, "changes_uno.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["구분", "물건", "수량 · 대신"])
        for r in U.CHANGES_IN:
            w.writerow(["더함"] + r)
        for r in U.CHANGES_OUT:
            w.writerow(["뺌"] + r)
    return bad


if __name__ == "__main__":
    b = main()
    print("problems", b)
    sys.exit(1 if b else 0)
