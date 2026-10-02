# Concept drawing (SVG + PNG via headless Chrome) for R31 touchscreen rev 3 (B1 on L2). All numbers from numbers.json.
import json, math, subprocess, time, os
from pathlib import Path
from xml.sax.saxutils import escape
D = Path(__file__).resolve().parent
N = json.load(open(D / 'numbers.json'))
PL = N['placement']; XC = PL['x_centre']; LID = PL['lid']; KO = PL['keepout']
U, F, HL = N['points']['use'], N['points']['fold'], N['points']['heel']
H = N['hinge']['axis_yz']; HG = N['hinge']; LG = N['leg']; CR = N['cradle']; HO = N['hole']; CL = N['clip']; V = N['vents']
CTX = N['context']; S = N['screen']; PI = N['pi5']; RB = N['ribbon']; FO = N['fold']; PK = LG['pocket']; ST = N['stability']; CK = N['checks']; E = N['eye']
UA, WA = HG['axis_cradle_uw']

def Pc(u, w, th):
    t = math.radians(th); du, dw = u - UA, w - WA
    return (H[0] + du * math.sin(t) + dw * math.cos(t), H[1] + du * math.cos(t) - dw * math.sin(t))

W_, HT = 1440, 2070
FONT = "'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif"
C = dict(ink='#1d2530', grey='#7d8796', light='#e9edf2', ply='#e8d3ad', plyline='#9a7a45', lid='#cfe6d4', lidline='#3f8a55',
         scr='#1f5fbf', act='#3d8bff', fold='#5d6b80', red='#d23c3c', rib='#d97000', leg='#7a4bb7', snd='#15907f', eye='#b03a8f',
         pi='#2e7d32', pw='#c2185b', body='#9fb6d9')
out = []
def add(s): out.append(s)
def kw2a(kw): return ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
def txt(x, y, s, size=13, color=None, anchor='start', weight='normal', halo=True):
    st = ' style="paint-order:stroke;stroke:#ffffff;stroke-width:3.2px;stroke-linejoin:round"' if halo else ''
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color or C["ink"]}" text-anchor="{anchor}" font-weight="{weight}"{st}>{escape(s)}</text>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_}" height="{HT}" viewBox="0 0 {W_} {HT}" font-family="{FONT}">')
add(f'<rect width="{W_}" height="{HT}" fill="#ffffff"/>')
add('<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    f'<line x1="0" y1="0" x2="0" y2="8" stroke="{C["red"]}" stroke-width="1.3" opacity="0.5"/></pattern>'
    f'<marker id="arrE" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{C["eye"]}"/></marker>'
    f'<marker id="arrR" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{C["rib"]}"/></marker>'
    '<clipPath id="clipA"><rect x="40" y="112" width="1370" height="636"/></clipPath>'
    '<clipPath id="clipI"><rect x="1062" y="146" width="340" height="180"/></clipPath>'
    '<clipPath id="clipB"><rect x="30" y="826" width="1000" height="590"/></clipPath>'
    '<clipPath id="clipZ"><rect x="1044" y="826" width="384" height="300"/></clipPath></defs>')
src = '확정 L2 값' if PL['source_is_final'] else 'L2 임시값'
txt(40, 40, 'Toccata R31 — 터치스크린 B1 (Waveshare 7-DSI-TOUCH-C) 설치 개념도 · 수정 3판 3a · L2 뒷바', 24, weight='bold')
txt(40, 64, f'좌표(mm): x = 건반 가로(A0 왼쪽 = 0), y = 흰건반 앞끝에서 뒤로, z = 책상에서 위로. 모든 수치는 numbers.json(수정 3판, {src})에서 읽음', 13, C['grey'])

# ================= A. side section =================
s = 2.9; YA0, ZA1 = -40.0, 215.0; AX0, AYT = 60.0, 112.0
def A(y, z): return (AX0 + (y - YA0) * s, AYT + (ZA1 - z) * s)
def poly(pts, **kw): add(f'<polygon points="{" ".join(f"{A(*p)[0]:.1f},{A(*p)[1]:.1f}" for p in pts)}" {kw2a(kw)}/>')
def pline(pts, **kw): add(f'<polyline points="{" ".join(f"{A(*p)[0]:.1f},{A(*p)[1]:.1f}" for p in pts)}" fill="none" {kw2a(kw)}/>')
def line(p, q, **kw):
    a, b = A(*p), A(*q); add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" {kw2a(kw)}/>')
def circ(p, r, **kw):
    a = A(*p); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="{r}" {kw2a(kw)}/>')
def T(p, sx, dx=0, dy=0, **kw):
    a = A(*p); txt(a[0] + dx, a[1] + dy, sx, **kw)
def label(pt, at, sx, color, anchor='end', size=12, weight='normal'):
    a, b = A(*pt), A(*at)
    add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]+(4 if anchor=="end" else -4):.1f}" y2="{b[1]-4:.1f}" stroke="{color}" stroke-width="0.8"/>')
    add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="2.4" fill="{color}"/>')
    txt(b[0], b[1], sx, size, color, anchor, weight)

txt(40, 100, f'A. 옆 단면 — 화면 가운데(x{XC:g})를 자른 면. 왼쪽이 연주자. 리본·전원선 길(x{HO["x"][0]:.0f}~{HO["x"][1]:.0f})과 Pi는 겹쳐 그림', 17, weight='bold')
add('<g clip-path="url(#clipA)">')
line((YA0, 0), (360, 0), stroke=C['ink'], stroke_width=1.5)
# key module
poly([(0, 5), (KO['module_rear_y'], 5), (KO['module_rear_y'], KO['z_min']), (0, KO['z_min'])], fill=C['light'], stroke=C['grey'], stroke_width=1)
line((0, CTX['white_top_z']), (CTX['key_rear_y'], CTX['white_top_z']), stroke=C['ink'], stroke_width=3)
line((CTX['black_front_y_draw'], CTX['black_top_z']), (CTX['key_rear_y'], CTX['black_top_z']), stroke='#333', stroke_width=6)
# keep-out
poly([(120, KO['z_min']), (KO['y_max'], KO['z_min']), (KO['y_max'], ZA1), (120, ZA1)], fill='url(#hatch)', stroke=C['red'], stroke_width=1.2, stroke_dasharray='5 3')
line((KO['y_max'], KO['z_min']), (KO['y_max'], ZA1), stroke=C['red'], stroke_width=1.6)
# rear bar (centre part)
poly([(LID['y'][0], 5), (PL['rear_face_y'], 5), (PL['rear_face_y'], LID['top_z']), (LID['y'][0], LID['top_z'])], fill=C['ply'], stroke=C['plyline'], stroke_width=1.2, opacity=0.55)
poly([(LID['y'][0] + 3, PL['floor_z']), (PL['rear_face_y'] - 3, PL['floor_z']), (PL['rear_face_y'] - 3, LID['bed_z']), (LID['y'][0] + 3, LID['bed_z'])], fill='#fbf7ee', stroke=C['plyline'], stroke_width=0.8)
poly([(LID['y'][0], LID['top_z'] - LID['plate_t']), (LID['y'][1], LID['top_z'] - LID['plate_t']), (LID['y'][1], LID['top_z']), (LID['y'][0], LID['top_z'])], fill=C['lid'], stroke=C['lidline'], stroke_width=1.5)
for yv in range(int(LID['y'][0]) + 20, int(LID['y'][1]), 25):
    poly([(yv, LID['bed_z']), (yv + 2, LID['bed_z']), (yv + 2, LID['top_z'] - LID['plate_t']), (yv, LID['top_z'] - LID['plate_t'])], fill=C['lid'], stroke=C['lidline'], stroke_width=0.5)
