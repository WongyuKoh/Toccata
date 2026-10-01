# Toccata R31 touchscreen — rev 3: Waveshare 7-DSI-TOUCH-C (B1) on the L2 low rear bar.
# World (mm): x across from the A0 left boundary, y away from the player from the white-key front lip, z up from the desk.
# Cradle frame: xr = x - XC (XC = screen centre), u = from the glass bottom edge up the screen, w = from the glass front face backward.
# ONE placement block (PL) is read from the L2 json; every world coordinate below is computed from PL + part geometry.
# Rev-2 mechanism kept: printed lid knuckles, cradle ears + heel stop at 22 deg (3 deg play), use at 25 deg set by an easel leg
# hinged on the cradle back with its foot in a lid pocket, backward fold for transport, leg clipped to the cradle back.
import json, math, sys, re, hashlib
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
T3 = OUT.parent
SRC_FINAL, SRC_PROV = T3 / 'L2_cu.json', T3 / 'L2_cu_provisional.json'
SRC = SRC_FINAL if SRC_FINAL.exists() else SRC_PROV
L2 = json.load(open(SRC))
IS_FINAL = SRC == SRC_FINAL
def md5_8(p): return hashlib.md5(open(p, 'rb').read()).hexdigest()[:8]
# body_L2.json (CAD session, read-only in the repo) is copied to work/ for the speaker driver centres; the copy is compared with the repo on every run
BODY_REPO = Path('/Users/kwg/Desktop/mydrive/project/Toccata/hardware/mechanical/cad/spec/body_L2.json')
BODY_COPY = OUT / 'work' / 'body_L2_copy.json'
BL2 = json.load(open(BODY_COPY))
BL2_INFO = dict(copy=str(BODY_COPY), md5=md5_8(BODY_COPY), repo_md5=md5_8(BODY_REPO) if BODY_REPO.exists() else None)
BL2_INFO['same_as_repo'] = BL2_INFO['md5'] == BL2_INFO['repo_md5']
if BL2_INFO['repo_md5'] and not BL2_INFO['same_as_repo']:
    print('WARNING: repo body_L2.json changed since the copy -> re-copy and re-run', BL2_INFO)

def pick(*keys, default=None):
    """first key path found in L2 (paths as 'a.b'); lists/ranges are returned as-is"""
    for k in keys:
        d = L2; ok = True
        for part in k.split('.'):
            if isinstance(d, dict) and part in d: d = d[part]
            else: ok = False; break
        if ok and d is not None: return d
    return default

def lo(v): return v[0] if isinstance(v, (list, tuple)) else v
def hi(v): return v[-1] if isinstance(v, (list, tuple)) else v
def mid(v): return (lo(v) + hi(v)) / 2 if isinstance(v, (list, tuple)) else v
def r2(v): return round(float(v), 2)
def r2l(p): return [r2(c) for c in p]

# ---- project context (keys; not placement): copied key_numbers.json + rev-2 L1 sensor row ----
_KN = json.load(open(OUT / 'work' / 'key_numbers_copy.json'))['keys']
CTX = dict(white_top_z=_KN['white_top_z'], black_top_z=_KN['black_top_z'], key_rear_y=_KN['key_rear_y'], module_top_z=_KN['module_top_z'],
           O4_x=_KN['O4_x'], O4_white_centre_x=_KN['O4_white_centre_x'], octave=_KN['octave_width_mm'], key_x=[0.0, 1222.0], sensor_y=67.0,
           black_front_y_draw=70.0, player_x=611.0, ear_dx=75.0, eye=[-350.0, 450.0],
           note='keys from touch/context/key_numbers.json; key_x, sensor_y from rev-2 geom (L1 dict); black_front_y_draw only for the drawing; eye/ears are estimates')
# ============================ PLACEMENT BLOCK (the only world input) ============================
# Reads the final L2 file (body_L2.json digest from the CAD session) when present, else the provisional file.
TZ = pick('touchscreen_lid_zone_for_W1', 'centre.touchscreen_lid_zone_for_W1', default={}) or {}
CM = pick('cad_message_extra', default={}) or {}
lid_x = TZ.get('x') or pick('lid_x', 'cu_lid.x', 'draft_A_x')
XC = float(mid(lid_x)) if lid_x else float(pick('screen_lid_x_centre', default=611.0))
if lid_x is None:
    wdt = lo(pick('screen_lid_width', default=200)); lid_x = [XC - wdt / 2, XC + wdt / 2]
LID_Y = TZ.get('y') or pick('lid_y', 'cu_lid.y', default=[215, 342])
LID_TOP = float(TZ.get('top_z') or pick('lid_top_z', default=72.85))
LID_BED = float(pick('centre.walls.lid_z', default=None)[0]) if pick('centre.walls.lid_z') else float(mid(pick('lid_ribs_underside_z', default=[61, 68])))
_screws_txt = str((CM.get('screen_lid') or {}).get('screws', ''))
_sy = [float(v) for v in re.findall(r'y(\d+(?:\.\d+)?)', _screws_txt)]
REAR_BAR_FRONT = float(lo(pick('overall.rear_unit_y', default=None)) if pick('overall.rear_unit_y') else pick('rear_bar_front_y', default=215))
MOD_REAR = float(lo(pick('front_joint.air_gap_y', default=None)) if pick('front_joint.air_gap_y') else pick('module_rear_wall_y', default=212))
TASK_KEEPOUT_Y = 215.0            # hard rule given with the task (y <= 215 at z >= 72.85); the final rear bar front is y214
_DRV = (BL2.get('speakers') or {}).get('driver') or {}
if _DRV.get('x_centre') and _DRV.get('centre_yz'):          # real driver (cone) centres from body_L2
    SPK_PLAN = [[float(_DRV['x_centre']['L']), float(_DRV['centre_yz'][0])], [float(_DRV['x_centre']['R']), float(_DRV['centre_yz'][0])]]
    SPK_FROM = 'body_L2 speakers.driver (x_centre, centre_yz)'
else:
    spk_x = pick('speakers_x', default=None)
    SPK_PLAN = [[mid(spk_x['L']), mid(LID_Y)], [mid(spk_x['R']), mid(LID_Y)]] if spk_x else [[-16 + 301 / 2, mid(LID_Y)], [1238 - 301 / 2, mid(LID_Y)]]
    SPK_FROM = 'pod centres (estimate)'
# 27 deg sound-path rule (L2): line from each cone's lower edge, 27 deg up toward the player, >= 3 above (module rear y, lid top z)
_BAF = ((BL2.get('speakers') or {}).get('baffle') or {}).get('angle_from_horizontal_deg', 43.0)
_CONE_R = 47.0                                               # Ø94 hole
SOUND_RULE = None
if _DRV.get('centre_yz'):
    cy_, cz_ = _DRV['centre_yz']; le = (cy_ - _CONE_R * math.cos(math.radians(_BAF)), cz_ - _CONE_R * math.sin(math.radians(_BAF)))
    SOUND_RULE = dict(cone_lower_edge_yz=[round(le[0], 2), round(le[1], 2)], baffle_deg=_BAF, line_deg=27.0)
# lid fixing hardware (CAD L2): seam rails + front posts with M3 inserts
def _cc(idp):
    for c in (L2.get('centre_contents') or []):
        if str(c.get('id', '')).startswith(idp): return c['bbox_x0x1y0y1z0z1']
    return None
SEAM = dict(rail=[_cc('PR-SEAMRAIL-1'), _cc('PR-SEAMRAIL-2')], post=[_cc('PR-SEAMPOST-1'), _cc('PR-SEAMPOST-2')])
PL = dict(
    source=str(SRC), source_is_final=IS_FINAL, source_note=pick('source', default=''),
    x_centre=XC,
    keepout=dict(y_max=max(TASK_KEEPOUT_Y, REAR_BAR_FRONT), z_min=LID_TOP, clearance=1.0, module_rear_y=MOD_REAR, rear_bar_front_y=REAR_BAR_FRONT,
                 rule=f'nothing of the touchscreen at y <= {max(TASK_KEEPOUT_Y, REAR_BAR_FRONT):g} while z >= {LID_TOP} (modules end y{MOD_REAR:g}, rear bar front y{REAR_BAR_FRONT:g}; modules are lifted out upward)'),
    lid=dict(x=[float(lid_x[0]), float(lid_x[1])], y=[float(LID_Y[0]), float(LID_Y[1])], top_z=LID_TOP, plate_t=3.0, bed_z=round(LID_BED, 2),
             note='CU-SCREENLID: printed PETG plate 3 + ribs to the bed plane (final L2: ribs 8.5, bottom z61.35)'),
    floor_z=float(lo(pick('centre.floor_zone.z', default=None)) if pick('centre.floor_zone.z') else hi(pick('under_lid.strip_floor_z', default=[14.5, 16.5]))),
    speaker_top_z=float(pick('speakers_top_z', default=None) or lo(pick('speakers.top_z', default=[134, 157]))),
    rear_face_y=float(hi(pick('overall.y', default=None)) if pick('overall.y') else LID_Y[1]),
    lid_screw=dict(y=_sy if len(_sy) >= 2 else [LID_Y[0] + 12.0], inset_x=5.0,
                   x=[float(lid_x[0]) + 5.0, float(lid_x[1]) - 5.0],
                   note=(_screws_txt or 'front 2 corners M3x10 (D23 rule kept)') + ' — x = lid edge +-5 (est.: middle of the 10 mm the lid overlaps each 20 mm seam rail)'),
    speakers_plan=SPK_PLAN, speakers_plan_from=SPK_FROM, sound_rule=SOUND_RULE, body_L2=BL2_INFO,
    seam=SEAM,
    body_x=[float(v) for v in (pick('overall.x', default=[-16.0, 1238.0]))],
    front_zone_y=pick('centre.front_zone.y', default=[LID_Y[0], LID_Y[0] + 27]),
    cad_recommendations=dict(hinge=CM.get('hinge_line_recommended'), ribbon_hole=CM.get('ribbon_hole_recommended'), folded=CM.get('folded'),
                             exhaust=CM.get('exhaust_slots') or TZ.get('vents'), dsi=TZ.get('dsi'), gpio=TZ.get('gpio_power')),
    keepout_zones=dict(dsi=(CM.get('disp1_connector') or {}).get('keepout'), dsi_z=[28.1, round(LID_BED, 2)], gpio=CM.get('gpio_2_6')),
)
# hinge axis height: fold feet under the rib plane (w16) + leg stow room -> 8 above lid top (same rule as rev 2)
H_Z_ABOVE_LID = 8.5

# ============================ SCREEN: Waveshare 7-DSI-TOUCH-C ============================
# Drawing ws_7-DSI-TOUCH-C-details-size.jpg (pixel-read 3.51 px/mm) + product photos. Orientation used: thick bezel (9.65) at the bottom,
# glass facing the player (native 1024x600 landscape, no rotation). Photos show that the drawing's BACK view is the front view
# flipped about the HORIZONTAL axis (Pi-hole mirror check, cable position, FPC/power order) -> back-view x from left = front x from left,
# back-view distance from top = u (distance from the glass bottom edge).
G = dict(w=166.10, h=101.00, body=8.00, body_studs=13.4, act_w=154.58, act_h=86.42,
         act_off=dict(left=3.97, right=7.55, top=4.94, bottom=9.65),
         holes=dict(pitch=[154.00, 88.00], from_side=6.05, from_tb=6.50, thread='M2.5', depth='unknown'),
         pi_holes=dict(xr=[64.05 - 83.05, 122.05 - 83.05], u=[25.5, 74.5], note='Pi mount holes 58 x 49 (not used; standoffs not fitted)'),
         window=dict(xr=[100.4 - 83.05, 126.6 - 83.05], u=[30.2, 70.5], note='opening in the metal back, driver PCB visible (est. +-0.5)'),
         fpc=dict(xr=[100.9 - 83.05, 106.3 - 83.05], u=[36.5, 52.4], pin_u_centre=43.8, mouth_xr=106.3 - 83.05, mouth='+x',
                  type='22-pin 0.5 mm ZIF, horizontal, on a blue strip PCB in the window; mouth faces the window (+x). est. +-0.5'),
         pwr=dict(xr=[102.4 - 83.05, 107.4 - 83.05], u=[56.6, 65.2], mouth_xr=107.4 - 83.05, mouth='+x',
                  type='MX1.25 2-pin horizontal, above the FPC connector, mouth +x. est. +-0.5'),
         emboss=dict(xr=[26.4 - 83.05, 97.4 - 83.05], u=[32.2, 71.0], h=2.1, note='raised stamped rectangle on the back, height from side view ~2.1 (est.)'),
         mass=0.30)
G['glass_xr'] = [-G['w'] / 2, G['w'] / 2]
G['act_xr'] = [-G['w'] / 2 + G['act_off']['left'], G['w'] / 2 - G['act_off']['right']]
G['act_u'] = [G['act_off']['bottom'], G['act_off']['bottom'] + G['act_h']]
G['holes_xr'] = [-G['w'] / 2 + G['holes']['from_side'], G['w'] / 2 - G['holes']['from_side']]
G['holes_u'] = [G['holes']['from_tb'], G['h'] - G['holes']['from_tb']]
_BF = json.load(open(OUT / 'work' / 'bottom_feature.json'))      # measured by work/measure_bottom_feature.py
G['bottom_feature'] = dict(xr=_BF['xr'], proud=_BF['proud_mm'], proud_max=_BF['proud_max_est'],
                           src='drawing front view (work/measure_bottom_feature.py) + photo details-9 (slot with a tab in the bottom face, right)')
CONN_SIDE = +1          # +1: connector right of centre, mouth +x (photo analysis). -1 = mirror everything connector-side about XC.

# ============================ CRADLE (local) ============================
RIM, CLR = 2.0, 0.3
CR = dict(xr=[-(G['w'] / 2 + CLR + RIM), G['w'] / 2 + CLR + RIM], u0=-2.5, u1=G['h'] + 2.5, w0=-1.0,
          w_screen_back=G['body'], w_plate_in=None, w_plate_out=None, w_rib=None)
