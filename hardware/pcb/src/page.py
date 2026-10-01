"""Builds the '회로도' tab (HTML fragment) for the merged Toccata v4 artifact.

usage: python3 page.py  -> hardware/pcb/page/circuit.html (+ circuit.css, circuit.js)
Sheets must be built first (build.py) so the CSVs exist.
"""
import csv
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sheets as S  # noqa: E402

ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "page")
E = html.escape

SHEETS = [
    ("sch/SCH-01_system.svg", "SCH-01 · 시스템 연결도", "모든 파트·보드와 그 사이 선(W 번호), 선 목록. 파트 사이는 모두 꽂았다 빼는 커넥터(R26). 개정 C: 화면 A605와 W605~W608(△16)."),
    ("sch/SCH-02_sensor_board.svg", "SCH-02 · 옥타브 센서 기판 (SB ×7)", "DRV5055A2 ×12(U201~U212, 핀 1 VCC · 2 GND · 3 OUT), 센서마다 100 nF, 버스 양 끝 10 µF, 리본 16심 2×8 블록 J201. 표: 센서 x(= W1 자석 x)·먹스 채널·리본 선 번호, W1 자석–소자 간격과 자기장·출력·ADC 범위."),
    ("sch/SCH-03_control_board.svg", "SCH-03 · 옥타브 제어 기판 (MB ×7)", "RP2040-Zero(A301)가 4067 모듈(A302)의 SIG를 GP26(ADC0)로 읽고 GP2~GP5로 채널을 고른다. GP6~GP8 ID 점퍼, GP14 PED 점퍼, EXT 보호 R301~R308, 테스트 포인트. 표: ID 점퍼·핀 배정."),
    ("sch/SCH-04_end_parts.svg", "SCH-04 · 끝 부속 센서 기판 (EL · ER) + EXT 연결", "A0·A#0·B0는 O1, C8은 O7의 EXT로. 기판은 W1 끝 부속 센서 바 안(EL x1.0~46.5, ER x1.0~23.0), 1 kΩ은 아랫면 1206(△13). JST-XH 6P 위치 1 = GND(검정 끝선) … 6 = 3V3(빨강 끝선)."),
    ("sch/SCH-05_pedal.svg", "SCH-05 · 페달 보드 (PB) + 댐퍼 페달 센서 (PS)", "페달 안 DRV5055 → 1 kΩ → 3 m TRS → PJ-313(TN = GND) → 1 kΩ + 100 nF → GP26. 링 급전 20 Ω, 팁 100 kΩ 풀다운, GP14 = GND → 'Toccata PED'."),
    ("sch/SCH-06_power.svg", "SCH-06 · 전원 (CU)", "HUSB238 20 V → 5 A 지연 퓨즈 → 로커 스위치 → +20V(앰프) · XL4016 → +5V1(Pi 5 USB-C 리드, 허브 DC). 별 접지점 = 강압 IN−. 표: 전원 예산. 개정 C(△16): 화면 A605 = Pi 40핀 헤더 2·6번 → 점퍼 F/F·M/M → 동봉선 2.54 3핀 → MX1.25 2핀(넷 +5V_PI), DSI 리본 W605, 예산에 화면 포함."),
    ("sch/SCH-07_audio.svg", "SCH-07 · 오디오 (CU)", "동글 → 볼 헤드폰 잭 J701(노멀 TN·RN) → J702 → 1 µF×2 병렬 + 1 kΩ(AGND) → XH-A232 → XT30 → CW-100B25 ×2(BTL)."),
    ("sch/BRD-01_control_board_placement.svg", "BRD-01 · 제어 기판 배치 (위에서 봄, 모듈 좌표)", "5×7 cm 기판 위 RP2040-Zero·4067 모듈·리본 2×8·EXT·보호 저항·점퍼·테스트 포인트의 구멍 좌표. W1 r4.3 홈(x81.92~84.72 × y145.5~172, F|F# 핀 발)과 금지 구역(주황, x81.22~85.42 × y≤173.2). 제로 x75.14(USB-C 가운데 = 선반 홈 가운데 x84.00, △15). 기판은 W1 r4.5 바닥 구멍(점선)으로 밑에서 넣고 매단 보스 4곳에 고정(△14)."),
    ("sch/BRD-02_sensor_board_placement.svg", "BRD-02 · 센서 기판 배치 (SB · EL · ER, 위에서 봄)", "161.6 × 15.24 SB(오른쪽 턱 기둥과 0.4): 센서 12개 리드 구멍 열, 3V3·GND·OUT 행, 100 nF·10 µF 자리, 리본 2×8 블록, 고정 구멍. 아래: 끝 부속 EL(45.5)·ER(22.0) 기판 — 센서·아랫면 1206 부품·리드 패드·필요한 리브 틈."),
]

