"""Module pinouts and part metadata for the Toccata schematics.

Pad numbers for modules without an official symbol (RP2040-Zero, 4067 breakout, PD trigger,
buck, amp) are OUR convention and are listed in hardware/pcb/netlist/*.csv so a custom
KiCad symbol/footprint can be made to match.
"""

# RP2040-Zero (Waveshare / layout-identical clone), top view, USB-C at the top edge.
# Pin numbers = dj505/RP2040-Zero-KiCAD library (symbol + footprint agree):
#   1-9 left edge top->bottom, 10-18 right edge top->bottom, 19-23 bottom edge left->right.
# WS_P1 = the same pad in Waveshare's own schematic header P1 (1 = GP0 top-right, clockwise).
RP2040_ZERO = [
    (1, "5V"), (2, "GND"), (3, "3V3"), (4, "GP29"), (5, "GP28"), (6, "GP27"), (7, "GP26"),
    (8, "GP15"), (9, "GP14"),
    (10, "GP0"), (11, "GP1"), (12, "GP2"), (13, "GP3"), (14, "GP4"), (15, "GP5"), (16, "GP6"),
    (17, "GP7"), (18, "GP8"),
    (19, "GP13"), (20, "GP12"), (21, "GP11"), (22, "GP10"), (23, "GP9"),
]
WS_P1 = {"GP0": 1, "GP1": 2, "GP2": 3, "GP3": 4, "GP4": 5, "GP5": 6, "GP6": 7, "GP7": 8, "GP8": 9,
         "GP9": 10, "GP10": 11, "GP11": 12, "GP12": 13, "GP13": 14, "GP14": 15, "GP15": 16,
         "GP26": 17, "GP27": 18, "GP28": 19, "GP29": 20, "3V3": 21, "GND": 22, "5V": 23}
RP2040_EDGE = {**{n: "왼쪽" for n in range(1, 10)}, **{n: "오른쪽" for n in range(10, 19)},
               **{n: "아래" for n in range(19, 24)}}
# hole centres, module-local mm (origin top-left, USB edge at y=0), Waveshare drawing
RP2040_HOLE = {}
for i, n in enumerate(range(1, 10)):
    RP2040_HOLE[n] = (1.38, 1.59 + 2.54 * i)
for i, n in enumerate(range(10, 19)):
    RP2040_HOLE[n] = (16.62, 1.59 + 2.54 * i)
for i, n in enumerate(range(19, 24)):
    RP2040_HOLE[n] = (3.92 + 2.54 * i, 21.91)


def zero_pin(name):
    for n, nm in RP2040_ZERO:
        if nm == name:
            return n
    raise KeyError(name)


# CD74HC4067 breakout (parts-parts PP-A324 = TENSTAR copy of SparkFun BOB-09056 v11), 40.64 x 17.78 mm.
# Channel header J1 (1x16): pins 1-16 = C0..C15.  Control header J2 (1x8, square pad = GND):
# J2-1 GND, J2-2 VCC, J2-3 EN, J2-4 S0, J2-5 S1, J2-6 S2, J2-7 S3, J2-8 SIG  -> symbol pins 17-24.
# On-board: 100 nF VCC-GND, 10 kohm EN-GND pull-down.  Rows 15.24 apart; J2-1 (GND) is in line with C4.
MUX_CH = [(1 + i, f"C{i}") for i in range(16)]
MUX_CTRL = [(17, "GND"), (18, "VCC"), (19, "EN"), (20, "S0"), (21, "S1"), (22, "S2"), (23, "S3"), (24, "SIG")]


def mux_pin(name):
    for n, nm in MUX_CTRL + MUX_CH:
        if nm == name:
            return n
    raise KeyError(name)


# HUSB238 PD trigger module (icbanq HAM6113): USB-C receptacle in, output pads.
PDTRIG = [(1, "VOUT+"), (2, "VOUT+"), (3, "GND"), (4, "GND")]   # 2 round + pads, 2 square - pads
# XL4016 buck module (XH-M401): screw terminals
BUCK = [(1, "IN+"), (2, "IN-"), (3, "OUT+"), (4, "OUT-")]
# XH-A232 (HW-404) TPA3110 amp board
AMP_IN = [(1, "L"), (2, "G"), (3, "R")]
AMP_PWR = [(4, "VCC"), (5, "GND")]
AMP_OUT = [(6, "L+"), (7, "L-"), (8, "R+"), (9, "R-")]   # silkscreen order along the top edge