for sl in V['slots'][::2]:
    poly([(sl[2], LID['top_z'] - LID['plate_t']), (sl[3], LID['top_z'] - LID['plate_t']), (sl[3], LID['top_z']), (sl[2], LID['top_z'])], fill='#ffffff', stroke=C['lidline'], stroke_width=0.6)
# hole + wall + clip pad
poly([(HO['y'][0], LID['bed_z']), (HO['y'][1], LID['bed_z']), (HO['y'][1], LID['top_z']), (HO['y'][0], LID['top_z'])], fill='#fff', stroke=C['rib'], stroke_width=1.2)
poly([(CL['pad']['y'][0], LID['bed_z']), (CL['pad']['y'][1], LID['bed_z']), (CL['pad']['y'][1], LID['top_z'] - LID['plate_t']), (CL['pad']['y'][0], LID['top_z'] - LID['plate_t'])], fill='#9fcaa9', stroke=C['lidline'], stroke_width=0.8)
# pocket + block
poly([(PK['block']['y'][0], LID['bed_z']), (PK['block']['y'][1], LID['bed_z']), (PK['block']['y'][1], LID['top_z']), (PK['block']['y'][0], LID['top_z'])], fill='#9fcaa9', stroke=C['lidline'], stroke_width=0.8)
poly([(PK['ramp_front_y'], LID['top_z']), (PK['ramp_end_y'], PK['bottom_z']), (PK['back_wall_y'], PK['bottom_z']), (PK['back_wall_y'], LID['top_z'])], fill='#ffffff', stroke=C['leg'], stroke_width=1)
# Pi 5 (side projection)
poly([(PI['board_y'][0], PI['board_top_z'] - 1.6), (PI['board_y'][1], PI['board_top_z'] - 1.6), (PI['board_y'][1], PI['board_top_z']), (PI['board_y'][0], PI['board_top_z'])], fill=C['pi'], stroke=C['pi'])
poly([(PI['heatsink']['y'][0], PI['board_top_z']), (PI['heatsink']['y'][1], PI['board_top_z']), (PI['heatsink']['y'][1], PI['heatsink']['top_z']), (PI['heatsink']['y'][0], PI['heatsink']['top_z'])], fill='#9bb59c', stroke=C['pi'], stroke_width=0.6)
poly([(PI['disp1']['y'][0], PI['board_top_z']), (PI['disp1']['y'][1], PI['board_top_z']), (PI['disp1']['y'][1], PI['board_top_z'] + 1.8), (PI['disp1']['y'][0], PI['board_top_z'] + 1.8)], fill='#6d4c41')
line((PI['gpio_pin2'][1], PI['board_top_z']), (PI['gpio_pin2'][1], PI['gpio_top_z']), stroke='#444', stroke_width=3)
kz = PL['keepout_zones']
poly([(kz['dsi']['y'][0], kz['dsi_z'][0]), (kz['dsi']['y'][1], kz['dsi_z'][0]), (kz['dsi']['y'][1], kz['dsi_z'][1]), (kz['dsi']['y'][0], kz['dsi_z'][1])], fill='none', stroke=C['rib'], stroke_width=0.8, stroke_dasharray='2 2')
# speaker-top line
line((150, PL['speaker_top_z']), (360, PL['speaker_top_z']), stroke=C['grey'], stroke_width=1, stroke_dasharray='3 4')
# ribbon (side projection)
th = 25.0; gap_w = (CR['w_screen_back'] + CR['plate'][0]) / 2
fs = CR['fold_square']; zr = RB['z_run']; mouth = PI['disp1']['mouth']; hole_yc = (HO['y'][0] + HO['y'][1]) / 2
rib_pts = [Pc(S['fpc']['pin_u_centre'], gap_w, th), Pc(CR['u'][0], gap_w, th)]
ex = rib_pts[-1]
loop = [(ex[0] + (hole_yc - ex[0]) * k + math.sin(k * math.pi) * 4.0, ex[1] + (LID['top_z'] + 1 - ex[1]) * k) for k in [i / 10 for i in range(11)]]
rib_pts += loop + [(p[1], p[2]) for p in RB['waypoints']]
pline(rib_pts, stroke=C['rib'], stroke_width=2.6)
# power wire
pw_pts = [Pc(sum(S['pwr']['u']) / 2, gap_w, th), Pc(CR['u'][0], gap_w + 0.6, th)] + [(p[0] + 0.8, p[1]) for p in loop] + [(p[1] + 0.8, p[2]) for p in N['power_wire']['waypoints']]
pline(pw_pts, stroke=C['pw'], stroke_width=1.4, stroke_dasharray='5 3')
# fold feet (behind the section plane) + lip
for f in N['fold_feet_detail'][:2]:
    poly([(f['y'][0], f['z'][0]), (f['y'][1], f['z'][0]), (f['y'][1], f['z'][1]), (f['y'][0], f['z'][1])], fill='#9fcaa9', stroke=C['lidline'], stroke_width=0.8, opacity=0.6)
    if f['rear']:
        poly([(f['lip']['y'][0], f['z'][1]), (f['lip']['y'][1], f['z'][1]), (f['lip']['y'][1], f['lip']['z'][1]), (f['lip']['y'][0], f['lip']['z'][1])], fill='#9fcaa9', stroke=C['lidline'], stroke_width=0.8)
# folded cradle (dashed) + stowed leg
cu0, cu1, cw0, cw1 = CR['u'][0], CR['u'][1], CR['w'][0], CR['w'][1]
poly([Pc(cu0, cw0, 90), Pc(cu1, cw0, 90), Pc(cu1, WA, 90), Pc(cu0, WA, 90)], fill='none', stroke=C['fold'], stroke_width=1.8, stroke_dasharray='7 4')
line(Pc(cu0 + 2, cw1, 90), Pc(cu1, cw1, 90), stroke=C['fold'], stroke_width=1, stroke_dasharray='3 3')
poly([(LG['fold_leg_y'][0], LG['fold_leg_z'][0]), (LG['fold_leg_y'][1], LG['fold_leg_z'][0]), (LG['fold_leg_y'][1], LG['fold_leg_z'][1]), (LG['fold_leg_y'][0], LG['fold_leg_z'][1])],
     fill='none', stroke=C['leg'], stroke_width=1.2, stroke_dasharray='4 3')
