# Toccata 아두이노 버전 (개정 U1) — Arduino Uno + 노트북

라즈베리파이 버전(이 폴더 위의 `hardware/pcb`, 개정 E)과 **따로 세울 수 있는 두 번째 구성**입니다. 건반·센서 기판·끝 부속·페달 센서·출력물·전지·앰프·스피커는 같고, 다음 두 가지만 다릅니다.

- 건반을 읽는 칩: 옥타브마다 RP2040-Zero 1개(8개) 대신 **Arduino Uno 1개**가 88건반과 페달을 읽습니다.
- 메인 프로그램: Raspberry Pi 5 대신 **노트북**에서 FluidSynth 음원과 리듬게임을 돌립니다.

## 다시 만들기

```
python3 hardware/pcb/src/build_uno.py     # U-01~U-04 SVG + CSV + 연결·글자 겹침 검사 (문제 0이면 종료 코드 0)
```

Pi 버전 도면(`build.py`)에는 손대지 않습니다. 원본은 `hardware/pcb/src/uno_sheets.py`입니다(핀 배정, 리본, 자르는 길이, 부품 표가 모두 여기에 있음).

## 파일

| 파일 | 내용 |
|---|---|
| `schematic/U-01_system.svg` | 시스템 연결도, 새 선 W801~W811, 빠지는 것·새로 필요한 것 |
| `schematic/U-02_control_board_MB-U.svg` | 옥타브 제어 기판 MB-U: 제로 없이 먹스만, 버스 패드 J303 |
| `schematic/U-03_bus_board_UB_uno.svg` | 버스 기판 UB + Arduino Uno + 페달 입력 + 버스 5 V 감시 |
| `schematic/U-04_power_audio.svg` | 전원(5.1 V는 UB로만) · 소리(노트북 → J701) · 전원 예산 |
| `pins_uno.csv` · `ribbon_uno.csv` · `changes_uno.csv` · `netlist_uno.csv` | 우노 핀, 리본 10심 핀과 모듈별 길이, 바뀌는 부품, 도면별 넷 |

## 핵심

- 모듈마다 10심 리본 하나(W801~W807): 1 GND · 2 SIG · 3 GND · 4~7 S0~S3 · 8 EN · 9 +5V_B · 10 GND. 모듈 쪽은 J303에 납땜하고, UB 쪽은 IDC 2×5 소켓으로 꽂습니다.
- 우노 D2~D5 = S0~S3(7개 포트 공통, 1 kΩ). D6~D12 = O1~O7 EN(포트마다 1 kΩ, 하나만 LOW). A0 = SIG(포트마다 1 kΩ → 합침 → 2.2 kΩ). A1 = 페달, A2 = 버스 5 V 감시(10k/10k).
- 센서·먹스 전원은 3.3 V에서 **5.1 V(+5V_B)**로 바뀝니다. 전지 → XL4016에서 받습니다. 우노 5V 핀은 연결하지 않고 GND만 함께 씁니다.
- 먹스 모듈 안의 EN–GND 10 kΩ 때문에 우노가 리셋 중이면 먹스 7개가 함께 켜집니다. SIG 1 kΩ가 서로 부딪는 전류를 막습니다.
- 스캔은 약 600~700회/초(계산값)이고 ADC는 10비트입니다. Pi 버전보다 세기 표현이 거칩니다.

펌웨어는 `firmware/uno/`, 노트북 프로그램은 `sw/README.md`의 "아두이노 버전" 절에 있습니다. 아직 실물로 만들어 보지 않은 설계입니다.
