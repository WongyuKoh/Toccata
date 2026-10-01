# Assemble design.json + texts.json + CAD_SPEC_rev3.md + README_rev3.md for R31 touchscreen rev 3a (B1 on L2).
# Every number comes from numbers.json (written by geom3.py). Korean texts, plain and short.
import json
from pathlib import Path
D = Path(__file__).resolve().parent
N = json.load(open(D / 'numbers.json'))
PL = N['placement']; XC = PL['x_centre']; LID = PL['lid']; KO = PL['keepout']
U, HL, F = N['points']['use'], N['points']['heel'], N['points']['fold']
S, CR, HG, HO, CL, V, LG, FO = N['screen'], N['cradle'], N['hinge'], N['hole'], N['clip'], N['vents'], N['leg'], N['fold']
RB, PW, PWR, ST, E, CK, PI, RE = N['ribbon'], N['power_wire'], N['power'], N['stability'], N['eye'], N['checks'], N['pi5'], N['reach']
PK = LG['pocket']; BO = CR['bosses']; INS = CR['insp']; GR = CR['groove']; HP = CR['hold_pad']; FS = CR['fold_square']
VAR = N['variants']; EAR = CR['ear']; AX = CR['axle_check']; SW = LG['swing']; NT = CR['notch']; WL = CR['walls']
LS = N['lid_screw']; SV = N['service_O4']; SR = N['sound_rule']; SB = VAR['corner_studs_bored']; FP = N['footprint_y']; RI = RB['route_info']
R2 = json.load(open(D / 'rev2_src' / 'numbers.json'))   # rev 2 values for the comparison column
r2h, r2c, r2l_, r2u = R2['hinge'], R2['cradle'], R2['leg'], R2['points']['use']
R3 = json.load(open(D / 'rev3a_before' / 'numbers.json'))   # first rev-3 run (before the review fix round)
SRC = '확정본 L2_cu.json' if PL['source_is_final'] else '임시값 L2_cu_provisional.json (확정값이 오면 geom3.py를 다시 돌림)'
CTX_O4 = N['context']['O4_white_centre_x']
def X(xr): return XC + xr
def xrng(xr, nd=2): return f'x{X(xr[0]):.{nd}f}~{X(xr[1]):.{nd}f}'
def uw(p): return f'(u{p[0]:g}, w{p[1]:g})'
def r2(v): return round(float(v), 2)
hL, hR = HG['left'], HG['right']
EX, ES = HG['ear_x'], HG['ear_slot_x']
rib_lo = CR['cross_ribs_u'][0]
sw25, sw22 = SW['at_25'], SW['at_22']
pi_note = PI['source'].split('"')[1] if '"' in PI['source'] else PI['source']

# ============================ summary ============================
summary_ko = (
 f"화면은 사용자가 고른 B1, Waveshare 7-DSI-TOUCH-C(7인치 1024×600, 유리 {S['glass'][0]}×{S['glass'][1]}, 두께 {S['body']})입니다. "
 f"자리는 L2 뒷바의 가운데 뚜껑(x{LID['x'][0]:g}~{LID['x'][1]:g}, y{LID['y'][0]:g}~{LID['y'][1]:g}, 윗면 z{LID['top_z']}) 위입니다. 화면 가운데는 x{XC:g}입니다. "
 f"경첩 축은 y{HG['axis_yz'][0]} z{HG['axis_yz'][1]}입니다. 이 값은 '모듈 위(y≤{KO['y_max']:g}, z≥{KO['z_min']})에 아무것도 없게' 규칙에서 계산했습니다. "
 f"화면은 25° 뒤로 기울여 섭니다. 보이는 영역 가운데는 y{U['act_centre'][0]} z{U['act_centre'][1]}입니다. "
 f"가장 앞 부품은 y{N['all_min_y']}라서 모듈 위로 넘어가지 않습니다(여유 {CK['keepout_margin']} mm). "
 f"구조는 2판과 같습니다: 뚜껑의 경첩 2개, 받침 귀와 뒤꿈치(22°에서 멈춤), 받침 뒤 받침다리(뚜껑 주머니에 발), 뒤로 접기. "
 f"접으면 z{FO['top_z']}까지이고 y{FO['y'][0]}~{FO['y'][1]}에 놓여 뚜껑 뒤끝 y{LID['y'][1]:g} 안에 {FO['rear_margin']} mm 남습니다. "
 f"화면은 받침 뒤에서 M2.5×6 나사 4개로 네 모서리 구멍(154×88)에 고정합니다. "
 f"DSI 리본(22핀 0.5 mm)은 L2 Pi CAM/DISP 1까지 약 {RB['total']:.0f} mm라 300 mm로 {RB['margin']:.0f} mm 남고, {RB['ffc_type'][0]}형(반대면)입니다. "
 f"3a(검수 반영)에서 여러 곳을 고쳤습니다. 귀 옆모양은 뒤꿈치 한 점만 남겼고, 아래 가로 리브는 u{rib_lo:g}로 옮겼습니다. 아래 벽에 홈을 내고 클립에 전원선 홈을 두었습니다. 다리는 22°에서 넣습니다.")

changes = [
 ('화면', f"Touch Display 2 7인치 유리 {R2['screen']['glass'][0]}×{R2['screen']['glass'][1]}", f"7-DSI-TOUCH-C {S['glass'][0]}×{S['glass'][1]}×{S['body']} (가로 기본, 돌리지 않음)"),
 ('자리', f"L1 CU 뚜껑 (화면 가운데 x{R2['screen']['x_centre']:g})", f"L2 가운데 뚜껑 x{LID['x'][0]:g}~{LID['x'][1]:g}, y{LID['y'][0]:g}~{LID['y'][1]:g}, z{LID['top_z']}"),
 ('화면 가운데 x', f"{R2['screen']['x_centre']:g}", f"{XC:g}"),
 ('경첩 축', f"y{r2h['axis_yz'][0]:g} z{r2h['axis_yz'][1]:g}", f"y{HG['axis_yz'][0]} z{HG['axis_yz'][1]} (모듈 위 금지 규칙에서 계산)"),
 ('축 자리(받침 좌표)', f"u{r2h['axis_cradle_uw'][0]:g}, w{r2h['axis_cradle_uw'][1]:g} (뒤 리브 면)", f"u{HG['axis_cradle_uw'][0]:g}, w{HG['axis_cradle_uw'][1]:g} (뒷판 뒷면) → 앞 돌출 {r2h['axis_cradle_uw'][1] - r2c['w'][0]:g}→{HG['axis_cradle_uw'][1] - CR['w'][0]:g}"),
 ('받침 크기', f"{r2c['size'][0]}×{r2c['size'][1]}×{r2c['size'][2]:g}", f"{CR['size'][0]}×{CR['size'][1]}×{CR['size'][2]}"),
 ('화면 고정', '러그 4개 M2.5 (TD2)', f"모서리 구멍 4개({S['holes']['x'][1]-S['holes']['x'][0]:g}×{S['holes']['u'][1]-S['holes']['u'][0]:g}) M2.5×6, 보스 Ø{BO['d']:g}(옆벽까지 채움)"),
 ('뒤꿈치', f"뚜껑 윗면에 닿음, 축에서 R{r2h['heel_R']}", f"귀 홈 바닥에 {HG['heel_stop_h']:g} mm 멈춤 블록, 축에서 R{HG['heel_R']}"),
 ('경첩 x', f"x{r2h['left']['x'][0]:g}~{r2h['left']['x'][1]:g} · x{r2h['right']['x'][0]:g}~{r2h['right']['x'][1]:g} (나사 +x)", f"x{HG['left_x'][0]}~{HG['left_x'][1]} · x{HG['right_x'][0]}~{HG['right_x'][1]} (대칭, 나사는 바깥에서)"),
 ('리본 구멍', f"x{R2['hole']['x'][0]:g}~{R2['hole']['x'][1]:g}, y{R2['hole']['y'][0]:g}~{R2['hole']['y'][1]:g}", f"x{HO['x'][0]}~{HO['x'][1]}, y{HO['y'][0]}~{HO['y'][1]} (22×6 그대로)"),
 ('DSI 커넥터', f"15핀 1 mm, x≈{R2['screen']['dsi']['x_centre']}, 입구 {R2['screen']['dsi']['opens']}", f"22핀 0.5 mm, {xrng(S['fpc']['xr'])}, u{S['fpc']['u'][0]}~{S['fpc']['u'][1]}, 입구 +x"),
 ('리본', f"FIT0997 22→15핀 {R2['ribbon']['cable']:g} mm", f"GUOCONN 22핀 0.5 mm {RB['cable']:g} mm {RB['ffc_type'][0]}형 (A형은 예비)"),
 ('점검창', 'ㄴ자 창', f"네모 창 {xrng(INS['xr'], 1)}, u{INS['u'][0]:g}~{INS['u'][1]:g} + 접힘 자리 볼록 덮개"),
 ('받침다리', f"u{r2l_['pivot_cradle_uw'][0]:g}·w{r2l_['pivot_cradle_uw'][1]:g} 축, {r2l_['length']:g} mm, {r2l_['angle_deg']}°", f"u{LG['pivot_cradle_uw'][0]:g}·w{LG['pivot_cradle_uw'][1]} 축, {LG['length']:g} mm, {LG['angle_deg']}°"),
 ('다리 주머니', f"경사 앞 y383.5 (v13 기록), 뒷벽 y{r2l_['pocket']['back_wall_y']}", f"경사 앞 y{PK['ramp_front_y']}, 뒷벽 y{PK['back_wall_y']}"),
 ('접은 높이', f"z{R2['hinge']['axis_yz'][1]:g}~{R2['folded_top']:g}", f"z{FO['rib_plane_z']}~{FO['top_z']}"),
 ('접이 받침 발', f"16×16×8, x{R2['fold_feet'][0][0]:g}~{R2['fold_feet'][0][1]:g}·{R2['fold_feet'][2][0]:g}~{R2['fold_feet'][2][1]:g}", f"16×16×{FO['feet_h']:g}, x{N['fold_feet'][0][0]:g}~{N['fold_feet'][0][1]:g}·{N['fold_feet'][2][0]:g}~{N['fold_feet'][2][1]:g}, 뒤 발에 턱"),
 ('받침 뒤 패드 (v13 ⑥)', 'x566~582·730~746, u53~69 (v13 기록)', f"xr±{CR['pads'][2]['xr'][0]:g}~{CR['pads'][2]['xr'][1]:g}, u{CR['pads'][0]['u'][0]:g}~{CR['pads'][0]['u'][1]:g}·u{CR['pads'][1]['u'][0]:g}~{CR['pads'][1]['u'][1]:g} (4개)"),
 ('채움 바닥 (v13 ②)', 'z76.5 (v13 기록)', f"z{LID['bed_z']} (L2 뚜껑 리브 밑면)"),
 ('통풍 슬롯 (v13 ③)', 'y302~397 (v13 기록)', f"화면 뒤 배기 {len(V['slots'])}개 {V['slot'][0]:g}×{V['slot'][1]:g}, y{V['band_y'][0]:g}~{V['band_y'][1]:g} (CAD L2 배기 자리)"),
 ('리본 클립 핀 (v13 ④)', 'x592.05·616.05, y320 (v13 기록)', f"x{CL['pins'][0][0]}·{CL['pins'][1][0]}, y{CL['pins'][0][1]}, 핀 길이 {CL['pin_len']:g}"),
 ('다리 클립 턱 (v13 ⑤)', 'w22.52부터 (v13 기록)', f"w{LG['clip']['catch_from_w']}부터, u{LG['clip']['u'][0]:g}~{LG['clip']['u'][1]:g}"),
 ('받침 아래 뒤 모서리', '없음', f"C{CR['rib_relief_at_cheeks']['chamfer']:g} 모따기 (경첩 볼과 틈 {CR['rib_relief_at_cheeks']['gap_after']})"),
 ('뚜껑 고정', 'D23 모서리 받침 + 앞 나사 2', f"L2 레일 인서트 M3×10 4개 (y{PL['lid_screw']['y'][0]:g}·{PL['lid_screw']['y'][-1]:g}), 자리파기 Ø{LS['cbore_d']:g}×{LS['cbore_depth']:g}"),
]

