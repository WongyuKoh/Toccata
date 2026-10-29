# Toccata CU power chain — part verification (2026-09-28)

Scope: the parts in the CU power path (R28): USB-C PD trigger -> 5 A T fuse -> rocker switch -> 20 V bus -> XL4016 buck (5.1 V) -> Pi 5 (USB-C pigtail) + USB hub (DC jack). The goal is correct pin names and settings for a KiCad schematic.

> **2026-10-07 개정 D (△17): 전원 입력이 LiFePO4 전지 팩으로 바뀌었습니다(R33).** 지금 기준은 아래 **0장**입니다. 1장(PD 트리거)과 "20 V 버스"를 전제로 한 문장, 맨 끝의 넷 뼈대는 개정 C까지의 **기록**으로 남깁니다(지우지 않음). 2~7장의 부품 사실(강압·스위치·퓨즈·Pi·허브·MT666)은 그대로 유효하고, 입력 전압만 20 V → 12.8 V(10.0~14.6 V)로 바뀝니다.

Raw downloads (seller images, datasheet text) are in `scratchpad/research/raw/`.

Summary of what changed versus the brief (2026-09-28; items 1–2 are history since rev D):

1. **PD trigger (HAM6113):** it is a HUSB238 board. The chip marking "HUSB238 000DD" is visible in the seller photos. The voltage is set with **3 solder-bridge pad pairs, not a DIP switch**. **20 V is the factory default, with all pads open.** The seller's feature text and its small top thumbnail show a different board with a DIP switch, so the listing is inconsistent (see 1.1).
2. **New risk: the HUSB238 may refuse a 20 V/3 A (60 W) source and fall back to a lower voltage, possibly 5 V.** The cause is its 3.25 A current request when the ISET pin is left open. The board's ISET configuration is not documented. The D19 "power bank PD 20 V 3 A" must be bench-tested. A 65 W charger (20 V/3.25 A) is safe.
3. **XL4016 module (HAM6415):** it is the **CV-only XH-M401**. It has no constant-current pot, one single-turn panel pot and 2 heatsinks. Its terminals are silk-labelled 입력+/입력-/출력+/출력-. The XL4016 IC's own recommended input range is 8–36/40 V. The seller's "4 V" figure is marketing. It cannot make 5.1 V if the PD trigger falls back to 5 V.
4. **Coms BU914:** the seller detail image confirms a **5x20 mm** holder with ~30 cm leads and no fuse included. The listing title wrongly says "3cm 유리관". No electrical rating or wire gauge is published.
5. **Pi 5 config:** the config.txt key `usb_max_current_enable=1` and the EEPROM key `PSU_MAX_CURRENT=5000` are both confirmed by Raspberry Pi primary sources. Setting PSU_MAX_CURRENT=5000 already implies usb_max_current_enable. Keep both; it does no harm.

---

## 0. 전지 입력 (개정 D, 2026-10-07) — 지금 쓰는 전원

사용자 결정 2026-10-07(R33). USB-C PD 입력(A601 HUSB238 + 65 W 충전기 / PD 보조배터리, W601 C-C 선)을 빼고 LiFePO4 전지 팩을 XT60으로 바로 받습니다. 계산은 `src/sheets.py`의 `BATT`·`budget()`에 있고 SCH-06 표·주가 같은 값을 씁니다.

### 0.1 연결

```
BT601 LiFePO4 12.8 V 6 Ah (76.8 Wh, BMS 내장 — 받으면 확인), 팩 리드 끝 XT60 암 = X605
  ⇄ X606 XT60 수 (W601 하네스, L80, 16 AWG 10 cm): 빨강 → F601 홀더 선, 검정 → ★ 강압 IN−
  → F601 5 A T (0218005.MXP, BU914 홀더) → SW601 KCD1-101A → +12V8 버스 (10.0~14.6 V)
  → A602 XL4016 IN+ (5.1 V → Pi 5 · 허브 · 화면)   /   A702 HW-720 (TPA3118D2) DC 잭 다리 (△32, 2026-10-26)
넷: VBAT = 전지 + → XT60 → 퓨즈, VBAT_F = 퓨즈 → 스위치, +12V8 = 스위치 뒤 (전원 심볼)
```

충전 잭은 팩에 있습니다. 회로에는 충전 경로가 없습니다.

