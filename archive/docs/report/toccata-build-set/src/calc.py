"""Derived numbers per method: print plan, filament, hardware quantities."""
import math
from model import L, METHODS, TAILS

OCT_EQ = 88 / 12          # octave-equivalents of frame parts
G_PER_H = 25.0            # PETG average throughput on a Bambu-class printer
WASTE = 1.15


def frame_parts(M):
    """(name, material, count, grams_each)."""
    mid = M["id"]
    rho = L["rho_petg"]
    fr_front = 164 * (34 * M["rail_w_top"] + 32 * M["rail_b_top"]) * 0.6 * rho / 1000
    fr_sens = (164 * 28 * 8 - 164 * 8 * 5) * 0.6 * rho / 1000
    parts = [("전면 레일", "PETG/PLA 회색", 8, fr_front), ("센서 레일", "PETG/PLA 회색", 8, fr_sens)]
    if mid in ("A", "B"):
        parts.append(("스프링 받침 레일", "PETG/PLA 회색", 8, 164 * 14 * M["post_top"] * 0.6 * rho / 1000))
    if mid == "A":
        parts.append(("스파인 받침 블록", "PETG/PLA 회색", 8, 164 * 20 * M["z_bot"] * 0.5 * rho / 1000))
    if mid in ("B", "D"):
        parts.append(("건반 힌지 콤", "PETG 회색", 8, (164 * 30 * 6 + 13 * 18 * 3 * (M["pivot"][1] + 5 - 6)) * 0.6 * rho / 1000))
    if mid == "C":
        parts.append(("밸런스 레일", "PETG/PLA 회색", 8, 164 * 24 * M["balrail_top"] * 0.5 * rho / 1000))
        parts.append(("백레일", "PETG/PLA 회색", 8, 164 * 20 * M["backrail_top"] * 0.6 * rho / 1000))
    if mid == "D":
        parts.append(("해머 콤", "PETG 회색", 8, (164 * 12 * 21) * 0.6 * rho / 1000))
        if M["h_rest_pad"] > 0:
            r0, r1 = M["h_rest"]
            parts.append(("추 받침 레일", "PETG/PLA 회색", 8, 164 * (r1 - r0) * M["h_rest_pad"] * 0.6 * rho / 1000))
        parts.append(("해머 레버 (빔 + 추 받침)", "PETG 회색", 88, M["beam_m"] + M["cradle_m"] + 0.8))
    return parts


def key_parts(M):
    mid = M["id"]
    wk, bk = M["wk"]["m"], M["bk"]["m"]
    if mid == "A":
        spine = 12 * 20 * 164 * 0.6 * L["rho_petg"] / 1000
        cap = 95 * (L["Bw"] + L["Bt"]) / 2 * L["black_h"] * 0.5 * L["rho_petg"] / 1000
        return [("건반 콤 (백·흑 스틱 + 스파인)", "PETG 흰색", 8, (7 * wk + 5 * (bk - cap) + spine) * 1.0),
                ("흑건 캡 (접착)", "PETG 검정", 36, cap)]
    if mid == "C":
        fw = wk * 240 / 372
        fb = bk * 240 / 372 + 0.0
        return [("백건 앞 부품", "PETG 흰색", 52, fw), ("흑건 앞 부품", "PETG 검정", 36, fb),
                ("건반 뒤 부품", "PETG 아무 색", 88, wk - fw)]
    return [("백건", "PETG 흰색", 52, wk), ("흑건", "PETG 검정", 36, bk)]


