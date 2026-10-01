#!/usr/bin/env python3
"""R26~R29(2026-09-25 사용자 결정): 파트별 분리·직사각형 본체(뒷바)·보조배터리 전원·건반 보관함 → bom_all.json·usage.json 갱신.
원본은 bom_all.before_r26.json·usage.before_r26.json으로 한 번만 백업한다. 다시 돌리면 백업에서 새로 만든다.
새 전원·커넥터 부품은 scratchpad/work_r26/(power·hw)/result.json의 9/25 확인값에서 가져온다(R26 아래 SEL)."""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
WR = os.path.join(os.path.dirname(HERE), 'work_r26')
P, BK = os.path.join(HERE, 'bom_all.json'), os.path.join(HERE, 'bom_all.before_r26.json')
UP, UBK = os.path.join(HERE, 'usage.json'), os.path.join(HERE, 'usage.before_r26.json')
for a, b in ((P, BK), (UP, UBK)):
    if not os.path.exists(b):
        shutil.copy(a, b)
B = json.load(open(BK))
U = json.load(open(UBK))
PWR = json.load(open(os.path.join(WR, 'power', 'result.json')))
from patch_r26 import CU_W  # noqa: E402  CU 칸 안폭 188.5(도면 10 칸 치수와 같은 값)
from draw import fmt  # noqa: E402
N_MOD = sum(1 for p in json.load(open(os.path.join(HERE, 'wf.json')))['final']['assembly_plan'] if p['name'].startswith('모듈 O'))  # 통로 USB-C 가닥 수(PED는 CU 칸 안)
HWR = json.load(open(os.path.join(WR, 'hw', 'result.json')))


def pick(res, cat, key):
    """조사 결과에서 cat이 같고 이름에 key가 들어간 항목 하나."""
    m = [x for x in res['items'] if x.get('cat') == cat and key in x['name']]
    assert len(m) == 1, (cat, key, [x['name'] for x in m])
    return m[0]


def find(bucket, lid):
    for l in B[bucket]:
        if l['line_id'] == lid:
            return l
    raise KeyError(lid)


def drop(bucket, *ids):
    n0 = len(B[bucket])
    B[bucket] = [l for l in B[bucket] if l['line_id'] not in ids]
    assert n0 - len(B[bucket]) == len(ids), (bucket, ids)


ORDER = ['line_id', 'group', 'name', 'role', 'design_ref', 'specs', 'qty', 'purchase_unit', 'unit_price_krw', 'shipping_krw',
         'consumable', 'optional', 'store', 'url', 'image_url', 'page_ok', 'image_ok', 'why']


def line(**kw):
    base = dict(consumable=False, optional=False, page_ok=True, image_ok=True, purchase_unit='1개', shipping_krw=0)
    base.update(kw)
    return {k: base[k] for k in ORDER}


def from_item(it, **kw):
    """조사 결과 한 줄(it) → 부품표 줄. kw가 조사값보다 우선한다."""
    d = dict(name=it['name'], store=it['store'], url=it['url'], image_url=it.get('image_url') or '',
             unit_price_krw=it['price_krw'], shipping_krw=it.get('shipping_krw') or 0,
             specs=[{'k': s['k'], 'v': s['v']} for s in it.get('specs', [])],
             page_ok=bool(it.get('page_ok', True)), image_ok=bool(it.get('image_ok', True)))
    d.update(kw)
    return line(**d)


S = lambda *kv: [{'k': k, 'v': v} for k, v in kv]
sub = lambda l: l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0)

# ---------------- 기본 구성: 빼는 줄 ----------------
# L06 19 V 어댑터·L54 DC 잭·L55 Pi 어댑터 → USB-C PD 입력 하나(L57~L60·L62), L11 스피커 단자 → XT30(L61),
# L37 황동 스탠드오프 → CU 트레이 출력 보스(비용 절감안 CP7과 같은 방식)
drop('base', 'L06', 'L11', 'L37', 'L54', 'L55')
T04 = dict(find('tools', 'T04'))
drop('tools', 'T04')  # 65 W PD 충전기는 피아노 벽 전원(L62)이 됐다. 제작 중에는 같은 충전기로 인두(T01)를 쓴다

# ---------------- 기본 구성: 쓰임이 바뀌는 줄 ----------------
l = find('base', 'L01')
l.update(design_ref='control_unit(R26): 가운데 유닛 CU 칸, CU 트레이 출력 보스 4개(M2.5×6, L47), USB 동글 직결, D6·D7·D16',
         why=l['why'].replace('전원은 5.1 V 5 A PD 어댑터(L55)다. 첫 부팅 때 vcgencmd get_throttled로 저전압이 없는지 확인한다',
                              '전원은 본체 안 5.1 V 강압 모듈(L58)이다(R28). PD 협상이 없으므로 config.txt에 usb_max_current_enable=1, '
                              'EEPROM에 PSU_MAX_CURRENT=5000을 넣고, 첫 부팅과 최대 부하에서 vcgencmd get_throttled로 저전압이 없는지 확인한다'))
assert 'L58' in l['why']
l = find('base', 'L07')
l.update(role='좌우 스피커 유닛 2개(R25: 서브 없음). 스피커 파트(오꾸메 밀폐 상자, 내부 5.05 L)의 출력 앞판에 끼워 연주자 쪽을 향하게 한다. 앰프(L53)가 채널당 약 21 W(20 V)를 준다',
         design_ref='control_unit(R26) 스피커 파트 L(x−16~164)·R(x1058~1238), y215~410, 유닛 중심 z142, 도면 7·8, D12·D13·D14·D17·D18',
         why=l['why'].replace('8 Ω이라 19 V TPA3110에서 채널당 약 19 W(12.3 Vrms)를 받아 1 m에서 약 98 dB(한 개)를 낸다.',
                              '8 Ω이라 TPA3110에서 채널당 약 19 W(19 V)~21 W(R28의 PD 20 V)를 받아 1 m에서 약 99 dB(한 개)를 낸다.'))
assert '약 99 dB' in l['why']
l = find('base', 'L10')
l.update(role='스피커 파트 2개의 상자(외형 180×195×210, 내부 5.05 L)를 한 장에서 재단한다. 앞판(배플)은 PETG 출력이라 합판은 10장이다(도면 8의 재단도)',
         design_ref='control_unit(R26) 스피커 파트 밀폐 상자, 도면 8, D12',
         why='서브 상자가 없어져(R25) 400 폭 한 장이면 상자 2개가 나온다. 오꾸메는 자작보다 가볍고 싸며 밀폐 상자에 충분히 단단하다(비용 절감안 SP2와 같은 결론). '
             'R26으로 상자 깊이가 뒷바에 맞춰 195가 됐고, 구멍이 필요한 앞판은 출력해 드릴 없이 직선 재단만 한다. '
             '두께가 11.5 mm가 아니면 뒤판·위·아래판 폭(157)을 (180 − 2 × 두께)로, 위·아래판 길이(172)를 (195 − 2 × 두께)로 바꾼다. 가운데 유닛용 600×1200(L63)과 같은 상품의 다른 옵션이고, 목공본드(C21)도 같은 판매처다.')
l['specs'] = [(dict(s, v='폭 210 띠: 옆판 195×210 ×4 + 뒤판 157×210 ×2 / 폭 157 띠: 위·아래판 172×157 ×4. 앞판 157×210 ×2는 PETG 출력(톱날 3 mm 포함 폭 370, 길이 약 1,109 mm)')
               if s['k'] == '재단 계획' else s) for s in l['specs']]
l = find('base', 'L14')
l.update(role='스피커 파트 2개(각 4개)와 가운데 유닛(6개)의 고무발 14개. 출력 받침 4 mm와 함께 뒷바를 22 mm 띄워 아래 앞쪽을 케이블 통로로 만든다(R27). 본체와 스피커 진동을 떼어 놓는다(D15)',
         design_ref="control_unit(R26) 뒷바 22 mm 띄움, 치수 A15, D15",
         why=l['why'].replace('필요 12개(R25로 서브 상자가 빠짐)지만 최소 주문이 20개라 8개가 남는다.', '필요 14개(R26: 스피커 파트 8 + 가운데 유닛 6)지만 최소 주문이 20개라 6개가 남는다.'))