### 0.2 버스 전압 범위와 두 부하

- 위 끝: 14.6 V = LiFePO4 4셀 충전 끝 전압(3.65 V × 4). 충전하며 연주하지 않으므로 실제로는 쉰 전압 약 13.0~13.4 V에서 시작합니다.
- 아래 끝: BMS 저전압 차단, 보통 약 10 V(2.5 V × 4). 받으면 판매 정보로 확인합니다.
- 강압 XL4016: 5.1 V를 내려면 VIN ≥ VOUT + 약 2 V = 약 7 V(2장). 10 V − 7 V = 3 V 남음 → **범위 전체에서 동작**합니다.
- 앰프 TPA3110: PVCC 권장 8~26 V(보드 콘덴서 35 V) → 10.0~14.6 V 모두 안.
- 그래서 둘 다 BMS가 끊을 때까지 켜져 있고, 끊기면 한꺼번에 꺼집니다(Pi는 갑자기 꺼짐 → 읽기 전용 파일 시스템, R13).

### 0.3 앰프 출력과 음량 상한 (8 Ω, BTL)

TPA3110 Rds(on) 약 240 mΩ, BTL이면 직렬 2개 = 0.48 Ω (audio.md와 같은 계산).

| PVCC | 최대 진폭 Vp = PVCC × 8 / 8.48 | 이상값 Vp² / (2 × 8) | 1 % THD 실제 (약 90 %) |
|---|---|---|---|
| 20 V | 18.87 V | 22.3 W | 약 20 W/ch |
| 12.8 V | 12.08 V | 9.1 W | **약 8 W/ch** |

- 비: 8 / 20 = 0.40 → 10 × log10(0.40) = **−3.98 dB ≈ −4 dB** (전압 비로도 20 × log10(12.8 / 20) = −3.88 dB).
- 최대 출력에 필요한 입력(36 dB = ×63): √(8 W × 8 Ω) = 8.0 Vrms ÷ 63 ≈ **0.13 Vrms** (20 V 때 √(20 × 8) = 12.6 Vrms ÷ 63 ≈ 0.20 Vrms).
- 그래서 **소프트웨어 음량 상한을 20 V 때보다 약 4 dB 낮춰** 앰프가 찌그러지지 않게 합니다(D19, SCH-07 주 4). 리미터는 그대로 둡니다.
- 전지가 다 돼 가면 더 낮아집니다: 11 V면 (11 / 12.8)² = 0.74 → −1.3 dB. 끝 무렵 큰 소리에서 찌그러지면 충전합니다.

### 0.4 전력 예산

5 V 쪽: Pi 7.7 + 허브 2.0 + 동글 0.5 + 화면 2.15 = 12.35 W
강압 손실(효율 90 %): 12.35 ÷ 0.9 − 12.35 = 1.37 W → 앰프 밖 입력 = 13.72 W
앰프 평균: 2~6 W (20 V 표 값 그대로. 새 상한이 4 dB 낮아 실제로는 더 작음 → 보수적)

| | 계산 | 결과 |
|---|---|---|
| 평균 | 13.72 + 2 = 15.72 W, 13.72 + 6 = 19.72 W | **약 15.7~19.7 W** |
| 평균 전류 | 15.72 ÷ 12.8 = 1.23 A, 19.72 ÷ 12.8 = 1.54 A | **약 1.2~1.5 A** |
| 순간 최대 (최저음 강타, 앰프가 찌그러지기 시작) | 앰프 입력 2 × 8 W ÷ 0.8(효율, 대기 전류 포함 보수적) = 20.0 W → 13.72 + 20.0 | **약 33.7 W, 12.8 V에서 2.63 A** |
| 같은 순간, BMS 차단 직전 | 33.7 ÷ 10.0 | 약 3.4 A |
| (비교) 이전 방식 | 개정 C D19 52 W의 앰프 몫 = 52 − 11.33 = 40.67 W, × 8 / 20 = 16.27 W → 13.72 + 16.27 | 약 30.0 W, 2.34 A |

- 순간 최대는 **약 30~34 W, 12.8 V에서 약 2.3~2.6 A**입니다. 표에는 큰 값(33.7 W, 2.6 A)을 씁니다.
- D19 글의 15.69~19.69 W와 0.03 W 차이는 반올림입니다(여기서는 손실을 12.35 ÷ 0.9로 계산).

