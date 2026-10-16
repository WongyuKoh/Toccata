# archive — 지난 설계·보고서·목록 보관

2026-10-06에 정리했습니다. 지금 설계(v4 확정본: 건반 액션 W1+ r4.5, 본체 L2, 터치스크린 3판, 회로도 개정 C)에서 더 쓰지 않는 자료를 여기로 옮겼습니다.
- 지운 것은 없습니다. 모두 옮기기만 했습니다.
- 경로 규칙: **원래 경로 앞에 `archive/`를 붙인 곳**에 있습니다(예: `hardware/mechanical/before/` → `archive/hardware/mechanical/before/`).
- 예외는 하나입니다. 옛 `docs/archive/*.md`는 `archive/docs/`로 옮겼습니다.
- 지금 쓰는 파일: 만들 때 쓰는 최종본은 [`../최종본/`](../최종본/), 작업 원본은 `docs/`와 `hardware/`에 있습니다.

| 지금 위치 | 무엇 | 왜 보관 |
|---|---|---|
| `docs/v0.3-overengineered.md` · `v1.5-multipart.md` · `v2.0-monolithic.md` | 이전 설계서 (v0.3 상용급, v1.5 다부품, v2.0 모노리식) | v4 설계서(`docs/01-hardware-design.md`)로 대체 |
| `docs/figures/` | v2.0 도해 SVG | v2.0 설계 |
| `docs/report/toccata-design-review.html` · `toccata-action-study.html` | v2.0 설계 검토서, 건반 액션 조사 | v2.0 시절 |
| `docs/report/toccata-audio-chain.html` · `toccata-build-v3.html` · `toccata-build-set/` · `toccata-fastener-study.html` · `toccata-cost-down.html` | v3 오디오 조합 조사, v3 제작 설계서(도면·부품표)와 생성기, 체결 조사, v3 절감안 | v3 리프 건반 → v4로 대체 |
| `docs/report/toccata-purchase-list.xlsx` | v3.2 구매 목록 (9/25) | v4 목록으로 대체 |
| `docs/report/toccata-purchase-list-v4.xlsx` · `hardware/bom/toccata-purchase-list-v4.xlsx` | **전체 구매 목록** v4 (가진 부품·공구·예비 포함 1,134,177원) | 주문은 최종본 엑셀(731,485원)로 함 |
| `docs/report/toccata-parts-list.xlsx` · `hardware/bom/parts-list/` | 핵심 부품 목록 v6과 생성기 (9/30, 832,909원) | 최종본 엑셀로 대체 |
| `hardware/bom/cost-selector/` · `hardware/bom/price-research/` | 재료·절감 선택기 생성기, 판매처 조사 | 선택이 끝나 최종 재료 페이지에 반영됨 |
| `hardware/bom/v4-parts-list.json` | 4차 모델 부품 목록 | 원본은 `hardware/mechanical/key-action-v4/model/parts_list.json` |
| `hardware/bom/final-bom/*.pre_L2.*` · `site_pre_L2/` | 최종 재료 페이지의 L2 전 백업 | L2 반영 완료 |
| `hardware/bom/README_2026-10-02.md` | 재료 폴더 README 이전 판 (전체 목록 기준 설명과 변경 기록) | README를 최종 목록 기준으로 새로 씀 |
| `hardware/mechanical/before/` | v2.0 일체형, v3 CAD·STL·렌더, 88건반 STEP, 회로 출발 메모(`curcuit/`) | v4로 대체 |
| `hardware/mechanical/toccata-최종-재료-2026-09-30.xlsx` | 최종 재료 페이지에서 내려받은 9/30 엑셀 (653,781원) | 터치스크린·L2 전 |
| `hardware/mechanical/구입항목_정리표.xlsx` | 사용자가 만든 빈 구입 양식 (10/6) | 이 양식대로 채운 것이 `최종본/01_구매목록/Toccata_구입항목_정리표_최종.xlsx` |
| `hardware/mechanical/key-action-v4/concepts/` | 건반 구조안 5개(S1 H1 K1 W1 F1)와 심사 결과 | W1으로 결정됨 → r4.5 |
| `hardware/mechanical/key-action-v4/report/r3-progress/` · `report/r4/` | 3차·4차 보고서 | r4.5 보고서로 대체 |
| `hardware/mechanical/key-action-v4/verification/` (DETAIL_BRIEF, R4_BRIEF, r3_*, r4_result) | r3·r4 검증 지시서와 결과 | r4.4·r4.5 검증으로 대체 (r4.4·r4.5 기록은 원래 자리에 남김) |
| `hardware/mechanical/touchscreen/compare/` | 화면 13가지 조합 비교 (10/1, 사용자가 B1 선택) | 결정 끝 |
| `hardware/mechanical/touchscreen/rev2_td2/` | 터치스크린 2판 (공식 Touch Display 2, L1 뚜껑) | 3판으로 대체 |
| `hardware/mechanical/cad/drawings/D06_plywood_cuts.*` · `hardware/mechanical/cad/drawings/plywood_cnc/` · `최종본/02_도면/6_합판가공/` · `최종본/01_구매목록/Toccata_합판가공_400x1200.*` | 합판 재단도 D06, 합판 CNC 가공 파일(DXF·PDF·SVG, 도그본 포함)·가공요청서·업체별 견적 문의 안내 (2026-10-15) | 2026-10-16 A안: 합판을 없애고 판을 모두 출력 |

## 알아 둘 것

- 옛 발표자료 v1~v7은 이번 정리 전에 이미 지워져 있어서 여기에 옮기지 않았습니다. 마지막 커밋(b32e015)에는 남아 있으므로 `git show b32e015:"docs/report/Toccata_발표자료_v7.pptx" > v7.pptx`처럼 꺼낼 수 있습니다.
- CAD 생성기 안의 L1·v3 보관 코드(`hardware/mechanical/cad/src/*_L1.py`, `*_v3_tall.py`, `touchscreen.py`)는 `cad/src`의 공용 모듈을 함께 써야 해서 원래 자리에 그대로 두었습니다(지금 빌드는 쓰지 않음). 그중 `touchscreen.py`를 다시 돌리려면 `rev2_td2/`를 `hardware/mechanical/touchscreen/`로 되돌려야 합니다.
- 여기 있는 문서 안의 링크와 경로는 옮기기 전 위치 기준이라 일부는 맞지 않습니다.
