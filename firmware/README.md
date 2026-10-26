# Toccata 옥타브 기판 펌웨어 (RP2040-Zero)

옥타브 제어 기판 MB(SCH-03)의 RP2040-Zero에 올리는 펌웨어입니다. 먹스(CD74HC4067)로 센서 12개(DRV5055A2)를 차례로 읽어 건반마다 자석 위치를 구하고, 누르는 속도로 벨로시티를 계산해 USB MIDI로 보냅니다. USB 이름은 ID 점퍼로 정해지며, O4 기판은 `Toccata O4`(C4 = MIDI 60 ~ B4 = 71)입니다.

같은 펌웨어를 7장 모두에 올립니다. ID 점퍼(JP301~JP303)가 하나도 닫혀 있지 않으면 O4로 동작하므로, 점퍼를 납땜하기 전의 한 옥타브 시험에도 그대로 씁니다. O4 기판으로 굳힐 때는 JP303만 닫습니다(`hardware/pcb/netlist/id_jumpers.csv`).

**아직 실제 보드에 올려 보지 않았습니다.** Mac에서 빌드와 키 판정 시험(아래)까지만 확인했습니다. USB 인식, 스캔 속도, 실제 센서 값은 보드를 꽂아 확인해야 합니다.

## 1. 펌웨어 올리기

빌드한 파일: [`dist/toccata_octave.uf2`](dist/toccata_octave.uf2) (pico-sdk 2.1.1, 2026-10-26 빌드)

1. RP2040-Zero의 **BOOT** 버튼을 누른 채 USB-C를 맥에 꽂습니다. 이미 꽂혀 있으면 BOOT를 누른 채 RESET을 눌렀다 뗍니다.
2. `RPI-RP2` 드라이브가 뜨면 uf2 파일을 끌어다 놓습니다. 복사가 끝나면 보드가 스스로 다시 시작합니다.
3. 맥에서 뽑아 라즈베리파이 USB에 꽂습니다.

라즈베리파이에서 바로 올릴 수도 있습니다. Pi OS Lite는 드라이브를 자동으로 붙이지 않으므로 직접 마운트합니다.

```bash
lsblk -o NAME,LABEL,SIZE
```

LABEL이 `RPI-RP2`인 장치(예: `sda1`)를 확인한 뒤:

```bash
sudo mount /dev/sda1 /mnt && sudo cp firmware/dist/toccata_octave.uf2 /mnt/ && sync; sudo umount /mnt
```

복사 직후 보드가 다시 시작하며 드라이브가 사라지므로 `umount` 오류는 무시해도 됩니다.

## 2. 한 옥타브 시험

**전원을 넣을 때 건반은 모두 올라와 있어야 합니다.** 켜지는 순간 센서마다 쉼 값을 64번 읽어 평균합니다. 켠 뒤 건반마다 **첫 타건이 바닥 위치를 가르치므로**, 첫 음의 세기는 조금 어긋날 수 있습니다.

### 인식 확인

```bash
./sw/toccata-midi list
```

`Toccata O4`가 보이면 됩니다. `amidi -l`에서는 `Toccata O4 MIDI 1`로 보입니다.

### 센서 확인 (콘솔)

보드는 MIDI와 함께 텍스트 콘솔(USB 시리얼)도 엽니다. 옥타브 하나만 꽂았다면 라즈베리파이에서는 `/dev/ttyACM0`입니다.

```bash
sudo apt-get install picocom
```

```bash
picocom /dev/ttyACM0
```

종료는 `Ctrl+A` 다음 `Ctrl+X`입니다. 맥에 꽂았을 때는 `screen /dev/cu.usbmodem*`(종료 `Ctrl+A` 다음 `K`)을 씁니다. 여러 옥타브를 꽂으면 `/dev/serial/by-id/usb-Toccata_Toccata_O4_*`처럼 이름으로 고릅니다.

