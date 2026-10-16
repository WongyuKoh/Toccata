# Toccata 최종 도안 아티팩트 — 다시 만들고 발행하는 법

재료 구매를 마친 뒤(2026-10-08) 이 폴더는 **최종 설계만** 보여 주는 한 페이지를 만듭니다. 예전 탭(진행 기록, 5안 비교, 재료·절감 선택, 대안 S1·H1·K1·F1, 구매 목록 05, 건반 도면 02, 뒷부분 도면 08)은 없습니다.

- 아티팩트 URL: **https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df** (이름 `Toccata v4 통합`은 바꾸지 않습니다)
- 발행 원본: 이 폴더의 `index.html`과 `publish_files.json`의 `files`에 적힌 파일들

## 탭과 원본

| 순서 | 탭 (page id) | 원본 | 다시 만드는 명령 (저장소 루트에서) |
|---|---|---|---|
| 요약 | 한눈에 보기 (`p-summary`, 첫 화면) | `src/summary.html` | `python3 docs/report/toccata-v4/src/build_summary.py` |
| 01 | 회로도 (`p-circuit`) | `hardware/pcb/page/circuit.{html,css,js}` + `assets.txt` | `python3 hardware/pcb/src/build.py` → `python3 hardware/pcb/src/page.py` (SVG는 merge.py가 `sch/`로 복사) |
| 02 | 설계도 (`p-dwg`) | `src/tabs/dwg/` | `python3 hardware/mechanical/cad/src/drawings_final.py` → `python3 docs/report/toccata-v4/src/tabs/dwg/build_section.py` |
| 03 | 부품 도면·출력 파일 (`p-partdwg`) | `src/tabs/partdwg/` | `python3 hardware/mechanical/cad/src/part_sheets.py` (약 3분) |
| 04 | 3D 모델 (`p-cad`) | `hardware/mechanical/cad/viewer/cad.{html,css,js}` | `python3 hardware/mechanical/cad/viewer/gen_viewer.py` (GLB는 merge.py가 base64로 `cad/`에) |
| 05 | 동작 시뮬레이션 (`p-sim`) | `src/tabs/sim/` | `python3 hardware/mechanical/key-action-v4/model/export_sim.py --cad-check` |
| 06 | 부품·사용처 (`p-parts`) | `src/tabs/parts/` | `python3 hardware/mechanical/cad/src/locate.py` → `python3 docs/report/toccata-v4/src/tabs/parts/build_section.py` |
| 07 | 준비 체크 (`p-prep`) | `src/tabs/prep/` | `python3 docs/report/toccata-v4/src/build_prep.py` |
| 08 | 건반 액션 원리 (`p-design`) | `src/progress.html`의 p-design | merge.py가 잘라 쓰고 합니다체로 바꾸며 개정 기록(r4.x 고침 등)을 뺌 |
| 09 | 출력·조립 (`p-build`) | **merge.py가 만듦**: 출력 계획은 `hardware/mechanical/cad/manifest.json`에서 계산, 합판·기판·뒷부분·책상에서 합치기·터치스크린·뚜껑·분해 순서는 `hardware/mechanical/cad/README.md`의 조립 순서를 옮긴 글, 모듈 조립·출력 공구·건반 빼기·조정은 `src/progress.html` p-build에서. 퓨즈 홀더 단계의 12 AWG 꼬리·W601 리드·W602a 길이는 `hardware/pcb/netlist/cables.csv`에서 읽어 넣음(`fill_cables`) | `python3 docs/report/toccata-v4/merge.py` |
| 10 | 검증·남은 위험 (`p-check`) | `src/progress.html`의 p-check (남은 문제·단계 0 시험·남은 위험만) | merge.py (08과 같은 정리) |

공통 재료 목록은 `data/final_items.json`(`src/build_items.py`)입니다. 요약·부품·준비 체크와 머리말 금액이 이것을 읽습니다. 사진은 `img/bom/<id>.jpg`입니다.

