"""최종 설계 JSON(wf.json['final']) → 치수 도면 SVG 7장."""
import json
import math
import re
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else '.'
sys.path.insert(0, BASE)
from draw import SVG, fmt  # noqa: E402

D = json.load(open(BASE + '/wf.json'))
F = D['final']
from patch_r25 import apply_r25  # noqa: E402
apply_r25(F)  # R25: 스피커 좌우 2개, 서브 없음
from patch_r26 import apply_r26  # noqa: E402
apply_r26(F)  # R26~R29: 뒷바·배터리·보관함
from r26_draw import assembly_r26, spk_box_r26, audio_wiring_r26, rear_bar_r26, cn_cut_r26  # noqa: E402


def items(key):
    return F[key]


def rot(pts, c, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (y - c[0]) * ca - (z - c[1]) * sa, c[1] + (y - c[0]) * sa + (z - c[1]) * ca) for y, z in pts]


def draw_poly(s, p, cls):
    s.poly([tuple(q) for q in p['points']], cls, p.get('closed', True) is not False, p['name'])


def z_span_at(pts, x):
    """폴리곤 옆변들과 세로선 x의 교점 높이 (최소, 최대)."""
    zs = []
    n = len(pts)
    for i in range(n):
        (x1, z1), (x2, z2) = pts[i], pts[(i + 1) % n]
        if x1 != x2 and min(x1, x2) <= x <= max(x1, x2):
            zs.append(z1 + (z2 - z1) * (x - x1) / (x2 - x1))
    return min(zs), max(zs)


def center_of(p):
    xs = [q[0] for q in p['points']]
    ys = [q[1] for q in p['points']]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


# ================================================================ 1. 옥타브 평면도
def octave_plan():
    s = SVG(-10, -8, 180, 214, scale=3.1, pad=(150, 70, 330, 170))
    kp = items('key_plan')
    for p in kp:
        if '척추' in p['name']:
            draw_poly(s, p, 'fixed')
    for p in kp:
        if '백건 몸체' in p['name']:
            draw_poly(s, p, 'white')
    for p in kp:
        n = p['name']
        if '리프' in n and '#' not in n.split(' ')[0]:
            draw_poly(s, p, 'flex')
    for p in kp:
        if '흑건 몸체' in p['name']:
            draw_poly(s, p, 'black')
    for p in kp:
        n = p['name']
        if '리프' in n and '#' in n.split(' ')[0]:
            draw_poly(s, p, 'flexb')
    for p in kp:
        n = p['name']
        if '가이드 리브' in n or '앞 바닥판' in n:
            draw_poly(s, p, 'ghost')
    mags = []
    for p in kp:
        if '자석 포켓' in p['name']:
            cx, cy = center_of(p)
            mags.append((p['name'].split(' ')[0], cx, cy))
            s.circle(cx, cy, 2.5, 'mag')
    # 음이름(백건 헤드 안)
    for nm, x in (('C', 11.75), ('D', 35.25), ('E', 58.75), ('F', 82.25), ('G', 105.75), ('A', 129.25), ('B', 152.75)):
        s.text(x, 36, nm, 'ttlk')  # 흰 건반(고정색 #F4F2EC) 위: 테마와 무관한 어두운 글자
    for nm, x in (('C#', 21.2), ('D#', 49.3), ('F#', 90.6), ('G#', 117.5), ('A#', 144.4)):
        s.text(x, 104, nm, 'ttlw')
    # 기준선
    s.line((-6, 67), (170, 67), 'center')
    yc_w = center_of(next(p for p in items('white_key_side') if '순간 회전 중심' in p['name']))[0]  # 백건 리프 중심 y171.04
    yc_b = center_of(next(p for p in items('black_key_side') if '순간 회전 중심' in p['name']))[0]  # 흑건 y170.24(선은 백건 값)
    s.line((-6, yc_w), (170, yc_w), 'center')
    # 앞쪽 치수
    bounds = [0, 23.5, 47, 70.5, 94, 117.5, 141, 164.5]
    for a, b in zip(bounds, bounds[1:]):
        s.dim_h(a, b, 0, -26)
    s.dim_h(0.5, 23.0, 0, -54, '22.5 헤드 폭')
    s.dim_h(23.0, 24.0, 0, -54, '1.0 틈')
    s.dim_h(0, 164.5, 0, -82, '164.5 (옥타브 모듈 폭)')  # 전체 치수가 가장 바깥(보조선이 다른 치수선을 가로지르지 않게)
    s.dim_h(15.715, 26.715, 118, 0, '11.0', tcls='dimt dimt-inv')  # 흑건 면 위: 밝은 글자
    s.dim_h(43.785, 54.785, 118, 0, '11.0', tcls='dimt dimt-inv')
    s.dim_h(14.361, 15.715, 132, 0, '1.354', lab_side='left', tcls='dimt dimt-onw')  # 글자를 C 꼬리(흰 면) 위에: 고정 진한 파랑
    # 왼쪽 y 치수: 보조선은 재는 모서리에서, 치수선은 x=-10 기준 열(XL)에 그대로
    XL = -10
    c_body = next(p for p in kp if p['name'].startswith('C 백건 몸체'))
    cs_body = next(p for p in kp if p['name'].startswith('C# 흑건 몸체'))
    xc0 = min(q[0] for q in c_body['points'])                                   # C 왼쪽 변 x0.5
    x_notch = min(q[0] for q in c_body['points'] if q[1] == 50)                 # C 노치 모서리 (14.36, 50)
    xcs0, vcs0 = min(q[0] for q in cs_body['points']), min(q[1] for q in cs_body['points'])  # C# 앞 모서리

    def dim_l(va, vb, off, lab, x2=None):
        s.dim_v(va, vb, xc0, off - (xc0 - XL) * s.s, lab, x2=x2)
    dim_l(0, 50, -24, '50 헤드', x2=x_notch)
    dim_l(0, vcs0, -50, f'{fmt(vcs0)} 흑건 앞', x2=xcs0)
    dim_l(0, 67, -76, '67 센서 열', x2=-6)          # 위 보조선 = y67 중심선 시작점
    dim_l(0, 146, -102, '146 건반 몸체')
    dim_l(146, 196, -24, '50 리프')
    dim_l(196, 209, -50, '13 척추')
    # 오른쪽 지시선(도면 밖 한 줄)
    L = 176
    s.leader_abs(164.5, 67, L, 67, '센서 소자 열 y67')
    s.leader_abs(157.6, 65.8, L, 58, '자석 Ø5×2 — 백건 y65.8')
    s.leader_abs(144.4, 64.2, L, 50, '자석 Ø5×2 — 흑건 y64.2')
    s.leader_abs(164.5, yc_w, L, yc_w, f'순간 회전 중심 y{yc_w:.1f} (백건) · 흑건 y{yc_b:.1f}')
    s.leader_abs(156.5, 185, L, 185, '백건 리프(실선) t2.6 · 폭 11→15')
    s.leader_abs(144.4, 160, L, 158, '흑건 리프(점선, z55.5 위층) t2.0 · 폭 11→18')
    s.leader_abs(164.0, 202.5, L, 202.5, '척추 y196~209 (콤 공통)')
    s.leader_abs(158.2, 20, L, 20, '가이드 리브·크로스바 (숨은선)')
    s.leader_abs(162.8, 6, L, 8, '앞 바닥판 (다운스톱 접촉면)')
    s.scalebar(50)
    return s.render('옥타브 모듈 건반 평면도', 'C~B 12건반 평면 치수, 단위 mm')


