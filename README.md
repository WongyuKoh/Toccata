# Toccata

portable Piano + Rhythm Game

88키 풀사이즈 접이식 휴대용 피아노와, 그 피아노를 컨트롤러로 쓰는 리듬 게임을 만드는 프로젝트.

## 진행 순서

1. **하드웨어 설계 및 제작** ← 현재 단계
2. 피아노 소리 테스트 (MIDI 프로그램 연결 + 온디바이스 구동)
3. 리듬게임 연동
4. 리듬게임 제작

## 문서

- [1단계 하드웨어 설계 v1.5](docs/01-hardware-design.md)
- [설계 검토서 (시각화 보고서)](docs/report/toccata-design-review.html) — 렌더·도해·수치표
- [CAD: toccata.scad](hardware/mechanical/toccata.scad) · [STL 13종](hardware/mechanical/stl/) · [렌더](hardware/mechanical/renders/) · [도해 SVG](docs/figures/)
- [폐기된 v0.3 상용급 설계](docs/archive/v0.3-overengineered.md) — 참고용

## 디렉토리

```
docs/         설계 문서
hardware/     기구·PCB·BOM
  mechanical/   toccata.scad (파라메트릭 OpenSCAD), stl/, renders/
  pcb/          회로도, 아트워크
  bom/          부품표
firmware/     RP2350 펌웨어 (키 스캔, 벨로시티, USB-MIDI, 신스)
sw/           라즈베리파이 소프트웨어 (FluidSynth, 설정 UI) 및 이후 리듬게임
```

## 핵심 사양 (v1.0 · 메이커 버전)

| | |
|---|---|
| 건반 | 88키 (A0–C8), 풀사이즈 피치 23.5mm, **3D 프린팅** (PLA) |
| 구조 | 옥타브(도~시) 모듈 반복 · 시작 3키 + 옥타브 12키 ×6 + 상단 13키 |
| 건반 기구 | Ø6 일체 피벗 핀 + 30° 열린 요람 + 인장 스프링 (joewing/organ 방식), 1키씩 탈착 |
| 센싱 | **홀 센서 SS49E(눕힘) + 자석**, 접근 모델 두 임계값 dt 벨로시티 |
| 모듈 MCU | **Raspberry Pi Pico** ×8, 각각 USB-MIDI 장치 (버스 없음) |
| 메인 CPU | **Raspberry Pi 5** + I2S DAC HAT — FluidSynth(4~6ms), Pianoteq 선택 |
| 정렬 | 합판 베이스 보드 + 알루미늄 평철(피치 기준) + 강철자 마킹 + 잠금 핀 |
| 예산 | **약 45~48만원** (Pi 5·PSU·프린터·Pianoteq 제외) |
| 출력량 | 필라멘트 약 6kg, 22~29판 · 2~3주 |

> 옥타브 모듈 1개가 곧 완결된 12키 USB-MIDI 키보드입니다. 첫 모듈에서 2단계(음원 테스트)를 시작합니다.
> 이전 상용급 설계(v0.3, 600~1,100만원)는 [docs/archive](docs/archive/)에 보관.

## 라이선스

MIT
