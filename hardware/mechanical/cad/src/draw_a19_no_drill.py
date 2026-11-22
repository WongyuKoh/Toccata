"""A19 detail sheet (2026-11-16): no drill - the press / locating holes printed r+1 with crush ribs, drawn from the live
solids (no_drill.py, keyaction.py). -> drawings/detail/A19_드릴없음_리브구멍_상세.png
   1 T1a K stub bore (section on x, post grown)   2 T1a L stub bore   3 balance-pin hole in the rail (plan at z15)
   4 T2 hub (plan)   5 table old -> new
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
from matplotlib.patches import Circle, PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

import keyaction as K  # noqa: E402
import keyaction_parts as KP  # noqa: E402
import no_drill as N  # noqa: E402

for fp in ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc"):
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = os.path.join(os.path.dirname(HERE), "drawings", "detail", "A19_드릴없음_리브구멍_상세.png")
NEW, OLD = "#e0a060", "#a9b4d6"


def sect(m, axis, v):
    if axis == "x":
        mm = m.transform(np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -v]], float))
    else:
        mm = m.translate((0, 0, -v))
    return mm.slice(0.0).to_polygons()


def draw(ax, m, axis, v, col, alpha=0.85, edge="#222"):
    """section with holes (even-odd compound path)."""
    verts, codes = [], []
    for p in sect(m, axis, v):
        p = np.asarray(p)
        verts += list(p) + [p[0]]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(p) - 1) + [MPath.CLOSEPOLY]
    if verts:
        ax.add_patch(PathPatch(MPath(np.asarray(verts), codes), fc=col, alpha=alpha, ec=edge, lw=0.6))


def ring(ax, c, d, ls, col="#c00", lw=1.0, label=None):
    ax.add_patch(Circle(c, d / 2.0, fill=False, ls=ls, ec=col, lw=lw, label=label))


def frame(ax, c, half, title):
    ax.set_xlim(c[0] - half, c[0] + half)
    ax.set_ylim(c[1] - half, c[1] + half)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title(title, fontsize=11.5)


def main():
    J = N.bench_jig()
    J0 = N._load("tool_bench_jig.stl")
    T2 = N.capstan_gauge()
    T20 = N._load("tool_capstan_gauge.stl")
    G = K.G
    fx = K.fixed_groups(G["parts"])
    rail = K.frame_split(fx, G["plan"])["rail"]
    A = N.A19
    fig, axs = plt.subplots(2, 4, figsize=(20, 10), gridspec_kw={"height_ratios": [1, 0.5], "hspace": 0.12})
    fig.suptitle("A19 드릴 없음 (2026-11-16) — 압입·자리 구멍 = 옛 반지름 + 1 mm + 크러시 리브 3줄 (실제 CAD 단면)",
                 fontsize=16, fontweight="bold", y=0.94)
    # 1 K stub (print frame: section at x = 21.7 inside the left K post; y, z)
    ck = (N.K[0] + N.J_OFF[1], N.K[1] + N.J_OFF[2])
    for ax, solid, col, t in ((axs[0, 0], J, NEW, "1  T1a K 봉 토막 구멍 (A19)"),):
        draw(ax, J0, "x", 21.7, OLD, 0.5, "#06c")
        draw(ax, solid, "x", 21.7, col, 0.75)
        ring(ax, ck, 4.0, "--", "#06c", 1.2, "Ø4 봉 토막")
        ring(ax, ck, A["k_bore"], ":", "#c00", 1.0, "구멍 Ø%.1f" % A["k_bore"])
        ring(ax, ck, A["k_tip"], "-", "#c00", 0.8, "리브 끝 Ø%.1f" % A["k_tip"])
        frame(ax, ck, 5.5, t)
        ax.set_xlabel("y (출력, = 모델 y + 8)")
        ax.set_ylabel("z (출력, = 모델 z - 3)")
        ax.text(ck[0], ck[1] - 5.0, "주황 = A19, 파랑 = A19에서 깎인 예전 살(Ø3.9 → Ø4.0 드릴)\n기둥을 y로 1.0씩·위로 1.0 키움, 벽 0.65",
                ha="center", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
    # 2 L stub (section at x = 27.2 inside the left L post)
    cl = (N.L[0] + N.J_OFF[1], N.L[1] + N.J_OFF[2])
    ax = axs[0, 1]
    draw(ax, J0, "x", 27.2, OLD, 0.5, "#06c")
    draw(ax, J, "x", 27.2, NEW, 0.75)
    ring(ax, cl, 4.0, "--", "#06c", 1.2, "Ø4 봉 토막")
    ring(ax, cl, A["l_bore"], ":", "#c00", 1.0, "구멍 Ø%.1f" % A["l_bore"])
    ring(ax, cl, A["l_tip"], "-", "#c00", 0.8, "리브 끝 Ø%.1f" % A["l_tip"])
    frame(ax, cl, 5.5, "2  T1a L 봉 토막 구멍 (A19)")
    ax.set_xlabel("y (출력)")
    ax.text(cl[0], cl[1] - 5.0, "앞(왼쪽) 1.2에 건반 꼬리 끝이 지나 Ø4.8까지만\n(앞벽 0.65), 기둥 위로 1.0", ha="center", fontsize=9)
    ax.legend(loc="upper right", fontsize=8)
    # 3 balance pin hole in the rail, plan at z15 (pin C)
    pins = [p for p in fx["bought"] if p["part"].startswith("balance pin D2 C")]
    p = pins[0]
    ys = [q[0] for q in p["side"]]
    cp = ((p["x"][0] + p["x"][1]) / 2, (min(ys) + max(ys)) / 2)
    ax = axs[0, 2]
    draw(ax, rail, "z", 15.0, NEW)
    ring(ax, cp, 2.0, "--", "#06c", 1.2, "Ø2 밸런스 핀")
    ring(ax, cp, A["pin_bore"], ":", "#c00", 1.0, "구멍 Ø%.2f" % A["pin_bore"])
    ring(ax, cp, A["pin_tip"], "-", "#c00", 0.8, "리브 끝 Ø%.2f" % A["pin_tip"])
    frame(ax, cp, 4.0, "3  밸런스 핀 구멍 (레일, z15 평면) (A19)")
    ax.set_xlabel("x (모듈)")
    ax.set_ylabel("y")
    ax.text(cp[0], cp[1] - 3.6, "막힌 z11.3, 레일 앞뒤 벽 1.0 (양 끝 걸쇠 홈 자리 0.5)\n끝 부속 바닥틀의 핀 구멍도 같음", ha="center", fontsize=9)
    ax.legend(loc="upper right", fontsize=8)
    # 4 T2 hub (print frame plan at z6.3)
    ch = (N.L[0] - 119.0, N.L[1] - 28.9)
    ax = axs[0, 3]
    draw(ax, T20, "z", 6.3, OLD, 0.5, "#06c")
    draw(ax, T2, "z", 6.3, NEW, 0.75)
    ring(ax, ch, 4.0, "--", "#06c", 1.2, "Ø4 봉 토막")
    ring(ax, ch, A["t2_hub"], ":", "#c00", 1.0, "허브 Ø%.1f" % A["t2_hub"])
    frame(ax, ch, 6.0, "4  T2 가짜 레버 허브 (A19)")
    ax.set_xlabel("x (출력)")
    ax.text(ch[0], ch[1] - 5.4, "돌아가는 맞춤 = A18 레버 허브와 같은 Ø4.3, 리브 없음", ha="center", fontsize=9)
    ax.legend(loc="upper right", fontsize=8)
    # 5 table
    for a in axs[1, :]:
        a.axis("off")
    rows = [["구멍", "예전", "A19", "맞춤", "왜"],
            ["밸런스 핀 (레일 · 끝 부속 바닥틀)", "Ø1.95 + Ø1.9~2.0 드릴", "Ø3.95 + 리브 끝 Ø1.95", "가벼운 압입", "핀이 리브 끝을 깎으며 꽉 물림"],
            ["T1a 예비 밸런스 핀", "Ø1.9 압입", "Ø3.9 + 리브 끝 Ø1.9", "가벼운 압입", "같은 방법"],
            ["T1a K 봉 토막 (건반 봉 자리)", "Ø3.9 + Ø4.0 드릴", "Ø5.9 + 리브 끝 Ø3.9", "압입", "봉 토막이 프레임 봉 자리에 고정돼야 함"],
            ["T1a L 봉 토막 (레버 봉 자리)", "Ø3.9 + Ø4.0 드릴", "Ø4.8 + 리브 끝 Ø3.9", "압입", "앞에 건반 꼬리 → 반지름 +0.45까지"],
            ["T2 허브", "Ø3.9 + Ø4.0 드릴", "Ø4.3 (리브 없음)", "돌아가는 맞춤", "가짜 레버가 L 봉 토막에서 돎"],
            ["캡스턴 너트 홈 0.4 막", "빡빡하면 Ø3 드릴", "나사가 뚫음", "-", "드릴 대안 없앰"]]
    tb = axs[1, 0].table(cellText=rows[1:], colLabels=rows[0], loc="upper left", cellLoc="left", bbox=[0.0, 0.25, 4.45, 0.75])
    tb.auto_set_font_size(False)
    tb.set_fontsize(10.5)
    for (r, c), cell in tb.get_celld().items():
        if r == 0:
            cell.set_facecolor("#eee")
            cell.set_text_props(fontweight="bold")
    axs[1, 0].text(0.0, 0.08, "리브: 3줄, 밑 %.1f · 끝 %.1f (핀 %.1f · %.1f). 가로 구멍(T1a, 세워 출력)은 지붕에서 내려오는 지느러미(끝 45° V) + "
                   "240°·300° 리브(밑면 40°) → 서포트 없음 (check_support 0). 시험편: 00_먼저_구멍시험편/구멍시험편_리브구멍 "
                   "(가로 끝 Ø3.8·3.9·4.0, 세로 끝 Ø1.85·1.95·2.05)." % (A["rib_base"], A["rib_tip"], A["pin_rib_base"], A["pin_rib_tip"]),
                   transform=axs[1, 0].transAxes, fontsize=10.5)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=110, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