EMB_CLR = 0.4
CR['w_plate_in'] = round(G['body'] + max(2.5, G['emboss']['h'] + EMB_CLR), 2)     # 10.5
CR['plate_t'] = 2.5
CR['w_plate_out'] = CR['w_plate_in'] + CR['plate_t']                                  # 13.0 = hinge-axis plane
CR['rib_h'] = 3.0
CR['w_rib'] = CR['w_plate_out'] + CR['rib_h']                                          # 16.0
UA = CR['u0'] - 6.5                  # axis 6.5 below the cradle bottom (cheek R5.5 + 1.0)
WA = CR['w_plate_out']               # axis in the plate back plane -> front lever b = WA - w0 = 14 (rev 2: 17)
HEEL_STOP_H = 3.5                    # raised stop block in each ear slot (heel radius 10.63 -> 8.60)
HEEL_REL22 = (-7.0, -(H_Z_ABOVE_LID - HEEL_STOP_H))
KNUCKLE_BASE_HALF = 9.0              # knuckle cheek profile: R5.5 around the axis + trapezoid to +-9 at the lid top
# heel stop block relative to the axis (dy, dz): from the knuckle base front to 2 before the axis, lid top .. lid top + 3.5
HEEL_BLOCK_REL = (-KNUCKLE_BASE_HALF, -2.0, -H_Z_ABOVE_LID - 20.0, -(H_Z_ABOVE_LID - HEEL_STOP_H))   # merged with the lid below, so depth = to the top / sides
SLOT_FLOOR_REL = (-40.0, 40.0, -H_Z_ABOVE_LID - 20.0, -H_Z_ABOVE_LID)   # lid top between the cheeks (outside the block)
# walls (explicit, so the model and the drawings use the same faces)
CR['walls'] = dict(bottom_u=[CR['u0'], 0.0], top_u=[r2(CR['u1'] - RIM), CR['u1']], top_gap=r2(CR['u1'] - RIM - G['h']), bottom_gap=0.0,
                   side_inner_xr=r2(G['w'] / 2 + CLR), side_gap=CLR, front_w=CR['w0'],
                   note='glass bottom edge rests on the bottom wall inner face u0 (u datum); top gap 0.5; side gaps 0.3; walls run w-1..16')
# relief notch in the bottom wall for the small feature below the glass bottom edge (Waveshare front view, right of centre)
NOTCH_MARGIN = 6.5
NOTCH = dict(xr=[float(math.floor(G['bottom_feature']['xr'][0] - NOTCH_MARGIN)), float(math.ceil(G['bottom_feature']['xr'][1] + NOTCH_MARGIN))],
             u=[CR['u0'], 0.0], w=[CR['w0'], G['body']], through=True, feature_xr=G['bottom_feature']['xr'], feature_proud=G['bottom_feature']['proud'],
             note='cut through the bottom wall (u-2.5..0) over w-1..8: the feature may stick out up to ~1 and stays reachable; the glass still rests on the wall on both sides')

# hinge sets (xr), symmetric, screw from the outer side (head outward)
def hinge_set(side):
    s = 1 if side == 'right' else -1
    far = sorted([s * 52.0, s * 60.0]); ear = sorted([s * 60.2, s * 68.2]); near = sorted([s * 68.4, s * 72.4])
    slot = sorted([s * 60.0, s * 68.4])                      # ear slot between the cheeks = ear 8.0 + 0.2 gap each side
    return dict(xr=sorted([s * 52.0, s * 72.4]), far_cheek=far, ear=ear, ear_slot=slot, near_cheek=near, screw_from='+x' if s > 0 else '-x')
HINGES = dict(left=hinge_set('left'), right=hinge_set('right'))
CHEEK_R = 5.5; EAR_HUB_R = 4.2
TH_USE, TH_HEEL, TH_FOLD = 25.0, 22.0, 90.0

# ============================ axis position from the keep-out rule ============================
def P_rel(u, w, th):
    """(dy, dz) of cradle point relative to the hinge axis at tilt th"""
    t = math.radians(th); du, dw = u - UA, w - WA
    return (du * math.sin(t) + dw * math.cos(t), du * math.cos(t) - dw * math.sin(t))

# ---- 2D helpers (convex hull, dense boundary, point/rect distances) ----
def hull2(pts):
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo_, hi_ = [], []
    for p in pts:
        while len(lo_) >= 2 and cross(lo_[-2], lo_[-1], p) <= 0: lo_.pop()
        lo_.append(p)
    for p in reversed(pts):
        while len(hi_) >= 2 and cross(hi_[-2], hi_[-1], p) <= 0: hi_.pop()
        hi_.append(p)
    return lo_[:-1] + hi_[:-1]                                   # CCW
def densify(poly, step=0.05):
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out
def rect_sd(p, r):
    """signed distance from p to rect r = (x0, x1, y0, y1): > 0 outside, < 0 inside"""
    dx = max(r[0] - p[0], 0, p[0] - r[1]); dy = max(r[2] - p[1], 0, p[1] - r[3])
    if dx > 0 or dy > 0: return math.hypot(dx, dy)
    return -min(p[0] - r[0], r[1] - p[0], p[1] - r[2], r[3] - p[1])
def in_convex(p, poly):
    return all((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0 for a, b in zip(poly, poly[1:] + poly[:1]))
def poly_rect_gap(poly, r):
    """min signed gap between a convex polygon and an axis-aligned rect (negative = overlap depth)"""
    g = min(rect_sd(p, r) for p in densify(poly))
    for c in [(r[0], r[2]), (r[0], r[3]), (r[1], r[2]), (r[1], r[3])]:
        if in_convex(c, poly): g = min(g, -min(math.dist(c, q) for q in densify(poly, 0.02)))
    return g

# ---- ear side profile (cradle local u, w): convex hull of the hub R4.2 round the axis, the attachment to the cradle bottom
# (u0, w8..13) and the heel point. No other lobe: the heel point must be the lowest ear point at 22 deg (rev-3a fix). ----
def to_local(dy, dz, th):
    t = math.radians(th); return (UA + dy * math.sin(t) + dz * math.cos(t), WA + dy * math.cos(t) - dz * math.sin(t))
HEEL_LOCAL = to_local(HEEL_REL22[0], HEEL_REL22[1], TH_HEEL)
EAR_HULL = hull2([(UA + EAR_HUB_R * math.cos(a), WA + EAR_HUB_R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 721)[:-1]]
                 + [(CR['u0'], CR['w_screen_back']), (CR['u0'], WA), HEEL_LOCAL])
_ih = EAR_HULL.index(min(EAR_HULL, key=lambda p: math.dist(p, HEEL_LOCAL)))
_ib = EAR_HULL.index(min(EAR_HULL, key=lambda p: math.dist(p, (CR['u0'], WA))))
_front = (CR['u0'], CR['w_screen_back'])
def _other_nb(i):
    nb = [EAR_HULL[i - 1], EAR_HULL[(i + 1) % len(EAR_HULL)]]
    return max(nb, key=lambda p: math.dist(p, _front))
EAR_EDGES = dict(heel=HEEL_LOCAL, front_to=_front, lower_tangent=_other_nb(_ih), back_from=(CR['u0'], WA), back_tangent=_other_nb(_ib))
EAR_MIN_U = min(p[0] for p in EAR_HULL)
# compact outline for drawings/3D: straight-edge vertices + the two exact tangent points + arc points every ~5 deg (CCW in u, w)
_on_arc = [abs(math.dist(p, (UA, WA)) - EAR_HUB_R) < 1e-3 for p in EAR_HULL]
EAR_PROFILE_OUT = [r2l(p) for i, p in enumerate(EAR_HULL)
                   if not _on_arc[i] or not _on_arc[i - 1] or not _on_arc[(i + 1) % len(EAR_HULL)] or i % 10 == 0]
def ear_outline_rel(th, dense=False):
    """ear side outline relative to the axis (dy, dz) at tilt th"""
    return [P_rel(u, w, th) for (u, w) in (densify(EAR_HULL, 0.1) if dense else EAR_HULL)]

CORNERS = [(CR['u0'], CR['w0']), (CR['u0'], CR['w_rib']), (CR['u1'], CR['w0']), (CR['u1'], CR['w_rib']),
           (CR['u0'], WA), (CR['u0'], CR['w_screen_back'])]
TH_SWEEP = np.linspace(TH_HEEL, TH_FOLD, 681)
front_reach = 0.0; front_reach_what = ''
for th in TH_SWEEP:
    for (u, w) in CORNERS:
        dy = P_rel(u, w, th)[0]
        if -dy > front_reach: front_reach, front_reach_what = -dy, f'cradle corner u{u} w{w} at {th:.1f} deg'
    for (dy, dz) in ear_outline_rel(th):
        if -dy > front_reach: front_reach, front_reach_what = -dy, f'ear/heel at {th:.1f} deg'
if KNUCKLE_BASE_HALF > front_reach: front_reach, front_reach_what = KNUCKLE_BASE_HALF, 'lid knuckle base'
H_Y = PL['keepout']['y_max'] + PL['keepout']['clearance'] + front_reach
H_Z = PL['lid']['top_z'] + H_Z_ABOVE_LID
H = (round(H_Y, 2), round(H_Z, 2))
PL['hinge_axis_yz'] = list(H)
PL['hinge_axis_rule'] = f'y = keep-out y{PL["keepout"]["y_max"]:g} + {PL["keepout"]["clearance"]} clearance + front reach {front_reach:.2f} ({front_reach_what}); z = lid top + {H_Z_ABOVE_LID}'
hint = pick('hinge_line_hint')
PL['hinge_hint_from_L2'] = hint

def P(u, w, th, h=H):
    d = P_rel(u, w, th); return (h[0] + d[0], h[1] + d[1])
def W3(xr, u, w, th):
    y, z = P(u, w, th); return (XC + xr, y, z)

# ============================ key poses ============================
pts = {}
for th, tag in [(TH_USE, 'use'), (TH_HEEL, 'heel'), (TH_FOLD, 'fold')]:
    pts[tag] = dict(
        glass_bottom=r2l(P(0, 0, th)), glass_top=r2l(P(G['h'], 0, th)), glass_centre=r2l(P(G['h'] / 2, 0, th)),
        act_bottom=r2l(P(G['act_u'][0], 0, th)), act_top=r2l(P(G['act_u'][1], 0, th)), act_centre=r2l(P(sum(G['act_u']) / 2, 0, th)),
        cr_bot_front=r2l(P(CR['u0'], CR['w0'], th)), cr_bot_back=r2l(P(CR['u0'], WA, th)), cr_bot_rib=r2l(P(CR['u0'], CR['w_rib'], th)),
        cr_top_front=r2l(P(CR['u1'], CR['w0'], th)), cr_top_back=r2l(P(CR['u1'], WA, th)), cr_top_rib=r2l(P(CR['u1'], CR['w_rib'], th)))
sweep_min_y, sweep_min_z, sweep_max_z = 1e9, 1e9, -1e9
for th in TH_SWEEP:
    for (u, w) in CORNERS:
        y, z = P(u, w, th); sweep_min_y = min(sweep_min_y, y); sweep_min_z = min(sweep_min_z, z); sweep_max_z = max(sweep_max_z, z)
    for (dy, dz) in ear_outline_rel(th):
        sweep_min_y = min(sweep_min_y, H[0] + dy)
knuckle_front_y = H[0] - KNUCKLE_BASE_HALF
all_min_y = min(sweep_min_y, knuckle_front_y)

# heel
hr = math.hypot(*HEEL_REL22); a22 = math.atan2(HEEL_REL22[1], HEEL_REL22[0])
a25 = a22 - math.radians(TH_USE - TH_HEEL)
heel25 = (H[0] + hr * math.cos(a25), H[1] + hr * math.sin(a25))
heel_stop_z = PL['lid']['top_z'] + HEEL_STOP_H
heel_gap25 = heel25[1] - heel_stop_z
heel_contact = (H[0] + HEEL_REL22[0], heel_stop_z)
heel_fwd_max = hr                     # the heel lobe points straight forward at about 22 + 180 - |a22| deg
# whole ear outline vs the heel stop block and the slot floor, 22..90 deg (0.1 deg): must touch (>= 0) at 22 and clear >= 0.3 from 25
EAR_BLOCK = []
for th in np.round(np.arange(TH_HEEL, TH_FOLD + 1e-9, 0.1), 2):
    poly = ear_outline_rel(th)
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) < 0: poly = poly[::-1]   # make CCW (the u,w -> y,z map flips)
    g = min(poly_rect_gap(poly, HEEL_BLOCK_REL), poly_rect_gap(poly, SLOT_FLOOR_REL))
    EAR_BLOCK.append((float(th), g))
ear_gap_22 = [g for t, g in EAR_BLOCK if abs(t - TH_HEEL) < 1e-6][0]
ear_gap_25_90 = min(g for t, g in EAR_BLOCK if t >= TH_USE - 1e-6)
ear_gap_25_90_at = [t for t, g in EAR_BLOCK if t >= TH_USE - 1e-6 and g == ear_gap_25_90][0]
ear_gap_22_25_min = min(g for t, g in EAR_BLOCK if t <= TH_USE)
EAR_CHECK = dict(gap_at_22=r2(ear_gap_22), min_gap_25_90=r2(ear_gap_25_90), at_deg=ear_gap_25_90_at, min_gap_22_25=r2(ear_gap_22_25_min),
                 ok=ear_gap_22 >= -0.01 and ear_gap_25_90 >= 0.3, rule='whole ear outline vs stop block + slot floor: >= 0 at 22 deg (contact), >= 0.3 at 25..90 deg')
# same check on the first rev-3 ear (extra heel-lobe point at +0.35 rad) -> shows why it was replaced
def _ear_rev3_first(th):
    hr_ = math.hypot(*HEEL_REL22); a_ = math.atan2(HEEL_REL22[1], HEEL_REL22[0]) - math.radians(th - TH_HEEL)
    p = hull2([(EAR_HUB_R * math.cos(a), EAR_HUB_R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 37)]
              + [P_rel(CR['u0'], CR['w_screen_back'], th), P_rel(CR['u0'], WA, th), (hr_ * math.cos(a_), hr_ * math.sin(a_)), (hr_ * math.cos(a_ + 0.35), hr_ * math.sin(a_ + 0.35))])
    return p if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) > 0 else p[::-1]