def print_plan(M):
    kp = key_parts(M)
    fp = frame_parts(M)
    rows = []
    for nm, mat, n, g in kp + fp:
        if nm == "건반 콤 (백·흑 스틱 + 스파인)":
            tot = g * OCT_EQ
        elif n == 8 and nm not in ("해머 레버",):
            tot = g * OCT_EQ
        else:
            tot = g * n
        rows.append(dict(name=nm, mat=mat, n=n, g=g, tot=tot))
    white = sum(r["tot"] for r in rows if "흰색" in r["mat"]) * WASTE
    black = sum(r["tot"] for r in rows if "검정" in r["mat"]) * WASTE
    other = sum(r["tot"] for r in rows if "흰색" not in r["mat"] and "검정" not in r["mat"]) * WASTE
    total = white + black + other
    return dict(rows=rows, white=white, black=black, other=other, total=total, hours=total / G_PER_H)


TIER = {  # 11번가 웰빙천사 재단 가격 (가로+세로 합 구간), 2026-09-24 확인분
    "MDF18": [(1600, 22400), (1800, 28100)],
    "MDF12": [(1800, 19000)],
    "자작18": [(1600, 70000), (1800, 88400)],
}


def panel_price(mat, w, h):
    s = w + h
    for lim, p in TIER[mat]:
        if s <= lim:
            return p, s <= 1400
    return round(TIER[mat][-1][1] * 1.2, -2), True      # beyond listed tiers: +20 % estimate


def plywood(M):
    """cut list (mm): (name, qty, w, h, t, material)."""
    W = 52 * L["Pw"] + 2 * 26
    d = M["depth"] + 14
    return [
        ("키베드", 1, W, d + 150, 18, "MDF18"),
        ("뚜껑·명판", 1, W, d, 18, "MDF18"),
        ("키슬립(앞)", 1, W, 40 + M["slip_top"], 18, "MDF18"),
        ("옆판(치크) 2개분 — 받아서 반으로 자름", 1, 2 * (d + 170) + 10, 120, 18, "MDF18"),
        ("뒤판", 1, W, 200, 12, "MDF12"),
        ("스피커 바 앞판 (유닛 구멍 Ø94)", 1, W, 150, 18, "MDF18"),
        ("스피커·서브 상자 판재 (직접 재단)", 3, 1200, 400, 18, "MDF18"),
    ]


def plywood_cost(M):
    rows, tot = [], 0
    for nm, n, w, h, t, mat in plywood(M):
        p, est = panel_price(mat, w, h)
        rows.append((nm, n, w, h, t, mat, p, est))
        tot += p * n
    return rows, tot


def hw_qty(M):
    mid = M["id"]
    q = dict(pin3=100, magnets=100, halls=100)
    q["pin3_len"] = M["pin_len"]            # guide pin Ø3 x pin_len (D is longer: taller key)
    q["springs"] = 100 if mid in ("A", "B") else 0
    q["setscrew"] = 100 if mid in ("A", "B") else 0
    q["shaft4"] = 8 if mid in ("B", "D") else 0
    q["shaft3"] = 8 if mid == "D" else 0
    q["dowel4"] = 100 if mid == "C" else 0
    q["punch"] = 100 if mid == "C" else 0
    q["flat925_m"] = (52 * M.get("cw_len", 0) + 36 * M.get("cw_len_b", 0)) / 1000 * 1.05 if mid == "C" else 0
    q["flat616_m"] = (52 * M.get("w_len", 0) + 36 * M.get("w_len_b", 0)) / 1000 * 1.05 if mid == "D" else 0
    q["inserts"] = {"A": 60, "B": 60, "C": 260, "D": 260}[mid]
    q["steel_kg"] = (52 * M.get("m_cw", 0) + 36 * M.get("m_cw_b", 0)) / 1000 if mid == "C" else (
        (52 * M.get("m_w", 0) + 36 * M.get("m_w_b", 0)) / 1000 if mid == "D" else 0)
    return q


if __name__ == "__main__":
    for M in METHODS:
        pp = print_plan(M)
        print(M["id"], {k: round(v, 2) for k, v in pp.items() if k != "rows"})
        for r in pp["rows"]:
            print("   ", r["name"], r["n"], round(r["g"], 1), round(r["tot"]))
        print("   hw", {k: round(v, 2) if isinstance(v, float) else v for k, v in hw_qty(M).items()})
