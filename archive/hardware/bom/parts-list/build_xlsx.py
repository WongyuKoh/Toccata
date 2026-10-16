"""Toccata 부품 목록(현재 설계: v4 W1 r4.5 건반 + v3.2 전자·오디오·본체) → docs/report/toccata-parts-list.xlsx
입력: rows.json (collect.py: toccata-purchase-list-v4.xlsx 의 v3.2 부품 + v4 r4 선택기 현재 안)
"""
import json, sys, re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = sys.argv[1] if len(sys.argv) > 1 else 'toccata-parts-list.xlsx'
D = json.load(open('rows.json'))
ROWS = D['rows']

# 공구: 드릴 손잡이 (v4 목록 145행, 나비엠알오 9/27 확인 — 드릴과 같은 판매처라 배송비 추가 없음)
ROWS.append(dict(code='T05', name='나비엠알오 탭 핸들 (사용범위 3~12 mm, 전장 200)', unit=5489, qty=1, url='https://www.navimro.com/g/179331/', b='공구', seller='나비엠알오', src='v4 r3 list'))
# 2단계 게임: 화면 출력 케이블 (2026-09-28 엘레파츠 상품 페이지 확인)
ROWS.append(dict(code='G01', name='[Raspberry Pi] 라즈베리파이4 공식 HDMI 케이블 PI-OFFICIAL-MICRO-HDMI-CABLE-1M (Micro HDMI → HDMI, 1m, 흰색)',
                 unit=17050, qty=1, url='https://www.eleparts.co.kr/goods/view?no=8250328', b='기본', seller='엘레파츠', src='game'))

