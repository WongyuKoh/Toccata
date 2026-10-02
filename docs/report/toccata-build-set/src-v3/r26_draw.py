"""R26~R29 도면: 7 전체 배치, 8 스피커 파트, 9 오디오·전원 배선, 10 뒷바 구성, 11 가운데 유닛 재단도."""
import math
from draw import SVG, fmt
from patch_r26 import Y0, Y1, DEPTH, RAISE, CH_D, T, CN_X0, CN_X1, CN_H, DIV1, DIV2, SPK_H, IN_H, IN_D
from patch_r26 import ENT_X0, ENT_W, ENT_Y0, ENT_D   # CU 트레이 케이블 입구(도면 7 USB 묶음 끝과 같은 값)
from patch_r26 import COMB_X0, COMB_W, COMB_D, BCOMB_W   # 건반 보관함 예비 콤(본문 '오른쪽 … mm'와 같은 값)
try:  # 스피커 고정 피스·링 길이(설계 문구와 같은 값)
    from patch_r26 import SCR_UNIT, SCR_GRILL, RING_L
except ImportError:
    SCR_UNIT, SCR_GRILL, RING_L = 16, 19, 10   # 8호 직결피스 16 mm(유닛)·19 mm(그릴), 스페이서 링 10 (ASM12·L49)

KERF = 3                        # 재단 톱날
GRILL_T = 2                     # PETG 그릴 판 두께
GR_X0, GR_V0, GR_S = 25, 55, 130  # PETG 육각 그릴 130×130(정면 x·높이 시작)
RING_W = 12                     # 스페이서 링 벽 폭(그릴 피스 Ø4.2 구멍 x33·147, 높이 63·177이 벽 안에 들어가도록)
UNIT_W = 105                    # 유닛 프레임·플랜지 폭(정면 105×105)
UNIT_F, UNIT_B = -7, 54         # 배플 바깥면 기준 유닛 앞(플랜지)·뒤(자석) 끝, 깊이 61
SPK_W = 180                     # 스피커 파트 폭
FOOT_L, FOOT_H = 28, 18         # 고무발 L14 외경 28(단면 밑변), 높이 18 (+ 받침 RAISE−18)
FOOT_Y = (Y0 + 70, Y1 - 45)     # 발 두 줄(앞끝 y)
SPK_FOOT_X = (6, 146)           # 스피커 파트 정면 기준 발 앞끝 x
CN_FOOT_CX = (CN_X0 + 36, (DIV1 + DIV2) / 2, CN_X1 - 36)   # 가운데 유닛 발 중심 x 3열
PI = (DIV1 + T / 2 + 6, Y1 - T - 64, 85, 56)        # Pi 5 (x, y, 폭, 깊이)
BUCK = (DIV1 + T / 2 + 110, Y0 + CH_D + 8, 61, 40)  # 5.1 V 강압 모듈


def _cls(n):
    if 'USB 케이블' in n or 'EXT 선' in n:
        return 'thin'
    if n.startswith('가운데 유닛'):
        return 'fixed'
    if '보관함' in n or '보조배터리' in n:
        return 'part'
    if n.startswith('CU 칸'):
        return 'pcb'
    if n.startswith('I/O'):
        return 'flex'
    if '케이블 통로' in n:
        return 'zone'
    if '브래킷' in n:  # L·R 같은 부품(L42, 구역 spk)
        return 'flex'
    if '모듈 O' in n or ('끝 부속' in n and '선' not in n):
        return 'part'
    if 'A#0' in n:
        return 'black'
    if '건반' in n:
        return 'white'
    if '스피커' in n:
        return 'spk'
    if '센서 열' in n:
        return 'center'
    if '브래킷' in n:
        return 'flex'
    return 'part'


