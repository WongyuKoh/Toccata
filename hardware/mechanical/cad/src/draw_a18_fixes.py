"""A18 detail sheet (2026-11-16): the four fixes after the one-octave print, drawn from the live solids (keyaction.py A18).
-> drawings/detail/A18_한옥타브_고침_상세.png
   1 lever: cover clip (sections y158 / y170 / y187) + crush ribs   2 cage snap legs (rear wall x29, fin 2)
   3 rail snap (x10 section)   4 bed: floor window under the board, edge ledges only (plan at z4)   5 hole sizes
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
from matplotlib import font_manager  # noqa: E402

import keyaction as K  # noqa: E402

for fp in ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc"):
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = os.path.join(os.path.dirname(HERE), "drawings", "detail", "A18_한옥타브_고침_상세.png")
C = {"body": "#7fb69a", "cover": "#e0a060", "steel": "#9a9a9a", "bed": "#a9b4d6", "rail": "#e0a060", "cage": "#e0a060"}


def sect(m, axis, v):
    if axis == "y":
        mm = m.transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, -v]], float))
    elif axis == "x":
        mm = m.transform(np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -v]], float))
    else:
        mm = m.translate((0, 0, -v))
    return mm.slice(0.0).to_polygons()


def draw(ax, m, axis, v, col, alpha=0.85, shift=(0.0, 0.0)):
    for p in sect(m, axis, v):
        p = np.vstack([p, p[:1]]) + np.array(shift)
        ax.fill(p[:, 0], p[:, 1], color=col, alpha=alpha, lw=0)
        ax.plot(p[:, 0], p[:, 1], color="#222", lw=0.5)


def main():
    G = K.G
    parts, plan = G["parts"], G["plan"]
    lb = K.lever_normalize([p for p in parts if p["body"] == "lever C"])
    body = K.lever_body_solid(lb, "C")
    cover = K.lever_cover_solid(lb)
    steel = K.lever_bought(lb, "rigid0")["steel"]
    FS = K.frame_split(K.fixed_groups(parts), plan)
    fig = plt.figure(figsize=(20, 13.5))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.05], hspace=0.28, wspace=0.22)
    fig.suptitle("A18 한 옥타브 출력 뒤 고침 (2026-11-16) — 실제 CAD 단면", fontsize=17, fontweight="bold", y=0.985)
    # 1 lever sections
    for i, (y, t) in enumerate(((158.0, "위 앞 날개 (y153~163)"), (170.0, "아래 날개 (y165~176.4)"), (187.0, "위 뒤 날개 (y184~190)"))):
        ax = fig.add_subplot(gs[0, i])
        draw(ax, steel, "y", y, C["steel"], 0.9)
        draw(ax, body, "y", y, C["body"])
        draw(ax, cover, "y", y, C["cover"])
        ax.set_xlim(1.0, 15.5)
        ax.set_ylim(30.5, 54.5)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_title("① 레버 C 단면 y%.0f — %s" % (y, t), fontsize=12)
        ax.set_xlabel("x (mm)")
        if i == 0:
            ax.set_ylabel("z (mm)")
            ax.annotate("갈고리 0.8 × 0.4\n양면 45°: 눌러 끼우고\n날개를 들어 뺌", (2.8, 51.8), (5.0, 44.5), fontsize=10,
                        arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
            ax.annotate("-x 벽 윗끝 z52.0\n(날개 자리만 낮춤)", (3.6, 52.0), (5.0, 37.0), fontsize=10,
                        arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
        if i == 1:
            ax.annotate("덮개 안쪽 크러시 리브 0.17\n(강철을 -x 벽 쪽으로)", (13.0, 46.5), (5.2, 49.8), fontsize=10,
                        arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
            ax.annotate("아래 날개 갈고리", (2.8, 33.1), (5.0, 35.5), fontsize=10,
                        arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
    # rear crush ribs: plan section at z37 near the pocket's rear wall
    ax = fig.add_subplot(gs[0, 3])
    for m, col in ((steel, C["steel"]), (body, C["body"]), (cover, C["cover"])):
        for p in sect(m, "z", 37.0):
            p = np.vstack([p, p[:1]])
            ax.fill(p[:, 1], p[:, 0], color=col, alpha=0.85, lw=0)
            ax.plot(p[:, 1], p[:, 0], color="#222", lw=0.5)
    ax.set_xlim(181.0, 194.0)
    ax.set_ylim(1.5, 15.0)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("① 칸 뒷벽 크러시 리브 (z37 평면)", fontsize=12)
    ax.set_xlabel("y (mm)")
    ax.set_ylabel("x (mm)")
    ax.annotate("리브 0.4: 39.7~39.9 강철을\n앞벽 쪽으로 눌러 잡음\n(+x 끝 45° 들어가는 면)", (189.8, 8.0), (181.5, 3.0), fontsize=10,
                arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
    # 2 cage legs
    ax = fig.add_subplot(gs[1, 0])
    draw(ax, FS["bed"], "y", 208.0, C["bed"])
    draw(ax, FS["cage"], "y", 208.0, C["cage"])
    draw(ax, FS["bed"], "y", 180.0, C["bed"], shift=(-12.0, 0.0), alpha=0.5)
    draw(ax, FS["cage"], "y", 180.0, C["cage"], shift=(-12.0, 0.0), alpha=0.5)
    ax.set_xlim(24.5, 33.5)
    ax.set_ylim(1.5, 17.0)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("② 레버틀 걸쇠 다리 (나사 4개 대신)", fontsize=12)
    ax.set_xlabel("x (mm) — 진한 색: 뒷벽 x29 (y208), 연한 색: 핀 2번 (y180, -12 옮김)")
    ax.set_ylabel("z (mm)")
    ax.annotate("갈고리 0.5가 바닥판 밑\n0.8 홈에 딸깍 (EVA 그대로)", (30.0, 3.4), (24.8, 6.6), fontsize=10,
                arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
    ax.annotate("풀 때: 다리를 -x로\n밀며 들어 올림", (28.0, 10.0), (24.8, 13.5), fontsize=10,
                arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
    # 3 rail snap
    ax = fig.add_subplot(gs[1, 1])
    draw(ax, FS["bed"], "x", 10.0, C["bed"])
    draw(ax, FS["rail"], "x", 10.0, C["rail"])
    ax.set_xlim(129.5, 147.5)
    ax.set_ylim(2.0, 21.5)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("③ 밸런스 레일 걸쇠 (나사 2개 대신), x10 단면", fontsize=12)
    ax.set_xlabel("y (mm)")
    ax.set_ylabel("z (mm)")
    ax.annotate("받침 턱의 걸쇠 0.4\n양면 45°: 눌러 딸깍,\n당기면 빠짐", (132.4, 11.6), (134.0, 4.2), fontsize=10,
                arrowprops=dict(arrowstyle="->", lw=0.8), bbox=dict(fc="white", ec="#999", alpha=0.9))
    # 4 bed plan
    ax = fig.add_subplot(gs[1, 2])
    draw(ax, FS["bed"], "z", 4.0, C["bed"])
    for p in sect(FS["bed"], "z", 6.0):
        p = np.vstack([p, p[:1]])
        ax.plot(p[:, 0], p[:, 1], color="#c0392b", lw=0.6)
    bx0, bx1, by0, by1 = K.A16["board"]
    ax.plot([bx0, bx1, bx1, bx0, bx0], [by0, by0, by1, by1, by0], "--", color="#2c7", lw=1.2)
    ax.set_aspect("equal")
    ax.set_title("④ 바닥틀 평면 (z4 바닥판, 빨강 = z6)", fontsize=12)
    ax.set_xlabel("x (mm) — 초록 점선: 80 × 120 기판")
    ax.text(82, 133, "바닥판 창\n기판 밑 z3~7.0 = 4.0\n(옛 2.0)\n가운데 리브 없음", ha="center", va="center", fontsize=10,
            bbox=dict(fc="white", ec="#999", alpha=0.9))
    ax.text(82, 84, "가장자리 턱 2.5만 받침", ha="center", fontsize=9.5, bbox=dict(fc="white", ec="#999", alpha=0.9))
    # 5 holes table
    ax = fig.add_subplot(gs[1, 3])
    ax.axis("off")
    ax.set_title("⑤ Ø4 봉 구멍 (드릴 없이)", fontsize=12)
    rows = [("자리", "전 (A17)", "A18"), ("레버 허브", "Ø3.9 → Ø4.0 드릴", "Ø%.1f" % K.FEAT["hub_bore_print"]),
            ("레버틀 핀 보스", "Ø3.9 → Ø4.0 드릴", "Ø%.1f 눈물방울" % K.FEAT["fin_bore_print"]),
            ("봉 끝 마개", "Ø4.0", "Ø%.1f" % K.A18["plug_d"])]
    tb = ax.table(cellText=rows, loc="upper center", cellLoc="center", colWidths=[0.28, 0.42, 0.30], bbox=[-0.05, 0.62, 1.15, 0.34])
    tb.auto_set_font_size(False)
    tb.set_fontsize(9.5)
    for (r, _c), cell in tb.get_celld().items():
        if r == 0:
            cell.set_facecolor("#e8e8e8")
    ax.text(0.0, 0.55, "반지름 +1~2 mm로 넓히지 않은 이유: 레버는 봉에 매달려 있어\n"
                       "구멍 틈만큼 내려앉고(멈춤·착지·캡스턴 치수가 1~2 mm 어긋남)\n"
                       "칠 때 덜컥거림. 출력 구멍은 보통 0.1~0.2 작게 나오므로\n"
                       "Ø4.3 / Ø4.5면 드릴 없이 들어가는 크기.\n\n"
                       "먼저 확인: 묶음의 00_먼저_구멍시험편 (Ø4.1~5.0,\n"
                       "세로·가로 두 방향, 15분). 손으로 들어가는 가장 작은\n"
                       "구멍이 4.3 / 4.5와 다르면 그 값만 바꾸면 됨.",
            va="top", fontsize=10.5, transform=ax.transAxes)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=110)
    print(OUT)


if __name__ == "__main__":
    main()