### 0.5 퓨즈 5 A T (그대로)

- 정상: 순간 최대 3.4 A(10 V) < 5 A. 218 시리즈는 1.5 × In = 7.5 A 아래에서 1시간 넘게 끊기지 않으므로(4장) 연주 중에는 끊기지 않습니다.
- **전지는 PD 전원처럼 스스로 전류를 3.25 A로 묶지 않습니다.** 단락이면 수십 A 이상이 흐를 수 있어 이제 퓨즈가 실제 보호입니다(BMS 단락 보호와 함께). 홀더를 XT60(X606) 바로 뒤 + 선에 둡니다.
- 돌입 전류: 스위치를 켤 때 강압·앰프 입력 콘덴서(약 0.5~1.5 mF)를 채웁니다. 선로·스위치·퓨즈 합 약 0.1 Ω이면 첫 순간 12.8 ÷ 0.1 = 128 A, 시정수 0.1 Ω × 1.5 mF = 0.15 ms → I²t ≈ 128² × 0.15 ms ÷ 2 ≈ 1.2 A²s. 퓨즈 녹는 I²t 111 A²s보다 훨씬 작아 퓨즈는 괜찮습니다. BMS가 이것을 단락으로 볼 수 있으니 스위치를 10번 켜고 끄며 확인합니다(검토 R12).
- 강하: 0.0104 Ω × 1.5 A ≈ 16 mV, 무시해도 됩니다.

### 0.6 KCD1 스위치

- DC 차단 정격이 공개되지 않았습니다(3장). AC 정격을 DC에서 50 %로 줄이면 약 3 A이고, 평균 1.2~1.5 A는 그 안입니다.
- **소리를 멈춘 뒤 끕니다.** 그러면 끊는 전류가 앰프 대기 + 5 V 쪽뿐(약 1.1 A)이라 불꽃이 작습니다.

### 0.7 연주 시간

76.8 Wh × 0.9(쓸 수 있는 몫) = 69.1 Wh → 69.1 ÷ 15.72 = 4.40 h, 69.1 ÷ 19.72 = 3.50 h → **약 3.5~4.4시간**.

### 0.8 접지 · 극성 · 충전 · 벤치

- 별 접지점은 강압 IN− 단자 그대로(△5). 전지 −(W601 검정)와 앰프 GND 선이 여기서만 만납니다.
- 극성: XT60은 모양으로 극성이 정해집니다. 하네스 X606을 납땜한 뒤 빨강 = +인지 전지 쪽과 맞춰 멀티미터로 확인합니다. 강압 모듈은 역극성 보호가 없습니다(2장).
- 충전: 뚜껑 L을 열고 사용자 LiFePO4 충전기(14.6 V)를 팩 DC 잭에 꽂습니다. 충전기가 부하를 단 채 충전해도 된다고 밝히지 않으면 **충전하며 연주하지 않습니다**(충전 중 버스가 14.6 V까지 오르고, 충전기의 끝 판정이 부하 전류 때문에 틀어질 수 있음).
- 벤치 시험: 12 V SMPS 출력에 XT60 암(L81)을 달아 **전지 대신** X606에 꽂습니다. **둘을 함께 꽂지 않습니다.** SMPS 선의 + 극성을 먼저 잽니다.

### 0.9 받으면 확인할 것

1. 무부하 전압 약 13.0~13.4 V(10 V 아래면 쓰지 않음).
2. BMS가 있는지(판매 정보·라벨), 저전압 차단 전압(보통 약 10 V), 연속 방전 한도(5 A 이상이면 충분).
3. XT60 극성(하네스 납땜 뒤, 벤치 SMPS 쪽도).
4. 스위치 10번 켜고 끔 — BMS가 끊기지 않음.
5. 처음 다 쓸 때 꺼지기 직전 버스 전압을 적어 둠.

---

## 1. (기록 — 개정 C까지) PD trigger — icbanq P017179277 "100W QC PD 트리거 디코이 고정출력 제어 모듈 5V-20V (HAM6113)"

Source: icbanq product page plus its detail images (JENO, `gi.esmplus.com/jeno0921/HAM6113/d1.jpg`, `d2.jpg`). The detail photos show a purple board with the silk text "ZYPDH" and "YZX" on the back and an IC marked "HUSB238 000DD 2117".

