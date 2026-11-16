"""A18 (2026-11-16) hole test coupon for the D4 lever rod, printed before the module is printed again.

The user printed one octave and the D4 rod would not go into the D3.9 printed bores (they were meant to be drilled D4.0).
A18 prints the lever hub D4.3 and the fin-boss bores D4.5 so the rod goes in undrilled; this coupon checks that on the
user's own printer in ~15 min: two small prints, holes D4.1 .. D5.0, sizes engraved (41 = D4.1).
  세로구멍 : a plate printed flat, holes along the print z - like the lever hub (the carrier prints on its side)
  가로구멍 : a wall printed upright, teardrop holes along y (apex up) - like the cage fin bosses (the cage prints on its back)
Pick the smallest hole the rod slides through by hand (hub: turns freely; fin boss: slides through), tell the CAD
(FEAT hub_bore_print / fin_bore_print in keyaction.py) if it differs from 4.3 / 4.5.
"""
import io

from cadlib import box, cyl_z, diff, teardrop_y, text_xy, to_bed, union, orient, rot_x

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


def entries():
    """[(file name, STL bytes)] for the one-octave bundles."""
    import numpy as np
    import trimesh
    out = []
    for name, m in (("구멍시험편_세로구멍_레버허브용__1개.stl", flat()), ("구멍시험편_가로구멍_레버틀핀용__1개.stl", upright())):
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
]
