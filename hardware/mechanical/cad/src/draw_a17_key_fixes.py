"""A17 key fixes (2026-11-01): before / after sections of the real key C solids - the slit beside the head step, the capstan
head, and the nut slot (print pose + plan at the nut). "Before" is the same code with the A17 parts off (A15/A16 state).
Run from cad/: python3 src/draw_a17_key_fixes.py -> drawings/detail/A17_건반틈_캡스턴_너트홈_상세.png / .svg"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keyaction as K                                          # noqa: E402
from cadlib import cyl_z, prism_x, union, hexagon_z             # noqa: E402

plt.rcParams.update({"font.family": "Apple SD Gothic Neo", "axes.unicode_minus": False, "font.size": 9})
INK, DIM, RED, BLUE, GRN, ORG = "#1f2328", "#5f656d", "#d0342c", "#2f6ea5", "#0f7a2e", "#b86200"
KEYC = dict(fc="#f3f1ea", ec="#6f757d", lw=0.7)
CAPC = dict(fc="#9aa3ad", ec="#3b4048", lw=0.7)
NUTC = dict(fc="#c9ced4", ec="#3b4048", lw=0.6)
ROT_A = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]], float)   # (x,y,z) -> (y,z,x): slice at x, draw (y, z)
ROT_B = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]], float)  # (x,y,z) -> (x,z,-y): slice at y, draw (x, z)
ZTOP = 43.5                                                    # white key top = print bed

P = K.G["parts"]
BP = K.bodies_of(P)["key C"]
_, _, CAP = K.key_points(BP, P, "C")
CX, CY = CAP
BEAM = [p for p in BP if p["part"] == "beam"][0]
BX0, BX1 = BEAM["x"]
WALL = [p for p in BP if p["part"] == "head wall R"][0]
XW = (WALL["x"][0] + WALL["x"][1]) / 2.0


def key(a17):
    if a17:
        return K.key_solid(BP, P, "C")
    keep = K.key_a17_parts, K.key_a17_nut_slot
    K.key_a17_parts, K.key_a17_nut_slot = (lambda parts: parts), K.key_a15_nut_slot
    try:
        return K.key_solid(BP, P, "C")
    finally:
        K.key_a17_parts, K.key_a17_nut_slot = keep


def capstan(a17):
    h = [p for p in BP if p["part"] == "capstan head"][0]
    if a17:
        return K.capstan_a17(h, CAP)
    return union([prism_x(h["side_rest"], *h["x"]), cyl_z(CX, CY, 23.3, 29.36, 3.0)])


def nut():
    z0 = K.A15["slot_z"][0] + 0.05
    return hexagon_z(CX, CY, z0, z0 + K.A15["nut_m"], K.A15["nut_s"], rot=30)


def draw(ax, polys, st, f=lambda p: p, z=2):
    verts, codes = [], []
    for p in polys:
        p = [f(q) for q in np.asarray(p, float)]
        if len(p) < 3:
            continue
        verts += p + [p[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(p) - 1) + [Path.CLOSEPOLY]
    if verts:
        ax.add_patch(PathPatch(Path(np.array(verts), codes), zorder=z, **st))


def note(ax, xy, xyt, txt, c=INK, fs=8.5, ha="center"):
    ax.annotate(txt, xy=xy, xytext=xyt, fontsize=fs, color=c, ha=ha, va="center", zorder=20,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=c, lw=0.6),
                arrowprops=dict(arrowstyle="-|>", color=c, lw=0.7, shrinkA=0, shrinkB=1))


def frame(ax, title, c, xl, yl, xlab, ylab):
    ax.set_title(title, fontsize=10, loc="left", color=c)
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_aspect("equal")
    ax.grid(True, color="#e6e8eb", lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel(xlab, fontsize=8)
    ax.set_ylabel(ylab, fontsize=8)
    ax.tick_params(labelsize=7)


KEYS = {False: key(False), True: key(True)}
fig = plt.figure(figsize=(15.5, 20.5), dpi=120)
gs = fig.add_gridspec(4, 2, hspace=0.32, wspace=0.12, left=0.06, right=0.985, top=0.925, bottom=0.03,
                      height_ratios=[1.0, 0.9, 1.05, 1.0])
fig.suptitle("A17 건반 고침 - 옆 세모 틈 · 캡스턴 머리 · 너트 홈 (백건 C 실제 모델 단면, 왼쪽 = 이전 A15·A16, 오른쪽 = 지금)",
             fontsize=14.5, fontweight="bold", x=0.02, ha="left", y=0.985)
fig.text(0.02, 0.955, "흑건 옆 백건 모두 같은 모양(흑건의 너트 홈은 같은 모양, 출력 높이 +12). 단위 mm, 모듈 좌표(x = C 왼쪽 경계 0, y = 백건 앞 끝 0, "
         "z = 바닥 기준).", fontsize=9.5, color=DIM)

for col, a17 in enumerate((False, True)):
    k = KEYS[a17]
    tag, tc = ("이전", DIM) if not a17 else ("지금 (A17)", GRN)
    # ---- 1: the slit, side section through the head wall (x mid-wall), seen from +x
    ax = fig.add_subplot(gs[0, col])
    draw(ax, k.transform(ROT_A).slice(XW).to_polygons(), KEYC)
    frame(ax, "① %s · 옆 단면 x%.2f (흑건 쪽 옆벽 속, +x에서 봄)" % (tag, XW), tc, (43.5, 55.5), (22.2, 31.6), "y (mm)", "z (mm)")
    ax.axvspan(48.8, 50.0, ymin=0, ymax=1, color="#e3ecf6", zorder=1, lw=0)
    ax.text(49.4, 30.9, "계단벽\ny48.8~50", fontsize=7.5, color=BLUE, ha="center", va="top", zorder=21)
    ax.text(45.6, 30.9, "앞쪽 옆벽\n(head wall)", fontsize=7.5, color=DIM, ha="center", va="top", zorder=21)
    ax.text(52.6, 30.9, "꼬리 옆면은\n안쪽(x14.4)", fontsize=7.5, color=DIM, ha="center", va="top", zorder=21)
    if not a17:
        ax.add_patch(Polygon([(48.5, 23.5), (48.8, 23.5), (48.8, 26.98)], closed=True, fc=RED, ec=RED, lw=0.8, zorder=6))
        note(ax, (48.7, 24.6), (46.0, 26.9), "세모 틈: 밑 폭 0.3, 높이 3.5\n(옆벽 끝이 비스듬해 계단벽에 안 닿음)", RED)
    else:
        note(ax, (48.65, 24.6), (46.0, 26.9), "옆벽 끝을 계단벽에서 시작(밑 y48.81)\n→ 틈 없음", GRN)
    ax.axhline(23.5, color=DIM, lw=0.5, ls=(0, (3, 2)))
    ax.text(43.7, 23.2, "건반 밑면 z23.5", fontsize=7, color=DIM, va="top")

    # ---- 2: the capstan, front section through the axis + top view
    ax = fig.add_subplot(gs[1, col])
    c = capstan(a17)
    sec = c.transform(ROT_B).slice(-CY).to_polygons()
    draw(ax, k.transform(ROT_B).slice(-CY).to_polygons(), KEYC)
    draw(ax, sec, CAPC, z=4)
    top = c.project().to_polygons()
    dx, dz = 14.0, 25.6                                       # top view drawn beside the section (shifted)
    draw(ax, top, CAPC, f=lambda q: (q[0] + dx, q[1] - CY + dz + 3.2), z=4)
    if a17:
        sock = hexagon_z(CX, CY, 0, 1, K.A17["socket_s"]).project().to_polygons()
        draw(ax, sock, dict(fc="#3b4048", ec="#3b4048", lw=0.4), f=lambda q: (q[0] + dx, q[1] - CY + dz + 3.2), z=5)
    ax.text(CX + dx, dz + 6.6, "위에서 봄", fontsize=8, ha="center", color=DIM)
    ax.text(CX, 32.2, "앞에서 본 단면 (축 y%.2f)" % CY, fontsize=8, ha="center", color=DIM)
    frame(ax, "② %s · 캡스턴 M3×6 버튼헤드 (i014)" % tag, tc, (2.0, 28.5), (22.5, 33.0), "x (mm)", "z (mm)")
    if not a17:
        note(ax, (CX + dx + 2.0, dz + 3.2 + 2.0), (CX + dx + 0.0, 23.6), "머리 옆모양을 x로 늘인 '빵' 모양\n(위에서 보면 네모, 앞에서 보면 납작)", RED)
    else:
        note(ax, (CX + dx + 1.9, dz + 3.2 + 1.1), (CX + dx + 0.0, 23.6), "실제 ISO 7380: 둥근 머리 Ø5.7 × 1.65\n+ 2 mm 육각 구멍 (렌치 i065)", GRN)

    # ---- 3: the nut slot in the print pose (turned over, bed at the bottom), front section through the axis
    ax = fig.add_subplot(gs[2, col])
    flip = lambda q: (q[0], ZTOP - q[1])
    draw(ax, k.transform(ROT_B).slice(-CY).to_polygons(), KEYC, f=flip)
    draw(ax, nut().transform(ROT_B).slice(-CY).to_polygons(), NUTC, f=flip, z=4)
    ax.axhline(0, color=INK, lw=1.4)
    ax.text(BX0 - 5.6, 0.5, "베드 (윗면 z43.5를 PEI에, 뒤집어 출력)", fontsize=7.5, color=INK)
    for x in np.linspace(BX0 + 0.4, BX1 - 0.4, 7):
        ax.plot([x, x + (CX - x) * 0.2], [0, ZTOP - 27.5 - 0.05], color="#e3a35a", lw=1.0, zorder=1)
    ax.text(CX, 7.2, "꼬리 밑 트리 서포트\n(빌드 플레이트에서만)", fontsize=7.5, color=ORG, ha="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85), zorder=3)
    zb = ZTOP - K.A15["slot_z"][0]
    x0 = CX - (K.A17["shoulder"] if a17 else K.A15["slot_end"])
    ax.add_patch(Polygon([(x0, zb), (BX1, zb), (BX1, zb + 0.2), (x0, zb + 0.2)], closed=True, fc=BLUE, ec=BLUE, zorder=6))
    note(ax, (CX + 2.6, zb + 0.1), (BX1 + 2.4, 23.4), "홈 천장 = 구멍 없는 0.4 막\n5.6 다리 (A15 그대로)", BLUE)
    if not a17:
        note(ax, (BX0 + 0.4, ZTOP - 25.0), (BX0 - 1.8, 13.0), "홈은 +x 쪽만 열림\n→ 홈 속에 남은 것은\n한쪽으로만 꺼내야 함", RED)
    else:
        ax.annotate("", xy=(CX - 1.2, ZTOP - 24.9), xytext=(BX0 - 4.6, ZTOP - 24.9), zorder=8,
                    arrowprops=dict(arrowstyle="-|>", color=GRN, lw=1.8))
        note(ax, (BX0 - 1.4, ZTOP - 24.9), (BX0 - 1.8, 13.0), "-x 쪽 폭 3 빼기 통로\n→ 2 mm 육각 렌치로\n반대쪽에서 밀어냄", GRN)
    ax.text(CX, ZTOP - 27.5 - 0.35, "Ø2.8 구멍 (A15 그대로 열림)", fontsize=7, color=DIM, ha="center", va="top", zorder=21)
    frame(ax, "③ %s · 너트 홈, 출력 자세 (y%.2f 단면, 앞에서 봄)" % (tag, CY), tc, (BX0 - 6.5, BX1 + 7.0), (-0.6, 25.0), "x (mm)", "출력 높이 (mm)")

    # ---- 4: plan at the nut (z24.9), seen from above in use
    ax = fig.add_subplot(gs[3, col])
    draw(ax, k.slice(24.9).to_polygons(), KEYC)
    draw(ax, nut().slice(24.9).to_polygons(), NUTC, z=4)
    draw(ax, cyl_z(CX, CY, 24.0, 25.0, 3.0).slice(24.9).to_polygons(), CAPC, z=5)
    frame(ax, "④ %s · 너트 높이 평면 (z24.9, 위에서 봄)" % tag, tc, (BX0 - 6.0, BX1 + 6.5), (CY - 6.0, CY + 6.0), "x (mm)", "y (mm)")
    ax.annotate("", xy=(BX1 + 0.2, CY - 4.4), xytext=(BX1 + 4.6, CY - 4.4), zorder=8,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0))
    ax.text(BX1 + 2.4, CY - 5.1, "너트 넣는 쪽 (+x)", fontsize=8, ha="center", color=INK)
    if not a17:
        note(ax, (CX - 3.2, CY + 1.2), (BX0 - 3.0, CY + 4.6), "막힌 끝벽 (축에서 3.2)\n홈 속에 서포트가 생기면\n한쪽으로만 열려 빼기 어려움", RED)
    else:
        ax.annotate("", xy=(BX0 + 1.4, CY), xytext=(BX0 - 4.8, CY), zorder=8,
                    arrowprops=dict(arrowstyle="-|>", color=GRN, lw=1.8))
        note(ax, (BX0 - 2.0, CY + 0.15), (BX0 - 2.6, CY + 4.4), "빼기 통로 폭 3 (-x 면까지)\n2 mm 육각 렌치로 밀어냄", GRN)
        note(ax, (CX - K.A17["shoulder"], CY - 2.2), (BX0 - 2.6, CY - 4.5), "너트는 양쪽 어깨에 닿아 축에 섬\n(축에서 %.2f)" % K.A17["shoulder"], GRN)

out = os.path.join(os.path.dirname(HERE), "drawings", "detail", "A17_건반틈_캡스턴_너트홈_상세")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out + ".png")
fig.savefig(out + ".svg")
print("wrote", out + ".png / .svg")