### 1.1 Voltage selection (verified from the seller's "출력 전압 설정" figure)
- Voltage is set by **3 SMD solder-jumper pad pairs** along the right edge of the component side. In this orientation the USB-C receptacle is at the bottom and the output pads are at the top. The pads connect VSET resistors: the markings read "15C" = 14.0 kΩ and "01C" = 10.0 kΩ (EIA-96 codes).

| Output | Top pair | Middle pair | Bottom pair |
|---|---|---|---|
| **20 V (default)** | open | open | open |
| 15 V | bridge | open | open |
| 12 V | open | bridge | open |
| 9 V | bridge | bridge | open |
| 5 V | open | bridge | bridge |

- **For 20 V, do nothing. Leave all 3 pairs open.** Seller spec: "출력 전압 지원: 5V, 9V, 12V, 15V, 20V (기본 20V)".
- The HUSB238 datasheet explains the mechanism. A 100 µA current source on VSET flows through R(VSET), and VSET open means 20 V. The table is 0 Ω = 5 V, 6.04 k = 9 V, 10 k = 12 V, 14 k = 15 V, 17.8 k = 18 V, open = 20 V. The request is the lower of the VSET setting and the internal fuse setting SNK_PDO2 (default 20 V).
- **Inconsistency in the listing.** The feature text says "딥 스위치 조정에 따른 출력 전압 설정", and the small thumbnail at the top of `d1.jpg` shows a different board with S1–S3 DIP switches and "VCC/GND" pads. The main product photo and all detail photos show the HUSB238 solder-bridge board. If a DIP-switch board arrives instead, set it from its own silk table and measure.

### 1.2 Output pads (for the schematic)
- There are 4 through-hole pads in a row on the edge opposite the USB-C. Seller label: **"출력 +" = the 2 left pads, which are round with a "+" silk mark. "출력 −" = the 2 right pads, which are square with a "−" silk mark.** This is as seen from the component side with USB-C at the bottom. On the back the silk is mirrored ("− − + +").
- Suggested KiCad symbol: a 4-pin module, `VOUT+` ×2 (pads 1–2) and `GND` ×2 (pads 3–4). Pad pitch ≈ 2.5 mm across the 10 mm edge; measure it. Input is the on-board USB-C receptacle.
- Board: 10 × 16.4 mm (16 mm without the USB receptacle), 4.4 mm thick.
- There is **no load-switch MOSFET** on the board. The photos show only the IC, 2R2, a 1 µF-class capacitor, 01A, 15C, 01C and the pads, and the HUSB238's GATE pin is unused. **VOUT = VBUS directly.** It is 5 V at attach, then 20 V after the contract, which takes about 1 s.

### 1.3 Current
- Seller: "최대 출력: 20V 5A 100W (QC/PD 충전기 및 연결 케이블 사양에 따라 달라집니다)". 5 A needs a 100 W source and a 5 A e-marked cable. Toccata needs ≤ ~3 A, so the board is not the limit.
- The HUSB238 requests the lower of the ISET setting and the fuse default of 3.25 A. **ISET open = 3.25 A request.**

### 1.4 Fallback when the source cannot give 20 V (datasheet "RDO determination")
- The chip walks the source PDOs from the highest voltage down. It picks the first PDO where **V_PDO ≤ requested V and I_PDO ≥ requested I**. The default fuse option is "continue to the next-lower PDO". The seller gives examples: a 5/9/12 V charger with the board set to 20 V gives 12 V, and a 5/9/15 V charger gives 15 V.
- **Current trap.** If ISET is open (3.25 A), a 20 V/3 A PDO fails the current test, and so do 15 V/3 A, 12 V/3 A and so on. Adafruit's HUSB238 guide confirms this: "If you configure the board for 3A but your power supply isn't up to the task, you may see the wrong voltage."
  - The ZYPDH's ISET resistor, if any, is not documented. **The 20 V/3 A power bank of D19 may therefore give 15 V, 12 V or even 5 V.** A 65 W charger advertising 20 V/3.25 A is safe.