# standing cradle, screen body, glass, active
poly([Pc(cu0, cw0, th), Pc(cu1, cw0, th), Pc(cu1, cw1, th), Pc(cu0 + 2, cw1, th), Pc(cu0, cw1 - 2, th)], fill='#dfe9fb', stroke=C['scr'], stroke_width=1.8)
poly([Pc(0, 0, th), Pc(S['glass'][1], 0, th), Pc(S['glass'][1], S['body'], th), Pc(0, S['body'], th)], fill=C['body'], stroke='#0b2a55', stroke_width=0.8)
line(Pc(0, 0, th), Pc(S['glass'][1], 0, th), stroke='#0b2a55', stroke_width=2.5)
line(Pc(S['active_u'][0], 0, th), Pc(S['active_u'][1], 0, th), stroke=C['act'], stroke_width=6)
line(Pc(cu0, CR['plate'][1], th), Pc(cu1, CR['plate'][1], th), stroke=C['scr'], stroke_width=0.8, stroke_dasharray='2 2')
poly([Pc(cu0, cw0, 22), Pc(cu1, cw0, 22), Pc(cu1, cw1, 22), Pc(cu0, cw1, 22)], fill='none', stroke=C['scr'], stroke_width=0.8, stroke_dasharray='2 3')
# knuckle + heel stop + ear
kp = HG['knuckle_profile']
poly([(kp['base_y'][0], LID['top_z']), (kp['base_y'][1], LID['top_z']), (kp['at_axis_y'][1], H[1]), (kp['at_axis_y'][0], H[1])], fill='#9fcaa9', stroke=C['lidline'], stroke_width=1)
circ(tuple(H), HG['cheek_R'] * s, fill='#9fcaa9', stroke=C['lidline'], stroke_width=1)
poly([(kp['base_y'][0], LID['top_z']), (H[0] - 2, LID['top_z']), (H[0] - 2, HG['heel_stop_z']), (kp['base_y'][0], HG['heel_stop_z'])], fill='#6fae80', stroke=C['lidline'], stroke_width=0.8)
def ear_world(thd):
    # ear side outline = numbers.json cradle.ear.profile_uw (hub + bottom attachment + heel point only), placed at tilt thd
    return [Pc(u_, w_, thd) for (u_, w_) in CR['ear']['profile_uw']]
