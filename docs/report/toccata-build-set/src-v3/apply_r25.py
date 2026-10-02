#!/usr/bin/env python3
"""R25(2026-09-24 사용자 결정): 스피커는 좌우 2개, 스피커·앰프는 싼 것으로 → bom_all.json 갱신.
원본은 bom_all.before_r25.json으로 한 번만 백업한다. 다시 돌리면 백업에서 새로 만든다."""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'bom_all.json')
BK = os.path.join(HERE, 'bom_all.before_r25.json')
if not os.path.exists(BK):
    shutil.copy(P, BK)
B = json.load(open(BK))


def find(bucket, lid):
    for l in B[bucket]:
        if l['line_id'] == lid:
            return l
    raise KeyError(lid)


def drop(bucket, *ids):
    n0 = len(B[bucket])
    B[bucket] = [l for l in B[bucket] if l['line_id'] not in ids]
    assert n0 - len(B[bucket]) == len(ids), (bucket, ids)


def line(**kw):
    base = dict(consumable=False, optional=False, page_ok=True, image_ok=True, purchase_unit='1개', shipping_krw=0)
    base.update(kw)
    order = ['line_id', 'group', 'name', 'role', 'design_ref', 'specs', 'qty', 'purchase_unit', 'unit_price_krw', 'shipping_krw',
             'consumable', 'optional', 'store', 'url', 'image_url', 'page_ok', 'image_ok', 'why']
    return {k: base[k] for k in order}


S = lambda *kv: [{'k': k, 'v': v} for k, v in kv]

# ---------------- 기본 구성: 빼는 줄 ----------------
drop('base', 'L04', 'L05', 'L08', 'L09', 'L13', 'L16', 'L28', 'L48')

