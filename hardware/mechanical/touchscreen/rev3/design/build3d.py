# Quick 3D check model (boxes/cylinders) for rev 3 — NOT the CAD model. All sizes from numbers.json; poses from numbers.json 'poses'.
# Writes preview3d_rev3.glb (use + folded scenes) and preview3d_rev3.png (4 views) so the layout can be checked before CAD.
import json, math
from pathlib import Path
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import font_manager
for fp in ['/System/Library/Fonts/AppleSDGothicNeo.ttc', '/System/Library/Fonts/Supplemental/AppleGothic.ttf']:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp); plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name(); break
D = Path(__file__).resolve().parent
N = json.load(open(D / 'numbers.json'))
PL = N['placement']; XC = PL['x_centre']; LID = PL['lid']; KO = PL['keepout']
CR, HG, LG, S, HO, CL, PI, FO = N['cradle'], N['hinge'], N['leg'], N['screen'], N['hole'], N['clip'], N['pi5'], N['fold']
PK = LG['pocket']; UA, WA = HG['axis_cradle_uw']; H = HG['axis_yz']

def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0]); m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return m
def cyl_x(x0, x1, y, z, r):
    m = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=24); m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    m.apply_translation([(x0 + x1) / 2, y, z]); return m
def cyl_z(x, y, z0, z1, r):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=24); m.apply_translation([x, y, (z0 + z1) / 2]); return m
def prism_x(x0, x1, pts_yz):
    """convex prism along x from a convex (y, z) profile"""
    pts = [(x, y, z) for x in (x0, x1) for (y, z) in pts_yz]
    return trimesh.convex.convex_hull(np.array(pts, float))

COL = dict(lid=[160, 205, 170, 255], knuckle=[95, 160, 115, 255], cradle=[190, 210, 245, 255], screen=[40, 60, 90, 255], active=[70, 140, 255, 255],
           leg=[122, 75, 183, 255], pi=[46, 125, 50, 255], module=[220, 225, 232, 255], bar=[232, 211, 173, 255], rib=[217, 112, 0, 255], hole=[217, 112, 0, 255])
def paint(m, c): m.visual.face_colors = c; return m