# rev 3 (first run) -> 3a: what the review changed
L3 = EAR['check']['rev3_first_lobe']
old_hdmi_pen = r2(PI['hdmi']['top_z'] - R3['ribbon']['waypoints'][-2][2])
old_pw_missing = r2(LID['bed_z'] - R3['power_wire']['waypoints'][1][2])
old_spec_h = R3['cradle']['size'][1] + (R3['cradle']['u'][0] - R3['hinge']['axis_cradle_uw'][0]) + R3['hinge']['ear_hub_R']
fix3a = [
 ('귀 옆모양', f"뒤꿈치 옆에 점이 하나 더 있음 {uw(L3['lobe_uw'])} → 22°에서 멈춤 블록을 {-L3['gap_at_22']:g} mm, 25°에서 {-L3['gap_at_25']:g} mm 파고듦 → 약 {L3['clears_from_deg']:g}°에서 멈춰 25°로 못 씀",
  f"축 원 R{EAR['hub']['R']:g} + 받침 아래 u{EAR['attach']['u']}(w{EAR['attach']['w'][0]:g}~{EAR['attach']['w'][1]:g}) + 뒤꿈치 {uw(EAR['heel_uw'])}만 감싼 모양. 블록과 22°에서 {EAR['check']['gap_at_22']}(닿음), 25~90°에서 {EAR['check']['min_gap_25_90']} 이상"),
 ('출력 높이', f"약 {old_spec_h:.0f}(사양) / {L3['print_height']}(도면, 잘못된 점) — 서로 다름", f"{CR['print_height']} (u{CR['u'][1]} − 뒤꿈치 u{EAR['min_u']})"),
 ('아래 가로 리브', f"u{R3['cradle']['cross_ribs_u'][0]:g} (다리 축 줄) → 축 나사 머리가 {-AX['rev3_u30_rib']['head_gap']:g} mm 파고들고 넣는 길이 막힘",
  f"u{rib_lo:g} (u{rib_lo - 1:g}~{rib_lo + 1:g}) → 머리·넣는 길과 {AX['min_head_gap']} mm 이상"),
 ('아래 벽 홈', '없음 (화면 아래 끝 작은 돌기가 걸림)', f"xr{NT['xr'][0]:g}~{NT['xr'][1]:g} (x{X(NT['xr'][0]):g}~{X(NT['xr'][1]):g}), u{NT['u'][0]}~{NT['u'][1]:g} 관통, w{NT['w'][0]:g}~{NT['w'][1]:g}"),
 ('벽·보스', '모델과 사양이 다름(모델은 아래 벽에도 틈, 보스가 따로 섬)', f"아래 벽 안쪽 u0(유리가 얹힘), 위 틈 {WL['top_gap']:g}, 옆 틈 {WL['side_gap']:g}; 보스는 옆벽까지 채움"),
 ('리본 클립', '납작한 30×12×3 (전원선이 리본을 들어 올림)', f"윗면에 전원선 홈 x{CL['wire_groove']['x'][0]}~{CL['wire_groove']['x'][1]}, 깊이 {CL['wire_groove']['depth']:g}; 핀 길이 {CL['pin_len']:g}"),
 ('뚜껑 밑 리본 높이', f"z{R3['ribbon']['z_run']} (클립과 안 맞음)", f"z{RB['z_run']} (뚜껑 밑면에 붙고 클립에 물림 z{CL['clamp_z'][0]}~{CL['clamp_z'][1]})"),
 ('리본 끝 (Pi 쪽)', f"z{R3['ribbon']['waypoints'][-2][2]:g}까지 곧게 내려와 U자로 셈(+{R3['ribbon']['parts']['u_bend_extra']}), 추정 HDMI를 {old_hdmi_pen:g} mm 파고듦, 꽂는 길이 {R3['ribbon']['pi_end_insert']:g}",
  f"기둥 x{RB['waypoints'][3][0]:g} 그대로(입구 − 보강판 3 − R3). 안 쓰는 HDMI 위(z{RI['z_land']})에 얹혀 {RI['approach_deg']}°로 입구에 들어감. 꽂는 길이 {RB['pi_end_insert']:g}(커넥터 깊이 {PI['disp1']['depth']:g} − 0.3)"),
 ('리본 길이', f"{R3['ribbon']['total']} mm (여유 {R3['ribbon']['margin']})", f"{RB['total']} mm (여유 {RB['margin']})"),
 ('전원선 길이', f"{R3['power_wire']['total']} (뚜껑 두께 {R3['power_wire']['parts']['through_lid']:g}만 셈, 뚜껑 밑 {old_pw_missing:g} 빠짐)", f"{PW['total']} (길 점으로 한 번씩 셈: 뚜껑 윗면→홈 높이 {PW['parts']['lid_top_to_run']}, 뚜껑 밑 {PW['parts']['run_to_gpio']})"),
 ('소리 길', f"스피커 추정 자리로 {R3['checks']['sound_paths_min']}", f"body_L2 유닛 가운데(x{PL['speakers_plan'][0][0]:g}/{PL['speakers_plan'][1][0]:g}, y{PL['speakers_plan'][0][1]:g})로 {CK['sound_paths_min']}; 27° 규칙 {SR['clear_above_module_edge']} mm"),
 ('다리 넣기', '순서 없음', f"화면을 22°(뒤꿈치)에 댄 채 넣고 뺌. 25°에서 넣으면 발이 뒷벽 위 모서리를 {-sw25['worst_overlap']:g} mm 긁음"),
 ('뚜껑 나사 자리', '값 없음 (모델과 도면이 서로 다름)', f"Ø{LS['cbore_d']:g} × {LS['cbore_depth']:g} 자리파기(머리 자리 z{LS['head_seat_z']}), 레일 인서트 물림 {LS['insert_engage']:g} (추정)"),
 ('O4 정비', '없음', f"뚜껑을 화면째 들고 Pi 쪽 ZIF를 풂. 리본을 꽂은 채 약 {SV['lift_with_ribbon_plugged']:.0f} mm 들 수 있음"),
 ('스터드가 박혀 있을 때', '스터드를 뗌 (못 뗄 수도 있음)', f"보스를 Ø{SB['bore_d']:g}로 w{SB['bore_w'][1]}까지 파고 뒤에서 나사 (뒷판·축 그대로)"),
 ('Pi 방향', '회전 0을 손으로 넣음', f"L2 글 \"{pi_note}\"에서 읽음. CAD 커넥터 상자와 {PI['disp1_vs_cad']} mm 안에서 맞는지 확인(틀리면 멈춤)"),
 ('낱말', "'귀 자리'가 귀와 귀 홈 둘 다를 뜻함", f"귀 = 받침 쪽 x{EX['left'][0]}~{EX['left'][1]}(8.0), 귀 홈 = 뚜껑 볼 사이 x{ES['left'][0]}~{ES['left'][1]}(8.4)"),
]

# ============================ CAD spec (Markdown) ============================
chg_rows = '\n'.join(f'| {a} | {b} | {c} |' for a, b, c in changes)
fix_rows = '\n'.join(f'| {a} | {b} | {c} |' for a, b, c in fix3a)
pads_txt = ', '.join(f"(xr{p['xr'][0]:g}~{p['xr'][1]:g}, u{p['u'][0]:g}~{p['u'][1]:g})" for p in CR['pads'])
feet = N['fold_feet_detail']
feet_txt = '; '.join(f"x{f['x'][0]}~{f['x'][1]}, y{f['y'][0]}~{f['y'][1]}" + (' (턱 있음)' if f['rear'] else '') for f in feet)
lip = feet[1]['lip']
ear_edges = (f"앞 변은 뒤꿈치 {uw(EAR['front_edge'][0])} → 받침 아래 {uw(EAR['front_edge'][1])} 곧은 선. "
             f"받침 아래 변은 u{EAR['attach']['u']} (w{EAR['attach']['w'][0]:g}~{EAR['attach']['w'][1]:g})로 받침 아래 벽에 붙음. "
             f"뒤 변은 {uw(EAR['back_edge'][0])} → 축 원 접점 {uw(EAR['back_edge'][1])}. "
             f"축 원 R{EAR['hub']['R']:g}(중심 u{EAR['hub']['u']:g}, w{EAR['hub']['w']:g})를 뒤쪽으로 돌아 접점 {uw(EAR['lower_edge'][1])}. "
             f"아래 변은 접점 {uw(EAR['lower_edge'][1])} → 뒤꿈치 {uw(EAR['lower_edge'][0])} 곧은 선.")