EAR = ear_world(th)
poly(EAR, fill=C['scr'], opacity=0.55, stroke=C['scr'], stroke_width=1)
circ(tuple(H), 2.2, fill=C['ink'])
# leg (use)
pv, tp = LG['pivot_yz'], LG['tip_yz']
line(tuple(pv), tuple(tp), stroke=C['leg'], stroke_width=6 * s * 0.9)
circ(tuple(tp), 3 * s, fill=C['leg'])
circ(tuple(pv), 3.8 * s, fill='#c9b3e6', stroke=C['leg'])
circ(tuple(pv), 2.2, fill=C['ink'])
# 25 deg arc
gb = U['glass_bottom']; R = 30; t = math.radians(25)
a0 = A(gb[0], gb[1] + R); a1 = A(gb[0] + R * math.sin(t), gb[1] + R * math.cos(t))
line(tuple(gb), (gb[0], gb[1] + 40), stroke=C['ink'], stroke_width=0.8, stroke_dasharray='3 3')
add(f'<path d="M{a0[0]:.1f},{a0[1]:.1f} A{R*s:.1f},{R*s:.1f} 0 0,1 {a1[0]:.1f},{a1[1]:.1f}" fill="none" stroke="{C["ink"]}" stroke-width="1.2"/>')
EY = tuple(E['eye'])
line(EY, tuple(U['act_centre']), stroke=C['eye'], stroke_width=1.6, marker_end='url(#arrE)')
line(EY, tuple(U['act_bottom']), stroke=C['eye'], stroke_width=1, stroke_dasharray='5 4')
circ((KO['module_rear_y'], E['sightline_z_at_module']), 3.2, fill=C['eye'])
circ((KO['module_rear_y'], E['sightline_centre_z_at_module']), 3.2, fill=C['eye'])
add('</g>')
# ---- A labels ----
T((2, CTX['white_top_z']), f"흰건반 윗면 z{CTX['white_top_z']}", dy=-7, size=12)
T((CTX['black_front_y_draw'] + 2, CTX['black_top_z']), f"흑건 z{CTX['black_top_z']}", dy=-9, size=12)
T((2, KO['z_min']), f'옥타브 모듈 틀 z{KO["z_min"]} · 뒤끝 y{KO["module_rear_y"]:g}', dy=-6, size=12, color=C['grey'])
T((122, 212), f'모듈 위 금지', dy=4, size=13, color=C['red'], weight='bold')
T((122, 212), f'y≤{KO["y_max"]:g}, z≥{KO["z_min"]}', dy=20, size=12, color=C['red'], weight='bold')
T((122, 212), '(모듈을 위로 뺌)', dy=36, size=11, color=C['red'])
T((-38, 212), f'↖ 연주자 눈(추정) y−350 z450에서 오는 시선', dy=4, size=12, color=C['eye'], weight='bold')
T((-38, 212), f'보이는 영역 가운데까지 아래로 {E["angle_to_centre"]}° (화면 25°와 {E["tilt_diff"]}° 차이)', dy=22, size=12, color=C['eye'])
T((-38, 212), f'거리 {E["dist_to_centre"]:.0f} mm · 눈 범위를 넓혀도 {E["angle_range"][0]}~{E["angle_range"][1]}°', dy=40, size=12, color=C['eye'])
T((-38, 212), f'y{KO["module_rear_y"]:g}에서 시선 높이: 가운데로 z{E["sightline_centre_z_at_module"]}, 보이는 영역 아래 끝으로 z{E["sightline_z_at_module"]}(점선)', dy=58, size=11, color=C['eye'])
LX = 108
label(tuple(U['cr_top_front']), (LX, 196), f'받침 윗끝 y{U["cr_top_front"][0]} z{U["cr_top_front"][1]}', C['scr'])
label(tuple(U['act_centre']), (LX, 176), f'보이는 영역 가운데 y{U["act_centre"][0]} z{U["act_centre"][1]}', '#0b2a55', weight='bold')
label(tuple(U['act_top']), (LX, 160), f'보이는 영역 z{U["act_bottom"][1]}~{U["act_top"][1]} (154.58×86.42)', C['act'])
label(tuple(U['glass_bottom']), (LX, 132), f'유리 아래 y{U["glass_bottom"][0]} z{U["glass_bottom"][1]}', '#0b2a55')
label(tuple(HL['cr_bot_front']), (LX, 116), f'가장 앞 y{N["all_min_y"]} (22°, 금지선 y{KO["y_max"]:g}보다 {CK["keepout_margin"]} 뒤)', C['red'], weight='bold')
T((gb[0] + 2, gb[1] + 34), '25°', size=14, weight='bold')
label(tuple(HG['heel_contact_yz']), (LX, 100), f'뒤꿈치 멈춤 블록 z{HG["heel_stop_z"]}: 22°에서 닿음 (25°에서 {HG["heel_gap_at_25"]} mm)', C['scr'])
label(tuple(H), (LX, 86), f'경첩 축 y{H[0]} z{H[1]} (M3×20, x{HG["left_x"][0]:.0f}~{HG["left_x"][1]:.0f} · x{HG["right_x"][0]:.0f}~{HG["right_x"][1]:.0f})', C['lidline'], weight='bold')
label((hole_yc, LID['top_z'] - 2), (LX, 64), f'리본·전원선 구멍 y{HO["y"][0]}~{HO["y"][1]} (x{HO["x"][0]:.0f}~{HO["x"][1]:.0f}, 22×6)', C['rib'])
label(((CL['pad']['y'][0] + CL['pad']['y'][1]) / 2, LID['bed_z']), (LX, 30), f'리본 클립 덩어리 y{CL["pad"]["y"][0]}~{CL["pad"]["y"][1]} (핀 Ø3 두 개)', C['lidline'])
lm = ((pv[0] + tp[0]) / 2, (pv[1] + tp[1]) / 2)
label(lm, (282, 122), f'받침다리 {LG["length"]:g} mm (10×6), 받침 뒤 u{LG["pivot_cradle_uw"][0]:g}에 경첩, {LG["angle_deg"]}°', C['leg'], anchor='start', weight='bold')
T((282, 122), f'발끝 y{LG["tip_yz"][0]} z{LG["tip_yz"][1]} → 주머니(경사 y{PK["ramp_front_y"]}, 뒷벽 y{PK["back_wall_y"]})', dy=16, size=11, color=C['leg'])
T((282, 122), f'넣고 뺄 때는 화면을 22°(뒤꿈치)에 댐 (25°에서는 뒷벽 모서리 {-LG["swing"]["at_25"]["worst_overlap"]:g} 긁음)', dy=31, size=11, color=C['leg'])
T((358, PL['speaker_top_z']), f'스피커 윗면 z{PL["speaker_top_z"]:g} (접은 높이 한계)', dy=-5, size=11, color=C['grey'], anchor='end')
# fold labels start right of the use-pose leg (leg y at this z + margin), so the leg never crosses them
_zf = LG['pivot_yz'][1] - 9.0
_yf = LG['pivot_yz'][0] + (LG['pivot_yz'][1] - _zf + 6.0) / math.tan(math.radians(LG['angle_deg'])) + 8.0
T((_yf, _zf), f'접은 화면(앞면 위) z{FO["rib_plane_z"]}~{FO["top_z"]}, y{FO["y"][0]}~{FO["y"][1]} (뒤끝까지 {FO["rear_margin"]})', size=11, color=C['fold'], weight='bold')
T((_yf, _zf), f'접은 다리 z{LG["fold_leg_z"][0]}~{LG["fold_leg_z"][1]} · 받침 발 16×16×{FO["feet_h"]:g}, 뒤 발에 턱', dy=15, size=11, color=C['fold'])
T((LID['y'][1] + 2, LID['top_z']), f'가운데 뚜껑', dx=4, dy=4, size=12, color=C['lidline'], weight='bold')
T((LID['y'][1] + 2, LID['top_z']), f'z{LID["top_z"]}, 판 {LID["plate_t"]:g}', dx=4, dy=19, size=11, color=C['lidline'])
T((LID['y'][1] + 2, LID['top_z']), f'리브 밑 z{LID["bed_z"]}', dx=4, dy=33, size=11, color=C['lidline'])
T((PI['board_y'][0], PI['board_top_z'] - 1.6), f'Pi 5 (L2 y{PI["board_y"][0]:g}~{PI["board_y"][1]:g}) · CAM/DISP 1 x{PI["disp1"]["x"][0]} y{PI["disp1"]["y"][0]}~{PI["disp1"]["y"][1]}', dy=15, size=11, color=C['pi'])
label((RB['waypoints'][3][1], 45), (300, 46), f'DSI 리본 300 mm ({RB["ffc_type"][0]}형), 필요 약 {RB["total"]:.0f} mm', C['rib'], anchor='start', weight='bold')
T((300, 46), f'뚜껑 밑 +y → 45° 접기 → −x → 기둥 x{RB["waypoints"][3][0]:g} 아래 → HDMI 위 → 입구 · 분홍 = 전원선', dy=15, size=11, color=C['pw'])
for yv in [0, KO['module_rear_y'], KO['y_max'], H[0], LID['y'][1]]:
    a = A(yv, 0); add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{a[0]:.1f}" y2="{a[1]+6:.1f}" stroke="{C["ink"]}"/>')
    txt(a[0], a[1] + 20 + (12 if yv in (KO['y_max'],) else 0), f'y{yv:g}', 11, C['grey'], 'middle')
T((YA0, 0), '책상 z0', dx=4, dy=16, size=12, color=C['grey'])

# ---- inset: hinge detail ----
IX, IY, k = 1066, 148, 6.0
Y0 = H[0] - 14
def I(y, z): return (IX + (y - Y0) * k, IY + (98 - z) * k)
def Ipoly(pts, **kw): add(f'<polygon points="{" ".join(f"{I(*p)[0]:.1f},{I(*p)[1]:.1f}" for p in pts)}" {kw2a(kw)}/>')
add(f'<rect x="1058" y="122" width="350" height="248" fill="#fafcff" stroke="{C["grey"]}" rx="6"/>')
txt(1066, 140, '경첩 확대 — 25° (옆에서)', 13, weight='bold')
add('<g clip-path="url(#clipI)">')
Ipoly([(Y0 - 2, LID['top_z']), (Y0 + 70, LID['top_z']), (Y0 + 70, LID['top_z'] - 3), (Y0 - 2, LID['top_z'] - 3)], fill=C['lid'], stroke=C['lidline'])
Ipoly([(KO['y_max'] - 20, 60), (KO['y_max'], 60), (KO['y_max'], 110), (KO['y_max'] - 20, 110)], fill='url(#hatch)', stroke=C['red'], stroke_dasharray='4 3')
Ipoly([(kp['base_y'][0], LID['top_z']), (kp['base_y'][1], LID['top_z']), (kp['at_axis_y'][1], H[1]), (kp['at_axis_y'][0], H[1])], fill='#9fcaa9', stroke=C['lidline'])
c = I(*H); add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{HG["cheek_R"]*k:.1f}" fill="#9fcaa9" stroke="{C["lidline"]}"/>')
Ipoly([(kp['base_y'][0], LID['top_z']), (H[0] - 2, LID['top_z']), (H[0] - 2, HG['heel_stop_z']), (kp['base_y'][0], HG['heel_stop_z'])], fill='#6fae80', stroke=C['lidline'])
Ipoly([Pc(cu0, cw0, th), Pc(cu0 + 30, cw0, th), Pc(cu0 + 30, cw1, th), Pc(cu0 + 2, cw1, th), Pc(cu0, cw1 - 2, th)], fill='#dfe9fb', stroke=C['scr'], stroke_width=1.5)
Ipoly([Pc(0, 0, th), Pc(28, 0, th), Pc(28, S['body'], th), Pc(0, S['body'], th)], fill=C['body'], stroke='#0b2a55')
Ipoly(EAR, fill=C['scr'], opacity=0.55, stroke=C['scr'])
add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{1.65*k:.1f}" fill="#fff" stroke="{C["ink"]}" stroke-width="1.4"/>')
add('</g>')
p = I(*H)
txt(p[0] + 46, p[1] - 34, f'축 y{H[0]} z{H[1]}, 구멍 Ø3.3', 11)
txt(p[0] + 46, p[1] - 20, f'볼 R{HG["cheek_R"]}, 귀 축살 R{HG["ear_hub_R"]}', 11)
txt(1066, 344, f'금지선 y{KO["y_max"]:g} ← 가장 앞 y{N["all_min_y"]} (22° 받침 앞 아래 모서리)', 11, C['red'], 'start', 'bold')
txt(1066, 360, f'멈춤 블록 z{HG["heel_stop_z"]} (뚜껑+{HG["heel_stop_h"]:g}), 뒤꿈치 R{HG["heel_R"]}', 11, C['scr'])

