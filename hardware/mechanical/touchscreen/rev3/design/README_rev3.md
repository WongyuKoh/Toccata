# R31 터치스크린 수정 3판 3a (B1 · L2) — 파일 안내

- 화면: Waveshare 7-DSI-TOUCH-C (사용자 선택 B1), 자리: L2 뒷바 가운데 뚜껑. L2 값: 확정본 L2_cu.json
- 순서: `python3 work/measure_bottom_feature.py` (도면에서 아래 끝 돌기 재기, 한 번) → `python3 geom3.py` (자리 블록 → numbers.json) → `python3 build3.py` (design.json, texts.json, CAD_SPEC_rev3.md, 이 파일) → `python3 draw3.py` (touch_concept_rev3.svg/png, 크롬으로 PNG) → `python3 build3d.py` (확인용 상자 3D: preview3d_rev3.png/.glb, CAD 아님, 출력용 STL 아님)
- 자리 블록은 numbers.json `placement` 하나입니다. L2 확정 파일(`../L2_cu.json`)이 있으면 자동으로 그것을 읽습니다. 스피커 유닛 자리는 work/body_L2_copy.json(저장소 body_L2.json 사본, 돌릴 때마다 md5 비교).
- 부품 모양은 받침 좌표(xr, u, w)로 정의하고, 세운·뒤꿈치·접은 자세는 `poses`의 4×4 행렬로 world로 옮깁니다.
- 3a(검수 반영)에서 바뀐 것은 CAD_SPEC_rev3.md의 "3a에서 고친 것" 표에 있습니다. 고치기 전 결과는 rev3a_before/에 있습니다.

핵심 값: 경첩 축 y226.55 z81.35 · 가장 앞 y216.0 · 받침 170.7×106.0×17.0 (출력 높이 119.76) · 접음 z95.35, 뒤끝 y339.05 · 다리 67 mm 39.78° (22°에서 넣음) · 가로 리브 u24·80 · 리본 약 256/300 mm B형 · 전원선 약 345 mm · 10 N에 다리 27.22 N

파일: geom3.py, build3.py, draw3.py, build3d.py, numbers.json, design.json, texts.json, CAD_SPEC_rev3.md, touch_concept_rev3.svg/png, preview3d_rev3.png/.glb(확인용 상자 모형), rev2_src/(2판 원본 복사), rev3a_before/(3판 처음 결과), work/(사진·잘라낸 그림·key_numbers·body_L2 사본, measure_bottom_feature.py)