# ================================================================ 2·3. 측면도
def keybed_cls(name, black):
    n = name
    if '척추(설치' in n:
        return None
    # 흑건 도면에서는 백건 부품(이름에 '백건'이 있거나, '흑건' 없이 '훅'만 있는 백건 훅 펠트)을 흐리게
    other = ('흑건' in n) if not black else ('백건' in n or ('훅' in n and '흑건' not in n))
    if black and '앞 가림판' in n:  # 가림판은 흑건 중심 ±6.5가 z56.5까지 트여 있어 이 단면에는 없다 → 뒤에 보이는 모서리만
        return 'faint'
    if other and any(w in n for w in ('홀센서', '스톱 펠트', '탭', '훅 펠트')):
        return 'faint'
    if not black and ('흑건' in n and ('레일' in n)):
        return 'faint'
    for k, c in (('시트', 'rubber'), ('펠트', 'pad'), ('센서 기판', 'pcb'), ('제어 기판', 'pcb'),
                 ('홀센서', 'sensor'), ('RP2040', 'pcb'), ('4067', 'pcb'), ('USB-C', 'part'),
                 ('철 원판', 'part'), ('인서트', 'part'), ('세트스크루', 'part'), ('x기준 핀', 'part'),
                 ('뒤 커버', 'part'), ('센서 바 흑건 구간', 'thin')):
        if k in n:
            return c
    return 'fixed'


def key_cls(name, black):
    if name.startswith(('백건 리프', '흑건 리프')):
        return 'flex'
    if '자석 Ø5' in name:
        return 'mag'
    if '포켓' in name:
        return 'hole'
    if '순간 회전 중심' in name:
        return None
    if any(w in name for w in ('척추', '세트스크루', '릿지', '클램프')):
        return 'part'
    if '보이는 부분 경계' in name or '노치면' in name:
        return 'thin'
    if any(w in name for w in ('보스', '가이드', '퍼티')):
        return 'ghostfill'
    if '외곽' in name:
        return 'black' if black else 'white'
    return 'inner'


SIDE_S = 4.2  # 측면도 배율(px/mm)


def _front_wall_follow_slope(wall, body):
    """흑건 '앞벽' 사각형을 외곽 앞면(z_f 위로 1.0 경사)을 따르도록 다시 만든다."""
    bp = body['points']
    fx = min(q[0] for q in bp)
    zf = max(q[1] for q in bp if q[0] == fx)
    zt = max(q[1] for q in bp)
    xt = min(q[0] for q in bp if q[1] == zt)
    wx0, wx1 = min(q[0] for q in wall['points']), max(q[0] for q in wall['points'])
    wz0, wz1 = min(q[1] for q in wall['points']), max(q[1] for q in wall['points'])
    th = wx1 - wx0

    def xf(z):
        return fx if z <= zf else fx + (z - zf) * (xt - fx) / (zt - zf)
    return dict(wall, points=[(fx, wz0), (fx + th, wz0), (fx + th, zf), (xf(wz1) + th, wz1), (xf(wz1), wz1), (fx, zf)])


def _post_on_spine(post, spine):
    """뒤 커버 받침 기둥의 밑면을 흑건 척추 윗면(기울기 10.76°)에 맞춘다. 모델 점은 수평 밑면이라 앞쪽이 척추에 묻히고 뒤쪽이 뜬다."""
    xs = [q[0] for q in post['points']]
    x0, x1, zt = min(xs), max(xs), max(q[1] for q in post['points'])
    return dict(post, points=[(x0, z_span_at(spine['points'], x0)[1]), (x1, z_span_at(spine['points'], x1)[1]), (x1, zt), (x0, zt)])