# ---------------- 기본 구성: 바꾸는 줄(같은 번호, 새 제품) ----------------
REPL = {
    'L06': line(
        line_id='L06', group='제어·전원',
        name='[프라임디렉트] 아답터, 220V / 19V 3.42A [내경2.1~2.5mm/외경5.5mm] 전원 케이블 일체형',
        role='앰프(L53) 전용 전원. DC 잭(L54)을 거쳐 XH-A232의 VCC·GND 패드로 들어간다. 8 Ω 스피커(L07)에서 채널당 약 19 W를 내려면 19 V가 필요하다(12 V면 약 7.5 W)',
        design_ref='control_unit(R25): 앰프 전용 19 V 어댑터, Pi는 L55로 따로 급전',
        specs=S(('입력', 'AC 220V 60Hz(프리볼트 아님), AC 코드 일체형 70cm'), ('출력', 'DC 19V 3.42A (65W)'),
                ('플러그', '외경 5.5 / 내경 2.1~2.5mm 겸용(옐로우팁)'), ('DC 케이블', '115cm'), ('인증', '전기안전인증, 전자파인증'),
                ('가격·발송', '10,272.73원 + VAT = 11,300원, 평균 2.5일, 제품번호 EPXUYX78')),
        qty=1, unit_price_krw=11300, store='엘레파츠 (no=10052202)',
        url='https://www.eleparts.co.kr/goods/view?no=10052202',
        image_url='https://image3.compuzone.co.kr/img/product_img/2021/0217/762947/762947_600.jpg',
        why='R25로 앰프가 XH-A232(TPA3110) 한 대가 돼 90 W가 필요 없다. 앰프 최대 소비가 2×19 W ÷ 효율 약 0.88 ≈ 43 W라 65 W로 충분하다. '
            'AC 코드가 붙어 있어 별매 코드(옛 C17)가 필요 없고, 플러그가 2.1·2.5 겸용이라 DC 잭(L54)에 맞는다. '
            '받은 뒤 멀티미터로 센터 + 극성과 무부하 전압(19~20 V)을 확인한다. 이전 19V 4.74A(23,600원) 대비 −12,300원. 배송비는 엘레파츠 통합 주문 기준 0원.'),
    'L07': line(
        line_id='L07', group='오디오',
        name='삼미스피커(SAAT) CW-100B25 4인치 풀레인지 8Ω 25W (KS 인증)',
        role='좌우 스피커 유닛 2개(R25: 서브 없음). 오꾸메 밀폐 상자(내부 약 4.7 L) 앞판에 끼워 연주자 쪽을 향하게 한다. 앰프(L53)가 채널당 약 19 W를 준다',
        design_ref='control_unit(R25) 스피커 L(x−16~164)·R(x1058~1238), 도면 8, D12·D13·D14·D17·D18',
        specs=S(('임피던스', '8 Ω (Re 6.2 Ω)'), ('감도', '86 dB/1W/1m(판매처 사양표) · 89±2 dB(제조사 검사성적서, 300~600 Hz 평균)'),
                ('허용입력', '정격 25 W / 최대 50 W'), ('대역', 'f0 ~ 13 kHz(사양표) / f0 ~ 15 kHz(검사성적서)'),
                ('T/S', 'Qts 0.72, Fs 128 Hz(판매처 T/S표) · 90±18 Hz(검사성적서) — 두 자료가 다르다. Sd 약 54 cm², Xmax 약 3 mm(계산값)'),
                ('크기·장착', '프레임 105×105 mm, 장착 4-Ø4.8×6.8 장공(PCD Ø115), 깊이 57 + 플랜지 4 mm, 컷아웃 약 Ø94(실물 확인), 0.74 kg'),
                ('가격·재고(9/24)', '9,600원/개 + 배송 4,000원, 판매 중')),
        qty=2, unit_price_krw=9600, shipping_krw=4000, store='11번가 세운상가새한음향 (상품 1565354988)',
        url='https://www.11st.co.kr/products/1565354988',
        image_url='https://cdn.011st.com/11dims/resize/600x600/quality/75/11src/product/1565354988/B.jpg?63000000',
        why='R25(스피커 2개, 비싸지 않게)로 다시 고른 국산 KS 인증 유닛이다. 8 Ω이라 19 V TPA3110에서 채널당 약 19 W(12.3 Vrms)를 받아 1 m에서 약 98 dB(한 개)를 낸다. '
            'P-145(7 W×2, 추정 93.5~96.5 dB)보다 크다. 자석 280 g·Xmax 약 3 mm로 같은 값대 FR-100B09보다 저음 여유가 크다. '
            '약점은 두 가지다. 고음이 13~15 kHz까지라 알루미늄 콘보다 반짝임이 덜할 수 있고, Fs 표기가 90/128 Hz로 달라 받은 뒤 임피던스 피크를 재서 HPF를 정한다(D18). '
            '같은 제품이 대동전자 12,000원, 다나와 최저 7,700원+배송(판매처 미확인)이다. 이전 DMA105-4 ×2(101,440원) 대비 −78,240원.'),
    'L10': line(
        line_id='L10', group='오디오',
        name='무료배송 오꾸메 합판 400×1200×11.5mm 무료재단',
        role='스피커 상자 2개(외형 180×190×210, 내부 약 4.7 L)를 한 장에서 재단한다(도면 8의 재단도)',
        design_ref='control_unit(R25) 밀폐 상자, 도면 8, D12',
        specs=S(('규격', '400 × 1200 × 11.5mm'), ('재질', '오꾸메 합판'), ('재단', '무료재단(재단도를 함께 보냄)'),
                ('가격', '17,680원(9/24 옵션가), 무료배송'),
                ('재단 계획', '폭 210 띠: 옆판 190×210 ×4 + 앞·뒤판 157×210 ×2 / 폭 157 띠: 앞·뒤판 157×210 ×2 + 위·아래판 157×167 ×4 (톱날 3 mm 포함 폭 370, 길이 약 1,106 mm)')),
        qty=1, unit_price_krw=17680, store='동진나무공장 (namugongjang.com, product_no=1378)',
        url='https://namugongjang.com/product/detail.html?product_no=1378',
        image_url='https://namugongjang.com/web/product/big/202512/bfea2e797b70fbfcc2008f0b36aa788b.png',
        why='서브 상자가 없어져(R25) 400 폭 한 장이면 상자 2개가 나온다. 오꾸메는 자작보다 가볍고 싸며 밀폐 상자에 충분히 단단하다(비용 절감안 SP2와 같은 결론). '
            '두께가 11.5 mm가 아니면 앞·뒤판과 위·아래판의 폭(157)을 (180 − 2 × 두께)로, 위·아래판 길이(167)를 (190 − 2 × 두께)로 바꾼다. 이전 자작 600×1200(33,520원) 대비 −15,840원. 목공본드(C21)도 같은 판매처다.'),
}
for bucket in ('base',):
    B[bucket] = [REPL.get(l['line_id'], l) for l in B[bucket]]

# ---------------- 기본 구성: 쓰임만 바뀌는 줄 ----------------
l = find('base', 'L11')
l.update(qty=2, role='스피커 상자 뒤판의 스피커선 단자. 상자마다 1개(4포트 중 +/− 2개 사용). 상자를 떼어 옮길 때 선을 뽑는다(R18)',
         why=l['why'].replace('엘레파츠에서 가장 싼 스피커 터미널.', '엘레파츠에서 가장 싼 스피커 터미널. R25로 서브 상자가 빠져 3개 → 2개.'))