_g3 = [(float(t), min(poly_rect_gap(_ear_rev3_first(t), HEEL_BLOCK_REL), poly_rect_gap(_ear_rev3_first(t), SLOT_FLOOR_REL))) for t in np.round(np.arange(TH_HEEL, 60.0, 0.05), 2)]
_lobe_local = to_local(math.hypot(*HEEL_REL22) * math.cos(math.atan2(HEEL_REL22[1], HEEL_REL22[0]) + 0.35),
                       math.hypot(*HEEL_REL22) * math.sin(math.atan2(HEEL_REL22[1], HEEL_REL22[0]) + 0.35), TH_HEEL)
EAR_CHECK['rev3_first_lobe'] = dict(gap_at_22=r2(_g3[0][1]), gap_at_25=r2([g for t, g in _g3 if abs(t - TH_USE) < 1e-6][0]),
                                    clears_from_deg=next(t for t, g in _g3 if g >= 0), lobe_uw=r2l(_lobe_local), print_height=r2(CR['u1'] - _lobe_local[0]))

# cheek clearance for the rib zone behind the axis plane (bottom wall w13..16 at the cheek x-ranges)
def in_knuckle(dy, dz):
    if math.hypot(dy, dz) < CHEEK_R: return True
    zl = -H_Z_ABOVE_LID
    if zl <= dz <= 0:
        half = CHEEK_R + (KNUCKLE_BASE_HALF - CHEEK_R) * (-dz / H_Z_ABOVE_LID)
        return abs(dy) <= half
    return False
def min_gap_to_knuckle(u, w):
    best = 1e9
    for th in TH_SWEEP:
        dy, dz = P_rel(u, w, th)
        if in_knuckle(dy, dz): return -1.0
        # distance to the profile boundary (approx: radial gap to circle, horizontal gap to trapezoid)
        g = math.hypot(dy, dz) - CHEEK_R
        if -H_Z_ABOVE_LID <= dz <= 0:
            half = CHEEK_R + (KNUCKLE_BASE_HALF - CHEEK_R) * (-dz / H_Z_ABOVE_LID); g = min(g, abs(dy) - half)
        best = min(best, g)
    return best
cheek_checks = {f'u{u}_w{w}': r2(min_gap_to_knuckle(u, w)) for (u, w) in
                [(CR['u0'], WA), (CR['u0'], 14.0), (CR['u0'], 15.0), (CR['u0'], CR['w_rib']), (-0.3, CR['w_rib']), (0.0, CR['w_rib']), (2.0, CR['w_rib'])]}
# find the lowest u at which the w16 rib line clears the knuckles by >= 0.5 at the cheek x-ranges
rib_relief_u = None
for uu in np.arange(CR['u0'], 20.0, 0.1):
    ok = all(min_gap_to_knuckle(uu, w) >= 0.5 for w in (13.5, 14.5, 15.5, 16.0))
    if ok: rib_relief_u = round(float(uu), 1); break

# chamfer of the bottom-back edge of the rib zone (u0, w_rib) so the cradle clears the knuckle cheeks by >= 0.5 over 22..90 deg
def outline_gap(c):
    pts_ = [(CR['u0'], w) for w in np.arange(WA, CR['w_rib'] - c + 1e-9, 0.25)]
    pts_ += [(CR['u0'] + c * k, CR['w_rib'] - c + c * k) for k in np.linspace(0, 1, 9)]
    pts_ += [(u, CR['w_rib']) for u in np.arange(CR['u0'] + c, 6.0, 0.25)]
    return min(min_gap_to_knuckle(u, w) for (u, w) in pts_)
RIB_CHAMFER = None
for c in np.arange(0.0, 6.01, 0.25):
    if outline_gap(c) >= 0.5: RIB_CHAMFER = float(c); break
RIB_CHAMFER_GAP = outline_gap(RIB_CHAMFER)

# ============================ fold ============================
FOLD = dict(back_plane_z=r2(H[1] - (WA - WA)), rib_plane_z=r2(H[1] - (CR['w_rib'] - WA)), top_z=r2(H[1] + (WA - CR['w0'])),
            y=[r2(H[0] + (CR['u0'] - UA)), r2(H[0] + (CR['u1'] - UA))])
FOLD['rear_margin'] = r2(PL['lid']['y'][1] - FOLD['y'][1])
FOLD['feet_h'] = r2(FOLD['rib_plane_z'] - PL['lid']['top_z'])
FOLD['speaker_margin'] = r2(PL['speaker_top_z'] - FOLD['top_z'])
FOLD['lid_rear_needed_for_2mm'] = r2(FOLD['y'][1] + 2.0)

# back pads on the cradle (w13..16) and the matching lid fold feet
PADS = [dict(xr=[s * 60.0, s * 76.0] if s > 0 else [-76.0, -60.0], u=uu) for s in (-1, 1) for uu in ([20.0, 36.0], [70.0, 86.0])]
FEET = []
for p in PADS:
    y0 = H[0] + (p['u'][0] - UA); y1 = H[0] + (p['u'][1] - UA)
    f = dict(x=[r2(XC + p['xr'][0]), r2(XC + p['xr'][1])], y=[r2(y0), r2(y1)], z=[PL['lid']['top_z'], r2(FOLD['rib_plane_z'])],
             rear=p['u'][0] > 50)
    if f['rear']:
        f['lip'] = dict(y=[r2(y1 + 0.5), r2(y1 + 2.5)], z=[r2(FOLD['rib_plane_z']), r2(FOLD['rib_plane_z'] + 2.0)])
    FEET.append(f)

# ============================ easel leg ============================
LEG = dict(b=10.0, t=6.0, r_tip=3.0, xr=[-5.0, 5.0], pocket_depth=3.5, ramp_deg=30.0, E=2000.0)
LEG['w_p'] = WA + 0.5 + LEG['t'] / 2          # 16.5: leg lies in a channel on the plate back when stowed
STOW_MARGIN = 1.0
tip_z = PL['lid']['top_z'] - LEG['pocket_depth'] + LEG['r_tip']
POCKET_BACK_MIN_MAT = 6.0                      # solid lid behind the pocket back wall
def leg_for(u_p, L):
    piv = P(u_p, LEG['w_p'], TH_USE)
    dz = piv[1] - tip_z
    if dz >= L: return None
    ty = piv[0] + math.sqrt(L ** 2 - dz ** 2)
    d = ((piv[0] - ty) / L, (piv[1] - tip_z) / L)               # tip -> pivot (force on cradle)
    r = (piv[0] - H[0], piv[1] - H[1]); arm = abs(r[0] * d[1] - r[1] * d[0])
    ang = math.degrees(math.atan2(piv[1] - tip_z, ty - piv[0]))
    return dict(piv=piv, tip=(ty, tip_z), dir=d, arm=arm, ang=ang)
cands = []
for u_p in np.arange(8.0, 44.1, 1.0):
    Lmax_stow = CR['u1'] - STOW_MARGIN - LEG['r_tip'] - u_p
    for L in np.arange(40.0, Lmax_stow + 0.01, 0.5):
        g = leg_for(u_p, L)
        if g is None: continue
        if g['tip'][0] + LEG['r_tip'] + POCKET_BACK_MIN_MAT > PL['lid']['y'][1]: continue
        if g['ang'] < 25.0 or g['ang'] > 40.0: continue
        cands.append((g['arm'], float(u_p), float(L), g))
cands.sort(key=lambda c: -c[0])
# choose: best arm, then prefer shorter leg within 1 mm of the best arm (stiffer, lighter)
best_arm = cands[0][0]
pool = [c for c in cands if c[0] >= best_arm - 1.0]
pool.sort(key=lambda c: c[2])
_, U_P, L_LEG, LG = pool[0]
LEG.update(u_p=U_P, L=L_LEG)
piv, tip = LG['piv'], LG['tip']
leg_ang = LG['ang']; arm = LG['arm']; leg_dir = LG['dir']
stow_tip_u = U_P + L_LEG + LEG['r_tip']
pocket = dict(x=[r2(XC - 7.0), r2(XC + 7.0)], back_wall_y=r2(tip[0] + LEG['r_tip']), bottom_z=r2(PL['lid']['top_z'] - LEG['pocket_depth']),
              bottom_y=[r2(tip[0]), r2(tip[0] + LEG['r_tip'])],
              ramp_front_y=r2(tip[0] - LEG['pocket_depth'] / math.tan(math.radians(LEG['ramp_deg']))))
# v13 deviation 1 rule (re-derived): the leg is a capsule (radius t/2 = r_tip) around the pivot-tip segment; the lid surface
# (flat top -> 30 deg ramp -> pocket floor -> back wall) must clear it by >= 0.2 except the intended floor/back-wall contact of the tip.
def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))
def ramp_clear(ys):
    zt, zb = PL['lid']['top_z'], pocket['bottom_z']
    ye = ys + (zt - zb) / math.tan(math.radians(LEG['ramp_deg']))
    worst = 1e9
    for yy in np.arange(ys - 25, ye + 1e-9, 0.02):
        zl = zt if yy <= ys else zt - (yy - ys) * math.tan(math.radians(LEG['ramp_deg']))
        worst = min(worst, seg_dist((yy, zl), piv, tip) - LEG['r_tip'])
    return worst
ys_nom = pocket['ramp_front_y']; clr_nom = ramp_clear(ys_nom)
ys = ys_nom
while ramp_clear(ys) < 0.2: ys -= 0.05
# the ramp must end in front of the tip's floor contact
pocket['ramp_front_y_rev2_rule'] = r2(ys_nom); pocket['ramp_clear_rev2_rule'] = r2(clr_nom)
pocket['ramp_front_y'] = r2(ys); pocket['ramp_min_clear'] = r2(ramp_clear(ys))
pocket['ramp_end_y'] = r2(ys + LEG['pocket_depth'] / math.tan(math.radians(LEG['ramp_deg'])))
pocket['floor_y'] = [pocket['ramp_end_y'], pocket['back_wall_y']]
pocket['block'] = dict(x=[r2(XC - 10), r2(XC + 10)], y=[r2(pocket['ramp_front_y'] - 3), r2(pocket['back_wall_y'] + 3)],
                       z=[PL['lid']['bed_z'], PL['lid']['top_z'] - LEG['pocket_depth']], note='filled solid to the print-bed plane (v13 rule)')
# folded / stowed leg
fold_leg_z = (r2(H[1] - (LEG['w_p'] + LEG['t'] / 2 - WA)), r2(H[1] - (LEG['w_p'] - LEG['t'] / 2 - WA)))
CLEVIS_R = 3.8
fold_clevis_zmin = r2(H[1] - (LEG['w_p'] + CLEVIS_R - WA))
fold_leg_y = (r2(H[0] + (U_P - LEG['r_tip'] - UA)), r2(H[0] + (stow_tip_u - UA)))
piv22 = P(U_P, LEG['w_p'], TH_HEEL); piv_shift = math.hypot(piv22[0] - piv[0], piv22[1] - piv[1])
LEG['clevis'] = dict(near=[-9.3, -5.3], leg=[-5.0, 5.0], far=[5.3, 11.3], hole_near='3.3 thru', hole_far='2.5 x 6 blind (M3x20 engages 5.4)', R=CLEVIS_R)
LEG['clip'] = dict(u=[r2(U_P + L_LEG - 10), r2(U_P + L_LEG - 4)], xr_bodies=[[-8.5, -5.3], [5.3, 8.5]], catch=0.8, over_leg=0.5,
                   catch_from_w=r2(LEG['w_p'] + LEG['t'] / 2 + 0.02), hook_t=1.2)
LEG['clip']['back_w'] = r2(LEG['clip']['catch_from_w'] + LEG['clip']['hook_t'])
fold_clip_zmin = r2(H[1] - (LEG['clip']['back_w'] - WA))
LEG['channel'] = dict(xr_walls=[[-7.3, -5.3], [5.3, 7.3]], u=[r2(U_P - CLEVIS_R), CR['u1']], w=[WA, CR['w_rib']])
# leg axle: M3x20 button head (ISO 7380, as v13) put in from -x through the near cheek; head and the whole insertion path must be clear.
AXLE = dict(screw='M3x20 ISO 7380', head_d=5.7, head_h=1.65, L=20.0, from_side='-x', tool='육각 L렌치 2.0')
RIB_T, AXLE_CLR = 2.0, 1.2
# low cross rib moved off the axle line (rev 3: u30 = axle line -> head 2.25 into the rib, insertion path blocked 1.0)
U_RIB_LOW = float(math.floor(U_P - max(CLEVIS_R, AXLE['head_d'] / 2) - AXLE_CLR - RIB_T / 2))
CROSS_RIBS_U = [U_RIB_LOW, 80.0]
def box_gap(a, b):
    """gap between two axis-aligned boxes ((x0,x1),(u0,u1),(w0,w1)); negative = overlap depth (smallest axis overlap)"""
    sep = [max(a[k][0] - b[k][1], b[k][0] - a[k][1]) for k in range(3)]
    return max(sep) if max(sep) > 0 else max(sep)
W_BACK = [WA, CR['w_rib']]
BACK_FEATURES = []
for uu in CROSS_RIBS_U:
    BACK_FEATURES += [(f'가로 리브 u{uu:g} (−x)', ((CR['xr'][0], LEG['channel']['xr_walls'][0][0]), (uu - RIB_T / 2, uu + RIB_T / 2), W_BACK)),
                      (f'가로 리브 u{uu:g} (+x)', ((LEG['channel']['xr_walls'][1][1], CR['xr'][1]), (uu - RIB_T / 2, uu + RIB_T / 2), W_BACK))]
for k, (a, b) in enumerate(LEG['channel']['xr_walls']):
    BACK_FEATURES.append((f'다리 길 벽 {k + 1}', ((a, b), tuple(LEG['channel']['u']), W_BACK)))
for p in PADS: BACK_FEATURES.append((f'패드 xr{p["xr"][0]:g}', (tuple(p['xr']), tuple(p['u']), W_BACK)))
for bb in LEG['clip']['xr_bodies']: BACK_FEATURES.append((f'다리 클립 xr{bb[0]:g}', (tuple(bb), tuple(LEG['clip']['u']), (WA, LEG['clip']['back_w']))))
for xb in (-77.0, 77.0):
    for ub in (6.5, 94.5): BACK_FEATURES.append((f'보스 xr{xb:g} u{ub:g}', ((xb - 4, xb + 4), (ub - 4, ub + 4), (G['body'], CR['w_rib']))))
