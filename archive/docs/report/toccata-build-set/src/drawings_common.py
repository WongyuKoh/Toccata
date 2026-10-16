"""All engineering drawings for the Toccata build report (inline SVG, mm units)."""
import math
from draw import View, fmt_mm, ord_y, ord_z
from model import L, KEYS, TAILS, METHODS, rot, rib_z0

_uid = [0]


def uid(p):
    _uid[0] += 1
    return f"{p}{_uid[0]}"


def hatch(v, kind="wood", spacing_px=6, ang=45):
    pid = uid("h")
    sp = v.px(spacing_px)
    v.defs.append(
        f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="{sp:.3f}" height="{sp:.3f}" '
        f'patternTransform="rotate({ang})"><line x1="0" y1="0" x2="0" y2="{sp:.3f}" class="hl-{kind}"/></pattern>')
    return pid


def hrect(v, u, w0, w, h, pid, cls):
    v.rect(u, w0, w, h, cls=cls)
    y = v.Y(w0 + h)
    v.el.append(f'<rect x="{u:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="url(#{pid})" class="nostroke"/>')


def hpoly(v, pts, pid, cls):
    v.poly(pts, cls=cls)
    v.el.append(f'<polygon points="{" ".join(v.P(a, b) for a, b in pts)}" fill="url(#{pid})" class="nostroke"/>')


def rotate_pts(pts, c, a):
    return [rot(p, c, a) for p in pts]


# =================================================================== common side-view parts
def front_rail_end(M):
    """rear end (y) of the printed front rail: 10 mm behind the black stop, 4 mm in D (hammer at 60)."""
    return M["stop_b_y"] + (10.0 if M["id"] != "D" else 4.0)


def black_pad_half(M):
    """half length (y) of the black down-stop felt pad, kept on the front rail."""
    return min(7.0, front_rail_end(M) - M["stop_b_y"])


def side_common(v, M, y_end, pids, show_front=True, sensor=True):
    wood, steel, prt = pids["wood"], pids["steel"], pids["print"]
    bt = L["base_t"]
    # keybed plywood
    hrect(v, -2, -bt, y_end + 2, bt, wood, "m-wood")
    # key slip (front cover)
    hrect(v, -2 - L["slip_gap"] - L["slip_t"], -bt, L["slip_t"], bt + M["slip_top"], wood, "m-wood")
    # front rail (printed) : white section + black step
    yb = M["stop_b_y"]
    rail_end = front_rail_end(M)
    pts = [(6, 0), (rail_end, 0), (rail_end, M["rail_b_top"]), (40, M["rail_b_top"]),
           (40, M["rail_w_top"]), (6, M["rail_w_top"])]
    hpoly(v, pts, prt, "m-print")
    # white down-stop felt strip
    v.rect(8, M["rail_w_top"], 20, L["felt"], cls="m-felt")
    # black down-stop pad (behind the section plane)
    hl = black_pad_half(M)
    v.rect(yb - hl, M["rail_b_top"], 2 * hl, L["felt"], cls="m-felt ph")
    # guide pins (white in section, black phantom): M.pin_len long, L.pin_depth in the plywood
    pd = L["pin_d"]
    v.rect(M["guide_w_y"] - pd / 2, -L["pin_depth"], pd, M["pin_len"], cls="m-steel")
    v.rect(M["guide_b_y"] - pd / 2, -L["pin_depth"], pd, M["pin_len"], cls="m-steel ph")
    M["_pin_top"] = M["pin_top"]
    # sensor rail
    if sensor:
        st = M["sensor_top"]
        y0, y1 = M.get("srail", (98, 126))
        r0, r1 = L["y_sensor"] - L["pocket_h"], L["y_sensor"] + L["pocket_h"]
        c0, c1 = L["wire_ch"]
        pd, ls, ys = L["pocket_d"], L["lead_slot"], L["y_sensor"]
        # the recess floor runs on as a narrow lead groove to the wire channel, then an ls-wide slot drops
        # into the channel (section at the key centre: rail cut in two; the recess end at r1 is seen beyond)
        hpoly(v, [(y0, 0), (y0, st), (r0, st), (r0, st - pd), (c0, st - pd), (c0, 0)], prt, "m-print")
        hpoly(v, [(c0 + ls, 5), (c0 + ls, st), (y1, st), (y1, 0), (c1, 0), (c1, 5)], prt, "m-print")
        v.line(r1, st - pd, r1, st, cls="ln")
        # TO-92 lying flat, leads along the groove and down the slot to the channel
        v.rect(ys - 1.5, st - 1.52, 3.0, 1.52, cls="m-sensor")
        v.line(ys + 1.5, st - 0.76, c0 + ls / 2, st - 0.76, cls="lead")
        v.line(c0 + ls / 2, st - 0.76, c0 + ls / 2, 4.0, cls="lead")
        v.line(c0 + ls / 2, 4.0, c0 + 2, 3.0, cls="lead")
        for dw in (2.0, 4.0, 6.4):              # VCC / GND bus + signal wires in the channel
            v.circle(c0 + dw, 2.5, 1.1, cls="m-wire")