# (그룹, 코드, 상품명에 들어 있는 글자, 짧은 이름, 용도)
G = [('제어 · 전원 (핵심)', [('L01', 'Raspberry Pi 5', 'Raspberry Pi 5 (2GB)', '피아노 음원(FluidSynth)과 리듬게임을 돌리는 중앙 컴퓨터'),
 ('L17', 'NEXTU', 'USB 허브 10포트 (전원형)', '모듈 7 + 페달을 Pi 5 한 포트로 모음'),
 ('L57', 'PD 트리거', 'PD 트리거 모듈 (HUSB238)', 'USB-C 전원 입력 → 20 V'),
 ('L58', 'XL4016', '강압 모듈 XL4016', '20 V → 5.1 V (Pi 5 · 허브 전원)'),
 ('L03', 'micro SD', 'microSD 32GB (SanDisk Ultra)', '운영체제 · 음원 · 게임 저장'),
 ('L02', '방열판', 'Pi 5 방열판 (4개 세트)', 'Pi 5 칩 방열'),
 ('L59', '로커 스위치', '로커 스위치', '피아노 전원 스위치'),
 ('L60', '휴즈 홀더', '퓨즈 홀더 (5×20 mm)', '20 V 선 보호'),
 ('L60', '지연형 퓨즈', '퓨즈 5 A 지연형 (5개)', '퓨즈 1 + 예비 4'),
 ('L62', '65W', '65 W PD 충전기', '벽 전원 (보조배터리 대신 쓸 때)')]),
 ('센서 · MCU · 기판', [('SEV2', 'RP2040', 'RP2040-Zero 마이크로컨트롤러', '모듈 7 + 페달 1: 센서 읽기 · 세기 계산 · USB-MIDI'),
 ('L20', 'DRV5055', '홀센서 TI DRV5055A2', '건반마다 1개, 건반 위치 측정 (88 + 페달 1 + 예비)'),
 ('L21', '5mm', '네오디뮴 자석 Ø5×2 N35', '건반 밑면에 1개씩, 센서가 읽는 자석'),
 ('SEV2', '멀티플렉서', '16채널 MUX 모듈 (CD74HC4067)', '센서 12 + 끝 부속 4를 ADC 1개로 차례로 읽음'),
 ('SE8', '5x7', '만능기판 5×7 cm', '모듈 제어 기판 7 + 페달 보드 1 (W1: 앞쪽 핀 홈 자리 비움)'),
 ('L22', '12x18', '만능기판 12×18 cm', '센서 기판 띠로 잘라 씀 (모듈 7 + 끝 부속 2)'),
 ('SE4', '100nF', '칩 콘덴서 100 nF (1206)', '센서마다 전원 잡음 제거 + MUX (97개 사용)'),
 ('L67', 'C3216-10UF', '칩 콘덴서 10 µF (1206, 50개)', '센서 기판 양 끝 · 끝 부속 전원 안정 (16개 사용, 회로도 △1·△3)'),
 ('SE7', '1단몰드', '핀헤더 1×40', 'MUX 모듈 7개 · RP2040-Zero 8개 핀 헤더 (312핀 → 9줄)'),
 ('L29', '1kΩ', '저항 1 kΩ (10개)', '앰프 입력 저음 차단 R701·R702 · 페달 R501·R551 (4개 사용)'),
 ('L29', '100kΩ', '저항 100 kΩ (10개)', '제어 기판 EXT 풀다운 R301~R303 · 페달 R502 (5개 사용)'),
 ('L29', '10kΩ', '저항 10 kΩ (10개)', '예비'),
 ('L29', '100Ω', '저항 100 Ω (10개)', '페달 링 급전 20 Ω (5개 병렬)'),
 ('L68', 'RC1206JR', '칩 저항 1 kΩ (1206, 10개)', '끝 부속 EL · ER 입력 직렬 저항 R401~R403 · R411 (기판 밑면, 4개 사용, 회로도 △13)')]),
 ('건반 액션 (W1: 시소 건반 + 무게 레버)', [('v4weight', '9T', '강철 평철 9T×19 (1 m 맞춤 재단)', '무게 레버 강철 블록 90개 (40 mm씩 잘라 씀, 개당 53.7 g)'),
 ('v4keyrod', '4mm', '스테인리스 봉 Ø4 (1 m) — 건반 봉', '건반 시소의 축 (모듈 7 + 끝 부속 2 + 예비 1 토막)'),
 ('v4levershaft', '4mm', '스테인리스 봉 Ø4 (1 m) — 레버 봉', '무게 레버가 매달리는 축 (건반 봉과 같은 봉)'),
 ('v4capstan', 'ISO7380', '캡스턴 나사 M3×6 버튼헤드 (SUS)', '건반 꼬리에서 레버를 들어 올리는 나사, 높이 조정 (88 + 예비)'),
 ('L31', 'XHHD', 'M3 육각 너트 (강철)', '캡스턴 나사 너트 96 + 스피커 브래킷 4'),
 ('v4pins', '다올핀', '밸런스 핀 Ø2×12 (SUS, 100개)', '건반 뒤쪽 좌우 위치를 잡는 핀 (88 + 예비)'),
 ('v4tspring', 'C-UA90R5', '비틀림 스프링 미스미 C-UA90R5-3-0.5 (기성품)', '레버마다 1개 (88 + 예비 12) — 두 다리를 22.3 / 8.0 mm로 잘라 끼움 (r4.5)'),
 ('v4felt2', '2mm', '양모 펠트 2 mm (20×30 cm)', '캡스턴 띠 · 앞 멈춤 · 키퍼 펠트'),
 ('v4felt2', '1mm', '양모 펠트 1 mm (20×30 cm)', '업스톱 패드 윗면 · 쉼 펠트 (0.5T와 겹쳐 1.5T)'),
 ('v4pu', 'PORON', '포론(PORON) 폼 5T 점착 (100×100)', '업스톱 패드 — 설계 6T 대신 5T: 패드 바 쐐기를 1.0 mm 두껍게 출력, 단계 0 시험 먼저'),
 ('v4pu', '하네나이트', '충격흡수재 하네나이트 1T (170×245)', '앞 펠트 밑 완충층 (NBR 고무, 단계 0 시험으로 확인)'),
 ('MEV1', '칼라펠트지', '접착 펠트 0.5T (30×45 cm)', '건반 노치 · 핀 홈 · 가이드 탭 부싱 천, 쉼 펠트 한 겹')]),
 ('오디오 (스피커 · 앰프)', [('L53', 'XH-A232', '앰프 보드 XH-A232 (TPA3110)', '스피커 구동, 채널당 약 21 W'),
 ('L07', 'CW-100B25', '스피커 유닛 삼미 CW-100B25 (4인치 8 Ω)', '좌우 내장 스피커'),
 ('L51', 'Apple', 'Apple USB-C 헤드폰 어댑터', 'USB DAC (디지털 → 아날로그 소리)'),
 ('L52', 'IH190', 'USB-C → USB-A 젠더', '어댑터를 Pi 5 USB 포트에 연결'),
 ('L15', 'PJ-313', '3.5 mm 스테레오 잭 PJ-313', '헤드폰 잭(꽂으면 스피커 차단) · 앰프 입력 · 페달 잭'),
 ('L56', '1uF', '적층 세라믹 콘덴서 1 µF', '앰프 입력 저음 차단 필터'),
 ('L61', 'XT30U-M', 'XT30 커넥터 수 (선 포함)', '스피커 연결 — 앰프 쪽'),
 ('L61', 'XT30U-F', 'XT30 커넥터 암 (선 포함)', '스피커 연결 — 스피커 쪽'),
 ('L10', '400×1200', '오꾸메 합판 400×1200 (무료 재단)', '스피커 상자 2개'),
 ('L12', '구름솜', '흡음솜 300 g', '스피커 상자 흡음재')]),
 ('본체 구조 · 결합', [('L63', '600×1200', '오꾸메 합판 600×1200 (무료 재단)', '가운데 유닛 상자 (건반 보관함 · 제어부 · 배터리 칸)'),
 ('L64', '매미고리', '토글 래치 (SUS)', '가운데 유닛 ↔ 스피커 파트 잠금'),
 ('L65', '8mm', '네오디뮴 자석 Ø8×3', '가운데 유닛 뚜껑 고정'),
 ('L66', 'JST-XH', 'JST-XH 6핀 연장선', '끝 부속 ↔ 모듈 센서 선 커넥터'),
 ('L14', '고무발', '고무발 28×5', '뒷바 받침 (5 mm 띄움, 진동 분리)'),
 ('L42', '댐퍼', 'M3 방진 댐퍼·그로밋 (20개)', '끝 부속 ↔ 스피커 브래킷 방진'),
 ('MEV1', 'EVA', 'EVA 폼 3T (330×490)', '모듈 · 끝 부속 바닥 시트, 스피커 가스켓'),
 ('L34', 'M3 × 10', '렌치볼트 M3×10 (SUS)', '센서 바 · 제어부 부품 · 토글 래치 고정'),
 ('L35', 'M3 × 6', '렌치볼트 M3×6 (SUS)', '제어 기판 고정'),
 ('L47', 'M2.5', '렌치볼트 M2.5×6 (SUS)', 'Pi 5 고정'),
 ('L36', '와셔', '와셔 M4 (SUS)', '고무발 피스 받침'),
 ('L49', '13mm', '직결피스 13 mm', '뒷바 출력 부품 · 고무발 고정'),
 ('L49', '16mm', '직결피스 16 mm', '스피커 유닛 고정'),
 ('L49', '19mm', '직결피스 19 mm', '스피커 그릴 고정')]),
 ('소모품', [('CT2', '화이트(30106) 스풀', 'PETG 필라멘트 흰색 1 kg (스풀)', '백건 출력'),
 ('CT2', '화이트(30106) 리필', 'PETG 필라멘트 흰색 1 kg (리필)', '백건 출력'),
 ('CT2', '블랙', 'PETG 필라멘트 검정 1 kg (스풀)', '프레임 · 레버 캐리어 · 흑건 등'),
 ('CT2+', '추가', 'PETG 필라멘트 1 kg 추가 (흰색 또는 검정)', '뒷바 출력 부품 · 여분'),
 ('C04', 'NA993', 'USB-A → USB-C 케이블 1 m', '모듈 7 + 페달 → USB 허브'),
 ('C05', '2651', '리본 케이블 16P (1 m)', '센서 기판 → 제어 기판'),
 ('SE12', '2651', '리본 케이블 16P (1 m) 추가', '기판 배선용 가닥'),
 ('C13', '스피커케이블', '스피커 케이블 16AWG 7 m', '앰프 → 스피커, 20 V 전원선'),
 ('C14', '1.5M', '3.5 mm 스테레오 케이블 1.5 m', '어댑터 → 헤드폰 잭 → 앰프'),
 ('C22', 'CPD606', 'USB-C PD 케이블 0.6 m', '보조배터리 → 피아노'),
 ('C23', 'CPD62', 'USB-C PD 케이블 2 m', '충전기 → 피아노'),
 ('C24', 'MAXTEK', 'USB-C 전원 케이블 (제작용)', '강압 모듈 → Pi 5 전원'),
 ('C10', '열수축', '열수축 튜브 세트', '선 이음 절연'),
 ('C11', '캡톤', '캡톤 테이프', '기판 절연'),
 ('C12', '케이블타이', '케이블 타이 (100개)', '케이블 정리'),
 ('CT5', '유연납', '실납 0.8 mm 50 g', '손 납땜 (약 1,500곳)'),
 ('ME8', '순간접착제', '순간접착제 5 g', '자석 고정'),
 ('v4msbond', '슈퍼X', 'MS 폴리머 탄성 접착제 세메다인 슈퍼X 흰색 20 mL', '강철 블록을 레버 캐리어에 붙임 (필요 약 14 mL, 흰색·검정만 — 투명은 PET 접착이 약함)'),
 ('ME9', '양면테이프', '종이 양면테이프', 'EVA 시트 · 펠트 부착'),
 ('SP6', '본드', '목공 본드 800 g', '합판 상자 접착'),
 ('ME14', '텅스텐', '텅스텐 퍼티 (22 g)', '건반별 무게 미세 조정 (필요할 때만)'),
 ('v4shim', 'OHP', 'OHP 필름 (A4 20매)', '0.1 mm 심 — 업스톱 시점 조정'),
 ('v4graphite', '흑연', '흑연 가루 30 ml', '캡스턴 펠트 마찰 줄이기')])]