ax_u, ax_w = U_P, LEG['w_p']; hr_ = AXLE['head_d'] / 2; near0 = LEG['clevis']['near'][0]
AX_HEAD = ((near0 - AXLE['head_h'], near0), (ax_u - hr_, ax_u + hr_), (ax_w - hr_, ax_w + hr_))
AX_PATH = ((near0 - AXLE['L'] - AXLE['head_h'], near0), (ax_u - hr_, ax_u + hr_), (ax_w - hr_, ax_w + hr_))   # whole screw before it goes in
ax_gaps = {name: (r2(box_gap(AX_HEAD, bx)), r2(box_gap(AX_PATH, bx))) for name, bx in BACK_FEATURES}
AXLE_CHECK = dict(head_box=[list(map(r2, v)) for v in AX_HEAD], path_box=[list(map(r2, v)) for v in AX_PATH],
                  min_head_gap=min(v[0] for v in ax_gaps.values()), min_path_gap=min(v[1] for v in ax_gaps.values()),
                  nearest=min(ax_gaps, key=lambda k: ax_gaps[k][1]), rib_low_u=U_RIB_LOW,
                  rule='axle head (Ø5.7 x 1.65) and the whole screw on its way in from -x (xr ' + f'{AX_PATH[0][0]:.2f}~{near0:g}) clear of every back rib/pad/boss by >= 0.5')
AXLE_CHECK['ok'] = AXLE_CHECK['min_head_gap'] >= 0.5 and AXLE_CHECK['min_path_gap'] >= 0.5
# the u30 layout of rev 3 for comparison (head / path overlap)
_old = ((CR['xr'][0], LEG['channel']['xr_walls'][0][0]), (U_P - 1, U_P + 1), W_BACK)
AXLE_CHECK['rev3_u30_rib'] = dict(head_gap=r2(box_gap(AX_HEAD, _old)), path_gap=r2(box_gap(AX_PATH, _old)))

# ---- leg deployment swing (the capsule swings down about the pivot): which lid edge does the foot meet first? ----
POCKET_EDGE_C = 0.5
def lid_profile_yz():
    zt, zb = PL['lid']['top_z'], pocket['bottom_z']; tn = math.tan(math.radians(LEG['ramp_deg']))
    pr = [(y, zt, 'lid_top') for y in np.arange(pocket['ramp_front_y'] - 60, pocket['ramp_front_y'], 0.05)]
    pr += [(y, zt - (y - pocket['ramp_front_y']) * tn, 'ramp') for y in np.arange(pocket['ramp_front_y'], pocket['ramp_end_y'], 0.02)]
    pr += [(y, zb, 'floor') for y in np.arange(pocket['ramp_end_y'], pocket['back_wall_y'], 0.02)]
    pr += [(pocket['back_wall_y'], z, 'back_wall') for z in np.arange(zb, zt - POCKET_EDGE_C, 0.02)]
    pr += [(pocket['back_wall_y'] + POCKET_EDGE_C * k, zt - POCKET_EDGE_C + POCKET_EDGE_C * k, 'back_wall_edge') for k in np.linspace(0, 1, 26)]
    pr += [(y, zt, 'lid_top_behind') for y in np.arange(pocket['back_wall_y'] + POCKET_EDGE_C, PL['lid']['y'][1], 0.05)]
    return pr
LID_PROF = lid_profile_yz()
_PY = np.array([q[0] for q in LID_PROF]); _PZ = np.array([q[1] for q in LID_PROF])
def _seg_d_all(a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    t = np.clip(((_PY - a[0]) * vx + (_PZ - a[1]) * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(_PY - (a[0] + t * vx), _PZ - (a[1] + t * vy))
def leg_swing(pv, stop_deg=None):
    first = None; worst = (1e9, None, None)
    for ang in np.arange(0.0, -70.0, -0.05):
        tp = (pv[0] + L_LEG * math.cos(math.radians(ang)), pv[1] + L_LEG * math.sin(math.radians(ang)))
        dd = _seg_d_all(pv, tp) - LEG['r_tip']; k = int(np.argmin(dd)); g, where = float(dd[k]), LID_PROF[k]
        if first is None and g <= 0: first = (r2(ang), where[2], r2l(where[:2]))
        if stop_deg is None and first is not None: break
        if stop_deg is not None and ang >= stop_deg - 1e-9 and g < worst[0]: worst = (g, r2(ang), where[2])
        if stop_deg is not None and ang < stop_deg: break
    corner = (pocket['back_wall_y'], PL['lid']['top_z'] - POCKET_EDGE_C)
    return dict(pivot=r2l(pv), first_contact_deg=first[0] if first else None, first_contact=first[1] if first else None, first_contact_yz=first[2] if first else None,
                back_edge_dist=r2(math.dist(pv, corner)), foot_reach=r2(L_LEG + LEG['r_tip']),
                worst_overlap=r2(worst[0]) if stop_deg is not None else None, worst_at_deg=worst[1] if stop_deg is not None else None)
SWING = dict(at_25=leg_swing(piv, stop_deg=-leg_ang), at_22=leg_swing(piv22))
SWING['ok_at_22'] = SWING['at_22']['first_contact'] in ('ramp', 'floor', 'lid_top') and SWING['at_22']['back_edge_dist'] > SWING['at_22']['foot_reach']
SWING['ok_at_25'] = SWING['at_25']['first_contact'] in ('ramp', 'floor', 'lid_top') and SWING['at_25']['worst_overlap'] >= 0
SWING['procedure'] = 'deploy / stow the leg with the screen held at the 22 deg heel stop; then let go (the foot slides down the ramp to the back wall)'

# ============================ eye / reach ============================
EYE = tuple(CTX['eye']); EYE_BOX = [(-300, 400), (-400, 500), (-300, 500), (-400, 400)]
gc = pts['use']['glass_centre']; ac = pts['use']['act_centre']
def down_ang(e, p): return math.degrees(math.atan2(e[1] - p[1], p[0] - e[0]))
eye_ang = down_ang(EYE, ac); eye_rng = [down_ang(e, ac) for e in EYE_BOX]
eye_dist = math.hypot(ac[0] - EYE[0], ac[1] - EYE[1])
ab = pts['use']['act_bottom']
z_at_mod = ab[1] + (EYE[1] - ab[1]) * (ab[0] - PL['keepout']['module_rear_y']) / (ab[0] - EYE[0])        # sightline to the BOTTOM of the visible area
z_at_mod_centre = ac[1] + (EYE[1] - ac[1]) * (ac[0] - PL['keepout']['module_rear_y']) / (ac[0] - EYE[0])  # sightline to the centre
px_mm = G['act_w'] / 1024
arcmin = lambda mm, d: math.degrees(math.atan(mm / d)) * 60
reach = dict(centre_from_key_front_y=r2(ac[0]), centre_z=r2(ac[1]), top_z=r2(pts['use']['act_top'][1]),
             centre_above_module_top=r2(ac[1] - PL['keepout']['z_min']), from_black_key_rear=r2(ac[0] - CTX['key_rear_y']))

# ============================ sound paths (plan) ============================
EARS = [(CTX['player_x'] - CTX['ear_dx'], CTX['eye'][0]), (CTX['player_x'] + CTX['ear_dx'], CTX['eye'][0])]
scr_rect = (XC + CR['xr'][0], all_min_y, XC + CR['xr'][1], max(pts['use']['cr_top_rib'][0], tip[0] + 3))
def seg_rect_dist(a, b, rect):
    x0, y0, x1, y1 = rect; best = 1e9
    for i in range(0, 2001):
        t = i / 2000; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
        dx = max(x0 - x, 0, x - x1); dy = max(y0 - y, 0, y - y1); best = min(best, math.hypot(dx, dy))
    return best
paths = [dict(src=r2l(s), ear=list(e), dist_to_screen=r2(seg_rect_dist(s, e, scr_rect))) for s in PL['speakers_plan'] for e in EARS]
if SOUND_RULE:     # the L2 27 deg rule (vertical section at each driver x): the screen parts are far away in x, so they cannot enter it
    le = SOUND_RULE['cone_lower_edge_yz']
    SOUND_RULE['z_at_module_rear'] = r2(le[1] + (le[0] - PL['keepout']['module_rear_y']) * math.tan(math.radians(27.0)))
    SOUND_RULE['clear_above_module_edge'] = r2(SOUND_RULE['z_at_module_rear'] - PL['lid']['top_z'])
    SOUND_RULE['ok'] = SOUND_RULE['clear_above_module_edge'] >= 3.0
    cone_x = [[s[0] - _CONE_R, s[0] + _CONE_R] for s in PL['speakers_plan']]
    SOUND_RULE['screen_x'] = [r2(XC + CR['xr'][0]), r2(XC + CR['xr'][1])]
    SOUND_RULE['screen_to_cone_x_gap'] = r2(min(XC + CR['xr'][0] - cone_x[0][1], cone_x[1][0] - (XC + CR['xr'][1])))

# ============================ cradle internals: connectors, ribbon, power wire ============================
FFC_W, FFC_T = 11.7, 0.3            # 22-pin 0.5 mm FFC: width ~11.7 (GUOCONN), thickness ~0.3
R_BEND, R_FOLD_ROLL = 3.0, 3.0
STIFF_OUT = 4.0                     # stiffener clear of the ZIF mouth before the first fold
INSERT = 3.5                        # contact length inside each ZIF
fpc = G['fpc']; pwr = G['pwr']
FOLD_SQ = dict(xr=[r2(fpc['mouth_xr'] + STIFF_OUT), r2(fpc['mouth_xr'] + STIFF_OUT + FFC_W)],
               u=[r2(fpc['pin_u_centre'] - FFC_W / 2), r2(fpc['pin_u_centre'] + FFC_W / 2)])
RIB_BAND_XR = FOLD_SQ['xr']                                 # descending band
RIB_XC = (RIB_BAND_XR[0] + RIB_BAND_XR[1]) / 2
WIRE_XR = [r2(RIB_BAND_XR[1] + 1.5), r2(RIB_BAND_XR[1] + 4.5)]   # 2 x AWG26-ish wires beside the band
GROOVE = dict(xr=[r2(RIB_BAND_XR[0] - 1.5), r2(WIRE_XR[1] + 1.5)], u=[CR['u0'], 3.0], w=[CR['w_screen_back'], CR['w_rib']],
              note='open at the bottom and at the back so the cables lie in from behind')
INSP = dict(xr=[15.5, 45.0], u=[33.0, 69.0])                  # inspection window in the plate (ZIF latch, MX1.25, fold)
INSP['cover'] = dict(flange=1.5, plug_under=0.2, t=2.0, dome=dict(xr=[FOLD_SQ['xr'][0] - 1, FOLD_SQ['xr'][1] + 1], u=[FOLD_SQ['u'][0] - 1, FOLD_SQ['u'][1] + 1],
                                                                    inner_to_w=r2(G['body'] + 2 * R_FOLD_ROLL + 3 * FFC_T + 0.3)))
HOLD_PAD = dict(xr=[r2(RIB_BAND_XR[0] - 0.5), r2(RIB_BAND_XR[1] + 0.5)], u=[8.0, 16.0], w=[r2(G['body'] + FFC_T + 0.3), CR['w_plate_in']],
                note='pad on the plate inner face presses the ribbon lightly (gap = ribbon + 0.3) - strain relief, + Kapton tape')

# lid hole (22 x 6 kept), centred on the groove
hole_xc = XC + (GROOVE['xr'][0] + GROOVE['xr'][1]) / 2
HOLE_XC = hole_xc
HOLE = dict(x=[r2(hole_xc - 11), r2(hole_xc + 11)], y=[r2(H[0] + 2), r2(H[0] + 8)], edge_R=1.0, wall=2.0)
hole_yc = (HOLE['y'][0] + HOLE['y'][1]) / 2
CLIP = dict(pad=dict(x=[r2(hole_xc - 15), r2(hole_xc + 15)], y=[r2(HOLE['y'][1] + HOLE['wall']), r2(HOLE['y'][1] + HOLE['wall'] + 12)],
                     z=[PL['lid']['bed_z'], PL['lid']['top_z'] - PL['lid']['plate_t']]),
            pins=[[r2(hole_xc - 12), r2(HOLE['y'][1] + HOLE['wall'] + 6)], [r2(hole_xc + 12), r2(HOLE['y'][1] + HOLE['wall'] + 6)]],
            pin_hole='3.1 x 5 blind from below', pin='3.0', clip='30 x 12 x 3 printed, ribbon clamped under the pad')
CLIP.update(t=3.0, pin_d=3.0, pin_hole_d=3.1, pin_hole_depth=5.0)
CLIP['pin_len'] = r2(CLIP['pin_hole_depth'] - 0.5)                  # pin sticks up from the clip top; 0.5 short of the hole bottom
WIRE_PAIR_D = 1.6                                                    # silicone jumper / MX1.25 lead, each (est. 1.3~1.6)
WIRE_UNDER_X = hole_xc + 8.0                                         # wire pair lane under the lid, beside the ribbon
CLIP['wire_groove'] = dict(x=[r2(WIRE_UNDER_X - (2 * WIRE_PAIR_D + 0.3) / 2), r2(WIRE_UNDER_X + (2 * WIRE_PAIR_D + 0.3) / 2)], depth=r2(WIRE_PAIR_D + 0.2),
                           along='y, full clip length', note='groove in the clip top face for the 2 power wires side by side; the flat part clamps only the ribbon')
CLIP['ribbon_edge_x'] = r2(hole_xc + FFC_W / 2); CLIP['pin_edge_x'] = r2(CLIP['pins'][1][0] - CLIP['pin_d'] / 2)
CLIP['groove_ok'] = CLIP['wire_groove']['x'][0] >= CLIP['ribbon_edge_x'] + 0.3 and CLIP['wire_groove']['x'][1] <= CLIP['pin_edge_x'] - 0.5
CLIP['clamp_z'] = [r2(PL['lid']['bed_z'] - FFC_T), PL['lid']['bed_z']]            # ribbon between the clip top and the pad underside
CLIP['clip_z'] = [r2(PL['lid']['bed_z'] - FFC_T - CLIP['t']), r2(PL['lid']['bed_z'] - FFC_T)]

# ---------- Pi 5 (placement default: long side along y, CAM/DISP 1 mouth facing the player (-y), right under the ribbon) ----------
PI_LOCAL = dict(board=[85.0, 56.0, 1.6], disp1=dict(x=[47.4, 50.1], y=[0.7, 16.2]), disp0=dict(x=[53.5, 56.3], y=[0.7, 16.2]),
                mouth_local=(-1, 0), gpio_2_4_6=dict(x=[8.37, 10.91, 13.45], y=53.77, ztop=8.5),
                heatsink=dict(x=[30, 41], y=[14, 31], h=8.0), hdmi=dict(x=[20, 43], y=[0, 7.5], h=3.2), usbc=dict(x=[3.5, 12.5], y=[0, 7.5], h=3.3))
def pi_pose(rot_deg, origin, board_top_z):
    c, s = round(math.cos(math.radians(rot_deg))), round(math.sin(math.radians(rot_deg)))
    def W(xl, yl): return (origin[0] + c * xl - s * yl, origin[1] + s * xl + c * yl)
    return W, (c, s)
CM_PI = CM.get('pi5') if isinstance(CM, dict) else None
_DIRV = {'+x': (1, 0), '-x': (-1, 0), '+y': (0, 1), '-y': (0, -1)}
def pi_rot_from_note(note):
    """local +x = toward the USB/RJ45 end, local +y = toward the GPIO edge. Parse the CAD note and return the rotation (deg);
       fail loudly if it cannot be parsed or would mirror the board."""
    m1 = re.search(r'USB/RJ45 end\s*([+-][xy])', note or ''); m2 = re.search(r'GPIO edge\s*([+-][xy])', note or '')
    if not (m1 and m2): raise SystemExit(f'Pi 5 orientation not understood from L2 note: {note!r}')
    ex, ey = _DIRV[m1.group(1)], _DIRV[m2.group(1)]
    if (-ex[1], ex[0]) != ey: raise SystemExit(f'Pi 5 orientation in L2 note would mirror the board: {note!r}')
    return int(round(math.degrees(math.atan2(ex[1], ex[0])))) % 360
if CM_PI and 'x' in CM_PI:
    PI_ROT = pi_rot_from_note(CM_PI.get('note'))      # final L2: 'USB/RJ45 end +x, GPIO edge +y' -> 0
    PI_TOP_Z = float(CM_PI['z'][0]) + PI_LOCAL['board'][2]
    _c, _s = round(math.cos(math.radians(PI_ROT))), round(math.sin(math.radians(PI_ROT)))
    _corners = [(_c * xl - _s * yl, _s * xl + _c * yl) for xl in (0, PI_LOCAL['board'][0]) for yl in (0, PI_LOCAL['board'][1])]
    PI_ORIGIN = (float(CM_PI['x'][0]) - min(p[0] for p in _corners), float(CM_PI['y'][0]) - min(p[1] for p in _corners))
    PI_FROM = f'final L2 (CAD bbox + orientation note "{CM_PI.get("note")}" -> rot {PI_ROT})'
else:
    PI_ROT = 90                   # provisional default: local x -> world +y ; local y (HDMI edge -> GPIO) -> world -x
    PI_TOP_Z = PL['floor_z'] + 6.0 + PI_LOCAL['board'][2]
    _, (c, s_) = pi_pose(PI_ROT, (0, 0), 0)
    PI_ORIGIN = ((XC + RIB_XC) - (c * PI_LOCAL['disp1']['x'][0] - s_ * sum(PI_LOCAL['disp1']['y']) / 2), (PL['lid']['y'][0] + PL['lid']['y'][1]) / 2 - 42.5)
    PI_FROM = 'provisional default'
disp_c_local = (PI_LOCAL['disp1']['x'][0], sum(PI_LOCAL['disp1']['y']) / 2)
_, (c, s) = pi_pose(PI_ROT, (0, 0), 0)
PIW, _ = pi_pose(PI_ROT, PI_ORIGIN, PI_TOP_Z)
def rect_world(xs, ys):
    pts_ = [PIW(x, y) for x in xs for y in ys]
    return [r2(min(p[0] for p in pts_)), r2(max(p[0] for p in pts_))], [r2(min(p[1] for p in pts_)), r2(max(p[1] for p in pts_))]
pi_board_x, pi_board_y = rect_world([0, 85], [0, 56])
d1x, d1y = rect_world(PI_LOCAL['disp1']['x'], PI_LOCAL['disp1']['y'])
d0x, d0y = rect_world(PI_LOCAL['disp0']['x'], PI_LOCAL['disp0']['y'])
mouth_w = PIW(PI_LOCAL['disp1']['x'][0], disp_c_local[1])
mouth_dir = (c * PI_LOCAL['mouth_local'][0] - s * PI_LOCAL['mouth_local'][1], s * PI_LOCAL['mouth_local'][0] + c * PI_LOCAL['mouth_local'][1])
gp2 = PIW(PI_LOCAL['gpio_2_4_6']['x'][0], PI_LOCAL['gpio_2_4_6']['y']); gp6 = PIW(PI_LOCAL['gpio_2_4_6']['x'][2], PI_LOCAL['gpio_2_4_6']['y'])
hs_x, hs_y = rect_world(PI_LOCAL['heatsink']['x'], PI_LOCAL['heatsink']['y'])
hd_x, hd_y = rect_world(PI_LOCAL['hdmi']['x'], PI_LOCAL['hdmi']['y'])
PI = dict(rot_deg=PI_ROT, origin=r2l(PI_ORIGIN), board_top_z=r2(PI_TOP_Z), board_x=pi_board_x, board_y=pi_board_y,
          disp1=dict(x=d1x, y=d1y, mouth=r2l(mouth_w), mouth_dir=list(mouth_dir), z=r2(PI_TOP_Z + 1.0)), disp0=dict(x=d0x, y=d0y),
          gpio_pin2=r2l(gp2), gpio_pin6=r2l(gp6), gpio_top_z=r2(PI_TOP_Z + PI_LOCAL['gpio_2_4_6']['ztop']),
          heatsink=dict(x=hs_x, y=hs_y, top_z=r2(PI_TOP_Z + PI_LOCAL['heatsink']['h'])), hdmi=dict(x=hd_x, y=hd_y, top_z=r2(PI_TOP_Z + PI_LOCAL['hdmi']['h'])),
          source=PI_FROM, cad_disp1=CM.get('disp1_connector') if isinstance(CM, dict) else None)
if PI['cad_disp1']:                                   # use the CAD connector box directly for the mouth (x face toward -x, centre y, mid z)
    dc = PI['cad_disp1']
    # the computed connector (local layout + parsed rotation) must match the CAD box, else the orientation reading is wrong -> stop
    PI['disp1_vs_cad'] = r2(max(abs(d1x[0] - dc['x'][0]), abs(d1x[1] - dc['x'][1]), abs(d1y[0] - dc['y'][0]), abs(d1y[1] - dc['y'][1])))
    if PI['disp1_vs_cad'] > 1.5: raise SystemExit(f'Pi 5 DISP1 from the parsed orientation {d1x},{d1y} differs from the CAD box {dc} by {PI["disp1_vs_cad"]}')
    mouth_w = (float(dc['x'][0]) if mouth_dir[0] < 0 else float(dc['x'][1]) if mouth_dir[0] > 0 else mid(dc['x']),
               mid(dc['y']) if mouth_dir[1] == 0 else (float(dc['y'][0]) if mouth_dir[1] < 0 else float(dc['y'][1])))
    PI['disp1'].update(mouth=r2l(mouth_w), z=r2(mid(dc['z'])), x=dc['x'], y=dc['y'])
    PI['disp1']['depth'] = r2(abs(dc['x'][1] - dc['x'][0]) if mouth_dir[0] != 0 else abs(dc['y'][1] - dc['y'][0]))
PL['pi5_mipi'] = dict(disp1_mouth_xyz=[r2(mouth_w[0]), r2(mouth_w[1]), PI['disp1']['z']], mouth_dir=list(mouth_dir),
                      long_axis='x' if PI_ROT in (0, 180) else 'y', gpio_2_6_xyz=[r2l(gp2), r2l(gp6), PI['gpio_top_z']], provisional=not bool(PI['cad_disp1']),
                      source=PI_FROM)

# ---------- ribbon frame tracker -> FFC type A (same side) / B (reverse) ----------
def rot(v, axis, ang):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis); v = np.asarray(v, float)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))
def track(steps, t0, n0):
    t, n = np.asarray(t0, float), np.asarray(n0, float); folds = 0
    for kind, tn in steps:
        tn = np.asarray(tn, float); tn = tn / np.linalg.norm(tn)
        if kind == 'bend':
            ax = np.cross(t, tn)
            if np.linalg.norm(ax) < 1e-9:
                if np.dot(t, tn) > 0: continue
                ax = np.cross(t, n)                       # 180 deg U-bend about the width axis
            ang = math.acos(max(-1, min(1, float(np.dot(t, tn)))))
            n = rot(n, ax, ang); t = tn
        elif kind == 'fold':                              # 45 deg crease/roll fold: in-plane 90 deg turn, face flips
            assert abs(np.dot(tn, n)) < 1e-6 and abs(np.dot(tn, t)) < 1e-6, 'fold must turn within the ribbon plane'
            n = -n; t = tn; folds += 1
    return t, n, folds
