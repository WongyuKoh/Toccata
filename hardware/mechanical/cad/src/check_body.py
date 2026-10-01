"""Self-check for body.py (L2 one-piece rear bar, spec/body_L2.json).

  python3 check_body.py          # parts table, overlaps (body/body, body/key action, body/electronics), L2 spec probes

(1) every body Part: kind / group / bbox / bodies; watertight (trimesh on the exported mesh), no sliver shells; printed parts:
    bed size <= 256, z>=0, one body, volume kept by orient, dims, print name / folder, Korean name, 추정 note format;
    nothing of L1's delete list (the rev 2 TS-* parts included), body.py builds the rev 3 touchscreen from touchscreen_rev3.py; the folded-screen
    'altview' parts are never checked against the standing-screen parts (two states of the same things)
(2) pairwise overlaps (a ^ b volume > 0.01 mm3) with a reason for every intended one: body/body, body/key action (pods and
    centre must not touch the modules), body/electronics (electronics.py L2; check_electronics.py checks the electronics side in full)
(3) L2 numbers probed on the solids: implementation_notes.check_body.py + the W1 acoustic conditions:
    plan rectangle, every panel / print vs the spec coordinates, speaker inner volume from the solids, driver basket / magnet
    clearances (driver model of electronics.py / electronics_L1.py) incl. the pole vent >= 10 mm along the axis, normal depth,
    slant length, D14, 27 deg sound path band (>= 3.0 vertical under the path for the key action and every rear-unit solid;
    grille plate lower edge = spec exception), grille W1 (open area >= 40 %, holes >= D3, plate <= 2, 4 screws), R18 (nothing of
    the rear unit at y<214 below z75, modules lift out), cable duct, centre unit, joints, feet, BRK2 pins, pods lift off,
    spec centre_contents boxes vs the body solids, pareto_by_angle reproduced by body.PodGeom
(4) R31 touchscreen rev 3 (touchscreen/rev3/design/CAD_SPEC_rev3.md A..G, numbers.json points / checks): screen lid additions + rib rule,
    cradle, hinge sweep 22..90 deg against the lid, Pi, cables, pods, key modules (nothing over the modules at y<=215), heel contact /
    gaps, fold, leg (use, ramp, deploy at 22 deg), cover, clip, screws (axles, M2.5, lid screws with the 5.5 counterbore), print folders
"""
import itertools
import json
import math
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import body  # noqa: E402
import touchscreen_rev3 as TS  # noqa: E402  (rev 3 numbers / poses, the same module body.py builds from)
from cadlib import box, cyl_x, cyl_y, cyl_z, diff, mesh_arrays, orient, prism_x, tidy, union  # noqa: E402

TOL = 0.01
SPEC = json.load(open(os.path.join(HERE, "..", "spec", "body_L2.json")))

# (regex a, regex b, reason) - intended overlaps (order-free)
INTENDED = [
    (r"^BRK2-.-BOLT", r"^BRK2-.-NUT", "M3 볼트 ↔ 너트 나사산 물림 (너트 Ø2.5 구멍으로 모델)"),
    (r"^JOIN-TS-", r"^JOIN-INS-", "M4 손잡이 나사 ↔ 목재 인서트 나사산 물림 (인서트 안지름 Ø3.3으로 모델)"),
    (r"^CU-M3X10-", r"^SEAM-INS-", "M3×10 ↔ 열압입 인서트 나사산 물림 (인서트 안지름 Ø2.6으로 모델)"),
    (r"^JOIN-INS-", r"^SPK.-PLY-SIDEIN$", "L73 나사산 인서트 겉 Ø6.5가 Ø5.8 구멍 벽에 나사산을 냄 (반지름 0.35 물림 - 의도, 아래에서 부피 확인)"),
    (r"^SPK.-INS-\d$", r"^SPK.-BAFFLE$", "L69 열압입 인서트 바깥 Ø6이 Ø5.6 구멍을 녹여 들어감 (반지름 0.2 - 의도, 아래에서 부피 확인)"),
    (r"^SEAM-INS-\d$", r"^SEAM-POSTRAIL-\d$", "L71 열압입 인서트 바깥 Ø4.5가 Ø4 구멍을 녹여 들어감 (반지름 0.25 - 의도, 아래에서 부피 확인)"),
    (r"^TS-M3X20-HINGE-[LR]$", r"^CU-SCREENLID$", "R31 M3×20 경첩 축이 먼 볼 Ø2.5에 직접 탭 (물림 7.6)"),
    (r"^TS-M3X20-LEG$", r"^TS-CRADLE$", "R31 M3×20 다리 축이 다리 걸이 먼 볼 Ø2.5에 직접 탭 (물림 5.4)"),
]
INTENDED_E = [
    (r"^SPK.-BAFFLE$", r"^SPK-.$", "유닛 바스켓 Ø94가 구멍 Ø94를 지남 (같은 원 - 다각형 근사 오차)"),
    (r"^SPK.-GASKET$", r"^SPK-.$", "가스켓 안 Ø94 = 유닛 바스켓 테두리 Ø94 (같은 원 - 다각형 근사 오차)"),
    (r"^XT30-CLIP-.$", r"^C-XT30F-.$", "XT30U-F가 집게 홈에 끼움 (면 일치)"),
    (r"^PR-BACKPLATE$", r"^CU-E-SWITCH$", "로커 몸체 13.2×19.2가 같은 크기 구멍에 스냅 끼움 (면 일치)"),
    (r"^TS-M25-\d$", r"^TS-E-SCREEN$", "R31 M2.5×6이 화면 모서리 구멍에 나사산을 냄 (물림 3, 구멍 안지름 Ø2.2로 모델)"),
]
# spec centre_contents boxes (the electronics agent's envelopes) vs body solids: boxes are coarse, these touch by design
INTENDED_CC = [
    (r"^C-XT30-L$", r"^XT30-CLIP-L$", "XT30 짝 상자 = 집게 자리"), (r"^C-XT30-R$", r"^XT30-CLIP-R$", "XT30 짝 상자 = 집게 자리"),
    (r"^Z-TS-[LR][12]$", r"^JOIN-(TS|SLV)-", "나비나사 머리 + 고무 슬리브 자리"),
    (r"^IO-CABLEPASS$", r"^PR-BACKPLATE$", "케이블 통과 Ø12 (사각 상자 ↔ 둥근 구멍)"),
    (r"^CU-E-SWITCH$", r"^PR-BACKPLATE$", "KCD1 테두리 15×21 상자가 판 구멍·오목 자리에 끼움"),
    (r"^CU-E-J501$", r"^PR-BACKPLATE$", "J501 코 Ø6이 판 구멍 Ø6.3에 (사각 상자 ↔ 둥근 구멍)"),
    (r"^CU-E-PEDBOARD$", r"^CU-POST-PED-[34]$", "위치 핀 Ø2.8이 기판 구멍 Ø3.0에"),
    (r"^CU-E-FUSE$", r"^CU-FUSECRADLE$", "퓨즈 홀더 Ø10 사각 상자가 받침 Ø%.1f에 (상자 모서리)" % body.FUSE_BORE),
    (r"^Z-SPKLEAD-L2$", r"^XT30-CLIP-L$", "집게 판 윗부분(z50~54, x271.5~274.5, y233.5~252.5)이 스피커선 구역 가장자리에 - 선은 판 뒤(y256에서 끝벽을 떠남)"),
    (r"^Z-SPKLEAD-L2$", r"^CABLE-CLIP-E[12]$", "끝벽 케이블 집게가 스피커선 구역 안에서 선(x275.1 z53)을 잡음"),
    (r"^Z-HUB-DROPS$", r"^CU-PLY-BOTTOM$", "구역 상자(y214~247, z0~40)가 아랫판 앞 6 mm를 덮음 - 선은 플러그(y247, z28.5)에서 R15로 z27 위에서 "
                                           "꺾여 통로(y<241)로 내려가 판에 닿지 않음 (앞 모서리 R3)"),
]
L1_GONE = [r"^SPK.-PLY-FRONT$", r"^SPK.-XT30HOLDER$", r"^JOIN-DT-", r"^JOIN-LATCH-", r"^CU-PLY-P\d\d$", r"^CU-TRAY$", r"^CU-LIDSUP-",
           r"^CU-MAG-(SUP|LID)-(KS|CU|PB)-", r"^CU-KSINSERT$", r"^CU-SMALLBOX", r"^CU-LID$", r"^CU-IOPLATE$", r"^BRK-[LR]",
           r"^TS-(E-TD2|C-POWER$|RCLIP-(LID|CR)$|M3X10-LID|M25-LUG)"]                 # rev 2 (Touch Display 2) touchscreen parts
BRK_FAMILY = r"^BRK2-"


def bbox_overlap(a, b):
    return not any(a[i] > b[i + 3] or b[i] > a[i + 3] for i in range(3))


def other_state(a, b):
    """R31: the folded screen ('altview') and the standing screen are two states of the same parts - never checked against each other."""
    return (a.note == "altview") != (b.note == "altview") and "터치" in a.group and "터치" in b.group


def overlaps(A, Bs, same=False):
    res = []
    bbA = [p.solid.bounding_box() for p in A]
    bbB = bbA if same else [p.solid.bounding_box() for p in Bs]
    pairs = itertools.combinations(range(len(A)), 2) if same else ((i, j) for i in range(len(A)) for j in range(len(Bs)))
    for i, j in pairs:
        b = A[j] if same else Bs[j]
        if not bbox_overlap(bbA[i], bbB[j]) or other_state(A[i], b):
            continue
        v = (A[i].solid ^ b.solid).volume()
        if v > TOL:
            res.append((v, A[i], b))
    return res


def classify(res, rules):
    ok, bad = [], []
    for v, a, b in res:
        why = None
        for ra, rb, w in rules:
            if (re.search(ra, a.id) and re.search(rb, b.id)) or (re.search(ra, b.id) and re.search(rb, a.id)):
                why = w
                break
        (ok if why else bad).append((v, a, b, why))
    return ok, bad


def union_bb(ps):
    bs = [(p.solid if hasattr(p, "solid") else p).bounding_box() for p in ps]
    return [min(b[i] for b in bs) for i in range(3)] + [max(b[i + 3] for b in bs) for i in range(3)]


def fmt(b):
    return "x%.2f~%.2f y%.2f~%.2f z%.2f~%.2f (%.2f × %.2f × %.2f)" % (b[0], b[3], b[1], b[4], b[2], b[5], b[3] - b[0], b[4] - b[1], b[5] - b[2])


def hangul(s):
    return any("가" <= ch <= "힣" for ch in s)


def watertight(m):
    """the mesh as build_all writes it (tidy) is a closed, consistently wound volume."""
    import trimesh
    v, f = mesh_arrays(tidy(m))
    t = trimesh.Trimesh(vertices=v, faces=f, process=True)
    return bool(t.is_watertight and t.is_winding_consistent and t.is_volume)


class Checks:
    def __init__(self):
        self.res = []

    def chk(self, label, got, want, tol=0.011):
        got, want = tuple(float(g) for g in got), tuple(float(w) for w in want)
        good = len(got) == len(want) and all(abs(g - w) <= tol for g, w in zip(got, want))
        self.res.append((good, label))
        print("   %s %-78s got %s  want %s" % ("OK" if good else "!!", label, " ".join("%.3f" % g for g in got),
                                              " ".join("%.3f" % w for w in want)))

    def at_least(self, label, got, lo):
        good = got >= lo
        self.res.append((good, label))
        print("   %s %-78s got %.3f  want >= %.3f" % ("OK" if good else "!!", label, got, lo))

    def at_most(self, label, got, hi):
        good = got <= hi
        self.res.append((good, label))
        print("   %s %-78s got %.3f  want <= %.3f" % ("OK" if good else "!!", label, got, hi))

    def true(self, label, cond, info=""):
        self.res.append((bool(cond), label))
        print("   %s %-78s %s" % ("OK" if cond else "!!", label, info))


def vol(a, b):
    return (a ^ b).volume()


def _seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2_ = ax * ax + ay * ay
    t = 0.0 if L2_ == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2_))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def poly_dist(A, B):
    """distance between two disjoint 2D polygons (vertex-to-edge both ways) - the (y, z) gap of an x-prism wall to a slanted
    cylinder that spans less than the wall in x (the rules-side reference for the clearance probes on the solids)."""
    d = min(_seg_dist(p, B[i], B[(i + 1) % len(B)]) for p in A for i in range(len(B)))
    return min(d, min(_seg_dist(p, A[i], A[(i + 1) % len(A)]) for p in B for i in range(len(A))))


def rect_sw(g, s0, s1, w0, w1):
    """(y, z) outline of the slant-frame rectangle s0..s1 x w0..w1 of PodGeom g (a cylinder's side view)."""
    return [g.D(s0, w0), g.D(s1, w0), g.D(s1, w1), g.D(s0, w1)]


def total_vol(parts, region):
    rb = region.bounding_box()
    return sum(vol(p.solid, region) for p in parts if bbox_overlap(p.solid.bounding_box(), rb))


def hits(parts, region, tol=TOL):
    rb = region.bounding_box()
    return sorted(set(p.id for p in parts if bbox_overlap(p.solid.bounding_box(), rb) and vol(p.solid, region) > tol))


# ------------------------------------------------------------------ driver model (electronics speaker_local, placed on the L2 pose)

def driver_model():
    """(local solid in (a = x, b = up the slant, w = along the axis), source) - the CW-100B25 model of electronics.py, falling back
    to electronics_L1.py, then to a plain envelope (flange 105 x 4 at w3..7, rim / basket D94 w-37..3, magnet D85 w-54..-37)."""
    R = json.load(open(os.path.join(HERE, "..", "spec", "electronics_rearbar.json")))
    for mod in ("electronics", "electronics_L1"):
        try:
            m = __import__(mod)
            loc, info = m.speaker_local(R)
            return loc, "%s.speaker_local (%s)" % (mod, "depth %.0f" % info["depth"])
        except Exception as ex:                                     # the other agent may be mid-edit
            last = "%s: %s" % (type(ex).__name__, ex)
    env = union([box(-52.5, 52.5, -52.5, 52.5, 3.0, 7.0), cyl_z(0, 0, -37.0, 3.0, 94.0), cyl_z(0, 0, -54.0, -37.0, 85.0)])
    return env, "envelope (electronics import failed: %s)" % last


def place_driver(loc, side):
    cx, cy, cz = body.DRIVER_POSE[side]
    U, N = body.SPK_U, body.SPK_N
    return loc.transform(np.array([[1.0, U[0], N[0], cx], [0.0, U[1], N[1], cy], [0.0, U[2], N[2], cz]]))


def to_local(m, side):
    """world -> body slant frame (x - xd, -w, s)."""
    cx = body.DRV_X[side]
    Rt = np.array(body.R_SL, dtype=float).T
    return orient(m.translate((-cx, -body.DRV_YZ[0], -body.DRV_YZ[1])), Rt)


def main():
    t0 = time.time()
    P = body.build()
    C = Checks()
    print("=" * 110)
    print("(1) body parts: %d   (ANGLE %.1f deg, driver centre y%.2f z%.2f, pod top z%.2f, back y%.2f)" % (
        len(P), body.ANGLE, body.DRV_YZ[0], body.DRV_YZ[1], body.SPK_ZT, body.YB))
    print("%-20s %-10s %-12s %s" % ("id", "kind", "group", "bbox (world)"))
    probs = []
    ids = [p.id for p in P]
    if len(set(ids)) != len(ids):
        probs.append("duplicate ids")
    n_wt = 0
    for p in P:
        b = p.solid.bounding_box()
        line = "%-20s %-10s %-12s %s" % (p.id, p.kind, p.group, fmt(b))
        if not hangul(p.name_ko):
            probs.append("%s: name_ko not Korean" % p.id)
        if not p.name_en or not p.group or not p.source:
            probs.append("%s: name_en / group / source missing" % p.id)
        if p.kind == "plywood" and "합판" not in p.material:
            probs.append("%s: plywood material" % p.id)
        if p.solid.is_empty() or str(p.solid.status()).split(".")[-1] != "NoError":
            probs.append("%s: empty or bad status" % p.id)
        comps = p.solid.decompose()
        if min(c.volume() for c in comps) < 0.5:
            probs.append("%s: sliver shell %.3f mm3" % (p.id, min(c.volume() for c in comps)))
        if not watertight(p.solid):
            probs.append("%s: exported mesh not watertight" % p.id)
        else:
            n_wt += 1
        if p.note and "추정" in p.note and not p.note.startswith("추정") and "; 추정" not in p.note and ". 추정" not in p.note:
            probs.append("%s: 추정 note format" % p.id)
        if p.kind == "print":
            if p.print_solid is None:
                if p.note != "altview" or "접은 상태" not in p.group:
                    probs.append("%s: printed part without a print solid" % p.id)
                line += "  | (altview: no print file)"
                print(line)
                continue
            q = p.print_solid.bounding_box()
            sz = (q[3] - q[0], q[4] - q[1], q[5] - q[2])
            line += "  | bed %.1f×%.1f×%.1f" % sz
            if len(comps) != 1 or len(p.print_solid.decompose()) != 1:
                probs.append("%s: %d bodies" % (p.id, len(comps)))
            if abs(q[2]) > 1e-6 or abs(q[0]) > 1e-6 or abs(q[1]) > 1e-6:
                probs.append("%s: print solid not at the bed origin %s" % (p.id, q[:3]))
            if max(sz) > 256.0:
                probs.append("%s: bed size %.1f > 256" % (p.id, max(sz)))
            elif max(sz) > 220:
                line += "  (> 220)"
            if abs(p.print_solid.volume() - p.solid.volume()) > 1e-3 * max(1.0, p.solid.volume()):
                probs.append("%s: print volume changed" % p.id)
            if not watertight(p.print_solid):
                probs.append("%s: print mesh not watertight" % p.id)
            if not p.dims:
                probs.append("%s: no dims" % p.id)
            if not p.print_name or p.print_folder != ("07_터치스크린" if p.id.startswith("TS-") else "05_본체출력물") or not p.print_note:
                probs.append("%s: print name / folder / note" % p.id)
        print(line)
    kinds = {}
    for p in P:
        kinds[p.kind] = kinds.get(p.kind, 0) + 1
    print("kinds:", kinds, "  watertight %d/%d" % (n_wt, len(P)))
    print("part problems:", probs or "none")
    C.true("every part: Korean name, watertight mesh, no sliver shell; prints: 1 body on the bed <= 256, dims, 05 folder (TS-* 07)", not probs,
           "%d problems" % len(probs))
    gone = [i for i in ids if any(re.search(r, i) for r in L1_GONE)]
    C.true("L1 delete list gone (front strips, XT30 holders, dovetails, latches, P01..P11, tray, lid supports, KS insert, "
           "small box, CU lid v2, I/O plate, L1 brackets, rev 2 Touch Display 2 parts)", not gone, ", ".join(gone) or "none left")
    src = open(os.path.join(HERE, "body.py")).read()
    C.true("body.py builds the touchscreen from touchscreen_rev3.py = rev 3 numbers (%s)" % TS.N["revision"][:2],
           re.search(r"^import touchscreen_rev3 as TS", src, re.M) is not None and str(TS.N["revision"]).startswith("3a") and "rev3" in TS.TS_DIR)

    import build_all
    sig = {}
    for p in P:
        if p.kind == "print" and p.print_solid is not None:
            sig.setdefault(build_all.signature(p.print_solid), []).append(p.print_name)
    print("distinct printed shapes: %d" % len(sig))
    names = {}
    for k, v in sig.items():
        names.setdefault(v[0], []).append(k)
    clash = [n for n, ks in names.items() if len(ks) > 1]
    C.true("one print file per distinct shape: no two different shapes share a print name (build_all would overwrite the STL)", not clash,
           ", ".join(clash) or "%d names" % len(names))
    for k, v in sig.items():
        print("   %-34s x%d  (%.1f cm3, bed %s)" % (v[0], len(v), k[0] / 1000.0, "×".join("%.1f" % d for d in k[1])))

    print("=" * 110)
    print("(2) overlaps > %.2f mm3" % TOL)
    res = overlaps(P, None, same=True)
    ok, bad = classify(res, INTENDED)
    print("body ↔ body: %d intended, %d unexpected" % (len(ok), len(bad)))
    for v, a, b, w in ok:
        print("   ok  %8.2f  %-18s %-18s %s" % (v, a.id, b.id, w))
    for v, a, b, w in bad:
        print("   !!  %8.2f  %-18s %-18s at %s" % (v, a.id, b.id, fmt((a.solid ^ b.solid).bounding_box())))
    C.true("body ↔ body: no unexpected overlap (pods, centre, joints, bracket)", not bad, "%d intended" % len(ok))

    import keyaction_parts
    K = keyaction_parts.build_all()
    res = overlaps(P, K)
    okk, badk = classify(res, INTENDED)
    print("body ↔ key action (%d parts): %d intended, %d unexpected" % (len(K), len(okk), len(badk)))
    for v, a, b, w in badk:
        print("   !!  %8.2f  %-18s %-22s at %s" % (v, a.id, b.id, fmt((a.solid ^ b.solid).bounding_box())))
    C.true("body ↔ key action: pods / centre / bracket never cut the modules, end parts or cheeks", not badk and not okk)

    E = None
    try:
        import electronics
        E = electronics.build()
    except Exception as ex:                                         # the other agent may be mid-edit
        print("body ↔ electronics: electronics.build() failed (%s: %s)" % (type(ex).__name__, str(ex)[:120]))
    if E is not None:
        res = overlaps(P, [e for e in E if e.note not in ("offdesk",)])
        oke, bade = classify(res, INTENDED_E)
        print("body ↔ electronics (%d parts, electronics.py L2): %d intended, %d not intended" % (len(E), len(oke), len(bade)))
        for v, a, b, w in sorted(bade, key=lambda r: -r[0])[:25]:
            print("   !!  %8.2f  %-18s %-18s at %s" % (v, a.id, b.id, fmt((a.solid ^ b.solid).bounding_box())))
        if len(bade) > 25:
            print("   !!  (%d more)" % (len(bade) - 25))
        C.true("body ↔ electronics (L2): no unintended overlap (cables, boards, plugs, drivers)", not bade, "%d intended" % len(oke))

    print("=" * 110)
    print("(3) L2 spec numbers (spec/body_L2.json) probed on the solids")
    by = {p.id: p for p in P}
    run_checks(P, by, K, C, E)
    print("=" * 110)
    print("(4) R31 touchscreen rev 3 (touchscreen/rev3/design/CAD_SPEC_rev3.md A..G, numbers.json)")
    run_checks_r31(P, by, K, C, E)
    n_ok = sum(1 for g, _ in C.res if g)
    print("=" * 110)
    print("checks: %d OK, %d failed   (%.1f s)" % (n_ok, len(C.res) - n_ok, time.time() - t0))
    for g, lab in C.res:
        if not g:
            print("   FAILED:", lab)
    return 0 if n_ok == len(C.res) else 1