CHANGES = [
    ("1", "SCH-02", "버스 양 끝 C213·C214 10 µF", "글 사양에는 있으나 구매 목록에 없었음", "구매: 1206 10 µF 16 V 50개(아이씨뱅큐 P001248090, 7,150원)"),
    ("2", "SCH-03", "먹스 VCC–GND C301 100 nF", "모듈 C1이 사진으로만 보여 미확인", "100 nF 여분"),
    ("3", "SCH-04", "EL·ER 기판 10 µF", "3V3가 150 + 350 mm 선 끝", "△1과 같은 묶음"),
    ("4", "SCH-05", "링 급전 R503 20 Ω (100 Ω ×5 병렬)", "TS 플러그·꽂는 순간 3V3–GND 단락 → PED 보드 리셋 (검토 R1, 필수)", "100 Ω 여분"),
    ("5", "SCH-06", "별 접지점 = 강압 IN− 단자", "동글–Pi–강압–앰프 GND 루프 험 (R7)", "—"),
    ("6", "SCH-03·04", "EXT·XH 순서 1 GND · 2~5 EXT1~4 · 6 3V3", "밸런스선 빨강 1 + 검정 5 → 빨강 = 3V3", "—"),
    ("7", "SCH-05", "페달 센서 OUT 뒤 R551 1 kΩ", "3 m 케이블 용량이 OUT에 직결 (TI: OUT에 C 직결 금지)", "1 kΩ 여분"),
    ("8", "SCH-03·04", "EXT: 센서 옆 1 kΩ 직렬(EL R401~R403, ER R411) + MB 100 kΩ 풀다운(R301~R304, O1 1~3·O7 1만)", "끝 부속을 빼면 입력이 떠서 유령 음 (R4, 필수). 1 kΩ은 약 0.6 m 선 용량을 센서 OUT에서 뗌", "1 kΩ·100 kΩ 여분"),
    ("9", "SCH-05", "페달 잭 TN → GND", "플러그 없으면 팁 = 0 V", "—"),
    ("10", "SCH-07", "AGND: 잭 슬리브·1 kΩ는 앰프 IN G로만", "험 방지 배선 규칙", "—"),
    ("11", "SCH-05", "R502 100 kΩ 팁→GND 고정, GP27 안 씀", "이전 글 사양의 'GP27로 뗀 쪽 전압 구동'은 GPIO가 0/3.3 V만 내서 불가 (R3)", "—"),
    ("12", "SCH-02·03", "리본 16심 모두 (15 GND, 16 3V3), 2×8 블록", "끊긴 선 유령 음·전원 여유 (R27), IDC 헤더와 번호 같음", "—"),
    ("—", "BRD-01", "RP2040-Zero를 안쪽 구멍 핀 헤더(몰드 뺌)로, 약 +1.3 mm", "밑면에 칩·수정·LDO가 있어 평평하게 안 붙음. W1 r4.3이 뒤 선반에 플러그 홈을 내 플러그와 1.3 mm", "구매: 핀헤더 1×40 ×4 (144핀)"),
    ("—", "BRD-01", f"모든 구멍을 제로 핀 격자(x{S.LAT_X:.2f}+2.54i, y173.59+2.54j)로, 4067 모듈 {S.MBX['mux'].split(' ×')[0]} 세로", "만능기판 한 장의 구멍에 모두 맞게 · W1 r4.3 홈·금지 구역", "—"),
    ("13", "SCH-04·BRD-02", "EL·ER R401~R403·R411 1 kΩ을 1206 칩(아랫면)으로, 기판을 W1 끝 부속 센서 바 안(EL 45.5, ER 22.0)으로", "센서 바가 기판 윗면을 모두 덮어 리드형 저항 자리가 없음. W1 r4.2 끝 부속 센서 바 x0.5~46.5 / x0.5~23.0", "구매: 1206 1 kΩ 10개(아이씨뱅큐 P011433924, 440원)"),
    ("14", "BRD-01", "기판 고정 자리 (50.0,149.0)(114.5,149.0)(50.0,192.5)(114.5,192.5) — W1 r4.5 매단 보스, M3×6 밑에서 2 · 위치 핀 2", "v3 P114 자리는 M3 머리가 밸런스 레일과 0.75, 선반 리브와 1.05 (W1 1.3 규칙 위반)", "M3×6 = 구매 목록 L35"),
    ("15", "BRD-01", "제로를 x75.14로(+0.14), J301 아랫면 납땜", "Waveshare 치수도: USB-C가 오른쪽에서 4.67(가운데보다 0.14 왼쪽) → 플러그를 W1 선반 홈 가운데 x84.00에(양옆 1.30). 리본은 차선 안 중심 x70.48 그대로", "—"),
    ("—", "전체", "테스트 포인트 8곳", "검토 R30", "—"),
    ("16", "SCH-01·06", "화면 A605 = " + S.DISP["model"] + "(B1): Pi 헤더 핀 2(5 V)·6(GND) → P603 → W606 F/F 20 cm → X601⇄X602 → W607 M/M 20 cm → X603⇄X604(동봉선 2.54 3핀: 1 빨강 · 2 빈 칸 · 3 검정) → W608 → P604 MX1.25 ⇄ A605. 넷 +5V_PI(Pi 안 5 V 레일, P601 MT666 ← +5V1)·GND. DSI = W605 FFC 22핀 300 mm B형. 예산: 화면 "
     + f"{S.budget()['disp_w']:.2f} W, 평균 약 {S.budget()['avg'][0]:.0f}~{S.budget()['avg'][1]:.0f} W, 순간 약 {S.budget()['peak']:.1f} W, 60 W 여유 약 {S.budget()['margin']:.1f} W, 45 W면 −2 dB",
     "R31(10/1 B1 선택). D16: 화면은 Pi에서 나가는 방향으로만. D19 여유. D14: 화면·경첩·다리에 자석 없음", "구매 목록 v4touch No.135 · No.49·50 · No.51~54 (반영됨)"),
]