# ================================================================ 7. 전체 배치(R27)
def assembly_r26(items, draw_poly):
    s = SVG(-40, -440, 1260, 560, scale=0.62, pad=(60, 30, 60, 40))
    order = []
    for p in items('assembly_plan'):
        n = p['name']
        if '페달 3개' in n:
            p = dict(p, name='댐퍼 페달 1개(바닥, 책상 앞)', points=[[640, -400], [716, -400], [716, -160], [640, -160]])
        order.append(p)
    first = [p for p in order if p['name'].startswith('가운데 유닛')]
    zone = [p for p in order if '케이블 통로' in p['name']]
    rest = [p for p in order if p not in first and p not in zone]
    for p in first + rest + zone:  # 통로(채움 없음)는 맨 위에
        draw_poly(s, p, _cls(p['name']))
    s.rect(ENT_X0, ENT_Y0, ENT_W, ENT_D, 'flexb', 'CU 트레이 케이블 입구')  # USB 묶음 끝이 닿는 곳(도면 10과 같은 입구)
    n_usb = sum(1 for p in order if p['name'].startswith('USB 케이블 O'))
    for k in range(7):
        s.text(47 + 164.5 * k + 82.25, 100, f'O{k + 1}', 'ttl')
    s.text(23, 180, 'L', 'ttl')
    s.text(1218, 180, 'R', 'ttl')
    s.text(345, 330, '건반 보관함', 'lbl')
    s.text(620, 330, 'CU 칸', 'lbl')
    s.text(886, 330, '보조배터리 칸', 'lbl')
    s.text(74, 330, '스피커 L', 'lbl')
    s.text(1148, 330, '스피커 R', 'lbl')
    s.dim_h(-16, 1238, Y1, 64, '1254 전체 폭 (볼 포함)')
    s.dim_h(0, 1222, 0, -24, '1222 (88건반)')
    s.dim_h(-16, 47, 0, -50, '63')
    s.dim_h(47, 211.5, 0, -50, '164.5')
    s.dim_h(1198.5, 1238, 0, -50, '39.5')
    s.dim_h(-16, CN_X0, Y1, 32, '180')
    s.dim_h(CN_X0, CN_X1, Y1, 32, '894 가운데 유닛')
    s.dim_h(CN_X1, 1238, Y1, 32, '180')
    s.dim_v(0, Y1, 1238, 54, f'{Y1} 깊이')      # 큰 치수가 바깥(보조선이 안쪽 글자를 지나지 않게)
    s.dim_v(Y0, Y1, 1238, 24, f'{DEPTH} 뒷바')
    s.dim_v(0, 212, -16, -24, '212')
    # 통로 지시선 점: 통로 띠 안, 가운데 유닛 앞판 두께 가운데(y{Y0 + T/2}). x490이면 선이 O2·O3 글자 사이를 지나고
    # 아래 '63 | 164.5' 치수의 화살촉(x47~56)과 '164.5' 글자 사이로 빠진다(O1 글자·USB 세로선 x460과도 떨어짐)
    s.leader_abs(490, Y0 + T / 2, 40, -110, f'케이블 통로: 뒷바 아래 앞쪽 y{Y0}~{Y0 + CH_D}, z0~{RAISE} (USB {n_usb}가닥 → CU 칸 입구)', 'start')
    s.leader_abs(660, 404, 850, 540, 'I/O 판: USB-C 전원 입력 · 전원 스위치 · 페달 잭', 'start')
    s.leader_abs(20, 214, -30, 540, '방진 브래킷(틈 3 mm, 그로밋)', 'start')
    s.leader_abs(716, -280, 780, -280, '댐퍼 페달 1개 (R24 · 듀로 개조 76×240)', 'start')
    s.scalebar(200)
    return s.render('전체 배치 평면도(R27)', '직사각형 1254 × 410, A0 왼쪽 경계 x=0 기준, 단위 mm')