def side_view(black):
    key = 'black_key_side' if black else 'white_key_side'
    kb = items('keybed_side')
    kps = items(key)

    def kb_(pre):
        return next(p for p in kb if p['name'].startswith(pre))

    def kp_(sub):
        return next(p for p in kps if sub in p['name'])

    def zmax(p):
        return max(q[1] for q in p['points'])

    def xmax(p):
        return max(q[0] for q in p['points'])

    c = center_of(kp_('순간 회전 중심'))
    ang = 4.623 if black else 3.35
    body = kp_('외곽')
    wbody = next(p for p in items('white_key_side') if '외곽' in p['name'])
    mag = kp_('자석 Ø5')
    mx, mz = center_of(mag)
    zm = min(q[1] for q in mag['points'])  # 건반 밑면 = 자석면
    sen = next(p for p in kb if '홀센서' in p['name'] and (('흑건' in p['name']) == black))
    ze = float(re.search(r'소자 z([\d.]+)', sen['note']).group(1))
    tab = kb_('흑건 가이드 탭' if black else '백건 가이드 탭')
    felt = kb_('흑건 훅 펠트' if black else '훅 펠트 3T')
    fcx, fz = center_of(felt)[0], zmax(felt)
    usb = next(p for p in kb if 'USB-C' in p['name'])
    xw = xmax(kb_('뒷벽'))                                  # 프레임 뒷면 212
    xr = max(q[0] for p in kb for q in p['points'])          # 뒤로 가장 튀어나온 것(USB-C 플러그 끝)
    # 아래 치수열(y 방향)과 그 아래 지시선 글자 행
    # (x, 글자, 재는 부분의 높이 — 보조선이 그 부분에서 내려온다; None이면 바닥)
    xk = xmax(body)                                        # 건반 몸체 뒤끝 146
    zk = min(q[1] for q in body['points'] if q[0] == xk)   # 그 아래 모서리 z23.5
    if black:
        bot = [(mx, f'{fmt(mx)} 자석', zm), (center_of(sen)[0], f'{fmt(center_of(sen)[0])} 센서 소자', ze),
               (c[0], f'{c[0]:.2f} 순간 회전 중심', c[1])]
    else:
        bot = [(mx, f'{fmt(mx)} 자석', zm), (center_of(sen)[0], f'{fmt(center_of(sen)[0])} 센서 소자', ze),
               (xk, f'{fmt(xk)} 건반 몸체', zk), (c[0], f'{c[0]:.2f} 순간 회전 중심', c[1]),
               (xmax(kb_('프레임 바닥판')), f'{fmt(xmax(kb_("프레임 바닥판")))} 프레임 깊이', None)]
    rows = [-18 - 22 * i for i in range(len(bot))]
    lab1 = min(-30, (rows[-1] - 14) / SIDE_S)
    lab2 = lab1 - 16 / SIDE_S
    s = SVG(-12, min(-34, (lab1 if black else lab2) - 8 / SIDE_S), 240, 82, scale=SIDE_S, pad=(40, 30, 60, 30))
    spine_b = kb_('흑건 척추(설치')
    for p in kb:
        cls = keybed_cls(p['name'], black)
        if cls:
            if p['name'].startswith('뒤 커버 받침 기둥'):
                p = _post_on_spine(p, spine_b)
            draw_poly(s, p, cls)
    for p in kb:
        if '척추(설치' in p['name']:
            draw_poly(s, p, 'part' if (('흑건' in p['name']) == black) else 'faint')
    draw_poly(s, usb, 'ghostfill')  # 척추 레일·뒷벽을 지나는 플러그 몰드(숨은선)
    if black:
        draw_poly(s, wbody, 'faint')  # 이웃 백건 실루엣(치수 기준)
    else:
        clamp = next(p for p in items('black_key_side') if '클램프 나사 축' in p['name'])
    for p in sorted(kps, key=lambda p: 0 if '외곽' in p['name'] else 1):
        cls = key_cls(p['name'], black)
        if cls:
            if black and p['name'].startswith('앞벽'):
                p = _front_wall_follow_slope(p, body)
            draw_poly(s, p, cls)
    draw_poly(s, tab, 'ghostfill')              # 건반 몸체에 가려진 탭·훅(숨은선)
    draw_poly(s, felt, keybed_cls(felt['name'], black))
    if not black:
        draw_poly(s, clamp, 'part')  # 척추를 관통하는 축이 백건 척추 채움에 가려지지 않게 나중에 그린다
    for p in kps:
        n = p['name']
        if '외곽' in n or '자석 Ø5' in n:
            s.poly(rot([tuple(q) for q in p['points']], c, ang), 'ghost', True)
    s.line((c[0] - 4, c[1]), (c[0] + 4, c[1]), 'thin')
    s.line((c[0], c[1] - 4), (c[0], c[1] + 4), 'thin')
    s.circle(c[0], c[1], 0.9, 'dot')
    top_row, top_row2 = 74, 66.5
    # 윗면 앞 모서리와 끝까지 눌렀을 때 그 모서리 높이(딥)
    bp = body['points']
    zt = max(q[1] for q in bp)
    xt = min(q[0] for q in bp if q[1] == zt)
    zp = rot([(xt, zt)], c, ang)[0][1]
    for (x, lab, zf_), off in zip(bot, rows):
        s.dim_h(0, x, 0, off, lab, vb=zf_)
    # 오른쪽 높이 치수: 뒤로 튀어나온 플러그 몰드 바깥에서 시작
    o0 = (xr - xw) * s.s + 16
    # (높이, 글자, 위 보조선이 시작하는 모서리 x — None이면 프레임 뒷면)
    rights = [(zmax(kb_('바닥 고무 시트')), '{} ', None), (zm, '{} 건반 밑면' if not black else '{} 밑면', xk),
              (zmax(wbody), '{} 백건 윗면', xmax(wbody)), (zmax(kb_('뒷벽')), '{} 프레임', None),
              (zmax(kb_('뒤 커버 윗판')), '{} 커버', None)]
    if black:
        rights = rights[1:3] + [(zmax(body), '{} 흑건 윗면', xk)]
    for i, (z, lab, x2) in enumerate(rights, start=1 if black else 0):
        s.dim_v(0, z, xw, o0 + 24 * i, lab.format(fmt(z)).strip(), x2=x2)
    # 센서 소자 ~ 자석면
    xa = max(q[0] for q in sen['points'] + mag['points'])
    s.dim_v(ze, zm, xa, 20, f'{zm - ze:.2f}', hlab=True)  # 누른 건반 점선이 지나는 띠를 피해 눕힌 글자
    # 리프: 뿌리(몸체 뒤끝) 윗면과 끝(척추 앞) 윗면 높이 — 위 치수 줄의 보조선이 여기서 올라간다
    leaf = next(p for p in kps if p['name'].startswith(('백건 리프', '흑건 리프')))
    xl = xmax(leaf)
    zl0 = max(q[1] for q in leaf['points'] if q[0] == xk)
    zl1 = max(q[1] for q in leaf['points'] if q[0] == xl)
    zw = zmax(kb_('뒷벽'))
    zc = zmax(kb_('뒤 커버 윗판'))                           # 위 치수 줄 기준 높이(커버 윗면)
    lf_x = 160                                             # 리프 지시선 점의 x(두께 가운데)
    lf_z = sum(z_span_at(leaf['points'], lf_x)) / 2
    if not black:
        ins = kp_('세트스크루 인서트')
        xs1 = xmax(kp_('척추(설치'))                        # 척추 뒤끝 209
        m35 = re.search(r'M3×\d+', clamp['name']).group(0)
        rail = kb_('앞 레일')
        s.dim_h(0, 50, 43.5, 22, '50 헤드')
        s.dim_h(xk, xl, zc, 20, f'{fmt(xl - xk)} 리프', va=zl0, vb=zl1)
        s.dim_h(xl, xs1, zc, 20, fmt(xs1 - xl), va=zl1, vb=zw)
        s.dim_h(xs1, xw, zc, 20, fmt(xw - xs1), va=zw, vb=zw)
        s.dim_v(zp, zt, xt, -22, f'딥 {zt - zp:.1f}')
        s.leader_abs(fcx, fz, 0, top_row, f'업스톱: 훅 아랫면 z{fmt(fz)} + 펠트 3T', 'start')
        s.leader_abs(mx, mz, 62, top_row2, f'자석 Ø5×2 N35 (S극 아래, 면 z{fmt(zm)})', 'start')
        s.leader_abs(lf_x, lf_z, 118, top_row2, '리프 t2.6 (정지 시 휜 모양, 예하중 8.61°)', 'start')
        s.leader_abs(center_of(ins)[0], zmax(ins), 186, top_row, f'척추 · 세트스크루 · {m35} 클램프', 'start')
        s.leader_abs(6, 12.5, -10, lab1, '다운스톱: 앞 펠트 3T', 'start')
        s.leader_abs(center_of(sen)[0], ze, 40, lab1, f'홀센서 DRV5055A2 (소자 z{ze:.2f})', 'start')
        s.leader_abs(141, 20.5, 118, lab1, '뒤 스톱(두 번째 바닥) 펠트 1T', 'start')
        s.leader_abs(180, 10.6, 176, lab2, '제어 기판 + 4067 + RP2040-Zero', 'start')
        s.leader_abs(*center_of(usb), 206, lab1, 'USB-C 터널', 'start')
        s.leader_abs(center_of(rail)[0], center_of(kb_('바닥 고무 시트'))[1], 40, lab2, '바닥 EVA 3T', 'start')
        s.text(-10, 30, '앞', 'ttl', 'end', dx=-2)
    else:
        fx, bx = min(q[0] for q in bp), max(q[0] for q in bp)
        zf = max(q[1] for q in bp if q[0] == fx)
        off = (zt - zf) * s.s + 22
        s.dim_h(0, fx, zf, off, fmt(fx))
        s.dim_h(fx, bx, zf, off, f'{fmt(bx - fx)} 흑건 몸체')
        s.dim_h(xk, xl, zc, 20, f'{fmt(xl - xk)} 리프', va=zl0, vb=zl1)
        s.dim_v(zf, zt, fx, -22, f'{zt - zf:.1f}', x2=xt)
        s.dim_v(zp, zt, xt, -52, f'딥 {zt - zp:.1f}')
        s.leader_abs(fcx, fz, fcx, top_row, f'업스톱: 흑건 훅 z{fmt(fz)} + 펠트 3T', 'start')
        s.leader_abs(mx, mz, mx, top_row2, f'자석 Ø5×2 (흑건 y{fmt(mx)})', 'end')
        s.leader_abs(lf_x, lf_z, 150, top_row, '리프 t2.0 · 폭 11→18 (예하중 10.76°)', 'start')
        s.leader_abs(*center_of(kb_('흑건 스톱 펠트')), 36, lab1, '흑건 스톱 펠트 3T', 'start')
        s.leader_abs(center_of(sen)[0], ze, 76, lab1, f'홀센서 (소자 z{ze:.2f}, 센서 바 낮은 구간)', 'start')
        s.leader_abs(86, 20, 150, lab1, '흑건 가이드 탭 (슬롯 8.6)', 'start')
        s.text(-10, 30, '앞', 'ttl', 'end', dx=-2)
    s.scalebar(20)
    t = '흑건(C#) 측면 단면도' if black else '백건(D) 측면 단면도'
    return s.render(t, '정지 상태 실선, 끝까지 누른 상태 점선. 단위 mm')