def run_checks(P, by, K, C, E=None):
    chk, at_least, at_most, true = C.chk, C.at_least, C.at_most, C.true
    B_ = box
    S = SPEC
    SP, CE, JN = S["speakers"], S["centre"], S["joints"]
    brk = [p for p in P if re.match(BRK_FAMILY, p.id)]
    rear = [p for p in P if not re.match(BRK_FAMILY, p.id)]          # the rear unit proper (bracket family sits on the cheeks)
    Y0 = S["overall"]["rear_unit_y"][0]
    # every angle-dependent reference comes from the l2_geom rules at the BUILT angle (G = body.PodGeom(body.ANGLE), an independent
    # instance of the rule class) and the spec pareto_by_angle row of that angle; the spec speakers.* / overall / centre numbers are the
    # record of the selected angle (spec selected_angle) and are compared with the rules only when the built angle is the selected one
    from body import poly_area
    G = body.PodGeom(body.ANGLE)
    YB, ZT = G.y_back, G.z_top                                          # 40 deg: 342.5 / 144.65 (43: 341.5 / 148.06)
    YBI = YB - body.T                                                   # 331 back-ply inner faces (43: 330)
    TOPY0 = G.inner_face_y(ZT - body.T)                                 # top-ply front edge
    PROW = next((r for r in S["pareto_by_angle"]["rows"] if abs(r["baffle_deg"] - body.ANGLE) < 1e-9), None)
    SEL_ANG = S.get("selected_angle", SP["baffle"]["angle_from_horizontal_deg"])
    SEL = abs(SEL_ANG - body.ANGLE) < 1e-9                              # spec speakers.* describe the built angle
    CC_B = {k: tuple(v) for k, v in body.CC.items()}                    # spec centre_contents, back-plate items moved with the back face

    # ---------------- angle (one constant) vs spec selection / pareto row
    print("   --  baffle angle %.1f deg (spec selected_angle %.1f, pareto row %s)" % (body.ANGLE, SEL_ANG, "found" if PROW else "missing"))
    true("built ANGLE %.1f = spec selected_angle %.1f = speakers.baffle angle, pareto row of that angle marked selected" % (body.ANGLE, SEL_ANG),
         SEL and abs(SP["baffle"]["angle_from_horizontal_deg"] - body.ANGLE) < 1e-9 and PROW is not None and PROW.get("selected") is True,
         "change the spec (selected_angle, speakers.*, pareto selected) together with body.ANGLE")
    if PROW:
        chk("rules at %.0f deg = pareto row: centre y z, top z, back y, gross L, flange corner clearance" % body.ANGLE,
            (G.C[0], G.C[1], G.z_top, G.y_back, poly_area(G.cavity()) * 250.0 / 1e6, G.sightline_clear(G.D(-52.5, 7.0))),
            (PROW["driver_centre_yz"][0], PROW["driver_centre_yz"][1], PROW["pod_top_z"], PROW["back_y"], PROW["gross_L_at_250"],
             PROW["flange_corner_clearance_mm"]))
    chk("body exports = rules (driver centre y z, pod top, back y, back-ply inner y, slant length)",
        (body.DRV_YZ[0], body.DRV_YZ[1], body.SPK_ZT, body.YB, body.YBI, body.SL_LEN),
        (G.C[0], G.C[1], G.z_top, G.y_back, YBI, G.s_top - body.S_LOW), tol=1e-9)
    if SEL:
        bpoly_s = next(p for p in SP["panels"] if "baffle" in p["part"])["yz_polygon"]
        dev = max([math.dist(p, q) for p, q in zip(G.outer(), SP["outer_yz_polygon"])] + [math.dist(p, q) for p, q in zip(G.cavity(), SP["inner_yz_polygon"])]
                  + [math.dist(p, q) for p, q in zip(G.baffle_poly(), bpoly_s)] + [math.dist(G.C, SP["driver"]["centre_yz"])])
        true("spec record of the selected angle = rules: speakers outer / inner / baffle polygons, driver centre (<= 0.011), y / z, overall, centre back",
             dev <= 0.011 and abs(SP["y"][1] - YB) < 1e-9 and abs(SP["z"][1] - ZT) < 1e-9 and abs(S["overall"]["y"][1] - YB) < 1e-9
             and abs(S["overall"]["rear_unit_y"][1] - YB) < 1e-9 and abs(S["overall"]["z_max"] - ZT) < 1e-9
             and abs(S["overall"]["depth_behind_keys"] - (YB - 212.0)) < 1e-9 and abs(CE["y"][1] - YB) < 1e-9
             and tuple(CE["walls"]["back_y"]) == (YBI, YB) and abs(SP["baffle"]["slant_length"] - (G.s_top - body.S_LOW)) < 0.011,
             "max vertex deviation %.4f" % dev)
    lb = S["centre_contents_check"].get("layout_back_y", YB)
    true("centre_contents: back-plate items (%s) = spec box + (back y %.1f - layout back y %.1f = %.1f), every other box = spec"
         % (", ".join(body.BACK_PLATE_ITEMS), YB, lb, YB - lb),
         all(CC_B[c["id"]] == tuple(v + ((YB - lb) if (c["id"] in body.BACK_PLATE_ITEMS and i in (2, 3)) else 0.0)
                                    for i, v in enumerate(c["bbox_x0x1y0y1z0z1"])) for c in S["centre_contents"]))

    # ---------------- plan / overall
    print("   --  overall")
    shell = [p for p in P if p.kind in ("plywood", "print") and not p.id.startswith("TS-")]     # the touchscreen stands above (section 4)
    b = union_bb(shell)
    chk("rear-unit shell x-16..1238 (1254), y..%.1f, z..%.2f (rules at %.0f deg; spec overall)" % (YB, ZT, body.ANGLE), (b[0], b[3], b[3] - b[0], b[4], b[5]),
        (S["overall"]["x"][0], S["overall"]["x"][1], 1254.0, YB, ZT))
    allb = union_bb(shell + K)
    chk("key action + rear unit = plan rectangle 1254 x %.1f (x-16..1238, y0..%.1f)" % (YB, YB), (allb[0], allb[3], allb[1], allb[4]),
        (-16.0, 1238.0, 0.0, YB))
    ry = min(p.solid.bounding_box()[1] for p in rear)
    chk("rear unit starts at y%.2f (grille plate edge D(-50, 13), R18 >= 213) / every other part y>=214" % G.D(-50.0, 13.0)[0], (ry,), (G.D(-50.0, 13.0)[0],), tol=0.005)
    low_front = hits(rear, B_(-30, 1250, -10, Y0 - 1e-4, -5, 75.0))
    true("R18: nothing of the rear unit at y<214 below z75 (bracket family on the cheeks excepted)", not low_front, ", ".join(low_front) or "none")
    col = B_(-16.0, 1238.0, -10.0, 212.0, 0.0, 600.0)
    true("modules / end parts lift straight up: nothing of the rear unit over y<=212 at any height", total_vol(rear, col) < TOL)
    true("depth behind the keys = %.1f (y212 -> %.1f, rules at %.0f deg)%s" % (YB - 212.0, YB, body.ANGLE, ", spec depth_behind_keys" if SEL else ""),
         abs(b[4] - 212.0 - (YB - 212.0)) < 1e-6 and (not SEL or abs(YB - 212.0 - S["overall"]["depth_behind_keys"]) < 1e-6), "%.1f" % (b[4] - 212.0))

    # ---------------- speaker pods vs the spec coordinates
    print("   --  speaker pods (rules at the built angle; spec speakers.* = the selected-angle record)")
    outer = G.outer()                                                   # rules at the built angle (= spec outer_yz_polygon when SEL)
    for s in "LR":
        x0, x1 = SP[s]["x"]
        ix0, ix1 = SP[s]["inner_x"]
        pod = [p for p in P if p.id.startswith("SPK%s-PLY" % s) or p.id in ("SPK%s-BAFFLE" % s, "SPK%s-DUCTFORMER" % s)]
        chk("pod %s x%g..%g y%g..%.1f z%g..%.2f" % (s, x0, x1, Y0, YB, body.ZB, ZT), union_bb(pod), (x0, Y0, body.ZB, x1, YB, ZT))
        so, si = by["SPK%s-PLY-SIDEOUT" % s].solid, by["SPK%s-PLY-SIDEIN" % s].solid
        sob, sib = so.bounding_box(), si.bounding_box()
        chk("pod %s side panels x (outer / inner) = spec x, inner x" % s, sorted((sob[0], sob[3], sib[0], sib[3])), sorted((x0, ix0, ix1, x1)))
        chk("pod %s outer side panel = 8-point outer polygon of the rules (area %.1f)" % (s, poly_area(outer)), (so.volume() / 11.5,), (poly_area(outer),), tol=0.5)
        for tag, yz in (("BACK", ((YBI, YB), (body.ZB, ZT))), ("TOP", ((TOPY0, YBI), (ZT - body.T, ZT))), ("BOTTOM", ((241.0, YBI), (body.ZB, body.Z_BOT)))):
            pb = by["SPK%s-PLY-%s" % (s, tag)].solid.bounding_box()
            chk("pod %s %s ply x%g..%g y%.2f..%.1f z%.2f..%.2f" % (s, tag.lower(), ix0, ix1, yz[0][0], yz[0][1], yz[1][0], yz[1][1]), pb,
                (ix0, yz[0][0], yz[1][0], ix1, yz[0][1], yz[1][1]))
        bpoly = G.baffle_poly()
        baf = by["SPK%s-BAFFLE" % s].solid
        bb = baf.bounding_box()
        chk("pod %s baffle bbox = rules yz polygon (y%.2f..%.2f, z%.2f..%.2f), width 250" % (
            s, min(v[0] for v in bpoly), max(v[0] for v in bpoly), min(v[1] for v in bpoly), max(v[1] for v in bpoly)), bb,
            (ix0, min(v[0] for v in bpoly), min(v[1] for v in bpoly), ix1, max(v[0] for v in bpoly), max(v[1] for v in bpoly)))
        slab = B_(ix0, ix0 + 1.0, 0, 400, 0, 200) if s == "L" else B_(ix1 - 1.0, ix1, 0, 400, 0, 200)
        chk("pod %s baffle section area = rules yz polygon area (slab away from the holes)" % s, (vol(baf, slab),), (poly_area(bpoly),), tol=0.5)
        df = by["SPK%s-DUCTFORMER" % s].solid
        fpoly = next(p for p in SP["panels"] if "duct former" in p["part"])["yz_polygon"]
        fixed = G.duct_former_poly()
        chk("pod %s duct former bbox y214..247 z16.5..%.2f, section = rules polygon (spec list with 241/247 fixed, +6x6 roof end)" % (s, G.z_fb),
            (df.bounding_box()[1], df.bounding_box()[4], df.bounding_box()[2], df.bounding_box()[5], vol(df, slab)),
            (214.0, 247.0, 16.5, G.z_fb, poly_area(fixed)), tol=0.5)
        # spec inner polygon vs the actual air (closed-box probe below)
    print("   ..  spec duct-former vertex list self-intersects: listed area %.1f vs built %.1f (the 6 x 6 roof end y241..247 z27..33)"
          % (poly_area([tuple(v) for v in fpoly]), poly_area(fixed)))

    # ---------------- inner volume, driver clearances, pole vent, depth, slant, D14
    print("   --  inner volume / driver (W1 limits)")
    loc, dsrc = driver_model()
    print("   ..  driver model: %s" % dsrc)
    vols = {}
    for s in "LR":
        ix0, ix1 = SP[s]["inner_x"]
        xd = body.DRV_X[s]
        walls = [p.solid for p in P if p.id.startswith("SPK%s-PLY" % s) or p.id in ("SPK%s-BAFFLE" % s, "SPK%s-DUCTFORMER" % s)]
        seals = [body.sl(cyl_y(0, 0, -0.5, 11.5, 94.5), xd) ^ prism_x(body.BAFFLE_POLY, ix0, ix1)]   # driver closes the D94 hole
                                                                                                    # (inside the baffle section only)
        wy, wz = body.WIRE_YZ[s]
        seals.append(cyl_x(wy, wz, ix1 if s == "L" else ix0 - 12.0, ix1 + 12.0 if s == "L" else ix0, 6.5))   # wire hole glued shut
        # the pod walls are x prisms: slice them (merged, + the seals) at several x in the (y, z) plane; the air around the probe
        # D(0, -30) must be an enclosed hole of the wall section (2D booleans have no coplanar-face slivers)
        from manifold3d import CrossSection, FillRule
        inner_walls = union([w for w in walls if w.bounding_box()[0] >= ix0 - 1e-6 and w.bounding_box()[3] <= ix1 + 1e-6] + seals)
        sides = {k: by["SPK%s-PLY-%s" % (s, k)].solid for k in ("SIDEOUT", "SIDEIN")}
        pb = union_bb(walls)
        big = CrossSection.square((pb[4] - pb[1] + 20.0, pb[5] - pb[2] + 20.0)).translate((pb[1] - 10.0, pb[2] - 10.0))
        pr = body.D(0.0, -30.0)
        dot = CrossSection.square((0.2, 0.2)).translate((pr[0] - 0.1, pr[1] - 0.1))
        yz = lambda m, x: orient(m, [[0, 1, 0], [0, 0, 1], [1, 0, 0]]).slice(x)             # section at x in (y, z)
        areas, open_ = [], False
        cav2d = None
        for x in (ix0 + 0.5, xd - 60.0, xd, xd + 40.0, ix1 - 0.5):
            comps = [c for c in (big - yz(inner_walls, x)).decompose() if (c ^ dot).area() > 0.01]
            c = comps[0]
            cbx = c.bounds()
            open_ |= cbx[0] <= pb[1] - 9.0 or cbx[1] <= pb[2] - 9.0 or cbx[2] >= pb[4] + 9.0 or cbx[3] >= pb[5] + 9.0
            areas.append(c.area())
            if abs(x - (ix0 + 0.5)) < 1e-9:
                cav2d = c
        ends = []
        for k, x in (("SIDEOUT", (pb[0] + ix0) / 2.0 if s == "L" else (ix1 + pb[3]) / 2.0),
                     ("SIDEIN", ix1 + 0.5 if s == "L" else ix0 - 0.5)):
            cov = yz(union([sides[k]] + seals), x)
            ends.append((cav2d - cov).area())
        closed = not open_ and max(ends) < 0.01
        leak = max(areas) - min(areas)
        true("pod %s air cavity closed: enclosed hole of the wall section at 5 x (%.0f mm2), side panels cover it (%.3f mm2 open)" % (s, areas[0], max(ends)),
             closed and leak < 0.5, "section spread %.3f mm2" % leak)
        v = sum(areas) / len(areas) * (ix1 - ix0) / 1e6
        cavity = cav2d.extrude(ix1 - ix0)                                   # (y, z, x) frame -> back to world
        cavity = orient(cavity, [[0, 0, 1], [1, 0, 0], [0, 1, 0]]).translate((ix0, 0, 0))
        drv = place_driver(loc, s)
        vnet = v - vol(drv, cavity) / 1e6 if cavity else 0.0
        vols[s] = (v, vnet)
        at_least("pod %s inner volume from the solids, gross (L; spec %.3f at %.0f deg, W1 >= 2.0)" % (s, SP["inner_volume"]["gross_L"], SEL_ANG), v, 2.0)
        chk("pod %s gross volume = rules cavity section %.0f mm2 x 250 (%.0f deg%s)" % (s, poly_area(G.cavity()), body.ANGLE,
            ", pareto row %.3f" % PROW["gross_L_at_250"] if PROW else ""), (v,), (poly_area(G.cavity()) * 250.0 / 1e6,), tol=0.002)
        at_least("pod %s net volume minus the driver model (L; spec net %.3f at %.0f deg, W1 min 1.8)" % (s, SP["inner_volume"]["net_L"], SEL_ANG), vnet, 1.8)
        # clearances (exact mesh distances)
        mag = body.sl(cyl_y(0, 0, 37.0, 54.0, 85.0), xd)
        bsk = body.sl(cyl_y(0, 0, 0.0, 37.0, 94.0), xd)
        names = {"BACK": "back ply", "TOP": "top ply", "BOTTOM": "bottom ply", "SIDEIN": "inner side", "SIDEOUT": "outer side"}
        gaps_m, gaps_b = {}, {}
        for p in P:
            if p.id.startswith("SPK%s-PLY" % s) or p.id == "SPK%s-DUCTFORMER" % s:
                k = names.get(p.id.split("-")[-1], "duct former")
                gaps_m[k] = mag.min_gap(p.solid, 80.0)
                gaps_b[k] = bsk.min_gap(p.solid, 80.0)
        gaps_m["baffle"] = mag.min_gap(by["SPK%s-BAFFLE" % s].solid, 80.0)
        print("   ..  pod %s magnet D85 gaps: %s" % (s, ", ".join("%s %.2f" % kv for kv in sorted(gaps_m.items(), key=lambda kv: kv[1]))))
        print("   ..  pod %s basket D94 gaps: %s" % (s, ", ".join("%s %.2f" % kv for kv in sorted(gaps_b.items(), key=lambda kv: kv[1]))))
        dcl = SP["driver_clearances_mm"]
        mag_sw, bsk_sw = rect_sw(G, -42.5, 42.5, -54.0, -37.0), rect_sw(G, -47.0, 47.0, -37.0, 0.0)    # side views of the two cylinders
        r_back = poly_dist(mag_sw, [(YBI, body.ZB), (YB, body.ZB), (YB, ZT), (YBI, ZT)])
        r_bot = poly_dist(mag_sw, [(241.0, body.ZB), (YBI, body.ZB), (YBI, body.Z_BOT), (241.0, body.Z_BOT)])
        r_fmr = poly_dist(bsk_sw, G.duct_former_poly())
        chk("pod %s magnet rim -> back ply inner face (rules %.2f; spec %.2f at %.0f deg; target >= 3.5)" % (s, r_back, dcl["magnet_back_rim_to_back_ply"], SEL_ANG),
            (gaps_m["back ply"],), (r_back,), tol=0.05)
        at_least("pod %s magnet -> every wall (W1 >= 2)" % s, min(gaps_m.values()), 2.0)
        chk("pod %s magnet lowest rim above the bottom ply (rules %.2f; spec %.2f)" % (s, r_bot, dcl["magnet_lowest_rim_above_bottom_ply"]),
            (gaps_m["bottom ply"],), (r_bot,), tol=0.05)
        chk("pod %s basket -> duct former (sill rear face y225; rules %.2f, spec %.2f)" % (s, r_fmr, dcl["basket_D94_generators"]["front-wall sill rear face (y225)"]),
            (gaps_b["duct former"],), (r_fmr,), tol=0.05)
        at_least("pod %s basket -> every ply / printed wall except the baffle it passes (W1 >= 2)" % s, min(gaps_b.values()), 2.0)
        true("pod %s driver model clear of every pod wall (basket D94 in the D94 hole: polygon error only)" % s,
             sum(vol(drv, w) for w in walls[:-2]) < TOL and vol(drv, by["SPK%s-DUCTFORMER" % s].solid) < TOL and vol(drv, by["SPK%s-BAFFLE" % s].solid) < 5.0,
             "baffle %.2f mm3" % vol(drv, by["SPK%s-BAFFLE" % s].solid))
        # pole vent (W1): nothing within 10 along the axis behind the magnet (walls; the fill is kept away there, see the note)
        wall_u = union(walls)
        pv0, pv1 = body.D(0.0, -54.0), body.D(0.0, -300.0)
        hitsr = wall_u.ray_cast((xd, pv0[0], pv0[1]), (xd, pv1[0], pv1[1]))
        free = hitsr[0].distance * math.hypot(pv1[0] - pv0[0], pv1[1] - pv0[1]) if hitsr else 999.0
        at_least("pod %s pole vent: free length along the axis behind the magnet (W1 >= 10)" % s, free, 10.0)
        true("pod %s pole vent: D20 x 10 cylinder behind the magnet clear of every wall" % s, vol(body.sl(cyl_y(0, 0, 54.0, 64.0, 20.0), xd), wall_u) < TOL)
        o0, o1 = body.D(0.0, 0.0), body.D(0.0, -300.0)
        hitsn = union(walls[:-1] + [by["SPK%s-DUCTFORMER" % s].solid]).ray_cast((xd, o0[0], o0[1]), (xd, o1[0], o1[1]))
        hitsn = [h for h in hitsn if h.distance * 300.0 > 11.6]
        nd = hitsn[0].distance * 300.0 if hitsn else 999.0
        at_least("pod %s depth along the normal from the outer face to the first wall (spec %.1f, W1 >= 72)" % (s, SP["driver_clearances_mm"]["inside_depth_along_normal_from_outer_face"]), nd, 72.0)
        v_, f_ = mesh_arrays(to_local(baf := by["SPK%s-BAFFLE" % s].solid, s))
        face = v_[np.abs(v_[:, 1]) < 1e-4]
        sl_len = face[:, 2].max() - face[:, 2].min()
        chk("pod %s baffle outer face slant length (rules %.2f, W1 >= 118)" % (s, G.s_top - body.S_LOW), (sl_len,), (G.s_top - body.S_LOW,), tol=0.02)
        at_least("pod %s baffle outer face slant length (W1 >= 118)" % s, sl_len, 118.0)
        dv, _ = mesh_arrays(drv)
        dmin = np.min(np.hypot(dv[:, 1] - body.SENSOR_YZ[0], dv[:, 2] - body.SENSOR_YZ[1]))
        mc = body.D(0.0, -45.5)
        mcg = G.D(0.0, -45.5)
        chk("pod %s D14 magnet centre -> sensor row (y67 z8) - spec reading (rules %.1f; spec %.1f at %.0f deg; >= 100)" % (
            s, math.hypot(mcg[0] - 67.0, mcg[1] - 8.0), SP["d14"]["to_sensor_row_mm"], SEL_ANG),
            (math.hypot(mc[0] - 67.0, mc[1] - 8.0),), (math.hypot(mcg[0] - 67.0, mcg[1] - 8.0),), tol=0.06)
        at_least("pod %s D14 magnet centre -> hall elements (y%.0f z%.1f = pocket floor 12.19 + 0.75)" % (s, body.SENSOR_YZ[0], body.SENSOR_YZ[1]),
                 math.hypot(mc[0] - body.SENSOR_YZ[0], mc[1] - body.SENSOR_YZ[1]), 100.0)
        at_least("pod %s D14 nearest driver steel -> hall elements (spec %.1f to z8)" % (s, SP["d14"]["nearest_steel_point_mm"]), dmin, 100.0)
    top_rule = round(body.D(52.5, 13.0)[1] + 0.5, 2)
    chk("pod top = grille plate over the frame corner D(52.5, 13) + 0.5 (touchscreen aside)", (max(p.solid.bounding_box()[5] for p in P if not p.id.startswith("TS-")),),
        (top_rule,), tol=0.005)

    # ---------------- 27 deg sound path (W1)
    print("   --  27 deg sound path from the D94 lower edge D(-47, 0)")
    qy, qz = body.D(-47.0, 0.0)
    zl = lambda y: qz + (qy - y) * body.TAN27

    def band(xd, below, above=0.0, y_from=-20.0):
        return prism_x([(y_from, zl(y_from) - below), (qy, qz - below), (qy, qz + above), (y_from, zl(y_from) + above)], xd - 47.0, xd + 47.0)

    src = lambda p: re.match(r"^SPK.-(BAFFLE|GASKET|GRILLE)$", p.id)
    solids_k = K
    solids_r = [p for p in P if not src(p)]
    for s in "LR":
        xd = body.DRV_X[s]
        vk, vr = total_vol(solids_k, band(xd, 3.0)), total_vol(solids_r, band(xd, 3.0))
        true("pod %s: band 3.0 under the path (x%.1f±47, y<%.2f) empty of the key action and every rear-unit solid" % (s, xd, qy),
             vk < TOL and vr < TOL, "key %.3f, rear %.3f mm3" % (vk, vr))
        lo, hi = 3.0, 25.0
        for _ in range(22):
            mid = (lo + hi) / 2.0
            if total_vol(solids_k, band(xd, mid)) < TOL:
                lo = mid
            else:
                hi = mid
        chk("pod %s: vertical clearance of the path over the key action (module rear top edge y212 z72.85; rules %.3f, W1 >= 3.0)" % (
            s, G.sightline_clear((212.0, 72.85))), (lo,), (G.sightline_clear((212.0, 72.85)),), tol=0.02)
        at_least("pod %s: vertical clearance of the path over the key action (W1 >= 3.0)" % s, lo, 3.0)
        lo2, hi2 = 3.0, 40.0
        for _ in range(22):
            mid = (lo2 + hi2) / 2.0
            if total_vol(solids_r, band(xd, mid)) < TOL:
                lo2 = mid
            else:
                hi2 = mid
        print("   ..  pod %s: nearest rear-unit solid under the path (baffle / gasket / grille aside): %.2f vertical (rules: front-wall top front edge %.2f)"
              % (s, lo2, G.sightline_clear((Y0, G.z_fb))))
        below = prism_x([(-20.0, -10.0), (qy, -10.0), (qy, qz), (-20.0, zl(-20.0))], xd - 47.0, xd + 47.0)
        gr = by["SPK%s-GRILLE" % s].solid
        true("pod %s: grille never comes down into the path inside the cone (x%.1f±47)" % (s, xd), vol(gr, below) < TOL,
             "%.3f mm3" % vol(gr, below))
        lgc = (to_local(gr, s) ^ B_(-47.0, 47.0, -13.01, -10.99, -60.0, 60.0)).bounding_box()      # plate over the cone, local frame
        perp = min(G.perp_clear(G.D(lgc[2], w)) for w in (-lgc[4], -lgc[1]))
        chk("pod %s: grille plate lower edge %.2f perpendicular over the path (rules D(-50, 11) %.2f; plate exception accepted by W1 - 0.94 at 43 deg)"
            % (s, perp, G.perp_clear(G.D(-50.0, 11.0))), (perp,),
            (G.perp_clear(G.D(-50.0, 11.0)),), tol=0.02)
        drv = place_driver(loc, s)
        dv, _ = mesh_arrays(drv)
        mm = (dv[:, 1] < qy)
        vc = qz + (qy - dv[mm, 1]) * body.TAN27 - dv[mm, 2]
        below_pts = vc[vc > 0]
        fl = below_pts.min() if len(below_pts) else 99.0
        r_fl = G.sightline_clear(G.D(-52.5, 7.0))
        acc = S.get("angle_decision", {}).get("w1_flange_corner_accepted_mm") if SEL else None
        lim_fl = 3.0 if r_fl >= 3.0 else (acc - 0.02 if acc else 3.0)        # W1 strict 3.0; at the selected angle W1 accepted its corner value
        at_least("pod %s: driver flange lower corner under the path - spec reading (corner only; the line starts behind the flange) (rules %.2f; W1 strict 3.0%s)" % (
            s, r_fl, "" if r_fl >= 3.0 else ", %.0f deg: W1 accepted %s" % (body.ANGLE, acc)), fl, lim_fl)
        chk("pod %s: driver flange lower corner under the path = rules D(-52.5, 7)" % s, (fl,), (r_fl,), tol=0.03)
        gk = by["SPK%s-GASKET" % s].solid
        gv2, _ = mesh_arrays(gk)
        vc2 = qz + (qy - gv2[:, 1]) * body.TAN27 - gv2[:, 2]
        low_corner = vc2[(gv2[:, 1] < body.D(-52.4, 0.0)[0])]
        chk("pod %s: gasket lower corner D(-52.5, 3) under the path - spec reading (corner only; the line starts behind the gasket) (rules %.2f)" % (s, G.sightline_clear(G.D(-52.5, 3.0))),
            (low_corner.min(),), (G.sightline_clear(G.D(-52.5, 3.0)),), tol=0.02)
        bv = [tuple(v) for v in mesh_arrays(by["SPK%s-BAFFLE" % s].solid)[0]]
        fz_ = min(v[2] for v in bv)
        f_built = min((v for v in bv if abs(v[2] - fz_) < 1e-6), key=lambda v: v[1])          # outer lower edge of the built baffle
        chk("pod %s: baffle outer lower edge F (y%.2f z%.2f) under the path (rules %.2f)" % (s, f_built[1], f_built[2], G.sightline_clear(G.F)),
            (G.sightline_clear((f_built[1], f_built[2])),), (G.sightline_clear(G.F),), tol=0.02)
        chk("pod %s: grille side-wall foot D(-50, 0) under the path (outside the cone; rules %.2f)" % (s, G.sightline_clear(G.D(-50.0, 0.0))),
            (body.POD.sightline_clear(body.D(-50.0, 0.0)),), (G.sightline_clear(G.D(-50.0, 0.0)),), tol=0.02)

    # the spec line starts at the D94 edge D(-47, 0) on the baffle face, BEHIND the gasket (w0..3) and the flange (w3..7): the real
    # radiating edge is the frame opening D(-45, 7) (cone recess D90) - cast the 27 deg path from there
    print("   --  27 deg path from the real radiating edge D(-45, 7) (frame opening; the spec line starts behind the gasket and flange)")
    o = body.D(-45.0, 7.0)
    c27, s27 = math.cos(math.radians(27.0)), math.sin(math.radians(27.0))
    far = (o[0] - 400.0 * c27, o[1] + 400.0 * s27)
    zl2 = lambda y: o[1] + (o[0] - y) * body.TAN27
    rear_ng = [p for p in P if not re.match(r"^SPK.-GRILLE$", p.id)]
    for s in "LR":
        xd = body.DRV_X[s]
        hit_ids = set()
        for x in (xd - 45.0, xd - 22.5, xd, xd + 22.5, xd + 45.0):
            for p in rear_ng + K:
                bb_ = p.solid.bounding_box()
                if not (bb_[0] <= x <= bb_[3] and bb_[1] <= o[0] and bb_[4] >= far[0] and bb_[5] >= o[1] and bb_[2] <= far[1]):
                    continue
                if p.solid.ray_cast((x, o[0], o[1]), (x, far[0], far[1])):
                    hit_ids.add(p.id)
        true("pod %s: 27 deg rays from D(-45, 7) at x%.1f±45 hit no rear-unit solid (grille aside) and no key-action part" % (s, xd), not hit_ids,
             ", ".join(sorted(hit_ids)) or "clear")
        clr = zl2(212.0) - 72.85
        at_least("pod %s: real path over the module rear top edge (y212, z72.85) (W1 >= 3.0; spec line from D(-47, 0): %.2f)" % (
            s, G.sightline_clear((212.0, 72.85))), clr, 3.0)
        band_r = prism_x([(-20.0, zl2(-20.0) - 3.0), (o[0], o[1] - 3.0), (o[0], o[1]), (-20.0, zl2(-20.0))], xd - 45.0, xd + 45.0)
        vr_, vk_ = total_vol(rear_ng, band_r), total_vol(K, band_r)
        true("pod %s: band 3.0 under the real path (x%.1f±45) empty of every rear-unit solid (grille aside) and the key action" % (s, xd),
             vr_ < TOL and vk_ < TOL, "rear %.3f, key %.3f mm3" % (vr_, vk_))
        print("   ..  pod %s: real path clears (212, 72.85) by %.2f; only the grille's solid lower bar (s-50..-48) meets it (W1 plate exception)" % (s, clr))

    # ---------------- grille (R18 + W1 conditions)
    print("   --  grille (W1: open >= 40 %, holes >= D3, plate <= 2, 4 screws)")
    for s in "LR":
        xd = body.DRV_X[s]
        gr = by["SPK%s-GRILLE" % s].solid
        gb = gr.bounding_box()
        at_least("grille %s plate lower edge y (R18 >= 213)" % s, gb[1], 213.0)
        chk("grille %s 150 wide (x%.1f..%.1f), top cut at the pod top z%.2f" % (s, xd - 75, xd + 75, ZT), (gb[0], gb[3], gb[5]), (xd - 75.0, xd + 75.0, ZT))
        lg = to_local(gr, s)
        lv, _ = mesh_arrays(lg)
        chk("grille %s plate outer face w13, stands on the baffle face w0 (local y -13 .. 0)" % s, (lv[:, 1].min(), lv[:, 1].max()), (-13.0, 0.0), tol=0.005)
        inner = B_(-46.9, 46.9, -10.99, -0.01, -49.9, 50.9)
        true("grille %s: nothing between the plate and the baffle in front of the cone (no lower ring wall)" % s, vol(lg, inner) < TOL)
        low_ring = B_(-53.0, 53.0, -11.0, 0.0, -60.0, -50.0)
        true("grille %s: no lower ring wall (nothing below s-50 inside x±53)" % s, vol(lg, low_ring) < TOL)
        plate_disc = cyl_y(0, 0, -13.0, -11.0, 94.0)
        frac = 1.0 - vol(lg, plate_disc) / plate_disc.volume()
        at_least("grille %s open area in front of the D94 cone (W1 >= 40 %%)" % s, 100.0 * frac, 40.0)
        reg = B_(-53.0, 53.0, -13.0, -11.0, -50.0, body.S_PLATE_TOP)
        frac2 = 1.0 - vol(lg, reg) / reg.volume()
        at_least("grille %s open area of the whole plate inside the ring (x±53, s-50..%.1f) (W1 >= 40 %%)" % (s, body.S_PLATE_TOP), 100.0 * frac2, 40.0)
        from manifold3d import CrossSection, FillRule, JoinType
        cs = orient(lg, [[1, 0, 0], [0, 0, 1], [0, 1, 0]]).slice(-12.0)          # plate section in (x, s)
        region = CrossSection([[(-52.9, -49.9), (52.9, -49.9), (52.9, body.GR_LAT[1] + 1.0), (-52.9, body.GR_LAT[1] + 1.0)]], FillRule.NonZero)
        holes_cs = (region - cs).decompose()
        small = [h for h in holes_cs if h.offset(-1.5, JoinType.Round).is_empty()]
        chk("grille %s: %d hex holes, every one holds a D3 circle (W1 >= D3)" % (s, len(holes_cs)), (len(small),), (0,))
        true("grille %s: 4 screw holes D4.5 open through the side walls, over 4 baffle pilots D3.4 x 9" % s,
             all(vol(gr, body.sl(cyl_y(hx, hz, -13.5, 0.5, 4.3), xd)) < TOL and vol(by["SPK%s-BAFFLE" % s].solid, body.sl(cyl_y(hx, hz, 0.2, 8.8, 3.2), xd)) < TOL
                 for (hx, hz) in body.GR_HOLES))
        drv = place_driver(loc, s)
        heads = union([body.sl(cyl_y(px, pz, -9.7, -7.0, 8.0), xd) for (px, pz) in body.DRV_PIL])     # M4 button heads 2.2 + 0.5
        true("grille %s clear of the driver model and the M4 screw heads (plate w11 vs heads <= 9.7)" % s,
             vol(gr, union([drv, heads])) < TOL, "%.3f" % vol(gr, union([drv, heads])))

    # ---------------- baffle holes / gasket
    for s in "LR":
        xd = body.DRV_X[s]
        baf = by["SPK%s-BAFFLE" % s].solid
        true("baffle %s: D94 hole open (D93.8 through), M4 inserts D5.6 x 6.5 blind, 4 at PCD115 45 deg" % s,
             vol(baf, body.sl(cyl_y(0, 0, -0.5, 12.0, 93.8), xd)) < TOL
             and all(vol(baf, body.sl(cyl_y(px, pz, 0.2, 6.3, 5.4), xd)) < TOL for (px, pz) in body.DRV_PIL)
             and all(vol(baf, body.sl(cyl_y(px, pz, 6.6, 11.4, 5.4), xd)) > 50.0 for (px, pz) in body.DRV_PIL))
        gk = by["SPK%s-GASKET" % s].solid
        true("gasket %s 3 mm on the outer face, no overlap with the baffle" % s, vol(gk, baf) < TOL and abs(to_local(gk, s).bounding_box()[1] + 3.0) < 1e-3)
        ring = math.pi / 4 * (body.DRV_INS[0] ** 2 - body.DRV_INSERT[0] ** 2) * body.DRV_INS[2]
        ins_ok = []
        for k, (px, pz) in enumerate(body.DRV_PIL):
            im = by["SPK%s-INS-%d" % (s, k + 1)].solid
            li = to_local(im, s).bounding_box()
            ins_ok.append(abs(li[1]) < 1e-3 and abs(li[4] - body.DRV_INS[2]) < 1e-3 and abs(vol(im, baf) - ring) < 0.3 and vol(im, gk) < TOL)
        tip = body.DRV_SCREW_IN
        true("baffle %s: 4 L69 inserts OD %.0f x %.0f flush with the outer face in the D%.1f x %.1f holes (%.1f mm3 melted in each); M4x12 through flange %.0f + "
             "gasket %.0f -> %.0f in: %.0f past the insert, %.1f above the hole bottom" % (s, body.DRV_INS[0], body.DRV_INS[2], body.DRV_INSERT[0], body.DRV_INSERT[1],
                                                                                          ring, body.DRV_SCREW[1], body.DRV_SCREW[2], tip, tip - body.DRV_INS[2],
                                                                                          body.DRV_INSERT[1] - tip),
             all(ins_ok) and body.DRV_INS[2] < tip < body.DRV_INSERT[1] - 1.0)

    # ---------------- cable duct, caps, sockets, bracket
    print("   --  cable duct y212..241 z0..27, caps, BRK2 pins")
    duct = B_(-16.0, 1238.0, 212.0, 241.0, 0.0, 27.0)
    dh = hits(P, duct)
    true("duct y212..241 z0..27 holds only the bracket family, the pin sockets, the end caps and the roof cable clips (z19..27)",
         all(re.match(r"^(BRK2-|POD-SOCKET-|DUCT-CAP-|CABLE-CLIP-[LR])", i) for i in dh), ", ".join(dh))
    cl = [by[i].solid.bounding_box() for i in by if re.match(r"^CABLE-CLIP-[LR]\d$", i)]
    true("roof cable clips hang z19..27 over y226..236 (above the bundle top z16.25), 3 per pod", len(cl) == 6 and all(abs(b[2] - 19.0) < 1e-6 and abs(b[5] - 27.0) < 1e-6 for b in cl))
    worst = 1e9
    for x in [-12.5 + 5.0 * i for i in range(250)]:
        occ = total_vol(P, B_(x, x + 1.0, 212.0, 241.0, 0.0, 27.0))
        worst = min(worst, 29.0 * 27.0 - occ)
    at_least("duct free cross-section between the caps, every 5 mm (mm2; spec 783, fill ~88 at the hub)", worst, 400.0)
    for s in "LR":
        cap = by["DUCT-CAP-%s" % s].solid.bounding_box()
        x_out = -16.0 if s == "L" else 1238.0
        chk("cap %s closes the duct end in the outer side-panel notch (x%g face, y214..241, z1..27)" % (s, x_out),
            ((cap[0] if s == "L" else cap[3]), cap[1], cap[4], cap[2], cap[5]), (x_out, 214.0, 241.0, 1.0, 27.0))
    cable_lanes = union([B_(-12.6, -4.1, 212.0, 241.0, 3.0, 7.5), B_(13.5, 22.5, 212.0, 241.0, 0.0, 6.0), B_(1206.1, 1212.5, 212.0, 241.0, 0.0, 6.0),
                         B_(124.75, 1117.0, 234.8, 238.8, 11.0, 15.0)]
                        + [B_(47 + 164.5 * k + 77.75, 47 + 164.5 * k + 90.25, 212.0, 221.8, 10.7, 18.3) for k in range(7)])
    true("cable lanes clear: headphone exit x-12.6..-4.1 z3..7.5, EL/ER leads z0..6, module plugs y..221.8, USB run y236.8 z13",
         total_vol(P, cable_lanes) < TOL, ", ".join(hits(P, cable_lanes)) or "clear")
    for s in "LR":
        bk = by["BRK2-%s" % s].solid
        so = by["POD-SOCKET-%s" % s].solid
        px, py = body.PIN_XY[s]
        chk("BRK2 %s pin D6 z14..24 at (x%.1f, y230) inside the socket, no touch, radial gap 0.25" % (s, px),
            (vol(bk, so), bk.min_gap(so, 5.0)), (0.0, 0.25), tol=0.03)
        true("BRK2 %s pin top 2.0 under the socket hole top (lifts 1.9 free, 2.1 hits)" % s,
             vol(bk.translate((0, 0, 1.9)), so) < TOL and vol(bk.translate((0, 0, 2.1)), so) > TOL)
        if s == "R":
            true("BRK2 R in the x slot: +-2.2 in x free (1221 mm pin spacing tolerance +-2.3)",
                 vol(bk.translate((2.2, 0, 0)), so) < TOL and vol(bk.translate((-2.2, 0, 0)), so) < TOL)
        else:
            true("BRK2 L in the round socket: 0.3 in x hits (locates the rear unit)", vol(bk.translate((0.3, 0, 0)), so) > TOL)
        got = sorted(round((by["BRK2-%s-GROM%d" % (s, i)].solid.bounding_box()[0] + by["BRK2-%s-GROM%d" % (s, i)].solid.bounding_box()[3]) / 2, 2) for i in (1, 2))
        chk("BRK2 %s grommets on the cheek M3 seats (L1 hardware)" % s, got, sorted(body.BRK_SEAT_X[s]))
        path = union([cyl_y(x, body.BRK_Z, 222.3, 260.0, 6.2) for x in body.BRK_SEAT_X[s]])
        true("BRK2 %s bolt heads / hex-key path free behind the grommets (D6.2 along y to y260)" % s, vol(bk, path) < TOL)
        bb = bk.bounding_box()
        chk("BRK2 %s plate z8 (above the headphone cables z7.5), pin top z24, y212.5..236.5" % s, (bb[2], bb[5], bb[1], bb[4]), (8.0, 24.0, 212.5, 236.5))
    chk("pin spacing (spec 1221; built 1217, R slot +-2.3 unchanged)", (body.PIN_XY["R"][0] - body.PIN_XY["L"][0],), (1217.0,))

    # ---------------- centre unit
    print("   --  centre unit (spec centre.*, plywood_cut_list, centre_contents)")
    cx0, cx1 = CE["x"]
    ix0, ix1 = CE["inner_x"]
    zlu, zlt = CE["walls"]["lid_z"]
    exp = {                                                             # back faces from the rules (YB / YBI at the built angle)
        "CU-PLY-BOTTOM": (ix0, 241.0, 5.0, ix1, YBI, 16.5),
        "CU-PLY-END-L": (cx0, 214.0, 5.0, CE["walls"]["end_L"][1], YBI, zlu),
        "CU-PLY-END-R": (CE["walls"]["end_R"][0], 214.0, 5.0, cx1, YBI, zlu),
        "CU-PLY-BACK": (cx0, YBI, 5.0, cx1, YB, zlu),
    }
    for l in CE["lids"]:
        exp[l["id"]] = (l["x"][0], 214.0, zlu, l["x"][1], YB, zlt)
    exp["CU-SCREENLID"] = (body.SLID_X[0], 214.0, zlu, body.SLID_X[1], YB, TS.AX_Z + TS.KNUCKLE["R"])   # 0.5 seam play; top = rev 3 hinge cheeks
    cc = dict(CC_B)                                                     # spec boxes; back-plate items moved with the back face
    for k in ("CU-PBHOLDER",):
        v = cc[k]
        exp[k] = (v[0], v[2], v[4], v[1], v[3], v[5])
    sh, b1 = cc["PR-HUBSHELF"], cc["PR-SHELFBRK-1"]
    exp["PR-HUBSHELF"] = (sh[0], sh[2], sh[4], sh[1], YBI, b1[5])     # shelf back strip + brackets reach the back ply (spec boxes: to y330 at 43 deg)
    for i in (1, 2):
        r = cc["PR-SEAMRAIL-%d" % i]
        exp["SEAM-POSTRAIL-%d" % i] = (r[0], r[2], cc["PR-SEAMPOST-%d" % i][4], r[1], YBI, r[5])   # rail to the back ply
    for k, e in exp.items():
        chk("%s bbox = spec (back y from the rules: y%.1f / %.1f)" % (k, YBI, YB), by[k].solid.bounding_box(), e)
    bp = cc["PR-BACKPLATE"]
    bpp = (by["PR-BACKPLATE"].solid ^ B_(390, 545, bp[2], bp[3] + 1, 0, 100)).bounding_box()
    chk("PR-BACKPLATE in the back-ply window x%.1f..%.1f y%.1f..%.1f z%.1f..%.2f" % (bp[0], bp[1], bp[2], bp[3], bp[4], bp[5]), bpp,
        (bp[0], bp[2], bp[4], bp[1], bp[3], bp[5]))
    true("PR-BACKPLATE box = back ply y%.1f..%.1f (rules)" % (YBI, YB), abs(bp[2] - YBI) < 1e-9 and abs(bp[3] - YB) < 1e-9)
    lg = (by["CU-SCREENLID"].solid.bounding_box()[0] - by["LID-L"].solid.bounding_box()[3], by["LID-R"].solid.bounding_box()[0] - by["CU-SCREENLID"].solid.bounding_box()[3])
    at_least("lid seams: play between LID-L | screen lid | LID-R (okoume cut +-0.5, spec 0)", min(lg), 0.5)
    rb = body.SLID_RIBBON
    true("screen lid: DSI ribbon / power hole x%.2f..%.2f y%.2f..%.2f open through the lid (rev 3 A-2)" % rb,
         vol(by["CU-SCREENLID"].solid, B_(rb[0] + 0.05, rb[1] - 0.05, rb[2] + 0.05, rb[3] - 0.05, zlu, zlt + 0.1)) < TOL)
    kt = max(p.solid.bounding_box()[5] for p in K)
    slp = (by["CU-SCREENLID"].solid ^ B_(505.0, 530.0, 230.0, 330.0, 0.0, 200.0)).bounding_box()[5]       # plate top beside the rev 3 hinges / feet
    chk("lids flush with the key tops z72.85 (L, screen-lid plate, R)", [by["LID-L"].solid.bounding_box()[5], slp, by["LID-R"].solid.bounding_box()[5]], (kt, kt, kt), tol=1e-3)
    for lid, sup in (("LID-L", ("CU-PLY-END-L", "CU-PLY-BACK", "SEAM-POSTRAIL-1", "PR-BACKPLATE")),
                     ("CU-SCREENLID", ("SEAM-POSTRAIL-1", "SEAM-POSTRAIL-2", "CU-PLY-BACK", "PR-BACKPLATE")),
                     ("LID-R", ("CU-PLY-END-R", "CU-PLY-BACK", "SEAM-POSTRAIL-2"))):
        dn = by[lid].solid.translate((0, 0, -0.05))
        true("%s rests on %s only (nothing on the modules)" % (lid, " / ".join(sup)),
             all(vol(dn, by[s_].solid) > 0.05 for s_ in sup) and not [i for i in hits([p for p in P if p.id != lid], dn) if i not in sup and not re.match(r"^(CU-MAG|CU-M3X10|SEAM-INS|TS-M3X20-HINGE)", i)],
             ", ".join(hits([p for p in P if p.id != lid], dn)))
    end_l = by["CU-PLY-END-L"].solid
    true("end walls: duct notch y214..241 z5..27 open (L and R)", vol(end_l, B_(259, 273, 214.0, 240.99, 5.0, 26.99)) < TOL
         and vol(by["CU-PLY-END-R"].solid, B_(949, 963, 214.0, 240.99, 5.0, 26.99)) < TOL)
    for s in "LR":
        wy, wz = body.WIRE_YZ[s]
        a, b_ = (cx0, ix0) if s == "L" else (ix1, cx1)
        ew = by["CU-PLY-END-%s" % s].solid
        pi_ = by["SPK%s-PLY-SIDEIN" % s].solid
        ey, ez = body.END_HOLE_YZ[s]
        true("end wall %s: XT30 hole D14 at y%.0f z%.1f (clip pocket axis, deviation from the D6 axis) open; pod wire hole D6 (y%.0f z%.0f) open"
             % (s, ey, ez, wy, wz), vol(ew, cyl_x(ey, ez, a - 1, b_ + 1, 13.8)) < TOL and vol(pi_, cyl_x(wy, wz, -100, 1300, 5.8)) < TOL)
        pf = body.SPK_X["L"][1] if s == "L" else body.SPK_X["R"][0]
        sg = -1.0 if s == "L" else 1.0
        dq, dd, t_ply = body.QS_HOLE[1], body.QS_HOLE[0], body.T
        open_ = all(vol(pi_, cyl_x(y_, z_, min(pf, pf + sg * (dq - 0.2)), max(pf, pf + sg * (dq - 0.2)), dd - 0.2)) < TOL for (y_, z_) in body.TS_YZ[s])
        floor_ = all(vol(pi_, cyl_x(y_, z_, min(pf + sg * (dq + 0.05), pf + sg * t_ply), max(pf + sg * (dq + 0.05), pf + sg * t_ply), dd))
                     > 0.98 * math.pi / 4 * dd ** 2 * (t_ply - dq - 0.05) for (y_, z_) in body.TS_YZ[s])
        under = t_ply - dq - body.QS_POINT
        true("pod %s L73 insert holes D%.1f x %.1f blind from the joint face (Norelem 07653-04 OD %.1f x %.0f: %.2f radial bite; maker min hole depth %.0f): "
             "%.1f of ply under the full-diameter bottom, %.1f under a %.1f drill point >= %.1f (sealed box); insert flush, %.0f free below it"
             % (s, dd, dq, body.INS[0], body.INS[2], (body.INS[0] - dd) / 2, body.QS_MIN_DEPTH, t_ply - dq, under, body.QS_POINT, body.QS_MIN_PLY,
                dq - body.INS[2]),
             open_ and floor_ and under >= body.QS_MIN_PLY - 1e-9 and body.INS[2] <= dq + 1e-9 and dq >= body.QS_MIN_DEPTH - 1e-9)
        xt = by["XT30-CLIP-%s" % s].solid
        pk = body.XT30_POCKET[s]
        pkb = B_(pk[0] + 0.05, pk[1] - 0.05, pk[2] + 0.05, pk[3] - 0.05, pk[4] + 0.05, pk[5] - 0.05)
        chk("XT30 clip %s pocket 12.4 x 10.6 x 5.6 empty (XT30U-F 12.4 x 10.2 x 5.2)" % s, (vol(xt, pkb), pk[1] - pk[0], pk[3] - pk[2], pk[5] - pk[4]),
            (0.0, 12.4, 10.6, 5.6), tol=0.011)
        mouth = pk[1] if s == "L" else pk[0]
        mbox = B_(mouth - 0.2, mouth + 10, pk[2] + 0.1, pk[3] - 0.1, pk[4] + 0.1, pk[5] - 0.1) if s == "L" else \
            B_(mouth - 10, mouth + 0.2, pk[2] + 0.1, pk[3] - 0.1, pk[4] + 0.1, pk[5] - 0.1)
        hole_ok = vol(xt, cyl_x(ey, ez, a - 1, b_ + 2.98, 13.8) if s == "L" else cyl_x(ey, ez, a - 2.98, b_ + 1, 13.8)) < TOL
        true("XT30 clip %s mouth open toward the centre (x%.1f), plate hole D14 coaxial with the end-wall hole, open" % (s, mouth),
             vol(xt, mbox) < TOL and hole_ok)
    bpl = by["PR-BACKPLATE"].solid
    hz = {k: tuple(v) for k, v in CE["back_plate_io"]["holes_xz"].items()}
    true("back plate: cable pass D12, USB-C mouth, KCD1 13.2 x 19.2 + 2 mm bezel recess, J501 D6 open at the spec x / z",
         vol(bpl, cyl_y(hz["cable_pass_D12"][0], hz["cable_pass_D12"][1], YBI - 0.1, YB + 0.1, 11.8)) < TOL
         and vol(bpl, cyl_y(hz["usb_c_pd_input_HUSB238"][0], hz["usb_c_pd_input_HUSB238"][1], YB - 1.95, YB + 0.1, 7.0)) < TOL
         and vol(bpl, B_(hz["rocker_KCD1_13.2x19.2"][0] - 6.5, hz["rocker_KCD1_13.2x19.2"][0] + 6.5, YBI, YB + 0.1, hz["rocker_KCD1_13.2x19.2"][1] - 9.5, hz["rocker_KCD1_13.2x19.2"][1] + 9.5)) < TOL
         and vol(bpl, B_(hz["rocker_KCD1_13.2x19.2"][0] - 7.5, hz["rocker_KCD1_13.2x19.2"][0] + 7.5, YB - 1.95, YB + 0.1, hz["rocker_KCD1_13.2x19.2"][1] - 10.5, hz["rocker_KCD1_13.2x19.2"][1] + 10.5)) < TOL
         and vol(bpl, cyl_y(hz["pedal_jack_J501_D6"][0], hz["pedal_jack_J501_D6"][1], YB - 2.1, YB + 0.1, 6.1)) < TOL)
    true("back plate: louvres x480..534 z18..46 open (6 slots of 3)", all(vol(bpl, B_(480.1, 533.9, YB - 2.1, YB + 0.1, z + 0.1, z + 2.9)) < TOL for (z, _) in body.BP_LOUV))
    pdt, j5 = cc["CU-E-PDTRIG"], cc["CU-E-J501"]
    true("back plate items ride on the plate: HUSB238 USB-C mouth y%.1f on the skin inner face y%.1f, J501 nose y%.1f flush with the outer face y%.1f"
         % (pdt[3], YB - body.BP_SKIN, j5[3], YB), abs(pdt[3] - (YB - body.BP_SKIN)) < 1e-6 and abs(j5[3] - YB) < 1e-6)
    jb = cc["CU-E-J501BOARD"]
    true("back plate: J501 board ledge top = board underside z%.1f, board box free" % jb[4],
         vol(bpl, B_(jb[0], jb[1], jb[2], jb[3], jb[4] - 0.3, jb[4])) > 10.0 and vol(bpl, B_(jb[0] + 0.1, jb[1] - 0.1, jb[2] + 0.1, jb[3] - 0.1, jb[4] + 0.01, jb[5])) < TOL)
    back = by["CU-PLY-BACK"].solid
    true("back ply window x397.5..538 z16.5..61.35 open, amp vents 8 x (4 x 15) open", vol(back, B_(397.6, 537.9, YBI, YB, 16.6, 61.4)) < TOL
         and all(vol(back, B_(a + 0.1, a + 3.9, YBI, YB, z0 + 0.1, z1 - 0.1)) < TOL for (a, z0, z1) in body.BACK_SLOTS))
    bot = by["CU-PLY-BOTTOM"].solid
    true("bottom ply intake slots open (6 under the buck, 8 under the Pi) and none under a board post",
         all(vol(bot, B_(a + 0.1, a + 3.9, y0 + 0.1, y1 - 0.1, 5, 16.5)) < TOL for (a, y0, y1) in body.BOT_SLOTS_BUCK + body.BOT_SLOTS_PI)
         and all(total_vol([p for p in P if p.id.startswith("CU-POST")], B_(a, a + 4.0, y0, y1, 16.4, 30)) < TOL for (a, y0, y1) in body.BOT_SLOTS_BUCK + body.BOT_SLOTS_PI))
    for i, (x, y) in enumerate(body.SLID_SCREWS):
        sl_ = by["CU-SCREENLID"].solid
        true("screen-lid screw %d (x%.0f y%.0f): D3.4 through, head seat D6.5 x 6, M3 insert L71 OD %.1f x %.0f melted into the D%.1f x %.1f rail hole%s"
             % (i + 1, x, y, body.INS3[0], body.INS3[2], body.INS3_HOLE, body.INS3[3], " over the post" if y < 300 else ""),
             vol(sl_, cyl_z(x, y, zlu - 0.1, zlt + 0.1, 3.3)) < TOL and vol(by["CU-M3X10-%d" % (i + 1)].solid, sl_) < TOL
             and abs(vol(by["SEAM-INS-%d" % (i + 1)].solid, by["SEAM-POSTRAIL-%d" % (1 if x < 611 else 2)].solid)
                     - math.pi / 4 * (body.INS3[0] ** 2 - body.INS3_HOLE ** 2) * body.INS3[2]) < 0.3
             and (y > 300 or vol(by["SEAM-POSTRAIL-%d" % (1 if x < 611 else 2)].solid, B_(x - 1, x + 1, y - 1, y + 1, 30, 50)) > 3.9))
    mags = [p for p in P if p.id.startswith("CU-MAG-")]
    pairs_ok = all(abs(by["CU-MAG-LID-%s" % p.id[-2:]].solid.bounding_box()[2] - p.solid.bounding_box()[5] - 0.4) < 1e-6 and
                   abs(by["CU-MAG-LID-%s" % p.id[-2:]].solid.bounding_box()[0] - p.solid.bounding_box()[0]) < 1e-6 for p in mags if "-PLY-" in p.id)
    true("LID-L / LID-R: 3 magnet pairs each (back-ply top edge 2, end-wall top edge 1), 0.4 apart, in pockets", len(mags) == 12 and pairs_ok)
    print("   ..  spec centre_contents boxes vs body solids (the electronics agent's envelopes):")
    walls_ids = ("CU-PBHOLDER", "PR-BACKPLATE", "PR-HUBSHELF", "PR-SHELFBRK-1", "PR-SHELFBRK-2", "PR-SEAMPOST-1", "PR-SEAMRAIL-1", "PR-SEAMPOST-2", "PR-SEAMRAIL-2")
    badcc, okcc = [], []
    for c in S["centre_contents"]:
        if c["id"] in walls_ids:
            continue
        v = cc[c["id"]]
        env = B_(v[0], v[1], v[2], v[3], v[4], v[5])
        for p in P:
            if bbox_overlap(p.solid.bounding_box(), env.bounding_box()):
                w_ = vol(p.solid, env)
                if w_ > TOL:
                    why = next((r[2] for r in INTENDED_CC if re.search(r[0], c["id"]) and re.search(r[1], p.id)), None)
                    (okcc if why else badcc).append((w_, c["id"], p.id, why))
    for w_, a, b_, why in okcc:
        print("       ok %8.2f  %-16s %-18s %s" % (w_, a, b_, why))
    for w_, a, b_, why in badcc:
        print("       !! %8.2f  %-16s %-18s" % (w_, a, b_))
    true("spec centre_contents (items + cable / plug zones) never cut by a body solid except the intended seats", not badcc,
         "%d intended, %d not" % (len(okcc), len(badcc)))
    fz = B_(ix0, ix1, 214.0, 241.0, 27.0, zlu)
    print("   ..  centre front zone y214..241 z27..61.35 holds: %s" % ", ".join(hits(P, fz)))

    # ---------------- joints, feet, pods lift off
    print("   --  joints pod <-> centre, feet")
    for s in "LR":
        a, b_ = (257.0, 260.0) if s == "L" else (962.0, 965.0)
        gap = B_(a + 0.001, b_ - 0.001, 150.0, 400.0, -1.0, 200.0)
        inside = hits(P, gap)
        true("joint gap %s x%.0f..%.0f holds only EVA strips and thumb-screw shanks (D15: no hard contact)" % (s, a, b_),
             all(re.match(r"^JOIN-(EVA|TS)-", i) for i in inside), ", ".join(inside))
        ev = [by["JOIN-EVA-%s%d" % (s, i)].solid.bounding_box() for i in (1, 2)]
        chk("EVA %s strips y243..339 z8..26 / y216..339 z48..70 at x%.0f..%.0f" % (s, a, b_), (ev[0][1], ev[0][4], ev[0][2], ev[0][5], ev[1][1], ev[1][4], ev[1][2], ev[1][5], ev[0][0], ev[0][3]),
            (243, 339, 8, 26, 216, 339, 48, 70, a, b_))
        for k, (y, z) in enumerate(body.TS_YZ[s]):
            t_ = by["JOIN-TS-%s%d" % (s, k + 1)].solid
            ins = by["JOIN-INS-%s%d" % (s, k + 1)].solid
            sv = by["JOIN-SLV-%s%d" % (s, k + 1)].solid
            tb_ = t_.bounding_box()
            pf = body.SPK_X["L"][1] if s == "L" else body.SPK_X["R"][0]
            bite = (pf - tb_[0]) if s == "L" else (tb_[3] - pf)
            ring = math.pi / 4 * (body.INS[0] ** 2 - body.QS_HOLE[0] ** 2) * body.INS[2]
            true("thumb screw %s%d (y%.0f z%.0f): M4x%.0f bites %.1f in the %.0f-long quick-sert (tip %.1f above the hole bottom), sleeve in the end-wall D8 hole, "
                 "head only on rubber; quick-sert D%.0f cuts %.2f into the D%.1f hole wall (%.1f mm3)"
                 % (s, k + 1, y, z, body.TS_LEN, bite, body.INS[2], body.QS_HOLE[1] - bite, body.INS[0], (body.INS[0] - body.QS_HOLE[0]) / 2, body.QS_HOLE[0], ring),
                 vol(t_, ins) > 10.0 and vol(sv, by["CU-PLY-END-%s" % s].solid) < TOL and abs(vol(ins, by["SPK%s-PLY-SIDEIN" % s].solid) - ring) < 1.0
                 and t_.min_gap(by["CU-PLY-END-%s" % s].solid, 3.0) > 0.05 and abs(bite - (body.TS_LEN - 16.0)) < 0.01 and bite < body.QS_HOLE[1] - 1.0)
            zz = cc["Z-TS-%s%d" % (s, k + 1)]
            hd = (t_ ^ B_(ix0 if s == "L" else ix1 - 30, ix0 + 30 if s == "L" else ix1, 150, 400, 0, 100)).bounding_box()
            true("thumb screw %s%d head inside the spec zone Z-TS-%s%d" % (s, k + 1, s, k + 1),
                 hd[0] >= zz[0] - 1e-6 and hd[3] <= zz[1] + 1e-6 and hd[1] >= zz[2] - 1e-6 and hd[4] <= zz[3] + 1e-6 and hd[2] >= zz[4] - 1e-6 and hd[5] <= zz[5] + 1e-6,
                 fmt(hd))
    ft = [p for p in P if p.id.startswith("FOOT-")]
    PODG = {}
    fp = body.foot_positions()
    spec_pos = sorted(tuple(float(c) for c in v) for k in ("pod_L", "centre", "pod_R") for v in S["feet"]["positions_xy"][k])
    pos = sorted(xy for _, xy, _ in fp)
    moved = [(sxy, xy) for _, xy, sxy in fp if sxy != xy]
    got = sorted((round((p.solid.bounding_box()[0] + p.solid.bounding_box()[3]) / 2, 2), round((p.solid.bounding_box()[1] + p.solid.bounding_box()[4]) / 2, 2)) for p in ft)
    chk("14 feet at the spec positions except the 4 outer pod feet x-2 / 1224 -> x6 / 1216 (all behind the duct, y>=248), z0..5",
        (len(ft), float(got == pos), float(sorted(sxy for _, _, sxy in fp) == spec_pos), len(moved), min(p.solid.bounding_box()[1] for p in ft),
         max(p.solid.bounding_box()[5] for p in ft)), (14, 1, 1, 4, 248, 5))
    for s in "LR":
        bp_ = by["SPK%s-PLY-BOTTOM" % s].solid.bounding_box()
        e_ = min(min(x - bp_[0], bp_[3] - x) for (_, (x, y), _) in fp if bp_[0] <= x <= bp_[3])
        at_least("pod %s feet: 8호 screw axis from the bottom-ply ends (spec x-2 / 1224 gave 2.5)" % s, e_, 10.0)
    # screws into the same ply: axes >= 8 apart and >= 5 from the ply edges (feet from below, PB holder / back-plate tabs from above)
    groups = {"CU-PLY-BOTTOM": [xy for g, xy, _ in fp if g == "가운데 유닛"] + list(body.PB_SCREWS) + [(sx, sy) for (_, _, sx, sy) in body.BP_TABS],
              "SPKL-PLY-BOTTOM": [xy for g, xy, _ in fp if g == "스피커 L"], "SPKR-PLY-BOTTOM": [xy for g, xy, _ in fp if g == "스피커 R"]}
    for pid, pts in groups.items():
        dmin = min(math.dist(a_, b2) for a_, b2 in itertools.combinations(pts, 2))
        pb_ = by[pid].solid.bounding_box()
        emin = min(min(x - pb_[0], pb_[3] - x, y - pb_[1], pb_[4] - y) for (x, y) in pts)
        true("%s: %d screw axes >= 8 apart (min %.1f) and >= 5 from the ply edges (min %.1f)" % (pid, len(pts), dmin, emin), dmin >= 8.0 and emin >= 5.0)
    # screw access (review 2026-10-01: the right back-plate tab screw sat under the J501 ledge, 9.5 free over its head): a straight
    # driver D6 x 80 along each screw axis from the head must not touch a solid. Assembly / service state: lids off; cables pushed aside
    # and the power bank out (not in the test); boards, hub, amp and every other rigid item in place. BRK2 bolts: before the pods go on.
    print("   --  screw access: straight driver D%.0f x %.0f along each screw axis from its head" % (body.DRIVER_D, body.DRIVER_L))
    lidfam = r"^(LID-|CU-SCREENLID$|CU-MAG-LID-|CU-M3X10-)"
    rigid_e = [e for e in (E or []) if e.note not in ("offdesk", "altview") and not re.match(r"^(C-|O\d-C-|EL-C-|ER-C-)", e.id)
               and e.id != "PB-E-BANK"]

    def shaft(pt, axis):
        x, y, z = pt
        a0, a1 = (0.02, body.DRIVER_L) if axis[1] > 0 else (-body.DRIVER_L, -0.02)
        return cyl_z(x, y, z + a0, z + a1, body.DRIVER_D) if axis[0] == "z" else cyl_y(x, z, y + a0, y + a1, body.DRIVER_D)
    centre_set = [p for p in P if not re.match(lidfam, p.id)] + rigid_e
    brk_set = list(K) + [p for p in P if p.id.startswith("BRK2-")] + rigid_e
    sh_ = cc["PR-HUBSHELF"]
    screw_groups = [
        ("back-plate tab screws (csk 8호 13, head flush z20.5)", [((sx, sy, 20.5), ("z", 1)) for (_, _, sx, sy) in body.BP_TABS], centre_set),
        ("power-bank holder screws (csk 8호 13, head flush z%.1f)" % (cc["CU-PBHOLDER"][4] + body.PB_FLOOR),
         [((x, y, cc["CU-PBHOLDER"][4] + body.PB_FLOOR), ("z", 1)) for (x, y) in body.PB_SCREWS], centre_set),
        ("hub-shelf bracket screws (D3 pan head D6 in the D6.5 seat, head top 2.1 in front of the seat bottom)",
         [(((b_[0] + b_[1]) / 2.0, b_[2] + 4.0 - 2.1, body.SHELF_SCREW_Z), ("y", -1)) for b_ in (cc["PR-SHELFBRK-1"], cc["PR-SHELFBRK-2"])], centre_set),
        ("BRK2 M3x16 bolts (hex key from +y, before the pods)",
         [((hxc, 212.0 + 8.6 + 1.65, body.BRK_Z), ("y", 1)) for s_ in "LR" for hxc in sorted(body.BRK_SEAT_X[s_])], brk_set),
    ]
    for lab, scr, parts_ in screw_groups:
        bad_ = []
        for pt, ax in scr:
            h_ = hits(parts_, shaft(pt, ax))
            if h_:
                bad_.append("(%.1f, %.1f, %.1f): %s" % (pt + (", ".join(h_),)))
        true("%s: D%.0f x %.0f driver path free at %s%s" % (lab, body.DRIVER_D, body.DRIVER_L, " · ".join("(%.1f, %.1f)" % ((pt[0], pt[1]) if ax[0] == "z" else (pt[0], pt[2]))
                                                                                          for pt, ax in scr), "" if E is not None else " (electronics not loaded)"),
             not bad_, "; ".join(bad_) or "clear")
    true("hub-shelf screw heads (D6 on z%.0f) clear the shelf top through the relief groove (%.0f x %.1f)" % (body.SHELF_SCREW_Z, body.SHELF_GROOVE[0], body.SHELF_GROOVE[1]),
         all(vol(by["PR-HUBSHELF"].solid, cyl_y((b_[0] + b_[1]) / 2.0, body.SHELF_SCREW_Z, sh_[2] - 1.0, b_[2] + 4.0 - 0.01, 6.0)) < TOL
             for b_ in (cc["PR-SHELFBRK-1"], cc["PR-SHELFBRK-2"])))
    for s in "LR":
        podg = [p for p in P if p.id.startswith("SPK%s-" % s) or p.id in ("DUCT-CAP-%s" % s, "POD-SOCKET-%s" % s)
                or p.id.startswith("JOIN-INS-%s" % s) or p.id.startswith("JOIN-EVA-%s" % s) or re.match(r"^CABLE-CLIP-%s\d$" % s, p.id)]
        fx = (lambda b: (b[0] + b[3]) / 2)
        podg += [p for p in ft if (fx(p.solid.bounding_box()) < 257 if s == "L" else fx(p.solid.bounding_box()) > 965)]
        rest = [p for p in P if p not in podg and not p.id.startswith("JOIN-TS-")]
        worst_ = 0.0
        for dz in (0.5, 2.0, 5.0, 10.0, 20.0, 40.0, 50.0):
            for p in podg:
                m = p.solid.translate((0, 0, dz))
                worst_ = max(worst_, total_vol(rest, m) + total_vol(K, m))
        true("pod %s lifts straight up off the pins once the 2 thumb screws are out (0.5..50 mm, body parts only)" % s, worst_ < TOL, "%.3f" % worst_)
        PODG[s] = podg

    # ---------------- pod service with the sealed pigtail (review 2026-10-01): XT30U-F out through the coaxial tunnel, tether
    print("   --  pod service: XT30U-F slides out of its clip through the plate + end-wall D14 tunnel; pod lift 10, slide 15 outboard, lift to 60")
    if E is None:
        true("pod service sequence (needs electronics.build())", False, "electronics.build() failed")
    else:
        import electronics as EL
        byE = {e.id: e for e in E}
        LIFT, SLIDE = 10.0, 15.0
        for s in "LR":
            sg = -1.0 if s == "L" else 1.0                                   # outboard
            podg = PODG[s]
            rest = [p for p in P if p not in podg and not p.id.startswith("JOIN-TS-")]
            F = byE["C-XT30F-%s" % s].solid
            fb = F.bounding_box()
            wall = body.CU_X[0] if s == "L" else body.CU_X[1]                # end-wall outer (joint) face 260 / 962
            d_out = (fb[3] - (wall - 0.05)) if s == "L" else ((wall + 0.05) - fb[0])
            worst_f = max(total_vol(rest, F.translate((sg * d, 0, 0))) for d in list(np.arange(0.0, d_out, 0.5)) + [d_out])
            true("pod %s: XT30U-F slides straight from its clip through the plate + end-wall hole to the joint face (%.1f mm, no body part hit)"
                 % (s, d_out), worst_f < TOL, "%.3f mm3" % worst_f)
            worst_p = 0.0
            moves = [(0, 0, dz) for dz in (0.5, 2.0, 5.0, 7.5, LIFT)] + [(sg * dx, 0, LIFT) for dx in (2.5, 5.0, 7.5, 10.0, 12.5, SLIDE)] \
                + [(sg * SLIDE, 0, dz) for dz in (20.0, 30.0, 45.0, 60.0)]
            for mv in moves:
                for p in podg:
                    m = p.solid.translate(mv)
                    worst_p = max(worst_p, total_vol(rest, m) + total_vol(K, m))
            true("pod %s: lifts %.0f off the pins, slides %.0f outboard, lifts to 60 without touching the centre unit, bracket or key action"
                 % (s, LIFT, SLIDE), worst_p < TOL, "%.3f mm3" % worst_p)
            Fout = F.translate((sg * d_out, 0, 0))
            podm = [p.solid.translate((sg * SLIDE, 0, LIFT)) for p in podg]
            true("pod %s: XT30U-F out of the end wall sits in the widened gap, clear of the moved pod" % s,
                 sum(vol(Fout, m) for m in podm) < TOL and total_vol(rest, Fout) < TOL)
            wy, wz = body.WIRE_YZ[s]
            face = body.SPK_X["L"][1] if s == "L" else body.SPK_X["R"][0]
            fback = (fb[0] if s == "L" else fb[3], (fb[1] + fb[4]) / 2.0, (fb[2] + fb[5]) / 2.0)
            d_need = math.dist((face + sg * SLIDE, wy, wz + LIFT), fback)
            l_out = EL.LENGTHS.get("PIG-OUT-" + s, 0.0)
            at_least("pod %s tether: pigtail outside the pod %.1f >= straight %.1f (pod lifted %.0f, slid %.0f, F still in its clip) + 10 bend allowance"
                     % (s, l_out, d_need, LIFT, SLIDE), l_out - d_need, 10.0)

    # ---------------- pareto_by_angle reproduced by the one-constant geometry
    print("   --  pareto_by_angle (spec) vs body.PodGeom(angle)")
    for row in S["pareto_by_angle"]["rows"]:
        g = body.PodGeom(row["baffle_deg"])
        vL = poly_area(g.cavity()) * 250.0 / 1e6
        chk("PodGeom(%.1f): centre y z, top z, back y, gross L, flange clearance" % row["baffle_deg"],
            (g.C[0], g.C[1], g.z_top, g.y_back, vL, g.sightline_clear(g.D(-52.5, 7.0))),
            (row["driver_centre_yz"][0], row["driver_centre_yz"][1], row["pod_top_z"], row["back_y"], row["gross_L_at_250"], row["flange_corner_clearance_mm"]),
            tol=0.011)
    print("   ..  volumes (gross / net L): " + ", ".join("%s %.3f / %.3f" % (s, v[0], v[1]) for s, v in vols.items()))