assert '필요 14개' in l['why']
l = find('base', 'L15')
l.update(qty=3,
         role='① 왼쪽 볼 앞면 헤드폰 잭: 동글(L51) 출력이 팁·링으로 들어오고 팁·링 노멀 접점이 앰프 쪽으로 나간다. 헤드폰을 꽂으면 노멀 접점이 떨어져 스피커가 기계적으로 끊긴다(R15) '
              '② I/O 판의 댐퍼 페달 잭(R24) ③ CU 트레이의 앰프 입력 잭: 선 ②의 플러그를 받아 저음 차단 RC를 거쳐 앰프(L53) 입력으로 보낸다(R26, 파트 분리)',
         design_ref='control_unit(R26) 헤드폰: PJ-313 노멀 접점, end_parts 왼쪽 볼, I/O 판, CU 트레이',
         why=l['why'] + ' R26으로 선 ②를 CU에서 뽑을 수 있게 세 번째 잭(앰프 입력)을 더했다(+198원).')
l = find('base', 'L24')
l.update(role='4067 모듈을 꽂는 암 헤더(모듈당 1×16 + 1×8). 끝 부속 연결은 R26부터 잠금형 6핀 커넥터(L66)라 EXT 암 헤더는 쓰지 않는다(남는 6핀은 예비)',
         why=l['why'].replace('EXT 1×6 암 2개는 16+16 줄의 남는 6핀으로 만든다.', '16+16 줄의 남는 6핀은 예비로 둔다(R26: 끝 부속은 L66).'))
l = find('base', 'L34')
l.update(qty=50, role='센서 바·센서 기판을 왼쪽 받침 기둥에 고정(모듈당 2, 끝 부속 포함)하고, CU 트레이 부품(앰프 4·강압 모듈 4·PD 트리거 2·앰프 입력 잭 기판 2·퓨즈 홀더 2)과 토글 래치 2개(각 4, L64)를 출력 보스·받침에 고정한다. PETG 구멍에 직접 탭을 내며 조인다',
         design_ref=l['design_ref'] + ', CU 트레이·래치 받침(R26)',
         why=l['why'] + ' R26으로 CU 트레이 부품 14개와 래치 8개 고정이 더해져 30 → 50개(+1,200원).')
l = find('base', 'L49')
l.update(unit_price_krw=14 * 60 + 8 * 50 + 8 * 50 + 40 * 40,
         role='고무발 14개 고정(25 mm), CW-100B25 유닛 8홀을 PETG 앞판에 고정(16 mm), PETG 그릴 8곳(19 mm), 뒷바 출력 부품(도브테일 블록 4×4·CU 트레이 4·I/O 판 4·보조배터리 받침 4·콤 받침 4·XT30 받침 4)을 합판 면에 고정(13 mm)',
         design_ref='control_unit(R26) 스피커 파트·가운데 유닛, 도면 8·10, D15',
         why=l['why'] + ' R26으로 13 mm 40개(뒷바 출력 부품)와 25 mm 2개(가운데 유닛 고무발 6개)가 더해졌다. 합판 면에 송곳으로 자리만 내고 드라이버로 조인다(드릴 없음, 합판 가장자리에는 박지 않는다).')
l['specs'] = [({'k': '구성', 'v': '25mm ×14 = 840원, 16mm ×8 = 400원, 19mm ×8 = 400원, 13mm ×40 = 1,600원'} if s['k'] == '구성' else
               {'k': '용도 치수', 'v': '고무발 구멍 약 Ø5 + M4 와셔(L36), 유닛 장공 Ø4.8에 8호(Ø4.2, PETG 앞판 파일럿 Ø3.4), 그릴은 스페이서 링 10 mm 관통, 출력 부품 관통 구멍 Ø4.5'} if s['k'] == '용도 치수' else s)
              for s in l['specs']]
l = find('base', 'L36')
l.update(role='클램프 나사 머리 아래 Ø9 와셔(흑건 척추 카운터보어 Ø9.5×1.0 안, 32개) + 고무발 고정 피스 와셔(14개, R26)')
l = find('base', 'L41')
l.update(role='모듈 7개·끝 부속 2개 바닥 전체에 붙이는 3T 시트(164×211 한 장씩). 남는 조각은 스피커 유닛 가스켓과 가운데 유닛 ↔ 스피커 파트 맞닿는 면의 띠(R26)')
l = find('base', 'L42')
l.update(role='끝 부속 ↔ 스피커 파트 짧은 PETG 브래킷(40×17×6, R26)의 방진 그로밋(브래킷당 2개). 위치 고정용이고 스피커 무게는 바닥 고무발이 받친다',
         design_ref="control_unit(R26) '짧은 방진 브래킷(그로밋 M3 2개)', 치수 A12, D15")
l = find('base', 'L47')
l.update(role='Pi 5를 CU 트레이의 출력 보스 4개(Ø2.2 탭 구멍)에 바로 조이는 나사(4개 + 예비 2). R26으로 황동 스탠드오프(L37)가 빠졌다(비용 절감안 CP7)',
         design_ref="CU 트레이 출력 보스(R26), 비용 절감안 CP7",
         why='볼트 주문과 같은 상품의 옵션이라 배송비가 늘지 않는다. R26으로 CU 트레이를 출력하므로 보스(외경 6, 높이 6)를 함께 뽑고, M2.5×6이 Pi 기판(1.6)을 지나 약 4 mm 물린다. 손으로 가볍게 조인다(PETG 나사산).')
l = find('base', 'L53')
l.update(role='좌우 스피커(L07)를 울리는 D급 앰프. 20 V 버스(PD 트리거 L57 → 퓨즈 → 스위치)에서 8 Ω 채널당 약 21 W. 입력은 CU 트레이의 앰프 입력 잭(L15 ③)에서 받는다',
         design_ref='control_unit(R26·R28), R14·R16·D18·D19',
         why='R28로 전원이 USB-C PD 20 V가 됐다(보드 콘덴서 35 V, 칩 최대 26 V라 여유가 있다). ' + l['why'].replace('8 Ω·19 V에서 약 19 W/ch라', '8 Ω·20 V에서 약 21 W/ch라'))
assert '20 V에서 약 21 W' in l['why']

# ---------------- 소모품 ----------------
l = find('consumable', 'C03')
l.update(qty=4, role='프레임 7개 + 끝 부속 프레임·커버 + 뒤 커버 7개 + 스피커 앞판 2 + CU 트레이·I/O 판·뒷바 받침(R26) + 도브테일·인서트·수축 시편',
         design_ref='filament: 프레임 175 g ×7, 커버 44 g ×7, 끝 부속, 스피커 앞판 155 g ×2, CU 트레이 160 g, I/O 판 60 g, 쿠폰')
l = find('consumable', 'C04')
l.update(role=f'모듈 7개 + PED 보드 → 허브 USB 8가닥. 모듈 {N_MOD}가닥은 허브에 꽂힌 채 뒷바 아래 케이블 통로에 두고(PED 1가닥은 CU 칸 안 짧은 선), 설치 때 모듈 쪽만 꽂는다(R27). 몰드 ≤12.5×7.5×25라 통로(높이 22)에 들어간다')
l = find('consumable', 'C12')
l.update(role=l['role'] + f' · 케이블 통로 안 모듈 USB-C {N_MOD}가닥 묶음(R27)')
l = find('consumable', 'C13')
l.update(role='앰프(L53) → 통로 → XT30 수(L61) 2쌍(좌우 각 약 0.6 m) + 스피커 파트 안 유닛 → XT30 암(각 약 0.3 m) + 20 V 전원선(PD 트리거 → 퓨즈 → 스위치 → 앰프·강압 모듈, 약 1 m)',
         design_ref='control_unit(R26) 스피커 배선·전원 배선, 도면 9')