### 다시 만드는 순서 (데이터가 앞 단계를 읽음)

선 길이의 원본은 회로의 `hardware/pcb/netlist/cables.csv`이고, 물건 글의 원본은 `data/final_items.json`입니다. 앞 단계를 고치면 뒤 단계를 모두 다시 돌립니다.

1. 회로: `python3 hardware/pcb/src/build.py` → `python3 hardware/pcb/src/page.py` (cables.csv · harness.csv · bom.csv · wiring_*.csv)
2. 재료 목록: `python3 docs/report/toccata-v4/src/build_items.py` (cables.csv를 읽음 → final_items.json)
3. 06 부품·사용처: `python3 hardware/mechanical/cad/src/locate.py` → `python3 docs/report/toccata-v4/src/tabs/parts/build_section.py` (final_items.json → fin/loc/cards.json)
4. 07 준비 체크: `python3 docs/report/toccata-v4/src/build_prep.py` (final_items.json + cables/harness/bom.csv → fin/prep/lines.json)
5. 05 동작 시뮬레이션: `python3 hardware/mechanical/key-action-v4/model/export_sim.py --cad-check` (cables.csv · wiring_MB.csv → fin/sim/system.json)
6. 요약: `python3 docs/report/toccata-v4/src/build_summary.py` (final_items.json · prep 줄 수 · 회로 도면 수)
7. `python3 docs/report/toccata-v4/merge.py --check` — 결과의 `data_freshness.ok`가 `false`이면 거기 적힌 주인(owner) 단계부터 다시 돌립니다.

02 설계도와 03 부품 도면은 CAD 입체만 읽으므로 CAD를 바꿨을 때만 다시 만듭니다.

**CAD 주의:** `hardware/mechanical/cad/src/build_all.py`를 그대로 실행하지 않습니다(main()이 `stl/print`를 지웁니다). 위 생성기들은 `build_all.collect()`만 부릅니다.

### 탭 조각 규칙 (`src/tabs/<id>/`)
- `section.html`: `<section class="page" id="p-<id>" hidden>` 하나. 맨 앞은 h2와 `p.lede`. h2 앞의 탭 번호("02 ")는 merge.py가 뗍니다(번호는 탭 줄에 있음).
- `style.css`: 모든 선택자가 `#p-<id>`로 시작. 색은 `:root` 토큰만(도면 종이 안은 예외).
- `script.js`: IIFE 하나. 다른 탭과는 `window.toccata.<id>`로만 이야기합니다.
- `assets.txt`: 실행 중에 쓰는 파일(이 폴더 기준 경로). 탭이 처음 열릴 때 불러옵니다.
- 요소 id는 페이지 전체에서 하나뿐이어야 하고 탭 id를 앞에 붙입니다(`dwg-e01`, `parts-i014`, `prep-r-…`, `build-ply`).

## merge.py가 하는 일

`python3 docs/report/toccata-v4/merge.py --check` (1초 안쪽)

1. 복사: 회로 SVG → `sch/`, CAD D01~D06·R01~R03 → `rear/`, 3D 모델 → `cad/parts.json` + `cad/toccata.glb.b64.txt`(GLB = `viewer/assets.json`의 `"glb"`, 없으면 `Toccata_전체조립.glb`).
2. **묶음 파일(`fin/bundle/*.json`)**: 한 아티팩트 버전에는 파일이 511개까지만 들어갑니다. 그래서 부품별 zip 122개(`fin/parts/P-*.zip.b64.txt`)는 출력 폴더별로, 위치 확대 그림 183개(`fin/loc/detail/*.svg`)는 종류별로 JSON 묶음 19개(묶음 하나 약 1.4 MB 이하, `{경로: 내용}`)에 넣습니다. 원래 파일은 디스크에 그대로 두고 발행하지 않습니다.
   - 페이지 첫 스크립트가 `window.toccata.bundle`(`has`, `text`, `url`, `img`)을 만들고 `fetch()`를 감쌉니다. 묶인 경로를 `fetch`하면 처음 한 번 그 묶음을 받아 그 안의 내용으로 답합니다(03의 zip 받기는 고칠 것 없이 그대로 동작).
   - 06의 확대 그림은 `<img>`라 `fetch`를 거치지 않으므로, merge.py가 `src/tabs/parts/script.js`의 한 줄(`img.setAttribute('src', img.getAttribute('data-src'));`)을 `toccata.bundle.img(...)` 호출로 바꿔 붙입니다. 그 줄이 정확히 한 번 있지 않으면 merge.py가 멈춥니다(조각을 고쳤다면 `PARTS_IMG_OLD`를 맞춥니다).