# ================================================================ 8. 스피커 파트(R25·R26)
def spk_box_r26():
    D, I_D = DEPTH, DEPTH - 2 * T  # 195, 172
    s = SVG(-20, -44, 520, 226, scale=1.4, pad=(240, 44, 310, 44))
    # --- 정면 (x0~180)
    s.rect(0, 0, T, SPK_H, 'fixed', '옆판(왼쪽) 끝면')
    s.rect(180 - T, 0, T, SPK_H, 'fixed', '옆판(오른쪽) 끝면')
    s.rect(T, 0, 180 - 2 * T, SPK_H, 'flexb2', '앞판(배플) PETG 출력 157×210×11.5')
    UC = (90, 120)  # 유닛 중심(정면 x, 상자 바닥에서 높이)
    UV0 = UC[1] - UNIT_W / 2                                  # 유닛 프레임·플랜지 아래 끝 67.5
    s.rect(UC[0] - UNIT_W / 2, UV0, UNIT_W, UNIT_W, 'ghostfill', f'유닛 프레임 {UNIT_W}×{UNIT_W}')
    s.rect(GR_X0, GR_V0, GR_S, GR_S, 'ghost', f'PETG 육각 그릴 {GR_S}×{GR_S}')
    s.circle(*UC, 47, 'hole')
    for dx in (-40.66, 40.66):
        for dv in (-40.66, 40.66):
            s.circle(UC[0] + dx, UC[1] + dv, 2.4, 'hole')
    for gx in (33, 147):
        for gv in (63, 177):
            s.circle(gx, gv, 2.1, 'part')
    WH_X, WH_R = 22, 3                       # 스피커선 구멍 Ø6
    WH_V = T + WH_R + 1.5                    # 아랫판 윗면(T) 위로 1.5 mm: 구멍이 통째로 상자 안으로 열린다
    s.circle(WH_X, WH_V, WH_R, 'hole')
    s.line((UC[0], UC[1] - 62), (UC[0], UC[1] + 62), 'center')
    s.line((UC[0] - 62, UC[1]), (SPK_W, UC[1]), 'center')  # 오른쪽 모서리까지(120 치수 보조선과 이어짐)
    pad_h = RAISE - FOOT_H
    for fx in SPK_FOOT_X:
        s.poly([(fx, -RAISE), (fx + FOOT_L, -RAISE), (fx + FOOT_L - 4, -pad_h), (fx + 4, -pad_h)], 'rubber', True, '고무발 L14')
        s.rect(fx + 4, -pad_h, FOOT_L - 8, pad_h, 'flex', f'받침 {pad_h} mm')
    s.dim_h(T, SPK_W - T, SPK_H, 22, f'{fmt(SPK_W - 2 * T)} 앞판(출력)')
    s.dim_h(0, SPK_W, SPK_H, 42, f'{SPK_W}')  # 전체 폭이 바깥 줄(157 보조선이 180 치수선을 가로지르지 않게)
    s.dim_v(0, UC[1], SPK_W, 18, f'{UC[1]}')
    s.dim_v(0, SPK_H, SPK_W, 46, f'{SPK_H}')  # 오른쪽 치수 줄(왼쪽 지시선과 겹치지 않게)
    xr = SPK_FOOT_X[-1] + FOOT_L  # 오른쪽 발 바닥 모서리
    s.dim_v(-RAISE, 0, xr, 18 + (SPK_W - xr) * s.s, f'{RAISE}')
    s.dim_h(GR_X0, GR_X0 + GR_S, GR_V0 + GR_S, 12, f'{GR_S} 그릴')
    # 지시선 글자 높이 순서 = 가리키는 점의 높이 순서(교차 없음)
    s.leader_abs(33, 177, -22, 196, f'그릴 고정 4곳 · 8호 직결피스 {SCR_GRILL} mm', 'end')
    s.leader_abs(UC[0] - 33.2, UC[1] + 33.2, -22, 160, '컷아웃 Ø94 (출력으로 구멍째)', 'end')
    s.leader_abs(UC[0] - 40.66, UC[1] - 40.66, -22, 90, f'유닛 나사 4 · 8호 직결피스 {SCR_UNIT} mm', 'end')
    s.leader_abs(WH_X, WH_V, -22, 30, '스피커선 구멍(아래 → 통로의 XT30)', 'end')
    s.leader_abs(10, -12, -22, -8, f'고무발 {FOOT_H} + 받침 {pad_h} = {RAISE} 띄움', 'end')
    s.text(90, -40, '정면 (배플, 연주자 쪽)', 'ttl')
    # --- 중앙 단면 (x = 300 + 깊이)
    o = 300
    s.rect(o, 0, D, SPK_H, 'faint')
    s.rect(o, 0, T, SPK_H, 'flexb2', '앞판(배플) 출력')
    s.rect(o + D - T, 0, T, SPK_H, 'fixed', '뒤판')
    s.rect(o + T, SPK_H - T, D - 2 * T, T, 'fixed', f'윗판 157×{I_D:.0f}')
    s.rect(o + T, 0, D - 2 * T, T, 'fixed', f'아랫판 157×{I_D:.0f}')
    s.rect(o + 150, T, D - T - 150, SPK_H - 2 * T, 'ghostfill', '흡음솜 40~60 g')
    s.rect(o - 3, UV0, 3, UNIT_W, 'pad', 'EVA 가스켓 3T')
    FL = (o + UNIT_F, UV0, 4, UNIT_W)        # 유닛 플랜지(배플 앞)
    MG = (o + 37, 77.5, UNIT_B - 37, 85)     # 자석(뒤끝 = UNIT_B)
    s.rect(*FL, 'part', '유닛 플랜지')
    s.poly([(o, 73), (o, 167), (o + 37, 142), (o + 37, 98)], 'spk', True, '유닛 바스켓·콘')
    s.rect(*MG, 'black', '자석 280 g')
    s.rect(o - RING_L - GRILL_T, GR_V0, GRILL_T, GR_S, 'flex', '그릴 면')
    for rv in (GR_V0, GR_V0 + GR_S - RING_W):  # 링은 배플 면에 닿는다. 벽 폭 안에 그릴 피스가 물린다
        s.rect(o - RING_L, rv, RING_L, RING_W, 'flex', f'스페이서 링 벽 {RING_W}')
    s.rect(o, -RAISE, CH_D, RAISE, 'zone', '케이블 통로')
    for fy in (o + y - Y0 for y in FOOT_Y):
        s.poly([(fy, -RAISE), (fy + FOOT_L, -RAISE), (fy + FOOT_L - 4, -pad_h), (fy + 4, -pad_h)], 'rubber', True, '고무발 L14')
        s.rect(fy + 4, -pad_h, FOOT_L - 8, pad_h, 'flex', f'받침 {pad_h} mm')
    DIM_IN_V = 150
    W_in, H_in = SPK_W - 2 * T, SPK_H - 2 * T
    s.dim_h(o, o + D, SPK_H, 22, f'{D}')
    s.dim_h(o + T, o + D - T, DIM_IN_V, 0, f'{I_D:.0f} 내부')
    EVA_DOT, EVA_LV = (o - 2, 100), 110      # 가스켓 지시선 점·글자 높이
    X187 = o + 120
    eva_kx = o + D + 20 - 10 / s.s           # 지시선 꺾임점 x(leader_abs: 글자 앞 10 px)
    eva_v = EVA_DOT[1] + (EVA_LV - EVA_DOT[1]) * (X187 - EVA_DOT[0]) / (eva_kx - EVA_DOT[0])  # 187 치수선 자리의 가스켓 지시선 높이
    s.dim_v(T, SPK_H - T, X187, 0, f'{H_in:.0f} 내부', lab_v=(DIM_IN_V + eva_v) / 2)  # 글자는 172 치수선과 가스켓 지시선 사이
    off61 = -((MG[1] - 30) * s.s + 14)
    s.dim_h(FL[0], MG[0] + MG[2], MG[1], off61, f'{MG[0] + MG[2] - FL[0]:.0f}')
    s.text(MG[0] + MG[2], MG[1] + off61 / s.s, '유닛 깊이', 'dimt', 'start', dx=4, dy=-3)  # 배플 띠 밖, 치수 오른쪽 끝
    s.dim_h(o, o + CH_D, -RAISE, -14, f'{CH_D} 통로')
    ABS_V = (DIM_IN_V + SPK_H - T) / 2       # 172 치수선과 윗판 사이
    s.leader_abs(o + 150 + (D - T - 150) / 2, ABS_V, o + D + 20, ABS_V, '흡음솜 40~60 g (L12, 느슨하게)', 'start')
    s.leader_abs(o + 100, 190, o + D + 20, 196, f'내부 {fmt(W_in)}×{I_D:.0f}×{fmt(H_in)} = {W_in * I_D * H_in / 1e6:.2f} L', 'start')
    s.leader_abs(*EVA_DOT, o + D + 20, EVA_LV, 'EVA 가스켓 3T + 목공본드로 밀폐', 'start')
    s.leader_abs(o - RING_L / 2, GR_V0 + GR_S - RING_W / 2, o + D + 20, 156, f'PETG 육각 그릴 + 스페이서 링 {RING_L}', 'start')  # 점은 위 링 벽 가운데
    s.leader_abs(o + 20, -10, o + D + 20, 25, '앞 43 mm 아래는 케이블 통로(XT30이 여기서 만남)', 'start')  # 글자 25: 선이 187 치수 아래 화살 끝 4 px 밑을 지난다
    s.text(o + 120, -40, '중앙 단면 (왼쪽이 연주자 쪽)', 'ttl')
    s.scalebar(50)
    top = s.render('스피커 파트 정면·단면(R26)', '앞판은 PETG 출력, 나머지는 오꾸메 11.5T, 단위 mm')
    # --- 재단도 400×1200 (앞판은 출력이라 합판에서 빠짐)
    c = SVG(0, 0, 1200, 400, scale=0.58, pad=(70, 40, 40, 40))
    c.rect(0, 0, 1200, 400, 'faint')
    x = 0
    for i in range(4):
        c.rect(x, 190, D, 210, 'fixed', f'옆판 {D}×210')
        c.text(x + D / 2, 300, '옆판', 'lbl')
        c.text(x + D / 2, 282, f'{D}×210', 'dimt')
        x += D + KERF
    for i in range(2):
        c.rect(x, 190, 157, 210, 'fixed', '뒤판 157×210')
        c.text(x + 78.5, 300, '뒤판', 'lbl')
        c.text(x + 78.5, 282, '157×210', 'dimt')
        x += 157 + KERF
    c.text((x + 1200) / 2, 295, '남음', 'lbl')
    x = 0
    for i in range(4):
        c.rect(x, 30, I_D, 157, 'fixed', f'위·아래판 157×{I_D:.0f}')
        c.text(x + I_D / 2, 112, '위·아래판', 'lbl')
        c.text(x + I_D / 2, 94, f'{I_D:.0f}×157', 'dimt')
        x += I_D + KERF
    c.text((x + 1200) / 2, 105, '남음', 'lbl')
    c.dim_h(0, 1200, 400, 18, '1200')
    c.dim_v(0, 400, 1200, 20, '400')
    c.dim_v(190, 400, 0, -26, '210 띠')
    c.dim_v(30, 187, 0, -26, '157 띠')
    c.scalebar(200)
    cut = c.render('오꾸메 400×1200 재단도(스피커 파트 2개)', f'톱날 {KERF} mm 포함, 10장(앞판 2장은 출력), 단위 mm')
    cut = cut.replace('id="arr"', 'id="arr2"').replace('url(#arr)', 'url(#arr2)')
    return top + '<p class="mut small" style="margin:10px 4px 4px">아래: 스피커 파트 2개의 오꾸메 400×1200 재단도. 합판은 직선으로만 자르고, 구멍이 필요한 앞판(배플)은 PETG로 출력한다.</p>' + cut