l = find('consumable', 'C14')
l.update(role='① 동글(L51) → 왼쪽 볼 헤드폰 잭(L15 ①) ② 헤드폰 잭 노멀 접점 → CU 트레이 앰프 입력 잭(L15 ③). 두 선 모두 CU 쪽 플러그를 남기고 끝 부속 쪽을 잘라 잭에 납땜한다(선이 끝 부속에 붙어 다니고 CU에서 뽑는다, R26)',
         design_ref="control_unit(R26) '선 ①·② 3.5 mm 플러그 2개'")
l = find('consumable', 'C21')
l.update(role='스피커 상자 2개(5.05 L ×2)와 가운데 유닛(오꾸메 11장) 접합, 출력 앞판 둘레 밀봉. 합판은 본드로만 붙이고 마스킹테이프로 눌러 굳힌다(드릴 없음)')

# ---------------- 공구 ----------------
l = find('tools', 'T03')
l.update(role='Pinecil(T01)과 65 W PD 충전기(L62, 피아노 벽 전원)를 잇는 실리콘 C-C 케이블. 제작 중에는 피아노 충전기를 인두 전원으로 쓴다(R26)')

# ---------------- 부품 쓰임새(usage.json) ----------------
Z, UU = U['zones'], U['use']
Z['cab'] = ['③', '케이블 통로(뒷바 아래 앞쪽, y215~258)',
            f'뒷바를 22 mm 띄워 생긴 높이 22 mm 통로(R27). 모듈 USB-C {N_MOD}가닥(PED 1가닥은 CU 칸 안 짧은 선), 스피커 XT30 2쌍, 헤드폰 선 ①·②, 끝 부속 6핀 선이 지난다. 따로 비우던 케이블 공간이 없어져 깊이가 30 mm 줄었다. 도면 7·10.']
Z['cu'] = ['④', '가운데 유닛(건반 보관함 · CU 칸 · 보조배터리 칸)',
           '오꾸메 894×195×100 상자(R26). 가운데 CU 칸(x520~720)의 출력 트레이에 Pi 5·허브·USB 동글·앰프·PED 보드·PD 트리거·5.1 V 강압 모듈·퓨즈가 있고, 뒤 I/O 판에 USB-C 전원 입력·스위치·페달 잭이 있다. '
           '왼쪽 칸은 건반 보관함(R29), 오른쪽 칸은 보조배터리 칸(R28). 도면 9·10·11.']
Z['spk'] = ['⑤', '스피커 파트(좌우 2개)',
            '뒷바 양 끝(x−16~164, x1058~1238)의 오꾸메 밀폐 상자 180×195×210(5.05 L)와 출력 앞판. 가운데 유닛에 도브테일·래치로, 끝 부속에 방진 브래킷으로 붙고, 앰프와는 XT30으로 잇는다(R26). 도면 7·8.']
for k in ('L06', 'L11', 'L37', 'L54', 'L55', 'T04'):
    del UU[k]
UU['L01'] = ['cu', 'CU 칸 출력 트레이 보스 4개 위 1',
             '피아노 소리를 만드는 중앙 컴퓨터. 허브를 거쳐 들어오는 USB-MIDI 8개(O1~O7, PED)를 한곳에서 받아 FluidSynth로 소리를 만들고 USB 동글(L51)로 내보낸다. 전원은 본체 안 5.1 V 강압 모듈(L58)이다.',
             '조립 12 · 도면 9·10']
UU['L07'] = ['spk', '스피커 파트 출력 앞판 2개에 1개씩',
             '왼쪽·오른쪽 스피커 유닛. 앞판 컷아웃(Ø94)에 EVA 가스켓을 대고 직결피스(L49 16 mm) 4개로 PETG 앞판 파일럿 구멍에 조인다. 선은 앞판 아래 선 구멍(본드로 막음)으로 빼서 XT30 암(L61)에 납땜한다. 연주자 쪽을 향한다.',
             '조립 12 · 도면 7·8']
UU['L10'] = ['spk', '합판 1장 → 스피커 상자 2개(10장)',
             '판매처 무료 재단으로 잘라 받아 목공본드(C21)로 붙여 밀폐 상자를 만든다. 외형 180×195×210, 앞판은 PETG 출력이라 합판은 10장이다.', '조립 12 · 도면 8']
UU['L14'] = ['spk', '스피커 파트 2 × 4 + 가운데 유닛 6 = 14 + 예비 6',
             '상자 바닥에 출력 받침(4 mm)을 대고 피스(L49 25 mm)와 와셔(L36)로 고정한다. 받침과 함께 뒷바를 22 mm 띄워 아래 앞쪽을 케이블 통로로 만들고(R27), 스피커 진동이 본체·센서로 가지 않게 한다(D15).',
             '조립 12 · 도면 10']
UU['L15'] = ['end', '① 왼쪽 끝 부속 볼 앞면 1(헤드폰 잭) ② I/O 판 1(댐퍼 페달 잭) ③ CU 트레이 1(앰프 입력 잭)',
             '① 헤드폰 잭: 동글 출력(C14 ①)을 받고 노멀 접점에서 선 ②로 보낸다. 헤드폰을 꽂으면 접점이 떨어져 스피커가 끊긴다(R15). ② 페달 케이블(L50)을 꽂는다. ③ 선 ②의 플러그를 받아 저음 차단 RC → 앰프 입력으로 보낸다(R26).',
             '조립 11·12 · 도면 9']
UU['L24'] = ['mod', '모듈마다 4067 소켓 1×16 + 1×8(×7)', '4067 모듈을 뺐다 꽂을 수 있게 하는 암 소켓. 필요한 길이로 잘라 쓴다. 끝 부속 연결은 잠금형 6핀 커넥터(L66)다(R26).', '조립 6']
UU['L34'] = ['mod', '모듈마다 2(×7 = 14) + 끝 부속 4 + CU 트레이 부품 14 = 32 + 예비 8',
             '센서 바와 센서 기판을 왼쪽 받침 기둥에, 앰프·강압 모듈·PD 트리거·앰프 입력 잭 기판·퓨즈 홀더를 CU 트레이 보스에 고정한다. PETG 구멍에 나사산을 내며 조인다.', '조립 5·12']
UU['L36'] = ['mod', '클램프 나사 32 + 고무발 피스 14 = 46 + 예비 14', '클램프 나사 머리 아래(흑건 척추 카운터보어 안)와 고무발 피스 아래에 끼워 누르는 힘을 넓게 나눈다.', '조립 7·12']
UU['L41'][1] = '모듈 7 + 끝 부속 2의 바닥 시트(164×211) + 자투리는 스피커 가스켓 · 가운데 유닛 ↔ 스피커 파트 맞닿는 면 띠'
UU['L42'] = ['spk', '끝 부속 ↔ 스피커 파트 브래킷 2개 × 2 = 4', '짧은 브래킷(40×17×6) 나사 구멍에 끼우는 실리콘 그로밋. 스피커 진동이 끝 부속으로 넘어가지 않게 한다. 무게는 고무발이 받친다.', '조립 11·12']
UU['L47'] = ['cu', 'Pi 윗면 4 + 예비 2', 'CU 트레이의 출력 보스(Ø2.2 탭 구멍)에 Pi 5 보드를 바로 조이는 나사. 손으로 가볍게 조인다.', '조립 12']
UU['L53'] = ['cu', 'CU 칸 1', '좌우 스피커 앰프. VCC·GND는 20 V 단자(퓨즈·스위치 뒤)에서, 입력 L·G·R은 앰프 입력 잭(L15 ③) → RC(L56·L29)에서, 출력 L±·R±는 스피커선(C13) → XT30(L61)으로.', '조립 12 · 도면 9']
UU['C03'] = ['com', '회색 4 kg — 프레임 7 + 뒤 커버 7 + 끝 부속 + 스피커 앞판 2 + CU 트레이·I/O 판·뒷바 출력물 + 쿠폰', '건반을 받치는 프레임과 덮개, 스피커 앞판, 뒷바 출력 부품을 출력하는 재료.', '조립 1·2·12']
UU['C04'] = ['cab', '모듈 7 + 페달 보드 1 → 허브, 8가닥', f'각 모듈 RP2040-Zero의 USB-C에서 CU 허브까지. 모듈 {N_MOD}가닥은 허브에 꽂힌 채 케이블 통로에 두고(PED 1가닥은 CU 칸 안 짧은 선), 설치 때 모듈 쪽만 꽂는다(R27).', '조립 11 · 도면 10']
UU['C12'] = ['cab', f'모듈 USB-C {N_MOD}가닥 + 끝 부속 선 묶음(통로 안)', '통로 안에서 USB 케이블을 묶어 두고, 모듈 뒷벽 고리에서 당김을 막는다.', '조립 8·11']
UU['C13'] = ['cu', '앰프 → XT30 수 2쌍(각 약 0.6 m) + 스피커 안 유닛 → XT30 암(각 약 0.3 m) + 20 V 전원선 약 1 m',
             '앰프 출력에서 통로를 지나 양 끝 XT30까지, 스피커 파트 안에서 유닛까지 잇는 스피커선. 남는 선으로 PD 트리거 → 퓨즈 → 스위치 → 앰프·강압 모듈 전원선을 만든다.', '조립 12 · 도면 9']
