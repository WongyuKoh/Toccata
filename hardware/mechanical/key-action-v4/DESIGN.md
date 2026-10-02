# Toccata v4 건반 액션 W1+ — 상세 설계 r4.5 회로 2차 대조 (r4 + 검증 1회차 + 도면 형상 지적 + 제어 기판 인터페이스 + 남은 문제 고침 + 비틀림 스프링 기성품 + 스프링 가둠·킬 고침 + 회로 2차 대조, 단일 모델)

2026-09-29 (r4.5 회로 2차 대조; r4.5 고침 2026-09-28) · 모든 수치는 `model_v4.py`를 돌리는 `run_all.py`가 만든 `metrics.json`·`geometry.json`·`parts_list.json`에서 `make_design_md.py`가 옮겼다. r3 값은 `final_r3/metrics.json`에서 읽었다. 치수 번호(P·K·S·D·A)는 `geometry.json`의 `dims`와 같다. 단위 mm·g·N·ms. z = 0 책상, y = 0 백건 립 앞끝(+y 뒤쪽), x = 0 모듈 C 왼쪽 명목 경계. 대표 건반은 백건 D, 흑건 C#. ‘연구’가 붙은 숫자는 r4 단순화 연구(업스톱·건반 유지·감사) 보고의 값이고, ‘검증자’가 붙은 숫자는 r3 검증 보고의 값이다.

사용자 요청은 "뺄 수 있는 부품은 다 빼고 더 작게"였다. r4는 r3 검증에서 나온 문제 18건(major 8, minor 10)을 모두 고치면서, 업스톱 레일·손나사 8개·접시 스프링 72장·탭 강철 띠 4개·위치 핀·커버 자석·흑건 납·경화 샤프트·황동 부싱·C-링·L 블록·패드 홀더 17개·스프링 자리판·강철 모따기·드라이버·빼기 고리를 모두 없앴다. 모듈 한 개의 부품 수는 249개에서 120개로, 무게는 2.03 kg에서 1.37 kg으로, 맨 위 높이는 z78.0(손나사 머리 z80.7)에서 z72.85로, 기본 구성 비용 변화는 +130,400원에서 +69,400원으로 줄었다.

**r4.1**: r4 검증 1회차(물리 major 2 · minor 4, 기하 major 2 · minor 6)를 반영했다. 부품은 늘리지 않았다. 바뀐 것은 펌웨어 거름 문턱(1.2 → 0.3 m/s), F|F# 핀이 만능기판 앞 홈을 지나 바닥에 닿게 한 것(6건반 화음 자리 196 → 492 N/mm), 조립 순서(레버 먼저), 흑건 뒤끝 윗면 낮춤, 패드 바 레일 앞으로 연장·립·예하중 잎, 캐리어 윗 립 끊음, 칼라 0.05 짧게, 스프링 홈 보스다. 판정과 숫자는 1a장, 형상 변경 목록은 1b장.

**r4.2**: 도면을 그리던 사람이 찾은 형상 문제 7건(검증자가 못 본 것)을 이 모델로 다시 재서 고쳤다(1c장). 부품은 늘리지 않았다. 패드 바 계단을 윗판 홈 끝보다 1.0 앞으로(r4.1은 윗판과 1.5×1.5 겹침), 윗판 계단과 바 뒤끝을 y185.0로(쐐기·패드 ↔ 계단 1.62 / 1.62), 레일을 L 레일(립 1.3×0.8, 바 밑 1.0 겹침) + 바 가장자리 출력 잎 혀로, 손톱 턱을 R3 모서리에 붙임, 허브 스프링 주머니에 코일·다리 홈(짧은 다리는 홈 면에 얹힘), 뒷벽 스프링 홈을 보스 밑까지, 끝 부속의 자기 쐐기·센서 바·스프링 홈을 geometry에 넣음. 윗판 계단이 1.5 뒤로 가서 가장 무른 패드 자리가 1559 → 1492 N/mm(동역학 자리 1550 → 1490)로 약간 물러졌고, 모든 동역학을 다시 돌렸다.

**r4.3**: 회로 세션이 r4.1 형상으로 제어 기판(BRD-01)을 설계하고 기구에 닿는 결과 3건을 알려 왔다(1d장). 부품은 늘리지 않았고 한 모듈의 프레임만 바꿨다(끝 부속에는 기판·USB가 없어 그대로). RP2040-Zero가 핀 헤더 위에 서서 USB-C 플러그가 z10.7~18.3로 1.3 올라가, r4.2의 얇은 선반(밑면 z18.55)과 0.25만 남았다 → 뒤 선반에 플러그 위 홈 x76.45~91.55를 앞뒤로 뚫고(플러그 ↔ 선반 1.30) F|F# 핀을 뒷벽까지 z21.5에 매달았다. 핀 발을 y170.7에서 끝내 제로 앞 모서리와 1.30, 금지 구역 ±1.2, 부품 구역을 BRD-01 배치(4067 y193까지 z20)대로, 16심 리본 차선을 x59~82로. 대가: F·F# 쉼 펠트가 홈 옆에 59 % / 42 %만 앉는다 — 쉼 펠트 접촉을 42 %로 낮춰 다시 돌린 동역학에서 연타 16.2 / 18.8 Hz, 끝까지 복귀 45.4 / 39.9 ms로 모든 목표 통과.

**r4.4**: 사용자 요청 "남은 문제 부분을 고쳐줄래"에 따라 r4.3의 남은 형상 문제 3건을 고쳤다(1e장). 부품은 늘리지 않았고 제어 기판 인터페이스(회로 세션 소유)는 그대로다. (1) 레버 윗 스냅 립의 앞 구간 뒤끝이 1 N 바닥·ff에서 패드 옆 0.64(공차 뒤 0.34)까지 들어가던 것을, 앞 립을 y163까지 줄이고(패드와 2.16) 뒤 립을 y184~190로 늘려(캡스턴이 강철 뒤끝을 밀어 올리는 힘을 받는 립, 뿌리 응력 13.1 → 3.8 MPa) 고쳤고, 립·핀 보스 구멍·레버 봉·봉 마개를 geometry.json과 스윕에 넣었다(레버 질량 모델이 립을 두 번 세던 것을 고치니 ff가 0.02° 커져 칸 가장자리 레버 ↔ 레일 웹이 1.30이 되어, 레일 웹 앞 아래 모서리를 1.0 모따기). (2) F·F# 쉼 펠트 착지(59 / 42 %)로 F·F# 자기 복귀 넘침 자세를 구해 스윕하니 4쌍이 1.3 미만(최소 1.14: 홈 위로 나온 F 펠트 ↔ USB 플러그, F# 건반 ↔ 자기 레버)이라, 두 펠트를 홈 가장자리에서 자르고 F#는 흑 꼬리 끝까지 넓혀(59 / 55 % 착지) 0쌍; 6건반 화음 자리(492 N/mm) 동역학의 모든 PLAY 목표 통과 — 출력 부품은 바뀌지 않았다. (3) 건반 누른 자세 내보내기를 두 색 모두 1 N 정착 바닥(패드 있음)으로 바꾸고 강체 바닥은 `side_dip_rigid`로 따로 두었다(스윕은 둘 다 검사). 모듈 스윕 최소 1.31(공차 뒤 1.01).

**r4.4 회로 대조**: 회로 세션이 r4.3 모델을 회로도와 맞춰 보고 보낸 기구 요청 7건(`hardware/pcb/README.md` 끝)을 이 모델로 하나씩 재서 모두 넣었다(1d-2장). BRD-01 부품을 제로 핀 격자(x = 76.52 + 2.54i)로, J301은 아랫면 납땜이라 16심 리본이 기판 밑 z5~9로, USB-C 플러그 면을 y196.8로(몰드 y196.8~221.8), 프레임에 제어 기판 받침 4개(나사 받침 2 + 출력 위치 핀 2, M3×6 머리 ↔ 레일 1.65 · 리브 1.54), 센서 기판 받침(v3 P111·P113)을 모델에 넣고 뒤 리브 틈을 x59~82로(리본 양옆 1.32 / 1.36), 끝 부속 EL·ER에 기판 받침·뒤 리브 틈·리드 차선(레일 밑 z5~10)·뒷벽 홈(z5~12). 산 부품은 모듈당 제어 기판 나사 M3×6 2개(v3.2 구매 목록 L35에 이미 있어 비용 0). 모든 틈 규칙을 지키고(모듈 스윕 1444쌍, 끝 부속 527 / 310쌍, 1.3 미만 0), 동역학·강도에 닿는 부품은 바뀌지 않았다.

**r4.4 남은 문제 4~7**(`report_r4/open_issues.r4_3.json` 번호): (4) USB-C 케이블: C 쪽 몰드 세 치수가 공개 실측으로 확인되고 동결 한계 안에 드는 선은 CVILUX DH-20M50052 하나다(11.97 × 6.42 × 20.93, 1d-3장). (5) RP2040-Zero 높이 한계는 그대로다(회로 쪽 조립 규칙, 18장). (6) 문서: 모든 표와 치수의 반올림을 한 규칙으로 맞췄다(5장 머리). 13·15장을 부품표와 맞췄다. 출력 공구 4개를 실제 치수로 넣었다(10.1장). (7) 시험 가정: 단계 0 시험 키트로 출력 시편 34종 36개와 절차, 합격 숫자, 결과마다 바꿀 모델 값을 모았다(17.1장). 이 문서 작업으로 바뀐 모델 수치는 없다.

**r4.4 고침 2**: r4.4 검증(물리 2, 기하 2, 출력물 4 major)을 반영했다(1e장 끝 ‘고침 2’). (1) **강철 블록을 캐리어에 에폭시로 접착한다** — 새 옆벽 판 모델로 재니 스냅 립만으로는 매 음(PLAY 1.5 m/s, 캐리어 → 강철 51.9 N)에 립 선이 한쪽 1.11~1.70 벌어지고(물림 1.0) 옆벽 립 뿌리가 층 안 23.5 MPa(한계 12)라 버티지 못한다; 접착 전단은 매 음 0.067 MPa. 산 것은 2액형 에폭시 한 통(소모품, 약 6,000원)뿐이고 출력·구매 부품은 늘지 않았다. (2) 스윕에 레버 축 놀음·패드 바 옆 놀음·건반 노치가 봉에 앉고 파고드는 만큼을 넣었다: 패드 구간 옆벽 윗단을 강철 윗면보다 2.6 낮춤, 레버-레버 칼라 한 개 0.76 이상, 핀 보스 +0.02, 밸런스 레일 블록 밑 포켓(백 z18.90, y137.4 뒤 / 흑 z18.80, y137.2 뒤), F·F# 꼬리 밑면 0.2 올림 — 모듈 스윕 최소 1.31(공차 뒤 1.01). (3) 핀 게이지 순서(누른 핀마다 바로 확인, 망치 금지)와 T3 뒤 발, 단계 0 시험 20(C16a·b), 3a 굽힘 띠(경간 100), 치수 글(S08·D02·A08·D11)·부품표 공구 행을 고쳤다. 회로 인터페이스는 그대로다.

**r4.4 고침 2b**: 고침 2를 넣은 모델을 다시 검증한 지적(기하 critical 1 · major 1, 물리 major 2, 출력물 major 2)을 모두 이 모델로 다시 재서 받아들였다(1e장 끝 ‘고침 2b’). (1) **제어 기판을 넣을 길이 없었다**: 한 덩어리 프레임에서 F|F# 핀 발이 바닥~윗판을 기판의 앞이 열린 홈으로 지나고, 홈 뒤 기판 띠 위에 핀이 매달려 있어 기판이 위·앞·뒤 어디로도 못 들어간다. 기판 밑 바닥을 뚫고(x46.25~118.25 y144.5~196.5) 기판을 **밑에서** 곧게 올려 넣는다: 핀 발은 바닥 대신 **킬**(핀 판을 홈 안에서 밸런스 레일 뒷면까지 z3~19로 이음)로 붙고, 받침 4개는 기판 **위에 매단 보스**(앞 2 레일, 뒤 2 리브·선반)가 되며 M3×6은 밑에서 조인다 — 길 위 최소 0.60, 6건반 화음 자리 492 N/mm(고침 2 492). (2) 강철 접착을 **MS 폴리머(탄성)**로 바꾸고 옆벽을 0.7로(주머니 9.2, 접착층 한쪽 0.10): 5분 에폭시는 PETG·강철 열팽창 차이로 ΔT 15 K에 가장자리 전단 2.24 MPa라 떨어진다 → 매 음 하중 0.067 + 열 0.189 MPa(허용 0.375). (3) 스윕 자세에 **최악 재료(합격선 밖)의 PLAY 복귀 넘침·ff**를 넣고 E·G 꼬리 밑면 0.1, F는 y176부터 0.15 올림. (4) 캡스턴 벤치 게이지(T2)의 기준을 정착 쉼 꼭대기 z30.90로(z31.0은 캡스턴을 0.108 / 0.088 높게 맞췄음). (5) 12장 PET 심 방향을 바로잡음. 부품은 늘지 않았다(소모품 에폭시 → MS 폴리머). 회로 인터페이스의 고정값·기판 구멍·홈·부품 자리는 그대로이고, 기판을 고정하는 방법만 바뀌었다(BRD-01 주 8의 글은 회로 세션이 고칠 것).

**r4.5**: 사용자가 2026-09-28 다른 세션에서 비틀림 보조 스프링(D05)을 주문 제작하지 않고 **한국미스미 경제형 토션스프링 C-UA90R5-3-0.5**(SUS304-WPB, 안지름 5, 선경 0.5, 3권, 암 각 90° 오른쪽 감기, 암 50/50; 100개 이상 282원 + VAT)를 쓰기로 했다(1f장). 두 암을 잘라(긴 다리 22.3, 짧은 다리 2.5) k_t 8.866 N·mm/rad, 자유각 -27.07°로 b = 0 토크 4.19 N·mm를 그대로 두어 DW·UW는 같다(51.9 / 51.0 g). 카탈로그 스프링은 두 다리가 1170° 감겨 있어 짧은 다리가 긴 다리의 홈으로 나올 수 없으므로 허브 주머니 구간(x ±1.5)에 **짧은 다리 홈**을 새로 팠다(허브 벽을 뚫고 웹 밑면을 1.21 깎음). 주머니 Ø6.6, 코일 홈 폭 6.5, 뒷벽 홈 2.4 × 3.2(보스 4.4). 부품 수는 그대로, 공구는 경선 니퍼 하나가 늘었다. 비용 변화 +26,000원(스프링 100 × 310 = 31,000원). 회로 인터페이스는 그대로다. *(r4.5 고침에서 짧은 다리는 8.0 mm로 바뀌었다. 두 다리는 22.3 / 8.0 mm로 자른다 — 1f-2장.)*

**r4.5 고침**: r4.4 고침 2b와 r4.5 스프링을 다시 검증한 지적(스프링 major 1 · minor 2, 고침 minor 3)을 이 모델로 다시 재서 모두 받아들였다(1f-2장). 부품은 늘지 않았다. (1) **코일이 봉 위에서 뜬다**: 짧은 다리 2.5가 홈의 한 면에만 기대면 다리 힘이 코일(ID 5.0)을 Ø4 봉 쪽으로 0.47 밀어 다리가 면에서 떨어지고 스프링이 13.4° 풀려 쉼 토크 4.19 → 2.18 N·mm — 백 립 DW 42.2 g · 흑 DW 46.0 g(< 47), 흑 바닥 UW 마찰 2배 18.9 g(< 20)로 PLAY 목표 3개 불합격. 짧은 다리를 8.0 mm로 길게 잘라 폭 0.70 **가둠 홈**(허브 벽을 지나 웹 안 막힌 끝)에 넣어, 다리 끝과 주머니 가장자리 두 점(팔 5.75)이 짝 힘(쉼 0.73 N)으로 토크를 받게 했다: 코일은 제 다리에 매달려 봉과 0.43 떨어지고(손 25°에서 0.33), 쉼 토크 4.19 N·mm, 봉 마찰 없음. 스프링은 짧은 다리 끝부터 홈을 따라 넣는다(넣는 슬롯 317°, 긴 다리 창 35°). 뒷벽 홈·보스를 긴 다리 x(+0.8)에 맞춰 건반 뺀 레버의 다리가 코일·레버 놀음을 더해도 홈에 걸린다(여유 0.61). (2) **킬 뿌리의 레일이 단단한 땅이 아니다**: 레일 + 바닥 띠를 핀 선 사이 보로 넣으니 r4.4 킬로는 화음 자리 447.5 N/mm(< 460) → F|F# 핀 앞끝을 y152 → **y148.6**로 당기고 킬(z3~19.3, 건반 F 블록과 1.34)을 4.1로 짧게 해 491.6 N/mm; 첫 모듈 정하중 확인(6 × 60 N, E·F ≤ 0.13 mm)을 단계 0에 넣음. (3) 글 고침: T2 기준 z30.90, 접착은 10장 4단계, 고침 2b 레버 질량, 설계 492, 얇은 쐐기의 되돌림, D#~G# 레버 떨어짐을 실제 착지로. 도면 작성자 메모(도구 T2·T24·T09 프리즘, 뒷벽 홈 잘라낸 부품·입구 모따기, 떨어짐 자세의 스프링 다리)도 내보냄에 넣었다.

**r4.5 회로 2차 대조**: 회로 세션이 r4.5 저장소 사본을 회로도(개정 B)와 다시 맞춰 보고 보낸 ‘2차 요청’(`hardware/pcb/README.md`) 가운데 8~11을 이 모델로 재서 고쳤다(1d-2장 끝 표). 12(구매 목록 글)·13(리본 차선을 바꾸면 알림)은 다른 곳에서 한다. 부품은 늘지 않았고 회로 인터페이스(리본 차선 x59~82 z5~10, 센서·제어 기판, 플러그)는 그대로다. (8) **센서 바 오른쪽 턱(v3 P112)이 r4 내보냄에서 빠져 있었다** — 바 오른쪽 끝을 잡는 것이 없었다(모듈을 뒤집어 기판을 넣을 때 바·기판이 왼쪽 나사에만 매달림). 프레임에 되살림: 두 조각 y59.0~63.4 · y70.6~77.5, 립 x161.5~163.0 z13.6~15.1(밑면 = 바 윗면), 기둥 x163.0~164.3; 가장 가까운 움직이는 부품 1.95(건반 B 꼬리 오른 옆벽 ff 최대). (9) **유령 거름 글을 모델(gfilter)·SCH-03 주 9와 같게**: note-on부터 250 ms 안에 재무장하면 의심, 첫 다시 눌림이 note-on부터 500 ms 안이면 속도 비로 판정. 재무장하는 28건을 note-on 뒤 1.5 s까지 돌리니 스스로 다시 닿는 것 0건 — 0.45~0.50 N 손가락이 건반을 뜬 자리(자석 22~96 %)에 붙잡고(흔들림은 222 ms까지), 그 뒤는 모델 마찰 정칙화의 기어내림(자석 ≤ 0.0005 m/s)뿐. (10) 11장 6단계 등 착지 글을 실제 착지로(D#·G# 매단 보스 16.75°, F#·G 기판 윗면 24.00 / 23.50°, E·F 4067 13.25°). (11) 끝 부속 EL 바닥에 모듈 기판 구멍 자르기가 새어 생긴 틈 x46.25~46.8 × y144.5~196.5를 없앰.

## 0. 하중 기준, 목표, 결과

### 0.1 하중 기준과 근거

- **근거 1 — Askenfelt & Jansson (1991)**, *From touch to string vibrations II: The motion of the key and hammer*, J. Acoust. Soc. Am. 90(5):2383–2393. KTH 강의 요약(https://www.speech.kth.se/music/5_lectures/askenflt/motions.html)에서 확인: 메조포르테에서 건반 최대 속도 약 0.3~0.5 m/s, 포르테에서도 1 m/s를 거의 넘지 않음, 해머 속도는 건반 속도의 약 5배(포르테 해머 약 5 m/s).
- **근거 2 — Goebl, Bresin & Galembo (2005)**, *Touch and temporal behavior of grand piano actions*, J. Acoust. Soc. Am. 118(2):1154–1165 (https://iwk.mdw.ac.at/goebl/papers/Goebl-Bresin-Galembo_JASA2005_PianoAction.pdf 본문에서 확인): 2300여 음을 측정했고, 치는 터치(struck)의 최대 해머 속도는 거의 8 m/s(가장 센 타건: Steinway G6 7.5, Yamaha G6 7.8, Bösendorfer C4 7.6 m/s), 누르는 터치(pressed)는 5 m/s를 거의 넘지 않았다. 실제 연주에서 흔한 세기는 해머 0.7~1.25 m/s. 근거 1의 5배 비율로 나누면 가장 센 타건의 건반 속도는 7.8 / 5 ≈ 1.56 m/s이다.
- **PLAY 한계**: 건반 **앞끝** 속도 1.5 m/s(앞 펠트에 닿는 순간 = 행정 중 최대 속도). 한 건반, 굴린 화음과 동시 화음 6건반까지, 손가락을 떼거나 0.45~2 N으로 누른 채. 모든 기능 목표(DW·UW·연타·복귀·노치 들림·키퍼·유령·이음·센서·틈)를 지켜야 한다. 모델은 이 앞끝 속도가 되도록 타건 시작 속도를 풀었다(손가락 점에서 백 0.93, 흑 0.77 m/s). 여유 확인으로 손가락 점 1.5 m/s에서 시작하는 경우(앞끝 약 2.0 m/s)도 계산했다(‘여유 확인’ 행).
- **ABUSE 한계**: 한 건반 2.5 m/s, 6건반 동시 2.0 m/s(앞끝). 손상만 없으면 된다: 항복 없음, 10^4회 피로 한계 아래, 제자리 영구 이탈 없음(건반이 들렸다 다시 앉는 것은 됨), 조정 풀림 없음. 노치 들림은 빠짐 들림 0.80 mm의 절반(0.40)까지, 유령은 펌웨어가 걸러내면 된다.
- **PETG 응력 한계(r3 기준 유지)**: 층간(핀·벽처럼 세워 출력한 부분의 세로 인장) 매 음 5 MPa, 드문 하중(6건반 화음·ABUSE, 10^4회 이하) 15 MPa; 층 안(윗판 굽힘, 건반 빔·꼬리) 매 음 12 MPa, 드문 하중 25 MPa; 상시(쉼) 2 MPa.
- **펌웨어 유령 거름(U6, r4.1 고침; r4.5 회로 2차: 글을 모델 gfilter·SCH-03 주 9와 같게)**: 같은 건반에서 앞끝 0.3 m/s 이상인 **어떤 음**이든, 그 note-on(모델: 앞 펠트에 닿는 순간)부터 250 ms 안에 건반이 재무장선(자석 복귀 50 %)을 넘으면 의심 상태가 된다. 그 뒤 **note-on부터 500 ms 안에** 닿는 첫 다시 눌림의 내려오는 속도(손가락 점)가 앞 음 속도의 25 % 미만(최대 0.45 m/s)이면 버린다; 500 ms가 지나면 의심을 풀고 다음 눌림은 보통 음이다. 모델에서 재무장하는 28건은 note-on 뒤 1.5 s까지 돌려도 스스로 다시 닿는 것이 0건이다(7.4) — 500 ms는 흔들림이 멈추는 가장 늦은 222 ms의 약 2배이고, 단계 0 시험 11에서 펌웨어 기록의 유령 다시 눌림 시각으로 확인한다. r4.0의 문턱 1.2 m/s는 0.8~1.1 m/s 화음의 유령(내려옴 0.03~0.17 m/s)을 통과시켰다(검증자). 대가: 진짜 연타라도 건반이 250 ms 안에 재무장한 뒤 note-on부터 500 ms 안에 앞 음의 1/4보다 느리게 다시 치면 모든 세기에서 버려진다(예: 1.0 m/s 뒤 0.25 m/s 미만).

### 0.2 목표 대비 결과

| 구간 | 목표 (모델 안의 판정식) | 결과 (백 / 흑) | 판정 |
|---|---|---|---|
| PLAY | DW 47~55 g (y13, 흑 앞+10), 기본 마찰 (백 / 흑) | 51.9 / 51.0 (마찰 2배 56.5 / 56.1, 참고) | 통과 |
| PLAY | UW 20 g 이상 (쉼·바닥, 마찰 2배 바닥 포함) | 42.8 / 40.8 (바닥 마찰 2배 최소 21.3) | 통과 |
| PLAY | DW 립 y0 47 g 이상 (백) | 47.1 | 통과 |
| PLAY | 연타 13.3 Hz 이상 (1/(2·t50), 50 % 재무장, 1.2 s 정착 뒤 뗌) | 16.3 / 18.8 | 통과 |
| PLAY | 연타, 마찰 2배 (비틀림 보조 스프링 기본; 끝 건반 A0·C8 포함) | 15.2 / 17.7 (끝 건반 최소 15.0) | 통과 |
| PLAY | 끝까지 복귀 60 ms 미만 (마찰 2배, 끝 건반 포함) | 45.4 / 39.9 (마찰 2배 48.5, 끝 건반 최대 49.3) | 통과 |
| PLAY | 노치 들림 0.20 이하 (들림으로만 판정; 0.5~1.5 m/s, 뗌·0.45~2 N, 한 건반·6건반 화음 자리 1.0~1.5 m/s 0.05 간격, 끝 건반, 합격선 재료; 접촉 하한 0.02) | 0.162 (재료 조합 0.159, 화음 자리 0.135 / 합격선 0.149, 끝 건반 0.140); 모델 하한 v_floor 0.1 모서리: 한 건반 0.198, 화음 0.219 (18장); 합격선 밖 최악 0.204 / 화음 0.204 | 통과 |
| PLAY | 키퍼 무접촉 (합격선 재료, 화음 자리 포함) | 최소 틈 0.52 (조합 0.41, 화음 0.51; v_floor 0.1 화음 0.26; 합격선 밖 최악 0.34 / 화음 0.34) | 통과 |
| PLAY | 유령: 재무장선 50 %를 넘는 경우는 모두 펌웨어 거름이 버림 (한 건반·6건반 화음 자리 0.5~1.5 m/s 0.1 간격, 0.45~2 N, 끝 건반, 거름 문턱 0.3 m/s; r4.5 회로 2차: 창 = note-on부터 재무장 250 ms, 첫 다시 눌림은 note-on부터 500 ms 안, 재무장한 경우는 note-on 뒤 1500 ms까지 돌림) | 한 건반 1.5 m/s 최대 17 %; 350건 중 재무장 28건 모두 거름 (못 거른 것 0); 재무장 28건 중 1500 ms 안에 다시 닿는 것 0건, 모두 222 ms까지 멈춤(뜬 자리 22~96 %, 기어내림 ≤ 0.0005 m/s) | 통과 |
| PLAY | 업스톱 이음 닫힘 | 이음 없음: 패드 → 패드 바 → 윗판 압축 (나사·예하중 없음) | 통과 |
| PLAY | 센서 최소 간격 3.0 이상 (2.5 m/s 과다 누름) | 4.76 | 통과 |
| PLAY | 모든 틈 ±0.3 공차 뒤 1.0 이상 (모듈, 끝 부속, 이음매) | 1.01 (끝 부속 1.01 / 1.01, 이음매 너머 고정 부품 1.02 / 1.02; 이음 면 0.40 / 0.40 = 모듈 이음과 같은 0.4) | 통과 |
| PLAY | 쉼 상시 응력 2 MPa 미만 | 0.50 MPa | 통과 |
| PLAY | 매 음 층간 응력 5 MPa 미만 (핀-윗판 이음, 한 건반 1.5 m/s) | 1.3 MPa | 통과 |
| PLAY | 6건반 화음 층간 응력 15 MPa 미만 (드문 하중, r3 기준) | 4.2 MPa (윗판 층 안 5.5) | 통과 |
| PLAY | 숨은 빔·얇은 꼬리 매 음 12 MPa 미만 (층 안: 건반은 윗면이 베드) | 빔 11.5, 꼬리 9.7 MPa | 통과 |
| PLAY | 레버 봉 SUS304 Ø4: 6건반 화음 응력 < 항복/1.5 | 65 MPa (항복 205, 풀림재 최소값) | 통과 |
| ABUSE | 노치 들림 0.40 이하 (빠짐 0.80 / 안전율 2), 모든 재료 조합, 2.0 m/s 6건반 화음 자리 포함 | 0.177 (조합 최대 0.349, 화음 자리 0.203) | 통과 |
| ABUSE | 항복 없음: 레버 봉 (2.0 m/s 6건반, 2.5 m/s 한 건반) | 88 MPa < 205 | 통과 |
| ABUSE | 피로 10^4회: 층간 15 MPa, 층 안 25 MPa 미만 (2.0 m/s 6건반) | 핀 이음 5.7, 윗판 7.5 MPa | 통과 |
| ABUSE | 숨은 빔·얇은 꼬리 25 MPa 미만 (층 안, 2.5 m/s) | 빔 10.0, 꼬리 9.7 MPa | 통과 |
| ABUSE | 제자리 이탈·조정 풀림 없음 | 패드 바는 압축, 조정은 인쇄 쐐기·PET 심·캡스턴(벤치) | 통과 |
| BUILD | 레버를 건반보다 먼저: 모든 레버가 윗판 밑 제자리(레버 봉 선)에 들어감 (2D C-공간, 끝 부속 포함) | 11 / 11 도달 (건반을 먼저 넣으면 흑 레버 막힘) | 통과 |
| BUILD | 고정 부품끼리 겹침 없음 (따로 출력하는 부품, 모듈·끝 부속; r4.1: 패드 바 ↔ 윗판 2.5 mm²) | 모듈 0, 끝 부속 0 / 0; 패드 바를 넣고 빼는 내내 윗판·레일과 최소 -0.01 (접촉 −0.01) | 통과 |
| BUILD | 패드 쐐기·패드 ↔ 윗판 계단·레일 1.3 이상 (패드 바 뒤끝만 계단에 닿음) | 쐐기 1.43, 패드 1.43 (끝 부속 1.43) | 통과 |
| BUILD | 비틀림 스프링 조립: 코일이 허브 홈으로 들어가고, 긴 다리가 레버 전 범위에서 홈 안(면까지 0.2 이상), 뒷벽 홈에 아래로 들어감 | 레버 -31.3°~18.0°에서 여유 0.57; 다리는 보스 면에 z41.45(보스 밑 z47.0 아래)에서 닿고 홈(z47부터)으로 들어감 | 통과 |
| BUILD | r4.5 고침 2 짧은 다리 가둠 홈에 넣기: 스프링을 짧은 다리 끝부터 홈을 따라 밀어 넣음 (홈이 0.15 좁게 나와도 틈 ≥ 0; 더 좁으면 0.5 날로 다듬음) | 짧은 다리 ↔ 홈 면 0.100 (0.10 / 0.15 좁게: 0.050 / 0.025), 코일 ↔ 조각 A 0.22 · B 0.14, 긴 다리 ↔ A 4.34 · B 3.14 | 통과 |
| PLAY | r4.5 고침 2 코일 뜸(검증 major): 짧은 다리를 가둬 코일이 봉에 닿지 않음 — 쉼 토크 설계값, 봉 마찰 이력 0, 홈이 +0.3 넓게 나와도 봉과 틈 > 0 | 쉼 4.19 N·mm (r4.5 한 면 받침이면 코일이 봉으로 0.47 밀려 2.18), 봉과 틈 쉼 0.43 · 바닥 0.38 · 손 25° 0.33, 홈 +0.3이면 쉼 3.75 N·mm·틈 0.17; 짝 힘 0.73 N | 통과 |
| BUILD | r4.5 고침 2 건반 뺀 레버의 긴 다리: 뒷벽 홈·보스를 다리 x(+0.8)에 맞춤 — 코일 축 놀음 + 레버 놀음을 더해도 홈 입구(모따기 포함)가 다리를 받음 | 다리 x 어긋남 최대 0.84 (코일 0.44 + 레버 0.41) ≤ 받는 폭 1.45: 여유 0.61 (레버 중심 홈이면 -0.19) | 통과 |
| BUILD | r4.5 스프링 카탈로그 한계: 손 들기(레버 25°) 감김각 ≤ 최대 사용각 55° | 감김 53.4°, 토크 7.83 N·mm = 카탈로그 55° 토크 7.52의 104 % (18장 위험), 응력 685 MPa (Su 32 %) | 통과 |
| ABUSE | r4.5 고침 2 허브·웹 (가둠 홈 자리): 층 안 < 25 MPa (홈 모서리 Kt 2 포함), 매 음 PLAY < 12 MPa | ABUSE 7.96 MPa (홈 없던 단면 3.44), PLAY 4.93 MPa; 다리 두 닿는 점 1.36 N (손 25°), 봉 지압 1.45 MPa | 통과 |
| BUILD | 패드 바 빼기 (앞부분이 나온 21.5 mm부터 윗판에 밀어 올림): 공칭 1.3 이상, PET 심 3장 1.0 이상 | 공칭 1.30, 심 3장 1.11 (곧게만 당기면 끝 0.5 mm에서 -0.39) | 통과 |
| PLAY | r4.3 쉼 펠트가 USB 홈 옆에 55 %만 앉을 때 (F#, 두 색에 적용): 연타 13.3 Hz 이상(마찰 2배 포함), 복귀 60 ms 미만, 들림 0.20 이하, 키퍼 무접촉 | 연타 16.3 / 18.8 Hz (마찰 2배 최소 15.2), 복귀 45.4 / 39.9 ms (마찰 2배 최대 48.5), 들림 0.114 / 0.061, 키퍼 0.41 / 1.11 | 통과 |
| BUILD | r4.3 USB-C 플러그(RP2040-Zero 핀 헤더 위, z10.7~18.3) ↔ 뒤 선반·리브·핀·뒷벽 1.3 이상 | 최소 1.30 (rear shelf); 선반 홈 x76.45~91.55, 리브 2.15, 핀 3.20, 뒷벽 개구 2.70 | 통과 |
| BUILD | r4.3 제어 기판 부품(BRD-01)·부품 한계 ↔ 출력 프레임 1.3 이상, 리본(16심) 차선 양옆 1.3 이상 | 최소 1.30 (board components (<= z20) ↔ fin); 핀 발 ↔ 제로 앞 모서리 1.30; 리본 1.32 / 1.36 | 통과 |
| PLAY | r4.4 윗 스냅 립 ↔ 패드·패드 바·레일 1.3 이상 (립을 geometry·스윕에 넣음; r4.3 립 y150~168은 0.64) | 최소 1.81 (패드 2.16, 패드 바·레일 1.81); r4.3 립은 1 N 바닥에서 패드 옆 0.64 (공차 뒤 0.34) | 통과 |
| PLAY | r4.4 강철 블록 유지 (고침 2b: MS 폴리머 탄성 접착, 접착층 한쪽 0.10): 캐리어 → 강철 힘·모멘트의 전단 + 열팽창 차이 전단(매 음 ΔT 15 K, 드문 30 K, 가장 얇은 접착층 0.02) — 매 음 0.375, 드문 0.750 MPa 이하 (설계 1.5 MPa / 4·2); 스냅 립만으로는 안 됨(18장) | 전단(하중 + 열) 매 음 0.067 + 0.189, 화음 0.057 + 0.379, ABUSE 0.100 + 0.379 MPa (면적 1411 mm²; 5분 에폭시면 열만 2.24 MPa), 충격 2009 g까지; 접착 없이 스냅만: 아래 립 뿌리 층간 6.8 MPa(한계 5), 옆벽 립 뿌리 층 안 23.5 MPa(한계 12), 립 선이 1.11 벌어짐(물림 1.0) | 통과 |
| PLAY | r4.4 F·F# 쉼 펠트 착지(r4.4 펠트) 6건반 화음 자리: 들림 0.20 이하, 키퍼 무접촉, 유령 모두 거름, 연타 13.3 Hz 이상·복귀 60 ms 미만(마찰 2배) | F 59 %: 들림 0.130 키퍼 0.37 연타 15.3 Hz 복귀 48.3 ms; F# 55 %: 들림 0.074 키퍼 1.11 연타 17.7 Hz 복귀 42.3 ms | 통과 |
| ABUSE | r4.4 F·F# 착지 ABUSE (2.5 m/s 한 건반·화음 자리, 2.0 m/s 화음): 들림 0.40 이하, ABUSE 복귀 넘침 자세에서 닿지 않음 | 들림 최대 0.353; ABUSE 복귀 넘침 최소 틈 1.27 (공차 뒤 0.97) | 통과 |
| BUILD | r4.4 레버 봉·핀 보스 구멍·봉 마개를 geometry·스윕에 넣음 (마개는 끝 핀 면과 같은 면, 축 놀음 > 0) | 마개 x0.2~1.4, 막힌 끝 x163.1; 축 놀음 0.10~0.50; 가장 가까운 움직이는 부품 1.77 | 통과 |
| BUILD | r4.4 고침 2b 제어 기판 넣기: 한 덩어리 프레임에 기판이 들어갈 길 — 바닥 구멍으로 밑에서 곧게 올림(기판 홈이 F\|F# 핀 발·킬을 따라감), 길 위 고정 부품과 평면 틈 > 0, 걸리는 것은 매단 보스(자리)뿐 | 길 위 최소 0.60 (기판 ↔ fin); 바닥 구멍 x46.25~118.25 y144.5~196.5(리셉터클 뒤 x78.53~89.47는 y197.8까지); 멈춤 = 기판 위 매단 보스 4개(z10.6에 닿음), 위치 핀 반경 놀음 0.10; r4.4 고침 2까지는 길이 없었음(핀 발이 바닥~윗판, 기판 뒤 여유 1.3) | 통과 |
| PLAY | r4.4 고침 2b F\|F# 핀 발 킬(밸런스 레일 뒷면까지, 바닥 대신): 화음 자리 강성 460 N/mm 이상(단계 0 합격선), 킬 굽힘 층 안 매 음 12 / 드문 25 MPa, 전단 층간 기준 매 음 5 / 드문 15 MPa | 화음 자리 492 N/mm (r4.5 고침 2: 레일 + 바닥 띠를 핀 선 사이 보로; 킬 z19.3 + F\|F# 핀 앞끝 y148.6; 레일 고정이면 495, r4.4 킬 z18·앞끝 y152면 447, 첫 시도 킬 z21은 건반 F에 0.21); 킬 한 건반 PLAY 3.35 MPa (전단 1.60), 6건반 화음 PLAY 13.02 (6.25), ABUSE 화음 2.0 m/s 17.68 (8.48) MPa | 통과 |
| BUILD | r4.5 고침 2 첫 모듈 정하중 확인(단계 0): 6패드 × 60 N에서 E·F 패드 자리 처짐 ≤ 60 / 460 = 0.13 mm (모델) | 모델 E·F 최대 0.121 mm (D-D#-E-F-F#-G 화음), 가장 무른 자리 496 N/mm | 통과 |
| BUILD | r4.4 회로 대조: 스탠드오프 M3 머리(L35 Ø5.7)·핀 ↔ 레일·리브 1.3, 핀은 기판 안·나사 구멍 둘레 기판 1.0 이상; 리본(차선·기판 밑·SB 리브 틈) 양옆 1.3; 플러그 y196.8~221.8 ↔ 선반 홈·뒷벽 개구 1.3; 끝 부속 리드 패드·선 ↔ 리브 틈 1.3, 리드 길(모음 포함) ↔ 바닥 부품 1.3, 기판이 센서 바 안 | 머리 ↔ 레일 1.65, ↔ 리브 1.54 (축 위 1.45), 구멍 둘레 기판 1.15 (머리는 모서리 밖 0.10); 리본 1.32 / 1.36 (SB 리브 틈 1.32 / 1.36, 기판 밑 ↔ 핀 발 1.88); 플러그 홈 1.30, 뒷벽 개구 2.70; 리드 틈 최소 1.35, 리드 길 ↔ 바닥 부품 1.30 (A#0 탭 받침 1.75); 기판 부품 ↔ 프레임 1.30 | 통과 |
| PLAY | r4.4 고침 2: 스윕에 레버 축 놀음(칼라·보스 사슬, 한쪽)·패드 바 옆 놀음 ±0.3·건반 노치가 봉에 앉음/파고듦(쉼·1 N 바닥 평면 상태, ff·복귀 넘침 동역학 최저) — 모든 쌍 1.3 이상 | 레버 ↔ 레버 1.32, 레버 ↔ 핀 1.32, 레버 ↔ 패드 바·패드·쐐기 1.44, 옆벽 ↔ 자기 패드 1.44 (고침 1 옆벽이면 0.73), 흑 블록 ↔ 밸런스 레일 1.31 (포켓 백 z18.90 y137.4~; 흑 z18.80 y137.2~) | 통과 |
| 참고 | 유효 질량 m_eff | 55.2 / 46.5 g (r3 68.9 / 64.7) | 가벼운 레버 + 스프링 |
| 참고 | 앞/뒤 힘 비 DW(y90)/DW(y13) | 2.52 (y90 131.0 g) | 단계 0 느낌 판정 |
| 참고 | 마찰 2배 DW | 56.5 / 56.1 g | 55 g을 넘음 (r3도 55.9 / 55.8) — 18장 |
| 참고 | 1 N으로 누른 바닥 (레버가 패드에 먼저) | 건반 앞이 펠트 위 +0.04 / +0.27 mm | 2 N이면 펠트에 닿음 |
| 참고 | 모듈 맨 위 높이 (v3 z59, r3 커버 z78.0·머리 z80.7) | z72.85, 그 위에 아무것도 없음 | ≤ z74 목표 통과 |
| 참고 | 모듈 무게 (r3 2.03 kg) | 1.37 kg | ≤ 1.6 kg 목표 통과 |
| 참고 | 부품 수 / 모듈 (출력 + 구매) | 32 + 88 = 120 (r3 76 + 173 = 249) | |
| 참고 | 필라멘트·출력 시간 (88건반, 서포트 포함) | 6.55 kg · 436 h (r3 6.54 kg · 436 h) | 윗판 서포트 때문에 약간 늘어남 |
| 참고 | 금속 (88건반) | 5.10 kg (r3 9.52 kg) | |
| 참고 | 기본 구성 비용 변화 (한도 100만 원) | +69,400원 → 기본 652,619원 (r3 +130,400원) | 한도 안 |

## 1. r3의 문제 8건(major)과 10건(minor) — 무엇이었고 r4에서 어떻게 됐나

r3 검증(`context/r3_findings.json`)은 물리·동역학 렌즈에서 major 2건, 기하·조립 렌즈에서 major 6건을 냈다. 아래 ‘문제’ 칸은 r3가 실제로 틀렸던 점, ‘r4’ 칸은 지금 모델의 값이다.

| # | 문제 (r3) | r4 해결 |
|---|---|---|
| 1 | 업스톱 패드 높이(S15)를 건반이 아직 튀는 320 ms 시점에서 잡았다. 실제로 만들면 백 레버가 0.71 mm 먼저 패드에 닿아, 연타 13.1~13.2 Hz(마찰 2배 12.2~12.4, 목표 13.3 미달), 합격선 재료에서 백 노치 들림 0.237 mm와 키퍼 접촉, 흑 캡스턴·빔 하중 약 2배(검증자). | 1 N으로 1.4 s 누른 **진짜 정착** 상태(끝에서 레버 각속도 1e-6 rad/ms 미만)에서 패드 면을 잡는다(S15). 모든 동역학·조정·끝 부속이 이 기준이다. 연타 16.3 / 18.8 Hz, 마찰 2배 15.2 / 17.7 Hz. |
| 2 | 스냅 노치 판정식 ‘떼어내는 힘 < 최소 빠짐 힘 4 N’이 모델 자신의 입술 법칙과 맞지 않았다: 그 법칙으로 빠짐 힘은 약 2.0 N, 뒤집힌 채 약 8.7 g 충격이면 빠진다(검증자). | 판정을 **들림**으로만 바꿨다(RET-2): PLAY ≤ 0.20, ABUSE ≤ 0.40(빠짐 0.80의 절반). 결과: PLAY 한 건반 0.162 / 6건반 화음 0.149, ABUSE 한 건반 0.177 / 6건반 화음(2.0 m/s) 0.203. 빠짐 힘은 덜걱 방지로만 보고, 단계 0 반지름 쿠폰(R2.50~2.60)에서 1~2 N을 고른다. |
| 3 | 끝 부속 이음을 만들 수 없었다: 이음 쪽 핀 보스가 모듈 핀과 0.95 mm 겹치고, 오른쪽 핀이 도브테일 홈을 막고, 도브테일이 내보내지지 않았고, 끝 부속 스윕에 이웃 모듈이 없었다(검증자). | 이음 핀 보스를 안쪽으로만(왼쪽 x43.83~46.80, 오른쪽 x0.20~6.32), 이음 핀을 도브테일 홈 앞 1.3·위 1.7에서 멈춤, 앞 연장 0.1 얇게, 왼쪽은 수·오른쪽은 암 도브테일을 내보냄. 끝 부속 스윕에 이웃 모듈의 건반 3개·레버 3개·고정 부품을 넣었다: 최소 1.01 / 1.01(공차 뒤), 이음매 고정-고정 1.32 / 1.32. |
| 4 | 흑건 가이드 탭 7.5 + 천 0.5T 양쪽 = 8.5가 흑건 낮은 벽 사이 8.0에 들어가 한쪽 0.25 억지끼움(걸림); 천이 없으면 놀음 ±0.25(검증자). | 흑 탭을 6.9로 좁혀 천 양쪽 = 7.9, 벽 사이 8.0에서 ±0.05(RET-5). 흑-백 건반 틈 1.32. 천 두께는 3칸 맞춤 쿠폰으로 고름. |
| 5 | 선택 보조 스프링을 만들 수 없었다: 자리 Ø7이 6.0 틈에 안 들어가고, 컵이 5.9 mm 움직여 33° 기울고, P18과 D05가 달랐다(검증자). | 압축 스프링을 없애고 레버 봉 위 **비틀림 스프링**(A2)을 기본으로 달았다(r4.5: 미스미 기성품): SUS304-WPB d0.5, ID 5.0, 몸통 3.25권, 코일은 허브 주머니, 긴 다리는 뒷벽 홈, 짧은 다리는 허브 홈. 응력 최대 685 MPa(Su의 32 %). 이 스프링이 DW 51.9 g 중 11.2 g을 낸다. |
| 6 | 조정을 제자리에서 할 수 없었다: 캡스턴에 손이 닿지 않아 1/8회전마다 커버·손나사 8개·레일·건반을 빼고 24 h 뒤 다시 조여야 했다(검증자). | 업스톱 시점은 그 칸 패드 바를 앞으로 빼서 패드 밑 PET 심 0.1로(한 장 = 건반 앞 0.18 mm), DW는 강철 앞 윗면 퍼티로(1 g = +1.23 g), 캡스턴은 건반을 넣기 전 벤치 게이지에서, 높이는 벤치 지그의 펀칭으로. 나사·드라이버·다시 조이기 없음. |
| 7 | 계단 밸런스 블록의 입술 벽이 강철 밸런스 핀에서 0.19~0.26 mm뿐이고 스윕에서 빠져 있었다(검증자). | 핀을 1.2 mm 앞으로(y135.3), 홈 y134.0~138.0, 블록 앞 y134.0, 레일 앞 y132.3(RET-4): 핀 ↔ 입술 벽 1.39, 홈 뒤끝 1.63(모든 자세). |
| 8 | 치수표 D11에 패드 e ≤ 0.12(r2 값)가 남아 있었다. 합격선은 0.07이고, e 0.10~0.12 패드면 유령 97~99 %를 펌웨어가 못 거른다(검증자). | D11 = ‘패드 실효 e ≤ 0.07 (캡 모양 60 g 추 2.5 m/s 낙하, 설계 0.06), 25 % 압축 0.36 MPa, 패드 자리 강성 ≥ 830 N/mm(100 N에 0.12 mm), 6건반 화음 자리 ≥ 460 N/mm’(U7). r4.4: e를 재는 기준 방법은 17.1장의 C01 진자대(모델 `pad_e` 정의)다. |

minor 10건:

| 문제 (r3) | r4 |
|---|---|
| 유령 격자가 0.6 N부터였다; 0.45~0.55 N 가벼운 누름에서 70~99 %, ‘오름 < 60 %’ 거름은 못 잡음(검증자) | 0.45·0.5·0.55·0.6·0.8·1·2 N 모두 계산. 한 건반 PLAY 최대 17 %, 6건반 화음 자리에서는 재무장하지만 새 규칙(속도 비)이 모두 버림: 재무장 28건, 못 거른 것 0건 |
| 노치 들림·키퍼 판정이 접촉 감쇠의 시작 속도 하한(V0_FLOOR 0.02)에 달렸다(검증자) | 0.02와 0.1 둘 다 계산(7장 표). v_floor 0.1에서 PLAY 들림 0.189 / 0.121, 키퍼 0.41 / 1.09 |
| 손나사 예하중을 막는 것이 없었다(검증자) | 손나사·접시 스프링 자체가 없다. 패드 힘은 패드 → 패드 바 → 윗판으로 압축만 전달 |
| 마찰 2배에서 DW·바닥 UW가 목표 밖(검증자: DW 56.0 / 55.3, 흑 바닥 UW 16.9) | 바닥 UW(마찰 2배)는 스프링으로 25.0 / 21.3 g(≥ 20 통과). 마찰 2배 DW 56.5 / 56.1 g은 여전히 55 초과(18장) |
| 흰 앞 펠트 ↔ 크로스바·리브 0.876(검증자) | 펠트를 y1.5~9.0로 잘라 1.68(공차 뒤 1.38) |
| 가림판 ↔ 꼬리 윗판이 노치 들림을 빼고 1.31(검증자) | 가림판 밑 z45.5, 들림을 넣은 ff 자세로 1.63 |
| 예비 보관함 길이 여유 0(검증자) | 건반 칸 201.3(1.0 + 199.3 + 1.0) + 칸막이 1.2 + 옆 칸 136.3 |
| 건반 빼기가 도구 없이가 아니었다(드라이버·고리), 흑건은 양옆 백건을 먼저 빼야 하고, 접시 스프링이 따로 놀고, L 블록을 잊으면 레버가 떨어짐(검증자) | 도구 없음: 가림판·패드 바를 손으로 빼고, 레버는 손톱 턱으로(0.47 N), 건반은 손톱으로(2.7 N). 흑건은 양옆 백건 먼저(조립은 흑건 먼저). 나사·접시 스프링 없음. L 블록 없음: 건반이 빠진 레버는 바닥판(30.3~30.8°)이나 기판 쪽(4067·매단 보스·기판 윗면, 13.3~24.0°) 위에 0.40 N으로 놓인다 |
| 빼기 때 레버 각 창이 좁았다(0.9°)(검증자) | 패드 바를 빼면 레버가 윗판까지 15.5°까지 올라감; 빼기에 필요한 각 13.1° / 9.2° → 창 2.4° |
| 표·글 불일치: P10 오프셋 기준, 봉 멈춤 기둥 1.0×1.4, 커버 자석 튀어나옴, 높이 z78/80.7(검증자) | P10을 실제 꼬리 중심 기준 1.83로, 멈춤 기둥 1.0×2.0, 자석·커버판 없음, 맨 위 z72.85 |

## 1a. r4 검증 1회차 지적과 해결 (r4.0 → r4.1)

지적마다 먼저 이 모델로 다시 계산해 보았다. 받아들인 것과 고친 방식, 받아들이지 않은 부분을 숫자로 적는다. 다시 돌린 범위: 한 모듈(대표 백 D·흑 C#, 끝 건반 A0·C8), PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45~2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악, 6건반 화음 자리 1.0~1.5 m/s(0.05 간격)·유령 격자 0.5~1.5 m/s(0.1 간격). 옥타브 모듈은 모두 같아 되풀이하지 않았다.

| # | 지적 (검증자) | 다시 계산 (이 모델) | 판정 | r4.1 해결과 결과 |
|---|---|---|---|---|
| 물리 M1 | 유령 거름 문턱 1.2 m/s 때문에 0.8~1.1 m/s 6건반 화음의 0.45~0.6 N 누름 유령(재무장 50~101 %, 내려옴 0.03~0.17 m/s)이 걸러지지 않는다 | r4.0 화음 자리(196 N/mm) 1.0 m/s 0.45 N 백 101 %, 0.5 N 99 % 재현(검증자 표와 같음) | 수용 | 펌웨어만 고침: 문턱 1.2 → 0.3 m/s, 규칙 ‘250 ms 안, 앞 음 속도의 25 % 미만(최대 0.45)’. 새 화음 자리 492 N/mm에서 0.5~1.5 m/s × 0.45~2 N 격자 132경우: 재무장 13건, 모두 버림(한계와의 여유 최소 0.22 m/s). 전체 350경우 중 못 버린 것 0건. |
| 물리 M2 | 기판 위 D#~G# 6건반 화음에서 노치 들림이 1.2~1.4 m/s에 0.216~0.238 (1.5 m/s의 0.126은 국소 최소); 무르고 감쇠 없는 자리(196 N/mm)가 원인 | r4.0 자리 203 N/mm, 백 D 뗌: 1.3 m/s 0.226, 1.35 m/s 0.232, v_floor 0.1이면 1.5 m/s 0.266 (검증자 0.227 / 0.238 / 0.262와 같음) | 수용 | F\|F# 핀이 만능기판 앞쪽 홈(x81.92~84.72, y145.5~172.0, 부품 없음)을 지나 y152~171에서 바닥에 닿게 함 → 6건반 화음 자리 492 N/mm(가장 무른 화음은 이제 C~F), 한 건반 자리 최소 1490 N/mm. 1.0~1.5 m/s 0.05 간격 최대 들림: 공칭 0.135 / 0.062, 합격선 재료 0.149 / 0.081 (백 / 흑), 키퍼 최소 0.51. 대가: F\|F# 핀이 하중을 더 받아 핀 윗 이음 층간 응력이 6건반 PLAY 화음 4.2 MPa(r4.0 4.9), 2.0 m/s 화음 5.7 MPa(r4.0 6.7; 한계 15). 대안 ‘D#~G# 칸 틈 −0.6’은 기각: 공칭은 0.223, v_floor 0.1이면 0.282에 키퍼 −0.03(r4.1 탐색). |
| 물리 m1 | 합격선 재료 + v_floor 0.1 한 건반 들림 0.205(묶어서 안 돌림); 흑건은 들림 0.06에서도 입술 모서리가 1.5~3.5 N으로 닿으니 ‘입술이 일하지 않음’은 틀림 | r4.0 자리에서 0.205 재현; r4.1 자리에서 같은 조합 0.198 / 0.099; 흑 PLAY 입술 힘 2.54 N(최대 조합 5.26 N) | 수용 | 묶은 조합을 표에 넣음(7.2). ‘입술이 일하지 않음’ 문구를 모두 지우고 노치는 들림으로만 판정(S04). 단계 0 시험 10에 흑건 입술 천 마모(PLAY 10^5회, 천 닳아 뚫림 없음) 추가. 형상 변경 없음. |
| 물리 m2 | 모든 여유가 패드 실효 e ≤ 0.07에 달렸는데 그런 재료를 이름으로 대지 않았다 | r4.1 자리에서 e 0.15: 백 들림 0.177, 0.45 N 유령 98 %, 흑 ABUSE 0.398; e 0.25: 0.208 / 100 % / 0.400 | 수용 (일부 남음) | 후보를 이름과 자료값으로 적음: Sorbothane(점탄성 PU) 카탈로그 Lupke 반발 10~15 %(자유 낙하 e ≈ 0.32~0.39), 충격 에너지 흡수 최대 94.7 %(e ≈ 0.23) (https://www.sorbothane.com/technical-data/material-properties/). 곧 판 하나의 자유 반발로는 0.07에 못 미치므로 e는 레버 + 패드 + 펠트 면 + 자리 계에서 단계 0 시험 1로 먼저 잰다. 번호 붙인 대안(부품 추가 없음): ① e 0.10~0.15 → 틈 −0.60 / −0.65 + 폼 E 1.4: 들림 0.116 / 0.043, 흑 ABUSE 0.197, 연타 17.6 / 20.8 Hz. 18장 위험으로 남김. |
| 물리 m3 | 제자리 조정(10장 8번)에 잴 수 있는 합격 기준이 없다 | 종이 띠 0.05가 앞 펠트 위에서 물리기 시작하는 누름 힘(백 틈 −0.30 / −0.40 / −0.50): 0.75 / 0.92 / 1.05 N | 수용 | 12장 표에 넣음: 백은 0.05 종이 띠가 0.75 N에서 미끄러지고 1.05 N에서 물리면 합격, 흑은 0.96 / 1.43 N. |
| 물리 m4 | 패드 바가 레일 안에서 FDM 놀음만큼 처져, 매번 들려 올라가 딸깍 | 레일과 바가 x로 겹치지 않아 모델에 바를 받치는 것이 없었음(확인) | 수용 | 바 뒤 계단 양쪽에 출력 예하중 잎(0.6×4×8, 0.3 눌림 ≈ 0.25 N = 바 무게의 9배)이 바를 레일 립(도브테일 밑, 새로 내보냄)에 대고 윗판 쪽으로 밀어 올림; 단계 0 점검에 ‘바 상하 놀음 없음’. 부품 추가 없음. (r4.2: 잎과 립이 글로만 있었고 립이 0.2 두께·0.3 겹침이라 1c장에서 형상으로 다시 만듦) |
| 물리 m5 | 글·값 불일치: 거름 상한 0.45 / 0.40, 자리 합격선 900 / 830, §1의 ABUSE 0.320(화음 값), S15 평행 기준 | 모두 확인 | 수용 | 상한 0.45 하나로, 자리 합격선 830 N/mm(0.12 mm) 하나로, §1 2번에 한 건반 / 화음을 나눠 적음, S15를 ‘패드 없는 1 N 정착 바닥(11.36°)과 평행, 실제 바닥 10.75°에서 0.61° 기움’으로. |
| 기하 M1 | 윗판이 한 몸이 된 뒤 10장 순서(건반 먼저, 레버 나중)로는 흑 레버가 자기 흑건 위를 못 지나감(창 13.3 < 단면 20), 스프링을 단 레버는 풀린 다리가 뒷벽을 뚫어 쉼 자세로 못 놓음 | 2D C-공간(0.25 mm, 피치 −40~60°): 건반을 다 넣으면 C#·D·E·G# 레버 모두 막힘; 건반이 없으면 11 / 11 도달 | 수용 | 10장을 ‘레버 먼저, 건반 나중’으로 다시 씀. 레버 넣기 C-공간 검사를 run_all에 넣음(모든 레버와 끝 부속 A0·A#0·C8 도달). 다리는 손가락으로 감아 홈 입구(0.5×45°)에 걸고 놓음. 건반은 이미 검사한 빼기 경로의 반대로 넣음. |
| 기하 M2 | 패드 바를 뺄 때(모든 건반 빼기·심 조정) 흑 패드 아래 모서리 z55.40이 흑건 뒤끝 윗면 z55.5를 침(−0.10), 15~23 mm 사이 바를 받치는 것이 없음 | r4.0 형상: 곧게 당기면 -0.10(검증자 −0.10과 같음, r4.1 탐색) | 수용 (보완) | 제안대로 흑건 윗면을 가림판 밑(y144.3~147)만 z54.1로(입술 0.6), 레일을 y160까지 앞으로 늘림(바가 레일 높이 유지). 그러나 곧게만 당기면 마지막 0.5 mm에서 패드의 비스듬한 아래 모서리가 흑건 윗면 턱 모서리(y144.3)를 0.02로 스침(심 3장 -0.27) — 검증자의 1.30은 가장 낮은 꼭짓점만 본 값. 그래서 절차를 ‘앞부분이 윗판에서 나온 21.5 mm부터 바를 윗판 홈 천장에 밀어 올린 채 뺌’으로 정하고 그 경로를 검사: 최소 1.30(심 3장 1.21). 대가: 레일 립 때문에 칸 가장자리 레버의 서비스 들어올림 17.75° → 15.5°(빼기에 필요 13.1°). (r4.2 모델로 다시: 곧게 당기면 -0.39 — 잎 돌기가 립 앞끝을 지나면 바가 립까지 0.3 내려앉으므로 — 밀어 올림 절차는 1.30 / 심 3장 1.11) |
| 기하 m1 | 비틀림 스프링이 geometry에 없음; 건반 빠진 레버(−31.3°)는 자유각 −30°를 지나 다리가 0.8 홈에서 0.48 빠짐, 자유각 공차 ±5°면 빠질 수 있음 | r4.1 보스 입구(y207.8) 기준 다리 끝: 공칭 1.25 안, 자유각 −25°이면 -0.65(음수 = 입구 앞) | 수용 | 뒷벽 면에 출력 보스(레버마다, y207.8~209, 폭 3.2)를 두어 홈을 깊이 2.0(바닥 y209.8 그대로, 걸린 다리 그대로) + 입구 0.5×45°로. 공칭 −31.3°에서 풀린 다리 끝이 입구 안 1.25. 자유각 −25°(공차 끝)면 입구 앞 0.65에 있다가 레버가 올라갈 때 입구 경사가 다시 받아 줌. 주머니·짧은 다리 구멍·다리 방향·홈을 P18에 내보냄. 바닥 멈춤 기둥 안은 기각(레버 떨어짐 각이 바뀌어 검사한 빼기 경로가 바뀜). (r4.4까지의 D05 값 — r4.5는 보스 4.4, 홈 2.4 × 3.2, 풀린 다리 끝 입구 안 1.88, 1f장) |
| 기하 m2 | 캐리어 ‘1종’이 아니다(칼라가 위치마다 다름, 15종), 패드 바 6종, 예비 레버·바가 한 자리에만 맞음 | 위치 16곳, 서로 다른 칼라 짝 14종 | 수용 | 부품표에 칼라 표(위치별)와 패드 바 6종을 적고, 캐리어 옆벽·바 손잡이에 음 이름을 새김. 완성 예비 레버 2·예비 바 1은 없애고 위치별 파일로 필요할 때 출력(예비 강철 2·스프링 12는 유지). |
| 기하 m3 | 패드 바 뒤끝 y183.0, 멈춤(윗판 계단)은 y183.5: 매 음 +y 힘으로 0.5 뒤로 밀려 백 틈 −0.40 → 약 −0.30; 도브테일 언더컷이 안 내보내짐 | 확인 | 수용 | 바를 0.5 늘려 y146.5~183.5(뒤끝이 계단에 닿음) → 모델 위치 = 실제 위치. 레일 립(언더컷) 내보냄. 조정 전 ‘바를 끝까지 밀어 넣기’ 명시. (r4.2: 계단과 바 뒤끝을 y185.0로 다시 옮김, 1c장) |
| 기하 m4 | 패드와 캐리어 윗 립 사이 x 0.7, 스윕에서 뺀 짝; 공차가 쌓이면 립이 폼 옆을 물음 | 확인 | 수용 | 윗 립을 y168~184에서 끊음(강철은 y150~168·184~186 립과 앞벽이 잡음). 짝을 스윕에 넣음: 캐리어 옆벽 ↔ 패드 1.44. |
| 기하 m5 | C-링을 없앤 뒤 칸마다 축 놀음 0.32, 출력 면 9개 | 0.32 확인 | 수용 | 칼라마다 0.05 짧게 → 칸마다 놀음 0.46 / 0.46 / 0.43 / 0.30. 조립 때 레버가 제 무게로 자유롭게 도는지 확인, 아니면 칼라 면 사포질. |
| 기하 m6 | 빠진 것·글 불일치: 레버 봉 마개, 출력 공구, 2.0 육각 렌치, 끝 부속 봉 길이, P26 걸이 립 y, §1·U6·§18 값 | 확인 | 수용 | 마개·출력 공구 3종·육각 렌치를 부품표에; 레버 봉 끝 부속 45.9 / 22.2; P26 = y145.5~148.0; 나머지 글 고침. |

## 1b. 형상 변경 (geometry.json `changes_this_round`: r4.5 고침 → r4.5 회로 2차, r4.5 → r4.5 고침, r4.4 → r4.5, r4.4 고침 2b, 고침 2, 고침 4회차 r4.3 → r4.4, 3회차 r4.2 → r4.3, 2회차 r4.1 → r4.2, 1회차 r4.0 → r4.1)

r4.5 고침 행만 이 판에서 새로 썼다. r4.5 행은 r4.5 때 내보낸 값(`geometry.r4_5a.json`), r4.4 행(고침 2b·고침 2·4회차)은 r4.4 때 내보낸 값을 그대로 옮겼고(`geometry.r4_4.json`; 접착 단계 번호만 ‘10 step 4’로 고침), 1~3회차 행은 r4.3 때 내보낸 값이다.

| 회차 | 부품 | 치수 번호 | 전 | 후 | 이유 |
|---|---|---|---|---|---|
| r4.5 fix -> r4.5 circuit 2nd | frame (module): sensor-bar right ledge (v3 P112) - fixed prisms 'sensor-bar ledge lip / post front / rear', plan, sweep | P36 | not in the r4 geometry (v3 P112 x161.5-164.5 x y59.0-63.4 / y70.6-77.5, underside z13.6; the bar's right end was held by nothing) | two inverted L pieces y59.0-63.4 / y70.6-77.5: lip x161.5-163.0 z13.6-15.1 (underside = white bar top), post x163.0-164.3 z5.0-15.1; over the bar end x162.9 by 1.4, post 0.1 from the bar end; closest moving part 1.95 (key B tail wall R ff), next module 0.70, ER 0.70 | circuit 2nd request 8: BRD-02 drew the ledge dashed pending W1; the v3 frame mass (175 g) the model starts from already holds it, only the export had lost it. x end 164.3 instead of v3 164.5 = the r4 seam inset 0.2 (fins, top plate). Thickness z13.6-15.1 chosen for >= 1.3 to key B at its ff pose; the lip stays off the B lead rows |
| r4.5 fix -> r4.5 circuit 2nd | end part left (EL): floor | A02 | floor 0.2-46.25 + 'in front of / behind the board hatch' 46.25-46.8 - the module's control-board hatch cut (x46.25-118.25 y144.5-196.5) leaked in: gap x46.25-46.8 x y144.5-196.5 | one floor piece x0.20-46.80 y0.0-212.0, no hole (the hatch is a module feature only; end_fixed_prisms takes the module floor without board_hatch) | circuit 2nd request 11: end_fixed_prisms clipped the module's hatched floor to the end part's x range |
| r4.5 fix -> r4.5 circuit 2nd | dynamics / firmware ghost filter (U6): model rule and long runs | DESIGN 0.1, 0.2, 7.4; metrics ghost_* | gfilter: re-arm within 250 ms of the note-on, re-press speed ratio; held strikes stopped at 320 ms (v_desc 0.00 = no descent seen yet); text said 're-press within 250 ms' | same rule as SCH-03 note 9 + the re-press bound: first re-press judged only if it lands within 500 ms of the note-on; every held strike that re-arms is run on to 1500 ms after the note-on: 0 of 28 land again (latest 0 ms), all stop at their float point by 222 ms (float 22-96 %, creep <= 0.0005 m/s at the magnet) | circuit 2nd request 9: the text and the model used different windows, and ghost_reland was never inside the 320 ms runs |
| r4.5 fix -> r4.5 circuit 2nd | DESIGN 11 step 6 / 10 step 5 / 1d-2 row 7 text: landings of a lever whose key is out | DESIGN 11 | D#, F#, G, G# 'on the board top (z10.6, 16.8-24.0 deg)', E/F 13.3 deg | D# 16.75 deg (hung control-board boss, screw); E 13.25 deg (CD74HC4067 module top z20); F 13.25 deg (CD74HC4067 module top z20); F# 24.00 deg (board top z10.6); G 23.50 deg (board top z10.6); G# 16.75 deg (hung control-board boss, pin) | circuit 2nd request 10: D# / G# land on the hung control-board bosses (16.75 deg), not on the board top - geometry and drawing 12 already had it |
| r4.5 -> r4.5 fix | torsion assist spring (bought MISUMI C-UA90R5-3-0.5): short leg cut length | D05, parts list | short leg 2.5 (straight, bears on ONE groove face); k_t 8.866 N mm/rad, free -27.07 deg; rest / bottom / hand 25 deg 4.19 / 6.14 / 8.06 N mm (hand 107 % of the catalogue 55-deg torque) | short leg 8.0 (straight, CAPTURED in its groove); k_t 8.437 N mm/rad (leg bending of the captured leg: l = 2 s_E + l_s), free -28.45 deg; rest / bottom / hand 4.19 / 6.03 / 7.83 N mm (hand 104 %) | verifier spring major, re-checked (model_v4.spring_pose 'face'): the one-face short leg lets the net leg force push the coil 0.47 onto the D4 rod (toward 54 deg), the leg lifts off and the spring unwinds 13.4 deg: rest 2.18 N mm (-48 %), D DW 46.5, lip y0 42.2 (< 47), C# DW 46.0 (< 47), C# UW at the bottom x2 friction 18.9 (< 20) - three PLAY fails; notch rotated -12.9 deg restores the torque but the coil rubs on the fixed rod with 3.2 N (mu 0.3: C# UW bottom x2 14.2); short leg 5 + rotation still rubs (19.0); the captured leg carries the couple itself: coil 0.43 / 0.33 off the rod (rest / hand), no hysteresis |
| r4.5 -> r4.5 fix | lever carrier (all 16 positions, module + end parts): short-leg groove -> captured groove | P18 | groove band 1.70..3.00 from the axis along 230.36 deg (inner clearance 0.8 for the insertion along the 35 deg slot); leg bears on the outer face only; web cut 1.21 | groove 0.70 wide (play 0.20) along 136.83 deg = the loaded leg turned 1.99 deg CW, faces 2.511 / 3.211 from the axis, from ss -0.5 in the pocket through the hub wall into the web, blind 0.3 past the tip (ss 8.21); contacts: leg tip on the outer face (y195.30 z36.56) + leg on the inner face's pocket edge (y199.97 z33.13), arm 5.75 -> 0.73 N at rest, 1.36 N at hand 25 deg; web underside cut 3.79 | coil float (above); groove printed dp: -0.15 -> rest 4.41 N mm, rod gap 0.30; +0.30 -> rest 3.75 N mm, rod gap 0.17; 0.70 = printable slot (2 x 0.4 lines), the 0.5 wire still goes in at -0.15 |
| r4.5 -> r4.5 fix | lever carrier (all 16 positions): insertion slot and long-leg window of the pocket section | P18 | one parallel slot 35 deg, faces +3.25 / -3.25: the coil in, the long leg out | insertion slot along the captured leg 316.83 deg, faces +-3.25 (the coil comes in tip-first along its short leg); the rear opening runs from that slot's face round to the long-leg window's upper face (35 deg, +2.6): long leg in it over -31.3..18.0 deg with >= 0.57 (+ wire radius + 0.2); pocket section = piece A (web side, both leg contacts) + B (lower ring) | a captured leg cannot drop into its groove from a slot at 35 deg: the spring goes in along the leg; insertion path to the faces 0.100 (0.050 / 0.025 with the groove 0.10 / 0.15 narrower); hub / web at the groove ABUSE 7.96 MPa in layer (x Kt 2), PLAY 4.93 |
| r4.5 -> r4.5 fix | frame (module 12, end parts 3 + 1): rear-wall spring-groove boss and groove centred on the long leg | P18 | boss 4.4 and groove 2.4 centred on the lever (x +-2.2) | boss and groove centred on lever x +0.8 (the long leg leaves the coil's +x end there); groove + its 0.5 x 45 deg entry chamfer exported as female cut parts ('spring groove cut', 'spring groove entry chamfer') | verifier spring minor: with the coil sliding 0.438 in the pocket and the lever floating 0.405, the leg can sit 0.84 off its nominal x; the groove catches 1.45 about its centre: margin 0.61 (centred on the lever: -0.19) |
| r4.5 -> r4.5 fix | frame (module): F\|F# fin keel to the balance rail's rear face + the F\|F# fin's front edge | P12, S29 / plate FE | keel y144.5-152.0 z3-18, F\|F# fin from y152 (clamped to a rigid rail in the FE: chord seat 494.2 N/mm) | keel y144.5-148.6 z3-19.3; the F\|F# fin (floor underside z3 to the plate) now starts at y148.6 (was 152); FE root on the rail spring (rail + floor strip beam over the fin lines, kv 970 N/mm, kr 130174 N mm/rad, face 759 N/mm): chord seat 491.6 N/mm (r4.4 keel z18 / y152 447.5, rigid rail 494.7); first-module dead load 6 x 60 N: E/F seats 0.121 mm (pass <= 0.130) | verifier fixes minor: the keel root is a free edge of the floor hatch, the rail is not a rigid ground (stage-0 test 3 cannot see it); with the rail beam the r4.4 keel gives 447.5 < 460. The first fix-2 pass raised the keel to z21 (470.3 N/mm) but that left 0.21 to key F (balance block, dip_rigid pose: the key's right tail wall is over the F\|F# fin line); the keel stays at z19.3 (to key F balance block 1.34) and the fin itself comes forward to y148.6 (1.40 to key F skin tail, over pose), so the keel is 4.1 long instead of 7.5: 491.6 N/mm; bounds: rail clamped at the hatch edges 492.9, simply supported between the neighbouring fin lines only (no continuity, no EVA) 337.6 -> the stage-0 test 21 measures it |
| r4.5 -> r4.5 fix | stage-0 kit C06a / C06b (test 8), C17a and tests 13, 21 | stage0_geometry.json | C06a groove on the coil centre (x2.7); C06b hub replica with the 35 deg slot and the one-face short-leg groove, disk from x4.2; C06 rod 16 | C06a groove on the leg (x3.5); C06b = model_v4.hub_pocket_poly (captured groove 0.70, insertion slot, window) on a 2.0 hub spacer (disk from x6.2, 0.5 off the boss); C06 rod 18; test 8 one-sided groove-bottom limit; test 21 = first-module dead load (6 x 60 N, E/F <= 0.13 mm) in the service direction: module on the new C17a comb (3 high, teeth under the fin lines + a bar under the rear wall; nothing under the rail between the fin lines, hatch open), load from above (fix 3); C06b hub spacer D8.5 (fix 3: watertight STL) | the rig must reproduce the captured groove; the groove boss (to x5.7) would reach the r4.5 disk face (x4.2). Fix 3 (verifier major): in service the pads push the plate up and the keel lifts the rail; loading from above on the floor EVA only measured the rigid-rail case, so even a failing rail passed; the model is linear, so the comb support reproduces the service case. The C06b spacer at the hub radius shared a vertex with the pocket section |
| r4.5 -> r4.5 fix | metrics / DESIGN text: lever drop (key out, lever let go) | metrics lever_drop | D# 13.50 deg onto board components (<= z20); E 13.00 deg onto board components (<= z20); F 13.00 deg onto board components (<= z20); F# 13.50 deg onto board components (<= z20); G 13.00 deg onto board components (<= z20); G# 14.25 deg onto board components (<= z20) | D# 16.75 deg onto control-board boss D6 hung over th; E 13.25 deg onto CD74HC4067 module on pin headers (; F 13.25 deg onto CD74HC4067 module on pin headers (; F# 24.00 deg onto control board; G 23.50 deg onto control board; G# 16.75 deg onto control-board boss D6 hung over th | drafter: metrics lever_drop used the generic z20 envelope while drawing 12 used circuit_r44.drop; now both are the real landings (lever_drop(actual=True)) |
| r4.5 -> r4.5 fix | solved values (consequence, all modules / end parts): capstans, pad faces, pad-bar seat, top plate, printed wedges | S08, S15, P17, S16, S19, A06, A07 | lever 56.97 g; capstan y white 188.34 / black 180.31; pad face white z58.638~56.228, black z57.447~55.412; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.349~2.759, black 1.502~3.537; end-part wedges A0 0.293~2.721, A#0 1.502~3.537, B0 0.361~2.767, C8 0.261~2.700 | lever 56.95 g; capstan y white 188.34 / black 180.31; pad face white z58.640~56.230, black z57.448~55.412; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.347~2.757, black 1.501~3.536; end-part wedges A0 0.291~2.720, A#0 1.501~3.536, B0 0.359~2.765, C8 0.259~2.699 | r4.5 fix consequence: the lever is 0.016 g lighter (captured-groove pocket section, spring 0.134 g with the 8.0 short leg) and k_t 8.437 (was 8.866; same b = 0 torque), bottom torque 6.03 (was 6.14), so the capstans / settled bottom / pad faces / wedges move by the amounts shown |
| r4.4 -> r4.5 | torsion assist spring (bought, 100 = 88 + 4 stage-0 tests + 8 spares): custom D05 -> catalogue part | D05, parts list, cost | custom wound SUS304-WPB d0.5 ID 4.5 4.2 turns, short leg 2.5 bent 5.7 deg onto the slot face, long leg 22.3; k_t 8.0 N mm/rad, free -30.0 deg; 100 x 200 KRW (estimate) | MISUMI Korea C-UA90R5-3-0.5 (SUS304-WPB d0.5 ID 5.0, 3 turns = 3.25 body turns, arm angle 90 deg right-hand, arms 50/50), both arms cut: long 22.3 (axis -> tip; 22.13 from the tangent point), short 2.5 straight; k_t 8.866 N mm/rad (catalogue E 186000, N_e 3.725), free -27.07 deg (same b = 0 torque 4.19 N mm); long leg at the coil's +x end; 100 x 310 KRW (282 + VAT) | user decision 2026-09-28: buy a stock spring instead of having one wound; rest torque kept (DW / UW unchanged), bottom torque +3 %, hand-lift 25 deg torque 107 % of the catalogue's 55-deg torque (DESIGN 18) |
| r4.4 -> r4.5 | lever carrier (all 16 positions, module + end parts): hub spring pocket and coil / long-leg slot | P18 | pocket D6.1 x 3.0; slot 35 deg, faces +3.00 / -3.00 (6.0 wide), short leg on its upper face | pocket D6.6 x 3.0; slot 35 deg, faces +3.25 / -3.25 (6.5 wide: the free coil OD 6.0 passes with 0.25 per side); long leg in the slot over -31.3..18.0 deg with >= 0.63 to the faces | MISUMI coil OD 6.0 (ID 5 + 2 x 0.5): pocket radial clearance 0.30, the coil drops in through the slot |
| r4.4 -> r4.5 | lever carrier (all 16 positions): NEW short-leg groove through the hub wall of the pocket section (x +-1.5) | P18 | none (the short leg lay on the slot's upper face, bent 5.7 deg) | band 1.70..3.00 from the axis along 230.36 deg (lever frame), from ss -0.5 along the leg direction 140.36 deg out through the hub (inner face leaves it at y199.12 z34.71, bearing face at y198.96 z33.16); bearing face = outer (rm + d/2 = 3.00); web underside cut 1.21 deep over the pocket width; the pocket section is two pieces (A web side, B lower ring) | the catalogue part's swept angle (1170 deg) puts its short leg at 230.36 deg, 105 deg from the r4.4 short-leg seat (slot + 90 deg): it cannot leave through the slot; the leg is straight (tip y199.57 z32.98, r 3.72) and bears 1.13 on the face, tip 0.58 inside its end; slid in along the slot axis the leg drops into the groove (short leg to the web side min 0.53, 0.23 after FDM; inner clearance 0.5 would leave 0.25); ABUSE hub / web at the groove 7.95 MPa in layer (x Kt 2), piece B 0.17 MPa across layers |
| r4.4 -> r4.5 | frame (module 12, end parts 3 + 1): torsion-spring groove and boss on the rear wall | P18, S28 | boss 3.2 wide; groove 1.2 wide x 2.0 deep from the boss face (bottom y209.8), z47~58 | boss 4.4 wide; groove 2.4 wide x 3.2 deep (bottom y211.0: 2.0 into the rear wall, 1.0 of wall left behind it), z47~58 | the long leg leaves the coil end at x +0.8 (coil 2.13 long in the 3.0 pocket) and rises straight into the groove (r4.4: kinked from the coil end to a 1.2 groove); 3.2 deep keeps a keyless lever's unloaded leg 1.37 inside the mouth (r4.4 1.25) |
| r4.4 -> r4.5 | stage-0 kit C06a / C06b (test 8 spring rig) and test 13 | stage0_geometry.json | C06a groove 1.2 x to y209.8 (one-sided ledge at the leg plane), C06b hub replica: pocket D6.1, slot 6.0, short leg on the slot face | C06a groove 2.4 wide centred on the coil, bottom y211.0 (boss 4.4); C06b hub replica from model_v4.hub_pocket_poly: pocket D6.6, slot 6.5, short-leg groove; test 8 pass rest 4.19 / bottom 6.14 N mm +-15 %, test 13 = the insertion into the short-leg groove | the rig must reproduce the new pocket, slot, short-leg groove and rear-wall groove |
| r4.4 -> r4.5 | solved values (consequence, all modules / end parts): capstans, pad faces, pad-bar seat, top plate, printed wedges | S08, S15, P17, S16, S19, A06, A07 | lever 57.05 g; capstan y white 188.34 / black 180.31; pad face white z58.642~56.231, black z57.448~55.413; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.346~2.756, black 1.500~3.536; end-part wedges A0 0.289~2.719, A#0 1.500~3.536, B0 0.358~2.764, C8 0.257~2.698 | lever 56.97 g; capstan y white 188.34 / black 180.31; pad face white z58.638~56.228, black z57.447~55.412; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.349~2.759, black 1.502~3.537; end-part wedges A0 0.293~2.721, A#0 1.502~3.537, B0 0.361~2.767, C8 0.261~2.700 | r4.5 consequence: the lever is 0.081 g lighter (the pocket-section removal - pocket D6.6, slot 6.5, short-leg groove, web cut - is now counted whole: r4.4 counted the pocket cylinder only; spring 0.126 g instead of 0.15) and the spring rate is 11 % higher (k_t 8.866, same b = 0 torque), so the capstans / settled bottom / pad faces / wedges move by the amounts shown |
| r4.4 fix 2 -> fix 2b | frame (module): floor under the control board | P35, frame | solid floor z3-5 (the board sat on 4 floor stand-offs D6 x z5-9) | hatch x46.25-118.25 y144.5-196.5 (1.0 around the board) + notch x78.53-89.47 to y197.8 (1.0 behind the USB-C receptacle); the frame is 8.2 g lighter | verifier geometry CRITICAL: the board could not be put into the one-piece frame (F\|F# foot floor-to-plate through its front-open slot, the fin hung over its solid strip, the plate over it, 1.3 behind it); now it rises straight up from below: closest frame part along the path 0.60 (fin), stops = the four hung bosses |
| r4.4 fix 2 -> fix 2b | frame (module): F\|F# fin foot | P12, D18 | foot y152-170.7 standing on the floor (z5), grounded there | foot down to z3 in the hatch + keel y144.5-152 z3-18 (the fin plate continued forward inside the board slot) joined to the balance rail's rear face | the floor under the foot is gone; plate FE with the keel clamped at the rail: 6-key chord seat 494 N/mm (fix 2: 491.9 with a rigid floor), F / F# single seats 2406 / 2427 N/mm; keel bending 2.57 / 10.18 / 13.82 MPa (single PLAY / chord PLAY / ABUSE chord) |
| r4.4 fix 2 -> fix 2b | frame (module): 4 control-board stand-offs -> 4 bosses hung above the board | P35 | D6 x z5-9 on the floor at (50,149) screw, (114.5,149) pin, (50,192.5) pin, (114.5,192.5) screw; M3x6 from above (head on the board top); pins D2.8 up to z11.8 | same 4 points: D6 bosses above the board (z10.6 up), front two on brackets from the balance rail's rear face (to z17.0), rear two on brackets from the shelf ribs x50 / x116 and the shelf underside (to z18.05); M3x6 from BELOW (head under the board z7.35-9.0) into D2.5 blind bores to z15.4; pins D2.8 hanging down through the board to z7.8 | a board coming from below cannot pass stand-offs under it; bosses: closest BRD-01 part 1.93, head to the rail 1.65 / ribs 1.54 (unchanged plan points), board ring 1.15 |
| r4.4 fix 2 -> fix 2b | lever carrier (all 16 positions): side walls and top snap lips | P11, D07 | side walls 0.8 (pocket 9.0 = the steel: zero bond line), top lips 0.8 wide | side walls 0.7 (pocket 9.2: bond line 0.10 each side), top lips 0.9 wide (inner edge x +-3.7 and outside width 10.6 unchanged); front / rear walls 0.8 | verifier physics major 2: the bond had no gap to go into (10.6 - 2 x 0.8 = 9.0 = steel) and DESIGN 10 had no bonding step |
| r4.4 fix 2 -> fix 2b | steel block bond (all 90) | D07, parts list, 10 step 4 | 2-part 5-min epoxy after snapping in (thermal edge shear 2.24 MPa at dT 15 K, line 0.10 - above its 2.0 MPa strength) | MS-polymer (hybrid) flexible adhesive buttered on both steel faces, then snapped in; per note 0.067 + thermal 0.189 = 0.256 MPa, rare 0.099 + 0.379 = 0.478 (allowed 0.375 / 0.750); slip at the pad peak 0.0016 mm | verifier physics major 1: thermal-mismatch shear of a rigid bond on 0.8 PETG walls over 40 mm; stage-0 test 20 now cycles 5-45 C before the push / drop |
| r4.4 fix 2 -> fix 2b | key F: beam / thin-tail underside | KF | z21.90 over y184.0~195.8 | z21.95 over y176.0~195.8 (in front of the rest felt) | verifier geometry major: with the worst material set's PLAY return overshoot in the sweep the E / G thin tails and the F beam / tail came 1.27-1.30 from the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30 |
| r4.4 fix 2 -> fix 2b | key E: beam / thin-tail underside | KE | z21.8 | z21.90 over y184.0~195.8 (in front of the rest felt) | verifier geometry major: with the worst material set's PLAY return overshoot in the sweep the E / G thin tails and the F beam / tail came 1.27-1.30 from the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30 |
| r4.4 fix 2 -> fix 2b | key G: beam / thin-tail underside | KG | z21.8 | z21.90 over y184.0~195.8 (in front of the rest felt) | verifier geometry major: with the worst material set's PLAY return overshoot in the sweep the E / G thin tails and the F beam / tail came 1.27-1.30 from the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30 |
| r4.4 fix 2 -> fix 2b | sweep poses (all keys / levers): return overshoot and ff | S24, S25 | nominal + pass line: white key -0.415 / lever -2.85, black -0.324 / -1.81 deg; F -0.510 / -3.20 | + the worst material set (PLAY): white key -0.460 / lever -3.04, black -0.351 / -1.82 deg; F -0.533 / -3.31, F# -0.474 / -2.00 | verifier geometry major: the case grid's worst materials were computed but not swept |
| r4.4 fix 2 -> fix 2b | printed tool T2 (capstan bench gauge): dummy-lever floor and jig zero pads | S08, T-dims (tools_geometry.json) | floor plane / calibration-rod top z31.0 (the key-frame crown) | z30.90 = the crown at the settled rest (white 30.892, black 30.912): the key on the jig sinks on its notch cloth / rest felt as in the frame | verifier printables major: z31.0 turned every capstan out 0.108 (white) / 0.088 (black) mm = 1.73 / 1.41 eighth-turns (up-stop gap -0.40 -> about -0.73) |
| r4.4 fix 2 -> fix 2b | stage-0 test 20 (C16a / C16b): procedure | stage0_procedure.md | epoxy, room temperature only | MS polymer; 3 cycles 5 C (fridge / freezer) <-> 45 C (warm water in a bag / car) before the 116 N push and the 1 m drop | verifier physics major 1 (thermal mismatch) |
| r4.4 fix 2 -> fix 2b | solved values (consequence, all modules / end parts): capstans, pad faces, pad-bar seat, top plate, printed wedges | S08, S15, P17, S16, S19, A06, A07 | lever 57.02 g; capstan y white 188.34 / black 180.31; pad face white z58.642~56.231, black z57.448~55.413; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.345~2.756, black 1.500~3.536; end-part wedges A0 0.282~2.715, A#0 1.500~3.536, B0 0.351~2.760, C8 0.257~2.698 | lever 57.05 g; capstan y white 188.34 / black 180.31; pad face white z58.642~56.231, black z57.448~55.413; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.346~2.756, black 1.500~3.536; end-part wedges A0 0.289~2.719, A#0 1.500~3.536, B0 0.358~2.764, C8 0.257~2.698 | fix 2b consequence: the lever is 0.028 g heavier (side walls 0.1 thinner, MS-polymer film in the two bond lines), so the capstans / settled bottom / pad faces / wedges move by the amounts shown |
| r4.4 fix 1 -> fix 2 | lever carrier (all 16 positions, module + end parts): side walls in the pad zone | D07, S13 | side-wall top z52.0 (= the steel top) over y163~184 (between the top-lip segments) | side-wall top z49.4 over y163~184 (2.6 below the steel top: the wall passes under the pad face) | verifier geometry major 4a: with the lever's axial float (up to 0.41) and the pad bar's +-0.3 the wall stood 0.73 beside its own pad (fix-1 wall, same play); now 1.44 |
| r4.4 fix 1 -> fix 2 | lever carrier + steel block (all 90): retention | D07, parts list | steel snapped past the bottom lips only (the lips carry the carrier-steel load) | steel snapped in, then its two 19 x 40 side faces bonded to the side walls with 2-part epoxy (1411 mm2); the lips only hold it while the glue cures | verifier physics majors 1-2 + side-wall plate model: the snap alone opens 1.11-1.70 at PLAY 1.5 m/s (overhang 1.0) and bends the wall at the lip root to 23.5 MPa (in-layer limit 12), bottom lip 6.8 MPa across layers (limit 5); bonded: shear 0.067 MPa every note, 0.099 ABUSE (allowed 0.50 / 1.00) |
| r4.4 fix 1 -> fix 2 | lever carriers G/G#/A/A#/B: hub collars (module); end parts A#0 2.62/0.70 -> 2.62/0.76, B0 0.70/0.00 -> 0.76/0.00 | P14, K* | G 1.16/0.75; G# 0.75/0.00; A 0.00/0.74; A# 0.74/0.70; B 0.70/0.00 | G 1.16/0.76; G# 0.76/0.00; A 0.00/0.76; A# 0.76/0.76; B 0.76/0.00 | verifier geometry major 4b: a lever-lever pair's collars sum to >= 1.52 (A#\|B was 1.40); with the pair's free gap closed and both levers yawed the carriers keep 1.32 |
| r4.4 fix 1 -> fix 2 | frame (module + end parts): fin bosses on the lever rod | D06, P22, D18 | 0.00/1.35; 1.35/1.35; 1.35/1.35; 1.35/1.35; 1.35/0.00 | 0.00/1.37; 1.37/1.37; 1.37/1.37; 1.37/1.37; 1.37/0.00 | verifier geometry major 4 (axial float): a lever floated onto its boss and yawed was 1.30 from the fin's full-thickness front (y176); every boss +0.02 -> lever-fin 1.32; bay play 0.46 / 0.46 / 0.43 / 0.30 |
| r4.4 fix 1 -> fix 2 | frame (module + end parts): balance rail under every white-key block | P20 | top z19.0 over the whole block zone | pocket top z18.90 behind y137.4 (block x +-4.0 + the key-play margin; the pin row y135.3 stays z19.0) | verifier geometry major 3: with the notch seated / sinking on the rod the block's lip region comes to z20.258 (ff); pocket -> block-to-rail 1.31 |
| r4.4 fix 1 -> fix 2 | frame (module + end parts): balance rail under every black-key block | P20 | top z19.0 over the whole block zone | pocket top z18.80 behind y137.2 (block x +-4.0 + the key-play margin; the pin row y135.3 stays z19.0) | verifier geometry major 3: with the notch seated / sinking on the rod the block's lip region comes to z20.165 (ff); pocket -> block-to-rail 1.31 |
| r4.4 fix 1 -> fix 2 | key F: beam / thin-tail underside | KF | z21.8 | z21.9 over y184.0~195.8 (in front of the rest felt) | the notch seating on the rod (now in the sweep) brought the F tail at its own return overshoot to 1.24-1.25 of the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30 |
| r4.4 fix 1 -> fix 2 | key F#: beam / thin-tail underside | KF# | z21.8 | z21.9 over y184.0~195.8 (in front of the rest felt) | the notch seating on the rod (now in the sweep) brought the F# tail at its own return overshoot to 1.24-1.25 of the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30 |
| r4.4 fix 1 -> fix 2 | geometry.json key poses (all keys, module + end parts) | S24 | side_dip_rigid / side_ff / side_over = rotation about K only | rotation about K + the notch translation on the rod as swept (r44.key_shift; side_dip was already the exact planar state) | verifier geometry major 3: the exported dip had the notch sink but the sweep did not; now the sweep and the export use the same poses |
| r4.4 fix 1 -> fix 2 | printed tool T3 (balance-pin gauge): rear foot | T24 (tools_geometry.json) | land y136.75~138.0 | land y136.75~137.10, the body behind it 0.3 above the rail (the foot stays on the z19.0 surface in front of the rail pockets) | verifier geometry major 3 / printables: the rail pockets start at y137.2 (black) / y137.4 (white) |
| r4.4 fix 1 -> fix 2 | stage-0 coupons C03a / C03b / C03c (plate-modulus strip) | stage0_geometry.json | strip 80 x 12 x 5.5 on a 60 span, dial on the nose plate | strip 120 x 12 x 5.5 on a 100 span (C03b base 30 x 120), C03c nose with a D4 hole at mid-span so the dial reads the strip top directly | verifier printables major: the 6.5 % chord-seat decision rested on 0.018 mm of dial reading through three line contacts; now ~1.2 mm of signal |
| r4.4 fix 1 -> fix 2 | stage-0 kit: carrier C16a (production carrier C, 3) + base C16b (new, test 20) | stage0_geometry.json | no test 20 in the kit | C16a from model_v4.lever_prisms (bore / cavity cut in 2-D), C16b slotted base 40 x 46 x 8 (slot 9.6) | verifier printables major: test 20 (steel retention) now in the kit |
| r4.4 fix 1 -> fix 2 | solved values (consequence, all modules / end parts): capstans, pad faces, pad-bar seat, top plate, printed wedges | S08, S15, P17, S16, S19, A06, A07 | lever 57.13 g; capstan y white 188.33 / black 180.29; pad face white z58.635~56.226, black z57.440~55.407; pad-bar seat z67.30, top plate z72.80 (module top); wedges white 0.302~2.711, black 1.459~3.491; end-part wedges A0 0.246~2.673, A#0 1.459~3.491, B0 0.315~2.719, C8 0.220~2.657 | lever 57.02 g; capstan y white 188.34 / black 180.31; pad face white z58.642~56.231, black z57.448~55.413; pad-bar seat z67.35, top plate z72.85 (module top); wedges white 0.345~2.756, black 1.500~3.536; end-part wedges A0 0.282~2.715, A#0 1.500~3.536, B0 0.351~2.760, C8 0.257~2.698 | fix 2 consequence: the carrier side walls are 2.6 lower over the pad zone (0.11 g lighter lever), so the settled 1 N bottom and the pad faces move up 0.006-0.008; the pad-bar seat is rounded up to the next 0.05 (wedge >= 0.3 over the thickest-backed pad), so the seat and the whole top plate go up 0.05 and every wedge is 0.04 thicker |
| r4.3 -> r4.4 | lever carrier (all 16 positions, module + end parts): top snap lip, front segment | D07, S13 | lip 0.8 x 1.0 over y150~168 (lever frame), side-wall top z53 to y168 | lip 0.8 x 1.0 over y150~163, side-wall top z53 to y163 (z52 behind it to y184) | R44 issue 1: at the settled 1 N bottom and at ff the lip's rear end (y168) swung to world y172-173 z59-60 beside the pad: 0.64 (x gap 0.64 after the lever yaw), 0.34 after FDM; now lip to pad 2.15, to the pad bars / rails 1.81 |
| r4.3 -> r4.4 | lever carrier (all): top snap lip, rear segment | D07, S13 | lip 0.8 x 1.0 over y184~186, side-wall top z52 over y186~190 | lip 0.8 x 1.0 over y184~190 (to the steel's rear end / rear wall), side-wall top z53 over it | R44 issue 1 retention: the capstan pushes the steel's rear end up into these lips on every note (19.1 N peak PLAY): root bending across the layers 13.1 MPa with 2 mm (limit 5), 3.8 MPa with 6 mm |
| r4.3 -> r4.4 | keys F and F#: rest felt (cut piece) | P28, D10 | F x71.69~79.69, F# x86.94~94.94 (8.0 centred; 59 / 42 % on the shelf, the rest over the USB slot) | F x71.69~76.45 (4.76 wide, cut at the slot edge), F# x91.55~95.94 (4.39 wide, cut at the slot edge and run to the black thin tail's edge): 59 / 55 % land, nothing over the slot | R44 issue 2: the r4.3 felts overshot on the return into the USB plug envelope and (F#) its own lever: 4 pairs < 1.3 (min 1.14) at the F / F# overshoot (key -0.510 / -0.513, lever -3.20 / -2.09 deg); now none (the F felt no longer hangs over the plug; F# lands stiffer). No key or frame part changes; circuit interface untouched (slot x76.45~91.55, plug, board envelope) |
| r4.3 -> r4.4 | frame (module, end parts): pad-bar rail webs (8 per module, 2 per end part) | P13 | web front end y160.0 square (front-bottom corner y160.0 z64.75) | 45 deg chamfer 1.0 x 1.0 on the web's front-bottom corner (y160.0~161.0, z64.75~65.75) | the bay-edge carrier side walls pass that corner at ff with 1.30 (r4.3 1.32): the r4.4 lever lost 0.08 g of lip mass the r4.3 mass model double-counted and swings 0.02 deg higher; now lever-rail 1.54. The pad bar never touches that corner (it runs above z65.75) |
| r4.3 -> r4.4 | frame (module, end parts): lever-rod fin-boss bores, rod, rod-end plug | D18 (new), P22, D06 | text only ('printed D3.9 bores drilled D4.0', 'plug 1.2', 'blind wall 1.2'); not in geometry.json | fixed prisms 'lever rod D4 SUS304' x1.5~162.9, 'fin boss bore D4.0' per fin (right end fin blind to x163.1), 'lever rod end plug' x0.2~1.4 flush with the end-fin face; end parts: plug at the seam fin, cheek-side fin blind | R44 issue 1 (drafter): exported and swept so this class of miss cannot recur; closest moving part 1.77 |
| r4.3 -> r4.4 | geometry.json key poses (all keys) | S24 | key side_dip = max(settled, rigid) = the rigid kinematic bottom (white 4.04, black 6.22 deg) | key side_dip = the truly settled 1 N bottom with the pad as the full planar key state (white 3.98, black 5.99 deg + the notch settling on the rod = front point 4.05 / 6.08 deg about K); side_dip_rigid added; the sweep checks both | R44 issue 3: same pose as the levers' side_dip (settled with the pad); no part changes |
| r4.3 -> r4.4 | geometry.json overshoot poses of keys / levers F and F# | S24, S25 | F / F# swept at their colour's overshoot (white key -0.415 / lever -2.85 deg, black -0.324 / -1.81) | F key -0.533 / lever -3.31 deg, F# -0.474 / -2.00 from their own landing runs (PLAY on the 6-key chord seat + ABUSE single key, nominal + pass line); the colours keep white -0.460 / -3.04, black -0.351 / -1.82 (the added PLAY chord seats, grids and pass line are not deeper). ABUSE 6-key chord / 2.5 m/s on the chord seat: checked for no contact (min 1.27) | R44 issue 2: the return-overshoot pose sweep of F / F#; no part changes |
| r4.3 -> r4.4 | solved values (consequence, all keys / levers / pad bars): capstans, pad faces, printed wedges | S08, S15, P17, S25, A07 | lever 57.21 g; capstan y white 188.31 / black 180.28; pad face white z58.621~56.217 (tilt 11.33 deg), black z57.435~55.404; wedges white 0.315~2.719, black 1.463~3.494; end-part wedges A0 0.253~2.678, A#0 1.463~3.494, B0 0.321~2.723, C8 0.227~2.661; rigid lever bottom white 12.60 deg | lever 57.05 g; capstan y white 188.34 / black 180.31; pad face white z58.642~56.231 (tilt 11.36 deg), black z57.448~55.413; wedges white 0.346~2.756, black 1.500~3.536; end-part wedges A0 0.289~2.719, A#0 1.500~3.536, B0 0.358~2.764, C8 0.257~2.698; rigid lever bottom white 12.64 deg | the lever mass model counted the top lips over y150-186 and the side-wall top at z53 over the whole carrier (0.08 g too heavy); corrected with the r4.4 lips. Every change is <= 0.02 mm (below FDM resolution) but the drawings print these numbers |
| r4.3 -> r4.4 | control-board parts (circuit BRD-01 on the Zero's 2.54 lattice) | P27 | Zero x75.0~93.0; receptacle y188.2~195.5; 4067 x53.3~71.1 y152.4~193.0; J301 x61.59~79.37 y148.59/151.13 on top, 16-core ribbon on top (z13) centred x70.48; J302 x95.25~107.95 y193.04 | Zero x75.14~93.14; receptacle y189.5~196.8 (1.3 proud of the edge); 4067 x54.93~72.71 y152.0~192.64; J301 x61.28~79.06 y148.19/150.73 soldered from the underside (top joints <= z12.0); ribbon under the board z5~9 x60.01~80.64 (centred x70.48 in the lane, last 6 mm -0.31 to J301); J302 x94.30~107.00 y193.91 | circuit 1 (delta 15): receptacle centred on the shelf slot (x84.00); J301 on the underside so the ribbon never folds within 1.0 of the rail (verify round-1 geometry 3). Named parts to the frame >= 1.30; ribbon lane margins 1.32 / 1.36; ribbon under the board to the F\|F# fin foot 1.88 |
| r4.3 -> r4.4 | USB-C plug envelope (purchased cable) | P24 | face y195.5, overmould y195.5~220.5 | face y196.8, overmould y196.8~221.8 (x, z unchanged) | circuit 2: the receptacle stands 1.0~1.5 past the Zero's edge. Slot 1.30 / 1.30 over the whole shelf, rear-wall opening x 3.75 / top 2.70, cable passage 11.2 spare after a 25 bend |
| r4.3 -> r4.4 | frame (module): 4 control-board stand-offs | P35 (new) | none in geometry (v3 P114 spots (49.75,148)(114.75,148)(49.75,193)(114.75,193) in text only) | D6 x z5~9 at (50.0,149.0) screw, (114.5,149.0) pin, (50.0,192.5) pin, (114.5,192.5) screw; screw bosses bore D2.5 to z4.2 + M3x6 (v3.2 L35 ISO 7380 button head; head envelope D5.7 x 3.0); locating pins D2.8 to z11.8 | circuit 3 (delta 14): head (L35 D5.7) to the rail's rear face 1.65, to the shelf ribs 1.54 (1.45 on the rib axis; v3 spots with D5.5: 0.75 / 1.05); nearest BRD-01 part 1.93 |
| r4.3 -> r4.4 | frame (module): v3 sensor-board support + the sensor board (now in the model) | P36 (new) | not in geometry (v3 P111 post, P113 ribs, rear-rib gap x60~82) | post x0.5~6.0, front rib y61.0~62.8 / rear rib y73.2~75.5 over x6.0~158.5, top z7.0; rear-rib gap x59~82; SB x1.0~162.9 y60.65~75.89 z7.0~8.6 | circuit 5: the 16-core ribbon x60.32~80.64 had 0.32 on the left in the v3 gap; now 1.32 / 1.36 (= the lane) |
| r4.3 -> r4.4 | end part left: sensor-board support, lead lane, rear-wall notch | A02 | sensor bar only; no board support, no rear-rib gap, no way out for W401 | EL board x1.0~46.5; post x0.5~6.0 + ribs x6.0~45.0, rear-rib gap x15~38; balance rail lane x13.53~22.48 z5~10; rear-wall notch x13.53~22.48 z5~12 | circuit 4: lead pads 2.51 / 8.53 and underside wires 1.69 / 2.03 inside the gap; 5-core lead 6.35 + 1.3 each side, fanned in by y77.39; lead path to floor parts >= 1.30; passes the A#0 tab base with 1.75; board inside the bar |
| r4.3 -> r4.4 | end part right: sensor-board support, lead lane, rear-wall notch | A03 | sensor bar only; no board support, no rear-rib gap, no way out for W411 | ER board x1.0~23.0; post x0.5~6.0 + ribs x6.0~21.5, rear-rib gap x6~16; balance rail lane x7.59~14.00 z5~10; rear-wall notch x7.59~14.00 z5~12 | circuit 4: lead pads 1.35 / 1.77 and underside wires 2.25 / 2.37 inside the gap; 3-core lead 3.81 + 1.3 each side, fanned in by y77.39; lead path to floor parts >= 1.30; C8 pin has 1.3 of rail under it; board inside the bar |
| r4.3 -> r4.4 | control board keep-out (text) | P23 | keep-out x81.22~85.42 y145.5~173.2; the Zero overhang not stated | keep-out unchanged (stripboard pins / pads / traces); P23 records the RP2040-Zero PCB overhang x81.22~85.42 y172.0~173.2 (z11.9~12.9, no pins / pads / traces) | circuit 6: Zero front edge to the fin foot 1.30, its top parts to the hung fin 5.20 |
| r4.2 -> r4.3 | USB-C plug envelope (purchased cable, module) | P24 | x77.75~90.25, y195.5~220.5, z9.45~16.95 (v3: RP2040-Zero soldered flat, USB-C centre z13.2) | x77.75~90.25, y195.5~220.5, z10.7~18.3 (RP2040-Zero on pin headers +1.3, USB-C centre z14.5) | circuit 1: chips, crystal and LDO under the Zero; it cannot lie flat |
| r4.2 -> r4.3 | RP2040-Zero / USB-C receptacle zone (module) | P27 (new) | 'RP2040-Zero + USB-C receptacle (<= z15.5)' over the whole board width x47.25~117.25, y190~195.5 | RP2040-Zero x75.0~93.0 y172.0~195.5 on pin headers (PCB z11.9~12.9, top parts <= z16.3, pin tips trimmed); receptacle x79.53~88.47 y188.2~195.5 z12.9~16.1 | circuit 1 + 2: the Zero sits at x75~93 y172~195.5 (BRD-01) |
| r4.2 -> r4.3 | control-board component envelope (module) | P27 (new), P23 | <= z20 over y145.5~190 (fin keep-out +-1.0 = x81.42~85.22 to y173.0), <= z15.5 over y190~195.5 | <= z20 over y145.8~194.5 (keep-out +-1.2 = x81.22~85.42 to y173.2), <= z16.7 over y194.5~195.5; named BRD-01 parts: 4067 x53.3~71.1 y152.4~193.0 <= z20, J301 2x8 x61.59~79.37 y148.59/151.13 + 16-core ribbon, J302 1x6 x95.25~107.95 y193.04 | circuit 2: the 4067 (to y193) and the Zero reach behind y190; the envelope keeps 1.3 to the rail (front), the shelf / ribs (rear) and the fin foot (keep-out; r4.1's 1.0 left 0.8 after FDM) |
| r4.2 -> r4.3 | frame: rear shelf (module) | P19 | x75.6~92.4 between ribs 75 / 93 only 1.5 thick, underside z18.55 (0.25 above the raised plug) | open slot x76.45~91.55 over the full depth y195.8~209.0 (plug -+ 1.3); 2.0 thick on both sides | circuit 1: plug top z18.3; plug to the slot edges 1.30 (1.0 after FDM) |
| r4.2 -> r4.3 | frame: F\|F# fin (module, x82.42~84.22) | P12, S29 | foot y152~171 on the floor through the stripboard slot; y171~196.8 hung from z21.5; y196.8~209 down to the thin shelf (z18.55) over the plug | foot y152~170.7; hung from z21.5 from y170.7 all the way to the rear wall y209 (3.2 above the plug) | circuit 1 (fin stood on the cut shelf) + circuit 2 (foot rear face 1.3 from the Zero's front edge y172.0; r4.2 1.0). Plate FE: fin hung over the tunnel, weakest seat unchanged 1490 N/mm |
| r4.2 -> r4.3 | control board (v3 stripboard): slot / keep-out | P23 | slot x81.92~84.72 y145.5~172.0; parts / wires / ribbon header out of x81.42~85.22, y145.5~173.0 | slot unchanged (x81.92~84.72 y145.5~172.0); keep-out x81.22~85.42, y145.5~173.2 | 1.3 from the 0.1-inset fin foot; every BRD-01 part is already outside (no part moves) |
| r4.2 -> r4.3 | frame: balance rail ribbon lane (module) | P20 | x60~82 under the rail (z5~10) | x59.0~82.0 (z5~10) | circuit 3: the ribbon uses all 16 cores (20.32 wide, centred x70.48 on J301): margins 1.32 / 1.36 (r4.2 lane: 0.32 / 1.36) |
| r4.2 -> r4.3 | keys F and F#: rest-felt landing (consequence, no part change) | P28 | full 8.0 width on the shelf | F x71.69~76.45 (59 %), F# x91.55~94.94 (42 %) | the slot edges; dynamics re-run with the rest-felt contact scaled to 42 % (0.2 table) |
| r4.1 -> r4.2 | pad bar (all 6 kinds): joggle | P13, S17 | top step y169.5, bottom step y168.0 (high front part z67.30~68.80 over y146.5~169.5; plate channel ends y168.0 -> 1.5 x 1.5 overlap, 2.50 mm2 raster) | top step y167.0, bottom step y165.5 (front part z67.30~68.80 over y146.5~167.0, 1.0 in front of the channel end y168.0; lower part z65.80~67.30 from y165.5) | drafter 1: the bar could not slide in (it overlapped the plate) |
| r4.1 -> r4.2 | pad bar (all 6 kinds): length / rear stop | P13, P15 | y146.5~183.5 (37.0), plate step y183.5 (exported as a 0.5 ramp to y184.0) | y146.5~185.0 (38.5), plate step y185.0 exported as a vertical face | drafter 3: wedge / pad rear edges (y183.38 white, 183.17 black) were 0.12 / 0.33 from the step face (0.24 / 0.45 to the exported ramp); now wedge 1.42, pad 1.43 (to the step or the rail lips) |
| r4.1 -> r4.2 | top plate | P15 | underside z67.30 over y168~183.5, 0.5 mm ramps at the channel end (y167.5~168.0) and at the rear step (y183.5~184.0) | underside z67.30 over y168.0~185.0; both steps vertical faces (y168.0, y185.0); thick rear zone z60.80 from y185.0 | drafter 1 + 3 (pad seat stiffness of the plate FE 1550 -> 1490 N/mm, 6-key chord seat 492 N/mm) |
| r4.1 -> r4.2 | pad-bar rails (8 per module, 2 per end part) | P13 | y160~183.5, web 1.0 wide z65.60~67.30 (channel zone from z68.80), lip 0.6 wide z65.60~65.80 (0.2 thick) y160~183.5, 0.3 under the bar edge | web 1.0 wide y160~185.0 down to z64.70 (channel zone y160~168 from z68.80); lip 1.3 wide x 0.8 thick z64.70~65.50 over y163.5~185.0, 1.0 under the bar edge, its top 0.3 below the bar | drafter 2: the 0.2 lip with 0.3 overlap vanishes within +-0.3 FDM; the lips start at y163.5 so the bay-edge levers keep the 15.5 deg service lift |
| r4.1 -> r4.2 | pad bar: leaf tongues (2 per bar, printed) | P13 | 'leaf 0.6 x 4 x 8' in text only, not in geometry | tongue 0.6 thick x 1.6 wide x 8 long at each bar edge, y175~183 (root at the rear), bump 0.8 long resting on the lip (installed tip raised 0.3), cut free by a 0.4 slot and the window above it; 0.10 N per leaf | drafter 2: what holds the bar up and against its seat is now geometry (pad bar edge strips / leaf prisms) |
| r4.1 -> r4.2 | lever carrier (all): fingernail tab | S13, D08 | y148.2~149.2, z51.5~53.0 rectangle, 0.37 in front of the R3 corner (loose) | y148.2 to the R3 arc, z51.5~53.0 (fills the corner above z51.5; one piece with the front wall, distance -0.036) | drafter 4 |
| r4.1 -> r4.2 | lever carrier (all): hub spring pocket | P18 | pocket D6.1 x 3.0 closed all round in the R4.3 hub (not in geometry), short-leg hole D0.7 without position | pocket section x +-1.5 exported as its own outline: slot through the hub wall at 35 deg (lever frame), faces +3.00 / -3.00 from the axis (coil in, long leg out over -31.3..18.0 deg, min 0.57 to the faces); short leg 2.5 long bent 5.7 deg, its tip on the upper face 0.59 inside its end (no hole) | drafter 5 |
| r4.1 -> r4.2 | frame rear wall: torsion-spring groove (module 12, end parts 3 + 1) | P18 | groove z50~58 in the boss z47~plate (the leg passed 3 mm of boss under it) | groove z47~58, open at the boss underside; the tangent long leg reaches the boss face y207.8 at z44.94 and enters from below | drafter 5 (leg drawn tangent to the coil) - found while re-checking it |
| r4.1 -> r4.2 | torsion spring (model) | D05, P18 | long leg radial from the axis to y209.8, z54.82; short leg 'in a hub hole' | long leg tangent to the coil (rm 2.5) on the rear side, tangent point y205.71 z33.07, tip centre y209.55 z54.89; short leg 2.5 long (r4.1: 3), tangent, bent 5.7 deg | drafter 5: how the spring is made and fitted |
| r4.1 -> r4.2 | end parts: pad wedges | P17, A02, A03 | identical to the module wedges (A0/B0/C8 0.315~2.719, A#0 1.463~3.494) | each key's own face (parallel to its own settled 1 N bottom, design gap, as in its dynamics): A0 0.253~2.678 (module 0.315~2.719); A#0 1.463~3.494 (module 1.463~3.494); B0 0.321~2.723 (module 0.315~2.719); C8 0.227~2.661 (module 0.315~2.719) | drafter 6 (DESIGN 14 asked for it) |
| r4.1 -> r4.2 | end parts: sensor bars | A02, A03 | none in end_parts (parts list counted 2) | left x0.5~46.5 (low x19.93~33.93 at A#0), right x0.5~23.0; v3 section | drafter 6 |
| r4.1 -> r4.2 | end parts: spring grooves | P18, S28 | bosses only, grooves not exported | end_parts[side].spring_grooves + plan (left 3, right 1) | drafter 6 |
| r4.0 -> r4.1 | F\|F# fin (module, x82.42~84.22) | P12, S29 | y152~176 front extension hung from z21.5 (above the board parts) | y152~171 bottom z5.0 (floor) through the stripboard slot; y171~196.8 hung from z21.5; y196.8~209 unchanged | physics major 2: 6-key chord seat D#~G# 196 -> 492 N/mm |
| r4.0 -> r4.1 | control board (v3 stripboard) | P23 | x47.25~117.25, y145.5~195.5, no slot | open slot from the front edge x81.92~84.72, y145.5~172.0; parts / wires / ribbon header out of x81.42~85.22, y145.5~173.0 | lets the F\|F# fin reach the floor; RP2040-Zero (behind y172) and USB-C untouched |
| r4.0 -> r4.1 | black keys C#, D#, F#, G#, A# and A#0: top skin | S31 (new), S02 | top z55.5 to y147.0 (skin 2.0 thick) | top z54.1 over y144.3~147.0 (lip 0.6 thick, underside z53.5 unchanged); z55.5 in front of y144.3 | geometry major 2: pad-bar slide-out, black pad corner z55.40 hit the skin (-0.10) |
| r4.0 -> r4.1 | pad bar (all 6 kinds) | P13 | y146.5~183.0 (36.5 long), no preload | y146.5~183.5 (37.0 long, rear end on the plate step y183.5); leaf 0.6 x 4 x 8 on each rear-step edge, 0.3 preload up against the rail lip (text only) | geometry minor: the bar was driven 0.5 back on every note; no vertical play |
| r4.0 -> r4.1 | pad-bar rails (8 per module, 2 per end part) | P13 | y168~183.0, z65.60~67.30, no lip exported | y160~183.5: y160~168 hang from the channel ceiling z68.80 down to z65.60, y168~183.5 z65.60~67.30; lip 0.6 wide z65.60~65.80 under the bar's rear-step edge (overlap 0.3), y160~183.5 | geometry major 2 (bar held at rail height until its front part is out) + minor (dovetail undercut exported) |
| r4.0 -> r4.1 | lever carrier (all) | D07, S13 | upper lips y150~186 continuous | upper lips y150~168 and y184~186; none over y168~184 (beside the pad) | geometry minor: lip 0.7 beside the soft pad; pair now in the sweep |
| r4.0 -> r4.1 | lever carrier hub collars | P14 | C 0.000/1.005, C# 1.005/1.075, D 1.075/0.000, D# 0.000/1.555, E 1.555/0.975, F 0.975/0.000, F# 0.000/1.210, G 1.210/0.795, G# 0.795/0.000, A 0.000/0.785, A# 0.785/0.750, B 0.750/0.000 | C 0.000/0.955, C# 0.955/1.025, D 1.025/0.000, D# 0.000/1.505, E 1.505/0.925, F 0.925/0.000, F# 0.000/1.160, G 1.160/0.745, G# 0.745/0.000, A 0.000/0.735, A# 0.735/0.700, B 0.700/0.000 | geometry minor: every collar 0.05 shorter, axial play per bay 0.32 -> 0.50 |
| r4.0 -> r4.1 | frame rear wall: torsion-spring groove | P18, S28 | groove in the wall face y209.0~209.8 (0.8 deep), 1.2 wide, z50~58 | printed boss y207.8~209.0, x lever +-1.6, z47~plate underside; groove y207.8~209.8 (2.0 deep, bottom unchanged), 1.2 wide, z50~58, lead-in 0.5 x 45 deg | geometry minor: an unloaded leg (keyless lever at -31.3 deg) stays in the groove |
| r4.0 -> r4.1 | lever-rod end plug | P22 | in the model only (1.2) | listed part (printed, 1 per module / end part) | geometry minor: parts list |

## 1c. 도면 작성자 형상 지적과 해결 (r4.1 → r4.2)

도면 작성자는 r4.0 `geometry.json`(고침 1회차 전)으로 그렸다. 그래서 지적마다 먼저 r4.1 형상(`geometry.r4_1.json`)에서 다시 재고, r4.1에서 이미 고쳐진 부분은 숫자로 기각했다. 다시 돌린 범위: 한 모듈(옥타브 모듈은 모두 같다)과 끝 부속 이음매 — 고정 부품 겹침(0.02 mm 격자, 모듈·끝 부속), 스윕(모듈 1444쌍, 끝 부속 527 / 310쌍), 패드 바 넣고 빼기 경로, 레버 넣기, 서비스 들어올림, 스프링 다리 범위. 윗판 계단을 옮겨 패드 자리가 바뀌었으므로 동역학과 화음·유령 격자도 모두 다시 돌렸다(`run_all.py` 한 번).

| # | 지적 (도면) | 다시 잰 값 (r4.1 형상) | 판정 | r4.2 해결과 결과 |
|---|---|---|---|---|
| 도면 1 | 패드 바 앞부분(y146.5~169.5, z67.3~68.8)이 윗판 홈 끝(y167.5~168.0에서 z68.8 → 67.3)과 1.5×1.5 겹침(2.56 mm²), 모듈 4개·끝 부속 2개 모두 | r4.1 geometry에서 0.02 mm 격자로 2.50 mm² (y167.54~169.48, z67.32~68.78), 모듈과 양 끝 부속 모두 — 바 계단(윗 y169.5 / 아래 y168.0)이 홈 끝 y168.0보다 뒤. r4.1의 패드 바 빼기 검사는 윗판·레일을 ‘설계 미끄럼’이라 건너뛰어 못 봄 | 수용 | 바의 계단을 앞으로: 윗 계단 y167.0(홈 끝 y168.0보다 1.0 앞), 아래 계단 y165.5. 윗판 홈 끝과 계단 면은 geometry에서 수직 면(0.5 mm 표본 경사 없앰). 겹침 검사(모듈 0, 끝 부속 0 / 0)와 ‘넣고 빼는 내내 바 ↔ 윗판·레일’ 검사(최소 -0.01 = 접촉)를 run_all에 넣음. 빼기 절차의 밀어 올림(21.5 mm)은 이제 윗 계단이 윗판 앞면보다 1.0 앞일 때라 윗판과 겹치지 않음(r4.1은 21.5 mm에서 앞부분이 윗판 앞 1.5 mm와 겹쳤음). 도면 작성자의 `_chk_ff.py`(사본, `work_r4r2/drafter_chk/`)로 새 geometry를 다시 보면 패드 바 겹침 0; 남는 것은 밸런스 핀 ↔ 밸런스 레일(15.2 mm², 핀을 압입하는 구멍이 모델에 없을 뿐인 설계 압입). |
| 도면 2 | 바를 받치는 것이 없다: 레일은 1.0×1.7 블록, 바 옆 0.3 틈, 가장자리 밑 립 없음; P13의 ‘도브테일 폭 1.0, 높이 1.2’가 geometry에 없음 | r4.0 형상 기준 지적. r4.1에는 립이 있었지만 0.6 폭 × 0.2 두께(z65.60~65.80), 바 밑 겹침 0.3 — ±0.3 공차면 0; 예하중 잎은 글로만; 레일 높이는 1.2가 아니라 1.7 | 일부 수용 | L 레일: 웹 1.0(z64.75까지) + 립 1.3×0.8(z64.75~65.55, y163.5~185.0), 바 가장자리 밑 1.0 겹침(공차 뒤 0.7). 바 가장자리마다 출력 잎 혀 0.6×1.6×8(y175~183, 뿌리 뒤), 앞 끝 돌기가 립을 딛고 0.3 눌려 잎마다 0.10 N으로 바를 윗판 자리(z67.35)에 밀어 올림 — 모두 geometry 부품. 립은 y163.5부터(y160부터면 칸 가장자리 레버의 서비스 들어올림이 15.5° → 14.5°): 들어올림 15.5°. 두 잎의 힘 = 패드 붙은 바 무게(3.4 g)의 6.0배. 대가: 잎 상시 굽힘 8.2 MPa(공차 +0.3이면 16.5)가 2 MPa 크리프 선을 넘어 예하중이 풀릴 수 있음 — 반으로 풀려도 3.0배라 바는 자리에 남음; 17장 시험, 18장 위험. P13 글을 ‘L 레일 + 립 + 잎’으로 고침. |
| 도면 3 | 쐐기·패드가 바 뒤끝(y183.0)보다 뒤로 나옴(y183.38 / 183.17); 윗판 계단 면(y183.5~184.0)까지 쐐기 D 0.24, 패드 D 0.45, 쐐기 C# 0.45, 패드 C# 0.72 — 1.0 미만 | 튀어나옴은 r4.1에서 이미 없음(바 뒤끝 y183.5 > 183.38 / 183.17): 기각. 계단 틈은 r4.1에도 그대로: 내보낸 0.5 경사 면까지 0.235 / 0.443 / 0.444 / 0.712(도면 값과 같음), 설계 의도인 수직 면 y183.5까지는 0.12 / 0.33 | 일부 수용 | 윗판 계단과 바 뒤끝을 y183.5 → 185.0로(바 길이 38.5): 쐐기 뒤끝 ↔ 계단 1.62, 패드 1.62, 쐐기·패드 ↔ 레일 립 1.43(끝 부속 1.43). 바 뒤끝만 계단에 닿는다. 대가: 윗판이 두꺼운 곳이 1.5 뒤로 가서 가장 무른 패드 자리 1559 → 1492 N/mm, 6건반 화음 자리 492 N/mm — 동역학을 이 값으로 다시 돌렸고 모든 목표 통과(0.2장). |
| 도면 4 | 손톱 턱(y148.2~149.2, z51.5~53.0)이 R3 앞 모서리와 떨어져 떠 있음(0.42~1.35), 따로 출력됨 | r4.1 레버 형상에서 턱 ↔ 캐리어 거리 0.37 (턱은 사각형, 캐리어 앞 윗모서리는 R3 원호라 z51.5에서 y149.60, z52.5에서 y150.54). 질량 모델(lever_body)은 이미 모서리를 꽉 채워 계산하고 있었음 | 수용 | 턱을 밑면 z51.5 위의 R3 모서리까지 채운 한 몸 모양으로(앞면 y148.2 그대로): 턱 ↔ 캐리어 -0.036(≤ 0 = 붙음). 턱 바깥 윤곽은 그대로라 스윕·빼기 경로 값 변화 없음, 질량 모델 그대로. |
| 도면 5 | 비틀림 스프링을 조립할 수 없다: Ø6.1×3.0 주머니가 R4.3 허브에 사방이 막힘, 긴 다리가 나갈 홈 없음(−2.97°~+17.75°, 약 21°), 짧은 다리 구멍 위치·지름 없음 | r4.1 geometry의 허브는 속이 찬 R4.3 원(주머니도 없음); P18 글의 ‘지름 방향 입구’·‘구멍 Ø0.7’은 위치가 없고, 축 방향 짧은 다리는 지름 방향으로 코일을 넣으면 구멍에 들어갈 수 없음. 게다가 r4.1 뒷벽 홈(z50~58)은 보스(z47부터) 밑 3 mm를 남겨, 다리가 보스를 뚫고 지나감(접선 다리 z44.9, 반지름 다리 z48.3에서 보스 면에 닿음) | 수용 | 허브의 주머니 구간(레버 x ±1.5)을 따로 내보냄: 레버 기준 35° 방향 평행 홈(축에서 +3.00 / −3.00, 폭 6.0)이 허브 벽을 뚫어 코일(OD 5.5)이 봉을 넣기 전에 들어감. 긴 다리는 코일 뒤쪽 접선(y205.71 z33.07) → 홈 바닥 끝(y209.55 z54.89), 레버 -31.3°~18.0° 내내 홈 안(면까지 최소 0.57 + 선 반지름 + 0.2). 짧은 다리는 2.5로 줄이고(r4.1 3) 접선에서 5.7° 바깥으로 굽혀 끝이 홈 위 면에 얹힘(면 끝까지 0.59 남음; 구멍 없음, 되돌림 토크가 이 면으로). 뒷벽 홈을 보스 밑면(z47)까지 열어 다리가 z44.94에서 보스 면을 지나 밑에서 홈으로 들어감. 스프링은 모든 레버 자세의 부품(‘spring X’)으로 geometry에 넣음. (r4.4까지의 D05 값 — r4.5는 미스미 스프링: 홈 폭 6.5, 짧은 다리는 새 짧은 다리 홈, 1f장) |
| 도면 6 | 끝 부속에 스프링 다리 홈 없음; 끝 부속 쐐기가 모듈과 같음(14장은 A0 −0.05, B0 +0.01, C8 −0.08을 요구); 끝 부속 센서 바 없음(부품표는 2개) | r4.1 end_parts: 스프링 홈 보스는 있으나(왼 3, 오른 1) 홈과 평면이 없음; 쐐기 4개가 모듈 백·흑 쐐기와 똑같음; 센서 바 없음 — 모두 확인 | 수용 | 끝 부속 건반마다 자기 1 N 정착 바닥에 평행한 자기 패드 면(끝 부속 동역학이 쓰던 면 그대로)으로 쐐기를 만듦: A0 0.291~2.720(모듈 대비 -0.056 / -0.037), A#0 1.501~3.536(모듈 대비 +0.000 / +0.000), B0 0.359~2.765(모듈 대비 +0.012 / +0.008), C8 0.259~2.699(모듈 대비 -0.088 / -0.059); A0·C8 쐐기 얇은 끝이 0.3 아래(한 층 0.2 이상이라 출력 가능); 쐐기 뒤끝 ↔ 계단 1.61 / 1.61(왼 / 오). 센서 바: 왼쪽 x0.5~46.5(A#0 낮은 구간 x19.93~33.93), 오른쪽 x0.5~23.0. 스프링 홈(y207.8~209.8 z47~58)과 평면을 end_parts에 넣음. 끝 부속 스윕 최소 1.31 / 1.31, 겹침 0. |
| 도면 7 | 치수표 글 불일치: P15 ‘y186 뒤 z60.80’ vs 계단 y183.5; P26 걸이 립 y145.5~147.0 vs 부품 y145.5~148.0; D07 두 번째 아래 립 ‘192.0~190.0’(거꾸로, 없는 부품); 패드 면 길이 12.24 vs 재단 6×12 | P26은 r4.1에서 이미 y145.5~148.0(부품과 같음): 기각. P15(y186은 바 뒤끝 + 3을 쓴 글), D07(펠트 끝~강철 뒤를 거꾸로 씀), 패드(면 길이 = 12 / cos 11.33° = 12.24, 흑 12.17)는 확인 | 일부 수용 | P15: 홈 끝 y168.0·계단 y185.0(둘 다 수직 면) 뒤 z60.85. D07: 아래 립은 y165~176.5 하나, 강철 뒤 아래는 뒤 바닥 y190.8~192.5. P16·부품표·D16: 패드·PET 심 재단 6 × 12.2(면 길이). P13·P18·S13·D05·D08도 새 형상대로. |

## 1d. 제어 기판 인터페이스 — 회로 세션 결과와 해결 (r4.2 → r4.3)

회로 세션(`hardware/pcb`)이 r4.1 형상을 기준으로 제어 기판을 설계했고(BRD-01 `board/BRD-01_control_board_placement.svg`, 좌표는 `src/sheets.py`), 기구에 닿는 결과 3건을 보냈다. 하나씩 r4.2 형상에서 다시 재고, 부품을 늘리지 않고 한 모듈(옥타브 모듈은 모두 같다)에서 고쳤다. 끝 부속에는 제어 기판·USB가 없고(O1·O7이 EXT로 읽음) 뒤 선반·뒷벽이 x74~94 밖이라 바뀐 것이 없다. 다시 돌린 범위: 고정 부품 검사(플러그·기판 부품 ↔ 프레임), 스윕(모듈 1190쌍, 끝 부속 422 / 237쌍), 윗판 FE(F|F# 핀 뒤쪽을 매단 채), 쉼 펠트 착지 민감도 동역학 1벌, 굴림·선반 응력; 모든 계산은 `run_all.py` 한 번.

| # | 회로 쪽 결과 | 다시 잰 값 (r4.2 형상) | 판정 | r4.3 해결과 결과 |
|---|---|---|---|---|
| 회로 1 | RP2040-Zero는 밑면에 칩·수정·LDO가 있어 평평하게 납땜할 수 없음 → 안쪽 2.54 구멍에 핀 헤더로 세움, 약 +1.3: USB-C 중심 z14.5(v3 z13.2), 플러그 몰드 윗면 약 z18.3 | r4.2 플러그 외곽 z9.45~16.95. 새 외곽 z10.7~18.3(7.6 높이, 폭 ≤ 12.5, 길이 ≤ 25)로 재면: 얇은 선반(x75.6~92.4, 1.5T) 밑면 z18.55와 0.25(공차 뒤 -0.05), 선반까지 내려오던 F\|F# 핀 뒤쪽도 0.25, 리브 2.15, 뒷벽 개구(z21) 2.70; ‘RP2040 + 리셉터클 ≤ z15.5’ 구역(y190~195.5, 기판 전폭)은 새 리셉터클 윗면 z16.1을 담지 못함 | 수용 | 뒤 선반에 플러그 위 홈 x76.45~91.55(플러그 ±1.3)를 y195.8~209.0 앞뒤로 뚫음(홈 양옆 선반은 2.0T 그대로), F\|F# 핀은 선반에 내려오지 않고 발 뒤부터 뒷벽까지 z21.5에 매달림. 플러그 ↔ 선반 1.30, 리브 2.15, 핀 3.20, 뒷벽 개구 2.70(개구 x74~94 z5~21 그대로 — 키울 필요 없음), 뒤 케이블 통로(z0~22, v3) 안 3.7. RP2040 구역 → ‘RP2040-Zero 핀 헤더 위 x75~93 y172~195.5, PCB z11.9~12.9, 윗면 부품 ≤ z16.3(헤더 핀 끝은 자름)’ + 리셉터클 x79.53~88.47 z12.9~16.1. 부품 한계 z20은 y194.5까지, 선반 앞 띠 y194.5~195.5는 z16.7 이하(선반 밑면 z18.05와 1.3). 건반 빔·꼬리 ↔ 기판 부품 1.41(공차 뒤 1.11, 건반 E 얇은 꼬리 복귀 넘침), 건반 꼬리·쉼 펠트 ↔ 플러그 1.38(공차 뒤 1.08). 대가: F·F# 쉼 펠트가 홈 옆에 F 59 %, F# 42 %만 앉음(아래 동역학), 홈 옆 선반 응력 3.2 MPa(r4.2 얇은 선반 3.6), 굴림 되돌림/넘김 비(쉼) F 3.95 (r4.2 4.1), F# 1.77 (r4.2 15.9). |
| 회로 2 | 새 배치(BRD-01): 4067 모듈 x53.3~71.1 × y152.4~193.0(세로, 핀 헤더 위 ≤ z20), 리본 2×8 x61.6~79.4 y148.6/151.1, EXT 패드 x95.3~108.0 y193.0(뒤, USB 터널 옆); 모두 r4.1 홈·금지 구역 x81.42~85.22 × y145.5~173.0 밖 | 배치는 금지 구역 밖(확인: 리본 패드 오른끝 x80.27, 4067 x71.1, 저항·점퍼 x97.8~). 그러나 r4.2 모델은 (a) 부품 구역 z20을 y190에서 끊고 그 뒤를 z15.5로 둬 4067 뒤끝 y190~193(z20)과 맞지 않음, (b) 제로 앞 모서리 y172가 핀 발 뒷면 y171과 1.0(공차 뒤 0.7), (c) 금지 구역 ±1.0은 0.1 얇은 핀 발과 1.1(공차 뒤 0.8), (d) 부품 구역 앞끝(기판 모서리 y145.5)이 밸런스 레일 뒷면과 1.0 | 수용 | 핀 발을 y152~170.7로(0.3 짧게; 만능기판 홈은 y172.0 그대로라 회로 쪽 변화 없음) → 제로 앞 모서리와 1.30. 금지 구역 ±1.2 = x81.22~85.42, y145.5~173.2(BRD-01 부품은 이미 밖, 옮길 부품 없음). 부품 구역 z20을 y145.8~194.5로(레일 뒷면과 1.3, 선반 앞 띠는 위). BRD-01 부품을 이름 붙인 구역으로 geometry에 넣음(RP2040-Zero, 리셉터클, 4067, J301 리본 2×8 + 16심, J302 EXT) — 스윕과 고정 부품 검사가 봄: 기판 부품 ↔ 프레임 최소 1.30(기판 부품(z20 이하) ↔ 핀). 윗판 FE: F\|F# 핀 뒤쪽이 이제 USB 터널 위에 매달려(r4.2 FE는 얇은 선반을 바닥처럼 봄) 패드 자리 E 1568 → 1550, F 1978 → 1932, F# 1996 → 1950, G 1607 → 1589 N/mm; 가장 무른 자리(C# 1492)는 그대로라 동역학 자리 1490 N/mm 그대로, 6건반 화음 자리 492 → 492 N/mm. 레버 봉 반력(최대 154 N)은 매달린 핀 → 뒷벽 이음(1.8 × 39.3)으로: 전단 2.17, 굽힘 1.91 MPa. |
| 회로 3 | 리본 16심 모두 사용; EXT / JST-XH 순서 1 GND · 2~5 EXT1~4 · 6 3V3(빨강 끝선) — 모델이나 DESIGN.md가 옛 순서를 적었으면 글만 고칠 것 | 모델·DESIGN.md·parts_list 어디에도 리본·EXT 핀 순서 글이 없음(확인). 16심 × 1.27 = 20.32 리본이 J301 가운데(x70.48)에 놓이면 레일 밑 리본 차선 x60~82에서 양옆 0.32 / 1.36(공차 뒤 0.02) | 일부 수용 | 순서 글은 고칠 것 없음. 리본 차선을 왼쪽으로 1.0 넓힘(x59~82, 레일 밑면 z10, 높이 5.0): 양옆 1.32 / 1.36. EXT 선(O1·O7만): J302 뒤 선반 밑 칸(x93.6~103.4)은 뒷벽이 막혀 나갈 곳이 없으므로, 선을 기판 **아랫면**에서 납땜해 기판 밑(z5~9, 높이 4.0)으로 USB 터널(x75.6~92.4)까지 보내고, 플러그 밑(z5~10.7, 높이 5.7)으로 뒷벽 개구를 지나 뒤 케이블 통로로 — 회로 쪽 확인 필요(18장). |

**쉼 펠트 착지의 대가(동역학으로 확인).** 홈 가장자리가 F 쉼 펠트(x71.69~79.69)와 F# 쉼 펠트(x86.94~94.94)를 가로질러 F는 x71.69~76.45(59 %, 반력이 레버 선에서 -1.62), F#는 x91.55~94.94(42 %, 반력이 레버 선에서 +2.30)만 선반에 앉는다. 쉼 펠트 접촉 강성을 가장 작은 착지(42 %)로 낮춰(실효 e 0.35 그대로) 두 색 모두 다시 돌렸다: 연타 16.2 / 18.8 Hz(기본 16.2 / 18.8), 끝까지 복귀 45.4 / 39.9 ms(기본 45.4 / 39.9), PLAY 들림 0.104 / 0.058, 키퍼 0.34 / 1.08(기본 최소 0.52 — 무른 착지에서 복귀 때 앞이 더 튀어 가장 크게 줄어든 값이지만 무접촉), ABUSE 들림 0.101 / 0.178, 0.45 N 유령 16 % / 13 %(거름 대상). 정적으로는 펠트가 조금 더 눌려(Hertz 법칙, 쉼 반력 1.05 / 0.60 N) F 앞이 0.11, F# 앞이 0.09 mm 높게 쉬는데, 이것은 벤치 지그의 펀칭(0.1)으로 맞춘다. 착지 순간의 굴림 짝힘은 막대 반력의 되돌림을 빼고도 가이드 탭에 F 최대 2.57 N, F# 최대 1.73 N — 탭 천이 받는다.

**검토했지만 쓰지 않은 안.** ① 만능기판을 1.3 내려(받침 짧게) 플러그를 r4.2 높이로 되돌림 — 회로가 준 높이(USB-C z14.5)를 바꾸고, 기판 밑 공간이 4.0 → 2.7이 되어 아랫면의 C301(1206 칩, 아랫면 — r4.4 글 고침: r4.3 글은 ‘리드형 적층 세라믹’)·배선·헤더 핀 끝이 들어가기 빠듯함. ② 플러그 위만 선반을 올림 — F·F# 쉼 펠트가 플러그 폭 안(y196.3~199)에 걸려 있어 선반 윗면 z20.054를 바꿀 수 없음; 플러그 윗면 + 1.3 = z19.6이면 선반이 0.45 두께뿐. ③ 뒷벽 개구를 키움 — 필요 없음(2.70). ④ F·F# 쉼 펠트를 옮기거나 좁힘 — 건반 부품이 바뀌고, 착지 비율의 영향은 위 동역학에서 작음(연타·복귀 그대로, 키퍼 여유만 줄어듦).

(1d장 위 글은 r4.3 문서의 글을 그대로 옮겼다 — C301 한 곳만 고침. F·F# 쉼 펠트는 r4.4에서 바뀌었다 — 1e장. r4.3 이후 회로 쪽 값은 아래 1d-2.)

### 1d-2. 회로 세션 대조 요청 (r4.4)

회로 세션(`hardware/pcb`, 소유자)이 r4.3 모델을 회로도·BRD-01·BRD-02와 대조하고 W1 기구 쪽에 넣어 달라고 한 7건(`hardware/pcb/README.md` ‘W1 기구 쪽에 요청한 것’)을 이 모델에서 하나씩 쟀다. 7건 모두 모델 값과 맞아 받아들였다(3번은 실제로 사는 나사가 v3.2 L35 스텐 유두 렌치볼트 = ISO 7380 머리 Ø5.7이라 회로가 가정한 Ø5.5보다 머리 여유가 0.1 작지만 1.3 이상; 4번은 EL 리드를 패드 줄에서 기판 뒤끝 + 1.5 안에 모아 A#0 흑 탭 받침과 1.3 이상; 7번은 도면 12 글에 G#를 더하고 O1·O7의 G를 따로 적음). 다시 돌린 범위: 이 요청이 닿는 모든 고정 부품 검사(기판 부품 ↔ 건반·레버·핀 홈·금지 구역·패드 바 레일, 받침·M3 머리 ↔ 레일·리브, 기판 밑 리본과 차선, 플러그 y 전 구간 ↔ 선반 홈·뒷벽 개구, 끝 부속 리드 차선·뒷벽 홈, SB 리브 틈), 모듈 스윕 1444쌍(새 고정 부품 포함), 끝 부속 스윕 527 / 310쌍, 고정 부품 겹침·이음 검사, 건반 뺀 레버 떨어짐; 모든 계산은 `run_all.py` 한 번. 움직이는 부품·윗판·핀·패드 자리는 바뀌지 않아 동역학·8.1장(윗판 FE)은 그대로다(받침·리브는 바닥 위 보스라 윗판 하중 길이 아님).

| # | 회로 쪽 요청 | 이 모델에서 잰 값 | 판정 | r4.4 반영과 결과 |
|---|---|---|---|---|
| 회로 1 | BRD-01 부품을 2.54 격자로(제로 핀 격자 x = 76.52 + 2.54i): 제로 x75.14~93.14(+0.14, Waveshare 치수도상 USB-C가 오른쪽 모서리에서 4.67), 4067 x54.93~72.71 × y152.0~192.64, J301 x61.28~79.06 y148.19/150.73 아랫면 납땜 → 리본은 기판 밑 z5~9(차선 안에서는 가운데 x70.48, J301 쪽 끝 6 mm만 0.31 비낌), J302 x94.30~107.00 y193.91, 리셉터클 x79.53~88.47 그대로 | 리셉터클 가운데 x84.00 = 선반 홈 가운데 x84.00(홈 양옆 1.30 / 1.30 그대로). 이름 붙은 BRD-01 부품 ↔ 출력 프레임 최소 1.30(RP2040-Zero(핀 헤더 위) ↔ 선반 리브), 4067 ↔ 금지 구역 8.51, J302 ↔ 선반 리브 앞면 1.99. 리본 20.32 폭이 차선 x59~82 가운데 x70.48에서 양옆 1.32 / 1.36; J301 가운데 x70.17라 끝 6 mm만 -0.31 — 레일 뒷면 y144.5 뒤(기판 밑)라 차선 여유는 그대로. 기판 밑 리본(z5~9, 높이 4.0) ↔ F\|F# 핀 발 1.88, ↔ 받침 (50,149) 7.16, 금지 구역 밖 0.58. 건반 빔·꼬리 ↔ 기판 부품 스윕 1.31(건반 F# 복귀 넘침) | 수용 | P27에 격자 값(치수 표), geometry의 이름 붙은 기판 부품을 새 자리로; J301은 윗면 납땜 자국(z12.0 이하)과 새 부품 ‘J301 리본(기판 밑, z5~9)’ 둘로; 평면에 기판 밑 리본·SB → 차선 리본·J201 패드. |
| 회로 2 | 리셉터클이 제로 가장자리 밖으로 약 1.3(1.0~1.5) → 플러그 면 y196.8, 몰드 y196.8~221.8, 리셉터클 y189.5~196.8 | 선반 홈 양옆 1.30 / 1.30 — 선반 y196.8~209.0 내내(x로만 정해지므로 y 이동과 무관), 리브 2.15 / 2.15, F\|F# 핀 3.20, 뒷벽 개구 x 3.75 / 3.75 · 위 2.70(y209~212 내내), 뒤 케이블 통로 y215~258(v3 A13): 끝 y221.8 + 굽힘 25 = y246.8(11.2 남음, r4.3 12.5), 통로 위 3.7. 리셉터클 ↔ 홈 가장자리 3.08, 리브 3.93, 윗면 z16.1 ≤ 선반 앞 띠 z16.7. 건반 꼬리·쉼 펠트 ↔ 플러그 스윕 1.56(건반 F#) | 수용 | P24 = y196.8~221.8(x·z 그대로). 선반 홈·뒷벽 개구는 바꿀 필요 없음. |
| 회로 3 | 프레임에 제어 기판 받침 4개 Ø6 × z5~9: 나사 받침 (50.0,149.0)·(114.5,192.5)에 Ø2.5 구멍을 바닥 속 z4.2까지(M3×6), 출력 위치 핀 (114.5,149.0)·(50.0,192.5) Ø2.8(기판 위 1.2); v3 P114 자리는 M3 머리 Ø5.5가 레일 0.75·리브 1.05라 옮김 | M3×6 = v3.2 구매 목록 L35 ‘스텐 유두 렌치볼트 M3 × 6mm’(ISO 7380 버튼헤드, 머리 Ø5.7 × 1.65; 모델은 머리 외곽 Ø5.7 × 3.0로 잡아 DIN 912 Ø5.5 × 3.0도 덮음) 머리 ↔ 밸런스 레일 뒷면 1.65, ↔ 선반 리브 1.54(리브 축 위로 재면 1.45; 회로 값 1.75 / 1.55는 Ø5.5), 머리 가장자리가 기판 모서리 x47.25 / 117.25 밖으로 0.10(머리 밑면은 기판 위, 나사 구멍 Ø3.2 둘레 기판 1.15); 위치 핀 ↔ 레일 3.10, ↔ 리브 2.90; 받침·머리·핀 ↔ 가장 가까운 BRD-01 부품 1.93, ↔ 핀(지느러미) 4.44; 받침 Ø6은 기판 가장자리 밖으로 0.25(받침은 기판 밑). 나사 길이: 기판 1.6 + 받침 4.0 + 바닥 0.8 = 6.0, 끝 z4.6, 구멍 끝 z4.2(0.4 남음), 구멍 밑 바닥 1.2, 물림 4.4. 건반·레버 ↔ 머리 스윕 1.57 | 수용 (부품 추가: 모듈당 나사 2) | P35(새 치수), 프레임 출력에 받침 4·위치 핀 2(geometry 고정 부품 + 평면 원). 부품표에 ‘제어 기판 나사 M3×6 스텐 유두 렌치볼트(ISO 7380)’ 모듈당 2, 합계 14 — v3.2 구매 목록 L35(20개 800원)로 이미 기본 구성에 있어 비용 변화 0; 모듈 구매 부품 수 +2(r3 수 249에도 없던 v3.2 부품). r4.4 고침 2b: 바닥 받침 위로는 기판을 넣을 길이 없어(검증 critical) 같은 네 자리의 보스를 기판 위에 매달고 나사를 밑에서 조임 — 1e장 ‘고침 2b’, P35. |
| 회로 4 | 끝 부속 EL·ER: 센서 기판 받침(기둥 x0.5~6.0 + 앞·뒤 리브 = v3 P111~P113), 뒤 리브 틈 EL x15~38 · ER x6~16(리드 패드 J401 x18.41~28.57, J411 x8.25~13.33, y74.62), 리드 길 = 레일 밑 차선 z5~10(EL 5심 6.35, ER 3심 3.81 + 양옆 1.3) + 뒷벽 홈 z5~12. EL 기판 x1.0~46.5, ER x1.0~23.0 | EL 기판 x1.0~46.5가 센서 바 x0.5~46.5 안, ER x1.0~23.0가 x0.5~23.0 안. 뒤 리브 틈: 패드(±0.9) 여유 EL 2.51 / 8.53, ER 1.35 / 1.77; 아랫면 선이 리브 띠(y73.2)에 드는 x — EL 16.69/27.75/35.97/18.41/28.57 → 1.69 / 2.03(B0 선 x35.97), ER 13.63/8.25/13.33 → 2.25 / 2.37. 리드 차선(레일 밑): EL 5심 6.35 + 1.3×2 = 8.95, x13.53~22.48(리드 가운데 x18.00: A#0 흑 탭 받침 x22.93~30.93 y79~93이 바닥에 있어 그 왼쪽으로 1.75 비껴 감; 차선 위 밸런스 핀 없음), ER 3심 3.81 + 2.6 = 6.41, x7.59~14.00(J411 가운데; C8 핀 밑 레일 1.3 — 모듈 리본 차선의 E·F 핀과 같음). 뒷벽 홈 같은 x z5~12: 뒤 도브테일과 20.53 / 3.59, 끝 핀과 13.73 / 5.79. 리드 길(패드 줄에서 y77.39까지 모음 + 곧은 길) ↔ 바닥 부품 최소 EL 1.30 / ER 1.30(차선·홈 옆 레일·뒷벽 = 1.3; 모음 ↔ 뒤 리브 끝 1.45, ER 받침 기둥 1.35; 1차 시도 그림의 y78.89 모음은 탭 받침 모서리와 0.76). 끝 부속 스윕 최소 1.31 / 1.31(1.3 미만 0) | 수용 (차선 x는 W1이 정함) | A02·A03 치수, geometry 끝 부속에 센서 기판·받침 기둥·앞 리브·뒤 리브(틈)·레일 밑 차선(레일 밑면 z10)·뒷벽 홈(‘rear wall (over the lead notch)’) + 평면(리드 패드·아랫면 선·리드 길·차선·홈). 리드 길: 패드(아랫면) → 기판 밑 → 뒤 리브 틈 → 바닥(건반 밑; y77.39까지 EL은 x14.83~21.18, ER은 x8.89~12.70로 모음) → 레일 밑 차선 → 바닥 → 뒷벽 홈 → 뒤 통로의 X401·X411. |
| 회로 5 | SB 뒤 받침 리브 틈 x60~82 → x59~82 (리본 x60.32~80.64가 왼쪽 0.32) | v3 틈 x60~82면 리본 양옆 0.32 / 1.36; x59~82면 1.32 / 1.36(= 리본 차선); J201 패드(±0.9) 1.69 / 1.73 | 수용 | P36(새 치수): v3 센서 기판 받침(기둥 x0.5~6.0, 앞·뒤 리브 x6.0~158.5, 윗면 z7.0)과 센서 기판을 모델·geometry에 넣고 뒤 리브를 x59~82에서 끊음. |
| 회로 6 | 금지 구역 끝을 y172.0으로 줄이거나, 제로 PCB가 y172.0~173.2에 걸치는 것을 P23에 적기 | 제로 PCB(z11.9~12.9, 핀 헤더 위)가 x81.22~85.42 × y172.0~173.2에 걸침; 헤더 열 x76.52 / x91.76는 금지 구역 밖. 제로 앞 모서리 ↔ 핀 발 뒷면 1.30, 제로 윗면 부품 ↔ 매달린 핀 밑면(z21.5) 5.20 — 두 안 모두 1.3을 지킴 | 수용 (둘째 안) | 금지 구역은 만능기판 위 핀·패드·배선을 위한 것이라 y173.2 그대로(홈 끝 잘린 면에서 1.2; 잘린 면 바로 뒤 패드는 떨어지기 쉬움). P23에 ‘제로 PCB만 걸침, 그 안에 핀·패드·배선 없음’을 적음 — BRD-01 글과 같음. |
| 회로 7 | 글: 1d장 C301은 1206 칩(리드형 아님). 도면 12: D#·F#·G 레버는 z20 한계가 아니라 기판 윗면에 떨어짐 | C301: 회로 BOM대로 1206 칩(아랫면). 건반 뺀 레버를 실제 BRD-01 부품·받침 머리·핀으로 떨어뜨리면: D# 16.75°(기판 위 매단 보스(나사 보스)); E 13.25°(4067 모듈 윗면(z20)); F 13.25°(4067 모듈 윗면(z20)); F# 24.00°(기판 윗면(z10.6)); G 23.50°(기판 윗면(z10.6)); G# 16.75°(기판 위 매단 보스(위치 핀 보스)); O1·O7의 G는 R301(누운 1/4 W, Ø2.5 가정) 위 20.8°. z20 한계(어디에나 z20 부품이 있다고 볼 때)로는 D# 13.5°, E 13.0°, F 13.0°, F# 13.5°, G 13.0°, G# 14.3° | 수용 (O1·O7의 G는 R301; r4.5 회로 2차 고침: D#·G#는 기판 윗면이 아니라 매단 보스 위) | 1d장 C301 글 고침(위). 11장 6번 글을 실제 떨어짐으로 고침; 도면 12(도면 작성자)는 이 값으로 고쳐야 한다. 가장 깊은 떨어짐은 여전히 바닥판 30.75°(C#·A#)라 스프링 다리 검사 범위는 그대로. |

회로 쪽에 알릴 것(인터페이스): (1) 끝 부속 리드 차선 EL x13.53~22.48, ER x7.59~14.00(레일 밑 z5~10, 뒷벽 홈 z5~12 같은 x) — 리드는 패드 줄에서 기판 뒤끝 + 1.5(y77.39) 안에 모아 EL x14.83~21.18, ER x8.89~12.70로(EL은 A#0 흑 탭 받침 왼쪽 1.75). (2) 제어 기판 나사는 v3.2 L35 스텐 유두 렌치볼트(ISO 7380) 머리 Ø5.7 × 1.65(윗면 z12.25; 모델 외곽 Ø5.7 × 3.0): 회로 △14의 Ø5.5 가정보다 머리 여유가 0.1 작아 레일 1.65, 리브 1.54(축 위 1.45), 머리가 기판 모서리 밖 0.10 — DIN 912(Ø5.5 × 3.0)로 사면 회로 값 그대로. (3) 금지 구역은 y173.2 그대로(P23에 제로 걸침을 적음). (4) O1·O7의 G 레버는 건반을 빼면 R301 위에 0.40 N으로 놓인다.

**r4.5 회로 2차 대조** (2026-09-29, `hardware/pcb/README.md` ‘2차 요청’): 회로 세션이 r4.5 사본을 회로도 개정 B와 다시 맞춰 본 요청 가운데 8~11. 12(구매 목록 글)와 13(단계 0 시험 21 뒤 리본 차선을 바꾸면 알림)은 다른 곳에서 한다. 모든 값은 `run_all.py` 한 번(Q3절, E2절).

| # | 회로 쪽 요청 | 이 모델에서 잰 값 | 판정 | 바꾼 것과 결과 |
|---|---|---|---|---|
| 8 | 센서 바 오른쪽 턱(v3 P112, x161.5~164.5 × y59.0~63.4 · y70.6~77.5, 밑면 z13.6)을 모델에 넣거나, 턱 없이 바 오른쪽 끝을 무엇이 잡는지 P36에 적기 | r4.5 geometry에 턱이 없음 — 바·기판(x0.5~162.9)의 오른쪽 끝을 잡는 것이 없었다: 왼쪽 M3×10 2개(x3.0)와 리브(z7.0 받침, x158.5까지)뿐이라, 모듈을 뒤집어 제어 기판을 넣을 때(10장 1단계) 바·기판이 왼쪽 나사에만 매달린다. 모델이 출발한 v3 프레임 질량 175 g에는 턱이 들어 있고 r4 내보냄에서만 빠졌다 | 받아들임 (모델에 넣음) | P36·고정 부품·평면·스윕: 두 조각 y59.0~63.4 · y70.6~77.5(B 센서 리드 줄 y63.9~70.1와 0.5 / 0.5), 각각 ㄱ자 — 립 x161.5~163.0 z13.6~15.1(밑면 = 백 구간 바 윗면 z13.6, 바 끝을 1.4 덮음, 15.8 mm²), 기둥 x163.0~164.3 바닥 z5.0부터(바 끝과 0.1, 기판 끝과 0.4). x 끝은 v3 164.5가 아니라 164.3(r4 이음 면 0.2 들임, 핀·윗판과 같음). 립은 B 리드 구멍 열 x160.65에서 0.85. 가장 가까운 움직이는 부품 1.95(공차 뒤 1.65, 건반 B 꼬리 오른 옆벽 ff 최대); 이음매 너머 고정 부품: 이웃 모듈 0.70(센서 바), 끝 부속 ER 0.70; 기판 부품 구역(아랫면 C214 x156.9~159.3, J201) 밖. 바·기판은 모듈을 따로 둔 채 1.5 mm 왼쪽에 내려놓고 오른쪽으로 밀어 턱 밑에 넣은 뒤 왼쪽 나사를 조인다(v3 절차). 끝 부속 바(EL 46.0 mm, ER 22.5 mm)는 턱 없이 같은 왼쪽 M3 2개 + 리브(짧고, 기판 넣기로 뒤집지 않음) |
| 9 | 유령 거름(U6) 글을 run_all.py gfilter와 같게(창 = note-on부터 재무장까지 250 ms), 무장된 28건을 1 s 이상 돌려 유령이 다시 닿는 시각(ghost_reland)으로 ‘다시 눌림 시각 상한’ 정하기 | 맞음: 글(0.1)은 ‘250 ms 안에 다시 눌림’, gfilter는 ‘note-on부터 재무장이 250 ms 안’(다시 눌림 시각은 안 봄). 게다가 누른 채 계산이 320 ms에서 끝나 다시 닿음은 한 번도 계산 안에 없었다(내려옴 0.00 = 아직 안 내려옴). 재무장 28건을 note-on 뒤 1.5 s까지 다시 돌리면: 스스로 다시 닿는 것 0건; 재무장 67.1 ms 안, 흔들림 멈춤 ≤ 222 ms, 끝 자석 위치 22~96 %, 끝 기어내림 ≤ 0.0005 m/s(자석; 모델 마찰이 0.2 mm/s 아래에서 비례라 생기는 값) → 그 속도로 가장 빨라도 3.8 s 뒤 바닥 | 받아들임 | 글(0.1·0.2·7.3·7.4·18장, 시험 11)과 gfilter를 SCH-03 주 9 형태 + **다시 눌림 시각 상한 = note-on부터 500 ms**로. 기구는 상한을 정하지 않는다(0.45~0.5 N 손가락이 건반을 뜬 자리에 붙잡아 유령이 스스로 오지 않음) — 유령 다시 눌림은 손가락이 만든다. 500 ms = 흔들림이 멈추는 가장 늦은 222 ms의 약 2배; 단계 0 시험 11의 펌웨어 기록에서 유령 다시 눌림이 500 ms를 넘으면 창 = (가장 늦은 것 + 100 ms). 못 거른 것 0 / 350 |
| 10 | DESIGN 11장 6단계 글: D#·G# 레버는 기판 윗면이 아니라 매단 보스 위(16.75°) | 맞음: 글은 ‘D#·F#·G·G#가 기판 윗면(z10.6, 16.8~24.0°)’, geometry(`circuit_r44.drop`)·도면 12는 D# 16.75°(기판 위 매단 보스(나사 보스)); E 13.25°(4067 모듈 윗면(z20)); F 13.25°(4067 모듈 윗면(z20)); F# 24.00°(기판 윗면(z10.6)); G 23.50°(기판 윗면(z10.6)); G# 16.75°(기판 위 매단 보스(위치 핀 보스)) | 받아들임 | 11장 6단계, 10장 5단계, 1장 L 블록 행, 1d-2 회로 7 판정 글을 이 값으로(바뀐 수치 없음) |
| 11 | 끝 부속 EL 바닥에 모듈 기판 구멍 자르기가 새어 생긴 틈 x46.25~46.8 × y144.5~196.5 없애기 | 맞음: `end_fixed_prisms`가 모듈 바닥(기판 구멍 x46.25~118.25 y144.5~196.5가 잘린 조각들)을 끝 부속 x0.2~46.8로 잘라 그 틈이 EL 바닥에 남았다(EL엔 제어 기판이 없음) | 받아들임 | 끝 부속은 기판 구멍 없는 모듈 바닥을 받는다(구멍은 모듈에만): EL 바닥 x0.20~46.80 y0~212, 구멍 없음; ER x0.20~23.30 y0~212. 질량은 이미 구멍 없이 셈 |

회로 쪽에 알릴 것: 인터페이스 값은 하나도 바뀌지 않았다(리본 차선 x59~82 z5~10, SB x1.0~162.6, EL·ER 기판·리드 차선, 제어 기판·바닥 구멍·보스, 플러그 z10.7~18.3). BRD-02의 점선 턱은 실선으로: x161.5~164.3(x164.5가 아니라 이음 면에서 0.2 안) × y59.0~63.4 · y70.6~77.5, 밑면 z13.6. SCH-03 주 9의 ‘다시 눌리는 시각 상한’ = note-on부터 500 ms.

**회로 v10 뒤 (2026-09-29).** 회로 세션이 BRD-02에 턱을 그리면서 SB 만능기판 오른끝을 x162.9 → **x162.6**(으)로 0.3 줄였다. 손으로 자른 기판은 ±0.3이 나므로, 바를 턱 밑으로 밀 때 기둥(x163.0)에 걸리지 않게 하려는 것이다. 기판 끝 ↔ 턱 기둥 0.1 → 0.4, B 센서 리드 패드(x160.65)와는 1 mm 넘게 남는다. 센서 바는 x162.9 그대로다. 모델 `sb_board`만 바꿨고 run_all을 다시 돌렸다: 판정 45개 통과, 바뀐 값은 SB 기판 끝과 이 틈뿐.

### 1d-3. USB-C 케이블 — 한계 안에 드는 실제 선 (r4.4, 남은 문제 4)

**한계(동결, 회로 세션 소유)**: C 쪽 몰드 폭 ≤ 12.5, 두께 ≤ 7.6, 부트를 포함한 길이 ≤ 25. 곧은 플러그, 데이터선이어야 한다. 플러그는 z10.7~18.3, 면 y196.8(몰드 y196.8~221.8)에 놓인다. 플러그는 선반 홈 가장자리와 1.30 떨어져 있다. 이 한계는 바꾸지 않았다.

**무엇을 잇나**: 선 목록 `hardware/pcb/netlist/cables.csv`. 모듈 O1~O7의 RP2040-Zero에서 USB 허브(NEXTU 710U3, 다운스트림이 USB-A)까지 USB-A(수) → USB-C(수) 1 m 선 7가닥(W201~W207), 페달 보드에 같은 선 1가닥(W208). 모두 8가닥이고 USB 2.0이다. 허브 쪽이 USB-A라 C-C 선은 못 쓴다. 몰드 한계가 걸리는 것은 모듈 7가닥이다. 끝 부속 EL·ER에는 USB가 없다.

**지금 구매 목록 줄(v4 22번 줄, C04)**: Coms NA993 USB-A → C 1 m, 1,620원 × 8 = 12,960원(엘레파츠). 판매 페이지와 제조사 상세 이미지에 C 쪽 몰드 치수가 없다. 사진으로 재면 폭 약 11.3, 길이 약 19.5지만 두께를 알 수 없다. 그래서 ‘확인 안 됨’이다(목록 메모의 ‘≤ 12.5 × 7.5 × 25’도 확인된 값이 아니다).

| 후보 | 판매처 | C 몰드 폭 × 두께 × 길이 | 치수 출처 | 판정 | 8개 (배송 포함) |
|---|---|---|---|---|---|
| CVILUX DH-20M50052 | DigiKey Korea | 11.97 × 6.42 × 20.93 | DigiKey TechForum 'Overmold size of the USB-C male end' | **맞음 (권장)** | 40,744 |
| NETmate NM-GCM01BN | 엘레파츠 | 11.5 × 6 × 약 32 | 제품 상세 이미지의 '제품 사이즈' 도면 (길이는 축척 추정) | 맞지 않음: 길이 > 25(추정값) | 23,040 |
| Same Sky (구 CUI Devices) CBL-UA-UC-10BP | DigiKey Korea | 12.2 × 6.4 × 31 | 제조사 데이터시트 CBL-UA-UC 시리즈 | 맞지 않음: 길이 > 25(부트 포함) | 93,336 |
| CNC Tech 105-1028-BL-00100 | DigiKey Korea | 10.7 × 6.3 × 20 | 제조사 도면 105-1028-BL-00XXX | 못 씀: 충전 전용(데이터선 없음) | 71,392 |
| NETmate NM-UAC201BA | 엘레파츠 | 꺾임 몸체 32 × (두께 미공개) × 15 | 제품 상세 이미지의 '제품 사이즈 & 핀맵' 도면 | 못 씀: 꺾임 몸체가 프레임 안에서 꺾일 자리 없음 | 41,040 |

**권장**: C04 줄을 **CVILUX DH-20M50052** 8개로 바꾼다(DigiKey Korea 2987-DH-20M50052-ND, USB 2.0 A(수) → C(수) 곧은 플러그, 1 m, 차폐). 몰드 치수(11.97 × 6.42 × 20.93)는 DigiKey TechForum ‘Overmold size of the USB-C male end’에 지원 담당이 캘리퍼로 잰 사진 4장으로 확인된다. 제조사 도면에는 금속 쉘 6.65, 케이블 Ø3.5, 데이터 꼬임쌍만 있다. 몰드가 플러그 가운데라고 보면 선반 홈 가장자리 틈이 1.30에서 약 1.57로, 건반 꼬리·쉼 펠트와 플러그 윗면의 틈이 1.38에서 약 1.97로 는다. 길이는 25보다 4 짧다. 값: 1개 2,593원 × 8 + 배송 20,000원 = 40,744원(지금 NA993보다 +27,784원). 10개면 22,009원 + 배송으로 예비 2개가 생긴다. 디지키에서 6만 원 넘게 함께 사면 배송비가 없다. 인터페이스는 바꾸지 않는다.

**확인과 대안**: (1) 받으면 캘리퍼로 C 쪽 몰드를 잰다. 폭(로고 돌기 포함 최댓값) ≤ 12.5, 두께 ≤ 7.6, 부트 포함 길이 ≤ 25, 몰드가 금속 쉘 가운데(좌우·위아래 차이 ≤ 0.6)여야 한다. 데이터선인지는 RP2040-Zero의 BOOTSEL을 누른 채 PC에 꽂아 RPI-RP2 드라이브가 뜨는지로 본다. (2) 단계 0 키트의 C13a 몰드 게이지(12.5 × 7.6 창, 길이 25)에 끝까지 들어가야 한다. 최종 확인은 17장 시험 19다. (3) 몰드를 칼이나 줄로 깎지 않는다(차폐와 스트레인 릴리프가 드러나 끊긴다). (4) 확인된 선을 못 구하면 인터페이스 완화를 회로 세션에 요청한다: 길이만 ‘딱딱한 몰드 ≤ 25, 부트 포함 ≤ 35’(뒷벽 밖은 열린 통로). 그러면 NETmate NM-GCM01BN(8개 23,040원, 엘레파츠 합배송)이 가장 싸다. 폭·두께는 늘리지 않는다(선반 홈을 넓히면 F·F# 쉼 펠트 착지가 줄어든다). 알리익스프레스는 몰드 치수를 공개한 판매 페이지를 찾지 못했다. 자료: `../cable/result.json`, `../cable/img/`.

## 1e. r4.3 → r4.4 남은 문제 해결

남은 문제 7건 가운데 형상 1~3은 이 장에서 다룬다. 4(USB-C 케이블)는 1d-3장, 5(RP2040-Zero 높이 한계)는 18장, 6(문서)은 5장 머리(반올림)·13·15장(부품표와 맞춤)·10.1장(출력 공구), 7(시험 가정)은 17.1장(단계 0 키트)이다.

r4.3의 남은 문제(`report_r4/open_issues.r4_3.json`) 중 형상 3건. 다시 돌린 범위: 한 모듈(옥타브 모듈은 모두 같다; 대표 백 D·흑 C#, 착지 문제는 F·F# 자기 건반), 바뀐 캐리어·봉 마개가 닿는 끝 부속 A0·C8; PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45 / 1 / 2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악; 모든 계산은 `run_all.py` 한 번(스윕 모듈 1444쌍, 끝 부속 527 / 310쌍). 부품은 늘리지 않았다. 고침 1회차에서 제어 기판 인터페이스는 하나도 바뀌지 않았다(회로 세션 대조로 바뀐 값은 1d-2장): USB-C 플러그 12.5 × 7.6 × 25 (z10.7~18.3), 선반 홈 x76.45~91.55(플러그와 1.30), 제로 윗면 부품 z16.3 이하·y194.5~195.5 띠 z16.7 이하, 선반 밑면 z18.05, 뒷벽 개구 z5~21, 금지 구역 x81.22~85.42 × y173.2까지.

### 문제 1 — 레버 윗 스냅 립이 패드 옆으로 들어감 (+ 립·핀 보스 구멍·봉 마개를 geometry·스윕에)

다시 잰 값: r4.3 윗 립(0.8×1.0, 레버 좌표 y150~168·184~186, 강철 윗면 위 x ±3.7~4.5)을 이 모델에 넣고 자기 패드(x ±3.0, 월드 y170~182)와 모든 자세로 쟀다. x 틈은 0.70인데 레버 요(±0.10, 캐리어 앞에서)를 빼면 0.64이고, 레버가 1 N 바닥(10.75°)만 가도 앞 립 뒤끝 모서리(y168 z53)가 월드 y172.26 z59.23 — 패드 y 구간 안 — 로 올라와 y·z로 겹친다: 최소 0.64(공차 뒤 0.34, 규칙 1.0). 강체 바닥·ff에서도 같다. 뒤 립(y184~186)은 패드와 3.2 이상.

| 항목 | r4.3 | r4.4 |
|---|---|---|
| 앞 윗 립 (레버 좌표) | y150~168 (y150~153은 전폭 뚜껑) | y150~163 (같은 뚜껑) — 5.0 짧게 |
| 뒤 윗 립 | y184~186 (길이 2) | y184~190 (길이 6, 뒷벽까지) |
| 옆벽 윗단 z53 | y150~168, y184~186 | 립과 같은 구간만 (그 사이 z52) |
| 립 ↔ 자기 패드 (모든 자세) | 0.64 (공차 뒤 0.34) — 바닥 자세, 레버 A | 2.16 (공차 뒤 1.86) |
| 립 ↔ 패드 바·레일 | 검사 안 됨 | 1.81 (공차 뒤 1.51) |
| 립이 geometry.json·스윕에 | 없음 (옆벽 윤곽 안, 글에만) | 레버 부품 `carrier top snap lip L/R y…` — 모든 자세(쉼·1 N 바닥·강체 바닥·ff·복귀 넘침·서비스); 스윕 최소 1.81 (레버 D [캐리어 윗 스냅 립 R y150-163 ff] ↔ 패드 바 레일) |
| 핀 보스 구멍·레버 봉·봉 마개 | 글만 (‘Ø3.9 → Ø4.0 드릴’, ‘마개 1.2’, ‘막힌 벽 1.2’) | 고정 부품 `fin boss bore D4.0`(핀 5장, 오른쪽 끝 핀은 x163.1까지 막힘), `lever rod D4` x1.5~162.9, `lever rod end plug` x0.2~1.4(끝 핀 면과 같게), 평면도 포함; 끝 부속은 이음 쪽 핀에 마개; 축 놀음 0.10 + 0.20(봉 ±0.2면 0.10~0.50); 스윕에서 가장 가까운 움직이는 부품 1.77 |
| 모듈 스윕 최소 (공차 뒤) | 1.31 (1.01) — 립 빠짐 | 1.31 (1.01), 1444쌍 중 1.3 미만 0 |

레버 질량 모델은 r4.3까지 윗 립을 y150~186 전체로(끊긴 구간까지) 세고 옆벽 윗단도 전 구간 z53으로 셌다. 고치니 레버가 57.21 → 57.13 g으로 가벼워졌고(고침 2의 옆벽 낮춤까지 넣은 지금 값 56.95 g), ff 최대각이 12.88° → 12.91°로 커지고, 칸 가장자리 레버 옆벽 ↔ 패드 바 레일 웹 앞 아래 모서리(y160 z64.75)가 1.32 → 1.30이 되었다. 그 모서리를 1.0×45° 모따기해(패드 바는 그 위 z65.75 위로만 지나감) 1.54(공차 뒤 1.24). 가벼워진 레버의 여파로 DW 목표에 맞춘 캡스턴 y가 백 188.31 → 188.34, 흑 180.28 → 180.31, 1 N 정착 바닥에 맞춘 패드 면·출력 쐐기가 0.038 이하로 바뀌었다(고침 2의 선반 +0.05 포함; 1b장 ‘solved values’ 두 행).

**강철 블록 유지 (숫자로).** 강철은 밑에서 끼워 아래 립을 넘기고(스냅), 위로는 앞 뚜껑(y150~153, 전폭 9 × 1.0) + 윗 립, 앞뒤는 앞벽·뒷벽, 옆은 옆벽이 막는다 — 아래 립 쪽 말고는 기하로 갇혀 있다. 힘은 4-DOF 동역학의 매 스텝에서 강철을 떼어 놓고 구했다: 캡스턴 펠트와 패드는 강철에 바로 닿으므로, 레버의 각가속도로 강철이 따라가는 데 필요한 힘·모멘트를 캐리어가 준다. 이것을 세 구역(윗 앞 = 뚜껑 + 앞 립, 윗 뒤 = 뒤 립, 아래 = 아래 립; 각 면적 중심 y154.1 / 187.0 / 170.75)으로 나눴다. 립 뿌리 굽힘은 층간(캐리어는 옆벽을 베드에 눕혀 출력): σ = 3 F a / (L t²), a = 물림 폭의 절반(고른 접촉, 상한). 한계: 매 음 5 MPa, 화음·ABUSE 15 MPa.

| 구역 | r4.3 립: 최대 힘 → 뿌리 응력 (PLAY / 화음 / ABUSE) | r4.4 립 | 판정 |
|---|---|---|---|
| 윗 앞 (뚜껑 + 앞 립 15 → 10) | 33.3 / 28.0 / 49.3 N → 립만 2.7 / 2.2 / 3.9 MPa | 29.5 / 24.8 / 43.7 N → 립만 3.5 / 3.0 / 5.2 MPa (뚜껑 몫을 빼지 않은 상한) | 통과 |
| 윗 뒤 (뒤 립 2 → 6) | 21.9 / 24.9 / 22.4 N → **13.1** / 14.9 / 13.5 MPa (매 음 5 초과) | 19.2 / 21.8 / 19.7 N → 3.8 / 4.4 / 3.9 MPa | 통과 (r4.3은 매 음 초과였음) |
| 아래 립 (1.0×1.0, 길이 11.5, 바꾸지 않음) | 55.7 / 48.1 / 83.7 N | 51.9 / 44.9 / 78.1 N → **6.8** / 5.9 / 10.2 MPa (뿌리 쪽 접촉이면 4.7 / 4.1 / 7.1) | ABUSE 통과, 매 음은 상한 6.8가 5를 넘음 → 18장·단계 0 시험 20 |

- 가장 큰 경우: 윗 앞 흑 한 건반 공칭 2.5 m/s 뗌, 윗 뒤 백 한 건반 합격선 1.0 m/s 뗌, 아래 백 한 건반 공칭 2.5 m/s 뗌. 윗 뒤 립 힘은 캡스턴이 강철 뒤끝(y188)을 밀어 올리고 봉이 허브를 당겨 내리는 짝힘이라 캡스턴이 미는 매 음 생긴다 — r4.3의 2 mm 립은 이 힘에 층간 13.1 MPa였다(검사하지 않았음). 아래 립 힘은 패드가 강철 윗면을 누를 때 봉 반력이 캐리어를 통해 강철을 받치는 힘이다.
- 취급·운반: 강철 0.53 N. 15 MPa(드문 하중)에 닿는 충격은 위로(모듈 뒤집힘) 뒤 립 295 g, 앞 립 459 g(뚜껑 빼고), 아래로 218 g. 뒤집어 둔 상태(1 g)면 뒤 립에 0.25 N.

### 문제 2 — F·F# 쉼 펠트 부분 착지 (복귀 넘침 자세 스윕, 약한 6건반 화음 자리 492 N/mm 동역학)

다시 잰 값: F·F#를 자기 건반 몸체·자기 착지 비율(쉼 펠트 접촉 강성 × 착지 폭 / 8.0, r4.3의 방법)로 화음 자리(492 N/mm)에서 PLAY 격자, ABUSE 2.5 m/s(요청대로 화음 자리, 그리고 한 건반 자리 1490), ABUSE 2.0 m/s 화음(505), 뗌(마찰 1·2배)을 공칭·합격선·최악 재료로 돌렸다. 동역학 목표는 r4.3 펠트로도 통과했지만, 무른 착지 때문에 복귀 때 꼬리가 더 깊이 내려가고 레버가 더 내려간다. 그 복귀 넘침 자세(공칭 + 합격선; r4.3처럼 PLAY + ABUSE 한 건반에 화음 자리 PLAY를 더함, 레버 여유 0.25°는 전과 같음)로 모듈을 스윕하니 **4쌍이 1.3 미만**: 건반 F# 쉼 펠트 ↔ USB-C 플러그 (z10.7-18.3) 1.14; 건반 F 쉼 펠트 ↔ USB-C 플러그 (z10.7-18.3) 1.18; 건반 F# 뒷벽 ↔ 레버 F# 손톱 턱 1.26; 건반 F# 빔 ↔ 기판 부품(z20 이하) 1.28. ABUSE 6건반 화음(2.0 m/s)과 요청한 화음 자리 2.5 m/s의 복귀 넘침은 ABUSE 규칙(손상 없음 = 닿지 않음)으로 따로 쟀다.

고침(부품 추가 없음, 출력 부품 그대로, 회로 인터페이스 그대로): USB 홈에 걸리던 두 쉼 펠트를 **홈 가장자리에서 자르고 반대쪽으로 꼬리 끝까지** 붙인다 — F는 흰 꼬리가 빔과 같은 8.0이라 x71.69~76.45(착지 그대로 59 %, 홈 위로 나오던 3.24를 없앰), F#는 흑 꼬리가 10.0이라 x91.55~95.94까지 넓혀 착지 42 → 55 %. 탐색한 다른 안: F 얇은 꼬리에 쉼 발(2.5면 착지 91 %) — F를 앞으로 뽑을 때 발이 E 건반 꼬리 옆벽을 침(뽑기 경로 −4.99), 1.0 이하면 착지 이득이 작음; F# 발 2.0(80 %) — 굴림 되돌림/넘김 비 1.03.

| 항목 | r4.3 | r4.4 |
|---|---|---|
| F 쉼 펠트 / 선반에 앉는 폭 | x71.69~79.69 / x71.69~76.45 (59 %, 반력이 레버 선에서 -1.62) | x71.69~76.45 / 전부 (59 %, -1.62) |
| F# 쉼 펠트 / 선반에 앉는 폭 | x86.94~94.94 / x91.55~94.94 (42 %, 반력이 레버 선에서 +2.30) | x91.55~95.94 / 전부 (55 %, +2.80) |
| F 복귀 넘침 (건반 / 레버, 여유 포함) | -0.510° / -3.20° | -0.534° / -3.31° |
| F# 복귀 넘침 (건반 / 레버, 여유 포함) | -0.513° / -2.09° | -0.474° / -2.00° |
| 그 자세로 모듈 스윕 | 1.3 미만 4쌍, 최소 1.14 (공차 뒤 0.84) | 1.3 미만 0쌍; F·F# 복귀 넘침 쌍 최소 1.31 (공차 뒤 1.01, 건반 F# 블록 웹 ↔ 레버 F# 손톱 턱) |
| 화음 자리 PLAY 0.5~1.5 m/s, 공칭: 들림 / 키퍼 (F · F#) | 0.103 / 0.40 · 0.054 / 1.07 | 0.103 / 0.40 · 0.056 / 1.11 |
| 화음 자리 PLAY 0.5~1.5 m/s, 합격선: 들림 / 키퍼 (F · F#) | 0.130 / 0.37 · 0.075 / 1.08 | 0.130 / 0.37 · 0.074 / 1.12 |
| 화음 자리 PLAY 0.5~1.5 m/s, 최악(합격선 밖): 들림 / 키퍼 (F · F#) | 0.188 / 0.19 · 0.187 / 1.02 | 0.188 / 0.19 · 0.187 / 1.06 |
| 유령 (0.45~2 N 누름, 공칭·합격선·최악): 재무장 → 거름 | 재무장 4, 못 거른 것 0 | 재무장 4, 못 거른 것 0 (최대 100 %, 내려옴 ≤ 0.03 m/s) |
| 연타 / 끝까지 복귀 (화음 자리, 마찰 1배 · 2배, F · F#) | 16.3 · 15.3 Hz / 45.2 · 48.3 ms · 18.9 · 17.7 Hz / 39.8 · 42.3 ms | 16.3 · 15.3 Hz / 45.2 · 48.3 ms · 18.9 · 17.7 Hz / 39.8 · 42.3 ms |
| ABUSE 들림 최대 (모든 재료·경우, F · F#) | 0.243 · 0.353 | 0.243 · 0.353 (한계 0.40) |
| ABUSE 복귀 넘침 (2.0 m/s 6건반 화음, 요청한 화음 자리 2.5 m/s; 건반 / 레버, F · F#) → 스윕 | — | -0.607° / -3.48° · -0.460° / -2.05° → 최소 1.27, 공차 뒤 0.97 > 0: 닿지 않음 (ABUSE = 손상 없음; 건반 F 꼬리 윗판 ↔ 레버 F 캐리어 오른 옆벽) |
| 굴림 되돌림/넘김 비 (쉼, F · F#) | 3.95 · 1.77 | 3.93 · 1.42 (1 이상 = 굴지 않음) |
| 착지 짝힘 상한 → 가이드 탭 (F · F#) | 2.57 · 1.73 N | 2.57 · 2.06 N (탭 천이 받음) |
| USB 홈 옆 선반 응력 | 3.2 MPa | 3.2 MPa |
| 색별 복귀 넘침 자세 (건반 / 레버, 백 · 흑) | -0.414° / -2.85° · -0.324° / -1.81° (주 동역학만) | -0.460° / -3.05° · -0.351° / -1.82° (PLAY 화음 자리·격자, 합격선 재료 포함) |

### 문제 3 — 흑건(과 백건) 누른 자세 내보내기

다시 잰 값: r4.3 `poses_for`는 건반 ‘dip’를 max(1 N 정착 각, 강체 각)으로 잡아, 레버가 패드에 먼저 닿는 두 색 모두 **강체** 각을 내보냈다(백도 3.98°가 아니라 4.04°). 레버 ‘dip’는 이미 1 N 정착(패드 있음)이었다.

| 항목 | r4.3 | r4.4 |
|---|---|---|
| 건반 `side_dip` (백 / 흑) | 강체 4.04° / 6.22° (K 둘레 회전) | 1 N 정착(패드 있음)의 평면 상태 그대로: 3.98° / 5.99° 회전 + 노치가 봉에 앉음(K가 (-0.020, -0.154) / (-0.014, -0.143)) = 앞끝 기준 4.05° / 6.08°; 앞끝 z33.50 / z46.21 (강체 z33.50 / z46.00) |
| 건반 `side_dip_rigid` | 없음 | 강체 4.04° / 6.22° (새 필드; 끝 부속 건반도) |
| 레버 `side_dip` / `side_dip_rigid` | 정착 10.75° / 8.97°, 강체 12.64° / 10.27° | 같음 (끝 부속 레버에도 `side_dip_rigid`, 비틀림 스프링에도) |
| 스윕 자세 | 쉼·dip(강체)·ff·복귀 넘침 | 쉼·dip(정착)·dip_rigid·ff·복귀 넘침 (자기 건반·레버 짝은 같은 이름끼리) |
| 바꾼 곳 |  | `model_v4.poses_for`, `clearance_sweep`, `export_geo` (건반·끝 부속 건반·스프링), geometry `meta.note`, 치수 S24 |

### 고침 2 — r4.4 검증 지적과 해결 (다시 잰 값, 받아들임 / 기각)

검증 3렌즈(물리·기하·출력물)의 major 8건을 이 모델에서 먼저 다시 재고 고쳤다. 다시 돌린 범위: 한 모듈(대표 백 D·흑 C#, 착지·꼬리는 F·F#), 바뀐 칼라·보스·레일이 닿는 끝 부속; PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45 / 1 / 2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악 — `run_all.py` 한 번. 새 모델 함수: `carrier_wall_plate`(옆벽 판), `steel_bond`, `lever_float`, `with_bar_play`, `key_pose_shifts`, `rail_pockets`.

| 지적 | 요지 | 다시 잰 값 | 판정 | 고친 것 / 기각한 안 |
|---|---|---|---|---|
| 물리 1 | 아래 스냅 립이 매 음 한계(층간 5 MPa)를 넘는데 0.2장 행은 ‘통과’; 압연 평철 모서리 R0.5면 a 0.5 → 0.75라 6.7 → 10.1 MPa | 캐리어 → 강철 힘(아래 립) PLAY 51.9 / ABUSE 78.1 N; 고른 접촉 6.8 MPa, R0.5 모서리 10.2 MPa — 맞음. 더 나쁜 것: 립 하중이 0.8 옆벽 밖으로 치우쳐 옆벽 립 뿌리가 층 안 23.5 MPa(판 모델 최대 32.6; 한계 12) | 받아들임 | 강철 두 19×40 옆면을 2액형 에폭시로 옆벽에 접착(면적 1411 mm²): 전단 매 음 0.067, 화음 0.057, ABUSE 0.100 MPa(허용 0.50 / 1.00 = 에폭시 2.0 ÷ 4 / 2). 립은 굳는 동안만 잡는다. 0.2장 행을 접착 기준으로 바꾸고 스냅만의 숫자도 적음. 기각한 안: 아래 립 앞으로 y153까지(끼울 때 앞벽에서 3.8 떨어진 곳이 1.0 벌어져야 해 변형률 약 8 % — 부러짐), 1.2 두께(립 뿌리 4.7로 내려가도 옆벽 립 뿌리는 21.1), 판에서 자른 직각 강철(접착이면 필요 없음) |
| 물리 2 | 빠짐(스냅 풀림) 검사가 없음: 옆벽이 벌어지는 강성 약 5 N/mm, 비탈 11~27°면 빠짐; 운반 218 g는 굽힘만 | 옆벽 판 모델(0.5 격자, 앞·뒷벽 핀 / 고정, 앞 뚜껑이 윗단을 묶음, 강철이 안쪽을 막음): 립 선 벌어짐 PLAY 1.11~1.70, ABUSE 1.68~2.56, 1.5×ABUSE 2.52~3.84 (물림 1.0), 비탈 12~14° — 스냅만으로는 매 음에 빠질 수 있음 | 받아들임 | 위 접착(벌어짐 0). 충격 2009 g까지 접착이 드문 하중 한계 안. 단계 0 시험 20(C16a 생산 캐리어 3 + C16b 받침): 스냅만 빠짐 힘(모델 30 ~ 47 N), 접착 117 N 10 s × 3에 움직임 ≤ 0.05, 1 m 낙하. 기각한 안: 강철 밑 다리(바닥)로 두 옆벽 묶기 + 위에서 넣기(앞 뚜껑 y150~153·뒤 립 y184~190이 앞·뒷벽 바로 옆이라 0.8 벌릴 수 없고, 바닥이 있으면 밑으로도 못 넣음), 되물림 경사 립(평평한 강철 면은 립 끝 모서리에만 닿아 힘 방향이 그대로 수직) |
| 기하 1 | 흑 블록 앞 뺨 ↔ 밸런스 레일: 내보낸 1 N 바닥 1.27, 동역학 1.23~1.25 — 스윕은 K 둘레 회전만 | 노치가 봉에 앉음/파고듦(K에서, dz): 쉼 백 -0.081 / 흑 -0.077, 1 N 바닥 -0.154 / -0.143, ff(모든 동역학 최저) -0.250 / -0.215, 복귀 넘침 -0.105 / -0.137 — 맞음; 흑 립 구간 가장 낮은 점 z20.165(ff) | 받아들임 | 스윕과 내보내기가 같은 평면 상태(회전 + 노치 이동)를 쓴다(ff·복귀 넘침은 동역학 최저; 1 N 손가락 격자에서 ff 노치가 더 파고들어 백 블록도 1.3 아래로 감). 흑건 블록 밑 레일을 y137.2 뒤로 z18.80까지 포켓(검증자 제안 y137.4면 포켓 앞 모서리 ↔ 블록 모서리 1.29라 y137.2), 백건은 y137.4 뒤 z18.90; 핀 줄은 z19.0 그대로 → 블록 ↔ 레일 1.31. T3 뒤 발을 y137.1에서 끝냄. 여파: 노치 이동을 넣으니 F·F# 꼬리 ↔ 제어 기판 부품 구역(z20, 회로 인터페이스)이 복귀 넘침에서 1.24~1.25 → F·F# 빔·얇은 꼬리 밑면 y176~195.8을 0.2 올림(꼬리 응력 ×1.104) |
| 기하 2 | 레버 축 놀음(칸마다 0.50)이 스윕에 없음: 옆벽 ↔ 패드 1.01(패드 바 ±0.3이면 0.71), A#\|B 칼라 합 1.40 → 1.20 | 한쪽 축 놀음 최대 0.405(칸 가장자리 레버); 고침 1 옆벽(윗단 = 강철 윗면)이면 옆벽 ↔ 자기 패드 0.73 — 맞음. 더 찾은 것: 보스 쪽으로 떠밀린 레버 ↔ 핀 1.30(요 포함, 딱 경계) | 받아들임 (고친 방법은 다름) | 스윕에 레버 한쪽 놀음(칼라·보스 사슬), 이웃 레버는 둘 사이 빈 틈만, 패드 바 무리(패드·쐐기·띠·잎·손잡이) ±0.3. 패드 구간 옆벽 윗단을 강철 윗면 −2.6로(옆벽이 패드 면 밑으로 지나감) → 1.44; 칼라 한 개 0.76 이상(짝 1.52; 검증자 0.75는 복귀 넘침에서 1.298) → 레버 ↔ 레버 1.32; 핀 보스 +0.02 → 칸 놀음 0.46 / 0.46 / 0.43 / 0.30. 기각한 안: 패드 폭 6.0 → 5.2 + 패드 바 놀음 0.1(패드 강성이 바뀌어 업스톱 동역학을 다시 해야 하고, 바 놀음 0.3은 빼기 절차의 틈) |
| 출력물 1 | T3 GO/NO-GO를 핀을 다 누른 뒤에 하면 다른 핀이 가운데 블록·반대쪽 NO-GO에 걸려 낮은 핀을 못 잡음 | 피치 13.05~14.61, 막대 52, 가운데 막음 \|u\| < 3, NO-GO 16~20 — 맞음 | 받아들임 | 누른 핀마다 바로(오른쪽 이웃 핀을 꽂기 전) +X로 옮겨 \|<GO로 확인, 프레임 한 장씩; 엄지·바이스로 누르고 망치 금지(80 N에서 멈춤 면 25~40 MPa) — tools.md·10.1장 |
| 출력물 2 | 단계 0 키트에 시험 20이 없음 | 순서·기록표·‘19개’ 글에 20 없음 — 맞음 | 받아들임 | 시험 20 = 강철 유지(C16a 생산 캐리어를 모델에서 그대로 3개, C16b 받침): 스냅만 빠짐 힘, 접착 117 N·1 m 낙하, 10^5회는 캠 필요(시험 10처럼); 순서 3번 다음, ‘20개’ |
| 출력물 3 | 남은 문제 5(공구)가 DESIGN·부품표에서 닫히지 않음(S08 ‘2.5 단’, D02, 부품표 3 × 15 g) | 문서 세션이 10.1·12장·조립 단계는 이미 고침; 남은 것은 S08·D02·A08·D11 글(`export_geo.py`)과 부품표 공구 행(`run_all.py`) — 맞음 | 받아들임 | S08·D02(1/8회전 = 바늘 0.34 / 0.22)·A08·D11 글을 고치고, 부품표 공구 행을 tools_geometry.json에서 4개 합계 68.2 g로 |
| 출력물 4 | 3a 굽힘 띠: 경간 60에서 판정이 다이얼 0.018 mm에 걸림(접촉 3곳 포함) | k 70.1 N/mm, 18 N에 0.257 mm, 합격선 0.275 — 맞음 | 받아들임 | 띠 120×12×5.5, 경간 100(k 15.4 N/mm, 18 N에 1.17 mm); 다이얼은 C03c 가운데 Ø4 구멍으로 띠 윗면에 직접(검증자 안의 ‘받침 밑 구멍’은 다이얼이 받침 밑에 서야 해 누름 코 구멍으로 바꿈); 기울기는 3번 평균 |

모든 틈(고침 2 스윕: 레버 축 놀음 + 패드 바 놀음 + 노치 이동): 모듈 1444쌍 중 1.3 미만 0, 최소 1.31(공차 뒤 1.01); 끝 부속 527 / 310쌍. 동역학·강도에 닿는 것은 레버 질량(옆벽 낮춤, 레버 56.95 g)과 F·F# 꼬리뿐이고 0.2장 목표는 모두 다시 판정했다.

### 고침 2b — r4.4 재검증 지적과 해결 (고침 2 뒤 다시 잰 값)

고침 2를 넣은 모델을 검증 3렌즈가 다시 재서 기하 critical 1 · major 1, 물리 major 2, 출력물 major 2를 냈다. 모두 이 모델에서 먼저 다시 쟀고 모두 맞아 받아들였다(기각한 지적 없음, 고치는 방법을 바꾼 것은 표에 적음). 다시 돌린 범위: 한 모듈(대표 백 D·흑 C#, 꼬리는 E·F·F#·G), 끝 부속 A0·C8(캐리어 옆벽이 닿음); PLAY 0.5 / 1.0 / 1.5 m/s × 뗌·0.45 / 1 / 2 N, ABUSE 2.5 m/s, 재료 공칭·합격선·최악 — `run_all.py` 한 번(1159 s). 새 모델 함수: `board_boss_rects`, `board_insert_check`, `bond_thermal`; 바뀐 함수: `plate_fe`(킬), `fixed_prisms`·`fin_poly`(바닥 구멍·킬·매단 보스), `board_prisms`(부품 구역을 보스 둘레 1.3 비움), `lever_body`·`lever_prisms`(옆벽 0.7·립 0.9·접착막), `circuit_c44_checks`. 고치기 전 보관 `geometry.r4_4b.json`, `work_f2b/*.pre_f2b.*`, 패치 `work_f2b/patch_*_f2b.py`.

| 지적 | 요지 | 다시 잰 값 | 판정 | 고친 것 / 기각한 안 |
|---|---|---|---|---|
| 기하 critical | 제어 기판을 한 덩어리 프레임에 넣을 길이 없음: F\|F# 핀 발(x82.52~84.12, y152~170.7)이 바닥~윗판, 기판 홈은 앞이 열림(x81.92~84.72, y145.5~172), 홈 뒤 기판 띠 위에 핀이 z21.5부터 매달림, 윗판이 덮음, 기판 뒤 여유 1.3 | 맞음: 핀 발이 홈에 들어가려면 기판이 25.2 뒤에서 앞으로 와야 하는데 뒤는 선반 리브 앞면까지 1.3; 옆모습(x = 핀 두께)에서 홈 뒤 띠의 자리(y170.7~196.8 × z5~21.5)는 핀 발·매단 핀·리브·바닥으로 사방이 막혀 있고, 기판을 옆으로 밀면 홈 옆이 핀 발에 걸림. 10장 조립 순서에 기판 단계가 없었음 | 받아들임 | 바닥을 기판 밑에서 뚫음(x46.25~118.25 y144.5~196.5, 리셉터클 뒤 x78.53~89.47는 y197.8까지): 모듈을 뒤집어 기판을 곧게 넣고(홈이 핀 발·킬을 따라감) 매단 보스 4개(D6, 같은 구멍 자리; 앞 2 = 밸런스 레일 뒷면에서 받침, 윗면 z17.0; 뒤 2 = 리브 x50·x116 앞면과 선반 밑면 z18.05)에 닿으면 M3×6 2개를 밑에서(머리는 기판 밑), 위치 핀 2개는 보스에서 기판 구멍으로 아래로. 핀 발은 킬(y144.5~152, z3~19)로 레일에 붙음. 넣는 길 검사 `board_insert_check`: 기판·BRD-01 부품을 밑에서 곧게 올릴 때 길 위 프레임 최소 0.60(fin), 바닥 구멍 1.0, 레일 1.0, 멈춤 = 보스 4개(기판 윗면 z10.6 닿음), 핀 반경 놀음 0.10. 부품 추가 없음. 기각한 안: 바닥 쟁반(검증자 권장 (a), 출력 +1/모듈이고 핀 발의 위로 당김을 쟁반이 받아야 함), 홈을 뒤로 열기(b, 제로·리셉터클을 핀 선 밖으로 = 회로 인터페이스 변경), 핀 발을 따로(c, +1/모듈), 출력을 멈추고 기판을 넣기(기판을 다시 뺄 수 없음) |
| 물리 major 1 | 접착(에폭시)이 PETG(60e-6/K)·강철(11.7e-6/K) 열팽창 차이를 받지 못함 — 5분 에폭시 G 700, 접착층 0.1이면 가장자리 전단 ΔT 10/20/30 K에 1.6/3.2/4.9 MPa; 시험 20은 실온만 | 맞음(전단 지연, 40 mm ≫ 지연 길이): 5분 에폭시 ΔT 15 K 접착층 0.10 / 0.05 → 2.24 / 3.17 MPa, ΔT 30 K → 4.48 / 6.33 MPa (설계 강도 2.0). 스냅만으로는 못 버티므로(고침 2) 접착이 떨어지면 강철이 빠짐 | 받아들임 | MS 폴리머(하이브리드) 탄성 접착제(G 약 1 MPa, 설계 겹침 전단 1.5 MPa — 단계 0 시험 20): 열 전단 ΔT 15 / 30 K, 접착층 0.10 → 0.085 / 0.169, 가장 얇은 0.02 → 0.189 / 0.379 MPa. `steel_bond` 판정에 열 항을 더함: 매 음 하중 0.067 + 열(ΔT 15, 0.02) 0.189 = 0.256 ≤ 0.375, ABUSE 0.100 + 열(ΔT 30) 0.379 = 0.478 ≤ 0.750 MPa. 패드 봉우리에서 강철 미끄럼 0.0016 mm. 시험 20에 5 ↔ 45 °C 3번(냉장고·따뜻한 물)을 넣음. 기각한 안: 강화(유연) 에폭시 G ≤ 50 MPa(구하기·표시값 확인이 어려움; MS 폴리머는 철물점 실란트) |
| 물리 major 2 | 접착층이 없음: 주머니 10.6 − 2 × 0.8 = 9.0 = 강철이라 에폭시가 들어갈 틈이 없고, 10장 3단계에는 접착이 없으며 부품표·16장은 ‘끼운 뒤 접착’(시험 20만 먼저 바름) | 맞음: geometry 옆벽 x28.735~29.535 / 38.535~39.335, 강철 x29.535~38.535. 접착막이 옆벽을 밀면 레버 폭이 늘어 레버 ↔ 레버 1.32가 줄어듦 | 받아들임 | 옆벽 0.8 → 0.7(주머니 9.2 = 강철 9.0 + 접착층 0.10 × 2; 레버 겉폭 10.6 그대로), 윗 립 0.8 → 0.9(안쪽 모서리 x ±3.7 그대로 = 패드와 틈 그대로), 아래 립 안쪽 x ±3.5 그대로; 강철 두께 8.9~9.1만(캘리퍼스). 순서는 시험 20과 같게: 사포·알코올 → 강철 두 면에 얇게 바름 → 밑에서 스냅 → 나온 것 닦음 → 24 h(10장 4단계 — r4.5 고침: 기판 단계가 1단계로 들어가 번호가 밀림, 부품표, 16장). 레버 57.02 → 57.05 g(옆벽 −, 접착막 +; r4.5 56.97, r4.5 고침 56.95). 기각한 안: 레버 폭 10.8(옆벽 0.8 유지) — 레버 ↔ 레버 1.32가 1.12로 |
| 기하 major | 스윕 자세가 공칭(+합격선) 재료뿐: 최악 재료 PLAY 1.5 m/s 뗌에서 백 건반 −0.458°(자세 −0.414), E·G 얇은 꼬리 ↔ 기판 부품 구역 1.279(공차 뒤 0.979), F 자기 최악 −0.533°에서 빔 ↔ 4067 1.295 | 맞음(재현: 고침 2 모델에 최악 자세를 넣은 스윕): E·G 얇은 꼬리 ↔ 부품 구역 1.27, E ↔ 4067 1.28, F 빔 ↔ 부품 구역·4067 1.30 — 1.3 미만 5쌍. 흑은 최악이 더 얕음(흑 -0.351° / 레버 -1.82°) | 받아들임 | 스윕 ‘over’·‘ff’ 자세에 최악 재료의 PLAY 격자·화음 스윕(F·F#는 자기 착지의 최악 PLAY)을 더함: 백 건반 -0.415 → -0.460°, 레버 -2.85 → -3.05°; F -0.510 / -3.20 → -0.534 / -3.31°. E·G 빔·얇은 꼬리 밑면 y184~195.8 0.1, F는 y176~195.8 0.15 올림(회로 인터페이스 z20 그대로; 꼬리 응력 ×1.068 / ×1.104). 결과: 모듈 1444쌍 중 1.3 미만 0, 최소 1.31(공차 뒤 1.01); 건반 ↔ 기판 부품 최소 1.31 (key F# beam ↔ board components) |
| 출력물 major 1 | 캡스턴 벤치 게이지(T2)가 꼭대기를 z31.0(건반 좌표)으로 맞춤 — 지그 위 건반도 노치 천에 가라앉아 모델의 정착 쉼 꼭대기는 30.892 / 30.912: 캡스턴이 0.108 / 0.088 높게(1/8회전 1.73 / 1.41번), 업스톱 틈 −0.40 → 약 −0.73 | 맞음: 정착 쉼(4-DOF, 레버가 캡스턴에) 꼭대기 백 30.892 · 흑 30.912 (건반 좌표 z31.0보다 0.108 / 0.088 낮음 = 1/8회전 1.73 / 1.41번) | 받아들임 (고친 방법은 다름) | 가짜 레버 밑면과 지그 영점 받침(교정봉 윗면)을 정착 쉼 꼭대기 한 면 z30.90로(백 +0.008, 흑 -0.012 = 1/8회전의 0.13 / 0.19); 바늘 ↔ 읽기 턱 ‘같은 높이’ 규칙과 교정은 그대로. `make_tools.py`가 모델 쉼 상태로 계산, 지그 틈 검사도 정착한 건반으로. S08 글 고침. 기각한 안: 읽기 턱 3단(0 · W · B, 검증자 안) — 한 면이면 같은 높이 규칙 하나로 백·흑을 다 읽고 교정봉이 그 면을 바로 확인함 |
| 출력물 major 2 | 12장 종이 띠 규칙의 심 방향이 반대: ‘먼저 물리면 심을 빼고, 늦게 물리면 넣는다’ — 심 한 장은 패드 면 0.1 아래 = 레버가 먼저 닿음 = 틈이 더 음수 = 띠가 더 큰 힘에서 물림 | 맞음: 모델 띠 물림 힘 백 틈 −0.30 / −0.40 / −0.50 → 0.75 / 0.92 / 1.05 N (틈이 음수일수록 큰 힘); 단계 0 키트(시험 T·1)는 이미 맞는 방향 | 받아들임 | 12장: 먼저(작은 힘에) 물리면 심을 넣고, 늦게 물리면 심을 뺀다; 뺄 심이 없으면 그 칸 패드 바를 쐐기 0.1 얇게 다시 출력 — r4.5 고침: 쐐기 얇은 끝이 0.40 미만인 자리(백 0.347, 끝 부속 A0·B0·C8)는 쐐기를 그대로 두고 그 패드 자리의 바 밑면을 0.1 올려(바 1.5 → 1.4) 다시 출력하거나 패드 펠트를 0.1 얇은 것으로. 기각한 안: 모든 패드 밑에 기본 심 1장 + 쐐기 0.1 얇게 — 가장 얇은 백 쐐기 0.35가 출력 최소 0.3 아래로 |

**킬과 기판 받침의 숫자.** 윗판 FE(킬 뿌리 = 레일 + 바닥 띠를 핀 선 사이 보로 — r4.5 고침; 고침 2b는 레일에 고정, 핀 발은 z3까지 깊은 보): 6건반 화음 자리 PLAY 492 N/mm(고침 2 바닥 가정 492), ABUSE 화음 505; 한 건반 자리 F 1873 · F# 1891 N/mm(고침 2 1932 · 1950), 가장 무른 자리 1490(동역학 값 그대로). 킬 굽힘(층 안) 한 건반 PLAY 3.35, 6건반 PLAY 13.02, ABUSE 화음 17.68 MPa, 전단 1.60 / 6.25 / 8.48 MPa(층간 기준 5 / 15 안). 핀 윗단 이음 인장 PLAY 화음 4.22 MPa(고침 2 9.51). 바닥 구멍 때문에 프레임이 7.8 g 가벼워짐(보스·킬 포함). 보스 ↔ 가장 가까운 BRD-01 부품 1.93, M3 머리 ↔ 레일 1.65 · 리브 1.54(리브 축 1.45), 나사 = 기판 1.6 + 보스 4.4(끝 z15.0, 구멍 끝 z15.4), 위치 핀 끝 z7.8. r4.5 고침: 고침 2b의 ‘레일 자체의 휨은 모델에 없다 — 단계 0 시험의 화음 자리 합격선 460 N/mm로 본다’는 틀렸다(시험 3은 띠의 E만 잼) — 레일 휨은 이제 모델에 있고(1f-2장) 첫 모듈 정하중(조립 시험 21)으로 잰다.

## 1f. r4.4 → r4.5 비틀림 스프링 기성품(미스미)

> 이 장은 r4.5 기록 그대로다. r4.5 고침에서 짧은 다리를 8.0 mm로 길게 잘라 가둠 홈에 넣었다(1f-2장). 지금 두 다리는 22.3 / 8.0 mm로 자른다. 이 장의 ‘짧은 다리 2.5’는 r4.5 값이다.

**왜.** 사용자가 2026-09-28 다른 세션에서 D05(주문 제작 추정 100 × 200원)를 한국미스미 경제형 토션스프링 **C-UA90R5-3-0.5**로 바꾸기로 했다(9/28 확인: 1~99개 332원, 100개 이상 282원 + VAT, 재고 있음, 다음 날 출하). 그 세션이 r4.4 모델을 읽기만 해서 바꿀 값을 계산해 보냈다(요청서 `work_r45/requester/W1_REQUEST.md`와 스크립트·결과). 이 판은 그 값을 따로 다시 유도해 모델에 넣고 run_all 전체를 다시 돌렸다. 90°형을 고른 까닭(요청서): 세 암 각 가운데 강성이 가장 낮고 최대 사용각이 55°로 가장 크다.

**스프링 값 다시 유도.** 카탈로그 k(다리 25/25로 잰 값) 0.1368 / 0.1409 / 0.1454 N·mm/°(암 90 / 135 / 180°)를 몸통 권수 n = 3 + (180 − 암 각)/360으로 풀면 E가 186,048 / 185,941 / 186,014 MPa로 한 값이 된다 → E 186000 MPa(JIS SUS304-WPB 186 GPa, 모델 SUS 일반값 193 GPa는 쓰지 않음). 다리를 긴 22.3(축에서 끝; 코일을 떠나는 점에서 22.13), 짧은 2.5로 자르면 N_e = 3.25 + (22.13 + 2.5)/(3π·5.5) = 3.725, k_t = E d⁴/(64 D N_e) = **8.866 N·mm/rad**(0.1547 /°; 몸통만이면 10.16; 카탈로그 다리 25/25로 같은 식이면 0.1368 /° = 카탈로그 값). b = 0 토크 4.189 N·mm(D05 8 × 30°)를 지키는 자유각은 **-27.07°**. 응력은 굽힘 보정 K_i = (4C² − C − 1)/(4C(C − 1)) = 1.073(C = 11)로:

| 상태 | 레버 각 b | 감긴 각 (r4.4 → r4.5) | 토크 N·mm (r4.4 → r4.5) | 응력 MPa (r4.4 → r4.5) | Su 2150의 % |
|---|---|---|---|---|---|
| 쉼 | 0.02° | 30.0 → 27.1° | 4.19 → 4.19 | 369 → 366 | 17 |
| 바닥(강체) | 12.64° | 42.6 → 39.7° | 5.95 → 6.14 | 524 → 537 | 25 |
| 서비스 16° | 16.00° | 46.0 → 43.1° | 6.42 → 6.66 | 566 → 583 | 27 |
| 손 들기 25° | 25.00° | 55.0 → 52.1° | 7.68 → 8.06 | 676 → 704 | 33 |

카탈로그 최대 사용각 55°(그때 카탈로그 토크 7.52 N·mm, 658 MPa). 손 들기 25°에서 감긴 각 52.1°는 그 안이지만, 다리를 짧게 잘라 강성이 13 % 커서 토크 8.06 N·mm는 카탈로그 55° 토크의 **107 %**다(18장 위험, 단계 0 시험 8). 코일 바깥지름 자유 6.0(주머니 Ø6.6와 반지름 0.30), 안지름은 바닥에서 4.84, 손 들기에서 4.79(봉 Ø4와 반지름 0.39). 코일 길이 (n + 1)d = 2.13(주머니 폭 3.0). 자른 스프링 하나 0.126 g(선 80.8 mm; r4.4 가정 0.15 g).

**파라미터 (모델 `P`) — r4.4 → r4.5, 요청서 값과 대조.** 요청서 표는 r4.4 고침 1 모델을 읽고 만들었다. 고침 2·2b가 레버에서 바꾼 것(칼라, 옆벽 0.7, 핀 보스 +0.02, 레버 질량, 강철 접착)은 허브 주머니 구간(x ±1.5)·뒷벽 홈·스프링 식에 닿지 않아 **표의 값은 하나도 바꿀 필요가 없었다**. 새로 넣은 값(E·자유 감긴 각·홈 여유)은 모델이 k_t와 자유각을 스스로 계산하게 하려는 것이다.

| 파라미터 | r4.4 (D05) | r4.5 (미스미) | 요청서 | 판정 |
|---|---|---|---|---|
| spring_kt (N·mm/rad) | 8.0 | 8.866 (계산: E, n, D, d, 다리) | 8.866 | 같음 |
| spring_free_deg | -30.0 | -27.07 (계산: b = 0 토크 4.189) | -27.07 | 같음 |
| spring_ID / spring_n / spring_rm | 4.5 / 4.2 / 2.50 | 5.0 / 3.25 / 2.75 | 5.0 / 3.25 / 2.75 | 같음 |
| spring_pocket | Ø6.1 × 3.0 | Ø6.6 × 3.0 | Ø6.6 × 3.0 | 같음 |
| spring_slot | 35°, ±3.00 | 35°, ±3.25 | 35°, ±3.25 | 같음 |
| spring_groove (폭 × 깊이, 바닥 y) | 1.2 × 2.0, y209.8 | 2.4 × 3.2, y211.0 (뒷벽 1.0 남음) | 2.4 × 3.2, y211.0 | 같음 |
| spring_boss (폭) | 3.2 | 4.4 | 4.4 | 같음 |
| 짧은 다리 | 2.5, 5.7° 굽혀 슬롯 윗면에 | 2.5 곧게, 새 홈 (접점 230.36°) | 2.5 곧게, 접점 230.4° | 같음 |
| spring_E / spring_swept_free / spring_notch (새 값) | - | 186000 / 1170° / 안쪽 여유 0.8, 띠 시작 -0.5 | 186000 / 1170° / 0.8, −0.5 | 같음 (모델 입력으로 만듦) |

**짧은 다리 홈 (새 형상).** 카탈로그 스프링은 자유 상태에서 두 다리 사이가 1170°(3권 + 90°) 감겨 있다. 긴 다리는 r4.4 슬롯·뒷벽 홈을 그대로 쓰지만(레버 -31.3°~18.0°에서 슬롯 면까지 0.63 + 선 반지름 + 0.2), 짧은 다리는 긴 다리 접점(월드 -12.57°)에서 117.07°(설치 감긴 각 mod 360) 앞, 곧 레버 기준 **230.36°**에 온다: α_s = φQ − ((1170 − 자유각) mod 360), 굽힘 없음. r4.4의 짧은 다리 자리(슬롯 윗면 쪽 접점 125°)에서 105° 떨어져 슬롯으로 나올 수 없다. 짧은 다리는 접점 y201.50 z31.38에서 140.36° 방향으로 2.5 곧게 가 끝이 y199.57 z32.98(축에서 3.72)이다. 그래서 주머니 구간(x ±1.5, 허브 두께 방향 전체)에 띠 모양 홈을 판다: 축에서 230.36° 방향으로 잰 거리 1.70~3.00(바깥 면 = rm + d/2, 안쪽 면 = rm − d/2 − 0.8), 다리 방향으로 -0.5(주머니 안)부터 안쪽 면이 허브를 나가는 곳(3.95)까지. 홈은 허브 벽을 뚫고(바깥 면은 y198.96 z33.16, 안쪽 면은 y199.12 z34.71에서 나감) 웹 밑면(z33.5)을 주머니 폭만큼 1.21 깎는다. 스프링은 짧은 다리를 반시계로 밀어 **바깥 면**이 되돌림 토크를 받는다: 다리가 그 면에 1.13 얹히고(면은 주머니에서 허브 겉까지 1.71), 끝은 면 끝 0.58 안. 주머니 구간 단면은 이제 두 조각이다 — A(웹 쪽: 슬롯 윗면 ~ 홈 안쪽 면, 웹) · B(아래 고리: 홈 바깥 면 ~ 슬롯 아랫면, x ±1.5 밖의 온전한 허브에 층으로 붙음). 요청서 글의 ‘다리 방향 −0.5…2.8’은 넣기 검사의 띠다. 홈을 2.8에서 끝내면 바깥 면 모서리(축에서 4.10)에 허브 겉과 0.20 두께 껍질이 남아 출력이 안 되므로, 요청서가 적은 나가는 점(y198.96~199.12, z33.16~34.71)대로 허브 벽을 뚫었다.

**넣기.** 조립은 봉을 꿰기 전 벤치에서: 자유 상태의 스프링(코일 OD 6.0, 곧은 짧은 다리, 자유 방향 50.4°의 긴 다리)을 슬롯 축(35°)을 따라 밖에서 밀어 넣으면 짧은 다리가 주머니 가장자리를 지나 새 홈으로 미끄러져 들어가 바깥 면에 앉는다. 선 외곽(폭 d의 직사각형)과 두 조각 A·B를 0.02 mm 걸음으로 잰 최소 틈: 짧은 다리 ↔ A(안쪽 면·주머니 모서리) **0.53**(공차 −0.3 뒤 0.23), 코일 ↔ 슬롯 면 0.25, 앉은 뒤 바깥 면 0.00(설계 접촉) → 지나감. 안쪽 여유를 0.5로 하면 0.25(공차 뒤 -0.05), 0.3이면 0.04 — 요청서는 다리 중심선 점 판정(주머니 안이면 중심이 r ≤ 3.05)이라 0.5에서 ‘막힘’이었다; 선 외곽으로 재면 0.3 아래에서 막히지만, 공차를 넣으면 0.5는 모자라 요청서대로 **0.8**을 둔다. 스프링은 **긴 다리가 코일의 +x(오른쪽) 끝**에 오게 넣는다: 오른쪽 감기에서 (y, z) 평면으로 짧은 다리 → 긴 다리가 반시계일 때만 레버가 올라갈수록 감기는 방향이고, 뒤집어 넣으면 짧은 다리가 105° 쪽에 와서 홈에 맞지 않는다(잘못 넣을 수 없음).

**홈이 허브·웹에 주는 영향.** 캐리어는 옆으로 눕혀 뽑으므로(x가 쌓는 방향) (y, z) 면의 굽힘은 층 안, 주머니 구간 조각이 옆 허브에 붙는 힘은 층간이다. 홈이 웹 밑면을 깎는 자리의 세로 단면(y198.91, 레버 폭 10.6 가운데 3.0만 깎임): ABUSE 봉 반력 44.1 N + 손 들기 스프링 8.06 N·mm → 248 N·mm, 층 안 3.97 MPa(홈 모서리 Kt 2를 곱해 7.95; 홈이 없던 r4.4 단면은 3.41), 전단 1.02 MPa — 한계 25(드묾) / 12(매 음). PLAY(봉 27.1 N, 바닥 토크)는 4.93(Kt 곱). 조각 B는 짧은 다리 힘 3.22 N(손 들기)을 두 옆면(9.3 mm² × 2)의 층간 전단 0.173 MPa로 옆 허브에 넘긴다(한계 5). 봉은 주머니 구간(Ø6.6)에 닿지 않고 양옆 온전한 허브 3.8 × 2에만 기댄다: ABUSE 지압 1.45 MPa(r4.4까지 적은 1.04는 폭 10.6 전체로 나눈 값).

**질량.** r4.4 질량 모델은 주머니 원통만 빼고 슬롯은 빼지 않았다. 이제 주머니 구간에서 빠진 것 전체(주머니·슬롯·짧은 다리 홈·웹 깎음, 31.8 mm² × 3.0)를 그 중심에서 빼고, 스프링은 실제 0.126 g을 축에 둔다 → 레버 57.05 → **56.97 g**(캐리어 2.92 → 2.86 g). 프레임 질량에 스프링 보스·홈을 새로 넣었다(모듈 -0.17 g: 보스는 넓어지고 홈은 뒷벽 안으로 2.0 깊어짐).

**결과 (r4.4 → r4.5, 이 모델 전부 다시 돌림) 와 요청서 결과 (요청서 base → 미스미).** 요청서 base는 r4.4 고침 1 모델이라 r4.4 값과 조금 다르다; 변화량을 비교한다.

| 항목 | r4.4 | r4.5 | 변화 | 요청서 base → 미스미 |
|---|---|---|---|---|
| DW 백 (g) | 51.92 | 51.92 | +0.00 | 51.89 → 51.89 |
| UW 백 (g) | 42.78 | 42.78 | +0.00 | 42.76 → 42.76 |
| 행정 중 DW 최대 백 (g, ≤ 55) | 54.36 | 54.76 | +0.40 | 54.34 → 54.73 |
| 바닥 UW 백 (g) | 34.50 | 34.89 | +0.38 | 34.49 → 34.87 |
| 스프링 토크 바닥 백 (N·mm) | 5.95 | 6.14 | +0.19 | 5.95 → 6.14 |
| DW 흑 (g) | 51.01 | 51.01 | +0.00 | 50.99 → 50.99 |
| UW 흑 (g) | 40.80 | 40.80 | +0.00 | 40.78 → 40.78 |
| 행정 중 DW 최대 흑 (g, ≤ 55) | 51.17 | 51.27 | +0.10 | 51.14 → 51.25 |
| 바닥 UW 흑 (g) | 30.37 | 30.62 | +0.26 | 30.35 → 30.61 |
| 스프링 토크 바닥 흑 (N·mm) | 5.62 | 5.78 | +0.16 | 5.62 → 5.78 |
| 연타 백 (Hz) | 16.23 | 16.30 | +0.06 | 16.23 → 16.30 |
| 연타 흑 (Hz) | 18.82 | 18.88 | +0.06 | 18.82 → 18.87 |
| 연타 마찰 2배 백 (Hz, ≥ 13.3) | 15.19 | 15.26 | +0.07 | 15.19 → 15.26 |
| 연타 마찰 2배 흑 (Hz) | 17.64 | 17.71 | +0.06 | 17.64 → 17.70 |
| 끝까지 복귀 백 (ms) | 45.4 | 45.3 | -0.2 | 45.5 → 45.3 |
| 노치 들림 PLAY / ABUSE 최대 (mm) | 0.161 / 0.178 | 0.162 / 0.177 | +0.001 / -0.001 | 백 0.136 / 0.134 → 0.135 / 0.137 |
| 키퍼 틈 최소 (mm) | 0.517 | 0.513 | -0.004 | 0.370 → 0.360 |
| m_eff 백 / 흑 (g) | 55.23 / 46.54 | 55.23 / 46.54 | +0.00 / +0.00 | 55.21 → 55.21 (백) |
| 레버 (g) | 57.05 | 56.97 | -0.08 | 같음 (요청서는 질량을 안 바꿈) |
| 모듈 스윕 최소 (공차 뒤) | 1.31 (1.01) | 1.31 (1.01) | -0.00 | - |
| 모듈 무게 (kg) | 1.375 | 1.374 | -0.001 | - |
| 기본 구성 비용 변화 (원) | +43,400 | +69,400 | +26,000 | 31,000 (스프링 행) |

스프링이 11 % 단단해져 행정 뒤쪽 토크가 커지므로(바닥 5.95 → 6.14 N·mm) 행정 중 DW 최대와 바닥 UW가 조금 오르고 연타가 조금 빨라진다; 쉼 토크가 같아 DW·UW는 같다. 0장 판정 42개 가운데 불합격 0개.

**요청서와 내 값의 차이 (요약).** (1) k_t·자유각·홈·주머니·슬롯·보스 값은 같다. (2) 넣기 검사: 요청서의 ‘0.5면 막힘’은 중심선 판정이라 보수적이다 — 선 외곽으로는 0.5에서 0.25로 지나가지만 공차를 넣으면 모자라 0.8은 그대로. (3) 짧은 다리 홈은 요청서의 나가는 점대로 허브를 뚫었다(글의 2.8은 검사 띠). (4) 레버 질량을 요청서는 그대로 두었고, 이 판은 주머니 구간 빠진 것을 다 빼 0.08 g 가벼워졌다(캡스턴 y는 188.34 / 180.31로 같음). (5) 요청서 결과는 고침 1 모델 기준이라 r4.4 값이 조금 다르지만 변화량(행정 중 DW 최대 +0.40, 바닥 UW +0.38, 연타 +0.07 Hz)은 이 판(+0.40, +0.38, +0.06 Hz)과 같다. (6) 요청서가 적은 ‘손 들기 704 MPa, 카탈로그 55° 토크의 107 %’도 같다(이 판 704 MPa, 107 %).

### 1f-2. r4.5 → r4.5 고침: 검증 지적 다시 재기와 해결

r4.4 고침 2b를 검증한 사람(‘고침’ 렌즈)과 r4.5 스프링을 검증한 사람(‘스프링’ 렌즈)의 지적 6건을 먼저 이 모델로 다시 재고 판정했다. 모든 판정은 모듈 하나(백 최악 D, 흑 C#, 착지 문제의 F·F#)로, PLAY 0.5/1.0/1.5 m/s × 누름 0.45/1/2 N + 뗌, ABUSE 2.5 m/s, 재료 공칭 + 최악이다. 부품은 늘지 않았다.

| 지적 | 요지 | 다시 잰 값 | 판정 | 고친 것 / 기각한 안 |
|---|---|---|---|---|
| 스프링 major | 코일(ID 5.0)이 Ø4 봉 위에서 약 0.44 뜸: 짧은 다리 2.5가 한 면에만 기대 다리 힘 합 1.56 N이 코일을 56° 쪽 봉으로 밀고, 다리가 면에서 떨어져 11° 풀림 → 쉼 4.19 → 2.49 N·mm, PLAY 목표 3개 불합격(립 DW, 흑 DW, 흑 바닥 UW 마찰 2배); 코일-봉 마찰 이력은 모델 밖 | 맞음 — 모델에 뜸 평형을 넣음(`spring_pose` ‘face’: 코일이 다리 힘 합 방향으로 봉에 닿고, 짧은 다리 끝이 면에 다시 닿을 때까지 풀림; 코일 반지름은 감긴 각을 따라). r4.5 그대로: 밀림 0.47(54° 쪽), 풀림 13.4°, 쉼 2.18 / 바닥 4.15 N·mm(검증자 2.49 / 4.57: 이 모델은 감길수록 줄어드는 ID도 셈), 봉 힘 1.18 / 2.22 N; D DW 46.5, 립 y0 42.2(< 47), UW 38.0; C# DW 46.0(< 47), 바닥 UW 마찰 2배 18.9(< 20) → 불합격 3개 확인 | 받아들임 (고친 방법은 다름) | 짧은 다리를 8.0로 잘라 폭 0.70 가둠 홈에(아래 표). 검증자 안 ① 홈을 -12.9° 돌림 — 쉼 토크는 돌아오나 코일이 봉을 3.2 N으로 문질러 μ 0.3이면 흑 바닥 UW 마찰 2배 14.2(μ 0.1이어도 19.0) 불합격; ② 짧은 다리 5 + -5.6° 돌림 — μ 0.3 19.0 불합격; ③ 다리 힘이 코일을 주머니 벽으로 밀게 — 힘 방향(54°)이 코일 슬롯 열림 안이라 벽이 없음. 테스트 8(C06b = 모델 주머니 단면, 진짜 Ø4 봉)이 이것을 잰다 |
| 스프링 minor 1 | 건반 뺀 레버의 긴 다리를 다시 걸 때 x 여유가 거의 없음: 뒷벽 홈(2.4)이 레버 중심에, 다리는 x +0.8; 코일 축 놀음 ±0.44 + 레버 놀음 0.405 → 다리 중심 최대 1.65, 홈이 받는 폭 1.45 | 맞음: 받는 폭 1.45(반폭 1.2 + 입구 0.5 − 선 반지름 0.25), 코일 축 놀음 0.438 + 레버 놀음 0.405 → 레버 중심 홈이면 여유 -0.19(음수) | 받아들임 | 뒷벽 홈·보스(4.4)를 긴 다리 x(레버 +0.8)에 맞춤(`spring_groove_dx`) → 여유 0.61. 풀린 다리 검사에 코일 뜸(가둠 홈 따라 봉까지 0.50 / 막힌 끝까지 0.3, 홈 안 기울기 ±1.99°)을 넣음: −31.3° 레버 공칭 입구 안 1.88(뜸 넣고 0.82), 자유각 +5°면 -0.01(뜸 넣고 -1.08) — 입구 밖이어도 x가 맞아 다시 넣을 때 모따기가 받음 |
| 스프링 minor 2 | 시험 8 되돌림 ‘±5° 넘으면 홈 바닥 y를 0.367 mm/° 옮김’은 더 감는 쪽으로 못 함: 홈 바닥 y211.0 뒤 뒷벽 1.0뿐 | 맞음: 홈 바닥 y211.0, 뒷벽 끝 y212 → 1.0 남음; 껍질 0.4를 두면 0.6 더 깊게 = +1.6° | 받아들임 | 시험 8 결과표를 한쪽 한계로 고침: 더 감기는 홈 바닥 깊게 0.6까지(+1.6°), 그보다 모자라면 `spring_notch_rot`(가둠 홈을 CW로 돌려 캐리어 다시 출력) 또는 스프링 다시 주문; 덜 감기는 홈 바닥 얕게(보스 안에서 자유) |
| 고침 minor 1 | 킬 뿌리가 밸런스 레일 뒷면에 ‘고정’: 그 면은 바닥 구멍 앞 가장자리이고 레일(핀 선 사이 약 82, 리본 차선 위는 9 높이)은 단단한 땅이 아님; 1e장은 단계 0 합격선이 이를 본다고 했지만 시험 3은 띠의 E만 잼 | 맞음: `rail_keel_root` — 레일(y132.3~144.5, z3~19.00) + 바닥 띠를 x 방향 보로(리본 차선 위는 위아래가 따로), 모듈 핀 선에서 단순 지지·비틀림 멈춤, EVA 받침 없음 → kv 970 N/mm, kr 130174 N·mm/rad, 뒷면에서 759 N/mm; 킬 z18이면 화음 자리 447.5 N/mm(< 460; 레일 고정 494.7). 6건반 PLAY 킬 굽힘 16.64 MPa | 받아들임 | F\|F# 핀(바닥 밑면 z3부터 윗판까지) 앞끝 y152 → **y148.6**(건반 F 윗면 꼬리까지 1.40, 복귀 넘침 자세), 킬 y144.5~148.6(길이 4.1, 이전 7.5) z3~**19.3**(건반 F 밸런스 블록까지 1.34, 복귀 넘침 자세) → 화음 자리 **491.6 N/mm**(6.9 % 여유; 가장 무른 화음이 다시 C-C#-D-D#-E-F), 킬 굽힘 13.02 MPa, 첫 모듈 정하중 E·F 0.121 mm. 이 판의 첫 시도(킬만 z21로)는 470.3 N/mm였지만 건반 F 밸런스 블록까지 0.21(강체 바닥 자세, 1.3 미만; ABUSE 복귀 넘침은 공차 뒤 접촉)라 버렸다; 핀 앞끝을 y152에 둔 채 킬을 한계 z19.3로 하면 458.0(< 460). 레일 받침의 범위: 해치 가장자리에 고정 492.9, 핀 선 사이 단순 지지만(연속·EVA 없음) 337.6(E·F 0.164 mm, 불합격) — 모델 값(핀 선 연속, EVA 없음)은 그 사이다. 하한이 합격선 아래이므로 단계 0에 **조립 시험 21 첫 모듈 정하중**(6 × 60 N, E·F ≤ 0.13 mm; 하중 방향은 아래 ‘r4.5 고침 3’)을 넣고 1e장 문장을 고침. 기각한 안: 레일 앞 치마(비틀림 축이 앞으로 가 오히려 떨어짐), 레일 뒷면을 바닥 구멍 위로 늘리기(기판 넣는 길·부품 구역과 겹침), 킬 T 날개(기판 홈 안이라 x로 못 넓힘) |
| 고침 minor 2 | 고침 2b·단계 번호가 남긴 낡은 글: (a) 10.1 T2 행 ‘z31.0’, 부품표 캡스턴 ‘z31.0’ (b) 접착은 10장 4단계인데 3곳이 3단계 (c) 고침 2b 행 레버 57.02 → 56.97(56.97은 r4.5 값) (d) 단계 0 ‘설계 492’ | 맞음: T2 게이지·S08·T17은 z30.90으로 맞음; 10장 단계 1이 기판 넣기라 접착은 4단계; 고침 2b 레버 57.05 g; 화음 자리는 r4.5 모델 494.2(이 판 491.6 — 킬 고침) | 받아들임 | (a) T2 행·부품표를 정착 쉼 z30.90(건반 좌표 z31.0)로 (b) 시험 20.3·부품표 강철 행·고침 2b 형상 행을 4단계로 (c) ‘57.02 → 57.05 g (r4.5 56.97, r4.5 고침 56.95)’ (d) 단계 0 글을 모델 값으로(지금 492) |
| 고침 minor 3 | 12장 ‘뺄 심이 없으면 쐐기 0.1 얇게 다시 출력’은 가장 얇은 백 쐐기(0.349 → 0.249)에서 출력 최소 0.3 아래 | 맞음: 백 쐐기 얇은 끝 0.347, 끝 부속 A0 0.291 · B0 0.359 · C8 0.259; 흑 1.501는 됨 | 받아들임 | 쐐기 얇은 끝 < 0.40인 자리는 쐐기를 그대로 두고 그 패드 자리의 바 밑면을 0.1 올려(바 1.5 → 1.4) 다시 출력하거나 펠트를 0.1 얇게(12장·1e장 글) |

**코일 뜸 — 후보 비교 (모델 `spring_pose`·`spring_T_table`, T(b)와 봉 힘 N(b)을 statics에 넣음; 이력 = μ N r_봉, 마찰 2배면 두 배).** 합격선: DW 47~55 g, 립 y0 ≥ 47 g, UW ≥ 20 g(바닥, 마찰 2배 포함).

| 안 | μ 코일-봉 | 쉼 / 바닥 토크 (N·mm) | 풀림 (°) | 봉 힘 쉼 / 바닥 (N) | 이력 바닥 (N·mm) | D DW / 립 / UW (g) | C# DW / UW (g) | 마찰 2배 D DW / C# 바닥 UW (g) |
|---|---|---|---|---|---|---|---|---|
| r4.5 그대로 (짧은 다리 2.5, 한 면) | 0.0 | 2.18 / 4.15 | 13.4 | 1.18 / 2.22 | 0.00 | 46.5 / 42.2 / 38.0 | 46.0 / 36.5 | 50.8 / 18.9 |
| 홈 돌림 -12.9 ° (다리 2.5) | 0.0 | 4.19 / 6.16 | 13.4 | 2.23 / 3.23 | 0.00 | 51.9 / 47.1 / 42.8 | 51.0 / 40.8 | 56.5 / 21.5 |
| 홈 돌림 -12.9 ° (다리 2.5) | 0.1 | 4.19 / 6.16 | 13.4 | 2.23 / 3.23 | 0.65 | 53.0 / 48.1 / 41.6 | 52.0 / 39.8 | 58.8 / 19.0 |
| 홈 돌림 -12.9 ° (다리 2.5) | 0.3 | 4.19 / 6.16 | 13.4 | 2.23 / 3.23 | 1.94 | 55.3 / 50.2 / 39.4 | 54.1 / 37.7 | 63.3 / 14.2 |
| 짧은 다리 5.0 + 홈 돌림 -5.6 ° | 0.0 | 4.19 / 6.13 | 5.8 | 0.76 / 1.07 | 0.00 | 51.9 / 47.1 / 42.8 | 51.0 / 40.8 | 56.5 / 21.4 |
| 짧은 다리 5.0 + 홈 돌림 -5.6 ° | 0.1 | 4.19 / 6.13 | 5.8 | 0.76 / 1.07 | 0.21 | 52.3 / 47.5 / 42.4 | 51.4 / 40.4 | 57.3 / 20.6 |
| 짧은 다리 5.0 + 홈 돌림 -5.6 ° | 0.3 | 4.19 / 6.13 | 5.8 | 0.76 / 1.07 | 0.64 | 53.1 / 48.2 / 41.6 | 52.1 / 39.7 | 58.8 / 19.0 |
| **r4.5 고침: 가둠 짧은 다리** 8.0 (홈 0.70) | - (봉에 안 닿음) | 4.19 / 6.03 | 0.0 | 0.00 / 0.00 | 0.00 | 51.9 / 47.1 / 42.8 | 51.0 / 40.8 | 56.5 / 21.3 |

**가둠 홈 (새 형상, P18).** 짧은 다리(8.0, 곧게)는 코일 접선(레버 기준 228.82°, y201.48 z31.48)에서 끝 y195.46 z36.75(축에서 8.44)까지 간다. 홈은 짐 받은 다리를 CW로 1.99° 돌린 띠(136.83° 방향, 폭 0.70 = 선 0.5 + 놀음 0.20)로, 축에서 잰 두 면 2.511 / 3.211, 주머니 안 -0.5에서 허브 벽을 지나 웹 안 막힌 끝(다리 끝 너머 0.3)까지 판다(웹 밑면 3.79 깎음). 짐을 받으면 다리 끝이 바깥 면(y195.30 z36.56)에, 다리 몸이 안쪽 면의 주머니 가장자리(y199.97 z33.13)에 닿아 두 점(팔 5.75)이 짝 힘으로 토크를 받는다: 쉼 0.73 N, 손 25° 1.36 N. 긴 다리 힘(쉼 약 0.2 N)은 두 점 힘의 차이와 마찰(또는 막힌 끝)이 받으므로 코일은 봉에 닿지 않는다 — 봉과 틈 쉼 0.435, 바닥 0.379, 손 25° 0.326(긴 다리 힘의 홈 방향 성분은 막힌 끝 쪽이고 두 점 마찰로 잡으려면 μ 0.10면 된다; 미끄러져 다리 끝이 막힌 끝에 닿아도 봉과 틈 0.026 이상). 짧은 다리가 길어져(가둔 다리의 굽힘 길이 2 s_E + l_s) k_t 8.866 → **8.437 N·mm/rad**, 자유각 -27.07 → **-28.45°**(b = 0 토크 4.19 그대로), 바닥 토크 6.14 → 6.03, 손 25° 8.06 → 7.83 N·mm(카탈로그 55° 토크의 107 % → 104 %). 주머니 구간은 넣는 슬롯(짧은 다리를 따라 316.83°, 면 ±3.25)과 긴 다리 창(35° 방향 윗면 +2.6)이 뒤쪽으로 이어진 열림이 되고, 두 조각 A(웹 쪽: 두 닿는 점) · B(아래 고리: 다리 힘 없음)로 남는다.

| 홈이 출력된 폭 (설계 대비) | 놀음 | 다리 기울기 변화 | 쉼 토크 (N·mm) | 봉과 틈 (쉼) |
|---|---|---|---|---|
| -0.20 | 0.00 | -1.99° | 4.48 | 0.257 |
| -0.15 | 0.05 | -1.49° | 4.41 | 0.302 |
| -0.10 | 0.10 | -1.00° | 4.34 | 0.346 |
| +0.00 | 0.20 | +0.00° | 4.19 | 0.435 |
| +0.10 | 0.30 | +1.00° | 4.04 | 0.346 |
| +0.20 | 0.40 | +2.00° | 3.89 | 0.257 |
| +0.30 | 0.50 | +3.00° | 3.75 | 0.168 |

**넣기와 창.** 봉을 꿰기 전, 자유 상태 스프링을 짧은 다리 끝부터 홈 중심선을 따라 밀어 넣는 길(0.02 걸음)에서 짧은 다리 ↔ 홈 면 0.100(홈이 0.10 / 0.15 좁게 나오면 0.050 / 0.025), 코일 ↔ 조각 A 0.22 · B 0.14, 긴 다리(자유 방향 46.8°) ↔ A 4.34 · B 3.14 → 지나감. 긴 다리는 레버 -31.3°~18.0° 내내 창 안(면까지 0.57 + 선 반지름 + 0.2; 가장 좁은 곳은 손 들기 25°). 허브·웹: ABUSE 층 안 7.96 MPa(Kt 2, 한계 25), PLAY 4.93(한계 12).

**레버 떨어짐 = 실제 착지(도면 작성자).** `metrics.lever_drop`이 이제 `circuit_r44.drop`과 같은 계산(이름 있는 BRD-01 부품·보스·기판)이다: D# 16.75°(기판 보스(나사 보스, 레일 뒷면 브래킷)); E 13.25°(CD74HC4067 모듈(핀 헤더 위)); F 13.25°(CD74HC4067 모듈(핀 헤더 위)); F# 24.00°(기판 윗면); G 23.50°(기판 윗면); G# 16.75°(기판 보스(위치 핀 보스, 레일 뒷면 브래킷)). 바닥판 위 레버(C·D 등)는 30.25°로 그대로다.

**도면 작성자 형상 메모 처리.**

| 메모 | 처리 |
|---|---|
| metrics lever_drop이 z20 일반 구역 착지 | run_all이 실제 착지(`lever_drop(actual=True)`)를 씀 — 위 문단, 11장 |
| 짧은 다리 홈이 레버 D 기준 하나뿐(흑은 쉼 각이 약 0.5° 다름) | 홈은 레버 좌표 값 그대로 두고 `solved.spring.rest_deg_per_lever`에 레버마다 쉼 각을 내보냄(주머니 구간 단면은 레버 부품으로 이미 레버마다 돌려 나감) |
| C06a 입구가 발 벽 뒤라 숨은 선으로만 보임 | 모델 잘못 아님(메모 그대로). C06a 홈은 이제 다리 x(코일 가운데 +0.8) |
| kit.MAT_FIXED에 ‘control-board boss’ 항목이 없음 | 도면 쪽 `kit.py`(도면 작성자 폴더)라 이 판에서 고치지 않음 — 이름이 ‘control-board boss’로 시작하는 프레임 부품이라 프레임 분류가 맞음 |
| T2 부리 프리즘이 몸통 윗면과 0.01 겹쳐 부리 밑이 z53.39 | 부리(손잡이) 밑면 z57.5 한 프리즘 + ‘beak web to the body top (0.01 into the body)’ 따로 |
| T24 ‘앞 발 y132.3~133.85’와 프리즘 이름이 다름 | 프리즘을 ‘front body (y132.00~132.30)’ + ‘front foot = land on the rail top (y132.30~…)’로 나누고 T24 글에 앞 몸통을 적음 |
| T09 기둥이 프리즘 투영으로는 한 덩어리 | tools_geometry에 프리즘마다 (X, z) `front` 윤곽을 더함 — T09 기둥은 사다리꼴(윗면 8, 밑 17); T09 글에 적음 |
| 뒷벽 스프링 홈이 잘라낸 부품으로 안 나감 | geometry `parts`에 ‘spring groove cut …’(female) 추가, 끝 부속도 |
| P18 입구 모따기 0.5×45°가 없음 | ‘spring groove entry chamfer …’(female, 옆모습 + 앞모습 `front`) 추가 |
| 스프링 다리가 빼기·떨어짐 자세로 안 나감 | 스프링 부품에 `side_drop`(레버를 lever_drop 각으로; 자유각 아래에서 긴 다리가 레버와 함께 돎)을 더함; `side_service` = 빼기 자세 |

**결과 (r4.5 → r4.5 고침, run_all 전체 다시 돌림).**

| 항목 | r4.5 | r4.5 고침 | 변화 |
|---|---|---|---|
| DW 백 (g) | 51.92 | 51.92 | -0.00 |
| UW 백 (g) | 42.78 | 42.78 | -0.00 |
| 바닥 UW 마찰 2배 백 (g, ≥ 20) | 25.17 | 24.99 | -0.18 |
| 스프링 토크 바닥 백 (N·mm) | 6.14 | 6.03 | -0.11 |
| DW 흑 (g) | 51.01 | 51.01 | -0.00 |
| UW 흑 (g) | 40.80 | 40.80 | -0.00 |
| 바닥 UW 마찰 2배 흑 (g, ≥ 20) | 21.46 | 21.34 | -0.12 |
| 스프링 토크 바닥 흑 (N·mm) | 5.78 | 5.69 | -0.09 |
| 레버 (g) | 56.97 | 56.95 | -0.02 |
| 연타 백 (Hz) | 16.30 | 16.26 | -0.04 |
| 연타 흑 (Hz) | 18.88 | 18.84 | -0.03 |
| 연타 마찰 2배 백 (Hz, ≥ 13.3) | 15.26 | 15.22 | -0.04 |
| 연타 마찰 2배 흑 (Hz) | 17.71 | 17.67 | -0.04 |
| 끝까지 복귀 백 (ms) | 45.28 | 45.38 | +0.10 |
| 노치 들림 PLAY (mm) | 0.162 | 0.162 | -0.00 |
| 모듈 스윕 최소 (mm) | 1.31 | 1.31 | -0.00 |
| 공차 뒤 (mm) | 1.01 | 1.01 | -0.00 |
| 모듈 무게 (kg) | 1.374 | 1.374 | +0.00 |
| 6건반 화음 자리 (N/mm, ≥ 460) | 494.2 | 491.6 | -2.65 |

0장 판정 45개 가운데 불합격 0개. 기본 구성 비용 변화 +69,400원(r4.5 +69,400원, 스프링은 같은 부품을 길게 자름).

**r4.5 고침 3 — 재검증 지적 (절차·글만 고침).** 설계 수치와 형상(모듈·건반·레버)은 바뀌지 않았다. run_all은 다시 돌리지 않았다. 단계 0 키트에 C17a 한 개가 늘었다.

| 지적 | 무엇이 틀렸나 | 고친 것 |
|---|---|---|
| 시험 21 하중 방향 (major) | 시험 21이 바닥 EVA 위의 모듈에서 윗판 윗면을 눌렀다. 쓰임에서는 패드가 윗판을 밑에서 밀어 F\|F# 핀·킬이 레일 뒷면을 들어 올린다. 위에서 누르면 레일·바닥 띠(z3~5)가 EVA(z0~3)에 얹혀, 레일 자체가 약해도 단단한 레일(E·F 0.094 mm)처럼 읽힌다. 그래서 불합격 쪽 하한(이웃 핀 선 사이 단순 지지, 0.159 mm)도 합격으로 나올 수 있었다. 위 표의 ‘EVA가 레일을 받쳐 실제는 더 단단하다’는 아래로 누를 때만 맞다 | 시험 21을 쓰임 방향으로 고쳤다. 모듈을 새 단계 0 부품 **C17a 받침 빗**(높이 3, 폭 3인 이 4개가 핀 선 x1.0 / 41.7 / 123.9 / 163.5 밑, 뒤 막대가 뒷벽 밑; 레일 밑 x43.2~122.4와 기판 구멍 밑은 빔, 164.5 × 212.0, 9.0 cm³)에 얹고 위에서 누른다. 모델이 선형이라 쓰임과 같은 레일 휨이다. 합격선 E·F ≤ 0.13 mm는 그대로다(모델 0.121). 두 끝 값은 시험이 누르는 D-D#-E-F-F#-G 화음 값이다(위 표의 0.164는 단순 지지일 때 가장 무른 D#-E-F-F#-G-G# 화음 값). ‘먼저 EVA 닿음 확인’ 되돌림과 ‘EVA가 더 단단하게 함’ 문장을 지웠다(17장 21번, 18장, 위 표) |
| 단계 0 되돌림이 설계와 어긋남 | 17장 정하중 줄의 ‘킬 뿌리 더 키움’: 킬은 이미 건반 F와 1.3 한계다. 17장 3번의 ‘F\|F# 핀이 바닥에 닿는지 확인, 핀 밑면 덧댐’: r4.4 고침 2b부터 기판 밑 바닥은 구멍이고 핀은 킬로만 레일에 붙는다. 17장 스프링 넣기 줄은 r4.5의 한 면 홈 글이었다 | 정하중 되돌림 = 잰 k_ch로 화음 자리 동역학을 다시 보고, 그래도 불합격이면 회로 세션과 리본 차선 위 레일 높이를 다시 정함(시험 21과 같음). 3번 되돌림 = 윗판 채움 100 % 또는 `plate_t` +0.6~1.2(17.1장 시험 3 표), 킬·레일 이음은 시험 21. 스프링 넣기 = 가둠 홈 순서(시험 13). 정하중 줄은 9번에 끼어 있어 10~21번이 키트 번호와 하나씩 어긋났다 — 표 끝 21번으로 옮겨 번호를 키트와 맞췄다 |
| 핀 발 y152 글 | 결과 파일(results.txt)과 부품표 프레임 줄이 F\|F# 핀 발을 y152~170.7로 적었다. 핀 앞끝은 r4.5 고침에서 y148.6(`keel_front`)다 | 두 곳을 `keel_front`로 찍음: y148.6~170.7 (run_all.py; results.txt·parts_list.json·metrics.json은 같은 모델이라 그 글만 고침) |
| C06b STL이 닫힌 몸이 아님 | 허브 받침 원기둥(Ø8.6 = 허브 R4.3)의 꼭짓점이 주머니 단면이 허브 원에서 웹으로 꺾이는 점(0, −4.3)과 겹쳐 Z7.01에 비다양체 모서리가 생겼다 | 허브 받침을 Ø8.5로(허브 안 0.05). 단계 0 STL 34개가 모두 닫힌 몸이다(make_stage0 검사, trimesh로도 확인) |

## 2. r3 → r4 단순화

### 2.1 전후 비교 (모듈 한 개, 표시가 없으면)

| 항목 | r3 | r4 | 변화 |
|---|---|---|---|
| 출력 부품 수 | 76 | 32 | -44 |
| 구매 부품 수 (캡스턴 나사·너트, 접시 스프링 낱개로) | 173 | 88 | -85 |
| 부품 수 합 | 249 | 120 | -129 (-52 %) |
| 악기당 공구 | 드라이버 Ø30, 빼기 고리, M3 탭, Ø3 H7 리머 | Ø4.0 드릴, 육각 렌치 2.0(캡스턴, 벤치에서만), 출력 공구 4개(벤치 지그 받침·높이 블록·캡스턴 벤치 게이지·밸런스 핀 높이 게이지, 10.1장) | |
| 모듈 무게 | 2.03 kg | 1.37 kg | -657 g |
| 맨 위 높이 | 커버 z78.0, 손나사 머리 z80.7 | 윗판 z72.85 (그 위 없음) | -7.9 mm |
| 기본 구성 비용 변화 (88건반) | +130,400원 | +69,400원 | −61,000원 |
| 금속 (88건반) | 9.52 kg | 5.10 kg | -4.42 kg |
| 필라멘트 (88건반, 서포트 포함) | 6.54 kg · 436 h | 6.55 kg · 436 h | +0.01 kg |
| 88건반 본체 무게 | 15.3 kg | 10.6 kg | |
| 유효 질량 m_eff (백 / 흑) | 68.9 / 64.7 g | 55.2 / 46.5 g | 가볍게 느껴짐 |
| 조립 뒤 다시 조이기 | 24 h 뒤, 운반 뒤 손나사 8개 | 없음 | |

출력 부품 수 내역 (모듈): r3 = keys 12, carriers 12, frame 1, cover 1, sensor_bar 1, c_rings 8, pad_holders 12, black_spacers 5, spring_seats 12, service_blocks 12; r4 = keys 12, carriers 12, frame 1, pad_bars 4, curtain_strip 1, sensor_bar 1, rod_plug 1.
구매 부품 수 내역 (모듈): r3 = steel_blocks 12, rail 1, tapped_strips 4, key_rod 1, lever_rod 1, brass_bushings 5, balance_pins 12, locating_pins 2, cover_magnets 2, capstans 12, capstan_nuts 12, thumb_screws 8, disc_springs 72, sensor_magnets 12, lead 5, pads 12; r4 = steel_blocks 12, key_rod 1, lever_rod 1, balance_pins 12, capstans 12, capstan_nuts 12, torsion_springs 12, sensor_magnets 12, pads 12, board_screws 2.

### 2.2 뺀 것과 그 값

| 뺀 것 (r3) | 대신 (r4) | 성능 대가 (숫자) |
|---|---|---|
| 업스톱 레일 SS400 3T×60 (231 g), 손나사 8, 접시 스프링 72, 탭 강철 띠 4 + 주머니, 드라이버, 24 h 다시 조이기 | 프레임 윗판(r3 브리지를 y146.5까지 앞으로 늘림) + 핀 칸마다 패드 바 1개(모듈 4) | 패드 자리 강성 건반마다 1492~2036 N/mm(연구: r3 레일+나사+브리지 433~816; r4.1은 F\|F# 핀이 기판 홈을 지나 바닥에 닿음, r4.4 고침 2b부터 킬로 밸런스 레일에). 6건반 동시 화음에서는 자리마다 492 N/mm로 물러져 가벼운 누름(0.45~0.6 N)에서 재무장 → 펌웨어 거름 필수. 이음이 없으니 ‘이음 열림’ 문제 자체가 없음 |
| 먼지 커버 판 + 위치 핀 2 + 자석 2 | 가림판 띠 1개(윗판 앞 턱에 걸침) | 윗판 윗면이 겉면이 됨. 운반할 때 가림판은 걸려 있을 뿐이라 모듈을 뒤집지 않는다 |
| 흑건 납 5 g × 5 + 추 칸 + 출력 뚜껑 + 에폭시 | 없음 | 흑 노치 들림 PLAY 0.068, ABUSE 0.177(한계 0.40); 흑건은 1 N에서 펠트 위 0.27 mm에 멈춤(레버가 패드에 먼저) |
| 강철 블록 9×50×21.5 (75.8 g) | 9×19×40 (53.7 g) + 비틀림 스프링 12 | 스프링 12개가 늘어남(r4.5: 미스미 기성품 C-UA90R5-3-0.5, 두 다리를 잘라 씀; 100 × 310원). 행정 중간 DW가 54.5 g까지 오름(쉼 51.9). 대신 m_eff 68.9 → 55.2 g, 연타 여유가 커짐 |
| 경화 SUJ2 Ø3 + 황동 부싱 5 + H7 리머 | SUS304 Ø4 (건반 봉과 같은 4 m 봉), 출력 보스 Ø3.9 → Ø4.0 드릴 | 레버 봉 마찰 1.20 g(r3 0.71 g). 6건반 화음 봉 응력 65 MPa, ABUSE 88 MPa로 풀림재 항복 205 아래; 보스 지압 12.9 MPa(ABUSE) |
| 간격 C-링 8 | 허브 칼라(캐리어와 한 몸, r4.1: 0.05씩 짧게) | 칸마다 축 놀음 0.46 / 0.46 / 0.43 / 0.30; 캐리어가 위치마다 달라짐(16곳, 이름 새김) |
| L 서비스 블록 12 (조립) + 3 (보관) | 없음 (r4.1 조립 순서: 레버 먼저, 건반 나중) | 빠진 건반의 레버는 바닥판이나 기판 부품 위에 0.40 N으로 놓인다; 다시 넣을 때 손톱 턱으로 든다 |
| 패드 홀더 12 + 흑 스페이서 5 | 패드 바에 출력한 쐐기 | 없음. 건반마다 조정은 PET 심 |
| 스프링 자리판 12 (빈 선택품, 만들 수 없던 것) | 비틀림 스프링 (기본) | 12개 추가 |
| 강철 앞 윗모서리 2×45° 줄 모따기 (88번) + R3 캡 접점 | 패드가 드러난 강철 윗면에 닿음 | 없음 |
| 출력 빼기 고리 | 손톱 + 레버 손톱 턱 | 건반 뒤 턱 당김 2.7 N(스냅 2 N; R2.50 쿠폰이면 5.2 N) |

### 2.3 단순화 연구 안: 채택 / 기각

세 연구(업스톱 U1~U10, 건반 유지 RET-1~10, 모듈 감사 A1~A12)의 안을 하나씩 판정했다. 연구들은 서로 다른 레버·패드를 가정했으므로, 채택한 안들은 이 모델에서 한꺼번에 다시 계산했다.

| 안 | 내용 | 판정 | 이유 (숫자) |
|---|---|---|---|
| U1 | 패드 면을 1 N 진짜 정착에서 잡음 | 채택 | r3 major 1의 해결. 1.4 s 누른 뒤 레버 각속도 1e-6 rad/ms 미만에서 읽음 |
| U2 | 레버가 패드에 먼저 닿는 틈, 보조 스프링 삭제 | 일부 채택 | 레버 먼저는 채택하되 백 -0.40 / 흑 -0.45(연구 −0.8 / −0.6은 무거운 r3 레버용). 스프링은 A1·A2의 비틀림 스프링으로 대신 — 가벼운 레버는 스프링 없이 연타 13.46 / 12.50 Hz(마찰 2배)로 불합격(r4 탐색) |
| U3 | 패드 접점을 강철 윗면으로, 미세셀 우레탄 4T + 펠트 1T | 고쳐서 채택 | 접점은 채택(모따기·캡 벽 조건 삭제). 폼 6T, 패드 y170~182로 바꿈: 뒤로 10 mm 옮기면 윗판이 두꺼운 곳에 가까워 자리 강성 1.7배, 폼 6T는 자리가 물러도 유령이 덜함(950 N/mm, 0.45 N: 4T 67 %, 6T 32 %, r4 탐색) |
| U4 | 흑건 납 삭제 | 채택 | 흑 ABUSE 들림 0.177 ≤ 0.40 |
| U5 | 레일·나사·접시 스프링·띠·핀·자석 삭제, 프레임 받침판 + 패드 바 | 채택 (고쳐서) | 패드 바를 계단형으로(앞부분은 윗판 홈 속 1.5 높게 → 레버 앞 모서리와 틈), L 레일(웹 + 립)에 끼우고 가장자리 잎 혀로 자리에 밀어 올림(r4.2). 맨 위 z72.85 |
| U6 | 펌웨어 유령 거름 (250 ms, 0.30 m/s, 25 %) | 고쳐서 채택 | 고정 0.30 대신 ‘앞 음 속도의 25 %, 최대 0.45’(ABUSE 화음 유령 내려옴 최대 0.07); r4.1: 앞 음 문턱 1.2 → 0.3 m/s(검증자 물리 M1) |
| U7 | D11 e ≤ 0.07, 자리 강성 조건, 단계 0 처짐 시험 | 채택 | D11 고침(r3 major 8). 자리 합격선 830 N/mm(100 N에 0.12 mm; r4.0 설계값, 모든 PLAY 목표 통과), 6건반 화음 460 N/mm; r4.1 설계 1490 / 492 |
| U8 | R3 캡 접점 유지 + 폼 7T | 기각 | 연구: 맨 위 z77.3(목표 z74 초과), 흑 ABUSE 들림 0.373 |
| U9 | 레일 유지, 접시 스프링 없이 손 조임 너트·쿼터턴 | 기각 | 연구: PETG가 5~10 µm 앉으면 예하중 ≈ 0 → 한 건반 PLAY에서도 이음이 열림 |
| U10 | 레일 + 접시 스프링 유지, U1~U4만 | 기각 | 연구: 부품이 줄지 않고 z78.0 / 80.7 |
| RET-1 | 흑건 납 삭제, 흑 캡스턴 다시 풂 | 채택 | 흑 캡스턴 y180.31 (가벼운 레버로 다시 풂) |
| RET-2 | 스냅 판정을 들림으로 (PLAY ≤ 0.20, ABUSE ≤ 0.40), 반지름 쿠폰 | 채택 | r3 major 2의 해결 |
| RET-3 | 키퍼 틈 1.2 → 1.5 | 채택 | PLAY 키퍼 최소 0.52(합격선 재료 0.41) |
| RET-4 | 밸런스 핀 1.2 앞으로 | 채택 | r3 major 7의 해결, 핀 ↔ 입술 벽 1.39 |
| RET-5 | 흑 탭 7.5 → 6.9 | 채택 | r3 major 4의 해결 |
| RET-6 | 흑 패드 강성 하한 (ABUSE 들림 0.40) | 채택 (형태 바꿈) | 패드가 폼이 되어 합격선을 ‘폼 E ≥ 0.7 MPa, e ≤ 0.07’로 적음. 그 조합에서 흑 ABUSE 들림 0.349 |
| RET-7 | 도구 없는 빼기(레버를 손으로 듦), 고리·L 블록 삭제, 조립 순서 | 고쳐서 채택 | 윗판은 남으므로 레버를 손톱 턱으로 듦(0.47 N), 레버는 윗판에 닿을 때까지 15.5°. L 블록은 보관용 3개도 없앰 |
| RET-8 | 스냅 없이 열린 노치 | 기각 | 연구: 무른 패드에서 ABUSE 흑 들림 1.27 mm(빠짐) |
| RET-9 | 닫힌 구멍 + 빼는 봉 | 기각 | 연구: 건반 하나를 빼려면 봉을 12건반에서 뽑아야 함 |
| RET-10 | 늘 닿는 키퍼 / 틈 없는 입술 | 기각 | 연구: 키퍼 무접촉 목표 위반, 출력 공차에 민감 |
| A1 | 강철 9×19×40 + 스프링 기본 | 채택 | 모듈 강철 −265 g, m_eff 68.9 → 55.2 |
| A2 | 비틀림 보조 스프링 | 채택 | r3 major 5의 해결 |
| A3 | 레버 봉 SUS304 Ø4 (냉간인발) | 채택 (조건 풂) | r4 하중에서 ABUSE 88 MPa < 풀림재 205 → 냉간인발 지정 불필요 |
| A4 | 흑건 납 삭제 | 채택 | U4·RET-1과 같음 |
| A5 | C-링 → 허브 칼라, L 블록 삭제 | 채택 |  |
| A6 | 높이 z74 (레일 밑면 패드 + 얇은 노브 너트) | 목표만 채택 | 레일 대신 윗판으로 z72.85 |
| A7 | 고정 방식에 달린 삭제 목록 | U5로 대신 | 띠·접시 스프링·핀·자석은 삭제, 브리지는 윗판이 되어 남음 |
| A8 | 질량·부품·비용 합 | 정보 | r4 실제: 1.37 kg, 120개, +69,400원 |
| A9 | 보관함 칸 나눔 | 채택 | r3 minor 해결 |
| A10 | 앞 펠트 y1.5~9.0 | 채택 | r3 minor 해결 |
| A11 | 가림판 z45.5 | 채택 | r4는 가림판을 1.0 앞으로도 옮김(레버 손톱 턱과 틈) |
| A12 | 손 닿는 조정 | 고쳐서 채택 | PET 심은 레일이 아니라 빼낸 패드 바의 패드 밑에 |

## 3. 원리 (r4)

- 건반은 Ø4 SUS304 봉 위의 짧은 시소다(봉 중심 K = (141.0, 21.5)). 스냅 노치(S04)가 봉을 223° 감싸고, 앞으로 옮긴 밸런스 핀(y135.3)이 건반 뒤쪽 x를 잡는다.
- 숨은 빔의 M3 버튼헤드 캡스턴(백 y188.34 · 흑 y180.31)이 레버 밑 펠트 띠를 들어 올린다. 레버 = 출력 캐리어(폭 10.6, 허브 칼라 일체 — 칼라 길이만 위치마다 다름) + SS400 평철 9×19×40(53.7 g, 모따기 없음), SUS304 Ø4 봉에 매달린다(L = (203.25, 33.5)). 허브 가운데 비틀림 스프링(r4.5: 미스미 C-UA90R5-3-0.5, 두 다리를 잘라 k_t 8.44 N·mm/rad, b = 0에서 28.4° 감김)이 강철을 아래로 민다.
- 쉬는 동안 레버 무게와 스프링이 캡스턴을 1.50 N(흑 0.98 N)으로 눌러 쉼 펠트가 뒤 선반(z20.054)에 앉는다. 플라스틱 상시 응력은 최대 0.50 MPa. 예하중이 걸린 이음이 하나도 없다.
- 누르면 레버의 드러난 강철 윗면(윗 립 사이 7.4)이 패드(폼 6T + 펠트 1T, 폭 6, y170~182)에 먼저 닿고(백 -0.40, 흑 -0.45 mm) 곧 건반이 앞 펠트에 닿는다. 패드 면은 1 N 정착 바닥의 강철 윗면과 평행(11.4° / 9.6°)이라 폼이 고르게 눌린다. 패드는 패드 바의 출력 쐐기에 붙어 있고, 패드 바는 윗판 밑 L 레일(웹 + 립)에 끼워져 가장자리의 출력 잎 혀가 립을 딛고 바를 윗판 자리에 밀어 올린다. 패드 힘은 윗판에 **누르는 힘**으로만 전한다.
- 윗판(프레임과 한 몸, z72.85)은 r3 브리지를 y146.5까지 늘린 것이다. 핀 5장과 뒷벽이 받친다. 기판 위 F|F# 핀은 r4.1부터 만능기판 앞쪽 홈을 지나 y148.6~170.7에서 내려가고(r4.4 고침 2b: 기판 밑 바닥이 뚫려 있어 바닥 대신 킬로 밸런스 레일 뒷면에 붙음 — 기판은 밑에서 넣음; r4.5 고침: 이 핀만 앞끝 y148.6, 킬 y144.5~148.6 z3~19.3), r4.3부터 그 뒤는 뒷벽까지 매달려 있다(뒤 선반은 USB 플러그 위가 뚫려 있음). 먼지 커버는 윗판 앞 턱에 걸친 가림판 띠 하나다.
- 손을 떼면 레버 무게 + 스프링이 캡스턴을 눌러 건반을 되돌린다(연타 16.3 / 18.8 Hz). 건반과 레버 사이에 홈이 없어 유격이 없다.
- v3 앞 훅은 크로스바 위 1.5 mm의 ‘닿지 않는 키퍼’다. 센서는 자석 Ø5×2(y67), 2.5 m/s 과다 누름에서도 간격 4.76 mm(≥ 3.0).

## 4. 부품 — 개수와 질량 (`parts_list.json`)

| 부품 | 종류 | 사양 | 모듈당 | 88건반 전체 (예비 포함) | 개당 질량 g | 비고 |
|---|---|---|---|---|---|---|
| 백건 C·D·E·F·G·A·B (+ 끝 A0·B0·C8) | 출력 | PETG, 7종 + 끝 3종, 윗면을 베드에, 스냅 노치 R2.55 + 천 0.5T, 밸런스 핀 홈 y134.0~138.0 | 7 | 62 | 21.68 | 88건반 52 + 예비 10 |
| 흑건 (4종: C#·D#은 같음, + 끝 A#0) | 출력 | PETG, 납·추 칸 없음, 가이드 탭 6.9 | 5 | 42 | 16.78 | 88건반 36 + 예비 6 |
| 레버 캐리어 (위치 16곳, 칼라 14종) | 출력 | PETG, 폭 10.6, 허브 Ø3.9→Ø4.0 드릴, 허브 칼라 일체(왼/오 길이가 위치마다 다름: C 0.00/0.96; C# 0.96/1.03; D 1.03/0.00; D# 0.00/1.51; E 1.51/0.93; F 0.93/0.00; F# 0.00/1.16; G 1.16/0.76; G# 0.76/0.00; A 0.00/0.76; A# 0.76/0.76; B 0.76/0.00; A0 0.00/2.62; A#0 2.62/0.76; B0 0.76/0.00; C8 0.00/0.00), 스프링 주머니 Ø6.6×3.0 + 긴 다리 창(35° 방향, 축에서 +2.6까지 열림) + 짧은 다리 가둠 홈(r4.5 고침 2: 폭 0.70, 주머니에서 허브 벽을 지나 웹 안 막힌 끝까지, 웹 밑면을 3.8 깎음; 넣는 슬롯은 다리를 따라 317°), 손톱 턱(R3 모서리를 채움), 윗 스냅 립 0.9×1.0는 y150~163·184~190에만(옆벽 윗단 z53.0도 그 구간만), 옆벽에 음 이름 새김 | 12 | 88 | 2.84 | 예비 없음: 위치별 파일로 필요할 때 출력 (20분) |
| 프레임 (모듈) | 출력 | PETG, 윗판 z72.85(패드 바 L 레일 8: 웹 1.0 + 립 1.3×0.8), 핀 5·보스(F\|F# 핀 발 y148.6~170.7는 기판 홈을 지나 킬로 밸런스 레일 뒷면에 붙음, 그 뒤 z21.5부터 매달림), 기판 밑 바닥 구멍 x46.25~118.25 y144.5~196.5(제어 기판을 밑에서 넣음), 제어 기판 보스 4 기판 위에 매달림(앞 2 레일, 뒤 2 리브), 밸런스 레일(리본 차선 x59~82), 뒤 선반·리브(USB 플러그 위 홈 x76.45~91.55), 뒷벽(USB 개구 x74~94 z5~21, 스프링 홈 보스 12(폭 4.4, 레버 x +0.8 중심 = 긴 다리 자리), 홈 2.4×3.2 z47~58 밑이 열림, 입구 모따기 0.5), 센서 기판 받침(기둥 x0.5~6.0·앞뒤 리브 윗면 z7.0)과 센서 바 오른쪽 턱 2(v3 P112, r4.5 회로 2차: 립 x161.5~163.0 z13.6~15.1, 기둥 x163.0~164.3) | 1 | 7 | 284.0 | 서포트 88 g 별도 |
| 끝 부속 프레임 (왼쪽 A0~B0, 오른쪽 C8) | 출력 | 같은 단면 + 볼(cheek), 이음 핀 보스 한쪽, 도브테일 (왼쪽 수, 오른쪽 암), 스프링 홈 보스 (왼쪽 3, 오른쪽 1), 패드 바 L 레일 2 | 0 | 2 | 93.3 | 왼쪽 1 + 오른쪽 1 |
| 패드 바 (6종: 모듈 칸 1~4 + 끝 부속 왼·오) | 출력 | PETG 1.5T 계단형(윗 계단 y167.0, 아래 계단 y165.5), 길이 38.5(뒤 멈춤까지), 쐐기 3개(백 0.35~2.76, 흑 1.50~3.54; 끝 부속은 건반마다 자기 면), 앞 손잡이(칸 이름 새김), 양쪽 가장자리 예하중 잎 혀 0.6×1.6×8 (0.3 눌림, 레일 립 위) | 4 | 30 | 2.9 | 모듈 28 + 끝 부속 2; 예비는 파일 |
| 레버 봉 끝 마개 | 출력 | PETG Ø4.0, 길이 1.2, 이음 쪽 끝 핀 보스 구멍(모듈은 왼쪽 x0.2~1.4)에 핀 면과 같게 눌러 끼움; 반대쪽 끝 핀은 막힌 벽 1.2 | 1 | 9 | 0.05 | 모듈 7 + 끝 부속 2 |
| 출력 공구 (악기당 1벌, 10.1장) | 출력 | 벤치 지그 받침(T1a), 높이 블록(T1b), 캡스턴 벤치 게이지 = 가짜 레버(T2), 밸런스 핀 높이 게이지(T3) — 형상·기준·쓰는 법·출력은 10.1장 | 0 | 4 | 38.4 / 10.3 / 13.3 / 6.3 | 악기당; 합계 68 g, 약 8시간 |
| 육각 렌치 2.0 | 공구 | M3 ISO 7380 캡스턴 돌림 (벤치에서만) | 0 | 1 | 10.0 | 악기당 |
| 가림판 띠 | 출력 | PETG 1.2T, z45.5(흑 노치 z57.5)~z72.85, 윗판 앞 턱에 걸침 | 1 | 9 | 6.3 | 모듈 7 + 끝 부속 2 |
| 센서 바 | 출력 | v3 (흑 낮은 구간 ±7.0); 끝 부속: 왼쪽 x0.5~46.5 (A#0 낮은 구간), 오른쪽 x0.5~23.0 | 1 | 9 | 17.0 | 모듈 7 + 끝 부속 2 (v3 단면) |
| 강철 블록 SS400 9T×19×40 | 구매 | 평철 9T×19를 40으로 절단(모따기 없음, 버 제거), 두께 8.9~9.1만 씀(캘리퍼스; 캐리어 주머니 9.2, 접착층 한쪽 0.10); 두 19×40 옆면에 MS 폴리머를 얇게 바르고 밑에서 스냅으로 끼워 접착(r4.4 고침 2b, 10장 4단계) | 12 | 90 | 53.69 | 88 + 예비 2 |
| 건반 봉 SUS304 Ø4 | 구매 | h9, 길이 161.4 ± 0.2 (끝 부속: 왼쪽 약 45, 오른쪽 약 21) | 1 | 10 | 16.08 | 모듈 7 + 끝 2 + 예비 1 |
| 레버 봉 SUS304 Ø4 | 구매 | h9 (풀림재 항복 205 MPa로 충분), 길이 161.4 ± 0.2 (끝 부속: 왼쪽 45.9, 오른쪽 22.2) — 건반 봉과 같은 4 m 봉 | 1 | 10 | 16.08 | 모듈 7 + 끝 2 + 예비 1 |
| 밸런스 핀 ISO 2338 Ø2×12 | 구매 | SUS, y135.3, 출력 높이 게이지로 꼭대기 z23.30 | 12 | 92 | 0.3 | 예비 4 |
| 캡스턴 M3×6 ISO 7380 + M3 너트 | 구매 | SUS 버튼헤드, 너트 트랩, 벤치 게이지(T2)로 꼭대기 z30.90(정착 쉼; 건반 좌표 z31.0) | 12 | 92 | 0.95 | 예비 4 (각 2개 부품) |
| 비틀림 보조 스프링 — 미스미 C-UA90R5-3-0.5 | 구매 | 한국미스미 경제형 토션스프링 C-UA90R5-3-0.5: SUS304-WPB d0.5, 안지름 5, 3권, 암 각 90° 오른쪽 감기, 암 50/50 — 두 암을 잘라 씀: 긴 다리 22.3 (코일 중심에서 끝까지, 코일을 떠나는 점에서 22.13), 짧은 다리 8.0 (코일을 떠나는 점에서, 굽히지 않음 — r4.5 고침 2: 레버의 가둠 홈에 끝까지 들어가 두 점으로 짝 힘을 냄, 코일은 봉에 닿지 않음). 잘린 뒤 k_t 8.44 N·mm/rad, b = 0에서 28.4° 감아 설치(쉼 4.19 N·mm); 긴 다리가 코일의 +x(오른쪽) 끝에 오게, 짧은 다리 끝부터 홈을 따라 밀어 넣음 — 반대로 넣으면 짧은 다리가 홈에 맞지 않음 | 12 | 100 | 0.134 | 88 + 단계 0 시험 4(시험 8에 1, 시험 13에 3) = 92 + 예비 8, 100개 × 310원(282원 + VAT) = 31,000원; 다리 200곳을 경선 니퍼로 자름 |
| 경선(피아노선) 니퍼 | 공구 | SUS304-WPB d0.5 경강선을 자르는 니퍼(일반 니퍼는 날이 이 빠짐); 스프링 100개 × 다리 2 = 200곳, 자른 끝의 거스러미는 줄로 | 0 | 1 | 80.0 | 악기당 (r4.5, 미스미 스프링) |
| 센서 자석 Ø5×2 N35 | 구매 | v3, y67 | 12 | 92 | 0.29 | v3 그대로 |
| 제어 기판 나사 M3×6 스텐 유두 렌치볼트 (ISO 7380 버튼헤드) | 구매 | SUS, 머리 Ø5.7 × 1.65 (모델은 Ø5.7 × 3.0 외곽 — DIN 912 Ø5.5 × 3.0로 사도 들어감); r4.4 고침 2b: 밑에서 기판을 지나(머리는 기판 밑) 기판 위에 매단 보스 (50.0,149.0)·(114.5,192.5)의 Ø2.5 막힌 구멍(z15.4까지)에 직접 탭 = 기판 1.6 + 보스 4.4; 나머지 2곳은 매단 보스의 위치 핀 Ø2.8(기판 구멍으로 아래로) | 2 | 14 | 0.6 | v3.2 구매 목록 L35 (20개 800원, 이미 기본 구성에 있음 → 비용 변화 0); 끝 부속에는 없음 |
| 업스톱 패드 | 구매(재단) | 미세셀 우레탄 폼 6T (25 % 압축 0.36 MPa) + 펠트 1T, 6×12.2 (면 길이 = y 12 / cos 11.36°), 쐐기에 접착 | 12 | 100 | 0.155 | 예비 12 |
| 펠트·천 (캡스턴 2T, 쉼 1.5T, 앞 펠트 2T + PU 1T, 키퍼 2T, 노치·핀 홈·탭 천 0.5T) | 소모 | 양모 펠트, 부싱 천; 쉼 펠트 8.0×2.7, F·F#만 USB 홈 옆 F 4.76×2.7 (x71.69~76.45), F# 4.39×2.7 (x91.55~95.94) (홈 위로 나오지 않게) | 1 | 1 | 1.0 | 묶음 |
| PET 심 0.1 (OHP 필름 6×12.2) | 소모 | 패드 밑 업스톱 시점 조정 (패드와 같은 크기) | 0 | 50 | 0.01 | 필요한 만큼 |
| MS 폴리머(하이브리드) 탄성 접착제 | 소모 | 강철 블록의 두 19×40 옆면 ↔ 캐리어 옆벽(0.7) 접착, 접착층 한쪽 0.10 (주머니 9.2 − 강철 9.0); 전단 탄성 G 약 1 MPa, 설계 겹침 전단 1.5 MPa(단계 0 시험 20); 면 #120 사포 + 알코올, 블록당 약 0.2 mL, 24 h 굳힘. 5분 에폭시(단단함)는 쓰지 않음 — 열팽창 차이로 떨어짐(1e장 고침 2b) | 0 | 1 | 80.0 | 튜브 약 80 mL 1개 (추정 8,000원) |

모듈 출력 589 g + 서포트 114 g, 모듈 무게 1.37 kg. 88건반 본체 약 10.6 kg(v3 4.5 kg, r3 15.3 kg). 강철 블록 90개 4.83 kg, 봉 0.27 kg.

## 5. 치수표 (geometry.json `dims`와 같은 번호)

**반올림 (r4.4, 한 규칙)**: 이 문서의 모든 표·글과 geometry.json의 치수는 보인 자리에서 반올림한다. 딱 절반이면 0에서 먼 쪽으로 올린다(0.955 → 0.96, 13.525 → 13.53, −0.955 → −0.96). 도우미는 하나다. `export_geo.hu`가 Decimal로 먼저 소수 6자리에서 이진 오차를 없애고 이 규칙으로 자른다. `export_geo.pf`는 모든 `%.Nf` 서식의 숫자를 `hu`로 거친다(이 판부터 `%s`로 찍는 목록 안의 실수도 소수 6자리로 줄임). `make_design_md.py`와 `export_geo.py`의 모든 숫자 서식이 이 둘을 쓴다. metrics.json은 소수 6자리로 저장된다(`run_all.py`의 `clean`, r4.4 고침 2). 그래서 이 문서가 저장값에서 찍은 숫자와 모델 참값 사이에 끝자리 차이가 없다.

**규칙 밖에 남은 글**: `run_all.py`가 직접 쓰는 글(results.txt, metrics.json `checks`의 결과 글, parts_list.json 사양 글 대부분)은 아직 옛 `%` 서식이다. 참값이 딱 절반이면 끝자리가 1 작게 보일 수 있다. 이 판에서 그런 곳은 둘이다. (1) 0.2장 ‘패드 쐐기·패드’ 행: run_all 글은 ‘쐐기 1.42, 패드 1.43 (끝 부속 1.43)’이고, 이 문서는 저장값 1.425를 규칙대로 다시 썼다(1.43). (2) 건반 뺀 레버가 떨어지는 각: 0.25° 격자라 참값이 딱 절반이다. results.txt는 30.2° · 13.2°, 이 문서는 30.3° · 13.3°다. 부품표의 칼라 길이 글은 r4.4 고침 2부터 `export_geo.pf`로 써서 이 문서와 같다.

**이 규칙으로 바뀐 칸 (지금 모델, 옛 `%` 서식 → 규칙; 모델 수치는 같음)**: geometry.json 치수 35칸 — KC·KC#·P14 0.95 → 0.96; KC# 17.21 → 17.22; KC# 25.21 → 25.22; KC# 21.21 → 21.22; KC#·KD·P14 1.02 → 1.03; KD 30.03 → 30.04; KD 38.03 → 38.04; KD# 45.28 → 45.29; KD# 53.28 → 53.29; KD# 49.28 → 49.29; KD#·KE·P14 1.50 → 1.51; KB 151.97 → 151.98; KB 159.97 → 159.98; P13 126.12 → 126.13; P14 0.29 → 0.30; P20 15.73 → 15.74; P20 43.80 → 43.81; P20 54.76 → 54.77. 이 문서의 글 22칸 — 0.2장 1.42 → 1.43; 1장·1d-2장·11장 30.2 → 30.3; 1a장·고침 2·2.2장·10장·18장 0.29 → 0.30; 1d-2장 20.52 → 20.53; 1d-2장 3.58 → 3.59; 1d-2장 13.72 → 13.73; 1d-2장·11장 13.2 → 13.3; 4장 0.95 → 0.96; 4장 1.02 → 1.03; 4장 1.50 → 1.51. 기록은 `work_doc44/r3/round_cells.json`이다. 치수는 지금 모델에서 치수표를 다시 만들어 옛 서식과 비교했다(`dims_cmp.py`). 글은 이 문서를 옛 서식으로 다시 그려 비교했다(`run_md_old.py`). r4.4 고침 2 전의 목록(`work_doc44/round_cells.json`)과 다른 것은 모델 값이 바뀌었기 때문이다(칼라 0.76 이상, 쐐기 +0.04, metrics 6자리).

### 평면 P

| 번호 | 항목 | 값 | 단위 | 기준 | 비고 |
|---|---|---|---|---|---|
| P01 | 옥타브 모듈 폭 | 164.5 | mm | x=0 C 왼쪽 명목 경계 → 164.5 | v3 P01 유지 |
| P02 | 백건 피치 | 23.5 | mm | 백건 경계 x=0/23.5/…/164.5 | v3 유지 |
| P03 | 백건 헤드 폭 | 22.04 | mm | y0~50 | 틈 1.46: 공차 0.3 + 핀 요 ±0.10 + 탭 옆 놀음 ±0.05 뒤 1.0 |
| P04 | 백건-백건 틈 (헤드 / E-F·B-C 꼬리) | 1.46 / 1.64 | mm | 헤드 사이 / 꼬리 사이 |  |
| P05 | 흑건 밑폭 / 윗면 폭 | 10.4 / 9.5 | mm | 흑건 슬롯 13.708 가운데 |  |
| P07 | 흑건-백건 꼬리 틈 | 1.654 | mm | 흑건 옆면 ~ 이웃 백건 꼬리 | v3 1.354 |
| P10 | 레버 중심 오프셋 최대 | 1.83 (실제 꼬리 중심 기준) / 1.67 (v3 센서 중심 기준) | mm | 레버 중심 − 건반 꼬리 중심 | 빔·블록이 레버를 따라감, 꼬리 안 (r3 P10은 v3 중심 기준이었음) |
| P11 | 레버(캐리어) 폭 | 10.6 | mm | 레버 중심 ±5.3 | 강철 9 + 접착층 0.10×2 + 옆벽 0.7×2 (r4.4 고침 2b: 주머니 9.2; 앞·뒷벽 0.8), 단면은 백·흑 공통; 허브 칼라 길이가 위치마다 달라(P14) 캐리어는 위치별(옆벽에 음 이름) |
| P12 | 핀(지느러미) 5장 x | x0.20~1.80; x40.76~42.56; x82.42~84.22; x123.03~124.83; x162.70~164.30 | mm | 끝 1.6, 안쪽 1.8, y176~209 (y152~176은 양쪽 0.1 얇은 앞 연장), 윗판 밑까지 | B-C 이음(양 끝)·D-D#·F-F#·G#-A; 레버 봉 스팬 40.7 / 41.7 / 40.6 / 39.6; F\|F# 핀은 y148.6~170.7에서 기판 앞 홈을 지나 내려감(r4.1: 바닥 z5까지; r4.4 고침 2b: 기판 밑 바닥이 뚫려 z3까지, 킬 y144.5~148.6 z3~19.3로 밸런스 레일 뒷면에 붙음; r4.5 고침 2: 이 핀만 앞끝 y152 → y148.6, 바닥부터 윗판까지), r4.3: 그 뒤 y170.7~209는 뒷벽까지 z21.5부터 매달림(USB 플러그 위 포함; r4.2는 y196.8부터 얇은 선반 z18.55까지) |
| P13 | 패드 바 x (핀 칸마다 1개) | x3.10~39.46; x43.86~81.12; x85.52~121.73; x126.13~161.40 | mm | y146.5~185.0 (뒤끝이 윗판 계단 y185.0에 닿음); 앞부분 z67.35~68.85는 y167.0까지, 아래 계단 y165.5부터 z65.85~67.35 (계단 y165.5~167.0는 두께 3.0) | r4.2: 윗 계단이 윗판 홈 끝(y168.0)보다 1.0 앞 (r4.1은 y169.5까지라 윗판과 1.5×1.5 겹침). 양쪽 L 레일 = 웹 폭 1.0(y160~185.0, 윗판 밑에서 z64.75까지; 홈 구간 y160~168은 홈 천장 z68.85부터) + 립 1.3×0.8(z64.75~65.55, y163.5~185.0; 바 가장자리 밑 1.0 겹침, 바 밑면과 0.3 띄움). 바 가장자리마다 출력 잎 혀 0.6×1.6×8(y175~183, 뿌리는 뒤, 앞 끝 돌기 0.8가 립 위에 얹힘; 주위 0.4 틈으로 잘림) 0.3 눌림 = 잎마다 0.10 N, 바를 윗판 자리에 밀어 올림 (상시 굽힘 8.2 MPa); 앞으로 밀어 뺌 (21.5 mm부터 윗판에 밀어 올림); r4.4: 웹 앞 아래 모서리(y160.0, z64.75)를 1.0×45° 모따기 (칸 가장자리 캐리어 옆벽이 ff에서 지나감) |
| P14 | 레버 허브 칼라 (r3 C-링 대신) | C 0.00/0.96; C# 0.96/1.03; D 1.03/0.00; D# 0.00/1.51; E 1.51/0.93; F 0.93/0.00; F# 0.00/1.16; G 1.16/0.76; G# 0.76/0.00; A 0.00/0.76; A# 0.76/0.76; B 0.76/0.00 | mm | 허브 옆면에서 왼/오 | 레버-레버 링(≥ 1.50 + 축 놀음 몫)을 양쪽 허브에 반씩에서 0.05씩 짧게, 단 r4.4 고침 2: 한 칼라 0.76 이상(짝 합 1.52 이상, 짝 사이 빈 틈 0.04 이상) — 칸마다 축 놀음 0.46 / 0.46 / 0.43 / 0.30; Ø6; 레버-핀 링은 핀 보스(+0.02); 레버가 제 무게로 자유롭게 돌지 않으면 칼라 면을 사포질 |
| P15 | 윗판 (r3 브리지 + 앞 받침판) | x0.2~164.3, y146.5~212 | mm | 핀 5장·뒷벽과 한 몸 | 앞 홈(패드 바 앞부분) 밑면 z68.85 (y146.5~168.0, 끝은 수직 면), 패드 구간 z67.35 (y168.0~185.0), 계단 y185.0(수직 면, 패드 바 뒤 멈춤) 뒤 z60.85 (두께 최대 12; 레버 봉 위는 스프링 다리 홈 위 1.3); 가림판 걸이 턱 1.5×1.0 |
| P16 | 업스톱 패드 | y170~182(면의 y 폭), 레버마다 폭 6 (윗 립 사이 7.4); 재단 6 × 12.2 (면을 따라 잰 길이 백 12.24 / 흑 12.17) | mm | 강철 윗면 위 | 미세셀 우레탄 6T + 펠트 1T, 면은 1 N 정착 바닥의 강철 윗면과 평행 (면 기울기 11.36° / 9.63°라 y 12.0 = 면 12.2) |
| P17 | 패드 쐐기 (패드 바에 출력) | 백 0.35~2.76, 흑 1.50~3.54; 끝 부속 A0 0.29~2.72; A#0 1.50~3.54; B0 0.36~2.77; C8 0.26~2.70 | mm | 패드 뒷면 ~ 패드 바 밑면 | r3 패드 홀더·흑 스페이서 17개를 대신함; r4.2: 끝 부속 건반은 자기 1 N 정착 바닥에 평행한 자기 면(동역학과 같은 면)으로 쐐기를 출력 — 쐐기 뒤끝 ↔ 윗판 계단 1.62, 쐐기·패드 ↔ 레일 립 1.43 |
| P18 | 비틀림 보조 스프링 자리 | 허브 가운데 주머니 Ø6.6×3.0 (레버 x ±1.5) + r4.5 고침 2: 짧은 다리 가둠 홈 폭 0.70 (레버 기준 136.83° 방향, 축에서 2.511~3.211 띠, 주머니 안 -0.5에서 허브 벽을 지나 웹 안 막힌 끝까지 — 다리 끝 너머 0.3), 웹 밑면을 3.79 깎음; 넣는 슬롯 316.83° 방향 ±3.25(다리를 따라); 긴 다리 창 = 35° 방향 윗면 +2.6까지 뒤로 열림; 뒷벽 면의 출력 보스 y207.8~209.0 × 폭 4.4(레버 x +0.8 중심 = 긴 다리 자리, ±2.2) × z47~윗판 밑, 그 안 세로 홈 y207.8~211.0 z47~58 (폭 2.4, 깊이 3.2 — 뒷벽 안으로 2.0, 뒷벽 1.0 남음; 입구 0.5×45° 모따기는 홈 x 면의 보스 밑면 z47~47.5, 보스 밑면에서 열림) | mm | 레버마다 1 | r4.5 고침 2 (검증 major, 코일 뜸): r4.5의 짧은 다리 2.5가 한 면에만 기대면 다리 힘이 코일(ID 5.0)을 Ø4 봉 쪽으로 0.47 밀어 다리가 떨어지고 스프링이 13.4° 풀려 쉼 2.18 N·mm(설계 4.19)가 되며 봉에 2.2 N으로 문질러짐 → 짧은 다리 8.0를 폭 0.70 홈에 가둬 끝(바깥 면)과 주머니 가장자리(안쪽 면) 두 점(팔 5.75)으로 짝 힘 0.73 N을 받음: 코일은 제 다리에 매달려 봉과 틈 0.43(쉼)·0.33(손 25°). 넣기: 봉 넣기 전, 짧은 다리 끝부터 홈을 따라 밀면 코일이 넣는 슬롯으로 주머니에 앉음 (짧은 다리 ↔ 홈 면 0.100; 홈이 0.15 좁게 나와도 지나감). 짧은 다리는 굽히지 않고 코일 접선(레버 기준 228.82°, y201.48 z31.48)에서 끝 y195.46 z36.75까지. 긴 다리 22.3(축에서 끝까지)는 코일 뒤쪽 접선(y205.87 z32.91)에서 홈 바닥 끝(y210.75 z54.50)까지, 레버 -31.3°~18.0° 내내 창 안 (면까지 최소 0.57 + 선 반지름 + 0.2); 보스 면 y207.8에는 z41.45(보스 밑 z47 아래)에서 닿아 홈으로 밑에서 들어감; 긴 다리는 코일 +x 끝(x +0.8)에서 곧게 홈으로 — 홈·보스를 그 x에 맞춤(코일 축 놀음 0.44 + 레버 놀음 0.41 ≤ 받는 폭 1.45, 여유 0.61). b=0이면 28.4° 감김; 건반 빠진 레버(-31.3°)에서 풀린 다리 끝이 홈 입구 안 1.88 |
| P19 | 뒤 선반 / 리브 | y195.8~209.0 / 리브 y196.8~ | mm | 리브 x 8.0, 22.0, 36.0, 50.0, 62.0, 75.0, 93.0, 104.0, 116.0, 126.0, 136.0, 150.0 | 두께 2.0, 윗면 z20.054; r4.3: USB 플러그 위는 앞뒤로 뚫린 홈 x76.45~91.55(플러그 ±1.3; r4.2는 x75.6~92.4 두께 1.5, 밑면 z18.55가 올라간 플러그 윗면 z18.3와 0.25) |
| P20 | 밸런스 레일 | y132.3~144.5, 홈 중심 y141; 블록 밑은 윗면 z19.0로 낮춤, 블록 사이 봉 받침 11개; r4.4 고침 2: 백건 블록 밑은 y137.4 뒤를 z18.90까지 더 낮춘 포켓(핀 줄 y135.3는 z19.0 그대로); 흑건 블록 밑은 y137.2 뒤를 z18.80까지 더 낮춘 포켓(핀 줄 y135.3는 z19.0 그대로) | mm | x0.3~164.2 | 받침 x 14.64~15.74, 26.70~27.79, 42.71~43.81, 54.77~55.86, 69.96~71.04, 84.00~85.09, 96.05~97.15, 110.93~112.02, 122.98~124.07, 137.85~138.95, 149.91~151.00; 핀 구멍 앞벽 2.0, 홈 양 끝 벽 1.0; 리본 차선 x59.0~82.0(레일 밑면 z10, r4.3: 16심 리본 20.32에 양옆 1.32 / 1.36, r4.2 x60~82); r4.4: 리본은 차선 안에서 SB J201 가운데 x70.48로 곧게, 레일 뒤(y144.5)부터 기판 밑 z5~9로 J301까지 — J301 쪽 끝 6 mm만 -0.31 비껴 꽂음(차선 밖) |
| P21 | 건반 봉 Ø4 SUS304 | x1.55~162.95 (길이 161.4 ± 0.2) | mm | 홈 끝 벽 x1.3 / 163.2 |  |
| P22 | 레버 봉 Ø4 SUS304 h9 | x1.5~162.9 (길이 161.4 ± 0.2) | mm | 핀 5장의 출력 보스(Ø3.9 → Ø4.0 드릴) 관통 | 왼쪽 끝 핀에 출력 마개 1.2, 오른쪽 끝 핀은 막힌 벽 1.2; 건반 봉과 같은 4 m 봉; 최대 응력 88 MPa < 풀림재 항복 205 |
| P23 | 제어 기판 (v3 만능기판) | x47.25~117.25, y145.5~195.5, z9.0~10.6; r4.1 앞 모서리에서 연 홈 x81.92~84.72, y145.5~172.0 | mm | v3 P114 외곽 그대로 (스탠드오프는 r4.4 P35) | r4.3: 부품·배선 금지 x81.22~85.42, y145.5~173.2(핀 면에서 1.2; r4.1 1.0) — BRD-01 배치는 이미 밖; 핀 발은 y170.7에서 끝나 홈 끝 y172.0와 1.3, RP2040-Zero 앞 모서리 y172.0와 1.3. r4.4: 금지 구역은 만능기판 위 핀·패드·배선에 대한 것이고, 핀 헤더에 선 RP2040-Zero PCB(z11.9~12.9)만 x81.22~85.42 × y172.0~173.2에 걸친다(그 안에 핀·패드·배선 없음; 헤더 열 x76.52 / x91.76; 매달린 핀 밑면 z21.5과 5.2). 받침 4곳 P35 |
| P24 | USB-C 플러그 외곽 | x77.75~90.25, y196.8~221.8, z10.7~18.3 | mm | v3 S37 (폭 12.5 · 높이 7.5 · 길이 25 이하) | r4.3: RP2040-Zero가 핀 헤더 위(+1.3)라 USB-C 중심 z14.5(v3 z13.2, r4.2 z9.45~16.95); 선반 홈·리브 x75.0 / x93.0·F\|F# 핀(z21.5부터)·뒷벽 개구(z21까지)와 1.30 이상; 뒤 케이블 통로(z0~22, v3) 안에서 3.7 여유. r4.4: 리셉터클이 제로 가장자리 밖으로 약 1.3(1.0~1.5) 나와 플러그 면 y196.8(r4.3 y195.5) — 선반 홈 양옆 1.30 / 1.30는 선반 y196.8~209.0 내내, 뒷벽 개구 x 3.75 / 위 2.70, 통로 y215~258에서 굽힘 25 뒤 11.2 남음 |
| P27 | 제어 기판 부품 (회로 BRD-01, r4.4 격자 x = 76.52 + 2.54i) | 부품 한계 z20(y145.8~194.5), 선반 앞 띠 z16.7(y194.5~195.5) | mm | 모듈 좌표, BRD-01 배치 | RP2040-Zero x75.14~93.14 y172.0~195.5 핀 헤더 위(PCB z11.9~12.9, 윗면 부품 z16.3 이하 — 핀 끝은 자름), USB-C 리셉터클 x79.53~88.47 y189.5~196.8 z12.9~16.1(제로 가장자리 밖으로 1.3); 4067 모듈 x54.93~72.71 y152.0~192.64 핀 헤더 위 z20 이하; J301 리본 2×8 x61.28~79.06 y148.19/150.73 아랫면 납땜(윗면은 납땜 자국 z12.0 이하), 16심 20.32 폭 리본은 기판 밑 z5~9; J302 EXT 1×6 x94.30~107.00 y193.91(선은 아랫면에서 납땜, 기판 밑 z5~9 → USB 터널 플러그 밑 → 뒷벽 개구). r4.3 값: 제로 x75.0, 리셉터클 y188.2~195.5, 4067 x53.3~71.1 y152.4~193.0, J301 x61.59~79.37 y148.59/151.13 윗면, J302 x95.25~107.95 y193.04 |
| P35 | 제어 기판 보스 (프레임 출력, r4.4 고침 2b: 기판 위에 매달림) · 바닥 구멍 | Ø6 보스 4곳(나사 (50.0, 149.0) · (114.5, 192.5), 위치 핀 (114.5, 149.0) · (50.0, 192.5)), 기판 윗면 z10.6에 닿음; 앞 2곳은 밸런스 레일 뒷면 y144.5까지 받침(윗면 z17.0), 뒤 2곳은 선반 리브 x50.0·x116.0 앞면 y196.8와 선반 밑면 z18.05까지; 바닥 구멍 x46.25~118.25 y144.5~196.5 (리셉터클 뒤 x78.53~89.47는 y197.8까지) | mm | 모듈 좌표 (회로 BRD-01 구멍 자리 그대로) | 기판은 모듈을 뒤집어 바닥 구멍으로 밑에서 넣는다(홈이 F\|F# 핀 발·킬을 따라 올라감, 길 위 최소 0.60); M3×6(v3.2 L35 ISO 7380, 머리 Ø5.7 × 1.65)을 밑에서 — 머리는 기판 밑 z7.35~9.0, 기판 1.6 + 보스 4.4, Ø2.5 막힌 구멍 z15.4까지(끝 z15.0); 위치 핀 Ø2.8가 보스에서 기판 Ø3.0 구멍으로 아래로(끝 z7.8, 반경 놀음 0.10). M3 머리 ↔ 밸런스 레일 뒷면 1.65, ↔ 선반 리브 1.54 (리브 축 위 1.45), 머리 가장자리가 기판 모서리 밖 0.10; 가장 가까운 BRD-01 부품 1.93; r4.4 고침 2까지의 바닥 스탠드오프(Ø6 × z5~9)는 기판이 들어갈 길이 없어 뺌 |
| P36 | 센서 기판 받침·센서 바 고정 (v3 P111·P112·P113; r4.4 받침, r4.5 회로 2차 오른쪽 턱) | 기둥 x0.5~6.0 y59.0~77.5, 앞 리브 y61.0~62.8, 뒤 리브 y73.2~75.5 (x6.0~158.5), 윗면 z7.0; 오른쪽 턱 y59.0~63.4 · y70.6~77.5: 립 x161.5~163.0 z13.6~15.1, 기둥 x163.0~164.3 z5.0~15.1 | mm | 센서 기판 SB x1.0~162.6 y60.65~75.89 z7.0~8.6 (v3 P108), 센서 바 x0.5~162.9 z8.6~13.6 (v3 P107) | r4.4: 뒤 리브 틈 x59~82(v3 x60~82) = 리본 차선: 리본 x60.32~80.64 양옆 1.32 / 1.36 (v3 틈이면 0.32), J201 패드 1.69 / 1.73. r4.5 회로 2차(8번): 바·기판의 왼쪽 끝은 M3×10 자가 탭 2개(3.0, 61.9)·(3.0, 74.6)로 기둥에, 오른쪽 끝은 프레임과 한 몸인 오른쪽 턱(v3 P112, r4 내보냄에서 빠졌던 것; 질량은 v3 프레임 175 g에 이미 있음)이 잡는다: 립 밑면 z13.6 = 백 구간 바 윗면, 바 끝 x162.9 위를 1.4 덮음(15.8 mm²), 기둥은 바 끝과 0.1 · 기판 끝과 0.4, 이음 면에서 0.2 안(핀과 같은 0.2); 두 조각은 B 센서 리드 줄(y63.9~70.1)을 0.5 / 0.5 피하고 립은 B 리드 구멍 열 x160.65에서 0.85 떨어짐. 바·기판은 모듈 하나를 빼 놓고(왼쪽 이웃 없이) 1.5 mm 왼쪽에 내려놓은 뒤 오른쪽으로 밀어 턱 밑에 넣고 왼쪽 나사를 조인다(v3 절차). 가장 가까운 움직이는 부품 1.95 (공차 뒤 1.65, 건반 B 꼬리 오른 옆벽 ff 최대), 이음매 너머 이웃 모듈 0.70 · ER 0.70(고정끼리, 이음 면 규칙 0.4 이상). 끝 부속 바(EL x0.5~46.5, ER x0.5~23.0)는 턱 없이 같은 왼쪽 M3×10 2개와 리브로 잡는다(46.0 / 22.5 mm로 짧고, 기판 넣기로 뒤집지 않음); 끝 부속은 A02·A03 |
| P25 | 센서 바 흑 낮은 구간 | 7.0 | mm | 흑건 중심 ± | v3 ±6.0 → ±7.0 |
| P26 | 가림판 띠 | y144.3~145.5, 걸이 립 y145.5~148.0 | mm | 흑건 자리 노치 ±7.0 | 윗판 앞 턱에 얹혀 들어서 뺌 (핀·자석 없음) |
| P28 | 꼬리 쉼 패드 | y196.3~199.0 | mm | 빔 폭 8 (F·F#는 아래) | 펠트 1.5T + 종이 펀칭 0.1×2; r4.4: USB 홈에 걸리는 펠트는 홈 가장자리에서 자르고 반대쪽으로 꼬리 끝까지: F x71.69~76.45(59 % 앉음, r4.3 x71.69~79.69 중 59 %), F# x91.55~95.94(55 % 앉음, r4.3 x86.94~94.94 중 42 %) |
| P29 | 자석 y (백·흑) | 67.0 | mm | 소자 열 y67 바로 위 |  |
| P30 | 흑건 앞면 (밑면/윗면 앞 모서리) | 54.2 / 55.2 | mm | y0 기준 |  |
| P31 | 가이드 탭 (백/흑) | 앞면 14.8 / 80.8, 폭 7.5 / 6.9 | mm | 크로스바 뒷면 + 0.8 | 천 0.5T 양쪽: 백 8.6 리브 사이, 흑 8.0 낮은 벽 사이 → 옆 놀음 ±0.05 (r3 흑 7.5는 0.25 억지끼움) |
| P32 | 밸런스 핀 | ISO 2338 Ø2.0×12, y135.3, 꼭대기 z23.30 ± 0.1 (출력 높이 게이지) | mm | 블록 가운데 x | 블록 밑 홈 출력 폭 3.2(천 0.5T 양쪽 → 2.2), 깊이 2.5, y134.0~138.0 앞이 열림; 핀 ↔ 입술 벽 1.39 (r3 0.19~0.26) |
| P34 | 키퍼 훅·펠트 폭 | 5.2 | mm | 탭 중심 ±2.6 |  |

### 건반별 평면 K

| 번호 | 항목 | 값 | 단위 | 기준 | 비고 |
|---|---|---|---|---|---|
| KC | C 건반 평면 x | 8.525 | mm | 레버 중심 x | 헤드 x0.73~22.77(y0~50), 꼬리 x0.820~14.361(y50~146), 밸런스 블록 x2.02~13.16(y134~146, 핀 홈 가운데 x7.59), 빔·캡스턴·레버 중심 x8.525(빔 x4.53~12.53), 가이드 탭 중심 x11.75, 자석 x7.431; 캡스턴 y188.34; 레버 허브 칼라 왼/오 0.00/0.96 |
| KC# | C# 건반 평면 x | 21.215 | mm | 레버 중심 x | 밑면 x16.015~26.415(y54.2~146), 윗면 x16.465~25.965, 밸런스 블록 x17.22~25.22(핀 홈 가운데 x21.22), 빔·캡스턴·레버 중심 x21.215(빔 x17.22~25.22), 탭(6.9)·자석 x21.215, 자석 보스 x17.22~25.22(옆벽과 붙음); 캡스턴 y180.31; 레버 허브 칼라 왼/오 0.96/1.03 |
| KD | D 건반 평면 x | 34.035 | mm | 레버 중심 x | 헤드 x24.23~46.27(y0~50), 꼬리 x28.069~42.431(y50~146), 밸런스 블록 x29.27~41.23(y134~146, 핀 홈 가운데 x35.25), 빔·캡스턴·레버 중심 x34.035(빔 x30.04~38.04), 가이드 탭 중심 x35.25, 자석 x35.250; 캡스턴 y188.34; 레버 허브 칼라 왼/오 1.03/0.00 |
| KD# | D# 건반 평면 x | 49.285 | mm | 레버 중심 x | 밑면 x44.085~54.485(y54.2~146), 윗면 x44.535~54.035, 밸런스 블록 x45.29~53.29(핀 홈 가운데 x49.29), 빔·캡스턴·레버 중심 x49.285(빔 x45.29~53.29), 탭(6.9)·자석 x49.285, 자석 보스 x45.29~53.29(옆벽과 붙음); 캡스턴 y180.31; 레버 허브 칼라 왼/오 0.00/1.51 |
| KE | E 건반 평면 x | 63.07 | mm | 레버 중심 x | 헤드 x47.73~69.77(y0~50), 꼬리 x56.139~69.680(y50~146), 밸런스 블록 x57.34~68.48(y134~146, 핀 홈 가운데 x62.91), 빔·캡스턴·레버 중심 x63.070(빔 x59.07~67.07), 가이드 탭 중심 x58.75, 자석 x63.070; r4.4 고침 2·2b: 빔·얇은 꼬리 밑면 y184.0~195.8을 0.10 올림 (최악 재료까지의 복귀 넘침에서 제어 기판 부품 구역 z20과 1.3); 캡스턴 y188.34; 레버 허브 칼라 왼/오 1.51/0.93 |
| KF | F 건반 평면 x | 75.693 | mm | 레버 중심 x | 헤드 x71.23~93.27(y0~50), 꼬리 x71.320~83.719(y50~146), 밸런스 블록 x72.52~82.52(y134~146, 핀 홈 가운데 x77.52), 빔·캡스턴·레버 중심 x75.693(빔 x71.69~79.69), 가이드 탭 중심 x82.25, 자석 x77.359; r4.4 고침 2·2b: 빔·얇은 꼬리 밑면 y176.0~195.8을 0.15 올림 (최악 재료까지의 복귀 넘침에서 제어 기판 부품 구역 z20과 1.3); 캡스턴 y188.34; 레버 허브 칼라 왼/오 0.93/0.00 |
| KF# | F# 건반 평면 x | 90.943 | mm | 레버 중심 x | 밑면 x85.373~95.773(y54.2~146), 윗면 x85.823~95.323, 밸런스 블록 x86.57~94.57(핀 홈 가운데 x90.57), 빔·캡스턴·레버 중심 x90.943(빔 x86.94~94.94), 탭(6.9)·자석 x90.573, 자석 보스 x86.57~94.57(옆벽과 붙음); r4.4 고침 2·2b: 빔·얇은 꼬리 밑면 y184.0~195.8을 0.10 올림 (최악 재료까지의 복귀 넘침에서 제어 기판 부품 구역 z20과 1.3); 캡스턴 y180.31; 레버 허브 칼라 왼/오 0.00/1.16 |
| KG | G 건반 평면 x | 104.037 | mm | 레버 중심 x | 헤드 x94.73~116.77(y0~50), 꼬리 x97.427~110.646(y50~146), 밸런스 블록 x98.63~109.45(y134~146, 핀 홈 가운데 x104.04), 빔·캡스턴·레버 중심 x104.037(빔 x100.04~108.04), 가이드 탭 중심 x105.75, 자석 x104.037; r4.4 고침 2·2b: 빔·얇은 꼬리 밑면 y184.0~195.8을 0.10 올림 (최악 재료까지의 복귀 넘침에서 제어 기판 부품 구역 z20과 1.3); 캡스턴 y188.34; 레버 허브 칼라 왼/오 1.16/0.76 |
| KG# | G# 건반 평면 x | 116.3 | mm | 레버 중심 x | 밑면 x112.300~122.700(y54.2~146), 윗면 x112.750~122.250, 밸런스 블록 x113.50~121.50(핀 홈 가운데 x117.50), 빔·캡스턴·레버 중심 x116.300(빔 x112.30~120.30), 탭(6.9)·자석 x117.500, 자석 보스 x113.50~121.50(옆벽과 붙음); 캡스턴 y180.31; 레버 허브 칼라 왼/오 0.76/0.00 |
| KA | A 건반 평면 x | 131.55 | mm | 레버 중심 x | 헤드 x118.23~140.27(y0~50), 꼬리 x124.354~137.573(y50~146), 밸런스 블록 x125.55~136.37(y134~146, 핀 홈 가운데 x130.96), 빔·캡스턴·레버 중심 x131.550(빔 x127.55~135.55), 가이드 탭 중심 x129.25, 자석 x130.964; 캡스턴 y188.34; 레버 허브 칼라 왼/오 0.00/0.76 |
| KA# | A# 건반 평면 x | 143.8 | mm | 레버 중심 x | 밑면 x139.227~149.627(y54.2~146), 윗면 x139.677~149.177, 밸런스 블록 x140.43~148.43(핀 홈 가운데 x144.43), 빔·캡스턴·레버 중심 x143.800(빔 x139.80~147.80), 탭(6.9)·자석 x144.427, 자석 보스 x140.43~148.43(옆벽과 붙음); 캡스턴 y180.31; 레버 허브 칼라 왼/오 0.76/0.76 |
| KB | B 건반 평면 x | 155.975 | mm | 레버 중심 x | 헤드 x141.73~163.77(y0~50), 꼬리 x151.281~163.680(y50~146), 밸런스 블록 x152.48~162.48(y134~146, 핀 홈 가운데 x157.48), 빔·캡스턴·레버 중심 x155.975(빔 x151.98~159.98), 가이드 탭 중심 x152.75, 자석 x157.641; 캡스턴 y188.34; 레버 허브 칼라 왼/오 0.76/0.00 |

### 측면 S

| 번호 | 항목 | 값 | 단위 | 기준 | 비고 |
|---|---|---|---|---|---|
| S01 | 바닥 EVA / 프레임 바닥판 | z0~3 / z3~5 | mm | v3 S01·S02 |  |
| S02 | 백건 윗면 / 밑면 / 흑건 윗면 | 43.5 / 23.5 / 55.5 | mm | 쉼 | v3 유지 |
| S03 | 건반 봉 중심 K | (141.0, 21.5) | mm | (y, z) | Ø4 SUS304 |
| S04 | 스냅 노치 | R2.55 + 천 0.5T → 유효 R2.05, 블록 밑면 z20.75 (봉 중심 아래 0.75) | mm | 중심 = K | 감싸는 각 223°, 입구 3.82, 쉼에서 입술 틈 0.07; 곧게 들리면 입술은 들림 0.20에서 닿고 0.80에서 빠짐 (흑건은 노치가 앞뒤로 밀려 들림 0.06에서도 입술 모서리가 닿음: 판정은 들림만); 빠짐 힘 1~2 N(단계 0 반지름 쿠폰으로 고름) |
| S05 | 봉 받침(크래들) 홈 | 입술 z20.5, 바닥 z19.50 | mm | y139.24~142.76 (R2.05) |  |
| S06 | 꼬리 옆벽 봉 위 도려냄 | y137~145, 밑면 z25.2 | mm | 건반 옆벽 |  |
| S07 | 숨은 빔 | z21.8~28.5, 폭 8 | mm | y146 → 캡스턴+4 |  |
| S08 | 캡스턴 (M3×6 ISO 7380 + 너트 트랩) | 백 y188.34, 흑 y180.31, 머리 꼭대기 z31.0 (건반 좌표 = 설계 자세) = 프레임 안 정착 쉼에서 백 z30.892 · 흑 z30.912 | mm | 빔 가운데 | 건반을 넣기 전 벤치 지그 T1a + 가짜 레버 T2(바늘 ↔ 읽기 턱)로 맞춤 (10.1장); r4.4 고침 2b: 지그 위 건반도 노치 천·쉼 펠트에 정착하므로 T2의 밑면·영점 받침은 정착 꼭대기 z30.90 면(고침 2까지 z31.0는 캡스턴을 백 0.108 · 흑 0.088 높게 맞췄음) |
| S09 | 얇은 꼬리 | z21.8~24.9, 끝 y199.0, 모따기 1.5 | mm |  | 폭 백 8 / 흑 10 |
| S10 | 뒤 선반 윗면 | 20.054 | mm | y195.8~209.0 | 쉼 펠트 1.5T + 펀칭 0.2를 넣어 맞춘 값 |
| S11 | 레버 봉 중심 L | (203.25, 33.5) | mm | (y, z) | Ø4 SUS304, 허브 R4.3, 구멍 Ø3.9 출력 → Ø4.0 드릴 |
| S12 | 강철 블록 SS400 9×19×40 | y150.0~190.0, z33.0~52.0, 모따기 없음 | mm | 쉼 (레버 0°) | 53.7 g (r3 9×50×21.5 = 75.8 g); 드러난 윗면 y153~190(윗 립 사이 7.2, y163~184는 전폭)의 가운데가 업스톱 접점 |
| S13 | 캐리어 | 앞면 y149.2, 윗면 z53.0, 앞 윗모서리 R3, 손톱 턱 1.0×1.5 (y148.2~, z51.5~53.0, R3 모서리를 채워 앞벽과 한 몸) | mm | 옆벽 0.8, 아래 립 y165부터, 뒤 바닥 y190.8~192.5 | 쉼 각 백 -1.09° / 흑 -0.55° |
| S14 | 캐리어 밑 펠트 띠 2T | y176.5~192.0, z31.0~33.0 | mm | 폭 7 | 흑연 가루 |
| S15 | 업스톱 패드 면 (백 / 흑) | y170 z58.64~y182 z56.23 / z57.45~z55.41 | mm | 면의 기울기 11.36° / 9.63° | 패드가 없는 1 N 정착 바닥(11.36° / 9.63°)의 강철 윗면과 평행, 법선 방향 -0.40 / -0.45 (레버가 먼저); 패드가 있는 실제 1 N 바닥은 10.75° / 8.97°라 면이 강철에 0.61° / 0.66° 기움 (12 mm에 0.13 / 0.14 mm) |
| S16 | 패드 쌓기 | 패드 7 + 쐐기 + 패드 바 1.5 | mm | 패드 면 ~ 패드 바 윗면(자리) z67.35 |  |
| S17 | 패드 바 자리 (패드 구간 윗판 밑면) | 67.35 | mm | z | 앞부분은 윗판 홈 속 z67.35~68.85 |
| S18 | 모듈 맨 위 (윗판 윗면) | 72.85 | mm | z | 그 위에 아무것도 없음 (v3 z59, r3 커버 z78.0 / 손나사 머리 z80.7) |
| S20 | 키퍼 펠트 밑면 | 26.6 | mm | 크로스바 윗면 + 1.5 | 펠트 2T; 훅을 r3보다 0.3 올림 |
| S21 | 백 앞 펠트 윗면 선 | (y1.5, z13.64)~(y9.0, z14.17) | mm | 딥에서 바닥판과 평행 | 펠트 2T + 저반발 PU 1T (e ≈ 0.20), y1.5~9.0로 자름 |
| S22 | 흑 앞 펠트 윗면 선 | (y54.5, z14.08)~(y59.0, z14.57) | mm |  | 같은 구성 |
| S23 | 딥 (백 y0 / 흑 앞 모서리) | 10.0 / 9.5 | mm |  | v3 유지; 1 N에서 흑건 앞이 펠트 위 0.27 (레버가 패드에 먼저) |
| S24 | 건반 회전각 (백 / 흑) | 4.04 / 6.22 | deg | K 기준 (강체 기구) | 1 N 정착 바닥(패드 있음) 3.98 / 5.99 (노치가 봉에 앉는 것까지 넣은 앞끝 기준 4.05 / 6.08) = geometry의 건반 side_dip (r4.4; r4.3은 두 색 모두 강체 값을 내보냄, 이제 side_dip_rigid), 2.5 m/s 최대 4.32 / 6.66, 복귀 넘침 -0.46 / -0.35 (F -0.53, F# -0.47) |
| S25 | 레버 회전각 (백 / 흑) | 12.64 / 10.27 | deg | L 기준 (강체 기구) | 1 N 정착 바닥 10.75 / 8.97, 최대 12.91 / 10.85, 복귀 넘침 -3.05 / -1.82 (F -3.31, F# -2.00; r4.4: 화음 자리·격자 포함) |
| S26 | 자석 이동 (백 / 흑) | 5.22 / 8.03 | mm | y67 | 바닥 간격 5.60 / 5.32, 최대 과다 누름 5.24 / 4.76 |
| S27 | 가림판 아래끝 (백 / 흑 노치) | 45.5 / 57.5 | mm |  | r3 z45.2 → 45.5 |
| S28 | 뒷벽 | y209~212, z5~72.85 | mm |  | USB 개구 x74~94 z5~21 (v3 그대로; r4.3 플러그 윗면 z18.3와 2.7); 안쪽 면에 스프링 홈 보스 12 (P18, 끝 부속 왼쪽 3 / 오른쪽 1) |
| S29 | 핀 높이 | z5~윗판 밑 (F\|F# 핀: y148.6~170.7은 기판 홈을 지나 z3부터(기판 밑 바닥 구멍, r4.4 고침 2b; 앞끝 y148.6은 r4.5 고침), 그 뒤 뒷벽까지 z21.5부터 매달림 — r4.3 USB 위도) | mm | y152~209 | 끝 핀은 도브테일 홈 위 z17.9부터 |
| S31 | 흑건 윗면 뒤끝 (가림판 밑) | y144.3~147.0에서 z55.5 → z54.1 (입술 두께 0.6, 밑면 z53.5 그대로) | mm | 흑건 5 + A#0 | r4.1: 패드 바를 뺄 때 흑 패드 아래 모서리(z55.40)가 흑건 뒤끝 윗면(z55.5)을 치던 것을 없앰; 가림판에 가려 보이지 않음 |
| S30 | 센서 소자 z (백 / 흑) | 12.68 / 10.15 | mm | v3 |  |

### 상세 D

| 번호 | 항목 | 값 | 단위 | 기준 | 비고 |
|---|---|---|---|---|---|
| D01 | 노치 라이닝 | 부싱 천 0.5T | mm | 노치 R2.55 안쪽 |  |
| D02 | 캡스턴 너트 트랩 | M3 육각 너트, 옆에서 끼움, 위 Ø2.8 자가 잠김 구멍 |  | 빔 안 | 1/8회전 = 캡스턴 0.0625 mm = 가짜 레버 T2 바늘 0.34 / 0.22 mm (백 / 흑, 10.1장) |
| D05 | 비틀림 보조 스프링 (기본) — 미스미 C-UA90R5-3-0.5 | 한국미스미 경제형 C-UA90R5-3-0.5: SUS304-WPB d0.50 · ID 5.0 · 3권(몸통 3.25권) · 암 각 90° 오른쪽 감기 · 암 50/50 → 두 다리를 잘라 씀: 긴 다리 22.3 (축에서 끝, 접선; 접점에서 22.13) / 짧은 다리 8.0 (접선, 굽힘 없음) | mm | k_t 8.44 N·mm/rad (E 186000, N_e 3.914), 자유각 -28.45° (b=0에서 28.45° 감김): 쉼 4.19, 바닥 6.03 N·mm | 응력 최대 685 MPa (Su 2150의 32 %, 손 들기 25°), 바닥 ID 4.83; 카탈로그 최대 사용각 55° 안(손 들기 53.4°)이나 토크는 카탈로그 55° 토크 7.52의 104 % (잘린 다리가 짧아 강성이 큼); 긴 다리가 코일 +x 끝에 오게 넣음 |
| D06 | 허브 칼라 / 핀 보스 | 칼라 Ø6 (P14) / 보스 Ø7, 황동 없음 | mm | 레버 허브 사이 / 핀 | 보스 길이 = 핀 + 레버-핀 링 + 0.02(r4.4 고침 2: 떠밀린 레버가 요와 함께 핀과 1.3; 끝 핀은 한쪽) |
| D07 | 캐리어 스냅 립 · 옆벽 · 접착 | 위 립 0.9×1.0: 앞 y150~163(앞 y150~153는 전폭 뚜껑), 뒤 y184~190(뒷벽까지); 옆벽 윗단 z53.0도 이 구간만, 그 사이 y163~184는 z49.4 (r4.4 고침 2: 강철 윗면보다 2.6 낮음, 패드 밑으로 지나감); 아래 립 1.0×1.0 (y165~176.5, 캡스턴 펠트 앞까지); 강철 뒤 아래는 뒤 바닥 y190.8~192.5 (두께 1.5); 옆벽 0.7(주머니 9.2), 강철은 두 19×40 옆면에 MS 폴리머를 바르고 밑에서 스냅으로 끼워 접착 (접착층 한쪽 0.10, 접착 면 1411 mm²; r4.4 고침 2b — 고침 2의 5분 에폭시는 열팽창 차이로 떨어짐) | mm | 레버 좌표 (레버 0°) | r4.4: 앞 립을 y168 → 163로 줄임 (r4.3 립 뒤끝이 1 N 바닥·ff에서 패드 옆 0.64, 공차 뒤 0.34) → 립 ↔ 패드 2.16, 패드 바·레일 1.81; 뒤 립 186 → 190 (캡스턴 힘이 강철 뒤끝을 립에 밀어 올림: 매 음 19.2 N → 뿌리 3.8 MPa, r4.3 2 mm 립이면 13.1 MPa); r4.1: 패드 옆에 립이 없어 패드 ↔ 캐리어 옆벽은 스윕에서 검사; r4.4 고침 2: 스냅만으로는 옆벽이 벌어짐(판 모델, 18장) → 접착이 하중을 받음, 립은 굳는 동안만 잡음 |
| D18 | 레버 봉 끝 (r4.4 geometry) | 마개 x0.2~1.4 (Ø4.0, 끝 핀 면과 같게), 막힌 끝 핀 구멍 x163.1까지 (벽 1.2) | mm | 핀 보스 구멍 Ø3.9 출력 → Ø4.0 드릴 (핀 5장) | 축 놀음 0.10 + 0.20 (봉 ±0.2면 0.10~0.50); 끝 부속은 이음 쪽 핀에 마개, 볼 쪽 핀은 막힘; geometry의 fixed 'lever rod'·'fin boss bore'·'lever rod end plug' |
| D08 | 캐리어 앞 모서리 / 손톱 턱 | R3 / 1.0 앞으로 × 1.5 | mm | 캐리어 앞 윗모서리 | 업스톱 접점 아님 (r4); 손톱으로 레버를 들어 올리는 턱. r4.2: 턱이 밑면 z51.5 위의 R3 모서리를 채워 앞벽에 붙음 (r4.1은 0.37 떠 있었음; 질량 모델은 이미 모서리를 채워 계산) |
| D09 | 도브테일 (v3 D01~D03) | 뿌리 6·끝 9·깊이 4, 앞 z3~8.5 / 뒤 z3~17 | mm | y6.5~15.5 / y198~207 | 꼬리·쉼 패드와 최소 2.25; 끝 부속: 왼쪽 수, 오른쪽 암 |
| D10 | 쉼 펠트 | 1.5T 양모 2.7×8 + 종이 펀칭 0.1×2 | mm | 꼬리 밑 | 펀칭 한 장 = 건반 앞 0.25 내려감 |
| D11 | 업스톱 패드 / 캡스턴 펠트 | 미세셀 우레탄 6T + 펠트 1T / 펠트 2T | mm |  | 패드 실효 e ≤ 0.07 (단계 0 시험 1: C01 진자대로 모델 pad_e 정의대로 측정, 17·17.1장; 설계 0.06); 25 % 압축 0.36 MPa; 패드 자리 강성 ≥ 830 N/mm (100 N에 0.12 mm 이하, 설계 1490), 6건반 화음 자리 ≥ 460 N/mm (60 N씩 6개에 0.13 mm 이하, 설계 492) |
| D12 | 흑건 앞 펠트 자리 | y54.5~59.0 (바닥판 y55.4~59.3) | mm |  |  |
| D15 | 스냅 노치 빠짐 힘 | 1~2 (모델 입술 법칙 1.99) | N | 노치에서 위로 | 덜걱 방지일 뿐, 판정은 들림(PLAY ≤ 0.20, ABUSE ≤ 0.40); 뒤 턱 당김 2.7 N(레버를 손으로 듦) |
| D16 | PET 심 (조정) | 0.1 × 6 × 12.2 (OHP 필름, 패드 재단 크기와 같음) | mm | 패드와 쐐기 사이 | 한 장 = 레버가 0.23° 일찍 닿음 = 건반 앞 0.18 mm |

### 배치 A

| 번호 | 항목 | 값 | 단위 | 기준 | 비고 |
|---|---|---|---|---|---|
| A01 | 88건반 총폭 / 전체 폭(볼 포함) | 1222 / 1254 | mm | v3 A01·A05 | 그대로 |
| A02 | 왼쪽 끝 부속 (A0·A#0·B0) | 47.0 | mm | x0~47, 볼 x−16~-0.68 | 레버 x 10.29, 26.30, 38.48, 핀 [(-1.8, -0.2), (45.2, 46.8)], 보스 [(0.0, 5.13), (1.37, 0.0)] (이음 핀은 안쪽으로만), 패드 바 1 (건반마다 자기 쐐기), 센서 바 x0.5~46.5, 스프링 홈 보스 3, 뒤·앞 도브테일 수; r4.4 EL 기판 x1.0~46.5(센서 바 안), 받침 기둥 x0.5~6.0 + 앞·뒤 리브 x6.0~45.0(z7.0까지), 뒤 리브 틈 x15~38(리드 패드 x18.41~28.57 ±0.9: 2.51 / 8.53, 아랫면 선이 리브 띠에 드는 곳 1.69 / 2.03); 리드 5심 6.35(x14.83~21.18, 패드 줄에서 기판 뒤끝 + 1.5 = y77.39까지 모음)가 레일 밑 차선 x13.53~22.48 z5~10(폭 8.95 = 리드 + 양옆 1.3)와 뒷벽 홈 z5~12(같은 x)로 뒤 통로의 X401까지; 리드 길 ↔ 바닥 부품 최소 1.30(레일·뒷벽 = 차선 여유); A#0 흑 탭 받침(x22.93~30.93, y79~93)을 왼쪽으로 1.75 비껴 감 |
| A03 | 오른쪽 끝 부속 (C8) | 39.5 | mm | 로컬 x0~23.5, 볼 24.18~39.5 | 레버 x 11.75, 핀 [(0.2, 1.8), (23.5, 25.1)], 보스 [(0.0, 4.52), (6.32, 0.0)], 패드 바 1 (자기 쐐기), 센서 바 x0.5~23.0, 스프링 홈 보스 1, 도브테일 암; r4.4 ER 기판 x1.0~23.0(센서 바 안), 받침 기둥 x0.5~6.0 + 앞·뒤 리브 x6.0~21.5(z7.0까지), 뒤 리브 틈 x6~16(리드 패드 x8.25~13.33 ±0.9: 1.35 / 1.77, 아랫면 선이 리브 띠에 드는 곳 2.25 / 2.37); 리드 3심 3.81(x8.89~12.70, 패드 줄에서 기판 뒤끝 + 1.5 = y77.39까지 모음)가 레일 밑 차선 x7.59~14.00 z5~10(폭 6.41 = 리드 + 양옆 1.3)와 뒷벽 홈 z5~12(같은 x)로 뒤 통로의 X411까지; 리드 길 ↔ 바닥 부품 최소 1.30(레일·뒷벽 = 차선 여유); C8 밸런스 핀 밑 레일 1.3 (모듈 E·F 핀과 같음) |
| A04 | 모듈 Ok 시작 x | 47 + 164.5·(k−1) | mm | v3 A03 |  |
| A05 | 프레임 깊이 / 전체 깊이 | 212 / 410 | mm | v3 A10 | 그대로 |
| A06 | 모듈 맨 위 vs 뒷바 | z72.85 vs 가운데 유닛 z22~122 · 스피커 z22~232 | mm |  | 뒷바보다 낮다 |
| A07 | 모듈 무게 | 1.374 | kg | 출력+강철+봉+패드+전자 | r3 2.03; 88건반 본체 10.6 kg |
| A08 | 건반 보관함 (R29) 안치수 | 338.8 × 172 × 77 | mm | 건반 칸 201.3 + 칸막이 1.2 + 옆 칸 136.3 | 백 7 + 흑 5 + A0·A#0·B0·C8 + 강철 2 + 봉 2 + 패드·스프링·심 (레버·패드 바는 위치별이라 예비 없음, 13장) |
| A09 | 금속 (88건반) | 블록 4.83 + 봉 0.27 kg | kg |  | r3 9.52 kg |

### 주요 점 좌표 (y, z): 쉼 → 바닥(강체) → 1 N 정착 바닥(패드 있음) → ff 최대

**white D** (a_dip 4.07°, b_dip 12.66°; 패드 면 기울기 11.36°, 틈 -0.40)

| 점 | 쉼 | 바닥(강체) | 1 N 정착 바닥 | ff 최대 |
|---|---|---|---|---|
| key front top | (0.0, 43.5) | (-1.2, 33.5) | (-1.21, 33.5) | (-1.26, 32.81) |
| finger point | (13.0, 43.5) | (11.77, 34.42) | (11.76, 34.4) | (11.71, 33.79) |
| front stop (floor) | (2.7, 23.5) | (2.9, 13.74) | (2.88, 13.73) | (2.94, 13.07) |
| rest felt bottom | (196.3, 20.1) | (196.26, 24.0) | (196.24, 23.79) | (196.25, 24.27) |
| magnet face | (67.0, 23.5) | (67.04, 18.28) | (67.02, 18.2) | (67.06, 17.92) |
| key COM | (89.78, 33.48) | (89.06, 29.84) | (89.05, 29.74) | (89.02, 29.59) |
| capstan crown | (188.34, 31.0) | (187.55, 34.32) | (187.55, 34.11) | (187.49, 34.54) |
| keeper point (crossbar top) | (11.5, 25.1) | (11.57, 15.96) | (11.54, 15.94) | (11.6, 15.33) |
| balance pin slot centre | (135.3, 22.3) | (135.26, 21.9) | (135.24, 21.75) | (135.26, 21.87) |
| lever COM | (170.44, 41.72) | (173.33, 49.27) | (172.83, 48.27) | (173.41, 49.41) |
| cap top (front corner) | (151.84, 52.03) | (157.7, 63.7) | (156.73, 62.18) | (157.85, 63.92) |
| steel top at the pad front | (152.66, 51.04) | (158.27, 62.55) | (157.33, 61.05) | (158.41, 62.76) |
| steel rear-top corner | (189.65, 51.74) | (194.37, 54.45) | (193.68, 54.15) | (194.47, 54.49) |

**black C#** (a_dip 6.25°, b_dip 10.26°; 패드 면 기울기 9.63°, 틈 -0.45)

| 점 | 쉼 | 바닥(강체) | 1 N 정착 바닥 | ff 최대 |
|---|---|---|---|---|
| key front top | (55.2, 55.5) | (52.02, 46.0) | (52.11, 46.21) | (51.84, 45.32) |
| finger point | (65.2, 55.5) | (61.96, 47.08) | (62.05, 47.26) | (61.77, 46.48) |
| front stop (floor) | (55.4, 23.5) | (55.69, 14.21) | (55.64, 14.41) | (55.75, 13.56) |
| rest felt bottom | (196.3, 20.1) | (196.13, 26.1) | (196.13, 25.74) | (196.09, 26.52) |
| magnet face | (67.0, 23.5) | (67.22, 15.47) | (67.18, 15.62) | (67.27, 14.91) |
| key COM | (116.72, 36.84) | (115.2, 34.12) | (115.24, 34.08) | (115.11, 33.92) |
| capstan crown | (180.31, 31.0) | (179.05, 35.2) | (179.09, 34.91) | (178.94, 35.49) |
| keeper point (crossbar top) | (77.5, 25.1) | (77.48, 18.2) | (77.46, 18.31) | (77.51, 17.71) |
| balance pin slot centre | (135.3, 22.3) | (135.25, 21.68) | (135.23, 21.56) | (135.25, 21.63) |
| lever COM | (170.52, 42.02) | (172.7, 48.02) | (172.38, 47.32) | (172.85, 48.33) |
| cap top (front corner) | (152.01, 52.51) | (156.49, 61.79) | (155.86, 60.72) | (156.78, 62.26) |
| steel top at the pad front | (152.82, 51.52) | (157.1, 60.66) | (156.5, 59.61) | (157.38, 61.13) |
| steel rear-top corner | (189.82, 51.87) | (193.51, 54.07) | (193.05, 53.84) | (193.72, 54.16) |

## 6. 힘·관성·복귀

| 항목 | 백 (D) | 흑 (C#) |
|---|---|---|
| 캡스턴 y | 188.34 | 180.31 |
| 건반 / 레버 질량 | 23.41 / 56.95 g (강철 53.69) | 18.04 / 56.95 g |
| BW / DW / UW | 47.3 / 51.9 / 42.8 g | 45.9 / 51.0 / 40.8 g |
| 마찰 (건반 봉 + 레버 봉 + 캡스턴 + 가이드) | 4.57 = 0.88 + 1.20 + 0.57 + 1.93 g | 5.11 = 1.08 + 0.48 + 2.06 + 1.48 g |
| 스프링 몫 (DW에서) | 11.2 g (스프링 없으면 DW 40.7) | 10.4 g (40.6) |
| 스프링 토크 쉼 / 바닥 | 4.19 / 6.03 N·mm | 4.19 / 5.69 N·mm |
| 행정 따라 DW (0 / 25 / 50 / 75 / 100 %) | 51.9 / 53.5 / 54.4 / 54.5 / 54.0 | 51.0 / 51.2 / 50.9 / 50.0 / 48.7 |
| 행정 따라 UW | 42.8 / 41.7 / 39.9 / 37.6 / 34.7 | 40.8 / 38.7 / 36.3 / 33.5 / 30.5 |
| 마찰 2배 DW / 바닥 UW | 56.5 / 25.0 g | 56.1 / 21.3 g |
| m_eff (건반 + 레버) | 55.2 (8.8 + 46.5) g | 46.5 (7.9 + 38.6) g |
| t50 / 끝까지 (1.2 s 정착 1 N에서 뗌) | 30.8 / 45.4 ms → 16.3 Hz | 26.5 / 39.9 ms → 18.8 Hz |
| 마찰 2배 | 32.9 / 48.5 ms → 15.2 Hz | 28.3 / 42.4 ms → 17.7 Hz |

백 립(y0) DW 47.1 g, y90 DW 131.0 g → 앞/뒤 비 2.52. 비틀림 스프링(r4.5 미스미 C-UA90R5-3-0.5, r4.5 고침: 짧은 다리 8.0를 가둠 홈에): 코일 몸통 강성 10.16 N·mm/rad(자른 다리 포함 8.437), C 11.0, 바닥에서 안지름 4.83 — 코일은 가둔 다리에 매달려 봉과 쉼 0.43 · 바닥 0.38 떨어짐(봉 마찰 없음).

## 7. 4-DOF 타건 시뮬레이션

모델: 건반 = 봉 위의 자유 평면 강체(스냅 노치·입술 마찰·키퍼), 레버 = 봉 위 1자유도 + 비틀림 스프링, 패드 = 강철 윗면과 평행한 폼 층(기울기 11.4°)을 패드 자리 스프링(1490 N/mm = 모듈에서 가장 무른 C# 자리)과 직렬로. 모든 PLAY·ABUSE 경우의 패드 자리는 가장 무른 건반 값이다(보수적).

### 7.1 PLAY / ABUSE (설계 재료)

| 경우 | 앞끝 m/s | 노치 들림 (백 / 흑) | 키퍼 틈 | 패드 힘 N | 캡스턴 N | 레버 봉 N | 자석 오름 |
|---|---|---|---|---|---|---|---|
| PLAY 1.5 m/s, 뗌 | 1.50 | 0.136 / 0.068 | 0.57 / 1.19 | 89 / 76 | 12.6 / 12.7 | 27 / 24 | 0 % / 0 % |
| PLAY 1.5 m/s, 0.45 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 17 % / 13 % |
| PLAY 1.5 m/s, 0.50 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 11 % / 10 % |
| PLAY 1.5 m/s, 0.55 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 8 % / 8 % |
| PLAY 1.5 m/s, 0.60 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 6 % / 7 % |
| PLAY 1.5 m/s, 0.80 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 2 % / 4 % |
| PLAY 1.5 m/s, 1.00 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 0 % / 2 % |
| PLAY 1.5 m/s, 2.00 N 누른 채 | 1.50 | 0.000 / 0.027 | 1.51 / 1.56 | 89 / 76 | 8.4 / 7.9 | 27 / 24 | 0 % / 0 % |
| ABUSE 2.5 m/s, 뗌 | 2.50 | 0.135 / 0.177 | 0.53 / 1.14 | 145 / 128 | 14.2 / 11.4 | 44 / 40 | 0 % / 0 % |
| ABUSE 2.5 m/s, 0.45 N 누른 채 | 2.50 | 0.038 / 0.174 | 1.51 / 1.56 | 145 / 128 | 8.7 / 8.6 | 44 / 40 | 57 % / 29 % |
| ABUSE 2.5 m/s, 0.60 N 누른 채 | 2.50 | 0.038 / 0.173 | 1.51 / 1.56 | 145 / 128 | 8.7 / 8.6 | 44 / 40 | 14 % / 11 % |
| ABUSE 2.5 m/s, 1.00 N 누른 채 | 2.50 | 0.039 / 0.172 | 1.51 / 1.56 | 145 / 128 | 8.7 / 8.6 | 44 / 40 | 2 % / 4 % |
| ABUSE 2.5 m/s, 2.00 N 누른 채 | 2.50 | 0.048 / 0.169 | 1.51 / 1.56 | 145 / 128 | 8.7 / 8.6 | 44 / 40 | 0 % / 0 % |
| 누름 0.8 N | 0.07 | 0.096 / 0.040 | 0.70 / 1.26 | 15 / 14 | 13.0 / 12.6 | 10 / 8 | 1 % / 0 % |
| 누름 1.5 N | 0.62 | 0.091 / 0.047 | 0.72 / 1.23 | 27 / 28 | 13.1 / 13.1 | 10 / 9 | 0 % / 0 % |
| 누름 3 N | 0.99 | 0.091 / 0.038 | 0.72 / 1.25 | 53 / 42 | 13.2 / 13.1 | 16 / 13 | 0 % / 0 % |
| 누름 6 N | 1.46 | 0.162 / 0.053 | 0.52 / 1.22 | 86 / 84 | 16.3 / 13.3 | 26 / 26 | 0 % / 0 % |
| 1.0 m/s, 뗌 | 1.00 | 0.112 / 0.060 | 0.64 / 1.20 | 55 / 42 | 13.6 / 13.6 | 17 / 13 | 0 % / 0 % |
| 2.0 m/s(ABUSE 화음 속도), 뗌 | 2.00 | 0.159 / 0.098 | 0.49 / 1.12 | 119 / 107 | 12.3 / 11.9 | 36 / 33 | 0 % / 0 % |
| 1.0 m/s, 1 N 누른 채 | 1.00 | 0.000 / 0.000 | 1.51 / 1.56 | 55 / 42 | 8.1 / 5.9 | 17 / 13 | 0 % / 2 % |
| 2.0 m/s, 1 N 누른 채 | 2.00 | 0.016 / 0.095 | 1.51 / 1.56 | 119 / 107 | 8.6 / 7.6 | 36 / 33 | 1 % / 3 % |
| 여유 확인: 손가락 시작 1.5 m/s, 뗌 | 2.02 | 0.160 / 0.122 | 0.48 / 1.17 | 120 / 115 | 12.3 / 11.6 | 36 / 36 | 0 % / 0 % |
| 여유 확인, 0.45 N 누른 채 | 2.02 | 0.016 / 0.121 | 1.51 / 1.56 | 120 / 115 | 8.6 / 8.2 | 36 / 36 | 33 % / 24 % |
| 여유 확인, 1 N 누른 채 | 2.02 | 0.017 / 0.121 | 1.51 / 1.56 | 120 / 115 | 8.6 / 8.2 | 36 / 36 | 1 % / 3 % |
| 1 N 정착에서 뗌 | 0.36 | 0.099 / 0.041 | 0.69 / 1.26 | 20 / 19 | 13.1 / 12.7 | 10 / 8 | 0 % / 2 % |

### 7.2 재료·자리·수치 민감도 (PLAY 1.5, ABUSE 2.5 m/s)

| 조합 | PLAY 들림 (백 / 흑) | 키퍼 | 패드 N | 유령 0.45 N | ABUSE 들림 | 연타 Hz |
|---|---|---|---|---|---|---|
| seat stiffest key | 0.139 / 0.061 | 0.56 / 1.20 | 90 / 77 | 17 % / 13 % | 0.120 / 0.183 | 16.3 / 18.8 |
| v_floor 0.1 | 0.189 / 0.121 | 0.41 / 1.09 | 91 / 75 | 18 % / 14 % | 0.167 / 0.197 | 17.0 / 19.8 |
| pad e 0.07 (pass line) | 0.142 / 0.061 | 0.55 / 1.20 | 82 / 72 | 22 % / 15 % | 0.138 / 0.239 | 16.3 / 18.9 |
| pad e 0.10 | 0.153 / 0.063 | 0.50 / 1.22 | 67 / 61 | 47 % / 25 % | 0.168 / 0.333 | 16.6 / 19.3 |
| pad E 0.7 (softer foam) | 0.154 / 0.082 | 0.51 / 1.17 | 74 / 66 | 17 % / 12 % | 0.170 / 0.310 | 16.2 / 18.7 |
| pad E 1.4 (firmer foam) | 0.114 / 0.050 | 0.62 / 1.21 | 104 / 83 | 23 % / 18 % | 0.161 / 0.105 | 16.3 / 19.0 |
| front felt e 0.28 | 0.141 / 0.056 | 0.55 / 1.22 | 89 / 77 | 17 % / 13 % | 0.181 / 0.227 | 16.3 / 18.8 |
| pass lines together (pad e 0.07, E 0.7, front e 0.22) | 0.159 / 0.097 | 0.50 / 1.13 | 67 / 61 | 25 % / 14 % | 0.176 / 0.349 | 16.3 / 18.8 |
| worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1) | 0.204 / 0.186 | 0.34 / 1.20 | 55 / 49 | 58 % / 23 % | 0.271 / 0.303 | 17.2 / 20.1 |
| lip friction 0.35 | 0.136 / 0.068 | 0.57 / 1.19 | 89 / 76 | 17 % / 13 % | 0.135 / 0.177 | 16.3 / 18.8 |
| pass lines + v_floor 0.1 | 0.198 / 0.099 | 0.37 / 1.13 | 69 / 61 | 25 % / 15 % | 0.131 / 0.298 | 17.0 / 19.7 |
| pad e 0.15 | 0.177 / 0.130 | 0.40 / 1.12 | 53 / 47 | 98 % / 52 % | 0.207 / 0.398 | 16.8 / 19.8 |
| pad e 0.25 | 0.208 / 0.192 | 0.24 / 1.09 | 42 / 36 | 100 % / 100 % | 0.314 / 0.400 | 17.0 / 20.3 |
| fallback 1: pad e 0.15, gap -0.60/-0.65, E 1.4 | 0.116 / 0.043 | 0.59 / 1.22 | 73 / 64 | 99 % / 77 % | 0.198 / 0.197 | 17.6 / 20.8 |
| friction x2 | 0.100 / 0.059 | 0.68 / 1.22 | 89 / 85 | 7 % / 8 % | 0.131 / 0.132 | 15.2 / 17.7 |
| rest felt landing (USB slot) | 0.114 / 0.061 | 0.41 / 1.11 | 89 / 76 | 17 % / 13 % | 0.113 / 0.177 | 16.3 / 18.8 |

‘합격선’ 조합(패드 e 0.07, 폼 E 0.7 MPa, 앞 펠트 e 0.22)까지는 PLAY 들림 0.159 ≤ 0.20, 키퍼 0.41 > 0(접촉 법칙 하한 공칭 0.02). 모델 하한 v_floor 0.1은 재료가 아니라 모델 불확실성이라 따로 적는다: 혼자 0.189, 합격선 재료와 묶어 0.198 / 0.099(검증자 물리 m1의 묶은 조합; r4.0 자리 830에서는 0.205였고 r4.1 자리 1490에서 0.20 아래). 합격선 밖 최악(패드 e 0.10, E 0.7, 앞 펠트 e 0.28, v_floor 0.1)은 들림 0.204, 키퍼 0.34 — 단계 0에서 걸러야 할 재료다. 패드 e 0.15 / 0.25(단계 0 시험 1의 대안 판단용): 백 들림 0.177 / 0.208, 흑 ABUSE 들림 0.398 / 0.400, 백 ABUSE 키퍼 0.25 / -0.16.

PLAY 속도 격자(한 건반, 자리 1490 N/mm, 공칭 / 최악 재료):

| 앞끝 m/s, 누름 | 백 들림 / 키퍼 / 자석 (공칭) | 흑 (공칭) | 백 (최악) | 흑 (최악) |
|---|---|---|---|---|
| 0.5, 뗌 | 0.104 / 0.67 / 0 % | 0.055 / 1.22 / 0 % | 0.182 / 0.45 / 0 % | 0.106 / 1.13 / 0 % |
| 0.5, 0.45 N | 0.000 / 1.51 / 5 % | 0.000 / 1.56 / 8 % | 0.000 / 1.51 / 8 % | 0.000 / 1.56 / 8 % |
| 0.5, 0.50 N | 0.000 / 1.51 / 4 % | 0.000 / 1.56 / 7 % | 0.000 / 1.51 / 5 % | 0.000 / 1.56 / 7 % |
| 0.5, 0.60 N | 0.000 / 1.51 / 2 % | 0.000 / 1.56 / 5 % | 0.000 / 1.51 / 2 % | 0.000 / 1.56 / 5 % |
| 0.5, 1.00 N | 0.000 / 1.51 / 0 % | 0.000 / 1.56 / 1 % | 0.000 / 1.51 / 0 % | 0.000 / 1.56 / 0 % |
| 0.5, 2.00 N | 0.000 / 1.51 / 0 % | 0.000 / 1.56 / 0 % | 0.000 / 1.51 / 0 % | 0.000 / 1.56 / 0 % |
| 1.0, 뗌 | 0.096 / 0.69 / 0 % | 0.052 / 1.22 / 0 % | 0.194 / 0.39 / 0 % | 0.109 / 1.12 / 0 % |
| 1.0, 0.45 N | 0.000 / 1.51 / 10 % | 0.020 / 1.56 / 10 % | 0.057 / 1.51 / 26 % | 0.071 / 1.56 / 16 % |
| 1.0, 0.50 N | 0.000 / 1.51 / 7 % | 0.020 / 1.56 / 8 % | 0.056 / 1.51 / 15 % | 0.071 / 1.56 / 12 % |
| 1.0, 0.60 N | 0.000 / 1.51 / 4 % | 0.020 / 1.56 / 6 % | 0.055 / 1.51 / 7 % | 0.071 / 1.56 / 7 % |
| 1.0, 1.00 N | 0.000 / 1.51 / 0 % | 0.020 / 1.56 / 2 % | 0.051 / 1.51 / 1 % | 0.071 / 1.56 / 1 % |
| 1.0, 2.00 N | 0.000 / 1.51 / 0 % | 0.019 / 1.56 / 0 % | 0.044 / 1.51 / 0 % | 0.070 / 1.56 / 0 % |

끝 건반(자기 캡스턴·자기 정착 바닥·자기 패드 쐐기, 자리 A0 1675, C8 2446 N/mm):

| 건반 | 재료 | 1.5 m/s 뗌 들림 / 키퍼 | 0.45 N 자석 | 1.0 N 자석 | 2.5 m/s 들림 | 연타 Hz (마찰 2배) | 끝까지 ms |
|---|---|---|---|---|---|---|---|
| A0 | 공칭 | 0.137 / 0.57 | 17 % | 0 % | 0.129 | 16.1 (15.0) | 49.0 |
| A0 | 최악 | 0.202 / 0.35 | 59 % | 1 % | 0.282 | 17.0 (16.0) | 47.2 |
| C8 | 공칭 | 0.140 / 0.56 | 17 % | 0 % | 0.164 | 16.0 (15.0) | 49.3 |
| C8 | 최악 | 0.201 / 0.35 | 60 % | 1 % | 0.297 | 16.9 (15.9) | 47.5 |

### 7.3 6건반 동시 화음 (윗판이 함께 휨)

윗판 FE에서 6건반이 한꺼번에 누르면 자리가 492 N/mm로 물러진다(한 건반일 때 최소 1490; 가장 무른 화음은 C-C#-D-D#-E-F). r4.0은 기판 위 F|F# 핀이 매달려 있어 D#~G# 화음이 196~203 N/mm였고, 그 자리에 저장된 에너지가 레버로 돌아와 1.2~1.4 m/s 화음에서 들림이 0.216~0.238까지 올랐다(검증자 물리 M2, 이 모델로 재현). r4.1은 그 핀을 만능기판 앞쪽 홈으로 바닥에 닿게 했다. 화음 자리를 1.0~1.5 m/s, 0.05 간격으로 훑은 들림(뗌):

| 재료 | 백 최대 들림 (그때 속도) / 키퍼 최소 | 흑 | 1.0 → 1.5 m/s 백 들림 |
|---|---|---|---|
| 공칭 | 0.135 (1.30) / 0.53 | 0.062 (1.05) / 1.18 | 0.122 0.125 0.130 0.135 0.126 0.118 |
| 합격선 | 0.149 (1.50) / 0.51 | 0.081 (1.30) / 1.15 | 0.112 0.127 0.102 0.124 0.138 0.149 |
| v_floor 0.1 (모델) | 0.219 (1.50) / 0.26 | 0.113 (1.05) / 1.10 | 0.190 0.195 0.201 0.207 0.211 0.219 |
| 합격선 + v_floor 0.1 | 0.202 (1.50) / 0.35 | 0.129 (1.40) / 1.06 | 0.187 0.190 0.192 0.196 0.199 0.202 |
| 합격선 밖 최악 | 0.204 (1.45) / 0.34 | 0.187 (1.50) / 1.06 | 0.194 0.194 0.199 0.202 0.204 0.203 |

공칭·합격선 재료에서는 모든 속도에서 0.20 아래다. 모델 하한 v_floor 0.1(모델 불확실성)과 묶으면 1.45~1.5 m/s 화음에서 0.219까지 오른다 — 0.20을 0.019 넘어 입술이 잠깐 닿는 정도이고 ABUSE 한계 0.40과는 멀다. 이 모서리는 18장에 남긴다. 아래는 화음 자리에서 누른 채 경우(PLAY 1.5 / 1.2 m/s, ABUSE 2.0 m/s):

| 누름 | 백 들림 / 키퍼 / 자석 / 내려옴 m/s | 흑 |
|---|---|---|
| PLAY 1.5, rel | 0.118 / 0.56 / 0 % / 0.00 | 0.046 / 1.21 / 0 % / 0.00 |
| PLAY 1.5, h0.45 | 0.000 / 1.51 / 99 % / 0.03 | 0.029 / 1.56 / 85 % / 0.01 |
| PLAY 1.5, h0.50 | 0.000 / 1.51 / 76 % / 0.02 | 0.029 / 1.56 / 49 % / 0.06 |
| PLAY 1.5, h0.60 | 0.000 / 1.51 / 35 % / 0.10 | 0.029 / 1.56 / 28 % / 0.10 |
| PLAY 1.5, h0.80 | 0.000 / 1.51 / 15 % / 0.10 | 0.029 / 1.56 / 14 % / 0.10 |
| PLAY 1.5, h1.00 | 0.000 / 1.51 / 7 % / 0.07 | 0.029 / 1.56 / 8 % / 0.06 |
| PLAY 1.5, h2.00 | 0.000 / 1.51 / 0 % / 0.00 | 0.029 / 1.56 / 1 % / 0.00 |
| ABUSE 2.0 (자리 505), rel | 0.203 / 0.27 / 0 % / 0.00 | 0.116 / 1.15 / 0 % / 0.00 |
| ABUSE 2.0 (자리 505), h0.45 | 0.014 / 1.43 / 100 % / 0.07 | 0.116 / 1.54 / 100 % / 0.03 |
| ABUSE 2.0 (자리 505), h1.00 | 0.014 / 1.51 / 15 % / 0.13 | 0.116 / 1.56 / 12 % / 0.12 |

화음 자리에서는 가벼운 누름의 건반이 기계적으로 재무장선을 넘는다. 이 유령들은 천천히 내려오므로(PLAY 1.5 m/s 화음 최대 0.03 m/s < 25 % = 0.375; ABUSE 2.0 m/s 화음 최대 0.07 < 상한 0.45) 거름 규칙이 버린다. 0.5~1.5 m/s 전체 격자는 7.4. 진짜 음이 버려지는 경우는 ‘어떤 음(≥ 0.3 m/s) 뒤 250 ms 안에 건반이 재무장하고, note-on부터 500 ms 안에 같은 건반을 앞 음의 1/4보다 느리게 다시 치는’ 때다(모든 세기).

### 7.4 유령 재타건과 펌웨어 거름

재무장선 50 %, 거름 문턱 0.3 m/s(r4.1). 창(r4.5 회로 2차, SCH-03 주 9와 같음): note-on부터 250 ms 안에 재무장 → note-on부터 500 ms 안에 닿는 첫 다시 눌림을 속도 비(25 %, 최대 0.45 m/s)로 판정. 계산한 350경우(한 건반 0.5 / 1.0 / 1.5 m/s 공칭·최악 재료, 6건반 화음 자리 0.5~1.5 m/s, 끝 건반, 재료 조합) 중 기계적으로 재무장하는 것 28건, 거름이 못 버리는 것 0건. 재무장한 경우는 note-on 뒤 1.5 s까지 이어 돌려 유령이 다시 닿는지 봤다(아래 표; 칸의 ‘내려옴’도 이 긴 계산의 값).

6건반 화음 자리(492 N/mm) 유령 격자, 칸 = 자석 오름 % / 내려옴 m/s (굵게 = 재무장 → 거름이 버림, ✗ = 못 버림). 1.15 m/s 아래는 손가락 1 N으로 쳐서 앞끝 속도를 맞췄다 (r4.0처럼 3 N으로 누르면 백은 0.99, 흑은 1.11 m/s 아래로 내려가지 않는다; 모든 격자 타건에서 목표와의 차 ≤ 0.001 m/s):

**백 D**

| 앞끝 m/s | 0.45 N | 0.50 N | 0.60 N | 0.80 N | 1.00 N | 2.00 N |
|---|---|---|---|---|---|---|
| 0.5 | 14 / 0.00 | 8 / 0.01 | 3 / 0.00 | 1 / 0.00 | 0 / 0.00 | 0 / 0.00 |
| 0.6 | 21 / 0.00 | 12 / 0.01 | 6 / 0.02 | 2 / 0.00 | 0 / 0.00 | 0 / 0.00 |
| 0.7 | 32 / 0.00 | 18 / 0.02 | 9 / 0.04 | 3 / 0.00 | 1 / 0.00 | 0 / 0.00 |
| 0.8 | 41 / 0.00 | 24 / 0.02 | 12 / 0.05 | 5 / 0.00 | 2 / 0.00 | 0 / 0.00 |
| 0.9 | **53 / 0.00** | 29 / 0.02 | 15 / 0.06 | 6 / 0.04 | 3 / 0.00 | 0 / 0.00 |
| 1.0 | **73 / 0.00** | 36 / 0.02 | 19 / 0.07 | 8 / 0.06 | 4 / 0.00 | 0 / 0.00 |
| 1.1 | **97 / 0.01** | 46 / 0.02 | 23 / 0.08 | 10 / 0.07 | 5 / 0.02 | 0 / 0.00 |
| 1.2 | **97 / 0.00** | 44 / 0.02 | 22 / 0.08 | 9 / 0.07 | 4 / 0.00 | 0 / 0.00 |
| 1.3 | **98 / 0.01** | **52 / 0.02** | 25 / 0.08 | 10 / 0.08 | 5 / 0.00 | 0 / 0.00 |
| 1.4 | **99 / 0.02** | **62 / 0.02** | 30 / 0.09 | 12 / 0.09 | 6 / 0.05 | 0 / 0.00 |
| 1.5 | **99 / 0.03** | **76 / 0.02** | 35 / 0.10 | 15 / 0.10 | 7 / 0.07 | 0 / 0.00 |

**흑 C#**

| 앞끝 m/s | 0.45 N | 0.50 N | 0.60 N | 0.80 N | 1.00 N | 2.00 N |
|---|---|---|---|---|---|---|
| 0.5 | 8 / 0.01 | 7 / 0.00 | 5 / 0.00 | 3 / 0.00 | 1 / 0.00 | 0 / 0.00 |
| 0.6 | 10 / 0.02 | 7 / 0.01 | 5 / 0.00 | 3 / 0.00 | 1 / 0.00 | 0 / 0.00 |
| 0.7 | 13 / 0.02 | 9 / 0.03 | 6 / 0.01 | 3 / 0.00 | 2 / 0.00 | 0 / 0.00 |
| 0.8 | 16 / 0.02 | 11 / 0.03 | 7 / 0.02 | 4 / 0.00 | 2 / 0.00 | 0 / 0.00 |
| 0.9 | 22 / 0.02 | 15 / 0.04 | 9 / 0.03 | 4 / 0.00 | 2 / 0.00 | 0 / 0.00 |
| 1.0 | 29 / 0.02 | 20 / 0.04 | 12 / 0.05 | 6 / 0.03 | 3 / 0.00 | 0 / 0.00 |
| 1.1 | 38 / 0.02 | 26 / 0.05 | 15 / 0.06 | 7 / 0.05 | 4 / 0.00 | 0 / 0.00 |
| 1.2 | 40 / 0.02 | 27 / 0.05 | 16 / 0.07 | 8 / 0.05 | 4 / 0.00 | 0 / 0.00 |
| 1.3 | **53 / 0.01** | 34 / 0.05 | 20 / 0.08 | 10 / 0.06 | 6 / 0.03 | 0 / 0.00 |
| 1.4 | **68 / 0.01** | 42 / 0.06 | 24 / 0.09 | 12 / 0.08 | 7 / 0.06 | 0 / 0.00 |
| 1.5 | **85 / 0.01** | 49 / 0.06 | 28 / 0.10 | 14 / 0.10 | 8 / 0.06 | 1 / 0.00 |

그 밖의 재무장 경우:

| 경우 | 자석 오름 | 내려옴 m/s | 결과 |
|---|---|---|---|
| main_white_abuse_h0.45 | 57 % | 0.00 | 버림 |
| chord_white_play_h0.45 | 99 % | 0.03 | 버림 |
| chord_white_play_h0.50 | 76 % | 0.02 | 버림 |
| chord_white_play_h0.60 | 35 % | 0.10 | 재무장 안 함 |
| chord_black_play_h0.45 | 85 % | 0.01 | 버림 |
| chord_black_play_h0.50 | 49 % | 0.06 | 재무장 안 함 |
| chord12_white_play_h0.45 | 97 % | 0.00 | 버림 |
| chord12_black_play_h0.45 | 40 % | 0.02 | 재무장 안 함 |
| chord20_white_play_h0.45 | 100 % | 0.07 | 버림 |
| chord20_black_play_h0.45 | 100 % | 0.03 | 버림 |
| grids_worst_white_1.5_h0.45 | 58 % | 0.00 | 버림 |
| grids_worst_white_1.5_h0.50 | 31 % | 0.02 | 재무장 안 함 |
| end_A0_worst_1.5_h0.45 | 59 % | 0.00 | 버림 |
| end_C8_worst_1.5_h0.45 | 60 % | 0.00 | 버림 |
| pad e 0.10_white_play_h0.45 | 47 % | 0.00 | 재무장 안 함 |
| worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)_white_play_h0.45 | 58 % | 0.00 | 버림 |
| land_r44_F_nom_1.0_h0.45_play_chord | 75 % | 0.00 | 버림 |
| land_r44_F_nom_1.5_h0.45_play_chord | 100 % | 0.03 | 버림 |
| land_r44_F_passline_1.5_h0.45_play_chord | 43 % | 0.00 | 재무장 안 함 |
| land_r44_F_worst_1.5_h0.45_play_chord | 70 % | 0.00 | 버림 |
| land_r44_F#_nom_1.5_h0.45_play_chord | 84 % | 0.01 | 버림 |
| land_r44_F#_passline_1.5_h0.45_play_chord | 30 % | 0.02 | 재무장 안 함 |

**재무장 28건의 긴 계산(r4.5 회로 2차, note-on 뒤 1.5 s까지)** — 재무장 = 자석이 50 %를 넘은 시각, 흔들림 멈춤 = 자석이 10 ms에 행정의 1 %보다 더 움직인 마지막 시각, 모두 note-on부터 ms:

| 경우 | 최대 오름 | 재무장 | 흔들림 멈춤 | 다시 닿음 | 끝 자석 위치 | 끝 기어내림 m/s (자석, − = 올라감) | 판정 |
|---|---|---|---|---|---|---|---|
| main_white_abuse_h0.45 | 57 % | 67.1 | 86 | 없음 (1500 ms까지) | 57 % | -0.00006 | 유령 안 옴 |
| chord_white_play_h0.45 | 99 % | 31.8 | 122 | 없음 (1500 ms까지) | 88 % | -0.00006 | 유령 안 옴 |
| chord_white_play_h0.50 | 76 % | 36.6 | 222 | 없음 (1500 ms까지) | 40 % | 0.00047 | 유령 안 옴 |
| chord_black_play_h0.45 | 85 % | 31.3 | 122 | 없음 (1500 ms까지) | 78 % | 0.00010 | 유령 안 옴 |
| chord12_white_play_h0.45 | 97 % | 42.0 | 129 | 없음 (1500 ms까지) | 96 % | 0.00000 | 유령 안 옴 |
| chord20_white_play_h0.45 | 100 % | 24.4 | 135 | 없음 (1500 ms까지) | 67 % | -0.00007 | 유령 안 옴 |
| chord20_black_play_h0.45 | 100 % | 23.5 | 115 | 없음 (1500 ms까지) | 80 % | 0.00009 | 유령 안 옴 |
| gridc_white_0.9_h0.45 | 53 % | 67.1 | 78 | 없음 (1500 ms까지) | 53 % | -0.00006 | 유령 안 옴 |
| gridc_white_1.0_h0.45 | 73 % | 48.8 | 100 | 없음 (1500 ms까지) | 73 % | -0.00007 | 유령 안 옴 |
| gridc_white_1.1_h0.45 | 97 % | 40.8 | 121 | 없음 (1500 ms까지) | 96 % | 0.00000 | 유령 안 옴 |
| gridc_white_1.2_h0.45 | 97 % | 42.0 | 129 | 없음 (1500 ms까지) | 96 % | 0.00000 | 유령 안 옴 |
| gridc_white_1.3_h0.45 | 98 % | 38.2 | 120 | 없음 (1500 ms까지) | 95 % | -0.00006 | 유령 안 옴 |
| gridc_white_1.3_h0.50 | 52 % | 54.4 | 160 | 없음 (1500 ms까지) | 22 % | 0.00051 | 유령 안 옴 |
| gridc_white_1.4_h0.45 | 99 % | 34.8 | 121 | 없음 (1500 ms까지) | 92 % | -0.00006 | 유령 안 옴 |
| gridc_white_1.4_h0.50 | 62 % | 42.7 | 181 | 없음 (1500 ms까지) | 31 % | 0.00049 | 유령 안 옴 |
| gridc_white_1.5_h0.45 | 99 % | 31.8 | 122 | 없음 (1500 ms까지) | 88 % | -0.00006 | 유령 안 옴 |
| gridc_white_1.5_h0.50 | 76 % | 36.6 | 222 | 없음 (1500 ms까지) | 40 % | 0.00047 | 유령 안 옴 |
| gridc_black_1.3_h0.45 | 53 % | 47.1 | 90 | 없음 (1500 ms까지) | 43 % | 0.00029 | 유령 안 옴 |
| gridc_black_1.4_h0.45 | 68 % | 35.7 | 111 | 없음 (1500 ms까지) | 60 % | 0.00019 | 유령 안 옴 |
| gridc_black_1.5_h0.45 | 85 % | 31.3 | 122 | 없음 (1500 ms까지) | 78 % | 0.00010 | 유령 안 옴 |
| grids_worst_white_1.5_h0.45 | 58 % | 67.0 | 93 | 없음 (1500 ms까지) | 58 % | -0.00006 | 유령 안 옴 |
| end_A0_worst_1.5_h0.45 | 59 % | 66.6 | 93 | 없음 (1500 ms까지) | 59 % | -0.00007 | 유령 안 옴 |
| end_C8_worst_1.5_h0.45 | 60 % | 65.7 | 93 | 없음 (1500 ms까지) | 60 % | -0.00007 | 유령 안 옴 |
| worst (pad e 0.10, E 0.7, front e 0.28, v_floor 0.1)_white_play_h0.45 | 58 % | 67.0 | 93 | 없음 (1500 ms까지) | 58 % | -0.00006 | 유령 안 옴 |
| land_r44_F_nom_1.0_h0.45_play_chord | 75 % | 48.6 | 110 | 없음 (1500 ms까지) | 75 % | -0.00008 | 유령 안 옴 |
| land_r44_F_nom_1.5_h0.45_play_chord | 100 % | 31.8 | 122 | 없음 (1500 ms까지) | 88 % | -0.00007 | 유령 안 옴 |
| land_r44_F_worst_1.5_h0.45_play_chord | 70 % | 58.1 | 103 | 없음 (1500 ms까지) | 70 % | -0.00008 | 유령 안 옴 |
| land_r44_F#_nom_1.5_h0.45_play_chord | 84 % | 31.3 | 122 | 없음 (1500 ms까지) | 78 % | 0.00010 | 유령 안 옴 |

**다시 눌림 시각 상한.** 모델에서 재무장한 유령은 스스로 다시 닿지 않는다(0 / 28, 1.5 s까지): 0.45~0.50 N 손가락은 UW(42.8 / 40.8 g ≈ 0.42 / 0.40 N)와 DW 사이 마찰 띠 안이라 건반을 뜬 자리(자석 22~96 %)에 붙잡는다. 흔들림은 222 ms 안에 멈추고(재무장은 67.1 ms 안), 그 뒤 움직임은 모델 마찰 정칙화(0.2 mm/s 아래 비례)의 기어내림 ≤ 0.0005 m/s(자석)뿐이다 — 그대로 가면 가장 빨라도 3.8 s 뒤 닿는다. 그래서 창의 상한은 기구가 아니라 손가락이 정한다 — 펌웨어 상수 **500 ms(note-on부터)** = 흔들림이 멈추는 가장 늦은 시각의 약 2배. 단계 0 시험 11에서 펌웨어가 의심 상태의 다시 눌림 시각을 기록해, 유령(원치 않은 다시 눌림)이 500 ms를 넘으면 창을 (가장 늦은 것 + 100 ms)로 늘린다(대가: 그만큼 느린 진짜 재타건이 더 버려짐). 창이 지난 뒤 기어내려 닿는 건반이 음을 내지 않게 하려면(선택, 펌웨어만) 두 문턱 사이 시간에 상한을 둔다: 자석 0.01 m/s(백 앞끝 약 0.02 m/s)보다 느린 눌림은 음 없음 — 모델 기어내림의 약 19배, PLAY 격자에서 가장 느린 0.5 m/s 음(자석 0.26 m/s)의 1/26.

### 7.5 운반 기울임과 스냅

| 자세 | 백 노치 들림 | 흑 | 눕힌 뒤 앞 높이 변화 |
|---|---|---|---|
| +90° | 0.01 | 0.00 | -0.003 / -0.001 |
| -90° | 0.05 | 0.06 | -0.001 / -0.001 |
| -120° | 0.30 | 0.27 | -0.001 / -0.000 |
| +180° | 0.35 | 0.29 | -0.001 / -0.000 |

정적으로는 뒤집혀도(180°) 들림 0.35 < 빠짐 0.80. 입술 법칙의 빠짐 힘 1.99 N이면 뒤집힌 채 약 8.7 g 충격에서 백건이 빠질 수 있다 → 모듈은 바로 세우거나 뒤 모서리로 세워 옮긴다(RET-2 운반 규칙).

## 8. 강도·하중

### 8.1 윗판과 핀 (그릴리지 FE, 1 mm 격자; 기판 위 F·F# 사이 핀은 y148.6~170.7에서 기판 홈을 지나 z3까지 깊은 보이고 킬(y144.5~148.6, z3~19.3)로 밸런스 레일 뒷면에 붙음 — r4.4 고침 2b, 바닥이 뚫림; r4.5 고침: 킬 뿌리는 레일 + 바닥 띠 보(핀 선 연속, EVA 없음), 핀 앞끝 y152 → y148.6; 그 뒤는 뒷벽까지 깊은 보 — r4.3: USB 터널 위도 매달림)

건반마다 패드 자리 강성(100 N): C 1722, C# 1492, D 1966, D# 1956, E 1525, F 1873, F# 1891, G 1563, G# 2036, A 1985, A# 1527, B 1742 N/mm.

| 하중 | 경우 | 패드 힘 합 N | 윗판 (층 안) MPa | 핀 윗 이음 (층간) MPa | 뒷벽 N/mm | 자리 처짐 최대 mm |
|---|---|---|---|---|---|---|
| PLAY 1.5 | 한 건반 | 89 | 2.3 | 1.3 | 0.90 | 0.06 |
| PLAY 1.5 | 6건반 동시 | 510 | 5.5 | 4.2 | 3.51 | 0.17 |
| ABUSE 2.0 | 한 건반 | 119 | 3.0 | 1.8 | 1.20 | 0.08 |
| ABUSE 2.0 | 6건반 동시 | 690 | 7.5 | 5.7 | 4.76 | 0.23 |
| ABUSE 2.5 | 한 건반 | 145 | 3.7 | 2.2 | 1.46 | 0.10 |

패드 힘(실제 수직력): PLAY 89 / 76 N, 2.0 m/s 119 / 107 N, ABUSE 145 / 128 N (r3는 손가락 시작 1.5 m/s에서 138 / 159 N). 패드 밑 지압 2.01 MPa, 폼 최대 압축 18 % / 15 %(치밀화 80 %).

### 8.2 레버 봉·핀 보스

| 하중 | 봉 반력 (백 / 흑) | 6건반 굽힘 | 처짐 | 핀 반력 → 보스 지압 | 한 건반 최악 |
|---|---|---|---|---|---|
| PLAY 1.5 | 27 / 24 N | 65 MPa | 0.014 | 93 N → 7.9 MPa | 31 MPa |
| 2.0 m/s 화음 | 36 / 33 N | 88 MPa | 0.019 | 127 N → 10.7 MPa | 43 MPa |
| ABUSE 2.5 | 44 / 40 N | 107 MPa | 0.023 | 153 N → 12.9 MPa | 52 MPa |

r4.5 고침 가둠 홈 자리의 허브·웹(1f-2장): ABUSE 층 안 7.96 MPa(홈 모서리 Kt 2 포함; 홈이 없던 r4.4 단면 3.44), 전단 0.99; PLAY 4.93; 짧은 다리의 두 닿는 점은 모두 웹 쪽 조각 A(층 안), 손 25°에서 1.36 N씩(d × d에 5.4 MPa); 아래 고리 조각 B는 다리 힘을 받지 않음; 봉은 양옆 온전한 허브에만 기대어 ABUSE 지압 1.45 MPa.

### 8.3 건반과 상시 응력

- 숨은 빔: PLAY 11.5 MPa(캡스턴 16.3 N), ABUSE 10.0 MPa. 얇은 꼬리: 백 5.4 / 흑 9.7 MPa(층 안, 매 음). USB 홈 옆 선반(F·F# 쉼 펠트 착지, r4.3) 3.2 MPa.
- 쉼 상시: 꼬리 0.43 / 0.50, 빔 0.16, 노치 단면 0.25 MPa, 스프링 다리 홈 0.38 MPa → 최대 0.50 MPa.
- 건반 굴림(되돌리는 / 넘기는 모멘트): C 9.0/3.3, C# 99.0/99.0, D 7.4/2.7, D# 99.0/99.0, E 52.2/19.1, F 3.9/1.5, F# 1.4/6.3, G 99.0/99.0, G# 4.9/1.9, A 13.9/5.1, A# 9.4/3.7, B 5.0/1.8.

## 9. 틈 (±0.3 공차, 공칭 1.3 이상)

모듈 스윕 1444쌍, 1.3 미만 0. 최소 1.31(공차 뒤 1.01).

| 짝 | 최소 | 공차 뒤 | 자세 |
|---|---|---|---|
| 건반 ↔ 밸런스 레일 | 1.31 | 1.01 | 건반 C# [밸런스 블록, 바닥] ↔ 밸런스 레일 봉 받침 [ ] |
| 건반 옆벽 ↔ 건반 봉 | 1.46 | 1.16 | 건반 C [꼬리 왼 옆벽, ff 최대] ↔ 건반 봉 Ø4 [ ] |
| 건반 ↔ 센서 바 | 1.70 | 1.40 | 건반 D# [왼 옆벽 아래, ff 최대] ↔ 센서 바 [ ] |
| 건반 ↔ 센서 바 오른쪽 턱 (v3 P112, r4.5 회로 2차) | 1.95 | 1.65 | 건반 B [꼬리 오른 옆벽, ff 최대] ↔ 센서 바 오른쪽 턱 립(앞, v3 P112) [ ] |
| 건반 빔·꼬리 ↔ 제어 기판 부품 | 1.31 | 1.01 | 건반 F# [빔, 복귀 넘침] ↔ 기판 부품(z20 이하) [ ] |
| 건반 꼬리·쉼 펠트 ↔ USB-C 플러그 | 1.56 | 1.26 | 건반 F# [쉼 펠트, 복귀 넘침] ↔ USB-C 플러그 (z10.7-18.3) [ ] |
| 건반 ↔ 가림판 띠 | 1.63 | 1.33 | 건반 F# [뒷벽, 쉼] ↔ 가림판 띠 [ ] |
| 건반 옆벽·리브 ↔ 키퍼 훅 | 1.33 | 1.03 | 건반 C# [왼 옆벽 아래, 쉼] ↔ 키퍼 훅 C# [ ] |
| 건반 꼬리 ↔ 도브테일 | 2.25 | 1.95 | 건반 C [쉼 펠트, 복귀 넘침] ↔ 뒤 도브테일(암 홈) [ ] |
| 건반 ↔ 핀 | 1.40 | 1.10 | 건반 F [꼬리 윗판, 복귀 넘침] ↔ 핀 [ ] |
| 흑건 ↔ 이웃 백건 | 1.32 | 1.02 | 건반 F [꼬리 윗판, 쉼] ↔ 건반 F# [뒷벽 복귀 넘침] |
| 백건 ↔ 백건 (x 틈) | 1.31 | 1.01 | 건반 A [헤드 윗판, 복귀 넘침] ↔ 건반 B [헤드 윗판 복귀 넘침] |
| 자기 건반 ↔ 자기 레버 | 1.31 | 1.01 | 건반 F# [블록 웹, 복귀 넘침] ↔ 레버 F# [손톱 턱 복귀 넘침] |
| 건반 ↔ 이웃 레버 | 1.36 | 1.06 | 건반 E [꼬리 윗판, 복귀 넘침] ↔ 레버 F [캐리어 왼 옆벽 복귀 넘침] |
| 레버 ↔ 레버 | 1.32 | 1.02 | 레버 A [캐리어 오른 옆벽, 복귀 넘침] ↔ 레버 A# [캐리어 왼 옆벽 복귀 넘침] |
| 레버 ↔ 핀 | 1.32 | 1.02 | 레버 D [캐리어 오른 옆벽, 쉼] ↔ 핀 [ ] |
| 레버 ↔ 윗판 | 4.04 | 3.74 | 레버 C [손톱 턱, ff 최대] ↔ 윗판 [ ] |
| 레버 ↔ 패드 바·레일 | 1.54 | 1.24 | 레버 D [캐리어 오른 옆벽, ff 최대] ↔ 패드 바 레일 [ ] |
| 레버 ↔ 패드 쐐기 | 5.00 | 4.70 | 레버 C [캐리어 윗 스냅 립 L y150-163, ff 최대] ↔ 패드 쐐기 C [ ] |
| 레버 ↔ 이웃 패드 | 1.44 | 1.14 | 레버 C [캐리어 왼 옆벽, ff 최대] ↔ 업스톱 패드 C [ ] |
| 레버 ↔ 뒷벽 | 1.45 | 1.15 | 레버 C# [허브, 쉼] ↔ 뒷벽 [ ] |
| 레버 ↔ 가림판 띠 | 1.66 | 1.36 | 레버 F [손톱 턱, 복귀 넘침] ↔ 가림판 띠 [ ] |
| 건반 블록 ↔ 밸런스 레일(낮춘 곳·받침) | 1.31 | 1.01 | 건반 C# [밸런스 블록, 바닥] ↔ 밸런스 레일 봉 받침 [ ] |

설계 접촉·맞춤(따로 보고): 크로스바 ↔ 탭 뒤쪽 y 멈춤 0.59, 흰 앞 펠트 ↔ 크로스바·리브 1.68, 밸런스 핀 ↔ 입술 벽 1.39 / 홈 뒤끝 1.63, 캐리어 옆벽 ↔ 패드(r4.1: 윗 립을 패드 옆에서 끊어 스윕에 넣음) 1.44, USB 플러그(r4.3 z10.7~18.3) ↔ 선반 홈·리브·핀·뒷벽 1.30, 제어 기판 부품(BRD-01) ↔ 프레임 1.30, 이웃 도브테일 홈 ↔ 끝 핀 1.30.

- 끝 부속 왼쪽: 527쌍, 1.3 미만 0, 최소 1.31 (건반 B0 [헤드 윗판] ↔ 건반 C(오른쪽 모듈) [헤드 윗판]); 볼과 1.33; 이음매 너머 움직이는 부품 1.31, 고정-고정 1.32 (핀 ↔ 뒤 도브테일(암 홈) (모듈)), 도브테일 맞춤 0.00. 이음 면(핀·윗판·가림판) 0.40 = 모듈 이음과 같은 0.4 (0.2씩 들여 뜀).
- 끝 부속 오른쪽: 310쌍, 1.3 미만 0, 최소 1.31 (건반 C8 [헤드 윗판] ↔ 건반 B(왼쪽 모듈) [헤드 윗판]); 볼과 1.33; 이음매 너머 움직이는 부품 1.31, 고정-고정 1.32 (뒤 도브테일(암 홈) ↔ 핀 (모듈)), 도브테일 맞춤 0.00. 이음 면(핀·윗판·가림판) 0.40 = 모듈 이음과 같은 0.4 (0.2씩 들여 뜀).

## 10. 조립 순서

r4.1(검증자 기하 M1): 윗판이 프레임과 한 몸이라 **레버를 건반보다 먼저** 넣는다. 건반을 먼저 넣으면 흑 레버가 자기 흑건 위를 지나갈 창이 13.3 mm뿐이라(레버 단면 ≥ 20) 못 들어간다. run_all의 레버 넣기 C-공간 검사(0.25 mm, 피치 −40~60°): 건반이 없으면 C 도달, C# 도달, D 도달, E 도달, F 도달, F# 도달, G# 도달, B 도달, A0 도달, A#0 도달, C8 도달; 건반이 다 있으면 C# 막힘, D 막힘, E 막힘, G# 막힘.

1. **제어 기판 먼저 (r4.4 고침 2b)**: 리본(J301)·EXT 선을 납땜한 기판을 넣는다. 모듈을 뒤집어 놓고, 기판을 부품 쪽이 프레임 안을 보게 들어 홈을 F|F# 핀 발·킬에 맞춘 뒤 바닥 구멍(x46.25~118.25 y144.5~196.5)으로 곧게 밀어 넣는다(길 위 최소 0.60). 기판이 매단 보스 4개에 닿고 위치 핀 2개가 구멍(반경 놀음 0.10)에 들어가면 M3×6 2개를 밑에서 (50.0, 149.0)·(114.5, 192.5)에 조인다(머리는 기판 밑, 육각 렌치 2.0). 리본은 밸런스 레일 밑 차선으로 센서 기판 쪽에 둔다. 다시 뒤집는다. **센서 바·기판(r4.5 회로 2차)**: 리본(J201)을 납땜한 센서 기판을 센서 바에 붙인 덩어리를 모듈 하나만 둔 채(왼쪽 이웃 없이) 1.5 mm 왼쪽에 내려놓아 기판을 기둥·리브에 얹고, 오른쪽으로 밀어 바 끝을 오른쪽 턱(P36, 립 밑면 z13.6) 밑에 넣은 뒤 왼쪽 M3×10 자가 탭 2개를 조인다(v3 절차). 턱이 오른쪽 끝을 잡으므로 모듈을 뒤집어도 바가 나사에만 매달리지 않는다.
2. 벤치에서: 프레임에 밸런스 핀을 핀 높이 게이지(T3)로 압입하고(꼭대기 z23.30) GO/NO-GO로 z23.20~23.40인지 본다(10.1장). 봉 받침에 건반 봉을 놓고 멈춤 기둥 사이에 둔다. 앞 펠트(y1.5~9.0)·흑 멈춤 펠트·키퍼 펠트를 붙인다. 가이드 탭에 천 0.5T(쿠폰으로 두께 확인).
3. 벤치 지그(T1)와 가짜 레버(T2)로 건반마다 맞춘다(10.1장): 가짜 레버를 캡스턴에 얹어 실제 쉼 하중(캡스턴 힘 백 1.53 / 흑 0.99 N)을 준 채, 먼저 높이 블록으로 앞 높이를 창 ±0.15 안에 쉼 펀칭으로 맞추고(한 장 = 앞 0.25), 그다음 캡스턴을 바늘 ↔ 읽기 턱으로 맞춘다(1/8회전 = 바늘 0.34 / 0.22 mm, 육각 렌치 2.0). 쉼 선반은 z20.054. 건반은 아직 프레임에 넣지 않는다.
4. 레버마다(위치 이름이 새겨진 캐리어): **강철 접착(r4.4 고침 2b)** — 강철 9×19×40(두께 8.9~9.1인지 캘리퍼스로)의 두 19×40 옆면과 캐리어 옆벽 안쪽을 #120 사포 → 알코올, 강철 두 옆면에 MS 폴리머를 얇게(블록당 약 0.2 mL) 펴 바르고 밑에서 끼운다(스냅: 아래 립이 걸림, 접착층 한쪽 0.10). 윗 립·아래 립·펠트 자리로 나온 것은 바로 닦고 24시간 굳힌다. 그다음 펠트 띠 2T(흑연)를 붙인다. **스프링(r4.5)**: 미스미 C-UA90R5-3-0.5의 두 암을 경선 니퍼로 잘라(긴 다리 코일 중심에서 끝까지 22.3 = 코일을 떠나는 점에서 22.13, 짧은 다리 8.0, 굽히지 않음; 끝 거스러미는 줄로) **긴 다리가 코일의 +x(오른쪽) 끝**에 오게 들고(r4.5 고침) 짧은 다리 끝을 가둠 홈(폭 0.70, 레버 기준 137° 방향) 입구에 대어 홈을 따라 끝까지 밀어 넣는다 — 코일은 넣는 슬롯(317°)으로 주머니에 들어가 앉는다(뒤집으면 짧은 다리가 홈에 맞지 않음). 0.5 선이 안 들어가면 홈을 0.5 날로 다듬는다. 넣는 슬롯이 뒤·아래로 열려 있어 코일이 제 무게로 다시 미끄러져 나올 수 있으므로, 봉을 꿸 때까지 이쑤시개(Ø2)를 허브 구멍과 코일에 꽂아 두고 봉이 그 레버에 오기 직전에 뽑는다. 긴 다리는 창 밖으로 자유 상태.
5. **건반이 없는 프레임**에 레버를 앞에서 하나씩 밀어 넣어 허브를 레버 봉 선(L)에 맞춘다. 레버 앞은 바닥판(C·C#·D·A·A#·B, -30.25°)이나 기판 쪽(E·F 4067 모듈 -13.25°, D#·G# 기판 위 매단 보스 -16.75°, F#·G 기판 윗면 -24.00 / -23.50°)에 놓인다. 긴 다리가 뒷벽을 먼저 치면 손가락으로 감아 누른 채 넣는다.
6. Ø4 레버 봉을 왼쪽 끝 핀부터 핀 보스·허브(칼라끼리 맞닿음)·스프링 코일에 손으로 허브를 맞추며 꿴다. 왼쪽 마개(출력)를 넣는다. 레버마다 제 무게로 자유롭게 도는지 본다(아니면 칼라 면 사포질; 칸마다 축 놀음 0.46 / 0.46 / 0.43 / 0.30).
7. 긴 다리를 뒷벽 보스의 홈(긴 다리 x +0.8에 맞춤, 입구 0.5×45°, r4.2: 보스 밑면에서 열려 다리가 밑에서 들어감)에 건다: 바닥판 위 레버(-31.3°)는 다리가 홈 입구 안 1.88에 거의 풀린 채 놓이고, 기판 위 레버(D#~G#, -14.3~-24.6°)는 손가락으로 약 14° 감아 입구에 대고 놓는다. 레버 위는 비어 있어 손이 들어간다.
8. **흑건 5개를 먼저**, 그다음 백건 7개를 넣는다: 건반마다 그 레버를 손톱 턱으로 15.0°까지 들고, 11장 빼기 경로(검사함)의 반대로 — 비스듬히 밀어 넣고, 3 mm 뒤로 밀고, 블록을 핀 위에 내려 스냅(블록 위를 누름). 레버를 놓으면 캡스턴에 앉는다.
9. 패드(폼 6T + 펠트 1T, 6×12.2)를 패드 바 쐐기에 붙이고(바 6종, 손잡이 이름 확인), 패드 바를 L 레일에 **뒤 멈춤(y185.0)까지** 밀어 넣는다: 가장자리 잎 혀의 돌기가 y163.5부터 립에 올라탄다. 바가 위아래로 놀지 않는지(잎 예하중) 확인.
10. 12장 종이 띠 기준으로 건반마다 바닥을 확인하고 필요하면 패드 밑 PET 심(0.1)으로 업스톱 시점을 맞춘다.
11. 가림판 띠를 윗판 앞 턱에 건다. 끝 부속(A0·A#0·B0, C8)도 같은 순서(A#0 레버 넣기 도달 확인됨).

### 10.1 출력 공구 — 벤치 지그 · 높이 블록 · 캡스턴 벤치 게이지(가짜 레버) · 밸런스 핀 높이 게이지 (r4.4)

`tools/make_tools.py`가 모델 값에서 만든다. 치수 T01~T29는 `tools/tools_geometry.json`, 설명과 옆모습 틈 표는 `tools/tools.md`, 출력 파일은 `tools/stl/`. 출력물 4개, 합계 약 68 g, 약 8시간. 새로 살 것은 없다: 건반 봉과 같은 4 m 봉에서 자른 봉 토막 3개(K 31.6, L 20.6, 교정봉 31.6), 100개 묶음에서 남는 밸런스 핀 1개, 설치 전에 빌려 쓰는 레버 강철 블록 1개.

**왜 가짜 레버인가(가장 중요한 발견).** 건반은 앞이 무겁다(무게중심 y89.8, 봉 y141.0). 그래서 벤치에서는 무언가가 꼬리를 눌러야 쉼 선반에 앉는데, 그 힘에 따라 건반 높이가 달라진다. 손가락으로 0.3~5 N을 누르면 백건 앞 높이가 -0.21~+0.33 mm 달라진다. 펀칭 1장(0.25)보다 크다. 그래서 r4.3 글의 ‘빔 윗면 위 2.5 단 게이지’ 대신 캡스턴 게이지를 **가짜 레버**로 만들었다. 지그의 L 봉 토막에 끼워 실제 레버와 같은 모멘트(22.82 N·mm, 실제 22.35)로 캡스턴을 누른다. 캡스턴 힘은 백 1.53 N(실제 1.50), 흑 0.99 N(실제 0.98)이고, 남는 앞 높이 차이는 0.004 / 0.001 mm다.

**기준은 책상이 아니라 프레임 자리다.** 지그 밑면 = 프레임 밑면 z3.0(출력 높이 = z − 3.0). K 봉 토막 구멍 중심 (141.0, 21.5), 쉼 선반 윗면 z20.054, L 봉 토막 (203.25, 33.5). 핀 게이지는 레일 윗면 z19.0과 레일 앞면 y132.3에 댄다. 교정용 영점 받침(교정봉 윗면 z30.9 = 캡스턴 꼭대기)이 지그와 가짜 레버를 한 번에 교정한다.

| 공구 | 하는 일 | 주요 치수 (번호 = tools_geometry.json `dims`) | 출력 (PETG, 서포트 없음) | g | 분 |
|---|---|---|---|---|---|
| T1a 벤치 지그 (받침) | 건반 1개를 모듈 프레임과 같은 자리에 올린다: K 봉 토막, 쉼 선반, 예비 밸런스 핀(x 위치), 가짜 레버용 L 봉 토막, 영점 받침, 읽기 턱 기둥, 주차 기둥. 모듈 건반 12개와 끝 A0·A#0·B0·C8에 모두 쓴다 | T02 받침판 X -36.0~36.0 × y -8.0~214.0, z3.0~5.0; T05 K 봉 토막 구멍 (건반 봉) 중심 (y141.0, z21.5), Ø3.9 출력 → Ø4.0 드릴, 눈물방울 윗부분; T06 쉼 선반 X ±13.0, y195.8~200.0, 윗면 z20.054; T07 L 봉 토막 구멍 (레버 봉) 중심 (y203.25, z33.5), Ø3.9 출력 → Ø4.0 드릴; T08 영점 받침 (교정) 백 y188.34 · 흑 y180.31, X ±13.0~17.0, 홈 바닥 z26.9 (폭 4.6, 턱 z27.9); T09 읽기 턱 기둥 X 12.9~20.9 (윗면), y118.4~123.6, 윗면 z65.5 | 밑면(z3 기준면)을 베드에 — 서포트 없음 (가로 구멍은 눈물방울); 층 프레임과 같은 층 높이 (권장 0.2 첫 층 + 0.1); 채움 40 %, 벽 3; 크기 72 × 222 × 62.5 | 38.4 | 215 |
| T1b 높이 블록 | 받침판(z5.0)에 세워 건반 머리 옆면에 붙이고 손톱으로 땅 높이와 비교한다. 높으면 펀칭 1장 더, 낮으면 1장 뺀다 | T11 땅 W+ (백건 높음 한계) 43.65; T12 땅 W- (백건 낮음 한계) 43.35; T13 땅 B+ (흑건 높음 한계) 55.65; T14 땅 B- (흑건 낮음 한계) 55.35; T15 창 (앞 높이) ±0.15 | 밑면을 베드에, 땅이 위; 층 0.1, 높이 37.9~50.8 구간만 0.05 (슬라이서 높이 범위 수정자); 채움 25 %, 벽 3; 크기 10 × 34 × 50.7 | 10.3 | 109 |
| T2 캡스턴 벤치 게이지 (가짜 레버) | L 봉 토막에 끼워 실제 레버와 같은 모멘트로 캡스턴을 누른다. 캡스턴 꼭대기 z30.90(정착 쉼; 건반 좌표 z31.0)를 부리 끝 바늘로 확대해 읽는다. 캡스턴을 돌릴 때는 주차 기둥으로 젖혀 둔다 | T17 밑면 (펠트 면) 30.9; T18 강철 주머니 y149.8~190.2, z32.8~52.2, 깊이 9.4 (+X 면이 열림); T22 확대비 (바늘 / 캡스턴) 백 5.52 · 흑 3.59; T23 모멘트 (L 기준) 22.82 (실제 레버 22.35) | −X 옆면(주머니 뒤 벽)을 베드에 — 옆모습이 베드 면에 그려짐, 서포트 없음; 층 0.1; 채움 100 %, 벽 3; 크기 88.9 × 36.6 × 18.1 | 13.3 | 105 |
| T3 밸런스 핀 높이 게이지 | 발은 레일 윗면, 울타리는 레일 앞면에 대고 핀을 멈춤 면까지 눌러 넣는다. 막대 끝으로 GO는 지나가고 NO-GO에서 멈추면 합격 | T24 발 (레일 윗면에 얹힘) z19.0, 앞 발 y132.3~133.85, 뒤 발 y136.75~137.10, 길이 u −26~26; T26 누름 구멍 Ø2.5, 멈춤 면 z23.30 (발에서 4.30); T28 GO 구간 u ±20~26, 천장 z23.40 (발에서 4.40); T29 NO-GO 구간 u ±16~20, 천장 z23.20 (발에서 4.20) | 뒤집어(쓸 때 윗면을 베드에) — 발·멈춤 면·GO/NO-GO 천장이 모두 윗면으로 뽑힘, 서포트 없음; 층 0.1 (첫 층 0.2) — 높이가 모두 0.1 격자; 채움 100 %, 벽 4; 크기 52 × 7.5 × 18 | 6.3 | 53 |

모두 256 × 256 베드에 들어간다(가장 큰 지그 72 × 222). 220 × 220 베드에서는 지그를 대각선으로 놓는다(45°에서 208 × 208).

**쓰는 법**

1. 준비(한 번): 네 개를 출력한다(지그는 프레임과 같은 층 설정). Ø4.0 드릴로 지그 K·L 구멍과 가짜 레버 허브를 뚫는다. 봉 토막 3개를 자르고 끝을 다듬는다. 강철 블록 1개를 가짜 레버 주머니에 눌러 끼운다(스냅 립). 예비 밸런스 핀 1개를 T3으로 지그 핀 구멍에 눌러 넣는다 — 이것이 T3의 첫 검증이다.
2. 교정(한 번): 건반이 없는 지그의 영점 받침(백 y188.34, 흑 y180.31) 홈에 교정봉을 놓고 가짜 레버를 내린다. 바늘 윗면과 읽기 턱이 손톱으로 같은 높이면 끝이다. 다르면 높은 쪽을 한 번 사포질한다. 백·흑 두 자리의 차이가 흑 1/8회전(바늘 0.22)보다 크면 가짜 레버 밑면을 평평하게 다듬는다.
3. 밸런스 핀(T3, 프레임마다, 모듈을 잇기 전, 조립 1단계): 왼쪽 핀부터. 핀을 구멍에 세우고 누름 구멍을 핀 위에, 울타리를 레일 앞면에 댄다. 발이 레일 윗면에 닿을 때까지 엄지나 바이스로 누른다(망치 금지: 멈춤 면이 파여 모든 핀이 낮아짐). **누른 핀은 바로, 오른쪽 이웃 핀을 꽂기 전에** 게이지를 +X로 옮겨 그 핀이 왼쪽 끝 |<GO로 들어오게 민다: GO는 지나가고 NO-GO에서 멈춰야 한다(꼭대기 z23.20~23.40). GO에서 막히면 다시 누르고, NO-GO를 지나가면 조금 뽑아 다시 누른다. 핀을 다 누른 뒤에는 다른 핀이 게이지에 걸려 확인할 수 없다(r4.4 고침 2).
4. 건반마다(T1 + T2, 조립 2단계): 가짜 레버를 주차 기둥에 젖혀 두고 건반 노치를 K 봉 토막에 끼운다. 가짜 레버를 캡스턴에 내린다 — 손으로 건반을 누르지 않는다. **높이 먼저**: 높이 블록을 머리 옆면에 붙이고 손톱으로 +/− 땅을 본다(백 43.65 / 43.35, 흑 55.65 / 55.35). 높으면 펀칭 1장 더, 낮으면 1장 뺀다(한 장 = 앞 0.25). **캡스턴 나중**: 바늘이 낮으면 캡스턴을 풀고, 높으면 조인다. 돌릴 때는 가짜 레버를 젖히고 육각 렌치를 위에서 넣는다. 1/8회전 = 바늘 0.34(백) / 0.22(흑) mm(확대 5.52 / 3.59배).
5. 출력 검증: 지그는 캘리퍼로 밑면 → K 봉 토막 윗면 20.50, 쉼 선반 윗면 17.05, 영점 홈 바닥 24.00, 읽기 턱 62.50(각 ±0.05). 높이 블록 38.65 / 38.35 / 50.65 / 50.35(각 ±0.03). 핀 게이지는 발 면 → 누름 구멍 바닥 4.30, GO 천장 4.40, NO-GO 천장 4.20(각 ±0.05).

**틈과 주의.** 모듈 건반 12개와 끝 부속 4개의 쉼 자세에서 지그·가짜 레버와 최소 1.62(설계 접촉 제외). 핀 게이지를 프레임에 놓으면 이웃 핀과 1.2, 봉 받침 능선과 0.44(손 공구라 움직이는 부품 규칙 밖). 지그 선반은 온전하므로 F·F#는 프레임에서 약 0.1 높게 쉰다 — 창 ±0.15 안이다. 지그는 프레임 한 대의 자리만 재현하므로 모든 프레임과 지그를 같은 프린터·같은 층 설정으로 뽑는다. 공구는 지금 모델(`final`, r4.5 circuit 2nd, `tools_geometry.json` meta)로 만들었다. 영점 받침 자리 = 모델 캡스턴 y(백 188.34, 흑 180.31, 차이 +0.00 / +0.00).

## 11. 건반 하나 빼기 (도구 없음, 모든 단계를 충돌 검사함)

1. 가림판 띠를 들어낸다.
2. 그 건반이 있는 핀 칸의 패드 바를 앞 손잡이로 잡아 수평으로 당긴다. 잎 돌기가 립 앞끝(y163.5)을 지나면(12.3 mm) 바가 0.3 내려앉아 아래 부분이 립에 얹히고, 립이 21.5 mm까지 받친다. 바 앞부분이 윗판에서 나온 뒤(21.5 mm)부터는 바를 윗판 쪽으로 밀어 올린 채(홈 천장, +1.5) 끝까지 뺀다: 패드와 건반·레버·핀 사이 최소 1.30(PET 심 3장 1.11). 곧게만 당기면 끝에서 흑 패드 모서리가 흑건 윗면 턱 모서리와 -0.39(흑건 뒤끝은 가림판 밑 y144.3~147에서 z54.1로 낮춤)라 밀어 올림을 꼭 한다. 그 칸 레버 3개가 자유로워진다.
3. 한 손 손톱으로 그 건반 레버의 손톱 턱(캐리어 앞 위)을 들어 윗판에 닿을 때까지 올린다(15.5°, 힘 0.47 N). 빼기에 필요한 각은 백 13.1°, 흑 9.2°.
4. 다른 손 손톱을 건반 뒤 윗판 턱(y146~147) 밑에 걸어 위로 당긴다: 백 2.7 N / 흑 2.5 N(스냅 2 N 기준; R2.50 쿠폰이면 5.2 N). 건반이 쉼 패드를 축으로 들렸다가 키퍼에 걸려, 뒤 노치 입술이 봉 위로 0.1 올라온다. 블록은 핀 위로 3.32.
5. 3 mm 앞으로 밀고, 앞을 2°(흑 5°) 들고, 앞으로 뽑는다. 흑건은 양옆 백건을 먼저 뺀다.
6. 레버를 내려놓는다. 건반이 빠진 레버는 0.40 N으로 놓인다: 기판 밖(C·C#·D·A·A#·B)은 바닥판(30.25~30.75° 떨어짐), 기판 위는 실제 BRD-01 배치로 E·F가 4067 모듈 윗면(z20, 13.25 / 13.25°), D#·G#가 기판 위에 매단 보스(Ø6, 레일 뒷면 브래킷 — D#는 나사 보스, G#는 위치 핀 보스; 16.75 / 16.75°), F#·G가 기판 윗면(z10.6, 24.00 / 23.50°) — O1·O7에서는 G가 R301 위(20.75°). (부품 한계 z20을 기판 전체에 두고 재면 13.0~14.3°.) 이때 스프링은 자유각을 지나 풀리지만 다리 끝은 보스 홈 입구 안 1.88에 남는다(자유각 공차 −25°이면 입구 앞 0.01 → 레버를 들면 입구 경사가 다시 받음). 다시 넣을 때는 3번처럼 레버를 들고 반대 순서로, 패드 바는 뒤 멈춤까지 민다.

| 건반 | 당겨 올림 | 3 mm 밀기 | 기울임 | 뽑기 | 가장 가까운 짝 |
|---|---|---|---|---|---|
| D | 0.43 | 0.10 | 0.11 | 0.86 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| E | 0.43 | 0.10 | 0.11 | 0.86 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| B | 0.43 | 0.10 | 0.11 | 0.86 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| C | 0.43 | 0.10 | 0.11 | 0.86 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| F | 0.43 | 0.10 | 0.11 | 0.86 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| C# (양옆 C+D 먼저) | 0.42 | 0.11 | 0.11 | 1.39 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| F# (양옆 F+G 먼저) | 0.42 | 0.11 | 0.11 | 1.39 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |
| A# (양옆 A+B 먼저) | 0.42 | 0.11 | 0.11 | 1.39 | 캡스턴 머리 ↔ 펠트 띠(자기 레버) |

레버를 윗판 멈춤 15.5°보다 0.5° 낮은 15.0°로 잡고 검사했다.

## 12. 조정 절차 (모두 손으로)

| 조정 | 어디서 | 한 단위의 효과 (백 / 흑) |
|---|---|---|
| 업스톱 시점 | 가림판 → 패드 바를 빼서, 패드와 쐐기 사이에 PET 심 0.1 넣고 빼기 | 레버가 0.23° / 0.24° 일찍 = 건반 앞 0.18 / 0.22 mm |
| DW | 가림판을 들고 강철 앞 윗면(패드 앞)에 텅스텐 퍼티 | 1 g = +1.23 / +1.14 g (건반 앞에 붙이면 -1.06 / -1.09 g) |
| 캡스턴 | 건반을 넣기 전 벤치 지그 + 가짜 레버 T2(10.1장): 바늘 ↔ 읽기 턱 (1/8회전 = 캡스턴 0.0625 = 바늘 0.34 / 0.22 mm) | DW +0.20 / +0.11 g, 바닥 캡 높이 +0.19 / +0.12 mm |
| 건반 높이 | 벤치 지그의 쉼 펀칭, 높이 블록 T1b로 확인 (창 ±0.15) | 0.1 mm 한 장 = 건반 앞 0.25 mm |

**업스톱 시점 합격 기준 (r4.1, 종이 띠)**: 패드 바를 뒤 멈춤까지 민 뒤, 두께 0.05 종이 띠(영수증 종이 등)를 건반 앞 펠트 위(백 y3~9, 흑 앞 모서리 밑)에 놓고 건반 앞(백 y13, 흑 앞 + 10)을 추로 누른다. 모델에서 띠가 물리기 시작하는 힘: 백 틈 −0.30 / −0.40(설계) / −0.50 → 0.75 / 0.92 / 1.05 N, 흑 −0.35 / −0.45 / −0.55 → 0.96 / 1.19 / 1.43 N. **합격: 백은 0.75 N에서 띠가 미끄러지고 1.05 N에서 물림, 흑은 0.96 N에서 미끄러지고 1.43 N에서 물림**(= 설계 틈 ±0.1). 먼저(작은 힘에) 물리면(틈이 덜 음수) 패드 밑에 심을 넣고, 늦게 물리면(틈이 더 음수) 심을 뺀다(한 장 = 패드 면 0.1 아래 = 레버가 0.23° 먼저 닿음; r4.4 고침 2b: r4.4 고침 2까지 방향이 반대였음). 뺄 심이 없으면 그 칸 패드 바를 쐐기 0.1 얇게 다시 출력한다 — 단 쐐기 얇은 끝이 0.40 미만인 자리(백 쐐기 0.347~, 끝 부속 A0·B0·C8)는 0.1 얇게 하면 출력 최소 0.3 아래라, 쐐기를 그대로 두고 그 패드 자리의 바 밑면을 0.1 올려(바 1.5 → 1.4) 다시 출력하거나 패드 펠트를 0.1 얇은 것으로 바꾼다(r4.5 고침).

## 13. 예비 건반 보관함 (R29, 안치수 338.8 × 172 × 77)

건반 칸 201.3(여유 1.0 + 건반 199.3 + 여유 1.0) + 칸막이 1.2 + 옆 칸 136.3. 예비 건반은 부품표대로 백 10개(모듈 7 + A0·B0·C8), 흑 6개(모듈 5 + A#0)다. 1층 백건 7개 160.3 × 23.4, 2층 흑 5 + A#0 + A0·B0·C8 139.8 × 35.4, 쌓은 높이 58.8 / 77, 폭 여유 한쪽 5.85.

옆 칸(136.3 × 172 × 77)에는 부품표의 예비를 넣는다: 강철 블록 2, Ø4 봉 2(건반 봉 1 + 레버 봉 1, 길이 161.4를 172 깊이 방향으로), 업스톱 패드 12, 비틀림 스프링 8, 작은 부품 통(밸런스 핀 4, 캡스턴 나사·너트 4벌, 센서 자석 4, PET 심).

레버 캐리어(16곳)와 패드 바(6종)는 위치마다 달라 예비를 두지 않는다(부품표). 필요할 때 위치별 파일로 출력한다(캐리어 약 20분). 출력 공구 가운데 높이 블록·가짜 레버·핀 게이지는 옆 칸에 들어간다(가장 큰 것 88.9 × 36.6). 벤치 지그(72 × 222)는 들어가지 않아 따로 둔다.

## 14. 끝 부속

- 왼쪽 (A0·A#0·B0): 레버 x A0 10.29, A#0 26.30, B0 38.48; 핀 x-1.8~-0.2, x45.2~46.8; 핀 보스(왼/오) 0.00/5.13, 1.37/0.00; 허브 칼라 A0 0.00/2.62, A#0 2.62/0.76, B0 0.76/0.00; 패드 자리 A0 1675, A#0 1200, B0 1564 N/mm; 모든 건반 2.5 m/s 동시에 윗판 9.3 MPa, 핀 이음 4.4 MPa.
  - A0: 캡스턴 y188.43, DW 52.0, UW 42.8, m_eff 56.2; 모듈 패드 면을 그대로 쓰면 자기 정착 바닥에서 강철 ↔ 패드 면 -0.45 (설계 -0.40) → r4.2: 자기 면(기울기 11.44°)으로 쐐기 0.291~2.720 출력 (모듈 0.347~2.757, -0.056 / -0.037)
  - A#0: 캡스턴 y180.31, DW 51.0, UW 40.8, m_eff 46.5; 모듈 패드 면을 그대로 쓰면 자기 정착 바닥에서 강철 ↔ 패드 면 -0.45 (설계 -0.45) → r4.2: 자기 면(기울기 9.63°)으로 쐐기 1.501~3.536 출력 (모듈 1.501~3.536, +0.000 / +0.000)
  - B0: 캡스턴 y188.32, DW 52.0, UW 42.8, m_eff 55.0; 모듈 패드 면을 그대로 쓰면 자기 정착 바닥에서 강철 ↔ 패드 면 -0.39 (설계 -0.40) → r4.2: 자기 면(기울기 11.34°)으로 쐐기 0.359~2.765 출력 (모듈 0.347~2.757, +0.012 / +0.008)
  - 센서 바 x0.5~46.5 (A#0 낮은 구간), 스프링 홈 보스 3, 겹침 0, 스윕 최소 1.31
- 오른쪽 (C8): 레버 x C8 11.75; 핀 x0.2~1.8, x23.5~25.1; 핀 보스(왼/오) 0.00/4.52, 6.32/0.00; 허브 칼라 C8 0.00/0.00; 패드 자리 C8 2446 N/mm; 모든 건반 2.5 m/s 동시에 윗판 3.2 MPa, 핀 이음 1.5 MPa.
  - C8: 캡스턴 y188.48, DW 52.0, UW 42.8, m_eff 56.7; 모듈 패드 면을 그대로 쓰면 자기 정착 바닥에서 강철 ↔ 패드 면 -0.48 (설계 -0.40) → r4.2: 자기 면(기울기 11.49°)으로 쐐기 0.259~2.699 출력 (모듈 0.347~2.757, -0.088 / -0.059)
  - 센서 바 x0.5~23.0, 스프링 홈 보스 1, 겹침 0, 스윕 최소 1.31
- r4.3: 끝 부속에는 제어 기판·RP2040-Zero·USB가 없다(센서는 O1·O7이 EXT로 읽음). 뒤 선반과 뒷벽은 모듈 것을 x74~94 밖에서 잘라 쓰므로 바뀐 것이 없고, 끝 부속 스윕·겹침 검사도 새 모델로 다시 돌렸다.
- r4.4 EL: 센서 기판 x1.0~46.5(센서 바 안), 받침 기둥 x0.5~6.0 + 앞·뒤 리브 x6.0~45.0(z7.0까지), 뒤 리브 틈 x15~38; 리드 5심은 패드(아랫면) → 틈 → 바닥(y77.39까지 모음) → 레일 밑 차선 x13.53~22.48(z5~10) → 뒷벽 홈(z5~12) → 뒤 통로 X401.
- r4.4 ER: 센서 기판 x1.0~23.0(센서 바 안), 받침 기둥 x0.5~6.0 + 앞·뒤 리브 x6.0~21.5(z7.0까지), 뒤 리브 틈 x6~16; 리드 3심은 패드(아랫면) → 틈 → 바닥(y77.39까지 모음) → 레일 밑 차선 x7.59~14.00(z5~10) → 뒷벽 홈(z5~12) → 뒤 통로 X411.

## 15. 출력 계획

| 부품 (88건반 전체 개수, 예비 포함) | 방향·서포트 | 개당 g |
|---|---|---|
| 백건 (7종 + 끝 A0·B0·C8), 62개 | 윗면을 매끈한 PEI에 대고 뒤집어(v3 방향). 트리 서포트는 숨은 빔·꼬리(y146~199) 밑에만. 노치 R2.55는 출력 맨 위의 열린 홈, 밸런스 핀 홈(폭 2.2+천)은 블록 밑면에서 열림 | 모듈 21.68(평균, 21.32~22.14) + 서포트 1.6; 끝 A0 24.1 · B0 21.4 · C8 24.7 |
| 흑건 (4종: C#·D#은 같음, + 끝 A#0), 42개 | 같은 방향(윗면이 베드). 서포트는 빔·꼬리 밑. 납·추 칸 없음 | 16.78 + 서포트 2.9; 끝 A#0 16.8 |
| 레버 캐리어 (위치 16곳, 칼라 14종 — G#·B·B0는 칼라가 같음, 옆벽에 음 이름 새김), 88개 | 옆으로 눕혀(옆벽이 베드, 허브 구멍이 세로). 강철 칸 안에 지지대 1개(z 틈 0.2): 먼 쪽 옆벽·립이 칸 위를 40 mm 건넘. 허브 구멍 Ø3.9로 뽑아 Ø4.0 드릴, 허브 칼라·스프링 주머니 함께 출력 r4.5: 주머니 구간의 짧은 다리 홈(허브 벽을 뚫는 3.0 폭, x 방향 = 쌓는 방향)은 서포트 없이 나오고, 주머니 Ø6.6는 한 층 위에서 다리(bridge)로 덮인다 | 2.84 |
| 프레임 (모듈), 7개 | 바로 세워(v3). 윗판 밑(y146.5~209)은 바닥·선반에서 올라오는 트리 서포트. 패드 바 L 레일(웹 + 립, P13)은 윗판과 한 몸. 핀 보스 구멍 Ø3.9 눈물방울, Ø4.0 드릴 | 284.0 + 서포트 88 |
| 끝 부속 프레임 (왼쪽 A0~B0, 오른쪽 C8), 2개 | 모듈 프레임과 같은 방향(바로 세워, 윗판 밑 트리 서포트). 볼(cheek)·도브테일·이음 핀 보스를 함께 출력 | 93.3(부품표 값, 왼쪽 폭 47 기준) + 서포트 |
| 패드 바 (6종: 모듈 칸 1~4 + 끝 부속 왼·오), 30개 | 윗면을 베드에(쐐기가 위). 앞 손잡이 3 mm, 양쪽 가장자리에 예하중 잎 혀 0.6×1.6×8(0.3 눌림, 레일 립 위) | 2.90(모듈 4개 평균) |
| 레버 봉 끝 마개, 9개 | 끝면을 베드에(원판 Ø4.0 × 1.2). 이음 쪽 핀 보스 구멍에 핀 면과 같게 눌러 끼움 | 0.05 |
| 가림판 띠, 9개 | 넓은 면을 베드에, 걸이 립은 위로 | 6.3 |
| 센서 바, 9개 | v3 (포켓이 위) | 17 |
| 출력 공구 (악기당 1벌), 4개 | 10.1장 표(모두 서포트 없음) | 38.4 / 10.3 / 13.3 / 6.3 |

88건반 전체(모듈 7 + 끝 부속 + v3 기타 출력 + 예비 세트): 필라멘트 6.55 kg, 436 h(15 g/h). 윗판 밑 서포트가 모듈마다 88 g이다(핀 사이 39 mm를 서포트 없이 브리지로 뽑으면 88건반에서 약 0.6 kg 줄어듦 — 단계 0 시험 16). 이 합계에 출력 공구(68 g, 약 8시간)와 단계 0 키트(추정 약 430 g, 15 g/h로 약 29시간; 속을 꽉 채우면 665 g, 17.1장)는 들어 있지 않다. 악기 부품은 모두 220 × 220 베드에 들어간다. 출력 공구와 단계 0 키트는 256 × 256 베드 기준이다(220 베드에서는 벤치 지그만 대각선으로).

## 16. 비용 (v3.2 대비)

| 구분 | 품목 | 수량 × 단가 | 금액 | 근거 |
|---|---|---|---|---|
| 추가 | SS400 평철 9T×19, 1 m 4개 (블록 90 × (40 + 톱날 2) = 3.78 m) | 4 × 3,500 | 14,000 | 추정 (9T×50의 단면 38 %) |
| 추가 | 강철 약 5 kg 택배 | 1 × 5,000 | 5,000 | 추정 |
| 추가 | SUS304 환봉 Ø4 h9 × 4 m (건반 봉 + 레버 봉 2.73 m) | 1 × 7,000 | 7,000 | 추정 (W1) |
| 추가 | M3×6 ISO 7380 버튼헤드 SUS (캡스턴) 100개 + M3 너트 100개 | 1 × 7,000 | 7,000 | 추정 |
| 추가 | 비틀림 스프링 미스미 C-UA90R5-3-0.5 (SUS304-WPB d0.5 ID5 3권 암 90°, 두 다리를 22.3 / 8.0로 잘라 씀) 100개 (88 + 단계 0 시험 4 + 예비 8) | 100 × 310 | 31,000 | 한국미스미 9/28 확인: 100개 이상 282원 + VAT |
| 추가 | 경선(피아노선) 니퍼 — 스프링 다리 200곳 자름 (d0.5 SUS 경강선) | 1 × 15,000 | 15,000 | 추정 (공구, 악기당 1) |
| 추가 | 밸런스 핀 SUS Ø2×12 (ISO 2338) 100개 | 1 × 6,000 | 6,000 | 추정 |
| 추가 | Ø4.0 드릴 | 1 × 2,000 | 2,000 | 추정 |
| 삭제 | v3.2 척추 클램프 M3×40 + 와셔 | 32 × 120 | −3,840 | 추정 |
| 삭제 | 세트스크루 M3×10 평끝 | 32 × 120 | −3,840 | 추정 |
| 삭제 | 황동 원판 8×1 | 32 × 250 | −8,000 | 추정 |
| 삭제 | M3 너트 (클램프 + 세트스크루) | 64 × 30 | −1,920 | 추정 |
| 소모품 | MS 폴리머(하이브리드) 탄성 접착제 튜브 약 80 mL (r4.4 고침 2b: 강철 블록 90개 × 두 옆면 약 0.2 mL; 고침 2의 5분 에폭시 대신) | | 8,000 | 추정 |
| 소모품 | 부싱 천 0.5T (노치·밸런스 핀 홈·탭) A4 한 장 | | 5,000 | 추정 |
| 소모품 | 펠트 1T·1.5T·2T 띠 추가 | | 6,000 | 추정 |
| 소모품 | 미세셀 우레탄 폼 6T (PORON 계열, 업스톱 패드 100개) + 앞 펠트 밑 PU 1T, 약 200×300 | | 15,000 | 추정 |
| 소모품 | OHP 필름 (PET 심 0.1) | | 1,000 | 추정 |
| 소모품 | 흑연 가루 | | 3,000 | 추정 |
| 선택 | 평철 90조각 절단을 철공소에 맡김 (모따기 없음) | | 31,500 | 추정 1개 350원 |
| 선택 | 직접 자를 때 쇠톱·바이스 (90번 약 4시간) | | 0 | 가진 공구 |

기본 구성 변화(소모품 38,000원 제외) +87,000 − 17,600 = +69,400원 → 652,619원(한도 1,000,000, r3 +130,400원). 가격은 모두 추정이다.

r4.5: 비틀림 스프링은 미스미 C-UA90R5-3-0.5 100개 × 310원(282원 + VAT 10 %) = 31,000원(r4.4 주문 제작 추정 100 × 200 = 20,000원), 다리 200곳을 자를 경선(피아노선) 니퍼 15,000원(추정)을 새로 넣었다 → 기본 구성 변화 +43,400 → +69,400원.

r4.4: 출력 공구는 살 것이 없다(봉 토막·핀·강철은 위 목록의 것을 씀). USB-C 선을 CVILUX DH-20M50052로 바꾸면 회로 쪽 구매 목록(C04 줄)이 +27,784원이다 — 이 표(W1 액션) 밖이다(1d-3장).

## 17. 단계 0 시험 계획 (합격 / 불합격 숫자)

시편: 프레임 조각 S1(모듈 x0~85, 건반 C~F, 핀 3개, 윗판·패드 바 포함) + 봉 2 + 레버(강철·스프링) + 패드. r4.3 글의 ‘D·D#·E 3건반 조각’은 C# 자리가 없고 패드 바 두 칸에 걸쳐 S1으로 바꿨다(FE로 S1의 C# 자리 강성은 모듈과 0.7 % 차이, 17.1장). 출력 시편·지그는 17.1장의 단계 0 키트다.

| # | 시험 | 방법 | 합격 | 불합격이면 |
|---|---|---|---|---|
| 1 | 패드 반발 (가장 먼저) | 레버(강철 + 캐리어)를 패드 바에 붙인 패드로 PLAY 속도에 휘둘러 되튐 각속도를 240 fps로 잼(계 전체 e). 후보: ① 미세셀 우레탄(PORON 계열) 6T + 펠트 1T, ② Sorbothane 계열 점탄성 PU 시트(카탈로그 Lupke 반발 10~15 %, 곧 판 하나의 자유 낙하 e ≈ 0.32~0.39), ③ ① 위에 부틸 고무 1T | 실효 e ≤ 0.07 (설계 0.06) | ① e 0.10~0.15: 쐐기를 다시 뽑아 틈 −0.60 / −0.65 + 폼 E 1.4 (계산: e 0.15에서 백 들림 0.116, 흑 ABUSE 0.197, 연타 17.6 / 20.8 Hz, 0.45 N 유령 99 % / 77 %는 모두 거름). ② e > 0.15: 다른 후보로(e 0.25면 백 들림 0.208, 흑 ABUSE 0.400로 한계 끝, 백 ABUSE 키퍼 -0.16) |
| 2 | 패드 강성 | 패드를 강철 조각으로 눌러 힘-눌림 | 25 % 압축 0.36 MPa ± 30 % (E 0.7~1.4 MPa) | 두께·등급 교체. E 0.7이면 흑 ABUSE 들림 0.310 |
| 3 | 패드 자리 처짐 | 윗판 C# 자리에 100 N, 그리고 C~F 6자리에 60 N씩, 다이얼 게이지 | 한 자리 ≤ 0.12 mm (830 N/mm, 설계 1490), 6자리 각 ≤ 0.13 mm (460 N/mm, 설계 492) | 띠 E가 낮으면 윗판 채움 100 % 다시, 그래도면 `plate_t` +0.6~1.2(17.1장 시험 3 표); 킬·레일 이음은 시험 21로 본다(F\|F# 핀은 바닥에 서지 않고 킬로 레일에 붙음 — r4.4 고침 2b부터 기판 밑 바닥은 구멍) |
| 4 | 앞 펠트 | 강철 공 낙하 + 누름 | 실효 e ≤ 0.22 | PU를 두껍게 |
| 5 | 스냅 노치 반지름 쿠폰 | R2.50 / 2.525 / 2.55 / 2.575 / 2.60에 천 0.5T, 빠짐 힘(용수철 저울)과 끼운 채 DW 변화 | 빠짐 1~2 N, DW 변화 ≤ 0.5 g | 다음 반지름 |
| 6 | 탭 천 쿠폰 | 흑 탭 6.9 + 천 0.4 / 0.5 / 0.6T를 벽 사이 8.0에 | 걸림 없이 옆 놀음 ≤ 0.1 | 천 두께 바꿈 |
| 7 | DW/UW | y13(흑 앞 + 10)에 저울·추 | DW 47~55 g(립 y0 ≥ 47), UW ≥ 20 g | 퍼티; 스프링 다리 홈 위치 |
| 8 | 비틀림 스프링 (r4.5 미스미, r4.5 고침 가둠 홈) | C06 시험대로(C06b = 모델 주머니 단면, 진짜 Ø4 봉 — 코일 뜸도 잼) 쉼·바닥 토크, k_t, 자유각; 손 들기 25°로 1시간 둔 뒤 자유각 다시; 가둠 홈 폭(0.5 날) | 쉼 4.19, 바닥 6.03 N·mm ± 15 %, 자유각 -28.4 ± 5°, 1시간 뒤 자유각 변화 ≤ 2° | 덜 감김: 뒷벽 홈 바닥 깊게 ≤ 0.6 mm(+1.6°), 더 모자라면 `spring_notch_rot`(가둠 홈을 돌려 캐리어 다시 출력); 더 감김: 홈 바닥 얕게; 1시간 뒤 자유각이 줄면 손 들기를 카탈로그 토크 한계 각 아래로(18장) |
| 9 | 복귀 시간 | 240 fps, 1 N 1 s 누른 뒤 뗌; 건반 뺀 레버를 다시 들어 스프링 다리가 홈에 다시 걸리는지 | t50 ≤ 37.6 ms, 끝까지 ≤ 60 ms; 다리 10번 모두 다시 걸림 | 스프링 감는 각 +10°; 홈 입구 경사 키움 |
| 10 | 노치 들림 + 입술 천 마모 | 노치 옆 흰 점 240 fps, 1.5 / 2.5 m/s급 뗌·누름 10회, 6건반 화음 1.0~1.5 m/s; 흑건 하나를 PLAY 1.5 m/s로 10^5회(흑은 들림 0.06에서도 입술 모서리가 2.5 N 안팎으로 닿음) | PLAY ≤ 0.20, ABUSE ≤ 0.40, 빠지지 않음; 입술 천 닳아 뚫림 없음, 빠짐 힘 변화 ≤ 30 % | 패드·앞 펠트를 합격선 쪽으로; 천을 두꺼운 것으로 |
| 11 | 유령 | 1.5 / 1.0 / 0.8 m/s 뒤 0.45·0.6·1 N 누름, 6건반 화음 0.8~1.5 m/s, 거름 켜고 끔; 펌웨어가 의심 상태의 다시 눌림 시각(note-on부터)을 기록 | 거름(문턱 0.3 m/s, 재무장 250 ms, 다시 눌림 500 ms)을 켜면 재타건 없음; 기록된 유령 다시 눌림 ≤ 500 ms | 거름 비율 25 → 30 %; 유령 다시 눌림이 500 ms를 넘으면 창 = 가장 늦은 것 + 100 ms |
| 12 | 패드 바 놀음·빼기 | 패드 바를 뒤 멈춤까지 넣고 위아래로 흔듦 — 넣은 직후와 40 °C 1주 뒤(잎 상시 굽힘 8.2 MPa의 크리프); 빼기를 흑 칸에서 10번(21.5 mm부터 밀어 올림) | 상하 놀음 없음(잎이 바를 자리에 밀어 올림), 패드 펠트가 흑건에 닿은 자국 없음 | 잎 눌림 0.3 → 0.5 또는 잎 두께 0.8; 그래도 늘어지면 바 윗면을 사포로 맞춰 레일에 빡빡하게(손 맞춤) |
| 13 | 스프링 넣기 (r4.5 고침 가둠 홈) | C16a 캐리어 3개에 짧은 다리 끝부터 가둠 홈을 따라 스프링을 밀어 넣음(긴 다리 +x 끝), 봉을 꿰고 긴 다리를 뒷벽 홈에 밑에서 넣음; 레버를 −31°~+18°로 돌림 | 짧은 다리 끝부터 가둠 홈(폭 0.70)을 따라 밀어 넣으면 코일이 주머니에 앉고 짧은 다리가 홈 끝까지 들어감 (3/3); 긴 다리가 코일 +x 끝; 레버 −31°~+18°에서 긴 다리가 창 면에 끌리지 않음 | 짧은 다리가 홈에 안 들어감 (홈이 좁게 나옴) → 0.5 날로 홈을 다듬음; 3개 다 그러면 `spring_notch` 놀음 +0.1 후 run_all; 짧은 다리가 홈에 맞지 않음(각이 틀림) → 스프링을 뒤집어 넣음 — 긴 다리가 +x 끝이어야 함; 긴 다리가 창 면에 끌림 → spring_window 면 +2.6 → +2.8 |
| 14 | 종이 띠 시점 | 12장 기준(0.05 띠) | 백·흑 모두 합격 띠 안 | PET 심 |
| 15 | 피로 | Z 방향 핀-윗판 이음 시편 반복 인장 | PLAY 한 건반 1.3 MPa 10^6회, 화음 4.2 MPa 10^4회 균열 없음 | 이음 모서리 살 3 mm |
| 16 | 윗판 출력 | 모듈 프레임 조각을 서포트 없이 브리지 | 핀 사이 39 mm 브리지가 처짐 ≤ 0.3 | 트리 서포트 (88 g) |
| 17 | 느낌 | 직접 쳐 봄: y90 131 g, 1 N에서 흑 바닥 0.27 mm 부드러움 | 받아들일 만함 | 흑 틈 −0.45 → −0.3 |
| 18 | 90° 세움 | 모듈 조각을 뒤로 세웠다 눕힘 | 모든 건반 제자리(앞 높이 ±0.2) | 쿠폰 반지름을 한 단계 작게 |
| 19 | USB 케이블 맞춤 (r4.3) | 뒤 선반 홈·뒷벽 개구가 있는 프레임 뒤 조각 + 핀 헤더에 세운 RP2040-Zero에 실제 USB-C 케이블을 10번 꽂고 뺌 | 몰드 ≤ 12.5 × 7.6(z10.7~18.3), 홈 가장자리·리브·핀과 1 mm 이상 떨어짐, 케이블이 뒤 통로로 꺾여도 리셉터클을 비틀지 않음 | 1d-3장의 확인된 선(CVILUX DH-20M50052, 11.97 × 6.42 × 20.93)으로 바꿈 |
| 20 | 강철 유지 (r4.4 고침 2·2b: 탄성 접착) | C16a(생산 캐리어 C, 3개) + C16b 받침: 스냅만(1개) 강철을 누름 코로 눌러 빠지는 힘을 잼(모델 30 ~ 47 N); MS 폴리머로 접착한 2개를 24 h 굳히고 5 ↔ 45 °C 3번 뒤 117 N(ABUSE의 1.5배)으로 10 s × 3, 1 m 낙하 3번; 10^5회(매 음 52 N)는 캠 장치 또는 완성 모듈 1주 연주 뒤 다시 | 접착: 온도 순환 뒤에도 강철이 캐리어에 대해 0.05 mm 넘게 움직이지 않음, 흰 줄·균열·들뜸 없음, 낙하 뒤 그대로 | 접착면 사포질·탈지 다시, PETG 프라이머 + 같은 MS 폴리머 또는 다른 MS 폴리머 제품(단단한 에폭시는 안 됨 — 열팽창); 그래도 안 되면 옆벽 0.7 → 1.0(레버 폭 11.2, 배치 다시) |
| 21 | 첫 모듈 정하중 (r4.5 고침; 하중 방향은 r4.5 고침 3) | 조립한 첫 모듈을 C17a 받침 빗에 얹음: 핀 선 x1.0 / 41.7 / 123.9 / 163.5 밑과 뒷벽 밑만 받침, 레일 밑 x43.2~122.4와 기판 구멍 밑은 빔, 모듈 밑 EVA는 뗌. D-D#-E-F-F#-G 여섯 패드 자리 위 윗판에 6 × 60 N(36.7 kg) 판재·물통, 다이얼로 E·F 자리 처짐. 쓰임에서는 패드가 윗판을 밑에서 밀어 킬이 레일을 들어 올린다. 모델이 선형이라 이 받침에서 위로부터 누르면 같은 레일 휨이다 | E·F ≤ 0.13 mm (모델 0.121; 레일 받침의 두 끝: 단단 0.094, 이웃 핀 선 사이 단순 지지 0.159 — 불합격) | run_all의 화음 자리 강성 `k_ch`를 잰 값(60 N ÷ 처짐)으로 바꿔 화음 자리 동역학(들림 0.20, 키퍼, 유령)을 다시 봄; 그래도 불합격이면 회로 세션과 리본 차선 위 레일 높이를 다시 정함(킬 z19.3과 핀 앞끝 y148.6은 이미 건반 F와 1.3 한계) |

### 17.1 단계 0 시험 키트 (r4.4, 남은 문제 7)

여기서는 아무도 물리 시험을 할 수 없다. 그래서 집에 있는 도구로 위 시험을 할 수 있게 출력 시편, 재는 법, 합격 숫자, 결과마다 바꿀 모델 값을 모았다. `stage0/make_stage0.py`가 지금 모델(`final`, r4.5, metrics.json)에서 만들었고, 모델에 없는 값은 ‘제안’이라고 적었다. 위 21개 시험에 모델 밖 시험 3개를 더했다: P 밸런스 핀 압입, C 캡스턴 너트 트랩, T 펠트·천 두께. 출력 시편은 34종 36개다(C01a~C17a; C16a는 3개). 모두 PETG, 서포트 없음, 닫힌 몸 STL이다. 256 × 256 베드에 들어가고, 가장 큰 것(C17a)이 212 × 164.5라 220 베드에도 들어간다. 속을 꽉 채우면 PETG 665 g(532 cm³)다. 채움 40 % 부품을 공구와 같은 계수 0.62로 줄이면 약 430 g, 15 g/h로 약 29시간이다(추정). 시험 20(강철 유지, r4.4 고침 2)은 C16a(생산 캐리어를 모델에서 그대로)·C16b로 한다.

- 절차: `stage0/stage0_procedure.md` (준비물, 출력 설정, 시험마다 재는 법·계산·합격·결과 표). 결과 기록표: `stage0/stage0_results_template.csv`(판정 O/X). 시편 치수·합격선·결과 대응: `stage0/stage0_geometry.json`. 시편 파일: `stage0/stl/<ID>.stl`, 두 방향 그림 `stage0/png/`, OpenSCAD 원본 `stage0/scad/`.
- 결과를 모델에 넣는 법: 기록표를 채우고, 바뀐 값만 `model_v4.py`의 `P`에 넣고, `run_all.py`를 다시 돌려 0.2장의 목표가 모두 통과인지 본다. 통과하지 않으면 아래 표의 다음 대안으로 간다. 모델에 아직 없는 값(시험 P의 핀 구멍 Ø, 시험 C의 너트 홈 폭·잠김 구멍 Ø)은 새 매개변수로 넣고 geometry에 내보낸다.

**키트를 만들며 찾은 것.** (1) 6건반 화음 자리의 여유가 6.4 %뿐이다(설계 492, 합격선 460 N/mm). 출력한 윗판의 실효 E가 1825 MPa(모델 1950의 93.6 %)보다 낮으면 불합격이다. 그래서 굽힘 띠 C03a를 시험 3의 핵심으로 넣었다. (2) 시험 3 시편은 S1(C~F)이다(위). (3) 패드 반발을 재는 방법이 D11(60 g 추를 2.5 m/s로 떨어뜨림)과 17장(레버를 휘두름)에서 다르다. 모델 정의(`PadTable.calibrate`: 레버 혼자, 단단한 자리, PLAY 각속도)에 맞춰 C01 진자대를 기준으로 삼았다. θ0 150°에서 PLAY 각속도의 96 %가 나오고, 마찰 보정 식에서 레버 질량과 무게중심이 지워진다. (4) 노치 R2.525 이하는 입술이 닿는 들림(0.095)이 PLAY 최대 들림(0.161)보다 작아, 그 R을 고르면 들림 판정을 다시 세워야 한다. R2.55 흑 추정 빠짐 힘은 1.33 N이다.

| 시험 | 시편 (`stage0/stl/`) | 합격 | 결과 → 모델에서 바꿀 값 |
|---|---|---|---|
| 1 패드 반발 (계 실효 e) | C01a 패드 반발 진자대 · C01b 시험 레버 · C01c 패드 받침판 · C01d 봉 끝 칼라 | e ≤ 0.07 (설계 0.06) | e ≤ 0.07 → pad_e = 측정값; 0.07 < e ≤ 0.10 → pad_e = 측정값, 다른 합격선(E·앞 펠트)은 공칭이어야; 0.10 < e ≤ 0.15 → 대안 ①: gap_us_w −0.40 → −0.60, gap_us_b −0.45 → −0.65 (PET 심 2장 더), pad_E 1.4; e > 0.15 → 다른 패드 후보 (② 점탄성 PU, ③ 부틸 1T 덧댐) |
| 2 패드 강성 | C02a 패드 압축 지그 · C02b 패드 압축 누름 막대 | 25 % 압축(1.75 mm)에서 18.3~36.7 N (E 0.7~1.4 MPa, 설계 26.2 N) | E < 0.7 → 두꺼운/단단한 등급; 0.7 ≤ E ≤ 1.4 → pad_E = 측정값; E > 1.4 → pad_E = 측정값, 윗판 하중 다시 |
| 3 윗판 패드 자리 처짐 (굽힘 띠 E + 프레임 조각) | C03a 윗판 굽힘 띠 · C03b 3점 굽힘 받침 · C03c 누름 코 · C03d 다이얼 게이지 스탠드, 낮은 · C03e 다이얼 게이지 스탠드, 높은 | 띠 E_eff ≥ 1825 MPa (화음 자리 460 N/mm), 프레임 C# 자리 다이얼 점 처짐 ≤ 0.103 mm @ 98 N | r = E_eff/1950 ≥ 0.936 → (선택) E_PETG = 1950 r; 0.862 ≤ r < 0.936 → 윗판 채움 100 % 다시; 그래도면 plate_t +0.6 (z_top 73.45); 0.810 ≤ r < 0.862 → plate_t +1.2 (z_top 74.05 — 높이 목표 z74를 0.05 넘음, +1.15까지); r < 0.810 → 재료·설정 바꿈 (다른 PETG, 온도) |
| 4 앞 펠트 반발 | C15a 앞 펠트 반발 낙하관 | e ≤ 0.22 (1.5 m/s 낙하 114.7 mm에서 되튐 ≤ 5.55 mm) | e ≤ 0.22 → front_e = 측정값; 0.22 < e ≤ 0.28 → front_e = 측정값 후 run_all; e > 0.28 → 펠트 밑 PU 1T → 2T (앞 레일을 1.0 낮게: w_felt_line) |
| 5 스냅 노치 반지름 | C04a 스냅 노치 반지름 쿠폰 · C04b 스냅 노치 반지름 쿠폰 · C04c 봉 받침 | 빠짐 힘 1~2 N (백·흑 모두), 끼운 채 DW 변화 ≤ 0.5 g | R2.5 → notch_R = 2.5; lift_play = 0.000, lift_popout = 0.750, lift_abuse = 0.375; R2.525 → notch_R = 2.525; lift_play = 0.095, lift_popout = 0.775, lift_abuse = 0.387; R2.55 → notch_R = 2.55; lift_play = 0.200, lift_popout = 0.800, lift_abuse = 0.400; R2.575 → notch_R = 2.575; lift_play = 0.318, lift_popout = 0.825, lift_abuse = 0.413; R2.6 → notch_R = 2.6; lift_play = 0.459, lift_popout = 0.850, lift_abuse = 0.425 |
| 6 가이드 탭 천 | C05a 가이드 탭 날 · C05b 건반 홈 쿠폰 | 10원 동전 올린 홈 쿠폰이 저절로 내려감(끌림 ≤ 0.02 N), 옆 놀음 < 0.1 (PET 심 0.1이 안 들어감) | 헐거움 (심 들어감) → 천 한 단계 두껍게 또는 날 +0.1 (tab_w_b / tab_w); 걸림 → 천 한 단계 얇게 또는 날 −0.1; 둘 다 통과 → tab_w_b·tab_w·tab_cloth = 고른 값 |
| 7 DW / UW (조립 건반) | C14a 추 컵 | DW 47~55 g (y13 / 흑 앞+10), 립 y0 ≥ 47 g, UW ≥ 20 g | DW 높음/낮음 → 퍼티 강철 앞 1 g = +1.23 / +1.14 g, 캡스턴 1/8회전 = +0.20 / +0.11 g |
| 8 비틀림 보조 스프링 | C06a 비틀림 스프링 시험대 · C06b 스프링 북 · C14a 추 컵 | k_t 8.4 ± 15 %, 자유각 -28 ± 5°, 쉼 4.19 / 바닥 6.03 N·mm ± 15 % | 자유각 벗어남 Δ° → spring_free_deg = 측정값; 덜 감김(자유각이 +쪽으로) > 5° → 뒷벽 홈 바닥을 더 깊게는 0.6 mm까지만(뒷벽 살 0.4 남김) = +1.6°; 더 모자라면 `spring_notch_rot`(가둠 홈을 CW로 Δ° 돌림, 캐리어 다시 출력) 또는 스프링 다시 주문; 더 감김(자유각이 −쪽으로) > 5° → 뒷벽 홈 바닥을 얕게(앞으로) 0.367 mm/° 옮김 (보스 3.2 안에서 자유); 쉼 토크가 모델보다 10 % 넘게 낮고 짧은 다리가 홈 바깥 면에서 떨어져 보임 → 가둠 홈 폭 재기(0.5 날·틈새 게이지): 넓으면 `spring_notch` 놀음 = 잰 폭 − 0.5 후 run_all; k_t 벗어남 → spring_kt = 측정값 후 run_all (연타·복귀) |
| 9 복귀 시간 (조립 건반) | 조립 모듈 | t50 ≤ 37.6 ms, 끝까지 ≤ 60 ms, 스프링 다리 10/10 다시 걸림 | 느림 → spring_free_deg −10° (감는 각 +10°) |
| 10 노치 들림·입술 천 마모 (조립) | 조립 모듈 | PLAY ≤ 0.20, ABUSE ≤ 0.40, 빠지지 않음 | 17장 표의 ‘불합격이면’ |
| 11 유령 (조립, 펌웨어 거름) | 조립 모듈 | 거름(0.3 m/s, 25 %, 재무장 250 ms · 다시 눌림 500 ms, 모두 note-on부터) 켜면 재타건 없음; 기록된 유령 다시 눌림 ≤ 500 ms | 유령 다시 눌림 > 500 ms → ghost_rep_max = 가장 늦은 것 + 100 ms (펌웨어 상수, SCH-03 주 9) |
| 12 패드 바 놀음·잎 크리프 | C10a 패드 바 잎 혀 쿠폰 · C10b 잎 크리프 받침 · C10c 잎 힘 측정 받침 | 40 °C 1주 뒤 잎 힘 ≥ 처음의 50 % (0.3 눌림), 바 상하 놀음 없음 | 남은 힘 ≥ 50 % → 그대로; 17~50 % → bar_leaf 두께 0.6 → 0.8 권장; < 17 % → bar_leaf (0.8, 1.6, 8, 0.5) 또는 손 맞춤 |
| 13 스프링 넣기 (조립, r4.5 고침 2 가둠 홈) | C16a 레버 캐리어 · C06b 스프링 북 | 짧은 다리 끝부터 가둠 홈(폭 0.70)을 따라 밀어 넣으면 코일이 주머니에 앉고 짧은 다리가 홈 끝까지 들어감 (3/3); 긴 다리가 코일 +x 끝; 레버 −31°~+18°에서 긴 다리가 창 면에 끌리지 않음 | 짧은 다리가 홈에 안 들어감 (홈이 좁게 나옴) → 0.5 날로 홈을 다듬음; 3개 다 그러면 `spring_notch` 놀음 +0.1 후 run_all; 짧은 다리가 홈에 맞지 않음(각이 틀림) → 스프링을 뒤집어 넣음 — 긴 다리가 +x 끝이어야 함; 긴 다리가 창 면에 끌림 → spring_window 면 +2.6 → +2.8 |
| 14 종이 띠 시점 (조립) | 조립 모듈 | 백 0.75 N 미끄러짐·1.04 N 물림, 흑 0.96 N·1.43 N | 먼저 물림 / 늦게 물림 → PET 심 빼기 / 넣기 |
| 15 층간 강도 (핀-윗판 이음) | C12a 층간 인장 쿠폰 | 층간 인장 강도 ≥ 30 MPa (= s_rare × 2) → 끊김 ≥ 108 N | ≥ 30 MPa → 그대로; 11.5~30 MPa → s_rare = 강도/2, s_cyc = 강도/6 로 모델 한계 바꿈; 이음 모서리 살 3; < 11.5 MPa → 출력 온도↑·팬↓, 이음 모서리 살 3 mm |
| 16 윗판 브리지 출력 | C11a 윗판 브리지 출력 쿠폰 | 서포트 없이 핀 사이 39.86 브리지 처짐 ≤ 0.3, 레일 립이 섬, 1.5T 띠가 레일에 들어감 | 처짐 > 0.3 또는 립 늘어짐 → 트리 서포트 유지 (§15, 모듈 88 g) |
| 17 느낌 | 조립 모듈 | 받아들일 만함 (y90 131 g, 흑 1 N 바닥 0.27 mm) | 흑 바닥이 무름 → gap_us_b −0.45 → −0.30 |
| 18 90° 세움 | 조립 모듈 | 모든 건반 제자리 (앞 높이 ±0.2) | 빠짐 → 노치 R 한 단계 작게 |
| 19 USB-C 케이블 맞춤 | C13a USB-C 몰드 게이지 | 몰드 ≤ 12.5 × 7.6 × 25 (게이지 통과), 실제 프레임에서 홈 가장자리와 1 mm 이상 | 게이지 안 들어감 → 1d-3장의 확인된 선 CVILUX DH-20M50052(11.97 × 6.42 × 20.93)로 바꿈(회로 인터페이스는 고정; `stage0_geometry.json` 시험 19의 ‘몰드 폭 ≤ 11 케이블로’는 이것으로 바뀜) |
| 20 강철 블록 유지 (캐리어 스냅 + 접착) | C16a 레버 캐리어 · C16b 강철 누름 받침 · C03c 누름 코 | MS 폴리머로 접착한 캐리어: 5 ↔ 45 °C 3번 뒤 117 N(ABUSE 78.1 N의 1.5배)을 10초씩 3번 눌러 강철이 캐리어에 대해 0.05 mm 넘게 움직이지 않음, 흰 줄·들뜸 없음; 1 m 낙하 3번 뒤 그대로 | 스냅만(접착 없이) 빠지는 힘 ≥ 117 N → carrier_wall_plate 받침 조건(clamped) — 접착은 그대로 두는 것을 권함(립 뿌리 응력은 여전히 한계 위); 접착 캐리어가 움직임 / 흰 줄 / 온도 순환 뒤 들뜸 → 접착면 사포질·탈지 다시, PETG용 프라이머 + 같은 MS 폴리머, 다른 MS 폴리머 제품; 단단한 2액형 에폭시는 쓰지 않음(열팽창 차이, DESIGN 1e 고침 2b); 그래도 안 되면 옆벽 0.7 → 1.0(레버 폭 11.2, 배치 다시) |
| 21 첫 모듈 정하중 (조립 모듈, 쓰임과 같은 레일 휨) | C17a 정하중 받침 빗 | C17a 위에서 D-D#-E-F-F#-G 여섯 자리 × 60 N: E·F 자리 처짐 ≤ 0.13 mm (= 60 N ÷ 460 N/mm) | E·F > 0.13 → run_all 화음 자리 강성 k_ch = 60 N ÷ 잰 처짐으로 화음 자리 동역학(들림 0.20, 키퍼, 유령) 다시; 그래도 불합격 → 회로 세션과 리본 차선 위 레일 높이를 다시 정함 |
| P 밸런스 핀 압입 (모델 밖 제안) | C07a 밸런스 핀 압입 레일 쿠폰 · C07b 핀 돌출 게이지 | 돌출 4.30 ± 0.1 (핀 꼭대기 z23.30), 누름 힘 15~80 N (제안), 흔들림 없음 | 고른 구멍 Ø → 새 값 P['pin_hole_print'] (모델에 없음 → 추가), 레일 구멍으로 geometry에 내보냄 |
| C 캡스턴 너트 트랩 (모델 밖 제안) | C08a 캡스턴 너트 트랩 빔 쿠폰 · C14a 추 컵 | 너트가 뒤집어도 안 빠짐, 돌림 토크 3~40 N·mm (제안), 8×1/8회전 = 0.50 ± 0.05 mm, 20번 조정 뒤 토크 ≥ 3 N·mm | 고른 변형 (홈 폭 / 구멍 Ø) → 건반 빔 너트 홈 폭·자가 잠김 구멍 Ø를 모델 key_body 'nut trap'에 넣음 (지금 5.6 / Ø2.8) |
| T 펠트·천 두께 (모델 밖 기준, 조정 환산) | C09a 두께 측정 받침 · C09b 누름판 | 공칭 ±10 % (제안); 벗어나면 절차 파일의 환산표로 조정량 | 17장 표의 ‘불합격이면’ |

## 18. 남은 위험

- **6건반 동시 화음의 유령은 펌웨어에 기댄다.** r4.1에서 화음 자리가 492 N/mm로 굳었어도 0.45~0.6 N 가벼운 누름은 기계적으로 재무장한다(7.4). 거름 규칙(문턱 0.3 m/s, 25 %, note-on부터 재무장 250 ms · 다시 눌림 500 ms)이 모두 버리지만(한계와의 여유 최소 0.22 m/s), 규칙을 끄면 유령이 난다. 모델에서는 재무장한 건반이 1.5 s 안에 스스로 다시 닿지 않아(뜬 채 붙잡힘) 창 500 ms는 손가락의 다시 눌림을 기준으로 잡은 값이다 — 단계 0 시험 11 기록으로 확인. 대가: 재무장 뒤 note-on부터 500 ms 안에 앞 음의 1/4보다 느린 진짜 재타건은 모든 세기에서 버려진다.
- **모델 하한 v_floor 0.1 모서리.** 접촉 감쇠의 시작 속도 하한을 0.1로 두면 6건반 화음 1.45~1.5 m/s에서 들림 0.219(0.20 초과 0.019, 입술이 잠깐 닿음), 한 건반은 0.198. 공칭 하한 0.02와 모든 합격선 재료에서는 0.20 아래다. 단계 0 시험 10(화음 포함)으로 확인한다.
- **패드 재료값(가장 큰 위험).** 모든 결과는 계 실효 e 0.06(합격선 0.07), 폼 E 1.0 MPa 가정이다. 카탈로그 재료 하나의 자유 반발은 이보다 크다(Sorbothane Lupke 반발 10~15 % → e ≈ 0.32~0.39). e 0.15면 백 0.45 N 유령 98 %(거름), 흑 ABUSE 들림 0.398; e 0.25면 백 PLAY 들림 0.208(0.20 초과), 백 ABUSE 키퍼 -0.16(닿음), 흑 ABUSE 0.400(한계). 대안 ①(틈 −0.60 / −0.65 + E 1.4)은 e 0.15에서 들림 0.116 / ABUSE 0.197로 되돌린다. 단계 0 시험 1을 가장 먼저 한다.
- **만능기판 홈.** F|F# 핀이 바닥에 닿으려면 기판 앞쪽에 폭 2.8, 깊이 26.5의 홈을 내고 x81.22~85.42(y145.5~173.2, r4.3: 핀 면에서 1.2)에 부품·배선·리본 헤더를 두지 않아야 한다(BRD-01은 지킴). 기판 배치를 이미 만들었다면 이 띠를 옮겨야 한다. 홈을 못 내면 화음 자리가 196 N/mm로 돌아가 r4.0의 화음 들림(1.3~1.4 m/s 0.23)이 되살아난다.
- **제어 기판 인터페이스(r4.3, 회로 쪽 확인 필요).** (1) USB-C 케이블 몰드는 12.5 × 7.6 × 25(z10.7~18.3) 이하여야 한다. 지금 구매 목록의 Coms NA993은 몰드 치수가 공개되지 않아 확인이 안 된다. 몰드가 실측으로 확인되고 한계 안에 드는 CVILUX DH-20M50052로 바꾸기를 권한다(1d-3장, +27,784원). 받은 선은 캘리퍼·C13a 게이지·시험 19로 확인한다. (2) RP2040-Zero 윗면 부품과 헤더 핀 끝은 z16.3 이하, 기판 뒤끝 y194.5~195.5 띠의 모든 것은 z16.7 이하여야 한다(선반 밑면 z18.05와 1.3). (3) EXT 선(O1·O7)은 아랫면 납땜 → 기판 밑 → USB 터널 플러그 밑으로만 나갈 수 있다(J302 뒤 선반 밑 칸은 뒷벽이 막힘). (4) 금지 구역 x81.22~85.42, y145.5~173.2(만능기판 위 핀·패드·배선; r4.4: 제로 PCB만 y172.0~173.2에 걸침 — P23). (5) F·F# 쉼 펠트가 F 59 % / F# 55 %만 앉아 두 건반이 약 0.1 높게 쉬므로 펀칭으로 맞춘다. (6) F|F# 핀 밑면(z21.5)이 발 뒤 y170.7에서 뒷벽 y209까지 38.3 mm 다리(bridge)가 된다(r4.2는 얇은 선반까지 25.8 mm) — 윗판 밑 트리 서포트와 함께 받쳐 출력한다. (7) r4.4: 끝 부속 리드 W401·W411은 뒤 리브 틈 → 바닥 → 레일 밑 차선 → 뒷벽 홈으로만 나간다(EL은 A#0 흑 탭 받침 왼쪽); 리드를 차선 밖으로 두면 레일·뒷벽에 막힌다.
- **마찰 2배 DW 56.5 / 56.1 g은 55 g을 넘는다.** r3와 같은 수준이다. 단계 0 마찰이 계산의 2배에 가까우면 캡스턴 펠트에 PTFE 필름, 가이드 천을 얇게.
- **흑건 바닥이 부드럽다.** 1 N에서 흑건 앞이 펠트 위 0.27 mm에 멈추고 2 N에서 닿는다(레버가 패드에 먼저). 느낌 판정에서 거슬리면 흑 틈을 −0.3으로(ABUSE 들림 연구값 0.30).
- **비틀림 스프링은 미스미 기성품(C-UA90R5-3-0.5), 두 다리를 잘라 쓴다(r4.5).** 자른 다리 길이가 곧 강성이다(긴 다리 1 mm → k_t 약 0.5 %). 자유각 공차가 ±5°를 넘으면 건반 뺀 레버(−31.3°)에서 다리가 홈 입구 앞 0.01까지 나온다(입구 경사가 다시 받음; 단계 0 시험 9). r4.5 고침: 짧은 다리를 가둠 홈(폭 0.70)에 넣어 예하중은 홈이 정한다 — 홈이 0.30 넓게 나오면 쉼 토크 4.19 → 3.75 N·mm(DW 약 1.2 g), 봉과 틈 0.17; 0.15 좁으면 4.41 N·mm, 더 좁으면 선이 들어가지 않아 0.5 날로 다듬는다(시험 8·13). 두 닿는 점(다리 끝·주머니 가장자리, 손 25°에서 1.36 N)의 PETG 모서리가 오래 눌려 크리프하면 쉼 토크가 조금 준다 — 시험 8의 1시간 뒤 다시 재기로 본다.
- **킬 뿌리와 밸런스 레일(r4.5 고침).** 화음 자리 491.6 N/mm는 레일 + 바닥 띠를 모듈 핀 선에서 받친 연속 보(앞 바닥판 없음)로 본 값이고 합격선 460의 1.07배다. 레일이 단단하면 494.7, 해치 가장자리 고정이면 492.9, 이웃 핀 선 사이 단순 지지만이면 337.6(불합격). 쓰임에서는 패드가 윗판을 밑에서 밀어 킬이 레일을 들어 올린다. 그래서 레일 밑 바닥 EVA는 레일을 돕지 못한다. 킬(z19.3)과 핀 앞끝(y148.6)은 이미 건반 F와의 1.3 한계라 더 키울 수 없다. 첫 모듈 정하중(단계 0 시험 21)은 모듈을 C17a 받침 빗(핀 선과 뒷벽만 받침)에 얹고 위에서 눌러 쓰임과 같은 레일 휨을 잰다(r4.5 고침 3). D-D#-E-F-F#-G 여섯 자리 × 60 N에서 E·F 처짐은 모델 0.121, 레일이 단단하면 0.094, 단순 지지만이면 0.159 mm이고 합격은 ≤ 0.13 mm다. 넘으면 run_all의 화음 자리 강성 `k_ch`를 잰 값(60 N ÷ 처짐)으로 바꿔 화음 자리 동역학(들림 0.20, 키퍼, 유령)을 다시 보고, 불합격이면 리본 차선 위 레일(9 높이)이 원인이므로 회로 세션과 차선 높이를 다시 정한다.
- **스프링 손 들기 토크가 카탈로그 55° 토크를 넘는다(r4.5).** 건반을 뺄 때 레버를 손으로 25°까지 들면 감긴 각 53.4°는 카탈로그 최대 사용각 55° 안이지만, 다리를 짧게 잘라 강성이 커서 토크 7.83 N·mm가 카탈로그 55° 토크 7.52의 104 %(응력 685 MPa, 카탈로그 한계 658 MPa, Su의 32 %)다. 11장 빼기 절차가 드는 각은 15.0°(감긴 각 43.4°, 토크 6.40 N·mm)라 카탈로그 55° 토크 이하이고, 55° 토크가 되는 레버 각은 22.6°다 — 25°는 손으로 더 든 경우다. 영구 변형이 생기면 자유각이 줄어 쉼 토크가 준다. 단계 0 시험 8에서 25°로 1시간 둔 뒤 자유각 변화 ≤ 2°를 본다. 넘으면 들어올림을 22.6° 아래로 지키라고 11장에 적는다.
- **패드 바를 곧게만 당기면** 끝에서 흑 패드 펠트 모서리가 흑건 윗면 턱과 -0.39(PET 심 3장이면 -0.69) — r4.2는 잎 돌기가 립을 떠나면 바가 0.3 내려앉기 때문. 절차(21.5 mm부터 밀어 올림)를 지키면 1.30.
- **패드 바 잎 혀의 크리프(r4.2).** 잎(0.6×1.6×8)이 0.3 눌린 채 8.2 MPa(공차 +0.3이면 16.5)로 늘 굽어 있어 2 MPa 크리프 선을 넘는다. PETG가 풀리면 예하중이 줄어든다: 두 잎의 힘은 처음에 패드 붙은 바 무게의 6.0배라 반으로 풀려도 3.0배, 83 % 넘게 풀려야 바가 0.3까지 처져 딸깍할 수 있다(동역학·틈에는 영향 없음, 소리만). 2 MPa 아래로 낮추면 휨이 0.01 mm대라 FDM 공차를 못 받는다. 단계 0 시험(40 °C 1주)으로 보고, 늘어지면 잎 두께 0.8 또는 손 맞춤.
- **끝 부속 쐐기 얇은 끝(r4.2).** A0 0.29, C8 0.26로 설계 최소 0.3 아래다(한 층 0.2 이상이라 출력은 됨). 출력이 안 되면 끝 부속 패드 바의 그 건반 자리만 바 밑면을 0.1 올려(바 1.4T) 쐐기를 0.1 두껍게 한다 — 패드 면은 그대로.
- **윗판 밑 서포트 88 g/모듈.** 핀 사이 브리지 출력이 되면 없앨 수 있다.
- **강철 블록은 접착으로 잡는다(r4.4 고침 2).** 스냅 립만으로는 옆벽(r4.4 고침 2b부터 0.7)이 버티지 못한다: 매 음 51.9 N에 립 선이 한쪽 1.11~1.70 벌어지고(물림 1.0, 판 모델의 앞·뒷벽 받침 고정 ~ 핀) 옆벽 립 뿌리가 층 안 23.5 MPa(한계 12), 아래 립 뿌리 층간 6.8 MPa(한계 5). 그래서 두 옆면을 MS 폴리머(탄성)로 붙인다(r4.4 고침 2b; 5분 에폭시는 열팽창 차이로 떨어짐): 전단 매 음 하중 0.067 + 열 0.189 MPa(허용 0.38). PETG 부착 강도(설계 1.5 MPa)와 G 약 1 MPa는 가정이다 — 단계 0 시험 20(온도 순환 포함). 접착이 떨어지면 강철이 아래로 빠져 건반 빔 위에 걸린다(날아가지 않음). 강철을 바꾸려면 캐리어를 새로 뽑는다(20분).
- **축 놀음이 줄었다(r4.4 고침 2).** 칼라 한 개 0.76 이상·핀 보스 +0.02로 칸 놀음이 0.46 / 0.46 / 0.43 / 0.30. 가장 좁은 A 칸(0.30)에서 레버가 제 무게로 돌지 않으면 칼라 면을 사포질한다.
- **F·F# 쉼 펠트 착지(r4.4).** F는 여전히 59 %만 앉는다(흰 꼬리 폭 = 빔, 쉼 발은 뽑기 때 E와 부딪혀 기각). F#는 55 %로 늘었지만 쉼 반력이 레버 선에서 +2.80로 멀어져 굴림 되돌림/넘김 비 1.42(r4.3 1.77), 착지 짝힘 상한 2.06 N(r4.3 1.73)이 탭 천으로 간다. ABUSE 복귀 넘침(2.0 m/s 화음, 요청한 화음 자리 2.5 m/s)에서는 F·F# 틈이 1.27(공차 뒤 0.97)까지 줄지만 닿지 않는다. 단계 0 시험 10의 화음 타건을 F~A# 칸에서도 본다.
- **화음 자리 여유 6.4 %(r4.4 단계 0 키트에서 드러남).** 6건반 화음 자리 492 N/mm는 합격선 460의 1.07배다. 출력한 윗판의 실효 E가 1825 MPa(모델 1950의 93.6 %)보다 낮으면 합격선 아래로 간다. 시험 1 다음에 시험 3a(C03a 굽힘 띠)를 한다. 낮으면 윗판 채움 100 %, 그래도 낮으면 윗판을 +0.6 / +1.2 두껍게 한다(FE 화음 자리 534 / 568 N/mm, z_top 73.45 / 74.05). +1.2는 높이 목표 z74를 0.05 넘으므로 +1.15까지만 쓴다. 키트 파일(`stage0_procedure.md`·`stage0_geometry.json`)의 ‘z_top 73.4 / 74.0’은 고침 2 전 z_top 72.80 기준이라 17.1장 표에서 고쳐 적었다.
- **벤치 지그는 프레임 한 대의 자리만 재현한다(r4.4 출력 공구).** 지그와 7개 모듈 프레임을 같은 프린터·같은 층 설정으로 뽑아야 쉼 선반과 봉 높이가 같은 층에서 반올림된다. 공구와 단계 0 키트는 r4.4 고침 2 모델(`MODEL_DIR=final`)로 다시 만들었다(공구의 캡스턴 y와 모델 차이 +0.00 / +0.00).
- **출력 공구와 단계 0 키트는 아직 뽑아 본 적이 없다(r4.4).** 치수는 모델에서 나오지만 층 반올림과 수축은 첫 출력에서 캘리퍼로 본다(10.1장 쓰는 법 5, `stage0/stage0_procedure.md` 출력 설정). 키트 무게 약 430 g과 시간 약 29시간은 채움 계수로 낸 추정이다(속을 꽉 채우면 665 g).

## 19. 파일

- `model_v4.py` — 단일 모델 (r4.0 조각은 `src/`; r4.1 고침은 `model_v4.py`에 바로 넣었고 `src/`는 r4.0 그대로). `run_all.py` — 모든 계산. `export_geo.py` — geometry.json. `make_design_md.py` — 이 문서.
- r4.0 결과 보관: `geometry.r4_0.json`, `work_r4r1/*.r4_0.*`. r4.1 탐색 스크립트: `work_r4r1/`. r4.1 결과 보관: `geometry.r4_1.json`, `work_r4r2/*.r4_1.*`; r4.2 고침 스크립트·검사: `work_r4r2/`. r4.2 결과 보관: `geometry.r4_2.json`, `work_r4r3/*.r4_2.*`; r4.3 고침(회로 인터페이스) 패치: `work_r4r3/patch_*_r43.py`. r4.3 결과 보관: `geometry.r4_3.json`, `work_r4r4/*.r4_3.*`; r4.4 고침(남은 문제 1~3) 패치: `work_r4r4/patch_*_r44*.py`, 탐색 스크립트 `work_r4r4/x*.py`. r4.4 회로 대조 전 보관: `geometry.r4_4_pre_circuit.json`, `work_c44/*.r4_4_pre_circuit.*`; 회로 대조 검사 `model_v4.circuit_c44_checks`, 탐색 `work_c44/c*.py`.
- `results.txt` · `metrics.json` · `geometry.json` · `parts_list.json` — 결과. r3는 `../final_r3/`, 도면 r3는 `../drawings_r3/`.
- r4.4 `tools/` — 출력 공구(10.1장): `make_tools.py` 생성기, `tools.md` 설명, `tools_geometry.json`(치수 T01~T29, 옆모습·평면, 가짜 레버 하중·확대비, 틈 검사), `stl/` 4개, `scad/`, `png/`.
- r4.4 `stage0/` — 단계 0 시험 키트(17.1장): `make_stage0.py`, `stage0_procedure.md` 절차, `stage0_geometry.json`(시편·합격선·결과 대응), `stage0_results_template.csv` 기록표, `stl/` C01a~C17a 34개 파일(C16a는 3개), `png/`, `scad/`.
- r4.4 `../cable/result.json`, `../cable/img/` — USB-C 케이블 조사(1d-3장). `../drawings/` — 도면 1~13(d01~d13 .svg/.png)과 r4.4 새 도면 `d14_printed_tools.svg`, `d15_stage0_coupons.svg`(도면 세션).
- r4.4 문서 작업: `work_doc44/` — 반올림 도우미로 서식을 바꾼 스크립트 `pf_transform.py`, 패치 `patch_doc44_*.py`, 바꾸기 전 보관 `*.pre_doc44.*`, 반올림으로 바뀐 칸 기록 `round_cells.json`(고침 2 전 모델), 새 서식 geometry.json을 만든 모델 사본 실행 `sb2/`와 비교 `cmp_sandbox2.json`(모델 수치 같음 확인). 고침 2 뒤 다시 맞춤: `work_doc44/r3/` — `patch_doc44_r3.py`·`patch_doc44_r3b.py`(이 판의 글 고침), `patch_export_r3.py`(`pf`가 `%s` 실수도 줄임), `dims_cmp.py`·`run_md_old.py`·`build_round_cells.py` → `round_cells.json`(5장 머리, 지금 모델), 고치기 전 보관 `make_design_md.start.py`·`DESIGN.start.md`.
- r4.4 고침 2: 고치기 전 보관 `geometry.r4_4a.json`, `work_f2/*.pre_f2`; 패치 `work_f2/patch_*_f2.py`, 탐색 `work_f2/t*.py`, 옆벽 판 모델 `model_v4.carrier_wall_plate`; 첫 전체 실행 기록 `work_f2/*.run1.*`(끝 부속 A#0 블록 ↔ 레일 1.20이 남아 포켓 x 구간을 블록 ± 받침 틈으로 넓히고 다시 돌림).
- r4.5 회로 2차 대조: 고치기 전 보관 `geometry.r4_5c.json`, `work_r45d/*.pre.py`; 패치 `work_r45d/patch_*.py`, 긴 유령 시험 `work_r45d/t_ghost.py`, 고침 확인 `work_r45d/t_fix.py`; 결과 `metrics.json`의 `c45`·`ghost_summary`, geometry.json의 `circuit_r45`.
- geometry.json에 합친 도면 쪽 고침: end_parts fin bosses one-sided on the seam fins (left 43.85-46.8, right 0.2-3.15); plan lever rod x = rod_L_x 1.5-162.9; black-key magnet bosses merged into the walls (+-4.0); r3 compression assist spring / P18 / D05 replaced by the torsion spring (audit A2).