l = find('base', 'L12')
l.update(role='밀폐 스피커 상자 2개의 흡음재(상자당 40~60 g, 폴리필 대용)')
l['specs'] = [s if s['k'] != '사용량' else {'k': '사용량', 'v': '상자당 40~60 g을 뒤판·옆판에 느슨하게(300 g 중 약 100 g 사용)'} for s in l['specs']]
l = find('base', 'L14')
l.update(role='스피커 상자 2개·CU 상자 바닥의 고무발(상자당 4개, 12개 사용). 본체와 스피커 진동을 떼어 놓고 상자 무게를 받친다',
         why=l['why'].replace('필요 16개지만 최소 주문이 20개다.', '필요 12개(R25로 서브 상자가 빠짐)지만 최소 주문이 20개라 8개가 남는다.'))
l = find('base', 'L15')
l.update(role='① 왼쪽 볼 앞면 헤드폰 잭: 동글(L51) 출력이 팁·링으로 들어오고 팁·링 노멀 접점이 앰프(L53) 입력으로 나간다. 헤드폰을 꽂으면 노멀 접점이 떨어져 스피커가 기계적으로 끊긴다(R15) ② CU 뒷면 댐퍼 페달 잭(R24)',
         design_ref='control_unit(R25) 헤드폰: PJ-313 노멀 접점, end_parts 왼쪽 볼, pedals',
         why='설계가 지정한 PJ-313. 5핀(L·R·GND + 팁·링 노멀)이라 R25 구성에서는 노멀 접점이 앰프 입력을 끊는다. 릴레이와 GPIO 감지가 필요 없다(비용 절감안 AE4와 같은 방식). '
             '너트 없는 PCB형이라 만능기판(L23) 자투리에 납땜해 왼쪽 볼의 출력 포켓에 끼운다. 두 번째는 댐퍼 페달 잭(R24)이다.')
l = find('base', 'L29')
l.update(role='앰프 입력 풀다운 겸 저음 차단 필터 저항(1 kΩ ×2, D18), 필요하면 입력 감쇠(직렬 1 kΩ ×2, −6 dB), 페달 입력(1 kΩ 직렬·100 kΩ 풀)',
         design_ref='control_unit(R25) 헤드폰 노멀 접점 배선, pedals',
         why=l['why'] + ' R25로 헤드폰 감지 회로(10 kΩ·100 kΩ)가 없어져 1 kΩ을 앰프 입력에 쓴다.')
l = find('base', 'L37')
l.update(role='Pi 5를 CU 상자 바닥에서 16 mm 띄워 고정하는 M2.5 스탠드오프 4개(수-암). R25로 HAT이 없어 Pi만 얹는다',
         why='수나사를 CU 바닥 아래로 빼서 동봉 너트로 조이고, Pi를 위에 얹어 M2.5×6(L47) 4개로 고정한다. 아이씨뱅큐 합배송. '
             '출력 보스로 대신하면 −4,160원(비용 절감안 CP7).')
l = find('base', 'L42')
l.update(role='끝 부속 ↔ 스피커 상자 PETG 브래킷의 방진 그로밋(브래킷당 2개). 위치 고정용이고 상자 무게는 바닥 고무발이 받친다',
         why=l['why'].replace('위성 상자(약 1.9kg)', '스피커 상자(약 1.9kg)'))
l = find('base', 'L47')
l.update(role='Pi 5를 스탠드오프(L37) 위에서 고정하는 나사(4개 + 예비 2)')
l = find('base', 'L49')
l.update(unit_price_krw=1520,
         role='고무발 12개 고정(25 mm), CW-100B25 유닛 8홀 고정(16 mm), PETG 그릴 8곳 고정(19 mm)',
         design_ref='control_unit(R25) 스피커 상자·CU 고무발, 도면 8, D15',
         why='고무발·유닛·그릴 고정 나사를 한 상품의 옵션으로 해결했다. 같은 판매자(굿나잇몰) 묶음배송이라 배송비가 L32의 3,500원에 묶인다(다른 상품번호라 주문 화면에서 묶음 여부를 확인). '
             '유닛은 16 mm − 플랜지 4 − EVA 가스켓 3 = 물림 약 9 mm라 11.5 mm 합판을 뚫지 않는다. R25로 서브 유닛용이던 16 mm를 CW-100B25 고정에 쓴다.')
l['specs'] = [({'k': '구성', 'v': '25mm ×12 = 720원, 19mm ×8 = 400원, 16mm ×8 = 400원'} if s['k'] == '구성' else
               {'k': '용도 치수', 'v': '고무발 구멍 약 Ø5 + M4 와셔(L36), 유닛 장공 Ø4.8에 8호(Ø4.2), 그릴은 스페이서 링 10 mm 관통'} if s['k'] == '용도 치수' else s)
              for s in l['specs']]