UU['C14'] = ['end', '① 동글 → 헤드폰 잭 ② 노멀 접점 → 앰프 입력 잭(각 약 0.7 m)',
             '끝 부속 쪽은 잘라 PJ-313에 납땜하고 CU 쪽 플러그를 남긴다. 선이 끝 부속에 붙어 다니고, 설치 때 CU(동글·앰프 입력 잭)에 꽂는다(R26).', '조립 11·12 · 도면 9']
UU['C21'] = ['spk', '스피커 상자 2개 + 가운데 유닛의 합판 이음', '합판을 붙이고 틈을 막아 공기가 새지 않게 한다(저음 보존). 가운데 유닛도 본드로만 붙인다(드릴 없음).', '조립 12 · 도면 8·11']
UU['T03'] = ['tool', 'T01 ↔ L62', '인두 전원 케이블. 피아노 벽 전원용 65 W PD 충전기(L62)에 꽂는다. 인두에 닿아도 녹지 않는 실리콘 피복이다.', '납땜 전반']

# ---------------- 기본 구성: 새 줄(커넥터·래치·자석, work_r26/hw) ----------------
KEEP = ('브랜드', '리드선', '정격', '하우징', '재질', '전체 길이', '본체', '걸이', '판 두께', '커넥터', '전선', '등급/규격', '흡착력(추정)', '사용 온도')
spec = lambda it, *extra: [s for s in it['specs'] if s['k'] in KEEP] + [{'k': k, 'v': v} for k, v in extra]
xt = pick(HWR, 'xt30', 'XT30U-M + XT30U-F')
la = pick(HWR, 'latch', '매미고리 1-20')
xh = pick(HWR, 'jst_xh6', 'BU-LP 5S')
mg = pick(HWR, 'magnet', '원형자석 8mm — 옵션 3.0T')
NEW_HW = [
    from_item(xt, line_id='L61', group='배선·납땜', name='[AMASS] XT30U-M + XT30U-F 18AWG 10cm 실리콘 와이어 (수·암 1쌍)',
              role='앰프 ↔ 좌우 스피커 파트의 스피커선 커넥터 2쌍. 수(앰프 쪽)는 통로 양 끝으로 나온 선에, 암(스피커 쪽)은 스피커 파트 앞판 아래로 나온 선에 납땜한다. 극성이 있어 거꾸로 꽂히지 않는다(R26)',
              design_ref="control_unit(R26) '스피커: XT30 2쌍', 도면 9·10",
              specs=spec(xt, ('구성', '수(XT30U-M) no=12779720 + 암(XT30U-F) no=12779721, 각 1,760원(VAT 포함)'),
                         ('XT90과 비교', 'XT90은 정격 약 40~45 A(순간 90 A)·4.5 mm 핀·10 AWG급 전선용이라 스피커선(최대 약 1.6 A rms)에 너무 크다')),
              qty=2, purchase_unit='1쌍(수 1 + 암 1)', unit_price_krw=3520, shipping_krw=0,
              store='엘레파츠 (수 no=12779720 / 암 no=12779721)',
              why='AMASS 정품이고 18 AWG 실리콘 리드가 달려 있어 납땜만 하면 된다(압착 공구 불필요). 정격 15~20 A라 스피커 전류의 9배 이상 여유가 있다. '
                  '말씀하신 XT90은 전기자전거·드론 배터리용 대형 커넥터라 같은 계열의 작은 XT30을 골랐다. 선을 뽑을 때 몸통을 잡고 뺀다. 엘레파츠 합배송이라 배송비 0원(따로 사면 3,000원). '
                  '더 싸게는 20 cm 연장선(no=12779738, 2,860원)을 잘라 쓸 수 있다.'),
    from_item(la, line_id='L64', group='구조·체결', name='매미고리 1-20 (SUS304 스테인리스 토글 래치, 25×54mm)',
              role='가운데 유닛 ↔ 스피커 파트를 뒷면에서 당겨 잠그는 토글 래치(이음마다 1개, 2개). 도브테일이 위치를 잡고 래치가 벌어지지 않게 한다(R26)',
              design_ref="control_unit(R26) '[결합] 출력 도브테일 2개 + 뒷면 토글 래치 1개', 도면 10",
              specs=spec(la, ('고정', '도브테일 블록의 출력 받침에 M3×10(L34) 4개로 자가 탭(합판에 직접 박지 않는다)')),
              qty=2, purchase_unit='1조(본체 + 걸이)', unit_price_krw=2400, shipping_krw=3000,
              store='철물박사 metaldiy.com (상품코드 8806379117286)',
              why='뒷면 높이(100 mm)에 맞는 크기이고 도면에 구멍 지름(Ø4)까지 나와 있다. 납작하고 폭이 넓어 두 상자를 옆으로 당겨 붙이기에 튼튼하다. '
                  '나사 포함 여부가 표기되지 않아 M3×10(L34)으로 출력 받침에 조이도록 했다(드릴 없음). 같은 제품이 11번가(9543586916)에 2,840원으로도 있다. 배송비 3,000원(10만원 이상 무료).'),
    from_item(mg, line_id='L65', group='구조·체결', name='초강력 네오디움 원형자석 8mm — 3.0T (Ø8×3mm, N35)',
              role='가운데 유닛 뚜껑 3장을 제자리에 붙여 두는 자석. 뚜껑마다 대각선 2곳에 뚜껑·받침 한 쌍씩(12개) + 예비 2. 출력 받침·뚜껑의 Ø8.2 포켓에 순간접착제(C18)로 붙인다(R26)',
              design_ref="control_unit(R26) '뚜껑 3장, 모서리 출력 받침과 작은 자석'",
              specs=spec(mg, ('센서와 거리', '뚜껑 자석(y≥215) ~ 센서 열(y67) 150 mm 이상, 영향 없음(D14 기준 100 mm)')),
              qty=14, unit_price_krw=160, shipping_krw=0,
              store='대건상사 dgmagnet.com (product_no=17, 옵션 3.0T)',
              why='건반 자석(L21 Ø5×2)을 산 곳과 같은 판매처라 합배송된다(배송비는 L21에 이미 있다). 한 쌍 흡착력이 약 1 kg이라 들고 옮길 때 뚜껑이 미끄러지지 않고 손으로는 쉽게 열린다. '
                  '포켓에 넣을 때 극(N·S)이 서로 당기게 방향을 맞춘다.'),
    from_item(xh, line_id='L66', group='배선·납땜', name='리튬폴리머 배터리 밸런스잭 연장선 5셀용 (JST-XH 6핀 수↔암, BU-LP 5S, 200mm)',
              role='끝 부속 ↔ O1·O7 센서 선 6가닥을 잇는 잠금형 커넥터 2쌍. 연장선 가운데를 잘라 수·암 리드 1쌍으로 쓴다(압착 공구 불필요, R26)',
              design_ref="control_unit(R26) '끝 부속 ↔ O1·O7: 6핀 잠금 커넥터', end_parts EXT 6선",
              specs=spec(xh, ('쓰는 법', '가운데를 잘라 수(검정)는 O1·O7 제어 기판에, 암(흰색)은 끝 부속 선에 납땜하고 수축튜브(C10)로 마감')),
              qty=2, unit_price_krw=3000, shipping_krw=3500,
              store='알씨뱅크 (상품번호 QQ29812, BU-LP 5S)',
              why='국내 재고(물류창고 44개)이고 22 AWG 실리콘 200 mm라 자르면 약 10 cm씩 수·암 리드가 된다. XH 하우징은 걸림 턱이 있어 듀폰 헤더보다 잘 안 빠진다. '
                  '추석 휴무로 9/29 출고 예정. 배송비 3,500원(5만원 이상 무료). 더 싸게는 다이프랜드 30 cm(1,700원, 전선 규격 미표기)도 있다.'),
]
for l in NEW_HW:
    l['image_url'] = l['image_url'] or ''