| 키 | 하는 일 |
|---|---|
| `s` | 상태표: 건반별 지금 값, 쉼 값, 바닥까지 폭(swing), 자석 극, 문턱 4개, 상태, 초당 스캔 수 |
| `w` | 센서 보기 켜기/끄기: 0.1초마다 `C4 2207/0%`처럼 ADC 값과 자석 행정(0 % 쉼 ~ 100 % 바닥) |
| `e` | 음 기록 켜기/끄기(기본 켜짐): note-on/off 벨로시티와 앞끝 속도, 버린 유령 다시 눌림 |
| `r` | 쉼 값 다시 재기(건반을 모두 올린 채). 그 전에 All Notes Off를 보냅니다 |
| `h` | 도움말 |

정상 값:
- 쉼 값은 백건 약 2207, 흑건 약 2138입니다(±100 정도).
- swing은 처음에 설계의 0.75배(백 491, 흑 618)로 시작하고, 끝까지 한 번 누르면 실제 폭(설계 백 655, 흑 824)으로 넓어집니다.
- `FAULT`는 쉼 값이 1800~2600 밖이라는 뜻입니다. 리본 배선, 센서 핀 방향, 또는 켤 때 눌려 있던 건반을 확인합니다.
- 누르면 값이 **올라가야** 합니다(S극 아래). 내려가면 콘솔에 `magnet N pole down?`이 뜨고 그 건반만 반대로 셉니다. 그 첫 누름은 소리가 나지 않습니다.

### MIDI와 소리

```bash
./sw/toccata-midi monitor --input 'Toccata O4'
```

누르면 `note_on`과 벨로시티, 떼면 `note_off`가 보입니다. 소리는 [sw/README.md](../sw/README.md)의 오디오 설정을 마친 뒤 다음 명령으로 냅니다.

```bash
./sw/toccata-midi synth
```

## 3. 동작 규칙

| 항목 | 값 | 근거 |
|---|---|---|
| 스캔 | 먹스 채널을 바꾸고 4 µs 기다린 뒤 ADC 2번 평균. 12건반 한 바퀴 약 0.1 ms(예상, 콘솔 `s`의 scans/s로 확인) | SCH-03 주 7 |
| 위치 | Ø5×2 자석의 축 자기장 모델로 ADC 값을 자석 행정 p(0 쉼 ~ 1 바닥)로 바꿈. 간격 백 10.82 → 5.60 mm, 흑 13.35 → 5.32 mm | `hardware/pcb/README.md` 센서 표 |
| note-on | p 0.85를 넘을 때. 벨로시티는 p 0.55 → 0.85 사이 시간(앞뒤 스캔 사이를 보간)으로 잰 자석 속도 × 1.91(백) / 1.18(흑) = 앞끝 속도를 로그 눈금으로: 0.10 m/s → 1, 0.5 m/s → 64, 2.5 m/s → 127 | SCH-03 주 9, D4(취향 곡선은 음원 쪽) |
| note-off · 재무장 | p 0.50(자석 복귀 50 %) 아래로. 정식 `0x80`, 릴리즈 벨로시티는 p 0.80 → 0.50 속도, 하한 5 | SCH-03 주 9, D2 |
| 유령 거름(U6) | 앞끝 0.3 m/s 이상인 음이 note-on부터 250 ms 안에 재무장하면 의심. note-on부터 500 ms 안의 첫 다시 눌림이 손가락 점 속도 min(0.45 m/s, 앞 음 × 25 %) 미만이면 버림. 버린 시각은 콘솔에 남음(단계 0 시험 11 기록용) | W1 DESIGN 0.1, SCH-03 주 9 |
| 느린 통과 | 자석 0.01 m/s 미만이면 소리 없음 | SCH-03 주 9(선택) |
| 보정 | 켤 때 쉼 값, 쉼 값은 건반이 쉬는 동안 천천히(약 7초) 따라감. 바닥은 누를 때마다 가장 깊은 값으로 넓힘(설계의 2배 넘는 값은 무시). 자석 극이 반대면 그 건반만 반대로 셈 | D4 |
| E11 | 문턱의 ADC 코드가 1536 · 2560 · 3584에서 10 이내이면 비켜 놓음 | SCH-03 주 7 |
| ID | GP6~8 풀업, 10 µs 뒤 읽기, 닫힘 = 1: JP301 + 2×JP302 + 4×JP303. 모두 열림이면 O4. O1은 C12~C14 → A0 · A#0 · B0, O7은 C12 → C8, 0.15 V 아래면 끝 부속 없음 | SCH-03 주 6 · 8, SCH-04 주 5 |
| USB | MIDI 1포트(채널 1) + 콘솔(CDC). 제품 이름 `Toccata O1`~`O7`, 일련번호 `O4-<칩 고유 번호>`, VID:PID `1209:0001`(pid.codes 시험용) | D3 |
| 복제 보드 | `PICO_XOSC_STARTUP_DELAY_MULTIPLIER=64` | SCH-03 주 8 |

