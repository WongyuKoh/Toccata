"""Toccata v4 재료 목록 엑셀 (현재 목록 = 구매 목록 v3.2 선택 + v4 3차 건반 액션).

v3.2 구매 목록과 같은 형식: 판매처별 묶음, 파란 글씨 입력, 구매 O/X, 소계·합계 SUMIFS.
"""
import json, os, re
from collections import OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

HERE = os.path.dirname(os.path.abspath(__file__))
OUTX = '/Users/kwg/Desktop/mydrive/project/Toccata/docs/report/toccata-purchase-list-v4.xlsx'
old = json.load(open(os.path.join(HERE, 'data_old.json')))
v4 = json.load(open(os.path.join(HERE, 'data_v4.json')))
BK = {'base': '기본', 'consumable': '소모품', 'tool': '공구'}

# ---------------------------------------------------------------- sections
SECTION_ORDER = ['아이씨뱅큐', '엘레파츠', '11번가', '메카솔루션', '파츠파츠 직영몰', 'Bambu Lab KR 공식 스토어', '다나와 (최저가 판매처)',
                 '동진나무공장', '대건상사', '알씨뱅크', '철물박사', '스튜디오분트', '피아노모아', 'Apple Store 온라인', 'AliExpress',
                 'PINE STORE (Pine64 공식)', '무료 (다운로드)']
THR = {'아이씨뱅큐': (50000, 2700, True, 'base'), '엘레파츠': (60000, 3000, True, 'consumable'), 'Bambu Lab KR 공식 스토어': (70000, 3000, False, 'consumable')}
THR['나비엠알오'] = (50000, 3300, True, 'base')  # 10/1 L2 고침: 기본 3,300원, 공급가 5만 원(VAT 별도) 이상 무료 — 선택기 SHIP['O:나비엠알오']와 같은 규칙
OLD_FEES = {'세운상가새한음향': (4000, 'base'), '두유레디': (3000, 'base'), '상우아트': (3000, 'base'), '오공 본드 판매처': (2500, 'consumable'),
            '굿나잇몰': (3500, 'base'), '메카솔루션': (3000, 'base'), '파츠파츠': (3000, 'base'), '다나와 최저가 판매처': (3000, 'base'),
            '대건상사': (2500, 'base'), '알씨뱅크': (3500, 'base'), '철물박사': (3000, 'base'), '스튜디오분트': (3000, 'base'),
            '피아노모아': (3000, 'base'), 'PINE STORE': (16200, 'tool')}


def section_of(it, old_row=None):
    if old_row:
        return old_row
    s = it.get('store') or ''
    for k in ('아이씨뱅큐', '엘레파츠', '스튜디오분트', '대건상사'):
        if k in s:
            return k
    if s.startswith('11번가') or '굿나잇몰' in s:
        return '11번가'
    n = re.sub(r'\s*\(.*$', '', s).strip()
    return n or '견적 필요 (주문 제작)'


def seller_of(it):
    s = it.get('store') or ''
    if s.startswith('11번가 '):
        return re.sub(r'\s*\(.*$', '', s[4:]).strip()
    return re.sub(r'\s*\(.*$', '', s).strip()


# old rows keep their original section: rebuild map code -> section from build_data rows
import importlib.util, io, contextlib
spec = importlib.util.spec_from_file_location('bd', os.path.join(HERE, 'build_data.py'))
with contextlib.redirect_stdout(io.StringIO()):
    bd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bd)
ROWSEC = {(r['code'], r['name']): (r['section'], r['seller']) for r in bd.ROWS}

rows = OrderedDict()  # section -> list of dict
def add(sec, d):
    rows.setdefault(sec, []).append(d)