l = find('base', 'L01')
l.update(role='FluidSynth 소프트웨어 신스를 돌리고 USB-MIDI 8개(O1~O7, PED) 입력을 한 곳에서 병합하는 중앙 컴퓨터. 소리는 USB 동글(L51)로 내보낸다(R25: HAT 없음, GPIO 배선 없음)',
         design_ref='control_unit(R25): CU 상자 안 Pi 5 2GB(스탠드오프 4개), USB 동글 직결, D6·D7·D16',
         why=l['why'].replace("AAmp60 데이터시트는 Pi 급전 여유를 'Pi 4B까지'로만 밝히므로, 첫 부팅 때 vcgencmd get_throttled로 저전압이 없는지 확인한다(USB 부하는 전원형 허브 L17이 맡는다, D16).",
                              '전원은 5.1 V 5 A PD 어댑터(L55)다. 첫 부팅 때 vcgencmd get_throttled로 저전압이 없는지 확인한다(모듈 USB 부하는 전원형 허브 L17이 맡는다, D16).'))
assert 'L55' in l['why']
l = find('base', 'L02')
l.update(role='SoC·메모리·RP1·이더넷 칩의 열을 뺀다. 팬 없는 저높이 스티커형(R25 이후 위에 HAT이 없어 높이 제한도 없다)',
         design_ref="parts_needed 'Pi 5 저높이 방열판'",
         why='설계안의 아이씨팩토리 ICF0310(7,700원)보다 싼 스티커형 저높이 세트다(−6,300원). 배송비 3,000원은 메카솔루션 주문 1회분(만능기판 L22 합배송)인데, 상품 페이지와 배송 안내 어디에도 금액이 없어 추정값이다. '
             'FluidSynth는 부하가 작아 팬 없이 충분하다. 연속 재생 시험 때 vcgencmd measure_temp로 온도를 확인한다.')
l = find('base', 'L37')
l.update(design_ref="parts_needed '볼트류 세트: M2.5 스탠드오프 세트(Pi 고정)'")
l = find('base', 'L47')
l.update(design_ref="parts_needed '볼트류 세트: M2.5 스탠드오프 세트(Pi 고정)' — 검증 누락 항목 'M2.5×6 나사 4개'")
l = find('base', 'L45')
l.update(role='기본 피아노 엔진(0원). midi.autoconnect=1로 USB-MIDI 8개 입력을 한 곳에서 병합하고 ALSA hw:로 USB 동글(L51)에 출력, 출력 리미터 synth.limiter.active=1(D18)',
         design_ref=l['design_ref'] + ', D18',
         why='FluidSynth로 충분해 기본은 무료 엔진이다. R25 이후 예산 여유가 커져 Pianoteq(O01, 약 18.8만원)를 넣어도 한도 안이다. 하프페달 음색(R3)을 더 원하면 O01로 엔진만 바꾼다(R9, 하드웨어 그대로).')
l = find('base', 'L11')
l.update(design_ref='control_unit(R25) 스피커 상자 뒤판, 도면 8')

