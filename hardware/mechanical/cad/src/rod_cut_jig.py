"""Rod cut jigs (2026-11-22, user: '봉을 넣고 자를 수 있는 고정대 ... 길이별로 각각').

The key rods and lever rods are cut from the 1 m SUS304 D4 bars (i066 / i067). One jig per cut length:

    161.4  module key rod + lever rod (14 pieces, both kinds the same length)
     45.9  EL lever rod      43.9  EL key rod      22.2  ER lever rod      20.4  ER key rod

Each jig is a flat plate (lies on the desk) carrying a row of guide blocks with one horizontal D4 bore along x:

    x = -S .. 0   stop block: the bore is closed by the separate end plug (마개) - flange on the outer face, stub S deep
    x = 0         rod end touches the stub tip here (viewing window from the top just past it)
    x = L         saw slot near face: the piece between the stub tip and the slot is L long; the blade runs in the slot
                  on the waste side (x L .. L + KERF), so the bar's remaining end is what leaves the jig
    x = L + OUT   outfeed end (bore entry chamfer) - the bar comes in here

Pull the plug to push the cut piece out through the stop end.
Lengths and allowed ranges: geometry.json end_parts + module (see the 2026-11-22 tolerance check):
module 160.8..161.5, EL lever 45.3..46.0, EL key 43.0..44.2, ER lever 19.5..22.3, ER key 19.5..20.7.
The slot sits at the nominal length; squaring the sawn end with a file takes ~0.1..0.3 off, which lands inside the range.

Printed on its plate, no supports: horizontal bore = teardrop (apex +z), window and slot open upward, the plug prints on its
flange. Bore D4.5 = the A18 fin-boss bore (the rod slides through a horizontal teardrop of that size on the user's P1S).
"""
import os

from cadlib import box, cone_z, cyl_z, diff, orient, rot_y, teardrop_x, text_xy, to_bed, union, write_stl  # noqa: F401

PRINT_SUB = "10_봉절단지그"

J = {
    "ax_z": 9.0,          # rod axis above the desk
    "bore": 4.5,          # teardrop bore (A18 fin boss: rod slides through)
    "plate_t": 3.0,
    "plate_w": 40.0,
    "blk_w": 16.0,        # guide block width (y)
    "blk_top": 16.0,      # guide block top z
    "stub": 4.0,          # plug stub depth = stop block outer face -> stop face (x = 0)
    "stop_len": 12.0,     # stop block x -stub .. -stub + stop_len
    "win": (0.6, 6.0),    # viewing window over x 0.6 .. 6.0 (rod end visible against the stub tip)
    "kerf": 1.3,          # saw slot width (hacksaw blade 0.65, set ~1.0)
    "slot_floor": 5.5,    # slot bottom z (rod bottom at ax_z - 2 = 7.0)
    "cut_in": 10.0,       # cut block reaches back x L - cut_in
    "out": 12.0,          # cut block reaches out to x L + out (outfeed bore length past the slot)
    "saddle_len": 8.0,
    "saddle_gap": 40.0,   # max open span between blocks
    "chamfer": 6.5,       # bore entry chamfer diameter at the outfeed end
    # plug
    "flange_d": 14.0, "flange_t": 2.0, "tab": (9.0, 6.0), "stub_d": 4.2, "rib_tip_d": 4.6, "rib_w": 0.8,
}

LENGTHS = [
    ("161.4", 161.4, "모듈_건반봉·레버봉", "14토막 (건반 봉 7 + 레버 봉 7)", "160.8~161.5"),
    ("45.9", 45.9, "EL_레버봉", "1토막", "45.3~46.0"),
    ("43.9", 43.9, "EL_건반봉", "1토막", "43.0~44.2"),
    ("22.2", 22.2, "ER_레버봉", "1토막", "19.5~22.3"),
    ("20.4", 20.4, "ER_건반봉", "1토막", "19.5~20.7"),
]