th = math.radians(TH_USE)
u_w = np.array([0, math.sin(th), math.cos(th)]); w_w = np.array([0, math.cos(th), -math.sin(th)])
n_screen = -w_w                                            # contacts face the screen's PCB (toward the glass)
t_start = np.array([CONN_SIDE * 1.0, 0, 0])                 # leaving the screen ZIF (mouth +x)
cradle_steps = [('fold', -u_w), ('bend', [0, 0, -1])]         # in-cradle 45 deg fold to run down; hinge loop to vertical in the lid hole

def route_under_lid(mouth_xyz, mdir, z_conn, obst_top=None, hole_x=None, rest=None):
    """Manhattan route below the lid: hole -> bend to run along y under the lid (through the clip) -> [45 deg fold to run along x]
       -> drop -> bend into the mouth. The run lies against the lid underside at the clip clamp height (bed - FFC_T/2).
       rest = (x_edge, top_z): an obstacle top (unused micro-HDMI) under the drop column: the ribbon lands on it and goes to the
       mouth from its edge at a shallow angle. Two 90 deg bends (down, then into the mouth) are NOT a U-bend: no extra length.
       Returns (length parts, tracker steps, waypoints xyz, z_under)."""
    xm, ym = mouth_xyz; d_in = (-mdir[0], -mdir[1])
    hole_xc = HOLE_XC if hole_x is None else hole_x
    z_top, z_bed = PL['lid']['top_z'], PL['lid']['bed_z']
    z_under = z_bed - FFC_T / 2
    APP = 3.0 + R_BEND                                   # stiffener + bend radius outside the mouth
    xd, yd = xm - d_in[0] * APP, ym - d_in[1] * APP     # descent point
    parts = dict(through_lid=r2(z_top - z_bed), down_to_run=r2(z_bed - z_under))
    steps = []; pts = [(hole_xc, hole_yc, z_top), (hole_xc, hole_yc, z_under)]
    L_corner = (2 - math.pi / 2) * R_BEND; nb = 0; nfold = 0; extra_u = 0.0
    x_leg = d_in[0] != 0                                 # mouth faces +-x -> last horizontal run along x (fold needed)
    sy = 1 if yd >= hole_yc else -1
    steps.append(('bend', [0, sy, 0])); nb += 1
    parts['run_y'] = r2(abs(yd - hole_yc)); pts.append((hole_xc, yd, z_under))
    if x_leg:
        sx = 1 if xd >= hole_xc else -1
        steps.append(('fold', [sx, 0, 0])); nfold += 1
        parts['run_x'] = r2(abs(xd - hole_xc)); pts.append((xd, yd, z_under)); last = (sx, 0)
    else:
        dx = xd - hole_xc
        if abs(dx) > 5.0:
            sx = 1 if dx > 0 else -1
            steps += [('fold', [sx, 0, 0]), ('fold', [0, sy, 0])]; nfold += 2
            parts['side_jog_x'] = r2(abs(dx)); pts[-1] = (hole_xc, yd - sy * 12, z_under); pts += [(xd, yd - sy * 12, z_under), (xd, yd, z_under)]
        last = (0, sy)
    steps.append(('bend', [0, 0, -1])); nb += 1
    z_land = z_conn if rest is None else max(z_conn, rest[1] + FFC_T / 2)
    parts['drop'] = r2(z_under - z_land); pts.append((xd, yd, z_land))
    steps.append(('bend', [d_in[0], d_in[1], 0])); nb += 1
    info = dict(turn_before_mouth='S' if (last[0] == d_in[0] and last[1] == d_in[1]) else 'two 90 deg bends (down, then into the mouth)',
                z_land=r2(z_land))
    if rest is not None and z_land > z_conn + 1e-9:
        ax = 0 if d_in[0] != 0 else 1; pe = [xd, yd]
        flat = max(0.0, (rest[0] - pe[ax]) * d_in[ax]); pe[ax] += d_in[ax] * flat
        pts.append((pe[0], pe[1], z_land))
        dh = abs((xm, ym)[ax] - pe[ax])
        parts['over_obstacle'] = r2(flat); parts['into_mouth'] = r2(math.hypot(dh, z_land - z_conn))
        info.update(rests_on='unused micro-HDMI (estimated top z%.2f)' % rest[1], approach_deg=r2(math.degrees(math.atan2(z_land - z_conn, dh))),
                    last_straight=r2(dh))
    else:
        parts['into_mouth'] = r2(APP)
    pts.append((xm, ym, z_conn))
    parts['fold_roll_allowance'] = r2(nfold * math.pi * R_FOLD_ROLL)
    parts['corner_rounding'] = r2(-L_corner * nb)
    info['column_x_rule'] = f'drop column = mouth - (stiffener 3.0 + R{R_BEND:g}) = {xd if d_in[0] else yd:.2f}'
    return parts, steps, [r2l(p) for p in pts], z_under, info