# ---------------- cradle in local (xr, u, w) -> world via M ----------------
def cradle_local():
    xr0, xr1 = CR['xr']; u0, u1 = CR['u']; w0, w1 = CR['w']; pl0, pl1 = CR['plate']; t = CR['rim']
    parts = []
    parts += [box(xr0, xr0 + t, u0, u1, w0, w1), box(xr1 - t, xr1, u0, u1, w0, w1)]              # side walls (to rib face)
    parts += [box(xr0, xr1, u1 - t, u1, w0, w1)]                                                   # top wall
    g = CR['groove']; nt = CR['notch']; bu = CR['walls']['bottom_u']          # bottom wall u-2.5..0; cable groove and relief notch cut into it
    segs = sorted([(xr0, g['xr'][0], w0, w1), (g['xr'][0], g['xr'][1], w0, g['w'][0]), (g['xr'][1], nt['xr'][0], w0, w1),
                   (nt['xr'][0], nt['xr'][1], nt['w'][1], w1), (nt['xr'][1], xr1, w0, w1)])
    parts += [box(a, b, bu[0], bu[1], c, d) for a, b, c, d in segs if b - a > 1e-6]
    ins = CR['insp']
    parts += [box(xr0, ins['xr'][0], u0, u1, pl0, pl1), box(ins['xr'][1], xr1, u0, u1, pl0, pl1),
              box(ins['xr'][0], ins['xr'][1], u0, ins['u'][0], pl0, pl1), box(ins['xr'][0], ins['xr'][1], ins['u'][1], u1, pl0, pl1)]
    for uu in CR['cross_ribs_u']:
        for a, b in [(xr0, LG['channel']['xr_walls'][0][0]), (LG['channel']['xr_walls'][1][1], xr1)]:
            if uu > ins['u'][0] - 2 and uu < ins['u'][1] + 2 and b > ins['xr'][0]: a2 = max(a, ins['xr'][1]); parts.append(box(a, ins['xr'][0], uu - 1, uu + 1, pl1, w1)); parts.append(box(a2, b, uu - 1, uu + 1, pl1, w1))
            else: parts.append(box(a, b, uu - 1, uu + 1, pl1, w1))
    for wl in LG['channel']['xr_walls']: parts.append(box(wl[0], wl[1], LG['channel']['u'][0], LG['channel']['u'][1], pl1, w1))
    for p in CR['pads']: parts.append(box(p['xr'][0], p['xr'][1], p['u'][0], p['u'][1], pl1, w1))
    bo = CR['bosses']
    for xr in bo['xr']:
        for u in bo['u']:
            m = trimesh.creation.cylinder(radius=bo['d'] / 2, height=w1 - bo['face_w'], sections=20); m.apply_translation([xr, u, (w1 + bo['face_w']) / 2]); parts.append(m)
            si = CR['walls']['side_inner_xr'] * (1 if xr > 0 else -1)                                 # boss joined to the side wall
            parts.append(box(min(xr, si), max(xr, si), u - bo['fill_to_side_wall']['width_u'] / 2, u + bo['fill_to_side_wall']['width_u'] / 2, bo['face_w'], w1))
    for side in ('left', 'right'):                                                                  # ears: numbers cradle.ear.profile_uw extruded over the ear x
        e = HG[side]['ear']
        parts.append(trimesh.convex.convex_hull(np.array([(x, u, w) for x in e for (u, w) in CR['ear']['profile_uw']], float)))
    cv = LG['clevis']; up, wp = LG['pivot_cradle_uw']
    for a, b in (cv['near'], cv['far']):
        m = trimesh.creation.cylinder(radius=cv['R'], height=b - a, sections=24); m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        m.apply_translation([(a + b) / 2, up, wp]); parts.append(m); parts.append(box(a, b, up - cv['R'], up + cv['R'], pl1, wp))
    for bb in LG['clip']['xr_bodies']: parts.append(box(bb[0], bb[1], LG['clip']['u'][0], LG['clip']['u'][1], pl1, LG['clip']['back_w']))
    cr = trimesh.util.concatenate(parts); paint(cr, COL['cradle'])
    gx0, gx1 = -S['glass'][0] / 2, S['glass'][0] / 2; ax0, ax1 = S['active_x'][0] - XC, S['active_x'][1] - XC; au0, au1 = S['active_u']
    scr = trimesh.util.concatenate([box(gx0, gx1, 0, S['glass'][1], 0.6, S['body']),                       # body behind the glass skin
                                    box(gx0, ax0, 0, S['glass'][1], 0, 0.6), box(ax1, gx1, 0, S['glass'][1], 0, 0.6),   # bezel strips
                                    box(ax0, ax1, 0, au0, 0, 0.6), box(ax0, ax1, au1, S['glass'][1], 0, 0.6)]); paint(scr, COL['screen'])
    act = box(ax0, ax1, au0, au1, 0, 0.6); paint(act, COL['active'])
    emb = box(S['emboss']['xr'][0], S['emboss']['xr'][1], S['emboss']['u'][0], S['emboss']['u'][1], S['body'], S['body'] + S['emboss']['h']); paint(emb, COL['screen'])
    rb = CR['rib_band_xr']; fs = CR['fold_square']
    rib = trimesh.util.concatenate([box(rb[0], rb[1], CR['u'][0] - 0.5, fs['u'][1], 8.4, 8.8), box(S['fpc']['mouth_xr'], fs['xr'][1], fs['u'][0], fs['u'][1], 8.4, 8.8)]); paint(rib, COL['rib'])
    return [cr, scr, act, emb, rib]

def to_world(meshes, M):
    out = []
    for m in meshes:
        m = m.copy(); m.apply_transform(np.array(M, float)); out.append(m)
    return out

def leg_use():
    p = N['poses']['leg_use']; piv = np.array(p['pivot_xyz'], float); d = np.array(p['dir_pivot_to_tip'], float); L = p['length']
    m = trimesh.creation.box(extents=[LG['section'][0], L, LG['section'][1]])
    ang = math.atan2(d[2], d[1]); R = trimesh.transformations.rotation_matrix(ang, [1, 0, 0])
    m.apply_translation([0, L / 2, 0]); m.apply_transform(R); m.apply_translation(piv)
    tip = cyl_x(XC - 5, XC + 5, piv[1] + d[1] * L, piv[2] + d[2] * L, LG['section'][1] / 2)
    return [paint(trimesh.util.concatenate([m, tip]), COL['leg'])]