# BOM codes from docs/report/toccata-purchase-list-v4.xlsx ("부품 코드" column)
BOM = {
    "DRV5055": ("L20", "TI DRV5055A2QLPG, TO-92-3 (LPG)", "아이씨뱅큐 P018076669"),
    "C100n": ("SE4", "Samsung CL31B104KCFNNNE 1206 100 nF 100 V X7R", "아이씨뱅큐 P014968846"),
    "C10u": ("L67", "C3216-10UF(K 16V) 1206 10 µF 16 V (50개 단위)", "아이씨뱅큐 P001248090"),
    "C1u": ("L56", "리드형 적층 세라믹 1 µF 50 V X7R", "아이씨뱅큐 P014159115"),
    "R1k": ("L29", "탄소피막 1/4 W 5 % 1 kΩ", "엘레파츠 10911"),
    "R1k1206": ("L68", "Yageo RC1206JR-071KL 1206 1 kΩ 5 % 1/4 W (10개 단위)", "아이씨뱅큐 P011433924"),
    "R100k": ("L29", "탄소피막 1/4 W 5 % 100 kΩ", "엘레파츠 10993"),
    "R100": ("L29", "탄소피막 1/4 W 5 % 100 Ω", "엘레파츠 10873"),
    "ZERO": ("SEV2", "Waveshare RP2040-Zero (파츠파츠 PP-A799-2)", "파츠파츠 2383"),
    "MUX": ("SEV2", "CD74HC4067 16채널 먹스 모듈 (파츠파츠 PP-A324)", "파츠파츠 303"),
    "HDR": ("SE7", "핀헤더 1×40 2.54 mm (자름) — 먹스 모듈 1×16 + 1×8", "아이씨뱅큐 P005666127"),
    "PADS6": ("", "패드만 — L66 모듈 쪽 리드를 아랫면에서 직접 납땜 (헤더 없음)", ""),
    "HDRZ": ("SE7", "핀헤더 1×40 2.54 mm — RP2040-Zero용 1×9 ×2 (먹스 168 + 제로 144 = 312핀 → 1×40 9줄)", "아이씨뱅큐 P005666127"),
    "PERF57": ("SE8", "양면 만능기판 5×7 cm", "메카솔루션 329798"),
    "PERF1218": ("L22", "양면 만능기판 12×18 cm (띠로 자름)", "메카솔루션 540645"),
    "RIBBON": ("C05", "EUNSUNG 2651-16P 플랫 케이블 (16심 전부 사용)", "엘레파츠 425"),
    "JSTXH": ("L66", "JST-XH 6핀 밸런스 연장선 5S 200 mm (모듈 쪽 150 · 끝 부속 쪽 50으로 잘라 씀)", "알씨뱅크 29812"),
    "PJ313": ("L15", "BSUN PJ-313 3.5 mm 스테레오 잭 (노멀 접점)", "엘레파츠 67811"),
    "TRS3M": ("L50", "Coms BC256 3.5 mm 스테레오 케이블 3 m (한쪽 잘라 씀)", "아이씨뱅큐 P004711396"),
    "TRS15": ("C14", "Coms AV0176 3.5 mm 스테레오 케이블 1.5 m (한쪽 잘라 씀)", "엘레파츠 2925673"),
    "PEDAL": ("L43", "듀로 서스테인 페달 (스위치형 → 홀센서 개조)", "피아노모아"),
    "MAG5": ("L21", "네오디뮴 Ø5×2 N35 (센서 자석)", "대건상사 (dgmagnet)"),
    "PDTRIG": ("L57", "HUSB238 PD 트리거 모듈 5~20 V (HAM6113)", "아이씨뱅큐 P017179277"),
    "FUSEH": ("L60", "Coms BU914 인라인 퓨즈 홀더 5×20 mm", "엘레파츠 3237821"),
    "FUSE": ("L60", "Littelfuse 0218005.MXP 5 A 지연형 5×20 mm", "엘레파츠 12766820"),
    "SW": ("L59", "KCD1-101A 로커 스위치 (SPST, 2핀)", "엘레파츠 32569"),
    "BUCK": ("L58", "XL4016 강압 모듈 XH-M401 (HAM6415) → 5.1 V", "아이씨뱅큐 P017179502"),
    "MT666": ("C24", "MAXTEK MT666 USB-C 수 2선 DIY 전원선", "엘레파츠 17358965"),
    "PI5": ("L01", "Raspberry Pi 5 2GB", "아이씨뱅큐 P016286897"),
    "HUB": ("L17", "NEXTU 710U3 유전원 USB 허브 (10포트)", "다나와"),
    "USBAC": ("C04", "Coms NA993 USB-A → C 1 m", "엘레파츠 4313490"),
    "DONGLE": ("L51", "Apple USB-C → 3.5 mm 어댑터 MW2Q3", "Apple"),
    "GENDER": ("L52", "Coms IH190 USB-C(F) → USB-A(M) 젠더", "엘레파츠 11043038"),
    "AMP": ("L53", "XH-A232 (HW-404) TPA3110 2×15 W 앰프 보드", "아이씨뱅큐 P017179248"),
    "XT30M": ("L61", "AMASS XT30U-M 18 AWG 10 cm", "엘레파츠 12779720"),
    "XT30F": ("L61", "AMASS XT30U-F 18 AWG 10 cm", "엘레파츠 12779721"),
    "SPK": ("L07", "삼미 CW-100B25 4인치 8 Ω 25 W", "11번가 1565354988"),
    "SPKW": ("C13", "스피커선 16 AWG (전원선 겸용)", "엘레파츠 18388615"),
    "PDCHG": ("L62", "파워마스터 65 W PD 충전기 PG65PDG2C1A", "다나와"),
    "CC2M": ("C23", "USB-C to C PD 60 W 2 m", "엘레파츠 17806170"),
    # △16 (rev C, 2026-10-01) R31 screen B1 — purchase list v4 rows with code "v4touch" (No. = list row number)
    "DISP7C": ("v4touch No.135", "Waveshare 7-DSI-TOUCH-C 7인치 DSI 정전식 터치 1024×600 IPS (약 2.15 W, 동봉: 전원선 MX1.25 2핀 → 2.54 3핀, 22핀 200 mm 리본 2)", "G마켓 해외직구 4783965807"),
    "JMPFF": ("v4touch No.51 · No.52", "실리콘 점퍼 26 AWG 20 cm F/F 빨강 1 + 검정 1 (W606, Pi 헤더 쪽 끝)", "엘레파츠 9461190 · 9461199"),
    "JMPFF2": ("", "W606 다른 끝 — P603과 같은 점퍼 (따로 사지 않음)", ""),
    "JMPMM": ("v4touch No.53 · No.54", "실리콘 점퍼 26 AWG 20 cm M/M 빨강 1 + 검정 1 (W607, X601에 꽂는 끝)", "엘레파츠 9756990 · 9756998"),
    "JMPMM2": ("", "W607 다른 끝 — X602와 같은 점퍼 (따로 사지 않음)", ""),
    "DPWR": ("v4touch No.135 동봉", "화면 동봉 전원선 W608의 2.54 3핀 하우징 (A605에 들어 있음)", "A605와 함께"),
    "DPWR2": ("", "W608 다른 끝 — MX1.25 2핀 플러그 (X604와 같은 선, 따로 사지 않음)", ""),
    "FFC22B": ("v4touch No.49", "GUOCONN 0.5*22P*300*B FFC 22핀 0.5 mm 300 mm 반대면(B형) 5개 묶음", "엘레파츠 18622271"),
    "FFC22A": ("v4touch No.50", "GUOCONN 0.5*22P*300*A FFC 22핀 0.5 mm 300 mm 같은 면(A형) 5개 묶음 (보험)", "엘레파츠 18581287"),
}
