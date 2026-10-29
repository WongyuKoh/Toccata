# 한 옥타브 조립 가이드 — 그림 다시 만들기

- `index.html` = 아티팩트 https://claude.ai/artifact/U6CnesuxwRDptj9u7QfwCY (img/ photo/ dwg/ 를 files로 함께 게시; dwg는 용량 때문에 두 번째 게시로).
- 단계 그림(img/*.webp)은 CAD GLB의 O4 부품을 OpenSCAD로 그린 것:
  1. `hardware/mechanical/cad/Toccata_전체조립.glb`에서 노드 이름이 `O4-`인 부품을 STL로 꺼내 `<작업폴더>/parts/`, 색·이름은 `manifest.json`에서 `<작업폴더>/parts.json`으로.
  2. `render_steps.py`를 그 작업폴더에 두고 실행(OpenSCAD는 샌드박스 밖에서만 뜸: Qt CPU 검사).
  3. PNG를 테두리 잘라 webp로 → `img/`.
- 사진은 `docs/report/toccata-v4/img/bom/<id>.jpg`를 360 px webp로, 도면은 `docs/report/toccata-v4/dwg/`와 `hardware/pcb/board/` 복사본.

## 3D 그림 (2026-10-27)

- 단계 그림은 이제 돌려 볼 수 있는 3D입니다. `python3 make_models.py` → `../model/octave.json`(O4 부품 169개 + 그림 13개 정의), `../viewer3d.js`가 그립니다. webp 그림은 불러오기 전·WebGL이 없을 때 보이는 대체 그림으로 남습니다.
- 게시: index.html + viewer3d.js + model/octave.json. 본 페이지 11번 탭은 `docs/report/toccata-v4/src/tabs/asm/build_section.py` → `merge.py --check` → index.html + fin/asm/octave.json.
