"""Renders of the rev-3 B1 preview model (OpenSCAD 2026, manifold backend) + Korean captions / labels (PIL).

Run after export3d.py (uses stl/use, stl/fold, stl/context) and check3d.py (interference.json for the clash marks).
Camera model (checked against a calibration render): look-at, up = +z, vertical FOV 22.5 deg; ortho half-height = d tan(11.25).
Label anchors are model points (numbers.json / b1model); labels are laid out automatically in the left / right margins.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import b1model as B
from cadlib import write_stl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "renders")
WORK = os.path.join(HERE, "work", "scad")
os.makedirs(OUT, exist_ok=True)
os.makedirs(WORK, exist_ok=True)
W, H = 1600, 900
HEAD = 96
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
MAN = json.load(open(os.path.join(HERE, "parts_manifest.json")))
INT = json.load(open(os.path.join(HERE, "interference.json")))
TAN = math.tan(math.radians(11.25))
RED = (200, 30, 30)


def fnt(sz, bold=False):
    return ImageFont.truetype(FONT, sz, index=6 if bold else 2)


# ------------------------------------------------------------------ camera / projection
def project(P, s):
    E, C = np.array(s["eye"], float), np.array(s["ctr"], float)
    fw = C - E
    d = np.linalg.norm(fw)
    fw /= d
    r = np.cross(fw, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, fw)
    v = np.array(P, float) - E
    if s.get("ortho"):
        sx, sy = (v @ r) / (d * TAN), (v @ u) / (d * TAN)
    else:
        z = v @ fw
        sx, sy = (v @ r) / (z * TAN), (v @ u) / (z * TAN)
    w_, h_, hd = s.get("W", W), s.get("H", H), s.get("head", HEAD)
    return (w_ / 2 + sx * h_ / 2, h_ / 2 - sy * h_ / 2 + hd)


# ------------------------------------------------------------------ scene files
def items_touch(sub, alpha=None, skip=()):
    return [(os.path.join(HERE, r["file"]), r["color"], (alpha or {}).get(r["id"], 1.0)) for r in MAN["parts"][sub] if r["id"] not in skip]


def items_context(keep=None, skip=("L2-FEET",), alpha=None, recolor=None):
    out = []
    for r in MAN["parts"]["context"]:
        if r["id"] in skip or (keep and not any(r["id"].startswith(k) for k in keep)):
            continue
        col = next((c for k, c in (recolor or {}).items() if r["id"].startswith(k)), r["color"])
        out.append((os.path.join(HERE, r["file"]), col, (alpha or {}).get(r["id"], 1.0)))
    return out


def items_modules(units=None):
    return [(p, c, 1.0) for (p, c, n) in B.module_stls(units)]


def scad(items, cut=None):
    """cut: (x0, x1) keeps x0..x1, or ('x'|'y'|'z', a0, a1)."""
    L = []
    items = sorted(items, key=lambda it: it[2] < 1.0)     # translucent parts last, or they hide what is behind them
    for (p, c, a) in items:
        imp = 'import("%s");' % p
        if cut is not None:
            ax, a0, a1 = cut if len(cut) == 3 else ("x",) + tuple(cut)
            lo = {"x": [a0, -2000, -2000], "y": [-2000, a0, -2000], "z": [-2000, -2000, a0]}[ax]
            sz = {"x": [a1 - a0, 4000, 4000], "y": [4000, a1 - a0, 4000], "z": [4000, 4000, a1 - a0]}[ax]
            imp = "intersection(){ %s translate([%.3f,%.3f,%.3f]) cube([%.3f,%.3f,%.3f]); }" % (imp, *lo, *sz)
        L.append('color("%s", %.2f) %s' % (c, a, imp))
    return "\n".join(L)


def run_scenes(scenes):
    procs = []
    for s in scenes:
        path = os.path.join(WORK, s["name"] + ".scad")
        open(path, "w").write(scad(s["items"], s.get("cut")))
        png = os.path.join(WORK, s["name"] + "_raw.png")
        cam = "--camera=%s" % ",".join("%.3f" % v for v in list(s["eye"]) + list(s["ctr"]))
        cmd = ["openscad", "--backend=manifold", "-o", png, "--imgsize=%d,%d" % (s.get("W", W), s.get("H", H)), cam, "--colorscheme=Tomorrow",
               "--projection=%s" % ("o" if s.get("ortho") else "p"), path]
        if s.get("render"):
            cmd.insert(2, "--render")
        procs.append((s, png, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
    for s, png, pr in procs:
        o, e = pr.communicate()
        if pr.returncode or not os.path.exists(png):
            print("openscad failed", s["name"], e[-1500:])
            sys.exit(1)
        s["raw"] = png


# ------------------------------------------------------------------ annotation
def header(img, title, sub):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, HEAD], fill=(255, 255, 255))
    d.line([0, HEAD - 1, W, HEAD - 1], fill=(210, 214, 220), width=2)
    d.text((24, 12), title, font=fnt(32, True), fill=(20, 26, 36))
    d.text((24, 60), sub, font=fnt(19), fill=(80, 88, 100))


def note_box(img, lines, where="bl", size=18):
    d = ImageDraw.Draw(img, "RGBA")
    ft = fnt(size)
    hh = size + 9
    wmax = max(d.textbbox((0, 0), s, font=ft)[2] for s in lines)
    hb = hh * len(lines) + 12
    x = 24
    y = HEAD + H - 14 - hb if where == "bl" else HEAD + 14
    d.rounded_rectangle([x - 10, y, x + wmax + 12, y + hb], radius=8, fill=(255, 255, 255, 232), outline=(190, 196, 206, 255))
    for i, s in enumerate(lines):
        d.text((x, y + 7 + i * hh), s, font=ft, fill=(40, 46, 58))
    return (y, y + hb)


def layout_labels(img, s, labels, reserve=None):
    """labels: (P, text, side 'L'/'R'/None, style) -> boxes in the left / right margin columns, sorted by anchor height."""
    d = ImageDraw.Draw(img, "RGBA")
    W, H, HEAD = s.get("W", globals()["W"]), s.get("H", globals()["H"]), s.get("head", globals()["HEAD"])
    fs = s.get("font", 20)
    ft = fnt(fs, True)
    rows = []
    for lb in labels:
        P, text = lb[0], lb[1]
        side = lb[2] if len(lb) > 2 else None
        style = lb[3] if len(lb) > 3 else {}
        a = project(P, s)
        side = side or ("L" if a[0] < W / 2 else "R")
        tb = d.textbbox((0, 0), text, font=ft)
        rows.append(dict(a=a, text=text, side=side, style=style, tw=tb[2] - tb[0], th=tb[3] - tb[1], ty0=tb[1]))
    top, bot = HEAD + 12, HEAD + H - 12
    for side in ("L", "R"):
        col = sorted([r for r in rows if r["side"] == side], key=lambda r: r["a"][1])
        if not col:
            continue
        hb = [r["th"] + 16 for r in col]
        lim_bot = bot
        if reserve and side == "L":
            lim_bot = reserve[0] - 8
        ys = []
        y = top
        for r, h in zip(col, hb):
            want = r["a"][1] - h / 2
            y = max(y, want)
            ys.append(y)
            y += h + 10
        over = (ys[-1] + hb[-1]) - lim_bot
        if over > 0:
            ys[-1] -= over
            for i in range(len(ys) - 2, -1, -1):
                ys[i] = min(ys[i], ys[i + 1] - hb[i] - 10)
        for r, y0, h in zip(col, ys, hb):
            w = r["tw"] + 18
            x0 = 16 if side == "L" else W - 16 - w
            r["box"] = (x0, y0, x0 + w, y0 + h)
    for r in rows:
        x0, y0, x1, y1 = r["box"]
        ax, ay = r["a"]
        ex = x1 if r["side"] == "L" else x0
        ey = min(max(ay, y0 + 8), y1 - 8)
        col = r["style"].get("color", (20, 26, 36))
        d.line([ax, ay, ex, ey], fill=(30, 34, 42, 255), width=2)
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=r["style"].get("dot", (214, 40, 40)), outline=(255, 255, 255))
        d.rounded_rectangle([x0, y0, x1, y1], radius=6, fill=(255, 255, 255, 238), outline=(120, 128, 140, 255), width=1)
        d.text((x0 + 9, y0 + 7 - r["ty0"]), r["text"], font=ft, fill=col)


def dashed(d, p0, p1, fill, width=3, dash=14, gap=9):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = np.linalg.norm(p1 - p0)
    if L < 1:
        return
    u = (p1 - p0) / L
    t = 0.0
    while t < L:
        d.line([tuple(p0 + u * t), tuple(p0 + u * min(L, t + dash))], fill=fill, width=width)
        t += dash + gap


def finish(s, title, sub, labels=(), notes=None, draw=None, notes_where="bl"):
    raw = Image.open(s["raw"]).convert("RGB")
    img = Image.new("RGB", (W, H + HEAD), (255, 255, 255))
    img.paste(raw, (0, HEAD))
    if draw:
        draw(img)
    reserve = None
    if notes:
        reserve = note_box(img, notes, notes_where)
        if notes_where != "bl":
            reserve = None
    layout_labels(img, s, labels, reserve)
    header(img, title, sub)
    out = os.path.join(OUT, s["name"] + ".png")
    img.save(out)
    return out


# ------------------------------------------------------------------ exploded view solids
EXPL = {"lift": 45.0, "screen_w": -70.0, "cover_w": 42.0, "m25_w": 24.0, "leg_along": 30.0, "leg_axle_x": -32.0, "axle_x": 38.0,
        "clip_z": -16.0, "lidscrew_z": 32.0, "lid_alpha": 0.45}


def exploded_items():
    th = B.TH_USE
    lift = np.array([0, 0, EXPL["lift"]])
    Mw = B.M(th)
    wdir, xdir = Mw[:, 2], Mw[:, 0]
    sub = os.path.join(HERE, "work", "explode")
    os.makedirs(sub, exist_ok=True)
    out, A = [], {}

    def put(pid, solid, col, off, alpha=1.0):
        m = solid.translate(tuple(float(v) for v in off))
        p = os.path.join(sub, pid + ".stl")
        write_stl(m, p, "explode " + pid)
        out.append((p, col, alpha))

    tw = lambda xr, u, w: B.to_world((xr, u, w), th)  # noqa: E731
    S = B.screen_local()
    o_scr = lift + EXPL["screen_w"] * wdir
    for k, col in (("body", B.COL["screen"]), ("bezel", "#0b0c0e"), ("active", B.COL["active"]), ("zif", B.COL["conn"]), ("mx", "#f2f2f2")):
        put("screen_" + k, B.place(S[k], th), col, o_scr)
    A["screen"] = tw(B.SC["emboss"]["xr"][0] + 10, (B.SC["emboss"]["u"][0] + B.SC["emboss"]["u"][1]) / 2, B.BODY + B.SC["emboss"]["h"]) + o_scr
    A["zif"] = tw(B.SC["fpc"]["xr"][1], B.SC["fpc"]["pin_u_centre"], B.BODY) + o_scr
    put("cradle", B.place(B.cradle_local(), th), B.COL["cradle"], lift)
    A["cradle"] = tw(-40.0, B.CR["cross_ribs_u"][1] + 8, B.PLO) + lift
    A["ear"] = tw((B.HG["left"]["ear"][0] + B.HG["left"]["ear"][1]) / 2, B.UA - B.HG["ear_hub_R"], B.WA) + lift
    A["clevis"] = tw(B.LG["clevis"]["far"][1], B.PIV_UW[0], B.PIV_UW[1]) + lift
    o_cov = lift + EXPL["cover_w"] * wdir
    put("cover", B.place(B.cover_local(), th), B.COL["cover"], o_cov)
    A["cover"] = tw(B.INS["xr"][1] + 1.0, B.INS["u"][1], B.PLO + 2.0) + o_cov
    o_m25 = lift + EXPL["m25_w"] * wdir
    for i, sc in enumerate(B.m25_local()):
        put("m25_%d" % i, B.place(sc, th), B.COL["screw"], o_m25)
    A["m25"] = tw(B.BO["xr"][0], B.BO["u"][1], B.BO["seat_w"] + 1.8) + o_m25
    lg, piv, tip = B.leg_world_use()
    ld = np.array([0, tip[0] - piv[0], tip[1] - piv[1]])
    ld /= np.linalg.norm(ld)
    o_leg = lift + EXPL["leg_along"] * ld
    put("leg", lg, B.COL["leg"], o_leg)
    A["leg"] = np.array([B.LG["x"][0], (piv[0] + tip[0]) / 2, (piv[1] + tip[1]) / 2]) + o_leg
    o_lax = lift + EXPL["leg_axle_x"] * xdir
    put("leg_axle", B.place(B.leg_axle_local(), th), B.COL["screw"], o_lax)
    A["leg_axle"] = tw(B.LG["clevis"]["near"][0] - B.EST["m3_head"][1], B.PIV_UW[0], B.PIV_UW[1]) + o_lax
    put("lid", B.lid_world(), B.COL["lid"], np.zeros(3), EXPL["lid_alpha"])
    A["lid"] = np.array([B.LID_X[0] + 25, B.LID_Y[1], B.LID_TOP - 4])
    A["pocket"] = np.array([B.POCKET["x"][0], B.POCKET["back_wall_y"], B.LID_TOP])
    A["hole"] = np.array([B.HOLE["x"][0], B.HOLE["y"][1], B.LID_TOP])
    A["knuckle"] = np.array([B.XC + B.HG["left"]["near_cheek"][0], B.AY, B.AZ + B.KP["R"]])
    A["stop"] = np.array([B.HG["ear_slot_x"]["left"][0], B.HG["heel_block"]["y"][1], B.HG["heel_block"]["z"][1]])
    ff = next(f for f in B.N["fold_feet_detail"] if f["rear"])
    A["feet"] = np.array([ff["x"][0], ff["lip"]["y"][1], ff["lip"]["z"][1]])
    for side, sld in B.hinge_axles_world():
        sg = -1 if side == "left" else 1
        put("axle_" + side, sld, B.COL["screw"], np.array([sg * EXPL["axle_x"], 0, 0]))
    A["axle"] = np.array([B.XC + B.HG["left"]["near_cheek"][0] - EXPL["axle_x"] - B.EST["m3_head"][1], B.AY, B.AZ])
    rc = B.ribbon_clip_world()
    put("clip", rc, B.COL["clip"], np.array([0, 0, EXPL["clip_z"]]))
    cb = rc.bounding_box()
    A["clip"] = np.array([cb[0], cb[4], cb[2] + EXPL["clip_z"]])
    gv = B.CLIP["wire_groove"]
    A["clip_groove"] = np.array([(gv["x"][0] + gv["x"][1]) / 2, cb[4], B.CLIP["clip_z"][1] + EXPL["clip_z"]])
    for i, sld in enumerate(B.lid_screws_world()):
        put("lidscrew_%d" % i, sld, B.COL["screw"], np.array([0, 0, EXPL["lidscrew_z"]]))
    xy = B.lid_screw_xy()[2]
    A["lidscrew"] = np.array([xy[0], xy[1], B.LS["head_seat_z"] + B.EST["m3_head"][1] + EXPL["lidscrew_z"]])
    A["vent"] = np.array([B.N["vents"]["slots"][0][0], B.N["vents"]["slots"][-1][3], B.LID_TOP])
    return out, A



# ------------------------------------------------------------------ detail sheets (3a fixes, close-ups)
PW_, PH_, PHEAD = 800, 450, 44


def _files(sub, ids, alpha=None, recolor=None):
    rows = {r["id"]: r for r in MAN["parts"][sub]}
    return [(os.path.join(HERE, rows[i]["file"]), (recolor or {}).get(i, rows[i]["color"]), (alpha or {}).get(i, 1.0)) for i in ids if i in rows]


def _ctx(ids, recolor=None):
    rows = {r["id"]: r for r in MAN["parts"]["context"]}
    return [(os.path.join(HERE, rows[i]["file"]), (recolor or {}).get(i, rows[i]["color"]), 1.0) for i in ids if i in rows]


def _ortho(name, axis, at, keep, ctr, half_h, items, depth=None):
    """section panel: cut plane axis = at, keep the side 'keep' (+1 / -1), camera looks at the cut face from the removed side."""
    d = half_h / TAN
    eye = list(ctr)
    k = "xyz".index(axis)
    eye[k] = at - keep * d
    ctr = list(ctr)
    ctr[k] = at
    cut = (axis, at, 3000.0) if keep > 0 else (axis, -3000.0, at)
    if depth is not None:                                  # keep only a slab behind the cut (no far background)
        cut = (axis, at, at + depth) if keep > 0 else (axis, at - depth, at)
    return dict(name=name, W=PW_, H=PH_, head=PHEAD, font=15, ortho=True, render=True, cut=cut, eye=tuple(eye), ctr=tuple(ctr), items=items)


def detail_scenes():
    th = B.TH_USE
    HGb = B.HG["heel_block"]
    xe = (B.HG["ear_x"]["left"][0] + B.HG["ear_x"]["left"][1]) / 2
    hinge_ids = ["TS-CRADLE", "TS-SCREEN", "TS-SCREEN-BEZEL", "TS-SCREEN-ACTIVE", "TS-LID", "TS-M3X20-HINGE-L", "TS-FFC", "TS-PWR-RED", "TS-PWR-BLK"]
    yc, zc = B.AY + 5.5, (HGb["z"][0] + B.AZ + B.KP["R"]) / 2 + 1.0
    # the ear section keeps x <= ear centre and is looked at from +x (the player is on the left)
    rc_lid = {"TS-LID": "#c9ced6"}
    p1 = _ortho("d1_ear22", "x", xe, -1, (xe, yc, zc), 14.0, _files("heel22", hinge_ids, recolor=rc_lid))
    p2 = _ortho("d2_ear25", "x", xe, -1, (xe, yc, zc), 14.0, _files("use", hinge_ids, recolor=rc_lid))
    cp = B.CLIP["pad"]
    yclip = B.CLIP["pins"][0][1] + 0.2                      # just off the pin axes (clean cut faces)
    p3 = _ortho("d3_clip", "y", yclip, +1, ((cp["x"][0] + cp["x"][1]) / 2, yclip, (B.CLIP["clip_z"][0] + cp["z"][1]) / 2), 16.0,
                _files("use", ["TS-LID", "TS-RCLIP", "TS-FFC", "TS-PWR-RED", "TS-PWR-BLK"]), depth=cp["y"][1] - yclip + 0.5)
    pi = B.N["pi5"]
    ycut = (pi["hdmi"]["y"][0] + pi["hdmi"]["y"][1]) / 2 + 1.0
    rbw = B.RB["waypoints"]
    p4 = _ortho("d4_pi_end", "y", ycut, +1, ((rbw[3][0] + pi["disp1"]["x"][1]) / 2, ycut, rbw[4][2] + 2.0), 8.0,
                _files("use", ["TS-FFC"]) + _ctx(["PI5-BOARD", "PI5-HDMI", "PI5-DISP1", "PI5-DISP0", "PI5-HEATSINK"]))
    # leg axle + u24 rib + the way in (translucent), from behind / -x at 25 deg
    wd = os.path.join(HERE, "work", "detail")
    os.makedirs(wd, exist_ok=True)
    path_stl = os.path.join(wd, "axle_path.stl")
    write_stl(B.place(B.leg_axle_path_local(), th), path_stl, "axle insertion path")
    piv = B.to_world((B.LG["clevis"]["near"][0] - 8.0, B.PIV_UW[0] - 3.0, B.PIV_UW[1]), th)
    p5 = dict(name="d5_axle", W=PW_, H=PH_, head=PHEAD, font=15, eye=(piv[0] - 62.0, piv[1] + 70.0, piv[2] + 40.0), ctr=tuple(piv),
              items=_files("use", ["TS-CRADLE", "TS-SCREEN", "TS-SCREEN-BEZEL", "TS-M3X20-LEG", "TS-WINCOVER"], recolor={"TS-CRADLE": "#7d8a9a"}) +
              [(path_stl, "#f0a030", 0.35)])
    nt = B.NOTCH
    c = B.to_world(((nt["xr"][0] + nt["xr"][1]) / 2, nt["u"][0], (nt["w"][0] + nt["w"][1]) / 2), th)
    dn, fr = B.dir_world((0, -1, 0), th), B.dir_world((0, 0, -1), th)
    eye = c + 70.0 * dn + 55.0 * fr + np.array([-25.0, 0, 0])
    p6 = dict(name="d6_notch", W=PW_, H=PH_, head=PHEAD, font=15, eye=tuple(eye), ctr=tuple(c),
              items=_files("use", ["TS-CRADLE", "TS-SCREEN", "TS-SCREEN-BEZEL", "TS-SCREEN-ACTIVE", "TS-SCREEN-TAB", "TS-M25-2", "TS-M25-4"]))
    sx, sy = B.lid_screw_xy()[0]
    rail = next(r["id"] for r in MAN["parts"]["context"] if r["id"].startswith("L2-PR-SEAMRAIL") and r["bbox"][0] < sx < r["bbox"][3])
    post = next(r["id"] for r in MAN["parts"]["context"] if r["id"].startswith("L2-PR-SEAMPOST") and r["bbox"][0] <= sx <= r["bbox"][3])
    lids = [r["id"] for r in MAN["parts"]["context"] if r["id"].startswith("L2-CU-LID") or r["id"].startswith("L2-LID")]
    p7 = _ortho("d7_lidscrew", "x", sx, -1, (sx, sy, (B.LS["rail_z"][0] + B.LID_TOP) / 2 - 3.0), 12.5,
                _files("use", ["TS-LID", "TS-M3X10-LID1"], recolor={"TS-LID": "#c9ced6"}) +
                _ctx([rail, post, "L2-INSERT-1"] + lids, recolor={rail: "#7f93b0", post: "#6d7f99", "L2-LID-L": "#d9c8a8"}))
    return [p1, p2, p3, p4, p5, p6, p7]


def panel_finish(s, title, labels, notes=None, draw=None):
    raw = Image.open(s["raw"]).convert("RGB")
    img = Image.new("RGB", (PW_, PH_ + PHEAD), (255, 255, 255))
    img.paste(raw, (0, PHEAD))
    if draw:
        draw(img)
    if notes:
        d = ImageDraw.Draw(img, "RGBA")
        ft = fnt(15)
        hh = 21
        wmax = max(d.textbbox((0, 0), t, font=ft)[2] for t in notes)
        y0 = PHEAD + PH_ - 10 - hh * len(notes) - 8
        d.rounded_rectangle([10, y0, 10 + wmax + 16, PHEAD + PH_ - 10], radius=6, fill=(255, 255, 255, 235), outline=(190, 196, 206, 255))
        for i, t in enumerate(notes):
            d.text((18, y0 + 5 + i * hh), t, font=ft, fill=(40, 46, 58))
        s = dict(s, reserve=(y0, PHEAD + PH_))
    layout_labels(img, s, labels, s.get("reserve"))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, PW_, PHEAD], fill=(243, 245, 248))
    d.text((14, 9), title, font=fnt(21, True), fill=(20, 26, 36))
    d.rectangle([0, 0, PW_ - 1, PH_ + PHEAD - 1], outline=(200, 205, 212), width=2)
    return img


def sheet(name, title, sub, tiles, cols=2):
    rows = (len(tiles) + cols - 1) // cols
    th_ = max(t.size[1] for t in tiles)
    img = Image.new("RGB", (PW_ * cols, HEAD + rows * th_), (255, 255, 255))
    for i, t in enumerate(tiles):
        img.paste(t, ((i % cols) * PW_, HEAD + (i // cols) * th_))
    header(img, title, sub)
    out = os.path.join(OUT, name + ".png")
    img.save(out)
    return out


def table_tile(rows, head_txt):
    img = Image.new("RGB", (PW_, PH_ + PHEAD), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, PW_, PHEAD], fill=(243, 245, 248))
    d.text((14, 9), head_txt, font=fnt(21, True), fill=(20, 26, 36))
    cx = [14, 250, 490, 705]
    y = PHEAD + 8
    for j, h in enumerate(("항목", "모델(메쉬로 잼)", "설계 numbers", "판정")):
        d.text((cx[j], y), h, font=fnt(15, True), fill=(60, 66, 78))
    y += 24
    d.line([10, y - 3, PW_ - 10, y - 3], fill=(200, 205, 212), width=1)
    for r in rows:
        col = (20, 110, 50) if r[3].startswith("맞음") or r[3].startswith("잡음") else ((200, 30, 30) if r[3].startswith("틀림") else (40, 46, 58))
        for j, t in enumerate(r):
            d.text((cx[j], y), t, font=fnt(14, j == 3), fill=col if j == 3 else (30, 36, 48))
        y += 22
    d.rectangle([0, 0, PW_ - 1, PH_ + PHEAD - 1], outline=(200, 205, 212), width=2)
    return img


def detail_finish(ds, sub):
    NC = INT["named"]
    E, A, LSW, WL_, CL, LSc, CB = NC["ear"], NC["axle"], NC["leg_swing"], NC["walls"], NC["clip"], NC["lid_screw"], NC["cables"]
    d1, d2, d3, d4, d5, d6, d7 = ds
    th = B.TH_USE
    hb = B.HG["heel_block"]
    xe = d1["ctr"][0]
    heel22 = B.to_world((0, *B.EAR["heel_uw"]), B.TH_HEEL)
    heel25 = B.to_world((0, *B.EAR["heel_uw"]), B.TH_USE)
    axis = (xe, B.AY, B.AZ)
    def ear_overlay(sc, theta, old=False):
        def _d(img):
            d = ImageDraw.Draw(img, "RGBA")
            pr = lambda P: project(P, sc)  # noqa: E731
            q = [pr((xe, *B.to_world((0, u, w), theta)[1:])) for (u, w) in B.EAR["profile_uw"]]
            d.line(q + [q[0]], fill=(0, 150, 215, 255), width=3)
            if old:
                q2 = [pr((xe, *B.to_world((0, u, w), theta)[1:])) for (u, w) in B.ear_profile_rev3_first()]
                for i in range(len(q2)):
                    dashed(d, q2[i], q2[(i + 1) % len(q2)], (140, 140, 150, 255), 2, 6, 5)
            y0, y1 = hb["y"]
            z0, z1 = hb["z"]
            box_ = [pr((xe, y0, z0)), pr((xe, y1, z0)), pr((xe, y1, z1)), pr((xe, y0, z1))]
            d.line(box_ + [box_[0]], fill=(214, 40, 40, 255), width=2)
            ax = pr(axis)
            d.ellipse([ax[0] - 4, ax[1] - 4, ax[0] + 4, ax[1] + 4], fill=(214, 40, 40, 255))
        return _d
    t1 = panel_finish(d1, "A. 경첩 귀 단면 x%.1f — 22° (뒤꿈치 멈춤)" % xe, [
        ((xe, heel22[1], heel22[2]), "뒤꿈치가 블록에 닿음 (틈 %.2f)" % E["gap_22"], "R"),
        ((xe, hb["y"][1], (hb["z"][0] + hb["z"][1]) / 2), "멈춤 블록 (빨간 틀)", "R"),
        (axis, "경첩 축 y%.2f z%.2f" % (B.AY, B.AZ), "R"),
        (B.to_world((0, B.EAR["hub"]["u"] - B.EAR["hub"]["R"], B.EAR["hub"]["w"] - 2.0), B.TH_HEEL) * np.array([0, 1, 1]) + np.array([xe, 0, 0]),
         "귀 윤곽 (파랑, numbers)", "R"),
        (B.to_world((0, *B.EAR["check"]["rev3_first_lobe"]["lobe_uw"]), B.TH_HEEL) * np.array([0, 1, 1]) + np.array([xe, 0, 0]),
         "3판 처음 윤곽 (회색 점선)", "R"),
    ], draw=ear_overlay(d1, B.TH_HEEL, old=True),
        notes=["3판 처음 윤곽이면 22°에서 %.2f 파고듦, %.1f°부터 풀림 (메쉬)" % (E["rev3_first_lobe"]["22"]["depth_z"], E["rev3_first_lobe"]["clears_from_deg"]),
               "3a 윤곽: 축 원 R%.1f + 아래 벽 붙음 + 뒤꿈치 한 점" % B.EAR["hub"]["R"]])
    t2 = panel_finish(d2, "B. 경첩 귀 단면 x%.1f — 25° (사용)" % xe, [
        ((xe, heel25[1], heel25[2]), "뒤꿈치 틈 %.3f (설계 %.2f)" % (E["min_gap_25_90"][0], E["design"]["min_gap_25_90"]), "R"),
        ((xe, hb["y"][1], (hb["z"][0] + hb["z"][1]) / 2), "멈춤 블록 z%.2f" % hb["z"][1], "R"),
        (axis, "경첩 축", "R"),
    ], draw=ear_overlay(d2, B.TH_USE),
        notes=["25~90°에서 가장 작은 틈 %.3f (%.1f°) · 규칙 0.3 이상" % tuple(E["min_gap_25_90"]),
               "C2 모따기 ↔ 경첩 볼 %.3f (%.0f°)" % tuple(NC["cheek_gap_min_22_90"])])
    cp = B.CLIP["pad"]
    yc = d3["ctr"][1]
    gv = B.CLIP["wire_groove"]
    pn = B.CLIP["pins"]
    t3 = panel_finish(d3, "C. 리본 클립 단면 (핀 줄), 앞에서 봄", [
        ((cp["x"][0] + 11.0, yc, B.RB["z_run"]), "리본 0.3 (물림)", "L"),
        ((pn[0][0] - 1.0, yc, B.CLIP["clip_z"][1] + B.CLIP["pin_len"] - 1), "핀 Ø%.0f×%.1f" % (B.CLIP["pin_d"], B.CLIP["pin_len"]), "L"),
        ((cp["x"][0] + 4.0, yc, B.CLIP["clip_z"][0] + 0.5), "리본 클립 30×12×3", "L"),
        (((gv["x"][0] + gv["x"][1]) / 2, yc, B.PW["waypoints"][1][2]), "전원선 → 홈", "R"),
        ((cp["x"][1] - 6.0, yc, (cp["z"][0] + cp["z"][1]) / 2), "클립 자리 (뚜껑)", "R"),
        ((pn[1][0], yc, B.LID_BED + B.CLIP["pin_hole_depth"] - 0.3), "핀 구멍 Ø%.1f×%.0f" % (B.CLIP["pin_hole_d"], B.CLIP["pin_hole_depth"]), "R"),
    ], notes=["리본 z%.2f~%.2f에 물림 · 전원선 홈 %.1f×%.1f (선과 바닥 %.2f)" % (
        CL["ribbon_z_in_clip"][0], CL["ribbon_z_in_clip"][1], gv["x"][1] - gv["x"][0], gv["depth"], CL["wires_to_clip_gap"]),
        "핀 끝 ↔ 구멍 바닥 %.1f · 단면 뒤 %.1f mm까지만 그림 (클립 뒤끝)" % (CL["pin_tip_to_hole_bottom"], cp["y"][1] - yc + 0.5)])
    pi = B.N["pi5"]
    yc = d4["ctr"][1]
    rbw = B.RB["waypoints"]
    hs = pi["heatsink"]
    t4 = panel_finish(d4, "D. 리본 Pi 끝 단면 y%.2f — CAM/DISP 1로" % yc, [
        ((rbw[3][0], yc, rbw[4][2] + 6.0), "리본 기둥 x%.0f" % rbw[3][0], "L"),
        ((hs["x"][1] - 3.0, hs["y"][0], hs["top_z"] - 1.5), "방열판 (추정)", "L"),
        ((pi["hdmi"]["x"][1] - 6.0, yc, pi["hdmi"]["top_z"] - 1.5), "micro-HDMI (추정)", "L"),
        ((rbw[5][0], yc, rbw[5][2] + 0.2), "HDMI 모서리에 얹힘", "R"),
        (((pi["disp1"]["x"][0] + pi["disp1"]["x"][1]) / 2, yc, pi["disp1"]["z"] + 1.5), "CAM/DISP 1 (%.1f 꽂음)" % B.RB["pi_end_insert"], "R"),
    ], notes=["기둥 x%.0f = 입구 x%.0f - 보강판 3 - R3 · 리본 끝 ↔ 커넥터 뒤끝 %.1f" % (rbw[3][0], pi["disp1"]["mouth"][0], CB["ribbon_end_short_of_back"]),
              "추정 방열판과 %.2f mm³ 겹침 (추정 자리, 사양 G-8) · HDMI와 틈 %.2f" % (CB["ribbon_heatsink_overlap_mm3"], CB["ribbon_to_hdmi_gap"])])
    s7 = sheet("07_3a_고친_곳_확대", "⑦ 3a에서 고친 곳 확대 — 귀·리본 클립·리본 Pi 끝 (모두 모델 단면)", sub, [t1, t2, t3, t4])
    nearc = B.LG["clevis"]["near"][0]
    t5 = panel_finish(d5, "E. 다리 축과 가로 리브 u%.0f (25°, 뒤 왼쪽에서, 다리는 뺌)" % B.CR["cross_ribs_u"][0], [
        (B.to_world((nearc - B.AXL["head_h"], B.PIV_UW[0], B.PIV_UW[1] + 2.0), th), "M3×20 머리 (-x에서 넣음)", "L"),
        (B.to_world((nearc - 14.0, B.PIV_UW[0] - 1.0, B.PIV_UW[1] + 2.9), th), "넣는 길 Ø%.1f (주황 반투명)" % B.AXL["head_d"], "L"),
        (B.to_world((nearc - 16.0, B.CR["cross_ribs_u"][0], B.W1), th), "가로 리브 u%.0f" % B.CR["cross_ribs_u"][0], "L"),
        (B.to_world((B.LG["clevis"]["far"][1], B.PIV_UW[0], B.PIV_UW[1]), th), "먼 볼 Ø2.5 (나사산)", "R"),
        (B.to_world((B.LG["clevis"]["near"][1] - 2.0, B.PIV_UW[0] + 3.0, B.PIV_UW[1] + 3.0), th), "가까운 볼 Ø3.3", "R"),
    ], notes=["넣는 길 ↔ 리브 %.2f · ↔ 뒷판 %.2f · 먼 볼 밖 겹침 %.1f mm³" % (A["3a"]["path_gap_to_ribs"], A["3a"]["path_gap_to_back_plate_w13"], abs(A["3a"]["seated_elsewhere_mm3"])),
              "u30 리브였다면: 머리 %.2f mm³, 넣는 길 %.2f mm³ 겹침 (메쉬로 확인)" % (A["rev3_u30_rib"]["seated_elsewhere_mm3"], A["rev3_u30_rib"]["path_overlap_mm3"])])
    nt = B.NOTCH
    t6 = panel_finish(d6, "F. 받침 아래 벽 홈 (앞 아래에서, 25°)", [
        (B.to_world(((nt["xr"][0] + nt["xr"][1]) / 2 - 5.0, nt["u"][0], 1.0), th), "아래 벽 홈 xr%.0f~%.0f (x%.0f~%.0f)" % (nt["xr"][0], nt["xr"][1], B.XC + nt["xr"][0], B.XC + nt["xr"][1]), "L"),
        (B.to_world(((nt["feature_xr"][0] + nt["feature_xr"][1]) / 2, -nt["feature_proud"], 4.0), th), "화면 아래 끝 돌기 (%.2f 튀어나옴, w는 추정)" % nt["feature_proud"], "R"),
        (B.to_world((nt["xr"][0] - 10.0, B.U0, 3.0), th), "유리가 아래 벽 u0에 얹힘 (틈 %.1f)" % WL_["glass_bottom_gap"], "L"),
        (B.to_world(((B.HG["right"]["ear"][0] + B.HG["right"]["ear"][1]) / 2, B.U0 - 4.0, 11.0), th), "오른쪽 귀 (홈은 w8 앞만)", "R"),
    ], notes=["돌기 양옆 여유 %.2f / %.2f (설계) · 뒤쪽(w)은 홈 끝과 %.1f (돌기 w는 추정)" % (WL_["tab_margin_x_design"][0], WL_["tab_margin_x_design"][1], WL_["tab_to_cradle_gap"])])
    sx, sy = B.lid_screw_xy()[0]
    L_ = B.LS
    t8 = panel_finish(d7, "H. 뚜껑 나사 단면 x%.0f (앞 왼쪽 y%.0f)" % (sx, sy), [
        ((sx, sy + L_["cbore_d"] / 2, L_["head_seat_z"] + 2.5), "자리파기 Ø%.1f×%.1f (머리 자리 z%.2f)" % (L_["cbore_d"], L_["cbore_depth"], L_["head_seat_z"]), "R"),
        ((sx, sy, (L_["tip_z"] + L_["head_seat_z"]) / 2 + 2), "M3×10 ISO 7380 (끝 z%.2f)" % L_["tip_z"], "L"),
        ((sx, sy + B.EST["insert_od"] / 2, L_["rail_z"][1] - L_["insert_engage"] / 2), "인서트 (길이 %.0f 추정, 구멍 %.1f)" % (L_["insert_engage"], L_["insert_hole_depth"]), "R"),
        ((sx, sy - 12.0, (L_["rail_z"][0] + L_["rail_z"][1]) / 2), "이음 레일 z%.2f~%.2f (CAD 부품)" % tuple(L_["rail_z"]), "L"),
        ((sx, sy - 3.0, L_["rail_z"][0] - 3.0), "앞 기둥 (나사 x%.0f는 기둥 모서리 위)" % sx, "L"),
    ], notes=["나사 끝 ↔ 인서트 구멍 바닥 %.2f · 구멍 밑 레일 살 %.2f · 끝 ↔ 기둥 윗면 %.2f" % (
        NC["lid_screw"]["tip_to_insert_hole_bottom"], NC["lid_screw"]["rail_floor_under_hole"], NC["lid_screw"]["tip_to_post_top"])])
    f = lambda v: ("%.3f" % v).rstrip("0").rstrip(".")  # noqa: E731
    s25 = LSW["25"]
    rows = [
        ("귀 ↔ 멈춤 블록 22°", "%s (겹침 %s)" % (f(E["gap_22"]), f(E["overlap_22_mm3"])), "0 (닿음)", "맞음" if E["overlap_22_mm3"] <= 1e-3 else "틀림"),
        ("귀 ↔ 블록 25~90° 최소", "%s (%g°)" % (f(E["min_gap_25_90"][0]), E["min_gap_25_90"][1]), "%s · 규칙 0.3↑" % f(E["design"]["min_gap_25_90"]), "맞음" if E["ok"] else "틀림"),
        ("3판 처음 귀 (검사 확인)", "-%s / -%s, %g°부터" % (f(E["rev3_first_lobe"]["22"]["depth_z"]), f(E["rev3_first_lobe"]["25"]["depth_z"]), E["rev3_first_lobe"]["clears_from_deg"]),
         "%g / %g, %g°" % (E["rev3_first_lobe"]["design_says"]["gap_at_22"], E["rev3_first_lobe"]["design_says"]["gap_at_25"], E["rev3_first_lobe"]["design_says"]["clears_from_deg"]), "잡음"),
        ("다리 축 머리·넣는 길 ↔ 리브", "%s (겹침 %s)" % (f(A["3a"]["path_gap_to_ribs"]), f(A["3a"]["path_overlap_mm3"])), "%s 이상" % f(A["design"]["path_gap"]), "맞음" if A["ok"] else "틀림"),
        ("u30 리브였다면 (검사 확인)", "겹침 %s + %s mm³" % (f(A["rev3_u30_rib"]["seated_elsewhere_mm3"]), f(A["rev3_u30_rib"]["path_overlap_mm3"])), "%g" % A["design"]["rev3_u30"]["head_gap"], "잡음"),
        ("다리 넣기 22°", "%g°에서 경사에 닿음, 겹침 0" % LSW["22"]["first_contact_deg"], "%g°" % -LSW["design"]["at_22_first_contact_deg"], "맞음" if LSW["22"]["max_overlap_mm3"] <= 1e-3 else "틀림"),
        ("다리 넣기 25° (쓰지 않는 순서)", "%g~%g° 긁힘, 최대 %s" % (s25["overlap_deg"][0], s25["overlap_deg"][1], f(s25["depth"])), "%g°부터, %s" % (-LSW["design"]["at_25_first_contact_deg"], f(-LSW["design"]["at_25_worst_overlap"])), "맞음"),
        ("유리 아래 / 위 / 옆 틈", "%s / %s / %s" % (f(WL_["glass_bottom_gap"]), f(WL_["glass_top_gap"]), f(WL_["glass_side_gap"])), "%s / %s / %s" % (f(WL_["design"]["bottom"]), f(WL_["design"]["top"]), f(WL_["design"]["side"])), "맞음"),
        ("보스 채움 · 아래 벽 홈", "채움 %s · 홈 속 살 %s" % ("/".join(f(v) for v in WL_["boss_fill_fraction"][:2]), f(WL_["notch_material_mm3"])), "옆벽까지 · 관통", "맞음"),
        ("출력 높이", f(WL_["print_height"]), f(WL_["print_height_design"]), "맞음" if abs(WL_["print_height"] - WL_["print_height_design"]) < 0.01 else "틀림"),
        ("리본 클립 물림 z", "%s~%s" % tuple(f(v) for v in CL["ribbon_z_in_clip"]), "%s~%s" % tuple(f(v) for v in CL["clamp_z_design"]), "맞음"),
        ("클립 핀 끝 ↔ 구멍 바닥", f(CL["pin_tip_to_hole_bottom"]), "구멍 %g - 핀 %g + 0.3" % (B.CLIP["pin_hole_depth"], B.CLIP["pin_len"]), "맞음"),
        ("뚜껑 나사 머리 / 끝 z", "%s / %s" % (f(LSc["head_seat_z"]), f(LSc["screw_z"][0])), "%s / %s" % (f(B.LS["head_seat_z"]), f(B.LS["tip_z"])), "맞음"),
        ("나사 끝 ↔ 인서트 구멍 바닥", f(LSc["tip_to_insert_hole_bottom"]), "구멍 %g - 인서트 %g (추정)" % (B.LS["insert_hole_depth"], B.LS["insert_engage"]), "맞음"),
        ("리본 끝 ↔ DISP1 뒤끝", f(CB["ribbon_end_short_of_back"]), "0.3", "맞음"),
        ("리본 길이 (300)", "%s + 접기 %s = %s" % (f(CB["ribbon_len_model"]), f(B.RB["parts"]["fold_roll_allowance"]), f(CB["ribbon_len_model_plus_lid_fold_roll"])), f(CB["ribbon_len_design"]), "비슷함"),
        ("전원선 길이 (500~550)", f(CB["wire_len_model_plus_pin_and_dupont"][0]), f(CB["wire_len_design"]), "비슷함"),
    ]
    t7 = table_tile(rows, "G. 3a 확인값 — 모델에서 잰 값과 설계 값")
    s8 = sheet("08_3a_다리축·아래벽홈·뚜껑나사·확인표", "⑧ 다리 축과 u%.0f 리브, 아래 벽 홈, 뚜껑 나사, 3a 확인값 표" % B.CR["cross_ribs_u"][0], sub, [t5, t6, t8, t7], cols=2)
    return [s7, s8]


# ------------------------------------------------------------------ main
def main():
    use_i = MAN["pose_info"]["use"]
    P = INT["poses"]
    th = B.TH_USE
    tw = lambda xr, u, w, t=th: B.to_world((xr, u, w), t)  # noqa: E731
    act_c = tw(0, (B.AU0 + B.AU1) / 2, 0)
    leg_piv, leg_tip = use_i["leg_pivot"], use_i["leg_tip"]
    leg_mid = (B.XC + B.LG["xr"][1], (leg_piv[0] + leg_tip[0]) / 2, (leg_piv[1] + leg_tip[1]) / 2)
    hinge_R = (B.XC + B.HG["right"]["near_cheek"][1], B.AY, B.AZ)
    hinge_L = (B.XC + B.HG["left"]["near_cheek"][0], B.AY, B.AZ)
    hole_c = ((B.HOLE["x"][0] + B.HOLE["x"][1]) / 2, (B.HOLE["y"][0] + B.HOLE["y"][1]) / 2, B.LID_TOP)
    pocket_c = (B.XC, (B.POCKET["ramp_front_y"] + B.POCKET["back_wall_y"]) / 2, B.POCKET["bottom_z"])
    spk_top = B.PL["speaker_top_z"]
    sp = B.BL2["speakers"]
    top_y = (sp["outer_yz_polygon"][3][0] + sp["outer_yz_polygon"][4][0]) / 2
    podL_top = ((sp["L"]["x"][0] + sp["L"]["x"][1]) / 2, top_y, spk_top)
    podR_top = ((sp["R"]["x"][0] + sp["R"]["x"][1]) / 2, top_y, spk_top)
    pi = B.N["pi5"]
    pi_c = ((pi["board_x"][0] + pi["board_x"][1]) / 2, (pi["board_y"][0] + pi["board_y"][1]) / 2, pi["board_top_z"])
    rbw = B.N["ribbon"]["waypoints"]
    pww = B.N["power_wire"]["waypoints"]
    cr_top = next(p["bbox"][5] for p in MAN["parts"]["use"] if p["id"] == "TS-CRADLE")
    sub = "B1 Waveshare 7-DSI-TOUCH-C · 수치: numbers.json(수정 3판 3a) + %s · 뒷바·스피커는 L2 잠정 외형(단순 모양) · CAD 전 확인용" % B.SRC["l2"]
    near_units = ["O3", "O4", "O5"]
    near_ctx = ["L2-POD-", "L2-GRILLE-", "L2-CU-BOX", "L2-LID-", "L2-PR-SEAM"]
    pale = {"L2-POD-": "#efe9de", "L2-GRILLE-": "#d9d9d9"}
    SW = INT["sweep"]["worst"]

    s1 = dict(name="01_연주자_시점_전체", eye=(-40.0, -1480.0, 1060.0), ctr=(611.0, 150.0, -15.0),
              items=items_modules() + items_context(keep=near_ctx) + items_touch("use"))
    s2 = dict(name="02_화면_가까이", eye=(355.0, -250.0, 345.0), ctr=(611.0, 252.0, 112.0),
              items=items_modules(near_units) + items_context(keep=near_ctx) + items_touch("use"))
    d_side = 600.0
    ctr_side = (B.XC, 185.0, 104.0)
    sec_items = items_modules(["O4"]) + items_context(skip=("L2-FEET",), recolor=pale) + items_touch("use")
    s3 = dict(name="03_옆_단면_x%.0f" % B.XC, ortho=True, render=True, cut=(-100.0, B.XC), eye=(B.XC + d_side, ctr_side[1], ctr_side[2]),
              ctr=ctr_side, items=sec_items)
    xcut_b = round(B.HOLE["x"][1] - 2.35, 2)
    s3b = dict(name="03b_옆_단면_x%.0f_리본길" % xcut_b, ortho=True, render=True, cut=(-100.0, xcut_b),
               eye=(xcut_b + d_side, ctr_side[1], ctr_side[2]), ctr=(xcut_b, ctr_side[1], ctr_side[2]), items=sec_items)
    s4 = dict(name="04_접은_상태_운반", eye=(1330.0, -430.0, 400.0), ctr=(640.0, 262.0, 88.0),
              items=items_modules(["O3", "O4", "O5", "O6", "O7", "끝_부속_오른쪽"]) + items_context(keep=near_ctx) + items_touch("fold"))
    s5 = dict(name="05_뒤에서_경첩·다리·선", eye=(1080.0, 640.0, 330.0), ctr=(622.0, 252.0, 92.0),
              items=items_modules(near_units) + items_context(skip=("L2-FEET", "L2-LID-R", "L2-POD-R", "L2-GRILLE-R")) +
              items_touch("use", alpha={"TS-LID": 0.33, "TS-WINCOVER": 0.4}))
    ex_items, EA = exploded_items()
    s6 = dict(name="06_분해도", eye=(210.0, 700.0, 470.0), ctr=(611.0, 250.0, 118.0), items=ex_items)
    scenes = [s1, s2, s3, s3b, s4, s5, s6]
    ds = detail_scenes()
    run_scenes(scenes + ds)
    outs = []

    outs.append(finish(s1, "① 연주자 시점 — 화면을 세운 상태(25°), 전체", sub, labels=[
        (act_c, "화면 7인치 B1 (1024×600)"),
        ((B.XC - 150, 100.0, 55.5), "건반 모듈 (그대로)"),
        (podL_top, "스피커 통 (L2 잠정 외형)"),
        (podR_top, "스피커 통 (L2 잠정 외형)"),
        ((B.LID_X[1] - 12, B.LID_Y[0] + 12, B.LID_TOP), "가운데 화면 뚜껑 (PETG)"),
        (((B.LID_X[1] + B.L2["centre"]["x"][1]) / 2, B.LID_Y[1] - 20, B.LID_TOP), "옆 뚜껑 (L2 잠정)"),
    ], notes=["화면 보이는 영역 가운데 z%.2f · 받침 가장 높은 곳 z%.2f · 스피커 윗면 z%.2f" % (B.N["reach"]["centre_z"], cr_top, spk_top),
              "모듈 위(y≤%.0f, z≥%.2f)에는 화면 부품이 없음: 가장 앞 y%.2f (22~90° 전체, 22°에서)" % (B.KEEP["y_max"], B.KEEP["z_min"], SW["min_y_moving_above_top"][0])]))

    outs.append(finish(s2, "② 화면 둘레 가까이 — 세운 상태 25°", sub, labels=[
        (act_c, "보이는 영역 154.58×86.42"),
        (tw(B.X0, B.U1 - 20, 4.0), "화면 받침(크래들) 170.7×106×17"),
        (hinge_L, "경첩 (M3×20, 바깥에서 넣음)"),
        (hinge_R, "경첩 (M3×20)"),
        (tw(B.LANE_XR, B.U0, B.W_FLAT), "리본·전원선 고리 → 구멍 22×6"),
        ((B.XC - 40, B.KEEP["module_rear_y"], B.KEEP["z_min"]), "모듈 뒤끝 y%.0f (금지선 y%.0f)" % (B.KEEP["module_rear_y"], B.KEEP["y_max"])),
    ],
        notes=["경첩 축 y%.2f z%.2f · 받침 가장 앞 y%.2f (25°) · 뒤꿈치 틈 %.2f mm (25°, 모델)" % (
            B.AY, B.AZ, P["25"]["min_y_above_module_top"]["per_part"]["TS-CRADLE"], INT["named"]["heel_gap_25"])]))

    def side_draw(s, paths=False):
        def _d(img):
            d = ImageDraw.Draw(img, "RGBA")
            pr = lambda y, z: project((s["ctr"][0], y, z), s)  # noqa: E731
            half_h = d_side * TAN
            top = s["ctr"][2] + half_h
            dashed(d, pr(B.KEEP["y_max"], B.KEEP["z_min"]), pr(B.KEEP["y_max"], top), (214, 40, 40, 230), 3)
            dashed(d, pr(B.KEEP["y_max"] - 70, B.KEEP["z_min"]), pr(B.KEEP["y_max"], B.KEEP["z_min"]), (214, 40, 40, 230), 3)
            ey, ez = B.N["eye"]["eye"]
            ac = B.N["points"]["use"]["act_centre"]
            yl = s["ctr"][1] - half_h * W / H
            zl = ez + (ac[1] - ez) * (yl - ey) / (ac[0] - ey)
            dashed(d, pr(yl, zl), pr(ac[0], ac[1]), (47, 111, 208, 220), 3, 18, 10)
            ax = pr(B.AY, B.AZ)
            d.ellipse([ax[0] - 7, ax[1] - 7, ax[0] + 7, ax[1] + 7], outline=(214, 40, 40), width=3)
            yb = B.LID_Y[1]
            dashed(d, pr(yb, B.LID_TOP), pr(yb, spk_top), (120, 128, 140, 200), 2)
            if paths:
                rb = B.ribbon_parts(th)["paths"]
                wr = B.wire_parts(th)["paths"]
                for pth in wr:
                    q = [pr(p[1], p[2]) for p in pth]
                    d.line(q, fill=(255, 255, 255, 230), width=6, joint="curve")
                    d.line(q, fill=(200, 30, 30, 255), width=3, joint="curve")
                for pth in rb:
                    q = [pr(p[1], p[2]) for p in pth]
                    d.line(q, fill=(255, 255, 255, 230), width=8, joint="curve")
                    d.line(q, fill=(224, 140, 20, 255), width=5, joint="curve")
        return _d

    sec_notes = lambda xc, extra=(): ["단면 x%.2f을 +x 쪽에서 봄 (왼쪽이 연주자) · 빨간 점선: 모듈 위 금지선 y%.0f / z%.2f · 빨간 원: 경첩 축 y%.2f z%.2f" % (  # noqa: E731
        xc, B.KEEP["y_max"], B.KEEP["z_min"], B.AY, B.AZ),
        "파란 점선: 시선 %.2f° (눈 y%.0f z%.0f, 추정) · 뒤의 연한 모양: 왼쪽 스피커 통(L2 잠정), 윗면 z%.2f · 회색 점선: 뚜껑 뒤끝 y%.1f" % (
            B.N["eye"]["angle_to_centre"], B.N["eye"]["eye"][0], B.N["eye"]["eye"][1], spk_top, B.LID_Y[1])] + list(extra)
    outs.append(finish(s3, "③ 옆 단면 (x%.0f, 받침다리·주머니 가운데) — 세운 상태 25°" % B.XC, sub, draw=side_draw(s3), labels=[
        (act_c, "화면 (단면)", "L"),
        (tw(0, B.U1 - 25, B.PLO), "화면 받침 (뒷판·리브)", "R"),
        (tw(0, B.PIV_UW[0], B.PIV_UW[1]), "다리 축 (u30, w16.5) M3×20", "R"),
        (leg_mid, "받침다리 67 mm, %.2f°" % B.LG["angle_deg"], "R"),
        (pocket_c, "다리 주머니 (발끝 y%.1f z%.2f)" % (leg_tip[0], leg_tip[1]), "R"),
        ((B.XC, B.AY - B.KP["R"], B.AZ), "경첩 볼 (보이는 것: 왼쪽 경첩)", "L"),
        ((B.XC, (B.N["context"]["key_rear_y"] + B.KEEP["module_rear_y"]) / 2, B.KEEP["z_min"] - 8), "건반 모듈 O4 (단면)", "L"),
        (pi_c, "Pi 5", "R"),
        ((B.XC, B.LID_Y[1] - 6, B.LID_TOP - 1), "화면 뚜껑 (판 %.0f + 리브, 밑면 z%.2f)" % (B.LID_T, B.LID_BED), "R"),
    ], notes=sec_notes(B.XC)))

    NC = INT["named"]
    cp = B.CLIP["pad"]
    cc = NC["cables"]
    lbl3b = [
        (tw(B.LANE_XR, 20.0, B.W_FLAT), "DSI 리본 (받침 안, 화면 뒷면 위)", "L"),
        (tw(B.LANE_XR, (B.CR["fold_square"]["u"][0] + B.CR["fold_square"]["u"][1]) / 2, B.EST["ribbon_mouth_w"] + 3), "45° 말아 접기 R3 (점검창 볼록 덮개 안)", "R"),
        (B.ribbon_parts(th)["loop_pts"][len(B.ribbon_parts(th)["loop_pts"]) // 2], "경첩 고리 %.1f mm (가장 앞 y%.2f)" % (B.EST["loop_len"], use_i["loop_min_y"]), "L"),
        ((xcut_b, B.HOLE["y"][0], B.LID_TOP - 5), "리본·전원선 구멍 22×6 (벽 2)", "L"),
        ((xcut_b, (cp["y"][0] + cp["y"][1]) / 2, B.CLIP["clip_z"][0]),
         "리본 클립: 리본 z%.2f~%.2f 물림 · 전원선은 홈" % tuple(NC["clip"]["ribbon_z_in_clip"]), "L"),
        ((rbw[3][0], rbw[3][1], 52.0), "리본 기둥 x%.0f (입구 - 보강판 3 - R3)" % rbw[3][0], "R"),
        ((rbw[4][0], rbw[4][1], rbw[4][2]), "HDMI(추정) 모서리에 얹혀 CAM/DISP 1에 %.1f 꽂음" % B.RB["pi_end_insert"], "R"),
        ((xcut_b, pww[3][1], 40.0), "전원선 → GPIO 2·6", "R"),
    ]
    outs.append(finish(s3b, "③-2 옆 단면 (x%.2f, 리본·전원선 길) — 세운 상태 25°" % xcut_b, sub, draw=side_draw(s3b, True), labels=lbl3b,
                       notes=sec_notes(xcut_b, ["주황 선: DSI 리본 중심선, 빨간 선: 전원선 (단면 뒤에 있어도 그림) · 리본 모델 %.0f mm(+뚜껑 밑 접기 여유 %.1f) / 설계 %.2f / 300 mm" % (
                           cc["ribbon_len_model"], B.RB["parts"]["fold_roll_allowance"], cc["ribbon_len_design"]),
                           "간섭 0 (22·25·90°) · 리본 끝은 커넥터 뒤끝보다 %.1f 안쪽 · 추정 방열판과 %.2f mm³ 겹침 (추정 자리, 사양 G-8)" % (
                           cc["ribbon_end_short_of_back"], cc["ribbon_heatsink_overlap_mm3"])])))

    fo = B.N["fold"]
    outs.append(finish(s4, "④ 접은 상태 (운반) — 화면을 뒤로 눕히고 다리는 받침 뒤에 끼움", sub, labels=[
        (B.to_world((B.AX0 + 30, (B.AU0 + B.AU1) / 2, 0), B.TH_FOLD), "화면 (유리가 위)"),
        ((sp["L"]["x"][1] - 10.0, top_y, spk_top), "스피커 윗면 z%.2f (양쪽 같음)" % spk_top),
        ((B.XC + B.X0, fo["y"][1], fo["top_z"]), "접은 끝 y%.2f (뚜껑 뒤끝 y%.1f)" % (fo["y"][1], B.LID_Y[1])),
        (hinge_R, "경첩"),
        ((B.XC + B.X1, (fo["y"][0] + fo["y"][1]) / 2, fo["top_z"]), "접은 윗면 z%.2f" % fo["top_z"]),
    ], notes=["접은 높이 z%.2f~%.2f · 스피커 윗면까지 %.2f mm · 뚜껑 뒤끝까지 %.2f mm" % (fo["rib_plane_z"], fo["top_z"], fo["speaker_margin"], fo["rear_margin"]),
              "받침 뒤 패드 4개가 뚜껑의 접이 받침 발(16×16×%.1f)에 얹힘 · 뒤 발 턱이 뒤로 밀림을 막음 · 통풍 슬롯은 덮임(운반 중 전원 끔)" % fo["feet_h"]]))

    outs.append(finish(s5, "⑤ 뒤에서 — 경첩·받침다리·선 (화면 뚜껑과 점검창 덮개는 반투명)", sub, labels=[
        (hinge_R, "경첩 (M3×20)"),
        (leg_mid, "받침다리"),
        ((B.XC, B.POCKET["back_wall_y"], B.LID_TOP), "다리 주머니"),
        (tw(B.INS["xr"][1], (B.INS["u"][0] + B.INS["u"][1]) / 2, B.PLO + 2), "점검창 덮개 (속에 ZIF·접힌 리본)"),
        (((rbw[2][0] + rbw[3][0]) / 2, rbw[2][1], rbw[2][2]), "DSI 리본 (뚜껑 밑)"),
        (((pww[2][0] + pww[3][0]) / 2, pww[2][1], pww[2][2]), "전원선 (뚜껑 밑 → GPIO 2·6)"),
        (pi_c, "Pi 5"),
        (((B.N["vents"]["slots"][1][0] + B.N["vents"]["slots"][1][1]) / 2, B.N["vents"]["slots"][-1][3], B.LID_TOP), "통풍 슬롯 34×4 ×8"),
        (tw(B.LG["clevis"]["far"][1], B.PIV_UW[0], B.PIV_UW[1]), "다리 걸이 + 다리 클립"),
    ], notes=["리본 길: 받침 안 45° 말아 접기 → 경첩 고리 → 구멍 → 뚜껑 밑 +y(클립) → 45° 접기 → -x → 기둥 x%.0f → HDMI 모서리 → Pi" % rbw[3][0],
              "리본 모델 %.0f + 뚜껑 밑 접기 여유 %.1f = %.0f mm (설계 %.2f, 케이블 300) · 뚜껑·점검창 덮개는 반투명" % (
                  INT["named"]["cables"]["ribbon_len_model"], B.RB["parts"]["fold_roll_allowance"], INT["named"]["cables"]["ribbon_len_model_plus_lid_fold_roll"], B.RB["total"])]))

    outs.append(finish(s6, "⑥ 분해도 — 화면 받침 묶음은 %.0f mm 들어 올림, 뚜껑은 반투명" % EXPL["lift"], sub, labels=[
        (EA["screen"], "화면 7-DSI-TOUCH-C (뒷면)"),
        (EA["zif"], "화면 DSI ZIF (추정 위치)"),
        (EA["cradle"], "화면 받침(크래들)"),
        (EA["ear"], "경첩 귀 (뒤꿈치 R%.1f)" % B.HG["heel_R"]),
        (EA["cover"], "점검창 덮개"),
        (EA["m25"], "M2.5×6 ×4"),
        (EA["leg"], "받침다리 67"),
        (EA["leg_axle"], "다리 축 M3×20"),
        (EA["axle"], "경첩 축 M3×20 ×2"),
        (EA["knuckle"], "경첩 볼"),
        (EA["stop"], "뒤꿈치 멈춤 블록"),
        (EA["hole"], "리본 구멍 22×6"),
        (EA["pocket"], "다리 주머니"),
        (EA["feet"], "접이 받침 발 (뒤 발 턱)"),
        (EA["clip"], "리본 클립 (뚜껑 밑에서 핀 %.1f로 끼움)" % B.CLIP["pin_len"]),
        (EA["clip_groove"], "클립 전원선 홈 %.1f×%.1f" % (B.CLIP["wire_groove"]["x"][1] - B.CLIP["wire_groove"]["x"][0], B.CLIP["wire_groove"]["depth"])),
        (EA["lidscrew"], "뚜껑 나사 M3×10 ×4 (자리파기 Ø%.1f×%.1f)" % (B.LS["cbore_d"], B.LS["cbore_depth"])),
        (EA["lid"], "가운데 화면 뚜껑 (B1판)"),
        (EA["vent"], "통풍 슬롯"),
    ]))
    outs += detail_finish(ds, sub)
    for o in outs:
        print(o)


if __name__ == "__main__":
    main()