rib_x0 = HO['x'][0] + 11 - RB['ffc_w'] / 2
spec = f"""# R31 터치스크린 — CAD 요청 사양 수정 3판 3a (B1: Waveshare 7-DSI-TOUCH-C, L2 뒷바)

작성 2026-10-01 · 좌표는 L2 world mm (x = A0 왼쪽에서 가로, y = 흰건반 앞끝에서 뒤로, z = 책상에서 위로) · 그림 `touch_concept_rev3.svg`
수치 출처: `numbers.json` (geom3.py가 L2 값에서 계산). L2 값: **{SRC}** · 스피커 유닛 자리: body_L2.json 사본(md5 {PL['body_L2']['md5']}, 저장소와 {'같음' if PL['body_L2']['same_as_repo'] else '다름 — 다시 복사할 것'}).
표시: 【새로】 3판에서 새로 생김, 【변경】 2판·v13과 다름, 【그대로】 v13 규칙을 그대로 씀, **【3a】 검수 뒤 이번에 고침**.

## 0. 자리 블록 (이 값 하나에서 모든 좌표를 계산)
| 항목 | 값 |
|---|---|
| 화면 가운데 x (XC) | {XC:g} |
| 뚜껑 x / y / 윗면 z | x{LID['x'][0]:g}~{LID['x'][1]:g} / y{LID['y'][0]:g}~{LID['y'][1]:g} / z{LID['top_z']} (판 {LID['plate_t']:g}, 리브 밑면 = 출력 바닥 z{LID['bed_z']}) |
| 모듈 위 금지 | y ≤ {KO['y_max']:g} 이면서 z ≥ {KO['z_min']} 에 화면 부품·선 없음 (여유 {KO['clearance']:g}) |
| 경첩 축 y / z | y{HG['axis_yz'][0]} / z{HG['axis_yz'][1]} — {PL['hinge_axis_rule']} |
| Pi 5 (L2 확정) | 방향 "{pi_note}" → 회전 {PI['rot_deg']}° · CAM/DISP 1 x{PI['disp1']['x'][0]}~{PI['disp1']['x'][1]}, y{PI['disp1']['y'][0]}~{PI['disp1']['y'][1]}, 입구 x{PL['pi5_mipi']['disp1_mouth_xyz'][0]:g} z{PL['pi5_mipi']['disp1_mouth_xyz'][2]} 방향 −x, 깊이 {PI['disp1']['depth']:g} · 리본 기둥 x{PL['keepout_zones']['dsi']['x'][0]}~{PL['keepout_zones']['dsi']['x'][1]}, y{PL['keepout_zones']['dsi']['y'][0]}~{PL['keepout_zones']['dsi']['y'][1]} |
| Pi 5 GPIO 2·6 | ({PI['gpio_pin2'][0]}, {PI['gpio_pin2'][1]}) · ({PI['gpio_pin6'][0]}, {PI['gpio_pin6'][1]}), 핀 끝 z{PI['gpio_top_z']} |
| 뚜껑 고정 (L2) | M3×10 4개: y{', y'.join(f'{v:g}' for v in PL['lid_screw']['y'])}, x≈{PL['lid_screw']['x'][0]:g}·{PL['lid_screw']['x'][1]:g} (이음 레일 x{LS['rails_x'][0][0]:g}~{LS['rails_x'][0][1]:g}·{LS['rails_x'][1][0]:g}~{LS['rails_x'][1][1]:g}, z{LS['rail_z'][0]}~{LS['rail_z'][1]}, 인서트) |
| 통풍 슬롯 | 화면 뒤 배기 {len(V['slots'])}개 {V['slot'][0]:g}×{V['slot'][1]:g}: x{V['slots'][0][0]:g}~{V['slots'][0][1]:g} · x{V['slots'][1][0]:g}~{V['slots'][1][1]:g}, y{V['band_y'][0]:g}~{V['band_y'][1]:g} (간격 {V['pitch']:g}) |
| 스피커 | 윗면 z{PL['speaker_top_z']:g}, 뒷면 y{PL['rear_face_y']:g}, 유닛 가운데 x{PL['speakers_plan'][0][0]:g} / x{PL['speakers_plan'][1][0]:g}, y{PL['speakers_plan'][0][1]:g} (body_L2) |

받침 좌표: xr = x − {XC:g}, u = 유리 아래 끝에서 화면 위쪽으로, w = 유리 앞면에서 뒤로. world = M·[xr, u, w, 1] (M은 numbers.json `poses`).
L2 값이 바뀌면 `python3 geom3.py && python3 build3.py && python3 draw3.py && python3 build3d.py`만 다시 돌리면 모든 수치가 바뀝니다.

## 3a에서 고친 것 (검수 반영)
| 항목 | 3판 처음 | 3a |
|---|---|---|
{fix_rows}

## 2판·v13과 달라진 것
| 항목 | 2판 / v13 | 3판 (3a) |
|---|---|---|
{chg_rows}

## A. 가운데 뚜껑 (L2 뚜껑에 더할 것)
뚜껑 자체(판, 리브, 뒤 자석, 이음 레일)는 CAD 세션의 L2 설계를 따릅니다. 아래는 화면 때문에 더하는 것입니다.
1) 【변경】 경첩 받침 2개(뚜껑과 한 몸). 폭 20.4 = 먼 볼 8.0 + 귀 홈 8.4 + 가까운 볼 4.0. 귀 홈(볼 사이) 8.4 = 귀 8.0 + 틈 0.2 × 2. 나사는 바깥쪽 가까운 볼에서 넣습니다.
   - 왼쪽: 가까운 볼 {xrng(hL['near_cheek'], 1)}, 귀 홈 x{ES['left'][0]:.1f}~{ES['left'][1]:.1f}, 먼 볼 {xrng(hL['far_cheek'], 1)} (나사 −x 쪽에서)
   - 오른쪽: 먼 볼 {xrng(hR['far_cheek'], 1)}, 귀 홈 x{ES['right'][0]:.1f}~{ES['right'][1]:.1f}, 가까운 볼 {xrng(hR['near_cheek'], 1)} (나사 +x 쪽에서)
   - 볼 옆모양(y-z): 축 (y{HG['axis_yz'][0]}, z{HG['axis_yz'][1]}) 둘레 R{HG['cheek_R']} + 아래로 넓어지는 사다리꼴(z{HG['axis_yz'][1]}에서 y{HG['knuckle_profile']['at_axis_y'][0]}~{HG['knuckle_profile']['at_axis_y'][1]}, z{LID['top_z']}에서 y{HG['knuckle_profile']['base_y'][0]}~{HG['knuckle_profile']['base_y'][1]}). 축 위로 R{HG['cheek_R']} 밖으로 나오면 안 됩니다.
   - 가까운 볼 Ø3.3 관통, 먼 볼 Ø2.5 × 8 (M3×20 직접 탭, 물림 7.6).
   - 【새로】 뒤꿈치 멈춤 블록: 귀 홈 바닥을 z{HG['heel_stop_z']}까지 올립니다(뚜껑 윗면 + {HG['heel_stop_h']:g}). x = 귀 홈, y{HG['heel_block']['y'][0]}~{HG['heel_block']['y'][1]}. 22°에서 귀의 뒤꿈치가 (y{HG['heel_contact_yz'][0]}, z{HG['heel_contact_yz'][1]})에 닿습니다.
   - 【그대로】 경첩 받침 밑은 출력 바닥 z{LID['bed_z']}까지 채웁니다.
2) 【변경】 리본·전원선 구멍 22×6: x{HO['x'][0]}~{HO['x'][1]}, y{HO['y'][0]}~{HO['y'][1]} 관통, 위아래 모서리 R{HO['edge_R']:g}. 둘레 벽 {HO['wall']:g} mm를 z{LID['bed_z']}까지 채웁니다. CAD 권장(x{PL['cad_recommendations']['ribbon_hole']['x'][0]}~{PL['cad_recommendations']['ribbon_hole']['x'][1]}, y{PL['cad_recommendations']['ribbon_hole']['y'][0]}~{PL['cad_recommendations']['ribbon_hole']['y'][1]})과 다른 이유: 화면 커넥터가 오른쪽(+x)이라 받침 안 리본이 x{X(CR['rib_band_xr'][0]):.1f}~{X(CR['rib_band_xr'][1]):.1f}로 내려옵니다. 구멍 밑은 L2 앞 빈 공간(y{PL['front_zone_y'][0]:g}~{PL['front_zone_y'][1]:g})입니다.
3) 【변경】 받침다리 주머니: x{PK['x'][0]:g}~{PK['x'][1]:g}. 앞 30° 경사는 (y{PK['ramp_front_y']}, z{LID['top_z']}) → (y{PK['ramp_end_y']}, z{PK['bottom_z']}). 바닥 z{PK['bottom_z']}는 y{PK['floor_y'][0]}~{PK['floor_y'][1]}. 뒷벽 y{PK['back_wall_y']} 수직(위 모서리 C{LG['pocket_edge_C']:g}).
   - 경사 앞끝 규칙(v13 ①을 다시 계산): 다리를 반지름 3 캡슐로 보고 경사·윗면과 0.2 mm 이상 떨어지게 함. 2판 규칙(y{PK['ramp_front_y_rev2_rule']})이면 {-PK['ramp_clear_rev2_rule']} mm 파고듦 → y{PK['ramp_front_y']}로 당김(최소 틈 {PK['ramp_min_clear']}).
   - 【3a】 다리는 화면을 22°(뒤꿈치)에 댄 채 넣고 뺍니다(D 참조). 뒷벽 위 모서리를 더 깎는 방법은 쓰지 않습니다. 발이 뒷벽에 닿는 점(z{LG['tip_yz'][1]})이 바로 그 모서리 아래라서 깎으면 발 자리가 없어집니다.
   - 【그대로】 주머니 밑 덩어리 x{PK['block']['x'][0]:g}~{PK['block']['x'][1]:g}, y{PK['block']['y'][0]}~{PK['block']['y'][1]}를 z{LID['bed_z']}까지 채웁니다.
4) 【변경】 접이 받침 발 4개 16×16, 높이 {FO['feet_h']:g} (z{LID['top_z']}~{FO['rib_plane_z']}): {feet_txt}.
   - 【새로】 뒤 발 2개에 턱: y{lip['y'][0]}~{lip['y'][1]}, z{lip['z'][0]}~{lip['z'][1]} (접은 받침이 뒤로 밀리지 않게).
5) 【변경】 리본 클립 자리: 뚜껑 밑 덩어리 x{CL['pad']['x'][0]}~{CL['pad']['x'][1]}, y{CL['pad']['y'][0]}~{CL['pad']['y'][1]}, z{CL['pad']['z'][0]}~{CL['pad']['z'][1]}(출력 바닥까지 채움). 밑에서 막힌 구멍 Ø{CL['pin_hole_d']:g} × {CL['pin_hole_depth']:g} 두 개: ({CL['pins'][0][0]}, {CL['pins'][0][1]}), ({CL['pins'][1][0]}, {CL['pins'][1][1]}). 클립(E-2)이 밑에서 리본을 덩어리 밑면에 눌러 잡습니다.
6) 【변경】 통풍(배기) 슬롯 {len(V['slots'])}개, 각 {V['slot'][0]:g}(x) × {V['slot'][1]:g}(y): 왼쪽 줄 x{V['slots'][0][0]:g}~{V['slots'][0][1]:g}, 오른쪽 줄 x{V['slots'][1][0]:g}~{V['slots'][1][1]:g}, y = {', '.join(f"{sl[2]:g}~{sl[3]:g}" for sl in V['slots'][::2])}. CAD L2의 "화면 뒤 배기 y{V['band_y'][0]:g}~{V['band_y'][1]:g}, {len(V['slots'])}×({V['slot'][1]:g}×{V['slot'][0]:g})"를 다리 주머니 덩어리 양옆으로 나눔. 접으면 덮임(운반 때, 전원 끔).
7) 【변경】【3a】 뚜껑 나사 자리 (L2 CAD 설계: 이음 레일 20×6 윗면의 M3 인서트, 앞 2개는 기둥 위): M3×10 4개, y{', y'.join(f'{v:g}' for v in LS['y'])}, x{LS['x'][0]:g}·{LS['x'][1]:g} (뚜껑 끝 ±5 = 레일 위 겹침 10 mm의 가운데).
   - 뚜껑 쪽: Ø{LS['boss_d']:g} 기둥을 z{LID['bed_z']}까지 채움, 구멍 Ø{LS['hole_d']:g}, 위에서 Ø{LS['cbore_d']:g} × {LS['cbore_depth']:g} 자리파기(머리 자리 z{LS['head_seat_z']}). 머리 밑 뚜껑 살 {LS['under_head']:g}.
   - 레일 쪽(CAD): 인서트 물림 {LS['insert_engage']:g}(추정), 인서트 구멍 깊이 {LS['insert_hole_depth']:g} 이상 → 나사 끝 z{LS['tip_z']}, 구멍 밑 레일 살 {LS['rail_floor_under_hole']:g}.
   - 규칙: 자리파기 깊이 = 나사 자리 뚜껑 두께 {LS['lid_t']:g} − (10 − 인서트 물림). CAD가 인서트 길이를 바꾸면 이 식으로 다시 잡습니다(추정 값).
   - 앞 기둥 x{LS['posts_x'][0][0]:g}~{LS['posts_x'][0][1]:g} · x{LS['posts_x'][1][0]:g}~{LS['posts_x'][1][1]:g}: 나사 x{LS['x'][0]:g}·{LS['x'][1]:g}이 기둥 안쪽 모서리 위에 옵니다. 인서트가 레일 안에 있어서 괜찮습니다. CAD가 기둥을 안쪽으로 2 옮기면 나사 밑이 기둥 가운데가 됩니다(CAD가 정함).
   - 받침 x{CR['x'][0]}~{CR['x'][1]}에서 {CR['x'][0]-LS['x'][0]:.1f} mm 밖이라 화면을 세운 채 풀 수 있습니다. 경첩 받침·받침 발과 겹치지 않습니다.
8) 자석은 뚜껑 뒤에만 둡니다. 화면·경첩·다리에는 자석이 없습니다(D14).
9) 출력: 리브 면을 베드에. 경첩 받침·주머니 덩어리·구멍 벽·클립 덩어리·나사 기둥은 모두 출력 바닥 z{LID['bed_z']}까지 채워 서포트 없이 뽑습니다. x 방향 구멍(Ø3.3, Ø2.5)은 물방울 모양으로 뽑고 드릴로 다듬습니다.

## B. 뚜껑 고정과 O4 정비
- 【변경】 L2에서는 D23의 나사형 모서리 받침 대신 레일 인서트에 M3×10 4개를 씁니다(앞 y{PL['lid_screw']['y'][0]:g}, 뒤 y{PL['lid_screw']['y'][-1]:g}, A-7). 자석은 옆 뚜껑에만 있고 화면 쪽에는 없습니다(D14).
- 앞으로 10 N 당길 때(뒤꿈치 {ST['heel_force']} N과 경첩이 짝힘) 앞 나사 두 개 합계 약 {ST['lid_screws_total']} N (앞 나사 y{PL['lid_screw']['y'][0]:g}와 뚜껑 앞 받침 사이 {ST['lid_screw_arm']} mm 기준).
- 【3a】 O4 정비(O4 USB 플러그가 화면 뚜껑 밑에 있음 — CAD 요청 "리본을 쉽게 뽑게"):
{chr(10).join(f'  {k + 1}. {s}' for k, s in enumerate(SV['steps_ko']))}
  - 리본 여유 {RB['margin']:.0f} mm는 {SV['spare_loop_where']}에 둡니다. 클립에서 Pi까지 풀린 리본은 약 {SV['free_ribbon_after_clip']:.0f} mm(여유 포함 {SV['with_spare']:.0f})입니다. 그래서 꽂은 채 약 {SV['lift_with_ribbon_plugged']:.0f} mm 들 수 있습니다(곧은 선 − 굽힘 10, 추정).
  - 뽑는 곳은 Pi 쪽 CAM/DISP 1입니다. 화면 쪽 ZIF는 받침 안(점검창 덮개 밑)이라 정비 때 건드리지 않습니다.

## C. 화면 받침(크래들) 새 STL, PETG
받침 좌표 xr·u·w (위 0장). 화면은 굵은 테두리(9.65)가 아래, 커넥터 창이 오른쪽(+x)에 오게 넣습니다.
1) 바깥: xr{CR['xr'][0]}~{CR['xr'][1]} ({xrng(CR['xr'])}, 폭 {CR['size'][0]}), u{CR['u'][0]}~{CR['u'][1]} ({CR['size'][1]}), w{CR['w'][0]}~{CR['w'][1]} ({CR['size'][2]}). 옆벽 앞끝은 유리보다 1.0 앞(w−1).
   - 【3a】 벽 안쪽 면을 정해 둡니다. 아래 벽 u{WL['bottom_u'][0]}~{WL['bottom_u'][1]:g}(두께 2.5, 안쪽 면 u0에 유리 아래 끝이 얹힘, 틈 0). 위 벽 u{WL['top_u'][0]}~{WL['top_u'][1]}(위 틈 {WL['top_gap']:g}). 옆벽 xr±{WL['side_inner_xr']}~±{CR['xr'][1]}(틈 {WL['side_gap']:g}). 벽은 모두 w−1~16입니다.
   - 【3a】【새로】 아래 벽 홈: xr{NT['xr'][0]:g}~{NT['xr'][1]:g} (x{X(NT['xr'][0]):g}~{X(NT['xr'][1]):g}), u{NT['u'][0]}~{NT['u'][1]:g} 관통, w{NT['w'][0]:g}~{NT['w'][1]:g}.
     - 이유: 화면 아래 끝에 작은 돌기가 있습니다. 도면 앞모습에서 xr{NT['feature_xr'][0]}~{NT['feature_xr'][1]}, 약 {NT['feature_proud']} 튀어나오고, 사진에서는 아래 면의 홈과 탭입니다.
     - 돌기 양옆 여유는 {CK['notch_margin'][0]}/{CK['notch_margin'][1]} mm입니다. 유리는 홈 양옆의 아래 벽에 얹힙니다.
     - 앞모습 기준이라 커넥터 쪽과 상관없습니다. G-1에서 뒤집어도 홈은 그대로입니다.
     - 오른쪽 귀(xr{hR['ear'][0]}~{hR['ear'][1]})와 x가 xr{max(NT['xr'][0], hR['ear'][0]):g}~{min(NT['xr'][1], hR['ear'][1]):g}에서 겹치지만, 홈은 w{NT['w'][1]:g} 앞쪽만 뚫습니다. 귀가 붙는 아래 벽 w{EAR['attach']['w'][0]:g}~{EAR['attach']['w'][1]:g}는 남습니다.
2) 뒷판: w{CR['plate'][0]}~{CR['plate'][1]} (두께 {CR['plate'][1]-CR['plate'][0]:g}). 화면 뒷면은 w{CR['w_screen_back']:g}. 가운데 볼록판(높이 약 {S['emboss']['h']}, xr{S['emboss']['xr'][0]}~{S['emboss']['xr'][1]}, u{S['emboss']['u'][0]}~{S['emboss']['u'][1]})과 {CR['emboss_clearance']} mm 뜹니다. 판과 화면 사이 {CR['plate'][0]-CR['w_screen_back']:g} mm 틈으로 리본·전원선이 지나갑니다.
3) 【변경】 화면 고정 보스 4개: xr ±{BO['xr'][1]:g} ({X(BO['xr'][0]):g}, {X(BO['xr'][1]):g}) / u {BO['u'][0]}, {BO['u'][1]}. Ø{BO['d']:g} 기둥 w{BO['w'][0]:g}~{BO['w'][1]:g}, 화면 뒷면(w{BO['face_w']:g})에 닿음. 구멍 Ø{BO['hole_d']}, 뒤(w{CR['w'][1]:g})에서 Ø{BO['cbore_d']} 자리파기, 나사 머리 자리 w{BO['seat_w']:g} → M2.5×6 물림 {BO['engage']:g} mm.
   - 【3a】 보스는 옆벽 안쪽 면(xr±{WL['side_inner_xr']})까지 폭 {BO['fill_to_side_wall']['width_u']:g}(u)로 이어 채웁니다(w{BO['w'][0]:g}~{BO['w'][1]:g}).
   - 구멍 깊이 규칙(깊이 모름): 물림 e = min(구멍 깊이 − 0.5, 4.0), 최소 2.0. 머리 자리 w = 8.0 + (6 − e). 받은 화면에서 깊이가 3.5보다 얕으면 그만큼 와셔를 넣거나 머리 자리를 올립니다.
4) 【변경】 커넥터(화면 뒤, 추정 ±0.5 — G 참조):
   - DSI: 22핀 0.5 mm ZIF(가로형), xr{S['fpc']['xr'][0]}~{S['fpc']['xr'][1]} ({xrng(S['fpc']['xr'])}), u{S['fpc']['u'][0]}~{S['fpc']['u'][1]}(핀 가운데 u{S['fpc']['pin_u_centre']}), 입구는 +x(xr{S['fpc']['mouth_xr']}).
   - 전원: MX1.25 2핀(가로형), xr{S['pwr']['xr'][0]}~{S['pwr']['xr'][1]}, u{S['pwr']['u'][0]}~{S['pwr']['u'][1]}, 입구 +x. 5V·GND.
   - 화면 뒤 창: xr{S['window']['xr'][0]}~{S['window']['xr'][1]}, u{S['window']['u'][0]}~{S['window']['u'][1]}.
5) 【변경】 점검창(뒷판을 뚫음): xr{INS['xr'][0]:g}~{INS['xr'][1]:g} ({xrng(INS['xr'], 1)}), u{INS['u'][0]:g}~{INS['u'][1]:g}. ZIF 잠금, MX1.25, 리본 접힘 자리가 모두 보입니다. 창 둘레 리브는 창보다 {INS['cover']['flange']+0.3:.1f} mm 밖에 둡니다(덮개 턱 자리).
6) 【새로】 리본 길(받침 안): 커넥터 입구에서 +x로 {RB['in_cradle_parts']['screen_exit_to_fold']:g} mm → 45° 접기 자리 xr{FS['xr'][0]}~{FS['xr'][1]}, u{FS['u'][0]}~{FS['u'][1]}(R3으로 말아 접기, 날카롭게 꺾지 않음) → −u로 xr{CR['rib_band_xr'][0]}~{CR['rib_band_xr'][1]}를 따라 내려감 → 아래 홈. 전원선은 xr{CR['wire_xr'][0]}~{CR['wire_xr'][1]}로 리본 옆을 내려감.
7) 【새로】 리본 누름 패드(뒷판 안쪽): xr{HP['xr'][0]}~{HP['xr'][1]}, u{HP['u'][0]:g}~{HP['u'][1]:g}, w{HP['w'][0]}~{HP['w'][1]} (리본 두께 + 0.3 틈). 캡톤테이프를 함께 씁니다.
8) 【변경】 아래 트인 홈(리본 + 전원선): xr{GR['xr'][0]}~{GR['xr'][1]} ({xrng(GR['xr'])}), u{GR['u'][0]}~{GR['u'][1]:g}, w{GR['w'][0]:g}~{GR['w'][1]:g}. 아래와 뒤가 트여 선을 뒤에서 넣고 뺍니다.
9) 뒤 리브(w{CR['rib'][0]:g}~{CR['rib'][1]:g}, 두께 {CR['rib_t']:g}): 바깥 둘레 벽을 w{CR['rib'][1]:g}까지, 가로 리브 2개, 다리 길 벽 2개, 점검창 둘레, 패드 4개, 보스 4개. 가로 리브는 다리 길(xr±7.3)에서 끊습니다.
   - 【3a】 가로 리브는 u{CR['cross_ribs_u'][0]:g}(u{CR['cross_ribs_u'][0] - 1:g}~{CR['cross_ribs_u'][0] + 1:g})와 u{CR['cross_ribs_u'][1]:g}입니다.
     - 3판 처음의 u{R3['cradle']['cross_ribs_u'][0]:g}는 다리 축 줄 위였습니다. 그래서 축 나사 머리가 {-AX['rev3_u30_rib']['head_gap']:g} mm 파고들고 넣는 길이 막혔습니다. 이제 다리 축 줄(u{LG['pivot_cradle_uw'][0]:g}) 둘레에는 리브가 없습니다.
     - 규칙: 리브 가운데 u = 다리 축 u − 걸이 볼 R{LG['clevis']['R']} − 여유 1.2 − 리브 반 두께 1 (내림).
   - 확인: 축 나사 머리(Ø5.7 × 1.65, xr{AX['head_box'][0][0]}~{AX['head_box'][0][1]})와 −x에서 넣는 나사 전체(xr{AX['path_box'][0][0]}~{AX['path_box'][0][1]}, u{AX['path_box'][1][0]}~{AX['path_box'][1][1]}, w{AX['path_box'][2][0]}~{AX['path_box'][2][1]})가 모든 뒤 리브·패드·보스와 {AX['min_path_gap']} mm 이상 떨어집니다(가장 가까운 것: {AX['nearest']}).
10) 【새로】 받침 아래 뒤 모서리(u{CR['u'][0]}, w{CR['w'][1]:g}) C{CR['rib_relief_at_cheeks']['chamfer']:g} 모따기: 22~90° 도는 동안 경첩 볼과 {CR['rib_relief_at_cheeks']['gap_after']} mm 이상 떨어집니다(모따기 없으면 {-min(CR['rib_relief_at_cheeks']['gaps_without'].values()):g} mm 파고듦).
11) 【변경】 뒤 패드 4개 16×16, w{CR['rib'][0]:g}~{CR['rib'][1]:g}: {pads_txt}. 접으면 뚜껑 받침 발 위에 얹힙니다.
12) 【변경】 경첩 귀 2개: 두께 8.0, 귀 x{EX['left'][0]}~{EX['left'][1]}와 x{EX['right'][0]}~{EX['right'][1]}(뚜껑의 귀 홈 x{ES['left'][0]}~{ES['left'][1]}·{ES['right'][0]}~{ES['right'][1]} 안, 양쪽 틈 0.2). 축 (u{HG['axis_cradle_uw'][0]:g}, w{HG['axis_cradle_uw'][1]:g}), 구멍 Ø3.3.
    - 【3a】 귀 옆모양(u, w)은 아래 네 가지만 감싼 볼록 모양이고, 다른 돌기는 두지 않습니다. {ear_edges}
    - 이렇게 하면 22°에서 뒤꿈치 {uw(EAR['heel_uw'])}가 귀의 가장 낮은 점이 됩니다. 이 점이 world (y{HG['heel_contact_yz'][0]}, z{HG['heel_contact_yz'][1]})에서 멈춤 블록에 닿습니다(축에서 R{HG['heel_R']}).
    - 귀 전체 윤곽과 블록·홈 바닥 사이 틈은 22°에서 {EAR['check']['gap_at_22']}(닿음), 25~90°에서 {EAR['check']['min_gap_25_90']} 이상입니다(25°에서 가장 작음). 윤곽 점은 numbers.json `cradle.ear.profile_uw`에 있습니다.
    - 뒤꿈치 모서리는 R0.3 이하로만 둥글게 합니다. 더 둥글면 멈추는 각이 22°보다 조금 커집니다.
13) 【변경】 받침다리 걸이: 축 (u{LG['pivot_cradle_uw'][0]:g}, w{LG['pivot_cradle_uw'][1]}), x 방향. 가까운 볼 xr{LG['clevis']['near'][0]}~{LG['clevis']['near'][1]} (Ø3.3 관통), 먼 볼 xr{LG['clevis']['far'][0]}~{LG['clevis']['far'][1]} (Ø2.5 × 6 막힘, 물림 5.4). 다리 자리 xr−5~5 (틈 0.3). 볼 둘레 R{LG['clevis']['R']}, 아래쪽 45° 모따기.
    - 【3a】 축 나사는 {LG['axle']['screw']}(머리 Ø{LG['axle']['head_d']} × {LG['axle']['head_h']})입니다. −x에서 넣고 {LG['axle']['tool']}로 조입니다. 머리는 가까운 볼 바깥 면 xr{LG['clevis']['near'][0]}에 평평하게 닿고, C-9 확인값대로 둘레가 비어 있습니다.
14) 【변경】 다리 길: 벽 xr{LG['channel']['xr_walls'][0][0]}~{LG['channel']['xr_walls'][0][1]}·{LG['channel']['xr_walls'][1][0]}~{LG['channel']['xr_walls'][1][1]}, u{LG['channel']['u'][0]}~{LG['channel']['u'][1]}. 접은 다리는 뒷판 위 w13.5~19.5에 눕습니다.
15) 【그대로·값 변경】 다리 클립 턱(v13 ⑤): 몸 xr−8.5~−5.3 / 5.3~8.5, u{LG['clip']['u'][0]:g}~{LG['clip']['u'][1]:g}, 걸림 {LG['clip']['catch']:g}(다리 위 {LG['clip']['over_leg']:g}), 걸림 턱 w{LG['clip']['catch_from_w']}~{LG['clip']['back_w']} (두께 {LG['clip']['hook_t']:g}). 접으면 턱 끝 z{LG['fold_clip_zmin']} (뚜껑과 {CK['fold_clip_clear_lid']}).
16) 확인값: 25° 가장 앞 (y{U['cr_bot_front'][0]}, z{U['cr_bot_front'][1]}), 가장 높은 곳 z{U['cr_top_front'][1]}, 가장 뒤 y{U['cr_top_rib'][0]}. 22° 가장 앞 y{HL['cr_bot_front'][0]}. 22~90° 전체 가장 앞 y{N['all_min_y']} (> y{KO['y_max']:g}). 90° 접음 y{FO['y'][0]}~{FO['y'][1]}, z{FO['rib_plane_z']}~{FO['top_z']}.
    - 평면 자리: 25°에서 y{FP['front_25']}~{FP['rear_25']}, 22°에서 앞끝 y{FP['front_22']}입니다. 도면에 '25° y216.00'으로 쓰면 틀립니다.
17) 【3a】 출력: 윗변(u{CR['u'][1]} 면)을 베드에 세워 출력합니다. 높이는 {CR['print_height']}(= u{CR['u'][1]} − 뒤꿈치 u{EAR['min_u']})이고 귀가 위로 옵니다.
    - 다리 걸이·클립·패드는 45° 모따기로 서포트 없이 뽑습니다. 보스 구멍은 물방울 모양입니다. 아래 벽 홈은 맨 위라 서포트가 필요 없습니다.
    - 약 {N['mass_est']['cradle_g']:.0f} g, 약 {N['mass_est']['cradle_h']:.1f}시간(추정).

18) 【새로】 선 나가는 방향과 굽힘 반경 (CAD 요청):
    - DSI 리본(22핀 0.5 mm, 폭 약 {RB['ffc_w']}, 두께 약 {RB['ffc_t']}): 화면 ZIF 입구 +x → 45° 말아 접기 R{RB['fold_roll_R']:g} → −u로 내려감 → 아래 홈에서 아래로 나감 → 경첩 고리 약 {RB['loop']['length']} mm (줄 길이 {RB['loop']['chord']['heel']}(22°)·{RB['loop']['chord']['use']}(25°)·{RB['loop']['chord']['fold']}(접음), 둥근 고리 R{RB['loop']['single_arc_R']['fold']}~{RB['loop']['single_arc_R']['heel']}) → 뚜껑 구멍으로 −z.
    - 【3a】 뚜껑 밑: 리본을 뚜껑 밑면에 붙입니다(가운데 z{RB['z_run']}, 클립에 물리는 높이 z{CL['clamp_z'][0]}~{CL['clamp_z'][1]}). 길은 +y {RB['parts']['run_y']} → 45° 접기 → −x {RB['parts']['run_x']} → 리본 기둥 x{RB['waypoints'][3][0]:g}에서 아래로 {RB['parts']['drop']}입니다. 기둥은 CAD 지킴 구역 x{PL['keepout_zones']['dsi']['x'][0]}~{PL['keepout_zones']['dsi']['x'][1]} 안입니다.
    - 【3a】 Pi 쪽 끝: R{RB['bend_R']:g}로 +x로 굽혀 안 쓰는 micro-HDMI 위(z{RI['z_land']})에 {RB['parts']['over_obstacle']:g} mm 얹힙니다. 그다음 {RI['approach_deg']}°로 {RI['last_straight']:g} mm 가서 CAM/DISP 1 입구(x{PL['pi5_mipi']['disp1_mouth_xyz'][0]:g}, 입구 −x)에 {RB['pi_end_insert']:g} 꽂습니다.
    - 기둥 x{RB['waypoints'][3][0]:g}은 규칙 값입니다({RI['column_x_rule']}). 기둥을 입구 쪽으로 옮기면 보강판이 곧게 나올 길이가 없어 실제 리본으로 만들 수 없습니다.
    - 아래로 내려가서 +x로 도는 것은 90° 굽힘 두 번이고 U자가 아닙니다. 길이를 더하지 않습니다.
    - 【3a】 전원선(MX1.25 2핀 → 2.54 3핀 → 점퍼): 입구 +x → 리본 옆 xr{CR['wire_xr'][0]}~{CR['wire_xr'][1]}로 내려감 → 같은 홈·고리·구멍(x{PW['waypoints'][0][0]}) → 뚜껑 밑 클립의 전원선 홈(z{PW['waypoints'][1][2]}) → +y → −x → GPIO 2·6 ({PI['gpio_pin2'][0]}, {PI['gpio_pin2'][1]})로 내려감. 3핀 이음은 22×6 구멍을 지나갑니다.
    - 선이 모듈 쪽으로 가장 나오는 곳은 약 y{CK['cables_fwd_min_y']}입니다(> y{KO['y_max']:g}).

## D. 받침다리 새 STL
PETG {LG['section'][0]:g}(x) × {LG['section'][1]:g}, 축 구멍 Ø3.3 중심에서 발끝 중심까지 {LG['length']:g}, 양 끝 R3(전체 {LG['length']+6:g}). 넓은 면을 베드에 눕혀 출력.
사용 상태: 축 world (y{LG['pivot_yz'][0]}, z{LG['pivot_yz'][1]}), 발끝 (y{LG['tip_yz'][0]}, z{LG['tip_yz'][1]}), 수평에서 {LG['angle_deg']}°. 접은 상태: 받침 뒤 w13.5~19.5, u{LG['pivot_cradle_uw'][0]-3:g}~{LG['stow_tip_u']:g}.
다리 길이·축 자리 결정: 접은 다리가 받침 윗끝 안(u{LG['stow_tip_u']:g} ≤ {CR['u'][1]-1:g}), 발이 뚜껑 뒤끝에서 {CK['pocket_back_material']} mm 안, 각도 25~40°에서 팔 길이가 가장 큰 쪽({ST['leg_arm_mm']} mm).
【3a】 넣고 빼는 순서: **화면을 22°(뒤꿈치)까지 앞으로 기울여 댄 채** 다리를 내리거나 올립니다.
- 22°에서는 다리 축이 y{sw22['pivot'][0]} z{sw22['pivot'][1]}로 {LG['pivot_shift_at_22']} mm 옮겨 갑니다. 그래서 뒷벽 위 모서리까지 {sw22['back_edge_dist']}로 발 끝 반경 {sw22['foot_reach']}보다 멉니다.
- 다리가 수평 아래 {-sw22['first_contact_deg']:g}°까지 내려오면 발이 경사(y{sw22['first_contact_yz'][0]}, z{sw22['first_contact_yz'][1]})에 먼저 닿습니다. 손을 놓으면 화면이 25°로 돌아가며 발이 경사를 타고 뒷벽까지 미끄러집니다.
- 25°에서 그대로 내리면 뒷벽 위 모서리까지 {sw25['back_edge_dist']}로 {sw25['foot_reach']}보다 가깝습니다. 다리가 수평 아래 {-sw25['first_contact_deg']:g}°에서 발이 모서리에 먼저 닿고, 최대 {-sw25['worst_overlap']:g} mm 긁습니다(수평 아래 {-sw25['worst_at_deg']:g}°).

## E. 작은 부품
1) 【변경】 점검창 덮개: 끼움부는 창보다 {INS['cover']['plug_under']:g} mm 작고(두께 = 뒷판 2.5), 턱은 사방 {INS['cover']['flange']:g} mm 크고 두께 {INS['cover']['t']:g}. 【새로】 안쪽 볼록 자리 xr{INS['cover']['dome']['xr'][0]}~{INS['cover']['dome']['xr'][1]}, u{INS['cover']['dome']['u'][0]}~{INS['cover']['dome']['u'][1]}를 w{INS['cover']['dome']['inner_to_w']}까지 비움(R3 말아 접은 리본 자리), 바깥 살 1.2. 걸쇠 2개.
2) 【3a】 리본 클립 {CL['pad']['x'][1]-CL['pad']['x'][0]:g}×{CL['pad']['y'][1]-CL['pad']['y'][0]:g}×{CL['t']:g} (뚜껑 밑, z{CL['clip_z'][0]}~{CL['clip_z'][1]}):
   - 윗면에 핀 Ø{CL['pin_d']:g} 두 개, 길이 {CL['pin_len']:g}(구멍 {CL['pin_hole_depth']:g}보다 0.5 짧게).
   - 윗면에 전원선 홈 x{CL['wire_groove']['x'][0]}~{CL['wire_groove']['x'][1]}(폭 {CL['wire_groove']['x'][1]-CL['wire_groove']['x'][0]:.1f}), 깊이 {CL['wire_groove']['depth']:g}, y 방향으로 끝까지.
   - 평평한 나머지 면은 리본(x{rib_x0:.2f}~{CL['ribbon_edge_x']})만 누릅니다. 홈은 리본 끝에서 {CL['wire_groove']['x'][0]-CL['ribbon_edge_x']:.1f}, 핀 가장자리에서 {CL['pin_edge_x']-CL['wire_groove']['x'][1]:.2f} 떨어집니다.
3) 선택: 화면 덮개 {CR['size'][0]+2:.0f}×{CR['size'][1]+2:.0f}×3 (접은 화면 위, 받침 테두리에 얹힘).

## F. 조립 파일 / 3D
- 화면 상자 {S['glass'][0]}×{S['glass'][1]}×{S['body']} (+ 뒤 볼록판 {S['emboss']['h']}), 커넥터 두 개 표시. 받침·화면은 25° 사용 상태(M = poses.cradle_use), 받침다리는 사용 상태. 접은 상태(poses.cradle_fold)는 별도 보기.
- 변환: world = M·[xr, u, w, 1]. M(25°) = {[[round(v, 6) for v in row] for row in N['poses']['cradle_use']]}. (u, w 좌표계는 왼손계라 det = −1. 오른손계가 필요하면 v = −w를 쓰고 3번째 열 부호를 바꿈.)
- Pi 5(L2 확정): 판 x{PI['board_x'][0]}~{PI['board_x'][1]}, y{PI['board_y'][0]}~{PI['board_y'][1]}, 윗면 z{PI['board_top_z']}, 회전 {PI['rot_deg']}°. CAM/DISP 1 x{PI['disp1']['x'][0]}~{PI['disp1']['x'][1]}, y{PI['disp1']['y'][0]}~{PI['disp1']['y'][1]}. micro-HDMI(추정) x{PI['hdmi']['x'][0]}~{PI['hdmi']['x'][1]}, y{PI['hdmi']['y'][0]}~{PI['hdmi']['y'][1]}, 윗면 z{PI['hdmi']['top_z']}; 방열판(추정) x{PI['heatsink']['x'][0]}~{PI['heatsink']['x'][1]}, y{PI['heatsink']['y'][0]}~{PI['heatsink']['y'][1]}.
- 【3a】 3D 모델은 이 사양과 같게 만듭니다.
  - 아래 벽 안쪽 u0(유리가 얹힘), 위 벽 안쪽 u{WL['top_u'][0]}. 보스는 옆벽까지 채웁니다.
  - 귀는 `cradle.ear.profile_uw`, 가로 리브는 u{CR['cross_ribs_u'][0]:g}·u{CR['cross_ribs_u'][1]:g}, 아래 벽 홈을 넣습니다.
  - 리본은 `ribbon.waypoints`(뚜껑 밑 z{RB['z_run']}, Pi에 {RB['pi_end_insert']:g} 꽂음), 전원선은 `power_wire.waypoints`입니다.
  - 클립 핀은 {CL['pin_len']:g}, 뚜껑 나사 자리는 A-7입니다. 미리보기 STL은 출력용이 아닙니다.

## G. 받은 부품으로 확인할 것 (출력 전에)
1) 커넥터가 어느 쪽인지: 사진 3장(Pi 구멍 좌우 반전, 케이블 위치, 전원이 FPC 위)으로 "화면 앞에서 볼 때 커넥터 창이 오른쪽, 입구 +x"로 판단했습니다.
   - 반대면 창·홈·구멍·클립을 x{XC:g} 기준으로 뒤집습니다. 구멍은 x{VAR['connector_mirrored']['hole_x'][0]}~{VAR['connector_mirrored']['hole_x'][1]}이 되어 CAD 권장 x{PL['cad_recommendations']['ribbon_hole']['x'][0]}~{PL['cad_recommendations']['ribbon_hole']['x'][1]}와 거의 같습니다.
   - 그때 리본은 약 {VAR['connector_mirrored']['ribbon']['total']:.0f} mm이고 {VAR['connector_mirrored']['ribbon']['ffc_type'][0]}형(같은 면, 예비로 산 것)입니다. 경첩·다리·패드와 아래 벽 홈(앞모습 기준)은 그대로입니다.
2) 모서리 구멍: 나사산 깊이를 잽니다(C-3 규칙). 동봉 스탠드오프는 달지 않습니다.
   - 【3a】 모서리가 박힌 스터드(도면 옆모습 13.4, 약 {VAR['corner_studs']['stud_h']} 튀어나옴)라서 뗄 수 없으면 보스를 팝니다.
     - Ø{SB['bore_d']:g}(둥근 스터드 5.8 이하 또는 육각 5)로 w{SB['bore_w'][0]:g}~{SB['bore_w'][1]}까지 파고, 보스는 Ø{SB['boss_d']:g}로 키웁니다.
     - 남은 바닥 {SB['floor_t']:g}를 지나 뒤에서 M2.5×6을 스터드 암나사에 조입니다(물림 {SB['engage']:g}). 머리는 w{CR['w'][1]:g} 면 위로 {SB['head_out']:g} 나옵니다.
     - 뒷판과 축은 그대로입니다. 접었을 때 머리는 뚜껑과 {SB['fold_head_to_lid']:g}, 받침 발과 평면에서 {SB['fold_head_to_feet_plan']:g} 떨어집니다.
   - (하지 말 것) 뒷판을 스터드 뒤로 물리면 {VAR['corner_studs']['plate_moves_back']} mm 뒤로 갑니다. 그러면 축 y{VAR['corner_studs']['result']['axis_y']}, 접은 끝 y{VAR['corner_studs']['result']['fold_rear_y']}(뚜껑 뒤끝과 {VAR['corner_studs']['result']['rear_margin']} mm)이라 맞지 않습니다.
3) 뒤 볼록판 높이(약 {S['emboss']['h']} 추정): 2.1보다 높으면 뒷판 안쪽 면 = 8.0 + 높이 + 0.4로 다시 계산.
4) Waveshare MX1.25→3핀 선 길이(약 100~150 추정): {PW['ws_cable_joint_needs']} mm 이상이면 3핀 이음이 뚜껑 밑에 옵니다. 짧으면 경첩 고리 안에 오므로 열수축튜브로 감쌉니다(22×6 구멍 통과 가능).
5) 리본: 받침과 뚜껑을 출력하기 전에 폭 12 mm 종이띠로 길을 잽니다. L2 Pi 자리까지 약 {RB['total']:.0f} mm / 300 mm (여유 {RB['margin']:.0f}). Pi 자리가 바뀌면 numbers.json `ribbon_table`과 공식으로 다시 봅니다.
6) 뒤꿈치 틈 {HG['heel_gap_at_25']} mm는 출력 공차와 비슷합니다. 다리 발이 주머니에 잘 안 들어가면 뒤꿈치를 0.3 mm 깎습니다.
7) 【3a】 화면 아래 끝 돌기: 받으면 위치(xr{NT['feature_xr'][0]}~{NT['feature_xr'][1]} 추정)와 튀어나온 높이(약 {NT['feature_proud']}, 1 이하로 봄)를 잽니다. 홈 xr{NT['xr'][0]:g}~{NT['xr'][1]:g} 밖이면 홈을 옮깁니다. 스위치나 슬롯이면 손이 닿는지도 봅니다.
8) 【3a】 실제 Pi 5에서 확인할 것:
   - micro-HDMI 윗면 높이(추정 z{PI['hdmi']['top_z']})와, 리본이 그 위에 얹혀 입구로 들어가는지.
   - CAM/DISP 1 깊이(CAD 상자 {PI['disp1']['depth']:g}, 꽂는 길이 {RB['pi_end_insert']:g}).
   - 추정 방열판은 CAD 리본 지킴 구역(x{PL['keepout_zones']['dsi']['x'][0]}부터)을 {-RB['pi_clearance']['heatsink_vs_cad_keepout_x']:g} mm 넘게 그려져 있습니다. 실제 방열판은 지킴 구역 밖이어야 합니다(리본 끝과 추정 방열판 모서리: y {RB['pi_clearance']['heatsink_y_gap']}, x {RB['pi_clearance']['heatsink_x_gap']}).
9) 【3a】 뚜껑 레일 인서트 길이(추정 {LS['insert_engage']:g}): 다르면 A-7 식으로 자리파기 깊이를 다시 잡습니다.

## H. 도면·3D 세션에 알릴 것 (이 사양이 기준)
- 귀(t01 확대 A, t03 단면 C–C): 뒤꿈치 옆 점 {uw(L3['lobe_uw'])}을 빼고 `cradle.ear.profile_uw`로 그립니다. 출력 높이는 {CR['print_height']}입니다.
- t03 뒤 모습·F–F: 가로 리브는 u{CR['cross_ribs_u'][0]:g}이고, 축 나사 머리 둘레가 비어 있어야 합니다. 뒤에서 본 모습(좌우 반전)은 왼쪽이 +x이므로 '+x' 글자가 왼쪽에 와야 합니다(지금은 바뀌어 있음).
- t03 앞 모습·아래 단면: 아래 벽 홈 xr{NT['xr'][0]:g}~{NT['xr'][1]:g}.
- t05·t06: 클립 전원선 홈, 핀 {CL['pin_len']:g}, 리본은 HDMI 위에 얹혀 입구로(U자 아님), O4 정비 순서(B).
- t02 J: 평면 자리는 '22~25° y{FP['front_22']}~{FP['rear_25']}' 또는 '25° y{FP['front_25']}~{FP['rear_25']}'로 씁니다.
- t01: z{E['sightline_z_at_module']}는 '보이는 영역 아래 끝을 보는 선'입니다(가운데를 보는 선은 y{KO['module_rear_y']:g}에서 z{E['sightline_centre_z_at_module']}). 52.71 치수 글자가 가려져 있습니다.
- t04 7번과 이 사양 A-7·B: 뚜껑 고정은 【변경】(L2 CAD 설계)입니다. 자리파기 Ø{LS['cbore_d']:g} × {LS['cbore_depth']:g}, 인서트 물림 {LS['insert_engage']:g}. 3D 모델의 7.5/4.0은 이 값으로 바꿉니다.
- 리본 기둥은 x{RB['waypoints'][3][0]:g} 그대로입니다(입구 쪽으로 옮기자는 제안은 보강판 규칙을 깸). 추정 HDMI·방열판과 닿는 것은 실제 Pi 5로 확인합니다(G-8).
- 도면 보기 틀과 제목의 x{XC:g}·뚜껑 범위는 numbers.json에서 계산해 넣어야 자리 블록이 바뀌어도 맞습니다.
"""