# ================================================================ 4. 모듈 프레임 평면도
def module_plan():
    s = SVG(-10, -16, 182, 220, scale=3.1, pad=(120, 60, 360, 60))
    for p in items('module_plan'):
        n = p['name']
        if '외곽' in n:
            cls = 'fixed'
        elif '시트' in n or '경량화' in n:
            cls = 'thin'
        elif '펠트' in n:
            cls = 'pad'
        elif any(w in n for w in ('센서 기판', '제어 기판', 'RP2040', '4067', 'EXT')):
            cls = 'pcb'
        elif '센서 포켓' in n or '소자 열' in n:
            cls = 'sensor'
        elif '센서 바' in n and '낮은' in n:
            cls = 'thin'
        elif '센서 바' in n and '기둥' not in n and '턱' not in n:
            cls = 'part'
        elif any(w in n for w in ('인서트', '원판', '핀')):
            cls = 'hole'
        elif '도브테일' in n:
            cls = 'flex'
        elif any(w in n for w in ('리본', '터널', '케이블')):
            cls = 'ghost'
        else:
            cls = 'part'
        draw_poly(s, p, cls)
    mp = items('module_plan')

    def mp_(pre):
        return next(p for p in mp if p['name'].startswith(pre))

    def bbox(p):
        xs, ys = [q[0] for q in p['points']], [q[1] for q in p['points']]
        return min(xs), min(ys), max(xs), max(ys)
    fv1 = bbox(mp_('프레임 외곽'))[3]                  # 212
    bx0, by0, bx1, by1 = bbox(mp_('제어 기판'))         # 47.25~117.25 × 145.5~195.5
    ux0, _, ux1, uy1 = bbox(mp_('USB 터널'))            # 74~94, 뒷벽 앞면 y209까지
    usb_t = mp_('USB 터널')
    s.rect(ux0, uy1, ux1 - ux0, fv1 - uy1, 'ghost', usb_t.get('note') or '뒷벽 개구')  # 뒷벽 개구(숨은선)
    s.dim_h(0, 164.5, 0, -30, '164.5')
    s.dim_h(164.5, 168.5, 6.5, -60, '4')
    # 왼쪽 y 치수: 보조선은 각 부품 왼쪽 모서리에서, 치수선은 x=-10 기준 열(XL)에 그대로
    XL = -10

    def dim_l(pre, off, suffix=''):
        x0_, v0_, _, v1_ = bbox(mp_(pre))
        s.dim_v(v0_, v1_, x0_, off - (x0_ - XL) * s.s, f'{fmt(v1_ - v0_)}{suffix}')
    dim_l('프레임 외곽', -56, ' 프레임 깊이')  # 전체 치수가 바깥 열(부품 치수 보조선이 212 치수선을 가로지르지 않게)
    for pre in ('앞 레일', '센서 바 왼쪽 받침 기둥', '뒤 스톱 레일', '척추 레일'):  # 27 · 18.5 · 6 · 13
        dim_l(pre, -30)
    # 제어 기판: 깊이는 기판 왼쪽 모서리에서, 폭은 뒷벽 너머(USB 터널 치수 한 줄 위)로
    USB_OFF = 24
    s.dim_v(by0, by1, bx0, -20, f'{fmt(by1 - by0)} 제어 기판')
    s.dim_h(bx0, bx1, by1, (fv1 - by1) * s.s + USB_OFF + 20, f'{fmt(bx1 - bx0)} 제어 기판')
    s.dim_h(ux0, ux1, fv1, USB_OFF, f'{fmt(ux1 - ux0)} USB 터널')
    s.dim_h(60, 82, 110, 0, '22 리본 차선')
    L = 182
    # 오른쪽 위 지시선 글자 행: 도브테일(뒤) 아래 꼭짓점과 4067 행 사이를 4등분
    dv0 = bbox(mp_('도브테일 수(뒤'))[1]               # 198
    LV_4067 = 170
    step = (dv0 - LV_4067) / 4
    lv_ins, lv_disc, lv_rp = dv0 - step, dv0 - 2 * step, dv0 - 3 * step
    ins = [p for p in mp if p['name'].startswith('클램프 인서트')]
    ins_x = sorted(center_of(p)[0] for p in ins)
    ins_last = max(ins, key=lambda p: center_of(p)[0])
    disc = max((p for p in mp if '원판' in p['name']), key=lambda p: center_of(p)[0])
    rp = mp_('RP2040')
    mux = mp_('4067')
    ext = mp_('EXT')
    s.leader_abs(168.5, 202.5, L, 214, '도브테일 수(뒤) 뿌리 6·끝 9·깊이 4, 높이 14')
    s.leader_abs(*center_of(ins_last), L, lv_ins, f'클램프 인서트 M3 ×{len(ins)} (x{" · ".join(fmt(x) for x in ins_x)})')
    s.leader_abs(*center_of(disc), L, lv_disc, '철 원판 Ø8×1 (세트스크루 받침)')
    s.leader_abs(bbox(rp)[2], center_of(rp)[1], L, lv_rp, 'RP2040-Zero (USB-C → 뒤, 직접 납땜)')
    s.leader_abs(bbox(mux)[2], center_of(mux)[1], L, LV_4067, '4067 먹스 (C0~C11 센서, C12~15 EXT)')
    s.leader_abs(bbox(ext)[2], center_of(ext)[1], L, 160, 'EXT 패드 6개 (끝 부속용)')
    s.leader_abs(164.5, 141, L, 141, '뒤 스톱 레일 (두 번째 바닥)')
    s.leader_abs(156, 116, L, 116, '바닥 경량화 창')
    s.leader_abs(162.9, 75, L, 84, '센서 기판 (6행 만능기판)')
    s.leader_abs(160, 67, L, 70, '센서 포켓 12개 (소자 y67)')
    s.leader_abs(164.5, 55, L, 55, '흑건 스톱 레일 + 펠트 3T')
    s.leader_abs(156.9, 20, L, 28, '백건 가이드 탭 + 훅 ×7')
    s.leader_abs(168.5, 11, L, 12, '도브테일 수(앞) 높이 5.5')
    s.leader_abs(164, 6, L, 2, '백건 앞 스톱 펠트 3T')
    s.scalebar(50)
    return s.render('옥타브 모듈 프레임 평면도', '키베드 프레임과 부착 부품, 단위 mm')