3. 08~10 정리: 해라체 문장 끝(“넣는다”, “있다”, “0.30다”)을 합니다체로 바꾸고, 개정 기록 표시(“(r4.5 고침)”, “r4.4 고침 2b:”, “(r3 68.9 / 64.7)”, “r4.1부터”)를 뺍니다. 기계적으로 안 되는 문장은 `OVR_DESIGN`·`OVR_BUILD`·`OVR_CHECK`(원문 → 고친 문장)와 `*_DROP_*`로 고칩니다. 원문이 바뀌어 맞지 않는 항목은 결과의 `override_misses`에 나옵니다.
4. 조립: 머리말(갱신일, 회로 개정은 `hardware/pcb/netlist/sheets.json`의 가장 높은 개정과 날짜, 금액은 `data/final_items.json` totals, 준비처 없는 물건이 있으면 그 줄 수와 `#sum-gap` 링크), 탭 줄 11개, 섹션 11개, 바닥글 한 줄. CSS는 기본(`src/progress.html`) + 회로(+ 페이지 공용 `.zbar/.csheet`) + 3D + 조각들 + 요약 + 통합 보정(보조 글자색 `--ink-3`을 밝은 화면 #5F6979, 어두운 화면 #8A93A5로 바꿔 카드·색 칩 위 대비 4.5:1 이상). 스크립트는 묶음·라우터 → 회로 → 설계도 → 부품 도면 → 3D → 시뮬레이션 → 부품 → 준비 체크 순서로 각자 `<script>`.
5. 옛 링크 바꾸기: `#overview → #summary`, `#drawings`·`#rear → #dwg`, `#buy`·`#cost → #parts`, `#dwg11 → #dwg-i04`. 라우터도 같은 표로 옛 해시를 새 탭에 보냅니다. `#dwg1`~`#dwg15`(11 제외)와 `#rd1`~`#rd6`은 02 설계도 탭의 도면입니다. 08~10 안의 같은 id(dwg1 등)는 `design-dwg1`, `build-dwg12`처럼 이름을 바꿔 겹치지 않게 합니다.
6. `publish_files.json`: 발행할 모든 파일(조각 `assets.txt` 합집합 + 회로 `assets.txt` + 페이지 안 경로 + `cad/` + 묶음, 묶인 원본은 뺌)과 크기, 폴더별 개수(`by_folder`), 묶음 목록(`bundles`), 없는 파일, 15 MB 넘는 파일, 합계, 한 버전에 들어가는지(`fits_one_version`), 발행 묶음(`batches`, 한 번에 250개·60 MB 이하), 이 폴더에 있지만 안 쓰는 파일(`not_referenced_local`).
7. `--check`: 섹션이 탭마다 하나인지, id 중복(주인 표시), `href="#…"` 대상, 옛 앵커, 로컬 경로, 묶음 내용이 원본과 같은지, 06 패치가 들어갔는지, 스크립트 문법(`node --check`, JSON 블록은 파싱), 조각 CSS 범위, alert/confirm/prompt·외부 URL, 08~10에 남은 해라체·개정 표시(`style_08_10`), 채우지 못한 자리표시(`placeholders_left`, 예: `__TAIL__`), 페이지 크기.
8. `--check`의 `data_freshness`(탭 사이 데이터 대조): 05 `fin/sim/system.json`의 선 행 = cables.csv, 07 `fin/prep/lines.json`의 c-w… 줄 자르는 길이 = cables.csv(숫자 비교), `final_items.json` 글의 ‘W703 580’ 같은 언급 = 그 선의 자르는 길이, 06 `fin/loc/cards.json` 카드의 이름·쓰는 곳 = final_items.json. 다르면 `stale`에 주인과 함께 나옵니다. `older_than_source_info`는 파일 시각만 비교한 참고입니다.

2026-10-08 결과: 발행 파일 316개 + index.html = 317개(한 버전 511개 안), 48.95 MB, 발행 2번, 없는 파일 0, id 631개 중복 0, 끊긴 링크 0, 옛 앵커 27개 모두 연결, 스크립트 9블록 모두 통과, 자리표시 0, 페이지 1.15 MB. **`data_freshness`는 아직 false**: 회로 2차 검토(△29 W701 1.0 m, △30 꼬리 36 · W601 리드 40 · W602a 105 · 검정 연장 195)보다 앞서 만든 final_items.json · 06 cards.json · 07 lines.json · 05 system.json이 옛 길이를 씁니다. 위 순서 2~6을 다시 돌린 뒤 발행합니다.

## 발행

1. 다른 세션이라면 먼저 Artifact `action: "read"`, `url: https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df`로 읽습니다.
2. 지금 올라가 있는 파일 목록을 봅니다: Artifact `action: "list"`, `scope: "files"`, 같은 `url`. `publish_files.json`의 `files`에 없는 경로는 모두 지울 대상입니다(예전 버전의 `alt/*`, `img/` 바로 밑 옛 사진 13개, `dwg/d11_overall_layout.svg`, 있다면 `data/*`). 남겨 두면 511개 한도에 같이 셉니다.
3. 첫 발행(페이지 + 첫 묶음 + 능력 선언 + 옛 파일 지우기):
   ```
   Artifact publish
     url:          https://claude.ai/artifact/4GRdsojXgi8FT78uvbj5Df
     file_path:    docs/report/toccata-v4/index.html
     root:         docs/report/toccata-v4
     capabilities: {"db": {}, "user": {}, "downloads": true}
     files:        publish_files.json batches[0]의 경로들 (각 경로를 같은 이름으로)
                   + 2번에서 찾은 옛 경로마다 "<경로>": null
   ```
   - `db`·`user`는 07 준비 체크의 공유 저장(`prep/state` 문서)에, `downloads`는 회로·설계도·부품 도면·3D·준비 체크의 파일 받기 단추에 필요합니다.
4. 남은 묶음(`batches[1]`)을 같은 `url`, 같은 `file_path`로 발행합니다(넘기지 않은 파일은 그대로 남고, 넘긴 파일만 더해집니다).
5. `icon`은 넘기지 않습니다. `url` 없이 발행하면 새 아티팩트가 생기니 꼭 `url`을 줍니다.
6. "newer version"(충돌)이 나오면 그 버전을 `read`로 받아 원본(`src/`)에 반영하고 `merge.py`를 다시 돌린 뒤 발행합니다.
7. 발행 뒤 확인: 06에서 아무 카드의 ‘확대 그림’을 열어 그림이 나오는지(묶음 + blob/data 이미지), 03에서 zip 받기를 한 번 눌러 보는지(묶음 fetch + downloads).

## 미리보기

`.claude/launch.json`의 `toccata-v4-page`(포트 8765, 이 폴더를 그대로 서빙). 로컬 미리보기에는 `window.claude`가 없어 준비 체크는 이 기기 저장소(localStorage)로 동작하고 안내 띠가 뜨며, 파일 받기 단추는 파일 이름·크기 안내만 보입니다. 미리보기 창이 숨겨져 있으면 3D 모델이 `requestAnimationFrame`을 기다리느라 "조립하는 중"에 멈춰 보일 수 있습니다(창을 보이게 하면 이어서 그립니다).
