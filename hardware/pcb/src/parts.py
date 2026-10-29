"""Module pinouts and part metadata for the Toccata schematics.

Pad numbers for modules without an official symbol (RP2040-Zero, 4067 breakout,
buck, amp) are OUR convention and are listed in hardware/pcb/netlist/*.csv so a custom
KiCad symbol/footprint can be made to match.
"""

import harness as _HN  # noqa: E402  (cut lengths quoted in the BOM text; harness imports none of our modules)

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


# Rev D (2026-10-07): the HUSB238 PD trigger (A601) is gone; power comes from BT601, a LiFePO4 pack with an XT60 lead.
# XL4016 buck module (XH-M401): screw terminals
BUCK = [(1, "IN+"), (2, "IN-"), (3, "OUT+"), (4, "OUT-")]
# HW-720 (XH-M312 V4 layout, TPA3118D2) amp board, the user's own (△32, 2026-10-26): XH 3P input in silkscreen order, DC 5.5x2.1 jack,
# two 2P 5 mm screw terminals OUTL / OUTR (+ / - per the silkscreen - check on the board)
AMP_IN = [(1, "INR"), (2, "GND"), (3, "INL")]
AMP_PWR = [(4, "DC+"), (5, "DC-")]
AMP_OUT = [(6, "OUTL+"), (7, "OUTL-"), (8, "OUTR+"), (9, "OUTR-")]

