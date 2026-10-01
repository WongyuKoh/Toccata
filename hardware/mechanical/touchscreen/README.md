# R31 터치스크린

| 폴더 | 내용 |
|---|---|
| [`rev3/`](rev3/) | **지금 판 (2026-10-01 사용자 승인).** Waveshare 7-DSI-TOUCH-C(7인치 가로 DSI)를 L2 가운데 화면 뚜껑에 25° 기울여 세우고, 접으면 뚜껑 위 z78~95에 눕힙니다. CAD 넘김 사양 `design/CAD_SPEC_rev3.md`, 수치 `design/numbers.json`(3a), 치수 도면 t01~t06, 3D 미리보기, 검수 페이지가 있습니다. CAD는 통합본 v15 탭 09의 `src/touchscreen_rev3.py`입니다 |
| [`compare/`](compare/) | 화면 13가지 조합 비교(2026-10-01). 사용자가 B1을 골랐습니다 |
| [`screen_dims/`](screen_dims/) | 제조사 치수도. B1은 `ws_7-DSI-TOUCH-C-details-size.jpg`입니다 |
| [`rev2_td2/`](rev2_td2/) | 2판 기록(2026-09-30: 공식 Touch Display 2 7인치, L1 CU 뚜껑). CAD L1 보관본(`cad/src/touchscreen.py`)이 여기 numbers.json을 읽습니다 |

설계 기준은 `../sound-requirements.md`의 R31과 D14·D16·D19·D20~D24이고, 회로는 `hardware/pcb` 개정 C(△16)입니다.
