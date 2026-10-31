#!/usr/bin/env python3
"""Canonical final item list for the Toccata page (부품·사용처 / 준비 체크 / 요약 tabs).

Writes  docs/report/toccata-v4/data/final_items.json
Copies  item photos to docs/report/toccata-v4/img/bom/<id>.<ext>  (< 150 KB each)

Inputs (read only):
  hardware/bom/final-bom/data.json, state_main.json, overrides.json, img/
  최종본/01_구매목록/Toccata_학교_사비_구매목록_2026-10-08.xlsx   (what was actually ordered)
  hardware/pcb/netlist/bom.csv, cables.csv                     (circuit refdes)
  hardware/mechanical/cad/src  build_all.collect()             (CAD part ids, in memory only)

Run from anywhere:  python3 docs/report/toccata-v4/src/build_items.py
Exits non-zero when a validation check fails.  Never calls build_all.main().
"""
import csv
import io
import json
import os
import re
import shutil
import sys
import contextlib
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.dirname(HERE)                                   # docs/report/toccata-v4
ROOT = os.path.abspath(os.path.join(PAGE, "..", "..", ".."))   # repo root
BOM = os.path.join(ROOT, "hardware", "bom", "final-bom")
XLSX = os.path.join(ROOT, "최종본", "01_구매목록", "Toccata_학교_사비_구매목록_2026-10-08.xlsx")
NET = os.path.join(ROOT, "hardware", "pcb", "netlist")
CAD_SRC = os.path.join(ROOT, "hardware", "mechanical", "cad", "src")
OUT_JSON = os.path.join(PAGE, "data", "final_items.json")
OUT_IMG = os.path.join(PAGE, "img", "bom")

USB_CAD_M = [1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]                 # bought USB lengths (10/14: NA993 1 m ×2 i022 + HB466 0.5 m ×6 i226;
                                                                 #  CAD routes O5·O6 are 0.3 m, the 0.5 m cable ties up the slack)
EXPECT = dict(school_items=215852, school_ship=28700, personal=356771, total=601323, school_lines=29)   # 10/16: -합판 17,680 -목공본드 3,949, +세메다인 1 (학교 8,000), +검정 PETG 4 (64,600 + 배송 3,000); 10/31 A16: +만능기판 8 × 12 4장 (11,440 + 배송 2,700, 사비)

CAT_ORDER = ["건반 액션", "센서·MCU·기판", "제어·전원", "오디오", "터치스크린", "본체·결합",
             "3D 출력 재료", "소모품", "페달", "공구"]
SOURCE_KO = {"school": "학교 지원 구매", "personal": "사비 구매",
             "owned": "가진 것", "tool": "가진 공구", "gap": "아직 준비처 없음"}

# --------------------------------------------------------------------------------------------
# 1. Curated final-design data.  Every number below comes from the CAD solids (build_all.collect,
#    manifest bbox), hardware/mechanical/cad/README.md, the circuit bom/cables CSV or data.json;
#    'need_note' says which.
#    fields: cat, name, unit, need, need_note, where, check, role, optional, pack (units per ordered qty)
#    role: 부품 (stays in the instrument) | 소모품 (used up) | 공구 | 부속 (kept with it) | 시험용
# --------------------------------------------------------------------------------------------
K = {}


def _fmt(v):
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:g}"