- **No PD at all** means VOUT stays 5 V. Examples are a QC-only charger or a USB-A-to-C cable. The HUSB238 datasheet lists only PD 3.0, Type-C 1.4, Apple divider 3 and BC1.2, which are all 5 V methods. The seller's "QC2.0/QC3.0/AFC" claim is not backed by the datasheet.
- Effect on Toccata:
  - 15/12/9 V: the XL4016 still makes 5.1 V, and the amp still works because TPA3110 PVCC is 8–26 V, with less headroom.
  - **5 V: the buck cannot make 5.1 V.** The Pi browns out, and the amp (PVCC min 8 V) is off.
- **Instruction:** after assembly, measure the 20 V bus with every source you intend to use. It must read 19–21 V. HUSB238 OVP is at 1.2 × the requested voltage, and UVP is off by default.

### 1.5 Inrush note
- The rocker switch sits after the trigger, so the charger has already negotiated 20 V when the switch closes. Closing the switch then dumps inrush into the buck's input electrolytic (470 µF class) and the amp's bulk capacitors.
- Most chargers ride through this. If the bus drops to 5 V or the charger resets when you flip the switch, add a small NTC (≈5 Ω, 3 A class) in series, or accept it.

---

## 2. Buck — icbanq P017179502 "200W XL4016 DC-DC 강압 컨버터 모듈 IN 4-40V OUT 1.25-36V 5A **CV** (HAM6415)"

Source: seller detail images (`gi.esmplus.com/xodhks3550/HAM6415/d1–d3.jpg`). The back silk reads **"XH-M401"**.

- **Terminals** (two 2-way screw blocks). Seller label, viewed from the component side with the heatsinks at the top and the pot shaft pointing toward you:
  - left block: top = **입력− (IN−)**, bottom = **입력+ (IN+)**
  - right block: top = **출력− (OUT−)**, bottom = **출력+ (OUT+)**
  - The PCB silk has a "+" next to the lower terminal of each block.
  - KiCad: 4-pin module, `IN+`, `IN−`, `OUT+`, `OUT−`. On this CV-only buck, IN− and OUT− are the common ground. **Verify continuity of about 0 Ω before relying on it.**
- **Adjustment:**
  - One rotary panel potentiometer, CV only. It has a knurled 7 mm-hole panel bushing (seller: hole Φ7), a 15 mm shaft and a 4.8 mm thread. Clockwise raises the output ("출력 전압 증가 ▶ 시계 방향").
  - **There is no constant-current pot.** The product name says "CV".
  - Because it is a single-turn pot over 1.25–36 V, 5.1 V is touchy to set. Set it with no load first, then under load. Afterwards, lock the shaft (thread-lock or paint) or remove the knob so it cannot be bumped: at 20 V input a bumped pot can put up to ~19 V on the Pi.
- **Current:** 5 A continuous, 8 A max with extra cooling ("최대 출력 전류: 8A (추가 방열 필수)"). 200 W max, 180 kHz, 94 % efficiency. The seller claims over-current, over-temperature and short-circuit protection. The XL4016 folds back to 48 kHz on a short.
- **Heatsinks:** two finned aluminium heatsinks, one on the XL4016E1 (TO-220-5) and one on the TO-220 output diode.
  - Size 60.8 × 40.3 mm, total height 29 mm, 4 corner mounting holes. The size is not stated; M3 is typical, so measure.
  - There is a red LED output indicator ("출력 표시 LED").
- **Dropout / minimum input:**
  - XL4016 IC: max duty 100 %, dropout 0.3 V (LCSC summary). The IC's recommended VIN is 8–36 V; the product page says 4–40 V.
  - In practice, keep VIN ≥ VOUT + 2 V at 3–5 A, so **≥ ~7 V for 5.1 V**.
  - 20/15/12/9 V inputs are OK. A 5 V fallback from the trigger is not.
- Reverse-polarity protection is not stated; assume there is none.

---

## 3. Rocker switch KCD1-101(A), 2-pin SPST

- The rating is marked on the body. Typical is **6 A 250 VAC / 10 A 125 VAC**. **No DC rating is published** by the sellers found (Cytron, ampul.eu, Daier). Contact resistance is ≤ 35–50 mΩ, life ≥ 10,000 cycles, panel cut-out ≈ 19.2 × 13.2 mm (21 × 15 mm bezel).
- DC use: the LCSC engineering guide says to derate the AC rating by at least 50 % for DC. That gives roughly 3 A at ≤ 30 VDC, which is right at Toccata's worst-case 20 V/3 A.
  - It is acceptable for hobby use because the PD source limits current. Switch off with the music stopped, which lowers the break current.
  - If you want margin, use a switch with an explicit DC rating (≥ 5 A at 24–32 VDC).