# ============================ other texts ============================
placement_txt = (
 f"자리: L2 뒷바 가운데 뚜껑(x{LID['x'][0]:g}~{LID['x'][1]:g}, y{LID['y'][0]:g}~{LID['y'][1]:g}, 윗면 z{LID['top_z']}) 위, 화면 가운데 x{XC:g}.\n"
 f"경첩 축: y{HG['axis_yz'][0]} z{HG['axis_yz'][1]}. 모듈을 위로 빼야 하므로 y≤{KO['y_max']:g}, z≥{KO['z_min']}에는 아무것도 둘 수 없습니다. 22°에서 받침 앞 아래 모서리가 축보다 {HG['front_reach']} mm 앞으로 나오므로 축을 y{KO['y_max']:g} + {KO['clearance']:g} + {HG['front_reach']}에 둡니다.\n"
 f"화면(유리 {S['glass'][0]}×{S['glass'][1]}): 유리 x{S['glass_x'][0]}~{S['glass_x'][1]}. 25°에서 유리 아래 끝 y{U['glass_bottom'][0]} z{U['glass_bottom'][1]}, 위 끝 y{U['glass_top'][0]} z{U['glass_top'][1]}. 보이는 영역 x{S['active_x'][0]}~{S['active_x'][1]}, z{U['act_bottom'][1]}~{U['act_top'][1]}.\n"
 f"받침: x{CR['x'][0]}~{CR['x'][1]}(폭 {CR['size'][0]}), 뚜껑 안에서 양쪽 {CK['lid_x_margin'][0]} mm 남음. 가장 높은 곳 z{U['cr_top_front'][1]}. 평면 자리 25° y{FP['front_25']}~{FP['rear_25']}(22°에서는 앞끝 y{FP['front_22']}).\n"
 f"모듈 위 금지: 22~90° 도는 동안 가장 앞 y{N['all_min_y']}, 선의 가장 앞 약 y{CK['cables_fwd_min_y']}.\n"
 f"연주자 시선(눈 y−350 z450 추정): 화면 가운데까지 아래로 {E['angle_to_centre']}°, 기울기 25°와 {E['tilt_diff']}° 차이라 거의 정면. 눈 범위를 넓혀도 {E['angle_range'][0]}~{E['angle_range'][1]}°. 거리 {E['dist_to_centre']:.0f} mm, 1 px = {E['arcmin_per_px']}분각, 32 px 글자 = {E['arcmin_32px']:.0f}분각. "
 f"보이는 영역 아래 끝을 보는 선은 모듈 뒤끝(y{KO['module_rear_y']:g})에서 z{E['sightline_z_at_module']}, 가운데를 보는 선은 z{E['sightline_centre_z_at_module']}라 가리지 않습니다.\n"
 f"손 닿는 거리: 화면 가운데가 흰건반 앞끝에서 {RE['centre_from_key_front_y']} mm 뒤, 높이 z{RE['centre_z']} (모듈 윗면보다 {RE['centre_above_module_top']} mm 위). 2판(y{r2u['glass_centre'][0]} z{r2u['glass_centre'][1]})보다 가깝고 낮습니다.\n"
 f"소리 길: 두 스피커 유닛 가운데(body_L2, x{PL['speakers_plan'][0][0]:g}/{PL['speakers_plan'][1][0]:g})에서 두 귀로 가는 선 4개가 화면에서 {CK['sound_paths_min']} mm 이상 떨어져 있습니다. L2의 27° 규칙(콘 아래 끝에서 27° 위로 가는 선이 모듈 뒤 모서리보다 3 이상 위)은 {SR['clear_above_module_edge']} mm이고, 화면은 콘과 x로 {SR['screen_to_cone_x_gap']:.0f} mm 떨어져 그 길에 들어가지 않습니다.\n"
 f"O4와 정렬: 화면 가운데 x{XC:g}는 O4 가운데(x{CTX_O4:g})보다 {abs(N['O4']['offset'])} mm 왼쪽. 게임 2옥타브 보기 흰 레인 {N['O4']['two_oct_white_px']} px({N['O4']['two_oct_white_mm']} mm).\n"
 f"홀센서: 센서 줄(y≈67)에서 화면 가장 앞까지 {N['sensor_gap']} mm, 화면부에 자석 없음(D14).")