EXCL = [('페달', [('L43', '듀로', '서스테인 페달 (듀로, 스위치형)', '홀센서로 개조한 댐퍼 페달 (하프페달)'), ('L50', '3M', '3.5 mm 스테레오 케이블 3 m', '페달 신호선')]), ('소프트웨어 (무료)', [('L45', 'FluidSynth', 'FluidSynth 2.6.1', '피아노 음원 엔진'), ('L46', 'Salamander', 'Salamander Grand Piano V3', '그랜드 피아노 샘플 음원')]), ('2단계 리듬게임', [('G01', 'MICRO-HDMI', 'Micro HDMI → HDMI 케이블 1 m (라즈베리파이 공식)', 'Pi 5 → 모니터 · TV로 게임 화면 출력 (모니터는 가진 것 사용)')]), ('공구', [('T01', 'PINECIL', '납땜 인두 Pinecil V2', '손 납땜'), ('T02', 'Stand', '인두 거치대', '인두 받침'), ('T03', 'SILICONE', 'USB-C 실리콘 케이블 1 m', '인두 ↔ 65 W 충전기'), ('CT11', 'DT-832', '디지털 멀티미터', '통전 · 전압 확인'), ('CT21', '스트리퍼', '정밀 스트리퍼', '가는 선 피복 벗기기'), ('CT13', '니퍼', '니퍼 5인치', '리드 · 선 자르기'), ('CT12', '캘리퍼', '버니어 캘리퍼스 200 mm', '치수 측정 (출력물 · 봉 · 펠트)'), ('T11', '2.5mm', '육각 렌치 2.5 mm', 'M3 렌치볼트 조이기'), ('T04', '2 mm', '육각 렌치 2 mm', '캡스턴 나사 높이 조정'), ('v4wirecut', 'FKN-150G', '경선용 니퍼 (후지야 FKN-150G)', '미스미 스프링 다리 200번 자르기 (지금 니퍼는 구리선용)'), ('v4drill4', 'SD 4.0', 'HSS 드릴 Ø4.0', '레버 허브 · 핀 보스 구멍 다듬기 (약 130구멍)'), ('T05', '탭 핸들', '탭 핸들 (3~12 mm)', 'Ø4.0 드릴을 손으로 돌리는 손잡이 (전동 드릴이 있으면 뺀다)'), ('v4cuttools', '쇠톱(대)', '쇠톱 300 mm', '강철 블록 90개 · 봉 자르기'), ('v4cuttools', '쇠톱날', '쇠톱날 12인치', '쇠톱 교체 날'), ('v4cuttools', '평줄', '평줄', '절단면 다듬기'), ('v4cuttools', '바이스', '탁상 바이스', '자를 때 고정')])]
# 수량 바꿈: 회로도(hardware/pcb README, 2026-09-28) — RP2040-Zero를 핀 헤더로 세움: 18핀 × 8장 = 144핀 → 1×40 4줄 추가
QTY = {('SE7', '1단몰드'): 9}
DROP = [('L39', '3mm', 'W1 r4.1 설계에 3T 펠트를 쓰는 곳이 없음 (앞 멈춤·키퍼는 2T)')]