모든 문턱과 비율은 [`src/keys.h`](src/keys.h) 맨 위에 모여 있습니다.

## 4. 직접 빌드

라즈베리파이에서:

```bash
sudo apt-get install cmake gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib build-essential git
```

```bash
git clone --depth 1 --branch 2.1.1 https://github.com/raspberrypi/pico-sdk.git ~/pico-sdk
git -C ~/pico-sdk submodule update --init --depth 1 lib/tinyusb
```

```bash
PICO_SDK_PATH=~/pico-sdk cmake -S firmware -B firmware/build && make -C firmware/build -j4
```

결과는 `firmware/build/toccata_octave.uf2`입니다. 첫 빌드 때 SDK가 picotool을 GitHub에서 받아 함께 빌드합니다. Mac에서는 Arm GNU Toolchain 14.2, CMake 3.31.6으로 빌드를 확인했고, 라즈베리파이 빌드는 아직 해 보지 않았습니다.

### 키 판정 시험 (보드 없이)

```bash
make -C firmware/test
```

`src/keys.c`를 컴퓨터에서 돌려, 자석 모델로 만든 센서 값(노이즈 ±3코드, 110 µs마다 읽기)을 넣고 나오는 음을 확인합니다. 지금 결과는 `199 checks, 0 failed`입니다.
- 설계 ADC 표: 재무장 백 2373 · 흑 2282, 1 N 바닥 백 2890 · 흑 2907과 일치
- 앞끝 0.15~2.5 m/s 속도 오차 1.5 % 이하, 2.5 m/s 타건을 스캔 위상 10가지로 쳐도 최악 0.7 %
- 바닥 폭이 설계의 0.55~1.6배인 센서도 첫 타건에 소리가 나고, 둘째 타건부터 정확함
- 유령 거름 6가지 경우, 극이 반대인 자석, 쉬는 동안 노이즈 ±5코드 10초와 쉼 값 드리프트 +24코드에서 헛음 없음
- E11 비켜 놓기(쉼 값 1800~2600 전부), 끝 부속 빠짐, 느린 통과

로직을 일부러 망가뜨린 사본 9가지(유령 거름 끔, E11 끔, 선형 위치, 바닥 학습 끔, 보간 끔, 극 뒤집기 끔, 쉼 값 추적 끔, 느린 통과 끔, 비율 틀림)는 모두 이 시험에서 실패했습니다.

## 아직 없는 것

- 실제 보드에서의 확인(위).
- 페달 기판: JP504가 닫힌 보드는 이름만 `Toccata PED`로 뜨고 아무것도 보내지 않습니다.
- 보정값 저장: 학습한 바닥 값은 전원을 끄면 사라지고, 켤 때마다 건반별 첫 타건이 다시 가르칩니다.
- CC88 고해상도 벨로시티(D5, 선택).

## 파일

| 파일 | 내용 |
|---|---|
| `src/keys.c` · `keys.h` | 건반 하나의 판정: 위치, 벨로시티, 재무장, 유령 거름, 보정(pico-sdk 없이 컴퓨터에서도 돎) |
| `src/scan.c` · `scan.h` | 코어 1: 먹스 · ADC 스캔, 켤 때 쉼 값 |
| `src/main.c` | 코어 0: ID 점퍼, USB MIDI, 콘솔 |
| `src/usb_descriptors.c` · `tusb_config.h` | USB 장치 설명(MIDI + CDC) |
| `test/` | 키 판정 시험 |
| `dist/toccata_octave.uf2` | 빌드한 펌웨어 |
