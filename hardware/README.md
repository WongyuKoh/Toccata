# hardware

Toccata 하드웨어 설계 자료입니다. 현재 기준은 **v4**(2026-09-29)입니다.
- 건반 액션: W1+ r4.5(미스미 기성품 스프링, 남은 문제 해결)
- 전자부: 회로도 개정 C(W1 r4.5 기준, 10/1 △16 터치스크린 전원)

확정 설계를 한곳에 모은 문서는 [하드웨어 설계서 v4](../docs/01-hardware-design.md)입니다.

통합 아티팩트는 건반 액션 보고서, 도면, 재료 선택, 회로도를 한 페이지에 모은 것입니다: https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df (발행 원본: [`docs/report/toccata-v4/`](../docs/report/toccata-v4/))

| 폴더 | 내용 |
|---|---|
| [`mechanical/sound-requirements.md`](mechanical/sound-requirements.md) | 요구사항 R1~R32, D1~D24. 모든 설계의 기준 (R31 터치스크린, R32 L2 한 몸 뒷바 · 스피커 앞판 40°) |
| [`mechanical/key-action-v4/`](mechanical/key-action-v4/) | **건반 액션 v4 (W1+).** 설계 문서, 좌표·물리 모델, 도면 15장, 출력 공구와 단계 0 시편 STL(`printables/`), 구조안 5개 비교, 검증 기록, 보고서 |
| [`mechanical/touchscreen/`](mechanical/touchscreen/) | **R31 터치스크린 수정 3판 (10/1 사용자 승인).** Waveshare 7-DSI-TOUCH-C(7인치 가로 DSI)를 L2 가운데 화면 뚜껑에 25° 기울여 세우고, 접으면 z78~95로 화면 뚜껑 위(뚜껑 윗면 z72.85, 뚜껑 평면 안)에 눕힘. `rev3/`에 CAD 넘김 사양(CAD_SPEC_rev3.md), 치수 도면 t01~t06, 3D 미리보기, 검수 페이지. 조합 비교 13가지는 `compare/`. 2판(공식 TD2, L1) 기록은 `rev2_td2/`. CAD는 통합본 v15 |
| [`mechanical/cad/`](mechanical/cad/) | **CAD (L2 한 몸 뒷바 + 건반 액션 r4.5 + 터치스크린 3판).** 출력 STL — `stl/print/`는 전부 뽑으면 되는 101파일(악기 73파일·289개 + 출력 공구 4파일 + 합판 지그 24파일 `08_합판지그`, 패드 바는 구매한 PORON 5T용; 묶음 `Toccata_출력STL_전체.zip`), `stl/print_extra/`는 선택·대안·예비(화면 덮개, 합판 지그 J-f 사포 막대, PORON 6T용 패드 바, 예비 건반), 합판 지그 사용법 [`jigs/README.md`](mechanical/cad/jigs/README.md)(공구 새로 안 삼, J-b 새들 4개는 모두 뽑아 판 두께에 맞는 것을 씀), 도면 D01~D06(`drawings/`), 렌더(`renders/`), 전체 조립 3MF·GLB, 사양(`spec/body_L2.json`), 생성기 `src/build_all.py`. 출력·조립 안내는 `README.md` |
| [`mechanical/before/`](mechanical/before/) | 이전 설계 보관: v2.0 일체형, v3 CAD·STL·렌더, 88건반 STEP |
| [`pcb/`](pcb/) | 전자부 회로도 9장, 기판 배치, 넷리스트, 부품표. 회로 세션이 관리합니다 |
| [`bom/`](bom/) | 구매 목록 엑셀(v4), 핵심 부품 목록 생성기, 판매처 조사(USB-C 케이블 포함), 절감 선택기 |

## 한눈에 보기 (v4)

- **건반:** 강철 봉 위의 짧은 시소 건반과, 꼬리가 들어 올리는 강철 추 레버가 있습니다. 무게와 작은 비틀림 스프링(미스미 C-UA90R5-3-0.5)으로 돌아오고, 늘 휘어 있는 플라스틱이 없습니다. 강철 블록은 캐리어에 MS 폴리머로 붙입니다.
- **힘:** 누르는 힘 약 51~52 g, 올라오는 힘 약 41~43 g, 연타 16~19 Hz입니다.
- **크기:** 옥타브 모듈은 164.5 × 212 mm, 1.37 kg이고 7개입니다. 끝 부속 2개를 더해 건반부는 1254 × 212 mm(깊이)이고, 바로 뒤에 붙는 한 몸 뒷바(L2: 스피커 2개 · 가운데 유닛 · 터치스크린, R32)까지 1254 × 342.5 mm입니다. 가운데 윗면은 건반과 같은 z72.85, 스피커 윗면은 z144.65(앞판 40°)입니다.
- **센싱:** 건반마다 선형 홀센서(DRV5055A2)와 자석(Ø5×2)이 있습니다. 모듈마다 RP2040-Zero와 16채널 먹스가 있고, USB-MIDI로 Raspberry Pi 5(FluidSynth)에 연결됩니다.
- **화면:** 7인치 가로 터치스크린(Waveshare 7-DSI-TOUCH-C, DSI)에서 메뉴와 리듬게임을 합니다. 외부 TV는 HDMI로 선택 연결합니다.
- **비용:** 실제로 살 금액은 **731,485원**입니다(부품 683,385원 + 배송비 48,100원, 가진 부품과 예비 제외; 최종 재료 페이지 https://claude.ai/artifact/9CJ3HwhbhoodCAui94g28n 10/2 기준). 구매 목록 엑셀 `bom/toccata-purchase-list-v4.xlsx`는 가진 부품·공구·소모품·예비까지 모두 넣은 **전체 목록**이고 1,134,177원입니다(추천 절감 1,091,558원). 그중 기본 구성은 754,492원으로 한도 100만 원 안입니다(터치스크린·L2 뒷바 포함).

다음 단계는 단계 0 시험입니다. 시편 34개와 절차서가 `mechanical/key-action-v4/printables/stage0/`에 있습니다(DESIGN.md 17장).
- **먼저 시험 1 (패드 반발).** 패드 재료값이 가장 큰 위험입니다(DESIGN.md 18장).
- 그다음 시험 3a (윗판 굽힘 띠, 6건반 화음 자리 여유 6.4 %).
- 그리고 r4.4~r4.5에서 바뀐 곳: 접착 강도(시험 20), 첫 모듈 정하중(시험 21), 스프링 토크(시험 8).