# ---------------- 기본 구성: 새 줄 ----------------
B['base'] += [
    line(line_id='L51', group='오디오', name='Apple USB-C–3.5mm 헤드폰 잭 어댑터 (MW2Q3KH/A)',
         role='USB DAC 겸 헤드폰 앰프. 젠더(L52)로 Pi 5 USB-A 포트에 직결해 소리를 아날로그로 바꾼다. 출력은 헤드폰 잭(L15)을 거쳐 앰프(L53)로 간다',
         design_ref='control_unit(R25): FluidSynth → ALSA hw:<동글>,0 48 kHz(D7) → 동글 → PJ-313 노멀 접점 → XH-A232',
         specs=S(('형식', 'USB 오디오 클래스 DAC + 헤드폰 앰프(드라이버 불필요, 리눅스에서 48 kHz)'),
                 ('측정(외부 자료)', 'SNR 113 dB, SINAD 98 dB, 출력 임피던스 0.9 Ω'),
                 ('연결', 'USB-C 수 → 젠더(L52) → Pi 5 USB 포트(허브 경유 금지)'),
                 ('지연', 'USB 오디오가 1~3 ms를 더해 키→소리 계산 8~10 ms(D8 한계 10 ms, 설치 후 측정)'),
                 ('가격·재고(9/24)', '14,900원, 재고 있음, 무료 배송')),
         qty=1, unit_price_krw=14900, store='Apple Store 온라인 (한국)', url='https://www.apple.com/kr/shop/product/mw2q3kh/a',
         image_url='https://store.storeimages.cdn-apple.com/1/as-images.apple.com/is/MU7E2?wid=1200&hei=630&fmt=jpeg&qlt=95&.v=1539385665732',
         why='R25로 DAC2 Pro(79,600원) 대신 골랐다. DAC 품질이 같은 급이고, I2S를 쓰지 않아 Pi 5 커널 #7320(D11) 위험이 없다. 헤드폰 앰프가 들어 있어 헤드폰을 직접 구동한다. '
             '약점은 USB 지연(1~3 ms)이다. 설치 후 지연이 10 ms를 넘으면 FluidSynth 주기를 줄이고, 그래도 넘으면 I2S DAC(선택 O03)로 바꾼다. '
             '한국판 최대 출력 전압은 확인하지 못했다. 사진은 Apple 페이지가 대표 사진으로 쓰는 구형 품번(MU7E2) 이미지다.'),
    line(line_id='L52', group='오디오', name='[Coms] IH190 USB-C(F) → USB-A(M) 변환 젠더 좌향 꺾임',
         role='Apple 동글(USB-C 수)을 Pi 5 USB-A 포트에 꽂는 젠더',
         design_ref='control_unit(R25): 동글은 Pi에 직결(허브 경유 금지)',
         specs=S(('방향', 'USB-C 암 → USB-A 수'), ('형태', '좌향 꺾임'), ('가격·발송', '1,545.46원 + VAT = 1,700원, 평균 3.5일')),
         qty=1, unit_price_krw=1700, store='엘레파츠 (no=11043038)', url='https://www.eleparts.co.kr/goods/view?no=11043038',
         image_url='https://img2.eleparts.co.kr/goods/external/1104/11043038_818819260912105231large.jpg',
         why='꺾임형이라 옆 포트를 가릴 수 있다. 가리면 다른 포트에 꽂는다(허브 1 + 동글 1이면 포트가 남는다). 엘레파츠 합배송.'),
    line(line_id='L53', group='오디오', name='XH-A232 (HW-404) TPA3110 2채널 앰프 보드 (제노 HAM6104)',
         role='좌우 스피커(L07)를 울리는 D급 앰프. 19 V(L06)에서 8 Ω 채널당 약 19 W. 입력은 헤드폰 잭(L15)의 노멀 접점에서 받는다',
         design_ref='control_unit(R25), R14·R16·D18',
         specs=S(('칩·전원', 'TI TPA3110D2, DC 8~26 V(보드 콘덴서 35 V 정격), 4~8 Ω'),
                 ('실제 출력(TI 곡선, 1% THD)', '19 V·8 Ω 약 19 W/ch (판매 표기 30 W+30 W는 과장된 최대치)'),
                 ('단자', '입력 L·G·R, 전원 VCC·GND, 스피커 L±·R± 모두 납땜 패드, 볼륨 노브 없음'),
                 ('가격·재고(9/24)', '2,500원 + VAT = 2,750원, 국내 재고, 1주 이내')),
         qty=1, unit_price_krw=2750, store='아이씨뱅큐 (제노 HAM6104, P017179248)', url='https://www.icbanq.com/P017179248',
         image_url='https://www.icbanq.com/icdownload/data/ICBShop/Product/core_images/JENO/HAM6104.jpg',
         why='R25로 AAmp60(61,700원)·ZK-TB21(17,350원) 두 대 대신 한 대로 좌우 2개를 구동한다. 8 Ω·19 V에서 약 19 W/ch라 P-145(7 W×2)보다 약 4 dB 크다. '
             'BTL 출력이라 스피커 −선을 GND에 묶지 않는다. 저가 보드라 칩 정품 여부와 이득(20~36 dB 중 하나)이 표기돼 있지 않다. '
             '첫 전원 때 스피커 단자 전압으로 이득을 확인해 입력 감쇠를 정한다(조립 12). 같은 보드가 파츠파츠 PP-A591 1,500원(+배송 3,000원)에도 있다. 아이씨뱅큐 합배송.'),
    line(line_id='L54', group='제어·전원', name='(PP-A198) DC 전원 잭 커넥터 Female 5.5×2.1 (나사 단자형)',
         role='19 V 어댑터(L06) 플러그를 받아 앰프의 VCC·GND 패드로 잇는 잭. CU 뒷벽의 출력 클립에 끼운다',
         design_ref='control_unit(R25): 19 V → DC 잭 → XH-A232',
         specs=S(('규격', '배럴 잭 암, 외경 5.5 / 핀 2.1 mm'), ('단자', '나사 단자 2P(+ / −)'), ('가격·재고(9/24)', '360원 + VAT = 396원, 국내 재고, 2~3일')),
         qty=1, unit_price_krw=396, store='아이씨뱅큐 (파츠파츠, P019042616)', url='https://www.icbanq.com/P019042616',
         image_url='https://parts-parts.co.kr/web/product/big/201802/369_shop1_556756.jpg',
         why='XH-A232에는 DC 잭이 없고 전원 패드만 있다. 나사 단자형이라 스피커선(C13) 자투리로 앰프 패드까지 잇는다. 어댑터 플러그가 2.1·2.5 겸용이라 맞는다. 아이씨뱅큐 합배송.'),
    line(line_id='L55', group='제어·전원', name='[엘레파츠] HT-PD27W-KC 라즈베리파이 5 호환 PD 27W 어댑터 (5.1V 5A)',
         role='Pi 5 전용 전원(USB-C). R25로 앰프 HAT이 없어 Pi는 이 어댑터로만 전원을 받는다(동시 급전 없음, D16 취지)',
         design_ref='control_unit(R25): Pi 5 USB-C 급전, D16',
         specs=S(('출력', "5.1 V 5 A USB-C PD('라즈베리파이 5 완벽 호환, 5A 지원')"), ('인증', '모델명에 KC 표기(번호 미확인)'), ('가격', '9,900원')),
         qty=1, unit_price_krw=9900, store='엘레파츠 (no=14202378)', url='https://www.eleparts.co.kr/goods/view?no=14202378',
         image_url='https://img2.eleparts.co.kr/goods/1/2024/05/14202378_tmp_f3e9a7ea0226d3569c0a7bcf8d23d21a5609large.JPG',
         why='5 A PD라 Pi 5가 USB 포트에 1.6 A를 열고, 저전압 경고와 EEPROM 조정(PSU_MAX_CURRENT)이 필요 없다. 공식 27W 어댑터(약 19,000원)보다 싸다. '
             '첫 부팅 때 vcgencmd get_throttled가 0x0인지 확인한다. 5V 5A PD 충전기가 이미 있으면 사지 않아도 된다(−9,900원). 엘레파츠 합배송.'),
    line(line_id='L56', group='오디오', name='Monolithic Capacitor 1uF X7R 50V (리드형 적층 세라믹)',
         role='앰프 입력의 저음 차단(고역 통과) 필터. 채널마다 1 µF 2개를 병렬(2 µF)로 직렬에 넣고 1 kΩ 풀다운(L29)과 묶어 약 80 Hz 아래를 6 dB/옥타브로 줄인다(D18)',
         design_ref='control_unit(R25) 앰프 입력 RC, 도면 9, D18',
         specs=S(('용량·유전체', '1 µF (105), X7R, 50 V'), ('형태', '리드형 적층 세라믹(만능기판에 바로 납땜)'),
                 ('필터 계산', 'fc = 1 / (2π × 1 kΩ‖Zin × 2 µF) ≈ 80~88 Hz (앰프 입력 저항 9~60 kΩ)'),
                 ('가격·재고(9/24)', '121원 + VAT = 133원/개, 국내 재고, 2~3일')),
         qty=5, unit_price_krw=133, store='아이씨뱅큐 (동신전자, P014159115)', url='https://www.icbanq.com/P014159115',
         image_url='https://www.icbanq.com/icdownload/data/ICBShop/Product/동신전자/P014159115.jpg',
         why='D7(ALSA hw: 직결)을 지키면 FluidSynth 뒤에 소프트웨어 필터를 넣을 수 없어, 앰프 입력에서 콘덴서로 저음을 줄인다. 작은 유닛은 최저 옥타브에서 소리는 적게 내면서 콘만 크게 움직여 먼저 찌그러지므로(R16), '
             '80 Hz 아래를 줄이면 같은 볼륨 상한에서 여유가 생긴다. 4개(2채널 × 2) + 예비 1. 앰프 입력을 −6 dB 낮춰야 하면 채널마다 1 µF 하나를 빼고 1 kΩ 직렬을 넣는다(필터 주파수는 그대로 약 80 Hz). 아이씨뱅큐 합배송.'),
]