def c13_lengths():
    """Speaker wire (purchase code C13) cut lengths from hardware/pcb/netlist/cables.csv.
    '리드 100' (XT60 lead) and '꼬리 30' (fuse-holder tail) are not C13 and are removed.
    'a / b' = red + black singles, 'a × n' = n singles, '1심' = single, otherwise 2-core length."""
    two, one, p2, p1 = 0.0, 0.0, [], []
    with open(os.path.join(NET, "cables.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if "C13" not in (r.get("구매 목록 코드") or ""):
                continue
            s = re.sub(r"(리드|꼬리)\s*\d+(?:\.\d+)?", "", r["자르는 길이 (mm)"])
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
            if not nums:
                continue
            if "×" in s:
                one += nums[0] * nums[1]
                p1.append(f"{r['W']} {_fmt(nums[0])} × {_fmt(nums[1])}")
            elif "/" in s:
                one += sum(nums)
                p1.append(f"{r['W']} " + " + ".join(_fmt(n) for n in nums))
            elif r["심"].strip() == "1심":
                one += nums[0]
                p1.append(f"{r['W']} {_fmt(nums[0])}")
            else:
                two += nums[0]
                p2.append(f"{r['W']} {_fmt(nums[0])}")
    # W601 black return (BRD-05 splice S2): 16 AWG black from the harness splice to the star point (buck IN-), not a
    # cables.csv row.  Same rule as hardware/pcb/src/harness.py: cut(PWR-FUSE + PWR-BUS-BUCK) = path + 20, up to 5 mm.
    blk = W601["black_ext"]
    if blk:
        one += blk
        p1.append(f"W601 검정 연장 {_fmt(blk)}")
    total = two + one
    need_m = max(1, -(-int(round(total)) // 1000))          # round up to whole metres
    note = (f"2심 그대로 {_fmt(two)} mm ({' + '.join(p2)}) + 한 가닥씩 {_fmt(one)} mm ({' + '.join(p1)}) "
            f"= 선 길이 약 {total / 1000:.1f} m (cables.csv 자르는 길이 + BRD-05 검정 연장, XT60 리드·홀더 꼬리 제외) → {need_m} m로 잡음. 7 m 롤이라 넉넉합니다")
    return dict(two=two, one=one, total=total, need_m=need_m, note=note)


def _cables():
    with open(os.path.join(NET, "cables.csv"), encoding="utf-8-sig") as f:
        return {r["W"]: r for r in csv.DictReader(f)}


def w601_harness():
    """Battery harness W601 (X606 XT60-M lead + fuse-holder 12 AWG stub) from cables.csv + cad_centre.json.
    Rule (hardware/pcb/README.md △25): holder -x end -> XT60 back, assembled, <= limit; splice overlap 10 mm."""
    row = _cables().get("W601", {})
    txt = row.get("자르는 길이 (mm)", "")
    m_lead, m_stub, m_max = (re.search(p, txt) for p in (r"리드\s*(\d+)", r"꼬리\s*(\d+)", r"≤\s*(\d+)"))
    lead = int(m_lead.group(1)) if m_lead else None
    stub = int(m_stub.group(1)) if m_stub else None
    lim = int(m_max.group(1)) if m_max else None
    ovl = 10                                                   # twisted splice overlap (harness.py SPLICE_OVL)
    total = lead + stub - ovl if lead and stub else None
    black_ext, need_l = None, None
    try:
        with open(os.path.join(NET, "cad_centre.json"), encoding="utf-8") as f:
            cc = json.load(f)
        ln = cc["lengths"]
        black_ext = int(-(-(ln["PWR-FUSE"] + ln["PWR-BUS-BUCK"] + 20.0) // 5) * 5)
        need_l = cc["points"]["mismate"]["need"]["L"]
    except (OSError, KeyError, ValueError):
        pass
    return dict(lead=lead, stub=stub, max=lim, ovl=ovl, total=total, cut_off=(100 - lead) if lead else None,
                black_ext=black_ext, need_l=need_l)


def aux_c14():
    """AUX cable (C14) pieces W701 / W702 / W707 from cables.csv: one 3 m cable cut in half."""
    rows = _cables()

    def mm(w):
        s = rows.get(w, {}).get("자르는 길이 (mm)", "")
        n = re.search(r"(\d+(?:\.\d+)?)\s*(m\b)?", s)          # '0.9 m' = metres, '약 300' = mm
        if not n:
            return None
        return float(n.group(1)) * (1000.0 if n.group(2) else 1.0)
    w701, w702, w707 = mm("W701"), mm("W702"), mm("W707")
    return dict(w701=w701, w702=w702, w707=w707, half=1500.0, left=(1500.0 - w701) if w701 else None)


W601 = w601_harness()
AUX = aux_c14()


def circuit_rev():
    try:
        head = open(os.path.join(ROOT, "hardware", "pcb", "README.md"), encoding="utf-8").readline()
        m = re.search(r"개정\s*([A-Z])", head)
        return f"개정 {m.group(1)}" if m else "개정 ?"
    except OSError:
        return "개정 ?"


def circuit_issues(nonprint):
    """Points where the circuit lists (rev E) still differ from the final purchase / CAD.  Computed, not typed."""
    notes = []
    usb = {w: float(m.group(1)) for w, r in _cables().items() if re.search(r"NA993|HB466", r["선"])
           for m in [re.search(r"(\d+(?:\.\d+)?)\s*m\b", r["선"])] if m}
    if sorted(usb.values()) != sorted(USB_CAD_M):
        notes.append("cables.csv의 USB 선 길이(" + ", ".join(f"{w} {_fmt(v)} m" for w, v in sorted(usb.items())) +
                     ")가 산 선 1 m × 2(O1·O2, i022), 0.5 m × 6(O3~O7·PED, i226)과 다릅니다.")
    if W601["black_ext"] and "W601 검정" not in " ".join(r.get("W", "") + r.get("선", "") for r in _cables().values()):
        notes.append(f"cables.csv에 W601 검정 연장(하네스 이음 S2 → 강압 IN− 별 접지점, 16 AWG 약 {W601['black_ext']} mm, BRD-05)이 "
                     "따로 한 줄로 없습니다. 이 목록은 스피커선(i037) 길이에 넣어 셉니다.")
    awg18 = sorted({p.name_ko for p in nonprint if "18 AWG" in (p.name_ko or "") and re.match(r"C-(SPK|SPKPIG|PWR)", p.id)})
    if awg18:
        notes.append("CAD 선 이름 " + str(len(awg18)) + "개가 18 AWG로 적혀 있지만 회로 선 목록(harness.csv)대로 16 AWG를 씁니다(i037).")
    if not notes:
        return []
    return [dict(level="낮음", id="circuit", text="회로 목록·CAD 이름에서 맞춰 볼 곳: " + " ".join(notes))]


def k(iid, **kw):
    kw.setdefault("role", "부품")
    kw.setdefault("optional", False)
    kw.setdefault("pack", 1)
    K[iid] = kw


# ---- 건반 액션 ------------------------------------------------------------------------------
k("i014", cat="건반 액션", name="캡스턴 나사 M3×6 버튼헤드", unit="개", need=88,
  need_note="건반마다 1개: 모듈 12 × 7 + 끝 부속 4 = 88 (CAD CAPSTAN 88개)",
  where="건반 꼬리 숨은 빔의 옆 홈에 넣은 M3 너트에 위 Ø2.8 구멍으로 돌려 넣어(A15, 처음 넣을 때 나사 끝이 홈 밑 0.4 막을 뚫음), 레버 밑 펠트 띠를 미는 높이 조절 나사입니다. 벤치 지그에서 1/8바퀴씩 돌려 누르는 힘을 맞춥니다.",
  check="ISO 7380 버튼헤드(머리 Ø5.7 × 1.65, 2.0 mm 육각)인지 봅니다. 100개 중 12개는 단계 0 시험과 예비로 둡니다.")
k("i011", cat="건반 액션", name="M3 육각너트 (강철)", unit="개", need=92,
  need_note="캡스턴 88 + 방진 브래킷 BRK2 볼 속 너트 4 = 92 (CAD NUT 88 + BRK2 NUT 4; A13에서 뺐던 캡스턴 너트를 A15(2026-10-30)에서 되살림)",
  where="건반 꼬리 빔의 너트 홈(맞변 5.6 × 2.8, +x 옆)에 옆에서 밀어 넣어 캡스턴 나사를 받습니다(88개). 홈 천장은 구멍 없는 0.4 막이라 서포트 없이 출력됩니다(A15). 끝 부속 볼의 방진 브래킷 너트 홈에 4개를 더 넣습니다.",
  check="표준 M3 육각너트(맞변 5.5)인지 봅니다. 92개 이상이 있는지 셉니다.")
k("i119", cat="건반 액션", name="강철 띠 9T × 19 × 1 m", unit="개", need=4,
  need_note="강철 블록 9 × 19 × 40 (53.7 g) 88개 = 1 m 띠 4장 (띠 한 장에서 41.3 간격으로 24개, CAD STEEL 88개)",
  where="1 m 띠를 40 mm씩 잘라 강철 블록 88개를 만듭니다. 블록은 레버 캐리어에 밑에서 끼우고 MS 폴리머(i071)로 붙이는 무게 추이고, 윗면이 업스톱 패드에 닿습니다.",
  check="띠마다 두께를 재서 8.9~9.1 mm만 씁니다(캐리어 주머니 9.2). 블록 길이는 40 −0.1/−0.3으로 자릅니다.")
k("i123", cat="건반 액션", name="미스미 토션스프링 C-UA90R5-3-0.5", unit="개", need=88,
  need_note="레버마다 1개 = 88 (CAD SPRING 88개). 100개 중 단계 0 시험 4, 예비 8",
  where="레버 허브의 스프링 주머니에 넣고 레버 봉에 꿰는 비틀림 스프링입니다. 다리를 긴 쪽 22.3, 짧은 쪽 8.0으로 잘라 짧은 다리는 허브 가둠 홈, 긴 다리는 뒷벽 보스 홈에 겁니다.",
  check="선경 0.5, 안지름 5, 두 암 90°인지 봅니다. 다리는 피아노선 니퍼(i127)로 자릅니다.")
k("i121", cat="건반 액션", name="밸런스 핀 Ø2 × 12 SUS304", unit="개", need=88, pack=100,
  need_note="건반마다 1개 = 88 (CAD balancepin 88개). 100개 봉에서 벤치 지그 1·단계 0 시험 5·예비 4",
  where="밸런스 레일(y135.3)에 핀 높이 게이지로 눌러 넣어 꼭대기를 z23.30에 맞춥니다. 건반 밑 홈(천 0.5T)이 이 핀을 물어 건반 뒤쪽 좌우 위치를 잡습니다.",
  check="Ø2 × 12 평행 핀(ISO 2338)인지 캘리퍼스로 잽니다. 박은 뒤 게이지로 z23.20~23.40인지 봅니다.")
k("i066", cat="건반 액션", name="SUS304 환봉 Ø4 × 1 m (건반 봉)", unit="개", need=2,
  need_note="건반 봉 9토막: 161.4 × 7 + 끝 부속 43.9 + 20.4 = 1,194.1 mm (CAD keyrod 9개) → 1 m 봉 2개",
  where="건반 시소의 축입니다. 밸런스 레일의 봉 받침(y141, z21.5)에 놓고 건반 노치가 위에서 스냅으로 뭅니다. 모듈마다 161.4 mm, 끝 부속 EL 43.9·ER 20.4 mm로 자릅니다.",
  check="지름이 3.97~4.00 mm인지 몇 곳 잽니다. 곧은지 굴려 봅니다.")
k("i067", cat="건반 액션", name="SUS304 환봉 Ø4 × 1 m (레버 봉)", unit="개", need=2,
  need_note="레버 봉 9토막: 161.4 × 7 + 끝 부속 45.9 + 22.2 = 1,197.9 mm (CAD leverrod 9개) → 1 m 봉 2개",
  where="무게 레버 12개가 매달려 도는 축입니다(모듈 뒤 y203.25, z33.5). 핀 보스 5개, 레버 허브 12개, 스프링 코일 12개를 꿰고 이음 쪽 끝을 출력 마개로 막습니다.",
  check="건반 봉과 같은 상품입니다. 지름 3.97~4.00 mm인지 잽니다.")
k("i106", cat="건반 액션", name="메리노 울 펠트 2T 20 × 30 cm (검정)", unit="장", need=1,
  need_note="약 220 cm² 사용 (캡스턴 띠 88 + 앞 펠트 백건 띠 9·흑건 조각 36 + 키퍼 펠트 88, data 추정)",
  where="레버 88개 밑 캡스턴 펠트 띠(폭 7 × y176.5~192.0), 앞 레일 앞 펠트(백건 띠 9개, 흑건 조각 36개, 하네나이트 1T 위), 키퍼 훅 88개 밑 펠트(5.2 × 3)를 자릅니다.",
  check="두께 2 mm인지 잽니다. 접착면이 없어 종이 양면테이프나 MS 폴리머로 붙입니다.")
k("i107", cat="건반 액션", name="메리노 울 펠트 1T 20 × 30 cm (검정)", unit="장", need=1,
  need_note="약 100 cm² 사용 (업스톱 패드 겉면 88 + 쉼 펠트 바탕 88, data 추정)",
  where="업스톱 패드의 강철이 닿는 면(6 × 12.2) 88개와 건반 꼬리 밑 쉼 펠트 1.5T의 바탕 88개를 자릅니다. 쉼 펠트는 이 1T 위에 0.5T 천(i062)을 한 겹 붙여 만듭니다.",
  check="두께 1 mm인지 잽니다.")
k("i125", cat="건반 액션", name="WAKI 하네나이트 1T 170 × 245", unit="장", need=1,
  need_note="약 110 cm² 사용 (앞 펠트 밑층: 백건 띠 9 + 흑건 조각 36, data 추정)",
  where="앞 레일의 앞 펠트 2T 밑에 까는 1T 저반발 층입니다. 백건 줄은 모듈·끝 부속마다 띠(y1.5~9.0, 폭 7.5), 흑건은 36개 자리마다 조각(y54.5~59.0)으로 붙입니다.",
  check="두께 1 mm인지 잽니다. 단계 0 시험 4 결과에 따라 2겹으로 바꿀 수 있어 남는 양을 버리지 않습니다.")
k("i124", cat="건반 액션", name="WAKI PORON 5T 점착 100 × 100", unit="장", need=1,
  need_note="업스톱 패드 6 × 12.2를 88개 + 예비 (한 장에서 약 128개)",
  where="업스톱 패드 폼입니다. 6 × 12.2로 잘라 강철이 닿는 쪽에 펠트 1T를 겹치고 패드 바 쐐기에 붙입니다. stl/print/04의 패드 바는 이 5T에 맞춰 쐐기를 1.0 두껍게 만든 것입니다.",
  check="두께가 5 mm인지 잽니다. 6T가 오면 stl/print_extra의 '대안_패드바_PORON6T용'을 대신 뽑습니다.")
k("i062", cat="건반 액션", name="대원 0.5T 접착 펠트지 30 × 45 (검정)", unit="장", need=1,
  need_note="약 270 cm² 사용 (부싱 천 약 250 + 쉼 펠트 겹 약 20, data 추정)",
  where="건반 스냅 노치 안쪽과 밸런스 핀 홈 양쪽 벽, 프레임 가이드 탭 88개 옆에 붙이는 0.5T 부싱 천입니다. 쉼 펠트 1.5T의 위 겹으로도 씁니다.",
  check="접착층을 포함한 두께를 캘리퍼스로 잽니다. 출력 치수는 천 0.5T를 넣고 노치 R2.55 → R2.05로 계산했습니다.")
k("i069", cat="건반 액션", name="OHP 필름 A4 0.1 mm 20매", unit="팩", need=1,
  need_note="PET 심 6 × 12.2 약 50장 (data 추정)",
  where="업스톱 패드와 패드 바 쐐기 사이에 넣는 0.1 mm PET 심입니다. 6 × 12.2로 잘라 업스톱 시점을 맞출 때 건반마다 필요한 만큼 넣고 뺍니다.",
  check="두께가 0.1 mm인지 캘리퍼스로 잽니다(판매 페이지에 두께 표기가 없습니다).")
k("i063", cat="건반 액션", name="텅스텐 퍼티 22 g", unit="개", need=1,
  need_note="필요할 때 조금씩 (설계서에 총량 없음)",
  where="조립 뒤 누르는 힘(DW)이 47~55 g을 벗어난 건반만 맞춥니다. 레버 강철 앞 윗면에 붙이면 DW가 오르고(1 g = 백 +1.23 g), 건반 앞에 붙이면 내려갑니다(1 g = 백 −1.06 g).",
  check="22 g인지 저울로 잽니다.")

# ---- 센서·MCU·기판 ---------------------------------------------------------------------------
k("i004", cat="센서·MCU·기판", name="홀센서 TI DRV5055A2QLPG", unit="개", need=89,
  need_note="센서 기판 12 × 7 = 84 + 끝 부속 EL 3 + ER 1 + 페달 1 = 89 (bom.csv U201~U212·U401~U403·U411·U551)",
  where="건반 밑 자석과의 거리를 전압으로 재는 센서입니다. 표시면을 위로 눕혀 센서 바 포켓(y67)에 넣고 다리를 2.54 간격으로 벌려 센서 기판에 납땜합니다. 페달 안에도 1개 들어갑니다.",
  check="몸통 표시가 DRV5055A2(A2 등급)인지 봅니다. 3.3 V를 넣고 자석이 없을 때 출력이 1.59~1.71 V인지 몇 개 잽니다.")
k("i098", cat="센서·MCU·기판", name="네오디뮴 자석 Ø5 × 2 N35", unit="개", need=89,
  need_note="건반 88 + 페달 1 = 89 (CAD MAGNET 88개, 페달 자석은 모델에 없음). 주문 89개 = 예비 없음",
  where="건반 밑면 포켓(y67, Ø5.2 × 2.1)에 S극이 아래로 가게 눌러 넣고 순간접착제로 고정합니다. 1개는 페달 발판 밑 발끝 쪽에 붙입니다.",
  check="89개가 왔는지 세고 깨진 것이 없는지 봅니다. 예비가 없어 깨지거나 극을 거꾸로 넣으면 다시 사야 합니다.")
k("i006", cat="센서·MCU·기판", name="100 nF 1206 칩 콘덴서", unit="개", need=97,
  need_note="센서 기판 12 × 7 = 84 + 제어 기판 7 + EL 3 + ER 1 + 페달 센서 1 + 페달 보드 1 = 97 (bom.csv)",
  where="홀센서마다 3V3 옆에 1개, 제어 기판·페달 보드 전원에 1개씩 납땜하는 바이패스 콘덴서입니다.",
  check="100개(97개 사용 + 예비 3)인지 셉니다. 1206(3.2 × 1.6) 크기이고 표시가 없으니 봉투째 보관합니다.")
k("i007", cat="센서·MCU·기판", name="10 µF 1206 칩 콘덴서 16 V", unit="개", need=16,
  need_note="센서 기판 2 × 7 = 14 + EL 1 + ER 1 = 16 (bom.csv C213·C214·C404·C412)",
  where="센서 기판마다 3V3 버스 양 끝에 2개, 끝 부속 EL·ER 기판에 1개씩 납땜합니다.",
  check="16개인지 셉니다. 100 nF와 섞이지 않게 봉투를 따로 둡니다.")
k("i008", cat="센서·MCU·기판", name="1 kΩ 1206 칩 저항", unit="개", need=4,
  need_note="끝 부속 EL R401~R403 + ER R411 = 4 (bom.csv). 10개 단위",
  where="끝 부속 기판 EL·ER의 센서 출력 직렬 저항입니다. 센서 바가 윗면을 덮어 아랫면에 답니다.",
  check="몸통 표시 '102'를 봅니다.")
k("i005", cat="센서·MCU·기판", name="핀헤더 1 × 40 (2.54 mm)", unit="줄", need=9, role="부품",
  need_note="먹스 7 × (1×16 + 1×8) = 168핀 + RP2040-Zero 8 × (1×9 × 2) = 144핀 = 312핀, 자를 때 버리는 핀까지 9줄 (bom.csv A302-HDR·A301-HDR·A501-HDR)",
  where="제어 기판에 먹스 모듈과 RP2040-Zero를 세워 납땜하는 핀입니다. 제로용은 좌·우 줄만 씁니다 - A16(10/31)부터 모듈 제어 기판의 제로는 플라스틱 몰드를 그대로 둡니다(페달 보드 제로는 그대로 몰드를 뺌). 기판 밑으로 나온 끝은 1.0 mm 이하로 자릅니다.",
  check="9줄(360핀) 이상 있는지 봅니다. 먹스 모듈에 헤더가 딸려 오면 그만큼 덜 씁니다.")
k("i084", cat="센서·MCU·기판", name="RP2040-Zero (PP-A799-2)", unit="개", need=8,
  need_note="제어 기판 A301 × 7 + 페달 보드 A501 1 = 8 (CAD E-ZERO 7 + PEDZERO 1)",
  where="모듈마다 제어 기판에 1개, 가운데 유닛 B칸 페달 보드에 1개를 핀 헤더로 세워 납땜합니다. 각각 USB-MIDI 장치로 허브에 붙습니다.",
  check="18.0 × 23.5 mm, USB-C인지 봅니다. BOOTSEL을 누른 채 PC에 꽂아 RPI-RP2 드라이브가 뜨는지 하나씩 봅니다.")
k("i085", cat="센서·MCU·기판", name="16채널 먹스 모듈 CD74HC4067", unit="개", need=7,
  need_note="제어 기판 A302 × 7 (CAD E-MUX 7개)",
  where="모듈마다 제어 기판에 1개를 핀 헤더로 세워 납땜합니다. 센서 12개 출력을 RP2040 ADC 하나로 차례로 읽습니다.",
  check="두 줄 간격 15.24 mm, 핀 C0~C15 + GND·VCC·EN·S0~S3·SIG인지 봅니다.")
k("i023", cat="센서·MCU·기판", name="16심 리본 케이블 2651-16P", unit="m", need=2,
  need_note="W101~W107 약 180 mm × 7 = 1.26 m + EL·ER 리드 0.35 m ≈ 1.6 m → 1 m 단위 2 (CAD RIBBON 7 + LEAD 2)",
  where="모듈마다 센서 기판 J201 ↔ 제어 기판 J301을 잇는 16심 리본입니다(커넥터 없이 양끝 납땜). 끝 부속 리드 EL 5심 350 mm(W401)와 ER 3심 300 mm(W411)도 이 리본을 갈라 만듭니다.",
  check="1번 심 빨간 줄과 1.27 mm 피치인지 봅니다.")
k("i024", cat="센서·MCU·기판", name="16심 리본 케이블 추가 1 m (배선용)", unit="m", need=1,
  need_note="가닥으로 갈라 약 16 m. 제어 기판 점 대 점 배선 약 1.2 m × 7 + 센서 기판 버스 + W502 (data 추정)",
  where="리본을 한 가닥씩 갈라 센서 기판 버스·제어 기판 점 대 점 배선과 페달 잭 → 페달 보드 선(W502, 약 10 cm)에 씁니다.",
  check="i023과 같은 상품입니다. 3 m 한 토막으로 와도 됩니다.")
k("i101", cat="센서·MCU·기판", name="JST-XH 6핀 케이블 한 쌍 (Adafruit 4876)", unit="쌍", need=2,
  need_note="EL ↔ O1 (X401/X402) + ER ↔ O7 (X411/X412) = 2쌍 (CAD C-XH 2 + EXT 2)",
  where="끝 부속 EL ↔ 모듈 O1, ER ↔ O7을 뒤 케이블 통로에서 잇는 6핀 짝입니다. 모듈 쪽 O1 약 160 mm(W403)·O7 약 150 mm(W413) — 제어 기판 J302 윗면에 납땜(A16) — , 끝 부속 쪽 약 50 mm로 잘라 씁니다.",
  check="플러그 선 1 + 소켓 선 1이 한 쌍인지, 6핀인지 봅니다. 선은 26 AWG입니다(설계 22 AWG, 신호선이라 충분).")
k("i029", cat="센서·MCU·기판", name="탄소피막 저항 1 kΩ 1/4 W", unit="개", need=4,
  need_note="R551 (페달 센서) + R501 (페달 보드) + R701·R702 (앰프 입력 필터) = 4 (bom.csv)",
  where="페달 센서 출력(R551), 페달 보드 입력(R501), J702 기판 앰프 입력 필터(R701·R702)에 1개씩 씁니다.",
  check="색띠 갈·검·빨·금을 봅니다.")
k("i031", cat="센서·MCU·기판", name="탄소피막 저항 100 kΩ 1/4 W", unit="개", need=5,
  need_note="제어 기판 R301 (O1·O7) 2 + R302 (O1) 1 + R303 (O1) 1 + 페달 보드 R502 1 = 5 (bom.csv)",
  where="O1 제어 기판 R301·R302·R303(A0·A#0·B0), O7 제어 기판 R301(C8), 페달 보드 R502 = 5개입니다. R301~R303은 끝 부속 EXT 입력을, R502는 페달 입력(PED_TIP)을 GND로 당깁니다.",
  check="색띠 갈·검·노·금을 봅니다.")
k("i032", cat="센서·MCU·기판", name="탄소피막 저항 100 Ω 1/4 W", unit="개", need=5,
  need_note="페달 보드 R503 = 100 Ω 5개 병렬 (20 Ω) (bom.csv)",
  where="페달 보드 R503 자리에 5개를 병렬로 묶어 20 Ω으로 씁니다. 모노 플러그를 잘못 꽂았을 때 전류를 막습니다.",
  check="색띠 갈·검·갈·금을 봅니다.")
k("i022", cat="센서·MCU·기판", name="USB-A → C 데이터 케이블 1 m (Coms NA993)", unit="개", need=2,
  need_note="모듈 O1·O2 = 2 (CAD 경로 1 m, W201·W202)",
  where="모듈 O1·O2의 RP2040-Zero를 USB 허브에 잇는 선입니다(W201·W202). 뒷바 밑 닫힌 통로(y212~241 × z0~27)를 지나 가운데 유닛 앞 공간에서 허브 포트 4·5로 올라갑니다.",
  check="모듈 쪽 C 몰드가 폭 12.5·두께 7.6·길이 25 mm 이하인지 단계 0 시험 19로 봅니다. 충전 전용 선은 안 됩니다(BOOTSEL을 누른 채 꽂아 RPI-RP2 드라이브가 뜨는지).")
k("i226", cat="센서·MCU·기판", name="USB-A → C 데이터 케이블 50 cm (Coms HB466)", unit="개", need=6,
  need_note="모듈 O3~O7 5 + 페달 보드 1 = 6 (CAD 경로 0.5 m × 4: O3·O4·O7·PED, 0.3 m × 2: O5·O6)",
  where="모듈 O3~O7의 RP2040-Zero와 페달 보드를 USB 허브에 잇는 선입니다(W203~W208). 모듈 선은 뒷바 밑 닫힌 통로를 지나 허브 포트로 올라가고, 페달 보드 선은 앞 공간 줄(y227 z37)을 따라갑니다. O5·O6는 CAD 0.3 m 자리라 남는 약 20 cm를 통로에서 끈·벨크로로 묶습니다.",
  check="모듈 쪽 C 몰드가 폭 12.5·두께 7.6·길이 25 mm 이하인지 단계 0 시험 19로 봅니다(HB466 몰드 크기는 공개되지 않았습니다). 충전 전용 선은 안 됩니다.")

k("i228", cat="센서·MCU·기판", name="양면 만능기판 8 × 12 cm 2.54 mm (Voltly VLT-PCB009)", unit="장", need=4,
  need_note="A16 (10/31): 제어 기판 MB 7장 − 가진 BE163 4장(u06) = 3장 + 페달 보드 PED 70 × 50 조각 1장 = 4장 (CAD O1~O7-E-MB 80 × 120 + CU-E-PEDBOARD)",
  where="제어 기판 MB 3장은 자르지 않고 통째로 모듈 바닥틀 자리(x22.25~142.25 × y93.3~173.3, 받침 리브 위)에 눕히고, 따로 출력한 밸런스 레일이 판의 빈 띠(y132.3~144.5)를 위에서 눌러 잡습니다. 나사·구멍이 없습니다. 1장은 지그 P-PED로 70 × 50을 잘라 페달 보드로 쓰고, 남는 반쪽은 예비입니다.",
  check="크기 80 × 120인지, 구멍 수(30 × 42 또는 28 × 40)와 두께(약 1.6)를 잽니다. 부품은 판 가운데 기준 격자에서 가장자리 한 줄을 비우므로 28 × 40이어도 같은 자리에 들어갑니다.")

# ---- 제어·전원 -----------------------------------------------------------------------------
k("i001", cat="제어·전원", name="라즈베리파이 5 (2GB)", unit="개", need=1,
  need_note="1대 (CAD CU-E-PI5와 포트 4곳)",
  where="가운데 유닛 E칸(x540~668)의 출력 받침 기둥 4개에 M2.5×6(i050) 4개로 고정합니다. 전원은 강압 모듈 5.1 V에서 측면 꺾임 선(i021)으로 USB-C에 받고, GPIO 2·6번은 터치스크린 전원으로만 씁니다. FluidSynth로 소리를 만듭니다.",
  check="2GB 이상 모델인지 봅니다. EEPROM PSU_MAX_CURRENT=5000과 config.txt usb_max_current_enable=1을 넣고 vcgencmd get_throttled로 저전압을 확인합니다. GPIO 5 V 핀으로 전원을 넣지 않습니다.")
k("i080", cat="제어·전원", name="Pi 5 방열판 (알루미늄 4조각)", unit="세트", need=1,
  need_note="SoC·메모리·RP1·이더넷 칩 4조각",
  where="Pi 5의 SoC·메모리·RP1·이더넷 칩에 한 조각씩 붙입니다. 가운데 유닛 아랫판 Pi 아래에는 흡기 구멍 Ø8 28개가 있습니다.",
  check="4조각인지 봅니다.")
k("i092", cat="제어·전원", name="microSD 32GB", unit="개", need=1, role="부품",
  need_note="1장",
  where="Raspberry Pi OS Lite, FluidSynth, Salamander 피아노 음원을 담아 Pi 5 뒷면 슬롯에 꽂습니다.",
  check="32GB 이상인지 봅니다.")
k("i003", cat="제어·전원", name="XL4016 강압 모듈 XH-M401", unit="개", need=1,
  need_note="1개 (CAD CU-E-BUCK, SCH-06 A602)",
  where="가운데 유닛 D칸(x475.5~540)의 5 mm 받침 기둥에 M3×6(i059) 4개로 고정합니다. +12V8 버스를 받아 5.1 V를 만들어 Pi 5와 USB 허브에 줍니다. IN− 단자가 별 접지점입니다.",
  check="Pi를 꽂기 전에 부하 없이 5.10~5.15 V로 맞추고 가변저항을 고정합니다. IN−와 OUT−가 0 Ω으로 이어져 있는지 잽니다. 크기 60.8 × 40.3 × 29인지 봅니다.")
k("i093", cat="제어·전원", name="NEXTU 710U3 10포트 전원형 USB 허브", unit="개", need=1,
  need_note="1개 (CAD PB-E-HUB). 딸린 DC 어댑터 선을 잘라 전원선으로 씀 (W604)",
  where="가운데 유닛 F칸 바닥에 뒤판에 붙여 놓고(포트는 앞 −y), 위에 앰프 선반을 얹습니다. 다운스트림 포트 2~9에 페달 보드와 모듈 O1~O7을 꽂고, 업스트림은 NA977(i222)로 Pi 5에 잇습니다. 전원은 강압 5.1 V를 허브 −x 끝면의 DC 잭에 넣습니다.",
  check="DC 플러그 규격·극성을 재고, 곧은 플러그가 잭 면에서 37 mm 이하이고 바로 위로 꺾이는지 봅니다(2026-10-26 Pi를 9 mm 앞으로 옮김). 더 길면 같은 규격의 짧은 DC 플러그 선이 따로 필요합니다. 선을 꽂은 8개 포트 스위치를 켭니다.")
k("i021", cat="제어·전원", name="USB-A → C 측면 꺾임 20 cm (Coms BT663)", unit="개", need=1,
  need_note="5.1 V → Pi 5 전원선 1개 (W603, CAD C-PWR-5V의 Pi 쪽)",
  where="강압 모듈 5.1 V 출력 → Pi 5 USB-C 전원선입니다. A 쪽을 잘라 빨강·검정을 강압 출력 단자에 물리고, 꺾인 C 머리는 선이 −x(강압 쪽)로 나오게 꽂습니다.",
  check="꺾인 머리가 x 방향 14 mm보다 길지 않은지 잽니다(18 mm까지 들어감). 선을 자른 뒤 빨강 = +인지 멀티미터로 봅니다.")
k("i222", cat="제어·전원", name="USB-A(위 꺾임) → B 25 cm (Coms NA977)", unit="개", need=1,
  need_note="허브 업스트림 짧은 선 1개 (CAD C-USB-UPSTREAM, 길이 41 + 169 + 40 = 250)",
  where="Pi 5 GPIO 쪽 USB-A 2단의 아래 포트 → 허브 업스트림 B 포트를 잇습니다. 선은 허브 선반 위 z56.5에서 납작한 U자로 돌아 내려옵니다.",
  check="Pi 포트에 꽂아 A 머리가 '위로' 꺾이는지 봅니다(아래로 꺾이면 바닥에 닿아 못 씁니다).")
k("i224", cat="제어·전원", name="XT60 수 커넥터 + 16 AWG 선 10 cm", unit="개", need=3,
  need_note="배터리 하네스 X606 1 + 스피커 앰프 쪽 X703·X705 2 = 3 (CAD C-XT60 짝의 수, C-XT60M-L·R)",
  where=(f"① 배터리 하네스(W601): 배터리 XT60에 꽂는 수 1개입니다. 빨강·검정 리드를 XT60 몸통 뒤끝에서 {W601['lead']} mm로 자르고"
         f"(10 cm 선에서 {W601['cut_off']} mm를 잘라냄) 빨강은 퓨즈 홀더 −x 12 AWG 꼬리({W601['stub']} mm)와 {W601['ovl']} mm 꼬아 납땜합니다. "
         f"이은 뒤 홀더 −x 끝에서 XT60 뒤끝까지 {W601['max']} mm 이하(약 {W601['total']} mm)인지 자로 잽니다. "
         f"검정은 16 AWG 검정 연장(약 {W601['black_ext']} mm, i037)으로 이어 강압 IN−(별 접지점)까지 보냅니다. 빨간 수축 튜브를 씌웁니다. "
         "② 스피커 좌우(W703·W705): 앰프 스피커선 끝에 리드 10 cm 그대로 달고 파란 수축 튜브 + 'SPK'로 표시합니다."),
  check=(f"빨강 = +인지 납땜 전에 봅니다. W601은 이은 전체가 {W601['max']} mm를 넘으면 리드를 줄입니다. "
         f"더 길면 왼쪽 스피커 XT60 암(직선 {_fmt(W601['need_l'])} mm)까지 닿아 12.8 V를 스피커에 꽂을 수 있습니다. "
         "전원 XT60(빨강)과 스피커 XT60(파랑 + SPK)을 섞지 않습니다."))
k("i225", cat="제어·전원", name="XT60 암 커넥터 + 16 AWG 선 10 cm", unit="개", need=3,
  need_note="스피커 꼬리 X704·X706 2 + 12 V 시험 전원 어댑터 1 = 3 (CAD C-XT60F-L·R)",
  where="① 스피커 꼬리선 좌우: 유닛 단자에서 나온 선 끝에 달아 가운데 유닛 끝벽 안쪽 XT60 집게 홈에 끼웁니다(파랑 + SPK). ② 시험용: 12 V SMPS 출력에 달아 배터리 대신 하네스에 꽂습니다(빨강).",
  check="어댑터 쪽은 SMPS의 + 극성을 먼저 잽니다. 배터리와 시험 전원을 함께 꽂지 않습니다.")

# ---- 오디오 --------------------------------------------------------------------------------
k("i009", cat="오디오", name="HW-720 앰프 보드 (가진 것, XH-A232 대신)", unit="개", need=1,
  need_note="1개 (CAD CU-E-AMP, SCH-07 A702) - 2026-10-01 사용자가 가진 HW-720으로 바꿈",
  where="가운데 유닛 F칸 허브 위 선반의 3 mm 받침 4개(구멍 간격 59 × 46)에 M3×6(i059)으로 고정합니다(선반 앞에 혀가 있음). +12V8 버스(10.0~14.6 V) 두 가닥을 보드 밑에서 DC 잭 핀에 납땜하고, J702 기판의 저음 차단 RC(약 93 Hz)를 거친 신호를 XH 3핀 입력(INR·GND·INL)으로 받아, 왼쪽 끝 파란 나사 단자 2개(뒤 L, 앞 R)로 좌우 스피커를 울립니다(12.8 V에서 채널당 약 8 W). 볼륨 노브는 빼서 보관합니다(꽂으면 뚜껑에 닿음).",
  check="구멍 간격 59 × 46(사진 추정)과 볼륨 몸통 높이(판 위 약 11.4)를 재 보고, 보드 밑 핀이 3 mm보다 길면 자릅니다. DC 잭 가운데 핀이 +인지 잽니다. 음량은 노브를 꽂아 낮게 시작해 맞춘 뒤 노브를 뺍니다.")
k("i010", cat="오디오", name="1 µF 적층 세라믹 콘덴서 50 V", unit="개", need=4,
  need_note="C701~C704 = 4 (bom.csv)",
  where="J702 기판의 앰프 입력 저음 차단 필터(C701~C704)입니다. 채널마다 2개를 나란히(병렬) 납땜해 2 µF로 만들고 신호에 직렬로 넣습니다. 1 kΩ(R701·R702, i029)는 앰프 입력과 GND 사이에 답니다.",
  check="몸통 표시 '105'를 봅니다.")
k("i033", cat="오디오", name="PJ-313 3.5 mm 스테레오 잭", unit="개", need=3,
  need_note="J701 헤드폰 + J702 앰프 입력 + J501 페달 = 3 (CAD EL-E-J701·CU-E-J702·CU-E-J501)",
  where="왼쪽 끝 부속 볼 앞면의 헤드폰 잭(J701), 가운데 유닛 D칸 J702 기판의 앰프 입력 잭, 뒤판 출력물의 페달 잭(J501)입니다.",
  check="5핀(T·TN·R·RN·S) 스루홀형인지 봅니다.")
k("i111", cat="오디오", name="Apple USB-C → 3.5 mm 헤드폰 어댑터", unit="개", need=1,
  need_note="1개 (CAD CU-E-DONGLE, SCH-07 A701)",
  where="젠더(i034)로 Pi 5에 바로 꽂는 USB 오디오 출력입니다. 3.5 mm 출력은 W701 선으로 왼쪽 볼 헤드폰 잭에 가고, 헤드폰을 빼면 노멀 접점으로 앰프 입력(J702)에 갑니다.",
  check="허브에 꽂지 않고 Pi에 바로 꽂습니다. 리눅스에서 48 kHz로 소리가 나는지 봅니다.")
k("i034", cat="오디오", name="USB-C(암) → USB-A(수) 일자 젠더", unit="개", need=1,
  need_note="1개 (CAD CU-E-GENDER, X701)",
  where="Pi 5의 RJ45 옆 USB-A 2단 아래 포트에 꽂고, 여기에 Apple 어댑터(i111)를 곧게 꽂습니다(허브 쪽으로). 어댑터 선은 머리 바로 뒤에서 바닥으로 내려 젠더 밑을 지나 3.5 mm 소켓으로 갑니다. 2026-10-26부터 ㄱ자 대신 일자 - 허브 DC는 ㄱ자 플러그여야 합니다.",
  check="포트 밖으로 나오는 길이가 26 mm 이하인지 잽니다(CAD 14 mm로 모델). 몸통이 위·옆 포트를 가리지 않는지 봅니다.")
k("i038", cat="오디오", name="3.5 mm 스테레오 AUX 선 3 m (반으로 잘라 2가닥)", unit="개", need=1,
  need_note=(f"1.5 m 두 가닥: W701 {AUX['w701'] / 1000:g} m + W702 {AUX['w702'] / 1000:g} m + "
             f"W707 약 {AUX['w707'] / 1000:g} m (W701을 자른 나머지 {AUX['left'] / 1000:g} m에서) (cables.csv)"),
  where=(f"가운데에서 잘라 플러그가 하나씩 달린 1.5 m 두 가닥으로 씁니다. ① W701: 플러그를 동글(i111)에 꽂고 잘린 끝을 왼쪽 볼 헤드폰 잭 J701에 "
         f"납땜합니다. 잘린 쪽에서 {AUX['left'] / 1000:g} m를 잘라 {AUX['w701'] / 1000:g} m로 맞춥니다. "
         f"② W702: 잘린 끝을 J701 노멀 접점(TN·RN)에 납땜하고 플러그를 J702 앰프 입력 잭에 꽂습니다({AUX['w702'] / 1000:g} m 그대로, 남는 선은 통로에서 묶음). "
         f"③ W707: ①에서 잘라낸 {AUX['left'] / 1000:g} m에서 약 {_fmt(AUX['w707'])} mm를 잘라 J702 기판 → 앰프 입력(L·G·R)을 잇습니다."),
  check="3극(TRS) 선인지 봅니다. W707은 앰프 입력 단자(P1) 자리를 받은 보드로 보고 길이를 맞춥니다.")
k("i051", cat="오디오", name="삼미 CW-100B25 4인치 스피커 8 Ω", unit="개", need=2,
  need_note="좌우 2개 (CAD SPK-L·R, SCH-07 LS701·LS702)",
  where="좌우 스피커 파트의 출력 앞판(수평에서 40°)에 EVA 가스켓 3T를 끼우고 M4×12(i212) 4개씩으로 앞판 인서트에 고정합니다. 유닛 중심은 x160.5 / 1061.5, y260, z100.45입니다.",
  check="컷아웃 약 Ø94, 장착 구멍 PCD 115, 깊이 57 + 플랜지 4인지 잽니다. +/− 단자를 확인합니다.")
k("i052", cat="오디오", name="폴리에스터 방울솜 1 kg (흡음솜)", unit="봉", need=1,
  need_note="스피커 상자마다 약 35 g (CAD README W1 조건), 두 상자 약 70 g",
  where="스피커 상자 안에 전체로 느슨하게 넣는 흡음재입니다. 앞판 Ø94 구멍으로 넣고, 유닛 뒤 10 mm와 자석 뒤 폴 벤트 축 10 mm는 비웁니다.",
  check="재생솜이 아닌 폴리에스터 솜인지 봅니다.")
_C13 = c13_lengths()
k("i037", cat="오디오", name="스피커선 16 AWG 2심 (7 m 롤)", unit="m", need=_C13["need_m"],
  need_note=_C13["note"],
  where=("앰프 → 스피커 XT60 수까지 좌우 선(W703·W705), 스피커 상자 안 유닛 → XT60 암 꼬리선(W704·W706), "
         "퓨즈 홀더 → 스위치 → 강압·앰프 12.8 V 선(W602a~c·j), 배터리 하네스 검정 연장(W601 → 강압 IN−)에 잘라 씁니다. "
         "한 가닥씩 쓰는 곳은 2심을 갈라 씁니다. 스피커선은 쌍마다 꼽니다."),
  check="16 AWG 2심인지 봅니다. CAD 이름은 18 AWG로 적혀 있지만 회로 선 목록대로 16 AWG를 씁니다.")

# ---- 터치스크린 ----------------------------------------------------------------------------
k("i202", cat="터치스크린", name="Waveshare 7-DSI-TOUCH-C 7인치 터치스크린", unit="대", need=1,
  need_note="1대 (CAD TS-E-SCREEN, 접은 상태 TS-E-SCREEN-FOLD)",
  where="가운데 화면 뚜껑(x501.5~720.5) 위 받침에 25°로 세우고 운반할 때 뒤로 접습니다. Pi 5 CAM/DISP 1에서 22핀 리본(i203)으로 화면을 받고, 전원은 GPIO 2·6번에서 점퍼 2단과 동봉 3핀 선으로 받습니다. 뒷면 M2.5 구멍 4곳(154 × 88)을 받침에 고정합니다.",
  check="외곽 166.10 × 101.00 × 8.0, 뒷면 구멍 154 × 88을 잽니다. config.txt에 dtoverlay=vc4-kms-dsi-waveshare-panel-v2,7_0_inch_c를 넣고 1024 × 600 가로 화면이 나오는지 봅니다. 화면 받침(07)은 실물로 커넥터 방향을 본 뒤 뽑습니다.")
k("i203", cat="터치스크린", name="22핀 FFC 리본 300 mm B형 (GUOCONN)", unit="개", need=1,
  need_note="1가닥 (CAD TS-C-DSI, 경로 254 mm, W605)",
  where="Pi 5 CAM/DISP 1 ↔ 화면 22핀 커넥터를 잇습니다. 화면 뚜껑의 22 × 6 구멍을 지나 받침 안에서 45°로 두 번 접힙니다. 동봉 200 mm 리본은 책상 시험에만 씁니다.",
  check="양 끝 접점이 반대 면(B형)인지 봅니다.")
k("i204", cat="터치스크린", name="22핀 FFC 리본 300 mm A형 (보험)", unit="개", need=1, optional=True,
  need_note="B형이 맞지 않을 때만 1가닥",
  where="리본을 접은 뒤 접점 면이 B형과 반대로 필요할 때만 대신 씁니다.",
  check="양 끝 접점이 같은 면(A형)인지 봅니다.")
k("i205", cat="터치스크린", name="실리콘 점퍼선 20 cm F/F 빨강", unit="개", need=1,
  need_note="화면 5 V 1단 (W606, P603)",
  where="Pi GPIO 2번(5 V)에 꽂고 다른 끝에 M/M 빨강(i207)을 잇는 화면 5 V 선 1단입니다.",
  check="26 AWG 실리콘, 양끝 암인지 봅니다.")
k("i206", cat="터치스크린", name="실리콘 점퍼선 20 cm F/F 검정", unit="개", need=1,
  need_note="화면 GND 1단 (W606)",
  where="Pi GPIO 6번(GND)에 꽂고 다른 끝에 M/M 검정(i208)을 잇습니다.",
  check="양끝 암인지 봅니다.")
k("i207", cat="터치스크린", name="실리콘 점퍼선 20 cm M/M 빨강", unit="개", need=1,
  need_note="화면 5 V 2단 (W607, X602)",
  where="F/F 빨강 끝과 화면 동봉 전원선의 2.54 3핀 하우징 1번을 잇습니다.",
  check="양끝 수인지 봅니다.")
k("i208", cat="터치스크린", name="실리콘 점퍼선 20 cm M/M 검정", unit="개", need=1,
  need_note="화면 GND 2단 (W607)",
  where="F/F 검정 끝과 화면 동봉 전원선의 3핀 하우징 3번을 잇습니다(가운데 2번은 빈 칸).",
  check="양끝 수인지 봅니다.")
k("i209", cat="터치스크린", name="M3 × 20 볼트", unit="개", need=7,
  need_note="화면 경첩 축 2 + 받침다리 축 1 + 방진 브래킷 BRK2 4 = 7 (CAD TS-M3X20 3 + BRK2 BOLT 4)",
  where="화면 받침 경첩 축 2개와 받침다리 축 1개를 PETG에 탭으로 넣고, 머리가 닿은 뒤 1/4바퀴 풀어 둡니다. 끝 부속 볼 뒤 방진 브래킷 BRK2를 그로밋·M4 와셔와 함께 볼 속 너트에 4개로 조입니다.",
  check="브래킷 4개는 십자 둥근머리여도 됩니다(뒤에서 드라이버로 조임). 길이 20 mm인지 봅니다.")

# ---- 본체·결합 -----------------------------------------------------------------------------
k("i096", cat="본체·결합", name="오꾸메 합판 400 × 1200 × 11.5", unit="장", need=1,
  need_note="L2 합판 10조각, 사각 재단 0.258 m² (CAD plywood 10개)",
  where="뒷바 합판 10조각을 이 한 장에서 받습니다: 스피커 바깥 옆판 128.5 × 139.65 ×2, 뒤판 250 × 139.65 ×2, 윗판 250 × 14.14 ×2, 아랫판 250 × 90 ×2, 가운데 뒤판 702 × 56.35, 가운데 아랫판 679 × 90. 뚜껑·끝벽·스피커 안쪽 옆판은 출력합니다.",
  check="조각 크기와 두께 11.5를 잽니다. 가게가 배치대로 자르지 못했으면 바로 알립니다.")
k("i039", cat="본체·결합", name="피스고무발 28 × 5 (화성고무 RUB-E2)", unit="개", need=14, pack=1,
  need_note="스피커 아랫판 4 × 2 + 가운데 아랫판 6 = 14 (CAD FOOT 14개). 20개 봉",
  where="뒷바 밑에 달아 뒷바를 5 mm 띄웁니다. 발은 모두 통로 뒤(y ≥ 248)에 있어 모듈 USB 선이 뒷바 밑 통로로 지나갑니다. 8호 13 mm 직결피스(i053)와 M4 와셔(i060)로 답니다.",
  check="높이를 잽니다. CAD는 5 mm로 그렸고, 다르면 뚜껑이 건반 윗면과 어긋나 얇은 받침으로 맞춥니다.")
k("i053", cat="본체·결합", name="스텐 직결피스 8호 13 mm (둥근머리)", unit="개", need=14,
  need_note="고무발 14 (CAD README '모델에 넣지 않은 것')",
  where="고무발 14개를 스피커 아랫판(4 × 2)과 가운데 아랫판(6)에 답니다. 스피커 아랫판은 밀폐 상자 바닥이라 구멍마다 MS 폴리머를 한 방울 넣습니다.",
  check="13 mm인지 봅니다. 16 mm 이상은 스피커 상자 바닥을 뚫으니 쓰지 않습니다.")
k("i055", cat="본체·결합", name="스텐 직결피스 8호 19 mm (둥근머리)", unit="개", need=8,
  need_note="그릴 4 × 2 = 8 (CAD README)",
  where="출력 그릴을 스페이서 링과 함께 스피커 앞판 파일럿 구멍(Ø3.4 × 9)에 그릴마다 4개로 고정합니다.",
  check="19 mm인지 봅니다. 25 mm는 앞판 밑 밀폐면을 뚫습니다.")
k("i219", cat="본체·결합", name="접시머리 직결피스 8호 13 mm (철 백색 아연)", unit="개", need=6,
  need_note="배터리 틀 귀 2 + 배터리 틀 받침 구멍 2 + 뒤판 출력물 바닥 탭 2 = 6 (CAD README)",
  where="가운데 유닛 아랫판 윗면에 배터리 틀(출력물) 4곳과 뒤판 출력물 바닥 탭 2곳을 조입니다. 출력물의 접시 구멍을 대고 바로 조입니다.",
  check="접시머리 13 mm인지 봅니다(둥근머리 i053과 섞지 않습니다).")
k("i220", cat="본체·결합", name="스텐 트러스 태핑 피스 M3 × 12", unit="개", need=2,
  need_note="허브 선반 받침 2 (CAD README)",
  where="허브 위 앰프 선반의 받침 2개를 가운데 뒤판 안쪽 면(왼쪽 끝에서 433·647, 아래에서 41)에 고정합니다. 드라이버는 선반 윗면의 머리 길 홈을 따라 앞에서 넣습니다.",
  check="트러스 머리(약 Ø6)가 받침의 머리 자리 Ø6.5에 들어가는지 봅니다.")
k("i050", cat="본체·결합", name="스텐 렌치볼트 M2.5 × 6 (50개 봉)", unit="개", need=8, pack=1,
  need_note="Pi 5 4 + 터치스크린 4 = 8 (CAD TS-M25 4개, Pi 나사는 모델에 없음). 50개 봉",
  where="Pi 5를 E칸 받침 기둥 4개(구멍 Ø2.2 × 5)에 고정하고, 터치스크린 뒷면 네 귀 M2.5 구멍을 받침 뒤판에 고정합니다.",
  check="화면 뒷면 구멍 깊이를 먼저 재서 6 mm가 화면 뒤를 누르지 않는지 봅니다.")
k("i058", cat="본체·결합", name="M3 × 10 볼트", unit="개", need=22,
  need_note="센서 바·기판 (모듈 7 × 2 + 끝 부속 2 × 2) 18 + 화면 뚜껑 4 = 22 (CAD SBSCREW 18 + CU-M3X10 4)",
  where="센서 바와 센서 기판을 왼쪽 받침 기둥에 고정합니다(출력 구멍에 자가 탭). 화면 뚜껑은 이음 레일의 M3 인서트에 4개(앞 y246 2, 뒤 y322 2)로 고정합니다.",
  check="센서 바 나사는 버튼헤드(머리 1.65)를 씁니다. 캡볼트면 눌린 C·A0·C8 건반 밑과 틈이 0.48 mm뿐입니다.")
k("i059", cat="본체·결합", name="M3 × 6 볼트", unit="개", need=26,
  need_note="모듈 밸런스 레일 7 × 2 = 14 + 앰프 4 + 강압 4 + J702 기판 2 + 페달 보드 2 = 26 (CAD RAILSCREW 14, 나머지 12는 CAD README 보드 나사 표; A16 전에는 제어 기판 나사 14)",
  where="모듈마다 따로 출력한 밸런스 레일 양 끝의 깊은 구멍(Ø6.2)에 2개씩 넣어 바닥틀 받침에 자가 탭으로 조이고(A16), 가운데 유닛의 앰프(선반 받침)·강압 모듈·J702 기판·페달 보드를 5 mm 받침 기둥에 자가 탭으로 조입니다.",
  check="6 mm인지 봅니다. M3×8 이상은 받침 기둥 밑 아랫판에 닿아 기둥을 밀어 올립니다.")
k("i060", cat="본체·결합", name="M4 평와셔 (외경 9 × 0.5T)", unit="개", need=18,
  need_note="고무발 14 + 방진 브래킷 4 = 18 (CAD README)",
  where="고무발 직결피스 14개의 머리 밑, 방진 브래킷 M3×20 4개의 그로밋 위에 1개씩 넣습니다.",
  check="외경 9 mm 안팎인지 봅니다.")
k("i211", cat="본체·결합", name="M4 황동 열압입 인서트", unit="개", need=12,
  need_note="스피커 앞판 4 × 2 = 8 (바깥 Ø6 × 4) + 스피커 안쪽 옆판 이음 2 × 2 = 4 (바깥 Ø6 × 6) = 12 (CAD SPK-INS 8 + JOIN-INS 4)",
  where="스피커 출력 앞판의 유닛 나사 자리 PCD 115에 4개씩, 스피커 안쪽 옆판(출력)의 손잡이볼트 자리에 2개씩 인두로 넣습니다. 구멍은 Ø5.6 × 6.5 막힘이고 인서트는 면까지만 넣습니다.",
  check="앞판용 8개는 길이 4, 이음용 4개는 길이 6인지 봅니다. 이음 구멍 뒤에 PETG 5 mm가 남아야 밀폐됩니다.")
k("i212", cat="본체·결합", name="스텐 렌치볼트 M4 × 12", unit="개", need=8,
  need_note="스피커 유닛 4 × 2 = 8 (CAD README)",
  where="스피커 유닛을 출력 앞판의 M4 인서트에 고정합니다. 플랜지 4 + 가스켓 3을 지나 인서트에 물립니다.",
  check="12 mm인지 봅니다. 14 mm 이상은 앞판 밑 밀폐면을 뚫습니다. 3 mm 육각 렌치가 필요합니다.")
k("i213", cat="본체·결합", name="M3 황동 열압입 인서트 (바깥 Ø5 × 4)", unit="개", need=4,
  need_note="화면 뚜껑 이음 레일 4 (CAD SEAM-INS 4개)",
  where="화면 뚜껑 이음 레일 2개 윗면(y246·y322)의 Ø4.2 × 4.5 구멍에 인두로 넣습니다. 레일을 붙이기 전에 넣습니다.",
  check="길이가 4가 아니면 자리파기 깊이 = 11.5 − (10 − 물림)으로 다시 계산합니다.")
k("i214", cat="본체·결합", name="평로렛 손잡이볼트 M4 × 20 (5개 봉)", unit="개", need=4, pack=5,
  need_note="스피커 ↔ 가운데 이음 2 × 2 = 4 (CAD JOIN-TS 4개). 5개 봉, 1개 예비",
  where="가운데 유닛 안에서 끝벽의 고무 슬리브(i216)를 지나 스피커 안쪽 옆판의 M4 인서트에 물려 스피커 파트를 잇습니다(앞 y227, 뒤 y315). 손으로 돌려 공구 없이 뗍니다.",
  check="M4 × 20, 머리 Ø8 × 6인지 봅니다. M4×22보다 긴 볼트는 구멍 바닥을 누릅니다.")
k("i216", cat="본체·결합", name="연료 호스 OD8 × ID4.5 (52 mm)", unit="가닥", need=1,
  need_note="13 mm 슬리브 4개 = 52 mm (CAD JOIN-SLV 4개). 연료 호스 한 가닥에서 자릅니다",
  where="13 mm로 4개를 잘라 가운데 유닛 끝벽(출력)의 Ø8 구멍에 끼웁니다. 손잡이볼트가 이 슬리브 안을 지나 쇠가 출력물에 닿지 않습니다.",
  check="바깥 8 mm가 끝벽 Ø8 구멍에 꽉 끼고 M4 볼트가 안을 지나는지 봅니다. 바깥 8 mm 튜브면 실리콘 튜브(ID4 × OD8) 등 다른 튜브도 됩니다.")
k("i112", cat="본체·결합", name="M3 방진 댐퍼(그로밋) 20개", unit="개", need=4, pack=20,
  need_note="방진 브래킷 BRK2 2 × 2 = 4 (CAD BRK2 GROM 4개). 20개 세트",
  where="왼쪽·오른쪽 끝 부속 볼 뒷면의 방진 브래킷 BRK2에 2개씩 끼우고 M3×20(i209)과 M4 와셔로 조입니다. 스피커는 이 브래킷 핀에 얹힙니다.",
  check="지름 6, 높이 8.6, 허리 홈 1.6인지 봅니다.")
k("i099", cat="본체·결합", name="네오디뮴 자석 Ø8 × 3 (12개)", unit="개", need=12, pack=12,
  need_note="뚜껑 L·R 밑면 3 × 2 + 받침 쪽 (뒤판 윗모서리 2 + 끝벽 윗모서리 1) × 2 = 12 (CAD CU-MAG 12개)",
  where="가운데 유닛 출력 뚜껑 L·R 밑면 3곳과 그 아래 뒤판 윗모서리 2곳·끝벽 윗모서리 1곳에 극이 서로 당기게 순간접착제로 붙입니다. 뒤판 자리(Ø8 × 3.2)는 지그 J-b로 뚫습니다.",
  check="12개인지 세고, 붙이기 전에 짝끼리 당기는 면을 표시합니다. 붙는 힘이 약하면 N35로 바꿉니다.")
k("i061", cat="본체·결합", name="EVA 고밀도 폼 3T 330 × 490 (검정)", unit="장", need=3,
  need_note="모듈 바닥 7 + 끝 부속 2 + 스피커 가스켓 2 + 이음 띠 4 (CAD EVA 9 + GASKET 2 + JOIN-EVA 4)",
  where="모듈 7개·끝 부속 2개 밑면 바닥 층(모듈 163.5 × 211, 제어 기판 자리 오려 냄), 스피커 유닛 가스켓 2개(안 Ø94, 바깥 105 × 105), 가운데 ↔ 스피커 이음 띠 4개를 자릅니다.",
  check="두께 3 mm인지 잽니다. 접착면이 없어 종이 양면테이프(i040)로 붙입니다.")
k("i221", cat="본체·결합", name="벨크로 링벨트 20 mm × 30 cm", unit="개", need=1,
  need_note="배터리 고정 1 (둘레 약 230 mm)",
  where="배터리를 배터리 틀 앞·뒤 벽 아래의 끈 구멍(22 × 3, x304~326)으로 밑과 위를 감아 묶습니다.",
  check="폭 20 mm 이하인지 봅니다(끈 구멍 22).")

# ---- 3D 출력 재료 --------------------------------------------------------------------------
k("i087", cat="3D 출력 재료", name="Bambu PETG Basic 흰색 1 kg (스풀)", unit="개", need=1,
  need_note="흰색 출력물 52개 = 속 꽉 채움 1.17 kg (manifest, 실제 채움으로 뽑으면 더 적음) — i088과 합쳐 2 kg",
  where="흰 건반 등 흰색 출력물에 씁니다.",
  check="1.75 mm PETG인지 봅니다. 출력 전에 건조합니다.")
k("i088", cat="3D 출력 재료", name="Bambu PETG Basic 흰색 1 kg (리필)", unit="개", need=1,
  need_note="흰색 2 kg 중 1 kg",
  where="i087의 빈 스풀에 끼워 흰색 출력물을 이어 뽑습니다.",
  check="리필(스풀 없음)이라 Bambu 재사용 스풀이 있어야 합니다.")
k("i089", cat="3D 출력 재료", name="Bambu PETG Basic 검정 1 kg × 5", unit="개", need=5,
  need_note="검정·회색·색 무관 출력물 242개 = 속 꽉 채움 7.48 kg + 공구·지그 0.33 kg (manifest) — 실제 채움 25~40 %로 뽑으면 훨씬 적음",
  where="프레임·레버 캐리어·센서 바·뒷바 출력물 등 흰색이 아닌 출력물에 씁니다. CAD에 '회색'으로 적힌 부품도 검정으로 뽑아도 됩니다(색만 다름).",
  check="5개인지 봅니다.")
k("i227", cat="3D 출력 재료", name="Bambu PETG Basic 검정 1 kg 스풀 × 4 (판 출력 추가분)", unit="개", need=4,
  need_note="10/16 A안: 검정 몫 약 9.1 kg(건반 액션 약 5.1 + 뒷바 나머지 약 1.5 + 새 판 10장 약 2.0 + 공구·시험 키트·기판 지그 약 0.5) − 가진 6.5 kg(검정 5 + 추가 1 + 흰색 남는 약 0.5) ≈ 2.6 kg + 여유 약 1.4 kg",
  where="합판 대신 출력하는 뒷바 판 10장(스피커 바깥 옆판·뒤판·윗판·아랫판 L·R, 가운데 아랫판·뒤판 3토막씩, 약 2.0 kg · 49시간)과 그 때문에 모자라는 검정 출력물에 씁니다.",
  check="블랙(30105) 스풀 포함 4개인지 봅니다.")
k("i090", cat="3D 출력 재료", name="Bambu PETG Basic 1 kg 추가", unit="개", need=1,
  need_note="단계 0 시편·출력 공구·실패 재출력 몫",
  where="단계 0 시편, 출력 공구(06)·지그(08·09), 실패한 부품 재출력에 씁니다.",
  check="색(흰색·검정)을 봅니다.")

# ---- 소모품 --------------------------------------------------------------------------------
k("i071", cat="소모품", name="세메다인 슈퍼X 8008 흑색 20 mL (MS 폴리머)", unit="개", need=3, role="소모품",
  need_note="강철 블록 88 × 약 0.2 mL ≈ 18 mL + 출력물 이음·밀봉 약 12 mL + 10/16 A안 판끼리 이음 약 24,900 mm²·반턱 약 4,700 mm² (0.3~0.5 mm 막 → 약 9~15 mL) ≈ 39~45 mL → 20 mL 3개",
  where="레버 캐리어에 강철 블록 88개를 붙이고(24시간 굳힘), 스피커 상자의 출력 판 이음(10/16부터 판이 모두 출력이라 목공본드 대신)·앞판 둘레 밀봉, 가운데 아랫판·뒤판 반턱 3토막 잇기, 가운데 유닛 끝벽·받침 기둥·이음 레일·J501 기판·XT60 집게 붙이기, 화면 받침 유리 턱 띠 2조각 붙이기(10/30 A14), 고무발 나사 구멍에 씁니다.",
  check="굳기 전 튜브 끝을 막아 둡니다. 에폭시·순간접착제로 대신하지 않습니다.")
k("i057", cat="소모품", name="오공 205 목공본드 800 g", unit="통", need=1, role="소모품",
  need_note="합판 10조각 이음",
  where="스피커 상자(바깥 옆판·아랫판·뒤판·윗판)와 가운데 유닛(아랫판·뒤판)의 합판 이음을 붙입니다. 출력물이 닿는 이음은 MS 폴리머로 붙입니다.",
  check="205(흰색 수성 목공본드)인지 봅니다.")
k("i012", cat="소모품", name="순간접착제 5 g", unit="개", need=1, role="소모품",
  need_note="자석 Ø5 89 + Ø8 12 고정",
  where="건반 밑 자석 88개와 페달 자석 1개, 뚜껑 자석 12개를 포켓에 붙입니다.",
  check="굳지 않았는지 봅니다.")
k("i070", cat="소모품", name="흑연 가루 30 mL", unit="통", need=1, role="소모품",
  need_note="펠트 띠 88장에 얇게 (몇 g)",
  where="레버 88개 밑 캡스턴 펠트 띠의 캡스턴이 닿는 면에 붓으로 얇게 바르고 털어 냅니다.",
  check="브랜드 표기가 없어 미술용 흑연 가루인지 봅니다.")
k("i040", cat="소모품", name="종이 양면테이프 48 mm × 6 m", unit="롤", need=1, role="소모품",
  need_note="EVA 바닥 9장 + 허브",
  where="모듈 7개·끝 부속 2개 밑면에 EVA 3T 바닥 시트를 띠로 붙이고, 가운데 유닛 F칸 뒤판에 USB 허브를 붙입니다.",
  check="종이(얇은) 양면테이프인지 봅니다. 두꺼운 폼 테이프는 바닥 높이를 바꿉니다.")
k("i025", cat="소모품", name="열수축튜브 세트 (2:1)", unit="세트", need=1, role="소모품",
  need_note="리드 이음 8곳, 전원선 이음 2곳, XT60 표시 6개, 페달 납땜",
  where="끝 부속 리드 ↔ JST-XH 이음 8곳, 퓨즈 홀더 12 AWG ↔ 16 AWG 이음, 페달 센서 납땜을 덮습니다. XT60은 전원 = 빨강, 스피커 = 파랑 + 'SPK'로 구분해 씌웁니다.",
  check="빨강·파랑 튜브가 들어 있는지 봅니다(XT60 표시). 없으면 테이프로 색을 표시합니다.")
k("i026", cat="소모품", name="캡톤 테이프 10 mm", unit="롤", need=1, role="소모품",
  need_note="페달 보드 RP2040-Zero 밑 + 리본 누름 패드 (A16: 모듈 제로 7장은 몰드 헤더 위라 필요 없음, 붙여도 됨)",
  where="페달 보드 RP2040-Zero 밑(제로 밑면과 만능기판 사이 절연)과 화면 받침 안 리본 누름 패드 자리에 붙입니다. 모듈 제어 기판의 제로 7장은 몰드(2.5)가 그대로인 헤더 위라 밑면 부품이 판에서 1.2 떠 있습니다(A16).",
  check="폭 10 mm 안팎이면 됩니다.")
k("i027", cat="소모품", name="케이블 타이 100 mm", unit="봉", need=1, role="소모품",
  need_note="모듈 USB 선·EXT 리드·페달 선",
  where="모듈 USB 선과 O1·O7 EXT 리드를 모듈 뒷벽에 묶어 당김을 막고, 페달 안 3 m 선을 한 번 묶습니다. 통로 안 USB 선 묶음은 느슨하게 묶고 케이블 집게에는 끼우지 않습니다.",
  check="폭 2.5 mm 안팎이면 됩니다.")
k("i028", cat="소모품", name="유연납 0.8 mm", unit="롤", need=1, role="소모품",
  need_note="약 1,500점 (data 추정)",
  where="센서 기판 7, 제어 기판 7, 끝 부속 EL·ER, 페달 보드·센서, 잭 3, 전원·스피커 선의 손 납땜 전체에 씁니다.",
  check="플럭스 코어 실납인지 봅니다.")

# ---- 페달 ---------------------------------------------------------------------------------
k("i109", cat="페달", name="듀로 서스테인 페달 (스위치형 → 홀센서 개조)", unit="개", need=1,
  need_note="1개 (CAD PEDAL-DAMPER, 바닥)",
  where="책상 앞 바닥에 두는 댐퍼 페달입니다. 마이크로스위치 배선을 떼고 발판 밑에 자석 Ø5×2, 바닥판에 홀센서 조각(PS: DRV5055 + 100 nF + 1 kΩ)을 붙여 연속형으로 바꿉니다.",
  check="발판을 밟았을 때 자석–센서 간격이 약 4.5 mm, 뗐을 때 12 mm 이상 나오는지 봅니다.")
k("i013", cat="페달", name="3.5 mm 스테레오 AUX 선 3 m (페달)", unit="개", need=1,
  need_note="W501 1가닥",
  where="댐퍼 페달과 가운데 유닛 뒤판 출력물의 페달 잭(J501)을 잇습니다. 한쪽 플러그를 잘라 페달 안 센서에 납땜합니다(팁 = 출력, 링 = 3V3, 슬리브 = GND).",
  check="3극(TRS) 플러그인지 봅니다. 2극(모노)은 센서 전원이 없어 못 씁니다.")

# ---- 공구 (가진 것) -----------------------------------------------------------------------
TOOL_WHERE = {
    "i041": ("디지털 멀티미터", "강압 5.10 V 맞추기, 배터리 전압, XT60·DC 극성, 통전 확인에 씁니다."),
    "i042": ("정밀 와이어 스트리퍼", "AWG 20~30 선 피복을 벗깁니다. 16 AWG는 니퍼 날로 칼집을 내 벗깁니다."),
    "i043": ("5인치 니퍼", "핀 헤더·부품 다리·선을 자릅니다."),
    "i044": ("버니어 캘리퍼스", "강철 블록 두께, 봉 지름, 펠트·폼 두께, 받은 부품 치수를 잽니다."),
    "i045": ("쇠톱 (300 mm)", "강철 띠 88토막(40 mm)과 SUS 봉 18토막을 자릅니다."),
    "i046": ("바이메탈 쇠톱날 12인치", "강철 띠 자르기용 새 날입니다."),
    "i047": ("철공용 평줄", "강철 블록·봉 끝 버, 만능기판 가장자리를 다듬습니다."),
    "i048": ("탁상 바이스", "강철 띠·봉을 물려 자릅니다."),
    "i064": ("육각 렌치 2.5 mm", "M3 소켓 캡 볼트(M3×10·M3×6·M3×20)를 조입니다."),
    "i065": ("육각 렌치 2.0 mm", "캡스턴 버튼헤드 M3×6 88개 조정, M2.5×6, 화면 경첩 M3×20에 씁니다."),
    "i113": ("Pinecil V2 납땜 인두", "모든 손 납땜과 열압입 인서트(M4 12개, M3 4개) 넣기에 씁니다. 전원은 USB-C PD 충전기나 DC 12~24 V입니다."),
    "i114": ("인두 거치대", "Pinecil 거치대입니다."),
    "i115": ("실리콘 USB-C 케이블 1 m", "Pinecil 전원선입니다."),
    "i126": ("HSS 드릴 날 Ø4.0", "출력한 Ø3.9 봉 구멍(레버 허브 88, 핀 보스 35 등 약 130곳)을 Ø4.0으로 넓힙니다."),
    "i127": ("피아노선 니퍼", "토션 스프링 다리를 22.3 / 8.0으로 자릅니다."),
}
for tid, (nm, wh) in TOOL_WHERE.items():
    k(tid, cat="공구", name=nm, unit="개", need=1, role="공구", need_note="1", where=wh, check="")
K["i046"]["need_note"] = "1장 (2장 상품 중 1장분)"

# ---- New lines not in data.json (user-owned) ----------------------------------------------
NEW = [
    dict(id="u01", code="BT601", cat="제어·전원", source="owned", role="부품",
         name="LiFePO4 배터리 12.8 V 6 Ah", unit="개", need=1, need_note="1개 (CAD BAT-LFP, SCH-06 BT601)",
         full_name="LiFePO4 12.8 V 32700 4S1P 배터리 '12.8V 10Ah DCXT60-3A' (계산 6 Ah · 76.8 Wh), XT60 출력 선 + DC 5.5×2.1 충전 선, 3 A 충전기 세트",
         where="가운데 유닛 A칸(x271.5~426) 바닥의 배터리 틀(출력물) 안에 눕혀 넣고 벨크로 끈(i221)으로 묶습니다 - 끈은 아랫판의 끈 골로 배터리 밑을 지나갑니다. XT60 선은 버스 하네스(i224)에 꽂고, DC 충전 선과 함께 배터리 윗면에 눕혀 둡니다. 버스 12.8 V(10.0~14.6 V)로 약 3.5~4.4시간 씁니다.",
         specs=[["형식", "LiFePO4 4S1P (32700 셀), BMS 4S 40 A (상품 설명) — 받으면 확인"], ["전압", "공칭 12.8 V (10.0~14.6 V)"],
                ["용량", "표기 10 Ah, 계산 6 Ah · 76.8 Wh"], ["크기", "140 × 35 × 72 mm (눕혀 140 × 72 × 35)"], ["무게", "약 0.9 kg (상품 설명)"],
                ["출력", "XT60 선 (X605)"], ["충전 입력", "DC 5.5×2.1 선 (세트 충전기 3 A)"],
                ["구매", "쿠팡 9669099122 옵션 '04 12.8V 10Ah DCXT60-3A', 판매자 월드셀러샵몰 70,500원 (충전기 포함, 11/12 도착; 같은 상품 쿠쿠스토어4호는 44,400원·11/23)"]],
         ident="140 × 35 × 72 mm 팩에서 XT60 선과 DC 충전 선이 나옵니다.",
         check="무부하 전압이 약 13.0~13.4 V인지 잽니다(10 V 아래면 쓰지 않음). BMS 저전압 차단·연속 방전 한도를 확인합니다. 선이 나오는 면·높이(가정: +x 끝면 y275 / y299, z34), DC 커넥터 높이 8.85 이하, 선 길이(XT60 약 50, DC 약 45 mm)를 보고, 다르면 배터리 틀(05)을 뽑기 전에 고칩니다.",
         cad=[r"BAT-LFP", r"C-BAT-LEAD", r"C-BAT-DC", r"C-DC", r"C-XT60"], replaces=None),
    dict(id="u02", code="", cat="제어·전원", source="owned", role="부속",
         name="LiFePO4 충전기 3 A (배터리 세트)", unit="개", need=1, need_note="1개 (배터리 u01 세트에 포함)",
         full_name="배터리 세트에 든 LiFePO4 4S 충전기 3 A, DC 5.5×2.1 플러그",
         where="스위치를 끄고 뚜껑 L(자석)을 들어 배터리 윗면의 DC 5.5×2.1 충전 선에 꽂아 충전합니다. XT60은 뽑지 않습니다. 6 Ah를 약 2~2.5시간에 채웁니다. 충전기가 부하 동시 사용을 밝히지 않으면 충전하며 연주하지 않습니다.",
         specs=[["출력", "LiFePO4 4S 14.6 V (받으면 표기 확인), 3 A"], ["플러그", "DC 5.5×2.1 (배터리 충전 선과 같은지 확인)"],
                ["구매", "배터리 u01 세트에 포함 (따로 사지 않음)"]],
         ident="LiFePO4(4S, 14.6 V) 표시가 있는 충전기입니다.",
         check="출력 전압 표기가 14.4~14.6 V이고 플러그가 배터리 충전 선에 맞는지 봅니다. 납축·리튬이온용 충전기는 쓰지 않습니다.",
         cad=[], replaces=None),
    dict(id="u03", code="L59", cat="제어·전원", source="owned", role="부품",
         name="KCD1-104 로커 스위치 (4핀)", unit="개", need=1, need_note="1개 (CAD CU-E-SWITCH, SCH-06 SW601)",
         full_name="KCD1-104 로커 스위치 4핀 2회로 ON-OFF, 6 A 250 VAC",
         where="가운데 유닛 뒤판 출력물의 13.2 × 19.2 구멍에 끼웁니다. 두 회로를 나란히 묶어(입력 둘, 출력 둘을 짧은 선으로) 퓨즈 뒤 12.8 V를 앰프와 강압 모듈에 켜고 끕니다.",
         specs=[["형식", "4핀, 2회로 ON-OFF (두 회로 나란히)"], ["정격", "6 A 250 VAC (DC 정격 미공개)"],
                ["패널 구멍", "약 19 × 13 (CAD 뒤판 구멍 13.2 × 19.2)"], ["CAD 몸통", "13.2 × 19.2 × 16.2, 단자 4.8 × 0.8 4개 (가정)"]],
         ident="뒤에 단자 4개가 있는 사각 로커 스위치입니다.",
         check="몸통·테두리를 재서 뒤판 출력물 구멍(13.2 × 19.2)에 맞는지 출력 전에 봅니다. 소리를 멈추고 끕니다(DC 차단 정격 미공개).",
         cad=[r"CU-E-SWITCH"], replaces="i016"),
    dict(id="u04", code="L60", cat="제어·전원", source="owned", role="부품",
         name="ATC/ATO 인라인 퓨즈 홀더 (12 AWG)", unit="개", need=1, need_note="1개 (CAD CU-E-FUSE, SCH-06 F601-HLD)",
         full_name="ATC/ATO 칼날형 인라인 퓨즈 홀더, 덮개 끼움식, 12 AWG 선",
         where="배터리 틀 앞의 퓨즈 선반에 옆으로 눕혀(덮개 +y) 꼭지 Ø8 두 곳을 받침에 눌러 끼웁니다. 12 AWG 꼬리 두 가닥을 홀더 끝에서 약 24 mm 뒤에서 잘라 16 AWG와 납땜합니다: −x 꼬리 → 하네스 XT60 수, +x 꼬리 → 스위치.",
         specs=[["크기", "40.1 × 11.1 × 33.8 mm (선 꼭지·덮개 포함)"], ["선", "12 AWG 빨강"], ["퓨즈", "ATO/ATC 표준 칼날"],
                ["CAD 가정", "꼭지 Ø8, 칼날 쪽 끝에서 7.5 — 받은 홀더로 확인"]],
         ident="덮개가 끼워지는 검은 칼날형 퓨즈 홀더에 굵은 빨간 선이 양쪽으로 나옵니다.",
         check="크기 40.1 × 11.1 × 33.8과 꼭지 위치·지름(Ø8)을 잽니다. 받침(Ø8.3, 위 입구 6.8)에 눌러 끼워지는지, 덮개가 위로 약 20 빠지는지 봅니다. 12 AWG는 R15보다 좁게 꺾지 않습니다.",
         cad=[r"CU-E-FUSE", r"C-PWR-IN", r"C-PWR-FUSE"], replaces="i017"),
    dict(id="u05", code="L60", cat="제어·전원", source="owned", role="부품",
         name="ATO 칼날 퓨즈 5 A (주황)", unit="개", need=1, need_note="1개 (SCH-06 F601). 켤 때 끊기면 7.5 A(갈색)",
         full_name="ATO 표준 칼날 퓨즈 5 A, 32 V DC",
         where="퓨즈 홀더(u04) 안에 넣습니다. 배선이 합선되면 선이 타기 전에 끊습니다. 갈 때는 스위치를 끄고 뚜껑 L을 들어 홀더를 받침에서 빼 덮개를 엽니다.",
         specs=[["형식", "ATO/ATC 표준 칼날 (미니 ATM·맥시 아님)"], ["정격", "5 A, 32 V DC"], ["색", "주황"]],
         ident="주황색 표준 크기 칼날 퓨즈에 '5'가 적혀 있습니다.",
         check="표준 ATO 크기인지 봅니다. 홀더에 딸린 10~40 A 퓨즈는 쓰지 않습니다.",
         cad=[r"CU-E-FUSE"], replaces="i018"),
    dict(id="u06", code="", cat="센서·MCU·기판", source="owned", role="부품",
         name="Coms BE163 양면 만능기판 80 × 120", unit="장", need=4,
         need_note="A16 (10/31): 제어 기판 MB 7장을 80 × 120 통째로 씀 - 가진 4장 = MB 4장, 나머지 MB 3장 + 페달 보드 1장은 새로 사는 8 × 12 4장(i228) (CAD O1~O7-E-MB)",
         full_name="Coms BE163 양면 만능기판 8 × 12 cm (구멍 30 × 42, 2.54 mm)",
         where="제어 기판 MB 4장으로 자르지 않고 통째로 씁니다(A16). 모듈 바닥틀 자리(x22.25~142.25 × y93.3~173.3)의 받침 리브 위에 놓고, 따로 출력한 밸런스 레일이 판의 빈 띠(y132.3~144.5)를 위에서 눌러 잡습니다. 나사·구멍 뚫기가 없습니다.",
         specs=[["크기", "80 × 120 mm, 두께 약 1.6 (받은 판으로 잼)"], ["구멍", "30 × 42, 2.54 mm 간격, 양면"],
                ["쓰는 법", "통째로 (A16) - 레일 밑 띠 y132.3~144.5에는 부품·배선 없음"]],
         ident="80 × 120 양면 만능기판입니다.",
         check="4장 있는지, 두께가 1.6 안팎인지 봅니다.",
         cad=[r"O[1-4]-E-MB"], replaces="i082"),
    dict(id="u07", code="", cat="제어·전원", source="owned", role="시험용", optional=True,
         name="12 V 10 A SMPS (배선 시험용)", unit="개", need=1, need_note="책상 시험 때만 1개",
         full_name="12 V 10 A 스위칭 전원 장치",
         where="배선 시험 때만 배터리 대신 씁니다. 출력에 XT60 암(i225, 빨강)을 달아 하네스 XT60 수에 꽂습니다. 배터리와 함께 꽂지 않습니다.",
         specs=[["출력", "12 V, 10 A"]],
         ident="12 V 출력 단자가 있는 SMPS입니다.",
         check="출력 극성을 멀티미터로 재고 XT60 암을 답니다.",
         cad=[], replaces=None),
]

# Prep tools / small consumables (data.json 'prep' list, rewritten for the final design)
PREP = [
    dict(id="t01", name="전동 드릴 + 목공 Ø8 트위스트 날", role="공구",
         where="합판 Ø8 관통 50개(뒤판 앰프 뒤 10 — 지그 J-d3, 아랫판 강압·Pi 아래 40 — 지그 J-d4)와 뒤판 윗모서리 자석 자리 Ø8 × 3.2 4곳(지그 J-b, 깊이 J-e 게이지)을 뚫습니다.",
         need_note="드릴은 사용자 것 (CAD README '드릴은 54번')"),
    dict(id="t02", name="철공 드릴 날 Ø3.0 · Ø3.2", role="공구",
         where="페달 보드 조각 1장의 고정 구멍(나사 Ø3.2 × 2, 위치 핀 Ø3.0 × 2)을 기판 지그(09 P-PED)로 뚫습니다. 제어 기판 MB 7장은 통째로 써서 뚫지 않습니다(A16).",
         need_note="cad/jigs/README.md '기판 지그'"),
    dict(id="t03", name="육각 렌치 3 mm", role="공구",
         where="스피커 유닛 M4 × 12 소켓 캡 볼트 8개를 조입니다.", need_note="목록의 렌치는 2.0·2.5 mm뿐"),
    dict(id="t04", name="십자 드라이버 (곧은 Ø6 × 80) · 송곳", role="공구",
         where="직결피스·접시머리 피스·트러스 태핑 피스와 방진 브래킷 십자 볼트를 조입니다. 가운데 유닛 나사는 곧은 드라이버(Ø6 × 80)로 닿습니다. 송곳으로 합판에 자리를 냅니다.",
         need_note="CAD README 조립 순서 3"),
    dict(id="t05", name="커터칼 · 펜치", role="공구",
         where="기판 지그 P-PED를 대고 페달 보드 조각을 긋고 꺾습니다(제어 기판은 자르지 않음, A16). 펠트·폼·EVA도 자릅니다.",
         need_note="cad/jigs/README.md"),
    dict(id="t06", name="사포 #120 · 소독용 알코올", role="소모품",
         where="강철 블록과 레버 캐리어 접착면을 갈고 닦습니다.", need_note="DESIGN 10장 4단계"),
    dict(id="t07", name="마스킹테이프", role="소모품",
         where="목공본드로 붙인 합판을 굳는 동안 눌러 둡니다.", need_note=""),
    dict(id="t08", name="이쑤시개 Ø2", role="소모품",
         where="토션 스프링을 레버 허브에 밀어 넣을 때 씁니다.", need_note=""),
    dict(id="t09", name="복사지 (0.1 mm 종이 펀칭)", role="소모품",
         where="쉼 펠트 밑에 건반마다 2장씩 넣어 건반 앞 높이를 맞춥니다.", need_note="CAD RESTFELT 이름 '쉼 펠트 1.5T + 종이 펀칭'"),
    dict(id="t10", name="단계 0 측정 도구", role="공구",
         where="0.1 g 저울, 주방 저울 5 kg, 다이얼 게이지 0.01 mm, Ø19.05 강철 공, 240 fps 촬영 폰, M3 × 12 볼트 2개로 단계 0 시험을 합니다.",
         need_note="data.json prep"),
]

# Lines that are not needed in the final design (with the reason), or merged into another line.
DROPPED = {
    "i002": ("PD 트리거 HUSB238", "전원이 LiFePO4 배터리(u01)로 바뀌어 USB-C PD 입력이 없습니다(R33, 10/7).", None),
    "i016": ("KCD1-101A 로커 스위치", "사용자가 가진 KCD1-104(u03)를 씁니다. 뒤판 구멍은 같습니다.", "u03"),
    "i017": ("Coms BU914 퓨즈 홀더 (5×20)", "사용자가 가진 ATC/ATO 칼날형 홀더(u04)를 씁니다.", "u04"),
    "i018": ("5 A 지연형 퓨즈 5×20", "ATO 칼날 퓨즈 5 A(u05)를 씁니다.", "u05"),
    "i019": ("USB-C↔C 90° 꺾임 1 m (NC888)", "PD 입력이 없어져 쓰지 않습니다.", None),
    "i020": ("USB-C↔C PD 60 W 케이블 2 m", "PD 입력이 없어져 쓰지 않습니다. CAD·회로 어디에도 이 선이 없습니다.", None),
    "i030": ("탄소피막 저항 10 kΩ", "회로(bom.csv)에 10 kΩ 자리가 없습니다.", None),
    "i035": ("XT30U-M 수 커넥터", "스피커 이음이 XT60(i224)으로 바뀌었습니다(△18).", "i224"),
    "i036": ("XT30U-F 암 커넥터", "스피커 이음이 XT60(i225)으로 바뀌었습니다(△18).", "i225"),
    "i054": ("직결피스 8호 16 mm", "L2에서 스피커 유닛은 M4 인서트 + M4×12로 고정합니다. 16 mm 이상은 스피커 밀폐 바닥을 뚫습니다.", None),
    "i056": ("직결피스 8호 25 mm", "L2에서 쓰는 곳이 없습니다(고무발 13 mm, 그릴 19 mm).", None),
    "i068": ("0.5T 부싱 천 (0원 줄)", "i062와 같은 물건입니다.", "i062"),
    "i082": ("만능기판 5 × 7 cm", "사용자가 가진 Coms BE163(u06)을 잘라 씁니다.", "u06"),
    "i094": ("65 W PD 충전기", "PD 입력이 없어져 피아노에는 쓰지 않습니다.", None),
    "i097": ("오꾸메 합판 600 × 1200", "2026-10-16부터 합판을 쓰지 않습니다(뒷바 판을 모두 PETG로 출력, A안).", None),
    "i096": ("오꾸메 합판 400 × 1200 × 11.5", "2026-10-16 A안: 뒷바 판 10조각을 모두 PETG로 출력합니다(가운데 아랫판·뒤판은 반턱 3토막). 사기 전에 뺐습니다.", None),
    "i057": ("오공 205 목공본드 800 g", "2026-10-16 A안: 판이 모두 PETG라 목공본드가 붙지 않아 이음을 MS 폴리머(i071)로 붙입니다. 사기 전에 뺐습니다.", "i071"),
    "i103": ("토글 래치 매미고리", "L2 한 몸 뒷바에서 도브테일 블록과 함께 없어졌습니다.", None),
    "i105": ("양모 펠트 3T", "r4.5 설계에서 쓰는 곳이 없습니다.", None),
    "i215": ("Norelem 나사산 인서트 M4", "스피커 안쪽 옆판을 출력하면서 M4 열압입 인서트(i211)로 바뀌었습니다(10/7).", "i211"),
    "i217": ("M3 × 16 볼트 (방진 브래킷)", "방진 브래킷 볼트가 M3 × 20(i209)으로 바뀌었습니다(10/7, 볼 구멍을 y199까지 늘림).", "i209"),
    "i218": ("M3 × 5 볼트 (가운데 유닛 보드)", "보드 받침 기둥 구멍을 관통 5로 바꾸고 M3 × 6(i059)을 씁니다(10/7).", "i059"),
    "i210": ("M2.5 × 6 (화면 고정)", "i050 50개 봉에서 4개를 씁니다.", "i050"),
    "i200": ("micro-HDMI → HDMI 케이블", "2단계 리듬게임용입니다. 악기에는 필요 없습니다.", None),
    "i201": ("탭 핸들", "사용자가 전동 드릴을 가지고 있어 필요 없습니다.", None),
}
for _iid in ("i096", "i057"):   # 2026-10-16 A안: dropped before buying (k() lines above kept for the record)
    K.pop(_iid, None)
NOT_PHYSICAL = {"i117": "FluidSynth 2.6.1 (무료 내려받기)", "i118": "Salamander 그랜드 피아노 음원 SF2 (무료 내려받기)"}
DROPPED_EXTRA = [  # not in data.json items but in the data.json prep list
    dict(id="x01", name="게임용 모니터나 TV", reason="2단계 리듬게임용입니다. 악기에는 필요 없습니다.", replaced_by=None),
]

SOURCE = {}
for i in "i011 i058 i059 i060 i209 i211 i213 i216 i021 i222 i203 i204".split():
    SOURCE[i] = "owned"   # 10/8 user: no separate label for these; they are on hand like owned parts
for i in ("i001 i003 i005 i009 i012 i025 i026 i027 i028 i029 i031 i032 i034 i037 i080 "
          "i087 i088 i089 i090 i092 i093 i109 i205 i206 i207 i208 i224 i225 i040").split():
    SOURCE[i] = "owned"
for i in TOOL_WHERE:
    SOURCE[i] = "tool"
SOURCE["i081"] = "owned"   # 10/8 user: 만능기판은 넉넉하게 삼

# i081: the user bought enough perfboard (10/8: "만능 기판은 넉넉하게 사서 괜찮아").
k("i081", cat="센서·MCU·기판", name="양면 만능기판 12 × 18 cm (센서 기판 띠용)", unit="장", need=2,
  need_note="SB 띠 161.6 × 15.24 (6행) × 7 + EL 45.5 + ER 22.0 + J702 30 × 25 + J501 25 × 24 + 페달 센서 조각 — 180 mm 방향 띠가 한 장에 약 6개라 2장 (CAD E-SB 7·EL/ER-E-BOARD·J702BOARD·J501BOARD)",
  where="센서 기판 SB 띠(161.6 × 15.24, 6행) 7개, 끝 부속 EL·ER 띠, 가운데 유닛 J702 기판(30 × 25)·J501 기판(25 × 24), 페달 센서 조각(PS)을 자르는 판입니다. SB 띠는 센서 바 바로 아래(y60.65~75.89, z7~8.6)에 들어갑니다.",
  check="사용자가 넉넉히 준비했습니다(10/8). SB 띠는 길이 161.6 mm라 162 mm보다 긴 방향이 있는 판에서 자릅니다. 120 mm 판뿐이면 띠를 두 조각으로 나눠 버스선을 이어야 합니다.")

# Open points found while building the list (shown on the page; 합니다체).
ISSUES = [
    dict(level="중간", id="i098",
         text="센서 자석 Ø5 × 2를 89개만 주문해 예비가 없습니다. 깨지거나 극을 거꾸로 붙이면 다시 사야 합니다(대건상사, 배송비 2,500원)."),
    dict(level="중간", id="i093",
         text="허브 DC 전원: 딸린 어댑터 선의 곧은 플러그가 잭 면에서 37 mm보다 길면 같은 규격의 짧은 DC 플러그 선이 따로 필요합니다(값 미정). 받으면 재 봅니다."),
    dict(level="중간", id="i022",
         text="USB-A → C 선 8가닥(NA993 1 m × 2, HB466 50 cm × 6)은 C 쪽 몰드 크기가 공개되지 않았습니다. 받으면 폭 12.5·두께 7.6·길이 25 mm 이하인지 단계 0 시험 19로 확인합니다."),
    dict(level="낮음", id="i006",
         text="100 nF 1206 칩 콘덴서는 100개를 주문해 예비가 3개뿐입니다. 더 잃어버리거나 깨지면 디바이스마트(no=14991278, 100개 단위)에서 다시 사야 합니다. 봉투째 두고 하나씩 꺼냅니다."),
    dict(level="낮음", id="i007",
         text="10 µF 1206 칩 콘덴서를 16개만 주문해 예비가 없습니다. 잃어버리거나 깨지면 엘레파츠(2675965)에서 다시 사야 합니다. 봉투째 두고 하나씩 꺼냅니다."),
    dict(level="낮음", id="i089",
         text="PETG: 출력 파일의 속 꽉 채움 질량은 악기 8.66 kg + 공구·지그 0.33 kg이고 가진 필라멘트는 8 kg입니다. 실제 채움(벽 3줄 + 15~40 %)이면 훨씬 적지만, 슬라이서 합계로 확인합니다. CAD에 '회색'으로 적힌 61개는 검정으로 뽑아도 됩니다."),
    dict(level="낮음", id="tools",
         text="합판 직접 톱질(스피커 바깥 옆판 40° 사선·통로 홈 27 × 22, 가운데 뒤판 창 140.5)에 쓸 목공 톱이 공구 목록에 없습니다. 쇠톱(i045)으로 자르거나 가진 톱을 씁니다."),
    dict(level="낮음", id="i113",
         text="65 W PD 충전기(i094)가 빠져 Pinecil 전원은 가진 USB-C PD 충전기(20 V 3 A 이상)나 DC 12~24 V로 받습니다."),
    dict(level="낮음", id="i216",
         text="고무 슬리브는 연료 호스(OD8 × ID4.5)에서 13 mm 4개를 자릅니다. 바깥 8 mm 튜브면 어느 것이든 됩니다."),
]

# CAD match rules: regexes on CAD part id (re.fullmatch)
CAD = {
    "i001": [r"CU-E-PI5.*"], "i003": [r"CU-E-BUCK"], "i009": [r"CU-E-AMP"],
    "i011": [r"(O\d|EL|ER)-NUT-.*", r"BRK2-[LR]-NUT\d"],
    "i014": [r"(O\d|EL|ER)-CAPSTAN-.*"], "i021": [r"C-PWR-5V"],
    "i022": [r"O[12]-C-USB"], "i226": [r"O[3-7]-C-USB", r"C-USB-PED"], "i228": [r"O[5-7]-E-MB", r"CU-E-PEDBOARD"], "i023": [r"O\d-C-RIBBON", r"E[LR]-C-LEAD"],
    "i033": [r"CU-E-J702", r"CU-E-J501", r"EL-E-J701"], "i034": [r"CU-E-GENDER"],
    "i037": [r"C-SPK-[LR]", r"C-SPKPIG-[LR]", r"C-PWR-FUSE", r"C-PWR-BUS"],
    "i039": [r"FOOT-\d+"], "i050": [r"TS-M25-\d"], "i051": [r"SPK-[LR]"],
    "i058": [r".*-SBSCREW\d", r"CU-M3X10-\d"], "i059": [r"O\d-RAILSCREW\d"],
    "i061": [r"(O\d|EL|ER)-EVA", r"SPK[LR]-GASKET", r"JOIN-EVA-[LR]\d"],
    "i062": [r".*-RESTFELT-.*"], "i066": [r".*-B-keyrodSUS304D4"], "i067": [r".*-B-leverrod.*"],
    "i081": [r"O\d-E-SB", r"E[LR]-E-BOARD", r"CU-E-J702BOARD", r"CU-E-J501BOARD"],
    "i084": [r"O\d-E-ZERO", r"CU-E-PEDZERO"], "i085": [r"O\d-E-MUX"], "i093": [r"PB-E-HUB", r"C-PWR-5V"],
    "i096": [r"(SPK[LR]|CU)-PLY-.*"], "i098": [r".*-MAGNET-.*"], "i099": [r"CU-MAG-.*"],
    "i101": [r"C-XH-[LR]", r"O\d-C-EXT"],
    "i106": [r".*-B-keeperfelt-.*", r".*-FELTSTRIP-.*", r".*-B-whitefrontfelt3T", r".*-B-blackfrontfelt-.*"],
    "i107": [r".*-RESTFELT-.*", r".*-B-upstoppad-.*"], "i109": [r"PEDAL-DAMPER"], "i111": [r"CU-E-DONGLE"],
    "i112": [r"BRK2-[LR]-GROM\d"], "i119": [r".*-STEEL-.*"], "i121": [r".*-B-balancepinD2-.*"],
    "i123": [r".*-SPRING-.*"], "i124": [r".*-B-upstoppad-.*"],
    "i125": [r".*-B-whitefrontfelt3T", r".*-B-blackfrontfelt-.*"],
    "i202": [r"TS-E-SCREEN", r"TS-E-SCREEN-FOLD"], "i203": [r"TS-C-DSI"],
    "i205": [r"TS-C-PWR-RED"], "i207": [r"TS-C-PWR-RED"], "i206": [r"TS-C-PWR-BLK"], "i208": [r"TS-C-PWR-BLK"],
    "i209": [r"TS-M3X20-.*", r"BRK2-[LR]-BOLT\d"], "i211": [r"SPK[LR]-INS-\d", r"JOIN-INS-[LR]\d"],
    "i213": [r"SEAM-INS-\d"], "i214": [r"JOIN-TS-[LR]\d"], "i216": [r"JOIN-SLV-[LR]\d"],
    "i222": [r"C-USB-UPSTREAM"], "i224": [r"C-XT60M-[LR]", r"C-XT60", r"C-PWR-IN"],
    "i225": [r"C-XT60F-[LR]", r"C-SPKPIG-[LR]"],
}
# physical units when the CAD parts are sub-solids of one thing
# photos taken from an equivalent listing, not the one actually ordered / shared
IMG_EXAMPLE = {"i052", "i070", "i099", "i033", "i053", "i055", "i050", "i058", "i059", "i060", "i209", "i212", "i112"}
SCH_QTY_SKIP = {"i023", "i101", "i005", "u01"}   # refdes count is not the line's unit (ribbon ends, pins, lead)
CAD_UNITS = {"i001": 1, "i202": 1, "i093": 1, "i021": 1, "i037": None, "i224": None, "i225": None}

# Schematic refs: (bom.csv code, filter on 값 or 부품) and cable codes
SCH_BOM = {
    "i004": [("L20", None)], "i006": [("SE4", None)], "i007": [("L67", None)], "i008": [("L68", None)],
    "i010": [("L56", None)], "i033": [("L15", None)], "i029": [("L29", "1k")], "i031": [("L29", "100k")],
    "i032": [("L29", "20Ω")], "i084": [("SEV2", "RP2040-Zero")], "i085": [("SEV2", "CD74HC4067 16채널 먹스 모듈")],
    "i005": [("SE7", None)], "i023": [("C05", None)], "i101": [("L66", None)], "i001": [("L01", None)],
    "i003": [("L58", None)], "i009": [("L53", None)], "i093": [("L17", None)], "i111": [("L51", None)],
    "i051": [("L07", None)], "i021": [("C24", None)], "i224": [("L80", None)], "i225": [("L81", None)],
    "u03": [("u03", None)], "u04": [("u04", None)], "u05": [("u05", None)],
    "u01": [("u01", None), ("", "XT60 암")], "i202": [("v4touch", "Waveshare"), ("v4touch", "동봉")],
    "i205": [("v4touch", "F/F")], "i206": [("v4touch", "F/F")],
    "i207": [("v4touch", "M/M")], "i208": [("v4touch", "M/M")],
}
SCH_CABLE = {"C05": ["i023"], "L17": ["i222"], "C25": ["i222"], "L17 부속": ["i093"], "L66": ["i101"], "L50": ["i013"],
             "SE12": ["i024"], "L80": ["i224"], "C13": ["i037"], "C24": ["i021"], "v4touch 49·50": ["i203", "i204"],
             "v4touch 51·52": ["i205", "i206"], "v4touch 53·54": ["i207", "i208"], "v4touch 135": ["i202"],
             "C14": ["i038"], "L81": ["i225"], "L52": ["i034"]}
# rev E cables.csv gives the touchscreen wires one code ('v4touch'), so they are matched by wire number
SCH_WIRE = {"W201": ["i022"], "W202": ["i022"], **{"W20%d" % k: ["i226"] for k in range(3, 9)},
            "W605": ["i203", "i204"], "W606": ["i205", "i206"], "W607": ["i207", "i208"], "W608": ["i202"]}

# Spec rows: drop shop/price rows; patch rows that describe the old design.
SPEC_DROP_KEYS = re.compile(r"가격|판매|배송|단가")
SPEC_PATCH = {

    "i039": {"높이": "CAD는 5 mm로 그림 — 받으면 잼"},
    "i010": {"필터": "1 µF 2개 병렬(2 µF)을 신호에 직렬 + 1 kΩ를 GND로. 앰프 입력(약 9 kΩ)과 보드 입력 콘덴서까지 넣어 계산하면 fc ≈ 93 Hz (필터만 따로 보면 79.6 Hz)"},
    "i050": {"체결": "Pi 받침 기둥 구멍 Ø2.2 × 5 (바닥 1.0)에 자가 탭, 화면은 뒷면 M2.5 구멍"},
    "i052": {"소재": "폴리에스터 솜 (방울솜)", "용량": "1 kg", "사용량": "상자마다 약 35 g (CAD README)", "안전": None},
    "i059": {"체결": "모듈: 밸런스 레일 깊은 구멍 Ø6.2(바닥 z10.1) → 레일 1.5 + 바닥틀 받침 Ø2.5 막힌 구멍 4.5 물림 (A16). 가운데 유닛: 5 mm 받침 기둥 관통 구멍",
             "머리": "버튼헤드(ISO 7380) 또는 소켓 캡(DIN 912) 모두 들어감"},
    "i070": {"제품": "드로잉용 흑연 파우더 소 (브랜드 표기 없음)"},
    "i096": {"조각 (L2, 16)": None, "재단": "무료, 직선만 (사선·홈·창은 직접)"},
    "i099": {"규격": "Ø8 × 3 mm 네오디뮴 (코멧, 등급 표기 없음)"},
    "i112": {"수량": "20개 (4개 사용)"},
    "i211": {"규격": "M4 황동 열압입 인서트: 앞판용 바깥 Ø6 × 4 (8개), 이음용 바깥 Ø6 × 6 (4개)"},
    "i213": {"규격": "M3 황동 열압입 인서트 바깥 Ø5 × 높이 4", "CAD 구멍": "Ø4.2 × 4.5 (자리파기 깊이 5.5)"},
    "i216": {"규격": "연료 호스 바깥 Ø8 × 안 Ø4.5. CAD도 이 호스로 그림",
             "쓰는 양": "13 mm × 4 = 52 mm",
             "대신 써도 되는 것": "바깥 8 mm 튜브 (실리콘 튜브 ID4 × OD8 등) — Ø8 구멍에 꽉 끼고 M4가 안을 지나면 됨"},
    "i209": {"머리": "화면 경첩·다리: 소켓 캡 또는 버튼헤드, 브래킷: 십자 둥근머리 가능"},
    "i058": {"체결": "센서 바: 출력 구멍 Ø2.7~2.8에 자가 탭. 화면 뚜껑: 레일 M3 인서트"},
    "i022": {"길이": "1 m (O1·O2 자리, CAD 경로 + 플러그 기준)"},
    "i226": {"길이": "50 cm (O3·O4·O7·PED 0.5 m 자리, O5·O6 0.3 m 자리는 남는 선을 묶음)"},
    "i012": {"대신한 것": None},
    "i001": {"전원 설정": "EEPROM PSU_MAX_CURRENT=5000, config.txt usb_max_current_enable=1 (PD 없는 5.1 V 입력)"},
    "i003": {"판매 코드": None},
    "i063": {"재질": "텅스텐 퍼티 (약 10 g/cm³, 추정)"},
    "i098": {"재질·등급": "NdFeB N35 (Br 약 1.20 T, 추정)"},
    "i039": {"고정": "8호 13 mm 직결피스(i053) + M4 와셔(i060)"},
    "i064": {"맞는 나사": "M3 소켓 캡(DIN 912) — M3×10, M3×6, M3×20"},
    "i065": {"맞는 나사": "M3 ISO 7380 버튼헤드(캡스턴), M2.5 소켓 캡"},
    "i109": {"개조 센서": "DRV5055(i004) + 자석 Ø5×2(i098) + 100 nF(i006) + 1 kΩ(R551, i029)"},
}
FULLNAME_PATCH = {
    "i216": "연료 호스 바깥 8 × 안 4.5 mm",
}
# Aircon-shared lines: which part of the smart-aircon order covers them (hardware/bom/README.md,
# overrides.json 'own', CAD README).  The 10/7-before count is read from state_main.json / data.json.
AIRCON_SRC = {
    "i011": "p17 볼트·너트·와셔 세트", "i058": "p17 볼트·너트·와셔 세트", "i059": "p17 볼트·너트·와셔 세트",
    "i060": "p17 볼트·너트·와셔 세트", "i209": "p17 볼트·너트·와셔 세트",
    "i211": "p16 인서트 세트", "i213": "p16 인서트 세트",
    "i216": "p57 연료 호스 2 m",
    "i021": "p65, 같은 엘레파츠 상품", "i222": "p64, 같은 엘레파츠 상품",
    "i203": "p67, 같은 엘레파츠 상품", "i204": "p66, 같은 엘레파츠 상품",
}
AIRCON_COUNTED = {"i011", "i058", "i059", "i060", "i209", "i211", "i213"}   # sets (10/8 user: bolt/nut sets x3 bought, enough)
IDENT_PATCH = {
    "i014": "납작한 둥근 머리에 2 mm 육각 구멍이 있는 짧은 은색 나사입니다(나사부 6 mm). 스테인리스라 자석에 거의 붙지 않습니다.",
    "i011": "작은 M3 육각너트입니다. 강철이라 자석에 붙어, 자석에 거의 붙지 않는 스테인리스 캡스턴 나사와 구별됩니다.",
    "i096": "옅은 분홍빛 갈색의 가벼운 합판 10조각입니다. 가장 긴 702 × 56.35(가운데 뒤판)와 679 × 90(가운데 아랫판)으로 알아봅니다.",
    "i209": "M3 볼트, 나사 길이 20 mm입니다. 이 악기에서 가장 긴 M3입니다.",
    "i098": "지름 5 mm, 두께 2 mm의 은색 원판 자석입니다. 서로 붙어 막대 모양으로 옵니다. 뚜껑 자석(Ø8 × 3)과 섞이지 않게 합니다.",
    "i050": "가는 스텐 렌치볼트(M2.5 × 6) 50개입니다. 2 mm 육각 렌치가 맞습니다.",
    "i219": "머리가 평평한 접시형 피스(철, 흰색 아연 도금)이고 길이 13 mm입니다. 둥근머리(i053)와 머리 모양으로 가릅니다.",
    "i211": "작은 황동 원통이고 바깥에 톱니 무늬, 안에 M4 나사산이 있습니다. 앞판용은 길이 4, 이음용은 길이 6입니다.",
    "i213": "작은 황동 원통이고 안에 M3 나사산이 있습니다(바깥 Ø5 × 4). M4 인서트보다 가늡니다.",
    "i070": "작은 통에 회흑색 흑연 가루가 들어 있습니다. 손가락에 묻히면 은회색으로 미끄럽습니다.",
    "i012": "가진 순간접착제(시아노아크릴레이트)면 됩니다.",
    "i101": "6핀 JST-XH 호환 하우징이 달린 짧은 선 2가닥(플러그 1 + 소켓 1)이 한 쌍입니다.",
    "i053": "끝이 드릴 모양인 스텐 피스이고 둥근 머리에 십자 홈이 있습니다. 길이 13 mm입니다.",
    "i058": "M3 볼트, 나사 길이 10 mm(머리 제외)입니다. M3 × 6과 섞이면 길이로 가릅니다.",
    "i059": "M3 볼트, 나사 길이 6 mm(머리 제외)입니다. M3 × 10보다 짧습니다.",
    "i060": "얇은 평와셔입니다. 바깥 지름 9 mm, 구멍 약 4.3 mm입니다.",
    "i216": "바깥 지름 8 mm, 안 지름 4.5 mm인 연료 호스입니다.",
    "i081": "초록색 에폭시 양면 만능기판이고 2.54 mm 간격 구멍이 판 전체에 뚫려 있습니다.",
    "i115": "빨간 실리콘 피복의 말랑한 USB-C 양끝 케이블(1 m)입니다.",
    "i062": "검정색 얇은 펠트 낱장(30 × 45 cm)입니다. 종이처럼 얇고 뒷면이 접착형입니다. 대원 칼라펠트지 포장입니다.",
}

SPEC_ADD = {
    "i096": [["조각 (L2, 10)", "스피커 바깥 옆판 128.5 × 139.65 ×2, 뒤판 250 × 139.65 ×2, 윗판 250 × 14.14 ×2, 아랫판 250 × 90 ×2, 가운데 뒤판 702 × 56.35, 가운데 아랫판 679 × 90"]],
}


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
def to_hapnida(text):
    """Turn plain 한다체 sentence endings into 합니다체 ('...다.' at sentence end, also before '(...).')."""
    if not text:
        return text
    pred_vowel = ("크", "쓰", "빠르", "다르", "모자라", "아니", "이", "고르", "바르", "부르", "자르", "오르",
                  "흐르", "누르", "따르", "가르")

    def conv(word):
        if word.endswith("는다"):
            return word[:-2] + "습니다"
        stem = word[:-1]
        if not stem:
            return word
        last = stem[-1]
        code = ord(last) - 0xAC00
        if not (0 <= code < 11172):
            return stem + "입니다"
        jong = code % 28
        base = chr(0xAC00 + code - jong)
        if jong == 0:
            if stem.endswith("하") or stem.endswith(pred_vowel):
                return stem[:-1] + chr(ord(base) + 17) + "니다"     # 크다 → 큽니다, 필요하다 → 필요합니다
            return stem + "입니다"                                     # 퍼티다 → 퍼티입니다 (명사 + 이다)
        if jong in (4, 8):                                             # ㄴ다 → ㅂ니다, 길다 → 깁니다
            return stem[:-1] + chr(ord(base) + 17) + "니다"
        return stem + "습니다"

    text = re.sub(r"([가-힣]+다)(\s*\([^()]*\))\.(?=\s|$)", lambda m: conv(m.group(1)) + m.group(2) + ".", text)
    text = re.sub(r"([가-힣]+다)\.(?=\s|$)", lambda m: conv(m.group(1)) + ".", text)
    text = re.sub(r"([A-Za-z0-9)\]'\"’”])다\.(?=\s|$)", lambda m: m.group(1) + "입니다.", text)
    return text


def load_xlsx():
    import openpyxl
    # the file keeps its formulas; a save from openpyxl drops the cached values, so evaluate them here
    wb = openpyxl.load_workbook(XLSX)
    memo = {}

    def cell(sheet, ref):
        key = (sheet, ref)
        if key not in memo:
            memo[key] = ev(sheet, wb[sheet][ref].value)
        return memo[key]

    def ev(sheet, v):
        if not (isinstance(v, str) and v.startswith("=")):
            return v
        f = v[1:]
        m = re.fullmatch(r"SUM\(([A-Z]+)(\d+):\1(\d+)\)", f)
        if m:
            return sum(cell(sheet, f"{m.group(1)}{i}") or 0 for i in range(int(m.group(2)), int(m.group(3)) + 1)
                       if isinstance(cell(sheet, f"{m.group(1)}{i}"), (int, float)))
        expr = re.sub(r"(?:'([^']+)'!)?\$?([A-Z]+)\$?(\d+)",
                      lambda mm: repr(cell(mm.group(1) or sheet, mm.group(2) + mm.group(3)) or 0), f)
        if not re.fullmatch(r"[\d\s+\-*/().]+", expr):
            raise ValueError(f"xlsx formula not handled: {sheet} {v}")
        return eval(expr)

    out = {}
    for sheet in ("학교 구매", "사비 구매", "요약"):
        ws = wb[sheet]
        rows = [tuple(cell(sheet, c.coordinate) for c in r) for r in ws.iter_rows()]
        out[sheet] = [r for r in rows if any(c not in (None, "") for c in r)]
    return out


def cad_parts():
    sys.path.insert(0, CAD_SRC)
    os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))
    import build_all  # noqa: E402  (collect() only — never main())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        parts = build_all.collect()
    return parts


def base_name(n):
    n = re.sub(r"\s*\((?:[A-G]#?\d|[A-G]#?)\)\s*$", "", n)
    n = re.sub(r",\s*[A-G]#?\d\)", ")", n)
    n = re.sub(r"\b(O\d|W\d{3})\b", "", n)
    n = re.sub(r"\s+\d+\)$", ")", n)
    return re.sub(r"\s{2,}", " ", n).strip()


def won(n):
    return f"{n:,}원"


# --------------------------------------------------------------------------------------------
def main():
    data = json.load(open(os.path.join(BOM, "data.json")))
    state = json.load(open(os.path.join(BOM, "state_main.json")))
    ovr = json.load(open(os.path.join(BOM, "overrides.json")))
    D = {it["id"]: it for it in data["items"]}
    ships = data["ships"]
    errors, warns = [], []

    # ---- xlsx --------------------------------------------------------------------------------
    X = load_xlsx()
    by_title = {}
    for it in data["items"]:
        by_title.setdefault(it["t"], []).append(it["id"])
    ordered = {}
    school_lines = personal_lines = 0
    personal_ship = []
    school_sum = personal_item_sum = 0
    personal_total_xlsx = school_total_xlsx = None
    for sheet in ("학교 구매", "사비 구매"):
        for r in X[sheet][1:]:
            name, unit, qty, amount, store, url = (list(r) + [None] * 6)[:6]
            if name is None:
                continue
            if str(name).startswith("학교 구매 합계"):
                school_total_xlsx = amount
                continue
            if str(name).startswith("사비 구매 합계"):
                personal_total_xlsx = amount
                continue
            if str(name).startswith("배송비"):
                personal_ship.append(dict(store=store, fee=amount))
                continue
            ids = by_title.get(name, [])
            if len(ids) != 1:
                errors.append(f"xlsx {sheet} line '{name}' maps to {ids}")
                continue
            iid = ids[0]
            if iid in ordered:
                errors.append(f"xlsx line '{name}' maps to {iid} twice")
            if unit * qty != amount:
                errors.append(f"xlsx {name}: {unit} × {qty} != {amount}")
            ordered[iid] = dict(sheet=sheet, qty=qty, unit_price=unit, amount=amount, store=store, url=url,
                                store_key=D[iid].get("sk"))
            if sheet == "학교 구매":
                school_lines += 1
                school_sum += amount
            else:
                personal_lines += 1
                personal_item_sum += amount
    summ = {r[0]: r[1] for r in X["요약"][1:] if r and r[0]}
    school_ship_xlsx = summ.get("학교 주문 배송비")

    # school shipping per store, from the data.json ship rules (the xlsx only has the total)
    sch_store = {}
    for iid, o in ordered.items():
        if o["sheet"] == "학교 구매":
            sch_store.setdefault(o["store_key"], 0)
            sch_store[o["store_key"]] += o["amount"]
    school_ship_rows = []
    for sk, amt in sorted(sch_store.items(), key=lambda kv: -kv[1]):
        rule = ships.get(sk) or {}
        fee = rule.get("fee", 0)
        thr = rule.get("free_over")
        pay = 0 if (thr is not None and amt >= thr) else fee
        school_ship_rows.append(dict(store=sk, items=amt, fee=pay,
                                     rule=f"{won(fee)}" + (f", {won(thr)} 이상 무료" if thr else ""),
                                     basis=(rule.get("basis") or "")[:160]))
    school_ship_calc = sum(r["fee"] for r in school_ship_rows)
    personal_ship_sum = sum(r["fee"] for r in personal_ship)
    personal_stores = {}
    for iid, o in ordered.items():
        if o["sheet"] == "사비 구매":
            personal_stores.setdefault(o["store"], 0)
            personal_stores[o["store"]] += o["amount"]
    ship_map = {r["store"]: r["fee"] for r in personal_ship}
    personal_ship_rows = [dict(store=s, items=a, fee=ship_map.get(s, 0),
                               note="" if s in ship_map else "구매 목록에 배송비 줄 없음 (무료배송)")
                          for s, a in sorted(personal_stores.items(), key=lambda kv: -kv[1])]
    for s in ship_map:
        if s not in personal_stores:
            errors.append(f"personal shipping row for unknown store {s}")

    # ---- totals check --------------------------------------------------------------------------
    totals = dict(
        school_items=school_sum, school_ship=school_ship_xlsx, school_ship_calc=school_ship_calc,
        personal_items=personal_item_sum, personal_ship=personal_ship_sum,
        personal=personal_item_sum + personal_ship_sum,
        total=school_sum + (school_ship_xlsx or 0) + personal_item_sum + personal_ship_sum,
        school_lines=school_lines, personal_lines=personal_lines,
        xlsx=dict(school_items=school_total_xlsx, school_ship=school_ship_xlsx,
                  personal=personal_total_xlsx, total=summ.get("합계")),
        budget_school=data.get("budget"), school_left=(data.get("budget") or 0) - school_sum,
    )
    for key, exp in (("school_items", EXPECT["school_items"]), ("school_ship", EXPECT["school_ship"]),
                     ("school_ship_calc", EXPECT["school_ship"]), ("personal", EXPECT["personal"]),
                     ("total", EXPECT["total"]), ("school_lines", EXPECT["school_lines"])):
        if totals[key] != exp:
            errors.append(f"total {key} = {totals[key]} != expected {exp}")
    for key in ("school_items", "school_ship", "personal", "total"):
        if totals["xlsx"][key] != EXPECT[key]:
            errors.append(f"xlsx {key} = {totals['xlsx'][key]} != {EXPECT[key]}")

    # ---- sources -----------------------------------------------------------------------------------
    for iid, o in ordered.items():
        SOURCE[iid] = "school" if o["sheet"] == "학교 구매" else "personal"

    # ---- CAD -------------------------------------------------------------------------------------------
    parts = cad_parts()
    nonprint = [p for p in parts if p.kind != "print"]
    pid = {p.id: p for p in parts}

    def match(rules):
        ids = []
        for p in nonprint:
            if any(re.fullmatch(r, p.id) for r in rules):
                ids.append(p.id)
        return ids

    used_cad = set()

    # ---- schematic ---------------------------------------------------------------------------------
    bomrows = list(csv.DictReader(open(os.path.join(NET, "bom.csv"), encoding="utf-8-sig")))
    cabrows = list(csv.DictReader(open(os.path.join(NET, "cables.csv"), encoding="utf-8-sig")))

    def sch_for(iid):
        refs, qty = [], 0
        for code, flt in SCH_BOM.get(iid, []):
            for r in bomrows:
                if r["구매 목록 코드"].strip() != code:
                    continue
                if flt and not (flt in r["값"] or flt in r["부품 설명"][:20]):
                    continue
                n = int(r["전체 수량"] or 0)
                if n == 0:
                    continue
                nb = int(r["보드 수"] or 1)
                board = r["보드"].replace(" ", "")      # 'J702 기판' -> 'J702기판': keep '<board> <ref>' two tokens
                tag = f"{board} {r['부품']}" + (f" ×{nb}" if nb > 1 and n >= nb else "")
                refs.append(tag)
                qty += n
        for r in cabrows:
            codes = [c.strip() for c in re.split(r"\s·\s", r["구매 목록 코드"])] + [r["구매 목록 코드"].strip()]
            w = r["﻿W"] if "﻿W" in r else r["W"]
            if any(iid in SCH_CABLE.get(c, []) for c in codes) or iid in SCH_WIRE.get(w, []):
                refs.append(w)
        seen, out = set(), []
        for x in refs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out, qty

    # ---- images -------------------------------------------------------------------------------------
    os.makedirs(OUT_IMG, exist_ok=True)
    assets = []

    def copy_img(iid, fname):
        if not fname:
            return None
        src = os.path.join(BOM, "img", fname)
        if not os.path.exists(src):
            warns.append(f"{iid}: image {fname} missing")
            return None
        ext = os.path.splitext(fname)[1].lower()
        dst = os.path.join(OUT_IMG, iid + ext)
        if os.path.getsize(src) > 150_000:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im.thumbnail((640, 640))
            dst = os.path.join(OUT_IMG, iid + ".jpg")
            im.save(dst, "JPEG", quality=82)
        else:
            shutil.copyfile(src, dst)
        rel = os.path.relpath(dst, PAGE)
        assets.append(rel)
        return rel

    # ---- build items --------------------------------------------------------------------------------
    items = []

    def specs_of(iid):
        rows = []
        patch = SPEC_PATCH.get(iid, {})
        for kk, vv in D[iid].get("specs", []):
            if kk in patch:
                if patch[kk] is None:
                    continue
                vv = patch[kk]
            elif SPEC_DROP_KEYS.search(kk) or (kk in ("값",) and "원" in vv):
                continue
            vv = vv.replace("v3 조사: ", "").replace("v3 자료", "추정")
            rows.append([kk, vv])
        have = {r[0] for r in rows}
        for kk, vv in patch.items():
            if vv is not None and kk not in have and kk not in {r[0] for r in D[iid].get("specs", [])}:
                rows.append([kk, vv])
        rows += SPEC_ADD.get(iid, [])
        return rows

    def pack_note(iid, c, o):
        need, unit = c["need"], c["unit"]
        if o:
            units = o["qty"] * c["pack"]
            if units > need:
                return f"{units}{unit} 중 {need}{unit} 사용, {units - need}{unit} 남음"
            return f"{units}{unit} 모두 사용"
        if SOURCE.get(iid) == "aircon":
            where = AIRCON_SRC.get(iid, "")
            if iid == "i216":
                return ""
            if iid in AIRCON_COUNTED:
                old = state["qty"].get(iid, D[iid].get("used") or D[iid].get("qty"))
                txt = ""
                if old is not None and old != need:
                    txt += f" (10/7 이전 계획 {old}{unit})"
                return txt
            return ""
        return ""

    for iid, c in K.items():
        src = SOURCE.get(iid)
        if src is None:
            errors.append(f"{iid}: no source")
            continue
        o = ordered.get(iid)
        d = D[iid]
        rules = CAD.get(iid, [])
        ids = match(rules)
        used_cad.update(ids)
        names = []
        for x in ids:
            bn = base_name(pid[x].name_ko)
            if bn not in names:
                names.append(bn)
        sref, sqty = sch_for(iid)
        it = dict(
            id=iid, code=d.get("code"), name=c["name"], full_name=FULLNAME_PATCH.get(iid) or d.get("n"), cat=c["cat"], source=src,
            source_ko=SOURCE_KO[src], role=c["role"], optional=c["optional"],
            ordered=(dict(sheet=o["sheet"], qty=o["qty"], unit_price=o["unit_price"], amount=o["amount"],
                          store=o["store"], url=o["url"], units=o["qty"] * c["pack"]) if o else None),
            qty_need=c["need"], unit=c["unit"], need_note=c["need_note"], pack_note=pack_note(iid, c, o),
            where=c["where"], specs=specs_of(iid), ident=IDENT_PATCH.get(iid) or to_hapnida(d.get("ident", "")),
            img=copy_img(iid, d.get("img")),
            img_note=("같은 종류 예시 사진 (받은 물건과 모양이 다를 수 있음)" if iid in IMG_EXAMPLE else None),
            cad_match=dict(ids=ids, count=len(ids), name_contains=names[:6], rules=rules,
                           **({"units": CAD_UNITS[iid]} if CAD_UNITS.get(iid) else {})),
            sch_refs=sref, sch_qty=(None if iid in SCH_QTY_SKIP else (sqty or None)),
            check_on_arrival=c["check"], replaces=None,
            store_url=(o["url"] if o else (d.get("url") if src == "gap" else None)),
        )
        items.append(it)

    for n in NEW:
        ids = match(n["cad"])
        used_cad.update(ids)
        names = []
        for x in ids:
            bn = base_name(pid[x].name_ko)
            if bn not in names:
                names.append(bn)
        sref, sqty = sch_for(n["id"])
        items.append(dict(
            id=n["id"], code=n["code"] or None, name=n["name"], full_name=n["full_name"], cat=n["cat"],
            source=n["source"], source_ko=SOURCE_KO[n["source"]], role=n["role"], optional=n.get("optional", False),
            ordered=None, qty_need=n["need"], unit=n["unit"], need_note=n["need_note"],
            pack_note="", where=n["where"], specs=n["specs"], ident=n["ident"], img=None, img_note=None,
            cad_match=dict(ids=ids, count=len(ids), name_contains=names[:6], rules=n["cad"]),
            sch_refs=sref, sch_qty=(None if n["id"] in SCH_QTY_SKIP else (sqty or None)), check_on_arrival=n["check"], replaces=n["replaces"],
            store_url=None,
        ))
    for t in PREP:
        items.append(dict(
            id=t["id"], code=None, name=t["name"], full_name=t["name"], cat="공구" if t["role"] == "공구" else "소모품",
            source="tool" if t["role"] == "공구" else "owned", role=t["role"], optional=False,
            ordered=None, qty_need=1, unit="벌" if t["role"] == "공구" else "개", need_note=t["need_note"],
            pack_note="", where=t["where"], specs=[], ident="", img=None, img_note=None,
            cad_match=dict(ids=[], count=0, name_contains=[], rules=[]), sch_refs=[], sch_qty=None,
            check_on_arrival="", replaces=None, store_url=None,
        ))
        items[-1]["source_ko"] = SOURCE_KO[items[-1]["source"]]

    # sort: category, then (gap first is not wanted) source order inside, then id
    src_rank = {"school": 0, "personal": 1, "aircon": 2, "owned": 3, "gap": 4, "tool": 5}
    items.sort(key=lambda x: (CAT_ORDER.index(x["cat"]), src_rank[x["source"]], x["id"]))

    # ---- dropped ----------------------------------------------------------------------------------------
    dropped = []
    for iid, (nm, why, rep) in DROPPED.items():
        dd = D.get(iid, {})
        dropped.append(dict(id=iid, code=dd.get("code"), name=nm, full_name=dd.get("n"), reason=why, replaced_by=rep))
    dropped += [dict(id=x["id"], code=None, name=x["name"], full_name=x["name"], reason=x["reason"],
                     replaced_by=x["replaced_by"]) for x in DROPPED_EXTRA]
    software = [dict(id=i, name=v) for i, v in NOT_PHYSICAL.items()]

    # ---- validation ----------------------------------------------------------------------------------
    kept_ids = {x["id"] for x in items}
    for iid in DROPPED:
        if iid in kept_ids:
            errors.append(f"{iid} both dropped and kept")
    for x in data["items"]:
        if x["id"] not in kept_ids and x["id"] not in DROPPED and x["id"] not in NOT_PHYSICAL:
            errors.append(f"data.json item {x['id']} ({x['t']}) not classified")
    for iid in ordered:
        if iid not in kept_ids:
            errors.append(f"ordered item {iid} is not in the kept list")
    over = []
    for x in items:
        if x["ordered"]:
            if x["qty_need"] > x["ordered"]["units"]:
                over.append(f"{x['id']} {x['name']}: need {x['qty_need']} > ordered {x['ordered']['units']}")
        if x["source"] in ("school", "personal") and not x["ordered"]:
            errors.append(f"{x['id']} source {x['source']} without an ordered line")
    if over:
        errors += over
    # school/personal line count
    if sum(1 for x in items if x["source"] == "school") != EXPECT["school_lines"]:
        errors.append("school item count != 29")
    if sum(1 for x in items if x["source"] == "personal") != personal_lines:
        errors.append("personal item count mismatch")

    # CAD coverage: every non-print CAD part should be referred to by some line
    uncovered = sorted(p.id for p in nonprint if p.id not in used_cad)
    # cross-checks CAD count vs need (where the CAD models every unit)
    cad_checks = []
    for iid, exp in (("i014", 88), ("i011", 92), ("i098", 88), ("i123", 88), ("i119", 88), ("i121", 88),
                     ("i058", 22), ("i039", 14), ("i099", 12), ("i112", 4), ("i214", 4), ("i216", 4),
                     ("i213", 4), ("i211", 12), ("i209", 7), ("i066", 9), ("i067", 9), ("i084", 8), ("i085", 7),
                     ("i051", 2), ("u06", 4), ("i228", 4), ("i033", 3), ("i022", 2), ("i226", 6)):
        it = next(x for x in items if x["id"] == iid)
        ok = it["cad_match"]["count"] == exp
        cad_checks.append(dict(id=iid, expected=exp, cad=it["cad_match"]["count"], ok=ok))
        if not ok:
            errors.append(f"CAD count {iid}: {it['cad_match']['count']} != {exp}")
    sch_checks = []
    for iid, exp in (("i004", 89), ("i006", 97), ("i007", 16), ("i008", 4), ("i010", 4), ("i029", 4),
                     ("i031", 5), ("i032", 5), ("i033", 3), ("i084", 8), ("i085", 7)):
        it = next(x for x in items if x["id"] == iid)
        ok = it["sch_qty"] == exp and it["qty_need"] == exp
        sch_checks.append(dict(id=iid, expected=exp, sch=it["sch_qty"], need=it["qty_need"], ok=ok))
        if not ok:
            errors.append(f"schematic qty {iid}: sch {it['sch_qty']} need {it['qty_need']} != {exp}")
    # cable rules (circuit rev E): W601 assembled length, AUX pieces from one 3 m cable, speaker wire within the roll
    cable_checks = [
        dict(id="i224", rule="W601 꼬리 + 리드 − 겹침 ≤ 최대", value=W601["total"], limit=W601["max"],
             ok=bool(W601["total"] and W601["max"] and W601["total"] <= W601["max"])),
        dict(id="i038", rule="W701 + W707 ≤ 반쪽 1.5 m, W702 ≤ 1.5 m", value=(AUX["w701"] or 0) + (AUX["w707"] or 0),
             limit=AUX["half"], ok=bool(AUX["w701"] and AUX["w707"] and AUX["w702"]
                                        and AUX["w701"] + AUX["w707"] <= AUX["half"] and AUX["w702"] <= AUX["half"])),
        dict(id="i037", rule="스피커선 합 ≤ 잡은 m", value=round(_C13["total"]), limit=_C13["need_m"] * 1000,
             ok=_C13["total"] <= _C13["need_m"] * 1000),
    ]
    for c in cable_checks:
        if not c["ok"]:
            errors.append(f"cable rule {c['id']}: {c['rule']} ({c['value']} vs {c['limit']})")
    for iid, bad in (("i224", r"68 mm가 남게|약 32 mm를 잘라"), ("i038", r"각 약 0\.7 m")):
        it = next(x for x in items if x["id"] == iid)
        if re.search(bad, it["where"] + it["need_note"]):
            errors.append(f"{iid}: stale cable text")

    # ---- counts ----------------------------------------------------------------------------------------
    counts = {}
    for x in items:
        counts.setdefault(x["source"], 0)
        counts[x["source"]] += 1
    by_cat = {}
    for x in items:
        by_cat.setdefault(x["cat"], 0)
        by_cat[x["cat"]] += 1

    out = dict(
        version=1, generated=datetime.date.today().isoformat(),
        about="Toccata 최종 재료 목록 — 완성된 악기에 들어가는 모든 물건과 설계가 쓰는 개수 (build_items.py)",
        sources=dict(
            data="hardware/bom/final-bom/data.json", state="hardware/bom/final-bom/state_main.json",
            xlsx="최종본/01_구매목록/Toccata_학교_사비_구매목록_2026-10-08.xlsx",
            circuit="hardware/pcb/netlist/bom.csv, cables.csv (회로 %s)" % circuit_rev(),
            cad="hardware/mechanical/cad/src build_all.collect() (%d parts, %d non-print)" % (len(parts), len(nonprint)),
            cad_readme="hardware/mechanical/cad/README.md"),
        legend=dict(source=SOURCE_KO, role={"부품": "악기 안에 남는 것", "소모품": "만들며 쓰고 없어지는 것",
                                            "공구": "만들 때만 쓰는 도구", "부속": "악기와 함께 두는 것",
                                            "시험용": "책상 시험 때만"},
                    optional="true면 전체 준비율에서 뺍니다 (보험·시험용)",
                    qty_need="설계가 쓰는 개수 (단위는 unit). 낱개로 셀 수 없는 재료는 사는 단위로 셉니다",
                    cad_match="ids = 이 물건을 나타내는 CAD 부품 id (build_all.collect, 위치 표시용)"),
        cat_order=CAT_ORDER,
        totals=totals,
        shipping=dict(school=school_ship_rows, personal=personal_ship_rows,
                      note="학교 주문 배송비는 학교가 내고 20만 원 한도에 넣지 않습니다. 학교 주문의 판매처별 배송비는 data.json 배송 규칙으로 계산한 값이고 합계는 구매 목록과 같습니다."),
        counts=dict(by_source=counts, by_cat=by_cat, total=len(items),
                    checklist=sum(1 for x in items if not x["optional"])),
        items=items, dropped=dropped, software=software,
        issues=ISSUES + circuit_issues(nonprint) + ([dict(level="낮음", id="img", text="사진이 없는 줄: " + ", ".join(
            x["id"] for x in items if x["img"] is None and x["id"].startswith("i") and x["source"] != "tool") + ". 상품 사진을 새로 받지 않았습니다. 나사·자석·흡음솜·흑연 등 13줄은 같은 종류의 예시 사진입니다(img_note).")]
            if any(x["img"] is None and x["id"].startswith("i") and x["source"] != "tool" for x in items) else []),
        checks=dict(cad=cad_checks, schematic=sch_checks, cables=cable_checks, cad_uncovered=uncovered,
                    unmatched_images=[x["id"] for x in items if x["img"] is None and x["id"].startswith("i")]),
    )

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ---- report -------------------------------------------------------------------------------------------
    print(f"items {len(items)}  by source {counts}")
    print(f"school {won(school_sum)} + ship {won(school_ship_xlsx)} (calc {won(school_ship_calc)}) | "
          f"personal {won(personal_item_sum)} + ship {won(personal_ship_sum)} = {won(totals['personal'])} | "
          f"total {won(totals['total'])}")
    print(f"dropped {len(dropped)}  software {len(software)}  images {len(assets)}")
    print(f"CAD non-print parts not referred to by any line: {len(uncovered)} {uncovered[:12]}")
    for w in warns:
        print("WARN", w)
    for e in errors:
        print("ERROR", e)
    print("wrote", os.path.relpath(OUT_JSON, ROOT))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