# ================= B. plan =================
sb = 0.76; BX0, BYT = 44.0, 832.0
def B(x, y): return (BX0 + (x + 30) * sb, BYT + (370 - y) * sb)
def Brect(x0, y0, x1, y1, **kw):
    a, b = B(x0, y1), B(x1, y0); add(f'<rect x="{a[0]:.1f}" y="{a[1]:.1f}" width="{b[0]-a[0]:.1f}" height="{b[1]-a[1]:.1f}" {kw2a(kw)}/>')
def Bline(p, q, **kw):
    a, b = B(*p), B(*q); add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" {kw2a(kw)}/>')
def BT(p, sx, dx=0, dy=0, **kw):
    a = B(*p); txt(a[0] + dx, a[1] + dy, sx, **kw)
txt(40, 800, 'B. 위에서 본 평면 — 아래쪽이 연주자. 소리 길 4개, 화면 자리', 17, weight='bold')
add('<g clip-path="url(#clipB)">')
KX = CTX['key_x']
Brect(KX[0], 0, KX[1], CTX['key_rear_y'], fill=C['light'], stroke=C['grey'])
Brect(KX[0], CTX['key_rear_y'], KX[1], KO['module_rear_y'], fill=C['light'], stroke=C['grey'])
Brect(PL['body_x'][0], PL['keepout']['rear_bar_front_y'], PL['body_x'][1], PL['rear_face_y'], fill=C['ply'], stroke=C['plyline'], opacity=0.8)
Brect(CTX['O4_x'][0], 0, CTX['O4_x'][1], KO['module_rear_y'], fill='none', stroke='#2b6cb0', stroke_width=2)
BT((CTX['O4_x'][0] + 4, KO['module_rear_y'] / 2), 'O4 모듈', size=12, color='#2b6cb0', weight='bold')
BT((KX[0] + 10, CTX['key_rear_y'] * 0.75), f"건반 88 (x{KX[0]:g}~{KX[1]:g}) · 모듈 뒤끝 y{KO['module_rear_y']:g}", size=12, color=C['grey'])
for sp in PL['speakers_plan']:
    a = B(*sp); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="{47*sb:.1f}" fill="#fff" stroke="{C["plyline"]}"/><circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="4" fill="{C["plyline"]}"/>')
BT((PL['body_x'][0] + 2, PL['rear_face_y']), f"L2 뒷바 y{PL['keepout']['rear_bar_front_y']:g}~{PL['rear_face_y']:g} (스피커 양끝, 콘 자리는 추정)", dy=-6, size=12, color=C['plyline'])
Brect(LID['x'][0], LID['y'][0], LID['x'][1], LID['y'][1], fill=C['lid'], stroke=C['lidline'], stroke_width=1.5)
Brect(CR['x'][0], FO['y'][0], CR['x'][1], FO['y'][1], fill='none', stroke=C['fold'], stroke_width=1.5, stroke_dasharray='6 4')
Brect(CR['x'][0], N['all_min_y'], CR['x'][1], U['cr_top_rib'][0], fill='#dfe9fb', stroke=C['scr'], stroke_width=1.5, opacity=0.9)
Brect(LG['x'][0], LG['pivot_yz'][0], LG['x'][1], LG['tip_yz'][0], fill=C['leg'], opacity=0.85)
BT((LID['x'][0], LID['y'][1]), f'가운데 뚜껑 x{LID["x"][0]:g}~{LID["x"][1]:g}', dy=-6, size=12, color=C['lidline'], weight='bold')
Bline((KX[0], KO['y_max']), (KX[1], KO['y_max']), stroke=C['red'], stroke_width=1.2, stroke_dasharray='5 3')
BT((740, KO['y_max']), f'모듈 위 금지선 y{KO["y_max"]:g}', dy=14, size=11, color=C['red'], weight='bold')
Bline((KX[0], CTX['sensor_y']), (KX[1], CTX['sensor_y']), stroke='#99994d', stroke_dasharray='2 4')
BT((KX[0] + 10, CTX['sensor_y']), f'홀센서 줄 y≈{CTX["sensor_y"]:g} → 화면 가장 앞까지 {N["sensor_gap"]:.0f} mm', dy=14, size=11, color='#77772f')
hx, hy = B(CTX['player_x'], CTX['eye'][0]); add(f'<ellipse cx="{hx:.1f}" cy="{hy:.1f}" rx="{70*sb:.1f}" ry="{80*sb:.1f}" fill="#f6e3ee" stroke="{C["eye"]}"/>')
txt(hx, hy + 5, f"연주자 (x{CTX['player_x']:g})", 12, C['eye'], 'middle', 'bold')
for pth in N['paths']:
    Bline(tuple(pth['src']), tuple(pth['ear']), stroke=C['snd'], stroke_width=1.6, stroke_dasharray='8 4')
BT((-20, -150), f'소리 길 4개(콘 → 두 귀): 화면에서 {CK["sound_paths_min"]:.0f} mm 이상 떨어짐', size=12, color=C['snd'], weight='bold')
Bline((CTX['O4_white_centre_x'], -30), (CTX['O4_white_centre_x'], 0), stroke='#2b6cb0'); Bline((XC, -30), (XC, N['all_min_y']), stroke='#2b6cb0', stroke_dasharray='2 2')
BT((XC + 6, -40), f'화면 가운데 x{XC:g} ↔ O4 가운데 x{CTX["O4_white_centre_x"]}: {abs(N["O4"]["offset"])} mm', size=11, color='#2b6cb0')
add('</g>')
for xv in [KX[0], LID['x'][0], LID['x'][1], KX[1]]:
    a = B(xv, 370); txt(a[0], a[1] - 4, f'x{xv:g}', 11, C['grey'], 'middle')