# ---------------- 소모품 ----------------
drop('consumable', 'C15', 'C16', 'C17')
l = find('consumable', 'C07')
l.update(role='CU 안 PED 보드·앰프 입력 배선(듀폰 점퍼)', design_ref='control_unit(R25) PED 보드, 앰프 입력',
         why='R25로 릴레이 모듈과 헤드폰 감지 회로가 없어져 쓰임이 줄었다. PED 보드와 앰프 입력 핀(L25 헤더를 패드에 납땜)을 압착 없이 잇는다. 비용 절감 T2~T4는 이 줄을 뺀다(X1).')
l = find('consumable', 'C07')
l['check'] = '2,850원 + VAT = 3,135원, 26AWG, F/F, 40C를 확인했다. R25 이후 Pi 40핀은 비어 있어(HAT 없음) GPIO에 바로 꽂을 수 있다.'
l = find('consumable', 'C13')
l.update(role='앰프(L53) → 좌우 스피커 상자 뒤 단자(L11), 왼쪽 약 1.2 m·오른쪽 약 0.8 m. 자투리는 19 V 잭 → 앰프 전원선',
         design_ref='control_unit(R25) 스피커 배선',
         why=l['why'] + ' R25로 서브선(약 2 m)이 빠져 약 2.5 m만 쓴다. 7 m 단위 재단 상품이라 남는데, 20AWG 5 m(2,130원)로 바꾸는 안은 비용 절감안 AE8에 있다.')