STATUS_CHANGED = {'L31': 'v4 수량 변경 (75 → 100)', 'L36': 'v4 수량 변경 (60 → 20)', 'CT2': '', 'T04': 'v4 신규'}
STATUS_CHANGED.update({'L67': 'v4 신규 (회로 검토)', 'L68': 'v4 신규 (회로 검토)', 'SE7': 'v4 수량 변경 (5 → 9, 회로 검토)'})
CIRCUIT_TEXT = {'L29', 'C05', 'L66', 'C04', 'L56', 'C10', 'C12'}  # 2026-09-28 circuit review: usage text only (C10·C12: EXT 헤더 빠짐)
STATUS_CHANGED['L35'] = 'r4.5 확인: 매단 보스, 밑에서 조임, 14 + 예비 6 (수량 그대로)'
# ---- 10/1 L2 (한 몸 뒷바) + 터치스크린 3판
STATUS_CHANGED.update({
    'L35': '10/1 L2 수량 변경 (20 → 24, 앰프 4)', 'L34': '10/1 L2 수량 변경 (54 → 28)',
    'C22': '10/1 L2 교체: 곧은 0.6 m → ㄱ자 0.5 m',
    **{k: '10/1 L2 신규' for k in ('L69', 'L70', 'L71', 'L72', 'L73', 'L74', 'L75', 'L76', 'L77', 'L78', 'L79', 'C25')},
    **{k: '10/1 L2: 용도 수정' for k in ('L10', 'L07', 'SP6', 'L14', 'L42', 'L65', 'L12', 'L17', 'L36', 'L47', 'L58', 'C11', 'T01', 'CT2+')},
})
for _k in ('L73', 'C25'):
    STATUS_CHANGED[_k] += ' · CAD 확인 필요'
STATUS_CHANGED['L36'] = 'v4 수량 변경 (60 → 20) · 10/1 L2: 용도 수정'
# ---- 10/1 L2 고침 (검토 반영)
STATUS_CHANGED.update({
    'C22': '10/1 L2 교체: 곧은 0.6 m → ㄱ자 0.5 m · 개별 배송비 3,000원(따로 줄)',
    'C24': '10/1 L2 교체: 곧은 MT666 → 측면 꺾임 C 20 cm (A 쪽을 잘라 씀) · CAD 확인 필요',
    'L74': '10/1 L2 신규 · 판매처 엘레파츠 → 나비엠알오(고침, 나비엠알오 배송비 0)',
    'L17': '10/1 L2: 용도 수정 · CAD 확인 필요 (DC 플러그 ㄱ자)',
    **{k: '10/1 L2: 용도 수정 (I/O 판·CU 트레이 → 뒤판 출력물·J702)' for k in ('L57', 'L59', 'L15', 'L53', 'C14', 'L62')},
    'SP6': '10/1 L2: 용도 수정 (판 가공은 따로)', 'T01': '10/1 L2: 용도 수정 (인서트 12개)',
})
STATUS_CHANGED['L73'] = '10/1 L2 신규 · CAD 확인 필요 (길이·구멍 지름)'


def st_l2(it, st):
    """10/1 L2: per-row status where one code has several rows (L49 13/19 mm) or keeps an older circuit-review status."""
    n = str(it['name'])
    if it['code'] == 'L49':
        return '10/1 L2 수량 변경 (54 → 20)' if '13mm' in n else ('10/1 L2: 용도 수정 (19 mm 이하)' if '19mm' in n else st)
    if it['code'] in ('C04', 'C10'):
        return st + ' · 10/1 L2 메모'
    return st
ST_V4 = {'v4wood': '10/1 L2 고침: 선택 공구(기본 X) — 전동 드릴·비트를 가졌다고 가정', 'v4touch': 'R31 신규: 터치스크린 (9/30 추가, 10/1 Waveshare 7-DSI-TOUCH-C 선택) · 10/1 3판·L2: 리본 길·나사 값 고침', 'v4tspring': 'r4.4 변경: 미스미 기성품 (9/28 결정)', 'v4msbond': 'r4.4 고침 2b: 강철 블록 접착 — 에폭시 → MS 폴리머 (9/29)', 'v4wirecut': 'r4.4 신규: 스프링 다리 자르기',
         'v4capstan': 'v4 신규 · 너트는 L31에서 한 번만 셈 (9/28 고침)'}
