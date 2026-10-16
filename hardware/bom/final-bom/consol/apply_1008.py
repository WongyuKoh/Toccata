"""2026-10-08 학교 지원 (user, 3rd clarification): 디바이스마트·엘레파츠·아이씨뱅큐·쿠팡에서 산 물건값(배송비 빼고) 200,000원까지 학교 지원.
학교 주문의 배송비는 20만 원 한도에 넣지 않는다 (학교가 냄, 사비 아님). 에어컨 주문은 따로.
Plan = consol/1008/out3_safe.json (opt_school.py school_ship_free, 해외 다웰핀·등급 미표기 센서 자석 제외).
Run after apply_1007.py on the 10/7 overrides (consol/1008/overrides.pre_1008.json).  Idempotent."""
import json, os
F = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = json.load(open(os.path.join(F, "overrides.json"), encoding="utf-8"))
N = json.load(open(os.path.join(F, "order_notes.json"), encoding="utf-8"))
EXTRA = {x["id"]: x for x in O.get("_extra", [])}
def put(iid, **kw):
    if iid in EXTRA: EXTRA[iid].update(kw); O.pop(iid, None)
    else: O.setdefault(iid, {}).update(kw)
D = "10/8 학교 지원"
O["_budget"] = 200000
O["_budget_items_only"] = True        # 한도 = 물건값
O["_school_pays_ship"] = True         # 학교 주문 배송비 = 학교 (한도 밖, 사비 아님)

# ---- school orders: same products, separate order
for iid in ("i004", "i006", "i008", "i010", "i014", "i050", "i101", "i210"):
    put(iid, sk="아이씨뱅큐 (학교)")
for iid in ("i007", "i013", "i023", "i024", "i038", "i221"):
    put(iid, sk="엘레파츠 (학교)")
for iid in ("i033", "i053", "i055", "i212", "i219", "i220"):          # 10/7 디바이스마트 직접 판매 품목 그대로
    put(iid, sk="디바이스마트 (학교)")
put("i112", n="M3 진동 방지 댐퍼 (20개)", unit=5500, url="https://www.devicemart.co.kr/goods/view?no=16080883", store="디바이스마트", seller="디바이스마트 입점 판매자 (드론 부품)",
    sk="디바이스마트·입점 (학교)",
    buy=f"20개 한 봉(4개 사용). {D}: 알씨뱅크(4,500원 + 배송 3,500원, 사비) → 디바이스마트 입점 판매자의 같은 상품(이름·구성 같음, 5,500원 + 배송 3,500원, 학교 주문). 입점 판매자라 디바이스마트 무료배송에 묶이지 않는다.")
# ---- 쿠팡 (10/8 쿠팡 검색 결과, 사용자 Chrome·와우회원)
put("i111", n="Apple 정품 USB C to 3.5mm Headphone Jack Adapter (MW2Q3KH/A)", unit=14260, store="쿠팡", seller="쿠팡 로켓배송", sk="쿠팡 로켓 (학교)",
    url="https://www.coupang.com/vp/products/169628214?vendorItemId=90711442678",
    buy=f"1개. {D}: 애플 스토어 14,900원 → 쿠팡 로켓 14,260원(같은 MW2Q3KH/A, 와우 무료배송).")
put("i099", n="코멧 강력한 원형 자석 8mm x T 3mm, 실버, 12개", t="네오디뮴 자석 Ø8×3 12개 (뚜껑)", unit=3890, qty=1, store="쿠팡", seller="쿠팡 로켓배송", sk="쿠팡 로켓 (학교)",
    url="https://www.coupang.com/vp/products/7589411879?vendorItemId=87148299583", pack="12개 1세트",
    buy=f"12개 한 세트. {D}: 대건상사 160원 × 12(사비) → 쿠팡 로켓 코멧 Ø8×3 12개 3,890원(학교). 등급 표기는 없지만 뚜껑 고정용이라 센서와 무관하다. 붙는 힘이 약하면 대건 N35로 바꾼다.")
put("i051", n="삼미스피커 CW-100B25 4인치 정격25W 최대50W 저음용스피커 오디오 자작용", unit=8500, store="쿠팡", seller="쿠팡 판매자 (삼미 CW-100B25)", sk="쿠팡·삼미 CW-100B25 (학교)",
    url="https://www.coupang.com/vp/products/181380607?vendorItemId=4341984346",
    buy=f"2개. {D}: 11번가 세운상가새한음향 9,600원 × 2 → 쿠팡 같은 모델 8,500원 × 2 (배송비 4,000원은 학교 주문).")
put("i071", n="세메다인 슈퍼X 8008 탄성접착제 흑색 20ml", unit=8000, store="쿠팡", seller="쿠팡 판매자 (세메다인)", sk="쿠팡·세메다인 흑색 (학교)",
    url="https://www.coupang.com/vp/products/7839505281?vendorItemId=90922897918",
    buy=f"20 mL 2개. {D}: 11번가 미건케미칼 7,300원 + 배송 3,000(사비) → 쿠팡 같은 흑색 8,000원 × 2 (배송비 3,000원은 학교 주문). 강철 블록 접착층은 보이지 않아 색은 상관없다.")