# ================================================================ 9. 오디오·전원 배선(R25·R28)
def audio_wiring_r26(items):
    s = SVG(0, 0, 1100, 500, scale=0.84, pad=(20, 30, 20, 40))
    n_mod = sum(1 for p in items('assembly_plan') if p['name'].startswith('모듈 O'))
    C_UF, N_C, R_PD = 1, 2, 1000      # 채널마다 1 µF 2개 병렬 → 신호에 직렬, 1 kΩ 풀다운(D18)
    fc = 1 / (2 * math.pi * R_PD * C_UF * N_C * 1e-6)

    def box(x, v, w, h, title, sub='', cls='part'):
        s.rect(x, v, w, h, cls, title)
        s.text(x + w / 2, v + h - 16, title, 'ttl')
        for i, line in enumerate([t for t in sub.split('\n') if t]):
            s.text(x + w / 2, v + h - 34 - 16 * i, line, 'lbl')

    def wire(pts, lab=None, at=0.5, dv=6, cls='lead'):
        s.poly(pts, cls, False)
        if lab:
            (x1, v1), (x2, v2) = pts[0], pts[-1]
            s.text(x1 + (x2 - x1) * at, v1 + (v2 - v1) * at + dv, lab, 'lbl')

    # 전원 줄(위)
    box(900, 420, 190, 60, '벽 65 W PD 충전기', '또는 보조배터리(PD 20 V 3 A↑)', 'fixed')
    box(735, 420, 140, 60, 'PD 트리거 20 V', 'USB-C 입력(I/O 판)', 'fixed')
    box(655, 420, 60, 60, '퓨즈', '', 'fixed')
    box(555, 420, 80, 60, '스위치', '', 'fixed')
    box(445, 420, 90, 60, '20 V 단자', '', 'fixed')
    box(225, 420, 170, 60, '5.1 V 5 A 강압', 'Pi·허브 전원', 'fixed')
    wire([(900, 450), (875, 450)])
    wire([(735, 450), (715, 450)])
    wire([(655, 450), (635, 450)])
    wire([(555, 450), (535, 450)])
    wire([(445, 450), (395, 450)])
    # 신호 줄(가운데)
    box(20, 220, 150, 110, 'Pi 5 (L01)', 'FluidSynth\nhw:<동글>,0', 'pcb')
    box(215, 235, 130, 70, 'USB 동글 (L51)', 'DAC + 헤드폰 앰프')
    box(395, 180, 140, 170, 'PJ-313 (L15)', '왼쪽 볼 헤드폰 잭', 'part')
    for v, lab in ((290, 'T (L)'), (265, 'R (R)'), (240, 'S (GND)')):
        s.text(401, v, lab, 'lbl', 'start')
    for v, lab in ((225, 'TN'), (203, 'RN')):
        s.text(529, v, lab, 'lbl', 'end')
    box(575, 180, 160, 150, '앰프 입력 잭 + RC',
        f'PJ-313 (선 ② 플러그)\n{C_UF:g} µF×{N_C} 병렬 = {C_UF * N_C:g} µF (L56)\n신호에 직렬 · fc ≈ {fc:.0f} Hz\n{R_PD / 1000:g} kΩ → GND (L29)', 'flexb2')
    box(775, 170, 130, 210, 'XH-A232 (L53)', 'TPA3110 · 20 V\n8 Ω 약 19~23 W/ch\nBTL: −선 GND 금지', 'pcb')
    box(985, 290, 105, 60, 'L 스피커', 'CW-100B25', 'spk')
    box(985, 190, 105, 60, 'R 스피커', 'CW-100B25', 'spk')
    box(20, 40, 150, 110, 'USB 허브 (L17)', f'모듈 O1~O{n_mod} · PED\n통로 USB-C {n_mod} + CU 안 1', 'part')
    wire([(170, 270), (215, 270)], '젠더', 0.5, 6)
    wire([(345, 282), (395, 282)], '선 ①', 0.5, 6)  # TRS 플러그 전체(T·R·S) — 핀 한 줄이 아니라 두 핀 사이로 들어간다
    wire([(535, 225), (575, 225)], 'L', 0.5, 5)
    wire([(535, 203), (575, 203)], 'R', 0.5, -13)
    s.text(557, 160, '선 ②', 'lbl')
    wire([(465, 180), (465, 150), (655, 150), (655, 180)], None)
    wire([(735, 250), (775, 250)], 'IN L', 0.5, 5)
    wire([(735, 220), (775, 220)], 'IN R', 0.5, -13)
    wire([(655, 150), (840, 150), (840, 170)], None)
    s.text(850, 156, 'IN G', 'lbl', 'start')
    wire([(905, 320), (985, 320)], 'XT30', 0.5, 6)
    wire([(905, 220), (985, 220)], 'XT30', 0.5, 6)
    wire([(95, 150), (95, 220)], None)
    s.text(103, 185, 'USB-A', 'lbl', 'start')
    # 전원 선
    wire([(490, 420), (490, 400), (840, 400), (840, 380)], None)
    s.text(660, 406, '20 V', 'lbl')
    wire([(310, 420), (310, 360), (95, 360), (95, 330)], None)
    s.text(200, 366, '5.1 V (USB-C)', 'lbl')
    wire([(225, 450), (8, 450), (8, 95), (20, 95)], None)
    s.text(14, 395, '5 V', 'lbl', 'start')
    s.text(560, 110, '헤드폰을 꽂으면 TN·RN 접점이 떨어져 앰프 입력이 끊긴다(R15)', 'lbl')
    s.text(560, 90, 'Pi에는 강압 모듈의 5 V만 넣는다(USB-C 동시 급전 금지, D16)', 'lbl')
    s.text(560, 70, '보조배터리·충전기는 PD 20 V 3 A 이상(D19) · 선 ①·②와 XT30은 꽂았다 뺀다(R26)', 'lbl')
    return s.render('오디오·전원 배선도(R28)', 'USB-C PD 입력 하나 → 20 V(앰프)·5.1 V(Pi·허브), 소리는 동글 → 헤드폰 잭 → RC → 앰프 → 스피커')