# ---- zoom of the lid (plan) ----
zs = 1.6; ZX0, ZYT = 1050.0, 838.0; zx0, zy1 = LID['x'][0] - 6, LID['y'][1] + 4
def Z(x, y): return (ZX0 + (x - zx0) * zs, ZYT + (zy1 - y) * zs)
def Zrect(x0, y0, x1, y1, **kw):
    a, b = Z(x0, y1), Z(x1, y0); add(f'<rect x="{a[0]:.1f}" y="{a[1]:.1f}" width="{b[0]-a[0]:.1f}" height="{b[1]-a[1]:.1f}" {kw2a(kw)}/>')
def Zpl(pts, **kw): add(f'<polyline points="{" ".join(f"{Z(*p)[0]:.1f},{Z(*p)[1]:.1f}" for p in pts)}" fill="none" {kw2a(kw)}/>')
txt(1044, 818, '뚜껑 확대 (위에서)', 14, weight='bold')
add('<g clip-path="url(#clipZ)">')
Zrect(LID['x'][0], LID['y'][0], LID['x'][1], LID['y'][1], fill=C['lid'], stroke=C['lidline'], stroke_width=1.5)
Zrect(zx0 - 5, KO['y_max'] - 20, LID['x'][1] + 20, KO['y_max'], fill='url(#hatch)', stroke=C['red'], stroke_dasharray='4 3')
for sl in V['slots']:
    Zrect(sl[0], sl[2], sl[1], sl[3], fill='#aad3b4', stroke='none')
Zrect(kz['dsi']['x'][0], kz['dsi']['y'][0], kz['dsi']['x'][1], kz['dsi']['y'][1], fill='none', stroke=C['rib'], stroke_dasharray='2 2')
Zrect(PI['board_x'][0], PI['board_y'][0], PI['board_x'][1], PI['board_y'][1], fill='none', stroke=C['pi'], stroke_width=1.2, stroke_dasharray='4 3')
Zrect(PI['disp1']['x'][0], PI['disp1']['y'][0], PI['disp1']['x'][1], PI['disp1']['y'][1], fill='#6d4c41')
Zrect(PI['disp0']['x'][0], PI['disp0']['y'][0], PI['disp0']['x'][1], PI['disp0']['y'][1], fill='#a1887f')
a = Z(*PI['gpio_pin2']); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="3" fill="{C["pw"]}"/>')
a = Z(*PI['gpio_pin6']); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="3" fill="{C["ink"]}"/>')
for f in N['fold_feet_detail']:
    Zrect(f['x'][0], f['y'][0], f['x'][1], f['y'][1], fill='#9fcaa9', stroke=C['lidline'])
    if f['rear']: Zrect(f['x'][0], f['lip']['y'][0], f['x'][1], f['lip']['y'][1], fill=C['lidline'], stroke='none')
for side in ('left_x', 'right_x'):
    Zrect(HG[side][0], HG['knuckle_profile']['base_y'][0], HG[side][1], HG['knuckle_profile']['base_y'][1], fill='#6fae80', stroke=C['lidline'])
Zrect(CL['pad']['x'][0], CL['pad']['y'][0], CL['pad']['x'][1], CL['pad']['y'][1], fill='none', stroke=C['lidline'], stroke_dasharray='3 2')
for pn in CL['pins']:
    a = Z(*pn); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="2.6" fill="#fff" stroke="{C["lidline"]}"/>')
Zrect(HO['x'][0], HO['y'][0], HO['x'][1], HO['y'][1], fill=C['rib'])
Zrect(PK['x'][0], PK['ramp_front_y'], PK['x'][1], PK['back_wall_y'], fill='#fff', stroke=C['leg'], stroke_width=1.3)
Zrect(CR['x'][0], FO['y'][0], CR['x'][1], FO['y'][1], fill='none', stroke=C['fold'], stroke_width=1.4, stroke_dasharray='6 4')
Zrect(CR['x'][0], N['all_min_y'], CR['x'][1], U['cr_top_rib'][0], fill='#dfe9fb', stroke=C['scr'], stroke_width=1.6, opacity=0.75)
Zrect(LG['x'][0], LG['pivot_yz'][0], LG['x'][1], LG['tip_yz'][0], fill=C['leg'], opacity=0.85)
hxc = (HO['x'][0] + HO['x'][1]) / 2
Zpl([(p[0], p[1]) for p in RB['waypoints']][1:], stroke=C['rib'], stroke_width=3.4, marker_end='url(#arrR)')
Zpl([(p[0], p[1]) for p in N['power_wire']['waypoints']], stroke=C['pw'], stroke_width=1.4, stroke_dasharray='4 3')
for p_ in [(xs_, ys_) for xs_ in PL['lid_screw']['x'] for ys_ in PL['lid_screw']['y']]:
    a = Z(*p_); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="4" fill="#fff" stroke="{C["ink"]}" stroke-width="1.4"/>')
add('</g>')
zl = [('경첩 받침 2 + 멈춤 블록', '#6fae80'), (f'구멍 22×6 x{HO["x"][0]:.0f}~{HO["x"][1]:.0f}', C['rib']), ('받침 발 16×16×5 (뒤 발 턱)', '#9fcaa9'),
      (f'다리 주머니 y{PK["ramp_front_y"]:.0f}~{PK["back_wall_y"]:.0f}', C['leg']), ('Pi 5 (L2 확정) · DISP1 · GPIO 2/6', C['pi']),
      ('세운 화면(파랑) · 접은 화면(점선)', C['scr']), ('배기 슬롯 · 클립 덩어리(점선) · 뚜껑 나사(흰 원)', C['lidline']), ('리본 길(주황) · 전원선(분홍) · 리본 기둥(점선)', C['rib'])]
for i, (sx, col) in enumerate(zl):
    yy = 1142 + i * 17
    add(f'<rect x="1050" y="{yy-10}" width="12" height="10" fill="{col}"/>'); txt(1068, yy, sx, 11)
st = N['stability']

# ================= C. cradle, seen from the front through the screen =================
cs = 3.4; CX0, CYB = 80.0, 1900.0
def Cp(xr, u): return (CX0 + (xr - CR['xr'][0]) * cs, CYB - (u - CR['u'][0]) * cs)
def Crect(x0, u0, x1, u1, **kw):
    a, b = Cp(x0, u1), Cp(x1, u0); add(f'<rect x="{a[0]:.1f}" y="{a[1]:.1f}" width="{b[0]-a[0]:.1f}" height="{b[1]-a[1]:.1f}" {kw2a(kw)}/>')