mount_txt = (
 f"구성: ① 가운데 뚜껑의 경첩 받침·다리 주머니·받침 발(L2 뚜껑에 더함) ② 화면 받침(PETG) ③ 받침다리(PETG) ④ 점검창 덮개 ⑤ 리본 클립 ⑥ 나사.\n"
 f"화면 고정: 화면 뒤 모서리 M2.5 구멍 4개(154×88)에 받침 뒤에서 M2.5×6을 조입니다. 보스(Ø{BO['d']:g}, 옆벽까지 채움)가 화면 뒷면 w8.0에 닿고 물림은 {BO['engage']:g} mm입니다. 유리 아래 끝은 아래 벽(u0)에 얹히고, 아래 끝 작은 돌기 자리는 홈(xr{NT['xr'][0]:g}~{NT['xr'][1]:g})으로 비웁니다.\n"
 f"경첩: 축 y{HG['axis_yz'][0]} z{HG['axis_yz'][1]}, M3×20 두 개(바깥에서 넣음). 뒤꿈치는 귀 홈의 {HG['heel_stop_h']:g} mm 블록에 22°에서 닿습니다(25°에서 {HG['heel_gap_at_25']} mm 뜸). 귀는 축 원·받침 아래·뒤꿈치 한 점만 감싼 모양입니다.\n"
 f"받침다리: 받침 뒤 u{LG['pivot_cradle_uw'][0]:g}에 M3×20 축(−x에서, 둘레에 리브 없음), 길이 {LG['length']:g}, 사용 때 발끝 y{LG['tip_yz'][0]} z{LG['tip_yz'][1]}, 수평에서 {LG['angle_deg']}°.\n"
 f"터치 안정성: 화면 위쪽 10 N → 다리 압축 {ST['leg_force']} N (좌굴 {ST['leg_Pcr']} N, {ST['leg_SF']}배). 경첩에는 앞뒤 {abs(ST['hinge_on_cradle'][0]):.0f} N, 위아래 {abs(ST['hinge_on_cradle'][1]):.0f} N. 화면 무게만으로 다리에 {ST['leg_static']} N. "
 f"앞으로 10 N 당기면 뒤꿈치 {ST['heel_force']} N, 뚜껑 앞 나사 합계 약 {ST['lid_screws_total']} N. 뒷바만 따로 놓였을 때(운반 중, 3.3 kg 추정) 넘어짐 여유 {ST['rear_bar_alone']['SF']}배, 건반 틀에 붙어 있으면 훨씬 큽니다.\n"
 f"세우기: 화면을 들어 앞으로 기울여 뒤꿈치(22°)에 댄 채 다리를 클립에서 빼 내립니다(발이 경사에 먼저 닿음). 손을 놓으면 화면이 25°로 가며 발이 경사를 타고 뒷벽까지 들어갑니다. 25°에서 다리를 내리면 발이 뒷벽 모서리를 긁습니다.\n"
 f"접기: 화면을 22°로 당긴 채 발을 빼 올림 → 다리를 받침 뒤 클립(u{LG['clip']['u'][0]:g}~{LG['clip']['u'][1]:g})에 끼움 → 화면을 뒤로 눕힘. 패드 4개가 받침 발 위 z{FO['rib_plane_z']}에 얹힙니다.")

