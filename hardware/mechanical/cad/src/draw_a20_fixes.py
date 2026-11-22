"""A20 detail sheet (2026-11-22): real CAD sections of the sensor bar (pockets / lead slots open to the rear), the bed under
the sensor board (no ribs, floor window, edge-row pads) and the bigger steel pocket of the lever carrier.

  python3 draw_a20_fixes.py   ->  ../drawings/detail/A20_센서바·기판밑·강철칸_상세.png
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import keyaction as K  # noqa: E402
from a20_fix import A20  # noqa: E402

plt.rcParams["font.family"] = ["AppleGothic", "Apple SD Gothic Neo", "DejaVu Sans"]
OUT = os.path.join(HERE, "..", "drawings", "detail", "A20_센서바·기판밑·강철칸_상세.png")
C = {"bar": "#7f9cc9", "bed": "#a9b2bf", "board": "#4f8f5a", "steel": "#8a8f98", "body": "#79b38a", "cover": "#e3a35b",
     "sensor": "#333333"}


def sect(m, axis, v):
    if axis == "y":
        mm = m.transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, -v]], float))
    elif axis == "x":
        mm = m.transform(np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -v]], float))
    else:
        mm = m.translate((0, 0, -v))
    return mm.slice(0.0).to_polygons()


def draw(ax, m, axis, v, col, alpha=0.85, swap=False):
    """filled section; manifold returns outer and hole contours, so draw them with the even-odd rule in one path."""
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    polys = sect(m, axis, v)
    if not polys:
        return
    verts, codes = [], []
    for p in polys:
        p = p[:, ::-1] if swap else p
        verts += list(p) + [p[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(p) - 1) + [Path.CLOSEPOLY]
    path = Path(np.array(verts), codes)
    ax.add_patch(PathPatch(path, fc=col, ec="#222", lw=0.5, alpha=alpha, fill=True))


def note(ax, xy, txt, at):
    ax.annotate(txt, xy, at, fontsize=10, arrowprops=dict(arrowstyle="->", lw=0.8),
                bbox=dict(fc="white", ec="#999", alpha=0.92))


def main():
    G = K.G
    fx = K.fixed_groups(G["parts"])
    FS = K.frame_split(fx, G["plan"])
    bed, sbar = FS["bed"], K.sensorbar_solid(fx)
    pk_c = [p for p in K.SPECF["sensor_bar"]["pockets_module"] if p["key"] == "C"][0]
    lx = pk_c["lead_holes"][0]["x"]
    lb = [p for p in G["parts"] if p["body"] == "lever C"]
    body, cover = K.lever_body_solid(lb, "C"), K.lever_cover_solid(lb)
    steel = K.lever_bought(lb, "rigid0")["steel"]

    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.0, 0.9, 1.15], hspace=0.38, wspace=0.2)
    fig.suptitle("A20 한 옥타브 조립 뒤 고침 (2026-11-22) — 실제 CAD 단면", fontsize=17, fontweight="bold", y=0.985)

    # 1 sensor bar plan view at the pocket floor + section through the C lead slot
    ax = fig.add_subplot(gs[0, :2])
    draw(ax, sbar, "z", 10.0, C["bar"])
    ax.add_patch(Rectangle((1.0, 60.65), 161.6, 15.24, fill=False, ec=C["board"], lw=1.0, ls="--"))
    ax.set_xlim(-1, 166)
    ax.set_ylim(50, 80)
    ax.set_aspect("equal")
    ax.set_title("① 센서 바 z10 단면 — 다리 홈 폭 1.6(흑건 자리는 포켓까지)이 모두 뒤(y77.5)로 열림", fontsize=12)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    note(ax, (lx, 72.0), "다리 홈 1.6 (예전 Ø0.9 구멍 3개)\n뒤에서 밀어 끼우거나 위에서 꽂음", (14.0, 51.0))
    note(ax, (21.2, 70.0), "흑건 포켓 4.05 × 4.9 (몸통 3.15 × 4.0)\n바닥 z9.66 — 포켓·다리 홈이 뒤로 열림", (62.0, 51.0))
    ax.text(124, 52.0, "점선 = 센서 기판 SB (6행)", fontsize=10, color=C["board"])

    ax = fig.add_subplot(gs[0, 2])
    draw(ax, bed, "x", lx, C["bed"])
    draw(ax, sbar, "x", lx, C["bar"])
    ax.add_patch(Rectangle((60.65, 7.0), 15.24, 1.6, fc=C["board"], ec="#222", lw=0.5))
    for y in (64.46, 67.0, 69.54):
        ax.plot([y, y], [7.0, 12.9], color=C["sensor"], lw=1.2)
    ax.add_patch(Rectangle((65.0, 12.19), 4.0, 1.52, fc=C["sensor"], ec="none"))
    ax.set_xlim(55, 82)
    ax.set_ylim(1.5, 16)
    ax.set_aspect("equal")
    ax.set_title("② x%.2f (C 다리) 옆 단면: 다리 홈이 뒤로 열림" % lx, fontsize=12)
    ax.set_xlabel("y (mm)")
    ax.set_ylabel("z (mm)")
    note(ax, (70.5, 10.0), "홈 앞끝 y63.9:\n앞 다리가 여기서 멈춤", (56.0, 14.2))

    # 2 bed under the board: plan of the support (z6) and floor (z4)
    ax = fig.add_subplot(gs[1, :2])
    draw(ax, bed, "z", 4.0, C["bed"], alpha=0.55)
    draw(ax, bed, "z", 6.0, "#5d6b80", alpha=0.95)
    ax.add_patch(Rectangle((1.0, 60.65), 161.6, 15.24, fill=False, ec=C["board"], lw=1.0, ls="--"))
    ax.set_xlim(-1, 166)
    ax.set_ylim(55, 81)
    ax.set_aspect("equal")
    ax.set_title("③ 바닥틀 위에서 봄 — 연한 색 = 바닥판(z4), 진한 색 = 기판 받침(z6): 리브 없음, 기판 밑 바닥 창", fontsize=12)
    ax.set_xlabel("x (mm)")
    for xc in A20["bridges"]["module"]:
        ax.text(xc, 56.0, "바닥 다리\nx%.1f" % xc, ha="center", fontsize=9)
    note(ax, (3.0, 68.0), "왼쪽 받침 기둥\n(M3×10 2개, 그대로)", (8.0, 77.6))
    note(ax, (160.6, 61.8), "받침 패드 3.5\n(쓰지 않는 1·6행 밑)", (128.0, 77.2))

    ax = fig.add_subplot(gs[1, 2])
    draw(ax, bed, "x", 60.0, C["bed"])
    draw(ax, sbar, "x", 60.0, C["bar"])
    ax.add_patch(Rectangle((60.65, 7.0), 15.24, 1.6, fc=C["board"], ec="#222", lw=0.5))
    ax.add_patch(Rectangle((50.0, 0.0), 35.0, 3.0, fc="#d8d0c0", ec="#999", lw=0.5))
    ax.set_xlim(52, 82)
    ax.set_ylim(-0.5, 15)
    ax.set_aspect("equal")
    ax.set_title("④ x60 옆 단면: 기판 밑 4.0 (예전 2.0, 리브 2줄)", fontsize=12)
    ax.set_xlabel("y (mm)")
    ax.set_ylabel("z (mm)")
    note(ax, (68.0, 5.0), "z3(EVA 윗면)~z7.0 = 4.0\n6행 모두 밑에서 납땜·배선", (53.0, 11.6))
    ax.text(51.0, 0.6, "EVA 3T", fontsize=9)

    # 3 steel pocket: sections of the lever C carrier
    for i, (y, t) in enumerate(((158.0, "위 앞 날개 y158"), (170.0, "아래 날개 y170"), (189.0, "뒤 리브 y189"))):
        ax = fig.add_subplot(gs[2, i])
        draw(ax, steel, "y", y, C["steel"], 0.9)
        draw(ax, body, "y", y, C["body"])
        draw(ax, cover, "y", y, C["cover"])
        ax.set_xlim(1.0, 15.5)
        ax.set_ylim(30.5, 54.5)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_title("⑤ 레버 C 강철 칸 단면 %s" % t, fontsize=12)
        ax.set_xlabel("x (mm)")
        if i == 0:
            ax.set_ylabel("z (mm)")
            note(ax, (8.5, 52.25), "칸 높이 19.5 (z32.75~52.25)\n강철 19.0 위아래 0.25", (2.0, 46.0))
        if i == 1:
            note(ax, (13.2, 42.0), "칸 폭 9.4 (벽 0.59)\n덮개 리브 0.17 → 9.23", (3.0, 36.0))
        if i == 2:
            note(ax, (8.0, 37.0), "칸 길이 40.5\n뒤 리브 0.3 → 40.2", (2.0, 46.0))
    fig.text(0.5, 0.01, "강철 블록은 39.7~40.2로 자르고 두께 9.25 · 폭 19.5 이하면 그대로 씀. 캐리어를 다시 뽑기 전에 00_먼저_구멍시험편의 "
             "무게추칸 시험편(창 40.5 × 19.5 + 뒤 리브)에 강철이 밀려 들어가는지 봄.", ha="center", fontsize=11)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=110)
    print(OUT)


if __name__ == "__main__":
    main()
