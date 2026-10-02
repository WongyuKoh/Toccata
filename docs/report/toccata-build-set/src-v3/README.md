# v3 도면 생성기 (치수 위치 수정본, 2026-09-25)

`docs/report/toccata-build-v3.html`의 도면 14장을 만드는 스크립트다. 치수선·치수 글자가 형상과 어긋나던 곳을 고친 판이다.

- `render_drawings.py`, `r26_draw.py`, `draw.py`: 도면 생성. 리프 상세(백건 t 2.6)의 11.0 치수는 리프 끝 모서리에, 15.0·18.0 뿌리 폭은 필렛 전 가상 교점(점선)에 맞췄다.
- `build_v3.py`, `patch_*.py`, `apply_*.py`, `assemble_bom.py`: 설계서 HTML 조립.
- `merge.py`, `merge_v32.py`: 설계서를 A–D 도면집과 합쳐 한 페이지로 만든다. `merge_v32.py`는 v3.2 이후 설계서 머리의 합계를 쓴다.

다시 빌드하려면 v3 작업 폴더의 데이터(`drawings.json`, `bom_all.json`, `cost/`, `img/` 등)가 필요하다. 이 데이터는 저장소에 없다.

v3.2(ME6·ME10, 체결부 변경)의 수정은 생성기가 아니라 HTML 문자열 치환으로 들어갔다. 그래서 이 생성기로 다시 빌드하면 v3.2 문구가 빠진다. 현재 `toccata-build-v3.html`은 수정한 도면과 v3.2 문구를 3-way 병합한 결과다.