for c in old['cards']:
    for it in c['options'][0]['items']:
        sec, sel = ROWSEC.get((it['code'], it['name']), (section_of(it), it.get('store')))
        st = STATUS_CHANGED.get(it['code'], '유지')
        if it['code'] in CIRCUIT_TEXT or (it['code'] == 'SEV2' and 'RP2040' in it['name']):
            st = '회로 검토: 용도 수정'
        if it['code'] == 'CT2' and '블랙' in it['name'] and it['qty'] == 5:
            st = 'v4 수량 변경 (3 → 5)'
        if it['code'] == 'T04':
            sec, sel = '11번가', '굿나잇몰'
        st = st_l2(it, st)
        own = (it['ship'][2:], it.get('ship_fee') or 0) if str(it.get('ship') or '').startswith('O:엘레파츠') else None  # 10/1 L2 고침: 개별 배송비
        add(sec, dict(name=it['name'], unit=it['unit'], qty=it['qty'], role=it.get('role', ''), url=it.get('url', ''), b=it['b'],
                      ox='O', seller=sel, code=it['code'], note=it.get('note', ''), st=st, ver='확인', own=own))
for c in v4['cards']:
    o = c['options'][0]
    for it in o['items']:
        sec = section_of(it)
        add(sec, dict(name=it['name'], unit=it['unit'], qty=it['qty'], role=c['title'] + ' — ' + (it.get('spec') or ''), url=it.get('url', ''),
                      b=it['b'], ox='X' if c.get('default') == 'none' else 'O', seller=seller_of(it), code=c['id'],
                      note=(it.get('note') or '')[:400], st=ST_V4.get(c['id']) or ('v4 신규' + (' · 4차에서 바뀔 수 있음' if c.get('r4') else '') + (' · 선택 부품(기본 X)' if c.get('default') == 'none' else '')),
                      ver='확인' if it.get('verified') else '미확인', fee=it.get('ship_fee') or 0))

order = [s for s in SECTION_ORDER if s in rows] + [s for s in rows if s not in SECTION_ORDER]

# ---------------------------------------------------------------- workbook
F = '맑은 고딕'
thin = Side(style='thin', color='FFBFBFBF')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WON = '#,##0\\원;\\-#,##0\\원;\\-'
wb = Workbook()
ws = wb.active
ws.title = '구매목록'
ws['A1'] = 'Toccata v4 재료 목록 — 구매 목록(v3.2 절감 선택) + v4 건반 액션(r4.5) + 뒷바 L2·터치스크린 3판(10/1)'
ws['A1'].font = Font(name=F, size=15, bold=True)
ws['A2'] = ('기준: docs/report/toccata-purchase-list.xlsx(v3.2, 고르신 절감 22개) + v4 W1+ 4차 설계 부품(2026-09-27~28 판매처 조사·링크 재검증) + 회로 검토(2026-09-28, hardware/pcb) + r4.4 스프링·니퍼(2026-09-28) + 블록 접착제 MS 폴리머(2026-09-29) + 한 몸 뒷바 L2·터치스크린 3판(2026-10-01, cad/spec/body_L2.json·cad/README.md·touchscreen/rev3). '
            '가격은 VAT·할인 반영(원). 구분: 기본 = 피아노에 들어가는 부품, 소모품 = 제작 중 쓰는 재료, 공구 = 제작용 공구')
ws['A2'].font = Font(name=F, size=9, color='FF595959')
ws['A3'] = ('사용법: 파란 글씨(단위당 가격·수량·구매 O/X)만 고친다. X로 바꾸면 소계·최종 금액에서 빠진다(줄이 회색). '
            '가격 확인이 "미확인"인 줄은 견적·추정가다.')
ws['A3'].font = Font(name=F, size=9, color='FF595959')
HEAD = ['No', '부품명', '단위당 가격(원)', '수량', '용도', '예상 가격(원)', '구매 링크', '구분', '구매(O/X)', '판매자', '부품 코드', '비고', 'v4 상태', '가격 확인']
for j, h in enumerate(HEAD, 1):
    c = ws.cell(5, j, h)
    c.font = Font(name=F, size=10, bold=True, color='FFFFFFFF')
    c.fill = PatternFill('solid', fgColor='FF1F3864')
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    c.border = BORDER
widths = [5, 44, 14, 7, 62, 15, 48, 8, 9, 16, 11, 36, 22, 9]
for j, w in enumerate(widths, 1):
    ws.column_dimensions[chr(64 + j)].width = w
ws.freeze_panes = 'C6'

