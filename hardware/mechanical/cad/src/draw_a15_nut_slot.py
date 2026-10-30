"""A15 capstan nut slot detail (2026-10-30): sections of the real key / nut / capstan solids + the first print layer over
the slot, A12 (tip hole through the ceiling) vs A15 (0.4 membrane). Run from cad/: python3 src/draw_a15_nut_slot.py
-> drawings/detail/A15_캡스턴_너트홈_상세.png / .svg"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib import font_manager as fm            # noqa: E402
from matplotlib.patches import PathPatch, Polygon, Circle  # noqa: E402
from matplotlib.path import Path                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keyaction as K                                # noqa: E402
from keyaction_parts import build_unit, G            # noqa: E402

try:
    fm.fontManager.addfont("/System/Library/Fonts/AppleSDGothicNeo.ttc")
except Exception:
    pass
plt.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "sans-serif"]
plt.rcParams["hatch.linewidth"] = 0.5

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
P = {p.id: p for p in build_unit(G["parts"], G["plan"], "O1", 0.0, "O1", {n: n + "1" for n in NOTES}, None)}
KEY, NUT, CAP = P["O1-KEY-C"].solid, P["O1-NUT-C"].solid, P["O1-CAPSTAN-C"].solid
FELT = [p.solid for i, p in P.items() if i.startswith("O1-FELTSTRIP-C")]
LEV = [p.solid for i, p in P.items() if i == "O1-LEVER-C"]
kp = [p for p in G["parts"] if p["body"] == "key C"]
CX, CY = K.key_points(kp, G["parts"], "C")[2]
BX0, BX1 = [p for p in kp if p["part"] == "beam"][0]["x"]
Z0, Z1 = K.A15["slot_z"]
MEM = K.A15["membrane"]
AF = K.A15["slot_af"]
ZTOP = 43.5                                          # white key top = print bed (rot_y 180)

INK, DIM, BLUE, RED, ORG = "#1d2433", "#3b4a6b", "#1f6fd1", "#c62828", "#e8892b"
STYLE = {"key": dict(fc="#f3efe6", ec=INK, hatch="////", lw=0.9), "nut": dict(fc="#aeb6c2", ec="#2d3748", hatch=None, lw=0.9),
         "cap": dict(fc="#d5dae2", ec="#2d3748", hatch=None, lw=0.9), "felt": dict(fc="#8fbf8f", ec="#2f5f2f", hatch=None, lw=0.6),
         "lev": dict(fc="none", ec="#8a94a6", hatch=None, lw=0.6)}


def sec_y(m, y):
    """section at y (front view): polygons in (x, z)."""
    return m.rotate((-90, 0, 0)).slice(-y).to_polygons()


def sec_x(m, x):
    """section at x (side view): polygons in (y, z)."""
    return [[(q[1], q[0]) for q in poly] for poly in m.rotate((0, 90, 0)).slice(-x).to_polygons()]


def draw(ax, polys, st, flip=False):
    if not polys:
        return
    verts, codes = [], []
    for poly in polys:
        pts = [(a, ZTOP - b) if flip else (a, b) for a, b in poly]
        verts += pts + [pts[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(pts) - 1) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=st["fc"], edgecolor=st["ec"], hatch=st["hatch"], lw=st["lw"]))


def arrow(ax, a, b, c=DIM, lw=0.7, both=True):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<|-|>" if both else "-|>", color=c, lw=lw, shrinkA=0, shrinkB=0,
                                                    mutation_scale=7))


def dim_v(ax, x, za, zb, txt, side=1, c=DIM, ext=None, fs=8):
    """vertical dimension at x from za to zb; ext = x of the feature (extension lines)."""
    if ext is not None:
        for z in (za, zb):
            ax.plot([ext, x + 0.15 * side], [z, z], color=c, lw=0.4)
    arrow(ax, (x, za), (x, zb), c)
    ax.text(x + 0.18 * side, (za + zb) / 2, txt, ha="left" if side > 0 else "right", va="center", fontsize=fs, color=c)


def dim_h(ax, z, xa, xb, txt, up=1, c=DIM, ext=None, fs=8):
    if ext is not None:
        for x in (xa, xb):
            ax.plot([x, x], [ext, z + 0.15 * up], color=c, lw=0.4)
    arrow(ax, (xa, z), (xb, z), c)
    ax.text((xa + xb) / 2, z + 0.2 * up, txt, ha="center", va="bottom" if up > 0 else "top", fontsize=fs, color=c)


def note(ax, xy, xyt, txt, c=INK, fs=8, ha="left"):
    ax.annotate(txt, xy=xy, xytext=xyt, fontsize=fs, color=c, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", color=c, lw=0.5, shrinkA=1, shrinkB=1))


fig = plt.figure(figsize=(16.5, 11.7), dpi=150)
fig.suptitle("A15 캡스턴 너트 홈 - 너트는 그대로, 홈 천장은 구멍 없는 0.4 막 (백건 C, 흑건은 같은 모양 · 출력 높이 +12)",
             fontsize=14, fontweight="bold", x=0.02, ha="left", y=0.985)
fig.text(0.02, 0.952, "M3 너트(i011)를 빔 옆 홈에 끼우고 캡스턴 M3×6 버튼헤드(i014)를 위에서 돌려 넣음. 뒤집어 출력하면 홈 위 첫 층이 맞변 사이 "
         "%.1f 다리 - Bambu 최대 다리 길이 10 mm 안, 서포트 없음. 처음 돌려 넣을 때 나사 끝이 막을 뚫음." % AF, fontsize=9.5, color=DIM)

# ---------------------------------------------------------------- 1: A-A front section, in use
ax = fig.add_axes([0.03, 0.50, 0.30, 0.42])
for m, k in ((KEY, "key"),) + tuple((m, "lev") for m in LEV) + tuple((m, "felt") for m in FELT) + ((NUT, "nut"), (CAP, "cap")):
    draw(ax, sec_y(m, CY), STYLE[k])
ax.set_xlim(2.0, 16.5)
ax.set_ylim(19.6, 33.6)
dim_v(ax, BX1 + 1.0, Z0, Z1, "홈 %.1f (z%.1f~%.1f)" % (Z1 - Z0, Z0, Z1), ext=BX1)
dim_v(ax, BX1 + 1.0, Z0 - MEM, Z0, "막 %.1f (두 층)" % MEM, ext=CX + 1.65, c=BLUE)
dim_v(ax, BX0 - 0.7, 21.8, Z0 - MEM, "Ø%.1f 나사 끝 구멍" % K.FEAT["cap_tip_d"], side=-1, ext=CX - 1.65)
dim_v(ax, BX0 - 0.7, Z1, 27.5, "Ø%.1f 잠김 구멍 %.1f" % (K.FEAT["cap_hole_d"], 27.5 - Z1), side=-1, ext=CX - 1.4)
dim_h(ax, 20.5, CX - 2.75 / math.cos(math.radians(30)), CX + 2.75 / math.cos(math.radians(30)), "너트 맞모 6.35 (M3, 맞변 5.5 × 2.4)",
      up=-1, ext=Z0)
ax.annotate("너트 넣는 쪽 (+x 옆면이 열림)", xy=(BX1 + 0.1, (Z0 + Z1) / 2 + 0.55), xytext=(BX1 + 0.4, 29.4), fontsize=8, color=INK,
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7))
note(ax, (CX + 1.0, 31.2), (9.6, 33.2), "레버 펠트 띠 (늘 캡스턴을 누름 → 너트는 막 쪽 면에 앉음)", fs=7.5, ha="center")
ax.set_title("① 단면 A–A (사용 자세, 캡스턴 축 y%.2f, 앞에서 봄)" % CY, fontsize=10.5, loc="left")
ax.set_aspect("equal")
ax.set_xlabel("x (mm)", fontsize=8)
ax.set_ylabel("z (mm)", fontsize=8)
ax.tick_params(labelsize=7)

# ---------------------------------------------------------------- 2: B-B side section, in use
ax = fig.add_axes([0.36, 0.50, 0.30, 0.42])
for m, k in ((KEY, "key"),) + tuple((m, "lev") for m in LEV) + tuple((m, "felt") for m in FELT) + ((NUT, "nut"), (CAP, "cap")):
    draw(ax, sec_x(m, CX), STYLE[k])
ax.set_xlim(178.0, 200.0)
ax.set_ylim(19.6, 33.6)
dim_h(ax, 20.5, CY - AF / 2, CY + AF / 2, "맞변 사이 %.1f = 출력 때 다리 길이" % AF, up=-1, ext=Z0, c=BLUE)
note(ax, (CY + 2.2, Z0 - MEM / 2), (193.6, 20.4), "0.4 막 (나사 끝이 뚫음)", c=BLUE)
note(ax, (196.0, 23.6), (194.6, 27.2), "얇은 꼬리", fs=7.5)
ax.set_title("② 단면 B–B (사용 자세, x%.3f, 옆에서 봄)" % CX, fontsize=10.5, loc="left")
ax.set_aspect("equal")
ax.set_xlabel("y (mm)", fontsize=8)
ax.tick_params(labelsize=7)

# ---------------------------------------------------------------- 3: B-B in the print pose (top face on the bed)
ax = fig.add_axes([0.69, 0.50, 0.29, 0.42])
draw(ax, sec_x(KEY, CX), STYLE["key"], flip=True)
ys = [146.0, 181.34, 182.34, 192.34, 192.34, 197.5, 199.0]
und = [ZTOP - 28.5, ZTOP - 28.5, ZTOP - 27.5, ZTOP - 27.5, ZTOP - 24.9, ZTOP - 24.9, ZTOP - 23.4]
ax.add_patch(Polygon([(176.0, 0), (176.0, ZTOP - 28.5)] + [(y, z) for y, z in zip(ys, und) if y >= 176.0] + [(199.0, 0)], closed=True,
                     fc="#fde7cf", ec=ORG, hatch="xx", lw=0.6))
ax.axhline(0, color=INK, lw=1.6)
ax.text(177.0, 0.6, "베드 (윗면 z43.5를 PEI에)", fontsize=8, color=INK)
ax.text(187.5, 7.0, "트리 서포트 (개략): 빔·꼬리 바깥 밑면만\n(빌드 플레이트에서만, 한 덩어리로 떨어짐)", fontsize=8, color="#9a4d0b", ha="center")
zb = ZTOP - Z0
ax.add_patch(Polygon([(CY - AF / 2, zb), (CY + AF / 2, zb), (CY + AF / 2, zb + 0.2), (CY - AF / 2, zb + 0.2)], closed=True,
                     fc=BLUE, ec=BLUE, lw=0.4))
note(ax, (CY, zb + 0.1), (184.0, 25.6), "홈 위 첫 층 = 다리 %.1f (양쪽 맞변에 붙음)\n→ Bambu 서포트 없음" % AF, c=BLUE, fs=8)
dim_v(ax, 199.6, ZTOP - Z1, zb, "홈 %.1f" % (Z1 - Z0), ext=CY + AF / 2)
dim_v(ax, 199.6, zb, zb + MEM, "막 %.1f" % MEM, ext=CY + 1.65, c=BLUE)
ax.text(176.4, 22.6, "출력 z = 43.5 − z: 홈 z%.1f~%.1f, 막 z%.1f~%.1f\n(모두 0.2 층 경계)" % (ZTOP - Z1, ZTOP - Z0, ZTOP - Z0,
                                                                                      ZTOP - Z0 + MEM), fontsize=7.5, color=DIM, va="bottom")
ax.set_ylim(-0.8, 27.0)
ax.set_xlim(176.0, 201.5)
ax.set_ylim(-0.8, 27.0)
ax.set_title("③ 출력 자세 B–B (뒤집음, 베드가 아래)", fontsize=10.5, loc="left")
ax.set_aspect("equal")
ax.set_xlabel("y (mm)", fontsize=8)
ax.set_ylabel("출력 높이 (mm)", fontsize=8)
ax.tick_params(labelsize=7)


# ---------------------------------------------------------------- 4: the first layer over the slot, plan (bridge lines)
def plan(ax, x0, hole, title, verdict, vc):
    """slot footprint (hex + open slot) seen from the bed side at the ceiling layer, bridge lines across y."""
    r = K.A15["slot_end"]                                            # flat closed end (A15; D02 had a hex V end)
    px = lambda x: x0 + (x - CX)                                     # noqa: E731
    beam = [(px(BX0), CY - 6), (px(BX1), CY - 6), (px(BX1), CY + 6), (px(BX0), CY + 6)]
    ax.add_patch(Polygon(beam, closed=True, fc="#f3efe6", ec=INK, hatch="////", lw=0.8))
    rh = AF / math.sqrt(3.0)                                         # D02 hex V end (old), corner 3.23 from the axis
    if hole:
        foot = [(px(CX - rh / 2), CY - AF / 2), (px(BX1), CY - AF / 2), (px(BX1), CY + AF / 2), (px(CX - rh / 2), CY + AF / 2),
                (px(CX - rh), CY)]
    else:
        foot = [(px(CX - r), CY - AF / 2), (px(BX1), CY - AF / 2), (px(BX1), CY + AF / 2), (px(CX - r), CY + AF / 2)]
    ax.add_patch(Polygon(foot, closed=True, fc="white", ec=INK, lw=0.9))
    x_end = CX - (rh if hole else r)
    xs = [x_end + 0.25 + 0.4 * i for i in range(40) if x_end + 0.25 + 0.4 * i < BX1]
    for x in xs:
        hw = AF / 2 if (not hole or x >= CX - rh / 2) else (x - (CX - rh)) * math.tan(math.radians(60))
        if hole and abs(x - CX) < 1.65:
            hy = math.sqrt(1.65 ** 2 - (x - CX) ** 2)
            ax.plot([px(x), px(x)], [CY - hw, CY - hy], color=RED, lw=1.1)
            ax.plot([px(x), px(x)], [CY + hy, CY + hw], color=RED, lw=1.1)
        else:
            ax.plot([px(x), px(x)], [CY - hw, CY + hw], color=BLUE, lw=0.9)
    if hole:
        ax.add_patch(Circle((px(CX), CY), 1.65, fc="white", ec=RED, lw=1.0, ls="--"))
    ax.text(px(CX), CY + 6.9, title, ha="center", fontsize=9, fontweight="bold")
    ax.text(px(CX), CY - 7.3, verdict, ha="center", va="top", fontsize=8, color=vc)


ax = fig.add_axes([0.03, 0.04, 0.62, 0.40])
plan(ax, 0.0, True, "예전 D02·A12 천장 (육각 V 끝, 가운데 Ø3.3 구멍)", "빨강 = 한쪽만 붙은 선(구멍 둘레가 허공)\n→ Bambu가 홈 속까지 트리 서포트 → 빼기 어려움", RED)
plan(ax, 16.0, False, "A15: 구멍 없는 0.4 막, 평평한 끝 (축에서 3.2)", "파랑 = 양쪽 맞변에 붙은 다리 5.6 (최대 다리 10 안)\n→ 서포트 없음, 나사가 처음 들어갈 때 막을 뚫음", BLUE)
ax.annotate("", xy=(16.0 - 7.2, CY), xytext=(7.4, CY), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0))
for x0 in (0.0, 16.0):
    ax.annotate("너트", xy=(x0 + (BX1 - CX) - 0.2, CY + 1.6), xytext=(x0 + (BX1 - CX) + 1.4, CY + 3.6), fontsize=7.5,
                arrowprops=dict(arrowstyle="<|-", color=INK, lw=0.7))
ax.set_xlim(-9.0, 25.0)
ax.set_ylim(CY - 10.5, CY + 8.5)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("④ 홈 위 첫 출력 층 (베드 쪽에서 봄, 선 = 다리 방향) - 예전 vs A15", fontsize=10.5, loc="left")

ax = fig.add_axes([0.67, 0.04, 0.31, 0.40])
ax.axis("off")
rows = [("부품", "M3 육각너트 i011 (건반 88 + 브래킷 4 = 92, 구매 목록 92 그대로)"),
        ("홈", "맞변 %.1f (너트 5.5 + 0.1) × 높이 %.1f (너트 2.4 + 다리 처짐 0.4), +x 옆면으로 열림, 닫힌 끝은 축에서 %.1f "
               "평평한 벽(너트 꼭짓점 3.175가 닿아 축에 섬; D02의 육각 V 대신)" % (AF, Z1 - Z0, K.A15["slot_end"])),
        ("막", "%.1f (0.2 두 층), 그 밑 Ø%.1f 나사 끝 구멍은 빔 밑까지" % (MEM, K.FEAT["cap_tip_d"])),
        ("잠김 구멍", "너트 위 Ø%.1f × %.1f (D02로 되돌림, A13의 Ø2.7 대신)" % (K.FEAT["cap_hole_d"], 27.5 - Z1)),
        ("조립", "① 너트를 옆에서 밀어 넣음  ② 캡스턴을 위에서 돌려 넣음 - 끝이 막에 닿으면 조금 더 돌려 뚫음 "
                 "(빡빡하면 Ø3 드릴을 손으로 밑에서)  ③ 높이 맞춤"),
        ("출력", "윗면을 PEI에, 서포트 켬 · 트리(자동) · 빌드 플레이트에서만 - 꼬리 바깥 밑면에만 생김"),
        ("확인", "check_support 125개 파일 서포트 0 (건반 28개: 다리 2 = 걸쇠 가로대 + 너트 홈), 예전 구멍 천장은 같은 검사에서 걸림; "
                 "check_interf · check_body · check_electronics 통과; 너트 ↔ 건반 겹침 0"),
        ("남은 확인", "실제 다리 처짐·막 뚫기는 C08a 쿠폰(같은 A15 홈으로 바꿈, 닫힌 끝 2.8 → 3.2)이나 첫 출력 건반에서")]
y = 0.98
for k, v in rows:
    ax.text(0.0, y, k, fontsize=9, fontweight="bold", va="top", color=INK, transform=ax.transAxes)
    import textwrap
    lines = textwrap.wrap(v, 46)
    ax.text(0.17, y, "\n".join(lines), fontsize=8.6, va="top", color=INK, transform=ax.transAxes, linespacing=1.35)
    y -= 0.045 + 0.047 * len(lines)
ax.set_title("⑤ 사양", fontsize=10.5, loc="left")

out = os.path.join(os.path.dirname(HERE), "drawings", "detail", "A15_캡스턴_너트홈_상세")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out + ".png")
fig.savefig(out + ".svg")
print("wrote", out + ".png / .svg")