def Cc(xr, u, r, **kw):
    a = Cp(xr, u); add(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="{r*cs:.1f}" {kw2a(kw)}/>')
def Cpl(pts, **kw): add(f'<polyline points="{" ".join(f"{Cp(*p)[0]:.1f},{Cp(*p)[1]:.1f}" for p in pts)}" fill="none" {kw2a(kw)}/>')
def CT(xr, u, sx, dx=0, dy=0, **kw):
    a = Cp(xr, u); txt(a[0] + dx, a[1] + dy, sx, **kw)
txt(40, 1476, f'C. 화면 받침 — 앞에서 투시해 본 모습 (xr = x − {XC:g}, u = 유리 아래 끝에서 위로). 화면 뒤 부품 + 받침 뒤 부품을 겹쳐 그림', 17, weight='bold')
Crect(CR['xr'][0], CR['u'][0], CR['xr'][1], CR['u'][1], fill='#dfe9fb', stroke=C['scr'], stroke_width=2)
Crect(-S['glass'][0] / 2, 0, S['glass'][0] / 2, S['glass'][1], fill='none', stroke='#0b2a55', stroke_width=1.2, stroke_dasharray='5 3')
Crect(S['active_x'][0] - XC, S['active_u'][0], S['active_x'][1] - XC, S['active_u'][1], fill=C['act'], opacity=0.12, stroke='none')
Crect(S['emboss']['xr'][0], S['emboss']['u'][0], S['emboss']['xr'][1], S['emboss']['u'][1], fill='#c9d3e3', stroke=C['grey'], stroke_dasharray='3 2')
Crect(S['window']['xr'][0], S['window']['u'][0], S['window']['xr'][1], S['window']['u'][1], fill='#eef0f3', stroke=C['grey'])
ins = CR['insp']
Crect(ins['xr'][0], ins['u'][0], ins['xr'][1], ins['u'][1], fill='none', stroke=C['ink'], stroke_width=1.6)
Crect(S['fpc']['xr'][0], S['fpc']['u'][0], S['fpc']['xr'][1], S['fpc']['u'][1], fill='#ffffff', stroke='#1e5aa8', stroke_width=1.4)
Crect(S['pwr']['xr'][0], S['pwr']['u'][0], S['pwr']['xr'][1], S['pwr']['u'][1], fill='#ffffff', stroke=C['pw'], stroke_width=1.4)
fsq = CR['fold_square']
Crect(fsq['xr'][0], fsq['u'][0], fsq['xr'][1], fsq['u'][1], fill=C['rib'], opacity=0.35, stroke=C['rib'])
Crect(S['fpc']['mouth_xr'], S['fpc']['pin_u_centre'] - 5.85, fsq['xr'][0], S['fpc']['pin_u_centre'] + 5.85, fill=C['rib'], opacity=0.6, stroke='none')
Crect(CR['rib_band_xr'][0], CR['u'][0], CR['rib_band_xr'][1], fsq['u'][0], fill=C['rib'], opacity=0.6, stroke='none')
Cpl([(S['pwr']['mouth_xr'], sum(S['pwr']['u']) / 2), (sum(CR['wire_xr']) / 2, sum(S['pwr']['u']) / 2), (sum(CR['wire_xr']) / 2, CR['u'][0])], stroke=C['pw'], stroke_width=2, stroke_dasharray='5 3')
gr = CR['groove']; Crect(gr['xr'][0], gr['u'][0], gr['xr'][1], gr['u'][1], fill='none', stroke=C['rib'], stroke_width=1.6)
nt = CR['notch']; Crect(nt['xr'][0], nt['u'][0], nt['xr'][1], nt['u'][1], fill='#ffffff', stroke=C['red'], stroke_width=1.6)
Crect(nt['feature_xr'][0], -min(1.0, nt['feature_proud']), nt['feature_xr'][1], 0, fill=C['red'], stroke='none')
hp = CR['hold_pad']; Crect(hp['xr'][0], hp['u'][0], hp['xr'][1], hp['u'][1], fill='none', stroke=C['lidline'], stroke_width=1.2, stroke_dasharray='3 2')
bo = CR['bosses']
for xr_ in bo['xr']:
    for u_ in bo['u']:
        Cc(xr_, u_, bo['d'] / 2, fill='#fff', stroke=C['ink'], stroke_width=1.3); Cc(xr_, u_, bo['cbore_d'] / 2, fill='none', stroke=C['grey'])
for xr_ in S['pi_holes']['xr']:
    for u_ in S['pi_holes']['u']:
        Cc(xr_, u_, 1.4, fill=C['grey'])
for p_ in CR['pads']:
    Crect(p_['xr'][0], p_['u'][0], p_['xr'][1], p_['u'][1], fill='#9fcaa9', opacity=0.6, stroke=C['lidline'])
for wall in LG['channel']['xr_walls']:
    Crect(wall[0], LG['channel']['u'][0], wall[1], LG['channel']['u'][1], fill=C['leg'], opacity=0.25, stroke='none')
Crect(-5, LG['pivot_cradle_uw'][0] - 3, 5, LG['stow_tip_u'], fill='none', stroke=C['leg'], stroke_width=1.4, stroke_dasharray='5 3')
Cc(0, LG['pivot_cradle_uw'][0], LG['clevis']['R'], fill='#c9b3e6', stroke=C['leg'])
for b_ in LG['clip']['xr_bodies']:
    Crect(b_[0], LG['clip']['u'][0], b_[1], LG['clip']['u'][1], fill=C['leg'])
for side in ('left', 'right'):
    e_ = HG[side]['ear']; Crect(e_[0], UA - HG['ear_hub_R'], e_[1], CR['u'][0], fill=C['scr'], opacity=0.55, stroke=C['scr'])
    for ck in ('far_cheek', 'near_cheek'):
        c_ = HG[side][ck]; Crect(c_[0], UA - HG['cheek_R'], c_[1], UA + HG['cheek_R'], fill='#9fcaa9', stroke=C['lidline'], opacity=0.7)
for uu in CR['cross_ribs_u']:
    Cpl([(CR['xr'][0], uu), (CR['xr'][1], uu)], stroke=C['scr'], stroke_width=1, stroke_dasharray='1 3')
# C labels (right side)
CL_X = CX0 + (CR['xr'][1] - CR['xr'][0]) * cs + 16
lines_c = [
 (f'받침 {CR["size"][0]}×{CR["size"][1]}×{CR["size"][2]} (x{CR["x"][0]}~{CR["x"][1]}), 벽 2.0, 유리와 틈 0.3', C['scr'], 'bold'),
 (f'유리 {S["glass"][0]}×{S["glass"][1]} (점선), 보이는 영역 옅은 파랑', '#0b2a55', 'normal'),
 (f'보스 4개 Ø{bo["d"]:g}: xr ±{bo["xr"][1]:g}, u {bo["u"][0]}·{bo["u"][1]} — M2.5×6, 머리 자리 w{bo["seat_w"]:g}, 물림 {bo["engage"]:g}', C['ink'], 'normal'),
 (f'DSI ZIF 22핀 0.5 (흰 네모) xr{S["fpc"]["xr"][0]}~{S["fpc"]["xr"][1]}, u{S["fpc"]["u"][0]}~{S["fpc"]["u"][1]}, 입구 +x', '#1e5aa8', 'normal'),
 (f'MX1.25 2핀 (분홍 네모) xr{S["pwr"]["xr"][0]}~{S["pwr"]["xr"][1]}, u{S["pwr"]["u"][0]}~{S["pwr"]["u"][1]}, 입구 +x', C['pw'], 'normal'),
 (f'점검창(검은 테) xr{ins["xr"][0]:g}~{ins["xr"][1]:g}, u{ins["u"][0]:g}~{ins["u"][1]:g} · 화면 뒤 창(회색)', C['ink'], 'normal'),
 (f'리본(주황): +x {RB["in_cradle_parts"]["screen_exit_to_fold"]:g} → 45° R3 접기 → −u로 내려감 → 아래 홈 xr{gr["xr"][0]}~{gr["xr"][1]}', C['rib'], 'bold'),
 (f'누름 패드(초록 점선) u{hp["u"][0]:g}~{hp["u"][1]:g} · 전원선(분홍 점선) xr{CR["wire_xr"][0]}~{CR["wire_xr"][1]}', C['lidline'], 'normal'),
 (f'뒤 패드 4개 16×16 (초록) · 가운데 볼록판(회색 점선, 높이 약 {S["emboss"]["h"]})', C['lidline'], 'normal'),
 (f'받침다리 걸이 u{LG["pivot_cradle_uw"][0]:g} (보라 원) · 접은 다리(보라 점선) · 클립 턱 u{LG["clip"]["u"][0]:g}~{LG["clip"]["u"][1]:g}', C['leg'], 'normal'),
 (f'경첩 귀(파랑) xr{HG["left"]["ear"][0]}~{HG["left"]["ear"][1]} · {HG["right"]["ear"][0]}~{HG["right"]["ear"][1]}, 볼(초록)', C['scr'], 'normal'),
 (f'가로 리브 u{CR["cross_ribs_u"][0]:g}·u{CR["cross_ribs_u"][1]:g} (점선, 다리 축 u{LG["pivot_cradle_uw"][0]:g} 둘레는 비움), 아래 뒤 모서리 C{CR["rib_relief_at_cheeks"]["chamfer"]:g}', C['scr'], 'normal'),
 (f'아래 벽 홈(빨간 테) xr{CR["notch"]["xr"][0]:g}~{CR["notch"]["xr"][1]:g} 관통: 화면 아래 끝 돌기(빨강) 자리', C['red'], 'bold'),
 (f'뒷판 w{CR["plate"][0]}~{CR["plate"][1]:g}, 리브 w{CR["rib"][0]:g}~{CR["rib"][1]:g}, 축 u{UA:g} w{WA:g}', C['ink'], 'normal'),
]
for i, (sx, col, wt) in enumerate(lines_c):
    txt(CL_X, 1520 + i * 20, sx, 12, col, 'start', wt)
CT(CR['xr'][0], CR['u'][1], '−x (연주자 왼쪽)', dy=-8, size=11, color=C['grey'])
CT(CR['xr'][1], CR['u'][1], '+x', dx=-14, dy=-8, size=11, color=C['grey'])
CT(0, UA - HG['cheek_R'], f'경첩 축 u{UA:g} (아래)', dy=16, size=11, color=C['grey'], anchor='middle')

# ================= D. ribbon route & FFC type =================
DX, DY = 700, 1812
txt(DX, DY, 'D. 리본 종류 정하기 (면이 뒤집히는 곳)', 15, weight='bold')
rp = RB['parts']; under_fold = 'run_x' in rp; RI = RB['route_info']
steps = [
 '① 화면 ZIF에서 +x로 나옴: 접점 면은 화면 쪽(−w)',
 '② 받침 안 45° 접기 1번 → 면 뒤집힘',
 '③ 경첩 고리·뚜껑 구멍: 굽힘만 (뒤집힘 없음)',
 '④ 뚜껑 밑 +y' + (' → 45° 접기(뒤집힘) → −x' if under_fold else '') + ' → 아래 → +x로 굽힘' + (' (HDMI 위)' if 'rests_on' in RI else '') + ' → 입구 (U자 아님)',
 f'⑤ 끝에서 접점 면이 {"위" if RB["end_normal"][2] > 0 else "아래"}를 봄, Pi 접점은 아래 → {RB["ffc_type"]}',
 f'커넥터가 왼쪽이면(G-1) 약 {N["variants"]["connector_mirrored"]["ribbon"]["total"]:.0f} mm, {N["variants"]["connector_mirrored"]["ribbon"]["ffc_type"]}',
 f'L2 Pi 자리까지 {RB["total"]:.0f} mm = 받침~뚜껑 {RB["in_cradle_total"] + RB["pi_end_insert"]:.1f} + 뚜껑 밑 {RB["total"] - RB["in_cradle_total"] - RB["pi_end_insert"]:.1f}',
]
for i, sx in enumerate(steps):
    txt(DX, DY + 22 + i * 19, sx, 12, C['rib'] if i < 5 else C['ink'])
NY = 1995
txt(40, NY, f'사용: 25° 뒤로 기울임, 가장 높은 곳 z{U["cr_top_front"][1]}, 가장 앞 y{N["all_min_y"]} (금지선 y{KO["y_max"]:g}). 접음: 다리를 받침 뒤에 붙이고 눕혀 z{FO["top_z"]} (스피커 윗면 z{PL["speaker_top_z"]:g} 아래, 여유 {FO["speaker_margin"]:.0f} mm), 뒤끝 y{FO["y"][1]} (뚜껑 y{LID["y"][1]:g}).', 13)
txt(40, NY + 22, f'화면 위쪽을 10 N으로 누르면 받침다리 {st["leg_force"]} N 압축 (좌굴 한계 {st["leg_Pcr"]} N). 앞으로 10 N 당기면 뒤꿈치 {st["heel_force"]} N, 뚜껑 앞 나사 합계 {st["lid_screws_total"]} N. 리본 필요 약 {RB["total"]:.0f} mm / 300 mm ({RB["ffc_type"][0]}형).', 13)
txt(40, NY + 44, '커넥터 쪽(창이 오른쪽, 입구 +x)과 모서리 구멍 깊이, 볼록판 높이는 사진·도면 추정 — 화면을 받으면 확인(CAD_SPEC_rev3 G).', 12, C['grey'])
add('</svg>')
svg = D / 'touch_concept_rev3.svg'; png = D / 'touch_concept_rev3.png'
svg.write_text('\n'.join(out), encoding='utf-8')
if png.exists(): png.unlink()
chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
p = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--screenshot={png}', f'--window-size={W_},{HT}', f'file://{svg}'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(120):
    if png.exists() and png.stat().st_size > 0: break
    time.sleep(0.5)
time.sleep(0.5)
try: p.terminate()
except Exception: pass
print('ok', svg, png.exists())