def lid(v, M, y0, y1, pids):
    hrect(v, y0, M["lid_bot"], y1 - y0, L["lid_t"], pids["wood"], "m-wood")
    uy = M["upstop_y"]
    v.rect(uy[0], M["lid_bot"] - L["felt"], uy[1] - uy[0], L["felt"], cls="m-felt")


def white_key_outline(M, y_end=None):
    y_end = y_end or M["body_end"]
    zb, zt = M["z_bot"], M["z_top"]
    return [(0, zb), (y_end, zb), (y_end, zt), (0, zt)]


def key_section(v, M, pids, ribs, bosses, y_end=None, rear_wall=True):
    """white key cut at its centre plane: far wall (light) + cut skin/walls/ribs/bosses (hatched)."""
    y_end = y_end or M["body_end"]
    zb, zt, s = M["z_bot"], M["z_top"], L["skin"]
    kp = pids["key"]
    v.rect(0, zb, y_end, zt - zb, cls="m-keyfar")
    hrect(v, 0, zt - s, y_end, s, kp, "m-key")                   # top skin
    hrect(v, 0, zb, 2.4, zt - zb - s, kp, "m-key")               # front wall
    if rear_wall:
        hrect(v, y_end - 1.6, zb, 1.6, zt - zb - s, kp, "m-key")
    for y in ribs:
        # rib lower edge: explicit (y, z0) or from the model (shortened over a rising hammer)
        y, z0 = y if isinstance(y, tuple) else (y, rib_z0(M, y))
        if z0 is None:
            continue
        hrect(v, y - L["rib"] / 2, zb + z0, L["rib"], zt - zb - s - z0, kp, "m-key")
    for (y0, y1, z0, z1) in bosses:
        hrect(v, y0, z0, y1 - y0, z1 - z0, kp, "m-key")
    v.poly(white_key_outline(M, y_end), cls="edge")


def black_phantom(v, M, tx=None, label="흑건 윗면"):
    """black key top (behind the section plane) as a phantom line, labelled just above its flat top.
    tx=None: the label goes where it crosses no leader/dimension/outline stroke of the finished view
    (resolved in View.svg(), so balloons drawn later are avoided), as near the middle as possible."""
    zt, zb = M["z_top"], M["z_black"]
    y0, y1 = L["head"], L["black_end"]
    c = L["black_chamfer"]
    v.poly([(y0, zt), (y0 + c, zb), (y1, zb), (y1, zt)], cls="ph2", closed=False)
    tz, sz = zb + v.px(5), 10
    if tx is not None:
        v.text(tx, tz, label, cls="tx-s", size_px=sz)
        return
    v.late(lambda vw: vw._text_el(vw.text_free(y0 + c, y1, tz, label, size_px=sz), tz, label, cls="tx-s", size_px=sz))


def pressed_outline(v, M, pts, c=None, a=None):
    c = c or M["pivot"]
    a = M["theta"] if a is None else a
    v.poly(rotate_pts(pts, c, a), cls="pressed")


def magnet(v, y, z_face, up=True):
    # z_face = the face toward the sensor
    if up:   # magnet sits in key, face at bottom
        v.rect(y - 3, z_face, 6, 1.5, cls="m-magS")
        v.rect(y - 3, z_face + 1.5, 6, 1.5, cls="m-magN")
    else:
        v.rect(y - 3, z_face - 3, 6, 1.5, cls="m-magN")
        v.rect(y - 3, z_face - 1.5, 6, 1.5, cls="m-magS")


def spring_zig(v, y, z0, z1, d_out=6.0, turns=8):
    r = d_out / 2
    pts = [(y - r, z0)]
    n = turns * 2
    for i in range(1, n + 1):
        zz = z0 + (z1 - z0) * i / n
        pts.append((y + (r if i % 2 else -r), zz))
    v.poly(pts, cls="spring", closed=False)


def z_ruler(v, u, levels, left=False):
    """stacked z dimensions from 0 to each level (baseline dims)."""
    step = v.px(34)
    for i, (z, lab) in enumerate(levels):
        uu = u + (i * step if not left else -i * step)
        v.dim_v(0, z, uu, text=fmt_mm(z, 1))
        v.text(uu, z + v.px(14), lab, cls="tx-s", size_px=9.5)


def y_baseline(v, zline, feats, z_from=None, step_px=19):
    """stacked y baseline dims from y=0 to each feature (feats sorted)."""
    for i, (y, lab) in enumerate(feats):
        zz = zline - i * v.px(step_px)
        v.dim_h(0, y, zz, text=f"{fmt_mm(y, 1)}", ext_from=None)
        v.line(y, zz - v.px(3), y, (z_from if z_from is not None else zz), cls="ex")
        if lab:
            v.text(y + v.px(4), zz - v.px(10), lab, cls="tx-s", anchor="start", size_px=9.5)


def std_pids(v):
    return dict(wood=hatch(v, "wood", 7, 45), steel=hatch(v, "steel", 4, -45),
                print=hatch(v, "print", 5, 45), key=hatch(v, "key", 4, -45))