# ================================================================ 5. 전체 배치도
def assembly():
    s = SVG(-40, -440, 1260, 640, scale=0.62, pad=(60, 30, 60, 40))
    for p in items('assembly_plan'):
        n = p['name']
        if '페달 3개' in n:  # R24: 페달은 댐퍼 하나(듀로 스위치 페달 76×240 개조)
            p = dict(p, name='댐퍼 페달 1개(바닥, 책상 앞)', points=[[640, -400], [716, -400], [716, -160], [640, -160]],
                     note='듀로 스위치 페달 홀센서 개조 → CU 3.5 mm 잭(PJ-313)')
            n = p['name']
        if 'USB 케이블' in n or 'EXT 선' in n:
            cls = 'thin'
        elif '모듈 O' in n or ('끝 부속' in n and '선' not in n):
            cls = 'part'
        elif 'A#0' in n:
            cls = 'black'
        elif '건반' in n:
            cls = 'white'
        elif '스피커' in n or '서브' in n:
            cls = 'spk'
        elif 'CU' in n:
            cls = 'pcb'
        elif '케이블 공간' in n:
            cls = 'zone'
        elif '센서 열' in n:
            cls = 'center'
        elif '브래킷' in n:
            cls = 'flex'
        else:
            cls = 'part'
        draw_poly(s, p, cls)
    for k in range(7):
        s.text(47 + 164.5 * k + 82.25, 100, f'O{k + 1}', 'ttl')
    s.text(23, 180, 'L', 'ttl')
    s.text(1218, 180, 'R', 'ttl')
    s.dim_h(-16, 1238, 474, 24, '1254 전체 폭 (볼 포함)')
    s.dim_h(0, 1222, 0, -24, '1222 (88건반)')
    s.dim_h(-16, 47, 0, -50, '63')
    s.dim_h(47, 211.5, 0, -50, '164.5')
    s.dim_h(1198.5, 1238, 0, -50, '39.5')
    s.dim_v(0, 440, 1238, 24, '440 깊이')
    s.dim_v(0, 212, -16, -24, '212')
    s.leader_abs(74, 345, -30, 615, '스피커 CW-100B25 · 오꾸메 밀폐 4.7 L (센서까지 269, 도면 8)', 'start')
    s.leader_abs(620, 330, 330, 585, 'CU 상자: Pi 5 + USB 동글 + 앰프 XH-A232 + 허브 + PED (배선 도면 9)', 'start')
    s.leader_abs(1148, 345, 1000, 615, '스피커 (오른쪽)', 'start')
    s.leader_abs(400, 235, 60, 555, '뒤 케이블 공간 y212~250 (USB 8가닥)', 'start')
    s.leader_abs(716, -280, 780, -280, '댐퍼 페달 1개 (R24 · 듀로 개조 76×240)', 'start')
    s.scalebar(200)
    return s.render('전체 배치 평면도', 'A0 왼쪽 경계 x=0 기준, 단위 mm')


# ================================================================ 6. 리프 상세
def _ends(pts):
    """테이퍼 리프 폴리곤 → (끝단 y, 끝단 x들, 뿌리 y, 뿌리 x들). 끝단 = 건반 쪽(작은 y), 뿌리 = 척추 쪽."""
    vt, vr = min(q[1] for q in pts), max(q[1] for q in pts)
    return vt, sorted(q[0] for q in pts if q[1] == vt), vr, sorted(q[0] for q in pts if q[1] == vr)


def _edge_x(pts, side, v):
    """리프 왼쪽(side=0)/오른쪽(side=-1) 옆변의 높이 v에서의 x."""
    vt, tip, vr, root = _ends(pts)
    return tip[side] + (root[side] - tip[side]) * (v - vt) / (vr - vt)