CRADLE_PARTS = dict(
    screen_insert=INSERT, screen_exit_to_fold=STIFF_OUT, fold_square=FFC_W, fold_roll_allowance=r2(math.pi * R_FOLD_ROLL),
    descend_to_cradle_bottom=r2(FOLD_SQ['u'][0] - CR['u0']), depth_jog=2.0)
# hinge loop: chord from the groove exit (u0, gap centre) to the hole top centre, at 22 / 25 / 90 deg
gap_w = (CR['w_screen_back'] + CR['w_plate_in']) / 2
def chord(th_):
    e = P(CR['u0'], gap_w, th_); return math.hypot(e[0] - hole_yc, e[1] - PL['lid']['top_z']), e
ch = {k: chord(v) for k, v in dict(heel=TH_HEEL, use=TH_USE, fold=TH_FOLD).items()}
LOOP_LEN = r2(max(22.0, max(c[0] for c in ch.values()) + 6.0))
def arc_R(c, s):
    lo_, hi_ = 1e-6, math.pi
    for _ in range(80):
        m = (lo_ + hi_) / 2
        if math.sin(m) / m > c / s: lo_ = m
        else: hi_ = m
    a = 2 * lo_; return s / a
loop = dict(length=LOOP_LEN, chord={k: r2(v[0]) for k, v in ch.items()}, groove_exit_yz={k: r2l(v[1]) for k, v in ch.items()},
            single_arc_R={k: r2(arc_R(v[0], LOOP_LEN)) for k, v in ch.items()},
            fwd_most_y_est=r2(min(v[1][0] for v in ch.values()) - 3.0))
CRADLE_PARTS['hinge_loop'] = LOOP_LEN
IN_CRADLE = r2(sum(CRADLE_PARTS.values()))

# Pi-end insertion: the CAD connector box is only 3.0 deep along the mouth -> never insert deeper than depth - 0.3
PI_INSERT = r2(min(INSERT, (PI['disp1'].get('depth') or INSERT + 0.3) - 0.3))
# unused micro-HDMI under the drop column: the ribbon rests on it (edge toward the mouth, estimated top)
_ax = 0 if mouth_dir[0] != 0 else 1
HDMI_REST = None
if PI.get('hdmi'):
    _hd = PI['hdmi']['x'] if _ax == 0 else PI['hdmi']['y']; _ho = PI['hdmi']['y'] if _ax == 0 else PI['hdmi']['x']
    _colc = (mouth_w[0], mouth_w[1])[_ax] + mouth_dir[_ax] * (3.0 + R_BEND)          # drop column along the mouth axis
    _band = (mouth_w[1], mouth_w[0])[_ax]
    if _hd[0] <= _colc <= _hd[1] and _ho[0] < _band + FFC_W / 2 and _ho[1] > _band - FFC_W / 2:
        HDMI_REST = (_hd[1] if -mouth_dir[_ax] > 0 else _hd[0], PI['hdmi']['top_z'])
def ribbon_for(mouth_xyz, mdir, z_conn, obst_top=None, cable=300.0, hole_x=None, conn_side=None, rest=None, pi_insert=INSERT):
    parts, steps, wpts, z_run, info = route_under_lid(mouth_xyz, mdir, z_conn, obst_top, hole_x, rest)
    tot = IN_CRADLE + sum(parts.values()) + pi_insert
    ts = t_start if conn_side is None else np.array([conn_side * 1.0, 0, 0])
    t_end, n_end, nf = track(cradle_steps + steps, ts, n_screen)
    n_pi_contact = np.array([0, 0, -1.0])                  # Pi 5 ZIF contacts face the Pi PCB (component side up)
    ffc = 'A (same side)' if float(np.dot(n_end, n_pi_contact)) > 0 else 'B (reverse)'
    return dict(parts=parts, total=r2(tot), cable=cable, margin=r2(cable - tot), ok=(cable - tot) >= 15.0, ffc_type=ffc,
                folds_total=int(nf), z_run=r2(z_run), end_normal=r2l(n_end), end_tangent=r2l(t_end), waypoints=wpts, route_info=info)
RIB = ribbon_for((mouth_w[0], mouth_w[1]), mouth_dir, PI['disp1']['z'], rest=HDMI_REST, pi_insert=PI_INSERT)
RIB['in_cradle_parts'] = CRADLE_PARTS; RIB['in_cradle_total'] = IN_CRADLE; RIB['loop'] = loop
RIB['screen_end_insert'] = INSERT; RIB['pi_end_insert'] = PI_INSERT
# clearances of the modelled ribbon to the estimated Pi parts (both estimates: check on the real Pi 5)
_wp = RIB['waypoints']; _col = _wp[-3] if HDMI_REST else _wp[-2]
RIB['pi_clearance'] = dict(
    heatsink_y_gap=r2(PI['heatsink']['y'][0] - (mouth_w[1] + FFC_W / 2)) if _ax == 0 else None,
    heatsink_x_gap=r2(_col[0] - FFC_T / 2 - PI['heatsink']['x'][1]) if _ax == 0 else None,
    heatsink_vs_cad_keepout_x=r2(PL['keepout_zones']['dsi']['x'][0] - PI['heatsink']['x'][1]) if PL['keepout_zones'].get('dsi') else None,
    hdmi_top_gap=r2(RIB['route_info']['z_land'] - FFC_T / 2 - PI['hdmi']['top_z']) if HDMI_REST else None,
    note='HDMI / heatsink boxes are estimates from a Pi 5 layout; the ribbon lies on the unused micro-HDMI as in the Waveshare photos. '
         'The drop column stays at the stiffener rule (mouth - 6); the CAD keep-out x582~600 wins over the heatsink estimate.')
RIB.update(ffc_w=FFC_W, ffc_t=FFC_T, bend_R=R_BEND, fold_roll_R=R_FOLD_ROLL, stiffener_out=STIFF_OUT)
# length function table: connector anywhere under the lid (z = Pi default), 4 mouth directions
RIB_TABLE = []
for mdir_ in [(0, -1), (1, 0), (-1, 0), (0, 1)]:
    for dx in [0, -40, 40, -80]:
        for yv in [260, 280, 300, 320]:
            r = ribbon_for((hole_xc + dx, yv), mdir_, PI['disp1']['z'])
            RIB_TABLE.append(dict(mouth_dir=list(mdir_), x=r2(hole_xc + dx), y=yv, total=r['total'], margin=r['margin'], ffc=r['ffc_type'][0], folds=r['folds_total']))
RIB['formula'] = (f'L ~= {IN_CRADLE + INSERT:.1f} (screen ZIF -> lid top, both insertions) + {PL["lid"]["top_z"] - PL["lid"]["bed_z"] + FFC_T / 2:.2f} (lid + under) '
                  f'+ |y_desc - {hole_yc:.1f}| + |x_desc - {hole_xc:.1f}| + ({PL["lid"]["bed_z"] - FFC_T / 2:.2f} - z_conn) + 6 (into mouth) '
                  f'+ 9.4 per 45 deg fold - 1.3 per 90 deg bend; desc = mouth - 6 mm outward; each 45 deg fold flips the FFC type '
                  f'(two 90 deg bends in a row are not a U-bend and add no length)')
# Waveshare standard (validation of the tracker): Pi on the screen back, U-loop, both ZIFs same convention -> Waveshare says B for Pi 5
tU, nU, _ = track([('bend', [0, 0, 0])] if False else [('bend', [-1, 0, 0])], [1, 0, 0], [0, 0, -1])
ws_check = 'B' if float(np.dot(nU, [0, 0, -1])) < 0 else 'A'

# ---------- power wire ----------
# the wire pair runs under the lid in the clip's wire groove (not squeezed under the ribbon), then -x to the GPIO header
z_w = r2(CLIP['clip_z'][1] - CLIP['wire_groove']['depth'] / 2)
gp_c = ((gp2[0] + gp6[0]) / 2, (gp2[1] + gp6[1]) / 2)
PW_WPTS = [(WIRE_UNDER_X, hole_yc, PL['lid']['top_z']), (WIRE_UNDER_X, hole_yc, z_w), (WIRE_UNDER_X, gp_c[1], z_w), (gp_c[0], gp_c[1], z_w), (gp_c[0], gp_c[1], PI['gpio_top_z'])]
_seg = [math.dist(PW_WPTS[k], PW_WPTS[k + 1]) for k in range(len(PW_WPTS) - 1)]
PW_DUPONT_SLACK = 15.0                                   # F/F housing on the pin + a little slack
PW_PARTS = dict(mx_exit_to_wire_lane=r2(WIRE_XR[0] - pwr['mouth_xr'] + 1.5), down_to_cradle_bottom=r2(sum(pwr['u']) / 2 - CR['u0']),
                hinge_loop=LOOP_LEN, lid_top_to_run=r2(_seg[0]), run_to_gpio=r2(sum(_seg[1:])), dupont_and_slack=PW_DUPONT_SLACK)
PW_TOTAL = r2(sum(PW_PARTS.values()))
WS_CABLE_EST = [100.0, 150.0]
PW = dict(parts=PW_PARTS, total=PW_TOTAL, waypoints=[r2l(p) for p in PW_WPTS], chain='screen MX1.25 2P -> Waveshare MX1.25-to-2.54 3P cable (~100~150 est.) -> M/M 20 cm -> F/F 20 cm -> GPIO pin 2 (5V red) / pin 6 (GND black)',
          available=[WS_CABLE_EST[0] + 400, WS_CABLE_EST[1] + 400],
          ws_cable_joint_needs=r2(PW_PARTS['mx_exit_to_wire_lane'] + PW_PARTS['down_to_cradle_bottom'] + LOOP_LEN + (PL['lid']['top_z'] - PL['lid']['bed_z']) + 5),
          count_note='every vertical and horizontal piece counted once from the waypoints: lid top -> run height (through the hole) -> +y -> -x -> up/down to the pin tip; rev 3 used the lid thickness (11.5) for the first piece and left out 3.5 below the lid',
          note='joint WS 3-pin housing <-> M/M sits under the lid if the WS cable >= ws_cable_joint_needs (in-cradle + hinge loop + lid thickness + 5); otherwise in the hinge loop (heat-shrink it; it passes the 22x6 hole)')

# ============================ power budget (fit_b formulas, S = 2.15 W) ============================
def power(S):
    avg = (13.3 + S / 0.9, 17.3 + S / 0.9); peak = 52 + S / 0.9
    return dict(S_W=S, avg_W=[r2(avg[0]), r2(avg[1])], peak_W=r2(peak), margin_60W=r2(60 - peak), w45_minus2dB=r2(37.0 + S / 0.9),
                battery_h=[r2(62.9 / avg[1]), r2(62.9 / avg[0])], rail_A=r2(2.0 + S / 5.1), pi_in_A=r2(1.6 + S / 5.1), screen_A_5V=r2(S / 5.0))
PWR = power(2.15)

# ============================ stability ============================
F = 10.0
du_top = G['act_u'][1] - UA
M_push = F * du_top / 1000
S = M_push / (arm / 1000)
t_ = math.radians(TH_USE); Wd = (math.cos(t_), -math.sin(t_))
m_scr = G['mass'] + 0.09
Fpush = (F * Wd[0], F * Wd[1]); Fs = (S * leg_dir[0], S * leg_dir[1]); Wg = (0, -m_scr * 9.81)
hinge_on_cradle = (-(Fpush[0] + Fs[0] + Wg[0]), -(Fpush[1] + Fs[1] + Wg[1]))
I_leg = LEG['b'] * LEG['t'] ** 3 / 12; Pcr = math.pi ** 2 * LEG['E'] * I_leg / L_LEG ** 2
heel_arm = abs(HEEL_REL22[0]); heel_F = M_push / (heel_arm / 1000)
screw_y = min(PL['lid_screw']['y']); support_y = PL['lid']['y'][0] + 1.5
lid_screw_F = M_push / ((screw_y - support_y) / 1000)
cg = P(G['h'] / 2, 6.0, TH_USE)
S_static = m_scr * 9.81 * (cg[0] - H[0]) / 1000 / (arm / 1000)
act_top = pts['use']['act_top']
m_cu = 3.3; cg_y = (PL['lid']['y'][0] + PL['rear_face_y']) / 2
M_over = Fpush[0] * act_top[1] / 1000 - (-Fpush[1]) * (PL['rear_face_y'] - act_top[0]) / 1000
M_res = m_cu * 9.81 * (PL['rear_face_y'] - cg_y) / 1000
STAB = dict(F=F, M_push=r2(M_push), leg_arm_mm=r2(arm), leg_force=r2(S), leg_static=r2(S_static), hinge_on_cradle=r2l(hinge_on_cradle),
            leg_Pcr=round(Pcr), leg_SF=r2(Pcr / S), heel_force=round(heel_F), lid_screws_total=round(lid_screw_F),
            lid_screw_arm=r2(screw_y - support_y), rear_bar_alone=dict(m_kg_est=m_cu, M_over=r2(M_over), M_res=r2(M_res), SF=r2(M_res / M_over)),
            note='rear-bar-alone case only happens when detached (screen folded for transport); attached to the key frame it is much more stable')

# ============================ vents ============================
_band = re.findall(r'y(\d+(?:\.\d+)?)~(\d+(?:\.\d+)?)', str(PL['cad_recommendations'].get('exhaust') or ''))
V_BAND = [float(_band[0][0]), float(_band[0][1])] if _band else [PL['lid']['y'][1] - 42, PL['lid']['y'][1] - 17]
V_ROWS, V_SLOT, V_LEN = 4, 4.0, 34.0
V_XR = [[-(pocket_half := (pocket['block']['x'][1] - pocket['block']['x'][0]) / 2) - 3 - V_LEN, -pocket_half - 3], [pocket_half + 3, pocket_half + 3 + V_LEN]]
V_PITCH = (V_BAND[1] - V_BAND[0] - V_SLOT) / (V_ROWS - 1)
VENT = dict(band_y=V_BAND, slot=[V_LEN, V_SLOT], rows=V_ROWS, pitch=r2(V_PITCH),
            slots=[[r2(XC + xr[0]), r2(XC + xr[1]), r2(V_BAND[0] + k * V_PITCH), r2(V_BAND[0] + k * V_PITCH + V_SLOT)] for k in range(V_ROWS) for xr in V_XR],
            note='CAD exhaust: 8 slots 4 x 34 behind the screen in the band y%g~%g; split left/right of the leg-pocket block, clear of the fold feet. Folded screen covers them (transport, power off)' % tuple(V_BAND))