put("i039", n="화성고무 피스고무발 RUB-E2 28*5 (RUB-E2) 20EA", unit=433, qty=20, min=20, step=20, store="쿠팡", seller="쿠팡 판매자 (화성고무)", sk="쿠팡·화성고무 (학교)",
    url="https://www.coupang.com/vp/products/130058387?vendorItemId=3929147929", pack="20개 1봉 (8,660원)",
    buy=f"20개 한 봉(14개 사용). {D}: 엘레파츠 583원 × 20 = 11,660원 → 쿠팡 같은 화성고무 RUB-E2 20개 8,660원(배송비 3,000원은 학교 주문, 10/14 도착 예정).")
put("i107", n="스튜디오분트 100% 메리노양모 70수 펠트지 1mm (80 블랙)", unit=6900, store="쿠팡", seller="쿠팡 판매자 (스튜디오분트)", sk="쿠팡·스튜디오분트 (학교)",
    url="https://www.coupang.com/vp/products/6627385385?vendorItemId=82316320569",
    buy=f"1장. {D}: 스튜디오분트 직영몰과 같은 상품을 쿠팡에서(판매자 분트(Bunt), 6,900원, 배송비 3,000원은 학교 주문). 옵션 '80.블랙' — 10/8 쿠팡 상품 페이지에서 재고 있음·10/13 도착 예정 확인. 2 mm(i106)는 쿠팡에 없어(10/8 확인) 직영몰(사비)에서 산다.")
nt_extra = {"i106": "쿠팡에 2 mm 없음 (10/8 확인) — 직영몰", "i062": "쿠팡 상우아트에는 H-20 검정 없음 (10/8 확인) — 11번가"}
for iid in ("i066", "i067"):
    put(iid, n="국내최초 스텐환봉 절단판매 1M (4파이)", unit=1500, store="쿠팡", seller="쿠팡 판매자 (스텐환봉 절단판매 = onezaze)", sk="쿠팡·onezaze (학교)",
        url="https://www.coupang.com/vp/products/7575965502?vendorItemId=87087416424",
        buy=f"{D}: 11번가 onezaze와 같은 판매자의 쿠팡 상품(1,500원, 배송비 3,500원은 학교 주문). 건반 봉 2 + 레버 봉 2를 한 주문으로.")
put("i070", n="흑연파우더 소 30ml 스케치 드로잉 흑연가루", t="흑연 가루 30 ml (드로잉용 흑연 파우더 소)", unit=3000, store="쿠팡", seller="쿠팡 판매자 (흑연파우더)", sk="쿠팡·흑연 (학교)",
    url="https://www.coupang.com/vp/products/8243268767?vendorItemId=90747166966",
    buy=f"1통. {D}: 11번가 비젼몰 크레타칼라 30 ml 2,750원 + 배송 3,000(사비) → 쿠팡 흑연 파우더 소 30 ml 3,000원(배송비는 학교 주문). 브랜드 표기가 없어 받으면 확인.")
# ---- personal changes
put("i052", n="방울솜 1kg 화이트", t="방울솜(폴리에스터) 1 kg — 흡음솜", unit=5200, store="쿠팡", seller="쿠팡 로켓배송", sk="쿠팡 로켓",
    url="https://www.coupang.com/vp/products/8826157891?vendorItemId=92708146513", pack="1 kg 1봉",
    buy=f"1봉. {D}: 11번가 두유레디 300 g 2,700원 + 배송 3,000 → 쿠팡 로켓 1 kg 5,200원(와우 무료배송, 사비 −500원). 상자당 40~60 g만 쓴다.")
# 파츠파츠(RP2040·먹스)·세메다인 외 나머지는 10/7 그대로 (사비)

# ---- ship rules
S = O.setdefault("_ships", {})
for k in ("엘레파츠", "디바이스마트"):
    if k in S: S[k].pop("carry", None); S[k].pop("shared", None)
for k in [k for k in S if k.endswith("(학교)")]:
    S.pop(k)
SCH = {"school": True, "verified": True}
def sch(k, fee, fo, basis): S[k] = {"fee": fee, "free_over": fo, **SCH, "basis": basis + " — 학교 지원 주문(따로 결제, 배송비는 학교가 내고 20만 원 한도에 넣지 않음)"}
sch("아이씨뱅큐 (학교)", 2700, 55000, "아이씨뱅큐: 5만 원(VAT 별도) 이상 무료 → 55,000원")
sch("엘레파츠 (학교)", 3000, 66000, "엘레파츠: 공급가 6만 원 이상 무료 → 66,000원")
sch("디바이스마트 (학교)", 2700, 66000, "디바이스마트 직접 판매: 2,700원, VAT 포함 66,000원 이상 무료")
sch("디바이스마트·입점 (학교)", 3500, 350000, "디바이스마트 입점 판매자(댐퍼): 택배 3,500원, 350,000원 이상 무료")
sch("쿠팡 로켓 (학교)", 0, None, "쿠팡 로켓배송: 와우회원 무조건 무료배송 (10/8)")
sch("쿠팡·삼미 CW-100B25 (학교)", 4000, None, "쿠팡 검색 결과(10/8): 배송비 4,000원 조건부 무료배송(기준 미확인)")
sch("쿠팡·세메다인 흑색 (학교)", 3000, None, "쿠팡 검색 결과(10/8): 배송비 3,000원")
sch("쿠팡·화성고무 (학교)", 3000, None, "쿠팡 검색 결과(10/8): 배송비 3,000원")
sch("쿠팡·스튜디오분트 (학교)", 3000, None, "쿠팡 검색 결과(10/8): 배송비 3,000원 조건부 무료배송(기준 미확인)")
sch("쿠팡·onezaze (학교)", 3500, None, "쿠팡 검색 결과(10/8): 배송비 3,500원")
sch("쿠팡·흑연 (학교)", 3000, None, "쿠팡 검색 결과(10/8): 배송비 3,000원 조건부 무료배송(기준 미확인)")
S["쿠팡 로켓"] = {"fee": 0, "free_over": None, "verified": True, "basis": "쿠팡 로켓배송: 와우회원 무조건 무료배송 (10/8)"}