def leg_stowed_local():
    up, wp = LG['pivot_cradle_uw']
    return [paint(box(-5, 5, up - 3, LG['stow_tip_u'], wp - LG['section'][1] / 2, wp + LG['section'][1] / 2), COL['leg'])]

def fixed_world():
    L = []
    L.append(paint(box(LID['x'][0], LID['x'][1], LID['y'][0], LID['y'][1], LID['top_z'] - LID['plate_t'], LID['top_z']), COL['lid']))
    kp = HG['knuckle_profile']
    prof = [(kp['base_y'][0], LID['top_z']), (kp['base_y'][1], LID['top_z']), (kp['at_axis_y'][1], H[1])] + \
           [(H[0] + HG['cheek_R'] * math.cos(a), H[1] + HG['cheek_R'] * math.sin(a)) for a in np.linspace(0, math.pi, 13)] + [(kp['at_axis_y'][0], H[1])]
    for side in ('left', 'right'):
        for ck in ('far_cheek', 'near_cheek'):
            c = HG[side][ck]; L.append(paint(prism_x(XC + c[0], XC + c[1], prof), COL['knuckle']))
        e = HG[side]['ear']
        L.append(paint(box(XC + e[0] - 0.2, XC + e[1] + 0.2, kp['base_y'][0], H[0] - 2, LID['top_z'], HG['heel_stop_z']), COL['knuckle']))
    for f in N['fold_feet_detail']:
        L.append(paint(box(f['x'][0], f['x'][1], f['y'][0], f['y'][1], f['z'][0], f['z'][1]), COL['knuckle']))
        if f['rear']: L.append(paint(box(f['x'][0], f['x'][1], f['lip']['y'][0], f['lip']['y'][1], f['z'][1], f['lip']['z'][1]), COL['knuckle']))
    L.append(paint(box(HO['x'][0], HO['x'][1], HO['y'][0], HO['y'][1], LID['top_z'], LID['top_z'] + 0.3), COL['hole']))
    L.append(paint(box(PK['x'][0], PK['x'][1], PK['ramp_front_y'], PK['back_wall_y'], LID['top_z'], LID['top_z'] + 0.3), COL['leg']))
    L.append(paint(box(XC - 125, XC + 125, 0, KO['module_rear_y'], 5, KO['z_min']), COL['module']))   # keys/module, cut to the view
    L.append(paint(box(PI['board_x'][0], PI['board_x'][1], PI['board_y'][0], PI['board_y'][1], PI['board_top_z'] - 1.6, PI['board_top_z']), COL['pi']))
    L.append(paint(box(PI['heatsink']['x'][0], PI['heatsink']['x'][1], PI['heatsink']['y'][0], PI['heatsink']['y'][1], PI['board_top_z'], PI['heatsink']['top_z']), COL['pi']))
    return L

P = N['poses']
def tubes(wpts, r, col):
    out = []
    for a, b in zip(wpts[:-1], wpts[1:]):
        if math.dist(a, b) > 0.5: out.append(paint(trimesh.creation.cylinder(radius=r, segment=[a, b], sections=10), col))
    return out
use = fixed_world() + to_world(cradle_local(), P['cradle_use']) + leg_use() + tubes(N['ribbon']['waypoints'], 2.0, COL['rib']) + tubes(N['power_wire']['waypoints'], 1.0, [194, 24, 91, 255])
fold = fixed_world() + to_world(cradle_local() + leg_stowed_local(), P['cradle_fold'])
sc = trimesh.Scene()
for i, m in enumerate(use): sc.add_geometry(m, node_name=f'use_{i}')
for i, m in enumerate(fold):
    m2 = m.copy(); m2.apply_translation([0, 260.0, 0]); sc.add_geometry(m2, node_name=f'fold_{i}')
sc.export(D / 'preview3d_rev3.glb')