used = set()
def find(code, key):
    hits = [i for i, r in enumerate(ROWS) if r['code'] == code and key.lower() in r['name'].lower() and i not in used]
    if len(hits) != 1:
        raise SystemExit(f'match {code}/{key}: {len(hits)} hits')
    used.add(hits[0]); return ROWS[hits[0]]

groups = []
for gname, items in G:
    lst = []
    for code, key, short, use in items:
        r = find(code, key)
        if (code, key) in QTY: r = dict(r, qty=QTY[(code, key)])
        lst.append(dict(short=short, use=use, qty=r['qty'], unit=r['unit'], url=r.get('url') or '', full=r['name'], seller=r['seller'], b=r['b']))
    groups.append((gname, lst))
excluded = []
for gname, items in EXCL:
    tot = 0
    for code, key, short, use in items:
        r = find(code, key); tot += r['qty'] * r['unit']
    excluded.append((gname, tot))
dropped = []
for code, key, why in DROP:
    r = find(code, key); dropped.append((r, why))
left = [ROWS[i] for i in range(len(ROWS)) if i not in used]
if left:
    raise SystemExit('unassigned: ' + str([(r['code'], r['name'][:40]) for r in left]))

# 배송비는 목록에서 뺀다(사용자 요청 2026-09-28). 참고 금액만 계산해 주에 적는다.
def norm(s):
    s = re.sub(r'\s*\(.*$', '', s or '').strip()
    return {'다나와 최저가': '다나와 최저가 판매처', 'Bambu Lab': 'Bambu Lab KR 공식 스토어', '나사코리아 nasakorea.com': '나사코리아'}.get(s, s)