# ------------------------------------------------------------------ (4) R31 touchscreen rev 3

R31_INFO = {}          # measured numbers (make_readme / the report read them back through check_body.r31_measure())


def run_checks_r31(P, by, K, C, E=None):
    """R31 touchscreen rev 3 (touchscreen/rev3/design/CAD_SPEC_rev3.md A..G, numbers.json points / checks) probed on the solids."""
    chk, at_least, at_most, true = C.chk, C.at_least, C.at_most, C.true
    B_ = box
    NP = TS.POINTS
    NC = TS.CHECKS
    lid = by["CU-SCREENLID"].solid
    zlu, zlt = body.Z_LIDU, body.Z_LID
    zp = zlt - body.SLID_PLATE

    def full(m, b):
        return abs(vol(m, b) - b.volume()) < 1e-3 * max(1.0, b.volume())

    # ---------------- A. screen lid (rev 3 additions on the CAD L2 lid)
    print("   --  A. CU screen lid: rev 3 additions + rib rule (CAD L2 lid x%.1f~%.1f y214~%.1f)" % (body.SLID_X[0], body.SLID_X[1], body.YB))
    for s in ("left", "right"):
        n0, n1 = TS.hinge_x(s, "near_cheek")
        f0, f1 = TS.hinge_x(s, "far_cheek")
        e0, e1 = TS.hinge_x(s, "ear_slot")
        a0, a1 = min(n0, f0), max(n1, f1)
        chk("A-1 %s hinge block x%.1f~%.1f = near %.1f~%.1f + ear slot %.1f~%.1f (8.4) + far %.1f~%.1f: cheeks solid round the axis, slot open above the "
            "heel block, nothing outside" % (s, a0, a1, n0, n1, e0, e1, f0, f1),
            (vol(lid, B_(a0 - 1.0, a0 - 0.01, 220, 233, zlt + 0.01, 90)), float(full(lid, B_(n0 + 0.1, n1 - 0.1, TS.AX_Y - 4.5, TS.AX_Y - 2.0, TS.AX_Z - 1, TS.AX_Z + 1))),
             vol(lid, B_(e0 + 0.01, e1 - 0.01, 210, 240, TS.HEEL_BLOCK["z"][1] + 0.01, 95)), float(full(lid, B_(f0 + 0.1, f1 - 0.1, TS.AX_Y + 2.0, TS.AX_Y + 4.5, TS.AX_Z - 1, TS.AX_Z + 1))),
             vol(lid, B_(a1 + 0.01, a1 + 1.0, 220, 233, zlt + 0.01, 90))), (0, 1, 0, 1, 0))
        kp = TS.KNUCKLE
        chk("A-1 %s cheek profile: top z%.2f (R%.1f, nothing above), z72.85 base y%.2f~%.2f, at the axis y%.2f~%.2f" % (s, TS.AX_Z + kp["R"], kp["R"],
            kp["base_y"][0], kp["base_y"][1], kp["at_axis_y"][0], kp["at_axis_y"][1]),
            (vol(lid, B_(n0, n1, 200, 250, TS.AX_Z + kp["R"] + 0.01, 100)), float(vol(lid, B_(n0, n1, TS.AX_Y - 0.2, TS.AX_Y + 0.2, TS.AX_Z + kp["R"] - 0.1, TS.AX_Z + kp["R"] - 0.02)) > 0),
             float(full(lid, B_(n0 + 0.1, n1 - 0.1, kp["base_y"][0] + 0.1, kp["base_y"][1] - 0.1, zlt, zlt + 0.1))),
             vol(lid, B_(n0, n1, kp["base_y"][0] - 1.0, kp["base_y"][0] - 0.01, zlt + 0.01, zlt + 0.3)),
             float(full(lid, B_(n0 + 0.1, n1 - 0.1, kp["at_axis_y"][0] + 0.05, TS.AX_Y - 1.9, TS.AX_Z - 0.1, TS.AX_Z - 0.02))),
             vol(lid, B_(n0, n1, kp["at_axis_y"][1] + 0.1, 240, TS.AX_Z + 0.01, TS.AX_Z + 0.3))), (0, 1, 1, 0, 1, 0))
        chk("A-1 %s axis y%.2f z%.2f: near cheek D3.3 open, far cheek D2.5 open (M3x20 taps it), >= 1.5 wall round the far hole" % (s, TS.AX_Y, TS.AX_Z),
            (vol(lid, cyl_x(TS.AX_Y, TS.AX_Z, n0 - 0.1, n1 + 0.1, 3.2)), vol(lid, cyl_x(TS.AX_Y, TS.AX_Z, f0 - 0.1, f1 + 0.1, 2.4)),
             float(full(lid, diff(cyl_x(TS.AX_Y, TS.AX_Z, f0 + 0.01, f1 - 0.01, 5.5), [cyl_x(TS.AX_Y, TS.AX_Z, f0, f1, 3.6)])))), (0, 0, 1))
        hb = TS.HEEL_BLOCK
        chk("A-1 %s heel stop block in the ear slot y%.2f~%.2f z72.85~%.2f (lid top + 3.5), slot floor z72.85 behind it" % (s, hb["y"][0], hb["y"][1], hb["z"][1]),
            (float(full(lid, B_(e0 + 0.05, e1 - 0.05, hb["y"][0] + 0.05, hb["y"][1] - 0.05, zlt - 0.1, hb["z"][1] - 0.01))),
             vol(lid, B_(e0 + 0.05, e1 - 0.05, hb["y"][1] + 0.01, 236, zlt + 0.01, hb["z"][1]))), (1, 0))
        chk("A-1/A-9 %s hinge block filled down to the print bed z%.2f (x%.1f~%.1f y%.2f~%.2f)" % (s, zlu, a0, a1, kp["base_y"][0], kp["base_y"][1]),
            (float(full(lid, B_(a0 + 0.05, a1 - 0.05, kp["base_y"][0] + 0.05, kp["base_y"][1] - 0.05, zlu + 0.01, zp + 0.01))),), (1,))
    rx0, rx1, ry0, ry1 = body.SLID_RIBBON
    hw = body.SLID_HOLE_WALL
    chk("A-2 ribbon / power hole x%.2f~%.2f y%.2f~%.2f open through z%.2f~%.2f; wall 2 filled to z%.2f; R1 on the y edges top and bottom"
        % (rx0, rx1, ry0, ry1, zlu, zlt, zlu),
        (vol(lid, B_(rx0 + 0.01, rx1 - 0.01, ry0 + 0.01, ry1 - 0.01, zlu - 0.1, zlt + 0.1)),
         float(full(lid, diff(B_(rx0 - hw + 0.05, rx1 + hw - 0.05, ry0 - hw + 0.05, ry1 + hw - 0.05, zlu + 0.01, zp), [B_(rx0 - 0.05, rx1 + 0.05, ry0 - 1.1, ry1 + 1.1, zlu, zp + 1)]))),
         round(1.0 - vol(lid, B_(640, 650, ry1, ry1 + 1.0, zlt - 1.0, zlt)) / 10.0, 2), round(1.0 - vol(lid, B_(640, 650, ry0 - 1.0, ry0, zlu, zlu + 1.0)) / 10.0, 2)),
        (0, 1, 0.21, 0.21), tol=0.02)
    pk = TS.POCKET
    t30 = math.tan(math.radians(30.0))
    zr = lambda y: zlt - (y - pk["ramp_front_y"]) * t30                                           # noqa: E731
    chk("A-3 leg pocket x%.0f~%.0f: 30 deg ramp from (y%.2f, z72.85) to (y%.2f, z%.2f), floor z%.2f open above, back wall y%.1f (C%.1f)"
        % (pk["x"][0], pk["x"][1], pk["ramp_front_y"], pk["ramp_end_y"], pk["bottom_z"], pk["bottom_z"], pk["back_wall_y"], TS.LG["pocket_edge_C"]),
        tuple(float(full(lid, B_(605, 617, y - 0.05, y + 0.05, zr(y) - 2.0, zr(y) - 0.1))) + float(vol(lid, B_(605, 617, y - 0.05, y + 0.05, zr(y) + 0.1, zlt + 1)) == 0)
              for y in (291.5, 293.5, 295.5))
        + (vol(lid, B_(pk["x"][0] + 0.01, pk["x"][1] - 0.01, pk["ramp_end_y"] + 0.05, pk["back_wall_y"] - 0.01, pk["bottom_z"] + 0.01, zlt + 1)),
           float(full(lid, B_(pk["x"][0] + 0.1, pk["x"][1] - 0.1, pk["ramp_end_y"] + 0.1, pk["back_wall_y"] - 0.1, zlu + 0.01, pk["bottom_z"] - 0.01))),
           float(full(lid, B_(pk["x"][0] + 0.1, pk["x"][1] - 0.1, pk["back_wall_y"] + 0.01, pk["back_wall_y"] + 2.0, pk["bottom_z"], zlt - 0.6)))),
        (2, 2, 2, 0, 1, 1))
    pb = pk["block"]
    chk("A-3 pocket block x%.0f~%.0f y%.2f~%.2f filled to z%.2f (under the floor)" % (pb["x"][0], pb["x"][1], pb["y"][0], pb["y"][1], zlu),
        (float(full(lid, B_(pb["x"][0] + 0.05, pb["x"][1] - 0.05, pb["y"][0] + 0.05, pb["y"][1] - 0.05, zlu + 0.01, pk["bottom_z"] - 0.01))),), (1,))
    ff = TS.FOLD_FEET
    chk("A-4 4 fold feet 16 x 16 x 5.5 (z72.85~78.35) + rear lips y322.05~324.05 to z80.35, 0.5 gap foot <-> lip",
        tuple(float(full(lid, B_(f_["x"][0] + 0.01, f_["x"][1] - 0.01, f_["y"][0] + 0.01, f_["y"][1] - 0.01, zlt, f_["z"][1] - 0.01))) for f_ in ff)
        + tuple(float(full(lid, B_(f_["x"][0] + 0.01, f_["x"][1] - 0.01, f_["lip"]["y"][0] + 0.01, f_["lip"]["y"][1] - 0.01, zlt, f_["lip"]["z"][1] - 0.01)))
                for f_ in ff if f_["rear"])
        + tuple(vol(lid, B_(f_["x"][0], f_["x"][1], f_["y"][1] + 0.01, f_["lip"]["y"][0] - 0.01, zlt + 0.01, 85)) for f_ in ff if f_["rear"]),
        (1, 1, 1, 1, 1, 1, 0, 0))
    cp = TS.CLIP["pad"]
    pins = TS.CLIP["pins"]
    chk("A-5 clip pad x%.2f~%.2f y%.2f~%.2f filled z%.2f~%.2f; 2 blind pin holes D%.1f x %.0f from below at %s, solid above"
        % (cp["x"][0], cp["x"][1], cp["y"][0], cp["y"][1], zlu, zp, TS.CLIP["pin_hole_d"], TS.CLIP["pin_hole_depth"], " · ".join("(%.2f, %.2f)" % tuple(q) for q in pins)),
        (float(full(lid, diff(B_(cp["x"][0] + 0.05, cp["x"][1] - 0.05, cp["y"][0] + 0.05, cp["y"][1] - 0.05, zlu + 0.01, zp), [cyl_z(x, y, zlu, zp, 3.3) for (x, y) in pins]))),)
        + tuple(vol(lid, cyl_z(x, y, zlu - 0.1, zlu + TS.CLIP["pin_hole_depth"] - 0.01, TS.CLIP["pin_hole_d"] - 0.1)) for (x, y) in pins)
        + tuple(float(full(lid, cyl_z(x, y, zlu + TS.CLIP["pin_hole_depth"] + 0.01, zp, 3.0))) for (x, y) in pins), (1, 0, 0, 1, 1))
    chk("A-6 8 vent slots 34 x 4 (x564~598 / 624~658, y300~325, pitch 7) open through the plate z%.2f~%.2f" % (zp, zlt),
        (sum(vol(lid, B_(a + 0.05, b - 0.05, c + 0.05, d - 0.05, zp + 0.01, zlt + 0.1)) for (a, b, c, d) in body.SLID_SLOTS), float(len(body.SLID_SLOTS))), (0, 8))
    ls = TS.LID_SCREW
    for i, (x, y) in enumerate(body.SLID_SCREWS):
        scr = by["CU-M3X10-%d" % (i + 1)].solid.bounding_box()
        ins = by["SEAM-INS-%d" % (i + 1)].solid.bounding_box()
        chk("A-7 lid screw %d (x%.0f y%.0f): D%.1f open, counterbore D%.1f x %.1f (head seat z%.2f), %.1f lid under the head, head top below the lid top; "
            "M3x10 tip z%.2f = %.1f above the insert-hole bottom z%.2f, %.1f in the insert (insert %.1f)"
            % (i + 1, x, y, ls["hole_d"], ls["cbore_d"], ls["cbore_depth"], ls["head_seat_z"], ls["under_head"], ls["tip_z"], ls["tip_z"] - (zlu - body.INS3[3]),
               zlu - body.INS3[3], ls["insert_engage"], body.INS3[2]),
            (vol(lid, cyl_z(x, y, zlu - 0.1, zlt + 0.1, ls["hole_d"] - 0.1)), vol(lid, cyl_z(x, y, ls["head_seat_z"] + 0.01, zlt + 0.1, ls["cbore_d"] - 0.1)),
             float(full(lid, diff(cyl_z(x, y, zlu + 0.01, ls["head_seat_z"] - 0.01, ls["cbore_d"] - 0.2), [cyl_z(x, y, zlu, zlt, ls["hole_d"] + 0.2)]))),
             scr[2], float(scr[5] <= zlt - 1.0), scr[2] - (zlu - body.INS3[3]), ins[5] - scr[2]),
            (0, 0, 1, ls["tip_z"], 1, 0.5, ls["insert_engage"]))
    at6 = ls["lid_t"] - (10.0 - body.INS3[2])
    true("A-7 counterbore rule: depth = lid thickness at the screw %.1f - (10 - insert %.1f) = %.1f = built %.1f (the old 6.0 would put the tip on the hole "
         "bottom z%.2f: 0 clearance)" % (ls["lid_t"], body.INS3[2], at6, body.SLID_CB[1], zlu - body.INS3[3]), abs(at6 - body.SLID_CB[1]) < 1e-9)
    # rib rule (spec A header): every rib box is solid except where it crosses the ribbon hole; the x651 rib stops at the hole wall
    rib_boxes = [(rx_ - 1.0, rx_ + 1.0, body.Y0 + body.SLID_WALL, body.YB - body.SLID_WALL) for rx_ in body.SLID_RIB_X] + \
                [(body.SLID_X[0] + body.SLID_WALL, body.SLID_X[1] - body.SLID_WALL, ry_ - 1.0, ry_ + 1.0) for ry_ in body.SLID_RIB_Y]
    hole_cut = B_(rx0 - 1.05, rx1 + 1.05, ry0 - 1.05, ry1 + 1.05, zlu - 1, zlt + 1)
    pk_cut = prism_x(body.pocket_cut_poly(), pk["x"][0], pk["x"][1])
    rib_missing = []
    for (a, b, c, d) in rib_boxes:
        rb_ = diff(B_(a + 0.02, b - 0.02, c + 0.02, d - 0.02, zlu + 0.02, zp - 0.02), [hole_cut, pk_cut])
        miss = rb_.volume() - vol(lid, rb_)
        if miss > 0.01:
            rib_missing.append("x%.0f~%.0f y%.0f~%.0f %.2f mm3" % (a, b, c, d, miss))
    x651 = [vol(lid, B_(650.05, 651.95, y0_, y1_, zlu + 0.05, zp - 0.05)) for (y0_, y1_) in ((217.5, 226.5), (ry0 + 0.01, ry1 - 0.01), (236.6, 248.5))]
    true("A rib rule: ribs x%s / y%s solid everywhere (merged into the hinge blocks, hole wall, clip pad, pocket block), none inside the hole; x651 stops "
         "at the hole wall (rib y217~226.55 %.1f / in the hole %.2f / at the clip pad %.1f mm3); clip pin holes %.2f / %.2f from the x651 rib"
         % ("/".join("%.0f" % v for v in body.SLID_RIB_X), "/".join("%.0f" % v for v in body.SLID_RIB_Y), x651[0], x651[1], x651[2],
            min(abs(px - 651.0) - 1.0 - TS.CLIP["pin_hole_d"] / 2 for (px, py) in pins), max(abs(px - 651.0) - 1.0 - TS.CLIP["pin_hole_d"] / 2 for (px, py) in pins)),
         not rib_missing and x651[1] < TOL and x651[0] > 0.98 * 1.9 * 9.0 * 8.4 and x651[2] > 0.98 * 1.9 * 11.9 * 8.4, "; ".join(rib_missing))
    q = by["CU-SCREENLID"].print_solid.bounding_box()
    chk("A-9 lid printed rib face down (z%.2f on the bed): bed 219 x %.1f x 25.5 (top z86.85 = cheek top)" % (zlu, body.YB - body.Y0),
        (q[3] - q[0], q[4] - q[1], q[5] - q[2], float(vol(by["CU-SCREENLID"].print_solid, B_(q[0], q[3], q[1], q[4], 0, 0.3)) > 0.3 * 0.3 * 219 * 128.5 * 0.3)),
        (219.0, body.YB - body.Y0, 25.5, 1))
    true("A-8 / D14: no magnet in or under the screen lid, cradle or leg (x501..721)", not [p.id for p in P if "MAG" in p.id and 501 <= p.solid.bounding_box()[0] <= 721])

    # ---------------- C. cradle (local frame + placed)
    print("   --  C. cradle (xr / u / w frame)")
    crl = body.cradle_local()
    X0, X1 = TS.CR_XR
    U0, U1 = TS.CR_U
    W0, W1 = TS.CR_W
    PLI, PLO = TS.PLATE_W
    IX = TS.WALLS["side_inner_xr"]
    cb_ = crl.bounding_box()
    bod = (crl ^ B_(X0 - 1, X1 + 1, U0, U1 + 1, W0 - 1, W1)).bounding_box()
    chk("C-1 body xr+-85.35 (170.7), u-2.5~103.5 (106.0), w-1~16 (17.0); ears to u%.2f, clip to w%.2f" % (TS.EAR["min_u"], TS.LCLIP["back_w"]),
        (bod[0], bod[3], bod[1], bod[4], bod[2], bod[5], cb_[1], cb_[5]), (X0, X1, U0, U1, W0, W1, TS.EAR["min_u"], TS.LCLIP["back_w"]))
    chk("C-1 walls: glass pocket xr+-83.35 u0~101.5 w-1~8 empty (glass on the bottom wall u0, top gap 0.5, side gaps 0.3); walls full",
        (vol(crl, B_(-IX + 0.01, IX - 0.01, 0.01, TS.WALLS["top_u"][0] - 0.01, W0 - 0.1, TS.BOSS["face_w"] - 0.01)),
         float(full(crl, B_(-85.3, -83.4, 1, 100, -0.95, 15.95))), float(full(crl, B_(-80, -70, -2.45, -0.05, -0.95, 13.9))),
         float(full(crl, B_(-80, -70, 101.55, 103.45, -0.95, 15.95)))), (0, 1, 1, 1))
    chk("C-2 back plate w%.1f~%.1f solid, 0.4 behind the screen's back emboss (w%.1f)" % (PLI, PLO, TS.BODY_T + TS.SC["emboss"]["h"]),
        (float(full(crl, B_(-50, -30, 40, 60, PLI + 0.01, PLO - 0.01))), PLI - (TS.BODY_T + TS.SC["emboss"]["h"])), (1, 0.4))
    bo = TS.BOSS
    for xr in bo["xr"]:
        for u in bo["u"]:
            chk("C-3 boss (xr%+.0f, u%.1f): D%.0f w%.0f~%.0f, hole D%.1f open, counterbore D%.1f from w%.0f open, filled to the side wall"
                % (xr, u, bo["d"], bo["w"][0], bo["w"][1], bo["hole_d"], bo["cbore_d"], bo["seat_w"]),
                (vol(crl, cyl_z(xr, u, bo["face_w"] - 0.5, W1 + 0.1, bo["hole_d"] - 0.1)), vol(crl, cyl_z(xr, u, bo["seat_w"] + 0.01, W1 + 0.1, bo["cbore_d"] - 0.1)),
                 float(full(crl, diff(cyl_z(xr, u, bo["face_w"] + 0.01, bo["seat_w"] - 0.01, bo["d"] - 0.1), [cyl_z(xr, u, 7, 12, bo["hole_d"] + 1.4)]))),
                 float(full(crl, B_(xr + 1.5, IX - 0.05, u - 3.9, u + 3.9, bo["face_w"] + 0.01, PLI - 0.01) if xr > 0 else
                                 B_(-IX + 0.05, xr - 1.5, u - 3.9, u + 3.9, bo["face_w"] + 0.01, PLI - 0.01)))), (0, 0, 1, 1))
            cap = body.BOSS_CB_CAP
            rr = bo["cbore_d"] / 2.0
            corner = math.hypot(cap, rr * math.sqrt(2.0) - cap)          # flat-roof corner distance from the axis
            chk("C-3 boss (xr%+.0f, u%.1f): counterbore flat-roof corners %.3f from the axis -> wall %.2f >= 0.80"
                % (xr, u, corner, bo["d"] / 2 - corner), (round(bo["d"] / 2 - corner, 2) >= 0.80,), (True,))
            chk("C-3 boss (xr%+.0f, u%.1f): counterbore teardrop roof cut flat at %.1f from the axis -> >= %.1f wall over it (-u = up in print), roof region open"
                % (xr, u, cap, bo["d"] / 2 - cap),
                (float(full(crl, B_(xr - 0.6, xr + 0.6, u - bo["d"] / 2 + 0.04, u - cap - 0.01, bo["seat_w"] + 0.01, W1 - 0.01))),
                 vol(crl, B_(xr - 0.6, xr + 0.6, u - cap + 0.01, u - bo["cbore_d"] / 2 + 0.01, bo["seat_w"] + 0.01, W1 + 0.1))), (1, 0))
    nt, gr, wn, hp = TS.NOTCH, TS.GROOVE, TS.INSP, TS.HOLD_PAD
    chk("C-1 bottom-wall notch xr48~66 u-2.5~0 w-1~8 through; C-8 open groove xr25.75~44.95 u-2.5~3 w8~16; C-5 window xr15.5~45 u33~69 through the plate; "
        "C-7 hold pad xr26.75~39.45 u8~16 w8.6~10.5",
        (vol(crl, B_(nt["xr"][0] + 0.01, nt["xr"][1] - 0.01, U0 - 0.1, 0.1, W0 - 0.1, nt["w"][1] - 0.01)),
         float(full(crl, B_(nt["xr"][0] + 0.1, nt["xr"][1] - 0.1, U0 + 0.1, -0.1, nt["w"][1] + 0.1, 13.0))),
         vol(crl, B_(gr["xr"][0] + 0.01, gr["xr"][1] - 0.01, U0 - 0.1, gr["u"][1] - 0.01, gr["w"][0] + 0.01, W1 + 0.1)),
         vol(crl, B_(wn["xr"][0] + 0.01, wn["xr"][1] - 0.01, wn["u"][0] + 0.01, wn["u"][1] - 0.01, PLI - 0.1, PLO + 0.1)),
         float(full(crl, B_(hp["xr"][0] + 0.01, hp["xr"][1] - 0.01, hp["u"][0] + 0.01, hp["u"][1] - 0.01, hp["w"][0] + 0.01, PLI)))), (0, 1, 0, 0, 1))
    ch = TS.CHANNEL
    chk("C-9 cross ribs u24 / u80 (2 thick, w13~16), cut at the leg channel xr+-7.3; channel walls xr+-5.3~7.3 to the top wall",
        tuple(float(full(crl, B_(-80, -8, u - 0.95, u + 0.95, PLO + 0.01, W1 - 0.01))) + float(full(crl, B_(8, 80, u - 0.95, u + 0.95, PLO + 0.01, W1 - 0.01)))
              for u in TS.CROSS_RIBS_U)
        + (vol(crl, B_(-5.0, 5.0, 20, 26, PLO + 0.01, W1 + 1)), float(full(crl, B_(-7.25, -5.35, 40, 100, PLO + 0.01, W1 - 0.01)))), (2, 2, 0, 1))
    chk("C-9 window rib ring 1.8 outside the window (2 thick); 4 back pads 16 x 16 w13~16 with the 45 deg chamfer on the +u face (lands 16 x 13 when folded)",
        (float(full(crl, B_(wn["xr"][0] - 3.75, wn["xr"][0] - 1.85, 40, 60, PLO + 0.01, W1 - 0.01))),
         vol(crl, B_(wn["xr"][0] - 1.75, wn["xr"][0] - 0.05, 40, 60, PLO + 0.01, W1 + 1)))
        + tuple(float(full(crl, B_(pd["xr"][0] + 0.05, pd["xr"][1] - 0.05, pd["u"][0] + 0.05, pd["u"][1] - body.PAD_CH - 0.05, PLO + 0.01, W1 - 0.01))) for pd in TS.PADS),
        (1, 0, 1, 1, 1, 1))
    ax_head = cyl_x(TS.LEG_PIVOT_UW[0], TS.LEG_PIVOT_UW[1], TS.LG["axle"]["L"] * 0 + TS.CLEVIS["near"][0] - TS.LG["axle"]["L"] - TS.LG["axle"]["head_h"],
                    TS.CLEVIS["near"][0], TS.LG["axle"]["head_d"])
    ribs_only = crl.trim_by_plane((0, 0, 1), PLO + 0.01).trim_by_plane((-1, 0, 0), -(TS.CLEVIS["near"][0] - 0.01))
    gpath = ax_head.min_gap(ribs_only, 5.0)
    gplate = ax_head.min_gap(crl.trim_by_plane((-1, 0, 0), -(TS.CLEVIS["near"][0] - 0.01)), 5.0)
    R31_INFO["axle_path_gap"] = gpath
    at_least("C-9/C-13 leg-axle head + insertion path from -x (D5.7, xr%.2f~%.2f at u30 w16.5) clear of every back rib / pad / boss (spec >= 2.0; "
             "to the back plate %.2f)" % (TS.CLEVIS["near"][0] - TS.LG["axle"]["L"] - TS.LG["axle"]["head_h"], TS.CLEVIS["near"][0], gplate), gpath, NC["axle_path_gap"])
    for s in ("left", "right"):
        e0, e1 = TS.HG[s]["ear"]
        ear = crl ^ B_(e0 - 0.1, e1 + 0.1, -30, U0 - 0.001, -5, 30)
        eb = ear.bounding_box()
        chk("C-12 %s ear xr%.1f~%.1f (8.0): outline = numbers.json profile_uw (u%.2f~-2.5, w%.2f~%.2f), axis (u-9, w13) D3.3 open, hub >= R4.2"
            % (s, e0, e1, TS.EAR["min_u"], min(p_[1] for p_ in TS.EAR_PROFILE), max(p_[1] for p_ in TS.EAR_PROFILE)),
            (eb[0], eb[3], eb[1], eb[2], eb[5], vol(crl, cyl_x(TS.AX_U, TS.AX_W, e0 - 0.1, e1 + 0.1, 3.2)),
             float(full(crl, diff(cyl_x(TS.AX_U, TS.AX_W, e0 + 0.01, e1 - 0.01, 8.3), [cyl_x(TS.AX_U, TS.AX_W, e0, e1, 4.8)])))),
            (e0, e1, TS.EAR["min_u"], min(p_[1] for p_ in TS.EAR_PROFILE), max(p_[1] for p_ in TS.EAR_PROFILE), 0, 1), tol=0.02)
    pu, pw = TS.LEG_PIVOT_UW
    cl = TS.LCLIP
    chk("C-13 leg hanger: near xr-9.3~-5.3 D3.3, far xr5.3~11.3 D2.5, leg gap xr-5~5 free (0.3 each side), R3.8 round (u30, w16.5); C-15 clip catch 0.8 at "
        "w%.2f~%.2f over the stowed leg (w13.5~19.5)" % (cl["catch_from_w"], cl["back_w"]),
        (vol(crl, cyl_x(pu, pw, TS.CLEVIS["near"][0] - 0.1, TS.CLEVIS["near"][1] + 0.1, 3.2)), vol(crl, cyl_x(pu, pw, TS.CLEVIS["far"][0] - 0.1, TS.CLEVIS["far"][1] + 0.1, 2.4)),
         vol(crl, B_(-5.0, 5.0, 10.0, 101.0, PLO + 0.5, cl["catch_from_w"] - 0.01)),
         float(full(crl, B_(-5.25, -4.55, cl["u"][0] + 0.05, cl["u"][1] - 0.05, cl["catch_from_w"] + 0.01, cl["back_w"] - 0.01))),
         float(full(crl, B_(4.55, 5.25, cl["u"][0] + 0.05, cl["u"][1] - 0.05, cl["catch_from_w"] + 0.01, cl["back_w"] - 0.01)))), (0, 0, 0, 1, 1))
    k45 = pu + pw + TS.CLEVIS["R"] * math.sqrt(2.0)                    # u + w on the 45 deg underside tangent (spec C-13, t03 B-B u38.87 at w13)
    cpoly = body.clevis_poly()
    nmax = 0.0
    for i_ in range(len(cpoly)):
        (a0_, b0_), (a1_, b1_) = cpoly[i_], cpoly[(i_ + 1) % len(cpoly)]
        L_ = math.hypot(a1_ - a0_, b1_ - b0_)
        if L_ > 1e-9 and min(b0_, b1_) >= PLO - 0.02:                  # edges in the free part above the plate back w13 (CCW: outward n = (dw, -du) / L)
            nmax = max(nmax, (b1_ - b0_) / L_)
    hang = [((crl ^ B_(x0_, x1_, 25, 45, wz, wz + 0.1)).bounding_box()[4]) for (x0_, x1_) in ((-9.2, -7.4), (7.4, 11.2)) for wz in (13.2, 18.5)]
    chk("C-13 leg-hanger cheeks: underside (+u = down in print) at 45 deg - end u%.2f at w13 (spec 38.87), on the line u + w = %.3f at w13.2 / w18.5 "
        "(near, far), max down-facing normal n_u %.4f <= 0.7072 (support-free)" % (k45 - PLO, k45, nmax),
        (k45 - PLO, hang[0] + 13.2, hang[1] + 18.5, hang[2] + 13.2, hang[3] + 18.5, float(nmax <= 0.7072)), (38.87, k45, k45, k45, k45, 1), tol=0.05)
    ch2 = body.CR_C2
    chk("C-10 bottom-back edge (u-2.5, w16) chamfer C%.1f (numbers C%.0f; corner region empty, ear attachment w8~13 untouched)" % (ch2, TS.CHAMFER_C2),
        (vol(crl, B_(-80, 80, U0 - 0.01, U0 + 0.6, W1 - 0.6, W1 + 0.1)), vol(crl, prism_x([(U0 - 0.01, W1 - ch2 + 0.05), (U0 - 0.01, W1 + 0.1), (U0 + ch2 - 0.05, W1 + 0.1)], -84, 84)),
         float(full(crl, B_(-80, 20, U0 + 0.05, U0 + 0.5, W1 - ch2 - 0.4, W1 - ch2 - 0.05)))), (0.0, 0.0, 1))
    ps = by["TS-CRADLE"].print_solid.bounding_box()
    chk("C-17 cradle printed on the top edge (u103.5 face on the bed): height %.2f, bed 170.7 x %.2f" % (TS.CR["print_height"], ps[4] - ps[1]),
        (ps[3] - ps[0], ps[5] - ps[2], float(max(ps[3] - ps[0], ps[4] - ps[1], ps[5] - ps[2]) <= 256)), (170.7, TS.CR["print_height"], 1))

    # ---------------- C-16 / hinge: poses, heel contact, 22..90 sweep
    print("   --  C-16 hinge: 25 / 22 / 90 deg poses, heel contact, swing 22..90 against the lid, the Pi, cables, pods, key modules")
    import electronics as EL
    cr = by["TS-CRADLE"].solid
    c25 = cr.bounding_box()
    front = cr.trim_by_plane((0, -1, 0), -(c25[1] + 0.02)).bounding_box()
    rear = cr.trim_by_plane((0, 1, 0), c25[4] - 0.02).bounding_box()
    U = NP["use"]
    chk("C-16 25 deg: front-most (y%.2f, z%.2f), highest z%.2f, rear-most y%.2f (numbers points.use)" % (U["cr_bot_front"][0], U["cr_bot_front"][1], U["cr_top_front"][1], U["cr_top_rib"][0]),
        (c25[1], (front[2] + front[5]) / 2.0, c25[5], c25[4]), (U["cr_bot_front"][0], U["cr_bot_front"][1], U["cr_top_front"][1], U["cr_top_rib"][0]), tol=0.03)
    c22 = TS.place(crl, TS.TILT_HEEL)
    b22 = c22.bounding_box()
    Hh = NP["heel"]
    chk("C-16 22 deg (heel stop): front-most y%.2f, highest z%.2f; heel on the stop block z%.2f (no overlap, touching)" % (Hh["cr_bot_front"][0], Hh["cr_top_front"][1], TS.HEEL_BLOCK["z"][1]),
        (b22[1], b22[5], vol(c22, lid), c22.min_gap(lid, 1.0)), (Hh["cr_bot_front"][0], Hh["cr_top_front"][1], 0.0, 0.0), tol=0.03)
    slot_lid = union([lid ^ B_(TS.hinge_x(s, "ear_slot")[0] + 0.001, TS.hinge_x(s, "ear_slot")[1] - 0.001, 200, 250, 50, 100) for s in ("left", "right")])
    cheek_lid = union([lid ^ B_(TS.hinge_x(s, ck)[0], TS.hinge_x(s, ck)[1], 200, 250, zlt - 0.001, 100) for s in ("left", "right") for ck in ("near_cheek", "far_cheek")])
    ears_l = crl ^ union([B_(TS.HG[s]["ear"][0] - 0.01, TS.HG[s]["ear"][1] + 0.01, -30, 10, -5, 30) for s in ("left", "right")])
    body_l = crl ^ union([B_(TS.HG[s]["far_cheek"][0] - 0.5, TS.HG[s]["near_cheek"][1] + 0.5, -30, 30, -5, 30) if s == "right" else
                          B_(TS.HG[s]["near_cheek"][0] - 0.5, TS.HG[s]["far_cheek"][1] + 0.5, -30, 30, -5, 30) for s in ("left", "right")])
    body_l = body_l - union([B_(TS.HG[s]["ear"][0] - 0.01, TS.HG[s]["ear"][1] + 0.01, -30, U0 + 0.1, -5, 30) for s in ("left", "right")])
    sweep_ear, sweep_cheek = [], []
    for th in [22.0 + 0.5 * i for i in range(137)]:
        sweep_ear.append((th, TS.place(ears_l, th).min_gap(slot_lid, 2.0)))
        sweep_cheek.append((th, TS.place(body_l, th).min_gap(cheek_lid, 2.0)))
    g22 = sweep_ear[0][1]
    g2590 = min(g for th, g in sweep_ear if th >= 25.0)
    th_min = min((g, th) for th, g in sweep_ear if th >= 25.0)[1]
    gch = min(sweep_cheek, key=lambda r: r[1])
    R31_INFO.update(ear_gap_22=g22, ear_gap_25_90=g2590, ear_gap_at=th_min, cheek_gap=gch[1], cheek_gap_at=gch[0])
    chk("C-12 ear outline vs stop block + slot floor: %.2f at 22 deg (contact), >= %.2f at 25..90 deg (min %.3f at %.1f deg; numbers %.2f at %.0f)"
        % (g22, NC["ear_block_gap_25_90"], g2590, th_min, NC["ear_block_gap_25_90"], TS.EAR["check"]["at_deg"]), (g22, g2590), (0.0, NC["ear_block_gap_25_90"]), tol=0.011)
    at_least("C-10 cradle bottom (C%.1f corner) vs hinge cheeks over 22..90 deg: min gap at %.1f deg (spec %.2f; C%.0f gave %.3f at 90, = W1 3D)"
             % (body.CR_C2, gch[0], TS.CR["rib_relief_at_cheeks"]["gap_after"], TS.CHAMFER_C2, body.C2_GAP_AT_C2), gch[1],
             TS.CR["rib_relief_at_cheeks"]["gap_after"])
    chk("C-12 heel gap at 25 deg (cradle lowest point over the stop block)", (TS.place(ears_l, 25.0).min_gap(slot_lid, 2.0),), (NC["heel_gap_at_25"],), tol=0.011)
    # whole moving group (cradle + window cover + screen + stowed leg + leg axle + M2.5) vs every static part, 22..90 deg every 1 deg
    lgl = body.leg_capsule((pu, pw), (pu + TS.LEG_L, pw), TS.LG["xr"][0], TS.LG["xr"][1], hole_at=(pu, pw))
    axl = body.m3_button_x(pu, pw, TS.CLEVIS["near"][0], TS.LG["axle"]["L"], +1)
    m25 = union([union([cyl_z(xr, u, bo["seat_w"], bo["seat_w"] + body.M25_HEAD[1], body.M25_HEAD[0]), cyl_z(xr, u, bo["seat_w"] - body.M25_LEN, bo["seat_w"], 2.5)])
                 for xr in bo["xr"] for u in bo["u"]])
    mov_l = union([crl, body.cover_local(), EL.screen_local(), lgl, axl, m25])
    moving_ids = {"TS-CRADLE", "TS-WINCOVER", "TS-LEG", "TS-M3X20-LEG", "TS-E-SCREEN"} | {"TS-M25-%d" % k for k in range(1, 5)}
    statics = [p for p in P + list(K) + list(E or []) if p.note not in ("offdesk", "altview") and p.id not in moving_ids and not p.id.startswith("TS-C-")]
    near = statics                                                      # every static part; the per-angle bbox test does the culling
    reach = set()
    keep = B_(-20, 1240, -10, TS.KEEP_Y, TS.KEEP_Z, 400)
    worst, kvol, miny = [], 0.0, 1e9
    for th in [22.0 + 1.0 * i for i in range(69)]:
        m = TS.place(mov_l, th)
        mb = m.bounding_box()
        for p in near:
            if bbox_overlap(mb, p.solid.bounding_box()):
                reach.add(p.id)
                v = vol(m, p.solid)
                if v > TOL:
                    worst.append("%s %.2f at %.0f" % (p.id, v, th))
        kvol += vol(m, keep)
        miny = min(miny, mb[1])
    R31_INFO.update(sweep_min_y=miny, sweep_hits=worst)
    true("C-16 swing 22..90 deg (1 deg steps): cradle + cover + screen + stowed leg + axle + M2.5 never cut a static part (%d body / key action / "
         "electronics parts tested - lid, Pi, cables, pods, modules; %d inside the swept box: %s)" % (len(near), len(reach), ", ".join(sorted(reach))),
         not worst, "; ".join(worst[:6]))
    chk("C-16 nothing of the touchscreen over the modules (y<=%.0f with z>=%.2f) at any angle 22..90; front-most y over the swing (numbers sweep_min_y %.2f)"
        % (TS.KEEP_Y, TS.KEEP_Z, TS.N["sweep_min_y"]), (kvol, miny), (0.0, TS.N["sweep_min_y"]), tol=0.03)
    # folded
    crf = by["TS-CRADLE-FOLD"].solid
    fb = (crf ^ B_(TS.XC - 86, TS.XC + 86, TS.N["fold"]["y"][0] - 0.001, 400, TS.N["fold"]["rib_plane_z"] - 0.001, 200)).bounding_box()
    fz_all = crf.bounding_box()
    chk("C-16 folded 90 deg: body y%.2f~%.2f, z%.2f~%.2f (rib plane on the fold feet, glass up); rear margin to the lid back y%.1f %.2f (spec %.2f at y341.5); "
        "top %.2f under the speaker top z%.2f" % (TS.N["fold"]["y"][0], TS.N["fold"]["y"][1], TS.N["fold"]["rib_plane_z"], TS.N["fold"]["top_z"], body.YB,
                                                   body.YB - fb[4], NC["fold_rear_margin"], body.SPK_ZT - fz_all[5], body.SPK_ZT),
        (fb[1], fb[4], fb[2], fb[5], vol(crf, lid), float(vol(crf.translate((0, 0, -0.05)), lid) > 0.05), float(body.YB - fb[4] >= 2.0), float(fz_all[5] <= body.SPK_ZT - 20)),
        (TS.N["fold"]["y"][0], TS.N["fold"]["y"][1], TS.N["fold"]["rib_plane_z"], TS.N["fold"]["top_z"], 0, 1, 1, 1))
    lips = union([lid ^ B_(f_["x"][0], f_["x"][1], f_["lip"]["y"][0], f_["lip"]["y"][1], zlt, 90) for f_ in ff if f_["rear"]])
    at_least("C-11/A-4 folded pads (45 deg chamfer) vs the rear-foot lips y322.05: gap", crf.min_gap(lips, 3.0), 0.5)
    lgf = by["TS-LEG-FOLD"].solid
    clip_f = crf ^ B_(TS.XC - 9, TS.XC + 9, 320, 330, 60, 80)
    clev_f = crf ^ B_(TS.XC - 9.4, TS.XC + 11.4, 260, 272, 60, 80)
    chk("D folded: leg z%.2f~%.2f (%.2f over the lid), hanger z%.2f (+%.2f), clip catch z%.2f (+%.2f) over the lid z72.85 (numbers %.2f / %.2f / %.2f)"
        % (TS.LG["fold_leg_z"][0], TS.LG["fold_leg_z"][1], TS.LG["fold_leg_z"][0] - zlt, TS.LG["fold_clevis_zmin"], NC["fold_leg_clear_lid"], TS.LG["fold_clip_zmin"],
           NC["fold_clip_clear_lid"], TS.LG["fold_leg_z"][0], TS.LG["fold_clevis_zmin"], TS.LG["fold_clip_zmin"]),
        (lgf.bounding_box()[2], lgf.bounding_box()[5], clev_f.bounding_box()[2], clip_f.bounding_box()[2], vol(lgf, crf), vol(lgf, lid)),
        (TS.LG["fold_leg_z"][0], TS.LG["fold_leg_z"][1], TS.LG["fold_clevis_zmin"], TS.LG["fold_clip_zmin"], 0, 0), tol=0.02)

    # ---------------- D. leg
    print("   --  D. support leg")
    leg = by["TS-LEG"].solid
    A = TS.LEG_AX_YZ
    lb = leg.bounding_box()
    chk("D leg axis (y%.2f, z%.2f), foot (y%.2f, z%.2f), 67, %.2f deg below horizontal" % (TS.LG["pivot_yz"][0], TS.LG["pivot_yz"][1], TS.LEG_TIP_YZ[0], TS.LEG_TIP_YZ[1], TS.LG["angle_deg"]),
        (A[0], A[1], TS.LEG_LEN_MODEL, TS.LEG_ANGLE), (TS.LG["pivot_yz"][0], TS.LG["pivot_yz"][1], TS.LG["length"], TS.LG["angle_deg"]), tol=0.02)
    chk("D leg x606~616, foot R3 on the pocket floor z%.2f and the back wall y%.1f (no overlap, touching), axis hole D3.3 open"
        % (TS.POCKET["bottom_z"], TS.POCKET["back_wall_y"]),
        (lb[0], lb[3], lb[2], lb[4], vol(leg, lid), float(vol(leg.translate((0, 0, -0.05)), lid) > 0.005), float(vol(leg.translate((0, 0.05, 0)), lid) > 0.005),
         vol(leg, cyl_x(A[0], A[1], 605, 617, 3.2))), (606, 616, TS.POCKET["bottom_z"], TS.POCKET["back_wall_y"], 0, 1, 1, 0), tol=0.02)
    ramp = lid ^ B_(600, 622, 280, TS.POCKET["ramp_end_y"] - 0.2, 60, 80)
    gr_ = leg.min_gap(ramp, 2.0)
    R31_INFO["leg_ramp_gap"] = gr_
    at_least("A-3 leg (R3 capsule) vs the 30 deg ramp at 25 deg (spec >= %.1f, rule y290.43)" % TS.POCKET["ramp_min_clear"], gr_, TS.POCKET["ramp_min_clear"] - 0.01)
    chk("D leg vs cradle no overlap; axle M3x20 taps the far hanger cheek (thread overlap > 5 mm3)",
        (vol(leg, cr), float(vol(by["TS-M3X20-LEG"].solid, cr) > 5.0), vol(by["TS-M3X20-LEG"].solid, leg)), (0, 1, 0))
    swing = {}
    for th_ in (TS.TILT_HEEL, TS.TILT_USE):
        pv = TS.pt(pu, pw, th_)
        res_ = []
        for k in range(0, 81):
            ph = math.radians(20.0 + 0.25 * k)
            tip = (pv[0] + TS.LEG_L * math.cos(ph), pv[1] - TS.LEG_L * math.sin(ph))
            res_.append((20.0 + 0.25 * k, vol(body.leg_capsule(pv, tip, 606, 616), lid)))
        first = next((a_ for a_, v_ in res_ if v_ > TOL), None)
        swing[th_] = (pv, first, max(v_ for a_, v_ in res_ if a_ <= (first or 40) + 2.5))
    R31_INFO["swing"] = swing
    chk("D deploy at 22 deg (pivot y%.2f z%.2f, numbers %.1f / %.1f): the leg swings down to %.2f deg with no lid contact before the ramp (first touch %.2f, numbers %.2f)"
        % (swing[22.0][0][0], swing[22.0][0][1], TS.LG["pivot22_yz"][0], TS.LG["pivot22_yz"][1], 40.0, swing[22.0][1] or 0, -TS.LG["swing"]["at_22"]["first_contact_deg"]),
        (swing[22.0][0][0], swing[22.0][0][1], float((swing[22.0][1] or 99) >= -TS.LG["swing"]["at_22"]["first_contact_deg"] - 0.3)),
        (TS.LG["pivot22_yz"][0], TS.LG["pivot22_yz"][1], 1), tol=0.02)
    true("D at 25 deg the same swing hits the back-wall edge first (%.2f deg, numbers %.2f, overlap %.1f mm3) -> procedure: deploy / stow at the 22 deg heel stop"
         % (swing[25.0][1] or 0, -TS.LG["swing"]["at_25"]["first_contact_deg"], swing[25.0][2]),
         swing[25.0][1] is not None and abs(swing[25.0][1] + TS.LG["swing"]["at_25"]["first_contact_deg"]) < 0.6)

    # ---------------- E. small parts, screws
    print("   --  E. small parts and screws")
    cov = by["TS-WINCOVER"].solid
    cvl = body.cover_local()
    chk("E-1 window cover: no overlap with the cradle; flange on the plate back w13 (shift -0.05 w overlaps); plug 0.2 inside the window; bumps in the grooves",
        (vol(cov, cr), float(vol(TS.place(cvl.translate((0, 0, -0.05)), 25.0), cr) > 0.05),
         (cvl ^ B_(-100, 100, -100, 200, PLI - 0.1, PLO - 0.01)).min_gap(crl ^ B_(10, 50, 28, 75, PLI - 0.1, PLO), 0.5),
         vol(cvl, crl)), (0, 1, 0.2, 0), tol=0.011)
    tx0, tx1 = body.COVER_TABS
    bt_, bh_, sl_ = body.COVER_BEAM
    ubf, utf = TS.INSP["u"][0] + TS.INSP["cover"]["plug_under"], TS.INSP["u"][1] - TS.INSP["cover"]["plug_under"]
    beam_ok = []
    for (b0_, b1_, r0_, r1_) in ((ubf, ubf + bt_, ubf + bt_, ubf + 2.0), (utf - bt_, utf, utf - 2.0, utf - bt_)):
        beam_ok += [float(full(cvl, B_(tx0 + 0.02, tx1 - 0.02, b0_ + 0.02, b1_ - 0.02, PLI + 0.02, PLI + bh_ - 0.02))),
                    vol(cvl, B_(tx0 + 0.01, tx1 + 0.99, r0_ + 0.01, r1_ - 0.01, PLI - 0.1, PLO - 0.01)),            # behind the beam
                    vol(cvl, B_(tx1 + 0.01, tx1 + 0.99, ubf - 0.5 if b0_ < 50 else utf - 2.0, ubf + 2.0 if b0_ < 50 else utf + 0.5, PLI - 0.1, PLO - 0.01)),
                    vol(cvl, B_(tx0 + 0.01, tx1 - 0.01, b0_ + 0.01, b1_ - 0.01, PLI + bh_ + 0.01, PLO - 0.01))]   # slot under the flange
    chk("E-1 cover snap beams along xr (root xr%.0f, free end xr%.0f, %.1f x %.1f, slot %.1f under the flange) free on 3 sides; interference %.2f -> strain %.2f %% (<= 2.5)"
        % (tx0, tx1, bt_, bh_, sl_, body.COVER_SNAP[0], body.COVER_SNAP[1] * 100),
        tuple(beam_ok) + (float(body.COVER_SNAP[1] <= 0.025),), (1, 0, 0, 0, 1, 0, 0, 0, 1))
    rc = by["TS-RCLIP"].solid
    rb = rc.bounding_box()
    chk("E-2 ribbon clip 30 x 12 x 3 at z%.2f~%.2f, pins D3 x 4.5 in the D3.1 x 5 holes (no overlap, tip 0.5 + clamp 0.3 short), clamp gap 0.3 under the pad (= FFC)"
        % (TS.CLIP["clip_z"][0], TS.CLIP["clip_z"][1]),
        (rb[3] - rb[0], rb[4] - rb[1], rb[2], rb[5], vol(rc, lid), zlu + TS.CLIP["pin_hole_depth"] - rb[5], zlu - TS.CLIP["clip_z"][1]),
        (30.0, 12.0, TS.CLIP["clip_z"][0], TS.CLIP["clip_z"][1] + TS.CLIP["pin_len"], 0, TS.CLIP["pin_hole_depth"] - TS.CLIP["pin_len"] + TS.RIBBON["ffc_t"],
         TS.RIBBON["ffc_t"]))
    gv = TS.CLIP["wire_groove"]
    chk("E-2 clip top power-wire groove x%.1f~%.1f x %.1f deep along y open; 0.4 from the ribbon edge x%.2f, %.2f from the pin edge"
        % (gv["x"][0], gv["x"][1], gv["depth"], TS.CLIP["ribbon_edge_x"], TS.CLIP["pin_edge_x"] - gv["x"][1]),
        (vol(rc, B_(gv["x"][0] + 0.01, gv["x"][1] - 0.01, rb[1] - 0.1, rb[4] + 0.1, TS.CLIP["clip_z"][1] - gv["depth"] + 0.01, TS.CLIP["clip_z"][1] + 0.1)),
         gv["x"][0] - TS.CLIP["ribbon_edge_x"]), (0, 0.4))
    sc = by["TS-SCREENCOVER"]
    sb = sc.solid.bounding_box()
    chk("E-3 optional screen cover 173 x 108 x 3 on the folded cradle rim z%.2f (altview), no overlap with the folded cradle" % TS.N["fold"]["top_z"],
        (sb[3] - sb[0], sb[4] - sb[1], sb[2], sb[5] - sb[2], float(sc.note == "altview"), vol(sc.solid, crf)), (173, 108, TS.N["fold"]["top_z"], 3, 1, 0))
    for s in ("left", "right"):
        hx = by["TS-M3X20-HINGE-%s" % s[0].upper()].solid
        f0, f1 = TS.hinge_x(s, "far_cheek")
        th_ = (hx ^ B_(f0 - 0.001, f1 + 0.001, 200, 250, 60, 100)).bounding_box()
        chk("A-1 %s M3x20 axle from the %s side: bite in the far cheek %.1f (spec 7.6), no overlap with the ear / cradle" % (s, TS.HG[s]["screw_from"], th_[3] - th_[0]),
            (th_[3] - th_[0], vol(hx, cr), float(vol(hx, lid) > 5)), (7.6, 0, 1), tol=0.02)
    eng = [vol(by["TS-M25-%d" % k].solid, cr) for k in range(1, 5)]
    chk("C-3 M2.5x6 heads seated in the D5.5 counterbores (w11), no overlap with the cradle", (max(eng),), (0.0,))
    # ---------------- F / G. assembly rules
    ts = [p for p in P if p.id.startswith("TS-")]
    alt = sorted(p.id for p in ts if p.note == "altview")
    chk("F folded state = separate 'altview' parts in group '터치스크린 (접은 상태, 별도 보기)' (excluded from the one-file assembly / 3MF / GLB)",
        (float(alt == ["TS-CRADLE-FOLD", "TS-LEG-FOLD", "TS-SCREENCOVER", "TS-WINCOVER-FOLD"]), float(all(by[i].group == "터치스크린 (접은 상태, 별도 보기)" for i in alt))), (1, 1))
    chk("G printed touchscreen parts in 07_터치스크린 (cradle, leg, cover, clip, screen cover), the lid in 05_본체출력물",
        (float(all(p.print_folder == "07_터치스크린" for p in ts if p.kind == "print")), float(by["CU-SCREENLID"].print_folder == "05_본체출력물"),
         sum(1 for p in ts if p.kind == "print" and p.print_solid is not None)), (1, 1, 5))
    use = [p for p in ts if p.note != "altview"]
    kv = sum(vol(p.solid, keep) for p in use)
    ub = union_bb(use)
    chk("G keep-out: no touchscreen part (use pose) at y<=%.0f with z>=%.2f; plan inside the lid x%.1f~%.1f (margin %.2f / %.2f)"
        % (TS.KEEP_Y, TS.KEEP_Z, body.SLID_X[0], body.SLID_X[1], ub[0] - body.SLID_X[0], body.SLID_X[1] - ub[3]),
        (kv, float(ub[0] >= body.SLID_X[0] and ub[3] <= body.SLID_X[1])), (0, 1))
    print("   ..  R31 measured: %s" % ", ".join("%s %s" % (k, ("%.3f" % v) if isinstance(v, float) else str(v)[:60]) for k, v in R31_INFO.items()))


if __name__ == "__main__":
    sys.exit(main())