cable_txt = (
 f"DSI 리본: 22핀 0.5 mm 300 mm, {RB['ffc_type']}. L2 Pi 자리까지 필요 약 {RB['total']:.0f} mm, 여유 {RB['margin']:.0f} mm.\n"
 f"1. 화면 ZIF(입구 +x)에서 +x로 {RB['in_cradle_parts']['screen_exit_to_fold']:g} mm, R3으로 45° 말아 접어 아래(−u)로 → 받침 안 틈(w8~10.5)으로 {RB['in_cradle_parts']['descend_to_cradle_bottom']} mm 내려감.\n"
 f"2. 아래 홈에서 나와 경첩 고리 약 {RB['loop']['length']} mm(줄 길이 세움 {RB['loop']['chord']['use']}, 접음 {RB['loop']['chord']['fold']}, 둥근 고리로 보면 R{RB['loop']['single_arc_R']['fold']}~{RB['loop']['single_arc_R']['use']}) → 뚜껑 구멍으로 내려감.\n"
 f"3. 뚜껑 밑면에 붙여(z{RB['z_run']}) R3으로 +y로 굽혀 클립 밑(물림 z{CL['clamp_z'][0]}~{CL['clamp_z'][1]})을 지나 {RB['parts']['run_y']} mm → 45° 접기(R3) → −x로 {RB['parts']['run_x']} mm → 리본 기둥 x{RB['waypoints'][3][0]:g}에서 {RB['parts']['drop']} mm 내려감 → R3으로 +x로 굽혀 안 쓰는 micro-HDMI 위에 얹힘 → {RI['approach_deg']}°로 CAM/DISP 1 입구(x{PL['pi5_mipi']['disp1_mouth_xyz'][0]:g}, 입구 −x)에 {RB['pi_end_insert']:g} mm 꽂음. 남는 약 {RB['margin']:.0f} mm는 클립과 45° 접기 사이에 둥근 고리(R10 이상)로 둡니다(O4 정비 때 뚜껑을 들 여유).\n"
 f"FFC 종류: 화면 ZIF와 Pi ZIF의 접점 방향이 같다고 봅니다(Waveshare가 Pi 5 표준 연결에 반대면 리본을 쓰는 것과 맞음). 굽힘·접기마다 면 방향을 따라가 계산하면 {RB['ffc_type']}입니다(받침 안 접기 1 + 뚜껑 밑 접기 {RB['folds_total']-1}). 화면 커넥터가 왼쪽으로 확인되면 {N['variants']['connector_mirrored']['ribbon']['ffc_type']}입니다. Pi 자리가 바뀌면 ribbon_table의 ffc 칸을 봅니다.\n"
 f"굽힘 반경: 고정 부분 R3 이상, 접기는 R3 말아 접기(손톱으로 꺾지 않음), 경첩 고리는 R6 이상.\n"
 f"전원선: 화면 MX1.25 2핀 → Waveshare MX1.25→2.54 3핀 선(길이 약 {PW['available'][0]-400:.0f}~{PW['available'][1]-400:.0f} 추정) → 수-수 점퍼 20 cm → 암-암 점퍼 20 cm → Pi GPIO 2번(5 V, 빨강)·6번(GND, 검정). 필요 약 {PW['total']:.0f} mm, 있는 길이 약 {PW['available'][0]:.0f}~{PW['available'][1]:.0f} mm → 남는 선은 뚜껑 밑에 감음. 받침 안에서는 리본 옆(xr{CR['wire_xr'][0]}~{CR['wire_xr'][1]}), 뚜껑 밑에서는 클립 윗면의 전원선 홈(x{CL['wire_groove']['x'][0]}~{CL['wire_groove']['x'][1]})을 지나갑니다.")

