import sys, textwrap
import trimesh, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

try:
    fm.fontManager.addfont('/System/Library/Fonts/AppleSDGothicNeo.ttc')
except Exception:
    pass
plt.rcParams['font.family'] = ['Apple SD Gothic Neo', 'AppleGothic', 'sans-serif']
SIDE = sys.argv[1] if len(sys.argv) > 1 else 'L'
s = trimesh.load('Toccata_전체조립.glb')


def g(n):
    m = s.geometry[n].copy()
    for node in s.graph.nodes_geometry:
        T, geom = s.graph[node]
        if geom == n:
            m.apply_transform(T)
            break
    return m


sys.path.insert(0, 'src')
import body as B  # noqa: E402
P = {'clip': g('XT60-CLIP-' + SIDE), 'wall': g('CU-PLY-END-' + SIDE), 'F': g('C-XT60F-' + SIDE), 'M': g('C-XT60M-' + SIDE),
     'pig': g('C-SPKPIG-' + SIDE), 'lead': g('C-SPK-' + SIDE)}
COL = {'clip': '#9aa6b8', 'wall': '#e6d2ad', 'F': '#f2c230', 'M': '#e0a01a', 'pig': '#c0392b', 'lead': '#c0392b'}
EDGE = {'clip': '#2d3748', 'wall': '#8a6d3b', 'F': '#7a5a00', 'M': '#7a5a00', 'pig': '#7b1d1d', 'lead': '#7b1d1d'}
HY, HZ = B.END_HOLE_YZ[SIDE]
PK = B.XT60_POCKET[SIDE]
HR = B.END_HOLE_D / 2
if SIDE == 'L':
    lo, hi = np.array([255, 228, 24]), np.array([315, 262, 60])
    px0, px1 = B.CU_IX[0], B.CU_IX[0] + B.CLIP_PLATE_T
    cx0, cx1 = px1, PK[1]
    XSEC = px1 + B.CLIP_COLLAR + 3.0
else:
    lo, hi = np.array([905, 274, 30]), np.array([965, 306, 63])
    px0, px1 = B.CU_IX[1] - B.CLIP_PLATE_T, B.CU_IX[1]
    cx0, cx1 = PK[0], px0
    XSEC = px0 - B.CLIP_COLLAR - 3.0


def sec(name, origin, normal, axes):
    segs = trimesh.intersections.mesh_plane(P[name], plane_normal=normal, plane_origin=origin)
    return [sg[:, axes] for sg in segs]


def crop(m):
    t = m.triangles
    keep = np.all(np.all((t >= lo) & (t <= hi), axis=2), axis=1)
    m.update_faces(keep)
    return m


def dim(ax, x0, y0, x1, y1, t, off=(0, 0), fs=9):
    ax.annotate('', xy=(x0, y0), xytext=(x1, y1), arrowprops=dict(arrowstyle='<->', color='#1f5fbf', lw=1))
    ax.text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], t, color='#1f5fbf', fontsize=fs, ha='center', va='center',
            bbox=dict(fc='white', ec='none', pad=0.5))


cb = P['clip'].bounds
fig = plt.figure(figsize=(16.5, 11.7), dpi=110)
fig.suptitle('XT60 짝 집게 %s (XT60집게_%s__1개.stl) — 가운데 유닛 끝벽 %s 안쪽, 조립 상태 · 단위 mm, 본체 좌표' % (SIDE, SIDE, SIDE),
             fontsize=15, x=0.02, ha='left', y=0.985)