r = 6
n = 0
sec_ranges = []  # (section, first, last_incl_ship, subtotal_row)
ox_ranges = []
for sec in order:
    ws.cell(r, 1, '■ ' + sec).font = Font(name=F, size=11, bold=True, color='FF1F3864')
    for j in range(1, 15):
        ws.cell(r, j).fill = PatternFill('solid', fgColor='FFD9E2F3')
        ws.cell(r, j).border = BORDER
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=14)
    r += 1
    first = r
    fees = OrderedDict()
    for d in rows[sec]:
        n += 1
        vals = [n, d['name'], d['unit'], d['qty'], d['role'], f'=C{r}*D{r}', d['url'], BK[d['b']], d['ox'], d['seller'], d['code'], d['note'], d['st'], d['ver']]
        for j, v in enumerate(vals, 1):
            c = ws.cell(r, j, v)
            c.font = Font(name=F, size=10, color='FF0000FF' if j in (3, 4, 9) else ('FF0563C1' if j == 7 else None))
            c.border = BORDER
            c.alignment = Alignment(wrap_text=j in (2, 5, 7, 12, 13), vertical='top', horizontal='center' if j in (4, 8, 9, 14) else None)
            if j in (3, 6):
                c.number_format = WON
        if d['url']:
            ws.cell(r, 7).hyperlink = d['url']
        # shipping bookkeeping
        s = d['seller'] or ''
        if d.get('own') and d['own'][1]:  # 10/1 L2 고침: 무료배송 기준과 따로 붙는 상품별 배송비(엘레파츠 해외재고 개별 배송비)
            fees[d['own'][0]] = (d['own'][1], d['b'])
        if sec in THR:
            fees[sec] = None
        else:
            hit = next((k for k in OLD_FEES if k in s or k in sec), None)
            if hit:
                fees.setdefault(hit, OLD_FEES[hit])
            elif d.get('fee'):
                prev = fees.get(s)
                fees[s] = (max(d['fee'], prev[0] if prev else 0), d['b'])
        r += 1
    last_item = r - 1
    for key, fv in fees.items():
        n += 1
        if fv is None:
            thr, fee, vat, b = THR[sec]
            expr = f'SUMIFS(F{first}:F{last_item},I{first}:I{last_item},"O")' + ('/1.1' if vat else '')
            unit = f'=IF({expr}<{thr},{fee},0)'
        else:
            unit, b = fv[0], fv[1]
            if not unit:
                n -= 1
                continue
        vals = [n, f'배송비 — {key}', unit, 1, '배송비', f'=C{r}*D{r}', '', BK[b], 'O', None, None, '', '', '']
        for j, v in enumerate(vals, 1):
            c = ws.cell(r, j, v)
            c.font = Font(name=F, size=10, color='FF0000FF' if j in (3, 4, 9) else None)
            c.border = BORDER
            if j in (3, 6):
                c.number_format = WON
        r += 1
    last = r - 1
    ox_ranges.append(f'I{first}:I{last}')
    ws.cell(r, 2, f'{sec} 소계').font = Font(name=F, size=10, bold=True)
    ws.cell(r, 6, f'=SUMIFS(F{first}:F{last},I{first}:I{last},"O")').font = Font(name=F, size=10, bold=True)
    ws.cell(r, 6).number_format = WON
    for j in range(1, 15):
        ws.cell(r, j).fill = PatternFill('solid', fgColor='FFF2F2F2')
        ws.cell(r, j).border = BORDER
    sec_ranges.append((sec, first, last, r))
    r += 2

end = r - 1
ws.cell(r, 2, '합계').font = Font(name=F, size=11, bold=True)
r += 1
tot_rows = {}
for lab, b in (('기본 부품 합계', '기본'), ('소모품 합계', '소모품'), ('공구 합계', '공구')):
    ws.cell(r, 2, lab).font = Font(name=F, size=10, bold=True)
    ws.cell(r, 6, f'=SUMIFS($F$6:$F${end},$H$6:$H${end},"{b}",$I$6:$I${end},"O")').number_format = WON
    ws.cell(r, 6).font = Font(name=F, size=10, bold=True)
    tot_rows[b] = r
    r += 1