UU['L49'] = ['spk', '고무발 14(25 mm) + 유닛 8홀(16 mm) + 그릴 8곳(19 mm) + 뒷바 출력 부품 40(13 mm)',
             '합판·PETG에 바로 박는 직결 피스. 합판 면에 송곳으로 자리만 내고 드라이버로 조인다(드릴 없음). 합판 가장자리(단면)에는 박지 않는다.', '조립 12 · 도면 8·10']
UU['L34'] = ['mod', '모듈마다 2(×7 = 14) + 끝 부속 4 + CU 트레이 부품 14 + 토글 래치 8 = 40 + 예비 10',
             '센서 바와 센서 기판을 왼쪽 받침 기둥에, 앰프·강압 모듈·PD 트리거·앰프 입력 잭 기판·퓨즈 홀더를 CU 트레이 보스에, 토글 래치를 도브테일 블록 받침에 고정한다. PETG 구멍에 나사산을 내며 조인다.', '조립 5·12']
UU['L61'] = ['cab', '앰프 쪽 수 2(통로 양 끝) + 스피커 쪽 암 2(앞판 아래)',
             '앰프 출력선과 스피커선을 잇는 커넥터. 설치 때 스피커 파트를 도브테일에 끼운 뒤 통로 안에서 꽂는다. 뽑을 때는 선이 아니라 몸통을 잡는다.', '조립 11·12 · 도면 9·10']
UU['L64'] = ['spk', '가운데 유닛 ↔ 스피커 파트 이음 뒷면 2(이음마다 1)',
             '본체(래치)는 가운데 유닛 쪽, 걸이는 스피커 파트 쪽 도브테일 블록의 출력 받침에 M3×10(L34) 4개로 조인다. 걸고 누르면 두 파트가 당겨져 붙는다.', '조립 11·12 · 도면 10']
UU['L65'] = ['cu', '뚜껑 3장 × 대각선 2곳 × 한 쌍(뚜껑·받침) = 12 + 예비 2',
             '출력 받침과 뚜껑의 Ø8.2 포켓에 순간접착제로 붙인다. 두 자석이 서로 당기게 극 방향을 맞춘다.', '조립 12']
UU['L66'] = ['end', '끝 부속 L·R ↔ O1·O7, 2쌍',
             '연장선 가운데를 잘라 수(검정)는 O1·O7 제어 기판의 EXT 패드에, 암(흰색)은 끝 부속 선에 납땜하고 수축튜브로 마감한다. 설치 때 꽂고 분리 때 뽑는다.', '조립 6·11']

# ---------------- 주문 전 확인(보고서 §check) ----------------
UN = B['unresolved']
assert UN[6].startswith('앰프 전원: XH-A232') and UN[7].startswith('Pi 5 전원은 HT-PD27W'), (UN[6][:30], UN[7][:30])
UN[4] = UN[4].replace('동진나무공장 목공본드 3,500원이 합판과 합배송되는지도 확인해야 한다.',
                      '동진나무공장 목공본드 3,500원이 합판 두 장(400×1200·600×1200)과 합배송되는지도 확인해야 한다.')
UN[6] = ('전원(R28): PD 트리거(L57)를 20 V로 맞추고 65 W 충전기(L62)를 꽂아 무부하 출력이 20 V인지 멀티미터로 확인한 뒤 퓨즈(L60)·스위치(L59)·앰프·강압 모듈(L58)을 잇는다. '
         '강압 모듈은 Pi를 꽂기 전에 부하 없이 5.10~5.20 V로 맞추고, 극성(+/−)을 두 번 확인한다.')
UN[7] = ('Pi 5 전원은 강압 모듈의 5.1 V다(PD 협상 없음). 공식 문서대로 EEPROM에 PSU_MAX_CURRENT=5000(sudo rpi-eeprom-config --edit), config.txt에 usb_max_current_enable=1을 넣으면 '
         'USB 포트 한도가 600 mA → 1.6 A가 된다. 첫 부팅과 최대 볼륨에서 vcgencmd get_throttled가 0x0인지 확인한다(저전압 경고는 4.63 V 아래).')
UN.insert(8, '보조배터리(D19): USB-C PD 20 V 3 A(60 W) 이상이어야 최대 음량에서 끊기지 않는다. 가진 제품의 출력 표기(예: 20V⎓3A)를 먼저 확인하고, 45 W(20 V 2.25 A) 제품이면 볼륨 상한을 1 dB 낮춘다. '
             '켠 채로 충전하는 패스스루는 제품마다 달라 권하지 않는다.')
assert UN[11].startswith('받은 뒤 치수 확인') and UN[12].startswith('설계와 다른 대체') and UN[15].startswith('필라멘트')
UN[11] = UN[11].replace('CW-100B25 바스켓 지름·장공 위치, ', 'CW-100B25 바스켓 지름·장공 위치, PD 트리거·강압 모듈 크기와 고정 구멍(CU 트레이 보스 위치), 토글 래치 구멍 간격, XT30 몸통 크기, ')
UN[12] = UN[12].replace('CU 뒷면 스피커 단자 생략', 'CU 뒷면 스피커 단자 생략 → 스피커 단자판도 XT30으로(R26)')
UN[15] = ('필라멘트: parts_needed의 \'회색 2 kg, 합계 5 kg\'을 \'흰 2 / 검정 1 / 회색 4 = 7 kg\'으로 고쳐야 한다'
          '(R26으로 스피커 앞판·CU 트레이·I/O 판·예비 콤이 더해져 회색 순수 필요량 약 2.65 kg).')
B['unresolved'] = UN