power_txt = (
 f"화면 약 {PWR['S_W']} W(5 V에서 {PWR['screen_A_5V']} A, Waveshare 최소 입력 0.43 A). Pi GPIO 2번(5 V)·6번(GND)에서 받음(D16 그대로).\n"
 f"5.1 V 레일 {PWR['rail_A']} A, Pi USB-C 입력 약 {PWR['pi_in_A']} A. 평균 {PWR['avg_W'][0]}~{PWR['avg_W'][1]} W, 순간 {PWR['peak_W']} W → 60 W까지 {PWR['margin_60W']} W 남음. 45 W 전원이면 −2 dB로 {PWR['w45_minus2dB']} W. 보조배터리 {PWR['battery_h'][0]}~{PWR['battery_h'][1]}시간.")

software_txt = (
 "OS: Raspberry Pi OS Lite(64-bit, 쓰는 판 고정). config.txt에 `dtoverlay=vc4-kms-dsi-waveshare-panel-v2,7_0_inch_c` 한 줄(기본 CAM/DISP 1, 0번 포트면 `,dsi0`).\n"
 "화면은 원래 가로 1024×600이라 회전이 필요 없습니다. pygame KMSDRM 앱과 터치 좌표를 그대로 씁니다(2판의 90° 회전 규칙은 필요 없음).\n"
 "밝기: /sys/class/backlight/*/brightness (0~255). 연주만 할 때는 0으로 줄여 전력을 아낍니다.\n"
 "알려진 문제: 찬 부팅에서 가끔 화면이 안 켜짐(I2C write failed −5, raspberrypi/linux PR #7182 미반영) → G2 시험에서 확인, 재부팅으로 복구.")

transport_txt = (
 f"운반: 다리를 받침 뒤 클립에 끼우고 화면을 뒤로 접으면 z{FO['top_z']}까지(스피커 윗면 z{PL['speaker_top_z']:g}보다 {FO['speaker_margin']} mm 낮음). "
 f"접은 화면은 y{FO['y'][0]}~{FO['y'][1]}, 뚜껑 뒤끝 안 {FO['rear_margin']} mm. 유리가 위를 보므로 화면 덮개나 천을 얹습니다.")

