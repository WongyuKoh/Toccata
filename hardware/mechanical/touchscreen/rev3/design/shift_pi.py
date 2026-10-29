# Toccata R31 touchscreen rev 3 - move the Pi 5 in y inside numbers.json without re-running geom3.py.
# 2026-10-26: the CAD moved the Pi 5 9 mm toward the keys (-y, body_L2.json centre.pi_move_2026_10_26) so a straight USB gender and a
# straight hub DC plug both fit. geom3.py needs the L2_cu digest from the CAD session (not kept in the repo), so this script shifts every
# Pi-derived number instead: the pi5 block, placement.pi5_mipi / keepout_zones, the ribbon and screen power-wire waypoints that end at
# the Pi (and their lengths). The screen, cradle, hinge, lid hole and vents do not depend on the Pi and stay as they are.
# Idempotent: numbers.json keeps the applied shift in "pi_shift"; run with the TOTAL shift wanted (python3 shift_pi.py -9).
import json, sys
from pathlib import Path

NUM = Path(__file__).resolve().parent / "numbers.json"
N = json.load(open(NUM))
want = float(sys.argv[1]) if len(sys.argv) > 1 else -9.0
done = float((N.get("pi_shift") or {}).get("dy", 0.0))
dy = want - done
r2 = lambda v: round(float(v) + dy, 2)


def ys(rng):                       # [y0, y1]
    return [r2(rng[0]), r2(rng[1])]


if abs(dy) > 1e-9:
    P = N["pi5"]
    P["origin"][1] = r2(P["origin"][1])
    P["board_y"] = ys(P["board_y"])
    for k in ("disp1", "disp0", "heatsink", "hdmi", "cad_disp1"):
        P[k]["y"] = ys(P[k]["y"])
    P["disp1"]["mouth"][1] = r2(P["disp1"]["mouth"][1])
    P["cad_disp1"]["keepout"]["y"] = ys(P["cad_disp1"]["keepout"]["y"])
    for k in ("gpio_pin2", "gpio_pin6"):
        P[k][1] = r2(P[k][1])
    N["poses"]["pi5"]["origin_xy"][1] = r2(N["poses"]["pi5"]["origin_xy"][1])
    M = N["placement"]["pi5_mipi"]
    M["disp1_mouth_xyz"][1] = r2(M["disp1_mouth_xyz"][1])
    for q in M["gpio_2_6_xyz"][:2]:
        q[1] = r2(q[1])
    for k in ("dsi", "gpio"):
        N["placement"]["keepout_zones"][k]["y"] = ys(N["placement"]["keepout_zones"][k]["y"])
    # ribbon: hinge hole y231.55 -> +y run at z61.2 -> -x -> down to the DISP1 mouth; the waypoints at the mouth y move, the +y run shortens
    old_mouth = P["disp1"]["mouth"][1] - dy
    for rb in (N["ribbon"], N["variants"]["connector_mirrored"]["ribbon"]):
        for w in rb["waypoints"]:
            if abs(w[1] - old_mouth) < 0.01:
                w[1] = r2(w[1])
    rb = N["ribbon"]
    rb["parts"]["run_y"] = r2(rb["parts"]["run_y"])
    rb["total"] = r2(rb["total"])
    rb["margin"] = round(rb["cable"] - rb["total"], 2)
    rb["margin_pct"] = round(100.0 * rb["margin"] / rb["cable"], 2)
    # screen power wire: lid hole -> +y run at z60.15 -> -x -> down to GPIO pins 2 / 6
    pw = N["power_wire"]
    old_pin = P["gpio_pin2"][1] - dy
    for w in pw["waypoints"]:
        if abs(w[1] - old_pin) < 0.01:
            w[1] = r2(w[1])
    pw["parts"]["run_to_gpio"] = r2(pw["parts"]["run_to_gpio"])
    pw["total"] = r2(pw["total"])
    N["pi_shift"] = dict(dy=want, date="2026-10-26", by="shift_pi.py",
                         why="CAD body_L2.json centre.pi_move_2026_10_26: Pi 5 9 toward the keys (straight gender + straight hub DC plug)",
                         note="geom3.py was not re-run (its L2_cu input is not in the repo); every Pi-derived number shifted here")
    open(NUM, "w").write(json.dumps(N, ensure_ascii=False, indent=1))
print("pi_shift", want, "applied now", dy, "ribbon", N["ribbon"]["total"], "margin", N["ribbon"]["margin"], "power wire", N["power_wire"]["total"])