# simple interference probes (vertex sampling): cradle/leg vs lid-fixed parts, and keep-out
def min_y_above(meshes, zmin):
    ys = [v[1] for m in meshes for v in m.vertices if v[2] >= zmin]
    return min(ys)
probe = dict(use_min_y_z_over_module=round(min_y_above(to_world(cradle_local(), P['cradle_use']), KO['z_min']), 2),
             heel_min_y_z_over_module=round(min_y_above(to_world(cradle_local(), P['cradle_heel']), KO['z_min']), 2),
             fold_min_z=round(min(v[2] for m in to_world(cradle_local() + leg_stowed_local(), P['cradle_fold']) for v in m.vertices), 2))

# ---------------- render ----------------
def zrender(meshes, elev, azim, W=900, Hh=640, pad=12):
    """tiny orthographic z-buffer renderer (flat shading) -> RGB image"""
    ev, az = math.radians(elev), math.radians(azim)
    fwd = -np.array([math.cos(ev) * math.cos(az), math.cos(ev) * math.sin(az), math.sin(ev)])     # camera looks along fwd
    right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    V = np.concatenate([m.vertices for m in meshes])
    px, py = V @ right, V @ up
    sc = min((W - 2 * pad) / (px.max() - px.min()), (Hh - 2 * pad) / (py.max() - py.min()))
    ox, oy = px.min(), py.max()
    img = np.ones((Hh, W, 3)); zb = np.full((Hh, W), np.inf)
    L = np.array([0.35, -0.55, 0.75]); L /= np.linalg.norm(L)
    for m in meshes:
        col = np.array(m.visual.face_colors[0, :3], float) / 255
        tri = m.vertices[m.faces]; nrm = m.face_normals
        sx = ((tri @ right) - ox) * sc + pad; sy = (oy - (tri @ up)) * sc + pad; sz = tri @ fwd
        shade = np.clip(0.45 + 0.55 * np.abs(nrm @ L), 0.3, 1.0)
        for k in range(len(tri)):
            x0, x1 = int(max(0, np.floor(sx[k].min()))), int(min(W - 1, np.ceil(sx[k].max())))
            y0, y1 = int(max(0, np.floor(sy[k].min()))), int(min(Hh - 1, np.ceil(sy[k].max())))
            if x1 < x0 or y1 < y0: continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax_, bx_, cx_), (ay_, by_, cy_) = sx[k], sy[k]
            den = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
            if abs(den) < 1e-9: continue
            l1 = ((by_ - cy_) * (gx - cx_) + (cx_ - bx_) * (gy - cy_)) / den
            l2 = ((cy_ - ay_) * (gx - cx_) + (ax_ - cx_) * (gy - cy_)) / den
            l3 = 1 - l1 - l2
            ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            if not ins.any(): continue
            z = l1 * sz[k][0] + l2 * sz[k][1] + l3 * sz[k][2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = ins & (z < sub - 1e-4)
            sub[upd] = z[upd]; img[y0:y1 + 1, x0:x1 + 1][upd] = col * shade[k]
    return img
fig = plt.figure(figsize=(16, 11.5), dpi=110)
views = [(use, 25, -125, '세운 상태 25° — 연주자 쪽 왼쪽 위에서'), (use, 0, 0, '세운 상태 — 옆에서 (왼쪽이 연주자, +x 쪽에서 봄)'),
         (fold, 40, 55, '접은 상태 — 뒤 오른쪽 위에서'), (use, 28, 55, '세운 상태 — 뒤에서 (받침다리, 점검창, 선)')]
for k, (ms, ev_, az_, ttl) in enumerate(views):
    ax = fig.add_subplot(2, 2, k + 1); ax.imshow(zrender(ms, ev_, az_)); ax.set_title(ttl, fontsize=13); ax.axis('off')
fig.suptitle(f"R31 3판 3a 확인용 3D (상자 모형, CAD 아님) · 경첩 y{H[0]} z{H[1]} · 모듈 위 가장 앞 y{probe['heel_min_y_z_over_module']} · 접은 받침 최저 z{probe['fold_min_z']}", fontsize=13)
plt.tight_layout(); fig.savefig(D / 'preview3d_rev3.png'); print('ok', probe)
json.dump(probe, open(D / 'work' / 'preview3d_probe.json', 'w'), indent=1)