# A: 3D
ax = fig.add_subplot(2, 2, 1, projection='3d')
for k in ['clip', 'F', 'M', 'pig', 'lead']:
    m = crop(P[k].copy())
    if len(m.faces) == 0:
        continue
    ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=COL[k], edgecolor='none', alpha=0.45 if k == 'wall' else 1.0))
ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
ax.set_box_aspect(tuple(hi - lo)); ax.view_init(elev=24, azim=-58 if SIDE == 'L' else -122)
ax.set_xlabel('x'); ax.set_ylabel('y (→ 뒤)'); ax.set_zlabel('z')
ax.set_title('A. 입체 — 회색 = 집게, 노랑 = XT60 암·수, 빨강 = 선 (끝벽 합판은 B·C 단면에)', loc='left', fontsize=11)
# B: section through the pocket centre (x-z)
yc = (PK[2] + PK[3]) / 2
ax = fig.add_subplot(2, 2, 2)
for k in ['wall', 'clip', 'F', 'M']:
    for poly in sec(k, [0, yc, 0], [0, 1, 0], [0, 2]):
        ax.plot(poly[:, 0], poly[:, 1], c=EDGE[k] if k != 'wall' else '#b08a4a', lw=1.6 if k in ('clip',) else 1.2)
ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[2], hi[2]); ax.set_aspect('equal'); ax.grid(alpha=.25)
ax.set_title('B. 단면 y%.0f (홈 가운데) — 옆에서 봄' % yc, loc='left', fontsize=12); ax.set_xlabel('x'); ax.set_ylabel('z')
dim(ax, px0, cb[0][2] - 1.2, px1, cb[0][2] - 1.2, '판 3', (0, -1.3))
dim(ax, cx0, cb[0][2] - 1.2, cx1, cb[0][2] - 1.2, '목 %.1f + 받침 %.1f' % (B.CLIP_COLLAR, abs(cx1 - cx0) - B.CLIP_COLLAR), (0, -1.3))
xt = (cx1 + 2.5) if SIDE == 'L' else (cx0 - 2.5)
dim(ax, xt, PK[4], xt, PK[5], '홈 %.1f' % (PK[5] - PK[4]), (4.6 if SIDE == 'L' else -4.6, 1.2))
ax.axhline(HZ, ls='-.', c='#555', lw=.8); ax.text(lo[0] + 1, HZ + 0.6, '구멍 축 z%.1f' % HZ, fontsize=8, color='#555')
dim(ax, hi[0] - 2, cb[0][2], hi[0] - 2, cb[1][2], '집게 높이 z%.1f~%.1f' % (cb[0][2], cb[1][2]), (-5.5, 8), 8)
ax.text((PK[0] + PK[1]) / 2, (PK[4] + PK[5]) / 2, '암', fontsize=9, ha='center', va='center')
# C: section across the cradle (y-z), looking from the centre unit toward the end wall
ax = fig.add_subplot(2, 2, 3)
for k in ['clip', 'F']:
    for poly in sec(k, [XSEC, 0, 0], [1, 0, 0], [1, 2]):
        ax.plot(poly[:, 0], poly[:, 1], c=EDGE[k], lw=1.6)
for poly in sec('clip', [(px0 + px1) / 2, 0, 0], [1, 0, 0], [1, 2]):
    ax.plot(poly[:, 0], poly[:, 1], c='#2d3748', lw=.8, ls='--')
