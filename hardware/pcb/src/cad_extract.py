"""Read the centre-unit electronics geometry out of the built CAD (hardware/mechanical/cad) for the board / wiring sheets.

usage:  python3 cad_extract.py            -> ../netlist/cad_centre.json
        (build.py calls refresh() first and falls back to the saved JSON when the CAD cannot be imported)

Nothing in the CAD tree is written: build_all.collect() builds the 1,467 Part objects in memory only (never build_all.main(),
which wipes stl/print). Every number the sheets BRD-03..06 print comes from here:
  * top-view outlines = Manifold.project() of each solid (world x, y; mm)
  * bounding boxes (x0, y0, z0, x1, y1, z1)
  * wire centre lines and lengths from electronics.py (pwr_paths, spk_lead_paths, pig_paths, cable_plan, LENGTHS, mismate)
  * fixing points (switch lugs, fuse-holder axis, amp / buck / PED / J702 holes) from electronics.py / body.py constants
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CAD_SRC = os.path.join(ROOT, "hardware", "mechanical", "cad", "src")
OUT = os.path.normpath(os.path.join(HERE, "..", "netlist", "cad_centre.json"))

# centre-unit region shown in BRD-04 (world mm): end walls x260..962, rear unit front y214 .. back face y342.5
REGION = (255.0, 967.0, 208.0, 346.0)
LID_Z = 61.35                     # lid underside (body.Z_LIDU): the top view is drawn with the lids and the screen off

ELEC = ["BAT-LFP", "C-XT60", "C-DC", "C-BAT-LEAD", "C-BAT-DC", "CU-E-FUSE", "CU-E-SWITCH", "CU-E-J501BOARD", "CU-E-J501",
        "CU-E-PEDBOARD", "CU-E-PEDZERO", "CU-E-J702BOARD", "CU-E-J702", "CU-E-BUCK", "CU-E-PI5", "CU-E-PI5-RJ45",
        "CU-E-PI5-USBA1", "CU-E-PI5-USBA2", "CU-E-PI5-DISP1", "CU-E-GENDER", "CU-E-DONGLE", "PB-E-HUB", "CU-E-AMP",
        "C-PWR-IN", "C-PWR-FUSE", "C-PWR-BUS", "C-PWR-5V", "C-XT60F-L", "C-XT60M-L", "C-XT60F-R", "C-XT60M-R",
        "C-SPK-L", "C-SPK-R", "C-SPKPIG-L", "C-SPKPIG-R", "C-USB-PED", "C-USB-UPSTREAM", "TS-C-DSI", "TS-C-PWR-RED",
        "TS-C-PWR-BLK"] + ["O%d-C-USB" % k for k in range(1, 8)]
CONTEXT_GROUPS = ("CU 칸 출력물", "가운데 유닛")


def _r(v, n=2):
    return round(float(v), n)


def _poly(solid, clip=None, eps=0.05):
    cs = solid.project()
    try:
        cs = cs.simplify(eps)
    except Exception:
        pass
    out = []
    for p in cs.to_polygons():
        pts = [(_r(x), _r(y)) for x, y in p]
        if len(pts) >= 3:
            out.append(pts)
    return out


def _bbox(solid):
    b = solid.bounding_box()
    return [_r(v) for v in b]


def _pl(pts):
    return [[_r(p[0]), _r(p[1]), _r(p[2])] for p in pts]


def refresh(verbose=True):
    """Import the CAD, collect the parts and write netlist/cad_centre.json. Returns the dict (or None on failure)."""
    t0 = time.time()
    sys.path.insert(0, CAD_SRC)
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))
    try:
        import build_all  # noqa: E402  (collect() only - never main())
        parts = build_all.collect()
        import electronics as E  # noqa: E402  (module state filled by collect(): LENGTHS, SW_LUGS)
        import body as B  # noqa: E402
    except Exception as ex:          # pragma: no cover - CAD tree missing or broken
        if verbose:
            print("cad_extract: CAD import failed:", ex)
        return None
    byid = {p.id: p for p in parts}
    res = {"meta": {"source": "hardware/mechanical/cad/src/build_all.collect() (in memory, %d parts)" % len(parts),
                    "built": time.strftime("%Y-%m-%d %H:%M"), "region": REGION, "lid_z": LID_Z},
           "parts": {}, "context": [], "paths": {}, "lengths": {}, "points": {}}
    for pid in ELEC:
        p = byid.get(pid)
        if p is None:
            continue
        res["parts"][pid] = {"name": p.name_ko, "kind": p.kind, "group": p.group, "bbox": _bbox(p.solid),
                             "poly": _poly(p.solid), "note": (p.note or "")[:400]}
    # printed / plywood context of the centre unit below the lids (drawn light)
    for p in parts:
        if p.group not in CONTEXT_GROUPS or p.kind not in ("print", "plywood"):
            continue
        b = p.solid.bounding_box()
        if b[2] >= LID_Z - 0.01 or b[3] < REGION[0] or b[0] > REGION[1] or b[4] < REGION[2] or b[1] > REGION[3]:
            continue
        res["context"].append({"id": p.id, "name": p.name_ko, "kind": p.kind, "bbox": _bbox(p.solid), "poly": _poly(p.solid, eps=0.1)})
    # centre lines
    P = E.pwr_paths()
    res["paths"]["PWR"] = {k: [_pl(q) for q in v] for k, v in P.items()}
    X = E.xt60_poses()
    res["paths"]["SPK"] = {k: _pl(v) for k, v in E.spk_lead_paths(X).items()}
    res["paths"]["PIG"] = {k: _pl(v) for k, v in E.pig_paths(X).items()}
    plan = E.cable_plan()
    res["paths"]["USB"] = {t: _pl(plan[t]) for t in ("O%d" % k for k in range(1, 8))}
    res["lengths"] = {k: _r(v, 1) for k, v in E.LENGTHS.items()}
    res["lengths"].update({"USB-" + t: _r(v, 1) for t, v in plan["_len"].items()})
    # standard cable length chosen per module / PED in the CAD (spec cable_duct.cables std_m: 1.0 / 0.5 / 0.3 m)
    res["points"]["usb_std_m"] = {t: float(c["std_m"]) for t, c in E.CABLE_SPEC.items()}
    res["points"]["usb_start_x"] = {t: _r(plan[t][0][0]) for t in ("O%d" % k for k in range(1, 8))}
    res["lengths"].update({"PWR-BUS-BUCK": _r(E.path_len(P["BUS"][0]), 1), "PWR-BUS-AMP": _r(E.path_len(P["BUS"][1]), 1),
                           "PWR-5V-PI": _r(E.path_len(P["5V"][0]), 1), "PWR-5V-HUB": _r(E.path_len(P["5V"][1]), 1)})
    mm = E.mismate()
    res["points"]["mismate"] = {"anchor": [_r(v) for v in mm["anchor"]], "cut": _r(mm["cut"], 1),
                                "need": {k: _r(v, 1) for k, v in mm["need"].items()}}
    res["points"]["sw_lugs"] = {k: _r(v) for k, v in E.SW_LUGS.items()}
    res["points"]["fuse_axis"] = [_r(v) for v in B.FH_AXIS]
    res["points"]["amp_holes"] = [[_r(a), _r(b)] for a, b in B.AMP_HOLES]
    bk = E.CC["CU-E-BUCK"]
    res["points"]["buck_holes"] = [[_r(bk[0] + 3.2), _r(bk[2] + 3.2)], [_r(bk[1] - 3.2), _r(bk[2] + 3.2)],
                                   [_r(bk[0] + 3.2), _r(bk[3] - 3.2)], [_r(bk[1] - 3.2), _r(bk[3] - 3.2)]]
    pb = E.CC["CU-E-PEDBOARD"]
    res["points"]["ped_board"] = {"box": [_r(v) for v in pb],
                                  "screws": [[_r(pb[0] + 4), _r(pb[2] + 4)], [_r(pb[1] - 4), _r(pb[3] - 4)]],
                                  "pins": [[_r(pb[1] - 4), _r(pb[2] + 4)], [_r(pb[0] + 4), _r(pb[3] - 4)]]}
    res["points"]["ped_zero"] = [_r(v) for v in E.CC["CU-E-PEDZERO"]]
    jb = E.CC["CU-E-J702BOARD"]
    res["points"]["j702_board"] = {"box": [_r(v) for v in jb], "holes": [[_r(jb[0] + 3.0), _r(jb[2] + 3.0)], [_r(jb[1] - 3.0), _r(jb[3] - 3.0)]]}
    res["points"]["j702"] = [_r(v) for v in E.CC["CU-E-J702"]]
    res["points"]["j501_board"] = [_r(v) for v in E.CC["CU-E-J501BOARD"]]
    res["points"]["j501"] = [_r(v) for v in E.CC["CU-E-J501"]]
    res["points"]["hub"] = {"bbox": [_r(v) for v in (E.HUB_X0, E.HUB_X1, E.HUB_Y, E.HUB_BACK, E.HUB_Z0, E.HUB_Z1)],
                            "ports_x": [_r(v) for v in E.HUB_PORT_X], "port_z": _r(E.HUB_Z), "port_map": E.HUB_PORT,
                            "dc": [_r(v) for v in E.HUB_DC], "dc_yz": [_r(v) for v in E.HUB_DC_YZ],
                            "dc_straight_max": _r(getattr(E, "HUB_DC_STRAIGHT_MAX", float("nan")), 1)}
    res["points"]["xt60_pose"] = {s: {"fem": [_r(v) for v in X[s]["fem"]], "mal": [_r(v) for v in X[s]["mal"]],
                                      "yc": _r(X[s]["yc"]), "zc": _r(X[s]["zc"])} for s in "LR"}
    res["points"]["c24_head"] = [_r(v) for v in E.C24_HEAD]
    res["points"]["pig"] = {"lead_mm": _r(B.PIG_LEAD_MM, 1)}
    res["points"]["splice"] = [_r(v) for v in E.SPLICE]
    res["points"]["fh_bend"] = _r(E.FH_BEND)
    res["points"]["awg12_d"] = _r(E.AWG12_D)
    fu = byid.get("CU-E-FUSE")
    if fu is not None:
        # where the CAD harness centre line starts off each holder end (12 AWG radius + touch): the cut stubs are measured from the holder end
        fb = fu.solid.bounding_box()
        res["points"]["fh_ends"] = {"x0": _r(fb[0]), "x1": _r(fb[3]),
                                    "e12_in": _r(fb[0] - P["IN"][0][0][0]), "e12_out": _r(P["FUSE"][0][0][0] - fb[3])}
        res["lengths"]["PWR-IN-SPLICE"] = _r(E.path_len(P["IN"][1]), 1)
        res["lengths"]["PWR-FUSE-SPLICE"] = _r(E.path_len(P["FUSE"][1]), 1)
    # headphone cables W701 / W702 are not modelled as solids (the plug zones are kept free): right-angle route (upper bound of any bent
    # route) through the modelled features - J701 legs (EL-E-J701 body bottom - jack_dims.pins_below_base) -> down the open insert slot ->
    # the left-cheek groove (keyaction_parts.py cheek cut box x-12.6..-4.1, y14.19..212.5, z2.5..7.5) -> out of the cheek rear face down onto
    # the duct floor (desk; AUX cable D3.5 -> centre z1.75) -> to the plug-zone front face y222 -> along x -> straight up into the plug rear
    # (Z-DONGLE-PLUG at the dongle socket axis x650 z21.75 / Z-J702-PLUG at the J702 jack axis z = board top + axis_above_base).
    try:
        jb = byid["EL-E-J701"].solid.bounding_box()
        with open(os.path.join(CAD_SRC, "..", "spec", "keyaction_features_frame.json"), encoding="utf-8") as f:
            jd = json.load(f)["cheeks"]["headphone_jack"]["jack_dims"]
        groove = (-12.6, -4.1, 14.19, 212.5, 2.5, 7.5)
        cx = (jb[0] + jb[3]) / 2.0
        ym = (jb[1] + jd["nose_L"] + jb[4]) / 2.0
        zl = jb[2] - jd["pins_below_base"]
        gz = (groove[4] + groove[5]) / 2.0
        zf = 3.5 / 2.0
        dzp, jzp, j7 = E.CC["Z-DONGLE-PLUG"], E.CC["Z-J702-PLUG"], E.CC["CU-E-J702"]
        sx, sz = E.DONGLE_SOCK[0], E.DONGLE_SOCK[1]
        j7x, j7z = (j7[0] + j7[1]) / 2.0, j7[4] + jd["axis_above_base"]
        head = [(cx, ym, zl), (cx, ym, gz), (cx, groove[3], gz), (cx, groove[3], zf)]
        hp = {"W701": head + [(cx, dzp[2], zf), (sx, dzp[2], zf), (sx, dzp[2], sz)],
              "W702": head + [(cx, jzp[2], zf), (j7x, jzp[2], zf), (j7x, jzp[2], j7z)]}
        res["paths"]["HP"] = {k: _pl(v) for k, v in hp.items()}
        for k, v in hp.items():
            res["lengths"]["HP-" + k] = _r(sum(math.dist(a, b) for a, b in zip(v, v[1:])), 1)
        res["points"]["hp_route"] = {"j701_legs": [_r(cx), _r(ym), _r(zl)], "groove": list(groove), "floor_z": zf, "run_y": _r(dzp[2]),
                                     "dongle_plug": [_r(sx), _r(dzp[2]), _r(sz)], "j702_plug": [_r(j7x), _r(jzp[2]), _r(j7z)]}
    except Exception as ex:          # pragma: no cover
        if verbose:
            print("cad_extract: headphone route skipped:", ex)
    res["meta"]["seconds"] = _r(time.time() - t0, 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    if verbose:
        print("cad_extract: %d parts, %d context, %.1f s -> %s" % (len(res["parts"]), len(res["context"]), time.time() - t0, OUT))
    return res


def load(refresh_first=True):
    if refresh_first:
        r = refresh(verbose=True)
        if r:
            return r
    with open(OUT, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    refresh()