ws.cell(r, 2, '최종 금액').font = Font(name=F, size=13, bold=True)
ws.cell(r, 6, f'=F{tot_rows["기본"]}+F{tot_rows["소모품"]}+F{tot_rows["공구"]}').number_format = WON
ws.cell(r, 6).font = Font(name=F, size=13, bold=True)
ws.cell(r, 6).fill = PatternFill('solid', fgColor='FFFFF2CC')
final_row = r
r += 1
ws.cell(r, 2, '확인: 판매처 소계의 합').font = Font(name=F, size=10)
ws.cell(r, 6, '=' + '+'.join(f'F{s[3]}' for s in sec_ranges)).number_format = WON
ws.cell(r, 12, '최종 금액과 같아야 한다').font = Font(name=F, size=9, color='FF595959')
r += 1
ws.cell(r, 2, '기본 구성 한도(R21)').font = Font(name=F, size=10)
ws.cell(r, 6, 1000000).number_format = WON
ws.cell(r, 6).font = Font(name=F, size=10, color='FF0000FF')
ws.cell(r, 12, '출처: sound-requirements.md R21 (소모품은 한도 밖)').font = Font(name=F, size=9, color='FF595959')
r += 1
ws.cell(r, 2, '한도까지 남은 금액').font = Font(name=F, size=10, bold=True)
ws.cell(r, 6, f'=F{r - 1}-F{tot_rows["기본"]}').number_format = WON
r += 2
notes = ['메모',
         '· v4에서 목록에서 뺀 부품: ' + '; '.join(f'{d["name"]}({d["code"]}) — {d["reason"]}' for d in old['dropped']),
         '· 4차 설계에서 3차의 업스톱 레일·손나사·접시 스프링·탭 강철 띠·황동 부싱·커버 자석·흑건 납·경화 샤프트가 빠졌다. 비용을 줄이는 대안과 "사용 안함"은 통합 아티팩트 07 재료·절감 선택 탭에서 고르고, 선택 코드를 대화창에 붙이면 이 표를 다시 만든다.',
         '· 토션 보조 스프링: 9/28 한국미스미 경제형 C-UA90R5-3-0.5 100개(100개 이상 282원 + VAT = 310원, 31,000원)로 정함. 두 다리를 22.3 / 8.0 mm로 잘라 쓴다(200번). r4.5 고침: 짧은 다리를 8.0으로 늘려 허브 홈에 가둔다(코일이 봉에 닿지 않게). 직접 감기·주문 제작은 선택기 대안.',
         '· r4.4 추가: 경선용 니퍼(스프링 다리 200번, 지금 니퍼 CT13은 구리선용).',
         '· 9/29 고침 2b: 강철 블록 접착제를 5분 에폭시에서 MS 폴리머 탄성 접착제로 바꿨다(에폭시는 딱딱해 온도 변화에 떨어짐). 세메다인 슈퍼X 백색 20 mL 2개(약 25~40 mL 필요). 투명형은 PET에 약해 사지 않는다. PETG 면은 사포 + 알코올, 24~48시간 경화, 단계 0 시험 20(5 ↔ 45 °C 3번)으로 확인.',
         '· 9/28 고침: 캡스턴 카드에 M3 너트 96개가 L31(100개)과 겹쳐 들어가 있던 것을 뺐다. 제어 기판 M3×6(L35) 20개는 r4.4의 14개 + 예비 6으로 충분.',
         '· 가격 확인이 "미확인"인 줄: 레이저 재단 견적, 한국미스미 SSFJ4 샤프트(9/27~28 점검), 알리익스프레스, 동네 철공소 — 주문 전에 다시 확인한다. 한국미스미 스프링 가격은 9/28 확인, 배송비는 무료로 알려져 있으나 결제 화면에서 확인하지 못했다.',
         '· 아이씨뱅큐·엘레파츠·Bambu Lab·나비엠알오(10/1 L2 고침: 공급가 5만 원 이상 무료) 배송비는 주문액에 따라 자동 계산된다. 다른 판매처 배송비와 엘레파츠 해외재고 개별 배송비는 한 줄로 넣었다.',
         '· 회로 검토(2026-09-28, hardware/pcb README) 반영: 1206 10 µF(L67)·1206 1 kΩ(L68) 추가, 핀헤더 1×40 5 → 9줄, 핀헤더 소켓 빼기, RP2040-Zero·저항·리본·L66·USB 케이블·1 µF 용도 글 수정.',
         '· USB 케이블(C04): 모듈 쪽 C 몰드 ≤ 12.5 × 7.6 × 25, 폭 초과 금지. NA993은 두께가 공개되지 않아(폭·길이는 사진 추정) 단계 0 시험 19로 확인한다. 세 치수가 공개된 대안은 CVILUX DH-20M50052(DigiKey, 선택기에서 고름).',
         # ---- 10/1 L2 (한 몸 뒷바) + 터치스크린 3판
         '· 10/1 L2(한 몸 뒷바, 앞판 40°)·터치스크린 3판 반영: 600×1200 합판(L63)·토글 래치(L64, 철물박사 배송비 3,000원 포함)·직결피스 16 mm를 뺐다. 추가: 스피커 유닛 M4 열압입 인서트(L69) + M4×12(L70), 화면 뚜껑 레일 M3 열압입 인서트(L71), 스피커↔가운데 M4 손잡이볼트(L72)·목재 인서트(L73)·실리콘 슬리브(L74), BRK2 M3×16(L75), 보드 받침 M3×5(L76), 접시머리 13 mm(L77), M3×12 태핑(L78), 보조배터리 벨크로(L79), 허브 업스트림 짧은 선(C25). 보조배터리 선(C22)은 ㄱ자로 바꿈. 수량: M3×10 54 → 28, M3×6 20 → 24, 직결피스 13 mm 54 → 20. 터치스크린 M3×20(70원)·M2.5×6(200원) 옵션 값을 확인해 고침.',
         '· 사양 bom_net_krw −21,060원은 합판 −22,520 · 래치 −4,800 · 손잡이 나사·목재 인서트·슬리브 +4,200(어림) · ㄱ자 선 +2,060(어림)만 셌다. 이 표는 실제 페이지 값(손잡이볼트 5개 6,700 · M4 인서트 Norelem 07653-04 1,749 ×5(10/1 CAD v16: 목재 퀵서트 전장 10은 밀폐 판을 뚫어 길이 6으로 바꿈) · 실리콘 튜브 1 m 2,959 · ㄱ자 0.5 m 4,270 + 개별 배송비 3,000)과 철물박사 배송비, 나비엠알오 배송비(5만 원 넘어 빠짐), CAD README의 "구매 목록에 없는 것"(인서트·M3×16·M3×5·접시머리·태핑·벨크로·허브 선·ㄱ자 Pi 전원선), 줄어든 수량을 함께 넣었다.',
         '· 10/1 L2 고침(검토 반영): ① 보조배터리 ㄱ자 선(C22, 엘레파츠 해외재고)은 개별 배송비 3,000원이 따로 붙어 배송비 줄을 더했다 — 개별 배송비가 없는 Coms NC888 꺾임 C–C 1 m(2,600원, 꺾임 방향·W 미표기)는 선택기 대안 ② 실리콘 튜브(L74)를 같은 상품의 나비엠알오 판매(2,959원)로 옮겨 나비엠알오 주문이 공급가 50,340원 → 배송비 3,300원이 빠짐(선택기도 나비엠알오 5만 원 기준을 씀; 추천·공구 묶음처럼 나비엠알오 줄이 줄면 다시 붙음) ③ Pi 전원선(C24): CAD는 측면 꺾임 머리 14×13×9를 그렸고 MT666은 곧은 플러그(사진)라 Coms BT663(C 쪽 측면 꺾임 20 cm, 2,550원)의 A 쪽을 잘라 쓴다. 검토가 권한 IH627은 수–수 U자 어댑터라 맞지 않는다 ④ I/O 판·CU 트레이 글을 뒤판 출력물·J702로 고침.',
         '· USB-A→C 케이블(C04)은 1 m ×8 그대로 산다. CAD가 권한 짧은 세트(1 m ×2 · 0.5 m ×4 · 0.3 m ×2, 같은 계열)는 선택 — 남는 선 약 2.3 m를 감지 않으려면 사기 전에 끈으로 길이를 재고 바꾼다.',
         '· 판 가공 공구(10/1 L2): 전동 드릴과 4·6·8 mm 비트를 가지고 있다고 본다(목록 공구는 Ø4.0 HSS·쇠톱·줄뿐). 필요한 가공 — 폭 4 mm 홈 38개(Ø4 줄 구멍 + 줄), Ø6 선 구멍 2, Ø8 슬리브 구멍 4, 목재 인서트 막힌 구멍 4(약 Ø5.5~6), Ø14 XT30 구멍 2(Ø10 + 줄), 자석 자리 Ø8 × 3.2 12곳(포스트너 또는 목공 비트), 40° 사선·27 × 22 홈·뒤판 창(쇠톱 또는 목공 톱·실톱). 비트가 없으면 나비엠알오 HARDEN 목공 드릴세트 8pcs(3~10 mm, 4,389원, v4wood 줄 — 기본 X)를 O로 바꾼다.',
         '· CAD 확인 필요(10/1 L2): ① 퀵서트(L73)는 길이 10이라 CAD의 목재 인서트 8 깊이보다 2 깊다(밑 밀폐 판 3.5 → 1.5). 구멍 지름도 — 겉나사 Ø7 목재용이라 Ø6.5는 너무 크고 약 Ø5.5~6.0(추정, 판매처 문의 또는 시편 구멍) ② 허브 업스트림 선(C25)은 Pi 쪽 A가 꺾이고 B가 곧다(CAD는 반대) ③ 허브 사진상 업스트림 USB 3.0 B 포트와 DC 잭이 같은 끝면(CAD는 양 끝으로 추정) ④ M4 열압입 인서트(L69)는 바깥 6 × 길이 4(CAD M4×6, 바깥 5.6) — 구멍 Ø5.6 × 6.5 그대로 ⑤ CAD는 Pi 전원(Z-PI-PWR 14×13×9)과 허브 DC 플러그(12×12×10)를 ㄱ자로 그렸다: Pi 쪽은 BT663 측면 꺾임 머리 크기를 받은 뒤 비교, 허브 DC는 딸린 어댑터 플러그가 곧으면 잭 규격을 재고 같은 규격 ㄱ자 DC 플러그 선을 따로 산다(아직 값 없음) — CAD 배치를 다시 볼 때 ③과 함께.']