sellers = {norm(it['seller']) for _, lst in groups for it in lst}
ship_ref = sum(s_['fee'] or 0 for s_ in D['ships'] if norm(s_['seller']) in sellers)
CORE = {'Raspberry Pi 5 (2GB)', 'RP2040-Zero 마이크로컨트롤러', '홀센서 TI DRV5055A2', '16채널 MUX 모듈 (CD74HC4067)'}
# ---------------------------------------------------------------- workbook
wb = Workbook(); ws = wb.active; ws.title = '부품 목록'
F = 'Apple SD Gothic Neo'
thin = Side(style='thin', color='D0D4DA')
BRD = Border(left=thin, right=thin, top=thin, bottom=thin)
HFILL = PatternFill('solid', fgColor='16181D'); GFILL = PatternFill('solid', fgColor='EEF0F3'); SFILL = PatternFill('solid', fgColor='FBE9E4')
BLUE = Font(name=F, size=10, color='0000FF'); BODY = Font(name=F, size=10); BOLD = Font(name=F, size=10, bold=True)
HEAD = ['No', '부품명', '수량', '용도', '단가(원)', '예상 가격(원)', '구매 링크', '판매처 · 상품명 (참고)']
WID = [5, 38, 7, 46, 11, 13, 46, 60]
ws['A1'] = 'Toccata 부품 목록 — 프로젝트 제작에 필요한 부품 (배송비 · 공구 · 2단계 게임 · 소프트웨어 · 페달 제외)'; ws['A1'].font = Font(name=F, size=14, bold=True)
ws['A2'] = ('기준: 2026-09-29 현재 설계 — 건반 액션 v4 W1(r4.5: 시소 건반 + 무게 레버) + v3.2 센서·전자·오디오·본체. '
            '가격은 판매처 페이지 확인값(2026-09-24~28, VAT 포함, 원). 3D 프린터는 포함하지 않는다.')