l = find('consumable', 'C14')
l.update(qty=2, role='① 동글(L51) → 왼쪽 볼 헤드폰 잭(L15) 팁·링·슬리브 ② 잭 노멀 접점 → 앰프(L53) 입력. ①은 한쪽, ②는 양쪽 플러그를 잘라 납땜한다',
         design_ref="control_unit(R25) '동글 → PJ-313 → 노멀 접점 → XH-A232'",
         why='CU에서 왼쪽 볼까지 경로가 약 0.6~0.7 m라 한 가닥을 반으로 자르면 여유가 5~15 cm뿐이다. 그래서 가닥마다 한 개씩 2개를 쓴다(+1,710원).')
l = find('consumable', 'C21')
l.update(role='스피커 밀폐 상자 2개(내부 4.7 L ×2) 합판 접합과 틈 밀봉')

# ---------------- 선택 항목 ----------------
drop('optional', 'O02', 'O03', 'O04')
opt = {l['line_id']: l for l in B['optional']}
new_opt = [
    line(line_id='O02', group='오디오', optional=True, name='Dayton Audio PC105-4 4" 풀레인지 4Ω (스피커 상향, 2개)',
         role='더 크고 데이터가 확실한 스피커가 필요할 때 L07 대신. 같은 상자에서 컷아웃만 Ø94 → Ø101.6으로 넓힌다',
         design_ref='control_unit(R25) 스피커 대안, 도면 8',
         specs=S(('임피던스·감도', '4 Ω, 90.3 dB @2.83V/1m(CW-100B25보다 +4.3 dB)'),
                 ('T/S', 'Fs 81.4 Hz, Qts 0.51, Vas 3.68 L, Xmax 2.0 mm, Sd 52.8 cm²'),
                 ('크기', '외경 126 mm, 컷아웃 Ø101.6, 깊이 60 mm, 장착 홀 PCD 113'),
                 ('밀폐 4.7 L', 'Qtc 0.68, Fc 109 Hz, F3 113 Hz → HPF 2차 80~90 Hz'),
                 ('가격·재고(9/24)', '52,320원/개, 다안 재고 5개, 5만원 이상 무료배송')),
         qty=2, unit_price_krw=52320, store='다안일렉트론 (데이톤 한국 공식대리점, goodsNo 1000000098)',
         url='https://www.daankorea.co.kr/goods/goods_view.php?goodsNo=1000000098',
         image_url='https://godomall-storage.cdn-nhncommerce.com/f29ccbb04aa664958bb6200a8d8febe9/goods/1000000098/image/detail/1000000098_detail_046.jpg',
         why='4 Ω이라 TPA3110은 16 V 이하로 쓰므로 L06을 12V 3A 어댑터(엘레파츠 no=3862351, 7,290원)로 바꾼다(12 V·4 Ω 약 12.5 W/ch). '
             '그러면 최대 음량은 삼미와 비슷하다(1 m 약 98 dB). 대신 T/S·Xmax가 공개돼 HPF를 계산으로 정할 수 있고 80 Hz~15 kHz 대역이 확실하다. '
             '소리 품질을 올리고 싶을 때만 쓴다. L07 대비 +81,440원(어댑터 −4,010원 별도).'),
    line(line_id='O03', group='오디오', optional=True, name='Raspberry Pi DAC+ (PCM5122 + 헤드폰 앰프, I2S HAT)',
         role='USB 동글의 지연이 D8(10 ms)을 넘을 때 L51·L52 대신 쓰는 I2S DAC. 헤드폰 잭 → 노멀 접점 → 앰프 배선은 그대로다',
         design_ref='control_unit(R25) 지연 대책, D8·D11',
         specs=S(('DAC', 'TI PCM5122, 하드웨어 볼륨, dtoverlay=rpi-dacplus'), ('출력', 'RCA 0~2 Vrms + 3.5 mm 헤드폰(전용 헤드폰 앰프)'),
                 ('지연', 'I2S라 계산 약 7 ms'), ('가격·재고(9/24)', '31,689원, 해외 재고 4~6일')),
         qty=1, unit_price_krw=31689, shipping_krw=2700, store='아이씨뱅큐 (P017025365)', url='https://www.icbanq.com/P017025365',
         image_url='https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/4574/MFG_SC0368.jpg',
         why='Pi 5 I2S HAT이라 커널 #7320(D11) 대비 절차(hw: 직결, 스트림 상시 유지, 워치독, 24~48 h 연속 재생)가 다시 필요하다. '
             '동글·젠더(16,600원)를 빼면 순증가는 약 +15,089원이다(아이씨뱅큐 합배송이면 배송비 0).'),
]
B['optional'] = [opt['O01']] + new_opt + [opt['O05'], opt['O06']]
_sub = lambda l: l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0)
TB = sum(map(_sub, B['base']))
opt['O01']['why'] = (f'기본 구성 {TB:,}원(R25 반영)에 더해도 {TB + _sub(opt["O01"]):,}원으로 R21 안이다. 그래도 FluidSynth로 충분해 선택으로 둔다. '
                     '결제 시 부가세 10%가 붙을 수 있다. 사기 전에 체험판으로 Pi 5 지연(D8)을 확인한다(USB 동글이라 여유가 작다).')