# ---------------- 기본 구성: 새 줄(전원부, work_r26/power + 엘레파츠 9/25 확인) ----------------
tr = next(x for x in PWR['items'] if x['id'] == 'P1')
bk = next(x for x in PWR['items'] if x['id'] == 'B1')
ch = next(x for x in PWR['items'] if x['id'] == 'CH1')
pb = next(x for x in PWR['items'] if x['id'] == 'PB1')
NEW_PW = [
    from_item(tr, line_id='L57', group='제어·전원', name='100W QC PD 트리거 디코이 고정출력 모듈 5V-20V (HAM6113, HUSB238)',
              role='피아노의 전원 입력(USB-C). 벽 충전기(L62)나 보조배터리와 PD로 협상해 20 V를 받아 퓨즈(L60) → 스위치(L59) → 20 V 버스로 보낸다. I/O 판 안쪽 포켓에 끼워 USB-C 구멍이 밖을 향한다(R28)',
              design_ref="control_unit(R28) '[전원] 입력은 USB-C 하나', 도면 9, D19",
              specs=[s for s in tr['specs'] if s['k'] != '재고/배송기간'] + [{'k': '20 V가 없을 때', 'v': '한 단계 낮은 전압(15·12 V)으로 내려간다 → 앰프·강압 모듈은 동작, 최대 음량만 준다'}],
              qty=1, unit_price_krw=4950, shipping_krw=0, store='아이씨뱅큐 (제노 HAM6113, P017179277)',
              why='기본값이 20 V라 따로 설정할 것이 없고(납땜 점퍼 없음 = 20 V), 20 V 5 A가 명시돼 있으며 16.4 × 10 mm로 I/O 판에 넣기 좋다. PD 전원은 꽂을 때 전압을 다시 협상하므로 전원 스위치는 트리거 뒤(20 V 쪽)에 둔다. '
                  '같은 판매처의 DIP 스위치형(HAM6109)은 전류 정격이 없고 20 V가 없는 전원에서 출력이 나오지 않아 뺐다. 아이씨뱅큐 합배송(앰프 보드 L53과 같은 제노 상품).'),
    from_item(bk, line_id='L58', group='제어·전원', name='200W XL4016 DC-DC 강압 컨버터 모듈 IN 4-40V OUT 1.25-36V 5A (HAM6415, XH-M401)',
              role='20 V 버스 → 5.1 V. Pi 5(USB-C 전원선 C24)와 USB 허브(L17, DC 잭)에 전원을 준다. Pi에는 이 5 V만 들어간다(D16). CU 트레이 보스에 M3×10(L34) 4개로 고정(R28)',
              design_ref="control_unit(R28) '5.1 V 5 A 강압 모듈이 Pi 5와 허브에 전원', 도면 9·10, D16",
              specs=bk['specs'] + [{'k': '설정', 'v': 'Pi를 꽂기 전에 부하 없이 5.10~5.20 V로 맞추고 노브를 빼거나 순간접착제로 고정'}],
              qty=1, unit_price_krw=5170, shipping_krw=0, store='아이씨뱅큐 (제노 HAM6415, P017179502)',
              why='연속 5 A가 명시돼 있고 방열판이 붙어 있다. 5 V 부하(Pi 약 1~2 A + 허브·모듈 약 0.6 A, 순간 약 3~3.5 A)에 여유가 있다. 비동기 벅이라 20 V → 5 V 효율은 약 85%로 추정한다(평균 손실 약 1.5 W). '
                  'Pi 5는 PD가 아닌 5 V를 받으면 3 A 전원으로 가정하므로, 공식 문서대로 EEPROM PSU_MAX_CURRENT=5000(또는 config.txt usb_max_current_enable=1)을 넣어 USB 한도를 1.6 A로 연다. 아이씨뱅큐 합배송.'),
    line(line_id='L59', group='제어·전원', name='[ZX Electronics] KCD1-101A BLACK I/O 로커 스위치 (2P ON-OFF, 6A 250VAC / 10A 125VAC)',
         role='피아노 전원 스위치. PD 트리거·퓨즈 뒤 20 V 쪽에 넣어 앰프와 강압 모듈을 함께 켜고 끈다. I/O 판의 출력 구멍에 끼운다(스냅인, R28)',
         design_ref="control_unit(R28) 'PD 트리거 → 퓨즈 → 스위치 → 20 V 버스', 도면 9",
         specs=S(('형식', '로커 스위치 2P ON-OFF(SPST), 오목형 액추에이터, I/O 표시'), ('정격', '6 A 250 VAC / 10 A 125 VAC, UL 인증, KC 인증서 게시'),
                 ('실장', '패널 스냅인(KCD1 표준 패널 구멍 약 19 × 13 mm, 받은 뒤 확인해 I/O 판 구멍을 맞춘다)'),
                 ('가격·발송(9/25)', '350원 + VAT = 385원, 24시간 이내 발송(제품번호 EPX389PN)')),
         qty=1, unit_price_krw=385, store='엘레파츠 (no=32569)', url='https://www.eleparts.co.kr/goods/view?no=32569',
         image_url='https://img2.eleparts.co.kr/goods/thumb/3/0620020090000000182.jpg',
         why='20 V에서 흐르는 전류는 평균 약 0.6 A, 순간 최대 약 2.6 A라 6 A 정격으로 충분하다. 끌 때는 소프트웨어로 먼저 볼륨을 0으로 하고 스위치를 내린다(팝 방지). 엘레파츠 합배송.'),
    line(line_id='L60', group='제어·전원', name='[Coms] BU914 원형 휴즈 홀더(5×20 mm) + [LITTELFUSE] 0218005.MXP 5 A 지연형 퓨즈 5개',
         role='20 V 버스 보호 퓨즈. PD 트리거 출력 + 선에 홀더를 끼워 넣어 배선 단락 때 선이 타지 않게 한다. 예비 퓨즈 4개(R28)',
         design_ref="control_unit(R28) 'PD 트리거가 20 V를 받아 퓨즈 → 전원 스위치', 도면 9",
         specs=S(('홀더', 'Coms BU914 인라인 원형 홀더, 5×20 mm 유리관 퓨즈용, 빨간 선 일체(가운데를 잘라 끼움), 1,110원(no=3237821, 3.5일)'),
                 ('퓨즈', 'Littelfuse 0218005.MXP, 5×20 mm 지연형(Slo-Blo) 5 A 250 V, 차단 용량 50 A, K-MARK 등, 100원 + VAT × 5개(최소 5) = 550원(no=12766820, 24시간)'),
                 ('왜 지연형', '켤 때 앰프·강압 모듈 입력 콘덴서 충전 전류로 속단형이 끊어지지 않게')),
         qty=1, purchase_unit='1세트(홀더 1 + 퓨즈 5)', unit_price_krw=1660, store='엘레파츠 (홀더 no=3237821 / 퓨즈 no=12766820)',
         url='https://www.eleparts.co.kr/goods/view?no=3237821', image_url='https://img2.eleparts.co.kr/goods/external/323/3237821_49d07a260912092605view.jpg',
         why='충전기·보조배터리는 스스로 과전류를 막지만, 본체 안 20 V 선이 눌려 단락되면 선이 먼저 뜨거워질 수 있어 퓨즈를 둔다. 평균 0.6 A·순간 약 2.6 A라 5 A면 평소에는 끊기지 않는다. 엘레파츠 합배송.'),
    dict(T04, line_id='L62', group='제어·전원',
         role='벽 전원. 피아노 I/O 판의 USB-C 입력(L57)에 2 m C-C 선(C23)으로 잇는다. C1 또는 C2 포트 하나만 쓴다(두 포트를 함께 쓰면 45 W로 줄어 최대 음량에서 모자람). 제작 중에는 같은 충전기로 인두(T01)를 쓴다(R28)',
         design_ref="control_unit(R28) '벽에서는 65 W PD 충전기', D19",
         specs=[{'k': k, 'v': v} for k, v in [(s['k'], s['v']) for s in ch['specs']]] + [{'k': '가격(9/25)', 'v': '다나와 최저가 19,800원, 무료배송(케이블 미포함)'}],
         unit_price_krw=19800, shipping_krw=0,
         why='C 포트 하나에서 20 V 3.25 A(65 W)가 나오는 것을 PDO 표로 확인했다(KC 적합성 R-R-S2Z-TY2213). 피아노의 순간 최대 약 52 W를 버티고, 공구 목록에 있던 인두용 충전기(옛 T04)와 같은 제품이라 피아노 전원으로 옮기고 인두와 함께 쓴다(공구 −19,800원, 기본 +19,800원). '
             '이미 USB-C PD 20 V 3 A 이상 충전기(노트북 충전기 등)가 있으면 사지 않아도 된다.'),
    dict(find('base', 'L10'), line_id='L63', group='구조·체결', name='무료배송 오꾸메 합판 600×1200×11.5mm 무료재단',
         role='가운데 유닛(894×195×100) 상자를 한 장에서 재단한다. 바닥 2·뚜껑 2·앞판·뒤판 2·끝판 2·칸막이 2 = 11장(도면 11의 재단도, R26)',
         design_ref='control_unit(R26) 가운데 유닛, 도면 11',
         specs=S(('규격', '600 × 1200 × 11.5mm'), ('재질', '오꾸메 합판'), ('재단', '무료재단(도면 11 재단도를 함께 보냄), 직선 재단만'),
                 ('가격', '22,520원(9/24 옵션가), 무료배송'),
                 ('재단 계획', '폭 195 띠 ①: 바닥 356·338 + 뚜껑 356 / 폭 195 띠 ②: 뚜껑 338 + 칸막이 172×77 / 폭 77 띠: 앞판 894 + 끝판 172 / 폭 77 띠: 뒤판 356·338 + 끝판 172 + 칸막이 172×57(CU↔보조배터리) / 남는 띠 약 44')),
         qty=1, unit_price_krw=22520, shipping_krw=0, store='동진나무공장 (namugongjang.com, product_no=1378)',
         why='스피커 상자용 400×1200(L10)과 같은 상품의 다른 옵션이다. 합판은 직선으로만 잘라 오고 구멍이 필요한 곳(CU 칸 바닥·뚜껑·I/O 판)은 출력해서 드릴이 필요 없다. 본드로만 붙인다(C21). '
             '두께가 11.5 mm가 아니면 앞·뒤판 높이(77)를 (100 − 2 × 두께)로 바꾼다. 무료배송이고 목공본드(C21)와 같은 판매처다.'),
]
B['base'] += NEW_HW + NEW_PW
B['base'].sort(key=lambda l: int(l['line_id'][1:]))
for l in B['base']:
    assert set(l) == set(ORDER), (l['line_id'], set(l) ^ set(ORDER))