# ================================================================ 10. 뒷바 구성(R26~R29)
def rear_bar_r26(items, draw_poly):
    def mp(key, pre):
        return next(p for p in items(key) if p['name'].startswith(pre))

    n_mod = sum(1 for p in items('assembly_plan') if p['name'].startswith('모듈 O'))
    # (가) 위에서 본 뒷바 속
    s = SVG(-30, Y0 - 12, 1250, Y1 + 12, scale=0.74, pad=(40, 120, 40, 90))
    s.rect(-16, Y0, 1254, CH_D, 'zone', '케이블 통로')
    s.rect(-16, Y0, SPK_W, DEPTH, 'spk', '왼쪽 스피커 파트')
    s.rect(CN_X1, Y0, SPK_W, DEPTH, 'spk', '오른쪽 스피커 파트')
    for x0 in (-16, CN_X1):
        cx = x0 + SPK_W / 2
        s.rect(cx - UNIT_W / 2, Y0 + UNIT_F, UNIT_W, UNIT_B - UNIT_F, 'faint', f'유닛(폭 {UNIT_W} · 깊이 {UNIT_B - UNIT_F})')
        s.text(cx, Y0 + (UNIT_F + UNIT_B) / 2, '유닛', 'lbl')
    s.rect(CN_X0, Y0, CN_X1 - CN_X0, DEPTH, 'fixed', '가운데 유닛 894×195')
    rooms = ((CN_X0 + T, DIV1 - T / 2, 'ks'), (DIV1 + T / 2, DIV2 - T / 2, 'cu'), (DIV2 + T / 2, CN_X1 - T, 'pb'))
    for x0, x1, lab in rooms:
        s.rect(x0, Y0 + T, x1 - x0, IN_D, 'part' if lab != 'cu' else 'pcb', lab)
    # 건반 보관함: 예비 콤 1세트
    cy0 = Y0 + T + (IN_D - COMB_D) / 2        # 콤을 칸 깊이 가운데에(앞뒤 3.75)
    s.rect(COMB_X0, cy0, COMB_W, COMB_D, 'white', f'예비 백건 콤 {fmt(COMB_W)}×{fmt(COMB_D)}×22')
    s.rect(COMB_X0 + (COMB_W - BCOMB_W) / 2, cy0, BCOMB_W, COMB_D, 'ghost', f'예비 흑건 콤 {fmt(BCOMB_W)}×{fmt(COMB_D)}×32(위에 겹침)')
    for i in range(3):
        s.rect(410 + 34 * i, Y0 + 30, 30, 150, 'faint', '작은 부품 칸')
    s.text(COMB_X0 + COMB_W / 2, Y0 + 110, '예비 백건 콤', 'lbl lblk')        # 흰 콤(고정색) 위: 어두운 글자
    s.text(COMB_X0 + COMB_W / 2, Y0 + 95, '(흑건 콤을 위에 겹침)', 'lbl lblk')
    s.text(461, Y0 + 17, '작은 부품', 'lbl')
    # CU 칸: 배치 예(안폭 188.5 — 허브 228은 보조배터리 칸으로)
    s.rect(*PI, 'pcb', f'Pi 5 {PI[2]}×{PI[3]}')
    s.rect(DIV1 + T / 2 + 100, Y1 - T - 64, 50, 40, 'pcb', 'XH-A232')
    s.rect(*BUCK, 'part', f'5.1 V 강압 {BUCK[2]}×{BUCK[3]}')
    s.rect(DIV1 + T / 2 + 6, Y0 + CH_D + 8, 60, 45, 'pcb', 'PED 보드·앰프 입력 잭')
    PD = (DIV1 + T / 2 + 100, Y1 - T - 20, 30, 16)
    s.rect(*PD, 'part', 'PD 트리거')
    s.rect(ENT_X0, ENT_Y0, ENT_W, ENT_D, 'flexb2', 'CU 트레이 케이블 입구')
    for (x, y, lab) in ((PI[0] + PI[2] / 2, PI[1] + PI[3] / 2, 'Pi 5'), (DIV1 + T / 2 + 125, Y1 - T - 44, '앰프'),
                        (BUCK[0] + BUCK[2] / 2, BUCK[1] + BUCK[3] / 2, '5 V'), (DIV1 + T / 2 + 36, Y0 + CH_D + 30, 'PED')):
        s.text(x, y, lab, 'lbl')
    s.text(PD[0] + PD[2] / 2, PD[1] + PD[3] / 2, 'PD', 'lbl', dy=4)  # 작은 사각형 안 가운데(글자 높이 절반만큼 내림)
    # 보조배터리 칸: 앞쪽 받침, 뒤 벽에 USB 허브
    s.rect(DIV2 + 20, Y0 + T + 6, 170, 85, 'ghostfill', '받침(최대 170×85×35)')
    s.rect(DIV2 + 30, Y0 + T + 12, 105, 71, 'part', '보조배터리 예 105×71(MT-65)')
    s.rect(DIV2 + 30, Y1 - T - 54, 228, 48, 'part', 'USB 허브 228×48(710U3)')
    s.text(DIV2 + 82, Y0 + T + 50, '보조배터리', 'lbl')
    s.text(DIV2 + 144, Y1 - T - 26, f'USB 허브(모듈 {n_mod} + PED 1)', 'lbl')
    # I/O 판, XT30, 도브테일, 래치
    s.rect(DIV1, Y1 - T, 200, T, 'flex', 'I/O 판')
    for x in (CN_X0 + 8, CN_X1 - 22):
        s.rect(x, Y0 + 8, 14, 10, 'black', 'XT30')
    for x in (CN_X0, CN_X1):
        for y in (Y0 + 60, Y1 - 50):
            s.rect(x - 4, y, 8, 18, 'flexb2', '도브테일')
        s.rect(x - 12, Y1 - 3, 24, 6, 'flex', '토글 래치')
    # 고무발 L14: 스피커 파트 2 × 2 + 가운데 유닛 3열 × 2 = 14 (단면·스피커 도면과 같은 두 줄)
    feet_x = ([-16 + fx + FOOT_L / 2 for fx in SPK_FOOT_X] + [CN_X1 + fx + FOOT_L / 2 for fx in SPK_FOOT_X]
              + list(CN_FOOT_CX))
    assert len(FOOT_Y) * len(feet_x) == 14
    for y in FOOT_Y:
        for x in feet_x:
            s.circle(x, y + FOOT_L / 2, FOOT_L / 2, 'ghostfill')  # 바닥 아래 숨은 발
    s.dim_h(-16, 1238, Y1, 44, '1254')
    for x0, x1, _ in rooms:  # 칸 안치수: 칸 안쪽 모서리(뒤판 안면)에서
        s.dim_h(x0, x1, Y1 - T, 20 + T * s.s, fmt(x1 - x0))
    s.dim_v(Y0, Y1, 1238, 24, f'{DEPTH}')
    s.dim_v(Y0, Y0 + CH_D, -16, -22, f'{CH_D}')
    s.text(294, Y0 - 30, '① 건반 보관함 (R29)', 'ttl')
    s.text(620, Y0 - 30, '② CU 칸', 'ttl')
    s.text(886, Y0 - 30, '③ 보조배터리 칸 (R28) · 허브', 'ttl')
    s.text(74, Y0 - 30, '스피커 L', 'ttl')
    s.text(1148, Y0 - 30, '스피커 R', 'ttl')
    s.leader_abs(CN_X0 + 15, Y0 + 13, 150, Y0 - 70, 'XT30(스피커선, 통로 안에서 연결)', 'start')
    s.leader_abs(CN_X1, Y1, 1000, Y1 + 95, '도브테일 2 + 뒷면 토글 래치 1(각 이음)', 'start')
    s.leader_abs(700, Y1 - 5, 640, Y1 + 95, 'I/O 판: USB-C 입력 · 선 통과 구멍 · 스위치 · 페달 잭', 'end')
    s.leader_abs(DIV2, Y0 + 100, 760, Y0 - 70, '칸막이를 20 mm 낮게: 허브·보조배터리 선이 넘어감', 'start')
    top = s.render('뒷바 속 배치(위에서 본 모습)', '왼쪽 스피커 파트 · 가운데 유닛(칸 셋) · 오른쪽 스피커 파트, 단위 mm')
    # (나) 옆 단면: 건반 + 뒷바(CU 칸을 지나는 단면) — 건반 모듈은 측면도(도면 2)의 모델 폴리곤 그대로
    c = SVG(-10, -8, 440, 250, scale=1.25, pad=(50, 30, 300, 58))
    for pre, cls in (('바닥 고무 시트', 'rubber'), ('프레임 바닥판', 'fixed'), ('척추 레일', 'fixed'), ('뒷벽 3.0', 'fixed'),
                     ('뒤 커버 윗판', 'part'), ('뒤 커버 앞 가림판', 'part'), ('뒤 커버 뒤 스커트', 'part')):
        draw_poly(c, mp('keybed_side', pre), cls)
    for pre, cls in (('백건 몸체 외곽', 'white'), ('백건 리프', 'flex'), ('백건 척추', 'part')):
        draw_poly(c, mp('white_key_side', pre), cls)
    pl = mp('keybed_side', 'USB-C 플러그')
    draw_poly(c, pl, 'black')
    fb_x1 = max(q[0] for q in mp('keybed_side', '프레임 바닥판')['points'])     # 212
    sk_x1 = max(q[0] for q in mp('keybed_side', '뒤 커버 뒤 스커트')['points'])  # 214
    cv = mp('keybed_side', '뒤 커버 윗판')
    cv_x0 = min(q[0] for q in cv['points'])
    cv_top = max(q[1] for q in cv['points'])
    px1 = max(q[0] for q in pl['points'])
    pz = (min(q[1] for q in pl['points']) + max(q[1] for q in pl['points'])) / 2
    c.rect(Y0, 0, CH_D, RAISE, 'zone', '케이블 통로')
    c.rect(Y0, RAISE, DEPTH, T, 'pcb', 'CU 트레이(출력 바닥)')
    c.rect(ENT_Y0, RAISE, ENT_D, T, 'flexb2', 'CU 트레이 케이블 입구')
    cab_y = Y0 + T + 2   # 케이블이 올라가는 y: 앞판 뒷면에서 2 mm(입구 y217~237 안)
    c.poly([(px1, pz), (cab_y, pz), (cab_y, RAISE + T + 8)], 'thin', False, 'USB-C 케이블')  # 트레이 입구를 지나 칸 안까지
    c.rect(Y0, RAISE + T, T, IN_H, 'fixed', '앞판')
    c.rect(Y1 - T, RAISE + T, T, IN_H, 'flex', 'I/O 판')
    c.rect(Y0, RAISE + CN_H - T, DEPTH, T, 'fixed', '뚜껑')
    c.rect(PI[1], RAISE + T + 6, PI[3], 20, 'pcb', 'Pi 5')
    c.text(PI[1] + PI[3] / 2, RAISE + T + 12, 'Pi 5', 'lbl')
    c.rect(BUCK[1], RAISE + T + 2, BUCK[3], 27, 'part', '5.1 V 강압')
    c.text(BUCK[1] + BUCK[3] / 2, RAISE + T + 10, '강압', 'lbl')
    c.poly([(Y0, RAISE), (Y0, RAISE + SPK_H), (Y1, RAISE + SPK_H), (Y1, RAISE)], 'ghostfill', False, '스피커 파트 윤곽(양 끝)')
    for y in FOOT_Y:
        c.poly([(y, 0), (y + FOOT_L, 0), (y + FOOT_L - 4, FOOT_H), (y + 4, FOOT_H)], 'rubber', True, '고무발')
        c.rect(y + 4, FOOT_H, FOOT_L - 8, RAISE - FOOT_H, 'flex', '받침')
    c.line((0, 0), (Y1, 0), 'thin')  # 바닥
    c.dim_h(0, fb_x1, 0, -40, f'{fmt(fb_x1)} 건반')   # 바닥선 아래 띠는 플러그 지시선 글자 자리
    c.dim_h(fb_x1, Y0, 0, -56, fmt(Y0 - fb_x1))      # 틈 3은 한 줄 아래(글자가 195 치수선 위에 얹히지 않게)
    c.dim_h(Y0, Y1, RAISE, -40 - RAISE * c.s, f'{DEPTH} 뒷바')
    c.dim_v(0, RAISE, Y1, 18, f'{RAISE}')            # '100'과 같은 줄
    c.dim_v(RAISE, RAISE + CN_H, Y1, 18, f'{CN_H}')
    c.dim_v(0, RAISE + SPK_H, Y1, 46, f'{RAISE + SPK_H} 스피커')
    c.dim_v(0, cv_top, 0, -24, fmt(cv_top), x2=cv_x0)  # 뒤 커버 윗면(앞 모서리)
    tx = cab_y + 3  # 케이블이 올라가는 선 오른쪽, 통로 안
    c.text(tx, RAISE - 8, '통로', 'dimt', 'start')            # 글자 위끝이 트레이 밑면(z RAISE)에 닿지 않게
    c.text(tx, RAISE - 16, f'{CH_D}×{RAISE}', 'dimt', 'start')
    c.leader_abs(*center_of_pts(pl['points']), 250, -10, 'USB-C 플러그가 통로로 들어가 굽는다', 'start')
    c.leader_abs(Y0 + 150, RAISE + T + 40, Y1 + 70, 100, 'CU 칸(Pi·앰프·전원, 허브는 옆 칸)', 'start')
    c.leader_abs(Y1 - 5, RAISE + T + 20, Y1 + 70, RAISE + 20, 'I/O 판(뒤)', 'start')  # 점은 I/O 판 안, 선은 '100' 글자 아래
    c.leader_abs(Y1 - 20, RAISE + SPK_H - 5, Y1 + 70, 220, f'스피커 파트 윤곽(양 끝, 높이 {RAISE + SPK_H})', 'start')
    c.scalebar(50)
    side = c.render('옆 단면(CU 칸을 지나는 면)',
                    f'건반 모듈 + 틈 {fmt(Y0 - fb_x1)}(커버 스커트와는 {fmt(Y0 - sk_x1)}) + 뒷바 {DEPTH}, 단위 mm')
    side = side.replace('id="arr"', 'id="arr3"').replace('url(#arr)', 'url(#arr3)')
    return top + '<p class="mut small" style="margin:10px 4px 4px">아래: 옆 단면. 뒷바를 22 mm 띄운 아래 앞쪽이 케이블 통로다. 모듈의 USB-C 플러그가 통로로 들어가 굽고, CU 트레이 입구로 올라간다.</p>' + side