- **Terminals are unmarked and interchangeable**, as expected for an SPST switch. In KiCad use `SW_SPST` with pins 1 and 2 (either can be LINE or LOAD). The terminals are 4.8 mm (0.187") quick-connect/solder lugs on most KCD1-101. Confirm on the part.

---

## 4. Fuse holder Coms BU914 + Littelfuse 0218005.MXP

- **BU914** (comsmart it_id=18176):
  - The detail image says "20mm*5Φ 유리관 휴즈용 원형 휴즈 홀더", "배선길이: 약 30cm", "휴즈는 미포함". It is a screw-cap inline holder with red leads.
  - The listing title's "(3cm 유리관 휴즈용)" contradicts the image; BU915 is also listed as "(2cm …)". The image text wins: it is 5x20.
  - **No voltage/current rating and no AWG are published.** Check that the lead is about 20–22 AWG copper. That is fine for 3 A over 30 cm (≈ 16 mΩ, ≈ 50 mV).
  - KiCad: `Fuse` symbol, 2 pins, or `FuseHolder`.
- **0218005.MXP**:
  - Littelfuse 218 series, 5x20 mm glass, **time-lag (T), 5 A, 250 VAC**, breaking capacity 50 A @ 250 VAC.
  - DigiKey: cold resistance 0.0104 Ω, melting I²t 111 A²s. The 218 series meets IEC 60127-2 sheet 3 (time-lag).
  - DigiKey lists **no DC voltage rating**.
- Suitability at 20 VDC / ~3 A:
  - Voltage drop ≈ 31 mV and dissipation ≈ 0.1 W, which is fine.
  - Under the IEC time-lag curve the fuse does not open below ~1.5 × In (7.5 A) for ≥ 1 h. So it will **never trip before the PD source's own OCP** (a 3.25 A source trips at about 3.5–4 A). It is only a fire/short backstop.
  - The prospective fault current from a USB-PD source is a few amps. Interrupting that at 20 V DC is trivial for a 250 V glass fuse, so the missing DC rating is not a practical concern.
  - 5 A T is appropriate. Do not go below ~4 A T, because of the inrush in 1.5.

---

## 5. Raspberry Pi 5 from a PD-less 5.1 V buck via USB-C

Primary sources: the Raspberry Pi white paper "USB Power Delivery on Raspberry Pi 5" (RP-009856-WP-1), the RPi documentation `eeprom-bootloader.adoc` (PSU_MAX_CURRENT) and `power-supplies.adoc`.

- Without a 5 V/5 A PD contract, the Pi "will assume a 5V 3A supply by default". It then "automatically limit[s] the total power available to the USB ports to 600mA (instead of 1.6A)", disables USB boot, and shows a desktop low-power warning.
- **EEPROM key: `PSU_MAX_CURRENT=5000`**
  - Pi 5 only. It "instructs the firmware to skip USB power-delivery negotiation and assume … the given current rating". Values are typically 3000 or 5000. Default is "".
  - Set it with `sudo rpi-eeprom-config --edit`, add the line, save and reboot.
- **config.txt key: `usb_max_current_enable=1`** in `/boot/firmware/config.txt`.
  - It allows 1.6 A to the USB ports instead of 600 mA. It is "set automatically if … negotiated 5V 5A … or if PSU_MAX_CURRENT has been set to 5000".
  - Check it with `vcgencmd get_config usb_max_current_enable`.
  - Setting both is redundant but harmless. **In Toccata the Pi's own USB load is tiny**: the self-powered hub upstream plus the Apple dongle, both well under 600 mA. So these keys mainly remove the warning and the USB-boot block.
- **GPIO powering** (header pins 2 and 4 = 5 V; GND on 6, 9, 14, 20, 25, 30, 34, 39):
  - It is officially possible. The white paper describes it and an RPi engineer on the forum says "Yes, you can power over the GPIO". The same PSU_MAX_CURRENT setting applies.
  - It **bypasses the USB-C input protection**. The Pi 5 has **no polyfuse** on the 5 V header, and Dupont pins/jumpers are poor at 3–5 A.
  - The design's choice of USB-C keeps the Pi's input protection, uses a keyed and removable connector, and leaves the header free. Keep it.
- **Back-feed from the self-powered hub:**
  - RPi docs (Back-powering): a badly made powered hub "will result in the powered USB hub supplying power to the host Raspberry Pi… bypasses the protection circuitry".
  - In Toccata both the hub and the Pi come from the same switched 5.1 V bus, so the risk is small. Still test it: feed only the hub, with the Pi's USB-C unplugged and the hub's upstream cable connected to the Pi. **Pi header pin 2 to pin 6 must read ≈ 0 V.**
  - If it does not, never run the hub without the Pi's supply. Cutting VBUS in the upstream cable can stop some hubs from enumerating.
- **Voltage at the Pi:** set the buck so that **pin 2–6 reads 5.10–5.20 V under load**, and stay ≤ 5.25 V. The pigtail's wire gauge is unknown (see 7), so expect a 0.05–0.15 V drop at 3 A. Check with `vcgencmd get_throttled` (0x0 = no undervoltage).

---

## 6. NEXTU / 유우젠 710U3, 10-port USB 3.0 powered hub (danawa pcode 29865749)

- Could not be re-verified today. The manufacturer's image host (`ez-net.co.kr` → `eznetimg.synology.me`) refused TLS from here, and danawa's text has no power specification.
- Earlier-session finding (repo `archive/docs/report/toccata-build-v3.html`, L17 card, R28 check on 9/25, from the danawa detail and manufacturer images): **DC 5 V 3 A adapter (15 W)**. The hub also works bus-powered ("외부전원 겸용"). It is 48 × 228 × 24 mm, 130 g, with a 0.6 m detachable upstream cable.
- **Barrel size and polarity are not published.** Do not assume 5.5 × 2.1 mm.
  - Read the polarity symbol on the adapter label. It is normally centre-positive, but verify.
  - Before cutting, plug the adapter in and measure the centre pin against the sleeve. After cutting, find which wire goes to the centre with a continuity test.
  - Measure the plug OD/ID with calipers if you ever want a separate plug.
  - KiCad: treat it as a 2-wire lead: `+5V1` → centre (+), `GND` → sleeve.
- Load budget on the hub's 5 V:
  - 8 RP2040-Zero boards at ≈ 25–30 mA each.
  - 89 DRV5055 sensors. TI rev C (06/2026) gives 2 mA typ / 4 mA max at 3.3 V; rev B (04/2021) gave 6 / 10 mA. Old stock may follow rev B.
  - Total ≈ 0.4 A typical, ≈ 1.2 A worst case, plus the hub controller. This is well inside 3 A and inside the 900 mA per-port limit (≈ 170 mA per module worst case).

---

## 7. MAXTEK MT666 "USB C타입 제작용 케이블 2선 Type-C Male DIY PD 전원"

Source: the MAXTEK detail image on compuzone (ProductNo 1241239).

- Construction: a molded Type-C **male** plug with a 2-wire flying lead, **red = +, black = −**, "제작용 DC2선". Length about 25 cm, PVC jacket.
- **Not stated anywhere:** wire AWG, current rating, and whether a CC resistor is inside.
  - Generic 2-wire Type-C male pigtails often contain a 5.1 kΩ Rd on CC so they can pull 5 V from a charger. Some have CC unconnected.
  - **Neither case makes the plug a USB-C "default source"**, which would need an Rp such as 56 kΩ to VBUS.
- Effect on the Pi:
  - A sink does not need CC to take power from a VBUS that is already live, and the buck output is always on.
  - With no Rp the Pi finds no PD source and uses its non-PD default. With `PSU_MAX_CURRENT=5000` the PD step is skipped entirely.
  - An Rd in the plug sits in parallel with the Pi's own Rd on CC, which is harmless.
  - Confidence is medium: no primary Pi 5 statement about CC-floating operation was found. **Bench-test before final assembly:** buck → MT666 → Pi, confirm it boots, and confirm `get_throttled` = 0x0 under load.
- Wire gauge: if the leads are thin (24–26 AWG), 25 cm at 3 A drops about 0.1 V. Set the buck by measuring at the Pi header (see 5). A pigtail rated 3 A / 20–22 AWG is better.
- KiCad: 2-pin connector `J_PI_PWR`, pin 1 `VBUS` (red) = `+5V1`, pin 2 `GND` (black).

---

## Suggested net and ref-des skeleton (power sheet) — 기록 (개정 C까지, 개정 D는 0.1)

```
J1  PD trigger module (HAM6113/HUSB238): VOUT+ x2 -> net VBUS_PD ; GND x2 -> GND   [all VSET pads open = 20 V]
F1  0218005.MXP 5A T in BU914 inline holder: VBUS_PD -> F1 -> net VBUS_F
SW1 KCD1-101 SPST: VBUS_F -> SW1 -> net +20V
U1  XH-M401 (XL4016) : IN+ <- +20V, IN- <- GND, OUT+ -> +5V1, OUT- -> GND (common)   [set 5.10-5.20 V at Pi]
J2  MAXTEK MT666 pigtail: red <- +5V1, black <- GND -> Pi 5 USB-C (J_PWR)
J3  hub DC lead (cut adapter cable): centre(+) <- +5V1, sleeve <- GND   [verify polarity]
amp XH-A232 VCC/GND <- +20V/GND
```

## Sources
- icbanq P017179277 (HAM6113): https://www.icbanq.com/P017179277 ; detail images https://gi.esmplus.com/jeno0921/HAM6113/d1.jpg , https://gi.esmplus.com/jeno0921/HAM6113/d2.jpg
- HUSB238 datasheet (Hynetek, Rev 2.0, Adafruit mirror): https://cdn-learn.adafruit.com/assets/assets/000/125/150/original/husb238_datasheet_full.pdf
- Adafruit HUSB238 guide (3 A request caveat): https://cdn-learn.adafruit.com/downloads/pdf/adafruit-husb238-usb-type-c-power-delivery-breakout.pdf
- done.land HUSB238: https://done.land/components/power/powersupplies/usb/usbtriggers/husb238/
- icbanq P017179502 (HAM6415/XH-M401): https://www.icbanq.com/P017179502 ; images https://gi.esmplus.com/xodhks3550/HAM6415/d1.jpg , d2.jpg , d3.jpg
- XL4016E1 (LCSC C55881): https://www.lcsc.com/product-detail/C55881.html ; AZ-Delivery XH-M401: https://www.manualslib.com/manual/3657066/Az-Delivery-Xh-M401.html
- KCD1 ratings/derating: https://www.lcsc.com/blog/kcd1-switches-rocker-switches-guide/ , https://www.chinadaier.com/kcd1-101-12v-dc-20a-mini-rocker-switch/ , https://www.cytron.io/p-2-pin-kcd1-101-rocker-switch-6a-250v-red
- Coms BU914: https://comsmart.co.kr/cmart/shop/item.php?it_id=18176 (detail image https://comsmart.co.kr/product/BU914.jpg)
- Littelfuse 0218005.MXP: https://www.digikey.com/en/products/detail/littelfuse-inc/0218005-MXP/777604 ; https://www.littelfuse.com/218
- Raspberry Pi USB PD white paper: https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-009856-WP-1-USB%20Power%20delivery%20on%20Raspberry%20Pi%205.pdf
- RPi docs PSU_MAX_CURRENT: https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/eeprom-bootloader.adoc ; power/back-powering: https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc
- RPi forum, Pi 5 GPIO power: https://forums.raspberrypi.com/viewtopic.php?t=358008
- 710U3: https://nextu.kr/product/%EC%9C%A0%EC%9A%B0%EC%A0%A0-10in1-%EB%A9%80%ED%8B%B0%ED%8F%AC%ED%8A%B8-usb%ED%97%88%EB%B8%8C-710u3/286/ ; https://prod.danawa.com/info/?pcode=29865749
- MAXTEK MT666: https://www.compuzone.co.kr/product/product_detail.htm?ProductNo=1241239 (detail image https://image3.compuzone.co.kr/img/product_img_detail/2025/0513/1241239/3cf3c30d9588d2cae4f3a8b779e602c5.jpg)
- TI DRV5055 datasheet rev C: https://www.ti.com/lit/gpn/DRV5055
