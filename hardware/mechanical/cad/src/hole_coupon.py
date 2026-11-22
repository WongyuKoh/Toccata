"""A18 (2026-11-16) hole test coupon for the D4 lever rod, printed before the module is printed again.

The user printed one octave and the D4 rod would not go into the D3.9 printed bores (they were meant to be drilled D4.0).
A18 prints the lever hub D4.3 and the fin-boss bores D4.5 so the rod goes in undrilled; this coupon checks that on the
user's own printer in ~15 min: two small prints, holes D4.1 .. D5.0, sizes engraved (41 = D4.1).
  세로구멍 : a plate printed flat, holes along the print z - like the lever hub (the carrier prints on its side)
  가로구멍 : a wall printed upright, teardrop holes along y (apex up) - like the cage fin bosses (the cage prints on its back)
Pick the smallest hole the rod slides through by hand (hub: turns freely; fin boss: slides through), tell the CAD
(FEAT hub_bore_print / fin_bore_print in keyaction.py) if it differs from 4.3 / 4.5.
A19 (2026-11-16, no drill at all): a third coupon checks the crush-rib holes (no_drill.py) - bore = old radius + 1 mm,
three ribs whose tips sit near the old drilled size; the rod / pin shaves the tips:
  리브구멍 : a wall (printed upright) with three horizontal D5.9 holes, rib tips D3.8 / 3.9 / 4.0 (T1a K stub; 3.9 = CAD),
             and three vertical D3.95 holes 8 deep, rib tips D1.85 / 1.95 / 2.05 (balance pin; 1.95 = CAD).
A20 (2026-11-22, the steel weight did not go into the carrier): a fourth coupon is the A20 steel pocket's opening -
  무게추칸 : a frame printed flat (like the carrier body, which prints on its -x wall), window 40.5 x 19.5 with the two rear
             crush ribs (0.3, to 40.2) - the cut steel block (9 x 19 x 40) must go through by hand.
"""
import io

from cadlib import box, cyl_z, diff, teardrop_y, text_xy, to_bed, union, orient, rot_x
from no_drill import A19, ribbed_hole_z, ribbed_teardrop_y
from a20_fix import A20

SIZES = (4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 5.0)
PITCH = 8.5
MARK = {4.3: "허브", 4.5: "레버틀"}


def flat():
    """plate 74 x 16 x 3.8 (the hub's width), vertical holes; labels engraved on the top."""
    n = len(SIZES)
    L = PITCH * n + 6.0
    m = box(0, L, 0, 16.0, 0, 3.8)
    cuts = []
    for i, d in enumerate(SIZES):
        x = 3.0 + PITCH * (i + 0.5)
        cuts.append(cyl_z(x, 10.5, -1, 5, d, 48))
        cuts.append(text_xy("%d" % round(d * 10), 3.2, 1.0, x, 3.0, 3.4, "center", "baseline", heavy=True))
    return diff(m, cuts)


def upright():
    """wall 74 x 6 x 14 standing on its long edge, teardrop holes along y (apex up); labels engraved on the +y face."""
    n = len(SIZES)
    L = PITCH * n + 6.0
    m = box(0, L, 0, 6.0, 0, 14.0)
    cuts = []
    for i, d in enumerate(SIZES):
        x = 3.0 + PITCH * (i + 0.5)
        cuts.append(teardrop_y(x, 9.0, -1, 7, d))
        # label on the +y face: text in xy turned up onto the face (rot_x 90), 0.6 deep
        t = text_xy("%d" % round(d * 10), 3.0, 1.0, 0, 0, 0, "center", "baseline", rot=180, heavy=True)
        cuts.append(orient(t, rot_x(-90)).translate((x, 5.4, 2.2)))       # reads upright from +y, 0.6 deep
    return diff(m, cuts)


RIB_ROD = (3.8, 3.9, 4.0)
RIB_PIN = (1.85, 1.95, 2.05)


def ribbed():
    """A19 coupon 48 x 16 x 14: front wall (y0..6) with three horizontal ribbed D5.9 holes along y (T1a K-stub kind),
    rear block (y6..16) with three vertical ribbed D3.95 holes 8 deep (balance-pin kind); labels engraved on the top."""
    m = box(0, 48.0, 0, 16.0, 0, 14.0)
    cuts, ribs = [], []
    for i, t in enumerate(RIB_ROD):
        x = 8.0 + 16.0 * i
        cu, ri = ribbed_teardrop_y(x, 7.0, -1.0, 6.5, A19["k_bore"], t, A19["rib_base"], A19["rib_tip"])
        cuts.append(cu)
        ribs.append(ri)
    for i, t in enumerate(RIB_PIN):
        x = 8.0 + 16.0 * i
        cuts.append(ribbed_hole_z(x, 11.5, 6.0, 14.01, A19["pin_bore"], t, A19["pin_rib_base"], A19["pin_rib_tip"]))
        cuts.append(text_xy("%d" % round(t * 100), 2.4, 1.0, x + 5.2, 9.0, 13.6, "center", "baseline", rot=90, heavy=True))
        cuts.append(text_xy("%d" % round(RIB_ROD[i] * 10), 2.4, 1.0, x - 5.2, 9.0, 13.6, "center", "baseline", rot=90, heavy=True))
    return union([diff(m, cuts)] + [r ^ box(0, 48.0, 0, 16.0, 0, 14.0) for r in ribs])