# ---------------- 허브(L17): 전원은 본체 5.1 V, 자리는 보조배터리 칸 ----------------
l = find('base', 'L17')
l.update(role='모듈 7개 + PED의 USB-MIDI를 Pi 5 USB 한 포트로 모은다. 전원은 본체 5.1 V 강압 모듈(L58)에서 DC 잭으로 받는다(허브에 딸린 5 V 3 A 어댑터 선을 잘라 플러그 쪽을 쓴다). 길이 228 mm라 CU 칸(안폭 ' + fmt(CU_W) + ')이 아니라 보조배터리 칸 뒤 벽에 둔다(R26·R28)',
         design_ref="electronics '[전원] 전원형 허브', control_unit(R28) 5.1 V 버스, 도면 10, D16",
         why=l['why'] + ' R28 확인(9/25): 허브 어댑터가 DC 5 V 3 A라 본체 5.1 V 버스에서 바로 먹일 수 있다(다나와 상세·제조사 이미지). DC 플러그 규격이 공개되지 않아 어댑터 선을 잘라 쓴다. 어댑터를 남기고 싶으면 실물 플러그를 재서 DC 플러그 선(5.5×2.1 등)을 따로 산다.')
l['specs'] = [({'k': '전원', 'v': 'DC 5 V 3 A(어댑터 5 V 3 A 15 W 포함), 외부전원 겸용(버스 전원으로도 동작), 크기 48 × 228 × 24 mm, 130 g'} if s['k'] == '전원' else s) for s in l['specs']]
assert any('5 V 3 A' in s['v'] for s in l['specs'])
UU['L17'] = ['cu', '보조배터리 칸 뒤 벽 1(CU 칸에 안 들어감)',
             '모듈 7개와 페달 보드의 USB 8가닥을 모아 Pi 5 USB 한 포트로 보낸다. 모듈 USB 선은 통로 → CU 트레이 입구 → 낮은 칸막이 위로 들어온다. 전원은 5.1 V 강압 모듈에서 DC 잭으로 받는다.', '조립 11·12 · 도면 9·10']

# ---------------- 소모품: 새 줄(케이블) ----------------
NEW_C = [
    line(line_id='C22', group='배선·납땜', consumable=True, name='[MachLink] USB-C to C PD 60W 초고속충전 케이블, ML-CPD606 [블랙/0.6m]',
         role='보조배터리 → 피아노 USB-C 입력. 보조배터리 칸에서 낮은 칸막이 위 → CU 칸 → I/O 판 선 통과 구멍으로 빼서 입력(L57)에 꽂는다(R28)',
         design_ref="control_unit(R28) '보조배터리를 같은 입력에 꽂는다'",
         specs=S(('규격', 'USB-C 수 ↔ USB-C 수, USB 2.0, PD 60 W(20 V 3 A)'), ('길이', '0.6 m'), ('가격·발송(9/25)', '1,309.09원 + VAT = 1,440원, 2.5일')),
         qty=1, unit_price_krw=1440, store='엘레파츠 (no=17806172)', url='https://www.eleparts.co.kr/goods/view?no=17806172',
         image_url='https://image3.compuzone.co.kr/img/product_img/2025/1028/1291849/1291849_600.jpg',
         why='피아노 최대 전류는 20 V에서 약 2.6 A라 3 A(60 W) 선으로 충분하다(5 A e-marker 선은 필요 없다). 보조배터리 일체형 짧은 선으로는 입력까지 닿지 않아 0.6 m를 쓴다. 엘레파츠 합배송.'),
    line(line_id='C23', group='배선·납땜', consumable=True, name='[MachLink] USB-C to C PD 60W 초고속충전 케이블, ML-CPD62 [블랙/2m]',
         role='벽 충전기(L62) → 피아노 USB-C 입력(L57). 제작 중에는 인두(T01) 전원선으로도 쓴다(R28)',
         design_ref="control_unit(R28) '벽에서는 65 W PD 충전기'",
         specs=S(('규격', 'USB-C 수 ↔ USB-C 수, USB 2.0, PD 60 W(20 V 3 A)'), ('길이', '2 m(콘센트에서 책상 위 피아노 뒤까지)'), ('가격·발송(9/25)', '2,427.27원 + VAT = 2,670원, 2.5일')),
         qty=1, unit_price_krw=2670, store='엘레파츠 (no=17806170)', url='https://www.eleparts.co.kr/goods/view?no=17806170',
         image_url='https://image3.compuzone.co.kr/img/product_img/2025/1028/1291847/1291847_600.jpg',
         why='3 A(60 W) 선이면 순간 최대 약 52 W를 버틴다. 1 m(1,850원)는 콘센트가 멀면 모자라 2 m로 했다. 이미 C-C 60 W 선이 있으면 사지 않아도 된다. 엘레파츠 합배송.'),
    line(line_id='C24', group='배선·납땜', consumable=True, name='[MAXTEK] 맥스텍 USB C타입 제작용 케이블 2선 Type-C Male(숫) DIY PD 전원 [MT666]',
         role='5.1 V 강압 모듈(L58) 출력 → Pi 5 USB-C 전원 입력. 벗겨진 두 선(빨강 +, 검정 −)을 강압 모듈 출력 단자에 물린다(R28)',
         design_ref="control_unit(R28) 'Pi에는 이 5 V만 들어간다(D16)'",
         specs=S(('형태', 'USB-C 수 플러그 + 2선(전원 전용), 길이 0.2~0.29 m'), ('가격·발송(9/25)', '1,081.82원 + VAT = 1,190원, 2.5일(제품번호 EPYGYMXJ)'),
                 ('Pi 5 설정', 'PD가 아닌 5 V라 EEPROM PSU_MAX_CURRENT=5000 또는 config.txt usb_max_current_enable=1')),
         qty=1, unit_price_krw=1190, store='엘레파츠 (no=17358965)', url='https://www.eleparts.co.kr/goods/view?no=17358965',
         image_url='https://image3.compuzone.co.kr/img/product_img/2025/0513/1241239/1241239_600.jpg',
         why='Pi 5를 GPIO 5 V 핀이 아니라 USB-C 입력으로 먹여 보드의 입력 경로를 그대로 쓴다. 전선 굵기가 표기되지 않아, 받은 뒤 최대 부하에서 Pi 쪽 전압이 5.0 V 아래로 내려가지 않는지(vcgencmd get_throttled 0x0) 확인한다. 엘레파츠 합배송.'),
]
B['consumable'] += NEW_C