# ---- order sheet names / notes
site = N.setdefault("site", {}); sn = N.setdefault("store_note", {}); nt = N.setdefault("note", {})
for k in [k for k in list(site) if k.endswith("(학교)")]: site.pop(k, None)
for k in [k for k in list(sn) if k.endswith("(학교)")]: sn.pop(k, None)
site.update({"아이씨뱅큐 (학교)": ["아이씨뱅큐", "icbanq.com"], "엘레파츠 (학교)": ["엘레파츠", "eleparts.co.kr"], "디바이스마트 (학교)": ["디바이스마트", "devicemart.co.kr"],
             "디바이스마트·입점 (학교)": ["디바이스마트 · 입점 판매자(댐퍼)", "devicemart.co.kr"],
             "쿠팡 로켓 (학교)": ["쿠팡 로켓배송", "coupang.com"], "쿠팡 로켓": ["쿠팡 로켓배송", "coupang.com"],
             "쿠팡·삼미 CW-100B25 (학교)": ["쿠팡 · 삼미 CW-100B25 판매자", "coupang.com"], "쿠팡·세메다인 흑색 (학교)": ["쿠팡 · 세메다인 판매자", "coupang.com"],
             "쿠팡·화성고무 (학교)": ["쿠팡 · 화성고무 판매자", "coupang.com"], "쿠팡·스튜디오분트 (학교)": ["쿠팡 · 스튜디오분트", "coupang.com"],
             "쿠팡·onezaze (학교)": ["쿠팡 · 스텐환봉 절단판매(onezaze)", "coupang.com"], "쿠팡·흑연 (학교)": ["쿠팡 · 흑연파우더 판매자", "coupang.com"]})
for k in site:
    if k.endswith("(학교)"): sn[k] = "학교 지원 주문 — 사비 주문과 따로 결제 (배송비는 학교, 20만 원 한도 밖)"
sn["아이씨뱅큐 (학교)"] += " · Adafruit·AOFENG 줄에 배송비가 따로 붙는지 장바구니에서 확인"
sn["쿠팡 로켓"] = "와우회원 무료배송"
nt.update({"i111": "쿠팡 로켓 MW2Q3KH/A", "i051": "같은 CW-100B25", "i066": "건반 봉", "i067": "레버 봉", "i052": "1 kg (300 g 대신)", "i070": "30 ml",
           "i039": "20개 1봉", "i099": "12개 1세트", "i107": "옵션 80.블랙 (재고 확인)", "i112": "20개 1봉", "i071": "흑색 (백색과 같은 8008)"})
nt.update(nt_extra)

# ---- design panel
dz = O.setdefault("_design", [])
dz[:] = [x for x in dz if not x.startswith(("2026-10-07 배송비 재최적화", "2026-10-08 학교 지원", "더 줄이는 선택지", "사비를 더 줄이는 선택지"))]
dz[0:0] = [
  "2026-10-08 학교 지원: '학교 지원' 표시 판매처(아이씨뱅큐·엘레파츠·디바이스마트·쿠팡)의 물건값 199,960원(한도 200,000원)을 학교가 내고, 그 주문들의 배송비 28,700원도 학교가 낸다(한도 밖). 나머지는 사비 227,166원(배송비 포함). 학교 주문은 따로 결제하고 에어컨 주문과 합치지 않는다.",
  "10/8 쿠팡 확인: 스튜디오분트 1 mm 80.블랙은 쿠팡에 있음(학교 주문), 2 mm는 쿠팡에 없음 → 직영몰(사비). 대원 0.5T 접착 펠트지 H-20 검정은 쿠팡 상우아트에 없음 → 11번가 상우아트(사비).",
  "사비를 더 줄이는 선택지(기본값에 넣지 않음): 쿠팡 해외 판매자 304 다웰핀 M2×12 100개(도착 10/22 무렵·공차 미확인) · 텅스텐 퍼티 i063 나중에 −8,750 · 하네나이트 30×500 점착 −4,400",
]
json.dump(O, open(os.path.join(F, "overrides.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(N, open(os.path.join(F, "order_notes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("patched")
