# Toccata

portable Piano + Rhythm Game

88키 풀사이즈 분할식 피아노와, 그 피아노를 컨트롤러로 쓰는 리듬 게임을 만드는 프로젝트.

건반은 **3D 프린터로 뽑는 짧은 시소 건반 + 강철 추 레버(v4, W1+)** 구조다 — 건반과 레버가 금속 봉 위에서 돌고, 레버 무게와 작은 토션 스프링으로 복귀한다. 늘 휘어 있는 플라스틱이 없다.

## 진행 순서

1. **하드웨어 설계 및 제작** ← 현재 단계
2. 피아노 소리 테스트 (MIDI 프로그램 연결 + 온디바이스 구동)
3. 리듬게임 연동
4. 리듬게임 제작

## 문서

- **[하드웨어 설계서 v4 (확정본, 2026-10-02)](docs/01-hardware-design.md)** — 지금 설계를 한곳에 모은 문서. 요구사항·건반 액션·회로·뒷바 L2·터치스크린·비용·출력·제작 순서·확인할 것·파일 지도
- [하드웨어 폴더 안내 (v4)](hardware/README.md) — 건반 액션 v4 · 회로 · CAD · 재료 목록. 통합 보고서: https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df
- [요구사항 R1~R32 · D1~D24](hardware/mechanical/sound-requirements.md) — 모든 설계의 기준
- [CAD 출력·조립 안내](hardware/mechanical/cad/README.md) — 출력 STL, 도면 D01~D06, 렌더, 조립 순서
- [리듬게임 기획서](docs/02-rhythm-game-design.md) — 2단계
- [보관: 1단계 하드웨어 설계 v2.0 (모노리식)](docs/archive/v2.0-monolithic.md) — v4로 대체됨
- [보관: 설계 검토서 (v2.0 시각화 보고서)](docs/report/toccata-design-review.html)
- [보관: v2.0·v3 CAD·STL·렌더](hardware/mechanical/before/cad/) · [도해 SVG](docs/figures/)
- [보관: v1.5 다부품·금속 스프링 설계](docs/archive/v1.5-multipart.md)
- [보관: v0.3 상용급 설계](docs/archive/v0.3-overengineered.md) — 참고용

## 디렉토리

```
docs/         설계 문서 (01 하드웨어 설계서 v4, 02 리듬게임 기획), archive/ (이전 설계서), report/ (보고서)
hardware/     기구·PCB·BOM
  mechanical/   sound-requirements.md (요구사항), key-action-v4/ (건반 액션), touchscreen/ (터치스크린 3판), before/ (이전 설계)
    cad/          출력 STL (stl/print/), 도면 (drawings/ D01~D06), 렌더 (renders/), 전체 조립 3MF·GLB, 생성기 (src/build_all.py)
  pcb/          회로도, 기판 배치, 넷리스트
  bom/          구매 목록 엑셀 v4, 최종 재료 페이지 생성기, 판매처 조사, 절감 선택기
firmware/     RP2040-Zero 펌웨어 (키 스캔, 벨로시티, USB-MIDI) — 아직 비어 있음
sw/           라즈베리파이 소프트웨어 (FluidSynth, 터치 메뉴) 및 이후 리듬게임 — 아직 비어 있음
```

## 핵심 사양 (v4 확정본 · 2026-10-02)

| | |
|---|---|
| 건반 | 88키 (A0–C8), 흰건반 피치 23.5 mm, **3D 프린팅** (PETG) |
| 구조 | 옥타브(도~시) 모듈 7개 + 왼쪽 끝 부속(A0·A#0·B0) + 오른쪽 끝 부속(C8). 모듈 164.5 × 212 mm, 1.37 kg |
| 건반 기구 | Ø4 봉 위의 짧은 시소 건반 + 강철 블록 무게 레버 + 미스미 비틀림 스프링(C-UA90R5-3-0.5). 누르는 힘 51.9 / 51.0 g, 연타 16.3 / 18.8 Hz |
| 센싱 | 선형 홀센서 **DRV5055A2** + 자석 Ø5×2, 위치를 연속으로 재서 벨로시티 계산 |
| 모듈 MCU | **RP2040-Zero** ×8 (모듈 7 + 페달), 모듈마다 16채널 먹스(CD74HC4067 ×7), 각각 USB-MIDI 장치 → 10포트 유전원 허브 |
| 메인 CPU · 소리 | **Raspberry Pi 5 2GB** + FluidSynth, USB 오디오 동글 → TPA3110 앰프 → 4인치 스피커 2개 (헤드폰을 꽂으면 꺼짐) |
| 본체 | 건반 바로 뒤에 붙는 한 몸 뒷바 L2. 전체 **1254 × 342.5 mm**, 가운데 윗면 z72.85(건반 틀과 같은 높이), 스피커 앞판 40°, 스피커 윗면 z144.65 |
| 화면 | 7인치 가로 터치스크린 Waveshare 7-DSI-TOUCH-C, 25°로 세우고 운반할 때 접음 |
| 전원 | USB-C PD 20 V (65 W 충전기 또는 보조배터리, 약 3.2~4.0시간) |
| 비용 | 실제 구매 **731,485원**(가진 부품·예비 제외, 배송비 포함). 전체 구매 목록(가진 부품·공구·예비 포함) 1,134,177원, 그중 기본 구성 754,492원 (한도 100만 원) |
| 출력량 | 악기 출력 289개(파일 73종, `hardware/mechanical/cad/stl/print` 전부 + 공구 4). 건반 액션 필라멘트 약 6.55 kg · 436시간 + 뒷바 약 1.1 kg |

> 옥타브 모듈 1개가 곧 완결된 12키 USB-MIDI 키보드입니다. 첫 모듈에서 2단계(음원 테스트)를 시작합니다.
> 이전 상용급 설계(v0.3, 600~1,100만원)는 [docs/archive](docs/archive/)에 보관.

## 라이선스

MIT