# ---------------- 선택 항목: 보조배터리 ----------------
B['optional'].append(line(line_id='O07', group='제어·전원', optional=True, name='Morui(모루이) 65W 20000mAh PD PPS 보조배터리 MT-65',
    role='무선 연주용 보조배터리(R28). 가운데 유닛 보조배터리 칸의 받침(최대 170×85×35)에 끈으로 고정하고 0.6 m C-C 선(C22)으로 입력에 꽂는다. 이미 PD 20 V 3 A 이상 보조배터리가 있으면 필요 없다',
    design_ref="control_unit(R28) '보조배터리(USB-C PD 20 V 3 A 이상, D19)', 치수 A18",
    specs=[s for s in pb['specs'] if s['k'] != 'KC'] + [{'k': 'KC', 'v': '안전인증 ZU101171-25002(수입 (주)그린전산)'},
                                                         {'k': '사용 시간(계산)', 'v': '76 Wh × 0.85 ÷ 평균 약 12 W ≈ 5시간(조용히 약 6, 크게 약 4)'},
                                                         {'k': '가격(9/25)', 'v': '공식몰 42,900원 무료배송(판매 중) · 다나와 최저 31,790원(판매처·배송비 미확인)'}],
    qty=1, unit_price_krw=42900, store='모루이 공식몰 (morui.co.kr, product_no=34)', url='https://morui.co.kr/product/detail.html?product_no=34',
    image_url='https://morui.co.kr/web/product/big/202509/9214bcb6e41555a23476d3055e9594e0.png',
    why='C 포트에서 20 V 3.25 A(65 W)가 나와(공식 상세 이미지) 순간 최대 약 52 W를 버틴다. 105 × 71 × 32 mm·335 g으로 받침에 들어간다. '
        '두 포트를 함께 쓰면 5 V로 떨어지고, 켠 채 충전(패스스루)은 15 W로 고정돼 충전하면서 연주할 수 없다. 더 빨리 충전되는 대안은 NEXTU 2014TQPB(47,100원, 65 W 입력, 400 g).'))

# ---------------- 쓰임새: 새 줄 ----------------
UU['L57'] = ['cu', 'I/O 판 안쪽 포켓 1(USB-C 구멍이 밖을 향함)', '피아노의 전원 입력. 충전기·보조배터리와 20 V로 협상해 퓨즈 → 스위치 → 20 V 단자로 보낸다.', '조립 12 · 도면 9·10']
UU['L58'] = ['cu', 'CU 트레이 보스 4개 위 1', '20 V → 5.1 V. 출력 단자에 Pi용 USB-C 전원선(C24)과 허브 DC 선을 함께 물린다. 맞춘 뒤 노브를 고정한다.', '조립 12 · 도면 9·10']
UU['L59'] = ['cu', 'I/O 판 구멍 1', '20 V 쪽 전원 스위치. 앰프와 강압 모듈이 함께 켜지고 꺼진다. 끄기 전에 소프트웨어로 볼륨을 0으로 한다.', '조립 12 · 도면 9']
UU['L60'] = ['cu', 'PD 트리거 출력 + 선 1(예비 퓨즈 4)', '홀더 선 가운데를 잘라 트리거 + 출력과 스위치 사이에 납땜하고 수축튜브로 감싼다.', '조립 12 · 도면 9']
UU['L62'] = ['tool', '콘센트 1(피아노 벽 전원 겸 인두 전원)', '피아노를 벽 전원으로 쓸 때 USB-C 입력에 C23으로 잇는다. 포트는 하나만 쓴다. 제작 중에는 인두(T01)를 먹인다.', '조립 12 · 납땜 전반']
UU['L63'] = ['cu', '합판 1장 → 가운데 유닛 11장', '판매처 무료 재단으로 잘라 받아 목공본드(C21)로만 붙인다. 낮은 칸막이(172×57)는 CU 칸과 보조배터리 칸 사이에 쓴다.', '조립 12 · 도면 11']
UU['C22'] = ['cu', '보조배터리 → I/O 판 입력 1', '보조배터리 칸에서 낮은 칸막이 위 → CU 칸 → I/O 판 선 통과 구멍으로 빼서 USB-C 입력에 꽂는다.', '조립 12']
UU['C23'] = ['tool', '충전기 → I/O 판 입력 1', '벽 충전기에서 피아노 뒤 USB-C 입력까지. 제작 중에는 인두 전원선으로도 쓴다.', '조립 12 · 납땜 전반']
UU['C24'] = ['cu', '강압 모듈 → Pi 5 USB-C 1', '빨강 +·검정 −를 강압 모듈 출력 단자에 물리고 플러그를 Pi 5 전원 입력에 꽂는다.', '조립 12 · 도면 9']
ids = {l['line_id'] for k in ('base', 'consumable', 'tools') for l in B[k]}
assert ids == set(UU), (sorted(ids - set(UU)), sorted(set(UU) - ids))

# ---------------- 선택 항목 문장·부품표 메모 ----------------
TB = sum(map(sub, B['base']))
opt = {l['line_id']: l for l in B['optional']}
opt['O01']['why'] = (f'기본 구성 {TB:,}원(R26~R29 반영)에 더해도 {TB + sub(opt["O01"]):,}원으로 R21 안이다. 그래도 FluidSynth로 충분해 선택으로 둔다. '
                     '결제 시 부가세 10%가 붙을 수 있다. 사기 전에 체험판으로 Pi 5 지연(D8)을 확인한다(USB 동글이라 여유가 작다).')
opt['O05']['why'] = f'L01 대신 쓰면 +97,900원으로 기본 구성이 {TB + 97_900:,}원이 된다. R26 이후에도 한도 안이다.'
opt['O06']['why'] = f'PC에 슬롯이나 리더가 있으면 필요 없다. 넣어도 기본 구성이 {TB + sub(opt["O06"]):,}원으로 한도 안이다.'
opt['O02']['why'] = opt['O02']['why'].replace('4 Ω이라 TPA3110은 16 V 이하로 쓰므로 L06을 12V 3A 어댑터(엘레파츠 no=3862351, 7,290원)로 바꾼다(12 V·4 Ω 약 12.5 W/ch). 그러면 최대 음량은 삼미와 비슷하다(1 m 약 98 dB).',
                                              '4 Ω이라 TPA3110은 16 V 이하로 쓰므로 PD 트리거(L57)를 15 V로 바꾼다(뒷면 점퍼 납땜, 15 V·4 Ω 약 18 W/ch, 계산). 그러면 최대 음량은 삼미와 비슷하다(1 m 약 100 dB).').replace('(어댑터 −4,010원 별도)', '')
assert 'PD 트리거(L57)를 15 V' in opt['O02']['why']
B['budget_strategy'] = ('[R26~R29 반영 2026-09-25] 뒷공간을 뒷바(스피커 파트 2 + 가운데 유닛)로 채워 1254 × 410 mm 직사각형으로 하고, 전원을 USB-C PD 입력 하나(65 W 충전기 또는 보조배터리)로 바꿨다. '
                        '19 V 어댑터·DC 잭·Pi 어댑터·스피커 단자판·황동 스탠드오프가 빠지고 PD 트리거·강압 모듈·스위치·퓨즈·XT30·토글 래치·자석·6핀 커넥터·충전기(공구에서 옮김)·오꾸메 600×1200이 들어왔다. 합계는 보고서가 부품표에서 다시 계산한다.\n\n'
                        + B['budget_strategy'])
B['notes'] = ('[R26 2026-09-25] 새 전원·커넥터 부품의 가격·링크·이미지는 scratchpad/work_r26/(power·hw)/result.json과 엘레파츠 페이지(스위치·퓨즈·케이블, 브라우저로 확인)의 9/25 값이다. '
              '이전 부품표는 bom_all.before_r26.json.\n\n' + B['notes'])

l = find('base', 'L25')
l.update(role='앰프 입력 패드·PED 보드에 세우는 수 헤더(점퍼선 C07을 꽂는 자리) + 예비. 끝 부속 EXT 연결은 R26부터 JST-XH 6핀(L66)이다',
         design_ref="control_unit(R26) 앰프 입력·PED 보드, C07 점퍼",
         why='압착 공구 없이 점퍼선(C07)을 꽂을 자리를 만든다. 처음에는 끝 부속 EXT 1×6 수 커넥터용이었지만, R26으로 끝 부속은 걸림 턱이 있는 JST-XH(L66)로 바꿨다. 1줄이면 충분하고 1줄은 예비.')
UU['L25'] = ['cu', '앰프 입력 패드 3핀 + PED 보드 + 예비', 'CU 칸 기판 패드에 세워 점퍼선(C07)을 꽂는다. 필요한 길이로 부러뜨려 쓴다.', '조립 12']

json.dump(B, open(P, 'w'), ensure_ascii=False, indent=1)
json.dump(U, open(UP, 'w'), ensure_ascii=False, indent=1)
for k in ('base', 'consumable', 'tools', 'optional'):
    print(k, len(B[k]), f'{sum(map(sub, B[k])):,}')