def _fillet(c, a, b, r, n=10):
    """모서리 c(변 c→a, c→b 사이)의 반지름 r 필렛 호 점열: c→a 변 위 접점에서 c→b 변 위 접점까지."""
    ua = ((a[0] - c[0]), (a[1] - c[1]))
    ub = ((b[0] - c[0]), (b[1] - c[1]))
    la, lb = math.hypot(*ua), math.hypot(*ub)
    ua, ub = (ua[0] / la, ua[1] / la), (ub[0] / lb, ub[1] / lb)
    th = math.acos(ua[0] * ub[0] + ua[1] * ub[1])
    L = r / math.tan(th / 2)
    bis = (ua[0] + ub[0], ua[1] + ub[1])
    lbis = math.hypot(*bis)
    o = (c[0] + bis[0] / lbis * r / math.sin(th / 2), c[1] + bis[1] / lbis * r / math.sin(th / 2))
    ta, tb = (c[0] + ua[0] * L, c[1] + ua[1] * L), (c[0] + ub[0] * L, c[1] + ub[1] * L)
    a0 = math.atan2(ta[1] - o[1], ta[0] - o[0])
    a1 = math.atan2(tb[1] - o[1], tb[0] - o[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi  # 짧은 쪽 호
    return [(o[0] + r * math.cos(a0 + da * i / n), o[1] + r * math.sin(a0 + da * i / n)) for i in range(n + 1)]


def leaf_detail():
    kp = items('key_plan')
    d_leaf = next(p for p in kp if p['name'].startswith('D 리프'))
    ds_leaf = next(p for p in kp if p['name'].startswith('D# 리프'))
    d_body = next(p for p in kp if p['name'].startswith('D 백건 몸체'))
    spine = next(p for p in kp if p['name'].startswith('백건 척추'))
    r6 = next(d for d in F['dims'] if d['id'] == 'P72')['value']
    sv0 = min(q[1] for q in spine['points'])
    sv1 = max(q[1] for q in spine['points'])
    # 배치: D 건반 왼쪽 경계를 x0에, D# 리프는 D 리프 오른쪽에 나란히(실제는 z55.5 위층에서 겹친다)
    dx_d = -min(q[0] for q in d_body['points'])
    dx_b = -8  # 보기 좋게 옆으로 옮긴 배치 값(치수에는 쓰지 않음)
    dl = [(x + dx_d, y) for x, y in d_leaf['points']]
    bl = [(x + dx_b, y) for x, y in ds_leaf['points']]
    vtd, tipd, vrd, rootd = _ends(dl)
    vtb, tipb, vrb, rootb = _ends(bl)
    # 뿌리 네 모서리의 R 필렛(P72: 백 리프→척추 양쪽, 흑 리프→척추 양쪽). 척추 창은 필렛 접점 바깥 2 mm까지
    fil = {}
    for key, vt, tip, vr, root in (('d', vtd, tipd, vrd, rootd), ('b', vtb, tipb, vrb, rootb)):
        fil[key] = (_fillet((root[0], vr), (tip[0], vt), (root[0] - 1, vr), r6),
                    _fillet((root[-1], vr), (tip[-1], vt), (root[-1] + 1, vr), r6))
    fx = [q[0] for f in fil.values() for arc in f for q in arc]
    sx0, sx1 = min(fx) - 2, max(fx) + 2
    s = SVG(sx0 - 4, vtd - 8, sx1 + 6, sv1 + 5, scale=6.0, pad=(60, 40, 260, 60))
    s.rect(sx0, sv0, sx1 - sx0, sv1 - sv0, 'fixed', f'척추 y{sv0:g}~{sv1:g} (일부)')
    for key, (vt, tip, vr, root), cls, nm in (('d', (vtd, tipd, vrd, rootd), 'flex', 'D 리프'),
                                              ('b', (vtb, tipb, vrb, rootb), 'flexb2', 'D# 리프')):
        left, right = fil[key]
        outline = [(tip[0], vt), (tip[-1], vt)] + right + list(reversed(left))
        s.poly(outline, cls, True, f'{nm} (뿌리 필렛 R{r6:g})')
    # 필렛 전 직선 테이퍼(가상선): 뿌리 폭 치수의 보조선이 이 가상 교점에서 시작한다
    for vt, tip, vr, root in ((vtd, tipd, vrd, rootd), (vtb, tipb, vrb, rootb)):
        s.line((tip[0], vt), (root[0], vr), 'ghostfill')
        s.line((tip[-1], vt), (root[-1], vr), 'ghostfill')
    # 폭: 끝단(건반 쪽)과 뿌리(필렛 전 가상 교점) — 모두 폴리곤 꼭짓점에서
    off_root = (sv1 - sv0) * s.s + 14
    for vt, tip, vr, root in ((vtd, tipd, vrd, rootd), (vtb, tipb, vrb, rootb)):
        s.dim_h(tip[0], tip[-1], vt, -22, f'{tip[-1] - tip[0]:.1f}')
        s.dim_h(root[0], root[-1], vr, off_root, f'{root[-1] - root[0]:.1f}')
    # 길이·척추 폭: 왼쪽 빈 곳에 한 줄로
    s.dim_v(vtd, vrd, tipd[0], -((tipd[0] - sx0) * s.s + 16), x2=sx0)  # 뿌리 쪽 보조선은 척추 왼쪽 모서리(13과 공유)
    s.dim_v(sv0, sv1, sx0, -16)
    s.text(center_of({'points': dl})[0], 170, '백건', 'ttl')
    s.text(center_of({'points': dl})[0], 165, 't 2.6', 'lbl')
    s.text(center_of({'points': bl})[0], 170, '흑건', 'ttl')
    s.text(center_of({'points': bl})[0], 165, 't 2.0', 'lbl')
    lx = sx1 + 8
    s.leader_abs(sx1, (sv0 + sv1) / 2, lx, (sv0 + sv1) / 2, f'척추 (y{sv0:g}~{sv1:g})')
    arc = fil['b'][1]
    s.leader_abs(*arc[len(arc) // 2], lx, vrb - 6, f'평면 필렛 R{r6:g} (리프 → 척추, 백·흑)')
    s.text(lx, vrb - 6, 'E|F 경계 쪽 뿌리(틈 1.0)는 필렛 없음', 'lbl', 'start', dx=2, dy=3.5 + 13)  # 둘째 줄
    s.leader_abs(_edge_x(bl, -1, 180), 180, lx, 184, '폭은 굽힘 모멘트 분포에 맞춘 직선 테이퍼')
    s.leader_abs(rootb[-1], vrb, lx, vrb - 1.5, '뿌리 폭 = 필렛 전 가상 교점 사이 (점선)')
    s.leader_abs(_edge_x(bl, -1, 170) - 1, 170, lx, 176, '재료 PETG · 윗면을 베드에 대고 출력(첫 10~13층)')
    s.scalebar(10)
    return s.render('리프(테이퍼 판 플렉서) 상세', 'D·D# 리프 평면, 단위 mm')


# ================================================================ 7. 도브테일 상세
DT_GAP = 0.10  # 암 홈 한쪽 틈(면에 수직, 단계 0 쿠폰 0.05~0.15에서 선택)


def _groove(male, x_face, c):
    """수 도브테일(볼록 사각형, 한 변이 면 x=x_face 위) → 각 면을 바깥 법선으로 c만큼 띄운 암 홈. 입구는 x=x_face에서 끊는다."""
    n = len(male)
    area = sum(male[i][0] * male[(i + 1) % n][1] - male[(i + 1) % n][0] * male[i][1] for i in range(n)) / 2
    k = 1 if area > 0 else -1  # 반시계면 바깥 법선 = (dy, -dx)
    faces = []
    for i in range(n):
        (x1, v1), (x2, v2) = male[i], male[(i + 1) % n]
        if abs(x1 - x_face) < 1e-9 and abs(x2 - x_face) < 1e-9:
            continue  # 입구(면 위의 변)
        L = math.hypot(x2 - x1, v2 - v1)
        nx, nv = k * (v2 - v1) / L, -k * (x2 - x1) / L
        faces.append(((x1 + nx * c, v1 + nv * c), (x2 + nx * c, v2 + nv * c)))

    def cross(a, b):
        (p1, p2), (q1, q2) = a, b
        d1, d2 = (p2[0] - p1[0], p2[1] - p1[1]), (q2[0] - q1[0], q2[1] - q1[1])
        t = ((q1[0] - p1[0]) * d2[1] - (q1[1] - p1[1]) * d2[0]) / (d1[0] * d2[1] - d1[1] * d2[0])
        return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)
    mouth = ((x_face, 0.0), (x_face, 1.0))
    pts = [cross(faces[0], mouth)] + [cross(faces[i], faces[i + 1]) for i in range(len(faces) - 1)] + [cross(faces[-1], mouth)]
    return [[round(x, 3), round(v, 3)] for x, v in pts]


def _fit_grooves(F):
    """module_plan의 암 홈(앞·뒤, 왼쪽면)을 이웃 모듈 수 도브테일의 면 오프셋(한쪽 틈 DT_GAP)으로 다시 만든다.
    (꼭짓점을 ±0.1씩 옮긴 원래 값은 경사면 틈이 0.06~0.09라 라벨 0.10과 달랐다.)"""
    mp = F['module_plan']
    x_face = max(q[0] for q in next(p for p in mp if p['name'].startswith('프레임 외곽'))['points'])  # 164.5
    for i, p in enumerate(mp):
        for side in ('앞', '뒤'):
            if p['name'].startswith(f'도브테일 암({side}'):
                m = next(q for q in mp if q['name'].startswith(f'도브테일 수({side}'))
                male = [(x - x_face, v) for x, v in m['points']]
                mp[i] = dict(p, points=_groove(male, 0.0, DT_GAP))


_fit_grooves(F)


def dovetail_detail():
    s = SVG(-12, 0, 26, 22, scale=12.0, pad=(70, 50, 330, 60))
    mp = items('module_plan')
    m = next(p for p in mp if p['name'].startswith('도브테일 수(앞'))
    f = next(p for p in mp if p['name'].startswith('도브테일 암(앞'))
    x0m = min(q[0] for q in m['points'])                    # 모듈 오른쪽 면 x164.5 → 0
    male = [(x - x0m, v) for x, v in m['points']]
    female = [tuple(q) for q in f['points']]
    STUB = (-10, 1, 10, 20)                                  # 모듈 몸체 일부(그림용)
    s.rect(*STUB, 'fixed')
    s.poly(male, 'flex', True, '도브테일 수')
    s.poly(female, 'ghost', False, f'암 홈 (한쪽 틈 {DT_GAP:.2f})')  # 입구(x0)는 열려 있어 선을 긋지 않는다
    xr = max(q[0] for q in male)
    root = sorted(v for x, v in male if x == 0)
    tip = sorted(v for x, v in male if x == xr)
    s.dim_v(root[0], root[-1], 0, -((0 - STUB[0]) * s.s + 16), f'{fmt(root[-1] - root[0])} 뿌리')  # 몸체 밖 왼쪽
    s.dim_v(tip[0], tip[-1], xr, 36, f'{fmt(tip[-1] - tip[0])} 끝')
    s.dim_h(0, xr, tip[-1], 36, f'{fmt(xr)} 깊이')
    s.text(-5, 3, '모듈 오른쪽 면', 'lbl')
    fx1 = max(q[0] for q in female)
    s.leader_abs(fx1, max(q[1] for q in female), 12, 19, f'암 쪽 한쪽 틈 {DT_GAP:.2f} (쿠폰 0.05 / 0.10 / 0.15에서 선택)')
    s.leader_abs(xr / 2, 9.5, 12, 7.5, '높이: 앞 5.5 (z3.0~8.5), 뒤 14 (z3.0~17.0)')   # 점은 수 안, 글자 줄은 '9 끝' 아래로
    s.leader_abs(fx1, 7, 12, 4, '암 홈은 바닥까지 뚫려 있어 위에서 내려 끼운다')      # 점은 홈 끝면 위
    s.scalebar(5)
    return s.render('모듈 결합 도브테일 상세', '평면, 단위 mm')


# ================================================================ 8. 스피커 상자(R25)
def spk_box():
    """정면(배플) + 중앙 단면 + 오꾸메 400×1200 재단도. 외형 180×190×210, 판 11.5T."""
    T = 11.5
    s = SVG(-20, -26, 500, 222, scale=1.45, pad=(240, 44, 300, 44))
    # --- 정면(연주자 쪽에서 본 배플) x0~180
    s.rect(0, 0, T, 210, 'fixed', '옆판(왼쪽) 끝면')
    s.rect(180 - T, 0, T, 210, 'fixed', '옆판(오른쪽) 끝면')
    s.rect(T, 0, 180 - 2 * T, 210, 'fixed', '앞판(배플) 157×210')
    s.rect(37.5, 67.5, 105, 105, 'ghostfill', '유닛 프레임 105×105')
    s.rect(25, 55, 130, 130, 'ghost', 'PETG 육각 그릴 130×130')
    s.circle(90, 120, 47, 'hole')
    for dx in (-40.66, 40.66):
        for dv in (-40.66, 40.66):
            s.circle(90 + dx, 120 + dv, 2.4, 'hole')
    for gx in (33, 147):
        for gv in (63, 177):
            s.circle(gx, gv, 2.1, 'part')
    s.line((90, 58), (90, 182), 'center')
    s.line((28, 120), (152, 120), 'center')
    for fx in (16, 136):
        s.poly([(fx, -18), (fx + 28, -18), (fx + 24, 0), (fx + 4, 0)], 'rubber', True, '고무발 L14')
    s.dim_h(0, 180, 210, 22, '180')
    s.dim_h(T, 180 - T, 210, 42, '157 앞판')
    s.dim_v(0, 210, 0, -28, '210')
    s.dim_v(0, 120, 180, 18, '120')
    s.dim_h(25, 155, 185, 12, '130 그릴')
    s.leader_abs(90 - 33.2, 120 + 33.2, -22, 196, '컷아웃 Ø94 (받은 뒤 바스켓 지름으로 확인)', 'end')
    s.leader_abs(90 - 40.66, 120 - 40.66, -22, 80, '장공 4-Ø4.8 · PCD 115 (45°) · 피스 16 mm', 'end')
    s.leader_abs(33, 177, -22, 160, '그릴 고정 4곳 · 직결피스 19 mm', 'end')
    s.leader_abs(20, -10, -22, 20, '고무발 4개 (L14, 25 mm 피스)', 'end')
    s.text(90, -24, '정면 (배플, 연주자 쪽)', 'ttl')
    # --- 중앙 단면 (왼쪽이 배플, x = 300 + 깊이 y)
    o = 300
    s.rect(o, 0, 190, 210, 'faint')
    s.rect(o, 0, T, 210, 'fixed', '앞판(배플)')
    s.rect(o + 190 - T, 0, T, 210, 'fixed', '뒤판')
    s.rect(o + T, 210 - T, 190 - 2 * T, T, 'fixed', '윗판 157×167')
    s.rect(o + T, 0, 190 - 2 * T, T, 'fixed', '아랫판 157×167')
    s.rect(o + 150, T, 190 - T - 150, 210 - 2 * T, 'ghostfill', '흡음솜 40~60 g')
    s.rect(o - 3, 67.5, 3, 105, 'pad', 'EVA 가스켓 3T')
    s.rect(o - 7, 67.5, 4, 105, 'part', '유닛 플랜지')
    s.poly([(o, 73), (o, 167), (o + 37, 142), (o + 37, 98)], 'spk', True, '유닛 바스켓·콘')
    s.rect(o + 37, 77.5, 17, 85, 'black', '자석 280 g')
    s.rect(o - 19, 55, 2, 130, 'flex', '그릴 면')
    s.rect(o - 17, 55, 10, 5, 'flex', '스페이서 링')
    s.rect(o - 17, 180, 10, 5, 'flex', '스페이서 링')
    s.rect(o + 190, 40, 5, 34, 'pcb', '단자 L11')
    for fx in (o + 12, o + 150):
        s.poly([(fx, -18), (fx + 28, -18), (fx + 24, 0), (fx + 4, 0)], 'rubber', True, '고무발 L14')
    s.dim_h(o, o + 190, 210, 22, '190')
    s.dim_h(o + T, o + 190 - T, 150, 0, '167 내부')
    s.dim_v(T, 210 - T, o + 120, 0, '187 내부')
    s.dim_h(o - 7, o + 54, 30, -14, '61 유닛 깊이')
    s.dim_h(o, o + T, 210, 44, '11.5')
    s.leader_abs(o + 195, 57, o + 214, 57, '뒤판 단자 L11 (선을 뽑아 분리, R18)', 'start')
    s.leader_abs(o + 170, 150, o + 214, 150, '흡음솜 40~60 g (L12, 느슨하게)', 'start')
    s.leader_abs(o + 100, 190, o + 214, 196, '내부 157×167×187 = 4.9 L (유닛·솜 빼면 약 4.7 L)', 'start')
    s.leader_abs(o - 2, 100, o + 214, 110, 'EVA 가스켓 3T (L41 자투리) + 목공본드로 밀폐', 'start')
    s.leader_abs(o - 18, 70, o + 214, 76, 'PETG 육각 그릴 + 스페이서 링 10 (개구율 약 72%)', 'start')
    s.text(o + 95, -24, '중앙 단면 (왼쪽이 연주자 쪽)', 'ttl')
    s.scalebar(50)
    top = s.render('스피커 상자 정면·단면', '오꾸메 11.5T 밀폐 상자, CW-100B25, 단위 mm')
    # --- 재단도 (두 번째 SVG, 화살표 marker id를 따로)
    c = SVG(0, 0, 1200, 400, scale=0.58, pad=(70, 40, 40, 40))
    c.rect(0, 0, 1200, 400, 'faint')
    x = 0
    for i in range(4):
        c.rect(x, 190, 190, 210, 'fixed', '옆판 190×210')
        c.text(x + 95, 300, '옆판', 'lbl')
        c.text(x + 95, 282, '190×210', 'dimt')
        x += 193
    for lab in ('앞판(배플)', '앞판(배플)'):
        c.rect(x, 190, 157, 210, 'flexb2', lab + ' 157×210')
        c.text(x + 78.5, 300, lab, 'lbl')
        c.text(x + 78.5, 282, '157×210', 'dimt')
        x += 160
    c.text((x + 1200) / 2, 295, '남음', 'lbl')
    x = 0
    for lab in ('뒤판', '뒤판'):
        c.rect(x, 30, 210, 157, 'fixed', lab + ' 157×210')
        c.text(x + 105, 112, lab, 'lbl')
        c.text(x + 105, 94, '210×157', 'dimt')
        x += 213
    for i in range(4):
        c.rect(x, 30, 167, 157, 'fixed', '위·아래판 157×167')
        c.text(x + 83.5, 112, '위·아래판', 'lbl')
        c.text(x + 83.5, 94, '167×157', 'dimt')
        x += 170
    c.text((x + 1200) / 2, 105, '남음', 'lbl')
    c.text(600, 12, '남는 띠 약 30', 'lbl')
    c.dim_h(0, 1200, 400, 18, '1200')
    c.dim_v(0, 400, 1200, 20, '400')
    c.dim_v(190, 400, 0, -26, '210 띠')
    c.dim_v(30, 187, 0, -26, '157 띠')
    c.scalebar(200)
    cut = c.render('오꾸메 400×1200 재단도', '톱날 3 mm 포함, 상자 2개분 12장, 단위 mm')
    cut = cut.replace('id="arr"', 'id="arr2"').replace('url(#arr)', 'url(#arr2)')
    return top + '<p class="mut small" style="margin:10px 4px 4px">아래: 오꾸메 400×1200 한 장의 재단도(주문할 때 함께 보낸다). 앞판 2장에 컷아웃, 뒤판 2장에 단자 구멍을 뚫는다.</p>' + cut


# ================================================================ 9. 오디오 배선(R25)
def audio_wiring():
    s = SVG(0, 0, 1060, 440, scale=0.86, pad=(20, 30, 20, 40))

    def box(x, v, w, h, title, sub='', cls='part'):
        s.rect(x, v, w, h, cls, title)
        s.text(x + w / 2, v + h - 16, title, 'ttl')
        if sub:
            for i, line in enumerate(sub.split('\n')):
                s.text(x + w / 2, v + h - 36 - 17 * i, line, 'lbl')

    def wire(pts, lab=None, at=0.5, dv=8, cls='lead'):
        s.poly(pts, cls, False)
        if lab:
            (x1, v1), (x2, v2) = pts[0], pts[-1]
            s.text(x1 + (x2 - x1) * at, v1 + (v2 - v1) * at + dv, lab, 'lbl')

    box(20, 200, 150, 110, 'Pi 5 (L01)', 'FluidSynth\nhw:<동글>,0 48 kHz', 'pcb')
    box(230, 215, 130, 80, 'USB 동글 (L51)', 'DAC + 헤드폰 앰프')
    box(430, 150, 140, 190, 'PJ-313 (L15)', '왼쪽 볼 헤드폰 잭', 'part')
    for v, lab in ((290, 'T (L)'), (262, 'R (R)'), (234, 'S (GND)')):
        s.text(436, v, lab, 'lbl', 'start')
    for v, lab in ((200, 'TN'), (178, 'RN')):
        s.text(564, v, lab, 'lbl', 'end')
    box(620, 150, 120, 150, '저음 차단 RC', '1 µF×2 직렬 (L56)\n1 kΩ → GND (L29)\nfc ≈ 80 Hz', 'flexb2')
    box(790, 140, 130, 200, 'XH-A232 (L53)', 'TPA3110 · 19 V\n8 Ω 약 19 W/ch\nBTL: −선 GND 금지', 'pcb')
    box(960, 245, 90, 70, 'L 스피커', 'CW-100B25', 'spk')
    box(960, 145, 90, 70, 'R 스피커', 'CW-100B25', 'spk')
    box(20, 385, 150, 45, 'PD 5.1 V 5 A (L55)', '', 'fixed')
    box(790, 398, 130, 36, '19 V 3.42 A (L06)', '', 'fixed')
    box(790, 358, 130, 28, 'DC 잭 (L54)', '', 'fixed')
    box(20, 40, 150, 110, 'USB 허브 (L17)', '모듈 O1~O7 · PED\nUSB 8가닥', 'part')
    wire([(170, 255), (230, 255)], '젠더 L52', 0.5, 8)
    s.text(295, 200, 'Pi에 직결(허브 경유 금지)', 'dimt')
    wire([(360, 255), (430, 255)], '선 ① C14', 0.5, 8)
    wire([(570, 200), (620, 200)], 'L', 0.5, 6)
    wire([(570, 178), (620, 178)], 'R', 0.5, 6)
    wire([(500, 150), (500, 120), (680, 120), (680, 150)], '선 ② C14: L·R + GND(슬리브)', 0.5, -18)
    wire([(740, 200), (790, 200)], 'IN L', 0.5, 6)
    wire([(740, 178), (790, 178)], 'IN R', 0.5, -14)
    wire([(680, 120), (855, 120), (855, 140)], None)
    s.text(870, 128, 'IN G', 'lbl', 'start')
    wire([(920, 280), (960, 280)], 'L±', 0.5, 6)
    wire([(920, 180), (960, 180)], 'R±', 0.5, 6)
    s.text(1050, 110, '스피커선 C13 → 상자 단자 L11', 'lbl', 'end')
    wire([(95, 385), (95, 310)], None)
    s.text(103, 345, 'USB-C', 'lbl', 'start')
    wire([(855, 398), (855, 386)], None)
    wire([(855, 358), (855, 340)], None)
    s.text(862, 345, 'VCC·GND', 'lbl', 'start')
    wire([(95, 150), (95, 200)], None)
    s.text(103, 172, 'USB-A', 'lbl', 'start')
    s.text(500, 95, '헤드폰을 꽂으면 TN·RN 접점이 떨어져 앰프 입력이 끊긴다(R15)', 'lbl')
    s.text(500, 75, '−6 dB가 필요하면 채널마다 1 µF 하나를 1 kΩ 직렬로 바꾼다(fc 그대로)', 'lbl')
    s.text(500, 55, '켤 때 Pi 먼저, 앰프 나중 · 핀 배치는 플러그를 꽂았다 빼며 멀티미터로 확인', 'lbl')
    return s.render('오디오 배선도', 'Pi 5 → USB 동글 → 헤드폰 잭 노멀 접점 → RC → 앰프 → 스피커 2개, 전원 3개')


OUT = {
    'octave_plan': octave_plan(),
    'white_side': side_view(False),
    'black_side': side_view(True),
    'module_plan': module_plan(),
    'assembly': assembly_r26(items, draw_poly),
    'leaf': leaf_detail(),
    'dovetail': dovetail_detail(),
    'spk_box': spk_box_r26(),
    'audio_wiring': audio_wiring_r26(items),
    'rear_bar': rear_bar_r26(items, draw_poly),
    'cn_cut': cn_cut_r26(),
}
json.dump(OUT, open(BASE + '/drawings.json', 'w'), ensure_ascii=False)
for k, v in OUT.items():
    print(k, len(v))