ws['A3'] = '사용법: 파란 글씨(수량·단가)만 고치면 예상 가격·소계·합계가 다시 계산된다. 예상 가격 = 수량 × 단가. 구매 링크는 한 번 누르면 열린다. 굵은 글씨 = 핵심 부품(1번 묶음 맨 위 Raspberry Pi 5, 2번 묶음 맨 위 RP2040-Zero · 홀센서 · MUX).'
for c in ('A2', 'A3'): ws[c].font = Font(name=F, size=9, color='555B66')
HR = 5
for j, h in enumerate(HEAD, 1):
    c = ws.cell(HR, j, h); c.font = Font(name=F, size=10, bold=True, color='FFFFFF'); c.fill = HFILL
    c.alignment = Alignment(horizontal='center', vertical='center'); c.border = BRD
for j, w in enumerate(WID, 1): ws.column_dimensions[get_column_letter(j)].width = w
r = HR + 1; n = 0; sub_cells = []; flat = []; pine_row = None
for gi, (gname, lst) in enumerate(groups, 1):
    ws.cell(r, 1, f'{gi}. {gname}').font = BOLD
    for j in range(1, 9): ws.cell(r, j).fill = GFILL; ws.cell(r, j).border = BRD
    r += 1; first = r
    for it in lst:
        n += 1
        vals = [n, it['short'], it['qty'], it['use'], it['unit'], f'=C{r}*E{r}', it['url'], (it['seller'] + ' · ' + it['full']) if it['full'] else it['seller']]
        for j, v in enumerate(vals, 1):
            c = ws.cell(r, j, v); c.border = BRD
            c.font = BLUE if j in (3, 5) else BODY
            c.alignment = Alignment(vertical='top', wrap_text=j in (2, 4, 7, 8), horizontal='center' if j in (1, 3) else None)
            if j in (5, 6): c.number_format = '#,##0'
        if it['short'] in CORE: ws.cell(r, 2).font = BOLD
        if it['url']:
            ws.cell(r, 7).hyperlink = it['url']; ws.cell(r, 7).font = Font(name=F, size=10, color='1F5FD8', underline='single')
        flat.append(dict(no=n, group=gname, **it))
        r += 1
    last = r - 1
    ws.cell(r, 4, f'{gname} 소계').font = BOLD
    c = ws.cell(r, 6, f'=SUM(F{first}:F{last})'); c.font = BOLD; c.number_format = '#,##0'
    for j in range(1, 9): ws.cell(r, j).fill = SFILL; ws.cell(r, j).border = BRD
    sub_cells.append((gname, f'F{r}')); r += 1
r += 1
ws.cell(r, 2, '합계').font = Font(name=F, size=12, bold=True); r += 1
SUMMARY = [
    ('피아노 부품 (1~5)', '+'.join(c for g, c in sub_cells[:5])),
    ('소모품 (6)', sub_cells[5][1]),
]
srow = {}
for label, ref in SUMMARY:
    ws.cell(r, 4, label).font = BOLD
    c = ws.cell(r, 6, f'={ref}'); c.number_format = '#,##0'; c.font = BOLD; srow[label] = r; r += 1