# BOM codes = the "code" column of the FINAL purchase data (hardware/bom/final-bom/data.json, plan C 2026-10-08).
# (code, description, where it comes from). The purchase STATE (학교 / 사비 / 보유) is read by purchase.py.
BOM = {
    "DRV5055": ("L20", "TI DRV5055A2QLPG, TO-92-3 (LPG)", "아이씨뱅큐 P018076669"),
    "C100n": ("SE4", "Samsung CL31B104KCFNNNE 1206 100 nF 100 V X7R", "디바이스마트 14991278"),
    "C10u": ("L67", "Samsung CL31A106KOHNNNE 1206 10 µF 16 V X5R (낱개)", "엘레파츠 2675965"),
    "C1u": ("L56", "리드형 적층 세라믹 1 µF 50 V X7R (몸통 105)", "아이씨뱅큐 P014159115"),
    "R1k": ("L29", "탄소피막 1/4 W 5 % 1 kΩ (리드형, 갈·검·빨·금)", "사용자 보유 (ABCO CFR 같은 값)"),
    "R1k1206": ("L68", "Yageo RC1206JR-071KL 1206 1 kΩ 5 % 1/4 W (10개 단위)", "아이씨뱅큐 P011433924"),
    "R100k": ("L29", "탄소피막 1/4 W 5 % 100 kΩ (리드형, 갈·검·노·금)", "사용자 보유 (ABCO CFR 같은 값)"),
    "R100": ("L29", "탄소피막 1/4 W 5 % 100 Ω (리드형, 갈·검·갈·금)", "사용자 보유 (ABCO CFR 같은 값)"),
    "ZERO": ("SEV2", "RP2040-Zero 호환 (파츠파츠 PP-A799-2, Waveshare 배치)", "파츠파츠 2383"),
    "MUX": ("SEV2", "CD74HC4067 16채널 먹스 모듈 (파츠파츠 PP-A324, SparkFun BOB-09056 배치)", "파츠파츠 303"),
    "HDR": ("SE7", "핀헤더 1×40 2.54 mm 11.5 mm 1단 몰드 (잘라 씀) — 먹스 모듈 1×16 + 1×8", "아이씨뱅큐 P005666127"),
    "PADS6": ("", "패드만 — Adafruit 4876 플러그 선(모듈 쪽)을 아랫면에서 직접 납땜 (헤더 없음)", ""),
    "HDRZ": ("SE7", "핀헤더 1×40 2.54 mm — RP2040-Zero용 1×9 ×2, 몰드 뺌 (먹스 168 + 제로 144 = 312핀 → 1×40 9줄)", "아이씨뱅큐 P005666127"),
    "PERF": ("u06", "Coms BE163 양면 만능기판 80 × 120 (30 × 42 구멍)에서 자른 70 × 50 조각 (지그 09_기판지그)", "사용자 보유 BE163 4장"),
    "PERF1218": ("L22", "양면 만능기판 12 × 18 cm에서 자른 6행 띠 (SB 161.6 × 15.24, EL 45.5, ER 22.0) · 자투리", "메카솔루션 540645"),
    "RIBBON": ("C05", "EUNSUNG 2651-16P 플랫 케이블 28 AWG (16심 전부 사용)", "엘레파츠 425"),
    "RIBBONW": ("SE12", "EUNSUNG 2651-16P 1 m 더 — 가닥으로 갈라 기판 배선·W502", "엘레파츠 425"),
    "JSTXH": ("L66", "Adafruit 4876 JST-XH 호환 6핀 짝 (플러그 선 + 소켓 선, 각 약 20 cm, 26 AWG) — 모듈 쪽 150 · 끝 부속 쪽 50으로 자름", "엘레파츠 19324904"),
    "PJ313": ("L15", "GEC PJ-313 3.5 mm 스테레오 잭 (5핀 T·TN·R·RN·S, 노멀 접점, PCB형)", "디바이스마트 2674"),
    "TRS3M": ("L50", "Coms BC256 3.5 mm 스테레오 케이블 3 m (페달 쪽 플러그를 잘라 씀)", "엘레파츠 2925651"),
    "TRS15": ("C14", "Coms BC256 3.5 mm 스테레오 케이블 3 m 1가닥을 반으로 잘라 1.5 m × 2 (W702 그대로, W701 = 플러그 뒤 %.1f m + 나머지에서 W707)"
              % (_HN.W701_CUT / 1000.0), "엘레파츠 2925651"),
    "PEDAL": ("L43", "듀로 서스테인 페달 (스위치형 → 홀센서 개조)", "피아노모아"),
    "MAG5": ("L21", "네오디뮴 Ø5×2 N35 (센서 자석)", "대건상사 (dgmagnet)"),
    # power (R33, 2026-10-07)
    # 2026-10-26: same 4S1P 32700 form, leads and size as the 10/7 pack, bought as the '12.8V 10Ah DCXT60-3A' set (3 A charger included)
    "BATT": ("u01", "LiFePO4 12.8 V 4S1P 32700 '12.8V 10Ah DCXT60-3A' 세트 (표기 10 Ah, 계산 6 Ah · 76.8 Wh), BMS 4S 40 A, 출력 XT60 암 리드 + DC 5.5×2.1 충전 리드, "
                    "3 A LiFePO4 충전기 포함 (DC 5.5×2.1), 140 × 35 × 72 mm (눕혀 140 × 72 × 35), 약 0.9 kg", "사용자 구매 (쿠팡 9669099122 옵션 04)"),
    "XT60F": ("", "AMASS XT60 암 — BT601 팩 리드 끝에 달려 옴 (따로 사지 않음)", "BT601과 함께"),
    "XT60M": ("L80", "AMASS XT60-M 16 AWG 실리콘 선 10 cm — W601 전지 하네스 (리드 %d mm로 자름 + 홀더 꼬리 %d mm, 이은 전체 %d mm 이하, 빨강 수축)"
              % (_HN.LEAD_W601, _HN.STUB12, _HN.W601_MAX), "엘레파츠 12779718"),
    "XT60F_BENCH": ("L81", "AMASS XT60-F 16 AWG 10 cm — 벤치 12 V SMPS 어댑터 (빨강 수축, 회로도 밖)", "엘레파츠 12779719"),
    "FUSEH": ("u04", "ATC/ATO 블레이드 인라인 퓨즈 홀더 (덮개 끼움식, 12 AWG 꼬리, 40.1 × 11.1 × 33.8)", "사용자 보유"),
    "FUSE": ("u05", "ATO 표준 블레이드 퓨즈 5 A (주황, 32 V DC) — 켤 때 끊기면 7.5 A (갈색)", "사용자 보유 (퓨즈 세트)"),
    "SW": ("u03", "KCD1-104 로커 스위치 (4핀 2회로 ON-OFF, 패널 구멍 19 × 13, 두 회로 나란히)", "사용자 보유 (디바이스마트 1788과 같은 품번)"),
    "BUCK": ("L58", "XL4016 강압 모듈 XH-M401 (HAM6415) → 5.1 V", "아이씨뱅큐 P017179502"),
    "C24": ("C24", "Coms BT663 USB-A → C 측면 꺾임 20 cm (A 끝을 잘라 빨강·검정을 강압 출력에)", "엘레파츠 8105815"),
    "HUBDC": ("L17 부속", "허브 5 V 어댑터 선의 플러그 쪽 — 딸린 일자 DC 플러그 그대로 (잭 면 → 부트 끝 %.0f mm 이하, CAD 30; 바로 뒤에서 선을 R5로 위로)"
              % _HN.HUB_DC_MAX, "허브와 함께"),
    "PI5": ("L01", "Raspberry Pi 5 2GB", "아이씨뱅큐 P016286897"),
    "HUB": ("L17", "NEXTU 710U3 유전원 USB 허브 (10포트, 5 V DC 입력)", "다나와"),
    "USBAC": ("C04", "USB-A → C 데이터선 — Coms NA993 1 m ×2 (W201·W202), Coms HB466 50 cm ×6 (W203~W208; W205·W206은 CAD 0.3 m 자리라 남는 선을 묶음) (C 쪽 몰드 ≤ 12.5 × 7.6 × 25)", "엘레파츠 4313490 · 12185313 (사비)"),
    "C25": ("C25", "Coms NA977 USB-A(상향 꺾임) → B 25 cm (허브 업스트림)", "엘레파츠 4314354"),
    "DONGLE": ("L51", "Apple USB-C → 3.5 mm 헤드폰 어댑터 MW2Q3KH/A", "쿠팡 (Apple 정품)"),
    "GENDER": ("L52", "USB-C(F) → USB-A(M) 일자 젠더 — 짧은형, 포트 밖 %.1f mm 이하 (CAD 14; 치수 미공개라 받으면 잼)" % _HN.GENDER_MAX,
               "미정 — 예: 디바이스마트 Coms IF353 / BT781"),
    "AMP": ("L53", "HW-720 앰프 보드 (XH-M312 V4 배치, TPA3118D2, 66 × 53) — 전원 DC 5.5×2.1 잭(밑에서 잭 다리에 납땜), 입력 XH 3P INR·GND·INL, "
                   "출력 5 mm 2P 나사 단자 OUTL·OUTR (BTL), 볼륨 노브(빼서 보관); 12.8 V·8 Ω에서 약 8 W/ch", "사용자 보유 (사지 않음)"),
    # △18 (2026-10-07): speaker joints use the same XT60 as the battery -> L80 ×3 (W601 + 2), L81 ×3 (bench adapter + 2)
    "XT60M_SPK": ("L80", "AMASS XT60-M 16 AWG 10 cm (앰프 쪽 스피커 리드, 파랑 수축 + SPK)", "엘레파츠 12779718"),
    "XT60F_SPK": ("L81", "AMASS XT60-F 16 AWG 10 cm (스피커 꼬리선, 파랑 수축 + SPK)", "엘레파츠 12779719"),
    "SPK": ("L07", "삼미 CW-100B25 4인치 8 Ω 25 W", "쿠팡"),
    "SPKW": ("C13", "2심 전원·스피커선 16 AWG (18 AWG도 됨, 최대 약 3.4 A)", "엘레파츠 18388615 또는 보유 선"),
    # △16 (rev C, 2026-10-01) R31 screen B1
    "DISP7C": ("v4touch", "Waveshare 7-DSI-TOUCH-C 7인치 DSI 정전식 터치 1024×600 IPS (약 2.15 W, 동봉: 전원선 MX1.25 2핀 → 2.54 3핀, 22핀 200 mm 리본 2)", "G마켓 해외직구 4783965807"),
    "JMPFF": ("v4touch", "실리콘 점퍼 26 AWG 20 cm F/F 빨강 1 + 검정 1 (W606, Pi 헤더 쪽 끝)", "엘레파츠 9461190 · 9461199"),
    "JMPFF2": ("", "W606 다른 끝 — P603과 같은 점퍼 (따로 사지 않음)", ""),
    "JMPMM": ("v4touch", "실리콘 점퍼 26 AWG 20 cm M/M 빨강 1 + 검정 1 (W607, X601에 꽂는 끝)", "엘레파츠 9756990 · 9756998"),
    "JMPMM2": ("", "W607 다른 끝 — X602와 같은 점퍼 (따로 사지 않음)", ""),
    "DPWR": ("v4touch", "화면 동봉 전원선 W608의 2.54 3핀 하우징 (A605에 들어 있음)", "A605와 함께"),
    "DPWR2": ("", "W608 다른 끝 — MX1.25 2핀 플러그 (X604와 같은 선, 따로 사지 않음)", ""),
    "FFC22B": ("v4touch", "GUOCONN 0.5*22P*300*B FFC 22핀 0.5 mm 300 mm 반대면(B형)", "엘레파츠 18622271"),
    "FFC22A": ("v4touch", "GUOCONN 0.5*22P*300*A FFC 22핀 0.5 mm 300 mm 같은 면(A형, 보험)", "엘레파츠 18581287"),
    "SHRINK": ("C10", "열수축 튜브 세트 (빨강·파랑 포함)", "엘레파츠 8170311"),
}