W1_REQ = [
    ("1", f"제어 기판 부품 자리를 격자 좌표로: 제로 {S.MBX['zero']}, 4067 {S.MBX['mux']}, J301 {S.MBX['rib']}(아랫면 납땜, 리본 기판 밑 z5~9), J302 {S.MBX['ext']}", "반영. 리셉터클 x79.53~88.47 그대로"),
    ("2", "USB 플러그 면 y약 196.8(리셉터클이 제로 밖으로 1.0~1.5), 몰드 y196.8~221.8", "반영. 선반 홈 x76.45~91.55 틈 1.30, 뒷벽 개구 z5~21 틈 2.70"),
    ("3", "제어 기판 고정 4곳 (50.0,149.0)(114.5,149.0)(114.5,192.5)(50.0,192.5)", "바뀜: 한 덩어리 프레임에 기판을 넣을 길이 없어 기판 밑 바닥을 뚫고(x46.25~118.25 × y144.5~196.5, 리셉터클 뒤 y197.8) 밑에서 넣음. 받침 = 위에 매단 Ø6 보스(밑면 z10.6), M3×6 ×2 밑에서(ISO 7380 머리 Ø5.7 × 1.65: 레일 1.65, 리브 1.45, 기판 모서리 밖 0.10), 위치 핀 ×2(놀음 0.10), 넣는 길 틈 0.60"),
    ("4", "끝 부속 센서 기판 받침·뒤 리브 틈(EL x15~38, ER x6~16)·리드 길", "반영: 레일 밑 차선 EL x13.53~22.48 · ER x7.59~14.00 (z5~10), 뒷벽 홈 z5~12, 리드는 y77.39 안에서 EL x14.83~21.18 · ER x8.89~12.70으로 모음"),
    ("5", "SB 뒤 받침 리브 틈 x60~82 → x59~82", "반영 (리본 양옆 1.32 / 1.36)"),
    ("6", "금지 구역과 제로 PCB 겹침 정리", "금지 구역 y173.2 그대로, 제로 PCB가 y172.0~173.2에 걸친다고 P23에 기록"),
    ("7", "C301 = 1206 칩, 레버가 떨어지는 곳", "반영: D#·G# 매단 보스, E·F 4067 위(13.25°), F#·G 기판 윗면, O1·O7의 G R301 위(0.40 N)"),
    ("+", "F|F# 핀 발", "r4.5: 바닥 대신 킬(y144.5~148.6, z3~19.3)로 밸런스 레일 뒷면에 붙음, 핀 앞끝 y152 → y148.6 — 둘 다 기판 홈 안이라 회로 변화 없음"),
    ("8", "(2차) 센서 바 오른쪽 턱(v3 P112)을 모델에 넣거나, 턱 없이 바 오른쪽 끝을 무엇이 잡는지 P36에 적기", "반영(r4.5 회로 2차): 두 조각 ㄱ자 턱, 립 x161.5~163.0 z13.6~15.1, 기둥 x163.0~164.3. 회로: SB를 x162.6까지(기둥과 0.4). EL·ER은 턱 없이 왼쪽 M3 ×2 + 리브"),
    ("9", "(2차) 유령 거름 글을 gfilter와 같게(창 = note-on부터 재무장까지 250 ms), 유령이 다시 닿는 시각을 구해 '다시 눌림 시각 상한' 정하기", "반영: note-on부터 250 ms 안 재무장 → 의심, note-on부터 500 ms 안의 첫 다시 눌림만 판정. 재무장 28건을 1.5 s까지 돌려 스스로 다시 닿는 것 0건(흔들림 ≤ 222 ms) — 500 ms는 약 2배, 시험 11에서 확인"),
    ("10", "(2차) DESIGN §11 6단계: D#·G# 레버는 매단 보스 위(16.75°)", "반영: D#·G# 매단 보스 16.75°, F#·G 기판 윗면 24.00 / 23.50°, E·F 4067 13.25°"),
    ("11", "(2차) EL 바닥에 새어 든 기판 구멍 자르기 틈 x46.25~46.8 × y144.5~196.5 없애기", "반영: EL 바닥 한 조각(x0.2~46.8)"),
    ("12", "(2차) 구매 목록 글: L35 용도(매단 보스·밑에서), SE4에 MB C301 ×7(97개 사용), L20·L21 = 건반 88 + 페달 1, 엑셀 제목 r4.5", "반영: L35 매단 보스·밑에서, SE4 97개 사용·예비 3, L20·L21 89개·예비 11, 제목 r4.5 (합계 1,060,470원 그대로)"),
    ("13", "(2차) 단계 0 시험 21 뒤 리본 차선이 바뀌면 알리기", "바뀐 것 없음 — 시험 21 결과가 나오면 W1이 알림"),
]