opt['O05']['why'] = f'L01 대신 쓰면 +97,900원으로 기본 구성이 {TB + 97_900:,}원이 된다. R25 이후에는 한도 안이다.'
opt['O06']['why'] = f'PC에 슬롯이나 리더가 있으면 필요 없다. 넣어도 기본 구성이 {TB + _sub(opt["O06"]):,}원으로 한도 안이다.'

# ---------------- 주문 전 확인(보고서 §check) ----------------
U = B['unresolved']
U[0] = U[0].replace('대안은 O05 4GB(예산 초과 → 서브 2단계).', '대안은 O05 4GB(+97,900원, R25 이후에는 예산 안).')
U[1] = ('삼미 CW-100B25(L07): Fs가 판매처 T/S표 128 Hz, 제조사 검사성적서 90±18 Hz로 다르고, 컷아웃도 사양표 102 mm와 도면(바스켓 Ø92)이 다르다. '
        '받은 뒤 캘리퍼스로 바스켓 지름을 재 컷아웃을 정하고(기본 Ø94), 멀티미터와 사인 스윕으로 임피던스 피크(Fs)를 찾아 HPF를 90~120 Hz로 정한다(D18).')
U[5] = U[5].replace('(35,420원/7개, 한도 초과 → 절감 순서 적용)', '(35,420원/7개, R25 이후 예산 안)')
U[6] = ('앰프 전원: XH-A232(L53)는 DC 잭이 없어 나사 단자형 잭(L54)에서 VCC·GND 패드로 선을 잇는다. 19 V 어댑터(L06) 플러그는 2.1·2.5 겸용이다. '
        '극성(센터 +)과 무부하 전압(19~20 V)을 멀티미터로 확인한 뒤 앰프에 잇는다.')
U[7] = 'Pi 5 전원은 HT-PD27W(L55, 5.1 V 5 A PD)다. 첫 부팅 때 vcgencmd get_throttled가 0x0인지, 부팅 화면에 전원 경고가 없는지 확인한다.'
U[8] = ('USB 오디오 지연(D8): Apple 동글(L51)은 USB라 I2S보다 1~3 ms 늦다(계산 8~10 ms). 설치 후 키→소리 지연을 휴대폰 녹음(건반 타격음과 스피커 소리의 간격)으로 재고, '
        '10 ms를 넘으면 FluidSynth audio.periods를 4 → 3으로, 그래도 넘으면 I2S DAC(O03)로 바꾼다.')
U[9] = ('XH-A232 이득과 Apple 동글 출력: 앰프 이득(20/26/32/36 dB)과 동글 한국판의 최대 출력 전압이 표기돼 있지 않다. 첫 전원 때 250 Hz 사인(−3 dBFS)을 동글 볼륨 100%로 틀고, '
        '스피커 단자 전압이 약 11 Vrms를 넘으면 노멀 접점과 앰프 입력 사이에 1 kΩ 직렬(L29)을 넣어 −6 dB로 낮춘다. 6 Vrms도 안 되면 감쇠 없이 쓴다.')
U[10] = U[10].replace('타공판 개구율(≥30%), ', 'CW-100B25 바스켓 지름·장공 위치, ').replace('DCS165-4 장착 구멍 지름, ', '')
B['unresolved'] = U

B['budget_strategy'] = ('[R25 반영 2026-09-24] 오디오를 Apple USB-C 동글 → PJ-313 노멀 접점 → XH-A232(TPA3110, 19 V) → 삼미 CW-100B25 ×2(오꾸메 밀폐 상자)로 바꿨다. '
                        'DAC2 Pro·AAmp60·서브(DCS165-4·ZK-TB21)·릴레이·타공 그릴·19V 90W 어댑터와 부속 케이블이 빠졌다. 합계는 보고서가 부품표에서 다시 계산한다.\n\n'
                        + B['budget_strategy'])
B['notes'] = ('[R25 2026-09-24] 새 오디오 부품의 가격·링크·이미지는 scratchpad/v3/work/audio2/(spk_result.json·amp_result.json)의 9/24 확인값이다. '
              '이전 부품표는 bom_all.before_r25.json.\n\n' + B['notes'])

json.dump(B, open(P, 'w'), ensure_ascii=False, indent=1)
sub = lambda l: l['qty'] * l['unit_price_krw'] + (l.get('shipping_krw') or 0)
for k in ('base', 'consumable', 'tools', 'optional'):
    print(k, len(B[k]), f'{sum(map(sub, B[k])):,}')