def steel_window():
    """A20 coupon: frame 3.0 thick, window = the steel pocket's y x z opening (40.5 x 19.5) with the 2 rear crush ribs (0.3)
    at the pocket's rib heights; label engraved on the top."""
    L = 40.0 + A20["rear_add"]                   # steel 40 long + 0.5 behind it (keyaction.a20_pocket)
    H = 19.0 + 2.0 * A20["z_add"]                # steel 19 wide + 0.25 above and below
    z0 = 33.0 - A20["z_add"]                     # steel underside z33.0 in the carrier (the rib heights below are carrier z)
    b, t = 3.5, 3.0
    m = box(0, L + 2 * b, 0, H + 2 * b, 0, t)
    cut = box(b, b + L, b, b + H, -1, t + 1)
    r, w = A20["rib_rear"], 0.3
    ribs = []
    for zc in (37.0, 48.0):                    # A18 rib_rear_z, pocket-relative
        yc = b + (zc - z0)
        ribs.append(box(b + L - r, b + L + 0.01, yc - w, yc + w, 0, t))
    lab = text_xy("A20 405x195", 2.6, 1.0, (L + 2 * b) / 2.0, 0.6, t - 0.5, "center", "baseline", heavy=True)
    return diff(union([diff(m, [cut])] + ribs), [lab])


def entries():
    """[(file name, STL bytes)] for the one-octave bundles."""
    import numpy as np
    import trimesh
    out = []
    for name, m in (("구멍시험편_세로구멍_레버허브용__1개.stl", flat()), ("구멍시험편_가로구멍_레버틀핀용__1개.stl", upright()),
                    ("구멍시험편_리브구멍_봉토막·밸런스핀용__1개.stl", ribbed()),
                    ("구멍시험편_무게추칸_강철블록용__1개.stl", steel_window())):
        mesh = to_bed(m).to_mesh()
        tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts))
        buf = io.BytesIO()
        tm.export(buf, file_type="stl")
        out.append((name, buf.getvalue()))
    return out


FOLDER = "00_먼저_구멍시험편"
README = [
    "",
    "00_먼저_구멍시험편 (A18, 2026-11-16) — 모듈을 다시 뽑기 전에 15분짜리 시험:",
    "  구멍시험편_세로구멍: 판을 눕혀 출력(레버 캐리어 허브와 같은 방향). 구멍 Ø4.1~5.0, 옆 숫자 41 = Ø4.1.",
    "  구멍시험편_가로구멍: 벽을 세워 출력(레버틀 핀 보스와 같은 방향, 눈물방울 구멍).",
    "  Ø4 봉이 손으로 들어가는 가장 작은 구멍을 찾습니다. 새 설계 값: 레버 허브 Ø4.3(봉에서 자유롭게 돌아야 함),",
    "  레버틀 핀 보스 Ø4.5(봉이 밀려 지나가면 됨). 결과가 다르면 그 값을 알려 주세요 - CAD 한 곳만 바꾸면 됩니다.",
    "  구멍시험편_리브구멍 (A19, 드릴 없음): 세워 출력. 앞 가로 구멍 3개 = Ø5.9 + 리브 3줄(끝 Ø3.8/3.9/4.0, 숫자 38·39·40) -",
    "  출력 공구 T1a 봉 토막 구멍과 같은 모양. 위 세로 구멍 3개 = Ø3.95 + 리브(끝 Ø1.85/1.95/2.05, 숫자 185·195·205) -",
    "  밸런스 핀 구멍과 같은 모양. Ø4 봉 토막·Ø2 핀이 손(또는 T3)으로 눌러 들어가고 빠지지 않는 칸이 맞는 값 (CAD 39 · 195).",
    "  구멍시험편_무게추칸 (A20): 눕혀 출력(레버 캐리어와 같은 방향). 창 40.5 × 19.5 + 뒤 크러시 리브 0.3 2줄(40.2) -",
    "  레버 캐리어 무게 추 칸의 입구와 같은 크기. 자른 강철 블록(9 × 19 × 40)이 손으로 밀려 들어가면 캐리어를 뽑습니다.",
    "  안 들어가면 강철의 실제 길이·폭을 재서 알려 주세요 (A20 pocket_y / pocket_z 한 곳만 바꾸면 됨).",
]