BUY_FIX = [
    ("L67 (반영)", "1206 10 µF 16 V 50개 (아이씨뱅큐 P001248090, 7,150원) ×1 — SB C213·C214 ×7 + EL C404 + ER C412 = 16개", "△1·△3"),
    ("L68 (반영)", "Yageo RC1206JR-071KL 1206 1 kΩ 10개 (아이씨뱅큐 P011433924, 44원 × 10 = 440원, VAT 포함) — EL R401~R403 + ER R411 = 4개", "△13"),
    ("SE7 핀헤더 1×40", "5 → 9줄 (먹스 7 × (16+8) = 168핀 + 제로 8 × 18 = 144핀)", "제로를 핀 헤더로"),
    ("SE7 핀헤더 소켓 1×40", "빼기 (EXT는 L66 JST-XH를 패드에 직접 납땜, 암 헤더 안 씀)", "J302·J401·J411 = 패드만"),
    ("SEV2 RP2040-Zero 용도", "'캐스털레이션 직접 납땜' → '안쪽 구멍 핀 헤더 1×9 ×2(몰드 뺌), 캡톤 위 약 +1.3 mm'", "BRD-01 주 3"),
    ("L29 1 kΩ·100 kΩ·100 Ω 용도", "1 kΩ: R701·R702·R501·R551 / 100 kΩ: R301(O1·O7)·R302·R303·R502 / 100 Ω: R503 20 Ω = 100 Ω ×5 병렬(필수)", "bom.csv"),
    ("C05 리본 용도", "리본 16심 전부(OUT 12 + 3V3 ×2 + GND ×2) ×7 + EL·ER 리드 가닥", "△12"),
    ("L66 용도", "200 mm 연장선을 모듈 쪽 150 · 끝 부속 쪽 50으로 자름 (가운데 자르면 100이라 모자람)", "W403·W413 150 mm"),
    ("C04 USB 케이블 (반영)", "몰드 ≤ 12.5 × 7.6 × 25 — 폭이 넘으면 안 들어감(선반 홈과 한쪽 1.30). 지금 NA993은 두께 미공개 → 단계 0 시험 19로 확인, 대안 CVILUX DH-20M50052(11.97 × 6.42 × 20.93)", "W1 r4.5 1d-3"),
    ("L56 1 µF 용도", "'약 80 Hz' → '약 93 Hz' (1 kΩ + 앰프 입력 9 kΩ)", "SCH-07"),
    ("(선택) L29 10 kΩ", "회로에서 쓰지 않음(예비로 둘지 선택)", "bom.csv"),
    ("L01 Raspberry Pi 5 용도 (10/1 새로 고칠 글)", "'(R25: HAT 없음, GPIO 배선 없음)' → 'HAT 없음. GPIO는 헤더 2·6번에서 화면 5 V만 나감(R31)'", "△16"),
]

CHECKS = [
    ("PD 트리거", "무부하로 전원마다 20 V. 20 V 3 A(60 W) 보조배터리는 HUSB238이 3.25 A를 요구해 15·12·5 V로 떨어질 수 있다."),
    ("XL4016", "무부하 5.10~5.15 V에 맞추고 가변저항 고정 뒤 연결. MT666 빨강 = +, 허브 선 중심 = + 확인."),
    ("PJ-313 ×3", "플러그 없음: T–TN, R–RN 닫힘이어야 한다. 노멀 없는 제품이면 헤드폰 차단(R15)이 안 된다."),
    ("RP2040-Zero", "복제품: LDO 표시(5핀 RT9013·ME6217) 확인, O1 3V3 전류 60~130 mA, 부팅 불안하면 XOSC 지연 64."),
    ("센서", "자석 없이 1.59~1.71 V, S극을 표시면에 가까이 하면 오름. 건반을 얹은 쉼 백 ≈1.78 · 흑 ≈1.72 V, 바닥 백 ≈2.31 · 흑 ≈2.39 V(±10 %). EXT를 빼면 0.15 V 아래."),
    ("페달", "꽂은 상태 링–슬리브 3.05 V 이상, 뺀 상태 팁 약 0 V."),
    ("앰프·스피커", "36 dB 이득 확인 → 소프트웨어 음량 상한. 스피커 Re 6~7 Ω(4 Ω 판매분 주의)."),
    ("허브", "Pi 선을 뺐을 때 Pi 5V 핀 0 V(역급전 없음)."),
    ("화면 (△16)", "동봉선 2.54 3핀 하우징 = 1 빨강 5 V · 2 빈 칸 · 3 검정 GND인지 통전 검사 뒤 점퍼 연결. 화면 쪽 5 V를 부하 때 잼(점퍼 왕복 강하 계산 약 "
     + f"{S.budget()['drop_v']:.2f} V). 최대 부하에서 vcgencmd get_throttled = 0x0(Pi 입력 약 {S.budget()['pi_in_a']:.1f} A). 화면 켬·끔, 밝기 0·100 %에서 센서 유휴 흔들림 다시 잼(D14). config.txt: " + S.DISP["overlay"] + "."),
]


