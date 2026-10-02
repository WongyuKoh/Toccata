# Toccata v4 통합 아티팩트 — 고치는 법

> **2026-10-02부터 최종본만 보여 줍니다**(사용자: "예전 구조 다 빼고 최종적으로 다루는 내용만"). `merge.py`의 `FINAL_ONLY = True`가 탭을 요약 · 01 건반 액션 구조 · 02 건반 도면(도면 11 뺌) · 03 검증·남은 위험(남은 문제·단계 0·남은 위험만) · 04 출력·조립(보관함 뺌) · 05 구매 목록(`src/build_buylist.py`) · 06 회로도 · 07 CAD · 08 뒷부분 도면으로 짭니다. 진행 기록(00), 부품·비용(04 옛), 5안 비교, 재료·절감 선택, S1·H1·K1·F1 대안 탭은 빠집니다(원본 `src/`는 그대로라 `FINAL_ONLY = False`로 되돌릴 수 있음).

두 아티팩트와 회로도를 **하나의 아티팩트**로 합쳤습니다.
- 건반 액션 진행 현황: https://claude.ai/artifact/1fA3D1HQRvNEanGCjDPhTZ
- 재료 절감 선택: https://claude.ai/artifact/Vv8pahUbEkKhwsZwGnmsGG
- 회로도: 새로 만든 탭

2026-09-28부터 Toccata v4에서 바뀌는 내용은 **모두 이 통합 아티팩트에 다시 발행**합니다. 원본 두 개는 더 고치지 않습니다.

- 통합 아티팩트 URL: **https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df** (2026-09-28 v1 발행)
- 이 폴더가 발행 원본입니다: `index.html`과 옆의 `dwg/ alt/ img/ sch/`.

## 탭과 원본

| 탭 | page id | 원본 | 누가 고치나 |
|---|---|---|---|
| 요약 한눈에 보기 (맨 앞, 첫 화면) | `p-summary` | `src/summary.html` ← `python3 src/build_summary.py <최종 재료 db state/main JSON>` (최종 재료 페이지 데이터 hardware/bom/final-bom/site/index.html + 사용자 선택으로 실제 구매 금액 계산, 설계 숫자는 스크립트 안) | W1 세션 |
| 00~06 진행 현황 · W1+ 구조 · 도면 12 · 검증 · 부품·비용 · 출력·조립 · 5안 비교, S1·H1·K1·F1 | `p-overview` … `p-f1` | `src/progress.html` + `dwg/` `alt/` `img/` | v4 건반 액션 세션 (report 빌더) |
| 07 재료·절감 선택 | `p-cost` | `src/costsel.html` | 재료·절감 세션 (`gen_sel.py`) |
| 08 회로도 | `p-circuit` | `hardware/pcb/page/circuit.{html,css,js}` + `sch/` | 회로 세션 (`hardware/pcb/src/build.py` → `page.py`) |
| 10 뒷부분 도면 | `p-rear` | `hardware/mechanical/cad/drawings/D01~D06` (SVG·PNG) + `renders/R01~R03` → `merge.py`가 `rear/`로 복사. 도면마다 확대 단추(맞춤·2배 = PNG, 3배 = SVG; 회로도 탭의 `.zbar`) | CAD 세션 (`hardware/mechanical/cad/src/drawings.py`, `build_all.py`가 끝에 실행) |

## 고치고 발행하는 순서

1. **자기 탭의 원본만 바꿉니다.**
   - **진행 현황.** 빌더가 만든 **전체 페이지**(`<title>…</title>`로 시작하는 `index.html`)를 `src/progress.html`로 덮어씁니다. 그 페이지가 쓰는 도면과 사진은 같은 경로로 `dwg/`, `alt/`, `img/`에 복사합니다.
     - `merge.py`는 `<nav class="tabs" aria-label="페이지">`, `<main class="wrap">`, `<footer><div class="wrap">`, 첫 `<script>`를 찾아 씁니다.
     - 탭 순서는 원본의 nav를 따릅니다. `<span class="sep"></span>` 뒤는 대안 탭입니다.
   - **재료·절감.** `gen_sel.py`가 만든 전체 페이지를 `src/costsel.html`로 덮어씁니다.
     - 합계 막대(`.sumbar`), `<main>` 안의 내용, 스크립트를 그대로 가져옵니다.
     - 공통 CSS를 뺀 나머지 CSS에는 자동으로 `#p-cost` 범위를 붙입니다.
   - **회로도.** `python3 hardware/pcb/src/build.py` 다음 `python3 hardware/pcb/src/page.py`를 실행합니다. SVG는 `merge.py`가 `sch/`로 복사합니다.
2. `python3 docs/report/toccata-v4/merge.py --check`를 실행합니다. 섹션 15개(`p-overview`…`p-f1`, `p-cost`, `p-circuit`, `p-cad`, `p-rear`)가 나와야 합니다.
3. **발행합니다.** 다른 세션은 먼저 Artifact `action: "read"`, `url: https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df`로 읽어야 발행할 수 있습니다. 읽은 뒤 이렇게 호출합니다:
   ```
   Artifact publish
     url:       https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df
     file_path: docs/report/toccata-v4/index.html
     root:      docs/report/toccata-v4
     files:     [바뀐 파일만, 예: "dwg/d01_white_D_side.svg", "sch/SCH-03_control_board.svg"]
   ```
   - `files`에 없는 파일은 그대로 남습니다. 지운 파일은 `{"경로": null}`로 뺍니다.
   - 새 아티팩트를 만들지 않습니다(`url` 없이 발행하면 새 URL이 생깁니다).
   - `icon`은 넘기지 않습니다(처음 발행 때 정했음).
4. 발행 결과에 "newer version"(충돌)이 나오면, 그 버전을 `read`로 받아 `src/`에 반영하고 `merge.py`를 다시 돌린 뒤 발행합니다.

## 주의

- 페이지 머리말(`header.tb`)과 합친 원본 안내는 `merge.py`의 `header`에 있습니다. 날짜와 상태 칸을 바꾸려면 거기를 고칩니다.
- 새 탭이 필요하면 `merge.py`의 `nav`와 `main` 조립부에 `<a href="#id" data-to="id">`와 `<section class="page" id="p-id" hidden>`를 추가합니다. 라우터는 `.page` 섹션과 `nav.tabs a`만 봅니다.
- 이 폴더의 `dwg/ alt/ img/`는 2026-09-28에 발행본과 크기를 대조해 옮겼습니다(29개 모두 같음).
