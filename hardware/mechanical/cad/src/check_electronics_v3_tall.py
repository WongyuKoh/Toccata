"""Self-check for electronics.py.

  python3 check_electronics.py

(1) lists every electronics Part (kind / group / bodies / bbox),
(2) pairwise overlaps (a ^ b volume > 0.01 mm3): electronics x electronics, electronics x key action,
    electronics x body (only when body.py exists) - each overlap is either matched to an EXPECTED reason or reported,
(3) bbox checks against the spec numbers (overall 1254 x 410, speaker boxes z22..232, centre unit 894 x 195 x 100,
    CU-bay component boxes of body_centre_unit.json, I/O-plate hole centres, XT30 holder pockets, J701 pocket,
    speaker flange / basket / magnet y, pedal off the desk).
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SPEC = os.path.normpath(os.path.join(HERE, "..", "spec"))

T0 = time.time()
TOL = 0.01          # mm3 overlap threshold
EPS = 0.02          # mm bbox tolerance

# (regex a, regex b, reason) - a/b match either order
EXPECTED = [
    # electronics x electronics
    (r"-C-USB$|^C-USB-PED$", r"-E-ZERO$|^CU-E-PEDZERO$", "USB-C 플러그 금속 쉘이 Zero 리셉터클 안으로 들어감 (의도)"),
    (r"^CU-E-GENDER$", r"^CU-E-PI5-USBA1$", "젠더 USB-A 플러그가 Pi USB-A 포트 안으로 들어감 (의도)"),
    (r"^C-USB-UPSTREAM$", r"^CU-E-PI5-USBA2$", "업스트림 USB-A 플러그가 Pi 포트 안으로 들어감 (의도)"),
    (r"^CU-E-DONGLE$", r"^CU-E-GENDER$", "동글 USB-C 플러그가 젠더 C 소켓 안으로 들어감 (의도)"),
    (r"^C-XT30M-", r"^C-XT30F-", "XT30 수·암 짝맞춤 (의도)"),
    # electronics x key action
    (r"-E-MB$", r"-B-controlboardscrew", "M3×6 나사 몸통이 기판 구멍 Ø3.2를 지남 (다각형 근사)"),
    (r"-E-MB$", r"-FRAME$", "프레임 위치 핀 Ø2.8 ↔ 기판 구멍 Ø3.0 (의도, 다각형 근사)"),
]

# known spec-level conflicts between two agents' specs (reported, not fixed here)
SPEC_CONFLICTS = [
    (r"^O1-C-USB$", r"XT30|xt30", "body_speakers XT30 받침 L(x128~164 y218~238 z8~22)이 O1 USB-C 플러그 봉투"
     "(x124.75~137.25 y196.8~221.8 z10.7~18.3)와 R25 굽힘을 막음 - 받침 위치를 옮겨야 함 (body_speakers vs electronics_modules)"),
]


def load(name):
    with open(os.path.join(SPEC, name)) as fh:
        return json.load(fh)


def bb(p):
    if not hasattr(p, "_bb"):
        p._bb = p.solid.bounding_box()
    return p._bb


def boxes_touch(a, b):
    return not any(a[i] > b[i + 3] + 1e-6 or b[i] > a[i + 3] + 1e-6 for i in range(3))


def overlap(a, b):
    if not boxes_touch(bb(a), bb(b)):
        return 0.0
    return (a.solid ^ b.solid).volume()


def reason(a, b, table):
    ka, kb = a.id + " " + a.name_ko, b.id + " " + b.name_ko
    for ra, rb, why in table:
        # rb may be anchored on the id ("...$") or search the id + Korean name
        if (re.search(ra, a.id) and (re.search(rb, b.id) or re.search(rb, kb))) or \
           (re.search(ra, b.id) and (re.search(rb, a.id) or re.search(rb, ka))):
            return why
    return None


# ------------------------------------------------------------------ body proxy (only while body.py does not exist)

class Proxy:
    def __init__(self, id, name_ko, solid):
        self.id, self.name_ko, self.solid, self.note, self.kind = id, name_ko, solid, "", "proxy"


def body_proxy():
    """body parts rebuilt from the spec boxes of body_centre_unit.json / body_speakers.json (solid envelopes with the
    openings that matter for the electronics: tray inlet, I/O-plate holes + pocket, baffle cut-out, holder pockets,
    grille-ring opening, fuse cradle U). Ribs / hollows whose positions the specs do not give are left out."""
    from cadlib import box, cone_z, cyl_x, cyl_y, cyl_z, diff, union
    C = load("body_centre_unit.json")
    S = load("body_speakers.json")
    out = []

    def bx(b):
        return box(b["x"][0], b["x"][1], b["y"][0], b["y"][1], b["z"][0], b["z"][1])

    for pnl in C["panels"]:
        out.append(Proxy("PX-" + pnl["id"], pnl["name_ko"], bx(pnl["box"])))
    pr = {q["id"]: q for q in C["printed"]}
    t = pr["PR-CU-TRAY"]
    f = {q["name"]: q for q in t["features"]}
    tray = diff(bx(t["box"]), [bx(f["cable_inlet"]["box"])])
    adds = []
    for nm in ("pi5_bosses", "amp_bosses", "buck_bosses", "amp_input_jack_board_bosses"):
        q = f[nm]
        for (x, y) in q["at"]:
            adds.append(cyl_z(x, y, q["z"][0], q["z"][1], q.get("od", 7.0)))
    q = f["ped_board_standoffs"]
    for (x, y) in q["screw_at"] + q["pin_at"]:
        adds.append(cyl_z(x, y, 33.5, 38.5, 6.0))
    for (x, y) in q["pin_at"]:
        adds.append(cyl_z(x, y, 38.5, 41.0, 2.8))
    q = f["foot_screw_bosses"]
    for (x, y) in q["at"]:
        adds.append(cyl_z(x, y, q["z"][0], q["z"][1], q["d"]))
    for tab in f["divider_screw_tabs"]["tabs"]:
        adds.append(bx(tab["box"]))
    cr = f["fuse_holder_cradle"]["box"]
    yc = (cr["y"][0] + cr["y"][1]) / 2.0
    zc = 40.5
    adds.append(diff(bx(cr), [cyl_x(yc, zc, cr["x"][0] - 1, cr["x"][1] + 1, f["fuse_holder_cradle"]["inner_d"]),
                              box(cr["x"][0] - 1, cr["x"][1] + 1, yc - 5.25, yc + 5.25, zc, cr["z"][1] + 1)]))
    out.append(Proxy("PX-PR-CU-TRAY", t["name_ko"], union([tray] + adds)))
    lid = pr["PR-CU-LID"]
    out.append(Proxy("PX-PR-CU-LID", lid["name_ko"], bx(lid["box"])))
    io = pr["PR-IO-PLATE"]
    g = {q["name"]: q for q in io["features"]}
    b = io["box"]
    skin = box(b["x"][0], b["x"][1], 408.0, 410.0, b["z"][0], b["z"][1])
    frame = diff(bx(b), [box(b["x"][0] + 4, b["x"][1] - 4, b["y"][0] - 1, 408.0, b["z"][0] + 4, b["z"][1] - 4)])
    cuts = [cyl_y(560, 92, 397, 411, 6.5), box(610 - 6.6, 610 + 6.6, 397, 411, 92 - 9.6, 92 + 9.6),
            box(660 - 6.75, 660 + 6.75, 397, 411, 92 - 4.0, 92 + 4.0), box(700 - 9, 700 + 9, 397, 411, 92 - 5.5, 92 + 5.5)]
    blk = g["usb_c_input"]["pocket"]
    parts = [skin, frame, bx(g["pedal_jack_hole"]["mount"]["box"]), diff(bx(blk["block"]), [bx(blk["cavity"])])]
    parts += [bx(tab["box"]) for tab in g["divider_screw_tabs"]["tabs"]]
    out.append(Proxy("PX-PR-IO-PLATE", io["name_ko"], diff(union(parts), cuts)))
    for inst in pr["PR-LID-SUP"]["instances"]:
        out.append(Proxy("PX-LIDSUP-" + inst["tag"], pr["PR-LID-SUP"]["name_ko"], bx(inst["box"])))
    h = pr["PR-PB-HOLDER"]["geometry"]
    hp = [bx(h["base"]["box"]), bx(h["left_stop_wall"]), bx(h["front_stop_wall"]), bx(h["strap"]["right_hook"]["box"])]
    hp += [cyl_z(x, y, 33.5, 36.5, 10) for (x, y) in h["screw_pads"]["at"]]
    out.append(Proxy("PX-PR-PB-HOLDER", pr["PR-PB-HOLDER"]["name_ko"], union(hp)))
    for k in ("PR-KS-INSERT", "PR-SMALL-BOX"):
        out.append(Proxy("PX-" + k, pr[k]["name_ko"], bx(pr[k]["box"])))
    for pos in S["feet"]["positions"]:
        out.append(Proxy("PX-FOOT-%d-%d" % (pos["x"], pos["y"]), "고무발 + 받침 4 mm",
                         union([cone_z(pos["x"], pos["y"], 0, 18, 28, 20), cyl_z(pos["x"], pos["y"], 18, 22, 20)])))
    for pnl in S["panels"]:
        sol = box(pnl["x"][0], pnl["x"][1], pnl["y"][0], pnl["y"][1], pnl["z"][0], pnl["z"][1])
        if pnl["id"].endswith("baffle"):
            cx = 74.0 if pnl["id"].startswith("spkL") else 1148.0
            wx = 6.0 if pnl["id"].startswith("spkL") else 1216.0
            sol = diff(sol, [cyl_y(cx, 142, 214, 227.5, 94.0), cyl_y(wx, 38, 214, 227.5, 6.0)])
        out.append(Proxy("PX-" + pnl["id"], pnl["name_ko"], sol))
    q = {p["id"]: p for p in S["printed"]}
    for side, cx in (("L", 74.0), ("R", 1148.0)):
        w = q["spk_grille"]["world"][side]
        ring = diff(box(w["x"][0], w["x"][1], w["ring_y"][0], w["ring_y"][1], w["z"][0], w["z"][1]),
                    [box(cx - 53, cx + 53, 204, 216, 142 - 53, 142 + 53)])
        face = box(w["x"][0], w["x"][1], w["face_y"][0], w["face_y"][1], w["z"][0], w["z"][1])
        out.append(Proxy("PX-GRILLE-" + side, q["spk_grille"]["name_ko"], union([ring, face])))
        gw = q["spk_gasket"]["world"][side]
        out.append(Proxy("PX-GASKET-" + side, q["spk_gasket"]["name_ko"], diff(bx(gw), [cyl_y(cx, 142, 211, 216, 94.0)])))
        hd = q["xt30_holder_" + side]
        out.append(Proxy("PX-xt30_holder_" + side, hd["name_ko"], diff(bx(hd["world"]), [bx(hd["pocket"]["world"])])))
        bw = q["spk_bracket"]["world"][side]
        out.append(Proxy("PX-BRACKET-" + side, q["spk_bracket"]["name_ko"], bx(bw)))
    for k in ("dovetail_L_speaker", "dovetail_L_centre", "dovetail_R_speaker", "dovetail_R_centre"):
        w = q[k]["world"]
        sols = [bx(w["bar"]), bx(w["latch_seat"])] + [bx(e) for e in w.get("ears", [])]
        if "male" in w:
            sols += [box(w["male"]["x"][0], w["male"]["x"][1], a, bb_, w["male"]["z"][0], w["male"]["z"][1]) for a, bb_ in w["male"]["y_ranges"]]
        out.append(Proxy("PX-" + k, q[k].get("name_ko", k), union(sols)))
    return out


def fmt(b):
    return "x%.2f..%.2f y%.2f..%.2f z%.2f..%.2f" % (b[0], b[3], b[1], b[4], b[2], b[5])


def inside(b, box, tol=EPS):
    return (b[0] >= box["x"][0] - tol and b[3] <= box["x"][1] + tol and b[1] >= box["y"][0] - tol and b[4] <= box["y"][1] + tol
            and b[2] >= box["z"][0] - tol and b[5] <= box["z"][1] + tol)


def main():
    import electronics
    import keyaction_parts
    E = electronics.build()
    K = keyaction_parts.build_all()
    B = []
    body_path = os.path.join(HERE, "body.py")
    if os.path.exists(body_path):
        import body
        B = body.build()
    X = [] if B else body_proxy()
    t_build = time.time() - T0
    ok = True

    # ------------------------------------------------------------------ (1) list
    print("=" * 100)
    print("(1) electronics parts: %d   (key action %d, body %s)   build %.1f s" % (len(E), len(K), len(B) if B else "없음 - body.py 아직 없음", t_build))
    ids = [p.id for p in E]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        ok = False
        print("  ! duplicate ids:", dup)
    kids = {p.id for p in K} | {p.id for p in B}
    clash = sorted(set(ids) & kids)
    if clash:
        ok = False
        print("  ! ids also used by other generators:", clash)
    for p in E:
        n = len(p.solid.decompose())
        flag = "" if n == 1 else "  ! %d bodies" % n
        if n != 1:
            ok = False
        if p.kind not in ("electronics", "bought", "consumable"):
            ok = False
            flag += "  ! kind"
        print("  %-16s %-11s %-18s %s  vol %9.1f%s%s" % (p.id, p.kind, p.group, fmt(bb(p)), p.solid.volume(),
                                                        "  [" + p.note + "]" if p.note == "offdesk" else "", flag))
    groups = {}
    for p in E:
        groups.setdefault(p.group, 0)
        groups[p.group] += 1
    print("  groups:", ", ".join("%s %d" % kv for kv in groups.items()))
    no_est = [p.id for p in E if p.note and p.note != "offdesk" and not p.note.startswith("추정:") and "추정" in p.note]
    if no_est:
        print("  ! notes with 추정 not at the start:", no_est)

    # ------------------------------------------------------------------ (2) overlaps
    print("=" * 100)
    print("(2) overlaps > %.2f mm3" % TOL)
    onsite = [p for p in E if p.note != "offdesk"]
    sets = [("전자 x 전자", [(a, b) for i, a in enumerate(onsite) for b in onsite[i + 1:]])]
    sets.append(("전자 x 건반 동작부", [(a, b) for a in onsite for b in K]))
    if B:
        sets.append(("전자 x 몸체", [(a, b) for a in onsite for b in B]))
    else:
        sets.append(("전자 x 몸체 대용(spec 상자로 만든 %d개 - body.py 없음)" % len(X), [(a, b) for a in onsite for b in X]))
    for title, pairs in sets:
        exp, conf, bad = [], [], []
        for a, b in pairs:
            v = overlap(a, b)
            if v <= TOL:
                continue
            w = reason(a, b, EXPECTED)
            c = reason(a, b, SPEC_CONFLICTS)
            (exp if w else conf if c else bad).append((v, a, b, w or c))
        print("  -- %s: expected %d, spec conflicts %d, UNEXPECTED %d" % (title, len(exp), len(conf), len(bad)))
        for v, a, b, w in sorted(exp, key=lambda r: -r[0]):
            print("     ok   %9.3f  %-16s ^ %-26s %s" % (v, a.id, b.id, w))
        for v, a, b, w in sorted(conf, key=lambda r: -r[0]):
            print("     SPEC %9.3f  %-16s ^ %-26s %s" % (v, a.id, b.id, w))
        for v, a, b, w in sorted(bad, key=lambda r: -r[0]):
            ok = False
            ib = (a.solid ^ b.solid).bounding_box()
            print("     !!   %9.3f  %-16s ^ %-26s (%s) at %s" % (v, a.id, b.id, b.name_ko[:40], fmt(ib)))

    # ------------------------------------------------------------------ (3) bbox checks
    print("=" * 100)
    print("(3) bbox checks")
    P = {p.id: p for p in E}
    C = load("body_centre_unit.json")
    R = load("electronics_rearbar.json")
    S = load("body_speakers.json")
    F = load("keyaction_features_frame.json")
    tray = next(q for q in C["printed"] if q["id"] == "PR-CU-TRAY")
    comp = {c["name_ko"]: c["box"] for c in tray["components"]}
    io = next(q for q in C["printed"] if q["id"] == "PR-IO-PLATE")
    iof = {f["name"]: f for f in io["features"]}
    res = []

    def chk(label, cond, detail=""):
        nonlocal ok
        res.append((cond, label, detail))
        if not cond:
            ok = False

    def union_bb(ps):
        bs = [bb(p) for p in ps]
        return [min(b[i] for b in bs) for i in range(3)] + [max(b[i] for b in bs) for i in range(3, 6)]

    # overall
    allp = [p for p in K + E + B if p.note != "offdesk"]
    ob = union_bb(allp)
    print("  overall (key action + electronics%s, off-desk pedal excluded): %s = %.2f x %.2f x %.2f"
          % (" + body" if B else "", fmt(ob), ob[3] - ob[0], ob[4] - ob[1], ob[5] - ob[2]))
    eb = union_bb(onsite)
    chk("electronics inside x-16..1238", eb[0] >= -16 - EPS and eb[3] <= 1238 + EPS, fmt(eb))
    chk("electronics y >= 0 (front lip)", eb[1] >= -EPS, fmt(eb))
    chk("electronics z >= 0 (desk)", eb[2] >= -EPS, fmt(eb))
    over_back = [p.id + " y..%.2f" % bb(p)[4] for p in onsite if bb(p)[4] > 410 + EPS]
    res.append((True, "info: parts behind the back face y410 (1254 x 410 overall)", ", ".join(over_back) or "none"))
    if B:
        bbx = union_bb([p for p in B if p.note != "offdesk"])
        chk("body overall 1254 x 410 (x-16..1238, y..410)", abs(bbx[0] + 16) < 0.5 and abs(bbx[3] - 1238) < 0.5 and bbx[4] <= 410 + EPS, fmt(bbx))

    # speakers
    for sid, cx in (("SPK-L", 74.0), ("SPK-R", 1148.0)):
        b = bb(P[sid])
        chk("%s centre x%.0f z142" % (sid, cx), abs((b[0] + b[3]) / 2 - cx) < 0.05 and abs((b[2] + b[5]) / 2 - 142) < 0.05, fmt(b))
        chk("%s flange front y208, magnet back y269" % sid, abs(b[1] - 208) < EPS and abs(b[4] - 269) < EPS, fmt(b))
        chk("%s inside speaker box z22..232" % sid, b[2] >= 22 and b[5] <= 232, fmt(b))
        bs = S["box_summary"]["L" if sid.endswith("L") else "R"]
        chk("%s inside speaker box x%s" % (sid, bs["x"]), b[0] >= bs["x"][0] and b[3] <= bs["x"][1], fmt(b))
        # slice checks: basket to y252 (Ø94), magnet y252..269 (Ø85)
        sl = P[sid].solid.trim_by_plane((0, 1, 0), 250.0).trim_by_plane((0, -1, 0), -251.0).bounding_box()
        chk("%s basket Ø94 at y250..251" % sid, abs((sl[3] - sl[0]) - 94) < 0.2, "%.2f" % (sl[3] - sl[0]))
        sl = P[sid].solid.trim_by_plane((0, 1, 0), 260.0).trim_by_plane((0, -1, 0), -261.0).bounding_box()
        chk("%s magnet Ø85 at y260..261" % sid, abs((sl[3] - sl[0]) - 85) < 0.2, "%.2f" % (sl[3] - sl[0]))

    # CU bay components vs body_centre_unit.json component boxes
    cu_map = [("CU-E-PI5", "라즈베리파이 5"), ("CU-E-AMP", "앰프 보드"), ("CU-E-BUCK", "5.1 V 강압 모듈"),
              ("CU-E-PEDBOARD", "페달 보드"), ("CU-E-PEDZERO", "페달 보드"), ("CU-E-J702BOARD", "앰프 입력 잭 기판"),
              ("CU-E-J702", "앰프 입력 잭 기판"), ("CU-E-FUSE", "퓨즈 홀더"), ("CU-E-PDTRIG", "PD 트리거"),
              ("CU-E-J501BOARD", "페달 잭"), ("PB-E-HUB", "USB 허브"), ("PB-E-BANK", "보조배터리(최대)")]
    jd = F["cheeks"]["headphone_jack"]["jack_dims"]
    for pid, cname in cu_map:
        b = bb(P[pid])
        box = dict(comp[cname])
        if pid == "CU-E-J702":   # jack nose Ø5 x 2.5 overhangs the board rear edge y271 (keep-out j702_plug y271..311)
            box["y"] = [box["y"][0], box["y"][1] + jd["nose_L"]]
        if pid == "PB-E-HUB":    # v3 A18 / BOM L17: taped to the back wall -> same x/z, y shifted to end at the wall y398.5
            dy = 398.5 - box["y"][1]
            box["y"] = [box["y"][0] + dy, box["y"][1] + dy]
            cname += " (뒷벽에 붙임 +%.1f)" % dy
        chk("%s inside CU-spec box '%s' %s" % (pid, cname, fmt([box["x"][0], box["y"][0], box["z"][0], box["x"][1], box["y"][1], box["z"][1]])),
            inside(b, box), fmt(b))
    # plan-view exceptions that are reported, not failed
    res.append((True, "info: J702 nose y271..273.5 overhangs the board rear edge into keep-out j702_plug (plug side, intended)", fmt(bb(P["CU-E-J702"]))))
    # Pi 5 port edge: RJ45, USB-A stack, USB-A stack from the power/HDMI edge (y336), faces 2.5 past the board edge x616
    pb5 = bb(P["CU-E-PI5"])
    pp = [bb(P["CU-E-PI5-" + k]) for k in ("RJ45", "USBA1", "USBA2")]
    yc = [(q[1] + q[4]) / 2 for q in pp]
    chk("Pi 5 port order from the power/HDMI edge y%.0f: RJ45 < USB-A 1 < USB-A 2 (y centres %s)" % (pb5[1], " / ".join("%.2f" % v for v in yc)),
        pb5[1] < pp[0][1] and yc[0] < yc[1] < yc[2] and pp[2][4] <= pb5[4] + EPS and pp[0][4] <= pp[1][1] and pp[1][4] <= pp[2][1])
    chk("Pi 5 port faces x%.1f = board edge + 2.5 (rearbar 'overhang 2.5')" % (pb5[3] + 2.5), all(abs(q[3] - pb5[3] - 2.5) < EPS for q in pp),
        " ".join(fmt(q) for q in pp))
    gb = bb(P["CU-E-GENDER"])
    chk("CU-E-GENDER in the LOWER port of the USB-A stack next to the RJ45 (y%.2f..%.2f, z < 50)" % (pp[1][1], pp[1][4]),
        gb[1] <= yc[1] <= gb[4] and gb[5] < 50 and abs((gb[1] + gb[4]) / 2 - yc[1]) < EPS and abs(gb[0] - pp[1][3]) < EPS, fmt(gb))
    upb = P["C-USB-UPSTREAM"].solid.trim_by_plane((-1, 0, 0), -662.0).trim_by_plane((0, 0, -1), -75.0).bounding_box()
    chk("C-USB-UPSTREAM plug in the UPPER port of the GPIO-edge stack (y%.2f..%.2f, z > 49)" % (pp[2][1], pp[2][4]),
        upb[1] <= yc[2] <= upb[4] and upb[2] >= 49 and abs(upb[0] - pp[2][3]) < EPS, fmt(upb))
    ko = next(k for k in tray["keep_out"] if k["name"] == "pi_usb_plugs")["box"]
    for pid, b in (("CU-E-GENDER", gb), ("CU-E-DONGLE", bb(P["CU-E-DONGLE"])),
                   ("C-USB-UPSTREAM (part below z75, x<=662)", upb)):
        chk("%s plan inside keep-out pi_usb_plugs x616..662 y336..392" % pid,
            b[0] >= ko["x"][0] and b[3] <= ko["x"][1] + EPS and b[1] >= ko["y"][0] and b[4] <= ko["y"][1], fmt(b))
    cb = comp["USB 동글 + 젠더"]
    res.append((True, "info: spec component box 'USB 동글 + 젠더' y%s is where the Pi 5 RJ45 sits - gender moved to the USB-A stack" % cb["y"], fmt(gb)))
    # one PJ-313 envelope (frame spec jack_dims) for J701 / J501 / J702: bbox W x (L + nose) x H
    want = (jd["body_W"], jd["body_L"] + jd["nose_L"], jd["body_H"])
    for pid in ("EL-E-J701", "CU-E-J501", "CU-E-J702"):
        b = bb(P[pid])
        got = (b[3] - b[0], b[4] - b[1], b[5] - b[2])
        chk("%s PJ-313 envelope %.1f x %.1f x %.1f (SHOU HAN 5JCJ)" % (pid, *want), all(abs(g_ - w_) < EPS for g_, w_ in zip(got, want)),
            "%.2f x %.2f x %.2f" % got)
    b = bb(P["CU-E-J702"])
    jb2 = bb(P["CU-E-J702BOARD"])
    chk("CU-E-J702 base on the board top z%.1f, axis z%.1f, nose from the rear edge y%.0f" % (jb2[5], jb2[5] + jd["axis_above_base"], jb2[4]),
        abs(b[2] - jb2[5]) < EPS and abs(b[4] - jb2[4] - jd["nose_L"]) < EPS and abs((b[0] + b[3]) / 2 - 691) < EPS, fmt(b))
    b = bb(P["CU-E-J501"])
    jb1 = bb(P["CU-E-J501BOARD"])
    chk("CU-E-J501 base on its board top z%.1f and axis z%.1f = hole centre z92; nose tip y%.1f" % (jb1[5], jb1[5] + jd["axis_above_base"], b[4]),
        abs(b[2] - jb1[5]) < EPS and abs(jb1[5] + jd["axis_above_base"] - 92) < EPS and b[4] <= 410 + EPS, fmt(b))
    led = iof["pedal_jack_hole"]["mount"]["box"]
    res.append((True, "info: J501 board bottom z%.2f = required I/O-plate ledge top (spec ledge top z%.1f -> +%.1f, body agent)"
                % (jb1[2], led["z"][1], jb1[2] - led["z"][1]), fmt(jb1)))
    if B:
        io_p = next((p for p in B if p.id == "CU-IOPLATE"), None)
        if io_p is not None:
            lt = io_p.solid.trim_by_plane((1, 0, 0), led["x"][0] + 3).trim_by_plane((-1, 0, 0), -(led["x"][1] - 3)) \
                .trim_by_plane((0, 1, 0), led["y"][0] + 1).trim_by_plane((0, -1, 0), -(led["y"][0] + 10)).bounding_box()
            res.append((True, "info: body CU-IOPLATE ledge top now z%.2f (J501 board bottom z%.2f, gap %.2f)" % (lt[5], jb1[2], jb1[2] - lt[5]), ""))
    # module USB cable lengths: plug 25 + path + hub plug 20 <= 1000 (Coms NA993 1 m)
    import electronics as _el
    cp = _el.cable_plan()
    for t in sorted(k for k in cp["_len"]):
        ln = cp["_len"][t]
        chk("%s-C-USB length %.1f mm <= %.0f (hub port %d x%.0f)" % (t, ln, _el.USB_CABLE_MAX, _el.HUB_PORT[t], cp["_xhub"][t]), ln <= _el.USB_CABLE_MAX)
    chk("O6 / O7 on the two hub ports nearest the tray inlet (lowest x)",
        sorted(cp["_xhub"][t] for t in cp["_xhub"])[:2] == sorted([cp["_xhub"]["O6"], cp["_xhub"]["O7"]]))
    hb = bb(P["PB-E-HUB"])
    chk("PB-E-HUB lying flat against the power-bank bay back wall y398.5 (y350.5..398.5, z33.5..57.5)",
        abs(hb[1] - 350.5) < EPS and abs(hb[4] - 398.5) < EPS and abs(hb[2] - 33.5) < EPS and abs(hb[5] - 57.5) < EPS, fmt(hb))
    # Pi hole pattern = tray boss centres
    pi = P["CU-E-PI5"].solid
    for (x, y) in next(f for f in tray["features"] if f["name"] == "pi5_bosses")["at"]:
        probe = __import__("cadlib").cyl_z(x, y, 39.0, 42.0, 2.5)
        chk("Pi 5 hole over boss (%.1f, %.1f)" % (x, y), (pi ^ probe).volume() < 1e-6)
    for fname, pid in (("amp_bosses", "CU-E-AMP"), ("buck_bosses", "CU-E-BUCK")):
        for (x, y) in next(f for f in tray["features"] if f["name"] == fname)["at"]:
            probe = __import__("cadlib").cyl_z(x, y, 37.0, 70.0, 3.0)
            chk("%s hole + screw column clear over boss (%.1f, %.1f)" % (pid, x, y), (P[pid].solid ^ probe).volume() < 1e-6)
    # I/O plate hole centres (z92)
    for fname, pid in (("pedal_jack_hole", "CU-E-J501"), ("power_switch_hole", "CU-E-SWITCH"), ("usb_c_input", "CU-E-PDTRIG")):
        cxz = iof[fname]["center_xz"]
        b = bb(P[pid])
        chk("%s centred on I/O plate %s x%.0f z%.0f" % (pid, fname, cxz[0], cxz[1]),
            abs((b[0] + b[3]) / 2 - cxz[0]) < 0.05 and (abs((b[2] + b[5]) / 2 - cxz[1]) < 0.35), fmt(b))
    cav = iof["usb_c_input"]["pocket"]["cavity"]
    chk("CU-E-PDTRIG inside the I/O plate pocket cavity", inside(bb(P["CU-E-PDTRIG"]), cav), fmt(bb(P["CU-E-PDTRIG"])))
    # XT30 female inside the holder pocket, mouth at the joint face
    hold = {q["id"]: q for q in S["printed"]}
    for side in "LR":
        pk = hold["xt30_holder_" + side]["pocket"]["world"]
        chk("C-XT30F-%s inside xt30_holder_%s pocket" % (side, side), inside(bb(P["C-XT30F-" + side]), pk), fmt(bb(P["C-XT30F-" + side])))
        mb = bb(P["C-XT30M-" + side])
        chk("C-XT30M-%s toward the centre unit" % side, mb[0] >= 164 - EPS if side == "L" else mb[3] <= 1058 + EPS, fmt(mb))
    # J701 in the cheek pocket
    hj = F["cheeks"]["headphone_jack"]["pocket"]
    cavj = hj["body_cavity"]
    b = bb(P["EL-E-J701"])
    chk("EL-E-J701 body inside cheek cavity x%s z%s, nose from y0" % (cavj["x"], cavj["z"]),
        b[0] >= cavj["x"][0] and b[3] <= cavj["x"][1] and b[2] >= cavj["z"][0] and b[5] <= cavj["z"][1] and abs(b[1]) < EPS
        and b[4] <= cavj["y"][1], fmt(b))
    # hub / bank inside the power-bank bay
    pbay = next(q for q in R["rearbar_items"] if q["id"] == "ref_cu_bay")["boxes"][2]
    for pid in ("PB-E-HUB", "PB-E-BANK"):
        chk("%s inside power-bank bay" % pid, inside(bb(P[pid]), pbay), fmt(bb(P[pid])))
    # CU-bay parts inside the CU bay + I/O plate
    cub = {"x": [525.74, 714.26], "y": [226.5, 412.0], "z": [33.5, 110.5]}
    for p in E:
        if p.group == "CU 칸 전자부":
            chk("%s inside CU bay (x525.74..714.26, y226.5..410 +2 bezel, z33.5..110.5)" % p.id, inside(bb(p), cub), fmt(bb(p)))
    # pedal
    pb_ = bb(P["PEDAL-DAMPER"])
    chk("PEDAL-DAMPER note=offdesk and below the desk", P["PEDAL-DAMPER"].note == "offdesk" and pb_[5] < 0, fmt(pb_))
    # module-local items land in their module (world x = 47 + 164.5 (k-1) + local)
    for k in range(1, 8):
        X0 = 47 + 164.5 * (k - 1)
        b = bb(P["O%d-E-MB" % k])
        chk("O%d-E-MB at local x47.25..117.25" % k, abs(b[0] - X0 - 47.25) < EPS and abs(b[3] - X0 - 117.25) < EPS, fmt(b))
    if B:
        cu = [p for p in B if re.search("가운데|CU|centre|center", p.group + p.id, re.I)]
        if cu:
            cb = union_bb(cu)
            res.append((True, "info: body centre-unit parts bbox (expect x164..1058 y215..410 z22..122 = 894x195x100)", fmt(cb)))
    for cond, label, det in res:
        print("  %s %s  %s" % ("ok" if cond else "!!", label, det))
    print("=" * 100)
    print("RESULT:", "PASS" if ok else "ISSUES (see !! lines)", "  total %.1f s" % (time.time() - T0))


if __name__ == "__main__":
    main()