# ============================ lid screws (CAD L2: seam rails 20x6 with M3 heat-set inserts, front 2 over the seam posts) ============================
_rail = SEAM['rail'][0]
RAIL_Z = [float(_rail[4]), float(_rail[5])] if _rail else [PL['lid']['bed_z'] - 6.0, PL['lid']['bed_z']]
LS_L, LS_INSERT = 10.0, 4.0                              # M3x10; heat-set insert length 4.0 (est.)
_lid_t = PL['lid']['top_z'] - PL['lid']['bed_z']         # screw boss filled to the bed plane
_under = LS_L - LS_INSERT
_cb = _lid_t - _under
LID_SCREW = dict(screw='M3x10 ISO 7380 (머리 Ø5.7 × 1.65)', x=PL['lid_screw']['x'], y=PL['lid_screw']['y'], boss_d=8.0, hole_d=3.4, cbore_d=6.5,
                 lid_t=r2(_lid_t), under_head=r2(_under), cbore_depth=r2(_cb), head_seat_z=r2(PL['lid']['top_z'] - _cb),
                 insert='M3 heat-set insert in the seam-rail top (length 4.0 est.)', insert_engage=LS_INSERT, insert_hole_depth=r2(LS_INSERT + 0.5),
                 tip_z=r2(PL['lid']['bed_z'] - LS_INSERT), rail_z=RAIL_Z, rail_floor_under_hole=r2(PL['lid']['bed_z'] - (LS_INSERT + 0.5) - RAIL_Z[0]),
                 posts_x=[p[0:2] for p in SEAM['post'] if p], rails_x=[p[0:2] for p in SEAM['rail'] if p],
                 rule='cbore depth = lid thickness at the screw (top - bed) - (10 - insert engagement); insert hole 0.5 deeper than the insert; x = lid edge +-5 = middle of the 10 mm the lid overlaps the rail',
                 estimate=True)
LID_SCREW['ok'] = LID_SCREW['rail_floor_under_hole'] >= 1.0 and LID_SCREW['under_head'] >= 4.0

# ============================ O4 service: lift the screen lid with the ribbon still plugged ============================
_clip_y1 = CLIP['pad']['y'][1]
L_to_clip = IN_CRADLE + INSERT + (PL['lid']['top_z'] - RIB['z_run']) + (_clip_y1 - hole_yc) - (2 - math.pi / 2) * R_BEND
free_route = RIB['total'] - L_to_clip
free_all = free_route + RIB['margin']                     # the spare length is kept as a loop between the clip and the 45 deg fold
_wpr = RIB['waypoints']; _colp = _wpr[3]                 # top of the drop column
_Q = (_colp[0], _colp[1], RIB['route_info']['z_land'] + R_BEND)
_L_Q = (RIB['route_info']['z_land'] + R_BEND - RIB['route_info']['z_land']) + RIB['parts'].get('over_obstacle', 0) + RIB['parts']['into_mouth'] + PI_INSERT
_avail = free_all - _L_Q - math.pi * R_FOLD_ROLL - 10.0   # 10 mm for bends / not quite straight
_dx, _dy = abs(hole_xc - _Q[0]), abs(_Q[1] - _clip_y1); _dz0 = RIB['z_run'] - _Q[2]
lift_max = math.sqrt(max(0.0, _avail ** 2 - _dx ** 2 - _dy ** 2)) - _dz0
SERVICE = dict(free_ribbon_after_clip=r2(free_route), with_spare=r2(free_all), lift_with_ribbon_plugged=r2(lift_max),
               steps_ko=['화면을 뒤로 접는다(다리는 클립에)', 'M3×10 4개를 푼다(앞 y%g, 뒤 y%g)' % (PL['lid_screw']['y'][0], PL['lid_screw']['y'][-1]),
                         '뚜껑을 화면째 천천히 든다(리본을 꽂은 채 약 %.0f mm까지)' % lift_max,
                         'Pi 5 CAM/DISP 1의 잠금 막대를 올리고 리본을 뺀다(화면 쪽 ZIF는 받침 안이라 건드리지 않음)',
                         'GPIO 2·6의 암-암 점퍼 2개를 뺀다', '뚜껑을 옆에 둔다 → O4 플러그 작업', '되돌릴 때: 리본 B형 방향 확인 후 잠금, 점퍼 2번 빨강·6번 검정, 나사 4개'],
               spare_loop_where='클립과 45° 접기 사이 (뚜껑 밑): 뚜껑을 들 때 이 여유가 풀림',
               note='lift estimate: straight line from the clip exit to the top of the drop column, minus 10 mm for bends')

# ============================ corner-stud fallback (bored bosses, plate and axis unchanged) ============================
STUD_H = G['body_studs'] - G['body']
STUD_BORE_D = 6.2                                        # fits a round stud <= 5.8 or a 5 mm hex (across corners 5.77)
_bore_to = G['body_studs'] + 0.3
_floor = CR['w_rib'] - _bore_to
M25_HEAD = (4.5, 1.8)
_heads = [(XC + xb, H[0] + (ub - UA)) for xb in G['holes_xr'] for ub in G['holes_u']]
def _circ_rect_gap(c, r, rx, ry):
    dx = max(rx[0] - c[0], 0, c[0] - rx[1]); dy = max(ry[0] - c[1], 0, c[1] - ry[1]); return math.hypot(dx, dy) - r
_feet_rects = [(f['x'], f['y']) for f in FEET] + [(f['x'], f['lip']['y']) for f in FEET if f['rear']]
STUDS_BORED = dict(bore_d=STUD_BORE_D, bore_w=[G['body'], r2(_bore_to)], boss_d=max(8.0, STUD_BORE_D + 2.4), floor_t=r2(_floor),
                   screw='M2.5x6 from the back through the boss floor into the stud thread; head sits on the rib face w%g (no counterbore)' % CR['w_rib'],
                   engage=r2(6.0 - _floor), head_out=M25_HEAD[1], fold_head_bottom_z=r2(FOLD['rib_plane_z'] - M25_HEAD[1]),
                   fold_head_to_lid=r2(FOLD['rib_plane_z'] - M25_HEAD[1] - PL['lid']['top_z']),
                   fold_head_to_feet_plan=r2(min(_circ_rect_gap(hc, M25_HEAD[0] / 2, rx, ry) for hc in _heads for rx, ry in _feet_rects)),
                   note='only if the corner features are pressed studs (cannot be removed): the studs go into the bores, the screen back still '
                        'rests on the boss rims at w8, so the plate and the hinge axis do not move')
STUDS_BORED['ok'] = STUDS_BORED['engage'] >= 2.0 and STUDS_BORED['fold_head_to_lid'] > 0.5 and STUDS_BORED['fold_head_to_feet_plan'] > 0.5

# ============================ checks ============================
KO = PL['keepout']
CHK = dict(
    keepout_min_y=r2(all_min_y), keepout_margin=r2(all_min_y - KO['y_max']), keepout_ok=all_min_y > KO['y_max'],
    cables_fwd_min_y=loop['fwd_most_y_est'], cables_ok=loop['fwd_most_y_est'] > KO['y_max'],
    fold_rear_margin=FOLD['rear_margin'], fold_rear_ok=FOLD['rear_margin'] >= 2.0,
    fold_speaker_margin=FOLD['speaker_margin'], fold_height_ok=FOLD['top_z'] < PL['speaker_top_z'],
    lid_x_margin=[r2(XC + CR['xr'][0] - PL['lid']['x'][0]), r2(PL['lid']['x'][1] - (XC + CR['xr'][1]))],
    pocket_back_material=r2(PL['lid']['y'][1] - pocket['back_wall_y']),
    leg_stow_ok=stow_tip_u <= CR['u1'] - STOW_MARGIN, fold_leg_clear_lid=r2(fold_clevis_zmin - PL['lid']['top_z']),
    fold_clip_clear_lid=r2(fold_clip_zmin - PL['lid']['top_z']),
    ribbon_ok=RIB['ok'], sound_paths_min=r2(min(p['dist_to_screen'] for p in paths)),
    heel_gap_at_25=r2(heel_gap25), sightline_z_at_module=r2(z_at_mod), sightline_ok=z_at_mod > KO['z_min'],
    cheek_gap_min=r2(min(cheek_checks.values())), rib_relief_needed=min(cheek_checks.values()) < 0.5,
    # rev 3a checks (fix round)
    ear_block_gap_22=EAR_CHECK['gap_at_22'], ear_block_gap_25_90=EAR_CHECK['min_gap_25_90'], ear_block_ok=EAR_CHECK['ok'],
    axle_head_gap=AXLE_CHECK['min_head_gap'], axle_path_gap=AXLE_CHECK['min_path_gap'], axle_ok=AXLE_CHECK['ok'],
    leg_swing_22_ok=SWING['ok_at_22'], leg_swing_25_overlap=SWING['at_25']['worst_overlap'],
    notch_margin=[r2(G['bottom_feature']['xr'][0] - NOTCH['xr'][0]), r2(NOTCH['xr'][1] - G['bottom_feature']['xr'][1])],
    notch_ok=min(G['bottom_feature']['xr'][0] - NOTCH['xr'][0], NOTCH['xr'][1] - G['bottom_feature']['xr'][1]) >= 5.0 and NOTCH['u'][1] - NOTCH['u'][0] >= 2.0,
    clip_groove_ok=CLIP['groove_ok'], lid_screw_ok=LID_SCREW['ok'], sound_rule_ok=bool(SOUND_RULE and SOUND_RULE['ok']),
    pi_orientation_ok=PI.get('disp1_vs_cad', 0.0) <= 1.5, power_wire_ok=PW_TOTAL < PW['available'][0], studs_fallback_ok=STUDS_BORED['ok'],
    sightline_centre_z_at_module=r2(z_at_mod_centre))