def _blocks(L):
    """[(x0, x1)] guide blocks: stop block, saddles every <= saddle_gap, cut block; merged where they touch."""
    s, z = J["stub"], []
    stop = (-s, -s + J["stop_len"])
    cut = (L - J["cut_in"], L + J["out"])
    z.append(stop)
    a = stop[1]
    span = cut[0] - a
    if span > J["saddle_gap"]:
        n = int(span // (J["saddle_gap"] + J["saddle_len"]))
        n = max(1, n)
        gap = (span - n * J["saddle_len"]) / (n + 1)
        for i in range(n):
            x0 = a + gap * (i + 1) + J["saddle_len"] * i
            z.append((x0, x0 + J["saddle_len"]))
    z.append(cut)
    z.sort()
    merged = [list(z[0])]
    for x0, x1 in z[1:]:
        if x0 <= merged[-1][1] + 3.0:         # gaps under 3 mm are not worth leaving open
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    return [tuple(b) for b in merged]


def jig(key, L, who, count, rng):
    s, ax = J["stub"], J["ax_z"]
    x_a, x_b = -s, L + J["out"]
    hw, bw = J["plate_w"] / 2.0, J["blk_w"] / 2.0
    body = [box(x_a, x_b, -hw, hw, 0, J["plate_t"])]
    for x0, x1 in _blocks(L):
        body.append(box(x0, x1, -bw, bw, 0, J["blk_top"]))
    m = union(body)
    cuts = [teardrop_x(0.0, ax, x_a - 1, x_b + 1, J["bore"])]
    # bore entry chamfer at the outfeed end (a 45 deg cone along x, printed sideways: its roof is 45 deg)
    cone = orient(cone_z(0, 0, 0, (J["chamfer"] - J["bore"]) / 2.0 + 0.01, J["chamfer"], J["bore"]), rot_y(-90))
    cuts.append(cone.translate((x_b + 0.01, 0, ax)))
    # viewing window just past the stop face, open from the top down to the rod axis
    w0, w1 = J["win"]
    cuts.append(box(w0, w1, -bw - 1, bw + 1, ax, J["blk_top"] + 1))
    # saw slot: near face at x = L, through the block width, down to slot_floor
    cuts.append(box(L, L + J["kerf"], -bw - 1, bw + 1, J["slot_floor"], J["blk_top"] + 1))
    # labels debossed 0.6 in the plate top (front strip y -hw .. -bw), reading from the front
    pt = J["plate_t"]
    txt_y = -(hw + bw) / 2.0
    big = "%s mm" % key
    lab_x = min(max((x_a + x_b) / 2.0, x_a + 14), x_b - 14)
    cuts.append(text_xy(big, 5.0 if L > 60 else 4.0, 1.0, lab_x, txt_y, pt - 0.6, "center", "center", heavy=True))
    if L > 60:
        cuts.append(text_xy("%s · %s" % (who.replace("_", " "), count), 3.2, 1.0, lab_x, hw - 6.0 + 0.0, pt - 0.6,
                            "center", "center", heavy=True))
        cuts.append(text_xy("마개", 3.2, 1.0, x_a + 7.0, hw - 6.0, pt - 0.6, "center", "center", heavy=True))
        cuts.append(text_xy("톱", 3.2, 1.0, L + 0.65, txt_y, pt - 0.6, "center", "center", heavy=True))
    else:
        cuts.append(text_xy(who.replace("_", " "), 3.0, 1.0, lab_x, (hw + bw) / 2.0, pt - 0.6, "center", "center", heavy=True))
    return diff(m, cuts)


def plug():
    """end plug: flange (with a pull tab) on the bed, stub up; 3 crush ribs on the stub (tips D rib_tip_d)."""
    fd, ft = J["flange_d"], J["flange_t"]
    tl, tw = J["tab"]
    parts = [cyl_z(0, 0, 0, ft, fd), box(0, fd / 2.0 + tl, -tw / 2.0, tw / 2.0, 0, ft)]
    sd, h = J["stub_d"], J["stub"]
    parts.append(cyl_z(0, 0, ft - 0.01, ft + h, sd))
    import math
    rw, rt = J["rib_w"], J["rib_tip_d"] / 2.0
    for i in range(3):
        a = math.radians(90 + 120 * i)
        r_ = box(sd / 2.0 - 0.4, rt, -rw / 2.0, rw / 2.0, ft - 0.01, ft + h - 0.6)
        parts.append(orient(r_, ((math.cos(a), -math.sin(a), 0), (math.sin(a), math.cos(a), 0), (0, 0, 1))))
    m = union(parts)
    # 0.4 lead-in chamfer at the stub tip so it starts into the bore
    tip = diff(cyl_z(0, 0, ft + h - 0.6, ft + h + 1, fd), [cone_z(0, 0, ft + h - 0.6, ft + h, sd + 0.4, sd - 0.8)])
    return diff(m, [tip])


def est_print(m):
    """same rough estimate as perfboard_jigs.est_print (3 walls, 15 % infill)."""
    V = m.volume()
    A = m.surface_area()
    shell = min(V, A * 1.1)
    printed = shell + 0.15 * (V - shell)
    g = printed / 1000.0 * 1.27
    h = m.bounding_box()[5]
    minutes = printed / 9.0 / 60.0 + h / 0.2 * 2.5 / 60.0 + 3.0
    return g, minutes


def build():
    out = []
    for key, L, who, count, rng in LENGTHS:
        out.append({"key": "rodjig-%s" % key, "name": "봉절단지그_%s_%s" % (key, who), "qty": 1,
                    "solid": to_bed(jig(key, L, who, count, rng)),
                    "note": "1 m Ø4 봉 → %s mm %s (허용 %s). 마개를 끼우고 봉을 끝까지 밀어 넣은 뒤 톱 홈으로 자름" % (key, count, rng)})
    out.append({"key": "rodjig-plug", "name": "봉절단지그_끝마개", "qty": len(LENGTHS), "solid": to_bed(plug()),
                "note": "지그마다 1개 (모두 같은 모양). 플랜지를 베드에, 꼭지를 위로"})
    return out


def write_files(root):
    paths = {}
    for j in build():
        path = os.path.join(root, PRINT_SUB, "%s__%d개.stl" % (j["name"], j["qty"]))
        write_stl(j["solid"], path, "Toccata %s x%d rod cut jig" % (j["key"], j["qty"]))
        paths[j["name"]] = path
    return paths


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(here, "..", "stl", "print")
    for j in build():
        b = j["solid"].bounding_box()
        g, mins = est_print(j["solid"])
        print("%-34s x%d  %.1f x %.1f x %.1f mm  ~%.0f g  ~%.0f min" % (j["name"], j["qty"], b[3] - b[0], b[4] - b[1], b[5] - b[2], g, mins))
    for n, p in write_files(root).items():
        print(os.path.relpath(p, os.path.join(here, "..")))