for t in notes:
    ws.cell(r, 1 if t == '메모' else 2, t).font = Font(name=F, size=10 if t == '메모' else 9, bold=t == '메모')
    r += 1

dv = DataValidation(type='list', formula1='"O,X"', allow_blank=False)
ws.add_data_validation(dv)
for rg in ox_ranges:
    dv.add(rg)
ws.conditional_formatting.add(f'A6:N{end}', FormulaRule(formula=['$I6="X"'], font=Font(color='FF9C9C9C'), fill=PatternFill('solid', fgColor='FFF2F2F2')))

# ---------------------------------------------------------------- 판매처 요약
s2 = wb.create_sheet('판매처 요약')
for j, h in enumerate(['No', '구매 사이트', '품목 수(O)', '소계(원)', '비중'], 1):
    c = s2.cell(1, j, h)
    c.font = Font(name=F, size=10, bold=True, color='FFFFFFFF')
    c.fill = PatternFill('solid', fgColor='FF1F3864')
    c.border = BORDER
for i, (sec, first, last, sub) in enumerate(sec_ranges, 1):
    row = i + 1
    vals = [i, sec, f'=COUNTIFS(구매목록!I{first}:I{last},"O",구매목록!E{first}:E{last},"<>배송비")', f'=구매목록!F{sub}',
            f'=IF(구매목록!F{final_row}=0,0,D{row}/구매목록!F{final_row})']
    for j, v in enumerate(vals, 1):
        c = s2.cell(row, j, v)
        c.font = Font(name=F, size=10)
        c.border = BORDER
    s2.cell(row, 4).number_format = WON
    s2.cell(row, 5).number_format = '0.0%'
row = len(sec_ranges) + 2
s2.cell(row, 2, '최종 금액').font = Font(name=F, size=10, bold=True)
s2.cell(row, 3, f'=SUM(C2:C{row - 1})')
s2.cell(row, 4, f'=SUM(D2:D{row - 1})').number_format = WON
s2.cell(row, 5, f'=SUM(E2:E{row - 1})').number_format = '0.0%'
for col, w in zip('ABCDE', (5, 34, 11, 16, 9)):
    s2.column_dimensions[col].width = w

wb.save(OUTX)
print('saved', OUTX, 'rows', n, 'sections', len(sec_ranges))