N = dict(
    rev=3, revision='3a (fix round 2026-10-01: ear outline, u24 rib, bottom notch, clip wire groove, ribbon on HDMI, power-wire count, service, studs fallback)', date='2026-10-01', placement=PL,
    screen=dict(model='Waveshare 7-DSI-TOUCH-C (7" 1024x600 IPS, 5-pt capacitive Goodix over I2C in the DSI FFC)', glass=[G['w'], G['h']], body=G['body'],
                body_with_studs=G['body_studs'], active=[G['act_w'], G['act_h']], active_offsets=G['act_off'], x_centre=XC,
                glass_x=[r2(XC + G['glass_xr'][0]), r2(XC + G['glass_xr'][1])], active_x=[r2(XC + G['act_xr'][0]), r2(XC + G['act_xr'][1])],
                active_u=r2l(G['act_u']), holes=dict(xr=r2l(G['holes_xr']), u=r2l(G['holes_u']), x=[r2(XC + v) for v in G['holes_xr']], thread='M2.5', depth='unknown'),
                pi_holes=G['pi_holes'], window=dict(xr=r2l(G['window']['xr']), u=G['window']['u']), fpc=dict(xr=r2l(fpc['xr']), u=fpc['u'], pin_u_centre=fpc['pin_u_centre'],
                mouth_xr=r2(fpc['mouth_xr']), mouth='+x', x=[r2(XC + v) for v in fpc['xr']]), pwr=dict(xr=r2l(pwr['xr']), u=pwr['u'], mouth_xr=r2(pwr['mouth_xr']), mouth='+x'),
                emboss=dict(xr=r2l(G['emboss']['xr']), u=G['emboss']['u'], h=G['emboss']['h']), mass_kg_est=G['mass'], conn_side=CONN_SIDE,
                orientation_evidence='drawing back view = front view flipped about the horizontal axis (photos: Pi 5 hole mirror 44/102 mm, cable x 116 vs 49 mm, power above FPC)'),
    cradle=dict(xr=r2l(CR['xr']), x=[r2(XC + CR['xr'][0]), r2(XC + CR['xr'][1])], u=[CR['u0'], CR['u1']], w=[CR['w0'], CR['w_rib']],
                size=[r2(CR['xr'][1] - CR['xr'][0]), r2(CR['u1'] - CR['u0']), r2(CR['w_rib'] - CR['w0'])], rim=RIM, clr=CLR,
                w_screen_back=CR['w_screen_back'], plate=[CR['w_plate_in'], CR['w_plate_out']], rib=[CR['w_plate_out'], CR['w_rib']],
                emboss_clearance=r2(CR['w_plate_in'] - G['body'] - G['emboss']['h']),
                bosses=dict(xr=r2l(G['holes_xr']), u=r2l(G['holes_u']), d=8.0, face_w=G['body'], seat_w=r2(G['body'] + 3.0), cbore_d=5.5, hole_d=2.8,
                            screw='M2.5x6', engage=3.0, w=[G['body'], CR['w_rib']],
                            fill_to_side_wall=dict(xr=[[-CR['walls']['side_inner_xr'], r2(G['holes_xr'][0])], [r2(G['holes_xr'][1]), CR['walls']['side_inner_xr']]], width_u=8.0,
                                                   note='each boss joined to the side wall by a block 8 wide (u) over w8..16')),
                walls=CR['walls'], notch=NOTCH,
                pads=PADS, groove=GROOVE, insp=INSP, hold_pad=HOLD_PAD, fold_square=FOLD_SQ, rib_band_xr=RIB_BAND_XR, wire_xr=WIRE_XR, cross_ribs_u=CROSS_RIBS_U,
                rib_t=RIB_T, cross_ribs_note=f'low rib moved u{U_P:g} -> u{U_RIB_LOW:g} (off the leg-axle line); both cut at the leg channel xr±7.3',
                ear=dict(profile_uw=EAR_PROFILE_OUT,
                         hub=dict(u=UA, w=WA, R=EAR_HUB_R), heel_uw=r2l(HEEL_LOCAL), front_edge=[r2l(HEEL_LOCAL), r2l(EAR_EDGES['front_to'])],
                         lower_edge=[r2l(HEEL_LOCAL), r2l(EAR_EDGES['lower_tangent'])], back_edge=[r2l(EAR_EDGES['back_from']), r2l(EAR_EDGES['back_tangent'])],
                         attach=dict(u=CR['u0'], w=[CR['w_screen_back'], WA]), min_u=r2(EAR_MIN_U), check=EAR_CHECK,
                         note='convex hull of hub R4.2 (u-9, w13), bottom attachment (u-2.5, w8..13) and the heel point only; the heel is the lowest ear point at 22 deg'),
                print_height=r2(CR['u1'] - EAR_MIN_U), axle_check=AXLE_CHECK,
                rib_relief_at_cheeks=dict(needed=CHK['rib_relief_needed'], chamfer=RIB_CHAMFER, gap_after=r2(RIB_CHAMFER_GAP), gaps_without=cheek_checks)),
    hinge=dict(axis_yz=list(H), axis_cradle_uw=[UA, WA], tilt_use_deg=TH_USE, heel_contact_deg=TH_HEEL, cheek_R=CHEEK_R, ear_hub_R=EAR_HUB_R,
               heel_rel22=list(HEEL_REL22), heel_R=r2(hr), heel_stop_z=r2(heel_stop_z), heel_stop_h=HEEL_STOP_H, heel_contact_yz=r2l(heel_contact),
               heel_gap_at_25=r2(heel_gap25), left=HINGES['left'], right=HINGES['right'],
               left_x=[r2(XC + v) for v in HINGES['left']['xr']], right_x=[r2(XC + v) for v in HINGES['right']['xr']],
               ear_x=dict(left=[r2(XC + v) for v in HINGES['left']['ear']], right=[r2(XC + v) for v in HINGES['right']['ear']]),
               ear_slot_x=dict(left=[r2(XC + v) for v in HINGES['left']['ear_slot']], right=[r2(XC + v) for v in HINGES['right']['ear_slot']]),
               heel_block=dict(y=[r2(H[0] + HEEL_BLOCK_REL[0]), r2(H[0] + HEEL_BLOCK_REL[1])], z=[PL['lid']['top_z'], r2(heel_stop_z)], x='ear slots'),
               ear_check=EAR_CHECK,
               knuckle_profile=dict(R=CHEEK_R, base_y=[r2(H[0] - KNUCKLE_BASE_HALF), r2(H[0] + KNUCKLE_BASE_HALF)],
                                    at_axis_y=[r2(H[0] - CHEEK_R), r2(H[0] + CHEEK_R)], base_z=PL['lid']['top_z'], axis_z=H[1]),
               front_reach=r2(front_reach), front_reach_what=front_reach_what),
    points=pts, sweep_min_y=r2(sweep_min_y), knuckle_front_y=r2(knuckle_front_y), all_min_y=r2(all_min_y), sweep_min_z=r2(sweep_min_z), sweep_max_z=r2(sweep_max_z),
    fold=FOLD, fold_feet=FEET,
    leg=dict(pivot_cradle_uw=[U_P, LEG['w_p']], pivot_yz=r2l(piv), tip_yz=r2l(tip), length=L_LEG, x=[r2(XC - 5), r2(XC + 5)], xr=LEG['xr'],
             section=[LEG['b'], LEG['t']], angle_deg=r2(leg_ang), stow_tip_u=r2(stow_tip_u), pocket=pocket, fold_leg_z=list(fold_leg_z),
             fold_clevis_zmin=fold_clevis_zmin, fold_clip_zmin=fold_clip_zmin, fold_leg_y=list(fold_leg_y), pivot_shift_at_22=r2(piv_shift), clevis=LEG['clevis'], clip=LEG['clip'],
             channel=LEG['channel'], candidates_top5=[dict(arm=r2(c[0]), u_p=c[1], L=c[2], tip_y=r2(c[3]['tip'][0]), ang=r2(c[3]['ang'])) for c in cands[:5]],
             axle=AXLE, pivot22_yz=r2l(piv22), swing=SWING, pocket_edge_C=POCKET_EDGE_C),
    eye=dict(eye=list(EYE), angle_to_centre=r2(eye_ang), tilt_diff=r2(eye_ang - TH_USE), angle_range=[r2(min(eye_rng)), r2(max(eye_rng))],
             dist_to_centre=r2(eye_dist), sightline_z_at_module=r2(z_at_mod), sightline_z_at_module_is='sightline to the BOTTOM of the visible area',
             sightline_centre_z_at_module=r2(z_at_mod_centre), px_mm=round(px_mm, 4), arcmin_per_px=r2(arcmin(px_mm, eye_dist)),
             arcmin_32px=r2(arcmin(32 * px_mm, eye_dist))),
    footprint_y=dict(front_22=pts['heel']['cr_bot_front'][0], front_25=pts['use']['cr_bot_front'][0], rear_25=pts['use']['cr_top_rib'][0],
                     front_22_90=r2(all_min_y), note='plan footprint of the standing cradle: 22 deg (heel) front vs 25 deg (use) front'),
    lid_screw=LID_SCREW, service_O4=SERVICE, sound_rule=SOUND_RULE,
    reach=reach, paths=paths, screen_rect_plan=[r2(v) for v in scr_rect],
    O4=dict(offset=r2(XC - CTX['O4_white_centre_x']), scale=round(G['act_w'] / CTX['octave'], 3), two_oct_white_px=r2(1024 / 14), two_oct_white_mm=r2(G['act_w'] / 14)),
    hole=HOLE, clip=CLIP, vents=VENT, pi5=PI,
    ribbon=RIB, ribbon_table=RIB_TABLE, ffc_tracker_check_waveshare_std=ws_check,
    power_wire=PW, power=PWR, stability=STAB, checks=CHK,
    sensor_gap=r2(all_min_y - CTX['sensor_y']), context=CTX,
)
# ---------- rev-2 compatible keys ----------
N['folded_top'] = FOLD['top_z']
N['folded_y'] = FOLD['y']
N['fold_feet_detail'] = FEET
N['fold_feet'] = [[f['x'][0], f['x'][1], f['y'][0], f['y'][1]] for f in FEET]
N['eye']['sightline_z_at_y212'] = N['eye']['sightline_z_at_module']
N['ribbon']['margin_pct'] = r2(RIB['margin'] / RIB['cable'] * 100)
N['ribbon']['loop_chord'] = loop['chord']
N['stability'].update(cu_unit_M_over=STAB['rear_bar_alone']['M_over'], cu_unit_M_res=STAB['rear_bar_alone']['M_res'], cu_unit_SF=STAB['rear_bar_alone']['SF'])
N['power'].update(avg_after=PWR['avg_W'], peak=[52.0, PWR['peak_W']], margin_60W_after=PWR['margin_60W'], pi_usbc_A=PWR['pi_in_A'], rail_A_after=PWR['rail_A'],
                  life_after=PWR['battery_h'], screen_at_5V_A=PWR['screen_A_5V'])

# ---------- variants ----------
def axis_for(wa_extra):
    """if the plate/axis plane moves back by wa_extra (e.g. protruding corner studs), recompute axis y and fold rear"""
    b = (WA + wa_extra) - CR['w0']; a = CR['u0'] - UA
    fr = max(b * math.cos(math.radians(TH_HEEL)) - a * math.sin(math.radians(TH_HEEL)), KNUCKLE_BASE_HALF)
    hy = PL['keepout']['y_max'] + PL['keepout']['clearance'] + fr
    return dict(axis_y=r2(hy), fold_rear_y=r2(hy + CR['u1'] - UA), rear_margin=r2(PL['lid']['y'][1] - (hy + CR['u1'] - UA)),
                fold_top_z=r2(H[1] + (WA + wa_extra - CR['w0'])))
STUD_H = G['body_studs'] - G['body']
N['variants'] = dict(
    corner_studs=dict(stud_h=r2(STUD_H), plate_moves_back=r2(max(0, G['body'] + STUD_H - CR['w_plate_in'])),
                      result=axis_for(max(0, G['body'] + STUD_H - CR['w_plate_in'])),
                      note='what would happen if the plate moved back over protruding studs (NOT the plan): rear margin goes negative -> use corner_studs_bored'),
    corner_studs_bored=STUDS_BORED,
    rev2_frame_b17=dict(result=axis_for(CR['w_rib'] - WA), note='axis at the rib face w16 as in rev 2 (b=17): shown to explain why rev 3 puts the axis on the plate back w13'),
    connector_mirrored=dict(note='if the FPC turns out on the left (mouth -x), mirror every connector-side item about x=XC',
                            ribbon=(lambda r: dict(total=r['total'], margin=r['margin'], ffc_type=r['ffc_type'], folds=r['folds_total'], waypoints=r['waypoints']))(
                                ribbon_for((mouth_w[0], mouth_w[1]), mouth_dir, PI['disp1']['z'], hole_x=2 * XC - HOLE_XC, conn_side=-CONN_SIDE,
                                           rest=HDMI_REST, pi_insert=PI_INSERT)),
                            notch_xr=NOTCH['xr'], notch_note='the bottom-edge notch follows the FRONT view (not the connector side) -> it does not move',
                            hole_x=[r2(2 * XC - HOLE['x'][1]), r2(2 * XC - HOLE['x'][0])], groove_xr=[r2(-GROOVE['xr'][1]), r2(-GROOVE['xr'][0])],
                            insp_xr=[-INSP['xr'][1], -INSP['xr'][0]], clip_pins_x=[r2(2 * XC - p[0]) for p in CLIP['pins']]))

# ---------- print mass estimate (primitive volumes) ----------
_W = CR['xr'][1] - CR['xr'][0]; _Hc = CR['u1'] - CR['u0']; _D = CR['w_rib'] - CR['w0']
vol = (2 * _Hc + 2 * _W) * RIM * _D                                        # perimeter walls
vol += (_W * _Hc - (INSP['xr'][1] - INSP['xr'][0]) * (INSP['u'][1] - INSP['u'][0])) * CR['plate_t']   # plate minus window
vol += 2 * _W * 2.0 * CR['rib_h'] + 2 * (CR['u1'] - U_P) * 2.0 * CR['rib_h'] + 4 * 16 * 16 * CR['rib_h']   # cross ribs, channel walls, pads
vol += 4 * math.pi * (8.0 / 2) ** 2 * (CR['w_rib'] - G['body']) + 2 * 8.0 * (CR['u0'] - UA + EAR_HUB_R) * 10.0 + 2 * math.pi * 3.8 ** 2 * 10
leg_vol = LEG['b'] * LEG['t'] * (L_LEG + 6)
N['mass_est'] = dict(cradle_g=r2(vol / 1000 * 1.27 * 0.9), cradle_h=r2(vol / 1000 * 1.27 * 0.9 / 22.0), leg_g=r2(leg_vol / 1000 * 1.27 * 0.9),
                     note='rough: PETG 1.27 g/cm3, 90 % solid, ~22 g/h on the P2S')
# ---------- 3D poses: world = M @ [xr, u, w, 1] ----------
def M_cradle(th):
    t = math.radians(th); s_, c_ = math.sin(t), math.cos(t)
    return [[1, 0, 0, XC], [0, r2(s_ * 1e6) / 1e6, r2(c_ * 1e6) / 1e6, r2(H[0] - UA * s_ - WA * c_)],
            [0, r2(c_ * 1e6) / 1e6, r2(-s_ * 1e6) / 1e6, r2(H[1] - UA * c_ + WA * s_)], [0, 0, 0, 1]]
leg_u = ((tip[0] - piv[0]) / L_LEG, (tip[1] - piv[1]) / L_LEG)
N['poses'] = dict(
    note='cradle local (xr, u, w) -> world (x, y, z): [x,y,z,1] = M @ [xr,u,w,1]; det = -1 (u,w frame is left-handed). For a proper rotation use v = -w: M_v = M with column 3 negated.',
    cradle_use=M_cradle(TH_USE), cradle_heel=M_cradle(TH_HEEL), cradle_fold=M_cradle(TH_FOLD),
    leg_use=dict(pivot_xyz=[XC, r2(piv[0]), r2(piv[1])], dir_pivot_to_tip=[0, r2(leg_u[0]), r2(leg_u[1])], length=L_LEG),
    leg_stowed=dict(pivot_cradle=[0, U_P, LEG['w_p']], dir_cradle=[0, 1, 0], note='lies along +u in the channel, w13.5..19.5'),
    pi5=dict(rot_deg=PI_ROT, origin_xy=r2l(PI_ORIGIN), board_top_z=r2(PI_TOP_Z)))
json.dump(N, open(OUT / 'numbers.json', 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    print('source', SRC.name, 'final' if IS_FINAL else 'provisional')
    print('H', H, 'front reach', r2(front_reach), front_reach_what)
    print('use', json.dumps(pts['use'])); print('heel front', pts['heel']['cr_bot_front'], 'fold', FOLD)
    print('sweep_min_y', r2(sweep_min_y), 'all_min_y', r2(all_min_y), 'sweep z', r2(sweep_min_z), r2(sweep_max_z))
    print('cheek gaps', cheek_checks, 'chamfer', RIB_CHAMFER, r2(RIB_CHAMFER_GAP))
    print('heel gap25', r2(heel_gap25), 'heel R', r2(hr))
    print('leg', dict(u_p=U_P, L=L_LEG, piv=r2l(piv), tip=r2l(tip), ang=r2(leg_ang), arm=r2(arm)), 'pocket', pocket)
    print('fold leg z', fold_leg_z, 'clevis zmin', fold_clevis_zmin)
    print('feet', FEET)
    print('eye', N['eye'], 'reach', reach)
    print('ribbon', json.dumps(RIB, default=str)[:1500])
    print('pi', PI)
    print('power wire', PW)
    print('power', PWR)
    print('stab', STAB)
    print('checks', CHK)
    print('paths', [p['dist_to_screen'] for p in paths], 'ws tracker check', ws_check)
    print('EAR', EAR_CHECK, 'edges', {k: r2l(v) for k, v in EAR_EDGES.items()}, 'print h', r2(CR['u1'] - EAR_MIN_U))
    print('AXLE', AXLE_CHECK)
    print('SWING', SWING)
    print('NOTCH', NOTCH)
    print('CLIP', CLIP)
    print('LID_SCREW', LID_SCREW)
    print('SERVICE', SERVICE)
    print('STUDS', STUDS_BORED)
    print('SOUND', SOUND_RULE)
    print('RIB route', RIB['route_info'], RIB['parts'], RIB['total'], RIB['margin'], RIB['ffc_type'], RIB['pi_clearance'])
    print('mirrored', N['variants']['connector_mirrored']['ribbon'])