ax.add_patch(Circle((HY, HZ), HR, fill=False, ls='--', ec='#8a6d3b', lw=1.3))
ax.text(HY, HZ - HR - 1.6, 'Ø%.0f 구멍 (판·끝벽)' % B.END_HOLE_D, fontsize=8, ha='center', color='#8a6d3b')
dim(ax, PK[2], PK[5] + 6, PK[3], PK[5] + 6, '홈 %.1f' % (PK[3] - PK[2]), (0, 1.2))
dim(ax, cb[0][1], cb[0][2] - 1.5, cb[1][1], cb[0][2] - 1.5, '판 %.0f' % (cb[1][1] - cb[0][1]), (0, -1.3))
ax.set_xlim(cb[0][1] - 4, cb[1][1] + 4); ax.set_ylim(cb[0][2] - 4, cb[1][2] + 6); ax.set_aspect('equal'); ax.grid(alpha=.25)
ax.set_title('C. 단면 x%.0f (가운데 유닛 안에서 끝벽 쪽을 봄) — 점선 = 판 윤곽' % XSEC, loc='left', fontsize=12); ax.set_xlabel('y'); ax.set_ylabel('z')
# D: notes
ax = fig.add_subplot(2, 2, 4); ax.axis('off')
sz = {s_: [round(v, 1) for v in (lambda b_: (b_[1][0] - b_[0][0], b_[1][1] - b_[0][1], b_[1][2] - b_[0][2]))(g('XT60-CLIP-' + s_).bounds)] for s_ in 'LR'}
notes = [('무엇', '스피커 상자에서 나온 꼬리선 끝의 XT60 암 커넥터(파란 수축 튜브 + SPK)를 가운데 유닛 끝벽 안쪽에 붙잡아 두는 출력 받침. 앰프 쪽 XT60 수가 여기에 꽂힌다. (2026-10-07 XT30 → XT60)'),
         ('모양', '끝벽에 붙는 판(두께 3, Ø%.0f 구멍) + 목 %.1f (안쪽 45° 원뿔) + 받침: 바닥·옆벽 2·위 걸림 턱 2(1 × 1.2, 목 밖에만)로 된 홈 %.1f × %.1f × %.1f를 세워 둠 (XT60 암 15.8 × 8.2 × 16에 0.2씩 여유)'
          % (B.END_HOLE_D, B.CLIP_COLLAR, PK[1] - PK[0], PK[3] - PK[2], PK[5] - PK[4])),
         ('설치', '판을 끝벽 안쪽 면에 MS 폴리머로 붙인다. 판 구멍과 끝벽 Ø%.0f 구멍이 같은 축 (L: y%.0f z%.1f, R: y%.0f z%.1f)'
          % ((B.END_HOLE_D,) + B.END_HOLE_YZ['L'] + B.END_HOLE_YZ['R'])),
         ('꽂기', '암을 홈 입구(가운데 쪽)로 당겨 꺼내 손으로 수를 끝까지 꽂고 → 짝을 다시 홈에 맞춰 위에서 걸림 턱 밑으로 눌러 끼운다. 뽑기는 거꾸로'),
         ('스피커 뗄 때', '수를 뽑고 스피커 상자를 %.0f mm 들어 %.0f mm 밖으로 밀면 암이 홈 뒤의 Ø%.0f 터널(판 3 + 끝벽 11.5)로 빠진다. 꼬리 여유 약 %.0f mm는 터널 안에 느슨하게 감아 둔다'
          % (B.POD_LIFT, B.POD_SLIDE, B.END_HOLE_D, B.PIG_SLACK_MM)),
         ('잘못 꽂기', '전원 XT60은 빨강, 스피커 XT60은 파랑 + SPK. 배터리·시험 전원을 여기에 꽂지 않는다 (12.8 V 직류가 앰프 출력·스피커 코일에)'),
         ('크기·출력', 'L %s / R %s mm. 판을 베드에 놓고 홈이 위로 서게, 서포트 없음, PETG' % (' × '.join(map(str, sz['L'])), ' × '.join(map(str, sz['R'])))),
         ('파일', 'stl/print/05_본체출력물/XT60집게_L__1개.stl · XT60집게_R__1개.stl (생성기 src/body.py xt60_clips)')]
yy = 0.98
for k, v in notes:
    w = textwrap.fill(v, 44)
    ax.text(0.0, yy, k, fontsize=11, fontweight='bold', va='top', transform=ax.transAxes)
    ax.text(0.19, yy, w, fontsize=10, va='top', transform=ax.transAxes)
    yy -= 0.062 + 0.047 * w.count('\n')
plt.tight_layout(rect=[0, 0, 1, 0.96])
out = 'drawings/detail/XT60_집게_%s_상세.png' % SIDE
plt.savefig(out)
print(out)