checks = [
 dict(item='모듈 위 금지 (y≤215, z≥72.85)', value=f"22~90° 전체 가장 앞 y{N['all_min_y']} (여유 {CK['keepout_margin']}), 선 가장 앞 약 y{CK['cables_fwd_min_y']}", ok=CK['keepout_ok'] and CK['cables_ok']),
 dict(item='접은 화면이 뚜껑 뒤끝 안', value=f"y{FO['y'][1]} ≤ y{LID['y'][1]:g} (여유 {FO['rear_margin']})", ok=CK['fold_rear_ok']),
 dict(item='접은 높이 < 스피커 윗면', value=f"z{FO['top_z']} < z{PL['speaker_top_z']:g} (여유 {FO['speaker_margin']})", ok=CK['fold_height_ok']),
 dict(item='받침이 뚜껑 폭 안', value=f"받침 x{CR['x'][0]}~{CR['x'][1]}, 뚜껑 x{LID['x'][0]:g}~{LID['x'][1]:g} (양쪽 {CK['lid_x_margin'][0]})", ok=min(CK['lid_x_margin']) > 0),
 dict(item='경첩 볼과 받침 간섭', value=f"아래 뒤 모서리 C{CR['rib_relief_at_cheeks']['chamfer']:g} 모따기로 틈 {CR['rib_relief_at_cheeks']['gap_after']}", ok=CR['rib_relief_at_cheeks']['gap_after'] >= 0.5),
 dict(item='【3a】 귀 전체 윤곽 vs 멈춤 블록', value=f"22°에서 {CK['ear_block_gap_22']}(닿음), 25~90°에서 {CK['ear_block_gap_25_90']} 이상 (기준 ≥0 / ≥0.3)", ok=CK['ear_block_ok']),
 dict(item='【3a】 다리 축 나사 머리·넣는 길', value=f"머리 {CK['axle_head_gap']}, 넣는 길 {CK['axle_path_gap']} mm (리브 u{rib_lo:g}; 3판 처음 u{R3['cradle']['cross_ribs_u'][0]:g}에서는 {AX['rev3_u30_rib']['head_gap']})", ok=CK['axle_ok']),
 dict(item='【3a】 아래 벽 홈', value=f"돌기 양옆 {CK['notch_margin'][0]}/{CK['notch_margin'][1]} mm, 관통 2.5", ok=CK['notch_ok']),
 dict(item='다리 접어 넣기', value=f"다리 끝 u{LG['stow_tip_u']:g} ≤ u{CR['u'][1]-1:g}", ok=CK['leg_stow_ok']),
 dict(item='접은 다리가 뚜껑에 안 닿음', value=f"다리 z{LG['fold_leg_z'][0]}~{LG['fold_leg_z'][1]}, 걸이 가장 낮은 곳 z{LG['fold_clevis_zmin']} (틈 {CK['fold_leg_clear_lid']}), 클립 턱 끝 z{LG['fold_clip_zmin']} (틈 {CK['fold_clip_clear_lid']})", ok=min(CK['fold_leg_clear_lid'], CK['fold_clip_clear_lid']) > 0),
 dict(item='다리 주머니 경사', value=f"경사 앞 y{PK['ramp_front_y']}에서 다리와 최소 {PK['ramp_min_clear']} mm", ok=PK['ramp_min_clear'] >= 0.2),
 dict(item='【3a】 다리 넣기 (22°에서)', value=f"발이 {sw22['first_contact']}에 먼저 닿음, 뒷벽 모서리 {sw22['back_edge_dist']} > {sw22['foot_reach']} (25°에서는 {sw25['worst_overlap']} → 22°에서 넣음)", ok=CK['leg_swing_22_ok']),
 dict(item='멈춤 과구속 없음', value=f"사용 각도는 다리, 뒤꿈치는 22°에서 닿음(25°에서 {HG['heel_gap_at_25']} mm)", ok=True),
 dict(item='DSI 리본 길이', value=f"약 {RB['total']:.0f} / 300 mm (여유 {RB['margin']:.0f}), {RB['ffc_type']}", ok=CK['ribbon_ok']),
 dict(item='【3a】 클립 전원선 홈', value=f"x{CL['wire_groove']['x'][0]}~{CL['wire_groove']['x'][1]}: 리본 끝과 {CL['wire_groove']['x'][0]-CL['ribbon_edge_x']:.1f}, 핀과 {CL['pin_edge_x']-CL['wire_groove']['x'][1]:.2f}", ok=CK['clip_groove_ok']),
 dict(item='전원선 길이', value=f"필요 약 {PW['total']:.0f} / 있는 길이 약 {PW['available'][0]:.0f}~{PW['available'][1]:.0f}", ok=CK['power_wire_ok']),
 dict(item='【3a】 뚜껑 나사 자리', value=f"자리파기 {LS['cbore_depth']:g}, 머리 밑 {LS['under_head']:g}, 레일 구멍 밑 살 {LS['rail_floor_under_hole']:g} (인서트 {LS['insert_engage']:g} 추정)", ok=CK['lid_screw_ok']),
 dict(item='【3a】 Pi 방향', value=f"L2 글에서 회전 {PI['rot_deg']}°, CAD 커넥터 상자와 {PI['disp1_vs_cad']} mm", ok=CK['pi_orientation_ok']),
 dict(item='시선', value=f"가운데까지 {E['angle_to_centre']}°, 기울기와 {E['tilt_diff']}° 차이, 모듈 뒤끝에서 아래 끝 시선 z{E['sightline_z_at_module']}", ok=CK['sightline_ok']),
 dict(item='소리 길', value=f"유닛→귀 선이 화면과 {CK['sound_paths_min']} mm, 27° 규칙 {SR['clear_above_module_edge']} mm", ok=CK['sound_paths_min'] > 50 and CK['sound_rule_ok']),
 dict(item='10 N 터치', value=f"다리 {ST['leg_force']} N, 좌굴 {ST['leg_Pcr']} N ({ST['leg_SF']}배)", ok=ST['leg_SF'] > 3),
 dict(item='앞으로 10 N 당김', value=f"뒤꿈치 {ST['heel_force']} N, 앞 나사 합계 {ST['lid_screws_total']} N", ok=True),
 dict(item='뒷바만 있을 때 넘어짐', value=f"{ST['rear_bar_alone']['M_over']} vs {ST['rear_bar_alone']['M_res']} N·m ({ST['rear_bar_alone']['SF']}배, 3.3 kg 추정)", ok=ST['rear_bar_alone']['SF'] > 1),
 dict(item='【3a】 스터드 대비안', value=f"보스를 파면 물림 {SB['engage']:g}, 접은 머리와 뚜껑 {SB['fold_head_to_lid']:g}, 발 {SB['fold_head_to_feet_plan']:g}", ok=CK['studs_fallback_ok']),
 dict(item='전력 (D19)', value=f"순간 {PWR['peak_W']} W / 60 W, 평균 {PWR['avg_W'][0]}~{PWR['avg_W'][1]} W", ok=PWR['margin_60W'] > 0),
 dict(item='홀센서 거리 (D14)', value=f"{N['sensor_gap']} mm, 자석 없음", ok=N['sensor_gap'] > 100),
]

printed_parts = [
 f"화면 받침 {CR['size'][0]}×{CR['size'][1]}×{CR['size'][2]} + 귀 2 + 다리 걸이 + 클립 + 패드 4 — 윗변을 베드에, 높이 {CR['print_height']}, 약 {N['mass_est']['cradle_g']:.0f} g, 약 {N['mass_est']['cradle_h']:.1f}시간(추정)",
 f"받침다리 {LG['length']+6:g}×{LG['section'][0]:g}×{LG['section'][1]:g} — 약 {N['mass_est']['leg_g']:.0f} g",
 "점검창 덮개(볼록 자리 포함) — 약 4 g",
 f"리본 클립 30×12×3 + 핀 2(길이 {CL['pin_len']:g}) + 전원선 홈 — 약 1 g",
 "가운데 뚜껑에 더하는 것(경첩 받침 2, 멈춤 블록, 주머니 덩어리, 받침 발 4, 구멍 벽, 클립 덩어리, 나사 기둥 4) — L2 뚜껑 출력에 포함",
 f"(선택) 화면 덮개 {CR['size'][0]+2:.0f}×{CR['size'][1]+2:.0f}×3 — 약 70 g",
]

open_issues = [
 (f"L2 확정값(L2_cu.json, {PL['source_note'][:60]})으로 계산했습니다. 모듈 위 금지선은 과제 규칙 y215를 씁니다(확정 뒷바 앞면 y{PL['keepout']['rear_bar_front_y']:g}, 모듈 뒤끝 y{PL['keepout']['module_rear_y']:g})." if PL['source_is_final'] else "L2 뒷바 값은 임시값입니다."),
 f"커넥터 쪽(오른쪽, 입구 +x)은 사진으로 판단한 추정입니다. 반대면 창·홈·구멍·클립만 x{XC:g} 기준으로 뒤집습니다(아래 벽 홈은 그대로).",
 "모서리 M2.5 구멍 깊이와 스터드 여부를 모릅니다. 받으면 재서 C-3 규칙을 적용합니다. 스터드면 G-2처럼 보스를 팝니다.",
 f"화면 아래 끝 돌기(xr{NT['feature_xr'][0]}~{NT['feature_xr'][1]}, 약 {NT['feature_proud']})는 도면에서 잰 추정입니다(G-7).",
 "Pi 5 micro-HDMI·방열판 자리는 추정입니다. 리본이 HDMI 위에 얹히는 것과 방열판이 CAD 지킴 구역 밖인지는 실제 Pi로 확인합니다(G-8).",
 (f"CAD 권장 경첩(y{PL['cad_recommendations']['hinge']['y'][0]}~{PL['cad_recommendations']['hinge']['y'][1]}, z{PL['cad_recommendations']['hinge']['z']})은 쓰지 않았습니다. 22°에서 받침 앞 아래 모서리가 축보다 {HG['front_reach']} mm 앞으로 나오므로 축이 y{HG['axis_yz'][0]}보다 앞이면 모듈 위로 넘어갑니다." if PL['cad_recommendations'].get('hinge') else ''),
 f"뚜껑 레일 인서트 길이({LS['insert_engage']:g})와 나사 x({LS['x'][0]:g}·{LS['x'][1]:g})는 추정입니다(A-7 식).",
 "화면 무게 0.30 kg, 뒷바 3.3 kg, 눈 위치 y−350 z450은 추정값입니다.",
 "sound-requirements.md의 R31·D20·D22·D23·D24(공식 TD2, 경첩 y290 z96 등)는 3판 값으로 고쳐야 합니다(이 작업에서는 저장소를 고치지 않음).",
]
open_issues = [o for o in open_issues if o]

files = [str(D / f) for f in ['geom3.py', 'build3.py', 'draw3.py', 'numbers.json', 'design.json', 'texts.json', 'CAD_SPEC_rev3.md',
                              'README_rev3.md', 'touch_concept_rev3.svg', 'touch_concept_rev3.png', 'build3d.py', 'preview3d_rev3.png', 'preview3d_rev3.glb']]
texts = dict(summary_ko=summary_ko, placement=placement_txt, mount=mount_txt, cable=cable_txt, power=power_txt, software=software_txt,
             transport=transport_txt, printed_parts=printed_parts, open_issues=open_issues, cad_spec_md=spec, changes=changes, fixes_3a=fix3a)
json.dump(texts, open(D / 'texts.json', 'w'), ensure_ascii=False, indent=1)
design = dict(rev=3, revision=N.get('revision'), date='2026-10-01', screen_choice='B1 Waveshare 7-DSI-TOUCH-C', summary_ko=summary_ko, changes_vs_rev2=changes,
              fixes_3a=fix3a, placement=placement_txt, mount=mount_txt, cable=cable_txt, power=power_txt, software=software_txt, transport=transport_txt,
              checks=checks, printed_parts=printed_parts, open_issues=open_issues, cad_spec_md=spec,
              materials_note='구매 목록은 이미 고침(화면, GUOCONN 22P 0.5 mm 300 mm B형 + A형, 실리콘 점퍼 4, M3×20 ×4, M2.5×6 ×4, M3×10 +4)',
              drawing_svg=str(D / 'touch_concept_rev3.svg'), drawing_png=str(D / 'touch_concept_rev3.png'), files=files, numbers=N)
json.dump(design, open(D / 'design.json', 'w'), ensure_ascii=False, indent=1)
(D / 'CAD_SPEC_rev3.md').write_text(spec, encoding='utf-8')

readme = f"""# R31 터치스크린 수정 3판 3a (B1 · L2) — 파일 안내

- 화면: Waveshare 7-DSI-TOUCH-C (사용자 선택 B1), 자리: L2 뒷바 가운데 뚜껑. L2 값: {SRC}
- 순서: `python3 work/measure_bottom_feature.py` (도면에서 아래 끝 돌기 재기, 한 번) → `python3 geom3.py` (자리 블록 → numbers.json) → `python3 build3.py` (design.json, texts.json, CAD_SPEC_rev3.md, 이 파일) → `python3 draw3.py` (touch_concept_rev3.svg/png, 크롬으로 PNG) → `python3 build3d.py` (확인용 상자 3D: preview3d_rev3.png/.glb, CAD 아님, 출력용 STL 아님)
- 자리 블록은 numbers.json `placement` 하나입니다. L2 확정 파일(`../L2_cu.json`)이 있으면 자동으로 그것을 읽습니다. 스피커 유닛 자리는 work/body_L2_copy.json(저장소 body_L2.json 사본, 돌릴 때마다 md5 비교).
- 부품 모양은 받침 좌표(xr, u, w)로 정의하고, 세운·뒤꿈치·접은 자세는 `poses`의 4×4 행렬로 world로 옮깁니다.
- 3a(검수 반영)에서 바뀐 것은 CAD_SPEC_rev3.md의 "3a에서 고친 것" 표에 있습니다. 고치기 전 결과는 rev3a_before/에 있습니다.

핵심 값: 경첩 축 y{HG['axis_yz'][0]} z{HG['axis_yz'][1]} · 가장 앞 y{N['all_min_y']} · 받침 {CR['size'][0]}×{CR['size'][1]}×{CR['size'][2]} (출력 높이 {CR['print_height']}) · 접음 z{FO['top_z']}, 뒤끝 y{FO['y'][1]} · 다리 {LG['length']:g} mm {LG['angle_deg']}° (22°에서 넣음) · 가로 리브 u{CR['cross_ribs_u'][0]:g}·{CR['cross_ribs_u'][1]:g} · 리본 약 {RB['total']:.0f}/300 mm {RB['ffc_type'][0]}형 · 전원선 약 {PW['total']:.0f} mm · 10 N에 다리 {ST['leg_force']} N

파일: geom3.py, build3.py, draw3.py, build3d.py, numbers.json, design.json, texts.json, CAD_SPEC_rev3.md, touch_concept_rev3.svg/png, preview3d_rev3.png/.glb(확인용 상자 모형), rev2_src/(2판 원본 복사), rev3a_before/(3판 처음 결과), work/(사진·잘라낸 그림·key_numbers·body_L2 사본, measure_bottom_feature.py)
"""
(D / 'README_rev3.md').write_text(readme, encoding='utf-8')
print('ok', len(spec), 'chars spec;', sum(1 for c in checks if c['ok']), '/', len(checks), 'checks ok;', [c['item'] for c in checks if not c['ok']])