def read_csv(name):
    with open(os.path.join(ROOT, "netlist", name), encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def table(header, rows, mono=()):
    h = "".join(f"<th>{E(c)}</th>" for c in header)
    b = ""
    for r in rows:
        b += "<tr>" + "".join(f'<td class="num">{E(str(c))}</td>' if i in mono else f"<td>{E(str(c))}</td>" for i, c in enumerate(r)) + "</tr>"
    return f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def build():
    os.makedirs(OUT, exist_ok=True)
    bom = read_csv("bom.csv")
    net = read_csv("netlist.csv")
    pads = read_csv("rp2040_zero_pads.csv")
    muxp = read_csv("mux_module_pins.csv")
    nets = {(r[0], r[2]) for r in net[1:]}
    parts_total = len(bom) - 1
    p = []
    p.append('<section class="page" id="p-circuit" hidden>')
    p.append('<h2>전자부 회로도</h2>')
    p.append('<p class="lede">W1(v4 W1+ r4.5) 건반 액션의 전자부 회로도입니다. W1은 센서 바·센서 기판·제어 기판·리본·USB를 이전 설계에서 그대로 가져와 글과 블록도로만 적어 두었는데, 이것을 W1 좌표·자석 위치·기판 외곽에 맞춰 CAD에 그대로 옮길 수 있는 회로도로 만들었습니다. '
             '부품 번호·핀 번호·넷 이름·값·연결을 모두 적었고, 보드 두 장은 실제 구멍 좌표로 부품 자리를 잡았습니다. '
             '기준은 W1 r4.5 좌표 모델(geometry.json 2026-09-29, circuit_r43·circuit_r44 블록)과 DESIGN.md입니다. 모듈 핀 배치는 판매 페이지·데이터시트·위키로 확인했고, 전기 설계 검토에서 나온 필수 수정 3건을 반영했습니다(△ 표시).</p>')
    p.append('<h3><span class="no">00</span>W1에서 전자부로 들어오는 값</h3>')
    p.append(table(["항목", "W1 값 (r4.3~r4.5)", "회로에 반영한 곳"], [
        ["자석", "Ø5×2 N35, 건반 밑 y67 (센서 소자 열 바로 위), S극 아래", "SCH-02 표, BRD-02"],
        ["자석 x (센서 x)", "C 7.431 · C# 21.215 · D 35.25 · D# 49.285 · E 63.07 · F 77.359 · F# 90.573 · G 104.037 · G# 117.5 · A 130.964 · A# 144.427 · B 157.641; 끝 부속 A0 10.287 · A#0 26.927 · B0 40.141 · C8 11.75(오른쪽 로컬)", "SCH-02·04, BRD-02"],
        ["자석–소자 간격 쉼/강체 바닥/과다", "백 10.82 / 5.60 / 5.24 mm, 흑 13.35 / 5.32 / 4.76 mm; 1 N 정착 바닥 백 5.52 · 흑 5.47(흑은 강체 바닥보다 0.15 위)", "SCH-02 표"],
        ["센서 출력 (DRV5055A2, 3.3 V)", "백 약 4 → 22 mT (ADC 약 2207 → 2862), 흑 약 2 → 25 mT (2138 → 2962); 최대 31 mT < 선형 ±44 mT. 재무장(자석 복귀 50 %) 백 ADC ≈2373 · 흑 ≈2282, 1 N 바닥 백 ≈2890 · 흑 ≈2907", "SCH-02 표 · A2 형 유지"],
        ["펌웨어 규칙", "재무장 = 자석 복귀 50 %. 유령 거름(U6, W1 r4.5 DESIGN 0.1 = gfilter): 같은 건반, 앞끝 0.3 m/s 이상 음의 note-on부터 250 ms 안에 재무장하면 의심 → note-on부터 500 ms 안의 첫 다시 눌림이 min(0.45 m/s, 앞 음 × 25 %)보다 느리면 버림, 500 ms 뒤는 보통 음. 자석 단위: 앞끝 = 자석 × 1.91(백)/1.18(흑), 비율 27.5 / 28.2 %", "SCH-03 주 9"],
        ["제어 기판 외곽", "x47.25~117.25 × y145.5~195.5, 홈 x81.92~84.72 × y≤172 (F|F# 핀 발 y148.6~170.7 + 킬 y144.5~148.6, r4.5), 금지 x81.22~85.42 × y≤173.2 (제로 PCB만 y172~173.2에 걸침)", "BRD-01"],
        ["기판 고정 (r4.4~r4.5)", "바닥 구멍 x46.25~118.25 × y144.5~196.5로 기판을 밑에서 넣음. 매단 Ø6 보스 4개(받침 6 × 7.5 / 6 × 7.3, 밑면 z10.6, 둘레 1.3 부품 없음), M3×6 ×2 밑에서(L35 ISO 7380 Ø5.7 × 1.65), 위치 핀 ×2. J301·J302는 넣기 전에 납땜", "BRD-01 주 8 (△14)"],
        ["USB 플러그 · 선반 홈", "홈 x76.45~91.55, 플러그 폭 12.5 → 양옆 1.30. Waveshare 치수도(USB-C가 오른쪽에서 4.67)로 제로를 x75.14에 → 리셉터클 x79.53~88.47 가운데 x84.00", "BRD-01 주 1·3 (△15)"],
        ["끝 부속 센서 바 (r4.2) · 리드 길 (r4.4)", "왼쪽 x0.5~46.5 (A#0 낮은 구간 x19.93~33.93), 오른쪽 로컬 x0.5~23.0. 레일 밑 차선 EL x13.53~22.48 · ER x7.59~14.00, 뒷벽 홈 z5~12", "SCH-04 주 6, BRD-02 EL·ER (△13)"],
        ["프레임 레일·리브", "밸런스 레일 뒷면 y144.5, 선반 리브 앞면 y196.8(x49.4~50.6, x115.4~116.6), 기판 부품 ↔ 프레임 1.3", "BRD-01 고정 자리 (△14)"],
        ["높이", "부품 ≤ z20 (y145.8~194.5), 뒤 띠 ≤ z16.7, 제로 PCB z11.9~12.9·부품 ≤ z16.3; 기판 밑은 바닥 구멍(r4.5)", "BRD-01 주 3"],
        ["리본·EXT 경로", "리본 차선 x59~82 (높이 5.0), 리본 중심 x70.48(J201 = 차선 여유 1.32 / 1.36). J301도 아랫면 납땜, 기판 밑으로. EXT 선: 기판 밑 → USB 플러그 밑 → 뒷벽 개구", "SCH-02·03, BRD-01 주 6·7"],
    ]))
    p.append('<div class="kfs">'
             '<div class="kf"><b>9장</b><span>회로도 7 + 배치도 2 (A3)</span></div>'
             '<div class="kf"><b>6종 보드</b><span>SB ×7 · MB ×7 · EL · ER · PB · PS + CU 배선</span></div>'
             f'<div class="kf"><b>{parts_total}줄</b><span>부품표 (KiCad 심볼·풋프린트 포함)</span></div>'
             f'<div class="kf"><b>{len(nets)}개</b><span>넷 (도면마다 다시 계산)</span></div>'
             '<div class="kf"><b>0 / 0</b><span>연결 검사 오류 / 글자끼리 겹침 (자동)</span></div>'
             '<div class="kf"><b>3줄</b><span>구매 목록에 반영됨: L67 10 µF 50개 7,150원 · L68 1206 1 kΩ 10개 440원 · 핀헤더 1×40 5 → 9줄</span></div>'
             '</div>')
    p.append('<div class="note">저장 위치: 저장소 <span class="mono">hardware/pcb/</span> — <span class="mono">schematic/</span>(SCH-01~07 SVG), '
             '<span class="mono">board/</span>(BRD-01·02), <span class="mono">netlist/</span>(CSV), <span class="mono">src/</span>(생성기), '
             '<span class="mono">README.md</span>(규칙·KiCad 옮기는 순서). 도면은 한 소스에서 만들고, 그린 선·라벨로 연결을 다시 계산해 '
             '의도한 넷리스트와 대조했습니다.</div>')
    # toc
    p.append('<h3><span class="no">01</span>도면</h3><ol class="dtoc">')
    for i, (src, title, cap) in enumerate(SHEETS):
        p.append(f'<li><a href="#sch{i+1}">{E(title)}</a></li>')
    p.append('</ol>')
    p.append('<p class="small muted">"&gt;&gt;" 표시는 맞물린 커넥터(플러그–잭)입니다. KiCad에서는 연결이 아니므로 양쪽 핀에 같은 넷 이름을 붙여 두었습니다. '
             '도면을 누르면 크게 볼 수 있고, "2배·3배"로 페이지 안에서 확대해 옆으로 넘겨 볼 수 있습니다. '
             '색: 초록 선 = 배선, 갈색 테두리 = 부품, 파란 상자 = 산 모듈, 점선 갈색 = 케이블, 노란 △ = 이전 글 사양 대비 변경.</p>')
    for i, (src, title, cap) in enumerate(SHEETS):
        p.append(f'<figure class="sheet csheet" id="sch{i+1}"><div class="cap"><span><b>{E(title)}</b></span>'
                 f'<span class="zbar" role="group" aria-label="확대"><button type="button" data-z="1" aria-pressed="true">맞춤</button>'
                 f'<button type="button" data-z="2">2배</button><button type="button" data-z="3">3배</button>'
                 f'<a class="mono" href="{src}" target="_blank" rel="noopener">크게 보기 ↗</a></span></div>'
                 f'<div class="dwimg"><img src="{src}" alt="{E(title)}" loading="lazy"></div>'
                 f'<figcaption class="small muted">{E(cap)}</figcaption></figure>')
    # changes
    p.append('<h3><span class="no">02</span>이전 글 사양 대비 바꾼 점 (도면의 △)</h3>')
    p.append(table(["△", "도면", "변경", "이유", "부품"], CHANGES, mono=(0,)))
    p.append('<div class="note"><b>W1 기구와 맞춘 것.</b> RP2040-Zero는 밑면에 칩·수정·LDO가 있어 핀 헤더로 세웠고(약 +1.3 mm), W1 r4.3이 뒤 선반에 USB 플러그 위 홈을 내어 플러그와 선반 사이 1.3 mm를 되찾았습니다. 제어 기판 배치(BRD-01)도 r4.3 형상 검사에 들어가 기판 부품 ↔ 프레임 최소 1.3 mm입니다.</div>')
    p.append('<h3><span class="no">02b</span>W1 기구 쪽에 요청한 것과 반영 결과 (W1 r4.4~r4.5)</h3>')
    p.append(table(["#", "회로가 요청한 것", "W1 결과"], W1_REQ, mono=(0,)))
    p.append('<h3><span class="no">02c</span>구매 목록에 넣거나 고칠 줄</h3><p class="small muted">2026-09-29 구매 목록(엑셀·07 탭 선택기)에 모두 반영됐습니다(새 줄 L67·L68). 기록으로 남깁니다.</p>')
    p.append(table(["줄", "바꿀 내용", "근거"], BUY_FIX))
    # checks
    p.append('<h3><span class="no">03</span>부품이 오면 먼저 확인할 것</h3>')
    p.append(table(["항목", "확인"], CHECKS))
    # KiCad guide
    p.append('<h3><span class="no">04</span>KiCad로 옮기는 순서</h3><ol class="flow">'
             '<li><b>프로젝트를 보드별로</b>: octave-sensor(SB), octave-control(MB, PB 겸용 가능), end-parts, pedal-sensor, 문서용 cu-wiring. 한 PCB에 7장을 넣지 않는다.</li>'
             '<li><b>라이브러리</b>: 아래 부품표의 KiCad 심볼·풋프린트 열. 직접 만들 것 = 4067 모듈 심볼·풋프린트, PJ-313 풋프린트(패드 이름 T/TN/R/RN/S), 모듈 심볼(HUSB238·XL4016·XH-A232·동글·RaspberryPi5 헤더 유닛·Waveshare 7-DSI-TOUCH-C), 전원 심볼 +20V·+5V1·+5V_PI.</li>'
             '<li><b>RP2040-Zero</b>는 dj505/RP2040-Zero-KiCAD 라이브러리(패드 번호 = 이 도면), 3V3 핀을 power_out으로. DRV5055는 Sensor_Magnetic:DRV5055A2xLPGxQ1, Value를 DRV5055A2QLPG로.</li>'
             '<li><b>번호 매기기</b>: Annotate → First free after sheet number × 100, X 위치순 — 이 도면과 같은 번호가 나온다.</li>'
             '<li><b>ERC</b>: 선으로 들어오는 전원(SB의 +3V3, +3V3_EL·+3V3_ER, +20V, +5V1, +5V_PI, PS의 PED_VCC, 각 GND)에 PWR_FLAG. GND·+3V3는 로컬 라벨이 아니라 전원 심볼로. +3V3_EL·+3V3_ER도 프로젝트 전원 심볼로 추가.</li>'
             f'<li><b>외곽·자리</b>: BRD-01·02 좌표. 제어 기판은 x{S.MB["keep"][0]:.2f}~{S.MB["keep"][1]:.2f} × y{S.MB["keep"][2]}~{S.MB["keep"][3]}(W1 r4.3) 비움, 홈 x{S.MB["slot"][0]:.2f}~{S.MB["slot"][1]:.2f} × y{S.MB["slot"][2]}~{S.MB["slot"][3]} 따냄. EL·ER 기판은 BRD-02 아래 그림.</li></ol>')
    # BOM
    p.append('<h3><span class="no">05</span>부품표 (KiCad 심볼·풋프린트, 구매 목록 코드)</h3>')
    p.append('<p class="small muted">"전체 수량" = 보드 수 × 보드당, MB의 보호 저항은 실장하는 보드만 셈. 구매 목록 코드는 v4 재료 목록(xlsx)의 부품 코드입니다. '
             '부품 사진·가격은 <a href="#cost">재료·절감 선택</a> 탭에 있습니다.</p>')
    by = {}
    for r in bom[1:]:
        by.setdefault(r[0], []).append(r)
    names = {"SCH-02": "센서 기판 SB", "SCH-03": "제어 기판 MB", "SCH-04": "끝 부속 EL·ER", "SCH-05": "페달 PB·PS",
             "SCH-06": "전원 CU", "SCH-07": "오디오 CU"}
    for code, rows in by.items():
        p.append(f'<details class="spec cbom"><summary>{E(code)} · {E(names.get(code, ""))} — {len(rows)}줄</summary>')
        p.append(table(["보드", "부품", "값", "설명", "보드 수", "보드당", "전체", "실장", "KiCad 심볼", "KiCad 풋프린트", "코드"],
                       [[r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11]] for r in rows], mono=(1, 4, 5, 6)))
        p.append('</details>')
    # cables & pads
    p.append('<h3><span class="no">06</span>선 목록</h3>')
    p.append(table(["W", "종류", "길이", "한쪽", "다른 쪽", "심선", "코드"], [list(c) for c in S.CABLES], mono=(0,)))
    p.append('<h3><span class="no">07</span>모듈 핀 번호</h3>')
    p.append('<div class="cols"><div>')
    p.append('<p class="small muted">RP2040-Zero: 패드 = dj505 KiCad 라이브러리 번호, WS P1 = Waveshare 회로도 번호. 구멍 좌표는 모듈 왼쪽 위(USB 가장자리) 기준 mm.</p>')
    p.append(table(pads[0], pads[1:], mono=(0, 1, 4, 5)))
    p.append('</div><div>')
    p.append('<p class="small muted">4067 모듈(SparkFun BOB-09056 복제, 40.64 × 17.78, 두 줄 간격 15.24): 심볼 핀 ↔ 모듈 헤더. J2 1번(네모 패드) = GND.</p>')
    p.append(table(muxp[0], muxp[1:], mono=(0, 3)))
    p.append('</div></div>')
    # downloads
    p.append('<h3><span class="no">08</span>파일 위치 (저장소)</h3>'
             '<div class="tbl"><table><thead><tr><th>파일</th><th>내용</th></tr></thead><tbody>'
             '<tr><td class="num">hardware/pcb/schematic/SCH-01~07_*.svg</td><td>회로도 7장 (A3, mm)</td></tr>'
             '<tr><td class="num">hardware/pcb/board/BRD-01·02_*.svg</td><td>기판 배치도 2장</td></tr>'
             '<tr><td class="num">hardware/pcb/netlist/netlist.csv</td><td>도면·보드·넷·부품·핀 (그린 도면에서 다시 계산)</td></tr>'
             '<tr><td class="num">hardware/pcb/netlist/bom.csv</td><td>부품표 (KiCad 심볼·풋프린트·구매 목록 코드)</td></tr>'
             '<tr><td class="num">hardware/pcb/netlist/cables.csv</td><td>선 목록 W101~W706</td></tr>'
             '<tr><td class="num">hardware/pcb/netlist/wiring_MB.csv</td><td>제어 기판 점 대 점 배선 (구멍 좌표)</td></tr>'
             '<tr><td class="num">hardware/pcb/netlist/rp2040_zero_pads.csv · mux_module_pins.csv</td><td>모듈 핀 번호표</td></tr>'
             '<tr><td class="num">hardware/pcb/README.md</td><td>규칙, 변경 목록, KiCad 옮기는 순서, 도착 후 확인</td></tr>'
             '<tr><td class="num">hardware/pcb/src/</td><td>생성기 (build.py → 도면·CSV, page.py → 이 탭)</td></tr>'
             '</tbody></table></div>')
    p.append('<p class="small muted">근거: TI DRV5055 SBAS640C, TI CD74HC4067, RP2040 데이터시트(E11), Waveshare RP2040-Zero 위키·회로도, SparkFun BOB-09056, Hynetek HUSB238, TI TPA3110D2, AMASS XT30, KiCad 9/10 라이브러리. '
             '조사 노트 원문은 저장소 hardware/pcb/research/.</p>')
    p.append('</section>')
    frag = "\n".join(p)
    css = """
.csheet .cap{align-items:center}
.zbar{display:inline-flex;gap:4px;align-items:center;flex-wrap:wrap}
.zbar button{font:inherit;font-size:12px;border:1px solid #C9D0DA;background:#fff;color:#1A2030;border-radius:6px;padding:2px 8px;cursor:pointer}
.zbar button[aria-pressed="true"]{background:#1A2030;color:#fff;border-color:#1A2030}
.zbar a{margin-left:6px}
.csheet .dwimg img{min-width:720px}
.csheet.z2 .dwimg img{width:auto;min-width:0;max-width:none;width:2000px}
.csheet.z3 .dwimg img{width:auto;min-width:0;max-width:none;width:3000px}
details.cbom{margin:6px 0;border:1px solid var(--rule);border-radius:10px;background:var(--card);padding:6px 10px}
details.cbom summary{font-size:14px;color:var(--ink);font-weight:600}
details.cbom summary::before{content:"＋ "}
details.cbom[open] summary::before{content:"－ "}
details.cbom .tbl{margin:8px 0 4px}
details.cbom table{font-size:12px}
#p-circuit .tbl table td{font-size:12.5px}
.sheet,[id^="sch"],h3{scroll-margin-top:calc(var(--navh,50px) + 12px)}
"""
    js = """
(function(){
  document.addEventListener('click',function(e){
    var b=e.target.closest('.zbar button'); if(!b) return;
    var f=b.closest('.csheet'); var z=b.dataset.z;
    f.classList.remove('z2','z3'); if(z!=='1') f.classList.add('z'+z);
    f.querySelectorAll('.zbar button').forEach(function(x){x.setAttribute('aria-pressed', x===b?'true':'false');});
  });
})();
"""
    for name, text in (("circuit.html", frag), ("circuit.css", css), ("circuit.js", js)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(text)
    print("page:", len(frag), "chars")


if __name__ == "__main__":
    build()