ws.cell(r, 4, '전체 합계 (부품 + 소모품)').font = Font(name=F, size=11, bold=True)
c = ws.cell(r, 6, f'=SUM(F{r-2}:F{r-1})'); c.number_format = '#,##0'; c.font = Font(name=F, size=11, bold=True); total_row = r; r += 2
notes = [
    '· 이 목록에 넣지 않은 것(사용자 요청): ' + ', '.join(f'{g} {t:,}원' for g, t in excluded) + f', 배송비 약 {ship_ref:,}원(판매처별 1회). 페달 보드 전자 부품(RP2040-Zero 1개 · 5×7 기판 1장 · 홀센서 1개 · 페달 잭 · 저항)은 공용 부품이라 위 목록 수량에 그대로 들어 있다.',
    '· 목록에서 뺀 중복 · 불필요 항목: ' + '; '.join(f"{d[0]['name'][:40]} — {d[1]}" for d in dropped) + '.',
    '· 비틀림 스프링은 직접 감지 않고 한국미스미 경제형 기성품 C-UA90R5-3-0.5(SUS304-WPB, 내경 5 · 선경 0.5 · 3권 · 암 각 90°)를 산다(2026-09-28 확인: 100개 이상 개당 282원 + VAT). 두 다리를 경선용 니퍼로 긴 다리 22.3 / 짧은 다리 8.0 mm로 자른다(r4.5: 짧은 다리를 허브의 가둠 홈에 넣어 코일이 봉에 닿지 않게 함). 단계 0 시험 8(쉼 4.19 / 바닥 6.03 N·mm ±15%)과 시험 13(가둠 홈 넣기)으로 확인한다. 한국미스미는 회원 가입 후 신용카드로 주문한다(개인 가능).',
    '· 강철 블록 접착제는 에폭시가 아니라 MS 폴리머 탄성 접착제(세메다인 슈퍼X 흰색)다. 에폭시는 온도 변화에 떨어져 설계(r4.4)와 맞지 않는다. 공기 중 습기로 굳어 닫힌 0.1 mm 틈 가운데는 며칠 걸릴 수 있어 단계 0 시험 20으로 확인한다.',
    '· PORON 폼은 판매처에 5T만 있어 설계 6T 대신 쓴다. 패드 바 6종의 쐐기를 1.0 mm 두껍게 출력해야 하고, 등급(25% 압축 0.36 MPa) 표기가 없어 단계 0 시험 1·2(반발 e ≤ 0.07, 강성)를 먼저 한다.',
    '· 단계 0 측정 도구(다이얼 게이지, 용수철 저울, 0.1 g 저울)와 커터칼 · 사포는 목록에 없다 — 빌리거나 가진 것을 쓴다. 봉 지름(3.97~4.00 mm)은 받은 뒤 확인한다.',
    '· 원본: docs/report/toccata-purchase-list-v4.xlsx (2026-09-29: v3.2 절감 선택 + v4 r4.5 + 회로 줄 변경 + 미스미 스프링 · MS 폴리머 접착제 · 경선 니퍼). 핀헤더 소켓은 회로 검토에서 빠졌다(끝 부속 EXT는 JST-XH를 패드에 직접 납땜). 건반 액션은 단계 0 시험 결과에 따라 바뀔 수 있다.',
]
for t in notes:
    ws.cell(r, 2, t).font = Font(name=F, size=9, color='555B66'); r += 1
ws.freeze_panes = f'A{HR+1}'
ws.page_setup.orientation = 'landscape'; ws.page_setup.paperSize = ws.PAPERSIZE_A4
ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0; ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.print_title_rows = f'{HR}:{HR}'
wb.save(OUT)
json.dump(dict(groups=[dict(name=g, items=l) for g, l in groups], flat=flat, excluded=[dict(name=g, total=t) for g, t in excluded], ship_ref=ship_ref, dropped=[dict(name=d[0]['name'], why=d[1]) for d in dropped], ),
          open('parts_final.json', 'w'), ensure_ascii=False, indent=1)
print('rows', n, 'groups', len(groups), 'saved', OUT, 'excluded', excluded, 'ship_ref', ship_ref)