def center_of_pts(pts):
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


# ================================================================ 11. 가운데 유닛 재단도(R26)
def cn_cut_r26():
    c = SVG(0, 0, 1200, 600, scale=0.58, pad=(70, 40, 40, 40))
    c.rect(0, 0, 1200, 600, 'faint')

    def piece(x, v, w, h, lab, size):
        c.rect(x, v, w, h, 'fixed', lab + ' ' + size)
        c.text(x + w / 2, v + h / 2 + 4, lab, 'lbl')
        c.text(x + w / 2, v + h / 2 - 12, size, 'dimt')

    L_W, R_W = DIV1 - CN_X0, CN_X1 - DIV2       # 356, 338
    v = 600 - DEPTH                             # 띠 A (폭 195)
    x = 0
    for w, lab in ((L_W, '바닥 왼쪽'), (R_W, '바닥 오른쪽'), (L_W, '뚜껑 왼쪽')):
        piece(x, v, w, DEPTH, lab, f'{w}×{DEPTH}')
        x += w + KERF
    v -= DEPTH + KERF                           # 띠 B (폭 195)
    piece(0, v, R_W, DEPTH, '뚜껑 오른쪽', f'{R_W}×{DEPTH}')
    piece(R_W + KERF, v + DEPTH - IN_H, IN_D, IN_H, '칸막이', f'{IN_D:.0f}×{IN_H:.0f}')
    c.text(R_W + KERF + IN_D + 200, v + 90, '남음(작은 부품 받침 등)', 'lbl')
    v -= IN_H + KERF                            # 띠 C (폭 77)
    piece(0, v, CN_X1 - CN_X0, IN_H, '앞판', f'{CN_X1 - CN_X0}×{IN_H:.0f}')
    piece(CN_X1 - CN_X0 + KERF, v, IN_D, IN_H, '끝판', f'{IN_D:.0f}×{IN_H:.0f}')
    v -= IN_H + KERF                            # 띠 D (폭 77)
    x = 0
    for w, h, lab in ((L_W, IN_H, '뒤판 왼쪽'), (R_W, IN_H, '뒤판 오른쪽'), (IN_D, IN_H, '끝판'), (IN_D, IN_H - 20, '칸막이(낮음)')):
        piece(x, v + IN_H - h, w, h, lab, f'{w:.0f}×{h:.0f}')
        x += w + KERF
    c.text(600, (v - KERF) / 2, f'남는 띠 약 {v - KERF:.0f}', 'lbl')  # 띠 D를 떼는 톱날 몫을 뺀 폭
    c.dim_h(0, 1200, 600, 18, '1200')
    c.dim_v(0, 600, 1200, 20, '600')
    c.scalebar(200)
    return c.render('오꾸메 600×1200 재단도(가운데 유닛)', f'톱날 {KERF} mm 포함, 11장(CU 칸 바닥·뚜껑·I/O 판은 출력). 낮은 칸막이(172×57)는 CU 칸과 보조배터리 칸 사이, 단위 mm')
